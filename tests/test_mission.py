"""Comprehensive unit tests for the SUAS 26-27 autonomous mission loop and state machine."""

import asyncio
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from mission import (
    MissionConfig,
    MissionPhase,
    MissionRunner,
    SearchBoundary,
    Waypoint,
    create_default_mission,
)


class TestMissionLoop(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.takeoff_mock = AsyncMock()
        self.fly_to_mock = AsyncMock()
        self.land_at_mock = AsyncMock()
        self.loiter_mock = AsyncMock()
        self.log_messages: list[str] = []

        def log_capture(msg: str) -> None:
            self.log_messages.append(msg)

        self.log_capture = log_capture

    def _create_runner(
        self,
        config: MissionConfig,
        battery_pct: float = 100.0,
    ) -> tuple[MissionRunner, Mock]:
        mock_drone = Mock()
        battery_mock = AsyncMock(return_value=battery_pct)

        runner = MissionRunner(
            drone=mock_drone,
            config=config,
            takeoff_fn=self.takeoff_mock,
            fly_to_fn=self.fly_to_mock,
            land_at_fn=self.land_at_mock,
            loiter_fn=self.loiter_mock,
            battery_fn=battery_mock,
            log_fn=self.log_capture,
        )
        return runner, battery_mock

    async def test_nominal_mission_executes_all_phases_in_order(self) -> None:
        """MAST-L2-ASW-01: Verify nominal autonomous sequence from takeoff to landing."""
        config = create_default_mission()
        config.target_laps = 1
        runner, _ = self._create_runner(config)

        await runner.run()

        # Check final phase
        self.assertEqual(runner.state.phase, MissionPhase.COMPLETED)
        self.assertEqual(runner.state.completed_laps, 1)
        self.assertTrue(runner.state.lap_locked)

        # Verify phase progression in transition log (MAST-L2-ASW-18)
        recorded_phases = [rec.to_phase for rec in runner.state.transition_log]
        expected_sequence = [
            MissionPhase.TAKEOFF,
            MissionPhase.TRANSITION_TO_CRUISE,
            MissionPhase.WAYPOINT_LAPS,
            MissionPhase.SURVEY,
            MissionPhase.SEARCH,
            MissionPhase.DELIVERY,
            MissionPhase.RETURN,
            MissionPhase.TRANSITION_TO_HOVER,
            MissionPhase.LANDING,
            MissionPhase.COMPLETED,
        ]
        self.assertEqual(recorded_phases, expected_sequence)

        # Verify SDK commands were called
        self.takeoff_mock.assert_awaited_once_with(runner.drone, 50.0)
        self.land_at_mock.assert_awaited_once_with(runner.drone, 0.0, 0.0, 0.0)
        self.loiter_mock.assert_not_called()

        # Check total waypoints flown:
        # 4 lap waypoints + 6 survey waypoints + 2 delivery waypoints + 1 return waypoint = 13
        self.assertEqual(self.fly_to_mock.await_count, 13)

    async def test_lap_counting_and_multi_lap_execution(self) -> None:
        """MAST-L2-ASW-04: Test tracking multiple laps and advancing only when target is met."""
        config = create_default_mission()
        config.target_laps = 3
        runner, _ = self._create_runner(config)

        await runner.run()

        self.assertEqual(runner.state.completed_laps, 3)
        self.assertTrue(runner.state.lap_locked)

        # Lap waypoints (4 per lap * 3 laps = 12) + 6 survey + 2 delivery + 1 return = 21
        self.assertEqual(self.fly_to_mock.await_count, 21)

    async def test_search_boundary_exclusion_zone_validation(self) -> None:
        """MAST-L2-ASW-03: Lap waypoints within Search Boundary 25m buffer must be rejected."""
        boundary = SearchBoundary(
            min_north=500.0,
            max_north=700.0,
            min_east=500.0,
            max_east=700.0,
            buffer_m=25.0,
        )
        # Point inside the buffer (north=480, east=500 -> distance is 20m from min_north 500, within 25m buffer)
        breaching_wp = Waypoint(north=480, east=500, height=50)
        safe_wp = Waypoint(north=400, east=500, height=50)

        cfg_breaching = MissionConfig(
            lap_waypoints=[breaching_wp],
            search_boundary=boundary,
        )
        with self.assertRaises(ValueError) as ctx:
            cfg_breaching.validate()
        self.assertIn("breaches Search Boundary 25 m exclusion zone", str(ctx.exception))

        cfg_safe = MissionConfig(
            lap_waypoints=[safe_wp],
            search_boundary=boundary,
        )
        # Safe config should not raise
        cfg_safe.validate()

    async def test_energy_curtailment_stops_laps_early(self) -> None:
        """MAST-L2-ASW-17: When battery reserve falls below 20%, curtail lap phase."""
        config = create_default_mission()
        config.target_laps = 5
        config.min_battery_pct = 20.0

        # Simulate battery dropping: starts at 50%, then drops to 15% after lap 1
        call_count = 0

        async def battery_decay() -> float:
            nonlocal call_count
            call_count += 1
            if call_count <= 4:
                return 50.0
            return 15.0  # Under 20% threshold

        mock_drone = Mock()
        runner = MissionRunner(
            drone=mock_drone,
            config=config,
            takeoff_fn=self.takeoff_mock,
            fly_to_fn=self.fly_to_mock,
            land_at_fn=self.land_at_mock,
            loiter_fn=self.loiter_mock,
            battery_fn=battery_decay,
            log_fn=self.log_capture,
        )

        await runner.run()

        # Should have stopped laps early (1 lap completed instead of 5)
        self.assertEqual(runner.state.completed_laps, 1)
        self.assertTrue(runner.state.lap_locked)
        # Should still proceed to survey and safely complete the mission
        self.assertEqual(runner.state.phase, MissionPhase.COMPLETED)
        self.assertTrue(any("Curtailing lap phase: battery" in msg for msg in self.log_messages))

    async def test_delivery_and_survey_skipped_if_zero_laps_completed(self) -> None:
        """MAST-L2-ASW-02, L0-MSN-04, L0-SDD-09: Must complete >= 1 lap before survey/delivery."""
        config = create_default_mission()
        config.target_laps = 2

        # Simulate immediate battery drain before completing lap 1
        async def low_battery() -> float:
            return 10.0

        mock_drone = Mock()
        runner = MissionRunner(
            drone=mock_drone,
            config=config,
            takeoff_fn=self.takeoff_mock,
            fly_to_fn=self.fly_to_mock,
            land_at_fn=self.land_at_mock,
            loiter_fn=self.loiter_mock,
            battery_fn=low_battery,
            log_fn=self.log_capture,
        )

        await runner.run()

        self.assertEqual(runner.state.completed_laps, 0)
        self.assertTrue(runner.state.lap_locked)

        # SURVEY and DELIVERY should not be present in transitions
        transition_phases = [rec.to_phase for rec in runner.state.transition_log]
        self.assertNotIn(MissionPhase.SURVEY, transition_phases)
        self.assertNotIn(MissionPhase.DELIVERY, transition_phases)
        # Should proceed directly to RETURN, TRANSITION_TO_HOVER, and LANDING
        self.assertIn(MissionPhase.RETURN, transition_phases)
        self.assertIn(MissionPhase.LANDING, transition_phases)

    async def test_lap_lock_is_irreversible(self) -> None:
        """L0-END-05: Cannot re-enter WAYPOINT_LAPS once lap count has locked."""
        config = create_default_mission()
        runner, _ = self._create_runner(config)

        runner.state.lap_locked = True
        with self.assertRaises(RuntimeError) as ctx:
            runner.transition_to(MissionPhase.WAYPOINT_LAPS, reason="Illegal re-entry")
        self.assertIn("lap count is locked", str(ctx.exception))

    async def test_operator_abort_transitions_to_loiter(self) -> None:
        """MAST-L2-ASW-13: Per-phase autonomous abort immediately halts navigation to loiter."""
        config = create_default_mission()
        runner, _ = self._create_runner(config)

        # When the first waypoint is reached, trigger an abort
        async def fly_to_with_abort(drone, n, e, h):
            runner.request_abort("Manual safety pilot trigger")

        runner.fly_to_fn = fly_to_with_abort

        await runner.run()

        self.assertEqual(runner.state.phase, MissionPhase.ABORTED)
        self.assertTrue(runner.state.abort_requested)
        self.assertEqual(runner.state.abort_reason, "Manual safety pilot trigger")
        self.loiter_mock.assert_awaited_once_with(runner.drone)
        self.land_at_mock.assert_not_called()

    async def test_unambiguous_phase_reporting(self) -> None:
        """MAST-L2-ASW-19, MAST-L2-GCS-04: Single unambiguous status dict."""
        config = create_default_mission()
        runner, _ = self._create_runner(config)

        status = runner.get_status()
        self.assertEqual(status["phase"], "IDLE")
        self.assertEqual(status["completed_laps"], 0)
        self.assertEqual(status["target_laps"], 1)
        self.assertFalse(status["lap_locked"])
        self.assertFalse(status["abort_requested"])

        runner.transition_to(MissionPhase.WAYPOINT_LAPS, reason="testing")
        status = runner.get_status()
        self.assertEqual(status["phase"], "WAYPOINT_LAPS")

    async def test_json_mission_config_roundtrip_and_loading(self) -> None:
        """MAST-L2-ASW-14, MAST-L2-ASW-16: JSON export, import, and validation."""
        config = create_default_mission()
        tmp_file = Path("/tmp/test_mission_export.json")

        try:
            config.to_json_file(tmp_file)
            loaded = MissionConfig.from_json_file(tmp_file)

            self.assertEqual(loaded.name, config.name)
            self.assertEqual(loaded.takeoff_height, config.takeoff_height)
            self.assertEqual(loaded.target_laps, config.target_laps)
            self.assertEqual(len(loaded.lap_waypoints), len(config.lap_waypoints))
            self.assertEqual(len(loaded.survey_waypoints), len(config.survey_waypoints))
            self.assertIsNotNone(loaded.search_boundary)
            self.assertEqual(loaded.search_boundary.buffer_m, 25.0)
        finally:
            if tmp_file.exists():
                tmp_file.unlink()

    def test_saved_flight_lines_load_and_validate(self) -> None:
        """MAST-L2-ASW-16: Verify flight_line_1.json and flight_line_2.json load cleanly."""
        for filename in ("default_mission.json", "flight_line_1.json", "flight_line_2.json"):
            path = Path(__file__).resolve().parents[1] / "missions" / filename
            self.assertTrue(path.exists(), f"{filename} does not exist")
            cfg = MissionConfig.from_json_file(path)
            self.assertGreater(len(cfg.lap_waypoints), 0)
            self.assertGreater(len(cfg.survey_waypoints), 0)
            self.assertIsNotNone(cfg.search_boundary)

    def test_get_waypoints_for_phase(self) -> None:
        """Verify retrieving waypoints from config based on the mission phase."""
        config = create_default_mission()
        self.assertEqual(config.get_waypoints_for_phase(MissionPhase.WAYPOINT_LAPS), config.lap_waypoints)
        self.assertEqual(config.get_waypoints_for_phase(MissionPhase.SURVEY), config.survey_waypoints)
        self.assertEqual(config.get_waypoints_for_phase(MissionPhase.DELIVERY), config.delivery_waypoints)
        self.assertEqual(config.get_waypoints_for_phase(MissionPhase.TAKEOFF), [])
        self.assertEqual(config.get_waypoints_for_phase("SURVEY"), config.survey_waypoints)
        self.assertEqual(config.get_waypoints_for_phase("INVALID_PHASE"), [])

    async def test_execute_waypoint_phase_nominal_and_empty(self) -> None:
        """Verify _execute_waypoint_phase transitions, reads waypoints, and flies them."""
        config = create_default_mission()
        runner, _ = self._create_runner(config)

        # Test nominal execution reading from config
        success = await runner.execute_waypoint_phase(MissionPhase.SURVEY, reason="Testing survey phase")
        self.assertTrue(success)
        self.assertEqual(runner.state.phase, MissionPhase.SURVEY)
        self.assertEqual(self.fly_to_mock.await_count, len(config.survey_waypoints))

        # Test phase with no waypoints configured
        config.delivery_waypoints = []
        fly_count_before = self.fly_to_mock.await_count
        success = await runner.execute_waypoint_phase(MissionPhase.DELIVERY, reason="Testing empty delivery")
        self.assertTrue(success)
        self.assertEqual(runner.state.phase, MissionPhase.DELIVERY)
        self.assertEqual(self.fly_to_mock.await_count, fly_count_before)
        self.assertTrue(any("No delivery waypoints configured; advancing." in msg for msg in self.log_messages))

    async def test_execute_waypoint_phase_abort_handling(self) -> None:
        """Verify abort handling before and during execute_waypoint_phase."""
        config = create_default_mission()
        runner, _ = self._create_runner(config)

        # Test abort before execution
        runner.request_abort("Abort prior to phase")
        success = await runner.execute_waypoint_phase(MissionPhase.SURVEY)
        self.assertFalse(success)
        self.assertEqual(runner.state.phase, MissionPhase.ABORTED)
        self.loiter_mock.assert_awaited_once_with(runner.drone)

        # Reset and test abort during flight
        runner2, _ = self._create_runner(config)

        async def fly_and_abort(drone, n, e, h):
            runner2.request_abort("Mid-flight abort")

        runner2.fly_to_fn = fly_and_abort
        success2 = await runner2.execute_waypoint_phase(MissionPhase.SURVEY)
        self.assertFalse(success2)
        self.assertEqual(runner2.state.phase, MissionPhase.ABORTED)
        self.loiter_mock.assert_awaited_with(runner2.drone)

    async def test_drone_control_run_mission_integration(self) -> None:
        """Verify drone_control.run_mission runs cleanly with JSON filepath."""
        from unittest.mock import patch
        import drone_control

        drone = Mock()
        mission_path = Path(__file__).resolve().parents[1] / "missions" / "default_mission.json"

        with patch.object(drone_control, "takeoff", AsyncMock()), \
             patch.object(drone_control, "fly_to", AsyncMock()), \
             patch.object(drone_control, "land_at", AsyncMock()), \
             patch.object(drone_control, "loiter", AsyncMock()):
            await drone_control.run_mission(drone, mission_path)


if __name__ == "__main__":
    unittest.main()
