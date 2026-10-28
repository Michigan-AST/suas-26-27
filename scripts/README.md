# First flight: take off and fly a loop

Edit **`flight_instructions()` at the top of `drone_control.py`**, under
`# START HERE`. This is where your drone instructions go. The helper functions
below handle the PX4 connection and telemetry.

The sample takes off to 50 m, flies one 500 m square loop, and then loiters.
Coordinates are **metres north/east of home**, and height is **metres above
home**, not height above the terrain. `await` waits for each step's telemetry
before starting the next step. Fixed-wing turns round the corners; this is an
approximate square, with arrival tolerance based on PX4's loiter radius.

```python
await takeoff(drone, height=50)
await fly_to(drone, north=0, east=500, height=50)
await fly_to(drone, north=500, east=500, height=50)
await fly_to(drone, north=500, east=0, height=50)
await fly_to(drone, north=0, east=0, height=50)
await fly_to(drone, north=0, east=500, height=50)
await loiter(drone)
```

## Run it in the simulator

Run these from the repository root. Enable Docker Desktop's **Settings >
Resources > Network > Enable host networking**, then start the fixed-wing model:

```bash
bash sitl.sh make px4_sitl gz_rc_cessna
```

In another terminal (Python 3.9+ on macOS/Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/drone_control.py
```

The script starts flying automatically once connected and ready. Run only one
simulator and one controller. QGroundControl can monitor the flight on UDP
14550; the script connects on UDP 14540. The X500 model is rejected because this
example is for a conventional fixed-wing plane.

## What happens after the loop?

The plane circles in Hold mode, and the script stays connected. **It does not
land automatically.** Monitor it in QGroundControl and use an appropriate
fixed-wing landing procedure. Ctrl-C attempts Hold before disconnecting; loss
of the connection then follows PX4's configured failsafe behavior. A script
error or telemetry timeout stops the remaining instructions and attempts Hold.

For this starter, targets are limited to 2 km from home and 30–150 m above home.
Each waypoint has a 180-second timeout. These limits are for this simulator
example, not a field flight plan or a geofence. Test your edits in SITL first.

## Checks

```bash
.venv/bin/python -m unittest discover -s tests
```
