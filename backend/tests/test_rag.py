import pytest
import numpy as np
from uuid import uuid4

from app.services.chunking_service import ChunkingService, ChunkMetadata
from app.services.embedding_service import OllamaEmbeddingService
from app.services.retrieval_service import RetrievalService, RetrievalResult
from app.models.knowledge_base import TranscriptDocument, TranscriptChunk
from app.schemas.chat import ChatRequest
from tests.fakes.embedding import FakeEmbeddingForUnitTestsOnly

pytestmark = pytest.mark.asyncio

def test_chunking_service():
    service = ChunkingService(chunk_size=10, chunk_overlap=2)
    
    text = "This is a very short text. " * 5
    chunks = service.chunk_text(text, document_id="doc1")
    
    assert len(chunks) > 0
    assert chunks[0].stable_chunk_id != ""
    assert chunks[0].metadata.chunk_index == 0

def test_chunking_preserves_speaker():
    service = ChunkingService(chunk_size=50, chunk_overlap=0)
    # The first paragraph has 19 tokens. With chunk_size=20, it should fit exactly.
    text = "**Lenny Rachitsky:** Hello and welcome.\n\n[Guest] Thanks for having me."
    
    chunks = service.chunk_text(text, document_id="doc1")
    assert len(chunks) == 1
    # When combined into a single chunk, it inherits the last speaker detected in that group
    assert chunks[0].metadata.speaker == "Guest"


async def test_retrieval_service(db_session):
    # Manually populate some chunks
    doc = TranscriptDocument(
        id=uuid4(),
        stable_doc_id="doc_retrieval_1",
        episode_title="Test Episode",
        content_hash="hash1",
        status="ingested"
    )
    db_session.add(doc)
    await db_session.flush()

    chunk1 = TranscriptChunk(
        id=uuid4(),
        stable_chunk_id="chunk_retrieval_1",
        document_id=doc.id,
        chunk_index=0,
        content="Product growth requires retention.",
        embedding=[1.0, 0.0, 0.0] # 3D for test
    )
    chunk2 = TranscriptChunk(
        id=uuid4(),
        stable_chunk_id="chunk_retrieval_2",
        document_id=doc.id,
        chunk_index=1,
        content="Marketing is about acquisition.",
        embedding=[0.0, 1.0, 0.0]
    )
    db_session.add(chunk1)
    db_session.add(chunk2)
    await db_session.commit()

    class _FakeRetention:
        def embed_query(self, query):
            if "retention" in query:
                return [1.0, 0.0, 0.0]
            else:
                return [0.0, 1.0, 0.0]

    retrieval_service = RetrievalService(
        embedding_service=_FakeRetention(),
        top_k=1,
        similarity_threshold=0.5
    )

    results = await retrieval_service.search(db_session, query="Tell me about retention")
    assert len(results) == 1
    assert results[0].content == "Product growth requires retention."
    assert results[0].episode_title == "Test Episode"


async def test_chat_with_retrieval(client, db_session):
    # Setup some DB context
    from app.providers.router import provider_router
    from app.providers.base import ProviderResponse
    from unittest.mock import patch
    
    doc = TranscriptDocument(
        id=uuid4(),
        stable_doc_id="doc_chat_1",
        episode_title="Chat Episode",
        content_hash="hash2",
        status="ingested"
    )
    db_session.add(doc)
    await db_session.flush()
    chunk1 = TranscriptChunk(
        id=uuid4(),
        stable_chunk_id="chunk_chat_1",
        document_id=doc.id,
        chunk_index=0,
        content="Product growth requires retention.",
        embedding=[1.0, 0.0, 0.0] # 3D for test
    )
    db_session.add(chunk1)
    await db_session.commit()

    # Mock embedding and provider
    async def mock_generate(provider_name, messages, system_instruction):
        # Verify the retrieved chunk is in the prompt
        assert "Product growth requires retention." in system_instruction
        return ProviderResponse(
            content="Mock answer based on evidence.",
            provider="ollama",
            model="qwen3:4b"
        )
        
    with patch('app.api.v1.endpoints.chat.get_retrieval_service') as mock_get_retrieval:
        mock_get_retrieval.return_value = RetrievalService(
            embedding_service=FakeEmbeddingForUnitTestsOnly(query_vector=[1.0, 0.0, 0.0]),
            top_k=1,
            similarity_threshold=0.5
        )
        with patch.object(provider_router, 'generate', new=mock_generate):
            # Create session
            create_resp = await client.post("/api/v1/sessions", json={"title": "RAG Chat"})
            session_id = create_resp.json()["id"]

            chat_resp = await client.post(
                f"/api/v1/sessions/{session_id}/chat",
                json={"content": "What about retention?", "provider": "ollama"}
            )
            
            assert chat_resp.status_code == 200
            data = chat_resp.json()
            assert "citations" in data
            assert len(data["citations"]) == 1
            assert data["citations"][0]["content"] == "Product growth requires retention."

async def test_chat_with_no_retrieval(client, db_session):
    from app.providers.router import provider_router
    from app.providers.base import ProviderResponse
    from unittest.mock import patch
    
    async def mock_generate(provider_name, messages, system_instruction):
        assert "No relevant transcript evidence was found" in system_instruction
        return ProviderResponse(
            content="I don't know.",
            provider="ollama",
            model="qwen3:4b"
        )
        
    with patch('app.api.v1.endpoints.chat.get_retrieval_service') as mock_get_retrieval:
        mock_get_retrieval.return_value = RetrievalService(
            embedding_service=FakeEmbeddingForUnitTestsOnly(query_vector=[0.0, 0.0, 1.0]),
            top_k=1,
            similarity_threshold=0.5
        )
        with patch.object(provider_router, 'generate', new=mock_generate):
            create_resp = await client.post("/api/v1/sessions", json={"title": "Empty RAG Chat"})
            session_id = create_resp.json()["id"]

            chat_resp = await client.post(
                f"/api/v1/sessions/{session_id}/chat",
                json={"content": "What about something else?"}
            )
            
            assert chat_resp.status_code == 200
            data = chat_resp.json()
            assert "citations" in data
            assert len(data["citations"]) == 0
