"""Camera intrinsics, FrameSource abstraction, EXIF-geotagged capture writer, and Replay/Gazebo/Real sources.

Captures are stored as standard EXIF-geotagged JPEGs (consumable directly by OpenDroneMap) alongside
a compact manifest.jsonl holding full attitude and autopilot timestamps (MAST-L2-PER-08, PER-17).
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator, Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from typing import Any, Optional, Protocol
import urllib.request

import cv2
import numpy as np
import piexif


# ----- Camera Calibration & Config -----

@dataclass(frozen=True)
class CameraIntrinsics:
    """Pinhole + Brown-Conrady distortion model (MAST-L2-PER-01).

    Defaults match the SUB-PER 1/2.3" sensor + 6 mm lens scaled to 1280x960 (55.4 deg HFOV).
    """

    camera_id: str = "nadir_6mm"
    width: int = 1280
    height: int = 960
    fx: float = 1221.3
    fy: float = 1221.3
    cx: float = 640.0
    cy: float = 480.0
    dist_coeffs: tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0)

    @classmethod
    def from_hfov(
        cls,
        width: int,
        height: int,
        horizontal_fov_rad: float = 0.967,
        camera_id: str = "nadir_6mm",
        dist_coeffs: tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0),
    ) -> CameraIntrinsics:
        fx = (width * 0.5) / math.tan(horizontal_fov_rad * 0.5)
        return cls(
            camera_id=camera_id,
            width=int(width),
            height=int(height),
            fx=float(fx),
            fy=float(fx),
            cx=width * 0.5,
            cy=height * 0.5,
            dist_coeffs=tuple(float(c) for c in dist_coeffs),
        )

    @property
    def camera_matrix(self) -> np.ndarray:
        return np.array(
            [[self.fx, 0.0, self.cx], [0.0, self.fy, self.cy], [0.0, 0.0, 1.0]],
            dtype=np.float64,
        )

    @property
    def dist_array(self) -> np.ndarray:
        return np.array(self.dist_coeffs, dtype=np.float64)

    def undistort(self, image: np.ndarray) -> np.ndarray:
        if not any(abs(c) > 1e-12 for c in self.dist_coeffs):
            return image
        return cv2.undistort(image, self.camera_matrix, self.dist_array)

    def pixel_to_normalized(self, u: float, v: float) -> tuple[float, float]:
        """Undistort pixel (u, v) to normalized camera coordinates (x_n, y_n)."""
        if any(abs(c) > 1e-12 for c in self.dist_coeffs):
            pts = np.array([[[float(u), float(v)]]], dtype=np.float64)
            und = cv2.undistortPoints(pts, self.camera_matrix, self.dist_array)
            return float(und[0, 0, 0]), float(und[0, 0, 1])
        return (float(u) - self.cx) / self.fx, (float(v) - self.cy) / self.fy

    def to_dict(self) -> dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "width": self.width,
            "height": self.height,
            "fx": self.fx,
            "fy": self.fy,
            "cx": self.cx,
            "cy": self.cy,
            "dist_coeffs": list(self.dist_coeffs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CameraIntrinsics:
        if "fx" in data and "fy" in data:
            return cls(
                camera_id=str(data.get("camera_id", "nadir_6mm")),
                width=int(data.get("width", 1280)),
                height=int(data.get("height", 960)),
                fx=float(data["fx"]),
                fy=float(data["fy"]),
                cx=float(data.get("cx", int(data.get("width", 1280)) * 0.5)),
                cy=float(data.get("cy", int(data.get("height", 960)) * 0.5)),
                dist_coeffs=tuple(float(c) for c in data.get("dist_coeffs", (0.0, 0.0, 0.0, 0.0, 0.0))),
            )
        return cls.from_hfov(
            width=int(data.get("width", 1280)),
            height=int(data.get("height", 960)),
            horizontal_fov_rad=float(data.get("horizontal_fov_rad", 0.967)),
            camera_id=str(data.get("camera_id", "nadir_6mm")),
            dist_coeffs=tuple(float(c) for c in data.get("dist_coeffs", (0.0, 0.0, 0.0, 0.0, 0.0))),
        )


@dataclass
class CameraConfig:
    """Mission-level camera configuration enabling single-flag swap between SITL, Replay, and HITL."""

    source: str = "gazebo"  # "gazebo" | "replay" | "real" | "none"
    url: str = "http://127.0.0.1:8554/latest.jpg"
    device_index: int = 0
    replay_dir: Optional[str] = None
    capture_dir: str = "captures"
    rate_hz: float = 2.0
    world_scene: Optional[str] = "worlds/suas_site/scene.json"
    dem_path: Optional[str] = "worlds/suas_site/dem.npz"
    detector_weights: Optional[str] = None
    mapper_backend: str = "auto"  # "auto" | "odm" | "opencv"
    intrinsics: CameraIntrinsics = field(default_factory=lambda: CameraIntrinsics.from_hfov(1280, 960, 0.967))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "url": self.url,
            "device_index": self.device_index,
            "replay_dir": self.replay_dir,
            "capture_dir": self.capture_dir,
            "rate_hz": self.rate_hz,
            "world_scene": self.world_scene,
            "dem_path": self.dem_path,
            "detector_weights": self.detector_weights,
            "mapper_backend": self.mapper_backend,
            "intrinsics": self.intrinsics.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CameraConfig:
        intr_raw = data.get("intrinsics")
        intr = CameraIntrinsics.from_dict(intr_raw) if isinstance(intr_raw, dict) else CameraIntrinsics.from_hfov(1280, 960, 0.967)
        return cls(
            source=str(data.get("source", "gazebo")),
            url=str(data.get("url", "http://127.0.0.1:8554/latest.jpg")),
            device_index=int(data.get("device_index", 0)),
            replay_dir=data.get("replay_dir"),
            capture_dir=str(data.get("capture_dir", "captures")),
            rate_hz=float(data.get("rate_hz", 2.0)),
            world_scene=data.get("world_scene", "worlds/suas_site/scene.json"),
            dem_path=data.get("dem_path", "worlds/suas_site/dem.npz"),
            detector_weights=data.get("detector_weights"),
            mapper_backend=str(data.get("mapper_backend", "auto")),
            intrinsics=intr,
        )


# ----- Frame Contract -----

@dataclass(frozen=True)
class Frame:
    """Single captured image paired with synchronized aircraft pose and capture timestamp."""

    image: np.ndarray  # BGR uint8 HxWx3 (OpenCV convention)
    t_capture_us: int
    lat_deg: float
    lon_deg: float
    alt_amsl_m: float
    rel_alt_m: float
    roll_deg: float
    pitch_deg: float
    yaw_deg: float
    camera_id: str = "nadir_6mm"
    seq: int = 0

    def metadata_dict(self, filename: str) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "filename": filename,
            "t_capture_us": self.t_capture_us,
            "lat_deg": self.lat_deg,
            "lon_deg": self.lon_deg,
            "alt_amsl_m": self.alt_amsl_m,
            "rel_alt_m": self.rel_alt_m,
            "roll_deg": self.roll_deg,
            "pitch_deg": self.pitch_deg,
            "yaw_deg": self.yaw_deg,
            "camera_id": self.camera_id,
            "width": int(self.image.shape[1]),
            "height": int(self.image.shape[0]),
        }


class FrameSource(Protocol):
    """Uniform async camera interface shared across Gazebo SITL, Replay, and Hardware HITL."""

    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def frames(self) -> AsyncIterator[Frame]: ...


# ----- Standard EXIF GPS Helpers (OpenDroneMap-compatible) -----

def _deg_to_dms_rational(deg: float) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    abs_deg = abs(float(deg))
    d = int(abs_deg)
    rem_m = (abs_deg - d) * 60.0
    m = int(rem_m)
    s = (rem_m - m) * 60.0
    return ((d, 1), (m, 1), (int(round(s * 10000)), 10000))


def _dms_rational_to_deg(dms: Any, ref: bytes | str) -> float:
    d = dms[0][0] / dms[0][1]
    m = dms[1][0] / dms[1][1]
    s = dms[2][0] / dms[2][1]
    val = d + m / 60.0 + s / 3600.0
    ref_str = ref.decode("ascii", errors="ignore") if isinstance(ref, (bytes, bytearray)) else str(ref)
    if ref_str.upper() in ("S", "W"):
        val = -val
    return val


def build_exif_bytes(frame: Frame, intrinsics: Optional[CameraIntrinsics] = None) -> bytes:
    """Encode WGS-84 GPS EXIF tags so JPEGs are directly readable by OpenDroneMap / QGIS."""
    alt_ref = 0 if frame.alt_amsl_m >= 0.0 else 1
    alt_num = int(round(abs(frame.alt_amsl_m) * 1000))
    gps_ifd: dict[int, Any] = {
        piexif.GPSIFD.GPSVersionID: (2, 3, 0, 0),
        piexif.GPSIFD.GPSLatitudeRef: b"N" if frame.lat_deg >= 0.0 else b"S",
        piexif.GPSIFD.GPSLatitude: _deg_to_dms_rational(frame.lat_deg),
        piexif.GPSIFD.GPSLongitudeRef: b"E" if frame.lon_deg >= 0.0 else b"W",
        piexif.GPSIFD.GPSLongitude: _deg_to_dms_rational(frame.lon_deg),
        piexif.GPSIFD.GPSAltitudeRef: alt_ref,
        piexif.GPSIFD.GPSAltitude: (alt_num, 1000),
    }
    exif_ifd: dict[int, Any] = {}
    if intrinsics is not None:
        # Encode focal length (assuming 6.0 mm equivalent) and 35mm hint for photogrammetry priors
        exif_ifd[piexif.ExifIFD.FocalLength] = (600, 100)
    zeroth_ifd: dict[int, Any] = {
        piexif.ImageIFD.Make: b"M-AST",
        piexif.ImageIFD.Model: frame.camera_id.encode("ascii", errors="ignore"),
    }
    return piexif.dump({"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": gps_ifd})


def read_exif_gps(jpeg_path: Path) -> tuple[float, float, float]:
    """Read (lat_deg, lon_deg, alt_amsl_m) from a standard EXIF-geotagged JPEG."""
    exif = piexif.load(str(jpeg_path))
    gps = exif.get("GPS", {})
    if piexif.GPSIFD.GPSLatitude not in gps or piexif.GPSIFD.GPSLongitude not in gps:
        raise ValueError(f"Missing EXIF GPS tags in {jpeg_path}")
    lat = _dms_rational_to_deg(gps[piexif.GPSIFD.GPSLatitude], gps.get(piexif.GPSIFD.GPSLatitudeRef, b"N"))
    lon = _dms_rational_to_deg(gps[piexif.GPSIFD.GPSLongitude], gps.get(piexif.GPSIFD.GPSLongitudeRef, b"E"))
    alt = 0.0
    if piexif.GPSIFD.GPSAltitude in gps:
        num, den = gps[piexif.GPSIFD.GPSAltitude]
        alt = num / den if den else 0.0
        if gps.get(piexif.GPSIFD.GPSAltitudeRef, 0) == 1:
            alt = -alt
    return lat, lon, alt


# ----- On-Disk Capture Writer (MAST-L2-PER-17) -----

class CaptureWriter:
    """Writes EXIF-geotagged JPEGs + manifest.jsonl into a self-contained run directory."""

    def __init__(
        self,
        run_dir: str | Path,
        intrinsics: CameraIntrinsics,
        jpeg_quality: int = 92,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.images_dir = self.run_dir / "images"
        self.manifest_path = self.run_dir / "manifest.jsonl"
        self.intrinsics = intrinsics
        self.jpeg_quality = int(jpeg_quality)
        self.count = 0

        self.images_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "camera.json").write_text(
            json.dumps(self.intrinsics.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )

    def write(self, frame: Frame) -> Path:
        filename = f"frame_{self.count:05d}.jpg"
        out_path = self.images_dir / filename

        ok, encoded = cv2.imencode(
            ".jpg",
            frame.image,
            [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality],
        )
        if not ok:
            raise RuntimeError(f"Failed to JPEG-encode frame {self.count}")

        exif_bytes = build_exif_bytes(frame, self.intrinsics)
        out_path.write_bytes(encoded.tobytes())
        piexif.insert(exif_bytes, str(out_path))

        record = frame.metadata_dict(filename)
        with open(self.manifest_path, "a", encoding="utf-8") as mf:
            mf.write(json.dumps(record) + "\n")

        self.count += 1
        return out_path


# ----- ReplaySource (Manifest Folder OR Raw EXIF-Geotagged ODM Folder) -----

class ReplaySource:
    """Replays captured flights OR any public EXIF-geotagged drone survey folder (e.g. ODMdata)."""

    def __init__(
        self,
        capture_dir: str | Path,
        rate_hz: float = 0.0,
        default_rel_alt_m: float = 50.0,
    ) -> None:
        self.capture_dir = Path(capture_dir)
        self.rate_hz = float(rate_hz)
        self.default_rel_alt_m = float(default_rel_alt_m)
        self._running = False

    async def start(self) -> None:
        if not self.capture_dir.exists():
            raise FileNotFoundError(f"Replay directory not found: {self.capture_dir}")
        self._running = True

    async def stop(self) -> None:
        self._running = False

    def iter_frames_sync(self) -> list[Frame]:
        """Load frames synchronously (handy for offline evaluation, search, and mapper CLI)."""
        manifest = self.capture_dir / "manifest.jsonl"
        frames: list[Frame] = []
        if manifest.is_file():
            img_root = self.capture_dir / "images"
            if not img_root.is_dir():
                img_root = self.capture_dir
            with open(manifest, "r", encoding="utf-8") as mf:
                for line in mf:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    img_path = img_root / rec["filename"]
                    img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
                    if img is None:
                        continue
                    frames.append(
                        Frame(
                            image=img,
                            t_capture_us=int(rec["t_capture_us"]),
                            lat_deg=float(rec["lat_deg"]),
                            lon_deg=float(rec["lon_deg"]),
                            alt_amsl_m=float(rec["alt_amsl_m"]),
                            rel_alt_m=float(rec["rel_alt_m"]),
                            roll_deg=float(rec["roll_deg"]),
                            pitch_deg=float(rec["pitch_deg"]),
                            yaw_deg=float(rec["yaw_deg"]),
                            camera_id=str(rec.get("camera_id", "nadir_6mm")),
                            seq=int(rec.get("seq", len(frames))),
                        )
                    )
            return frames

        # Fallback: standard EXIF-geotagged JPEG directory (e.g. ODMdata or raw camera SD card)
        search_root = self.capture_dir / "images" if (self.capture_dir / "images").is_dir() else self.capture_dir
        jpgs = sorted(
            p for p in search_root.iterdir()
            if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg")
        )
        for seq, jpg_path in enumerate(jpgs):
            img = cv2.imread(str(jpg_path), cv2.IMREAD_COLOR)
            if img is None:
                continue
            lat, lon, alt = read_exif_gps(jpg_path)
            frames.append(
                Frame(
                    image=img,
                    t_capture_us=seq * 500_000,
                    lat_deg=lat,
                    lon_deg=lon,
                    alt_amsl_m=alt,
                    rel_alt_m=self.default_rel_alt_m,
                    roll_deg=0.0,
                    pitch_deg=0.0,
                    yaw_deg=0.0,
                    camera_id="exif_replay",
                    seq=seq,
                )
            )
        return frames

    async def frames(self) -> AsyncIterator[Frame]:
        delay = (1.0 / self.rate_hz) if self.rate_hz > 0.0 else 0.0
        for frame in self.iter_frames_sync():
            if not self._running:
                break
            yield frame
            if delay > 0.0:
                await asyncio.sleep(delay)


# ----- Telemetry Buffer for Synchronized Pose Tagging -----

@dataclass
class _PoseSample:
    t_wall_s: float
    lat_deg: float
    lon_deg: float
    alt_amsl_m: float
    rel_alt_m: float
    roll_deg: float
    pitch_deg: float
    yaw_deg: float


class TelemetryPoseTracker:
    """Subscribes to MAVSDK telemetry and maintains a rolling pose buffer."""

    def __init__(self, drone: Any, maxlen: int = 200) -> None:
        self._drone = drone
        self._samples: deque[_PoseSample] = deque(maxlen=maxlen)
        self._lat = 47.397971057728974
        self._lon = 8.546163739800146
        self._alt_amsl = 0.0
        self._rel_alt = 0.0
        self._roll = 0.0
        self._pitch = 0.0
        self._yaw = 0.0
        self._tasks: list[asyncio.Task] = []

    def _record(self) -> None:
        self._samples.append(
            _PoseSample(
                t_wall_s=time.monotonic(),
                lat_deg=self._lat,
                lon_deg=self._lon,
                alt_amsl_m=self._alt_amsl,
                rel_alt_m=self._rel_alt,
                roll_deg=self._roll,
                pitch_deg=self._pitch,
                yaw_deg=self._yaw,
            )
        )

    async def start(self) -> None:
        if self._drone is None or not hasattr(self._drone, "telemetry"):
            return

        async def watch_pos() -> None:
            async for pos in self._drone.telemetry.subscribe_position():
                self._lat = float(pos.latitude_deg)
                self._lon = float(pos.longitude_deg)
                self._alt_amsl = float(pos.absolute_altitude_m)
                self._rel_alt = float(pos.relative_altitude_m)
                self._record()

        async def watch_att() -> None:
            async for euler in self._drone.telemetry.subscribe_attitude_euler():
                self._roll = float(euler.roll_deg)
                self._pitch = float(euler.pitch_deg)
                self._yaw = float(euler.yaw_deg)
                self._record()

        self._tasks = [
            asyncio.create_task(watch_pos()),
            asyncio.create_task(watch_att()),
        ]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []

    def sample_at(self, t_wall_s: float) -> _PoseSample:
        """Return pose linearly interpolated to t_wall_s (or latest if out of range)."""
        if not self._samples:
            return _PoseSample(
                t_wall_s=t_wall_s,
                lat_deg=self._lat,
                lon_deg=self._lon,
                alt_amsl_m=self._alt_amsl,
                rel_alt_m=self._rel_alt,
                roll_deg=self._roll,
                pitch_deg=self._pitch,
                yaw_deg=self._yaw,
            )
        if t_wall_s <= self._samples[0].t_wall_s:
            return self._samples[0]
        if t_wall_s >= self._samples[-1].t_wall_s:
            return self._samples[-1]

        prev = self._samples[0]
        for cur in self._samples:
            if cur.t_wall_s >= t_wall_s:
                dt = cur.t_wall_s - prev.t_wall_s
                if dt <= 1e-6:
                    return cur
                alpha = (t_wall_s - prev.t_wall_s) / dt
                # Shortest-angle interpolation for yaw
                dyaw = ((cur.yaw_deg - prev.yaw_deg + 180.0) % 360.0) - 180.0
                return _PoseSample(
                    t_wall_s=t_wall_s,
                    lat_deg=prev.lat_deg + alpha * (cur.lat_deg - prev.lat_deg),
                    lon_deg=prev.lon_deg + alpha * (cur.lon_deg - prev.lon_deg),
                    alt_amsl_m=prev.alt_amsl_m + alpha * (cur.alt_amsl_m - prev.alt_amsl_m),
                    rel_alt_m=prev.rel_alt_m + alpha * (cur.rel_alt_m - prev.rel_alt_m),
                    roll_deg=prev.roll_deg + alpha * (cur.roll_deg - prev.roll_deg),
                    pitch_deg=prev.pitch_deg + alpha * (cur.pitch_deg - prev.pitch_deg),
                    yaw_deg=(prev.yaw_deg + alpha * dyaw) % 360.0,
                )
            prev = cur
        return self._samples[-1]


# ----- GazeboCameraSource (SITL) -----

class GazeboCameraSource:
    """Polls Gazebo's HTTP camera relay (sim/gz/camera_relay.py) and pairs frames with PX4 pose."""

    def __init__(
        self,
        drone: Any,
        url: str = "http://127.0.0.1:8554/latest.jpg",
        rate_hz: float = 2.0,
        camera_id: str = "nadir_6mm",
        timeout_s: float = 2.0,
    ) -> None:
        self.url = url
        self.rate_hz = float(rate_hz)
        self.camera_id = camera_id
        self.timeout_s = float(timeout_s)
        self._pose_tracker = TelemetryPoseTracker(drone)
        self._running = False
        self._last_seq = -1

    async def start(self) -> None:
        self._running = True
        await self._pose_tracker.start()

    async def stop(self) -> None:
        self._running = False
        await self._pose_tracker.stop()

    def _fetch_latest(self) -> Optional[tuple[np.ndarray, int, int]]:
        try:
            with urllib.request.urlopen(self.url, timeout=self.timeout_s) as resp:
                if resp.status != 200:
                    return None
                data = resp.read()
                sim_us = int(resp.headers.get("X-Sim-Timestamp-Us", int(time.time() * 1_000_000)))
                seq = int(resp.headers.get("X-Frame-Seq", "0"))
        except Exception:
            return None

        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        return img, sim_us, seq

    async def frames(self) -> AsyncIterator[Frame]:
        period = 1.0 / max(0.1, self.rate_hz)
        while self._running:
            t_req = time.monotonic()
            result = await asyncio.to_thread(self._fetch_latest)
            if result is not None:
                img, sim_us, seq = result
                if seq != self._last_seq:
                    self._last_seq = seq
                    pose = self._pose_tracker.sample_at(t_req)
                    yield Frame(
                        image=img,
                        t_capture_us=sim_us,
                        lat_deg=pose.lat_deg,
                        lon_deg=pose.lon_deg,
                        alt_amsl_m=pose.alt_amsl_m,
                        rel_alt_m=pose.rel_alt_m,
                        roll_deg=pose.roll_deg,
                        pitch_deg=pose.pitch_deg,
                        yaw_deg=pose.yaw_deg,
                        camera_id=self.camera_id,
                        seq=seq,
                    )
            elapsed = time.monotonic() - t_req
            await asyncio.sleep(max(0.02, period - elapsed))


