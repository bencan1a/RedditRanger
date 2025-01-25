import streamlit as st
import logging
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
from utils.visualizations import (
    create_score_radar_chart,
    create_monthly_activity_table,
    create_monthly_activity_chart,
    create_bot_analysis_chart
)
import pandas as pd
import time
import itertools
import threading
from queue import Queue, Empty

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cache initializers
@st.cache_resource
def get_reddit_analyzer():
    try:
        return RedditAnalyzer()
    except Exception as e:
        logger.error(f"Failed to initialize Reddit analyzer: {str(e)}")
        return None

@st.cache_resource
def get_text_analyzer():
    try:
        return TextAnalyzer()
    except Exception as e:
        logger.error(f"Failed to initialize text analyzer: {str(e)}")
        return None

@st.cache_resource
def get_account_scorer():
    try:
        return AccountScorer()
    except Exception as e:
        logger.error(f"Failed to initialize account scorer: {str(e)}")
        return None

# Mentat Sapho Juice Litany - moved to separate file for cleaner main code
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

@st.cache_data(ttl=3600)  # Cache analysis results for 1 hour
def perform_analysis(username, result_queue):
    """Perform the analysis in a separate thread"""
    try:
        logger.debug(f"Starting perform_analysis for user: {username}")

        # Get cached analyzers
        reddit_analyzer = get_reddit_analyzer()
        text_analyzer = get_text_analyzer()
        account_scorer = get_account_scorer()

        if not all([reddit_analyzer, text_analyzer, account_scorer]):
            raise Exception("Failed to initialize analyzers")

        # Set a timeout for the entire analysis
        logger.debug("Fetching user data...")
        user_data, comments_df, submissions_df = reddit_analyzer.get_user_data(username)

        logger.debug(f"User data fetched. Type: {type(user_data)}")
        logger.debug(f"User data contents: {user_data}")

        # Handle empty dataframes
        if comments_df.empty and submissions_df.empty:
            logger.warning("No data found for user")
            result_queue.put(('error', 'No data found for this user'))
            return

        logger.debug("Analyzing activity patterns...")
        activity_patterns = reddit_analyzer.analyze_activity_patterns(
            comments_df, submissions_df)
        logger.debug(f"Activity patterns: {activity_patterns}")

        # Get comment texts safely
        comment_texts = comments_df['body'].tolist() if not comments_df.empty else []
        comment_times = comments_df['created_utc'].tolist() if not comments_df.empty else None

        logger.debug("Analyzing comment texts...")
        text_metrics = text_analyzer.analyze_comments(comment_texts, comment_times)
        logger.debug(f"Text metrics: {text_metrics}")

        # Create default text metrics if analysis fails
        if not text_metrics:
            logger.warning("Text metrics analysis failed, using defaults")
            text_metrics = {
                'vocab_size': 0,
                'avg_similarity': 0.0,
                'bot_probability': 0.0
            }

        logger.debug("Calculating final score...")
        final_score, component_scores = account_scorer.calculate_score(
            user_data, activity_patterns, text_metrics)
        logger.debug(f"Final score: {final_score}")
        logger.debug(f"Component scores: {component_scores}")

        # Log karma values before calculation
        comment_karma = user_data.get('comment_karma', 0)
        link_karma = user_data.get('link_karma', 0)
        logger.debug(f"Comment karma: {comment_karma} (type: {type(comment_karma)})")
        logger.debug(f"Link karma: {link_karma} (type: {type(link_karma)})")

        # Calculate total karma with explicit type conversion
        total_karma = int(comment_karma) + int(link_karma) if isinstance(comment_karma, (int, float)) and isinstance(link_karma, (int, float)) else 0
        logger.debug(f"Total karma calculated: {total_karma}")

        result = {
            'username': username,
            'account_age': user_data['created_utc'].strftime('%Y-%m-%d'),
            'karma': total_karma,
            'risk_score': (1 - final_score) * 100,
            'ml_risk_score': component_scores.get('ml_risk_score', 0.5) * 100,
            'traditional_risk_score': (1 - sum(float(v) for k, v in component_scores.items()
                                           if k != 'ml_risk_score' and isinstance(v, (int, float))) /
                                       max(1, len([k for k in component_scores
                                           if k != 'ml_risk_score' and isinstance(component_scores[k], (int, float))]))) * 100,
            'user_data': user_data,
            'activity_patterns': activity_patterns,
            'text_metrics': text_metrics,
            'component_scores': component_scores,
            'comments_df': comments_df,
            'submissions_df': submissions_df,
            'bot_probability': text_metrics.get('bot_probability', 0) * 100
        }

        logger.debug("Analysis complete, putting success result in queue")
        # Set result and mark as complete atomically
        result_queue.put(('success', result))
    except Exception as e:
        logger.error(f"Error in perform_analysis: {str(e)}", exc_info=True)
        error_details = f"Error during analysis: {str(e)}"
        result_queue.put(('error', error_details))

