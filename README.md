# netmaster

A Raspberry Pi home automation hub that provides Wake-on-LAN and TV control (via HDMI-CEC) as HTTP endpoints. It runs two Flask servers in a single process:

- **Tailscale server** (`127.0.0.1:5050`) — WoL endpoints, accessible only through `tailscale serve`
- **LAN server** (`0.0.0.0:8080`) — TV/CEC endpoints, accessible on the local network

## Requirements

- Python 3.6+
- Flask (`pip install flask`)
- `cec-client` (for TV control, e.g. `sudo apt install cec-utils`)
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
python3 server.py [--ts-port PORT] [--lan-port PORT] [--lan-host HOST] [--config PATH]
```

| Flag         | Description                        | Default              |
|--------------|------------------------------------|----------------------|
| `--ts-port`  | Tailscale-facing port on localhost | `5050`               |
| `--lan-port` | LAN-facing port                    | `8080`               |
| `--lan-host` | LAN bind address                   | `0.0.0.0`            |
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

### LAN — TV Control

These endpoints are served on `0.0.0.0:8080` and control the TV via HDMI-CEC. Requests with Tailscale identity headers are rejected.

#### `GET /tv/status`

Returns the TV power state.

```json
{ "ok": true, "message": "on" }
```

#### `POST /tv/on`

Turn the TV on.

#### `POST /tv/off`

Turn the TV off (standby).

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
