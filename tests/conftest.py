"""
tests/conftest.py — Shared pytest fixtures for Rungus analyzer tests.
"""
import sys
from pathlib import Path
import pytest

# Ensure the project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from rungus_analyzer_lib import load_dictionary

@pytest.fixture(scope="session")
def dictionary():
    """Load the dictionary once for the entire test session."""
    return load_dictionary()
