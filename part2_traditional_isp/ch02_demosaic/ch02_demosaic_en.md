# Part 2, Chapter 02: Demosaic (Bayer Interpolation)

> **Pipeline position:** After BLC + PDPC + LSC; before Denoising
> **Prerequisites:** Chapter 6 (RAW Format & Bayer CFA), Chapter 4 (Noise Models)
> **Reader path:** Algorithm Engineer (core chapter), DL Researcher (§1 only needed)

---

## §1 Theory

### 1.1 The Bayer CFA and the Undersampling Problem

Every pixel on a digital camera's image sensor (CMOS/CCD) can only measure light intensity; it cannot distinguish color. To capture color information with a single sensor, Kodak engineer Bryce Bayer proposed the **Color Filter Array (CFA)** in 1976 — placing a tiny filter in front of each pixel that transmits only a specific wavelength band, forming a periodic color pattern known as the **Bayer array**.

The most common Bayer pattern is **RGGB**, whose 2×2 fundamental unit is:

```
R  G
G  B
```

In an H×W RAW image filtered through the Bayer CFA, R and B each occupy 1/4 of the pixels while G occupies 1/2. This arrangement is deliberate: the human visual system is far more sensitive to luminance than to chrominance, and the green channel is highly correlated with the luminance signal, so assigning it twice the sampling density effectively reduces perceived noise and aliasing.

**The demosaicing problem:** Because each pixel records only one color, the values of the other two colors are missing at every pixel location. From an information-theoretic perspective, the RAW image is aliased in the spatial-frequency domain:

- The R and B channels are 2×2 downsampled; their Nyquist frequency is half that of the G channel.
- In high-frequency texture regions (fine fabrics, diagonal edges), color information is severely underrepresented.
- Naive interpolation introduces **false color** and **zipper artifacts**.

The goal of demosaicing is to reconstruct a complete H×W×3 RGB image from the sparsely sampled single-channel Bayer image, such that the result closely approximates the "true" color image that would have been captured by three separate full-resolution sensors.

### 1.2 Algorithm Families Overview

Over approximately 50 years of development, demosaicing algorithms can be grouped into four generations — each generation addressing the failure modes of the previous one:

| Generation | Representative | Core idea | Main weakness |
|-----------|---------------|-----------|---------------|
| 1st | Bilinear interpolation | Uniform linear interpolation of missing colors | Severe false color and blur at high frequencies |
| 2nd | Gradient-guided (MHC 2004) | Corrects interpolation using color-difference smoothness prior | Zipper effect persists at strong edges |
| 3rd | Adaptive-direction (Hamilton-Adams 1997; AHD 2005; DLMMSE 2005) | Interpolates separately in H and V directions, selects by homogeneity or LMMSE criterion | Maze pattern in isotropic textures; direction judgment unstable under noise |
| 4th | Deep learning (Gharbi 2016+) | End-to-end CNN, joint demosaicing and denoising | Requires large training sets; higher inference cost |

**Hamilton-Adams (1997)** is the foundation of the third generation: Hamilton and Adams proposed switching the interpolation path between horizontal and vertical directions based on gradient magnitude, and is the direct precursor to AHD and other direction-adaptive methods. The paper was published as Hewlett-Packard Labs Technical Report HPL-96-139 (1997).

### 1.3 Bilinear Interpolation

Bilinear interpolation is the simplest baseline: each missing color value is estimated as the arithmetic average of the surrounding same-color pixels.

For the green estimate at an R-position $(r, c)$ in the RGGB pattern (both $r$ and $c$ even):

$$G_{\text{est}}(r, c) = \frac{G(r, c-1) + G(r, c+1) + G(r-1, c) + G(r+1, c)}{4}$$

Blue estimate at the same R-position (no B present):

$$B_{\text{est}}(r, c) = \frac{B(r-1,c-1) + B(r-1,c+1) + B(r+1,c-1) + B(r+1,c+1)}{4}$$

Bilinear interpolation is equivalent to applying a low-pass filter independently to each channel, which causes severe color aliasing at high-frequency textures. PSNR on the Kodak dataset is typically 34–36 dB.

### 1.4 MHC Algorithm: High-Quality Linear Interpolation (Malvar-He-Cutler 2004)

**Source:** Henrique S. Malvar, Li-wei He, Ross Cutler, "High-quality linear interpolation for demosaicing of Bayer-patterned color images," *ICASSP 2004*, Microsoft Research Technical Report MSR-TR-2004-138.

The key insight of MHC is **color-difference smoothness**: in natural images, the ratio (or difference) between adjacent pixel values in different color channels is often smoother than the absolute values themselves. Using this prior, the high-frequency information of a known channel can correct the low-frequency estimate of a missing channel.

#### 1.4.1 Green Channel Interpolation at an R Position

At R-position $(r, c)$:
- Known: $R(r, c)$, four neighboring green values $G(r,c-1), G(r,c+1), G(r-1,c), G(r+1,c)$
- Same-channel values at distance 2: $R(r,c-2), R(r,c+2)$ (horizontal direction)

The MHC green estimate:

$$\boxed{G_{\text{est}}(r, c) = \frac{G(r,c-1) + G(r,c+1) + G(r-1,c) + G(r+1,c)}{4} + \frac{2R(r,c) - R(r,c-2) - R(r,c+2)}{8}}$$

**Term-by-term interpretation:**

- **First term** $\frac{G_L + G_R + G_U + G_D}{4}$: The standard bilinear result, providing a low-frequency estimate of G.
- **Second term** $\frac{2R_C - R_{LL} - R_{RR}}{8}$: A color-difference correction. The expression $2R_C - R_{LL} - R_{RR}$ is the **second-order finite difference** (discrete Laplacian) of the R channel at the current position, capturing the local curvature of R. Because the color difference $G - R$ varies slowly in natural images, the curvature of R approximates the curvature offset that G should also have at this position. Adding this correction (divided by 8 as a regularization factor) effectively uses the high-frequency content of R to refine the bilinear G estimate.

