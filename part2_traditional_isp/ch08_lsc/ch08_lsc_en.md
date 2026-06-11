# Part 2, Chapter 08: Lens Shading Correction (LSC)

> **Pipeline position:** After BLC/PDPC; before Demosaic
> **Prerequisites:** Chapter 2 (Optics), Chapter 3 (Sensor Physics)
> **Reader path:** Algorithm Engineer, System Designer

---

## §1 Theory

### 1.1 Vignetting: What It Is and Why It Happens

Vignetting is the gradual darkening of an image toward the corners and edges compared to the center. In a camera ISP pipeline, it manifests as a spatially nonuniform response on the sensor, even when the scene is perfectly uniform. Understanding its physical origin is essential before designing a correction strategy.

Three distinct physical mechanisms contribute to the observed shading:

#### (1) Natural Vignetting — the cos⁴θ Law

Natural vignetting is rooted in fundamental radiometry. For an ideal, aberration-free lens, the irradiance at a point on the image sensor located at field angle θ from the optical axis follows:

```
I(r) = I_center · cos⁴(θ)
```

where:
- `I_center` is the on-axis irradiance,
- `θ = arctan(r / f)` is the half-angle subtended at the exit pupil,
- `r` is the radial distance from the image center (in pixels or physical units),
- `f` is the effective focal length (in matching units).

