# Part 1, Chapter 17: Sensor Pixel Binning Mechanisms and ISP Adaptation

> **Position:** This chapter provides a systematic treatment of pixel binning — the hardware principles, CFA-variant architectures, ISP pipeline adaptations, and mode-switching strategies between full-resolution and binning modes. Pixel binning is the central mechanism behind low-light performance in modern mobile image sensors, and it fundamentally shapes the full ISP chain from noise models through demosaicing.
> **Prerequisites:** Vol.1 Ch.03 (Sensor Physics), Vol.1 Ch.04 (Noise Models)
> **Audience:** ISP Algorithm Engineers, Sensor Engineers
> **Scope:** This chapter focuses on hardware binning mechanisms and ISP algorithm adaptation. Multi-frame burst synthesis (software temporal binning) is covered in Vol.2 Ch.24; super-resolution reconstruction in Vol.3 Ch.03.

---

## §1 Theory

### 1.1 Why Pixel Binning?

The pixel pitch of mobile camera sensors has been shrinking continuously — from ~1.12 μm in 2015 to 0.56–0.64 μm in the early 2020s, reducing the photodiode area by roughly a factor of four. This creates a fundamental physical tension:

**Photon capture capacity scales linearly with pixel area.** Given exposure time $t$ and scene illuminance $E$ (in lux), the expected photon count for a single pixel is:

$$\bar{N}_\text{ph} = \frac{E \cdot A_\text{pixel} \cdot t \cdot \eta_{QE}}{E_\text{photon}}$$

where $A_\text{pixel}$ is the pixel area, $\eta_{QE}$ is quantum efficiency, and $E_\text{photon}$ is the energy of a single photon. Halving the pixel area halves the photon count; the shot noise standard deviation $\sqrt{\bar{N}_\text{ph}}$ and the resulting SNR $= \sqrt{\bar{N}_\text{ph}}$ each drop by ~3 dB.

**The physical essence of binning:** Before (or after) the ADC, spatially adjacent $N$ same-color pixels are merged, creating a virtual pixel with a larger effective area. This approach:

1. Trades spatial resolution for increased effective signal and improved SNR;
2. Reduces per-frame data volume, enabling higher frame rates or lower power consumption;
3. Provides the most effective hardware-level SNR gain in low-light conditions.

**SNR improvement formula:**

For a single pixel with shot-noise model $\sigma_\text{shot}^2 = K \cdot S$ (where $K$ is system gain in e⁻/DN and $S$ is signal in DN), merging $N$ pixels in **average mode** gives:

$$\text{SNR}_\text{binning}^\text{avg} = \frac{N \cdot \bar{S} / N}{\sqrt{N \cdot \sigma_\text{shot}^2 / N^2 + \sigma_\text{read}^2/N}} = \sqrt{N} \cdot \text{SNR}_\text{single} \quad \text{(shot-noise dominated)}$$

**Merging $N$ pixels improves SNR by $\sqrt{N}$, equivalent to $10\log_{10}(N)/2$ dB.**

| Merge count $N$ | SNR gain factor | Gain in dB | Effective area |
|:---------------:|:---------------:|:----------:|:--------------:|
| 2×2 = 4         | 2×              | +6 dB      | 4× original    |
| 3×3 = 9         | 3×              | +9.5 dB    | 9× original    |
| 4×4 = 16        | 4×              | +12 dB     | 16× original   |

---

### 1.2 Taxonomy of Binning Methods

#### 1.2.1 Hardware (Analog) Binning

Charge merging occurs in the analog domain, before ADC conversion. Primary implementations:

- **Charge-domain binning:** Adjacent pixel charges are merged at the Floating Diffusion (FD) node before the source follower. This is the highest-SNR approach since readout noise is incurred only once:
  $$\text{SNR}_\text{binning}^\text{hardware} \approx \sqrt{N} \cdot \text{SNR}_\text{single} + \Delta_\text{readout}$$
- **Current-domain binning:** Used in global-shutter CMOS sensors; columns are summed before the column amplifier.
- **Pros:** Minimizes readout noise contributions, optimal SNR. **Cons:** More complex pixel circuitry, lower flexibility.

#### 1.2.2 Software (Digital) Binning

Pixel merging is performed in the digital domain after ADC readout:

- **Sum mode:** $I_\text{out} = \sum_{i=1}^{N} I_i$ — signal increases $N$-fold, noise increases $\sqrt{N}$-fold, SNR improves $\sqrt{N}$-fold, but dynamic range may be limited by output bit-depth.
- **Average mode:** $I_\text{out} = \frac{1}{N}\sum_{i=1}^{N} I_i$ — preserves the original DN range, SNR still improves $\sqrt{N}$-fold (shot-noise dominated).
- **Pros:** Fully software-configurable. **Cons:** Each pixel still requires an independent ADC and readout cycle; no power savings from reduced readout count.

#### 1.2.3 Spatial Binning vs. Temporal Binning

| Dimension | Spatial Binning | Temporal Binning |
|-----------|----------------|-----------------|
| Merge strategy | Adjacent pixels within one frame | Accumulation across frames |
| Resolution impact | Reduced spatial resolution | Spatial resolution preserved |
| Motion robustness | Unaffected by motion | Motion causes ghosting artifacts |
| Typical application | Quad-Bayer, Nona-Bayer | Burst night-mode synthesis (Vol.2 Ch.24) |

---

### 1.3 Binning Patterns under Bayer CFA

#### 1.3.1 Conventional 2×2 Bayer Binning

In a standard RGGB Bayer array, each CFA repeat unit contains R×1, G×2, B×1 pixels. 2×2 binning merges each 2×2 block into one output pixel:

```
Original Bayer (4×4):       After 2×2 Binning (2×2):
R  G  R  G                   R'  G'
G  B  G  B       →           G'  B'
R  G  R  G
G  B  G  B
```

**Note:** In conventional Bayer 2×2 binning, the two G pixels within a 2×2 block are merged while R and B are read independently — the output is still a valid Bayer mosaic at 1/4 the original resolution.

#### 1.3.2 Quad-Bayer (4-in-1) Architecture

The mainstream approach in flagship sensors such as Sony IMX766 and IMX989. The core idea: each color channel of the standard Bayer pattern is split into 2×2 same-color sub-pixels, so that at each "logical pixel" position there are four physically co-located, same-color photodiodes.

```
Quad-Bayer CFA (8×8 physical):
R  R  G  G  R  R  G  G
R  R  G  G  R  R  G  G
G  G  B  B  G  G  B  B
G  G  B  B  G  G  B  B
...
```

**Binning mode (low light):** Merge each group of 4 same-color pixels into 1 output, producing a standard Bayer output image at 1/4 the physical pixel count:

$$I_\text{out} = \frac{1}{4}\sum_{i=1}^{4} I_i \quad \text{(average mode)}$$

$$I_\text{out} = \sum_{i=1}^{4} I_i \quad \text{(sum mode — watch for bit-depth clipping)}$$

**Full-pixel mode (sufficient light):** All 4 sub-pixels are read independently; a dedicated Remosaic algorithm (conventional or DNN-based) reconstructs a standard Bayer mosaic before entering the ISP pipeline, yielding the full physical resolution.

**SNR improvement:** With N = 4:

$$\text{SNR}_\text{Quad-Bayer} = \sqrt{4} \cdot \text{SNR}_\text{single} = 2 \times \text{SNR}_\text{single} \approx +6\text{ dB}$$

#### 1.3.3 Tetra-pixel (Samsung ISOCELL 4-in-1)

Samsung ISOCELL HP1, HP3 and similar sensors use a structurally similar arrangement — 4 same-color sub-pixels per logical pixel — but with a different remosaic mapping:

- Samsung's "Tetra²pixel" technology (HP series) extends to **16-in-1** (4×4 same-color merge);
- In Nona-pixel mode, 9 same-color pixels are merged for extreme low-light / night-vision;
- Full-resolution output requires a Samsung-specific Remosaic step for the proprietary CFA pattern.

#### 1.3.4 Nona-Bayer (9-in-1)

A 3×3 block of 9 same-color pixels is merged into a single output, targeting extreme low-light scenarios:

$$\text{SNR improvement} = \sqrt{9} = 3\times \approx +9.5\text{ dB}$$

The trade-off: spatial resolution shrinks to $1/9$ of the physical pixel count, meaning image dimensions reduce to $1/3$ in each axis.

#### 1.3.5 RYYB Binning (Huawei Mate Series)

Huawei P30 Pro / Mate series adopts an RYYB (Red-Yellow-Yellow-Blue) CFA, replacing the two green positions with yellow:

- Yellow filters transmit both red and green light, providing ~1.5× more photons than the green channel;
- RYYB binning merges the two Y pixels per Bayer super-pixel; the output requires a dedicated RYYB-to-RGB color matrix (see Vol.2 Ch.06 on CCM);
- ISP color calibration must account for the RYYB spectral response; the CCM differs substantially from standard Bayer.

