import pytest
import logging
from unittest.mock import patch, MagicMock
import time
from streamlit_app import get_analyzers, initialize_analyzers
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def reset_analyzers():
    """Reset global analyzer instances before each test"""
    import streamlit_app
    streamlit_app.reddit_analyzer = None
    streamlit_app.text_analyzer = None
    streamlit_app.account_scorer = None
    yield
    # Cleanup after test
    streamlit_app.reddit_analyzer = None
    streamlit_app.text_analyzer = None
    streamlit_app.account_scorer = None

def test_analyzers_initially_none(reset_analyzers):
    """Test that analyzers are initially uninitialized"""
    import streamlit_app
    assert streamlit_app.reddit_analyzer is None
    assert streamlit_app.text_analyzer is None
    assert streamlit_app.account_scorer is None

def test_lazy_loading_initialization(reset_analyzers):
    """Test that get_analyzers creates instances on first call"""
    # First call should create new instances
    reddit, text, scorer = get_analyzers()
    assert isinstance(reddit, RedditAnalyzer)
    assert isinstance(text, TextAnalyzer)
    assert isinstance(scorer, AccountScorer)

def test_lazy_loading_caching(reset_analyzers):
    """Test that subsequent calls return cached instances"""
    # First call
    reddit1, text1, scorer1 = get_analyzers()
    
    # Second call should return same instances
    reddit2, text2, scorer2 = get_analyzers()
    
    assert reddit1 is reddit2  # Should be same instance
    assert text1 is text2
    assert scorer1 is scorer2

@pytest.mark.parametrize("mock_init_time", [0.1, 0.5, 1.0])
def test_initialization_timing(reset_analyzers, mock_init_time):
    """Test that initialization timing is properly logged and within limits"""
    with patch('time.time') as mock_time:
        # Mock time.time() to return increasing values
        mock_time.side_effect = [0, mock_init_time]  # Start and end times
        
        with patch('logging.Logger.info') as mock_logger:
            reddit, text, scorer = get_analyzers()
            
            # Verify timing log was made
            mock_logger.assert_any_call(
                f"Completed initialize_analyzers in {mock_init_time:.2f} seconds"
            )

def test_error_handling(reset_analyzers):
    """Test error handling during analyzer initialization"""
    with patch('streamlit_app.RedditAnalyzer', side_effect=Exception("Test error")):
        with pytest.raises(Exception) as exc_info:
            get_analyzers()
        assert "Test error" in str(exc_info.value)

def test_performance_threshold():
    """Test that analyzer initialization completes within acceptable time"""
    start_time = time.time()
    reddit, text, scorer = get_analyzers()
    initialization_time = time.time() - start_time
    
    # Initialization should complete within 2 seconds
    assert initialization_time < 2.0, f"Initialization took {initialization_time:.2f} seconds"
