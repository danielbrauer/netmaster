#!/usr/bin/env python3
"""
Raspberry Pi WoL hub server (Flask).

Tailscale setup (one-time):
  tailscale serve --https=443 http://127.0.0.1:5050

Endpoints:
  Tailscale (via tailscale serve):
    POST /wol              - Wake a machine by name or MAC

Usage:
  python3 server.py
  python3 server.py --ts-port 5050
  python3 server.py --config /path/to/wol_targets.json
"""

import argparse
import json
import logging
import os
import socket
import struct
from pathlib import Path

from flask import Flask, jsonify, request

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TAILSCALE_HOST = "127.0.0.1"
TAILSCALE_PORT = 5050

WOL_TARGETS_PATH = Path(__file__).parent / "wol_targets.json"
PC_BROADCAST = "255.255.255.255"  # Or your subnet broadcast, e.g. 192.168.1.255
WOL_PORT = 9

# Module-level state (loaded at startup)
wol_targets: dict = {}

# Set log level via LOG_LEVEL env var (e.g. LOG_LEVEL=DEBUG)
log_level = os.environ.get("LOG_LEVEL", "WARNING").upper()
logging.getLogger("werkzeug").setLevel(getattr(logging, log_level, logging.WARNING))

# ---------------------------------------------------------------------------
# Wake-on-LAN
# ---------------------------------------------------------------------------


def send_wol(mac: str) -> tuple[bool, str]:
    """Send a Wake-on-LAN magic packet."""
    try:
        mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
        if len(mac_bytes) != 6:
            return False, "invalid MAC address"
        packet = b"\xff" * 6 + mac_bytes * 16
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, (PC_BROADCAST, WOL_PORT))
        return True, f"WoL packet sent to {mac}"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# WoL target config
# ---------------------------------------------------------------------------


def load_wol_targets(path: Path) -> dict:
    """Load WoL target map from JSON file. Returns empty dict on failure."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: WoL targets file not found: {path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Warning: Invalid JSON in {path}: {e}")
        return {}


# ---------------------------------------------------------------------------
# Tailscale app (WoL — localhost only, behind tailscale serve)
# ---------------------------------------------------------------------------

app = Flask("netmaster")


@app.route("/wol", methods=["GET", "POST"])
def wol_handler():
    # GET is used by tailscale serve health checks
    if request.method == "GET":
        return jsonify(ok=True), 200

    # Verify request came through tailscale serve
    ts_user = request.headers.get("Tailscale-User-Login")
    if not ts_user:
        return jsonify(ok=False, error="forbidden: Tailscale identity required"), 403

    body = request.get_json(silent=True) or {}

    # Resolve MAC address from target name or direct MAC
    if "target" in body:
        target_name = body["target"]
        target = wol_targets.get(target_name)
        if target is None:
            available = ", ".join(wol_targets.keys()) if wol_targets else "(none)"
            return jsonify(
                ok=False,
                error=f"unknown target: '{target_name}'",
                available=available,
            ), 400
        mac = target["mac"]
    elif "mac" in body:
        mac = body["mac"]
    else:
        return jsonify(ok=False, error="request must include 'target' or 'mac'"), 400

    ok, message = send_wol(mac)
    status = 200 if ok else 500
    return jsonify(ok=ok, message=message), status


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Raspberry Pi WoL hub")
    parser.add_argument(
        "--ts-port",
        type=int,
        default=TAILSCALE_PORT,
        help=f"Tailscale-facing port on localhost (default {TAILSCALE_PORT})",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=WOL_TARGETS_PATH,
        help=f"WoL targets JSON file (default {WOL_TARGETS_PATH})",
    )
    args = parser.parse_args()

    global wol_targets
    wol_targets = load_wol_targets(args.config)

    print(f"Listening: {TAILSCALE_HOST}:{args.ts_port}")
    if wol_targets:
        print(f"WoL targets: {', '.join(wol_targets.keys())}")
    else:
        print("WoL targets: (none loaded)")

    try:
        app.run(host=TAILSCALE_HOST, port=args.ts_port, use_reloader=False)
    except KeyboardInterrupt:
        print("\nShutting down")


if __name__ == "__main__":
    main()
