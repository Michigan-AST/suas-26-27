# L1 — System Requirements

**Level definition.** L1 requirements describe what the aircraft system as a whole must do. They
are derived from L0 competition requirements and from the two analyses in Appendix A and
Appendix B below. Every L1 requirement names its L0 parent and states why the specific number
was chosen.

**Configuration.** Tailsitter VTOL — a fixed-wing airframe that rotates bodily between a
nose-up hover attitude and a horizontal cruise attitude. Requirements that exist specifically
because of this configuration are marked **[TS]**.

**Team prefix.** `MAST`. Requirement IDs are stable; once published they are never renumbered,
only superseded.

---

## Appendix A — Mission clock budget (drives L1-03, L1-04, L1-05)

The 45-minute Mission Clock (2700 s) includes setup, and the rules force the waypoint laps to
be flown *before* any Search Boundary work, so the phases are strictly serial and cannot be
overlapped.

| Phase | Allocation | Basis |
|---|---|---|
| Unpack, assemble, power, GNSS/compass init, preflight, arm | 420 s | 180 s of this is the scored unpack (L0-VEH-11); remainder is 2-operator boot and checks |
| Takeoff, climb, transition to cruise | 60 s | Vertical climb to 150 ft AGL plus transition |
| **10 waypoint laps (20 mi / 32.19 km)** | **1290 s** | Remainder — this is the number being solved for |
| Risk mapping survey of Search Boundary | 180 s | 5 passes over a 147 x 262 m box, plus turns (Appendix B) |
| Search, detect, and two delivery runs | 420 s | Two wind-compensated hover releases plus repositioning |
| Return, transition, land | 90 s | |
| Clear runway, relinquish airspace, export map to USB, submit | 180 s | Mission Clock runs until deliverables are submitted (L0-MSN-02) |
| **Total** | **2640 s** | 60 s unallocated margin against a 2700 s clock |

The 1290 s remaining for 32.19 km sets the required average groundspeed at **24.95 m/s**, which
is the origin of the 25 m/s cruise requirement. This budget has only 2.2% schedule margin, which
is itself a finding: the 45-minute clock, not battery energy, is the tighter of the two
constraints on lap count.

## Appendix B — Energy budget (drives L1-04, L1-21)

Assumes 6.80 kg (15 lb) all-up weight, 0.45 m² wing area, aspect ratio 7, CD0 = 0.035 (elevated
to account for four exposed VTOL rotors and nacelles in cruise), Oswald efficiency 0.85,
propeller efficiency 0.70, motor and ESC efficiency 0.85.

At 25 m/s: CL = 0.387, CD = 0.043, drag = 7.4 N, required shaft power 185 W, **electrical
cruise power 311 W**.

Hover, with four 12 in rotors (total disk area 0.292 m², disk loading 228 N/m²), figure of merit
0.65: ideal power 644 W, **electrical hover power 1166 W** — 3.7x cruise power, which is why
hover time is budgeted so tightly.

| Phase | Power | Duration | Energy |
|---|---|---|---|
| Cruise (10 laps) | 311 W | 1290 s | 111 Wh |
| Cruise (mapping and search) | 311 W | 600 s | 52 Wh |
| Hover (takeoff, landing, 2 transitions, 2 drop hovers) | 1166 W | 130 s | 42 Wh |
| Climb energy (potential + transition losses) | — | — | 10 Wh |
| Avionics, compute, camera, radios | 50 W | 2100 s | 29 Wh |
| **Mission total** | | | **244 Wh** |
| 20% reserve at landing | | | 49 Wh |
| **Required usable energy** | | | **293 Wh** |

With a 95% usable depth of discharge, installed capacity must be at least 308 Wh. Rounded up
for pack granularity under the sub-100 Wh rule, the requirement is **four packs of 82.5 Wh or
greater (330 Wh installed)**.

At 180 Wh/kg cell-level specific energy this is 1.83 kg of battery — **27% of a 15 lb all-up
weight**. Combined with two delivery payloads, the mass situation is the dominant system-level
risk; see the note under L1-01.

---

## Mass, Volume, and Transport

