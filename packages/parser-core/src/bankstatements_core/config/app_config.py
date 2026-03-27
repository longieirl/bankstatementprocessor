"""Application configuration with validation.

This module defines the core application configuration structure (AppConfig)
and related exceptions. It was extracted from app.py to break circular
dependencies with patterns/repositories.py and patterns/factories.py.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from bankstatements_core.config.environment_parser import EnvironmentParser

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when application configuration is invalid."""

    pass


@dataclass
class AppConfig:
    """
    Application configuration with validation.

    Loads configuration from environment variables and validates
    values before use to prevent runtime errors.
    """

    input_dir: Path
    output_dir: Path
    table_top_y: int = 300
    table_bottom_y: int = 720
    enable_dynamic_boundary: bool = False
    sort_by_date: bool = True
    recursive_scan: bool = True
    totals_columns: list[str] = field(default_factory=list)
    generate_monthly_summary: bool = True
    generate_expense_analysis: bool = True
    output_formats: list[str] = field(
        default_factory=lambda: ["csv", "json", "excel"]
    )  # All formats available in FREE tier
    data_retention_days: int = 0  # 0 = no limit
    auto_cleanup_on_exit: bool = False
    logs_dir: Path = field(default_factory=lambda: Path("logs"))

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_paths()
        self._validate_table_bounds()
        self._validate_output_formats()

    def _validate_paths(self) -> None:
        """Validate input and output directory configuration."""
        # Paths are already Path objects from from_env() or direct construction
        # Output directory should be writable (will be created if needed)
        # Input directory doesn't need to exist yet (PDFs might be added later)
        pass

    def _validate_table_bounds(self) -> None:
        """Validate table boundary values."""
        if self.table_top_y < 0:
            raise ConfigurationError(
                f"TABLE_TOP_Y must be non-negative, got {self.table_top_y}"
            )

        if self.table_bottom_y < 0:
            raise ConfigurationError(
                f"TABLE_BOTTOM_Y must be non-negative, got {self.table_bottom_y}"
            )

        if self.table_top_y >= self.table_bottom_y:
            raise ConfigurationError(
                f"TABLE_TOP_Y ({self.table_top_y}) must be less than "
                f"TABLE_BOTTOM_Y ({self.table_bottom_y})"
            )

        # Sanity check: PDF pages are typically 792 points tall
        if self.table_bottom_y > 1000:
            logger.warning(
                "TABLE_BOTTOM_Y=%d is unusually large (PDF pages are typically 792 points tall)",
                self.table_bottom_y,
            )

    def _validate_output_formats(self) -> None:
        """Validate output format configuration."""
        valid_formats = {"csv", "json", "excel"}

        if not self.output_formats:
            raise ConfigurationError("At least one output format must be specified")

        for fmt in self.output_formats:
            if fmt not in valid_formats:
                raise ConfigurationError(
                    f"Invalid output format '{fmt}'. "
                    f"Valid formats: {', '.join(sorted(valid_formats))}"
                )

    @classmethod
    def from_env(cls) -> AppConfig:
        """
        Load configuration from environment variables with validation.

        Returns:
            AppConfig instance with validated configuration

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Import here to avoid circular dependency during module load
        from bankstatements_core.config.totals_config import (  # noqa: PLC0415
            parse_totals_columns,
        )

        try:
            # Parse integer values with validation
            try:
                table_top_y = EnvironmentParser.parse_int("TABLE_TOP_Y", 300)
                table_bottom_y = EnvironmentParser.parse_int("TABLE_BOTTOM_Y", 720)
            except ValueError as e:
                raise ConfigurationError(str(e)) from e

            # Parse boolean values
            enable_dynamic_boundary = EnvironmentParser.parse_bool(
                "ENABLE_DYNAMIC_BOUNDARY", False
            )
            sort_by_date = EnvironmentParser.parse_bool("SORT_BY_DATE", True)
            recursive_scan = EnvironmentParser.parse_bool("RECURSIVE_SCAN", True)
            generate_monthly_summary = EnvironmentParser.parse_bool(
                "GENERATE_MONTHLY_SUMMARY", True
            )
            generate_expense_analysis = EnvironmentParser.parse_bool(
                "GENERATE_EXPENSE_ANALYSIS", True
            )

            # Parse totals configuration
            totals_config = os.getenv("TOTALS_COLUMNS", "debit,credit")
            try:
                totals_columns = (
                    parse_totals_columns(totals_config) if totals_config else []
                )
            except (ValueError, KeyError, TypeError) as e:
                raise ConfigurationError(
                    f"Invalid TOTALS_COLUMNS configuration '{totals_config}': {e}"
                ) from e

            # Parse output formats configuration
            # Special handling: if OUTPUT_FORMATS is explicitly set to empty,
            # we should not use the default (this is an error case)
            output_formats_env = os.getenv("OUTPUT_FORMATS")
            if output_formats_env is None:
                # Not set at all - use FREE tier compatible default (CSV only)
                # This ensures out-of-the-box FREE tier usage works without configuration
                output_formats = ["csv"]
            else:
                # Explicitly set - parse it (could be empty list if string is empty)
                output_formats = [
                    fmt.lower()
                    for fmt in EnvironmentParser.parse_csv_list("OUTPUT_FORMATS", [])
                ]

            # Get directory paths with PROJECT_ROOT support
            # PROJECT_ROOT: Optional base directory for all paths (default: current working directory)
            # If INPUT_DIR/OUTPUT_DIR/LOGS_DIR are absolute, PROJECT_ROOT is ignored
            # If they are relative, they are resolved relative to PROJECT_ROOT
            project_root_str = os.getenv("PROJECT_ROOT")
            project_root = Path(project_root_str) if project_root_str else Path.cwd()

            # Helper function to resolve paths with PROJECT_ROOT support
            def resolve_dir(env_var: str, default: str) -> Path:
                """Resolve directory path with PROJECT_ROOT support.

                Args:
                    env_var: Environment variable name
                    default: Default relative path

                Returns:
                    Resolved Path object
                """
                path_str = os.getenv(env_var, default)
                path = Path(path_str)

                # If absolute path, use as-is (ignore PROJECT_ROOT)
                if path.is_absolute():
                    return path

                # If relative path, resolve relative to PROJECT_ROOT
                return project_root / path

            input_dir = resolve_dir("INPUT_DIR", "input")
            output_dir = resolve_dir("OUTPUT_DIR", "output")
            logs_dir = resolve_dir("LOGS_DIR", "logs")

            # Parse data retention configuration
            data_retention_days = EnvironmentParser.parse_int("DATA_RETENTION_DAYS", 0)
            auto_cleanup_on_exit = EnvironmentParser.parse_bool(
                "AUTO_CLEANUP_ON_EXIT", False
            )

            return cls(
                input_dir=input_dir,
                output_dir=output_dir,
                table_top_y=table_top_y,
                table_bottom_y=table_bottom_y,
                enable_dynamic_boundary=enable_dynamic_boundary,
                sort_by_date=sort_by_date,
                recursive_scan=recursive_scan,
                totals_columns=totals_columns,
                generate_monthly_summary=generate_monthly_summary,
                generate_expense_analysis=generate_expense_analysis,
                output_formats=output_formats,
                data_retention_days=data_retention_days,
                auto_cleanup_on_exit=auto_cleanup_on_exit,
                logs_dir=logs_dir,
            )

        except ConfigurationError:
            raise
        except (ValueError, TypeError, AttributeError, OSError, RuntimeError) as e:
            # Expected errors: validation failures, type errors, attribute errors, file system errors, runtime errors
            raise ConfigurationError(f"Failed to load configuration: {e}") from e
        # Let truly unexpected errors (like MemoryError, SystemError) bubble up

    def log_configuration(self) -> None:
        """Log current configuration in a structured way."""
        logger.info("========== CONFIGURATION ==========")
        logger.info("Input directory: %s", self.input_dir)
        logger.info("Output directory: %s", self.output_dir)
        logger.info("Table bounds: Y=%d to %d", self.table_top_y, self.table_bottom_y)
        logger.info(
            "Dynamic boundary detection: %s",
            "ENABLED" if self.enable_dynamic_boundary else "DISABLED",
        )
        logger.info(
            "Chronological date sorting: %s",
            "ENABLED" if self.sort_by_date else "DISABLED",
        )
        logger.info(
            "Column totals: %s",
            ", ".join(self.totals_columns) if self.totals_columns else "DISABLED",
        )
        logger.info(
            "Monthly summary generation: %s",
            "ENABLED" if self.generate_monthly_summary else "DISABLED",
        )
        logger.info(
            "Expense analysis generation: %s",
            "ENABLED" if self.generate_expense_analysis else "DISABLED",
        )
        logger.info("Output formats: %s", ", ".join(self.output_formats))
        logger.info(
            "Data retention: %s",
            (
                f"{self.data_retention_days} days"
                if self.data_retention_days > 0
                else "No limit"
            ),
        )
        logger.info(
            "Auto cleanup on exit: %s",
            "ENABLED" if self.auto_cleanup_on_exit else "DISABLED",
        )
        logger.info("===================================")
