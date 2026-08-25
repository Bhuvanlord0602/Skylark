"""Work Orders board extraction, normalization, and operational metrics tool."""

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
from app.tools.column_map import build_dynamic_column_map_with_metadata, extract_item_fields, WORK_ORDERS_COLUMN_MAP
from app.tools.monday_client import monday_client
from app.analytics.work_orders_metrics import compute_work_orders_analytics

logger = logging.getLogger("work_order_tools")


async def get_work_orders(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Retrieve and normalize all items from the Work Orders board with schema discovery."""
    board_id = settings.MONDAY_WORK_ORDERS_BOARD_ID
    
    # 1. Schema Discovery
    mapping_metadata = []
    try:
        schema = await monday_client.fetch_board_schema(board_id)
        schema_columns = schema.get("columns", [])
        active_column_map, mapping_metadata = build_dynamic_column_map_with_metadata(schema_columns, "work_orders")
    except Exception as e:
        logger.warning(f"Failed to fetch work orders schema dynamically: {e}. Using static mapping fallback.")
        active_column_map = WORK_ORDERS_COLUMN_MAP

    # 2. Fetch All Items via Cursor Pagination
    raw_items = await monday_client.fetch_board_items(board_id)
    
    normalized_orders: List[Dict[str, Any]] = []
    field_audit = {
        "execution_status": {"valid": 0, "missing": 0, "total": len(raw_items)},
        "sector": {"valid": 0, "missing": 0, "total": len(raw_items)},
        "start_date": {"valid": 0, "missing": 0, "total": len(raw_items)},
        "end_date": {"valid": 0, "missing": 0, "total": len(raw_items)},
        "billed_value": {"valid": 0, "missing": 0, "total": len(raw_items)},
        "collected_amount": {"valid": 0, "missing": 0, "total": len(raw_items)}
    }
    
    for item in raw_items:
        fields = extract_item_fields(item, active_column_map)
        
        # Parse Dates
        start_date, s_note = parse_date_any(fields.get("start_date") or fields.get("probable_start_date"))
        end_date, e_note = parse_date_any(fields.get("end_date") or fields.get("probable_end_date"))
        delivery_date, _ = parse_date_any(fields.get("data_delivery_date"))
        po_date, _ = parse_date_any(fields.get("po_loi_date"))
        
        # Parse Financial Fields
        billed_val, b_note = clean_number(fields.get("billed_value"))
        collected_val, c_note = clean_number(fields.get("collected_amount"))
        receivable_val, r_note = clean_number(fields.get("amount_receivable"))

        # Calculate receivable if billed and collected are present and receivable is not explicitly given
        if receivable_val is None and billed_val is not None and collected_val is not None:
            receivable_val = max(0.0, billed_val - collected_val)

        # Normalize Sector
        sector_clean, is_unknown_sec = normalize_sector(fields.get("sector"))
        
        # Normalize Client Name for Linking
        client_name = normalize_text(fields.get("client") or fields.get("deal_name"))
        client_norm = normalize_client_name(client_name) if client_name else ""
        
        # Execution Status
        exec_status = normalize_text(fields.get("execution_status") or fields.get("status")) or "Unspecified"

        # Field Audit Tracking
        if exec_status != "Unspecified":
            field_audit["execution_status"]["valid"] += 1
        else:
            field_audit["execution_status"]["missing"] += 1

        if sector_clean != "Unspecified":
            field_audit["sector"]["valid"] += 1
        else:
            field_audit["sector"]["missing"] += 1

        if start_date is not None:
            field_audit["start_date"]["valid"] += 1
        else:
            field_audit["start_date"]["missing"] += 1

        if end_date is not None:
            field_audit["end_date"]["valid"] += 1
        else:
            field_audit["end_date"]["missing"] += 1

        if billed_val is not None:
            field_audit["billed_value"]["valid"] += 1
        else:
            field_audit["billed_value"]["missing"] += 1

        if collected_val is not None:
            field_audit["collected_amount"]["valid"] += 1
        else:
            field_audit["collected_amount"]["missing"] += 1

        order_record = {
            "id": fields.get("id"),
            "deal_name": fields.get("deal_name") or client_name or f"Order #{fields.get('id')}",
            "client": client_name,
            "client_normalized": client_norm,
            "customer_name_code": fields.get("customer_name_code"),
            "serial_number": fields.get("serial_number"),
            "nature_of_work": fields.get("nature_of_work"),
            "type_of_work": fields.get("type_of_work"),
            "execution_status": exec_status,
            "status": exec_status,
            "sector": sector_clean,
            "sector_is_unknown": is_unknown_sec,
            "start_date": start_date,
            "end_date": end_date,
            "data_delivery_date": delivery_date,
            "po_loi_date": po_date,
            "billed_value": billed_val,
            "collected_amount": collected_val,
            "amount_receivable": receivable_val,
            "invoice_status": normalize_text(fields.get("invoice_status")),
            "billing_status": normalize_text(fields.get("billing_status")),
            "collection_status": normalize_text(fields.get("collection_status")),
            "expected_billing_month": fields.get("expected_billing_month"),
            "actual_billing_month": fields.get("actual_billing_month"),
            "actual_collection_month": fields.get("actual_collection_month"),
            "assigned_team": normalize_text(fields.get("assigned_team")) or "Unassigned",
            "region": normalize_text(fields.get("region")) or "Unassigned"
        }

        # Apply Filters if requested
        if filters:
            if "status" in filters and filters["status"]:
                target_status = filters["status"].lower()
                if target_status not in str(order_record["execution_status"]).lower():
                    continue
            if "sector" in filters and filters["sector"]:
                target_sec = filters["sector"].lower()
                if sector_clean.lower() != target_sec and target_sec not in sector_clean.lower():
                    continue
            if "region" in filters and filters["region"]:
                target_reg = filters["region"].lower()
                if target_reg not in str(order_record["region"]).lower():
                    continue

        normalized_orders.append(order_record)

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
        "board_name": "Work Orders",
        "total_retrieved": len(raw_items),
        "total_filtered": len(normalized_orders),
        "work_orders": normalized_orders,
        "data_quality": {
            "score_breakdown": quality_scores,
            "field_audit": field_audit,
            "mapping_metadata": mapping_metadata
        }
    }


async def compute_ops_metrics(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Calculate deterministic operational and financial KPIs from live Work Orders data."""
    wo_data = await get_work_orders(filters)
    orders = wo_data["work_orders"]
    raw_count = wo_data["total_retrieved"]
    quality_info = wo_data.get("data_quality", {})

    metrics = compute_work_orders_analytics(orders, raw_count, quality_info)
    metrics["board_id"] = wo_data["board_id"]
    metrics["data_quality_scores"] = quality_info.get("score_breakdown", {})
    return metrics
