# System Architecture: The Lenny Growth Assistant

## 1. System Architecture
A modern, decoupled web application.
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui.
- **Backend:** Python, FastAPI.
- **Database:** PostgreSQL.

## 2. Frontend/Backend Boundaries
- Frontend acts as a thin presentation layer, managing state and API communication.
- Backend handles business logic, agent orchestration, LLM API calls, RAG retrieval, and state persistence.
- REST/WebSocket APIs bridge the two.

## 3. Proposed Database Entities (PostgreSQL)
- `Session`: id, created_at, updated_at, title.
- `Message`: id, session_id, role (user/assistant), content, model_provider, created_at.
- `Artifact`: id, message_id, type (markdown/html), content, created_at.
- `Document` (for RAG context): id, content, metadata (episode, timestamp, etc.), embedding.

## 4. API Endpoint Plan
- `POST /api/chat`: Send a message and get a streaming response.
- `GET /api/sessions`: Retrieve chat history.
- `GET /api/sessions/{id}/messages`: Retrieve messages for a session.
- `GET /api/health`: Health checks.

## 5. Model-Provider Interface
A common adapter interface (`BaseProvider`) implementing `generate()`.
- `ClaudeProvider` (Anthropic API - `anthropic` package)
- `OllamaProvider` (Local Qwen3:4b via HTTP with `httpx`)
- `ProviderRouter` handles provider selection per request or falls back to `DEFAULT_LLM_PROVIDER`.
- Cloud APIs keys are strictly kept on the backend.

## 6. Agent Layer Integration
- **Framework:** Anthropic Claude Agent SDK.
- **Implementation Note:** Since there is no official Python SDK named exactly "Anthropic Claude Agent SDK" for generic workflows, we implemented an explicit `ClaudeAgentWrapper` class as a placeholder to document this blocker and prevent unrestricted tool use, keeping standard Claude model inference separate from agent execution.

## 7. Transcript Ingestion & Retrieval Flow
- Transcripts chunked and embedded using an embedding model.
- Stored in a vector database (or PostgreSQL with pgvector).
- On query: retrieve top-k chunks, inject into the prompt as context.

## 8. Session and Persistence Design
- Independent chat sessions stored in PostgreSQL.
- Each message references the generating model.

### Database Schema (Implemented in Phase 2)
- **ChatSession (`chat_sessions`)**:
    - `id` (UUID, primary key)
    - `title` (String, nullable)
    - `created_at` (DateTime, timezone-aware)
    - `updated_at` (DateTime, timezone-aware)
    - `metadata` (JSON, nullable)
- **Message (`messages`)**:
    - `id` (UUID, primary key)
    - `session_id` (UUID, foreign key to `chat_sessions.id`)
    - `role` (String, valid values: 'user', 'assistant', 'system')
    - `content` (Text)
    - `created_at` (DateTime, timezone-aware)
    - `metadata` (JSON, nullable)

### API Endpoints (Implemented in Phase 2)
- `GET /health/live`: Liveness probe.
- `GET /health/ready`: Readiness probe (checks DB connectivity).
- `POST /api/v1/sessions`: Create a new session.
- `GET /api/v1/sessions`: List sessions with pagination.
- `GET /api/v1/sessions/{id}`: Get a session by ID.
- `DELETE /api/v1/sessions/{id}`: Delete a session and its messages.
- `POST /api/v1/sessions/{id}/messages`: Add a message to a session.
- `GET /api/v1/sessions/{id}/messages`: List messages in a session.

### Transaction Strategy and Error Handling
- FastAPI dependency injection manages SQLAlchemy `AsyncSession` per request.
- Changes are committed explicitly via service functions, which can be safely rolled back on exceptions.
- Global FastAPI exception handlers return standard JSON error schemas without exposing tracebacks or DB details.
- UUID validation enforces 404 responses for invalid IDs instead of internal errors.

### Current Limitations (End of Phase 2)
- No user authentication or authorization.
- LLM Provider adapters not yet implemented.
- RAG retrieval not yet connected to conversation flow.

## 9. Artifact-Generation and Rendering Security
- Artifacts are identified by XML-like tags in the LLM response.
- Extracted and served to the frontend.
- Rendered in a sandboxed `<iframe>` with `sandbox="allow-scripts"` (if necessary, but highly restricted) to prevent XSS. Treat generated HTML as untrusted.

## 10. Logging, Resilience, and Error Handling
- Structured logging (JSON format).
- Fallback logic for LLM provider failures.
- Global exception handlers in FastAPI.

## 11. Local Development and Deployment Topology
- Local: Docker Compose orchestrating FastAPI, PostgreSQL, and Vite dev server. Ollama runs natively on the host to access GPU.
- Deployment: Free-tier friendly (e.g., Render or Fly.io for FastAPI, Vercel/Netlify for Frontend, Supabase/Neon for Postgres).
