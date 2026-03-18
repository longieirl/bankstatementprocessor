"""PDF table extraction facade (backward compatibility).

This module maintains backward compatibility by re-exporting functions
from the new extraction modules. The implementation has been split into:
- extraction_params.py: Constants and thresholds
- extraction_facade.py: Main extraction functions
- row_classification_facade.py: Row classification
- content_analysis_facade.py: Content density analysis
- validation_facade.py: Page validation and header detection
"""

from __future__ import annotations

import logging

import pdfplumber  # noqa: F401 - used by extraction module

logger = logging.getLogger(__name__)

# Re-export column configuration (backward compatibility)
from bankstatements_core.config.column_config import (  # noqa: E402, F401
    DEFAULT_COLUMNS,
    get_column_names,
    get_columns_config,
    parse_columns_from_env,
)

# Re-export content analysis functions (backward compatibility)
from bankstatements_core.extraction.content_analysis_facade import (  # noqa: E402, F401
    analyze_content_density,
)

# Re-export extraction functions (backward compatibility)
from bankstatements_core.extraction.extraction_facade import (  # noqa: E402, F401
    detect_table_end_boundary_smart,
    extract_tables_from_pdf,
)

# Re-export extraction parameters (backward compatibility)
from bankstatements_core.extraction.extraction_params import (  # noqa: E402, F401
    ADMINISTRATIVE_PATTERNS,
    CONTENT_DENSITY_THRESHOLD,
    ENABLE_PAGE_VALIDATION,
    MIN_COLUMN_COVERAGE,
    MIN_HEADER_KEYWORDS,
    MIN_TABLE_ROWS,
    MIN_TRANSACTION_RATIO,
    MIN_TRANSACTION_SCORE,
    REQUIRE_AMOUNT_COLUMN,
    REQUIRE_DATE_COLUMN,
    SLIDING_WINDOW_SIZE,
    TABLE_BOTTOM_Y,
    TABLE_TOP_Y,
)

# Re-export row classification functions (backward compatibility)
from bankstatements_core.extraction.row_classification_facade import (  # noqa: E402, F401
    _looks_like_date,
    calculate_row_completeness_score,
    classify_row_type,
)

# Re-export validation functions (backward compatibility)
from bankstatements_core.extraction.validation_facade import (  # noqa: E402, F401
    calculate_column_coverage,
    detect_table_headers,
    has_column_type,
    merge_continuation_lines,
    validate_page_structure,
)

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
    "_looks_like_date",
    "calculate_row_completeness_score",
    # Content analysis
    "analyze_content_density",
    # Validation
    "validate_page_structure",
    "calculate_column_coverage",
    "has_column_type",
    "detect_table_headers",
    "merge_continuation_lines",
]
