# Appendix B — Calibration Chart Standards | 标定卡参考

> Quick reference for all calibration charts used in this handbook.
> For measurement procedures, see the §2 Calibration section of each relevant chapter.

---

## Overview

Calibration charts (also called test charts or targets) are physical or digital references used to characterize ISP modules. Each chart is optimized for measuring specific image quality attributes. This appendix lists the most common charts, their structure, the metrics they produce, and which ISP modules they support.

---

## B.1 Macbeth ColorChecker 24 (Classic)

| Field | Details |
|-------|---------|
| **Full name** | Macbeth ColorChecker Classic (X-Rite) |
| **Purpose** | Color accuracy calibration, AWB ground truth, CCM fitting |
| **Structure** | 4×6 grid = 24 colored patches: 6 natural object colors, 6 primary/secondary colors, 6 achromatic patches (white to black) |
| **Key patches** | Row 4 (bottom): gray scale from D18 to near-black |
| **Metric extracted** | ΔE₀₀ (per patch), mean/max ΔE, gray scale neutrality, CCM fit residual |
| **Calibration module** | CCM (Ch23), AWB (Ch22), Gamma (Ch24) |
| **Measurement standard** | Illuminant: D50 or D65. Recommended observer: CIE 1931 2°. Reference XYZ values from manufacturer. |
| **Public reference** | https://www.xrite.com/categories/calibration-profiling/colorchecker-classic |
| **Notes** | The 24 patches span a range of natural object colors. The L-shaped gray row (patches 19–24) is especially critical for white balance and neutrality assessment. CIE Lab reference values for all 24 patches under D50/D65 are publicly documented by X-Rite. |

**Typical ISP use (Ch23 CCM fitting):**

```
1. Capture chart under D65 illumination, RAW format.
2. Extract per-patch mean RGB (avoid patch borders).
3. Apply current pipeline up to pre-CCM stage.
4. Solve: M_CCM = argmin Σᵢ ΔE²(M · RGB_i^sensor, XYZ_i^reference)
5. Evaluate: report mean ΔE₀₀ and max ΔE₀₀.
```

---

## B.2 ISO 12233 / SFRplus

| Field | Details |
|-------|---------|
| **Full name** | ISO 12233:2017 Photography — Electronic still picture imaging — Resolution and spatial frequency responses |
| **Purpose** | Spatial resolution measurement, MTF50 characterization |
| **Structure** | Multiple slanted edges (5° tilt) at various field positions + hyperbolic/sinusoidal patterns for visual assessment |
| **Key feature** | Slanted-edge regions at center and corners for spatial frequency response (SFR/MTF) measurement |
| **Metric extracted** | MTF50 (cycles/pixel or lp/mm), MTF50P, MTF30, spatial frequency response curve |
| **Calibration module** | Sharpening (Ch21), Optics/Lens (Ch02), Demosaic (Ch19) |
| **Measurement standard** | ISO 12233:2017. Software: Imatest, OpenCV SFR, or open-source sfr-esfr |
| **Public reference** | https://www.iso.org/standard/71696.html |
| **SFRplus variant** | Adds high-contrast slanted edges for automatic detection, field uniformity measurement. Imatest-specific. |
| **Notes** | The slanted-edge method is the industry standard for MTF measurement. Edge should be tilted 3–7° to achieve sub-pixel sampling. Requires sufficient contrast ratio (≥50:1). |

---

## B.3 Siemens Star

| Field | Details |
|-------|---------|
| **Full name** | Siemens Star (also: radial resolution target) |
| **Purpose** | Spatial resolution, demosaic artifact detection, aliasing visualization |
| **Structure** | Radially symmetric pattern with alternating black/white sectors converging to a center point. Typically 36 or 72 sectors. |
| **Key feature** | As radius decreases, spatial frequency increases. The radius at which the pattern becomes indistinguishable gives the resolution limit. |
| **Metric extracted** | Limiting resolution (cycles/pixel), aliasing visibility, color moiré at high frequencies |
| **Calibration module** | Demosaic (Ch19), Sharpening (Ch21) |
| **Measurement standard** | ISO 15739, various implementations |
| **Public reference** | https://en.wikipedia.org/wiki/Siemens_star |
| **Notes** | Particularly useful for detecting demosaic-induced aliasing: color moiré appears as chromatic fringing near the center of the star. Visual inspection complements quantitative MTF measurement. |

---

## B.4 USAF 1951 Resolution Target

| Field | Details |
|-------|---------|
| **Full name** | United States Air Force 1951 MIL-STD-150A resolution test chart |
| **Purpose** | Limiting resolution measurement |
| **Structure** | Groups of 3 horizontal + 3 vertical bar patterns at increasing spatial frequencies. Groups -2 to +7, elements 1–6 per group. |
| **Key feature** | Each group/element combination encodes a specific spatial frequency in lp/mm. |
| **Metric extracted** | Limiting resolution in lp/mm (highest group/element where bars are distinguishable) |
| **Calibration module** | Optics (Ch02), Demosaic (Ch19) |
| **Public reference** | https://en.wikipedia.org/wiki/USAF_1951_resolution_test_chart |
| **Spatial frequency formula** | f [lp/mm] = 2^(Group + (Element-1)/6) |
| **Notes** | USAF targets are primarily used in microscopy and scientific imaging. In consumer camera ISP, ISO 12233 slanted-edge is preferred due to its sub-pixel accuracy, but USAF remains useful for quick visual resolution checks. |

