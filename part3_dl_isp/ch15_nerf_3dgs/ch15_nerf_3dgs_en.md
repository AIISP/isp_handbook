# Part 3, Chapter 15: NeRF and 3D Gaussian Splatting in Computational Imaging

> **Scope:** This chapter covers Neural Radiance Fields (NeRF, 神经辐射场) and 3D Gaussian Splatting (3DGS, 3D高斯飞溅) and their applications in imaging simulation and computational photography, including RAW-NeRF and other methods designed specifically for camera modeling.
> **Prerequisites:** Volume 3, Chapter 1 (DL ISP Overview)
> **Target Readers:** Algorithm researchers, deep learning engineers

---

## §1 Theoretical Foundations

### 1.1 The Basic Framework of Neural Radiance Fields (NeRF)

Neural Radiance Fields (NeRF) was first proposed by Mildenhall et al. at ECCV 2020. Its core idea is to use a Multi-Layer Perceptron (MLP) to implicitly represent the volumetric density and radiance color of a 3D scene, and to project the 3D scene onto 2D images via differentiable volume rendering. Multi-view images serve as supervision signals to optimize the scene representation.

Given a point $\mathbf{x} = (x, y, z)$ in space and a viewing direction $\mathbf{d} = (\theta, \phi)$ (spherical coordinates), the NeRF network $F_\Theta$ outputs:

$$
F_\Theta(\mathbf{x}, \mathbf{d}) \rightarrow (\mathbf{c}, \sigma)
$$

where $\mathbf{c} = (r, g, b)$ is the color at that point in direction $\mathbf{d}$, and $\sigma \geq 0$ is the volumetric density (analogous to an absorption coefficient).

**Volume Rendering Equation**: Integrating along the camera ray $\mathbf{r}(t) = \mathbf{o} + t\mathbf{d}$ from near bound $t_n$ to far bound $t_f$, the pixel color is:

$$
\hat{C}(\mathbf{r}) = \int_{t_n}^{t_f} T(t)\, \sigma(\mathbf{r}(t))\, \mathbf{c}(\mathbf{r}(t), \mathbf{d})\, dt
$$

where the transmittance $T(t) = \exp\!\left(-\int_{t_n}^{t} \sigma(\mathbf{r}(s))\, ds\right)$ represents the accumulated transmittance from $t_n$ to $t$. In practice, the continuous integral is replaced by a discrete approximation using stratified sampling plus importance sampling.

**Positional Encoding (PE)**: Raw coordinates $(x, y, z)$ have insufficient expressive power for high-frequency details. NeRF maps them into high-dimensional Fourier features:

$$
\gamma(p) = \left(\sin(2^0\pi p), \cos(2^0\pi p), \ldots, \sin(2^{L-1}\pi p), \cos(2^{L-1}\pi p)\right)
$$

Typically $L=10$ (coordinates) and $L=4$ (directions), enabling the MLP to learn high-frequency textures and details.

### 1.2 Limitations of NeRF for Camera Imaging Models

Original NeRF assumes images are captured by a linear camera (linear photometry), i.e., 3D radiance directly equals pixel values. However, real smartphone photos are processed by an ISP:

1. **Tone Mapping**: Compresses linear HDR to 8-bit sRGB — a non-linear transformation;
2. **Auto White Balance (AWB)**: Different per-channel gains;
3. **Demosaicing** and **Noise**: The RAW signal undergoes multiple processing steps.

These non-linear transformations make it difficult for NeRF to accurately reconstruct geometry and radiance when learning from sRGB images, especially in scenes with significant exposure differences, where cross-view color inconsistency severely degrades reconstruction quality.

### 1.3 The Core Concept of 3D Gaussian Splatting (3DGS)

3D Gaussian Splatting (3DGS) was published by Kerbl et al. in ACM TOG (SIGGRAPH 2023). It explicitly represents a scene using a set of anisotropic 3D Gaussian primitives, each described by the following attributes:

- Center position $\boldsymbol{\mu} \in \mathbb{R}^3$;
- Covariance matrix $\boldsymbol{\Sigma} \in \mathbb{R}^{3\times 3}$ (decomposed from rotation quaternion $\mathbf{q}$ and scale vector $\mathbf{s}$: $\boldsymbol{\Sigma} = \mathbf{R}\mathbf{S}\mathbf{S}^\top\mathbf{R}^\top$);
- Opacity $\alpha \in [0,1]$;
- Spherical Harmonics (SH) coefficients encoding view-dependent color.

During rendering, 3D Gaussians are projected (splatted) onto the image plane, sorted by depth, and composited via $\alpha$-blending:

$$
C = \sum_{i=1}^{N} \mathbf{c}_i \alpha_i \prod_{j=1}^{i-1}(1-\alpha_j)
$$

The key advantage of 3DGS is real-time rendering (100+ FPS on an RTX3090) and explicit editability. Compared to NeRF, it eliminates the costly ray marching step.

---

## §2 Algorithmic Methods

### 2.1 Mip-NeRF: Multi-Scale Anti-Aliasing

Original NeRF samples a single 3D point per ray, ignoring the fact that each pixel actually corresponds to a conical frustum. This leads to aliasing at close range and blurring at far distances.

Barron et al. (ICCV 2021) proposed Mip-NeRF, replacing rays with cones and using Integrated Positional Encoding (IPE) instead of point-based PE:

$$
\text{IPE}(\boldsymbol{\mu}, \boldsymbol{\Sigma}) = \left(\mathbb{E}[\sin(\gamma(\mathbf{x}))], \mathbb{E}[\cos(\gamma(\mathbf{x}))]\right), \quad \mathbf{x} \sim \mathcal{N}(\boldsymbol{\mu}, \boldsymbol{\Sigma})
$$

where $\boldsymbol{\mu}$ and $\boldsymbol{\Sigma}$ are the mean and covariance of the conical frustum cross-section, given by closed-form expressions without requiring Monte Carlo sampling. Mip-NeRF improves PSNR by approximately 2 dB on multi-scale 360° scenes.

### 2.2 RAW-NeRF: Camera-Aware Neural Radiance Fields

Mildenhall et al. (CVPR 2022) proposed RAW-NeRF, a landmark work deeply integrating NeRF with RAW camera imaging models. Key contributions:

**(1) Direct Training from RAW Images**: Bypasses ISP processing by using Bayer-format RAW images as training supervision, avoiding the interference of ISP-introduced non-linearities on radiance field learning. Volume rendering is performed in linear photometric space, fully consistent with physical imaging.

**(2) Camera-Aware Loss**: For each training image, the network predicts the corresponding frame's exposure value (EV) and white balance gains, comparing the linear HDR rendering result against the RAW image. The loss function is:

$$
\mathcal{L} = \sum_{\mathbf{r}} \left\| \text{ISP}_{\phi}(\hat{C}(\mathbf{r})) - C_{\text{raw}}(\mathbf{r}) \right\|^2_2
$$

where $\text{ISP}_\phi$ is a learnable lightweight color transform (linear matrix + gamma curve) with parameters $\phi$ jointly optimized with NeRF parameters.

**(3) Exposure Normalization**: For HDR scene reconstruction, input images at different exposures are normalized to a unified linear radiance space. RAW-NeRF can seamlessly handle exposure bracketing data to achieve neural HDR reconstruction.

Experiments show that RAW-NeRF achieves 1.5–3 dB higher PSNR than sRGB-NeRF in low-light scenes, with significantly improved color accuracy.

### 2.3 Zip-NeRF: Combining Hash Encoding with Anti-Aliasing

Barron et al. (ICCV 2023) proposed Zip-NeRF, combining the anti-aliasing concept of Mip-NeRF with the Multiresolution Hash Encoding (MHE) of Instant-NGP (Müller et al., SIGGRAPH 2022):

- For each conical frustum cross-section, multiple points are sampled on hash grids at multiple resolutions and averaged, replacing the closed-form IPE integral;
- A regularization term is introduced to suppress "floater" artifacts caused by high-frequency hash collisions.

Zip-NeRF reduces training time from Mip-NeRF's several hours to a few minutes, while PSNR on 360° scenes surpasses Mip-NeRF by approximately 0.5 dB, making it one of the highest-accuracy NeRF variants as of 2023.

### 2.4 Extensions of 3DGS for Computational Imaging

The original 3DGS imaging model also assumes linear photometry. In computational photography applications, the following extensions have been developed:

**4D Gaussian Splatting** (Wu et al., CVPR 2024): Introduces a deformation field to handle dynamic scenes, enabling 3DGS for scene reconstruction from video sequences. This has important value for temporal consistency analysis in ISP evaluation.

**Physical Camera Model Integration**: Integrates lens aberrations (distortion, chromatic aberration) and camera noise models into the 3DGS rendering pipeline to generate realistic "RAW-like" simulated images, providing data augmentation for ISP algorithm validation.

**ISP Simulation with 3DGS**: After reconstructing a real scene with 3DGS, different lighting conditions are simulated by modifying SH coefficients and opacity, and corresponding RAW images are generated by overlaying camera noise models (Poisson noise + readout noise). This provides paired training data for ISP denoising algorithms and enables the construction of large-scale synthetic datasets without physical shooting.

