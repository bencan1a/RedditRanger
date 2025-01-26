import streamlit as st
import logging
import traceback
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
from utils.database import AnalysisResult, SessionLocal
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

# Mentat Sapho Juice Litany
MENTAT_LITANY = [
    "It is by will alone I set my mind in motion.",
    "It is by the juice of Sapho that thoughts acquire speed,",
    "The lips acquire stains,", "The stains become a warning.",
    "It is by will alone I set my mind in motion."
]


def cycle_litany():
    #Creates a cycling iterator of the Mentat litany
    return itertools.cycle(MENTAT_LITANY)


def perform_analysis(username, reddit_analyzer, text_analyzer, account_scorer,
                     result_queue):
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


def analyze_single_user(username, reddit_analyzer, text_analyzer,
                        account_scorer):
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
        analysis_thread = threading.Thread(target=perform_analysis,
                                           args=(username, reddit_analyzer,
                                                 text_analyzer, account_scorer,
                                                 result_queue),
                                           daemon=True)
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
                """,
                                    unsafe_allow_html=True)
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error during analysis loop: {str(e)}",
                             exc_info=True)
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
            logger.error(
                f"Returning error result: {st.session_state.analysis_error}")
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
            opacity: 1;
            transform: translateY(0);
            transition: opacity 0.3s ease-out, transform 0.3s ease-out;
        }

        .grid-container.fade-out {
            opacity: 0;
            transform: translateY(20px);
        }

        .grid-item {
            background: linear-gradient(145deg, rgba(44, 26, 15, 0.8), rgba(35, 20, 12, 0.95));
            border: 1px solid rgba(255, 152, 0, 0.1);
            border-radius: 8px;
            padding: 20px;
            box-sizing: border-box;
            box-shadow: 0 4px 12px rgba(255, 152, 0, 0.05);
            backdrop-filter: blur(8px);
        }
        .grid-item.half-width { flex: 0 0 50%; }
        .grid-item.full-width { flex: 0 0 100%; }
        .grid-item.quarter-width { flex: 0 0 25%; }

        .risk-score {
            font-family: 'Space Mono', monospace;
            font-size: 1.8rem;
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

        #sand-background {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: -1;
        }

        /* Add semi-transparent overlay to improve text readability */
        .stApp {
            background: linear-gradient(rgba(35, 20, 12, 0.85), rgba(44, 26, 15, 0.9));
        }


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
            animation: glow 1.5s ease-in-out infinite alternate;
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.5s ease-out, transform 0.5s ease-out;
        }

        .mentat-litany.visible {
            opacity: 1;
            transform: translateY(0);
        }

        .mentat-litany .char {
            opacity: 0;
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

        /* Add loading spinner style */
        .mentat-spinner {
            width: 40px;
            height: 40px;
            margin: 20px auto;
            border: 3px solid rgba(255, 152, 0, 0.1);
            border-top: 3px solid #FF9800;
            border-radius: 50%;
            animation: spin 1s ease-in-out infinite;
            position: relative;
        }

        .mentat-spinner::before {
            content: '';
            position: absolute;
            top: -3px;
            left: -3px;
            right: -3px;
            bottom: -3px;
            border: 3px solid transparent;
            border-top: 3px solid rgba(255, 152, 0, 0.3);
            border-radius: 50%;
            animation: spin-reverse 2s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @keyframes spin-reverse {
            0% { transform: rotate(360deg); }
            100% { transform: rotate(0deg); }
        }
        </style>

        <script>
        function animateText(text) {
            const container = document.querySelector('.mentat-litany');
            if (!container) return;

            container.innerHTML = '';
            container.classList.remove('visible');

            // Add characters with delay
            [...text].forEach((char, i) => {
                const span = document.createElement('span');
                span.textContent = char;
                span.className = 'char';
                span.style.animationDelay = `${i * 50}ms`;
                container.appendChild(span);
            });

            // Show container
            requestAnimationFrame(() => {
                container.classList.add('visible');
            });
        }

        function fadeOutPreviousResults() {
            const containers = document.querySelectorAll('.grid-container');
            containers.forEach(container => {
                container.classList.add('fade-out');
                setTimeout(() => {
                    container.remove();
                }, 300); // Match transition duration
            });
        }

        // Expose the function globally for Streamlit to call
        window.fadeOutPreviousResults = fadeOutPreviousResults;
        </script>
    """, unsafe_allow_html=True)