def analyze_single_user(username, reddit_analyzer, text_analyzer, account_scorer):
    """Analyze a single user with background processing"""
    try:
        logger.debug(f"Starting analysis for user: {username}")

        # Reset state for new analysis
        st.session_state.analysis_complete = False
        st.session_state.analysis_result = None
        st.session_state.analysis_error = None

        # Create a queue for thread communication
        result_queue = Queue()
        logger.debug("Created result queue")

        # Start analysis in background thread
        analysis_thread = threading.Thread(
            target=perform_analysis,
            args=(username, result_queue),
            daemon=True
        )
        analysis_thread.start()
        logger.debug("Started analysis thread")

        # Show loading animation while analysis runs
        placeholder = st.empty()
        litany = cycle_litany()

        # Wait for result with timeout
        timeout = time.time() + 60  # 60 second timeout
        while time.time() < timeout and not st.session_state.analysis_complete:
            try:
                # Check if result is available
                try:
                    status, result = result_queue.get(block=False)
                    logger.debug(f"Got result from queue: status={status}")
                    if status == 'error':
                        logger.error(f"Analysis error: {result}")
                        st.session_state.analysis_error = result
                    else:
                        logger.debug("Analysis successful, storing result")
                        st.session_state.analysis_result = result
                    st.session_state.analysis_complete = True
                    break
                except Empty:
                    # No result yet, continue with animation
                    pass

                # Update loading animation
                litany_text = next(litany)
                placeholder.markdown(f"""
                    <div class="mentat-litany visible">
                        {litany_text}
                    </div>
                """, unsafe_allow_html=True)
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error during analysis loop: {str(e)}", exc_info=True)
                st.session_state.analysis_error = f"Error during analysis: {str(e)}"
                st.session_state.analysis_complete = True
                break

        # Clear loading animation
        placeholder.empty()

        # Handle timeout
        if not st.session_state.analysis_complete:
            logger.warning("Analysis timed out")
            st.session_state.analysis_error = "Analysis timed out. Please try again."
            st.session_state.analysis_complete = True

        # Return result or error
        if st.session_state.analysis_error:
            logger.error(f"Returning error result: {st.session_state.analysis_error}")
            return {'username': username, 'error': st.session_state.analysis_error}

        logger.debug("Returning successful analysis result")
        return st.session_state.analysis_result

    except Exception as e:
        logger.error(f"Error in analyze_single_user: {str(e)}", exc_info=True)
        st.session_state.analysis_complete = True
        return {'username': username, 'error': str(e)}

def load_css():
    """Load CSS from external file for better performance"""
    with open('static/style.css', 'r') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def get_risk_class(risk_score):
    if risk_score > 70:
        return "high-risk"
    elif risk_score > 40:
        return "medium-risk"
    return "low-risk"


def main():
    try:
        st.set_page_config(
            page_title="Reddit Mentat Detector | Arrakis",
            layout="wide",
            initial_sidebar_state="collapsed")

        # Initialize session state variables
        if 'analysis_complete' not in st.session_state:
            st.session_state.analysis_complete = False
        if 'analysis_result' not in st.session_state:
            st.session_state.analysis_result = None
        if 'analysis_error' not in st.session_state:
            st.session_state.analysis_error = None

        # Load CSS asynchronously
        with st.spinner("Initializing interface..."):
            load_css()

        # Basic title and description - simplified initial render
        st.markdown("""
            <div class="grid-container">
                <div class="grid-item full-width">
                    <h1>Thinking Machine Detector</h1>
                    <div class='intro-text'>
                    Like the calculations of a Mentat, this tool uses advanced cognitive processes 
                    to identify Abominable Intelligences among Reddit users.
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)


        analysis_mode = st.radio("Analysis Mode:", ["Single Account", "Bulk Detection"])

        if analysis_mode == "Single Account":
            username = st.text_input("Enter Reddit Username:", "")
            if username:
                try:
                    # Create result queue
                    result_queue = Queue()

                    # Start analysis in background thread
                    analysis_thread = threading.Thread(
                        target=perform_analysis,
                        args=(username, result_queue),
                        daemon=True
                    )
                    analysis_thread.start()

                    # Show loading animation while analysis runs
                    placeholder = st.empty()
                    litany = cycle_litany()

                    # Wait for result with timeout
                    timeout = time.time() + 60  # 60 second timeout
                    while time.time() < timeout and not st.session_state.analysis_complete:
                        try:
                            # Check if result is available
                            try:
                                status, result = result_queue.get(block=False)
                                logger.debug(f"Got result from queue: status={status}")
                                if status == 'error':
                                    logger.error(f"Analysis error: {result}")
                                    st.session_state.analysis_error = result
                                else:
                                    logger.debug("Analysis successful, storing result")
                                    st.session_state.analysis_result = result
                                st.session_state.analysis_complete = True
                                break
                            except Empty:
                                # No result yet, continue with animation
                                pass

                            # Update loading animation
                            litany_text = next(litany)
                            placeholder.markdown(f"""
                                <div class="mentat-litany visible">
                                    {litany_text}
                                </div>
                            """, unsafe_allow_html=True)
                            time.sleep(1)
                        except Exception as e:
                            logger.error(f"Error during analysis loop: {str(e)}", exc_info=True)
                            st.session_state.analysis_error = f"Error during analysis: {str(e)}"
                            st.session_state.analysis_complete = True
                            break

                    # Clear loading animation
                    placeholder.empty()

                    # Handle timeout
                    if not st.session_state.analysis_complete:
                        logger.warning("Analysis timed out")
                        st.session_state.analysis_error = "Analysis timed out. Please try again."
                        st.session_state.analysis_complete = True

                    # Process results
                    if st.session_state.analysis_error:
                        error_msg = st.session_state.analysis_error
                        st.error(f"Error analyzing account: {error_msg}")
                        with st.expander("See detailed error information"):
                            st.code(error_msg)
                        return

                    result = st.session_state.analysis_result
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
                        logger.debug(f"Component scores for radar chart: {result['component_scores']}")
                        radar_chart = create_score_radar_chart(result['component_scores'])
                        st.plotly_chart(
                            radar_chart,
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
                        result = analyze_single_user(username, get_reddit_analyzer(),
                                                     get_text_analyzer(), get_account_scorer())
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

    except Exception as e:
        st.error(f"Application error: {str(e)}")

if __name__ == "__main__":
    main()