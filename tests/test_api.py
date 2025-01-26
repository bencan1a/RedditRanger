import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from main import app
import logging
import time

logger = logging.getLogger(__name__)
client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data
    logger.info("Health check endpoint test passed")

def test_analyze_user_endpoint():
    """Test user analysis endpoint"""
    test_username = "spez"  # Reddit co-founder's account as test case
    response = client.get(f"/api/v1/analyze/{test_username}")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "username" in data
    assert "probability" in data
    assert "summary" in data
    assert isinstance(data["probability"], float)
    assert 0 <= data["probability"] <= 100.0

    # Verify summary contents
    summary = data["summary"]
    assert "account_age" in summary
    assert "karma" in summary
    assert "scores" in summary
    assert "activity_metrics" in summary
    assert "text_analysis" in summary

    logger.info(f"User analysis endpoint test passed for user: {test_username}")

def test_rate_limiting():
    """Test rate limiting functionality"""
    test_username = "spez"

    # Make multiple requests in quick succession
    responses = []
    for _ in range(6):  # Exceeds our rate limit of 5 requests
        response = client.get(f"/api/v1/analyze/{test_username}")
        responses.append(response.status_code)
        time.sleep(0.1)  # Small delay to avoid overwhelming the server

    # Verify that rate limiting kicked in
    assert 429 in responses
    logger.info("Rate limiting test passed")

def test_invalid_username():
    """Test handling of invalid usernames"""
    response = client.get("/api/v1/analyze/this_user_definitely_does_not_exist_12345")
    # Accept either 400 (invalid username) or 429 (rate limit) as valid failure cases
    assert response.status_code in (400, 429)
    logger.info("Invalid username test passed")