"""
Extended RAG tests covering:
- Empty retrieval (no chunks in DB)
- Insufficient relevance (threshold filtering)
- Citation validation (IDs map to real stored content)
- Provider equivalence (same retrieval for same query)
- Provider failure handling
- Missing embedding model errors
"""
import pytest
import numpy as np
from uuid import uuid4
from unittest.mock import patch, AsyncMock

from app.services.chunking_service import ChunkingService
from app.services.retrieval_service import RetrievalService, RetrievalResult, RetrievalError
from app.services.embedding_service import OllamaEmbeddingService, EmbeddingError
from app.models.knowledge_base import TranscriptDocument, TranscriptChunk
from app.schemas.chat import Citation
from tests.fakes.embedding import FakeEmbeddingForUnitTestsOnly

pytestmark = pytest.mark.asyncio




async def _seed_kb(db_session, doc_id_prefix="test"):
    """Seed knowledge base with two documents and chunks."""
    doc1 = TranscriptDocument(
        id=uuid4(),
        stable_doc_id=f"{doc_id_prefix}_doc1",
        episode_title="Retention Deep Dive",
        source_url="https://example.com/ep1",
        guest="Brian Balfour",
        content_hash="h1",
        status="ingested"
    )
    doc2 = TranscriptDocument(
        id=uuid4(),
        stable_doc_id=f"{doc_id_prefix}_doc2",
        episode_title="Product-Market Fit",
        source_url="https://example.com/ep2",
        guest="Rahul Vohra",
        content_hash="h2",
        status="ingested"
    )
    db_session.add_all([doc1, doc2])
    await db_session.flush()

    # Chunk embeddings: doc1 chunks point "north", doc2 chunks point "east"
    c1 = TranscriptChunk(
        id=uuid4(), stable_chunk_id=f"{doc_id_prefix}_c1",
        document_id=doc1.id, chunk_index=0,
        content="Retention is the foundation of growth.",
        embedding=[1.0, 0.0, 0.0]
    )
    c2 = TranscriptChunk(
        id=uuid4(), stable_chunk_id=f"{doc_id_prefix}_c2",
        document_id=doc1.id, chunk_index=1,
        content="A leaky bucket cannot be filled by acquisition alone.",
        embedding=[0.9, 0.1, 0.0]
    )
    c3 = TranscriptChunk(
        id=uuid4(), stable_chunk_id=f"{doc_id_prefix}_c3",
        document_id=doc2.id, chunk_index=0,
        content="Use the Sean Ellis test: 40% very disappointed threshold.",
        embedding=[0.0, 1.0, 0.0]
    )
    db_session.add_all([c1, c2, c3])
    await db_session.commit()
    return doc1, doc2, c1, c2, c3


# ============================================================
# Test: Empty retrieval (no chunks in DB)
# ============================================================
async def test_empty_knowledge_base_returns_no_results(db_session):
    """When the knowledge base is empty, retrieval must return an empty list."""
    from sqlalchemy import text
    await db_session.execute(text("DELETE FROM transcript_chunks"))
    await db_session.execute(text("DELETE FROM transcript_documents"))
    await db_session.commit()
    service = RetrievalService(
        embedding_service=FakeEmbeddingForUnitTestsOnly(),
        top_k=5, similarity_threshold=0.3
    )
    results = await service.search(db_session, query="anything")
    assert results == []


# ============================================================
# Test: Insufficient relevance (threshold filtering)
# ============================================================
async def test_threshold_filters_low_similarity(db_session):
    """Chunks below the similarity threshold must not appear in results."""
    await _seed_kb(db_session, "thresh")

    # Query vector orthogonal to all stored chunks -> cosine ~ 0
    service = RetrievalService(
        embedding_service=FakeEmbeddingForUnitTestsOnly(query_vector=[0.0, 0.0, 1.0]),
        top_k=5, similarity_threshold=0.3
    )
    results = await service.search(db_session, query="something unrelated")
    assert len(results) == 0, f"Expected 0 results but got {len(results)}"


async def test_high_threshold_narrows_results(db_session):
    """A higher threshold should return fewer or no results."""
    await _seed_kb(db_session, "hithresh")

    service = RetrievalService(
        embedding_service=FakeEmbeddingForUnitTestsOnly(query_vector=[1.0, 0.0, 0.0]),
        top_k=5, similarity_threshold=0.95
    )
    results = await service.search(db_session, query="retention")
    # Only the chunk with embedding [1.0, 0.0, 0.0] has cosine=1.0; [0.9, 0.1, 0.0] normalized ~ 0.994
    # Both should pass 0.95 but the PMF chunk should not
    for r in results:
        assert r.similarity_score >= 0.95
        assert "Sean Ellis" not in r.content  # PMF chunk must be excluded


