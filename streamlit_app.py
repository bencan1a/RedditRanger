import streamlit as st
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
from utils.visualizations import (create_score_radar_chart,
                                  create_monthly_activity_table,
                                  create_subreddit_distribution,
                                  create_monthly_activity_chart,
                                  create_bot_analysis_chart)
import pandas as pd


def load_css():
    st.markdown("""
        <style>
        .grid-container {
            display: flex;
            gap: 20px;
            width: 100%;
            align-items: stretch;
            margin-bottom: 20px;
            flex-direction: row;
        }
        .grid-item {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 5px;
            padding: 20px;
            box-sizing: border-box;
        }
        .grid-item.half-width {
            flex: 1 1 50%;
        }
        .grid-item.full-width {
            flex: 1 1 100%;
        }
        .grid-item.quarter-width {
            flex: 1 1 25%;
        }
        .risk-score {
            font-size: 2.1rem;
            text-align: center;
            padding: 1rem;
            border-radius: 10px;
            margin: 0;
        }
        .info-icon {
            font-size: 1rem;
            color: #E6D5B8;
            margin-left: 8px;
            cursor: help;
            display: inline-block;
            position: relative;
        }
        .tooltip {
            visibility: hidden;
            background-color: rgba(45, 45, 45, 0.95);
            color: #E6D5B8;
            text-align: left;
            padding: 8px 12px;
            border-radius: 6px;
            position: absolute;
            z-index: 1;
            width: 280px;
            bottom: 125%;
            left: 50%;
            margin-left: -140px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 0.85rem;
            line-height: 1.4;
        }
        .info-icon:hover .tooltip {
            visibility: visible;
            opacity: 1;
        }
        .high-risk { background-color: rgba(255, 0, 0, 0.1); }
        .medium-risk { background-color: rgba(255, 165, 0, 0.1); }
        .low-risk { background-color: rgba(0, 255, 0, 0.1); }
        </style>
    """,
                unsafe_allow_html=True)


def get_risk_class(risk_score):
    if risk_score > 70:
        return "high-risk"
    elif risk_score > 40:
        return "medium-risk"
    return "low-risk"


def analyze_single_user(username, reddit_analyzer, text_analyzer,
                        account_scorer):
    """Analyze a single user and return their analysis results."""
    try:
        user_data, comments_df, submissions_df = reddit_analyzer.get_user_data(
            username)
        activity_patterns = reddit_analyzer.analyze_activity_patterns(
            comments_df, submissions_df)

        # Enhanced text analysis with timestamps
        text_metrics = text_analyzer.analyze_comments(
            comments_df['body'].tolist() if not comments_df.empty else [],
            comments_df['created_utc'].tolist()
            if not comments_df.empty else None)

        final_score, component_scores = account_scorer.calculate_score(
            user_data, activity_patterns, text_metrics)

        return {
            'username':
            username,
            'account_age':
            user_data['created_utc'].strftime('%Y-%m-%d'),
            'karma':
            user_data['comment_karma'] + user_data['link_karma'],
            'risk_score': (1 - final_score) * 100,
            'ml_risk_score':
            component_scores.get('ml_risk_score', 0.5) * 100,
            'traditional_risk_score':
            (1 -
             sum(v
                 for k, v in component_scores.items() if k != 'ml_risk_score')
             / len([k
                    for k in component_scores if k != 'ml_risk_score'])) * 100,
            'user_data':
            user_data,
            'activity_patterns':
            activity_patterns,
            'text_metrics':
            text_metrics,
            'component_scores':
            component_scores,
            'comments_df':
            comments_df,
            'submissions_df':
            submissions_df,
            'bot_probability':
            text_metrics.get('bot_probability', 0) * 100
        }
    except Exception as e:
        return {'username': username, 'error': str(e)}


