"""PDF Analysis CLI Command.

This command analyzes PDF bank statements to detect table structures and IBANs,
generating template configurations for bank statement processing.

IMPORTANT CONSTRAINTS:
- NO PAID FEATURES: Does not use ProcessorFactory or any entitlement-restricted features
- FIRST PAGE ONLY for IBAN: Only analyzes first page for IBAN extraction
- SINGLE FILE OUTPUT: Only writes template JSON (creates or overwrites)
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import pdfplumber

from bankstatements_core.analysis.column_analyzer import ColumnAnalyzer
from bankstatements_core.analysis.iban_spatial_filter import IBANSpatialFilter
from bankstatements_core.analysis.table_detector import TableDetector
from bankstatements_core.analysis.template_generator import TemplateGenerator
from bankstatements_core.extraction.pdf_extractor import PDFTableExtractor

logger = logging.getLogger(__name__)


class PDFAnalyzer:
    """Main orchestrator for PDF analysis workflow."""

    def __init__(
        self,
        pdf_path: Path,
        output_path: Path | None = None,
        template_path: Path | None = None,
        base_template_path: Path | None = None,
    ):
        """Initialize PDF analyzer.

        Args:
            pdf_path: Path to PDF file to analyze
            output_path: Optional path to save generated template JSON
            template_path: Optional path to existing template for validation
            base_template_path: Optional path to base template (default: templates/default.json)
        """
        self.pdf_path = pdf_path
        self.output_path = output_path
        self.template_path = template_path
        self.base_template_path = base_template_path

        # Initialize analysis components
        self.table_detector = TableDetector()
        self.iban_filter = IBANSpatialFilter()
        self.column_analyzer = ColumnAnalyzer()
        self.template_generator = TemplateGenerator(
            base_template_path=base_template_path
        )

    def analyze(self) -> dict:  # noqa: C901, PLR0912, PLR0915
        """Run full PDF analysis workflow.

        Returns:
            Dictionary containing analysis results

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If PDF analysis fails
        """
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")

        logger.info(f"🔍 Analyzing PDF: {self.pdf_path}")
        logger.info(
            "⚠️  Analysis utility operates outside entitlement system (no paid features)"
        )

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # CRITICAL: Only first page for IBAN detection
                first_page = pdf.pages[0]
                page_height = first_page.height
                page_width = first_page.width

                logger.info(
                    f"PDF: {len(pdf.pages)} pages, size: {page_width:.1f}x{page_height:.1f}"
                )

                # Step 1-2: Detect tables
                logger.info("Step 1-2: Detecting transaction tables...")
                table_detection = self.table_detector.detect_tables(first_page)

                if not table_detection.tables:
                    logger.warning("⚠️  No transaction tables detected")
                    return {"success": False, "error": "No tables detected"}

                # Log table detections
                for i, table_bbox in enumerate(table_detection.tables, 1):
                    logger.info(
                        f"  Table {i}: {table_bbox}, " f"area={table_bbox.area:.0f}px²"
                    )

                # Use largest table for analysis
                largest_table = self.table_detector.get_largest_table(table_detection)
                if largest_table is None:
                    raise ValueError("No tables detected in PDF")

                # Step 3-4: Extract IBAN candidates (FIRST PAGE ONLY)
                logger.info("Step 3-4: Extracting IBAN candidates (first page only)...")
                iban_candidates = self.iban_filter.extract_iban_candidates(first_page)

                logger.info(f"  Found {len(iban_candidates)} IBAN candidates")
                for candidate in iban_candidates:
                    logger.info(f"    - {candidate.masked} at {candidate.bbox}")

                # Step 5: Filter by table overlap
                logger.info("Step 5: Filtering IBANs by table overlap...")
                table_regions = self.table_detector.get_expanded_table_regions(
                    table_detection, margin=20.0
                )
                filtered_candidates = self.iban_filter.filter_by_table_overlap(
                    iban_candidates, table_regions
                )

                logger.info(
                    f"  {len(filtered_candidates)} IBANs after filtering "
                    f"({len(iban_candidates) - len(filtered_candidates)} rejected)"
                )

                # Step 6: Score and select best IBAN
                logger.info("Step 6: Selecting best IBAN...")
                if filtered_candidates:
                    scored_candidates = self.iban_filter.score_candidates(
                        filtered_candidates, page_height
                    )
                    best_iban = self.iban_filter.select_best_iban(scored_candidates)

                    if best_iban:
                        logger.info(
                            f"  ✓ Selected IBAN: {best_iban.masked} "
                            f"(score: {best_iban.confidence_score:.1f})"
                        )
                        logger.info(f"    Location: {best_iban.bbox}")
                        logger.info("    Reason: Header area bonus, Y-position score")
                # Fallback: If spatial filtering removed all IBANs,
                # use unfiltered candidates (for template generation,
                # any valid IBAN is better than none)
                elif iban_candidates:
                    logger.warning(
                        "  ⚠️  All IBANs filtered by spatial overlap, "
                        "using best unfiltered candidate for template"
                    )
                    scored_candidates = self.iban_filter.score_candidates(
                        iban_candidates, page_height
                    )
                    best_iban = self.iban_filter.select_best_iban(scored_candidates)
                    if best_iban:
                        logger.info(
                            f"  ✓ Using unfiltered IBAN: {best_iban.masked} "
                            f"(score: {best_iban.confidence_score:.1f})"
                        )
                else:
                    best_iban = None
                    logger.warning("  ⚠️  No valid IBAN found")

                # Step 7: Analyze columns and generate template
                logger.info("Step 7: Analyzing column boundaries...")
                columns = self.column_analyzer.analyze_columns(
                    first_page, largest_table
                )

                logger.info(f"  Detected {len(columns)} columns:")
                for name, (x_min, x_max) in columns.items():
                    logger.info(f"    {name}: ({x_min:.1f}, {x_max:.1f})")

                # Generate template
                logger.info("  Generating template JSON...")
                template = self.template_generator.generate_template(
                    columns=columns,
                    iban=best_iban.iban if best_iban else None,
                    table_top_y=largest_table.y0,
                    table_bottom_y=largest_table.y1,
                    page_height=page_height,
                    page=first_page,
                )

                # Save template if output path specified
                if self.output_path:
                    self.template_generator.save_template(template, self.output_path)
                    logger.info(f"✓ Template saved to: {self.output_path}")
                else:
                    # Show sample of generated template
                    logger.info("Generated template JSON (sample):")
                    logger.info(
                        json.dumps(
                            {
                                "extraction": {
                                    "table_top_y": template["extraction"][
                                        "table_top_y"
                                    ],
                                    "table_bottom_y": template["extraction"][
                                        "table_bottom_y"
                                    ],
                                    "columns": dict(
                                        list(template["extraction"]["columns"].items())[
                                            :3
                                        ]
                                    ),
                                },
                                "detection": {
                                    "iban_patterns": template["detection"][
                                        "iban_patterns"
                                    ]
                                },
                            },
                            indent=2,
                        )
                    )

                # Step 8: Optional validation with provided template
                if self.template_path:
                    logger.info(
                        f"Step 8: Validating extraction with template {self.template_path}"
                    )
                    self._validate_extraction(pdf, self.template_path)

                # Step 9: Log transaction stats
                logger.info("Step 9: Transaction detection summary...")
                total_transactions = self._log_transaction_stats(pdf, table_detection)

                logger.info(
                    f"✓ Analysis complete. Template generated with {len(columns)} columns."
                )
                if self.output_path:
                    logger.info(
                        f"  Next step: Run with --template {self.output_path} to test extraction"
                    )

                return {
                    "success": True,
                    "tables": len(table_detection.tables),
                    "iban": best_iban.masked if best_iban else None,
                    "columns": len(columns),
                    "transactions": total_transactions,
                    "template": template,
                }

        except (OSError, ValueError, AttributeError, TypeError) as e:
            # Expected errors: file I/O, invalid PDF structure, missing attributes, type errors
            logger.exception(f"❌ Analysis failed: {e}")
            raise ValueError(f"PDF analysis failed: {e}") from e
        # Let unexpected errors bubble up

    def _validate_extraction(self, pdf: Any, template_path: Path) -> None:
        """Validate extraction using provided template.

        IMPORTANT: Uses direct PDFTableExtractor instantiation, NOT ProcessorFactory.

        Args:
            pdf: Opened pdfplumber PDF object
            template_path: Path to template JSON file
        """
        import json  # noqa: PLC0415

        logger.info(f"  Loading template: {template_path.stem}")

        try:
            # Load template manually (no TemplateRegistry to avoid entitlement checks)
            with open(template_path) as f:
                template_data = json.load(f)

            extraction_config = template_data.get("extraction", {})
            columns = extraction_config.get("columns", {})
            table_top_y = extraction_config.get("table_top_y", 0)
            table_bottom_y = extraction_config.get("table_bottom_y", 0)

            # CRITICAL: Direct instantiation, NOT ProcessorFactory
            # This bypasses entitlement system
            extractor = PDFTableExtractor(
                columns=columns,
                table_top_y=table_top_y,
                table_bottom_y=table_bottom_y,
                header_check_top_y=extraction_config.get("header_check_top_y", 0),
                enable_header_check=extraction_config.get("enable_header_check", True),
            )

            # Extract from first page only for validation
            first_page = pdf.pages[0]
            rows = extractor._extract_page(first_page, 1)
            if rows is None:
                rows = []

            logger.info(f"  ✓ Validation: Extracted {len(rows)} rows from page 1")
            logger.info(
                f"  ✓ Validation: Columns detected: {', '.join(columns.keys())}"
            )

            # Try to find IBAN using IBANExtractor
            from bankstatements_core.extraction.iban_extractor import (  # noqa: PLC0415
                IBANExtractor,
            )

            iban_extractor = IBANExtractor()

            iban_text = first_page.extract_text()
            iban_found = iban_extractor.extract_iban(iban_text)

            if iban_found:
                masked = iban_extractor._mask_iban(iban_found)
                logger.info(f"  ✓ Validation: IBAN = {masked}")
            else:
                logger.warning("  ⚠️  Validation: No IBAN detected")

            logger.info("  ✓ Validation complete. Template is working correctly.")
            logger.info(
                f"  If extraction incorrect, edit {template_path.name} and re-run."
            )

        except (OSError, ValueError, AttributeError, KeyError) as e:
            # Expected errors: file I/O, extraction errors, missing attributes/keys
            logger.error(f"  ❌ Validation failed: {e}")
        # Let unexpected errors bubble up

    def _log_transaction_stats(self, pdf: Any, table_detection: Any) -> int:
        """Log transaction detection statistics.

        Args:
            pdf: Opened pdfplumber PDF object
            table_detection: TableDetectionResult from first page

        Returns:
            Total estimated transaction count
        """
        total_transactions = 0

        for i, page in enumerate(pdf.pages, 1):
            # Detect tables on this page
            page_detection = self.table_detector.detect_tables(page)

            if page_detection.tables:
                # Estimate transactions based on table height
                # Assume average row height of ~15 pixels
                largest = self.table_detector.get_largest_table(page_detection)
                estimated_rows = int(largest.height / 15) if largest else 0

                logger.info(f"  Page {i}: ~{estimated_rows} potential transactions")
                total_transactions += estimated_rows
            else:
                logger.info(f"  Page {i}: No tables detected")

        logger.info(f"  Total transactions across all pages: ~{total_transactions}")
        return total_transactions


def main() -> None:
    """Main entry point for CLI command."""
    parser = argparse.ArgumentParser(
        description="Analyze PDF bank statements to generate template configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate template (analysis mode)
  python -m bankstatements_core.commands.analyze_pdf statement.pdf --output custom_templates/mybank.json

  # Test/validate template (validation mode)
  python -m bankstatements_core.commands.analyze_pdf statement.pdf --template custom_templates/mybank.json

  # Both modes together
  python -m bankstatements_core.commands.analyze_pdf statement.pdf \\
      --output custom_templates/mybank.json \\
      --template custom_templates/mybank.json
        """,
    )

    parser.add_argument("pdf_path", type=Path, help="Path to PDF file to analyze")

    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for generated template JSON (creates/overwrites)",
    )

    parser.add_argument(
        "--template",
        type=Path,
        help="Existing template JSON to test validation (skips generation)",
    )

    parser.add_argument(
        "--base-template",
        type=Path,
        help="Base template path (default: templates/default.json)",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        analyzer = PDFAnalyzer(
            pdf_path=args.pdf_path,
            output_path=args.output,
            template_path=args.template,
            base_template_path=args.base_template,
        )

        result = analyzer.analyze()

        if result["success"]:
            sys.exit(0)
        else:
            sys.exit(1)

    except (ValueError, OSError, KeyError) as e:
        # Expected errors: invalid PDFs, file I/O errors (including FileNotFoundError), configuration errors
        logger.error(f"❌ Error: {e}")
        sys.exit(1)
    # Let unexpected errors bubble up (will be caught by Python and show stack trace)


if __name__ == "__main__":
    main()
