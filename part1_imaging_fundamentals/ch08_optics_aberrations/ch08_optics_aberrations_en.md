# Part 1, Chapter 08: Optics Aberrations, Lens Characterization & Calibration Light Sources

> **Pipeline position:** The optical system precedes the sensor; understanding aberrations underpins the design of LSC, CAC, and distortion correction ISP modules
> **Prerequisites:** Chapter 02 (Optics Basics), Chapter 03 (Image Sensor Physics)
> **Reader path:** Algorithm Engineers, Optical Engineers, Calibration Engineers

---

## §1 Theory

### 1.1 Geometric Aberrations (Seidel 5)

The Seidel aberrations — named after Ludwig von Seidel — are the five primary monochromatic aberrations arising from third-order (paraxial) optics theory. Each degrades image quality in a distinct spatial pattern and requires a different correction strategy inside the ISP.

#### 1.1.1 Spherical Aberration

**Definition:** Rays passing through different annular zones of the lens converge at different focal distances along the optical axis. Marginal rays (passing near the lens edge) focus closer to the lens than paraxial rays (passing near the center), creating a rotationally symmetric blur.

**ISP relevance:** Spherical aberration manifests as a soft, hazy center in full-aperture captures. It is not spatially variant in the radial sense beyond the central field, making it difficult to correct with a simple position-dependent filter. Deconvolution-based sharpening (e.g., Wiener filter or DNN-based restoration) can partially compensate if the PSF is characterized.

**Mitigation:** Optical design uses aspherical lens elements to reduce spherical aberration. In ISP, adaptive sharpening with a spatially varying PSF model is the primary correction path.

#### 1.1.2 Coma

**Definition:** Off-axis point sources produce comet-shaped blur rather than a circular PSF. The shape arises because rays through different lens zones form different-sized circles whose centers are displaced, stacking into a characteristic flare tail pointing toward or away from the optical axis.

**ISP relevance:** Coma is most visible near corners and edges of the frame. It is particularly problematic for astrophotography and night-mode captures where point-like light sources appear at large field angles. Coma is field-angle dependent and cannot be corrected by LSC alone.

**Mitigation:** Advanced lens designs use symmetric elements or field flatteners. ISP-side correction requires spatially variant PSF deconvolution, which is computationally expensive for real-time pipelines.

#### 1.1.3 Astigmatism

**Definition:** A point source away from the optical axis is imaged as two separate line foci (tangential and sagittal) at different depths, with a circle of least confusion between them. The two line orientations are perpendicular to each other.

**ISP relevance:** Astigmatism causes directional blurring that varies with field position. Horizontal structures may appear sharper than vertical ones (or vice versa) at the same image location. This directional MTF drop is measurable with oriented test targets.

**Mitigation:** Lens design corrections use separated meniscus elements. No standard ISP module directly corrects astigmatism; it contributes to the position-dependent MTF degradation that motivates spatially adaptive sharpening.

#### 1.1.4 Field Curvature (Petzval Curvature)

**Definition:** The ideal image plane of a real lens is not flat but curved (the Petzval surface). When a flat sensor is placed at the paraxial focus, objects at the field edges are defocused even if the center is sharp.

**ISP relevance:** Field curvature causes a characteristic center-sharp / corner-soft pattern that cannot be fixed by focus alone. On mobile camera lenses with tight telephoto designs, field curvature can be a dominant performance limiter. The effect couples with depth-of-field: at small apertures, diffraction softens the center while field curvature softens corners, resulting in relatively uniform but low overall sharpness.

**Mitigation:** Optical design uses field-flattening elements. ISP may apply spatially varying sharpening with stronger enhancement at corners to partially compensate for the perceived softness, though this amplifies noise as well.

#### 1.1.5 Distortion

**Definition:** Distortion does not blur the image but displaces off-axis image points radially. Barrel distortion moves points inward (the square pincushions); pincushion distortion moves points outward (the square barrels outward). The displacement follows a polynomial relationship with field angle.

**ISP relevance:** Distortion correction is a standard ISP module present in virtually all smartphone pipelines. The correction maps each output pixel position to the corresponding (fractional) input position using the inverse distortion polynomial, followed by bilinear or bicubic interpolation.

Correction model (radial polynomial):

```
r_corrected = r_distorted * (1 + k1*r² + k2*r⁴ + k3*r⁶)
```

Ultra-wide-angle (UWA) lenses typically exhibit >10% barrel distortion before correction. Post-correction, field of view is slightly cropped.

**Mitigation:** Geometric distortion calibration using a checkerboard grid target is performed during lens characterization. The polynomial coefficients are stored as lens parameters and applied in the ISP distortion correction block.

---

### 1.2 Chromatic Aberration

Chromatic aberration (CA) arises because the refractive index of glass is wavelength-dependent (dispersion). It manifests in two distinct forms with different spatial signatures and ISP correction approaches.

