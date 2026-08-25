"""Column ID and title mapping for Monday.com Deals and Work Orders boards.

Supports dynamic schema inspection, title alias matching, and confidence tracking.
"""

from typing import Dict, Any, List, Optional, Tuple
import re


# Semantic Field Definitions for Deals Board
DEALS_SEMANTIC_FIELDS = {
    "deal_name",
    "client",
    "client_code",
    "owner",
    "owner_code",
    "deal_status",
    "stage",
    "deal_value",
    "close_date",
    "tentative_close_date",
    "closure_probability",
    "product_deal",
    "sector_service",
    "created_date",
    "last_updated",
    "notes"
}

# Semantic Field Definitions for Work Orders Board
WORK_ORDERS_SEMANTIC_FIELDS = {
    "deal_name",
    "client",
    "customer_name_code",
    "serial_number",
    "nature_of_work",
    "type_of_work",
    "execution_status",
    "data_delivery_date",
    "po_loi_date",
    "start_date",
    "end_date",
    "probable_start_date",
    "probable_end_date",
    "sector",
    "invoice_status",
    "billing_status",
    "billed_value",
    "collected_amount",
    "amount_receivable",
    "expected_billing_month",
    "actual_billing_month",
    "actual_collection_month",
    "collection_status",
    "assigned_team",
    "region"
}

# Static column ID mapping fallback for Deals
DEALS_COLUMN_MAP: Dict[str, str] = {
    "name": "client",
    "client": "client",
    "client_name": "client",
    "client_code": "client_code",
    "sector": "sector_service",
    "sector_service": "sector_service",
    "status_1": "sector_service",
    "dropdown": "sector_service",
    "stage": "stage",
    "deal_stage": "stage",
    "deal_status": "deal_status",
    "status": "stage",
    "deal_value": "deal_value",
    "numbers": "deal_value",
    "value": "deal_value",
    "amount": "deal_value",
    "close_date": "close_date",
    "expected_close_date": "close_date",
    "tentative_close_date": "tentative_close_date",
    "date": "close_date",
    "owner": "owner",
    "owner_code": "owner_code",
    "person": "owner",
    "people": "owner",
    "probability": "closure_probability",
    "probability_%": "closure_probability",
    "closure_probability": "closure_probability",
    "numbers_1": "closure_probability",
    "product_deal": "product_deal",
    "created_date": "created_date",
    "last_updated": "last_updated",
    "date_1": "last_updated",
    "notes": "notes",
    "long_text": "notes"
}

# Title aliases for Deals board
DEALS_TITLE_ALIASES: Dict[str, str] = {
    "client": "client",
    "client name": "client",
    "company": "client",
    "account": "client",
    "deal name": "deal_name",
    "name": "client",
    "client code": "client_code",
    "customer code": "client_code",
    
    "sector": "sector_service",
    "sector/service": "sector_service",
    "sector service": "sector_service",
    "industry": "sector_service",
    "service": "sector_service",
    
    "stage": "stage",
    "deal stage": "stage",
    "pipeline stage": "stage",
    "deal status": "deal_status",
    "status": "stage",
    
    "deal value": "deal_value",
    "value": "deal_value",
    "amount": "deal_value",
    "revenue": "deal_value",
    "contract value": "deal_value",
    
    "close date": "close_date",
    "expected close date": "close_date",
    "tentative close date": "tentative_close_date",
    "target close date": "close_date",
    "closing date": "close_date",
    
    "owner": "owner",
    "deal owner": "owner",
    "owner code": "owner_code",
    "sales rep": "owner",
    "lead": "owner",
    
    "probability": "closure_probability",
    "probability %": "closure_probability",
    "closure probability": "closure_probability",
    "win probability": "closure_probability",
    "win %": "closure_probability",
    
    "product deal": "product_deal",
    "product": "product_deal",
    "offering": "product_deal",
    
    "created date": "created_date",
    "creation date": "created_date",
    "last updated": "last_updated",
    "updated date": "last_updated",
    
    "notes": "notes",
    "comments": "notes",
    "description": "notes"
}

# Static column ID mapping fallback for Work Orders
WORK_ORDERS_COLUMN_MAP: Dict[str, str] = {
    "name": "deal_name",
    "client": "client",
    "client_name": "client",
    "customer_name_code": "customer_name_code",
    "serial_number": "serial_number",
    "nature_of_work": "nature_of_work",
    "type_of_work": "type_of_work",
    "sector": "sector",
    "status_1": "sector",
    "status": "execution_status",
    "execution_status": "execution_status",
    "start_date": "start_date",
    "end_date": "end_date",
    "probable_start_date": "probable_start_date",
    "probable_end_date": "probable_end_date",
    "data_delivery_date": "data_delivery_date",
    "po_loi_date": "po_loi_date",
    "invoice_status": "invoice_status",
    "billing_status": "billing_status",
    "billed_value": "billed_value",
    "collected_amount": "collected_amount",
    "amount_receivable": "amount_receivable",
    "expected_billing_month": "expected_billing_month",
    "actual_billing_month": "actual_billing_month",
    "actual_collection_month": "actual_collection_month",
    "collection_status": "collection_status",
    "assigned_team": "assigned_team",
    "pilot": "assigned_team",
    "region": "region",
    "location": "region"
}

