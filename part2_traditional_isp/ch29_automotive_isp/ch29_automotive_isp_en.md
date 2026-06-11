# Part 2, Chapter 29: Automotive / Industrial Sensor ISP

> **Scope:** This chapter covers the special ISP requirements of automotive cameras (ADAS/AVM/DVR) and industrial cameras — wide-temperature-range calibration, functional safety (ISO 26262), HDR wide-dynamic-range perception, global shutter sensor characteristics, and key architectural considerations for automotive-grade ISP chips.
> **Prerequisites:** Volume 1, Chapter 3 (Sensor Physics); Volume 2, Chapter 8 (Gamma and Tone Mapping)
> **Target readers:** Embedded engineers, algorithm engineers, automotive camera system engineers

---

## Table of Contents

1. [Special Requirements of Automotive ISP](#1-special-requirements-of-automotive-isp)
2. [Automotive Sensors and Calibration Methods](#2-automotive-sensors-and-calibration-methods)
3. [AVM Surround-View System ISP Design](#3-avm-surround-view-system-isp-design)
4. [Special ISP for Industrial Cameras](#4-special-isp-for-industrial-cameras)
5. [Tuning Guide](#5-tuning-guide)
6. [Common Artifacts and Failure Modes](#6-common-artifacts-and-failure-modes)
7. [Evaluation Methods](#7-evaluation-methods)
8. [Code Example](#8-code-example)
9. [References](#references)
10. [Glossary](#glossary)

---

## 1 Special Requirements of Automotive ISP

### 1.1 Operating Environment: Extreme Temperature Range

Automotive cameras must operate over a wide temperature range of **–40 °C to +125 °C** (AEC-Q100 Grade 1 for SoC; camera module typically rated to +105 °C), far exceeding the consumer mobile camera range (–20 °C to +60 °C). Temperature variation has the following primary effects on image sensors:

**Dark current (暗电流) temperature characteristics:** Dark current increases exponentially with temperature, approximately following the Arrhenius model:

$$I_{\text{dark}}(T) = I_0 \cdot \exp\left(-\frac{E_a}{k_B T}\right)$$

where $E_a \approx 0.6 \text{ eV}$ (silicon activation energy), $k_B$ is the Boltzmann constant, and $T$ is absolute temperature (K). Dark current roughly doubles for every 6–8 °C rise in temperature. At 105 °C, dark current can be 100–1000× higher than at 25 °C, causing severe image noise and black-level shift.

**Read noise (读出噪声):** Temperature has a relatively small effect on read noise (within ±20 %), although analog circuit performance may degrade at low temperatures.

**Fixed Pattern Noise (FPN, 固定图案噪声):** Dark current non-uniformity increases with temperature; FPN becomes more pronounced at high temperatures and BLC (Black Level Correction) calibration must be performed at the corresponding temperature points.

**Pixel sensitivity drift:** Temperature variation causes a slight drift in sensor quantum efficiency (QE, 量子效率) — typically ±2 %/10 °C. Compensation is required for precision measurement applications such as lane-color recognition.

### 1.2 Functional Safety: ISO 26262 ASIL Requirements

ISO 26262 is the international functional safety standard for automotive electrical/electronic systems. It classifies system hazard levels from ASIL-A (lowest) to ASIL-D (highest). Camera-related ISP chips typically must satisfy:

- **ADAS forward-looking cameras:** ASIL-B to ASIL-C (affecting emergency braking, lane keeping)
- **AVM surround-view cameras:** ASIL-A to ASIL-B (parking assistance)
- **DVR dash cameras:** QM (Quality Management; no ASIL requirement)

**Engineering implementation of ISP functional safety requirements:**

1. **Image Integrity Monitoring:** Real-time detection of image quality anomalies (blurring, darkness, occlusion), with a validity flag (Valid Flag) output to higher-level ADAS algorithms
2. **Dual-path ISP:** Some ASIL-C/D applications require redundant ISP processing paths; two independent processing results are compared, and a safety response is triggered when the difference exceeds a threshold
3. **Memory ECC (Error Correcting Code):** ISP internal SRAM/DRAM must be configured with ECC to prevent Single Event Upsets (SEU, 单粒子翻转) from corrupting image data
4. **Watchdog timer:** Monitors the ISP frame-processing rate; outputs an alarm signal if processing times out for N consecutive frames
5. **BIST (Built-In Self Test):** On power-up, performs self-diagnosis of ISP hardware, checking register and memory faults

### 1.3 Global Shutter Sensor Eliminates Jello Effect

The row-sequential exposure of Rolling Shutter sensors produces the "Jello Effect" (果冻效应) under vehicle vibration (engine shake, road bumps) and fast lateral movement — image deformation along the vertical direction that severely affects ADAS object detection and ranging accuracy.

A Global Shutter (全局快门, GS) sensor exposes all pixels simultaneously, completely eliminating the Jello Effect. It is the preferred solution for automotive forward-looking cameras (especially high-speed driving scenarios). Key engineering characteristics of Global Shutter sensors:

- **Storage node (存储节点):** Each pixel requires an additional storage node to hold accumulated charge during the exposure period until row readout is complete. The storage node must be metal-shielded, introducing extra pixel area (fill factor reduced by approximately 20–40 %)
- **Parasitic Light Sensitivity (PLS, 寄生光敏性):** The storage node is not perfectly shielded from light, so a small number of external photons still leak into the storage node during exposure, producing an extra signal. ISP must compensate for PLS (frame-reference subtraction)
- **Dynamic range impact:** The storage node introduces additional dark current and kTC noise; Global Shutter sensors typically have a dynamic range approximately 6–10 dB lower than contemporary Rolling Shutter sensors

### 1.4 120 dB Wide Dynamic Range Requirement

Automotive cameras encounter scenes with extreme lighting contrast (tunnel exits, driving into back-lit conditions, direct headlight illumination), requiring the ISP system dynamic range to reach **120 dB or more** (consumer cameras typically achieve 70–80 dB).

Main technology approaches for achieving 120 dB dynamic range:
1. **Multi-exposure HDR merging** (see Volume 2, Chapter 11 (HDR frame merging)): short-exposure + long-exposure multi-frame merging
2. **Dual Conversion Gain (DCG, 双转换增益):** Sensor switches between high and low conversion gain to achieve wide dynamic range within a single exposure
3. **Logarithmic response (对数感光):** Some industrial sensors support a pixel logarithmic response mode, which naturally compresses large dynamic ranges
4. **Compressive sensing (压缩感知):** Emerging approach; encodes wide-dynamic-range information within a single frame through random exposure patterns

---

## 2 Automotive Sensors and Calibration Methods

### 2.1 Multi-Temperature BLC Calibration

Because dark current varies dramatically with temperature, automotive ISP must build a **multi-temperature BLC calibration table**:

**Calibration procedure:**
1. Place the sensor in a temperature chamber; stabilize at multiple temperature points: –40 °C, –20 °C, 0 °C, 25 °C, 40 °C, 60 °C, 85 °C, 105 °C
2. At each temperature point, capture multiple dark-field frames (with light blocked); compute the mean and standard deviation for each channel (R/Gr/Gb/B)
3. Build a 2D BLC lookup table BLC(T, ISO): index by temperature and gain; output is the BLC value for each channel
4. At runtime, use the real-time temperature sensor reading and current ISO to bilinearly interpolate the current BLC compensation value

**Calibration accuracy requirement:** BLC calibration error < 1 DN (digital code value); otherwise, visible color cast occurs at high ISO.

**OB (Optical Black) pixel method:** High-end automotive sensors typically reserve shielded pixels (OB region) at the chip edge. The ISP can read the OB pixel mean in real time as a dynamic BLC reference, without relying on a temperature sensor. The OB method achieves higher accuracy but requires hardware support in the sensor.

### 2.2 Wide-Dynamic-Range HDR Calibration

Automotive HDR calibration requires separate calibration for each exposure level in the multi-exposure fusion:

**Multi-exposure response curve (CRF, Camera Response Function) calibration:**
1. Capture a uniform, known-radiance light field at each exposure level (e.g., short exposure 1/10000 s, medium 1/1000 s, long 1/100 s)
2. For each exposure level, establish linearization coefficients: digital output value → true radiance
3. The HDR merging algorithm depends on accurate CRF to achieve seamless multi-exposure fusion (otherwise halo artifacts appear)

### 2.3 Fisheye Lens Geometric Calibration (AVM Applications)

AVM (Around View Monitor, 环视摄像) systems use four wide-angle/fisheye cameras (front, rear, left, right); a single lens typically covers 180° or more. Fisheye lens calibration requires dedicated fisheye distortion models (Equidistant / Equisolid-angle / Orthographic projection models), which differ from the standard pinhole camera model.

**Calibration procedure** (reference: OpenCV fisheye model):
1. Prepare a checkerboard calibration target; capture images at multiple positions and angles (covering the entire field of view)
2. Detect checkerboard corners; minimize reprojection error using the fisheye distortion model
3. Output intrinsics (focal lengths $f_x, f_y$, principal point $c_x, c_y$) and distortion coefficients ($k_1, k_2, k_3, k_4$)
4. Automotive requirement: reprojection error RMS < 0.5 pixels

**Extrinsic calibration (multi-camera joint extrinsic calibration):**
- Use ground-plane checkerboards or dedicated calibration targets (ADAS Camera Calibration Target); calibrate the relative positions and orientations of all four cameras simultaneously in the same scene
- Extrinsic accuracy requirements: position error < 5 mm, angular error < 0.3° (otherwise, visible misalignment occurs at AVM stitching seams)

### 2.4 Automotive Tolerances and Mass-Production Consistency

After reliability testing (vibration, shock, thermal cycling), calibration parameters of automotive camera modules may drift. Engineering practice requires:
- **Principal-point drift:** < 2 pixels after thermal cycling (otherwise lane-detection accuracy degrades)
- **Focal-length drift:** < 0.5 % (focal-length accuracy directly affects monocular ranging accuracy)
- **Factory calibration validity period:** Typical automotive requirements specify that calibration data remain valid for the vehicle's lifetime (15 years / 200,000 km); accelerated aging verification is required

---

## 3 AVM Surround-View System ISP Design

### 3.1 Four-Channel Camera Synchronization

AVM systems require all four cameras to **expose synchronously**, preventing motion objects (pedestrians, vehicles) from appearing as "ghosts" or "disappearing" in the stitched top-down view due to different image timestamps.

Synchronization mechanism:
- **Hardware synchronization:** The SoC (or MCU) outputs a unified synchronization trigger signal (VSYNC Trigger) to simultaneously control the exposure start instant of all four sensors
- **Software alignment:** When hardware synchronization is unavailable, align via timestamps + phase adjustment so that the difference in exposure center instants across the four channels is < 1 ms

**AE/AWB synchronization:** The four cameras face different directions; lighting conditions may differ significantly (e.g., front in back-light, rear in front-light). The AE algorithm runs independently for each channel, but to ensure consistent tone across the stitched view, **global luminance equalization** is applied to the tone-mapping outputs of the four channels:

$$L_{\text{eq}}^{(i)} = \alpha^{(i)} \cdot L^{(i)} + \beta^{(i)}, \quad i = 0,1,2,3$$

where $\alpha^{(i)}, \beta^{(i)}$ are the linear equalization coefficients for channel $i$, computed centrally to ensure smooth luminance transition at stitching boundaries.

### 3.2 ISP-SVM Color Equalization

One of the key quality metrics of a stitched Surround View Module (SVM, 环视图生成模块) is **color uniformity**: adjacent cameras' overlapping regions should have consistent colors. Due to lens aging and sensor batch differences, color differences between channels actually exist in practice.

Color equalization method:
1. Extract color samples from the overlap zones (Overlap Zone, typically near the four corners of the vehicle)
2. Compute the color difference between adjacent cameras in the overlap zone (ΔE in Lab color space)
3. Apply a 3×3 CCM (Color Correction Matrix) or per-channel gain to each channel's output, so that the color difference ΔE in the overlap zone is < 3.0

### 3.3 Inverse Perspective Mapping (IPM) and Ground Projection

AVM systems need to convert the perspective view from each camera into a ground-plane top-down view. The core algorithm is Inverse Perspective Mapping (IPM, 逆透视变换):

**Basic principle:** Using camera intrinsics and extrinsics (known height H, pitch angle, etc.), project ground-plane points from image coordinates to world coordinates:

Let image coordinates be $(u, v)$, ground height $Z = 0$, and world coordinates $(X, Y, 0)$ satisfy:

$$\lambda \begin{pmatrix} u \\ v \\ 1 \end{pmatrix} = K [R | t] \begin{pmatrix} X \\ Y \\ 0 \\ 1 \end{pmatrix}$$

where $K$ is the intrinsic matrix and $[R|t]$ is the extrinsic. Solving yields world coordinates.

**Position of IPM in the ISP pipeline:** IPM is typically executed in an independent hardware module (Warp Engine) downstream of the ISP, receiving YUV images from the ISP output and producing the transformed top-down view. From the ISP side, LSC (Lens Shading Correction) must be completed before IPM; otherwise, uneven edge luminance produces arc-shaped bright/dark bands in the top-down view.

### 3.4 ADAS-Perception-Specific Tone Mapping

ADAS object detection networks (vehicle/pedestrian/lane detection) are typically trained on sRGB color-space normal tone-mapped images. When automotive HDR images are fed directly into ADAS networks, **perception-preserving tone mapping** is required:

Unlike traditional consumer-grade tone mapping (emphasizing visual aesthetics), the optimization objectives of ADAS-specific tone mapping are:
1. **Object detection recall:** Ensure that objects across the full dynamic range (pedestrians in dark areas, vehicles in bright areas) remain detectable after compression
2. **Color consistency:** The same category of object (e.g., white vehicles) presents stable color appearance across different exposure conditions
3. **Low latency:** Meets ADAS real-time processing requirements (typically < 33 ms/frame)

Representative work: Eilertsen et al. (2017) proposed a convolutional neural network tone mapping for HDR images, outperforming traditional Reinhard/Drago operators in ADAS scenes.

---

## 4 Special ISP for Industrial Cameras

### 4.1 Line Scan Camera (Linear Array Sensor)

A line scan sensor (线阵传感器) reads only one row (or a few rows) of pixels at a time; a complete image is scanned through relative motion between a conveyor belt or object and the sensor. Widely used in industrial inspection (print quality, wafer inspection, textile defect detection).

**Special ISP requirements:**
- **Linear response preservation:** Industrial inspection depends on accurate grayscale or color quantization; sensors are typically operated in the linear response region (no Gamma encoding), or precise inverse-Gamma linearization is required
- **FPN correction (per-column FPN):** Fixed pattern noise in line scan sensors mainly manifests as inter-column non-uniformity (rather than inter-frame), requiring a per-column gain/offset compensation table
- **TDI (Time Delay Integration) mode:** Advanced line scan sensors support TDI mode, accumulating signals from multiple rows to improve SNR (for detecting dim objects); ISP must handle motion aliasing introduced by TDI cascading

**Correction method** (reference: EMVA 1288):
1. Capture a reference image under uniform illumination; compute gain $g_c$ and offset $o_c$ for each column
2. For each column's output: $P_c' = (P_c - o_c) / g_c$ (joint PRNU + DSNU correction)

### 4.2 High-Speed Photography ISP (1000 fps+)

High-speed imaging (≥ 1000 fps) requires ISP with extremely low latency and extremely high bandwidth:

- **Row timing:** At 1000 fps with 1080 rows, each row's readout time is only about 0.9 µs (compared to ~33 µs/row at consumer 30 fps), requiring ISP module processing latency to shorten proportionally
- **Denoising trade-off:** Ultra-high-speed photography typically involves very short exposure times (< 1 ms), resulting in low signal and high noise; however, frame rate constraints prevent temporal noise reduction (TNR), so spatial noise reduction (SNR) is the primary approach
- **Data bandwidth:** 1000 fps × 1080P × 12 bit ≈ 25 Gbps; requires high-speed serial interfaces (CoaXPress / Camera Link HS) and high-bandwidth memory (HBM)

### 4.3 Industrial Camera Interface Standards

| Interface | Bandwidth | Cable Length | Applications |
|-----------|-----------|--------------|--------------|
| **GigE Vision** | 125 MB/s (×4 = 500 MB/s) | 100 m | Low-speed machine vision, long-range transmission |
| **USB3 Vision** | 400 MB/s | 5 m | Medium-speed industrial inspection, desktop devices |
| **Camera Link** | Up to 6.8 Gbps | 15 m | High-speed line scan and area scan sensors |
| **CoaXPress** | Up to 12.5 Gbps × 4 | 40 m (coaxial) | High-speed high-resolution industrial cameras |

ISP design must account for transmission latency and packet error rates for the specific interface.

### 4.4 Scientific Imaging ISP (Cooled CCD/CMOS)

Scientific imaging applications (astronomy, medical, materials analysis) use cooled sensors (−100 °C liquid-nitrogen cooling or semiconductor cooling). ISP characteristics:
- **Extremely low dark current:** Cooling greatly suppresses dark current; FPN is primarily determined by readout circuitry
- **Bias-frame / dark-frame subtraction:** The standard scientific imaging pipeline includes per-pixel subtraction of a Bias Frame and a Dark Frame
- **Flat-field frame normalization:** Per-pixel normalization using a uniformly illuminated flat-field frame (Flat Field Frame) to eliminate pixel response non-uniformity
- **Cosmic ray rejection:** When stacking multiple frames, reject high-energy particle impact bright spots that appear in a single frame

---

## 5 Tuning Guide

### 5.1 Temperature BLC Compensation Table Calibration Density

| Temperature Sampling Interval | Application | Interpolation Error (reference) |
|-------------------------------|-------------|----------------------------------|
| One point every 20 °C | Low-accuracy applications | ~2–3 DN (at high temperature) |
| One point every 10 °C | Standard automotive | ~0.5–1 DN |
| One point every 5 °C | High-accuracy scientific imaging | ~0.1–0.2 DN |

Recommendation: For automotive applications, use one point per 10 °C; increase to one point per 5 °C in the high-temperature segment (> 85 °C) because dark current changes faster in this range.

### 5.2 HDR Fusion Weight Tuning

The weight function for multi-exposure HDR fusion (Exposure Fusion) directly affects the trade-off between dynamic range and noise:

- **Highlight protection zone (overexposed region):** Weight should drop rapidly to 0 for long exposures; avoid using overexposed pixels
- **Shadow transition zone:** Weight transitions smoothly from short to long exposure; note that short-exposure SNR is extremely low in very dark regions and its weight should not be too high
- **Fusion exposure ratio:** Typical settings 4× or 16× (three levels: high/medium/low); excessively large exposure ratios produce noise steps at fusion boundaries

### 5.3 Fisheye LSC Calibration

Lens shading correction (LSC) for AVM fisheye lenses differs from standard wide-angle lenses:
- 180°+ field of view causes extreme edge luminance attenuation (> 3× center luminance); the LSC gain table must cover the high-gain edge region
- Noise amplification in the high-gain (> 4×) edge region is significant; requires joint tuning with the denoising algorithm
- Fisheye lens distortion parameters drift more with temperature; verify LSC effectiveness at multiple temperature points

### 5.4 AVM Stitching Seam Quality Tuning

Image quality tuning objectives at AVM stitching seams:
1. Color difference at seam ΔE < 3.0 (within JND)
2. Luminance gradient transition band width > 30 pixels (avoid hard cuts)
3. No ghosting at stitching region (overlapping objects between adjacent cameras should appear as a single clear contour)

---

## 6 Common Artifacts and Failure Modes

### 6.1 High-Temperature Dark-Current Hot Pixels (Thermal Noise Hot Pixels)

**Symptom:** Numerous random bright spots appear in images at high temperature (> 85 °C); their density increases rapidly with temperature.

**Cause:** Spatial non-uniformity of dark current (DSNU, 暗信号非均匀性) increases with temperature; some "hot pixels" have extremely high dark current and saturate at elevated temperatures.

**Solution:** Dynamic hot-pixel detection (real-time dark-field detection with defect map updates), temperature-segmented BLC compensation, or use sensors that support on-chip dark current cancellation.

### 6.2 Global Shutter PLS (Parasitic Light Sensitivity) Smearing

**Symptom:** Bright objects in global shutter images (e.g., headlights, sun) are surrounded by hazy smearing that resembles light leakage during exposure.

**Cause:** The storage node's shielding is incomplete; a small number of photons still leak into the storage node during exposure, producing an extra signal (PLS, Parasitic Light Sensitivity).

**Solution:** Frame Reference Subtraction: capture a reference frame under dark conditions and subtract it from the normal image; or improve the sensor hardware shielding structure.

### 6.3 HDR Fusion Halo

**Symptom:** After HDR fusion, bright halos appear at high-contrast boundaries (e.g., window edges); unnaturally bright regions appear just inside boundaries.

**Cause:** Inaccurate motion estimation between exposure images during fusion, or non-smooth weight transitions at boundaries, causing the short-exposure (highlight) image's weight to contaminate the dark region.

**Solution:** Improve fusion weight calculation (introduce spatial consistency constraints); refine motion alignment algorithm (optical flow or feature-point registration).

### 6.4 Fisheye LSC Over-Correction Bands

**Symptom:** Bright/dark arc bands centered at the camera position appear in the AVM top-down view.

**Cause:** LSC gain table over-compensates at the extreme edge of the fisheye lens, or integrating-sphere non-uniformity during calibration introduces gain table bias.

**Solution:** Recalibrate LSC, limit the maximum gain in edge regions, apply smoothness constraints to the gain table.

### 6.5 AVM Stitching Zone Pedestrian "Cutting" Artifacts

**Symptom:** A pedestrian or obstacle located exactly at a stitching seam is "cut" into two halves that are misaligned.

**Cause:** Insufficient extrinsic calibration accuracy of the two cameras, or the pedestrian is at a position where the ground-plane assumption breaks down (the person is above ground level).

**Solution:** Improve extrinsic calibration accuracy; use height-aware stitching algorithms in the seam region; or incorporate LiDAR/ultrasound depth information as assistance.

---

## 7 Evaluation Methods

### 7.1 Parameter Drift Evaluation After Thermal Cycling

**Test method** (reference: AEC-Q100 standard):
1. Subject the camera module under test to thermal shock (–40 °C ↔ +105 °C, 100 cycles)
2. Capture calibration images at standard conditions (25 °C) before and after each cycle
3. Evaluation metrics: BLC mean drift < 1 DN, LSC non-uniformity change < 5 %, fisheye distortion coefficient drift < 0.1 %

### 7.2 AVM Stitching Seam ΔE Evaluation

1. Place a standard ColorChecker card directly above the AVM stitching seam (on the ground or at low height)
2. Generate a top-down view; sample colors on both sides of the seam at the card's color patches
3. Compute ΔE00 (CIEDE2000 color difference) between corresponding patches on both sides of the seam
4. Pass criterion: ΔE00 < 3.0 (JND threshold)

### 7.3 ADAS Perception Performance Evaluation

The impact of ISP parameter changes on ADAS algorithm accuracy can be quantified through end-to-end evaluation:
- **Object detection AP (Average Precision):** Fix the ADAS detection network; compare detection AP under different ISP settings
- **Recall vs. false-positive rate:** Focus on detection recall for extremely dark regions (pedestrians inside tunnels) and extremely bright regions (backlit vehicles)
- **Reference benchmarks:** KITTI dataset (Geiger et al., CVPR 2012), nuScenes (Caesar et al., CVPR 2020)

### 7.4 Dark-Region SNR Evaluation

At extreme temperature conditions of –40 °C and +105 °C, capture a known-luminance uniform field image and compute the SNR of the dark region (10 % gray target):

$$\text{SNR}_{\text{dark}} = 20 \log_{10}\left(\frac{\mu_{\text{signal}}}{\sigma_{\text{noise}}}\right) \text{ (dB)}$$

Automotive requirements: SNR > 30 dB (–40 °C), > 25 dB (+105 °C).

---

## 8 Code Example

```python
"""
Automotive ISP Demo: Multi-temperature BLC compensation lookup table interpolation
Dependencies: numpy, scipy, matplotlib
Usage: python ch27_automotive_isp_demo.py
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import RegularGridInterpolator
from typing import Dict, Tuple


# ─────────────────────────────────────────────
# Part 1: Multi-temperature BLC calibration table structure
# ─────────────────────────────────────────────

def build_blc_lut(
    temperatures: np.ndarray,   # Calibration temperature points (°C)
    iso_values: np.ndarray,     # Calibration ISO points
    seed: int = 42,
) -> Dict[str, np.ndarray]:
    """
    Generate a simulated multi-temperature/multi-ISO BLC calibration lookup table (LUT).

    Real calibration comes from dark-field image measurements;
    here the Arrhenius model simulates dark current temperature characteristics.

    Returns:
        blc_lut: {'R': array, 'Gr': array, 'Gb': array, 'B': array}
                 Each array has shape (len(temperatures), len(iso_values))
                 Values are per-channel BLC values (DN, 12-bit, range 0–4095)
    """
    rng = np.random.default_rng(seed)

    # Arrhenius model: dark current increases exponentially with temperature
    # Base dark current at 25 °C reference (units: DN/s)
    base_dark_current = {'R': 0.5, 'Gr': 0.4, 'Gb': 0.42, 'B': 0.55}

    # Activation energy Ea/kB ≈ 7000 K (silicon ~0.6 eV)
    Ea_over_kB = 7000.0  # K
    T_ref = 25.0 + 273.15  # K

    T_K = temperatures + 273.15  # Convert to Kelvin

    blc_lut = {}
    for ch, i_base in base_dark_current.items():
        # Arrhenius: I_dark(T) = I_0 * exp(Ea/kB * (1/T_ref - 1/T))
        dark_factor = np.exp(Ea_over_kB * (1.0 / T_ref - 1.0 / T_K))  # shape (nT,)

        # ISO scaling (higher gain → larger equivalent DN from dark current)
        iso_gain = iso_values / 100.0  # Normalize; ISO100 = 1×

        # 2D BLC table [nT × nISO]
        blc = (i_base * dark_factor[:, np.newaxis] * iso_gain[np.newaxis, :]
               + 64.0  # Base black-level offset
               + rng.normal(0, 0.2, (len(temperatures), len(iso_values))))  # Small calibration noise

        blc_lut[ch] = blc.astype(np.float32)

    return blc_lut


# ─────────────────────────────────────────────
# Part 2: Runtime BLC interpolation query
# ─────────────────────────────────────────────

class TemperatureBLCCompensator:
    """
    Automotive multi-temperature/multi-ISO BLC compensator.

    Uses bilinear interpolation from the calibration LUT
    to obtain BLC values at arbitrary temperature and ISO.
    """

    def __init__(
        self,
        temperatures: np.ndarray,
        iso_values: np.ndarray,
        blc_lut: Dict[str, np.ndarray],
    ):
        self.temperatures = temperatures
        self.iso_values = iso_values
        self.blc_lut = blc_lut

        # Build interpolator for each channel (bilinear)
        self._interpolators = {}
        for ch, lut in blc_lut.items():
            self._interpolators[ch] = RegularGridInterpolator(
                (temperatures, iso_values),
                lut,
                method='linear',
                bounds_error=False,
                fill_value=None,  # Extrapolate beyond range (clamp to boundary value)
            )

    def query(self, temp_c: float, iso: float) -> Dict[str, float]:
        """
        Query BLC values at the specified temperature and ISO.

        Args:
            temp_c: Current temperature (°C), from on-chip temperature sensor
            iso: Current ISO value

        Returns:
            {'R': blc_R, 'Gr': blc_Gr, 'Gb': blc_Gb, 'B': blc_B}
        """
        point = np.array([[temp_c, iso]])
        result = {}
        for ch, interp in self._interpolators.items():
            val = float(interp(point)[0])
            # Constrain BLC range for 12-bit sensor
            result[ch] = float(np.clip(val, 0, 255))
        return result

    def apply_blc(
        self,
        raw_image: np.ndarray,
        bayer_pattern: str = 'RGGB',
        temp_c: float = 25.0,
        iso: float = 100.0,
    ) -> np.ndarray:
        """
        Apply temperature-adaptive BLC compensation to a RAW image.

        Args:
            raw_image: (H, W) uint16 Bayer image
            bayer_pattern: 'RGGB' / 'BGGR' / 'GRBG' / 'GBRG'
            temp_c: Current temperature (°C)
            iso: Current ISO

        Returns:
            corrected: (H, W) float32 BLC-compensated image
        """
        blc = self.query(temp_c, iso)

        # Bayer channel offset mapping
        pattern_map = {
            'RGGB': {'R': (0, 0), 'Gr': (0, 1), 'Gb': (1, 0), 'B': (1, 1)},
            'BGGR': {'B': (0, 0), 'Gb': (0, 1), 'Gr': (1, 0), 'R': (1, 1)},
            'GRBG': {'Gr': (0, 0), 'R': (0, 1), 'B': (1, 0), 'Gb': (1, 1)},
            'GBRG': {'Gb': (0, 0), 'B': (0, 1), 'R': (1, 0), 'Gr': (1, 1)},
        }
        offsets = pattern_map[bayer_pattern]

        corrected = raw_image.astype(np.float32)
        for ch, (row_off, col_off) in offsets.items():
            corrected[row_off::2, col_off::2] -= blc[ch]

        return np.clip(corrected, 0, 4095)


# ─────────────────────────────────────────────
# Part 3: Simplified AVM color equalization example
# ─────────────────────────────────────────────

def avm_color_balance(
    images: list,
    overlap_masks: list,
) -> Tuple[list, list]:
    """
    AVM 4-channel camera color equalization (linear gain compensation).

    Computes the color difference between cameras in the overlap region
    and outputs RGB gain compensation coefficients for each camera.

    Args:
        images: list of (H, W, 3) float32 images [front, right, rear, left]
        overlap_masks: list of (H, W) bool masks marking the overlap region

    Returns:
        gains: list of [r_gain, g_gain, b_gain] for each camera
        balanced: list of color-balanced images
    """
    n = len(images)
    assert n == len(overlap_masks)

    # Compute mean color in the overlap region for each channel
    mean_colors = []
    for img, mask in zip(images, overlap_masks):
        if mask.sum() > 0:
            mean_colors.append(img[mask].mean(axis=0))  # (3,) RGB mean
        else:
            mean_colors.append(img.mean(axis=(0, 1)))

    # Use the global mean of all channels as the reference
    global_mean = np.mean(mean_colors, axis=0)  # (3,)

    gains = []
    balanced = []
    for i, (img, mc) in enumerate(zip(images, mean_colors)):
        gain = global_mean / (mc + 1e-9)
        gain = np.clip(gain, 0.5, 2.0)  # Limit gain range
        gains.append(gain.tolist())
        balanced.append(np.clip(img * gain[np.newaxis, np.newaxis, :], 0, 1).astype(np.float32))

    return gains, balanced


# ─────────────────────────────────────────────
# Part 4: Comprehensive demo
# ─────────────────────────────────────────────

def run_demo():
    print("=" * 60)
    print("Automotive ISP Demo  (ch27_automotive_isp)")
    print("=" * 60)

    # Calibration temperature points and ISO points
    temperatures = np.array([-40, -20, 0, 25, 40, 60, 85, 105], dtype=np.float32)
    iso_values   = np.array([100, 200, 400, 800, 1600, 3200], dtype=np.float32)

    # Build simulated BLC LUT
    print("\n[1] Building multi-temperature BLC calibration table...")
    blc_lut = build_blc_lut(temperatures, iso_values)
    compensator = TemperatureBLCCompensator(temperatures, iso_values, blc_lut)

    # Print BLC query results at different temperatures/ISOs
    print("\n[2] BLC interpolation query examples (channel R):")
    print(f"    {'Temp(°C)':>10} {'ISO':>8} {'BLC_R':>10}")
    print("    " + "-" * 32)
    test_cases = [(-30, 100), (0, 400), (25, 800), (80, 1600), (100, 3200)]
    for t, iso in test_cases:
        blc = compensator.query(t, iso)
        print(f"    {t:>10.0f} {iso:>8.0f} {blc['R']:>10.2f}")

    # Visualize BLC vs. temperature
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    temp_range = np.linspace(-40, 105, 200)
    for iso in [100, 400, 1600]:
        blc_r = [compensator.query(t, iso)['R'] for t in temp_range]
        axes[0].plot(temp_range, blc_r, label=f'ISO {iso}')
    axes[0].set_xlabel('Temperature (°C)')
    axes[0].set_ylabel('BLC value (DN)')
    axes[0].set_title('Channel R BLC vs. Temperature (Arrhenius model)')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Demonstrate BLC application
    rng = np.random.default_rng(0)
    H, W = 64, 64

    # Simulate a RAW image with severe dark current at high temperature
    temp_demo = 100.0
    blc_hot = compensator.query(temp_demo, 800)
    true_signal = (rng.integers(100, 600, (H, W), dtype=np.uint16))
    dark_noise = rng.normal(blc_hot['R'], 5, (H, W)).astype(np.float32)
    raw_hot = np.clip(true_signal + dark_noise, 0, 4095).astype(np.uint16)

    corrected_hot = compensator.apply_blc(raw_hot, 'RGGB', temp_c=temp_demo, iso=800)

    axes[1].hist(raw_hot.flatten(), bins=50, alpha=0.6, label=f'Before BLC (T={temp_demo}°C)', color='red')
    axes[1].hist(corrected_hot.flatten(), bins=50, alpha=0.6, label='After BLC compensation', color='blue')
    axes[1].axvline(true_signal.mean(), color='green', linestyle='--', label='True signal mean')
    axes[1].set_xlabel('Pixel value (DN)')
    axes[1].set_ylabel('Pixel count')
    axes[1].set_title('High-temperature BLC compensation effect (simulated)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = 'automotive_isp_demo.png'
    plt.savefig(out_path, dpi=120)
    plt.close()
    print(f"\nDemo figure saved: {out_path}")

    # AVM color equalization demo
    print("\n[3] AVM color equalization demo...")
    rng2 = np.random.default_rng(1)
    H2, W2 = 64, 64

    # Simulate 4 camera images with slight color differences
    base_color = np.array([0.5, 0.48, 0.46])
    cam_offsets = [
        np.array([0.05, 0.0, -0.03]),
        np.array([-0.03, 0.04, 0.0]),
        np.array([0.02, -0.02, 0.05]),
        np.array([0.0, 0.01, -0.01]),
    ]
    images = []
    for offset in cam_offsets:
        img = np.ones((H2, W2, 3), dtype=np.float32) * (base_color + offset)
        img += rng2.normal(0, 0.01, img.shape).astype(np.float32)
        img = np.clip(img, 0, 1)
        images.append(img)

    # Use entire image as overlap region (simplified demo)
    masks = [np.ones((H2, W2), dtype=bool)] * 4

    gains, balanced = avm_color_balance(images, masks)
    print(f"    {'Camera':>8}  {'R gain':>8}  {'G gain':>8}  {'B gain':>8}")
    cam_names = ['Front', 'Right', 'Rear', 'Left']
    for i, (g, name) in enumerate(zip(gains, cam_names)):
        print(f"    {name:>8}  {g[0]:>8.4f}  {g[1]:>8.4f}  {g[2]:>8.4f}")

    print("=" * 60)


if __name__ == '__main__':
    run_demo()
```

---

## References

[1] Geiger, A., et al. "Are We Ready for Autonomous Driving? The KITTI Vision Benchmark Suite." Proceedings of CVPR, 2012, pp. 3354–3361.
[2] Caesar, H., et al. "nuScenes: A Multimodal Dataset for Autonomous Driving." Proceedings of CVPR, 2020, pp. 11621–11631.
[3] ISO 26262-1:2018. "Road Vehicles — Functional Safety." International Organization for Standardization, 2018.
[4] Eilertsen, G., et al. "HDR Image Reconstruction from a Single Exposure Using Deep CNNs." ACM Transactions on Graphics (SIGGRAPH Asia), vol. 36, no. 6, 2017.
[5] Zhang, Z. "A Flexible New Technique for Camera Calibration." IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 22, no. 11, 2000, pp. 1330–1334.
[6] Scaramuzza, D., et al. "A Toolbox for Easily Calibrating Omnidirectional Cameras." Proceedings of IEEE/RSJ IROS, 2006, pp. 5695–5701.
[7] EMVA Standard 1288 Release 4.0. "Standard for Characterization of Image Sensors and Cameras." European Machine Vision Association, 2021.
[8] Fossum, E.R., & Hondongwa, D.B. "A Review of the Pinned Photodiode for CCD and CMOS Image Sensors." IEEE Journal of the Electron Devices Society, vol. 2, no. 3, 2014.
[9] He, K., et al. "Single Image Haze Removal Using Dark Channel Prior." IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 33, no. 12, 2011.
[10] ON Semiconductor. "Automotive Image Sensor Design Guide." Application Note AND9636/D, 2018.

## Glossary

| Term | Full Form / Explanation |
|------|-------------------------|
| **ADAS (Advanced Driver Assistance System)** | Includes automatic emergency braking, lane keeping, and other driver assistance functions |
| **AVM (Around View Monitor)** | Surround-view monitoring; stitches a 360° top-down view from four cameras |
| **DVR (Digital Video Recorder)** | Dash camera / drive recorder |
| **ISO 26262** | International automotive functional safety standard; defines ASIL safety integrity levels |
| **ASIL (Automotive Safety Integrity Level)** | Automotive safety integrity level, A through D in increasing order |
| **Global Shutter** | All pixels exposed simultaneously; eliminates the Jello Effect caused by motion |
| **Jello Effect** | Image distortion caused by Rolling Shutter sensors during rapid motion |
| **DCG (Dual Conversion Gain)** | Sensor switches conversion gain to extend dynamic range |
| **PLS (Parasitic Light Sensitivity)** | Incomplete shielding of the storage node in a Global Shutter sensor from ambient light |
| **IPM (Inverse Perspective Mapping)** | Converts a camera's perspective view into a ground-plane top-down view |
| **SVM (Surround View Module)** | Surround-view generation module; responsible for multi-camera image stitching |
| **FPN (Fixed Pattern Noise)** | Noise caused by pixel response non-uniformity |
| **DSNU (Dark Signal Non-Uniformity)** | Non-uniformity of dark current across pixels |
| **PRNU (Photo Response Non-Uniformity)** | Non-uniformity of pixel response to light |
| **CRF (Camera Response Function)** | Maps scene radiance to digital values |
| **TDI (Time Delay Integration)** | Line scan sensor mode that accumulates signals from multiple rows to improve SNR |
| **ECC (Error Correcting Code)** | Protects memory data from single-event upsets |
| **BIST (Built-In Self Test)** | Hardware self-diagnosis on power-up |
| **QE (Quantum Efficiency)** | Pixel efficiency for converting photons to electrons |
| **SEU (Single Event Upset)** | Memory bit flip caused by high-energy particle impact |