Analogously, for green estimation at a B position, the vertical B difference is used:

$$G_{\text{est}}(r, c)\big|_{B} = \frac{G(r,c-1) + G(r,c+1) + G(r-1,c) + G(r+1,c)}{4} + \frac{2B(r,c) - B(r-2,c) - B(r+2,c)}{8}$$

#### 1.4.2 Red and Blue Channel Interpolation

MHC applies the same color-difference correction principle to R and B channels as well, defining 6 different position types (R at R-row, G at R-row, G at B-row, B at B-row, etc.), each corresponding to a precomputed 5×5 convolution kernel that can be stored as a lookup table for efficient implementation.

MHC achieves approximately 40–42 dB PSNR on the Kodak dataset and is widely deployed in industry as a high-quality linear method.

### 1.5 AHD Algorithm: Adaptive Homogeneity-Directed Demosaicing (Hirakawa 2005)

**Source:** Keigo Hirakawa, Thomas W. Parks, "Adaptive Homogeneity-Directed Demosaicing Algorithm," *IEEE Transactions on Image Processing*, vol. 14, no. 3, pp. 360–369, March 2005.

The AHD (Adaptive Homogeneity-Directed) algorithm recognizes that edges in natural images have directional structure, and interpolation along an edge is superior to interpolation across it.

**Algorithm steps:**

1. **Demosaic independently in both the horizontal and vertical directions** to produce two candidate RGB images $\hat{I}_H$ and $\hat{I}_V$.
2. Convert each candidate image from sRGB to **CIELab color space** (a perceptually uniform space).
3. For each pixel, count the number of "homogeneous pixels" in a small neighborhood (typically 5×5 or 3×3): a pixel is homogeneous if its $\Delta E$ difference from its neighbors is below a threshold. Compute homogeneity counts $H_H$ and $H_V$ for the horizontal and vertical candidates respectively.
4. **Select the direction with the higher homogeneity count** as the final result:

$$\hat{I}(r,c) = \begin{cases} \hat{I}_H(r,c) & \text{if } H_H > H_V \\ \hat{I}_V(r,c) & \text{if } H_V > H_H \\ \frac{\hat{I}_H(r,c)+\hat{I}_V(r,c)}{2} & \text{otherwise} \end{cases}$$

AHD achieves approximately 42–44 dB PSNR on the Kodak dataset, significantly reducing zipper artifacts at edges, though it may produce maze patterns in isotropic texture regions (e.g., diagonal stripes).

#### 1.5.1 Formal Definition of the Homogeneity Criterion

The **homogeneity** criterion in the original paper is defined as follows.

**Perceptual color-difference thresholding:** For position $(r, c)$ and candidate direction $d \in \{H, V\}$, inspect each neighbor $(r', c')$ in the $5 \times 5$ window $\mathcal{N}(r,c)$:

$$\delta_d(r',c') = \begin{cases} 1 & \text{if } \Delta E_{76}\!\left(\text{Lab}_d(r,c),\, \text{Lab}_d(r',c')\right) < \tau \\ 0 & \text{otherwise} \end{cases}$$

where $\text{Lab}_d(r,c)$ is the CIELab coordinate of the direction-$d$ candidate at $(r,c)$, $\Delta E_{76}$ is the Euclidean color difference ($\sqrt{\Delta L^{*2}+\Delta a^{*2}+\Delta b^{*2}}$), and $\tau$ is the homogeneity threshold (typical value $\tau = 1.0$, approximately 1 JND).

The homogeneity count for direction $d$ at pixel $(r,c)$:

$$H_d(r,c) = \sum_{(r',c') \in \mathcal{N}(r,c)} \delta_d(r', c')$$

**Intuition:** $H_d$ counts how many neighbors in the $d$-direction candidate image are perceptually close to the center pixel. A higher $H_H$ means the horizontal interpolation yields a smoother neighborhood — more likely aligned with the true edge — so the horizontal result is chosen.

**Notes on $\tau$:** Hirakawa & Parks used $\Delta E_{76}$ (plain Lab Euclidean distance), not $\Delta E_{2000}$. Industrial ISP implementations often use only $\Delta a^{*2}+\Delta b^{*2}$ (ignoring $\Delta L^*$) to reduce computation, equivalent to a chroma-only homogeneity test. The tuning values $\tau \in [2,4]$ at low ISO (common in open-source implementations like LibRaw/dcraw) are empirically derived on 8-bit images and do not directly correspond to the paper's $\tau=1.0$ JND value.

### 1.6 Deep Learning Methods

#### 1.6.1 Gharbi et al. 2016: Joint Demosaicing and Denoising

**Source:** Michaël Gharbi, Gaurav Chaurasia, Sylvain Paris, Frédo Durand, "Deep Joint Demosaicking and Denoising," *ACM SIGGRAPH Asia 2016*, vol. 35, no. 6, Article 191.

Key contributions:
- Unifies demosaicing and denoising as a single end-to-end learning task.
- Introduces a **15-channel input** representation: the Bayer image is decomposed into 15 explicit feature channels that explicitly encode CFA pattern information.
- Uses a fully convolutional network (FCN) with residual connections.
- Trains on a synthetic noisy dataset (MIT-Adobe 5K + Bayer simulation).
- Achieves approximately 43–44 dB PSNR on the Kodak dataset with significantly better noise robustness.

**Why joint learning matters:** In the traditional pipeline, demosaicing precedes denoising. However, demosaicing inherently amplifies the spatial correlation of noise (neighborhood averaging spreads noise), making the subsequent denoising step less effective. Joint optimization can maintain interpolation accuracy while suppressing noise simultaneously.

#### 1.6.2 Later Developments

- **RCAN (Zhang et al. 2018) / RRDB (Wang et al. 2018):** Attention-based residual architectures originally designed for super-resolution, adapted for demosaicing to achieve 44–46 dB PSNR.
- **Transformer-based methods (2021+):** Self-attention mechanisms capture long-range dependencies, yielding better results on uniform textures and fine detail recovery.
- **RAW-to-RGB end-to-end pipelines:** Demosaicing is integrated into a larger end-to-end ISP model rather than treated as a standalone module.

