# Part 3, Chapter 21: DL Single-Image Denoising (Merged into Chapter 20)

> **This chapter's content has been consolidated into Volume 3 Chapter 20:
> "Deep Learning Image Denoising: From Residual Learning to Diffusion Models"**
>
> All content is now available in Chapter 20, including:
> - Classical methods (DnCNN / FFDNet / CBDNet / NAFNet) with full architecture derivations
> - NLF maximum likelihood estimation derivation (EMVA 1288 Photon Transfer Curve)
> - Self-supervised denoising (Noise2Noise / Blind2Unblind / Noise2Fast)
> - Diffusion-based denoising (Cold Diffusion / DiffIR two-stage framework)
> - Real camera noise modeling (ELD 4-parameter calibration / CycleISP domain transfer)
> - INT8 quantization analysis and NPU deployment strategies
>
> → Please read **Volume 3 Chapter 20** directly

> **Chapter positioning note (division of scope with Volume 2, Chapter 3)**
> Volume 2, Chapter 3 (`part2_traditional_isp/ch03_denoising`) covers **traditional algorithms and classical DL methods**: complete derivations and engineering tuning for BM3D, NLM, and DnCNN. This chapter focuses on **advances from 2020–2025**: diffusion-model denoising (Cold Diffusion / DiffIR), self-supervised denoising paradigms (Noise2Noise / Blind2Unblind / Noise2Fast), real camera noise modeling (SIDD / ELD / CycleISP), and engineering deployment details such as INT8 quantization and NPU frame-rate targets. The two chapters are complementary; the recommended reading order is Volume 2, Chapter 3 for fundamentals, then this chapter for the latest directions.

---

## §1 Theory

### 1.1 Problem Definition and Noise Models for Single-Image Denoising

The goal of single-image denoising (单帧图像去噪) is to estimate a clean image $x$ from a single noisy observation $y = x + n$, where $n$ is the noise component. The accuracy of the noise model directly determines algorithmic design choices.

**Additive White Gaussian Noise (AWGN):** $n \sim \mathcal{N}(0, \sigma^2 I)$, the most commonly used theoretical noise model. AWGN assumes noise is spatially IID, which holds approximately in the sRGB domain after ISP processing (AGC, gamma, and other non-linear operations), but is not accurate in the RAW domain.

**Poisson-Gaussian Noise (泊松-高斯噪声):** Real camera noise in the RAW domain is more accurately modeled as a Poisson-Gaussian mixture:

$$n = \underbrace{n_\text{shot}}_{\text{shot noise}} + \underbrace{n_\text{read}}_{\text{read noise}}$$

where shot noise $n_\text{shot} \sim \mathcal{P}(\lambda x / K)$ ($K$ = camera gain, $\lambda$ = photon flux), and read noise $n_\text{read} \sim \mathcal{N}(0, \sigma_r^2)$. For high photon counts, the Poisson distribution approaches a Gaussian whose variance equals its mean, so the overall model approximates a **non-stationary Gaussian with signal-dependent variance**:

$$\text{Var}[y | x] \approx \frac{x}{K} + \sigma_r^2 \tag{1}$$

This heteroscedastic noise (信号依赖方差) must be explicitly modeled when processing in the RAW domain; otherwise the denoising network will over-smooth low-light regions (high noise variance) and under-process highlights.

**Real Camera Noise:** Real sensors additionally exhibit Fixed Pattern Noise (FPN, 固定模式噪声), row/column noise, and banding noise — spatially correlated components that violate the spatial-independence assumption and challenge denoising methods designed for independent noise (e.g., blind-spot networks).

---

### 1.2 Classical Deep Denoising Baselines: DnCNN and FFDNet

**DnCNN** (Zhang et al., TIP 2017) is a milestone work in deep learning image denoising. Its architecture is clean:

- 17 layers of $3\times3$ Conv + BatchNorm + ReLU;
- Output: **noise residual** $\hat{n} = f_\theta(y)$; denoised image $\hat{x} = y - \hat{n}$ (residual learning);
- Trained with synthetic AWGN ($\sigma \in [0, 55]$) and an $L_2$ loss.

The advantage of residual learning (残差学习) is that the noise residual is easier to fit than the clean image itself (smaller variance), gradients are more stable, and the network is freed from learning the global appearance of clean images from the ISP. DnCNN pushed PSNR on AWGN denoising to approximately **31.7 dB** ($\sigma=25$), surpassing the previous non-deep-learning best, BM3D.

**FFDNet** (Zhang et al., TIP 2018) extends DnCNN by introducing a **Noise Level Map (NLM, 噪声水平图)**: a tunable noise level $\sigma$ is fed as an extra input channel alongside the image:

$$\hat{x} = f_\theta([y, \mathbf{M}_\sigma])$$

