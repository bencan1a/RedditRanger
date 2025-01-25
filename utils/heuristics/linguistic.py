from typing import Dict, Any, List
import re
from collections import Counter
import numpy as np
from nltk.tokenize import word_tokenize
from nltk.util import ngrams
from .base import BaseHeuristic

class LinguisticHeuristic(BaseHeuristic):
    """Analyzes linguistic patterns and writing style"""

    def __init__(self):
        self.suspicious_patterns = {
            'template_phrases': [
                r'thanks for sharing',
                r'great post',
                r'nice work',
                r'check out',
                r'click here'
            ],
            'promotional_language': [
                r'discount',
                r'offer',
                r'limited time',
                r'best price',
                r'check out my'
            ]
        }

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            comments = data.get('comments', [])
            if not comments:
                return self._get_default_scores()

            comment_texts = [c.get('body', '') for c in comments if c.get('body')]
            if not comment_texts:
                return self._get_default_scores()

            # Initialize scores dictionary
            scores = {}

            # Calculate individual scores
            similarity_score = self._analyze_similarity(comment_texts)
            complexity_score = self._analyze_complexity(comment_texts)
            pattern_score = self._analyze_patterns(comment_texts)
            style_score = self._analyze_style(comment_texts)

            # Store scores as float values
            scores['similarity_score'] = float(similarity_score)
            scores['complexity_score'] = float(complexity_score)
            scores['pattern_score'] = float(pattern_score)
            scores['style_score'] = float(style_score)

            # Store metrics separately
            scores['metrics'] = {
                'total_comments': float(len(comment_texts)),
                'avg_comment_length': float(sum(len(t) for t in comment_texts) / max(1, len(comment_texts))),
                'pattern_matches': float(self._count_pattern_matches(comment_texts))
            }

            return scores

        except Exception as e:
            return self._get_default_scores()

    def _get_default_scores(self) -> Dict[str, Any]:
        """Return neutral default scores"""
        return {
            'similarity_score': 0.8,
            'complexity_score': 0.8,
            'pattern_score': 0.8,
            'style_score': 0.8,
            'metrics': {
                'total_comments': 0.0,
                'avg_comment_length': 0.0,
                'pattern_matches': 0.0
            }
        }

    def _count_pattern_matches(self, texts: List[str]) -> int:
        """Count total pattern matches across all texts"""
        count = 0
        for text in texts:
            text_lower = str(text).lower()
            for pattern_list in self.suspicious_patterns.values():
                for pattern in pattern_list:
                    if re.search(pattern, text_lower):
                        count += 1
        return count

    def _analyze_similarity(self, texts: List[str]) -> float:
        """Analyze similarity between comments"""
        if len(texts) < 2:
            return 0.8

        try:
            # Create n-grams for each text
            text_ngrams = []
            for text in texts:
                try:
                    tokens = word_tokenize(str(text).lower())
                    if tokens:
                        text_ngrams.append(set(ngrams(tokens, 3)))  # Use trigrams
                except:
                    continue

            if len(text_ngrams) < 2:
                return 0.8

            # Calculate average similarity between all pairs
            similarities = []
            for i in range(len(text_ngrams)):
                for j in range(i + 1, len(text_ngrams)):
                    if text_ngrams[i] and text_ngrams[j]:
                        union_size = len(text_ngrams[i] | text_ngrams[j])
                        if union_size > 0:  # Prevent division by zero
                            similarity = len(text_ngrams[i] & text_ngrams[j]) / union_size
                            similarities.append(similarity)

            if not similarities:
                return 0.8

            avg_similarity = float(np.mean(similarities))

            if avg_similarity > 0.5:  # Very similar content
                return 0.3
            elif avg_similarity > 0.3:  # Moderately similar
                return 0.5
            elif avg_similarity > 0.1:  # Some similarity
                return 0.7
            return 0.9  # Natural variation
        except:
            return 0.8

    def _analyze_complexity(self, texts: List[str]) -> float:
        """Analyze text complexity"""
        if not texts:
            return 0.8

        try:
            # Calculate average sentence length and word length
            avg_sent_lengths = []
            avg_word_lengths = []

            for text in texts:
                text = str(text)
                sentences = [s for s in text.split('.') if s.strip()]
                words = [w for w in word_tokenize(text) if w.strip()]

                if sentences and words:
                    avg_sent_lengths.append(len(words) / len(sentences))
                if words:
                    avg_word_lengths.append(float(np.mean([len(w) for w in words])))

            if not avg_sent_lengths or not avg_word_lengths:
                return 0.8

            # Score based on variance and averages
            sent_length_var = float(np.var(avg_sent_lengths))
            word_length_var = float(np.var(avg_word_lengths))

            if sent_length_var < 1 and word_length_var < 0.5:  # Very uniform
                return 0.4
            elif sent_length_var < 2 and word_length_var < 1:  # Somewhat uniform
                return 0.6
            return 0.8  # Natural variation
        except:
            return 0.8

    def _analyze_patterns(self, texts: List[str]) -> float:
        """Analyze presence of suspicious patterns"""
        if not texts:
            return 0.8

        try:
            pattern_matches = self._count_pattern_matches(texts)
            total_patterns = len(self.suspicious_patterns['template_phrases']) + \
                           len(self.suspicious_patterns['promotional_language'])

            if total_patterns == 0:
                return 0.8

            pattern_ratio = pattern_matches / (max(1, len(texts)) * total_patterns)

            if pattern_ratio > 0.3:  # High pattern matches
                return 0.3
            elif pattern_ratio > 0.2:  # Moderate matches
                return 0.5
            elif pattern_ratio > 0.1:  # Some matches
                return 0.7
            return 0.9  # Few/no matches
        except:
            return 0.8

    def _analyze_style(self, texts: List[str]) -> float:
        """Analyze consistency of writing style"""
        if len(texts) < 3:
            return 0.8

        try:
            # Calculate stylometric features
            features = []
            for text in texts:
                try:
                    words = word_tokenize(str(text))
                    if not words:
                        continue

                    # Calculate basic stylometric features
                    avg_word_length = float(np.mean([len(w) for w in words]))
                    punct_ratio = len([c for c in text if c in '.,!?;:']) / max(1, len(text))

                    features.append([avg_word_length, punct_ratio])
                except:
                    continue

            if len(features) < 3:  # Need at least 3 samples for meaningful analysis
                return 0.8

            # Calculate feature variance
            feature_var = np.var(features, axis=0)
            avg_var = float(np.mean(feature_var))

            if avg_var < 0.1:  # Very consistent style
                return 0.4
            elif avg_var < 0.3:  # Somewhat consistent
                return 0.6
            return 0.8  # Natural variation
        except:
            return 0.8