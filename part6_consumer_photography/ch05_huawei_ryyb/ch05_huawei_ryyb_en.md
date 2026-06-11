# Part 6, Chapter 05: Huawei RYYB Sensor, XD Fusion Engine, and Variable Aperture

> **Position:** This chapter provides an in-depth analysis of Huawei's unique sensor and algorithm innovations.
> **Prerequisites:** Vol.2 Ch.02 (Demosaicing), Vol.6 Ch.01 (Consumer Photography Evolution), Vol.6 Ch.02 (Google HDR+)
> **Audience:** Algorithm engineers, sensor engineers

---

## §1 RYYB Sensor Theory

### 1.1 Optical Limitations of the Standard Bayer CFA

The standard Bayer Color Filter Array (CFA) uses a 2×2 R-G-G-B mosaic arrangement, in which green (G) occupies 50% of pixels and red (R) and blue (B) each occupy 25%. This design follows the human eye's dependence on the green channel for luminance information (chrominance signal bandwidth is far lower than luminance signal bandwidth), but the spectral transmission characteristics of G filter elements carry an inherent cost:

Standard G filter elements have a peak transmission wavelength of approximately 530 nm (green region) and a full width at half maximum (FWHM) of approximately 90–110 nm. This effectively blocks the vast majority of photons in the red (600–700 nm) and blue (400–480 nm) bands. After passing through a G filter element, **approximately 65% of the photons in the visible spectrum (400–700 nm) are absorbed**, and only approximately 35% of the incident photons actually reach the photodiode.

Quantified: assuming a uniform photon flux density across all bands under white light, the equivalent quantum efficiency (QE) of the G channel is:

$$\eta_G = \int_{400}^{700} T_G(\lambda) \cdot S(\lambda) \, d\lambda \bigg/ \int_{400}^{700} S(\lambda) \, d\lambda \approx 0.35$$

where $T_G(\lambda)$ is the spectral transmittance of the G filter element and $S(\lambda)$ is the normalized white-light spectral density.

### 1.2 RYYB CFA Design Principles

Huawei's RYYB (Red-Yellow-Yellow-Blue) CFA was introduced with the P30 Pro in 2019, replacing the two G pixels in the standard Bayer array with Y (Yellow) pixels:

```
Standard Bayer 2×2:       RYYB 2×2:
  R  G               R  Y
  G  B               Y  B
```

The yellow (Y) filter element is a composite R-G channel (broadband filter) with a peak transmission of approximately 580 nm and an FWHM of approximately 160–190 nm, covering the combined red-green spectral range of 540–700 nm:

$$T_Y(\lambda) \approx T_R(\lambda) + T_G(\lambda) - T_R(\lambda) \cdot T_G(\lambda)$$

Approximately, the equivalent QE of the Y filter element is:

$$\eta_Y = \int_{400}^{700} T_Y(\lambda) \cdot S(\lambda) \, d\lambda \bigg/ \int_{400}^{700} S(\lambda) \, d\lambda \approx 0.55$$

Compared to the G channel's ~0.35, **the Y channel collects approximately 57% more photons than the G channel**, i.e.:

$$\text{Gain ratio} = \frac{\eta_Y}{\eta_G} \approx \frac{0.55}{0.35} \approx 1.57$$

Huawei's officially claimed "40% improvement in light intake" corresponds to the overall CFA average (R/B channel transmittance unchanged; average gain from YY replacing GG):

$$\text{Average gain} = \frac{\eta_R + \eta_Y + \eta_Y + \eta_B}{4} \bigg/ \frac{\eta_R + \eta_G + \eta_G + \eta_B}{4} = \frac{\eta_R + 2\eta_Y + \eta_B}{\eta_R + 2\eta_G + \eta_B}$$

Substituting typical values $\eta_R \approx 0.25, \eta_G \approx 0.35, \eta_Y \approx 0.55, \eta_B \approx 0.20$:

$$\text{Average gain} = \frac{0.25 + 2 \times 0.55 + 0.20}{0.25 + 2 \times 0.35 + 0.20} = \frac{1.55}{1.15} \approx 1.35$$

This means overall light intake is improved by approximately 35%, consistent with Huawei's claimed "40%" (actual measured values differ slightly depending on the specific filter design of the sensor).

