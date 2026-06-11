# Part 1, Chapter 05: Color Science Basics

> **Pipeline position:** Foundation for AWB (Ch22), CCM (Ch23), Gamma/TM (Ch25–26), and all downstream color processing
> **Prerequisites:** Chapter 3 (Sensor Physics) — radiometric response, spectral sensitivity
> **Reader path:** All readers. Algorithm engineers focus on §2–§4; DL researchers should understand §1 thoroughly.

---

## §1 Theory

### 1.1 Human Color Vision and Trichromacy

The human retina contains three types of cone photoreceptors, conventionally labeled **L** (long-wavelength, peak ~564 nm), **M** (medium, peak ~534 nm), and **S** (short, peak ~420 nm). Their overlapping spectral sensitivities mean that any physical spectrum is compressed into exactly three numbers — the (L, M, S) cone responses. This compression is the foundation of both the beauty and the difficulty of color science.

**Metamerism** is the direct consequence: two physically different spectral power distributions (SPDs) that produce identical (L, M, S) responses appear identical in color. A camera sensor with three spectral channels exploits the same trichromatic principle, but its spectral sensitivities generally differ from the cone sensitivities, which is why raw sensor data must be transformed to match human perception.

### 1.2 CIE 1931 Standard Observer and XYZ Tristimulus

In 1931, the Commission Internationale de l'Éclairage (CIE) standardized color measurement by defining the **CIE 2° Standard Observer**: a set of three color matching functions $\bar{x}(\lambda)$, $\bar{y}(\lambda)$, $\bar{z}(\lambda)$ derived from psychophysical experiments conducted by Guild and Wright. For any SPD $P(\lambda)$ under illuminant $E(\lambda)$, the tristimulus values are:

$$
X = \int_{380}^{780} P(\lambda)\, E(\lambda)\, \bar{x}(\lambda)\, d\lambda
$$

$$
Y = \int_{380}^{780} P(\lambda)\, E(\lambda)\, \bar{y}(\lambda)\, d\lambda
$$

$$
Z = \int_{380}^{780} P(\lambda)\, E(\lambda)\, \bar{z}(\lambda)\, d\lambda
$$

The $\bar{y}(\lambda)$ function was deliberately designed to match the **photopic luminosity function** $V(\lambda)$, so $Y$ represents perceived luminance. The **chromaticity coordinates** eliminate luminance and encode only color:

$$
x = \frac{X}{X+Y+Z}, \quad y = \frac{Y}{X+Y+Z}, \quad z = 1 - x - y
$$

The **CIE xy chromaticity diagram** is the projection of all visible colors onto this 2D plane. The horseshoe-shaped boundary is the **spectral locus** (monochromatic lights); the straight bottom edge is the **purple line**. All physically realizable colors lie inside this boundary. White points, gamut triangles, and the Planckian locus all live in this diagram — it is the universal "map" of color.

**ISP implication:** Raw sensor values (R, G, B) must ultimately be transformed into a device-independent space such as XYZ before any perceptual judgement can be made. This transformation is the Color Correction Matrix (CCM), detailed in Chapter 23.

### 1.3 Standard Color Spaces

#### sRGB

Defined in IEC 61966-2-1 (1999) and adopted universally for consumer displays, sRGB specifies:

- **Red primary:** (0.6400, 0.3300) in xy
- **Green primary:** (0.3000, 0.6000) in xy
- **Blue primary:** (0.1500, 0.0600) in xy
- **White point:** D65 (x = 0.3127, y = 0.3290)
- **Transfer function (EOTF):** piecewise — linear for small values, then approximate gamma 2.2:

$$
C_\text{linear} = \begin{cases} C_\text{sRGB} / 12.92 & C_\text{sRGB} \le 0.04045 \\ \left(\dfrac{C_\text{sRGB} + 0.055}{1.055}\right)^{2.4} & C_\text{sRGB} > 0.04045 \end{cases}
$$

The effective perceptual gamma is approximately 2.2. Most camera pipelines output sRGB 8-bit for JPEG delivery.

#### DCI-P3 / Display P3

