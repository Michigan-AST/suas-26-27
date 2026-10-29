"""Checks for the student fixed-wing starter and its telemetry waits."""

import asyncio
import math
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace as State
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import drone_control as flight


def stream(*values):
    async def updates():
        for value in values:
            yield value
    return updates()


class StarterFlight(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.drone = State(
            action=State(**{name: AsyncMock() for name in (
                'goto_location', 'hold', 'set_takeoff_altitude', 'takeoff', 'arm',
            )}),
            telemetry=State(
                subscribe_home=lambda: stream(State(latitude_deg=47, longitude_deg=8, absolute_altitude_m=500)),
                subscribe_position=lambda: stream(),
            ),
            param=State(get_param_float=AsyncMock(return_value=80)),
        )

    async def test_sample_flies_a_closed_loop_after_takeoff(self):
        steps = []
        async def takeoff(drone, height):
            steps.append(('takeoff', height))
        async def fly_to(drone, north, east, height):
            steps.append((north, east, height))
        async def loiter(drone):
            steps.append(('loiter',))
        with patch.multiple(flight, takeoff=takeoff, fly_to=fly_to, loiter=loiter):
            await flight.flight_instructions(self.drone)
        self.assertEqual(steps[0], ('takeoff', 50))
        self.assertEqual(steps[-1], ('loiter',))
        corners = steps[1:-1]
        self.assertEqual(corners[0], corners[-1])
        self.assertEqual(len(set(corners)), 4)
        self.assertTrue(all(point[2] == 50 for point in corners))

    async def test_goto_converts_metres_and_height_to_gps_and_amsl(self):
        longitude = 8 + 500 / (math.pi * 6371000 / 180 * math.cos(math.radians(47)))
        self.drone.telemetry.subscribe_position = lambda: stream(
            State(latitude_deg=47, longitude_deg=8, absolute_altitude_m=550),
            State(latitude_deg=47, longitude_deg=longitude, absolute_altitude_m=550),
        )
        await flight.fly_to(self.drone, north=0, east=500, height=50)
        lat, lon, alt, yaw = self.drone.action.goto_location.call_args.args
        self.assertAlmostEqual(lat, 47)
        self.assertAlmostEqual(lon, longitude)
        self.assertEqual(alt, 550)
        self.assertTrue(math.isnan(yaw))

    async def test_invalid_targets_do_not_send_navigation(self):
        for north, east, height in [(math.nan, 0, 50), (0, 3000, 50), (0, 500, 5)]:
            with self.assertRaises(ValueError):
                await flight.fly_to(self.drone, north, east, height)
        self.drone.action.goto_location.assert_not_called()

    async def test_taking_off_requires_grounded_disarmed_aircraft(self):
        self.drone.telemetry.subscribe_armed = lambda: stream(True)
        self.drone.telemetry.subscribe_in_air = lambda: stream(True)
        with self.assertRaises(RuntimeError):
            await flight.takeoff(self.drone, height=50)
        self.drone.action.arm.assert_not_called()

    async def test_launch_mode_is_selected_before_arm_and_climb_is_observed(self):
        self.drone.telemetry.subscribe_armed = lambda: stream(False)
        self.drone.telemetry.subscribe_in_air = Mock(side_effect=[stream(False), stream(True)])
        self.drone.telemetry.subscribe_health = lambda: stream(State(
            is_global_position_ok=True, is_home_position_ok=True, is_armable=True,
        ))
        self.drone.telemetry.subscribe_position = lambda: stream(
            State(relative_altitude_m=5), State(relative_altitude_m=48),
        )
        steps = []
        self.drone.action.takeoff.side_effect = lambda: steps.append('takeoff_mode')
        self.drone.action.arm.side_effect = lambda: steps.append('arm')
        await flight.takeoff(self.drone, height=50)
        self.assertEqual(steps, ['takeoff_mode', 'arm'])

    async def test_timeout_closes_telemetry_subscription(self):
        closed = []
        async def stalled():
            try:
                yield False
                await asyncio.Event().wait()
            finally:
                closed.append(True)
        with self.assertRaises(asyncio.TimeoutError):
            await flight.wait_for(stalled(), lambda value: value, timeout=0.01)
        self.assertEqual(closed, [True])

    async def test_incomplete_telemetry_does_not_count_as_arrival(self):
        with self.assertRaises(RuntimeError):
            await flight.wait_for(stream(False), lambda value: value)

    async def test_wrong_vehicle_type_is_rejected(self):
        self.drone.mavlink_direct = State(subscribe_message=lambda name: stream(
            State(component_id=1, fields_json='{"autopilot":12,"type":2}'),
        ))
        with self.assertRaises(RuntimeError):
            await flight.check_aircraft(self.drone)


if __name__ == '__main__':
    unittest.main()
