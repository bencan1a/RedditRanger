import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

class TextAnalyzer:
    def __init__(self):
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('punkt')
            nltk.download('stopwords')
        
        self.stop_words = set(stopwords.words('english'))
        self.vectorizer = TfidfVectorizer()

    def analyze_comments(self, comments):
        if not comments:
            return {}
        
        # Combine all comments for analysis
        combined_text = ' '.join(comments)
        tokens = word_tokenize(combined_text.lower())
        tokens = [t for t in tokens if t.isalnum() and t not in self.stop_words]
        
        # Calculate basic metrics
        metrics = {
            'vocab_size': len(set(tokens)),
            'avg_word_length': np.mean([len(t) for t in tokens]),
            'common_words': dict(Counter(tokens).most_common(10))
        }
        
        # Calculate comment similarity
        if len(comments) > 1:
            tfidf_matrix = self.vectorizer.fit_transform(comments)
            similarity_matrix = (tfidf_matrix * tfidf_matrix.T).toarray()
            metrics['avg_similarity'] = float(np.mean(similarity_matrix[np.triu_indices_from(similarity_matrix, k=1)]))
        else:
            metrics['avg_similarity'] = 0.0
            
        return metrics
