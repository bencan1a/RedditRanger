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
        
    def analyze(self, data: Dict[str, Any]) -> Dict[str, float]:
        if not data['comments']:
            return {
                'similarity_score': 0.8,
                'complexity_score': 0.8,
                'pattern_score': 0.8,
                'style_score': 0.8
            }
            
        comment_texts = [c['body'] for c in data['comments']]
        
        scores = {}
        
        # Analyze text similarity
        scores['similarity_score'] = self._analyze_similarity(comment_texts)
        
        # Analyze text complexity
        scores['complexity_score'] = self._analyze_complexity(comment_texts)
        
        # Analyze suspicious patterns
        scores['pattern_score'] = self._analyze_patterns(comment_texts)
        
        # Analyze writing style consistency
        scores['style_score'] = self._analyze_style(comment_texts)
        
        return scores
        
    def _analyze_similarity(self, texts: List[str]) -> float:
        """Analyze similarity between comments"""
        if len(texts) < 2:
            return 0.8
            
        # Create n-grams for each text
        text_ngrams = []
        for text in texts:
            tokens = word_tokenize(text.lower())
            text_ngrams.append(set(ngrams(tokens, 3)))  # Use trigrams
            
        # Calculate average similarity between all pairs
        similarities = []
        for i in range(len(text_ngrams)):
            for j in range(i + 1, len(text_ngrams)):
                if text_ngrams[i] and text_ngrams[j]:
                    similarity = len(text_ngrams[i] & text_ngrams[j]) / \
                               len(text_ngrams[i] | text_ngrams[j])
                    similarities.append(similarity)
                    
        if not similarities:
            return 0.8
            
        avg_similarity = np.mean(similarities)
        
        if avg_similarity > 0.5:  # Very similar content
            return 0.3
        elif avg_similarity > 0.3:  # Moderately similar
            return 0.5
        elif avg_similarity > 0.1:  # Some similarity
            return 0.7
        return 0.9  # Natural variation
        
    def _analyze_complexity(self, texts: List[str]) -> float:
        """Analyze text complexity"""
        if not texts:
            return 0.8
            
        # Calculate average sentence length and word length
        avg_sent_lengths = []
        avg_word_lengths = []
        
        for text in texts:
            sentences = text.split('.')
            words = word_tokenize(text)
            
            if sentences:
                avg_sent_lengths.append(len(words) / len(sentences))
            if words:
                avg_word_lengths.append(np.mean([len(w) for w in words]))
                
        if not avg_sent_lengths or not avg_word_lengths:
            return 0.8
            
        # Score based on variance and averages
        sent_length_var = np.var(avg_sent_lengths)
        word_length_var = np.var(avg_word_lengths)
        
        if sent_length_var < 1 and word_length_var < 0.5:  # Very uniform
            return 0.4
        elif sent_length_var < 2 and word_length_var < 1:  # Somewhat uniform
            return 0.6
        return 0.8  # Natural variation
        
    def _analyze_patterns(self, texts: List[str]) -> float:
        """Analyze presence of suspicious patterns"""
        pattern_matches = 0
        total_patterns = len(self.suspicious_patterns['template_phrases']) + \
                        len(self.suspicious_patterns['promotional_language'])
        
        for text in texts:
            text_lower = text.lower()
            # Check template phrases
            for pattern in self.suspicious_patterns['template_phrases']:
                if re.search(pattern, text_lower):
                    pattern_matches += 1
            # Check promotional language
            for pattern in self.suspicious_patterns['promotional_language']:
                if re.search(pattern, text_lower):
                    pattern_matches += 1
                    
        pattern_ratio = pattern_matches / (len(texts) * total_patterns)
        
        if pattern_ratio > 0.3:  # High pattern matches
            return 0.3
        elif pattern_ratio > 0.2:  # Moderate matches
            return 0.5
        elif pattern_ratio > 0.1:  # Some matches
            return 0.7
        return 0.9  # Few/no matches
        
    def _analyze_style(self, texts: List[str]) -> float:
        """Analyze consistency of writing style"""
        if len(texts) < 3:  # Need more texts for meaningful analysis
            return 0.8
            
        # Calculate stylometric features
        features = []
        for text in texts:
            words = word_tokenize(text)
            if not words:
                continue
                
            # Calculate basic stylometric features
            avg_word_length = np.mean([len(w) for w in words])
            punct_ratio = len([c for c in text if c in '.,!?;:']) / len(text)
            
            features.append([avg_word_length, punct_ratio])
            
        if not features:
            return 0.8
            
        # Calculate feature variance
        feature_var = np.var(features, axis=0)
        avg_var = np.mean(feature_var)
        
        if avg_var < 0.1:  # Very consistent style
            return 0.4
        elif avg_var < 0.3:  # Somewhat consistent
            return 0.6
        return 0.8  # Natural variation