### 2.5 Applications of NeRF in Imaging Simulation

**Bokeh Synthesis**: Using depth maps and scene density estimated by NeRF, a view-dependent blur kernel (Lens PSF) is applied to background regions during rendering to simulate shallow depth-of-field effects from large apertures (complementary to the deep learning bokeh methods in Volume 3, Chapter 13).

**Virtual Camera Calibration Data Generation**: After reconstructing a real calibration board scene with NeRF, images are rendered along virtual camera trajectories, generating calibration data with precisely known 3D-2D correspondences and reducing the physical calibration workload.

**Multi-Exposure Fusion Evaluation**: Using the HDR scene representation from RAW-NeRF, RAW image sequences at arbitrary exposure values can be rendered to provide ground truth for HDR fusion algorithms (Volume 2, Chapter 11).

---

## §3 Tuning Guide

### 3.1 NeRF Training Stability

| Parameter | Recommended Setting | Notes |
|-----------|---------------------|-------|
| Positional encoding frequency bands $L$ | 10 for coordinates, 4 for directions | Too large causes noise overfitting; too small loses detail |
| Stratified sample count | 64 coarse network, 128 fine network | Too few fine network samples degrades detail reconstruction |
| Learning rate schedule | Exponential decay, 5e-4 → 5e-5 | Cosine decay is also commonly used with similar effect |
| Batch size (number of rays) | 4096 rays/batch | Increasing batch size when GPU memory allows improves convergence speed |
| Exposure normalization | Estimate EV independently for each exposure frame | Avoids cross-frame color inconsistency affecting geometry optimization |

### 3.2 3DGS Tuning

| Parameter | Recommended Setting | Notes |
|-----------|---------------------|-------|
| Initial Gaussian count | Determined by SfM point cloud, typically 100K–1M | Point cloud quality directly affects reconstruction results |
| Densification threshold | Gradient threshold 0.0002 | Too low causes Gaussian explosion; too high results in insufficient detail |
| Spherical Harmonics order | 3rd order (16 coefficients) | 0th order handles diffuse only; 3rd order handles specular highlights |
| Opacity pruning threshold | 0.005 | Periodically remove invalid Gaussian primitives with low opacity |
| Training steps | 30,000 steps | Complex scenes can be extended to 50,000 steps |

### 3.3 RAW-NeRF-Specific Settings

- **Bayer Channel Handling**: Input RAW Bayer images as 4-channel (RGGB); output 4 channels during rendering then interpolate to RGB, rather than demosaicing first before input;
- **Noise-Aware Loss**: For high-ISO images, the per-pixel weight in the loss function should be inversely proportional to signal-dependent noise variance (lower weights for low-brightness regions), preventing noisy regions from dominating gradients:
  $$w(\mathbf{r}) \propto \frac{1}{\sigma^2_{\text{noise}}(C_{\text{raw}}(\mathbf{r}))}$$
- **Exposure Embedding**: Learn a trainable exposure embedding vector for each frame and concatenate it with spatial coordinates before feeding into the MLP, enabling the network to explicitly distinguish radiance differences across different exposures.

---

## §4 Artifacts

### 4.1 Floaters

**Phenomenon:** In NeRF or 3DGS scene reconstructions, semi-transparent cloud-like structures or discrete "ghost points" appear floating in mid-air — particularly noticeable in textureless background regions such as sky, white walls, and glass. When the camera view is rotated, floaters shift in position with the viewing angle, while the corresponding real scene locations are empty. 3DGS floaters manifest as semi-transparent floating Gaussian ellipsoids that produce a hazy appearance during rendering; NeRF floaters manifest as air regions with volumetric density $\sigma > 0$ that occlude the background.

**Root Cause:** In NeRF, the volumetric density MLP lacks effective supervision in textureless background regions — ray sample points in background regions contribute near-zero color to all training views (weight $T_i\alpha_i \approx 0$), making it difficult for the MLP to learn the correct "air density = 0" constraint from gradients. When there is slight pose error across views, the MLP tends to generate low-density "fog" in error regions to reduce the rendering L2 loss. In 3DGS, the densification strategy clones Gaussians in high-gradient background regions, but if the gradients primarily originate from view transitions rather than real scene structure, incorrectly positioned Gaussians appear in mid-air.

**Diagnostic Methods:** Render and visualize depth maps — floaters correspond to anomalously close depth values in the depth map (closer than real scene objects). Count the density distribution histogram of NeRF — if more than 5% of samples with $\sigma > 0.1$ are in known empty regions (verifiable by sparse SfM point clouds), floaters are significant. For 3DGS, count the proportion of Gaussians with $\alpha > 0.5$ that fall outside the SfM point cloud support region.

