import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from main import app
import logging
import time
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)
client = TestClient(app)

@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data
    logger.info("Health check endpoint test passed")

@pytest.mark.asyncio
async def test_analyze_user_endpoint(mock_reddit_analyzer):
    """Test user analysis endpoint with mock data"""
    test_username = "test_user"

    # Inject mock analyzer
    app.dependency_overrides[RedditAnalyzer] = lambda: mock_reddit_analyzer

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

    # Clean up
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting functionality"""
    test_username = "test_user"

    # Make multiple requests in quick succession
    responses = []
    for _ in range(6):  # Exceeds our rate limit of 5 requests
        response = client.get(f"/api/v1/analyze/{test_username}")
        responses.append(response.status_code)
        time.sleep(0.1)  # Small delay to avoid overwhelming the server

    # Verify that rate limiting kicked in
    assert 429 in responses
    logger.info("Rate limiting test passed")

@pytest.mark.asyncio
async def test_invalid_username():
    """Test handling of invalid usernames"""
    response = client.get("/api/v1/analyze/this_user_definitely_does_not_exist_12345")
    assert response.status_code in (400, 429)
    logger.info("Invalid username test passed")

@pytest.mark.asyncio
async def test_database_integration(test_db):
    """Test database integration"""
    from utils.database import AnalysisResult

    # Clean up any existing test data
    test_db.query(AnalysisResult).filter_by(username="test_user").delete()
    test_db.commit()

    # Create test data
    test_result = AnalysisResult(
        username="test_user",
        bot_probability=50.0,
        analysis_count=1
    )
    test_db.add(test_result)
    test_db.commit()

    # Query test data
    result = test_db.query(AnalysisResult).filter_by(username="test_user").first()
    assert result is not None
    assert result.bot_probability == 50.0
    assert result.analysis_count == 1

    # Clean up test data
    test_db.delete(result)
    test_db.commit()

    logger.info("Database integration test passed")

def run_test_suite():
    """Run all tests and return results"""
    import pytest
    import sys
    from pathlib import Path

    # Get the test directory
    test_dir = Path(__file__).parent

    # Run pytest with logging
    logger.info("Starting test suite execution")
    result = pytest.main([
        str(test_dir),
        '-v',
        '--log-cli-level=INFO',
        '--log-file=test_logs/latest_run.log'
    ])

    logger.info(f"Test suite completed with exit code: {result}")
    return result

if __name__ == "__main__":
    sys.exit(run_test_suite())