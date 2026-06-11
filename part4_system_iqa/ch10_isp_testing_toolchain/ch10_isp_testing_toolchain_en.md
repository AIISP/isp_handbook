# Part 4, Chapter 10: ISP Testing and IQA Toolchain (Imatest / OpenCV / Custom Calibration Charts)

> **Scope:** This chapter covers the complete toolchain for ISP engineering testing: Imatest MTF measurement, ISO 12233, EMVA 1288, ISO 15739, OpenCV color calibration, and automated IQA evaluation system construction.
> **Prerequisites:** Volume 4, Chapter 8 (IQA System Engineering); Volume 4, Chapter 4 (Perceptual IQA)
> **Target Readers:** IQA engineers, system engineers

---

## Table of Contents

- [§1 Theory](#1-theory)
- [§2 Calibration and Measurement Methods](#2-calibration-and-measurement-methods)
- [§3 Tuning Guide](#3-tuning-guide)
- [§4 Common Test Artifacts and Error Sources](#4-common-test-artifacts-and-error-sources)
- [§5 Evaluation Methods](#5-evaluation-methods)
- [§6 Code Implementation](#6-code-implementation)
- [References](#references)
- [§8 Glossary](#8-glossary)

---

## §1 Theory

### 1.1 Engineering Goals of ISP Testing

Testing and calibration of Image Signal Processor (ISP) algorithms is a core component of the entire camera system development process. The testing framework must answer the following engineering questions:

1. **Resolution:** Can the ISP output faithfully reproduce the physical resolution of the sensor? Do the effective pixel count and the nominal specification match?
2. **Noise:** Under different ISO and exposure combinations, does the signal-to-noise ratio (SNR) of the output image meet specifications?
3. **Color Accuracy:** After AWB and CCM correction, is the color rendering Delta E within an acceptable range?
4. **Dynamic Range:** After joint processing by the sensor and ISP, how many EV of usable dynamic range are available?
5. **Lens Shading:** After LSC correction, does the luminance uniformity across the full frame meet the required standard?

These questions correspond to the core measurement dimensions of the ISP testing toolchain, and are the subjects of international standards (ISO 12233, EMVA 1288, ISO 15739, IEEE P2020).

### 1.2 MTF and Resolution Measurement Theory

**MTF (Modulation Transfer Function, 调制传递函数)** is the key metric describing the spatial frequency response of the combined optical + sensor + ISP system. For spatial frequency $f$ (in units of cycles/pixel or lp/mm):

$$\text{MTF}(f) = \frac{\text{Output Modulation}}{\text{Input Modulation}} = \frac{(I_{\max} - I_{\min})_{\text{out}}}{(I_{\max} - I_{\min})_{\text{in}}}$$

MTF = 1.0 means the frequency is transmitted completely (the system is transparent); MTF = 0 means the frequency is completely lost (the cutoff frequency).

**Nyquist Frequency:** For a pixel pitch of $p$, the Nyquist frequency is $f_N = 1/(2p)$. Signals beyond the Nyquist frequency produce aliasing. The MTF value at $f_N$ (MTF50N) is a key parameter for evaluating ISP resolution.

**MTF50:** The spatial frequency at which the MTF drops to 50%, typically expressed in lp/mm or cy/px. A higher MTF50 indicates better system resolution.

**Slanted Edge Method:** The standard MTF measurement method adopted by ISO 12233 and Imatest. The measurement procedure is:
1. Capture an image of a black-and-white edge pattern tilted approximately 5°
2. Perform super-resolution sampling along the slant direction to extract the Edge Spread Function (ESF)
3. Differentiate the ESF to obtain the Line Spread Function (LSF)
4. Apply FFT to the LSF to obtain the MTF

The advantage of the slanted edge method is that the tilt angle enables sub-pixel sampling, allowing MTF measurement beyond the Nyquist frequency (including post-cutoff overshoot, i.e., ringing).

### 1.3 EMVA 1288 Standard Framework

**EMVA 1288** (European Machine Vision Association Standard 1288) is the authoritative specification for standardized characterization of industrial cameras and sensors, covering:

**Quantum Efficiency (QE):** The efficiency of converting incident photons into photoelectrons:
$$\text{QE}(\lambda) = \frac{N_e}{N_{ph}(\lambda)}$$

**Responsivity:** The digital signal output per unit of illuminance:
$$R = \frac{\bar{\mu}_y}{\bar{\mu}_p} \cdot K$$

where $\bar{\mu}_y$ is the mean digital output, $\bar{\mu}_p$ is the mean photon count, and $K$ is the system gain (DN/e$^-$).

**Noise Model Verification:** EMVA 1288 uses the PTC (Photon Transfer Curve) method to verify the noise model of a camera. Images of a uniformly illuminated gray field are captured at different illuminance levels to measure the mean-variance relationship:

$$\sigma_y^2 = \sigma_d^2 + K \cdot \mu_y$$

where $\sigma_d^2$ is the dark-current noise variance, $K$ is the gain, and $\mu_y$ is the signal mean. A linear fit extracts readout noise and gain parameters.

### 1.3b ISO 15739 Standard: Noise Floor and Dynamic Range for Still Cameras

While EMVA 1288 targets industrial and machine-vision sensors, **ISO 15739** (Photography — Electronic still-picture imaging — Noise measurements) is the primary international standard for characterizing **noise floor** and **dynamic range** of consumer and professional still-camera systems, including smartphone ISPs.

**Noise Floor Measurement (ISO 15739):**
- Defines noise in terms of visually weighted signal-to-noise ratio (SNR_v), incorporating a visual weighting function matched to human spatial frequency sensitivity
- Specifies capture conditions: uniformly illuminated gray field at 18% reflectance gray card, measured at multiple ISO settings
- Noise floor is defined as the illuminance level at which SNR_v drops below a specified threshold (typically 1.0 for "just acceptable" quality)

**Dynamic Range Measurement (ISO 15739 / CPIQ):**
- ISO 15739 DR is defined as the ratio (in EV or dB) between the saturation luminance and the noise floor luminance
  $$\text{DR} = \log_2\left(\frac{L_{\text{sat}}}{L_{\text{noise\_floor}}}\right) \quad [\text{EV}]$$
- **CPIQ (Camera Phone Image Quality)** initiative (IEEE P2020) extends DR characterization to mobile camera systems with an equivalent definition, accounting for multi-frame HDR capture modes
- Typical consumer smartphone ISP DR: 10–13 EV (single frame); 14–16 EV (multi-frame HDR)

**Standard Selection Guide:**
| Use Case | Recommended Standard |
|----------|---------------------|
| Industrial / machine-vision sensors | EMVA 1288 |
| Consumer still cameras and smartphones | ISO 15739 |
| Mobile camera benchmarking | ISO 15739 + CPIQ (IEEE P2020) |

### 1.4 Color Calibration Theory

The goal of **Color Calibration** is to establish an accurate mapping from the camera's RGB response to a standard color space (such as sRGB or CIE XYZ). The calibration process is based on the following assumptions:

1. A standard color chart (such as the X-Rite ColorChecker Classic 24-patch) is used as a reference.
2. Each patch has a known CIE XYZ reference value (measured under standard illuminant D50/D65).
3. A CCM (Color Correction Matrix) is solved using the Least Squares method.

**CCM Solution:** Given camera RGB measurements $\mathbf{R}_i \in \mathbb{R}^3$ and corresponding reference XYZ values $\mathbf{X}_i \in \mathbb{R}^3$ for $N$ patches:

$$\min_{\mathbf{M}} \sum_{i=1}^N \| \mathbf{M} \mathbf{R}_i - \mathbf{X}_i \|^2$$

The analytical solution is: $\mathbf{M} = \mathbf{X} \mathbf{R}^T (\mathbf{R} \mathbf{R}^T)^{-1}$, where $\mathbf{R}, \mathbf{X}$ are measurement matrices stacked column-wise.

**Polynomial CCM:** A standard 3×3 CCM provides insufficient fitting for nonlinear color responses. In practice, quadratic terms are commonly added to expand the feature vector: $\tilde{\mathbf{r}} = [R, G, B, R^2, G^2, B^2, RG, RB, GB, 1]^T$, using a 3×10 CCM.

---

## §2 Calibration and Measurement Methods

### 2.1 Imatest Toolchain

**Imatest** is the most widely used camera image quality testing software in industry, supporting the following core measurements:

**MTF Measurement (SFR Module):**
- Input: RAW or JPEG images containing a slanted edge pattern
- Output: MTF curve, MTF50, MTF50P (MTF50 normalized to Nyquist frequency)
- Supports multi-region measurement: MTF distribution across center, corners, and edge regions (for lens aberration assessment)

**Noise Measurement (Noise Module):**
- Input: Uniformly illuminated gray field images (flat field)
- Output: RMS noise, signal-to-noise ratio (SNR), and dynamic range (DR) at different signal levels

**Color Chart Analysis (ColorChecker Module):**
- Input: Image containing an X-Rite ColorChecker
- Output: Delta E (CIE76/CIE2000) per patch, white point deviation, suggested color matrix values

**Lens Shading (Uniformity Module):**
- Input: Uniformly illuminated white panel image
- Output: Full-frame luminance uniformity map, corner/center luminance ratio

### 2.2 ISO 12233 Test Chart and Procedure

The ISO 12233 standard specifies the format for standard resolution test charts used to measure camera resolution. Recommended test procedure:

1. **Environment Preparation:**
   - Illuminance: 1000–2000 lux, color temperature D50 (5000K) or D65 (6500K) per ISO 12233:2017 Annex C
   - Lens aperture: f/5.6 to f/8 (avoiding extremes of diffraction and aberration)
   - Focus: manually focus precisely on the test chart surface

2. **Capture Parameters:**
   - ISO: 100 (base ISO, lowest noise)
   - Shutter speed: no motion blur (1/200 s or faster)
   - Save RAW + JPEG simultaneously to evaluate the sensor and ISP contributions separately

3. **Analysis:**
   - Analyze slanted edge regions using Imatest or MATLAB/OpenCV
   - Record center MTF50 and corner MTF50; calculate field uniformity

4. **Typical Specifications (smartphone main camera):**
   - Center MTF50 > 0.35 cy/px
   - Corner/center MTF50 ratio > 0.6
   - MTF @ Nyquist > 0.1 (to avoid severe aliasing)

### 2.3 EMVA 1288 Measurement Procedure

**PTC (Photon Transfer Curve) Measurement Steps:**

1. **Dark Frame Acquisition:** Cover the lens and capture a series of images (>50 frames); compute the dark current mean and variance.
2. **Bright Frame Acquisition:** Using a uniform illumination source (integrating sphere or uniform illumination panel), capture a series of images from low illuminance to saturation (≥10 frames per illuminance level).
3. **Mean-Variance Computation:** For each illuminance level, compute the mean $\mu$ and variance $\sigma^2$ of the ROI (using temporal-sequence variance to eliminate PRNU effects).
4. **Linear Fitting:** Fit a line to the $(\mu, \sigma^2)$ points to extract the slope (gain $K$) and intercept (readout noise $\sigma_d^2$).
5. **Dynamic Range Calculation:** $DR = 20 \log_{10}(FWC / \sigma_d)$ (dB), where $FWC$ is the Full Well Capacity.

### 2.4 OpenCV Color Calibration Workflow

OpenCV provides a complete color calibration toolchain supporting color chart detection and CCM computation:

**Color Chart Detection (Automated Workflow):**
- `cv2.mcc.CCheckerDetector`: automatically detects the location and patches of a ColorChecker chart
- Supports multiple chart formats: Classic 24, Passport, Digital SG

**Color Space Transform Verification:**
- Use `cv2.cvtColor` to convert between RGB/XYZ/Lab color spaces
- Evaluate calibration accuracy using Delta E

---

## §3 Tuning Guide

### 3.1 Key Factors Affecting MTF Measurement

**Slanted Edge Angle Selection:** ISO 12233 recommends 5° ± 0.5°. An angle that is too large (>10°) reduces super-resolution sampling density and degrades high-frequency MTF accuracy. An angle that is too small (<2°) reduces the number of effective samples and increases estimation error.

**Region of Interest (ROI) Size:** Imatest recommends that the ROI contain 10–100 pixel rows (in the slant direction). When the ROI is too small, estimation variance is high. When too large, field curvature causes PSF variations at different positions to be averaged, resulting in underestimated MTF.

**Effect of Sharpening on MTF:** ISP sharpening algorithms artificially inflate MTF, making MTF50 values appear higher than the true optical + sensor resolution. For testing, it is recommended to:
- Disable ISP sharpening (via parameter configuration or using RAW data) to measure optical resolution alone
- Measure with sharpening enabled and record the MTF "gain" contributed by the ISP

**Common Pitfall:** JPEG compression introduces DCT block artifacts, which manifest as high-frequency spurious peaks (spurious resolution) in MTF measurements. It is advisable to perform MTF analysis on RAW or highest-quality JPEG (compression ratio > 90%) to avoid compression artifact interference.

### 3.2 Optimization Strategies for Color Calibration

**Delta E Metric Selection:**
- CIE76 ($\Delta E_{76}$): Simple Euclidean distance; fast to compute but poorly correlated with human perception
- CIE2000 ($\Delta E_{00}$): Perceptually uniform weighted distance; the currently recommended standard
- Industry acceptance standard: $\Delta E_{00} < 3$ is acceptable; $< 1$ is excellent

**CCM Constraints:** An unconstrained least-squares CCM may produce physically unreasonable matrices (e.g., negative weights), causing color distortion. In practice, the following constraints are recommended:
- Row-sum constraint (row sum = 1): preserves the gray axis from cross-channel contamination
- Non-negativity constraint (non-negative entries): implemented via Non-Negative Least Squares (NNLS)
- Tikhonov regularization: $\| \mathbf{M} - \mathbf{I} \|_F^2$ as a regularization term, biasing the CCM toward the identity matrix to limit the extent of color distortion

**Multi-Illuminant Calibration:** A CCM calibrated under a single illuminant may fail under other illuminants. It is recommended to calibrate separately under at least three color temperatures (2700 K / 4000 K / 6500 K), and to select the CCM by interpolating based on the color temperature estimated by AWB during actual use.

### 3.3 Building an Automated Test System

**Test Fixture Design:**
- Use stepper motors to drive the test chart position, enabling automatic switching between different test patterns
- Illumination control: programmable LED light box with independent control of color temperature and illuminance
- Camera interface: capture RAW data via USB3 UVC or MIPI CSI interface

**Batch Test Data Management:**
- Test results for each device stored by serial number
- Define pass/fail decision thresholds to automatically generate compliance certificates
- Statistical Process Control (SPC): plot Cpk charts to monitor inter-batch performance drift

---

## §4 Common Test Artifacts and Error Sources

### 4.1 Systematic Errors in MTF Measurement

**Tilt Angle Estimation Error:** If the slanted edge angle is inaccurately calculated, super-resolution sampling will introduce phase errors, causing spurious oscillations in the MTF curve.

**Solution:** Use a sub-pixel precision slanted edge angle estimation algorithm (Hough transform or Radon transform), with accuracy better than 0.1°.

**Test Chart Print Quality:** The edge acuity and density (Dmax) of the test chart directly affect MTF measurement accuracy. The edge MTF of the test chart should be significantly higher than that of the system under test; the test chart edge MTF is required to be > 0.5 at the Nyquist frequency.

**Vibration:** Minute vibrations of the camera or test chart will cause MTF measurement results to appear lower (equivalent to additional motion blur). It is recommended to use an anti-vibration table and to verify the ambient vibration level before measurement (monitoring with an accelerometer).

### 4.2 Error Sources in Color Measurement

**Fluorescence Bias:** The fluorescence effect in ColorChecker patches causes bias under UV-rich illumination. Using calibrated standard light sources (CIE A, D65) can reduce this error.

**Color Chart Aging:** The patches on a ColorChecker chart oxidize and fade over time. It is recommended to re-calibrate the color chart every 6–12 months (by comparing with spectrophotometer measurements).

**Angular Effects:** The color chart produces specular reflections under non-normal incident light, causing non-uniform luminance at measurement points. The camera axis should be perpendicular to the color chart plane, with the light source illuminating from a 45° angle (avoiding direct frontal illumination).

### 4.3 Common Issues with Automated Test Systems

**Repeatability Deviation:** When MTF50 differences between repeated tests of the same camera exceed 2%, it is usually caused by the following:
- Inconsistent autofocus results (recommend using manually fixed focus)
- Slight positional variation of the test chart between tests (use mechanical positioning)
- Unstable illumination (lamps require a warm-up stabilization time, typically 10 minutes)

**Lot-to-Lot Drift:** Lens assembly tolerances cause significant MTF50 variation between lots, requiring a Cpk process capability index monitoring system.

---

## §5 Evaluation Methods

### 5.1 Multi-Dimensional Comprehensive Scoring System

ISP testing should not focus on a single metric alone. It is recommended to build a multi-dimensional weighted composite score (IQA Scorecard):

| Test Dimension | Metric | Weight (Example) | Evaluation Tool |
|----------------|--------|-----------------|-----------------|
| Resolution | MTF50 (center) | 25% | Imatest SFR |
| Noise | SNR @ ISO 1600 | 20% | Imatest Noise |
| Color | Delta E00 (mean) | 20% | Imatest ColorChecker |
| Dynamic Range | DR (dB) | 15% | EMVA 1288 |
| Lens Shading | Corner/center ratio | 10% | Imatest Uniformity |
| White Balance | CCT error (K) | 10% | Imatest AWB |

**Composite Score:** $S = \sum_i w_i \cdot s_i$, where $s_i$ is the normalized score for each dimension (0–100).

### 5.2 Fully Automated IQA Pipeline

The IQA pipeline on a production line must satisfy:
- **Speed:** Testing time per device < 30 seconds (including image capture + analysis)
- **Accuracy:** Misjudgment rate (False Accept + False Reject) < 0.1%
- **Traceability:** All test data (RAW images + test results) archived for reference

**Pipeline Architecture:**
1. Device connection (USB/ADB/MIPI) → trigger capture
2. RAW image transferred to test host
3. Each test module executed in parallel (multi-threaded)
4. Results aggregated and compared against thresholds
5. Pass/fail decision output + test report

### 5.3 Statistical Analysis and Process Control

**Gage R&R (Gauge Repeatability and Reproducibility) Analysis:** Evaluates the proportion of variation attributable to the test system itself relative to total variation. The test system variation is required to be < 10% of total variation (Gage R&R < 10%); otherwise, the test system's precision is insufficient to effectively distinguish product differences.

**Cpk Process Capability Index:**
$$Cpk = \min\left(\frac{USL - \bar{X}}{3\sigma}, \frac{\bar{X} - LSL}{3\sigma}\right)$$

A requirement of $Cpk > 1.33$ (equivalent to a defect rate < 64 ppm) applies. Cpk values for MTF50 and Delta E are key metrics for mass production quality control.

---

## §6 Code Implementation

### 6.1 Slanted Edge MTF Computation (Python Implementation)

```python
import numpy as np
import cv2
from typing import Tuple, Optional
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import signal, interpolate


def detect_slanted_edge(image: np.ndarray,
                        roi: Optional[Tuple[int, int, int, int]] = None
                        ) -> Tuple[np.ndarray, float]:
    """
    Detect the slanted edge region in an image; return ROI grayscale image and edge angle.
    image: [H, W] or [H, W, 3] uint8
    roi: (x, y, w, h) or None (auto-detect)
    """
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float64)
    else:
        gray = image.astype(np.float64)

    if roi is not None:
        x, y, w, h = roi
        gray = gray[y:y+h, x:x+w]

    # Use Canny + Hough to detect slanted edge angle
    edges = cv2.Canny(gray.astype(np.uint8), 50, 150)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=50)
    if lines is not None:
        angles = [line[0][1] for line in lines[:5]]
        angle_deg = np.degrees(np.median(angles)) - 90  # Convert to angle relative to horizontal
    else:
        angle_deg = 5.0  # Default 5 degrees

    return gray, angle_deg


def compute_esf(gray: np.ndarray,
                angle_deg: float,
                oversample: int = 4) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute ESF (Edge Spread Function) from a slanted edge image.
    Uses the tilt angle to achieve sub-pixel sampling.

    gray: [H, W] float64, slanted edge region
    angle_deg: slanted edge tilt angle (degrees), relative to vertical
    oversample: oversampling factor
    Returns: (positions, esf_values) ESF with sub-pixel accuracy
    """
    H, W = gray.shape
    tan_angle = np.tan(np.radians(angle_deg))

    # Compute sub-pixel position of each pixel relative to the edge
    pixel_positions = []
    pixel_values = []

    for row in range(H):
        # Estimate edge x-coordinate for this row (based on overall angle)
        edge_x_center = W / 2 + row * tan_angle
        for col in range(W):
            # Sub-pixel offset relative to the edge
            offset = (col - edge_x_center) * oversample
            pixel_positions.append(offset)
            pixel_values.append(gray[row, col])

    # Sort by position
    positions = np.array(pixel_positions)
    values = np.array(pixel_values)
    sort_idx = np.argsort(positions)
    positions = positions[sort_idx]
    values = values[sort_idx]

    # Bin averaging onto a uniform grid
    bin_width = 1.0  # 1/oversample pixels
    bin_edges = np.arange(positions.min(), positions.max() + bin_width, bin_width)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    esf = np.zeros(len(bin_centers))
    counts = np.zeros(len(bin_centers))

    for pos, val in zip(positions, values):
        idx = int((pos - positions.min()) / bin_width)
        if 0 <= idx < len(esf):
            esf[idx] += val
            counts[idx] += 1

    valid = counts > 0
    esf[valid] /= counts[valid]

    # Interpolate to fill gaps
    if not valid.all():
        f_interp = interpolate.interp1d(
            bin_centers[valid], esf[valid],
            kind='linear', fill_value='extrapolate')
        esf = f_interp(bin_centers)

    return bin_centers, esf


def esf_to_mtf(esf: np.ndarray,
               oversample: int = 4) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute MTF from ESF.
    1. Differentiate ESF -> LSF (Line Spread Function)
    2. Window LSF -> reduce truncation effects
    3. FFT -> MTF

    Returns: (frequencies, mtf) with frequencies in cycles/pixel (0 to 0.5)
    """
    # Numerical differentiation to get LSF
    lsf = np.diff(esf)
    lsf = np.append(lsf, lsf[-1])  # Maintain consistent length

    # Hamming window (reduce spectral leakage)
    window = np.hamming(len(lsf))
    lsf_windowed = lsf * window

    # FFT
    fft_result = np.abs(np.fft.fft(lsf_windowed))
    fft_result = fft_result[:len(fft_result) // 2]  # Take positive frequency half

    # Normalize (DC component = 1)
    if fft_result[0] > 0:
        fft_result /= fft_result[0]

    # Frequency axis (cycles/pixel): range is 0 to 0.5 cy/px (Nyquist).
    # The FFT is computed on the oversampled ESF, but the oversampling is
    # already accounted for by the bin_centers in compute_esf (which are in
    # native-pixel units). Do NOT divide by oversample here — doing so would
    # make MTF50 read out as (true_MTF50 / oversample), a 4× underestimate.
    freqs = np.linspace(0, 0.5, len(fft_result))

    return freqs, fft_result


def find_mtf50(freqs: np.ndarray, mtf: np.ndarray) -> float:
    """
    Find the spatial frequency where MTF = 0.5 (MTF50).
    Uses linear interpolation.
    """
    # Find where MTF crosses 0.5 from above
    for i in range(len(mtf) - 1):
        if mtf[i] >= 0.5 >= mtf[i + 1]:
            # Linear interpolation
            t = (0.5 - mtf[i]) / (mtf[i + 1] - mtf[i])
            return freqs[i] + t * (freqs[i + 1] - freqs[i])
    return freqs[-1]  # If MTF always > 0.5, return maximum frequency


def compute_mtf_from_image(image_path: str,
                            roi: Optional[Tuple[int, int, int, int]] = None,
                            oversample: int = 4) -> dict:
    """
    Complete MTF analysis workflow.
    Input: image path (preferably a TIFF converted from 16-bit RAW)
    Output: dictionary of MTF analysis results
    """
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    gray, angle_deg = detect_slanted_edge(image, roi)
    positions, esf = compute_esf(gray, angle_deg, oversample=oversample)
    freqs, mtf = esf_to_mtf(esf, oversample=oversample)
    mtf50 = find_mtf50(freqs, mtf)

    # MTF at Nyquist frequency (f = 0.5 cy/px)
    nyquist_idx = np.argmin(np.abs(freqs - 0.5))
    mtf_nyquist = mtf[nyquist_idx]

    return {
        'mtf50': mtf50,
        'mtf_nyquist': mtf_nyquist,
        'edge_angle_deg': angle_deg,
        'freqs': freqs,
        'mtf': mtf,
        'esf': esf,
        'esf_positions': positions
    }


# ─────────────────────────────────────────────
# ColorChecker Color Calibration (OpenCV)
# ─────────────────────────────────────────────

def compute_ccm_least_squares(
        measured_rgb: np.ndarray,
        reference_xyz: np.ndarray,
        regularization: float = 0.01) -> np.ndarray:
    """
    Least-squares CCM computation (with Tikhonov regularization).

    measured_rgb: [N, 3] linear RGB values measured by the camera (normalized)
    reference_xyz: [N, 3] reference XYZ values (D50 illuminant, normalized)
    regularization: regularization coefficient to prevent overfitting

    Returns: [3, 3] CCM matrix M such that M @ rgb ≈ xyz
    """
    N = measured_rgb.shape[0]
    R = measured_rgb.T  # [3, N]
    X = reference_xyz.T  # [3, N]

    # Regularized least squares: min ||M@R - X||^2 + lambda*||M-I||^2
    I = np.eye(3)
    # Solve each row independently (3 independent regression problems)
    ccm = np.zeros((3, 3))
    for ch in range(3):
        # (R@R^T + lambda*I) @ m = R@x^T + lambda*e
        A = R @ R.T + regularization * np.eye(3)
        b = R @ X[ch] + regularization * I[ch]
        ccm[ch] = np.linalg.solve(A, b)

    return ccm


def compute_delta_e_76(lab1: np.ndarray,
                        lab2: np.ndarray) -> np.ndarray:
    """
    CIE Delta E 1976 (CIE76) computation — Euclidean distance in Lab space.
    lab1, lab2: [..., 3] Lab color space values (L*a*b*)
    Returns: [...] Delta E 76 values

    Note: For the full CIEDE2000 formula (with chroma/hue/lightness weighting),
    use the `colormath` library: colormath.color_diff.delta_e_cie2000().
    """
    diff = lab1.astype(np.float64) - lab2.astype(np.float64)
    # Simplified CIE76 (full CIEDE2000 formula should be used in production)
    delta_e = np.sqrt(np.sum(diff ** 2, axis=-1))
    return delta_e


def evaluate_color_accuracy(
        image: np.ndarray,
        patch_coords: np.ndarray,
        reference_lab: np.ndarray,
        patch_size: int = 20) -> dict:
    """
    Evaluate color accuracy.

    image: [H, W, 3] uint8 BGR image
    patch_coords: [N, 2] center coordinates (x, y) of each patch
    reference_lab: [N, 3] reference Lab values
    patch_size: patch sampling window size (pixels)

    Returns: dictionary of color evaluation results
    """
    # Convert to Lab color space
    image_lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float64)
    # OpenCV Lab range: L [0,100], a [-127,127], b [-127,127]
    image_lab[:, :, 0] *= 100.0 / 255.0  # Normalize L
    image_lab[:, :, 1] -= 128.0           # Normalize a
    image_lab[:, :, 2] -= 128.0           # Normalize b

    half = patch_size // 2
    measured_lab = []
    for x, y in patch_coords:
        x, y = int(x), int(y)
        patch = image_lab[y-half:y+half, x-half:x+half]
        measured_lab.append(patch.mean(axis=(0, 1)))
    measured_lab = np.array(measured_lab)

    delta_e = compute_delta_e_76(measured_lab, reference_lab)

    return {
        'mean_delta_e': delta_e.mean(),
        'max_delta_e': delta_e.max(),
        'delta_e_per_patch': delta_e,
        'measured_lab': measured_lab
    }


# ─────────────────────────────────────────────
# EMVA 1288: PTC Curve Analysis
# ─────────────────────────────────────────────

def analyze_ptc(mean_values: np.ndarray,
                variance_values: np.ndarray) -> dict:
    """
    PTC (Photon Transfer Curve) analysis.
    Extracts gain K, readout noise sigma_d, and dynamic range DR.

    mean_values: [N] mean values (DN) at different illuminance levels
    variance_values: [N] corresponding temporal-sequence variance (DN^2)
    """
    # Linear fit: sigma^2 = sigma_d^2 + K * mu
    # Exclude saturated points (variance drops at high illuminance)
    valid = variance_values > variance_values[0] * 0.5
    valid &= mean_values < mean_values.max() * 0.9

    coeffs = np.polyfit(mean_values[valid], variance_values[valid], 1)
    K = coeffs[0]         # Slope = gain (DN/e-)
    sigma_d_sq = coeffs[1]  # Intercept = readout noise variance (DN^2)
    sigma_d = np.sqrt(max(sigma_d_sq, 0))  # Readout noise (DN)

    # Full Well Capacity (FWC): point where variance starts to drop
    fwc_dn = mean_values[valid].max()
    fwc_electrons = fwc_dn / K

    # Dynamic range (dB)
    if sigma_d > 0:
        dr_db = 20 * np.log10(fwc_dn / sigma_d)
        dr_ev = dr_db / 6.02  # 1 EV ≈ 6.02 dB
    else:
        dr_db = 0
        dr_ev = 0

    # Readout noise in electrons
    sigma_d_electrons = sigma_d / K

    return {
        'gain_K': K,
        'read_noise_DN': sigma_d,
        'read_noise_electrons': sigma_d_electrons,
        'fwc_DN': fwc_dn,
        'fwc_electrons': fwc_electrons,
        'dynamic_range_dB': dr_db,
        'dynamic_range_EV': dr_ev,
        'ptc_fit_coeffs': coeffs
    }


def demo_mtf_analysis():
    """Demonstration of MTF analysis (using a synthetic slanted edge image)."""
    # Generate a synthetic slanted edge image (ideal edge, ~5-degree tilt)
    H, W = 128, 128
    image = np.zeros((H, W), dtype=np.uint8)
    angle_rad = np.radians(5)
    for row in range(H):
        edge_x = W // 2 + row * np.tan(angle_rad)
        for col in range(W):
            if col > edge_x:
                image[row, col] = 200
    # Add slight blur (simulating optical PSF)
    image = cv2.GaussianBlur(image, (3, 3), 1.0)
    # Add noise
    noise = np.random.normal(0, 3, image.shape).astype(np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # ESF and MTF computation
    gray = image.astype(np.float64)
    positions, esf = compute_esf(gray, angle_deg=5.0, oversample=4)
    freqs, mtf = esf_to_mtf(esf, oversample=4)
    mtf50 = find_mtf50(freqs, mtf)

    print(f"Synthetic Slanted Edge MTF Analysis:")
    print(f"  MTF50 = {mtf50:.3f} cy/px")
    print(f"  MTF @ Nyquist (0.5 cy/px) = {mtf[len(mtf)//2]:.3f}")


def demo_ptc_analysis():
    """Demonstration of PTC analysis (using synthetic data)."""
    # Simulate PTC measurement data (K=0.5, sigma_d=20 DN, FWC=60000 DN)
    K_true = 0.5
    sigma_d_true = 20.0
    mu = np.linspace(100, 55000, 50)
    sigma_sq = sigma_d_true**2 + K_true * mu
    sigma_sq += np.random.normal(0, 50, len(sigma_sq))  # Add measurement noise

    results = analyze_ptc(mu, sigma_sq)
    print(f"\nPTC Analysis Results:")
    print(f"  Gain K = {results['gain_K']:.3f} DN/e-  (true value: {K_true})")
    print(f"  Read noise = {results['read_noise_DN']:.1f} DN "
          f"= {results['read_noise_electrons']:.1f} e-")
    print(f"  Dynamic range = {results['dynamic_range_dB']:.1f} dB "
          f"= {results['dynamic_range_EV']:.1f} EV")


if __name__ == '__main__':
    demo_mtf_analysis()
    demo_ptc_analysis()
```

---

## References

[1] ISO 12233:2017. Photography — Electronic still picture imaging — Resolution and spatial frequency responses.
[2] EMVA Standard 1288:2021. Standard for Characterization of Image Sensors and Cameras, Release 4.0. European Machine Vision Association.
[3] Burns, P.D. (2000). Slanted-Edge MTF for Digital Camera and Scanner Analysis. PICS 2000.
[4] Imatest LLC. (2024). Imatest Documentation: SFR, Noise, Color modules. https://www.imatest.com/docs/
[5] X-Rite Inc. (2016). ColorChecker Classic Target. (Data Sheet)
[6] Janesick, J.R. (2001). Scientific Charge-Coupled Devices. SPIE Press. (PTC theory reference)
[7] Ramanath, R., Snyder, W.E., Yoo, Y., Drew, M.S. (2005). Color Image Processing Pipeline. IEEE Signal Processing Magazine.
[8] Reinhard, E., et al. (2010). Color Imaging: Fundamentals and Applications. A K Peters/CRC Press.
[9] Lukac, R. (Ed.) (2018). Computational Photography: Methods and Applications. CRC Press.
[10] IEEE P2020. Automotive Image Quality Standard (under development). IEEE Standards Association.

## §8 Glossary

| Term | Full Name | Description |
|------|-----------|-------------|
| CCM | Color Correction Matrix | Matrix for correcting camera color response |
| Cpk | Process Capability Index | Statistical measure of process capability |
| DR | Dynamic Range | Dynamic range (in dB or EV) |
| ESF | Edge Spread Function | Spatial profile of intensity across an edge |
| EMVA | European Machine Vision Association | Standards body for machine vision |
| FWC | Full Well Capacity | Maximum charge capacity of a pixel (in electrons) |
| Gage R&R | Gauge Repeatability & Reproducibility | Analysis of measurement system variation |
| LSF | Line Spread Function | Derivative of ESF; impulse response along a line |
| MTF | Modulation Transfer Function | Spatial frequency response of an imaging system |
| MTF50 | — | Spatial frequency at which MTF drops to 50% |
| PSF | Point Spread Function | Impulse response of an imaging system at a point |
| PRNU | Photo Response Non-Uniformity | Pixel-to-pixel sensitivity variation |
| PTC | Photon Transfer Curve | Noise characterization curve (mean vs. variance) |
| QE | Quantum Efficiency | Ratio of photoelectrons generated per incident photon |
| ROI | Region of Interest | Selected area of an image for analysis |
| SFR | Spatial Frequency Response | Imatest module for MTF/SFR measurement |
| SNR | Signal-to-Noise Ratio | Ratio of signal power to noise power |
| SPC | Statistical Process Control | Use of statistical methods to monitor manufacturing |