where $\mathbf{M}_\sigma$ is a noise level map at the same spatial resolution as $y$ (can be uniform or spatially varying). This design allows a single network to handle arbitrary noise levels and supports spatially non-uniform noise. FFDNet also introduces a **sub-sampling strategy**: the $H\times W\times 1$ input is split into four $H/2 \times W/2$ channels for processing, reducing computation while expanding the effective receptive field.

---

### 1.3 The Transformer Era: NAFNet and Restormer

Attention mechanisms and Transformer architectures significantly raised the PSNR ceiling for single-frame denoising.

**Restormer** (Zamir et al., CVPR 2022) applies Transformers to high-resolution image restoration. Standard ViT self-attention in the spatial dimension has complexity $O(H^2W^2)$, which is infeasible for high-resolution images. Restormer's core innovation is **Transposed Attention (转置注意力)**: attention is computed in the channel dimension rather than the spatial dimension, reducing complexity to $O(C^2)$ ($C$ = number of channels) while maintaining a global receptive field.

Transposed attention computation:

$$\text{TAttention}(Q, K, V) = V \cdot \text{Softmax}(K^T Q / \tau) \tag{2}$$

where $Q, K, V \in \mathbb{R}^{C \times HW}$, so the attention weight matrix is $C \times C$ rather than $HW \times HW$.

Restormer achieves **40.02 dB** PSNR on SIDD real camera noise and **32.00 dB** on Gaussian denoising ($\sigma=25$), establishing a strong Transformer-era baseline.

**NAFNet** (Chen et al., ECCV 2022) (Nonlinear Activation Free Network) achieves remarkable efficiency through more aggressive simplification:

- All non-linear activation functions (ReLU, GELU, etc.) are removed, replaced by a **SimpleGate (简单门控)**: $\text{SG}(x) = x_1 \odot x_2$ (split feature map in half along channels, then element-wise multiply);
- Full SE-Block channel attention is replaced by **Simplified Channel Attention (SCA, 简单通道注意力)**: global average pooling + per-channel scaling only.

NAFNet achieves **40.30 dB** PSNR on SIDD with only ~17M parameters, roughly $3\times$ faster inference than Restormer. Its success demonstrates that **well-designed feature interaction is more important than complex non-linear activations** for image restoration tasks.

---

### 1.4 Diffusion Model Denoising: DiffusionMBIR and DnCNN-Score

Denoising based on **Denoising Diffusion Probabilistic Models (DDPM, 去噪扩散概率模型)** is an emerging direction. The core idea is to model the denoising process as a **reverse diffusion process**: starting from Gaussian noise $x_T \sim \mathcal{N}(0, I)$ and progressively recovering the clean image $x_0$ through a sequence of denoising steps $p_\theta(x_{t-1}|x_t)$.

For denoising with known noise level $\sigma$, the DDPM forward process directly corresponds to the noisy image: let $x_t = x_0 + \sqrt{t}\epsilon$, $\epsilon \sim \mathcal{N}(0,I)$; then time step $T$ corresponds to noise level $\sigma = \sqrt{T}$, and we only need to run the reverse process starting from step $T$.

**Advantages:** The perceptual quality (high-frequency texture restoration) of diffusion-model denoising is generally better than discriminative models trained with MSE/L1 losses, because the stochastic sampling in the diffusion process can generate multiple visually coherent clean images rather than outputting only the pixel-space mean (the MSE-optimal solution, which tends to be over-smooth).

**Disadvantages:** Diffusion models require tens to hundreds of reverse sampling steps, making inference 10–100× slower than discriminative models (e.g., NAFNet with a single forward pass), which is unfriendly to real-time ISP deployment. Accelerated sampling methods such as DDIM (Song et al., 2020) can compress the step count to 10–20, with a slight PSNR drop of approximately 0.3–0.5 dB.

---

### 1.5 Diffusion Denoising Models: Cold Diffusion and DiffIR

#### 1.5.1 Cold Diffusion (Bansal et al., NeurIPS 2023)

Standard DDPM's forward process is fixed Gaussian noise injection. Cold Diffusion proposes a more general view: **any (approximately) invertible image degradation** can serve as the forward process, and the corresponding reverse process is restoration. For image denoising, Cold Diffusion directly uses **additive Gaussian noise injection** as the forward process:

$$x_t = x_0 + \sqrt{t}\,\epsilon, \quad \epsilon \sim \mathcal{N}(0, I) \tag{3}$$

A noise prediction network $\epsilon_\theta(x_t, t)$ is trained for the reverse process, restoring the clean image via:

$$x_{t-1} = x_t - \left(\sqrt{t} - \sqrt{t-1}\right) \epsilon_\theta(x_t, t) \tag{4}$$

Cold Diffusion's contribution is to reveal that the denoising capability of diffusion models comes from the **iterative refinement** structure, not from the Gaussian forward process itself. Experiments show that using deblurring or super-resolution as the forward process can also train effective generative models. For real camera noise denoising, replacing the forward process with Poisson-Gaussian noise injection allows the model to better fit the true sensor noise distribution.

