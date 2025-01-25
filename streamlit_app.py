import streamlit as st
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
from utils.visualizations import (
    create_score_radar_chart,
    create_monthly_activity_table,
    create_subreddit_distribution,
    create_monthly_activity_chart,
    create_bot_analysis_chart # Added import for the new chart function
)
import pandas as pd

def load_css():
    st.markdown("""
        <style>
        .risk-score {
            font-size: 2.1rem !important;  /* Reduced by ~30% from default 3rem */
            text-align: center;
            padding: 1rem;
            border-radius: 10px;
            margin: 1rem 0;
            position: relative;
            display: inline-block;
        }
        .info-icon {
            font-size: 1rem;
            color: #E6D5B8;
            margin-left: 8px;
            cursor: help;
            position: relative;
            display: inline-block;
        }
        .info-icon .tooltip {
            visibility: hidden;
            background-color: rgba(45, 45, 45, 0.95);
            color: #E6D5B8;
            text-align: left;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.85rem;
            line-height: 1.4;

            /* Position the tooltip */
            position: absolute;
            z-index: 1;
            width: 280px;
            bottom: 125%;
            left: 50%;
            margin-left: -140px;

            /* Fade in/out */
            opacity: 0;
            transition: opacity 0.3s;
        }
        .info-icon:hover .tooltip {
            visibility: visible;
            opacity: 1;
        }
        .chart-container {
            border-radius: 5px;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.05);
            margin: 0 0.5rem;
            height: 100%;
        }
        .chart-divider {
            width: 1px;
            background: rgba(255, 255, 255, 0.1);
            margin: 0 0.5rem;
        }
        .high-risk { background-color: rgba(255, 0, 0, 0.1); }
        .medium-risk { background-color: rgba(255, 165, 0, 0.1); }
        .low-risk { background-color: rgba(0, 255, 0, 0.1); }
        </style>
    """, unsafe_allow_html=True)

def get_risk_class(risk_score):
    if risk_score > 70:
        return "high-risk"
    elif risk_score > 40:
        return "medium-risk"
    return "low-risk"

def analyze_single_user(username, reddit_analyzer, text_analyzer, account_scorer):
    """Analyze a single user and return their analysis results."""
    try:
        user_data, comments_df, submissions_df = reddit_analyzer.get_user_data(username)
        activity_patterns = reddit_analyzer.analyze_activity_patterns(comments_df, submissions_df)

        # Enhanced text analysis with timestamps
        text_metrics = text_analyzer.analyze_comments(
            comments_df['body'].tolist() if not comments_df.empty else [],
            comments_df['created_utc'].tolist() if not comments_df.empty else None
        )

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
            'component_scores': component_scores,
            'comments_df': comments_df,
            'submissions_df': submissions_df,
            'bot_probability': text_metrics.get('bot_probability', 0) * 100
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

    # Title section
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

                    # Display risk score prominently with hover tooltip
                    risk_class = get_risk_class(result['risk_score'])
                    tooltip_text = """
                    • Account age, karma & activity (25%)
                    • Posting patterns & subreddit diversity (25%)
                    • Comment analysis & vocabulary (25%)
                    • ML-based behavior assessment (25%)

                    Higher score = more bot-like patterns"""

                    st.markdown(f"""
                        <div class='risk-score {risk_class}'>
                            {result['risk_score']:.1f}% Thinking Machine Probability
                            <span class='info-icon'>ⓘ
                                <span class='tooltip'>{tooltip_text}</span>
                            </span>
                        </div>
                    """, unsafe_allow_html=True)

                    # Display bot probability score
                    bot_prob = result['bot_probability']
                    risk_class = get_risk_class(bot_prob)
                    tooltip_text = """
                    Bot Probability Score is calculated using:
                    • Repetitive phrase patterns
                    • Template response detection
                    • Timing analysis
                    • Language complexity
                    • Suspicious behavior patterns

                    Higher score = more bot-like patterns"""

                    st.markdown(f"""
                        <div class='risk-score {risk_class}'>
                            {bot_prob:.1f}% Bot Probability
                            <span class='info-icon'>ⓘ
                                <span class='tooltip'>{tooltip_text}</span>
                            </span>
                        </div>
                    """, unsafe_allow_html=True)

                    # Overview and Risk Analysis section
                    overview_cols = st.columns([1, 2])

                    with overview_cols[0]:
                        st.subheader("Account Overview")
                        st.write(f"Account Age: {result['account_age']}")
                        st.write(f"Total Karma: {result['karma']:,}")

                    with overview_cols[1]:
                        st.plotly_chart(
                            create_score_radar_chart(result['component_scores']),
                            use_container_width=True,
                            config={'displayModeBar': False}
                        )

                    # Activity and Subreddits section & Bot Analysis Section
                    activity_cols = st.columns(2)

                    with activity_cols[0]:
                        # Get activity data
                        activity_data = create_monthly_activity_table(
                            result['comments_df'],
                            result['submissions_df']
                        )
                        # Create and display the chart
                        st.plotly_chart(
                            create_monthly_activity_chart(activity_data),
                            use_container_width=True,
                            config={'displayModeBar': False}
                        )

                    with activity_cols[1]:
                        st.subheader("Bot Behavior Analysis")
                        # Display the new bot analysis chart
                        st.plotly_chart(
                            create_bot_analysis_chart(result['text_metrics'], result['activity_patterns']),
                            use_container_width=True,
                            config={'displayModeBar': False}
                        )

                        st.subheader("Suspicious Patterns Detected")
                        suspicious_patterns = result['text_metrics'].get('suspicious_patterns', {})

                        # Create a formatted display of suspicious patterns
                        patterns_md = """
                        | Pattern | Count |
                        |---------|-------|
                        """
                        for pattern, count in suspicious_patterns.items():
                            pattern_name = pattern.replace('_', ' ').title()
                            patterns_md += f"| {pattern_name} | {count} |\n"

                        st.markdown(patterns_md)


                    # Top Subreddits section remains in its original location

                    with activity_cols[1]:
                        st.subheader("Top Subreddits")
                        for subreddit, count in result['activity_patterns']['top_subreddits'].items():
                            st.write(f"{subreddit}: {count} posts")

                    # Feedback section remains in its original location

                    feedback_cols = st.columns([2, 1])
                    with feedback_cols[0]:
                        st.subheader("Improve the Abominable Intelligence")
                        st.write("Help us improve our detection capabilities by marking legitimate human accounts.")

                    with feedback_cols[1]:
                        if st.button("Mark as Human Account"):
                            account_scorer.ml_analyzer.add_training_example(
                                result['user_data'],
                                result['activity_patterns'],
                                result['text_metrics'],
                                is_legitimate=True
                            )
                            st.success("Thank you for your feedback! This will help our Abominable Intelligence become more accurate.")

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