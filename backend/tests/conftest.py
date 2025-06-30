"""
Pytest configuration and fixtures.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """Create a FastAPI app for testing."""
    return FastAPI()


@pytest.fixture
def client(app):
    """Create a TestClient for testing."""
    return TestClient(app)
