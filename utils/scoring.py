from datetime import datetime, timezone

class AccountScorer:
    def calculate_score(self, user_data, activity_patterns, text_metrics):
        scores = {}
        final_score = 0.0
        
        # Account age score (0-1)
        account_age_days = (datetime.now(timezone.utc) - user_data['created_utc']).days
        scores['age_score'] = min(account_age_days / 365, 1.0)
        
        # Karma score (0-1)
        total_karma = user_data['comment_karma'] + user_data['link_karma']
        scores['karma_score'] = min(total_karma / 10000, 1.0)
        
        # Activity diversity score (0-1)
        subreddit_diversity = min(activity_patterns['unique_subreddits'] / 10, 1.0)
        scores['diversity_score'] = subreddit_diversity
        
        # Text complexity score (0-1)
        vocab_score = min(text_metrics['vocab_size'] / 1000, 1.0)
        scores['text_score'] = vocab_score
        
        # Comment similarity score (0-1, inverted)
        similarity_score = 1.0 - text_metrics.get('avg_similarity', 0.0)
        scores['uniqueness_score'] = similarity_score
        
        # Calculate final weighted score
        weights = {
            'age_score': 0.2,
            'karma_score': 0.2,
            'diversity_score': 0.2,
            'text_score': 0.2,
            'uniqueness_score': 0.2
        }
        
        for score_name, weight in weights.items():
            final_score += scores[score_name] * weight
        
        return final_score, scores
