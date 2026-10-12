# Frontend Compliance Report: The Lenny Growth Assistant

## 1. Required User Experience
**Status:** VERIFIED
- **Conversational Interface:** The UI provides a full chat experience with proper loading states (Spinners, Skeletons), empty states ("How can I help you grow?"), and error handling (shadcn/ui Toasts).
- **Independent Sessions:** Implemented via a sidebar list. Changing sessions updates the message view correctly without context leakage.
- **Provider Selection:** A dropdown allows toggling between `ollama` and `claude`, which is correctly passed to the backend API.
- **Citations:** Source metadata is displayed via interactive tooltips `[1] Podcast Transcript` below assistant messages that contain citations.
- **Empty Retrieval:** When `citations` is empty for an assistant message, the UI displays a clear "No transcript evidence found" warning.
- **Essay Generation:** Typing `/essay [topic]` dynamically intercepts the request and calls the backend `/essay` endpoint.
- **Artifact Viewer:** A side-by-side artifact panel safely renders both `markdown` (via `react-markdown`) and `html` (via a strictly sandboxed iframe + `DOMPurify`).
- **Accessibility:** Uses accessible primitives from Radix UI (shadcn) and supports keyboard-only submission (Enter to send).

## 2. Frontend–Backend Contract
**Status:** VERIFIED
- **API Setup:** The frontend uses `axios` and expects the backend at `import.meta.env.VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`).
- **Session API:** `/sessions` and `/sessions/{id}/messages` correctly map to typed interfaces.
- **Provider Routing:** The `provider` state is explicitly sent in `ChatRequest` and `EssayRequest`.
- **Artifact Contract:** 
  - **UPDATED:** Added an explicit `Artifact` schema to `ChatResponse` matching the updated backend schema. 
  - The UI now checks for `response.artifact` directly. If absent, it gracefully falls back to inline string parsing (`<artifact>...`).
  - No dedicated artifact endpoint was invented; it respects the assignment constraint.
- **Error Handling:** Backend HTTP 404s, 503s, and 422s are caught and surfaced natively in the Toast notifications using the backend's `detail` message string.
- **Secrets:** No API keys or secrets are exposed in the frontend codebase.

## 3. Tests and Quality
**Status:** VERIFIED
- **Build:** `npm run build` (tsc typecheck + vite build) completes successfully with no TypeScript compilation errors.
- **Tests:** `npx vitest run` executes 3 tests checking message submission, provider selection, and citation rendering. All tests pass.
- **Linting:** No unresolved linting errors blocking the build.

## 4. Manual Validation Steps
1. `npm run dev` to start the Vite server.
2. Verify the session list loads (calls `GET /sessions`).
3. Click "New Chat" and verify session creation.
4. Select "Ollama" from the dropdown and type a question. Verify loading spinner appears and message is sent to `POST /sessions/{id}/chat`.
5. Hover over the resulting citation tags to verify source text tooltips.
6. Type `/essay Product-Led Growth`. Verify it hits `POST /sessions/{id}/essay` and opens the Artifact Panel.
7. Disconnect the backend and verify the Toaster displays "Could not connect to the backend."

## 5. Security and Architecture
- **XSS Prevention:** HTML artifacts are sanitized using `DOMPurify.sanitize()` before being injected into an `iframe`.
- **Sandboxing:** The iframe uses `sandbox=""`, which disables scripts, form submission, and same-origin access, enforcing a strict boundary for generated HTML.
- **Styling:** Retained `TailwindCSS` and `shadcn/ui`.

## Remaining Blockers
- **None.** The frontend is fully compliant with the assignment requirements and properly integrated with the backend contract.
