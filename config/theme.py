"""Theme configuration for the Reddit Mentat Detector application."""
from dataclasses import dataclass
from typing import Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

@dataclass
class ThemeConfig:
    # Colors
    primary_color: str = "#FFB74D"
    primary_dark: str = "#FF9800"
    background_dark: str = "rgba(35, 20, 12, 0.85)"
    background_light: str = "rgba(44, 26, 15, 0.9)"
    border_color: str = "rgba(255, 152, 0, 0.1)"

    # Gradients
    gradient_primary: str = "linear-gradient(145deg, rgba(44, 26, 15, 0.8), rgba(35, 20, 12, 0.95))"
    gradient_header: str = "linear-gradient(180deg, rgba(44, 26, 15, 0.95), rgba(35, 20, 12, 0.98))"

    # Typography
    font_family_primary: str = "'Space Mono', monospace"
    font_size_base: str = "1rem"
    font_size_large: str = "1.5rem"
    font_size_xlarge: str = "1.8rem"

    # Spacing
    spacing_small: str = "0.5rem"
    spacing_medium: str = "1rem"
    spacing_large: str = "1.5rem"
    spacing_xlarge: str = "2rem"

    # Effects
    shadow_small: str = "0 4px 12px rgba(255, 152, 0, 0.05)"
    shadow_large: str = "0 4px 20px rgba(0, 0, 0, 0.3)"
    glow_text: str = "0 0 10px rgba(255, 152, 0, 0.2)"

    # Animations
    transition_speed: str = "0.3s"
    transition_function: str = "ease-out"

    def to_css_variables(self) -> str:
        """Convert theme configuration to CSS variables."""
        variables = []
        for key, value in self.__dict__.items():
            css_key = key.replace('_', '-')
            variables.append(f'    --{css_key}: {value};')
        return '\n'.join([':root {'] + variables + ['}'])

def get_asset_path(filename: str) -> str:
    """Get absolute path for static assets."""
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(current_dir, 'static', filename)
    if not os.path.exists(path):
        logger.error(f"Asset file not found: {path}")
        raise FileNotFoundError(f"Asset file not found: {path}")
    return path

def load_theme_files() -> Dict[str, Any]:
    """Load all theme-related files and return their contents."""
    logger.info("Starting to load theme files...")
    theme = ThemeConfig()
    css_files = {
        'theme': 'theme.css',
        'style': 'style.css',
    }
    js_files = {
        'animate': 'animate.js',
        'sand_effect': 'sand_effect.js'
    }

    result = {
        'css_variables': theme.to_css_variables(),
        'css_files': {},
        'js_files': {}
    }

    # Load CSS files
    for key, filename in css_files.items():
        try:
            logger.debug(f"Loading CSS file: {filename}")
            with open(get_asset_path(filename), 'r', encoding='utf-8') as f:
                result['css_files'][key] = f.read()
            logger.info(f"Successfully loaded CSS file: {filename}")
        except Exception as e:
            logger.error(f"Error loading {filename}: {str(e)}")
            result['css_files'][key] = f"/* Error loading {filename}: {str(e)} */"

    # Load JS files
    for key, filename in js_files.items():
        try:
            logger.debug(f"Loading JS file: {filename}")
            if filename == 'sand_effect.js' and not os.path.exists(get_asset_path(filename)):
                logger.warning(f"Optional file {filename} not found, skipping...")
                continue
            with open(get_asset_path(filename), 'r', encoding='utf-8') as f:
                result['js_files'][key] = f.read()
            logger.info(f"Successfully loaded JS file: {filename}")
        except Exception as e:
            logger.error(f"Error loading {filename}: {str(e)}")
            result['js_files'][key] = f"console.error('Error loading {filename}:', {str(e)});"

    logger.info("Theme files loading completed")
    return result