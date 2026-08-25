"""Data cleaning, parsing, and normalization engine for Monday.com BI Agent.

Implements resilient parsing for messy dates, currencies, Indian numbering formats,
multipliers, sector aliases, and corporate entity names.
Every parsed field retains its raw value, normalized value, and parse status.
Invariable rule: Never silently default invalid or ambiguous data.
"""

from __future__ import annotations

import re
import datetime
from typing import Any, Optional, Tuple, Dict, Set, List
from dateutil import parser as date_parser


# Default sector canonical mapping
DEFAULT_SECTOR_ALIASES: Dict[str, str] = {
    # Energy / Utilities / Power / Renewables
    "energy": "Energy",
    "oil & gas": "Energy",
    "oil and gas": "Energy",
    "oil & gas / energy": "Energy",
    "power": "Energy",
    "renewables": "Energy",
    "solar": "Energy",
    "wind": "Energy",
    "utilities": "Energy",
    
    # Financial Services / Banking / Fintech
    "financial services": "Financial Services",
    "finance": "Financial Services",
    "fintech": "Financial Services",
    "banking": "Financial Services",
    "insurance": "Financial Services",
    "wealth management": "Financial Services",
    
    # Healthcare / Medtech / Pharma
    "healthcare": "Healthcare",
    "health": "Healthcare",
    "health care": "Healthcare",
    "medtech": "Healthcare",
    "pharma": "Healthcare",
    "pharmaceuticals": "Healthcare",
    "biotech": "Healthcare",
    "medical": "Healthcare",
    
    # Technology / Software / IT / Telecom
    "technology": "Technology",
    "tech": "Technology",
    "software": "Technology",
    "saas": "Technology",
    "it": "Technology",
    "it services": "Technology",
    "telecom": "Technology",
    "telecommunications": "Technology",
    
    # Manufacturing / Industrial / Aerospace / Defense
    "manufacturing": "Manufacturing",
    "mfg": "Manufacturing",
    "industrial": "Manufacturing",
    "automotive": "Manufacturing",
    "aerospace": "Manufacturing",
    "defense": "Defense",
    "defence": "Defense",
    
    # Government / Public Sector / Infrastructure
    "government": "Government",
    "govt": "Government",
    "public sector": "Government",
    "defense & security": "Government",
    "infrastructure": "Infrastructure",
    "smart cities": "Infrastructure",
    "urban planning": "Infrastructure",
    
    # Agriculture / Forestry
    "agriculture": "Agriculture",
    "agritech": "Agriculture",
    "farming": "Agriculture",
    "forestry": "Agriculture",
    
    # Mining / Minerals
    "mining": "Mining",
    "minerals": "Mining",
    "quarry": "Mining",
    
    # Retail / E-commerce
    "retail": "Retail",
    "ecommerce": "Retail",
    "e-commerce": "Retail",
    "consumer": "Retail",
    
    # Logistics / Supply Chain / Transportation
    "logistics": "Logistics",
    "supply chain": "Logistics",
    "transport": "Logistics",
    "transportation": "Logistics",
    "freight": "Logistics",
    
    # Real Estate / Construction
    "real estate": "Real Estate",
    "construction": "Real Estate",
    "proptech": "Real Estate",
    
    # Education
    "education": "Education",
    "edtech": "Education",
    "university": "Education"
}

CANONICAL_SECTORS: Set[str] = {
    "Energy",
    "Financial Services",
    "Healthcare",
    "Technology",
    "Manufacturing",
    "Defense",
    "Government",
    "Infrastructure",
    "Agriculture",
    "Mining",
    "Retail",
    "Logistics",
    "Real Estate",
    "Education",
    "Unspecified"
}

LEGAL_SUFFIXES_REGEX = re.compile(
    r"\b(pvt\s*ltd|private\s*limited|ltd|limited|inc|incorporated|corp|corporation|"
    r"llc|llp|plc|co|company|gmbh|sa|bv|srl|pty|holdings|group|services|enterprises|technologies|solutions)\b\.?",
    re.IGNORECASE
)


class ParsedField:
    """Wrapper encapsulating raw value, normalized value, parse status, and notes."""
    def __init__(self, raw_value: Any, normalized_value: Any, parse_status: str, note: Optional[str] = None):
        self.raw_value = raw_value
        self.normalized_value = normalized_value
        self.parse_status = parse_status  # "valid", "missing", "ambiguous", "invalid"
        self.note = note

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "parse_status": self.parse_status,
            "note": self.note
        }


