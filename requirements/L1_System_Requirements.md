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

### MAST-L1-02 — Stowed volume
**Requirement.** The system shall collapse to fit entirely within the Carry-On envelope of
22 x 14 x 9 in (559 x 356 x 229 mm), including all ground support equipment required for
assembly.
**Parents.** L0-VEH-10

### MAST-L1-03 — Assembly time and crew
**Requirement.** The system shall be assembled from its fully collapsed state to flight-ready,
with motors and control surfaces operating, in 180 s or less, using hands only, with no tools,
by no more than 2 people.
**Parents.** L0-VEH-11, L0-VEH-12, L0-OPR-01

---

## Flight Performance

### MAST-L1-04 — Cruise speed
**Requirement.** The aircraft shall sustain a true airspeed of at least 25 m/s (48.6 kt) in
cruise configuration at maximum takeoff weight, in level flight, at field density altitude with
ambient temperature up to 110 °F.
**Parents.** L0-END-03, L0-END-04, L0-MSN-01

### MAST-L1-05 — Range and energy reserve
**Requirement.** The aircraft shall complete 32.19 km (20 statute mi) of cruise, plus the Risk
Mapping survey, plus target search and two payload deliveries, plus takeoff, landing, and two
transitions, on a single battery load, and shall retain at least 20% of usable energy at
touchdown.
**Parents.** L0-END-03, L0-VEH-09, L0-MAP-01, L0-SDD-01

### MAST-L1-06 — Sustained turn capability
**Requirement.** The aircraft shall sustain a level turn of 45.7 m (150 ft) radius at 25 m/s at
maximum takeoff weight, which requires 54.3 degrees of bank and a 1.72 g load factor, while
retaining a stall margin of at least 1.3x the stall speed applicable at that load factor.
**Parents.** L0-FLT-03

### MAST-L1-07 — Climb and descent angle
**Requirement.** The aircraft shall achieve climb and descent angles of at least 20 degrees.
**Parents.** L0-FLT-04

### MAST-L1-08 — Altitude envelope
**Requirement.** The aircraft shall operate within 150 to 400 ft AGL throughout the mission,
descending below 150 ft AGL only over its own assigned runway during takeoff and landing. The
system shall compute AGL against terrain varying from 633 to 748 ft MSL rather than against a
single field elevation datum.
**Parents.** L0-FLT-05, L0-FLT-06, L0-FLT-10

### MAST-L1-09 — VTOL takeoff and landing footprint **[TS]**
**Requirement.** The aircraft shall take off and land vertically within a 12.2 x 12.2 m
(40 x 40 ft) paved pad, with touchdown position accuracy of 3.0 m CEP or better, and shall
tolerate the possibility of being assigned either Runway 1 (40 x 500 ft) or Runway 2
(40 x 40 ft).
**Parents.** L0-FLT-07

### MAST-L1-10 — Transition **[TS]**
**Requirement.** The aircraft shall transition between hover and cruise attitudes in both
directions, completing each transition within 10 s, within a horizontal corridor of 100 m,
with altitude excursion not exceeding 15 m, and without departure from controlled flight.
Transitions shall be performed entirely within the Flight Boundary and within the 150 to 400 ft
AGL band.
**Parents.** L0-FLT-06, L0-SAF-11

### MAST-L1-11 — Wind envelope **[TS]**
**Requirement.** The aircraft shall hold hover position within 3.0 m horizontally in sustained
winds of 6.3 m/s (14 mph) with gusts to 9.8 m/s (22 mph), and shall complete all cruise,
transition, takeoff, and landing phases in the same conditions. The aircraft shall remain
controllable, though not necessarily mission-capable, in sustained winds to 8.5 m/s (19 mph).
**Parents.** L0-FLT-08, L0-FLT-09

### MAST-L1-12 — Thermal envelope
**Requirement.** The system shall operate at full performance in ambient temperatures up to
43.3 °C (110 °F) in direct sunlight, with no component exceeding its rated temperature and no
thermal derating of propulsion or compute.
**Parents.** L0-FLT-08

---

## Autonomy and Operations

### MAST-L1-13 — Mission autonomy
**Requirement.** The system shall execute all waypoint laps, the Risk Mapping survey, target
search and classification, and both payload deliveries with no operator input beyond a single
takeoff command and a single landing command.
**Parents.** L0-END-02, L0-END-05, L0-OPR-02, L0-PEN-06

### MAST-L1-14 — Two-operator operation
**Requirement.** The system shall be operable end to end by exactly 2 operators, a Safety Pilot
and a GCS Operator, neither of whom performs any task other than manual override standby and
autopilot supervision while the aircraft is airborne.
**Parents.** L0-OPR-01, L0-OPR-02

### MAST-L1-15 — Navigation accuracy
**Requirement.** The aircraft shall pass within 30.5 m (100 ft) of every commanded waypoint,
with the autopilot waypoint acceptance radius configured below 15.2 m (50 ft), and shall
maintain horizontal navigation error of 5.0 m or less throughout the mission.
**Parents.** L0-FLT-01, L0-FLT-02

