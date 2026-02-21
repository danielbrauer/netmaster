# netmaster

A Raspberry Pi Wake-on-LAN hub exposed as an HTTP endpoint. It runs a Flask server on `0.0.0.0:5050`, accessible from the LAN or via Tailscale.

## Requirements

- Python 3.6+
- Flask (`pip install flask`)

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
| `--ts-port`  | Port to listen on                  | `5050`               |
| `--config`   | Path to WoL targets JSON file      | `./wol_targets.json` |

## Endpoints

### `GET /wol`

Health check. Returns `{"ok": true}`.

### `POST /wol`

Wake a machine by target name or MAC address.

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
- `500` — Failed to send packet

### `GET /wol/last-wake/<name>`

Check when a machine was last woken via WoL. The `name` must match a target name used in a previous `POST /wol` request.

```
GET /wol/last-wake/desktop
```

**Responses:**

- `200` — `{"ok": true, "target": "desktop", "last_wake": "2026-02-21T15:30:00.123456+00:00"}`
- `404` — No WoL record for that name

Note: wake history is in-memory and resets when the server restarts.

## Running as a systemd service

Copy `netmaster.service.example` to `/etc/systemd/system/netmaster.service` and replace `YOUR_USER` with your username, then:

```
sudo systemctl daemon-reload
sudo systemctl enable --now netmaster
```
