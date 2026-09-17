# SUB-PWR — Power and Electrical Subsystem (L2)

**Scope.** Battery packs and pack architecture, power distribution, avionics power conversion,
wiring, connectors, current and voltage sensing, and the propulsion power disconnect.

**Parent L1 requirements.** MAST-L1-05 (energy), MAST-L1-21 (battery packaging),
MAST-L1-12 (thermal), MAST-L1-24 (propeller interlock).

---

## Design-driving analysis

### The sub-100 Wh rule forces a multi-pack architecture

The 75 points for all-packs-below-100 Wh is the largest single sub-item in Design for Rapid
Response — larger than the weight component, larger than any sizing tier. It constrains pack
*packaging*, not total energy: the handbook places no limit on installed capacity or on the
number of packs.

Requiring 330 Wh installed (L1 Appendix B) across packs each below 100 Wh means at least four
packs. Two architecture options follow, and they are not equivalent:

**Series-connected packs.** Four 82.5 Wh packs in series at, say, 6S each gives 24S — far too
high for typical ESCs. Practical series arrangements use 3S or 4S packs to reach 12S or 16S.
Series connection means a single cell failure disables the whole string, and pack-to-pack
capacity mismatch causes the weakest pack to limit usable energy.

**Parallel-connected packs.** Four 6S packs in parallel at 82.5 Wh each gives 22.2 V nominal
and 330 Wh. Parallel is fault-tolerant and allows any pack to be swapped between flights, but
requires either matched packs or per-pack isolation diodes or FETs to prevent inter-pack current
surges when connecting packs at different states of charge.

The requirements below mandate per-pack isolation because the alternative — hand-matching pack
voltages under a 45-minute clock with two operators — is an operational error waiting to happen
on competition day.

### Peak current occurs at the worst moment

Hover draws 1166 W. At a 22.2 V nominal bus that is 52 A, but at end-of-discharge the pack sags
toward 19.8 V, so the current rises to 59 A — and the highest-power hover of the mission is the
final landing, at the lowest state of charge. Sizing the wiring and C-rating for nominal voltage
understates the real peak by about 13%.

---

## L2 — Subsystem requirements

| ID | Requirement | Parents | Rationale |
|---|---|---|---|
| MAST-L2-PWR-01 | The power system shall provide at least 330 Wh of installed capacity, with at least 293 Wh usable, using cells of at least 180 Wh/kg specific energy so that total pack mass does not exceed 1.83 kg. | L1-05, L1-21, L1-01 | From L1 Appendix B: 244 Wh mission energy plus 20% reserve, at 95% usable depth of discharge. The mass allocation depends on the specific energy figure; a lower value directly breaks the 15 lb target. |
| MAST-L2-PWR-02 | Every individually packaged battery shall have a rated capacity below 100 Wh, verified against manufacturer specification, and shall use a commercially available lithium chemistry rather than an exotic or experimental one. | L0-VEH-13, L1-21, L0-VEH-01 | Worth 75 points. "Individually packaged" is the operative phrase: a pack is what the judge can pick up as one unit. The handbook prohibits exotic batteries and reserves the right to deny any option judged high risk. |
| MAST-L2-PWR-03 | Battery packs shall be connected with per-pack isolation, implemented with ideal-diode or FET-based controllers rather than plain Schottky diodes, such that packs at differing states of charge can be connected in any order without inter-pack surge current and a single pack fault does not disable the aircraft. | L1-21, L0-MSN-01 | Operational robustness under a 45-minute clock with two operators; removes pack voltage matching from the setup procedure entirely. At 15 A per pack a Schottky drop of 0.4 V dissipates 6 W per pack and wastes about 8 Wh over the mission. |
| MAST-L2-PWR-04 | The power system shall deliver at least 59 A continuous at end-of-discharge voltage without exceeding conductor or connector ratings, with each pack rated for at least 1.5x its share of that peak and all wiring sized for a conductor temperature rise not exceeding 30 °C above 43.3 °C ambient. | L2-PRP-01, L1-12 | Sized at sagged voltage, not nominal; the peak hover occurs at the final landing when the pack is nearly empty. The 1.5x margin covers pack aging, cell imbalance, and elevated temperature. Peak current and peak ambient coincide, which is when insulation is most at risk. |
| MAST-L2-PWR-05 | Each battery pack shall be brightly coloured, or wrapped in brightly coloured tape, for identification in a crash. | L0-VEH-05 | Explicit rule, inspected. |
| MAST-L2-PWR-06 | Each battery pack shall be removable and installable by hand, without tools and without disassembly of any structural joint, in under 15 s per pack, using polarity-protected connectors rated for at least 500 mating cycles. | L0-VEH-05, L1-21, L1-03 | The rule requires no vehicle deconstruction. The 15 s figure keeps four packs inside the 180 s assembly budget. Packs are removed after every flight across a season of testing. |
| MAST-L2-PWR-07 | The avionics bus shall be electrically isolated from the propulsion bus such that propulsion current transients do not brown out avionics, compute, or imaging payload, and shall supply at least 5 A at 5 V plus the compute module rail at no less than 90% combined efficiency. | L1-12, L2-PER-20 | A compute reset during hover costs the map and the detections; a flight controller reset costs the aircraft. Sized for flight controller, GNSS, radios, camera, and inference compute concurrently. |
| MAST-L2-PWR-08 | The avionics bus shall be supplied with redundancy such that failure of any single regulator does not remove power from the flight controller. | L0-SAF-01, L1-16 | Failsafe behaviour is meaningless if the controller executing it is unpowered. |
| MAST-L2-PWR-09 | Battery pack temperature shall remain below manufacturer limits during the full mission discharge at 43.3 °C ambient in direct sunlight, monitored on at least one pack and logged at no less than 1 Hz. | L1-12, L0-SAF-08 | Both a performance and a safety requirement; swollen or hot packs must be removed from use per the handbook. Logged history makes degradation visible before it becomes a safety event. |
| MAST-L2-PWR-10 | The system shall measure and report pack voltage, current, and consumed capacity to the GCS at no less than 2 Hz, with current and voltage sensing accurate to 1%. | L1-05, L2-GCS-04 | The 20% reserve is only meaningful if the GCS Operator can see it approaching, and the operator cannot do anything else in flight but watch. 1% error over a 244 Wh mission is 2.4 Wh. |
| MAST-L2-PWR-11 | The system shall provide a manual, visually unambiguous propulsion power disconnect, operable without tools, that removes power from all motors while leaving avionics powered, and whose state is identifiable from outside every propeller arc. | L1-24, L0-VEH-08 | Explicitly inspected; enables ground work and preflight checks without a live propeller arc. An operator must be able to confirm it is safe *before* approaching, not after. |
| MAST-L2-PWR-12 | Battery documentation including specifications, MSDS, and manufacturer disposal procedures shall be available in hard copy on site for every pack used, with LiPo-safe bags adequate for every pack on the ground equipment manifest. | L0-SAF-08 | Required submission and an on-site inspection item. |
| MAST-L2-PWR-13 | No battery shall be swapped, charged, or otherwise serviced while on the Mission Clock. | L0-VEH-09 | Explicit rule. Reinforces that MAST-L2-PWR-01 must close on a single load. |
| MAST-L2-PWR-14 | Wiring and connectors shall be secured such that no conductor, connector, or retention component can depart the aircraft in flight. | L0-VEH-07, L1-23 | 10% penalty per item. |
