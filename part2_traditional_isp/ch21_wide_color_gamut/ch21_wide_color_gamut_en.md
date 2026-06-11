# Part 2, Chapter 21: Wide Color Gamut & HDR Color Pipeline

> **Position in series:** Part 2 Chapter 20 (HDR Display Pipeline) → **Wide Color Gamut & HDR Color Pipeline** (this chapter) → Part 2 Chapter 22 (Multi-Camera Fusion Color Consistency)
> **Prerequisites:** Part 2 Chapter 7 (Gamma & Tone Mapping), Part 2 Chapter 20 (HDR Display Pipeline), Part 1 Chapter 5 (Color Science Fundamentals)
> **Target readers:** ISP algorithm engineers, display pipeline engineers, color science engineers

---

## §1 Theory

### 1.1 Color Gamut Standards

**Color Gamut (色域)** is the complete set of colors that an imaging or display system can represent. On the CIE 1931 xy chromaticity diagram, it is defined by the triangle formed by the coordinates of the three primary colors.

**Major color gamut standards (ordered by area, smallest to largest):**

| Standard | Application | sRGB Coverage | DCI-P3 Coverage | BT.2020 Coverage |
|----------|-------------|--------------|-----------------|-----------------|
| **sRGB / BT.709** | Internet, SDR displays, broadcast TV | 100% | ~73% | ~36% |
| **DCI-P3** | Digital cinema, Apple Display P3 | Contains sRGB | 100% | ~54% |
| **Adobe RGB** | Professional photography, print | Contains sRGB | ~90% | ~52% |
| **BT.2020 / Rec.2020** | 4K/8K UHD, HDR broadcast | Contains sRGB | Contains P3 | 100% |

**Evolution of color gamut in smartphone photography:**
- Before 2017: output was essentially sRGB
- 2017–2020: Apple introduced Display P3; P3 became standard on smartphones
- After 2020: RAW formats (ProRAW/RAW+) preserve the sensor's native wide color gamut; post-processing can output BT.2020

**Key formula — Gamut Coverage (色域覆盖率):**

$$\text{Coverage} = \frac{\text{Area of target gamut triangle} \cap \text{Area of reference gamut triangle}}{\text{Area of reference gamut triangle}}$$

The area in the CIE xy chromaticity diagram is computed using the vector cross-product (Shoelace formula):

$$A = \frac{1}{2} \left| \sum_{i=0}^{2} (x_i y_{i+1} - x_{i+1} y_i) \right|$$

### 1.2 Relationship Between HDR and WCG

HDR (High Dynamic Range) and WCG (Wide Color Gamut) are technically independent, but are typically delivered together in consumer products:

$$\text{HDR Display} \Leftrightarrow \text{High Peak Luminance} + \text{Wide Color Gamut} + \text{High Bit Depth}$$

| Property | Typical SDR | Typical HDR |
|----------|------------|------------|
| Peak luminance | 100–300 nit | 1000–10000 nit |
| Black level | 0.3–1.0 nit | < 0.005 nit (with local dimming) |
| Color gamut | sRGB (BT.709) | Display P3 / BT.2020 |
| Bit depth | 8-bit | 10-bit / 12-bit |

**Physical motivation:** The BT.2020 green primary (x=0.170, y=0.797) and blue primary (x=0.131, y=0.046) correspond to highly saturated colors whose high-luminance versions (e.g., saturated green at 1000 nit) simply cannot be represented within the sRGB gamut. Therefore, HDR content **must** use a wide color gamut.

### 1.3 HDR Transfer Standards: HDR10, HLG, and Dolby Vision

#### 1.3.1 HDR10 (Static Metadata)

**HDR10** is an open standard (SMPTE ST 2084 + SMPTE ST 2086) based on the PQ (Perceptual Quantizer) electro-optical transfer function:

$$\text{PQ EOTF:} \quad L = \left( \frac{\max(V^{1/m_2} - c_1, 0)}{c_2 - c_3 V^{1/m_2}} \right)^{1/m_1}$$

