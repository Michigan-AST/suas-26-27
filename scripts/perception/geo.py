"""Geospatial transforms, DEM elevation queries, and pixel-to-ground ray projection.

Uses pyproj for WGS-84 <-> local ENU/NED projections (no flat-Earth duplication) and supports
both regular .npz DEM grids (generated for SITL) and GeoTIFF DEMs (when rasterio is installed).
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import numpy as np
from pyproj import CRS, Transformer

if TYPE_CHECKING:
    from .camera import CameraIntrinsics, Frame


class LocalProjection:
    """Accurate WGS-84 <-> local North/East (metres) conversion around a site origin."""

    def __init__(self, origin_lat_deg: float, origin_lon_deg: float, origin_alt_amsl_m: float = 0.0) -> None:
        self.origin_lat_deg = float(origin_lat_deg)
        self.origin_lon_deg = float(origin_lon_deg)
        self.origin_alt_amsl_m = float(origin_alt_amsl_m)

        wgs84 = CRS.from_epsg(4326)
        local_aeqd = CRS.from_proj4(
            f"+proj=aeqd +lat_0={self.origin_lat_deg:.10f} +lon_0={self.origin_lon_deg:.10f} "
            "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
        )
        self._to_local = Transformer.from_crs(wgs84, local_aeqd, always_xy=True)
        self._to_wgs84 = Transformer.from_crs(local_aeqd, wgs84, always_xy=True)

    def gps_to_ne(self, lat_deg: float, lon_deg: float) -> tuple[float, float]:
        """Convert (lat, lon) in degrees to (north_m, east_m) relative to origin."""
        east_m, north_m = self._to_local.transform(float(lon_deg), float(lat_deg))
        return float(north_m), float(east_m)

    def ne_to_gps(self, north_m: float, east_m: float) -> tuple[float, float]:
        """Convert (north_m, east_m) relative to origin to (lat_deg, lon_deg)."""
        lon_deg, lat_deg = self._to_wgs84.transform(float(east_m), float(north_m))
        return float(lat_deg), float(lon_deg)


class DemGrid:
    """Terrain elevation lookup (metres above site origin) with bilinear interpolation.

    Supports:
      - Flat terrain fallback (elevation = 0.0 everywhere)
      - Local .npz grids written by worlds/suas_site/build_site.py
      - Optional GeoTIFF (.tif/.tiff) when rasterio is installed
    """

    def __init__(
        self,
        north_axis: Optional[np.ndarray] = None,
        east_axis: Optional[np.ndarray] = None,
        elevation_m: Optional[np.ndarray] = None,
        default_elevation_m: float = 0.0,
    ) -> None:
        self._default = float(default_elevation_m)
        if north_axis is not None and east_axis is not None and elevation_m is not None:
            self._north = np.asarray(north_axis, dtype=np.float64)
            self._east = np.asarray(east_axis, dtype=np.float64)
            self._elev = np.asarray(elevation_m, dtype=np.float64)
            self._n0 = float(self._north[0])
            self._e0 = float(self._east[0])
            self._dn = float(self._north[1] - self._north[0]) if len(self._north) > 1 else 1.0
            self._de = float(self._east[1] - self._east[0]) if len(self._east) > 1 else 1.0
        else:
            self._north = None
            self._east = None
            self._elev = None
            self._n0 = self._e0 = 0.0
            self._dn = self._de = 1.0

    @classmethod
    def flat(cls, elevation_m: float = 0.0) -> DemGrid:
        return cls(default_elevation_m=elevation_m)

    @classmethod
    def from_file(cls, path: str | Path) -> DemGrid:
        p = Path(path)
        if p.suffix.lower() == ".npz":
            data = np.load(p)
            return cls(
                north_axis=data["north_axis"],
                east_axis=data["east_axis"],
                elevation_m=data["elevation_m"],
            )
        if p.suffix.lower() in (".tif", ".tiff"):
            try:
                import rasterio  # type: ignore
            except ImportError as err:
                raise ImportError("Install rasterio to load GeoTIFF DEM files") from err
            with rasterio.open(p) as ds:
                arr = ds.read(1).astype(np.float64)
                # Build row/col coordinates from affine transform
                rows = np.arange(ds.height, dtype=np.float64)
                cols = np.arange(ds.width, dtype=np.float64)
                xs = ds.transform.c + (cols + 0.5) * ds.transform.a
                ys = ds.transform.f + (rows + 0.5) * ds.transform.e
                if ys[0] > ys[-1]:
                    ys = ys[::-1]
                    arr = arr[::-1, :]
                return cls(north_axis=ys, east_axis=xs, elevation_m=arr)
        raise ValueError(f"Unsupported DEM file format: {p}")

    @property
    def has_grid(self) -> bool:
        return self._elev is not None

    def sample(self, north_m: float, east_m: float) -> float:
        """Return terrain height (m above site origin) at (north_m, east_m)."""
        if self._elev is None:
            return self._default

        fi = (float(north_m) - self._n0) / self._dn
        fj = (float(east_m) - self._e0) / self._de
        ni, nj = self._elev.shape
        fi = float(np.clip(fi, 0.0, ni - 1.0))
        fj = float(np.clip(fj, 0.0, nj - 1.0))
        i0 = int(math.floor(fi))
        j0 = int(math.floor(fj))
        i1 = min(i0 + 1, ni - 1)
        j1 = min(j0 + 1, nj - 1)
        wi = fi - i0
        wj = fj - j0

        v00 = self._elev[i0, j0]
        v10 = self._elev[i1, j0]
        v01 = self._elev[i0, j1]
        v11 = self._elev[i1, j1]
        return float(
            (1.0 - wi) * (1.0 - wj) * v00
            + wi * (1.0 - wj) * v10
            + (1.0 - wi) * wj * v01
            + wi * wj * v11
        )

    def agl_m(self, north_m: float, east_m: float, rel_alt_m: float) -> float:
        """Compute altitude AGL against terrain rather than runway datum (MAST-L2-GNC-04)."""
        return float(rel_alt_m) - self.sample(north_m, east_m)


def euler_ned_to_dcm(roll_deg: float, pitch_deg: float, yaw_deg: float) -> np.ndarray:
    """Rotation matrix R_ned_from_body (3x3) for PX4 aerospace ZYX (yaw-pitch-roll) Euler angles.

    Body frame: +X forward (nose), +Y right wing, +Z down.
    World frame: +N north, +E east, +D down.
    """
    r = math.radians(roll_deg)
    p = math.radians(pitch_deg)
    y = math.radians(yaw_deg)

    cr, sr = math.cos(r), math.sin(r)
    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)

    return np.array(
        [
            [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr],
        ],
        dtype=np.float64,
    )


@dataclass(frozen=True)
class GroundPoint:
    north_m: float
    east_m: float
    terrain_elev_m: float
    lat_deg: float
    lon_deg: float


def project_pixel_to_ground(
    u: float,
    v: float,
    frame: Frame,
    intrinsics: CameraIntrinsics,
    local_proj: LocalProjection,
    dem: Optional[DemGrid] = None,
    max_iters: int = 8,
) -> Optional[GroundPoint]:
    """Project an image pixel (u, v) from a fixed nadir camera to WGS-84 & local North/East.

    Camera convention (matches rc_cessna_cam_down and SUB-PER fixed nadir mount):
      - Image +u (right) -> +Y_body (right wing)
      - Image +v (down)  -> -X_body (aft/tail)
      - Optical axis     -> +Z_body (down)
    """
    x_n, y_n = intrinsics.pixel_to_normalized(u, v)
    ray_body_ned = np.array([-y_n, x_n, 1.0], dtype=np.float64)
    ray_body_ned /= np.linalg.norm(ray_body_ned)

    r_ned_body = euler_ned_to_dcm(frame.roll_deg, frame.pitch_deg, frame.yaw_deg)
    ray_ned = r_ned_body @ ray_body_ned
    if ray_ned[2] <= 1e-3:
        # Ray points at or above the horizon (e.g., extreme bank angle)
        return None

    cam_n, cam_e = local_proj.gps_to_ne(frame.lat_deg, frame.lon_deg)
    cam_up = float(frame.rel_alt_m)
    dem_grid = dem if dem is not None else DemGrid.flat(0.0)

    # Iterative ray-DEM intersection (exact in 1 step on flat terrain, converges in ~3-5 steps on slopes)
    z_ground = dem_grid.sample(cam_n, cam_e)
    hit_n, hit_e = cam_n, cam_e
    for _ in range(max_iters):
        height_above = cam_up - z_ground
        if height_above <= 0.1:
            return None
        t = height_above / float(ray_ned[2])
        hit_n = cam_n + t * float(ray_ned[0])
        hit_e = cam_e + t * float(ray_ned[1])
        new_z = dem_grid.sample(hit_n, hit_e)
        if abs(new_z - z_ground) < 1e-3:
            z_ground = new_z
            break
        z_ground = new_z

    lat_deg, lon_deg = local_proj.ne_to_gps(hit_n, hit_e)
    return GroundPoint(
        north_m=hit_n,
        east_m=hit_e,
        terrain_elev_m=z_ground,
        lat_deg=lat_deg,
        lon_deg=lon_deg,
    )


def frame_ground_footprint(
    frame: Frame,
    intrinsics: CameraIntrinsics,
    local_proj: LocalProjection,
    dem: Optional[DemGrid] = None,
) -> Optional[list[tuple[float, float]]]:
    """Return the four ground corners [(north_m, east_m), ...] of a frame, or None if any misses ground."""
    corners_px = [
        (0.0, 0.0),
        (float(intrinsics.width - 1), 0.0),
        (float(intrinsics.width - 1), float(intrinsics.height - 1)),
        (0.0, float(intrinsics.height - 1)),
    ]
    corners_ne: list[tuple[float, float]] = []
    for u, v in corners_px:
        pt = project_pixel_to_ground(u, v, frame, intrinsics, local_proj, dem=dem)
        if pt is None:
            return None
        corners_ne.append((pt.north_m, pt.east_m))
    return corners_ne
