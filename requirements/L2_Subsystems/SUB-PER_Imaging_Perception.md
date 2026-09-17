# SUB-PER — Imaging and Perception Subsystem (L2)

**Scope.** Camera, lens, mounting and stabilisation, image capture triggering, onboard storage,
orthomosaic generation, target detection and classification, and target geolocation.

**Parent L1 requirements.** MAST-L1-19 (detection and geolocation), MAST-L1-20 (risk map),
MAST-L1-12 (thermal), MAST-L1-14 (two-operator autonomy).

---

## Design-driving analysis

### Camera orientation resolves favourably for a tailsitter

A tailsitter rotates 90 degrees between hover and cruise, which initially appears to force a
gimbal with more than 90 degrees of pitch travel. It does not, because **all imaging happens in
cruise**. Both the Risk Mapping survey and the target search are flown as cruise passes over the
Search Boundary; nothing useful is imaged while hovering. A camera fixed to the fuselage looking
"down" relative to the cruise attitude is therefore nadir-pointing exactly when it matters, and
points uselessly at the horizon during hover, which costs nothing.

This eliminates the gimbal, and with it roughly 150 to 250 g of mass, a rotating interface, and
a failure mode — a material win against the MAST-L1-01 mass target. The requirement below
therefore specifies a fixed nadir mount with passive vibration isolation rather than a gimbal.

### Resolution and coverage

Search Boundary 1 measures approximately 147 m (north-south) by 262 m (east-west), about 9.5
acres, consistent with the handbook's "approximately 10 acres."

Minimum imaging altitude is 45.7 m AGL, because the aircraft may not descend below the 150 ft
floor. With a 1/2.3 in class sensor at 4056 x 3040 px and 1.55 µm pixel pitch behind a 6 mm
lens, ground sample distance at 45.7 m is:

`GSD = 1.55e-6 * 45.72 / 6e-3 = 0.0118 m/px = 1.18 cm/px`

giving a ground footprint of 47.9 m across-track by 35.9 m along-track. This comfortably meets
the 2.0 cm/px requirement of MAST-L1-20 with 40% margin, which is deliberate: margin here
absorbs a higher survey altitude if terrain forces it, since terrain inside the boundary varies
by 115 ft.

Survey geometry, flying the long axis with 30% sidelap and 70% along-track overlap:

| Parameter | Value |
|---|---|
| Across-track stride | 47.9 x 0.70 = 33.5 m |
| Number of passes | 147 / 33.5 = 4.4, so 5 passes |
| Pass length | 262 m |
| Turn allowance (5 turns at 45.7 m radius) | ~718 m |
| Total survey path | ~2030 m |
| Survey time at 18 m/s | ~113 s, inside the 180 s L1 allocation |
| Along-track trigger interval | 35.9 x 0.30 = 10.8 m, i.e. 0.60 s at 18 m/s |
| Required trigger rate | 1.67 Hz |

Survey speed is capped at 18 m/s rather than the 25 m/s cruise requirement because the trigger
rate and motion blur both scale with speed, and Appendix A of the L1 document already allocates
180 s for mapping — going faster saves at most 45 s of a 2700 s clock while making the capture
pipeline and blur budget materially harder.

Motion blur at 18 m/s with a 1/1000 s shutter is 18 mm of smear, which is 1.5 px at 1.18 cm/px.
Acceptable. At 25 m/s the same shutter yields 2.1 px, which begins to degrade stitching quality
against a scoring rubric that explicitly evaluates stitching.

### Detection feasibility

A mannequin is roughly 1.7 m by 0.4 m. At 1.18 cm/px that is 144 x 34 px — a large, well-resolved
target. Even degraded to the 2.0 cm/px requirement it remains 85 x 20 px. An open pop-up tent at
2 to 3 m spans 100 to 250 px. Both are comfortably detectable; **the difficulty is not
resolution, it is occlusion and pose.** The handbook states the mannequin may be laying down,
sitting up, or face-down, and may be surrounded or covered by bushes, trees, or vehicles, among
unrelated debris. Requirements below therefore emphasise training data diversity and multi-frame
association over raw sensor performance.

### Geolocation budget