The cos⁴ attenuation is the product of four separate geometric factors:
1. **cos θ** — reduced projected area of the pupil as seen from an off-axis point,
2. **cos θ** — oblique incidence on the sensor plane (Lambert's cosine law),
3. **cos² θ** — the r⁻² falloff of irradiance combined with the increased object-to-image distance for off-axis points.

At a typical wide-open aperture of f/1.8, a full-frame lens may exhibit 2–3 stops of corner falloff due to natural vignetting alone.

#### (2) Mechanical Vignetting

Mechanical vignetting arises when the barrel, aperture stop, or other physical elements of the lens mount physically block off-axis ray bundles. Unlike natural vignetting, this effect has a hard boundary and depends strongly on aperture:

- At wide apertures (small f-number), mechanical vignetting adds significantly to natural vignetting.
- Stopping down (larger f-number) reduces the cone angle of ray bundles, allowing them to pass through without obstruction.
- Mechanical vignetting typically creates a more abrupt spatial falloff profile than cos⁴θ.

#### (3) Pixel-Level (Micro-Lens) Vignetting

Modern CMOS sensors use per-pixel micro-lenses to concentrate incident light onto the photodiode. This optical element is designed for near-normal incidence. When light arrives at an oblique angle (as for off-axis pixels), the micro-lens focuses light partially outside the photodiode active area, causing additional signal loss.

This effect:
- Is more pronounced in sensors with small pixel pitch (where the acceptance cone is narrower),
- Differs between sensor generations and manufacturers,
- Is often lens-module dependent because the chief ray angle (CRA) profile of the lens must be matched to the sensor's micro-lens tilt design.

### 1.2 Combined Vignetting Model

In practice, all three mechanisms combine into a spatially nonuniform per-channel gain field. We model this as a 2D gain map `G(x, y, c)` per Bayer channel `c ∈ {R, Gr, Gb, B}`:

```
I_corrected(x, y, c) = I_raw(x, y, c) · G(x, y, c)
```

The gain map is defined such that `G(center, c) = 1.0` and `G(x, y, c) ≥ 1.0` everywhere (we are amplifying attenuated pixels back to their correct value).

### 1.3 Polynomial Radial Model

For lenses with near-rotationally symmetric vignetting, a polynomial in the normalized radial distance `r_norm` (where `r_norm = 1.0` at the image corner) provides a compact parameterization:

```
G(r_norm) = 1 + a·r_norm² + b·r_norm⁴ + c·r_norm⁶
```

- Coefficients `(a, b, c)` are fitted per channel from calibration data.
- The even-power-only polynomial reflects the symmetry of vignetting.
- Typically 3–4 terms are sufficient; higher-order terms fit noise rather than true shading.
- Storage cost: 3–4 floats per channel per aperture setting (extremely compact).

**Limitation:** Real vignetting is rarely perfectly radially symmetric, especially with decentered lenses or asymmetric mechanical obstructions. A mesh model is needed for such cases.

### 1.4 Mesh / LUT Model

The dominant representation in production ISPs is a 2D grid of correction gains, typically at a resolution of 16×16 or 32×32 nodes, with bilinear interpolation to reconstruct the full-resolution gain map at runtime.

```
G_full(x, y, c) = BilinearInterp( G_table[c], x_norm, y_norm )
```

where `x_norm = x / (W-1)` and `y_norm = y / (H-1)` map pixel coordinates into the unit square.

Advantages over polynomial model:
- Can represent arbitrary (non-radially-symmetric) shading,
- Hardware-friendly: table lookup + two-tap interpolation,
- Easily updated for different focal lengths or temperatures.

### 1.5 Illuminant Dependency

Vignetting is a purely physical-optical phenomenon, but in practice LSC tables must account for illuminant-dependent effects:

- **Mixed-source scenes:** If the ambient light source has a spatially nonuniform color temperature distribution (e.g., a window on one side), the "flat field" seen by the sensor is not truly flat in all channels.
- **Spectral response interaction:** The relative R/G/B gain differences across the field depend on the illuminant spectral power distribution interacting with the filter spectral transmittances.
- **AR coating effects:** Anti-reflection coatings on the lens may have angle-dependent transmittance that is spectrally nonuniform.

Consequence: production ISPs often carry multiple LSC tables — one for each dominant CCT (e.g., 2800 K, 4000 K, 6500 K) — and select or interpolate between them based on the AWB estimate.

---

## §2 Calibration

### 2.1 Flat Field Capture

The gold standard for LSC calibration is capturing a scene with known spatial uniformity:

**Integrating Sphere Output Port:**
- A sphere coated internally with high-reflectance diffuse paint, illuminated by calibrated lamps, produces a Lambertian output port with uniformity better than ±0.5%.
- Used for high-accuracy production calibration.

**Opal Glass Diffuser Lightbox:**
- A white opal glass panel backlit by a uniform array of LEDs.
- Achieves ±1–2% uniformity; acceptable for engineering calibration.

**Capture Conditions:**
- Defocus the lens slightly or place the diffuser very close; this blurs any texture or dust on the diffuser.
- Capture at multiple apertures: f/1.8, f/2.8, f/5.6. Vignetting is strongest wide open.
- Capture enough frames to average down noise (typically 16–64 frames).
- Ensure sensor is at operating temperature (thermal stabilization ≥ 5 min after power-on).

### 2.2 Per-Channel, Per-Aperture Table Generation

**Step 1 — Average Frames**

```python
flat = mean(frames, axis=0)   # shape: (H, W, channels) or raw Bayer
```

**Step 2 — Define the Reference Region**

Select a small central region (e.g., 64×64 pixels at image center) and compute its mean per channel:

```python
center_mean[c] = mean( flat[H//2-32:H//2+32, W//2-32:W//2+32, c] )
```

**Step 3 — Compute the Raw Gain Map**

```python
G_raw(x, y, c) = center_mean[c] / flat(x, y, c)
```

This inverts the attenuation: a pixel that received only 60% of center illuminance gets a gain of 1/0.6 ≈ 1.67.

**Step 4 — Smooth the Gain Map**

The raw gain map contains sensor noise and fixed-pattern noise. Amplifying this noise into the LSC table would degrade image quality. Apply a low-pass filter:

- **2D polynomial fit:** Fit `G_raw` per channel to the polynomial model `1 + a·r² + b·r⁴ + c·r⁶` using least squares. Guaranteed smooth but loses asymmetric shading.
- **Gaussian blur:** Apply a Gaussian filter with `σ ≈ H/20` to `G_raw`. Preserves spatial variation while suppressing noise.
- **Mesh downsampling:** Downsample `G_raw` to 16×16 by block-averaging; the reduced resolution itself acts as a low-pass filter.

**Step 5 — Clamp and Validate**

```python
G_table = clip(G_smooth, 1.0, MAX_GAIN)   # MAX_GAIN typically 4.0–8.0
```

Gains below 1.0 are physically incorrect (would darken already-bright pixels); gains above the maximum risk overflow or noise amplification.

### 2.3 Verification — Uniformity Measurement

Apply the table to the flat field and measure residual non-uniformity:

```
Uniformity = 1 - (max_region_mean - min_region_mean) / center_mean
```

Target: uniformity > 98% (< 2% corner-to-center deviation after correction).

If uniformity is not met, investigate:
- Insufficient frame averaging (increase frame count),
- Diffuser non-uniformity (re-characterize or replace diffuser),
- Smoothing too aggressive (reduce σ or polynomial order).

---

## §3 Tuning

### 3.1 Table Resolution

| Grid Size | Nodes | Memory (4 ch × float32) | Notes |
|-----------|-------|--------------------------|-------|
| 8×8       | 64    | 1 KB                     | Too coarse; visible banding on high-quality sensors |
| 16×16     | 256   | 4 KB                     | Standard; adequate for most lenses |
| 32×32     | 1024  | 16 KB                    | High accuracy; needed for complex shading profiles |
| 64×64     | 4096  | 64 KB                    | Overkill for most applications |

The minimum table size is set by the spatial frequency of the shading profile. For smooth cos⁴θ vignetting, 16×16 is more than sufficient. For lenses with mechanical vignetting features or sensor-level nonuniformity (column-level FPN), 32×32 may be warranted.

### 3.2 Smoothing Strength

The smoothing applied during calibration trades off between:
- **Too little smoothing:** Noise and PRNU (photo-response non-uniformity) from the calibration capture get embedded in the LSC table and are amplified in every subsequent capture.
- **Too much smoothing:** The table under-corrects spatial shading variations; residual shading remains visible.

Practical guideline:
- Smooth Gaussian σ: `H / 30` to `H / 15` (e.g., σ = 10–20 for a 512-row sensor).
- Verify post-smoothing uniformity is still ≥ 95% before reducing smoothing further.

### 3.3 Aperture and Focal Length Dependency

- **Multiple aperture tables:** Calibrate at the primary apertures of interest (typically wide open and mid-range). Most ISPs carry 1–3 tables and apply the most relevant one based on EXIF aperture or a fixed selection.
- **Zoom lenses:** Vignetting changes substantially across the zoom range. Store tables at several focal lengths and interpolate gain tables linearly in between.
- **Temperature:** For applications where thermal effects change sensor uniformity (e.g., automotive, industrial cameras operating at extreme temperatures), periodic re-calibration or temperature-compensated tables may be needed.

---

## §4 Artifacts

### 4.1 Over-Correction

**Symptom:** Corners appear brighter than the center after LSC; the image looks like a reverse vignette.

**Cause:** The LSC table gains are too large — typically because the flat field was captured in conditions that did not represent the actual lens–sensor combination (e.g., wrong aperture, wrong focus distance, or table from a different unit).

**Mitigation:**
- Always calibrate per lens–sensor unit (or at least per lens variant) rather than using a universal table.
- Clamp maximum gain to a physically reasonable value (e.g., 4.0 for wide-aperture lenses).

### 4.2 Noise Amplification

**Symptom:** Corners are noisier than the center even after LSC; the noise increase is disproportionate to the gain.

**Cause:** LSC gain at corners may be 2–4×. Since photon noise (shot noise) is proportional to `√signal`, amplifying a dark pixel's signal by 3× also amplifies its noise by 3×. The SNR at corners is fundamentally worse than at the center.

**Quantification:**
```
SNR_corner_after_LSC = SNR_corner_before_LSC / G_corner
```

For a typical corner gain of 2.5× and corner SNR of 20 dB before LSC, the corrected corner SNR is only 12 dB — a significant cost.

**Mitigation:**
- Apply stronger denoising to corners (spatially adaptive denoising aware of the LSC gain map).
- In low-light scenes, consider reducing LSC gain at corners to limit noise amplification.

### 4.3 LSC Table Mismatch (Residual Shading Ring)

**Symptom:** A ring pattern or gradual shading that varies with aperture; the correction is good at one aperture but poor at others.

**Cause:** Using an LSC table calibrated at one aperture for a scene captured at a different aperture. The mechanical vignetting component changes shape with aperture, so the residual mismatch appears as an annular artifact.

**Mitigation:** Calibrate and store separate tables per aperture; use metadata (EXIF) to select the correct table at capture time.

### 4.4 Banding from Low-Resolution Table

**Symptom:** Visible step artifacts, especially in smooth-toned areas like skies or uniform backgrounds.

**Cause:** A table resolution that is too low (e.g., 8×8) combined with bilinear interpolation creates a visible piecewise-linear gain profile. Bilinear interpolation ensures C⁰ continuity but not C¹ continuity (derivative is discontinuous at grid boundaries).

**Mitigation:**
- Increase table resolution to 16×16 or 32×32.
- Use bicubic or spline interpolation instead of bilinear (at cost of hardware complexity).
- Ensure the table values are smooth (well-calibrated flat field, adequate smoothing).

---

## §5 Evaluation

### 5.1 Corner-to-Center Uniformity Ratio

The primary metric for LSC quality:

```
Uniformity = (mean_corner_region) / (mean_center_region)
```

Computed per channel, before and after LSC. The target after correction is:
- Consumer cameras: > 95%
- Professional / industrial cameras: > 98%

### 5.2 Mean Absolute Deviation from Uniform

Divide the image into an N×N grid of patches (e.g., 8×8) and compute:

```
MAD = mean( |mean_patch(i,j) - mean_center| / mean_center )
```

This single number captures both corner and mid-field residual shading.

### 5.3 SNR Cost at Corners

Compare the noise standard deviation at the center vs. corners before and after LSC:

```python
noise_center = std( corrected[center_patch] )
noise_corner = std( corrected[corner_patch] )
snr_cost_dB  = 20 * log10( noise_corner / noise_center )
```

A well-calibrated LSC should have a SNR cost no greater than `20·log10(G_corner)` dB (the inevitable shot-noise cost from amplification). Excess SNR cost indicates noise embedded in the table.

### 5.4 Residual Shading Profile

Plot a horizontal and vertical cross-section through the corrected flat field and verify the profile is flat within the uniformity specification. A smooth residual curve indicates table inaccuracy; an oscillatory pattern indicates noise in the table.

---

## §6 Code

See *See §6 Code section for runnable examples.* for a full worked example including:
- Simulated flat field with cos⁴θ vignetting and per-channel color variation,
- LSC table estimation using Gaussian smoothing and grid downsampling,
- Correction and uniformity evaluation with before/after visualization,
- Noise cost analysis at corners.

---

## References

1. **cos⁴θ Vignetting Law:** Born, M. & Wolf, E. (2013). *Principles of Optics* (7th ed.), Chapter 4 — Geometrical Theory of Optical Imaging. Cambridge University Press.
2. **EMVA Standard 1288:** *Standard for Characterization of Image Sensors and Cameras*, Release 4.0, European Machine Vision Association. (Defines flat field measurement protocol and uniformity metrics.)
3. **Zheng, S., et al. (2009).** "Single-Image Vignetting Correction." *IEEE CVPR*. (Blind vignetting estimation from natural images.)
4. **Goldman, D. B. (2010).** "Vignette and Exposure Calibration and Compensation." *IEEE TPAMI*, 32(12), 2276–2288.
5. **Kang, S. B., & Weiss, R. (2000).** "Can we calibrate a camera using an image of a flat, textureless Lambertian surface?" *ECCV 2000*.
6. **MIPI Alliance (2022).** *Camera Module Calibration Guideline for Mobile Platforms.* (Industry practice for per-aperture, per-CCT LSC table storage in EEPROM.)
7. **Goldman, D. B., & Chen, J.-H. (2005).** "Vignette and exposure calibration and compensation." *IEEE ICCV 2005*, 899–906. (Journal version: *IEEE TPAMI*, 32(12):2276–2288, 2010.)
8. **Healey, G. E., & Kondepudy, R. (1994).** "Radiometric CCD camera calibration and noise estimation." *IEEE TPAMI*, 16(3), 267–276.
9. **Nakamura, J. (Ed.). (2006).** *Image Sensors and Signal Processing for Digital Still Cameras*, Chapter 4: Optical Performance. CRC Press.
10. **Qualcomm Technologies. (2023).** *Chromatix ISP Tuning Guide: Lens Shading Correction Module.* Qualcomm Developer Network.

---

## §1 Extended: Luma Shading vs. Color Shading

LSC addresses two distinct but interrelated problems that coexist in the same gain-map framework:

| Type | Root cause | Visual symptom | Correction approach |
|------|-----------|----------------|---------------------|
| **Luma Shading** | cos⁴θ natural vignetting, mechanical vignetting, micro-lens roll-off | Corners darker than center; single-channel brightness falloff | Multiply each channel by a spatially varying gain ≥ 1.0 to restore uniform brightness |
| **Color Shading** | Lateral chromatic aberration, CRA–micro-lens mismatch, spectrally dependent AR coating transmittance | Color fringing at corners/edges (cyan, magenta tint); center-to-edge hue shift | Correct all four Bayer channels (R, Gr, Gb, B) independently to remove inter-channel gain ratio differences |

**Why four independent gain maps are mandatory:**

Using a single gain map for all channels is a common shortcut whose consequence is that luma shading is removed but color fringing remains. The reason is straightforward: blue light diffracts more strongly at the lens edges, so the B channel attenuates differently from R. A shared map compensates brightness equally across channels but leaves the inter-channel ratio imbalance untouched — and that imbalance is precisely the source of color fringing.

Production ISP implementations therefore maintain **four independent gain grids**: `G_R(x,y)`, `G_Gr(x,y)`, `G_Gb(x,y)`, and `G_B(x,y)`, each applied to the corresponding Bayer plane:

```
I_corrected(x, y, c) = I_raw(x, y, c) · G_c(x, y)    # c ∈ {R, Gr, Gb, B}
```

A practical consequence of maintaining separate Gr and Gb maps is that green channel imbalance (a common cause of horizontal green/magenta banding) can be independently corrected — something impossible with a shared G map.

---

## §3 Extended: Platform Parameters and Multi-illuminant LSC

### 3.4 Three-Platform LSC Parameter Comparison

| Feature | Qualcomm CamX / Chromatix | MTK Imagiq / NDD | HiSilicon Ispv |
|---------|--------------------------|-----------------|----------------|
| Master enable | `LSC_Enable` (shared BPS module with PDPC) | `LSCEnabled` (NDD bool) | `LSC_Enable` |
| Mesh dimensions | `LSC_MeshGridWidth` / `LSC_MeshGridHeight` (typical: 17×13 or 13×10) | `LSCMeshWidth` / `LSCMeshHeight` (Dimensity supports up to 32×32) | `LSC_GridSize` |
| Gain LUT | `LSC_R_gain[m×n]`, `LSC_Gr_gain[m×n]`, `LSC_Gb_gain[m×n]`, `LSC_B_gain[m×n]` (float or Q8.8 fixed-point) | `LSCGainR[row][col]`, `LSCGainGr`, `LSCGainGb`, `LSCGainB` (Q4.12 fixed-point) | `LSC_GainTable_R/Gr/Gb/B` |
| CCT interpolation | `LSC_CCT_tables[]` (multi-illuminant LUTs interpolated by AWB CCT; Chromatix supports 5–8 CCT nodes) | `LSCIlluminantTable[N_CCT]` (NDD, up to 8 nodes) | `LSC_IlluminantGains[N]` |
| Maximum gain clamp | `LSC_MaxGain` (float, typical upper limit 3.5–4.0) | `LSCMaxGain` (NDD float, default 4.0) | `LSC_MaxGainClamp` |
| Interpolation method | Bilinear (between mesh nodes) | Bilinear | Bilinear + optional bicubic |
| Independent per-channel color shading | Yes (R/Gr/Gb/B independent LUTs) | Yes | Yes |
| Shading center auto-detection | `LSC_CenterX/CenterY` (fixed coordinates, written during factory calibration) | `LSCCenterEstimate` (bool; can estimate from flat field) | `LSC_AutoCenter` |

**Porting note:** Qualcomm `LSC_MaxGain` defaults to 3.5, while MTK defaults to 4.0. When migrating calibration data from MTK to Qualcomm, verify that corner gains do not exceed 3.5 and re-calibrate if necessary.

**Qualcomm Chromatix XML snippet (multi-illuminant, D65 node, R channel first row):**

```xml
<!-- chromatix_lsc34.xml -->
<lsc34_rgn_data>
  <r_gain_tab>
    <r_gain type="float" description="mesh gain, size: 17x13">
      1.82 1.78 1.72 1.66 1.61 1.57 1.54 1.53 1.54 1.57 1.61 1.66 1.72 1.78 1.82 1.85 1.87
      ...
    </r_gain>
  </r_gain_tab>
  <!-- Similar structure: Gr_gain_tab / Gb_gain_tab / B_gain_tab -->
  <cct_start>5500</cct_start>
  <cct_end>7500</cct_end>
</lsc34_rgn_data>
```

**MTK NDD snippet (Dimensity 9300, 16×12 mesh):**

```
[LSC]
LSCEnabled = 1
LSCMeshWidth = 16
LSCMeshHeight = 12
LSCMaxGain = 4.0
# D65 R-channel gain table (row-major, 16 cols × 12 rows = 192 values)
LSCGainR_D65 = 1.76 1.72 1.68 ... (192 values total)
LSCGainGr_D65 = 1.00 1.00 1.00 ...
LSCGainGb_D65 = 1.00 1.00 1.00 ...
LSCGainB_D65 = 1.55 1.51 1.47 ...
# Tungsten (2800K)
LSCGainR_A   = 1.92 1.88 1.83 ...
LSCGainB_A   = 1.30 1.27 1.24 ...
```

### 3.5 Multi-Illuminant LSC and CCT Interpolation

Production ISPs carry multiple LSC gain-map sets keyed by Correlated Color Temperature (CCT) — typically 3–8 nodes spanning 2800 K (tungsten) through 6500 K (daylight) — and interpolate between adjacent nodes using the AWB color-temperature estimate:

```
G_applied(x, y, c) = lerp(G_low[x,y,c], G_high[x,y,c], t)
where  t = (CCT_awb - CCT_low) / (CCT_high - CCT_low)
```

**Spectral dimension limitation:** CCT alone is not a unique identifier of a light source's spectral power distribution (SPD). Two sources with the same CCT (e.g., cool-white LED and D65 daylight) may differ in their blue-peak energy by 3–5%, causing the B-channel edge attenuation to differ measurably. Best practice is to calibrate separate LSC tables for spectrally distinct sources at the same nominal CCT (LED vs. fluorescent vs. daylight), and use the AWB light-source-type classification to select among them.

### 3.6 Dynamic LSC: Zoom-Dependent Gain Map Switching

For optical zoom lenses, vignetting changes substantially across the focal-length range. The standard approach:

1. Calibrate independent gain maps at several focal-length nodes (e.g., 24 mm / 50 mm / 105 mm equivalent).
2. At runtime, read the focal length from lens metadata (EXIF or OIS controller) and linearly interpolate between the two bracketing gain maps:

```python
t = (focal_mm - focal_lo) / (focal_hi - focal_lo)
G_applied = (1 - t) * G_table_lo + t * G_table_hi
```

3. Ensure adjacent gain-map nodes have monotonically varying corner values (no gain jumps); a gain change exceeding 0.05 per CCT or focal-length node is a calibration quality warning.

### 3.7 LSC and AWB Execution Order

**LSC executes before AWB** — this ordering is universal across Qualcomm Spectra, MTK Imagiq, and HiSilicon ISPs (BLC → LSC → AWB → Demosaic → CCM). The rationale and engineering consequences are significant.

**Why ordering matters:**

AWB statistics are collected over the full sensor field. If LSC were applied after AWB (incorrect order), the raw pixels presented to the AWB estimator would contain the vignetting attenuation: corners are darker than center, and each channel attenuates differently. This biases the white-point estimate.

| Ordering | AWB behavior | Observable symptom |
|---------|-------------|-------------------|
| LSC **before** AWB (correct) | AWB statistics reflect a vignetting-compensated uniform field; white-point estimate is unbiased | Consistent color temperature across the full frame |
| LSC **after** AWB (incorrect) | AWB statistics contain vignetting; darker, cooler corner pixels pull the white-point estimate | Center-to-edge color inconsistency; cyan or magenta tinting at frame edges that varies with aperture and focal length |

**Calibration implication:** Because LSC precedes AWB, the gain tables are calibrated in the pre-AWB sensor color space. The tables therefore encode both luma correction and color shading correction simultaneously, in the domain before any AWB gain is applied.

**Feedback loop for multi-illuminant LSC:**

The AWB color-temperature output feeds back to the LSC module to select or interpolate the correct gain table for the *next* frame:

```
Sensor RAW
  → BLC
  → LSC (using gain table interpolated from previous frame's AWB CCT)
  → AWB statistics (compute current frame CCT) → feed to next frame LSC selection
  → Demosaic / CCM / ...
```

After changing an LSC gain table (e.g., following re-calibration for a new lens), always re-verify AWB convergence accuracy across CCT conditions, especially edge-region color error (shoot a neutral gray card; verify center-vs.-corner ΔE₀₀ < 1.5).

---

## §7 Glossary

**Lens Shading Correction (LSC)**
An ISP module that compensates for the spatially nonuniform pixel response of a camera sensor. Encompasses both luma shading (corners darker than center) and color shading (per-channel gain ratio variation across the field). Implemented as four independent gain grids for Bayer channels R, Gr, Gb, B; applied after BLC and before demosaicing.

**Natural Vignetting (cos⁴θ Law)**
In an ideal optical system, the irradiance at a sensor location at off-axis angle θ follows I(θ) = I_center · cos⁴θ. The four-power attenuation arises from four independent cos θ factors: (1) reduced projected pupil area, (2) oblique incidence (Lambert cosine), (3)(4) increased object-to-image distance causing solid-angle reduction. At f/1.8 wide aperture, corner falloff from natural vignetting alone typically reaches 1–3 stops.

**Mechanical Vignetting**
Additional light blockage caused by the lens barrel, aperture stop, or mounting hardware physically intercepting off-axis ray bundles. Unlike natural vignetting, mechanical vignetting has a hard spatial boundary and is strongly aperture-dependent: it diminishes when the aperture is stopped down (smaller cone angle avoids obstruction). Mechanical vignetting is the primary reason observed corner falloff exceeds pure cos⁴θ predictions at wide apertures.

**Chief Ray Angle (CRA)**
The angle between the chief ray (the ray passing through the center of the pupil) at a given image point and the sensor normal. Sensor micro-lenses are optimized for a specific CRA profile; when the lens CRA does not match the sensor design CRA, off-axis pixels suffer additional signal loss (pixel-level vignetting) and color shading. High-end modules measure and write the CRA curve to EEPROM for use during LSC calibration.

**Flat Field Calibration**
The standard method for generating LSC gain tables: capture multiple frames of a spatially uniform illumination source (integrating sphere or opal glass lightbox), average them to suppress noise, and compute the normalized gain G(x,y,c) = center_mean[c] / flat(x,y,c) (with black level subtracted first). Typically 16–64 frames are averaged; the result is smoothed and downsampled to the target mesh resolution.

**Radial Polynomial LSC Model**
A compact parameterization for nearly rotationally symmetric vignetting: G(r_norm) = 1 + a·r_norm² + b·r_norm⁴ + c·r_norm⁶, where r_norm = 1 at the image corner. Only even-power terms are used because vignetting depends on off-axis distance, not direction. Advantages: minimal storage (3–4 coefficients per channel). Limitation: cannot represent asymmetric shading caused by decentered elements, column-level FPN, or mechanical obstructions.

**Mesh / 2D Grid LUT Model**
The dominant LSC representation in production ISPs: correction gains stored at a sparse grid of nodes (typically 16×16 or 32×32), with bilinear interpolation used to reconstruct the full-resolution gain map at runtime. A 16×16 grid for 4 channels in float32 occupies 4 KiB; a 32×32 grid occupies 16 KiB. Can represent arbitrary non-symmetric shading; hardware-friendly (table lookup + bilinear interpolation).

**LSC Noise Amplification Cost**
LSC multiplicative gain amplifies both signal and noise equally, so the SNR at a given pixel location is unchanged by the LSC operation itself. However, corner pixels originally received fewer photons (by factor G) than center pixels, so their intrinsic SNR is lower. After LSC brings corner brightness to parity with the center:
- Read-noise dominated: SNR_corner = SNR_center / G
- Shot-noise dominated: SNR_corner = SNR_center / √G

This is an irreducible SNR penalty arising from optical vignetting. Mitigation: apply spatially adaptive denoising that is aware of the LSC gain map and applies stronger smoothing in high-gain (corner) regions.

**Uniformity (Acceptance Metric)**
Primary quantitative metric for LSC correction quality: Uniformity = 1 − (max_region_mean − min_region_mean) / center_mean. Targets: consumer cameras > 95%; professional/industrial cameras > 98%. Mean Absolute Deviation (MAD) across an N×N patch grid serves as a complementary full-field quality indicator.

**Color Shading**
Spatially varying inter-channel gain ratio differences caused by lateral chromatic aberration, CRA–micro-lens mismatch, and spectrally dependent lens coating transmittance. Manifests as color fringing at frame edges (cyan or magenta tint at corners). Requires four independent gain tables (R, Gr, Gb, B); a single shared gain map can correct luma shading but leaves color shading unaddressed. Gr/Gb gain ratio exceeding 1.03 typically produces visible horizontal green/magenta banding.

**CCT-Interpolated LSC**
Production ISPs carry multiple gain-map sets indexed by Correlated Color Temperature (CCT). The AWB module's CCT estimate selects or interpolates between neighboring nodes. Inter-node gain change should be smooth (≤ 0.05 per node) to avoid visible vignetting jumps during light-source transitions.

**DL-Based Self-Calibration LSC**
Emerging research direction: estimating the LSC gain map from ordinary video frames (without a dedicated flat-field capture) using deep learning models that distinguish scene content from spatially smooth lens shading. Representative work: Zheng et al. (2009) for blind parametric estimation; recent video-based methods (2022–2024) learn shading priors from large image datasets and achieve < 2% residual non-uniformity without a calibration chart.

---

## §8 Engineering Recommendations

Calibration quality determines the ceiling of LSC performance. The gain map itself is just a lookup table; the genuine engineering challenge is acquiring and validating a truly uniform flat field.

| Scenario | Recommended approach | Typical constraints | Notes |
|---------|---------------------|--------------------|----|
| Mobile single-camera (fixed focal length) | Integrating sphere + 17×13 mesh, 4 independent channels, 3 CCT nodes | Source uniformity ±0.5%; MAX_GAIN ≤ 3.5 | Must calibrate per module in mass production; sharing calibration data across units is not acceptable |
| Mobile multi-camera (ultra-wide / main / tele) | Calibrate each lens independently; store separate gain tables | Module CRA differs; tables are not cross-compatible | When switching cameras, simultaneously switch LSC table to avoid corner color jump |
| Optical zoom lens | Calibrate at several focal-length nodes (e.g., 24/50/105 mm equiv.); interpolate gain tables linearly at runtime | Inter-node gain variation must be monotonically smooth | Large interpolation steps leave residual vignetting rings |
| Automotive / high-temperature industrial | Calibrate at ambient and high temperature (80–120°C); switch table via temperature sensor | Thermal expansion shifts corner gains by ~2–5% | Consumer phones typically do not need this; temperature rise during prolonged 4K video is <15°C with adequate design margin |
| Low-cost / rapid prototyping | LED lightbox (opal glass) + 16×16 mesh + 32-frame average | Uniformity ±1–2%; slightly lower accuracy than integrating sphere | Acceptable for engineering validation; switch to integrating sphere for production |

**Key debugging rules:**

1. **Validate the light source before calibrating the lens.** Before shooting the calibration frame, use a known-good reference camera to image the same light field and confirm spatial uniformity. If the source corners are more than 2% darker than the center, subtract that non-uniformity from the LSC measurement; otherwise the source error gets frozen into the gain table.

2. **All gain values must be ≥ 1.0 everywhere.** After calibration, inspect all four channel gain maps. Any position with gain < 1.0 means that pixel is brighter than center — a sign of source non-uniformity or incorrect focus position. Do not silently clamp these values to 1.0; re-acquire the calibration data.

3. **Verify corner-to-center gain ratio plausibility.** For a typical f/1.8 mobile lens, corner R-channel gain is approximately 1.6–2.2; extreme wide-angle lenses can reach 3.0. If corner gain exceeds MAX_GAIN and is clipped, the corrected corner will still be darker than center. Either reduce the MAX_GAIN clamp ceiling or revisit the lens aperture operating point.

4. **Green-channel imbalance check.** Gr/Gb gain ratio > 1.03 anywhere in the frame will produce visible horizontal green/magenta banding in uniform areas. Always calibrate Gr and Gb as separate channels; never merge them into a single G channel.

5. **After any LSC table change, re-validate AWB.** Because LSC runs before AWB in the pipeline, changes to the gain tables alter the statistics visible to the AWB estimator. Confirm that AWB converges correctly across CCT conditions and that center-vs.-corner ΔE₀₀ remains < 1.5 on a neutral gray card.

**When simplified calibration is acceptable:**

In rapid-prototype phases (algorithm validation, not final IQ tuning), when corner falloff is small (< 5%), or when downstream software compensation (e.g., RAW-domain AI de-vignetting) is applied, a radial polynomial model (3–4 coefficients per channel) is sufficient and saves significant production-line calibration time.

> **Engineer's note:** Most LSC problems are calibration problems, not algorithm problems. The gain map is just arithmetic. Non-uniform light sources, mismatched aperture conditions, insufficient frame averaging, and cross-unit table sharing account for the vast majority of field failures. Invest in the calibration setup, not in a more sophisticated interpolation algorithm.
