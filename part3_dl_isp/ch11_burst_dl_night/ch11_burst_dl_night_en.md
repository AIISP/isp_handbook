# Part 3, Chapter 11: Deep Learning Multi-Frame Burst Denoising and Night Mode

> **Scope:** This chapter covers deep learning multi-frame alignment and fusion algorithms, with §3 dedicated to the hybrid traditional-alignment + DL-denoising pipeline (Burst Denoising, 多帧Burst降噪) that dominates current production night mode implementations. For traditional multi-frame synthesis principles, see Volume 2, Chapter 26.
> **Prerequisites:** Volume 2, Chapter 26 (Burst Night Mode Synthesis), Volume 3, Chapter 1 (DL ISP Overview), Volume 3, Chapter 2 (End-to-End Image Restoration)
> **Target Readers:** Algorithm engineers, deep learning researchers

---

## §1 Theoretical Principles

### 1.1 Physical Challenges of Night Scene Imaging

Low-light night photography faces two fundamental contradictions: insufficient photon capture by the sensor leads to significant shot noise (散粒噪声), while extending single-frame exposure time introduces motion blur. Burst night mode circumvents this contradiction fundamentally by capturing multiple short-exposure frames (typical configuration: 8–16 frames, ISO 800–3200, exposure time 1/30 s–1/8 s) and then fusing them.

From a signal processing perspective, if $N$ frames of images with independent, identically distributed noise variance are captured and perfectly aligned before averaging, the signal-to-noise ratio (SNR) improves by approximately $\sqrt{N}$:

$$
\text{SNR}_{\text{burst}} = \sqrt{N} \cdot \text{SNR}_{\text{single}}
$$

In practice, however, inter-frame displacement caused by hand shake, foreground motion, and breathing motion means that alignment errors directly introduce ghosting (鬼影). The core value of deep learning methods lies in: (1) replacing traditional block matching (块匹配) with data-driven optical flow or deformable alignment, improving alignment robustness; and (2) using kernel prediction networks (KPN, 核预测网络) or implicit weighted merging to naturally suppress motion ghosting.

### 1.2 Multi-Frame Signal Model

Let the reference frame be $\mathbf{y}_0$ and the $k$-th frame be $\mathbf{y}_k$, with an inter-frame displacement field $\mathbf{u}_k$. The noisy observation model is:

$$
\mathbf{y}_k = \mathcal{W}(\mathbf{x}, \mathbf{u}_k) + \boldsymbol{\epsilon}_k
$$

where $\mathbf{x}$ is the clean scene, $\mathcal{W}$ is the image warping (图像扭曲) operator, and $\boldsymbol{\epsilon}_k \sim \mathcal{N}(0, \sigma_k^2)$ is the Gaussian-approximated noise (real sensor noise follows a Poisson-Gaussian mixture).

The classical maximum a posteriori (MAP) fusion estimate is:

$$
\hat{\mathbf{x}} = \arg\min_{\mathbf{x}} \sum_{k=0}^{N-1} \left\| \mathbf{y}_k - \mathcal{W}(\mathbf{x}, \mathbf{u}_k) \right\|_2^2 + \lambda R(\mathbf{x})
$$

Deep learning methods either unroll this optimization as a learnable network structure, or directly regress $\hat{\mathbf{x}}$ end-to-end.

### 1.3 Noise Model Calibration

The noise variance of actual RAW images varies with signal intensity. The Poisson-Gaussian noise model (泊松-高斯混合模型) is:

$$
\text{Var}[\mathbf{y}] = \alpha \cdot \mathbf{x} + \beta
$$

where $\alpha$ (shot noise coefficient) and $\beta$ (read noise variance) are obtained through sensor calibration. Leading night mode algorithms — including Google Night Sight and Samsung Expert RAW — both construct a noise map (噪声图) before feeding data into the network to guide the network's adaptive denoising strength.

---

## §2 Algorithm Methods

### 2.1 Kernel Prediction Network (KPN)

**KPN** (Kernel Prediction Network, 核预测网络), published by Mildenhall et al. (CVPR 2018), is a landmark work in deep learning burst denoising.

**Core idea:** Rather than directly outputting a denoised image, the network predicts a set of fusion weight kernels for each pixel position (per-pixel kernel), which are then used to compute a weighted sum over the corresponding neighborhoods across multiple frames:

