# L0 — Competition Requirements (SUAS 2026)

**Level definition.** L0 requirements are imposed externally by the competition organizers. They
are not negotiable, not derived, and not ours to change. Every requirement below traces to a
section of the *SUAS 2026 Team Handbook*. Where the handbook expresses something as a scoring
incentive rather than a hard rule, the Type column says so — this distinction matters, because
incentives can be traded against each other while rules cannot.

**Type key.**
- `RULE` — mandatory. Violation prevents flight, terminates the mission, or disqualifies.
- `SCORE` — affects points only. Legitimate to trade.
- `INFO` — environmental or contextual fact that constrains design without being a pass/fail rule.

See `L0_Reconciliation_Notes.md` for differences between this baseline and the original CSV
summary, including two inverted constraints.

---

## Eligibility and Team Composition

| ID | Type | Requirement | Source |
|---|---|---|---|
| L0-ELG-01 | RULE | The team shall be comprised of 75% or more full-time students, with no more than 25% alumni, industry, academic, or government partners. | §1.4.1 |
| L0-ELG-02 | RULE | The team shall enter exactly one aircraft design in the competition. | §1.4, §5.1.2 |
| L0-ELG-03 | RULE | The design shall be locked upon submission of the Proof of Flight Readiness Video. Modifications to core capabilities (propulsion, avionics) are prohibited, as is any change altering system size or weight by more than 5%. | §5.3.4 |
| L0-ELG-04 | RULE | A minimum of 2 team members (Safety Pilot and GCS Operator) and a maximum of 4 operators shall run the mission. No more than 8 team members may be on the flight line. | §1.4.1, §3.3 |
| L0-ELG-05 | RULE | One student shall be designated team lead, be conversationally fluent in English, and be the only team member who speaks during the mission demonstration. | §5.1.6 |
| L0-ELG-06 | RULE | The team shall have at least one representative present at team orientation. | §5.1.7 |

## Design Documentation

| ID | Type | Requirement | Source |
|---|---|---|---|
| L0-DOC-01 | SCORE | The team shall submit a Technical Design Report of at most 10 pages. Worth 150 points. | §2.3, §4.1.1 |
| L0-DOC-02 | SCORE | The team shall publish a team website. Worth 100 points. | §2.4, §4.1.1 |
| L0-DOC-03 | RULE | The team shall submit a Proof of Flight Readiness Video. Flight order and on-site invitation depend on it; only the first ~50 qualifying teams are invited. | §2.1, §3.0.7 |
| L0-DOC-04 | RULE | The team shall submit a Proof of Pilot Competence Video. | §2.2 |

## Regulatory Compliance

| ID | Type | Requirement | Source |
|---|---|---|---|
| L0-REG-01 | RULE | The UAS shall be registered via FAADroneZone, the certificate shall be presented at safety inspection and at the flight line, and the registration number shall be marked on an external surface of the vehicle. | §5.3.3 |
| L0-REG-02 | RULE | The UAS shall comply with FAA Remote ID, broadcasting at minimum a unique vehicle ID and vehicle position. | §5.3.3 |
| L0-REG-03 | RULE | The Safety Pilot shall hold a completed FAA TRUST certificate and present it at safety inspection and at the flight line. | §5.3.3 |
| L0-REG-04 | RULE | All RF communications shall comply with FCC regulations. Judges use 462 MHz for handheld radios. | §5.3.12 |
| L0-REG-05 | INFO | No RF spectrum management is provided. Any device may transmit in any permitted band at any time, in the pits and on the flight line. Teams must assume competitors use identical equipment and must prevent invalid connections to another team's autopilot. | §5.3.12 |

## Vehicle Configuration