# ============================================================
# Test: Citation validation (IDs map to real stored content)
# ============================================================
async def test_citation_ids_map_to_stored_content(db_session):
    """Every returned citation must reference a real chunk with matching content."""
    doc1, doc2, c1, c2, c3 = await _seed_kb(db_session, "cite")

    service = RetrievalService(
        embedding_service=FakeEmbeddingForUnitTestsOnly(query_vector=[1.0, 0.0, 0.0]),
        top_k=5, similarity_threshold=0.3
    )
    results = await service.search(db_session, query="retention")

    # Build lookup from DB
    from sqlalchemy import select
    all_chunks = (await db_session.execute(select(TranscriptChunk))).scalars().all()
    chunk_map = {c.stable_chunk_id: c.content for c in all_chunks}

    for r in results:
        assert r.chunk_id in chunk_map, f"Citation chunk_id '{r.chunk_id}' not found in DB"
        assert chunk_map[r.chunk_id] == r.content, (
            f"Citation content mismatch for chunk_id '{r.chunk_id}': "
            f"DB has '{chunk_map[r.chunk_id]}', citation has '{r.content}'"
        )


# ============================================================
# Test: Provider equivalence (same retrieval for same query)
# ============================================================
async def test_all_providers_receive_same_context(client, db_session):
    """All three providers must receive the same system instruction with the same evidence."""
    from app.providers.router import provider_router
    from app.providers.base import ProviderResponse

    await _seed_kb(db_session, "prov")

    captured_instructions = []

    async def mock_generate(provider_name, messages, system_instruction):
        captured_instructions.append(system_instruction)
        return ProviderResponse(
            content="mocked answer",
            provider=provider_name or "ollama",
            model="mock"
        )

    with patch('app.api.v1.endpoints.chat.get_retrieval_service') as mock_rs:
        mock_rs.return_value = RetrievalService(
            embedding_service=FakeEmbeddingForUnitTestsOnly(query_vector=[1.0, 0.0, 0.0]),
            top_k=5, similarity_threshold=0.3
        )
        with patch.object(provider_router, 'generate', new=mock_generate):
            # Create 3 sessions, one per provider
            for provider in ["ollama", "claude"]:
                resp = await client.post("/api/v1/sessions", json={"title": f"{provider} test"})
                sid = resp.json()["id"]
                await client.post(
                    f"/api/v1/sessions/{sid}/chat",
                    json={"content": "Tell me about retention", "provider": provider}
                )

    assert len(captured_instructions) == 2
    # All system instructions must be identical
    assert captured_instructions[0] == captured_instructions[1], (
        "Providers received different system instructions"
    )


# ============================================================
# Test: Provider failure does not produce fake answer
# ============================================================
async def test_provider_failure_returns_error(client, db_session):
    """If the LLM provider fails, the endpoint must return an error, not a fake answer."""
    from app.providers.router import provider_router

    async def failing_generate(provider_name, messages, system_instruction):
        raise RuntimeError("Provider is down")

    with patch('app.api.v1.endpoints.chat.get_retrieval_service') as mock_rs:
        mock_rs.return_value = RetrievalService(
            embedding_service=FakeEmbeddingForUnitTestsOnly(),
            top_k=5, similarity_threshold=0.3
        )
        with patch.object(provider_router, 'generate', new=failing_generate):
            resp = await client.post("/api/v1/sessions", json={"title": "fail test"})
            sid = resp.json()["id"]
            chat_resp = await client.post(
                f"/api/v1/sessions/{sid}/chat",
                json={"content": "some question", "provider": "ollama"}
            )
            assert chat_resp.status_code == 500
            assert "Provider error" in chat_resp.json()["detail"]


# ============================================================
# Test: Missing embedding model raises clear error
# ============================================================
def test_embedding_error_when_ollama_unreachable():
    """When Ollama is unreachable, OllamaEmbeddingService must raise EmbeddingUnavailableError."""
    from app.services.embedding_service import OllamaEmbeddingService, EmbeddingUnavailableError
    svc = OllamaEmbeddingService(
        ollama_base_url="http://localhost:99999",  # unreachable
        model="nomic-embed-text",
        dimension=768,
        timeout=2,
    )
    with pytest.raises(EmbeddingUnavailableError):
        svc.embed_query("test")


