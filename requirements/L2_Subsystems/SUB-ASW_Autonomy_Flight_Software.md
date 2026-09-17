# SUB-ASW — Autonomy and Flight Software Subsystem (L2)

**Scope.** Mission state machine, task sequencing, survey and search path planning, delivery
decision logic, onboard data pipeline orchestration, and the software configuration and
parameter management that supports design lock.

**Parent L1 requirements.** MAST-L1-13 (mission autonomy), MAST-L1-14 (two operators),
MAST-L1-20 (map production), MAST-L1-28 (onsite independence), MAST-L1-27 (configuration
control).

---

## Design-driving analysis

### Task order is constrained by rule, and the constraint is irreversible

The handbook imposes a strict ordering that the mission state machine must enforce, because
violating it silently forfeits points that cannot be recovered:

1. All waypoint laps the team intends to fly must be completed **before** entering the Search
   Boundary for either Risk Mapping or Search, Detect, and Deliver (L0-MSN-04).
2. The moment the aircraft enters the Search Boundary with the purpose of performing a task,
   **the lap count locks** and no further laps count (L0-END-05).
3. At least one full lap must precede any delivery, or deliveries score zero (L0-SDD-09).
4. Any manual takeover requires returning to the start of the lap (L0-PEN-06).

Point 2 is the dangerous one. An inadvertent clip of the Search Boundary during a lap — while
navigating with a 15.2 m acceptance radius and 5 m cross-track error — could be interpreted as
entering to perform a task, locking the lap count early. Since Flight Endurance scores as the
square of lap count, locking at 6 laps instead of 10 costs 128 points. The software must
therefore treat the Search Boundary as an exclusion zone during the lap phase, with margin.

### No human is available in flight

MAST-L1-14 permits exactly two operators, neither of whom may do anything but safety piloting
and autopilot supervision while airborne. There is nobody to run a stitching tool, nobody to
click on a target, nobody to pick a release point. Every step from image capture through map
production and target declaration to release-point computation must be automatic. This is the
single most consequential constraint on the software architecture and it comes from a scoring
rule, not from a technical preference.

### The clock runs until deliverables are submitted

Mission Time does not stop at touchdown; it stops when the runway is cleared, the airspace
relinquished, and deliverables submitted (L0-MSN-02), with overrun charged at 0.5% of mission
points per second (L0-PEN-01). At that rate, 60 seconds of post-landing map stitching costs 30%
of the mission score if the clock has already run out. The pipeline must therefore be
incremental — stitching as imagery arrives — rather than batch at the end.

---

## L2 — Subsystem requirements