| ID | Type | Requirement | Source |
|---|---|---|---|
| L0-VEH-01 | RULE | The UAS shall be battery-electric powered. No fuels and no exotic batteries are permitted. Any option deemed high risk by organizers will be denied. | §5.1.4, §5.3.6 |
| L0-VEH-02 | RULE | All-up flying weight shall be 35 lb or less, inclusive of all batteries, payloads, and delivery objects in the maximum takeoff state. | §5.3.2, §3.4.1 |
| L0-VEH-03 | SCORE | Maximum weight points are awarded at an all-up weight of 15 lb or less. Weight component is worth 50 points. | §3.4.1, §3.4.4 |
| L0-VEH-04 | RULE | The UAS shall be capable of heavier-than-air flight and shall be free-flying with no ground encumbrances such as tethers. | §5.3.2 |
| L0-VEH-05 | RULE | All batteries shall be brightly colored for identification in a crash, and shall be located so they can be removed and installed without any vehicle deconstruction. Batteries shall not be embedded in the airframe. | §5.3.6 |
| L0-VEH-06 | RULE | All fasteners shall be secured with safety wire, thread-locking fluid, or nylon lock nuts. | Appendix B |
| L0-VEH-07 | RULE | No pieces shall depart the aircraft in flight, except components involved in an active delivery attempt. Foreign object debris shall be cleared from the operating area before mission flight time stops. | §5.3.9 |
| L0-VEH-08 | RULE | Personnel shall be clear of the propeller arc whenever motors have the ability to receive power. Software-based disarm is explicitly insufficient; motor power disconnect or physical propeller restraint is required to work on the UAS. | §5.3.10, Appendix B |
| L0-VEH-09 | RULE | The UAS shall not land to swap or recharge batteries while on the Mission Clock, except during a sanctioned Air Traffic or Weather Mission Pause. | §5.3.6, §3.1.3 |
| L0-VEH-10 | SCORE | The UAS shall collapse to a transport state more compact than its flight state. Sizing tiers: Personal Item 18 x 14 x 8 in (50 pts), Carry-On 22 x 14 x 9 in (25 pts), Check-In 27 x 21 x 14 in (10 pts). | §3.4.2 |
| L0-VEH-11 | SCORE | The UAS shall be unpacked from fully collapsed to flight-ready state, with motors and control surfaces operating, within 3 minutes using at most 4 personnel. Failure to meet the time or personnel limit forfeits all points for this task. | §3.4.2 |
| L0-VEH-12 | SCORE | Unpacking without tools, using only hands, earns 25 additional points. | §3.4.2 |
| L0-VEH-13 | SCORE | Every individually packaged battery onboard shall be below 100 Wh capacity. Worth 75 points. There is no limit on the number of batteries. | §3.4.3 |

## Safety and Failsafes

| ID | Type | Requirement | Source |
|---|---|---|---|
| L0-SAF-01 | RULE | The UAS shall have autonomous return to home or return to land, activatable independently by both the Safety Pilot and the GCS Operator. | §5.3.8, Appendix B |
| L0-SAF-02 | RULE | The UAS shall have autonomous flight termination, activatable independently by both the Safety Pilot and the GCS Operator. Fixed-wing termination configuration: throttle closed, full up elevator, full right rudder, full aileron, full flaps down. Rotary termination: throttle closed. | §5.3.8, Appendix B |
| L0-SAF-03 | RULE | The UAS shall automatically execute RTH/RTL after 15 seconds of communications loss. | Appendix B |
| L0-SAF-04 | RULE | The UAS shall automatically execute flight termination after 90 seconds of communications loss. | Appendix B |
| L0-SAF-05 | RULE | The UAS shall permit manual Safety Pilot takeoff and override at any time. | §5.3.1 |
| L0-SAF-06 | RULE | All safety-critical functionality shall operate on onsite systems under the team's full control, with no dependency on the public internet or public cloud providers. This includes RTL, flight termination, manual piloting, autopilot commanding, and delivery failsafes. | §5.3.5, Appendix B |
| L0-SAF-07 | RULE | The UAS shall pass safety inspection before flight, including a safety checklist verifying operation of all safety features. | §5.2.1, Appendix B |
| L0-SAF-08 | RULE | The team shall submit battery specifications, MSDS, and manufacturer disposal procedures for all batteries; keep hard copies on site; bring adequate LiPo safe bags; inspect batteries daily; and monitor charging batteries at all times. | §5.2.2 |
| L0-SAF-09 | RULE | The team shall have PPE, safety risk mitigation materials (training, checklists, radios), and accident response equipment (first aid kit, fire extinguisher) available. | §5.2 |
| L0-SAF-10 | RULE | The team shall be prepared to rapidly secure all equipment against sudden wind and rain. | §5.1.12 |
| L0-SAF-11 | RULE | The UAS shall be prepared to avoid other teams' UAS. Up to two UAS operate in the airspace simultaneously. Organizers will not deliberately create known collision paths, and inter-team coordination occurs via judges. | §5.3.7 |
| L0-SAF-12 | RULE | The UAS shall operate with some level of autonomy while retaining the ability for manual Safety Pilot takeoff at any time. | §5.3.1 |