where the parameters are: $m_1 = 0.1593017578125$, $m_2 = 78.84375$, $c_1 = 0.8359375$, $c_2 = 18.8515625$, $c_3 = 18.6875$

**Key characteristics:**
- 10-bit encoding, BT.2020 color gamut
- **Static metadata** (MaxCLL, MaxFALL): a single set of tone-mapping parameters applies to the entire content
- Broadest adoption: UHD Blu-ray, Netflix, Disney+

#### 1.3.2 HLG (Hybrid Log-Gamma)

**HLG (Hybrid Log-Gamma, ARIB STD-B67 / ITU-R BT.2100)** is an HDR standard designed for broadcast television:

$$\text{HLG OETF:} \quad E = \begin{cases} \sqrt{3L} & 0 \leq L \leq \frac{1}{12} \\ a \ln(12L - b) + c & L > \frac{1}{12} \end{cases}$$

where $a = 0.17883277$, $b = 0.28466892$, $c = 0.55991073$

**Key characteristics:**
- **Backwards compatible with SDR:** an SDR display can interpret the HLG signal as SDR and display it without any metadata
- Suitable for live broadcast (where static metadata cannot be computed in advance)
- Widely used in smartphone video recording (e.g., iPhone "Video HDR" records in HLG format)

#### 1.3.3 Dolby Vision (Dynamic Metadata)

Dolby Vision (SMPTE ST 2094-10) extends HDR10 by adding **per-scene/per-frame** dynamic metadata, enabling the display device to perform optimal tone mapping on every individual frame:

| Feature | HDR10 | Dolby Vision |
|---------|-------|-------------|
| Metadata type | Static (one set for entire content) | Dynamic (per frame) |
| Bit depth | 10-bit | 10-bit or 12-bit |
| Tone mapping | Handled by the display itself | Precisely guided by Dolby |
| Licensing | Free | Requires license |
| Smartphone support | Universal | Flagship models (iPhone 12+, Xiaomi 13+) |

### 1.4 Gamut Mapping (色域映射)

**Gamut mapping** is the process of mapping colors from a source gamut (e.g., BT.2020) to a target gamut (e.g., sRGB). The core challenge is that BT.2020 contains a large number of colors that fall outside the sRGB triangle (gamut out-of-range). Direct clipping destroys color relationships.

**Main gamut mapping algorithms:**

#### 1.4.1 Linear Compression

$$\mathbf{p}_\text{out} = \mathbf{M}_\text{src→XYZ} \cdot \mathbf{p}_\text{src}$$
$$\mathbf{p}_\text{dst} = \mathbf{M}_\text{XYZ→dst} \cdot \mathbf{p}_\text{XYZ}$$

A matrix transform through the XYZ color space, with out-of-range values hard-clipped. Computationally simple, but highly saturated colors are clipped abruptly, causing visible hue shifts (色带) and banding.

#### 1.4.2 CUSP Compression (Soft Clipping)

In a perceptually uniform color space such as JzAzBz or ICtCp, the hue angle is held constant while only the chroma (色度) and lightness (亮度) components are compressed:

$$C_\text{out} = f(C_\text{in}) = C_\text{in} \cdot \frac{C_\text{max,dst}}{C_\text{max,src}}$$

**Knee function (soft clipping):**

$$f(x) = \begin{cases} x & x < x_0 \\ x_0 + (C_\text{max} - x_0) \cdot \left(1 - e^{-(x - x_0)/(C_\text{max} - x_0)}\right) & x \geq x_0 \end{cases}$$

#### 1.4.3 ICC Color Profiles (Perceptual Rendering Intent)

The International Color Consortium (ICC) defines four rendering intents (渲染目的):

