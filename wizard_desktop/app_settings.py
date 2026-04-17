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
_LEADERBOARD_URL = "http://158.180.32.188:8000"

# Event-message defaults -----------------------------------------------------
_DEFAULT_MESSAGE_DURATION_MS = 2200
_MIN_MESSAGE_DURATION_MS = 500
_MAX_MESSAGE_DURATION_MS = 10000

# Keys used by CelebrationOverlay / event dispatcher.  Each key maps to a
# translation entry in translations.py (same key name); users can override
# the displayed text from the Settings dialog.
EVENT_KEYS = (
    "huge_loss",
    "bow_stretched",
    "revenge_lever",
    "tobi_message",
    "fire",
    "new_leader",
    "big_scorer",
)

_settings: dict = {
    "language": _DEFAULT_LANGUAGE,
    "theme": _DEFAULT_THEME,
    "message_display_duration_ms": _DEFAULT_MESSAGE_DURATION_MS,
    # user-supplied overrides for event strings.  Empty string / missing key
    # means "use the translated default".
    "custom_event_messages": {k: "" for k in EVENT_KEYS},
    "custom_rules": [],
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
    # Always ensure all known event keys exist (for forward-compat when new
    # events get added in later versions).
    cem = _settings.setdefault("custom_event_messages", {})
    if not isinstance(cem, dict):
        cem = {}
        _settings["custom_event_messages"] = cem
    for k in EVENT_KEYS:
        cem.setdefault(k, "")


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


def get_leaderboard_url() -> str:
    """Gibt die fest eingestellte Leaderboard-Server-URL zurück."""
    return _LEADERBOARD_URL


# ── Message display duration ────────────────────────────────────────────────

def get_message_display_duration_ms() -> int:
    """Return the current event-overlay display duration in milliseconds."""
    try:
        v = int(_settings.get("message_display_duration_ms", _DEFAULT_MESSAGE_DURATION_MS))
    except (TypeError, ValueError):
        v = _DEFAULT_MESSAGE_DURATION_MS
    return max(_MIN_MESSAGE_DURATION_MS, min(_MAX_MESSAGE_DURATION_MS, v))


def set_message_display_duration_ms(ms: int) -> None:
    _settings["message_display_duration_ms"] = max(
        _MIN_MESSAGE_DURATION_MS, min(_MAX_MESSAGE_DURATION_MS, int(ms))
    )
    save_settings()


# ── Custom event messages ───────────────────────────────────────────────────

def get_custom_event_messages() -> dict:
    """Return a copy of the custom-event-message overrides (key → string)."""
    cem = _settings.get("custom_event_messages") or {}
    if not isinstance(cem, dict):
        return {k: "" for k in EVENT_KEYS}
    return {k: str(cem.get(k, "") or "") for k in EVENT_KEYS}


def set_custom_event_message(key: str, value: str) -> None:
    """Override the message for a given event key. Empty string clears."""
    if key not in EVENT_KEYS:
        return
    cem = _settings.setdefault("custom_event_messages", {})
    if not isinstance(cem, dict):
        cem = {}
        _settings["custom_event_messages"] = cem
    cem[key] = str(value or "")
    save_settings()


def set_custom_event_messages(mapping: dict) -> None:
    """Bulk-update all custom-event-message overrides."""
    cem = _settings.setdefault("custom_event_messages", {})
    if not isinstance(cem, dict):
        cem = {}
        _settings["custom_event_messages"] = cem
    for k in EVENT_KEYS:
        if k in mapping:
            cem[k] = str(mapping.get(k) or "")
    save_settings()


def get_custom_rules() -> list:
    return _settings.get("custom_rules", [])


def add_custom_rule(rule: dict) -> None:
    rules = _settings.setdefault("custom_rules", [])
    if not isinstance(rules, list):
        rules = []
        _settings["custom_rules"] = rules
    rules.append(rule)
    save_settings()


def remove_custom_rule(index: int) -> None:
    rules = _settings.get("custom_rules", [])
    if isinstance(rules, list) and 0 <= index < len(rules):
        rules.pop(index)
        save_settings()


def resolve_event_message(key: str, **kwargs) -> str:
    """Return the user override (formatted with kwargs) if set, otherwise the
    translated default for ``key``.
    """
    if key not in EVENT_KEYS:
        return t(key, **kwargs)
    override = get_custom_event_messages().get(key, "")
    if override:
        try:
            return override.format(**kwargs)
        except (KeyError, IndexError):
            return override
    return t(key, **kwargs)


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