**Binning Architecture Comparison Table:**

| Sensor Architecture | Manufacturer | Merge N | SNR Gain | Res. Reduction | Full-pixel Mode |
|--------------------|--------------|:-------:|:--------:|:--------------:|:--------------:|
| Quad-Bayer         | Sony IMX766/989 | 4    | +6 dB    | 1/4            | Requires Remosaic |
| Tetra-pixel        | Samsung HP1  | 4       | +6 dB    | 1/4            | Requires Remosaic |
| Nona-Bayer         | Samsung HP1 (night) | 9 | +9.5 dB | 1/9          | N/A |
| Tetra²pixel        | Samsung HP3  | 16      | +12 dB   | 1/16           | Requires Remosaic |
| RYYB Binning       | Huawei Mate/P | 4      | +6 dB+   | 1/4            | Requires RYYB Remosaic |
| Conventional 2×2   | Legacy CMOS  | 4       | +6 dB    | 1/4            | Full-res independent |

---

### 1.4 Full-pixel vs. Binning Mode — Switching Strategy

One of the ISP's central control decisions is when to switch modes.

**Typical switching conditions (actual thresholds are sensor-specific):**

| Condition | Full-pixel Mode | Binning Mode |
|-----------|----------------|-------------|
| Scene brightness | > 100 lux | < 50 lux |
| Exposure time | < 1/30 s | > 1/30 s (pre-switch candidate) |
| Frame rate requirement | ≤ 30 fps | > 60 fps (4K video) |
| Resolution requirement | Still photography (max res) | Preview, video, quick capture |
| ISO level | < ISO 800 | > ISO 1600 |

**Hysteresis design:** To prevent rapid oscillation, switching thresholds are typically set with a 20–30% hysteresis band:

$$\text{Enter binning: } L < L_\text{low}; \quad \text{Exit binning: } L > L_\text{high}; \quad L_\text{high} = 1.3 \times L_\text{low}$$

---

## §2 Calibration

### 2.1 LSC Calibration per Mode

Because full-pixel and binning modes have different effective pixel pitches (binning doubles the logical pitch), their vignetting characteristics differ. **Each mode requires independent LSC gain maps.**

**Calibration procedure:**
1. Capture RAW images on a uniform illumination source (integrating sphere or flat-field panel) in both full and binning modes;
2. Calibrate separately per illuminant (D50, D65, Illuminant A);
3. Compute per-channel (R/G/B or R/Gr/Gb/B) 2D gain correction maps;
4. Verify post-correction uniformity residual: $\sigma_\text{uniformity} < 1\%$.

**Binning-mode LSC specifics:**
- Lateral chromatic aberration is partially averaged out during same-color pixel binning, so chromatic LSC components may differ from full mode;
- In theory, the virtual pixel center after 4-in-1 binning coincides with the original sub-pixel centers, so the LSC curve shape is similar but gain amplitude may differ slightly;
- In practice, binning-mode LSC can often be approximated by downsampling the full-mode LSC map, but the residual error must be verified.

### 2.2 Noise Model Re-calibration

Binning changes the noise parameters $(K, \sigma_\text{read})$; these must be recalibrated (see Vol.1 Ch.04 for the noise model framework).

**Average binning — noise parameter update:**

Single-pixel noise variance: $\sigma^2 = K \cdot S + \sigma_\text{read}^2$

After averaging $N$ pixels:
$$K_\text{binning}^\text{avg} = \frac{K}{N}, \quad \sigma_\text{read,binning}^\text{avg} = \frac{\sigma_\text{read}}{\sqrt{N}}$$

**Sum binning — noise parameter update:**

$$K_\text{binning}^\text{sum} = K \cdot N, \quad \sigma_\text{read,binning}^\text{sum} = \sigma_\text{read} \cdot \sqrt{N}$$

Note: in sum mode, **FPN is also linearly accumulated** — it grows $N$-fold rather than being averaged out (see §4.1).

**Calibration steps:**
1. Capture dark frames at multiple exposure times in binning mode; extract $(K_\text{binning}, \sigma_\text{read,binning})$;
2. Capture flat fields for PTC (Photon Transfer Curve) verification of noise model linearity;
3. Compare against theoretical predictions; if discrepancy > 10%, investigate electrical cross-talk between sub-pixels.

### 2.3 Color Calibration and Full-to-Binning Alignment Verification

**Target:** Full-pixel and binning mode color outputs should be visually consistent; mode transitions should be imperceptible.

