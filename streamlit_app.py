import logging
import time
import streamlit as st
import sys

# Configure startup logging with more detail
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more verbose output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Simple app for testing connectivity
def main():
    """Minimal startup for testing"""
    try:
        logger.info("🚀 Starting minimal test application")
        logger.debug(f"Python version: {sys.version}")
        logger.debug(f"Streamlit version: {st.__version__}")

        st.title("Connection Test")
        st.write("If you can see this message, the Streamlit app is working!")

        # Add a simple interaction to test WebSocket
        if st.button("Click me"):
            st.write("Button clicked!")

    except Exception as e:
        logger.error(f"❌ Application error: {str(e)}", exc_info=True)
        st.error(f"Application error: {str(e)}")

if __name__ == "__main__":
    logger.debug("🔍 Script starting...")
    main()