| Rendering Intent | Principle | Recommended Use |
|-----------------|-----------|----------------|
| **Perceptual** | Compresses the entire gamut while preserving color relationships | Natural images; recommended default |
| **Relative Colorimetric** | White-point adaptation with accurate color matching | Professional print calibration |
| **Absolute Colorimetric** | No white-point adaptation | Proof simulation |
| **Saturation** | Preserves vividness | Charts and business graphics |

### 1.5 Position of WCG Processing in the ISP Pipeline

```
RAW → BLC → Demosaic → AWB → CCM(sRGB) → [Gamut Expansion / WCG Processing] → Gamma/TM → YUV/Output
                                   ↑                                                    ↑
                        Traditional pipeline ends here                   WCG pipeline operates here
                            (outputs sRGB)                           (HDR Tone Mapping + Gamut Mapping)
```

**Key decision points:**
1. **CCM matrix color space:** A standard CCM outputs sRGB; in WCG mode, the CCM outputs P3 or BT.2020 (different matrix coefficients)
2. **Tone mapping curve:** SDR uses sRGB gamma 2.2; HDR uses PQ or HLG
3. **Output encoding:** HDR content requires 10-bit or 12-bit (8-bit sRGB is insufficient to encode BT.2020 + HDR luminance)

---

## §2 Calibration

### 2.1 WCG CCM Calibration

Compared to standard CCM calibration (Part 2 Chapter 7), WCG CCM calibration differs in the following ways:

**Change in target color space:**
- Standard: sensor RGB → sRGB (BT.709 primaries)
- Wide color gamut: sensor RGB → Display P3 (DCI-P3 primaries) or BT.2020

**Change in calibration reference values:**

| Color patch | sRGB reference (D65) | Display P3 reference (D65) |
|-------------|---------------------|---------------------------|
| White (N9.5) | [243, 243, 242] | [252, 252, 251] |
| Pure red | [175, 54, 60] | [234, 51, 35] (more saturated) |
| Pure green | [70, 148, 73] | [19, 182, 59] (more vivid) |

**Row-sum constraint for the P3 CCM:** Same as the sRGB CCM — each row must sum to 1, ensuring that white maps to white.

**Acceptance criterion:** Under the Display P3 reference, target $\overline{\Delta E_{00}} < 2.5$ (slightly more relaxed than the sRGB standard, because the P3 gamut is larger and edge colors are harder to calibrate precisely).

### 2.2 PQ / HLG Electro-Optical Transfer Function Calibration

**PQ peak luminance calibration:**

The PQ encoding assumes a display peak luminance of 10000 nit, but actual smartphone screens reach only 1000–2000 nit. Therefore, the PQ signal must be remapped according to the actual screen peak luminance:

$$\text{PQ}_\text{remapped}(L) = \text{PQ}\left(L \cdot \frac{L_\text{screen,peak}}{10000}\right)$$

**HLG system gamma parameter (ITU-R BT.2100):**

$$\gamma = 1.2 + 0.42 \log_{10}\left(\frac{L_\text{peak}}{1000}\right)$$

Typical values: at $L_\text{peak} = 1000$ nit, $\gamma = 1.2$; at $L_\text{peak} = 2000$ nit, $\gamma \approx 1.33$.

### 2.3 Multi-Camera Color Consistency Calibration

In a multi-camera system (main camera + ultrawide + telephoto), the different sensor models produce color deviations in wide-gamut output:

**Calibration procedure:**
1. Use the main camera as reference; capture ColorChecker and Macbeth chart
2. Compute CCMs in P3/BT.2020 color space separately for each camera
3. Compute a **cross-camera correction matrix** that maps each secondary camera's colors to the main camera's colors (removing sensor-to-sensor differences)
4. Acceptance criterion: color deviation on camera switch $\Delta E_{00} < 1.5$ (below the threshold of human visibility)

---

## §3 Tuning

### 3.1 Color Space Mode Switching Strategy

A smartphone ISP typically supports multiple color gamut output modes that are switched dynamically based on the use case:

| Mode | Color Gamut | Use Case | Bit Depth |
|------|------------|----------|-----------|
| Standard mode | sRGB | Photo sharing, social media | 8-bit |
| Photo professional mode | Display P3 | Local storage, professional editing | 10-bit |
| ProRAW / Professional video | Sensor native (close to BT.2020) | Post-production | 12-bit |
| Video HDR (HLG) | BT.2020 | Video capture + HDR display | 10-bit |
| Dolby Vision video | BT.2020 (12-bit) | High-end video on flagship devices | 12-bit |

**Mode switching decision logic:**

```
User selection → Scene detection → Color space / TM parameter update
     ↓                ↓
Photo / Video    HDR content / Normal scene
Standard / Pro   PQ / HLG / SDR gamma
```

### 3.2 Tone Mapping Parameter Tuning

**Key PQ tone mapping parameters:**

| Parameter | Meaning | Tuning Range |
|-----------|---------|-------------|
| `MaxCLL` (Max Content Light Level) | Maximum luminance of any single pixel in the content | 1000–4000 nit (scene-dependent) |
| `MaxFALL` (Maximum Frame-Average Light Level) | Maximum average luminance across all frames | 100–400 nit |
| `MinCLL` (Min Content Light Level) | Minimum luminance | 0.001–0.01 nit |

**Tone mapping knee curve tuning:**

```
HDR content luminance (nit)
10000 |              ___________  ← PQ full-scale
      |           __/
      |         _/
1000  |        / ← Knee point
      |      _/
      |    _/
100   |  _/  ← Linear region
      | /
0     |/____________
      0    SDR display luminance (nit)    1000
```

- **Knee point position:** typically set at the SDR peak luminance (300–600 nit); luminance below the knee is mapped linearly, and luminance above is compressed
- **Compression ratio:** depends on the display's HDR capability; a 1000 nit screen requires far less compression than a 400 nit screen

### 3.3 Saturation Protection

When expanding from a small gamut (sRGB) to a large gamut (P3/BT.2020), a simple matrix transform cannot be applied directly — it may produce perceptually unnatural "neon" (荧光色) artifacts:

**Saturation gain limit:**

$$C_\text{out} = \min(C_\text{expanded}, C_\text{max,natural} \cdot (1 + k_\text{boost}))$$

Typical value: $k_\text{boost} = 0.15–0.30$ (allowing at most 15–30% saturation boost above the reference value)

**Skin tone protection:** In the ICtCp or JzAzBz color space, identify the skin tone locus and limit the saturation gain for pixels within that region (to prevent skin from appearing fluorescent).

### 3.4 Key WCG Parameter Comparison Across Three Platforms

| Parameter Function | Qualcomm CamX | MTK Imagiq | HiSilicon Yueying |
|-------------------|--------------|------------|------------------|
| Color space selection | `ColorSpace` (sRGB/P3/BT2020) | `CSC_OutputColorSpace` | `ISP_ColorSpace` |
| CCM matrix (P3) | `CCM_P3_Matrix[3x3]` | `CCM_Matrix_P3[9]` | `ISP_CCM_P3` |
| PQ/HLG switching | `HDR_EOTF` (PQ/HLG/SDR) | `HDR_CurveType` | `ISP_HDR_OETF` |
| MaxCLL setting | `HDR_MaxCLL` | `HDRMaxCLL` | `ISP_MaxCLL` |
| Gamut mapping algorithm | `GamutMappingMode` (clip/perceptual) | `GamutMapMode` | `ISP_GamutMode` |
| WCG bit depth | `OutputBitDepth` (8/10/12) | `OutputBitWidth` | `ISP_OutputDepth` |

---

## §4 Artifacts

### 4.1 Hue Shift at Gamut Boundary (色带)

**Symptom:** Highly saturated colors (e.g., vivid red, fluorescent green) exhibit an abrupt hue shift at the gamut boundary — for example, saturated red becomes orange-red.

**Cause:** Linear clipping maps colors outside the sRGB triangle directly to the triangle boundary, changing the hue angle in the process.