$$
\hat{x}_p = \sum_{k=0}^{N-1} \sum_{q \in \Omega} w_{k,p,q} \cdot y_{k,q}
$$

where $w_{k,p,q}$ is the $|\Omega|$-dimensional soft kernel weight predicted by the network for the $k$-th frame at position $p$, satisfying $\sum_{k,q} w_{k,p,q} = 1$.

**Network architecture:**
- Input: $N$ RAW frames concatenated along the channel dimension + noise map
- Encoder: U-Net structure with 4-level downsampling
- Output head: predicts $K \times K$ (typically $K=5$) kernel weights per frame per pixel, totaling $N \cdot K^2$ channels
- Loss function: L1 loss with a perceptual term

KPN's implicit alignment capability derives from the spatial search range of the kernel — if the kernel covers a sufficiently large neighborhood, the network can compensate for inter-frame displacement by learning asymmetric weight distributions along the motion direction, without requiring explicit optical flow.

### 2.2 Google Night Sight Pipeline

Google Night Sight (Liba et al., SIGGRAPH Asia 2019) combines traditional motion-robust merging with deep denoising:

1. **Frame selection (帧选择):** Computes the perceptual similarity between each frame and the reference frame; discards blurry or overexposed frames
2. **Hierarchical motion estimation:** Global affine estimation (to eliminate hand shake) + local pixel-level motion segmentation (foreground occlusion detection)
3. **Adaptive Spatial Weighting (ASW, 自适应空间权重) merging:** Down-weights motion regions, full weight for static regions
4. **Residual learning network refinement:** The merged result passes through a lightweight convolutional network to remove residual ghosting and edge artifacts

The key engineering innovation of this pipeline is **performing alignment and merging in the RAW domain**, avoiding color interpolation errors introduced by demosaicing. The network directly learns a RAW-to-RAW mapping.

### 2.3 EDVR: Deformable Alignment + Temporal Fusion

**EDVR** (Enhanced Deformable Video Restoration), proposed by Wang et al. (CVPR Workshop NTIRE 2019), introduces deformable convolution (DCN, 可变形卷积) into multi-frame alignment:

**Pyramid Cascading Deformable (PCD) Alignment Module:**
- In a multi-scale pyramid, predicts offset $\Delta p$ and modulation scalar $m$ for each feature point
- Deformable sampling: $y(p) = \sum_{k=1}^{K} w_k \cdot m_k \cdot x(p + p_k + \Delta p_k)$
- Alignment is performed in feature space, which is more robust to occlusion and large displacements than pixel-domain warping

**Temporal and Spatial Attention (TSA) Fusion Module:**
- Spatial attention: channel-wise correlation between reference frame features and aligned frame features to compute inter-frame weights
- Temporal attention: soft-weighted aggregation along the frame dimension

EDVR has long maintained state-of-the-art performance on video super-resolution (Vid4, REDS) and video denoising (DAVIS) benchmarks. Its alignment-fusion decoupled design forms the foundation for a large body of subsequent work (BasicVSR, RealBasicVSR).

### 2.4 RViDeNet: RAW-domain Video Denoising

Yue et al. (CVPR 2020) proposed **RViDeNet**, specifically targeting RAW-domain video denoising:

- Introduces a real-noise dataset (multi-frame RAW sequences captured by real hardware + long-exposure reference frames)
- Dual-branch network: spatial denoising branch (intra-frame) + temporal fusion branch (inter-frame)
- Noise modeling: the network input includes estimated Poisson-Gaussian parameters $(\alpha, \beta)$, enabling generalization across ISO settings

Compared to KPN, RViDeNet is better suited for real-time video stream processing (sliding window inference) rather than single-shot burst merging.

### 2.5 Comparison of Deep Learning Alignment Methods

| Method | Alignment Strategy | Processing Domain | Suitable Scenario |
|--------|-------------------|------------------|------------------|
| KPN (2018) | Implicit kernel search | RAW | Handheld burst |
| EDVR (2019) | DCN deformable | Feature space | Video sequences |
| RViDeNet (2020) | Optical flow + DCN | RAW / feature | Video denoising |
| Night Sight (2019) | Hierarchical motion segmentation | RAW | Mobile night mode |
| BPN (IEEE TIP 2021) | Transformer attention | Feature space | Large-displacement scenes |

