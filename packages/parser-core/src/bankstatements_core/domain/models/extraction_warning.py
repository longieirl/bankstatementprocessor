"""ExtractionWarning domain model for structured pipeline warning events."""

from __future__ import annotations

from dataclasses import dataclass, field

# Machine-readable warning codes
CODE_DATE_PROPAGATED = "DATE_PROPAGATED"
CODE_CREDIT_CARD_SKIPPED = "CREDIT_CARD_SKIPPED"
CODE_MISSING_BALANCE = "MISSING_BALANCE"


@dataclass
class ExtractionWarning:
    """A structured warning event produced during PDF extraction.

    Attributes:
        code: Machine-readable identifier (use CODE_* constants).
        message: Human-readable description of the event.
        page: Page number the warning relates to, or None if document-level.

    Examples:
        >>> w = ExtractionWarning(code=CODE_DATE_PROPAGATED,
        ...     message="date propagated from previous row ('01 Jan 2024')")
        >>> w.code
        'DATE_PROPAGATED'
    """

    code: str
    message: str
    page: int | None = field(default=None)

    def to_dict(self) -> dict:
        """Serialise to a plain dict for JSON encoding."""
        return {"code": self.code, "message": self.message, "page": self.page}

    @classmethod
    def from_dict(cls, data: dict) -> ExtractionWarning:
        """Deserialise from a plain dict."""
        return cls(
            code=data["code"],
            message=data["message"],
            page=data.get("page"),
        )
