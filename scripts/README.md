# Python drone commands

A small command interface for the **PX4 X500 simulator** on macOS/Linux,
using Python 3.9 or later. Run all shell commands below from the repository root.

## Setup

Start Docker Desktop with host networking enabled, then launch the simulator:

```bash
bash sitl.sh
```

In a second terminal, install and run the controller:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/drone_control.py
```

The script listens on UDP `14540`. QGroundControl can remain open on UDP
`14550` to monitor the vehicle. Run one controller at a time. The dependency is
pinned to MAVSDK 3.10.2 because MAVSDK 4 changed its Python interface.

If connection times out on Docker Desktop, first check host networking is
enabled. On setups where container localhost traffic still does not reach the
Mac, run this in another Mac terminal **after PX4 finishes starting**, then
retry the script. It adds a temporary MAVLink stream to the Mac through
`host.docker.internal`; it changes no source files and ends with the simulator:

```bash
docker exec suas-px4-sitl sh -c '
  host_ip=$(getent ahostsv4 host.docker.internal | head -n 1 | cut -d " " -f 1)
  test -n "$host_ip" || exit 1
  build/px4_sitl_default/bin/px4-mavlink start -x -u 14581 -o 14540 -t "$host_ip" -r 4000000 -m onboard
'
```

## Commands

```text
status
takeoff 5
move north 10
status
hold
move east 5
land
quit
```

Type `help` to list commands. `rtl` requests PX4's return-to-launch procedure
and waits for disarming; its route and landing behavior follow PX4's RTL
parameters. Use `land` to land at the current location.

Takeoff waits for the requested height. Movement is relative to the **current
measured position**, along compass axes rather than the drone's heading.
`move` sends a target and returns immediately so you can use `hold`, `land`,
or `rtl` while moving. Check `status` before issuing the next relative move.
PX4 chooses the speed using its configured position-control parameters.
MAVSDK resends the Offboard target continuously; once reached, PX4 holds it.
`hold` switches to PX4 Hold mode at the current location.

Takeoff altitude must be 1–20 metres above home. Each move is at most 20 metres,
with targets restricted to 50 metres horizontally from PX4's local origin and
1–20 metres above that origin (local NED uses negative down for up).
Home and local-origin altitude are approximately equal in the default SITL setup.
These are command limits, not a PX4 geofence.

Readiness failures and rejected commands are printed. Takeoff first requests
Hold and waits for PX4 to report that it can arm. Wait for valid position
and home estimates before retrying takeoff. Commands have timeouts; a failed
takeoff or move attempts Hold. `land` and `rtl` wait up to 120 seconds for ground
and disarmed telemetry. A timeout does not cancel the autopilot's action.

`quit`, Ctrl-D, or Ctrl-C attempts landing if armed before exiting. If landing
cannot be confirmed, check QGroundControl. A killed process or lost connection
cannot guarantee landing; PX4's configured link/Offboard-loss behavior applies.
Keep the simulator running until landing completes.

This is a simulator starter, with no hardware connection option. UDP alone does
not identify a simulated vehicle: keep physical vehicles off this endpoint.

References: [MAVSDK 3 Python quickstart](https://mavsdk.mavlink.io/v2.0/en/python/quickstart.html)
and [Offboard control](https://mavsdk.mavlink.io/main/en/cpp/guide/offboard.html).
