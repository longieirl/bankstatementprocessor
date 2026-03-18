"""Processing facade for simplified bank statement processing.

This module provides a Facade pattern implementation that simplifies
the high-level interface for processing bank statements by hiding
the complexity of configuration, factory creation, and error handling.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from bankstatements_core.config.app_config import AppConfig, ConfigurationError
from bankstatements_core.entitlements import EntitlementError, Entitlements
from bankstatements_core.pdf_table_extractor import get_columns_config

if TYPE_CHECKING:
    from bankstatements_core.processor import BankStatementProcessor

logger = logging.getLogger(__name__)


class BankStatementProcessingFacade:
    """
    Facade for bank statement processing operations.

    Provides a simplified interface that hides the complexity of:
    - Configuration loading and validation
    - Processor factory creation
    - Directory setup
    - Error handling and logging
    """

    def __init__(
        self,
        config: AppConfig | None = None,
        entitlements: Entitlements | None = None,
    ):
        """
        Initialize the processing facade.

        Args:
            config: Optional configuration. If None, loads from environment.
            entitlements: Optional entitlements. If None, uses FREE tier.
        """
        self.config = config
        self.entitlements = entitlements or Entitlements.free_tier()
        self._processor: "BankStatementProcessor" | None = None

    @classmethod
    def from_environment(
        cls, entitlements: Entitlements | None = None
    ) -> "BankStatementProcessingFacade":
        """
        Create facade from environment variables.

        Args:
            entitlements: Optional entitlements. If None, uses FREE tier.

        Returns:
            Configured facade instance

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Load configuration using singleton
        # ConfigurationError will propagate to caller
        from bankstatements_core.patterns.repositories import get_config_singleton

        try:
            config = get_config_singleton()
            logger.info("Loaded configuration from environment")
            return cls(config, entitlements)
        except ConfigurationError:
            # Re-raise ConfigurationError to be handled by caller
            raise

    def process_all(self) -> dict[str, Any]:
        """
        Process all bank statement PDFs with simplified interface.

        This method handles all the complexity of:
        - Output directory creation
        - Configuration logging
        - Column configuration loading
        - Processor creation via factory
        - Running the processing
        - Returning summary

        Returns:
            Dictionary containing processing summary with statistics

        Raises:
            ConfigurationError: If configuration is invalid
            FileNotFoundError: If required files or directories are missing
            PermissionError: If insufficient permissions
            Exception: For other processing errors
        """
        if self.config is None:
            raise ConfigurationError(
                "Configuration not loaded. Use from_environment()."
            )

        # Create output directory
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Created output directory: %s", self.config.output_dir)

        # Log configuration
        self.config.log_configuration()

        # Enforce entitlements for configured features
        logger.info(f"Enforcing {self.entitlements.tier} tier entitlements")

        # Check recursive scan entitlement
        if self.config.recursive_scan:
            try:
                self.entitlements.check_recursive_scan()
            except EntitlementError as e:
                logger.error(str(e))
                raise ConfigurationError(str(e)) from e

        # Check monthly summary entitlement
        if self.config.generate_monthly_summary:
            try:
                self.entitlements.check_monthly_summary()
            except EntitlementError as e:
                logger.error(str(e))
                raise ConfigurationError(str(e)) from e

        # Check output format entitlements
        for format_name in self.config.output_formats:
            try:
                self.entitlements.check_output_format(format_name)
            except EntitlementError as e:
                logger.error(str(e))
                raise ConfigurationError(str(e)) from e

        # Load column configuration
        try:
            columns = get_columns_config()
            logger.info("Using columns: %s", list(columns.keys()))
        except (ValueError, KeyError, FileNotFoundError) as e:
            # Expected errors: invalid config format, missing keys, missing config file
            logger.error("Failed to load column configuration: %s", e)
            raise ConfigurationError(f"Column configuration error: {e}") from e
        # Let unexpected errors bubble up

        # Create processing activity log for GDPR audit trail
        from bankstatements_core.services.processing_activity_log import (
            ProcessingActivityLog,
        )

        activity_log = ProcessingActivityLog(self.config.logs_dir)

        # Create processor using factory
        from bankstatements_core.patterns.factories import ProcessorFactory

        self._processor = ProcessorFactory.create_from_config(
            self.config, activity_log=activity_log, entitlements=self.entitlements
        )
        logger.info("Created processor via factory")

        # Run processing
        summary = self._processor.run()
        logger.info("Processing completed successfully")

        # Auto cleanup if enabled
        if self.config.auto_cleanup_on_exit:
            logger.info("Auto cleanup enabled, deleting output files...")
            from bankstatements_core.services.data_retention import DataRetentionService

            service = DataRetentionService(0, self.config.output_dir)
            deleted_count = service.cleanup_all_files(audit_log=activity_log)
            logger.info("Deleted %d files", deleted_count)

        return summary

    def process_with_error_handling(self) -> int:
        """
        Process all files with comprehensive error handling.

        This method wraps process_all() with error handling and
        returns appropriate exit codes for different error types.

        Returns:
            Exit code: 0 for success, non-zero for various failure types
                1 - Configuration error
                2 - File not found error
                3 - Permission error
                4 - Unexpected error
                130 - User interrupt (Ctrl+C)
        """
        try:
            summary = self.process_all()
            from bankstatements_core.utils import log_summary

            log_summary(summary)
            return 0

        except ConfigurationError as e:
            logger.error("Configuration error: %s", e)
            return 1

        except FileNotFoundError as e:
            logger.error("File not found: %s", e)
            return 2

        except PermissionError as e:
            logger.error("Permission denied: %s", e)
            return 3

        except EntitlementError as e:
            logger.error("Entitlement error: %s", e)
            return 5

        except KeyboardInterrupt:
            logger.info("Processing interrupted by user")
            return 130  # Standard Unix exit code for SIGINT

        except Exception as e:
            # Final safety net for truly unexpected errors
            # This should only catch system errors, not domain errors
            logger.exception("Unexpected error during processing: %s", e)
            return 4