## Flight Performance

| ID | Type | Requirement | Source |
|---|---|---|---|
| L0-FLT-01 | RULE | The UAS shall fly waypoints with a maximum error of 100 ft, and the threshold shall be configured in the autopilot. | §3.0.1 |
| L0-FLT-02 | RULE | The ground station shall display a waypoint threshold configured to less than 50 ft. | Appendix B |
| L0-FLT-03 | RULE | The UAS shall achieve a turn radius of 150 ft and remain within the Flight Boundary. | §3.0.1 |
| L0-FLT-04 | RULE | The UAS shall achieve climb and descent angles of 20 degrees. | §3.0.1 |
| L0-FLT-05 | RULE | The UAS shall remain above 150 ft AGL when more than 500 ft from the runway. | §3.0.1 |
| L0-FLT-06 | RULE | The UAS shall remain within the Flight Boundary polygon and within the altitude band [150 ft AGL, 400 ft AGL]. Descent below 150 ft AGL is permitted only for takeoff and landing, and never over a runway occupied by another team. Exceeding the polygon or the altitude band terminates the mission. | §3.0.4 |
| L0-FLT-07 | RULE | The UAS shall take off and land within the assigned runway. Runway 1 is 40 x 500 ft paved, supporting both VTOL and HTOL. Runway 2 is 40 x 40 ft paved, supporting VTOL only. Teams may use only their assigned runway. | §3.0.1, §3.0.2 |
| L0-FLT-08 | RULE | The UAS shall operate in any winds and temperatures experienced at the airfield, including temperatures up to 110 degrees Fahrenheit. | §5.3.11 |
| L0-FLT-09 | INFO | Average September wind speed in Tulsa is approximately 14 mph. Teams do not operate during precipitation but must secure equipment quickly. Fog is acceptable with at least 3 miles visibility. | §5.3.11 |
| L0-FLT-10 | INFO | Terrain elevation within the Flight Boundary varies from 633 to 748 ft MSL, with the runway at approximately 690 ft MSL. Average magnetic deviation is 2 degrees west. Trees within the boundary may reach 100 ft AGL. | §3.0.3 |
| L0-FLT-11 | INFO | The Flight Boundary is an 11-vertex GPS polygon; the Search Boundary is a quadrilateral of approximately 10 acres. Two Search Boundaries exist, one per runway. | §3.0.4, §3.0.5 |

## Mission Conduct and Timeline

| ID | Type | Requirement | Source |
|---|---|---|---|
| L0-MSN-01 | RULE | The team shall set up the UAS and complete the mission within 45 minutes of Mission Time. No setup, including powering on the aircraft or GCS, may begin before Mission Time starts. Judges start the clock when the airspace is available regardless of team readiness. | §3.1.1 |
| L0-MSN-02 | RULE | Mission Time stops once the team has cleared the runway, relinquished the airspace, and submitted all attempted deliverables. No points are awarded for finishing early. | §3.1.1 |
| L0-MSN-03 | RULE | The team shall remove all equipment from the flight line tent area within 10 minutes of teardown time. | §3.1.2 |
| L0-MSN-04 | RULE | All waypoint laps the team intends to attempt shall be flown before entering the Search Boundary for Risk Mapping or Search, Detect, and Deliver. At least one lap shall be flown before entering the Search Boundary. | §3.0.9 |
| L0-MSN-05 | INFO | Waypoint sequences for both flight lines are provided at Check-In, prior to Mission Time. The team must be ready to fly whichever sequence corresponds to its assigned flight line. | §3.2.2 |

