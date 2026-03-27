"""Template JSON generation for PDF analysis results.

This module generates template configuration files based on analyzed PDF structure.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TemplateGenerator:
    """Generate template JSON configurations from analysis results."""

    def __init__(self, base_template_path: Path | None = None):
        """Initialize template generator.

        Args:
            base_template_path: Path to base template JSON file.
                              Defaults to templates/default.json
        """
        if base_template_path is None:
            # Default to templates/default.json
            base_template_path = (
                Path(__file__).parent.parent.parent / "templates" / "default.json"
            )

        self.base_template_path = base_template_path
        logger.debug(f"Using base template: {self.base_template_path}")

    def generate_template(
        self,
        columns: dict[str, tuple[float, float]],
        iban: str | None,
        table_top_y: float,
        table_bottom_y: float,
        page_height: float,
        template_id: str = "custom_generated",
        template_name: str = "Custom Template - Generated",
        page: Any | None = None,
    ) -> dict[str, Any]:
        """Generate template JSON from analysis results.

        Args:
            columns: Dictionary mapping column names to (x_min, x_max) boundaries
            iban: Detected IBAN (or None if not found)
            table_top_y: Top Y coordinate of transaction table
            table_bottom_y: Bottom Y coordinate of transaction table
            page_height: Height of PDF page
            template_id: ID for the generated template
            template_name: Display name for the template
            page: Optional pdfplumber page object for analyzing content patterns

        Returns:
            Dictionary representing complete template JSON
        """
        logger.debug("Generating template JSON")

        # Load base template
        try:
            with open(self.base_template_path) as f:
                template: dict[str, Any] = json.load(f)
                logger.debug(f"Loaded base template from {self.base_template_path}")
        except (OSError, ValueError, KeyError) as e:
            # Expected errors: file I/O errors, invalid JSON, missing keys
            # Use debug level since minimal template is fully functional
            logger.debug(f"Could not load base template: {e}, using minimal template")
            template = self._create_minimal_template()
        # Let unexpected errors bubble up

        # Update template ID and name
        template["id"] = template_id
        template["name"] = template_name

        # Update extraction config
        if "extraction" not in template:
            template["extraction"] = {}

        template["extraction"]["table_top_y"] = round(table_top_y)
        template["extraction"]["table_bottom_y"] = round(table_bottom_y)

        # Calculate header check Y
        # table_top_y already includes margin above header (header_y - 5 in table detection)
        # So header check should start slightly above table_top_y to catch the header row
        header_check_top_y = max(0, table_top_y - 10)
        template["extraction"]["header_check_top_y"] = round(header_check_top_y)
        template["extraction"]["enable_header_check"] = True

        # Update columns - round coordinates to whole numbers for cleaner JSON
        columns_json = {}
        for name, (x_min, x_max) in columns.items():
            columns_json[name] = [round(x_min), round(x_max)]
        template["extraction"]["columns"] = columns_json

        logger.debug(f"Updated extraction config with {len(columns_json)} columns")

        # Update detection config
        if "detection" not in template:
            template["detection"] = {}

        if iban:
            # Extract country code (first 2 chars)
            country_code = iban[:2]
            pattern = f"^{country_code}\\d{{2}}.*"
            template["detection"]["iban_patterns"] = [pattern]
            logger.debug(f"Added IBAN pattern: {pattern}")
            logger.info(f"  ✓ IBAN pattern added to template: {pattern}")
        else:
            # No IBAN detected - leave patterns empty
            template["detection"]["iban_patterns"] = []
            logger.warning(
                "  ⚠️  No IBAN detected - template will have empty iban_patterns"
            )
            logger.warning(
                "  ⚠️  FREE tier requires IBAN patterns. To use this template with FREE tier:"
            )
            logger.warning(
                "     1. Manually add IBAN pattern to template JSON (e.g., 'IE.*' for Irish banks)"
            )
            logger.warning(
                "     2. OR: Use CUSTOM_TEMPLATES_DIR instead of BANK_TEMPLATES_DIR"
            )
            logger.warning("     3. OR: Upgrade to PAID tier (no IBAN requirement)")

        # Update column headers for detection
        template["detection"]["column_headers"] = list(columns.keys())

        # Detect date grouping pattern (supports_multiline)
        if page and "Date" in columns:
            supports_multiline = self._detect_date_grouping(
                page, columns["Date"], table_top_y, table_bottom_y
            )
            # Ensure processing section exists
            if "processing" not in template:
                template["processing"] = {
                    "supports_multiline": False,
                    "date_format": "%d/%m/%Y",
                    "currency_symbol": "",
                    "decimal_separator": ".",
                }
            # Update the setting
            template["processing"]["supports_multiline"] = supports_multiline

            if supports_multiline:
                logger.info(
                    "  ✓ Detected date grouping pattern: transactions grouped by date"
                )
                logger.info("    Set supports_multiline=true for date carry-forward")
            else:
                logger.debug("Date grouping not detected, supports_multiline=false")

        logger.info(f"Generated template '{template_name}' with {len(columns)} columns")

        return template

    def save_template(self, template: dict, output_path: Path) -> None:
        """Save template JSON to file.

        Creates or overwrites the file at output_path.

        Args:
            template: Template dictionary
            output_path: Path to save template JSON

        Raises:
            IOError: If unable to write file
        """
        logger.debug(f"Saving template to {output_path}")

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, "w") as f:
                json.dump(template, f, indent=2)
            logger.info(f"✓ Template saved successfully: {output_path}")
        except (OSError, TypeError) as e:
            # Expected errors: file I/O errors, JSON serialization errors
            logger.error(f"Failed to save template: {e}")
            raise OSError(f"Could not save template to {output_path}: {e}") from e
        # Let unexpected errors bubble up

    def _create_minimal_template(self) -> dict:
        """Create a minimal template structure if base template not available.

        Returns:
            Minimal template dictionary
        """
        return {
            "id": "minimal",
            "name": "Minimal Template",
            "enabled": True,
            "detection": {"iban_patterns": [], "column_headers": []},
            "extraction": {
                "table_top_y": 0,
                "table_bottom_y": 0,
                "enable_header_check": True,
                "header_check_top_y": 0,
                "columns": {},
            },
            "processing": {
                "supports_multiline": False,
                "date_format": "%d/%m/%Y",
                "currency_symbol": "",
                "decimal_separator": ".",
            },
        }

    def _detect_date_grouping(
        self,
        page: Any,
        date_column: tuple[float, float],
        table_top_y: float,
        table_bottom_y: float,
    ) -> bool:
        """Detect if transactions are grouped by date (sparse date pattern).

        Checks if some rows have dates while others don't, indicating a
        date-grouping format where the date appears once and subsequent
        transactions inherit it.

        Args:
            page: pdfplumber page object
            date_column: (x_min, x_max) tuple for Date column
            table_top_y: Top Y of table
            table_bottom_y: Bottom Y of table

        Returns:
            True if date grouping detected, False otherwise
        """
        from collections import defaultdict

        # Extract words in the Date column within table region
        x_min, x_max = date_column
        bbox = (x_min, table_top_y, x_max, table_bottom_y)
        cropped = page.within_bbox(bbox)
        words = cropped.extract_words()

        if not words:
            return False

        # Group words by Y position (rows)
        y_groups = defaultdict(list)
        for word in words:
            y_key = round(word["top"] / 5) * 5  # Group by 5px buckets
            y_groups[y_key].append(word)

        # Check for date-like patterns (numbers with slashes or month names)
        date_indicators = [
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
            "/",
        ]

        rows_with_dates = 0
        total_rows = len(y_groups)

        for _y_pos, words_at_y in y_groups.items():
            text = " ".join([w["text"].lower() for w in words_at_y])
            # Check if this row has date-like content
            has_date = any(indicator in text for indicator in date_indicators)
            if has_date:
                rows_with_dates += 1

        # If less than 60% of rows have dates, likely a grouped format
        if total_rows >= 3 and rows_with_dates > 0:
            date_ratio = rows_with_dates / total_rows
            logger.debug(
                f"Date grouping analysis: {rows_with_dates}/{total_rows} rows have dates "
                f"({date_ratio:.1%})"
            )

            if date_ratio < 0.6:
                logger.debug(
                    f"Detected sparse date pattern ({date_ratio:.1%} < 60%) - "
                    f"enabling date grouping support"
                )
                return True

        return False

    def format_template_for_display(self, template: dict) -> str:
        """Format template as pretty-printed JSON for logging.

        Args:
            template: Template dictionary

        Returns:
            Pretty-printed JSON string
        """
        return json.dumps(template, indent=2)
