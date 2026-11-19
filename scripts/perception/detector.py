"""Raw-frame target detection, ground projection, and multi-frame association (MAST-L2-PER-12..16).

Detection intentionally runs on raw captured frames rather than the stitched orthomosaic so:
  - targets are associated across >= 3 independent views (MAST-L2-PER-14), and
  - a mapping failure cannot prevent target detection or payload delivery (MAST-L2-ASW-12).
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Optional, Protocol

import cv2
import numpy as np

from .camera import CameraIntrinsics, Frame
from .geo import DemGrid, LocalProjection, project_pixel_to_ground


@dataclass(frozen=True)
class Detection:
    label: str  # "tent" | "mannequin"
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]

    @property
    def centroid_uv(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox_xyxy
        return (x1 + x2) * 0.5, (y1 + y2) * 0.5


@dataclass(frozen=True)
class ProjectedObservation:
    label: str
    confidence: float
    north_m: float
    east_m: float
    lat_deg: float
    lon_deg: float
    frame_seq: int


@dataclass(frozen=True)
class DeclaredTarget:
    label: str  # "tent" | "mannequin"
    north_m: float
    east_m: float
    lat_deg: float
    lon_deg: float
    confidence: float
    observations: int

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "north_m": round(self.north_m, 2),
            "east_m": round(self.east_m, 2),
            "lat_deg": round(self.lat_deg, 7),
            "lon_deg": round(self.lon_deg, 7),
            "confidence": round(self.confidence, 3),
            "observations": self.observations,
        }


class Detector(Protocol):
    def detect(self, image_bgr: np.ndarray) -> list[Detection]: ...


class ColorShapeDetector:
    """Lightweight OpenCV detector for the Gazebo SITL targets (open blue tent & orange-red mannequin).

    Lets the full SURVEY -> SEARCH -> DELIVERY autonomy loop run end-to-end in SITL with zero
    PyTorch/YOLO weight downloads. Swap to YoloDetector for competition flights.
    """

    def __init__(self, min_tent_area_px: float = 180.0, min_mannequin_area_px: float = 45.0) -> None:
        self.min_tent_area_px = float(min_tent_area_px)
        self.min_mannequin_area_px = float(min_mannequin_area_px)

    def detect(self, image_bgr: np.ndarray) -> list[Detection]:
        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
        detections: list[Detection] = []
        kernel = np.ones((3, 3), np.uint8)

        # 1. Open blue canopy tent: high-saturation cobalt blue, roughly square footprint
        blue_mask = cv2.inRange(hsv, np.array([102, 120, 70]), np.array([130, 255, 255]))
        blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)
        blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_tent_area_px:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = max(w, h) / max(1.0, min(w, h))
            fill_ratio = area / max(1.0, float(w * h))
            if aspect <= 1.8 and fill_ratio >= 0.45:
                conf = min(0.99, 0.70 + 0.25 * fill_ratio)
                detections.append(Detection("tent", conf, (float(x), float(y), float(x + w), float(y + h))))

        # 2. Clothed mannequin: high-saturation orange-red jacket
        red1 = cv2.inRange(hsv, np.array([0, 125, 80]), np.array([14, 255, 255]))
        red2 = cv2.inRange(hsv, np.array([168, 125, 80]), np.array([179, 255, 255]))
        red_mask = cv2.bitwise_or(red1, red2)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_mannequin_area_px:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            fill_ratio = area / max(1.0, float(w * h))
            conf = min(0.98, 0.65 + 0.30 * min(1.0, fill_ratio + 0.2))
            detections.append(Detection("mannequin", conf, (float(x), float(y), float(x + w), float(y + h))))

        return detections


class YoloDetector:
    """Ultralytics YOLO11 wrapper using local weights only (no runtime network per MAST-L2-PER-16)."""

    def __init__(
        self,
        weights_path: str | Path,
        conf_threshold: float = 0.35,
        class_map: Optional[dict[str, str]] = None,
    ) -> None:
        weights = Path(weights_path)
        if not weights.is_file():
            raise FileNotFoundError(f"Local YOLO weights not found: {weights}")
        try:
            from ultralytics import YOLO  # type: ignore
        except ImportError as err:
            raise ImportError("Install ultralytics to run YoloDetector") from err
        self._model = YOLO(str(weights))
        self.conf_threshold = float(conf_threshold)
        self.class_map = class_map or {"mannequin": "mannequin", "person": "mannequin", "tent": "tent"}

    def detect(self, image_bgr: np.ndarray) -> list[Detection]:
        results = self._model.predict(image_bgr, conf=self.conf_threshold, verbose=False)
        detections: list[Detection] = []
        for res in results:
            names = res.names
            for box in res.boxes:
                cls_name = str(names[int(box.cls[0])]).lower()
                mapped = self.class_map.get(cls_name)
                if mapped is None:
                    continue
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
                detections.append(Detection(mapped, float(box.conf[0]), (x1, y1, x2, y2)))
        return detections


def create_detector(weights_path: Optional[str | Path] = None) -> Detector:
    """Use YoloDetector if local weights are configured and present; otherwise ColorShapeDetector."""
    if weights_path and Path(weights_path).is_file():
        return YoloDetector(weights_path)
    return ColorShapeDetector()


def associate_and_declare(
    observations: list[ProjectedObservation],
    local_proj: LocalProjection,
    min_observations: int = 3,
    cluster_radius_m: float = 8.0,
) -> list[DeclaredTarget]:
    """Cluster projected detections per class and declare at most one mannequin and one tent.

    Enforces:
      - MAST-L2-PER-14: require observations across >= `min_observations` distinct frames.
      - MAST-L2-ASW-07: declare at most one target per class (mannequin, tent).
    """
    declared: list[DeclaredTarget] = []

    for label in ("mannequin", "tent"):
        cls_obs = [o for o in observations if o.label == label]
        if not cls_obs:
            continue

        # Connected-component / greedy spatial clustering in North/East metres
        clusters: list[list[ProjectedObservation]] = []
        for obs in cls_obs:
            best_cluster: Optional[list[ProjectedObservation]] = None
            best_dist = cluster_radius_m
            for cl in clusters:
                cn = sum(item.north_m for item in cl) / len(cl)
                ce = sum(item.east_m for item in cl) / len(cl)
                dist = math.hypot(obs.north_m - cn, obs.east_m - ce)
                if dist <= best_dist:
                    best_dist = dist
                    best_cluster = cl
            if best_cluster is not None:
                best_cluster.append(obs)
            else:
                clusters.append([obs])

        # Filter to clusters supported by >= min_observations distinct frames
        valid: list[tuple[int, float, list[ProjectedObservation]]] = []
        for cl in clusters:
            distinct_frames = len({item.frame_seq for item in cl})
            if distinct_frames >= min_observations:
                avg_conf = sum(item.confidence for item in cl) / len(cl)
                valid.append((distinct_frames, avg_conf, cl))

        if not valid:
            continue

        # Pick strongest cluster (most distinct frame observations, then highest confidence)
        valid.sort(key=lambda item: (item[0], item[1]), reverse=True)
        distinct_frames, avg_conf, winner = valid[0]

        # Confidence-weighted centroid
        w_sum = sum(max(0.01, item.confidence) for item in winner)
        north_m = sum(item.north_m * max(0.01, item.confidence) for item in winner) / w_sum
        east_m = sum(item.east_m * max(0.01, item.confidence) for item in winner) / w_sum
        lat_deg, lon_deg = local_proj.ne_to_gps(north_m, east_m)

        declared.append(
            DeclaredTarget(
                label=label,
                north_m=north_m,
                east_m=east_m,
                lat_deg=lat_deg,
                lon_deg=lon_deg,
                confidence=avg_conf,
                observations=distinct_frames,
            )
        )

    return declared


def run_search_pipeline(
    frames: list[Frame],
    intrinsics: CameraIntrinsics,
    local_proj: LocalProjection,
    dem: Optional[DemGrid] = None,
    detector: Optional[Detector] = None,
    min_observations: int = 3,
    cluster_radius_m: float = 8.0,
    max_bank_deg: float = 25.0,
) -> tuple[list[DeclaredTarget], list[ProjectedObservation]]:
    """Run per-frame detection -> DEM-aware ray projection -> multi-frame clustering."""
    det = detector or ColorShapeDetector()
    observations: list[ProjectedObservation] = []

    for frame in frames:
        if abs(frame.roll_deg) > max_bank_deg or abs(frame.pitch_deg) > max_bank_deg:
            continue
        for hit in det.detect(frame.image):
            u, v = hit.centroid_uv
            pt = project_pixel_to_ground(u, v, frame, intrinsics, local_proj, dem=dem)
            if pt is None:
                continue
            observations.append(
                ProjectedObservation(
                    label=hit.label,
                    confidence=hit.confidence,
                    north_m=pt.north_m,
                    east_m=pt.east_m,
                    lat_deg=pt.lat_deg,
                    lon_deg=pt.lon_deg,
                    frame_seq=frame.seq,
                )
            )

    targets = associate_and_declare(
        observations=observations,
        local_proj=local_proj,
        min_observations=min_observations,
        cluster_radius_m=cluster_radius_m,
    )
    return targets, observations