DCI-P3 was defined by the Digital Cinema Initiatives for cinema projection. Display P3 (Apple's variant) uses the same primaries but replaces the DCI white point with D65:

- **Green primary** extends to (0.2650, 0.6900), significantly expanding the green gamut
- Covers approximately 45.5% of CIE 1931 vs. sRGB's 35.9%
- Used in iPhone, iPad Pro, and modern Android flagship displays

#### Rec.2020 (BT.2020)

ITU-R BT.2020 defines the ultra-high-definition television color space:

- **Red:** (0.708, 0.292), **Green:** (0.170, 0.797), **Blue:** (0.131, 0.046)
- White point: D65
- Covers ~75.8% of CIE 1931 — most of visually distinguishable colors
- Practical capture in true Rec.2020 remains challenging; most cameras approximate it via computational mapping

#### HDR Color Spaces: PQ and HLG Transfer Functions

High Dynamic Range (HDR) content requires transfer functions that encode luminance values up to 1000–10000 nits, far beyond the 80–100 nits of SDR displays.

**PQ (Perceptual Quantizer, SMPTE ST 2084)** — Used in HDR10, Dolby Vision, and HDR video production. The EOTF maps a normalized code value $V$ to absolute luminance $F$ (cd/m²):

$$F = 10000 \cdot \left(\frac{\max(V^{1/m_2} - c_1,\, 0)}{c_2 - c_3 \cdot V^{1/m_2}}\right)^{1/m_1}$$

where $m_1=2610/16384$, $m_2=2523/32$, $c_1=107/128$, $c_2=2413/128$, $c_3=2392/128$ (SMPTE ST 2084 constants). PQ is an **absolute** transfer function: the same code value always maps to the same physical luminance regardless of display.

**HLG (Hybrid Log-Gamma, ARIB STD-B67 / ITU-R BT.2100)** — Used in broadcast HDR (BBC/NHK co-developed). The OETF is a piecewise function:

$$E = \begin{cases} \sqrt{3E'} & 0 \leq E' \leq 1/12 \\ a \cdot \ln(12E' - b) + c & E' > 1/12 \end{cases}$$

where $a=0.17883277$, $b=0.28466892$, $c=0.55991073$. HLG is **scene-referred and relative** — it is backward-compatible with SDR displays and does not require HDR metadata. This makes HLG preferable for live broadcast and real-time ISP pipelines.

**ISP Integration Implications:**
- Internal processing should operate in linear light (scene-referred) domain
- Before output, apply the target OETF (PQ for HDR10 delivery, HLG for broadcast)
- HDR metadata (MaxCLL — Maximum Content Light Level, MaxFALL — Maximum Frame Average Light Level) must be computed from the output frame in real time
- ISP AWB and tone mapping operate differently in HDR mode: the tone curve must preserve specular highlights above 100 nits rather than clip them

#### OKLab Color Space (Björn Ottosson, 2020)

CIELAB, while historically dominant, exhibits several known perceptual non-uniformities — particularly for blue hues, where equal Euclidean steps in L\*a\*b\* do not correspond to equal perceived differences.

**OKLab** (Ottosson, 2020, published as a blog post and widely adopted in CSS Color Level 4 and Photoshop) improves on CIELAB by fitting the transfer to a large set of visual matching data. The conversion from XYZ to OKLab uses a two-stage transform:

$$[l, m, s] = M_1 \cdot [X, Y, Z]^T, \quad [l', m', s'] = [l^{1/3}, m^{1/3}, s^{1/3}]$$

$$[L, a, b]_\text{OK} = M_2 \cdot [l', m', s']^T$$

where $M_1$ and $M_2$ are fixed 3×3 matrices fitted to perceptual data. Key properties:
- More uniform hue linearity (rotating a\*-b\* vector changes apparent hue predictably)
- Better chroma uniformity across hue angles — sRGB blues are correctly perceived as more saturated relative to greens
- No discontinuity near the achromatic axis (a common CIELAB artifact for low-saturation colors)

**ISP Applications:** OKLab is increasingly used for perceptual color grading, skin tone detection, and selective color protection. For example, a skin tone protection algorithm operating in OKLab can define a compact convex region in (a, b) space that closely matches human judgments of "skin tone," whereas the same region in CIELAB would require a more complex irregular boundary.

#### CIELAB (L\*a\*b\*)

XYZ is not perceptually uniform — equal Euclidean distances do not correspond to equal perceived color differences. CIE 1976 introduced **CIELAB** to correct this:

$$
L^* = 116\, f\!\left(\frac{Y}{Y_n}\right) - 16
$$

$$
a^* = 500\left[f\!\left(\frac{X}{X_n}\right) - f\!\left(\frac{Y}{Y_n}\right)\right]
$$

$$
b^* = 200\left[f\!\left(\frac{Y}{Y_n}\right) - f\!\left(\frac{Z}{Z_n}\right)\right]
$$

where $f(t) = t^{1/3}$ for $t > (6/29)^3$, else $f(t) = \tfrac{1}{3}(29/6)^2 t + \tfrac{4}{29}$, and $(X_n, Y_n, Z_n)$ is the XYZ of the reference white (D65: $X_n=0.9504$, $Y_n=1.0$, $Z_n=1.0888$).

The $L^*$ axis encodes lightness (0 = black, 100 = white). The $a^*$ axis encodes green (negative) to red (positive). The $b^*$ axis encodes blue (negative) to yellow (positive). CIELAB is the working space for all color difference calculations in ISP calibration.

**Table 1: Color Space Comparison**

| Color Space | Red (xy) | Green (xy) | Blue (xy) | White Point | Bit Depth (typical) | Primary Use Case |
|-------------|----------|------------|-----------|-------------|----------------------|-----------------|
| sRGB | (0.640, 0.330) | (0.300, 0.600) | (0.150, 0.060) | D65 | 8-bit | Web, JPEG, consumer display |
| DCI-P3 | (0.680, 0.320) | (0.265, 0.690) | (0.150, 0.060) | DCI (0.314, 0.351) | 12-bit | Cinema projection |
| Display P3 | (0.680, 0.320) | (0.265, 0.690) | (0.150, 0.060) | D65 | 10-bit | Mobile flagship, macOS |
| Rec.2020 | (0.708, 0.292) | (0.170, 0.797) | (0.131, 0.046) | D65 | 10/12-bit | 4K/8K HDR video |
| CIELAB | — | — | — | Adaptive (any) | — | Color measurement, ΔE |

### 1.4 Color Temperature and Planckian Locus

A **blackbody radiator** at absolute temperature $T$ (in Kelvin) emits radiation following Planck's law. Its chromaticity traces the **Planckian locus** across the CIE diagram as $T$ varies. The **Correlated Color Temperature (CCT)** of a real light source is defined as the temperature of the Planckian radiator whose perceived color most closely matches the source, measured as the perpendicular distance on the CIE uv diagram (Robertson's method).

Approximate CCT from xy chromaticity (McCamy's formula):

$$
\text{CCT} \approx \frac{-449\, n^3 + 3525\, n^2 - 6823.3\, n + 5520.33}{}
$$

where $n = (x - 0.3320)/(y - 0.1858)$.

**Table 2: Common Illuminants**

| Illuminant | CCT (K) | Typical Scene | ISP Implication |
|------------|---------|---------------|-----------------|
| Candlelight / A | 2856 K | Indoor incandescent | Strong orange cast; WB gains: R↓↓, B↑↑ |
| Warm white LED | 2700–3000 K | Home LED bulb | Moderate orange; CCM needed for skin accuracy |
| TL84 / CWF | ~4000 K | Office fluorescent | Green spike; problematic metamerism |
| D50 | 5003 K | Horizon daylight | ICC printing standard white point |
| D65 | 6504 K | Overcast noon | sRGB / Rec.2020 standard white point |
| D75 | 7504 K | Overcast sky | Cool bluish cast |
| Shade / D93 | ~9000–10000 K | Open shade | Very blue; aggressive WB correction |

### 1.5 Chromatic Adaptation

When the illuminant changes, the human visual system adapts and the appearance of surfaces remains approximately constant — this is **chromatic adaptation**. In ISP, the AWB module estimates the scene illuminant and applies a gain correction that mimics this adaptation.

The **Bradford transform** (used in ICC profiles) and **CAT02** (used in CIECAM02) model this adaptation. The process is:

1. Convert source XYZ to the CAT02 sharpened cone response space via matrix $\mathbf{M}_\text{CAT02}$
2. Scale each channel by the ratio of the destination white point to the source white point
3. Invert back to XYZ

For ISP practice, the simplified **von Kries adaptation** (diagonal scaling in cone space) is sufficient for AWB → CCM handoff, and is what virtually all camera ISPs implement.

### 1.6 Color Difference Metrics

**ΔE76 (CIE 1976):** Euclidean distance in CIELAB space:

$$
\Delta E_{76} = \sqrt{(\Delta L^*)^2 + (\Delta a^*)^2 + (\Delta b^*)^2}
$$

Simple to compute, but perceptually non-uniform: 1 unit of ΔE76 in the blue region appears much larger than 1 unit in the yellow-green region.

**ΔE2000 (CIEDE2000):** The current gold standard, published by Sharma et al. (2005). Key improvements over ΔE76:

- **Lightness weighting** $S_L$: reduces sensitivity at very dark and very light extremes
- **Chroma weighting** $S_C$: accounts for the fact that color differences are harder to see in saturated colors
- **Hue weighting** $S_H$: hue tolerance is larger than chroma tolerance
- **Hue rotation** $R_T$: empirical correction for the blue-violet region where perceived hue and chroma are coupled

$$
\Delta E_{00} = \sqrt{\left(\frac{\Delta L'}{k_L S_L}\right)^2 + \left(\frac{\Delta C'}{k_C S_C}\right)^2 + \left(\frac{\Delta H'}{k_H S_H}\right)^2 + R_T \frac{\Delta C'}{k_C S_C} \frac{\Delta H'}{k_H S_H}}
$$

where $\Delta L'$, $\Delta C'$, $\Delta H'$ are lightness, chroma, and hue differences in a modified Lab space.

**Practical rule of thumb:**
- ΔE2000 < 1.0: not perceptible to most observers
- 1.0–2.0: perceptible on side-by-side comparison
- 2.0–3.5: clearly noticeable in typical viewing
- > 3.5: objectionable color error

ISP calibration targets ΔE2000 < 3.0 on all 24 Macbeth patches; consumer-grade tuning typically achieves mean ΔE2000 < 3.0 with max < 6.0.

---

## §2 Calibration

### 2.1 Macbeth ColorChecker 24

The **X-Rite Macbeth ColorChecker Classic** (24-patch chart) is the de facto standard for camera color calibration. It contains 24 surface color samples organized in a 4×6 grid:
- Rows 1–2: natural object colors (skin tones, foliage, sky blue, etc.)
- Rows 3–4: saturated primary/secondary colors + a neutral gray scale

The **CIE L\*a\*b\*** reference values for the 24 patches (measured under D50) are published by X-Rite and widely available. The spectral reflectance curves have been measured and are available in the `colour-science` library under `colour.SDS_COLOURCHECKERS`.

### 2.2 Calibration Procedure

**Step 1 — Multi-illuminant capture:** Photograph the ColorChecker under each target illuminant (D65, D50, A/Incandescent, TL84/Fluorescent). Use a calibrated light booth or a measured studio strobe. Fix exposure to avoid clipping on the white patch.

**Step 2 — Linearize raw data:** Apply black level subtraction and lens shading correction. Extract the mean pixel value from a central region of each patch (avoid edges). This yields 24 raw (R, G, B) triplets per illuminant.

**Step 3 — Estimate CCM via least squares:** The color correction matrix $\mathbf{M}$ (3×3 or 3×4 with an offset column) maps raw RGB to the reference XYZ (or sRGB):

$$
\mathbf{M} = \arg\min_{\mathbf{M}} \sum_{i=1}^{24} \left\| \mathbf{M}\, \mathbf{r}_i - \mathbf{t}_i \right\|^2
$$

where $\mathbf{r}_i$ is the raw patch vector and $\mathbf{t}_i$ is the target Lab/XYZ value. Solved in closed form via the pseudo-inverse: $\mathbf{M} = \mathbf{T}\mathbf{R}^+$.

**Step 4 — Validate:** Apply the estimated CCM to the raw patches, convert to Lab, and compute ΔE76 and ΔE2000 for all 24 patches. Report mean, max, and per-patch values.

### 2.3 IT8 Chart

For wider coverage, the **ANSI/ISO IT8.7** chart contains hundreds of color patches including a neutral wedge and saturated ramps. It is used in high-accuracy scanner and printer profiling and is beneficial when the CCM must cover a wide gamut beyond the Macbeth 24.

### 2.4 Code: Measure ΔE from ColorChecker Patches

```python
import numpy as np

def srgb_to_xyz(srgb):
    """Convert sRGB [0,1] to XYZ using ITU-R BT.709 matrix (D65)."""
    # Linearize
    linear = np.where(srgb <= 0.04045,
                      srgb / 12.92,
                      ((srgb + 0.055) / 1.055) ** 2.4)
    # sRGB -> XYZ (D65) matrix
    M = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    return linear @ M.T

def xyz_to_lab(xyz, Xn=0.9504, Yn=1.0000, Zn=1.0888):
    """Convert XYZ to CIELAB with D65 white point."""
    epsilon, kappa = (6/29)**3, (29/6)**2 / 3
    def f(t):
        return np.where(t > epsilon, t**(1/3), kappa * t + 4/29)
    fx = f(xyz[..., 0] / Xn)
    fy = f(xyz[..., 1] / Yn)
    fz = f(xyz[..., 2] / Zn)
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    return np.stack([L, a, b], axis=-1)

def delta_e76(lab1, lab2):
    """ΔE76: Euclidean distance in CIELAB."""
    diff = lab1 - lab2
    return np.sqrt(np.sum(diff**2, axis=-1))

# Example usage
# measured_srgb: (24, 3) array of measured patch values in [0,1]
# reference_srgb: (24, 3) array of reference ColorChecker sRGB values
measured_lab = xyz_to_lab(srgb_to_xyz(measured_srgb))
reference_lab = xyz_to_lab(srgb_to_xyz(reference_srgb))
de76 = delta_e76(measured_lab, reference_lab)
print(f"Mean ΔE76: {de76.mean():.2f}, Max ΔE76: {de76.max():.2f}")
```

---

## §3 Tuning

### 3.1 CCM Optimization

The least-squares CCM minimizes mean ΔE on the ColorChecker but often sacrifices visual preference: accurate neutrals at the cost of desaturated colors. In practice, camera tuning applies a **constrained optimization**:

1. **Hard constraint:** ΔE2000 < 3.0 on neutral gray patches (rows 3–4 of Macbeth) — skin and gray accuracy is non-negotiable
2. **Soft preference:** allow up to ΔE2000 ≤ 6.0 on saturated patches to enable a controlled **saturation boost**

The saturation boost is injected by adding a hue-selective saturation matrix (often in HSL or Lab space) after the linear CCM. This is sometimes called the "color enhancement matrix" or "vivid mode."

### 3.2 Trade-off: Accuracy vs. Saturation

| Tuning Mode | Mean ΔE2000 | Skin Tone ΔE2000 | User Perception |
|-------------|-------------|------------------|-----------------|
| Colorimetric (accurate) | ~1.5–2.5 | < 2.0 | "Flat," "muted" |
| Preferred (boosted) | ~3.5–5.0 | < 3.0 | "Vivid," "pleasing" |
| Over-saturated | > 6.0 | > 4.0 | "Unnatural," "neon" |

DXOMark and mobile camera reviews consistently show that users prefer slightly oversaturated images in side-by-side preference tests, even when ΔE2000 is larger. The industry convention is to tune for **preferred rendering**, not strict colorimetric accuracy.

### 3.3 Multi-Illuminant CCM

A single CCM is only valid at the illuminant under which it was calibrated. In real-world ISP:

- Calibrate separate CCMs at D65, D50, A, and TL84
- The AWB module estimates scene CCT
- Interpolate between the nearest two CCMs (linear interpolation in CCT space)

This is the **CCT-indexed CCM** approach used in virtually all production ISPs.

### 3.4 Gamut Mapping

Colors captured in wide-gamut raw space may fall **outside the target output gamut** (e.g., outside sRGB). Gamut mapping strategies:

- **Clipping:** Set out-of-gamut values to the gamut boundary. Fast, but causes hue shifts and flat rendering in vivid subjects (e.g., flowers, neon signs)
- **Chroma compression:** Reduce chroma until the color is on the gamut boundary, preserving hue. Preferred for photographic content
- **Perceptual rendering intent:** ICC-profile-based global compression. Used for printing

### 3.5 AWB → CCM Dependency

The CCM assumes a specific illuminant (e.g., D65). If the AWB mis-estimates the illuminant and applies wrong gains, the CCM will compound the error. The correct pipeline order is:

```
Raw → BLC → Linearization → AWB gains → Demosaic → CCM (indexed to AWB CCT estimate) → Gamma
```

The CCM must be selected *after* AWB has committed to an illuminant estimate.

---

## §4 Artifacts

### 4.1 Color Casts

A color cast is a global tint affecting the entire image. Causes:

- **Wrong AWB:** AWB module chose incorrect illuminant (e.g., interpreted fluorescent light as tungsten), resulting in incorrect gain vector
- **Wrong CCM:** CCM calibrated under D65 applied to an A-illuminant scene without switching to the correct indexed CCM
- **Diagnosis:** Gray patches in ColorChecker will show non-zero $a^*$ or $b^*$ in Lab space

### 4.2 Gamut Clipping

When highly saturated real-world colors (vivid red flowers, neon signs, saturated fabrics) exceed the output gamut, clipping occurs. Symptoms:

- Flat, posterized appearance in saturated regions
- Loss of detail and texture in hue transitions
- Impossible to recover in post-processing once clipped

**Detection:** Compute the percentage of pixels with any RGB channel at or near 255 in 8-bit output. A well-tuned ISP should show < 0.1% of pixels clipped on natural scenes.

### 4.3 Hue Shifts

Hue shifts most commonly appear in:

- **Green-yellow:** Over-aggressive green channel gain (common in Bayer demosaic) shifts foliage and skin toward yellow
- **Magenta shift in skin:** Incorrect L/M/S primaries in the CCM shifts Asian skin tones toward magenta
- **Blue shift in shadows:** Insufficient blue channel correction in dark regions

**Diagnosis tool:** Plot hue angle error vs. hue angle for all ColorChecker patches. Look for systematic offsets in particular hue regions.

### 4.4 Metamerism Failure

A CCM optimized for D65 may be accurate under D65 but wrong under TL84 (fluorescent) because the fluorescent SPD has a discontinuous spectrum with sharp emission lines. The camera's spectral sensitivities handle these lines differently from the human cones, breaking the colorimetric relationship.

**Symptom:** A skin tone or gray patch that looks correct under D65 develops a green/magenta cast under office fluorescent lighting.

**Mitigation:** Multi-illuminant CCM calibration (§3.3) and careful TL84 characterization.

---

## §5 Evaluation

### 5.1 ColorChecker ΔE Metrics

The standard color accuracy test protocol:

1. Photograph the X-Rite ColorChecker Classic under a calibrated D65 light booth
2. Extract mean Lab values from each of the 24 patches (central 50% area, avoid edge artifacts)
3. Compare to the published X-Rite reference Lab values (D50-adapted)
4. Compute **mean ΔE2000** (primary metric), **max ΔE2000** (worst patch), and the distribution

**Industry targets:**

| Metric | Excellent | Good | Acceptable | Poor |
|--------|-----------|------|------------|------|
| Mean ΔE2000 | < 2.0 | < 3.5 | < 5.0 | ≥ 5.0 |
| Max ΔE2000 | < 4.0 | < 7.0 | < 10.0 | ≥ 10.0 |
| Skin tone ΔE2000 | < 2.0 | < 3.0 | < 4.5 | ≥ 4.5 |

### 5.2 Gamut Coverage

**Gamut coverage ratio** measures how much of a reference gamut (typically P3 or Rec.2020) the camera pipeline can faithfully reproduce:

$$
\text{Coverage}_{P3} = \frac{\text{Area of camera gamut} \cap \text{Area of P3}}{\text{Area of P3}} \times 100\%
$$

Measured in the CIE xy chromaticity diagram using the polygon area of the camera's effective color gamut (estimated from ColorChecker or IT8 patches).

### 5.3 DXOMark Color Score

DXOMark's color accuracy score is derived from:

- **White balance** accuracy across multiple illuminants (measured with a spectrophotometer)
- **Color shading** — how color accuracy varies across the image field
- **Color depth** — the number of distinguishable color steps (linked to noise floor and quantization)

DXOMark uses custom charts including their own color target with skin tone patches. Their score is not a direct ΔE2000 number but a composite index (weighted combination of white balance accuracy, color shading, and color depth). DXOMark Color sub-score reference (Camera v5 protocol, data prior to July 2025):

| Category | DXOMark Color Sub-score (approx.) | Representative ΔE2000 | Example devices |
|----------|----------------------------------|----------------------|----------------|
| Top flagship (2025) | 125–130 | Mean ~1.5–2.5 | Huawei Pura 70 Ultra (130), iPhone 16 Pro Max (130) |
| Upper mid / premium | 115–124 | Mean ~2.5–3.5 | Samsung Galaxy S25 Ultra (125), iPhone 16 (124) |
| Mid-range smartphone | 90–115 | Mean ~3.5–5.0 | Mainstream Android, Snapdragon 7-series |
| Consumer compact camera | 65–85 | Mean ~5.0–8.0 | Entry-level compact, beginner mirrorless |

> **Note:** DXOMARK released Camera v6 protocol in July 2025, rescaling all scores. The Huawei Pura 80 Ultra leads at 175 (overall v6 score); color sub-score boundaries shifted accordingly and cannot be directly compared to v5 values. ΔE2000 figures are lab-measured under D65 illumination at image center using ISO 12233 / Macbeth 24-block chart.

### 5.4 Additional Metrics

- **Hue linearity:** std dev of hue angle error across the 24 patches
- **Chroma accuracy:** mean chroma ratio (measured $C^*$ / reference $C^*$); > 1.0 indicates saturation boost
- **White balance accuracy:** ΔE2000 of the 6 gray scale patches specifically (patches 19–24 in Macbeth)

---

## §6 Code

See *See §6 Code section for runnable examples.* for a fully runnable notebook covering:

1. ColorChecker data loading (via `colour-science` or hardcoded reference values)
2. sRGB → XYZ → CIELAB conversion pipeline
3. ΔE76 computation per patch
4. CIE xy chromaticity diagram with sRGB / P3 / Rec.2020 gamut triangles
5. ΔE bar chart per patch
6. Summary statistics and exercises

---

## §7 Engineering Color Challenges

### 7.1 IR Cut Filter and Spectral Matching

Camera sensor silicon is sensitive to near-infrared radiation (700–1100 nm), which is invisible to humans but contributes to the sensor's raw signal. Without an IR-cut filter, outdoor images acquire a magenta/red cast because IR radiation adds primarily to the R channel. The IRCF (Infrared Cut Filter) is placed in the optical path (often integrated into the lens barrel) to block wavelengths above ~700 nm.

In mobile devices with ultra-thin form factors, the IRCF specification directly affects color accuracy: a narrower cut-off (e.g., 680 nm vs. 700 nm) reduces IR contamination but also slightly attenuates red channel sensitivity, affecting skin tone rendering. ISP CCM calibration must account for the IRCF's actual spectral transmittance curve, which varies across vendors and temperature.

### 7.2 Rec.2100 HDR Color Space Integration

HDR video pipelines target the **Rec.2100** container, which combines:
- **Primaries**: Rec.2020 (covering ~75.8% of CIE 1931)
- **Transfer function**: PQ (SMPTE ST 2084) or HLG (BT.2100)
- **Peak luminance**: 1000–10000 nits

Key ISP integration steps:
1. Internal processing in linear light (scene-referred) domain
2. Apply PQ/HLG OETF before encoding
3. Compute HDR metadata (MaxCLL, MaxFALL) from output in real time

**Gamut coverage numbers and practical implications:**

| Color Space | CIE 1931 Coverage | Peak Luminance | Primary Use Case |
|-------------|-------------------|----------------|-----------------|
| sRGB | 35.9% | 80–100 nits SDR | JPEG, web, consumer display |
| Display P3 | 45.5% | 500–1000 nits | Mobile flagship, macOS |
| Rec.2020 | 75.8% | ≤10000 nits (with PQ) | 4K/8K HDR broadcast, cinema |
| DCI-P3 | ~45.5% | 48 nits (DCI spec) | Cinema digital projection |

For mobile ISP, Display P3 capture is the practical 2024 target. True Rec.2020 capture requires sensors with primaries closer to the spectral locus — most current smartphone sensors can cover 70–80% of Rec.2020 via computational gamut extension (extrapolation from the sensor's native color space), but with increasing color noise near the gamut boundary.

---

## §8 Glossary Additions

**PQ (Perceptual Quantizer, SMPTE ST 2084)**
The absolute HDR transfer function used in HDR10 and Dolby Vision. Maps code values to absolute luminance (0–10000 cd/m²). Because it is absolute, metadata (MaxCLL, MaxFALL) must accompany the bitstream so displays can adapt. Required for any mobile device producing HDR10 video.

**HLG (Hybrid Log-Gamma)**
The relative, scene-referred HDR transfer function (ARIB STD-B67 / ITU-R BT.2100). Compatible with SDR displays without conversion. Preferred for live streaming and broadcast because no per-clip metadata is needed. Increasingly used in high-end smartphone video modes.

**OKLab**
A perceptually uniform color space (Björn Ottosson, 2020) improving on CIELAB's hue uniformity and chroma consistency. Derived from fitting to visual matching data. Useful in ISP for skin tone detection, selective color protection, and perceptual color grading.

**Gamut Mapping**
The process of converting colors from a source color space (e.g., Rec.2020) to a destination space (e.g., Display P3 or sRGB) when out-of-gamut colors exist. Strategies: clipping (fast but hue-distorting), soft-knee compression (preserves hue relationships), and perceptual intent (compresses entire gamut uniformly). ISP must apply gamut mapping at the output stage when delivering P3-wide captures to sRGB displays.

**MaxCLL / MaxFALL**
HDR10 metadata fields: Maximum Content Light Level (peak pixel luminance in nits over the entire video) and Maximum Frame Average Light Level (peak frame-average luminance). Required for HDR10 delivery. ISP must measure these from the encoded output frames and embed them in the container.

---

## §9 Engineering Recommendations for Color Space Selection in Mobile ISP

The following recommendations are for algorithm engineers designing the color pipeline of a mobile ISP.

**1. Internal processing: always linear light**
All ISP modules (demosaicing, denoising, AWB, tone mapping, sharpening) should operate in linear light (linear sensor units or linear sRGB). Applying these algorithms in gamma-encoded space introduces non-linearities that are difficult to compensate and cause visible artifacts, particularly in shadow regions.

**2. Output color space selection**
- For JPEG/HEIF still capture: encode in Display P3 with sRGB OETF for maximum compatibility. Flagship Android and iOS devices since 2020 support P3-tagged HEIF.
- For video: offer HLG for HDR video (broadcast-compatible, no metadata complexity) and Dolby Vision/HDR10 (PQ) for cinematic capture on premium devices.
- For computational photography (multi-frame HDR, Night Mode): process in FP16 linear light; tone map and gamut map as the final step.

**3. AWB and CCM under HDR**
In HDR mode, the AWB should estimate the illuminant from a lower exposure frame to avoid bias from highlight clipping. The CCM should remain trained on D65 reference even in HDR mode — PQ/HLG encoding does not change the chromaticity targets.

**4. OKLab for perceptual quality features**
For skin tone protection, selective saturation, or hue rotation effects, implement the processing in OKLab rather than CIELAB. The improved hue linearity reduces hue-shift side effects when boosting saturation in one region of the color gamut.

**5. Gamut coverage validation**
During sensor and tuning qualification, measure color gamut coverage using a spectrophotometer and the ITP color space (used in HDR evaluation). Report: sRGB coverage %, P3 coverage %, and Rec.2020 coverage %. Set a minimum threshold of >99% sRGB coverage and >90% P3 coverage under D65 illuminant for flagship-tier qualification.

---

## References

1. **CIE Publication 15:2004** — *Colorimetry*, 3rd edition. Commission Internationale de l'Éclairage.

2. **IEC 61966-2-1:1999** — *Multimedia systems and equipment — Colour measurement and management — Part 2-1: Colour management — Default RGB colour space — sRGB.*

3. **Sharma, G., Wu, W., & Dalal, E. N. (2005).** "The CIEDE2000 color-difference formula: Implementation notes, supplementary test data, and mathematical observations." *Color Research & Application*, 30(1), 21–30.

4. **Hunt, R. W. G., & Pointer, M. R. (2011).** *Measuring Colour*, 4th edition. Wiley-IS&T Series in Imaging Science and Technology.

5. **Fairchild, M. D. (2013).** *Color Appearance Models*, 3rd edition. Wiley-IS&T.

6. **Reinhard, E., Heidrich, W., Debevec, P., Pattanaik, S., Ward, G., & Myszkowski, K. (2010).** *High Dynamic Range Imaging: Acquisition, Display, and Image-Based Lighting*, 2nd edition. Morgan Kaufmann.

7. **colour-science contributors (2024).** *colour — a Python package implementing colour science.* https://www.colour-science.org/. (Open source, BSD license.)

8. **X-Rite (2009).** *ColorChecker Classic spectral data.* Available via the `colour` library: `colour.SDS_COLOURCHECKERS`.

9. **McCamy, C. S. (1992).** "Correlated color temperature as an explicit function of chromaticity coordinates." *Color Research & Application*, 17(2), 142–144.

10. **ITU-R BT.709-6 (2015).** *Parameter values for the HDTV standards for production and international programme exchange.*

11. **ITU-R BT.2020-2 (2015).** *Parameter values for ultra-high definition television systems for production and international programme exchange.*

12. **DXOMark (2024).** *DXOMark Mobile Benchmark Methodology.* https://www.dxomark.com/ranking/

13. **Karaimer, H. C., & Brown, M. S. (2016).** "A Software Platform for Manipulating the Camera Imaging Pipeline." *ECCV 2016.*

14. **Li, Z., Snavely, N., et al. (2018).** "Learning-Based Color/Tone Mapping for Practical Camera ISP Pipelines." *CVPR 2018 workshop.*
