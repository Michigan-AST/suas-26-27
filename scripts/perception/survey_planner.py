"""Boustrophedon (lawnmower) survey planner meeting MAST-L2-ASW-05 & MAST-L2-PER-07."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mission import SearchBoundary, Waypoint
    from .camera import CameraIntrinsics


@dataclass(frozen=True)
class SurveyPlan:
    waypoints: list[Waypoint]
    pass_count: int
    across_track_stride_m: float
    along_track_trigger_m: float
    ground_footprint_across_m: float
    ground_footprint_along_m: float
    gsd_cm_per_px: float
    estimated_path_length_m: float


def plan_boustrophedon_survey(
    boundary: SearchBoundary,
    intrinsics: CameraIntrinsics,
    altitude_agl_m: float = 50.0,
    along_overlap: float = 0.70,
    across_sidelap: float = 0.30,
    edge_buffer_m: float = 15.0,
    lead_in_m: float = 40.0,
) -> SurveyPlan:
    """Generate a lawnmower survey covering `boundary` + `edge_buffer_m` with required overlap.

    Flies along the longer axis of the Search Boundary to minimize fixed-wing turns, and adds
    `lead_in_m` overshoot at each end so wings are level before entering the buffered area.
    """
    from mission import Waypoint

    if not (0.0 <= along_overlap < 0.95) or not (0.0 <= across_sidelap < 0.95):
        raise ValueError("Overlap and sidelap must be in [0, 0.95)")
    if altitude_agl_m < 45.7:
        raise ValueError("Survey altitude must be >= 45.7 m AGL (150 ft floor)")

    # Ground footprint from pinhole intrinsics: image width is across-track, height is along-track
    footprint_across_m = altitude_agl_m * (intrinsics.width / intrinsics.fx)
    footprint_along_m = altitude_agl_m * (intrinsics.height / intrinsics.fy)
    gsd_cm = (footprint_across_m / intrinsics.width) * 100.0

    stride_m = footprint_across_m * (1.0 - across_sidelap)
    trigger_m = footprint_along_m * (1.0 - along_overlap)

    min_n = boundary.min_north - edge_buffer_m
    max_n = boundary.max_north + edge_buffer_m
    min_e = boundary.min_east - edge_buffer_m
    max_e = boundary.max_east + edge_buffer_m

    span_n = max_n - min_n
    span_e = max_e - min_e

    waypoints: list[Waypoint] = []
    if span_n >= span_e:
        # Fly North-South passes stepping East
        pass_count = max(1, math.ceil(span_e / stride_m))
        step_e = span_e / pass_count
        e_positions = [min_e + (i + 0.5) * step_e for i in range(pass_count)]
        n_start = min_n - lead_in_m
        n_end = max_n + lead_in_m
        for idx, east in enumerate(e_positions):
            if idx % 2 == 0:
                waypoints.append(Waypoint(north=round(n_start, 2), east=round(east, 2), height=altitude_agl_m))
                waypoints.append(Waypoint(north=round(n_end, 2), east=round(east, 2), height=altitude_agl_m))
            else:
                waypoints.append(Waypoint(north=round(n_end, 2), east=round(east, 2), height=altitude_agl_m))
                waypoints.append(Waypoint(north=round(n_start, 2), east=round(east, 2), height=altitude_agl_m))
    else:
        # Fly East-West passes stepping North
        pass_count = max(1, math.ceil(span_n / stride_m))
        step_n = span_n / pass_count
        n_positions = [min_n + (i + 0.5) * step_n for i in range(pass_count)]
        e_start = min_e - lead_in_m
        e_end = max_e + lead_in_m
        for idx, north in enumerate(n_positions):
            if idx % 2 == 0:
                waypoints.append(Waypoint(north=round(north, 2), east=round(e_start, 2), height=altitude_agl_m))
                waypoints.append(Waypoint(north=round(north, 2), east=round(e_end, 2), height=altitude_agl_m))
            else:
                waypoints.append(Waypoint(north=round(north, 2), east=round(e_end, 2), height=altitude_agl_m))
                waypoints.append(Waypoint(north=round(north, 2), east=round(e_start, 2), height=altitude_agl_m))

    path_len = 0.0
    for a, b in zip(waypoints, waypoints[1:]):
        path_len += math.hypot(b.north - a.north, b.east - a.east)

    return SurveyPlan(
        waypoints=waypoints,
        pass_count=pass_count,
        across_track_stride_m=round(stride_m, 2),
        along_track_trigger_m=round(trigger_m, 2),
        ground_footprint_across_m=round(footprint_across_m, 2),
        ground_footprint_along_m=round(footprint_along_m, 2),
        gsd_cm_per_px=round(gsd_cm, 3),
        estimated_path_length_m=round(path_len, 1),
    )
