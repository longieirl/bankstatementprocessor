"""Data models for bank statement templates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class PerPageBoundaries:
    """Per-page boundary overrides for documents with varying table positions.

    Attributes:
        table_top_y: Override for top Y-coordinate boundary on this page
        table_bottom_y: Override for bottom Y-coordinate boundary on this page
        header_check_top_y: Override for header check top Y-coordinate on this page
    """

    table_top_y: int | None = None
    table_bottom_y: int | None = None
    header_check_top_y: int | None = None


@dataclass
class TemplateDetectionConfig:
    """Configuration for detecting which template to use.

    Attributes:
        iban_patterns: Regex patterns to match IBAN format (DEPRECATED - use document_identifiers)
        document_identifiers: Dictionary of identifier types to regex patterns
            - iban_patterns: List of IBAN regex patterns
            - card_number_patterns: List of card number regex patterns
            - loan_reference_patterns: List of loan reference regex patterns
            - account_reference_patterns: List of account reference patterns
        filename_patterns: Glob patterns to match filename (e.g., "Statement JL CA *.pdf")
                          If empty, defaults to ["*.pdf"] to match all PDF files.
        header_keywords: Keywords to search for in page header (e.g., ["Allied Irish Banks"])
        column_headers: Expected column header text (e.g., ["Date", "Details", "Debit"])
        exclude_keywords: Keywords that if found, exclude this template (e.g., ["IBAN"] for credit cards)
    """

    # Legacy support (backward compatibility)
    iban_patterns: list[str] = field(default_factory=list)
    # NEW: Multi-identifier support
    document_identifiers: dict[str, list[str]] = field(default_factory=dict)
    filename_patterns: list[str] = field(default_factory=list)
    header_keywords: list[str] = field(default_factory=list)
    column_headers: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Populate legacy fields from document_identifiers for backward compatibility."""
        # If document_identifiers provided, extract iban_patterns for legacy code
        if self.document_identifiers and not self.iban_patterns:
            self.iban_patterns = self.document_identifiers.get("iban_patterns", [])

        # If only legacy iban_patterns provided, populate document_identifiers
        if self.iban_patterns and not self.document_identifiers:
            self.document_identifiers = {"iban_patterns": self.iban_patterns}

    def get_filename_patterns(self) -> list[str]:
        """Get filename patterns with default fallback.

        Returns:
            List of filename patterns. If none configured, returns ["*.pdf"].
        """
        return self.filename_patterns if self.filename_patterns else ["*.pdf"]

    def get_card_number_patterns(self) -> list[str]:
        """Get card number patterns from document_identifiers.

        Returns:
            List of card number regex patterns, empty list if not configured.
        """
        return self.document_identifiers.get("card_number_patterns", [])

    def get_loan_reference_patterns(self) -> list[str]:
        """Get loan reference patterns from document_identifiers.

        Returns:
            List of loan reference regex patterns, empty list if not configured.
        """
        return self.document_identifiers.get("loan_reference_patterns", [])

    def get_account_reference_patterns(self) -> list[str]:
        """Get account reference patterns from document_identifiers.

        Returns:
            List of account reference regex patterns, empty list if not configured.
        """
        return self.document_identifiers.get("account_reference_patterns", [])


