#!/usr/bin/env python3
"""Interactive MAVSDK commands for the PX4 X500 simulator (macOS/Linux)."""

import asyncio
import math
import signal
import sys
import time

from mavsdk import System
from mavsdk.action import ActionError
from mavsdk.offboard import OffboardError, PositionNedYaw


HELP = """Commands:
  status                       Show telemetry
  takeoff <metres>              Take off to 1–20 m above home
  move <direction> <metres>     north/south/east/west/up/down, 0–20 m
  hold                         Hold the current position
  land                         Land here and wait for disarming
  rtl                          Return home and wait for disarming
  help                         Show commands
  quit                         Land if armed, then disconnect
Movement stays within 50 m of the local origin and 1–20 m above it.
"""


class Controller:
    """Translate terminal commands into PX4 actions and track telemetry."""

    def __init__(self):
        self.drone = System()
        self.address = "udpin://0.0.0.0:14540"

        # Cache each telemetry value with the time it was received.
        self.values = {}
        self.tasks = []

        # Remember an arming attempt even before telemetry confirms it.
        self.arm_requested = False

    async def observe(self, name, stream):
        """Keep one telemetry subscription running in the background."""
        async for value in stream:
            self.values[name] = (value, time.monotonic())

    def get(self, name):
        """Read cached telemetry, rejecting missing or stale measurements."""
        value, timestamp = self.values.get(name, (None, 0))

        # State subscriptions may emit only when their value changes.
        # Only continuously updated measurements have a freshness deadline.
        if value is None or (
            name in ("local", "attitude", "position", "battery")
            and time.monotonic() - timestamp > 5
        ):
            raise RuntimeError(f"No recent {name} telemetry")

        return value

    async def wait_for(self, condition, timeout):
        """Wait for a telemetry condition without blocking other async tasks."""
        async def poll():
            while not condition():
                await asyncio.sleep(0.1)

        await asyncio.wait_for(poll(), timeout)

    async def call(self, operation):
        """Limit how long an individual SDK request can take."""
        return await asyncio.wait_for(operation, 10)

    async def connect(self):
        """Connect to SITL and start the telemetry subscriptions."""
        print(f"Connecting to {self.address} (up to 30 seconds)...")
        await asyncio.wait_for(
            self.drone.connect(system_address=self.address), 30
        )

        # Separate tasks keep telemetry flowing while commands are running
        # or the terminal is waiting for input.
        for name, stream in {
            "connection": self.drone.core.connection_state(),
            "armed": self.drone.telemetry.armed(),
            "in_air": self.drone.telemetry.in_air(),
            "health": self.drone.telemetry.health(),
            "position": self.drone.telemetry.position(),
            "local": self.drone.telemetry.position_velocity_ned(),
            "attitude": self.drone.telemetry.attitude_euler(),
            "mode": self.drone.telemetry.flight_mode(),
            "battery": self.drone.telemetry.battery(),
        }.items():
            self.tasks.append(asyncio.create_task(self.observe(name, stream)))

        # A running SDK backend does not yet mean PX4 is connected or ready.
        await self.wait_for(
            lambda: "connection" in self.values
            and self.get("connection").is_connected,
            20,
        )
        await self.wait_for(
            lambda: all(
                key in self.values
                for key in ("armed", "in_air", "health", "local")
            ),
            20,
        )

        print("Connected to PX4.")

    def require_flight(self):
        """Reject movement commands unless the drone is connected and flying."""
        if not self.get("connection").is_connected:
            raise RuntimeError("Drone disconnected")

        if not self.get("armed") or not self.get("in_air"):
            raise RuntimeError("Take off before moving or holding")

    async def hold(self):
        """Ask PX4 to hold its current position."""
        self.require_flight()

        # PX4 Hold takes over from Offboard without an intermediate stale target.
        await self.call(self.drone.action.hold())

    async def takeoff(self, altitude):
        """Check readiness, arm, and wait until the requested height is reached."""
        if not 1 <= altitude <= 20:
            raise ValueError("Takeoff altitude must be 1–20 metres")

        if self.get("armed") or self.get("in_air"):
            raise RuntimeError("Drone must be disarmed and on the ground")

        health = self.get("health")
        if not (
            health.is_global_position_ok
            and health.is_home_position_ok
            and health.is_local_position_ok
        ):
            raise RuntimeError("Position/home estimate is not ready; try again shortly")

        # A previous Land/RTL/Offboard mode may inhibit a new arming attempt.
        await self.call(self.drone.action.hold())
        await self.wait_for(lambda: self.get("health").is_armable, 10)
        await self.call(self.drone.action.set_takeoff_altitude(altitude))

        self.arm_requested = True
        try:
            await self.call(self.drone.action.arm())
        except ActionError:
            # An explicit rejection means the arming request did not succeed.
            self.arm_requested = False
            raise

        # Send takeoff promptly: PX4 can auto-disarm if it stays on the ground.
        await self.call(self.drone.action.takeoff())
        print(f"Taking off to {altitude:g} m...")

        # Acknowledgment of the command is different from reaching the height.
        await self.wait_for(
            lambda: self.get("in_air")
            and abs(self.get("position").relative_altitude_m - altitude) < 0.5,
            45,
        )
        print("Takeoff altitude reached.")

    async def move(self, direction, distance):
        """Send a position target relative to the current measured position."""
        # PX4 uses north/east/down (NED), so moving up reduces the down value.
        directions = {
            "north": (1, 0, 0),
            "south": (-1, 0, 0),
            "east": (0, 1, 0),
            "west": (0, -1, 0),
            "up": (0, 0, -1),
            "down": (0, 0, 1),
        }

        if direction not in directions or not 0 < distance <= 20:
            raise ValueError("Use move north/south/east/west/up/down <metres>, 0 < metres <= 20")

        self.require_flight()
        current = self.get("local").position
        yaw = self.get("attitude").yaw_deg

        # Keep the current heading and offset the position along compass axes.
        dn, de, dd = directions[direction]
        north = current.north_m + dn * distance
        east = current.east_m + de * distance
        down = current.down_m + dd * distance

        # These bounds validate targets; they do not configure a PX4 geofence.
        if math.hypot(north, east) > 50 or not 1 <= -down <= 20:
            raise ValueError("Target exceeds the 50 m radius or 1–20 m altitude limits")

        # Seed with the current position before switching to Offboard.
        await self.call(
            self.drone.offboard.set_position_ned(
                PositionNedYaw(current.north_m, current.east_m, current.down_m, yaw)
            )
        )
        await self.call(self.drone.offboard.start())

        # MAVSDK continuously resends this setpoint while the REPL accepts commands.
        await self.call(
            self.drone.offboard.set_position_ned(
                PositionNedYaw(north, east, down, yaw)
            )
        )
        print(f"Target sent: {distance:g} m {direction}. Use status or hold while moving.")

    async def finish_flight(self, return_home=False):
        """Land here or return home, then wait for touchdown and disarming."""
        await self.call(
            self.drone.action.return_to_launch()
            if return_home
            else self.drone.action.land()
        )
        print("Returning home..." if return_home else "Landing...")

        await self.wait_for(lambda: not self.get("in_air") and not self.get("armed"), 120)
        self.arm_requested = False
        print("On ground and disarmed.")

    def status(self):
        """Print available telemetry, including any missing-data errors."""
        for name in ("connection", "armed", "in_air", "mode", "health", "battery", "position"):
            try:
                print(f"{name}: {self.get(name)}")
            except RuntimeError as error:
                print(error)

        # Display height as positive up, although PX4 reports positive down.
        try:
            p = self.get("local").position
            print(f"Local N/E/up: {p.north_m:.1f} / {p.east_m:.1f} / {-p.down_m:.1f} m")
        except RuntimeError as error:
            print(error)

    async def execute(self, line):
        """Parse one command; return False when the user requests quit."""
        parts = line.lower().split()
        if not parts:
            return True

        command, *args = parts

        # Check argument counts before converting values or sending commands.
        if command == "takeoff" and len(args) == 1:
            await self.takeoff(float(args[0]))
        elif command == "move" and len(args) == 2:
            await self.move(args[0], float(args[1]))
        elif command == "hold" and not args:
            await self.hold()
            print("Holding position.")
        elif command in ("land", "rtl") and not args:
            await self.finish_flight(return_home=command == "rtl")
        elif command == "status" and not args:
            self.status()
        elif command == "help" and not args:
            print(HELP)
        elif command == "quit" and not args:
            return False
        else:
            raise ValueError("Unknown command or wrong arguments. Type help.")

        return True


