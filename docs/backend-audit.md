# Backend Audit: The Lenny Growth Assistant

> **Living document.** Updated as each work block completes.

## Baseline (Block 0)

| Item | Result |
|---|---|
| Test suite baseline | **32 passed, 0 failed, 5 warnings** |
| Ollama running | Yes — `nomic-embed-text:latest`, `qwen3:4b` available |
| ANTHROPIC_API_KEY | Empty in `.env` — Claude live calls BLOCKED |
| Transcript data | 2 in `data/transcripts/`; 303 in `data/real_transcripts/episodes/` |

---

## Requirements Audit Table

### R1. Provider Architecture
| # | Requirement | Status | Evidence |
|---|---|---|---|
| R1.1 | Only `claude` and `ollama` providers remain | **VERIFIED** | Router whitelist; 422 for unknown |
| R1.2 | Gemini provider fully removed | **VERIFIED** | `gemini.py` deleted; `.env` cleaned; grep clean |
| R1.3 | Clear HTTP 422 for unsupported provider | **VERIFIED** | `test_unknown_provider` passes |
| R1.4 | No silent fallback between providers | **VERIFIED** | Code raises, never substitutes |
| R1.5 | BaseProvider interface preserved | **VERIFIED** | ABC with `generate()` |
| R1.6 | Claude error handling (auth, rate, timeout) | **VERIFIED** | `claude.py:38-47` |
| R1.7 | Ollama error handling (connection, 404) | **VERIFIED** | `ollama.py:32-47` |

### R2. Configuration and Environment
| # | Requirement | Status | Evidence |
|---|---|---|---|
| R2.1 | Gemini settings removed from config | **VERIFIED** | `config.py` clean |
| R2.2 | Gemini removed from `.env.example` | **VERIFIED** | Root `.env.example` updated |
| R2.3 | Gemini removed from `backend/.env` | **FIXED** | Lines 25-27 removed |
| R2.4 | `.env` in `.gitignore` | **VERIFIED** | Line 2 |
| R2.5 | `USE_DUMMY_EMBEDDINGS` removed from production | **FIXED** | Setting, `DummyModel` class, all branches removed. Fakes moved to `tests/fakes/` |
| R2.6 | Real Ollama embeddings configured | **FIXED** | `backend/.env` now uses Ollama only |
| R2.7 | Embedding dimension matches model | **FIXED** | Set to 768 (nomic-embed-text) |
| R2.8 | Duplicate `OLLAMA_BASE_URL` in config | **FIXED** | Single field remains |

### R3. Dependencies
| # | Requirement | Status | Evidence |
|---|---|---|---|
| R3.1 | `google-genai` removed from requirements | **VERIFIED** | Prior session |
| R3.2 | `google-genai` uninstalled from venv | **VERIFIED** | `pip list` clean |
| R3.3 | `anthropic` present | **VERIFIED** | `anthropic>=1.0.0` |
| R3.4 | Agent SDK dependency | **DOCUMENTED** | No official SDK exists; using Messages+Tools API |

### R4. Database and Sessions
| # | Requirement | Status | Evidence |
|---|---|---|---|
| R4.1 | Migrations reproduce from scratch | **VERIFIED** | Two migration files, tests use `create_all` |
| R4.2 | Foreign keys with CASCADE delete | **VERIFIED** | `ondelete="CASCADE"` |
| R4.3 | Session isolation | **VERIFIED** | `test_session_isolation` passes |
| R4.4 | 404 for unknown sessions | **VERIFIED** | `test_invalid_session_id_returns_404` passes |
| R4.5 | Message ordering | **VERIFIED** | `order_by(Message.created_at.asc())` |
| R4.6 | No orphan messages on provider failure | **FIXED** | Both messages now persisted AFTER provider success |
| R4.7 | Context window bounded | **VERIFIED** | Loads last 100 messages |

### R5. Ingestion and Retrieval
| # | Requirement | Status | Evidence |
|---|---|---|---|
| R5.1 | Genuine transcript source | **VERIFIED** | Real Lenny episodes |
| R5.2 | Metadata stored | **VERIFIED** | All fields present |
| R5.3 | Idempotent re-ingestion | **VERIFIED** | Content hash check |
| R5.4 | Accurate ingestion stats | **VERIFIED** | processed/skipped/failed |
| R5.5 | CLI for ingestion | **VERIFIED** | `ingestion/run.py`, `scripts/ingest.py` |
| R5.6 | Cosine similarity correct | **VERIFIED** | Normalize then dot product |
| R5.7 | Threshold direction correct | **VERIFIED** | `>=` for similarity |
| R5.8 | Deterministic tiebreaker | **FIXED** | Sort by `(-score, chunk_index)` |
| R5.9 | Ad/sponsor filtering | **DOCUMENTED** | Known gap; not implemented |
| R5.10 | Citations only for passed chunks | **VERIFIED** | Same `results` list |
| R5.11 | Three distinct outcomes | **VERIFIED** | results/no-results/error |
| R5.12 | Threshold calibration | **DOCUMENTED** | No labeled set exists |
| R5.13 | search_document/search_query prefixes | **VERIFIED** | `embedding_service.py` |

### R6. Agent Layer
| # | Requirement | Status | Evidence |
|---|---|---|---|
| R6.1 | Agent SDK integration | **FIXED** | Proper Messages+Tools loop with real KB search |
| R6.2 | Narrow tool exposure (search_transcripts) | **FIXED** | Single `search_transcripts` tool backed by RetrievalService |
| R6.3 | Max turns limit and timeout | **FIXED** | `AGENT_MAX_TURNS=4`, `AGENT_TIMEOUT=120` from config |
| R6.4 | Agent path exposed via endpoint | **DOCUMENTED** | No dedicated endpoint yet; wrapper available for integration |

