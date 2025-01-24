import streamlit as st
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
from utils.visualizations import (
    create_score_radar_chart,
    create_activity_heatmap,
    create_subreddit_distribution
)
import pandas as pd

def analyze_single_user(username, reddit_analyzer, text_analyzer, account_scorer):
    """Analyze a single user and return their analysis results."""
    try:
        user_data, comments_df = reddit_analyzer.get_user_data(username)
        activity_patterns = reddit_analyzer.analyze_activity_patterns(comments_df)
        text_metrics = text_analyzer.analyze_comments(comments_df['body'].tolist())
        final_score, component_scores = account_scorer.calculate_score(
            user_data, activity_patterns, text_metrics
        )
        return {
            'username': username,
            'account_age': user_data['created_utc'].strftime('%Y-%m-%d'),
            'karma': user_data['comment_karma'] + user_data['link_karma'],
            'risk_score': (1 - final_score) * 100,
            'ml_risk_score': component_scores.get('ml_risk_score', 0.5) * 100,
            'traditional_risk_score': (1 - sum(v for k, v in component_scores.items() if k != 'ml_risk_score') 
                                     / len([k for k in component_scores if k != 'ml_risk_score'])) * 100,
            'user_data': user_data,
            'activity_patterns': activity_patterns,
            'text_metrics': text_metrics,
            'component_scores': component_scores
        }
    except Exception as e:
        return {
            'username': username,
            'error': str(e)
        }

def main():
    st.set_page_config(page_title="Reddit Account Analyzer", layout="wide")

    st.title("Reddit Account Analysis Tool")
    st.markdown("""
    This tool analyzes Reddit accounts to detect potential bots or purchased accounts.
    Enter usernames to begin the analysis. For bulk analysis, enter multiple usernames separated by commas or newlines.
    """)

    # Initialize analyzers
    reddit_analyzer = RedditAnalyzer()
    text_analyzer = TextAnalyzer()
    account_scorer = AccountScorer()

    # Analysis mode selection
    analysis_mode = st.radio("Analysis Mode:", ["Single User", "Bulk Analysis"])

    if analysis_mode == "Single User":
        username = st.text_input("Enter Reddit Username:", "")
        if username:
            try:
                with st.spinner('Analyzing account...'):
                    result = analyze_single_user(username, reddit_analyzer, text_analyzer, account_scorer)

                    if 'error' in result:
                        st.error(f"Error analyzing account: {result['error']}")
                        return

                    # Display detailed analysis
                    col1, col2 = st.columns(2)

                    with col1:
                        st.subheader("Account Overview")
                        st.write(f"Account Age: {result['account_age']}")
                        st.write(f"Total Karma: {result['karma']}")

                        st.subheader("Risk Analysis")

                        # Traditional Score
                        st.write("Traditional Metrics Score:")
                        st.progress(1 - result['traditional_risk_score']/100)
                        st.write(f"{result['traditional_risk_score']:.1f}% risk based on traditional metrics")

                        # ML-based Score
                        st.write("Machine Learning Score:")
                        st.progress(1 - result['ml_risk_score']/100)
                        st.write(f"{result['ml_risk_score']:.1f}% risk based on ML analysis")

                        # Feedback section
                        st.subheader("Provide Feedback")
                        if st.button("Mark as Legitimate Account"):
                            account_scorer.ml_analyzer.add_training_example(
                                result['user_data'],
                                result['activity_patterns'],
                                result['text_metrics'],
                                is_legitimate=True
                            )
                            st.success("Thank you for your feedback! This will help improve our detection model.")

                        st.plotly_chart(create_score_radar_chart(result['component_scores']))

                    with col2:
                        st.subheader("Activity Patterns")
                        st.plotly_chart(create_activity_heatmap(result['activity_patterns']['activity_hours']))
                        st.plotly_chart(create_subreddit_distribution(result['activity_patterns']['top_subreddits']))

                        st.subheader("Text Analysis")
                        st.write(f"Vocabulary Size: {result['text_metrics']['vocab_size']}")
                        st.write(f"Average Word Length: {result['text_metrics']['avg_word_length']:.2f}")
                        st.write("Common Words:", result['text_metrics']['common_words'])

            except Exception as e:
                st.error(f"Error analyzing account: {str(e)}")

    else:  # Bulk Analysis
        usernames = st.text_area("Enter Reddit Usernames (one per line or comma-separated):", "")
        if usernames:
            # Parse usernames
            usernames = [u.strip() for u in usernames.replace(',', '\n').split('\n') if u.strip()]

            if st.button(f"Analyze {len(usernames)} Accounts"):
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                for i, username in enumerate(usernames):
                    status_text.text(f"Analyzing {username}... ({i+1}/{len(usernames)})")
                    result = analyze_single_user(username, reddit_analyzer, text_analyzer, account_scorer)
                    results.append(result)
                    progress_bar.progress((i + 1) / len(usernames))

                status_text.text("Analysis complete!")

                # Convert results to DataFrame for display
                df = pd.DataFrame([
                    {
                        'Username': r.get('username'),
                        'Account Age': r.get('account_age', 'N/A') if 'error' not in r else 'N/A',
                        'Total Karma': r.get('karma', 'N/A') if 'error' not in r else 'N/A',
                        'ML Risk Score': f"{r.get('ml_risk_score', 'N/A'):.1f}%" if 'error' not in r else 'N/A',
                        'Traditional Risk': f"{r.get('traditional_risk_score', 'N/A'):.1f}%" if 'error' not in r else 'N/A',
                        'Overall Risk': f"{r.get('risk_score', 'N/A'):.1f}%" if 'error' not in r else 'N/A',
                        'Status': 'Success' if 'error' not in r else f"Error: {r['error']}"
                    } for r in results
                ])

                st.subheader("Bulk Analysis Results")
                st.dataframe(df)

                # Download results as CSV
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name="reddit_analysis_results.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    main()