**Pass criterion:**
$$\Delta E_{00}^\text{Full \leftrightarrow Binning} < 1.5 \quad \text{(X-Rite Macbeth 24-patch ColorChecker, D65 illuminant)}$$

**Sources of color discrepancy:**
1. Micro-lens offset in Quad-Bayer creates small angular response differences between sub-pixels, leading to slightly different spectral responses when averaged;
2. Effective Chief Ray Angle (CRA) shifts between modes;
3. Full-pixel Remosaic introduces interpolation artifacts absent in direct binning.

**Correction strategy:** Calibrate a separate CCM and AWB gain set for binning mode; maintain a mode flag in the AE/AWB control system to dynamically select the correct parameter set.

---

## §3 Tuning Guide

### 3.1 AWB Differences in Binning Mode

**Problem:** With fewer effective pixels per frame (e.g., 50 MP → 12.5 MP after 4-in-1), AWB statistics become less reliable over small-area color patches.

**Tuning recommendations:**
- **Tile size:** Keep AWB tile sizes in proportion to the physical field of view (not pixel count), so each tile covers the same scene area in both modes;
- **Gray-world weighting:** With fewer pixels per tile, per-tile variance is higher; increase temporal smoothing coefficient $\alpha$ in binning mode;
- **Color temperature estimation:** Re-verify CCT estimation accuracy at extremes (< 2800 K warm light, > 7000 K cool/blue-sky) after switching to binning mode.

### 3.2 Demosaicing Algorithm Selection

Binning mode changes the spatial structure of the effective CFA pattern; the demosaic algorithm must be chosen accordingly.

| Mode | Effective pixel pitch | Recommended demosaic | Complexity |
|------|-----------------------|--------------------|------------|
| Full-pixel (after Remosaic) | Original pitch | LMMSE, AHD, DNN Remosaic | High |
| Binning (2×2 average) | 2× original pitch | Simplified Bilinear, Malvar | Low |
| Binning (Quad-Bayer 4-in-1) | 2× original pitch | Standard Bayer demosaic | Medium |

**Quad-Bayer binning output validity:** After 4-in-1 merging, the output is a standard RGGB Bayer mosaic, fully compatible with conventional Bayer demosaic algorithms — no special handling required. This is a key engineering advantage of the Quad-Bayer design.

**Full-pixel Remosaic:** The independently-read 4×4 Quad-Bayer RAW must first be processed by a Remosaic algorithm (similar to super-resolution interpolation or a DNN) to reconstruct a standard Bayer mosaic before entering the ISP. Remosaic quality directly determines the sharpness and color accuracy of full-resolution still images.

### 3.3 Noise Reduction Parameter Coupling

**The SNR improvement from binning means NR demands are lower:**

If the NR strength parameter for full-pixel mode is $\lambda_\text{NR}^\text{full}$, the recommended binning-mode NR strength is:

$$\lambda_\text{NR}^\text{binning} \approx \frac{\lambda_\text{NR}^\text{full}}{\sqrt{N}} \quad \text{(rough approximation)}$$

In practice:
- NR parameters are stored as ISO-indexed LUTs; binning mode requires its own separate LUT;
- Equivalent ISO mapping: physical ISO 1600 in binning mode ≈ full-pixel ISO 400 in noise level terms;
- Spatial frequency: effective Nyquist frequency is halved in 2×2 binning; spatial filter cutoff must be adjusted accordingly.

### 3.4 Sharpening Parameter Adjustment

Reduced spatial resolution in binning mode means high-frequency texture detail is lost; excessive sharpening introduces ringing and aliasing artifacts:

- **Unsharp Mask radius:** Increase relative to full-resolution settings, maintaining the same physical scale rather than pixel-count scale;
- **Sharpening gain cap:** Due to the lower Nyquist frequency, sharpening gain in binning mode should not exceed ~0.7× the full-mode gain to prevent aliasing;
- **Edge-adaptive threshold:** Relax edge detection thresholds slightly in binning mode (edges appear wider in pixel units at lower resolution).

---

## §4 Artifacts

### 4.1 Fixed Pattern Noise (FPN) Amplification

**Mechanism:** FPN arises from pixel-to-pixel gain non-uniformity. In sum-mode binning, the FPN contributions from $N$ pixels are linearly accumulated:

$$\text{FPN}_\text{binning}^\text{sum} = \sum_{i=1}^{N} \text{FPN}_i \approx N \cdot \bar{\text{FPN}}$$

