import pytest
import logging
import sys
from datetime import datetime

def main():
    """Run test suite with detailed logging"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'test_run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting test suite execution")

    try:
        # Run pytest with verbose output and logging
        exit_code = pytest.main([
            "-v",  # verbose
            "--log-cli-level=INFO",  # Show logs in console
            "--tb=short",  # Shorter traceback format
            "tests/"  # Test directory
        ])
        
        if exit_code == 0:
            logger.info("All tests passed successfully!")
        else:
            logger.error(f"Test suite failed with exit code: {exit_code}")
        
        return exit_code
        
    except Exception as e:
        logger.error(f"Error running test suite: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
