# Part 2, Chapter 25: RAW Video and Cinema ISP Pipeline

> **Scope:** This chapter covers the engineering implementation of professional RAW video recording and post-production ISP pipelines — from sensor Log encoding and CinemaDNG/BRAW format parsing to the color management chain in DaVinci Resolve/Lightroom, with a detailed analysis of the underlying mechanisms behind smartphone ProRes/Log modes.
> **Prerequisites:** Volume 1, Chapter 6 (RAW Format and CFA Patterns); Volume 2, Chapter 8 (Gamma and Tone Mapping)
> **Target Readers:** Algorithm engineers, imaging engineers

---

## Table of Contents

1. [Log Encoding Theory](#1-log-encoding-theory)
2. [RAW Video Formats](#2-raw-video-formats)
3. [Cinema-Grade ISP Tuning](#3-cinema-grade-isp-tuning)
4. [Common Artifacts and Issues](#4-common-artifacts-and-issues)
5. [Evaluation Methods](#5-evaluation-methods)
6. [Code Examples](#6-code-examples)
7. [References](#7-references)
8. [Glossary](#8-glossary)

---

## §1 Log Encoding Theory

### 1.1 Fundamental Motivation for Dynamic Range Extension

Under linear exposure, the raw photoelectric response (Scene-Linear) of a camera sensor is directly proportional to scene luminance. However, if the output of a sensor with 14–15 stops of dynamic range is quantized directly as an 8-bit integer, the shadows receive very few quantization levels, resulting in dark-area noise and tonal banding. The essence of Log Encoding (对数编码) is to apply a logarithmic transform to the linear signal so that equal perceptual differences correspond to equal quantization steps, thereby distributing the limited bit depth evenly across the dynamic range that is perceptually uniform to the human eye.

From an information-theoretic perspective, the human visual system's luminance perception approximates the Weber-Fechner Law (韦伯-费希纳定律), whereby a perceived change in brightness is proportional to the ratio of stimulus change to stimulus intensity. Log encoding precisely matches this perceptual characteristic, ensuring that shadow detail and highlight information both retain sufficient signal-to-noise ratio within a 16-bit Log file.

### 1.2 S-Log2 / S-Log3 Mathematical Model (Sony)

The Sony S-Log series is among the most widely used Log curves in professional video production today.

**S-Log2** (targeting the S-Gamut color space) uses the following encoding formula:

```
If x ≥ 0 (linear scene luminance, normalized so that 18% gray = 0.18):
  S-Log2(x) = (0.432699 × log10(x/0.9 + 0.037584) + 0.616596) + 0.03

If x < 0 (clipped to 0)
```

S-Log2 has a nominal dynamic range of approximately 1300% (about 13.5 stops), with 18% gray mapped to roughly 32% of the code value (approximately 347/1023 in 10-bit space).

**S-Log3** (targeting S-Gamut3/S-Gamut3.Cine) introduces a piecewise function for better shadow protection:

```
If x ≥ 0.01125000:
  S-Log3(x) = (420 + log10((x + 0.01) / (0.18 + 0.01)) × 261.5) / 1023

If x < 0.01125000 (linear segment):
  S-Log3(x) = (x × (171.2102946929 - 95) / 0.01125000 + 95) / 1023
```

The lower bound of the S-Log3 linear segment is approximately 0.0014, corresponding to about −7 stops (relative to 18% gray). This design keeps the deepest shadows in an approximately linear relationship above the noise floor, avoiding the amplification of quantization errors that a logarithm function would introduce near zero. S-Log3 has a nominal dynamic range of approximately 1600% (15+ stops), with 18% gray corresponding to roughly 41% of the code value (420/1023, 10-bit).

### 1.3 ARRI Log C Mathematical Model

ARRI Log C (the current latest version being LogC4 for the ALEXA 35) is one of the cinema industry's de facto standards. The basic equation for LogC (third generation, applicable to the ALEXA Classic/Mini/SXT) is as follows:

```
If x ≥ cut (depends on EI):
  LogC(x) = c × log10(a × x + b) + d

If x < cut (linear segment):
  LogC(x) = e × x + f
```

The parameters a, b, c, d, e, f vary with the Exposure Index (EI, 曝光指数), and ARRI publishes standard parameter tables covering EI 160 through EI 3200. The Reference White of LogC corresponds to 90% of the code value (0.9), with 18% gray corresponding to approximately 39.4% (0.394). ARRI LogC4 extends the dynamic range to approximately 17 stops to support the ALEXA 35 sensor.

### 1.4 Apple Log Mathematical Model

Apple Log was introduced with the iPhone 15 Pro as Apple's first officially supported Log encoding format, designed for ProRes video recording.

Key characteristics of Apple Log:
- Reference White mapped to a code value of 0.6099 (10-bit normalized)
- Black Level mapped to a code value of 0.0929
- Nominal dynamic range: approximately 16 stops
- Associated color space: Apple Log Color Space (wide gamut, close to BT.2020 primaries)

The piecewise OETF (Opto-Electronic Transfer Function) of Apple Log:

```
If Lin ≥ -0.01:
  AppleLog(Lin) = 0.212735 × log2(Lin + 0.037584) + 0.848805

If Lin < -0.01 (clipped to linear segment):
  AppleLog(Lin) = 12.92 × (Lin + 0.037584) + 0.424530
```

18% gray (Lin = 0.18) maps to approximately 0.48 in code value, placing it in the midtone region similarly to S-Log3.

### 1.5 Essential Differences Between Log Encoding and Gamma

| Dimension | Gamma Encoding (e.g., Rec.709 BT.1886) | Log Encoding (e.g., S-Log3) |
|-----------|----------------------------------------|------------------------------|
| Mathematical form | Power function y = x^(1/γ) | Logarithmic function y = a×log(x+b)+c |
| Dynamic range | Approximately 6–8 stops | 13–20 stops |
| 18% gray code value | ~42% (Rec.709) | ~41% (S-Log3) |
| Direct viewing appearance | Low contrast but acceptable | Foggy gray, desaturated; requires a LUT to restore |
| Primary use | Broadcast/consumer delivery | Acquisition/post-production intermediate |
| Bit depth requirement | 8-bit sufficient (SDR) | 10-bit minimum (12-bit recommended) |

The core engineering significance of Log encoding is the decoupling of "acquisition" (Camera Original) from "delivery." Maximum dynamic range is retained at acquisition time; in post-production, creative LUTs (Look-Up Tables) can freely shape the tonal style, converting from Log to any delivery target — Rec.709, HDR10, Dolby Vision, etc. — without information loss.

---

## §2 RAW Video Formats

### 2.1 CinemaDNG Format Parsing

CinemaDNG (Cinema Digital Negative, 电影数字负片) is a cinema-grade RAW video format that Adobe extended from the DNG (Digital Negative) specification. At its core, each frame is stored as an individual DNG file, organized sequentially into a folder or MXF container.

**Metadata Structure (key IFD fields):**

```
TIFF/IFD Main Directory:
  - ImageWidth / ImageLength: Frame dimensions
  - BitsPerSample: 12 or 16 bit
  - Compression: Lossless (7/34892) or lossy (approx. 34892 variant)
  - CFAPattern: Bayer pattern (RGGB/GRBG, etc.)
  - CFARepeatPatternDim: [2, 2]

SubIFD (Raw Sub-directory):
  - ActiveArea: Active pixel region [top, left, bottom, right]
  - BlackLevel / WhiteLevel: Black level and white level (linear domain)
  - BaselineExposure: Relative exposure correction (EV)
  - NoiseProfile: [sigma0, sigma1], corresponding to noise model σ² = σ0² + σ1² × μ

Color Science IFD:
  - AsShotNeutral: [R_gain_inv, G_gain_inv, B_gain_inv] (white balance reference)
  - ColorMatrix1 / ColorMatrix2: XYZ→camera 3×3 matrices under two reference illuminants (D65/A)
  - CameraCalibration1 / CameraCalibration2: Per-camera individual calibration matrices
  - ForwardMatrix1 / ForwardMatrix2: Camera→XYZ_D50 mapping matrices
  - CalibrationIlluminant1 / 2: Reference illuminant enumerations (17=D65, 2=A)
```

**Video extension metadata (DNG 1.4+):**
```
  - TimeCodes: SMPTE timecode
  - FrameRate: Frame rate (rational number)
  - OpcodeList2 / OpcodeList3: Lens distortion correction and vignetting correction opcode chains
```

The engineering challenge of CinemaDNG lies in its enormous file size (approximately 25 MB per frame for 4K 12-bit, roughly 3.6 GB/s at 4K 24fps). Commercial products typically use lossy CinemaDNG (based on JPEG 2000 or proprietary compression) to reduce the file size by approximately 5–8×.

### 2.2 Apple ProRes RAW

Apple ProRes RAW (introduced in 2018; ProRes RAW HQ is a higher-quality variant) is Apple's semi-compressed format combining a ProRes container with RAW pixel data.

**Key characteristics:**
- Stores Bayer RAW data using Apple's proprietary variable bit rate compression (not per-frame DNG)
- Embeds ISP parameters in metadata: black level, white balance gain matrix, noise reduction parameters (algorithm not disclosed)
- Platform support: Apple platforms only (Final Cut Pro X, Motion); third-party applications (e.g., DaVinci Resolve) must decode via an Apple plug-in
- Encoding bit depth: 12–16-bit linear RAW
- Color science: Camera color description embedded within the file (similar to DNG ColorMatrix)

The key distinction between ProRes RAW and ProRes (Log-encoded): ProRes RAW stores the sensor's linear photon count, while ProRes (e.g., ProRes 4444 XQ) stores Log-encoded RGB images that have already been processed through the ISP. The "Apple Log" mode on iPhone outputs ProRes (not RAW) and has already completed demosaicing.

### 2.3 Blackmagic BRAW Format

Blackmagic RAW (BRAW, released in 2018) is a RAW video format designed by Blackmagic Design for the BMPCC 4K/6K and URSA Mini Pro series, striking an engineering balance between RAW data flexibility and efficient compression.

**Compression schemes:**
- Constant Bit Rate (CBR) mode: 3:1, 5:1, 8:1, 12:1
- Constant Quality (CQ) mode: Q0, Q1, Q3, Q5
- Uses wavelet encoding (similar to JPEG 2000), supporting random frame access

**Metadata structure:**
- Sidecar file (.sidecar): Stores ISP parameters that can be modified in post-production (white balance, exposure, saturation)
- Embedded camera metadata: Sensor matrix, black level, white balance, ISO gain mapping
- Color science version: Blackmagic Design Color Science Generation 5 (from BMPCC 6K Pro onward)

A key engineering highlight of BRAW is the "dual-track ISP": sensor data is frozen as RAW at acquisition time, but ISP parameters are attached as metadata, allowing non-destructive modification of white balance and exposure ±5 EV in DaVinci Resolve in post-production without reprocessing the original RAW (analogous to non-destructive editing in Lightroom, but applied to a video stream).

### 2.4 Smartphone Apple ProRAW and iPhone Log Formats

**Apple ProRAW** (introduced with iPhone 12 Pro):
- Is essentially a DNG file, but the pixel values store "semi-processed" data that has undergone Apple's computational photography preprocessing
- Preprocessing includes: multi-frame HDR compositing, noise reduction, and inverse linearization of Smart HDR tone mapping
- Color description: Embedded CameraCalibration matrices with color temperature adaptation support
- Bit depth: 16-bit linear or 12-bit logarithmic (depending on device and OS version)

**iPhone Log (Apple Log) mode** (introduced with iPhone 15 Pro):
- Outputs ProRes video (with demosaicing already complete), not RAW
- ISP pipeline: Sensor → Black Level → Noise Reduction → Demosaic → White Balance → CCM → Apple Log Encoding → ProRes container
- Color gamut: Apple Log Color Space (wide gamut); a LUT is required at delivery time to convert to Rec.709/P3
- Limitations: Fixed 24fps/30fps; EIS (electronic image stabilization) cannot be disabled; ISP parameters cannot be adjusted in post-production

---

## §3 Cinema-Grade ISP Tuning

### 3.1 1D LUT: Channel Alignment and Basic Tone Shaping

A 1D LUT (One-Dimensional Look-Up Table, 一维查找表) is an independent one-dimensional lookup table for each color channel (R, G, B). In a Log video ISP chain, it primarily handles the following functions:

**Black level and white level alignment:**
```
normalized = (code_value - black_level) / (white_level - black_level)
```
The black level drift of different sensors (varying with temperature/ISO) must be compensated via the offset term of the 1D LUT.

**Log→Linear decoding (EOTF, electro-optical inverse transform):**
1D LUT decoding for S-Log3:
```
Input: 10-bit S-Log3 code values [0, 1023]
Output: Linear scene luminance (normalized relative to 18% gray)
Table granularity: typically 4096 points (12-bit precision), interpolation error < 0.01%
```

**Tone curve fine-tuning:**
Before converting from Log to delivery color gamut, post-production colorists often fine-tune an S-curve (boosting midtone contrast, tightening shadows) within the 1D LUT. This is a low-cost creative tool.

### 3.2 3D LUT: Full Gamut Mapping

A 3D LUT (Three-Dimensional Look-Up Table, 三维查找表) stores color mappings in a (R,G,B) three-dimensional grid and is the central tool of modern cinema color management.

**Standard specifications:**
- Grid size: 17³ (quick preview), 33³ (standard delivery), 65³ (high-precision master)
- File formats: `.cube` (Adobe, most universal), `.3dl` (Autodesk), `.lut` (DaVinci Resolve)
- Trilinear interpolation error: maximum ΔE2000 < 0.5 for smooth gradients with a 33³ grid (empirically measured)

**Log→Rec.709 transform chain (typical cinema ISP pipeline):**

```
[Sensor RAW]
    ↓ (1) Black level / white level normalization
[Linear RAW]
    ↓ (2) Demosaic (Bayer→RGB, typically high-quality AHD/MLCD)
[Linear RGB, camera color gamut]
    ↓ (3) White balance gain (R/B channels individually multiplied by gain factors)
[White-balanced linear RGB]
    ↓ (4) Camera gamut → XYZ_D65 (ForwardMatrix 3×3)
[XYZ_D65]
    ↓ (5) XYZ_D65 → Rec.709 linear (BT.709 standard matrix)
[Rec.709 linear]
    ↓ (6) Log encoding (S-Log3 OETF, if intermediate storage is required)
[S-Log3]
    ↓ (7) Creative 3D LUT (post-production color grading)
[Delivery gamut RGB]
    ↓ (8) Delivery gamma (Rec.709 BT.1886: γ=2.4)
[Rec.709/SDR delivery]
```

### 3.3 Trivariate Joint Optimization of Color Temperature, Color Gamut, and Tone Curve

In professional Log video post-production, color grading involves three mutually coupled dimensions that require joint optimization:

**Color Temperature Adjustment (White Balance):**
Color temperature adjustment is performed in the linear domain (after Log decoding) by applying independent gain to the R and B channels. Precise color temperature adjustment should use a Chromatic Adaptation Transform (CAT, 色适应变换), such as the Bradford matrix:

```
XYZ_adapted = M_Bradford × diag(d_r, d_g, d_b) × M_Bradford_inv × XYZ_original
```

where d_r, d_g, d_b are the scaling factors for the source and target white points in Bradford chromatic adaptation space.

**Gamut Conversion:**

The mutual conversion matrices between DCI-P3 and Rec.709 (linear domain, D65 white point, row-major approximations):

```
P3 → Rec.709:
 [ 1.2249,  -0.2247,   0.0000 ]
 [-0.0420,   1.0419,   0.0002 ]
 [-0.0197,  -0.0786,   1.0979 ]

Rec.2020 → Rec.709:
 [ 1.6605,  -0.5877,  -0.0728 ]
 [-0.1246,   1.1329,  -0.0083 ]
 [-0.0182,  -0.1006,   1.1187 ]
```

Gamut Mapping (色域裁剪) after gamut conversion is a critical engineering point: the P3 color gamut is approximately 25% wider than Rec.709. A direct linear clamp causes color breaks in highly saturated regions; soft clipping or HSL soft mapping should be used instead.

**Tone Curve:**
In the final step of converting Log to Gamma/PQ, the tone curve determines the Highlight Rolloff (高光卷曲) style. The ARRI ACES Output Transform uses a Filmic S-curve (referencing an improved version of Reinhard tone mapping), while DaVinci Resolve's Color Space Transform node provides an adjustable highlight compression slope.

### 3.4 Derivation Principles for Rec.709 / P3 / 2020 Gamut Conversion Matrices

Standard gamut conversion matrices are derived from the primaries (Primaries) and white point definitions of each color space. Taking BT.2020 → DCI-P3 (D65) as an example, the derivation steps are:

1. Convert the xy chromaticity coordinates of each primary to XYZ tristimulus values:
   `XYZ_r = [x_r/y_r, 1, (1-x_r-y_r)/y_r]`

2. Solve for the scaling coefficients S = [S_r, S_g, S_b] for each primary under white point constraints:
   `M_primaries × S = XYZ_white`

3. Build the RGB→XYZ matrix M = M_primaries × diag(S)

4. XYZ → target gamut matrix = M_target_inv × M_source

The complete standard values are defined in CIE 15:2004 appendices; the colour-science library provides the full set of precomputed matrices.

---

## §4 Common Artifacts and Issues

### 4.1 Log Underexposure: Noise Amplification Effect

**Symptom description:**
When S-Log3 or Log C video is shot underexposed by 1–2 stops, pulling up the exposure in post-production significantly amplifies sensor noise. This is an inherent mathematical property of Log encoding: the derivative (slope) of the logarithmic function is steeper at low values, meaning the same quantization noise error corresponds to a larger linear amplitude change.

**Quantitative analysis:**
Let the sensor readout noise be σ_ADU (in ADU units). In the S-Log3 linear segment (x < 0.01125):
```
dSLog3/dx = (171.2102946929 - 95) / (0.01125000 × 1023) ≈ 6.63 per ADU
```
Whereas near 18% gray (logarithmic segment):
```
dSLog3/dx = 261.5 / ((x + 0.01) × ln(10) × 1023) ≈ 0.62 per normalized unit
```
The noise amplification factor in the shadows is roughly 10× that of the highlights — this is the fundamental reason why "Log underexposure" must be avoided.

**Engineering countermeasures:**
- ETTR (Expose To The Right, 向右曝光): Push the exposure as high as possible without clipping highlights to maximize the signal-to-noise ratio
- For night scenes, use a high native ISO (e.g., ARRI Mini LF native ISO 3200) to ensure the RAW pixels are adequately exposed
- Apply post-production noise reduction (NR) after decoding from Log to the linear domain; avoid doing NR in the Log domain

### 4.2 Highlight Rolloff Problems

**Symptom description:**
When the luminance of a subject exceeds the rated upper limit of the Log encoding, the highlight region undergoes "rolloff" or "clipping." The theoretical upper limit of Log encoding is typically around 7–8 stops above 18% gray.

**Typical symptoms:**
- Hue shift on highly reflective objects (metals, white clothing), especially after P3→Rec.709 gamut conversion
- Hue distortion in overexposed regions: because the saturation points of the three RGB channels differ, overexposed highlights shift toward green or magenta
- 3D LUT extrapolation failure in highlight regions (colors extrapolated beyond the LUT grid range are unpredictable)

**Engineering countermeasures:**
- When constructing the 3D LUT, apply HSL Highlight Compression for highlight regions (input values > 0.9×white_level) rather than linear extrapolation
- DaVinci Resolve's "Highlight Recovery" node reconstructs highlight detail by analyzing the ratio relationships between the three channels

### 4.3 3D LUT Boundary Banding

**Symptom description:**
When the 3D LUT granularity is insufficient (e.g., 17³), visible color blocking or gradient banding appears in regions with abrupt color transitions (highly saturated colors, skin-tone-to-highlight transitions).

**Root cause:**
Trilinear interpolation performs a weighted average among the 8 vertices of the LUT cube; if the color difference between adjacent grid points is large (e.g., at gamut boundaries, in regions with abrupt HSL changes), the interpolated result will be non-smooth.

**Quantitative standards:**
- 17³ LUT: Maximum interpolation error can reach ΔE2000 ≈ 2–5 (unacceptable)
- 33³ LUT: Maximum interpolation error approximately ΔE2000 ≈ 0.5 (acceptable for broadcast)
- 65³ LUT: Maximum interpolation error approximately ΔE2000 ≈ 0.1 (cinema master quality)

**Engineering countermeasures:**
- Use 33³ or larger LUTs throughout the post-production color management chain
- Add extra grid density in key color regions such as skin tones and sky (non-uniform LUT)
- Use tetrahedral interpolation (四面体插值, default in DaVinci Resolve) instead of trilinear interpolation — approximately 3–5× improvement in precision

---

## §5 Evaluation Methods

### 5.1 Vectorscope Analysis

A Vectorscope (矢量示波器) displays the chrominance vector distribution of a video signal, with the horizontal and vertical axes corresponding to Cb/Cr. The six pure colors (Red/Green/Blue/Cyan/Magenta/Yellow) of a standard color bar (SMPTE Color Bars) should fall precisely within their corresponding target boxes.

**Log video evaluation workflow:**
1. Shoot a standard color chart (Macbeth ColorChecker Classic) or IT8 target
2. Apply a Log→Rec.709 LUT in DaVinci Resolve
3. Vectorscope observation:
   - 18% gray should be near the origin (chrominance < 1%)
   - The skin tone vector should fall on the "Skin Tone Line" (approximately the 11 o'clock direction, within roughly ±15° of the R-Y axis)
   - Color patches should be evenly distributed without obvious hue shifts

### 5.2 Waveform Monitor Analysis

A Waveform Monitor (波形监视器) displays the distribution of luminance/RGB in a video signal as a function of horizontal position, used to evaluate:
- **Exposure consistency:** 18% gray in the Log domain should be at approximately 40–42% (Y-axis); after conversion, approximately 42–46 IRE in Rec.709
- **Black level alignment:** For multi-camera shoots, quantify the drift of the black point (0 IRE); target < 1 IRE
- **Highlight protection:** Overexposed regions appear as a "flat top" in the waveform; the percentage of overexposed frames can be quantified

### 5.3 ΔE2000 Color Accuracy Evaluation (P3 Color Gamut)

Color difference ΔE2000 is the most widely used quantitative metric for color accuracy, combining perceptually weighted contributions from lightness, chroma, and hue.

**Cinema ISP chain color accuracy evaluation workflow:**
1. Use a spectrophotometer (e.g., X-Rite i1Pro 3) to measure the true CIE XYZ values of a standard color chart
2. Process the color chart image through the target ISP chain (including the 3D LUT)
3. Compute ΔE2000 between the processed result and the true values in the P3 gamut (D65)
4. Evaluation criteria (referencing ICC color management specifications):
   - ΔE2000 < 1.0: Excellent (cinema master quality)
   - ΔE2000 < 2.0: Good (broadcast delivery quality)
   - ΔE2000 < 3.0: Acceptable (consumer grade)
   - ΔE2000 > 3.0: Unacceptable (visible color difference)

### 5.4 Noise Spectrum Analysis (PSD)

Power Spectral Density (PSD, 功率谱密度) analysis of shadow noise in Log video can distinguish sensor-inherent noise (white noise) from structured noise introduced by ISP processing (e.g., demosaic false color, sharpening ringing):

```python
import numpy as np
from scipy.signal import welch

# Take single-channel pixels from a uniform dark region (e.g., the Macbeth black patch)
patch = frame_log[y:y+64, x:x+64, 1]  # Green channel
freqs, psd = welch(patch.flatten(), fs=1.0, nperseg=256)
# White noise: PSD should be a flat spectrum; colored noise: abnormal elevation in low-frequency components
```

---

## §6 Code Examples

The following Python code implements a complete pipeline for S-Log3 decoding and 3D LUT application, and can be run directly.

```python
"""
RAW Video ISP Demo: S-Log3 Decoding + 3D LUT Application
Dependencies: numpy, scipy, colour-science (pip install numpy scipy colour-science)
"""

import numpy as np


# =============================================================================
# 1. S-Log3 Encoding / Decoding Functions
# =============================================================================

def slog3_encode(lin: np.ndarray) -> np.ndarray:
    """
    将线性场景亮度编码为 S-Log3 代码值（归一化至[0,1]）

    参数:
        lin: 线性亮度，18%灰 = 0.18，支持任意 shape
    返回:
        slog3: S-Log3 代码值，[0, 1]（等效10-bit值需乘以1023）
    """
    lin = np.asarray(lin, dtype=np.float64)
    cut = 0.01125000

    # 对数段
    log_part = (420 + np.log10((lin + 0.01) / 0.19) * 261.5) / 1023.0
    # 线性段
    lin_part = (lin * (171.2102946929 - 95) / cut + 95) / 1023.0

    return np.where(lin >= cut, log_part, lin_part)


def slog3_decode(slog3: np.ndarray) -> np.ndarray:
    """
    将 S-Log3 代码值解码为线性场景亮度

    参数:
        slog3: S-Log3 代码值，归一化至[0,1]（即10-bit除以1023）
    返回:
        lin: 线性亮度，18%灰 ≈ 0.18
    """
    slog3 = np.asarray(slog3, dtype=np.float64)
    cut = 95.0 / 1023.0  # 线性段上限的 S-Log3 代码值

    # 对数段解码
    log_part = (10 ** ((slog3 * 1023.0 - 420) / 261.5)) * 0.19 - 0.01
    # 线性段解码
    lin_part = (slog3 * 1023.0 - 95) * 0.01125000 / (171.2102946929 - 95)

    return np.where(slog3 >= cut, log_part, lin_part)


# =============================================================================
# 2. 3D LUT 构建与三线性插值应用
# =============================================================================

def build_contrast_lut(size: int = 33, contrast: float = 0.20) -> np.ndarray:
    """
    构建带 S 曲线对比度的 3D LUT

    参数:
        size:     LUT 网格尺寸（17 / 33 / 65）
        contrast: S 曲线强度，0 = 恒等，0.2 = 适度对比度
    返回:
        lut: shape (size, size, size, 3)，值域[0, 1]
    """
    axis = np.linspace(0.0, 1.0, size, dtype=np.float64)
    r, g, b = np.meshgrid(axis, axis, axis, indexing='ij')
    rgb = np.stack([r, g, b], axis=-1)  # (size, size, size, 3)

    # 逐通道施加 S 曲线：f(x) = x + k * sin(π*x) * x*(1-x)
    lut = rgb + contrast * np.sin(np.pi * rgb) * (rgb * (1.0 - rgb))
    return np.clip(lut, 0.0, 1.0).astype(np.float32)


def apply_3d_lut_trilinear(image: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """
    对图像施加 3D LUT（三线性插值）

    参数:
        image: 输入图像，shape (H, W, 3)，值域[0, 1]
        lut:   3D LUT，shape (N, N, N, 3)，值域[0, 1]
    返回:
        output: 输出图像，shape (H, W, 3)，dtype float32
    """
    N = lut.shape[0]
    img_flat = image.reshape(-1, 3).astype(np.float64)

    # 将[0,1]映射到 LUT 网格坐标[0, N-1]
    coords = np.clip(img_flat * (N - 1), 0.0, N - 1 - 1e-9)
    i0 = coords.astype(np.int32)
    i1 = np.minimum(i0 + 1, N - 1)
    f = coords - i0  # 小数权重，shape (P, 3)

    ir, ig, ib = i0[:, 0], i0[:, 1], i0[:, 2]
    jr, jg, jb = i1[:, 0], i1[:, 1], i1[:, 2]
    fr = f[:, 0:1]; fg = f[:, 1:2]; fb = f[:, 2:3]

    # 三线性插值：8 顶点加权和
    out = (lut[ir, ig, ib] * (1-fr)*(1-fg)*(1-fb) +
           lut[jr, ig, ib] * fr    *(1-fg)*(1-fb) +
           lut[ir, jg, ib] * (1-fr)* fg   *(1-fb) +
           lut[jr, jg, ib] * fr    * fg   *(1-fb) +
           lut[ir, ig, jb] * (1-fr)*(1-fg)* fb    +
           lut[jr, ig, jb] * fr    *(1-fg)* fb    +
           lut[ir, jg, jb] * (1-fr)* fg   * fb    +
           lut[jr, jg, jb] * fr    * fg   * fb)

    return out.reshape(image.shape).astype(np.float32)


# =============================================================================
# 3. Rec.709 伽马编码（BT.1886 简化版）
# =============================================================================

def rec709_oetf(lin: np.ndarray) -> np.ndarray:
    """Rec.709 OETF（γ ≈ 2.2，ITU-R BT.709 规范）"""
    lin = np.clip(lin, 0.0, None)
    return np.where(lin < 0.018,
                    lin * 4.5,
                    1.099 * np.power(lin, 0.45) - 0.099)


# =============================================================================
# 4. 完整演示流水线
# =============================================================================

def demo_pipeline():
    print("=== S-Log3 解码 + 3D LUT 电影 ISP 演示 ===\n")

    # --- 4.1 灰阶楔验证 ---
    stops = np.linspace(-7.0, 7.0, 15)
    lin_vals = 0.18 * (2.0 ** stops)
    slog3_vals = slog3_encode(lin_vals)

    print(f"{'Stops':>7}  {'线性值':>10}  {'SLog3[0-1]':>11}  {'SLog3[10bit]':>13}")
    print("-" * 50)
    for s, lin, sl in zip(stops, lin_vals, slog3_vals):
        print(f"{s:+7.1f}  {lin:10.5f}  {sl:11.4f}  {sl*1023:13.1f}")

    # 关键验证点
    gray18_code = slog3_encode(np.array([0.18]))[0]
    print(f"\n18%灰 S-Log3 代码值：{gray18_code*1023:.1f}/1023  （规范期望：~420）")

    decoded_vals = slog3_decode(slog3_vals)
    max_rel_err = np.max(np.abs(decoded_vals - lin_vals) / (lin_vals + 1e-12))
    print(f"编解码往返最大相对误差：{max_rel_err:.2e}  （应 < 1e-9）\n")

    # --- 4.2 合成测试图像（256×512，左半灰阶楔，右半彩色块） ---
    H, W = 256, 512
    img_slog3 = np.zeros((H, W, 3), dtype=np.float32)

    # 左半：18级灰阶楔
    n_steps = len(stops)
    step_w = (W // 2) // n_steps
    for k, sv in enumerate(slog3_vals):
        x0, x1 = k * step_w, min((k + 1) * step_w, W // 2)
        img_slog3[:, x0:x1, :] = float(sv)

    # 右半：4个彩色色块（模拟 S-Gamut3 宽色域颜色）
    palette_lin = np.array([
        [0.25, 0.03, 0.03],   # 饱和红
        [0.03, 0.25, 0.03],   # 饱和绿
        [0.03, 0.03, 0.25],   # 饱和蓝
        [0.80, 0.80, 0.80],   # 近白高光
    ], dtype=np.float64)
    block_w = (W // 2) // len(palette_lin)
    for k, lin_col in enumerate(palette_lin):
        encoded_col = slog3_encode(lin_col).astype(np.float32)
        x0 = W // 2 + k * block_w
        x1 = x0 + block_w
        img_slog3[:, x0:x1, :] = encoded_col[np.newaxis, np.newaxis, :]

    # --- 4.3 ISP 流水线 ---
    print("--- 执行 ISP 流水线 ---")

    # Step 1: S-Log3 → 线性
    img_lin = slog3_decode(img_slog3)
    print(f"Step 1 S-Log3解码：值域 [{img_lin.min():.4f}, {img_lin.max():.4f}]")

    # Step 2: 色域转换占位（实际需 colour-science 库）
    # Sony S-Gamut3 → Rec.709（近似矩阵，仅供演示）
    M_sgamut3_to_rec709 = np.array([
        [ 1.3456,  -0.2558,  -0.0898],
        [-0.0438,   1.0879,  -0.0441],
        [-0.0083,  -0.0676,   1.0759],
    ], dtype=np.float64)
    img_r709_lin = np.einsum('...c,dc->...d', img_lin, M_sgamut3_to_rec709)
    img_r709_lin = np.clip(img_r709_lin, 0.0, 1.0).astype(np.float32)
    print(f"Step 2 色域转换（S-Gamut3→Rec.709）：值域 [{img_r709_lin.min():.4f}, {img_r709_lin.max():.4f}]")

    # Step 3: 施加 33³ S 曲线 3D LUT
    lut_33 = build_contrast_lut(size=33, contrast=0.20)
    img_lut = apply_3d_lut_trilinear(img_r709_lin, lut_33)
    print(f"Step 3 3D LUT（S曲线，33³）：值域 [{img_lut.min():.4f}, {img_lut.max():.4f}]")

    # Step 4: Rec.709 伽马编码
    img_final = rec709_oetf(img_lut)
    img_final = np.clip(img_final, 0.0, 1.0)
    print(f"Step 4 Rec.709 OETF：值域 [{img_final.min():.4f}, {img_final.max():.4f}]")

    # --- 4.4 输出摘要 ---
    print(f"\n最终图像均值：R={img_final[:,:,0].mean():.4f}  G={img_final[:,:,1].mean():.4f}  B={img_final[:,:,2].mean():.4f}")

    print("\n--- S-Log3 关键曝光点代码值 ---")
    kp = [('Scene Black',    0.0),
          ('18% Gray',       0.18),
          ('90% White',      0.9),
          ('+3 stops (×8)', 0.18 * 8),
          ('+5 stops (×32)', 0.18 * 32)]
    for name, lv in kp:
        cv = slog3_encode(np.array([lv]))[0]
        print(f"  {name:22s}  lin={lv:.4f}  →  {cv*1023:.1f}/1023")

    print("\n演示完成！")
    return img_final


if __name__ == '__main__':
    result = demo_pipeline()
```

**Running instructions:**
```bash
pip install numpy scipy
python ch23_demo.py
# Install colour-science to enable accurate gamut conversion:
pip install colour-science
```

---

## §7 References

1. Sony Corporation, "S-Log3 Technical White Paper," Technical Bulletin, 2014.

2. ARRI, "ALEXA Log C Curve Usage in VFX," White Paper WP-2017-001, 2017.

3. Apple Inc., "Apple Log Profile White Paper," Developer Documentation, 2023.

4. Adobe Systems, "CinemaDNG 1.2 Specification," 2012.

5. Blackmagic Design, "BRAW SDK Developer Reference," v2.8, 2023.

6. Hasinoff, S. et al., "Burst Photography for High Dynamic Range and Low-Light Imaging on Mobile Cameras," *ACM Transactions on Graphics (SIGGRAPH Asia)*, 2016.

7. Reinhard, E. et al., "Photographic Tone Reproduction for Digital Images," *ACM SIGGRAPH*, pp. 267–276, 2002.

8. Blackmagic Design, "DaVinci Resolve 18 Color Management," User Manual, 2023.

9. CIE, "Colorimetry, 3rd Edition," Technical Report 15:2004, International Commission on Illumination.

10. International Color Consortium, "Specification ICC.1:2022," 2022.

11. Mansencal, T. et al., "Colour 0.4.4," *colour-science.org*, 2023.

12. ISO 22028-1:2004, "Photography and graphic technology — Extended colour encodings for digital image storage, manipulation and interchange — Part 1: Architecture and requirements."

---

## §8 Glossary

| Term | Full Name | Description |
|------|-----------|-------------|
| Log Encoding | Log Encoding | A quantization coding strategy that applies a logarithmic transform to linear output to extend dynamic range |
| S-Log3 | Sony Log Curve 3 | Sony camera Log encoding curve; nominal 15+ stops with a piecewise linear shadow protection segment |
| Log C | ARRI Log C Curve | ARRI ALEXA series Log encoding curve; parameters vary with EI |
| Apple Log | Apple Log Encoding | Log encoding supported from iPhone 15 Pro onward, paired with ProRes video output |
| OETF | Opto-Electronic Transfer Function | The forward encoding curve (light-to-electrical) |
| EOTF | Electro-Optical Transfer Function | The decoding/display curve (electrical-to-light) |
| CinemaDNG | Cinema Digital Negative | Adobe's cinema-grade per-frame RAW format extended from the DNG specification |
| BRAW | Blackmagic RAW | Blackmagic Design's proprietary RAW video format supporting post-production ISP adjustment |
| ProRes RAW | Apple ProRes RAW | Apple's semi-compressed format combining a ProRes container with sensor RAW data |
| 1D LUT | 1D Look-Up Table | A one-dimensional lookup table with independent per-channel mapping, used for channel alignment and gamma adjustment |
| 3D LUT | 3D Look-Up Table | A three-dimensional color mapping lookup table supporting full gamut mapping and creative color grading |
| ETTR | Expose To The Right | An acquisition strategy of maximizing exposure without clipping highlights to maximize the signal-to-noise ratio |
| CCM | Color Correction Matrix | A 3×3 linear RGB-space transform matrix for color correction |
| CAT | Chromatic Adaptation Transform | Color adaptation transform used for white point conversion (e.g., Bradford matrix) |
| ΔE2000 | Delta E 2000 | CIEDE2000 color difference formula; a perceptually uniform color difference quantification standard |
| Vectorscope | Vectorscope | An instrument displaying the chrominance vector distribution of a video signal, used for color accuracy evaluation |
| PSD | Power Spectral Density | Power spectral density, used for frequency-domain analysis of noise characteristics |
| Rec.709 | ITU-R BT.709 | High-definition broadcast video standard color gamut; the mainstream SDR delivery standard |
| DCI-P3 | Digital Cinema Initiatives P3 | Digital cinema color gamut standard, approximately 25% wider than Rec.709 |
| Rec.2020 | ITU-R BT.2020 | Ultra-high definition/HDR video color gamut standard, covering approximately 75% of the visible gamut |
| EI | Exposure Index | Exposure index; an ISO-equivalent setting that affects Log C parameters in ARRI systems |
| SMPTE | Society of Motion Picture and Television Engineers | The primary standards body for motion picture and television engineering |
