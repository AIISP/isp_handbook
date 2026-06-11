# Part 2, Chapter 30: Full ISP Pipeline Calibration and Validation Methodology

> **Scope:** This chapter provides a systematic methodology for full ISP pipeline calibration — from the sensor dark field to the color science calibration chain, automated validation test suites, and calibration data version management and mass-production release processes. It complements Volume 4, Chapter 17 (Tuning Workflow): this chapter focuses on calibration accuracy and repeatability, while the tuning chapter focuses on scene image quality convergence.
> **Prerequisites:** Volume 2, Chapter 1 (BLC); Volume 2, Chapter 9 (LSC); Volume 2, Chapter 6 (AWB); Volume 2, Chapter 7 (CCM)
> **Target readers:** ISP calibration engineers, algorithm engineers

---

## Table of Contents

1. [Calibration Chain Theory](#1-calibration-chain-theory)
2. [Per-Module Calibration Methods](#2-per-module-calibration-methods)
3. [Automated Calibration Validation](#3-automated-calibration-validation)
4. [Common Calibration Failure Modes](#4-common-calibration-failure-modes)
5. [Calibration Accuracy Evaluation Standards](#5-calibration-accuracy-evaluation-standards)
6. [Code Example](#6-code-example)
7. [References](#references)
8. [Glossary](#glossary)

---

## 1 Calibration Chain Theory

### 1.1 Linearity Assumption in Radiometric Calibration

The starting point of full ISP pipeline calibration is **radiometric calibration (辐射标定)**: establishing an accurate quantitative relationship between the sensor's digital output value (DN, Digital Number) and the scene radiance.

The core assumption of radiometric calibration is sensor response **linearity**:

$$DN(E) = G \cdot E \cdot T_{\text{exp}} + \text{BLC} + n$$

where:
- $E$: incident irradiance (W/m²)
- $G$: sensor gain (includes conversion gain $k_{\text{ADC}}$ and optical gain)
- $T_{\text{exp}}$: exposure time (s)
- $\text{BLC}$: black level (Black Level Clamp; dark current + ADC offset)
- $n$: noise (shot noise + read noise)

**Verifying the linearity assumption:** Adjust a uniform light source's irradiance (or exposure time) and record the DN response to plot the response curve. An ideal sensor responds linearly. Real sensors deviate at:
- Low end (< 5 % full scale): ADC non-linearity and FPN interference
- High end (> 90 % full scale): approaching saturation; response flattens (compression)

Linearity deviation is typically described by **INL (Integral Non-Linearity)** or **DNL (Differential Non-Linearity)**. High-quality scientific cameras require INL < 1 % of full scale; consumer image sensors typically < 3 %.

### 1.2 Color Science Calibration Chain

The complete color science calibration chain maps sensor output to the standard color space (sRGB) through the following sequential steps:

```
Light source spectral power × sensor spectral response → Sensor Raw RGB
         ↓ BLC compensation
         ↓ DPC defect pixel correction
         ↓ LSC lens shading correction
         ↓ Demosaic (not a calibration module, but affects downstream calibration quality)
         ↓ AWB white balance gain
         ↓ CCM color correction matrix
         ↓ Gamma / tone mapping
         ↓
      sRGB output (standard color space)
```

**Sensor Spectral Response (SSR, 传感器光谱响应):** Sensor sensitivity to light of different wavelengths. The R/G/B channel SSR of a consumer image sensor deviates significantly from the CIE 1931 XYZ color matching functions; the role of CCM is to approximately compensate for this deviation in the linear light domain.

**Sripathi & Hirakawa (2014) and others have shown** that for a sensor with arbitrary SSR, an exact 3×3 CCM exists if and only if the sensor's SSR is a linear transformation of the CIE XYZ functions (i.e., satisfies the "Luther-Ives condition"). Real sensor Luther-Ives deviation means no single CCM can be simultaneously accurate under different illuminants — this is the theoretical basis for multi-illuminant calibration (multiple CCMs).

### 1.3 Calibration Error Propagation Analysis

Calibration errors from each module propagate along the pipeline and ultimately manifest as output color error ΔE. Qualitative analysis:

| Calibration Error Source | Effect on Output |
|--------------------------|-----------------|
| BLC calibration error 1 DN | At low light / high ISO, color deviation ΔE00 ≈ 0.5–2.0 |
| LSC non-uniformity 5% | Uneven color at image edges, ΔE00 ≈ 1.0–3.0 |
| AWB gain error 2% | Global color cast, ΔE00 ≈ 2.0–5.0 |
| CCM minimization ΔE deviation | Directly reflected as ColorChecker ΔE |

**Separability of calibration chain errors:** In first-order approximation, errors from different modules add independently (RSS principle). However, BLC errors are amplified by the non-linear Gamma, and LSC errors affect the weighting of AWB statistics regions; actual error propagation has some coupling. Therefore, calibration order must strictly follow the ISP pipeline order (BLC → DPC → LSC → AWB → CCM) to prevent downstream calibration errors from contaminating upstream calibration baselines.

---

## 2 Per-Module Calibration Methods

### 2.1 BLC (Black Level Correction) Calibration

**Goal:** Determine the average output value of each sensor channel under zero-illumination conditions (black level), for subtraction from the dark bias of RAW images.

**Method 1: Dark Frame Method**

1. Cover the lens (complete light exclusion); capture $N \geq 100$ frames (fixed exposure time, ISO)
2. Compute the multi-frame mean for each of the four Bayer channels (R/Gr/Gb/B):
   $$\text{BLC}_{\text{ch}} = \frac{1}{N \cdot (H/2) \cdot (W/2)} \sum_{\text{frames}} \sum_{(r,c) \in \text{ch}} DN(r, c)$$
3. Compute standard deviation $\sigma_{\text{ch}}$ as a BLC accuracy indicator (a measure of shot noise + read noise)

**Method 2: OB Pixel Method (Optical Black Pixel Method)**

Sensors typically reserve optically black pixels (OB, Optical Black) at the edge, which are completely shielded by metal:
1. Read OB region pixel values; compute the mean for each channel
2. The OB method can dynamically update BLC in real time without covering the lens, achieving higher accuracy

**Multi-temperature/multi-ISO calibration:** See Volume 2, Chapter 29 (Automotive ISP); the emphasis here is on the completeness of the calibration matrix:
- Temperature axis: one point every 10 °C (automotive), one point every 25 °C (consumer)
- ISO axis: nominal ISO values: 100, 200, 400, 800, 1600, 3200 (covering the actual usage range)

**BLC calibration accuracy requirements:**
- Consumer cameras: BLC error < 1 DN (12-bit system)
- Automotive cameras: < 0.5 DN (high-temperature end)

### 2.2 DPC (Defect Pixel Correction) Calibration

**Goal:** Build a sensor defect pixel map (Defect Pixel Map) for runtime defect interpolation repair.

**Defect pixel types:**
- **Hot Pixel (热像素):** In dark field, output value significantly higher than neighborhood mean (typically > 3σ); caused by pixel defects that produce abnormally high dark current
- **Cold Pixel (冷像素):** In a uniform light field, output value significantly lower than neighborhood mean (typically < 3σ); caused by abnormally low quantum efficiency
- **Stuck Pixel (粘滞像素):** Output fixed at a constant value (always bright or always dark)
- **Cluster Defect (簇缺陷):** Multiple adjacent pixels that are simultaneously defective

**Dark-field detection procedure:**
1. Block light; compute a multi-frame mean dark-field image
2. For each pixel, compute local (5×5 neighborhood) statistics: if $DN_{\text{pixel}} > \mu_{\text{neighbor}} + K\sigma$, mark as hot pixel (typical $K = 5$–$10$)
3. Bright-field detection: capture a uniform integrating-sphere light field image; detect cold pixels with low response

**Factory Defect Map:** Store calibration results as a defect pixel coordinate list (typically in compressed format); write to sensor EEPROM or ISP NVM (Non-Volatile Memory).

**On-the-fly DPC:** The factory defect map covers static defects; new hot pixels may appear during high-temperature use. ISP must detect them in real time at runtime. This is typically done by comparing adjacent pixel differences (absolute difference > threshold) per row in the current frame for dynamic identification and repair.

### 2.3 LSC (Lens Shading Correction) Calibration

**Goal:** Build a gain compensation table to eliminate spatial luminance non-uniformity caused by lens vignetting and pixel micro-lens offset (chief ray angle dependence).

**Integrating sphere uniform light field calibration:**
1. Aim the camera at the output port of an integrating sphere (积分球); the sphere provides extremely high spatial uniformity (> 99 %) diffuse light
2. Adjust integrating sphere brightness or exposure time so that the sensor center pixel signal falls at **40 %–60 % of Full Well Capacity (FWC)**; this avoids both saturation clipping and low-SNR noise floor effects
3. Capture multiple RAW frames; compute the spatial uniformity map $\text{Gain}(r, c)$ for each channel

$$\text{LSC\_Gain}(r, c) = \frac{\mu_{\text{center}}}{\text{RAW}(r, c)}$$

3. Typically downsample the gain map to a sparse grid (e.g., 17×17 or 33×33); store grid node values; at runtime, bilinearly interpolate to obtain the full gain map

**Smoothness constraint:** To avoid overfitting noise, the LSC gain grid must satisfy a smoothness constraint (adjacent node gain difference < 5 %). This can be achieved via 2D smoothing or least-squares smooth fitting.

**Multi-illuminant LSC:** Different light sources (different CRI, different spectral distributions) produce slightly different lens vignetting behavior (due to interaction between sensor spectral response and illuminant spectrum). High-accuracy calibration requires separate LSC gain tables under multiple light sources. At runtime, select or interpolate the appropriate LSC gain table based on the AWB-detected current illuminant.

**Edge gain limit:** For fisheye or ultra-wide-angle lenses, LSC gain at the edge can be as high as 5–8×. Excessively high gain significantly amplifies edge noise; this requires joint design with the denoising algorithm. Typically, a maximum gain upper limit is set (e.g., 4×), accepting a small residual shadow at the edge.

### 2.4 AWB (Auto White Balance) Calibration

**Goal:** Establish white balance gains (R_gain, G_gain, B_gain) under standard illuminants, and the interpolation curve from color temperature to gains (Planckian Locus).

**Calibration illuminants:**
- **D65** (daylight, 6504 K): CIE standard illuminant D65, sRGB white point reference
- **D50** (5003 K): Photography studio light, slightly warmer
- **D75** (7500 K): Overcast daylight
- **Illuminant A** (Incandescent, 2856 K): Incandescent lamp, reddish-orange
- **TL84** (fluorescent, 3800 K)
- **CWF (Cool White Fluorescent, 4150 K)**

**Calibration procedure:**
1. Place the camera in front of an integrating sphere or the white patch of a Macbeth color chart; capture RAW images under each illuminant
2. Compute R, G, B channel means directly in the RAW domain (before demosaicing) for the gray region (ColorChecker white/gray patches); this avoids color interpolation errors from demosaic polluting the white balance estimation
3. Compute gains under the gray world assumption: $R_{\text{gain}} = G_{\text{mean}} / R_{\text{mean}}$, $B_{\text{gain}} = G_{\text{mean}} / B_{\text{mean}}$
4. Each illuminant produces a (color temperature, R_gain, B_gain) triplet; fit the gain-vs.-color-temperature curve from multiple triplets

**CCT interpolation curve:** Along the Planckian Locus (black-body radiation trajectory), fit the AWB gains at different color temperatures using a polynomial or piecewise-linear function. At runtime, interpolate from the estimated real-time color temperature to obtain the current AWB gains.

### 2.5 CCM (Color Correction Matrix) Calibration

**Goal:** Determine the 3×3 matrix that maps sensor RAW RGB (after white balance) to the standard color space (XYZ or sRGB), minimizing the color reproduction error for a standard color target.

The **ColorChecker 24-patch** (X-Rite Macbeth ColorChecker) is the industry-standard calibration tool, containing 24 patches with known standard colors.

**Calibration procedure:**
1. Photograph the ColorChecker under standard illuminants (D65/A); ensure uniform illumination of the color target (avoid local shadows)
2. Extract RAW mean values for each of the 24 patches (after BLC/LSC/AWB), obtaining 24 sensor RGB vectors
3. Obtain standard XYZ values for the 24 ColorChecker patches (from X-Rite official data, or measured under the standard illuminant)
4. Convert XYZ to linear sRGB (via sRGB primaries matrix)
5. Solve for the 3×3 CCM using least squares:

$$\min_{M} \sum_{i=1}^{24} w_i \cdot \Delta E_{00}\left(M \cdot \mathbf{r}_i, \mathbf{s}_i\right)$$

where $\mathbf{r}_i$ is the sensor RGB, $\mathbf{s}_i$ is the target sRGB, and $w_i$ is the weight for each patch.

**Weighted least squares vs. uniform least squares:**

- **Uniform weights:** Equal optimization over all 24 patches; minimizes overall ΔE
- **Weighted:** Higher weights for neutral patches (white/gray/black) to prioritize grayscale accuracy (white balance perception); higher weights for skin-tone patches to prioritize facial aesthetics

**Multi-illuminant CCM:** CCM accuracy depends on the illuminant. Typically at least two sets are calibrated: D65 daylight CCM and Illuminant A CCM. At runtime, linearly interpolate between the two CCMs based on the AWB-detected color temperature:

$$M_{\text{current}} = \alpha \cdot M_{\text{D65}} + (1-\alpha) \cdot M_{\text{A}}$$

where $\alpha$ is determined by color temperature ($\alpha = 1$ for D65, $\alpha = 0$ for Illuminant A).

### 2.6 Gamma / Tone Mapping LUT Calibration

**Goal:** Build a tone-mapping lookup table (Tone Mapping LUT) that maps the linear light domain to a perceptually uniform space (sRGB Gamma 2.2 / Rec.709), while also correcting the display transfer function (EOTF, Electro-Optical Transfer Function).

**Grayscale wedge input-output linearization:**
1. Photograph a grayscale test chart (OECF test chart, with steps uniformly covering 0 %–100 % reflectance)
2. Measure the RAW input value and target sRGB output value for each grayscale step
3. Fit a piecewise linear or spline curve; generate a 256-point (8-bit) or 4096-point (12-bit) LUT

---

## 3 Automated Calibration Validation

### 3.1 Numerical Validation of Calibration Results

Establish an automated Calibration Verification Test Suite that quantitatively validates each calibration result:

**BLC validation:**
- Dark-field image mean after BLC subtraction should be close to 0 (deviation < ±1 DN)
- BLC error for each of the four channels (R/Gr/Gb/B) individually < 0.5 DN
- Gr/Gb channel BLC difference (Green Imbalance) < 0.5 DN

**LSC validation:**
- Spatial non-uniformity (Spatial Non-Uniformity) of the gain-compensated image < 1 %
- Non-uniformity defined as: $(DN_{\max} - DN_{\min}) / DN_{\text{center}} \times 100\%$
- Maximum gain table value < maximum allowed gain upper limit

**AWB validation:**
- Color deviation (ΔE00) of a gray card under standard illuminant < 1.0
- After AWB convergence, color cast ratio (R_gain × B_gain deviation ratio) < 5 %

**CCM validation:**
- ColorChecker 24-patch mean ΔE00 < 2.0 (D65), < 3.0 (Illuminant A)
- No individual patch ΔE00 > 5.0 (single-patch over-spec alert)
- Neutral patches (patches 19–24) ΔE00 < 1.5 (stricter grayscale accuracy requirement)

### 3.2 Image-Level Regression Testing

Build a **Golden Reference Image Set** of standard scenes; automatically compare the current calibration version against the baseline:

**Regression testing procedure:**
1. Capture test images in a strictly controlled test environment (fixed illuminant, fixed scene, fixed exposure)
2. Compute full-image PSNR (Peak Signal-to-Noise Ratio) and SSIM (Structural Similarity Index) against historical baseline images
3. Compute ΔE00 separately in specific regions of interest (ROI) such as neutral gray patches, skin-tone patches, and highly saturated patches

**PSNR baseline threshold:** A PSNR decrease of > 0.5 dB relative to the previous version triggers an alert requiring manual review.

**ΔE00 baseline threshold:** A ΔE00 change of > 0.5 in key color regions triggers an alert.

### 3.3 Cpk Process Capability Index Control

In mass production, **batch-to-batch consistency** of calibration parameters is critical. The Process Capability Index (Cpk, 过程能力指数) measures the stability of the production process:

$$C_{pk} = \min\left(\frac{USL - \mu}{3\sigma}, \frac{\mu - LSL}{3\sigma}\right)$$

where $USL$ (Upper Spec Limit) and $LSL$ (Lower Spec Limit) are the specification upper and lower limits, and $\mu$ and $\sigma$ are the batch mean and standard deviation.

**Cpk requirement:** Mass-production qualification typically requires $C_{pk} \geq 1.33$ (i.e., ±4σ within specification).

**Cpk monitoring for key calibration parameters:**

| Parameter | USL | LSL | Typical Cpk Target |
|-----------|-----|-----|--------------------|
| ColorChecker mean ΔE00 | 3.0 | 0 | ≥ 1.33 |
| LSC maximum non-uniformity | 5% | 0% | ≥ 1.33 |
| BLC R-channel error | 1 DN | −1 DN | ≥ 1.67 |
| AWB D65 color temperature deviation | 200 K | −200 K | ≥ 1.33 |

**SPC (Statistical Process Control):** Use control charts (X-bar chart, R chart) to monitor calibration results from each unit in real-time production. Alert immediately when a drift trend is detected (five consecutive units exceeding mean + 1σ).

### 3.4 Calibration Data Version Management

**Version management principles:**
1. **All calibration data under version control** (Git LFS or a dedicated calibration database); every calibration change has a commit record, change reason, and test validation conclusion
2. **Calibration Package format:** Each version includes sensor ID, calibration date/time, calibration environment (temperature/humidity/illuminant batch), parameter values for each module, and pass/fail status of validation tests
3. **Mass-production release approval process:** A calibration package must pass the following acceptance checks before entering mass production:
   - Numerical acceptance (BLC/LSC/AWB/CCM metrics all pass)
   - Image subjective review (at least 3 engineers score blind-test images)
   - Cpk evaluation (based on small-batch prototype statistics)

---

## 4 Common Calibration Failure Modes

### 4.1 Integrating Sphere Non-Uniformity → LSC Over-Correction

**Symptom:** After LSC calibration, "reverse vignetting" appears in a uniform scene — image center is darker and edges are brighter than normal.

**Cause:** The integrating sphere's output port is not ideally uniform, or the camera is not perpendicular to / centered on the sphere's output port during capture, so the calibration reference image itself has spatial non-uniformity. The LSC algorithm misidentifies this non-uniformity as lens vignetting and over-compensates.

**Solution:**
- Use a high-quality integrating sphere with known spatial uniformity (> 99 %)
- Before capture, verify sphere uniformity with a reference detector
- Pre-correct the calibration reference image for uniformity (if sphere non-uniformity is known and stable)

### 4.2 ColorChecker Aging → CCM Shift

**Symptom:** The same CCM is color-accurate early in mass production but gradually develops systematic color deviation (e.g., global yellow or magenta shift) over time.

**Cause:** A physical ColorChecker card ages with use and time; patch reflectance and chromaticity values change (especially highly saturated patches fade after UV exposure from sunlight). The calibration algorithm still uses the original factory standard chromaticity values, while the actual card has drifted.

**Solution:**
- Re-measure the actual CIE XYZ values of each patch with a spectrophotometer periodically (every quarter); update the calibration reference data
- Establish a card verification procedure: before each use, automatically compare against historical measurements; trigger a warning when deviation exceeds 1 ΔE
- Store the card under light-excluding, temperature- and humidity-controlled conditions (20 °C, 50 % RH) to extend its service life

### 4.3 Incomplete OB Region Shielding → BLC Bias

**Symptom:** After BLC subtraction, a small constant offset remains in the RAW image (e.g., entire image is approximately 5–10 DN brighter), with offset varying at different ISOs.

**Cause:** If the sensor OB region shielding structure is incomplete (manufacturing defect or design issue), OB pixels receive a small amount of leaked light, causing the OB mean to exceed the true dark current. BLC compensation based on OB pixels is therefore insufficient.

**Solution:**
- Switch to the dark-frame method for calibration, rather than relying on OB pixels
- Hardware fix to the shielding structure (if a batch issue)
- Software compensation: measure OB pixel response at different illuminance levels; estimate leak amount and compensate

### 4.4 Demosaic-Induced AWB Statistics Region Color Bias

**Symptom:** AWB calibration results (R_gain, B_gain) under standard illuminants have a 2 %–5 % deviation from the true white-balance gains, causing a slight color cast.

**Cause:** If the AWB calibration procedure computes white-balance gains after Demosaic and before CCM, the color interpolation error of the Demosaic algorithm (especially at boundary regions) contaminates the mean statistics.

**Solution:** Compute AWB gains by directly computing means of Bayer channels in the RAW domain (before Demosaic), avoiding the influence of Demosaic errors.

### 4.5 Multi-Batch Sensor Consistency Issues

**Symptom:** CCM calibration results differ significantly between adjacent production batches (mean ΔE00 difference > 1.0), causing different batches to produce images with different color styles.

**Cause:** Wafer manufacturing process variations (slight adjustments to lithography exposure, errors in color filter coating thickness) cause inter-batch spectral response differences, while the calibration algorithm uses the same fixed set of reference chromaticity values.

**Solution:**
- Perform per-batch calibration (Per-Batch Calibration) for each mass-production batch
- Establish a batch sampling validation mechanism: sample N units per batch (n ≥ 30) for statistical validation
- For batches that exceed control limits, trigger a recalibration or rejection process

---

## 5 Calibration Accuracy Evaluation Standards

### 5.1 EMVA 1288 Standard

The **EMVA 1288** standard published by the European Machine Vision Association (EMVA, 欧洲机器视觉协会) is the authoritative standard for industrial camera sensor performance evaluation. Main measurement indicators:

- **Quantum efficiency (QE):** Photon-to-electron conversion efficiency (%)
- **Read noise:** Number of electrons (e⁻ RMS)
- **Full well capacity:** Maximum storable electrons per pixel
- **Dark current:** e⁻/pixel/s
- **Dynamic range:** Full well capacity / read noise (dB)
- **Linearity error:** Maximum deviation of response from linear (%)

Measurement method: use a monochromatic light source of known power (530 nm or other wavelength); systematically scan the sensor response curve by adjusting optical power or exposure time; extract the above parameters from the Photon Transfer Curve (PTC).

### 5.2 ISO 15739 Image Noise and Quality Testing

ISO 15739:2023 "Photography — Electronic still-picture imaging — Noise measurements" defines standard measurement methods for digital camera image noise:

1. **SNR Measurement:** Photograph a uniform gray card; measure the ratio of signal mean to noise standard deviation
2. **Dynamic range measurement:** Determine usable exposure range based on noise floor
3. **Measurement conditions:** Specified illuminant (D65, 2000 lux), specified white balance, specified exposure (ISO sensitivity)

### 5.3 ΔE00 < 2.0 Acceptance Standard

ColorChecker color accuracy is the final comprehensive metric of ISP calibration. Industry-accepted acceptance standards:

| Application | Mean ΔE00 Requirement | Maximum Single-Patch ΔE00 |
|-------------|----------------------|---------------------------|
| Consumer smartphone (high-end flagship) | < 2.0 | < 5.0 |
| Consumer smartphone (mid-range) | < 3.0 | < 8.0 |
| Broadcast-grade camera | < 1.5 | < 3.0 |
| Medical imaging | < 1.0 | < 2.0 |
| Automotive camera (ADAS) | < 3.0 (visual task) | — |

Note: ΔE00 (CIEDE2000) is currently the color difference formula closest to human visual perception, superior to traditional ΔE76 (CIELAB Euclidean distance).

### 5.4 Calibration Repeatability Evaluation

Using the same calibration equipment and the same sensor, perform K separate calibrations at different times; evaluate calibration result repeatability:

$$\text{Repeatability}(X) = \frac{\text{Range}(X_1, \ldots, X_K)}{\text{Tolerance}(X)}$$

For BLC, if the range of 10 repeated calibrations (maximum − minimum) is < 0.3 DN, repeatability is good (< 30 % of tolerance).

---

## 6 Code Example

```python
"""
ISP Full Pipeline Calibration Demo: ColorChecker CCM automatic calibration script
Dependencies: numpy, scipy, colour-science (colour), matplotlib
Install: pip install colour-science
Usage: python ch28_isp_calibration_demo.py
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from typing import Tuple, Dict, Optional


# ─────────────────────────────────────────────
# Part 1: ColorChecker 24-patch standard data
# ─────────────────────────────────────────────

def get_colorchecker_d65_srgb() -> np.ndarray:
    """
    Returns the standard sRGB values (linear, 0–1 range) of the ColorChecker Classic
    24 patches under D65 illuminant.
    Data source: X-Rite official chromaticity data + IEC 61966-2-1 sRGB standard conversion.

    Returns:
        srgb_linear: (24, 3) float64, linear sRGB
    """
    # ColorChecker 24-patch CIE XYZ D65 (Y normalized to 1 for complete diffuse reflector)
    # Data source: Lindbloom (2003), based on Babelcolor CT&S measurements
    xyz_d65 = np.array([
        # Row 1: Skin tones
        [0.3897, 0.3551, 0.1968],  # 1 Dark Skin
        [0.5765, 0.5587, 0.4328],  # 2 Light Skin
        [0.2470, 0.2700, 0.4090],  # 3 Blue Sky
        [0.3378, 0.3810, 0.1945],  # 4 Foliage
        [0.3368, 0.3212, 0.5530],  # 5 Blue Flower
        [0.3530, 0.4477, 0.5082],  # 6 Bluish Green
        # Row 2: Primary & secondary
        [0.6285, 0.4922, 0.0944],  # 7 Orange
        [0.2033, 0.1956, 0.4650],  # 8 Purplish Blue
        [0.4940, 0.3079, 0.2185],  # 9 Moderate Red
        [0.1529, 0.1308, 0.2015],  # 10 Purple
        [0.4420, 0.5250, 0.0985],  # 11 Yellow Green
        [0.6160, 0.5409, 0.0497],  # 12 Orange Yellow
        # Row 3: RGB + CMY
        [0.1396, 0.1047, 0.4285],  # 13 Blue
        [0.2415, 0.3497, 0.1146],  # 14 Green
        [0.3939, 0.2130, 0.0785],  # 15 Red
        [0.6892, 0.6624, 0.0294],  # 16 Yellow
        [0.4922, 0.2862, 0.4017],  # 17 Magenta
        [0.1787, 0.2474, 0.4926],  # 18 Cyan
        # Row 4: Neutral patches
        [0.8600, 0.9000, 1.0800],  # 19 White (D65)
        [0.5765, 0.5984, 0.7010],  # 20 Neutral 8 (80%)
        [0.3587, 0.3700, 0.4300],  # 21 Neutral 6.5 (65%)
        [0.1908, 0.1984, 0.2298],  # 22 Neutral 5 (50%)
        [0.0860, 0.0900, 0.1025],  # 23 Neutral 3.5 (35%)
        [0.0291, 0.0300, 0.0340],  # 24 Black
    ], dtype=np.float64)

    # XYZ → linear sRGB (using IEC 61966-2-1 standard matrix)
    M_xyz_to_srgb = np.array([
        [ 3.2406, -1.5372, -0.4986],
        [-0.9689,  1.8758,  0.0415],
        [ 0.0557, -0.2040,  1.0570],
    ], dtype=np.float64)

    # Normalize: D65 white point corresponds to XYZ_D65 = [0.9505, 1.0000, 1.0886]
    xyz_d65_norm = xyz_d65 / np.array([0.9505, 1.0000, 1.0886])

    srgb_linear = (M_xyz_to_srgb @ xyz_d65_norm.T).T  # (24, 3)
    srgb_linear = np.clip(srgb_linear, 0, None)  # Small values may be slightly negative due to measurement error

    return srgb_linear


# ─────────────────────────────────────────────
# Part 2: Simulate sensor response (with spurious spectral response deviation)
# ─────────────────────────────────────────────

def simulate_sensor_response(
    srgb_linear: np.ndarray,
    sensor_matrix: Optional[np.ndarray] = None,
    noise_std: float = 0.005,
    seed: int = 42,
) -> np.ndarray:
    """
    Simulate sensor RAW response to ColorChecker.

    Transform ideal sRGB with a "wrong" matrix (simulating sensor SSR deviation),
    add small random noise as calibration input.

    Args:
        srgb_linear: (24, 3) target sRGB
        sensor_matrix: (3, 3) simulated sensor response matrix (None uses default bias matrix)
        noise_std: noise standard deviation (as fraction of signal)

    Returns:
        sensor_rgb: (24, 3) sensor output (normalized)
    """
    if sensor_matrix is None:
        # Simulate typical sensor color bias (red shift, G channel too close to red)
        sensor_matrix = np.array([
            [0.95, 0.08, -0.03],
            [-0.12, 1.10, 0.02],
            [0.02, -0.15, 1.13],
        ], dtype=np.float64)

    sensor_rgb = (sensor_matrix @ srgb_linear.T).T
    sensor_rgb = np.clip(sensor_rgb, 0, 1)

    rng = np.random.default_rng(seed)
    sensor_rgb += rng.normal(0, noise_std, sensor_rgb.shape)
    sensor_rgb = np.clip(sensor_rgb, 0.0, 1.0)

    return sensor_rgb.astype(np.float64)


# ─────────────────────────────────────────────
# Part 3: ΔE00 color difference calculation
# ─────────────────────────────────────────────

def srgb_to_lab(srgb: np.ndarray) -> np.ndarray:
    """
    Linear sRGB → CIE Lab (D65 white point).

    Args:
        srgb: (..., 3) linear sRGB [0,1]

    Returns:
        lab: (..., 3) L*, a*, b*
    """
    # Linear sRGB → XYZ
    M_srgb_to_xyz = np.array([
        [0.4124, 0.3576, 0.1805],
        [0.2126, 0.7152, 0.0722],
        [0.0193, 0.1192, 0.9505],
    ])
    shape = srgb.shape
    rgb_flat = srgb.reshape(-1, 3)
    xyz = (M_srgb_to_xyz @ rgb_flat.T).T

    # XYZ → Lab (D65: Xn=0.9505, Yn=1.0000, Zn=1.0886)
    xyz_n = np.array([0.9505, 1.0000, 1.0886])
    xyz_norm = xyz / xyz_n

    def f(t):
        delta = 6.0 / 29.0
        return np.where(t > delta**3, np.cbrt(t), t / (3 * delta**2) + 4.0 / 29.0)

    fx = f(xyz_norm[:, 0])
    fy = f(xyz_norm[:, 1])
    fz = f(xyz_norm[:, 2])

    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)

    return np.stack([L, a, b], axis=-1).reshape(shape)


def delta_e00(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """
    Compute CIEDE2000 color difference ΔE00.

    Args:
        lab1, lab2: (..., 3) CIE Lab color values

    Returns:
        de: (...,) ΔE00 values
    """
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]

    # Full CIEDE2000 formula (simplified implementation, kL=kC=kH=1)
    avg_L = (L1 + L2) / 2.0
    C1 = np.sqrt(a1**2 + b1**2)
    C2 = np.sqrt(a2**2 + b2**2)
    avg_C = (C1 + C2) / 2.0
    G = 0.5 * (1 - np.sqrt(avg_C**7 / (avg_C**7 + 25**7)))
    a1p = a1 * (1 + G)
    a2p = a2 * (1 + G)
    C1p = np.sqrt(a1p**2 + b1**2)
    C2p = np.sqrt(a2p**2 + b2**2)

    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360

    dLp = L2 - L1
    dCp = C2p - C1p
    dhp = np.where(
        np.abs(h2p - h1p) <= 180, h2p - h1p,
        np.where(h2p <= h1p, h2p - h1p + 360, h2p - h1p - 360)
    )
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp / 2))

    avg_Lp = (L1 + L2) / 2.0
    avg_Cp = (C1p + C2p) / 2.0
    avg_hp = np.where(
        np.abs(h1p - h2p) > 180,
        np.where(h1p + h2p < 360, (h1p + h2p + 360) / 2, (h1p + h2p - 360) / 2),
        (h1p + h2p) / 2
    )

    T = (1
         - 0.17 * np.cos(np.radians(avg_hp - 30))
         + 0.24 * np.cos(np.radians(2 * avg_hp))
         + 0.32 * np.cos(np.radians(3 * avg_hp + 6))
         - 0.20 * np.cos(np.radians(4 * avg_hp - 63)))

    SL = 1 + 0.015 * (avg_Lp - 50)**2 / np.sqrt(20 + (avg_Lp - 50)**2)
    SC = 1 + 0.045 * avg_Cp
    SH = 1 + 0.015 * avg_Cp * T
    RT = (-2 * np.sqrt(avg_Cp**7 / (avg_Cp**7 + 25**7))
          * np.sin(np.radians(60 * np.exp(-((avg_hp - 275) / 25)**2))))

    de = np.sqrt(
        (dLp / SL)**2 + (dCp / SC)**2 + (dHp / SH)**2
        + RT * (dCp / SC) * (dHp / SH)
    )
    return de


# ─────────────────────────────────────────────
# Part 4: CCM calibration (weighted least squares + ΔE optimization)
# ─────────────────────────────────────────────

def calibrate_ccm(
    sensor_rgb: np.ndarray,
    target_srgb: np.ndarray,
    weights: Optional[np.ndarray] = None,
    method: str = 'least_squares',
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calibrate CCM from sensor RGB and target sRGB.

    Args:
        sensor_rgb: (N, 3) sensor RAW RGB (after white balance; BLC/LSC complete)
        target_srgb: (N, 3) target linear sRGB
        weights: (N,) per-patch weights (None = uniform weights)
        method: 'least_squares' (linear least squares) or 'delta_e' (ΔE00 optimization)

    Returns:
        ccm: (3, 3) color correction matrix (right-multiply format: corrected = sensor_rgb @ ccm.T)
        de_per_patch: (N,) per-patch ΔE00 after calibration
    """
    N = sensor_rgb.shape[0]
    if weights is None:
        weights = np.ones(N)
    weights = weights / weights.sum() * N  # Normalize weights

    if method == 'least_squares':
        # Weighted least squares: min ||W(S @ M - T)||_F^2
        # Analytical solution: M = (S^T W S)^{-1} S^T W T (per channel)
        W = np.diag(weights)
        SWS = sensor_rgb.T @ W @ sensor_rgb  # (3,3)
        SWT = sensor_rgb.T @ W @ target_srgb  # (3,3)
        ccm = np.linalg.lstsq(SWS, SWT, rcond=None)[0]  # (3,3)

    elif method == 'delta_e':
        # Weighted ΔE00 optimization (non-linear, computationally intensive)
        target_lab = srgb_to_lab(target_srgb)

        def objective(m_flat):
            M = m_flat.reshape(3, 3)
            pred = np.clip(sensor_rgb @ M, 0, 1)
            pred_lab = srgb_to_lab(pred)
            de = delta_e00(pred_lab, target_lab)
            return float((weights * de**2).sum())

        m0 = np.eye(3).flatten()
        result = minimize(objective, m0, method='Nelder-Mead',
                         options={'maxiter': 10000, 'xatol': 1e-5, 'fatol': 1e-5})
        ccm = result.x.reshape(3, 3)
    else:
        raise ValueError(f"Unknown method: {method}")

    # Compute per-patch ΔE00 after calibration
    corrected = np.clip(sensor_rgb @ ccm, 0, 1)
    corrected_lab = srgb_to_lab(corrected)
    target_lab = srgb_to_lab(target_srgb)
    de_per_patch = delta_e00(corrected_lab, target_lab)

    return ccm, de_per_patch


# ─────────────────────────────────────────────
# Part 5: BLC validation helper function
# ─────────────────────────────────────────────

def validate_blc(dark_frames: np.ndarray) -> Dict[str, float]:
    """
    Validate BLC calibration result: compute dark-field mean and standard deviation.

    Args:
        dark_frames: (N, H, W) dark-field frames, uint16 (Bayer RGGB)

    Returns:
        stats: {'R_mean', 'Gr_mean', 'Gb_mean', 'B_mean',
                'R_std', 'Gr_std', 'Gb_std', 'B_std'}
    """
    channels = {
        'R': dark_frames[:, 0::2, 0::2],
        'Gr': dark_frames[:, 0::2, 1::2],
        'Gb': dark_frames[:, 1::2, 0::2],
        'B': dark_frames[:, 1::2, 1::2],
    }
    stats = {}
    for ch, data in channels.items():
        stats[f'{ch}_mean'] = float(data.mean())
        stats[f'{ch}_std'] = float(data.std())
    return stats


# ─────────────────────────────────────────────
# Part 6: Comprehensive demo
# ─────────────────────────────────────────────

def run_demo():
    print("=" * 60)
    print("ISP Full Pipeline Calibration Demo  (ch28_isp_calibration)")
    print("=" * 60)

    # 1. Load ColorChecker standard data
    print("\n[1] Loading ColorChecker D65 standard data...")
    target_srgb = get_colorchecker_d65_srgb()
    print(f"    24-patch target sRGB shape: {target_srgb.shape}")
    print(f"    Target sRGB range: [{target_srgb.min():.3f}, {target_srgb.max():.3f}]")

    # 2. Simulate sensor response (with color bias)
    print("\n[2] Simulating sensor response (with SSR bias + noise)...")
    sensor_rgb = simulate_sensor_response(target_srgb, noise_std=0.008)

    # Compute pre-correction color error
    sensor_lab = srgb_to_lab(sensor_rgb)
    target_lab = srgb_to_lab(target_srgb)
    de_before = delta_e00(sensor_lab, target_lab)
    print(f"    Before correction: mean ΔE00={de_before.mean():.3f}  max ΔE00={de_before.max():.3f}")

    # 3. CCM calibration (least squares)
    print("\n[3] CCM calibration (weighted least squares; neutral patches weight ×3)...")
    # Assign 3× weight to neutral patches (patches 19–24)
    weights = np.ones(24)
    weights[18:24] = 3.0  # Row 4: neutral patches

    ccm_ls, de_after_ls = calibrate_ccm(sensor_rgb, target_srgb,
                                         weights=weights, method='least_squares')

    print(f"    Least-squares CCM:\n{ccm_ls}")
    print(f"    After correction: mean ΔE00={de_after_ls.mean():.3f}  max ΔE00={de_after_ls.max():.3f}")

    # 4. Acceptance check
    print("\n[4] Calibration acceptance check:")
    avg_de = de_after_ls.mean()
    max_de = de_after_ls.max()
    neutral_de = de_after_ls[18:24].mean()
    print(f"    Mean ΔE00 = {avg_de:.3f}  (standard: < 2.0)  → {'PASS' if avg_de < 2.0 else 'FAIL'}")
    print(f"    Max ΔE00  = {max_de:.3f}  (standard: < 5.0)  → {'PASS' if max_de < 5.0 else 'FAIL'}")
    print(f"    Neutral ΔE00 = {neutral_de:.3f}  (standard: < 1.5)  → {'PASS' if neutral_de < 1.5 else 'FAIL'}")

    # 5. BLC validation demo
    print("\n[5] BLC dark-field validation demo...")
    rng = np.random.default_rng(7)
    # Simulate 10 frames of 64×64 dark-field images (12-bit, BLC ≈ 64)
    dark_sim = rng.normal(64.0, 2.0, (10, 64, 64)).astype(np.uint16)
    blc_stats = validate_blc(dark_sim)
    print(f"    {'Channel':>8}  {'Mean':>8}  {'Std':>8}  {'Error(−64)':>12}")
    for ch in ['R', 'Gr', 'Gb', 'B']:
        mean = blc_stats[f'{ch}_mean']
        std  = blc_stats[f'{ch}_std']
        err  = mean - 64.0
        status = 'PASS' if abs(err) < 1.0 else 'FAIL'
        print(f"    {ch:>8}  {mean:>8.3f}  {std:>8.3f}  {err:>+10.3f}  {status}")

    # 6. Visualization
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Per-patch color comparison
    patch_indices = np.arange(1, 25)
    axes[0].bar(patch_indices - 0.2, de_before, width=0.35,
                label='Before correction', color='salmon', alpha=0.8)
    axes[0].bar(patch_indices + 0.2, de_after_ls, width=0.35,
                label='After CCM correction', color='steelblue', alpha=0.8)
    axes[0].axhline(2.0, color='red', linestyle='--', linewidth=1, label='Acceptance line ΔE=2.0')
    axes[0].set_xlabel('ColorChecker patch number')
    axes[0].set_ylabel('ΔE00')
    axes[0].set_title('Color error before/after CCM calibration')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # CCM matrix visualization
    im = axes[1].imshow(ccm_ls, cmap='RdBu_r', vmin=-0.5, vmax=1.5, aspect='auto')
    axes[1].set_title('CCM Matrix (Least Squares)')
    axes[1].set_xticks([0, 1, 2])
    axes[1].set_xticklabels(['R', 'G', 'B'])
    axes[1].set_yticks([0, 1, 2])
    axes[1].set_yticklabels(['R_out', 'G_out', 'B_out'])
    for i in range(3):
        for j in range(3):
            axes[1].text(j, i, f'{ccm_ls[i,j]:.4f}', ha='center',
                        va='center', fontsize=9)
    plt.colorbar(im, ax=axes[1])

    # Color distribution scatter plot (target vs. corrected)
    corrected = np.clip(sensor_rgb @ ccm_ls, 0, 1)
    axes[2].scatter(target_srgb[:, 0], corrected[:, 0], c='red', alpha=0.7, s=50, label='R')
    axes[2].scatter(target_srgb[:, 1], corrected[:, 1], c='green', alpha=0.7, s=50, label='G')
    axes[2].scatter(target_srgb[:, 2], corrected[:, 2], c='blue', alpha=0.7, s=50, label='B')
    axes[2].plot([0, 1], [0, 1], 'k--', linewidth=1, label='Ideal')
    axes[2].set_xlabel('Target sRGB')
    axes[2].set_ylabel('CCM-corrected sRGB')
    axes[2].set_title('Color accuracy scatter plot')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    axes[2].set_aspect('equal')

    plt.tight_layout()
    out_path = 'isp_calibration_demo.png'
    plt.savefig(out_path, dpi=120)
    plt.close()
    print(f"\nDemo figure saved: {out_path}")
    print("=" * 60)


if __name__ == '__main__':
    run_demo()
```

---

## References

[1] Reinhard, E., et al. Color Imaging: Fundamentals and Applications. A K Peters/CRC Press, 2008. Chapter 10: Camera Characterization.
[2] Sharma, G., Wu, W., & Dalal, E.N. "The CIEDE2000 Color-Difference Formula: Implementation Notes, Supplementary Test Data, and Mathematical Observations." Color Research & Application, vol. 30, no. 1, 2005, pp. 21–30.
[3] EMVA Standard 1288 Release 4.0. "Standard for Characterization of Image Sensors and Cameras." European Machine Vision Association, 2021.
[4] ISO 15739:2023. "Photography — Electronic Still-Picture Imaging — Noise Measurements." International Organization for Standardization, 2023.
[5] Cheung, V., & Westland, S. "Methods for Optimal Color Selection." *Journal of Imaging Science and Technology*, vol. 50, no. 5, pp. 481–488, 2006.
[6] Karaimer, H.C., & Brown, M.S. "A Software Platform for Manipulating the Camera Imaging Pipeline." Proceedings of ECCV, 2016, pp. 429–444.
[7] Lindbloom, B. "Chromatic Adaptation." www.brucelindbloom.com, 2003. (ColorChecker CIE XYZ data reference)
[8] X-Rite Inc. "ColorChecker Classic Specifications." X-Rite Technical Note, 2019.
[9] Wueller, D. "OECF Measurements According to ISO 14524 — What We Learn and What We Don't." Proceedings of SPIE, vol. 5294, 2004.
[10] Bianco, S., Gasparini, F., & Schettini, R. "Colour Correction Pipeline Optimization for Digital Cameras." Journal of Electronic Imaging, vol. 18, no. 2, 2009.
[11] Imai, F.H., & Berns, R.S. "Spectral Estimation Using Trichromatic Digital Cameras." Proceedings of International Symposium on Multispectral Imaging and Color Reproduction for Digital Archives, 1999.

## Glossary

| Term | Full Form / Explanation |
|------|-------------------------|
| **BLC (Black Level Clamp/Correction)** | Subtracts the sensor dark-field offset |
| **DPC (Defect Pixel Correction)** | Interpolation repair of hot/cold/stuck pixels |
| **LSC (Lens Shading Correction)** | Compensates for spatial luminance non-uniformity caused by lens vignetting |
| **AWB (Auto White Balance)** | Adjusts RGB gains to render gray objects as neutral |
| **CCM (Color Correction Matrix)** | Maps sensor RGB to a standard color space |
| **ΔE00 (CIEDE2000)** | Color difference formula published by CIE in 2000; closest to human visual perception |
| **ColorChecker** | X-Rite Macbeth ColorChecker color target; industry standard tool for ISP color calibration |
| **CRF (Camera Response Function)** | Describes the mapping from radiance to digital values |
| **OB (Optical Black)** | Shielded pixels at sensor edge used as a real-time BLC reference |
| **PTC (Photon Transfer Curve)** | Used to measure sensor noise characteristics |
| **INL (Integral Non-Linearity)** | Cumulative deviation of sensor response from the ideal line |
| **DNL (Differential Non-Linearity)** | Non-uniformity between adjacent code values |
| **SSR (Sensor Spectral Response)** | Describes each channel's sensitivity to different wavelengths |
| **Luther-Ives condition** | Sufficient condition for sensor SSR to be a linear transform of CIE XYZ functions; when satisfied, color matching invariance can be achieved |
| **EMVA 1288** | European Machine Vision Association camera performance evaluation standard |
| **Cpk (Process Capability Index)** | Quantifies the distance between the production process and specification limits |
| **SPC (Statistical Process Control)** | Real-time production quality monitoring via control charts |
| **NVM (Non-Volatile Memory)** | Used to store factory calibration data |
| **D65** | CIE standard illuminant D65, precise CCT 6504 K, representing average daylight; sRGB white point |
| **CCT (Correlated Color Temperature)** | Approximate black-body temperature describing illuminant color (K) |
| **OECF (Opto-Electronic Conversion Function)** | Camera response curve; defined in ISO 14524 |
| **JND (Just Noticeable Difference)** | Minimum perceptible color difference; ΔE00 ≈ 1.0–2.0 is a typical JND |
