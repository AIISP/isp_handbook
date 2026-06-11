# Part 6, Chapter 11: Under-Display Camera Image Restoration

> **Position:** This chapter belongs to Part 6 "Consumer Photography Engineering" as a frontier special topic. Under-display cameras (UDC) are a key technology for full-screen smartphone design: the camera is hidden beneath the OLED display panel, and light passing through the pixel grid undergoes diffraction and scattering, causing severe imaging degradation. This chapter systematically covers the physics-based degradation model, PSF calibration, classical and deep-learning restoration algorithms, tuning strategies, artifact analysis, engineering evaluation, and provides complete runnable code.
> **Prerequisites:** Vol.1 Ch.04 (Noise Models), Vol.2 Ch.03 (Denoising), Vol.2 Ch.04 (Sharpening), Vol.3 Ch.01 (Deep Learning ISP Overview). Readers interested in optical background may refer to Vol.1 Ch.02 (Optics Basics).
> **Audience:** Algorithm engineers, IQA engineers, optical engineers

---

## §1 Theory

### 1.1 UDC System Overview

An under-display camera system places a CMOS image sensor directly beneath the OLED panel; the display panel simultaneously serves the dual functions of display and light transmission. To improve light throughput, the UDC region typically employs the following design modifications:

- **Reduced pixel density**: PPI (pixels per inch) in the UDC region drops to 100–200, compared to 300–460 PPI in the normal display area.
- **Increased pixel pitch**: The proportion of transparent inter-pixel gaps is increased, raising the aperture ratio.
- **Sparse metal routing**: Blocking area is reduced, but the regular metal grid structure introduces a grating-like structure.

Even so, the light received by the camera must still pass through hundreds of micrometers of OLED encapsulation, color filter array (CFA), and metal interconnect layers. Each layer modulates the light wave.

### 1.2 Degradation Physics Model

UDC imaging degradation can be modeled as a linear space-invariant (LSI) system (under approximate conditions):

$$
y = h * x + n
$$

where:

| Symbol | Meaning |
|--------|---------|
| $y$ | Degraded observed image (UDC captured result) |
| $x$ | Ideal sharp image (target restored result) |
| $h$ | Point Spread Function (PSF) |
| $*$ | 2D convolution operator |
| $n$ | Additive noise (AWGN + shot noise) |

This model is the foundation for all subsequent restoration algorithms. Note that in practice the UDC PSF exhibits **spatial variation**, strongly correlated with the brightness of the displayed content. In strict terms this should be written as:

$$
y(p) = \int h(p, q) \cdot x(q) \, dq + n(p)
$$

where $h(p, q)$ represents the response at position $p$ due to a point source at position $q$.

### 1.3 Diffraction Theory and PSF Characteristics

The OLED pixel grid constitutes a two-dimensional grating; its diffraction follows the grating equation:

$$
d \sin\theta_m = m\lambda
$$

where:
- $d$: grating period (pixel pitch; typical UDC region value $d \approx 120$–$250\,\mu\text{m}$)
- $\theta_m$: diffraction angle for order $m$
- $m$: diffraction order ($m = 0, \pm1, \pm2, \ldots$)
- $\lambda$: incident wavelength

For visible light ($\lambda \approx 450$–$700\,\text{nm}$) and a typical pixel pitch of $d = 200\,\mu\text{m}$, the first-order diffraction angle is approximately:

$$
\theta_1 = \arcsin\!\left(\frac{\lambda}{d}\right) \approx \arcsin(0.00225\text{–}0.0035) \approx 0.13°\text{–}0.20°
$$

Although the diffraction angle is small, when projected onto a sensor with focal length $f \approx 4\,\text{mm}$, the offset is approximately $9$–$14\,\mu\text{m}$ — approaching or exceeding the pixel pitch ($1.0$–$1.4\,\mu\text{m}$), making diffraction effects significant.

**PSF morphological characteristics**:

- **Central sharp peak**: The zeroth-order diffraction carries most of the energy, forming an Airy-disk-like central bright spot.
- **Diffraction rings/side-lobe halo**: Higher-order diffraction forms regularly arranged side lobes in a cross or grid pattern (depending on the pixel array geometry).
- **Diffuse scattering background**: Particulate scattering in the OLED encapsulation contributes a broad low-frequency halo.
- **Wavelength dependence**: $\theta_m \propto \lambda$; short wavelengths (blue) deflect less and long wavelengths (red) deflect more, producing colored diffraction fringes.

### 1.4 Blind vs. Non-Blind Deconvolution

| Type | PSF Known? | Characteristics |
|------|-----------|----------------|
| Non-blind deconvolution | Yes (from calibration) | Deterministic algorithm, suitable for engineering deployment |
| Blind deconvolution | No, must be estimated simultaneously | More flexible, but the problem is highly ill-posed |

In engineering practice the **non-blind** approach is standard: PSF is precisely calibrated offline; online restoration uses the known PSF. Deep learning methods can be viewed as a form of implicit blind deconvolution.

