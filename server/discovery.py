"""
Controller-Discovery: Pingt alle 6 WLED-Controller via HTTP.
Aktualisiert mDNS-Auflösung dynamisch.
"""
import asyncio
import httpx
import socket
import logging
from .config import CONTROLLERS, FACE_NAMES, MDNS_HOSTS

log = logging.getLogger("wled-cube")


async def check_controller(client: httpx.AsyncClient, face: int, ip: str) -> dict:
    base = {"face": FACE_NAMES[face], "face_id": face, "ip": ip, "online": False,
            "name": "", "version": "", "leds": 0}
    try:
        r = await client.get(f"http://{ip}/json/info", timeout=1.5)
        if r.status_code == 200:
            info = r.json()
            base["online"]  = True
            base["name"]    = info.get("name", "")
            base["version"] = info.get("ver", "")
            base["leds"]    = info.get("leds", {}).get("count", 0)
    except httpx.ConnectTimeout:
        log.warning(f"Timeout beim Verbinden mit {base['face']} ({ip})")
    except httpx.ConnectError:
        log.warning(f"Verbindung abgelehnt von {base['face']} ({ip})")
    except Exception as e:
        log.error(f"Fehler bei Discovery von {base['face']}: {e}")
    return base


def resolve_mdns(hostname: str) -> str | None:
    try:
        return socket.getaddrinfo(hostname, None, socket.AF_INET)[0][4][0]
    except Exception:
        return None


async def check_all() -> list[dict]:
    async with httpx.AsyncClient() as client:
        # mDNS neu auflösen für alle Faces
        for face_id, (hostname, fallback) in MDNS_HOSTS.items():
            new_ip = resolve_mdns(hostname)
            if new_ip:
                if CONTROLLERS[face_id] != new_ip:
                    log.info(f"Controller {FACE_NAMES[face_id]} hat neue IP: {new_ip}")
                CONTROLLERS[face_id] = new_ip
        
        tasks = [check_controller(client, face, ip) for face, ip in CONTROLLERS.items()]
        return list(await asyncio.gather(*tasks))
