"""
Controller-Discovery: Pingt alle 6 WLED-Controller via HTTP.
"""
import asyncio
import httpx
from .config import CONTROLLERS, FACE_NAMES


async def check_controller(client: httpx.AsyncClient, face: int, ip: str) -> dict:
    base = {"face": FACE_NAMES[face], "face_id": face, "ip": ip, "online": False,
            "name": "", "version": "", "leds": 0}
    try:
        r = await client.get(f"http://{ip}/json/info", timeout=2.0)
        if r.status_code == 200:
            info = r.json()
            base["online"]  = True
            base["name"]    = info.get("name", "")
            base["version"] = info.get("ver", "")
            base["leds"]    = info.get("leds", {}).get("count", 0)
    except Exception:
        pass
    return base


async def check_all() -> list[dict]:
    async with httpx.AsyncClient() as client:
        tasks = [check_controller(client, face, ip) for face, ip in CONTROLLERS.items()]
        return list(await asyncio.gather(*tasks))
