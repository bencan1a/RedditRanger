import streamlit as st
import logging
import traceback
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
from utils.database import AnalysisResult, SessionLocal
from utils.i18n import _, i18n, SUPPORTED_LANGUAGES
from utils.visualizations import (create_score_radar_chart,
                                  create_monthly_activity_table,
                                  create_subreddit_distribution,
                                  create_monthly_activity_chart,
                                  create_bot_analysis_chart)
import pandas as pd
import time
import itertools
import threading
from queue import Queue, Empty
import os
from config.theme import load_theme_files

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize analyzers at the module level
try:
    logger.debug("Initializing analyzers...")
    reddit_analyzer = RedditAnalyzer()
    text_analyzer = TextAnalyzer()
    account_scorer = AccountScorer()
    logger.debug("Analyzers initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize analyzers: {str(e)}", exc_info=True)
    st.error(f"Failed to initialize analyzers: {str(e)}")

# Function to get the translated Mentat litany.
def get_mentat_litany():
    """Get the translated Mentat litany."""
    return [
        _("It is by will alone I set my mind in motion."),
        _("It is by the juice of Sapho that thoughts acquire speed,"),
        _("The lips acquire stains,"),
        _("The stains become a warning."),
        _("It is by will alone I set my mind in motion.")
    ]

def cycle_litany():
    """Creates a cycling iterator of the Mentat litany"""
    return itertools.cycle(get_mentat_litany())