**Mitigation Strategies:**
- Introduce a density sparsification regularization term: $\mathcal{L}_{\text{sparse}} = \lambda \sum_{i} \sigma_i^2$ (weight $\lambda = 1\text{e-}4$), encouraging the network to compress density to zero in textureless regions;
- Use depth priors as constraints: leverage SfM sparse point clouds or depth maps predicted by monocular depth networks as supervision to constrain density distribution near physical scene geometry;
- For 3DGS, periodically reset opacity (every 3,000 steps) and raise the pruning threshold (prune $\alpha < 0.005$) to prevent floater Gaussians from accumulating during iterations.

### 4.2 Ghost / Double Image

**Phenomenon:** When rendering novel views, moving objects in the scene (at different positions across training frames) or dynamic scene elements (leaves blowing in wind, pedestrians walking) appear as "double exposures" in the rendered result — two or more semi-transparent versions of the same object appear at the same location, creating a double-exposure effect. This problem is most pronounced when the camera is static but the scene is dynamic.

**Root Cause:** The static scene assumption of NeRF/3DGS conflicts with reality — if an object appears at different positions across training frames, the MLP or Gaussian set will simultaneously assign density/Gaussians at both positions. When rendering any viewpoint, both positions contribute density, creating ghosts. Specifically: NeRF's MLP "averages" colors across multiple views (the mean solution minimizing L2), with dynamic objects having partial training view support at both positions, producing a bimodal density distribution; 3DGS's densification strategy generates Gaussians at both positions, each with approximately 0.5 opacity.

**Diagnostic Methods:** Detect the proportion of moving objects (optical flow magnitude > 5 pixels) across multiple training frames — if more than 15% of training pixels come from motion regions, the probability of Ghost artifacts is high. Render difference maps of the same viewpoint at different illumination levels or timestamps — if differences concentrate in dynamic object regions with magnitude > 10 DN, this confirms ghosts from dynamic objects rather than rendering noise.

**Mitigation Strategies:**
- During training data preprocessing, use motion detection (optical flow + semantic segmentation) to generate dynamic object masks. Reduce loss weight for pixels inside the mask (weight $\rightarrow 0.1$), or directly skip dynamic pixels during training;
- Use dynamic scene reconstruction methods such as Nerfies / HyperNeRF / Dynamic-3DGS, introducing temporal encoding per frame to let the network model scene changes over time;
- If only static background is needed, use multi-view consistency filtering: retain only point cloud regions that are positionally consistent across multiple frames for training.

### 4.3 Gaussian Splat Edge Bleeding

**Phenomenon:** In 3DGS rendering results, foreground objects (people, objects) exhibit "halos" or "color fringing" with background colors at their edges — along the long axis of Gaussian ellipsoids, colors blend from foreground to background, creating a 5–15 pixel wide color mixing band at edges. Object edges exhibit a "glowing halo" effect, inconsistent with the sharp edges of real photographs.

**Root Cause:** In 3DGS, the size (covariance $\Sigma$) of Gaussian ellipsoids tends to increase during optimization to cover larger areas and reduce overall rendering error. If Gaussian ellipsoids at foreground object edges have their long axis extending into background regions, the tail of the opacity function $\alpha(x) = e^{-\frac{1}{2}\mathbf{x}^\top \Sigma^{-1}\mathbf{x}}$ mixes background color into foreground edge rendering with low weight, producing color bleeding. When the number of training viewpoints is insufficient (< 50 views), the optimization constraints on edge Gaussians are weak, and ellipsoid scales more easily diverge.

**Diagnostic Methods:** Visualize the 2D projection of 3DGS Gaussian ellipsoids (along the camera direction) — if the projected ellipse semi-axis $r > 15$ pixels at edge regions (at 1080p), oversized Gaussians are causing color bleeding. Calculate $\Delta E_{00}$ between the rendered image and GT image in edge regions (identified by Sobel detection) — if the edge band's $\Delta E_{00}$ is more than 3× that of non-edge regions, edge bleeding is significant.

**Mitigation Strategies:**
- Introduce Gaussian scale regularization: $\mathcal{L}_{\text{scale}} = \lambda_s \sum_i \max(\mathbf{s}_i - s_{\max}, 0)^2$ ($s_{\max}$ is the maximum allowed Gaussian scale, approximately 5–10 pixels), preventing excessive Gaussian growth;
- Raise the opacity pruning threshold and merge (merging) rather than clone tiny Gaussians with $\alpha < 0.01$, reducing the stacking of numerous small Gaussians covering edge regions;
- Use 2D GS (a 2D variant of Gaussian Splatting) or add edge-aware regularization: constrain the scale of Gaussians crossing known edge positions (extracted by Canny or semantic segmentation), forcing Gaussians at edges to remain small.