#### 1.2.1 Longitudinal (Axial) Chromatic Aberration

**Definition:** Different wavelengths focus at different distances along the optical axis. Red light may focus behind the sensor plane while blue light focuses in front of it, with green focusing close to the nominal plane.

**ISP relevance:** Longitudinal CA creates colored halos around high-contrast edges across the entire image field — it does not have a center-exempt zone. Out-of-focus red or blue fringing appears on both sides of sharp edges depending on the sign of defocus for each channel. This is the dominant component of "purple fringing" (see §4).

**Mitigation:** Optical design uses achromatic doublets (crown + flint glass pairs) or apochromatic triplets to bring two or three wavelengths to a common focus. ISP correction is limited because longitudinal CA creates a channel-dependent defocus (MTF degradation), not a simple lateral shift.

#### 1.2.2 Transverse (Lateral) Chromatic Aberration

**Definition:** Different wavelengths form images at slightly different magnifications. The result is a lateral displacement between color channels that increases with distance from the image center. At the center (on-axis), lateral CA is zero by symmetry.

**ISP relevance:** Lateral CA is the primary target of the ISP Chromatic Aberration Correction Filter (CACF). It manifests as colored fringing at high-contrast edges near the image corners and periphery. Green is typically chosen as the reference channel (being most sensitive to the human visual system), and R and B channels are shifted or warped to align with G.

**Correction model (sub-pixel R/B shift relative to G):**

```
x_R_corrected = x_R + (ΔxR_lateral(r))
y_R_corrected = y_R + (ΔyR_lateral(r))
```

The lateral shift is radially symmetric for ideal lenses and can be modeled as a polynomial of the normalized radial distance r from the image center. For higher accuracy, a 2D grid-based warp map is used.

**Typical values:** On a flagship smartphone camera, lateral CA at the extreme corner is 0.3–0.8 pixels before CACF correction. Post-correction target is < 0.3 pixels.

---

### 1.3 MTF and the Diffraction Limit

#### 1.3.1 MTF Definition

The Modulation Transfer Function (MTF) quantifies how faithfully a lens (or entire imaging system) reproduces spatial contrast at different spatial frequencies. It is defined as:

```
MTF(f) = M_output(f) / M_input(f)
```

where M = (I_max - I_min) / (I_max + I_min) is the modulation (contrast) of a sinusoidal pattern at spatial frequency f. MTF = 1.0 means perfect contrast reproduction; MTF = 0 means the frequency is unresolved.

Key MTF metrics:
- **MTF50:** spatial frequency at which MTF drops to 50% of its low-frequency value (cy/pixel or lp/mm). Primary sharpness metric.
- **MTF10:** approximate resolution limit (Rayleigh-like criterion).
- **Spatial frequency normalization:** cycles/pixel (cy/pix) is sensor-independent; lp/mm depends on sensor pixel pitch.

#### 1.3.2 Diffraction-Limited MTF

For a diffraction-limited circular aperture, the OTF is real and non-negative, giving the MTF as:

```
MTF_diff(f) = (2/π) * [arccos(f/f_co) - (f/f_co)*sqrt(1-(f/f_co)²)]
```

where the incoherent cutoff frequency is:

```
f_co = 1 / (λ * f/#)     [cycles/mm]
```

or in normalized cycles/pixel:

```
f_co_normalized = p / (λ * f/#)
```

with p = pixel pitch (mm), λ = wavelength (mm), f/# = lens f-number.

**Practical implication:** A lens operating at f/2.0 with p = 0.8 µm pixel pitch and λ = 550 nm has f_co ≈ 0.73 cy/pix. The Nyquist limit is 0.5 cy/pix, so diffraction does not limit resolution at f/2.0 for this pixel size. At f/5.6, f_co ≈ 0.26 cy/pix — below Nyquist — so diffraction softening becomes the dominant image quality limiter (see §4, Diffraction Softening).

#### 1.3.3 ISO 12233 Slanted Edge Method

The slanted edge method (standardized in ISO 12233) provides a practical, low-noise MTF measurement from a single image capture.

**Procedure:**
1. Capture a test chart with a high-contrast straight edge tilted 5–10 degrees from the sensor column direction.
2. Extract the Edge Spread Function (ESF): sample pixel values along lines perpendicular to the edge, aligning each row to the sub-pixel edge position. This oversamples the edge by the number of rows used.
3. Differentiate the ESF to obtain the Line Spread Function (LSF).
4. Apply a Hamming or Hann window to the LSF to reduce spectral leakage.
5. Take the absolute value of the Fourier Transform of the windowed LSF to obtain the MTF.

**Mathematical chain:**

```
Chart edge --> ESF(x) --> LSF(x) = dESF/dx --> MTF(f) = |FFT{LSF}| / |FFT{LSF}|_{f=0}
```