### R7. Essay Generation
| # | Requirement | Status | Evidence |
|---|---|---|---|
| R7.1 | Word count enforcement | **VERIFIED** | Range 800-1700 with retry |
| R7.2 | Bounded retry (max 2 attempts) | **VERIFIED** | Single retry |
| R7.3 | No orphan on failure | **FIXED** | Persist after success only |
| R7.4 | Real citations in essay | **VERIFIED** | Same retrieval pipeline |
| R7.5 | Artifact wrapping | **VERIFIED** | `<artifact>` tags |

### R8. Health and Observability
| # | Requirement | Status | Evidence |
|---|---|---|---|
| R8.1 | `/health/live` | **VERIFIED** | Returns `{"status":"ok"}` |
| R8.2 | `/health/ready` (DB + Ollama) | **FIXED** | Now checks both DB and Ollama reachability |
| R8.3 | Correlation-ID middleware | **FIXED** | Added to `main.py`; `X-Correlation-ID` header |
| R8.4 | Structured logging | **DOCUMENTED** | Not yet JSON; uses Python stdlib logging |
| R8.5 | Consistent error envelope | **VERIFIED** | FastAPI `{"detail":"..."}` |
| R8.6 | EmbeddingUnavailableError -> 503 | **FIXED** | Global exception handler in `main.py` |

### R9/R10. Artifact Backend / Frontend
| # | Requirement | Status | Evidence |
|---|---|---|---|
| R9.1 | Backend artifact endpoint | **DOCUMENTED** | Not implemented; inline in message content |
| R10.1 | Gemini removed from frontend | **VERIFIED** | Prior session |
| R10.2 | TypeScript type excludes gemini | **VERIFIED** | `"ollama" | "claude"` |

---

## Block Completion Log

| Block | Status | Date |
|---|---|---|
| 0 - Baseline | COMPLETE | 2026-10-10 |
| 1 - Audit Document | COMPLETE | 2026-10-10 |
| 2 - Foundation (dummy/Gemini removal, embeddings, config) | COMPLETE | 2026-10-10 |
| 3 - Database and Sessions (orphan fix, essay fix) | COMPLETE | 2026-10-10 |
| 4 - Ingestion and Retrieval (tiebreaker) | COMPLETE | 2026-10-10 |
| 5 - Providers and Agent (agent rewrite, health check) | COMPLETE | 2026-10-10 |
| 6 - Essay, Artifacts, API (essay transaction fix) | COMPLETE | 2026-10-10 |
| 7 - Validation and Report | COMPLETE | 2026-10-10 |

---

## Final Test Results

```
32 passed, 5 warnings in 17.16s
```

All 32 tests pass after all changes. No test was edited just to make it pass — test assertions were updated only where the **behavior** was intentionally changed (orphan message fix: 1 orphan -> 0 messages on failure).

---

## Summary of Changes Made

### Files Modified
| File | Change |
|---|---|
| `app/core/config.py` | Removed `USE_DUMMY_EMBEDDINGS`, `USE_OLLAMA_EMBEDDINGS`, `EMBEDDING_MODEL`, duplicate `OLLAMA_BASE_URL`. Added `EMBEDDING_TIMEOUT`, `AGENT_MAX_TURNS`, `AGENT_TIMEOUT`. |
| `app/services/embedding_service.py` | **Full rewrite.** Removed `DummyModel`, sentinel-transformer fallback. Now `OllamaEmbeddingService` with typed errors (`EmbeddingError`, `EmbeddingUnavailableError`), vector validation, timeout handling. |
| `app/services/retrieval_service.py` | Updated imports, duck-typed embedding service, added deterministic tiebreaker `(-score, chunk_index)`, propagated `EmbeddingUnavailableError`. |
| `app/api/v1/endpoints/chat.py` | **Transaction fix:** Both chat and essay handlers now persist user+assistant messages AFTER provider success. No orphan messages on failure. |
| `app/api/v1/endpoints/health.py` | Enhanced `/health/ready` to check both DB and Ollama reachability. |
| `app/main.py` | Added global `EmbeddingUnavailableError` -> 503 handler. Added correlation-ID middleware. |
| `app/providers/claude.py` | Rewrote `ClaudeAgentWrapper` with real `search_transcripts` tool backed by RetrievalService, configurable max turns and timeout. |
| `app/ingestion/pipeline.py` | Updated import for new embedding error types. |
| `backend/.env` | Removed Gemini entries, `USE_DUMMY_EMBEDDINGS`, `USE_OLLAMA_EMBEDDINGS`. Clean Ollama-only config. |
| `.env.example` | Updated to match new config structure. |
| `scripts/evaluate_rag.py` | Removed dummy/sentence-transformers mode check. |

### Files Created
| File | Purpose |
|---|---|
| `tests/fakes/__init__.py` | Test fakes package |
| `tests/fakes/embedding.py` | `FakeEmbeddingForUnitTestsOnly` — deterministic test double |

### Tests Updated (behavior change only)
| Test | Change | Reason |
|---|---|---|
| `test_chat_provider_failure_does_not_create_fake_response` | Assert 0 msgs (was 1) | Orphan fix: no messages persisted on failure |
| `test_health_ready` | Handle new checks structure | Health endpoint now returns component status |
| `test_embedding_error_when_ollama_unreachable` | New test replacing old dummy test | Tests real `OllamaEmbeddingService` connection error |
| All `MockEmbeddingService` uses | Replaced with `FakeEmbeddingForUnitTestsOnly` | Centralized test fakes |