### 1.5 Wiener Deconvolution

The Wiener filter minimizes mean-squared error (MMSE) in the frequency domain, yielding an analytic solution:

$$
\hat{X}(u,v) = \frac{H^*(u,v)}{|H(u,v)|^2 + 1/\text{SNR}(u,v)} \cdot Y(u,v)
$$

where:
- $H(u,v) = \mathcal{F}\{h\}$: Fourier transform of the PSF
- $H^*$: complex conjugate of $H$
- $\text{SNR}(u,v)$: frequency-domain SNR, often approximated as a constant in practice

The regularization parameter $1/\text{SNR}$ balances two extremes:
- $\text{SNR} \to \infty$ (no regularization): equivalent to inverse filtering; noise is severely amplified.
- $\text{SNR} \to 0$ (strong regularization): output approaches zero; result is blurred.

Typical SNR range: $10$–$100\,\text{dB}$; must be tuned jointly with the actual image quality.

### 1.6 Richardson-Lucy Iterative Deconvolution

The Richardson-Lucy (RL) algorithm is based on Poisson-statistics maximum likelihood; its iterative update rule is:

$$
x^{(t+1)} = x^{(t)} \cdot \left( h^T * \frac{y}{h * x^{(t)}} \right)
$$

where $h^T$ denotes the PSF rotated by 180° (the correlation kernel). The RL algorithm preserves non-negativity and has clear physical interpretation, but it converges slowly and exhibits ringing when iterated too many times. In practice **10–30 iterations** are used, with an SSIM plateau criterion for early stopping.

### 1.7 Deep Learning Restoration Methods

A large number of DNN-based UDC restoration methods have emerged in recent years; representative works include:

- **UDC-UNet** (Zhou et al., 2021): An encoder-decoder network that takes the degraded image (optionally along with an estimated PSF) as input and outputs the restored image.
- **PDCRN** (Pan et al., 2023): Progressive Decomposition Convolutional Residual Network, which decomposes restoration into two stages — denoising and deconvolution.
- **End-to-end paired training**: Uses a UDC device and a standard camera to simultaneously capture the same scene, constructing paired datasets (Feng et al., 2021) for direct supervised pixel-level restoration.
- **Display-adaptive PSF estimation**: Takes the current frame's display content as an additional input; the network dynamically predicts the spatially varying PSF and then performs deconvolution (Display-Adaptive Restoration).

DNN methods typically achieve a PSNR gain of $+3$–$+5\,\text{dB}$ over classical methods, with more pronounced perceptual quality improvements, but inference latency is generally higher and requires NPU acceleration.

---

## §2 Calibration

### 2.1 PSF Measurement Principle

Accurate non-blind deconvolution depends on accurate PSF priors. The core calibration concept: under controlled conditions, the UDC device photographs a **known ideal point light source**, yielding the approximate PSF (convolution response).

### 2.2 Required Equipment

| Equipment | Specification Requirements |
|-----------|---------------------------|
| Pinhole aperture | Diameter 50–100 μm, laser-machined metal foil |
| Collimated LED light source | Bandwidth < 10nm (narrowband) or broadband white light, adjustable brightness |
| Dark room environment | Stray light < 0.1 lux |
| Six-axis adjustable stage (optional) | Precise alignment of pinhole with lens optical axis |
| High-precision white panel (optional) | Uniform Lambertian reflectance, for Siemens Star calibration method |

### 2.3 Point Source Calibration Procedure

1. **Screen state settings**: Capture under three OLED drive states — fully black (Black), fully white (White, 255 nit), and standard gray (128 gray) — to capture the PSF's dependence on display brightness.
2. **Multi-exposure capture**: To avoid saturation/quantization errors, capture 5–10 frames at different exposure times and average them.
3. **PSF extraction**: Locate the center bright spot (centroid method), crop an $N \times N$ window (typically $N=128$ or $256$), and normalize so that $\sum h = 1$.
4. **Per-channel processing**: Extract PSF separately for R/G/B channels (due to chromatic dispersion).
5. **Denoising post-processing**: Apply threshold truncation to the PSF ($h < \epsilon \to 0$) to remove the noise floor, then re-normalize.

### 2.4 Spatially-Varying PSF Grid Measurement

The UDC's PSF varies slowly across the field of view (FoV) due to sensor field curvature and OLED panel non-uniformity. Measure PSF at $M \times N$ grid positions (typically $5\times5$ or $7\times7$):

- Move the pinhole sequentially to grid positions in the sensor's FoV (or move the device to align with a fixed pinhole).
- Repeat the §2.3 procedure for each grid point.
- Obtain a PSF grid $\{h_{ij}\}$; during online restoration, tile the image and apply the corresponding PSF to each tile.

### 2.5 Display-Content Dependence

The higher the OLED brightness, the stronger the diffracted light power, and the larger the halo energy fraction in the PSF:

$$
h_{\text{eff}}(p) = h_0(p) + \alpha \cdot L_d \cdot h_{\text{halo}}(p)
$$

where $L_d$ is the local display brightness (normalized to $[0,1]$), $\alpha$ is the coupling coefficient (requiring calibration), $h_0$ is the baseline PSF, and $h_{\text{halo}}$ is the additional halo PSF.

Engineering approximation: calibrate only the two extreme states (fully black and fully white), then interpolate during runtime:

$$
h_{\text{eff}} = (1 - L_d) \cdot h_{\text{black}} + L_d \cdot h_{\text{white}}
$$

---

## §3 Tuning

### 3.1 Wiener SNR Parameter Adjustment

The SNR parameter is the most critical tuning knob for Wiener deconvolution:

| SNR Setting | Observed Phenomenon | Typical Range |
|------------|---------------------|--------------|
| Too high (> 60 dB) | Over-sharpening, visible ringing artifacts | — |
| Appropriate | Optimal sharpness-noise balance | 20–40 dB |
| Too low (< 10 dB) | Blurred image, detail loss | — |

Tuning recommendation: grid-search SNR (5 dB steps) on a calibrated dataset, select the best value using SSIM as the objective, then perform subjective validation on real-world scenes.

### 3.2 Richardson-Lucy Iteration Count

The RL iteration count directly affects restoration quality and computational cost:

- **< 10 iterations**: Insufficient restoration, image remains blurry.
- **10–30 iterations**: Typically the optimal range; SSIM tends to plateau.
- **> 50 iterations**: Significant noise amplification; "salt-and-pepper"-like artifacts appear.

**Stopping criterion**: Early stopping when the SSIM change between consecutive iterations satisfies $\Delta \text{SSIM} < 5 \times 10^{-4}$.

### 3.3 Pre-Deconvolution Denoising

Deconvolution is an ill-posed inverse problem; high-frequency noise gets amplified by PSF inverse filtering. It is recommended to **denoise first, then deconvolve**:

- **Bilateral filter**: Edge-preserving denoising; parameters: spatial $\sigma_s = 1$–$2\,\text{px}$, range $\sigma_r = 0.03$–$0.05$.
- **BM3D**: Stronger non-local denoising, suitable for low-light scenarios, but slower.
- **DNN-based denoising** (e.g., DnCNN): Can be integrated into an end-to-end pipeline.

Pre-denoising strength and subsequent deconvolution sharpening must be jointly optimized to avoid double over-processing.

### 3.4 TV Regularization Strength

When using total variation (TV) regularized deconvolution:

$$
\hat{x} = \arg\min_x \|y - h * x\|_2^2 + \lambda \|\nabla x\|_1
$$

The regularization coefficient $\lambda$ controls the smoothing level: too large a $\lambda$ produces "oil-painting" effects (staircase artifacts); too small a $\lambda$ is equivalent to no regularization. Typical $\lambda \in [10^{-4}, 10^{-2}]$; should be tuned per ISO level.

### 3.5 Spatially-Varying Deconvolution Tiling Strategy

When using a PSF grid, process the image in tiles:

- **Tile size**: 128×128 or 256×256 pixels.
- **Overlap ratio**: 50% overlap; use **Hann window** weighted blending to suppress tile boundary seams.
- **Boundary padding**: Use mirror (reflect) padding to reduce boundary ringing.

---

## §4 Artifacts

### 4.1 Ringing Artifacts (Gibbs Phenomenon)

**Cause**: Wiener deconvolution, by truncating the PSF at zero-crossings in the frequency domain, effectively multiplies the spectrum by a rectangular window; this produces Sinc oscillations in the spatial domain.

**Manifestation**: Parallel light-dark fringe pairs appear on either side of high-contrast edges (typical amplitude 5%–15% of edge contrast).

**Suppression methods**:
- Lower Wiener SNR (increase regularization).
- Apply edge-aware post-filtering (e.g., guided filter) after deconvolution.
- Apply a Hann window to smooth the PSF spectrum.

### 4.2 Noise Amplification

**Cause**: Deconvolution drives gain toward infinity at frequencies where the PSF spectrum is near zero, effectively amplifying noise at those frequencies.

**Manifestation**: High-frequency graininess appears in flat regions, especially at higher ISO settings.

**Suppression methods**: Lower the SNR parameter; use pre-denoising; deep learning methods implicitly learn noise suppression.

### 4.3 Halo Artifacts

**Cause**: Bright point sources (e.g., light bulbs, specular reflections) have concentrated PSF halo energy; after deconvolution the halo shrinks but is not fully eliminated, leaving a residual ring.

**Manifestation**: White or colored halos appear around bright sources; diameter is related to the PSF halo size (typically 5–20 pixels).

**Suppression methods**: Reduce deconvolution gain locally in highlight regions (local SNR-adaptive); display-adaptive PSF compensation.

### 4.4 Color Fringing

