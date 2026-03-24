"""PDF table extraction facade (backward compatibility).

This module maintains backward compatibility by re-exporting functions
from the new extraction modules. The implementation has been split into:
- extraction_params.py: Constants and thresholds
- extraction_facade.py: Main extraction functions
- services/: Service classes for row classification, validation, etc.
"""

from __future__ import annotations

import logging
import warnings

import pdfplumber  # noqa: F401 - used by extraction module

warnings.warn(
    "bankstatements_core.pdf_table_extractor is a backward-compatibility shim "
    "and will be removed in a future version. "
    "Import directly from bankstatements_core.extraction.extraction_facade or "
    "bankstatements_core.services instead.",
    DeprecationWarning,
    stacklevel=2,
)

logger = logging.getLogger(__name__)

# Re-export column configuration (backward compatibility)
from bankstatements_core.config.column_config import (  # noqa: E402, F401
    DEFAULT_COLUMNS,
    get_column_names,
    get_columns_config,
    parse_columns_from_env,
)

# Re-export extraction functions (backward compatibility)
from bankstatements_core.extraction.extraction_facade import (  # noqa: E402, F401
    detect_table_end_boundary_smart,
    extract_tables_from_pdf,
)

# Direct service imports — replacing the three thin facade modules
# Re-export extraction parameters (backward compatibility)
from bankstatements_core.extraction.extraction_params import (  # noqa: E402, F401
    ADMINISTRATIVE_PATTERNS,
    CONTENT_DENSITY_THRESHOLD,
    ENABLE_PAGE_VALIDATION,
)
from bankstatements_core.extraction.extraction_params import (  # noqa: E402, F401
    MIN_COLUMN_COVERAGE,
)
from bankstatements_core.extraction.extraction_params import (
    MIN_COLUMN_COVERAGE as _MIN_COLUMN_COVERAGE,
)
from bankstatements_core.extraction.extraction_params import MIN_HEADER_KEYWORDS
from bankstatements_core.extraction.extraction_params import (
    MIN_HEADER_KEYWORDS as _MIN_HEADER_KEYWORDS,
)
from bankstatements_core.extraction.extraction_params import MIN_TABLE_ROWS
from bankstatements_core.extraction.extraction_params import (
    MIN_TABLE_ROWS as _MIN_TABLE_ROWS,
)
from bankstatements_core.extraction.extraction_params import MIN_TRANSACTION_RATIO
from bankstatements_core.extraction.extraction_params import (
    MIN_TRANSACTION_RATIO as _MIN_TRANSACTION_RATIO,
)
from bankstatements_core.extraction.extraction_params import (  # noqa: E402, F401
    MIN_TRANSACTION_SCORE,
)
from bankstatements_core.extraction.extraction_params import REQUIRE_AMOUNT_COLUMN
from bankstatements_core.extraction.extraction_params import (
    REQUIRE_AMOUNT_COLUMN as _REQUIRE_AMOUNT_COLUMN,
)
from bankstatements_core.extraction.extraction_params import REQUIRE_DATE_COLUMN
from bankstatements_core.extraction.extraction_params import (
    REQUIRE_DATE_COLUMN as _REQUIRE_DATE_COLUMN,
)
from bankstatements_core.extraction.extraction_params import SLIDING_WINDOW_SIZE
from bankstatements_core.extraction.extraction_params import (
    SLIDING_WINDOW_SIZE as _SLIDING_WINDOW_SIZE,
)
from bankstatements_core.extraction.extraction_params import (  # noqa: E402, F401
    TABLE_BOTTOM_Y,
    TABLE_TOP_Y,
)
from bankstatements_core.extraction.row_classifiers import (  # noqa: E402, F401
    create_row_classifier_chain,
)
from bankstatements_core.services.content_density import (  # noqa: E402, F401
    ContentDensityService,
)
from bankstatements_core.services.header_detection import (  # noqa: E402, F401
    HeaderDetectionService,
)
from bankstatements_core.services.page_validation import (  # noqa: E402, F401
    PageValidationService,
)
from bankstatements_core.services.row_merger import RowMergerService  # noqa: E402, F401

