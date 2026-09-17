# SUB-GCS — Ground Control Station Subsystem (L2)

**Scope.** Operator console hardware, the judge-viewable display, map and telemetry
presentation, command interfaces for failsafes, the USB deliverable export path, and ground
power.

**Parent L1 requirements.** MAST-L1-14 (two operators), MAST-L1-16 (failsafes),
MAST-L1-18 (link), MAST-L1-20 (map submission), MAST-L1-28 (onsite independence).

---

## Design-driving analysis

### The display is a gate, not a convenience

The handbook is unusually blunt: teams "will not be able to fly" without a judge-viewable
display, and if judges cannot see it during the mission the aircraft "will not be permitted to
take off and/or required to return to land" (L0-GCS-01, L0-GCS-03). The GCS judge sits with the
GCS Operator and must have continuous uninterrupted access.

This makes the display a single point of mission failure with no redundancy in the rules. A
laptop that sleeps, dims, overheats in direct sun at 43 °C, or loses its window focus can end
the mission. The requirements below treat sunlight readability and power robustness as
mission-critical rather than ergonomic.

### Mandated display content is specific and inspected

Appendix B lists exactly what is checked: a map with flight boundaries, UAS position, and a
waypoint threshold configured to less than 50 feet; UAS ground speed in **knots**; and altitude
in **feet AGL**. The units are prescribed. A display showing metres per second or MSL altitude
fails inspection even if the underlying data is correct.

---

## L2 — Subsystem requirements

| ID | Requirement | Parents | Rationale |
|---|---|---|---|
| MAST-L2-GCS-01 | The GCS shall provide a display positioned and oriented for continuous, uninterrupted viewing by the GCS judge simultaneously with the GCS Operator, of at least 13 in diagonal. | L0-GCS-01, L0-GCS-03 | Loss of judge visibility prevents takeoff or forces a landing. Size is set so judge and operator can both read it from their seated positions. |
| MAST-L2-GCS-02 | The display shall present a map showing the Flight Boundary, the Search Boundary, the commanded waypoints with their acceptance radii, the aircraft position, and the aircraft track, using pre-cached offline basemap tiles. | L0-GCS-01, L0-FLT-02, L1-28 | "All other competition elements" is required; boundaries and waypoint thresholds are named explicitly. There is no reliable internet at a rural range, and the display is a flight gate. |
| MAST-L2-GCS-03 | The display shall present aircraft ground speed in knots and altitude in feet AGL, and shall show the configured waypoint acceptance threshold as a value below 50 ft. | L0-GCS-02, L0-FLT-02 | Units are prescribed by the handbook and verified at inspection. |
| MAST-L2-GCS-04 | The display shall present current mission phase, completed lap count, remaining battery energy as a percentage and in Wh, link quality, wind estimate, declared target positions, and a countdown of elapsed Mission Time against the 45-minute limit. | L2-ASW-04, L2-PWR-10, L2-COM-10, L2-GNC-07, L0-PEN-01 | The GCS Operator's entire permitted role in flight is supervision, so every decision-relevant quantity must be visible without navigation. Overrun is charged at 0.5% of mission points per second, and the decision to stop flying laps depends on the clock. |
| MAST-L2-GCS-05 | The display shall remain readable in direct sunlight at 43.3 °C ambient, with a screen luminance of at least 1000 cd/m² and a hood or canopy, and the GCS computer shall not thermally throttle at that ambient. | L1-12, L0-GCS-03 | A display the judge cannot read is a display the judge cannot see. Typical laptop panels at 250 to 300 cd/m² are unreadable in open-field Oklahoma sun, and a throttled or shut-down console ends the mission. |
| MAST-L2-GCS-06 | The GCS shall provide dedicated, clearly labelled, physically distinct and guarded controls for return-to-land and flight termination, each requiring a deliberate action and each operable by the GCS Operator without navigating a menu. | L0-SAF-01, L0-SAF-02, L2-GNC-10 | Both must be activatable by the GCS Operator independently of the Safety Pilot, and both are exercised during safety inspection. Confusing the two under pressure either aborts a recoverable situation or fails to terminate an unrecoverable one. |
| MAST-L2-GCS-07 | Failsafe commands issued from the GCS shall not depend on the internet or any cloud service, and shall function with the GCS fully disconnected from any external network. | L0-SAF-06, L1-28 | Explicitly enumerated in the handbook as safety-critical functionality that must be under the team's full control. |
| MAST-L2-GCS-08 | The GCS shall operate for at least 90 minutes on self-contained power of at least 200 Wh with state-of-charge indication, drawn from a battery separate from the aircraft packs. | L0-MSN-01, L0-MSN-03 | A 45-minute mission plus setup and teardown, twice, since the handbook intends to give every team two flights. Ground batteries are not subject to the sub-100 Wh aircraft rule but are still covered by the battery documentation requirements. |
| MAST-L2-GCS-09 | The GCS shall inhibit all power management behaviour that could blank, sleep, or dim the display during a mission. | L0-GCS-03 | A screen blanking event is functionally identical to hiding the display from the judge. |
| MAST-L2-GCS-10 | The GCS shall provide a single-action export of the completed risk map to a judge-supplied USB mass storage device, supporting FAT32 and exFAT without operator configuration, with read-back verification and an unambiguous completion indication. | L1-20, L2-PER-11 | Worth 150 points, performed on the Mission Clock at 0.5% of mission points per second, by an operator who has just landed the aircraft. The drive is handed over at the start of Mission Time and its formatting is unknown. |
| MAST-L2-GCS-11 | All GCS equipment including antennas and supports shall be within 15 ft in height and shall pack into transportable cases removable from the flight line tent area within 10 minutes. | L0-GCS-04, L0-MSN-03 | Height is a rule; the 10-minute teardown is a separate timed requirement. |
| MAST-L2-GCS-12 | The GCS shall be set up, powered, and linked to the aircraft within the setup allocation of the mission clock budget, with no setup begun before the clock starts, connecting to the telemetry radio over a wired interface with the radio mounted at the antenna. | L0-MSN-01, L1-03, L2-COM-12 | Powering on the GCS before the clock starts is explicitly prohibited, so boot time is on the clock. Mounting the radio at the antenna preserves the link margin of MAST-L2-COM-02. |
| MAST-L2-GCS-13 | The GCS shall log all telemetry received and all commands issued, timestamped, for post-mission analysis. | L2-GNC-16, L2-COM-10 | Independent ground record for diagnosing link events and for design report evidence. |
| MAST-L2-GCS-14 | The GCS shall present a preflight checklist that the operators complete and that covers every safety inspection item verifiable at the console. | L0-SAF-07, L0-SAF-09 | The handbook requires checklists as safety risk mitigation, and a two-operator team under a running clock will otherwise skip steps. |
