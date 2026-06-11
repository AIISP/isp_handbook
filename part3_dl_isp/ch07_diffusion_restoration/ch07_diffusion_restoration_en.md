# Part 3, Chapter 07: Diffusion Models for Image Restoration

> **Positioning:** This chapter provides a systematic treatment of diffusion probabilistic models (扩散概率模型, Diffusion Probabilistic Models) in the field of image restoration, covering the full technical chain from the foundational theory of DDPM to state-of-the-art methods such as StableSR and DiffIR, including principal architectures and industrial applications.
> **Prerequisites:** Part 2, Chapter 03 (Denoising), Part 3, Chapter 02 (End-to-End Image Restoration), Part 3, Chapter 03 (Super-Resolution), Part 3, Chapter 05 (LLIE)
> **Target readers:** Deep learning researchers, algorithm engineers

---

## §1 Theory

### 1.1 Physical Intuition Behind Diffusion Models

Diffusion models draw their inspiration from the diffusion process in non-equilibrium thermodynamics: noise is gradually injected into a clean image (the forward process), and a neural network is then trained to learn the inverse of this process (reverse denoising).

**Forward Process — Markov Noising Chain:**
$$q(x_t | x_{t-1}) = \mathcal{N}(x_t; \sqrt{1-\beta_t} x_{t-1}, \beta_t \mathbf{I})$$

Here $\beta_t \in (0,1)$ is the noise schedule (噪声调度, Noise Schedule) and $t \in \{1, \ldots, T\}$ (typically $T=1000$).

Using the reparameterization trick, one can sample $x_t$ at any timestep directly from $x_0$:
$$x_t = \sqrt{\bar{\alpha}_t} x_0 + \sqrt{1-\bar{\alpha}_t} \epsilon, \quad \epsilon \sim \mathcal{N}(0, \mathbf{I})$$

where $\bar{\alpha}_t = \prod_{s=1}^{t}(1-\beta_s)$. As $t \to T$, $\bar{\alpha}_T \approx 0$ and $x_T \approx \mathcal{N}(0, \mathbf{I})$.

**Reverse Process — Learning to Denoise:**
$$p_\theta(x_{t-1}|x_t) = \mathcal{N}(x_{t-1}; \mu_\theta(x_t, t), \Sigma_\theta(x_t, t))$$

The neural network $\epsilon_\theta(x_t, t)$ predicts the noise $\epsilon$, and the mean is computed as:
$$\mu_\theta(x_t, t) = \frac{1}{\sqrt{\alpha_t}}\left(x_t - \frac{\beta_t}{\sqrt{1-\bar{\alpha}_t}} \epsilon_\theta(x_t, t)\right)$$

**Training Objective (simplified form):**
$$\mathcal{L}_{simple} = \mathbb{E}_{t, x_0, \epsilon} \left[\|\epsilon - \epsilon_\theta(\sqrt{\bar{\alpha}_t}x_0 + \sqrt{1-\bar{\alpha}_t}\epsilon, t)\|^2\right]$$

### 1.2 Score-Based Model Perspective

Song & Ermon (2019) derived an equivalent framework from a different angle: learning the **score function (得分函数, Score Function)** $\nabla_x \log p(x)$ of the data distribution.

**Key equivalence:**
$$s_\theta(x_t, t) \approx \nabla_{x_t} \log q(x_t \mid x_0) = -\frac{\epsilon_\theta(x_t, t)}{\sqrt{1-\bar{\alpha}_t}}$$

Strictly, the right-hand side is the **conditional score** given $x_0$, not the marginal score $\nabla_{x_t}\log q(x_t)$. Via Tweedie's formula (MMSE denoising estimate) the conditional score approximates the marginal score, and both theoretical frameworks are unified in DDPM (Ho et al., 2020).

### 1.3 Conditional Diffusion for Image Restoration

In image restoration scenarios (super-resolution, denoising, deblurring, LLIE), the degraded image $y$ must be incorporated as a condition:

$$p_\theta(x_{t-1}|x_t, y) \propto p_\theta(x_{t-1}|x_t) \cdot p(y|x_{t-1})$$

**Two conditioning mechanisms:**

1. **Concatenation (串联条件):** $\epsilon_\theta([x_t, y_\uparrow], t)$ — the degraded image is directly concatenated with $x_t$ and fed into the network.
2. **Cross-Attention (交叉注意力):** Features extracted from the degraded image are injected into intermediate layers of the U-Net, providing finer-grained semantic guidance.

### 1.4 Accelerating Inference — From 1000 Steps to 10 Steps

Standard DDPM requires 1000 inference steps, each calling the neural network once, which is prohibitively expensive for high-resolution images.

**DDIM (Denoising Diffusion Implicit Models, Song et al., ICLR 2021):**

Replaces the stochastic Markov chain with a deterministic non-Markovian process:
$$x_{t-1} = \sqrt{\bar{\alpha}_{t-1}} \underbrace{\left(\frac{x_t - \sqrt{1-\bar{\alpha}_t}\epsilon_\theta}{\sqrt{\bar{\alpha}_t}}\right)}_{\text{predicted } x_0} + \sqrt{1-\bar{\alpha}_{t-1}} \epsilon_\theta$$

DDIM supports skip-step sampling (e.g., using only 10 timesteps from $t \in \{1000, 900, 800, \ldots, 100\}$), reducing the number of inference steps by 10–100× without retraining the network. Image quality degrades slightly but remains generally acceptable.

### 1.5 Flow Matching — Straight-Path Training Revolution

