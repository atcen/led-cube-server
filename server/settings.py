"""
Persistente Einstellungen via settings.json im Projektroot.
"""
import json
import pathlib
from .animations import REGISTRY

_PATH = pathlib.Path("settings.json")
_CACHE = None
_LAST_MTIME = 0

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
    # Globale Tastenkürzel für den Hotkey-Daemon (scripts/hotkeys.py).
    # Konfigurierbar über das Web UI (Einstellungen → Hotkeys).
    # Format: pynput GlobalHotKeys-Syntax, z.B. "<ctrl>+<alt>+<right>"
    # Globale Hotkeys für den Daemon (scripts/hotkeys.py).
    # Einzelne Tasten — keine Kombinationen. Im Web UI konfigurierbar.
    # Format: pynput-Key-String, z.B. "<f9>", "<right>", "1"
    "hotkey_shortcuts": {
        "enabled":       True,
        "stop":          "<f10>",   # Alles aus
        "on":            "<f11>",   # Alles an (letzte Animation)
        "next":          "<f12>",   # Nächste Animation
        "random":        "<f9>",    # Zufällige Animation
        "per_animation": {},        # z.B. {"snake": "1", "rainbow": "2"}
    },
    "face_orientations": [
        {"rotate": 0, "flip": False}, # 0: FRONT
        {"rotate": 0, "flip": False}, # 1: BACK
        {"rotate": 0, "flip": False}, # 2: LEFT
        {"rotate": 0, "flip": False}, # 3: RIGHT
        {"rotate": 0, "flip": False}, # 4: TOP
        {"rotate": 0, "flip": False}, # 5: BOTTOM
    ],
}


def load() -> dict:
    """Lädt settings.json und merged mit DEFAULTS. Nutzt In-Memory Cache."""
    global _CACHE, _LAST_MTIME
    
    if _PATH.exists():
        try:
            mtime = _PATH.stat().st_mtime
            if _CACHE is not None and mtime == _LAST_MTIME:
                return _CACHE
                
            saved = json.loads(_PATH.read_text())
            merged = dict(DEFAULTS)
            merged.update(saved)
            
            _CACHE = merged
            _LAST_MTIME = mtime
            return merged
        except Exception:
            pass
    
    if _CACHE is None:
        _CACHE = dict(DEFAULTS)
    return _CACHE


def save(data: dict) -> None:
    global _CACHE, _LAST_MTIME
    _PATH.write_text(json.dumps(data, indent=2))
    _CACHE = data
    try:
        _LAST_MTIME = _PATH.stat().st_mtime
    except Exception:
        pass


def get(key: str, default=None):
    return load().get(key, default)


def update(partial: dict) -> dict:
    """Merged partial in gespeicherte Einstellungen, speichert und gibt das Ergebnis zurück."""
    current = load()
    current.update(partial)
    save(current)
    return current
