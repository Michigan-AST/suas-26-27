#!/usr/bin/env python3
"""Standalone orthomosaic mapper (OpenDroneMap + fast OpenCV fallback) and verified USB export.

Runs as an independent process reading a captures/<run_id>/ directory so mapping faults are
isolated from flight control and target delivery (MAST-L2-ASW-12, MAST-L2-PER-09/10/11).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import time
from typing import Optional

import cv2
import numpy as np

from .camera import CameraIntrinsics, Frame, ReplaySource
from .geo import DemGrid, LocalProjection, frame_ground_footprint


@dataclass(frozen=True)
class MapResult:
    output_path: Path
    backend_used: str
    frame_count: int
    used_frames: int
    width_px: int
    height_px: int
    gsd_m_per_px: float
    elapsed_s: float
    bounds_ne: tuple[float, float, float, float]  # (min_north, max_north, min_east, max_east)


def _odm_available(image: str = "opendronemap/odm") -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        proc = subprocess.run(
            ["docker", "image", "inspect", image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
        return proc.returncode == 0
    except Exception:
        return False


def build_orthomosaic_odm(
    capture_dir: Path,
    output_path: Path,
    odm_image: str = "opendronemap/odm",
    orthophoto_resolution_cm: float = 2.0,
) -> MapResult:
    """Run offline OpenDroneMap (--fast-orthophoto) in Docker on an EXIF-geotagged capture folder."""
    t0 = time.monotonic()
    capture_dir = capture_dir.resolve()
    images_dir = capture_dir / "images" if (capture_dir / "images").is_dir() else capture_dir
    jpgs = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg"))
    if not jpgs:
        raise ValueError(f"No JPEG images found in {images_dir}")

    # ODM expects <project_root>/<project_name>/images/*.jpg
    odm_work = capture_dir / "_odm_work"
    odm_proj = odm_work / "survey"
    odm_images = odm_proj / "images"
    odm_images.mkdir(parents=True, exist_ok=True)
    for jpg in jpgs:
        dst = odm_images / jpg.name
        if not dst.exists():
            shutil.copy2(jpg, dst)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{odm_work}:/datasets",
        odm_image,
        "--project-path", "/datasets", "survey",
        "--fast-orthophoto",
        "--orthophoto-resolution", f"{orthophoto_resolution_cm:.2f}",
        "--orthophoto-png",
        "--skip-3dmodel",
        "--skip-report",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"ODM failed (exit {proc.returncode}): {proc.stderr[-500:]}")

    odm_png = odm_proj / "odm_orthophoto" / "odm_orthophoto.png"
    odm_tif = odm_proj / "odm_orthophoto" / "odm_orthophoto.tif"
    src_img_path = odm_png if odm_png.is_file() else odm_tif
    if not src_img_path.is_file():
        raise FileNotFoundError(f"ODM finished without producing orthophoto under {odm_proj}")

    img = cv2.imread(str(src_img_path), cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"Could not decode ODM orthophoto at {src_img_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), img)
    elapsed = time.monotonic() - t0
    return MapResult(
        output_path=output_path,
        backend_used="odm",
        frame_count=len(jpgs),
        used_frames=len(jpgs),
        width_px=int(img.shape[1]),
        height_px=int(img.shape[0]),
        gsd_m_per_px=orthophoto_resolution_cm / 100.0,
        elapsed_s=elapsed,
        bounds_ne=(0.0, 0.0, 0.0, 0.0),
    )


def build_orthomosaic_opencv(
    frames: list[Frame],
    intrinsics: CameraIntrinsics,
    local_proj: LocalProjection,
    output_path: Path,
    dem: Optional[DemGrid] = None,
    gsd_m_per_px: float = 0.05,
    max_canvas_dim_px: int = 8192,
    max_bank_deg: float = 22.0,
) -> MapResult:
    """Fast pose-projected incremental orthomosaic with distance-transform feather blending.

    Bounds peak canvas size to `max_canvas_dim_px` (MAST-L2-ASW-06) and runs in seconds on CPU,
    serving as both an in-flight preview and a guaranteed <60 s fallback when ODM is unavailable.
    """
    t0 = time.monotonic()
    if not frames:
        raise ValueError("Cannot build orthomosaic from 0 frames")

    valid_entries: list[tuple[Frame, list[tuple[float, float]]]] = []
    for frame in frames:
        if abs(frame.roll_deg) > max_bank_deg or abs(frame.pitch_deg) > max_bank_deg:
            continue
        fp = frame_ground_footprint(frame, intrinsics, local_proj, dem=dem)
        if fp is not None:
            valid_entries.append((frame, fp))

    if not valid_entries:
        raise ValueError("No valid near-level frames with ground intersection to stitch")

    all_n = [pt[0] for _, fp in valid_entries for pt in fp]
    all_e = [pt[1] for _, fp in valid_entries for pt in fp]
    min_n, max_n = min(all_n), max(all_n)
    min_e, max_e = min(all_e), max(all_e)

    span_n = max(1.0, max_n - min_n)
    span_e = max(1.0, max_e - min_e)

    # Enforce bounded memory cap (MAST-L2-ASW-06)
    effective_gsd = max(
        float(gsd_m_per_px),
        span_n / max_canvas_dim_px,
        span_e / max_canvas_dim_px,
    )
    canvas_h = max(16, int(math.ceil(span_n / effective_gsd)))
    canvas_w = max(16, int(math.ceil(span_e / effective_gsd)))

    accum_rgb = np.zeros((canvas_h, canvas_w, 3), dtype=np.float32)
    accum_w = np.zeros((canvas_h, canvas_w), dtype=np.float32)

    # Smooth center-weighted feather mask per frame so seam edges blend cleanly
    h_in, w_in = valid_entries[0][0].image.shape[:2]
    src_corners = np.array(
        [[0.0, 0.0], [w_in - 1.0, 0.0], [w_in - 1.0, h_in - 1.0], [0.0, h_in - 1.0]],
        dtype=np.float32,
    )
    ones = np.ones((h_in, w_in), dtype=np.uint8)
    ones[0, :] = ones[-1, :] = ones[:, 0] = ones[:, -1] = 0
    feather_mask = cv2.distanceTransform(ones, cv2.DIST_L2, 3)
    if feather_mask.max() > 0:
        feather_mask = (feather_mask / feather_mask.max()).astype(np.float32)
    else:
        feather_mask = np.ones((h_in, w_in), dtype=np.float32)

    for frame, fp in valid_entries:
        img = intrinsics.undistort(frame.image)
        if img.shape[0] != h_in or img.shape[1] != w_in:
            img = cv2.resize(img, (w_in, h_in), interpolation=cv2.INTER_AREA)

        # Map ground (north, east) to canvas pixels: top = max_n, right = max_e
        dst_corners = np.array(
            [[(e - min_e) / effective_gsd, (max_n - n) / effective_gsd] for n, e in fp],
            dtype=np.float32,
        )

        # Warp only into the tight bounding box of this frame on the canvas (O(frame), not O(canvas))
        x0 = max(0, int(math.floor(float(dst_corners[:, 0].min()))))
        y0 = max(0, int(math.floor(float(dst_corners[:, 1].min()))))
        x1 = min(canvas_w, int(math.ceil(float(dst_corners[:, 0].max()))) + 1)
        y1 = min(canvas_h, int(math.ceil(float(dst_corners[:, 1].max()))) + 1)
        if x1 <= x0 or y1 <= y0:
            continue

        local_dst = dst_corners - np.array([[float(x0), float(y0)]], dtype=np.float32)
        H = cv2.getPerspectiveTransform(src_corners, local_dst)
        roi_w, roi_h = x1 - x0, y1 - y0
        warped = cv2.warpPerspective(img, H, (roi_w, roi_h), flags=cv2.INTER_LINEAR)
        warped_w = cv2.warpPerspective(feather_mask, H, (roi_w, roi_h), flags=cv2.INTER_LINEAR)

        accum_rgb[y0:y1, x0:x1] += warped.astype(np.float32) * warped_w[..., None]
        accum_w[y0:y1, x0:x1] += warped_w

    valid_mask = accum_w > 1e-6
    out = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
    out[valid_mask] = np.clip(
        accum_rgb[valid_mask] / accum_w[valid_mask, None],
        0.0,
        255.0,
    ).astype(np.uint8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), out)

    elapsed = time.monotonic() - t0
    return MapResult(
        output_path=output_path,
        backend_used="opencv",
        frame_count=len(frames),
        used_frames=len(valid_entries),
        width_px=canvas_w,
        height_px=canvas_h,
        gsd_m_per_px=effective_gsd,
        elapsed_s=elapsed,
        bounds_ne=(min_n, max_n, min_e, max_e),
    )


def build_orthomosaic(
    capture_dir: str | Path,
    output_path: str | Path,
    backend: str = "auto",
    scene_path: Optional[str | Path] = None,
    dem_path: Optional[str | Path] = None,
    gsd_m_per_px: float = 0.05,
) -> MapResult:
    """Build an orthomosaic using ODM (when requested/available) or the fast OpenCV fallback."""
    cdir = Path(capture_dir)
    out = Path(output_path)

    mode = backend.lower()
    if mode == "odm" or (mode == "auto" and _odm_available()):
        try:
            return build_orthomosaic_odm(cdir, out, orthophoto_resolution_cm=max(1.0, gsd_m_per_px * 100.0))
        except Exception as err:
            if mode == "odm":
                raise
            print(f"ODM backend failed ({err}); falling back to OpenCV orthomosaic.")

    cam_json = cdir / "camera.json"
    intrinsics = (
        CameraIntrinsics.from_dict(json.loads(cam_json.read_text(encoding="utf-8")))
        if cam_json.is_file()
        else CameraIntrinsics.from_hfov(1280, 960, 0.967)
    )
    frames = ReplaySource(cdir).iter_frames_sync()
    if not frames:
        raise ValueError(f"No frames found in {cdir}")

    if scene_path and Path(scene_path).is_file():
        scene = json.loads(Path(scene_path).read_text(encoding="utf-8"))
        origin = scene["origin"]
        local_proj = LocalProjection(origin["latitude_deg"], origin["longitude_deg"], origin.get("elevation_m", 0.0))
    else:
        local_proj = LocalProjection(frames[0].lat_deg, frames[0].lon_deg, frames[0].alt_amsl_m)

    dem = DemGrid.from_file(dem_path) if (dem_path and Path(dem_path).is_file()) else DemGrid.flat(0.0)
    return build_orthomosaic_opencv(
        frames=frames,
        intrinsics=intrinsics,
        local_proj=local_proj,
        output_path=out,
        dem=dem,
        gsd_m_per_px=gsd_m_per_px,
    )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def export_map_to_usb(
    map_path: str | Path,
    usb_mount_dir: str | Path,
    team_name: str = "MAST",
) -> tuple[Path, str]:
    """Copy the risk map to a USB drive with team name in filename and SHA-256 read-back verification.

    Satisfies MAST-L2-PER-11 and MAST-L2-GCS-10.
    """
    src = Path(map_path)
    if not src.is_file():
        raise FileNotFoundError(f"Map file not found: {src}")
    suffix = src.suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg"):
        raise ValueError(f"Competition map must be .png or .jpeg (got {suffix})")

    dst_dir = Path(usb_mount_dir)
    if not dst_dir.is_dir():
        raise FileNotFoundError(f"USB destination directory not found: {dst_dir}")

    safe_team = "".join(c for c in team_name if c.isalnum() or c in ("_", "-")) or "MAST"
    dst = dst_dir / f"{safe_team}_risk_map{suffix}"

    src_hash = _sha256_file(src)
    shutil.copyfile(src, dst)
    with open(dst, "rb+") as f:
        f.flush()
    dst_hash = _sha256_file(dst)
    if dst_hash != src_hash:
        raise IOError(f"USB checksum verification failed: {dst_hash} != {src_hash}")
    return dst, dst_hash


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SUAS Risk Mapping orthomosaic from a capture directory.")
    parser.add_argument("capture_dir", help="Path to captures/<run_id> or EXIF-geotagged JPEG folder")
    parser.add_argument("--out", default=None, help="Output map path (default: <capture_dir>/MAST_risk_map.png)")
    parser.add_argument("--backend", choices=["auto", "odm", "opencv"], default="auto")
    parser.add_argument("--scene", default="worlds/suas_site/scene.json", help="Optional scene.json for site origin")
    parser.add_argument("--dem", default="worlds/suas_site/dem.npz", help="Optional DEM file")
    parser.add_argument("--gsd", type=float, default=0.05, help="Output pixel size in metres (default: 0.05 m/px)")
    parser.add_argument("--export-usb", default=None, help="Optional USB mount path for checksum-verified export")
    args = parser.parse_args()

    cdir = Path(args.capture_dir)
    out = Path(args.out) if args.out else cdir / "MAST_risk_map.png"
    result = build_orthomosaic(
        capture_dir=cdir,
        output_path=out,
        backend=args.backend,
        scene_path=args.scene,
        dem_path=args.dem,
        gsd_m_per_px=args.gsd,
    )
    print(
        f"Map built via {result.backend_used}: {result.output_path} "
        f"({result.width_px}x{result.height_px} px, {result.gsd_m_per_px * 100:.1f} cm/px, "
        f"{result.used_frames}/{result.frame_count} frames, {result.elapsed_s:.2f} s)"
    )
    if args.export_usb:
        dst, digest = export_map_to_usb(result.output_path, args.export_usb)
        print(f"Verified USB export: {dst} (sha256={digest[:16]}...)")


if __name__ == "__main__":
    main()