async def read_command():
    """Read without blocking telemetry or leaving a background input thread."""
    loop = asyncio.get_running_loop()
    ready = loop.create_future()

    # Wake up only when stdin is readable, leaving the event loop free meanwhile.
    loop.add_reader(sys.stdin, lambda: ready.done() or ready.set_result(None))
    try:
        await ready
        return sys.stdin.readline()
    finally:
        loop.remove_reader(sys.stdin)


async def main():
    """Run the command loop and clean up the vehicle and SDK on exit."""
    controller = Controller()
    task = asyncio.current_task()
    loop = asyncio.get_running_loop()

    # Cancel the command loop on Ctrl-C or termination so finally can land.
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, task.cancel)

    try:
        await controller.connect()
        print(HELP)

        while True:
            print("drone> ", end="", flush=True)
            line = await read_command()
            if not line:  # EOF / Ctrl-D
                break

            try:
                if not await controller.execute(line):
                    break
            except ValueError as error:
                # Input mistakes should not change the drone's flight mode.
                print(f"Command failed: {error}")
            except (RuntimeError, ActionError, OffboardError, asyncio.TimeoutError) as error:
                print(f"Command failed: {str(error) or type(error).__name__}")

                # Freeze movement after a failed flight command where possible.
                if line.split() and line.split()[0].lower() in ("move", "takeoff"):
                    try:
                        if controller.get("armed") and controller.get("in_air"):
                            await controller.hold()
                    except (RuntimeError, ActionError, asyncio.TimeoutError) as recovery:
                        print(f"Could not hold: {recovery}")

    except asyncio.CancelledError:
        print("\nStopping; attempting to land if armed.")
    finally:
        try:
            # A command may have armed before its telemetry update arrived.
            # Request land on unknown/stale armed state too, if connected.
            if "connection" in controller.values:
                try:
                    needs_landing = controller.get("armed") or controller.arm_requested
                except RuntimeError:
                    needs_landing = True

                if needs_landing:
                    await controller.finish_flight()
        except (RuntimeError, ActionError, asyncio.TimeoutError) as error:
            print(f"Landing could not be confirmed: {error}. Check QGroundControl.")
        finally:
            # Finish the telemetry tasks before stopping their SDK backend.
            for observer in controller.tasks:
                observer.cancel()
            await asyncio.gather(*controller.tasks, return_exceptions=True)

            # This pinned SDK has no public close(); explicitly stop its owned
            # backend, including when connection discovery times out.
            controller.drone._stop_mavsdk_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (RuntimeError, asyncio.TimeoutError) as error:
        sys.exit(f"Connection/control failed: {str(error) or type(error).__name__}")
