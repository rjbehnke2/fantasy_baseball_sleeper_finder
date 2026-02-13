"""Tests for the daily insights digest endpoint."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db.session import get_db
from backend.app.main import app


async def _mock_db():
    """Provide a mock async session that returns empty results."""
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = []
    session.execute.return_value = result
    yield session


@pytest.fixture(autouse=True)
def override_db():
    """Override the DB dependency for all tests in this module."""
    app.dependency_overrides[get_db] = _mock_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_daily_digest_endpoint():
    """The /insights/daily endpoint should return a valid digest structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/insights/daily")

    assert response.status_code == 200
    data = response.json()
    assert "top_sleepers" in data
    assert "bust_warnings" in data
    assert "dynasty_risers" in data
    assert "improvement_leaders" in data
    assert "generated_date" in data
    assert isinstance(data["top_sleepers"], list)


@pytest.mark.asyncio
async def test_daily_digest_empty_returns_valid_structure():
    """With no projections, digest should return empty lists."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/insights/daily")

    data = response.json()
    assert data["top_sleepers"] == []
    assert data["bust_warnings"] == []
    assert data["dynasty_risers"] == []
    assert data["improvement_leaders"] == []
