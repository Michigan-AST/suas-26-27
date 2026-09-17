# SUB-AIR — Airframe and Structures Subsystem (L2)

**Scope.** Wing, fuselage, control surfaces, rotor booms and nacelles, joints and disassembly
interfaces, landing and ground-resting structure, payload bay structure, battery bays, and
external markings.

**Parent L1 requirements.** MAST-L1-01 (mass), MAST-L1-02 (stowed volume),
MAST-L1-03 (assembly), MAST-L1-06 (turn), MAST-L1-22 (structure), MAST-L1-23 (part retention).

---

## Design-driving analysis

### Wing area is pinned from both directions

Wing area cannot be chosen freely. Reducing it lowers cruise drag and helps the 25 m/s
requirement, but it raises stall speed, and MAST-L1-06 requires a 45.7 m radius sustained turn
at 25 m/s — a 1.72 g manoeuvre whose stall speed is 1.31x the 1 g value.

At 6.80 kg with CL_max = 1.2, a 0.45 m² wing stalls at 14.2 m/s in 1 g and 18.6 m/s at 1.72 g,
leaving a 1.34x margin to 25 m/s. Shrinking to 0.38 m² raises the 1 g stall to 15.5 m/s and the
1.72 g stall to 20.3 m/s, cutting the margin to 1.23x — below the 1.3x floor in MAST-L1-06.
**0.45 m² is therefore close to the minimum permissible area, not a comfortable midpoint**, and
any mass growth above 15 lb pushes it up further since stall speed scales with the square root
of weight.

### Stowed volume versus part retention

MAST-L1-02 requires the assembled aircraft to collapse into 559 x 356 x 229 mm, while
MAST-L1-03 requires toolless reassembly in 180 s and MAST-L1-23 requires that nothing depart in
flight. These pull against each other directly. A 2.0 m span at a 559 mm limit needs the wing
in at least 4 segments, so there are at least 3 spanwise joints plus boom and tail joints, each
carrying flight loads and each a candidate for the 10% part-departure penalty.

The resolution adopted below is that every structural joint must be **positively locked with a
visually verifiable indication**, so that a 180 s assembly can be confirmed correct by eye
rather than by torque check. This is the reason MAST-L2-AIR-07 specifies visual verification
rather than just locking.

### Two orthogonal load cases

A tailsitter's structure sees two largely independent primary load cases. In cruise the wing
carries 1.72 g of bending and torsion in the conventional way. In hover the airframe stands
vertically and the wing becomes a large cantilevered sail: rotor thrust loads act along the
fuselage axis while gusts apply pitching and rolling moments to the full wing area with only
differential rotor thrust to resist them. A conventional fixed-wing sizing exercise addresses
only the first case and will under-size the boom and wing root attachments for the second.

---

## L2 — Subsystem requirements

