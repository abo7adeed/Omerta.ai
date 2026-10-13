# 🛡️ Omerta.ai — Graduation Defense Presentation

An interactive, responsive presentation for the **NTI Graduation Project: Omerta.ai (Autonomous Financial Crime Investigation & Banking Platform)**, packaged into **one single self-contained HTML file**.

---

## 🚀 Quickstart (How to Run)

The entire presentation is 100% self-contained in [`index.html`](file:///e:/Ai-projects/NTI_Graduation_Project/omerta-final/Omerta.ai/presentation/index.html) with zero external stylesheet or script dependencies:

1. **Direct Double-Click:** Double-click `index.html` in your file explorer to open it immediately in any web browser (Chrome, Edge, Firefox, Safari).
2. **Local Web Server (Optional):**
   ```bash
   cd presentation
   python -m http.server 3000
   ```
   Then open `http://localhost:3000` in your web browser.

---

## 📱 Universal Screen Responsiveness (All Formats Supported)

The presentation features a **Universal Responsive Engine** that automatically adapts dynamically across every screen size:

- **🖥️ 4K & Ultra-Wide Displays (2560px+)**: High-resolution scaling, crisp typography, and spacious layouts.
- **💻 Laptops & Desktop Monitors (1920×1080, 1440×900, 1366×768)**: Fluid multi-column cards, interactive simulators, and crisp vector diagrams.
- **📱 Tablets & iPads (768px – 1199px)**: Automatic 2-column wrapping, responsive touch sliders, and adaptive canvas scaling.
- **📲 Mobile Phones (360px – 767px)**: Vertical single-column stacking with smooth internal slide scrolling (`overflow-y: auto`), compact touch navigation controls, and fluid font sizing (`clamp`).
- **📽️ Projectors (4:3, 16:9, 16:10)**: Automatically scales to the projector's native aspect ratio.

---

## ⌨️ Keyboard & Touch Shortcuts

| Input | Action | Description |
|---|---|---|
| **`→` / `Space` / `PgDn` / Swipe Left** | **Next Slide** | Advances to the next slide with smooth transitions |
| **`←` / `PgUp` / Swipe Right** | **Previous Slide** | Moves back to the previous slide |
| **`Home` / `End`** | **Start / Finish** | Jumps directly to Slide 1 or Slide 20 |
| **`F`** | **Fullscreen** | Toggles full-screen presentation mode |
| **`O`** | **Overview Grid** | Opens visual thumbnail grid to jump directly to any slide |
| **`N`** | **Speaker Notes** | Toggles speaker defense notes drawer for rehearsal |
| **`P`** | **Autoplay** | Toggles 7-second automatic slideshow rotation |
| **`M`** | **Sound Effects** | Mutes / Unmutes synthesized Web Audio API sound effects |
| **`T`** | **Theme Toggle** | Toggles between Executive Light (Ivory & Sapphire) and Dark mode |

---

## 📑 Slide Deck Inventory (20 Detailed Slides)

1. **Slide 1 — Hero & Title Showcase:** NTI Graduation Project banner, glowing shield, tech badges (FastAPI, React 19, PostgreSQL 17, Neo4j, LangGraph, LightGBM, MCP).
2. **Slide 2 — The $2T Problem & AML Crisis:** Global illicit flows, 95% false positives, 48hr triage latency, Legacy TMS vs. Omerta.ai.
3. **Slide 3 — 5-Tier Canonical Architecture:** Client Tier, FastAPI Gateway, Multi-Agent Tier, MCP Layer, Dual-Persistence Tier.
4. **Slide 4 — Core Banking Engine & Double-Entry Ledger:** Accounting balance invariant $\Delta Debit + \Delta Credit = 0$, row-level lock concurrency `SELECT ... FOR UPDATE`, live interactive transfer balance simulator.
5. **Slide 5 — Dual Passwords & 3-Strikes Non-Logout Hold:** Separation of login vs. transfer passwords, Strike 1 warning, Strike 2 alert, Strike 3 transfer freeze, non-logout session preservation, interactive strike tester.
6. **Slide 6 — Customer Support & Identity Restoration:** 4-phase lifecycle, WhatsApp-style chat, Egyptian National ID card upload, compliance officer triage, dedicated restoration API invariant.
7. **Slide 7 — Interactive Multi-Hop Graph Topology (`/network`):** Real-time SVG network visualizer, inbound feeder sources, outbound cashout mules, pass-through conduit detection (ratio > 0.65), shared hardware nodes, clickable entity inspector.
8. **Slide 8 — Device Intelligence & Localhost Co-Location (`/devices`):** Hardware fingerprints, loopback/user-agent binding, interactive risk escalator (1 account LOW, 2 accounts HIGH hopping warning, 3+ accounts CRITICAL syndicate ring).
9. **Slide 9 — Supervised ML Risk Engine (LightGBM):** Phase 14 classifier, 13 features (`features-v1`), 15,000 train samples, 0.9979 ROC-AUC, 0.9886 PR-AUC, 94.3% precision, 98.3% recall, animated radial SVG gauges.
10. **Slide 10 — Multi-Agent LangGraph Forensic Consensus:** 9 specialized sub-agents (Banking Rules, Behavioral, ATO, Device/Network, Graph Intelligence, ML Risk, Merchant Intelligence, Identity/Security, Final Decision), interactive consensus runner.
11. **Slide 11 — Model Context Protocol (MCP) Tool Architecture:** 4 sandboxed read-only MCP servers (Transaction, Graph, Risk, Knowledge), strict Pydantic schemas, zero-write invariant.
12. **Slide 12 — Agentic RAG Cognitive Copilot:** 13 natural language query intents, zero-mock Matplotlib visualizer, non-accusatory guardrails, collapsible 7-stage forensic trace.
13. **Slide 13 — Cryptographic Evidence Grounding & Regulatory SAR:** Subset invariant $\text{Finding}.\text{evidence\_ids} \subseteq \text{CollectedFacts}.\text{evidence\_ids}$, deterministic SHA-256 content hashing, live interactive hasher demo.
14. **Slide 14 — Enterprise RBAC & Persona Matrix:** Administrator, Fraud Analyst, Senior Investigator, Auditor, and Customer profiles with pre-seeded credentials and balances.
15. **Slide 15 — Showcase Case Studies & Scenarios:** Side-by-side comparison of clean retail transactions (TXN-LEGIT-101) vs. smurfing structuring (TXN-RISK-501), hardware syndicates (TXN-RISK-502), and rapid ATO drain (TXN-RISK-503).
16. **Slide 16 — Frontend Engineering & UI/UX Design System:** React 19, TypeScript 5.5, Tailwind CSS, Lucide icons, dark-mode glassmorphism, 26+ bespoke application views.
17. **Slide 17 — Quality Assurance & Verification Suite:** Pytest test suites, double-entry balance verification, pessimistic locking race condition tests, 100% test pass rate.
18. **Slide 18 — Step-by-Step GitHub Pull & Quickstart Run Guide:** 6-step reproduction commands, Docker Compose, uv, alembic, seed scripts, and live service links.
19. **Slide 19 — Strategic Roadmap & Future Horizons:** Completed Phases 1-17, sub-50ms WebSockets, cross-border corridors, blockchain crypto tracing, automated regulatory XML filings.
20. **Slide 20 — Graduation Defense Conclusion & Live Demo Hub:** Summary of accomplishments, launchpad buttons to the live Banking Portal (`:5173`) and Swagger Docs (`:8000/docs`).
