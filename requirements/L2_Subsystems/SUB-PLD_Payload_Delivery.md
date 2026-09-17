# SUB-PLD — Payload Delivery Subsystem (L2)

**Scope.** Payload bays, retention and release mechanisms, descent retardant devices, payload
carriers, object-to-carrier interfaces, and the release-point computation.

**Parent L1 requirements.** MAST-L1-17 (placement accuracy), MAST-L1-01 (mass),
MAST-L1-23 (no part departure).

---

## Design-driving analysis: why this is the hardest task in the competition

Two rules interact badly. Release must occur **above** 45.7 m (150 ft) AGL (L0-SDD-08), and
freefall delivery is explicitly **not** credited (L0-SDD-05). So the payload must spend several
seconds descending under a drag device, during which the wind advects it horizontally, and it
must still land within 15.2 m (50 ft) of the target.

Once a payload reaches terminal velocity it drifts with the wind at essentially the full wind
speed. Descent time is approximately `h / Vt`, and drift is `Vw * t`. At the 14 mph (6.3 m/s)
September average from a 45.7 m release:

| Terminal velocity Vt | Descent time | Uncompensated drift | Within 15.2 m? |
|---|---|---|---|
| 5 m/s (conventional parachute) | 9.1 s | 57.6 m | No — 3.8x over |
| 8 m/s | 5.7 s | 36.0 m | No — 2.4x over |
| 10 m/s | 4.6 s | 28.8 m | No — 1.9x over |
| 12 m/s | 3.8 s | 24.0 m | No — 1.6x over |
| 15 m/s | 3.0 s | 19.2 m | No — 1.3x over |
| 20 m/s | 2.3 s | 14.4 m | Marginally |

**No achievable retardant device closes this requirement by drag alone.** A conventional
parachute is the worst possible choice. Even a device fast enough to be borderline unsafe leaves
no margin. Active wind compensation at the release point is therefore mandatory.

With compensation — releasing upwind of the target by the predicted drift — the residual error
is driven by how well the wind and the ballistics are known, not by the drift itself. Taking
Vt = 10 m/s (a deliberate choice: slow enough to protect the object and the judges in the drop
area, since a 907 g payload at 15 m/s carries 102 J, versus 45 J at 10 m/s):

| Error source | Magnitude | Contribution at t = 4.6 s |
|---|---|---|
| Wind velocity estimate error | ±1.5 m/s | 6.9 m |
| Terminal velocity uncertainty | ±15% (±0.69 s) | 4.3 m |
| Aircraft position error (GNSS) | 1.5 m | 1.5 m |
| Hover position hold error | 2.0 m | 2.0 m |
| Release timing and mechanism scatter | — | 0.5 m |
| **Root-sum-square** | | **8.5 m CEP** |

8.5 m CEP against a 15.2 m radius, combined with the 5.0 m target geolocation error from
MAST-L1-19, gives `sqrt(8.5^2 + 5.0^2) = 9.9 m` — inside the scoring radius with 35% margin.
This closes, but only because of the release-from-hover decision below.

**The tailsitter configuration is a genuine competitive advantage here.** Releasing from hover
removes the forward-throw term entirely. A fixed-wing aircraft releasing at 25 m/s throws the
payload roughly 67 m downrange and must predict that throw as well as the wind, with release
timing error scaling at 25 m per second of latency. From hover, a 100 ms timing error moves the
impact point by centimetres. This is the strongest mission-level argument for the configuration
choice and belongs in the Technical Design Report.

---

## L2 — Subsystem requirements