---

## B.5 X-Rite ColorChecker Passport Photo 2

| Field | Details |
|-------|---------|
| **Full name** | X-Rite ColorChecker Passport Photo 2 |
| **Purpose** | Wide gamut color calibration, skin tone profiling, creative color matching |
| **Structure** | 3 charts on folding card: (1) Classic 24-patch, (2) Creative enhancement (enhanced saturation) patches, (3) White balance target (clean white/gray patches) |
| **Key feature** | Compact form factor (passport size). Wide gamut patches extend beyond sRGB for profiling RAW-to-display pipelines. |
| **Metric extracted** | ΔE₀₀, skin tone accuracy, ICC profile quality |
| **Calibration module** | CCM (Ch23), AWB (Ch22), Gamma (Ch24) |
| **Public reference** | https://www.xrite.com/categories/calibration-profiling/colorchecker-passport-photo-2 |
| **Notes** | The white balance target (4 neutral patches) provides a clean reference for AWB calibration under field conditions. The creative enhancement row enables testing of gamut mapping and vivid color rendering. |

---

## B.6 eSFR ISO 12233 (Slanted Edge Target)

| Field | Details |
|-------|---------|
| **Full name** | Enhanced Spatial Frequency Response (eSFR) target per ISO 12233:2017 |
| **Purpose** | MTF measurement at multiple field positions, lateral chromatic aberration, geometric distortion |
| **Structure** | Multiple slanted edges distributed across the field (center + 4 corners + mid-edge positions). Includes gray scale and color patches. |
| **Key feature** | Automated edge detection enables fast MTF50 mapping across the full field. |
| **Metric extracted** | MTF50 map (field uniformity), chromatic aberration (lateral), distortion |
| **Calibration module** | Sharpening (Ch21), LSC (Ch25), Optics (Ch02) |
| **Measurement standard** | ISO 12233:2017 Annex A (slanted edge method) |
| **Public reference** | Imatest eSFR documentation: https://www.imatest.com/solutions/esfr-iso-12233/ |
| **Notes** | The eSFR chart is the current preferred standard for production-line IQA in smartphone camera manufacturing. Its combination of resolution and color patches in a single chart reduces test fixture complexity. |

---

## B.7 Gray Card 18%

| Field | Details |
|-------|---------|
| **Full name** | 18% Neutral Gray Reflectance Card |
| **Purpose** | Exposure calibration, noise measurement, gain calibration |
| **Structure** | Uniform flat gray surface with reflectance ≈ 18% (≈ 1 EV below mid-tone on photographic scale) |
| **Key feature** | Spectrally neutral. Provides known luminance for absolute exposure calibration. |
| **Metric extracted** | Absolute exposure (EV), read noise floor, SNR at ISO X, PTC slope (photon transfer coefficient α) |
| **Calibration module** | BLC (Ch18), Noise model (Ch04), AE calibration (Ch46) |
| **Notes** | For noise model calibration: capture a series of 18% gray frames at varying ISO. Plot variance vs. mean signal per channel. Slope = photon transfer coefficient α; y-intercept ≈ read noise β. This produces the Poisson-Gaussian noise model parameters. See Ch04 §2. |

---

## B.8 Flat Field (Uniform Illumination Field)

