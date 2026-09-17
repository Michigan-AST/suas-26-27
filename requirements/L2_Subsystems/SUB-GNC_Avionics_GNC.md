# SUB-GNC — Avionics, Guidance, Navigation and Control Subsystem (L2)

**Scope.** Flight controller hardware, inertial and magnetic sensing, GNSS, airspeed and
altitude sensing, attitude and position estimation, control laws for hover and cruise,
failsafe logic, and Remote ID.

**Parent L1 requirements.** MAST-L1-08 (altitude envelope), MAST-L1-09 (VTOL accuracy),
MAST-L1-10 (transition), MAST-L1-11 (wind), MAST-L1-15 (navigation accuracy),
MAST-L1-16 (failsafes), MAST-L1-26 (Remote ID).

---

## Design-driving analysis

### Two mission-ending geometric boundaries

Only two things in this competition terminate the mission outright on geometry: leaving the
Flight Boundary polygon, and leaving the 150 to 400 ft AGL band. Everything else is a penalty.
That makes boundary enforcement a GNC requirement rather than an operator responsibility,
particularly given that the GCS Operator is the only person watching and may do nothing else.

The subtle part is the **AGL reference**. Terrain inside the boundary varies from 633 to 748 ft
MSL while the runway sits near 690 ft MSL. An aircraft holding a constant altitude referenced to
takeoff elevation will be 58 ft lower than commanded over the 748 ft high ground. Against a
150 ft floor, that consumes 39% of the entire margin — and trees to 100 ft AGL consume more.
Barometric altitude referenced to field elevation is therefore not sufficient; the system needs
a terrain model or a conservative floor offset.

### Wind estimation is load-bearing for the delivery task

MAST-L2-PLD-08 requires wind-compensated release, and the error budget in `SUB-PLD` allocates
±1.5 m/s to wind estimate error, contributing 6.9 m of the 8.5 m drop CEP. Wind estimation is
therefore not a nice-to-have telemetry field; it is the single largest contributor to the
highest-difficulty scored task. A tailsitter has an advantage here: it can hover, and the
attitude and thrust required to hold position in hover is itself a direct wind measurement,
independent of the airspeed-versus-groundspeed method used in cruise.

### Magnetic environment

Average magnetic deviation at the field is 2 degrees west, which is trivial to correct. The real
issue is that the aircraft draws 59 A near the airframe during hover, and heading error directly
becomes hover position drift. Compass calibration must be performed with the propulsion current
path in its as-built configuration, and magnetometer placement must be remote from the
high-current run.

---

## L2 — Subsystem requirements

