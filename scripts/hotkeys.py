#!/usr/bin/env python3
"""
WLED Cube – Globaler Hotkey-Daemon für Raspberry Pi.

Liest Tastatureingaben direkt via evdev (/dev/input) — funktioniert
auf X11, Wayland und headless gleichermaßen.

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
import select
import sys
import time
from typing import Optional, Callable

import httpx
from evdev import InputDevice, ecodes, list_devices

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

# Mapping von pynput-kompatiblen Key-Strings zu evdev-Keycodes
_KEY_MAP: dict[str, int] = {
    "<right>":     ecodes.KEY_RIGHT,
    "<left>":      ecodes.KEY_LEFT,
    "<up>":        ecodes.KEY_UP,
    "<down>":      ecodes.KEY_DOWN,
    "<esc>":       ecodes.KEY_ESC,
    "<enter>":     ecodes.KEY_ENTER,
    "<backspace>": ecodes.KEY_BACKSPACE,
    "<delete>":    ecodes.KEY_DELETE,
    "<space>":     ecodes.KEY_SPACE,
    "<tab>":       ecodes.KEY_TAB,
    "<page_up>":   ecodes.KEY_PAGEUP,
    "<page_down>": ecodes.KEY_PAGEDOWN,
    "<home>":      ecodes.KEY_HOME,
    "<end>":       ecodes.KEY_END,
}
for _i in range(1, 13):
    _KEY_MAP[f"<f{_i}>"] = getattr(ecodes, f"KEY_F{_i}")

# Einzelne Zeichen a–z, 0–9
for _c in "abcdefghijklmnopqrstuvwxyz":
    _KEY_MAP[_c] = getattr(ecodes, f"KEY_{_c.upper()}")
for _d in "0123456789":
    _KEY_MAP[_d] = getattr(ecodes, f"KEY_{_d}", None) or getattr(ecodes, f"KEY_KP{_d}", None)


def parse_key(key_str: str) -> Optional[int]:
    return _KEY_MAP.get(key_str)


def find_keyboards() -> list[InputDevice]:
    devices = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
            caps = dev.capabilities()
            # Gerät muss EV_KEY haben und mindestens KEY_A kennen
            if ecodes.EV_KEY in caps and ecodes.KEY_A in caps[ecodes.EV_KEY]:
                devices.append(dev)
                log.info(f"Tastatur gefunden: {dev.path} ({dev.name})")
        except Exception:
            pass
    return devices


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
        self.server           = server_url.rstrip("/")
        self.client           = httpx.Client(timeout=3.0)
        self._animations:     list[str]   = []
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


def build_action_map(daemon: HotkeyDaemon, shortcuts: dict) -> list[tuple[int, Callable]]:
    pairs: list[tuple[int, Callable]] = []
    for action_name, cmd in [
        ("stop",   daemon.cmd_stop),
        ("on",     daemon.cmd_on),
        ("next",   daemon.cmd_next),
        ("random", daemon.cmd_random),
    ]:
        key_str = shortcuts.get(action_name)
        code = parse_key(key_str) if key_str else None
        if code is not None:
            pairs.append((code, cmd))

    for anim_name, key_str in shortcuts.get("per_animation", {}).items():
        code = parse_key(key_str) if key_str else None
        if code is not None:
            pairs.append((code, lambda n=anim_name: daemon.cmd_animation(n)))

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
    key_name_map = {v: k for k, v in _KEY_MAP.items()}
    for code, fn in action_map:
        log.info(f"  {key_name_map.get(code, str(code)):20s} → {getattr(fn, '__name__', str(fn))}")

    keyboards = find_keyboards()
    if not keyboards:
        log.error("Keine Tastatur gefunden unter /dev/input. User in Gruppe 'input'?")
        sys.exit(1)

    code_to_action = {code: fn for code, fn in action_map}
    fd_to_dev = {dev.fd: dev for dev in keyboards}

    log.info("Daemon läuft. Strg+C zum Beenden.")

    last_refresh = time.monotonic()
    last_settings_check = time.monotonic()

    while True:
        try:
            readable, _, _ = select.select(fd_to_dev, [], [], 5.0)
        except (OSError, ValueError):
            # Gerät getrennt — neu scannen
            log.warning("Eingabegerät getrennt, scanne neu…")
            for dev in fd_to_dev.values():
                try:
                    dev.close()
                except Exception:
                    pass
            time.sleep(2)
            keyboards = find_keyboards()
            fd_to_dev = {dev.fd: dev for dev in keyboards}
            continue

        for fd in readable:
            dev = fd_to_dev[fd]
            try:
                for event in dev.read():
                    if event.type == ecodes.EV_KEY and event.value == 1:  # key down
                        action = code_to_action.get(event.code)
                        if action:
                            action()
            except OSError:
                pass

        now = time.monotonic()

        # Server-State alle 30s auffrischen
        if now - last_refresh > 30:
            daemon._refresh_state()
            last_refresh = now

        # Settings alle 5s auf Änderungen prüfen
        if now - last_settings_check > 5:
            last_settings_check = now
            new_sc = load_shortcuts()
            if new_sc != shortcuts:
                log.info("Settings geändert — Hotkeys werden neu geladen…")
                for dev in fd_to_dev.values():
                    try:
                        dev.close()
                    except Exception:
                        pass
                run(server_url)
                return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WLED Cube Hotkey-Daemon")
    parser.add_argument("--server", default="http://localhost:8000",
                        help="Server-URL (default: http://localhost:8000)")
    args = parser.parse_args()
    run(args.server)
