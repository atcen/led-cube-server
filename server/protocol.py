"""
UDP DRGB-Protokoll für WLED Realtime-Control.

DRGB-Format: [0x02, timeout, R0, G0, B0, R1, G1, B1, ...]
Port: 21324

Alle 6 Controller werden gleichzeitig über einen gemeinsamen
UDP-Socket angesprochen (kein TCP-Overhead, kein Handshake).
"""
import socket
import time
from .config import CONTROLLERS, UDP_PORT

_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)

REALTIME_TIMEOUT = 5  # Sekunden — WLED kehrt nach dieser Zeit zum normalen Betrieb zurück


def push_frame(face_buffers: dict[int, bytes]) -> None:
    """
    Sendet RGB-Puffer an alle Controller.
    face_buffers: {face_id: bytes(480 * 3)}
    Fügt eine winzige Pause zwischen den Paketen ein, um Controller nicht zu überlasten.
    """
    header = bytes([0x02, REALTIME_TIMEOUT])
    for face, buf in face_buffers.items():
        host = CONTROLLERS.get(face)
        if host:
            _sock.sendto(header + buf, (host, UDP_PORT))
            time.sleep(0.0005)  # 0.5ms Pause zwischen Controllern