### MAST-L1-01 — All-up weight
**Requirement.** System all-up weight, including all batteries, both complete delivery payloads,
and all installed systems in the maximum takeoff state, shall not exceed 15.0 lb (6.80 kg), and
shall under no circumstances exceed 35.0 lb (15.88 kg).
**Parents.** L0-VEH-02, L0-VEH-03
**Rationale.** 35 lb is the hard rule; 15 lb earns maximum weight points. The 15 lb target is
deliberately set as a requirement rather than a goal because the weight score is only 50 of
1000 points, but weight compounds into every other task: hover power scales with W^1.5, cruise
power with W, and energy with both. A heavier aircraft needs more battery, which makes it
heavier. Per Appendix B, battery alone is 27% of the 15 lb budget and the two delivery payloads
may add up to 4 lb more, leaving roughly 7 lb for airframe, propulsion, avionics, and payload
bay. **This is the tightest requirement in the document and should be treated as the primary
mass-growth watch item.** If the design converges above 15 lb, relax this requirement
deliberately and in writing rather than by drift.

### MAST-L1-02 — Stowed volume
**Requirement.** The system shall collapse to fit entirely within the Carry-On envelope of
22 x 14 x 9 in (559 x 356 x 229 mm), including all ground support equipment required for
assembly.
**Parents.** L0-VEH-10
**Rationale.** Carry-On is the recommended target rather than the smaller Personal Item tier.
The step from Carry-On to Personal Item is worth only 25 points, but it reduces the longest
stowed dimension from 559 mm to 457 mm. For the ~2.0 m span implied by the Appendix B wing
area, that is the difference between 4 wing segments and 5, and every additional segment adds
a joint that carries mass, adds assembly time against the 180 s limit (L0-VEH-11), threatens
the toolless bonus (L0-VEH-12, worth the same 25 points), and creates another candidate for a
part departing in flight (L0-PEN-02, 10% penalty). The trade is roughly points-neutral at best
and risk-negative. Revisit only if the airframe converges with fewer segments than expected.

### MAST-L1-03 — Assembly time and crew
**Requirement.** The system shall be assembled from its fully collapsed state to flight-ready,
with motors and control surfaces operating, in 180 s or less, using hands only, with no tools,
by no more than 2 people.
**Parents.** L0-VEH-11, L0-VEH-12, L0-OPR-01
**Rationale.** 180 s and toolless come directly from the rules. The 2-person limit is derived,
not given: maximum Efficient Operators points require exactly 2 operators (L0-OPR-01), and
non-operators may not assist operators during Mission Time (L0-OPR-03), so designing for the
4 personnel that L0-VEH-11 permits would forfeit 100 to 200 points elsewhere. Designing to
2 people makes the two scoring incentives compatible. This depends on open question 1 in
`L0_Reconciliation_Notes.md`; if organizers confirm the unpack demonstration is off the clock,
this requirement can be relaxed to 4 people.

---

## Flight Performance

### MAST-L1-04 — Cruise speed
**Requirement.** The aircraft shall sustain a true airspeed of at least 25 m/s (48.6 kt) in
cruise configuration at maximum takeoff weight, in level flight, at field density altitude with
ambient temperature up to 110 °F.
**Parents.** L0-END-03, L0-END-04, L0-MSN-01
**Rationale.** Derived in Appendix A. Flying all 10 laps requires averaging 24.95 m/s
groundspeed over the lap phase. Because Flight Endurance scores as the square of lap count,
falling short is expensive and non-linear: 8 laps instead of 10 costs 72 points. Specified as
true airspeed at 110 °F because density altitude at 690 ft MSL and 43 °C is roughly 3,500 ft,
reducing available thrust and increasing true airspeed for a given indicated airspeed.

### MAST-L1-05 — Range and energy reserve
**Requirement.** The aircraft shall complete 32.19 km (20 statute mi) of cruise, plus the Risk
Mapping survey, plus target search and two payload deliveries, plus takeoff, landing, and two
transitions, on a single battery load, and shall retain at least 20% of usable energy at
touchdown.
**Parents.** L0-END-03, L0-VEH-09, L0-MAP-01, L0-SDD-01
**Rationale.** Derived in Appendix B: 244 Wh mission energy, 293 Wh usable with reserve.
Batteries may not be swapped or recharged on the Mission Clock (L0-VEH-09), so the entire
mission is one discharge. The 20% reserve covers a diverted landing, a go-around, a headwind
worse than the 14 mph average, and cell aging over a season of testing.

