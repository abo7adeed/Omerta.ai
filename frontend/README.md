# 💻 Omerta.ai — Banking & Financial Crime Forensic Frontend

<div align="center">

![Omerta.ai Frontend](https://img.shields.io/badge/Omerta.ai-Frontend_Interface-0A192F?style=for-the-badge&logo=react&logoColor=61DAFB)

**Enterprise-grade React 19 banking portal and compliance investigation interface for the Omerta.ai platform.**

[![React 19](https://img.shields.io/badge/React-19.2-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![TypeScript 5.5](https://img.shields.io/badge/TypeScript-5.5+-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Vite 8](https://img.shields.io/badge/Vite-8.3-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev)
[![Tailwind CSS 4](https://img.shields.io/badge/Tailwind_CSS-4.3-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![React Router 7](https://img.shields.io/badge/React_Router-7.18-CA4245?style=flat-square&logo=react-router&logoColor=white)](https://reactrouter.com)
[![Lucide Icons](https://img.shields.io/badge/Lucide-Icons-F59E0B?style=flat-square)](https://lucide.dev)

</div>

---

## 🌟 Overview

The **Omerta.ai Frontend** delivers a responsive single-page application (SPA) serving two primary user personas:
1. **Retail Banking Customers:** Account dashboard, multi-currency P2P transfers with dual-password authentication, step-up verification modals, and 2-way support chat.
2. **Compliance Officers & Fraud Investigators:** Real-time transaction risk scoring, multi-hop Neo4j fund flow visualization (`/network`), hardware device syndicate tracking (`/devices`), and identity verification queues (`/support-cases`).

---

## 🏗️ Architecture & Technology Stack

- **Core Framework:** [React 19](https://react.dev) with Concurrent Mode rendering.
- **Routing:** [React Router 7](https://reactrouter.com) with role-based route protection (`CUSTOMER`, `FRAUD_ANALYST`, `INVESTIGATOR`, `AUDITOR`, `ADMINISTRATOR`).
- **Styling:** [Tailwind CSS v4](https://tailwindcss.com) with custom glassmorphism design tokens, subtle gradients, and dark-mode optimization.
- **Charts & Visualization:** [Recharts](https://recharts.org) and custom interactive SVG vector engines for graph network topology.
- **Icons:** [Lucide React](https://lucide.dev) for consistent enterprise iconography.
- **Build Tool:** [Vite 8](https://vitejs.dev) with high-speed Hot Module Replacement (HMR).
- **Linter & Code Quality:** [Oxlint](https://oxc.rs) for lightning-fast Rust-based static code analysis.

---

## 📑 Application Views & Route Breakdown

### 👤 Customer Banking Portal
| Route | Description | Key Features |
|---|---|---|
| `/portal` | **Main Dashboard** | Active checking accounts, multi-currency balances (EGP, USD, EUR, GBP), rapid action shortcuts, recent ledger entries. |
| `/portal/transfers` | **P2P Transfer Hub** | Recipient account autocomplete, currency converter, transfer password authorization, 3-strikes hold detection, step-up confirmation modal. |
| `/portal/support` | **Support & Identity Desk** | WhatsApp-style timeline chat with compliance staff, National ID card attachment uploader, live resolution badges. |

### 🛡️ Compliance & Forensic Command Center
| Route | Description | Key Features |
|---|---|---|
| `/network` | **Entity & Fund Flow Graph** | Real-time interactive SVG network graph. Traces itemized fund inflows (*"From where got money"*) and outflows (*"Where money went"*), highlights pass-through conduits, and clusters co-located hardware. |
| `/devices` | **Device Intelligence** | Hardware fingerprint inspector, multi-account co-location counters (1 account = LOW, 2 accounts = HIGH, $\ge 3$ accounts = CRITICAL syndicate), linked accounts drawer. |
| `/support-cases` | **Staff Triage Hub** | Officer inbox for tickets and account freezes, side-by-side National ID card inspector, one-click transfer permission restoration. |
| `/admin/review` | **Transaction Risk Hub** | Live transaction scoring stream, LightGBM feature attribution breakdown, LangGraph multi-agent SAR consensus logs. |

### 🔐 Authentication Suite
| Route | Description |
|---|---|
| `/login` | Dual-purpose login (Customer / Staff) with active session enforcement. |
| `/register` | Onboarding with separate login password, transfer password, and National ID. |
| `/forgot-password` | SMTP-backed password reset request interface. |
| `/reset-password` | Cryptographic JWT token-based password reset form. |

---

## 🔐 Frontend Security Features

1. **Dual-Password UX Segregation:**
   - Account login and transaction authorization are strictly separated.
   - The transfer interface explicitly prompts for the high-security **Transfer Password**.
   - Handles the **3-Strikes Non-Logout Rule**: Strike 1 gives a warning, Strike 2 escalates, Strike 3 locks outbound transfers without terminating the user's active portal session.

2. **Step-Up Confirmation Token Handling:**
   - For flagged or high-risk transfers, the UI prompts for single-use SHA-256 confirmation tokens (`/api/v1/transactions/{id}/customer-confirmation`).

3. **Role-Based Access Control (RBAC):**
   - Route guards automatically prevent customer accounts from accessing `/admin/*`, `/network`, `/devices`, and `/support-cases`.
   - Read-only restrictions enforced for `AUDITOR` personas.

4. **Session Integrity:**
   - JWT stored in authenticated client storage with automatic 401 interceptors redirecting expired sessions.

---

## 🚀 Getting Started

### 1. Prerequisites
- **Node.js 20+**
- **npm 10+**
- Running Omerta.ai FastAPI backend at `http://localhost:8000`

### 2. Installation
```bash
# From the frontend directory
npm install
```

### 3. Development Server
```bash
npm run dev
```
The application will launch at `http://localhost:5173`. API requests to `/api/v1/*` are automatically proxied to `http://localhost:8000`.

### 4. Production Build
```bash
# Typecheck and build optimized bundle
npm run build

# Preview production build locally
npm run preview
```

### 5. Linting
```bash
npm run lint
```

---

<div align="center">

*Omerta.ai Frontend &copy; 2026. Built for secure, resilient financial intelligence.*

</div>
