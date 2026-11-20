"""Unit and end-to-end tests for Phases 0-3 (capture, replay, survey planning, geolocation,
detection/clustering, orthomosaic mapping, USB export, Foxglove scene, and MissionRunner hooks)."""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from foxglove_bridge import build_site_scene_update
from mission import MissionConfig, MissionPhase, MissionRunner, SearchBoundary, Waypoint, create_default_mission
from perception.camera import (
    CameraConfig,
    CameraIntrinsics,
    CaptureSession,
    CaptureWriter,
    Frame,
    ReplaySource,
    read_exif_gps,
)
from perception.detector import (
    ColorShapeDetector,
    ProjectedObservation,
    associate_and_declare,
    run_search_pipeline,
)
from perception.evaluate import evaluate_capture
from perception.geo import DemGrid, LocalProjection, project_pixel_to_ground
from perception.mapper import build_orthomosaic, export_map_to_usb
from perception.survey_planner import plan_boustrophedon_survey


def _make_synthetic_frame(
    north_m: float,
    east_m: float,
    rel_alt_m: float,
    intrinsics: CameraIntrinsics,
    proj: LocalProjection,
    seq: int = 0,
    yaw_deg: float = 0.0,
    tent_ne: tuple[float, float] | None = None,
    mannequin_ne: tuple[float, float] | None = None,
) -> Frame:
    """Create a synthetic nadir BGR frame with optional tent & mannequin drawn at true pixel coords."""
    # Dry sandy field (BGR) — matches worlds/suas_site ground palette
    img = np.full((intrinsics.height, intrinsics.width, 3), (72, 98, 130), dtype=np.uint8)
    img[::64, :, :] = (88, 112, 148)
    img[:, ::64, :] = (88, 112, 148)

    def _draw_world_box(tn: float, te: float, size_m: float, color_bgr: tuple[int, int, int]) -> None:
        # Inverse of flat level nadir projection (yaw=0): u = cx + (dE/alt)*fx, v = cy - (dN/alt)*fy
        dn, de = tn - north_m, te - east_m
        rad = math.radians(yaw_deg)
        # Rotate world NE into body (forward, right)
        fwd = dn * math.cos(rad) + de * math.sin(rad)
        right = -dn * math.sin(rad) + de * math.cos(rad)
        u = intrinsics.cx + (right / rel_alt_m) * intrinsics.fx
        v = intrinsics.cy - (fwd / rel_alt_m) * intrinsics.fy
        half_px = max(6, int(round((size_m * 0.5 / rel_alt_m) * intrinsics.fx)))
        x1, y1 = int(round(u - half_px)), int(round(v - half_px))
        x2, y2 = int(round(u + half_px)), int(round(v + half_px))
        if x2 > 0 and y2 > 0 and x1 < intrinsics.width and y1 < intrinsics.height:
            cv2.rectangle(img, (max(0, x1), max(0, y1)), (min(intrinsics.width - 1, x2), min(intrinsics.height - 1, y2)), color_bgr, -1)

    if tent_ne is not None:
        _draw_world_box(tent_ne[0], tent_ne[1], size_m=3.0, color_bgr=(230, 80, 20))  # Vivid blue in BGR
    if mannequin_ne is not None:
        _draw_world_box(mannequin_ne[0], mannequin_ne[1], size_m=1.2, color_bgr=(25, 45, 235))  # Vivid red-orange in BGR

    lat, lon = proj.ne_to_gps(north_m, east_m)
    return Frame(
        image=img,
        t_capture_us=seq * 500_000,
        lat_deg=lat,
        lon_deg=lon,
        alt_amsl_m=rel_alt_m,
        rel_alt_m=rel_alt_m,
        roll_deg=0.0,
        pitch_deg=0.0,
        yaw_deg=yaw_deg,
        camera_id=intrinsics.camera_id,
        seq=seq,
    )