def normalize_text(value: Any) -> Optional[str]:
    """Trim whitespace, collapse internal spaces, case-normalize, handle empty/null."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("none", "null", "n/a", "na", "-", "--", "undefined", "tbd"):
        return None
    cleaned = re.sub(r"\s+", " ", text)
    return cleaned if cleaned else None


def normalize_client_name(value: Any) -> str:
    """Normalize client name for multi-stage exact and fuzzy matching.
    
    Steps:
    1. Lowercase string
    2. Strip punctuation & special symbols
    3. Strip common corporate/legal suffixes (Ltd, Pvt Ltd, Inc, Corp, LLC, etc.)
    4. Collapse whitespace
    """
    text = normalize_text(value)
    if not text:
        return ""
    lowered = text.lower()
    clean_punct = re.sub(r"[^\w\s]", " ", lowered)
    without_suffixes = LEGAL_SUFFIXES_REGEX.sub(" ", clean_punct)
    normalized = re.sub(r"\s+", " ", without_suffixes).strip()
    return normalized if normalized else lowered.strip()


def parse_date_any(value: Any, dayfirst: bool = True) -> Tuple[Optional[str], Optional[str]]:
    """Parse raw date representation into ISO YYYY-MM-DD string.
    
    CRITICAL RULE: Never silently defaults to 'today'. If unparseable or ambiguous, returns (None, note).
    """
    if value is None:
        return None, "missing_date"
    
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime("%Y-%m-%d"), None
    
    # Handle Excel serial dates (e.g. 44927 -> 2023-01-01)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            if 30000 <= value <= 60000:
                excel_base = datetime.date(1899, 12, 30)
                dt = excel_base + datetime.timedelta(days=int(value))
                return dt.strftime("%Y-%m-%d"), None
        except Exception:
            pass

    raw_str = str(value).strip()
    if not raw_str or raw_str.lower() in ("none", "null", "n/a", "na", "-", "--", "tbd", "undefined", "blank"):
        return None, "missing_date"
    
    # Direct ISO format YYYY-MM-DD
    iso_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", raw_str)
    if iso_match:
        try:
            year, month, day = map(int, iso_match.groups())
            dt = datetime.date(year, month, day)
            return dt.strftime("%Y-%m-%d"), None
        except ValueError:
            return None, f"invalid_date_values: {raw_str}"

    # Try dateutil parser with dayfirst
    try:
        parsed_dt = date_parser.parse(raw_str, dayfirst=dayfirst, fuzzy=False)
        return parsed_dt.strftime("%Y-%m-%d"), None
    except Exception:
        pass

    # Try dateutil parser with US format (Month DD, YYYY or MM/DD/YYYY)
    try:
        parsed_dt = date_parser.parse(raw_str, dayfirst=not dayfirst, fuzzy=False)
        return parsed_dt.strftime("%Y-%m-%d"), None
    except Exception:
        pass

    # Fallback fuzzy parser
    try:
        parsed_dt = date_parser.parse(raw_str, fuzzy=True)
        return parsed_dt.strftime("%Y-%m-%d"), None
    except Exception:
        return None, f"unparseable_date: {raw_str}"


def parse_date_structured(value: Any) -> ParsedField:
    """Parse date and return a structured ParsedField object."""
    iso_val, note = parse_date_any(value)
    if iso_val:
        return ParsedField(raw_value=value, normalized_value=iso_val, parse_status="valid", note=None)
    if note == "missing_date":
        return ParsedField(raw_value=value, normalized_value=None, parse_status="missing", note="Missing date value")
    return ParsedField(raw_value=value, normalized_value=None, parse_status="invalid", note=note)


def clean_number(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """Clean numeric values (currency signs, percentages, Indian/US comma formats, multipliers).
    
    Supports:
        - $100,000 / €1,000,000 / £50,000
        - ₹1,00,000 / INR 50,00,000 (Indian numbering system)
        - Multipliers: 100k (100,000), 1.5M (1,500,000), 2.5Cr (25,000,000), 10Lakh (1,000,000)
        - Negative values in parentheses: ($5,000) -> -5000.0
    
    CRITICAL RULE: Returns None (not 0.0) if unparseable or missing.
    """
    if value is None:
        return None, "missing_number"
    
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (value != value):
            return None, "missing_number"
        return float(value), None
    
    raw = str(value).strip()
    if not raw or raw.lower() in ("none", "null", "n/a", "na", "-", "--", "tbd", "undefined", "blank", "masked"):
        return None, "missing_number"
    
    # Handle negative brackets
    is_negative = False
    if raw.startswith("(") and raw.endswith(")"):
        is_negative = True
        raw = raw[1:-1].strip()
    elif raw.startswith("-"):
        is_negative = True
        raw = raw[1:].strip()

    lowered = raw.lower().replace(" ", "")

    multiplier = 1.0
    if lowered.endswith("cr") or lowered.endswith("crore") or lowered.endswith("crores"):
        multiplier = 10_000_000.0
        raw = re.sub(r"(cr|crore|crores)$", "", raw, flags=re.I).strip()
    elif lowered.endswith("lakh") or lowered.endswith("lakhs") or lowered.endswith("lac") or lowered.endswith("lacs") or lowered.endswith("l"):
        multiplier = 100_000.0
        raw = re.sub(r"(lakh|lakhs|lac|lacs|l)$", "", raw, flags=re.I).strip()
    elif lowered.endswith("k"):
        multiplier = 1_000.0
        raw = raw[:-1].strip()
    elif lowered.endswith("m") or lowered.endswith("million"):
        multiplier = 1_000_000.0
        raw = re.sub(r"(m|million)$", "", raw, flags=re.I).strip()
    elif lowered.endswith("b") or lowered.endswith("billion"):
        multiplier = 1_000_000_000.0
        raw = re.sub(r"(b|billion)$", "", raw, flags=re.I).strip()

    # Strip currency signs, percentages, letters, spaces
    cleaned = re.sub(r"[$,€,£,₹,¥,%,A-Za-z\s]", "", raw)
    # Remove commas
    cleaned = cleaned.replace(",", "")

    if not cleaned:
        return None, f"unparseable_number: {value}"
    
    try:
        num = float(cleaned) * multiplier
        if is_negative:
            num = -num
        return num, None
    except ValueError:
        return None, f"unparseable_number: {value}"


def clean_number_structured(value: Any) -> ParsedField:
    """Parse number and return a structured ParsedField object."""
    num_val, note = clean_number(value)
    if num_val is not None:
        return ParsedField(raw_value=value, normalized_value=num_val, parse_status="valid", note=None)
    if note == "missing_number":
        return ParsedField(raw_value=value, normalized_value=None, parse_status="missing", note="Missing numeric value")
    return ParsedField(raw_value=value, normalized_value=None, parse_status="invalid", note=note)


def normalize_sector(value: Any, alias_map: Optional[Dict[str, str]] = None) -> Tuple[str, bool]:
    """Map messy sector string to canonical sector set.
    
    Unknown values are bucketed into 'Unspecified' and flagged (is_unknown=True),
    never silently guessed.
    """
    text = normalize_text(value)
    if not text:
        return "Unspecified", True
    
    mapping = alias_map if alias_map is not None else DEFAULT_SECTOR_ALIASES
    lowered = text.lower()
    
    for canon in CANONICAL_SECTORS:
        if lowered == canon.lower():
            return canon, False
            
    if lowered in mapping:
        return mapping[lowered], False
        
    for alias_key, canon_val in mapping.items():
        if re.search(r"\b" + re.escape(alias_key) + r"\b", lowered):
            return canon_val, False
            
    return "Unspecified", True


def calculate_days_between(start_date: Optional[str], end_date: Optional[str]) -> Optional[int]:
    """Calculate days difference between two ISO date strings safely."""
    if not start_date or not end_date:
        return None
    try:
        d1 = datetime.datetime.strptime(start_date[:10], "%Y-%m-%d").date()
        d2 = datetime.datetime.strptime(end_date[:10], "%Y-%m-%d").date()
        return (d2 - d1).days
    except Exception:
        return None


def calculate_data_quality_scores(
    total_records: int,
    completeness_fields: Dict[str, Dict[str, int]],
    unique_items_count: int,
    raw_items_count: int,
    mapping_confidence_scores: List[float]
) -> Dict[str, Any]:
    """Compute transparent 4-part Data Quality score breakdown."""
    if total_records == 0:
        return {
            "overall_score_pct": 100.0,
            "completeness_score_pct": 100.0,
            "parsing_score_pct": 100.0,
            "mapping_confidence_score_pct": 100.0,
            "retrieval_integrity_score_pct": 100.0
        }

    # 1. Completeness Score (filled values / total expected fields)
    total_expected_slots = 0
    total_filled_slots = 0
    total_valid_slots = 0
    
    for field_name, stats in completeness_fields.items():
        total_slots = stats.get("total", total_records)
        valid_slots = stats.get("valid", 0)
        missing_slots = stats.get("missing", 0)
        
        total_expected_slots += total_slots
        total_filled_slots += (total_slots - missing_slots)
        total_valid_slots += valid_slots

    completeness_score = round((total_filled_slots / total_expected_slots * 100), 1) if total_expected_slots > 0 else 100.0
    parsing_score = round((total_valid_slots / total_filled_slots * 100), 1) if total_filled_slots > 0 else 100.0

    # 2. Mapping Confidence Score
    avg_map_conf = round(sum(mapping_confidence_scores) / len(mapping_confidence_scores) * 100, 1) if mapping_confidence_scores else 100.0

    # 3. Retrieval Integrity Score
    retrieval_integrity = 100.0 if raw_items_count == unique_items_count and raw_items_count > 0 else (
        round((unique_items_count / raw_items_count * 100), 1) if raw_items_count > 0 else 100.0
    )

    # Weighted Overall Score
    overall_score = round(
        (completeness_score * 0.35) +
        (parsing_score * 0.35) +
        (avg_map_conf * 0.15) +
        (retrieval_integrity * 0.15),
        1
    )

    return {
        "overall_score_pct": overall_score,
        "completeness_score_pct": completeness_score,
        "parsing_score_pct": parsing_score,
        "mapping_confidence_score_pct": avg_map_conf,
        "retrieval_integrity_score_pct": retrieval_integrity
    }
