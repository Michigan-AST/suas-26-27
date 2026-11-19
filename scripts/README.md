# First flight: take off and fly a loop

The sample takes off to 50 m, flies one 500 m square loop, and lands at
home. Coordinates are **meters north/east of home**, and height is **meters
above home**, not height above the terrain. `await` waits for each step's
telemetry before starting the next step. Fixed-wing turns round the corners;
this is an approximate square, with arrival tolerance based on PX4's loiter radius.

```python
await takeoff(drone, height=50)
await fly_to(drone, north=0, east=500, height=50)
await fly_to(drone, north=500, east=500, height=50)
await fly_to(drone, north=500, east=0, height=50)
await fly_to(drone, north=0, east=0, height=50)
await fly_to(drone, north=0, east=500, height=50)
await land_at(drone, north=0, east=0, runway_heading_deg=0)
```

## Running missions in the simulator

Run these from the repository root. Enable Docker Desktop's **Settings >
Resources > Network > Enable host networking**, then start the fixed-wing model:

```bash
make sitl SITL_ARGS="make px4_sitl gz_rc_cessna"
```

In another terminal (Python 3.9+ on macOS/Linux):

```bash
make venv
make run
```

`make run` starts the full mapping mission (`missions/mapping_sitl.json`) by default:
Takeoff → Cruise → Waypoint Laps → Lawnmower Survey (camera capture) → **auto-spawn mapper** → Search (raw-frame detect) → Delivery → Return → Landing.

The orthomosaic is built in a background process after SURVEY; you do not need `make map` during flight. Use `make map` / `make eval` only to redo or score a capture offline (see root [`README.md`](../README.md)).

### Running specific missions or the simple loop

- **Simple 500 m loop**:
  ```bash
  make run loop
  # or
  make run MISSION=loop
  # or via Python directly:
  ./.venv/bin/python scripts/drone_control.py --mission loop
  ```

- **Competition Flight Lines**:
  ```bash
  make run flight_line_1
  make run flight_line_2
  ```

- **Custom JSON file**:
  ```bash
  make run MISSION=path/to/custom_mission.json
  ```

`make venv` creates `.venv` and installs the exact package versions in
`requirements.txt`. No activation is needed: the Makefile uses `.venv/bin/python`
directly. Run it again after pulling changes to the requirements; dependencies
are reinstalled when that file changes. To choose an interpreter for a new
environment, use `make venv PYTHON=python3.11`. To change Python for an existing
environment, remove `.venv` first and recreate it. Using the same Python version
across the team gives the closest match; the Makefile does not install Python.

The script starts flying automatically once connected and ready. Run only one
simulator and one controller. QGroundControl can monitor the flight on UDP
14550; the script connects on UDP 14540. The X500 model is rejected because this
example is for a conventional fixed-wing plane.

## What happens after the loop?

The plane enters the landing approach towards the configured touchdown
coordinates and runway heading, flares, touches down, and disarms automatically.
If you prefer circling instead of landing, finish with `await loiter(drone)`.
Ctrl-C attempts Hold before disconnecting; loss of the connection then follows
PX4's configured failsafe behavior. A script error or telemetry timeout stops
the remaining instructions and attempts Hold.

For this starter, targets are limited to 2 km from home and 30–150 m above home.
Each waypoint has a 180-second timeout. These limits are for this simulator
example, not a field flight plan or a geofence. Test your edits in SITL first.

## Checks

```bash
make test
```