---

## §3 Tuning Guide

### 3.1 Hybrid Traditional-Alignment + DL-Denoising Pipeline (Dominant Night Mode Architecture)

Current production smartphone night modes (Huawei, Samsung, Xiaomi, vivo) universally adopt a **"traditional alignment + deep learning denoising" hybrid pipeline**, rather than a purely end-to-end network. The reasons are:

1. **Alignment reliability:** Traditional hierarchical block matching (分层块匹配) is more stable than neural network optical flow in extremely low light (SNR < 10 dB) and does not produce optical flow hallucinations
2. **Compute budget:** Optical flow networks (PWC-Net requires approximately 8.7 GFLOPs/frame) have poor real-time performance on low-end SoCs, whereas block matching can be accelerated with dedicated hardware
3. **Denoising quality:** Multi-frame input after alignment provides the network with sufficient information; the network only needs to handle the denoising task, and complexity can be reduced to a lightweight level

**Recommended hybrid pipeline steps:**

```
RAW Burst Input (N frames)
    ↓
[1] Global alignment: ECC/RANSAC affine transform to eliminate hand shake
    ↓
[2] Block-wise local alignment: pyramid block matching, block size 16×16, search range ±32 pixels
    ↓
[3] Motion confidence map: SAD similarity threshold filtering, flagging foreground motion regions
    ↓
[4] Weighted merging: mean fusion for static regions, single frame (reference) for motion regions
    ↓
[5] DL refinement network: lightweight U-Net or MobileNet, input is fused result + reference frame + noise map
    ↓
Output: denoised RAW or partially demosaiced result
```

### 3.2 Frame Count Selection Strategy

- **Frame count vs. latency:** 8 frames yield an SNR gain of approximately $\sqrt{8} \approx 2.83\times$ (+9 dB) in static tripod scenarios; in handheld dynamic scenes the effective frame count is typically only 4–6 (some frames are down-weighted due to motion)
- **Adaptive frame count:** Determined dynamically based on scene brightness (Lux value): 16 frames in extremely dark scenes (< 1 lux), 8 frames in normal indoor conditions (10 lux)
- **Shutter interval:** Burst interval recommended < 33 ms (equivalent to 30 fps) to avoid excessive scene change between captures

### 3.3 Noise Model Parameter Calibration

Capture uniform gray-card RAW images at multiple ISO levels and fit the Poisson-Gaussian parameters:

```python
def calibrate_noise_model(flat_raws, iso_list):
    """
    flat_raws: list of RAW images (H, W) at different ISO levels
    iso_list:  corresponding ISO values
    returns:   dict {iso: (alpha, beta)}

    Method: divide each flat RAW into 64×64 non-overlapping patches, measure
    (mean, var) per patch, then fit var = alpha*mean + beta via least-squares.
    Requires a flat field with mild spatial brightness variation (e.g., slight
    vignetting or a stepped gray chart); a perfectly uniform field collapses all
    patches to one point and makes the fit degenerate.
    """
    import numpy as np
    params = {}
    patch_size = 64
    for iso, raw in zip(iso_list, flat_raws):
        raw = raw.astype(np.float64)
        h, w = raw.shape[:2]
        means, vars_ = [], []
        for y in range(0, h - patch_size + 1, patch_size):
            for x in range(0, w - patch_size + 1, patch_size):
                patch = raw[y:y + patch_size, x:x + patch_size]
                means.append(patch.mean())
                vars_.append(patch.var())
        means = np.array(means)
        vars_ = np.array(vars_)
        # Least-squares fit: var = alpha * mean + beta
        A = np.column_stack([means, np.ones_like(means)])
        sol, _, rank, _ = np.linalg.lstsq(A, vars_, rcond=None)
        if rank < 2:
            raise ValueError(f"Degenerate noise fit at ISO={iso}: ensure patch brightness varies.")
        alpha, beta = sol
        params[iso] = (float(alpha), float(beta))
    return params
```

### 3.4 Key Hyperparameters for the Network Refinement Module

