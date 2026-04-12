"""
app_settings.py – Zentrale Einstellungsverwaltung für Wizard GUI.

Verwaltet:
  • Sprachauswahl (de/en/fr/hi)
  • Theme (dark/light)
  • Persistenz in ~/.wizard_gui_settings.json
"""
from __future__ import annotations

import json
from pathlib import Path

_SETTINGS_FILE = Path.home() / ".wizard_gui_settings.json"
_DEFAULT_LANGUAGE = "de"
_DEFAULT_THEME = "dark"

_settings: dict = {
    "language": _DEFAULT_LANGUAGE,
    "theme": _DEFAULT_THEME,
}


def load_settings() -> None:
    """Lädt Einstellungen aus der JSON-Datei (sofern vorhanden)."""
    global _settings
    if _SETTINGS_FILE.exists():
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                _settings.update(loaded)
        except Exception:
            pass  # Fallback auf Standardwerte


def save_settings() -> None:
    """Speichert aktuelle Einstellungen in der JSON-Datei."""
    try:
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(_settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_language() -> str:
    """Gibt das aktuelle Sprachkürzel zurück (z.B. 'de', 'en')."""
    return _settings.get("language", _DEFAULT_LANGUAGE)


def get_theme() -> str:
    """Gibt das aktuelle Theme zurück ('dark' oder 'light')."""
    return _settings.get("theme", _DEFAULT_THEME)


def set_language(lang: str) -> None:
    """Setzt die Sprache und speichert die Einstellung."""
    _settings["language"] = lang
    save_settings()


def set_theme(theme: str) -> None:
    """Setzt das Theme und speichert die Einstellung."""
    _settings["theme"] = theme
    save_settings()


def t(key: str, **kwargs) -> str:
    """
    Gibt den übersetzten String für den aktuellen Sprachschlüssel zurück.

    Beispiel: t("round_header", n=3)  →  "Runde 3" / "Round 3"
    """
    from translations import TRANSLATIONS
    lang = get_language()
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS.get(_DEFAULT_LANGUAGE, {}))
    text = lang_dict.get(key, TRANSLATIONS.get(_DEFAULT_LANGUAGE, {}).get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text
