"""Headless Flask/SocketIO server — sidecar entry point for Tauri."""
import sys
import platform
import socket as _socket

if getattr(sys, "frozen", False) and sys._MEIPASS not in sys.path:
    sys.path.insert(0, sys._MEIPASS)

from app.main import create_app

HOST = "127.0.0.1"
PORT = 5254


def _probe_local_network():
    """On macOS, send a zero-byte datagram to the mDNS multicast address.

    This links the sidecar process to the app bundle's local-network privacy
    permission in TCC. Without it, macOS may block outbound UDP to LAN
    addresses (OSC targets) with EHOSTUNREACH even after the user has approved
    local network access for the main app.
    """
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.bind(("0.0.0.0", 0))
        s.sendto(b"", ("224.0.0.251", 5353))
        s.close()
    except Exception:
        pass


def main():
    if platform.system() == "Darwin":
        _probe_local_network()

    app, socketio = create_app()
    print(f"GOOEY_SERVER_READY http://{HOST}:{PORT}", flush=True)
    socketio.run(app, host=HOST, port=PORT, use_reloader=False, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