**Mitigation:** Perform chroma compression (rather than clipping) in a perceptually uniform color space (ICtCp, JzAzBz), preserving the hue angle.

### 4.2 Oversaturated Neon Appearance (荧光感)

**Symptom:** After wide-gamut expansion, the image develops an unnaturally vivid, fluorescent quality — especially visible in green foliage and sky.

**Cause:** The matrix expansion from sRGB to P3/BT.2020 is too aggressive, pushing even mid-saturation colors far toward the gamut boundary.

**Mitigation:** Limit the saturation gain (see §3.3) and apply knee compression in the high-saturation region.

### 4.3 Cross-Camera Color Jump

**Symptom:** Switching between the main camera, ultrawide, and telephoto produces a visible hue or saturation difference (approximately $\Delta E_{00} > 2$).

**Cause:** The P3/BT.2020 CCMs for each camera have not been calibrated for cross-camera color consistency.

**Mitigation:** Apply the multi-camera cross-correction matrix (§2.3) combined with transition frame smoothing (blend over 2–3 frames during camera switch).

### 4.4 HDR Content Overexposed on SDR Displays

**Symptom:** HLG/PQ-encoded video appears significantly overexposed on displays that do not support HDR; highlight detail is completely lost.

**Cause:** An SDR display treats the PQ high-luminance encoded values as direct linear luminance, causing the entire highlight range to exceed the display's output capability.

**Mitigation:**
- HLG provides SDR backward compatibility (acceptable appearance on SDR displays)
- PQ content must pass through tone mapping before it can be correctly displayed on an SDR display
- Provide an SDR fallback stream (Dolby Vision Profile 8) or implement automatic downgrade detection

---

## §5 Evaluation

### 5.1 Gamut Coverage Measurement

**Measurement tools:** Calman (Portrait Displays), X-Rite i1Display Pro, Konica Minolta CS-100A

**Measurement procedure:**
1. Display standard gamut test patterns (ITU-R BT.709/P3/BT.2020 primaries + white)
2. Measure the actual chromaticity coordinates $(x, y)$ with a colorimeter
3. Compute: area of measured gamut triangle / area of standard gamut = coverage

**Acceptance criteria (smartphone industry reference):**

| Metric | Pass | Excellent |
|--------|------|-----------|
| sRGB coverage | > 95% | 100% |
| P3 coverage | > 90% | > 99% |
| Color temperature deviation | ΔCCx < 0.005 | ΔCCx < 0.002 |
| Grayscale $\Delta E_{00}$ | < 3.0 | < 1.5 |

### 5.2 HDR Tone Mapping Quality Evaluation

**Objective metrics:**
- **HDR-VDP-3** (Mantiuk et al.): A perceptually calibrated HDR visual difference metric that quantifies quality loss from HDR→SDR compression
- **μ-PSNR** (for HDR content): computes PSNR in the logarithmic luminance domain; more perceptually meaningful than linear-domain PSNR
- **TMQI** (Tone Mapping Quality Index): an index specifically designed to evaluate tone-mapped images for structural fidelity and statistical naturalness

**Subjective evaluation (MOS — Mean Opinion Score):**
- Evaluation dimensions: highlight detail preservation, shadow gradation, color naturalness, overall contrast
- Display environment: must be performed on an HDR-capable display (Apple XDR, Samsung QLED, etc.)

### 5.3 Cross-Camera Color Consistency Evaluation

Under a standard D65 illuminant, capture a ColorChecker sequentially with the main camera, ultrawide, and telephoto. Compute the $\Delta E_{00}$ between each camera's output and the reference, as well as the $\Delta E_{00}$ between pairs of cameras:

| Camera pair | Pass criterion | Excellent criterion |
|-------------|---------------|-------------------|
| Main camera vs. reference | $\Delta E_{00} < 2.5$ | $< 1.5$ |
| Secondary camera vs. main | $\Delta E_{00} < 2.0$ | $< 1.0$ |

