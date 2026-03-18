"""Extraction parameters for PDF table processing.

This module defines default parameters and thresholds used throughout
the PDF extraction process. Extracted from pdf_table_extractor.py
to improve separation of concerns.
"""

from __future__ import annotations

from bankstatements_core.config.environment_parser import EnvironmentParser

# ---- Table vertical bounds ----
TABLE_TOP_Y = 300
TABLE_BOTTOM_Y = 720

# ---- Dynamic detection parameters ----
CONTENT_DENSITY_THRESHOLD = EnvironmentParser.parse_float(
    "CONTENT_DENSITY_THRESHOLD", 0.3
)
SLIDING_WINDOW_SIZE = EnvironmentParser.parse_int("SLIDING_WINDOW_SIZE", 5)
MIN_TRANSACTION_SCORE = EnvironmentParser.parse_float("MIN_TRANSACTION_SCORE", 0.6)

# ---- Page validation parameters ----
ENABLE_PAGE_VALIDATION = EnvironmentParser.parse_bool(
    "ENABLE_PAGE_VALIDATION", True
)  # Default ON to ensure table validation on every page
MIN_TABLE_ROWS = EnvironmentParser.parse_int(
    "MIN_TABLE_ROWS", 1
)  # More lenient - allow single transactions
MIN_COLUMN_COVERAGE = EnvironmentParser.parse_float(
    "MIN_COLUMN_COVERAGE", 0.2
)  # Reduced from 40% to 20%
MIN_TRANSACTION_RATIO = EnvironmentParser.parse_float(
    "MIN_TRANSACTION_RATIO", 0.1
)  # Allow 10% instead of 25%
REQUIRE_DATE_COLUMN = EnvironmentParser.parse_bool(
    "REQUIRE_DATE_COLUMN", False
)  # Made optional
REQUIRE_AMOUNT_COLUMN = EnvironmentParser.parse_bool(
    "REQUIRE_AMOUNT_COLUMN", False
)  # Made optional
MIN_HEADER_KEYWORDS = EnvironmentParser.parse_int(
    "MIN_HEADER_KEYWORDS", 2
)  # Minimum number of header keywords to detect table headers

# Known non-transaction patterns (can be extended via environment)
ADMINISTRATIVE_PATTERNS = EnvironmentParser.parse_json_list(
    "ADMINISTRATIVE_PATTERNS",
    ["BALANCE FORWARD", "Interest Rate", "Lending @"],
)