@dataclass
class TemplateExtractionConfig:
    """Configuration for extracting table data from PDF.

    Attributes:
        table_top_y: Top Y-coordinate boundary of transaction table (default for all pages)
        table_bottom_y: Bottom Y-coordinate boundary of transaction table (default for all pages)
        columns: Dictionary mapping column names to (x_start, x_end) tuples
        enable_page_validation: Whether to validate page structure (header detection)
        enable_header_check: Whether to check for table headers before extraction (None = use env var)
        header_check_top_y: Optional Y-coordinate to start header search (None = auto-calculate)
        per_page_overrides: Optional page-specific boundary overrides (key: page number)
    """

    table_top_y: int
    table_bottom_y: int
    columns: dict[str, tuple[float, float]]
    enable_page_validation: bool = True
    enable_header_check: bool | None = None
    header_check_top_y: int | None = None
    per_page_overrides: dict[int, PerPageBoundaries] = field(default_factory=dict)

    def get_table_top_y(self, page_num: int) -> int:
        """Get table_top_y for a specific page, applying overrides if present.

        Args:
            page_num: Page number (1-indexed)

        Returns:
            Table top Y-coordinate for the specified page
        """
        if page_num in self.per_page_overrides:
            override = self.per_page_overrides[page_num]
            if override.table_top_y is not None:
                return override.table_top_y
        return self.table_top_y

    def get_table_bottom_y(self, page_num: int) -> int:
        """Get table_bottom_y for a specific page, applying overrides if present.

        Args:
            page_num: Page number (1-indexed)

        Returns:
            Table bottom Y-coordinate for the specified page
        """
        if page_num in self.per_page_overrides:
            override = self.per_page_overrides[page_num]
            if override.table_bottom_y is not None:
                return override.table_bottom_y
        return self.table_bottom_y

    def get_header_check_top_y(self, page_num: int) -> int | None:
        """Get header_check_top_y for a specific page, applying overrides if present.

        Args:
            page_num: Page number (1-indexed)

        Returns:
            Header check top Y-coordinate for the specified page, or None
        """
        if page_num in self.per_page_overrides:
            override = self.per_page_overrides[page_num]
            if override.header_check_top_y is not None:
                return override.header_check_top_y
        return self.header_check_top_y

    def __post_init__(self) -> None:
        """Validate extraction configuration."""
        if self.table_top_y >= self.table_bottom_y:
            raise ValueError(
                f"table_top_y ({self.table_top_y}) must be less than "
                f"table_bottom_y ({self.table_bottom_y})"
            )

        if not self.columns:
            raise ValueError("columns dictionary cannot be empty")

        for col_name, (x_start, x_end) in self.columns.items():
            if x_start >= x_end:
                raise ValueError(
                    f"Column '{col_name}': x_start ({x_start}) must be less than "
                    f"x_end ({x_end})"
                )

        # Enhanced column boundary validation
        self._validate_column_boundaries()

        # Validate per-page overrides
        for page_num, override in self.per_page_overrides.items():
            if (
                override.table_top_y is not None
                and override.table_bottom_y is not None
                and override.table_top_y >= override.table_bottom_y
            ):
                raise ValueError(
                    f"Page {page_num}: table_top_y ({override.table_top_y}) must be "
                    f"less than table_bottom_y ({override.table_bottom_y})"
                )

    def _validate_column_boundaries(self) -> None:
        """Validate column boundaries for common configuration issues.

        Checks for:
        1. Overlapping columns
        2. Extremely narrow columns (< 10 points)
        3. Columns exceeding page width (> 600 points)
        4. Missing Date column
        5. Large gaps between columns (> 50 points)

        Issues are logged as warnings (non-fatal) to maintain backward compatibility.
        """
        import logging

        logger = logging.getLogger(__name__)

        # Sort columns by x_start for overlap/gap detection
        sorted_cols = sorted(self.columns.items(), key=lambda item: item[1][0])

        # Check #1: Detect overlapping columns
        for i in range(len(sorted_cols) - 1):
            current_name, (current_start, current_end) = sorted_cols[i]
            next_name, (next_start, next_end) = sorted_cols[i + 1]

            if current_end > next_start:
                overlap = current_end - next_start
                logger.warning(
                    f"Column overlap detected: '{current_name}' [{current_start}, {current_end}] "
                    f"overlaps with '{next_name}' [{next_start}, {next_end}]. "
                    f"Overlap: {overlap:.1f} points. "
                    f"This may cause data extraction issues."
                )

        # Check #2: Detect extremely narrow columns
        MIN_COLUMN_WIDTH = 10  # 10 PDF points (~3.5mm)
        for col_name, (_x_start, x_end) in self.columns.items():
            width = x_end - _x_start
            if width < MIN_COLUMN_WIDTH:
                logger.warning(
                    f"Column '{col_name}' is very narrow: {width:.1f} points. "
                    f"May truncate data. Consider widening to at least {MIN_COLUMN_WIDTH} points."
                )

        # Check #3: Detect columns exceeding typical page width
        MAX_PAGE_WIDTH = 600  # A4 page is ~595 points wide
        for col_name, (_x_start, x_end) in self.columns.items():
            if x_end > MAX_PAGE_WIDTH:
                logger.warning(
                    f"Column '{col_name}' extends beyond typical page width: "
                    f"x_end={x_end:.1f} (A4 width ~595 points). "
                    f"May be misconfigured."
                )

        # Check #4: Ensure Date column exists (critical for sorting)
        date_col_candidates = [
            "Date",
            "Transaction Date",
            "Posting Date",
            "Date Posted",
            "Trans Date",
        ]
        has_date = any(
            any(candidate.lower() in col.lower() for candidate in date_col_candidates)
            for col in self.columns.keys()
        )
        if not has_date:
            logger.warning(
                f"No Date column found. Expected one containing: "
                f"{', '.join(date_col_candidates)}. "
                f"Date sorting may fail."
            )

        # Check #5: Detect large gaps between columns
        MAX_GAP = 50  # 50 points (~18mm)
        for i in range(len(sorted_cols) - 1):
            current_name, (_, current_end) = sorted_cols[i]
            next_name, (next_start, _) = sorted_cols[i + 1]
            gap = next_start - current_end

            if gap > MAX_GAP:
                logger.info(
                    f"Large gap detected between '{current_name}' and '{next_name}': "
                    f"{gap:.1f} points. May indicate missing column or misconfiguration."
                )