**Cause**: The diffraction angle $\theta_m = \arcsin(m\lambda/d)$ is wavelength-dependent; R/G/B channels have PSF side-lobe positions at different locations, and incomplete cross-channel alignment after deconvolution produces chromatic aberration.

**Manifestation**: Red/cyan or blue/yellow color fringes appear on fine lines and high-contrast edges; width is approximately 1–3 pixels.

**Suppression methods**: Use wavelength-specific calibrated PSFs for each channel; apply gentle low-pass filtering to the chroma channels in Lab color space after deconvolution.

### 4.5 Display Refresh Banding (Display Flicker Pattern)

**Cause**: When the OLED panel uses PWM dimming, and the exposure time is shorter than the PWM period (typical 240 Hz → 4.2ms), the sensor captures the bright and dark half-cycles of the display, producing horizontal bands.

**Manifestation**: Evenly spaced horizontal bright-dark bands appear in the image; spacing corresponds to the number of scan lines during one PWM half-cycle.

**Suppression methods**: Drive the UDC region with DC constant-brightness (not participating in PWM dimming) on the device side; or align the exposure time to an integer multiple of the PWM period.

---

## §5 Evaluation

### 5.1 Reference-Based Evaluation Metrics

Reference-based metrics require comparison with a ground-truth image captured with a standard camera of the same scene:

| Metric | Formula / Description | Typical Range |
|--------|----------------------|--------------|
| PSNR | $10\log_{10}(255^2 / \text{MSE})$ | Degraded: 25–30 dB; After restoration: +2–8 dB |
| SSIM | Structural similarity, combining luminance/contrast/structure | Degraded: 0.7–0.85; After restoration: 0.85–0.95 |
| LPIPS | Perceptual distance based on VGG/AlexNet features, lower is better | DNN methods typically 0.05–0.15 |

### 5.2 No-Reference Evaluation Metrics

No-reference metrics are suitable for evaluating in-the-wild real-world captures without a ground truth:

- **NIQE** (Natural Image Quality Evaluator): Based on natural image statistics; lower score is better.
- **BRISQUE**: Based on locally normalized luminance statistics; lower score is better.
- **MUSIQ** (Multi-scale Image Quality Transformer): Transformer-based perceptual quality score.

### 5.3 Benchmark Datasets

| Dataset | Source | Scale | Characteristics |
|---------|--------|-------|----------------|
| **Real-UDC** (Feng et al., 2021) | ZTE Axon 20 UDC + reference camera | 5,184 pairs | Real captured; includes daytime/nighttime/indoor |
| **SYNTH-UDC** | Synthetic; clean images convolved with real PSF | Scalable | Controlled experiments; PSF fully known |
| **UDC-SIT** (Samsung) | Samsung Galaxy Z Fold UDC | ~2,000 pairs | Folding-screen UDC scenarios |

### 5.4 Typical Baseline Performance Numbers

Typical results on the Real-UDC dataset (for reference only; test conditions vary slightly across papers):

| Method | PSNR (dB) | SSIM | LPIPS |
|--------|----------|------|-------|
| Degraded input (no processing) | 27.2 | 0.81 | 0.22 |
| Wiener deconvolution | 29.5 (+2.3) | 0.85 | 0.18 |
| Richardson-Lucy (20 iterations) | 30.1 (+2.9) | 0.86 | 0.17 |
| UDC-UNet (Zhou et al., 2021) | 33.4 (+6.2) | 0.92 | 0.09 |
| PDCRN (Pan et al., 2023) | 34.6 (+7.4) | 0.94 | 0.07 |

---

## §6 Code

The following code is based on NumPy / SciPy / OpenCV. It simulates UDC degradation and demonstrates the complete restoration pipeline. Since a real UDC hardware device is not available in the development environment, degraded input is generated by convolving a clean image with a synthetic PSF, and then restoration effectiveness is validated.