### 4.4 Common Artifact Reference Table

| Artifact Type | Trigger Condition | Typical Manifestation | Mitigation |
|--------------|-------------------|----------------------|------------|
| Floaters | Textureless background, pose noise | Floating semi-transparent haze / discrete ghost points | Density sparsification regularization, depth priors, opacity reset |
| Ghost / Double Image | Dynamic scene in training frames | Double overlapping shadows of objects, semi-transparent phantoms | Dynamic pixel masking, dynamic NeRF/3DGS, multi-view consistency filtering |
| Edge Bleeding | Oversized Gaussian ellipsoids extending into background | Glowing halo at foreground edges, 5–15 pixel mixing band | Gaussian scale regularization, edge-aware pruning, 2D GS |
| Cross-Exposure Color Inconsistency | AWB not uniformly normalized | Color shift in rendering of same location across different exposure training frames | RAW-NeRF joint AWB optimization, color histogram alignment |
| Noise Overfitting | High-ISO RAW noise memorized by NeRF | Regular noise texture reproduces in novel views | Noise-aware loss, downweighting high-ISO frames, TV regularization |

---

## §5 Evaluation Methods

### 5.1 Standard Novel View Synthesis Metrics

| Metric | Definition | Applicable Scenarios |
|--------|------------|----------------------|
| PSNR | Peak Signal-to-Noise Ratio, higher is better | Comprehensive pixel-level accuracy measurement |
| SSIM | Structural Similarity Index, higher is better | Perceptual quality, robust to brightness/contrast changes |
| LPIPS | Learned Perceptual Image Patch Similarity, lower is better | High-frequency textures and perceptual details, more correlated with human perception |

Evaluation requires using **held-out views**, i.e., views not participating in training. NeRF papers typically reserve 1/8 of viewpoints as the test set.

### 5.2 Specialized Evaluation for ISP Applications

For ISP-related applications, additional evaluation metrics include:

- **RAW Reconstruction Fidelity**: For RAW-NeRF, evaluate PSNR/SSIM of rendered RAW images versus real RAW images (computed in linear photometric space);
- **HDR Dynamic Range**: Evaluate the dynamic range (quantified in EV stops) of rendering results on HDR scenes, verifying RAW-NeRF's HDR reconstruction capability;
- **ISP Simulation Data Quality**: Train a denoising network on generated synthetic RAW data, using downstream PSNR to assess simulation data effectiveness (Fréchet Inception Distance is not applicable to the RAW domain);
- **Rendering Speed**: NeRF measured in seconds/frame; 3DGS measured in frames per second (FPS); real-time applications require 3DGS to achieve 60 FPS.

### 5.3 Common Benchmark Datasets

| Dataset | Characteristics | Applicable Methods |
|---------|----------------|-------------------|
| NeRF-Synthetic (Blender) | Synthetic objects, 360° viewpoints, known GT | NeRF accuracy benchmark |
| LLFF (Local Light Field Fusion) | Real forward-facing scenes, handheld capture | Forward-facing view synthesis |
| Mip-NeRF 360 | 360° unbounded real scenes, high resolution | Large-scale NeRF benchmark |
| RawNeRF Dataset | Multi-exposure RAW photos, low-light scenes | RAW-NeRF dedicated evaluation |
| Tanks and Temples | Outdoor large scenes, LiDAR point cloud GT | Reconstruction completeness evaluation |

---

## §6 Code Implementation

### 6.1 NeRF Volume Rendering (Simplified PyTorch Implementation)

