import praw
from datetime import datetime, timezone
import pandas as pd
import os
from prawcore.exceptions import ResponseException, OAuthException
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedditAnalyzer:
    def __init__(self):
        client_id = os.environ.get('REDDIT_CLIENT_ID')
        client_secret = os.environ.get('REDDIT_CLIENT_SECRET')

        if not client_id or not client_secret:
            raise ValueError("Reddit API credentials not found in environment variables")

        try:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent="script:reddit-analyzer:v1.0 (by /u/RedditAnalyzerBot)",
                check_for_async=False
            )
            # Verify connection
            self.reddit.read_only = True
            logger.info("Verifying Reddit API connection...")
            _ = self.reddit.user.me()
            logger.info("Reddit API connection successful")
        except ResponseException as e:
            logger.error(f"Reddit API error: {str(e)}")
            if e.response.status_code == 429:
                raise Exception("Rate limit exceeded. Please try again in a few minutes.")
            elif e.response.status_code == 401:
                raise Exception("Invalid Reddit API credentials. Please check your Client ID and Client Secret.")
            raise Exception(f"Reddit API error: {str(e)}")
        except OAuthException as e:
            logger.error(f"Reddit API authentication error: {str(e)}")
            raise Exception(f"Reddit API authentication error: {str(e)}")
        except Exception as e:
            logger.error(f"Error initializing Reddit client: {str(e)}")
            raise Exception(f"Error initializing Reddit client: {str(e)}")

    def get_user_data(self, username):
        try:
            logger.info(f"Fetching data for user: {username}")
            user = self.reddit.redditor(username)
            # Force a simple API call to verify the user exists
            created_utc = user.created_utc

            user_data = {
                'created_utc': datetime.fromtimestamp(created_utc, tz=timezone.utc),
                'comment_karma': user.comment_karma,
                'link_karma': user.link_karma,
                'verified_email': user.has_verified_email if hasattr(user, 'has_verified_email') else None,
            }

            # Collect recent comments
            comments = []
            try:
                logger.info(f"Fetching recent comments for user: {username}")
                for comment in user.comments.new(limit=100):
                    comments.append({
                        'body': comment.body,
                        'created_utc': datetime.fromtimestamp(comment.created_utc, tz=timezone.utc),
                        'score': comment.score,
                        'subreddit': str(comment.subreddit)
                    })
                logger.info(f"Successfully fetched {len(comments)} comments")
            except Exception as e:
                logger.warning(f"Could not fetch comments for user {username}: {str(e)}")
                if not comments:
                    comments = []

            return user_data, pd.DataFrame(comments)
        except ResponseException as e:
            if e.response.status_code == 404:
                logger.error(f"User '{username}' not found")
                raise Exception(f"User '{username}' not found")
            elif e.response.status_code == 403:
                logger.error(f"Access to user '{username}' data is forbidden")
                raise Exception(f"Access to user '{username}' data is forbidden. The account might be private or suspended.")
            elif e.response.status_code == 429:
                logger.error("Rate limit exceeded")
                raise Exception("Rate limit exceeded. Please try again in a few minutes.")
            logger.error(f"Error fetching user data: {str(e)}")
            raise Exception(f"Error fetching user data: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching user data: {str(e)}")
            raise Exception(f"Error fetching user data: {str(e)}")

    def analyze_activity_patterns(self, comments_df):
        if comments_df.empty:
            return {
                'total_comments': 0,
                'unique_subreddits': 0,
                'avg_score': 0,
                'activity_hours': {},
                'top_subreddits': {}
            }

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