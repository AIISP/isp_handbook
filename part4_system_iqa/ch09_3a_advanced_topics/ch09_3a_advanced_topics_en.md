# Part 4, Chapter 09: Advanced 3A Topics — Multi-Camera Sync, PDAF Degradation, and Loop Coupling

> **Positioning:** This chapter focuses on three advanced 3A engineering topics: cross-stream synchronization for multi-camera systems, PDAF accuracy degradation compensation in low-light environments, and AE/AF/AWB three-loop coupling stability design.
> **Prerequisites:** Part 4, Chapter 01 (3A Control System Overview), Part 4, Chapter 02 (Auto Exposure Fundamentals), Part 4, Chapter 03 (Auto Focus Fundamentals)
> **Target readers:** 3A systems engineers, multi-camera algorithm engineers

> **Note:** Core AE/AF/AWB algorithms (metering modes, PI controller, PDAF principles, gray-world AWB, etc.) are fully covered in the following chapters:
> - **Part 4, Chapter 01** — 3A system architecture, traditional and AI hybrid algorithms, SoC platform implementations (Qualcomm/MediaTek/HiSilicon)
> - **Part 4, Chapter 02** — Complete AE stack (exposure equation, multi-zone metering, PI controller, HDR AE, anti-banding)
> - **Part 4, Chapter 03** — Complete AF stack (CDAF, PDAF, VCM drive, hybrid AF)
> - **Part 2, Chapter 05** — Auto White Balance algorithms (gray world, white-patch detection, neural network AWB)

---

## §1 Multi-Camera 3A Synchronization

### 1.1 Problem Background

Modern flagship smartphones carry 2–4 cameras (ultra-wide, wide, 2× telephoto, 5× telephoto). Because each stream runs its own 3A loop independently, switching between cameras causes:

- **Luminance jump:** Different exposure parameters on each ISP produce a sudden brightness shift at the switch instant.
- **Color temperature jump:** Each AWB loop converges to a different CCT; switching causes a color flicker.
- **Focus jump:** The new stream must re-search for focus, breaking the user experience.

### 1.2 Synchronization Strategies

**Master-Slave Mode:**

The primary camera (typically wide-angle) acts as master; telephoto/ultra-wide streams follow:

```
Master AE target → convert to equivalent EV → Slave target EV = Master EV + ΔEV_correction
```

$\Delta EV_{correction}$ compensates for the aperture difference between the two lenses:

$$\Delta EV = 2 \log_2 \frac{F_{tele}}{F_{wide}}$$

**Frame-Level Hardware Sync:**

Both ISP pipelines are triggered by a shared hardware SOF (Start-Of-Frame) signal so that 3A statistics collection and parameter updates happen at the same frame boundary, ensuring parameter coherence.

**Predictive Interpolation:**

Before switching, the master stream transforms its current 3A state into the predicted target parameters for the slave stream. These predicted values are applied at the switch instant, eliminating the search-and-converge delay:

$$\theta_{slave}^{target} = \mathcal{T}(\theta_{master}^{current}, \Delta_{optics})$$