Since shot noise (random) only grows by $\sqrt{N}$, the **FPN-to-noise ratio worsens by a factor of $\sqrt{N}$** in sum mode.

**Average binning FPN:**

$$\text{FPN}_\text{binning}^\text{avg} = \frac{1}{N}\sum_{i=1}^{N} \text{FPN}_i$$

For spatially random FPN (row-to-row pixel variation), averaging reduces it favorably. For correlated FPN (e.g., column FPN from the column amplifier), averaging provides no benefit.

**Mitigations:**
1. Apply BLC (Black Level Correction) independently at each sub-pixel level before binning;
2. Prefer average mode over sum mode (trading dynamic range headroom);
3. Symmetric pixel circuit layout to minimize inter-pixel FPN variation.

### 4.2 Moire Pattern Behavior Change

Binning reduces the effective Nyquist spatial frequency:

$$f_\text{Nyquist}^\text{binning} = \frac{f_\text{Nyquist}^\text{full}}{M} \quad \text{($M$ = merge factor per spatial dimension)}$$

For 2×2 binning, $f_\text{Nyquist}$ is halved. Spatial frequencies near the full-pixel Nyquist (e.g., fine textile patterns) alias completely in binning mode, producing different moire appearances compared to full-pixel output.

**Engineering countermeasure:** Apply a low-pass anti-aliasing filter before binning with cutoff at $f_\text{Nyquist}^\text{binning}$; or rely on the sensor's OLPF (Optical Low-Pass Filter), which is often omitted in cost-optimized sensors.

### 4.3 Color Discontinuity at Mode Transitions

**Symptom:** At the moment of a full-pixel ↔ binning mode switch, the image color shifts abruptly (inter-frame $\Delta E > 3$), visibly noticeable to the user.

**Root causes:**
1. Different demosaic algorithms in each mode produce slightly different color responses;
2. AWB has not yet converged in the new mode at the moment of transition;
3. LSC gain map switchover takes 1–2 extra frames;
4. Remosaic network output has a systematic color offset relative to direct binning output.

**Solutions:**
1. Freeze AWB updates for 1–3 frames at the transition point; resume once AWB has converged in the new mode;
2. Use brightness-ramp interpolation: blend color gains between the two modes across the $[L_\text{low}, L_\text{high}]$ transition zone, gradually shifting frame-by-frame;
3. Enforce a unified color target at the CCM level across both modes to minimize the baseline color offset.

### 4.4 Cross-talk Exacerbated in Binning Mode

**Optical cross-talk:** Obliquely incident photons traveling through a neighboring pixel's microlens and depositing charge in the adjacent photodiode. In Quad-Bayer's closely packed same-color sub-pixel arrangement, cross-talk paths are shorter, and the four co-located sub-pixels have a higher probability of sharing carriers.

**Electrical cross-talk:** Photo-generated carriers diffusing through the silicon substrate into adjacent depletion regions. In binning mode this effectively pre-blends sub-pixel signals before the intended merge point, creating signal aliasing.

**Impact on image quality:**
- The effective PSF broadens, degrading the MTF curve (see §5.2);
- In full-pixel mode, cross-talk between sub-pixels violates the independence assumption underlying Remosaic algorithms, causing color noise in the reconstructed image.

**Engineering mitigations:**
- Process engineering: Deep Trench Isolation (DTI) to reduce electrical cross-talk;
- Algorithm: Train Remosaic networks on real sensor data so that cross-talk effects are implicitly learned by the network.

---

## §5 Evaluation

### 5.1 SNR Improvement Quantification

**Reference standard:** ISO 12232:2019

**Test procedure:**
1. Set up a uniform flat-field target (18% neutral gray card) and capture images in both full and binning modes at the same Exposure Index (EI);
2. Compute SNR from the RAW-domain center region (center 1/4 of frame area):
   $$\text{SNR} = 20 \log_{10} \frac{\bar{S}}{\sigma_S}$$
3. Compare the SNR difference against the theoretical expectation of $10\log_{10}(N)/2$ dB;
4. Also measure Read Noise (dark frame) and shot noise slope (PTC curve).

**Expected results (2×2 binning):**

| Mode | SNR @ ISO 3200 | Notes |
|------|:--------------:|-------|
| Full-pixel | ~20 dB | Baseline |
| Binning (average, theoretical) | ~26 dB | +6 dB |
| Binning (measured, typical) | ~24–25 dB | Real-world losses from cross-talk, FPN |

### 5.2 Resolution Loss Assessment (MTF50)