### MAST-L1-06 — Sustained turn capability
**Requirement.** The aircraft shall sustain a level turn of 45.7 m (150 ft) radius at 25 m/s at
maximum takeoff weight, which requires 54.3 degrees of bank and a 1.72 g load factor, while
retaining a stall margin of at least 1.3x the stall speed applicable at that load factor.
**Parents.** L0-FLT-03
**Rationale.** The 150 ft turn radius is a stated rule, but the handbook gives it without a
speed, so the binding case is the radius at the required cruise speed. tan(phi) = V^2/(r*g)
gives 54.3 degrees and n = 1/cos(phi) = 1.72. The load-factor stall speed is
V_stall * sqrt(1.72) = 1.31 * V_stall, so the 1.3x margin requires a 1 g stall speed at or below
14.7 m/s. With CL_max = 1.2 and 0.45 m² of wing, the 1 g stall speed is 14.2 m/s, which closes
with a small margin. **This couples wing area to cruise speed and is the reason wing area cannot
simply be shrunk to reduce cruise drag.**

### MAST-L1-07 — Climb and descent angle
**Requirement.** The aircraft shall achieve climb and descent angles of at least 20 degrees.
**Parents.** L0-FLT-04
**Rationale.** Stated rule. Trivially satisfied by a tailsitter, which can climb vertically, but
the requirement is retained because it must also be demonstrable in cruise configuration for
the safety inspection, and because 20 degrees at 25 m/s implies an 8.55 m/s climb rate needing
about 570 W of excess power above the 185 W cruise requirement.

### MAST-L1-08 — Altitude envelope
**Requirement.** The aircraft shall operate within 150 to 400 ft AGL throughout the mission,
descending below 150 ft AGL only over its own assigned runway during takeoff and landing. The
system shall compute AGL against terrain varying from 633 to 748 ft MSL rather than against a
single field elevation datum.
**Parents.** L0-FLT-05, L0-FLT-06, L0-FLT-10
**Rationale.** Breaching this band terminates the mission (L0-FLT-06), making it one of only
two mission-ending geometric constraints. The terrain clause is the subtle part: 115 ft of
elevation variation inside the boundary is 77% of the entire 150 ft floor margin, so an
aircraft holding a constant barometric or MSL altitude referenced to the runway will breach the
AGL floor over high terrain. Trees to 100 ft AGL (L0-FLT-10) further reduce real clearance.

### MAST-L1-09 — VTOL takeoff and landing footprint **[TS]**
**Requirement.** The aircraft shall take off and land vertically within a 12.2 x 12.2 m
(40 x 40 ft) paved pad, with touchdown position accuracy of 3.0 m CEP or better, and shall
tolerate the possibility of being assigned either Runway 1 (40 x 500 ft) or Runway 2
(40 x 40 ft).
**Parents.** L0-FLT-07
**Rationale.** Runway 2 is VTOL-only and just 40 ft square, and teams may not use the runway
they were not assigned. A 3.0 m CEP keeps the aircraft inside the pad with margin for a 2.0 m
half-span. This requirement is a direct competitive advantage of the VTOL configuration — a
conventional fixed-wing team is restricted to Runway 1.

### MAST-L1-10 — Transition **[TS]**
**Requirement.** The aircraft shall transition between hover and cruise attitudes in both
directions, completing each transition within 10 s, within a horizontal corridor of 100 m,
with altitude excursion not exceeding 15 m, and without departure from controlled flight.
Transitions shall be performed entirely within the Flight Boundary and within the 150 to 400 ft
AGL band.
**Parents.** L0-FLT-06, L0-SAF-11
**Rationale.** The altitude excursion limit is the derived part and it is tight for a reason:
the aircraft transitions at or near 150 ft AGL, and the floor is a mission-ending boundary. A
tailsitter accelerating through transition typically sags in altitude as the wing takes over
from rotor thrust, so a 15 m budget leaves 30 m of the floor margin intact. The 100 m corridor
ensures a transition initiated anywhere inside the boundary cannot exit it.

### MAST-L1-11 — Wind envelope **[TS]**
**Requirement.** The aircraft shall hold hover position within 3.0 m horizontally in sustained
winds of 6.3 m/s (14 mph) with gusts to 9.8 m/s (22 mph), and shall complete all cruise,
transition, takeoff, and landing phases in the same conditions. The aircraft shall remain
controllable, though not necessarily mission-capable, in sustained winds to 8.5 m/s (19 mph).
**Parents.** L0-FLT-08, L0-FLT-09
**Rationale.** **This is the highest-risk requirement for a tailsitter and the rules offer no
protection.** The handbook sets no wind limit at all — the aircraft must handle "any winds
experienced at the airfield" — and only notes a 14 mph September average. The 19 mph figure
inherited from the original CSV summary is a self-imposed assumption, recorded here as a
controllability floor rather than a mission requirement. A tailsitter in hover presents its
entire wing area as a sail, so a gust produces a large pitching moment that must be countered
by differential rotor thrust alone. Gust magnitude is set at 1.55x sustained, a standard
convention. The 3.0 m hover accuracy derives from L1-09 touchdown accuracy and from the drop
accuracy chain in L1-17.

