"""Tests for PDF discovery service."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from bankstatements_core.entitlements import Entitlements
from bankstatements_core.services.pdf_discovery import PDFDiscoveryService


class TestPDFDiscoveryService(unittest.TestCase):
    """Test PDFDiscoveryService functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.input_dir = Path(self.temp_dir) / "input"
        self.input_dir.mkdir()
        self.service = PDFDiscoveryService()

    def test_discover_pdfs_no_files(self):
        """Test discovery with no PDF files."""
        pdfs = self.service.discover_pdfs(self.input_dir)

        self.assertEqual(len(pdfs), 0)

    def test_discover_pdfs_multiple_files(self):
        """Test discovery with multiple PDF files."""
        # Create test PDF files
        (self.input_dir / "file1.pdf").write_text("fake pdf 1")
        (self.input_dir / "file2.pdf").write_text("fake pdf 2")
        (self.input_dir / "file3.pdf").write_text("fake pdf 3")

        pdfs = self.service.discover_pdfs(self.input_dir)

        self.assertEqual(len(pdfs), 3)
        self.assertTrue(all(p.suffix == ".pdf" for p in pdfs))

    def test_discover_pdfs_mixed_files(self):
        """Test discovery ignores non-PDF files."""
        # Create mixed files
        (self.input_dir / "file1.pdf").write_text("fake pdf")
        (self.input_dir / "file2.txt").write_text("text file")
        (self.input_dir / "file3.doc").write_text("word file")
        (self.input_dir / "file4.pdf").write_text("another pdf")

        pdfs = self.service.discover_pdfs(self.input_dir)

        self.assertEqual(len(pdfs), 2)
        self.assertTrue(all(p.suffix == ".pdf" for p in pdfs))

    def test_discover_pdfs_directory_not_exists(self):
        """Test discovery creates directory if it doesn't exist."""
        non_existent = Path(self.temp_dir) / "non_existent"

        # Directory should not exist initially
        self.assertFalse(non_existent.exists())

        # Discover PDFs (should create directory)
        pdfs = self.service.discover_pdfs(non_existent)

        # Directory should now exist
        self.assertTrue(non_existent.exists())
        self.assertTrue(non_existent.is_dir())

        # Should return empty list (no PDFs in new directory)
        self.assertEqual([], pdfs)

    def test_discover_pdfs_path_not_directory(self):
        """Test discovery raises error when path is not a directory."""
        file_path = self.input_dir / "file.txt"
        file_path.write_text("not a directory")

        with self.assertRaises(ValueError) as context:
            self.service.discover_pdfs(file_path)

        self.assertIn("not a directory", str(context.exception))

    def test_discover_pdfs_recursive_no_entitlements(self):
        """Test recursive discovery without entitlements."""
        # Create subdirectory with PDFs
        subdir = self.input_dir / "subdir"
        subdir.mkdir()
        (self.input_dir / "file1.pdf").write_text("top level")
        (subdir / "file2.pdf").write_text("nested")

        pdfs = self.service.discover_pdfs(self.input_dir, recursive=True)

        # Should find both files
        self.assertEqual(len(pdfs), 2)

    def test_discover_pdfs_recursive_with_entitlements_allowed(self):
        """Test recursive discovery with entitlements that allow it."""
        # Create mock entitlements that allow recursive scan
        mock_entitlements = MagicMock(spec=Entitlements)
        mock_entitlements.check_recursive_scan.return_value = None  # No exception

        service = PDFDiscoveryService(entitlements=mock_entitlements)

        # Create subdirectory with PDFs
        subdir = self.input_dir / "subdir"
        subdir.mkdir()
        (self.input_dir / "file1.pdf").write_text("top level")
        (subdir / "file2.pdf").write_text("nested")

        pdfs = service.discover_pdfs(self.input_dir, recursive=True)

        # Should find both files
        self.assertEqual(len(pdfs), 2)
        mock_entitlements.check_recursive_scan.assert_called_once()

    def test_discover_pdfs_recursive_with_entitlements_denied(self):
        """Test recursive discovery with entitlements that deny it."""
        from bankstatements_core.entitlements import EntitlementError

        # Create mock entitlements that deny recursive scan
        mock_entitlements = MagicMock(spec=Entitlements)
        mock_entitlements.check_recursive_scan.side_effect = EntitlementError(
            "Not allowed"
        )

        service = PDFDiscoveryService(entitlements=mock_entitlements)

        # Create subdirectory with PDFs
        subdir = self.input_dir / "subdir"
        subdir.mkdir()
        (self.input_dir / "file1.pdf").write_text("top level")
        (subdir / "file2.pdf").write_text("nested")

        with self.assertLogs(
            "bankstatements_core.services.pdf_discovery", level="WARNING"
        ):
            pdfs = service.discover_pdfs(self.input_dir, recursive=True)

        # Should only find top-level file (fallback to non-recursive)
        self.assertEqual(len(pdfs), 1)
        self.assertEqual(pdfs[0].name, "file1.pdf")

    def test_discover_pdfs_sorted(self):
        """Test that discovered PDFs are sorted."""
        # Create PDFs in random order
        (self.input_dir / "c.pdf").write_text("c")
        (self.input_dir / "a.pdf").write_text("a")
        (self.input_dir / "b.pdf").write_text("b")

        pdfs = self.service.discover_pdfs(self.input_dir)

        # Should be sorted
        names = [p.name for p in pdfs]
        self.assertEqual(names, ["a.pdf", "b.pdf", "c.pdf"])

    def test_discover_pdfs_creation_permission_error(self):
        """Test that permission errors when creating directory are properly raised."""
        from unittest import mock

        non_existent = Path(self.temp_dir) / "no_permission"

        # Mock mkdir to raise PermissionError
        with mock.patch.object(
            Path, "mkdir", side_effect=PermissionError("Access denied")
        ):
            with self.assertRaises(FileNotFoundError) as context:
                self.service.discover_pdfs(non_existent)

            # Should wrap PermissionError in FileNotFoundError
            self.assertIn("could not be created", str(context.exception))


if __name__ == "__main__":
    unittest.main()
