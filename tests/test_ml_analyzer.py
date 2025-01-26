import pytest
import numpy as np
from utils.ml_analyzer import MLAnalyzer
import logging

logger = logging.getLogger(__name__)

class TestMLAnalyzer:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test instance of MLAnalyzer"""
        self.analyzer = MLAnalyzer()
        
    def test_initialization(self):
        """Test MLAnalyzer initialization"""
        assert not self.analyzer.is_trained
        assert self.analyzer.model is not None
        assert self.analyzer.scaler is not None
        logger.info("MLAnalyzer initialization test passed")
        
    def test_add_training_example(self, sample_user_data):
        """Test adding training examples"""
        activity_patterns = {'unique_subreddits': 5, 'avg_score': 10}
        text_metrics = {'vocab_size': 100, 'avg_word_length': 5}
        
        result = self.analyzer.add_training_example(
            sample_user_data,
            activity_patterns,
            text_metrics,
            is_legitimate=True
        )
        
        assert result
        assert len(self.analyzer.training_features) > 0
        assert len(self.analyzer.training_labels) > 0
        logger.info("Training example addition test passed")
        
    def test_extract_features(self, sample_user_data):
        """Test feature extraction"""
        activity_patterns = {'unique_subreddits': 5, 'avg_score': 10}
        text_metrics = {'vocab_size': 100, 'avg_word_length': 5}
        
        features = self.analyzer.extract_features(
            sample_user_data,
            activity_patterns,
            text_metrics
        )
        
        assert isinstance(features, np.ndarray)
        assert features.shape[1] == 12  # Number of features
        logger.info("Feature extraction test passed")
        
    def test_analyze_account(self, sample_user_data):
        """Test account analysis"""
        activity_patterns = {'unique_subreddits': 5, 'avg_score': 10}
        text_metrics = {'vocab_size': 100, 'avg_word_length': 5}
        
        risk_score, feature_importance = self.analyzer.analyze_account(
            sample_user_data,
            activity_patterns,
            text_metrics
        )
        
        assert isinstance(risk_score, float)
        assert 0 <= risk_score <= 1.0
        logger.info(f"Account analysis test passed with risk score: {risk_score}")
