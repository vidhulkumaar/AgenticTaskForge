from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, List

from app.db.session import get_db
from app.services.session_service import SessionService
from app.services.retrieval_service import get_retrieval_service, RetrievalService, RetrievalError
from app.services.embedding_service import EmbeddingUnavailableError
from app.schemas.chat import ChatRequest, ChatResponse, Citation
from app.schemas.message import MessageCreate
from app.providers.router import provider_router
from app.providers.base import ProviderMessage
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def build_grounding_instruction(base_instruction: Optional[str], retrieved_passages: List[dict]) -> str:
    """Builds the system instruction incorporating retrieved evidence."""
    sys_prompt = base_instruction or (
        "You are The Lenny Growth Assistant. You provide actionable growth insights grounded in Lenny's Podcast transcripts. "
        "Answer the user's question using ONLY the provided retrieved evidence. "
        "When answering, clearly distinguish between explicit claims made in the transcripts and your own reasonable interpretations or syntheses. "
        "If the available evidence is insufficient to answer the question reliably, explicitly acknowledge that "
        "the transcripts do not support a reliable response, and do not fabricate an answer. "
        "If the user's question or follow-up is too ambiguous, ask a concise clarification question instead of guessing. "
        "Cite the sources by referring to the provided Document ID and Chunk ID."
    )
    
    if not retrieved_passages:
        return sys_prompt + "\n\nNo relevant transcript evidence was found for this query."
        
    evidence_text = "\n\n### RETRIEVED EVIDENCE ###\n"
    for idx, passage in enumerate(retrieved_passages):
        evidence_text += f"\n--- Source {idx+1} ---\n"
        evidence_text += f"Document ID: {passage['document_id']}\n"
        evidence_text += f"Chunk ID: {passage['chunk_id']}\n"
        if passage['episode_title']:
            evidence_text += f"Episode: {passage['episode_title']}\n"
        if passage['speaker']:
            evidence_text += f"Speaker: {passage['speaker']}\n"
        evidence_text += f"Excerpt: {passage['content']}\n"
        
    return sys_prompt + evidence_text

