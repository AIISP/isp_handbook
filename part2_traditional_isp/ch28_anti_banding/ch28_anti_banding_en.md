# Part 2, Chapter 28: Anti-Banding and Fluorescent Flicker Suppression

> **Scope:** This chapter covers the complete anti-flicker algorithm for cameras — from 50 Hz/60 Hz frequency detection of fluorescent light sources and exposure-time quantization constraints, to row-by-row luminance ripple suppression under Rolling Shutter video capture.
> **Prerequisites:** Volume 1, Chapter 3 (Sensor Physics); Volume 4, Chapter 2 (Auto Exposure)
> **Target readers:** Algorithm engineers, 3A engineers

---

## Table of Contents

1. [Flicker Physical Model](#1-flicker-physical-model)
2. [Flicker Frequency Detection Algorithms](#2-flicker-frequency-detection-algorithms)
3. [Anti-Flicker Exposure Constraints and AE Integration](#3-anti-flicker-exposure-constraints-and-ae-integration)
4. [Rolling Shutter Flicker Suppression in Video](#4-rolling-shutter-flicker-suppression-in-video)
5. [Anti-Flicker Tuning Guide](#5-anti-flicker-tuning-guide)
6. [Common Flicker Artifact Analysis](#6-common-flicker-artifact-analysis)
7. [Evaluation Methods](#7-evaluation-methods)
8. [Code Example](#8-code-example)
9. [References](#references)
10. [Glossary](#glossary)

---

## 1 Flicker Physical Model

### 1.1 AC Power Supply and Light-Source Luminance Fluctuation

Indoor artificial light sources (fluorescent lamps, HID gas-discharge lamps, and some PWM-dimmed LEDs) exhibit periodic luminance fluctuations over time. The root cause is alternating-current (AC, 交流电) power supply. For standard mains electricity:

- **China / Europe mains:** 50 Hz, one electrical cycle = 20 ms
- **North America / Japan mains:** 60 Hz, one electrical cycle ≈ 16.67 ms

A fluorescent lamp (荧光灯) produces light by exciting phosphor via gas discharge; discharge occurs once per half electrical cycle (once per positive half-wave and once per negative half-wave), so the luminance fluctuation frequency is **twice** the mains frequency:

$$L(t) = L_0 + L_1 \cdot \cos(2\pi \cdot 2f_{\text{AC}} \cdot t + \phi)$$

where:
- $L_0$: mean luminance (DC component)
- $L_1$: fluctuation amplitude (AC component), depends on light-source type
- $f_{\text{AC}}$: mains frequency (50 Hz or 60 Hz)
- $2f_{\text{AC}}$: luminance fluctuation frequency (**100 Hz or 120 Hz**)
- $\phi$: initial phase, determined by the current switch state of the light source

The modulation depth of a typical fluorescent lamp, $M = L_1 / L_0$, can be as high as 0.5–1.0 (i.e., luminance oscillates between 0 % and 200 %); modern electronic-ballast fluorescent lamps have lower modulation depth, around 0.05–0.2; LED PWM dimming at low brightness levels can produce near-square-wave fluctuations with extremely high modulation depth.

### 1.2 CMOS Sensor Integration Sampling and Flicker

Each row of pixels in a CMOS image sensor (图像传感器) integrates the optical signal over the exposure time $T_{\text{exp}}$:

$$\text{Signal}(t_{\text{start}}) = \int_{t_{\text{start}}}^{t_{\text{start}} + T_{\text{exp}}} L(t) \, dt$$

For a sinusoidal light source, the integration result is:

$$\text{Signal} = L_0 \cdot T_{\text{exp}} + L_1 \cdot \frac{\sin(\pi \cdot 2f_{\text{AC}} \cdot T_{\text{exp}})}{\pi \cdot 2f_{\text{AC}}} \cdot \cos(2\pi \cdot 2f_{\text{AC}} \cdot t_{\text{mid}})$$

where $t_{\text{mid}}$ is the center instant of the current exposure. Key conclusions:

1. **When $T_{\text{exp}}$ is an integer multiple of the light-source fluctuation period**, the sinusoidal component integrates to zero and flicker disappears:
   $$T_{\text{exp}} = n \cdot \frac{1}{2f_{\text{AC}}}, \quad n = 1, 2, 3, \ldots$$
   Corresponding exposure times are 1/100 s, 1/50 s, 1/33.3 s (50 Hz mains) or 1/120 s, 1/60 s, 1/40 s (60 Hz mains).

2. **When $T_{\text{exp}}$ is not an integer multiple**, the residual sinusoidal component depends on $t_{\text{mid}}$. Different frames (different phases) yield different integration results, producing frame-to-frame luminance jumps — i.e., **flicker**.

### 1.3 Rolling Shutter and the Spatial Distribution of Flicker

The Rolling Shutter (卷帘快门) mechanism of CMOS sensors causes each row to begin its exposure at a different instant; adjacent rows have a fixed row-period delay $\Delta t_{\text{row}}$ (typically a few microseconds to tens of microseconds).

Let the exposure center instant of row $r$ be:

$$t_{\text{mid}}(r) = t_0 + r \cdot \Delta t_{\text{row}}$$

Then the sampled signal of row $r$ contains a phase component that varies with row index:

$$\text{Signal}(r) \propto L_0 + L_1' \cdot \cos(2\pi \cdot 2f_{\text{AC}} \cdot (t_0 + r \cdot \Delta t_{\text{row}}))$$

This forms light and dark horizontal bands along the row (vertical) direction in image space. The number of bands is approximately:

$$N_{\text{bands}} = \frac{2f_{\text{AC}}}{f_{\text{frame}}}$$

For example: a 100 Hz light source at 30 fps yields roughly 3.3 complete light/dark cycles per frame. When frame rate approaches 100 fps, the band count approaches 1, manifesting as whole-frame luminance alternation between frames (inter-frame flicker).

### 1.4 LED PWM Dimming Flicker Characteristics

LED dimming typically uses Pulse Width Modulation (PWM, 脉冲宽度调制), producing a near-square-wave optical output containing a fundamental frequency and multiple harmonics. PWM frequencies range from a few hundred Hz to tens of kHz:

- **Low-frequency PWM (< 200 Hz):** produces horizontal bands in CMOS images similar to fluorescent lamps
- **High-frequency PWM (> 1000 Hz):** a single row's integration time usually spans multiple PWM cycles, smoothing out the bands; bands may still be visible in extremely short exposures (high-speed photography)
- **Non-integer-multiple relationship:** when the PWM frequency is not an integer multiple of the row frequency, bright bands appear at random positions

### 1.5 Global Shutter vs. Rolling Shutter: Flicker Differences

Compared with Rolling Shutter, a Global Shutter (全局快门) sensor exposes all pixels simultaneously; $t_{\text{mid}}$ is identical for every row, so:
- No spatial bands (no horizontal flicker stripes)
- Only inter-frame luminance jumps (temporal flicker)
- Anti-flicker strategy reduces to a pure exposure-time constraint; no row-by-row gain compensation is required

---

## 2 Flicker Frequency Detection Algorithms

### 2.1 Overall Detection Framework

The goal of automatic flicker frequency detection (50 Hz / 60 Hz) is to infer the light-source type from an image sequence without relying on external input. The mainstream approach is **row-mean luminance statistics + temporal FFT**:

```
Image sequence input
    ↓
Extract center ROI (Region of Interest) for each frame
    ↓
Compute per-row mean luminance of ROI → row-luminance vector Y[row] (single-frame spatial analysis)
    ↓  or
Time series of row means at a fixed position across multiple frames Y[frame] (temporal analysis)
    ↓
FFT spectral analysis → 100 Hz / 120 Hz peak detection
    ↓
Confidence calculation → Decision: 50 Hz / 60 Hz / Unknown
```

### 2.2 Single-Frame Spatial Frequency Detection

**Principle:** Exploit the Rolling Shutter effect — there is a known mapping between the spatial frequency of horizontal bands in a single frame and the temporal frequency of the light source.

Steps:
1. Select a central rectangular ROI (recommended: avoid scene regions with high-frequency textures)
2. Compute the mean row luminance (Mean Row Luminance) for each row of the ROI, yielding vector $Y \in \mathbb{R}^H$
3. Compute the DFT of $Y$ to obtain spectrum $\hat{Y}(k)$
4. The expected spatial period (band spacing) is:
   $$P_{\text{pixel}} = \frac{f_{\text{frame}}}{2f_{\text{AC}}} \cdot H_{\text{total}}$$
   where $H_{\text{total}}$ is the total number of sensor rows (including blanking rows)
5. Detect peaks corresponding to 50 Hz and 60 Hz in the DFT spectrum and compare peak energies

**Notes:**
- Scene content with horizontal patterns (blinds, grid fabric) can interfere with detection; use multiple ROIs for cross-validation
- Detection accuracy is better in static scenes than in scenes with motion
- It is recommended to detect both the fundamental frequency and the second harmonic to improve robustness

### 2.3 Multi-Frame Temporal Frequency Detection

**Principle:** Apply FFT analysis to the time series of pixel or row-mean luminance at a fixed position across a sequence of frames.

Steps:
1. Collect row-mean values from the same ROI across $N$ consecutive frames (typical: 32–64)
2. Build time series $Y[n]$, $n = 0, 1, \ldots, N-1$, with sampling rate = frame rate $f_{\text{fps}}$
3. Compute the FFT of $Y[n]$; frequency resolution is $\Delta f = f_{\text{fps}} / N$
4. Detect peaks near 100 Hz and 120 Hz

**Practical alternative:** For standard 30 fps / 60 fps video, 100 Hz / 120 Hz exceeds the Nyquist frequency. Use the **differential frame luminance variance** method:
- The variance of the inter-frame luminance difference increases significantly when flicker is present
- Determine frequency by examining the periodicity of the differential variance (peaks every 100 ms or 83 ms)

### 2.4 Confidence Calculation and Adaptive Decision

Let the spectral peak at 50 Hz be $P_{50}$, at 60 Hz be $P_{60}$, and the background noise floor be $P_{\text{noise}}$:

$$\text{Conf}_{50} = \frac{P_{50} - P_{\text{noise}}}{P_{\text{noise}} + \epsilon}, \quad \text{Conf}_{60} = \frac{P_{60} - P_{\text{noise}}}{P_{\text{noise}} + \epsilon}$$

Decision rules:
- $\text{Conf}_{50} > \text{Th}_{\text{high}}$ and $\text{Conf}_{50} > \text{Conf}_{60}$: decide 50 Hz, enable 100 Hz constraint
- $\text{Conf}_{60} > \text{Th}_{\text{high}}$ and $\text{Conf}_{60} > \text{Conf}_{50}$: decide 60 Hz, enable 120 Hz constraint
- Both $< \text{Th}_{\text{low}}$: natural light, no constraint (flicker-free mode)
- Both $> \text{Th}_{\text{low}}$: retain the previous frame's decision (hysteresis to prevent oscillation)

Typical thresholds: $\text{Th}_{\text{high}} = 3.0$, $\text{Th}_{\text{low}} = 1.5$.

### 2.5 Hardware-Assisted Detection

Some ISP SoCs (System on Chip) provide a dedicated flicker-detection hardware module that reads sensor-output statistics (row-mean histograms) and performs FFT computation in hardware, reducing CPU/ISP firmware load. Such hardware is typically implemented as an independent statistics path that does not occupy main image-path bandwidth.

---

## 3 Anti-Flicker Exposure Constraints and AE Integration

### 3.1 Exposure Time Quantization Principle

The core of anti-flicker is constraining the exposure time to integer multiples of the light-source fluctuation period. Define the **anti-banding exposure step**:

$$T_{\text{step}} = \frac{1}{2f_{\text{AC}}}$$

- 50 Hz mains: $T_{\text{step}} = 1/100 \text{ s} = 10 \text{ ms}$
- 60 Hz mains: $T_{\text{step}} = 1/120 \text{ s} \approx 8.33 \text{ ms}$

The allowed exposure time set is $\{T_{\text{step}}, 2T_{\text{step}}, 3T_{\text{step}}, \ldots\}$, i.e., $\{10\text{ ms}, 20\text{ ms}, 30\text{ ms}, \ldots\}$ (50 Hz).

**AE exposure quantization algorithm:** After Auto Exposure (AE, 自动曝光) computes target exposure $T_{\text{target}}$, quantize to the nearest allowed step:

$$T_{\text{quantized}} = \text{round}\left(\frac{T_{\text{target}}}{T_{\text{step}}}\right) \times T_{\text{step}}$$

Note: the quantized exposure time may deviate from the target; AE must compensate the brightness difference by adjusting analog gain:

$$G_{\text{comp}} = \frac{T_{\text{target}}}{T_{\text{quantized}}}$$

### 3.2 AE Step-Size Constraints

Traditional AE can adjust exposure time continuously; enabling anti-flicker requires switching to **discrete-step** mode:

1. **Step convergence:** each AE adjustment can only move within the quantized step set; non-allowed values cannot be used
2. **Step priority:** in aperture-priority (Av) or shutter-priority (Tv) mode, the anti-flicker step constraint may conflict with user settings; the anti-flicker constraint is typically lower priority than manual user settings
3. **Gain compensation:** quantization error in exposure is compensated in real time via digital gain, but gain compensation introduces noise amplification

### 3.3 Extreme Exposure Handling

**Very short exposure ($T_{\text{exp}} < T_{\text{step}}$):**

When the scene is extremely bright (strong light, direct sunlight), the AE target exposure is $< 1/100$ s (50 Hz) and the anti-flicker constraint cannot be enforced. In this case:
- The exposure time is typically allowed to fall below the anti-flicker step (entering the "flicker-free range")
- Because the fluctuation integral is approximately linear over very short exposure times, flicker visibility is relatively low (perceived contrast decreases in high-brightness scenes)
- Some ISP implementations choose to disable the anti-flicker constraint at this boundary condition

**Very long exposure (night-scene long exposure):**
- The anti-flicker step constraint still applies: use the maximum allowed value of $nT_{\text{step}}$
- In Auto ISO mode, first extend the exposure time to the maximum anti-flicker-allowed value, then increase ISO

### 3.4 Anti-Flicker in Video Mode

Video mode typically has a fixed frame rate (30 fps / 60 fps); the upper limit on exposure time is determined by the frame period:

- 30 fps video: maximum exposure ≈ 1/30 s; 50 Hz mode allows exposure times {1/100 s, 1/50 s}
- 60 fps video: maximum exposure ≈ 1/60 s; 50 Hz mode allows {1/100 s}

Note: 1/60 s is not an integer multiple of 1/100 s, so for 60 fps + 50 Hz mains there is a theoretically unresolvable flicker region. In this case, 1/100 s (1 complete cycle) is the best compromise.

---

## 4 Rolling Shutter Flicker Suppression in Video

### 4.1 Row-wise Luminance Deviation Estimation

Even with exposure-time quantization, residual horizontal bands may remain in video frames due to AE quantization errors and sensor row-readout timing. Row-wise luminance deviation (逐行亮度偏差) estimation:

1. Compute per-row mean luminance $\bar{Y}(r)$ for the current frame, $r = 0, \ldots, H-1$
2. Apply a low-pass filter to $\bar{Y}(r)$ to obtain the scene-trend component $\bar{Y}_{\text{smooth}}(r)$ (use a large-kernel mean or Gaussian filter; kernel size should be at least 2× the band spacing)
3. Compute the row deviation: $\delta(r) = \bar{Y}(r) / \bar{Y}_{\text{smooth}}(r)$
4. If $\delta(r)$ has a significant spectral peak at the expected flicker frequency, residual flicker is present

### 4.2 Row Gain Table

Apply gain correction to each row:

$$Y_{\text{corrected}}(r, c) = Y_{\text{raw}}(r, c) \cdot \frac{1}{\delta(r)}$$

Gain compensation constraints:
- Gain range limit: $[0.5, 2.0]$ to prevent extreme compensation
- Compensation is only enabled when clear flicker is detected; avoid miscorrecting scene luminance gradients under natural light
- Smoothness constraint: gain change between adjacent rows must not exceed $\pm 5\%$ to avoid gain jumps that create new bands

### 4.3 Interaction with Temporal Noise Reduction (TNR)

Temporal Noise Reduction (TNR, 时域降噪) achieves denoising via inter-frame motion estimation and blending. Flicker row-gain compensation and TNR have an ordering dependency:

**Flicker compensation must be performed before TNR:**

Reason: if flicker luminance fluctuations (10 %–30 % inter-frame luminance difference) are misidentified by TNR's frame-difference detector as motion, TNR will suppress temporal blending (no blending = degraded single-frame denoising). If flicker compensation is applied first, adjacent frames have consistent luminance and TNR can work normally.

Recommended ISP pipeline order:
```
RAW → BLC → DPC → LSC → Flicker Row-Gain Compensation
    → Demosaic → WB → CCM → TNR → Sharpening → Output
```

### 4.4 Phase-Locking Assistance Method

High-end ISPs can use phase-detection methods to lock the sensor row-readout phase to the light-source phase (Phase Locking), fixing the start instant of each frame's exposure to a fixed phase point on the light-source waveform, thereby theoretically eliminating intra-frame spatial bands entirely. This method requires real-time light-source phase measurement, is complex to implement, and is mainly found in broadcast-grade cameras.

---

## 5 Anti-Flicker Tuning Guide

### 5.1 Frequency Detection Sensitivity

| Parameter | Recommended Range | Notes |
|-----------|-------------------|-------|
| FFT ROI size | Central 1/4 of frame | Avoid moving objects near scene edges |
| FFT frame count (temporal method) | 32–64 frames | More frames → higher frequency resolution, but larger latency |
| Peak detection threshold $\text{Th}_{\text{high}}$ | 3.0–5.0 | Higher = more conservative, lower false-trigger rate |
| Hysteresis frame count | 10–30 frames | Prevents repeated switching between 50 Hz and 60 Hz |

### 5.2 Exposure Quantization Step Accuracy

The actual mains frequency may deviate from its nominal value by ±0.5 Hz, causing residual error in the anti-flicker quantization step. Use **adaptive step estimation**: exploit the precisely detected peak frequency to dynamically update $T_{\text{step}}$ rather than fixing it at 10 ms / 8.33 ms.

### 5.3 Gain Compensation Strength

| Parameter | Recommended Value | Notes |
|-----------|-------------------|-------|
| Compensation gain ceiling | 1.5× | Prevents noise amplification |
| Compensation activation threshold | Flicker amplitude > 3% | No compensation below this level |
| Low-pass smoothing kernel size | ≥ 2× band spacing | Prevents misidentifying scene gradients as flicker |

### 5.4 Night and Low-Light Scenes

In low-light conditions (SNR < 20 dB), row-mean noise is large and the flicker detection false-positive rate increases. Recommendations:
- Enlarge the spatial ROI (whole-frame average) to improve the SNR of row means
- Reduce the update frequency of the compensation gain (increase the time constant) to reduce noise-driven erroneous compensation
- When ISO exceeds a certain threshold (e.g., ISO 1600), consider disabling row-by-row gain compensation, since noise may be more visible than flicker bands at that point

---

## 6 Common Flicker Artifact Analysis

### 6.1 Static Horizontal Bands

**Symptom:** Fixed-position light/dark horizontal bands in a still scene; band spacing is stable.

**Causes:**
- Anti-flicker not enabled, or frequency detection error (50/60 Hz confusion)
- Insufficient exposure-time precision (sensor row-timing jitter)
- Light-source PWM frequency happens to form an integer-multiple relationship with the frame rate

**Solution:** Verify that frequency detection is correct; check sensor row-timing configuration.

### 6.2 Flickering Frames

**Symptom:** Entire-frame luminance jumps occur every few frames in video; no spatial bands.

**Cause:** A Global Shutter sensor without the anti-flicker exposure constraint enabled, or a Rolling Shutter sensor with long exposure (low band density, so each frame approximates a uniformly alternating bright/dark pattern).

**Solution:** Confirm that the anti-flicker exposure constraint is active in video mode.

### 6.3 Noise Bands Introduced by Gain Compensation

**Symptom:** Random noisy horizontal bands appear after anti-flicker is activated; band spacing is irregular.

**Cause:** Row-gain compensation is too aggressive; row noise is misidentified as flicker and amplified.

**Solution:** Raise the compensation activation threshold, increase the low-pass filter kernel size for row means, and limit the maximum gain compensation.

### 6.4 Unsuppressed LED PWM Flicker

**Symptom:** LED screens and indicator lights show light/dark bands in camera images; band spacing is irregular (because LED PWM frequencies vary widely).

**Cause:** Standard anti-flicker targets only integer multiples of 50/60 Hz; LED PWM frequencies fall outside the detection range.

**Solution:** Extend the detection frequency range (covering 100–20000 Hz), or manually configure the corresponding step for specific light-source types (e.g., screen-capture mode).

### 6.5 Interaction Between Flicker and Motion Blur

High-frequency moving objects (such as rotating fan blades) under flickering illumination may produce "ghost" bands — motion object and background flicker bands superimpose to form complex Moiré (莫尔纹) patterns. Such artifacts typically cannot be eliminated by the standard anti-flicker algorithm; higher frame rates or post-processing are required.

---

## 7 Evaluation Methods

### 7.1 Subjective Flicker Visibility Test

**Standard test method** (reference: IEEE 1789-2015):

1. **Test environment:** Controlled dark room, target light source (fluorescent lamp or PWM-dimmed LED), gray card or white card as the subject
2. **Test sequence:** Record at least 10 seconds of video (30 fps or 60 fps), with no camera motion
3. **Scoring method:** Play video; manual score 0–5 (0 = no flicker, 5 = severe flicker)

### 7.2 Objective Flicker Quantification Metrics

**Vertical Frequency Energy (VFE):**

$$\text{VFE} = \sum_{k \in [f_{\text{flicker}} \pm \Delta f]} |\hat{Y}_{\text{row}}(k)|^2$$

Extract the row-mean series $Y_{\text{row}}$ from a single frame, compute the DFT, and measure the energy at the flicker frequency as an objective flicker-intensity indicator.

**Frame-to-Frame Luminance Variation (FFLV):**

$$\text{FFLV} = \text{std}_{t}\left(\text{mean}_{r,c}(Y_t)\right)$$

Compute the standard deviation of the global mean luminance across video frames, reflecting inter-frame flicker intensity.

### 7.3 Dark-Field Horizontal Band Test

1. Cover the lens and record dark-field video (scattered fluorescent light as the subject scene)
2. Compute the FFT of the row-mean vector and measure the peak SNR at the flicker frequency
3. Pass criterion: peak SNR < 3 dB (i.e., flicker peak does not exceed noise floor by more than 3 dB)

### 7.4 Exposure Step Accuracy Verification

Use an oscilloscope or optical power meter to capture the actual light-source waveform and precisely measure $f_{\text{AC}}$; compare against the ISP anti-flicker step configuration and verify that the $T_{\text{step}}$ error is < ±1 %.

---

## 8 Code Example

```python
"""
Anti-Flicker Algorithm Demo: FFT frequency detection + exposure quantization + row-gain compensation
Dependencies: numpy, scipy, matplotlib
Usage: python ch26_anti_banding_demo.py
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
from scipy.ndimage import uniform_filter1d
from typing import Optional, Tuple


# ─────────────────────────────────────────────
# Part 1: Simulate Rolling Shutter image under fluorescent illumination
# ─────────────────────────────────────────────

def simulate_flicker_image(
    height: int = 480,
    width: int = 640,
    fps: float = 30.0,
    ac_freq: float = 50.0,
    modulation: float = 0.3,
    exp_time_ms: float = 15.0,
    frame_phase: float = 0.0,
    total_rows: int = 520,
) -> np.ndarray:
    """
    Simulate a Rolling Shutter CMOS sensor image under fluorescent illumination.

    Light-source luminance model: L(t) = L0 * (1 + M * cos(2*pi*2*f_AC*t))
    Each row integrates L(t) over [t_start, t_start + T_exp].

    Returns:
        image: (height, width) float32, normalized to [0,1]
    """
    flicker_freq = 2.0 * ac_freq       # Light-source fluctuation frequency (Hz)
    row_period = 1.0 / (fps * total_rows)  # Row period (s)
    exp_time_s = exp_time_ms * 1e-3

    # Base scene: simulate a natural luminance gradient
    base_scene = np.ones((height, width), dtype=np.float32) * 0.5
    ramp = np.linspace(0.4, 0.6, height)[:, np.newaxis]
    base_scene = base_scene * ramp

    image = np.zeros_like(base_scene)
    for r in range(height):
        t_start = frame_phase / (2 * np.pi * flicker_freq) + r * row_period

        # Numerical integration (16-point sampling)
        n_samples = 16
        t_samples = np.linspace(t_start, t_start + exp_time_s, n_samples)
        light = 1.0 + modulation * np.cos(2 * np.pi * flicker_freq * t_samples)
        gain = np.mean(light)

        image[r, :] = base_scene[r, :] * gain

    return np.clip(image, 0, 1).astype(np.float32)


# ─────────────────────────────────────────────
# Part 2: Per-row luminance extraction + FFT frequency detection
# ─────────────────────────────────────────────

def detect_flicker_frequency(
    image: np.ndarray,
    fps: float,
    total_rows: int = 520,
    roi_ratio: float = 0.5,
) -> Tuple[Optional[float], float, float]:
    """
    Detect flicker frequency (50 Hz / 60 Hz) from a single frame.

    Returns:
        (detected_ac_freq, conf_50, conf_60)
        detected_ac_freq: 50.0 / 60.0 / None
        conf_50, conf_60: confidence (SNR ratio)
    """
    H, W = image.shape

    # Extract center ROI
    h_start = int(H * (1 - roi_ratio) / 2)
    h_end = int(H * (1 + roi_ratio) / 2)
    roi = image[h_start:h_end, :]
    row_means = roi.mean(axis=1)

    # Detrend (remove scene luminance gradient)
    x = np.arange(len(row_means), dtype=np.float64)
    coeffs = np.polyfit(x, row_means, 1)
    trend = np.polyval(coeffs, x)
    row_means_dt = row_means - trend

    # FFT (apply Hanning window to reduce spectral leakage)
    N = len(row_means_dt)
    window = np.hanning(N)
    fft_mag = np.abs(fft(row_means_dt * window))[:N // 2]

    # Map row spatial frequency → temporal frequency
    row_period_s = 1.0 / (fps * total_rows)
    freq_axis_spatial = np.arange(N // 2) / N        # cycles/row
    freq_axis_temporal = freq_axis_spatial / row_period_s  # Hz

    # Detect peaks within ±8 Hz windows around 100 Hz and 120 Hz
    def peak_in_band(center_hz: float, bw_hz: float = 8.0) -> float:
        mask = np.abs(freq_axis_temporal - center_hz) < bw_hz / 2
        return float(fft_mag[mask].max()) if mask.sum() > 0 else 0.0

    noise_floor = float(np.median(fft_mag)) + 1e-9
    p_100 = peak_in_band(100.0)
    p_120 = peak_in_band(120.0)
    conf_50 = (p_100 - noise_floor) / noise_floor
    conf_60 = (p_120 - noise_floor) / noise_floor

    th_high = 3.0
    if conf_50 > th_high and conf_50 >= conf_60:
        detected = 50.0
    elif conf_60 > th_high and conf_60 > conf_50:
        detected = 60.0
    else:
        detected = None

    return detected, conf_50, conf_60


# ─────────────────────────────────────────────
# Part 3: Anti-flicker exposure time quantization
# ─────────────────────────────────────────────

def quantize_exposure_antibanding(
    target_exp_ms: float,
    ac_freq: float = 50.0,
    min_exp_ms: float = 0.1,
    max_exp_ms: float = 33.3,
) -> Tuple[float, float]:
    """
    Quantize target exposure time to an integer multiple of the anti-flicker step.

    Step = 1000 / (2 * f_AC) ms
      50 Hz → 10.0 ms
      60 Hz →  8.33 ms

    Returns:
        (quantized_exp_ms, gain_compensation)
    """
    step_ms = 1000.0 / (2.0 * ac_freq)
    n = max(1, round(target_exp_ms / step_ms))
    quantized_ms = float(np.clip(n * step_ms, min_exp_ms, max_exp_ms))
    gain_comp = target_exp_ms / quantized_ms
    return quantized_ms, gain_comp


# ─────────────────────────────────────────────
# Part 4: Row-gain compensation
# ─────────────────────────────────────────────

def apply_row_gain_correction(
    image: np.ndarray,
    flicker_freq_hz: float = 100.0,
    fps: float = 30.0,
    total_rows: int = 520,
    gain_limit: float = 1.5,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Estimate and apply row-gain compensation to suppress residual flicker bands.

    Returns:
        corrected: gain-compensated image
        row_gains: (H,) per-row gain values
    """
    H, W = image.shape
    row_means = image.mean(axis=1)

    # Low-pass filter to extract scene trend (kernel size = 3× band spacing)
    stripe_period_rows = fps * total_rows / flicker_freq_hz
    kernel_size = int(stripe_period_rows * 3)
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel_size = max(kernel_size, 7)

    row_smooth = uniform_filter1d(row_means, size=kernel_size, mode='reflect')
    ratio = row_means / (row_smooth + 1e-9)

    # Compensation gain = 1/deviation ratio, clipped
    row_gains = np.clip(1.0 / ratio, 1.0 / gain_limit, gain_limit)
    # Smooth gain table to prevent jumps
    row_gains = uniform_filter1d(row_gains, size=3, mode='reflect')

    corrected = np.clip(image * row_gains[:, np.newaxis], 0, 1).astype(np.float32)
    return corrected, row_gains


# ─────────────────────────────────────────────
# Part 5: Comprehensive demo + evaluation
# ─────────────────────────────────────────────

def compute_vfe(img: np.ndarray, fps=30.0, total_rows=520,
                center_hz=100.0, bw_hz=10.0) -> float:
    """Compute Vertical Frequency Energy (VFE)"""
    row_means = img.mean(axis=1)
    N = len(row_means)
    fft_mag = np.abs(fft(row_means * np.hanning(N)))[:N // 2]
    row_period_s = 1.0 / (fps * total_rows)
    freq_axis = np.arange(N // 2) / N / row_period_s
    mask = np.abs(freq_axis - center_hz) < bw_hz / 2
    return float(fft_mag[mask].sum()) if mask.sum() > 0 else 0.0


def run_demo():
    print("=" * 60)
    print("Anti-Flicker Algorithm Demo  (ch26_anti_banding)")
    print("=" * 60)

    # 1. Generate simulated images
    print("\n[1] Generating simulated images...")
    img_flickering = simulate_flicker_image(
        height=480, width=640, fps=30.0,
        ac_freq=50.0, modulation=0.3,
        exp_time_ms=15.0,   # Not an integer multiple of anti-flicker step
        frame_phase=0.7,
    )
    img_ideal = simulate_flicker_image(
        height=480, width=640, fps=30.0,
        ac_freq=50.0, modulation=0.3,
        exp_time_ms=10.0,   # 1/100s = integer multiple of anti-flicker step
        frame_phase=0.7,
    )

    # 2. Frequency detection
    print("\n[2] Flicker frequency detection...")
    freq, c50, c60 = detect_flicker_frequency(
        img_flickering, fps=30.0, total_rows=520, roi_ratio=0.6
    )
    print(f"    Detection result: AC freq={freq}Hz  conf_50={c50:.2f}  conf_60={c60:.2f}")

    # 3. Exposure quantization table
    print("\n[3] Exposure quantization demo (50 Hz mains):")
    print(f"    {'Target(ms)':>10} {'Quantized(ms)':>13} {'Gain Comp':>10}")
    print("    " + "-" * 37)
    for t in [7.5, 12.0, 15.0, 18.0, 25.0, 33.0]:
        q, g = quantize_exposure_antibanding(t, ac_freq=50.0)
        print(f"    {t:>10.1f} {q:>13.1f} {g:>10.3f}")

    # 4. Row-gain compensation
    print("\n[4] Row-gain compensation...")
    corrected, row_gains = apply_row_gain_correction(
        img_flickering, flicker_freq_hz=100.0, fps=30.0, total_rows=520
    )

    # 5. Evaluation metrics
    print("\n[5] Flicker evaluation metrics (VFE @ 100 Hz):")
    vfe_before = compute_vfe(img_flickering)
    vfe_after  = compute_vfe(corrected)
    vfe_ideal  = compute_vfe(img_ideal)
    print(f"    Flickering image VFE :  {vfe_before:.4f}")
    print(f"    After gain comp  VFE :  {vfe_after:.4f}")
    print(f"    Ideal (no flicker) VFE: {vfe_ideal:.4f}")
    if vfe_before > 1e-9:
        db = 20 * np.log10(max(vfe_after, 1e-9) / vfe_before)
        print(f"    Flicker suppression  :  {db:.1f} dB")

    # 6. Visualization
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))

    for ax, img, title in zip(
        axes[0],
        [img_flickering, corrected, img_ideal],
        ['With Flicker (exp=15ms)', 'After Row-Gain Comp', 'Ideal (exp=10ms)']
    ):
        ax.imshow(img, cmap='gray', vmin=0, vmax=1)
        ax.set_title(title)
        ax.axis('off')

    axes[1, 0].plot(img_flickering.mean(axis=1))
    axes[1, 0].set_title('Row Means - With Flicker')
    axes[1, 0].set_xlabel('Row index')

    axes[1, 1].plot(row_gains)
    axes[1, 1].axhline(1.0, color='r', linestyle='--', label='Baseline=1')
    axes[1, 1].set_title('Per-Row Compensation Gain Table')
    axes[1, 1].set_xlabel('Row index')
    axes[1, 1].legend()

    axes[1, 2].plot(corrected.mean(axis=1), label='After comp', alpha=0.8)
    axes[1, 2].plot(img_ideal.mean(axis=1), '--', label='Ideal', alpha=0.8)
    axes[1, 2].set_title('Row Means Comparison')
    axes[1, 2].set_xlabel('Row index')
    axes[1, 2].legend()

    plt.tight_layout()
    out_path = 'anti_banding_demo.png'
    plt.savefig(out_path, dpi=120)
    plt.close()
    print(f"\nDemo figure saved: {out_path}")
    print("=" * 60)


if __name__ == '__main__':
    run_demo()
```

---

## References

[1] Wilkins, A., Veitch, J., & Lehman, B. "LED lighting flicker and potential health concerns: IEEE standard PAR1789 update." *IEEE Energy Conversion Congress and Exposition (ECCE)*, 2010.
[2] Konnik, M., & Welsh, J. "High-level Numerical Simulations of Noise in CCD and CMOS Photosensors: Review and Tutorial." arXiv:1412.4031, 2014.
[3] IEEE Standard 1789-2015. "IEEE Recommended Practices for Modulating Current in High-Brightness LEDs for Mitigating Health Risks to Viewers." IEEE, 2015.
[4] Baugh, G., Kokaram, A., & Pitié, F. "Advanced video debanding." *European Conference on Visual Media Production (CVMP)*, 2014.
[5] Janesick, J.R. Scientific Charge-Coupled Devices. SPIE Press, 2001. Chapter 5: Noise Sources.
[6] SMIA Specification. "Standard Mobile Imaging Architecture: Sensor Core Specification." MIPI Alliance, 2005.
[7] Nakamura, J. (Ed.) Image Sensors and Signal Processing for Digital Still Cameras. CRC Press, 2006. Chapter 6: Noise Characteristics.
[8] Gu, J., et al. "Coded Rolling Shutter Photography: Flexible Space-Time Sampling." Proceedings of ICCP, 2010.

## Glossary

| Term | Full Form / Explanation |
|------|-------------------------|
| **Flicker** | Periodic luminance fluctuation of a light source over time; manifests as inter-frame flashing or intra-frame horizontal bands in images |
| **Anti-banding** | Anti-flicker / anti-banding; eliminates image bands caused by flicker through exposure-time constraints |
| **AC (Alternating Current)** | Mains frequency 50 Hz (China/Europe) or 60 Hz (North America/Japan) |
| **Rolling Shutter** | CMOS sensor row-sequential exposure mechanism; different rows have different exposure start times |
| **Global Shutter** | All pixels exposed simultaneously; no Rolling Shutter banding problem |
| **PWM (Pulse Width Modulation)** | Common LED dimming method; produces high-frequency luminance fluctuations |
| **FFT (Fast Fourier Transform)** | Used to extract frequency components from a signal |
| **Modulation Depth** | Light-source luminance fluctuation depth $M = L_1/L_0$; higher value = more visible flicker |
| **Row Gain Table** | Per-row gain compensation table; applies different gains per row to eliminate row-to-row luminance differences |
| **TNR (Temporal Noise Reduction)** | Uses inter-frame information to reduce noise; has an ordering dependency with flicker compensation |
| **VFE (Vertical Frequency Energy)** | Vertical frequency component energy; objective metric for horizontal bands (flicker) in an image |
| **ROI (Region of Interest)** | Image sub-region selected for flicker detection |
| **AE (Auto Exposure)** | Controls exposure time and gain to achieve target image brightness |
| **Moiré** | Pattern formed by the beat frequency of two overlapping periodic signals |
| **FFLV (Frame-to-Frame Luminance Variation)** | Standard deviation of per-frame global mean luminance; reflects inter-frame flicker intensity |