- **Receptive field:** The denoising refinement network requires at least a 32×32 receptive field to capture alignment residuals from neighboring frames
- **Normalization layer:** Avoid BatchNorm (burst frames have inconsistent brightness across frames); recommend InstanceNorm or removing normalization entirely
- **Loss weight ratio:** L1 : SSIM : Perceptual = 1.0 : 0.5 : 0.1; overly strong perceptual loss will introduce texture hallucinations
- **Quantization deployment:** Before INT8 quantization, calibrate activation ranges with real night scene RAW sequences to avoid overflow in extremely dark regions

### 3.5 Common Tuning Pitfalls

| Pitfall | Problem | Recommendation |
|---------|---------|----------------|
| Increasing frame count expecting linear gain | In handheld scenarios, motion frames are down-weighted and gain saturates | Use adaptive frame count strategy |
| Stacking aligned frames directly as network input | Alignment errors are treated as noise; the network struggles to distinguish them | Merge first, then refine |
| Training data consisting entirely of synthetic noise | Sim-to-Real gap is large; poor performance on real scenes | Mix in real RAW noise data during training |
| Omitting noise map input | Unstable results across ISO settings and device models | Calibrated noise parameters must be provided as input |
| Applying vignette correction before fusion | Corner noise variance increases, producing blotchy artifacts after fusion | Fuse first, then apply LSC vignette correction |

---

## §4 Common Artifacts

### 4.1 Motion Ghosting (运动鬼影)

**Manifestation:** Moving objects in the scene (pedestrians, branches, text) display semi-transparent double images after fusion — foreground contours appear blurred, background "shows through" from motion regions, and phantom images at motion edges overlap with reference frame content, creating a double-exposure effect. The more frames used in night mode multi-frame fusion (≥ 5 frames), the more pronounced the ghosting.

**Root cause:** Offset estimation errors from block-matching-based alignment (the implicit alignment in Kernel Prediction Networks) on moving objects cause incorrect fusion. Specifically: when the SAD (Sum of Absolute Differences) threshold is set too loosely, motion regions are incorrectly classified as static, and multi-frame fusion weights and averages objects from different positions; while deep learning fusion networks (such as KPN) cannot fully suppress the contribution of offset frames in motion regions (weights not decayed to zero), allowing motion frame content to seep into the output at low weight. Quantification: Ghost Score $= \frac{1}{|\mathcal{M}|}\sum_{p\in\mathcal{M}}|\hat{x}_p - x_p^{\text{ref}}|$ (where $\mathcal{M}$ is the motion mask region); normal fusion should yield < 2 DN (normalized < 0.008).

**Diagnosis method:** Compute a difference map between the reference frame and auxiliary frames aligned by optical flow to mark motion regions $\mathcal{M}$ (difference > $2\sigma$); compute the Ghost Score in motion regions; visualize the KPN kernel weight map — if the weight distribution across frames is uniform in motion regions (rather than concentrated on the reference frame), the fusion is failing to suppress motion frame contributions.

**Mitigation strategies:**
- In KPN, for detected motion regions (block-matching SAD is large, or optical flow magnitude > threshold), force non-reference frame kernel weights to zero, falling back to single-frame pass-through;
- Introduce an anti-ghosting loss: $\mathcal{L}_{\text{ghost}} = \frac{1}{|\mathcal{M}|}\sum_{p\in\mathcal{M}}\|\hat{x}_p - x_p^{\text{ref}}\|_1$, with weight $\lambda_{\text{ghost}} \in [0.05, 0.1]$;
- For large-displacement motion regions (> 8 pixels), skip them entirely from multi-frame alignment and fusion to avoid warping-induced smearing.

### 4.2 Waxy Skin Effect (蜡像效应)

**Manifestation:** After multi-frame fusion in portrait night scenes, skin areas exhibit a "wax figure" appearance — skin texture (pores, fine hairs, fine wrinkles) is over-smoothed, skin color is preserved but texture quality disappears, showing a clear difference from the microscopic structure of real skin. LPIPS captures this problem better than PSNR (PSNR appears normal but LPIPS shows significant deviation).

**Root cause:** Multi-frame fusion is fundamentally a weighted average over local patches, and the spatial frequency of skin texture (pores approximately 0.1–0.3 mm, corresponding to 1–3 pixels) falls right at the fusion smoothing cutoff frequency. KPN trained with L2 loss tends toward the "mean solution" that minimizes MSE for under-constrained high-frequency texture detail: the expected average of high-frequency texture detail corresponding to the same low-frequency skin color region across all training samples causes texture to disappear. Furthermore, when the number of frames $N \geq 8$ and noise $\sigma$ is relatively low, the multi-frame average itself reduces high-frequency signal gain to less than the theoretical $1/\sqrt{N}$ gain, actually losing detail.

