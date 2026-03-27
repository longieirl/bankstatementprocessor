"""Main application entry point for bank statement processing (FREE tier)."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from bankstatements_core.config.app_config import AppConfig, ConfigurationError
from bankstatements_core.entitlements import Entitlements

logger = logging.getLogger(__name__)

__all__ = [
    "AppConfig",
    "ConfigurationError",
    "log_summary",
    "main",
    "resolve_entitlements",
    "setup_logging",
]


def resolve_entitlements() -> Entitlements:
    """Return FREE tier entitlements (no license required)."""
    return Entitlements.free_tier()


def setup_logging() -> None:
    """Configure logging from environment variables."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if log_level not in valid_levels:
        log_level = "INFO"
        logger.warning(
            "Invalid LOG_LEVEL '%s', using INFO. Valid levels: %s",
            os.getenv("LOG_LEVEL"),
            ", ".join(valid_levels),
        )

    class _ShortNameFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            record.name = record.name.rsplit(".", 1)[-1]
            return super().format(record)

    handler = logging.StreamHandler()
    handler.setFormatter(
        _ShortNameFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logging.root.setLevel(getattr(logging, log_level))
    logging.root.handlers = [handler]


def log_summary(summary: dict) -> None:
    """Log processing summary in structured format."""
    logger.info("========== SUMMARY ==========")
    logger.info("PDFs read: %d", summary["pdf_count"])
    logger.info(
        "PDFs extracted: %d", summary.get("pdfs_extracted", summary["pdf_count"])
    )
    logger.info("Pages read: %d", summary["pages_read"])
    logger.info("Unique transactions: %d", summary["transactions"])
    logger.info("Duplicate transactions: %d", summary["duplicates"])

    if "csv_path" in summary:
        logger.info("CSV output: %s", summary["csv_path"])
    if "json_path" in summary:
        logger.info("JSON output: %s", summary["json_path"])
    if "excel_path" in summary:
        logger.info("Excel output: %s", summary["excel_path"])

    if "duplicates_path" in summary:
        logger.info("Duplicates output: %s", summary["duplicates_path"])
    if "monthly_summary_path" in summary:
        logger.info("Monthly summary output: %s", summary["monthly_summary_path"])

    logger.info("=============================")


def main(argv: list[str] | None = None) -> int:
    """Main application entry point.

    Args:
        argv: Command line arguments (default: None, uses sys.argv)

    Returns:
        Exit code: 0 for success, non-zero for failure
    """
    import argparse  # noqa: PLC0415

    from bankstatements_core.__version__ import __version__  # noqa: PLC0415
    from bankstatements_core.facades import (  # noqa: PLC0415
        BankStatementProcessingFacade,
    )

    parser = argparse.ArgumentParser(
        prog="bankstatements", description="Bank Statement Processor"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument("--config", help="Path to config file (optional)")
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize directory structure (input, output, logs, custom_templates)",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        help="Base directory for --init command (default: current directory)",
    )
    parser.add_argument(
        "--with-samples",
        action="store_true",
        help="Create sample configuration files when using --init",
    )

    args = parser.parse_args(argv)

    if args.init:
        from bankstatements_core.commands.init import init_directories  # noqa: PLC0415

        return init_directories(
            base_dir=args.base_dir,
            create_samples=args.with_samples,
            verbose=True,
        )

    setup_logging()

    try:
        entitlements = resolve_entitlements()
        facade = BankStatementProcessingFacade.from_environment(entitlements)
        return facade.process_with_error_handling()
    except ConfigurationError as e:
        logger.error("Configuration error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
