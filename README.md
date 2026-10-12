# The Lenny Growth Assistant

A conversational assistant grounded in Lenny's Podcast transcripts, providing actionable growth insights, retrieval-augmented generation (RAG) with source citations, and artifact generation.

## Project Overview
This application features a minimalist, dark-themed UI with a selectable model provider routing system supporting Claude and local Ollama.

## Documentation
- [Product Requirements (PRD)](docs/PRD.md)
- [Design Specification](docs/design.md)
- [System Architecture](docs/architecture.md)

## Prerequisites
- Docker and Docker Compose
- Node.js (v20+)
- Python (3.11+)
- Ollama (installed locally with `qwen3:4b` model for local inference)

## Proposed Setup & Local Development
1. Clone the repository.
2. Copy `.env.example` to `.env` and fill in necessary keys. **Never commit actual API keys.**
3. Start the database using Docker Compose:
   ```bash
   docker compose up -d db
   ```
4. Set up the Python environment and install dependencies:
   ```bash
   cd backend
   python -m venv venv
   # On Windows: .\venv\Scripts\activate
   # On macOS/Linux: source venv/bin/activate
   pip install -r requirements.txt
   ```
5. Run the database migrations:
   ```bash
   alembic upgrade head
   ```
6. Start the FastAPI backend server locally:
   ```bash
   fastapi dev app/main.py
   ```
   The API will be available at http://127.0.0.1:8000 and the interactive Swagger documentation at http://127.0.0.1:8000/docs.

7. Start the Frontend Vite server:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   The React UI will be available at http://localhost:5173.

## Usage Guide
### Chatting & Provider Selection
Use the chat interface to ask questions. You can swap between Ollama and Claude dynamically using the provider dropdown in the top right.

### The "Ship 30 for 30" Essay Skill
You can leverage the dedicated "Ship 30 for 30" writing skill directly from the chat UI by typing `/essay` followed by your topic.
**Example**: `/essay Product-Led Growth for early stage startups`

The assistant will synthesize retrieved transcripts, enforce a 1,250-word length constraint, provide actionable takeaways, and return the response wrapped in a UI Artifact for reading and copying.

## Testing
To run the automated tests against an isolated SQLite memory database:
```bash
cd backend
pytest
```

## Troubleshooting
- If the database refuses connections, ensure Docker is running and the `postgres_data` volume hasn't corrupted. To reset the DB, run `docker compose down -v` (WARNING: This destroys all data).
- If FastAPI complains about missing modules, verify your virtual environment is activated and `pip install -r requirements.txt` ran successfully.

## Development Phases
- [x] **Phase 1:** Project Foundation & Documentation (Implemented)
- [x] **Phase 2:** Backend API & Database (Implemented)
- [ ] **Phase 3:** Frontend UI Scaffolding (Planned)
- [ ] **Phase 4:** Agent Layer & Artifact Viewer (Planned)
- [ ] **Phase 5:** Polish & Deployment (Planned)

## Testing Strategy
- **Backend:** `pytest` for unit and integration tests.
- **Frontend:** `vitest` and React Testing Library.

## Features (Planned & Implemented)
- [x] Selectable LLM providers (Claude, Ollama)
- [x] Agent Layer integration (Claude Agent / SDK via explicit wrapper)
- [ ] RAG pipeline for transcript citations
- [ ] In-app Artifact Viewer
- [ ] Ship 30 for 30 essay generation skill

## Configuration and Secrets
To configure providers, edit your `.env` file (never commit this file!).
- **Claude**: Obtain an API key from Anthropic Console. Set `ANTHROPIC_API_KEY`.
- **Ollama**: Download and install Ollama locally. Run `ollama run qwen3:4b` to pull the local model. Ensure `OLLAMA_BASE_URL` is correct.

You can select the provider at runtime per request, or rely on `DEFAULT_LLM_PROVIDER`.

## Privacy Notice
Cloud providers (Anthropic) receive the prompts and conversation data sent to them. Local inference (Ollama) keeps data locally, but does not automatically guarantee privacy for other parts of the application (e.g. if the UI sends analytics, though none are currently implemented). Keep API keys safely on the backend and do not expose them to the frontend.

## Testing
To run tests:
```bash
cd backend
python -m pytest
```
Integration tests against real providers can be implemented using explicit markers and environment variables (currently mocked to avoid charges).