#### 1.6.3 Recent Advances (2023–2025)

**Diffusion models and conditional flow methods:**

- **FlowDemosaic (ECCV 2024, normalizing flow):** Probabilistic demosaicing based on normalizing flows; generates multiple plausible demosaic candidates and obtains the optimal reconstruction via MMSE estimation. Demonstrates significant advantage on high-ISO noisy scenes.
- **DualDn (NeurIPS 2024):** A dual-branch network for joint noise estimation and demosaicing that self-calibrates on real RAW without a noise map input, outperforming the FFDNet+AHD two-step baseline by approximately 1.3 dB PSNR.

**Mamba / State-Space Models (SSM):**

From 2024, Mamba (Selective State Space Model) has been applied to image restoration tasks including demosaicing. Its linear complexity is advantageous over Transformers for 4K-resolution RAW, with inference latency approximately 60% lower than Restormer, making it a promising direction for real-time DL demosaicing on mobile.

**Performance comparison across method generations:**

| Method | PSNR (Kodak σ=0 synthetic Bayer) | Mobile latency | Best-fit scenario |
|--------|----------------------------------|----------------|-------------------|
| AHD (traditional) | ~42 dB | < 1 ms (HW) | General use, weak noise suppression |
| Gharbi 2016 (DL joint) | ~45 dB | 5–15 ms (NPU INT8) | High-ISO noisy scenes |
| Restormer 2022 (Transformer) | ~47 dB | > 50 ms (NPU) | Offline quality-first |
| Mamba-based 2024 | ~46.5 dB | 15–25 ms (NPU) | Real-time / practical future |

### 1.7 Algorithm Comparison

| Algorithm | PSNR on Kodak 24 (dB) | Relative speed | Main artifact | Implementation complexity |
|------|-----------------------|-------------|---------------|------------|
| Bilinear | ~35.5 | 1× (baseline) | Severe false color, blur | Minimal |
| MHC (Malvar 2004) | ~41.5 | ~2× | Mild zipper at strong edges | Low (5×5 convolution) |
| AHD (Hirakawa 2005) | ~43.0 | ~10× | Maze pattern in isotropic textures | Medium (direction selection) |
| DLMMSE (Zhang 2005) | ~42.5 | ~8× | Random texture noise | Medium |
| Menon 2007 | ~43.5 | ~12× | Very minor | Medium-high |
| Gharbi DNN 2016 | ~43.8 | ~50× (GPU) | Learned artifacts | High (inference framework) |
| RCAN/RRDB-Demosaic | ~45.0 | ~200× (GPU) | Learned artifacts | High |

> Note: PSNR values are from original papers and the colour-demosaicing library benchmarks; implementation differences of ±0.5 dB exist.

### 1.8 Coupling with Denoising

Demosaicing is highly sensitive to sensor noise for three reasons:

1. **Direction judgment disturbed by noise:** AHD's homogeneity metric relies on ΔE differences; noise can cause genuinely homogeneous regions to be misclassified as non-homogeneous, leading to incorrect direction selection.
2. **Difference correction amplifies noise:** MHC's second-order difference term $2R_C - R_{LL} - R_{RR}$ is very sensitive to high-frequency noise; at high ISO the correction magnitude should be limited (alpha blending).
3. **Asymmetric noise across color channels:** The R and B channels have lower SNR due to sparser sampling; multi-directional interpolation spreads this color noise.

**In engineering practice**, a light spatial pre-denoising (BNR/NLM) before demosaicing is common, or a joint solution such as Gharbi 2016 is adopted. During tuning, attention must be paid to the trade-off between denoising strength and demosaic sharpness.

---

## §2 Calibration

### 2.1 CFA Pattern Verification

Different camera modules may use different Bayer arrangements (RGGB, BGGR, GRBG, GBRG). An incorrect pattern assumption will completely scramble the color channels. Calibration procedure:

1. **Capture a pure-color target:** Aim at a red, green, or blue LED or color chart patch.
2. **Read a 2×2 sub-array:** Check which position has the highest response value to identify the channel.
3. **Code-based verification:**

```python
import rawpy
import numpy as np

with rawpy.imread('calibration_red.dng') as raw:
    bayer = raw.raw_image_visible.copy()
    # Take the top-left 4×4 region
    patch = bayer[:4, :4]
    print("RAW patch (Red LED):")
    print(patch)
    # Mean of the four sub-pixel positions
    r00 = bayer[0::2, 0::2].mean()  # top-left
    r01 = bayer[0::2, 1::2].mean()  # top-right
    r10 = bayer[1::2, 0::2].mean()  # bottom-left
    r11 = bayer[1::2, 1::2].mean()  # bottom-right
    print(f"TL={r00:.0f}, TR={r01:.0f}, BL={r10:.0f}, BR={r11:.0f}")
    # The position with the highest value is the R channel
    positions = {'TL': r00, 'TR': r01, 'BL': r10, 'BR': r11}
    print("Red position:", max(positions, key=positions.get))
```

### 2.2 Test Charts

| Test target | What it verifies | How to use |
|----------|----------|----------|
| Siemens Star | Resolution limit, onset frequency of zipper artifacts | Observe at which ring the periodic pattern reaches the center |
| ISO 12233 (e-SFR) | MTF curve, color aliasing at Nyquist frequency | Slanted-edge MTF analysis + color channel separation |
| Fine fabric / diagonal weave | Severity of false color | Visual assessment + ΔE measurement |
| Checkerboard (32×32) | Zipper effect | Enlarge 1-pixel-wide black-and-white squares and inspect |
| Uniform color patches | Color accuracy | CIELab ΔE vs. reference values |

### 2.3 Building a Multi-ISO Sample Set

A complete ISO range must be covered to tune the denoising-coupling parameters:

```
ISO 100   → Baseline; verify upper limit of sharpness
ISO 400   → Mild noise; verify lightly coupled denoising
ISO 1600  → Moderate noise; AHD direction judgment becomes unstable
ISO 6400  → Heavy noise; may need to switch to a joint solution
ISO 12800 → Extreme noise; advantage of DL methods becomes apparent
```

