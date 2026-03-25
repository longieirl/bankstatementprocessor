"""Pytest configuration for integration tests."""

from __future__ import annotations


def pytest_addoption(parser):
    parser.addoption(
        "--snapshot-update",
        action="store_true",
        default=False,
        help="Regenerate the output snapshot baseline instead of comparing against it.",
    )