#### 1.5.2 DiffIR (Xia et al., ICCV 2023) Pipeline for Denoising

**DiffIR** (Diffusion-based Image Restoration) proposes a **two-stage diffusion restoration framework** designed for high-fidelity image restoration (including denoising). The core idea separates "coarse recovery" from "detail generation":

**Stage 1: Deterministic Coarse Restoration (Efficient Restoration Prior, ERP)**

A lightweight discriminative network $f_{\theta_1}$ (NAFNet-like architecture) quickly estimates a coarse restoration:

$$\tilde{x}_0 = f_{\theta_1}(y) \tag{5}$$

**Stage 2: Diffusion Refinement (Compact IR Prior, CIRP)**

Conditioned on the coarse result $\tilde{x}_0$, diffusion sampling runs in a **compact latent space** (rather than pixel space) to generate high-frequency texture details:

$$z_0 \sim p_\theta(z | \tilde{x}_0, y), \quad \hat{x} = D(z_0, \tilde{x}_0) \tag{6}$$

where $z_0$ is a low-dimensional latent vector encoding only the texture residual; decoder $D$ fuses it with the coarse result for the final output. This design compresses the diffusion step count from DDPM's 1000 to **4–8 steps** (because the latent space dimension is low, the sampling space is simpler), making inference approximately **20–50× faster** than pixel-space diffusion, while the perceptual quality (LPIPS) significantly surpasses single-stage discriminative methods.

**DiffIR performance on SIDD:** PSNR approximately 40.2 dB (comparable to NAFNet), but LPIPS improves by approximately **15%**, with noticeably richer subjective texture detail.

---

### 1.6 Self-Supervised Denoising: from Noise2Noise to Blind2Unblind

Unsupervised/self-supervised denoising methods break the limitation of needing clean reference images, training denoising networks using only noisy images. This is highly valuable in real camera scenarios where paired data is difficult to obtain.

#### 1.6.1 Noise2Noise (Lehtinen et al., ICML 2018)

The core insight of **Noise2Noise** is: if noise $n$ is zero-mean random noise, then **using another independent noisy image as the supervision target** is equivalent to using a clean image as the target:

$$\mathbb{E}_{n_1, n_2}[\|f_\theta(x+n_1) - (x+n_2)\|^2] = \mathbb{E}_{n_1}[\|f_\theta(x+n_1) - x\|^2] + \text{const} \tag{7}$$

That is: when $n_2$ has zero mean, the expectation of $(x+n_2)$ is $x$, so the $L_2$ loss with target $(x+n_2)$ is exactly equivalent (in expectation) to using $x$ as the target. Therefore, Noise2Noise trains using **two independent noisy captures of the same scene** as input-target pairs, with no clean images required.

**Application scenarios:** MRI medical images (multiple scans), astronomical images (multiple exposures), camera captures at the same position. In mobile photography, different frames from burst sequences can be used as Noise2Noise training pairs for self-supervised fine-tuning of denoising networks on-device.

**Limitation:** Requires two noisy observations of the same scene; not applicable in strictly single-image scenarios.

#### 1.6.2 Blind2Unblind (Wang et al., CVPR 2022)

**Blind2Unblind** solves the self-supervised denoising problem with only a single noisy image, using a **Re-Visible** mechanism:

1. **Global-Aware Inference (GAI, 全局感知推断):** Train the network with full-image (noisy) input for global receptive field;
2. **Re-Visible Blind Spot (重新可见盲点):** Artificially overlay additional known noise $\tilde{n}$ at random pixel positions on the noisy image $y$, producing $\tilde{y} = y + \tilde{n}$;
3. **Self-supervised target:** Train network $f_\theta$ to satisfy $f_\theta(\tilde{y}) \approx y$, i.e., remove the known extra noise $\tilde{n}$.

Since $\tilde{n}$ is known, this target is supervised (relative to $y$); and since $y$ itself contains the original noise, the network is forced to learn to remove various types of noise, not just the known $\tilde{n}$. Blind2Unblind achieves approximately **39.4 dB** PSNR on SIDD (trained only on noisy images), comparable to fully supervised methods (DnCNN approximately 39.2 dB) — an important milestone in self-supervised denoising.

#### 1.6.3 Noise2Fast (Huang et al., 2022)

**Noise2Fast** further simplifies self-supervised denoising: it generates training pairs via **self-subsampling** on a single image. Image $y$ is regularly subsampled into four sub-images $\{y^{(k)}\}_{k=1}^4$ (similar to Bayer packing). One sub-image serves as the input; the mean of the remaining sub-images serves as the supervision target. Training is completed entirely on a single image with no external data. Noise2Fast's denoising quality is slightly below Blind2Unblind, but it can **self-train online immediately after a new scene is captured**, making it suitable for extreme domain-shift scenarios (e.g., specialized cameras, non-standard sensors).