| ID | Requirement | Parents | Rationale |
|---|---|---|---|
| MAST-L2-ASW-01 | The mission state machine shall sequence takeoff, transition, waypoint laps, survey, search, deliveries, return, transition, and landing autonomously, requiring exactly one operator command to begin and one to land. | L1-13, L0-END-02 | Any intervention beyond a single command risks the takeoff or landing being judged non-autonomous. |
| MAST-L2-ASW-02 | The state machine shall enforce the mandated task order: all intended laps before Search Boundary entry, at least one lap before any delivery. | L0-MSN-04, L0-END-05, L0-SDD-09 | Violating the order forfeits points irrecoverably. |
| MAST-L2-ASW-03 | During the lap phase the software shall treat the Search Boundary as an exclusion zone with a 25 m buffer, and shall replan rather than clip it. | L0-END-05, L1-15 | Prevents premature lap-count lock. The 25 m buffer covers the 15.2 m acceptance radius plus 5 m cross-track error with margin. |
| MAST-L2-ASW-04 | The software shall track completed lap count and report it to the GCS, and shall not advance to the survey phase until the operator-configured lap target is met or an energy-based abort triggers. | L0-END-03, L2-PWR-10 | Lap count is worth up to 200 points on a square law; the decision to stop must be informed by remaining energy rather than optimism. |
| MAST-L2-ASW-05 | The software shall plan and fly the Risk Mapping survey as a boustrophedon pattern over the Search Boundary meeting the overlap, sidelap, speed, and buffer requirements of MAST-L2-PER-06 and MAST-L2-PER-07. | L1-20, L2-PER-07 | Coverage is a scored criterion and edge coverage is the usual failure. |
| MAST-L2-ASW-06 | The software shall generate the orthomosaic incrementally during flight such that no more than 60 s of processing remains at touchdown, with bounded peak memory so that no out-of-memory condition can occur across a full-length survey at maximum capture rate. | L2-PER-10, L0-PEN-01, L1-20 | Batch processing after landing is charged at 0.5% of mission points per second. An out-of-memory kill mid-survey loses the 150-point deliverable with no recovery time available. |
| MAST-L2-ASW-07 | The software shall run target detection on captured imagery in flight, associate detections across frames, and declare at most one mannequin and one tent with their geolocated positions. | L1-19, L2-PER-12, L2-PER-14 | Two targets, two payloads, correct pairing worth 60 points. |
| MAST-L2-ASW-08 | On target declaration the software shall plan a delivery approach to a hover at the wind-compensated release point, verify predicted impact within 10.0 m of the target, and command release over an acknowledged interface, consuming wind, position, attitude, and AGL altitude at no less than 5 Hz. | L1-17, L2-PLD-07, L2-PLD-08 | Implements the release logic whose error budget is derived in `SUB-PLD`. An unacknowledged release command is indistinguishable from a lost one, and blind retry could double-release, forfeiting up to 100 points. |
| MAST-L2-ASW-09 | The software shall inhibit release if the predicted impact point is outside 10.0 m of the target, if the wind estimate is stale or invalid, or if altitude AGL is below 45.7 m. | L2-PLD-08, L0-SDD-08, L1-17 | Payloads are irreplaceable during a mission; a bad release wastes up to 100 points. Release inhibit is named safety-critical functionality in the handbook. |
| MAST-L2-ASW-10 | The software shall assign the water bottle payload to the mannequin and the beacon payload to the tent, and shall not release a payload to a target of the wrong class. | L0-SDD-10, L0-SDD-11 | 30 points per delivery depend on correct pairing. |
| MAST-L2-ASW-11 | All autonomy functions in the safety-critical path, including release inhibit, geofence enforcement, and failsafe triggering, shall execute onboard or on onsite equipment with no internet or cloud dependency. | L0-SAF-06, L1-28 | Explicitly inspected and explicitly enumerated in the handbook. |
| MAST-L2-ASW-12 | The software shall degrade gracefully: the detection and stitching pipelines shall run as separate fault-isolated processes under a watchdog that restarts a failed pipeline without operator action, such that failure of detection does not prevent map production and failure of map production does not prevent deliveries or landing. | L1-20, L1-19, L0-PEN-03 | The tasks are worth 150 and 200 points independently; coupling their failure modes would risk both at once. No operator is available to intervene in flight, so recovery must be automatic. |
| MAST-L2-ASW-13 | The software shall provide an operator-commandable abort for each task phase that returns the aircraft to a safe autonomous state without requiring manual piloting. | L0-PEN-06, L1-14 | A manual takeover restarts the lap; an autonomous abort does not. |
| MAST-L2-ASW-14 | All tunable behaviour shall be exposed as configuration parameters, exportable and importable as a single file, logged with each flight, and changeable without rebuilding flight software. | L1-27 | After design lock only 5% of size and weight change is permitted and core capability changes are prohibited; parameter tuning must not require touching the locked build. |
| MAST-L2-ASW-15 | Software builds shall be version controlled, and the exact build and parameter set flown shall be recorded and archived for every flight alongside the log. | L1-27, L0-ELG-03 | The design is locked at the Proof of Flight Readiness Video; demonstrating that the competition aircraft matches the submitted one requires this record. |
| MAST-L2-ASW-16 | Waypoint sequences for both flight lines shall be importable at the field, with the active line selectable in under 30 s. | L0-MSN-05, L2-GNC-19 | Both sequences are issued at Check-In and the assignment is not known in advance; selection happens on the Mission Clock. |
| MAST-L2-ASW-17 | The software shall monitor remaining energy against the return-to-land requirement and shall autonomously curtail the lap phase if projected reserve falls below 20%. | L1-05, L2-PWR-10 | Protects against the square-law lap incentive tempting an overrun, which would risk a 50% crash penalty instead of a partial score. |
| MAST-L2-ASW-18 | Every state shall have a defined transition for loss of GNSS, loss of link, low energy, and geofence proximity, and all phase transitions, release decisions, release inhibits with cause, and detection declarations shall be logged with timestamps at the time of decision. | L2-GNC-05, L2-GNC-11, L2-ASW-09 | Undefined behaviour in an off-nominal state is the usual cause of an autonomous aircraft doing something that looks unsafe to a judge, which is a 50% penalty. Post-flight reconstruction of why a release was inhibited is otherwise guesswork. |
| MAST-L2-ASW-19 | The software shall present a single unambiguous mission-phase indication to the GCS, distinguishing lap phase, survey phase, search phase, delivery phase, and return phase. | L1-14, L2-GCS-04 | The GCS Operator supervises a fully autonomous mission and must be able to tell at a glance whether the lap count is still accumulating. |