def main():
    st.set_page_config(page_title="Reddit Thinking Machine Detector | Arrakis",
                       layout="wide",
                       initial_sidebar_state="collapsed")

    load_css()

    # Row 1: Header
    st.markdown("""
        <div class="grid-container">
            <div class="grid-item full-width">
                <h1>Thinking Machine Detector</h1>
                <div class='intro-text'>
                Like the Bene Gesserit's ability to detect truth, this tool uses Abominable Intelligence 
                to identify Thinking Machines among Reddit users. The spice must flow, but the machines must not prevail.
                </div>
            </div>
        </div>
    """,
                unsafe_allow_html=True)

    # Initialize analyzers
    reddit_analyzer = RedditAnalyzer()
    text_analyzer = TextAnalyzer()
    account_scorer = AccountScorer()

    analysis_mode = st.radio("Analysis Mode:",
                             ["Single Account", "Bulk Detection"])

    if analysis_mode == "Single Account":
        username = st.text_input("Enter Reddit Username:", "")
        if username:
            try:
                with st.spinner(
                        'Analyzing through Abominable Intelligence...'):
                    result = analyze_single_user(username, reddit_analyzer,
                                                 text_analyzer, account_scorer)

                    if 'error' in result:
                        st.error(f"Error analyzing account: {result['error']}")
                        return

                    # Probabilities section with proper grid layout
                    risk_class = get_risk_class(result['risk_score'])
                    bot_prob = result['bot_probability']
                    bot_risk_class = get_risk_class(bot_prob)

                    st.markdown(f"""
                        <div class="grid-container">
                            <div class="grid-item half-width">
                                <div class="risk-score {risk_class}">
                                    {result['risk_score']:.1f}% Thinking Machine Probability
                                    <span class="info-icon">ⓘ
                                        <span class="tooltip">
                                        • Account age, karma & activity (25%)
                                        • Posting patterns & subreddit diversity (25%)
                                        • Comment analysis & vocabulary (25%)
                                        • ML-based behavior assessment (25%)

                                        Higher score = more bot-like patterns
                                        </span>
                                    </span>
                                </div>
                            </div>
                        </div>
                    """,
                                unsafe_allow_html=True)

                    # Separate markdown for bot probability
                    st.markdown(f"""
                        <div class="grid-container">
                            <div class="grid-item half-width">
                                <div class="risk-score {bot_risk_class}">
                                    {bot_prob:.1f}% Bot Probability
                                    <span class="info-icon">ⓘ
                                        <span class="tooltip">
                                        Bot Probability Score is calculated using:
                                        • Repetitive phrase patterns
                                        • Template response detection
                                        • Timing analysis
                                        • Language complexity
                                        • Suspicious behavior patterns

                                        Higher score = more bot-like patterns
                                        </span>
                                    </span>
                                </div>
                            </div>
                        </div>
                    """,
                                unsafe_allow_html=True)

                    # Overview sections with proper grid layout
                    st.markdown("""
                        <div class="grid-container">
                            <div class="grid-item quarter-width">
                                <h3>Account Overview</h3>
                    """,
                                unsafe_allow_html=True)
                    st.write(f"Account Age: {result['account_age']}")
                    st.write(f"Total Karma: {result['karma']:,}")
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("""
                            <div class="grid-item quarter-width">
                                <h3>Top Subreddits</h3>
                    """,
                                unsafe_allow_html=True)
                    for subreddit, count in result['activity_patterns'][
                            'top_subreddits'].items():
                        st.write(f"{subreddit}: {count} posts")
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("""
                            <div class="grid-item quarter-width">
                                <h3>Activity Overview</h3>
                    """,
                                unsafe_allow_html=True)
                    activity_data = create_monthly_activity_table(
                        result['comments_df'], result['submissions_df'])
                    st.plotly_chart(
                        create_monthly_activity_chart(activity_data),
                        use_container_width=True,
                        config={'displayModeBar': False})
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("""
                            <div class="grid-item quarter-width">
                                <h3>Risk Analysis</h3>
                    """,
                                unsafe_allow_html=True)
                    st.plotly_chart(create_score_radar_chart(
                        result['component_scores']),
                                    use_container_width=True,
                                    config={'displayModeBar': False})
                    st.markdown("</div></div>", unsafe_allow_html=True)

                    # Row 4: Detailed Analysis Header
                    st.markdown("""
                        <div class="grid-container">
                            <div class="grid-item full-width">
                                <h2>Detailed Analysis</h2>
                            </div>
                        </div>
                    """,
                                unsafe_allow_html=True)

                    # Row 5: Bot Behavior Analysis
                    st.markdown("""
                        <div class="grid-container">
                            <div class="grid-item half-width">
                                <h3>Bot Behavior Analysis</h3>
                                <div class='help-text'>
                                This chart shows three key aspects of potential automated behavior:
                                • Text Patterns: How repetitive and template-like the writing is
                                • Timing Patterns: If posting follows suspicious timing patterns
                                • Suspicious Patterns: Frequency of bot-like behavior markers

                                Higher scores (closer to 1.0) indicate more bot-like characteristics.
                                </div>
                            </div>
                            <div class="grid-item half-width">
                    """,
                                unsafe_allow_html=True)
                    st.plotly_chart(create_bot_analysis_chart(
                        result['text_metrics'], result['activity_patterns']),
                                    use_container_width=True,
                                    config={'displayModeBar': False})
                    st.markdown("</div></div>", unsafe_allow_html=True)

                    # Row 6: Suspicious Patterns
                    st.markdown("""
                        <div class="grid-container">
                            <div class="grid-item half-width">
                                <h3>Suspicious Patterns Detected</h3>
                                <div class='help-text'>
                                Shows the percentage of comments that contain specific patterns often associated with bots:
                                • Identical Greetings: Generic hello/hi messages
                                • URL Patterns: Frequency of link sharing
                                • Promotional Phrases: Marketing-like language
                                • Generic Responses: Very basic/template-like replies
                                </div>
                            </div>
                            <div class="grid-item half-width">
                    """,
                                unsafe_allow_html=True)

                    suspicious_patterns = result['text_metrics'].get(
                        'suspicious_patterns', {})
                    st.markdown("""
                        <table class='pattern-table'>
                        <tr>
                            <th>Pattern Type</th>
                            <th>Frequency (%)</th>
                        </tr>
                        """ + "\n".join([
                        f"<tr><td>{pattern.replace('_', ' ').title()}</td><td>{count}%</td></tr>"
                        for pattern, count in suspicious_patterns.items()
                    ]) + "</table>",
                                unsafe_allow_html=True)
                    st.markdown("</div></div>", unsafe_allow_html=True)

                    # Row 7: Divider
                    st.markdown("""
                        <div class="grid-container">
                            <div class="grid-item full-width">
                                <div class="divider"></div>
                            </div>
                        </div>
                    """,
                                unsafe_allow_html=True)

                    # Row 8: Feedback
                    st.markdown("""
                        <div class="grid-container">
                            <div class="grid-item half-width">
                                <h3>Improve the Abominable Intelligence</h3>
                                <p>Help us improve our detection capabilities by marking legitimate human accounts.</p>
                            </div>
                            <div class="grid-item half-width">
                    """,
                                unsafe_allow_html=True)
                    if st.button("Mark as Human Account"):
                        account_scorer.ml_analyzer.add_training_example(
                            result['user_data'],
                            result['activity_patterns'],
                            result['text_metrics'],
                            is_legitimate=True)
                        st.success(
                            "Thank you for your feedback! This will help our Abominable Intelligence become more accurate."
                        )
                    st.markdown("</div></div>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Error analyzing account: {str(e)}")

    else:  # Bulk Analysis
        usernames = st.text_area(
            "Enter Reddit Usernames (one per line or comma-separated):", "")
        if usernames:
            # Parse usernames
            usernames = [
                u.strip() for u in usernames.replace(',', '\n').split('\n')
                if u.strip()
            ]

            if st.button(
                    f"Analyze {len(usernames)} Accounts for Thinking Machines"
            ):
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                for i, username in enumerate(usernames):
                    status_text.text(
                        f"Analyzing {username}... ({i+1}/{len(usernames)})")
                    result = analyze_single_user(username, reddit_analyzer,
                                                 text_analyzer, account_scorer)
                    results.append(result)
                    progress_bar.progress((i + 1) / len(usernames))

                status_text.text("Analysis complete!")

                # Convert results to DataFrame for display
                df = pd.DataFrame([{
                    'Username':
                    r.get('username'),
                    'Account Age':
                    r.get('account_age', 'N/A') if 'error' not in r else 'N/A',
                    'Total Karma':
                    r.get('karma', 'N/A') if 'error' not in r else 'N/A',
                    'Thinking Machine Probability':
                    f"{r.get('risk_score', 'N/A'):.1f}%"
                    if 'error' not in r else 'N/A',
                    'Status':
                    'Success' if 'error' not in r else f"Error: {r['error']}"
                } for r in results])

                st.subheader("Bulk Analysis Results")
                st.dataframe(df)

                # Download results as CSV
                csv = df.to_csv(index=False)
                st.download_button(label="Download Results as CSV",
                                   data=csv,
                                   file_name="thinking_machine_analysis.csv",
                                   mime="text/csv")


if __name__ == "__main__":
    main()
