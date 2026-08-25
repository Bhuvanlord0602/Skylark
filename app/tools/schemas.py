"""OpenAI/Groq Function Calling Schemas for Qwen Tool Calling."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_deals",
            "description": "Retrieve normalized deal records from the Monday.com Deals board with optional filtering.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "description": "Optional filters such as sector, stage, min_value, max_value, close_year, close_month",
                        "properties": {
                            "sector": {"type": "string", "description": "Filter by canonical sector (e.g. Energy, Mining, Infrastructure)"},
                            "stage": {"type": "string", "description": "Filter by deal stage"},
                            "min_value": {"type": "number", "description": "Minimum deal value in USD"},
                            "max_value": {"type": "number", "description": "Maximum deal value in USD"},
                            "close_year": {"type": "integer", "description": "Expected close year (e.g. 2025)"},
                            "close_month": {"type": "integer", "description": "Expected close month (1-12)"}
                        }
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_work_orders",
            "description": "Retrieve normalized work orders from the Monday.com Work Orders board with execution statuses, dates, and financial metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "description": "Optional filters such as sector, execution_status, delayed_only, client_name",
                        "properties": {
                            "sector": {"type": "string", "description": "Filter by sector"},
                            "execution_status": {"type": "string", "description": "Filter by status (e.g. In Progress, Completed, Stuck, Delayed)"},
                            "delayed_only": {"type": "boolean", "description": "Only return orders past end date or delayed"},
                            "client_name": {"type": "string", "description": "Search client name substring"}
                        }
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compute_pipeline_metrics",
            "description": "Deterministically calculate all sales pipeline analytics: Total Pipeline Value, Weighted Pipeline, Win Rate, Sector Breakdown, Stage Distribution, and Deal Value Quartiles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "description": "Optional query filters for pipeline aggregation (e.g. sector, close_year, close_month)",
                        "properties": {
                            "sector": {"type": "string", "description": "Filter by sector"},
                            "close_year": {"type": "integer", "description": "Expected close year"},
                            "close_month": {"type": "integer", "description": "Expected close month"}
                        }
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compute_ops_metrics",
            "description": "Deterministically calculate operational & financial performance: Total Work Orders, Delayed Orders, Sector Distribution, Billed Values, Collections, and Outstanding Receivables.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "description": "Optional query filters for operations metrics",
                        "properties": {
                            "sector": {"type": "string", "description": "Filter by sector"}
                        }
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "join_deals_to_work_orders",
            "description": "Execute cross-board entity resolution (Exact Code -> Normalized Name -> RapidFuzz >= 90) and calculate the Sector Health Matrix (Pipeline vs Operational Load).",
            "parameters": {
                "type": "object",
                "properties": {
                    "deals_filters": {
                        "type": "object",
                        "description": "Optional filters for deals board prior to join"
                    },
                    "orders_filters": {
                        "type": "object",
                        "description": "Optional filters for work orders board prior to join"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "data_quality_report",
            "description": "Generate transparent Data Quality & Audit report: 4-part dimensional scores (Completeness, Parsing, Mapping, Retrieval), field audits, missing value rates, and linkage statistics.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_leadership_summary",
            "description": "Generate an 8-section executive leadership briefing synthesizing Pipeline, Key Opportunities, Operational Health, Billing & Receivables, Founder Risks, and Strategic Recommendations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Focus topic for the brief (e.g. 'Executive Business Review')"
                    },
                    "period": {
                        "type": "string",
                        "description": "Reporting period (e.g. 'Q3 2025' or 'Current Fiscal Year')"
                    }
                }
            }
        }
    }
]
