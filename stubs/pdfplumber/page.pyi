"""Type stubs for pdfplumber.page module."""

from typing import Any, Dict, List, Optional

class Page:
    """Represents a page in a PDF document."""

    width: float
    height: float
    bbox: tuple[float, float, float, float]

    def crop(self, bbox: tuple[float, float, float, float]) -> Page:
        """Crop the page to the specified bounding box.

        Args:
            bbox: Tuple of (x0, top, x1, bottom) coordinates

        Returns:
            A new Page object representing the cropped area
        """
        ...

    def extract_words(
        self,
        x_tolerance: float = 3,
        y_tolerance: float = 3,
        keep_blank_chars: bool = False,
        use_text_flow: bool = False,
        horizontal_ltr: bool = True,
        vertical_ttb: bool = True,
        extra_attrs: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Extract words from the page.

        Args:
            x_tolerance: Tolerance for combining characters into words horizontally
            y_tolerance: Tolerance for combining characters into words vertically
            keep_blank_chars: Whether to keep blank characters
            use_text_flow: Whether to use text flow for word ordering
            horizontal_ltr: Whether horizontal text flows left-to-right
            vertical_ttb: Whether vertical text flows top-to-bottom
            extra_attrs: Additional attributes to extract

        Returns:
            List of word dictionaries with keys like 'text', 'x0', 'x1', 'top', 'bottom'
        """
        ...

    def extract_text(self) -> str:
        """Extract text from the page.

        Returns:
            Text content of the page
        """
        ...

    def extract_tables(
        self,
        table_settings: Optional[Dict[str, Any]] = None,
    ) -> List[List[List[Optional[str]]]]:
        """Extract tables from the page.

        Args:
            table_settings: Optional settings for table extraction

        Returns:
            List of tables, where each table is a list of rows,
            and each row is a list of cell values
        """
        ...

    def extract_table(
        self,
        table_settings: Optional[Dict[str, Any]] = None,
    ) -> List[List[Optional[str]]]:
        """Extract the first table from the page.

        Args:
            table_settings: Optional settings for table extraction

        Returns:
            A table as a list of rows, where each row is a list of cell values
        """
        ...
