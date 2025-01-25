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
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');

        .grid-container {
            display: flex;
            gap: 20px;
            width: 100%;
            align-items: stretch;
            margin-bottom: 20px;
            flex-direction: row;
        }
        .grid-item {
            background: linear-gradient(145deg, rgba(44, 26, 15, 0.8), rgba(35, 20, 12, 0.95));
            border: 1px solid rgba(255, 152, 0, 0.1);
            border-radius: 8px;
            padding: 20px;
            box-sizing: border-box;
            box-shadow: 0 4px 12px rgba(255, 152, 0, 0.05);
            backdrop-filter: blur(4px);
        }
        .grid-item.half-width { flex: 0 0 50%; }
        .grid-item.full-width { flex: 0 0 100%; }
        .grid-item.quarter-width { flex: 0 0 25%; }

        .risk-score {
            font-family: 'Space Mono', monospace;
            font-size: 2.1rem;
            text-align: center;
            padding: 1.5rem;
            border-radius: 10px;
            margin: 0;
            text-shadow: 0 0 10px rgba(255, 152, 0, 0.3);
            letter-spacing: 0.05em;
        }

        .info-icon {
            font-size: 1rem;
            color: #FFB74D;
            margin-left: 8px;
            cursor: help;
            display: inline-block;
            position: relative;
        }

        .tooltip {
            visibility: hidden;
            background: linear-gradient(145deg, rgba(44, 26, 15, 0.95), rgba(35, 20, 12, 0.98));
            color: #FFB74D;
            text-align: left;
            padding: 12px 16px;
            border-radius: 6px;
            border: 1px solid rgba(255, 152, 0, 0.2);
            position: absolute;
            z-index: 1;
            width: 280px;
            bottom: 125%;
            left: 50%;
            margin-left: -140px;
            opacity: 0;
            transition: opacity 0.3s, transform 0.3s;
            transform: translateY(10px);
            font-family: 'Space Mono', monospace;
            font-size: 0.85rem;
            line-height: 1.4;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .info-icon:hover .tooltip {
            visibility: visible;
            opacity: 1;
            transform: translateY(0);
        }

        .high-risk { 
            background: linear-gradient(145deg, rgba(180, 30, 0, 0.2), rgba(140, 20, 0, 0.3));
            border: 1px solid rgba(255, 50, 0, 0.2);
        }
        .medium-risk { 
            background: linear-gradient(145deg, rgba(255, 152, 0, 0.2), rgba(200, 120, 0, 0.3));
            border: 1px solid rgba(255, 152, 0, 0.2);
        }
        .low-risk { 
            background: linear-gradient(145deg, rgba(0, 180, 0, 0.2), rgba(0, 140, 0, 0.3));
            border: 1px solid rgba(0, 255, 50, 0.2);
        }

        .section-heading {
            font-family: 'Space Mono', monospace;
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            color: #FFB74D;
            letter-spacing: 0.1em;
            display: block;
            text-transform: uppercase;
            text-shadow: 0 0 10px rgba(255, 152, 0, 0.2);
        }

        /* Override Streamlit's default button styles */
        .stButton>button {
            background: linear-gradient(145deg, rgba(44, 26, 15, 0.8), rgba(35, 20, 12, 0.95));
            color: #FFB74D;
            border: 1px solid rgba(255, 152, 0, 0.2);
            font-family: 'Space Mono', monospace;
            letter-spacing: 0.05em;
            transition: all 0.3s ease;
        }

        .stButton>button:hover {
            background: linear-gradient(145deg, rgba(54, 36, 25, 0.8), rgba(45, 30, 22, 0.95));
            border-color: rgba(255, 152, 0, 0.4);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255, 152, 0, 0.1);
        }

        /* Additional Dune-inspired elements */
        div[data-testid="stHeader"] {
            background: linear-gradient(180deg, rgba(44, 26, 15, 0.95), rgba(35, 20, 12, 0.98));
            border-bottom: 1px solid rgba(255, 152, 0, 0.1);
        }

        .intro-text {
            font-family: 'Space Mono', monospace;
            color: #FFB74D;
            font-size: 1.1rem;
            line-height: 1.6;
            margin: 1rem 0;
            text-shadow: 0 0 10px rgba(255, 152, 0, 0.2);
        }
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

    # Row 1: Header - Single markdown call
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
    """, unsafe_allow_html=True)

    # Initialize analyzers and get input
    reddit_analyzer = RedditAnalyzer()
    text_analyzer = TextAnalyzer()
    account_scorer = AccountScorer()

    analysis_mode = st.radio("Analysis Mode:", ["Single Account", "Bulk Detection"])

    if analysis_mode == "Single Account":
        username = st.text_input("Enter Reddit Username:", "")
        if username:
            try:
                with st.spinner('Analyzing through Abominable Intelligence...'):
                    result = analyze_single_user(username, reddit_analyzer,
                                                text_analyzer, account_scorer)

                    if 'error' in result:
                        st.error(f"Error analyzing account: {result['error']}")
                        return

                    # Probabilities section - Single markdown call
                    risk_class = get_risk_class(result['risk_score'])
                    bot_prob = result['bot_probability']
                    bot_risk_class = get_risk_class(bot_prob)

                    st.markdown(f"""
                        <div class="grid-container">
                            <div class="grid-item half-width">
                                <div class="risk-score {risk_class}">
                                    {result['risk_score']:.1f}% Thinking Machine Probability
                                    <span class="info-icon">ⓘ<span class="tooltip">
                                        <ul>
                                            <li>Account age, karma & activity (25%)</li>
                                            <li>Posting patterns & subreddit diversity (25%)</li>
                                            <li>Comment analysis & vocabulary (25%)</li>
                                            <li>ML-based behavior assessment (25%)</li>
                                        </ul>
                                        Higher score = more bot-like patterns
                                    </span></span>
                                </div>
                            </div>
                            <div class="grid-item half-width">
                                <div class="risk-score {bot_risk_class}">
                                    {bot_prob:.1f}% Bot Probability
                                    <span class="info-icon">ⓘ<span class="tooltip">
                                        <ul>
                                            <li>Bot Probability Score is calculated using:</li>
                                            <li>Repetitive phrase patterns</li>
                                            <li>Template response detection</li>
                                            <li>Timing analysis</li>
                                            <li>Language complexity</li>
                                            <li>Suspicious behavior patterns</li>
                                        </ul>
                                        Higher score = more bot-like patterns
                                    </span></span>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    # Overview sections - Single markdown call
                    overview_html = f"""
                        <div class="grid-container">
                            <div class="grid-item half-width">
                                <span class="section-heading">Account Overview</span>
                                <p>Account Age: {result['account_age']}</p>
                                <p>Total Karma: {result['karma']:,}</p>
                            </div>
                            <div class="grid-item half-width">
                                <span class="section-heading">Top Subreddits</span>
                    """

                    # Add subreddit information
                    for subreddit, count in result['activity_patterns']['top_subreddits'].items():
                        overview_html += f"<p>{subreddit}: {count} posts</p>"

                    overview_html += """
                            </div>
                        </div>
                        <div class="grid-container">
                            <div class="grid-item half-width">
                                <span class="section-heading">Activity Overview</span>
                            </div>
                            <div class="grid-item half-width">
                                <span class="section-heading">Risk Analysis</span>
                            </div>
                        </div>
                    """

                    st.markdown(overview_html, unsafe_allow_html=True)

                    # Add charts after the HTML structure
                    col3, col4 = st.columns(2)
                    with col3:
                        activity_data = create_monthly_activity_table(
                            result['comments_df'], result['submissions_df'])
                        st.plotly_chart(
                            create_monthly_activity_chart(activity_data),
                            use_container_width=True,
                            config={'displayModeBar': False})

                    with col4:
                        st.plotly_chart(
                            create_score_radar_chart(result['component_scores']),
                            use_container_width=True,
                            config={'displayModeBar': False})


                    # Bot Behavior Analysis - Single markdown call
                    st.markdown("""
                        <div class="grid-container">
                            <div class="grid-item full-width">
                                <span class="section-heading">Bot Behavior Analysis</span>
                                <span class="info-icon">ⓘ<span class="tooltip">
                                    <ul>
                                        <li>Text Patterns: How repetitive and template-like the writing is</li>
                                        <li>Timing Patterns: If posting follows suspicious timing patterns</li>
                                        <li>Suspicious Patterns: Frequency of bot-like behavior markers</li>
                                    </ul>
                                    
                                    Higher scores (closer to 1.0) indicate more bot-like characteristics.
                                </span></span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    # Add bot analysis chart
                    st.plotly_chart(
                        create_bot_analysis_chart(result['text_metrics'],
                                                 result['activity_patterns']),
                        use_container_width=True,
                        config={'displayModeBar': False})

                    # Row 6: Suspicious Patterns - Single markdown call
                    suspicious_patterns = result['text_metrics'].get('suspicious_patterns', {})
                    patterns_html = "\n".join([
                        f"<tr><td>{pattern.replace('_', ' ').title()}</td><td>{count}%</td></tr>"
                        for pattern, count in suspicious_patterns.items()
                    ])

                    st.markdown(f"""
                        <div class="grid-container">
                            <div class="grid-item half-width">
                                <span class="section-heading">Suspicious Patterns Detected</span>
                                <div class='help-text'>
                                Shows the percentage of comments that contain specific patterns often associated with bots:
                                • Identical Greetings: Generic hello/hi messages
                                • URL Patterns: Frequency of link sharing
                                • Promotional Phrases: Marketing-like language
                                • Generic Responses: Very basic/template-like replies
                                </div>
                            </div>
                            <div class="grid-item half-width">
                                <table class='pattern-table'>
                                    <tr>
                                        <th>Pattern Type</th>
                                        <th>Frequency (%)</th>
                                    </tr>
                                    {patterns_html}
                                </table>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    # Row 7: Divider - Single markdown call
                    st.markdown("""
                        <div class="grid-container">
                            <div class="grid-item full-width">
                                <div class="divider"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    # Row 8: Feedback - Single markdown call
                    st.markdown("""
                        <div class="grid-container">
                            <div class="grid-item full-width">
                                <span class="section-heading">Improve the Abominable Intelligence</span>
                                <p>Help us improve our detection capabilities by providing feedback on the account classification.</p>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Mark as Human Account", key="human-account-btn"):
                            account_scorer.ml_analyzer.add_training_example(
                                result['user_data'],
                                result['activity_patterns'],
                                result['text_metrics'],
                                is_legitimate=True)
                            st.success(
                                "Thank you for marking this as a human account! This feedback helps improve our detection."
                            )

                    with col2:
                        if st.button("Mark as Bot Account", key="bot-account-btn"):
                            account_scorer.ml_analyzer.add_training_example(
                                result['user_data'],
                                result['activity_patterns'],
                                result['text_metrics'],
                                is_legitimate=False)
                            st.success(
                                "Thank you for marking this as a bot account! This feedback helps improve our detection."
                            )

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