**Tools:**
- **Imatest SFR (Spatial Frequency Response):** Industry-standard commercial tool. Outputs MTF50, MTF50P, MTF10, SFR curves, CA, noise, and lens uniformity reports. Reference: https://www.imatest.com/docs/sfr/
- **MTFMapper:** Open-source tool by Frans van den Bergh, suitable for measuring MTF at multiple edge locations in a grid target simultaneously. Reference: https://sourceforge.net/projects/mtfmapper/

---

### 1.4 Vignetting Types

Vignetting is the reduction of image brightness toward the periphery of the frame. Multiple physical mechanisms produce vignetting, and they differ in their angular dependence and correction approach.

#### 1.4.1 Natural (Optical) Vignetting — cos⁴θ Law

For an ideal lens with a circular aperture, the irradiance at a field angle θ from the optical axis falls as:

```
E(θ) = E(0) * cos⁴(θ)
```

This arises from three cos(θ) factors: projected aperture area (cos θ), obliquity of the chief ray to the image plane (cos θ), and the increased image distance for off-axis points (cos²θ from the inverse-square law). For a field angle of 30°, the natural vignetting is cos⁴(30°) ≈ 0.56, meaning a 44% brightness drop at the corners — before any mechanical obstruction.

#### 1.4.2 Mechanical Vignetting

Physical elements — lens barrel walls, aperture stops, baffles — obstruct the cone of rays reaching off-axis image points. Unlike natural vignetting, mechanical vignetting can cause a hard cutoff in the pupil function and is more pronounced at wide apertures. It is reduced by stopping down the lens.

#### 1.4.3 Pixel/CRA Mismatch (Chief Ray Angle Mismatch)

Modern CMOS sensors have microlens arrays optimized for a specific chief ray angle (CRA) profile, typically matched to the intended camera module lens. When the CRA of the optical system does not match the sensor's microlens CRA design, off-axis pixels suffer reduced light collection efficiency. This is effectively a pixel-level vignetting that depends on the micro-optics rather than the macro-optics.

Cross-reference: Chapter 03 (Image Sensor Physics) — microlens array design and CRA specifications.

This type of vignetting is fixed for a given lens-sensor combination and is corrected by the same LSC gain map, but it cannot be removed by changing the aperture.

#### 1.4.4 Artistic Vignetting

Intentional darkening of the image periphery is applied in post-processing or in-camera as a stylistic choice, emulating the look of vintage photographic lenses. This is a separate ISP aesthetic processing step and is not a defect to be corrected.

---

### 1.5 Calibration Light Sources

Accurate characterization of camera systems requires controlled, spectrally defined illumination. The choice of light source directly impacts the validity of calibration results for AWB, CCM, LSC, and noise characterization.

#### 1.5.1 CIE Standard Illuminants

The CIE (International Commission on Illumination) defines standard illuminants as reference spectral power distributions (SPDs) for colorimetric and photometric calculations.

| Illuminant | CCT (K) | Primary Application in ISP Calibration |
|---|---|---|
| D65 | 6504 | Primary AWB reference, CCM fitting, display white point standard |
| D50 | 5003 | Print/prepress color matching, ICC profile reference |
| A | 2856 | Tungsten lamp simulation, indoor warm-light AWB testing |
| F2 / CWF | 4230 | Cool white fluorescent; North American retail environment |
| F11 / TL84 | 3992 | Narrow-band tri-phosphor fluorescent; European retail standard |
| F12 / TL83 | 3000 | Warm white fluorescent; used in DXO color testing |

D-illuminants (D65, D50) are phase-correlated daylight reconstructions based on actual measured daylight SPDs. They contain UV content, which is important for fluorescent sample excitation during color calibration. Physical D65 simulators are graded by CIE 51-1981 quality categories (A, B, C, D, E).

F-series illuminants represent measured fluorescent lamp SPDs and are important because fluorescent lighting introduces narrow-band spectral spikes that stress AWB and CCM algorithms.

#### 1.5.2 Integrating Sphere Light Sources

**Principle:** An integrating sphere is a hollow sphere coated internally with a highly reflective Lambertian material (typically barium sulfate or PTFE-based coatings, reflectance > 99%). A light source inside the sphere undergoes multiple diffuse reflections, and the output at any aperture port is spatially and angularly uniform Lambertian radiance, independent of the input source position.

**Applications in ISP calibration:**
- **LSC gain map capture:** The sphere output provides a near-perfect flat-field illuminant. Capturing a RAW image of the sphere aperture reveals only the optical vignetting and pixel response non-uniformity (PRNU) of the camera system.
- **PRNU measurement:** Photo-Response Non-Uniformity characterization requires uniform illumination; integrating spheres are the standard tool.
- **QE measurement:** Quantum Efficiency spectral response measurements use monochromatic output from a sphere fed by a monochromator.

