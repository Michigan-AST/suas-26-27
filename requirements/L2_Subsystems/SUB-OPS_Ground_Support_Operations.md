# SUB-OPS — Ground Support and Operations Subsystem (L2)

**Scope.** Transport containers, assembly procedures and tooling, ground handling and the
tailsitter resting cradle, checklists, crew roles and training, safety equipment,
documentation carried on site, and the deliverable submission process.

**Parent L1 requirements.** MAST-L1-02 (stowed volume), MAST-L1-03 (assembly),
MAST-L1-14 (two operators), MAST-L1-24 (propeller interlock), MAST-L1-27 (configuration
control).

---

## Design-driving analysis

### Ground handling is a real subsystem for a tailsitter

A tailsitter rests nose-up on its tail. That has three consequences that a conventional design
never faces. The aircraft is tall and narrow, so it is tip-prone in exactly the wind conditions
the mission requires. Its four rotors sit near head height or near the ground depending on the
resting scheme, so the propeller-arc clearance rule (L0-VEH-08, a potential disqualification)
becomes a ground-geometry problem rather than a procedural one. And it usually needs a cradle or
stand, which is ground support equipment that must itself fit inside the MAST-L1-02 transport
envelope and be deployed inside the 180 s assembly budget.

### Two people, 180 seconds, no tools, and the clock is already running

The compound operational requirement is the hardest thing in this subsystem. Per MAST-L1-03 the
aircraft must go from stowed to flight-ready in 180 s, toolless, with 2 people — and per
L0-MSN-01 nothing may be powered on before the Mission Clock starts, so GNSS acquisition,
compass initialisation, autopilot boot, GCS boot, link establishment, and payload loading are
all on the clock too. The L1 Appendix A budget allocates 420 s total for all of it.

There is no slack for a procedure that is learned on the day. Rehearsal to a repeatable time is
itself a requirement, stated below as MAST-L2-OPS-05.

### Payload objects arrive at the start of the clock

The beacon and water bottle are handed over at the start of Mission Time, along with the USB
drive (L0-MSN-01). The bottle's exact dimensions are unknown until then, within the published
2 to 2.5 in diameter and 5 to 6 in height range. Loading is therefore both time-critical and
must tolerate an object the team has not previously handled.

---

## L2 — Subsystem requirements