| ID | Requirement | Parents | Rationale |
|---|---|---|---|
| MAST-L2-AIR-01 | Airframe structural mass, excluding propulsion, avionics, batteries, and payloads, shall not exceed 1.60 kg, tracked against measured rather than estimated mass properties from first article onward. | L1-01, L1-27 | Derived allocation. Of the 6.80 kg target, battery takes 1.83 kg (L1 Appendix B) and payloads 1.40 kg (MAST-L2-PLD-03), leaving 3.57 kg for structure, propulsion, and avionics. 1.60 kg is the structural share. Mass growth is the top system risk and the design-lock rule permits only 5% of change afterwards, so drift must be visible early. |
| MAST-L2-AIR-02 | Wing reference area shall be 0.45 m² ±10%, with CL_max not less than 1.2 in the clean cruise configuration. | L1-04, L1-06 | Jointly sized by the cruise-speed and sustained-turn requirements as shown above. The CL_max floor is as binding as the area. |
| MAST-L2-AIR-03 | Wing aspect ratio shall be not less than 6.5. | L1-04, L1-05 | Induced drag at cruise CL scales inversely with aspect ratio; below 6.5 the Appendix B cruise power figure of 311 W no longer holds and the energy budget opens up. |
| MAST-L2-AIR-04 | The airframe shall withstand a limit load of 1.72 g with an ultimate factor of safety of 1.5, and shall separately withstand hover-attitude rotor thrust and gust-induced moment loads at the MAST-L1-11 wind envelope, with rotor booms sized for the hover case rather than the cruise case. | L1-22, L1-06, L1-11 | Both load cases must be sized explicitly; see analysis above. The hover load case governs boom sizing for a tailsitter and is routinely missed. |
| MAST-L2-AIR-05 | The airframe shall withstand vertical landing impact at 2.0 m/s descent rate at maximum takeoff weight without permanent deformation. | L1-09, L0-END-01 | A landing is only credited if the UAS touches down without damage to itself or the environment. |
| MAST-L2-AIR-06 | The airframe shall disassemble into no more than 4 spanwise wing segments, each not exceeding 550 mm, collectively stowing within a single 559 x 356 x 229 mm envelope along with all assembly ground support equipment. | L1-02, L0-VEH-10 | The envelope is a single container, not per-segment, so packing efficiency matters as much as segment size. 550 mm leaves 9 mm of packing clearance. |
| MAST-L2-AIR-07 | Every structural joint shall be assembled and positively locked by hand without tools, requiring no more than 50 N of force, shall provide a visual or audible indication of correct engagement, and shall not be capable of appearing assembled while unlocked. | L1-03, L1-23, L0-VEH-12 | Poka-yoke requirement. With 180 s to assemble and a 10% penalty per part lost, a joint that can look right while being wrong is the dominant airworthiness risk of a repeatedly assembled airframe. 50 N bounds the force an operator can reliably apply under time pressure. |
| MAST-L2-AIR-08 | The number of structural joints requiring assembly at the field shall not exceed 8, and each shall be rated for at least 500 assembly cycles without exceeding its wear allowance. | L1-03 | Derived from the 180 s assembly budget: at roughly 15 s per joint including verification, 8 joints consume 120 s, leaving 60 s for payload loading, control surface checks, and power-up. A season of testing plus competition plausibly reaches several hundred cycles, and wear in a detent joint manifests as looseness, then as flutter. |
| MAST-L2-AIR-09 | All threaded fasteners shall be secured with safety wire, thread-locking fluid, or nylon lock nuts. Field-assembled joints shall use captive, non-threaded positive locks. | L0-VEH-06, L1-23 | Explicitly inspected. Threaded fasteners are incompatible with toolless field assembly, so field joints must be a different mechanism class entirely. |
| MAST-L2-AIR-10 | The structure shall provide externally accessible bays for every battery pack, permitting removal and installation without disassembly of any structural joint, retaining each pack against 2.58 g in all axes, and thermally isolated from compute and power electronics heat sources. | L0-VEH-05, L1-21, L1-22 | Explicit rule that batteries may not be embedded in the airframe. Conflicts with stowed volume efficiency; resolved in favour of the rule. Ultimate load in any axis because the aircraft operates in two orthogonal attitudes. |
| MAST-L2-AIR-11 | The structure shall provide a stable ground-resting configuration in the hover attitude that tolerates the MAST-L1-11 wind envelope without tipping, keeps all propeller arcs clear of the ground and personnel, and provides hard points for the propeller restraint or motor power disconnect reachable from outside every propeller arc. | L1-09, L1-24 | Tailsitter-specific. The aircraft rests nose-up on its tail, which is inherently tip-prone in wind and places rotors near the ground. The interlock geometry problem is specific to a nose-up resting airframe with four rotors. |
| MAST-L2-AIR-12 | Ground-resting structure shall be integral to the aircraft or, if separate, shall stow within the MAST-L1-02 envelope and be deployable within the 180 s assembly budget. | L1-02, L1-03 | A separate cradle is permissible but is not free: it consumes transport volume and assembly time, both of which are scored. |
| MAST-L2-AIR-13 | Control surfaces shall provide sufficient authority for 54.3 degrees of bank at 25 m/s and for pitch trim across the full centre-of-gravity range including both payloads loaded and both released, with hinges sealed or shrouded against runway and field debris. | L1-06, L2-PLD-16 | Asymmetric payload release is the normal case, not a contingency. A jammed surface during an autonomous lap forces a manual takeover and a lap restart. |
| MAST-L2-AIR-14 | The airframe shall accommodate propulsion, avionics, imaging payload, and both delivery payloads with the centre of gravity inside limits for both hover and cruise attitudes, in all four payload load states. | L1-10, L2-PLD-16 | Four states: both loaded, bottle released, beacon released, both released. |
| MAST-L2-AIR-15 | An external surface shall carry the FAA registration number in permanent, legible marking. | L0-REG-01, L1-26 | Inspected at safety inspection and at the flight line. |
| MAST-L2-AIR-16 | Structure and skin shall retain full properties after soak at 43.3 °C in direct sunlight. | L1-12 | Relevant to adhesive-bonded composite and to any thermoplastic printed components, whose glass transition may be near this temperature. |
| MAST-L2-AIR-17 | The imaging payload aperture shall be unobstructed by airframe structure, landing gear, propeller arc, or payload bay doors in the cruise attitude. | L2-PER-02, L2-PER-07 | Interface requirement; the camera has no gimbal, so the structure must guarantee the view. |
| MAST-L2-AIR-18 | Electrical connections crossing any field-assembled joint shall use blind-mate connectors that engage as part of the mechanical joint motion, keyed against mis-mating, and all external surfaces shall be free of sharp edges and protrusions. | L1-03, L2-AIR-07 | Separate manual connector mating inside 180 s is a time and error risk; keying prevents a reversed motor or servo connection during a rushed assembly. Assembly is hands-only and time-pressured. |