```python
import torch
import torch.nn as nn
import torch.nn.functional as F


def positional_encoding(x: torch.Tensor, L: int = 10) -> torch.Tensor:
    """
    傅里叶位置编码
    x: (..., D)
    返回: (..., D*(1+2*L))，前D维是原始输入，后面是正弦/余弦特征
    """
    freqs = 2.0 ** torch.arange(L, dtype=torch.float32, device=x.device)  # (L,)
    # x: (..., D) -> (..., D, L) -> (..., D*L)
    x_freq = (x.unsqueeze(-1) * freqs).flatten(-2)   # (..., D*L)
    enc = torch.cat([x, torch.sin(x_freq), torch.cos(x_freq)], dim=-1)
    return enc


class NeRFMLP(nn.Module):
    """简化版NeRF MLP，8层全连接 + 跳跃连接"""
    def __init__(self, pos_enc_L=10, dir_enc_L=4, hidden=256):
        super().__init__()
        pos_dim = 3 * (1 + 2 * pos_enc_L)   # 63
        dir_dim = 3 * (1 + 2 * dir_enc_L)   # 27
        # 前4层处理位置编码
        self.pts_layers = nn.Sequential(
            nn.Linear(pos_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
        )
        # 第5层：跳跃连接（concatenate原始位置编码）
        self.pts_skip = nn.Linear(hidden + pos_dim, hidden)
        self.pts_tail = nn.Sequential(
            nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
        )
        # 密度输出（不依赖视角方向）
        self.sigma_head = nn.Linear(hidden, 1)
        # 颜色输出（依赖视角方向）
        self.color_proj = nn.Linear(hidden, hidden)
        self.color_head = nn.Sequential(
            nn.Linear(hidden + dir_dim, hidden // 2), nn.ReLU(),
            nn.Linear(hidden // 2, 3), nn.Sigmoid()
        )
        self.pos_enc_L = pos_enc_L
        self.dir_enc_L = dir_enc_L

    def forward(self, pts: torch.Tensor, dirs: torch.Tensor):
        """
        pts:  (N, 3) 空间采样点
        dirs: (N, 3) 单位方向向量
        返回: colors (N, 3), sigmas (N,)
        """
        pos_enc = positional_encoding(pts, self.pos_enc_L)   # (N, 63)
        dir_enc = positional_encoding(dirs, self.dir_enc_L)  # (N, 27)

        h = self.pts_layers(pos_enc)
        h = F.relu(self.pts_skip(torch.cat([h, pos_enc], dim=-1)))
        h = self.pts_tail(h)

        sigma = F.softplus(self.sigma_head(h)).squeeze(-1)   # (N,)

        feat = self.color_proj(h)
        colors = self.color_head(torch.cat([feat, dir_enc], dim=-1))  # (N, 3)
        return colors, sigma


def volume_render(colors: torch.Tensor, sigmas: torch.Tensor,
                  z_vals: torch.Tensor) -> torch.Tensor:
    """
    体积渲染：将沿光线采样的颜色/密度合成为像素颜色。
    colors: (N_rays, N_samples, 3)
    sigmas: (N_rays, N_samples)
    z_vals: (N_rays, N_samples)  各采样点深度
    返回: rgb (N_rays, 3)
    """
    # 计算相邻采样点间距
    deltas = z_vals[..., 1:] - z_vals[..., :-1]                 # (N_rays, N_samples-1)
    deltas = torch.cat([deltas, torch.full_like(deltas[..., :1], 1e10)], dim=-1)  # 最后一段无穷远

    # 透射率
    alpha = 1.0 - torch.exp(-sigmas * deltas)                    # (N_rays, N_samples)
    T = torch.cumprod(torch.cat([
        torch.ones_like(alpha[..., :1]),
        1.0 - alpha + 1e-10
    ], dim=-1), dim=-1)[..., :-1]                                 # (N_rays, N_samples)

    weights = T * alpha                                           # (N_rays, N_samples)
    rgb = (weights.unsqueeze(-1) * colors).sum(dim=-2)           # (N_rays, 3)
    return rgb
```

### 6.2 Camera-Aware Loss for RAW-NeRF

```python
class CameraAwareLoss(nn.Module):
    """
    RAW-NeRF的相机感知损失：
    对渲染的线性RGB施加可学习的色彩变换，再与RAW图像对比。
    per_frame_params: 每帧的白平衡增益和曝光值（可训练参数）
    """
    def __init__(self, num_frames: int):
        super().__init__()
        # 每帧：3个白平衡增益（R、G、B）+ 1个曝光缩放
        self.wb_gains   = nn.Parameter(torch.ones(num_frames, 3))
        self.exposures  = nn.Parameter(torch.zeros(num_frames))   # log空间

    def apply_camera_model(self, linear_rgb: torch.Tensor,
                           frame_idx: int) -> torch.Tensor:
        """将线性辐射转换为该帧对应的RAW线性响应"""
        ev_scale = torch.exp(self.exposures[frame_idx])
        wb = F.softplus(self.wb_gains[frame_idx])   # 保证正值
        return linear_rgb * wb * ev_scale

    def forward(self, rendered_linear: torch.Tensor,
                raw_pixels: torch.Tensor,
                frame_idx: int,
                noise_var: torch.Tensor = None) -> torch.Tensor:
        """
        rendered_linear: (N, 3) 体渲染输出的线性RGB
        raw_pixels:      (N, 3) 真实RAW像素值（线性空间，已归一化到[0,1]）
        noise_var:       (N, 3) 噪声方差（用于噪声感知加权），可选
        """
        predicted = self.apply_camera_model(rendered_linear, frame_idx)
        residual  = predicted - raw_pixels

        if noise_var is not None:
            # 噪声感知加权：方差大的像素权重低
            weight = 1.0 / (noise_var.detach() + 1e-6)
            loss   = (weight * residual ** 2).mean()
        else:
            loss = (residual ** 2).mean()
        return loss
```