## Mission Task: Flight Endurance (250 points)

| ID | Type | Requirement | Source |
|---|---|---|---|
| L0-END-01 | SCORE | At least one successful takeoff and landing, manual or autonomous, earns 20 points. A takeoff is successful once the UAS is above 150 ft AGL; a landing is successful if the UAS touches down without damage to itself or the environment. | §3.2.1, §3.2.3 |
| L0-END-02 | SCORE | Conducting all takeoffs and landings fully autonomously earns 30 points. Fully autonomous means a single command initiates the action; any intervention beyond one button press may be judged non-autonomous. | §3.2.1, §3.2.3 |
| L0-END-03 | SCORE | Flight endurance earns 200 x (N_L / 10)^2 points, where N_L is the number of completed waypoint laps, between 1 and 10. | §3.2.3 |
| L0-END-04 | RULE | A waypoint lap consists of up to 15 waypoints (GPS coordinates and altitudes) and is approximately 2 miles long. The UAS shall pass within 100 ft of each waypoint. | §3.2.2 |
| L0-END-05 | RULE | Laps shall be flown in the specified order, fully autonomously, with no intermediate manual takeover or landing. Partial laps do not count. Once the UAS enters the Search Boundary to perform a task, the lap count is locked. | §3.2.2 |

## Mission Task: Efficient Operators (200 points)

| ID | Type | Requirement | Source |
|---|---|---|---|
| L0-OPR-01 | SCORE | Efficient Operators earns 200 x min(1, (4 - O) / 2) points, where O is the number of operators. Two operators earn the full 200; three earn 100; four earn zero. | §3.3.1 |
| L0-OPR-02 | RULE | The Safety Pilot and GCS Operator shall be dedicated to manual flight override and autopilot operation respectively, and shall perform no other task while the UAS is in flight. Violation terminates the mission. | §3.3 |
| L0-OPR-03 | RULE | Non-operator team members shall stand aside, not communicate with or assist operators, and observe only during Mission Time. They may assist with teardown. Operator assignments shall be declared to judges before the mission and cannot change once it starts. | §3.3 |

## Mission Task: Design for Rapid Response (200 points)

Covered by L0-VEH-02, L0-VEH-03, and L0-VEH-10 through L0-VEH-13.

## Mission Task: Risk Mapping (150 points)

| ID | Type | Requirement | Source |
|---|---|---|---|
| L0-MAP-01 | RULE | The team shall submit an imagery map of the Search Boundary via USB drive within Mission Time. Maps received outside Mission Time receive no points. | §3.5.1 |
| L0-MAP-02 | RULE | The map file shall be .png or .jpeg format and the filename shall include the team name in some form. | §3.5.1 |
| L0-MAP-03 | SCORE | The map earns a sliding 0 to 150 points based on coverage, projection accuracy, stitching, and other quality signals. A high-quality map is indiscernible from a professional map such as Google Maps. A medium-quality map has minor stitch errors, varying exposures, or minor missing coverage. Insufficient quality earns zero. | §3.5.2 |
| L0-MAP-04 | RULE | The map shall cover a larger area and higher resolution than a single photograph can achieve. | §3.5 |
| L0-MAP-05 | RULE | Ground-based imaging sensors shall not be used as a replacement for the UAS imaging payload. | §5.3.5 |

## Mission Task: Search, Detect, and Deliver (200 points)

