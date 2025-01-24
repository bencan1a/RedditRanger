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

def load_css():
    with open('static/style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def get_risk_class(risk_score):
    if risk_score > 70:
        return "high-risk"
    elif risk_score > 40:
        return "medium-risk"
    return "low-risk"

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
    st.set_page_config(
        page_title="Reddit Thinking Machine Detector | Arrakis",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    load_css()

    # Title section with Dune-inspired description
    st.title("Thinking Machine Detector")
    st.markdown("""
    <div class='intro-text'>
    Like the Bene Gesserit's ability to detect truth, this tool uses Abominable Intelligence 
    to identify Thinking Machines among Reddit users. The spice must flow, but the machines must not prevail.
    </div>
    """, unsafe_allow_html=True)

    # Initialize analyzers
    reddit_analyzer = RedditAnalyzer()
    text_analyzer = TextAnalyzer()
    account_scorer = AccountScorer()

    # Analysis mode selection
    analysis_mode = st.radio("Analysis Mode:", ["Single Account", "Bulk Detection"])

    if analysis_mode == "Single Account":
        username = st.text_input("Enter Reddit Username:", "")
        if username:
            try:
                with st.spinner('Analyzing through Abominable Intelligence...'):
                    result = analyze_single_user(username, reddit_analyzer, text_analyzer, account_scorer)

                    if 'error' in result:
                        st.error(f"Error analyzing account: {result['error']}")
                        return

                    # Display risk score prominently
                    risk_class = get_risk_class(result['risk_score'])
                    st.markdown(f"""
                        <div class='risk-score {risk_class}'>
                            {result['risk_score']:.1f}% Thinking Machine Probability
                        </div>
                    """, unsafe_allow_html=True)

                    # Account overview and feedback
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        st.markdown("""
                        <div class='account-overview'>
                            <h3>Account Overview</h3>
                            <div class='overview-content'>
                        """, unsafe_allow_html=True)
                        st.write(f"Account Age: {result['account_age']}")
                        st.write(f"Total Karma: {result['karma']:,}")

                        # Feedback section
                        st.subheader("Improve the Abominable Intelligence")
                        if st.button("Mark as Human Account"):
                            account_scorer.ml_analyzer.add_training_example(
                                result['user_data'],
                                result['activity_patterns'],
                                result['text_metrics'],
                                is_legitimate=True
                            )
                            st.success("Thank you for your feedback! This will help our Abominable Intelligence become more accurate.")
                        st.markdown("</div></div>", unsafe_allow_html=True)

                    # Charts section
                    st.markdown("<div class='charts-grid'>", unsafe_allow_html=True)

                    # Radar Chart
                    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                    st.plotly_chart(create_score_radar_chart(result['component_scores']), use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                    # Activity Heatmap
                    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                    st.plotly_chart(create_activity_heatmap(result['activity_patterns']['activity_hours']), use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                    # Subreddit Distribution
                    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                    st.plotly_chart(create_subreddit_distribution(result['activity_patterns']['top_subreddits']), use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Error analyzing account: {str(e)}")

    else:  # Bulk Analysis
        usernames = st.text_area("Enter Reddit Usernames (one per line or comma-separated):", "")
        if usernames:
            # Parse usernames
            usernames = [u.strip() for u in usernames.replace(',', '\n').split('\n') if u.strip()]

            if st.button(f"Analyze {len(usernames)} Accounts for Thinking Machines"):
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
                        'Thinking Machine Probability': f"{r.get('risk_score', 'N/A'):.1f}%" if 'error' not in r else 'N/A',
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
                    file_name="thinking_machine_analysis.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    main()