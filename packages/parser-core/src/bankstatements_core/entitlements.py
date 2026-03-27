"""Entitlements system for tier-based feature access control.

This module defines the entitlement tiers (FREE/PAID) and controls which features
are available in each tier.

Enforcement map — where each field is enforced in the call stack:

  require_iban          -> ExtractionOrchestrator._initialize_template_system()
  check_recursive_scan  -> BankStatementProcessingFacade._run()  (primary)
                           PDFDiscoveryService                    (defense in depth, intentional)
  check_monthly_summary -> BankStatementProcessingFacade._run()  (primary)
                           MonthlySummaryService.generate()       (defense in depth, intentional)
  check_output_format   -> BankStatementProcessingFacade._run()
  check_expense_analysis -> ExpenseAnalysisService
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Tier definition
Tier = Literal["FREE", "PAID"]


class EntitlementError(Exception):
    """Exception raised when a feature is accessed without proper entitlements."""

    pass


@dataclass(frozen=True)
class Entitlements:
    """
    Defines what features are available for a given tier.

    Attributes:
        tier: The entitlement tier (FREE or PAID)
        allow_recursive_scan: Whether recursive directory scanning is allowed
        allowed_output_formats: Set of allowed output formats (e.g., {"csv"})
        allow_monthly_summary: Whether monthly summary generation is allowed
        allow_expense_analysis: Whether expense analysis generation is allowed
        require_iban: Whether PDFs must have IBANs to be processed
    """

    tier: Tier
    allow_recursive_scan: bool
    allowed_output_formats: set[str]
    allow_monthly_summary: bool
    allow_expense_analysis: bool
    require_iban: bool

    @classmethod
    def free_tier(cls) -> Entitlements:
        """
        Create FREE tier entitlements.

        FREE tier includes:
        - All output formats (CSV, JSON, Excel/XLSX)
        - Recursive directory scanning
        - Monthly summaries
        - Expense analysis
        - IBAN required (templates without IBAN patterns are ignored)
        """
        return cls(
            tier="FREE",
            allow_recursive_scan=True,
            allowed_output_formats={"csv", "json", "excel", "xlsx"},
            allow_monthly_summary=True,
            allow_expense_analysis=True,
            require_iban=True,
        )

    @classmethod
    def paid_tier(cls) -> Entitlements:
        """
        Create PAID tier entitlements.

        PAID tier includes:
        - All FREE tier features
        - IBAN not required (can process credit card statements and templates without IBAN patterns)
        """
        return cls(
            tier="PAID",
            allow_recursive_scan=True,
            allowed_output_formats={"csv", "json", "excel", "xlsx"},
            allow_monthly_summary=True,
            allow_expense_analysis=True,
            require_iban=False,
        )

    def check_output_format(self, format_name: str) -> None:
        """
        Check if a given output format is allowed.

        Args:
            format_name: The format to check (e.g., "csv", "json", "xlsx")

        Raises:
            EntitlementError: If the format is not allowed in this tier
        """
        if format_name.lower() not in self.allowed_output_formats:
            raise EntitlementError(
                f"Output format '{format_name}' is not available in {self.tier} tier. "
                f"Allowed formats: {', '.join(sorted(self.allowed_output_formats))}"
            )

    def check_monthly_summary(self) -> None:
        """
        Check if monthly summary generation is allowed.

        Raises:
            EntitlementError: If monthly summaries are not allowed in this tier
        """
        if not self.allow_monthly_summary:
            raise EntitlementError(
                f"Monthly summary generation is not available in {self.tier} tier. "
                "Please upgrade to PAID tier to access this feature."
            )

    def check_recursive_scan(self) -> None:
        """
        Check if recursive directory scanning is allowed.

        Raises:
            EntitlementError: If recursive scanning is not allowed in this tier
        """
        if not self.allow_recursive_scan:
            raise EntitlementError(
                f"Recursive directory scanning is not available in {self.tier} tier. "
                "Please upgrade to PAID tier to access this feature."
            )

    def check_expense_analysis(self) -> None:
        """
        Check if expense analysis generation is allowed.

        Raises:
            EntitlementError: If expense analysis is not allowed in this tier
        """
        if not self.allow_expense_analysis:
            raise EntitlementError(
                f"Expense analysis generation is not available in {self.tier} tier. "
                "Please upgrade to PAID tier to access this feature."
            )
