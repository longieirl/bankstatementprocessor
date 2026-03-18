"""Row Analysis Service for bank statement transactions.

This module provides services for analyzing row quality, completeness scoring,
and date validation for extracted PDF transaction data.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bankstatements_core.domain.column_types import get_type_as_string

if TYPE_CHECKING:
    pass


class RowAnalysisService:
    """Service for analyzing row completeness and quality.

    Provides scoring mechanisms to evaluate transaction row quality based on:
    - Filled columns with weighted importance
    - Content quality (proper formatting, meaningful data)
    - Semantic column types
    """

    def __init__(self) -> None:
        """Initialize row analysis service."""
        # Weight different column types based on importance for transaction ID
        self.type_weights = {
            "date": 0.2,
            "description": 0.3,
            "debit": 0.25,
            "credit": 0.25,
            "balance": 0.2,
            "other": 0.1,
        }

    def calculate_row_completeness_score(
        self, row: dict, columns: dict[str, tuple[int, int]]
    ) -> float:
        """Score row completeness (0.0-1.0) based on filled columns and quality.

        Args:
            row: Dictionary containing row data
            columns: Column definitions for weight calculation

        Returns:
            Float score between 0.0 and 1.0

        Examples:
            >>> service = RowAnalysisService()
            >>> row = {"Date": "01/01/23", "Details": "Payment", "Amount": "100.00"}
            >>> columns = {"Date": (0, 50), "Details": (50, 200), "Amount": (200, 250)}
            >>> score = service.calculate_row_completeness_score(row, columns)
            >>> 0.0 <= score <= 1.0
            True
        """
        # Exclude Filename from scoring
        data_columns = list(columns.keys())
        filled_columns = 0.0
        total_weight = 0.0

        for col in data_columns:
            # Identify column type semantically
            col_type = get_type_as_string(col)
            weight = self.type_weights[col_type]
            total_weight += weight

            value = row.get(col, "").strip()
            if value:
                filled_columns += weight

                # Bonus for high-quality content based on semantic type
                if col_type == "description" and len(value) > 5:
                    # Meaningful description
                    filled_columns += weight * 0.2
                elif col_type in ["debit", "credit", "balance"] and re.match(
                    r"\d+\.\d{2}$", value
                ):
                    # Proper money format
                    filled_columns += weight * 0.3

        return min(filled_columns / total_weight, 1.0) if total_weight > 0 else 0.0

    def looks_like_date(self, text: str) -> bool:
        """Check if text looks like a valid date.

        Args:
            text: Text to check

        Returns:
            True if text appears to be a date, False otherwise

        Examples:
            >>> service = RowAnalysisService()
            >>> service.looks_like_date("01/12/2023")
            True
            >>> service.looks_like_date("15 Jan 2023")
            True
            >>> service.looks_like_date("Hello World")
            False
        """
        # Common date patterns
        date_patterns = [
            r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$",  # DD/MM/YY, DD-MM-YY
            r"^\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}$",  # DD MMM YYYY, DD Month YYYY
            r"^\d{1,2}\s+[A-Za-z]{3,9}$",  # DD MMM (without year)
            r"^\d{1,2}[A-Z]{3}\d{2,4}$",  # DDMMMYY, DDMMMYYYY
        ]

        text = text.strip()
        return any(re.match(pattern, text) for pattern in date_patterns)