```python
"""
UDC (Under-Display Camera) Image Restoration Demonstration
Dependencies: numpy, scipy, opencv-python, matplotlib
"""

import numpy as np
import cv2
import matplotlib.pyplot as plt
from scipy.signal import fftconvolve
from scipy.ndimage import gaussian_filter


# ──────────────────────────────────────────────────────────────────────
# 1. PSF Measurement: Extract normalized PSF from a point source image
# ──────────────────────────────────────────────────────────────────────

def measure_psf_from_point_source(image: np.ndarray,
                                   crop_size: int = 128,
                                   noise_thresh: float = 0.01) -> np.ndarray:
    """
    Extract a normalized PSF from a captured point source image.

    Parameters
    ----------
    image       : grayscale or single-channel float image, range [0, 1]
    crop_size   : crop window size (pixels); should be at least 2× the PSF support radius
    noise_thresh: PSF values below this threshold are truncated to 0 (removes noise floor)

    Returns
    -------
    psf : shape (crop_size, crop_size), normalized PSF with sum = 1
    """
    if image.ndim == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    img = image.astype(np.float64)

    # Locate center bright spot (centroid method)
    total = img.sum()
    y_coords = np.arange(img.shape[0])[:, None]
    x_coords = np.arange(img.shape[1])[None, :]
    cy = int(np.round((img * y_coords).sum() / total))
    cx = int(np.round((img * x_coords).sum() / total))

    # Crop window centered on the bright spot
    half = crop_size // 2
    y0, y1 = max(0, cy - half), min(img.shape[0], cy + half)
    x0, x1 = max(0, cx - half), min(img.shape[1], cx + half)
    psf = img[y0:y1, x0:x1].copy()

    # Zero-pad if window is smaller than requested
    if psf.shape != (crop_size, crop_size):
        padded = np.zeros((crop_size, crop_size), dtype=np.float64)
        ph, pw = psf.shape
        padded[:ph, :pw] = psf
        psf = padded

    # Threshold-based noise floor removal
    psf[psf < noise_thresh * psf.max()] = 0.0

    # Normalize
    s = psf.sum()
    if s > 0:
        psf /= s
    return psf.astype(np.float32)


# ──────────────────────────────────────────────────────────────────────
# 2. Wiener Deconvolution (frequency domain, per-channel processing)
# ──────────────────────────────────────────────────────────────────────

def wiener_deconvolve(image: np.ndarray,
                      psf: np.ndarray,
                      snr_db: float = 30.0) -> np.ndarray:
    """
    Wiener frequency-domain deconvolution.

    Parameters
    ----------
    image  : input image, float32, range [0, 1], shape (H, W) or (H, W, C)
    psf    : point spread function, float32, sum = 1, shape (kH, kW)
    snr_db : signal-to-noise ratio (dB), typical range 10–60

    Returns
    -------
    restored : same shape as image, float32, range [0, 1]
    """
    snr_linear = 10.0 ** (snr_db / 10.0)
    reg = 1.0 / snr_linear            # regularization term

    def _deconv_channel(ch: np.ndarray) -> np.ndarray:
        H, W = ch.shape
        # Zero-pad PSF to image size and center-shift
        psf_pad = np.zeros((H, W), dtype=np.float64)
        kh, kw = psf.shape
        psf_pad[:kh, :kw] = psf
        psf_pad = np.roll(psf_pad, -kh // 2, axis=0)
        psf_pad = np.roll(psf_pad, -kw // 2, axis=1)

        Y = np.fft.fft2(ch.astype(np.float64))
        H_fft = np.fft.fft2(psf_pad)
        H_conj = np.conj(H_fft)
        H_abs2 = np.abs(H_fft) ** 2

        # Wiener filter
        W_filt = H_conj / (H_abs2 + reg)
        X_est = np.fft.ifft2(W_filt * Y).real
        return np.clip(X_est, 0.0, 1.0).astype(np.float32)

    if image.ndim == 2:
        return _deconv_channel(image)
    else:
        channels = [_deconv_channel(image[:, :, c]) for c in range(image.shape[2])]
        return np.stack(channels, axis=2)


# ──────────────────────────────────────────────────────────────────────
# 3. Richardson-Lucy Iterative Deconvolution
# ──────────────────────────────────────────────────────────────────────

def richardson_lucy(image: np.ndarray,
                    psf: np.ndarray,
                    iterations: int = 20,
                    ssim_tol: float = 5e-4) -> np.ndarray:
    """
    Richardson-Lucy iterative deconvolution with SSIM plateau early stopping.

    Parameters
    ----------
    image      : input image, float32 [0,1], shape (H,W) or (H,W,C)
    psf        : point spread function, float32, sum=1
    iterations : maximum number of iterations
    ssim_tol   : SSIM change threshold; stops early when change falls below this value

    Returns
    -------
    restored : same shape as image, float32 [0,1]
    """
    from skimage.metrics import structural_similarity as ssim

    psf_flip = psf[::-1, ::-1]  # PSF rotated 180° (transpose convolution kernel)

    def _rl_channel(ch: np.ndarray) -> np.ndarray:
        x = ch.copy().astype(np.float64)
        x = np.clip(x, 1e-6, None)       # avoid division by zero
        prev_ssim = -1.0

        for i in range(iterations):
            # Forward convolution h * x^t
            hx = fftconvolve(x, psf.astype(np.float64), mode='same')
            hx = np.clip(hx, 1e-10, None)

            # Ratio
            ratio = ch.astype(np.float64) / hx

            # Backward convolution (correlation) h^T * ratio
            corr = fftconvolve(ratio, psf_flip.astype(np.float64), mode='same')

            # Update
            x = x * corr
            x = np.clip(x, 0.0, 1.0)

            # Convergence check (compute SSIM every 5 iterations)
            if (i + 1) % 5 == 0:
                cur_ssim = ssim(ch, x, data_range=1.0)
                if abs(cur_ssim - prev_ssim) < ssim_tol:
                    break
                prev_ssim = cur_ssim

        return x.astype(np.float32)

    if image.ndim == 2:
        return _rl_channel(image)
    else:
        channels = [_rl_channel(image[:, :, c]) for c in range(image.shape[2])]
        return np.stack(channels, axis=2)


# ──────────────────────────────────────────────────────────────────────
# 4. Spatially-Varying Deconvolution (Tiling + Hann Window Blending)
# ──────────────────────────────────────────────────────────────────────

def apply_sv_deconvolution(image: np.ndarray,
                           psf_grid: list,
                           tile_size: int = 256,
                           overlap: float = 0.5,
                           snr_db: float = 30.0) -> np.ndarray:
    """
    Spatially-varying deconvolution: tile the image, apply per-tile PSF,
    and blend with Hann window weighting.

    Parameters
    ----------
    image     : input image, float32 [0,1], (H,W) or (H,W,C)
    psf_grid  : 2D list psf_grid[row][col] = PSF array; grid uniformly covers the image
    tile_size : tile size (pixels)
    overlap   : overlap ratio between adjacent tiles (0–1)
    snr_db    : Wiener filter SNR (dB)

    Returns
    -------
    output : same shape as image, float32 [0,1]
    """
    H, W = image.shape[:2]
    step = int(tile_size * (1.0 - overlap))
    n_rows = len(psf_grid)
    n_cols = len(psf_grid[0])

    # Create accumulation buffer and weight map
    if image.ndim == 3:
        accum = np.zeros_like(image, dtype=np.float64)
        weight = np.zeros((H, W, 1), dtype=np.float64)
    else:
        accum = np.zeros_like(image, dtype=np.float64)
        weight = np.zeros((H, W), dtype=np.float64)

    # Hann window
    hann_1d_row = np.hanning(tile_size)
    hann_1d_col = np.hanning(tile_size)
    hann_2d = np.outer(hann_1d_row, hann_1d_col).astype(np.float32)

    y_starts = list(range(0, H - tile_size + 1, step)) + [H - tile_size]
    x_starts = list(range(0, W - tile_size + 1, step)) + [W - tile_size]
    y_starts = sorted(set(max(0, y) for y in y_starts))
    x_starts = sorted(set(max(0, x) for x in x_starts))

    for yi, y0 in enumerate(y_starts):
        for xi, x0 in enumerate(x_starts):
            y1, x1 = y0 + tile_size, x0 + tile_size
            y1, x1 = min(y1, H), min(x1, W)
            tile = image[y0:y1, x0:x1]

            # Select nearest PSF
            grid_row = min(int(yi / len(y_starts) * n_rows), n_rows - 1)
            grid_col = min(int(xi / len(x_starts) * n_cols), n_cols - 1)
            psf = psf_grid[grid_row][grid_col]

            restored_tile = wiener_deconvolve(tile, psf, snr_db)

            th, tw = restored_tile.shape[:2]
            w = hann_2d[:th, :tw]
            if image.ndim == 3:
                accum[y0:y1, x0:x1] += restored_tile * w[:, :, None]
                weight[y0:y1, x0:x1, 0] += w
            else:
                accum[y0:y1, x0:x1] += restored_tile * w
                weight[y0:y1, x0:x1] += w

    weight = np.maximum(weight, 1e-10)
    output = (accum / weight).astype(np.float32)
    return np.clip(output, 0.0, 1.0)


# ──────────────────────────────────────────────────────────────────────
# 5. Complete UDC Restoration Pipeline
# ──────────────────────────────────────────────────────────────────────

def udc_restoration_pipeline(raw_image: np.ndarray,
                              psf: np.ndarray,
                              method: str = 'wiener',
                              snr_db: float = 30.0,
                              rl_iters: int = 20,
                              denoise_sigma: float = 1.0,
                              sharpen_amount: float = 0.3) -> np.ndarray:
    """
    Complete UDC restoration pipeline: pre-denoise → deconvolve → light sharpening → output.

    Parameters
    ----------
    raw_image      : UDC degraded image, float32 [0,1], (H,W,3) BGR
    psf            : point spread function
    method         : 'wiener' or 'rl'
    snr_db         : Wiener SNR (dB); only used in wiener mode
    rl_iters       : RL iteration count; only used in rl mode
    denoise_sigma  : pre-denoising Gaussian sigma (0 = skip)
    sharpen_amount : USM sharpening strength after deconvolution (0 = skip)

    Returns
    -------
    output : restored image, float32 [0,1], (H,W,3) BGR
    """
    img = raw_image.astype(np.float32)

    # Step 1: Pre-denoising
    if denoise_sigma > 0:
        img_denoised = np.stack(
            [gaussian_filter(img[:, :, c], sigma=denoise_sigma) for c in range(3)],
            axis=2
        )
    else:
        img_denoised = img

    # Step 2: Deconvolution
    if method == 'wiener':
        restored = wiener_deconvolve(img_denoised, psf, snr_db)
    elif method == 'rl':
        restored = richardson_lucy(img_denoised, psf, rl_iters)
    else:
        raise ValueError(f"Unknown method: {method}. Choose 'wiener' or 'rl'.")

    # Step 3: Light USM sharpening (to offset blur from pre-denoising)
    if sharpen_amount > 0:
        blurred = np.stack(
            [gaussian_filter(restored[:, :, c], sigma=1.0) for c in range(3)],
            axis=2
        )
        restored = np.clip(restored + sharpen_amount * (restored - blurred), 0.0, 1.0)

    return restored.astype(np.float32)


# ──────────────────────────────────────────────────────────────────────
# 6. Synthetic UDC Degradation + Visualization Demo
# ──────────────────────────────────────────────────────────────────────

def make_synthetic_udc_psf(size: int = 64, pitch_px: float = 8.0,
                            wavelength_nm: float = 550.0,
                            focal_mm: float = 4.0,
                            pixel_um: float = 1.2) -> np.ndarray:
    """
    Generate a simulated UDC PSF: Gaussian core + periodic diffraction side lobes.

    Parameters
    ----------
    size        : PSF kernel size (odd number)
    pitch_px    : OLED pixel pitch (in sensor pixel units)
    wavelength_nm: center wavelength (nm)
    focal_mm    : equivalent focal length (mm)
    pixel_um    : sensor pixel pitch (μm)
    """
    half = size // 2
    y, x = np.mgrid[-half:half + 1, -half:half + 1]
    r = np.sqrt(x**2 + y**2) + 1e-10

    # Central Gaussian peak (Airy disk approximation)
    sigma_core = 1.2
    core = np.exp(-r**2 / (2 * sigma_core**2))

    # Diffraction side lobes (grid pattern, simulating square pixel array)
    freq = 2 * np.pi / pitch_px
    halo = (np.cos(freq * x) * np.cos(freq * y)) ** 2
    halo = np.clip(halo - 0.5, 0, None)  # keep positive values only

    # Diffuse scattering halo (broad Gaussian)
    sigma_halo = size / 5.0
    scatter = np.exp(-r**2 / (2 * sigma_halo**2)) * 0.05

    psf = 0.7 * core + 0.25 * halo + scatter
    psf = np.clip(psf, 0, None)
    psf /= psf.sum()
    return psf.astype(np.float32)


def demo_udc_restoration():
    """Full demonstration: synthetic degradation → Wiener restoration → RL restoration → visualization."""

    # ── Generate or load test image ──
    # Replace with cv2.imread if a real image is available
    np.random.seed(42)
    H, W = 256, 256
    # Simple synthetic image with edges and texture
    clean = np.zeros((H, W, 3), dtype=np.float32)
    cv2.rectangle(clean, (40, 40), (120, 120), (0.9, 0.5, 0.2), -1)
    cv2.circle(clean, (180, 80), 40, (0.2, 0.8, 0.9), -1)
    cv2.putText(clean, 'UDC', (60, 180), cv2.FONT_HERSHEY_SIMPLEX,
                2.0, (1.0, 1.0, 0.3), 3)

    # ── Synthetic PSF ──
    psf = make_synthetic_udc_psf(size=65, pitch_px=10.0)

    # ── Synthetic UDC degradation ──
    degraded = np.stack(
        [fftconvolve(clean[:, :, c], psf, mode='same') for c in range(3)],
        axis=2
    ).astype(np.float32)
    # Add Gaussian noise (simulating ISO 800 level)
    noise = np.random.normal(0, 0.015, degraded.shape).astype(np.float32)
    degraded = np.clip(degraded + noise, 0.0, 1.0)

    # ── Restoration ──
    restored_wiener = udc_restoration_pipeline(
        degraded, psf, method='wiener', snr_db=30.0,
        denoise_sigma=0.8, sharpen_amount=0.2)

    restored_rl = udc_restoration_pipeline(
        degraded, psf, method='rl', rl_iters=20,
        denoise_sigma=0.8, sharpen_amount=0.15)

    # ── Compute PSNR ──
    def psnr(a, b):
        mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
        if mse < 1e-10:
            return 100.0
        return 10 * np.log10(1.0 / mse)

    print(f"PSNR degraded input  vs GT: {psnr(degraded, clean):.2f} dB")
    print(f"PSNR Wiener restored vs GT: {psnr(restored_wiener, clean):.2f} dB")
    print(f"PSNR RL restored     vs GT: {psnr(restored_rl, clean):.2f} dB")

    # ── Visualization ──
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    titles = ['Clean Original (GT)', 'Degraded Image (UDC)', 'Wiener Restored',
              'RL Restored (20 iters)', 'PSF (log scale)', 'Frequency Domain Amplitude']

    for ax in axes.flat:
        ax.axis('off')

    def show(ax, img, title):
        ax.imshow(np.clip(img[:, :, ::-1], 0, 1))  # BGR→RGB
        ax.set_title(title, fontsize=11)
        ax.axis('off')

    show(axes[0, 0], clean, titles[0])
    show(axes[0, 1], degraded, titles[1])
    show(axes[0, 2], restored_wiener, titles[2])
    show(axes[1, 0], restored_rl, titles[3])

    # PSF log-scale visualization
    axes[1, 1].imshow(np.log1p(psf * 1000), cmap='hot')
    axes[1, 1].set_title(titles[4], fontsize=11)
    axes[1, 1].axis('off')

    # Frequency domain amplitude comparison (green channel)
    def fft_mag(img_ch):
        f = np.fft.fftshift(np.abs(np.fft.fft2(img_ch)))
        return np.log1p(f)

    axes[1, 2].plot(fft_mag(clean[:, H//2, 1]), label='GT', linewidth=1.5)
    axes[1, 2].plot(fft_mag(degraded[:, H//2, 1]), label='Degraded', linewidth=1.5)
    axes[1, 2].plot(fft_mag(restored_wiener[:, H//2, 1]), label='Wiener', linewidth=1.5)
    axes[1, 2].set_title(titles[5], fontsize=11)
    axes[1, 2].legend()
    axes[1, 2].axis('on')

    plt.suptitle('UDC Image Restoration Demonstration', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('udc_restoration_demo.png', dpi=150, bbox_inches='tight')
    plt.show()
    print("Result saved to udc_restoration_demo.png")


if __name__ == '__main__':
    demo_udc_restoration()
```

