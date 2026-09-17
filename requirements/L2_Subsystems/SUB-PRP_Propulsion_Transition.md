# SUB-PRP — Propulsion and Transition Subsystem (L2)

**Scope.** Lift and cruise motors, propellers, ESCs, motor mounts, thrust vectoring if any, and
the transition control schedule between hover and cruise.

**Parent L1 requirements.** MAST-L1-04 (cruise speed), MAST-L1-05 (energy),
MAST-L1-09 (VTOL), MAST-L1-10 (transition), MAST-L1-11 (wind), MAST-L1-12 (thermal).

---

## Design-driving analysis

### Hover authority, not hover thrust, is the binding requirement

Hover thrust is straightforward: 66.7 N at 6.80 kg, and a conventional thrust-to-weight target
of 2.0 gives 133 N installed. The hard requirement is **control authority in gusts**, and for a
tailsitter it is far more demanding than for a quadplane.

In hover the wing is broadside to the wind. Taking 0.45 m² of wing plus roughly 0.15 m² of
fuselage and boom area as 0.60 m² of exposed area at a bluff-body drag coefficient near 1.2, a
9.8 m/s gust produces:

`F = 0.5 * 1.225 * 9.8^2 * 0.60 * 1.2 = 42.3 N`

That is 63% of the aircraft's weight, applied as a side force, and because the aerodynamic
centre of that area is offset from the centre of mass it also applies a substantial pitching
moment. The only thing resisting it is differential rotor thrust. A rotor layout with a short
moment arm will simply not hold attitude, regardless of installed thrust.

This is why MAST-L2-PRP-04 specifies a control-moment requirement rather than only a
thrust-to-weight ratio, and why the four-rotor layout must be spread rather than compact.

### Disk loading trades hover efficiency against stowed volume

Appendix B of the L1 document assumes four 12 in rotors, giving 0.292 m² of disk area,
228 N/m² of disk loading, and 1166 W of electrical hover power. Halving the disk area by moving
to 8.5 in rotors raises hover power by a factor of roughly sqrt(2) to about 1650 W. Since hover
is only 130 s of the mission, the energy penalty is modest at about 17 Wh, but the **peak
current** rises by 40%, which drives ESC sizing, battery C-rating, and wiring mass — and the
peak occurs during landing, at the end of the discharge, when pack voltage is lowest. Larger
rotors are preferred, bounded by the 559 mm stowed dimension of MAST-L1-02.

### Cruise and hover propulsion share or split

A tailsitter can either use the same rotors for hover and cruise, or add a dedicated cruise
propulsor. Sharing saves mass, which matters against MAST-L1-01, but forces one propeller to
operate at two wildly different advance ratios, and a propeller optimised for 25 m/s cruise is
a poor hover rotor and vice versa. The requirements below are written to permit either
architecture but require each to meet both operating points, which is the honest way to state
it at L2 without prejudging the trade.

---

## L2 — Subsystem requirements

