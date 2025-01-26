import pytest
import logging
import sys
from datetime import datetime
from pathlib import Path

def main():
    """Run test suite with detailed logging"""
    # Create test_results directory if it doesn't exist
    test_results_dir = Path('test_results')
    test_results_dir.mkdir(exist_ok=True)

    # Configure logging with the new directory
    log_file = test_results_dir / f'test_run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
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

        # Cleanup old test files
        cleanup_old_logs(test_results_dir)
        cleanup_root_test_logs()

        return exit_code

    except Exception as e:
        logger.error(f"Error running test suite: {str(e)}")
        return 1

def cleanup_old_logs(test_results_dir: Path):
    """Keep only the 5 most recent test log files"""
    try:
        # Get all log files sorted by modification time (newest first)
        log_files = sorted(
            test_results_dir.glob('*.log'),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        # Remove all but the 5 most recent files
        for log_file in log_files[5:]:
            try:
                log_file.unlink()
            except Exception as e:
                logging.error(f"Error during log cleanup: {str(e)}")
    except Exception as e:
        logging.error(f"Error during log directory cleanup: {str(e)}")

def cleanup_root_test_logs():
    """Clean up any test log files in the root directory"""
    try:
        root_dir = Path('.')
        root_test_logs = list(root_dir.glob('test_run_*.log'))

        for log_file in root_test_logs:
            try:
                log_file.unlink()
            except Exception as e:
                logging.error(f"Error removing root test log {log_file}: {str(e)}")
    except Exception as e:
        logging.error(f"Error during root directory cleanup: {str(e)}")

if __name__ == "__main__":
    sys.exit(main())