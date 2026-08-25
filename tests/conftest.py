"""Test fixtures and mock Monday.com data for Skylark Drones BI Agent test suite."""

import pytest
from typing import Dict, Any, List


@pytest.fixture
def mock_deals_raw_items() -> List[Dict[str, Any]]:
    """Sample raw Monday.com items from Deals board covering various messy data conditions."""
    return [
        {
            "item_id": "1001",
            "item_name": "Apex Solar Energy Ltd",
            "columns": {
                "client_code": {"text": "APX-01", "value": None, "type": "text"},
                "sector": {"text": "Renewables", "value": None, "type": "status"},
                "stage": {"text": "Won", "value": None, "type": "status"},
                "deal_value": {"text": "$150,000", "value": "150000", "type": "numbers"},
                "close_date": {"text": "2025-03-31", "value": None, "type": "date"},
                "owner": {"text": "Alice Walker", "value": None, "type": "text"},
                "probability": {"text": "100%", "value": "100", "type": "numbers"},
                "last_updated": {"text": "2025-01-15", "value": None, "type": "date"},
                "notes": {"text": "Contract executed", "value": None, "type": "text"}
            }
        },
        {
            "item_id": "1002",
            "item_name": "Zenith Healthcare Inc.",
            "columns": {
                "client_code": {"text": "ZNT-02", "value": None, "type": "text"},
                "sector": {"text": "Healthcare", "value": None, "type": "status"},
                "stage": {"text": "Proposal", "value": None, "type": "status"},
                "deal_value": {"text": "$250k", "value": "250000", "type": "numbers"},
                "close_date": {"text": "30/04/2025", "value": None, "type": "date"},
                "owner": {"text": "Bob Smith", "value": None, "type": "text"},
                "probability": {"text": "60%", "value": "60", "type": "numbers"},
                "last_updated": {"text": "2025-02-10", "value": None, "type": "date"},
                "notes": {"text": "Reviewing security terms", "value": None, "type": "text"}
            }
        },
        {
            "item_id": "1003",
            "item_name": "Hyperion Cloud Tech LLC",
            "columns": {
                "client_code": {"text": "HYP-03", "value": None, "type": "text"},
                "sector": {"text": "Software", "value": None, "type": "status"},
                "stage": {"text": "Lost", "value": None, "type": "status"},
                "deal_value": {"text": "$80,000", "value": "80000", "type": "numbers"},
                "close_date": {"text": "invalid-date-string", "value": None, "type": "date"},
                "owner": {"text": "Alice Walker", "value": None, "type": "text"},
                "probability": {"text": "0", "value": "0", "type": "numbers"},
                "last_updated": {"text": "2025-01-20", "value": None, "type": "date"},
                "notes": {"text": "Selected competitor", "value": None, "type": "text"}
            }
        },
        {
            "item_id": "1004",
            "item_name": "Omni Global Logistics",
            "columns": {
                "client_code": {"text": "OMG-04", "value": None, "type": "text"},
                "sector": {"text": "Transport", "value": None, "type": "status"},
                "stage": {"text": "Negotiation", "value": None, "type": "status"},
                "deal_value": {"text": "N/A", "value": None, "type": "numbers"},
                "close_date": {"text": "2025-05-15", "value": None, "type": "date"},
                "owner": {"text": "Charlie Davis", "value": None, "type": "text"},
                "probability": {"text": None, "value": None, "type": "numbers"},
                "last_updated": {"text": "2025-02-14", "value": None, "type": "date"},
                "notes": {"text": "Price discussion ongoing", "value": None, "type": "text"}
            }
        },
        {
            "item_id": "1005",
            "item_name": "Bharat Power Corporation Pvt Ltd",
            "columns": {
                "client_code": {"text": "BPC-05", "value": None, "type": "text"},
                "sector": {"text": "Power & Energy", "value": None, "type": "status"},
                "stage": {"text": "Won", "value": None, "type": "status"},
                "deal_value": {"text": "₹1,00,00,000", "value": None, "type": "numbers"},
                "close_date": {"text": "2025-06-30", "value": None, "type": "date"},
                "owner": {"text": "Alice Walker", "value": None, "type": "text"},
                "probability": {"text": "90%", "value": "90", "type": "numbers"},
                "last_updated": {"text": "2025-02-15", "value": None, "type": "date"},
                "notes": {"text": "Indian power grid contract", "value": None, "type": "text"}
            }
        }
    ]


@pytest.fixture
def mock_work_orders_raw_items() -> List[Dict[str, Any]]:
    """Sample raw Monday.com items from Work Orders board."""
    return [
        {
            "item_id": "2001",
            "item_name": "Apex Solar Energy",
            "columns": {
                "customer_name_code": {"text": "APX-01", "value": None, "type": "text"},
                "sector": {"text": "Renewables", "value": None, "type": "status"},
                "status": {"text": "Completed", "value": None, "type": "status"},
                "start_date": {"text": "2025-01-01", "value": None, "type": "date"},
                "end_date": {"text": "2025-02-01", "value": None, "type": "date"},
                "billed_value": {"text": "$50,000", "value": "50000", "type": "numbers"},
                "collected_amount": {"text": "$48,000", "value": "48000", "type": "numbers"},
                "assigned_team": {"text": "Pilot Team Alpha", "value": None, "type": "text"},
                "region": {"text": "Texas", "value": None, "type": "text"}
            }
        },
        {
            "item_id": "2002",
            "item_name": "Zenith Healthcare",
            "columns": {
                "customer_name_code": {"text": "ZNT-02", "value": None, "type": "text"},
                "sector": {"text": "Healthcare", "value": None, "type": "status"},
                "status": {"text": "Delayed", "value": None, "type": "status"},
                "start_date": {"text": "2025-01-15", "value": None, "type": "date"},
                "end_date": {"text": "2025-02-15", "value": None, "type": "date"},
                "billed_value": {"text": "$30,000", "value": "30000", "type": "numbers"},
                "collected_amount": {"text": "$10,000", "value": "10000", "type": "numbers"},
                "assigned_team": {"text": "Pilot Team Beta", "value": None, "type": "text"},
                "region": {"text": "California", "value": None, "type": "text"}
            }
        },
        {
            "item_id": "2003",
            "item_name": "Unlinked Field Services Pvt Ltd",
            "columns": {
                "customer_name_code": {"text": "UFS-99", "value": None, "type": "text"},
                "sector": {"text": "Industrial", "value": None, "type": "status"},
                "status": {"text": "In Progress", "value": None, "type": "status"},
                "start_date": {"text": "2025-02-01", "value": None, "type": "date"},
                "end_date": {"text": "2025-03-15", "value": None, "type": "date"},
                "billed_value": {"text": "$75,000", "value": "75000", "type": "numbers"},
                "collected_amount": {"text": "$40,000", "value": "40000", "type": "numbers"},
                "assigned_team": {"text": "Pilot Team Gamma", "value": None, "type": "text"},
                "region": {"text": "Ohio", "value": None, "type": "text"}
            }
        }
    ]