**Industry implementation:** The Qualcomm CAMX MultiCamera node manages 3A coordination across multiple ISP streams. See [github.com/quic/camx](https://github.com/quic/camx) (BSD-3, public).

### 1.3 Transition Smoothing Strategies

| Strategy | Principle | Use Case |
|----------|-----------|----------|
| Crossfade | Linearly interpolate both streams' output over N frames | Slow zoom-switch |
| Fast Align | Switch after slave converges in 1–2 frames | Quick focal-length jump |
| Pre-align | Run slave 3A in background before switch | Flagship simultaneous multi-stream |

> **Engineering recommendation (mobile multi-camera):** With two cameras and no simultaneous streaming support, use Fast Align — complete EV alignment first, then switch within 3 crossfade frames. On platforms that support background simultaneous streaming, prefer Pre-align to compress switch latency to under 1 frame. Both strategies must be paired with factory-calibrated cross-camera color offset vector $\boldsymbol{\delta}_{calib}$; otherwise forced AWB alignment will still leave a systematic color temperature bias.

### 1.4 Precise Derivation of Cross-Camera Gain / Shutter Alignment

**Equivalent Exposure Value (EV) Alignment Model:**

Let the master camera (wide-angle) current exposure state be $(t_m, G_m)$ (integration time, gain). The slave camera (telephoto) must align to the same scene luminance; its target EV is:

$$EV_{slave} = EV_{master} + \Delta EV_{optics}$$

$$\Delta EV_{optics} = 2\log_2\frac{F_{tele}}{F_{wide}} + \log_2\frac{T_{wide}}{T_{tele}}$$

The transmittance ratio term $\log_2(T_{wide}/T_{tele})$ corrects for the T-stop difference (actual optical transmittance) between the two lenses. It is measured during factory calibration and written into the camera characteristics file (`camera_characteristics.xml`).

**Hardware Timing Signals for Frame-Level Sync:**

Multi-ISP pipelines achieve frame-level synchronization via the following hardware mechanisms:

- **VSYNC bus (I2C broadcast):** Master camera broadcasts at each SOF via I2C to notify all slave cameras; slaves apply the master's published AE parameters at the next SOF — one-frame latency.
- **GPIO hard trigger:** Master camera's frame-trigger signal is wired to the slave sensor's FSIN (Frame Sync Input) pin, ensuring all sensors begin integration simultaneously.
- **Software frame-number alignment:** On devices without hardware FSIN, software frame alignment is achieved by comparing SOF timestamps in metadata (precision ≈ 10 μs).

**Luminance-Jump Quantification Metric:**

Switch luminance delta is defined as the difference between the mean luminance (Y channel, normalized 0–255) of the last 5 pre-switch frames and the first 5 post-switch frames. Target:

$$|\bar{Y}_{post} - \bar{Y}_{pre}| < 3.0 \quad (\approx 0.05\ \text{EV at moderate luminance})$$

---

## §2 Low-Light PDAF Accuracy Degradation

### 2.1 Degradation Mechanism

PDAF relies on phase-detection pixel pairs on the sensor to measure beam offset. Under low-light (high ISO) conditions:

$$\sigma_\phi \propto \frac{1}{\text{SNR}} \propto \sqrt{\frac{\sigma_{noise}^2}{I_{signal}}}$$

where $\sigma_\phi$ is the phase estimation error. Typical degradation curve:

| Scene Luminance (lux) | Typical PDAF Error | Note |
|----------------------|--------------------|------|
| > 300 lux | < 5 μm (negligible) | Outdoor daylight |
| 30–300 lux | 10–50 μm | Indoor normal lighting |
| 3–30 lux | 50–200 μm | Dusk / dim room |
| < 3 lux | > 500 μm (failure) | Extreme night scene |

### 2.2 Compensation Strategies

**Fallback to CDAF (Contrast Detection AF):**

When PDAF confidence falls below threshold $\tau_{conf}$, automatically switch to contrast-based hill-climbing search:

```
if pdaf_confidence < τ_conf:
    use CDAF with coarse-to-fine sweep
else:
    use PDAF for fast convergence
```

**Slow AF Mode (Extended Integration):**

Increase PDAF pixel integration time (reduce frame rate) to improve SNR at the cost of focus speed.

**Fusion AF (Multi-Sensor Fusion):**

$$d_{final} = \begin{cases} d_{ToF} & \text{if } d_{ToF} < 1.5\text{m and ToF valid} \\ d_{PDAF} & \text{if PDAF confidence} > \tau_{high} \\ d_{CDAF} & \text{fallback} \end{cases}$$

Laser ToF ranging accuracy is light-independent. At distances below 1.5 m, ToF is preferred.

### 2.3 Dirty Lens Effect on PDAF Confidence

Lens contamination (fingerprint oil, water drops, dust) introduces additional phase bias into the phase-difference image, causing a dangerous state of **high confidence but low accuracy** — the PDAF confidence score is inflated while actual focus accuracy degrades.

**Detection mechanisms:**

1. **Global confidence–variance inconsistency:** Compute the spatial standard deviation $\sigma_{conf}$ of the full-frame PDAF confidence map. Under lens contamination, the confidence map shows blocky patterns (abnormally high local confidence in contaminated regions) and $\sigma_{conf}$ rises markedly.
2. **Confidence map low-pass filtering:** Apply a $7\times7$ mean filter to the confidence map to suppress spurious high-confidence spikes from single-point noise:

$$\tilde{C}(x,y) = \frac{1}{49}\sum_{i=-3}^{3}\sum_{j=-3}^{3} C(x+i, y+j)$$

3. **Multi-region consistency voting:** Trust the current PDAF estimate only when the high-confidence region ($\tilde{C} > 0.7$) covers more than 60% of the full frame.

**Lens contamination warning:** If the confidence anomaly is detected for 30 consecutive frames, trigger a "Please clean the lens" user prompt.

### 2.4 PDAF Confidence Map Post-Processing Pipeline

```
Raw Phase Difference Map
    ↓ Phase difference computation (left – right sub-aperture image pair)
    ↓ Confidence estimation (SNR, phase consistency)
    ↓ Bad-pixel mask filtering (occluded and saturated pixels removed)
    ↓ Spatial low-pass smoothing (7×7 mean or Gaussian)
    ↓ Confidence threshold filtering (τ_conf = 0.4)
    ↓ Defocus estimation (defocus = phase_diff / phase_slope_calib)
    ↓ Output: defocus amount + valid-region mask
```

`phase_slope_calib` is a factory calibration parameter describing the linear relationship between phase difference and defocus amount (in μm). It varies with lens focal length and aperture.

---

## §3 3A Three-Loop Coupling Stability

### 3.1 Coupling Relationships

The AE, AWB, and AF loops share the same sensor readout and are physically coupled:

```
AE changes exposure gain
    → Luminance statistics change → AWB statistics affected
      (overexposed regions saturate, cannot be used for CCT estimation)
    → CCM/WB gain changes → AE's Y-channel luminance target shifts

AWB changes WB gains
    → R/G/B channel ratios change → AE perceived brightness changes
      (Y = 0.299R + 0.587G + 0.114B)
    → Indirectly affects AF contrast statistics
```

### 3.2 Decoupling Design Principles

**AE operates in the log-luminance domain:**

$$L_{target} = \log(Y_{target})$$

In log space, the luminance shift caused by color temperature changes is small, weakening the AWB→AE coupling.

**AWB operates in chromaticity space:**

Perform AWB estimation in CIEuv $(u', v')$ chromaticity space, decoupled from luminance $Y$, to prevent AE→AWB interference from amplifying.

**Convergence order scheduling:**

| Loop | Typical Convergence | Scheduling Strategy |
|------|--------------------|--------------------|
| AE | 3–5 frames | Converge first; other loops wait for AE to stabilize |
| AWB | 5–10 frames | Start after AE stable; avoids exposure changes corrupting CCT estimation |
| AF | 10–30 frames (CDAF) / 1–3 frames (PDAF) | Runs independently; AF does not affect AE/AWB |

### 3.3 Oscillation Detection and Damping

When AE and AWB form a positive feedback loop (e.g., an unusual illuminant causes AWB gain changes that continuously re-trigger AE adjustment):

$$\text{Oscillation detected when} \quad \|\bar{Y}(t) - \bar{Y}(t-1)\| > \tau_{osc} \quad \text{for } N \text{ consecutive frames}$$

Upon detection:
1. Temporarily freeze AWB gains (hold last stable value).
2. Reduce AE step size ($K_P$ halved).
3. Apply inter-frame EMA smoothing: $\theta(t) = \alpha \theta(t-1) + (1-\alpha)\theta^*(t)$, increasing $\alpha$ from 0.5 to 0.8.

### 3.4 AF → AE Unidirectional Coupling During Zoom

In cameras with continuous zoom (periscope or liquid lens), lens element movement changes the effective aperture, altering the luminous flux reaching the sensor:

$$\Delta EV_{AF} = -2\log_2\frac{F_{new}}{F_{old}}$$

When AF drives the VCM to move lens elements, AE must simultaneously compensate for this EV change, otherwise luminance fluctuates during zoom. Engineering implementation:

- The VCM driver writes the current lens position into frame metadata via I2C.
- AE reads the lens position, looks up the pre-calibrated $F(\text{position})$ curve, and computes the $\Delta EV_{AF}$ compensation.
- This compensation is applied as **feedforward** (outside the PI closed loop) — it does not pass through the PI controller.

### 3.5 Quantification of AWB Gain Changes on AE Luminance Perception

AE typically computes Y-channel statistics in the Bayer domain (pre-demosaic), approximated as:

$$Y \approx 0.299 \cdot w_R \cdot R + 0.587 \cdot w_G \cdot G + 0.114 \cdot w_B \cdot B$$

where $w_R, w_G, w_B$ are AWB white-balance gains. When AWB transitions from daylight ($w_R \approx 1.0,\ w_B \approx 1.8$) to tungsten ($w_R \approx 2.2,\ w_B \approx 0.8$):

$$\Delta Y = 0.299 \cdot \Delta w_R \cdot R + 0.114 \cdot \Delta w_B \cdot B$$

In a typical indoor scene ($R/G \approx 0.9,\ B/G \approx 0.7$), this $\Delta Y$ can reach 10–15%, sufficient to re-trigger AE adjustment. **Solution:** AE computes luminance in normalized gain space with $w_G = 1$, eliminating the first-order effect of AWB gain changes on luminance perception.

### 3.6 Scene-Adaptive 3A: Scene Classification Driving Multi-Loop Coordination

On flagship phones, 3A is no longer three independent controllers — it is a coupled system orchestrated by a **scene classification module**. The scene category directly determines which parameter set each loop uses:

```
AI Scene Classification
    Input: thumbnail (224×224) + AE statistics
    Output: scene probabilities (P(indoor), P(outdoor), P(night), P(face), P(text), ...)

Scene category → controls the following 3A parameter sets:
    AE:   [luminance target, anti-banding priority, HDR trigger threshold, max ISO]
    AWB:  [algorithm weight (Gray World vs Statistical AWB), CCT range constraint]
    AF:   [focus zone weight (face-priority vs center-weight), PDAF/CDAF switch threshold]
```

**Typical scene–parameter mapping:**

| Scene Type | AE Target EV Offset | AWB Strategy | AF Strategy |
|-----------|--------------------|--------------|-----------  |
| Outdoor daylight | 0 EV (standard) | Gray World + illuminant constraint | PDAF priority |
| Indoor artificial light | +0.3 EV (slightly brighter) | Statistical AWB (anti-yellow bias) | PDAF + face weight |
| Night scene | +0.5 EV (night boost) | Fixed AWB (prevent CCT oscillation) | Laser ToF priority |
| Face close-up | Face-zone metering | Skin-tone constrained AWB | Face PDAF |
| Backlit scene | HDR mode, compress highlights | Neutral-constrained AWB | Subject-contour CDAF |

### 3.7 Multi-Frame 3A and TNR/HDR Merge Interaction

**TNR effect on AE:**

TNR-fused images have noise reduced by $\sqrt{N}$ compared to a single frame — this is a trap for AE statistics. If AE estimates luminance from the TNR output frame, the artificially suppressed variance makes the controller incorrectly judge that dark-region detail is already clean, maintaining under-exposure: an "under-exposure → TNR denoising → AE misjudges → continues under-exposure" negative feedback chain.

**Engineering fix is straightforward:** AE statistics are computed on the raw RAW frame **before** TNR (Pre-TNR AE stats). TNR output goes only to the display/storage path and never enters the AE closed loop.

**HDR multi-frame merge effect on AWB:**

HDR merge combines the short-exposure frame (highlight data) and long-exposure frame (shadow data) into a single image. Each frame's color characteristics only represent one portion of the dynamic range. If AWB estimates color temperature from the merged composite, the color noise from both exposure ranges accumulates, raising CCT estimation variance significantly.

**Correct approach:** AWB statistics are computed on the **middle-exposure frame** (M-frame, EV=0). The M-frame's highlights and shadows both lie within the sensor's linear region, making it the most reliable source for CCT estimation.

---

## §4 Multi-Frame 3A Fusion

### 4.1 3A Strategy During Burst Capture

During burst capture (continuous shooting, night multi-frame), the typical 3A strategy is **lock** rather than continuous adjustment:

**AE Lock in Burst:**
- Before burst start, trigger Pre-Capture AE (Android Camera2 API `PRECAPTURE_TRIGGER`) and wait for AE convergence.
- After convergence, lock AE (`AE_LOCK = true`); all burst frames use the same exposure parameters.
- Purpose: ensure consistent luminance across frames to provide a stable reference for subsequent alignment and merging.

**AWB Lock in Burst:**
- Synchronized with AE Lock — freeze AWB gains at burst start.
- Prevents white balance drift causing color inconsistency across frames (color inconsistency is harder to fix during merging than luminance inconsistency).

**AF Behavior in Burst:**
- Static shooting (tripod): focus before burst, then lock AF.
- Continuous tracking (moving subject): maintain CRAF (Continuous AF), update focus every frame (for sports burst, not multi-frame denoising merge).

### 4.2 Pre-Capture Sequence Design

```
User presses shutter (Shutter Release)
    ↓ [Stage 1: Pre-Capture AE/AWB/AF, ~3-8 frames]
    Trigger PRECAPTURE_TRIGGER
    AE converges (luminance error < 3%)
    AWB converges (CCT error < 100 K)
    AF locks (confidence > 0.8)
    ↓ [Stage 2: Lock & Burst, N frames]
    AE_LOCK = true
    AWB_LOCK = true
    AF_LOCK = true (or CRAF continues)
    Capture N consecutive RAW frames
    ↓ [Stage 3: Post-Processing]
    Frame alignment → merge (TNR/HDR) → ISP → JPEG/HEIF
```

More Pre-Capture frames mean better 3A convergence, but longer shutter lag. Flagship cameras compress this to under 200 ms (~3–5 frames) for a reason: beyond 300 ms, users perceive the camera as "unresponsive." Achieving sub-200 ms requires **Predictive 3A** — begin pre-running 3A when the user half-presses the shutter, rather than waiting for a full press.

### 4.3 HDR Multi-Frame Merge and AE Bidirectional Interaction

**AE determines the HDR exposure ratio:**

AE must decide the exposure ratio $R = t_L / t_S$ between the long-exposure frame (L) and the short-exposure frame (S):

$$R = \frac{\text{darkest valid pixel target signal}}{\text{brightest non-saturated highlight signal}} \approx \frac{Y_{target,dark}}{Y_{safe,highlight}}$$

Typical values: $R = 4$ (2 EV HDR) to $R = 16$ (4 EV HDR). AE automatically computes $R$ by analyzing the bimodal luminance histogram of the scene (the dynamic range span between the highlight peak and shadow peak).

**HDR merge feedback on AE convergence:**

The luminance distribution of an HDR-merged image differs from any single frame. If AE statistics are computed on the merged image, a multi-level feedback loop forms: "AE targets merged image → adjusts exposure → new merged image → re-adjusts." **Solution** (as in §3.7): AE statistics are fixed on the middle-exposure frame (M-frame), so HDR merge only affects the final output and never enters the AE closed loop.

---

## §5 Tuning

### 5.1 Multi-Camera Transition Smoothing Parameters

| Parameter | Recommended Range | Description |
|-----------|------------------|-------------|
| `crossfade_frames` | 3–8 frames | Number of crossfade frames at switch |
| `ev_correction_step` | 0.1 EV/frame | Master-slave EV alignment step size |
| `awb_sync_alpha` | 0.3–0.5 | AWB parameter interpolation coefficient |
| `ev_match_tolerance` | 0.15 EV | EV alignment convergence tolerance |
| `precheck_frames` | 2–4 frames | Pre-switch background pre-alignment frames for slave |

### 5.2 PDAF Fallback Thresholds

| Parameter | Recommended Value | Description |
|-----------|------------------|-------------|
| `pdaf_conf_threshold` | 0.3–0.5 | Below this, switch to CDAF |
| `tof_range_max` | 1.0–2.0 m | Upper distance limit for ToF priority |
| `slow_af_iso_threshold` | ISO 1600–3200 | ISO gate for triggering slow AF mode |
| `pdaf_conf_spatial_std_max` | 0.15 | Confidence map std-dev threshold for dirty lens detection |
| `pdaf_valid_area_min` | 0.6 | Below this high-confidence area fraction, do not trust PDAF |

### 5.3 Three-Platform Advanced 3A Parameter Comparison

The following shows typical differences in advanced 3A configuration across the three mainstream SoC platforms — Qualcomm, MediaTek, and HiSilicon — compiled from public documentation and industry experience (not a complete specification; for reference only):

| Parameter / Feature | Qualcomm (Snapdragon) | MediaTek (Dimensity) | HiSilicon (Kirin) |
|--------------------|-----------------------|---------------------|------------------|
| Multi-camera coordination | CAMX MultiCamera node, up to 4 parallel 3A streams | MMSDK MultiCam, up to 3 streams | IPP MultiCamera, up to 4 streams |
| Frame sync method | Hardware FSIN GPIO + software frame-number alignment (dual redundancy) | Primarily software frame-number alignment | Hardware VSYNC broadcast |
| AWB statistics domain | Bayer domain (pre-demosaic) + linearized | Bayer domain | Bayer domain + optional post-demosaic stats |
| PDAF confidence bit-width | 12-bit | 10-bit | 12-bit |
| Scene classification integration | Qualcomm AI Engine, Scene Detection SDK | APU-integrated, NeuroPilot scene classification | NPU, Huawei AI Scene Recognition |
| 3A tuning toolchain | QCAT (Qualcomm Camera Autofocus Tool) | Camera Tuning Tool (CTT) | Tune Tool (Huawei internal) |
| HDR multi-frame AE statistics | Long/medium/short frame independent stats, weighted merge | Post-merge statistics (some versions support per-frame) | Per-frame stats, middle-exposure frame as primary |
| Anti-banding detection | Time-domain FFT (128-point), auto-detects 50/60 Hz | Time-domain FFT + rule-based detection | Adaptive flicker detection |
| Max multi-frame merge count (AE-aware) | 8 frames (TNR-aware) | 4 frames (TNR-aware) | 6 frames (TNR-aware) |

> Note: Data in the table above is sourced from public white papers (Qualcomm CAMX docs, MTK MMSDK docs, Huawei IPP public materials) and industry experience. Specific SKUs may differ significantly; always consult the latest toolchain documentation during debugging.

### 5.4 Oscillation Damping Parameters

| Parameter | Recommended Range | Description |
|-----------|------------------|-------------|
| `ae_awb_osc_threshold` | 0.03–0.05 (normalized luminance) | Oscillation detection sensitivity |
| `ae_awb_osc_frames` | 5–10 frames | Consecutive frames required to declare oscillation |
| `awb_freeze_duration` | 10–20 frames | AWB freeze duration after oscillation detection |
| `ae_kp_damp_factor` | 0.4–0.6 | AE proportional gain attenuation factor during oscillation |
| `ema_alpha_damp` | 0.7–0.85 | EMA coefficient during oscillation damping |

---

## §6 Evaluation

### 6.1 Multi-Camera Switch Quality Metrics

- **Switch luminance delta ($\Delta L_{switch}$):** Mean luminance difference across 5 frames before and after switch. Target: < 0.5 EV.
- **CCT jump ($\Delta CCT_{switch}$):** Color temperature difference across the switch. Target: < 200 K.
- **Focus switch latency:** Frames from switch completion to re-focus lock. Target: < 10 frames.

### 6.2 PDAF Low-Light Evaluation

Measure PDAF success rate (success = focus error < 50 μm) at ISO 3200 and ISO 6400, and compare degradation against the daylight baseline (ISO 100).

**Evaluation matrix:**

| ISO | Test Scene Luminance (lux) | PDAF Success Rate Target | CDAF Fallback Rate Limit |
|-----|---------------------------|--------------------------|--------------------------|
| 100 | > 500 | > 99% | < 1% |
| 400 | 100–500 | > 95% | < 5% |
| 1600 | 10–100 | > 80% | < 20% |
| 3200 | 3–10 | > 60% | < 40% |
| 6400 | < 3 | > 30% | < 70% |

### 6.3 3A Loop Coupling Stability Evaluation

**Oscillation frequency test:**
- Capture 300 preview frames under tungsten (2800 K) and mixed illumination (half tungsten, half fluorescent).
- Extract per-frame Y-channel mean time series and perform FFT analysis.
- Target: no sustained oscillation — power spectral density peak at any frequency above 1 Hz must be below 5% of the DC component.

**Multi-camera switch test standard scenes:**
1. **Outdoor daylight switch (1× → 3×):** Luminance jump < 0.1 EV, CCT jump < 150 K.
2. **Indoor low-light switch (1× → 2×):** Luminance jump < 0.2 EV, re-focus lock < 8 frames.
3. **Backlit scene switch:** HDR mode correctly inherited, no sudden highlight overexposure.

### 6.4 Scene-Adaptive 3A Evaluation

| Test Scene | Target Metric | Typical Benchmark |
|-----------|---------------|--------------------|
| Face detection → AE metering zone switch latency | N frames after face detected for metering zone to shift to face region | < 3 frames |
| AWB stabilization frames after night scene mode switch | Frames for AWB to re-stabilize after switching ISP profile | < 15 frames |
| Scene classification false positive rate (indoor misclassified as outdoor) | Evaluated on 500 test images | < 5% |
| Backlit HDR correct trigger rate | Auto-enable HDR when highlight zone EV > +3 | > 95% |

### 6.5 AE Convergence Speed

**Definition:** Frames from a step change in scene luminance (e.g., suddenly entering/leaving a brightly lit area) until AE output stabilizes within ±5% of the target:

$$N_{converge} = \min\left\{n \;\middle|\; \forall k \geq n,\; \left|\frac{Y(k) - Y_{target}}{Y_{target}}\right| \leq 0.05\right\}$$

**Test method:**
1. Fixed target (standard gray card, $Y_{target} = 118$, 18% gray).
2. Use an opaque card to rapidly cover/uncover the lens, simulating a luminance step from $L_0$ to $L_1$ (common combinations: dark room 5 lux → indoor 500 lux; indoor → bright sunlight 80,000 lux).
3. Record AE luminance $Y(k)$ per frame; compute $N_{converge}$.
4. Targets:
   - Fast scene change (e.g., lights switched on): $N_{converge} \leq 8$ frames (@30 fps, ~267 ms).
   - Continuous preview with normal movement: $N_{converge} \leq 20$ frames (@30 fps, ~667 ms).

**Stepwise convergence curve analysis (typical values):**

| Phase | Frame Range | Luminance Behavior | Typical Notes |
|-------|-------------|-------------------|---------------|
| Overshoot | 1–3 frames | $|Y - Y_{target}| > 30\%$ | Proportional term dominates; integral not yet built up |
| Fast convergence | 3–8 frames | Error drops from 30% to 10% | Integral term takes over; step size limited to prevent overshoot |
| Fine tuning | 8–15 frames | Error < 5%, micro-adjustment phase | Small-step AE corrections eliminate residual error |
| Steady state | > 15 frames | $|Y - Y_{target}| < 2\%$ | Closed-loop stable |

### 6.6 AE Accuracy (Steady-State Error)

**Definition:** Error between the steady-state luminance (typically mean over 10 post-convergence frames) and the target luminance, expressed in EV:

$$\Delta EV_{steady} = \log_2\frac{\bar{Y}_{steady}}{Y_{target}}$$

Target: $|\Delta EV_{steady}| \leq 0.1\ \text{EV}$ (approximately 7% luminance error).

**Evaluation scene matrix:**

| Scene | Metering Zone | Target $|\Delta EV|$ | Notes |
|-------|--------------|---------------------|-------|
| Standard gray card (18% gray) | Full-frame average metering | ≤ 0.05 EV | Strictest baseline |
| Face close-up | Face zone center-weighted metering | ≤ 0.1 EV | Background may be slightly over-exposed |
| Backlit scene | HDR subject zone metering | ≤ 0.15 EV | Evaluated after HDR merge |
| High-contrast indoor | Center-weighted | ≤ 0.1 EV | Ignore edge overexposure areas |

### 6.7 AF Focus Accuracy

**Definition:** Across multiple shots (typically N=50) at a specified subject distance (e.g., 50 cm, 100 cm, 300 cm), the fraction of results that fall within the Depth of Field (DoF):

$$\text{AF Accuracy} = \frac{\text{shots in-DoF}}{N} \times 100\%$$

DoF calculation (circle of confusion diameter $c$, focal length $f$, aperture $F_{num}$, subject distance $D$):

$$\text{DoF} \approx \frac{2 D^2 F_{num} c}{f^2}$$

Typical mobile parameters (wide-angle, $f=5.6\text{ mm}$, $F_{2.0}$, $c=0.029\text{ mm}$):

| Subject Distance | DoF (approx.) | AF Accuracy Target (PDAF) | AF Accuracy Target (CDAF fallback) |
|-----------------|---------------|--------------------------|-----------------------------------|
| 30 cm (macro) | ±3 mm | > 90% | > 75% |
| 100 cm (portrait) | ±20 mm | > 95% | > 85% |
| 300 cm (mid-range) | ±180 mm | > 98% | > 92% |
| Infinity (landscape) | Beyond hyperfocal | N/A | N/A |

**Test chart:** ISO 12233 resolution test chart or Siemens star target recommended, tested in a reflection-free environment. Confirm focus plane alignment with the chart plane via the MTF50 curve.

### 6.8 AWB Angular Error

**Definition:** The angle between the estimated illuminant color vector and the ground-truth illuminant color vector — the standard quantitative metric for AWB accuracy (Finlayson & Hordley, JOSA-A, 2001).

**Standard calculation (3D normalized RGB vector):**

Let normalized illuminant vector $\hat{\mathbf{e}}_{est} = (\mu_R, \mu_G, \mu_B)/\|(\mu_R, \mu_G, \mu_B)\|$, ground truth $\hat{\mathbf{e}}_{gt} = (l_R, l_G, l_B)/\|(l_R, l_G, l_B)\|$; then:

$$\varepsilon_{ang} = \arccos\left(\hat{\mathbf{e}}_{est} \cdot \hat{\mathbf{e}}_{gt}\right) \times \frac{180°}{\pi}$$

**AWB algorithm comparison benchmark (typical results on NUS-8 dataset):**

| AWB Algorithm | Median Angular Error | Mean Angular Error | Notes |
|--------------|----------------------|-------------------|-------|
| Gray World | 4.5° | 6.2° | Baseline; usable in simple scenes |
| White Patch | 3.8° | 5.3° | Better in highlight-rich scenes |
| Statistical AWB (2nd-order Gray) | 2.9° | 3.8° | Requires calibration |
| Deep Learning AWB (FFCC, 2017) | 1.4° | 1.8° | Common in flagship phones |
| Target (industry standard) | < 2.0° | < 3.0° | < 3° generally considered acceptable |

**Correlation with subjective perception:** < 1° nearly imperceptible; 1–3° detectable slight color cast; > 5° obvious color cast (skin appears greenish or yellowish).

---

## §7 Failure Cases

### 7.1 PDAF Striping

**Cause:** PDAF sensors embed phase-detection pixel pairs (PD pixels) in the Bayer array. These PD pixels are cut off-center by their microlenses (Left-blocked / Right-blocked), giving them different spectral sensitivity from normal pixels:

$$R_{PD} = R_{normal} \cdot (1 - \delta_{sensitivity}), \quad \delta_{sensitivity} \approx 0.05\text{–}0.15$$

Because PD pixels are arranged in a regular row/column pattern (typically one PD-pair row per 2 rows, period of 4–8 rows), their sensitivity difference appears in RAW as **periodic horizontal or vertical luminance banding**, which becomes especially visible after demosaicing (false color / banding near high-frequency edges).

**Correction — PDAF Correction in Demosaic Stage:**

1. **PD pixel location map:** Obtain the full-frame PD pixel coordinate map (PDAF pixel map) from the sensor vendor's PDAF metadata (typically encoded in EXIF / ISP configuration).
2. **PD pixel interpolation replacement:** Before Bayer demosaicing, replace PD pixel luminance values by interpolating from neighboring normal pixels, eliminating amplitude bias from sensitivity mismatch:

$$\hat{I}_{PD}(x,y) = \frac{1}{|N_p|}\sum_{(i,j)\in N_p} I_{normal}(i,j)$$

where $N_p$ is the set of nearby normal pixels at position $(x,y)$ (typically the nearest 4 same-channel non-PD pixels).

3. **Sensitivity correction:** If interpolation replacement is not performed, apply a sensitivity compensation gain directly to PD pixels:

$$I_{corrected}(x,y) = I_{raw}(x,y) / (1 - \delta_{sensitivity})$$

$\delta_{sensitivity}$ is measured during factory calibration via a uniform light source (integrating sphere), stored in the calibration database (OTP or calibration file).

**Typical platform implementations:** Sony IMX series sensors (IMX766, IMX989) provide a PDAF pixel coordinate table (`pdaf_coordinates` struct) and recommended PD-correction algorithms. Qualcomm ISP integrates PDAF correction in the BPC/BCC module.

### 7.2 Multi-Camera Color Seam

**Cause:** In multi-camera systems, each camera runs its own independent AWB and AE loops. Due to optical differences (lens transmittance color shift, sensor spectral response variation, field-of-view luminance differences from different focal lengths), each loop converges to a slightly different CCT estimate and exposure state, even for the same scene. At the switch instant from master (e.g., 1× wide-angle) to slave (e.g., 3× telephoto):

- **CCT jump:** Wide-angle AWB converges to 5500 K, telephoto AWB only to 5100 K — a 400 K difference at the switch frame causes a yellowish or bluish flicker.
- **Color seam:** In continuous optical zoom scenarios, a single-frame color discontinuity "seam" may appear near the camera physical switch point.

**Suppression approaches:**

**Approach 1: AWB Force-Sync**

Before switching, force-align the slave AWB gains to the master's current AWB gains (accounting for the cross-camera color calibration offset $\Delta_{CCT,calib}$):

$$\mathbf{w}_{slave}^{init} = \mathbf{w}_{master}^{current} + \boldsymbol{\delta}_{calib}$$

where $\boldsymbol{\delta}_{calib} = (\delta_R, \delta_G, \delta_B)$ is the factory-calibrated cross-camera color offset vector (measured by shooting both cameras at the same color chart, written into the camera parameter file).

**Approach 2: Crossfade Color Correction**

Over $K$ frames after the switch, linearly interpolate CCT on the slave output:

$$CCT_{output}(t) = CCT_{slave}(t) \cdot \frac{t - t_{switch}}{K} + CCT_{master}(t_{switch}) \cdot \left(1 - \frac{t - t_{switch}}{K}\right)$$

This uses a $K$-frame gradual transition to mask the color temperature discontinuity at the switch instant. $K = 5\text{–}10$ frames is the empirical optimum.

**Engineering specification (Color Seam Specification):**

$$\Delta CCT_{seam} = |CCT_{post-switch} - CCT_{pre-switch}| < 150\ \text{K}$$
$$\Delta E_{seam} < 2.0\ (\text{CIELAB ΔE}_{00})$$

### 7.3 AF Hunting

**Cause:** Focus hunting is the oscillatory instability of the CDAF hill-climbing search algorithm under the following conditions:

1. **Flat contrast peak:** When subject texture is insufficient or the scene lacks high-frequency detail, the contrast curve's peak is wide and flat; the CDAF algorithm cannot accurately locate the maximum, and oscillates back and forth near the peak:

$$\frac{\partial C}{\partial d}\bigg|_{d_{focus}} \approx 0, \quad \frac{\partial^2 C}{\partial d^2}\bigg|_{d_{focus}} \approx 0$$

2. **Low-texture scene:** In scenes with blue sky, white walls, or solid-color backgrounds, the contrast statistics signal (e.g., Laplacian variance) noise floor exceeds the effective texture signal (SNR < 3 dB), causing the algorithm to mistake noise extrema for the focus point.

3. **Step size too large:** When the VCM driver's minimum step size is too large, the contrast difference between adjacent search positions falls within the quantization noise floor, preventing monotonic convergence.

**Detection mechanism:**

$$\text{Hunting} = \begin{cases} \text{True} & \text{if} \; |\text{lens\_pos}(t) - \text{lens\_pos}(t-2)| > \Delta_{hunt} \text{ for } M \text{ consecutive frames} \\ \text{False} & \text{otherwise} \end{cases}$$

where $\Delta_{hunt}$ is the hunting detection step threshold (typically 3–5% of VCM full travel) and $M = 4\text{–}6$ frames.

**Suppression strategies:**

| Strategy | Principle | Applicable Condition |
|----------|-----------|---------------------|
| Focus lock | Lock at current position after hunting detected; wait for scene change | Static low-texture scene |
| PDAF fallback | If PDAF confidence > $\tau_{low}$, switch to PDAF-assisted convergence | Light present but texture poor |
| Adaptive step reduction | Halve VCM step size after hunting detection for fine search | Flat peak |
| Best-position hold | Track historical maximum-contrast position $d_{best}$; retreat to $d_{best}$ after hunting | Any hunting situation |
| Low-pass contrast curve filtering | EMA-smooth contrast values across frames ($\alpha=0.7$); reduce noise-driven false extrema | Low-texture high-noise |

**Engineering parameter recommendations:**

```
hunting_detect_threshold    = 15  % VCM DAC counts (~5% of full travel)
hunting_detect_frames       = 5   % consecutive frames
fine_step_reduction_factor  = 0.5 % step size reduction ratio after hunting
best_position_hold_frames   = 30  % hold duration for best-position lock
cdaf_texture_snr_min        = 3.0 % dB; below this, treat as low-texture and fall back to PDAF
```

---

## §8 PDAF Physics Deep Dive

### 8.1 Phase Detection Principle

The core physical principle of PDAF is lateral image displacement caused by **wavefront tilt**. Left-masked pixels (L) and right-masked pixels (R) embedded in the sensor receive light only from the left half and right half of the lens respectively, forming a left sub-aperture image and a right sub-aperture image.

When the subject is **front-focused**, the L image shifts rightward relative to the R image; when **back-focused**, it shifts leftward; when **in-focus**, L and R images are aligned with zero shift.

**Phase difference to subject distance relationship (PDAF fundamental equation):**

$$\boxed{\Delta x_{PD} = \frac{f \cdot d}{D_z}}$$

where:
- $\Delta x_{PD}$: lateral displacement between L and R sub-aperture images (pixel units)
- $f$: lens focal length (mm)
- $d$: effective pupil separation distance between the L/R PD pixel pair (mm), determined by sensor microlens design (typically 0.5–1× pixel pitch)
- $D_z$: subject distance from sensor (mm)

**Derivation (geometric optics):**

Let the image distance from lens principal plane to sensor be $v$ (determined by thin-lens formula $1/f = 1/D_z + 1/v$); at in-focus, the image plane coincides with the sensor. Out-of-focus, the point $P$'s circle of confusion (CoC) diameter on the sensor plane is:

$$c = d \cdot \left|\frac{v - v_0}{v_0}\right|$$

From this, the phase difference is derived: $\Delta x_{PD} \approx f \cdot d / D_z$ (near-field requires higher-order correction terms).

**Defocus-to-phase-difference conversion:**

In practice, the **phase slope calibration coefficient** $k_{phase}$ (units: DAC counts/pixel shift) converts phase difference to VCM drive amount:

$$\text{VCM\_delta} = k_{phase} \cdot \Delta x_{PD}$$

$k_{phase}$ is obtained by multi-distance calibration during factory production (subject placed at multiple known distances; corresponding phase differences measured and fitted), then stored in OTP (One-Time Programmable memory).

### 8.2 PDAF Calibration: Optical Center Offset Correction

Due to manufacturing tolerances, the actual optical center (Chief Ray Angle, CRA) of PD pixel microlenses deviates from the design value, causing **position-dependent systematic phase offset** (Phase Offset Map) across the full frame.

**Calibration procedure:**

1. Point the camera at an infinitely distant uniform bright target (integrating sphere or clear sky against a white wall).
2. Capture full-frame PDAF statistics in a known in-focus state (confirmed by CDAF).
3. At this point, the theoretical phase difference is 0; measured phase differences are the position-dependent offset map $\Phi_{offset}(x,y)$.
4. Correction: $\Delta x_{PD,corrected}(x,y) = \Delta x_{PD,raw}(x,y) - \Phi_{offset}(x,y)$.
5. $\Phi_{offset}(x,y)$ is stored in OTP or calibration file (typically as a polynomial or lookup table).

**CRA mismatch:** In full-frame sensors or large-aperture lenses, the chief ray incidence angle (CRA) at image edges can reach 20–30°. If microlens CRA design does not match, edge PDAF accuracy degrades significantly. Solution: Lens-Sensor Co-Design ensuring CRA compatibility across the full frame.

### 8.3 Dual-PD Sensor (Sony IMX766 as Example)

Traditional PDAF embeds PD pixel pairs only every few rows (Sparse PDAF, coverage ≈ 5–10%), limiting PDAF spatial resolution and focus speed.

**Dual-PD (All-Pixel PDAF)** architecture (Sony IMX766, IMX989; Samsung ISOCELL GN series) implements L/R optical path separation inside every pixel: two independent photodiodes (Left PD + Right PD) are placed under a single pixel's microlens. Each pixel simultaneously outputs L and R signals; coverage reaches 100%.

**Dual-PD advantages:**

| Comparison | Sparse PDAF | Dual-PD (All-Pixel PDAF) |
|-----------|-------------|--------------------------|
| Coverage | 5–10% | 100% |
| AF spatial resolution | Low (1 measurement per 8–16 rows) | High (computable per pixel) |
| Low-light PDAF capability | Weak (few PD pixels, low SNR) | Strong (full-frame PD; can average over regions) |
| Striping artifacts | More visible (sensitivity delta in regular row pattern) | Milder (but L+R merge requires special demosaic) |
| PDAF readout data volume | Low | High (2× data; requires bandwidth) |
| Representative models | OmniVision early PDAF | Sony IMX766, IMX989; Samsung GN2 |

**IMX766 Dual-PD demosaicing note:** During readout, L+R merged (Full Pixel = L+R) is used as normal Bayer; L−R (Phase Difference) is used for AF computation. Demosaicing must be **PDAF-aware** — after extracting AF data, perform luminance repair on PD pixels; otherwise, mild banding remains.

### 8.4 CDAF vs PDAF Comparison

| Dimension | CDAF (Contrast Detection AF) | PDAF (Phase Detection AF) |
|----------|------------------------------|--------------------------|
| **Working principle** | Hill-climbing search for contrast maximum | Directly measure phase difference to compute direction and distance |
| **Focus speed** | Slow (requires multi-frame search, 20–50 steps) | Fast (converges in 1–3 frames) |
| **Low-light performance** | Better (only needs sufficient readout brightness) | Weak (phase difference SNR drops with illuminance) |
| **Low-texture scene** | Poor (no contrast means no search basis) | Better (relies on pupil separation, not entirely on texture) |
| **Accuracy** | High (diffraction-limited) | Affected by calibration accuracy (±10–30 μm system error) |
| **Depth dependence** | None (pure image statistics) | Yes ($\Delta x_{PD} = fd/D_z$; influenced by focal length) |
| **Hardware requirement** | None (standard Bayer sensor) | PDAF pixels required (higher cost) |
| **Typical use** | Low-light / macro / solid-color fallback | Mainstream daily-use fast AF |
| **Hybrid use** | Hybrid AF: PDAF coarse-locates + CDAF fine-tunes | — |

---

## §9 Multi-Camera 3A Coordination

### 9.1 Multi-Camera 3A State Sync Architecture

Flagship multi-camera systems (primary + ultra-wide + telephoto, up to 4 cameras) require state sharing at the following levels:

```
┌────────────────────────────────────────────────────────────┐
│              3A Coordination Manager (HAL Level)            │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Primary (1×) │  │ Ultra-wide   │  │  Telephoto (3×/5×) │  │
│  │  AE: master  │  │  (0.6×)      │  │   AE: slave        │  │
│  │  AWB: master │  │  AE: slave   │  │   AWB: slave       │  │
│  │  AF: indep.  │  │  AWB: slave  │  │   AF: indep. (SAF) │  │
│  └──────┬───────┘  │  AF: indep.  │  └─────────┬──────────┘  │
│         │          └──────┬───────┘             │             │
│         │  EV/CCT broadcast                     │             │
│         └──────────────────┴─────────────────────┘            │
└────────────────────────────────────────────────────────────┘
```

**Primary camera coordination responsibilities:**
- Publish current AE state ($EV_{master}$) and AWB state ($CCT_{master}$, or WB gain vector) every frame for slave cameras.
- When a switch is anticipated (zoom gesture detected), publish a "switch preview" in advance to trigger slave camera background pre-alignment.

**Slave camera follow strategy:**

$$EV_{slave}(t) = EV_{master}(t) + \Delta EV_{calib,optics} + \Delta EV_{luma\_diff}(t)$$

where $\Delta EV_{luma\_diff}(t)$ is the luminance difference from the slave's independent metering (compensating for field-of-view differences — e.g., telephoto aimed at a local highlight while wide-angle includes a large dark area).

### 9.2 Zoom Transition Smoothing

At the optical zoom switch point, the scene undergoes a physical camera transition (e.g., from 1× to 3×), involving:

**AE transition smoothing:**

Define the transition zone as $[z_1, z_2]$ (zoom multiplier, e.g., $[2.8\times, 3.2\times]$). Within this range, interpolate EV output:

$$EV_{output}(z) = EV_{main}(z) \cdot \alpha(z) + EV_{tele}(z) \cdot (1 - \alpha(z))$$

$$\alpha(z) = \frac{z_2 - z}{z_2 - z_1}, \quad z \in [z_1, z_2]$$

During video recording, both ISP streams run simultaneously (Dual-Stream Mode); $EV_{output}$ software-blends both frame outputs, avoiding abrupt transition frames.

**AWB transition smoothing:**

Similar to AE transition — linearly interpolate CCT across the switch zone, while ensuring $|\Delta CCT_{transition}| < 50\text{ K/frame}$ (to prevent perceptible flicker).

**AF SAF (Seamless Auto Focus):**

During optical zoom, the focal length changes continuously; the VCM position corresponding to the same focus distance changes with focal length. SAF mechanism:

1. Continuously track the focus **subject distance** $D_z$ (back-calculated from PDAF equation $D_z = f \cdot d / \Delta x_{PD}$).
2. When focal length changes to $f'$, re-compute the target VCM position:

$$\text{VCM}_{target}(f') = k_{phase}(f') \cdot \frac{f' \cdot d}{D_z}$$

3. Proactively drive VCM to follow the focal length change, maintaining focus throughout with no re-search needed.

SAF requires the VCM controller to have **predictive drive** capability — at fast zoom speeds (e.g., rapid pinch gesture), pre-compute the VCM target position rather than waiting for PDAF feedback (closed-loop latency ≈ 2–3 frames).

### 9.3 Color Seam Suppression

Color seam suppression at the multi-camera boundary (switch point) significantly impacts video zoom experience. Industrial-grade solutions operate at three levels:

**Level 1: Factory Calibration**
- Cross-camera color calibration: shoot all camera combinations with a ColorChecker 24-patch chart under 3–5 standard illuminants.
- Compute the $3\times3$ color conversion matrix between each camera pair: $\mathbf{I}_{slave,corrected} = \mathbf{M}_{cross} \cdot \mathbf{I}_{slave}$.
- Store $\mathbf{M}_{cross}$ in the camera calibration file; apply it together with AWB sync at each switch.

**Level 2: Runtime Dynamic Alignment**
- At switch time, compare the actual CCT estimation difference between master and slave for the current scene; use adaptive CCT interpolation to eliminate residuals.
- Handles illuminant conditions not fully covered by calibration (e.g., special CCT LED lights).

**Level 3: Image-Domain Post-Processing**
- In YUV domain, apply local color transfer on the switch frame — using the master's current color distribution as reference, transfer the slave output to match (a real-time lightweight version of the Reinhard et al. 2001 color transfer algorithm).
- Cost: additional computation (approximately 5–10 ms @ 1080p on NPU).

**Engineering specification (Color Seam Specification):**

| Metric | Target | Test Condition |
|--------|--------|----------------|
| Switch frame CCT delta $\Delta CCT$ | < 100 K | Standard D65 illuminant, Macbeth gray card scene |
| Switch frame $\Delta E_{00}$ | < 1.5 | Skin-tone patch (#18 Macbeth) |
| Video zoom CCT fluctuation rate | < 30 K/frame | Continuous zoom 1× → 5× |
| Transition frame count | 5–12 frames | Fast switch (gesture focal-length jump) |

---

## §10 Glossary

| Term | English | Definition |
|------|---------|------------|
| Master-slave sync | Master-Slave Sync | Multi-camera synchronization strategy: designate one camera as master controller; others follow and align to master 3A state |
| Frame sync signal | FSIN / Frame Sync Input | Hardware GPIO signal ensuring all sensor streams begin integration at the same instant |
| Equivalent exposure value | EV (Exposure Value) | Logarithmic measure combining shutter, gain, and aperture; 1 EV difference corresponds to 2× luminance |
| PDAF confidence | PDAF Confidence | Reliability of phase-difference estimation (0–1); low confidence triggers CDAF fallback |
| Defocus amount | Defocus Amount | Distance between current imaging plane and focal plane (μm); computed by dividing phase difference by calibration coefficient |
| Oscillation damping | Oscillation Damping | Stabilization measure after AE–AWB coupling oscillation is detected: temporarily reduce controller gain and freeze AWB |
| Feedforward compensation | Feedforward Compensation | Active EV compensation by AE for aperture changes caused by AF lens movement (bypasses the PI closed loop) |
| Scene-adaptive 3A | Scene-Adaptive 3A | AI scene classification–driven multi-loop 3A parameter switching mechanism |
| Pre-TNR statistics | Pre-TNR AE Stats | AE statistics computed on the raw RAW frame before temporal noise reduction, preventing TNR from disturbing the closed loop |
| T-stop | T-Stop | Effective aperture value corresponding to actual lens optical transmittance (differs from F-number by transmittance loss) |
| EMA smoothing | Exponential Moving Average | $\theta(t) = \alpha\theta(t-1)+(1-\alpha)\theta^*(t)$; used to suppress parameter jumps |
| Crossfade | Crossfade | Multi-camera switch smoothing strategy: linear alpha-blend both streams' output over N frames |
| Pre-Capture AE | Pre-Capture AE | Brief AE convergence sequence triggered before shutter press; ensures accurate exposure before burst capture begins |
| Exposure ratio | Exposure Ratio | Ratio of integration times between long and short exposure frames in HDR multi-frame capture; determines dynamic range coverage |
| Middle exposure frame | Middle Exposure Frame (M-frame) | Frame with mid-range exposure in HDR three-frame structure (L/M/S); typically used as primary reference for AWB/AE statistics |
| Scene classification | Scene Classification | AI module's semantic inference of current frame content (indoor/outdoor/night/face, etc.); drives 3A parameter switching |
| Predictive 3A | Predictive 3A | Predicts optimal next-frame parameters from prior-frame 3A state trends; skips the delay of waiting for closed-loop convergence |
| PDAF striping | PDAF Striping | Periodic luminance banding artifact from PD pixel sensitivity mismatch with normal pixels; must be corrected before demosaicing |
| PD pixel | Phase Detection Pixel | Specially off-center microlens-cut pixels in PDAF sensor; exist as Left-masked (L) and Right-masked (R) variants |
| Phase slope calibration | Phase Slope Calibration | Linear calibration coefficient $k_{phase}$ converting phase difference (pixel shift) to VCM drive amount; stored in OTP |
| CRA mismatch | Chief Ray Angle Mismatch | Microlens chief ray angle not matching lens exit angle; causes systematic phase offset at image edges |
| Dual-PD | Dual Photodiode PDAF | All-pixel phase detection architecture with two photodiodes per pixel (L+R); coverage 100% (e.g., Sony IMX766) |
| AF hunting | AF Hunting | CDAF hill-climbing oscillatory instability in low-texture or flat-contrast-peak scenes |
| Color seam | Color Seam | Sudden color change on the switch frame due to unsynchronized AWB/AE states at multi-camera switch instant |
| Seamless AF | SAF (Seamless Auto Focus) | Maintains focus throughout optical zoom transition via subject-distance tracking and predictive VCM drive; no re-search needed |
| Frames to convergence | Frames-to-Convergence | Frames required for AE/AF/AWB to reach steady state from initial state; core 3A speed evaluation metric |
| AWB angular error | AWB Angular Error | Angle (degrees) in log-chromaticity space between estimated and ground-truth illuminant direction; defined by Finlayson & Hordley |
| Cross-camera color calibration | Cross-Camera Color Calibration | Factory calibration procedure measuring systematic color differences between multiple cameras and writing results to calibration files |
| Circle of confusion | Circle of Confusion (CoC) | Blur circle formed on the image plane by an out-of-focus point source; its diameter determines the sharpness threshold in DoF calculation |

---

## Figures

![3a convergence](img/fig_3a_convergence_ch.png)

*Figure 1. 3A algorithm convergence process schematic (Source: author's original)*

![deep awb](img/fig_deep_awb_ch.png)

*Figure 2. Deep learning–based AWB method (Source: author's original)*

![multi exposure ae](img/fig_multi_exposure_ae_ch.png)

*Figure 3. Multi-exposure AE control schematic (Source: author's original)*

![3a advanced control](img/fig_3a_advanced_control_ch.png)

*Figure 4. Advanced 3A control strategies (Source: author's original)*

![3a system diagram](img/fig_3a_system_diagram_ch.png)

*Figure 5. 3A system block diagram (Source: author's original)*

![ae af awb interaction](img/fig_ae_af_awb_interaction_ch.png)

*Figure 6. AE, AF, and AWB interaction relationships (Source: author's original)*

![awb advanced algorithm](img/fig_awb_advanced_algorithm_ch.png)

*Figure 7. AWB advanced algorithm framework (Source: author's original)*

## References

[1] Qualcomm CAMX MultiCamera — [github.com/quic/camx](https://github.com/quic/camx) (BSD-3, public)

[2] Chen, Q., et al. (2021). Fast and Accurate Phase-Detection Autofocus Using a Single Image. *IEEE Transactions on Image Processing*, 30, 2296–2308.

[3] Nakamura, J. (ed.). *Image Sensors and Signal Processing for Digital Still Cameras*. CRC Press.

[4] Adams, J., et al. (2012). Photographic Metering and Exposure Control. *SPIE Proc. Electronic Imaging*.

[5] MediaTek MMSDK MultiCam Architecture Documentation (MTK developer portal, requires developer account).

[6] Wronski, B., et al. (2019). Handheld Multi-Frame Super-Resolution. *ACM Transactions on Graphics*, 38(4).

[7] Yuan, L., et al. (2020). Multi-Camera System Calibration and 3A Synchronization for Mobile Phones. *IEEE ICASSP*.

[8] Hu, X., et al. (2022). Towards Unified On-Device 3A with Scene Understanding. *CVPR Workshops*.

[9] Geiger, A., et al. (2020). Seamless Zoom with Multi-Camera Systems. *IS&T Electronic Imaging*.

[10] Reinhard, E., et al. (2001). Color Transfer Between Images. *IEEE Computer Graphics & Applications*, 21(5), 34–41.

[11] Sony Semiconductor. *IMX766 Product Brief: Dual-PD All-Pixel PDAF Architecture*. Official documentation, 2023.

[12] Finlayson, G.D., & Hordley, S.D. (2001). Color Constancy at a Pixel. *Journal of the Optical Society of America A*, 18(2), 253–264.

[13] Luo, M.R., et al. (2001). The Development of the CIE 2000 Colour-Difference Formula: CIEDE2000. *Color Research & Application*, 26(5), 340–350.

[14] Lukac, R., et al. (2004). Digital Camera Image Processing: From Sensor to Image. *IEEE Workshop on Digital Media Processing*.

[15] Degaki, R., et al. (2019). Phase Difference Detection Auto Focus in CMOS Image Sensors. *SPIE Photonics West*.

[16] Ohta, N., & Robertson, A. (2005). *Colorimetry: Fundamentals and Applications*. Wiley.
