import time
import threading
import requests
import RPi.GPIO as GPIO
from rpi_ws281x import PixelStrip, Color

# Konfiguration
BUTTON_PIN      = 24
LED_PIN         = 18
LED_COUNT       = 37        # 1 + 8 + 12 + 16
LED_FREQ        = 800_000
LED_DMA         = 10
LED_INVERT      = False
LED_CHANNEL     = 0
BRIGHTNESS      = 40        # 0–255
CHARGE_DURATION = 10.0      # Sekunden für Ladebalken

# Ring-Grenzen (Index im Strip, innen→außen)
RING_CENTER = [0]
RING_8      = list(range(1, 9))
RING_12     = list(range(9, 21))
RING_16     = list(range(21, 37))
ALL_RINGS   = [RING_CENTER, RING_8, RING_12, RING_16]

SERVER_URL = "http://localhost:8000"

_state      = "rainbow"
_state_lock = threading.Lock()
_state_time = 0.0


def hue_to_color(h: float, brightness: float = 1.0) -> Color:
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    q = 1.0 - f
    r, g, b = [(1,f,0),(q,1,0),(0,1,f),(0,q,1),(f,0,1),(1,0,q)][i % 6]
    s = brightness * 255
    return Color(int(r * s), int(g * s), int(b * s))


def set_all(strip, color: Color):
    for i in range(LED_COUNT):
        strip.setPixelColor(i, color)


def led_loop(strip):
    global _state, _state_time

    hue_offset   = 0.0
    ring_offsets = [0.0, 0.15, 0.30, 0.45]

    while True:
        with _state_lock:
            state = _state
            since = time.time() - _state_time

        # ── FLASH ──────────────────────────────────────────────
        if state == "flash":
            set_all(strip, Color(255, 255, 255))
            strip.show()
            time.sleep(0.15)
            with _state_lock:
                _state = "charging"
                _state_time = time.time()

        # ── LADEBALKEN ─────────────────────────────────────────
        elif state == "charging":
            progress  = min(since / CHARGE_DURATION, 1.0)
            lit_count = int(progress * LED_COUNT)

            for i in range(LED_COUNT):
                if i < lit_count:
                    # leuchtend cyan
                    strip.setPixelColor(i, Color(0, 180, 255))
                else:
                    # sehr dunkel (Rest sichtbar aber ungeladen)
                    strip.setPixelColor(i, Color(0, 8, 20))
            strip.show()

            if progress >= 1.0:
                with _state_lock:
                    _state = "rainbow"
                    _state_time = time.time()
            time.sleep(0.033)

        # ── REGENBOGEN ─────────────────────────────────────────
        else:
            hue_offset = (hue_offset + 0.003) % 1.0
            for ring, offset in zip(ALL_RINGS, ring_offsets):
                color = hue_to_color(hue_offset + offset)
                for i in ring:
                    strip.setPixelColor(i, color)
            strip.show()
            time.sleep(0.033)


def trigger_flash():
    global _state, _state_time
    with _state_lock:
        _state = "flash"
        _state_time = time.time()


def get_state():
    with _state_lock:
        return _state


def next_animation():
    try:
        r = requests.post(f"{SERVER_URL}/animation/next", timeout=2.0)
        print(f"API Trigger OK: {r.status_code}")
    except Exception as e:
        print(f"API Trigger FEHLER: {e}")


def main():
    global _state_time
    _state_time = time.time()

    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ, LED_DMA,
                       LED_INVERT, BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    t = threading.Thread(target=led_loop, args=(strip,), daemon=True)
    t.start()

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    print(f"Buzzer-Daemon läuft — Button: GPIO {BUTTON_PIN}, LEDs: GPIO {LED_PIN}")

    last_state = True
    try:
        while True:
            btn = GPIO.input(BUTTON_PIN)

            if btn == False and last_state == True:
                if get_state() == "rainbow":
                    print(">>> BUZZER GEDRÜCKT <<<")
                    trigger_flash()
                    next_animation()
                else:
                    print(">>> ignoriert (lädt noch) <<<")

            last_state = btn
            time.sleep(0.02)

    except KeyboardInterrupt:
        pass
    finally:
        set_all(strip, Color(0, 0, 0))
        strip.show()
        GPIO.cleanup()
        print("Buzzer-Daemon beendet.")


if __name__ == "__main__":
    main()
