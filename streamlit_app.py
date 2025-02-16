import logging
import time
import streamlit as st

# Configure startup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def log_timing(start_time, operation):
    """Log time taken for operations"""
    duration = time.time() - start_time
    logger.info(f"⏱️ {operation} took {duration:.2f} seconds")
    return time.time()

def main():
    """Minimal startup with timing instrumentation"""
    try:
        overall_start = time.time()
        logger.info("🚀 Starting minimal application")

        # Basic streamlit config
        start_time = time.time()
        st.set_page_config(
            page_title="Thinking Machine Detector",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        start_time = log_timing(start_time, "Basic Streamlit configuration")

        # Just show the input field
        logger.info("Rendering minimal UI")
        st.title("Thinking Machine Detector")
        username = st.text_input("Enter Reddit Username:", "")

        # Log total startup time
        total_time = time.time() - overall_start
        logger.info(f"🏁 Total initialization time: {total_time:.2f} seconds")

    except Exception as e:
        logger.error(f"❌ Application error: {str(e)}", exc_info=True)
        st.error(f"Application error: {str(e)}")

if __name__ == "__main__":
    main()