# ----- RealCameraSource (HITL / Hardware Plug-in Point) -----

class RealCameraSource:
    """Hardware camera source using OpenCV VideoCapture (USB/V4L2/RTSP) paired with PX4 pose.

    Phase 4 upgrades timestamping to hardware trigger / MAVLink CAMERA_IMAGE_CAPTURED sync
    (MAST-L2-PER-08) without changing this interface or any downstream code.
    """

    def __init__(
        self,
        drone: Any,
        source: int | str = 0,
        rate_hz: float = 2.0,
        camera_id: str = "real_nadir",
    ) -> None:
        self._source = source
        self.rate_hz = float(rate_hz)
        self.camera_id = camera_id
        self._pose_tracker = TelemetryPoseTracker(drone)
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._seq = 0

    async def start(self) -> None:
        self._cap = cv2.VideoCapture(self._source)
        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open real camera source: {self._source}")
        self._running = True
        await self._pose_tracker.start()

    async def stop(self) -> None:
        self._running = False
        await self._pose_tracker.stop()
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    async def frames(self) -> AsyncIterator[Frame]:
        period = 1.0 / max(0.1, self.rate_hz)
        while self._running and self._cap is not None:
            t_req = time.monotonic()
            ok, img = await asyncio.to_thread(self._cap.read)
            if ok and img is not None:
                pose = self._pose_tracker.sample_at(t_req)
                self._seq += 1
                yield Frame(
                    image=img,
                    t_capture_us=int(time.time() * 1_000_000),
                    lat_deg=pose.lat_deg,
                    lon_deg=pose.lon_deg,
                    alt_amsl_m=pose.alt_amsl_m,
                    rel_alt_m=pose.rel_alt_m,
                    roll_deg=pose.roll_deg,
                    pitch_deg=pose.pitch_deg,
                    yaw_deg=pose.yaw_deg,
                    camera_id=self.camera_id,
                    seq=self._seq,
                )
            elapsed = time.monotonic() - t_req
            await asyncio.sleep(max(0.01, period - elapsed))