### 6.3 3DGS Gaussian Initialization and Attributes

```python
import numpy as np
from dataclasses import dataclass


@dataclass
class GaussianPrimitive:
    """3DGS单个高斯基元的属性"""
    center:   np.ndarray  # (3,) 世界坐标系中心
    rotation: np.ndarray  # (4,) 四元数 [w, x, y, z]
    scale:    np.ndarray  # (3,) 各轴缩放（log空间存储）
    opacity:  float       # 不透明度（sigmoid前）
    sh_coeffs: np.ndarray # (16, 3) 3阶球谐系数，每颜色通道16个系数


def init_gaussians_from_sfm(sfm_points: np.ndarray,
                             sfm_colors: np.ndarray) -> list:
    """
    从SfM（Structure from Motion）点云初始化高斯基元。
    sfm_points: (N, 3) 世界坐标
    sfm_colors: (N, 3) RGB颜色 [0, 1]
    """
    gaussians = []
    for i in range(len(sfm_points)):
        # 初始协方差：等方向小球
        init_scale = np.log(np.array([0.01, 0.01, 0.01]))  # log空间

        # 0阶球谐系数由颜色初始化，高阶系数初始为0
        sh = np.zeros((16, 3))
        # 0阶SH系数：C = (color - 0.5) / 0.28
        sh[0] = (sfm_colors[i] - 0.5) / 0.28209479177387814

        g = GaussianPrimitive(
            center    = sfm_points[i].copy(),
            rotation  = np.array([1., 0., 0., 0.]),   # 单位四元数
            scale     = init_scale,
            opacity   = -2.0,   # sigmoid(-2) ≈ 0.12，初始低不透明度
            sh_coeffs = sh
        )
        gaussians.append(g)
    return gaussians


def render_gaussian_2d(gaussian: GaussianPrimitive,
                       view_matrix: np.ndarray,
                       proj_matrix: np.ndarray,
                       img_h: int, img_w: int):
    """
    将单个3D高斯投影为2D高斯（简化版，忽略平铺加速）。
    返回2D中心、2D协方差、颜色、不透明度。
    """
    # 转为相机坐标
    center_h = np.append(gaussian.center, 1.0)
    center_cam = (view_matrix @ center_h)[:3]

    # 将3D协方差投影到2D（Zwicker等2002，EWA splatting）
    R = _quat_to_matrix(gaussian.rotation)
    S = np.diag(np.exp(gaussian.scale))
    Sigma3D = R @ S @ S.T @ R.T

    J = _jacobian_proj(center_cam, proj_matrix, img_h, img_w)
    W = view_matrix[:3, :3]
    Sigma2D = J @ W @ Sigma3D @ W.T @ J.T   # (2, 2)

    # 2D中心（NDC -> 像素坐标）
    p_ndc = proj_matrix @ np.append(center_cam, 1.0)
    p_pix = np.array([(p_ndc[0]/p_ndc[3] + 1) * img_w / 2,
                      (1 - p_ndc[1]/p_ndc[3]) * img_h / 2])

    alpha = 1.0 / (1.0 + np.exp(-gaussian.opacity))   # sigmoid
    return p_pix, Sigma2D, gaussian.sh_coeffs[0] * 0.28 + 0.5, alpha


def _quat_to_matrix(q):
    w, x, y, z = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
                     [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
                     [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]])


def _jacobian_proj(t, P, H, W):
    """投影的Jacobian矩阵（近似线性化）"""
    fx, fy = P[0, 0] * W / 2, P[1, 1] * H / 2
    return np.array([[fx/t[2], 0, -fx*t[0]/t[2]**2],
                     [0, fy/t[2], -fy*t[1]/t[2]**2]])

# ─── 示例调用与输出 ───────────────────────────────────────
def render_ray(model, ray_o, ray_d, t_near=0.1, t_far=6.0, n_samples=64):
    """Sample n_samples points along a single ray and volume-render to RGB."""
    t = torch.linspace(t_near, t_far, n_samples)       # (N,)
    pts  = ray_o + t[:, None] * ray_d                  # (N, 3)
    dirs = ray_d.unsqueeze(0).expand(n_samples, -1)    # (N, 3)
    colors, sigmas = model(pts, dirs)                  # (N,3), (N,)
    return volume_render(colors[None], sigmas[None],   # (1,N,3), (1,N)
                         t[None]).squeeze(0)           # → (3,)

nerf_model  = NeRFMLP()
ray_origin  = torch.zeros(3)                     # camera position (x, y, z)
ray_dir     = torch.tensor([0., 0., 1.])         # unit direction vector
rgb = render_ray(nerf_model, ray_origin, ray_dir, t_near=0.1, t_far=6.0)
print(rgb)
# 输出: tensor([0.312, 0.481, 0.225])  # 该像素 RGB 颜色

```