**Diagnosis method:** Compute LPIPS and local spectral energy (FFT magnitude in the $f = 0.1$–$0.4$ Nyquist frequency range) in skin regions (extracted using a body parsing network) before and after fusion; if the mid-to-high frequency energy in skin regions after fusion is < 60% of the single frame before fusion, waxy skin is present. Conduct subjective comparison scoring (Realism Score) against images of the same scene taken with a reference large-aperture camera; < 3.5/5 indicates significant waxy skin.

**Mitigation strategies:**
- Introduce perceptual loss (VGG-16 `relu3_4` layer feature distance), with weight $\lambda_{\text{perc}} \in [0.1, 0.3]$, to compensate for L2 loss's averaging bias toward high-frequency texture;
- Perform frequency mixing between the fusion output and single-frame DnCNN denoising result: low-frequency components take the multi-frame fusion output (higher SNR), high-frequency components take single-frame denoising (texture preservation), with mixing ratio adaptively adjusted by ISO;
- Enable a dedicated texture enhancement branch (e.g., GFPGAN skin texture prior) for portrait regions to recover pore detail lost during fusion.

### 4.3 Low-SNR Color Noise Residual (低SNR颜色噪声残留)

**Manifestation:** After multi-frame fusion in night scenes, obvious color noise spots remain in dark regions (luminance < 32 DN, normalized < 0.125) — random red/green/blue pixels scattered against a dark background, still visible even after multi-frame averaging, especially in shadow areas and dark skies. PSNR appears normal but chroma uniformity shows significant deviation.

**Root cause:** Color noise in image sensors originates from two sources: photon shot noise (Poisson distribution) in each color channel of the Bayer array, and fixed pattern noise (FPN). In extremely dark regions (< 32 DN) with very few signal photons, color noise amplitude is approximately 50%–200% of the signal level ($\text{CRN} = \sigma_{\text{chroma}} / I_{\text{signal}}$). Multi-frame averaging provides $1/\sqrt{N}$ attenuation for luminance noise (low inter-frame correlation), but FPN inter-channel correlation is high (FPN phase is the same across all frames), so FPN residual does not decrease and may even increase after averaging. Additionally, if DL fusion networks are trained primarily on medium-brightness images (assuming AWGN), they learn insufficiently about extremely low-SNR color noise, resulting in poor generalization.

**Diagnosis method:** Compute color standard deviations $\sigma_{\text{R}}$, $\sigma_{\text{G}}$, $\sigma_{\text{B}}$ in dark regions (uniform background patches, luminance < 32 DN) before and after fusion; if post-fusion color standard deviation > 70% of single frame (i.e., color noise attenuation < 30%), color noise residual is present; also check whether the mean deviation of the Cb/Cr channels is zero (FPN-induced color bias will cause Cb/Cr means to deviate significantly from zero).

**Mitigation strategies:**
- Perform inter-frame alignment and fusion in the RAW domain before demosaicing, using the physical noise model in the Bayer domain (Poisson-Gaussian parameters already calibrated) to apply prior constraints on color noise — more effective than RGB-domain fusion;
- Use real RAW data (containing real FPN) for network training; do not use pure AWGN synthetic noise;
- For extremely dark regions (< 32 DN), supplement post-processing with HSV-space Hue/Saturation denoising (smooth only hue and saturation, not luminance) to specifically clear color noise residuals;
- Pre-calibrate sensor FPN (dark frame correction), subtract the FPN fixed pattern from each frame before fusion to eliminate inter-frame correlated color bias.

### 4.4 Common Artifacts Reference Table

| Artifact Type | Trigger Conditions | Typical Manifestation | Mitigation |
|--------------|-------------------|----------------------|-----------|
| Motion Ghosting | Block-matching threshold too loose; KPN kernel weights fail to suppress motion frames | Semi-transparent double images of moving objects | Force single-frame pass-through for motion regions; anti-ghosting loss |
| Waxy Skin Effect | L2 mean regression; high-frequency texture averaging | Skin texture disappears; oil-painting appearance | Perceptual loss; frequency mixing; texture enhancement branch |
| Color Noise Residual | High FPN correlation; out-of-distribution extremely low SNR | Color spots remaining in dark regions | RAW-domain fusion; real noise training; dark frame correction |
| Color Shift | Inconsistent AWB gains across frames | Overall cool or green color cast | Unify all frames to reference frame AWB space before alignment |
| Vignette Noise Heterogeneity | LSC applied before fusion | Blotchy noise in image corners | Fuse multiple frames first, then apply LSC correction |

