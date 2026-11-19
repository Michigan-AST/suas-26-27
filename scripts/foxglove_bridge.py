#!/usr/bin/env python3
"""Foxglove Studio bridge: streams PX4 telemetry and 3D transforms to Foxglove Studio."""

from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path
import time
from dataclasses import dataclass
from typing import Any, Optional

import cv2
import foxglove
from foxglove.schemas import (
    CameraCalibration,
    Color,
    CompressedImage,
    CubePrimitive,
    CylinderPrimitive,
    FrameTransform,
    LinePrimitive,
    LinePrimitiveLineType,
    LocationFix,
    Point3,
    Pose,
    Quaternion,
    SceneEntity,
    SceneUpdate,
    SpherePrimitive,
    Timestamp,
    TriangleListPrimitive,
    Vector3,
)
import numpy as np


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


def build_site_scene_update(
    scene_path: str | Path = "worlds/suas_site/scene.json",
    dem_path: Optional[str | Path] = "worlds/suas_site/dem.npz",
    ts: Optional[Timestamp] = None,
) -> Optional[SceneUpdate]:
    """Build Foxglove /scene entities for terrain, Search Boundary, trees, and ground-truth targets."""
    sp = Path(scene_path)
    if not sp.is_file():
        return None
    scene = json.loads(sp.read_text(encoding="utf-8"))
    if ts is None:
        ts = Timestamp(sec=int(time.time()), nsec=0)

    ident_rot = Quaternion(x=0.0, y=0.0, z=0.0, w=1.0)
    ident_pose = Pose(position=Vector3(x=0.0, y=0.0, z=0.0), orientation=ident_rot)
    entities: list[SceneEntity] = []

    # 1. Search Boundary outline (+ 15 m buffer) in world ENU (x=east, y=north, z=up)
    sb = scene.get("search_boundary")
    if sb:
        min_n, max_n = float(sb["min_north"]), float(sb["max_north"])
        min_e, max_e = float(sb["min_east"]), float(sb["max_east"])
        buf = float(sb.get("buffer_m", 15.0))
        lines = [
            LinePrimitive(
                type=LinePrimitiveLineType.LineLoop,
                pose=ident_pose,
                thickness=1.2,
                scale_invariant=False,
                points=[
                    Point3(x=min_e, y=min_n, z=0.5),
                    Point3(x=max_e, y=min_n, z=0.5),
                    Point3(x=max_e, y=max_n, z=0.5),
                    Point3(x=min_e, y=max_n, z=0.5),
                ],
                color=Color(r=1.0, g=0.82, b=0.0, a=0.95),
            ),
            LinePrimitive(
                type=LinePrimitiveLineType.LineLoop,
                pose=ident_pose,
                thickness=0.6,
                scale_invariant=False,
                points=[
                    Point3(x=min_e - buf, y=min_n - buf, z=0.4),
                    Point3(x=max_e + buf, y=min_n - buf, z=0.4),
                    Point3(x=max_e + buf, y=max_n + buf, z=0.4),
                    Point3(x=min_e - buf, y=max_n + buf, z=0.4),
                ],
                color=Color(r=1.0, g=0.50, b=0.0, a=0.65),
            ),
        ]
        entities.append(
            SceneEntity(
                timestamp=ts,
                frame_id="world",
                id="search_boundary",
                frame_locked=True,
                lines=lines,
            )
        )

    # 2. Terrain mesh from DEM (downsampled for lightweight WebSocket updates)
    dp = Path(dem_path) if dem_path else None
    if dp and dp.is_file() and dp.suffix.lower() == ".npz":
        data = np.load(dp)
        north_axis = data["north_axis"]
        east_axis = data["east_axis"]
        elev = data["elevation_m"]
        stride = max(1, len(north_axis) // 32)
        na = north_axis[::stride]
        ea = east_axis[::stride]
        zz = elev[::stride, ::stride]
        z_min = float(zz.min())
        z_span = max(1.0, float(zz.max()) - z_min)
        tri_pts: list[Point3] = []
        tri_cols: list[Color] = []

        def elev_color(z_val: float) -> Color:
            t = (z_val - z_min) / z_span
            # Dry sandy field (matches worlds/suas_site ground texture)
            return Color(r=0.42 + 0.22 * t, g=0.38 + 0.18 * t, b=0.28 + 0.12 * t, a=0.85)

        for i in range(len(na) - 1):
            for j in range(len(ea) - 1):
                p00 = Point3(x=float(ea[j]), y=float(na[i]), z=float(zz[i, j]))
                p10 = Point3(x=float(ea[j]), y=float(na[i + 1]), z=float(zz[i + 1, j]))
                p01 = Point3(x=float(ea[j + 1]), y=float(na[i]), z=float(zz[i, j + 1]))
                p11 = Point3(x=float(ea[j + 1]), y=float(na[i + 1]), z=float(zz[i + 1, j + 1]))
                c00, c10 = elev_color(float(zz[i, j])), elev_color(float(zz[i + 1, j]))
                c01, c11 = elev_color(float(zz[i, j + 1])), elev_color(float(zz[i + 1, j + 1]))
                tri_pts.extend([p00, p01, p11, p00, p11, p10])
                tri_cols.extend([c00, c01, c11, c00, c11, c10])

        entities.append(
            SceneEntity(
                timestamp=ts,
                frame_id="world",
                id="site_terrain",
                frame_locked=True,
                triangles=[TriangleListPrimitive(pose=ident_pose, points=tri_pts, colors=tri_cols)],
            )
        )

    # 3. Ground-truth targets and trees/debris
    cubes: list[CubePrimitive] = []
    cylinders: list[CylinderPrimitive] = []
    spheres: list[SpherePrimitive] = []

    for target in scene.get("targets", []):
        x, y, z = float(target["east_m"]), float(target["north_m"]), float(target.get("elevation_m", 0.0))
        if target["label"] == "tent":
            cubes.append(
                CubePrimitive(
                    pose=Pose(position=Vector3(x=x, y=y, z=z + target["height_m"] * 0.5), orientation=ident_rot),
                    size=Vector3(x=float(target["width_m"]), y=float(target["length_m"]), z=float(target["height_m"])),
                    color=Color(r=0.08, g=0.30, b=0.92, a=0.95),
                )
            )
        else:
            cubes.append(
                CubePrimitive(
                    pose=Pose(position=Vector3(x=x, y=y, z=z + 0.25), orientation=ident_rot),
                    size=Vector3(x=float(target["width_m"]) + 0.5, y=float(target["length_m"]) + 0.3, z=0.5),
                    color=Color(r=0.94, g=0.22, b=0.10, a=0.95),
                )
            )

    for obj in scene.get("objects", []):
        x, y = float(obj["east_m"]), float(obj["north_m"])
        if obj["kind"] == "tree":
            r, h = float(obj["radius_m"]), float(obj["height_m"])
            cylinders.append(
                CylinderPrimitive(
                    pose=Pose(position=Vector3(x=x, y=y, z=h * 0.225), orientation=ident_rot),
                    size=Vector3(x=0.6, y=0.6, z=h * 0.45),
                    bottom_scale=1.0,
                    top_scale=0.8,
                    color=Color(r=0.35, g=0.22, b=0.12, a=1.0),
                )
            )
            spheres.append(
                SpherePrimitive(
                    pose=Pose(position=Vector3(x=x, y=y, z=h * 0.45 + r * 0.65), orientation=ident_rot),
                    size=Vector3(x=r * 2.0, y=r * 2.0, z=r * 1.8),
                    color=Color(r=0.16, g=0.38, b=0.14, a=0.9),
                )
            )
        else:
            h = float(obj["height_m"])
            cubes.append(
                CubePrimitive(
                    pose=Pose(position=Vector3(x=x, y=y, z=h * 0.5), orientation=ident_rot),
                    size=Vector3(x=float(obj["length_m"]), y=float(obj["width_m"]), z=h),
                    color=Color(r=0.55, g=0.52, b=0.45, a=0.9),
                )
            )

    if cubes or cylinders or spheres:
        entities.append(
            SceneEntity(
                timestamp=ts,
                frame_id="world",
                id="site_objects",
                frame_locked=True,
                cubes=cubes,
                cylinders=cylinders,
                spheres=spheres,
            )
        )

    return SceneUpdate(entities=entities)


def _now_ts() -> Timestamp:
    now_ns = int(time.time() * 1_000_000_000)
    return Timestamp(sec=now_ns // 1_000_000_000, nsec=now_ns % 1_000_000_000)


def _safe_log(topic: str, msg: Any) -> None:
    """Best-effort Foxglove publish (no-op if server not running / import path only)."""
    try:
        foxglove.log(topic, msg)
    except Exception:
        pass


# Accumulated mission visualization state (ENU: x=east, y=north, z=up)
_FLOWN_TRACK: list[Point3] = []
_FOOTPRINT_LINES: list[LinePrimitive] = []
_LAST_FOOTPRINT_PUB = 0.0
_MAX_FLOWN_POINTS = 4000
_MAX_FOOTPRINTS = 200


def publish_camera_frame(frame: Any, intrinsics: Optional[Any] = None, jpeg_quality: int = 80) -> None:
    """Publish a live or replayed camera frame + calibration to Foxglove (/camera/image)."""
    ok, encoded = cv2.imencode(".jpg", frame.image, [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)])
    if not ok:
        return

    ts = _now_ts()
    _safe_log(
        "/camera/image",
        CompressedImage(
            timestamp=ts,
            frame_id="nadir_camera",
            data=encoded.tobytes(),
            format="jpeg",
        ),
    )
    if intrinsics is not None:
        fx, fy, cx, cy = float(intrinsics.fx), float(intrinsics.fy), float(intrinsics.cx), float(intrinsics.cy)
        _safe_log(
            "/camera/camera_info",
            CameraCalibration(
                timestamp=ts,
                frame_id="nadir_camera",
                width=int(intrinsics.width),
                height=int(intrinsics.height),
                distortion_model="plumb_bob",
                D=list(intrinsics.dist_coeffs),
                K=[fx, 0.0, cx, 0.0, fy, cy, 0.0, 0.0, 1.0],
                R=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
                P=[fx, 0.0, cx, 0.0, 0.0, fy, cy, 0.0, 0.0, 0.0, 1.0, 0.0],
            ),
        )


def publish_mission_status(status: dict[str, Any]) -> None:
    """Publish unambiguous mission phase / laps / battery (MAST-L2-ASW-19)."""
    payload = {
        "phase": str(status.get("phase", "UNKNOWN")),
        "completed_laps": int(status.get("completed_laps", 0)),
        "target_laps": int(status.get("target_laps", 0)),
        "lap_locked": bool(status.get("lap_locked", False)),
        "battery_pct": float(status.get("battery_pct", 0.0)),
        "current_waypoint_index": int(status.get("current_waypoint_index", 0)),
        "abort_requested": bool(status.get("abort_requested", False)),
        "abort_reason": status.get("abort_reason"),
    }
    _safe_log("/mission", payload)


def publish_ned_path(
    entity_id: str,
    waypoints_ne: list[tuple[float, float, float]] | list[Any],
    *,
    color: Color,
    thickness: float = 2.0,
    z_offset_m: float = 1.0,
) -> None:
    """Publish a path of (north, east[, height]) waypoints as a /scene line strip."""
    if not waypoints_ne:
        return
    pts: list[Point3] = []
    for wp in waypoints_ne:
        if hasattr(wp, "north"):
            n, e, h = float(wp.north), float(wp.east), float(getattr(wp, "height", 50.0))
        else:
            n, e = float(wp[0]), float(wp[1])
            h = float(wp[2]) if len(wp) > 2 else 50.0
        pts.append(Point3(x=e, y=n, z=h + z_offset_m))
    if len(pts) < 2:
        return
    ident = Pose(position=Vector3(x=0.0, y=0.0, z=0.0), orientation=Quaternion(x=0.0, y=0.0, z=0.0, w=1.0))
    _safe_log(
        "/scene",
        SceneUpdate(
            entities=[
                SceneEntity(
                    timestamp=_now_ts(),
                    frame_id="world",
                    id=entity_id,
                    frame_locked=True,
                    lines=[
                        LinePrimitive(
                            type=LinePrimitiveLineType.LineStrip,
                            pose=ident,
                            thickness=thickness,
                            scale_invariant=False,
                            points=pts,
                            color=color,
                        )
                    ],
                )
            ]
        ),
    )


def append_flown_track(north_m: float, east_m: float, alt_m: float = 50.0) -> None:
    """Append a flown sample and republish the track polyline."""
    global _FLOWN_TRACK
    _FLOWN_TRACK.append(Point3(x=float(east_m), y=float(north_m), z=float(alt_m)))
    if len(_FLOWN_TRACK) > _MAX_FLOWN_POINTS:
        _FLOWN_TRACK = _FLOWN_TRACK[-_MAX_FLOWN_POINTS:]
    if len(_FLOWN_TRACK) < 2:
        return
    ident = Pose(position=Vector3(x=0.0, y=0.0, z=0.0), orientation=Quaternion(x=0.0, y=0.0, z=0.0, w=1.0))
    _safe_log(
        "/scene",
        SceneUpdate(
            entities=[
                SceneEntity(
                    timestamp=_now_ts(),
                    frame_id="world",
                    id="flown_track",
                    frame_locked=True,
                    lines=[
                        LinePrimitive(
                            type=LinePrimitiveLineType.LineStrip,
                            pose=ident,
                            thickness=1.4,
                            scale_invariant=False,
                            points=list(_FLOWN_TRACK),
                            color=Color(r=0.15, g=0.75, b=1.0, a=0.95),
                        )
                    ],
                )
            ]
        ),
    )


def publish_capture_footprint(corners_ne: list[tuple[float, float]], *, force: bool = False) -> None:
    """Accumulate a frame ground footprint (N/E corners) and publish coverage outlines."""
    global _FOOTPRINT_LINES, _LAST_FOOTPRINT_PUB
    if len(corners_ne) < 3:
        return
    ident = Pose(position=Vector3(x=0.0, y=0.0, z=0.0), orientation=Quaternion(x=0.0, y=0.0, z=0.0, w=1.0))
    pts = [Point3(x=float(e), y=float(n), z=0.3) for n, e in corners_ne]
    _FOOTPRINT_LINES.append(
        LinePrimitive(
            type=LinePrimitiveLineType.LineLoop,
            pose=ident,
            thickness=0.35,
            scale_invariant=False,
            points=pts,
            color=Color(r=0.2, g=0.95, b=0.55, a=0.55),
        )
    )
    if len(_FOOTPRINT_LINES) > _MAX_FOOTPRINTS:
        _FOOTPRINT_LINES = _FOOTPRINT_LINES[-_MAX_FOOTPRINTS:]
    now = time.time()
    if not force and (now - _LAST_FOOTPRINT_PUB) < 0.5:
        return
    _LAST_FOOTPRINT_PUB = now
    _safe_log(
        "/scene",
        SceneUpdate(
            entities=[
                SceneEntity(
                    timestamp=_now_ts(),
                    frame_id="world",
                    id="capture_footprints",
                    frame_locked=True,
                    lines=list(_FOOTPRINT_LINES),
                )
            ]
        ),
    )


def publish_declared_targets(targets: list[Any]) -> None:
    """Publish SEARCH-declared targets (distinct from scene.json ground-truth markers)."""
    cubes: list[CubePrimitive] = []
    spheres: list[SpherePrimitive] = []
    ident_rot = Quaternion(x=0.0, y=0.0, z=0.0, w=1.0)
    for t in targets:
        label = str(getattr(t, "label", "target"))
        n = float(getattr(t, "north_m", 0.0))
        e = float(getattr(t, "east_m", 0.0))
        if label == "tent":
            cubes.append(
                CubePrimitive(
                    pose=Pose(position=Vector3(x=e, y=n, z=2.5), orientation=ident_rot),
                    size=Vector3(x=4.0, y=4.0, z=3.0),
                    color=Color(r=0.15, g=0.85, b=1.0, a=0.85),
                )
            )
        else:
            spheres.append(
                SpherePrimitive(
                    pose=Pose(position=Vector3(x=e, y=n, z=1.5), orientation=ident_rot),
                    size=Vector3(x=2.5, y=2.5, z=2.5),
                    color=Color(r=1.0, g=0.85, b=0.1, a=0.9),
                )
            )
    _safe_log(
        "/scene",
        SceneUpdate(
            entities=[
                SceneEntity(
                    timestamp=_now_ts(),
                    frame_id="world",
                    id="declared_targets",
                    frame_locked=True,
                    cubes=cubes,
                    spheres=spheres,
                )
            ]
        ),
    )
    _safe_log(
        "/targets/declared",
        {
            "count": len(targets),
            "targets": [
                {
                    "label": str(getattr(t, "label", "")),
                    "north_m": float(getattr(t, "north_m", 0.0)),
                    "east_m": float(getattr(t, "east_m", 0.0)),
                    "confidence": float(getattr(t, "confidence", 0.0)),
                    "observations": int(getattr(t, "observations", 0)),
                }
                for t in targets
            ],
        },
    )


def publish_orthomosaic(map_path: str | Path, jpeg_quality: int = 85) -> bool:
    """Publish a completed risk-map PNG/JPEG to /map/orthomosaic for the Image panel."""
    path = Path(map_path)
    if not path.is_file():
        return False
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        return False
    # Downscale huge orthos so Foxglove stays responsive
    h, w = img.shape[:2]
    max_dim = 1600
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)])
    if not ok:
        return False
    _safe_log(
        "/map/orthomosaic",
        CompressedImage(
            timestamp=_now_ts(),
            frame_id="map",
            data=encoded.tobytes(),
            format="jpeg",
        ),
    )
    _safe_log("/map/status", {"path": str(path), "ready": True, "width": int(img.shape[1]), "height": int(img.shape[0])})
    return True