Target geolocation error must be 5.0 m or better to combine with the 8.5 m drop CEP. At 45.7 m
altitude the achievable error is:

| Error source | Magnitude | Contribution |
|---|---|---|
| Attitude knowledge (1 degree) | 45.7 * tan(1°) | 0.80 m |
| Aircraft GNSS position | | 1.50 m |
| Image-to-attitude time sync (20 ms at 18 m/s) | | 0.36 m |
| Terrain elevation uncertainty within boundary | | 1.50 m |
| Detection centroid error (10 px) | | 0.12 m |
| **Root-sum-square** | | **2.2 m** |

2.2 m against a 5.0 m requirement gives healthy margin. Note that **time synchronisation between
image capture and attitude/position solution is the dominant controllable term** once attitude
is good — a 200 ms sync error alone would contribute 3.6 m and consume most of the budget. This
is why MAST-L2-PER-08 requires hardware-level timestamping rather than a software timestamp.

---

## L2 — Subsystem requirements

| ID | Requirement | Parents | Rationale |
|---|---|---|---|
| MAST-L2-PER-01 | The imaging payload shall achieve a ground sample distance of 2.0 cm/px or finer at 45.7 m AGL, with lens distortion characterised and corrected in the processing pipeline. | L1-20, L1-19 | Serves both the map quality rubric and target detection from the minimum legal altitude. Uncorrected radial distortion is a direct projection-accuracy error — a scored criterion — and a common cause of visible mosaic defects at frame edges. |
| MAST-L2-PER-02 | The camera shall be rigidly mounted in a fixed nadir orientation relative to the cruise attitude, with passive vibration isolation attenuating airframe vibration above 50 Hz, and no gimbal. | L1-20, L1-01 | All imaging occurs in cruise, so the tailsitter's 90-degree attitude change never needs to be compensated. Deletes gimbal mass and a failure mode. Propeller-order vibration from four rotors lands well above 50 Hz and appears as blur that no shutter speed fixes. |
| MAST-L2-PER-03 | The camera shall capture at a sustained rate of at least 2.0 Hz at full resolution for the duration of the survey without frame drops or buffer overruns. | L1-20 | 1.67 Hz is required by the survey geometry; 2.0 Hz provides margin for a faster pass or tighter overlap. Sustained is the operative word — burst capability is insufficient for a 113 s survey. |
| MAST-L2-PER-04 | Exposure shall be controlled to hold shutter time at or below 1/1000 s throughout the survey, prioritising shutter speed over ISO. | L1-20 | Limits motion blur to 1.5 px. Stitching quality is explicitly scored, and blur degrades feature matching before it degrades visual appearance. |
| MAST-L2-PER-05 | Exposure shall be held consistent across the survey such that adjacent frames differ by no more than 1/3 stop. | L1-20 | "Varying exposures" is named in the handbook as a defect characterising a medium-quality map. Auto-exposure per frame is therefore a scoring liability, not a convenience. |
| MAST-L2-PER-06 | The survey shall be flown at a ground speed not exceeding 18 m/s. | L1-20, L2-PER-03 | Caps trigger rate and blur. Costs at most 45 s against a 2700 s clock. |
| MAST-L2-PER-07 | Survey coverage shall provide at least 70% along-track overlap and 30% across-track sidelap over the entire Search Boundary, including a 15 m buffer beyond each boundary edge, with the camera aperture unobstructed by structure throughout the cruise attitude range. | L1-20 | Coverage is a scored criterion and edge coverage is where mosaics typically fail. The buffer also absorbs navigation error. |
| MAST-L2-PER-08 | Every captured frame shall be tagged with position, attitude, and capture time synchronised to the flight control solution within 20 ms, using hardware timestamping against the autopilot time base rather than an application-layer software timestamp. | L1-19, L1-20 | Drives both geolocation accuracy and orthomosaic projection accuracy, the latter explicitly scored. Software timestamps on a loaded Linux system routinely scatter by 100 ms or more, which alone would consume most of the 5.0 m geolocation budget. |
| MAST-L2-PER-09 | The subsystem shall generate a georeferenced orthomosaic of the Search Boundary onboard or on onsite equipment, with no human intervention and no internet or cloud dependency. | L1-20, L1-14, L1-28 | Two operators may perform no other task in flight, so nobody is available to run a photogrammetry tool. Cloud processing is barred for safety-critical paths and unavailable in practice at a rural range. |
| MAST-L2-PER-10 | Orthomosaic generation shall be complete, or complete within 60 s of touchdown, such that the file is written and submitted inside Mission Time. | L1-20, L0-MSN-02, L0-PEN-01 | The Mission Clock runs until deliverables are submitted and excess time costs 0.5% of mission points per second. Sixty seconds of post-landing stitching costs 30% of the mission score if the clock has already expired. |
| MAST-L2-PER-11 | The output map shall be written as .png or .jpeg with the team name embedded in the filename, to a judge-supplied USB mass storage device, verified by checksum read-back, within 30 s. | L0-MAP-01, L0-MAP-02 | Format and naming are explicit rules; maps received outside Mission Time score zero. A silently failed write costs 150 points and the operator has no time to investigate, so read-back verification is cheap insurance on the highest-value single deliverable. |
| MAST-L2-PER-12 | The subsystem shall detect and classify one mannequin and one open pop-up tent within the Search Boundary, distinguishing the two classes with at least 95% confidence on the accepted detection. | L1-19, L0-SDD-10 | Correct pairing is worth 30 points per delivery, 60 total. A confident wrong classification is worse than an uncertain one because it directs both drops incorrectly. |
| MAST-L2-PER-13 | Detection shall be robust to the mannequin appearing in any orientation including prone, supine, face-down, and seated, and to partial occlusion of up to 50% of its area by vegetation, vehicles, or debris. The detection model shall be trained on data spanning these poses and occlusions at 1.0 to 2.5 cm/px. | L0-SDD-10 | Stated explicitly in the handbook and the single largest detection risk. Training-domain match to the deployment condition is the controlling factor in detection reliability, more than model architecture. |
| MAST-L2-PER-14 | The subsystem shall reject false positives from unrelated debris in the Search Boundary, and shall associate detections across at least 3 frames before declaring a target. | L0-SDD-10, L1-19 | Targets are deliberately placed "amongst other debris." Multi-frame association is the cheapest available false-positive filter and also improves centroid accuracy. |
| MAST-L2-PER-15 | Each declared target shall be geolocated to within 5.0 m of its true position in WGS-84, and its position, class, and confidence shall be published to the flight software and GCS at no less than 1 Hz once declared. | L1-19, L1-17 | Combines with the 8.5 m drop CEP to close the 15.2 m scoring radius, and defines the interface to the SUB-PLD release computation. |
| MAST-L2-PER-16 | Detection and geolocation shall execute onboard or on onsite equipment within 30 s of the completion of the search pass, with the model and all weights resident locally and no runtime network dependency. | L1-14, L1-28, L0-MSN-01 | The delivery phase follows immediately in the mission timeline; the aircraft cannot loiter waiting for a detection result without consuming schedule margin. The release decision depends on detection, and release inhibit is named as safety-critical functionality that must run onsite. |
| MAST-L2-PER-17 | Imagery shall be retained in non-volatile storage onboard so that a map can be produced after landing even if the downlink fails entirely. | L1-18, L1-20 | The map is worth 150 points and must not depend on a contested RF link. Decouples the highest-value deliverable from the least controllable subsystem. |
| MAST-L2-PER-18 | Compute hardware shall sustain the full capture, detection, and stitching workload at 43.3 °C ambient in direct sunlight with no thermal throttling, with junction temperature monitored and logged. | L1-12 | A silent compute throttle during the detection phase would cost up to 200 points with no indication to the operators. Logging makes a throttle event detectable in post-flight analysis rather than inferred from a lost score. |
| MAST-L2-PER-19 | No ground-based imaging sensor shall be used to substitute for the airborne imaging payload. | L0-MAP-05 | Explicit rule. |
| MAST-L2-PER-20 | Camera and compute power shall be drawn from the avionics bus, not the propulsion bus, and shall be protected against propulsion-induced voltage transients. | L1-12 | A compute brownout during hover, when propulsion draws 1166 W, would lose the map and the detections simultaneously. |