---

## §5 Evaluation Methods

### 5.1 Reference-based Image Quality Metrics

| Metric | Description | Recommended Tool |
|--------|-------------|-----------------|
| PSNR | Peak signal-to-noise ratio | scikit-image |
| SSIM | Structural similarity index | scikit-image |
| LPIPS | Perceptual distance (AlexNet features) | richzhang/PerceptualSimilarity |
| FSIM | Feature similarity index | Custom implementation or piq library |

### 5.2 No-Reference Evaluation

- **BRISQUE / NIQE:** Assess texture naturalness; scores rise significantly with over-smoothing
- **RealSR-MUSIQ:** Transformer-based blind IQA with good discriminability for night scene over/under-exposure
- **CLIP-IQA:** Zero-shot image quality assessment using CLIP pre-trained features

### 5.3 Quantitative Ghosting Evaluation

Ghosting cannot be measured by PSNR alone. The recommended **Ghost Score** (local error weighted by motion mask) is:

$$
\text{GhostScore} = \frac{1}{|\mathcal{M}|} \sum_{p \in \mathcal{M}} \left| \hat{x}_p - x_p^{\text{ref}} \right|
$$

where $\mathcal{M}$ is the motion region mask (generated by thresholding the optical flow field) and $x_p^{\text{ref}}$ is the reference frame value. A lower score indicates less ghosting.

### 5.4 Benchmark Datasets

| Dataset | Source | Characteristics |
|---------|--------|----------------|
| SID (CVPR 2018) | Chen et al. | Real RAW low-light, Sony/Fuji sensors |
| SMID (ICCV 2019) | Chen et al. | Multi-frame low-light video sequences |
| CRVD (CVPR 2020) | Yue et al. | Real RAW video denoising dataset |
| MCR (SIGGRAPH Asia 2019) | Liba et al. | Real burst sequences from Google Night Sight |
| ELD (CVPR 2020) | Wei et al. | Extreme low-light RAW with detailed noise calibration |

### 5.5 Subjective Evaluation Protocol

- **MOS evaluation:** At least 20 observers rating on a calibrated display (sRGB D65, luminance 100 cd/m²)
- **A/B testing:** Compare single-frame denoising of the reference frame vs. multi-frame fusion, focusing on: texture fidelity, presence of ghosting, color reproduction
- **Dynamic scene specific:** Pay special attention to ghosting scores in pedestrian/vehicle regions; must be computed and reported separately

---

## §6 Code Examples

### 6.1 Poisson-Gaussian Noise Synthesis

```python
import numpy as np

def synthesize_poisson_gaussian_noise(clean_raw, alpha, beta, seed=42):
    """
    合成泊松-高斯混合噪声，用于训练数据生成。
    clean_raw: float32 RAW图像，范围[0, 1]
    alpha:     shot noise系数（泊松强度近似）
    beta:      read noise方差（高斯）
    返回:      含噪RAW图像 float32
    """
    rng = np.random.default_rng(seed)
    # 泊松噪声近似为高斯，方差=alpha*signal
    shot = rng.normal(0.0, np.sqrt(alpha * np.clip(clean_raw, 1e-6, None)))
    # 高斯读出噪声
    read = rng.normal(0.0, np.sqrt(beta), clean_raw.shape)
    noisy = clean_raw + shot.astype(np.float32) + read.astype(np.float32)
    return np.clip(noisy, 0.0, 1.0).astype(np.float32)
```

### 6.2 Pyramid Block Matching Alignment (Simplified Demo)