| ID | Requirement | Parents | Rationale |
|---|---|---|---|
| MAST-L2-OPS-01 | All aircraft components and all ground support equipment required for assembly shall stow within a single 559 x 356 x 229 mm container, using custom foam or fixtures that locate each component in a defined position and present components in the order the assembly procedure consumes them. | L1-02, L0-VEH-10 | The sizing tier is scored against a single luggage envelope, and a cradle or assembly fixture that does not fit forfeits the points it was meant to enable. Defined positions make a 180 s assembly repeatable, make a missing component immediately visible, and packing order is one of the cheapest available reductions in assembly time variance. |
| MAST-L2-OPS-02 | The assembly procedure shall require no tools of any kind, including no hex keys, no screwdrivers, and no torque tools. | L0-VEH-12, L1-03 | Worth 25 points, and a single tool in the procedure forfeits all of it. |
| MAST-L2-OPS-03 | The assembly procedure shall be executable by 2 people in 180 s or less, ending with motors and control surfaces demonstrably operating. | L0-VEH-11, L1-03, L1-14 | The rules permit 4 personnel, but using non-operators conflicts with maximum Efficient Operators scoring. See open question 1 in `L0_Reconciliation_Notes.md`. |
| MAST-L2-OPS-04 | The full setup sequence — unpack, assemble, load both payloads, power up, acquire GNSS, initialise compass, establish link, complete preflight checklist, and arm — shall be executable by 2 operators in 420 s or less from the start of the Mission Clock. | L0-MSN-01, L1-03, L2-GCS-12 | This is the allocation in the L1 Appendix A mission clock budget; exceeding it directly reduces available lap count. |
| MAST-L2-OPS-05 | The setup and teardown procedures shall be rehearsed to a repeatable time with a demonstrated standard deviation not exceeding 15 s before the competition. | L2-OPS-04, L0-PEN-01 | Variance, not mean time, is what causes an overrun on the day. Overrun costs 0.5% of mission points per second. |
| MAST-L2-OPS-06 | A ground cradle or resting structure shall support the aircraft in its hover attitude with a tipping margin of at least 1.5 against a 9.8 m/s gust on the full exposed area, keep all propeller arcs clear of the ground and personnel, permit vertical departure without interference or component removal, and allow payload loading with the aircraft in place. | L2-AIR-11, L1-24, L0-VEH-08, L1-09 | Tailsitter-specific. Propeller-arc violations may cause disqualification. The same gust force that drives the propulsion control-authority requirement also tries to tip the parked aircraft. A cradle requiring removal before launch adds a step inside the 420 s setup budget. |
| MAST-L2-OPS-07 | The propulsion power disconnect or propeller restraint shall be engaged whenever any person is within any propeller arc, shall be the default state during all ground handling, and shall be reachable and verifiable from outside every propeller arc with the aircraft in its cradle. | L0-VEH-08, L1-24, L2-PWR-11 | The handbook states software disarm is insufficient and violation may cause disqualification. Making it the default rather than a step removes it from the list of things a rushed operator can skip. |
| MAST-L2-OPS-08 | Written checklists shall exist for preflight, setup, payload loading, post-flight, battery handling, and emergency response, printed on weather-resistant material, mounted for hands-free reading during setup, and carried on site in hard copy. | L0-SAF-09, L2-GCS-14 | Checklists are explicitly named as required safety risk mitigation. Both operators have their hands occupied during a 180 s toolless assembly. |
| MAST-L2-OPS-09 | The team shall carry PPE including gloves, eye protection, and hearing protection, plus a first aid kit and a fire extinguisher, on site at all times. | L0-SAF-09 | Explicit requirement, inspected. |
| MAST-L2-OPS-10 | The team shall carry LiPo-safe bags adequate for every battery used, plus a bucket and sand for the handbook's prescribed failed-battery procedure, and shall maintain a battery log recording daily inspection for swelling, heat, leaking, venting, or deformation of every pack. | L0-SAF-08 | The handbook prescribes this exact containment method in the absence of manufacturer guidance, and daily inspection is mandated with affected packs removed from use and reported. |
| MAST-L2-OPS-11 | The team shall carry hard copies of FAA registration, Remote ID documentation, the Safety Pilot's TRUST certificate, and battery specifications, MSDS, and disposal procedures for every battery. | L0-REG-01, L0-REG-02, L0-REG-03, L0-SAF-08 | Each is presented at safety inspection and at the flight line; a missing document prevents flight. |
| MAST-L2-OPS-12 | The team shall designate exactly 2 operators, a Safety Pilot and a GCS Operator, declare them to judges before the mission, and ensure no other member communicates with or assists them while the aircraft is airborne. | L0-OPR-01, L0-OPR-02, L0-OPR-03, L1-14 | Worth 200 points; a violation terminates the mission. Assignments cannot change once the mission starts. |
| MAST-L2-OPS-13 | The Safety Pilot shall hold a current FAA TRUST certificate and shall demonstrate manual flight proficiency in both hover and cruise modes, including manual recovery from a failed transition. | L0-REG-03, L0-DOC-04, L2-GNC-13 | A tailsitter is demanding to fly manually, and the Safety Pilot must be able to take over at any moment in either flight regime. Also required for the Proof of Pilot Competence Video. |
| MAST-L2-OPS-14 | The team shall be able to secure all equipment against sudden precipitation and wind within 5 minutes, against a documented go/no-go criteria sheet defining the wind, temperature, and system-health conditions under which the team declines to fly or curtails the mission. | L0-SAF-10, L1-11, L2-ASW-17 | Explicit requirement to be prepared for sudden weather. The wind envelope is self-imposed because the rules impose none, so the decision to fly must be made against a pre-agreed standard rather than in the moment. |
| MAST-L2-OPS-15 | All equipment shall be removable from the flight line tent area within 10 minutes, using the full team including non-operators. | L0-MSN-03, L0-OPR-03 | Teardown is separately timed and is the one phase where non-operators may help. |
| MAST-L2-OPS-16 | A configuration record shall document the exact aircraft configuration submitted with the Proof of Flight Readiness Video, all subsequent changes shall be assessed against the 5% size and weight limit before implementation, and a single named person shall be accountable for mass properties tracking against the MAST-L1-01 budget. | L0-ELG-03, L1-27, L1-01 | 5% of a 15 lb aircraft is 0.75 lb, so changes must be assessed before, not after. Mass growth is the top system-level risk and needs a named owner rather than collective responsibility. |
| MAST-L2-OPS-17 | Spares shall be carried for every component whose failure would prevent flight and which can be replaced without violating the design-lock rules. | L0-ELG-03, L0-DOC-03 | Replacement of damaged components is explicitly permitted after lock, so spares preserve the flight opportunity; a modification would not. |