| ID | Requirement | Parents | Rationale |
|---|---|---|---|
| MAST-L2-PLD-01 | The subsystem shall carry two independent delivery payloads simultaneously and release each independently. | L0-SDD-01, L1-17 | Reloading by landing is prohibited, and the two objects go to different targets, so both must be aboard and separately commandable. |
| MAST-L2-PLD-02 | Each complete delivery payload, including object, carrier, retardant device, and all hardware that separates from the aircraft, shall not exceed 907 g (2 lb). | L0-SDD-03 | Inspected at safety inspection. Note this is a per-payload allowance, not a total — see `L0_Reconciliation_Notes.md` §1.5. |
| MAST-L2-PLD-03 | Total delivery payload mass allocation, both payloads combined, shall not exceed 1400 g. | L1-01, L0-SDD-03 | Derived mass allocation, not a rule. The rules permit 1814 g across both payloads, but Appendix B of the L1 document leaves only about 3.2 kg for airframe, propulsion, avionics, and payload bay after battery. Spending the full rule allowance on payloads would break the 15 lb target. |
| MAST-L2-PLD-04 | Each payload shall incorporate a passive retardant device reducing impact velocity to between 8 and 12 m/s, with the as-built terminal velocity of each configured payload established by drop test rather than by estimate. | L0-SDD-05, L0-SDD-06, L1-17 | Lower bound from the drift analysis above: below 8 m/s the compensated error budget no longer closes. Upper bound from object survival and from the requirement that the payload be safe for humans present in the drop area. Terminal velocity uncertainty contributes 4.3 m of the 8.5 m error budget, so measuring it rather than predicting it is the cheapest available accuracy improvement. |
| MAST-L2-PLD-05 | The retardant device shall deploy within 0.5 s of release and shall achieve terminal velocity within 1.0 s. | L1-17 | The error budget assumes terminal velocity is reached almost immediately. A slow-deploying device adds an unmodelled acceleration phase and shifts the impact point unpredictably. A ribbon or drag-skirt decelerator deploys faster and more repeatably than a canopy parachute, and suffers less from partial-inflation scatter — which is the dominant term in the terminal-velocity uncertainty. |
| MAST-L2-PLD-06 | The retardant device shall contain no means of sustaining flight — no propulsion, propeller, jet, aerodynamic lift-generating surface producing net thrust, or lighter-than-air element. | L0-SDD-04 | Explicitly inspected. Rules out autogyro and powered-descent concepts; permits streamers, drag skirts, ribbon decelerators, and parachutes. |
| MAST-L2-PLD-07 | The subsystem shall release payloads from a hover or near-hover state with horizontal ground speed not exceeding 2.0 m/s. | L1-17, L1-11 | Eliminates the forward-throw term and reduces release-timing sensitivity from metres per 100 ms to centimetres. This is the decision that makes the accuracy budget close. |
| MAST-L2-PLD-08 | The subsystem shall compute release position by compensating for estimated wind velocity, release altitude AGL, and payload ballistic properties, and shall inhibit release until predicted impact lies within 10.0 m of the assigned target. | L1-17, L1-28 | The inhibit is as important as the computation: a release commanded with a bad wind estimate wastes an irreplaceable payload. Release inhibit is named in the handbook as safety-critical functionality and so must run onsite (L0-SAF-06). |
| MAST-L2-PLD-09 | Release shall occur at an altitude between 45.7 m and 53.0 m AGL. | L0-SDD-08, L0-FLT-06 | Floor is the rule; the 7.3 m band above it bounds descent-time uncertainty while staying well clear of the 400 ft ceiling. Releasing higher would add drift for no benefit. |
| MAST-L2-PLD-10 | The retention mechanism shall hold both payloads through all flight phases including 1.72 g manoeuvre, hover-attitude rotor loads, transition, and landing impact, with no unintended release. | L0-VEH-07, L0-PEN-02, L1-22 | An unintended release is a 10% penalty as a part departing the aircraft and forfeits the delivery. |
| MAST-L2-PLD-11 | The retention mechanism shall be fail-safe to the retained state on loss of power or loss of command, shall be commanded on outputs isolated from flight-control and propulsion outputs, and shall provide a ground-engageable mechanical interlock independent of electrical state. | L0-SAF-06, L1-16, L1-24 | A release triggered by a brownout during the 90 s comms-loss window would drop a payload outside the Search Boundary. Output isolation prevents a mixer misconfiguration from triggering a release. The mechanical interlock covers ground safety while the aircraft is powered with payloads loaded during setup. |
| MAST-L2-PLD-12 | A judge shall be able to separate the delivery object from the carrier using hands only, without tools and without instructions, in under 10 s and with no more than 30 N of force. | L0-SDD-07 | If the judge cannot separate them the drop does not count, regardless of accuracy. The "without instructions" clause means the interface must be self-evident to someone who has never seen it; 30 N is comfortably within one-handed capability for an unprepared user wearing gloves. |
| MAST-L2-PLD-13 | The water bottle carrier shall accommodate bottles of 50 to 64 mm diameter and 127 to 152 mm height with no adjustment or tooling. | L0-SDD-02 | The handbook states no brand is specified and teams must adapt to vendor variation across a 2.0 to 2.5 in diameter and 5 to 6 in height range. The carrier is sized to the full stated range because the actual bottle is not seen until Mission Time begins. |
| MAST-L2-PLD-14 | The beacon carrier shall accommodate the GP908 strobing beacon with 3 AAA cells installed, approximately 155 g, without obstructing the strobe. | L0-SDD-02 | Geometry is published as an STL by the organizers, so this interface can be designed to a known shape rather than a tolerance band. |
| MAST-L2-PLD-15 | Payloads shall be loadable into the aircraft, in flight-ready condition, within 45 s per payload by one operator, with the aircraft assembled and resting in its ground cradle. | L1-03, L0-MSN-01 | Objects are handed over at the *start* of Mission Time, so loading is on the clock and inside the 420 s setup allocation of the L1 Appendix A budget. |
| MAST-L2-PLD-16 | Payload bays shall be positioned so that releasing either payload, or both, shifts the centre of gravity within limits that preserve hover and cruise controllability. | L1-10, L1-11 | Asymmetric release is the normal case: the two payloads go to two different targets, so the aircraft flies with one payload gone. For a tailsitter this matters in both axes because the body rotates 90 degrees between phases. |
| MAST-L2-PLD-17 | Release of one payload shall not disturb retention or deployment of the other. | L0-SDD-11, L1-17 | If multiple payloads are dropped at once, only the best-scoring one counts, so an inadvertent double release forfeits up to 100 points. |
| MAST-L2-PLD-18 | The subsystem shall publish predicted impact point to the flight software and the GCS at no less than 5 Hz while in the delivery phase, and shall present no sharp edges, pinch points, or protruding hardware on any surface a judge handles. | L2-PLD-08, L0-SDD-06 | 5 Hz gives the operator and the autopilot a stable convergence indication during the hover approach. The payload must be safe to retrieve and handle, and must carry the team identifier. |