```python
import cv2
import numpy as np

def pyramid_block_match_align(ref, src, levels=3, search_range=32):
    """
    多尺度金字塔块匹配，估计src相对ref的全局平移偏移。
    ref, src: float32 单通道图像（如Gr通道）
    返回: (dx, dy) 全局平移量
    """
    ref_u8 = (np.clip(ref, 0, 1) * 255).astype(np.uint8)
    src_u8 = (np.clip(src, 0, 1) * 255).astype(np.uint8)

    ref_pyr, src_pyr = [ref_u8], [src_u8]
    for _ in range(levels - 1):
        ref_pyr.append(cv2.pyrDown(ref_pyr[-1]))
        src_pyr.append(cv2.pyrDown(src_pyr[-1]))

    dx, dy = 0, 0
    for lvl in range(levels - 1, -1, -1):
        scale = 2 ** lvl
        rl, sl = ref_pyr[lvl], src_pyr[lvl]
        sr = max(1, search_range // scale)
        h, w = rl.shape
        # 裁剪参考帧中心区域
        crop_ref = rl[sr:h-sr, sr:w-sr]
        # 在src上加入上一级估计的偏移
        shifted_src = np.zeros_like(sl)
        ox, oy = int(dx * 2), int(dy * 2)
        # 简单平移（演示用，生产环境应用cv2.remap）
        tx = np.clip(sr + ox, 0, w - (w - 2*sr))
        ty = np.clip(sr + oy, 0, h - (h - 2*sr))
        crop_src = sl[ty:ty + crop_ref.shape[0], tx:tx + crop_ref.shape[1]]
        if crop_src.shape != crop_ref.shape:
            continue
        result = cv2.matchTemplate(sl, crop_ref, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(result)
        dx = (max_loc[0] - sr) / (1.0)
        dy = (max_loc[1] - sr) / (1.0)

    return float(dx), float(dy)
```

### 6.3 KPN-style Per-pixel Kernel Fusion

```python
import torch
import torch.nn.functional as F

def kpn_fuse(frames, kernels):
    """
    KPN融合：用逐像素预测核对多帧Burst进行加权合并。
    frames:  (B, N, C, H, W) — N帧burst图像
    kernels: (B, N, K*K, H, W) — 网络预测的核权重（未归一化）
    返回:    (B, C, H, W) 融合结果
    """
    B, N, C, H, W = frames.shape
    K2 = kernels.shape[2]
    K = int(K2 ** 0.5)
    pad = K // 2

    # 在N*K2维度做softmax归一化，确保权重之和为1
    w = kernels.view(B, N * K2, H, W)
    w = F.softmax(w, dim=1)            # (B, N*K2, H, W)
    w = w.view(B, N, K2, H, W)

    output = torch.zeros(B, C, H, W, device=frames.device, dtype=frames.dtype)
    for n in range(N):
        frame_n = frames[:, n]         # (B, C, H, W)
        # unfold取K×K空间邻域: (B, C*K2, H*W)
        unfolded = F.unfold(frame_n, kernel_size=K, padding=pad)  # (B, C*K2, H*W)
        unfolded = unfolded.view(B, C, K2, H * W).view(B, C, K2, H, W)
        w_n = w[:, n].unsqueeze(1)     # (B, 1, K2, H, W)
        output += (unfolded * w_n).sum(dim=2)

    return output
```

### 6.4 Simplified End-to-End Training Framework