---

## §6 Code

```python
"""
wcg_gamut_coverage.py
Gamut coverage calculation and gamut mapping demonstration

Dependencies: numpy, matplotlib, colour-science (pip install colour-science)
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ── Standard color gamut primaries in CIE xy coordinates ──────────────────────
GAMUTS = {
    "sRGB / BT.709": {
        "R": (0.640, 0.330), "G": (0.300, 0.600), "B": (0.150, 0.060),
        "color": "#E74C3C", "linestyle": "--"
    },
    "DCI-P3": {
        "R": (0.680, 0.320), "G": (0.265, 0.690), "B": (0.150, 0.060),
        "color": "#2ECC71", "linestyle": "-."
    },
    "BT.2020": {
        "R": (0.708, 0.292), "G": (0.170, 0.797), "B": (0.131, 0.046),
        "color": "#3498DB", "linestyle": "-"
    },
}

def triangle_area(vertices: list[tuple]) -> float:
    """Compute triangle area using the Shoelace formula"""
    x = [v[0] for v in vertices]
    y = [v[1] for v in vertices]
    n = len(x)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += x[i] * y[j]
        area -= x[j] * y[i]
    return abs(area) / 2.0

def gamut_coverage(src_gamut: dict, ref_gamut: dict) -> float:
    """Compute coverage of src gamut over ref gamut (simplified: triangle area ratio)

    WARNING: This function is only valid for nested gamuts (src ⊇ ref, e.g. P3 over sRGB).
    For non-nested gamuts (e.g. BT.2020 over sRGB), true coverage requires computing
    the intersection area of the two triangles — a simple area ratio will overestimate
    coverage by treating "larger src area" as "higher coverage".
    """
    src_area = triangle_area([src_gamut["R"], src_gamut["G"], src_gamut["B"]])
    ref_area = triangle_area([ref_gamut["R"], ref_gamut["G"], ref_gamut["B"]])
    return min(src_area / ref_area, 1.0)  # valid only for nested gamuts

def plot_gamut_diagram():
    """Plot gamut triangles on the CIE xy chromaticity diagram"""
    fig, ax = plt.subplots(1, 1, figsize=(8, 7))
    ax.set_facecolor("#F8F9FA")
    fig.patch.set_facecolor("#F8F9FA")

    # Draw each gamut triangle
    for name, g in GAMUTS.items():
        vertices = [g["R"], g["G"], g["B"], g["R"]]
        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        ax.plot(xs, ys, color=g["color"], linestyle=g["linestyle"],
                linewidth=2, label=name)
        # Fill
        tri = patches.Polygon([g["R"], g["G"], g["B"]],
                                alpha=0.08, facecolor=g["color"])
        ax.add_patch(tri)
        # Mark primaries
        for ch, pos in [("R", g["R"]), ("G", g["G"]), ("B", g["B"])]:
            ax.plot(*pos, "o", color=g["color"], markersize=6)

    # D65 white point
    ax.plot(0.3127, 0.3290, "w+", markersize=12, markeredgecolor="black", label="D65 White Point")

    ax.set_xlabel("CIE x", fontsize=11)
    ax.set_ylabel("CIE y", fontsize=11)
    ax.set_xlim(0.0, 0.8)
    ax.set_ylim(0.0, 0.9)
    ax.set_title("Color Gamut Standards Comparison: sRGB / DCI-P3 / BT.2020",
                 fontsize=12, fontweight="bold")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(
        "<handbook_root>/"
        "part2_traditional_isp/ch21_wide_color_gamut/img/fig21_1_gamut_comparison.png",
        dpi=150, bbox_inches="tight"
    )
    print("Saved gamut comparison figure")
    plt.close()

# ── PQ / HLG transfer functions ───────────────────────────────────────────────
def pq_eotf(V: np.ndarray) -> np.ndarray:
    """PQ EOTF: encoded value V [0,1] → absolute luminance L [nit]"""
    m1, m2 = 0.1593017578125, 78.84375
    c1, c2, c3 = 0.8359375, 18.8515625, 18.6875
    Vm2 = V ** (1 / m2)
    L = ((np.maximum(Vm2 - c1, 0) / (c2 - c3 * Vm2)) ** (1 / m1)) * 10000
    return L

def hlg_oetf(L: np.ndarray) -> np.ndarray:
    """HLG OETF: scene luminance L → encoded value E"""
    a, b, c = 0.17883277, 0.28466892, 0.55991073
    E = np.where(L <= 1/12, np.sqrt(3 * L), a * np.log(12 * L - b) + c)
    return E

if __name__ == "__main__":
    import os
    os.makedirs(
        "<handbook_root>/"
        "part2_traditional_isp/ch21_wide_color_gamut/img",
        exist_ok=True
    )
    plot_gamut_diagram()

    # Print gamut coverage
    print("\n=== Gamut Coverage (area approximation) ===")
    for name, g in GAMUTS.items():
        area = triangle_area([g["R"], g["G"], g["B"]])
        srgb_area = triangle_area([
            GAMUTS["sRGB / BT.709"]["R"],
            GAMUTS["sRGB / BT.709"]["G"],
            GAMUTS["sRGB / BT.709"]["B"]
        ])
        print(f"{name}: area = {area:.4f}, relative to sRGB = {area/srgb_area*100:.1f}%")
```