**Key specifications:**
- Aperture size: must be large enough to overfill the camera field of view (typically 200–600 mm diameter for smartphone module testing)
- Spatial uniformity: > 98% across the aperture (some high-end spheres achieve > 99.5%)
- CCT programmability: via adjustable current or multi-lamp configurations
- Spectral power distribution: must be characterized and traceable to national standards (NIST/NIM)

**Major suppliers:**

- **Yanding Instruments (研鼎仪器, Shenzhen):** A leading Chinese supplier of integrating sphere systems and camera module testing equipment specifically for the smartphone industry. Serves Xiaomi, OPPO, vivo, and their component supply chains. Website: www.yanding.com
- **Zhengyin (正印, Shenzhen):** Specializes in factory-line camera calibration equipment for high-throughput production environments, including integrating sphere flat-field stations and multi-step calibration lines.
- **Everfine (杭州远方光电, Hangzhou):** China's leading manufacturer of spectroradiometers and light source calibration instruments. Provides sphere sources with traceable SPD characterization. Website: www.everfine.net
- **Labsphere (USA):** International benchmark for integrating sphere design. Manufactures the CSTM-LED series and custom sphere sources for laboratory and production use.
- **Gamma Scientific (USA):** Supplies integrating sphere sources and spectroradiometer systems for camera and display characterization.
- **Instrument Systems (Germany):** Known for high-accuracy spectroradiometers (CAS series) and light source calibration systems used in European automotive and consumer electronics testing labs.

#### 1.5.3 Multi-Illuminant Switching Cabinets

For AWB algorithm development and validation, it is necessary to capture test targets (typically X-Rite ColorChecker) under multiple, well-defined illuminants and measure the camera's color error under each.

**Design:** A motorized switching mechanism cycles through multiple fluorescent or LED lamp assemblies, each with a different SPD. The camera and test chart remain stationary; only the illuminant changes. Baffles prevent cross-illumination between sources.

**Standard illuminant set for smartphone AWB testing:**
- D65 (daylight reference)
- A (tungsten, 2856 K)
- TL84 / F11 (European fluorescent)
- F12 / TL83 (warm fluorescent)
- CWF / F2 (North American cool white)

**DXO Mark color testing standard:**
DXO Mark uses a standardized multi-illuminant test protocol. The color score requires the camera's AWB to achieve ΔE₀₀ < 3.0 under each tested illuminant condition. The ΔE₀₀ threshold of 3.0 corresponds to a just-noticeable color difference under critical viewing, representing a pass/fail criterion for commercial smartphone performance.

Reference: https://www.dxomark.com/methodology/

#### 1.5.4 Programmable Light Sources (PLS)

Programmable light sources represent the state-of-the-art in tunable illuminant technology for camera calibration. They use arrays of narrow-band LEDs with independently controllable drive currents to synthesize arbitrary target SPDs.

**Principle of SPD synthesis:**

The output SPD S(λ) is a weighted sum of individual LED channel basis functions:

```
S(λ) = Σᵢ wᵢ · φᵢ(λ)
```

where φᵢ(λ) is the measured SPD of the i-th LED channel at unit drive current, and wᵢ ≥ 0 is the drive weight. The weights are solved for a target SPD T(λ) using Non-Negative Least Squares (NNLS):

```
minimize ||Φw - T||²₂   subject to   w ≥ 0
```

where Φ is the matrix of column-stacked channel SPDs.

**Channel configurations and capabilities:**

| Channel Count | Best-suited Approximations | Typical Application |
|---|---|---|
| 8-channel | Smooth blackbody / daylight SPDs | AWB CCT sweep (2000–8000 K) |
| 12–16-channel | Fluorescent lamp approximation | CCM robustness testing |
| 19–24-channel | Hyperspectral research targets | Metamerism index evaluation |

**Applications in ISP development:**
- **AWB locus sweep:** Generate illuminants continuously from 2000 K to 8000 K to map the camera's AWB Planckian tracking performance and find color constancy failure zones.
- **CCM robustness testing:** Verify that a CCM trained on D65/A/TL84 generalizes to unusual intermediate illuminants.
- **Stress testing:** Generate illuminants with strong narrow-band spikes (simulating exotic retail or industrial lighting) to stress-test AWB and auto-color algorithms.
- **Ground-truth illuminant annotation:** PLS output SPD is measured in-situ by a reference spectroradiometer, providing traceable spectral ground truth for each captured image.

**Domestic PLS suppliers (2023–2025):**
Chinese manufacturers including Hopoocolor (杭州虹谱色彩), Yanding, and Zhengyin have produced competitive PLS systems at 60–70% lower cost compared to equivalent international products (Gamma Scientific, Instrument Systems), with comparable spectral synthesis accuracy for 8–16-channel configurations. This has significantly lowered the barrier for domestic smartphone ISP labs to adopt PLS-based calibration workflows.

---

### 1.6 Metamerism Risk with Programmable Light Sources

