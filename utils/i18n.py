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
    def __init__(self):
        self._translations = {}
        if 'language' not in st.session_state:
            st.session_state.language = 'en'
        self._load_translations()

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
        return st.session_state.language

    def set_language(self, lang_code: str) -> None:
        if lang_code in SUPPORTED_LANGUAGES:
            st.session_state.language = lang_code

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