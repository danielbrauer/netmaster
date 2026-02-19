# netmaster

A Raspberry Pi Wake-on-LAN hub exposed as an HTTP endpoint via Tailscale. It runs a Flask server on `127.0.0.1:5050`, intended to be exposed via `tailscale serve`.

## Requirements

- Python 3.6+
- Flask (`pip install flask`)
- Tailscale (for remote WoL access)

## Configuration

### WoL targets

Create a file called `wol_targets.json` in the project directory (see `wol_targets.example.json`):

```json
{
  "desktop": {
    "mac": "AA:BB:CC:DD:EE:FF"
  },
  "server": {
    "mac": "11:22:33:44:55:66"
  }
}
```

Each key is a friendly name you can use to wake the device. The `mac` field is the target device's MAC address.

### Environment variables

| Variable    | Description                          | Default   |
|-------------|--------------------------------------|-----------|
| `LOG_LEVEL` | Werkzeug log level (e.g. `DEBUG`, `INFO`) | `WARNING` |

### Command-line options

```
python3 server.py [--ts-port PORT] [--config PATH]
```

| Flag         | Description                        | Default              |
|--------------|------------------------------------|----------------------|
| `--ts-port`  | Tailscale-facing port on localhost | `5050`               |
| `--config`   | Path to WoL targets JSON file      | `./wol_targets.json` |

## Endpoints

### Tailscale — Wake-on-LAN

These endpoints are served on `127.0.0.1:5050` and are intended to be exposed via `tailscale serve`.

#### `GET /wol`

Health check. Returns `{"ok": true}`.

#### `POST /wol`

Wake a machine by target name or MAC address. Requires the `Tailscale-User-Login` header (set automatically by `tailscale serve`).

**Wake by name** (must match a key in `wol_targets.json`):

```json
{ "target": "desktop" }
```

**Wake by MAC address directly:**

```json
{ "mac": "AA:BB:CC:DD:EE:FF" }
```

**Responses:**

- `200` — WoL packet sent successfully
- `400` — Unknown target name, or missing `target`/`mac` field
- `403` — Request did not come through Tailscale
- `500` — Failed to send packet

## Tailscale setup

Expose the WoL endpoint over your tailnet (one-time):

```
tailscale serve --https=443 http://127.0.0.1:5050
```

## Running as a systemd service

Copy `netmaster.service.example` to `/etc/systemd/system/netmaster.service` and replace `YOUR_USER` with your username, then:

```
sudo systemctl daemon-reload
sudo systemctl enable --now netmaster
```