#### 1.6.1 Definition

Metamerism is the phenomenon whereby two objects with different spectral reflectance functions R₁(λ) and R₂(λ) appear identical in color under one illuminant E₁ but differ visibly under another illuminant E₂. The color match under E₁ is called a metameric match.

**Formal condition for a metameric pair under illuminant E₁:**

```
∫ E₁(λ) R₁(λ) x̄(λ) dλ = ∫ E₁(λ) R₂(λ) x̄(λ) dλ
∫ E₁(λ) R₁(λ) ȳ(λ) dλ = ∫ E₁(λ) R₂(λ) ȳ(λ) dλ
∫ E₁(λ) R₁(λ) z̄(λ) dλ = ∫ E₁(λ) R₂(λ) z̄(λ) dλ
```

where x̄(λ), ȳ(λ), z̄(λ) are the CIE 1931 color matching functions. The pairs are only metameric — they will generally produce different tristimulus values under E₂.

#### 1.6.2 PLS-Specific Metamerism Risk Mechanism

A PLS synthesizes a D65 approximation S_PLS(λ) that matches the CIE D65 tristimulus values but not the full SPD. The residual SPD error is:

```
ΔS(λ) = S_PLS(λ) − D65(λ)
```

When a ColorChecker patch with reflectance R_patch(λ) is illuminated by the PLS, its apparent XYZ values differ from those under a true D65 source by:

```
ΔX = ∫ ΔS(λ) · R_patch(λ) · x̄(λ) dλ
```

This error is patch-dependent: patches with spectrally smooth reflectances (e.g., neutral gray) are less affected, while patches with narrow-band spectral features (e.g., saturated primaries, fluorescent samples) can accumulate larger errors. This creates a systematic per-patch calibration bias when a CCM or AWB model is trained under PLS illumination and deployed under a real D65 source.

#### 1.6.3 Types of Metamerism

- **Illuminant metamerism:** The most common type in camera calibration. Two SPDs (PLS and D65) cause the same camera response under one condition but different responses under another. This is the PLS risk described above.
- **Observer metamerism:** Two observers with slightly different color vision (cone sensitivity functions) perceive differently what an instrument measures as a match. Relevant when comparing human and camera color matching.
- **Geometric metamerism:** Match changes with viewing angle due to directional reflectance effects (BRDF). Relevant for glossy calibration targets.

#### 1.6.4 Detection and Quantification

**CIE Metamerism Index (MI):** The MI quantifies how much a metameric pair deviates in color appearance when the illuminant changes from the matching illuminant to a reference. CIE 51-1981 defines the MI for daylight simulator assessment:

- MI < 0.25: Category A (excellent simulator)
- 0.25 ≤ MI < 0.5: Category B
- 0.5 ≤ MI < 1.0: Category C
- MI ≥ 1.0: Category D or E (poor simulator)

A PLS-synthesized D65 with MI > 1.0 should not be used as the sole source for CCM training without cross-validation.

**Cross-validation protocol:** Capture ColorChecker under both PLS-D65 and a physical D65 simulator (Category A or B). Compare per-patch ΔE₀₀. If ΔE₀₀ > 0.5 for any saturated patch, the PLS residual is causing meaningful calibration error.

#### 1.6.5 Mitigation Strategies

1. **Increase PLS channel count:** More LED channels reduce the SPD residual norm. A 19–24-channel PLS can typically achieve MI < 0.5 for D65 synthesis.
2. **In-situ SPD measurement:** Measure S_PLS(λ) for each capture session with a co-located spectroradiometer. Use the measured SPD (not the nominal D65) for CCM and AWB fitting — this absorbs the systematic SPD error into the calibration model.
3. **Physical D65 final validation:** Train calibration on PLS for speed and flexibility; validate final tuning coefficients under a physical Category-A D65 simulator before production release.
4. **Spectral-aware CCM fitting:** Use per-patch spectral reflectance data (measured by spectrophotometer) to compute the expected XYZ under true D65, and fit the CCM to these spectral ground-truth values rather than to the camera responses under PLS illumination.
5. **Avoid fluorescent patches:** When using a PLS with MI > 0.5, exclude fluorescent or high-chroma patches from the CCM training set, as these are most susceptible to illuminant metamerism error.

---

## §2 Calibration

### 2.1 MTF Calibration Workflow

**Target:** ISO 12233:2017 resolution chart or custom slanted edge targets with spatial frequency content at or above Nyquist.

**Procedure:**
1. Mount the camera on a stable, vibration-isolated fixture. Align the optical axis perpendicular to the test chart plane.
2. Set illumination to D65, uniform across the chart (uniformity > 95%).
3. Capture RAW images at multiple focus distances and aperture settings. For fixed-aperture mobile cameras, capture at multiple object distances to assess field curvature.
4. Process RAW to linear demosaiced images (no sharpening, no noise reduction).
5. Run Imatest SFR or MTFMapper on slanted edges at center, mid-field, and corner positions.
6. Record MTF50 (cy/pix) at each position. Compute edge/center MTF50 ratio for lens uniformity.
7. Compare against specification limits and flag out-of-spec lenses for rejection.