def watch_orthomosaic_file(map_path: str | Path, poll_s: float = 2.0, timeout_s: float = 600.0) -> None:
    """Background helper: wait for mapper output and publish it once."""
    path = Path(map_path)
    deadline = time.time() + timeout_s
    last_mtime = -1.0
    while time.time() < deadline:
        if path.is_file():
            mtime = path.stat().st_mtime
            if mtime != last_mtime and path.stat().st_size > 0:
                if publish_orthomosaic(path):
                    print(f"Foxglove: published orthomosaic from {path}")
                    return
                last_mtime = mtime
        time.sleep(poll_s)


async def run_foxglove_telemetry_loop(
    drone: Any,
    port: int = 8765,
    scene_path: Optional[str | Path] = None,
    dem_path: Optional[str | Path] = None,
) -> None:
    """Continuously stream PX4 telemetry and 3D transforms to Foxglove Studio."""
    try:
        foxglove.start_server(port=port)
        print(f"Foxglove WebSocket server listening on ws://localhost:{port}")
    except Exception as error:
        print(f"Foxglove server already running or failed to bind port {port}: {error}")

    repo_root = Path(__file__).resolve().parents[1]
    resolved_scene = Path(scene_path) if scene_path else (repo_root / "worlds" / "suas_site" / "scene.json")
    resolved_dem = Path(dem_path) if dem_path else (repo_root / "worlds" / "suas_site" / "dem.npz")

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
    last_track_sample = 0.0

    try:
        while True:
            now_sec = time.time()
            now_ns = int(now_sec * 1_000_000_000)
            ts = Timestamp(sec=now_ns // 1_000_000_000, nsec=now_ns % 1_000_000_000)

            # 1. Publish 3D Airplane Model + site terrain/targets to /scene periodically (every 2 seconds)
            if now_sec - last_scene_publish >= 2.0:
                foxglove.log("/scene", build_airplane_entity(ts))
                site_update = build_site_scene_update(resolved_scene, resolved_dem, ts)
                if site_update is not None:
                    foxglove.log("/scene", site_update)
                last_scene_publish = now_sec

            # 1b. Flown track breadcrumb (~2 Hz)
            if now_sec - last_track_sample >= 0.5 and (abs(state.north_m) + abs(state.east_m)) > 0.01:
                append_flown_track(state.north_m, state.east_m, max(1.0, state.rel_alt_m))
                last_track_sample = now_sec

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