| ID | Requirement | Parents | Rationale |
|---|---|---|---|
| MAST-L2-GNC-01 | The subsystem shall estimate horizontal position to within 1.5 m and altitude AGL to within 1.5 m throughout the flight envelope, using a multi-constellation GNSS receiver with RTK capability retained as a growth option via an onsite base station. | L1-15, L1-17, L2-PER-15 | Feeds the navigation accuracy requirement, the drop error budget, and target geolocation. RTK would reduce the position term in both the drop and geolocation budgets, and an onsite base station is permitted since the constraint is only on internet and cloud dependence. |
| MAST-L2-GNC-02 | The subsystem shall estimate attitude to within 1.0 degree in pitch and roll and 2.0 degrees in heading, using redundant IMUs with automatic fault detection and failover. | L2-PER-15, L1-11 | 1.0 degree is what the geolocation budget assumes; heading accuracy drives hover position hold. An IMU fault in hover is unrecoverable within the reaction time available. |
| MAST-L2-GNC-03 | The subsystem shall navigate to each commanded waypoint with a cross-track error not exceeding 5.0 m, and shall use a waypoint acceptance radius configured below 15.2 m. | L1-15, L0-FLT-01, L0-FLT-02 | The 50 ft acceptance radius is a separately inspected configuration item; 5 m cross-track gives 3x margin. |
| MAST-L2-GNC-04 | The subsystem shall compute altitude AGL against a terrain model or a conservative terrain offset covering the 633 to 748 ft MSL variation within the Flight Boundary, not against a single field-elevation datum. | L1-08, L0-FLT-10 | Without this, level flight referenced to the runway breaches the 150 ft AGL floor over high terrain, which terminates the mission. |
| MAST-L2-GNC-05 | The subsystem shall enforce the Flight Boundary polygon and the 150 to 400 ft AGL band as hard geofences, initiating a defined recovery action before the boundary is crossed rather than after, with the published 11-vertex polygon and both Search Boundary quadrilaterals loadable as configurable parameters. | L1-08, L0-FLT-06, L0-PEN-05, L0-FLT-11 | Mission-ending on breach. Predictive rather than reactive enforcement because a 25 m/s aircraft covers 25 m in the second it takes to react. Loading boundaries as data avoids a firmware change and keeps the design-lock configuration stable. |
| MAST-L2-GNC-06 | The subsystem shall hold hover position within 3.0 m horizontally and 1.5 m vertically in sustained 6.3 m/s wind with gusts to 9.8 m/s. | L1-11, L1-09, L2-PLD-07 | Drives the drop accuracy budget and the VTOL touchdown accuracy. |
| MAST-L2-GNC-07 | The subsystem shall estimate wind velocity to within 1.5 m/s in magnitude and 10 degrees in direction, using a dedicated airspeed sensor with a pitot-static source outside rotor wash, and shall publish the estimate to the payload release computation and to the GCS. | L2-PLD-08, L1-17 | Largest single term in the drop error budget. Transition scheduling and wind estimation both require true airspeed, and rotor wash corrupts the measurement. |
| MAST-L2-GNC-08 | The subsystem shall execute fully autonomous vertical takeoff and vertical landing, each initiated by exactly one operator command, with touchdown within 3.0 m of the commanded point. | L0-END-02, L1-09, L1-13 | The handbook states any intervention beyond a single command may be judged non-autonomous, forfeiting 30 points. |
| MAST-L2-GNC-09 | The subsystem shall execute hover-to-cruise and cruise-to-hover transitions autonomously per the MAST-L2-PRP-08 schedule with no operator input, using a flight controller whose firmware supports a VTOL tailsitter configuration natively including transition scheduling and dual-attitude control law sets. | L1-10, L1-13 | Manual intervention during a lap forces a lap restart. Writing tailsitter transition control from scratch is a multi-season effort; both major open-source autopilot stacks already support it, and adopting one is the single largest schedule risk reduction available. |
| MAST-L2-GNC-10 | The subsystem shall provide return-to-land and flight termination functions, each independently commandable by the Safety Pilot via a manual control link and by the GCS Operator via the telemetry link, with the two command paths independent in hardware and frequency band. | L0-SAF-01, L0-SAF-02, L1-16 | Independence of the two command paths is inspected; a shared path would not satisfy it, and a shared band would fail simultaneously under interference. |
| MAST-L2-GNC-11 | The subsystem shall automatically initiate return-to-land after 15 s of continuous loss of both command links, and flight termination after 90 s. | L0-SAF-03, L0-SAF-04, L1-16 | Inspected behaviour with specific timings. |
| MAST-L2-GNC-12 | Flight termination shall command the surface and throttle configuration appropriate to the aircraft's current flight mode, and the applicable configuration for a tailsitter shall be confirmed with organisers. | L0-SAF-02 | Appendix B gives distinct fixed-wing and rotary terminations; a tailsitter's applicable case is ambiguous. See open question 2 in `L0_Reconciliation_Notes.md`. |
| MAST-L2-GNC-13 | Manual Safety Pilot override shall be available at any time in any flight mode, taking effect within 200 ms of command. | L0-SAF-05, L0-SAF-12, L0-PEN-04 | Failure to respond to a judge's manual takeover command is a 50% penalty. |
| MAST-L2-GNC-14 | All failsafe and override logic shall execute onboard, with no dependency on the GCS, the internet, or any cloud service. | L0-SAF-06, L1-28 | Explicitly inspected. |
| MAST-L2-GNC-15 | The subsystem shall broadcast Remote ID containing a unique vehicle identifier and vehicle position, using a self-contained module with its own position source and an unobstructed antenna path. | L0-REG-02, L1-26 | Inspected. Self-contained modules decouple compliance from flight controller firmware and are explicitly permitted as a post-design-lock addition, making this a low-risk item to defer. |
| MAST-L2-GNC-16 | The subsystem shall log all state estimates, commands, and mode transitions at no less than 10 Hz, retained onboard for at least 4 complete missions without overwrite. | L1-27, L2-PRP-10 | Transition tuning, thermal margin, and boundary margin are all empirical and iterate through flight test. Four missions covers two competition flights plus test flights without a laptop download between them. |
| MAST-L2-GNC-17 | Sensor and estimator performance shall be unaffected by temperatures up to 43.3 °C, and static pressure sensing shall be insensitive to the 90 degree attitude change between hover and cruise. | L1-12, L2-GNC-04 | IMU bias drift over temperature feeds the geolocation budget. A tailsitter rotates its entire body, so any static port sensitivity to attitude appears as an altitude step during transition — directly against the 15 m transition excursion budget. |
| MAST-L2-GNC-18 | The magnetometer shall be mounted at least 150 mm from any conductor carrying more than 10 A, and compass calibration shall be performed with propulsion wiring in its as-built configuration. | L2-GNC-02, L2-GNC-06 | 59 A of hover current near the airframe is the dominant heading error source, and heading error becomes hover drift. |
| MAST-L2-GNC-19 | The subsystem shall expose aircraft position, ground speed, and AGL altitude to the GCS at no less than 4 Hz, and shall accept either flight line's waypoint sequence loaded at the field within 120 s without a firmware rebuild. | L2-GCS-02, L0-GCS-02, L0-MSN-05 | Defines the interface supporting the judge-viewable display. Both sequences are issued at Check-In and the assigned line is not known until the mission, so loading is on the Mission Clock. |