At each ISO, capture at least: 3 still-life scenes (low texture, medium texture, high-frequency texture) — at least 15 RAW images total.

---

## §3 Tuning

### 3.1 AHD Direction Threshold

The homogeneity threshold $\tau$ (the ΔE decision boundary) in AHD is the most critical tuning parameter:

| $\tau$ too large | $\tau$ too small |
|-------------|-------------|
| More pixels classified as "homogeneous" | More pixels classified as "non-homogeneous" |
| Direction selection stable in smooth regions | Edge detail better preserved |
| Possible direction error at true edges | Noise regions suffer direction jitter → maze pattern |
| Zipper effect increases | False color decreases |

**Recommended tuning range:**
- Low ISO (100–400): $\tau \in [2, 4]$ ΔE76 units
- Medium ISO (1600): $\tau \in [4, 8]$ (loosen slightly to resist noise interference)
- High ISO (6400+): $\tau \in [8, 16]$, or disable AHD and switch to MHC + joint denoising

### 3.2 Chroma Smoothing Strength

Most ISPs apply a light chroma (CbCr or A/B channel) smoothing pass after demosaicing, controlled by radius $r$ and strength $\alpha$:

```python
# Typical implementation: Gaussian smoothing of Lab chroma channels
from scipy.ndimage import gaussian_filter
lab[:, :, 1] = (1 - alpha) * lab[:, :, 1] + alpha * gaussian_filter(lab[:, :, 1], sigma=r)
lab[:, :, 2] = (1 - alpha) * lab[:, :, 2] + alpha * gaussian_filter(lab[:, :, 2], sigma=r)
```

| Parameter | Low ISO recommendation | High ISO recommendation | Effect |
|------|-------------|-------------|------|
| $r$ (sigma) | 0.5–1.0 | 1.5–3.0 | Larger = smoother |
| $\alpha$ | 0.1–0.2 | 0.4–0.7 | Larger = less false color, less detail |

### 3.3 Joint Denoising Strength vs. ISO

When using a DL joint demosaic-denoise model, the ISO value must be mapped to a noise strength parameter $\sigma$:

```python
# Typical ISO→sigma mapping (must be calibrated for actual sensor)
iso_to_sigma = {100: 1.5, 200: 2.5, 400: 4.0, 800: 6.5, 1600: 10.0, 3200: 16.0}
```

### 3.4 Tuning Order

```
1. Low ISO (100–400): Fix denoising strength = 0, tune AHD threshold alone
   → Goal: Siemens Star as sharp as possible, no false color on diagonal weave

2. Medium ISO (800–3200): Gradually increase joint denoising strength alpha
   → Goal: clean image first, maintain subject sharpness

3. High ISO (6400+): Consider switching algorithm (MHC + strong denoising or DL)
   → Goal: no maze pattern, acceptable colors

4. Full ISO range: Verify smooth parameter transitions across ISO values (no jumps)
```

### 3.5 Algorithm Selection Decision Table

> **Engineering recommendation (mobile ISP context):** In hardware ISPs you will rarely see a raw Bilinear or textbook AHD implementation — every platform ships a proprietary direction-adaptive variant with tuned parameters. The real threshold for introducing DL demosaicing is ISO ≥ 3200, where traditional direction judgment has been corrupted by noise and joint denoising+demosaicing (Gharbi 2016 variant) yields a clear win. If the NPU latency budget is < 5 ms, prefer an MHC variant + dedicated Bayer-domain noise reduction (BNR). With 5–15 ms available, a DL joint solution is worthwhile. Transformer-based methods exceeding 50 ms are effectively offline-only.

| Application scenario | Recommended algorithm | Reason |
|----------|----------|------|
| Low-power / real-time preview | Bilinear | Minimal compute |
| Still photography, standard quality | MHC | Good quality/speed trade-off, hardware-friendly |
| Still photography, high quality | AHD or Menon | Best traditional methods |
| High ISO (ISO ≥ 3200) | Gharbi DNN variant | Joint denoising + demosaicing |
| Mobile flagship, NPU 5–15 ms | DL joint solution | Best quality, requires NPU |

---

## §4 Artifacts

### 4.1 Artifact Classification

| Artifact | Typical cause | Visual appearance | Prone scenarios |
|---------------|--------|----------|----------|----------|
| Zipper Effect | Frequency aliasing along edge direction | Alternating color fringe along black-and-white edges | High-contrast horizontal/vertical lines |
| False Color | High-frequency texture exceeds Nyquist; channel aliasing | Rainbow colors on fabric/diagonal weave | Fine fabric, diagonal stripes, inner rings of Siemens Star |
| Maze Pattern | AHD direction judgment randomized under noise | Block-like color noise at high ISO | ISO 3200+ in uniform regions |
| Color Fringing | Chromatic aberration + demosaic coupling, amplified at edges | Purple/green fringes at bright edges | Blown-highlight edges |
| Moiré | Scene periodic texture resonates with Bayer period | Low-frequency interference fringes | Displays, window screens, fine suits |

### 4.2 Artifact Details

#### 4.2.1 Zipper Effect

**Analysis:** At a horizontal black-and-white edge (e.g., text), two adjacent rows belong to different Bayer rows (one R/G row, one G/B row), each with different missing colors. Linear interpolation samples pixels of different intensities from either side, causing alternating color deviations along the edge.

**Test case:** Generate 1-pixel-wide black-and-white horizontal stripes at Nyquist/2 frequency, apply Bayer sampling, and interpolate with bilinear to observe the color deviation.

**Suppression:** Use gradient-guided interpolation (interpolate along the edge rather than across it); AHD provides significant improvement.

#### 4.2.2 False Color

**Analysis:** When a scene contains texture close to the Bayer Nyquist frequency (one cycle per 2 pixels), different color channels sample that texture at different phases, causing phase differences between reconstructed color channels and producing color fringes.

