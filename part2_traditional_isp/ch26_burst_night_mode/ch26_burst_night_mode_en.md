# Vol. 2 Ch. 26: Multi-Frame Burst Synthesis and Night Mode Algorithms

> **Scope:** This chapter focuses on traditional (non-DL) multi-frame Burst Photography (多帧合成) pipelines — handheld motion alignment, pixel-level fusion weights, and night scene brightness enhancement. It covers the Hasinoff algorithm from Google HDR+ and the motion-robust design of Handheld HDR. Deep learning multi-frame architectures are covered in Vol. 3 Ch. 11.
> **Prerequisites:** Vol. 2 Ch. 11 (HDR Frame Merging); Vol. 1 Ch. 4 (Noise Models)
> **Target Readers:** Algorithm engineers

---

## Table of Contents

1. [Night Scene Noise Models](#1-night-scene-noise-models)
2. [Burst Alignment Algorithms](#2-burst-alignment-algorithms)
3. [Fusion Weight Design](#3-fusion-weight-design)
4. [Common Artifacts and Issues](#4-common-artifacts-and-issues)
5. [Evaluation Methods](#5-evaluation-methods)
6. [Code Examples](#6-code-examples)
7. [References](#7-references)
8. [Glossary](#8-glossary)

---

## §1 Night Scene Noise Models

### 1.1 Poisson-Gaussian Noise Model in Low-Light Conditions

In engineering analysis, sensor noise is typically decomposed into two independent components whose sum determines the signal-to-noise characteristics of a night scene RAW image.

**Photon Shot Noise (光子散粒噪声):**
The arrival of photons at sensor pixels follows a Poisson Distribution (泊松分布). Let the mean photon count be μ (corresponding to a linear pixel value); the variance of shot noise is then:

```
σ²_shot = μ
```

A key property of the Poisson process: the weaker the signal (darker the region), the larger the relative proportion of shot noise (i.e., noise/signal).

**Read-out Noise (读出噪声) and Dark Current (暗电流):**
The additive white Gaussian noise (AWGN) introduced by sensor circuitry consists of amplifier thermal noise, ADC quantization error, etc., with variance σ²_read. Dark current contributes additional shot noise under long exposure, typically 0.1–10 electrons/pixel/s (varying with temperature).

**Complete Poisson-Gaussian Noise Model (Heteroscedastic Gaussian Approximation):**
When there are sufficient photoelectrons (μ > 30), the Poisson distribution approximates a Gaussian distribution, and the total noise variance is:

```
σ²_total(μ) = α × μ + σ²_read
```

where α is a correction term for the inverse quantum efficiency, typically determined during the hardware calibration stage by shooting a flat field (Flat Field). The `NoiseProfile` field in DNG format stores [α, σ²_read] parameters directly.

### 1.2 Low-Light Signal-to-Noise Ratio Analysis

In a single-frame exposure, the Signal-to-Noise Ratio (SNR, 信噪比) at a pixel is:

```
SNR_single = μ / σ_total = μ / sqrt(α×μ + σ²_read)
```

In the limit of abundant photon counts (shot noise dominated, μ >> σ²_read/α):

```
SNR_single ≈ μ / sqrt(α×μ) = sqrt(μ/α)
```

SNR is proportional to the square root of the signal amplitude — this is the fundamental physical limitation of photon detection.

### 1.3 SNR Gain from Burst Stacking

The core SNR gain principle of multi-frame Burst acquisition: averaging N frames of aligned independent identically distributed frames causes the signal to add linearly while noise adds in quadrature (root mean square), so:

```
SNR_burst_N = (N × μ) / sqrt(N × σ²_total) = sqrt(N) × SNR_single
```

**SNR gain: ∝ √N** — shooting 4 frames yields a 2× (6 dB) SNR improvement; 16 frames yields a 4× (12 dB) improvement.

**Practical constraints:**
- Handheld shake causes inter-frame alignment errors, which reduce the effective SNR gain
- Total exposure time for N frames = N × T_single; there is a risk of ghost artifacts from subject motion
- Systematic luminance bias from inconsistent inter-frame ISO/exposure (e.g., AE adjustments)

**Google HDR+'s design choices** (Hasinoff et al., SIGGRAPH 2016):
Choosing multiple short-exposure frames (e.g., N=4–15 frames, each approximately 1/30s–1/60s) rather than a single long exposure, for the following reasons:
1. Short exposures reduce motion blur within a single frame
2. Short exposures reduce the probability of highlight clipping
3. Distributed high-ISO short exposures are superior to a single low-ISO long exposure because read-out noise is added only once (not N times)

---

## §2 Burst Alignment Algorithms

### 2.1 Engineering Challenges of Image Alignment

A handheld Burst sequence faces the following types of motion, each requiring a different alignment approach:

| Motion Type | Frequency Range | Primary Source | Alignment Difficulty |
|-------------|-----------------|----------------|----------------------|
| Global translation | Low-frequency (< 5Hz) | Handheld shake | Low (global estimation) |
| Global rotation | Low-frequency | Wrist twist | Medium (affine estimation) |
| Local motion (foreground) | Arbitrary | Subject movement | High (optical flow / occlusion) |
| Rolling shutter (RS) distortion | Intra-frame | CMOS row-by-row readout | High (RS correction) |

### 2.2 Pyramid Hierarchical Lucas-Kanade Optical Flow

**Lucas-Kanade (LK) Optical Flow** (Lucas & Kanade, 1981) assumes that a local pixel patch undergoes only translational motion between two frames, and solves for the displacement vector by minimizing the photometric error:

```
min_{d} Σ_{p∈Ω} (I₁(p + d) - I₀(p))²
```

where Ω is the local window centered on a feature point, and d = (dx, dy) is the displacement to be estimated.

A first-order Taylor expansion of the above (brightness constancy assumption):

```
I₁(p + d) ≈ I₀(p) + ∇I₀(p) · d
```

Setting the residual to zero gives a linear system (least-squares solution):

```
[Σ(Ix²)   Σ(Ix·Iy)] [dx]   [-Σ(Ix·It)]
[Σ(Ix·Iy) Σ(Iy²) ] [dy] = [-Σ(Iy·It)]

where: Ix, Iy = spatial gradients, It = I₁(p) - I₀(p) temporal difference
```

**Image Pyramid (图像金字塔) hierarchical processing:**
Single-scale LK optical flow can only handle sub-pixel to 5-pixel displacements. Handheld shake can cause 20–50 pixel displacements within a 100 ms Burst interval, requiring coarse-scale large-displacement estimation followed by layer-by-layer refinement.

Typical pyramid settings:
- Levels: 3–5
- Scale factor: 0.5 (resolution halved at each level)
- Iterations per level: 5–10
- Window size: 15×15 to 21×21

### 2.3 The Hasinoff Method: HDR+ Merge Kernel

The core pipeline of Google HDR+ (Hasinoff et al., *ACM SIGGRAPH Asia*, 2016) first performs **pyramid L2 spatial alignment (global frame alignment)** across all frames to compensate for handheld shake, then applies frequency-domain tile-by-tile weighted merging on small tiles (typically 64×64 pixels), adaptively handling local motion through per-tile merge weights. Moving tiles receive weights near 0 (excluded from merging); static tiles receive weights near 1 (fully merged for SNR accumulation).

The innovation lies in the frequency-domain adaptive merge kernel — not in abandoning global alignment. In fact, the global pyramid alignment is an indispensable preceding step; without it, inter-frame offsets of tens of pixels would invalidate tile-level frequency comparison.

**Core idea:**
The reference frame and the frame to be merged are each processed by DFT on small tiles (typically 64×64 pixels); the similarity of the two in the frequency domain is compared, and merging weights are determined by the degree of similarity. For a moving tile, the coefficient approaches 0 (no merging); for a static tile, the coefficient approaches 1 (full merging).

**Hasinoff merge kernel weight formula (simplified):**

```
w(f) = 1 / (1 + (‖A(f) - B(f)‖² / (σ²(f) × c))^p)

where:
  A(f), B(f): DFT coefficients of the reference and candidate frames at frequency f
  σ²(f):      Noise power spectrum at that frequency (estimated from the noise model)
  c:          Constant controlling the merge threshold (larger = more aggressive merging)
  p:          Soft-threshold steepness (typical p=4 is the original Hasinoff setting)
```

**Key engineering design choices:**
- The noise power spectrum σ²(f) is derived from the sensor noise model (DNG NoiseProfile); only frequency-whitened differences have statistical meaning
- Tiles use 50% overlap and are windowed with a Hanning Window (汉宁窗) to avoid block-boundary effects
- Reference frame selection: typically the sharpest frame (ranked by Laplacian variance; the frame with the highest Laplacian sharpness is selected as the merge reference)

### 2.4 Tile-Based Frequency-Domain Alignment (Handheld Multi-Frame SR)

Unlike the frequency-domain merging of the Hasinoff method, Wronski et al. (*Handheld Multi-Frame Super-Resolution*, SIGGRAPH 2019) first performs accurate optical flow estimation at the tile level, then merges in the spatial domain.

**Tile alignment workflow:**
1. Estimate global motion vectors using LK optical flow at the low-resolution layer (1/8 of the original image)
2. At the mid-resolution layer (1/4 size), refine tile-wise using the global vector as the initial value (tile size: 32×32)
3. Further refinement at the half-resolution layer (1/2 size)
4. Perform consistency checks on the displacement vector for each tile (neighborhood smoothness constraint) and discard outliers

**Motion occlusion detection:**
For foreground object motion regions, the tile difference between the reference frame and the candidate frame is large; even with accurate optical flow estimation, seamless merging is not possible. Occlusion detection identifies such regions using the following metric:

```
occlusion_score(t) = mean(|I_ref(t) - I_alt(t + d_t)|²) / σ²_noise

If occlusion_score > threshold_occ, the tile is classified as a motion/occlusion region
```

The merging weight for occluded regions is reduced to 0, using only the reference frame pixels.

---

## §3 Fusion Weight Design

### 3.1 Inverse Variance Weighting (IVW): Optimal Linear Estimation

In the statistical optimality (MLE, Maximum Likelihood Estimation) framework, if observations at the same position across frames are mutually independent and Gaussian distributed, the optimal combined estimate is **Inverse Variance Weighting (IVW, 逆方差加权)**:

```
î(p) = Σ_k [w_k(p) × I_k(p)] / Σ_k w_k(p)

where: w_k(p) = 1 / σ²_k(p) (inverse noise variance)
```

For the Poisson-Gaussian noise model σ²_k(p) = α × I_k(p) + σ²_read, the inverse variance weights vary dynamically with pixel luminance:
- Bright areas (large μ, shot noise dominated): weights across frames are nearly equal; simple averaging suffices
- Dark areas (small μ, read-out noise dominated): frames with higher SNR (brighter) receive greater weight

The SNR improvement ceiling of IVW is still √N, but when inter-frame exposure is not perfectly consistent (e.g., slight AE jitter), IVW outperforms simple averaging because it naturally reduces the contribution of low-SNR frames.

### 3.2 Motion Region Down-Weighting: Ghost Suppression

Pure IVW produces **ghost artifacts (鬼影)** at moving objects: moving pixels are at different positions across frames, and stacking them produces semi-transparent double exposures.

**Motion detection and weight adjustment:**

```
motion_diff(p) = |I_k(p) - I_ref(p)|²  (inter-frame difference after alignment)

motion_weight(p) = exp(-motion_diff(p) / (2 × σ²_motion))

total_weight_k(p) = ivw_weight_k(p) × motion_weight_k(p)
```

where σ²_motion is the soft threshold for motion weighting, determining the tolerance for motion:
- σ²_motion too small: ghost suppression is strong, but static texture regions also lose frames, reducing SNR gain
- σ²_motion too large: ghosts are visible, but SNR gain is maximized

**Elegance of the original Hasinoff method:** The frequency-domain merge weights naturally reduce the weight of moving tiles to near zero without explicit motion detection — this is the primary engineering advantage of that method.

### 3.3 Extremal Detection (Robustness Enhancement for the Hasinoff Merge Kernel)

Building on the Hasinoff method, a common enhancement is **extremal pixel detection**: if a pixel value in a given frame is clearly higher (overexposed false color) or clearly lower (random hot pixel, cosmic ray) than in all other Burst frames, the contribution of that frame at that pixel is directly excluded.

```python
def extremal_weight(frames: np.ndarray, sigma_clip: float = 3.0) -> np.ndarray:
    """
    基于极值检测的权重遮罩（沿帧维度）
    frames: shape (N, H, W, C)
    返回: weight mask shape (N, H, W, C)，0 或 1
    """
    median = np.median(frames, axis=0, keepdims=True)
    mad = np.median(np.abs(frames - median), axis=0, keepdims=True) + 1e-6
    z_score = np.abs(frames - median) / (mad * 1.4826)
    return (z_score < sigma_clip).astype(np.float32)
```

Median Absolute Deviation (MAD, 中位绝对偏差) is more robust to outliers than standard deviation, and is a commonly used tool for detecting anomalous frames in Burst fusion.

---

## §4 Common Artifacts and Issues

### 4.1 Ghost Artifacts (运动鬼影)

**Symptom description:**
Moving foreground objects (people, cars, leaves) in the merged image appear as transparent double exposures, typically manifesting as motion-directional blurring or semi-transparent overlapping images.

**Root cause:**
The alignment algorithm (global rigid-body transform) cannot achieve accurate pixel-level alignment for non-rigid, locally moving regions; even with accurate optical flow, occluded regions cannot be meaningfully corresponded.

**Quantitative metrics:**
The visibility of ghost artifacts is directly related to the magnitude of motion, the number of frames N, and the fusion weight strategy. In the laboratory, a "Ghost Rate" (鬼影率) is typically used for quantification: in a controlled scene with annotated motion regions, count the ratio of ghost pixels to the total moving foreground pixel area in the fusion result.

**Engineering countermeasures:**
- Apply motion down-weighting (Section 3.2), or the adaptive weights of Hasinoff's frequency-domain merging
- Add motion occlusion detection; use only the reference frame for occluded regions
- Limit the number of Burst frames (N ≤ 8) to balance SNR gain against ghost risk

### 4.2 Residual Low-Frequency Handheld Shake

**Symptom description:**
Even with optical flow alignment, blurring appears at image edges, typically manifesting as "double edges" (sub-pixel misalignment) along straight lines.

**Root cause:**
- The low-frequency component (1–5 Hz human physiological tremor) of handheld shake is large in amplitude and can be accurately estimated by pyramid optical flow
- However, high-frequency shake (e.g., camera shutter vibration, 50–200 Hz) can cause 1–3 pixel displacement within short inter-frame intervals (33 ms), which is difficult to model accurately with a simple motion model
- In Rolling Shutter (RS, 滚动快门) CMOS sensors, different rows are exposed at different times during the row-by-row readout, causing the "jello effect" during motion that cannot be compensated by a simple global displacement

**Engineering countermeasures:**
- RS correction: use IMU (gyroscope) data to apply independent RS correction per row (see Vol. 2 Ch. 23, EIS/OIS)
- Use smaller tile sizes (16×16 or smaller) for improved local motion estimation accuracy
- Apply mild Gaussian pre-filtering (σ = 0.5–0.8 pixels) to the merged image to remove high-frequency noise from sub-pixel alignment residuals

### 4.3 Inter-Frame Exposure Inconsistency (ISO Jumps)

**Symptom description:**
During Burst acquisition, the AE algorithm may experience ISO jumps in rapidly changing scenes (e.g., a subject quickly entering the frame), causing inconsistent baseline noise levels between adjacent frames. The merged image exhibits localized luminance patches, especially pronounced in motion regions.

**Engineering countermeasures:**
- Lock AE/ISO during Burst acquisition (AE Lock), fixing all frames to the exposure parameters of the reference frame
- Inter-frame exposure normalization: if there are still minor inter-frame exposure differences, normalize each frame's luminance before merging using the correction factor k_i = 1/t_i
- For HDR Burst (intentionally using different exposures), the inter-frame fusion weights must include an exposure-level correction term

---

## §5 Evaluation Methods

### 5.1 Alignment Accuracy Assessment (PSNR/SSIM)

The standard method for evaluating Burst alignment quality is to compute PSNR and SSIM against the ideal alignment (Ground Truth).

**Laboratory evaluation scheme (controlled scene):**
1. Use a mechanical shooting platform (eliminating handheld shake) to shoot a multi-frame perfectly aligned baseline sequence
2. Apply known displacements (integer-pixel translation, for validation) or known affine transforms (for full-pipeline validation) to the baseline sequence
3. Use the alignment algorithm under test to recover the displacement, and compute PSNR/SSIM against the original image:
   - PSNR > 40 dB: Alignment error is essentially invisible
   - PSNR 35–40 dB: Slight alignment error, visible upon careful inspection
   - PSNR < 35 dB: Obvious alignment residuals

### 5.2 Night Scene SNR Improvement (dB)

For quantifying SNR improvement in actual night scenes:

1. Shoot a series of Burst frames (N=8 or 16), plus a high-ISO single-frame reference of the scene
2. Extract a uniform region (flat texture, e.g., night sky background) from the Burst merged result and the single frame
3. Compute local mean (μ) and standard deviation (σ); SNR (dB) = 20×log10(μ/σ)
4. SNR gain = SNR_burst − SNR_single
5. Theoretical ceiling: 10×log10(N) dB (e.g., N=8 gives a theoretical ceiling of ≈ 9 dB)

**Empirical values from mid-to-high-end smartphone platforms:**
- N=4 frame aligned merge: SNR gain approximately 4–5 dB (theoretical ceiling 6 dB; gap due to alignment errors)
- N=8 frames: gain approximately 7–8 dB (theoretical ceiling 9 dB)
- N=16 frames: gain approximately 10–11 dB (theoretical ceiling 12 dB); ghost risk rises significantly

### 5.3 Ghost Rate Quantification

**Standard scene design:**
1. Design a controlled scene with "static background + known moving foreground" (e.g., a moving target)
2. Shoot a Burst sequence; the reference frame is a static frame in which the moving object is sharp
3. Manually annotate the merged result (or use a motion segmentation algorithm as aid), counting the ghost pixel ratio:
   ```
   Ghost Rate = (number of ghost pixels) / (total moving foreground pixels) × 100%
   ```
4. Evaluation criteria (correlated with subjective visibility):
   - Ghost Rate < 5%: Excellent; essentially invisible
   - Ghost Rate 5–15%: Good; visible upon careful inspection
   - Ghost Rate > 15%: Obvious ghosting; optimization required

---

## §6 Code Examples

The following Python code implements pyramid optical flow alignment and inverse variance weighting Burst fusion, and can be run directly.

```python
"""
多帧 Burst 合成演示：金字塔光流对齐 + 逆方差加权融合
依赖：numpy, scipy (pip install numpy scipy)
"""

import numpy as np
from scipy.ndimage import gaussian_filter, zoom, map_coordinates


# =============================================================================
# 1. 图像金字塔构建
# =============================================================================

def build_pyramid(image: np.ndarray, levels: int = 4) -> list:
    """
    构建高斯图像金字塔

    参数:
        image:  输入图像，shape (H, W) 或 (H, W, C)，float32
        levels: 金字塔层数（包含原始尺寸）
    返回:
        pyramid: list of arrays，pyramid[0] 为最粗分辨率
    """
    pyramid = [image]
    for _ in range(levels - 1):
        # 高斯低通滤波后降采样至 1/2
        blurred = gaussian_filter(pyramid[-1], sigma=1.0)
        if blurred.ndim == 3:
            downsampled = blurred[::2, ::2, :]
        else:
            downsampled = blurred[::2, ::2]
        pyramid.append(downsampled)
    return list(reversed(pyramid))  # pyramid[0] = 最粗，pyramid[-1] = 最细


# =============================================================================
# 2. 单尺度 Lucas-Kanade 光流（简化平移估计）
# =============================================================================

def lk_optical_flow_patch(ref: np.ndarray, alt: np.ndarray,
                           init_dx: float = 0.0, init_dy: float = 0.0,
                           iterations: int = 8,
                           window_size: int = 15) -> tuple:
    """
    全局平移估计（简化 Lucas-Kanade，用于演示）

    参数:
        ref, alt:    参考帧与待对齐帧，shape (H, W)，float32
        init_dx/dy:  初始位移猜测（来自粗尺度）
        iterations:  迭代次数
        window_size: 计算梯度的窗口半径（未使用，全图计算）
    返回:
        (dx, dy): 估计位移
    """
    dx, dy = float(init_dx), float(init_dy)
    H, W = ref.shape

    for _ in range(iterations):
        # 将 alt 按当前估计平移
        coords_y = np.arange(H, dtype=np.float32) - dy
        coords_x = np.arange(W, dtype=np.float32) - dx
        yy, xx = np.meshgrid(coords_y, coords_x, indexing='ij')
        # 双线性插值采样
        coords = np.array([yy.ravel(), xx.ravel()])
        alt_warped = map_coordinates(alt, coords, order=1,
                                     mode='reflect').reshape(H, W)

        # 计算空间梯度（Sobel 近似）
        Ix = np.gradient(ref, axis=1)
        Iy = np.gradient(ref, axis=0)
        It = alt_warped - ref  # 时间差分

        # LK 矩阵（全图累加，等同于仿射/平移全局估计）
        A11 = (Ix * Ix).sum()
        A12 = (Ix * Iy).sum()
        A22 = (Iy * Iy).sum()
        b1  = -(Ix * It).sum()
        b2  = -(Iy * It).sum()

        det = A11 * A22 - A12 ** 2
        if abs(det) < 1e-10:
            break

        ddx = (A22 * b1 - A12 * b2) / det
        ddy = (A11 * b2 - A12 * b1) / det

        dx += ddx
        dy += ddy

        if abs(ddx) < 0.01 and abs(ddy) < 0.01:
            break

    return dx, dy


# =============================================================================
# 3. 金字塔层次对齐
# =============================================================================

def pyramid_align(ref: np.ndarray, alt: np.ndarray,
                  levels: int = 4) -> tuple:
    """
    金字塔层次光流对齐，返回全局平移位移 (dx, dy)

    参数:
        ref, alt:  单通道参考帧与待对齐帧，shape (H, W)，float32
        levels:    金字塔层数
    返回:
        (dx, dy): 从 alt 到 ref 的平移位移（像素）
    """
    pyr_ref = build_pyramid(ref, levels)
    pyr_alt = build_pyramid(alt, levels)

    dx, dy = 0.0, 0.0
    for level in range(levels):
        scale = 2 ** (levels - 1 - level)
        init_dx = dx / scale * (2 ** (levels - 1 - level) / (2 ** (levels - 1 - level)))
        # 在当前尺度精化位移
        r = pyr_ref[level].astype(np.float32)
        a = pyr_alt[level].astype(np.float32)
        if r.ndim == 3:
            r = r.mean(axis=-1)
            a = a.mean(axis=-1)

        dx_new, dy_new = lk_optical_flow_patch(
            r, a, init_dx=dx, init_dy=dy, iterations=6)
        dx, dy = dx_new, dy_new

    return dx, dy


def warp_image(image: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """
    对图像施加平移变换（双线性插值）

    参数:
        image:      输入图像，shape (H, W, C) 或 (H, W)
        dx, dy:     水平/垂直位移
    返回:
        warped:     变换后图像，dtype 与输入一致
    """
    H, W = image.shape[:2]
    coords_y = np.arange(H, dtype=np.float32) - dy
    coords_x = np.arange(W, dtype=np.float32) - dx
    yy, xx = np.meshgrid(coords_y, coords_x, indexing='ij')

    if image.ndim == 3:
        channels = []
        for c in range(image.shape[2]):
            warped_c = map_coordinates(image[:, :, c].astype(np.float64),
                                       [yy.ravel(), xx.ravel()],
                                       order=1, mode='reflect').reshape(H, W)
            channels.append(warped_c)
        return np.stack(channels, axis=-1).astype(image.dtype)
    else:
        return map_coordinates(image.astype(np.float64),
                               [yy.ravel(), xx.ravel()],
                               order=1, mode='reflect').reshape(H, W).astype(image.dtype)


# =============================================================================
# 4. 逆方差加权融合
# =============================================================================

def noise_variance(image: np.ndarray,
                   alpha: float = 0.005,
                   sigma_read_sq: float = 1e-5) -> np.ndarray:
    """
    根据泊松-高斯噪声模型计算各像素噪声方差

    参数:
        image:        线性归一化图像，[0,1]，shape (H, W, C)
        alpha:        散粒噪声系数（等效DNG NoiseProfile[1]）
        sigma_read_sq:读出噪声方差（等效DNG NoiseProfile[0]）
    返回:
        variance:     噪声方差图，shape (H, W, C)
    """
    return alpha * np.maximum(image, 0.0) + sigma_read_sq


def inverse_variance_merge(frames: list,
                           noise_params: tuple = (0.005, 1e-5),
                           motion_sigma: float = 0.02) -> np.ndarray:
    """
    逆方差加权 Burst 融合（含运动降权）

    参数:
        frames:       对齐后的帧列表，每帧 shape (H, W, C)，float32，[0,1]
        noise_params: (alpha, sigma_read_sq) 噪声模型参数
        motion_sigma: 运动检测软阈值（归一化亮度单位）
    返回:
        merged:       融合结果，shape (H, W, C)，float32
    """
    alpha, sigma_read_sq = noise_params
    ref = frames[0]

    weight_sum = np.zeros_like(ref)
    weighted_sum = np.zeros_like(ref)

    for k, frame in enumerate(frames):
        # 逆方差权重
        var_k = noise_variance(frame, alpha, sigma_read_sq)
        ivw = 1.0 / (var_k + 1e-12)

        # 运动降权：与参考帧的差异越大，权重越小
        diff_sq = (frame - ref) ** 2
        motion_w = np.exp(-diff_sq / (2.0 * motion_sigma ** 2))

        # 最终权重
        w_k = ivw * motion_w

        weight_sum  += w_k
        weighted_sum += w_k * frame

    merged = weighted_sum / (weight_sum + 1e-12)
    return merged.astype(np.float32)


# =============================================================================
# 5. 完整演示流水线
# =============================================================================

def generate_synthetic_burst(n_frames: int = 8,
                              height: int = 128,
                              width: int = 192,
                              base_snr: float = 5.0,
                              seed: int = 42) -> list:
    """
    生成合成低照度 Burst 序列（含随机抖动与噪声）

    参数:
        n_frames:  帧数
        height, width: 图像尺寸
        base_snr:  基准信噪比（越小越暗越噪）
        seed:      随机种子
    返回:
        frames:    帧列表，每帧 shape (H, W, 3)，float32，[0,1]
        shifts:    真实位移列表 [(dx0,dy0), ...]
    """
    rng = np.random.default_rng(seed)

    # 生成干净场景图（简单几何图案）
    y, x = np.mgrid[:height, :width]
    clean = (
        0.5 * np.exp(-((x - width*0.3)**2 + (y - height*0.5)**2) / (height*0.1)**2) +
        0.3 * np.exp(-((x - width*0.7)**2 + (y - height*0.4)**2) / (height*0.08)**2) +
        0.1 * np.sin(x / 15.0) * np.sin(y / 15.0) * 0.5 + 0.15
    )
    clean = np.clip(clean, 0.0, 1.0)
    clean_rgb = np.stack([clean * 0.9, clean, clean * 0.85], axis=-1)

    # 缩放至低照度
    signal_level = 0.15  # 模拟夜景（约 15% 平均亮度）
    scene = clean_rgb * signal_level

    alpha, sigma_read_sq = 0.008, 2e-5
    frames, shifts = [], []
    for k in range(n_frames):
        # 随机手持抖动（正态分布，σ=3 pixel）
        dx = float(rng.normal(0, 3.0))
        dy = float(rng.normal(0, 3.0))
        shifts.append((dx, dy))

        # 平移场景
        warped = warp_image(scene, dx, dy)

        # 泊松-高斯噪声
        shot_noise = rng.normal(0, np.sqrt(alpha * np.maximum(warped, 0)), warped.shape)
        read_noise = rng.normal(0, np.sqrt(sigma_read_sq), warped.shape)
        noisy = warped + shot_noise + read_noise
        frames.append(np.clip(noisy, 0.0, 1.0).astype(np.float32))

    return frames, shifts, scene


def demo_burst_pipeline():
    print("=== 多帧 Burst 合成演示：金字塔光流对齐 + 逆方差加权融合 ===\n")

    N = 8
    frames, gt_shifts, scene_clean = generate_synthetic_burst(
        n_frames=N, height=128, width=192, seed=42)

    print(f"生成 {N} 帧 Burst 序列，尺寸：{frames[0].shape}")
    print(f"场景平均亮度：{scene_clean.mean():.4f}")

    # --- 选取最清晰帧作为参考帧（Laplacian 方差最大） ---
    def laplacian_sharpness(frame):
        gray = frame.mean(axis=-1)
        lap = np.array([[0,1,0],[1,-4,1],[0,1,0]], dtype=np.float32)
        from scipy.ndimage import convolve
        return convolve(gray, lap).var()

    sharpness_scores = [laplacian_sharpness(f) for f in frames]
    ref_idx = int(np.argmax(sharpness_scores))
    print(f"参考帧索引：k={ref_idx}（Laplacian 方差最大，最清晰）")
    print(f"参考帧平均亮度：{frames[ref_idx].mean():.4f}\n")

    # --- 对齐 ---
    ref = frames[ref_idx]
    aligned_frames = [ref]
    align_errors = []

    print(f"{'帧号':>4}  {'GT(dx,dy)':>16}  {'Est(dx,dy)':>18}  {'误差(px)':>10}")
    print("-" * 56)
    for k in range(N):
        if k == ref_idx:
            continue  # 参考帧无需对齐自身
        gt_dx, gt_dy = gt_shifts[k]
        # 金字塔光流对齐
        est_dx, est_dy = pyramid_align(
            ref.mean(axis=-1), frames[k].mean(axis=-1), levels=4)
        err = np.sqrt((est_dx - gt_dx)**2 + (est_dy - gt_dy)**2)
        align_errors.append(err)
        print(f"{k:>4}  ({gt_dx:+6.2f},{gt_dy:+6.2f})  ({est_dx:+7.3f},{est_dy:+7.3f})  {err:10.3f}")

        warped = warp_image(frames[k], est_dx, est_dy)
        aligned_frames.append(warped)

    mean_err = np.mean(align_errors)
    print(f"\n对齐平均误差：{mean_err:.3f} 像素")

    # --- 融合 ---
    # 方法1：简单均值（基线）
    merged_mean = np.mean(aligned_frames, axis=0)

    # 方法2：逆方差加权融合
    merged_ivw = inverse_variance_merge(
        aligned_frames, noise_params=(0.008, 2e-5), motion_sigma=0.03)

    # --- SNR 对比 ---
    def calc_snr_db(image, clean_ref):
        """在均匀区域计算 SNR（dB），用标准差作为噪声代理"""
        noise = image - gaussian_filter(image, sigma=2.0)
        std_noise = noise.std()
        mean_signal = np.percentile(image, 80)  # 取亮区均值代替信号
        return 20 * np.log10(mean_signal / (std_noise + 1e-12))

    snr_single   = calc_snr_db(frames[0], scene_clean)
    snr_mean     = calc_snr_db(merged_mean, scene_clean)
    snr_ivw      = calc_snr_db(merged_ivw, scene_clean)
    snr_theory   = snr_single + 10 * np.log10(N)

    print(f"\n--- SNR 对比 ---")
    print(f"  单帧参考（k=0）：     {snr_single:.2f} dB")
    print(f"  N={N}帧简单均值：    {snr_mean:.2f} dB  （增益 {snr_mean-snr_single:+.2f} dB）")
    print(f"  N={N}帧逆方差加权：  {snr_ivw:.2f} dB  （增益 {snr_ivw-snr_single:+.2f} dB）")
    print(f"  理论上限 √N：       {snr_theory:.2f} dB  （增益 {snr_theory-snr_single:+.2f} dB）")

    # --- 基本质量指标 ---
    def psnr(a, b, max_val=1.0):
        mse = np.mean((a.astype(np.float64) - b.astype(np.float64))**2)
        return 10 * np.log10(max_val**2 / (mse + 1e-12))

    print(f"\n--- PSNR vs 干净场景 ---")
    print(f"  单帧：  {psnr(frames[0], scene_clean):.2f} dB")
    print(f"  均值合并：{psnr(merged_mean, scene_clean):.2f} dB")
    print(f"  IVW合并： {psnr(merged_ivw, scene_clean):.2f} dB")

    print("\n演示完成！")
    return merged_ivw


if __name__ == '__main__':
    result = demo_burst_pipeline()
```

**Running instructions:**
```bash
pip install numpy scipy
python ch24_demo.py
```

**Expected output key metrics:**
- Average alignment error: < 0.5 pixels (typical synthetic scene)
- N=8 frame IVW merge SNR gain: approximately 7–8 dB (close to theoretical ceiling of 9 dB)
- PSNR improvement: approximately 6–8 dB (relative to a single frame)

---

## §7 References

1. Hasinoff, S. et al., "Burst Photography for High Dynamic Range and Low-Light Imaging on Mobile Cameras," *ACM Transactions on Graphics (SIGGRAPH Asia)*, vol. 35, no. 6, 2016.

2. Wronski, B. et al., "Handheld Multi-Frame Super-Resolution," *ACM SIGGRAPH*, vol. 38, no. 4, pp. 28:1–28:18, 2019.

3. Lucas, B.D. and Kanade, T., "An Iterative Image Registration Technique with an Application to Stereo Vision," *IJCAI*, pp. 674–679, 1981.

4. Bouguet, J.Y., "Pyramidal Implementation of the Affine Lucas-Kanade Feature Tracker," *Intel Corporation Technical Report*, 2001.

5. Foi, A. et al., "Practical Poissonian-Gaussian Noise Modeling and Fitting for Single-Image Raw-Data," *IEEE Transactions on Image Processing*, vol. 17, no. 10, pp. 1737–1754, 2008.

6. Liba, O. et al., "Handheld Mobile Photography in Very Low Light," *ACM Transactions on Graphics (SIGGRAPH Asia)*, vol. 38, no. 6, 2019.

7. Mildenhall, B. et al., "Burst Denoising with Kernel Prediction Networks," *CVPR*, 2018.

8. Dong, W., Shi, G., & Li, X. "Nonlocally Centralized Sparse Representation for Image Restoration." *IEEE Transactions on Image Processing*, vol. 22, no. 4, pp. 1620–1630, 2013.

9. Google AI Blog, "Night Sight: Seeing in the Dark on Pixel Phones," 2018. https://ai.googleblog.com/2018/11/night-sight-seeing-in-dark-on-pixel.html

---

## §8 Glossary

| Term | Full Name | Description |
|------|-----------|-------------|
| Burst | Burst Photography | Rapid continuous shooting of multiple frames for post-synthesis quality improvement |
| SNR | Signal-to-Noise Ratio | Ratio of signal to noise intensity, in dB |
| IVW | Inverse Variance Weighting | Optimal linear estimation where frames with smaller noise variance receive greater weight |
| MLE | Maximum Likelihood Estimation | Statistically optimal inference framework |
| LK | Lucas-Kanade | Classical optical flow estimation algorithm based on the brightness constancy assumption |
| Photon Shot Noise | Photon Shot Noise | Noise arising from the randomness of photon arrival; variance equals the mean |
| Read-out Noise | Read-out Noise | Additive Gaussian noise introduced by sensor readout circuitry |
| Ghost Artifact | Ghost Artifact | Semi-transparent double exposures of moving objects in Burst composites due to incomplete alignment |
| Optical Flow | Optical Flow | A velocity field describing pixel motion in an image sequence |
| Image Pyramid | Image Pyramid | Multi-resolution hierarchical representation of an image, used for multi-scale processing |
| RS | Rolling Shutter | Rolling shutter; temporal distortion artifacts caused by CMOS row-by-row readout |
| AE Lock | Auto Exposure Lock | Auto-exposure lock; fixing exposure parameters during Burst acquisition |
| MAD | Median Absolute Deviation | A statistically robust measure of dispersion, resistant to outliers |
| HDR+ | High Dynamic Range Plus | Burst synthesis algorithm developed by Google, integrated in Pixel series phones |
| ETTR | Expose To The Right | Exposure strategy to maximize SNR by pushing exposure as high as possible |
| DFT | Discrete Fourier Transform | Discrete Fourier Transform; used for frequency-domain merging in the Hasinoff method |
| Tile | Image Tile | An image sub-block; the basic unit for local processing |
