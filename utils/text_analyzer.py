import nltk
import os
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import logging
from typing import List, Dict
import re
from datetime import datetime
from utils.performance_monitor import timing_decorator
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextAnalyzer:
    _instance = None
    _initialized = False
    _nltk_initialized = False
    _nltk_data_dir = os.path.join(os.getcwd(), 'nltk_data')
    _cache_file = os.path.join(os.getcwd(), 'nltk_data', 'resource_cache.json')
    _required_resources = {
        'punkt': 'tokenizers/punkt',
        'stopwords': 'corpora/stopwords',
        'averaged_perceptron_tagger': 'taggers/averaged_perceptron_tagger'
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TextAnalyzer, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            logger.info("Initializing TextAnalyzer instance")
            self.vectorizer = TfidfVectorizer(
                min_df=1,
                max_df=0.95
            )
            # Create NLTK data directory if it doesn't exist
            if not os.path.exists(self._nltk_data_dir):
                os.makedirs(self._nltk_data_dir)

            nltk.data.path.append(self._nltk_data_dir)
            self._initialized = True
            self._cache_status = self._load_cache()

    def _load_cache(self) -> dict:
        """Load resource cache status"""
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading cache: {str(e)}")
            return {}

    def _save_cache(self):
        """Save resource cache status"""
        try:
            with open(self._cache_file, 'w') as f:
                json.dump(self._cache_status, f)
        except Exception as e:
            logger.error(f"Error saving cache: {str(e)}")

    def _verify_resource(self, resource: str) -> bool:
        """Verify if a resource exists and is valid"""
        try:
            resource_path = self._required_resources.get(resource)
            if not resource_path:
                return False

            nltk.data.find(resource_path)
            return True
        except LookupError:
            return False

    @timing_decorator("nltk_resource_loading")
    def _ensure_nltk_resources(self, resources: List[str] = None):
        """Lazy load specific NLTK resources"""
        if resources is None:
            resources = list(self._required_resources.keys())

        try:
            missing_resources = []
            for resource in resources:
                if not self._verify_resource(resource):
                    missing_resources.append(resource)
                    continue

                # Update cache for verified resources
                self._cache_status[resource] = {
                    'downloaded': True,
                    'last_verified': datetime.now().isoformat()
                }

            if missing_resources:
                logger.info(f"Downloading missing NLTK resources: {missing_resources}")
                for resource in missing_resources:
                    try:
                        nltk.download(resource, 
                                    quiet=True, 
                                    download_dir=self._nltk_data_dir)
                        self._cache_status[resource] = {
                            'downloaded': True,
                            'last_verified': datetime.now().isoformat()
                        }
                    except Exception as e:
                        logger.error(f"Error downloading {resource}: {str(e)}")
                        self._cache_status[resource] = {
                            'downloaded': False,
                            'error': str(e),
                            'last_attempt': datetime.now().isoformat()
                        }

            self._save_cache()

            if 'stopwords' in resources:
                self.stop_words = set(stopwords.words('english'))

            logger.info("NLTK initialization complete")
        except Exception as e:
            logger.error(f"Error initializing NLTK: {str(e)}")
            raise

    def _ensure_specific_resources(self, resource_names: List[str]):
        """Ensure specific resources are available"""
        if not self._nltk_initialized or any(
            resource not in self._cache_status or 
            not self._cache_status[resource].get('downloaded', False)
            for resource in resource_names
        ):
            self._ensure_nltk_resources(resource_names)
            self._nltk_initialized = True

    @timing_decorator("comment_analysis")
    def analyze_comments(self, comments: List[str], timestamps: List[datetime] = None) -> Dict:
        """Analyze comments for bot-like patterns."""
        # Only load required resources for comment analysis
        required_resources = ['punkt', 'stopwords']
        self._ensure_specific_resources(required_resources)

        if not comments:
            logger.warning("No comments provided for analysis")
            return self._get_empty_metrics()

        try:
            logger.info(f"Starting analysis of {len(comments)} comments")

            # Calculate all scores
            repetition_score = self._calculate_repetition_score(comments)
            template_score = self._calculate_template_score(comments)
            complexity_score = self._calculate_complexity_score(comments)
            timing_score = self._analyze_timing_patterns(timestamps) if timestamps else 0.5
            suspicious_patterns = self._identify_suspicious_patterns(comments)

            # Log individual scores for debugging
            logger.info(f"Repetition score: {repetition_score}")
            logger.info(f"Template score: {template_score}")
            logger.info(f"Complexity score: {complexity_score}")
            logger.info(f"Timing score: {timing_score}")
            logger.info(f"Suspicious patterns: {suspicious_patterns}")

            # Combine all metrics
            metrics = {
                'repetition_score': repetition_score,
                'template_score': template_score,
                'complexity_score': complexity_score,
                'timing_score': timing_score,
                'suspicious_patterns': suspicious_patterns,
            }

            # Calculate final probability
            bot_prob = self._calculate_bot_probability(metrics)
            metrics['bot_probability'] = bot_prob

            logger.info(f"Final bot probability: {bot_prob}")
            return metrics

        except Exception as e:
            logger.error(f"Error in analyze_comments: {str(e)}")
            return self._get_empty_metrics()

    def _calculate_repetition_score(self, comments: List[str]) -> float:
        """Calculate repetition score with higher sensitivity."""
        try:
            if not comments:
                return 0.0

            # Get all word sequences (2-4 words) - reduced length for better detection
            sequences = []
            for comment in comments:
                words = comment.lower().split()
                for i in range(len(words)-1):
                    sequences.extend([' '.join(words[i:i+n]) for n in range(2, 5) if i+n <= len(words)])

            if not sequences:
                return 0.0

            # Count repeated sequences and normalize
            sequence_counts = Counter(sequences)
            max_repetition = max(sequence_counts.values())
            total_sequences = len(sequences)

            # More aggressive scoring
            repetition_score = min(1.0, (max_repetition / total_sequences) * 3)
            logger.info(f"Max repetition: {max_repetition}, Total sequences: {total_sequences}")

            return repetition_score
        except Exception as e:
            logger.error(f"Error calculating repetition score: {str(e)}")
            return 0.0

    def _calculate_template_score(self, comments: List[str]) -> float:
        """Detect template usage with increased sensitivity."""
        try:
            if len(comments) < 2:
                return 0.0

            # Convert to TF-IDF vectors
            vectors = self.vectorizer.fit_transform(comments)
            similarity_matrix = (vectors * vectors.T).toarray()

            # Calculate average similarity excluding self-similarity
            n = len(comments)
            similarity_sum = similarity_matrix.sum() - n  # Subtract diagonal
            avg_similarity = similarity_sum / (n * (n-1)) if n > 1 else 0

            # Amplify the score for better detection
            template_score = min(1.0, avg_similarity * 3)
            logger.info(f"Average similarity: {avg_similarity}, Template score: {template_score}")

            return template_score
        except Exception as e:
            logger.error(f"Error calculating template score: {str(e)}")
            return 0.0

    def _calculate_complexity_score(self, comments: List[str]) -> float:
        """Calculate language complexity score."""
        try:
            if not comments:
                logger.debug("No comments provided for complexity analysis")
                return 0.5  # Neutral score

            scores = []
            for comment in comments:
                try:
                    # Use word split instead of word_tokenize to avoid NLTK dependency
                    words = str(comment).lower().split()
                    if not words:
                        continue

                    # Calculate metrics
                    unique_ratio = float(len(set(words)) / len(words))
                    avg_word_length = float(np.mean([len(w) for w in words]))

                    # More aggressive scoring for bot-like patterns
                    comment_score = 1.0 - ((unique_ratio + min(1.0, avg_word_length/8)) / 2)
                    scores.append(float(comment_score))

                except Exception as e:
                    logger.error(f"Error processing comment for complexity: {str(e)}")
                    continue

            complexity_score = float(np.mean(scores) if scores else 0.5)
            logger.info(f"Calculated complexity score: {complexity_score}")

            return complexity_score
        except Exception as e:
            logger.error(f"Error calculating complexity score: {str(e)}")
            return 0.5  # Return neutral score on error

    def _analyze_timing_patterns(self, timestamps: List[datetime]) -> float:
        """Analyze timing patterns with increased sensitivity."""
        try:
            if not timestamps or len(timestamps) < 2:
                return 0.5

            # Calculate time differences
            sorted_times = sorted(timestamps)
            time_diffs = np.array([(t2 - t1).total_seconds() 
                                    for t1, t2 in zip(sorted_times[:-1], sorted_times[1:])])

            if len(time_diffs) == 0:
                return 0.5

            # Calculate statistics
            mean_diff = np.mean(time_diffs)
            std_diff = np.std(time_diffs)
            cv = std_diff / mean_diff if mean_diff > 0 else float('inf')

            # Calculate bot-like patterns
            regularity_score = 1.0 / (1.0 + cv)  # More regular = higher score
            rapid_responses = np.sum(time_diffs < 30) / len(time_diffs)  # Proportion of quick responses

            # Combine scores with higher weight on patterns
            timing_score = min(1.0, (regularity_score * 0.6 + rapid_responses * 0.4) * 1.5)
            logger.info(f"Timing regularity: {regularity_score}, Rapid responses: {rapid_responses}")

            return timing_score
        except Exception as e:
            logger.error(f"Error analyzing timing patterns: {str(e)}")
            return 0.5

    def _identify_suspicious_patterns(self, comments: List[str]) -> Dict[str, int]:
        """Identify suspicious patterns with improved detection."""
        patterns = {
            'identical_greetings': 0,
            'url_patterns': 0,
            'promotional_phrases': 0,
            'generic_responses': 0
        }

        try:
            if not comments:
                return patterns

            total_comments = max(1, len(comments))

            # Enhanced pattern detection
            for comment in comments:
                comment_lower = comment.lower().strip()

                # Generic greetings
                if re.match(r'^\s*(hi|hello|hey|greetings|good morning|good evening|good day)\b.*?$', comment_lower):
                    patterns['identical_greetings'] += 1

                # URLs and links
                if re.search(r'http[s]?://\S+|www\.\S+|\[link\]|\(link\)', comment):
                    patterns['url_patterns'] += 1

                # Promotional content
                if re.search(r'\b(check out|visit|click|buy|discount|offer|limited time|act now|don\'t miss|exclusive)\b', comment_lower):
                    patterns['promotional_phrases'] += 1

                # Generic/template responses
                if re.search(r'^(thanks|thank you|great|nice|good|awesome|excellent|interesting|wow|cool)\s+(post|article|point|content|stuff|work|job|share|sharing)\s*[.!]*$', comment_lower):
                    patterns['generic_responses'] += 1

            # Convert to percentages and amplify
            for key in patterns:
                patterns[key] = min(100, int((patterns[key] / total_comments) * 100 * 1.5))

            logger.info(f"Detected patterns (percentage): {patterns}")
            return patterns
        except Exception as e:
            logger.error(f"Error identifying suspicious patterns: {str(e)}")
            return patterns

    def _calculate_bot_probability(self, metrics: Dict) -> float:
        """Calculate final bot probability with balanced weighting."""
        try:
            # Primary metrics weights - adjusted for less aggressive scoring
            weights = {
                'repetition_score': 0.25,     # Reduced from 0.3
                'template_score': 0.2,        # Reduced from 0.25
                'complexity_score': 0.15,     # Reduced from 0.2
                'timing_score': 0.15          # Reduced from 0.25
            }

            # Calculate primary score
            primary_score = 0.0
            weight_sum = 0.0

            for key, weight in weights.items():
                if key in metrics and metrics[key] is not None:
                    score = metrics[key]
                    # Apply dampening to reduce false positives
                    if score < 0.3:  # Low scores get reduced further
                        score = score * 0.5
                    primary_score += score * weight
                    weight_sum += weight
                    logger.info(f"{key}: {score} (weight: {weight})")

            if weight_sum == 0:
                return 0.0

            # Normalize primary score
            primary_score = primary_score / weight_sum

            # Calculate suspicious patterns score with reduced impact
            suspicious_patterns = metrics.get('suspicious_patterns', {})
            if suspicious_patterns:
                pattern_score = sum(val/100 for val in suspicious_patterns.values()) / len(suspicious_patterns)
                # Dampen pattern score to reduce impact
                pattern_score = pattern_score * 0.5
            else:
                pattern_score = 0.0

            # Combine scores with reduced pattern impact
            final_score = primary_score * 0.8 + pattern_score * 0.2

            # Remove aggressive amplification
            logger.info(f"Primary score: {primary_score}, Pattern score: {pattern_score}, Final score: {final_score}")
            return final_score

        except Exception as e:
            logger.error(f"Error calculating bot probability: {str(e)}")
            return 0.0

    def _get_empty_metrics(self) -> Dict:
        """Return empty metrics structure."""
        return {
            'repetition_score': 0.0,
            'template_score': 0.0,
            'timing_score': 0.5,
            'complexity_score': 0.5,
            'suspicious_patterns': {
                'identical_greetings': 0,
                'url_patterns': 0,
                'promotional_phrases': 0,
                'generic_responses': 0
            },
            'bot_probability': 0.0
        }