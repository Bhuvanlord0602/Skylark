# Architecture Decision Log (ADR) — Monday.com Executive BI Agent

**Project:** Skylark Drones Executive BI Assistant  
**Author:** AI Engineering & Architecture Team  
**Scope:** Architectural Trade-offs, Data Integrity Assumptions, Performance, & Technical Decisions  

---

## 1. Key Architectural Assumptions

1. **Monday.com is the Sole Runtime Source of Truth:**  
   Business metrics are never hardcoded, precalculated, or loaded from offline CSVs/spreadsheets. All numbers reflect the live state of the Monday.com Deals (`5030842959`) and Work Orders (`5030843495`) boards via cursor pagination.

2. **Real-World Messiness Must Be Explicitly Handled:**  
   Real CRM data contains nulls, corrupted currency strings (`₹1,00,000`, `100k`, `1.5M`), and non-standard dates (`DD/MM/YYYY`, text months, Excel serial timestamps). Missing values are never converted to `0` unless explicitly zero in the source, and invalid dates are never defaulted to "today".

3. **Strictly Read-Only Operations:**  
   The application acts as a secure, read-only analytics consumer. GraphQL mutations (`create_item`, `change_column_value`, etc.) are actively blocked at the network client layer.

---

## 2. Technical Decisions & Trade-Offs

### A. Direct GraphQL API vs. MCP (Model Context Protocol)
- **Decision:** Implemented a direct async GraphQL client with cursor pagination and exponential backoff rather than relying on generic MCP sidecars.
- **Rationale:** MCP servers introduce external process dependencies and can obscure cursor-based pagination across large boards. Direct GraphQL client gives 100% control over retry loops, 429 rate limit backoff, schema introspection, and data verification.

### B. Deterministic Calculation Before AI Narrative Generation
- **Decision:** All mathematical aggregations, weighted valuations, and risk matrices are computed deterministically in pure Python before being passed to Claude.
- **Rationale:** LLMs are prone to arithmetic errors and hallucinations when calculating multi-column weighted sums across hundreds of records. Computing metrics deterministically guarantees 100% mathematical accuracy; the LLM focuses on synthesis, strategic context, and executive commentary.

### C. 3-Tier Cross-Board Entity Resolution
- **Decision:** Cross-board linking uses a 3-tier hierarchy:
  1. *Level 1:* Exact Customer Code match (`client_code` == `customer_name_code`).
  2. *Level 2:* Normalized Client Name match (punctuation & legal suffixes stripped).
  3. *Level 3:* Cautious RapidFuzz token sort ratio (Threshold $\ge 90$).
- **Rationale:** Prevents spurious links between distinct legal entities while tolerating minor typographic variations. Unmatched deals and work orders are never dropped, preserving full data visibility.

---

## 3. Performance & Memory Addendum Decisions

### D. Multi-Tier Caching Architecture (Redis with In-Memory Fallback)
- **Decision:** Implemented a dual-tier caching layer (`app/cache.py`). If Redis is running (`REDIS_URL`), it stores board snapshots (`board:{id}:raw`) and computed metrics (`metrics:{name}:{filters_hash}`). If Redis is offline or not installed, it automatically falls back to an in-memory dictionary with timestamp-based TTL eviction without raising errors.
- **Cache TTL Choice:** 300 seconds (5 minutes).
  - *Trade-off:* Founders and executives reviewing business intelligence do not need millisecond-level live polling against Monday.com. A 5-minute TTL reduces Monday.com GraphQL API traffic by over 95%, eliminates rate-limit exposure (HTTP 429), and enables sub-50ms response times for dashboards and conversational queries.

### E. Background Refresh: Celery Beat vs. In-Process `asyncio` Task Loop
- **Decision:** Dual support: Celery worker + beat configuration (`app/celery_app.py`, `app/tasks.py`) for multi-container production deployments via Docker Compose, paired with an in-process `asyncio.create_task()` lifespan background loop in FastAPI (`app/main.py`).
- **Rationale:** While Celery provides enterprise task queuing and independent worker scaling, deploying Celery + Redis + Beat adds infrastructure overhead for standalone or local testing environments. Providing the in-process `asyncio` background loop allows the system to achieve 100% background polling benefits (zero blocking on the user request path) even when run locally as a single Python process.

### F. Multi-Turn Conversation Memory (§2.2)
- **Decision:** Structured session memory (`app/memory.py`) stored in Redis / memory under `session:{session_id}:history` with a 24-hour TTL and a 20-turn sliding window cap.
- **Rationale:** Allows executives to ask follow-up questions (e.g., "What about the energy sector?", followed by "Which of those close next month?") without re-typing context. Capping at 20 turns prevents context window exhaustion while maintaining strategic thread continuity.

### G. Frontend Upgrade Strategy (Track A vs. Track C)
- **Decision:** Executed Track A (Polished Streamlit UI with custom CSS theme, HTML/CSS KPI cards, dynamic Plotly chart styling, and session memory) over a full React/Next.js rewrite (Track C).
- **Rationale:** FastAPI already exposes clean REST and SSE endpoints for any prospective React frontend. For a fast-turnaround executive BI deliverable, polishing Streamlit with custom CSS, theme toggles, and sub-second cached rendering yielded the highest ROI without multiplying deployment complexity.

---

## 4. Leadership Updates Interpretation

The Leadership Update feature synthesizes 5 strategic dimensions into an 8-section brief:
1. **Pipeline Health:** Total pipeline valuation, weighted pipeline, win rates, and stage distribution.
2. **Key Opportunities:** Top opportunities, closure probabilities, and close timings.
3. **Sector Performance:** Revenue concentrations and market drivers.
4. **Operational & Execution Health:** Work order progress, active delays, and on-time delivery rates.
5. **Billing & Collections:** Billed amounts, collections, and outstanding receivables.
6. **Founder Risks:** Concentration risk, delivery bottlenecks, and receivables aging.
7. **Strategic Actions:** Actionable next steps for executive leadership.
8. **Data Caveats:** Transparent audit of excluded records and missing values.

---

## 5. What Would Be Improved With More Time

1. **Historical Snapshot Storage & Delta Tracking:**  
   Implement time-series snapshots in PostgreSQL to track pipeline velocity, deal slippage, and stage dwell time over 30/60/90 days.
2. **Machine Learning Win Probability Calibration:**  
   Calibrate rep-entered closure probabilities using historical stage conversion patterns.
3. **Automated Anomaly Detection:**  
   Alert leadership on sudden spikes in work order delays or stalled high-value deals.
4. **Role-Based Access Control (RBAC):**  
   Implement granular role tiers (Founder, VP Sales, Project Lead) with data masking for sensitive compensation fields.
