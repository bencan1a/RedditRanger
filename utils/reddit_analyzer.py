import praw
from datetime import datetime, timezone
import pandas as pd
import os
from prawcore.exceptions import ResponseException, OAuthException
import logging
from typing import Optional, Dict, Union, Tuple, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedditAnalyzer:
    _instance = None
    _initialized = False
    _reddit_client = None

    def __new__(cls, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(RedditAnalyzer, cls).__new__(cls)
        return cls._instance

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        if not self._initialized:
            self.client_id = client_id or os.environ.get('REDDIT_CLIENT_ID')
            self.client_secret = client_secret or os.environ.get('REDDIT_CLIENT_SECRET')

            if not self.client_id or not self.client_secret:
                raise ValueError("Reddit API credentials not found")

            self._initialized = True

    @property
    def reddit(self):
        """Lazy initialization of Reddit client"""
        if self._reddit_client is None:
            try:
                self._reddit_client = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent="script:reddit-analyzer:v1.0 (by /u/RedditAnalyzerBot)",
                    check_for_async=False,
                    read_only=True
                )
                logger.info("Reddit API connection successful")
            except Exception as e:
                logger.error(f"Error initializing Reddit client: {str(e)}")
                raise
        return self._reddit_client

    def _fetch_user_content(self, user, content_type: str = 'comments', limit: Optional[int] = None) -> List[Dict]:
        """Fetch either comments or submissions for a user."""
        content_list = []
        one_year_ago = datetime.now(timezone.utc).timestamp() - (365 * 24 * 60 * 60)

        try:
            iterator = user.comments.new(limit=limit) if content_type == 'comments' else user.submissions.new(limit=limit)

            logger.info(f"Fetching {content_type} for user {user.name}")
            for item in iterator:
                if item.created_utc < one_year_ago:
                    break

                created_time = datetime.fromtimestamp(item.created_utc, tz=timezone.utc)
                content_dict = {
                    'created_utc': created_time,
                    'score': item.score,
                    'subreddit': str(item.subreddit),
                }

                if content_type == 'comments':
                    content_dict['body'] = item.body
                else:
                    content_dict['title'] = item.title
                    content_dict['is_self'] = item.is_self

                content_list.append(content_dict)

                if len(content_list) % 100 == 0:
                    logger.info(f"Fetched {len(content_list)} {content_type}")

            logger.info(f"Total {content_type} fetched: {len(content_list)}")
            return content_list

        except Exception as e:
            logger.error(f"Error fetching {content_type}: {str(e)}")
            return []

    def get_user_data(self, username: str) -> Tuple[Dict, pd.DataFrame, pd.DataFrame]:
        """Get user data including both comments and submissions."""
        try:
            logger.info(f"Analyzing user: {username}")
            user = self.reddit.redditor(username)

            # Basic user info
            user_data = {
                'created_utc': datetime.fromtimestamp(user.created_utc, tz=timezone.utc),
                'comment_karma': user.comment_karma,
                'link_karma': user.link_karma,
                'verified_email': user.has_verified_email if hasattr(user, 'has_verified_email') else None,
            }

            # Fetch both comments and submissions
            comments = self._fetch_user_content(user, 'comments')
            submissions = self._fetch_user_content(user, 'submissions')

            logger.info(f"Found {len(comments)} comments and {len(submissions)} submissions")

            return (
                user_data,
                pd.DataFrame(comments),
                pd.DataFrame(submissions)
            )

        except ResponseException as e:
            if e.response.status_code == 404:
                raise Exception(f"User '{username}' not found")
            elif e.response.status_code == 403:
                raise Exception(f"Access to user '{username}' data is forbidden")
            raise Exception(f"Error fetching user data: {str(e)}")
        except Exception as e:
            raise Exception(f"Error analyzing user: {str(e)}")

    def analyze_activity_patterns(self, comments_df: pd.DataFrame, submissions_df: pd.DataFrame = None) -> Dict:
        """Analyze activity patterns from both comments and submissions."""
        if comments_df.empty and (submissions_df is None or submissions_df.empty):
            return {
                'total_comments': 0,
                'total_submissions': 0,
                'unique_subreddits': 0,
                'avg_score': 0,
                'activity_hours': {},
                'top_subreddits': {},
                'bot_patterns': {
                    'regular_intervals': 0,
                    'rapid_responses': 0,
                    'automated_timing': 0
                }
            }

        # Analyze comment timings for bot-like patterns
        bot_patterns = self._analyze_timing_patterns(comments_df)

        # Original activity pattern analysis
        all_subreddits = pd.concat([
            comments_df['subreddit'] if not comments_df.empty else pd.Series(),
            submissions_df['subreddit'] if submissions_df is not None and not submissions_df.empty else pd.Series()
        ])

        # Log activity stats
        logger.info(f"Total comments: {len(comments_df)}")
        logger.info(f"Total submissions: {len(submissions_df) if submissions_df is not None else 0}")
        logger.info(f"Unique subreddits: {all_subreddits.nunique()}")

        # Calculate average scores
        comments_avg = comments_df['score'].mean() if not comments_df.empty else 0
        submissions_avg = submissions_df['score'].mean() if submissions_df is not None and not submissions_df.empty else 0

        # Combine timestamps for activity analysis
        all_times = pd.concat([
            comments_df['created_utc'] if not comments_df.empty else pd.Series(),
            submissions_df['created_utc'] if submissions_df is not None and not submissions_df.empty else pd.Series()
        ])

        patterns = {
            'total_comments': len(comments_df),
            'total_submissions': len(submissions_df) if submissions_df is not None else 0,
            'unique_subreddits': all_subreddits.nunique(),
            'avg_comment_score': comments_avg,
            'avg_submission_score': submissions_avg,
            'activity_hours': all_times.dt.hour.value_counts().to_dict(),
            'top_subreddits': all_subreddits.value_counts().head(5).to_dict(),
            'bot_patterns': bot_patterns
        }

        return patterns

    def _analyze_timing_patterns(self, comments_df: pd.DataFrame) -> Dict:
        """Analyze comment timing patterns for bot-like behavior."""
        bot_patterns = {
            'regular_intervals': 0,
            'rapid_responses': 0,
            'automated_timing': 0
        }

        if comments_df.empty:
            return bot_patterns

        try:
            # Sort comments by timestamp
            comments_df = comments_df.sort_values('created_utc')

            # Calculate time differences between consecutive comments
            time_diffs = comments_df['created_utc'].diff().dropna()

            if len(time_diffs) < 2:
                return bot_patterns

            # Convert to seconds
            time_diffs_seconds = time_diffs.dt.total_seconds()

            # Check for regular intervals
            std_dev = time_diffs_seconds.std()
            mean_diff = time_diffs_seconds.mean()
            if mean_diff > 0:
                variation_coef = std_dev / mean_diff
                if variation_coef < 0.5:  # Very regular posting pattern
                    bot_patterns['regular_intervals'] = 1

            # Check for rapid responses (less than 30 seconds between comments)
            rapid_responses = (time_diffs_seconds < 30).sum()
            if rapid_responses > len(time_diffs) * 0.3:  # More than 30% are rapid responses
                bot_patterns['rapid_responses'] = 1

            # Check for automated timing patterns (posting at exact minute marks)
            seconds_distribution = comments_df['created_utc'].dt.second.value_counts()
            if len(seconds_distribution) < 10 and len(comments_df) > 10:
                # Comments cluster around specific seconds
                bot_patterns['automated_timing'] = 1

            return bot_patterns

        except Exception as e:
            logger.error(f"Error analyzing timing patterns: {str(e)}")
            return bot_patterns