```python
import torch
import torch.nn as nn

class LightweightKPN(nn.Module):
    """轻量KPN演示网络：U-Net编码器 + 核权重输出头"""
    def __init__(self, n_frames=8, k=5, base_ch=64):
        super().__init__()
        self.n_frames = n_frames
        self.k = k
        in_ch = n_frames * 4 + 2  # RGGB×N帧 + 噪声图2通道(alpha,beta)

        # 简化编码器
        self.enc = nn.Sequential(
            nn.Conv2d(in_ch, base_ch, 3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(base_ch, base_ch * 2, 3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(base_ch * 2, base_ch, 3, padding=1), nn.ReLU(inplace=True),
        )
        # 核权重输出头：每帧每像素输出K×K权重
        self.head = nn.Conv2d(base_ch, n_frames * k * k, kernel_size=1)

    def forward(self, burst_raw, noise_map):
        """
        burst_raw:  (B, N*4, H, W) — N帧RGGB RAW按通道拼接
        noise_map:  (B, 2, H, W)   — alpha/beta噪声参数图
        """
        B = burst_raw.shape[0]
        H, W = burst_raw.shape[2], burst_raw.shape[3]

        feat = self.enc(torch.cat([burst_raw, noise_map], dim=1))
        kernels_flat = self.head(feat)                        # (B, N*K2, H, W)
        kernels = kernels_flat.view(B, self.n_frames,
                                    self.k * self.k, H, W)

        frames = burst_raw.view(B, self.n_frames, 4, H, W)
        return kpn_fuse(frames, kernels)                      # (B, 4, H, W)


def train_epoch(model, loader, optimizer, device):
    """单轮训练，使用Charbonnier损失（平滑L1近似）"""
    model.train()
    criterion = lambda p, t: torch.mean(torch.sqrt((p - t) ** 2 + 1e-6))
    total_loss = 0.0
    for burst, noise_map, target in loader:
        burst     = burst.to(device)
        noise_map = noise_map.to(device)
        target    = target.to(device)

        optimizer.zero_grad()
        pred = model(burst, noise_map)
        loss = criterion(pred, target)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    return total_loss / len(loader)

# ─── 示例调用与输出 ───────────────────────────────────────
def add_shot_noise(img: torch.Tensor, iso: int) -> torch.Tensor:
    """Apply simplified Poisson shot noise scaled by ISO."""
    scale = iso / 100.0
    return torch.poisson(img.clamp(min=0) * scale) / scale

clean_frame = torch.rand(3, 256, 256)   # simulate a single clean RAW frame (C,H,W)
noisy = add_shot_noise(clean_frame, iso=3200)
# 输出: noisy.shape 与 clean_frame 相同，dtype=float32，range [0,1]

```

---

## References

1. Mildenhall, B., et al. **"Burst Denoising with Kernel Prediction Networks."** CVPR 2018.
2. Liba, O., et al. **"Handheld Mobile Photography in Very Low Light."** SIGGRAPH Asia 2019. *(Google Night Sight)*
3. Wang, X., et al. **"EDVR: Video Restoration with Enhanced Deformable Convolutional Networks."** CVPR Workshop NTIRE 2019.
4. Yue, H., et al. **"Supervised Raw Video Denoising with a Benchmark Dataset on Dynamic Scenes."** CVPR 2020. *(RViDeNet)*
5. Chen, C., et al. **"Learning to See in the Dark."** CVPR 2018. *(SID dataset)*
6. Chan, K., et al. **"BasicVSR: The Search for Essential Components in Video Super-Resolution and Beyond."** CVPR 2021.
7. Wei, K., et al. **"A Physics-based Noise Formation Model for Extreme Low-light Raw Denoising."** CVPR 2020. *(ELD dataset)*
8. Chen, C., et al. **"Seeing Motion in the Dark."** ICCV 2019. *(SMID dataset)*
9. Zhang, K., et al. **"Beyond a Gaussian Denoiser: Residual Learning of Deep CNN for Image Denoising."** IEEE TIP 2017.
10. Plotz, T., Roth, S. **"Benchmarking Denoising Algorithms with Real Photographs."** CVPR 2017.

## §8 Glossary

| Term | Chinese | Explanation |
|------|---------|-------------|
| Burst Denoising | Burst降噪 | Technology that captures multiple short-exposure frames and merges them to improve SNR |
| Kernel Prediction Network (KPN) | 核预测网络 | A deep network that predicts per-pixel fusion kernel weights |
| Deformable Convolution (DCN) | 可变形卷积 | A convolution operator whose sampling points have learnable spatial offsets |
| Motion Ghosting | 运动鬼影 | Semi-transparent double images of moving objects caused by multi-frame alignment errors |
| Poisson-Gaussian Noise | 泊松-高斯噪声 | Mixed sensor noise model: shot noise (Poisson) + read noise (Gaussian) |
| Noise Map | 噪声图 | Per-pixel noise standard deviation estimate used as auxiliary input to the network |
| Image Warping | 图像扭曲 | Spatial transformation applied to an image according to a displacement field |
| Receptive Field | 感受野 | The spatial range of the input that an output pixel can perceive |
| Signal-to-Noise Ratio (SNR) | 信噪比 | Ratio of signal power to noise power, measured in dB |
| RAW-domain Processing | RAW域处理 | Algorithmic operations performed on Bayer raw data before demosaicing |
| Adaptive Spatial Weighting (ASW) | 自适应空间权重 | Mechanism that dynamically adjusts fusion weights for each frame based on inter-frame similarity |
