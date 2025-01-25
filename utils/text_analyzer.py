import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import logging
from typing import List, Dict
import re
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextAnalyzer:
    def __init__(self):
        try:
            logger.info("Initializing NLTK resources...")
            # Download required NLTK data
            nltk.download('punkt')
            nltk.download('stopwords')
            nltk.download('averaged_perceptron_tagger')

            # Initialize resources
            self.stop_words = set(stopwords.words('english'))
            self.vectorizer = TfidfVectorizer()

            # Bot detection thresholds
            self.thresholds = {
                'repeat_phrase_threshold': 0.3,  # Max allowable phrase repetition
                'template_similarity_threshold': 0.8,  # Similarity threshold for template detection
                'time_pattern_threshold': 0.7,  # Threshold for suspicious timing patterns
                'complexity_threshold': 0.4,  # Minimum complexity score
            }

            logger.info("NLTK initialization complete")
        except Exception as e:
            logger.error(f"Error initializing NLTK: {str(e)}")
            self.stop_words = set()
            self.vectorizer = TfidfVectorizer()

    def analyze_comments(self, comments: List[str], timestamps: List[datetime] = None) -> Dict:
        """Enhanced comment analysis with bot detection features."""
        if not comments:
            return self._get_empty_metrics()

        try:
            # Basic metrics
            metrics = self._calculate_basic_metrics(comments)

            # Enhanced bot detection metrics
            bot_metrics = {
                'repetition_score': self._analyze_repetition(comments),
                'template_score': self._detect_templates(comments),
                'timing_score': self._analyze_timing_patterns(timestamps) if timestamps else 0.0,
                'complexity_score': self._analyze_complexity(comments),
                'copy_paste_score': self._detect_copy_paste(comments),
                'suspicious_patterns': self._identify_suspicious_patterns(comments)
            }

            metrics.update(bot_metrics)

            # Calculate overall bot probability
            metrics['bot_probability'] = self._calculate_bot_probability(bot_metrics)

            return metrics
        except Exception as e:
            logger.error(f"Error analyzing comments: {str(e)}")
            return self._get_empty_metrics()

    def _calculate_basic_metrics(self, comments: List[str]) -> Dict:
        """Calculate basic text metrics."""
        combined_text = ' '.join(comments)
        tokens = word_tokenize(combined_text.lower())
        tokens = [t for t in tokens if t.isalnum() and t not in self.stop_words]

        return {
            'vocab_size': len(set(tokens)),
            'avg_word_length': np.mean([len(t) for t in tokens]) if tokens else 0,
            'common_words': dict(Counter(tokens).most_common(10))
        }

    def _analyze_repetition(self, comments: List[str]) -> float:
        """Analyze text for repetitive phrases."""
        if not comments:
            return 0.0

        # Extract phrases (3-5 words) from all comments
        phrases = []
        for comment in comments:
            words = comment.lower().split()
            for i in range(len(words)-2):
                for j in range(3, 6):
                    if i + j <= len(words):
                        phrases.append(' '.join(words[i:i+j]))

        # Calculate phrase frequencies
        phrase_counts = Counter(phrases)
        if not phrase_counts:
            return 0.0

        # Calculate repetition score
        max_repeat_ratio = max(count/len(comments) for count in phrase_counts.values())
        return min(1.0, max_repeat_ratio / self.thresholds['repeat_phrase_threshold'])

    def _detect_templates(self, comments: List[str]) -> float:
        """Detect usage of template-like responses."""
        if len(comments) < 2:
            return 0.0

        try:
            # Convert comments to TF-IDF vectors
            tfidf_matrix = self.vectorizer.fit_transform(comments)
            similarity_matrix = (tfidf_matrix * tfidf_matrix.T).toarray()

            # Calculate average similarity excluding self-similarity
            n = len(comments)
            total_similarity = 0
            count = 0
            for i in range(n):
                for j in range(i+1, n):
                    total_similarity += similarity_matrix[i][j]
                    count += 1

            avg_similarity = total_similarity / count if count > 0 else 0
            return min(1.0, avg_similarity / self.thresholds['template_similarity_threshold'])
        except:
            return 0.0

    def _analyze_timing_patterns(self, timestamps: List[datetime]) -> float:
        """Analyze comment timing patterns for bot-like behavior."""
        if not timestamps or len(timestamps) < 2:
            return 0.0

        try:
            # Calculate time differences between consecutive comments
            time_diffs = []
            sorted_times = sorted(timestamps)
            for i in range(len(sorted_times)-1):
                diff = (sorted_times[i+1] - sorted_times[i]).total_seconds()
                time_diffs.append(diff)

            # Check for suspiciously regular intervals
            if not time_diffs:
                return 0.0

            std_dev = np.std(time_diffs)
            mean_diff = np.mean(time_diffs)
            variation_coefficient = std_dev / mean_diff if mean_diff > 0 else float('inf')

            # Lower variation coefficient indicates more regular posting patterns
            regularity_score = 1.0 / (1.0 + variation_coefficient)
            return min(1.0, regularity_score / self.thresholds['time_pattern_threshold'])
        except:
            return 0.0

    def _analyze_complexity(self, comments: List[str]) -> float:
        """Analyze language complexity."""
        if not comments:
            return 0.0

        try:
            # Calculate average sentence length and unique words ratio
            total_sentences = 0
            total_words = 0
            unique_words = set()

            for comment in comments:
                sentences = sent_tokenize(comment)
                total_sentences += len(sentences)

                words = word_tokenize(comment.lower())
                words = [w for w in words if w.isalnum()]
                total_words += len(words)
                unique_words.update(words)

            avg_sentence_length = total_words / total_sentences if total_sentences > 0 else 0
            unique_ratio = len(unique_words) / total_words if total_words > 0 else 0

            # Combine metrics into complexity score
            complexity_score = (avg_sentence_length / 20 + unique_ratio) / 2
            return max(0.0, min(1.0, complexity_score / self.thresholds['complexity_threshold']))
        except:
            return 0.0

    def _detect_copy_paste(self, comments: List[str]) -> float:
        """Detect copy-pasted content across comments."""
        if len(comments) < 2:
            return 0.0

        try:
            # Create pairs of comments and check for exact or near-exact matches
            exact_matches = 0
            total_pairs = 0

            for i in range(len(comments)):
                for j in range(i+1, len(comments)):
                    total_pairs += 1
                    if self._is_similar_text(comments[i], comments[j]):
                        exact_matches += 1

            return exact_matches / total_pairs if total_pairs > 0 else 0.0
        except:
            return 0.0

    def _is_similar_text(self, text1: str, text2: str) -> bool:
        """Check if two texts are similar (allowing for minor differences)."""
        # Normalize texts
        t1 = ' '.join(text1.lower().split())
        t2 = ' '.join(text2.lower().split())

        # Calculate similarity ratio
        longer = max(len(t1), len(t2))
        shorter = min(len(t1), len(t2))
        if longer == 0:
            return True

        edit_distance = self._levenshtein_distance(t1, t2)
        similarity = 1.0 - (edit_distance / longer)
        return similarity > 0.9

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate the Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _identify_suspicious_patterns(self, comments: List[str]) -> Dict[str, int]:
        """Identify suspicious patterns in comments."""
        patterns = {
            'identical_greetings': 0,
            'url_patterns': 0,
            'promotional_phrases': 0,
            'generic_responses': 0
        }

        # Common bot patterns
        greeting_patterns = r'\b(hi|hello|hey|greetings)\b.*'
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        promo_patterns = r'\b(check out|visit|click|buy|discount|offer)\b'
        generic_patterns = r'\b(thanks for sharing|great post|nice one|good point)\b'

        for comment in comments:
            comment_lower = comment.lower()

            if re.match(greeting_patterns, comment_lower):
                patterns['identical_greetings'] += 1
            if re.search(url_pattern, comment):
                patterns['url_patterns'] += 1
            if re.search(promo_patterns, comment_lower):
                patterns['promotional_phrases'] += 1
            if re.search(generic_patterns, comment_lower):
                patterns['generic_responses'] += 1

        return patterns

    def _calculate_bot_probability(self, metrics: Dict) -> float:
        """Calculate overall bot probability based on all metrics."""
        weights = {
            'repetition_score': 0.25,
            'template_score': 0.2,
            'timing_score': 0.2,
            'complexity_score': 0.15,
            'copy_paste_score': 0.2
        }

        weighted_sum = sum(weights[key] * metrics[key] for key in weights if key in metrics)
        return min(1.0, weighted_sum)

    def _get_empty_metrics(self) -> Dict:
        """Return empty metrics structure."""
        return {
            'vocab_size': 0,
            'avg_word_length': 0,
            'common_words': {},
            'repetition_score': 0.0,
            'template_score': 0.0,
            'timing_score': 0.0,
            'complexity_score': 0.0,
            'copy_paste_score': 0.0,
            'suspicious_patterns': {
                'identical_greetings': 0,
                'url_patterns': 0,
                'promotional_phrases': 0,
                'generic_responses': 0
            },
            'bot_probability': 0.0
        }