def load_js():
    """Load all JavaScript code including shaders and Three.js initialization"""
    st.markdown(f"""
        <div id="sand-background"></div>
        <script src="/static/shaders.js"></script>
        <script>
        // Initialize Three.js and create sand effect
        if (!window.threeJsLoaded) {{
            const script = document.createElement('script');
            script.src = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js";
            script.onload = function() {{
                window.threeJsLoaded = true;
                initSandEffect();
            }};
            document.body.appendChild(script);
        }}

        function initSandEffect() {{
            const container = document.getElementById('sand-background');
            if (!container) return;

            const scene = new THREE.Scene();
            const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
            const renderer = new THREE.WebGLRenderer({{ alpha: true }});

            function resize() {{
                renderer.setSize(window.innerWidth, window.innerHeight);
            }}
            window.addEventListener('resize', resize);
            resize();
            container.appendChild(renderer.domElement);

            const uniforms = {{
                time: {{ value: 0 }},
                resolution: {{ value: new THREE.Vector2() }}
            }};

            const material = new THREE.ShaderMaterial({{
                uniforms: uniforms,
                vertexShader: window.SAND_SHADERS.vertexShader,
                fragmentShader: window.SAND_SHADERS.fragmentShader
            }});

            const geometry = new THREE.PlaneGeometry(2, 2);
            const mesh = new THREE.Mesh(geometry, material);
            scene.add(mesh);

            function animate(time) {{
                if (!window.threeJsLoaded) return;
                uniforms.time.value = time * 0.001;
                renderer.render(scene, camera);
                requestAnimationFrame(animate);
            }}
            requestAnimationFrame(animate);
        }}
        </script>""", unsafe_allow_html=True)


def render_stats_page():
    #Render the statistics page with analysis history
    st.title("Analysis Statistics")

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
                    st.error("""
                        Unable to fetch analysis statistics. 
                        Please try refreshing the page in a few moments.

                        If the problem persists, the database might be temporarily unavailable.
                    """)
                    return
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying... Error: {str(e)}"
                )
                time.sleep(1)  # Wait before retry

        if df.empty:

            st.info("No analysis results found in the database yet.")
            return

        # Add search box for username
        search = st.text_input("Search by username")
        if search:
            df = df[df['Username'].str.contains(search, case=False)]

        # Configure the table
        st.dataframe(df,
                     column_config={
                         "Username":
                         st.column_config.TextColumn("Username",
                                                     help="Reddit username",
                                                     max_chars=50),
                         "Last Analyzed":
                         st.column_config.DatetimeColumn(
                             "Last Analyzed",
                             help="When the analysis was last performed",
                             format="D MMM YYYY, HH:mm"),
                         "Analysis Count":
                         st.column_config.NumberColumn(
                             "Times Analyzed",
                             help="Number of times this account was analyzed"),
                         "Bot Probability":
                         st.column_config.TextColumn(
                             "Bot Probability",
                             help="Likelihood of being a bot")
                     },
                     hide_index=True,
                     use_container_width=True)
    except Exception as e:
        logger.error(f"Error rendering stats page: {str(e)}", exc_info=True)
        st.error("""
            An error occurred while loading the statistics page.
            Please try refreshing the page.
        """)


def get_risk_class(risk_score):
    if risk_score > 70:
        return "high-risk"
    elif risk_score > 40:
        return "medium-risk"
    return "low-risk"


