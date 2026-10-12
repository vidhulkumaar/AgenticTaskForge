# Design Specification: The Lenny Growth Assistant

## 1. Visual Direction
Inspired by a minimalist chat interface, uniquely branded as The Lenny Growth Assistant. The interface is clean, focusing on content and usability without visual clutter, proprietary branding, or generic aesthetics.

## 2. Color Palette & Typography
- **Background:** Near-black (`#0a0a0a`).
- **Accents:** Subtle navy-blue glow (`#1e3a8a` with low opacity) around the central welcome area.
- **Text:** High contrast white/off-white (`#f8fafc`) for primary text, muted gray (`#94a3b8`) for secondary text.
- **Typography:** Clean, modern sans-serif (e.g., Inter or Roboto). Restrained spacing.

## 3. Navigation & Information Architecture
- **Slim Vertical Navigation Rail (Left):** Simple, consistent outline icons for New Chat, History, Settings, and Help.
- **Main Content Area:** Centered welcome heading on the initial screen. Natural chat flow once started.

## 4. Chat Composer & Model Selector
- **Composer:** Rounded prompt input box at the bottom, featuring attachment (paperclip) and send (arrow) icons.
- **Model Selector:** A discrete dropdown or segmented control supporting Claude and Ollama, positioned cleanly.

## 5. Chat History & Session Interactions
- Saved sessions accessible via the left navigation rail.
- Chat messages displayed naturally top-to-bottom after the first user message.

## 6. Artifact Viewer
- Side-by-side display on wide screens (desktop).
- Stacked or tabbed layout on narrow screens (mobile/tablet).
- Renders generated Markdown or HTML/CSS.

## 7. Responsive Layouts
- **Desktop:** Sidebar + Chat + Artifact Viewer (side-by-side).
- **Tablet:** Collapsible Sidebar + Chat (Artifact Viewer in a tab/overlay).
- **Mobile:** Bottom navigation or hamburger menu + Chat (Artifact Viewer in a full-screen modal or tab).

## 8. Application States
- **Initial State:** Centered welcome heading with the subtle navy-blue glow.
- **Active Conversation:** Chat bubbles with citations.
- **Loading State:** Skeleton loaders or subtle pulsing indicators.
- **Empty State:** Helpful prompt suggestions.
- **Error/Model Failure:** Graceful inline error messages with retry options.
- **Artifact Preview:** Split view with rendering constraints.

## 9. Accessibility & Security
- ARIA labels on all icons and controls.
- Keyboard navigable.
- Secure artifact rendering using iframe sandboxing or sanitization to isolate untrusted HTML/CSS.