# Title aliases for Work Orders board
WORK_ORDERS_TITLE_ALIASES: Dict[str, str] = {
    "deal name": "deal_name",
    "order name": "deal_name",
    "name": "deal_name",
    "client": "client",
    "client name": "client",
    "customer name code": "customer_name_code",
    "customer code": "customer_name_code",
    "client code": "customer_name_code",
    "serial number": "serial_number",
    "sl no": "serial_number",
    "wo number": "serial_number",
    
    "nature of work": "nature_of_work",
    "type of work": "type_of_work",
    "work type": "type_of_work",
    
    "execution status": "execution_status",
    "order status": "execution_status",
    "status": "execution_status",
    
    "data delivery date": "data_delivery_date",
    "delivery date": "data_delivery_date",
    "po / loi date": "po_loi_date",
    "po date": "po_loi_date",
    "loi date": "po_loi_date",
    
    "probable start date": "probable_start_date",
    "start date": "start_date",
    "probable end date": "probable_end_date",
    "end date": "end_date",
    
    "sector": "sector",
    "industry": "sector",
    
    "invoice status": "invoice_status",
    "billing status": "billing_status",
    "collection status": "collection_status",
    
    "billed value": "billed_value",
    "billed amount": "billed_value",
    "invoice amount": "billed_value",
    
    "collected amount": "collected_amount",
    "received amount": "collected_amount",
    "amount collected": "collected_amount",
    
    "amount receivable": "amount_receivable",
    "receivable": "amount_receivable",
    "outstanding": "amount_receivable",
    "balance amount": "amount_receivable",
    
    "expected billing month": "expected_billing_month",
    "actual billing month": "actual_billing_month",
    "actual collection month": "actual_collection_month",
    
    "assigned team": "assigned_team",
    "pilot": "assigned_team",
    "team": "assigned_team",
    
    "region": "region",
    "location": "region",
    "site": "region"
}


def build_dynamic_column_map_with_metadata(
    schema_columns: List[Dict[str, Any]],
    board_type: str
) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    """Map monday columns dynamically and track mapping confidence & provenance metadata."""
    resolved_map: Dict[str, str] = {}
    mapping_metadata: List[Dict[str, Any]] = []
    
    title_aliases = DEALS_TITLE_ALIASES if board_type == "deals" else WORK_ORDERS_TITLE_ALIASES
    static_map = DEALS_COLUMN_MAP if board_type == "deals" else WORK_ORDERS_COLUMN_MAP

    for col in schema_columns:
        col_id = col.get("id", "")
        title = col.get("title", "").strip().lower()
        col_type = col.get("type", "")

        matched_field = None
        method = "none"
        confidence = "low"
        confidence_num = 0.3

        # 1. Exact title alias match
        if title in title_aliases:
            matched_field = title_aliases[title]
            method = "exact_title_alias"
            confidence = "high"
            confidence_num = 1.0
        else:
            norm_title = re.sub(r"[^\w\s]", "", title)
            if norm_title in title_aliases:
                matched_field = title_aliases[norm_title]
                method = "normalized_title_alias"
                confidence = "high"
                confidence_num = 0.9
            else:
                for alias_key, canon_name in title_aliases.items():
                    if alias_key in title.split():
                        matched_field = canon_name
                        method = "substring_title_match"
                        confidence = "medium"
                        confidence_num = 0.7
                        break

        # 2. Fall back to static map by ID
        if not matched_field and col_id in static_map:
            matched_field = static_map[col_id]
            method = "static_id_fallback"
            confidence = "high"
            confidence_num = 0.95

        if matched_field:
            resolved_map[col_id] = matched_field
            mapping_metadata.append({
                "column_id": col_id,
                "column_title": col.get("title", ""),
                "column_type": col_type,
                "semantic_field": matched_field,
                "mapping_method": method,
                "confidence": confidence,
                "confidence_score": confidence_num
            })
        else:
            mapping_metadata.append({
                "column_id": col_id,
                "column_title": col.get("title", ""),
                "column_type": col_type,
                "semantic_field": None,
                "mapping_method": "unmapped",
                "confidence": "none",
                "confidence_score": 0.0
            })

    return resolved_map, mapping_metadata


def build_dynamic_column_map(schema_columns: List[Dict[str, Any]], board_type: str) -> Dict[str, str]:
    """Helper returning only the column_id -> semantic_field dictionary."""
    resolved_map, _ = build_dynamic_column_map_with_metadata(schema_columns, board_type)
    return resolved_map


def extract_item_fields(item: Dict[str, Any], column_map: Dict[str, str]) -> Dict[str, Any]:
    """Extract canonical business concepts from raw monday item using the column mapping."""
    fields: Dict[str, Any] = {
        "id": item.get("item_id"),
        "raw_name": item.get("item_name")
    }
    
    if item.get("item_name"):
        fields["client"] = item.get("item_name")
        fields["deal_name"] = item.get("item_name")
        
    cols = item.get("columns", {})
    
    for col_id, col_data in cols.items():
        canonical_field = column_map.get(col_id)
        if not canonical_field:
            continue
            
        text_val = col_data.get("text")
        raw_val = col_data.get("value")
        
        val_to_use = text_val if (text_val is not None and str(text_val).strip() != "") else raw_val
        fields[canonical_field] = val_to_use
        
    return fields