| Method | Needs clean images | Needs multiple noisy images | SIDD PSNR | Core idea |
|--------|-------------------|-----------------------------|-----------|-----------|
| DnCNN (supervised) | Yes | — | ~39.2 dB | Residual learning, supervised training |
| Noise2Noise | No | Yes (2 of same scene) | ~39.0 dB | Noisy images supervise each other |
| Blind2Unblind | No | No (single image) | ~39.4 dB | Re-Visible Blind Spot self-supervision |
| Noise2Fast | No | No (single image) | ~38.5 dB | Sub-sampling self-training |

---

### 1.7 Deep Modeling of Real Camera Noise: ELD and CycleISP

#### 1.7.1 ELD (Wei et al., CVPR 2020)

The ELD dataset focuses on **extreme low-light RAW domain denoising**, with two key contributions:

**Precise Poisson-Gaussian parameter calibration:** ELD provides a complete camera noise parameter calibration procedure, calibrating four parameters $(K, \sigma_r, \sigma_{TL}, \sigma_{row})$ at multiple ISO levels for several cameras (Sony / Nikon / Canon), where $\sigma_{TL}$ is the temperature-dependent leakage (thermal noise) and $\sigma_{row}$ is the row-noise standard deviation. Noise synthesis based on precisely calibrated parameters reduces the KL divergence between the real and synthetic noise distributions by approximately **60%** compared to the two-parameter model using only $(K, \sigma_r)$.

**Calibration-based data augmentation:** With only a small number of real RAW pairs available (approximately 10 pairs per camera), the precise noise model synthesizes large numbers of additional training pairs, significantly expanding training set size and addressing the scarcity of RAW paired data. ELD achieves approximately **1.8 dB** higher PSNR in extreme low-light scenarios (equivalent EV -4 to -6) compared to prior methods.

#### 1.7.2 CycleISP (Zamir et al., CVPR 2020)

**CycleISP** addresses the shortage of sRGB-domain denoising data by learning a bidirectional RAW↔sRGB ISP mapping to enable low-cost synthesis of realistic noisy data:

- **RAW → sRGB** (forward ISP network $G_{RS}$): simulates the ISP processing chain (demosaicing, AWB, CCM, Gamma);
- **sRGB → RAW** (inverse ISP network $G_{SR}$): maps sRGB images back to equivalent RAW;
- **Noise injection:** Poisson-Gaussian noise is injected in the RAW domain, then mapped to sRGB via $G_{RS}$, producing **realistically styled noisy sRGB images**.

CycleISP's key validation: training DnCNN with synthesized noisy sRGB data achieves **39.5 dB** PSNR on SIDD (vs 37.8 dB for training directly with AWGN), demonstrating that precise RAW-domain modeling can substantially close the domain gap in real camera noise.

---

### 1.9 RAW Domain vs. sRGB Domain Denoising

A critical design choice in ISP engineering is whether to apply DL denoising in the **RAW domain** or the **sRGB domain** (or YUV/Y luminance domain):

| Comparison dimension | RAW-domain denoising | sRGB-domain denoising |
|---|---|---|
| Noise model | Poisson-Gaussian (Eq. 1), known variance | Complex noise model after Gamma/non-linear processing |
| Color information | Bayer mosaic, weak spatial correlation | Full three-channel after demosaicing, strong spatial correlation |
| ISP integration | Replaces traditional RAW-domain NR block | Post-processing; does not affect upstream modules |
| Data acquisition | Requires RAW paired data; high acquisition cost | sRGB data abundant (SIDD/DND etc.) |
| Training difficulty | Known noise model; precise supervision possible | Complex real sRGB noise; domain shift in simulated data |

Mainstream smartphone cameras typically deploy **denoising modules in both domains**: RAW-domain BM3D/DL handles the main shot noise; a lightweight sRGB/YUV DL module suppresses residual color noise and FPN.

---

### 1.10 Engineering Deployment: INT8 Quantization and Mobile Frame-Rate Targets

#### 1.10.1 PSNR Loss Analysis for INT8 Quantization

Deep denoising networks on mobile NPUs typically run at **INT8 precision** (approximately 3–4× faster inference than FP32, 75% lower memory footprint). However, quantization introduces accuracy loss that varies considerably by network architecture:

| Network | FP32 PSNR (SIDD) | INT8 PSNR (SIDD) | Loss | Notes |
|---------|-----------------|-----------------|------|-------|
| DnCNN-17 | 39.23 dB | 38.89 dB | −0.34 dB | BN layers have poor quantization compatibility |
| FFDNet | 39.58 dB | 39.31 dB | −0.27 dB | Sub-sampling structure is quantization-friendly |
| NAFNet-32 | 40.30 dB | 40.08 dB | −0.22 dB | SimpleGate multiplication error needs calibration |
| Restormer | 40.02 dB | 39.52 dB | −0.50 dB | Attention softmax is sensitive to quantization |