| ID | Requirement | Parents | Rationale |
|---|---|---|---|
| MAST-L2-PRP-01 | The propulsion system shall provide at least 133 N of static thrust in the hover attitude at maximum takeoff weight, giving a thrust-to-weight ratio of at least 2.0. | L1-09, L1-11 | 2.0 is required rather than conventional for a tailsitter because gust rejection consumes thrust margin that a quadplane spends only on climb. |
| MAST-L2-PRP-02 | The propulsion system shall provide at least 311 W of electrical power at the cruise operating point of 25 m/s at maximum takeoff weight, with the capability to sustain it continuously for 1900 s. | L1-04, L1-05 | From L1 Appendix B. Continuous rating matters: the lap phase alone is 1290 s at this power. |
| MAST-L2-PRP-03 | The propulsion system shall provide at least 1270 W of electrical power for climb, sufficient for a 20 degree climb angle at 25 m/s. | L1-07 | 570 W of climb power above 185 W cruise shaft power, divided by combined propulsive and electrical efficiency. |
| MAST-L2-PRP-04 | The hover rotor layout shall generate a control moment of at least 25 N·m in pitch and roll about the centre of mass using differential thrust alone, with the aircraft in the hover attitude. | L1-11, L1-09 | Derived from the 42.3 N gust side force analysed above acting at a plausible 0.3 m offset from the centre of mass, with 2.0x margin for control margin and actuator lag. **This is the requirement most likely to be missed and hardest to recover from late.** |
| MAST-L2-PRP-05 | Rotor thrust response shall reach 90% of a commanded step change within 100 ms, in both increasing and decreasing directions, using active braking or equivalent rapid thrust reduction. | L1-11, L1-10 | Gust rejection bandwidth. A slow thrust response makes the 3.0 m hover position requirement unachievable no matter how much authority exists. Rapid *reduction* matters as much as increase, because a freewheeling propeller decays slowly. |
| MAST-L2-PRP-06 | Individual rotor diameter shall not exceed 355 mm, and total hover disk area shall be at least 0.25 m². | L1-02, L1-05 | Upper bound from the 356 mm intermediate stowed dimension; lower bound keeps disk loading and therefore peak hover current within the L1 Appendix B assumptions. |
| MAST-L2-PRP-07 | The subsystem shall execute hover-to-cruise and cruise-to-hover transitions within 10 s each, with altitude excursion not exceeding 15 m and without departure from controlled flight. | L1-10 | The altitude excursion budget exists because transition happens near the mission-ending 150 ft AGL floor. |
| MAST-L2-PRP-08 | The transition schedule shall be a deterministic function of airspeed and attitude, shall be repeatable, shall not require operator input, and shall use airspeed from a dedicated sensor rather than GNSS ground speed. | L1-13, L1-10 | Transition occurs with no operator able to intervene, and any manual takeover forces a lap restart. In 6.3 m/s wind, ground speed differs from airspeed by up to 25% of the transition airspeed — enough to trigger a transition at the wrong condition. |
| MAST-L2-PRP-09 | The subsystem shall abort a transition and recover to the previous stable flight mode if airspeed, attitude, or thrust margin falls outside defined bounds, with those bounds held as logged configurable parameters not requiring a firmware rebuild to adjust. | L1-10, L0-PEN-03 | A failed transition at 150 ft AGL is a crash, worth a 50% penalty. Transition tuning is empirical and will iterate through flight test; parameter-based thresholds keep the design-lock configuration stable while tuning continues. |
| MAST-L2-PRP-10 | Motors and ESCs shall operate continuously at the cruise power level, and for at least 180 s at the hover power level, at 43.3 °C ambient without exceeding rated temperature or derating, with temperature telemetry logged at no less than 1 Hz. | L1-12 | 180 s of cumulative hover exceeds the 130 s mission allocation, covering a go-around or a prolonged landing approach. Logging makes thermal margin an observable rather than an assumption. |
| MAST-L2-PRP-11 | Loss of any single lift rotor in hover shall result in a controlled descent or a commanded flight termination, not an uncontrolled departure. | L0-SAF-02, L0-PEN-03 | A four-rotor tailsitter cannot generally hold hover on three rotors; the requirement is graceful behaviour, not full redundancy. |
| MAST-L2-PRP-12 | Propellers shall be retained by a locknut or equivalent positive retention such that no blade or hub component can depart in flight, inspected before each flight. | L0-VEH-07, L1-23 | 10% penalty per item, and a shed blade is also a crash. Folding propellers, attractive for the stowed volume requirement, add a hinge that must be positively retained. |
| MAST-L2-PRP-13 | The subsystem shall accept a physical propeller restraint or a motor power disconnect that prevents rotation independent of software state. | L1-24, L0-VEH-08 | Explicitly inspected; software disarm is stated to be insufficient. |
| MAST-L2-PRP-14 | Motor mounts shall be integral to field-assembled boom segments such that no motor requires separate installation during the 180 s assembly, and each rotor position shall be keyed or labelled so that reversed installation is physically prevented or immediately visible. | L1-03, L2-AIR-08 | Motor installation at the field would consume most of the assembly budget. A reversed rotor on a four-rotor tailsitter is an immediate loss of control at takeoff, and 180 s leaves no time for verification by test. |
| MAST-L2-PRP-15 | Propulsion shall be commanded on outputs isolated from payload release outputs. | L2-PLD-11 | Prevents cross-coupling between a mixer fault and a payload release. |
| MAST-L2-PRP-16 | Motor mount stiffness shall place the first bending mode of the motor and boom assembly above 2.5x the maximum blade passage frequency. | L2-PRP-10, L2-PER-02 | Avoids resonance that would both fatigue the boom and inject vibration into the unstabilised camera. |
