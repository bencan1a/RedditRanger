import streamlit as st
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
from utils.visualizations import (
    create_score_radar_chart,
    create_activity_heatmap,
    create_subreddit_distribution
)

def main():
    st.set_page_config(page_title="Reddit Account Analyzer", layout="wide")
    
    st.title("Reddit Account Analysis Tool")
    st.markdown("""
    This tool analyzes Reddit accounts to detect potential bots or purchased accounts.
    Enter a username to begin the analysis.
    """)
    
    # Initialize analyzers
    reddit_analyzer = RedditAnalyzer()
    text_analyzer = TextAnalyzer()
    account_scorer = AccountScorer()
    
    # User input
    username = st.text_input("Enter Reddit Username:", "")
    
    if username:
        try:
            with st.spinner('Analyzing account...'):
                # Fetch and analyze data
                user_data, comments_df = reddit_analyzer.get_user_data(username)
                activity_patterns = reddit_analyzer.analyze_activity_patterns(comments_df)
                text_metrics = text_analyzer.analyze_comments(comments_df['body'].tolist())
                final_score, component_scores = account_scorer.calculate_score(
                    user_data, activity_patterns, text_metrics
                )
                
                # Display results
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Account Overview")
                    st.write(f"Account Age: {(user_data['created_utc']).strftime('%Y-%m-%d')}")
                    st.write(f"Comment Karma: {user_data['comment_karma']}")
                    st.write(f"Link Karma: {user_data['link_karma']}")
                    st.write(f"Verified Email: {user_data['verified_email']}")
                    
                    st.subheader("Analysis Score")
                    st.metric(
                        "Bot/Purchased Account Probability",
                        f"{(1 - final_score) * 100:.1f}%"
                    )
                    
                    st.plotly_chart(create_score_radar_chart(component_scores))
                
                with col2:
                    st.subheader("Activity Patterns")
                    st.plotly_chart(create_activity_heatmap(activity_patterns['activity_hours']))
                    st.plotly_chart(create_subreddit_distribution(activity_patterns['top_subreddits']))
                
                st.subheader("Text Analysis")
                col3, col4 = st.columns(2)
                
                with col3:
                    st.write("Vocabulary Statistics")
                    st.write(f"Vocabulary Size: {text_metrics['vocab_size']}")
                    st.write(f"Average Word Length: {text_metrics['avg_word_length']:.2f}")
                
                with col4:
                    st.write("Common Words")
                    st.write(text_metrics['common_words'])
                
                st.subheader("Analysis Explanation")
                st.markdown("""
                The score is calculated based on:
                - Account age and karma distribution
                - Activity patterns across different times
                - Subreddit diversity
                - Text complexity and uniqueness
                - Comment similarity patterns
                
                Lower scores indicate more natural behavior, while higher scores suggest potential bot or purchased account activity.
                """)
                
        except Exception as e:
            st.error(f"Error analyzing account: {str(e)}")

if __name__ == "__main__":
    main()