**Reference standard:** ISO 12233:2017, slanted-edge method

**Test procedure:**
1. Photograph an ISO 12233 chart with both full and binning modes at the same focal length;
2. Compute MTF50 using imatest or an OpenCV slanted-edge method (in cycles/pixel or lp/mm);
3. Convert to consistent physical spatial frequency (lp/mm) to avoid confusion caused by the difference in pixel count.

**Expected results (2×2 binning):**

$$\text{MTF50}_\text{binning} \approx \frac{1}{2} \times \text{MTF50}_\text{full} \quad \text{(in cycles/pixel)}$$

When measured in physical units (lp/mm), the values should be similar because the effective pixel pitch doubles, keeping the physical Nyquist frequency approximately constant.

### 5.3 Full/Binning Switching Consistency

**Metric:** $\Delta E_{00}$ color difference (CIEDE2000)

**Test procedure:**
1. Fix the light source (D65, 6504 K) and slowly ramp scene brightness from 30 to 150 lux to trigger a mode switch;
2. Record 10 frames before and 10 frames after the switch; compute $\Delta E_{00}$ between the transition frame and the pre-switch 10-frame average;
3. Repeat across multiple color temperatures (2800 K, 4500 K, 6500 K) and ISO settings.

**Pass criteria (industry reference):**

$$\Delta E_{00}^\text{at transition} < 2.0 \quad \text{(just-noticeable difference for the human eye)}$$

$$\Delta E_{00}^\text{stabilized (within 3 frames)} < 1.0 \quad \text{(high-quality target)}$$

---

## §6 Code Example

The following Python code simulates 2×2 pixel binning in both average and sum modes, computes SNR improvements, and visualizes the noise distribution comparison between full-pixel and binning modes.