Analysis of quantization sensitivity:
- **BN fusion (BN折叠):** BN parameters can be folded into convolution weights (BN Fusion), eliminating quantization error introduced by BN. With BN fusion, DnCNN's INT8 loss can be reduced from −0.34 dB to −0.15 dB;
- **Softmax attention:** The transposed attention softmax in Restormer is highly sensitive to quantization error; requires **per-channel INT8** or mixed FP16 precision;
- **Activation calibration:** For PTQ (post-training quantization), the calibration dataset should cover noisy images at various ISO levels to avoid excessive quantization error in low-light ISO 6400 scenes (dynamic range differs from low-ISO by more than 2 orders of magnitude).

#### 1.10.2 Mobile DL Denoising Frame-Rate Requirements and Implementation Paths

Frame-rate requirements for mobile camera DL denoising vary significantly by application scenario:

| Scenario | Input resolution | Frame-rate requirement | Latency budget | Typical solution |
|---|---|---|---|---|
| Real-time preview (video viewfinder) | 1080p | 30 fps | < 33 ms | Lightweight network (<5M params) + INT8 |
| Video recording (4K@30fps) | 4K | 30 fps | < 33 ms | Tile inference + pipeline parallelism |
| Photo capture (single frame) | 12–50 MP | < 200 ms | < 200 ms | Medium-complexity network (NAFNet-32) |
| Night-mode burst (long exposure) | Multi-frame fusion | N/A | < 1 s | Large model (can use diffusion) offline |

**Real-time preview optimization strategies:**
1. **Resolution downsampling:** Downsample the preview frame to 1/4 resolution (e.g., 1080p → 540p) before denoising, then bilinear upsample; 4× speed gain with PSNR loss of approximately 0.5–1.0 dB (subjectively acceptable);
2. **Tile streaming inference:** Divide the 4K frame into $M\times N$ tiles; process each tile in parallel with the ISP HW pipeline, then stitch; achieves zero additional latency;
3. **Frame skip strategy:** Scene changes between consecutive video frames are small; run DL denoising every 2–3 frames and propagate the previous denoised result to intermediate frames via motion compensation (optical flow); 2–3× speed gain with slight artifacts in motion scenes;
4. **Dynamic quantization:** Switch to lightweight INT8 DnCNN (3 layers) in daylight at low ISO; switch to high-accuracy NAFNet (INT8+FP16 mixed) in night mode at high ISO; adaptively balance image quality and power consumption.

**Typical mobile NPU performance reference (2024 flagship SoC):**
- Qualcomm Snapdragon 8 Gen 3 NPU: NAFNet-32 (INT8) at 1080p approximately **18 ms/frame** (~55 fps), 4K approximately **72 ms/frame** (tile processing needed for 30 fps);
- MediaTek Dimensity 9300 NPU: same network approximately **22 ms/frame** (1080p);
- Huawei Kirin 9000 DaVinci architecture: optimized for matrix multiply; Restormer INT8 approximately **45 ms/frame** (1080p).

---

## §2 Calibration

### 2.1 Mainstream Evaluation Datasets

| Dataset | Domain | Scale | Characteristics |
|---------|--------|-------|-----------------|
| SIDD (Abdelhamed et al., CVPR 2018) | sRGB | 30K pairs | Real noise from 5 smartphones |
| DND (Plotz & Roth, CVPR 2017) | sRGB | 50 pairs | DSLR real noise; no GT; blind testing |
| RENOIR (Anaya & Barbu, JVCIR 2018) | sRGB | 120 pairs | Real noise from handheld cameras |
| ELD (Wei et al., CVPR 2020) | RAW | 1K+ pairs | Extreme low-light RAW noise; multiple ISOs |
| SID (Chen et al., CVPR 2018) | RAW | 5,094 images | Short-to-long exposure pairs; extremely dark scenes |
| LSID (Maharjan et al., 2019) | RAW | 2K+ pairs | Long-exposure RAW real noise |

### 2.2 Noise Level Estimation and ISO Mapping

In actual deployment, denoising networks typically need a Noise Level Estimator (NLE, 噪声水平估计器) as a front-end module. Camera manufacturers typically provide **noise calibration curves**: shoot a standard gray card at different ISO levels and temperatures, fitting the variation of parameters $(\sigma_r^2, K)$ with ISO. Typical calibration results:

- Read noise $\sigma_r$: ISO 100 approximately 3–5 DN (Device Number), ISO 6400 approximately 15–25 DN;
- Gain $K$: approximately linear with ISO, $K \approx \text{ISO} / 100$.

