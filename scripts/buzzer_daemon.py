import time
import requests
import threading
import RPi.GPIO as GPIO
from rpi_ws281x import PixelStrip, Color

# Konfiguration
LED_COUNT      = 37        # 1 + 8 + 12 + 16
LED_PIN        = 10        # GPIO 10 (SPI MOSI, Pin 19)
LED_FREQ_HZ    = 3200000   # SPI-Frequenz für WS2812B (3.2MHz)
LED_DMA        = 10
LED_BRIGHTNESS = 150       # 0-255
LED_INVERT     = False
BUTTON_PIN     = 24        # GPIO 24 (Pin 18)

# API-Endpunkt
SERVER_URL = "http://localhost:8000"

print("Initialisiere LED-Strip...")
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)
try:
    strip.begin()
except Exception as e:
    print(f"Fehler beim LED-Start: {e}")

def next_animation():
    try:
        r = requests.post(f"{SERVER_URL}/animation/next", timeout=2.0)
        print(f"API Trigger OK: {r.status_code}")
    except Exception as e:
        print(f"API Trigger FEHLER: {e}")

def pulse_leds():
    """Sanftes Pulsieren der LED-Ringe."""
    print("LED-Puls-Thread aktiv.")
    while True:
        try:
            # Blaues Ein- und Ausfaden
            for i in range(20, 150, 3):
                for j in range(strip.numPixels()):
                    strip.setPixelColor(j, Color(0, 0, i))
                strip.show()
                time.sleep(0.02)
            for i in range(150, 20, -3):
                for j in range(strip.numPixels()):
                    strip.setPixelColor(j, Color(0, 0, i))
                strip.show()
                time.sleep(0.02)
        except Exception as e:
            print(f"LED-Thread Fehler: {e}")
            time.sleep(1)

def main():
    # GPIO Setup (Polling Modus)
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    print(f"Buzzer-Daemon (Polling) läuft auf Pin {BUTTON_PIN}")
    
    # Pulsing im Hintergrund
    t = threading.Thread(target=pulse_leds, daemon=True)
    t.start()

    last_state = True
    try:
        while True:
            state = GPIO.input(BUTTON_PIN)
            
            # Flankenerkennung (High -> Low = Drücken)
            if state == False and last_state == True:
                print(">>> BUZZER GEDRÜCKT <<<")
                # Weißer Flash-Effekt
                for j in range(strip.numPixels()):
                    strip.setPixelColor(j, Color(255, 255, 255))
                strip.show()
                
                # API Call
                next_animation()
                
                time.sleep(0.5) # Entprellen / Anzeigezeit Flash
            
            last_state = state
            time.sleep(0.02) # Kurze Pause für CPU
            
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()
        print("Buzzer-Daemon beendet.")

if __name__ == "__main__":
    main()
