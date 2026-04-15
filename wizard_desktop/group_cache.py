"""
group_cache.py – Local persistence of known group codes.

Stores a mapping of group-code → group-info so that users can opt in to
having codes auto-filled the next time they join a group.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

_CACHE_FILE = Path.home() / ".wizard_gui_groups.json"


def _load_all() -> Dict[str, Dict]:
    if not _CACHE_FILE.exists():
        return {}
    try:
        with open(_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save_all(data: Dict[str, Dict]) -> None:
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def remember_group(group: Dict) -> None:
    """Store a group's name+code locally so the code can be auto-filled later."""
    code = str(group.get("code", "")).strip()
    name = str(group.get("name", "")).strip()
    if not code:
        return
    data = _load_all()
    data[code] = {"name": name, "code": code}
    _save_all(data)


def forget_group(code: str) -> None:
    """Remove a cached group by code."""
    data = _load_all()
    if code in data:
        del data[code]
        _save_all(data)


def lookup_code_by_name(name: str) -> Optional[str]:
    """Return the cached 4-digit code for a group by its name (first match)."""
    if not name:
        return None
    data = _load_all()
    for code, info in data.items():
        if info.get("name") == name:
            return code
    return None


def lookup_group_by_code(code: str) -> Optional[Dict]:
    """Return the cached group info for a given code, or None."""
    return _load_all().get(code)


def known_groups() -> Dict[str, Dict]:
    """Return a copy of all known (code → group) mappings."""
    return dict(_load_all())
