import streamlit as st
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
import pandas as pd
import time
import itertools

# Mentat Sapho Juice Litany
MENTAT_LITANY = [
    "It is by will alone I set my mind in motion.",
    "It is by the juice of Sapho that thoughts acquire speed,",
    "The lips acquire stains,",
    "The stains become a warning.",
    "It is by will alone I set my mind in motion."
]

def cycle_litany():
    """Creates a cycling iterator of the Mentat litany"""
    return itertools.cycle(MENTAT_LITANY)

def load_css():
    st.markdown("""
        <style>
        .mentat-litany {
            font-family: 'Space Mono', monospace;
            font-size: 1.2rem;
            color: #FFB74D;
            text-align: center;
            padding: 2rem;
            margin: 1rem 0;
            background: linear-gradient(145deg, rgba(44, 26, 15, 0.8), rgba(35, 20, 12, 0.95));
            border: 1px solid rgba(255, 152, 0, 0.1);
            border-radius: 8px;
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.5s ease-out, transform 0.5s ease-out;
        }

        .mentat-litany.visible {
            opacity: 1;
            transform: translateY(0);
        }

        .mentat-litany .char {
            display: inline-block;
            opacity: 0;
            transform: translateY(10px);
            animation: typeChar 0.1s ease-in-out forwards;
        }

        @keyframes typeChar {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes glow {
            from {
                text-shadow: 0 0 5px #FF9800, 0 0 10px #FF9800;
                box-shadow: 0 0 10px rgba(255, 152, 0, 0.2);
            }
            to {
                text-shadow: 0 0 10px #FF9800, 0 0 20px #FF9800;
                box-shadow: 0 0 20px rgba(255, 152, 0, 0.4);
            }
        }
        </style>

        <script>
        function animateText(text) {
            const container = document.querySelector('.mentat-litany');
            if (!container) return;

            // Clear and reset container
            container.innerHTML = '';
            container.classList.remove('visible');

            // Add characters one by one
            [...text].forEach((char, i) => {
                const span = document.createElement('span');
                span.textContent = char === ' ' ? '\u00A0' : char;  // Use non-breaking space for spaces
                span.className = 'char';
                span.style.animationDelay = `${i * 50}ms`;  // 50ms delay between each character
                container.appendChild(span);
            });

            // Show container after a brief delay
            setTimeout(() => {
                container.classList.add('visible');
            }, 100);
        }
        </script>
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
        litany_placeholder = st.empty()
        litany_cycle = cycle_litany()

        while True:
            try:
                # Show the current litany line with animation
                litany_text = next(litany_cycle)
                litany_placeholder.markdown(f"""
                    <div class="mentat-litany">
                        {litany_text}
                    </div>
                    <script>
                        animateText("{litany_text}");
                    </script>
                """, unsafe_allow_html=True)
                time.sleep(2)  # Wait for 2 seconds between transitions

                user_data, comments_df, submissions_df = reddit_analyzer.get_user_data(username)
                activity_patterns = reddit_analyzer.analyze_activity_patterns(
                    comments_df, submissions_df)

                text_metrics = text_analyzer.analyze_comments(
                    comments_df['body'].tolist() if not comments_df.empty else [],
                    comments_df['created_utc'].tolist()
                    if not comments_df.empty else None)

                final_score, component_scores = account_scorer.calculate_score(
                    user_data, activity_patterns, text_metrics)

                litany_placeholder.empty()
                return {
                    'username': username,
                    'account_age': user_data['created_utc'].strftime('%Y-%m-%d'),
                    'karma': user_data['comment_karma'] + user_data['link_karma'],
                    'risk_score': (1 - final_score) * 100,
                    'ml_risk_score': component_scores.get('ml_risk_score', 0.5) * 100,
                    'traditional_risk_score': (1 - sum(v for k, v in component_scores.items()
                                                 if k != 'ml_risk_score') /
                                         len([k for k in component_scores
                                             if k != 'ml_risk_score'])) * 100,
                    'user_data': user_data,
                    'activity_patterns': activity_patterns,
                    'text_metrics': text_metrics,
                    'component_scores': component_scores,
                    'comments_df': comments_df,
                    'submissions_df': submissions_df,
                    'bot_probability': text_metrics.get('bot_probability', 0) * 100
                }
            except Exception as e:
                if 'error' in str(e):
                    raise e
                litany_placeholder.markdown(f"""
                    <div class="mentat-litany">
                        {next(litany_cycle)}
                    </div>
                    <script>
                        animateText("{next(litany_cycle)}");
                    </script>
                """, unsafe_allow_html=True)
                time.sleep(2)
    except Exception as e:
        return {'username': username, 'error': str(e)}

def main():
    st.set_page_config(
        page_title="Reddit Mentat Detector | Arrakis",
        layout="wide",
        initial_sidebar_state="collapsed")

    load_css()

    # Row 1: Header - Single markdown call
    st.markdown("""
        <div class="grid-container">
            <div class="grid-item full-width">
                <h1>Mentat Detector</h1>
                <div class='intro-text'>
                Like the calculations of a Mentat, this tool uses advanced cognitive processes 
                to identify automated behaviors among Reddit users. The spice must flow, but the machines must not prevail.
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
                litany_placeholder = st.empty()
                litany_cycle = cycle_litany()

                with st.spinner(''):
                    while True:
                        try:
                            result = analyze_single_user(username, reddit_analyzer,
                                                          text_analyzer, account_scorer)
                            break
                        except Exception as e:
                            if 'error' in str(e):
                                st.error(f"Error analyzing account: {str(e)}")
                                return
                        litany_placeholder.markdown(f"""
                            <div class="mentat-litany">
                                {next(litany_cycle)}
                            </div>
                        """, unsafe_allow_html=True)
                        time.sleep(2)

                if 'error' in result:
                    st.error(f"Error analyzing account: {result['error']}")
                    return

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

                st.plotly_chart(
                    create_bot_analysis_chart(result['text_metrics'],
                                             result['activity_patterns']),
                    use_container_width=True,
                    config={'displayModeBar': False})

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

                st.markdown("""
                    <div class="grid-container">
                        <div class="grid-item full-width">
                            <div class="divider"></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                st.markdown("""
                    <div class="grid-container">
                        <div class="grid-item full-width">
                            <span class="section-heading">Improve the Mentat</span>
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

                csv = df.to_csv(index=False)
                st.download_button(label="Download Results as CSV",
                                   data=csv,
                                   file_name="thinking_machine_analysis.csv",
                                   mime="text/csv")


if __name__ == "__main__":
    main()