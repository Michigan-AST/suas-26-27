# MAST — SUAS 2026 Requirements Baseline

Requirements for a **tailsitter VTOL** entry to the 2026 Student Unmanned Aerial Systems
competition, decomposed from the competition handbook down to subsystem level.

---

## Documents

| File | Contents |
|---|---|
| `L0_Reconciliation_Notes.md` | Differences between the original CSV summary and the official handbook. **Read this first** — it documents two inverted constraints and five open questions for the judges. |
| `L0_Competition_Requirements.md` | 91 externally imposed competition requirements, each traced to a handbook section and tagged RULE, SCORE, or INFO. |
| `L1_System_Requirements.md` | 28 system-level requirements, plus the mission clock budget and energy budget that most of them derive from. |
| `L2_Subsystems/` | Ten subsystem documents containing 170 L2 subsystem requirements. |
| `Requirements_Traceability_Matrix.csv` | All 289 requirements with their parent links, for spreadsheet review and coverage auditing. |
| `System Requirements Review - Sheet1.csv` | Original summary. Superseded by the L0 document; retained for history. |
| `2026_SUAS_HANDBOOK.pdf` | Official handbook. Has no extractable text layer, so the baseline was taken from the published web version. |

## Subsystem documents

| Code | Subsystem | L2 count |
|---|---|---|
| `AIR` | Airframe and Structures | 18 |
| `PRP` | Propulsion and Transition | 16 |
| `PWR` | Power and Electrical | 14 |
| `GNC` | Avionics, Guidance, Navigation and Control | 19 |
| `COM` | Communications | 15 |
| `PLD` | Payload Delivery | 18 |
| `PER` | Imaging and Perception | 20 |
| `ASW` | Autonomy and Flight Software | 19 |
| `GCS` | Ground Control Station | 14 |
| `OPS` | Ground Support and Operations | 17 |

---

## Identifier scheme

```
L0-<DOMAIN>-<nn>            Competition requirement, externally imposed
MAST-L1-<nn>                System requirement
MAST-L2-<SUB>-<nn>          Subsystem requirement
```

L0 domains are `ELG` (eligibility), `DOC` (documentation), `REG` (regulatory), `VEH` (vehicle),
`SAF` (safety), `FLT` (flight performance), `MSN` (mission conduct), `END` (endurance task),
`OPR` (operators task), `MAP` (mapping task), `SDD` (search detect deliver task), `GCS`, and
`PEN` (penalties).

IDs are permanent. A requirement that is withdrawn is marked superseded rather than deleted, and
numbers are never reused. Within a document, parents are sometimes written in short form
(`L1-17` rather than `MAST-L1-17`); the traceability matrix always uses full form.

**L2 is the lowest level in this baseline.** It stops at "what each subsystem must achieve" and
deliberately leaves "which part to buy and how to wire it" to the subsystem leads. Where a
component-level choice genuinely determines whether an L2 requirement can be met — a
tailsitter-capable autopilot, hardware capture timestamping, keyed rotor positions, measured
rather than estimated payload ballistics — that constraint is stated inside the relevant L2
requirement rather than spun out as a separate item to track.

## How to use this baseline

Each requirement states a parent and a rationale. The rationale exists so that when a
requirement becomes inconvenient — and the mass and cruise-speed requirements will — you can
see what it is protecting and make an informed decision instead of quietly relaxing it. If you
change a requirement value, update the rationale in the same edit.

Two things are deliberately absent because they were not requested: verification methods
(inspection, analysis, demonstration, test) per requirement, and formal mass, power, and RF link
budgets as standalone artifacts. Simplified mass, energy, and timeline analyses appear inline in
`L1_System_Requirements.md` where they were needed to justify a number. Both additions are
straightforward to layer on.

---

## Where the design is tightest

Five findings came out of the decomposition and are worth carrying into design reviews.

**Mass is the binding constraint, not endurance.** The 15 lb target leaves roughly 7 lb for
airframe, propulsion, avionics, and payload bay once 4 lb of battery and up to 4 lb of delivery
payloads are accounted for. Every other requirement gets harder as mass grows, because hover
power scales with weight to the 1.5 power. `MAST-L1-01` should be the standing agenda item.

**The 45-minute clock, not battery energy, limits lap count.** The mission clock budget in
`L1_System_Requirements.md` Appendix A closes with only 60 seconds of margin, and it is what
sets the 25 m/s cruise requirement. Because Flight Endurance scores as the square of lap count,
schedule slip converts directly and non-linearly into lost points.

**Payload delivery does not close without active wind compensation.** Release must be above
150 ft AGL and freefall is prohibited, so the payload drifts under a drag device. At the average
14 mph wind, an uncompensated drop lands 2 to 4 times further from the target than the scoring
radius allows, depending on the retardant. The analysis and the resulting error budget are in
`L2_Subsystems/SUB-PLD_Payload_Delivery.md`.

**Hover gust rejection is the configuration's main exposure.** A tailsitter presents its whole
wing as a sail in hover, and a 22 mph gust produces a side force equal to 63% of the aircraft's
weight, resisted only by differential rotor thrust. This is why `MAST-L2-PRP-04` specifies a
control moment rather than just a thrust-to-weight ratio. The handbook sets no wind limit at
all, so there is no rule protecting you here.

**Two operators is effectively mandatory, and it forces full automation.** Four operators, the
maximum the rules allow, scores zero. With two operators who may do nothing but safety-pilot and
supervise while airborne, there is nobody to stitch a map or pick a target, so the entire
perception and delivery chain must be autonomous. This single scoring rule shapes the software
architecture more than any technical consideration.

Two places where the configuration pays off are worth stating too, since they belong in the
Technical Design Report. Releasing from hover removes the forward-throw term from the delivery
problem that a fixed-wing team cannot escape. And VTOL capability means the team can be assigned
either runway, including the 40 x 40 ft VTOL-only pad, whereas conventional aircraft are
restricted to one.

---

## Coverage notes

Every L0 requirement tagged RULE or SCORE that constrains the aircraft or its operation has at
least one derived child. The following L0 items are intentionally not decomposed because they
are programmatic or documentation obligations rather than engineering requirements, and they are
satisfied by team process rather than by design: `L0-ELG-01`, `L0-ELG-02`, `L0-ELG-05`,
`L0-ELG-06`, `L0-DOC-01`, `L0-DOC-02`. `L0-VEH-04` (heavier-than-air, untethered) and
`L0-SDD-12` (judges may occupy the Search Boundary) are satisfied inherently by the
configuration. This list is stated explicitly so that a coverage audit of the traceability
matrix does not read these as gaps.

The five open questions in `L0_Reconciliation_Notes.md` each affect a requirement value and
should be resolved with organisers before design freeze. The most consequential is the first:
whether the 3-minute unpack demonstration runs on the Mission Clock, which determines whether
`MAST-L1-03` and `MAST-L2-OPS-03` can be relaxed from 2 people to 4.
