
import socket
import time
import json
import urllib.request

IP = "192.168.10.215"
PORT = 21324

def set_state(on=True, bri=128):
    payload = json.dumps({"on": on, "bri": bri, "live": True}).encode()
    req = urllib.request.Request(f"http://{IP}/json/state", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.read().decode()
    except Exception as e:
        return f"FEHLER: {e}"

def send_drgb(num_leds, r, g, b, timeout=1):
    header = bytes([0x02, timeout])
    payload = bytes([r, g, b] * num_leds)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(header + payload, (IP, PORT))
    sock.close()

print(f"--- Diagnostik für TOP (Face 4) @ {IP} ---")
print("1. Setze WLED State via HTTP (Helligkeit 50, On)...")
print(set_state(True, 50))
time.sleep(1)

print("\n2. Teste UDP-Belastung (DRGB)...")
for leds in [1, 10, 50, 100, 250, 480]:
    print(f"   Sende {leds} LEDs (Rot)...")
    send_drgb(leds, 100, 0, 0)
    time.sleep(1)
    # Check if still alive
    check = set_state(True, 50)
    if "FEHLER" in check:
        print(f"   !!! ABSTURZ bei {leds} LEDs !!!")
        break
    else:
        print(f"   {leds} LEDs OK.")

print("\n3. Montage-Muster einzeln senden (TOP)...")
# Hier simulieren wir die Datenmenge, aber nur für TOP
full_buf = bytes([0, 0, 0] * 480)
# (Wir füllen hier ein paar LEDs wie im Montage-Mode)
send_drgb(480, 255, 255, 255) # Teste ein Mal voll Weiß (kurz)
time.sleep(0.5)
print("Diagnose beendet.")