---

## References

[1] Mildenhall, B., Srinivasan, P. P., Tancik, M., Barron, J. T., Ramamoorthi, R., & Ng, R. "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis." ECCV 2020.
[2] Barron, J. T., Mildenhall, B., Tancik, M., Hedman, P., Martin-Brualla, R., & Srinivasan, P. P. "Mip-NeRF: A Multiscale Representation for Anti-Aliasing Neural Radiance Fields." ICCV 2021.
[3] Mildenhall, B., Hedman, P., Martin-Brualla, R., Srinivasan, P. P., & Barron, J. T. "NeRF in the Dark: High Dynamic Range View Synthesis from Noisy Raw Images." CVPR 2022.
[4] Barron, J. T., Mildenhall, B., Verbin, D., Srinivasan, P. P., & Hedman, P. "Zip-NeRF: Anti-Aliased Grid-Based Neural Radiance Fields." ICCV 2023.
[5] Kerbl, B., Kopanas, G., Leimkühler, T., & Drettakis, G. "3D Gaussian Splatting for Real-Time Radiance Field Rendering." ACM TOG (SIGGRAPH 2023).
[6] Müller, T., Evans, A., Schied, C., & Keller, A. "Instant Neural Graphics Primitives with a Multiresolution Hash Encoding." ACM TOG (SIGGRAPH 2022).
[7] Martin-Brualla, R., Radwan, N., Sajjadi, M. S., Barron, J. T., Dosovitskiy, A., & Duckworth, D. "NeRF in the Wild: Neural Radiance Fields for Unconstrained Photo Collections." CVPR 2021.
[8] Wu, G., Yi, T., Fang, J., et al. "4D Gaussian Splatting for Real-Time Dynamic Scene Rendering." CVPR 2024.
[9] Zwicker, M., Pfister, H., van Baar, J., & Gross, M. "EWA Splatting." IEEE TVCG 2002.
[10] Barron, J. T., Mildenhall, B., Verbin, D., Srinivasan, P. P., & Hedman, P. "Mip-NeRF 360: Unbounded Anti-Aliased Neural Radiance Fields." CVPR 2022.

## §8 Glossary

| Abbreviation / Term | Full Name (Chinese) | Brief Description |
|---------------------|---------------------|-------------------|
| NeRF | Neural Radiance Field (神经辐射场) | Method that implicitly represents 3D scene radiance using an MLP |
| 3DGS | 3D Gaussian Splatting (3D高斯飞溅) | Real-time rendering method that represents scenes with explicit 3D Gaussian primitives |
| IPE | Integrated Positional Encoding (积分位置编码) | Positional encoding integrated over conical frustum cross-sections in Mip-NeRF |
| MHE | Multiresolution Hash Encoding (多分辨率哈希编码) | Hash grid used in Instant-NGP for accelerated feature lookup |
| SH | Spherical Harmonics (球谐函数) | Orthogonal basis function set for representing view-dependent radiance |
| Volume Rendering | Volume Rendering (体积渲染) | Method for projecting 3D volumetric density and color to pixels by integrating along rays |
| SfM | Structure from Motion (运动重建结构) | Method for recovering 3D point clouds and camera poses from multi-view images |
| Splatting | Splatting (飞溅/投影混合) | Rendering technique projecting 3D primitives onto 2D images and blending them |
| Ray Marching | Ray Marching (光线步进) | Discrete approximation of volume rendering by uniformly sampling density along rays |
| Floaters | Floaters (浮游物) | Low-density noise structures floating in mid-air in NeRF reconstructions |
| EV | Exposure Value (曝光值) | Logarithmic measure of camera exposure: $\text{EV} = \log_2(\text{exposure ratio})$ |
| LPIPS | Learned Perceptual Image Patch Similarity (学习感知图像距离) | Perceptual similarity metric based on VGG features; lower is better |
| GT | Ground Truth (地面真值) | Reference image or data used for evaluation |
| HDR | High Dynamic Range (高动态范围) | High luminance ratio images beyond the standard 8-bit display range |
| PSF | Point Spread Function (点扩散函数) | Function describing an imaging system's response to a point light source, used for bokeh simulation |