def perform_analysis(username, reddit_analyzer, text_analyzer, account_scorer, result_queue):
    # Perform the analysis in a separate thread
    try:
        logger.debug(f"Starting perform_analysis for user: {username}")

        # Set a timeout for the entire analysis
        logger.debug("Fetching user data...")
        user_data, comments_df, submissions_df = reddit_analyzer.get_user_data(
            username)

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
        comment_texts = comments_df['body'].tolist(
        ) if not comments_df.empty else []
        comment_times = comments_df['created_utc'].tolist(
        ) if not comments_df.empty else None

        logger.debug("Analyzing comment texts...")
        text_metrics = text_analyzer.analyze_comments(comment_texts,
                                                      comment_times)
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
        logger.debug(
            f"Comment karma: {comment_karma} (type: {type(comment_karma)})")
        logger.debug(f"Link karma: {link_karma} (type: {type(link_karma)})")

        # Calculate total karma with explicit type conversion
        total_karma = int(comment_karma) + int(link_karma) if isinstance(
            comment_karma,
            (int, float)) and isinstance(link_karma, (int, float)) else 0
        logger.debug(f"Total karma calculated: {total_karma}")

        # Save to database with proper error handling
        try:
            with SessionLocal() as db:
                bot_probability = (1 -
                                   final_score) * 100  # Convert to percentage
                logger.debug(
                    f"Calculated bot_probability for database: {bot_probability}"
                )
                analysis_result = AnalysisResult.get_or_create(
                    db, username, bot_probability)
                db.commit()
                logger.info(
                    f"Successfully saved analysis results to database for user: {username}"
                )
                logger.debug(
                    f"Database record: id={analysis_result.id}, "
                    f"analysis_count={analysis_result.analysis_count}, "
                    f"last_analyzed={analysis_result.last_analyzed}")
        except Exception as db_error:
            logger.error(
                f"Database error while saving results for {username}: {str(db_error)}",
                exc_info=True)
            # Continue with analysis even if database save fails

        result = {
            'username':
                username,
            'account_age':
                user_data['created_utc'].strftime('%Y-%m-%d'),
            'karma':
                total_karma,
            'risk_score': (1 - final_score) * 100,
            'ml_risk_score':
                component_scores.get('ml_risk_score', 0.5) * 100,
            'traditional_risk_score': (1 - sum(
                float(v) for k, v in component_scores.items()
                if k != 'ml_risk_score' and isinstance(v, (int, float))) / max(
                1,
                len([
                    k for k in component_scores if k != 'ml_risk_score'
                    and isinstance(component_scores[k], (int, float))
                ]))) * 100,
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

        logger.debug("Analysis complete, putting success result in queue")
        # Set result and mark as complete atomically
        result_queue.put(('success', result))
    except Exception as e:
        logger.error(f"Error in perform_analysis: {str(e)}", exc_info=True)
        error_details = f"Error during analysis: {str(e)}\nFull traceback: {traceback.format_exc()}"
        result_queue.put(('error', error_details))


def analyze_single_user(username, reddit_analyzer, text_analyzer, account_scorer):
    # Analyze a single user with background processing
    try:
        logger.debug(f"Starting analysis for user: {username}")

        # Reset state for new analysis
        st.session_state.analysis_complete = False
        st.session_state.analysis_result = None
        st.session_state.analysis_error = None

        # Create results placeholder and clear it immediately
        results_placeholder = st.empty()
        results_placeholder.empty()

        # Create a queue for thread communication
        result_queue = Queue()
        logger.debug("Created result queue")

        # Start analysis in background thread
        analysis_thread = threading.Thread(
            target=perform_analysis,
            args=(username, reddit_analyzer, text_analyzer, account_scorer, result_queue),
            daemon=True
        )
        analysis_thread.start()
        logger.debug("Started analysis thread")

        # Show loading animation while analysis runs
        placeholder = st.empty()
        litany = cycle_litany()  # Get fresh litany iterator for each analysis

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

                # Update loading animation with translated litany
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
            return {
                'username': username,
                'error': st.session_state.analysis_error
            }

        logger.debug("Returning successful analysis result")
        return st.session_state.analysis_result

    except Exception as e:
        logger.error(f"Error in analyze_single_user: {str(e)}", exc_info=True)
        st.session_state.analysis_complete = True
        return {'username': username, 'error': str(e)}


def render_stats_page():
    #Render the statistics page with analysis history
    st.title(_("Analysis Statistics"))

    df = pd.DataFrame()  # Initialize df as an empty DataFrame
    try:
        # Get analysis results from database with retry
        for attempt in range(3):  # Try up to 3 times
            try:
                df = AnalysisResult.get_all_analysis_stats()
                break
            except Exception as e:
                if attempt == 2:  # Last attempt
                    logger.error(
                        f"Failed to fetch analysis stats after 3 attempts: {str(e)}"
                    )
                    st.error(_("Unable to fetch analysis statistics. Please try refreshing the page in a few moments. If the problem persists, the database might be temporarily unavailable."))
                    return
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying... Error: {str(e)}"
                )
                time.sleep(1)  # Wait before retry

        if df.empty:
            st.info(_("No analysis results found in the database yet."))
            return

        # Add search box for username
        search = st.text_input(_("Search by username"))
        if search:
            df = df[df['Username'].str.contains(search, case=False)]

        # Configure the table
        st.dataframe(df,
                     column_config={
                         "Username":
                         st.column_config.TextColumn(_("Username"),
                                                     help=_("Reddit username"),
                                                     max_chars=50),
                         "Last Analyzed":
                         st.column_config.DatetimeColumn(
                             _("Last Analyzed"),
                             help=_("When the analysis was last performed"),
                             format="D MMM YYYY, HH:mm"),
                         "Analysis Count":
                         st.column_config.NumberColumn(
                             _("Times Analyzed"),
                             help=_("Number of times this account was analyzed")),
                         "Bot Probability":
                         st.column_config.TextColumn(
                             _("Bot Probability"),
                             help=_("Likelihood of being a bot"))
                     },
                     hide_index=True,
                     use_container_width=True)
    except Exception as e:
        logger.error(f"Error rendering stats page: {str(e)}", exc_info=True)
        st.error(_("An error occurred while loading the statistics page. Please try refreshing the page."))

def get_risk_class(risk_score):
    if risk_score > 70:
        return "high-risk"
    elif risk_score > 40:
        return "medium-risk"
    return "low-risk"


def load_styles():
    """Load and apply all theme styles and scripts."""
    try:
        theme_files = load_theme_files()

        # Combine all CSS content
        css_content = [
            theme_files['css_variables'],  # CSS variables first
            *theme_files['css_files'].values()  # Then other CSS files
        ]

        # Apply combined CSS
        st.markdown(
            '<style>' + '\n'.join(css_content) + '</style>',
            unsafe_allow_html=True
        )

        # Add JavaScript with proper paths
        js_content = "\n".join([
            f"<script>{js_code}</script>"
            for js_code in theme_files['js_files'].values()
        ])
        st.markdown(js_content, unsafe_allow_html=True)

        logger.debug("Successfully loaded and applied all theme files")
    except Exception as e:
        logger.error(f"Error in load_styles: {str(e)}")
        st.warning("Some styles failed to load. The application may not look correct.")


