#!/usr/bin/env python3
"""Autonomous mission loop and state machine for SUAS 26-27.

Adheres to:
  - MAST-L2-ASW-01: Full mission autonomous sequencing (Takeoff to Land).
  - MAST-L2-ASW-02: Task ordering enforcement (Laps -> Survey -> Search -> Delivery).
  - MAST-L2-ASW-03: Search Boundary exclusion zone (25 m buffer) during laps.
  - MAST-L2-ASW-04: Completed lap tracking and GCS reporting.
  - MAST-L2-ASW-13: Per-phase safe operator abort to loiter.
  - MAST-L2-ASW-14: Tunable mission parameters exportable/importable.
  - MAST-L2-ASW-16: Rapid field import for Flight Lines 1 & 2.
  - MAST-L2-ASW-17: Autonomous lap phase curtailment on < 20% battery reserve.
  - MAST-L2-ASW-18: Timestamped transition logging.
  - MAST-L2-ASW-19: Unambiguous mission phase reporting.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import math
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Optional,
    TypedDict,
    Union,
)

if TYPE_CHECKING:
    from drone_control import Drone


# ----- Type Aliases & Typed Dictionaries -----

TakeoffFn = Callable[[Any, float], Awaitable[None]]
FlyToFn = Callable[[Any, float, float, float], Awaitable[None]]
LandAtFn = Callable[[Any, float, float, float], Awaitable[None]]
LoiterFn = Callable[[Any], Awaitable[None]]
BatteryFn = Callable[[], Awaitable[float]]
LogFn = Callable[[str], None]


class WaypointDict(TypedDict):
    """Dictionary structure for a single waypoint."""

    north: float
    east: float
    height: float


class SearchBoundaryDict(TypedDict):
    """Dictionary structure for a search boundary."""

    min_north: float
    max_north: float
    min_east: float
    max_east: float
    buffer_m: float


class MissionConfigDict(TypedDict):
    """Dictionary structure for a full mission configuration."""

    name: str
    takeoff_height: float
    target_laps: int
    min_battery_pct: float
    lap_waypoints: list[WaypointDict]
    survey_waypoints: list[WaypointDict]
    delivery_waypoints: list[WaypointDict]
    search_boundary: Optional[SearchBoundaryDict]
    landing_north: float
    landing_east: float
    landing_runway_heading_deg: float


class TransitionRecordDict(TypedDict):
    """Dictionary structure for a transition record."""

    timestamp: str
    from_phase: str
    to_phase: str
    reason: str


class MissionStatusDict(TypedDict):
    """Dictionary structure representing instantaneous mission status."""

    phase: str
    completed_laps: int
    target_laps: int
    lap_locked: bool
    battery_pct: float
    current_waypoint_index: int
    abort_requested: bool
    abort_reason: Optional[str]


# ----- Class Declarations -----

class MissionPhase(str, Enum):
    """Discrete, unambiguous mission phases as defined in the SUAS ASW spec."""

    IDLE = "IDLE"
    TAKEOFF = "TAKEOFF"
    TRANSITION_TO_CRUISE = "TRANSITION_TO_CRUISE"
    WAYPOINT_LAPS = "WAYPOINT_LAPS"
    SURVEY = "SURVEY"  # Lawnmower mapping pattern over Search Boundary
    SEARCH = "SEARCH"
    DELIVERY = "DELIVERY"
    RETURN = "RETURN"
    TRANSITION_TO_HOVER = "TRANSITION_TO_HOVER"
    LANDING = "LANDING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


@dataclass
class TransitionRecord:
    """Timestamped record of a mission phase transition (MAST-L2-ASW-18)."""

    timestamp: str
    from_phase: MissionPhase
    to_phase: MissionPhase
    reason: str

    def to_dict(self) -> TransitionRecordDict:
        return {
            "timestamp": self.timestamp,
            "from_phase": self.from_phase.value,
            "to_phase": self.to_phase.value,
            "reason": self.reason,
        }


@dataclass
class Waypoint:
    """Waypoint relative to home in meters, with height above home in meters."""

    north: float
    east: float
    height: float = 50.0

    def to_dict(self) -> WaypointDict:
        """Serialize waypoint to a dictionary."""
        return {"north": self.north, "east": self.east, "height": self.height}

    @classmethod
    def from_dict(cls: type[Waypoint], data: dict[str, Any] | WaypointDict) -> Waypoint:
        """Construct waypoint from a dictionary."""
        return cls(
            north=float(data["north"]),
            east=float(data["east"]),
            height=float(data.get("height", 50.0)),
        )


@dataclass
class SearchBoundary:
    """Search Boundary rectangle with a 25 m exclusion buffer (MAST-L2-ASW-03)."""

    min_north: float
    max_north: float
    min_east: float
    max_east: float
    buffer_m: float = 25.0

    def contains_point(self, north: float, east: float, include_buffer: bool = True) -> bool:
        """Check whether coordinates fall inside the boundary or its exclusion buffer."""
        buf: float = self.buffer_m if include_buffer else 0.0
        return (
            (self.min_north - buf) <= north <= (self.max_north + buf)
            and (self.min_east - buf) <= east <= (self.max_east + buf)
        )

    def to_dict(self) -> SearchBoundaryDict:
        """Serialize boundary to a dictionary."""
        return {
            "min_north": self.min_north,
            "max_north": self.max_north,
            "min_east": self.min_east,
            "max_east": self.max_east,
            "buffer_m": self.buffer_m,
        }

    @classmethod
    def from_dict(cls: type[SearchBoundary], data: dict[str, Any] | SearchBoundaryDict) -> SearchBoundary:
        """Construct boundary from a dictionary."""
        return cls(
            min_north=float(data["min_north"]),
            max_north=float(data["max_north"]),
            min_east=float(data["min_east"]),
            max_east=float(data["max_east"]),
            buffer_m=float(data.get("buffer_m", 25.0)),
        )


@dataclass
class MissionConfig:
    """Full mission parameter configuration (MAST-L2-ASW-14)."""

    name: str = "default_mission"
    takeoff_height: float = 50.0
    target_laps: int = 1  # 1 to 10 laps (L0-END-03)

    # threshold used to determine when to stop running laps 
    min_battery_pct: float = 20.0  # Reserve curtailment threshold (MAST-L2-ASW-17)
    lap_waypoints: list[Waypoint] = field(default_factory=list)
    survey_waypoints: list[Waypoint] = field(default_factory=list)  # Lawnmower pattern
    delivery_waypoints: list[Waypoint] = field(default_factory=list)
    search_boundary: Optional[SearchBoundary] = None
    landing_north: float = 0.0
    landing_east: float = 0.0
    landing_runway_heading_deg: float = 0.0

    def validate(self) -> None:
        """Validate config parameters against competition and safety rules."""
        if self.target_laps < 1:
            raise ValueError("target_laps must be at least 1")
        if self.target_laps > 10:
            raise ValueError("target_laps cannot exceed 10 laps (L0-END-03)")
        if not (30.0 <= self.takeoff_height <= 150.0):
            raise ValueError("takeoff_height must be between 30 and 150 m")

        # Verify lap waypoints do not breach Search Boundary 25 m buffer (MAST-L2-ASW-03)
        if self.search_boundary is not None and self.lap_waypoints:
            for idx, wp in enumerate(self.lap_waypoints):
                if self.search_boundary.contains_point(wp.north, wp.east, include_buffer=True):
                    raise ValueError(
                        f"Lap waypoint {idx} ({wp.north} N, {wp.east} E) breaches "
                        f"Search Boundary 25 m exclusion zone (MAST-L2-ASW-03)"
                    )

    def get_waypoints_for_phase(self, phase: MissionPhase | str) -> list[Waypoint]:
        """Return the waypoints configured for a specific mission phase."""
        if isinstance(phase, str):
            try:
                phase = MissionPhase(phase)
            except ValueError:
                return []
        phase_map: dict[MissionPhase, list[Waypoint]] = {
            MissionPhase.WAYPOINT_LAPS: self.lap_waypoints,
            MissionPhase.SURVEY: self.survey_waypoints,
            MissionPhase.DELIVERY: self.delivery_waypoints,
        }
        return phase_map.get(phase, [])

    def to_dict(self) -> MissionConfigDict:
        """Serialize configuration to a dictionary."""
        return {
            "name": self.name,
            "takeoff_height": self.takeoff_height,
            "target_laps": self.target_laps,
            "min_battery_pct": self.min_battery_pct,
            "lap_waypoints": [wp.to_dict() for wp in self.lap_waypoints],
            "survey_waypoints": [wp.to_dict() for wp in self.survey_waypoints],
            "delivery_waypoints": [wp.to_dict() for wp in self.delivery_waypoints],
            "search_boundary": self.search_boundary.to_dict() if self.search_boundary else None,
            "landing_north": self.landing_north,
            "landing_east": self.landing_east,
            "landing_runway_heading_deg": self.landing_runway_heading_deg,
        }

    @classmethod
    def from_dict(cls: type[MissionConfig], data: dict[str, Any] | MissionConfigDict) -> MissionConfig:
        """Construct configuration from a dictionary."""
        boundary_raw = data.get("search_boundary")
        boundary = SearchBoundary.from_dict(boundary_raw) if boundary_raw else None
        return cls(
            name=str(data.get("name", "mission")),
            takeoff_height=float(data.get("takeoff_height", 50.0)),
            target_laps=int(data.get("target_laps", 1)),
            min_battery_pct=float(data.get("min_battery_pct", 20.0)),
            lap_waypoints=[Waypoint.from_dict(wp) for wp in data.get("lap_waypoints", [])],
            survey_waypoints=[Waypoint.from_dict(wp) for wp in data.get("survey_waypoints", [])],
            delivery_waypoints=[Waypoint.from_dict(wp) for wp in data.get("delivery_waypoints", [])],
            search_boundary=boundary,
            landing_north=float(data.get("landing_north", 0.0)),
            landing_east=float(data.get("landing_east", 0.0)),
            landing_runway_heading_deg=float(data.get("landing_runway_heading_deg", 0.0)),
        )

    def to_json_file(self, path: str | Path) -> None:
        """Write mission config to JSON file (MAST-L2-ASW-14)."""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_json_file(cls: type[MissionConfig], path: str | Path) -> MissionConfig:
        """Load mission config from JSON file (MAST-L2-ASW-16)."""
        file_path = Path(path)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = cls.from_dict(data)
        cfg.validate()
        return cfg


@dataclass
class MissionState:
    """Runtime tracking of mission progress and telemetry."""

    phase: MissionPhase = MissionPhase.IDLE
    completed_laps: int = 0
    lap_locked: bool = False  # Irreversible lock per L0-END-05#
    # prevents the bot from trying to complete more laps after we entered the search boundary
    # and stops loops from being counted when we're just doing searches

    battery_pct: float = 100.0
    current_waypoint_index: int = 0
    abort_requested: bool = False
    abort_reason: Optional[str] = None
    transition_log: list[TransitionRecord] = field(default_factory=list)


class MissionRunner:
    """State machine controller executing the autonomous mission lifecycle."""

    def __init__(
        self,
        drone: Union[Drone, Any],
        config: MissionConfig,
        takeoff_fn: Optional[TakeoffFn] = None,
        fly_to_fn: Optional[FlyToFn] = None,
        land_at_fn: Optional[LandAtFn] = None,
        loiter_fn: Optional[LoiterFn] = None,
        battery_fn: Optional[BatteryFn] = None,
        log_fn: Optional[LogFn] = None,
    ) -> None:
        self.drone: Union[Drone, Any] = drone
        self.config: MissionConfig = config
        self.state: MissionState = MissionState()

        # If flight functions are not injected, import defaults from drone_control
        if takeoff_fn is None or fly_to_fn is None or land_at_fn is None or loiter_fn is None:
            import drone_control

            self.takeoff_fn: TakeoffFn = takeoff_fn or drone_control.takeoff
            self.fly_to_fn: FlyToFn = fly_to_fn or drone_control.fly_to
            self.land_at_fn: LandAtFn = land_at_fn or drone_control.land_at
            self.loiter_fn: LoiterFn = loiter_fn or drone_control.loiter
        else:
            self.takeoff_fn = takeoff_fn
            self.fly_to_fn = fly_to_fn
            self.land_at_fn = land_at_fn
            self.loiter_fn = loiter_fn

        self.battery_fn: Optional[BatteryFn] = battery_fn
        self.log_fn: LogFn = log_fn or print

    def log(self, message: str) -> None:
        """Format and emit a mission log entry."""
        self.log_fn(f"[MISSION {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}")

    def transition_to(self, new_phase: MissionPhase, reason: str = "") -> None:
        """Validate and apply a state transition with logging (MAST-L2-ASW-18)."""
        current = self.state.phase

        # Rule check: cannot re-enter WAYPOINT_LAPS once lap count has locked (L0-END-05)
        if new_phase == MissionPhase.WAYPOINT_LAPS and self.state.lap_locked:
            raise RuntimeError("Cannot re-enter WAYPOINT_LAPS: lap count is locked (L0-END-05)")

        record = TransitionRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            from_phase=current,
            to_phase=new_phase,
            reason=reason,
        )
        self.state.transition_log.append(record)
        self.state.phase = new_phase
        self.log(f"Phase transition: {current.value} -> {new_phase.value} (reason: {reason})")

    def request_abort(self, reason: str = "Operator abort") -> None:
        """Trigger an immediate safe autonomous abort to loiter (MAST-L2-ASW-13)."""
        self.state.abort_requested = True
        self.state.abort_reason = reason
        self.log(f"Abort requested: {reason}")

    def get_status(self) -> MissionStatusDict:
        """Return unambiguous mission status representation (MAST-L2-ASW-19, MAST-L2-GCS-04)."""
        return {
            "phase": self.state.phase.value,
            "completed_laps": self.state.completed_laps,
            "target_laps": self.config.target_laps,
            "lap_locked": self.state.lap_locked,
            "battery_pct": round(self.state.battery_pct, 1),
            "current_waypoint_index": self.state.current_waypoint_index,
            "abort_requested": self.state.abort_requested,
            "abort_reason": self.state.abort_reason,
        }

    async def _update_battery(self) -> float:
        """Fetch latest battery percentage from telemetry if available."""
        # typically, battery_fn is None, but we can inject func
        # to use during unit testing w/o sitl env
        if self.battery_fn is not None:
            try:
                pct = await self.battery_fn()
                self.state.battery_pct = pct
                return pct
            except Exception as err:
                self.log(f"Telemetry warning: failed to read battery: {err}")
        elif hasattr(self.drone, "telemetry") and hasattr(self.drone.telemetry, "subscribe_battery"):
            try:
                # Read one sample with 1s timeout
                stream = self.drone.telemetry.subscribe_battery()
                async for batt in stream:
                    if hasattr(batt, "remaining_percent") and batt.remaining_percent is not None:
                        self.state.battery_pct = batt.remaining_percent * 100.0
                    break
            except Exception:
                pass
        return self.state.battery_pct

    async def _fly_waypoint_list(self, waypoints: list[Waypoint], phase_name: str) -> bool:
        """Fly a sequence of waypoints, checking abort and battery each step."""
        for idx, wp in enumerate(waypoints):
            if self.state.abort_requested:
                return False

            self.state.current_waypoint_index = idx
            self.log(f"{phase_name} WP {idx + 1}/{len(waypoints)} -> {wp.north}m N, {wp.east}m E, {wp.height}m H")
            await self.fly_to_fn(self.drone, wp.north, wp.east, wp.height)

            # Check battery
            batt = await self._update_battery()
            if batt < self.config.min_battery_pct:
                self.log(f"Battery reserve alert: {batt:.1f}% <= {self.config.min_battery_pct:.1f}%")

        return True

    def get_waypoints_for_phase(self, phase: MissionPhase | str) -> list[Waypoint]:
        """Read waypoints from config for the given mission phase."""
        return self.config.get_waypoints_for_phase(phase)

    async def _execute_waypoint_phase(
        self,
        phase: MissionPhase,
        reason: str = "",
        waypoints: Optional[list[Waypoint]] = None,
        phase_name: Optional[str] = None,
    ) -> bool:
        """Change phase, resolve waypoints from config, fly them, and handle aborts.

        Args:
            phase: MissionPhase to transition to.
            reason: Optional description for the phase transition log.
            waypoints: Optional explicit waypoint sequence. If None, waypoints are
                       read from the mission config based on the phase.
            phase_name: Optional label for logging (e.g. "Survey", "Delivery").
                        Defaults to title-cased phase name ("Lap" for WAYPOINT_LAPS).

        Returns:
            True if waypoints were completed successfully without abort; False otherwise.
        """
        if self.state.abort_requested:
            await self._handle_abort()
            return False

        if not reason:
            reason = f"Beginning {phase.value} phase"
        self.transition_to(phase, reason=reason)

        if self.state.abort_requested:
            await self._handle_abort()
            return False

        if waypoints is None:
            waypoints = self.get_waypoints_for_phase(phase)

        if phase_name is None:
            if phase == MissionPhase.WAYPOINT_LAPS:
                phase_name = "Lap"
            else:
                phase_name = phase.value.replace("_", " ").title()

        if waypoints:
            completed_ok = await self._fly_waypoint_list(waypoints, phase_name)
            if not completed_ok or self.state.abort_requested:
                await self._handle_abort()
                return False
        else:
            self.log(f"No {phase_name.lower()} waypoints configured; advancing.")

        if self.state.abort_requested:
            await self._handle_abort()
            return False

        return True

    # Method aliases for flexibility and clean external/internal access
    execute_waypoint_phase = _execute_waypoint_phase
    run_waypoint_phase = _execute_waypoint_phase
    _run_waypoint_phase = _execute_waypoint_phase

    async def run(self) -> None:
        """Execute the full autonomous mission loop (MAST-L2-ASW-01)."""
        self.config.validate()

        try:
            # 1. TAKEOFF
            self.transition_to(MissionPhase.TAKEOFF, reason="Autonomous mission start command")
            await self.takeoff_fn(self.drone, self.config.takeoff_height)

            if self.state.abort_requested:
                await self._handle_abort()
                return

            # 2. TRANSITION TO CRUISE
            self.transition_to(MissionPhase.TRANSITION_TO_CRUISE, reason="Takeoff climbout completed")
            # For fixed-wing/SITL transition is instantaneous; tailsitters would rotate body here.
            await asyncio.sleep(0.5)

            if self.state.abort_requested:
                await self._handle_abort()
                return

            # 3. WAYPOINT LAPS
            self.transition_to(MissionPhase.WAYPOINT_LAPS, reason="Beginning endurance laps")
            lap_curtailed = False

            while self.state.completed_laps < self.config.target_laps:
                if self.state.abort_requested:
                    await self._handle_abort()
                    return

                # Check energy before starting a new lap (MAST-L2-ASW-17)
                batt = await self._update_battery()
                if batt < self.config.min_battery_pct:
                    self.log(
                        f"Curtailing lap phase: battery {batt:.1f}% is below {self.config.min_battery_pct:.1f}% reserve threshold (MAST-L2-ASW-17)"
                    )
                    lap_curtailed = True
                    break

                self.log(f"Starting Lap {self.state.completed_laps + 1} of {self.config.target_laps}")
                completed_ok = await self._fly_waypoint_list(self.config.lap_waypoints, "Lap")
                if not completed_ok or self.state.abort_requested:
                    await self._handle_abort()
                    return

                self.state.completed_laps += 1
                self.log(f"Completed Lap {self.state.completed_laps}/{self.config.target_laps}")

            # Permanently lock lap count upon exiting lap phase (L0-END-05)
            self.state.lap_locked = True
            lock_reason = "Curtailment due to energy reserve" if lap_curtailed else "Target laps completed"
            self.log(f"Lap count locked permanently at {self.state.completed_laps} (L0-END-05: {lock_reason})")

            # 4. SURVEY (Lawnmower pattern)
            if self.state.completed_laps < 1:
                # Rule L0-MSN-04: At least 1 lap must be completed before entering Search Boundary
                # TODO: Go back and try to do laps if none completed
                self.log("Skipping SURVEY phase: 0 laps completed (L0-MSN-04 requires at least 1 lap)")
            else:
                if not await self._execute_waypoint_phase(
                    MissionPhase.SURVEY,
                    reason="Laps complete; beginning lawnmower survey",
                ):
                    return

            # 5. SEARCH
            if self.state.completed_laps >= 1 and not self.state.abort_requested:
                self.transition_to(MissionPhase.SEARCH, reason="Survey complete; searching for targets")

                # TODO: gather camera data from survey, feed into CV model to find person and shelter
                # then, geolocate positions and set those to delivery_waypoints

            # 6. DELIVERY
            if self.state.completed_laps < 1:
                # Rule L0-SDD-09: Must complete >= 1 lap before any delivery
                self.log("Skipping DELIVERY phase: 0 laps completed (L0-SDD-09 requires at least 1 lap)")
            elif not self.state.abort_requested:
                if not await self._execute_waypoint_phase(
                    MissionPhase.DELIVERY,
                    reason="Targets declared; proceeding to deliveries",
                ):
                    return

            # 7. RETURN
            if not self.state.abort_requested:
                self.transition_to(MissionPhase.RETURN, reason="All mission tasks finished; returning to base")
                await self.fly_to_fn(
                    self.drone,
                    self.config.landing_north,
                    self.config.landing_east,
                    self.config.takeoff_height,
                )

            # 8. TRANSITION TO HOVER
            if not self.state.abort_requested:
                self.transition_to(MissionPhase.TRANSITION_TO_HOVER, reason="Over landing pad; transitioning to hover")
                await asyncio.sleep(0.5)
                
            # 9. LANDING
            if not self.state.abort_requested:
                self.transition_to(MissionPhase.LANDING, reason="Autonomous landing approach initiated")
                await self.land_at_fn(
                    self.drone,
                    self.config.landing_north,
                    self.config.landing_east,
                    self.config.landing_runway_heading_deg,
                )

            # 10. COMPLETED
            if not self.state.abort_requested:
                self.transition_to(MissionPhase.COMPLETED, reason="Touchdown and disarm confirmed")
                self.log("Mission complete! Ready for deliverable submission.")

        except Exception as error:
            self.log(f"Mission execution error: {error}")
            self.request_abort(f"Error: {error}")
            await self._handle_abort()
            raise

    async def _handle_abort(self) -> None:
        """Handle abort transition and enter safe holding pattern (MAST-L2-ASW-13)."""
        if self.state.phase != MissionPhase.ABORTED:
            self.transition_to(MissionPhase.ABORTED, reason=self.state.abort_reason or "Abort requested")
        self.log("Aircraft entering safe autonomous loiter...")
        await self.loiter_fn(self.drone)


def create_default_mission() -> MissionConfig:
    """Create a default mission specification with sample waypoints."""
    # Default 500m square lap
    lap: list[Waypoint] = [
        Waypoint(north=0.0, east=500.0, height=50.0),
        Waypoint(north=500.0, east=500.0, height=50.0),
        Waypoint(north=500.0, east=0.0, height=50.0),
        Waypoint(north=0.0, east=0.0, height=50.0),
    ]
    # Search boundary located further north (e.g. 700 to 900m N, 200 to 400m E)
    boundary = SearchBoundary(
        min_north=700.0,
        max_north=900.0,
        min_east=200.0,
        max_east=400.0,
        buffer_m=25.0,
    )
    # Lawnmower pattern inside search boundary
    survey: list[Waypoint] = [
        Waypoint(north=720.0, east=220.0, height=50.0),
        Waypoint(north=880.0, east=220.0, height=50.0),
        Waypoint(north=880.0, east=270.0, height=50.0),
        Waypoint(north=720.0, east=270.0, height=50.0),
        Waypoint(north=720.0, east=320.0, height=50.0),
        Waypoint(north=880.0, east=320.0, height=50.0),
    ]
    # Delivery target drops (mannequin at WP1, tent at WP2)
    delivery: list[Waypoint] = [
        Waypoint(north=750.0, east=250.0, height=45.7),
        Waypoint(north=850.0, east=350.0, height=45.7),
    ]

    return MissionConfig(
        name="default_mission",
        takeoff_height=50.0,
        target_laps=1,
        min_battery_pct=20.0,
        lap_waypoints=lap,
        survey_waypoints=survey,
        delivery_waypoints=delivery,
        search_boundary=boundary,
        landing_north=0.0,
        landing_east=0.0,
        landing_runway_heading_deg=0.0,
    )