### MAST-L1-12 — Thermal envelope
**Requirement.** The system shall operate at full performance in ambient temperatures up to
43.3 °C (110 °F) in direct sunlight, with no component exceeding its rated temperature and no
thermal derating of propulsion or compute.
**Parents.** L0-FLT-08
**Rationale.** Stated rule. Flagged as system-level rather than subsystem-level because it
binds three subsystems simultaneously: battery internal resistance and voltage sag, motor and
ESC thermal margin during the high-power hover phases, and onboard compute throttling during
the mapping and detection workload. A compute thermal throttle during the detection phase would
silently cost up to 200 points.

---

## Autonomy and Operations

### MAST-L1-13 — Mission autonomy
**Requirement.** The system shall execute all waypoint laps, the Risk Mapping survey, target
search and classification, and both payload deliveries with no operator input beyond a single
takeoff command and a single landing command.
**Parents.** L0-END-02, L0-END-05, L0-OPR-02, L0-PEN-06
**Rationale.** Three separate rules converge on this. Fully autonomous takeoff and landing
requires a single command each (L0-END-02, 30 points). Laps must be fully autonomous with no
manual takeover or a lap restarts (L0-END-05, L0-PEN-06). And the two operators may perform no
other task while airborne (L0-OPR-02), so there is nobody available to fly the survey or pick
drop points manually. Autonomy here is not a stretch goal; it is the only way the mission closes
with 2 operators.

### MAST-L1-14 — Two-operator operation
**Requirement.** The system shall be operable end to end by exactly 2 operators, a Safety Pilot
and a GCS Operator, neither of whom performs any task other than manual override standby and
autopilot supervision while the aircraft is airborne.
**Parents.** L0-OPR-01, L0-OPR-02
**Rationale.** Worth 200 points, and the scoring is effectively binary — 4 operators, the
maximum the rules allow, scores zero. The consequence that propagates furthest is that no human
is available to process imagery in flight, which forces L1-20 to require a fully automated
mapping pipeline rather than a human-in-the-loop one.

### MAST-L1-15 — Navigation accuracy
**Requirement.** The aircraft shall pass within 30.5 m (100 ft) of every commanded waypoint,
with the autopilot waypoint acceptance radius configured below 15.2 m (50 ft), and shall
maintain horizontal navigation error of 5.0 m or less throughout the mission.
**Parents.** L0-FLT-01, L0-FLT-02
**Rationale.** The 100 ft figure is the scored tolerance and 50 ft is the separately mandated
autopilot configuration that judges inspect (L0-FLT-02). Designing to 5 m navigation error
gives 3x margin against the 15.2 m acceptance radius, which matters because a lap must be flown
fully autonomously to count and a missed acceptance radius risks the autopilot holding or
circling, burning the tight schedule margin from Appendix A.

### MAST-L1-16 — Failsafe behavior
**Requirement.** The system shall provide return-to-land and flight termination functions, each
independently activatable by both the Safety Pilot and the GCS Operator, shall automatically
initiate return-to-land after 15 s of communications loss, and shall automatically initiate
flight termination after 90 s of communications loss. All failsafe functions shall operate
without dependency on the public internet or cloud services.
**Parents.** L0-SAF-01, L0-SAF-02, L0-SAF-03, L0-SAF-04, L0-SAF-06
**Rationale.** Directly inspected at safety inspection; the aircraft does not fly without it.
The derived consequence appears in L1-18: a 15 s automatic RTL trigger means any link dropout
longer than 15 s ends the mission attempt, which sets the link availability requirement far
above what mere telemetry display would need.

### MAST-L1-17 — Delivery placement accuracy
**Requirement.** The system shall place each delivery payload within 15.2 m (50 ft) of its
assigned target, released from an altitude at or above 45.7 m (150 ft) AGL, achieving a
placement accuracy of 10.0 m CEP or better.
**Parents.** L0-SDD-08, L0-SDD-11
**Rationale.** This is the hardest accuracy problem in the competition and the reason is the
interaction of two rules. Release must occur above 150 ft AGL (L0-SDD-08) and freefall is
prohibited (L0-SDD-05), so the payload spends seconds descending under a drag device while the
wind advects it. At the 14 mph average wind, an uncompensated release with an 8 m/s descent
device lands about 36 m downwind, roughly 2.4x the allowed radius. Wind compensation is
therefore mandatory, not optional. The full error analysis is in
`L2_Subsystems/SUB-PLD_Payload_Delivery.md`; the 10 m CEP budget leaves room to combine with
the 5 m target geolocation error from L1-19 and still close inside 15.2 m.