class TestPerceptionPipeline(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.proj = LocalProjection(47.397971057728974, 8.546163739800146, 0.0)
        self.intrinsics = CameraIntrinsics.from_hfov(640, 480, horizontal_fov_rad=0.967)

    def test_survey_planner_meets_overlap_and_buffer(self) -> None:
        boundary = SearchBoundary(min_north=700.0, max_north=900.0, min_east=200.0, max_east=400.0, buffer_m=25.0)
        intr = CameraIntrinsics.from_hfov(1280, 960, 0.967)
        plan = plan_boustrophedon_survey(boundary, intr, altitude_agl_m=50.0, along_overlap=0.70, across_sidelap=0.30, edge_buffer_m=15.0)

        self.assertGreaterEqual(plan.pass_count, 6)
        self.assertEqual(len(plan.waypoints), plan.pass_count * 2)
        self.assertLessEqual(plan.across_track_stride_m, plan.ground_footprint_across_m * 0.701)
        self.assertLessEqual(plan.along_track_trigger_m, plan.ground_footprint_along_m * 0.301)
        # Verify coverage spans full buffered box [185..415 E] and [685..915 N]
        easts = [wp.east for wp in plan.waypoints]
        norths = [wp.north for wp in plan.waypoints]
        self.assertLess(min(easts), 205.0)
        self.assertGreater(max(easts), 395.0)
        self.assertLess(min(norths), 685.0)
        self.assertGreater(max(norths), 915.0)

    def test_project_pixel_to_ground_flat_and_sloped_dem(self) -> None:
        frame = _make_synthetic_frame(800.0, 300.0, 50.0, self.intrinsics, self.proj, yaw_deg=0.0)
        center = project_pixel_to_ground(
            self.intrinsics.cx, self.intrinsics.cy, frame, self.intrinsics, self.proj, dem=DemGrid.flat(0.0)
        )
        self.assertIsNotNone(center)
        self.assertAlmostEqual(center.north_m, 800.0, places=2)
        self.assertAlmostEqual(center.east_m, 300.0, places=2)

        # Sloped DEM: ground rises +10 m at (800, 320), so a ray aimed at the right edge hits closer
        north_axis = np.array([700.0, 900.0])
        east_axis = np.array([250.0, 350.0])
        elev = np.array([[0.0, 20.0], [0.0, 20.0]])  # linear slope in east: 0 m at E=250, 10 m at E=300, 20 m at E=350
        dem = DemGrid(north_axis, east_axis, elev)
        self.assertAlmostEqual(dem.agl_m(800.0, 300.0, 50.0), 40.0, places=3)

        flat_right = project_pixel_to_ground(
            self.intrinsics.width - 1, self.intrinsics.cy, frame, self.intrinsics, self.proj, dem=DemGrid.flat(0.0)
        )
        sloped_right = project_pixel_to_ground(
            self.intrinsics.width - 1, self.intrinsics.cy, frame, self.intrinsics, self.proj, dem=dem
        )
        self.assertIsNotNone(flat_right)
        self.assertIsNotNone(sloped_right)
        # Higher ground east of camera intercepts ray nearer to nadir
        self.assertLess(sloped_right.east_m, flat_right.east_m - 5.0)
        self.assertGreater(sloped_right.terrain_elev_m, 12.0)

    def test_exif_capture_writer_and_replay_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_001"
            writer = CaptureWriter(run_dir, self.intrinsics)
            frame = _make_synthetic_frame(760.0, 265.0, 50.0, self.intrinsics, self.proj, seq=7, yaw_deg=90.0)
            jpg_path = writer.write(frame)

            # Standard EXIF GPS tags readable directly by OpenDroneMap
            lat, lon, alt = read_exif_gps(jpg_path)
            self.assertAlmostEqual(lat, frame.lat_deg, places=5)
            self.assertAlmostEqual(lon, frame.lon_deg, places=5)
            self.assertAlmostEqual(alt, frame.alt_amsl_m, places=2)

            # Replay with manifest preserves exact attitude and timestamp
            replayed = ReplaySource(run_dir).iter_frames_sync()
            self.assertEqual(len(replayed), 1)
            self.assertAlmostEqual(replayed[0].yaw_deg, 90.0, places=3)
            self.assertEqual(replayed[0].t_capture_us, frame.t_capture_us)

            # Replay of a plain EXIF-only JPEG directory (like public ODMdata) also works with zero converter
            (run_dir / "manifest.jsonl").unlink()
            exif_only = ReplaySource(run_dir).iter_frames_sync()
            self.assertEqual(len(exif_only), 1)
            self.assertAlmostEqual(exif_only[0].lat_deg, frame.lat_deg, places=5)
            self.assertAlmostEqual(exif_only[0].lon_deg, frame.lon_deg, places=5)

    def test_association_enforces_three_frames_and_rejects_debris(self) -> None:
        obs = []
        # 4 observations of true tent near (760, 265)
        for seq, (dn, de) in enumerate([(0.3, -0.2), (-0.4, 0.5), (0.1, 0.1), (-0.2, -0.3)]):
            lat, lon = self.proj.ne_to_gps(760.0 + dn, 265.0 + de)
            obs.append(ProjectedObservation("tent", 0.9, 760.0 + dn, 265.0 + de, lat, lon, frame_seq=seq))
        # Only 2 observations of a stray false positive -> must be rejected (MAST-L2-PER-14)
        for seq in (10, 11):
            lat, lon = self.proj.ne_to_gps(820.0, 210.0)
            obs.append(ProjectedObservation("tent", 0.95, 820.0, 210.0, lat, lon, frame_seq=seq))
        # 3 observations of mannequin near (835, 330)
        for seq, (dn, de) in enumerate([(0.2, 0.0), (-0.1, 0.4), (0.0, -0.2)], start=20):
            lat, lon = self.proj.ne_to_gps(835.0 + dn, 330.0 + de)
            obs.append(ProjectedObservation("mannequin", 0.85, 835.0 + dn, 330.0 + de, lat, lon, frame_seq=seq))

        declared = associate_and_declare(obs, self.proj, min_observations=3)
        self.assertEqual(len(declared), 2)
        by_lbl = {t.label: t for t in declared}
        self.assertLess(math.hypot(by_lbl["tent"].north_m - 760.0, by_lbl["tent"].east_m - 265.0), 0.5)
        self.assertLess(math.hypot(by_lbl["mannequin"].north_m - 835.0, by_lbl["mannequin"].east_m - 330.0), 0.5)

    def test_end_to_end_capture_detection_mapping_usb_and_eval(self) -> None:
        scene_path = REPO_ROOT / "worlds" / "suas_site" / "scene.json"
        self.assertTrue(scene_path.is_file(), "Run 'make world' to generate worlds/suas_site/scene.json")
        scene = json.loads(scene_path.read_text(encoding="utf-8"))
        tent = next(t for t in scene["targets"] if t["label"] == "tent")
        mann = next(t for t in scene["targets"] if t["label"] == "mannequin")

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "sitl_run"
            usb_dir = Path(tmp) / "usb_drive"
            usb_dir.mkdir()
            writer = CaptureWriter(run_dir, self.intrinsics)

            # Simulate 6 overlapping nadir frames over tent and 6 over mannequin
            seq = 0
            for offset_n in (-10.0, -5.0, 0.0, 5.0, 10.0, 12.0):
                writer.write(
                    _make_synthetic_frame(
                        tent["north_m"] + offset_n,
                        tent["east_m"],
                        50.0,
                        self.intrinsics,
                        self.proj,
                        seq=seq,
                        tent_ne=(tent["north_m"], tent["east_m"]),
                        mannequin_ne=(mann["north_m"], mann["east_m"]),
                    )
                )
                seq += 1
            for offset_n in (-10.0, -5.0, 0.0, 5.0, 10.0, 12.0):
                writer.write(
                    _make_synthetic_frame(
                        mann["north_m"] + offset_n,
                        mann["east_m"],
                        50.0,
                        self.intrinsics,
                        self.proj,
                        seq=seq,
                        tent_ne=(tent["north_m"], tent["east_m"]),
                        mannequin_ne=(mann["north_m"], mann["east_m"]),
                    )
                )
                seq += 1

            report = evaluate_capture(
                capture_dir=run_dir,
                scene_path=scene_path,
                dem_path=REPO_ROOT / "worlds" / "suas_site" / "dem.npz",
                build_map=True,
                mapper_backend="opencv",
            )
            self.assertTrue(report.geolocation_pass, f"Expected <5m geolocation, got {report.target_errors_m}")
            self.assertLess(report.target_errors_m["tent"], 1.5)
            self.assertLess(report.target_errors_m["mannequin"], 1.5)
            self.assertIsNotNone(report.map_result)
            self.assertTrue(report.map_result.output_path.is_file())
            self.assertLess(report.map_result.elapsed_s, 60.0)

            exported, sha = export_map_to_usb(report.map_result.output_path, usb_dir, team_name="MAST")
            self.assertEqual(exported.name, "MAST_risk_map.png")
            self.assertEqual(len(sha), 64)

    async def test_mission_runner_capture_search_handoff_and_abort_cleanup(self) -> None:
        config = create_default_mission()
        events: list[str] = []

        class FakeCapture:
            async def start(self) -> Path:
                events.append("capture_start")
                return Path("/tmp/fake_capture")

            async def stop(self) -> Path:
                events.append("capture_stop")
                return Path("/tmp/fake_capture")

        async def fake_search(capture_dir: Path | None) -> list[Waypoint]:
            events.append(f"search:{capture_dir}")
            return [
                Waypoint(north=761.0, east=264.0, height=45.7),
                Waypoint(north=834.0, east=331.0, height=45.7),
            ]

        delivered: list[tuple[float, float, float]] = []

        async def record_fly(drone, n, e, h):
            delivered.append((n, e, h))

        runner = MissionRunner(
            drone=Mock(),
            config=config,
            takeoff_fn=AsyncMock(),
            fly_to_fn=record_fly,
            land_at_fn=AsyncMock(),
            loiter_fn=AsyncMock(),
            battery_fn=AsyncMock(return_value=100.0),
            log_fn=lambda _msg: None,
            capture_controller=FakeCapture(),
            search_fn=fake_search,
        )
        await runner.run()
        self.assertEqual(runner.state.phase, MissionPhase.COMPLETED)
        self.assertEqual(events, ["capture_start", "capture_stop", "search:/tmp/fake_capture"])
        # Last 3 fly_to calls are the 2 detected deliveries + 1 return to base
        self.assertEqual(delivered[-3:-1], [(761.0, 264.0, 45.7), (834.0, 331.0, 45.7)])

        # Verify capture_stop still runs if an abort fires mid-survey
        events.clear()
        config2 = create_default_mission()
        runner2 = MissionRunner(
            drone=Mock(),
            config=config2,
            takeoff_fn=AsyncMock(),
            fly_to_fn=AsyncMock(),
            land_at_fn=AsyncMock(),
            loiter_fn=AsyncMock(),
            battery_fn=AsyncMock(return_value=100.0),
            log_fn=lambda _msg: None,
            capture_controller=FakeCapture(),
        )

        async def abort_in_survey(drone, n, e, h):
            if runner2.state.phase == MissionPhase.SURVEY:
                runner2.request_abort("Simulated mid-survey abort")

        runner2.fly_to_fn = abort_in_survey
        await runner2.run()
        self.assertEqual(runner2.state.phase, MissionPhase.ABORTED)
        self.assertEqual(events, ["capture_start", "capture_stop"])

    def test_mapping_sitl_mission_and_foxglove_scene_load(self) -> None:
        cfg = MissionConfig.from_json_file(REPO_ROOT / "missions" / "mapping_sitl.json")
        self.assertIsNotNone(cfg.camera)
        self.assertTrue(cfg.auto_plan_survey)
        cam_cfg = CameraConfig.from_dict(cfg.camera)
        self.assertEqual(cam_cfg.source, "gazebo")

        scene_update = build_site_scene_update(
            REPO_ROOT / "worlds" / "suas_site" / "scene.json",
            REPO_ROOT / "worlds" / "suas_site" / "dem.npz",
        )
        self.assertIsNotNone(scene_update)
        encoded = scene_update.encode()
        self.assertIn(b"search_boundary", encoded)
        self.assertIn(b"site_terrain", encoded)
        self.assertIn(b"site_objects", encoded)


if __name__ == "__main__":
    unittest.main()