**Test case:** Photograph diagonal fabric (45° orientation, stripe spacing ~4–8 pixels) and check for color fringes.

**Suppression:** Moderate chroma smoothing; or use direction-adaptive algorithms such as DLMMSE or AHD.

#### 4.2.3 Maze Pattern

**Analysis:** Direction-adaptive algorithms such as AHD randomize their per-pixel direction decisions under high noise, causing random mixing of horizontal and vertical interpolation results. This produces block-like color noise roughly 2 pixels in size, resembling a maze.

**Suppression:** Increase the AHD homogeneity threshold; apply spatial pre-denoising before demosaicing; switch to MHC or a joint DL method at high ISO.

#### 4.2.4 Color Fringing

The primary source is not just demosaicing but also lens chromatic aberration, which demosaicing amplifies. In particular, in blown-highlight (clipping) regions, R/G/B channels saturate at different times, causing color imbalance at edges. Purple fringing (Purple Fringing) requires dedicated post-processing.

---

## §5 Evaluation

### 5.1 Standard Benchmark Datasets

#### Kodak Lossless True Color Image Suite (24 images)
- **Source:** Kodak Inc., publicly available
- **URL:** http://r0k.us/graphics/kodak/
- **Specification:** 24 images at 768×512 or 512×768, losslessly compressed
- **Usage:** Use 24 PNG/PPM images as ground truth, synthesize Bayer, run algorithms, compute PSNR/SSIM
- **Bayer synthesis code:**

```python
def rgb_to_bayer(rgb, pattern='RGGB'):
    """Downsample an RGB image to Bayer RAW"""
    bayer = np.zeros(rgb.shape[:2], dtype=rgb.dtype)
    if pattern == 'RGGB':
        bayer[0::2, 0::2] = rgb[0::2, 0::2, 0]  # R
        bayer[0::2, 1::2] = rgb[0::2, 1::2, 1]  # G
        bayer[1::2, 0::2] = rgb[1::2, 0::2, 1]  # G
        bayer[1::2, 1::2] = rgb[1::2, 1::2, 2]  # B
    return bayer
```

#### McMaster Uncompressed Color Image Dataset (18 images)
- **Source:** McMaster University, publicly available
- **Notes:** Designed specifically for demosaicing evaluation; includes more high-frequency texture images (fabric, plants, buildings)
- **Specification:** 18 images at 500×500
- **Reference:** Zhang et al., "Color Demosaicking via Directional Linear Minimum Mean Square-Error Estimation," IEEE TIP 2005

### 5.2 Published Benchmark Numbers

The table below summarizes PSNR (dB) of major algorithms on the Kodak 24 dataset, sourced from original papers and independent reproductions:

| Algorithm | PSNR (dB) | SSIM | Reference |
|------|-----------|------|----------|
| Bilinear | 35.28 | 0.924 | Multiple survey papers |
| MHC (Malvar 2004) | 41.68 | 0.971 | MSR-TR-2004-138 |
| DLMMSE (Zhang 2005) | 42.63 | 0.976 | IEEE TIP 2005 |
| AHD (Hirakawa 2005) | 43.05 | 0.979 | IEEE TIP 2005 |
| Menon (2007) | 43.63 | 0.981 | Independent reproduction |
| Gharbi DNN (2016) | 43.79 | 0.982 | SIGGRAPH Asia 2016 |
| RCAN-Demosaic | 44.88 | 0.987 | Independent reproduction |

> Note: These values are for synthetic Bayer (noise-free). With added noise, DL methods show a significantly larger advantage.

### 5.3 Building Your Own Test Set

**Steps:**

1. Shoot diverse scenes (include at minimum: faces, architectural lines, textiles, natural vegetation, text)
2. Use a tripod to ensure alignment with a "reference capture" (same frame, or a stereo camera)
3. For scenes where ground truth cannot be obtained, use alternatives to full-reference metrics (PSNR/SSIM):
   - **No-reference metrics (NR-IQA):** BRISQUE, NIQE
   - **Edge fidelity:** MTF measurement computed separately along and perpendicular to edges
   - **Color accuracy:** Measure ΔE against reference values on a color chart

---

## §6 Code

Complete runnable code is in *See §6 Code section for runnable examples.*, including:

- Synthetic Bayer test image generation
- Bilinear interpolation implementation
- Full MHC algorithm implementation (including the 5-point template formula)
- colour-demosaicing library calls (AHD/Menon methods)
- 4-panel comparison visualization (full image + zoomed crops)
- PSNR/SSIM quantitative comparison table

---

## §7 Special CFA Patterns and Demosaicing

### 7.1 Quad-Bayer and Nona-Bayer

Modern high-resolution sensors (Samsung ISOCELL HP3 200MP, Sony IMX989 1-inch) use **Quad-Bayer** (2×2 same-color pixel groups) or **Nona-Bayer** (3×3 groups) to enable pixel binning in low light.

**Remosaic pipeline:**
- **Full-resolution mode:** A hardware remosaic unit converts Quad-Bayer → standard Bayer → standard demosaic.
- **Binned mode:** 4-in-1 binning produces 50MP output from a 200MP sensor; the ISP receives a regular Bayer image at 1/4 resolution.
- Both Qualcomm Spectra and MediaTek Imagiq 790+ include dedicated hardware remosaic engines.

Formula for Quad-Bayer to standard Bayer conversion (example, R channel):

```
R_bayer[i,j] = (R_quad[2i,2j] + R_quad[2i,2j+1] + R_quad[2i+1,2j] + R_quad[2i+1,2j+1]) / 4  # binned mode
R_bayer[i,j] = remosaic(R_quad, neighbors)  # full-res mode, content-adaptive
```

### 7.2 RYYB CFA (Huawei-specific)

Huawei/HiSilicon replaced the two G channels in the standard Bayer pattern with Y (Yellow = R+G) to capture approximately 40% more light.

