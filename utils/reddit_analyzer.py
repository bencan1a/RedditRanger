import praw
from datetime import datetime, timezone
import pandas as pd
import os

class RedditAnalyzer:
    def __init__(self):
        self.reddit = praw.Reddit(
            client_id=os.environ.get('REDDIT_CLIENT_ID'),
            client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
            user_agent="BotDetector/1.0"
        )

    def get_user_data(self, username):
        try:
            user = self.reddit.redditor(username)
            user_data = {
                'created_utc': datetime.fromtimestamp(user.created_utc, tz=timezone.utc),
                'comment_karma': user.comment_karma,
                'link_karma': user.link_karma,
                'verified_email': user.has_verified_email,
            }

            # Collect recent comments
            comments = []
            for comment in user.comments.new(limit=100):
                comments.append({
                    'body': comment.body,
                    'created_utc': datetime.fromtimestamp(comment.created_utc, tz=timezone.utc),
                    'score': comment.score,
                    'subreddit': str(comment.subreddit)
                })

            return user_data, pd.DataFrame(comments)
        except Exception as e:
            raise Exception(f"Error fetching user data: {str(e)}")

    def analyze_activity_patterns(self, comments_df):
        if comments_df.empty:
            return {}

        # Convert to user's local timezone
        comments_df['hour'] = comments_df['created_utc'].dt.hour

        patterns = {
            'total_comments': len(comments_df),
            'unique_subreddits': comments_df['subreddit'].nunique(),
            'avg_score': comments_df['score'].mean(),
            'activity_hours': comments_df['hour'].value_counts().to_dict(),
            'top_subreddits': comments_df['subreddit'].value_counts().head(5).to_dict()
        }

        return patterns