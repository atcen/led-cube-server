
import socket
import time
import json
import urllib.request

IP = "192.168.10.215"
PORT = 21324
FPS = 30

def set_state(on=True, bri=50):
    payload = json.dumps({"on": on, "bri": bri, "live": True}).encode()
    req = urllib.request.Request(f"http://{IP}/json/state", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.read().decode()
    except Exception as e:
        return f"FEHLER: {e}"

def send_drgb(num_leds, r, g, b):
    header = bytes([0x02, 1])
    payload = bytes([r, g, b] * num_leds)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(header + payload, (IP, PORT))
    sock.close()

print(f"--- Stress-Test für TOP @ {IP} ---")
set_state(True, 50)
time.sleep(1)

for duration in [2, 5, 10]:
    print(f"Sende 480 LEDs @ {FPS} FPS für {duration} Sekunden...")
    start = time.time()
    while time.time() - start < duration:
        send_drgb(480, 50, 50, 50) # Graues Rauschen
        time.sleep(1.0 / FPS)
    
    # Check health
    health = set_state(True, 50)
    if "FEHLER" in health:
        print("!!! Controller ABGESTÜRZT !!!")
        break
    else:
        print("Test bestanden.")
        time.sleep(1)

print("\nMontage-Muster-Sim (FRONT-TOP, BACK-TOP, LEFT-TOP, RIGHT-TOP)...")
# Wir simulieren genau die 12 LEDs des Montage-Modus
pattern = [0, 0, 0] * 480
# Ein paar LEDs setzen (row 0, row 4 etc) -> vereinfacht
for i in [1,2,3, 21,22,23, 100,101,102]: 
    pattern[i*3:i*3+3] = [255, 0, 0]

start = time.time()
while time.time() - start < 10:
    send_drgb(480, 0, 0, 0) # Placeholder logic for real pattern
    time.sleep(1.0 / FPS)

print("Simulation beendet.")