### MAST-L1-18 — Communications availability
**Requirement.** The system shall maintain continuous bidirectional command and telemetry
connectivity everywhere within the Flight Boundary, with no single link outage exceeding 5.0 s,
in the presence of uncoordinated co-channel transmissions from other teams using identical
equipment. Ground equipment shall not exceed 15 ft in height.
**Parents.** L0-SAF-03, L0-REG-04, L0-REG-05, L0-GCS-04
**Rationale.** The 5.0 s outage limit is derived from the 15 s automatic RTL trigger
(L0-SAF-03) with a 3x margin. This is the requirement most likely to be underestimated: the
handbook explicitly provides no spectrum management, permits any team to transmit in any
permitted band at any time including in the pits, and warns that teams must prevent invalid
connections to another team's autopilot (L0-REG-05). A spurious 15 s dropout does not merely
degrade telemetry, it automatically aborts the mission. The Flight Boundary spans roughly
1.1 x 1.1 km, so maximum slant range is about 1.6 km — the challenge is interference
rejection, not path loss.

### MAST-L1-19 — Target detection and geolocation
**Requirement.** The system shall autonomously detect, classify, and geolocate one mannequin and
one open pop-up tent within the approximately 10-acre Search Boundary from an altitude at or
above 45.7 m (150 ft) AGL, with geolocation error of 5.0 m or less, and shall correctly
distinguish the two classes so that the water bottle is assigned to the mannequin and the
beacon to the tent.
**Parents.** L0-SDD-10, L0-SDD-11
**Rationale.** 30 of the 100 points per delivery depend on correct pairing, so misclassifying
which target is which costs 60 points even with two perfectly accurate drops. The detection
problem is harder than the target sizes suggest: the mannequin may be face-down, laying down,
or partially covered by bushes, trees, or vehicles, and both targets sit among unrelated debris.
The 5.0 m geolocation budget combines with the 10.0 m drop CEP of L1-17 to give
sqrt(5^2 + 10^2) = 11.2 m total, inside the 15.2 m scoring radius.

### MAST-L1-20 — Risk map production
**Requirement.** The system shall autonomously produce a georeferenced orthomosaic covering the
entire Search Boundary at a ground sample distance of 2.0 cm/pixel or finer, complete the
stitching without human intervention, and write the result as a .png or .jpeg file whose
filename contains the team name to a judge-supplied USB drive before Mission Time ends.
**Parents.** L0-MAP-01, L0-MAP-02, L0-MAP-03, L0-MAP-04, L1-14
**Rationale.** The quality bar is "indiscernible from a professional map seen on services like
Google Maps" for full marks, which drives the 2.0 cm/pixel figure — comfortably finer than the
3 cm/pixel typically needed to look professional, and also sufficient for the L1-19 detection
task to reuse the same imagery. The requirement that stitching be autonomous follows from
L1-14: with 2 operators who may not perform other tasks in flight, there is nobody to run a
photogrammetry tool. Because the Mission Clock does not stop until deliverables are submitted
(L0-MSN-02), every second of post-landing processing is charged at 0.5% of mission points per
second, so the map must be essentially finished at touchdown.

---

## Safety, Integrity, and Compliance

### MAST-L1-21 — Battery packaging architecture
**Requirement.** The power system shall provide at least 330 Wh of installed capacity using
individually packaged batteries each below 100 Wh, all brightly colored, each removable and
installable without any structural disassembly of the airframe.
**Parents.** L0-VEH-05, L0-VEH-13, L1-05
**Rationale.** The sub-100 Wh rule is worth 75 points, the largest single sub-item in Design for
Rapid Response, and it constrains pack architecture rather than total energy — there is no cap
on installed capacity. Appendix B requires 308 Wh usable, so 330 Wh across four sub-100 Wh packs
satisfies both. The accessibility clause is a separate rule (L0-VEH-05: batteries explicitly may
not be embedded in the airframe), and it conflicts mildly with L1-02 stowed volume, since
externally accessible pack bays are volumetrically inefficient.