**Imatest SFR vs. MTFMapper:**
- Imatest SFR: GUI-based, comprehensive report generation, license cost, widely used in production labs.
- MTFMapper: command-line open-source, suitable for automation in CI pipelines, supports batch processing of large target grids.

### 2.2 Vignetting Calibration

**Target:** Integrating sphere aperture (diameter ≥ 2× sensor diagonal when projected to object space).

**Procedure:**
1. Capture RAW flat-field images of the sphere aperture at the nominal working aperture. Capture ≥ 16 frames for averaging.
2. Average frames to reduce noise. Extract per-channel (R, Gr, Gb, B) normalized gain maps.
3. Normalize each map to unity at the image center.
4. Store gain maps as the LSC (Lens Shading Correction) table in the ISP.
5. Validate corrected uniformity: measure residual non-uniformity across the corrected image. Target: < 2% residual.

**Notes:**
- Repeat calibration across multiple CCT settings if the lens exhibits spectrally dependent vignetting (CRA mismatch is wavelength-dependent).
- Factory-line LSC calibration typically uses a dedicated integrating sphere station with automated capture and upload of LSC tables to the device NVM.

### 2.3 Chromatic Aberration Calibration

**Target:** High-contrast checkerboard grid chart (minimum 15×15 squares), illuminated by D65.

**Procedure:**
1. Capture RAW image at standard focus distance. Process to per-channel (R, G, B) grayscale images without any ISP corrections.
2. Detect checkerboard corners in each channel independently using sub-pixel corner detection.
3. For each corner detected in G channel, find the corresponding corner in R and B channels. Compute the 2D lateral displacement vector (Δx, Δy) for each corner location.
4. Fit a polynomial model (degree 3 or 5) to the radial displacement as a function of normalized radius r:

```
Δr_R(r) = a1*r + a2*r³ + a3*r⁵
Δr_B(r) = b1*r + b2*r³ + b3*r⁵
```

5. Store polynomial coefficients as CACF parameters in the ISP. For non-radially-symmetric CA (due to lens tilt or decentering), use a 2D warp grid instead.

### 2.4 DXO Mark Color Test Light Source Standards

DXO Mark color testing uses a controlled multi-illuminant cabinet with the following requirements:
- Illuminants: D65, A, TL84 (F11), F12 (TL83), optionally CWF
- X-Rite ColorChecker 24-patch or ColorChecker Passport
- Measurement: per-illuminant ΔE₀₀ for each patch, reported as mean and maximum
- Pass threshold: ΔE₀₀ < 3.0 for AWB-corrected images under each illuminant
- Light source uniformity: > 95% across chart area
- Luminance level: matched to typical photographic conditions (≈ 1000 lux on chart)

---

## §3 Tuning

The following table maps measured test results to recommended ISP tuning actions:

| Test Result | Root Cause | Tuning Action |
|---|---|---|
| Center MTF50 < 0.4 cy/pix | Lens spherical aberration / focus offset | Adjust focus calibration offset; increase sharpening gain in center region; consider DNN restoration |
| Corner MTF50 / Center MTF50 < 0.6 | Field curvature / coma / astigmatism | Apply spatially variant sharpening with stronger boost at corners; consult optical team for lens redesign |
| Lateral CA > 1 pixel at corner | Transverse chromatic aberration | Increase CACF polynomial degree; recalibrate CA coefficients; verify calibration chart alignment |
| Lateral CA > 0.5 pixel post-CACF | CACF correction undershoot | Re-fit polynomial with higher-order terms or switch to 2D warp map |
| Corner vignetting > 40% (pre-LSC) | Strong natural + mechanical vignetting | Re-measure LSC table; check CRA mismatch; consider re-designing module |
| LSC corrected uniformity > 5% | LSC table noise / quantization | Increase flat-field frame averaging (≥ 32 frames); increase LSC table resolution |
| Barrel distortion > 3% (non-UWA) | Lens design | Recalibrate distortion polynomial; verify calibration target flatness |
| PLS Metamerism Index > 1.0 | PLS SPD residual | Switch to higher channel-count PLS; use in-situ SPD measurement; cross-validate with physical D65 |
| AWB ΔE₀₀ > 3.0 under TL84 | CCM not covering fluorescent locus | Retrain CCM with TL84 training patches; expand AWB gray world boundary |
| Purple fringing at backlit edges | Longitudinal CA + UV leak | Enable CACF; add desaturation in hue range 270–320°; verify UV-cut filter presence |

---

## §4 Artifacts

### 4.1 Purple Fringing