**The ill-posed problem:** Standard demosaicing assumes that missing channels can be interpolated from neighboring same-color pixels. For RYYB:
- Y = R + G (the yellow filter transmits both red and green light)
- To recover G: G = Y - R (requires knowing R at the same pixel location — a chicken-and-egg problem)
- At pixel locations where only Y is available and R is missing, we must estimate: G&#772; = Y - R&#772;

**HiSilicon's solution:** Train a CNN to map RYYB RAW → RGB directly, bypassing the traditional interpolation step entirely. The network learns the spectral mixing relationship implicitly. As a result, the RYYB ISP pipeline has no "Demosaic" module in the classical sense — the CNN is the demosaic.

**Color accuracy challenge:** Because the Y channel has a broader spectral response than G, the resulting color gamut mapping differs from a standard pipeline, requiring a recalibrated CCM (Color Correction Matrix).

**Reference:** The Huawei P40 series uses the IMX700 with RYYB; see Huawei MWC 2020 press materials.

### 7.3 RCCB CFA (Low-Light Clear Channel)

**RCCB** replaces the two G channels in the standard RGGB pattern with a **C (Clear) channel** — a broadband transparent filter with no wavelength restriction. Clear pixels have significantly higher quantum efficiency than narrow-band G filters, providing a substantial SNR boost in very low-light conditions.

**Typical applications:**
- Automotive night-vision cameras (e.g., OmniVision OX08B40 and similar ADAS sensors)
- Security / surveillance low-illumination imaging
- Some smartphone auxiliary cameras prioritizing light sensitivity over color fidelity

**Demosaicing challenges:**
- Applying standard Bayer algorithms to RCCB directly causes severe color errors, because C carries broadband luminance rather than narrowband green information.
- Common approach: **first synthesize a G estimate from RCCB**, then run standard demosaicing:
  - $\hat{G} = C - \alpha \cdot R - \beta \cdot B$ (where $\alpha$, $\beta$ are determined by spectral calibration)
  - Alternatively, train a CNN to map RCCB RAW → RGB end-to-end, bypassing the intermediate synthesis step.
- The Clear channel responds to R, G, and B simultaneously, so it cannot serve as a direction-guidance channel the way G does in AHD. Standard direction-adaptive algorithms require channel remapping before they can be applied.

**Color calibration note:** The RCCB CCM must be calibrated after RCCB→RGB synthesis. Because the C channel has a broader spectral response, the off-diagonal CCM terms are generally larger than for RGGB, and the matrix is more sensitive to illuminant changes. At least three illuminants (D65 + A + F11) are recommended for calibration.

### 7.4 Platform-Specific Demosaic Summary

| Platform | CFA Type | Demosaic Method | Hardware Unit |
|----------|----------|----------------|---------------|
| Qualcomm Spectra 480/580/680 | RGGB / Quad-Bayer | Directional gradient-guided interpolation (MHC/AHD variant) + dedicated Remosaic engine (Quad→Standard Bayer) | BPS (Bayer Processing Segment) subsystem |
| HiSilicon Kirin (RYYB, Kirin 990/9000) | RYYB | CNN direct RYYB→RGB, bypasses traditional interpolation | NPU (Da Vinci architecture); see §7.2 |
| HiSilicon Kirin (RGGB, Kirin 970/980) | RGGB / Quad-Bayer | Direction-adaptive interpolation (AHD variant) | ISP hardware |
| MediaTek Imagiq 5.0+ (Dimensity 9000/9300, Imagiq 890/990) | RGGB / Quad-Bayer / Nona-Bayer | Adaptive directional interpolation + dedicated Remosaic engine; Dimensity 9300 supports 18-bit RAW ISP | Imagiq hardware unit; tuning via MSDK / ImagiqSimulator |
| Raspberry Pi PiSP (BCM2712) | RGGB | Hardware directional interpolation (MHC-like), fixed in chip; `rpi.demosaic` module in libcamera | PiSP Back End (BE) hardware block |
| OmniVision OX08B40 / automotive ADAS | RCCB | RCCB→G synthesis then standard demosaic, or CNN end-to-end (see §7.3) | Depends on platform integration |

---

> **Engineer's Note: Three Things That Actually Make Demosaicing Painful in Production**
>
> **First: Moire is not demosaic's fault, but demosaic always gets blamed.** When you photograph fine fabrics (shirts, window screens) and see rainbow moire, the root cause is undersampling aliasing between sensor pixel pitch and fabric frequency — this already happened at the Bayer sampling stage. Demosaicing merely "reveals" the aliased frequencies; it did not create them. The most common factory-floor mistake: swap in stronger AHD parameters, moire persists, so you start adjusting LSC, then CCM, and only after going full circle do you admit it's a physical limit. The genuinely effective remedy is a frequency-adaptive low-pass pre-filter before demosaicing, or a post-demosaic local desaturation mask triggered by a moire detector (at the cost of that region becoming gray).
>
> **Second: AHD's advantage disappears in low-texture areas and gets worse under heavy noise.** AHD's direction-adaptive voting relies on local homogeneity. At high ISO, noise corrupts the homogeneity metric in smooth regions, misclassification rate rises, and the algorithm introduces more false color than it would have with a simpler method. The standard engineering fix on mobile ISPs is to run a lightweight RAW-domain pre-denoiser (bilateral NR or BM3D-lite) before demosaicing to lift the SNR, and only then feed AHD. Qualcomm's BPS subsystem is designed exactly in this order — RAW NR → Demosaic, not the reverse. MediaTek Imagiq performs a similar "noise-aware direction selection" optimization in the same pipeline.
>
> **Third: Joint Demosaic+Denoise (JDD) is architecturally correct but expensive to validate.** After Gharbi et al. 2016 (SIGGRAPH Asia), many vendors followed with DL JDD pipelines (Huawei XD-Fusion early versions, OPPO MariSilicon X RAW processing). The real production obstacle is training data: a JDD network needs real RAW pairs from the same sensor, and changing sensors means re-collecting data and re-training, with a validation cycle far longer than re-tuning AHD parameters. So most production devices today use traditional AHD for daylight and switch to JDD for night — a mode-switching classifier gates between them rather than running JDD end-to-end.
>
> *References: Gharbi et al., "Deep Joint Demosaicking and Denoising", ACM SIGGRAPH Asia, 2016.*

