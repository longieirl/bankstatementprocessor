"""Date parsing service for bank statement transactions.

This module provides a centralized service for parsing various date formats
commonly found in bank statements. It handles 2-digit year normalization,
partial dates, and multiple date format variations.
"""

from __future__ import annotations

import contextlib
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DateParserService:
    """Service for parsing bank statement dates.

    Handles multiple date formats, 2-digit year normalization, and partial
    date parsing (dates without years). Provides consistent date parsing
    across the application.
    """

    # Constants for date parsing
    EPOCH_DATE = datetime(1970, 1, 1)
    TWO_DIGIT_YEAR_CUTOFF = 50  # Years 00-49 are 2000-2049, 50-99 are 1950-1999
    DEFAULT_YEAR = 2023  # Default year for partial dates without year component

    # Common date formats found in bank statements
    DATE_FORMATS = [
        "%d/%m/%y",  # 01/12/23
        "%d/%m/%Y",  # 01/12/2023
        "%d-%m-%y",  # 01-12-23
        "%d-%m-%Y",  # 01-12-2023
        "%d %b %Y",  # 25 Apr 2025
        "%d %B %Y",  # 25 April 2025
        "%d %b %y",  # 25 Apr 25
        "%d %B %y",  # 25 April 25
        "%d%b%y",  # 01DEC23
        "%d%B%y",  # 01December23
        "%d%b%Y",  # 01DEC2023
        "%d%B%Y",  # 01December2023
    ]

    def parse_transaction_date(self, date_str: str) -> datetime:
        """
        Parse bank statement date string into datetime object.

        Handles common bank statement date formats:
        - DD/MM/YY (e.g., "01/12/23")
        - DD/MM/YYYY (e.g., "01/12/2023")
        - DD-MM-YY (e.g., "01-12-23")
        - DD-MM-YYYY (e.g., "01-12-2023")
        - DD MMM YYYY (e.g., "25 Apr 2025")
        - DD MMMM YYYY (e.g., "25 April 2025")
        - DD MMM YY (e.g., "25 Apr 25")
        - DD MMMM YY (e.g., "25 April 25")
        - DDMMMYY (e.g., "01DEC23")
        - DDMMMYYYY (e.g., "01DEC2023")
        - Partial dates: "DD/MM" (missing year)

        Args:
            date_str: Date string from bank statement

        Returns:
            datetime object, or epoch (1970-01-01) if unparseable

        Note:
            Returns epoch date for unparseable dates to ensure they sort to
            beginning rather than causing errors. This preserves all transaction data.

        Examples:
            >>> service = DateParserService()
            >>> service.parse_transaction_date("01/12/23")
            datetime.datetime(2023, 12, 1, 0, 0)
            >>> service.parse_transaction_date("25 Apr 2025")
            datetime.datetime(2025, 4, 25, 0, 0)
            >>> service.parse_transaction_date("")
            datetime.datetime(1970, 1, 1, 0, 0)
        """
        # Handle empty or whitespace-only strings
        if not date_str or not date_str.strip():
            return self.EPOCH_DATE

        date_str = date_str.strip()

        # Normalize non-standard month abbreviations used by some banks
        # "Sept" -> "Sep" (Python's datetime uses 3-letter abbreviations)
        date_str = date_str.replace("Sept", "Sep")

        # Try common date formats
        parsed_date = self._parse_common_date_formats(date_str)
        if parsed_date is not None:
            return parsed_date

        # Try partial date parsing (DD/MM without year)
        parsed_date = self._parse_partial_date(date_str)
        if parsed_date is not None:
            return parsed_date

        # If all parsing attempts fail, log warning and return epoch
        logger.warning(
            "Unable to parse date '%s', using epoch date for sorting", date_str
        )
        return self.EPOCH_DATE

    def _normalize_two_digit_year(
        self, parsed_date: datetime, format_string: str
    ) -> datetime:
        """
        Normalize 2-digit years using cutoff logic.

        Years 00-49 are treated as 2000-2049.
        Years 50-99 are treated as 1950-1999.

        Args:
            parsed_date: Datetime parsed from format string
            format_string: Format string used for parsing (to detect 2-digit year)

        Returns:
            Datetime with corrected 4-digit year

        Examples:
            >>> service = DateParserService()
            >>> date = datetime(2025, 4, 25)
            >>> service._normalize_two_digit_year(date, "%d/%m/%y")
            datetime.datetime(2025, 4, 25, 0, 0)
            >>> date = datetime(2055, 4, 25)  # year parsed as 2055 from "55"
            >>> service._normalize_two_digit_year(date, "%d/%m/%y")
            datetime.datetime(1955, 4, 25, 0, 0)
        """
        # Only adjust for 2-digit year formats
        if "%y" not in format_string:
            return parsed_date

        # Only adjust if year is in 2000+ range (needs correction)
        if parsed_date.year < 2000:
            return parsed_date

        year_suffix = parsed_date.year % 100
        if year_suffix >= self.TWO_DIGIT_YEAR_CUTOFF:
            # 50-99 should be 1950-1999
            return parsed_date.replace(year=1900 + year_suffix)

        return parsed_date

    def _try_parse_date_format(
        self, date_str: str, format_string: str
    ) -> datetime | None:
        """
        Try to parse a date string with a specific format.

        Args:
            date_str: Date string to parse
            format_string: strptime format string to try

        Returns:
            Parsed datetime if successful, None if parsing fails

        Examples:
            >>> service = DateParserService()
            >>> service._try_parse_date_format("01/12/23", "%d/%m/%y")
            datetime.datetime(2023, 12, 1, 0, 0)
            >>> service._try_parse_date_format("invalid", "%d/%m/%y")
            None
        """
        try:
            parsed_date = datetime.strptime(date_str, format_string)
            return self._normalize_two_digit_year(parsed_date, format_string)
        except ValueError:
            return None

    def _parse_common_date_formats(self, date_str: str) -> datetime | None:
        """
        Try to parse date string using common bank statement formats.

        Iterates through all known DATE_FORMATS and returns the first successful
        parse result.

        Args:
            date_str: Date string to parse

        Returns:
            Parsed datetime if any format matches, None otherwise

        Examples:
            >>> service = DateParserService()
            >>> service._parse_common_date_formats("01/12/2023")
            datetime.datetime(2023, 12, 1, 0, 0)
            >>> service._parse_common_date_formats("25 Apr 2025")
            datetime.datetime(2025, 4, 25, 0, 0)
            >>> service._parse_common_date_formats("not-a-date")
            None
        """
        for fmt in self.DATE_FORMATS:
            parsed_date = self._try_parse_date_format(date_str, fmt)
            if parsed_date is not None:
                return parsed_date

        return None

    def _parse_partial_date(self, date_str: str) -> datetime | None:
        """
        Parse partial date strings like "DD/MM" or "DD-MM" (missing year).

        Uses DEFAULT_YEAR for dates without a year component.
        Handles 2-digit years with cutoff logic.

        Args:
            date_str: Date string to parse

        Returns:
            Parsed datetime if successful, None if parsing fails

        Examples:
            >>> service = DateParserService()
            >>> service._parse_partial_date("01/12")
            datetime.datetime(2023, 12, 1, 0, 0)
            >>> service._parse_partial_date("25-04")
            datetime.datetime(2023, 4, 25, 0, 0)
            >>> service._parse_partial_date("no-slashes")
            None
        """
        # Only try if we have date separators
        if "/" not in date_str and "-" not in date_str:
            return None

        with contextlib.suppress(ValueError, IndexError):
            parts = date_str.replace("-", "/").split("/")
            if len(parts) >= 2:
                day = int(parts[0])
                month = int(parts[1])
                year = int(parts[2]) if len(parts) > 2 else self.DEFAULT_YEAR

                # Handle 2-digit years using cutoff logic
                if year < self.TWO_DIGIT_YEAR_CUTOFF:
                    year += 2000
                elif year < 100:
                    year += 1900

                return datetime(year, month, day)

        return None
