"""Launch the Due Diligence Workstation (local browser UI)."""

from __future__ import annotations

import logging
import socket
import sys

import eel

from app.server import init_eel, register_exposables

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

_LOG = logging.getLogger(__name__)
PORT = 8765
HOST = "127.0.0.1"


def _port_taken(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((host, port)) == 0


def main() -> None:
    if _port_taken(HOST, PORT):
        raise OSError(
            f"Port {PORT} is already in use. Use the Stop file in the Mac, Windows, or Linux folder, then start again."
        )

    init_eel()
    register_exposables()
    _LOG.info("Due Diligence Workstation on http://%s:%s/ (also try http://localhost:%s/)", HOST, PORT, PORT)
    print("", flush=True)
    print("Ready. Leave this window open.", flush=True)
    print(f"  http://localhost:{PORT}/", flush=True)
    print(f"  http://127.0.0.1:{PORT}/", flush=True)
    print("If one does not load, try the other. They are the same app.", flush=True)
    print("", flush=True)

    eel.start(
        "index.html",
        host=HOST,
        port=PORT,
        mode=None,
        block=True,
        close_callback=lambda *_a: None,
    )


if __name__ == "__main__":
    sys.exit(main() or 0)