---

## Engineering Recommendations

The core of demosaicing engineering decisions is matching **algorithm — scene — compute budget**. No single solution fits all scenarios.

| Scenario | Recommended approach | Typical constraint | Notes |
|----------|---------------------|--------------------|-------|
| Daytime normal light, real-time preview | AHD / MHC | < 1 ms/frame (720p) | Built into Qualcomm BPS and MediaTek ISP; no extra configuration needed |
| ISO > 800, low-light capture | RAW NR → AHD | NR adds 0.5–2 ms | Lightweight RAW-domain denoising (bilateral NR or BM3D-lite) first to raise SNR, then AHD |
| Super night mode / offline RAW post-processing | JDD network (e.g., NAFNet-JDD) | 5–30 ms/frame, NPU deployment | Requires real RAW pair training data for the sensor; re-train when sensor changes |
| Pre-processing for super-resolution | Traditional AHD (edge-preserving) | — | Do not use bilinear — it introduces upstream blur that SR networks cannot recover |
| Low-end device, compute-limited | Bilinear | < 0.2 ms/frame | Accept false color and zipper; recover apparent sharpness with post-EE |

**Key debugging points:**

- **Evaluate false color on a color chart first:** Photograph the ColorChecker along the diagonal high-frequency edge, looking for purple fringing (zipper) at red-green boundaries. AHD's canonical failure is false color at 45° diagonal edges, not at 0°/90° straight edges — shooting brick walls alone will miss this.
- **Moire is a demosaic failure signal, but the cause may be upstream:** If brick/grid textures show colored moire, first check whether the LSC gain map is introducing local frequency modulation, and whether the AA filter is too weak. Both upstream problems will prevent demosaicing — regardless of algorithm — from eliminating the moire.
- **JDD acceptance testing cannot rely on PSNR alone:** JDD simultaneously denoises and demosaics, and can over-smooth high-frequency details (hair, fabric texture). PSNR may be high while MTF50 is significantly below a plain AHD result. Acceptance must include both MTF50 and PSNR; both must clear the threshold.

---

## §8 Glossary

**Color Filter Array (CFA) / Bayer Array**
The array of micro-filters placed over each pixel of a CMOS/CCD image sensor, enabling a single sensor to capture color. The most common Bayer pattern is RGGB (2×2 unit: R top-left, G top-right, G bottom-left, B bottom-right). Green pixels occupy 1/2 of the array to match the human visual system's higher luminance sensitivity. Each pixel records only one color; the missing two must be recovered by demosaicing.

**Demosaicing / Bayer Interpolation**
The process of reconstructing a full H×W×3 RGB image from a sparse single-channel Bayer RAW. Because R/B channels are 2×2 downsampled, their Nyquist frequency is half that of G, making high-frequency texture regions prone to false color and zipper artifacts. Algorithm families range from bilinear interpolation (1st gen) to direction-adaptive methods (3rd gen) to end-to-end deep learning (4th gen).

**Bilinear Interpolation**
The simplest demosaicing baseline: each missing color is estimated as the arithmetic average of surrounding same-color pixels. Equivalent to independent low-pass filtering per channel. PSNR on Kodak 24 (noise-free synthetic Bayer) is approximately 35.28 dB. Used as a comparison baseline or in low-power real-time preview contexts.

**MHC Algorithm (Malvar-He-Cutler 2004)**
A high-quality linear interpolation method from Microsoft Research, presented at ICASSP 2004. Core insight: **color difference smoothness** — the differences G-R and G-B vary much more slowly than the absolute channel values. Starting from a bilinear estimate, MHC adds a correction term based on the second-order finite difference (Laplacian) of the known channel. Implementable as a fixed 5×5 convolution kernel. PSNR on Kodak 24 is approximately 41.68 dB.

**AHD Algorithm (Adaptive Homogeneity-Directed Demosaicing, Hirakawa & Parks 2005)**
Direction-adaptive interpolation from IEEE TIP 2005. Steps: (1) independently demosaic in horizontal and vertical directions to produce two candidate RGB images; (2) convert to CIELab perceptually uniform space; (3) count homogeneous pixels in a 5×5 window (original paper specification) for each direction; (4) select the direction with the higher homogeneity count. PSNR on Kodak 24 is approximately 43.05 dB. Significantly reduces zipper artifacts, but can produce maze patterns under high noise.

**False Color**
When scene texture frequency approaches the Bayer Nyquist limit (one cycle per 2 pixels), different color channels sample the same texture at different phases. The resulting phase difference between reconstructed channels produces color fringes. Typical appearance: rainbow stripes on fine fabric, diagonal weaves, or the inner rings of a Siemens Star. Mitigation: chroma smoothing, or direction-adaptive algorithms (AHD/DLMMSE).

**Zipper Effect**
Alternating color fringes along high-contrast horizontal/vertical edges (e.g., text, checkerboard), resembling a zipper. Caused by adjacent Bayer rows having different color arrangements (one R/G row, one G/B row); linear interpolation samples pixels of different color intensities from either side of the edge, producing alternating color deviation along it. Gradient-guided interpolation (along the edge rather than across it) substantially reduces this artifact.

**Maze Pattern**
At high ISO, direction-adaptive algorithms like AHD randomize their per-pixel direction decisions due to noise, randomly mixing horizontal and vertical interpolation results. This produces block-like color noise approximately 2 pixels in size, resembling a maze. Mitigated by raising the AHD homogeneity threshold, applying spatial pre-denoising before demosaicing, or switching to MHC + joint denoising or a DL method at high ISO.

**Gharbi 2016 (Deep Joint Demosaicking and Denoising)**
An end-to-end joint demosaicing and denoising framework from ACM SIGGRAPH Asia 2016. Unifies demosaic and denoise as a single learning task using a multi-channel input representation of the Bayer observation, optimized via a residual fully-convolutional network. The primary contribution and representative experimental results are in the **noisy** condition; its ~43.79 dB PSNR on Kodak 24 noise-free synthetic Bayer is a supplementary result, not the main claim.