@router.post("/{session_id}/chat", response_model=ChatResponse)
async def chat(
    session_id: UUID, 
    chat_request: ChatRequest, 
    db: AsyncSession = Depends(get_db)
):
    session = await SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
    # Get previous messages for context
    db_messages, _ = await SessionService.get_messages(db, session_id, page=1, size=100)
    
    # Extract to plain dicts to prevent lazy loading errors after db.commit() in add_message
    message_history = [{"role": m.role, "content": m.content} for m in db_messages]
    
    # Extract conversation context for retrieval (last 2 messages)
    conversation_context = None
    if message_history:
        recent_msgs = message_history[-2:]
        conversation_context = " | ".join([f"{m['role']}: {m['content']}" for m in recent_msgs])

    # Perform retrieval BEFORE persisting anything
    retrieval_service = get_retrieval_service()
    citations: List[Citation] = []
    retrieved_passages_dicts = []
    
    try:
        results = await retrieval_service.search(
            db=db, 
            query=chat_request.content,
            conversation_context=conversation_context
        )
        for r in results:
            citations.append(Citation(
                document_id=r.document_id,
                chunk_id=r.chunk_id,
                episode_title=r.episode_title,
                source_url=r.source_url,
                content=r.content,
                timestamp_start=r.timestamp_start,
                speaker=r.speaker
            ))
            retrieved_passages_dicts.append({
                "document_id": r.document_id,
                "chunk_id": r.chunk_id,
                "episode_title": r.episode_title,
                "speaker": r.speaker,
                "content": r.content
            })
    except RetrievalError as e:
        logger.error(f"Retrieval failed: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Retrieval service unavailable: {str(e)}")
        
    # Build grounded system instruction
    grounded_system_instruction = build_grounding_instruction(
        chat_request.system_instruction, 
        retrieved_passages_dicts
    )
    
    # Convert DB messages + new user message to ProviderMessages
    provider_messages = []
    for msg in message_history:
        if msg['role'] in ("user", "assistant"):
            provider_messages.append(ProviderMessage(role=msg['role'], content=msg['content']))
    provider_messages.append(ProviderMessage(role="user", content=chat_request.content))
    
    # Invoke provider BEFORE persisting anything
    await db.commit() # Release SQLite lock during LLM generation
    try:
        provider_response = await provider_router.generate(
            provider_name=chat_request.provider,
            messages=provider_messages,
            system_instruction=grounded_system_instruction
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Provider error: {str(e)}")
        
    # SUCCESS: persist both user and assistant messages in one transaction
    user_message_in = MessageCreate(
        role="user",
        content=chat_request.content
    )
    user_message = await SessionService.add_message(db, session_id, user_message_in)

    assistant_metadata = {
        "provider": provider_response.provider,
        "model": provider_response.model,
        "citations": [c.model_dump() for c in citations]
    }
    if provider_response.metadata:
        assistant_metadata.update(provider_response.metadata)
        
    assistant_message_in = MessageCreate(
        role="assistant",
        content=provider_response.content,
        metadata_=assistant_metadata
    )
    assistant_message = await SessionService.add_message(db, session_id, assistant_message_in)
    
    return ChatResponse(
        session_id=session_id,
        message_id=assistant_message.id,
        provider=provider_response.provider,
        model=provider_response.model,
        content=provider_response.content,
        created_at=assistant_message.created_at,
        citations=citations
    )

from app.schemas.chat import ChatRequest, ChatResponse, Citation, EssayRequest, EssayResponse
import re

@router.post("/{session_id}/essay", response_model=EssayResponse)
async def generate_essay(
    session_id: UUID,
    essay_request: EssayRequest,
    db: AsyncSession = Depends(get_db)
):
    session = await SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
    user_prompt = (
        f"Topic: {essay_request.topic}\n"
        f"Target Audience: {essay_request.target_audience}\n"
        f"Central Argument: {essay_request.central_argument}\n"
    )

    # Retrieve BEFORE persisting anything
    retrieval_service = get_retrieval_service()
    citations: List[Citation] = []
    retrieved_passages_dicts = []
    
    try:
        results = await retrieval_service.search(db=db, query=essay_request.topic + " " + essay_request.central_argument)
        for r in results:
            citations.append(Citation(
                document_id=r.document_id,
                chunk_id=r.chunk_id,
                episode_title=r.episode_title,
                source_url=r.source_url,
                content=r.content,
                timestamp_start=r.timestamp_start,
                speaker=r.speaker
            ))
            retrieved_passages_dicts.append({
                "document_id": r.document_id,
                "chunk_id": r.chunk_id,
                "episode_title": r.episode_title,
                "speaker": r.speaker,
                "content": r.content
            })
    except RetrievalError as e:
        logger.error(f"Retrieval failed: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Retrieval service unavailable: {str(e)}")

    evidence_limitations = None
    if not retrieved_passages_dicts:
        evidence_limitations = "No relevant podcast evidence found. Output may rely heavily on general knowledge or be constrained."
        
    base_instruction = (
        "You are an expert essay writer for the Ship 30 for 30 framework. Write an essay based on the provided topic, audience, and central argument. "
        "Strict Requirements:\n"
        "- Target length of approximately 1,250 words.\n"
        "- A compelling opening hook.\n"
        "- A coherent narrative with skimmable headings and formatting.\n"
        "- A useful, actionable conclusion.\n"
        "- Ground factual claims about podcast guests, companies, frameworks, and examples in the retrieved evidence.\n"
        "- Distinguish sourced facts from original analysis.\n"
        "- Avoid invented quotes, statistics, anecdotes, and attribution.\n"
        "- Clearly state when evidence is insufficient for a requested claim. Do not fabricate supporting evidence simply to meet the word count.\n"
        "Output Format:\n"
        "Produce the essay wrapped entirely within an `<essay>` block. First line of the block must be `# [Title]` followed by the markdown body."
    )
    
    grounded_system_instruction = build_grounding_instruction(base_instruction, retrieved_passages_dicts)
    
    provider_messages = [ProviderMessage(role="user", content=user_prompt)]
    
    # Invoke provider BEFORE persisting anything
    await db.commit() # Release SQLite lock during LLM generation
    try:
        provider_response = await provider_router.generate(
            provider_name=essay_request.provider,
            messages=provider_messages,
            system_instruction=grounded_system_instruction
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Provider error: {str(e)}")
        
    raw_content = provider_response.content
    
    # Validation loop for word count (tightened range: 800-1700 for generous first pass)
    word_count = len(raw_content.split())
    if word_count < 800 or word_count > 1700:
        # Simple single retry for length issues
        retry_prompt = f"Your previous response was {word_count} words. It MUST be approximately 1,250 words. Please expand the depth of your analysis or concisely summarize to reach the target length without fabricating quotes."
        provider_messages.append(ProviderMessage(role="assistant", content=raw_content))
        provider_messages.append(ProviderMessage(role="user", content=retry_prompt))
        try:
            provider_response = await provider_router.generate(
                provider_name=essay_request.provider,
                messages=provider_messages,
                system_instruction=grounded_system_instruction
            )
            raw_content = provider_response.content
            word_count = len(raw_content.split())
        except Exception:
            pass # Keep original if retry fails

    # Extract Title and Body
    title = "Generated Essay"
    body = raw_content
    match = re.search(r"<essay>\s*(?:#\s*(.*?)\n)?(.*?)<\/essay>", raw_content, re.IGNORECASE | re.DOTALL)
    if match:
        if match.group(1):
            title = match.group(1).strip()
        body = match.group(2).strip()
        word_count = len(body.split())
    else:
        # Fallback heuristic
        lines = raw_content.split('\n')
        if lines[0].startswith('#'):
            title = lines[0].strip('# ')
            body = '\n'.join(lines[1:]).strip()
            word_count = len(body.split())

    # SUCCESS: persist both user and assistant messages in one transaction
    user_message_in = MessageCreate(role="user", content=f"Generate a Ship 30 for 30 essay based on:\n{user_prompt}")
    user_message = await SessionService.add_message(db, session_id, user_message_in)

    artifact_wrapper = f"<artifact type=\"markdown\" title=\"{title}\">\n# {title}\n\n{body}\n</artifact>"
    display_content = f"I've written an essay titled '{title}'. The essay is approximately {word_count} words long.\n\n{artifact_wrapper}"

    assistant_metadata = {
        "provider": provider_response.provider,
        "model": provider_response.model,
        "citations": [c.model_dump() for c in citations],
        "type": "essay",
        "word_count": word_count
    }
        
    assistant_message_in = MessageCreate(
        role="assistant",
        content=display_content,
        metadata_=assistant_metadata
    )
    assistant_message = await SessionService.add_message(db, session_id, assistant_message_in)

    return EssayResponse(
        session_id=session_id,
        message_id=assistant_message.id,
        title=title,
        body=body,
        word_count=word_count,
        citations=citations,
        limitations=evidence_limitations
    )