# Module-level singletons (instantiated once, not per-call)
_PAGE_VALIDATION_SERVICE = PageValidationService(
    min_table_rows=_MIN_TABLE_ROWS,
    min_column_coverage=_MIN_COLUMN_COVERAGE,
    min_transaction_ratio=_MIN_TRANSACTION_RATIO,
    require_date_column=_REQUIRE_DATE_COLUMN,
    require_amount_column=_REQUIRE_AMOUNT_COLUMN,
)
_ROW_CLASSIFIER_CHAIN = create_row_classifier_chain()
_HEADER_SERVICE = HeaderDetectionService()
_ROW_MERGER_SERVICE = RowMergerService()
_CONTENT_DENSITY_SERVICE = ContentDensityService()


# Wrapper functions (backward compatibility)
def validate_page_structure(rows: list, columns: dict) -> bool:
    """Validate page structure (backward compatibility wrapper)."""
    return _PAGE_VALIDATION_SERVICE.validate_page_structure(rows, columns)


def calculate_column_coverage(rows: list, columns: dict) -> float:
    """Calculate column coverage (backward compatibility wrapper)."""
    return _PAGE_VALIDATION_SERVICE.calculate_column_coverage(rows, columns)


def has_column_type(
    columns: dict,
    required_types,
) -> bool:
    """Check if columns contain required types (backward compatibility wrapper)."""
    return _PAGE_VALIDATION_SERVICE.has_column_type(columns, required_types)


def detect_table_headers(words: list, columns: dict) -> bool:
    """Detect table headers (backward compatibility wrapper)."""
    return _HEADER_SERVICE.detect_headers(
        words, columns, min_keywords=_MIN_HEADER_KEYWORDS
    )


def merge_continuation_lines(rows: list, columns: dict) -> list:
    """Merge continuation lines (backward compatibility wrapper)."""
    return _ROW_MERGER_SERVICE.merge_continuation_lines(rows, columns)


def classify_row_type(row: dict, columns: dict) -> str:
    """Classify row type (backward compatibility wrapper)."""
    return _ROW_CLASSIFIER_CHAIN.classify(row, columns)


def analyze_content_density(
    word_groups: dict,
    columns: dict,
    window_size: int = _SLIDING_WINDOW_SIZE,
) -> list:
    """Calculate transaction density in sliding windows (backward compat wrapper).

    Note: per-call construction retained because window_size varies per caller.
    """
    return ContentDensityService(window_size=window_size).analyze_content_density(
        word_groups, columns
    )


# Implementation-detail helpers kept importable for legacy callers but removed
# from the explicit public list.
def _looks_like_date(text: str) -> bool:
    """Check if text looks like a valid date (backward compatibility wrapper)."""
    from bankstatements_core.services.row_analysis import RowAnalysisService

    service = RowAnalysisService()
    return service.looks_like_date(text)


def calculate_row_completeness_score(row: dict, columns: dict) -> float:
    """Score row completeness (backward compatibility wrapper)."""
    from bankstatements_core.services.row_analysis import RowAnalysisService

    service = RowAnalysisService()
    return service.calculate_row_completeness_score(row, columns)


# Explicitly list all public exports for backward compatibility
__all__ = [
    # Column configuration
    "DEFAULT_COLUMNS",
    "get_column_names",
    "get_columns_config",
    "parse_columns_from_env",
    # Extraction parameters
    "TABLE_TOP_Y",
    "TABLE_BOTTOM_Y",
    "CONTENT_DENSITY_THRESHOLD",
    "SLIDING_WINDOW_SIZE",
    "MIN_TRANSACTION_SCORE",
    "ENABLE_PAGE_VALIDATION",
    "MIN_TABLE_ROWS",
    "MIN_COLUMN_COVERAGE",
    "MIN_TRANSACTION_RATIO",
    "REQUIRE_DATE_COLUMN",
    "REQUIRE_AMOUNT_COLUMN",
    "MIN_HEADER_KEYWORDS",
    "ADMINISTRATIVE_PATTERNS",
    # Extraction functions
    "extract_tables_from_pdf",
    "detect_table_end_boundary_smart",
    # Row classification
    "classify_row_type",
    # Content analysis
    "analyze_content_density",
    # Validation
    "validate_page_structure",
    "calculate_column_coverage",
    "has_column_type",
    "detect_table_headers",
    "merge_continuation_lines",
]