def main():
    try:
        st.set_page_config(page_title="Reddit Mentat Detector | Arrakis",
                           layout="wide",
                           initial_sidebar_state="collapsed")

        load_css()

        # Only load JS when needed
        if st.session_state.get('load_js', True):
            load_js()
            st.session_state['load_js'] = False

        # Add page selection in sidebar
        page = st.sidebar.radio("Select Page", ["Analyzer", "Stats"])

        if page == "Stats":
            render_stats_page()
        else:
            st.title("Thinking Machine Detector")
            st.markdown("""
                Like the calculations of a Mentat, this tool uses advanced cognitive processes 
                to identify Abominable Intelligences among Reddit users. The spice must flow, but the machines must not prevail.
            """)

            analysis_mode = st.radio("Analysis Mode:",
                                     ["Single Account", "Bulk Detection"])

            if analysis_mode == "Single Account":
                username = st.text_input("Enter Reddit Username:", "")

                # Create a placeholder for results at the top level
                results_placeholder = st.empty()

                if username:
                    # Clear any previous results immediately when username changes
                    if 'prev_username' not in st.session_state or st.session_state.prev_username != username:
                        results_placeholder.empty()
                        st.session_state.prev_username = username

                    try:
                        # Use results_placeholder to show analysis
                        with results_placeholder.container():
                            #Added this line to remove previous results before showing new ones.
                            st.markdown(
                                "<script>fadeOutPreviousResults()</script>",
                                unsafe_allow_html=True)
                            result = analyze_single_user(
                                username, reddit_analyzer, text_analyzer,
                                account_scorer)
                            if 'error' in result:
                                st.error(
                                    f"Error analyzing account: {result['error']}"
                                )
                                with st.expander(
                                        "See detailed error information"):
                                    st.code(result['error'])
                                return

                            # Main scores row
                            col1, col2 = st.columns(2)
                            with col1:
                                risk_class = get_risk_class(
                                    result['risk_score'])
                                st.markdown(f"""
                                    <div class="risk-score {risk_class}">
                                        {result['risk_score']:.1f}% Thinking Machine Probability
                                        <span class="info-icon">ⓘ<span class="tooltip">
                                            Score breakdown:
                                            • Account age, karma & activity (25%)
                                            • Posting patterns & subreddit diversity (25%)
                                            • Comment analysis & vocabulary (25%)
                                            • ML-based behavior assessment (25%)
                                        </span></span>
                                    </div>
                                """,
                                            unsafe_allow_html=True)

                            with col2:
                                bot_prob = result['bot_probability']
                                bot_risk_class = get_risk_class(bot_prob)
                                st.markdown(f"""
                                    <div class="risk-score {bot_risk_class}">
                                        {bot_prob:.1f}% Bot Probability
                                        <span class="info-icon">ⓘ<span class="tooltip">
                                            Based on:
                                            • Repetitive phrase patterns
                                            • Template response detection
                                            •Timing analysis
                                            • Language complexity
                                            •Suspicious behavior patterns
                                        </span></span>
                                    </div>
                                """,
                                            unsafe_allow_html=True)

                            # Account Overview section
                            st.subheader("Account Overview")
                            col3, col4 = st.columns(2)
                            with col3:
                                st.markdown(
                                    f"**Account Age:** {result['account_age']}"
                                )
                                st.markdown(
                                    f"**Total Karma:** {result['karma']:,}")

                            with col4:
                                st.markdown("**Top Subreddits**")
                                for subreddit, count in result[
                                        'activity_patterns'][
                                            'top_subreddits'].items():
                                    st.markdown(
                                        f"• {subreddit}: {count} posts")

                            # Activity and Risk Analysis
                            st.subheader("Analysis Results")
                            col5, col6 = st.columns(2)
                            with col5:
                                st.markdown("#### Activity Overview")
                                activity_data = create_monthly_activity_table(
                                    result['comments_df'],
                                    result['submissions_df'])
                                st.plotly_chart(
                                    create_monthly_activity_chart(
                                        activity_data),
                                    use_container_width=True,
                                    config={'displayModeBar': False})

                            with col6:
                                st.markdown("#### Risk Analysis")
                                radar_chart = create_score_radar_chart(
                                    result['component_scores'])
                                st.plotly_chart(
                                    radar_chart,
                                    use_container_width=True,
                                    config={'displayModeBar': False})

                            # Bot Behavior Analysis
                            st.subheader("Bot Behavior Analysis")
                            st.markdown("""
                                Detailed analysis of text patterns, timing patterns, and suspicious behaviors.
                                Higher scores indicate more bot-like characteristics.
                            """)
                            st.plotly_chart(create_bot_analysis_chart(
                                result['text_metrics'],
                                result['activity_patterns']),
                                                                           use_container_width=True,
                                            config={'displayModeBar': False})

                            # Suspicious Patterns
                            st.subheader("Suspicious Patterns Detected")
                            col7, col8 = st.columns(2)
                            with col7:
                                st.markdown("#### Pattern Analysis")
                                for pattern, value in result['activity_patterns'].items():
                                    if isinstance(value, (int, float)):
                                        st.write(f"• {pattern}: {value}")

                            with col8:
                                suspicious_patterns = result[
                                    'text_metrics'].get(
                                        'suspicious_patterns', {})
                                for pattern, count in suspicious_patterns.items():
                                    st.metric(
                                        pattern.replace('_', ' ').title(),
                                        f"{count}%")

                            # Mentat Feedback Section
                            st.markdown("---")
                            st.subheader("Improve the Mentat")
                            st.markdown("""
                                Help us improve our detection capabilities by providing feedback 
                                                               on the account classification.
                            """)

                            feedback_col1, feedback_col2 = st.columns(2)
                            with feedback_col1:
                                if st.button("Mark as Human Account",
                                             key="human-account-btn"):
                                    account_scorer.ml_analyzer.add_training_example(
                                        result['user_data'],
                                        result['activity_patterns'],
                                        result['text_metrics'],
                                        is_legitimate=True)
                                    st.success(
                                        "Thank you for marking this as a human account! "
                                        "This feedback helps improve our detection."
                                    )

                            with feedback_col2:
                                if st.button("Mark as Bot Account",
                                             key="bot-account-btn"):
                                    account_scorer.ml_analyzer.add_training_example(
                                        result['user_data'],
                                        result['activity_patterns'],
                                        result['text_metrics'],
                                        is_legitimate=False)
                                    st.success(
                                        "Thank you for marking this as a bot account! "
                                        "This feedback helps improve our detection."
                                    )

                    except Exception as e:
                        logger.error(f"Error in analysis: {str(e)}",
                                     exc_info=True)
                        st.error(
                            f"An error occurred during analysis: {str(e)}")

            else:  # Bulk Analysis
                usernames = st.text_area(
                    "Enter Reddit Usernames (one per line or comma-separated):",
                    "")
                if usernames:
                    usernames = [
                        u.strip()
                        for u in usernames.replace(',', '\n').split('\n')
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
                                f"Analyzing {username}... ({i+1}/{len(usernames)})"
                            )
                            result = analyze_single_user(
                                username, reddit_analyzer, text_analyzer,
                                account_scorer)
                            results.append(result)
                            progress_bar.progress((i + 1) / len(usernames))

                        status_text.text("Analysis complete!")

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

                        st.subheader("Bulk Analysis Results")
                        st.dataframe(df)

                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="Download Results as CSV",
                            data=csv,
                            file_name="thinkingmachine_analysis.csv",
                            mime="text/csv")

    except Exception as e:
        st.error(f"Application error: {str(e)}")


if __name__ == "__main__":
    main()