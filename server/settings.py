"""
Persistente Einstellungen via settings.json im Projektroot.
"""
import json
import pathlib
from .animations import REGISTRY

_PATH = pathlib.Path("settings.json")

DEFAULTS: dict = {
    "setup_complete": False,
    "brightness": 128,
    "enabled_animations": list(REGISTRY.keys()),
    "playlist": [],
    "playlist_mode": "manual",
    "animation_params": {},
    "keyboard_shortcuts": {
        "enabled": True,
        "next": "ArrowRight",
        "stop": "Escape",
        "random": "r",
        "per_animation": {},
    },
}


def load() -> dict:
    """Lädt settings.json und merged mit DEFAULTS."""
    if _PATH.exists():
        try:
            saved = json.loads(_PATH.read_text())
            merged = dict(DEFAULTS)
            merged.update(saved)
            return merged
        except Exception:
            pass
    return dict(DEFAULTS)


def save(data: dict) -> None:
    _PATH.write_text(json.dumps(data, indent=2))


def get(key: str, default=None):
    return load().get(key, default)


def update(partial: dict) -> dict:
    """Merged partial in gespeicherte Einstellungen, speichert und gibt das Ergebnis zurück."""
    current = load()
    current.update(partial)
    save(current)
    return current