| ID | Type | Requirement | Source |
|---|---|---|---|
| L0-SDD-01 | RULE | The UAS shall carry all delivery objects it intends to drop simultaneously. Landing to reload payloads is not permitted. | §3.6 |
| L0-SDD-02 | INFO | Delivery objects are provided at the start of Mission Time: a GP908 strobing beacon with 3 AAA batteries installed, approximately 155 g; and an 8 oz plastic water bottle, approximately 255 g, 2 to 2.5 in diameter and 5 to 6 in tall. Bottle brand is not specified, so the system must adapt to minor vendor variation. Both are labeled with a team identifier. | §3.6 |
| L0-SDD-03 | RULE | Each independent delivery payload shall weigh no more than 2 lb, including everything that separates from the UAS. | §3.6.1, Appendix B |
| L0-SDD-04 | RULE | The delivery payload shall contain no means of sustaining flight — no propulsion, propellers, jets, or lighter-than-air elements. | §3.6.1, Appendix B |
| L0-SDD-05 | RULE | Payloads delivered in freefall, with no form of retardant mechanism, shall not be deemed successful. | §3.6.1 |
| L0-SDD-06 | RULE | The delivery payload shall land undamaged, be safe for humans present in the drop area, and be safe to retrieve and handle. | §3.6.1 |
| L0-SDD-07 | RULE | A judge shall be able to separate the delivery object from the delivery payload safely and easily, without tools and without instructions. If the judge cannot separate them, the drop does not count. | §3.6.1 |
| L0-SDD-08 | RULE | The UAS shall remain above the 150 ft AGL minimum altitude fence while conducting deliveries. | §3.6 |
| L0-SDD-09 | RULE | The UAS shall fly at least one full waypoint lap before performing any delivery. Objects delivered without a prior lap earn zero. | §3.6, §3.6.3 |
| L0-SDD-10 | RULE | The UAS shall detect a mannequin and deliver the water bottle to it, and detect a tent and deliver the strobing beacon to it. The tent is an open pop-up variant. The mannequin may be in any orientation, including laying down, sitting up, or face-down, and may be surrounded or covered by bushes, trees, or vehicles. Both are scattered among other debris. | §3.6.2 |
| L0-SDD-11 | SCORE | Each of the two deliveries earns up to 100 points: 20 for the object surviving within the vicinity of the Search Boundary, 50 for landing within 50 ft of a target, and 30 for delivery to the correct target. If multiple payloads are dropped at once, only the best-scoring payload counts. | §3.6.3 |
| L0-SDD-12 | INFO | Judges may be within the Search Boundary scoring drops, and the ground may be marked to identify the 50 ft drop target radius. Targets may be temporarily occluded while judges evaluate another team's drops. | §3.6 |

## Ground Control Station

| ID | Type | Requirement | Source |
|---|---|---|---|
| L0-GCS-01 | RULE | The team shall provide a display, always viewable by the judges, presenting a map showing the flight boundaries, the UAS position, and all other competition elements. Without this display the team may not fly. | §3.0.6 |
| L0-GCS-02 | RULE | The display shall indicate UAS position, ground speed in knots, and altitude in feet AGL. | §3.0.6, Appendix B |
| L0-GCS-03 | RULE | The GCS judge shall have continuous uninterrupted access to a display meeting the above requirements. If judges cannot see the display during the mission, the UAS will not be permitted to take off or will be required to return and land. | §3.0.6, §3.0.8 |
| L0-GCS-04 | RULE | No antenna masts, balloons, or other objects taller than 15 ft shall be used. | §5.3.5 |

## Penalties

| ID | Type | Requirement | Source |
|---|---|---|---|
| L0-PEN-01 | RULE | Excess time is penalized at 0.5% of mission demonstration points per second over the limit. Penalties are unbounded and can zero the mission score. Teams cannot score points while generating a penalty. | §3.8.1, §3.7 |
| L0-PEN-02 | RULE | Each item that falls off the aircraft in flight incurs a 10% penalty. | §3.8.2 |
| L0-PEN-03 | RULE | Each crash, or collision with another team's UAS, incurs a 50% penalty. A team within its own runway's dedicated airspace is not penalized for a collision; only the offending team is. | §3.8.3 |
| L0-PEN-04 | RULE | Each unsafe operation infraction, including failure to respond correctly to judge commands for manual takeover or kill switch, incurs a 50% penalty. | §3.8.4 |
| L0-PEN-05 | RULE | A Flight Boundary breach deemed safety-critical by the GCS judge results in commanded mission termination and return to launch. | §3.8.5 |
| L0-PEN-06 | RULE | Any transition to manual flight, except during takeoff or landing, requires the UAS to return to the start of the waypoint lap. If the UAS lands and takes off again, it must fly at least one waypoint lap before attempting other tasks. | §3.8.6 |
