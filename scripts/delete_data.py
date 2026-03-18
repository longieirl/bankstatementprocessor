#!/usr/bin/env python3
"""CLI tool for deleting output files (GDPR Article 17: Right to Erasure)."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports  # noqa: E402
sys.path.insert(0, str(Path(__file__).parent.parent))  # noqa: E402

from src.app import AppConfig  # noqa: E402
from src.services.data_retention import DataRetentionService  # noqa: E402

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def confirm_deletion(message: str) -> bool:
    """
    Prompt user for confirmation.

    Args:
        message: Message to display

    Returns:
        True if user confirms, False otherwise
    """
    response = input(f"{message} (yes/no): ").strip().lower()
    return response == "yes"


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Delete output files for GDPR compliance (Article 17: Right to Erasure)"
    )
    parser.add_argument("--all", action="store_true", help="Delete all output files")
    parser.add_argument(
        "--older-than",
        type=int,
        metavar="DAYS",
        help="Delete files older than N days",
    )
    parser.add_argument(
        "--date-range",
        nargs=2,
        metavar=("START", "END"),
        help="Delete files within date range (YYYY-MM-DD format)",
    )
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Load configuration
    try:
        config = AppConfig.from_env()
    except Exception as e:
        logger.error("Failed to load configuration: %s", e)
        return 1

    # Create service
    service = DataRetentionService(config.data_retention_days, config.output_dir)

    # Validate arguments
    if not any([args.all, args.older_than, args.date_range]):
        parser.error("Must specify --all, --older-than, or --date-range")

    # Delete all files
    if args.all:
        if not args.force:
            if not confirm_deletion(
                "⚠️  This will delete ALL output files. Are you sure?"
            ):
                logger.info("Deletion cancelled")
                return 0

        logger.info("Deleting all output files...")
        deleted_count = service.cleanup_all_files()
        logger.info("✅ Deleted %d files", deleted_count)
        return 0

    # Delete files older than N days
    if args.older_than:
        days = args.older_than
        if days <= 0:
            parser.error("--older-than must be positive")

        if not args.force:
            expired_files = service.find_expired_files()
            if expired_files:
                logger.info("Files to be deleted:")
                for f in expired_files:
                    logger.info("  - %s", f.name)
                if not confirm_deletion(
                    f"⚠️  This will delete {len(expired_files)} files older than {days} days. Continue?"
                ):
                    logger.info("Deletion cancelled")
                    return 0
            else:
                logger.info("No files older than %d days found", days)
                return 0

        # Temporarily override retention days for this operation
        service.retention_days = days
        logger.info("Deleting files older than %d days...", days)
        deleted_count = service.cleanup_expired_files()
        logger.info("✅ Deleted %d files", deleted_count)
        return 0

    # Delete by date range
    if args.date_range:
        try:
            start_date = datetime.strptime(args.date_range[0], "%Y-%m-%d")
            end_date = datetime.strptime(args.date_range[1], "%Y-%m-%d")
        except ValueError as e:
            parser.error(f"Invalid date format: {e}. Use YYYY-MM-DD")

        if start_date > end_date:
            parser.error("Start date must be before end date")

        if not args.force:
            if not confirm_deletion(
                f"⚠️  This will delete files between {args.date_range[0]} and {args.date_range[1]}. Continue?"
            ):
                logger.info("Deletion cancelled")
                return 0

        logger.info(
            "Deleting files between %s and %s...",
            args.date_range[0],
            args.date_range[1],
        )
        deleted_count = service.cleanup_by_date(start_date, end_date)
        logger.info("✅ Deleted %d files", deleted_count)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