| Field | Details |
|-------|---------|
| **Full name** | Flat field / uniform illumination target |
| **Purpose** | Lens shading characterization, black level calibration |
| **Structure** | Not a physical chart — uniform integrating sphere or light box producing spatially uniform radiance across the full field of view |
| **Key feature** | Any spatial non-uniformity in the captured image is attributable to the optical system (vignetting) + sensor (PRNU) |
| **Metric extracted** | Gain map G(x,y) per color channel; corner-to-center ratio; LSC polynomial coefficients |
| **Calibration module** | LSC (Ch25), BLC (Ch18) |
| **Procedure** | (1) Capture flat field at multiple apertures and focus distances. (2) Compute per-pixel mean over N frames. (3) Normalize by center value: G(x,y) = I_center / I(x,y). (4) Fit polynomial or piecewise surface. |
| **Notes** | LSC calibration is highly aperture-dependent (physical vignetting varies with f/#) and focus-dependent (at macro distances, pupil geometry changes). A complete LSC table covers the full aperture × focus distance space. |

---

## Summary Table

| Chart | Primary Module | Key Metric | Format |
|-------|---------------|------------|--------|
| Macbeth ColorChecker 24 | CCM, AWB | ΔE₀₀ | Physical / digital |
| ISO 12233 / SFRplus | Sharpening, Optics | MTF50 | Physical |
| Siemens Star | Demosaic, Sharpening | Limiting resolution, aliasing | Physical / digital |
| USAF 1951 | Optics, Demosaic | lp/mm (visual) | Physical |
| ColorChecker Passport | CCM, AWB | ΔE₀₀, skin tone | Physical |
| eSFR ISO 12233 | Sharpening, LSC | MTF50 field map | Physical |
| Gray card 18% | BLC, Noise model, AE | SNR, α, β (noise params) | Physical |
| Flat field | LSC, BLC | Gain map G(x,y) | Integrating sphere |

---

## B.3 Standard Operating Procedures for Calibration

### B.3.1 BLC Black Level Calibration SOP

**Objective**: Accurately measure the dark-current baseline of each sensor channel, ensuring BLC correction values are precise across temperature and gain conditions.

**Prerequisites**
- Lens cap on or sensor fully light-blocked (aperture at minimum; use a blackout board)
- Wait for sensor temperature to stabilize before starting (3–5 minutes after power-on)
- Gain settings: cover all ISO stops (ISO 100/400/800/1600/3200/6400)

**Procedure Steps**

| Step | Action | Acceptance Criterion |
|------|--------|---------------------|
| 1 | Set exposure time = 0 (shortest available, approx. 1/32000s), ISO 100 | Confirm no light leakage |
| 2 | Capture 16 consecutive RAW frames; extract OB (Optical Black) row data | OB pixel uniformity σ < 2 DN |
| 3 | Compute median over 16 frames to obtain R/Gr/Gb/B four-channel BLC offsets | Four-channel delta ΔBL < 5 DN |
| 4 | Repeat steps 1–3 at 10°C / 25°C / 45°C | Temperature coefficient dBLC/dT < 0.5 DN/°C |
| 5 | Repeat for all ISO stops; build 2D BLC(ISO, T) lookup table | Interpolation error < 1 DN |
| 6 | Write calibration results to ISP BLC LUT (Chromatix XML or MTK NDD format) | Verify no color cast in dark-field image corners |

**Acceptance Criterion**: After BLC correction, R/G channel mean ratio on 18% gray card = 1.000 ± 0.005 (before AWB)

**Troubleshooting**

| Symptom | Possible Cause | Resolution |
|---------|---------------|------------|
| OB row fluctuation (σ > 5 DN) | Incomplete light-blocking or unstable VDD | Check blackout seal; re-regulate supply |
| Four-channel BLC discrepancy > 10 DN | Inter-channel gain mismatch | Check PDAF phase-pixel bias settings |
| Temperature drift > 1 DN/°C | High dark-current activation energy | Build fine-grained temperature interpolation table (5°C intervals) |
| Fixed pattern noise at high ISO | Readout amplifier fixed offset | Apply column-wise BLC correction |

**Important Notes**

1. OB row count: use at least 8 OB pixel rows for averaging; single-row OB is susceptible to neighboring pixel influence.
2. Long-exposure BLC: night-mode long exposures (>1s) require a separate long-exposure BLC table, as dark current accumulates significantly.
3. Multi-frame median preferred over mean: median is more robust against burst noise (cosmic rays, EMI).

---

### B.3.2 LSC Lens Shading Calibration SOP

**Objective**: Generate an LSC gain grid (17×17 or 33×33) for each focal length/aperture/color-temperature combination to compensate for lens vignetting and color shading.

**Required Equipment**
- Uniform light field box (integrating sphere or LED panel): uniformity > 99% (center vs. corner luminance ratio < 1%)
- Calibration target: plain white board (white paper or uniform Lambertian reflector)
- Color temperature controllable (D50/D65/A illuminant switching)

**Procedure Steps**

```
Step 1: Light field uniformity verification
  - Capture a uniform white field (monochrome, no ISP processing)
  - Verify center 1/3 area vs. edge luminance ratio ≤ 1:1.25 (±20%)
  - If non-uniform: adjust light source position or switch to integrating sphere

Step 2: Raw LSC measurement (no correction)
  - Disable all ISP modules (keep BLC on, turn off LSC)
  - Capture 8 RAW frames per illuminant condition; average for noise reduction
  - Compute gain map: G(x,y) = I_center / I(x,y)
  - Compute separately for four channels: G_R, G_Gr, G_Gb, G_B

Step 3: Gain smoothing and interpolation (LSC mesh generation)
  - Fit G(x,y) with a 2D polynomial (5th to 7th order)
  - Generate 17×17 or 33×33 grid-point gain table
  - Verify: fit residual RMS < 0.3%
```

**Multi-Focal-Length LSC Calibration Matrix**

| Equivalent Focal Length | Aperture | Color Temperature | Table Count |
|------------------------|----------|------------------|-------------|
| 0.6× ultra-wide | f/2.2 | D65 + A | 2 |
| 1× main | f/1.8 / f/2.8 / f/4.0 | D65 + A | 6 |
| 3.2× telephoto | f/2.8 | D65 + A | 2 |

**LSC Gain Grid Format Notes**

Qualcomm Chromatix format (17×17 grid, 289 nodes per channel):
```xml
<lsc_r_gain>
  <!-- 17 rows × 17 cols, row-major; center=1.0, corners typically 1.5–3.0 -->
  1.862 1.744 1.632 1.534 1.453 1.389 1.341 1.307 1.291 1.307 1.341 1.389 1.453 1.534 1.632 1.744 1.862
  <!-- ... remaining 16 rows ... -->
</lsc_r_gain>
```

MTK NDD format (HW supports 33×33 grid for higher accuracy):
```c
// lsc_table[channel][row][col], channel: 0=R,1=Gr,2=Gb,3=B
uint16_t lsc_table[4][33][33] = { ... };
```

**LSC and Color Consistency**

Color temperature affects LSC: R/B channel shading distributions differ under different illuminants (B-channel shading is deeper under warm light). Therefore, a separate LSC table must be built per illuminant, with the ISP dynamically interpolating between tables based on the AWB-estimated CCT.

**Acceptance Criterion**: After LSC correction, per-channel uniformity of a uniform white field σ/μ < 0.5% (corner-to-center luminance difference < 2%)

---

### B.3.3 AWB Color Temperature Calibration SOP

**Objective**: Establish the mapping between sensor (R/G, B/G) gains and correlated color temperature (CCT) to ensure accurate white balance across multiple illuminants.

**Calibration Illuminant Parameters**

| Illuminant | CCT (K) | Standard | Application |
|------------|---------|----------|-------------|
| A (incandescent) | 2856 K | CIE Illuminant A | Indoor warm light |
| TL84 (tri-phosphor fluorescent) | 4150 K | CIE F11 | Commercial lighting |
| D50 | 5003 K | ISO 3664:2000 | Print standard |
| D65 | 6504 K | CIE Illuminant D65 | Daylight standard |
| D75 | 7500 K | Overcast sky | Outdoor shade |

**Procedure Steps**

```
Step 1: Capture ColorChecker (X-Rite standard color chart); 5 RAW frames per illuminant
Step 2: Extract neutral gray patches from ColorChecker (rows G/H 18% gray + N9 white)
Step 3: Compute measured (R/G, B/G) gains
Step 4: Using G/G = 1.0 as reference, compute target gains:
        WB_R = G_target_R / G_measured_R
        WB_B = G_target_B / G_measured_B
Step 5: Verify ColorChecker 24-patch ΔE₀₀ < 3.0 (after AWB correction)
Step 6: Build CCT → (WB_R, WB_B) mapping table (Chromatix multi-light-source table)
```

**Planckian Locus and AWB Lock Region**

AWB algorithms typically define a lock region (locus) in the CIE 1931 xy or u'v' chromaticity diagram; only sensor measurements falling within this region contribute to AWB statistics:

```
Typical AWB valid region (u'v' chromaticity):
  ±0.05 u'v' around Planckian locus from 2000K–8000K
  Exclude highly saturated pixels (Chroma > 0.6)
  Exclude overexposed pixels (Y > 240) and underexposed pixels (Y < 16)
```

**Inter-Illuminant Interpolation Verification**

Capture a test shot at 3500 K (between A and TL84) and verify interpolated ΔE₀₀ < 4.0 to prevent interpolation overshoot.

**Mixed Illuminant Scene Handling**

Real scenes often contain mixed light (e.g., daylight + fluorescent); AWB must estimate the illuminant mixture ratio:
- Method 1: Weighted average (by illuminant area weight)
- Method 2: Optimal transport distance matching (Wasserstein distance)
- Method 3: CNN-based illuminant estimation (see Volume 3, Chapter 1)

**Acceptance Criteria**

| Scene | Metric | Threshold |
|-------|--------|-----------|
| Single-illuminant standard | ΔE₀₀ (18% gray) | < 1.5 |
| Single-illuminant ColorChecker | Mean ΔE₀₀ | < 3.0 |
| Interpolated mid-CCT | ΔE₀₀ | < 4.0 |
| Mixed illuminant | ΔE₀₀ | < 5.0 |

---

### B.3.4 CCM Color Correction Matrix Calibration SOP

**Objective**: Minimize color error from sensor RGB to standard sRGB (or Display P3).

**Calibration Parameters**
- Chart: X-Rite ColorChecker Classic (24 patches) or ColorChecker Passport (48 patches)
- Reference values: XYZ values per patch under D65 from colour-science.org
- Solver: Ordinary Least Squares (OLS) or Weighted Least Squares (WLS, assigning higher weight ×3 to neutral gray patches)

**Mathematical Derivation**

Given N patches, sensor measurements $\mathbf{S} \in \mathbb{R}^{N \times 3}$, reference sRGB values $\mathbf{T} \in \mathbb{R}^{N \times 3}$:

$$\mathbf{M} = \arg\min_{\mathbf{M}} \|\mathbf{S} \mathbf{M}^T - \mathbf{T}\|_F^2$$

OLS solution: $\mathbf{M}^T = (\mathbf{S}^T \mathbf{S})^{-1} \mathbf{S}^T \mathbf{T}$

Weighted WLS: $\mathbf{M}^T = (\mathbf{S}^T \mathbf{W} \mathbf{S})^{-1} \mathbf{S}^T \mathbf{W} \mathbf{T}$, where $\mathbf{W}$ is a diagonal weight matrix.

**Constraint**: White maps to white (row-sum constraint: $\sum_j M_{ij} = 1, \forall i$)

**Practical Weight Strategy**

```python
# Weight configuration example (Python)
weights = np.ones(24)
weights[18:24] *= 3.0   # Neutral gray axis (patches 19–24) weight ×3
weights[0:3]  *= 2.0    # Skin tones (patches 1–3) weight ×2
weights[6:12] *= 1.5    # Natural object colors weight ×1.5

W = np.diag(weights)
# WLS solution
M_T = np.linalg.solve(S.T @ W @ S, S.T @ W @ T)
CCM = M_T.T
```

**Multi-Illuminant CCM**

CCM should be calibrated separately per illuminant; the ISP interpolates between CCMs based on the AWB-estimated CCT:

| Illuminant | CCM Application |
|------------|----------------|
| A light (2856 K) | Indoor warm light scenes |
| D65 (6504 K) | Daylight / standard scenes |
| Interpolated | Auto-interpolated for intermediate CCT |

**Acceptance Criteria**
- All 24 patches $\overline{\Delta E_{00}} < 2.5$ (sRGB) or $< 3.0$ (Display P3)
- Neutral gray axis (N2–N9.5) $\Delta E_{00} < 1.5$
- Skin tones (patches 1–3) $\Delta E_{00} < 2.0$ (especially critical for face recognition)

**CCM Validation Workflow**

```
1. Load ColorChecker D65 reference values using the colour-science Python library
2. Extract 24-patch mean RGB from the calibrated image
3. Apply sRGB gamma decoding (linearize)
4. Convert linear RGB to XYZ (via sRGB matrix)
5. Convert to CIE Lab (D65 white point)
6. Compute per-patch ΔE₀₀ (CIEDE2000 formula)
7. Output mean/max values and per-patch scatter plot
```

---

### B.3.5 DPC Defective Pixel Calibration SOP

**Objective**: Generate the factory static defective pixel map (Static DPC Map) for static bad-pixel correction.

**Defect Type Definitions**

| Type | Definition | Detection Method |
|------|-----------|-----------------|
| Hot Pixel | Dark-field luminance > mean + 5σ | Dark-field capture (blocked); find above-threshold pixels |
| Dead Pixel | Bright-field luminance < mean − 5σ | Bright-field capture (white field); find below-threshold pixels |
| Stuck Pixel | Pixel value is constant (no response) | Value unchanged across multiple exposure levels |
| Cluster Defect | ≥ 2 defects within a 3×3 region | Clustering detection algorithm |

**Procedure Steps**

```
Step 1: Dark-field capture
  - Block light (lens cap + blackout cloth), exposure 1/30s, ISO 1600
  - Capture 16 RAW frames; per-pixel median stack (resist random noise)
  - Compute full-image mean μ and standard deviation σ
  - Hot pixel map = { (x,y) | I(x,y) > μ + 5σ }

Step 2: Bright-field capture
  - Uniform white-field light source (uniformity > 95%); expose so histogram
    peak is approximately 80% full-scale
  - Capture 16 RAW frames; median stack
  - Compute full-image mean μ and standard deviation σ
  - Dead pixel map = { (x,y) | I(x,y) < μ − 5σ }

Step 3: Stuck pixel detection
  - Capture at 10%, 50%, and 90% exposure levels
  - Stuck pixels = pixels where the value difference across all three levels < 2 DN

Step 4: Merge defect maps
  - Static DPC Map = hot pixel map ∪ dead pixel map ∪ stuck pixel map
  - Label cluster defects (require separate handling strategy)

Step 5: Format conversion
  - Convert to ISP platform format
    (Qualcomm: coordinate list CSV; MTK: bit-mask or coordinate pairs)
  - Write to OTP (One-Time-Programmable Memory) or XML configuration file
```

**Defect Grade Classification**

| Grade | Defect Count (per MP) | Disposition |
|-------|-----------------------|-------------|
| Grade A (Excellent) | < 50 | Normal shipment; static DPC correction |
| Grade B (Pass) | 50–200 | Normal shipment; static + dynamic DPC correction required |
| Grade C (Marginal) | 200–500 | Customer negotiation required; acceptable for special applications |
| Grade D (Fail) | > 500 | Scrap or downgrade |

**Acceptance Criterion**: Factory static DPC count < 100 pixels/MP (< 100 defects per million pixels); no cluster defects

---

### B.3.6 Noise Model Calibration SOP (PTC Curve)

**Objective**: Measure the photon transfer characteristics of the sensor to obtain Poisson-Gaussian noise model parameters (α, β) for use in ISP denoising module tuning.

**Principle**

Poisson-Gaussian noise model:

$$\sigma^2(s) = \alpha \cdot s + \beta$$

Where:
- $s$: per-pixel mean signal (DN)
- $\sigma^2$: per-pixel variance
- $\alpha$: photon transfer coefficient (slope); related to quantum efficiency and full-well capacity
- $\beta$: readout noise variance (fixed noise floor); related to dark current and ADC precision

**Measurement Steps**

```
Step 1: Prepare a uniform illuminated scene (18% gray card or integrating sphere)
Step 2: By varying exposure time (fixed ISO), capture 10–15 different luminance levels
        Coverage: from 5% full-scale to 95% full-scale (avoid saturation)
Step 3: Capture 32 RAW frames at each luminance level
Step 4: For each luminance level:
        - Compute per-pixel mean μ over 32 frames (signal)
        - Compute per-pixel variance σ² over 32 frames (noise)
        - Take (μ, σ²) samples from the center 512×512 region
Step 5: Perform linear fit (OLS) on the (μ, σ²) data
        - Slope = α
        - Intercept = β
Step 6: Repeat for each ISO stop; build α(ISO), β(ISO) tables
```

**PTC Curve Feature Analysis**

| Region | Characteristic | Interpretation |
|--------|---------------|----------------|
| Linear region (5%–85% FW) | σ² = αs + β | Normal operating range |
| Pre-saturation hump | σ² decreases | Approaching full well; Poisson statistics break down |
| Y-intercept | β ≈ read noise² | ADC noise + thermal noise |

**Applications**: The calibrated (α, β) parameters are used for:
1. Noise estimation in classical denoising algorithms (BM3D, NLM)
2. Noise synthesis for DNN denoising training data
3. Optimal weight computation for HDR multi-frame fusion

---

## B.4 Recommended Calibration Automation Tools

| Tool | Function | Open Source | Platform |
|------|----------|-------------|----------|
| **Imatest** | Full-featured calibration (LSC/MTF/SNR/ΔE) | Commercial | Windows/Mac |
| **OpenImatest (MATLAB)** | Open-source LSC/CCM alternative | Open source | MATLAB |
| **colour-science Python** | AWB/CCM matrix computation | Open source | Python |
| **rawpy + NumPy** | BLC/LSC raw computation | Open source | Python |
| **Qualcomm CIQT** | Qualcomm platform full-chain calibration | Vendor tool | Android (Qualcomm) |
| **MTK CameraToolkit** | MTK platform calibration interface | Vendor tool | Android (MTK) |
| **OpenCV calibrateCamera** | Geometric calibration (checkerboard) | Open source | C++/Python |
| **dcraw / LibRaw** | RAW format decoding | Open source | Cross-platform |
| **ExifTool** | Metadata extraction (ISO/exposure/CCT) | Open source | Cross-platform |

**colour-science Python Example (CCM Computation)**

```python
import colour
import numpy as np

# Load ColorChecker D65 reference values (CIE Lab)
cc = colour.CCS_COLOURCHECKERS['ColorChecker 2005']
reference_XYZ = colour.colorimetry.sd_to_XYZ(
    cc.data, illuminant=colour.SDS_ILLUMINANTS['D65']
)

# Sensor measurements (linearized)
sensor_RGB = np.array([...])  # shape: (24, 3)

# Solve for CCM (3×3)
CCM = colour.characterisation.matrix_colour_correction_Finlayson2015(
    sensor_RGB, reference_XYZ
)
print("CCM:\n", CCM)

# Validate ΔE₀₀
corrected = sensor_RGB @ CCM.T
corrected_Lab = colour.XYZ_to_Lab(corrected)
reference_Lab = colour.XYZ_to_Lab(reference_XYZ)
delta_E = colour.delta_E(corrected_Lab, reference_Lab, method='CIE 2000')
print(f"Mean ΔE₀₀: {delta_E.mean():.3f}, Max ΔE₀₀: {delta_E.max():.3f}")
```

**rawpy + NumPy BLC Computation Example**

```python
import rawpy
import numpy as np

def compute_blc(raw_path, n_frames=16):
    """Compute four-channel BLC offsets"""
    frames = []
    for i in range(n_frames):
        with rawpy.imread(raw_path) as raw:
            # Extract raw Bayer data (unprocessed)
            bayer = raw.raw_image_visible.astype(np.float32)
            frames.append(bayer)

    # Median stacking for noise reduction
    stack = np.stack(frames, axis=0)
    median_frame = np.median(stack, axis=0)

    # Separate Bayer channels (RGGB pattern)
    R  = median_frame[0::2, 0::2]  # even row, even col
    Gr = median_frame[0::2, 1::2]  # even row, odd col
    Gb = median_frame[1::2, 0::2]  # odd row, even col
    B  = median_frame[1::2, 1::2]  # odd row, odd col

    blc = {
        'R':  float(np.median(R)),
        'Gr': float(np.median(Gr)),
        'Gb': float(np.median(Gb)),
        'B':  float(np.median(B)),
    }
    return blc
```

---

## B.5 Calibration Data Management Standards

### B.5.1 Version Naming Convention

```
{SensorModel}_{LensModel}_{CCT}_{ISO}_{Date}_v{Major}.{Minor}
Example: OV50H_Samsung_LN5_D65_ISO100_20260515_v1.2
```

Field descriptions:

| Field | Description | Example |
|-------|-------------|---------|
| SensorModel | Sensor model identifier | OV50H, IMX890, S5KJN1 |
| LensModel | Lens module model | Samsung_LN5, Largan_80211 |
| CCT | Calibration illuminant CCT | D65, D50, A, TL84 |
| ISO | Calibration ISO stop | ISO100, ISO800, AllISO |
| Date | Calibration date (YYYYMMDD) | 20260515 |
| Major.Minor | Version number | v1.0, v1.2, v2.0 |

### B.5.2 Directory Storage Structure

```
calibration_data/
├── blc/
│   ├── OV50H_Samsung_LN5_AllISO_20260515_v1.2.csv    # 2D BLC (ISO, T) table
│   └── OV50H_Samsung_LN5_LongExp_20260515_v1.0.csv   # Long-exposure BLC table
├── lsc/
│   ├── main_1x/
│   │   ├── OV50H_Samsung_LN5_D65_f1.8_20260515_v1.2.xml
│   │   ├── OV50H_Samsung_LN5_A_f1.8_20260515_v1.2.xml
│   │   └── OV50H_Samsung_LN5_D65_f2.8_20260515_v1.0.xml
│   ├── ultra_0.6x/
│   │   └── IMX563_Largan_D65_f2.2_20260515_v1.0.xml
│   └── tele_3.2x/
│       └── OV08A_Genius_D65_f2.8_20260515_v1.0.xml
├── awb/
│   ├── OV50H_Samsung_LN5_AllCCT_20260515_v1.2.xml    # CCT→(WB_R,WB_B) map
│   └── OV50H_Samsung_LN5_MixedLight_20260515_v1.0.json
├── ccm/
│   ├── OV50H_Samsung_LN5_D65_20260515_v1.2.txt       # 3×3 matrix
│   └── OV50H_Samsung_LN5_A_20260515_v1.2.txt
├── dpc/
│   ├── OV50H_SN001_DPCmap_20260515_v1.0.bin          # Per-unit defect map
│   └── OV50H_SN001_DPCmap_20260515_v1.0.csv          # Human-readable format
├── noise/
│   ├── OV50H_Samsung_LN5_PTC_AllISO_20260515_v1.0.csv # α(ISO), β(ISO) table
│   └── OV50H_Samsung_LN5_PTC_20260515_report.pdf      # PTC curve report
└── changelog.md  # Version change log
```

### B.5.3 Change Control Standards

**Golden Version Freeze Milestones**

| Project Phase | Calibration Data Status | Change Authorization |
|---------------|------------------------|---------------------|
| EVT (Engineering Verification Test) | Initial version; frequent updates allowed | Engineer direct modification |
| DVT-A (Design Verification Test A) | Feature-complete; changes require review | ISP lead approval required |
| DVT-B (Design Verification Test B) | Freeze candidate; bug fixes only | ECN process required |
| PVT (Production Verification Test) | **Frozen version**; modifications not permitted in principle | ECN + customer confirmation |
| MP (Mass Production) | **Production golden version**; absolutely no modification | ECN + multi-party sign-off |

**ECN (Engineering Change Notice) Template**

```
ECN-YYYYMMDD-NNN
Change description: LSC D65 f/1.8 gain table update
  (resolves corner luminance deficiency of 3%)
Affected module: LSC
Affected scope: Main 1x camera, all production lots
Previous version: OV50H_Samsung_LN5_D65_f1.8_20260501_v1.1
New version:      OV50H_Samsung_LN5_D65_f1.8_20260515_v1.2
Validation record: See attachment LSC_Validation_20260515.pdf
Approval signatures: [ISP Lead] [Optics Lead] [Test Lead]
```

### B.5.4 Calibration Data Quality Audit

Conduct periodic audits (quarterly) of calibration data, checking the following items:

```
Audit Checklist:
□ All production sensor models have corresponding calibration data
□ Calibration data version matches production ISP firmware version
□ DPC Map is individually calibrated per unit (not shared)
□ BLC table covers all ISO stops and temperature points
□ LSC table covers all focal length / aperture / CCT combinations
□ AWB table covers 2000K–8000K range
□ CCM has at least two sets: D65 and A illuminant
□ PTC noise parameters documented
□ changelog.md records all version changes
□ Backup stored in version control system (Git LFS)
```

---

## B.6 Platform Calibration Data Format Reference

### B.6.1 Qualcomm Chromatix Format

Qualcomm ISP uses the Chromatix XML format to store all calibration parameters. Key module-to-node mapping:

| Module | XML Node | Format Description |
|--------|----------|--------------------|
| BLC | `<black_level_correction>` | Four-channel offsets + temperature/ISO lookup table |
| LSC | `<lens_rolloff_config>` | 17×17 grid; 289 uint16 values per channel |
| AWB | `<awb_algo_config>` | Multi-illuminant gains + CCT range |
| CCM | `<color_correction_matrix>` | 3×3 float matrix with temperature interpolation |
| DPC | `<bad_pixel_correction>` | Static defect pixel coordinate list |

**LSC XML Example Fragment**

```xml
<lens_rolloff_config>
  <rolloff_table_size>17</rolloff_table_size>
  <r_gain type="float" length="289">
    1.862 1.744 1.632 1.534 1.453 1.389 1.341 1.307 1.291
    1.307 1.341 1.389 1.453 1.534 1.632 1.744 1.862
    <!-- ... 289 values total (17×17, row-major) ... -->
  </r_gain>
  <gr_gain type="float" length="289"> ... </gr_gain>
  <gb_gain type="float" length="289"> ... </gb_gain>
  <b_gain type="float" length="289">  ... </b_gain>
</lens_rolloff_config>
```

### B.6.2 MTK (MediaTek) NDD Format

MTK ISP uses the NDD (Native Device Driver) C header format to store calibration parameters.

**BLC NDD Format Example**

```c
// imx890_blc_table.h
typedef struct {
    uint16_t r_offset;
    uint16_t gr_offset;
    uint16_t gb_offset;
    uint16_t b_offset;
} BLC_ENTRY;

// ISO to BLC lookup table (6 ISO stops x 3 temperature points)
static const BLC_ENTRY blc_lut[3][6] = {
    // T = 10 degrees C
    { {64, 65, 65, 63}, {66, 67, 67, 65} },
    // T = 25 degrees C
    { {64, 65, 65, 63}, {67, 68, 68, 66} },
    // T = 45 degrees C
    { {65, 66, 66, 64}, {69, 70, 70, 68} },
};
```

### B.6.3 Samsung Exynos SEHF Format

Samsung Exynos ISP uses the SEHF (Samsung Exynos HAL Format) JSON format:

```json
{
  "calibration_version": "1.2",
  "sensor_id": "S5KHP3",
  "blc": {
    "r_offset": 64,
    "gr_offset": 65,
    "gb_offset": 65,
    "b_offset": 63,
    "iso_lut": [
      {"iso": 100,  "r": 64, "gr": 65, "gb": 65, "b": 63},
      {"iso": 400,  "r": 66, "gr": 67, "gb": 67, "b": 65},
      {"iso": 800,  "r": 68, "gr": 69, "gb": 69, "b": 67},
      {"iso": 1600, "r": 71, "gr": 72, "gb": 72, "b": 70},
      {"iso": 3200, "r": 75, "gr": 76, "gb": 76, "b": 74},
      {"iso": 6400, "r": 82, "gr": 83, "gb": 83, "b": 81}
    ]
  },
  "lsc": {
    "grid_size": 17,
    "r_gain":  [1.862, 1.744],
    "gr_gain": [1.523, 1.432],
    "gb_gain": [1.521, 1.430],
    "b_gain":  [1.901, 1.788]
  }
}
```

---

## B.7 Field Calibration Quick Reference

### B.7.1 Production-Line Calibration (ATE) Workflow

During mass production, calibration is performed automatically by ATE (Automatic Test Equipment), targeting < 30 seconds per module.

**Typical Production Calibration Sequence (Timing)**

```
T=0s    Load module; power on; initialize
T=3s    BLC dark-field capture (4 frames, light-blocked)
T=7s    LSC bright-field capture (4 frames, uniform light field)
T=12s   AWB reference capture (illuminant switching, 2×2 frames)
T=18s   OTP write (BLC + LSC + AWB gains)
T=22s   Readback verification (OTP CRC check)
T=25s   Unload module
Total:  approx. 25–30 seconds per unit
```

**Lab Calibration vs. Production-Line Calibration**

| Item | Lab Calibration | Production-Line Calibration |
|------|----------------|----------------------------|
| Frame count | 8–32 frames | 4–8 frames (speed priority) |
| Temperature control | Precise (±1°C) | Ambient (±5°C) |
| Illuminant accuracy | Standard source (±50 K) | LED simulation (±100 K) |
| Validation scope | Full validation | Key metrics quick check |
| Operator | Engineer | Operator (fully automated ATE) |

### B.7.2 OTP Data Structure

OTP (One-Time Programmable) memory is typically integrated into the camera module and stores per-unit calibration data.

**Typical OTP Map (by byte address)**

```
Address 0x0000–0x000F: Module info (manufacturer ID, sensor ID, date)
Address 0x0010–0x001F: BLC data (4 channels × 2 bytes = 8 bytes + CRC)
Address 0x0020–0x02FF: LSC data (17×17 × 4 channels × 2 bytes ≈ 2312 bytes)
Address 0x0300–0x030F: AWB data (WB_R, WB_B × 5 illuminants = 20 bytes)
Address 0x0310–0x031F: Module checksum (CRC-16)
```

**OTP Write Notes**

1. OTP is one-time write; write errors cannot be corrected — 100% verification is required before writing.
2. Compute CRC before writing; read back and compare after writing.
3. Some platforms support OTP partitioning, allowing new partition writes while preserving old data (Shadowing).

---

## References

1. **ISO 17321-1:2012** — Graphic technology and photography: Colour characterisation of digital still cameras (DSCs)
2. **IEC 62341-6-1** — Organic light emitting diode (OLED) displays: Measurement of optical and electro-optical parameters
3. **EMVA Standard 1288** (Edition 4.0, 2021) — Standard for characterisation and presentation of specifications for machine vision sensors and cameras
4. **X-Rite** ColorChecker reference dataset: https://www.xrite.com/service-support/new_colorchecker_color_standards
5. **colour-science** Python library documentation: https://colour.readthedocs.io/
6. **Imatest** documentation: https://www.imatest.com/docs/
7. **SMIA (Standard Mobile Imaging Architecture)** CCI register specification (MIPI Alliance)
8. For detailed algorithm derivations, see: Volume 2 Chapter 1 (BLC), Chapter 9 (LSC), Chapter 6 (AWB), Chapter 7 (CCM).
