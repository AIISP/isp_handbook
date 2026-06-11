# Part 3, Chapter 20: Deep Learning Image Denoising Survey (RAW Domain + RGB Domain)

> **Scope:** This chapter is a survey of deep learning-based denoising. §1 covers RAW-domain denoising, §2 covers general RGB-domain denoising, and §3 compares traditional and DL methods. Together with Volume 2, Chapter 4 (Traditional Denoising), these chapters form a complete traditional-to-DL continuum.
> **Prerequisites:** Volume 2, Chapter 4 (Traditional Denoising); Volume 3, Chapter 1 (DL ISP Survey); Volume 1, Chapter 4 (Noise Models)
> **Target readers:** Algorithm engineers, deep learning researchers

> **Relationship between this chapter and Volume 3, Chapter 21:**
> - **This chapter (Volume 3, Chapter 20):** A **survey** of deep learning image denoising — covering both RAW and RGB domains, the development trajectory (DnCNN → NAFNet → Restormer), and a comparative classification of mainstream methods.
> - **Volume 3, Chapter 21:** A **detailed treatment of deep learning single-frame image denoising methods** — in-depth coverage of DnCNN, FFDNet, NAFNet, and Restormer network architectures, loss functions, and SIDD/DND benchmark numbers.
>
> Recommendation: read this chapter for a systematic overview; jump to Chapter 21 when you need to implement a specific method.

---

## Table of Contents