**Description:** A purple or magenta halo appearing at high-contrast edges, especially at backlit boundaries (bright sky behind dark objects) and near specular highlights.

**Cause:** A combination of mechanisms:
1. **Longitudinal chromatic aberration:** Blue/violet wavelengths focus in front of the sensor plane, creating a defocused blue halo around bright sources.
2. **UV leakage:** Inadequate UV-cut filter transmits UV energy that the Bayer blue pixels detect, contributing to the blue/purple halo.
3. **Blooming:** Charge overflow from overexposed pixels, particularly in the blue channel, spreads laterally to adjacent pixels.

**ISP correction:**
- CACF corrects the lateral component of CA but cannot fix longitudinal CA (which is a defocus, not a shift).
- Hue-specific desaturation: detect pixels with high S (saturation) and H in the purple range (approximately 270–320° in HSV space) near high-contrast edges, and reduce saturation selectively.
- Edge-aware application prevents desaturation from affecting legitimate purple/blue content in the scene.

### 4.2 Flare and Ghosting

**Description:** Flare appears as a diffuse reduction in local contrast (veiling glare). Ghosting appears as a secondary displaced image of a bright source (typically the sun or lamp) created by internal lens reflections following a specific geometric path between lens surfaces.

**Cause:** Fresnel reflections at lens surfaces (even AR-coated surfaces reflect ~0.2–0.5% per surface), internal scattered light, and sensor cover glass reflections contribute to flare. Ghosts follow paths where light reflects from the sensor back to a lens surface and then to the sensor again.

**ISP mitigation:**
- Optical: AR coatings, lens baffles, lens hood design.
- ISP: The MIPI Alliance Night Mode special interest group has documented a Night Flare Removal challenge. Flare removal algorithms detect and subtract the flare component estimated from the bright source PSF and position. DNN-based flare removal has shown the best performance on the Flare7K and similar benchmarks.

### 4.3 Diffraction Softening at Small Aperture

**Description:** As the aperture is stopped down (higher f-number), the Airy disk diameter grows and begins to exceed the pixel pitch, causing diffraction-limited softening that no amount of ISP sharpening can cleanly reverse.

**Airy disk diameter:**

```
d_Airy = 2.44 * λ * f/#
```

For λ = 550 nm:
- f/1.8: d_Airy = 2.4 µm (< typical 0.8–1.0 µm pixel pitch × 3 → sharp)
- f/4.0: d_Airy = 5.4 µm (≈ 6 pixels at 0.9 µm pitch → significant softening)
- f/8.0: d_Airy = 10.7 µm (≈ 12 pixels → severe diffraction limit)

**ISP consideration:** Mobile cameras with fixed aperture are designed to operate near their diffraction-optimal aperture. Variable-aperture implementations (e.g., Samsung Galaxy S23 Ultra with f/1.7–f/2.4 switching) must balance depth of field, diffraction, and vignetting trade-offs. The ISP sharpening parameters should be aperture-aware, applying stronger sharpening at smaller apertures to partially compensate for diffraction softening.

---

## §5 Evaluation

Performance benchmarks for flagship smartphone cameras (state of the art, 2024):

