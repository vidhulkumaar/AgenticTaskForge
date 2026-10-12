# Product Requirements Document (PRD): The Lenny Growth Assistant

## 1. Product Overview
The Lenny Growth Assistant is a conversational AI application grounded in Lenny's Podcast transcripts. It provides domain-specific, retrieval-augmented generation (RAG) with source citations, featuring an agent layer and a dedicated essay-generation skill. 

## 2. Primary Users and User Problems
- **Primary Users:** Product managers, founders, engineers, and marketers seeking growth insights.
- **User Problems:** Discovering actionable growth insights from long-form podcast content is time-consuming and difficult to synthesize. Users need quick, authoritative answers with citations.

## 3. User Journeys
- **Inquiry:** A user asks a specific question about product growth. The system retrieves relevant transcript segments and generates a cited answer.
- **Essay Generation:** A user triggers the Ship 30 for 30 essay generation skill to produce a ~1,250-word synthesis of growth strategies.
- **Artifact Interaction:** The user views generated HTML/CSS or markdown artifacts in the side-by-side Artifact Viewer.

## 4. Measurable Success Metrics
- Response accuracy and relevance based on transcript context.
- System latency (Time to First Token).
- Successful artifact rendering without security vulnerabilities.
- Multi-provider fallback success rate.

## 5. Functional Requirements
- Conversational RAG interface with source citations.
- Selectable model providers (Anthropic Claude, Local Ollama with Qwen3:4b).
- Agent layer using the Anthropic Claude Agent SDK.
- Essay-generation skill (~1,250 words, Ship 30 for 30 style).
- Markdown and HTML/CSS artifact generation and side-by-side display.
- PostgreSQL-based independent chat session persistence.
- Secure artifact rendering.

## 6. Non-Functional Requirements
- API validation, structured logging, health checks, error handling.
- Automated tests for core logic.
- Reproducible local startup via Docker Compose.
- Free-tier-friendly hosting architecture.
- Modular code to support provider switching.

## 7. Assumptions
- Podcast transcripts are available and ingestible.
- Users have local resources for Ollama (Qwen3:4b) or valid API keys for cloud providers.

## 8. Included and Excluded Scope
- **Included:** Chat interface, RAG pipeline, 3 model integrations, agent layer, artifact viewer, DB persistence.
- **Excluded:** User authentication (for Phase 1/MVP), live transcription, mobile app (PWA only).

## 9. Risks and Trade-offs
- **Risk:** Local LLM (Ollama) performance varies by user hardware.
- **Trade-off:** Minimal UI vs. deep feature set; prioritizing a polished chat over complex settings.

## 10. Acceptance Criteria
- RAG pipeline answers questions with citations.
- Users can switch between Claude and Ollama.
- Artifacts render securely beside the chat.
- Conversations persist in PostgreSQL.
- App starts cleanly via `docker-compose up`.

## 11. Phased Implementation Plan
- **Phase 1:** Project foundation and documentation.
- **Phase 2:** Backend API, database setup, and basic RAG pipeline.
- **Phase 3:** Frontend UI scaffolding and chat integration.
- **Phase 4:** Agent layer, artifact viewer, and essay skill.
- **Phase 5:** Polish, deployment, and testing.
