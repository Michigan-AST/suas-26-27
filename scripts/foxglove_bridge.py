#!/usr/bin/env python3
"""Foxglove Studio bridge: streams PX4 telemetry and 3D transforms to Foxglove Studio."""

from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass
from typing import Any, Optional

import foxglove
from foxglove.schemas import (
    Color,
    CubePrimitive,
    FrameTransform,
    LocationFix,
    Pose,
    Quaternion,
    SceneEntity,
    SceneUpdate,
    Timestamp,
    Vector3,
)


@dataclass
class TelemetryState:
    # NED position & relative altitude
    north_m: float = 0.0
    east_m: float = 0.0
    down_m: float = 0.0
    rel_alt_m: float = 0.0
    abs_alt_m: float = 0.0

    # Euler attitude (deg, PX4 NED convention)
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0

    # GPS coordinates
    latitude_deg: float = 47.397742  # default SITL Zurich airfield coordinates
    longitude_deg: float = 8.545594

    # Flight dynamics & status
    airspeed_m_s: float = 0.0
    climb_rate_m_s: float = 0.0
    throttle_pct: float = 0.0
    battery_pct: float = 100.0
    voltage_v: float = 16.8
    in_air: bool = False
    armed: bool = False
    flight_mode: str = "UNKNOWN"


