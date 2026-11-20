# suas-26-27

Code and documentation for the M-AST 2026-27 drone for the S.U.A.S competition.

## Prerequisites

- **Docker Desktop** (macOS/Linux/Windows)
- **QGroundControl** (installed on host)
- **Python 3.9+** and `make`
- **tmux** + **Foxglove Studio** (for `make up`)

## Quick Start

### 1. Configure Docker Networking (macOS)

In Docker Desktop, navigate to **Settings > Resources > Network** and enable **Enable host networking**. Apply and restart Docker Desktop.

Make sure Docker Desktop is running, if you're using it.

### 2. One-command SITL + mission (recommended)

```bash
brew install tmux                 # once
brew install --cask foxglove      # once, if needed
make up                           # opens QGC + Foxglove, then tmux: sitl | mission | scratch
```

This opens **QGroundControl** and **Foxglove Studio** (WebSocket `ws://localhost:8765`), then starts PX4 + Gazebo + nadir camera (`make sitl`), waits until `http://127.0.0.1:8554/health` is ready, and runs `mapping_sitl`. Foxglove telemetry starts with the mission. Import [`foxglove_layout.json`](foxglove_layout.json) once via **Layout → Import from file…** (re-import after pulling layout updates). Detach with `Ctrl-b d`; `make down` stops tmux + Docker (leaves QGC/Foxglove running). Skip host apps with `SUAS_SKIP_APPS=1 make up`.

Foxglove during a mapping flight shows: 3D site + survey plan + flown track + capture footprints, nadir camera, orthomosaic (when the background mapper finishes), mission phase (`/mission`), declared targets, GPS map, and alt/airspeed/attitude/**battery** plots.

### 3. Manual / split-terminal alternative

```bash
make sitl                 # CAMERA=1 + suas_site by default
make sitl SPEED=2         # faster-than-realtime
make sitl CAMERA=0 WORLD=moving_platform   # plain PX4 world, no mapping camera

make run                  # mapping_sitl by default
make down                 # stop container / tmux session
```

`sitl.sh` remains a thin wrapper around `make sitl` (`--no-camera`, `--speed`, etc.).

### 4. Mapping & evaluation (what runs when)

You do **not** run `make map` during the flight.

| When | What happens |
|------|----------------|
| During SURVEY | Camera frames are written to `captures/<run_id>/` |
| Right after SURVEY | Mission **auto-spawns** a fault-isolated mapper subprocess (look for `Spawned fault-isolated mapper subprocess...`). SEARCH/DELIVERY continue without waiting. Output: `captures/<run_id>/MAST_risk_map.png` |
| During SEARCH | Target detection runs on the **raw frames** (not the mosaic) |

Offline tools (optional, after the fact):

```bash
make map    # redo orthomosaic for the newest capture (or: make map <run_id>)
make eval   # score coverage % + target geolocation vs worlds/suas_site/scene.json
```

`make map` / `make eval` are for re-stitching or scoring — they are not part of the flight loop.

### 5. View the Drone in 3D (Foxglove Studio)

1. **Open Foxglove Studio** (or [https://app.foxglove.dev](https://app.foxglove.dev)).
2. **Layout → Import from file…** → [`foxglove_layout.json`](foxglove_layout.json).
3. **Open connection** → Foxglove WebSocket → `ws://localhost:8765`.

Whenever you run `make run`, 3D transforms and telemetry stream automatically. You can also run `make foxglove` anytime without flying the autonomous mission.

### 6. Stop the Simulation

```bash
make down
# or: docker stop suas-px4-sitl
```

---

## Python Development & Testing

- **Edit Flight Instructions**: Modify `flight_instructions()` at the top of [`scripts/drone_control.py`](scripts/drone_control.py).
- **Run Tests**: `make test`
- **Custom Python Interpreter**: `make venv PYTHON=python3.11`

---

## Troubleshooting

### QGroundControl Connection

If QGroundControl does not connect automatically:

1. Open **Application Settings > Comm Links**.
2. Disable UDP auto-connect.
3. Add a manual UDP link with listening port `14550` and target host `127.0.0.1:18570`.

### Docker Image Export Failures

If you see `failed to receive status ... error reading from server: EOF` during layer export:

1. Confirm Docker Desktop is running and has sufficient disk space/memory allocated.
2. Rebuild: `make sitl REBUILD=1`