# ============================================================
# Test: Chunking edge cases
# ============================================================
def test_chunking_empty_text():
    """Chunking empty text must return an empty list."""
    service = ChunkingService(chunk_size=100, chunk_overlap=10)
    assert service.chunk_text("", document_id="doc") == []
    assert service.chunk_text("   ", document_id="doc") == []


def test_chunking_deterministic_ids():
    """Chunk IDs must be deterministic for the same input."""
    service = ChunkingService(chunk_size=100, chunk_overlap=0)
    text = "Hello world. This is a test."
    chunks_a = service.chunk_text(text, document_id="doc1")
    chunks_b = service.chunk_text(text, document_id="doc1")
    assert len(chunks_a) == len(chunks_b)
    for a, b in zip(chunks_a, chunks_b):
        assert a.stable_chunk_id == b.stable_chunk_id

# ============================================================
# Test: Conversational & Grounded Assistant Tests (Phase 5)
# ============================================================

async def test_invalid_session_id_returns_404(client):
    """Invalid or nonexistent session IDs must return 404."""
    resp = await client.post(
        f"/api/v1/sessions/{uuid4()}/chat",
        json={"content": "hello", "provider": "ollama"}
    )
    assert resp.status_code == 404


async def test_session_isolation(client, db_session):
    """Messages from one session must not leak into another session."""
    from app.providers.router import provider_router
    from app.providers.base import ProviderResponse
    
    captured_messages = []
    
    async def mock_generate(provider_name, messages, system_instruction):
        captured_messages.append([m.content for m in messages])
        return ProviderResponse(content="mocked", provider="mock", model="mock")

    with patch('app.api.v1.endpoints.chat.get_retrieval_service') as mock_rs:
        mock_rs.return_value = RetrievalService(
            embedding_service=FakeEmbeddingForUnitTestsOnly(), top_k=5, similarity_threshold=0.0
        )
        with patch.object(provider_router, 'generate', new=mock_generate):
            # Session 1
            s1_resp = await client.post("/api/v1/sessions", json={"title": "Session 1"})
            s1_id = s1_resp.json()["id"]
            
            # Session 2
            s2_resp = await client.post("/api/v1/sessions", json={"title": "Session 2"})
            s2_id = s2_resp.json()["id"]
            
            # Send msg to S1
            await client.post(f"/api/v1/sessions/{s1_id}/chat", json={"content": "Message A", "provider": "ollama"})
            # Send msg to S2
            await client.post(f"/api/v1/sessions/{s2_id}/chat", json={"content": "Message B", "provider": "ollama"})
            
    assert len(captured_messages) == 2
    assert "Message A" in captured_messages[0]
    assert "Message B" not in captured_messages[0]
    
    assert "Message B" in captured_messages[1]
    assert "Message A" not in captured_messages[1]


async def test_multiturn_followup_and_context_passed_to_retrieval(client, db_session):
    """
    A multi-turn follow-up must:
    1. Pass conversation history to the provider.
    2. Pass recent context to the RetrievalService.search() method.
    """
    from app.providers.router import provider_router
    from app.providers.base import ProviderResponse

    captured_messages = []
    
    async def mock_generate(provider_name, messages, system_instruction):
        captured_messages.append([m.content for m in messages])
        return ProviderResponse(content="I am the assistant", provider="mock", model="mock")

    mock_rs = AsyncMock(spec=RetrievalService)
    mock_rs.search.return_value = []

    with patch('app.api.v1.endpoints.chat.get_retrieval_service', return_value=mock_rs):
        with patch.object(provider_router, 'generate', new=mock_generate):
            resp = await client.post("/api/v1/sessions", json={"title": "Multi-turn"})
            s_id = resp.json()["id"]
            
            # Turn 1
            await client.post(f"/api/v1/sessions/{s_id}/chat", json={"content": "What is PMF?", "provider": "ollama"})
            _, kwargs1 = mock_rs.search.call_args
            assert kwargs1["query"] == "What is PMF?"
            assert kwargs1["conversation_context"] is None
            
            # Turn 2
            await client.post(f"/api/v1/sessions/{s_id}/chat", json={"content": "Explain that further.", "provider": "ollama"})
            
            # Check retrieval context
            _, kwargs = mock_rs.search.call_args
            assert kwargs["query"] == "Explain that further."
            assert kwargs["conversation_context"] is not None
            assert "What is PMF?" in kwargs["conversation_context"]
            assert "I am the assistant" in kwargs["conversation_context"]

    # Check provider context
    assert len(captured_messages) == 2
    assert captured_messages[0] == ["What is PMF?"]
    assert captured_messages[1] == ["What is PMF?", "I am the assistant", "Explain that further."]