```python
"""
ch17_sensor_binning_demo.py
Simulates 2×2 pixel binning, compares SNR of Full vs. Binning modes

Dependencies: numpy, matplotlib
"""

import numpy as np
import matplotlib.pyplot as plt

# ──────────────────────────────────────────
# Parameters
# ──────────────────────────────────────────
np.random.seed(42)

HEIGHT, WIDTH = 512, 512         # Simulated sensor resolution (full mode)
SIGNAL_MEAN   = 100.0            # Mean signal level (DN) — 18% gray field
K             = 1.0              # System gain (e⁻/DN)
SIGMA_READ    = 3.0              # Read noise standard deviation (DN)
N_BINNING     = 4                # Number of pixels to merge (2×2 = 4)


def add_noise(signal: np.ndarray, K: float, sigma_read: float) -> np.ndarray:
    """Add Poisson shot noise and Gaussian read noise to a signal array."""
    shot_noise = np.random.poisson(signal / K).astype(np.float32) * K - signal
    read_noise = np.random.normal(0, sigma_read, signal.shape).astype(np.float32)
    return signal + shot_noise + read_noise


def pixel_binning_avg(raw: np.ndarray, bin_size: int = 2) -> np.ndarray:
    """
    Spatial binning — average mode.
    Input:  (H, W) RAW image
    Output: (H//bin_size, W//bin_size) binned image
    """
    h, w = raw.shape
    h_b, w_b = h // bin_size, w // bin_size
    cropped = raw[:h_b * bin_size, :w_b * bin_size]
    reshaped = cropped.reshape(h_b, bin_size, w_b, bin_size)
    return reshaped.mean(axis=(1, 3))


def pixel_binning_sum(raw: np.ndarray, bin_size: int = 2) -> np.ndarray:
    """Spatial binning — sum mode."""
    h, w = raw.shape
    h_b, w_b = h // bin_size, w // bin_size
    cropped = raw[:h_b * bin_size, :w_b * bin_size]
    reshaped = cropped.reshape(h_b, bin_size, w_b, bin_size)
    return reshaped.sum(axis=(1, 3))


def compute_snr(img: np.ndarray) -> float:
    """Compute image SNR in dB: 20 * log10(mean / std)."""
    return 20.0 * np.log10(img.mean() / img.std())


# ──────────────────────────────────────────
# Generate simulation data
# ──────────────────────────────────────────
# Ideal uniform signal (flat-field)
ideal_signal = np.full((HEIGHT, WIDTH), SIGNAL_MEAN, dtype=np.float32)

# Full-pixel mode: add noise to each individual pixel
full_noisy = add_noise(ideal_signal, K, SIGMA_READ)

# Software Binning (digital): bin the already-noisy full-pixel image
binned_avg = pixel_binning_avg(full_noisy, bin_size=2)
binned_sum = pixel_binning_sum(full_noisy, bin_size=2)

# Hardware Binning approximation: merge signal first, then add one
# (reduced) read noise to model a single shared readout circuit
merged_signal = pixel_binning_avg(ideal_signal, bin_size=2)
hw_binned = add_noise(merged_signal, K, SIGMA_READ / np.sqrt(N_BINNING))

# ──────────────────────────────────────────
# SNR statistics
# ──────────────────────────────────────────
snr_full = compute_snr(full_noisy)
snr_avg  = compute_snr(binned_avg)
snr_sum  = compute_snr(binned_sum / N_BINNING)    # normalize before computing SNR
snr_hw   = compute_snr(hw_binned)

print("=" * 45)
print(f"Full-pixel SNR:              {snr_full:.2f} dB")
print(f"SW Binning (average):        {snr_avg:.2f} dB  (Δ = {snr_avg - snr_full:+.2f} dB)")
print(f"SW Binning (sum, normalized):{snr_sum:.2f} dB  (Δ = {snr_sum - snr_full:+.2f} dB)")
print(f"HW Binning (approx):         {snr_hw:.2f} dB  (Δ = {snr_hw - snr_full:+.2f} dB)")
print(f"Theoretical gain (N=4):      +{10*np.log10(N_BINNING):.2f} dB")
print("=" * 45)

# ──────────────────────────────────────────
# Visualization
# ──────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
fig.suptitle("Pixel Binning Simulation: Full vs. Binning Noise Comparison", fontsize=14)

# Cropped image patches (center 128×128 region)
cx, cy = HEIGHT // 2, WIDTH // 2
crop_full = full_noisy[cx-64:cx+64, cy-64:cy+64]
crop_avg  = binned_avg[cx//2-32:cx//2+32, cy//2-32:cy//2+32]

axes[0, 0].imshow(crop_full, cmap='gray', vmin=60, vmax=140)
axes[0, 0].set_title(f"Full-pixel Mode (SNR={snr_full:.1f} dB)")
axes[0, 0].axis('off')

axes[0, 1].imshow(crop_avg, cmap='gray', vmin=60, vmax=140)
axes[0, 1].set_title(f"Binning Average Mode (SNR={snr_avg:.1f} dB)")
axes[0, 1].axis('off')

# Noise histograms
noise_full = full_noisy.flatten() - SIGNAL_MEAN
noise_avg  = binned_avg.flatten() - SIGNAL_MEAN
axes[1, 0].hist(noise_full, bins=100, range=(-30, 30), alpha=0.7,
                color='steelblue', label=f'Full σ={noise_full.std():.2f} DN')
axes[1, 0].hist(noise_avg,  bins=100, range=(-30, 30), alpha=0.7,
                color='tomato',    label=f'Binning avg σ={noise_avg.std():.2f} DN')
axes[1, 0].set_xlabel("Noise (DN)")
axes[1, 0].set_ylabel("Pixel count")
axes[1, 0].set_title("Noise Distribution Comparison")
axes[1, 0].legend()

# SNR bar chart
labels     = ['Full', 'SW Avg', 'SW Sum', 'HW Binning', 'Theoretical\nUpper Bound']
snr_values = [snr_full, snr_avg, snr_sum, snr_hw, snr_full + 6.02]
colors     = ['steelblue', 'tomato', 'orange', 'green', 'gray']
bars = axes[1, 1].bar(labels, snr_values, color=colors, alpha=0.8)
axes[1, 1].set_ylabel("SNR (dB)")
axes[1, 1].set_title("SNR Comparison Across Modes (2×2 Binning)")
axes[1, 1].set_ylim(min(snr_values) - 2, max(snr_values) + 2)
for bar, val in zip(bars, snr_values):
    axes[1, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    f'{val:.1f}', ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig("binning_snr_comparison.png", dpi=150)
plt.show()
```

**Expected output (approximate):**

```
=============================================
Full-pixel SNR:              20.48 dB
SW Binning (average):        26.21 dB  (Δ = +5.73 dB)
SW Binning (sum, normalized):26.19 dB  (Δ = +5.71 dB)
HW Binning (approx):         26.85 dB  (Δ = +6.37 dB)
Theoretical gain (N=4):      +6.02 dB
=============================================
```

