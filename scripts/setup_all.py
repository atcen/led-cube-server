#!/usr/bin/env python3
"""
Einmalig ausführen: Lädt LED-Map und Segmente auf alle 6 Panel-Controller.
"""
import json
import urllib.request
import threading
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from server.config import SEGMENTS, LED_MAP as _led_map, CONTROLLERS
def build_led_map(): return _led_map

# CONTROLLERS kommt jetzt direkt aus server.config (dynamisch aufgelöst)
# CONTROLLERS ist ein Dict {face_id: ip}
targets = list(CONTROLLERS.values())

led_map  = build_led_map()
led_map_json = json.dumps({"map": led_map}).encode()


def setup(host):
    try:
        # LED-Map hochladen
        boundary = "----WLEDBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="data"; filename="/ledmap.json"\r\n'
            f"Content-Type: application/json\r\n\r\n"
        ).encode() + led_map_json + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            f"http://{host}/edit",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            upload_status = resp.status

        # Segmente setzen
        payload = {
            "ledmap": 0,
            "seg": [{"id": s["id"], "start": s["start"], "stop": s["stop"], "on": True}
                    for s in SEGMENTS]
        }
        req = urllib.request.Request(
            f"http://{host}/json/state",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            seg_result = resp.read().decode()

        print(f"{host}: Upload {upload_status}, Segmente {seg_result}")

    except Exception as e:
        print(f"{host}: FEHLER — {e}")


threads = [threading.Thread(target=setup, args=(h,)) for h in targets]
for t in threads:
    t.start()
for t in threads:
    t.join()

print("Fertig.")
