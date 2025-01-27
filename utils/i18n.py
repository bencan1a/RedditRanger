import gettext
import os
from typing import Optional
from functools import lru_cache
import streamlit as st
from pathlib import Path

TRANSLATIONS_DIR = Path(__file__).parent.parent / "translations"
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch',
    'ja': '日本語',
    'zh': '中文',
}

class I18n:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(I18n, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._translations = {}
            self._ensure_session_state()
            self._load_translations()
            self._initialized = True

    def _ensure_session_state(self):
        """Ensure session state is properly initialized"""
        if not hasattr(st, 'session_state'):
            return

        if 'language' not in st.session_state:
            st.session_state['language'] = 'en'

    def _load_translations(self):
        """Load all available translations"""
        if not TRANSLATIONS_DIR.exists():
            TRANSLATIONS_DIR.mkdir(parents=True)

        for lang_code in SUPPORTED_LANGUAGES:
            try:
                translator = gettext.translation(
                    'messages',
                    localedir=str(TRANSLATIONS_DIR),
                    languages=[lang_code],
                    fallback=True
                )
                self._translations[lang_code] = translator.gettext
            except Exception as e:
                print(f"Failed to load translation for {lang_code}: {e}")
                self._translations[lang_code] = lambda x: x

    def get_language(self) -> str:
        """Get the current language from session state"""
        self._ensure_session_state()
        return st.session_state.get('language', 'en')

    def set_language(self, lang_code: str) -> None:
        """Set the current language if it's supported"""
        if lang_code in SUPPORTED_LANGUAGES:
            self._ensure_session_state()
            st.session_state['language'] = lang_code

    def translate(self, text: str) -> str:
        """Translate text using current language"""
        current_lang = self.get_language()
        translator = self._translations.get(current_lang, lambda x: x)
        return translator(text)

# Create global instance
i18n = I18n()

# Shorthand function for translation
def _(text: str) -> str:
    """Translate text using current language"""
    return i18n.translate(text)