The diffusion trajectory in DDPM is fundamentally a **curved stochastic process**: the forward process uses an SDE to warp the data distribution gradually into Gaussian noise, and the reverse process must follow the same curved path back. ODE solvers must sample densely to integrate this trajectory accurately (the truncation-error problem in DDIM's 10-step variant in §1.4 traces back to this). Flow Matching takes a more fundamental approach: **if the path from noise to data is itself a straight line, integration requires only one or very few steps**.

**Mathematical Framework**

Flow Matching (Lipman et al., ICLR 2023) models the generation process as a Continuous Normalizing Flow (CNF), defining a velocity field $v_\theta(x, t)$ that drives an ODE:

$$\frac{dx}{dt} = v_\theta(x, t), \quad t \in [0, 1]$$

where $x_0 \sim \mathcal{N}(0, \mathbf{I})$ is noise and $x_1 \sim p_{data}$ is the real image. The training objective is **Conditional Flow Matching (CFM)**:

$$\mathcal{L}_{CFM} = \mathbb{E}_{t,\, x_0,\, x_1}\bigl[\|v_\theta(x_t,\, t) - (x_1 - x_0)\|^2\bigr]$$

where $x_t = (1-t)x_0 + t x_1$ is the linear interpolation between noise and data (Rectified Flow, Liu et al., ICLR 2023). **The velocity target $(x_1 - x_0)$ is constant along the linear path** — the network only needs to learn a fixed directional vector rather than a complex noise field that varies with time. Training signal variance is far smaller than DDPM's $\epsilon$-prediction.

**Comparison with Score Matching**

Score Matching (§1.2) trains the score function $s_\theta(x_t, t) \approx \nabla_{x_t}\log q(x_t)$ and samples via Langevin dynamics or SDE inversion. Flow Matching trains the velocity field $v_\theta(x_t, t)$ and samples via ODE integration. Both are simulation-free (no forward-process simulation needed during training), but Flow Matching directly regresses the tangent vector along the **optimal transport path**, while Score Matching learns the score of a stochastic diffusion process. The former yields straighter paths and fewer integration steps; the latter benefits from SDE stochasticity for more robust gradient estimation in data-sparse regions.

**Engineering Advantages and Representative Models**

| Dimension | DDPM/Score SDE | Flow Matching |
|-----------|---------------|---------------|
| Path type | Stochastic, curved (SDE trajectory) | Deterministic, straight (ODE trajectory) |
| Training target variance | High ($\epsilon$ varies with $t$) | Low (constant velocity field) |
| Quality at equal NFE | Baseline | Better (lower path curvature) |
| 1–4 step usability | Requires distillation (LCM/CM) | Native (Euler integration) |
| Industrial representatives | DDPM/LDM family | SD3, FLUX.1, InvSR |

**Stable Diffusion 3** (Esser et al., ICML 2024) marks the milestone of FM entering the mainstream: Rectified Flow replaces DDPM, combined with a Multi-Modal Diffusion Transformer (MMDiT) architecture, achieving DDPM-1000-step quality at 20–30 steps on text-to-image tasks with sharper generated details. **FLUX.1** (Black Forest Labs, 2024) extends this to 12B parameters using the same FM framework and is currently the de facto standard for text-to-image perceptual quality.

In image restoration, **PMRF** (Ohayon et al., ICLR 2025) proves theoretically that using the MMSE estimate of the degraded image ($\mathbb{E}[x_1|y]$) rather than pure noise as the Rectified Flow starting point simultaneously minimizes MSE and perceptual distortion, achieving the first rigorous approximation of the perception-distortion Pareto frontier on face restoration. **InvSR** (Yue et al., CVPR 2025) leverages the inversion capability of pretrained diffusion models to support arbitrary-step inference without retraining the backbone — usable at 1 step and progressively improving with more steps.

**Application to Image Restoration**

For image restoration, the core advantage of Flow Matching lies in **constructing a straight flow from degraded to clean**: set $x_0 = y$ (degraded image) and $x_1 = x_{clean}$ (clean image), making the linear interpolation path $x_t = (1-t)y + t x_{clean}$, and the velocity field target reduces to $v_\theta(x_t, t | y) = x_{clean} - y$ — predicting the residual direction from degraded to clean. At inference, starting from the degraded image, 1–4 Euler integration steps reach the restored result, **naturally circumventing the high-step-count problem inherent to "starting from pure Gaussian noise"**.

In ISP scenarios, Flow Matching has two particularly promising characteristics:
1. **Deterministic transport for RAW→sRGB**: The mapping from RAW to sRGB is one-to-many (different ISP tuning yields different results); traditional diffusion methods generate excessive diversity making the result uncontrollable. Flow Matching's straight-line flow can achieve more deterministic color transformation trajectories by constraining the velocity field direction.
2. **Fidelity-preserving transport for low-light enhancement**: The path from low-light to normal-exposure images should be perceptually "shape-preserving" (no change to scene semantics). Rectified Flow's optimal transport property (minimizing transport cost) naturally matches this requirement, with lower hallucination risk than the generative prior introduced by DDPM.

> **Relationship with §10.4:** This section focuses on the mathematical foundations and restoration principles of Flow Matching. §10.4 approaches from an engineering acceleration perspective and includes detailed Rectified Flow inference formulas, InstaFlow latency data, and empirical comparisons with Consistency Models — the two sections are complementary.

---

## §2 Main Methods

### 2.1 SR3 — Diffusion-Based Super-Resolution (Saharia et al., 2021)

**SR3 (Super-Resolution via Repeated Refinement)** was the first work to apply diffusion models to image super-resolution.

**Conditioning mechanism:** The low-resolution image is bicubically upsampled and concatenated with $x_t$ before being fed into the U-Net.

**Cascaded super-resolution:** A first model upscales from 16×16 → 128×128; a second model then upscales from 128×128 → 512×512. Each stage trains a separate diffusion model, and high magnification ratios are achieved by cascading them at inference time.

**Key contribution:** On the 8× face super-resolution task, SR3 achieves substantially better perceptual quality (LPIPS) than GAN-based methods such as RRDB/ESRGAN, though PSNR/SSIM scores are slightly lower — diffusion models tend to generate perceptually plausible details that do not align perfectly at the pixel level.

### 2.2 Palette — Unified Diffusion Image Restoration (Saharia et al., SIGGRAPH 2022)

**Palette** demonstrates that a single diffusion framework can simultaneously handle four restoration tasks: image colorization, image inpainting, JPEG artifact removal, and super-resolution.

**Unified architecture design:**
- Backbone: U-Net with Self-Attention (Transformer blocks inserted at 16×16 and 8×8 resolutions)
- Task conditioning: achieved solely through concatenation with the degraded image; no task-specific modules required
- Training: each task is trained independently with separate datasets

**Significance:** Validates the powerful generalizability of diffusion models — one codebase and one framework covers a wide range of image restoration tasks.

### 2.3 StableSR — Latent Diffusion Super-Resolution (Wang et al., IJCV 2024)

**Motivation:** SR3 and Palette operate in pixel space, making high-resolution (512×512+) inference extremely slow (several minutes per image).

**StableSR** builds upon Stable Diffusion (latent diffusion model, Rombach et al., CVPR 2022):

**Architecture:**
```
Low-resolution image y
    ↓
[Frozen VAE Encoder E]
    ↓
Latent representation z_y (8× spatial reduction)
    ↓
Concatenate z_t + z_y → [Conditioned U-Net Denoiser]
    ↓
Predicted z_0
    ↓
[Frozen VAE Decoder D]
    ↓
High-resolution output
```

**Key technique — Time-Aware Feature Transform (时控特征变换, TAWT):** Timestep information is injected into the decoder, making the decoding process aware of the current denoising stage and allowing it to dynamically balance fine detail generation against fidelity.

**Advantage:** Inference time at 512×512 resolution drops to approximately 30 seconds (versus 10+ minutes for pixel-space diffusion).

### 2.4 StableSR — Complete Technical Details

**Latent Space Mapping:** StableSR's core idea is moving image restoration from pixel space into the VAE-compressed latent space. The encoding and decoding are:

$$z = \mathcal{E}(x) \in \mathbb{R}^{\frac{H}{8} \times \frac{W}{8} \times 4}$$

$$\hat{x} = \mathcal{D}(\hat{z}) \in \mathbb{R}^{H \times W \times 3}$$

where $\mathcal{E}$ is the frozen VAE encoder and $\mathcal{D}$ is the frozen VAE decoder. Spatial resolution is compressed by $8\times$, and the channel count expands from 3 to 4 (latent channels), reducing computation by approximately $64\times$.

**Timestep Conditioning:** The diffusion denoiser receives a timestep embedding vector $\tau(t)$ at each step, injected into intermediate U-Net layers via Adaptive Layer Normalization (AdaLN):

$$\text{AdaLN}(h, t) = \alpha(t) \cdot \text{LayerNorm}(h) + \beta(t)$$

where $\alpha(t), \beta(t)$ are linearly projected from the timestep embedding $\tau(t)$. This allows the denoising network to adopt different activation distributions at different noise levels — large-$t$ steps focus on global structure, small-$t$ steps refine detail.

**SPADE Normalization (Spatially Adaptive Denormalization):** To address the color shift introduced by the VAE decoder (discussed in §4.3), StableSR introduces SPADE modulation in the decoder path:

$$\text{SPADE}(h, z_y) = \gamma(z_y) \odot \frac{h - \mu}{\sigma} + \beta(z_y)$$

where $\gamma(z_y), \beta(z_y)$ are predicted by a small convolutional network from the degraded image's latent representation $z_y$, modulating decoder features at each spatial position. This injects the color information of the low-resolution image back into the decoded result, effectively suppressing color temperature drift.

**Quality vs. Speed Trade-off:**

| Configuration | PSNR↑ | LPIPS↓ | Inference Time (512²) | Use Case |
|---------------|-------|--------|-----------------------|---------|
| 200-step DDIM | 26.8  | 0.156  | ~60s  | Academic benchmarking |
| 50-step DDIM  | 26.4  | 0.163  | ~15s  | Offline enhancement |
| 20-step DDIM  | 25.9  | 0.175  | ~6s   | Mobile background |
| Pixel-space SR3 (1000 steps) | 27.1 | 0.152 | ~600s | Reference only |

Reducing inference steps from 200 to 20 yields only 0.9 dB PSNR loss while cutting inference time by 10×. In practice, 20–50 steps is the reasonable engineering trade-off.

---

### 2.5 DiffBIR — Blind Image Restoration Two-Stage Pipeline (Lin et al., ECCV 2024)

**Motivation:** SR3/Palette perform poorly on blind restoration (unknown degradation type and severity) because the diffusion generative prior interferes with uncertain degradation conditions, producing hallucinated details or failing to eliminate degradation effectively.

**Two-Stage Design:**

```
Stage 1 (Degradation Removal):
  Degraded image y → CNN/Transformer restoration network (RealESRGAN or SwinIR) → coarse restoration y'
  Goal: remove noise/blur/JPEG artifacts, recover rough structure (PSNR-first)

Stage 2 (Detail Generation):
  Coarse restoration y' → conditioned LDM (ControlNet conditioning, Zhang & Agrawala, ICCV 2023) → fine output x̂
  Goal: supplement high-frequency details with diffusion prior without altering global structure (LPIPS-first)
```

**Design Rationale:** The Stage 1 CNN focuses exclusively on "degradation removal" with high PSNR as its objective. After degradation is removed, the Stage 2 LDM faces a relatively clean input, substantially reducing the probability of hallucination when the diffusion prior supplements high-frequency texture. The two stages have separate optimization objectives and do not interfere with each other.

**Key Module — IRControlNet:** In Stage 2 LDM, an IRControlNet variant injects Stage 1 coarse restoration features, providing spatially aligned condition signals and avoiding the information loss that would occur when conditioning directly on the degraded image. For face scenes, DiffBIR additionally introduces a **BFR Adapter (Blind Face Restoration Adapter)** to enhance face detail recovery — the BFR Adapter is a face-specific sub-module, not a general component of DiffBIR.

**Blind Degradation Handling:** DiffBIR outperforms StableSR across multiple blind test sets (RealWorld-SR, BSRGAN degradation, DPR degradation) with better NIQE, BRISQUE, and LPIPS, at the cost of PSNR approximately 1–2 dB below pure CNN methods such as RealESRGAN.

---

### 2.5b ResShift — Residual Shifting for Accelerated Diffusion Restoration (Yue et al., NeurIPS 2023)

**Motivation:** SR3/StableSR/DiffBIR require 100–1000 diffusion sampling steps; even with DDIM acceleration, 50 steps are needed, and the latency cannot satisfy mobile real-time requirements.

**Core Innovation — Residual Shifting:** Conventional diffusion starts from $x_T \sim \mathcal{N}(0,\mathbf{I})$ (pure Gaussian noise) and denoises backward. ResShift replaces the forward process starting point from Gaussian noise with the degraded image $y$ itself:

$$q(x_t|x_0, y) = \mathcal{N}\!\left(\sqrt{\bar\alpha_t}\,x_0 + (1-\sqrt{\bar\alpha_t})\,y,\; \kappa^2(1-\bar\alpha_t)\mathbf{I}\right)$$

where $\kappa$ is the variance scaling coefficient, and the degraded image $y$ acts as a bias term in the distribution mean. Because the forward process starts from the degraded image rather than white noise, **signal energy retention is higher, and the number of steps required for the reverse process decreases significantly** (15 steps achieves the quality level of StableSR at 200 steps).

**Performance:** On real-scene super-resolution benchmarks (RealSR, DRealSR), ResShift at 15 steps outperforms StableSR at 200 steps across PSNR/SSIM/LPIPS, achieving approximately 13× inference speedup. It is equally effective on SIDD denoising (Yue et al., NeurIPS 2023, arXiv:2307.12348).

**Engineering Significance:** ResShift's "start from the degraded image" concept directly influenced the design of subsequent one-step/few-step diffusion restoration methods (OSEDiff, InvSR). It is the most important efficiency breakthrough in diffusion restoration for 2023.

---

### 2.5c SeeSR — Semantics-Aware Real-World Super-Resolution (Wu et al., CVPR 2024)

**Motivation:** DiffBIR/StableSR rely on Stable Diffusion's visual prior, but the CLIP semantic space in SD is too abstract for restoration tasks — the model cannot distinguish "a blurry dog" from "an intentionally soft-focus background," leading to high hallucination rates in semantically complex scenes (text, faces, plant textures).

**Core Innovation:** SeeSR introduces **Semantic Tag Guidance**, injecting dense semantic tags into the diffusion denoising process so the model can sense the content category of each region, thus avoiding cross-semantic hallucinations.

**Architecture:** Two stages:
1. **Semantic tag extraction:** A lightweight RAM (Recognize Anything Model) extracts a dense tag list for the image (e.g., "sky, building, tree, text")
2. **Tag-conditioned diffusion:** Tag embeddings are injected into every layer of the ControlNet, providing semantic constraints at multi-scale feature levels

$$x_{t-1} = \mu_\theta(x_t, c_{\text{LQ}}, c_{\text{tag}}) + \sigma_t \epsilon, \quad \epsilon \sim \mathcal{N}(0, \mathbf{I})$$

where $c_{\text{LQ}}$ is the degraded image condition and $c_{\text{tag}}$ is the semantic tag embedding.

**Performance (CVPR 2024 official report):**

| Method | RealSR LPIPS↓ | RealSR NIQE↓ | Text Sharpness | Face Naturalness |
|--------|--------------|-------------|----------------|-----------------|
| Real-ESRGAN | 0.267 | 4.12 | Medium | Medium |
| StableSR | 0.242 | 3.89 | Low (hallucination) | Low (hallucination) |
| DiffBIR | 0.228 | 3.71 | Medium | High |
| **SeeSR** | **0.198** | **3.45** | **High** | **High** |

**Engineering Significance:** SeeSR is the first work to bring semantic awareness into the mainstream diffusion ISR framework, addressing the core pain point of "high perceptual quality but uncontrollable semantics" in diffusion models. For mobile deployment, RAM tag extraction requires approximately 50 ms (Snapdragon 8 Gen 3 NPU), an acceptable overhead.

---

### 2.6 DiffIR — Efficient Diffusion for Image Restoration (Xia et al., ICCV 2023)

**Problem:** StableSR still relies on the large Stable Diffusion foundation model (~860M parameters), making industrial deployment difficult.

**DiffIR's lightweight strategy:**
1. The diffusion process runs only in a **compact representation space** (Compact IR Prior, CIRP) rather than in pixel or VAE latent space.
2. The CIRP encodes only high-level semantic information (e.g., texture style, blur type) and has very low dimensionality (typically a 512-dimensional vector).
3. Restoration parameters are predicted from the CIRP to drive a lightweight Transformer restoration network via Cross-Attention.

**Architecture:**
```
Degraded image y
    ↓
[CIRP Encoder φ] → compact prior vector c ∈ ℝ^512
    ↓ (diffusion denoising, T steps on c only)
Refined prior ĉ
    ↓ (Cross-Attention conditioning)
[Lightweight Transformer restoration network]
    ↓
High-quality output x̂
```

**Parameter count comparison:**

| Method | Parameters | Inference Time (512²) | Platform |
|--------|-----------|----------------------|---------|
| StableSR | ~860M | ~30s | A100 |
| Palette | ~625M | ~10min | A100 |
| DiffIR-S | ~17M | ~1.5s | A100 |
| DiffIR-B | ~33M | ~2.8s | A100 |
| RRDB (non-diffusion baseline) | ~16M | ~0.2s | A100 |

**Performance:** DiffIR-S exceeds Restormer/NAFNet on denoising, deraining, and deblurring while its inference efficiency approaches pure CNN methods — making it currently the most industrially deployable diffusion restoration solution.

### 2.7 IR-SDE — Stochastic Differential Equation Framework (Luo et al., ICML 2023)

**Innovation:** Image restoration is uniformly modeled as a **stochastic differential equation (SDE)** trajectory from the degraded image to the clean image:

$$dx = f(x,t)dt + g(t)dW$$

The forward process starts from the degraded image $y$ (rather than Gaussian noise as in DDPM) and terminates at a distribution close to the ground truth $x_0$. This shortens the sampling trajectory and reduces the required number of inference steps.

**Advantage:** Converges faster than standard conditional DDPM (achieving comparable quality in fewer than 100 steps), making it suitable for latency-sensitive industrial scenarios.

---

### 2.8 ControlNet-Tile for Super-Resolution

**Background:** Directly performing diffusion inference on high-resolution images (2K/4K) demands prohibitive VRAM. ControlNet-Tile is a tile-based super-resolution strategy developed by the AUTOMATIC1111/kohya-ss community that uses ControlNet constraints to ensure each tile's generated content matches the original image, preventing content hallucination.

**Core Idea:** The high-resolution image is divided into tiles (Tile), each fed independently into the diffusion model. The ControlNet condition image is set to the low-resolution version of that tile, enforcing semantic consistency of the generated content:

$$\hat{x}_{tile_i} = \text{LDM}(z_{t}, c_{tile_i}), \quad c_{tile_i} = \text{ControlNet}(\text{downsample}(tile_i))$$

**Three-Layer Mechanism for Preventing Content Hallucination:**
1. **ControlNet condition constraint:** Each denoising step is anchored by the original tile features; the diffusion process cannot deviate from the source content.
2. **Tile overlap blending:** Adjacent tiles use $k$-pixel overlap regions, with the overlap taken as a weighted average of the two tiles' outputs (Gaussian weights), eliminating boundary seams.
3. **Low-frequency consistency constraint:** The low-frequency components (DCT low-frequency coefficients) of each tile are aligned with the original image, preventing color drift.

**Tile Overlap Blending Weights:**

$$\hat{x}(i,j) = \frac{\sum_{k} w_k(i,j) \cdot \hat{x}^{(k)}(i,j)}{\sum_{k} w_k(i,j)}$$

where $w_k(i,j)$ is the Gaussian weight of the $k$-th tile at position $(i,j)$: high near the tile center, low near the edges.

**Practical Parameter Recommendations:**

| Parameter | Recommended Value | Notes |
|-----------|------------------|-------|
| Tile size | 512×512 | Matches SD training resolution |
| Overlap pixels | 64–128 px | Larger overlap reduces seams but increases computation |
| ControlNet weight | 0.5–0.8 | Higher = more faithful to original; lower = richer details |
| Inference steps | 20–30 | DDIM 20 steps is sufficient |

**Limitation:** Each tile is processed independently without awareness of global illumination, causing brightness inconsistencies across regions in complex lighting scenes (backlit scenes, high dynamic range). Post-processing global tone alignment is required.

---

### 2.9 Inference Efficiency: From 1000 Steps to 1 Step

**DDIM vs. Full-Step Quality Comparison:**

| Sampling Scheme | Steps | PSNR (SR task, DIV2K 4×) | Inference Time (512², A100) | Notes |
|----------------|-------|--------------------------|----------------------------|-------|
| DDPM | 1000 | 29.2 dB | ~200s | Academic reference ceiling |
| DDIM | 100 | 28.9 dB (−0.3 dB) | ~20s | Offline batch processing |
| DDIM | 20 | 28.4 dB (−0.8 dB) | ~4s | Mobile background (recommended) |
| DDIM | 10 | 27.8 dB (−1.4 dB) | ~2s | Real-time preview |
| DDIM | 5 | 27.0 dB (−2.2 dB) | ~1s | Quick draft |
| LCM | 4 | — (perceptual-first) | ~0.8s | Few-step efficient |
| SDXL Turbo | 1–4 | — (perceptual-first) | ~0.2–0.8s | Extreme speed |

Note: LCM/SDXL Turbo papers report FID/perceptual quality metrics rather than SR task PSNR; PSNR is not an appropriate primary metric for perceptual-quality-first scenarios.

**LCM (Latent Consistency Model, Luo et al., 2023):** Uses Consistency Distillation to compress a multi-step diffusion model into a few-step model:

$$f_\theta(x_t, t) \approx x_0 \quad \forall t \in [0, T]$$

The training objective is for the network to directly predict the clean image $x_0$ from any timestep $t$, rather than predicting noise. After distillation, 4 steps achieve ~80% of 20-step DDIM quality; 1 step produces usable results.

**SDXL Turbo (ADD, Adversarial Diffusion Distillation, Sauer et al., 2023):** Combines adversarial training with score distillation, enabling high-quality image generation in 1 step. Suitable for real-time preview scenarios, though fidelity optimization for image restoration tasks is limited (trained on generative tasks).

**Mobile / NPU Deployment Memory Budget:**

| Model | Precision | Parameters | VRAM/Memory (512²) | Target Platform |
|-------|-----------|-----------|---------------------|----------------|
| DiffIR-S (FP32) | FP32 | 17M | ~680 MB | Edge server |
| DiffIR-S (FP16) | FP16 | 17M | ~340 MB | Mid-high-end phone NPU |
| StableSR (INT8 quantized) | INT8 | 860M | ~860 MB | High-end phone |
| LCM-ControlNet (INT8) | INT8 | ~860M | ~1.2 GB | Flagship phone (>12 GB RAM) |
| Pixel-space diffusion (64ch U-Net) | FP16 | 30M | ~2 GB (1024²) | Not recommended for mobile |

**Quantization Strategy:** Diffusion model U-Nets are sensitive to INT8 weight quantization (Attention QK products overflow easily). FP8 or W4A8 (4-bit weights, 8-bit activations) is recommended, combined with a calibration set (~100 representative images) for PTQ (post-training quantization), achieving < 0.3 dB quality loss while reducing memory by 3–4×.

> **Engineering Recommendations (diffusion restoration method selection):**
> - **Mobile background async enhancement (15–60s acceptable):** DiffIR-S + DDIM 20 steps, FP16, estimated 15–30s/frame on Snapdragon 8 Gen 3 NPU. 17M parameters, 340MB memory — the most cost-effective mobile diffusion solution.
> - **Edge server offline batch processing (no time limit):** StableSR 200 steps or DiffBIR; best perceptual quality. StableSR for pure super-resolution, DiffBIR for blind degradation (unknown noise/blur type).
> - **Perceptual-quality-first for faces/portraits:** DiffBIR (two-stage: Stage 1 CNN degradation removal + Stage 2 diffusion detail synthesis); best LPIPS. Not recommended for scientific/medical imaging (hallucination textures are errors, not aesthetics).
> - **Fastest perceived result (background 3–8s):** OSEDiff one-step + INT8 — currently the closest to phone-practical diffusion path, but PSNR optimization is weak; suitable only for perceptual enhancement scenarios.
> - **Real-time ISP (< 100ms):** No current diffusion solution qualifies. Use discriminative methods (NAFNet/Restormer).

---

### 2.10 Noise Schedule Calibration

**Background:** Standard DDPM/LDM noise schedules (cosine or linear) are designed for natural images from ImageNet/LAION — optimal for "generating images from pure Gaussian noise" but suboptimal for specific degradation types in image restoration (real-world blur, sensor noise, JPEG compression).

**Calibration Principle:** For a specific degradation type, the noise schedule should be chosen so that the cumulative noise level $\bar{\alpha}_t$ at intermediate timesteps ($t \approx T/2$) matches the SNR of the degradation signal, allocating the most computation to the most relevant denoising stage.

**Degradation SNR Estimation:** For a degraded image $y$ and corresponding clean image $x_0$, estimate the noise standard deviation introduced by degradation:

$$\text{SNR}_{degradation} = 10\log_{10}\frac{\mathbb{E}[x_0^2]}{\mathbb{E}[(y-x_0)^2]}$$

If $\text{SNR}_{degradation} = k$ dB, select $t^* = \arg\min_t |\text{SNR}(t) - k|$ as the calibration starting point, ensuring the model works primarily in the low-noise stage $t \leq t^*$.

**Schedule Recommendations for Common Degradations:**

| Degradation Type | Typical SNR Range | Recommended Schedule | Optimal Starting Step $t^*$ |
|-----------------|------------------|---------------------|---------------------------|
| Light Gaussian noise (σ=10) | 30–35 dB | Cosine | t* = 200–300 |
| Heavy real noise (ISO 3200) | 20–25 dB | Sigmoid | t* = 400–500 |
| Motion blur (kernel length 15px) | 15–20 dB | Linear | t* = 500–600 |
| JPEG compression (QF=30) | 25–30 dB | Cosine | t* = 300–400 |
| Extreme low-light (4× underexposed) | 10–15 dB | Sigmoid | t* = 600–700 |

**Calibration Implementation Steps:**
1. Compute the degradation SNR distribution on a calibration dataset (containing degraded/clean pairs).
2. Select the schedule type based on SNR (cosine for high SNR, Sigmoid for low SNR).
3. Set inference starting step $t^* < T$; run only reverse denoising from $t^*$ to 0, skipping the high-noise stage ($t > t^*$) to reduce wasted computation.
4. Test PSNR/LPIPS on the validation set and fine-tune $t^*$ to find the optimum.

**Engineering Significance:** For real sensor degradation (non-synthetic), schedule calibration can improve PSNR by 0.3–0.8 dB without retraining the model, while reducing inference steps by approximately 30% (from $T$ to $t^*$).

---

### 2.11 SUPIR — Billion-Parameter Blind Restoration at Scale (Ye et al., CVPR 2024)

**Motivation:** Existing diffusion restoration methods (DiffBIR/SeeSR) are capped at ~860M parameters (Stable Diffusion v2), constrained by a single text-image alignment prior. Their ability to handle complex real degradations (simultaneous noise, blur, JPEG compression, low-light) has a ceiling. SUPIR asks: if the restoration model scale is pushed to ~1B parameters with multimodal understanding, how much further can perceptual quality improve?

**SUPIR (Scaling Up to Excellence, Ye et al., CVPR 2024)** pushes diffusion image restoration to the current scale limit via three key innovations:

**1. Large-Scale Data Engine (~20M image-text pairs):** SUPIR collects approximately 20 million high-quality images and uses LLaVA (a multimodal large language model) to automatically generate descriptive text annotations, building a restoration-specific dataset. Compared to the millions-scale datasets of DiffBIR/SeeSR, data scale increases by an order of magnitude, enabling the model to learn richer real-world texture priors.

**2. Negative Quality Prompts (NQP):** Descriptive negative text characterizing degradation (e.g., "blurry, noisy, low quality, artifacts") is introduced as a contrastive condition during training. At inference, Classifier-Free Guidance steers generation away from the degradation space:

$$x_{t-1} = \mu_\theta(x_t, c_{pos}) + \lambda\bigl[\mu_\theta(x_t, c_{pos}) - \mu_\theta(x_t, c_{neg})\bigr]$$

where $c_{pos}$ is the high-quality description text, $c_{neg}$ is the negative quality prompt, and $\lambda$ is the guidance scale (typically 7–10). This effectively suppresses residual degradation and low-frequency blur during the diffusion sampling process.

**3. CKPT-Merge Capability Injection:** SDXL's original weights have strong natural image generation priors; direct fine-tuning would destroy the existing semantic alignment. SUPIR uses **Model Merging** to combine restoration-specific fine-tuned weights (trained on degraded-clean image pairs) with the original SDXL weights:

$$\theta_{SUPIR} = \alpha \cdot \theta_{finetune} + (1-\alpha) \cdot \theta_{SDXL}$$

where $\alpha \approx 0.3$–$0.5$ (determined experimentally), injecting restoration capability while preserving SDXL's generative prior and avoiding catastrophic forgetting.

**Performance (SUPIR original paper, Real-ISP Benchmark):**

| Method | MUSIQ↑ (perceptual quality) | NIQE↓ | LPIPS↓ | Parameters |
|--------|-----------------------------|-------|--------|-----------|
| Real-ESRGAN | ~45 | 5.2 | 0.25 | ~17M |
| StableSR | ~52 | 4.5 | 0.21 | ~860M |
| DiffBIR | ~58 | 4.1 | 0.19 | ~860M |
| **SUPIR** | **>65** | **3.6** | **0.16** | **~2B** (SDXL backbone) |

MUSIQ > 65 represents a ~44% improvement over Real-ESRGAN in perceptual quality — the highest among blind restoration methods at CVPR 2024.

**Engineering Limitations (why mobile deployment is infeasible):**

- **VRAM requirement:** The SDXL backbone is approximately 6.5B parameters (VAE + CLIP + U-Net); SUPIR full-precision inference requires approximately **18–24 GB VRAM**. An A100 80GB can run it; a consumer RTX 4090 (24GB) requires FP16 + gradient checkpointing.
- **Inference time:** Single image at 512×512 takes approximately **5–30 seconds** (A100, 50-step DDIM); 1024×1024 takes 60–90 seconds. Not feasible on a Snapdragon 8 Gen 3 phone.
- **Applicable scenarios:** Offline batch photo restoration (cloud servers), album "super enhancement" features (background queue processing), commercial editing tools (analogous to Topaz AI).

**Technology Lineage:**

```
Scale:   Small ────────────────────────────────────→ Large
         DiffIR-S (17M) → StableSR/DiffBIR (860M) → SUPIR (~2B)
Speed:   Fast ←───────────────────────────────────── Slow
Quality: Medium         High                         Excellent
             Suitable for mobile        Suitable for server
```

SUPIR represents the "maximize quality ceiling first" technical route and is the direct predecessor of FLUX-based restoration (2024–2025). FLUX.1 uses the Flow Matching framework (§10.4) at similar model scale but with straighter paths, further surpassing SUPIR in perceptual quality.

> **Code:** https://github.com/Fanghua-Yu/SUPIR (MIT License)

---

## §3 Integration with ISP

### 3.1 RAW-Domain Diffusion Restoration

**GDP (Generative Diffusion Prior, Fei et al., 2023):** Leverages a pretrained diffusion model as an image prior, eliminating the need to retrain for each specific degradation type:

$$\hat{x}_0 = \arg\min_{x_0} \|y - \mathcal{A}(x_0)\|^2 \quad \text{s.t.} \quad x_0 \sim p_{data}$$

where $\mathcal{A}$ is the degradation operator (downsampling, blur, noise, etc.). By imposing data-consistency constraints during diffusion reverse sampling, blind restoration becomes possible for arbitrary degradation types.

### 3.2 Hybrid Architecture: Diffusion Models + Traditional ISP

**Practical approach (industry trend as of 2024):**

```
RAW → Traditional ISP (BLC/Demosaic/AWB/CCM) → sRGB (fast path)
                                                      ↓
                                            [Diffusion Enhancement Module]
                                          (activated only when needed: night / high ISO)
                                                      ↓
                                               Final Output
```

- Daytime normal scenes: diffusion module is bypassed; traditional ISP is used (< 10 ms)
- Low-light / high-noise scenes: diffusion enhancement is activated (~500 ms, background processing, perceived latency is low)

---

## §4 Artifacts

### 4.1 Over-Smoothing vs. Hallucinated Detail

**Phenomenon:** Diffusion models exhibit a fundamental trade-off between fidelity (PSNR) and perceptual quality (LPIPS). Few-step inference (5–10 DDIM steps) tends to produce over-smoothed textures (worn-down skin and fabric details), while many-step inference (100+ steps) may generate visually plausible but non-existent details — **hallucination artifacts** — manifesting as spurious brick-wall textures or false text edges in super-resolution.

**Root Cause:** The reverse denoising process in diffusion models is a stochastic sampling process. The condition constraint (degraded image $y$) is introduced only through attention or concatenation, and its constraint strength weakens as timestep $t$ approaches 0. In the final "detail filling" stage ($t \to 0$), the model relies primarily on the natural image prior rather than the input condition, causing generated content to deviate from the actual scene.

**Diagnostic Method:** Compute both PSNR (fidelity) and LPIPS/FID (perceptual quality) on a test set and plot the perception-distortion curve (P-D curve). If PSNR decreases as steps increase while LPIPS improves, this is quantitative evidence of hallucination artifacts. For suspicious regions, use difference maps ($|output - GT|$) with amplification for visualization.

**Mitigation Strategies:**
- Introduce a distortion penalty: add $\lambda_{distortion} \cdot \nabla_x \|y - \mathcal{A}(x)\|^2$ to the score function; adjust $\lambda$ to balance perceptual quality and fidelity.
- Use low-temperature sampling (Temperature Scaling): reduce randomness in the final 10% of denoising steps to decrease stochastic hallucination.
- Use DiffIR-style lightweight diffusion: run diffusion only in compact latent space, reducing the spatial dimensions where hallucination can occur.

### 4.2 Accumulated Error in Multi-Step DDPM Inference

**Phenomenon:** In few-step (< 20 steps) DDIM sampling, the reconstructed image exhibits slight global color tone shift (overall warming or cooling), blurred high-frequency details, and faint staircase artifacts at edges.

**Root Cause:** DDIM's deterministic non-Markovian sampling, when using large skips (e.g., from $t=1000$ directly to $t=900$), makes the prediction $\hat{x}_0$ at each step a coarse approximation of the clean image. Errors accumulate linearly across subsequent steps. Mathematically, DDIM's skip approximation is $\hat{x}_0^{(t)} = (x_t - \sqrt{1-\bar{\alpha}_t}\epsilon_\theta) / \sqrt{\bar{\alpha}_t}$. At large $t$, $\bar{\alpha}_t$ approaches zero, so small noise prediction errors are amplified by $1/\sqrt{\bar{\alpha}_t}$.

**Diagnostic Method:** Compare outputs at 1000 steps vs. 20 steps vs. 5 steps, and plot PSNR vs. step count on a standard test set (e.g., Set5 super-resolution). Identify the "knee point" where quality loss exceeds 0.5 dB.

**Mitigation Strategies:**
- Use DPM-Solver or DPM-Solver++ high-order ODE solvers: at the same step count, approximately 0.3–0.8 dB better PSNR than DDIM.
- Use an adequate step count for inference (20 steps for mobile background processing; 5–10 steps for online preview).
- Use EDM (Elucidated Diffusion Models, Karras et al.) higher-order Runge-Kutta samplers to approach near-convergence quality within 10 steps.

### 4.3 Color Drift in Conditional Diffusion

**Phenomenon:** In latent-diffusion-based super-resolution methods such as StableSR, the output image's overall color tone deviates from the input low-resolution image, particularly in scenes with complex lighting (sunset, fluorescent light), where color temperature shifts can exceed 500K.

**Root Cause:** VAE encoding/decoding introduces non-linear compression in color space. When decoding latent variables, if the denoised $z_0$ distribution deviates from the VAE training prior distribution (distribution shift), the decoded result shows systematic color tone drift. The TAWT (Time-Aware Feature Transform) module's over-regulation of color in the late denoising stage is also a contributing factor.

**Diagnostic Method:** Compute the global mean color difference $\Delta E_{00}$ in the sRGB gamut between the (upsampled) input and the output; values above 2 units indicate significant color drift. Compute per-channel mean values to localize the shifted channel (R/G/B).

**Mitigation Strategies:**
- Post-processing color correction: perform tone alignment (color tone alignment) after diffusion output, forcing the output image's low-frequency color to align with the bicubic upsampling reference.
- Add color consistency loss: during fine-tuning, add Lab color space constraints to the VAE decoder.
- Use IR-SDE instead of conditional DDPM: the SDE trajectory starting from the degraded image naturally reduces color deviation from the input condition.

### 4.4 Common Artifact Reference Table

| Artifact Type | Trigger Conditions | Typical Appearance | Mitigation |
|--------------|-------------------|-------------------|------------|
| Hallucination texture | High-step inference, weak condition | Non-existent brick textures, false text edges | Add distortion penalty, reduce end-stage sampling temperature |
| Over-smoothing | Few-step DDIM (< 10 steps) | Worn skin/fabric detail; high PSNR but poor LPIPS | DPM-Solver high-order sampling, increase steps |
| Color drift | StableSR latent diffusion, VAE distribution shift | Whole-image color temperature shift > 500K | Post-processing color alignment, use IR-SDE instead |
| Accumulated step error | Large-stride DDIM skips (> 100 steps/step) | Global mild blur, edge staircase artifacts | DPM-Solver++, EDM Runge-Kutta sampler |
| Boundary ringing | VAE decode after latent upsampling | Fine ringing lines at high-contrast edges | Guided filter post-processing, larger VAE decoder receptive field |

---

## §5 Tuning

### 5.1 Choosing a Noise Schedule

| Schedule Type | Formula | Characteristics |
|---------------|---------|-----------------|
| Linear (DDPM) | $\beta_t = \beta_1 + (t-1)\frac{\beta_T - \beta_1}{T-1}$ | Simple, but noise changes too rapidly in early training |
| Cosine (Improved DDPM) | $\bar{\alpha}_t = \cos^2\left(\frac{t/T + 0.008}{1.008} \cdot \frac{\pi}{2}\right)$ | Smoother; does not over-destroy the signal at the tail end |
| Sigmoid | Gradual at both ends, rapid in the middle | Better detail preservation; recommended for image restoration |

### 5.2 Inference Steps vs. Quality Trade-off

| Steps | PSNR (typical, SR task) | Inference Time (512², A100) | Suitable Use Case |
|-------|------------------------|----------------------------|-------------------|
| 1000 | Highest | ~200s | Academic research |
| 100 | −0.3 dB | ~20s | Offline batch processing |
| 20 | −0.8 dB | ~4s | Mobile background processing |
| 5 | −1.5 dB | ~1s | Real-time preview |

**Recommendation:** For mobile night mode, use 10–20 step DDIM sampling executed in the background (completing approximately 3–5 seconds after the user takes a photo).

### 5.3 Perceptual Quality vs. Fidelity Trade-off

Diffusion models naturally lean toward high perceptual quality (low LPIPS) but yield lower pixel-level fidelity (PSNR) compared to discriminative methods.

**Adjustment method:** Introduce a distortion penalty term $\lambda_{distortion} \cdot \|x_0 - \hat{x}_0\|^2$ added to the score function. At inference time, $\lambda$ interpolates between perceptual quality and PSNR (based on the perception-distortion trade-off theorem established by Blau & Michaeli, 2018).

---

## §6 Evaluation

### 6.1 Standard Metrics for Restoration Tasks

| Task | Primary Metrics | Secondary Metrics |
|------|----------------|-------------------|
| Super-Resolution | PSNR/SSIM (DIV2K) | LPIPS, NIQE |
| Image Denoising | PSNR (SIDD, DND) | SSIM |
| JPEG Artifact Removal | PSNR/SSIM (LIVE1) | BRISQUE |
| LLIE | PSNR/SSIM (LOL) | LPIPS, NIQE |

### 6.2 Perception-Distortion Curve

**Blau & Michaeli (CVPR 2018) proved:** There exists an inescapable trade-off boundary between perceptual quality (perceptual index) and distortion (PSNR/SSIM) — the **perception-distortion trade-off curve (感知-失真曲线, P-D Tradeoff)**.

Diffusion models occupy the "high perceptual quality" end of the curve (low PSNR but high perceptual quality as measured by LPIPS); discriminative networks (RRDB, NAFNet) occupy the "high fidelity" end (high PSNR but flat textures).

**Engineering selection principle:** For face/portrait super-resolution, prioritize perceptual quality (diffusion models); for scientific imaging or medical imaging, prioritize low distortion (discriminative methods).

---

## §7 Code

See the companion notebook *See §6 Code section for runnable examples.*, which covers:

- **DDPM forward noising visualization:** Shows the noising process for an input image at stages $t=0, 100, 500, 1000$
- **DDIM inference step comparison:** Compares PSNR and visual quality for 1000-step / 100-step / 20-step DDIM on a super-resolution task
- **Noise schedule visualization:** Plots the $\bar{\alpha}_t$ curves for the linear, cosine, and Sigmoid schedules
- **StableSR inference example:** Loads a pretrained StableSR model to perform 4× super-resolution on a low-resolution image and showcases the generated details
- **Perception-distortion curve plot:** Compares RRDB, ESRGAN, SR3, StableSR, and DiffIR in PSNR vs. LPIPS space

---

## §8 Glossary

**DDPM (Denoising Diffusion Probabilistic Models)**
The standard diffusion model framework established by Ho et al. (NeurIPS 2020). Forward process $q(x_t|x_{t-1}) = \mathcal{N}(x_t; \sqrt{1-\beta_t}x_{t-1}, \beta_t\mathbf{I})$ gradually adds noise until reaching Gaussian noise; the reverse process trains a neural network $\epsilon_\theta(x_t, t)$ to predict the noise via simplified objective $\mathcal{L}_{simple} = \mathbb{E}[\|\epsilon - \epsilon_\theta(\sqrt{\bar\alpha_t}x_0 + \sqrt{1-\bar\alpha_t}\epsilon, t)\|^2]$. Here $\bar{\alpha}_t = \prod_{s=1}^t(1-\beta_s)$ is the cumulative noise schedule, $T=1000$ steps. Forms the theoretical foundation for diffusion-based image restoration.

**DDIM (Denoising Diffusion Implicit Models)**
Song et al. (ICLR 2021) replace DDPM's stochastic Markovian sampling with a deterministic non-Markovian process: $x_{t-1} = \sqrt{\bar\alpha_{t-1}}\hat{x}_0(x_t) + \sqrt{1-\bar\alpha_{t-1}}\epsilon_\theta(x_t, t)$, where $\hat{x}_0$ is the clean image predicted at the current step. Deterministic sampling paths enable skip-step inference (1000 steps → 10 steps), with 10–100× inference speedup and minimal quality loss. DDPM-trained models can use DDIM sampling without retraining.

**Score Function / Score Matching**
Framework proposed by Song & Ermon (NeurIPS 2019): learn the gradient of the data distribution $s_\theta(x) \approx \nabla_x \log p(x)$ (score function) and sample using Langevin dynamics. Key equivalence: $s_\theta(x_t, t) = -\epsilon_\theta(x_t, t)/\sqrt{1-\bar\alpha_t}$ — noise prediction networks and score networks are fundamentally identical; both theoretical frameworks unify in DDPM.

**SR3 (Super-Resolution via Repeated Refinement)**
Saharia et al. (TPAMI 2023): first diffusion model applied to image super-resolution. Low-resolution image is bicubically upsampled and concatenated with $x_t$ as input to a conditional U-Net denoiser. Cascaded architecture (16×16→128×128→512×512, each stage trained independently) achieves high magnification. On 8× face super-resolution, LPIPS substantially better than GAN methods (ESRGAN) — the classic demonstration of the perception-distortion trade-off with diffusion models.

**Palette (Unified Diffusion Image Restoration)**
Saharia et al. (SIGGRAPH 2022): proves a single diffusion framework can handle 4 restoration tasks simultaneously (colorization, inpainting, JPEG artifact removal, super-resolution). Backbone is a Self-Attention U-Net; task conditioning is achieved solely through concatenation with the degraded image (no task-specific modules). Each task trained independently, with the same code and framework handling very different degradation types.

**StableSR (Latent Diffusion Super-Resolution)**
Wang et al. (IJCV 2024): builds on Stable Diffusion (LDM, Rombach et al., CVPR 2022) and moves super-resolution into the 8×-compressed latent space. Frozen VAE encoder maps the low-resolution image to $z_y$, concatenated into the diffusion U-Net; frozen VAE decoder outputs the high-resolution result. Core innovation: Time-Aware Feature Transform (TAWT) makes the decoding process aware of the current denoising stage to balance fidelity and detail. Inference time drops from 10+ minutes (pixel space) to ~30 seconds (512²).

**DiffIR (Efficient Diffusion for Image Restoration)**
Xia et al. (ICCV 2023): lightweight design in which the diffusion process runs only in an extremely low-dimensional **Compact IR Prior (CIRP)** space. CIRP encodes only high-level semantics (texture style, blur type), not the full image. Restoration parameters predicted from CIRP drive a lightweight Transformer via Cross-Attention. Only ~17M parameters (vs. StableSR's 860M); inference time ~1.5s (512²), oriented toward industrial deployment.

**IR-SDE (SDE-Based Image Restoration)**
Luo et al. (ICML 2023): unified framework modeling image restoration as $dx = f(x,t)dt + g(t)dW$ — an SDE trajectory starting from the degraded image $y$ (not Gaussian noise). The trajectory terminates at a distribution close to the ground truth $x_0$. Shorter sampling trajectory than standard conditional DDPM (comparable quality in < 100 steps); suitable for latency-sensitive industrial scenarios.

**Perception-Distortion Trade-off**
Theoretical lower bound proved by Blau & Michaeli (CVPR 2018): for any image restoration algorithm, there exists an inescapable trade-off boundary between perceptual quality (distance between generated image distribution and natural image distribution) and distortion (PSNR/SSIM relative to reference). Diffusion models occupy the "high perceptual quality" end of the curve (low PSNR, low LPIPS value); discriminative networks (RRDB/NAFNet) occupy the "low distortion" end (high PSNR, high LPIPS value). Engineering selection: prioritize perceptual quality for faces/portraits; prioritize distortion for scientific/medical imaging.

**Noise Schedule**
The hyperparameter controlling $\beta_t$ (the per-step noise addition amount) in the DDPM forward process. The linear schedule (original DDPM) increases noise too rapidly at the tail end. The **cosine schedule** (Improved DDPM) $\bar\alpha_t = \cos^2\!\big(\frac{t/T+0.008}{1.008}\cdot\frac{\pi}{2}\big)$ is smoother at the tail, avoiding over-destruction of the signal. The **Sigmoid schedule** is slow at both ends and fast in the middle, preserving more detail — recommended for image restoration tasks. Schedule choice affects training stability and few-step inference quality.

**Flow Matching (FM)**
Generative framework proposed by Lipman et al. (ICLR 2023): models generation as an ODE $dx/dt = v_\theta(x,t)$ driven by a learned velocity field, training via Conditional Flow Matching (CFM). The **Rectified Flow** variant (Liu et al., ICLR 2023) uses linear interpolation paths $x_t = (1-t)x_0 + tx_1$, making the velocity target a constant $(x_1 - x_0)$. Straight paths enable accurate integration in 1–4 Euler steps. Representative models: Stable Diffusion 3 (Esser et al., ICML 2024), FLUX.1.

**Consistency Models (CM)**
Framework by Song et al. (ICML 2023): learns a consistency function $f_\theta(x_t, t) \approx x_0$ that maps any point on a diffusion trajectory directly to the clean image in a single step. Training via Consistency Distillation (CD) uses a pretrained diffusion model as teacher. Single-step inference with NFE=1; 2–4 iterative refinement steps approach the quality of DDPM at 20 steps. Latent Consistency Model (LCM, Luo et al., 2023) applies this to latent diffusion models.

---

## §9 On-Device Deployment

> **Special note for this chapter:** On-device deployment of diffusion models is an active research direction, not yet a mature engineering reality. This section honestly records the current technical boundary.

### 9.1 Current Deployment Status and Technical Limits

The core bottleneck of diffusion model inference is **step count**: DDPM requires 1000 steps, each needing a complete U-Net forward pass. Even with DDIM compressed to 20 steps, processing one 512×512 frame on a phone NPU still takes seconds — far exceeding the 100ms budget of real-time ISP.

| Model Configuration | Inference Steps | A100 Latency (512²) | Phone NPU Estimated Latency | Viable for Real-Time ISP |
|--------------------|-----------------|--------------------|----------------------------|--------------------------|
| DDPM (pixel space) | 1000 | ~200s | Hours | No |
| DDIM 50 steps (StableSR) | 50 | ~15s | ~10–30 min | No |
| DDIM 20 steps (DiffIR-S) | 20 | ~1.5s | ~30–120s | No (offline usable) |
| LCM 4 steps | 4 | ~0.8s | ~10–30s | No (background usable) |
| LCM-ControlNet INT8 | 4 | ~0.8s | ~5–15s | Marginally viable for background processing |

**Key conclusion:** Real-time on-phone diffusion processing (< 200ms/frame) remains a **research direction, not engineering reality** as of 2024–2025. All mass-production phones support "post-capture background async processing" rather than real-time diffusion ISP.

### 9.2 Inference Framework Compatibility

| Framework | Quantization | Typical Speedup (vs CPU) | Notes |
|-----------|-------------|--------------------------|-------|
| Qualcomm SNPE/QNN | INT8/FP16 | HVX DSP 3–6× | Diffusion U-Net Attention layers require FP16; not fully INT8-safe |
| MTK NeuroPilot | INT8/INT4 mixed | APU 4–8× | Diffusion models require offline compilation via neuron_runtime (time-consuming) |
| TFLite + NNAPI | INT8 | 2–5× (device-dependent) | Universal on Android, but limited diffusion Attention operator support |
| ARM NN | INT8 | Mali GPU 2–4× | Open source, suitable for embedded; large diffusion models constrained by memory |
| Apple CoreML | FP16/INT8 | ANE 5–10× | iOS devices; LCM 4-step ~5–8s/frame on A17 Pro |

### 9.3 Quantization Accuracy Loss Reference (Diffusion-Specific)

Diffusion models are more sensitive to quantization than standard CNNs:

- **Attention QK product:** wide numerical range; INT8 easily overflows — keep Attention layers at FP16.
- **Timestep embedding layers:** few parameters but global influence; quantization error systematically shifts all denoising steps.
- **AdaLN modulation layers:** $\gamma(t), \beta(t)$ have large dynamic range — recommend INT16 or FP16.

| Quantization Scheme | PSNR Loss (SR task) | Memory Savings | Recommended Use |
|--------------------|---------------------|----------------|-----------------|
| FP32 | Baseline | — | Server inference |
| FP16 | < 0.1 dB | 50% | High-end phones (recommended) |
| W4A8 (4-bit weights, 8-bit activations) | 0.2–0.5 dB | ~70% | Flagship phones with memory constraints |
| Full INT8 | 0.8–2.0 dB | 75% | **Not recommended** (Attention layer overflow risk) |

**Recommendation:** Prioritize FP16 for on-device diffusion deployment. If memory is insufficient, use W4A8 mixed precision (INT4 for convolution layers, FP16 for Attention/AdaLN layers).

### 9.4 Viable Mobile Deployment Scenarios

**Scenario 1: DiffIR-S + DDIM 20 Steps (Background Processing)**
- 17M parameters; FP16 memory ~340MB — fits flagship phone requirements.
- Snapdragon 8 Gen 3 NPU estimated: ~15–30s/frame (512²); suitable for post-capture background async enhancement.
- User experience: capture → traditional ISP for instant preview → background diffusion enhancement → update album thumbnail.

**Scenario 2: LCM 4 Steps + INT8 Convolution (Near-Instant Preview)**
- 4-step inference reduces latency to ~5–15s/frame (Snapdragon 8 Gen 3 estimate).
- Suitable for "preview-before-capture" scenarios: long-press shutter triggers diffusion enhancement.
- Note: LCM's PSNR optimization for image restoration is limited; better suited for perceptual enhancement.

**Scenario 3: Traditional ISP + Conditional Diffusion Enhancement (Recommended Engineering Approach)**
```
Normal scenes:  Traditional ISP (< 10ms, real-time preview)
                ↓ night/high-ISO detection
Low-light:      Traditional ISP (instant preview) + background diffusion enhancement (15–60s)
                ↓ on completion
                Replace album photo (similar to Night Sight computational photography flow)
```

### 9.5 Reference Platform: Raspberry Pi 4B + IMX477

- ARM Cortex-A72 @1.8GHz, no NPU.
- DiffIR-S FP32, DDIM 20 steps, 512²: estimated ~30–60 minutes — **unsuitable for any real-time application**.
- Recommended only for algorithm verification; actual on-device validation must be performed on the target phone SoC.

### 9.6 One-Step Diffusion Inference: Consistency Models

**Background:** DDIM at 20 steps still requires ~1.5s on an A100, and ~30–120s on a phone NPU. Two technical paths for compressing inference steps emerged in 2023–2024: distillation and Consistency Models.

**Core Idea of Consistency Models (Song et al., ICML 2023):**

Consistency models directly learn the mapping $f_\theta(x_t, t) \approx x_0$ from any point $x_t$ on the diffusion trajectory to the starting point $x_0$, rather than denoising step by step. Training objective (Consistency Distillation):

$$\mathcal{L}_{CD} = \mathbb{E}\left[d\!\left(f_\theta(x_{t_{n+1}}, t_{n+1}),\; f_{\theta^-}(\hat{x}^\phi_{t_n}, t_n)\right)\right]$$

where:
- $d(\cdot,\cdot)$: perceptual distance function (e.g., LPIPS)
- $\theta^-$: EMA parameters (stop-gradient target network)
- $\hat{x}^\phi_{t_n}$: single-step ODE solver (e.g., DDIM 1 step) result from $x_{t_{n+1}}$

The consistency constraint requires the model to give a consistent $x_0$ prediction at different timesteps on the same trajectory, enabling single-step sampling.

**IR-CM (Image Restoration via Consistency Model, Gong & Ma, NeurIPS 2024):**

Applies Consistency Models to image restoration, achieving **single-step inference** on denoising, super-resolution, and deraining tasks. Core modification: replaces the standard CM's Gaussian noise starting point with the degraded image $y$, via conditional consistency distillation, allowing the model to jump directly from a degraded input to a clean output. PSNR loss compared to DDIM 20-step baseline is < 0.3 dB; inference speed improvement ~20×.

**Updated Deployment Latency Comparison:**

| Method | Inference Steps | A100 Latency (512²) | Phone NPU Estimate | Use Case |
|--------|----------------|--------------------|--------------------|---------|
| DDIM 20 steps (DiffIR-S) | 20 | ~1.5s | ~30–120s | Offline post-processing |
| LCM 4 steps | 4 | ~0.8s | ~10–30s | Background processing |
| Consistency Model 1 step (IR-CM) | **1** | **~0.2s** | **~3–8s** | Fast background processing |
| OSEDiff INT8 | 1 | ~0.04s | ~1–3s | **Approaching near-real-time** |

**OSEDiff (Wu et al., NeurIPS 2024):** One-step diffusion super-resolution combining one-step diffusion distillation with INT8 quantization. Estimated ~1–3s/frame (512²) on Snapdragon 8 Gen 3 NPU (extrapolated from A100 benchmark by compute ratio, not original paper measured data) — currently the closest diffusion ISP solution to phone-practical use. Differs from IR-CM in that OSEDiff additionally uses Quantization-Aware Distillation to keep INT8 precision loss under 0.2 dB.

**Engineering Significance:** One-step diffusion inference pushes the feasibility boundary of on-phone diffusion ISP from "offline minutes" to "background seconds." Estimated to enter mass production in 2025–2026 as flagship SoC compute improves. Compared to LCM, Consistency Models require no iterative steps, are more NPU-batch-scheduling-friendly, and have lower peak memory.

---

## §10 Inference Acceleration: Engineering Breakthroughs from Thousand Steps to One

> **Positioning:** This section systematically integrates and extends the content from §1.4, §2.9, and §9.6, focusing on the latest 2023–2025 advances in one-step/few-step inference, with emphasis on the Flow Matching route and engineering deployment data.

### 10.1 Problem Background: 1000 Steps is the Biggest ISP Deployment Barrier

Standard DDPM requires 1000 inference steps, each calling U-Net once. Even with DDIM compressed to 20 steps, processing one 512×512 frame on a phone NPU still takes ~30–120 seconds — 3 orders of magnitude above real-time ISP's 100ms budget.

**This is not fixable by tuning** — it is a structural bottleneck of the diffusion inference paradigm:
- Each denoising step depends on the previous step's output; no inter-step parallelism (unlike layer-parallel convolution networks).
- U-Net Attention layers at high resolution are memory-bandwidth-limited; NPU utilization is low.
- Compressing steps to the extreme (< 5 DDIM steps) causes cliff-edge quality degradation (§2.9 quantified: DDIM 5-step PSNR loss ~2.2 dB).

Post-2022 research split into two paths: **faster samplers** (DDIM/DPM-Solver family) and **model restructuring** (Consistency Models / Flow Matching). The former leaves the model unchanged; the latter eliminates multi-step dependency at the root.

### 10.2 DDIM: Engineering Value of Deterministic Sampling

§1.4 gives the DDIM core formula. Here we add its engineering implications and limitations.

DDIM replaces stochastic Markovian sampling with a deterministic non-Markovian process (setting stochastic coefficient $\sigma_t = 0$):

$$x_{t-1} = \sqrt{\bar{\alpha}_{t-1}} \underbrace{\frac{x_t - \sqrt{1-\bar{\alpha}_t}\,\epsilon_\theta(x_t, t)}{\sqrt{\bar{\alpha}_t}}}_{\hat{x}_0 \text{ (predicted clean image)}} + \sqrt{1-\bar{\alpha}_{t-1}}\,\epsilon_\theta(x_t, t)$$

**Three Key Engineering Properties:**
1. **Deterministic:** Same $x_T$ always produces the same output — convenient for debugging and comparison experiments.
2. **No retraining required:** DDPM-trained models use DDIM sampling directly with zero additional overhead.
3. **Skip-step compatible:** Sampling sequence $\{t_N, t_{N-1}, \ldots, t_1, 0\}$ can be designed freely as long as it is monotonically decreasing.

**Limitation:** DDIM is a first-order ODE approximation; truncation error grows rapidly when step sizes exceed 100. DPM-Solver (Lu et al., NeurIPS 2022) and DPM-Solver++ use high-order Runge-Kutta integration, achieving ~0.3–0.8 dB better PSNR at the same step count — the practical replacement for DDIM.

### 10.3 Consistency Models: Breaking the Step Lower Bound

**Yang Song et al., ICML 2023** proposed a framework that theoretically eliminates multi-step dependency.

**Core Idea — Consistency Function:**

Define a consistency function $f: (x_t, t) \mapsto x_0$ requiring consistent $x_0$ predictions at all timesteps on the same diffusion trajectory:

$$f_\theta(x_t, t) = f_\theta(x_{t'}, t') \quad \forall\; t, t' \in [\epsilon, T]$$

**Boundary condition:** $f_\theta(x_0, 0) = x_0$ (identity mapping at $t=0$).

**Two Training Modes:**
- **Consistency Distillation (CD):** Uses a pretrained diffusion model as teacher; training objective: $\mathcal{L}_{CD} = \mathbb{E}[d(f_\theta(x_{t_{n+1}}, t_{n+1}),\; f_{\theta^-}(\hat{x}^{\phi}_{t_n}, t_n))]$
- **Consistency Training (CT):** Trains directly from data without a teacher model; quality slightly below CD.

**Inference (NFE=1):** $x_0 = f_\theta(x_T, T)$ — single network forward pass yields $x_0$. 2–4 step iterative refinement approaches DDPM 20-step quality.

**Relationship with LCM:** Latent Consistency Model (Luo et al., 2023) applies CM to latent diffusion models — essentially CD distillation in latent space, not an independent methodological innovation.

### 10.4 Flow Matching: Replacing Curved Diffusion with Straight Paths

**Lipman et al., ICLR 2023 (Meta AI)** proposed Flow Matching (FM).

**Starting Point:** DDPM's diffusion path is a highly curved stochastic process trajectory; ODE solving requires dense sampling. If the path can be made "straight," fewer integration steps suffice for accurate results.

**Flow Matching ODE Framework:**

$$\frac{dx}{dt} = v_\theta(x, t), \quad t \in [0, 1]$$

Trained via Conditional Flow Matching (CFM):

$$\mathcal{L}_{CFM} = \mathbb{E}_{t, x_0, x_1}\bigl[\|v_\theta(x_t, t) - u_t(x_t | x_0, x_1)\|^2\bigr]$$

**Rectified Flow (Liu et al., ICLR 2023):** Linear path $x_t = (1-t)x_0 + t x_1$; corresponding velocity field is constant $u_t = x_1 - x_0$. The straight path minimizes ODE solution curvature, yielding reasonable results even with a 1-step Euler method.

**Essential Difference from DDPM:**

| Dimension | DDPM | Flow Matching |
|-----------|------|---------------|
| Path type | Stochastic, curved (SDE) | Deterministic, straight (ODE) |
| Integration difficulty | High (dense steps needed) | Low (1–4 Euler steps) |
| Training target | Noise prediction $\epsilon_\theta$ | Velocity field $v_\theta$ |
| Quality at equal NFE | Baseline | Better (lower curvature) |
| Industrial representatives | DDPM/LDM family | Stable Diffusion 3, FLUX.1 |

**For Image Restoration:** Set $x_0 = y$ (degraded), $x_1 = x_{clean}$ (clean). Train velocity field $v_\theta(x_t, t | y)$ predicting the direction from degraded to clean. At inference, start from the degraded image and integrate 1–4 Euler steps to reach the restored result — naturally bypassing the high-step-count problem of "starting from pure Gaussian noise."

**InstaFlow (Liu et al., ICLR 2024):** First application of Rectified Flow to image super-resolution. Core design: Reflow operation (train flow model on generated $(x_0, x_1)$ pairs to further straighten paths); 1-step inference formula $\hat{x}_1 = x_0 + v_\theta(x_0, 0)$. On NVIDIA RTX 3090, InstaFlow 1-step inference latency is approximately **45–50 ms** (512×512 input); LPIPS comparable to DDPM 20-step; PSNR loss ~0.4–0.6 dB (DIV2K 4× SR).

### 10.5 IR-CM: Consistency Models Applied to Image Restoration

**IR-CM (Gong & Ma, NeurIPS 2024)** (architecture introduced in §9.6; engineering details here)

**Key Modification:** Standard CM starts from $x_T \sim \mathcal{N}(0, \mathbf{I})$; IR-CM changes the starting point to the degraded image $y$ via **conditional consistency distillation**:

$$\mathcal{L}_{IR-CD} = \mathbb{E}\bigl[d\bigl(f_\theta(x_{t_{n+1}}, t_{n+1}, y),\; f_{\theta^-}(\hat{x}^{\phi}_{t_n}, t_n, y)\bigr)\bigr]$$

Inference: $\hat{x}_0 = f_\theta(y, T, y)$ — one step yields the restored image.

**Performance (IR-CM original paper):**

| Task/Test Set | PSNR (DDIM 20-step baseline) | PSNR (IR-CM 1-step) | Speedup |
|--------------|------------------------------|---------------------|---------|
| Denoising (SIDD) | 39.9 dB | 39.78 dB (−0.1 dB) | ~20× |
| Denoising (DND) | 40.1 dB | 39.91 dB (−0.2 dB) | ~20× |
| Super-resolution (DIV2K 4×) | 28.4 dB | 28.1 dB (−0.3 dB) | ~20× |
| Deraining (Rain100L) | 40.8 dB | 40.3 dB (−0.5 dB) | ~20× |

### 10.6 Engineering Practice: Inference Efficiency Comparison

| Method | NFE | PSNR (Set5 4×, reference) | Estimated NPU Latency | VRAM (512²) |
|--------|-----|--------------------------|----------------------|-------------|
| DDPM (pixel space) | 1000 | Baseline (~31 dB range) | Not viable (hours) | ~2 GB |
| DDIM 50 steps | 50 | ≈Baseline −0.1 dB | Viable on high-end server | ~500 MB |
| DDIM 20 steps (DiffIR-S) | 20 | ≈Baseline −0.8 dB | Snapdragon 8 Gen 3 ~30–120s | ~340 MB (FP16) |
| DPM-Solver++ 10 steps | 10 | ≈Baseline −0.5 dB (~0.5 dB better than DDIM 10-step) | ~15–60s | ~340 MB |
| LCM 4 steps | 4 | — (perceptual-first) | ~10–30s | ~500 MB |
| Consistency Model 1 step (IR-CM) | **1** | ≈Baseline −0.3 dB | **Snapdragon 8 Gen 3 ~3–8s** | ~340 MB |
| Flow Matching 1–4 steps (FM-IR, experimental) | 1–4 | Close to CM 1-step | Comparable to CM | ~340 MB |
| OSEDiff INT8 | 1 | — (perceptual-first) | **~1–3s (estimated)** | ~200 MB (INT8) |

> **Note:** "NPU Latency" values are extrapolated from A100 public benchmarks by compute ratio; Snapdragon 8 Gen 3 Hexagon NPU (approximately 34 TOPS, third-party estimate) vs. A100 (312 TOPS FP16) ratio ~1:7. Actual values are significantly affected by memory bandwidth and operator adaptation differences — these are not original paper measured data.

**Method Selection (2025 Engineering Perspective):**
- **Maximize image quality (offline, no time limit):** DiffBIR or StableSR 50 steps; best LPIPS.
- **Background async enhancement (15–60s acceptable):** DiffIR-S + DDIM 20 steps FP16; best cost-effectiveness.
- **Fast background processing (target 5–10s):** IR-CM 1-step distillation; PSNR loss < 0.3 dB. Recommended.
- **Exploring real-time boundary (target < 3s):** OSEDiff INT8; currently most aggressive production direction.
- **Real-time ISP (< 100ms):** Diffusion solutions infeasible; use NAFNet/Restormer discriminative methods.

---

## §11 Further Reading and Research Frontiers

### 11.1 2024–2025 Key Paper Tracking

- **Score Distillation Sampling (SDS) for ISP parameter optimization (2024):** Uses diffusion priors as a regularizer for optimizing traditional ISP tuning, without end-to-end diffusion model training.
- **Diffusion for RAW-to-RGB** (§3 already mentions GDP): Running diffusion restoration directly in the RAW domain avoids information loss from ISP pipeline processing. Multiple CVPR/ICCV 2024 papers follow up on this direction.
- **Video Diffusion and ISP integration:** Temporal consistency is the next major challenge for diffusion ISP. Frame-independent inference causes flickering; 2024 solutions including AnimateDiff and FLATTEN begin exploring temporally consistent conditional diffusion.
- **Flow Matching for image restoration:** 2024–2025 sees growing work fine-tuning Stable Diffusion 3 (FM framework) for super-resolution/denoising tasks; performance approaches CM methods but training is more stable. Worth continued monitoring.

---

## References

**Diffusion Model Foundations:**
- Ho, J., Jain, A., & Abbeel, P. (2020). **Denoising diffusion probabilistic models.** *NeurIPS 2020*.
- Song, J., Meng, C., & Ermon, S. (2021). **Denoising diffusion implicit models.** *ICLR 2021*. [DDIM]
- Song, Y., & Ermon, S. (2019). **Generative modeling by estimating gradients of the data distribution.** *NeurIPS 2019*. [Score Matching]

**Diffusion Models for Image Restoration:**
- Saharia, C., et al. (2021). **Image super-resolution via iterative refinement.** *IEEE TPAMI*, 45(4), 4713-4726. [SR3]
- Saharia, C., et al. (2022). **Palette: Image-to-image diffusion models.** *ACM SIGGRAPH 2022*. [Palette]
- Wang, J., et al. (2024). **Exploiting diffusion prior for real-world image super-resolution.** *International Journal of Computer Vision (IJCV)*, 2024. [StableSR] (arXiv:2305.07015)
- Lin, X., et al. (2024). **DiffBIR: Towards blind image restoration with generative diffusion prior.** *ECCV 2024*. (arXiv:2308.15070) [DiffBIR]
- Yue, Z., et al. (2023). **ResShift: Efficient diffusion model for image super-resolution by residual shifting.** *NeurIPS 2023*. (arXiv:2307.12348) [ResShift]
- Wu, J., et al. (2024). **SeeSR: Towards semantics-aware real-world image super-resolution.** *CVPR 2024*. (arXiv:2311.16518) [SeeSR]
- Xia, B., et al. (2023). **DiffIR: Efficient diffusion model for image restoration.** *ICCV 2023*. [DiffIR]
- Luo, Z., et al. (2023). **Image restoration with mean-reverting stochastic differential equations.** *ICML 2023*. [IR-SDE]
- Ye, J., et al. (2024). **Scaling up to excellence: Practicing model scaling for photo-realistic image restoration at scale.** *CVPR 2024*. (arXiv:2401.13627) [SUPIR]

**Latent Diffusion Model Foundations:**
- Rombach, R., et al. (2022). **High-resolution image synthesis with latent diffusion models.** *CVPR 2022*. [Stable Diffusion / LDM]

**Perception-Distortion Trade-off:**
- Blau, Y., & Michaeli, T. (2018). **The perception-distortion tradeoff.** *CVPR 2018*.

**Generative Prior Restoration:**
- Fei, B., et al. (2023). **Generative diffusion prior for unified image restoration and enhancement.** *CVPR 2023*. [GDP]

**Inference Acceleration:**
- Luo, S., et al. (2023). **Latent consistency models: Synthesizing high-resolution images with few-step inference.** arXiv:2310.04378. [LCM]
- Sauer, A., et al. (2023). **Adversarial diffusion distillation.** arXiv:2311.17042. [SDXL Turbo]
- Song, Y., et al. (2023). **Consistency models.** *ICML 2023*. (arXiv:2303.01469) [CM]
- Gong, Z., & Ma, L. (2024). **IR-CM: The fast and general-purpose image restoration method based on consistency model.** *NeurIPS 2024*. [IR-CM]
- Wu, S., et al. (2024). **OSEDiff: One-step diffusion for real-world super-resolution.** *NeurIPS 2024*. [OSEDiff]

**Flow Matching:**
- Lipman, Y., et al. (2023). **Flow matching for generative modeling.** *ICLR 2023*. (arXiv:2210.02747)
- Liu, X., et al. (2023). **Flow straight and fast: Learning to generate and transfer data with rectified flow.** *ICLR 2023*. (arXiv:2209.03003) [Rectified Flow]
- Esser, P., et al. (2024). **Scaling rectified flow transformers for high-resolution image synthesis.** *ICML 2024*. (arXiv:2403.03206) [Stable Diffusion 3]
- Liu, X., et al. (2024). **InstaFlow: One step is enough for high-quality diffusion-based text-to-image generation and super-resolution.** *ICLR 2024*. (arXiv:2309.06380)
- Ohayon, G., Michaeli, T., & Elad, M. (2025). **Posterior-mean rectified flow: Towards minimum MSE photo-realistic image restoration.** *ICLR 2025*. (arXiv:2410.00418) [PMRF]
- Yue, Z., Liao, K., & Loy, C. C. (2025). **Arbitrary-steps image super-resolution via diffusion inversion.** *CVPR 2025*. (arXiv:2412.09013) [InvSR]