def euler_ned_to_enu_quat(roll_deg: float, pitch_deg: float, yaw_deg: float) -> tuple[float, float, float, float]:
    """Convert PX4 NED Euler angles (degrees) to an ENU coordinate quaternion.

    In aviation NED:
      - 0 deg yaw points North (+X in NED, +Y in ENU)
      - 90 deg yaw points East (+Y in NED, +X in ENU)
      - Pitch is nose up (+)
      - Roll is right wing down (+)

    In Foxglove ENU robotics frame:
      - +X is East, +Y is North, +Z is Up
      - Body frame: +X forward, +Y left, +Z up
    """
    roll = math.radians(roll_deg)
    pitch = math.radians(pitch_deg)
    yaw = math.radians(yaw_deg)

    # In ENU: yaw is measured counterclockwise from East (+X) toward North (+Y)
    yaw_enu = math.pi / 2.0 - yaw
    pitch_enu = pitch
    roll_enu = -roll

    cy = math.cos(yaw_enu * 0.5)
    sy = math.sin(yaw_enu * 0.5)
    cp = math.cos(pitch_enu * 0.5)
    sp = math.sin(pitch_enu * 0.5)
    cr = math.cos(roll_enu * 0.5)
    sr = math.sin(roll_enu * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    return x, y, z, w


def build_airplane_entity(ts: Optional[Timestamp] = None) -> SceneUpdate:
    """Create a fixed-wing RC Cessna 3D model using primitives for the Foxglove 3D scene."""
    if ts is None:
        ts = Timestamp(sec=int(time.time()), nsec=0)
    white = Color(r=0.92, g=0.92, b=0.96, a=1.0)
    blue = Color(r=0.0, g=0.2, b=0.55, a=1.0)   # Michigan Blue
    maize = Color(r=1.0, g=0.78, b=0.0, a=1.0)  # Maize

    ident_rot = Quaternion(x=0.0, y=0.0, z=0.0, w=1.0)

    # Body frame: +X is forward (nose), +Y is left wing, +Z is up (tail)
    fuselage = CubePrimitive(
        pose=Pose(position=Vector3(x=0.0, y=0.0, z=0.0), orientation=ident_rot),
        size=Vector3(x=2.2, y=0.35, z=0.35),
        color=white,
    )
    main_wing = CubePrimitive(
        pose=Pose(position=Vector3(x=0.2, y=0.0, z=0.18), orientation=ident_rot),
        size=Vector3(x=0.45, y=3.2, z=0.06),
        color=blue,
    )
    wing_tips = CubePrimitive(
        pose=Pose(position=Vector3(x=0.2, y=0.0, z=0.18), orientation=ident_rot),
        size=Vector3(x=0.46, y=3.25, z=0.08),
        color=maize,
    )
    tail_h = CubePrimitive(
        pose=Pose(position=Vector3(x=-0.9, y=0.0, z=0.1), orientation=ident_rot),
        size=Vector3(x=0.3, y=1.1, z=0.04),
        color=blue,
    )
    tail_v = CubePrimitive(
        pose=Pose(position=Vector3(x=-0.85, y=0.0, z=0.35), orientation=ident_rot),
        size=Vector3(x=0.35, y=0.04, z=0.55),
        color=maize,
    )
    propeller_hub = CubePrimitive(
        pose=Pose(position=Vector3(x=1.15, y=0.0, z=0.0), orientation=ident_rot),
        size=Vector3(x=0.12, y=0.22, z=0.22),
        color=maize,
    )

    entity = SceneEntity(
        timestamp=ts,
        frame_id="drone",
        id="cessna_fixed_wing",
        frame_locked=True,
        cubes=[fuselage, main_wing, wing_tips, tail_h, tail_v, propeller_hub],
    )
    return SceneUpdate(entities=[entity])


async def run_foxglove_telemetry_loop(drone: Any, port: int = 8765) -> None:
    """Continuously stream PX4 telemetry and 3D transforms to Foxglove Studio."""
    try:
        foxglove.start_server(port=port)
        print(f"Foxglove WebSocket server listening on ws://localhost:{port}")
    except Exception as error:
        print(f"Foxglove server already running or failed to bind port {port}: {error}")

    state = TelemetryState()

    async def update_pos_ned():
        async for pos_ned in drone.telemetry.subscribe_position_velocity_ned():
            state.north_m = pos_ned.position.north_m
            state.east_m = pos_ned.position.east_m
            state.down_m = pos_ned.position.down_m

    async def update_pos_gps():
        async for pos in drone.telemetry.subscribe_position():
            state.rel_alt_m = pos.relative_altitude_m
            state.abs_alt_m = pos.absolute_altitude_m
            state.latitude_deg = pos.latitude_deg
            state.longitude_deg = pos.longitude_deg

    async def update_attitude():
        async for euler in drone.telemetry.subscribe_attitude_euler():
            state.roll_deg = euler.roll_deg
            state.pitch_deg = euler.pitch_deg
            state.yaw_deg = euler.yaw_deg

    async def update_metrics():
        async for metrics in drone.telemetry.subscribe_fixedwing_metrics():
            state.airspeed_m_s = metrics.airspeed_m_s
            state.climb_rate_m_s = metrics.climb_rate_m_s
            state.throttle_pct = metrics.throttle_percentage * 100.0

    async def update_battery():
        async for b in drone.telemetry.subscribe_battery():
            state.voltage_v = b.voltage_v
            state.battery_pct = b.remaining_percent * 100.0

    async def update_in_air():
        async for in_air in drone.telemetry.subscribe_in_air():
            state.in_air = in_air

    async def update_flight_mode():
        async for mode in drone.telemetry.subscribe_flight_mode():
            state.flight_mode = str(mode)

    async def update_armed():
        async for armed in drone.telemetry.subscribe_armed():
            state.armed = armed

    # Launch telemetry listeners in the background
    listeners = [
        asyncio.create_task(update_pos_ned()),
        asyncio.create_task(update_pos_gps()),
        asyncio.create_task(update_attitude()),
        asyncio.create_task(update_metrics()),
        asyncio.create_task(update_battery()),
        asyncio.create_task(update_in_air()),
        asyncio.create_task(update_flight_mode()),
        asyncio.create_task(update_armed()),
    ]

    last_scene_publish = 0.0
    last_gps_publish = 0.0

    try:
        while True:
            now_sec = time.time()
            now_ns = int(now_sec * 1_000_000_000)
            ts = Timestamp(sec=now_ns // 1_000_000_000, nsec=now_ns % 1_000_000_000)

            # 1. Publish 3D Airplane Model to /scene periodically (every 2 seconds)
            if now_sec - last_scene_publish >= 2.0:
                foxglove.log("/scene", build_airplane_entity(ts))
                last_scene_publish = now_sec

            # 2. Publish 3D Transform to /tf (World -> Drone)
            # In ENU: X=East, Y=North, Z=Up
            x_enu = state.east_m
            y_enu = state.north_m
            z_enu = state.rel_alt_m if state.rel_alt_m > 0 else -state.down_m

            qx, qy, qz, qw = euler_ned_to_enu_quat(state.roll_deg, state.pitch_deg, state.yaw_deg)

            tf = FrameTransform(
                timestamp=ts,
                parent_frame_id="world",
                child_frame_id="drone",
                translation=Vector3(x=x_enu, y=y_enu, z=z_enu),
                rotation=Quaternion(x=qx, y=qy, z=qz, w=qw),
            )
            foxglove.log("/tf", tf)

            # 3. Publish GPS Fix to /gps (5 Hz)
            if now_sec - last_gps_publish >= 0.2:
                loc = LocationFix(
                    timestamp=ts,
                    frame_id="world",
                    latitude=state.latitude_deg,
                    longitude=state.longitude_deg,
                    altitude=state.abs_alt_m,
                )
                foxglove.log("/gps", loc)
                last_gps_publish = now_sec

            # 4. Publish Numeric Telemetry to /telemetry for Plotting
            telemetry_data = {
                "altitude_rel_m": round(state.rel_alt_m, 2),
                "altitude_abs_m": round(state.abs_alt_m, 2),
                "airspeed_m_s": round(state.airspeed_m_s, 2),
                "climb_rate_m_s": round(state.climb_rate_m_s, 2),
                "throttle_pct": round(state.throttle_pct, 1),
                "roll_deg": round(state.roll_deg, 2),
                "pitch_deg": round(state.pitch_deg, 2),
                "yaw_deg": round(state.yaw_deg, 2),
                "battery_pct": round(state.battery_pct, 1),
                "voltage_v": round(state.voltage_v, 2),
                "in_air": state.in_air,
                "armed": state.armed,
                "flight_mode": state.flight_mode,
            }
            foxglove.log("/telemetry", telemetry_data)

            # Run broadcast loop at 25 Hz
            await asyncio.sleep(0.04)

    except asyncio.CancelledError:
        pass
    finally:
        for task in listeners:
            task.cancel()


async def standalone_main():
    """Standalone launcher: connects directly to SITL on UDP 14540 and streams to Foxglove."""
    from mavsdk.asyncio import ComponentType, Configuration, Mavsdk, System
    from mavsdk.asyncio.plugins.action import ActionAsync
    from mavsdk.asyncio.plugins.mavlink_direct import MavlinkDirectAsync
    from mavsdk.asyncio.plugins.mission_raw import MissionRawAsync
    from mavsdk.asyncio.plugins.param import ParamAsync
    from mavsdk.asyncio.plugins.telemetry import TelemetryAsync

    print("Starting Foxglove Bridge standalone...")
    config = Configuration.create_with_component_type(ComponentType.GROUND_STATION)

    async with Mavsdk(config) as sdk:
        print("Connecting to PX4 SITL on udpin://0.0.0.0:14540...")
        await sdk.add_any_connection("udpin://0.0.0.0:14540")
        system = await sdk.first_autopilot(timeout_s=30.0)
        if system is None:
            print("Timed out waiting for PX4 autopilot. Is the SITL simulator running?")
            return

        class MinimalDrone:
            def __init__(self, sys):
                self.telemetry = TelemetryAsync(sys)

        drone = MinimalDrone(system)
        print("Connected to PX4! Streaming 3D transforms & telemetry to Foxglove Studio...")
        print("Open Foxglove Studio (or https://app.foxglove.dev) and connect to ws://localhost:8765")
        await run_foxglove_telemetry_loop(drone)


if __name__ == "__main__":
    try:
        asyncio.run(standalone_main())
    except KeyboardInterrupt:
        print("\nFoxglove bridge stopped.")

