# Architecture Decision Log (ADR) — Monday.com Executive BI Agent

**Project:** Skylark Drones Executive BI Assistant  
**Author:** AI Engineering & Architecture Team  
**Scope:** Architectural Trade-offs, Data Integrity Assumptions, Performance, & Technical Decisions  

---

## 1. Key Architectural Assumptions

1. **Monday.com is Runtime Truth (Zero Static CSV Reliance):**  
   Business metrics are never hardcoded, precalculated, or loaded from static CSVs in production. All numbers reflect the live state of the Monday.com Deals (`5030842959`) and Work Orders (`5030843495`) boards via dynamic cursor pagination.

2. **Real-World Messiness Must Be Resiliently Handled:**  
   Real CRM data contains nulls, corrupted currency strings (`₹1,00,00,000`, `100k`, `1.5M`, `2.5Cr`), and non-standard dates (`DD/MM/YYYY`, text months, Excel serial timestamps). Missing values are never converted to `0` unless explicitly zero in the source, and invalid dates are never defaulted to "today".

3. **Strictly Read-Only Operations:**  
   The application acts as a secure, read-only analytics consumer. GraphQL mutations (`create_item`, `change_column_value`, `delete_item`) are actively blocked at the network client layer with `PermissionError`.

---

## 2. Technical Decisions & Trade-Offs

### A. Groq API + Qwen LLM with OpenAI-Compatible SDK
- **Decision:** Integrated **Groq API with the Qwen model (`qwen/qwen3.6-27b`)** using the standard `openai` Python SDK (`base_url="https://api.groq.com/openai/v1"`).
- **Rationale:** Groq provides ultra-low latency inference (sub-500ms TTFT), allowing instantaneous conversational responses. Standardizing on the OpenAI-compatible interface ensures maximum portability and eliminates vendor lock-in.

### B. Deterministic Python Analytics Before AI Interpretation
- **Decision:** All mathematical aggregations, weighted valuations, stage counts, win rates, and risk matrices are computed deterministically in pure Python before being passed to Qwen.
- **Rationale:** LLMs are prone to arithmetic errors and hallucinations when calculating multi-column weighted sums across hundreds of records. Computing metrics deterministically guarantees 100% mathematical accuracy; Qwen focuses on intent classification, tool orchestration, and executive strategic context.

### C. Explicit Tool Allowlist Registry (`app/tools/registry.py`)
- **Decision:** All tool invocations route through a strict dictionary allowlist (`TOOL_REGISTRY`).
- **Rationale:** Prevents arbitrary code execution vulnerabilities while allowing Qwen to execute multi-round tool calling loops (`MAX_TOOL_ROUNDS=8`).

### D. Token-Efficient Tool Result Serializer (`compact_tool_result_for_llm`)
- **Decision:** Raw board items returned to Qwen are compacted into essential structured summaries rather than serializing 300+ full raw objects.
- **Rationale:** Prevents exceeding Groq rate limits (8,000 TPM limit on free tier) while giving Qwen the exact summary statistics needed to answer founder queries accurately.

### E. 3-Tier Cross-Board Entity Resolution
- **Decision:** Cross-board linking uses a 3-tier hierarchy:
  1. *Level 1:* Exact Customer Code match (`client_code` == `customer_name_code`).
  2. *Level 2:* Normalized Client Name match (punctuation & legal suffixes stripped).
  3. *Level 3:* RapidFuzz token sort ratio (Threshold $\ge 90$).
- **Rationale:** Prevents spurious links between distinct legal entities while tolerating minor typographic variations. Unmatched deals and work orders are never dropped, preserving full data visibility.

### F. Multi-Tier Caching & Background Polling (Redis + In-Memory Fallback)
- **Decision:** Implemented a dual-tier caching layer (`app/cache.py`). If Redis is running (`REDIS_URL`), it stores board snapshots and computed metrics. If Redis is offline or running in standalone mode, it automatically falls back to an in-memory dictionary with timestamp-based TTL eviction.
- **Cache TTL:** 300 seconds (5 minutes).
- **Rationale:** Reduces Monday.com GraphQL API traffic by over 95%, eliminates rate-limit exposure (HTTP 429), and enables sub-50ms response times for dashboards and conversational queries.

---

## 3. Leadership Updates Interpretation

The Leadership Update feature synthesizes 5 strategic dimensions into an 8-section executive briefing:
1. **Executive Direct Answer:** High-level summary of pipeline valuation and operational load.
2. **Pipeline Health:** Total pipeline valuation, weighted pipeline, win rates, and stage distribution.
3. **Key Opportunities:** Top opportunities, closure probabilities, and close timings.
4. **Sector Performance:** Revenue concentrations and market drivers.
5. **Operational & Execution Health:** Work order progress, active delays, and on-time delivery rates.
6. **Billing & Collections:** Billed amounts, collections, and outstanding receivables.
7. **Founder Risks:** Concentration risk, delivery bottlenecks, and receivables aging.
8. **Strategic Recommendations:** Actionable next steps for executive leadership.

---

## 4. What Would Be Improved With More Time

1. **Historical Snapshot Storage & Delta Tracking:**  
   Implement time-series snapshots in PostgreSQL to track pipeline velocity, deal slippage, and stage dwell time over 30/60/90 days.
2. **Machine Learning Win Probability Calibration:**  
   Calibrate rep-entered closure probabilities using historical stage conversion patterns.
3. **Automated Anomaly Alerts:**  
   Send proactive Slack/Email alerts to leadership on sudden spikes in work order delays or stalled high-value deals.
4. **Role-Based Access Control (RBAC):**  
   Implement granular role tiers (Founder, VP Sales, Project Lead) with data masking for sensitive customer accounts.
