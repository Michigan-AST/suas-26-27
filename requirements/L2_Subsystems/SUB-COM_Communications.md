# SUB-COM — Communications Subsystem (L2)

**Scope.** Telemetry and command datalink, manual control link, antennas, ground radio
equipment, link security, and any video downlink.

**Parent L1 requirements.** MAST-L1-18 (availability), MAST-L1-16 (failsafes),
MAST-L1-28 (onsite independence).

---

## Design-driving analysis

### Path loss is easy; interference is the whole problem

The Flight Boundary spans roughly 1.1 x 1.1 km, so the maximum slant range from a ground station
at the runway is about 1.6 km. At 915 MHz that is approximately 96 dB of free-space path loss —
trivially closed by a 100 mW radio with modest antennas and 20 dB or more of margin.

The actual risk is stated plainly in the handbook: **no RF spectrum management is provided.** Any
team may transmit in any FCC-permitted band at any time, including in the pits. Up to two
aircraft fly simultaneously. Teams are warned to expect competitors using identical equipment
and are explicitly told they must prevent invalid connections to another team's autopilot.

This converts an easy link-budget problem into a coexistence problem, and the consequence is
severe and asymmetric: **a 15-second link outage automatically triggers return-to-land**
(L0-SAF-03) and ends the mission attempt. A team can lose the mission to another team's radio
without either team doing anything wrong. The 5.0 s outage limit in MAST-L1-18 exists to give
3x margin against that trigger.

### Antenna height is capped

Ground equipment may not exceed 15 ft (L0-GCS-04), which caps the ground antenna height. At
1.6 km with a 15 ft antenna and an aircraft at 150 to 400 ft AGL, the geometry is well clear of
the first Fresnel zone obstruction, so the cap is not limiting for line-of-sight. It does
prevent using height to escape ground-level interference from the pits, which reinforces the
case for directional antennas and frequency agility.

---

## L2 — Subsystem requirements

| ID | Requirement | Parents | Rationale |
|---|---|---|---|
| MAST-L2-COM-01 | The command and telemetry link shall maintain bidirectional connectivity at all points within the Flight Boundary and across the 150 to 400 ft AGL band, with no single outage exceeding 5.0 s. | L1-18, L0-SAF-03 | 3x margin against the 15 s automatic RTL trigger. |
| MAST-L2-COM-02 | The link shall close with at least 15 dB of margin at the maximum slant range of 1.6 km, using a telemetry radio of at least 100 mW and a ground directional antenna of at least 6 dBi. | L1-18 | Margin covers antenna pattern nulls during 54 degree bank turns, airframe blockage in the hover attitude, and multipath over the field. Directional gain also rejects off-axis interference from the pits, which the 15 ft height cap cannot. |
| MAST-L2-COM-03 | The link shall employ frequency hopping or dynamic channel selection, with selectable channel maps allowing relocation away from an interferer discovered on site. | L0-REG-05, L1-18 | The handbook explicitly encourages this and provides no spectrum management. |
| MAST-L2-COM-04 | The link shall use a unique, non-default network identifier and link-layer encryption or authentication such that the aircraft cannot associate with another team's ground station, and the ground station cannot associate with another team's aircraft. | L0-REG-05, L1-18 | The handbook explicitly warns teams must ensure they do not allow invalid connections. Two aircraft fly at once, potentially with identical autopilots — and vendor-default identifiers are precisely how two such teams cross-connect. |
| MAST-L2-COM-05 | The manual control link shall be independent of the telemetry link in hardware and shall operate in a different frequency band. | L2-GNC-10, L1-16 | RTL and flight termination must be independently commandable by the Safety Pilot and the GCS Operator; independence fails if a single interference event takes both. |
| MAST-L2-COM-06 | No communications equipment shall transmit in the 462 MHz band. | L0-REG-04 | Judges use 462 MHz for handheld radios; interfering with judge communications is an unsafe-operations exposure. |
| MAST-L2-COM-07 | All RF equipment shall operate within FCC-permitted bands at FCC-permitted power levels, and an RF band plan listing every transmitter on the aircraft and in the ground segment with frequency, bandwidth, and power shall be maintained and available at safety inspection. | L0-REG-04, L0-SAF-07 | Stated rule. The band plan makes self-interference between onboard transmitters visible before it is discovered in flight. |
| MAST-L2-COM-08 | Ground station antennas and all supporting structure shall not exceed 15 ft (4.57 m) in height. | L0-GCS-04, L1-18 | Explicit rule; no masts, balloons, or objects above this height. |
| MAST-L2-COM-09 | The link shall carry aircraft position, ground speed, AGL altitude, battery state, wind estimate, flight mode, and declared target information at rates sufficient for the GCS display requirements. | L0-GCS-02, L2-GCS-02 | Defines the payload the display depends on. |
| MAST-L2-COM-10 | Link quality, including received signal strength and packet loss rate, shall be displayed to the GCS Operator continuously and logged onboard at no less than 1 Hz. | L1-18, L1-14 | The GCS Operator's only job in flight is supervision; a degrading link is the earliest warning of an impending automatic RTL. Post-flight diagnosis of a spurious RTL is impossible without the log. |
| MAST-L2-COM-11 | No safety-critical function shall depend on the telemetry link, the public internet, or any cloud provider. | L0-SAF-06, L1-28, L2-GNC-14 | Failsafes execute onboard; the link is for supervision and for the second command path only. |
| MAST-L2-COM-12 | Where a wired connection can replace an RF link on the ground, the wired connection shall be used. | L0-REG-05 | The handbook explicitly encourages hardwired connections to reduce spectrum congestion, and it removes the ground segment from the interference problem entirely. |
| MAST-L2-COM-13 | Communications equipment shall operate at ambient temperatures up to 43.3 °C without thermal shutdown or output power reduction. | L1-12 | Power amplifiers derate with temperature, which silently erodes the margin in MAST-L2-COM-02. |
| MAST-L2-COM-14 | Airborne antennas shall be mounted at least 150 mm from carbon fibre structure and from the GNSS antenna, and shall exhibit no pattern null deeper than 10 dB across the full 90 degree attitude change between hover and cruise. | L2-COM-02, L2-GNC-01 | Carbon fibre is conductive and detunes and shadows antennas; co-located transmitters desensitise GNSS. Tailsitter-specific: the airframe and therefore the antenna rotates bodily, so a pattern optimised for cruise may null toward the ground station in hover. |
| MAST-L2-COM-15 | The system shall be verified to operate with a second identical system transmitting simultaneously within 50 m, and any video downlink shall occupy a band separate from both command links and be independently inhibitable. | L2-COM-03, L2-COM-04, L2-COM-05 | Directly reproduces the competition condition of two teams flying similar equipment; passing it may require architecture change rather than tuning. Video is the highest-bandwidth and least essential link and must never be able to degrade the two that matter. |
