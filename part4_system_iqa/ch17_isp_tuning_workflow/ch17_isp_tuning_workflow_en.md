# Part 4, Chapter 17: ISP Tuning Workflow: From Prototype to Mass Production

> **Scope:** This chapter covers the full-lifecycle engineering methodology for ISP parameter tuning, from basic calibration at the EVT prototype stage through multi-scene parameter convergence in DVT/PVT pre-mass-production, and describes a systematic iterative tuning workflow.
> **Prerequisites:** Part 2, Chapter 9 (Lens Shading Correction); Part 2, Chapter 6 (Auto White Balance); Part 4, Chapter 1 (3A Control System)
> **Reader path:** ISP tuning engineers, algorithm engineers, camera systems engineers

---

## Table of Contents

1. [Tuning Workflow Theoretical Foundation](#1-tuning-workflow-theoretical-foundation)
2. [Basic Calibration Procedures](#2-basic-calibration-procedures)
3. [Scene-specific Tuning Guide](#3-scene-specific-tuning-guide)
4. [Common Tuning Problems and Diagnostics](#4-common-tuning-problems-and-diagnostics)
5. [Mass Production Tuning Validation](#5-mass-production-tuning-validation)
6. [Code Examples](#6-code-examples)
7. [References](#7-references)
8. [Glossary](#8-glossary)

---

## §1 Tuning Workflow Theoretical Foundation

### 1.1 Project Phase Breakdown and Tuning Objectives

Mobile terminal camera development typically follows the standard hardware iteration flow: EVT (Engineering Verification Test) → DVT (Design Verification Test) → PVT (Production Verification Test) → MP (Mass Production). ISP tuning depth requirements differ substantially across each phase:

**EVT phase** (prototype verification, typically 4–8 weeks):
- Objective: Verify optical path, basic sensor power-on functionality, ISP pipeline connectivity
- Tuning focus: Black Level Correction (BLC), Pixel Defect Correction (PDC), basic LSC (Lens Shading Correction)
- Quality metrics: Image can be previewed normally; no obvious green/magenta stripes; no large areas of dead pixels

**DVT phase** (design verification, typically 6–12 weeks):
- Objective: Achieve full-scene parameter convergence; reach 80% of the target image quality before mass production
- Tuning focus: Fine-tuning AWB (Auto White Balance) / CCM (Color Correction Matrix), NR (Noise Reduction) / EE (Edge Enhancement) trade-off, AE (Auto Exposure) strategy, multi-scene parameter switching
- Quality metrics: ColorChecker ΔE < 5 (D65 illuminant); SNR10 (minimum illuminance achieving 10 dB SNR) meets specification

**PVT phase** (production verification, typically 4–6 weeks):
- Objective: Converge multi-unit consistency; finalize mass production parameters
- Tuning focus: Parameter consistency across batch units (Cpk control); factory calibration procedure validation
- Quality metrics: MTF50 standard deviation < 5 lp/ph across 50+ sample units; ΔE mean < 4

**MP phase:**
- Objective: Ongoing maintenance; OTA parameter updates; field bug fixes
- Tuning focus: Targeted optimization for complex scenes (backlight, night, dynamic scenes)

### 1.2 Sensor-to-Display Tuning Chain

ISP tuning is not the isolated adjustment of a single module; it is a chain with well-defined data dependencies. Understanding upstream/downstream dependencies is the foundation of systematic tuning:

```
RAW Sensor → BLC → PDC → LSC → Demosaic → AWB Gain Apply → CCM
  → NR → Gamma / Tone Mapping → EE → CSC → Display Output
```

**Typical upstream-affects-downstream rules:**
- BLC offset propagates systematically through all downstream modules, causing CCM color shift
- Inaccurate LSC gain maps cause AWB to sample incorrect color temperature estimates at image edges
- Zipper (false color) artifacts introduced by Demosaic are further amplified by EE

**Tuning sequence principle:** Converge modules from foundational to derived, following data dependencies. The parameters of each module can be finalized only after its upstream modules are stable. Violating this principle causes "tuning oscillation" — downstream parameters must be redone each time an upstream module changes.

> **Important:** The standard ISP tuning order is **BLC → LSC → CCM → AWB → Gamma → NR → sharpening → AE**. Note that CCM is calibrated *before* AWB, even though "AWB Gain Apply" appears upstream of CCM in the data pipeline diagram above. This is because CCM is calibrated under known illuminant conditions (no AWB active), producing a per-illuminant linear transform; AWB then interpolates between pre-calibrated CCMs at runtime. BLC and LSC must always come first because all downstream modules assume clean, shading-corrected linear data.

### 1.3 Relationship Between Objective Metrics and Subjective Scores

ISP image quality evaluation has historically faced a tension between objective and subjective assessment. The industry typically employs a dual-track parallel strategy:

**Objective metrics** (quantifiable, automatable):
- MTF50 (Modulation Transfer Function at 50% contrast): resolution metric, unit: lp/ph (line pairs per picture height)
- SNR (Signal-to-Noise Ratio): unit: dB
- ΔE2000: color difference; measures CCM/AWB accuracy
- DR (Dynamic Range): unit: stops or dB

**Subjective scores** (MOS, Mean Opinion Score):
- Typically uses a 5-point ACR (Absolute Category Rating) scale
- Requires at least 10 non-expert raters to reduce individual bias
- ABX blind testing (double-blind comparison) for detecting subtle quality differences

**Key insight:** Objective metrics do not always align with subjective perception. For example, excessive sharpening (high EE gain) can raise MTF50 but introduces visible ringing artifacts, causing subjective scores to drop. Tuning engineers must understand the perceptual meaning behind each metric to avoid chasing objective numbers at the cost of actual user experience.

### 1.4 Iterative Convergence Theory: PID Analogy

Treating ISP tuning as a control problem, the iterative convergence process can be understood through the lens of a PID (Proportional-Integral-Derivative) controller:

- **P (proportional):** Current error. For example, an AWB gain offset ΔG; directly adjusting the corresponding gain table produces a fast response.
- **I (integral):** Accumulated historical error. For systematic bias (e.g., AWB blue cast across all color temperatures), apply global compensation by accumulating measurements across multiple scenes.
- **D (derivative):** Rate of error change. Prevents overfitting to a single scene — over-adjusting one scene's parameters and breaking others corresponds to the derivative term's overshoot suppression.

Practical convergence strategy:
1. **Coarse tuning:** Large-step adjustment to quickly locate the parameter range (analogous to the P-dominated phase)
2. **Fine tuning:** Small-step refinement to eliminate systematic bias (analogous to the I integration phase)
3. **Stability check:** Verify that other scenes have not regressed after the adjustment (analogous to the D constraint preventing overshoot)

In addition, maintaining a **parameter change log** — recording each modified parameter name, change magnitude, and corresponding metric changes — is essential engineering practice to prevent "tuning round trips."

---

## §2 Basic Calibration Procedures

### 2.1 Dark-frame Calibration: Black Level and Noise Floor

**Black Level calibration** is the foundation of all subsequent calibrations. The first step in ISP processing must subtract the sensor's inherent output offset in no-light conditions.

**Calibration method:**
1. Capture 100+ RAW frames under completely shielded (dark) conditions
2. Compute mean and standard deviation for each color channel (Gr, R, B, Gb) separately
3. Black level = median of per-channel means; noise floor (read noise floor) = mean of per-channel standard deviations

**Temperature dependence:** Black level increases with sensor temperature (typically 0.5–2 DN/°C). Calibrate separately at 25°C and 45°C; apply linear interpolation for temperature compensation in the parameter set. Some advanced platforms (e.g., Qualcomm ISP series) support run-time dynamic BLC adjustment based on a temperature sensor.

**Role of OB (Optical Black) pixels:** Modern CMOS sensors typically have light-shielded OB pixel regions outside the active pixel area, allowing real-time black level monitoring and dynamic compensation (OB clamp). During ISP tuning, confirm that the OB pixel region readout path is functional and that the OB mean is within an acceptable range of the offline calibration value (difference < 2 DN).

**Noise model calibration:** Critical for downstream NR algorithms. Capture uniform bright scenes (e.g., a uniform gray card) at multiple analog gain (AG) settings:

- **Fixed Pattern Noise (FPN):** Residual spatial non-uniformity after multi-frame averaging; typically characterized by standard deviation
- **Random noise:** Follows a Poisson-Gaussian mixture model; variance σ² = a·μ + b (a = shot noise coefficient, b = read noise variance = σ_read², μ = pixel mean). Note: some chapters of this handbook write the equivalent formula as σ²(x) = ax + b² where b denotes read noise *standard deviation*; in that notation the two forms are related by b_variance = b_std². In this chapter b always denotes variance (DN²), consistent with the code below.

Fit (μ, σ²) pairs across multiple gain settings to obtain noise model parameters, which serve as prior information for the NR algorithm's intensity parameters.

### 2.2 Uniform Field Calibration: LSC Gain Map

**Lens shading** causes image corners to darken; the typical magnitude ranges from a 20%–60% brightness drop from center to corner, depending on lens design and aperture. LSC calibration requires an accurate uniform light field.

**Calibration equipment:**
- **Integrating sphere:** A spherical cavity with a diffuse-reflective inner coating; output light uniformity > 99%; the highest-precision calibration device, suitable for R&D verification.
- **Flat field box (LED backlight panel):** Lower cost; uniformity > 95%; suitable for high-volume production line calibration. Requires periodic calibration of the box itself using a reference camera.

**Calibration steps:**
1. Under a standard D65 illuminant, aim the lens at the uniform light field with fixed exposure (AE disabled to avoid AE-induced errors)
2. Capture RAW images for R, Gr, Gb, B channels
3. For each channel, compute per-pixel gain compensation using the image center as the reference: `G(x,y) = I_center / I(x,y)`
4. Smooth the gain map (typically via polynomial fitting or 2D Gaussian smoothing) to prevent noise-induced high-frequency gain oscillation
5. Calibrate separately at multiple color temperatures (e.g., 2300 K / 4000 K / 6500 K); interpolate at run time based on estimated color temperature

**Important notes:**
- During calibration, exposure should be in the sensor's linear range (typically **40%–50% of Full Well Capacity, FWC**). Too low → noise degrades gain map precision; too high → non-linearity and pixel crosstalk introduce error. Exceeding 50% FWC increasingly risks entering the soft-saturation region where the sensor response begins to deviate from linearity.
- If AE convergence occurs during calibration, the gain map will include AE oscillation error; recapture is required.

### 2.3 ColorChecker Calibration: AWB + CCM

**ColorChecker Classic** (24-patch standard color chart, X-Rite/Macbeth) is the most widely used AWB/CCM calibration tool in the industry.

**AWB calibration** (white balance base gains):

Under standard illuminants, capture a gray card or the neutral gray patches of the ColorChecker (patches 19–24), extract R/G/B channel ratios, and compute AWB base gains. Standard illuminants used in calibration include:

| Illuminant | CCT | Description |
|-----------|-----|-------------|
| **D65** | ~6500 K | CIE Standard Daylight (overcast daylight); primary calibration reference |
| **D50** | ~5000 K | CIE Horizon daylight; ICC profile reference white point; used for printing/studio calibration |
| **A** | 2856 K | CIE Illuminant A (incandescent/tungsten lamp); standard for warm indoor light calibration |
| **F2** | ~4230 K | CIE Cool White Fluorescent; representative of indoor fluorescent lighting |
| TL84 | ~4100 K | Philips TL84 fluorescent (common in European retail environments) |
| CWF | ~4150 K | Cool White Fluorescent (common in US retail/office environments) |

At minimum, calibrate at D65, D50, A, and F2 to cover the standard illuminant gamut; add TL84/CWF for retail scene coverage.

```
R_gain = G_channel_mean / R_channel_mean
B_gain = G_channel_mean / B_channel_mean
```

Repeat at multiple color temperature points to generate a color-temperature-to-gain look-up table (LUT). This LUT is the basis for AWB algorithm correction gain lookups after estimating color temperature.

**CCM calibration** (color correction matrix):

On a correctly white-balanced image, extract RGB values from the first 18 patches of the ColorChecker; least-squares fit against Macbeth standard XYZ values to solve the 3×3 CCM:

```
[R']   [a11 a12 a13] [R]
[G'] = [a21 a22 a23] [G]
[B']   [a31 a32 a33] [B]
```

Constraints: each row of the CCM sums to 1 (preserving luminance normalization); diagonal elements are positive; off-diagonal element magnitudes typically do not exceed 0.5. **Calibrate CCM separately at multiple color temperatures** (called dual-CCM or multi-CCM strategy); at run time, interpolate the matrix based on AWB-estimated color temperature, accommodating changes in sensor spectral response across illuminants.

### 2.4 AE Target Calibration

**AE calibration** establishes the baseline target luminance that the auto-exposure algorithm drives toward in neutral scenes.

**Standard procedure:**
1. Place an **18% gray card** (Kodak or equivalent) under a **D65** standard illuminant (calibrated lightbox or natural overcast daylight)
2. Disable AE; manually sweep exposure until the RAW pixel mean on the gray card reaches **40%–50% of Full Well Capacity (FWC)**
3. Read the 8-bit output level (after Gamma/Tone Mapping) at this exposure — this becomes the AE target luma setpoint (typically 100–120 / 255 ≈ 39%–47% of output range)
4. Store the corresponding EV (exposure value) as the AE base reference point; all other scene targets are derived relative to this reference

**Rationale:** 18% reflectance gray is the photometric midpoint of the natural luminance distribution. 40%–50% FWC places the sensor in its most linear region while leaving headroom for specular highlights. This calibration also defines the "golden sample" reference exposure — the tuned device whose output serves as the baseline for mass production consistency checks.

**Golden sample:** In production, one or more factory-verified reference devices ("golden samples") are kept as calibration anchors. The golden sample's LSC maps, CCM matrices, and AE target exposure are the authoritative baselines. Per-unit calibration deviations are measured against the golden sample; a typical color accuracy requirement is ΔE00 < 3.0 between the unit under test and the golden sample under D65.

### 2.5 MTF/SFR Resolution Calibration

**MTF (Modulation Transfer Function)** is the standard metric for measuring the spatial resolution of a camera system (lens + sensor + ISP). **SFR (Spatial Frequency Response)** is the slanted-edge MTF measurement method standardized by ISO 12233.

**Calibration steps:**
1. Capture a slanted edge test pattern (10:1 contrast, tilted approximately 5° to avoid pixel grid aliasing)
2. Use Imatest or the open-source sfr tool to extract MTF50 values
3. Measure at image center and four corners (typically a 9-zone grid) to assess field uniformity

**Engineering evaluation metrics:**
- MTF50: Spatial frequency at 50% contrast; unit: lp/ph
- MTF50P: MTF50 normalized by the Nyquist frequency (inverse of pixel pitch); expressed as a percentage
- Typical mass production target: center MTF50 > 0.75 × Nyquist frequency; corner MTF50 > 60% × center value

**Note:** MTF calibration should be performed with NR disabled or set to minimum, to measure the intrinsic resolution of the optics + sensor. The NR/EE impact on MTF50 should be evaluated separately.

---

## §3 Scene-specific Tuning Guide

### 3.1 Scene Classification and Parameter Impact Matrix

The core challenge of scene-specific ISP tuning is that the same parameter set cannot simultaneously optimize all scenes. Identify the critical scenes, define a parameter combination for each, and design a reasonable scene-switching logic.

| Scene | Illuminance range (lux) | Key ISP modules | Primary conflict |
|-------|------------------------|-----------------|-----------------|
| Daylight outdoor | 5000–100000 | EE, color saturation, HDR | Highlight clipping vs. texture detail |
| Indoor artificial light | 100–1000 | AWB, CCM, NR | White balance accuracy, chroma noise |
| Low-light / dim | 1–100 | NR, Demosaic, AE | Noise vs. texture |
| Backlight / high contrast | Span > 5 stops | HDR merge, LTM | Highlight overexposure vs. shadow noise |
| Night long exposure | < 1 | Multi-frame NR, ghost removal | Motion blur vs. noise |

Scene-specific parameter organization typically uses ISO and color temperature as the primary index, with shooting mode (e.g., "portrait mode," "night mode") as a secondary override. Detailed parameter version management strategy is covered in Part 4, Chapter 20.

### 3.2 Daylight Scene Tuning

**Typical lighting conditions:** LV (Light Value) 12–16; sensor operates at minimum analog gain (AG_min).

**AE parameters:**
- Target luma: typically set to 108–120 in 8-bit encoding space (approximately 42%–47%), balancing highlight preservation and shadow detail.
- AE convergence speed: daylight scenes can use faster convergence (converge to ±2% of target luma within 3–5 frames), reducing the over/under exposure transient during scene cuts.

**EE parameters (sharpening):**
- Daylight has rich texture; Edge Enhancement Gain can be set medium-high (1.2–1.5× base gain).
- Control the high-frequency gain amplitude ceiling (Coring Threshold) to prevent graininess appearing in smooth areas (sky, skin).

**Color parameters:**
- Saturation: can be slightly boosted in daylight (+5%–+15%) for a more vibrant look matching consumer preferences.
- Hue rotation: slight hue shifts for green vegetation and blue sky can bring colors closer to human "memory colors."

**Highlight protection:** Enable Highlight Roll-off or the highlight compression segment of the Tone Mapping curve to prevent overexposed areas from clipping to white ("blown highlights").

### 3.3 Indoor Artificial Light Tuning

**Typical lighting conditions:** LV 5–9; fluorescent lamps (TL84, ~4100 K) or warm white LEDs (2700–3500 K), mixed light sources.

**AWB challenges:** Indoor mixed light sources (natural + artificial) are the hardest scenes for AWB algorithms.

Tuning strategies:
- Expand the color temperature convergence range for the Gray World Assumption AWB algorithm; typical setting: 2200 K–7000 K.
- Adjust sampling region weight distribution for white-point candidates to avoid AWB estimate being dominated by large areas of colored objects (e.g., red walls, green plants).
- Tune AWB convergence rate (time constant): indoor light sources change slowly; use slower convergence (10–20 frames) to reduce AWB color jitter.

**NR parameters:**
- Indoor illuminance is moderate; chroma noise (Chroma Noise) is visible at ISO 400–1600, manifesting as colorful speckles.
- Chroma denoise strength can be set medium-high (0.6–0.8 normalized strength).
- Luma NR must preserve texture and avoid over-smoothing skin and fabric detail.

**Anti-banding (AB):**
- Artificial light sources (50/60 Hz AC power) cause horizontal banding in images.
- Exposure time must be locked to integer multiples of the light source cycle: 50 Hz mains → 1/100 s, 1/50 s; 60 Hz mains → 1/120 s, 1/60 s.
- AE in indoor scenes should preferentially adjust gain rather than freely adjusting exposure time to maintain anti-banding conditions.

### 3.4 Low-light Dark Scene Tuning

**Low-light scenes** (< 10 lux) are the most challenging for ISP tuning, with low SNR and high processing difficulty.

**AE strategy:**
- First extend exposure time to the OIS (Optical Image Stabilization) limit (typically 1/15 s–1/4 s, depending on OIS capability and user shake characteristics).
- Then raise analog gain (AG) to the sensor maximum (typically ×16 to ×64); finally enable digital gain (DG).
- Target luma can be slightly lower than in daylight (e.g., drop to 85–95), accepting slight underexposure in exchange for lower noise, to avoid excessive amplification of dark-area noise.

**NR parameter tuning order (low-light golden sequence):**
1. First tune Temporal NR (TNR): uses inter-frame correlation for denoising; highly effective but requires careful motion compensation threshold settings to prevent ghosting in motion regions.
2. Then tune Spatial NR (SNR): spatially-based NR provides fallback coverage for fast-motion regions that TNR cannot handle; tune radius and strength.
3. Finally tune EE: at low-light, EE gain should be significantly reduced (< 0.8× base gain) to prevent noise being sharpened and amplified.

**Typical parameter ranges (comparison):**

| Parameter | Daylight (ISO 100) | Low-light (ISO 3200) |
|-----------|------------------|---------------------|
| Luma NR strength | 0.2–0.4 | 0.7–0.9 |
| Chroma NR strength | 0.3–0.5 | 0.85–0.95 |
| EE gain | 1.2–1.5 | 0.5–0.8 |
| Sharpening radius (pixels) | 1.0–1.5 | 0.8–1.2 |
| TNR inter-frame weight | 0.1–0.2 | 0.5–0.7 |

### 3.5 Backlight / High-contrast Scene Tuning

**Backlight scenes** require the ISP to simultaneously handle bright areas (direct light sources) and dark areas (shadows), with dynamic range requirements reaching 10–14 stops.

**HDR merge parameters:**
- Exposure ratio: typically 8×–16× (3–4 stops); selected automatically by AE control logic based on scene contrast.
- Fusion weight curve: controls the blending ratio of high/low exposure frames at different luminance levels; transition regions must be smooth to avoid seam artifacts.
- Ghost suppression threshold: motion region detection sensitivity. Too high → HDR merge effect incomplete (shadows still noisy); too low → motion ghosting introduced.

**Local Tone Mapping (LTM):**
- Global Tone Mapping (GTM) can only compress dynamic range globally, making images look flat and lacking depth.
- LTM independently enhances contrast in local tiles, preserving highlight detail while boosting shadow detail.
- Tuning focus: trade-off between spatial resolution (Tile Size, typically 64×64 to 256×256 pixels) and strength (LTM Gain Limit, typically capped at 4×–8×). Tiles too small cause blocking artifacts; tiles too large degrade to GTM behavior.

---

## §4 Common Tuning Problems and Diagnostics

### 4.1 Over-denoising vs. Texture Loss

**Symptom:** Image looks like "wax" or "oil painting"; skin/hair/grass/fabric detail disappears; subjective scores drop significantly.

**Root causes:**
- Spatial NR filter radius too large, smoothing high-frequency texture
- NR strength curve does not adaptively decrease with improving SNR in the mid-to-high ISO range
- Both luma and chroma NR strengths are too high; insufficient edge and luma-detail protection

**Diagnostic methods:**
1. Capture a standard texture test chart (e.g., ISO 12233); compare MTF50 with NR on vs. off.
2. MTF50 reduction > 15% generally indicates excessive NR impact on resolution.
3. Compare 400% zoom crops of hair/grass/fabric to assess texture preservation.
4. Use SSIM (Structural Similarity Index) or GMSD (Gradient Magnitude Similarity Deviation) for objective texture preservation evaluation.

**Fix strategy:**
- In the mid-ISO range (ISO 400–1600), reduce NR strength slightly (10%–20% reduction).
- Enable Edge-Aware NR; automatically reduce NR strength in high-gradient (high-contrast edge) regions.
- Adjust NR adaptive weights so smooth regions (sky/skin) and textured regions (hair/fabric) are controlled separately.

### 4.2 Systematic Diagnostics for AWB Color Cast

**AWB color cast** is one of the most common image quality complaints before mass production; the root cause must be distinguished:

| Color cast type | Possible cause | Diagnostic method |
|-----------------|---------------|-------------------|
| Overall warm/cool cast under all illuminants | CCM base matrix bias | ColorChecker ΔE analysis (AWB disabled) |
| Color cast at specific color temperatures | AWB CCT-to-gain curve inaccuracy | Multi-temperature gray card point-by-point test |
| Color cast with dominant colored backgrounds | AWB algorithm polluted by scene dominant color | White-point extraction algorithm exclusion ratio tuning |
| Transient color cast on scene transitions | AWB convergence rate / time constant issue | Video continuous-frame AWB gain curve analysis |
| Color cast in backlight / bright scenes | AE exposure region affects AWB sampling distribution | Analyze exposure state of AWB statistics region |

**Diagnostic flow:**
1. First confirm BLC and LSC are correct (rule out upstream interference).
2. Disable AWB (fixed gains); capture a standard gray card; verify CCM accuracy (ΔE < 2 is acceptable).
3. Enable AWB; under a single standard illuminant, verify convergence accuracy at each color temperature point (CCT error < ±150 K).
4. Introduce complex scenes (mixed light, colored backgrounds); evaluate AWB interference rejection.

### 4.3 Diagnosing Parameter Interactions

Parameter interactions in the ISP pipeline are the core source of tuning complexity. Typical interaction chains:

**EE and NR interaction:** NR reduces image high-frequency energy, but EE subsequently amplifies it; the net outcome depends on the gain product of both. The correct approach is to measure MTF50 after NR, not before, and use that as the EE tuning baseline.

**AE and NR interaction:** AE changes the ISO setting, and NR strength is typically a function of ISO (an ISO-indexed strength curve). The NR strength curve cannot converge until the AE strategy (exposure-gain trade-off curve) is finalized.

**LSC and AWB interaction:** Inaccurate LSC causes AWB color temperature estimation bias at image edges (edge brightness lower than center; color ratios distorted), which then affects AWB convergence. To diagnose, restrict AWB sampling to the image center (disable edge sampling weights) and check whether AWB improves.

**Demosaic and EE interaction:** False color (false chroma) introduced by Demosaic algorithms (e.g., AHDE, Menon) at edges is amplified by EE's high-frequency gain. Assess Demosaic quality (false color suppression) before tuning EE parameters.

**Diagnostic principle:** Use the control variable method — change only one module's parameters at a time; use versioned parameter management (see Part 4, Chapter 20) to record objective metric changes before and after each modification. Each modification should have a complete "change–test–rollback" record.

### 4.4 Systematic Analysis of Overexposure and Underexposure

**Overexposure** manifests as lost highlight detail (blown highlights); common causes:
- AE target luma set too high (> 130/255)
- AE metering zone biased toward shadows (spot metering on a dark background causes subject overexposure)
- HDR merge exposure ratio insufficient; the long-exposure frame itself is already overexposed

**Underexposure** manifests as shadow detail buried in noise; common causes:
- AE target luma set too low (< 90/255)
- AE metering zone biased toward highlights (center-weighted metering in backlight causes subject underexposure)
- Exposure cap set too conservatively; SNR prioritized at the expense of brightness

**Diagnostic tool:** Histogram analysis is the most direct tool. Overexposure appears as right-side clipping; underexposure appears as left-side stacking. During tuning, simultaneously examine the RAW histogram (reflects AE control effect) and the ISP output histogram (reflects Tone Mapping effect).

---

## §5 Mass Production Tuning Validation

### 5.1 Objective Metric Acceptance Criteria

Pre-mass-production objective metric acceptance typically covers the following items (typical mid-to-high-end flagship standard; specifications vary by manufacturer):

| Metric | Measurement method | Typical mass production target |
|--------|-------------------|-------------------------------|
| MTF50 (center) | ISO 12233 slanted edge | > 1100 lp/ph (~0.75 × Nyquist for 12 MP rear camera, consistent with §2.5 guideline) |
| MTF50 (corner mean) | Same | > 75% × center value |
| SNR @ ISO 100 | ISO 15739 uniform gray field | > 42 dB |
| SNR @ ISO 400 | ISO 15739 | > 36 dB |
| SNR @ ISO 1600 | ISO 15739 | > 30 dB |
| SNR @ ISO 6400 | ISO 15739 | > 22 dB |
| ΔE2000 (24-patch mean) | ColorChecker + D65 | < 3.0 |
| ΔE2000 (maximum) | Same | < 6.0 |
| Dynamic Range (DR) | ISO 15739 | > 10.5 stops |
| Lens shading uniformity | LSC residual after correction | < 1% corner-to-center delta |
| White balance error (CCT deviation) | Multi-temperature gray card | < ±200 K |
| AWB stability (video) | Continuous-frame gain std. dev. | < 0.02 (normalized gain) |

**Platform-specific notes:** On the Qualcomm (Snapdragon) ISP platform, the Spectra ISP series has a built-in Chromatix tuning framework with standardized test applications for MTF and SNR measurement. The MTK (MediaTek) Imagiq ISP uses an NDD (Native Device Driver) parameter scheme with similar acceptance procedures. HiSilicon (Kirin) ISP uses a proprietary tuning toolchain. The objective metrics listed above are platform-agnostic universal standards.

**MTK ImagiqSimulator Offline Tuning Workflow**

MTK's ImagiqSimulator + FSViewer toolchain supports offline RAW-based ISP parameter tuning — changes are visible immediately without flashing firmware:

```bash
# Enable RAW/YUV dump on the device (via ADB)
adb shell setprop vendor.debug.camera.p2.dump.filter 3
adb shell setprop vendor.mfll.log_level 3
adb shell setprop vendor.debug.camera.p2.dump 1
# Dump output path on device: /data/vendor/camera_dump/
adb pull /data/vendor/camera_dump/ ./dump/
```

ImagiqSimulator workflow:
1. Load sensor parameter folder → `Tools → ISP REG HEADER File Tool`
2. Select module to tune (e.g., DM for Demosaic, or ALL) → click **Read**
3. Load tuning code → load RAW → simulate → compare output
4. Adjust parameters, click **Run**, observe preview update
5. To write back: select **Write** mode → select module → select scene (photo/video) → select ISO range → Run

**Key Demosaic (DM) tuning parameters:**

| Parameter | Range | Effect |
|-----------|-------|--------|
| `HA STR` | 0–25 | Overall sharpness strength; higher = more detail but more noise |
| `H1` | — | High-frequency detail weight (textured surfaces) |
| `H2`, `H3` | — | Low-frequency weight (flat areas like sky, skin) |

**Tuning order (recommended for new camera bringup):**

```
BPC (bad pixel) → DM (RAW-to-RGB sharpness) → YNR (luma NR) → CNR (chroma NR) → EE (edge detail)
```

Parameter glossary: YNR = Luma Noise Reduction, CNR = Chroma Noise Reduction, EE = Edge Enhancement, OV TH = black fringe suppression threshold, UN TH = white fringe suppression threshold.

### 5.2 Subjective Evaluation Procedure

**MOS (Mean Opinion Score) evaluation procedure:**

1. **Rater selection:** 10–20 non-expert raters; balanced age distribution (18–50); vision corrected to normal.
2. **Display calibration:** P3 color gamut monitor; brightness calibrated to 200 cd/m²; ambient light < 10 lux; white point D65.
3. **Sample design:** Capture 3 photos per scene per device; test 10 representative scenes (daylight, indoor, low-light, backlight, portrait, etc.).
4. **Scoring:** 5-point scale (1=poor, 2=fair, 3=average, 4=good, 5=excellent); 30-second rest between test groups.
5. **Statistical processing:** Remove outliers (scores deviating > 2σ from the mean); compute MOS ± 95% confidence interval.

**ABX blind test** for detecting whether subtle tuning differences are perceptible:
- Group A: Current parameter version
- Group B: New parameter version (a specific module's parameters changed)
- Group X: Randomly either A or B (rater does not know which)
- Rater judges "is X closer to A or B?"; tally correct rate.
- Correct rate > 75% indicates that the difference between the two versions is perceptibly significant (statistically significant).

**Common pitfall:** Order effect — raters tend to score the first image more leniently; randomize test order and include practice trials for calibration.

### 5.3 Multi-unit Consistency Cpk Control

In mass production, parameter consistency is measured using **Cpk (Process Capability Index)**, ensuring that the image quality of different batches and units stays within specification.

**Cpk definition:**
```
Cpk = min( (USL - μ) / (3σ),  (μ - LSL) / (3σ) )
```
where USL/LSL are the Upper/Lower Specification Limits, μ is the sample mean, and σ is the sample standard deviation.

**Mass production requirements:**
- Cpk > 1.33 indicates adequate process capability (6σ quality target: Cpk > 1.67)
- Critical image quality items (e.g., MTF50, ΔE2000): Cpk > 1.33
- Secondary items (e.g., hue deviation, saturation deviation): Cpk > 1.0

**Variation source analysis:** When Cpk < 1.0, identify variation sources in the manufacturing process:
- **Lens assembly deviation** (optical axis tilt): causes increased MTF field non-uniformity
- **Sensor batch variation** (sensor lot variation): black level and noise floor differences across batches
- **Factory calibration precision:** repeatability of LSC, AWB calibration procedures

When variation primarily originates from module-level differences, enable **per-unit calibration** — separately calibrating LSC gain maps and AWB base gains for each unit, rather than using a unified mass production parameter set.

---

## §6 Code Examples

### 6.1 AWB Color Temperature-to-Gain Curve Fitting

```python
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# Calibration data: color temperature (K) and corresponding R_gain / B_gain
cct_points = np.array([2300, 2700, 3200, 4000, 5000, 6500, 7500])
r_gains    = np.array([2.45, 2.20, 1.98, 1.72, 1.52, 1.35, 1.28])
b_gains    = np.array([0.82, 0.88, 0.95, 1.05, 1.18, 1.38, 1.52])

# Fit using a rational function: gain = (a + b*T) / (c + d*T)
# Rational functions outperform simple polynomials over wide CCT ranges
def rational_fit(T, a, b, c, d):
    return (a + b * T) / (c + d * T)

# Fit R_gain curve
popt_r, _ = curve_fit(rational_fit, cct_points, r_gains,
                      p0=[100, 0, 50, 0.01], maxfev=5000)
# Fit B_gain curve
popt_b, _ = curve_fit(rational_fit, cct_points, b_gains,
                      p0=[0.1, 0.0002, 1, -0.00005], maxfev=5000)

# Generate continuous curve for run-time interpolation
T_range = np.linspace(2000, 8000, 1000)
r_fitted = rational_fit(T_range, *popt_r)
b_fitted = rational_fit(T_range, *popt_b)

# Plot
fig, axes = plt.subplots(1, 2, figsize=(12, 4))

axes[0].scatter(cct_points, r_gains, color='red', s=50, zorder=5, label='Calibration points')
axes[0].plot(T_range, r_fitted, 'r-', linewidth=2, label='Fitted curve')
axes[0].set_xlabel('Color temperature (K)')
axes[0].set_ylabel('R_gain')
axes[0].set_title('AWB R_gain vs. Color Temperature')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

axes[1].scatter(cct_points, b_gains, color='blue', s=50, zorder=5, label='Calibration points')
axes[1].plot(T_range, b_fitted, 'b-', linewidth=2, label='Fitted curve')
axes[1].set_xlabel('Color temperature (K)')
axes[1].set_ylabel('B_gain')
axes[1].set_title('AWB B_gain vs. Color Temperature')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('awb_gain_curve.png', dpi=150, bbox_inches='tight')
plt.show()

# Gain query function for a given color temperature
def get_awb_gains(cct, popt_r, popt_b, cct_min=2000, cct_max=8000):
    """Query AWB gains for a given estimated CCT (G_gain normalized to 1.0)."""
    cct = np.clip(cct, cct_min, cct_max)
    r = rational_fit(cct, *popt_r)
    b = rational_fit(cct, *popt_b)
    return float(r), 1.0, float(b)

# Example output
print("=== AWB gain query examples ===")
for test_cct in [2700, 4000, 5500, 6500]:
    rg, gg, bg = get_awb_gains(test_cct, popt_r, popt_b)
    print(f"CCT={test_cct}K: R_gain={rg:.3f}, G_gain={gg:.3f}, B_gain={bg:.3f}")
```

### 6.2 SNR-NR Strength Trade-off Curve Generation

```python
import numpy as np
import matplotlib.pyplot as plt

# Noise model parameters (from sensor calibration)
# Poisson-Gaussian mixture model: sigma^2 = shot_noise_coeff * mean + read_noise_var
SHOT_NOISE_COEFF = 0.012   # Shot noise coefficient (from calibration)
READ_NOISE_VAR   = 4.0     # Read noise variance (DN^2)

# ISO list and corresponding effective noise amplification factors (simplified linear model)
ISO_LIST     = np.array([100, 200, 400, 800, 1600, 3200, 6400])
NOISE_FACTOR = ISO_LIST / 100.0   # Normalized gain multiplier

def compute_snr(signal_dn, gain_factor, shot_coeff, read_var):
    """Compute SNR (dB) at a given signal level."""
    sigma2 = shot_coeff * signal_dn * gain_factor + read_var * (gain_factor ** 2)
    sigma  = np.sqrt(sigma2)
    snr    = 20.0 * np.log10(signal_dn / (sigma + 1e-8))
    return snr

# Compute SNR at each ISO for a uniform gray field (50% full well, ~128 DN @ 8 bit)
SIGNAL_LEVEL = 128.0
snr_values = np.array([
    compute_snr(SIGNAL_LEVEL, gf, SHOT_NOISE_COEFF, READ_NOISE_VAR)
    for gf in NOISE_FACTOR
])

# Recommended NR strength curve: lower SNR → higher NR strength (sigmoid mapping)
def nr_strength_from_snr(snr_db, snr_pivot=38.0, k=0.4):
    """Map SNR (dB) to recommended NR strength [0, 1]."""
    return 1.0 / (1.0 + np.exp(k * (snr_db - snr_pivot)))

nr_luma_strengths   = nr_strength_from_snr(snr_values)
nr_chroma_strengths = np.minimum(nr_luma_strengths * 1.1, 1.0)  # Chroma NR slightly stronger

# Plot
fig, axes = plt.subplots(1, 3, figsize=(15, 4))

# (1) SNR vs. ISO
axes[0].semilogx(ISO_LIST, snr_values, 'go-', linewidth=2, markersize=6)
axes[0].set_xlabel('ISO gain')
axes[0].set_ylabel('SNR (dB)')
axes[0].set_title('SNR vs. ISO')
axes[0].set_xticks(ISO_LIST)
axes[0].set_xticklabels([str(i) for i in ISO_LIST])
axes[0].grid(True, alpha=0.3)
for iso, snr in zip(ISO_LIST, snr_values):
    axes[0].annotate(f'{snr:.1f}', (iso, snr), textcoords='offset points',
                     xytext=(0, 8), ha='center', fontsize=8)

# (2) Recommended NR strength vs. ISO
axes[1].semilogx(ISO_LIST, nr_luma_strengths, 'bs-', linewidth=2,
                 markersize=6, label='Luma NR')
axes[1].semilogx(ISO_LIST, nr_chroma_strengths, 'r^--', linewidth=2,
                 markersize=6, label='Chroma NR')
axes[1].set_xlabel('ISO gain')
axes[1].set_ylabel('NR strength [0, 1]')
axes[1].set_title('Recommended NR Strength vs. ISO')
axes[1].set_ylim(0, 1.1)
axes[1].set_xticks(ISO_LIST)
axes[1].set_xticklabels([str(i) for i in ISO_LIST])
axes[1].axhline(0.5, color='gray', linestyle=':', alpha=0.5, label='Medium strength baseline')
axes[1].legend(fontsize=8)
axes[1].grid(True, alpha=0.3)

# (3) NR strength vs. SNR (mapping curve)
snr_range = np.linspace(20, 50, 200)
nr_range  = nr_strength_from_snr(snr_range)
axes[2].plot(snr_range, nr_range, 'k-', linewidth=2, label='Mapping curve')
axes[2].scatter(snr_values, nr_luma_strengths, color='blue', s=60,
                zorder=5, label='Luma NR calibration points')
axes[2].set_xlabel('SNR (dB)')
axes[2].set_ylabel('NR strength')
axes[2].set_title('NR Strength vs. SNR (mapping)')
axes[2].invert_xaxis()   # Low-SNR (high-ISO) on the right
axes[2].grid(True, alpha=0.3)
axes[2].legend(fontsize=8)

plt.tight_layout()
plt.savefig('snr_nr_tradeoff.png', dpi=150, bbox_inches='tight')
plt.show()

# Output recommended NR parameter table
print("\n=== Recommended NR Strength Parameter Table ===")
print(f"{'ISO':>8} {'SNR(dB)':>10} {'NR_Luma':>10} {'NR_Chroma':>12}")
print("-" * 45)
for iso, snr, nr_l, nr_c in zip(ISO_LIST, snr_values,
                                  nr_luma_strengths, nr_chroma_strengths):
    print(f"{iso:>8} {snr:>10.1f} {nr_l:>10.3f} {nr_c:>12.3f}")
```

### 6.3 ColorChecker ΔE2000 Automated Measurement

```python
import numpy as np

# D65 standard Lab values for the first 18 ColorChecker Classic patches
# (source: X-Rite official data)
CC_LAB_D65 = np.array([
    [37.54, 14.37, 14.92],   # 1  Dark skin
    [65.71, 18.13, 17.81],   # 2  Light skin
    [49.93, -4.88, -21.93],  # 3  Blue sky
    [43.14, -13.10, 21.91],  # 4  Foliage
    [55.11,  8.84, -25.40],  # 5  Blue flower
    [70.72, -33.40, -0.20],  # 6  Bluish green
    [62.66, 36.07, 57.10],   # 7  Orange
    [40.02, 10.41, -45.96],  # 8  Purplish blue
    [51.12, 48.24, 16.25],   # 9  Moderate red
    [30.33, 22.98, -20.87],  # 10 Purple
    [72.53, -23.71, 57.26],  # 11 Yellow-green
    [71.94, 19.36, 67.86],   # 12 Orange-yellow
    [28.78, 14.18, -50.30],  # 13 Blue
    [55.26, -38.34, 31.37],  # 14 Green
    [42.10, 53.38, 28.19],   # 15 Red
    [81.73,  4.04, 79.82],   # 16 Yellow
    [51.94, 49.99, -14.57],  # 17 Magenta
    [51.04, -28.63, -28.64], # 18 Cyan
])

def delta_e_2000(lab1, lab2):
    """
    Compute CIE ΔE2000 color difference between two Lab colors.
    Reference: Sharma et al., Color Research & Application, 2005.
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    # Step 1: Compute C'ab and a'
    C1 = np.sqrt(a1**2 + b1**2)
    C2 = np.sqrt(a2**2 + b2**2)
    C_avg7 = ((C1 + C2) / 2.0) ** 7
    G  = 0.5 * (1.0 - np.sqrt(C_avg7 / (C_avg7 + 25.0**7)))
    a1p = a1 * (1.0 + G)
    a2p = a2 * (1.0 + G)
    C1p = np.sqrt(a1p**2 + b1**2)
    C2p = np.sqrt(a2p**2 + b2**2)

    # Step 2: h' (hue angle)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0

    # Step 3: Differences
    dLp = L2 - L1
    dCp = C2p - C1p
    dh_diff = h2p - h1p
    if abs(dh_diff) <= 180.0:
        dhp = dh_diff
    elif dh_diff > 180.0:
        dhp = dh_diff - 360.0
    else:
        dhp = dh_diff + 360.0
    dHp = 2.0 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp / 2.0))

    # Step 4: Weighting functions
    Lp_avg  = (L1 + L2) / 2.0
    Cp_avg  = (C1p + C2p) / 2.0
    dh_abs  = abs(h1p - h2p)
    if dh_abs <= 180.0:
        Hp_avg = (h1p + h2p) / 2.0
    elif h1p + h2p < 360.0:
        Hp_avg = (h1p + h2p + 360.0) / 2.0
    else:
        Hp_avg = (h1p + h2p - 360.0) / 2.0

    T  = (1.0
          - 0.17 * np.cos(np.radians(Hp_avg - 30.0))
          + 0.24 * np.cos(np.radians(2.0 * Hp_avg))
          + 0.32 * np.cos(np.radians(3.0 * Hp_avg + 6.0))
          - 0.20 * np.cos(np.radians(4.0 * Hp_avg - 63.0)))

    SL  = 1.0 + 0.015 * (Lp_avg - 50.0)**2 / np.sqrt(20.0 + (Lp_avg - 50.0)**2)
    SC  = 1.0 + 0.045 * Cp_avg
    SH  = 1.0 + 0.015 * Cp_avg * T

    Cp_avg7 = Cp_avg ** 7
    RC  = 2.0 * np.sqrt(Cp_avg7 / (Cp_avg7 + 25.0**7))
    dth = 30.0 * np.exp(-((Hp_avg - 275.0) / 25.0)**2)
    RT  = -np.sin(np.radians(2.0 * dth)) * RC

    dE = np.sqrt(
        (dLp / SL)**2 +
        (dCp / SC)**2 +
        (dHp / SH)**2 +
        RT * (dCp / SC) * (dHp / SH)
    )
    return dE

def evaluate_ccm_accuracy(measured_lab, reference_lab=CC_LAB_D65, verbose=True):
    """
    Batch-evaluate CCM accuracy; output per-patch ΔE2000 statistics.

    Args:
        measured_lab: shape (N, 3), Lab values from the camera under test
        reference_lab: shape (N, 3), standard reference Lab values

    Returns:
        de_array: shape (N,), ΔE2000 per patch
    """
    n = len(reference_lab)
    de_values = np.array([
        delta_e_2000(measured_lab[i], reference_lab[i])
        for i in range(n)
    ])
    if verbose:
        print(f"ΔE2000 mean:            {de_values.mean():.2f}")
        print(f"ΔE2000 maximum:         {de_values.max():.2f} (patch {de_values.argmax()+1})")
        print(f"Patches with ΔE > 5:   {(de_values > 5).sum()} / {n}")
        print(f"Patches with ΔE > 3:   {(de_values > 3).sum()} / {n}")
        if de_values.mean() < 3.0:
            print(">>> Result: PASS mass production acceptance (mean < 3.0)")
        else:
            print(">>> Result: FAIL — CCM recalibration required")
    return de_values

# Example: simulate measured values (add random offset to ground truth, simulating real camera output)
np.random.seed(42)
simulated_measurement = CC_LAB_D65 + np.random.randn(*CC_LAB_D65.shape) * 1.8

print("=== CCM Accuracy Evaluation ===")
de_results = evaluate_ccm_accuracy(simulated_measurement)
```

---

## §7 References

1. **ISO 12233:2017** — Photography — Electronic still picture imaging — Resolution and spatial frequency responses. ISO, 2017.

2. **ISO 15739:2023** — Photography — Electronic still picture imaging — Noise measurements. ISO, 2023.

3. **Imatest Documentation** — MTF, SFR, and Noise Measurement Methodology. https://www.imatest.com/docs/ (accessed 2024).

4. **Nakamura, J. (2006)**. *Image Sensors and Signal Processing for Digital Still Cameras*. CRC Press.

5. **Lukac, R., & Plataniotis, K. N. (2006)**. *Color Image Processing: Methods and Applications*. CRC Press.

6. **Ohta, N., & Robertson, A. (2005)**. *Colorimetry: Fundamentals and Applications*. Wiley.

7. **Sharma, G., Wu, W., & Dalal, E. N. (2005)**. The CIEDE2000 color-difference formula: Implementation notes, supplementary test data, and mathematical observations. *Color Research & Application*, 30(1), 21–30.

8. **Healey, G. E., & Kondepudy, R. (1994)**. Radiometric CCD camera calibration and noise estimation. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 16(3), 267–276.

9. **Hasinoff, S. W., et al. (2016)**. Burst photography for high dynamic range and low-light imaging on mobile cameras. *ACM Transactions on Graphics (SIGGRAPH Asia 2016)*, 35(6), Article 192.

10. **Liu, C., Szeliski, R., et al. (2008)**. Automatic estimation and removal of noise from a single image. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 30(2), 299–314.

11. **Kang, S. B., et al. (2003)**. High dynamic range video. *ACM Transactions on Graphics (SIGGRAPH 2003)*, 22(3), 319–325.

12. **Reinhard, E., et al. (2010)**. *High Dynamic Range Imaging: Acquisition, Display, and Image-Based Lighting*, 2nd ed. Morgan Kaufmann.

---

## §8 Glossary

| Term | Full Name | Notes |
|------|-----------|-------|
| EVT | Engineering Verification Test | Early prototype verification phase |
| DVT | Design Verification Test | Primary tuning phase |
| PVT | Production Verification Test | Multi-unit consistency verification phase |
| MP | Mass Production | Mass production phase |
| BLC | Black Level Correction | Subtracts sensor dark-field bias offset |
| PDC / PDPC | Pixel Defect Correction | Repairs dead and hot pixels |
| LSC | Lens Shading Correction | Compensates corner brightness falloff |
| AWB | Auto White Balance | Automatic white balance |
| CCM | Color Correction Matrix | 3×3 linear color transform |
| NR | Noise Reduction | Noise reduction processing |
| TNR | Temporal Noise Reduction | Uses inter-frame correlation |
| EE | Edge Enhancement | Edge enhancement (sharpening) |
| AE | Auto Exposure | Automatic exposure |
| MTF | Modulation Transfer Function | Measures spatial resolution |
| MTF50 | MTF at 50% contrast | Spatial frequency at 50% modulation |
| SFR | Spatial Frequency Response | Slanted-edge MTF measurement |
| SNR | Signal-to-Noise Ratio | Unit: dB |
| DR | Dynamic Range | Unit: stops or dB |
| ΔE2000 | CIEDE2000 Color Difference | Perceptually linearized color difference |
| MOS | Mean Opinion Score | Mean perceptual quality score |
| ACR | Absolute Category Rating | 5-point subjective rating scale |
| Cpk | Process Capability Index | Measures mass production consistency |
| LTM | Local Tone Mapping | Local tone mapping |
| GTM | Global Tone Mapping | Global tone mapping |
| OB | Optical Black | Light-shielded reference pixels on the sensor |
| FPN | Fixed Pattern Noise | Sensor spatial non-uniformity |
| CCT | Correlated Color Temperature | Unit: K |
| LUT | Look-Up Table | Look-up table |
| AG | Analog Gain | In-sensor amplification |
| DG | Digital Gain | ISP digital-domain amplification |
| LV | Light Value | Logarithmic illuminance representation |
| OIS | Optical Image Stabilization | Lens-shift-based stabilization |
| AB | Anti-Banding | Exposure time synchronized to AC power frequency |
| FWC | Full Well Capacity | Maximum charge capacity of a pixel |
| Per-unit calibration | Per-Unit Calibration | Individual calibration performed on each unit |

---

*End of chapter.*

*Next chapter: Part 4, Chapter 18 — Camera HAL Architecture (Camera Hardware Abstraction Layer Architecture)*
*Related chapters: Part 4, Chapter 20 (ISP Multi-scene Parameter Version Management); Part 2, Chapter 9 (Lens Shading Correction); Part 4, Chapter 1 (3A Control System)*