### MAST-L1-22 — Structural integrity
**Requirement.** The airframe shall withstand a limit load of 1.72 g, matching the sustained
turn of L1-06, with a factor of safety of 1.5 giving an ultimate load of 2.58 g, and shall
additionally withstand hover-attitude rotor thrust loads and landing impact loads without
permanent deformation.
**Parents.** L0-VEH-07, L0-PEN-02, L0-PEN-03
**Rationale.** The 1.72 g limit load is inherited from the turn requirement rather than assumed.
The tailsitter-specific part is that the structure sees two distinct and largely orthogonal load
cases: wing bending in cruise, and rotor thrust plus gust-induced pitching moments applied to a
vertically oriented airframe in hover. A conventional fixed-wing analysis covers only the first.

### MAST-L1-23 — Zero part departure
**Requirement.** No component shall depart the aircraft in flight other than the intended
delivery payloads. All fasteners shall be secured by safety wire, thread-locking fluid, or nylon
lock nuts.
**Parents.** L0-VEH-06, L0-VEH-07, L0-PEN-02
**Rationale.** 10% of mission points per item lost, and fastener retention is explicitly
inspected. The requirement is more demanding for this design than it appears: L1-02 and L1-03
require a toolless, repeatedly assembled and disassembled airframe with multiple wing joints,
which is in direct tension with fastener retention. Quick-release joints must be positively
locked and the locking must be verifiable by eye during the 180 s assembly.

### MAST-L1-24 — Propeller safety interlock
**Requirement.** The system shall provide a physical means of disconnecting motor power, or
physically restraining all propellers, that is engageable before any person approaches the
propeller arc, and that does not rely on software disarm.
**Parents.** L0-VEH-08
**Rationale.** Explicitly inspected, and the handbook states software disarm is insufficient and
that violation may cause disqualification. For this configuration the requirement is unusually
awkward: a tailsitter rests nose-up with its rotors near head height or near the ground
depending on the ground handling scheme, so the interlock must be reachable without entering the
arc of any of the four rotors.

### MAST-L1-25 — Traffic deconfliction
**Requirement.** The system shall maintain separation from a second UAS operating simultaneously
within the Flight Boundary, and shall present sufficient position and intent information at the
GCS for the operators to deconflict via judge-relayed coordination.
**Parents.** L0-SAF-11, L0-PEN-03
**Rationale.** A collision costs 50% of mission points, and a team inside its own runway's
dedicated airspace is not penalized while the offending team is — so the practical requirement
is to stay predictable and inside one's own lane. Organizers do not create known collision
paths, so this is a monitoring and airmanship requirement rather than a sense-and-avoid one. No
onboard detect-and-avoid sensor is required.

### MAST-L1-26 — Regulatory marking and identification
**Requirement.** The aircraft shall carry its FAA registration number on an external surface and
shall broadcast Remote ID containing a unique vehicle identifier and vehicle position.
**Parents.** L0-REG-01, L0-REG-02
**Rationale.** Inspected before flight. Called out at L1 because the Remote ID module is one of
the few additions explicitly permitted after design lock (L0-ELG-03), making it a low-risk item
to defer — but its mass and mounting location must still be reserved in the layout.

### MAST-L1-27 — Configuration control
**Requirement.** The system configuration shall be frozen at submission of the Proof of Flight
Readiness Video. After freeze, no change shall alter propulsion, avionics, or other core
capability, and no change shall alter system size or weight by more than 5%.
**Parents.** L0-ELG-03
**Rationale.** A programmatic requirement with a hard engineering consequence: 5% of a 15 lb
aircraft is 0.75 lb. Any mass growth discovered after the video submission must fit in that
band, so the mass margin strategy must front-load reserve before the freeze rather than after.
Flight order and on-site invitation also depend on submitting this video early (L0-DOC-03, only
about 50 teams are invited), which puts schedule pressure directly against design maturity.

### MAST-L1-28 — Onsite independence
**Requirement.** All safety-critical functions — return to land, flight termination, manual
piloting, autopilot commanding, and delivery release inhibit — shall execute on equipment under
the team's direct physical control, with no dependency on the public internet or any cloud
provider.
**Parents.** L0-SAF-06
**Rationale.** Stated rule, inspected. Its real effect is on L1-20 and L1-19: any temptation to
offload photogrammetry or model inference to a cloud service is barred for anything in the
safety-critical path, and since the delivery release inhibit is named explicitly, the detection
and release decision chain must run entirely onsite or onboard.