def create_frame_source(config: CameraConfig, drone: Any = None) -> Optional[FrameSource]:
    """Instantiate the configured FrameSource (gazebo | replay | real | none)."""
    mode = config.source.lower()
    if mode in ("none", "off", "disabled"):
        return None
    if mode == "gazebo":
        return GazeboCameraSource(
            drone=drone,
            url=config.url,
            rate_hz=config.rate_hz,
            camera_id=config.intrinsics.camera_id,
        )
    if mode == "replay":
        if not config.replay_dir:
            raise ValueError("camera.replay_dir must be set when camera.source == 'replay'")
        return ReplaySource(config.replay_dir, rate_hz=config.rate_hz)
    if mode == "real":
        src: int | str = config.url if config.url.startswith(("rtsp://", "http://", "/dev/")) else config.device_index
        return RealCameraSource(
            drone=drone,
            source=src,
            rate_hz=config.rate_hz,
            camera_id=config.intrinsics.camera_id,
        )
    raise ValueError(f"Unsupported camera.source: {config.source!r}")


# ----- Background Capture Session for MissionRunner -----

class CaptureSession:
    """Runs a FrameSource in the background during SURVEY, writing EXIF JPEGs and notifying hooks."""

    def __init__(
        self,
        source: FrameSource,
        intrinsics: CameraIntrinsics,
        capture_root: str | Path = "captures",
        run_name: str = "survey",
        on_frame: Optional[Callable[[Frame], None]] = None,
    ) -> None:
        self.source = source
        self.intrinsics = intrinsics
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path(capture_root) / f"{run_name}_{stamp}"
        self.writer = CaptureWriter(self.run_dir, intrinsics=intrinsics)
        self.on_frame = on_frame
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> Path:
        await self.source.start()

        async def _loop() -> None:
            async for frame in self.source.frames():
                self.writer.write(frame)
                if self.on_frame is not None:
                    try:
                        self.on_frame(frame)
                    except Exception:
                        pass

        self._task = asyncio.create_task(_loop())
        return self.run_dir

    async def stop(self) -> Path:
        await self.source.stop()
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        return self.run_dir
