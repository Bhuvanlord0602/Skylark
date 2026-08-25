"""Unit tests for data normalization and parsing engine."""

import pytest
from app.normalize import (
    parse_date_any,
    clean_number,
    normalize_sector,
    normalize_client_name,
    calculate_days_between,
    calculate_data_quality_scores
)


class TestDateParsing:
    def test_iso_date(self):
        val, note = parse_date_any("2025-03-31")
        assert val == "2025-03-31"
        assert note is None

    def test_slash_date_dayfirst(self):
        val, note = parse_date_any("30/04/2025")
        assert val == "2025-04-30"
        assert note is None

    def test_text_month_date(self):
        val, note = parse_date_any("15 March 2025")
        assert val == "2025-03-15"
        assert note is None

    def test_excel_serial_date(self):
        val, note = parse_date_any(45658)  # 2025-01-01
        assert val == "2025-01-01"
        assert note is None

    def test_missing_date_returns_none(self):
        val, note = parse_date_any(None)
        assert val is None
        assert note == "missing_date"

    def test_unparseable_date_never_defaults_to_today(self):
        val, note = parse_date_any("not-a-real-date-string")
        assert val is None
        assert "unparseable_date" in note


class TestNumberCleaning:
    def test_standard_number(self):
        val, note = clean_number(150000)
        assert val == 150000.0
        assert note is None

    def test_currency_with_commas(self):
        val, note = clean_number("$150,000")
        assert val == 150000.0
        assert note is None

    def test_indian_rupee_format(self):
        val, note = clean_number("₹1,00,00,000")
        assert val == 10000000.0
        assert note is None

    def test_multiplier_crores(self):
        val, note = clean_number("2.5 Cr")
        assert val == 25000000.0
        assert note is None

    def test_multiplier_k(self):
        val, note = clean_number("250k")
        assert val == 250000.0
        assert note is None

    def test_multiplier_million(self):
        val, note = clean_number("1.5M")
        assert val == 1500000.0
        assert note is None

    def test_percentage_string(self):
        val, note = clean_number("60%")
        assert val == 60.0
        assert note is None

    def test_negative_parentheses(self):
        val, note = clean_number("($5,000)")
        assert val == -5000.0
        assert note is None

    def test_missing_number_returns_none(self):
        val, note = clean_number(None)
        assert val is None
        assert note == "missing_number"

    def test_unparseable_number_returns_none_never_zero(self):
        val, note = clean_number("N/A - Pending Negotiation")
        assert val is None
        assert "unparseable_number" in note


class TestSectorNormalization:
    def test_direct_canonical_match(self):
        sec, is_unknown = normalize_sector("Healthcare")
        assert sec == "Healthcare"
        assert is_unknown is False

    def test_alias_renewables(self):
        sec, is_unknown = normalize_sector("Solar Power Renewables")
        assert sec == "Energy"
        assert is_unknown is False

    def test_alias_fintech(self):
        sec, is_unknown = normalize_sector("Fintech Banking Solution")
        assert sec == "Financial Services"
        assert is_unknown is False

    def test_unknown_sector_buckets_to_unspecified(self):
        sec, is_unknown = normalize_sector("Completely Unknown Industry")
        assert sec == "Unspecified"
        assert is_unknown is True


class TestClientNormalization:
    def test_strip_ltd_and_punctuation(self):
        norm = normalize_client_name("Apex Solar Energy Ltd.")
        assert norm == "apex solar energy"

    def test_strip_inc(self):
        norm = normalize_client_name("Zenith Healthcare, Inc.")
        assert norm == "zenith healthcare"

    def test_strip_pvt_ltd(self):
        norm = normalize_client_name("Bharat Power Corporation Pvt Ltd")
        assert norm == "bharat power"


class TestDataQualityCalculation:
    def test_quality_score_computation(self):
        field_audit = {
            "deal_value": {"valid": 8, "missing": 2, "total": 10},
            "sector": {"valid": 10, "missing": 0, "total": 10}
        }
        scores = calculate_data_quality_scores(
            total_records=10,
            completeness_fields=field_audit,
            unique_items_count=10,
            raw_items_count=10,
            mapping_confidence_scores=[1.0, 0.9]
        )
        assert "overall_score_pct" in scores
        assert scores["completeness_score_pct"] == 90.0
        assert scores["retrieval_integrity_score_pct"] == 100.0
