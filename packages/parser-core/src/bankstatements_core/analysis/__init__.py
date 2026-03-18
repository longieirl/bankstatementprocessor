"""Analysis utilities for PDF bank statement processing.

This package provides tools for analyzing PDF structure to assist with
template generation, without triggering any paid features.
"""

from bankstatements_core.analysis.bbox_utils import BBox

__all__ = ["BBox"]
