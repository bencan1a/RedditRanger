import streamlit as st
import logging
import traceback  # Add traceback import
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
    "The lips acquire stains,",
    "The stains become a warning.",
    "It is by will alone I set my mind in motion."
]

def cycle_litany():
    """Creates a cycling iterator of the Mentat litany"""
    return itertools.cycle(MENTAT_LITANY)

def perform_analysis(username, reddit_analyzer, text_analyzer, account_scorer, result_queue):
    """Perform the analysis in a separate thread"""
    try:
        logger.debug(f"Starting perform_analysis for user: {username}")

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
        error_details = f"Error during analysis: {str(e)}\nFull traceback: {traceback.format_exc()}"
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
            args=(username, reddit_analyzer, text_analyzer, account_scorer, result_queue),
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
                    <div class="mentat-spinner"></div>
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
        </script>

        <!-- Add shader code -->
        <script type="x-shader/x-vertex" id="vertex-shader">
            varying vec2 vUv;
            void main() {
                vUv = uv;
                gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
        </script>

        <script type="x-shader/x-fragment" id="fragment-shader">
            uniform float time;
            uniform vec2 resolution;
            varying vec2 vUv;

            float rand(vec2 n) { 
                return fract(sin(dot(n, vec2(12.9898, 4.1414))) * 43758.5453);
            }

            float noise(vec2 p) {
                vec2 ip = floor(p);
                vec2 u = fract(p);
                u = u*u*(3.0-2.0*u);

                float res = mix(
                    mix(rand(ip), rand(ip+vec2(1.0,0.0)), u.x),
                    mix(rand(ip+vec2(0.0,1.0)), rand(ip+vec2(1.0,1.0)), u.x), u.y);
                return res*res;
            }

            void main() {
                vec2 uv = vUv;

                float nx = noise(uv * 8.0 + time * 0.2);
                float ny = noise(uv * 8.0 - time * 0.2);

                vec3 sandColor1 = vec3(0.76, 0.45, 0.2);  // Spice orange
                vec3 sandColor2 = vec3(0.55, 0.35, 0.15); // Dark sand

                vec3 color = mix(sandColor1, sandColor2, noise(uv * 4.0 + vec2(nx, ny)));

                float sparkle = pow(rand(uv + time * 0.1), 20.0) * 0.3;
                color += vec3(sparkle);

                gl_FragColor = vec4(color, 1.0);
            }
        </script>

        <!-- Add Three.js -->
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>

        <!-- Add sand effect container -->
        <div id="sand-background"></div>

        <script>
        // Initialize sand effect
        const container = document.getElementById('sand-background');
        const scene = new THREE.Scene();
        const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
        const renderer = new THREE.WebGLRenderer({ alpha: true });

        // Set canvas size
        function resize() {
            renderer.setSize(window.innerWidth, window.innerHeight);
        }
        window.addEventListener('resize', resize);
        resize();

        // Add to container
        container.appendChild(renderer.domElement);

        // Create shader material
        const uniforms = {
            time: { value: 0 },
            resolution: { value: new THREE.Vector2() }
        };

        const material = new THREE.ShaderMaterial({
            uniforms: uniforms,
            vertexShader: document.getElementById('vertex-shader').textContent,
            fragmentShader: document.getElementById('fragment-shader').textContent
        });

        // Create mesh
        const geometry = new THREE.PlaneGeometry(2, 2);
        const mesh = new THREE.Mesh(geometry, material);
        scene.add(mesh);

        // Animation loop
        function animate(time) {
            uniforms.time.value = time * 0.001;
            renderer.render(scene, camera);
            requestAnimationFrame(animate);
        }
        requestAnimationFrame(animate);
        </script>
    """,
        unsafe_allow_html=True)



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

        load_css()

        # Basic title and description
        st.markdown("""
            <div class="grid-container">
                <div class="grid-item full-width">
                    <h1>Thinking Machine Detector</h1>
                    <div class='intro-text'>
                    Like the calculations of a Mentat, this tool uses advanced cognitive processes 
                    to identify Abominable Intelligences among Reddit users. The spice must flow, but the machines must not prevail.
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)


        analysis_mode = st.radio("Analysis Mode:", ["Single Account", "Bulk Detection"])

        if analysis_mode == "Single Account":
            username = st.text_input("Enter Reddit Username:", "")
            if username:
                try:
                    with st.spinner('Analyzing account...'):
                        result = analyze_single_user(username, reddit_analyzer, text_analyzer, account_scorer)
                        if 'error' in result:
                            error_msg = result['error']
                            st.error(f"Error analyzing account: {error_msg}")
                            # Add an expander for detailed error information
                            with st.expander("See detailed error information"):
                                st.code(error_msg)
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

    except Exception as e:
        st.error(f"Application error: {str(e)}")

if __name__ == "__main__":
    main()