**Code notes**:

1. `measure_psf_from_point_source`: Centroid localization + crop + threshold truncation; extracts a normalized PSF from a measured point source image.
2. `wiener_deconvolve`: Frequency-domain Wiener filter; PSF is zero-padded and shift-aligned; processing is per-channel independently.
3. `richardson_lucy`: fftconvolve-accelerated RL iterations; convergence is checked by computing SSIM every 5 iterations.
4. `apply_sv_deconvolution`: Image tiling + PSF grid bilinear lookup + Hann window weighted blending; implements approximate spatially-varying deconvolution.
5. `udc_restoration_pipeline`: Complete pipeline including pre-denoising (Gaussian), deconvolution (Wiener/RL), and post-sharpening (USM).
6. `demo_udc_restoration`: Synthetic UDC degradation demonstration (OLED grating PSF = Gaussian peak + grid diffraction side lobes + diffuse scattering) with PSNR comparison output.

---

## References

1. **Feng, Y., et al.** (2021). "Removing Diffraction Image Artifacts in Under-Display Camera via Dynamic Skip Connection Network." *CVPR 2021.* [Real-UDC dataset and DSNet baseline]

2. **Zhou, Y., et al.** (2021). "Image Restoration for Under-Display Camera." *CVPR 2021.* [UDC-UNet; end-to-end paired training framework]