| Metric | Tool | Typical Flagship Value | Notes |
|---|---|---|---|
| Center MTF50 | Imatest SFR / MTFMapper | 0.45–0.55 cy/pix | Post-demosaic, no ISP sharpening |
| Edge/Center MTF50 ratio | Imatest SFR / MTFMapper | > 0.70 (good lens) | < 0.60 = field curvature concern |
| Max lateral CA (pre-CACF) | Imatest CA / MTFMapper | < 1.0 pixel at corner | |
| Max lateral CA (post-CACF) | Imatest CA / MTFMapper | < 0.5 pixel | < 0.3 pixel = excellent |
| Corner vignetting (pre-LSC) | Flat-field + Imatest | < 25% for standard lens; < 50% for UWA | cos⁴θ natural + mechanical |
| LSC corrected uniformity | Flat-field residual | < 2% | Post-correction non-uniformity |
| Max geometric distortion | Checkerboard / Imatest | < 1.0% (standard); < 3.0% (UWA) | Post-correction residual |
| AWB ΔE₀₀ (D65) | Multi-illuminant ColorChecker | < 2.0 | DXOMARK pass = < 3.0 |
| AWB ΔE₀₀ (TL84/F11) | Multi-illuminant ColorChecker | < 3.0 | Fluorescent hardest case |
| PLS Metamerism Index | CIE MI (via spectroradiometer) | < 0.5 (Category B simulator) | < 0.25 = Category A |
| Diffraction-limited MTF50 | Calculated (f/#, λ, pixel pitch) | Compare with measured MTF50 | If measured ≈ theoretical, lens is near diffraction-limited |

---

## §6 Code

Companion notebook: `ch08_code.ipynb`

The notebook contains the following implementations:

### Cell 1: MTF Calculation from Slanted Edge (MTFMapper Wrapper)

Automates MTFMapper invocation on a folder of slanted-edge images, parses the output CSV, and plots MTF curves for center, mid-field, and corner positions. Computes MTF50 and edge/center ratio automatically.

```python
# Key steps (see notebook for full implementation)
# 1. Call MTFMapper subprocess on input image
# 2. Parse mtfmapper_<image>_data.csv output
# 3. Group measurements by image region (center, mid, corner)
# 4. Plot MTF curves and annotate MTF50 intersections
```

### Cell 2: Flat-Field RAW Vignetting Gain Map Extraction

Reads multiple RAW frames (using rawpy), averages to reduce shot noise, extracts per-Bayer-channel (R, Gr, Gb, B) images, normalizes to center, and saves the vignetting gain map as a 4-channel TIFF suitable for LSC table generation.

```python
# Key steps
# 1. rawpy.imread() for each frame, extract raw_image (Bayer pattern)
# 2. Average across N frames: mean_raw = np.mean(stack, axis=0)
# 3. Separate into R/Gr/Gb/B channels by Bayer position
# 4. Normalize each channel: gain_map = center_value / channel_image
# 5. Save gain maps; visualize with matplotlib
```

### Cell 3: Polynomial Fit for Lateral CA Offset

Uses a checkerboard RAW image to detect corner positions in R, G, B channels using OpenCV, computes lateral displacement vectors, and fits a radial polynomial model using scipy.optimize.curve_fit. Outputs polynomial coefficients for CACF programming.

```python
# Key steps
# 1. cv2.findChessboardCorners() on each channel grayscale image
# 2. Compute displacement: delta_r = G_corners - R_corners
# 3. Compute normalized radius for each corner: r = sqrt(x² + y²) / r_max
# 4. Fit polynomial: delta_r = a1*r + a3*r³ + a5*r⁵ via curve_fit
# 5. Plot measured vs. fitted displacement; report RMSE
```

### Cell 4: PLS D65 Approximation and Metamerism Index Computation

Simulates a PLS SPD synthesis for a D65 target using NNLS with a set of 8 or 16 LED channel basis functions. Computes the residual ΔS(λ), then calculates the CIE Metamerism Index for a set of ColorChecker patches to quantify calibration error risk.

```python
# Key steps
# 1. Load LED channel SPDs: phi_matrix (N_wavelengths × N_channels)
# 2. Load CIE D65 SPD as target
# 3. Solve NNLS: weights, _ = scipy.optimize.nnls(phi_matrix, D65_spd)
# 4. Reconstruct PLS SPD: S_pls = phi_matrix @ weights
# 5. Compute delta_S = S_pls - D65_spd
# 6. For each ColorChecker patch reflectance R_patch(λ):
#    delta_XYZ = integrate(delta_S * R_patch * cmf, dλ)
# 7. Convert delta_XYZ to delta_E00; plot per-patch metamerism error
# 8. Report CIE MI: max(delta_E00) across reference patches
```

---

## References

1. Smith, W. J. (2008). *Modern Optical Engineering* (4th ed.). McGraw-Hill. — Comprehensive treatment of geometric and chromatic aberrations, Seidel theory, and MTF.

2. ISO 12233:2017 — *Photography — Electronic still picture imaging — Resolution and spatial frequency responses.* International Organization for Standardization.

3. CIE 15:2004 — *Colorimetry* (3rd ed.). Commission Internationale de l'Éclairage. — Defines CIE standard illuminants D65, A, F-series and color matching functions.

4. CIE 51-1981 — *Method for Assessing the Quality of Daylight Simulators for Colorimetry.* Commission Internationale de l'Éclairage. — Defines the Metamerism Index and simulator grading categories A–E.

5. Imatest LLC — SFR (Spatial Frequency Response) MTF measurement documentation. https://www.imatest.com/docs/sfr/

6. MTFMapper open-source MTF analysis tool, by Frans van den Bergh. https://sourceforge.net/projects/mtfmapper/

7. DXO Mark — Camera and smartphone testing methodology. https://www.dxomark.com/methodology/

8. Yanding Instruments (研鼎仪器) — Integrating sphere and camera module test equipment. www.yanding.com

9. Everfine (远方光电) — Spectroradiometers and light source calibration systems. www.everfine.net

10. Nakamura, J. (Ed.) (2006). *Image Sensors and Signal Processing for Digital Still Cameras.* CRC Press. — Chapter on lens characterization and ISP pipeline design.

11. Wyszecki, G., & Stiles, W. S. (2000). *Color Science: Concepts and Methods, Quantitative Data and Formulae* (2nd ed.). Wiley. — Metamerism theory and colorimetric foundations.

12. Born, M., & Wolf, E. (1999). *Principles of Optics* (7th ed.). Cambridge University Press. — Diffraction theory, Airy disk, and wave aberrations.

---

*End of Chapter 8*
