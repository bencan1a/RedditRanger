import pytest
from utils.text_analyzer import TextAnalyzer
import logging

logger = logging.getLogger(__name__)

class TestTextAnalyzer:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test instance of TextAnalyzer"""
        self.analyzer = TextAnalyzer()
        
    def test_initialization(self):
        """Test TextAnalyzer initialization"""
        assert self.analyzer._initialized
        assert self.analyzer._nltk_initialized
        logger.info("TextAnalyzer initialization test passed")
        
    def test_analyze_comments_empty_input(self):
        """Test analyzer behavior with empty input"""
        result = self.analyzer.analyze_comments([])
        assert isinstance(result, dict)
        assert result['bot_probability'] == 0.0
        logger.info("Empty input test passed")
        
    def test_analyze_comments_valid_input(self, sample_comments):
        """Test analyzer with valid comments"""
        result = self.analyzer.analyze_comments(sample_comments)
        assert isinstance(result, dict)
        assert 0 <= result['bot_probability'] <= 1.0
        assert 'repetition_score' in result
        assert 'template_score' in result
        assert 'complexity_score' in result
        logger.info(f"Valid input test passed with bot probability: {result['bot_probability']}")
        
    def test_analyze_timing_patterns(self, sample_timestamps):
        """Test timing pattern analysis"""
        result = self.analyzer._analyze_timing_patterns(sample_timestamps)
        assert isinstance(result, float)
        assert 0 <= result <= 1.0
        logger.info(f"Timing pattern analysis test passed with score: {result}")
        
    def test_identify_suspicious_patterns(self, sample_comments):
        """Test suspicious pattern detection"""
        patterns = self.analyzer._identify_suspicious_patterns(sample_comments)
        assert isinstance(patterns, dict)
        assert 'identical_greetings' in patterns
        assert 'url_patterns' in patterns
        assert 'promotional_phrases' in patterns
        assert 'generic_responses' in patterns
        logger.info(f"Suspicious pattern detection test passed: {patterns}")

    def test_calculate_bot_probability(self):
        """Test bot probability calculation"""
        test_metrics = {
            'repetition_score': 0.3,
            'template_score': 0.4,
            'complexity_score': 0.5,
            'timing_score': 0.6,
            'suspicious_patterns': {
                'identical_greetings': 20,
                'url_patterns': 10,
                'promotional_phrases': 5,
                'generic_responses': 15
            }
        }
        probability = self.analyzer._calculate_bot_probability(test_metrics)
        assert isinstance(probability, float)
        assert 0 <= probability <= 1.0
        logger.info(f"Bot probability calculation test passed with score: {probability}")