@dataclass
class TemplateProcessingConfig:
    """Configuration for processing transactions after extraction.

    Attributes:
        supports_multiline: Whether transactions can span multiple lines
        date_format: Expected date format (e.g., "%d/%m/%Y")
        currency_symbol: Currency symbol used (e.g., "€")
        decimal_separator: Decimal separator character (e.g., ".")
        transaction_types: Dictionary mapping transaction type names to keyword lists
                          (e.g., {"purchase": ["POS", "CONTACTLESS"], "payment": ["PAYMENT"]})
    """

    supports_multiline: bool = False
    date_format: str = "%d/%m/%Y"
    currency_symbol: str = ""
    decimal_separator: str = "."
    transaction_types: dict[str, list[str]] = field(default_factory=dict)


DocumentType = Literal["bank_statement", "credit_card_statement", "other"]


@dataclass
class BankTemplate:
    """Complete bank statement template definition.

    Attributes:
        id: Unique identifier for the template (e.g., "aib", "revolut")
        name: Human-readable name (e.g., "Allied Irish Banks")
        enabled: Whether this template is active
        detection: Detection configuration
        extraction: Extraction configuration
        processing: Processing configuration
        document_type: Type of financial document (bank_statement, credit_card_statement, other)
    """

    id: str
    name: str
    enabled: bool
    detection: TemplateDetectionConfig
    extraction: TemplateExtractionConfig
    processing: TemplateProcessingConfig = field(
        default_factory=TemplateProcessingConfig
    )
    document_type: DocumentType = "bank_statement"

    def __post_init__(self) -> None:
        """Validate template configuration."""
        if not self.id:
            raise ValueError("Template id cannot be empty")

        if not self.name:
            raise ValueError("Template name cannot be empty")

        # Ensure at least one detection method is configured
        has_detection = (
            self.detection.iban_patterns
            or self.detection.filename_patterns
            or self.detection.header_keywords
            or self.detection.column_headers
        )

        if not has_detection:
            raise ValueError(
                f"Template '{self.id}' must have at least one detection method configured"
            )
