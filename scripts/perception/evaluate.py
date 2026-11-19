#!/usr/bin/env python3
"""Automated SITL scoring script against worlds/suas_site/scene.json ground truth.

Evaluates a capture directory on:
  - Search Boundary (+ 15 m buffer) coverage % (MAST-L2-PER-07)
  - Target detection & geolocation error in metres vs 5.0 m budget (MAST-L2-PER-15)
  - Orthomosaic build time vs 60 s post-landing budget (MAST-L2-PER-10)
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

from .camera import CameraIntrinsics, ReplaySource
from .detector import DeclaredTarget, create_detector, run_search_pipeline
from .geo import DemGrid, LocalProjection, frame_ground_footprint
from .mapper import MapResult, build_orthomosaic


@dataclass(frozen=True)
class EvaluationReport:
    frame_count: int
    coverage_pct: float
    buffered_coverage_pct: float
    target_errors_m: dict[str, Optional[float]]
    declared_targets: list[DeclaredTarget]
    geolocation_pass: bool
    map_result: Optional[MapResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_count": self.frame_count,
            "coverage_pct": round(self.coverage_pct, 2),
            "buffered_coverage_pct": round(self.buffered_coverage_pct, 2),
            "target_errors_m": {
                k: (round(v, 3) if v is not None else None) for k, v in self.target_errors_m.items()
            },
            "declared_targets": [t.to_dict() for t in self.declared_targets],
            "geolocation_pass": self.geolocation_pass,
            "map_elapsed_s": round(self.map_result.elapsed_s, 3) if self.map_result else None,
            "map_backend": self.map_result.backend_used if self.map_result else None,
        }


def compute_boundary_coverage_pct(
    footprints: list[list[tuple[float, float]]],
    min_north: float,
    max_north: float,
    min_east: float,
    max_east: float,
    grid_step_m: float = 1.0,
) -> float:
    """Rasterize frame footprints onto a 1 m grid and return % of boundary covered."""
    h = max(1, int(math.ceil((max_north - min_north) / grid_step_m)))
    w = max(1, int(math.ceil((max_east - min_east) / grid_step_m)))
    covered = np.zeros((h, w), dtype=np.uint8)
    for fp in footprints:
        poly = np.array(
            [[int(round((e - min_east) / grid_step_m)), int(round((n - min_north) / grid_step_m))] for n, e in fp],
            dtype=np.int32,
        )
        cv2.fillConvexPoly(covered, poly, 1)
    return float(covered.mean() * 100.0)


def evaluate_capture(
    capture_dir: str | Path,
    scene_path: str | Path = "worlds/suas_site/scene.json",
    dem_path: Optional[str | Path] = "worlds/suas_site/dem.npz",
    detector_weights: Optional[str | Path] = None,
    build_map: bool = True,
    mapper_backend: str = "opencv",
    min_observations: int = 3,
    geolocation_budget_m: float = 5.0,
) -> EvaluationReport:
    cdir = Path(capture_dir)
    scene = json.loads(Path(scene_path).read_text(encoding="utf-8"))
    origin = scene["origin"]
    local_proj = LocalProjection(origin["latitude_deg"], origin["longitude_deg"], origin.get("elevation_m", 0.0))
    dem = DemGrid.from_file(dem_path) if (dem_path and Path(dem_path).is_file()) else DemGrid.flat(0.0)

    cam_json = cdir / "camera.json"
    intrinsics = (
        CameraIntrinsics.from_dict(json.loads(cam_json.read_text(encoding="utf-8")))
        if cam_json.is_file()
        else CameraIntrinsics.from_hfov(1280, 960, 0.967)
    )
    frames = ReplaySource(cdir).iter_frames_sync()

    footprints = []
    for frame in frames:
        fp = frame_ground_footprint(frame, intrinsics, local_proj, dem=dem)
        if fp is not None:
            footprints.append(fp)

    sb = scene["search_boundary"]
    buf = float(sb.get("buffer_m", 15.0))
    cov_pct = compute_boundary_coverage_pct(
        footprints, sb["min_north"], sb["max_north"], sb["min_east"], sb["max_east"]
    )
    buf_cov_pct = compute_boundary_coverage_pct(
        footprints,
        sb["min_north"] - buf,
        sb["max_north"] + buf,
        sb["min_east"] - buf,
        sb["max_east"] + buf,
    )

    detector = create_detector(detector_weights)
    declared, _ = run_search_pipeline(
        frames=frames,
        intrinsics=intrinsics,
        local_proj=local_proj,
        dem=dem,
        detector=detector,
        min_observations=min_observations,
    )
    by_label = {t.label: t for t in declared}

    errors: dict[str, Optional[float]] = {}
    for truth in scene.get("targets", []):
        lbl = truth["label"]
        pred = by_label.get(lbl)
        if pred is None:
            errors[lbl] = None
        else:
            errors[lbl] = math.hypot(pred.north_m - truth["north_m"], pred.east_m - truth["east_m"])

    geo_pass = bool(errors) and all(err is not None and err <= geolocation_budget_m for err in errors.values())

    map_res: Optional[MapResult] = None
    if build_map and frames:
        map_res = build_orthomosaic(
            capture_dir=cdir,
            output_path=cdir / "MAST_risk_map.png",
            backend=mapper_backend,
            scene_path=scene_path,
            dem_path=dem_path,
        )

    return EvaluationReport(
        frame_count=len(frames),
        coverage_pct=cov_pct,
        buffered_coverage_pct=buf_cov_pct,
        target_errors_m=errors,
        declared_targets=declared,
        geolocation_pass=geo_pass,
        map_result=map_res,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a SITL capture against ground truth.")
    parser.add_argument("capture_dir", help="Path to captures/<run_id>")
    parser.add_argument("--scene", default="worlds/suas_site/scene.json")
    parser.add_argument("--dem", default="worlds/suas_site/dem.npz")
    parser.add_argument("--weights", default=None, help="Optional local YOLO .pt weights")
    parser.add_argument("--backend", choices=["auto", "odm", "opencv"], default="opencv")
    parser.add_argument("--no-map", action="store_true", help="Skip building orthomosaic during evaluation")
    args = parser.parse_args()

    report = evaluate_capture(
        capture_dir=args.capture_dir,
        scene_path=args.scene,
        dem_path=args.dem,
        detector_weights=args.weights,
        build_map=not args.no_map,
        mapper_backend=args.backend,
    )
    print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