### MAST-L1-16 — Failsafe behavior
**Requirement.** The system shall provide return-to-land and flight termination functions, each
independently activatable by both the Safety Pilot and the GCS Operator, shall automatically
initiate return-to-land after 15 s of communications loss, and shall automatically initiate
flight termination after 90 s of communications loss. All failsafe functions shall operate
without dependency on the public internet or cloud services.
**Parents.** L0-SAF-01, L0-SAF-02, L0-SAF-03, L0-SAF-04, L0-SAF-06

### MAST-L1-17 — Delivery placement accuracy
**Requirement.** The system shall place each delivery payload within 15.2 m (50 ft) of its
assigned target, released from an altitude at or above 45.7 m (150 ft) AGL, achieving a
placement accuracy of 10.0 m CEP or better.
**Parents.** L0-SDD-08, L0-SDD-11

### MAST-L1-18 — Communications availability
**Requirement.** The system shall maintain continuous bidirectional command and telemetry
connectivity everywhere within the Flight Boundary, with no single link outage exceeding 5.0 s,
in the presence of uncoordinated co-channel transmissions from other teams using identical
equipment. Ground equipment shall not exceed 15 ft in height.
**Parents.** L0-SAF-03, L0-REG-04, L0-REG-05, L0-GCS-04

### MAST-L1-19 — Target detection and geolocation
**Requirement.** The system shall autonomously detect, classify, and geolocate one mannequin and
one open pop-up tent within the approximately 10-acre Search Boundary from an altitude at or
above 45.7 m (150 ft) AGL, with geolocation error of 5.0 m or less, and shall correctly
distinguish the two classes so that the water bottle is assigned to the mannequin and the
beacon to the tent.
**Parents.** L0-SDD-10, L0-SDD-11

### MAST-L1-20 — Risk map production
**Requirement.** The system shall autonomously produce a georeferenced orthomosaic covering the
entire Search Boundary at a ground sample distance of 2.0 cm/pixel or finer, complete the
stitching without human intervention, and write the result as a .png or .jpeg file whose
filename contains the team name to a judge-supplied USB drive before Mission Time ends.
**Parents.** L0-MAP-01, L0-MAP-02, L0-MAP-03, L0-MAP-04, L1-14

---

## Safety, Integrity, and Compliance

### MAST-L1-21 — Battery packaging architecture
**Requirement.** The power system shall provide at least 330 Wh of installed capacity using
individually packaged batteries each below 100 Wh, all brightly colored, each removable and
installable without any structural disassembly of the airframe.
**Parents.** L0-VEH-05, L0-VEH-13, L1-05

### MAST-L1-22 — Structural integrity
**Requirement.** The airframe shall withstand a limit load of 1.72 g, matching the sustained
turn of L1-06, with a factor of safety of 1.5 giving an ultimate load of 2.58 g, and shall
additionally withstand hover-attitude rotor thrust loads and landing impact loads without
permanent deformation.
**Parents.** L0-VEH-07, L0-PEN-02, L0-PEN-03

### MAST-L1-23 — Zero part departure
**Requirement.** No component shall depart the aircraft in flight other than the intended
delivery payloads. All fasteners shall be secured by safety wire, thread-locking fluid, or nylon
lock nuts.
**Parents.** L0-VEH-06, L0-VEH-07, L0-PEN-02

### MAST-L1-24 — Propeller safety interlock
**Requirement.** The system shall provide a physical means of disconnecting motor power, or
physically restraining all propellers, that is engageable before any person approaches the
propeller arc, and that does not rely on software disarm.
**Parents.** L0-VEH-08

### MAST-L1-25 — Traffic deconfliction
**Requirement.** The system shall maintain separation from a second UAS operating simultaneously
within the Flight Boundary, and shall present sufficient position and intent information at the
GCS for the operators to deconflict via judge-relayed coordination.
**Parents.** L0-SAF-11, L0-PEN-03

### MAST-L1-26 — Regulatory marking and identification
**Requirement.** The aircraft shall carry its FAA registration number on an external surface and
shall broadcast Remote ID containing a unique vehicle identifier and vehicle position.
**Parents.** L0-REG-01, L0-REG-02

### MAST-L1-27 — Configuration control
**Requirement.** The system configuration shall be frozen at submission of the Proof of Flight
Readiness Video. After freeze, no change shall alter propulsion, avionics, or other core
capability, and no change shall alter system size or weight by more than 5%.
**Parents.** L0-ELG-03

### MAST-L1-28 — Onsite independence
**Requirement.** All safety-critical functions — return to land, flight termination, manual
piloting, autopilot commanding, and delivery release inhibit — shall execute on equipment under
the team's direct physical control, with no dependency on the public internet or any cloud
provider.
**Parents.** L0-SAF-06