---

## §7 Extended Topics

### 7.1 ICtCp Color Space

ICtCp (ITU-R BT.2100) is a perceptually uniform color space proposed by Dolby, specifically designed for color difference calculation and gamut mapping in HDR/WCG content:

$$\begin{bmatrix} I \\ C_T \\ C_P \end{bmatrix} = \mathbf{M}_2 \cdot \text{PQ}\left(\mathbf{M}_1 \cdot \begin{bmatrix} R \\ G \\ B \end{bmatrix}_\text{BT.2020}\right)$$

**Comparison with CIE Lab:** ICtCp achieves 3–4× better perceptual uniformity than CIE Lab across the HDR luminance range (0.001–10000 nit), and $\Delta E_\text{ICtCp}$ shows stronger correlation with MPEG HDR subjective evaluation results.

### 7.2 JzAzBz Color Space

JzAzBz (Safdar et al. 2017) is another perceptually uniform space designed for HDR content. Compared to ICtCp, it provides better uniformity at extreme luminance levels (>1000 nit) and is commonly used as the intermediate computation space in HDR tone mapping algorithms.

### 7.3 Apple ProRes RAW and Wide Color Gamut

Apple ProRes RAW encapsulates raw sensor data directly into a ProRes file, preserving the sensor's native wide color gamut (close to BT.2020). Gamut mapping is deferred to post-production software such as Final Cut Pro at output time. This represents a "defer gamut decisions to post" workflow — a fundamentally different approach from the traditional ISP model, in which gamut mapping is completed inside the camera.

---

## References

1. IEC 61966-2-1:1999 — sRGB Standard (International Electrotechnical Commission).
2. ITU-R BT.2020 (2015). *Parameter values for ultra-high definition television systems*. ITU.
3. ITU-R BT.2100 (2018). *Image parameter values for HDR television for use in production and international programme exchange*. ITU.
4. SMPTE ST 2084:2014. *High Dynamic Range EOTF of Mastering Reference Displays*. SMPTE.
5. SMPTE ST 2086:2018. *Mastering Display Color Volume Metadata*. SMPTE.
6. Dolby Laboratories (2016). *Dolby Vision Streams Within the IMF Package*. Dolby Technical Guidance.
7. Mantiuk, R., et al. (2011). HDR-VDP-2: A calibrated visual metric for comparing any two images in any dynamic range. *ACM Transactions on Graphics*, 30(4).
8. Safdar, M., et al. (2017). Perceptually uniform color space for image signals including high dynamic range and wide color gamut. *Optics Express*, 25(13), 15131.
9. ITU-R BT.2407 (2017). *Colour gamut conversion from Recommendation ITU-R BT.2020 to Recommendation ITU-R BT.709*. ITU-R. *(Original citation "Lu et al., IS&T EI 2023" could not be verified and has been replaced with this authoritative ITU-R gamut conversion reference.)*
10. Apple Inc. (2022). *Working with HDR Video: HLG and Dolby Vision on Apple Devices*. developer.apple.com.