**Quad-Bayer / Remosaic**
A 2×2 same-color pixel grouping CFA structure used in modern high-resolution sensors (Samsung ISOCELL HP3, Sony IMX989, etc.) to enable 4-in-1 pixel binning (Binning) for SNR improvement in low light. In full-resolution capture mode, a hardware Remosaic engine converts the Quad-Bayer pattern back to standard RGGB Bayer before the standard demosaic pipeline. Both Qualcomm Spectra and MediaTek Imagiq 790+ include dedicated hardware Remosaic engines.

**RYYB CFA**
A non-standard CFA used by Huawei/HiSilicon starting with the P30 series, replacing the two G channels in RGGB with Y (yellow filter, passing both red and green light). The vendor claims approximately 40% more light capture than RGGB (this is a system-level claim under specific test conditions; actual gain depends on filter spectral transmittance, sensor QE, and scene spectrum). The Y channel simultaneously contains R+G signals, making traditional demosaicing frameworks inapplicable; typically a CNN is trained to map RYYB RAW → RGB directly.

**Color Difference Smoothness**
A statistical prior of natural images: the color difference signals (G-R, G-B) between adjacent pixels are smoother and slower-varying than the absolute color values. The MHC algorithm exploits this prior by using the second-order finite difference (Laplacian) of a known channel to correct the bilinear estimate of a missing channel, significantly improving interpolation quality without additional computational complexity.

**Kodak 24 Dataset**
A set of 24 full-color lossless images (768×512 or 512×768) released by Kodak Inc., the standard benchmark dataset for demosaicing evaluation. Usage: synthesize Bayer RAW from PNG/PPM images (via `rgb_to_bayer`), run demosaicing algorithms, compute PSNR/SSIM against the originals. Note: this is a noise-free synthetic Bayer benchmark; it does not reflect algorithm performance under real RAW noise conditions, where the advantage of deep learning methods is substantially larger.

---

## References

### Core Papers

1. **Malvar, H. S., He, L., & Cutler, R.** (2004). High-quality linear interpolation for demosaicing of Bayer-patterned color images. *IEEE ICASSP 2004*. Microsoft Research Technical Report MSR-TR-2004-138. Available: https://www.microsoft.com/en-us/research/publication/high-quality-linear-interpolation-for-demosaicing-of-bayer-patterned-color-images/

2. **Hirakawa, K., & Parks, T. W.** (2005). Adaptive homogeneity-directed demosaicing algorithm. *IEEE Transactions on Image Processing*, 14(3), 360–369. DOI: 10.1109/TIP.2004.838691

3. **Zhang, L., Wu, X., Buades, A., & Li, X.** (2011). Color demosaicking by local directional interpolation and nonlocal adaptive thresholding. *Journal of Electronic Imaging*, 20(2), 023016.

4. **Gharbi, M., Chaurasia, G., Paris, S., & Durand, F.** (2016). Deep joint demosaicking and denoising. *ACM Transactions on Graphics (SIGGRAPH Asia 2016)*, 35(6), Article 191. DOI: 10.1145/2980179.2982399. Available: https://groups.csail.mit.edu/graphics/demosaicnet/

5. **Menon, D., Andriani, S., & Calvagno, G.** (2007). Demosaicing with directional filtering and a posteriori decision. *IEEE Transactions on Image Processing*, 16(1), 132–141.

6. **Zhang, L., & Wu, X.** (2005). Color demosaicking via directional linear minimum mean square-error estimation. *IEEE Transactions on Image Processing*, 14(12), 2167–2178.

7. **Bayer, B. E.** (1976). Color imaging array. *U.S. Patent 3,971,065*, filed March 7, 1975, issued July 20, 1976.

### Survey Papers

8. **Mihoubi, S., Losson, O., Mathon, B., & Macaire, L.** (2018). Multispectral demosaicing using pseudo-panchromatic image. *IEEE Transactions on Computational Imaging*, 3(4), 982–995.

9. **Monno, Y., Kikuchi, S., Tanaka, M., & Okutomi, M.** (2015). A practical one-shot multispectral imaging system using a single image sensor. *IEEE Transactions on Image Processing*, 24(10), 3048–3059.

### Deep Learning Methods

10. **Zhang, Y., Li, K., Li, K., Wang, L., Zhong, B., & Fu, Y.** (2018). Image super-resolution using very deep residual channel attention networks (RCAN). *ECCV 2018*. arXiv:1807.02758.

11. **Wang, X., Yu, K., Wu, S., Gu, J., Liu, Y., Dong, C., ... & Change Loy, C.** (2018). ESRGAN: Enhanced super-resolution generative adversarial networks. *ECCV 2018 Workshops*. (RRDB backbone).

### Datasets and Tools

12. **Kodak Lossless True Color Image Suite** (24 images). Available: http://r0k.us/graphics/kodak/

13. **McMaster University Uncompressed Color Image Database** (18 images). Available: https://www4.comp.polyu.edu.hk/~cslzhang/CDM_Dataset.htm

14. **colour-demosaicing** (Python library). Available: https://github.com/colour-science/colour-demosaicing. Implements Malvar 2004, Menon 2007, DDFAPD, and others.

15. **rawpy** (Python RAW processor). Available: https://github.com/letmaik/rawpy. Wraps LibRaw with access to dcraw demosaic algorithms.

### Courses and Tutorials

16. **Srinivasa Narasimhan**, CMU 15-463/663/862 Computational Photography, Lecture on Demosaicing. Available: http://www.cs.cmu.edu/afs/cs/academic/class/15463-f17/www/lec_slides/

17. **Marc Levoy**, Stanford CS 448A Digital Photography (archived). Available: http://graphics.stanford.edu/courses/cs448a-08-fall/

18. **Frédéric Morain-Nicolier**, "Demosaicing Algorithms" technical report, Université de Reims. (Overview of classical methods.)

---

*End of Chapter 19*