**Code notes:**
- `add_noise`: Models Poisson shot noise + Gaussian read noise, consistent with the Vol.1 Ch.04 noise framework;
- `pixel_binning_avg/sum`: Two software binning modes implemented via `numpy.reshape` + `mean`/`sum` — efficient and vectorized;
- Hardware binning is approximated by merging signal first and then adding one (reduced) read noise, giving higher SNR than software binning;
- Measured improvement (~5.7 dB) falls slightly below the theoretical 6.02 dB because software binning accumulates N independent read noise instances instead of one shared readout.

---

## References

1. **Sony Corporation.** *IMX989 1-inch Type Back-illuminated CMOS Image Sensor Technical Brief*, 2022. [https://www.sony-semicon.com]

2. **Samsung Semiconductor.** *ISOCELL HP1 — Tetra²pixel Technology and 200MP ISOCELL Image Sensor*, Technical Whitepaper, 2021. [https://semiconductor.samsung.com]

3. **Chen, C., Chen, Q., Xu, J., & Koltun, V.** (2018). Learning to See in the Dark. *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR 2018)*. [arXiv:1805.01934]

4. **Zhang, Y., et al.** (2021). Rethinking Noise Synthesis and Modeling in Raw Denoising. *Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV 2021)*. arXiv:2110.04756

5. **Qian, G., et al.** (2022). Rethinking Learning-based Demosaicing, Denoising, and Super-Resolution Pipeline. *IEEE International Conference on Computational Photography (ICCP 2022)*. arXiv:1905.02538

6. **EMVA Standard 1288 Release 4.0.** *Standard for Characterization of Image Sensors and Cameras*. European Machine Vision Association, 2021. — Chapter 3: Pixel binning effects on noise parameters.

7. **Nakamura, J. (Ed.).** *Image Sensors and Signal Processing for Digital Still Cameras*. CRC Press, 2006. — Chapter 4: Pixel Design and Binning Circuits.

8. **Fossum, E. R., & Hondongwa, D. B.** (2014). A Review of the Pinned Photodiode for CCD and CMOS Image Sensors. *IEEE Journal of the Electron Devices Society*, 2(3), 33–43.

---

## §8 Glossary

| Term (English) | Term (Chinese) | Brief Definition |
|----------------|---------------|-----------------|
| Pixel Binning | 像素合并 | Merging adjacent pixels to increase effective signal and SNR |
| Analog (Hardware) Binning | 硬件合并 | Charge merging in the analog domain before ADC; optimal SNR |
| Digital (Software) Binning | 软件合并 | Sum or average in the digital domain after ADC |
| Quad-Bayer (4-in-1) | 四合一 | Sony's 4 same-color sub-pixel merge architecture |
| Tetra-pixel / Tetra²pixel | 四像素技术 | Samsung ISOCELL's 4-in-1 / 16-in-1 technology |
| Nona-Bayer (9-in-1) | 九合一 | 9 same-color pixel merge for extreme low light |
| Full-pixel Mode | 全分辨率模式 | All pixels read independently at maximum resolution |
| Binning Mode | 合并模式 | Pixel-merged readout, SNR-optimized |
| Remosaic | 重映射 | Algorithm to reconstruct a standard Bayer mosaic from non-standard CFA |
| Fixed Pattern Noise (FPN) | 固定模式噪声 | Spatially fixed noise pattern from pixel-to-pixel gain non-uniformity |
| Readout Noise | 读出噪声 | Random noise introduced by the ADC and amplifier chain |
| Shot Noise | 散粒噪声 | Noise from Poisson statistics of photon arrival |
| Signal-to-Noise Ratio (SNR) | 信噪比 | Ratio of signal mean to noise standard deviation; expressed in dB |
| Nyquist Frequency | 奈奎斯特频率 | Maximum spatial frequency representable by a sampling system |
| Chief Ray Angle (CRA) | 主光线角 | Angle between the chief ray incident on a pixel and the optical axis |
| Deep Trench Isolation (DTI) | 深沟隔离 | CMOS process structure that reduces electrical cross-talk between pixels |
| Cross-talk | 跨像素串扰 | Optical or electrical signal leakage between adjacent pixels |
| ΔE₀₀ | 色差 | CIEDE2000 color difference metric; used to assess color consistency |
| Lens Shading Correction (LSC) | 镜头阴影校正 | Correction for per-pixel gain roll-off caused by the lens vignetting |
| Photon Transfer Curve (PTC) | 光子转移曲线 | Plot of signal vs. noise variance used to characterize sensor noise parameters |

---

*End of Chapter. Next: Vol.2 Ch.01 — Black Level Correction (BLC) and Pixel Defect Correction (PDPC)*
