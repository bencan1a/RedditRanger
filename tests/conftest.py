import pytest
import os
import sys
from datetime import datetime, timezone, timedelta
import logging
from pathlib import Path

# Configure logging for tests
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
log_dir = Path('test_logs')
log_dir.mkdir(exist_ok=True)

# Create a unique log file for each test run
log_file = log_dir / f'test_run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

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

@pytest.fixture
def mock_reddit_analyzer():
    """Fixture providing a mocked RedditAnalyzer"""
    from utils.reddit_analyzer import RedditAnalyzer
    import pandas as pd

    class MockRedditAnalyzer(RedditAnalyzer):
        def __init__(self):
            self.client_id = 'mock_id'
            self.client_secret = 'mock_secret'
            self._initialized = True

        def get_user_data(self, username):
            sample_data = {
                'created_utc': datetime.now(timezone.utc),
                'comment_karma': 1000,
                'link_karma': 500,
            }
            comments_df = pd.DataFrame({
                'body': ['Test comment 1', 'Test comment 2'],
                'created_utc': [datetime.now(timezone.utc)] * 2,
                'score': [1, 2],
                'subreddit': ['test_sub'] * 2
            })
            submissions_df = pd.DataFrame({
                'title': ['Test post 1', 'Test post 2'],
                'created_utc': [datetime.now(timezone.utc)] * 2,
                'score': [1, 2],
                'subreddit': ['test_sub'] * 2
            })
            return sample_data, comments_df, submissions_df

    return MockRedditAnalyzer()

@pytest.fixture
def test_db():
    """Fixture providing a test database session"""
    from utils.database import init_db, get_db, Base, engine

    # Create test database tables
    Base.metadata.create_all(bind=engine)

    # Get database session
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def cleanup_test_logs():
    """Cleanup old test logs"""
    yield
    log_dir = Path('test_logs')
    if log_dir.exists():
        # Keep only the last 5 log files
        log_files = sorted(log_dir.glob('*.log'), reverse=True)
        for log_file in log_files[5:]:
            try:
                log_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete old log file {log_file}: {e}")