def main():
    try:
        st.set_page_config(
            page_title="Reddit Mentat Detector | Arrakis",
            layout="wide",
            initial_sidebar_state="collapsed"
        )

        load_styles()

        # Add language selector in sidebar
        st.sidebar.selectbox(
            "Language / Idioma / Langue",
            options=list(SUPPORTED_LANGUAGES.keys()),
            format_func=lambda x: SUPPORTED_LANGUAGES[x],
            key="language"
        )

        # Add page selection in sidebar
        page = st.sidebar.radio(_("Select Page"), [_("Analyzer"), _("Stats")])

        if page == _("Stats"):
            render_stats_page()
        else:
            st.title(_("Thinking Machine Detector"))
            st.markdown(_("Like the calculations of a Mentat, this tool uses advanced cognitive processes to identify Abominable Intelligences among Reddit users. The spice must flow, but the machines must not prevail."))

            analysis_mode = st.radio(_("Analysis Mode:"),
                                   [_("Single Account"), _("Bulk Detection")])

            if analysis_mode == _("Single Account"):
                username = st.text_input(_("Enter Reddit Username:"), "")

                # Create a placeholder for results at the top level
                results_placeholder = st.empty()

                if username:
                    try:
                        # Use results_placeholder to show analysis
                        with results_placeholder.container():
                            result = analyze_single_user(username, reddit_analyzer,
                                                       text_analyzer, account_scorer)

                            if 'error' in result:
                                st.error(
                                    f"{_('Error analyzing account')}: {result['error']}"
                                )
                                return

                            # Main scores row
                            col1, col2 = st.columns(2)
                            with col1:
                                risk_class = get_risk_class(result['risk_score'])
                                # Pre-translate the label
                                original_label = "Thinking Machine Probability"
                                thinking_machine_label = _(original_label)
                                logger.debug(f"Translation attempt - Original: '{original_label}' -> Translated: '{thinking_machine_label}'")
                                st.markdown(
                                    f"""
                                    <div class="risk-score {risk_class}">
                                        {result['risk_score']:.1f}% {thinking_machine_label}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                            with col2:
                                bot_prob = result['bot_probability']
                                bot_risk_class = get_risk_class(bot_prob)
                                # Pre-translate the label
                                original_bot_label = "Bot Probability"
                                bot_probability_label = _(original_bot_label)
                                logger.debug(f"Translation attempt - Original: '{original_bot_label}' -> Translated: '{bot_probability_label}'")
                                st.markdown(
                                    f"""
                                    <div class="risk-score {bot_risk_class}">
                                        {bot_prob:.1f}% {bot_probability_label}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                            # Account Overview section
                            st.subheader(_("Account Overview"))
                            col3, col4 = st.columns(2)
                            with col3:
                                st.markdown(
                                    f"**{_('Account Age')}:** {result['account_age']}"
                                )
                                st.markdown(
                                    f"**{_('Total Karma')}:** {result['karma']:,}")

                            with col4:
                                st.markdown(_("**Top Subreddits**"))
                                for subreddit, count in result[
                                        'activity_patterns'][
                                            'top_subreddits'].items():
                                    st.markdown(
                                        f"• {subreddit}: {count} {_('posts')}")

                            # Activity and Risk Analysis
                            st.subheader(_("Analysis Results"))
                            col5, col6 = st.columns(2)
                            with col5:
                                st.markdown("#### " + _("Activity Overview"))
                                activity_data = create_monthly_activity_table(
                                    result['comments_df'],
                                    result['submissions_df'])
                                st.plotly_chart(
                                    create_monthly_activity_chart(
                                        activity_data),
                                    use_container_width=True,
                                    config={'displayModeBar': False})

                            with col6:
                                st.markdown("#### " + _("Risk Analysis"))
                                radar_chart = create_score_radar_chart(
                                    result['component_scores'])
                                st.plotly_chart(
                                    radar_chart,
                                    use_container_width=True,
                                    config={'displayModeBar': False})

                            # Bot Behavior Analysis
                            st.subheader(_("Bot Behavior Analysis"))
                            description_text = _("Detailed analysis of text patterns, timing patterns, and suspicious behaviors. Higher scores indicate more bot-like characteristics.")
                            st.markdown(description_text)

                            st.plotly_chart(create_bot_analysis_chart(
                                result['text_metrics'],
                                result['activity_patterns']),
                                use_container_width=True,
                                config={'displayModeBar': False})

                            # Suspicious Patterns
                            st.subheader(_("Suspicious Patterns Detected"))
                            col7, col8 = st.columns(2)
                            with col7:
                                st.markdown("#### " + _("Pattern Analysis"))
                                for pattern, value in result['activity_patterns'].items():
                                    if isinstance(value, (int, float)):
                                        # Ensure pattern key is translated
                                        translated_pattern = _(pattern)
                                        st.write(f"• {translated_pattern}: {value}")

                            with col8:
                                suspicious_patterns = result[
                                    'text_metrics'].get(
                                        'suspicious_patterns', {})
                                for pattern, count in suspicious_patterns.items():
                                    # Translate the pattern name
                                    translated_pattern = _(pattern.replace('_', ' ').title())
                                    st.metric(
                                        translated_pattern,
                                        f"{count}%")

                            # Mentat Feedback Section
                            st.markdown("---")
                            st.subheader(_("Improve the Mentat"))
                            feedback_text = _("Help us improve our detection capabilities by providing feedback on the account classification.")
                            st.markdown(feedback_text)

                            feedback_col1, feedback_col2 = st.columns(2)
                            with feedback_col1:
                                if st.button(_("Mark as Human Account")):
                                    account_scorer.ml_analyzer.add_training_example(
                                        result['user_data'],
                                        result['activity_patterns'],
                                        result['text_metrics'],
                                        is_legitimate=True)
                                    st.success(_("Thank you for marking this as a human account!"))

                            with feedback_col2:
                                if st.button(_("Mark as Bot Account")):
                                    account_scorer.ml_analyzer.add_training_example(
                                        result['user_data'],
                                        result['activity_patterns'],
                                        result['text_metrics'],
                                        is_legitimate=False)
                                    st.success(_("Thank you for marking this as a bot account!"))

                    except Exception as e:
                        logger.error(f"Error in analysis: {str(e)}",
                                     exc_info=True)
                        st.error(
                            f"{_('An error occurred during analysis')}: {str(e)}")

            else:  # Bulk Analysis
                usernames = st.text_area(
                    _("Enter Reddit Usernames (one per line or comma-separated):"),
                    "")
                if usernames:
                    usernames = [
                        u.strip()
                        for u in usernames.replace(',', '\n').split('\n')
                        if u.strip()
                    ]

                    if st.button(
                            f"{_('Analyze')} {len(usernames)} { _('Accounts for Thinking Machines')}"
                    ):
                        results = []
                        progress_bar = st.progress(0)
                        status_text = st.empty()

                        for i, username in enumerate(usernames):
                            status_text.text(
                                f"{_('Analyzing')} {username}... ({i+1}/{len(usernames)})"
                            )
                            result = analyze_single_user(
                                username, reddit_analyzer, text_analyzer,
                                account_scorer)
                            results.append(result)
                            progress_bar.progress((i + 1) / len(usernames))

                        status_text.text(_("Analysis complete!"))

                        df = pd.DataFrame([{
                            'Username':
                                r.get('username'),
                            'Account Age':
                                r.get('account_age', 'N/A')
                                if 'error' not in r else 'N/A',
                            'Total Karma':
                                r.get('karma', 'N/A')
                                if 'error' not in r else 'N/A',
                            'Thinking Machine Probability':
                                f"{r.get('risk_score', 'N/A'):.1f}%"
                                if 'error' not in r else 'N/A',
                            'Status':
                                'Success'
                                if 'error' not in r else f"Error: {r['error']}"
                        } for r in results])

                        st.subheader(_("Bulk Analysis Results"))
                        st.dataframe(df)

                        csv = df.to_csv(index=False)
                        st.download_button(
                            label=_("Download Results as CSV"),
                            data=csv,
                            file_name="thinkingmachine_analysis.csv",
                            mime="text/csv")

    except Exception as e:
        st.error(f"{_('Application error')}: {str(e)}")


if __name__ == "__main__":
    main()