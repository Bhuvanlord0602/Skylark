# 📊 Skylark Drones — Monday.com Executive BI Agent (Groq + Qwen)

[![Tests: 59 passed](https://img.shields.io/badge/Tests-59%20passed-brightgreen.svg)](#-automated-testing)
[![LLM: Groq Qwen](https://img.shields.io/badge/LLM-Groq%20Qwen-orange.svg)](#-groq--qwen-architecture)
[![Monday.com: Strictly Read-Only](https://img.shields.io/badge/Monday.com-Strictly%20Read--Only-blue.svg)](#-security--read-only-guarantees)
[![Caching: Redis + In-Memory](https://img.shields.io/badge/Caching-Redis%20%2B%20In--Memory-red.svg)](#-multi-tier-caching--background-refresh)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://python.org)
[![UI Theme: High-Contrast Dark & Light](https://img.shields.io/badge/UI%20Theme-Dark%20%26%20Light%20Mode-blueviolet.svg)](#-frontend-features)

An enterprise-grade Conversational Business Intelligence Agent built for founders, executives, and leadership teams. The platform dynamically retrieves, normalizes, caches, and analyzes live data from Monday.com **Deals** (sales pipeline) and **Work Orders** (project execution, billing, and cash collection) boards, powered by **Groq API + Qwen model** with deterministic Python calculations, interactive Plotly visualizations, multi-turn conversation memory, and strategic leadership briefs.

---

## 🏛️ System Architecture

```
                    USER
                      │
                      ▼
             STREAMLIT CHAT UI (:8501)
                      │
                      ▼
            FASTAPI BACKEND (:8000)
                      │
                      ▼
             BI AGENT (app/agent.py)
                      │
                      ▼
        GROQ API (OpenAI-compatible SDK)
                      │
                      ▼
                  QWEN MODEL
                      │
               TOOL SELECTION
                      │
                      ▼
          TOOL REGISTRY (app/tools/registry.py)
                  /       \
                 ▼         ▼
            DEALS       WORK ORDERS
                 \         /
                  ▼       ▼
               MONDAY.COM API v2
            (Strictly Read-Only GraphQL)
                      │
                      ▼
               LIVE BOARD DATA
                      │
                      ▼
            DATA NORMALIZATION & CLEANING
                      │
                      ▼
         DETERMINISTIC PYTHON ANALYTICS
                  /        \
                 ▼          ▼
         VISUALIZATIONS   INSIGHTS
                  \        /
                   ▼      ▼
              EXECUTIVE ANSWER
```

---

## ⚡ Key Highlights

1. **Groq + Qwen Intelligence Engine (`app/llm_client.py`, `app/agent.py`):**
   - Direct integration with Groq API via standard OpenAI SDK client (`base_url="https://api.groq.com/openai/v1"`).
   - Multi-round tool calling loop (`MAX_TOOL_ROUNDS=8`) with explicit allowlist registry (`app/tools/registry.py`).
   - Clean separation of concerns: Qwen selects tools and interprets business context; Python deterministically computes all pipeline and operations metrics.
   - Resilient zero-hallucination fallback when offline or during unconfigured test runs.

2. **Strictly Read-Only Monday.com Integration (`app/tools/monday_client.py`):**
   - Live dynamic cursor-pagination over Deals (`5030842959`) and Work Orders (`5030843495`).
   - Mutation blocker permanently rejecting any `create_item`, `change_column_value`, etc. with `PermissionError`.
   - Concurrent board extraction (`asyncio.gather`) with persistent connection pooling (`httpx.Limits`).

3. **Multi-Tier Caching & Background Refresh (`app/cache.py`, `app/tasks.py`):**
   - Redis snapshots + in-memory dictionary fallback with configurable 5-minute TTL (`CACHE_TTL_SECONDS=300`).
   - Scheduled Celery Beat / in-process FastAPI `lifespan` periodic polling.
   - On-demand `POST /refresh` manual trigger from UI.

4. **Multi-Turn Conversation Memory (`app/memory.py`):**
   - Session tracking (`session:{id}:history`) maintaining a 20-turn sliding window with 24-hour TTL.

5. **Track A Executive Frontend (`ui/streamlit_app.py`):**
   - High-contrast Dark & Light mode theme.
   - 4 Tabs: Executive Dashboard, Executive Chat, Leadership Brief, and Data Quality & Provenance Audit.
   - Auto-rendered Plotly charts with unique key isolation preventing duplicate element IDs.

---

## 🛠️ Environment Configuration (`.env`)

```ini
# ==========================================
# GROQ / QWEN
# ==========================================
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.6-27b

# ==========================================
# MONDAY.COM
# ==========================================
MONDAY_API_TOKEN=your_monday_api_token_here
MONDAY_DEALS_BOARD_ID=5030842959
MONDAY_WORK_ORDERS_BOARD_ID=5030843495

# ==========================================
# SERVER & CACHING
# ==========================================
HOST=0.0.0.0
PORT=8000
BACKEND_URL=http://localhost:8000
ENVIRONMENT=production
LOG_LEVEL=info

REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=300
SESSION_TTL_SECONDS=86400
```

---

## 🚀 Quick Start (Native Local Execution)

### 1. Activate Environment & Start Backend (Terminal 1)
```powershell
cd "C:\Users\RVU\Downloads\FULL STACK"
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --port 8000 --host 0.0.0.0
```

### 2. Start Frontend UI (Terminal 2)
```powershell
cd "C:\Users\RVU\Downloads\FULL STACK"
.venv\Scripts\Activate.ps1
python -m streamlit run ui/streamlit_app.py --server.port 8501
```

- **Frontend Dashboard:** [http://localhost:8501](http://localhost:8501)
- **FastAPI OpenAPI Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Endpoint:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 🐳 Docker Compose Execution

```powershell
docker compose up --build
```
Spins up all 5 services: `redis`, `celery-worker`, `celery-beat`, `backend`, and `ui`.

---

## 🧪 Automated Testing & Diagnostic Scripts

### 1. Run Complete Automated Test Suite (59 Tests Passing)
```powershell
python -m pytest tests/ -v
```

### 2. Test Groq Connection
```powershell
python scripts/test_groq.py
# Expected output: Groq connection successful
```

### 3. Test Tool Calling Workflow
```powershell
python scripts/test_tool_calling.py
# Expected output: [OK] Qwen requested tool: get_test_value -> The test value is 42.
```

### 4. Test Live Monday.com Ingestion
```powershell
python scripts/test_monday_connection.py
# Verifies Deals Board, Work Orders Board, schema introspection, and read-only mutation guard.
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root service metadata, caching status, and Groq model info |
| `GET` | `/health` | Live board connectivity, item counts, and LLM status |
| `POST` | `/chat` | Conversational BI endpoint with session memory & tool execution |
| `POST` | `/refresh` | On-demand background cache refresh trigger |
| `GET` | `/schema` | Dynamic column mappings & confidence metadata |
| `GET` | `/data-quality` | 4-part data quality audit & cross-board match stats |
| `POST` | `/leadership-summary` | Generates 8-section strategic leadership briefing |
| `GET` | `/cache/status` | Real-time cache hit/miss statistics |
| `POST` | `/cache/clear` | Flushes all cached board and metric keys |

---

## 🔒 Security & Privacy Guarantees

1. **Strictly Read-Only Access:** No GraphQL mutations (`create_item`, `change_column_value`, `delete_item`) can ever be dispatched.
2. **Credential Isolation:** API keys are never exposed over API responses or client-side bundles; `.env` is ignored by Git.
3. **Deterministic Calculations:** Financial metrics, pipeline aggregates, and conversion rates are 100% computed in Python, never hallucinated by the LLM.
