"""Tests for PDF discovery with entitlement enforcement."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from bankstatements_core.entitlements import Entitlements
from bankstatements_core.utils import discover_pdfs


class TestPdfDiscoveryEntitlements:
    """Test entitlement enforcement for PDF discovery."""

    def test_free_tier_top_level_only(self):
        """Test FREE tier only scans top-level directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir)

            # Create PDFs in top-level and subdirectory
            (input_dir / "top1.pdf").touch()
            (input_dir / "top2.pdf").touch()
            subdir = input_dir / "subdir"
            subdir.mkdir()
            (subdir / "sub1.pdf").touch()
            (subdir / "sub2.pdf").touch()

            # FREE tier with recursive=False (allowed)
            free_ent = Entitlements.free_tier()
            pdfs = discover_pdfs(input_dir, recursive=False, entitlements=free_ent)

            # Should find only top-level PDFs
            assert len(pdfs) == 2
            assert all("subdir" not in str(p) for p in pdfs)

    def test_free_tier_allows_recursive_scan(self):
        """Test FREE tier allows recursive scanning (now available to all)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir)

            # Create PDFs in subdirectory
            (input_dir / "top.pdf").touch()
            subdir = input_dir / "subdir"
            subdir.mkdir()
            (subdir / "sub.pdf").touch()

            # FREE tier with recursive=True (now allowed)
            free_ent = Entitlements.free_tier()
            pdfs = discover_pdfs(input_dir, recursive=True, entitlements=free_ent)

            # Should find all PDFs recursively
            assert len(pdfs) == 2
            assert any("subdir" in str(p) for p in pdfs)

    def test_paid_tier_allows_recursive_scan(self):
        """Test PAID tier allows recursive scanning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir)

            # Create PDFs in top-level and nested subdirectories
            (input_dir / "top.pdf").touch()
            subdir1 = input_dir / "subdir1"
            subdir1.mkdir()
            (subdir1 / "sub1.pdf").touch()
            subdir2 = subdir1 / "nested"
            subdir2.mkdir()
            (subdir2 / "nested.pdf").touch()

            # PAID tier with recursive=True
            paid_ent = Entitlements.paid_tier()
            pdfs = discover_pdfs(input_dir, recursive=True, entitlements=paid_ent)

            # Should find all PDFs recursively
            assert len(pdfs) == 3
            assert any("subdir1" in str(p) for p in pdfs)
            assert any("nested" in str(p) for p in pdfs)

    def test_paid_tier_top_level_when_not_requested(self):
        """Test PAID tier respects recursive=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir)

            # Create PDFs in top-level and subdirectory
            (input_dir / "top.pdf").touch()
            subdir = input_dir / "subdir"
            subdir.mkdir()
            (subdir / "sub.pdf").touch()

            # PAID tier with recursive=False (explicit choice)
            paid_ent = Entitlements.paid_tier()
            pdfs = discover_pdfs(input_dir, recursive=False, entitlements=paid_ent)

            # Should find only top-level PDFs
            assert len(pdfs) == 1
            assert "subdir" not in str(pdfs[0])

    def test_empty_directory(self):
        """Test handling of empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir)

            # No PDFs in directory
            free_ent = Entitlements.free_tier()
            pdfs = discover_pdfs(input_dir, recursive=False, entitlements=free_ent)

            assert len(pdfs) == 0

    def test_no_pdfs_only_other_files(self):
        """Test directory with non-PDF files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir)

            # Create non-PDF files
            (input_dir / "file.txt").touch()
            (input_dir / "document.docx").touch()

            free_ent = Entitlements.free_tier()
            pdfs = discover_pdfs(input_dir, recursive=False, entitlements=free_ent)

            assert len(pdfs) == 0

    def test_results_are_sorted(self):
        """Test that results are returned in sorted order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir)

            # Create PDFs in non-alphabetical order
            (input_dir / "zebra.pdf").touch()
            (input_dir / "alpha.pdf").touch()
            (input_dir / "beta.pdf").touch()

            free_ent = Entitlements.free_tier()
            pdfs = discover_pdfs(input_dir, recursive=False, entitlements=free_ent)

            # Should be sorted
            assert len(pdfs) == 3
            filenames = [p.name for p in pdfs]
            assert filenames == ["alpha.pdf", "beta.pdf", "zebra.pdf"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
