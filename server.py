#!/usr/bin/env python3
"""
Lightweight REST server for Raspberry Pi CEC + WoL hub.
No dependencies beyond Python stdlib.

Endpoints:
  GET  /tv/status    - Returns TV power state
  POST /tv/on        - Turn TV on via CEC
  POST /tv/off       - Turn TV off via CEC
  POST /wol          - Send Wake-on-LAN magic packet to PC

Usage:
  python3 pi_server.py
  python3 pi_server.py --port 8080
  python3 pi_server.py --host 0.0.0.0 --port 9000
"""

import json
import socket
import struct
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PC_MAC = "AA:BB:CC:DD:EE:FF"  # Replace with your PC's MAC address
PC_BROADCAST = "255.255.255.255"  # Or your subnet broadcast, e.g. 192.168.1.255
WOL_PORT = 9

CEC_DEVICE = "0"  # CEC logical address for TV is typically 0
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080

# ---------------------------------------------------------------------------
# CEC helpers
# ---------------------------------------------------------------------------

def cec_send(command: str) -> tuple[bool, str]:
    """Send a command via cec-client. Returns (success, output)."""
    try:
        result = subprocess.run(
            ["cec-client", "-s", "-d", "1"],
            input=command + "\n",
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0, result.stdout.strip()
    except FileNotFoundError:
        return False, "cec-client not found"
    except subprocess.TimeoutExpired:
        return False, "cec-client timed out"


def tv_on() -> tuple[bool, str]:
    ok, output = cec_send(f"on {CEC_DEVICE}")
    return ok, "TV turned on" if ok else output


def tv_off() -> tuple[bool, str]:
    ok, output = cec_send(f"standby {CEC_DEVICE}")
    return ok, "TV turned off" if ok else output


def tv_status() -> tuple[bool, str]:
    """Query TV power status. Returns (success, status_string)."""
    ok, output = cec_send(f"pow {CEC_DEVICE}")
    if not ok:
        return False, output
    # cec-client output contains lines like "power status: on" or "power status: standby"
    for line in output.splitlines():
        lower = line.lower()
        if "power status:" in lower:
            if "on" in lower.split("power status:")[-1]:
                return True, "on"
            else:
                return True, "off"
    return False, f"could not parse power status: {output}"


# ---------------------------------------------------------------------------
# Wake-on-LAN
# ---------------------------------------------------------------------------

def send_wol(mac: str = PC_MAC) -> tuple[bool, str]:
    """Send a Wake-on-LAN magic packet."""
    try:
        mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
        if len(mac_bytes) != 6:
            return False, "invalid MAC address"
        # Magic packet: 6x 0xFF + 16x MAC
        packet = b"\xff" * 6 + mac_bytes * 16
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, (PC_BROADCAST, WOL_PORT))
        return True, f"WoL packet sent to {mac}"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

ROUTES: dict[tuple[str, str], callable] = {
    ("GET",  "/tv/status"): tv_status,
    ("POST", "/tv/on"):     tv_on,
    ("POST", "/tv/off"):    tv_off,
    ("POST", "/wol"):       send_wol,
}


class Handler(BaseHTTPRequestHandler):
    def _handle(self, method: str):
        handler = ROUTES.get((method, self.path))
        if handler is None:
            self._respond(404, {"error": "not found"})
            return

        ok, message = handler()
        status = 200 if ok else 500
        self._respond(status, {"ok": ok, "message": message})

    def _respond(self, status: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    # Suppress default stderr logging per request (optional — remove to debug)
    def log_message(self, format, *args):
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    host = DEFAULT_HOST
    port = DEFAULT_PORT

    args = sys.argv[1:]
    while args:
        flag = args.pop(0)
        if flag == "--host" and args:
            host = args.pop(0)
        elif flag == "--port" and args:
            port = int(args.pop(0))
        else:
            print(f"Usage: {sys.argv[0]} [--host HOST] [--port PORT]")
            sys.exit(1)

    server = HTTPServer((host, port), Handler)
    print(f"Listening on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down")
        server.server_close()


if __name__ == "__main__":
    main()