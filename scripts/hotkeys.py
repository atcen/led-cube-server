#!/usr/bin/env python3
"""
WLED Cube – Globaler Hotkey-Daemon für Raspberry Pi.

Jeder Hotkey ist ein einzelner Tastendruck (keine Kombinationen).
Konfiguration über das Web UI: Einstellungen → Hotkeys.

Starten:
    python scripts/hotkeys.py [--server http://localhost:8000]

Als systemd-Service installieren:
    sudo cp scripts/wled-hotkeys.service /etc/systemd/system/
    sudo systemctl enable --now wled-hotkeys

Hinweis: Benötigt Zugriff auf /dev/input → User muss in Gruppe "input" sein:
    sudo usermod -aG input pi
"""
import argparse
import json
import logging
import pathlib
import random
import sys
import time
from typing import Optional, Callable

import httpx
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

log = logging.getLogger("wled-hotkeys")
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")

SETTINGS_PATH = pathlib.Path(__file__).parent.parent / "settings.json"

DEFAULTS: dict = {
    "enabled":       True,
    "stop":          "<f10>",
    "on":            "<f11>",
    "next":          "<f12>",
    "random":        "<f9>",
    "per_animation": {},
}

# Mapping von pynput-Key-Strings zu Key-Enum-Werten
_KEY_MAP: dict[str, Key] = {
    "<right>":     Key.right,
    "<left>":      Key.left,
    "<up>":        Key.up,
    "<down>":      Key.down,
    "<esc>":       Key.esc,
    "<enter>":     Key.enter,
    "<backspace>": Key.backspace,
    "<delete>":    Key.delete,
    "<space>":     Key.space,
    "<tab>":       Key.tab,
    "<page_up>":   Key.page_up,
    "<page_down>": Key.page_down,
    "<home>":      Key.home,
    "<end>":       Key.end,
}
for _i in range(1, 13):
    _KEY_MAP[f"<f{_i}>"] = getattr(Key, f"f{_i}")


def parse_key(key_str: str) -> Key | KeyCode | None:
    """Konvertiert einen Key-String in ein pynput Key/KeyCode-Objekt."""
    if not key_str:
        return None
    if key_str in _KEY_MAP:
        return _KEY_MAP[key_str]
    if len(key_str) == 1:
        return KeyCode.from_char(key_str)
    return None


def key_matches(pressed: Key | KeyCode, key_str: str) -> bool:
    """Prüft ob ein gedrückter Key dem konfigurierten Key-String entspricht."""
    target = parse_key(key_str)
    if target is None:
        return False
    if isinstance(target, Key):
        return pressed == target
    if isinstance(target, KeyCode) and isinstance(pressed, KeyCode):
        return pressed.char == target.char
    return False


def load_shortcuts() -> dict:
    try:
        data = json.loads(SETTINGS_PATH.read_text())
        ks   = data.get("hotkey_shortcuts", {})
        merged = dict(DEFAULTS)
        merged.update({k: v for k, v in ks.items() if v is not None})
        if "per_animation" in ks:
            merged["per_animation"] = {k: v for k, v in ks["per_animation"].items() if v}
        return merged
    except Exception as e:
        log.warning(f"settings.json nicht lesbar ({e}), nutze Defaults")
        return dict(DEFAULTS)


