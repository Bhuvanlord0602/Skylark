"""Deals board extraction, normalization, and metrics tool."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from app.config import settings
from app.normalize import (
    parse_date_any,
    clean_number,
    normalize_sector,
    normalize_client_name,
    normalize_text,
    calculate_data_quality_scores
)
from app.tools.column_map import build_dynamic_column_map_with_metadata, extract_item_fields, DEALS_COLUMN_MAP
from app.tools.monday_client import monday_client
from app.analytics.deals_metrics import compute_deals_analytics

logger = logging.getLogger("deals_tools")


async def get_deals(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Retrieve and normalize all items from the Deals board with schema discovery."""
    board_id = settings.MONDAY_DEALS_BOARD_ID
    
    # 1. Schema Discovery
    mapping_metadata = []
    try:
        schema = await monday_client.fetch_board_schema(board_id)
        schema_columns = schema.get("columns", [])
        active_column_map, mapping_metadata = build_dynamic_column_map_with_metadata(schema_columns, "deals")
    except Exception as e:
        logger.warning(f"Failed to fetch deals schema dynamically: {e}. Using static mapping fallback.")
        active_column_map = DEALS_COLUMN_MAP

    # 2. Fetch All Items via Cursor Pagination
    raw_items = await monday_client.fetch_board_items(board_id)
    
    normalized_deals: List[Dict[str, Any]] = []
    field_audit = {
        "deal_value": {"valid": 0, "missing": 0, "total": len(raw_items)},
        "sector_service": {"valid": 0, "missing": 0, "total": len(raw_items)},
        "close_date": {"valid": 0, "missing": 0, "total": len(raw_items)},
        "stage": {"valid": 0, "missing": 0, "total": len(raw_items)},
        "closure_probability": {"valid": 0, "missing": 0, "total": len(raw_items)}
    }
    
    for item in raw_items:
        fields = extract_item_fields(item, active_column_map)
        
        # Parse Dates safely (Never defaults to today)
        close_date, c_note = parse_date_any(fields.get("close_date"))
        tentative_date, _ = parse_date_any(fields.get("tentative_close_date"))
        last_updated, _ = parse_date_any(fields.get("last_updated"))
        created_date, _ = parse_date_any(fields.get("created_date"))
        
        # Parse Numeric Deal Value safely (Never converts missing to 0)
        deal_value, v_note = clean_number(fields.get("deal_value"))
        
        # Parse Closure Probability
        raw_prob = fields.get("closure_probability")
        prob_val, p_note = clean_number(raw_prob)
        if prob_val is not None and prob_val > 100:
            prob_val = min(prob_val, 100.0)

        # Normalize Sector
        sector_clean, is_unknown_sec = normalize_sector(fields.get("sector_service") or fields.get("sector"))
        
        # Normalize Client Name for Exact & Fuzzy Matching
        client_name = normalize_text(fields.get("client"))
        client_norm = normalize_client_name(client_name) if client_name else ""
        
        # Audit statistics
        if deal_value is not None:
            field_audit["deal_value"]["valid"] += 1
        else:
            field_audit["deal_value"]["missing"] += 1

        if sector_clean != "Unspecified":
            field_audit["sector_service"]["valid"] += 1
        else:
            field_audit["sector_service"]["missing"] += 1

        if close_date is not None:
            field_audit["close_date"]["valid"] += 1
        else:
            field_audit["close_date"]["missing"] += 1

        if fields.get("stage"):
            field_audit["stage"]["valid"] += 1
        else:
            field_audit["stage"]["missing"] += 1

        if prob_val is not None:
            field_audit["closure_probability"]["valid"] += 1
        else:
            field_audit["closure_probability"]["missing"] += 1

        deal_record = {
            "id": fields.get("id"),
            "deal_name": fields.get("deal_name") or client_name or f"Deal #{fields.get('id')}",
            "client": client_name,
            "client_normalized": client_norm,
            "client_code": fields.get("client_code"),
            "sector": sector_clean,
            "sector_service": sector_clean,
            "sector_is_unknown": is_unknown_sec,
            "stage": normalize_text(fields.get("stage")) or "Unspecified",
            "deal_status": normalize_text(fields.get("deal_status")),
            "deal_value": deal_value,
            "deal_value_raw": fields.get("deal_value"),
            "deal_value_parse_note": v_note,
            "close_date": close_date,
            "close_date_raw": fields.get("close_date"),
            "close_date_parse_note": c_note,
            "tentative_close_date": tentative_date,
            "closure_probability": prob_val,
            "probability_raw": raw_prob,
            "owner": normalize_text(fields.get("owner")) or "Unassigned",
            "owner_code": fields.get("owner_code"),
            "product_deal": fields.get("product_deal"),
            "created_date": created_date,
            "last_updated": last_updated,
            "notes": fields.get("notes")
        }

        # Apply Filters if requested
        if filters:
            if "sector" in filters and filters["sector"]:
                target_sec = filters["sector"].lower()
                if sector_clean.lower() != target_sec and target_sec not in sector_clean.lower():
                    continue
            if "stage" in filters and filters["stage"]:
                target_stage = filters["stage"].lower()
                deal_stg = str(deal_record["stage"]).lower()
                if target_stage not in deal_stg:
                    continue
            if "owner" in filters and filters["owner"]:
                target_owner = filters["owner"].lower()
                if target_owner not in str(deal_record["owner"]).lower():
                    continue
            if "min_value" in filters and filters["min_value"] is not None:
                if deal_value is None or deal_value < float(filters["min_value"]):
                    continue

        normalized_deals.append(deal_record)

    conf_scores = [m.get("confidence_score", 0.8) for m in mapping_metadata] if mapping_metadata else [0.9]
    quality_scores = calculate_data_quality_scores(
        total_records=len(raw_items),
        completeness_fields=field_audit,
        unique_items_count=len(raw_items),
        raw_items_count=len(raw_items),
        mapping_confidence_scores=conf_scores
    )

    return {
        "board_id": board_id,
        "board_name": "deals",
        "total_retrieved": len(raw_items),
        "total_filtered": len(normalized_deals),
        "deals": normalized_deals,
        "data_quality": {
            "score_breakdown": quality_scores,
            "field_audit": field_audit,
            "mapping_metadata": mapping_metadata
        }
    }


async def compute_pipeline_metrics(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Calculate deterministic sales pipeline KPIs from live retrieved Deals data."""
    deals_data = await get_deals(filters)
    deals = deals_data["deals"]
    raw_count = deals_data["total_retrieved"]
    quality_info = deals_data.get("data_quality", {})

    metrics = compute_deals_analytics(deals, raw_count, quality_info)
    metrics["board_id"] = deals_data["board_id"]
    metrics["data_quality_scores"] = quality_info.get("score_breakdown", {})
    return metrics
