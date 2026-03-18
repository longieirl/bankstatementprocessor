"""Transaction domain model for bank statement processing.

This module defines the core Transaction entity with validation and business logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation


@dataclass
class Transaction:
    """Domain model for a bank transaction.

    Represents a single transaction row from a bank statement with typed fields,
    validation, and business logic encapsulation.

    Attributes:
        date: Transaction date as string (format varies by bank)
        details: Transaction description/narrative
        debit: Debit amount (money out), None if credit transaction
        credit: Credit amount (money in), None if debit transaction
        balance: Account balance after transaction
        filename: Source PDF filename
        additional_fields: Dictionary for bank-specific custom columns

    Examples:
        >>> tx = Transaction(
        ...     date="01/12/2023",
        ...     details="TESCO STORES",
        ...     debit="45.23",
        ...     credit=None,
        ...     balance="1234.56",
        ...     filename="statement_20231201.pdf"
        ... )
        >>> tx.is_debit()
        True
        >>> tx.get_amount()
        Decimal('45.23')
    """

    date: str
    details: str
    debit: str | None
    credit: str | None
    balance: str | None
    filename: str
    additional_fields: dict[str, str] = field(default_factory=dict)

    def is_debit(self) -> bool:
        """Check if transaction is a debit (money out).

        Returns:
            True if transaction has debit amount, False otherwise
        """
        return self.debit is not None and self.debit.strip() != ""

    def is_credit(self) -> bool:
        """Check if transaction is a credit (money in).

        Returns:
            True if transaction has credit amount, False otherwise
        """
        return self.credit is not None and self.credit.strip() != ""

    def get_amount(self) -> Decimal | None:
        """Get transaction amount as Decimal.

        Returns:
            Decimal amount (positive for credit, negative for debit),
            or None if amount cannot be parsed

        Examples:
            >>> tx = Transaction(date="01/01/23", details="Test", debit="50.00",
            ...                  credit=None, balance="100.00", filename="test.pdf")
            >>> tx.get_amount()
            Decimal('-50.00')
        """
        try:
            if self.is_debit():
                # Clean amount string (remove currency symbols, spaces)
                amount_str = self._clean_amount_string(self.debit)  # type: ignore
                return -Decimal(amount_str)
            elif self.is_credit():
                amount_str = self._clean_amount_string(self.credit)  # type: ignore
                return Decimal(amount_str)
        except (InvalidOperation, ValueError, AttributeError):
            return None
        return None

    def get_balance(self) -> Decimal | None:
        """Get account balance as Decimal.

        Returns:
            Decimal balance, or None if balance cannot be parsed
        """
        if self.balance is None or self.balance.strip() == "":
            return None

        try:
            balance_str = self._clean_amount_string(self.balance)
            return Decimal(balance_str)
        except (InvalidOperation, ValueError, AttributeError):
            return None

    def _clean_amount_string(self, amount: str) -> str:
        """Clean amount string for Decimal conversion.

        Removes currency symbols, spaces, and other non-numeric characters.

        Args:
            amount: Amount string to clean

        Returns:
            Cleaned string suitable for Decimal conversion
        """
        if not amount:
            return "0"

        # Remove common currency symbols and spaces
        cleaned = amount.replace("€", "").replace("$", "").replace("£", "")
        cleaned = cleaned.replace(" ", "").replace(",", "")
        cleaned = cleaned.strip()

        return cleaned if cleaned else "0"

    def has_valid_date(self) -> bool:
        """Check if transaction has a non-empty date.

        Returns:
            True if date field is not empty
        """
        return bool(self.date and self.date.strip())

    def has_valid_details(self) -> bool:
        """Check if transaction has non-empty details.

        Returns:
            True if details field is not empty
        """
        return bool(self.details and self.details.strip())

    @classmethod
    def from_dict(cls, data: dict[str, str | None]) -> Transaction:
        """Create Transaction from dictionary.

        Handles various column naming conventions (with/without €, EUR suffix).

        Args:
            data: Dictionary with transaction data

        Returns:
            Transaction instance

        Examples:
            >>> data = {
            ...     "Date": "01/12/2023",
            ...     "Details": "Payment",
            ...     "Debit €": "50.00",
            ...     "Credit €": None,
            ...     "Balance €": "100.00",
            ...     "Filename": "test.pdf"
            ... }
            >>> tx = Transaction.from_dict(data)
            >>> tx.details
            'Payment'
        """
        # Handle various column naming conventions
        date = cls._get_value(data, ["Date", "date", "Transaction Date"])
        details = cls._get_value(
            data, ["Details", "details", "Description", "Narrative"]
        )
        debit = cls._get_value(data, ["Debit €", "Debit_EUR", "Debit", "Debit Amount"])
        credit = cls._get_value(
            data, ["Credit €", "Credit_EUR", "Credit", "Credit Amount"]
        )
        balance = cls._get_value(
            data, ["Balance €", "Balance_EUR", "Balance", "Running Balance"]
        )
        filename = cls._get_value(data, ["Filename", "filename", "source_pdf"]) or ""

        # Collect any additional fields not in standard schema
        standard_keys = {
            "Date",
            "date",
            "Transaction Date",
            "Details",
            "details",
            "Description",
            "Narrative",
            "Debit €",
            "Debit_EUR",
            "Debit",
            "Debit Amount",
            "Credit €",
            "Credit_EUR",
            "Credit",
            "Credit Amount",
            "Balance €",
            "Balance_EUR",
            "Balance",
            "Running Balance",
            "Filename",
            "filename",
            "source_pdf",
        }
        additional_fields = {
            k: str(v)
            for k, v in data.items()
            if k not in standard_keys and v is not None
        }

        return cls(
            date=date or "",
            details=details or "",
            debit=debit,
            credit=credit,
            balance=balance,
            filename=filename,
            additional_fields=additional_fields,
        )

    @staticmethod
    def _get_value(data: dict[str, str | None], keys: list[str]) -> str | None:
        """Get first matching value from dict using list of possible keys.

        Args:
            data: Dictionary to search
            keys: List of possible key names

        Returns:
            First matching value or None
        """
        for key in keys:
            if key in data:
                return data[key]
        return None

    def to_dict(self) -> dict[str, str | None]:
        """Convert Transaction to dictionary.

        Uses standard column names for consistency.

        Returns:
            Dictionary representation

        Examples:
            >>> tx = Transaction(date="01/01/23", details="Test", debit="50.00",
            ...                  credit=None, balance="100.00", filename="test.pdf")
            >>> d = tx.to_dict()
            >>> d["Date"]
            '01/01/23'
        """
        result: dict[str, str | None] = {
            "Date": self.date,
            "Details": self.details,
            "Debit €": self.debit,
            "Credit €": self.credit,
            "Balance €": self.balance,
            "Filename": self.filename,
        }

        # Add any additional fields
        result.update(self.additional_fields)

        return result

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String representation showing key fields
        """
        amount = self.debit if self.is_debit() else self.credit
        amount_type = "Dr" if self.is_debit() else "Cr"
        return (
            f"Transaction(date='{self.date}', "
            f"details='{self.details[:30]}...', "
            f"{amount_type}={amount}, "
            f"balance={self.balance})"
        )