3. **Pan, J., et al.** (2023). "PDCRN: Progressive Decomposition Convolutional Residual Network for Under-Display Camera Image Restoration." *IEEE TIP 2023.*

4. **Wiener, N.** (1949). *Extrapolation, Interpolation, and Smoothing of Stationary Time Series.* MIT Press. [Original Wiener filter theory]

5. **Richardson, W. H.** (1972). "Bayesian-based iterative method of image restoration." *JOSA, 62(1), 55–59.*

6. **Lucy, L. B.** (1974). "An iterative technique for the rectification of observed distributions." *AJ, 79, 745.*

7. **Born, M., & Wolf, E.** (2013). *Principles of Optics*, 7th ed. Cambridge University Press. [Diffraction grating theory, Chapter 8]

8. **Wang, Z., et al.** (2004). "Image quality assessment: From error visibility to structural similarity." *IEEE TIP, 13(4), 600–612.* [SSIM]

9. **Zhang, R., et al.** (2018). "The Unreasonable Effectiveness of Deep Features as a Perceptual Metric." *CVPR 2018.* [LPIPS]

10. **Mittal, A., et al.** (2012). "Making a 'Completely Blind' Image Quality Analyzer." *IEEE SPL, 20(3), 209–212.* [BRISQUE]

11. **Samsung Display.** (2022). "Under Panel Camera Technology Whitepaper." Samsung Electronics.

12. **Wang, X., et al.** (2021). "Towards Real-World Blind Face Restoration with Generative Facial Prior." *CVPR 2021.* [Face enhancement combined with UDC restoration reference]

---

> **Chapter Summary:** The core challenge of UDC image restoration is the diffraction degradation introduced by the OLED pixel grating. The degradation model $y=h*x+n$ provides the theoretical foundation for all algorithms. Wiener deconvolution yields the frequency-domain optimal analytic solution; adjusting the SNR parameter enables a trade-off between ringing and blur. The RL algorithm preserves non-negativity and is suitable for Poisson noise scenarios. Spatially-varying deconvolution handles PSF spatial non-uniformity through tiling + Hann window blending. Deep learning methods (UDC-UNet, PDCRN) achieve PSNR gains of $+6$–$+8\,\text{dB}$ on paired datasets and represent the mainstream direction for industrial deployment. Accurate PSF calibration and appropriate tuning strategies are prerequisites for achieving effective algorithm performance.
