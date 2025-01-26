import pytest
import os
import sys
from datetime import datetime, timezone, timedelta
import logging

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def sample_user_data():
    """Fixture providing sample user data for testing"""
    return {
        'username': 'test_user',
        'created_utc': datetime.now(timezone.utc),
        'comment_karma': 1000,
        'link_karma': 500,
        'comments': [],
        'submissions': []
    }

@pytest.fixture
def sample_comments():
    """Fixture providing sample comments for testing"""
    return [
        "This is a normal comment with some content.",
        "Another unique comment about different things.",
        "Some people might say similar things sometimes.",
        "This is a totally different comment.",
        "A unique perspective on things."
    ]

@pytest.fixture
def sample_timestamps():
    """Fixture providing sample timestamps for testing"""
    base_time = datetime.now(timezone.utc)
    return [
        base_time,
        base_time + timedelta(minutes=5),
        base_time + timedelta(minutes=10),
        base_time + timedelta(minutes=15),
        base_time + timedelta(minutes=20)
    ]