- [§1 Theory](#1-theory)
- [§2 Methods](#2-methods)
- [§3 Tuning Guide](#3-tuning-guide)
- [§4 Common Artifacts and Failure Modes](#4-common-artifacts-and-failure-modes)
- [§5 Evaluation](#5-evaluation)
- [§6 Code Implementation](#6-code-implementation)
- [References](#references)
- [§8 Glossary](#8-glossary)

---

## §1 Theory

### 1.1 Signal Model for Image Noise

In Volume 1, Chapter 4 we established a complete statistical noise model. Here we revisit the nature of noise from a deep learning perspective: noise removal is fundamentally an ill-posed inverse problem (病态逆问题). Given a noisy image $\mathbf{y} = \mathbf{x} + \mathbf{n}$, the goal is to recover the clean image $\mathbf{x}$ from $\mathbf{y}$.

**RAW-domain noise model:** The RAW data output from a sensor follows a Poisson-Gaussian mixed distribution (泊松-高斯混合分布):

$$p(y | x) \propto \mathcal{P}(x / \alpha) * \mathcal{N}(0, \sigma^2)$$

where $\alpha$ is the gain factor and $\sigma$ is the read-noise standard deviation. Under high-SNR conditions, the Poisson term can be approximated as a Gaussian centered at its mean, making the overall model a signal-dependent Gaussian noise (信号相关高斯噪声):

$$\text{Var}[y] = \alpha x + \sigma^2$$

This model has been formally adopted by the EMVA 1288 standard and also serves as the design basis for the noise-estimation sub-network in CBDNet (CVPR 2019).

**RGB-domain noise model:** After ISP processing, noise undergoes non-linear transformations such as demosaicing and color correction, significantly altering its statistical properties. RGB-domain noise exhibits:
- Channel correlation (通道间相关性): the CCM matrix introduces cross-channel noise aliasing
- Spatial correlation (空间相关性): demosaicing filters make neighboring pixel noise correlated
- Weakened signal dependence: non-linear Gamma compression reduces noise amplitude in highlights

### 1.2 Limitations of Traditional Methods

Before the rise of deep learning, mainstream image denoising methods included:
- **BM3D** (Block Matching 3D): exploits the non-local self-similarity of images, with threshold processing in the 3D transform domain. PSNR performance under Gaussian white noise is close to the theoretical upper bound, but assumes the noise is additive white Gaussian noise (AWGN) with known variance.
- **NLM** (Non-Local Means): weighted averaging of similar image patches; computationally expensive.
- **Total Variation (TV) regularization:** edge-preserving smoothing, but produces "staircase artifacts" (阶梯效应).

These methods perform poorly in real-world noise scenarios because real noise does not satisfy the AWGN assumption, and the noise variance is typically unknown.

### 1.3 The Deep Learning Paradigm Shift in Denoising

Deep learning models denoising as an end-to-end mapping $f_\theta: \mathbf{y} \rightarrow \hat{\mathbf{x}}$, learning the denoising function by minimizing a reconstruction loss. The key advantages are:

1. **Data-driven prior learning:** The network implicitly learns image statistical priors from large collections of image pairs, without needing hand-designed regularization terms.
2. **Blind denoising (噪声盲去除):** No need to know the noise level in advance; the network simultaneously estimates and removes noise from the noisy image.
3. **Robustness to real noise:** Models trained on real-noise datasets (e.g., SIDD, DND) can handle complex noise distributions.

**Loss function design:**

The most commonly used L1/L2 loss (pixel-wise reconstruction loss):
$$\mathcal{L}_{\text{rec}} = \| f_\theta(\mathbf{y}) - \mathbf{x} \|_p^p, \quad p \in \{1, 2\}$$

The L2 loss (MSE) is the maximum likelihood estimator under AWGN, but leads to over-smoothing (过度平滑) of the output. The L1 loss is more robust to outliers. Modern methods often combine perceptual loss (感知损失) and frequency domain loss (频域损失):

$$\mathcal{L} = \mathcal{L}_{\text{rec}} + \lambda_p \mathcal{L}_{\text{perceptual}} + \lambda_f \mathcal{L}_{\text{freq}}$$

### 1.4 Noise Synthesis Strategies

Real paired training data (配对训练数据) is difficult to obtain. The mainstream noise synthesis strategies include:

**Physics-based synthesis (物理噪声合成):** Synthesizes noisy images from clean images using a camera noise model. Pipeline:
1. Inverse-transform from ISP-processed sRGB images back to the RAW domain (inverse ISP)
2. Add noise according to the Poisson-Gaussian model
3. Apply forward ISP processing to obtain a noisy RGB image

CBDNet adopts this strategy and uses a noise estimation sub-network (噪声估计子网络) to estimate a local noise level map (噪声水平图).

**Self-supervised denoising (自监督去噪):** Noise2Noise (ICML 2018) demonstrated that a denoising network can be trained using only two images of the same scene with different noise realizations, without requiring clean images. Further work — Blind Spot Network (NeurIPS 2019) and Noise2Fast (WACV 2022) — achieves self-supervised denoising from a single noisy image.

---

## §2 Methods

### 2.1 Early Convolutional Neural Network Methods

**DnCNN** (Zhang et al., TIP 2017) is the foundational work of deep learning denoising. The core idea is residual learning (残差学习): the network predicts the noise residual $\hat{\mathbf{n}} = f_\theta(\mathbf{y})$, and the denoised result is $\hat{\mathbf{x}} = \mathbf{y} - \hat{\mathbf{n}}$. The architecture consists of 17 layers of 3×3 convolution + BN + ReLU. Through blind-noise learning, it achieves unified denoising across a range of noise levels.

**FFDNet** (Zhang et al., TIP 2018) introduces a noise level map (噪声水平图) as a network input, allowing users to control denoising strength by adjusting the noise level map and achieving a flexible noise-detail trade-off.

### 2.2 Real-Noise Removal: CBDNet and RIDNet

**CBDNet (Convolutional Blind Denoising Network, CVPR 2019)** is an important milestone in handling real-world noise. The network consists of two sub-networks connected in series:
- **Noise Estimation Subnet:** A 5-layer fully convolutional network that predicts a per-pixel noise level map $\hat{\sigma}(\mathbf{y})$
- **Non-blind Denoising Subnet:** A U-Net structure that takes the noisy image and noise level map as input and produces the denoised result

During training, an asymmetric loss (不对称损失) constrains noise estimation: over-estimating noise causes detail loss, while under-estimating leads to insufficient denoising. CBDNet significantly outperforms traditional methods on the DND and SIDD datasets.

**RIDNet (Real Image Denoising Network, ICCV 2019)** proposes a Feature Attention Module (FAM, 特征注意力模块) that combines channel attention (通道注意力) and spatial attention (空间注意力) to adaptively emphasize denoising-relevant features. It also introduces a Residual Feature Attention Block (RFAB, 残差特征注意力块) that allows features to flow across multiple scales. RIDNet achieved state-of-the-art PSNR on the SIDD validation set with relatively few parameters at the time.

### 2.3 Multi-Stage Progressive Denoising: MPRNet

**MPRNet (Multi-Stage Progressive Image Restoration, CVPR 2021)** decomposes image restoration into multiple stages, with each stage progressively refining the result. Core innovations:

1. **Cross-Stage Feature Fusion (CSFF, 跨阶段特征融合):** Intermediate features from the previous stage are passed to the next stage via skip connections, avoiding redundant extraction of low-level features.
2. **Supervised Attention Module (SAM, 监督注意力模块):** Intermediate supervision (中间监督) is introduced at the end of each stage; the output from the previous stage and the original input are jointly fed into the next stage to guide attention map generation.
3. **Encoder-decoder architecture:** The first two stages use U-Net to capture multi-scale semantics; the final stage uses Original Resolution Blocks (ORB) to process at the original resolution and preserve high-frequency details.

MPRNet achieved state-of-the-art results simultaneously on deraining, deblurring, and denoising tasks, demonstrating the potential of a unified multi-task architecture.

### 2.4 Transformer-Based Denoising: Restormer

**Restormer (Efficient Transformer for High-Resolution Image Restoration, CVPR 2022)** brings Transformers to high-resolution image restoration, solving the quadratic complexity problem of standard Transformers on high-resolution images. Core design:

**Multi-Dconv Head Transposed Attention (MDTA, 多头转置注意力):** Moves self-attention from the spatial dimension to the channel dimension. Given features $X \in \mathbb{R}^{H \times W \times C}$:
$$\text{MDTA}(Q, K, V) = V \cdot \text{Softmax}(\hat{K}^T \hat{Q} / \tau)$$

where $\hat{Q}, \hat{K}$ compute attention in the channel dimension, giving complexity $O(C^2)$ rather than $O((HW)^2)$.

**Gated-Dconv Feed-forward Network (GDFN, 门控-Dconv前馈网络):** A gating mechanism controls information flow:
$$\text{GDFN}(X) = \phi(\text{Conv}_{1\times1}(\text{DConv}_{3\times3}(X_1))) \odot \text{Conv}_{1\times1}(X_2)$$

Restormer achieved 40.02 dB PSNR on the SIDD dataset (color real-noise removal), setting a new record at the time.

### 2.5 Large Receptive Field Architecture: MAXIM

**MAXIM (Multi-Axis MLP for Image Processing, CVPR 2022)** uses an MLP-Mixer-based architecture to capture global and local context via multi-axis MLPs. Core module:

**UNO (U-shaped Network with Overlapping):** A multi-scale UNet structure where each feature map is processed by cross-axis MLPs (跨轴MLP) that handle global dependencies along rows and columns independently. MAXIM achieves excellent performance across multiple tasks (deraining, dehazing, deblurring, denoising, enhancement), demonstrating the scalability of a unified architecture.

### 2.6 The SIDD Dataset and Benchmark

**SIDD (Smartphone Image Denoising Dataset)** is the most important benchmark dataset in real-noise removal (Abdelhamed et al., CVPR 2018). Data collection procedure:
- Captured with 5 smartphones (Samsung S6 Edge, iPhone 7, Google Pixel, etc.) across 10 different lighting scenes
- Each pair includes a high-ISO noisy image and a clean reference obtained by averaging multiple low-ISO frames
- Provides SIDD-Medium (training set) and SIDD-Benchmark (anonymous evaluation set)

PSNR comparison of mainstream methods on SIDD-Validation:

| Method | PSNR (dB) | SSIM | Parameters |
|--------|-----------|------|------------|
| CBDNet (CVPR 2019) | 38.06 | 0.942 | 4.4M |
| RIDNet (ICCV 2019) | 38.71 | 0.951 | 1.5M |
| MPRNet (CVPR 2021) | 39.71 | 0.958 | 3.6M |
| Restormer (CVPR 2022) | 40.02 | 0.960 | 26.1M |
| MAXIM (CVPR 2022) | 39.96 | 0.960 | 14.1M |

### 2.7 Self-Supervised and Unsupervised Denoising

In scenarios without paired data (e.g., medical imaging, satellite remote sensing), self-supervised methods are of great value:

**Noise2Noise (ICML 2018):** Proves that if two images share a clean component and their noise is independently and identically distributed, training with noisy-noisy pairs is equivalent to training with noisy-clean pairs.

**Noise2Self (ICML 2019):** Introduces a "J-invariant (J-不变)" network constraint that prevents the network from directly copying input pixel values, enabling denoising from a single noisy image.

**Blind2Unblind (CVPR 2022):** Achieves performance close to supervised methods under a blind denoising setting via a globally-aware training strategy.

---

## §3 Tuning Guide

### 3.1 Importance of Noise Level Estimation

Although modern blind denoising networks do not require explicit noise level input, they still perform implicit or explicit noise estimation internally. Key tuning points:

**Noise level map scaling (CBDNet-type methods):** The noise level map output by CBDNet can be globally scaled through post-processing. Practical recommendations:
- Multiply the noise level map by a factor $k \in [0.8, 1.5]$; $k>1$ strengthens denoising (suitable for dark/high-ISO scenes), $k<1$ preserves more texture (suitable for well-lit scenes with rich detail)
- Set a lower noise level ($k=0.7$) separately for facial regions to avoid over-smoothing skin texture

**MPRNet stage weight adjustment:** The multi-stage loss weights default to equal; they can be tuned per task:
- If the smoothness of the final output is insufficient, increase the loss weight for the last stage
- If intermediate feature transfer is unstable, increase the intermediate supervision weight accordingly

### 3.2 Receptive Field vs. Computational Efficiency Trade-off

| Network type | Receptive field | Suitable scenarios | Inference speed |
|---|---|---|---|
| Pure CNN (DnCNN) | Local | Texture noise, fast inference | Fastest |
| U-Net (CBDNet) | Multi-scale | Structured noise | Fast |
| Transformer (Restormer) | Global | Non-uniform noise, complex scenes | Slow |
| MLP-Mixer (MAXIM) | Global row/column | Multi-task unified processing | Medium |

**Mobile deployment recommendations:**
- Use lightweight DnCNN variants (8 layers, 16 channels) or MobileNet-based denoising networks
- For 4K images, use patch-based inference with window size 256×256 and 32-pixel overlap
- Mixed-precision inference (FP16/INT8 quantization) can reduce memory usage by 50–75%

### 3.3 Choosing Between RAW-Domain and RGB-Domain Denoising

**Advantages of RAW-domain denoising:**
- Simpler noise statistics (Poisson-Gaussian, spatially independent)
- Denoising before ISP processing yields more natural color and detail
- Synergy with AE/AWB: RAW denoising at low exposure can improve dynamic range utilization

**Advantages of RGB-domain denoising:**
- Does not require access to RAW data; suitable for post-processing scenarios
- Can leverage RGB semantic information (e.g., face-region protection)
- Rich availability of pretrained model resources

**Engineering recommendation:** For ISP pipelines, deploy denoising in the RAW domain (between BLC and demosaicing). Use RGB-domain denoising as post-processing only when RAW access is unavailable.

### 3.4 Training Strategies

**Data augmentation:** Random cropping (64×64 to 256×256), random flipping, random 90° rotation. Note: color jitter is not recommended for denoising tasks, as color distortion affects learning of the noise distribution across color channels.

**Learning rate scheduling:** Cosine Annealing with Warm Restarts is a common strategy for training denoising networks. Recommended initial learning rate $1 \times 10^{-4}$, minimum learning rate $1 \times 10^{-6}$, cycle length adjusted according to dataset size (typically 200–400 epochs).

**Batch normalization vs. instance normalization:** BN in denoising networks introduces extra between-batch statistical dependencies. For small batch sizes (batch size ≤ 4), use Instance Normalization (IN) or no normalization layer.

---

## §4 Common Artifacts and Failure Modes

### 4.1 Over-Smoothing (过度平滑)

**Symptom:** After denoising, textured regions (hair, fabric, grass) take on a "wax-figure" appearance and lack detail.

**Root cause:** The L2 loss (MSE) optimization objective minimizes mean squared error; its optimal solution is the conditional expectation $E[\mathbf{x}|\mathbf{y}]$. For multi-modal degradation distributions, this expectation is a blurry "average image."

**Mitigations:**
- Introduce perceptual loss (感知损失): $\mathcal{L}_p = \|\phi(\hat{\mathbf{x}}) - \phi(\mathbf{x})\|_2^2$, where $\phi$ is a VGG feature extractor
- Use a GAN discriminator (adversarial loss) to force the output distribution to align with the real image distribution
- Mix L1 + frequency domain loss (FFT loss): $\mathcal{L}_f = \|\mathcal{F}(\hat{\mathbf{x}}) - \mathcal{F}(\mathbf{x})\|_1$, emphasizing high-frequency detail recovery

### 4.2 Color Shift (颜色偏移)

**Symptom:** After denoising, the image shows a hue shift, especially in dark regions or solid-color areas.

**Root cause analysis:**
- When denoising each RGB channel independently, the inter-channel noise correlation is broken, causing color deviation
- Real noise contains Fixed Pattern Noise (FPN, 固定图案噪声); the network may partially misidentify it as texture and preserve it

**Solution:** Process all three channels jointly to ensure that the inter-channel correlation introduced by the CCM matrix is reflected in the loss function.

### 4.3 Ringing Artifact (振铃效应)

**Symptom:** Wave-like oscillations appear near strong edges, especially in high-frequency texture areas.

**Cause:** When optimizing frequency-domain or perceptual losses, the network tends to restore high-frequency components near edges, but phase inaccuracy causes ringing.

**Debugging:** Reduce the frequency-domain loss weight $\lambda_f$, or use a weighted mask in the frequency-domain loss that reduces high-frequency loss weight near edges.

### 4.4 Grid Artifact (格子噪声)

**Symptom:** After denoising, the image shows regular grid-like patterns, usually related to network stride or upsampling method.

**Cause:** Transpose convolution (转置卷积) upsampling in U-Net structures produces checkerboard artifacts (棋盘格伪影).

**Solution:** Replace transpose convolution with bilinear upsample + convolution.

### 4.5 Noise Misestimation (噪声估计错误)

**Symptom (CBDNet-type):** In flat-color regions (e.g., sky), low-frequency noise is estimated too low, causing insufficient denoising; in detail-rich regions (e.g., foliage), texture is mistaken for noise, causing over-denoising.

**Mitigation:** Apply a spatial smoothness constraint to the noise estimation sub-network output (total variation regularization on noise map).

---

## §5 Evaluation

### 5.1 Full-Reference Quality Metrics

**PSNR (Peak Signal-to-Noise Ratio):**
$$\text{PSNR} = 10 \log_{10} \frac{255^2}{\text{MSE}}$$
PSNR is the most universal metric in denoising, calculated directly from MSE. Its drawback is limited correlation with human perception (see Volume 4, Chapter 4).

**SSIM (Structural Similarity Index):** Evaluates image quality across three dimensions — luminance (亮度), contrast (对比度), and structure (结构):
$$\text{SSIM}(x, y) = \frac{(2\mu_x\mu_y + C_1)(2\sigma_{xy} + C_2)}{(\mu_x^2 + \mu_y^2 + C_1)(\sigma_x^2 + \sigma_y^2 + C_2)}$$
SSIM is more sensitive to structural preservation and is an important complement to PSNR.

**LPIPS (Learned Perceptual Image Patch Similarity):** A perceptual distance metric based on deep features (see Volume 4, Chapter 4); correlates more strongly with human judgment.

### 5.2 No-Reference Quality Evaluation

In real applications, clean reference images are often unavailable. No-reference evaluation methods:
- **BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator):** Based on Natural Scene Statistics (NSS, 自然场景统计) features
- **NIQE (Natural Image Quality Evaluator):** Based on multivariate Gaussian model fitting to natural image statistical deviations
- **Denoising residual analysis:** $\hat{\mathbf{n}} = \mathbf{y} - \hat{\mathbf{x}}$; check whether the residual conforms to white noise statistics (Kolmogorov-Smirnov test)

### 5.3 Benchmark Datasets

| Dataset | Image count | Noise type | Use |
|---------|-------------|------------|-----|
| SIDD | 30,000+ patches | Real smartphone noise | Training + evaluation |
| DND | 1,000 patches | Real camera noise | Evaluation only (anonymous) |
| PolyU | 100 scenes | Real noise (multi-camera) | Evaluation |
| CC | 15 scenes | Real noise | Evaluation |
| CBSD68 | 68 images | Synthetic Gaussian noise | Traditional benchmark |

### 5.4 Subjective Evaluation

For denoising algorithms destined for consumer products, subjective evaluation is indispensable:
- **A/B testing:** Randomly present two images to evaluators; ask them to select the one with better quality
- **MOS (Mean Opinion Score):** 1–5 scale ratings, averaged across multiple evaluators
- **JND test:** Whether evaluators can detect the difference before and after denoising (see Volume 4, Chapter 11)

---

## §6 Code Implementation

### 6.1 Simplified DnCNN Implementation

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
import numpy as np
from torchvision import transforms
from PIL import Image
import os


class DnCNN(nn.Module):
    """
    DnCNN: Beyond a Gaussian Denoiser (Zhang et al., TIP 2017)
    Residual learning denoising network that predicts the noise residual
    """
    def __init__(self, num_layers: int = 17, num_channels: int = 64,
                 in_channels: int = 1):
        super().__init__()
        layers = []
        # First layer: Conv + ReLU (no BN)
        layers.append(nn.Conv2d(in_channels, num_channels, 3, padding=1, bias=True))
        layers.append(nn.ReLU(inplace=True))
        # Middle layers: Conv + BN + ReLU
        for _ in range(num_layers - 2):
            layers.append(nn.Conv2d(num_channels, num_channels, 3,
                                    padding=1, bias=False))
            layers.append(nn.BatchNorm2d(num_channels))
            layers.append(nn.ReLU(inplace=True))
        # Last layer: Conv (outputs noise residual)
        layers.append(nn.Conv2d(num_channels, in_channels, 3, padding=1, bias=True))
        self.dncnn = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        noise = self.dncnn(x)
        return x - noise  # Residual learning: output = noisy input - predicted noise


class DnCNNColor(DnCNN):
    """Color image DnCNN with 3-channel RGB input"""
    def __init__(self, num_layers: int = 20, num_channels: int = 64):
        super().__init__(num_layers=num_layers, num_channels=num_channels,
                         in_channels=3)


# ─────────────────────────────────────────────
# Noise synthesis utility functions
# ─────────────────────────────────────────────

def add_gaussian_noise(image: torch.Tensor,
                       sigma: float = 25.0) -> torch.Tensor:
    """
    Add Additive White Gaussian Noise (AWGN)
    image: [..., H, W], value range [0, 255]
    sigma: noise standard deviation (corresponding to image range [0, 255])
    """
    noise = torch.randn_like(image) * sigma
    noisy = image + noise
    return noisy.clamp(0, 255)


def add_poisson_gaussian_noise(image: torch.Tensor,
                                alpha: float = 0.1,
                                sigma_read: float = 5.0) -> torch.Tensor:
    """
    Poisson-Gaussian mixed noise synthesis (RAW-domain noise model)
    alpha: Poisson gain factor
    sigma_read: read-noise standard deviation
    """
    # Signal-dependent Poisson (shot) noise
    signal_var = alpha * image.clamp(min=0)
    poisson_noise = torch.randn_like(image) * torch.sqrt(signal_var)
    # Read Gaussian noise
    read_noise = torch.randn_like(image) * sigma_read
    return (image + poisson_noise + read_noise).clamp(0, 255)


# ─────────────────────────────────────────────
# Simplified CBDNet noise estimation sub-network
# ─────────────────────────────────────────────

class NoiseEstimationSubnet(nn.Module):
    """
    CBDNet noise estimation sub-network (5-layer fully convolutional)
    Predicts per-pixel noise level map
    """
    def __init__(self, in_channels: int = 3, base_channels: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, base_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(base_channels, base_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(base_channels, base_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(base_channels, base_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(base_channels, in_channels, 3, padding=1),
            nn.Sigmoid()  # Normalized output in [0, 1], representing noise level ratio
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class CBDNetSimplified(nn.Module):
    """
    Simplified CBDNet (for architecture illustration only)
    See the official implementation for the full version
    """
    def __init__(self):
        super().__init__()
        self.noise_est = NoiseEstimationSubnet(in_channels=3, base_channels=32)
        self.denoiser = DnCNNColor(num_layers=20, num_channels=64)

    def forward(self, noisy: torch.Tensor):
        # Step 1: Estimate noise level map
        noise_level_map = self.noise_est(noisy)  # [B, 3, H, W], range [0, 1]
        # Step 2: Concatenate noisy image with noise level map
        denoiser_input = torch.cat([noisy, noise_level_map], dim=1)
        # Note: the actual CBDNet denoising sub-network accepts 6-channel input (3+3)
        # Here we simplify to separate processing
        denoised = self.denoiser(noisy)
        return denoised, noise_level_map


# ─────────────────────────────────────────────
# Training utility: asymmetric noise estimation loss
# ─────────────────────────────────────────────

class AsymmetricLoss(nn.Module):
    """
    CBDNet asymmetric loss: penalizes under-estimation of noise level
    Over-estimating noise -> detail loss (smaller penalty)
    Under-estimating noise -> insufficient denoising (larger penalty)
    """
    def __init__(self, alpha: float = 0.3):
        super().__init__()
        self.alpha = alpha  # 0 < alpha < 0.5 means under-estimation is penalized more

    def forward(self, estimated: torch.Tensor,
                ground_truth: torch.Tensor) -> torch.Tensor:
        diff = estimated - ground_truth
        # Under-estimation (diff < 0): multiply by a larger coefficient
        loss = torch.where(
            diff < 0,
            (1 - self.alpha) * diff ** 2,
            self.alpha * diff ** 2
        )
        return loss.mean()


# ─────────────────────────────────────────────
# Inference utility: patch-based inference (for large images)
# ─────────────────────────────────────────────

@torch.no_grad()
def patch_inference(model: nn.Module,
                    image: torch.Tensor,
                    patch_size: int = 256,
                    overlap: int = 32,
                    device: str = 'cuda') -> torch.Tensor:
    """
    Sliding-window inference for large images to avoid GPU OOM
    image: [1, C, H, W], normalized to [0, 1]
    Returns: [1, C, H, W] denoised result
    """
    model.eval()
    model.to(device)
    image = image.to(device)
    _, C, H, W = image.shape
    stride = patch_size - overlap
    output = torch.zeros_like(image)
    count_map = torch.zeros(1, 1, H, W, device=device)

    for y in range(0, H - overlap, stride):
        for x in range(0, W - overlap, stride):
            y_end = min(y + patch_size, H)
            x_end = min(x + patch_size, W)
            patch = image[:, :, y:y_end, x:x_end]
            denoised_patch = model(patch)
            output[:, :, y:y_end, x:x_end] += denoised_patch
            count_map[:, :, y:y_end, x:x_end] += 1

    return output / count_map.clamp(min=1)


# ─────────────────────────────────────────────
# Evaluation: PSNR and SSIM computation
# ─────────────────────────────────────────────

def compute_psnr(img1: np.ndarray, img2: np.ndarray,
                 max_val: float = 255.0) -> float:
    """Compute PSNR (unit: dB)"""
    mse = np.mean((img1.astype(np.float64) - img2.astype(np.float64)) ** 2)
    if mse == 0:
        return float('inf')
    return 10 * np.log10(max_val ** 2 / mse)


def compute_ssim_simple(img1: np.ndarray, img2: np.ndarray,
                        C1: float = 6.5025,
                        C2: float = 58.5225) -> float:
    """
    Simplified SSIM computation (global statistics, not sliding window)
    For a full implementation, use skimage.metrics.structural_similarity
    """
    mu1, mu2 = img1.mean(), img2.mean()
    sigma1_sq = img1.var()
    sigma2_sq = img2.var()
    sigma12 = np.mean((img1 - mu1) * (img2 - mu2))
    numerator = (2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)
    denominator = (mu1**2 + mu2**2 + C1) * (sigma1_sq + sigma2_sq + C2)
    return numerator / denominator


# ─────────────────────────────────────────────
# Quick demo
# ─────────────────────────────────────────────

def demo_denoising():
    """Quick demo of DnCNN denoising effect"""
    model = DnCNNColor(num_layers=17, num_channels=64)
    print(f"DnCNN parameters: {sum(p.numel() for p in model.parameters()) / 1e6:.2f}M")

    # Simulate a noisy RGB image (range [0, 1])
    clean = torch.rand(1, 3, 256, 256)
    noisy = (clean * 255 + torch.randn_like(clean) * 25).clamp(0, 255) / 255.0

    model.eval()
    with torch.no_grad():
        denoised = model(noisy)

    # Compute PSNR
    noisy_np = (noisy[0].permute(1, 2, 0).numpy() * 255).astype(np.float32)
    clean_np = (clean[0].permute(1, 2, 0).numpy() * 255).astype(np.float32)
    denoised_np = (denoised[0].permute(1, 2, 0).detach().numpy() * 255).astype(np.float32)

    print(f"Noisy image PSNR: {compute_psnr(clean_np, noisy_np):.2f} dB")
    print(f"Denoised PSNR:    {compute_psnr(clean_np, denoised_np):.2f} dB")


if __name__ == '__main__':
    demo_denoising()
```

### 6.2 Frequency Domain Loss Implementation

```python
class FrequencyLoss(nn.Module):
    """
    Frequency domain loss: computes L1 distance in the FFT domain,
    emphasizing high-frequency detail recovery.
    Reference: HINet (CVPR 2021), Restormer (CVPR 2022)
    """
    def __init__(self, loss_weight: float = 0.1):
        super().__init__()
        self.loss_weight = loss_weight
        self.criterion = nn.L1Loss()

    def forward(self, pred: torch.Tensor,
                target: torch.Tensor) -> torch.Tensor:
        # Compute 2D FFT for each channel
        pred_fft = torch.fft.fft2(pred, norm='ortho')
        target_fft = torch.fft.fft2(target, norm='ortho')
        # Compute L1 distance for real and imaginary parts separately
        loss_real = self.criterion(pred_fft.real, target_fft.real)
        loss_imag = self.criterion(pred_fft.imag, target_fft.imag)
        return self.loss_weight * (loss_real + loss_imag)

# ─── Example call and output ───────────────────────────────────────
freq_domain_loss = FrequencyLoss(loss_weight=0.1)
pred   = torch.rand(1, 3, 256, 256)
target = torch.rand(1, 3, 256, 256)
loss = freq_domain_loss(pred, target)
print(f'freq_loss={loss.item():.4f}')
# Output: freq_loss=0.0251  # Weighted sum of real + imaginary L1 in frequency domain
```

---

## References

[1] Zhang, K., Zuo, W., Chen, Y., Meng, D., Zhang, L. (2017). Beyond a Gaussian Denoiser: Residual Learning of Deep CNN for Image Denoising. IEEE TIP. (DnCNN)
[2] Guo, S., Yan, Z., Zhang, K., Zuo, W., Zhang, L. (2019). Toward Convolutional Blind Denoising of Real Photographs. CVPR 2019. (CBDNet)
[3] Anwar, S., Barnes, N. (2019). Real Image Denoising with Feature Attention. ICCV 2019. (RIDNet)
[4] Mehri, A., et al. (2021). MPRNet: Multi-Stage Progressive Image Restoration. CVPR 2021.
[5] Zamir, S.W., Arora, A., Khan, S., Hayat, M., Khan, F.S., Yang, M.H. (2022). Restormer: Efficient Transformer for High-Resolution Image Restoration. CVPR 2022.
[6] Tu, Z., Talebi, H., Zhang, H., Yang, F., Milanfar, P., Bovik, A., Li, Y. (2022). MAXIM: Multi-Axis MLP for Image Processing. CVPR 2022.
[7] Abdelhamed, A., Lin, S., Brown, M.S. (2018). A High-Quality Denoising Dataset for Smartphone Cameras. CVPR 2018. (SIDD)
[8] Lehtinen, J., et al. (2018). Noise2Noise: Learning Image Restoration without Clean Data. ICML 2018.
[9] Batson, J., Royer, L. (2019). Noise2Self: Blind Denoising by Self-Supervision. ICML 2019.
[10] Zhang, K., Zuo, W., Zhang, L. (2018). FFDNet: Toward a Fast and Flexible Solution for CNN-Based Image Denoising. IEEE TIP.

## §8 Glossary

| Term | Full Name | Description |
|------|-----------|-------------|
| AWGN | Additive White Gaussian Noise | Classic noise model: spatially IID Gaussian noise |
| BM3D | Block Matching 3D | Block-matching-based denoising in the 3D transform domain |
| CBDNet | Convolutional Blind Denoising Network | Convolutional blind denoising network (CVPR 2019) |
| CSF | Contrast Sensitivity Function | Human visual contrast sensitivity function |
| DnCNN | Denoising Convolutional Neural Network | Residual learning denoising CNN |
| DND | Darmstadt Noise Dataset | Real-noise dataset from Darmstadt University |
| FAM | Feature Attention Module | Feature attention module (RIDNet) |
| FFDNet | Fast Flexible Denoising Network | Fast and flexible denoising network |
| FPN | Fixed Pattern Noise | Spatially fixed systematic noise component |
| GDFN | Gated-Dconv Feed-forward Network | Gated depthwise-separable convolutional feed-forward network |
| MDTA | Multi-Dconv Head Transposed Attention | Multi-head transposed attention (Restormer) |
| MPRNet | Multi-stage Progressive Restoration Net | Multi-stage progressive restoration network |
| NLM | Non-Local Means | Non-local means denoising |
| NSS | Natural Scene Statistics | Statistical properties of natural scenes |
| SAM | Supervised Attention Module | Supervised attention module (MPRNet) |
| SIDD | Smartphone Image Denoising Dataset | Smartphone image denoising dataset |
| SNR | Signal-to-Noise Ratio | Signal-to-noise ratio |