Noise level values from calibration curves can be directly used as NLM input for networks like FFDNet, replacing runtime estimation and avoiding online variance estimation errors in uniform regions.

---

## §3 Engineering Practice

### 3.1 ISP Integration Strategies for Denoising Networks

**RAW-domain integration:** Replace or parallelize the DL denoising network with the traditional ISP Raw Domain NR (e.g., BM3D/NLM). The network input is 4-channel Bayer-packed RAW; the output is denoised RAW, which is then passed to downstream ISP modules (demosaicing, AWB, etc.).

**YUV-domain integration:** After the ISP converts RAW to YUV, the DL network processes only the Y (luminance) channel (highest resolution); U/V channel noise is typically lower and can be handled more lightly. This strategy reduces computation by approximately 2/3, but sacrifices color-channel correlation modeling from the RAW domain.

**Parallel inference architecture:** On SoC NPUs, DL denoising and the ISP HW pipeline run in parallel: ISP HW handles the normal flow; the NPU handles DL denoising; final fusion is done via a blending coefficient. This ensures the pipeline introduces no additional latency (approximately 6–12 ms at 4K@30fps).

### 3.2 Key Hyperparameter Tuning

Denoising strength control is the core of engineering tuning: **over-denoising** causes loss of texture detail (painting-like appearance); **under-denoising** leaves visible noise at high ISO. Typical tuning paths in the industry:

1. **Noise-level-scene adaptation:** Use AE exposure information (ISO, ET) to dynamically adjust denoising strength; increase denoising at high ISO in night scenes; near-bypass at low ISO;
2. **Content-aware denoising:** Introduce scene segmentation or saliency detection; reduce denoising strength in face and text regions to preserve detail;
3. **Frequency-domain joint optimization:** Low-frequency denoising strength is independent of high-frequency, avoiding overall luminance shift caused by low-frequency smoothing.

---

## §4 Failure Modes

### 4.1 Texture Over-Smoothing

Networks trained with $L_2$ (MSE) loss naturally tend to output pixel-wise means, causing over-smoothing of high-frequency textures (fabric textures, hair, grass). Objective metrics (PSNR) are good but subjective appearance is poor ("oil-painting effect"). Mitigation: add perceptual loss (VGG perceptual loss) or GAN adversarial loss, trading approximately 0.3–0.5 dB PSNR for significantly better texture preservation.

### 4.2 Color Shift

In sRGB-domain denoising, if noise is estimated too high, the denoising network may apply excessively strong tone suppression globally, reducing color saturation (color desaturation phenomenon). RAW-domain denoising is more resistant to this problem because color information is separately calibrated by subsequent AWB+CCM steps.

### 4.3 Residual FPN / Row Noise

Fixed Pattern Noise (FPN) and row/column noise have spatial correlation that exceeds the AWGN assumption used during training for most DL denoising networks. Networks typically handle FPN poorly: they may preserve it as signal, or introduce striped artifacts when attempting to remove it. A two-stage approach — column/row mean subtraction followed by DL denoising — is commonly used in the industry.

### 4.4 Unstable Denoising in Motion Regions

Single-frame denoising does not use temporal information, treating motion and static regions equally. In practice, motion regions often have **natural blur** (motion blur); aggressive denoising may incorrectly sharpen motion blur, leading to ringing artifacts in motion regions.

---

## §5 Evaluation

### 5.1 Standard Quantitative Metrics

| Metric | Description | Typical range (SIDD, sRGB) |
|--------|-------------|---------------------------|
| PSNR ↑ | Pixel-domain signal-to-noise ratio | 38–41 dB |
| SSIM ↑ | Structural similarity | 0.95–0.99 |
| LPIPS ↓ | VGG perceptual distance | 0.02–0.08 |

### 5.2 Divergence Between Perceptual Quality and PSNR

High PSNR denoising results are not necessarily good in perceptual quality. DnCNN (discriminative, high PSNR) vs. diffusion-model denoising (generative, lower PSNR but higher perceptual quality) is a canonical example. It is recommended to report together:
- **PSNR/SSIM** (fidelity metrics)
- **LPIPS** (perceptual similarity)
- **NIQE/BRISQUE** (no-reference naturalness)
- **Subjective A/B comparison** (final arbiter)

### 5.3 Out-of-Distribution Generalization Evaluation

The noise distribution in the training set and the real noise distribution of the test camera often have a **domain gap**: DnCNN trained on AWGN achieves approximately **1.5–2 dB** lower PSNR on real camera noise (SIDD) compared to the version trained on real noise. Evaluation should include cross-camera-model testing (e.g., trained on iPhone, tested on Samsung Galaxy) to quantify generalization ability.

---

## §6 Code

The companion code for this chapter is in *See §6 Code section for runnable examples.* and includes the following demonstrations:

1. **DnCNN baseline implementation:** Train a single-noise-level DnCNN on BSD68, visualize residual maps (sparsity comparison of noise residuals vs. clean image residuals), PSNR comparison with BM3D;
2. **FFDNet variable-noise-level denoising:** Demonstrate the effect of the Noise Level Map (NLM); compare uniform NLM vs. spatially varying NLM (simulating non-uniform noise in a scene with darker edges and brighter center);
3. **NAFNet fast denoising:** Fine-tune NAFNet on a small SIDD subset; compare PSNR difference with DnCNN on real camera noise (demonstrating domain shift effect);
4. **RAW-domain Poisson-Gaussian denoising:** Using paired RAW data from the ELD dataset, demonstrate RAW-domain denoising with noise-level input (ISO information); visualize automatic denoising strength adjustment at different ISOs.

---

## §8 Glossary

**DnCNN (Zhang et al., TIP 2017)**
Milestone architecture for deep learning image denoising: 17 layers of $3\times3$ Conv + BN + ReLU, outputting **noise residual** $\hat{n} = f_\theta(y)$, denoised image $\hat{x}=y-\hat{n}$. Residual learning bypasses the difficulty of fitting the global appearance of clean images, producing more stable gradients. PSNR approximately 31.7 dB on AWGN $\sigma=25$, surpassing the previous non-deep-learning best BM3D. Limitation: trained at a single noise level, does not support adjustable noise level; approximately 1.5 dB domain-shift loss on real camera noise.

**FFDNet (Zhang et al., TIP 2018)**
Adjustable noise-level extension of DnCNN: spatial noise level map $\mathbf{M}_\sigma$ (same resolution as input) is fed as an extra channel; a single network supports arbitrary noise levels (AWGN $\sigma \in [0,75]$) and spatially non-uniform noise. Also introduces a subsampling strategy ($H\times W \to H/2\times W/2\times 4$) to expand receptive field and reduce computation. FFDNet is the classic engineering baseline for signal-adaptive denoising strength design.

**NAFNet (Chen et al., ECCV 2022)**
Nonlinear Activation Free Network: removes all ReLU/GELU, replaces them with SimpleGate ($\text{SG}(x)=x_1\odot x_2$, halve channels then element-wise multiply) and Simplified Channel Attention (global mean pooling + scaling). PSNR 40.30 dB on SIDD, ~17M parameters, inference $3\times$ faster than Restormer. Reveals that appropriate feature interaction design is more important than complex non-linear activations for image restoration.

**Restormer (Zamir et al., CVPR 2022)**
Applies Transformer to high-resolution image restoration: core innovation is **Transposed Attention (转置注意力)**, computing attention in the $C$ dimension rather than $HW$ dimension; complexity $O(C^2)$ replaces $O(H^2W^2)$, achieving global receptive field while remaining computationally feasible at high resolution. SIDD PSNR 40.02 dB, Gaussian denoising $\sigma=25$ achieves 32.00 dB. The standard Transformer-era baseline for image restoration; its transposed attention design has been widely adopted in subsequent work.

**Poisson-Gaussian Noise Model (泊松-高斯噪声模型)**
Accurate physical model for real camera noise in the RAW domain: sum of shot noise (Poisson statistics of photon counting) and read noise (thermal and quantization noise from CMOS readout circuitry). Signal-dependent variance $\text{Var}[y|x]\approx x/K+\sigma_r^2$, where $K$ is the gain and $\sigma_r$ is the read-noise standard deviation. In highlights $x/K \gg \sigma_r^2$, shot noise dominates; in shadows $x/K \ll \sigma_r^2$, read noise dominates. Ignoring this model in RAW-domain denoising (assuming uniform AWGN) leads to over-denoising in shadows (variance underestimated) or under-denoising in highlights (variance overestimated); engineering implementations typically provide $(K,\sigma_r)$ parameters from an ISO-exposure calibration curve to the network.

**SIDD Dataset (Abdelhamed et al., CVPR 2018)**
Smartphone Image Denoising Dataset: 30,000+ pairs of real noisy/clean sRGB images captured with 5 smartphones under various ISO and scene conditions (clean reference obtained by long-duration averaging), the standard benchmark for evaluating real camera noise denoising. Compared to synthetic AWGN benchmarks, SIDD covers complex real-world noise components including FPN, striped noise, and JPEG compression noise, making it more representative of industrial deployment scenarios. Typical PSNR range: DnCNN ~39.2 dB, NAFNet ~40.3 dB, diffusion models ~40.5 dB (but 100× slower).

**Perceptual-PSNR Trade-off (感知损失与PSNR背离)**
Discriminative denoising networks trained with $L_2$/MSE loss tend to output pixel means; PSNR is high but high-frequency textures are over-smoothed ("oil-painting effect"). GAN/diffusion-based generative methods output high-perceptual-quality textures but PSNR is typically 0.3–1 dB lower. Information-theoretic explanation: maximizing PSNR is equivalent to minimizing MSE, whose optimal solution is the posterior mean $\mathbb{E}[x|y]$ (an average of many possible clean images, causing blurring); high perceptual quality requires sampling a single realization from the posterior distribution $p(x|y)$ (sharp textures but non-unique). In practice, a mixed loss ($\lambda_1 L_2 + \lambda_2 \mathcal{L}_\text{perc}$) balances fidelity and perceptual quality.