---

## §8 Glossary

**Wide Color Gamut (WCG, 宽色域)**
A color gamut capable of representing a larger range of colors than sRGB/BT.709. The main WCG standards are DCI-P3 (digital cinema, approximately 26% larger than sRGB) and BT.2020 (UHD broadcast, approximately 2.65× the area of sRGB on the CIE xy chromaticity diagram; approximately 62% of BT.2020's area lies outside sRGB, making gamut mapping the primary challenge for HDR wide-gamut content). Smartphone photography currently uses Display P3 as its primary WCG standard.

**PQ (Perceptual Quantizer, SMPTE ST 2084)**
The electro-optical transfer function for HDR content. It uses absolute luminance encoding, with full scale corresponding to 10000 nit. The minimum luminance resolution of 0.01 nit matches the human visual system's just-noticeable difference (JND), making it approximately 30× more perceptually efficient than Gamma 2.2 in the high-luminance region. Used in HDR10 and Dolby Vision formats.

**HLG (Hybrid Log-Gamma, ITU-R BT.2100)**
The HDR standard for broadcast television. It uses a square-root (gamma-like) curve for low luminance and a logarithmic curve for high luminance. Its key advantage is **SDR backward compatibility** — an HLG signal can be interpreted by an SDR display as Gamma 2.0 and displayed without any additional tone mapping. Well suited for live broadcast and smartphone video recording.

**Gamut Mapping (色域映射)**
The process of mapping colors from a source gamut (e.g., BT.2020) to a target gamut (e.g., sRGB). Simple clipping causes hue shifts; production-grade solutions perform chroma compression in a perceptually uniform color space (ICtCp, JzAzBz), preserving the hue angle throughout.

**ICtCp**
A perceptually uniform color space defined in ITU-R BT.2100, where $I$ represents Intensity (luminance), $C_T$ represents Tritan (blue-yellow) chroma, and $C_P$ represents Protan (red-green) chroma. Its perceptual uniformity across the HDR luminance range surpasses that of CIE Lab, making it the recommended working space for HDR color difference calculation and gamut mapping.

**HDR10**
An open HDR standard based on PQ + BT.2020 + 10-bit + static metadata (MaxCLL/MaxFALL). The static metadata means the entire piece of content uses a single set of tone-mapping parameters with no per-frame optimization; Dolby Vision addresses this limitation with per-frame dynamic metadata.

**Dolby Vision**
Dolby's proprietary HDR format, which extends HDR10 with dynamic metadata (a separate set of tone-mapping parameters per frame or per scene), supports 12-bit encoding, and gives the display device precise guidance for tone mapping. Visual quality typically exceeds HDR10. Requires a licensing fee.

**MaxCLL / MaxFALL (HDR10 static metadata)**
- MaxCLL (Maximum Content Light Level): the maximum luminance of any single pixel in the content (nit)
- MaxFALL (Maximum Frame-Average Light Level): the maximum value of the per-frame average luminance across all frames (nit)

These values guide the display in selecting appropriate tone-mapping parameters.

**Gamut Coverage (色域覆盖率)**
The proportion of the source gamut that falls within the target gamut, computed as a triangle area ratio on the CIE xy chromaticity diagram. For example, Display P3 covers approximately **~99%** of sRGB (P3 nearly fully contains sRGB; P3's own area is approximately 26% larger than sRGB). BT.2020 has approximately 2.65× the area of sRGB, with approximately 62% of BT.2020's area lying outside sRGB.