class HotkeyDaemon:
    def __init__(self, server_url: str) -> None:
        self.server          = server_url.rstrip("/")
        self.client          = httpx.Client(timeout=3.0)
        self._animations:    list[str]    = []
        self._last_animation: str | None  = None
        self._refresh_state()

    def _refresh_state(self) -> None:
        try:
            r    = self.client.get(f"{self.server}/animations")
            self._animations = list(r.json().keys())
            s    = self.client.get(f"{self.server}/status")
            data = s.json()
            anim = data.get("animation", "none")
            if anim and anim != "none":
                self._last_animation = anim
        except Exception as e:
            log.warning(f"Server nicht erreichbar: {e}")

    def _post(self, path: str) -> Optional[dict]:
        try:
            return self.client.post(f"{self.server}{path}").json()
        except Exception as e:
            log.warning(f"POST {path} fehlgeschlagen: {e}")
            return None

    def _enabled_animations(self) -> list[str]:
        try:
            data = json.loads(SETTINGS_PATH.read_text())
            enabled = data.get("enabled_animations")
            if enabled:
                return [a for a in self._animations if a in enabled]
        except Exception:
            pass
        return list(self._animations)

    def cmd_stop(self) -> None:
        log.info("■  Alles aus")
        self._post("/stop")

    def cmd_on(self) -> None:
        if not self._animations:
            self._refresh_state()
        target = self._last_animation
        if not target or target not in self._animations:
            available = self._enabled_animations()
            target = available[0] if available else None
        if target:
            log.info(f"▶  Alles an: {target}")
            self._post(f"/animation/{target}")

    def cmd_next(self) -> None:
        if not self._animations:
            self._refresh_state()
        available = self._enabled_animations()
        if not available:
            return
        idx = available.index(self._last_animation) if self._last_animation in available else -1
        nxt = available[(idx + 1) % len(available)]
        log.info(f"▶  Nächste: {nxt}")
        self._post(f"/animation/{nxt}")
        self._last_animation = nxt

    def cmd_random(self) -> None:
        if not self._animations:
            self._refresh_state()
        available = self._enabled_animations()
        if not available:
            return
        name = random.choice(available)
        log.info(f"?  Zufällig: {name}")
        self._post(f"/animation/{name}")
        self._last_animation = name

    def cmd_animation(self, name: str) -> None:
        log.info(f"▶  Animation: {name}")
        self._post(f"/animation/{name}")
        self._last_animation = name


def build_action_map(daemon: HotkeyDaemon, shortcuts: dict) -> list[tuple[str, Callable]]:
    """Gibt eine Liste von (key_str, action) zurück."""
    pairs: list[tuple[str, Callable]] = []

    for action_name, cmd in [
        ("stop",   daemon.cmd_stop),
        ("on",     daemon.cmd_on),
        ("next",   daemon.cmd_next),
        ("random", daemon.cmd_random),
    ]:
        key_str = shortcuts.get(action_name)
        if key_str and parse_key(key_str) is not None:
            pairs.append((key_str, cmd))

    for anim_name, key_str in shortcuts.get("per_animation", {}).items():
        if key_str and parse_key(key_str) is not None:
            pairs.append((key_str, lambda n=anim_name: daemon.cmd_animation(n)))

    return pairs


def run(server_url: str) -> None:
    shortcuts = load_shortcuts()
    if not shortcuts.get("enabled", True):
        log.info("Hotkeys deaktiviert (enabled=false in settings.json)")
        return

    log.info(f"Verbinde mit Server: {server_url}")
    daemon     = HotkeyDaemon(server_url)
    action_map = build_action_map(daemon, shortcuts)

    if not action_map:
        log.warning("Keine Hotkeys konfiguriert. Bitte im Web UI unter Einstellungen → Hotkeys einrichten.")

    log.info("Aktive Tastenkürzel:")
    for key_str, fn in action_map:
        log.info(f"  {key_str:20s} → {getattr(fn, '__name__', str(fn))}")

    def on_press(key: Key | KeyCode) -> None:
        for key_str, action in action_map:
            if key_matches(key, key_str):
                action()
                return  # nur erste Übereinstimmung auslösen

    listener = keyboard.Listener(on_press=on_press, suppress=False)
    listener.start()
    log.info("Daemon läuft. Strg+C zum Beenden.")

    try:
        while True:
            time.sleep(30)
            daemon._refresh_state()
            # Settings neu laden wenn geändert
            new_sc = load_shortcuts()
            if new_sc != shortcuts:
                log.info("Settings geändert — Hotkeys werden neu geladen…")
                listener.stop()
                run(server_url)
                return
    except KeyboardInterrupt:
        log.info("Beende.")
    finally:
        listener.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WLED Cube Hotkey-Daemon")
    parser.add_argument("--server", default="http://localhost:8000",
                        help="Server-URL (default: http://localhost:8000)")
    args = parser.parse_args()
    run(args.server)
