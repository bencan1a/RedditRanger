import os
import subprocess
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def compile_translations():
    """Compile all .po translation files to .mo files"""
    translations_dir = Path(__file__).parent / "translations"

    # First ensure gettext is installed
    try:
        subprocess.run(['msgfmt', '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.info("Installing gettext...")
        subprocess.run(['apt-get', 'update'], check=True)
        subprocess.run(['apt-get', 'install', '-y', 'gettext'], check=True)

    success_count = 0
    error_count = 0

    # Compile each translation file
    for lang_dir in translations_dir.glob("*/LC_MESSAGES"):
        po_file = lang_dir / "messages.po"
        mo_file = lang_dir / "messages.mo"

        if po_file.exists():
            try:
                logger.info(f"Compiling translations for {lang_dir.parent.name}")
                subprocess.run(['msgfmt', str(po_file), '-o', str(mo_file)], 
                            check=True, capture_output=True)
                success_count += 1
            except subprocess.CalledProcessError as e:
                logger.error(f"Error compiling translations for {lang_dir.parent.name}: {e}")
                error_count += 1

    logger.info(f"Translation compilation complete. Success: {success_count}, Errors: {error_count}")
    return success_count, error_count

if __name__ == "__main__":
    compile_translations()