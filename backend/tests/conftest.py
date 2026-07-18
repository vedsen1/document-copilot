"""Pytest configuration for the backend test suite."""
from __future__ import annotations

import asyncio
import selectors
import sys
import warnings

import pytest


# ---------------------------------------------------------------------------
# Windows: psycopg async is incompatible with ProactorEventLoop.
# We subclass DefaultEventLoopPolicy so that every call to new_event_loop()
# returns a SelectorEventLoop.  This runs at import time — before
# pytest-asyncio creates any loop — so the policy is in place from the start.
# The set/get_event_loop_policy deprecation warnings are suppressed the same
# way pytest-asyncio does it internally.
# ---------------------------------------------------------------------------
if sys.platform == "win32":

    class _SelectorLoopPolicy(asyncio.DefaultEventLoopPolicy):  # type: ignore[misc]
        """Always produce a SelectorEventLoop on Windows."""

        def new_event_loop(self) -> asyncio.AbstractEventLoop:
            return asyncio.SelectorEventLoop(selectors.SelectSelector())

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(_SelectorLoopPolicy())


def pytest_configure(config):
    """Register custom markers so pytest doesn't warn about unknown marks."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require a live database and OpenAI API key "
        "(deselect with: pytest -m 'not integration')",
    )