### 1.3 Theoretical Derivation of SNR Improvement

Assuming the pixel full well capacity (FWC) is $N_{sat}$ and the noise model is dominated by Poisson noise (at low gain):

$$\text{SNR} = \frac{N_e}{\sqrt{N_e + \sigma_{read}^2}}$$

where $N_e$ is the number of photoelectrons and $\sigma_{read}$ is the read noise standard deviation. Under the same exposure time and incident light intensity, the number of electrons collected by the Y channel is:

$$N_{e,Y} = \eta_Y \cdot \Phi \cdot t_{exp} \cdot A_{pixel}$$

Compared to the G channel $N_{e,G} = \eta_G \cdot \Phi \cdot t_{exp} \cdot A_{pixel}$, under equal conditions:

$$\text{SNR}_Y - \text{SNR}_G \approx 10\log_{10}\left(\frac{N_{e,Y}}{N_{e,G}}\right)^{1/2} = 5\log_{10}\left(\frac{\eta_Y}{\eta_G}\right) \approx 5\log_{10}(1.57) \approx 1.0 \text{ dB}$$

This indicates that in the photon-noise-dominated regime, RYYB provides a per-pixel SNR improvement of approximately 1 dB over Bayer. However, if the extra photons are used to reduce gain (lower the ISO gain), the relative contribution of read noise decreases, and the actual improvement is more significant — especially in extremely dark environments (< 100 photons per pixel), where read noise dominates and the benefit of increased light collection is fully converted into SNR improvement.

### 1.4 The Trade-off of RYYB: Color Accuracy Challenges

The core engineering challenge introduced by RYYB is: **the Y channel contains an R component, causing standard color theory to break down**.

In a standard Bayer system, the three independent channels (R, G, B) are approximately orthogonal, and the Color Correction Matrix (CCM) can be solved by a linear system:

$$\begin{bmatrix} R_{lin} \\ G_{lin} \\ B_{lin} \end{bmatrix} = M_{Bayer} \begin{bmatrix} R_{raw} \\ G_{raw} \\ B_{raw} \end{bmatrix}$$

In RYYB, the spectral response of the Y channel is highly correlated with the R channel (high mutual information), making color demultiplexing difficult. The transform from CIE XYZ to sRGB must pass through a dedicated CCM calibrated for the RYYB spectral responses, and the condition number of this matrix is far larger than that of the standard Bayer CCM. This means color correction is more sensitive to noise — slight channel noise, once amplified, can cause noticeable hue shifts.

---

## §2 RYYB Demosaic Algorithm

### 2.1 Why Standard Demosaic Algorithms Do Not Apply

Standard Bayer demosaicing algorithms (AHD, VNG, LMMSE, etc.) all assume that the G channel carries high-frequency luminance information and use G's high spatial sampling rate (50%) to guide R and B interpolation. RYYB violates this assumption:

1. The Y channel replaces the G channel, but Y's spectral response partially overlaps with R — it is not a "pure luminance channel"
2. Directly substituting Y for G in AHD introduces systematic color shifts, because the spatial correlation of Y–R is not equal to that of G–R
3. Commercial RAW processing software (Lightroom, Capture One) does not support RYYB RAW format (using the Huawei P30 Pro's .rw2 format as an example, correct color rendering is not achievable in third-party software)

### 2.2 Two-Stage Demosaic Approach

Implementation details of Huawei's RYYB demosaicing are not publicly disclosed, but academic and reverse-engineering analysis (DPReview 2019 technical analysis, Imatest laboratory data) reveals an approximate workflow:

**Stage 1: Estimating a virtual G channel from the Y channel (Pseudo-G Recovery)**

The spectral response of the Y channel can be approximately expressed as:

$$Y_{raw} \approx \alpha \cdot R_{raw} + \beta \cdot G_{true} + \varepsilon$$

where $\alpha \approx 0.40$, $\beta \approx 0.60$ (estimated from filter design), and $\varepsilon$ is noise. Using the known R channel interpolation result $\hat{R}$, a virtual G can be estimated:

$$\hat{G} = \frac{Y_{raw} - \alpha \cdot \hat{R}}{\beta} = \frac{Y_{raw} - 0.40 \cdot \hat{R}}{0.60}$$

Simplified form (common approximation):

$$\hat{G} \approx Y - 0.3 \cdot R_{interpolated}$$

This "pseudo-G" still differs spectrally from the true G channel, but is sufficient to drive subsequent spatial interpolation.

**Stage 2: Standard demosaicing on the virtual RGGB**

A virtual Bayer frame is constructed by replacing Y1 and Y2 positions in RYYB with the estimated $\hat{G}$, forming an R-$\hat{G}$-$\hat{G}$-B pseudo-Bayer pattern, followed by AHD (Adaptive Homogeneity-Directed) or LMMSE (Linear Minimum Mean Square Error) interpolation:

```
RYYB original:        Pseudo-Bayer conversion:
  R  Y₁             R   Ĝ₁
  Y₂  B             Ĝ₂  B
```

**Stage 3: RYYB-specific CCM correction**

The sRGB values output by Stage 2 exhibit systematic color shifts because Pseudo-G is not spectrally equivalent to the true G. A final CCM re-calibrated from the RYYB spectral response must be applied:

$$\begin{bmatrix} R_{out} \\ G_{out} \\ B_{out} \end{bmatrix} = M_{RYYB \to XYZ} \cdot \begin{bmatrix} R_{dem} \\ \hat{G}_{dem} \\ B_{dem} \end{bmatrix}$$

$M_{RYYB \to XYZ}$ is obtained by least-squares fitting from measured data of a ColorChecker 24-patch chart under multiple illuminants (D65, Illuminant A, F11 fluorescent), with a target error of $\Delta E_{00} < 3.0$ (CIE 2000 color difference formula).

### 2.3 Characteristic Artifacts of RYYB Demosaicing

1. **Blue hue shift:** The Y channel is completely insensitive to the blue spectral band; G estimation accuracy in blue regions is poor. Color restoration in blue areas relies solely on the B channel, with weak noise resistance
2. **Saturated red clipping:** When the R channel saturates, the Y channel also approaches saturation, causing loss of detail in bright red areas (e.g., traffic lights, roses)
3. **Purple fringing:** Spectral aliasing produces purple/green fringing at high-contrast edges, requiring an additional chromatic aberration (CA) correction step

---

## §3 XD Fusion Engine (P40 Pro, 2020)

### 3.1 The Dual Meaning of XD Fusion

The XD Fusion Engine in the Huawei P40 Pro is a brand name for a multi-layer technology stack. "XD" simultaneously refers to two dimensions:

- **eXtreme Dynamic range:** Multi-frame RAW-domain HDR fusion, targeting 120 dB dynamic range
- **eXtreme Detail:** AI-assisted super-resolution and texture preservation, counteracting detail loss from noise suppression

### 3.2 Dual Matrix Camera

The P40 Pro introduces a dual optical filter matrix in front of the sensor:

- **Coarse Matrix:** Standard broadband RYYB, responsible for capturing luminance/dynamic range information
- **Fine Matrix:** Narrowband spectral filtering, providing more precise color separation information (similar to computational spectral imaging principles)

The two signals are fused in the ISP: the coarse matrix contributes high-SNR luminance information, while the fine matrix contributes high-precision color difference signals — analogous to luminance-chrominance (Luma-Chroma) separation processing, but physically realized through two independent filter matrices.

> **Note:** Huawei keeps the specific implementation details of the dual matrix confidential. The above description is based on patent analysis of the P40 Pro (CN111263028A, etc.) and content from the Huawei Developer Conference 2020 technical presentation.

### 3.3 XD Optics: Computational Optical Correction

XD Optics is a computational optics technology introduced by Huawei on the P40 Pro:

**Core idea:** The lens design accepts an aberration budget in hardware optics, with software correcting it through PSF (Point Spread Function) deconvolution. Specifically:

1. Factory calibration: The PSF is measured for each lens (or lens-sensor combination), building a per-unit correction LUT
2. During capture: The corresponding PSF is retrieved by looking up focal length, aperture, and focus distance
3. In the ISP: Inverse filtering (Inverse Filter / Wiener Filter) is applied to the RAW image to correct field curvature, lateral chromatic aberration (Lateral CA), and other aberrations

Wiener filter deconvolution (frequency domain):

$$\hat{F}(u,v) = \frac{H^*(u,v)}{|H(u,v)|^2 + K} \cdot G(u,v)$$

where $G$ is the observed image spectrum, $H$ is the PSF spectrum, $K$ is the noise-to-signal power ratio (balancing deblur strength against noise amplification), and $\hat{F}$ is the corrected image spectrum.

This design allows the actual lens assembly to be thinner (reducing lens module thickness by approximately 0.3 mm), with software compensating for optical quality loss.

### 3.4 AI Multi-Frame Fusion Workflow

XD Fusion Engine's multi-frame RAW fusion workflow (reconstructed from publicly available technical materials):

```
RYYB sensor capture (N consecutive frames, N=4–8)
          │
          ├─────────────────────┐
          ▼                     ▼
   Reference frame        Non-reference frames × (N-1)
          │                     │
          │          Optical flow estimation → Motion vectors
          │                     │
          │          Deformation alignment (Warping)
          │                     │
          └──────────┬──────────┘
                     ▼
           Weighted RAW-domain fusion (Weighted Merge)
           Weight = f(confidence map, motion residual, luminance)
                     │
                     ▼
           RYYB demosaicing (two-stage)
                     │
                     ▼
           XD Optics deconvolution correction
                     │
                     ▼
           AI denoising (NPU, Kirin ISP)
           [50 MP input → 50 MP enhanced / pixel binning → 12.5 MP]
                     │
                     ▼
           HDR tone mapping + Leica color tuning
                     │
                     ▼
           HEIF 10-bit output (main image)
```

### 3.5 Pixel Binning and Resolution Selection Strategy

The P40 Pro sensor is 50 MP (1/1.28-inch, 0.9 µm pixels). Huawei uses a quad-bayer (Tetracell) pixel binning strategy:

| Output Mode | Pixel Count | Effective Pixel Area | Applicable Scenario |
|-------------|------------|----------------------|---------------------|
| Binning mode (4:1) | 12.5 MP | 1.8 µm equivalent | Low light, SNR-priority |
| Full-pixel mode | 50 MP | 0.9 µm | Bright light, detail-priority |
| AI super-resolution mode | >50 MP | — | Extreme-range digital zoom |

The AI denoising network simultaneously processes the full 50 MP output, suppressing noise while preserving detail, avoiding the irreversible detail loss of traditional quad-bayer binning.

---

## §4 Variable Aperture (P50 Pro)

### 4.1 Dual-Aperture Mechanical Design

The Huawei P50 Pro (2021) features a variable aperture (Variable Aperture) system for the main camera, supporting two-stop switching between f/1.8 and f/4.0:

| Parameter | f/1.8 (large aperture) | f/4.0 (small aperture) |
|-----------|----------------------|----------------------|
| Light intake ratio | $(4.0/1.8)^2 \approx 5\times$ | 1× |
| Depth of field | Shallow (natural background bokeh) | Deep (full-scene sharpness) |
| Diffraction limit | Low (geometric aberration dominates) | Higher (diffraction begins to affect) |
| Applicable scenario | Night scenes, portraits | Architecture, scanning, ample light |
| Shutter speed (same exposure) | ~5 stops faster (5 EV advantage) | — |

The mechanical implementation uses a **VCM (Voice Coil Motor)** to drive aperture blades, with a position feedback sensor (Hall effect sensor) providing closed-loop control. Switching time is approximately 150–200 ms (single trigger); continuous automatic switching (based on ambient brightness) is controlled by the AE algorithm.

### 4.2 Coordination Between Variable Aperture and the ISP

Aperture switching triggers coordinated adjustments across multiple ISP modules — a systems engineering problem that pure optics design cannot handle:

**1. Exposure Jump Prevention**

When a physical aperture switch occurs during a single frame capture (on a rolling shutter sensor), the upper and lower halves of the same frame may correspond to different apertures, producing a horizontal brightness dividing line (banding). Huawei's ISP solution:

- Triggers aperture switching only during the vertical blanking period (VBI, ~1–2 ms) between frames
- Immediately updates exposure parameters (ET, Gain) after switching, maintaining the target exposure under the new aperture

**2. AWB Adaptive Update**

The spectral transmittance of the lens differs slightly between f/1.8 and f/4.0 (different lens element thicknesses, different degrees of chromatic aberration), and the change in light intake shifts the sensor response curve's operating range. The ISP triggers a fast AWB re-estimation (Fast AWB Reconvergence) after aperture switching, re-converging to the correct white balance within approximately 3–5 frames.

**3. Demosaic and Noise Reduction Parameter Switching**

At f/4.0, diffraction begins to affect high-frequency detail, manifesting as a slight global softening (compared to f/1.8). When the ISP detects that the aperture is f/4.0, it automatically increases sharpening strength to compensate for the MTF reduction caused by diffraction. At the same time, since the 5× reduction in light intake (at the same exposure, gain must be increased or exposure extended), noise reduction strength is adaptively raised.

**4. Focus-Depth of Field Consistency**

When the aperture switches from f/1.8 to f/4.0, the depth of field deepens; previously out-of-focus (bokeh) areas gradually come into focus. In the real-time preview stream, users can intuitively see background details gradually appearing, without needing to refocus. The ISP preview stream switches in real time, maintaining 30 fps (the user's perception of aperture switch latency is approximately 150 ms, experienced as a smooth transition).

---

## §5 Kirin ISP Evolution

### 5.1 Kirin 970 (2017): The Starting Point of Mobile AI

The Kirin 970 was the world's first commercial smartphone SoC with an integrated NPU (Huawei Mate 10, released October 2017), marking the dawn of the AI-ISP era:

| Kirin Version | Release Year | NPU Specs | ISP AI Capability |
|--------------|-------------|----------|-------------------|
| Kirin 970 | 2017 | 1× NPU (Cambricon MA-1 IP) | Scene classification (food / vegetation / text / night scene, etc.; 13 categories), 1200 images/min |
| Kirin 980 | 2018 | 2× NPU (dual-core) | AI denoising, AI deblurring (PDAF-assisted) |
| Kirin 990 5G | 2019 | 2× large-core + micro-core NPU | AI-AE, AI-AWB, real-time semantic segmentation |
| Kirin 9000 | 2020 | 2× large-core NPU (2× throughput increase) | XD Optics computational optic correction hardened, AI super-resolution |

The Kirin 970's NPU uses the Cambricon MA-1 IP, INT8 inference. Measured ResNet-50 inference speed is approximately 1.5 ms/frame (vs. ~500 ms/frame on the same-era CPU), a speedup of approximately 330×. This enabled real-time scene classification (13 categories): each viewfinder frame is classified by the NPU, and the ISP's tone mapping, color saturation, and sharpening strength are automatically adjusted according to the scene category.

### 5.2 Kirin 9000 (2020): XD Optics Hardening

The Kirin 9000 (in the Mate 40 Pro, released October 2020) is the last complete flagship SoC from Huawei (the final TSMC 5 nm tape-out before export control), reaching the peak of Huawei's proprietary ISP:

- **5 nm process:** Power/performance ratio improved ~50% over the 7 nm Kirin 990
- **Dual large-core NPU:** INT8 throughput approximately 12–15 TOPS (estimated; Huawei has not disclosed specific TOPS figures)
- **Dedicated XD Optics hardware:** PSF deconvolution no longer relies on NPU general compute; replaced by a dedicated logic unit (hardwired Wiener filter) within the ISP subsystem, reducing latency by approximately 60%
- **4K HDR video:** 8-bit log format (Log) recording with post-processing HDR10/HLG transcode

### 5.3 Impact of Sanctions and the Resulting Technology Gap

After US EAR (Export Administration Regulations) sanctions took effect in September 2020, Huawei could no longer commission TSMC to manufacture Kirin SoCs, halting the evolution of its proprietary ISP chips:

- Huawei phones released from 2021 onward (P50 series) use a Snapdragon 888 4G special edition (with 5G modem disabled), reverting to the Spectra ISP architecture
- The 2023 Mate 60 Pro uses a Kirin 9000s manufactured on SMIC's 7 nm process (N+2 node), but the process maturity limits NPU compute density; AI-ISP capability falls back compared to the Kirin 9000
- In the long term, Huawei's ISP evolution has entered a "compensating for process with algorithms" path: using increasingly complex multi-frame and computational optics algorithms to compensate for the absence of advanced process nodes

### 5.4 Leica Color Tuning System

Huawei established its partnership with Leica in 2016, introducing Leica color tuning starting from the P9 series:

- **Leica Authentic:** Color expression faithful to actual scene colors; tends toward lower saturation and higher color accuracy
- **Leica Vivid:** Increases color saturation and contrast; appeals to a broader user aesthetic

In technical implementation, Leica tuning is reflected in a customized color matrix and gamma curve at the end of the ISP pipeline:

$$M_{Leica} = M_{CCM} \cdot M_{hue\text{-}rotation} \cdot M_{saturation}$$

Specific parameters are jointly tuned by Huawei ISP engineers and Leica's optical laboratory (Leica plant, Wetzlar, Germany), calibrated using professional colorimetric instruments (X-Rite i1Pro spectrophotometer) under standard illuminant light boxes (D65, Illuminant A).

---

## §6 Code: RYYB Demosaic Simulation

Companion notebook: *See §6 Code section for runnable examples.*

### 6.1 Notebook Content Overview

The notebook simulates the RYYB CFA pattern, implements the two-stage demosaicing algorithm, and provides a quantitative comparison of color accuracy (ΔE) and noise SNR against standard Bayer demosaicing.

**Cell 1: RYYB CFA simulation generation**

```python
import numpy as np
import colour
from colour_checker_detection import colour_checkers_coordinates_segmenter

def simulate_ryyb_raw(rgb_image, noise_level=0.01):
    """
    Convert an sRGB image to simulated RYYB RAW data
    R  Y            R  R+G(~0.6G+0.4R)
    Y  B    →       R+G  B
    """
    h, w, _ = rgb_image.shape
    raw = np.zeros((h, w), dtype=np.float32)

    R = rgb_image[:,:,0]
    G = rgb_image[:,:,1]
    B = rgb_image[:,:,2]

    # Yellow channel = 0.40*R + 0.60*G (approximate spectral mixing)
    Y = 0.40 * R + 0.60 * G

    # RYYB 2×2 mosaic pattern:
    # (0,0)=R  (0,1)=Y
    # (1,0)=Y  (1,1)=B
    raw[0::2, 0::2] = R[0::2, 0::2]   # R
    raw[0::2, 1::2] = Y[0::2, 1::2]   # Y
    raw[1::2, 0::2] = Y[1::2, 0::2]   # Y
    raw[1::2, 1::2] = B[1::2, 1::2]   # B

    # Add Poisson noise
    raw = np.random.poisson(raw / noise_level) * noise_level
    return raw.astype(np.float32)
```

**Cell 2: Two-stage RYYB demosaicing implementation**

```python
from scipy.ndimage import convolve

def ryyb_demosaic_two_stage(raw, alpha=0.40, beta=0.60):
    """
    Two-stage RYYB demosaicing
    Stage 1: estimate virtual G from Y
    Stage 2: bilinear interpolation on pseudo-RGGB
    """
    h, w = raw.shape

    # --- Stage 1: Extract individual channels ---
    R_raw = np.zeros((h, w))
    Y_raw = np.zeros((h, w))
    B_raw = np.zeros((h, w))

    R_raw[0::2, 0::2] = raw[0::2, 0::2]
    Y_raw[0::2, 1::2] = raw[0::2, 1::2]
    Y_raw[1::2, 0::2] = raw[1::2, 0::2]
    B_raw[1::2, 1::2] = raw[1::2, 1::2]

    # Bilinear interpolation for R channel (standard)
    k_bilinear_R = np.array([[1,2,1],[2,4,2],[1,2,1]]) / 4.0
    R_interp = convolve(R_raw, k_bilinear_R, mode='reflect')

    # Stage 1: G_pseudo = (Y - alpha*R) / beta
    G_pseudo = np.zeros((h, w))
    mask_Y = np.zeros((h, w), dtype=bool)
    mask_Y[0::2, 1::2] = True
    mask_Y[1::2, 0::2] = True

    G_pseudo[mask_Y] = (Y_raw[mask_Y] - alpha * R_interp[mask_Y]) / beta
    G_pseudo = np.clip(G_pseudo, 0, 1)

    # --- Stage 2: Pseudo-RGGB bilinear demosaicing ---
    pseudo_raw = np.zeros((h, w))
    pseudo_raw[0::2, 0::2] = R_raw[0::2, 0::2]  # R
    pseudo_raw[0::2, 1::2] = G_pseudo[0::2, 1::2]  # G_pseudo
    pseudo_raw[1::2, 0::2] = G_pseudo[1::2, 0::2]  # G_pseudo
    pseudo_raw[1::2, 1::2] = B_raw[1::2, 1::2]  # B

    # Bilinear interpolation for full channels
    k_G = np.array([[0,1,0],[1,4,1],[0,1,0]]) / 4.0
    k_RB = np.array([[1,2,1],[2,4,2],[1,2,1]]) / 4.0

    R_out = convolve(pseudo_raw * (pseudo_raw == R_raw).astype(float), k_RB)
    G_out = convolve(G_pseudo, k_G)
    B_out = convolve(pseudo_raw * (pseudo_raw == B_raw).astype(float), k_RB)

    return np.stack([R_out, G_out, B_out], axis=-1)
```

**Cell 3: Color accuracy ΔE comparison**

```python
import colour

def compute_delta_e(img_test, img_ref):
    """Compute mean ΔE00 between two images"""
    # Convert to Lab color space
    lab_test = colour.XYZ_to_Lab(colour.sRGB_to_XYZ(img_test))
    lab_ref = colour.XYZ_to_Lab(colour.sRGB_to_XYZ(img_ref))
    delta_e = colour.delta_E(lab_test, lab_ref, method='CIE 2000')
    return delta_e.mean(), delta_e.max()

# Compare on ColorChecker 24-patch chart
# Standard Bayer vs. RYYB two-stage demosaicing
results = []
for patch_idx in range(24):
    patch = colorchecker_patches[patch_idx]
    bayer_raw = simulate_bayer_raw(patch)
    ryyb_raw = simulate_ryyb_raw(patch)

    bayer_rgb = standard_bilinear_demosaic(bayer_raw)
    ryyb_rgb = ryyb_demosaic_two_stage(ryyb_raw)

    de_mean_bayer, _ = compute_delta_e(bayer_rgb, patch)
    de_mean_ryyb, _ = compute_delta_e(ryyb_rgb, patch)
    results.append((de_mean_bayer, de_mean_ryyb))

print(f"Bayer mean ΔE00: {np.mean([r[0] for r in results]):.2f}")
print(f"RYYB two-stage mean ΔE00: {np.mean([r[1] for r in results]):.2f}")
```

**Cell 4: Low-light SNR comparison (light intake gain verification)**

```python
def compute_snr_db(signal_patch):
    """Compute green-channel SNR (using a uniform gray patch)"""
    mean_val = signal_patch.mean()
    std_val = signal_patch.std()
    if std_val == 0:
        return float('inf')
    return 20 * np.log10(mean_val / std_val)

# Simulate SNR curves at different exposure levels (photon counts)
photon_counts = [10, 20, 50, 100, 200, 500, 1000]
snr_bayer = []
snr_ryyb = []

for pc in photon_counts:
    # Simulate Bayer G channel (QE=0.35)
    G_bayer = np.random.poisson(pc * 0.35, size=(64, 64)).astype(float)
    # Simulate RYYB Y channel (QE=0.55)
    Y_ryyb = np.random.poisson(pc * 0.55, size=(64, 64)).astype(float)

    snr_bayer.append(compute_snr_db(G_bayer))
    snr_ryyb.append(compute_snr_db(Y_ryyb))

import matplotlib.pyplot as plt
plt.semilogx(photon_counts, snr_bayer, 'b-o', label='Bayer G (QE=0.35)')
plt.semilogx(photon_counts, snr_ryyb, 'r-s', label='RYYB Y (QE=0.55)')
plt.xlabel('Incident photon count (photons/pixel)')
plt.ylabel('SNR (dB)')
plt.title('RYYB vs. Bayer photon SNR comparison')
plt.legend()
plt.grid(True)
plt.savefig('ryyb_vs_bayer_snr.png', dpi=150)
```

---

## §7 References

1. Huawei. *P30 Pro: Official Camera Technical Overview*. Huawei Consumer, 2019. [Official technical documentation]
2. Huawei. *XD Fusion Engine: P40 Pro Camera Technology Deep Dive*. Huawei Developer Conference 2020. [Public technical presentation]
3. Huawei. *P50 Pro Variable Aperture Technology Overview*. Huawei Official, 2021. [Official press release]
4. DPReview. *Huawei P30 Pro In-Depth Review: The RYYB Mystery*. dpreview.com, 2019. [Independent technical analysis]
5. Imatest. *RYYB vs RGGB CFA Analysis*. Imatest Technical Report, 2019. [Measurement lab analysis]
6. Li X. et al. *Color Filter Array Demosaicking: New Method and Performance Measures*. IEEE Trans. Image Processing, 2001. [AHD algorithm foundations]
7. Malvar H. S., He L., Cutler R. *High-Quality Linear Interpolation for Demosaicing of Bayer-Patterned Color Images*. ICASSP 2004. [LMMSE demosaicing]
8. Heikkinen V. et al. *Spectral Analysis of RYYB Color Filter Arrays for Camera Image Processing*. Color Imaging Conference, 2020. [RYYB spectral analysis academic reference]
9. CN111263028A. *An image processing method and apparatus (XD Fusion related)*. Huawei Technologies Co., Ltd., 2020. [Published patent]
10. Leica Camera AG & Huawei. *Leica Optics for Huawei P Series: Joint Technical Statement*. 2016–2022. [Collaborative technical statement]

---

## §8 Glossary

| Term | Full Name / Explanation |
|------|------------------------|
| **RYYB** | Red-Yellow-Yellow-Blue; Huawei's non-standard CFA introduced with the P30 Pro, replacing the two G channels in Bayer with broadband yellow (Y) filter elements, theoretically improving light intake by ~35–40% |
| **XD Fusion** | eXtreme Dynamic range + eXtreme Detail; the brand name for the multi-frame RAW fusion engine in the Huawei P40 Pro |
| **XD Optics** | Huawei's computational optics technology; corrects lens aberrations (field curvature, lateral chromatic aberration, etc.) through PSF deconvolution in software, allowing thinner physical lens hardware |
| **Variable Aperture** | Variable Aperture; the Huawei P50 Pro offers two electronically controlled stops (f/1.8 and f/4.0), with aperture blades driven by VCM |
| **Leica Tuning** | Leica color tuning; a color matrix and tone mapping parameter system jointly specified by Huawei ISP engineers and Leica's laboratory, introduced from the P9 series onward |
| **Dual Matrix Camera** | Dual Matrix Camera; the P40 Pro introduces two layers of optical filter matrices (coarse + fine spectrum) in front of the sensor to improve color separation precision |
| **VCM** | Voice Coil Motor; the mechanical actuator for the variable aperture, also used in AF (autofocus) motors |
| **PSF** | Point Spread Function; describes an optical system's imaging response to a point source; the core parameter for XD Optics deconvolution |
| **ΔE00** | Color difference computed by the CIE 2000 formula; ΔE < 1 is imperceptible, 1–3 is slight, > 3 is a perceptible color difference |
| **Full Well Capacity** | Full Well Capacity (FWC); the maximum number of photoelectrons a single pixel can accumulate before saturation; determines the upper bound of dynamic range |
| **Kirin NPU** | The neural network processing unit in Huawei's Kirin SoCs; first introduced in the Kirin 970 (Cambricon MA-1 IP); reached the peak of Huawei's proprietary design in the Kirin 9000 |
| **PSF Deconvolution** | Deconvolution; inverse filtering using a known point spread function to recover image detail blurred by optical aberrations |
| **Staggered HDR** | Staggered HDR (also discussed in Chapter 4); row-level alternating exposure within a single frame; also employed by MediaTek in RYYB scenarios |
| **HDR10 / HLG** | Two HDR video formats: HDR10 uses static metadata; HLG (Hybrid Log-Gamma) is a broadcast-grade HDR standard. Both are supported by Huawei P50/Mate 40 series |