**Fixed Pattern Noise (FPN, 固定模式噪声)**
Spatially fixed systematic noise: caused by manufacturing non-uniformity in the CMOS pixel array (dark current, gain inconsistency), manifesting as fixed offsets at the same positions in every exposure; does not satisfy the spatially independent Gaussian assumption. FPN is corrected by **dark frame subtraction** or **column mean subtraction**, but residual FPN is still significant at high ISO or long exposure. DL denoising networks based on blind-spot networks or trained under AWGN assumptions have limited ability to handle FPN; engineering practice typically applies traditional FPN removal first, then DL denoising.

---

## References

[1] Zhang, K., Zuo, W., Chen, Y., Meng, D., & Zhang, L. (2017). Beyond a Gaussian denoiser: Residual learning of deep CNN for image denoising. IEEE Transactions on Image Processing, 26(7), 3142–3155. — DnCNN foundational paper; residual learning + BatchNorm framework; milestone in deep convolutional denoising.
[2] Zhang, K., Zuo, W., & Zhang, L. (2018). FFDNet: Toward a fast and flexible solution for CNN-based image blind denoising. IEEE Transactions on Image Processing, 27(9), 4608–4622. — FFDNet adjustable noise-level denoising; noise level map design; engineering-friendly parametric denoising baseline.
[3] Chen, L., Chu, X., Zhang, X., & Sun, J. (2022). Simple baselines for image restoration. ECCV, 17–33. — NAFNet original paper; nonlinear-activation-free design; 40.30 dB new SOTA on SIDD; efficient image restoration baseline.
[4] Zamir, S. W., Arora, A., Khan, S., Hayat, M., Khan, F. S., & Yang, M. H. (2022). Restormer: Efficient transformer for high-resolution image restoration. CVPR, 5728–5739. — Transposed attention Transformer; high-resolution image restoration SOTA; benchmark for Transformer-based ISP denoising.
[5] Abdelhamed, A., Lin, S., & Brown, M. S. (2018). A high-quality denoising dataset for smartphone cameras. CVPR, 1692–1700. — SIDD dataset paper; real-noise denoising standard benchmark from 5 smartphones.
[6] Foi, A., Trimeche, M., Katkovnik, V., & Egiazarian, K. (2008). Practical Poissonian-Gaussian noise modeling and fitting for single-image raw-data. IEEE TIP, 17(10), 1737–1754. — Classic paper on Poisson-Gaussian noise model calibration; theoretical foundation for RAW-domain noise modeling.
[7] Bansal, A., Borgnia, E., Chu, H. M., et al. (2023). Cold diffusion: Inverting arbitrary image transforms without noise. NeurIPS, 36. — Cold Diffusion original paper; generalizes diffusion forward process to arbitrary image degradations; theoretical foundation for diffusion-based general image restoration.
[8] Xia, B., Zhang, Y., Wang, S., et al. (2023). DiffIR: Efficient diffusion model for image restoration. ICCV, 13095–13105. — DiffIR two-stage diffusion restoration; compact latent-space diffusion compresses steps to 4–8; unified diffusion restoration baseline balancing PSNR fidelity and perceptual quality.
[9] Lehtinen, J., Munkberg, J., Hasselgren, J., et al. (2018). Noise2Noise: Learning image restoration without clean data. ICML, 2965–2974. — Noise2Noise foundational paper; proves theoretical equivalence of noisy-image mutual supervision for zero-mean noise; establishes self-supervised denoising paradigm.
[10] Wang, Z., Liu, J., Li, G., & Han, H. (2022). Blind2Unblind: Self-supervised image denoising with visible blind spots. CVPR, 2027–2036. — Blind2Unblind original paper; re-visible noise self-supervision; single-image self-supervised denoising achieving PSNR comparable to supervised methods (SIDD ~39.4 dB).
[11] Wei, K., Fu, Y., Yang, J., & Huang, H. (2020). A physics-based noise formation model for extreme low-light raw denoising. CVPR, 2758–2767. — ELD dataset and extreme low-light noise modeling; four-parameter Poisson-Gaussian calibration; standard benchmark for extreme low-light RAW denoising.
[12] Zamir, S. W., et al. (2020). CycleISP: Real image restoration via improved data synthesis. CVPR, 2696–2705. — CycleISP original paper; learns bidirectional RAW↔sRGB ISP mapping; low-cost synthesis of realistically styled noisy data; significantly reduces domain shift in real camera denoising.
