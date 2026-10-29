#!/usr/bin/env python3
"""Student starter code: take off, fly a square loop, and loiter in PX4 SITL."""

# .venv/bin/python scripts/drone_control.py


import asyncio
import json
import math
from pathlib import Path
import signal
import subprocess

import mavsdk
from mavsdk import System


async def flight_instructions(drone):
    # START HERE: write your flight instructions in order below.
    # Distances are metres NORTH and EAST of home. Height is metres above home.
    # 'await' waits for a step to finish before moving to the next instruction.

    await takeoff(drone, height=50)

    # Fly to the first corner, then fly one 500 m by 500 m square loop.
    await fly_to(drone, north=0, east=500, height=50)
    await fly_to(drone, north=500, east=500, height=50)
    await fly_to(drone, north=500, east=0, height=50)
    await fly_to(drone, north=0, east=0, height=50)
    await fly_to(drone, north=0, east=500, height=50)

    # A fixed-wing plane cannot hover. Finish by circling at this location.
    await loiter(drone)


# Helper functions: you should not need to edit these for your first flight.

async def command(operation):
    """Send one SDK request, with a timeout if PX4 does not respond."""
    return await asyncio.wait_for(operation, timeout=15)


async def wait_for(stream, condition, timeout=180):
    """Watch telemetry until a condition is met, instead of guessing a delay."""
    async def watch():
        try:
            async for value in stream:
                if condition(value):
                    return value
            raise RuntimeError("Telemetry stream ended before the step finished")
        finally:
            await stream.aclose()

    return await asyncio.wait_for(watch(), timeout=timeout)


async def check_aircraft(drone):
    """Check that we connected to a conventional PX4 fixed-wing aircraft."""
    async def check():
        stream = drone.mavlink_direct.message("HEARTBEAT")
        try:
            async for message in stream:
                fields = json.loads(message.fields_json)
                if message.component_id == 1 and fields.get("autopilot") == 12:
                    if fields.get("type") != 1:  # MAV_TYPE_FIXED_WING
                        raise RuntimeError("Start the fixed-wing model: gz_rc_cessna")
                    return
            raise RuntimeError("No PX4 heartbeat received")
        finally:
            await stream.aclose()

    await asyncio.wait_for(check(), timeout=15)


async def takeoff(drone, height):
    """Use the configured fixed-wing launch procedure, then wait for climbout."""
    if not math.isfinite(height) or not 30 <= height <= 150:
        raise ValueError("Use a takeoff height between 30 and 150 metres")

    armed = await wait_for(drone.telemetry.armed(), lambda value: True, timeout=10)
    in_air = await wait_for(drone.telemetry.in_air(), lambda value: True, timeout=10)
    if armed or in_air:
        raise RuntimeError("Start this example with the plane disarmed and on the ground")

    await wait_for(
        drone.telemetry.health(),
        lambda health: health.is_global_position_ok and health.is_home_position_ok,
        timeout=60,
    )

    # Fixed-wing Takeoff mode must be selected before arming in this setup.
    await command(drone.action.set_takeoff_altitude(height))
    await command(drone.action.takeoff())
    await wait_for(drone.telemetry.health(), lambda health: health.is_armable, timeout=20)
    await command(drone.action.arm())
    print(f"Taking off and climbing to {height:g} m...")

    await wait_for(drone.telemetry.in_air(), lambda flying: flying)
    await wait_for(
        drone.telemetry.position(),
        lambda position: position.relative_altitude_m >= height - 5,
    )
    print("Takeoff complete.")


async def fly_to(drone, north, east, height):
    """Fly near a point given in metres north/east of home at the given height."""
    if not all(math.isfinite(value) for value in (north, east, height)):
        raise ValueError("Distances and height must be finite numbers")
    if math.hypot(north, east) > 2000 or not 30 <= height <= 150:
        raise ValueError("Keep targets within 2 km of home and 30–150 m above home")

    home = await wait_for(drone.telemetry.home(), lambda value: True, timeout=10)
    cosine = math.cos(math.radians(home.latitude_deg))
    if abs(cosine) < 0.01:
        raise ValueError("This example does not support flights near the poles")

    # Convert the student's metre offsets into the GPS coordinates PX4 expects.
    metres_per_degree = math.pi * 6_371_000 / 180
    latitude = home.latitude_deg + north / metres_per_degree
    longitude = (home.longitude_deg + east / (metres_per_degree * cosine) + 180) % 360 - 180
    altitude = home.absolute_altitude_m + height  # MAVSDK needs altitude above sea level.

    # A plane starts turning before reaching a point. Allow its configured loiter
    # radius plus a margin, rather than requiring it to pass through the centre.
    radius = await command(drone.param.get_param_float("NAV_LOITER_RAD"))
    arrival_radius = max(50, abs(radius) + 30)

    print(f"Flying to north={north:g} m, east={east:g} m, height={height:g} m...")
    await command(drone.action.goto_location(latitude, longitude, altitude, math.nan))

    def arrived(position):
        delta_lon = (position.longitude_deg - longitude + 180) % 360 - 180
        distance = math.hypot(
            (position.latitude_deg - latitude) * metres_per_degree,
            delta_lon * metres_per_degree * cosine,
        )
        return distance <= arrival_radius and abs(position.absolute_altitude_m - altitude) <= 10

    await wait_for(drone.telemetry.position(), arrived)
    print("Waypoint reached (within the turn radius).")


async def loiter(drone):
    """Keep flying in a circle using PX4's Hold mode."""
    await command(drone.action.hold())
    print("Loitering. Monitor the plane in QGroundControl.")


async def main():
    drone = System(mavsdk_server_address="127.0.0.1")
    backend = None
    verified = False

    # Let Ctrl-C cancel the flight steps and reach the cleanup block below.
    task = asyncio.current_task()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, task.cancel)

    try:
        print("Connecting to the simulator...")

        # Run the SDK connection in its own process group, so Ctrl-C reaches
        # this script first and we can request Hold before closing the link.
        server = Path(mavsdk.__file__).parent / "bin" / "mavsdk_server"
        backend = subprocess.Popen(
            [str(server), "-p", "50051", "udpin://0.0.0.0:14540"],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        await asyncio.wait_for(drone.connect(), 30)
        await wait_for(drone.core.connection_state(), lambda state: state.is_connected, timeout=20)
        await check_aircraft(drone)
        verified = True

        await flight_instructions(drone)
        print("Loop complete! Keeping the connection open. Ctrl-C disconnects.")

        # Keep sending the SDK heartbeat while the plane loiters.
        await asyncio.Event().wait()

    except asyncio.CancelledError:
        print("\nStopping the script...")
    except Exception as error:
        print(f"Flight stopped: {str(error) or type(error).__name__}")
    finally:
        try:
            if verified:
                in_air = await wait_for(drone.telemetry.in_air(), lambda value: True, timeout=5)
                if in_air:
                    await loiter(drone)
                else:
                    armed = await wait_for(drone.telemetry.armed(), lambda value: True, timeout=5)
                    if armed:
                        await command(drone.action.disarm())
        except Exception as error:
            print(f"Check QGroundControl; exit recovery was not confirmed: {error}")
        finally:
            if backend is not None:
                backend.terminate()
                try:
                    backend.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    backend.kill()
                    backend.wait()


if __name__ == "__main__":
    asyncio.run(main())
