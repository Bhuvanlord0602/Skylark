# 🔧 Monday.com Integration & Setup Guide

This guide walks through configuring your Monday.com workspace, generating API tokens, setting up the **Deals** and **Work Orders** boards, and discovering column mappings.

---

## 1. Obtaining Your Monday.com API Token

1. Log into your **Monday.com** account.
2. Click on your profile avatar in the bottom-left corner and select **Developers**.
3. Navigate to **My Access Tokens** (or **API**).
4. Copy your personal API token.
5. Add the token to your `.env` file:
   ```env
   MONDAY_API_TOKEN=your_personal_api_token_here
   ```

> [!CAUTION]
> Treat `MONDAY_API_TOKEN` as a confidential credential. Never commit it to git or expose it to client-side code.

---

## 2. Board Configuration & IDs

The agent connects to two boards by reading their IDs from environment variables:

| Board Name | Description | Default Board ID |
| :--- | :--- | :--- |
| **Deals** | Sales pipeline, deal values, stages, win probabilities, expected close dates | `5030842959` |
| **Work Orders** | Delivery operations, execution statuses, start/end dates, hours & costs | `5030843495` |

Set these in `.env`:
```env
MONDAY_DEALS_BOARD_ID=5030842959
MONDAY_WORK_ORDERS_BOARD_ID=5030843495
```

---

## 3. Recommended Board Schemas

### Deals Board Columns

| Column Name | Recommended Column Type | Description |
| :--- | :--- | :--- |
| **Client / Deal Name** | Text or Name | Name of the prospective client |
| **Sector** | Status or Dropdown | Industry vertical (e.g., Energy, Tech, Healthcare) |
| **Stage** | Status | Funnel stage (e.g., Lead, Proposal, Negotiation, Won, Lost) |
| **Deal Value** | Numbers | Financial deal size ($) |
| **Expected Close Date** | Date | Target closing date |
| **Owner** | People or Text | Sales representative |
| **Probability %** | Numbers | Win probability percentage (0–100) |
| **Last Updated** | Date | Date of latest activity |
| **Notes** | Long Text | Contextual notes |

### Work Orders Board Columns

| Column Name | Recommended Column Type | Description |
| :--- | :--- | :--- |
| **Client / Order Name** | Text or Name | Name of the client |
| **Sector** | Status or Dropdown | Industry vertical |
| **Status** | Status | Execution status (Planned, In Progress, Completed, Delayed, Blocked) |
| **Start Date** | Date | Planned or actual start date |
| **End Date** | Date | Target completion date |
| **Planned Hours** | Numbers | Estimated labor hours |
| **Actual Hours** | Numbers | Actual hours spent |
| **Planned Cost** | Numbers | Budgeted delivery cost |
| **Actual Cost** | Numbers | Actual cost spent |
| **Assigned Team / Pilot** | Text or People | Operating team / pilot |
| **Region** | Text | Site or geographical region |

---

## 4. Dumping Board Schema via CLI

To inspect your board column IDs and verify connectivity, use the built-in CLI:

```bash
# Verify health and reachability
python -m app.tools.monday_client --health

# Dump schema for Deals board
python -m app.tools.monday_client --dump-schema --board-id 5030842959

# Dump schema for Work Orders board
python -m app.tools.monday_client --dump-schema --board-id 5030843495
```

The output displays all column IDs and titles. If your board uses custom column titles, `app/tools/column_map.py` automatically resolves them dynamically using title aliases and column type heuristics.

