# Part 3, Chapter 02: End-to-End Image Restoration with U-Net

> **Pipeline position:** DL module replacing or augmenting full denoising pipeline
> **Prerequisites:** Ch DL Overview, Chapter 4 (Noise Models)
> **Reader path:** DL Researcher

---

## §1 原理 (Theory)

### U-Net Architecture

The U-Net, originally proposed by Ronneberger et al. (2015) for biomedical image segmentation, has become the dominant backbone for image restoration tasks in ISP. Its success rests on a single architectural insight: the encoder-decoder structure with **skip connections** allows the network to simultaneously leverage global context (for understanding the degradation pattern) and fine-grained local detail (for accurate reconstruction).

#### Why Skip Connections?

In a plain encoder-decoder without skip connections, spatial detail is progressively discarded during the downsampling stages. The bottleneck representation must encode both "what degradation is present" and "where every texture detail was"—a conflicting demand. Skip connections resolve this by routing high-resolution feature maps directly from the encoder to the corresponding decoder level, bypassing the bottleneck. The decoder can then use the skip features to recover fine detail, while the bottleneck focuses on high-level degradation understanding.

Empirically, removing skip connections from a U-Net for denoising causes a 1-3 dB PSNR drop, depending on noise level. This is because fine-grained texture information at edges and fine patterns is precisely the information that is encoded in the high-resolution encoder features.

#### Encoder: Progressive Downsampling

The encoder applies a series of convolutional blocks with stride-2 downsampling (or max-pooling), halving spatial resolution at each level while doubling the number of feature channels. For a 3-level U-Net:

```
Input:    [B, C_in, H, W]
Level 1:  [B, 64,  H/2, W/2]   → skip connection to decoder level 1
Level 2:  [B, 128, H/4, W/4]   → skip connection to decoder level 2
Level 3:  [B, 256, H/8, W/8]   → bottleneck
```

Each encoder block typically consists of: Conv → BatchNorm → ReLU → Conv → BatchNorm → ReLU. Strided convolution (stride=2) for downsampling is preferred over max-pooling in modern implementations because it is learnable and preserves more information.

#### Decoder: Progressive Upsampling

The decoder reverses the encoder, progressively restoring spatial resolution. At each level, the decoder:
1. Upsamples the feature map (2x bilinear or transposed convolution).
2. Concatenates the skip connection from the corresponding encoder level.
3. Applies a convolutional block to fuse the upsampled and skip features.

```
Bottleneck:  [B, 256, H/8, W/8]
Level 2 up:  [B, 128, H/4, W/4]  ← concatenate encoder level 2 skip [B, 128, H/4, W/4]
Level 1 up:  [B, 64,  H/2, W/2]  ← concatenate encoder level 1 skip [B, 64, H/2, W/2]
Output:      [B, C_out, H, W]
```

The output layer is a 1x1 convolution mapping to the desired number of output channels. For residual training, the network outputs the noise estimate; the clean image is obtained by subtracting the noise estimate from the input.

#### Transposed Convolution vs. Bilinear Upsampling

Transposed convolution (also called fractionally-strided convolution or deconvolution) is a learnable upsampling operation. Its primary disadvantage is susceptibility to **checkerboard artifacts**: periodic grid patterns in the output caused by uneven overlap of the transposed convolution kernel. The standard fix is to use bilinear upsampling followed by a regular convolution, which eliminates the artifact at the cost of slightly lower expressiveness.

### Loss Functions for Restoration

The loss function is the primary lever for controlling the quality-fidelity tradeoff in image restoration.

**L1 Loss (Mean Absolute Error)**

```
L_L1 = (1/N) * Σ |y_pred - y_gt|
```

L1 loss corresponds to maximum likelihood estimation under a Laplacian noise model. It produces sharper outputs than L2 because the Laplacian distribution has heavier tails—large errors are penalized less severely relative to the L2 case, so the optimizer does not strongly incentivize averaging over uncertainty. In practice, L1 is the default choice for most ISP restoration tasks.

**L2 Loss (Mean Squared Error)**

```
L_L2 = (1/N) * Σ (y_pred - y_gt)^2
```

L2 corresponds to maximum likelihood under a Gaussian noise model. It penalizes large errors quadratically, which makes gradients large when the prediction is far from GT—helpful for fast convergence early in training. However, when there is genuine ambiguity (e.g., fine texture that could plausibly be reconstructed multiple ways), L2 averages over the possibilities, producing blurry outputs.

**SSIM Loss**

```
L_SSIM = 1 - SSIM(y_pred, y_gt)
```

SSIM measures structural similarity by comparing local statistics (mean, variance, covariance) between patches. As a loss function, it penalizes changes in local structure more than pixel-level MSE, which helps preserve edges and textures. It is typically used as an additive term alongside L1.

**Perceptual/VGG Loss**

```
L_VGG = Σ_l || φ_l(y_pred) - φ_l(y_gt) ||^2_F
```

where φ_l denotes the feature map at layer l of a pretrained VGG-19 network. By comparing feature activations rather than raw pixels, the perceptual loss measures semantic similarity. High-level VGG features capture texture patterns and object-level structures that correlate strongly with human visual preference.

**Practical Combined Recipe**

For a general-purpose ISP restoration network:

```
L_total = L_L1 + λ_ssim * L_SSIM + λ_vgg * L_VGG
```

Typical weights: λ_ssim = 0.1, λ_vgg = 0.01. The VGG loss is weighted lowest because it can introduce hallucinated textures if weighted too heavily.

### Training Recipe

Standard configuration for U-Net ISP training:

| Hyperparameter | Value | Rationale |
|----------------|-------|-----------|
| Patch size | 128-256 px | Larger patches give more context; limited by VRAM |
| Batch size | 16-32 | Large batch stabilizes gradient estimates |
| Optimizer | Adam (β1=0.9, β2=0.999) | Adaptive LR handles different gradient scales |
| Initial LR | 2e-4 | Standard starting point for Adam on ISP tasks |
| LR schedule | Cosine annealing | Smooth decay; avoids abrupt LR drops |
| Epochs | 200-500 | Depends on dataset size |
| Augmentation | Flip + 90° rotation | Safe for RAW Bayer patterns |

### Noise2Noise: Training Without Clean Ground Truth

The standard supervised approach requires paired noisy-clean images. Lehtinen et al. (2018) showed that this constraint is unnecessary: a network can be trained on pairs of **noisy-noisy** images (two independent noisy observations of the same scene) and converge to the same solution as supervised training. The key insight is that the expected value of the noisy observations is the clean image, so minimizing expected L2 loss over noisy pairs is equivalent to minimizing against the clean target.

In practice, collecting two independent noisy shots of a static scene is far easier than collecting ground truth via multi-frame averaging. Noise2Noise enables training on in-the-wild data: burst photography pairs, video frames, or even synthetic corruption applied independently twice.

**Limitation**: Noise2Noise requires that the noise be zero-mean and independent between the two observations. Structured noise (fixed-pattern noise, JPEG compression artifacts) violates this assumption and cannot be handled by standard Noise2Noise.

### Self-Supervised Approaches

When even paired noisy observations are unavailable, blind-spot networks and Noise2Void allow training on single noisy images.

**Noise2Void**: Corrupts random pixels during training ("masking") and trains the network to predict the original pixel value from surrounding context. The blind spot prevents the network from simply copying the noisy input value.

**Blind-spot networks (BNs)**: Architecturally enforce that each output pixel does not depend on the corresponding input pixel, using masked convolutions. This forces the network to denoise using only neighborhood context.

Self-supervised methods are 1-3 dB below supervised methods on standard benchmarks but are increasingly valuable for sensor-specific adaptation where clean ground truth is unavailable.

---

## §2 State-of-the-Art Methods

### 2.1 NAFNet — Non-linear Activation Free Network (Chen et al., ECCV 2022)

**Core idea:** NAFNet (Non-linear Activation Free Network, 非线性激活免除网络) removes all conventional nonlinear activations (ReLU, GELU) and replaces them with a simpler gating mechanism, achieving simultaneous SOTA on SIDD denoising and GoPro deblurring. **[4]**

**SimpleGate mechanism:** Split the input feature map into two halves along the channel dimension and multiply element-wise:

$$\text{SimpleGate}(X_1, X_2) = X_1 \odot X_2, \quad X_1, X_2 = \text{split}(\text{Conv}(F), \text{dim=channel})$$

Compared to activations like GELU ($x \cdot \Phi(x)$), SimpleGate drops the Gaussian CDF approximation $\Phi(x)$, retaining only the gating effect at half the compute with better numerical stability.

**Why removing nonlinear activations works:** A common misconception is that "removing activations improves training stability". NAFNet's actual contribution is not eliminating activations — it is replacing them with SimpleGate. The difference: ReLU/GELU are **pointwise nonlinearities**, while SimpleGate is **channel-wise multiplicative gating** — $X_1 \odot X_2$ lets one feature stream selectively gate the other, achieving dynamic channel weighting. This is a qualitatively different nonlinearity.

The ablation in Chen et al. reveals the real finding: for **low-level vision tasks** like image restoration, textures and noise signals are naturally sparse. Multiplicative gating matches this sparse activation pattern well. The discriminative nonlinearities of ReLU/GELU, designed for classification, offer limited benefit in restoration. SimpleGate achieves more appropriate feature interaction for low-level vision with fewer parameters.

**SCAM (Simplified Channel Attention Module):** NAFNet uses a simplified channel attention in place of SE Block:

$$\text{SCAM}(F) = F \odot W(F), \quad W(F) = \text{sigmoid}\!\left(\text{Linear}\!\left(\text{GAP}(F)\right)\right)$$

where GAP is Global Average Pooling and Linear is a single fully-connected layer with no hidden layer (contrast with SE Block's two-layer MLP). Compute cost is roughly 1/4 of standard SE Block, with equivalent performance.

**SIDD Validation Set SOTA:**

| Method | SIDD PSNR↑ (val) | SIDD SSIM↑ | Params | Latency (1080p, A100) |
|--------|------------------|-----------|--------|----------------------|
| DnCNN-B | 38.60 **[2]** | 0.943 | 0.56M | ~0.05s |
| RIDNet | 41.99 | 0.971 | 1.5M | ~0.3s |
| MPRNet | 42.13 | 0.961 | 20.1M | ~0.5s |
| Restormer | 42.06 **[5]** | 0.956 | 26.1M | ~0.9s |
| **NAFNet-32** | **42.61** **[4]** | **0.964** | **17.1M** | **~0.4s** |
| NAFNet-64 | 43.14 **[4]** | 0.968 | 67.9M | ~1.6s |
| MambaIR | 42.75 **[15]** | 0.965 | 26.7M | ~0.8s |

> ⚠️ **Benchmark note:** Numbers above are **SIDD Validation Set** results (computable locally). The **SIDD Benchmark Test Set** is evaluated via an online server and yields approximately 2 dB lower: Restormer = 40.02 dB, NAFNet-64 = 40.30 dB, DiffIR = 40.47 dB. The two protocols are **not directly comparable**.

---

### 2.2 Restormer — Efficient Transformer for High-Resolution Restoration (Zamir et al., CVPR 2022)

**Motivation:** Standard Vision Transformer (ViT) self-attention has complexity $O\!\left((HW)^2 C\right)$; for a 4MP image ($2000 \times 2000$) this equals $1.6 \times 10^{13}$ operations — completely infeasible. Restormer solves this by moving the attention dimension from spatial to channel. **[5]**

**MDTA (Multi-Dconv Head Transposed Attention):** Attention is computed along the channel dimension rather than spatial:

$$Q, K, V \in \mathbb{R}^{HW \times C}, \quad \text{Attn} = V \cdot \text{Softmax}\!\left(\frac{K^T Q}{\sqrt{d}}\right)$$

The attention matrix is $C \times C$ (not $(HW) \times (HW)$), reducing complexity to $O(HW C^2)$. When $C \ll HW$ (typical case: $C=128$, $HW=2000\times2000$), this saves approximately $10^4\times$ compute.

The "Transposed" name derives from the layout: standard attention has $Q, K \in \mathbb{R}^{HW \times C}$, so $K^T \in \mathbb{R}^{C \times HW}$ and the product $K^T Q$ has shape $C \times C$ — attention unfolds along the channel dimension, hence "transposed".

**Depth-wise convolution augmentation:** The Q/K/V projection layers include a 3×3 depth-wise convolution (DWConv) to inject local positional cues (addressing the lack of spatial awareness in pure channel attention):

$$Q = W_Q \cdot \text{DWConv}(F), \quad K = W_K \cdot \text{DWConv}(F), \quad V = W_V \cdot \text{DWConv}(F)$$

**GDFN (Gated-Dconv Feed-Forward Network):** Restormer replaces the standard MLP FFN with a gated depth-wise FFN:

$$\text{GDFN}(F) = W_2\!\left(\phi\!\left(W_1^{(1)} \cdot \text{DWConv}(F)\right) \odot W_1^{(2)} \cdot \text{DWConv}(F)\right)$$

where $\phi$ is GELU activation. The gating structure is analogous to SimpleGate — one path activates, one passes through — effectively suppressing unhelpful feature propagation.

**Complexity comparison:**

| Attention type | Complexity | Estimated FLOPs at 1080p (C=64) |
|---------------|--------|----------------------|
| Standard spatial self-attention (ViT) | $O\!\left((HW)^2 C\right)$ | $\approx 10^{13}$ |
| Swin Transformer (window attention) | $O\!\left(HW \cdot w^2 C\right)$ | $\approx 10^{10}$ |
| **Restormer (transposed attention)** | **$O(HW C^2)$** | **$\approx 10^{9}$** |
| NAFNet (no attention) | $O(HWC)$ | $\approx 10^{8}$ |

---

### 2.3 MPRNet — Multi-Stage Progressive Image Restoration (Zamir et al., CVPR 2021)

**Motivation:** Single-stage networks (e.g., U-Net) struggle with severe degradations (heavy motion blur, dense rain streaks) because a single forward pass must simultaneously optimize both "degradation type identification" and "pixel-level reconstruction". MPRNet decomposes restoration into multiple progressive subtasks.

**Three-stage architecture:** MPRNet consists of three cascaded subnetworks, each handling coarse-to-fine restoration:

```
Degraded input y
    ↓
[Stage 1: shallow feature extraction + U-Net encoder]
    ↓ coarse restoration y1 + intermediate features F1
[Stage 2: feature fusion + further restoration]
    ↓ refined restoration y2 + features F2
[Stage 3: high-frequency detail refinement]
    ↓
Final output x̂
```

**CSFF (Cross-Stage Feature Fusion):** Intermediate features from each stage are passed not only to the next stage but, via learnable projection layers, to all subsequent stages at matching resolution levels:

$$F^{(s+1)}_{l} = F^{(s+1, \text{local})}_{l} + \text{CSFF}\!\left(F^{(1)}_{l}, F^{(2)}_{l}, \ldots, F^{(s)}_{l}\right)$$

CSFF ensures that large-scale structural features extracted in early stages continuously inform later refinement stages, avoiding information degradation across stage boundaries.

**SAM (Supervised Attention Module):** Each stage includes a SAM that generates a spatial attention map from the current intermediate restoration result, guiding the next stage to focus on regions not yet fully restored:

$$M^{(s)} = \sigma\!\left(W_m \cdot y^{(s)}\right), \quad F^{(s+1)}_{\text{in}} = M^{(s)} \odot F^{(s)}$$

SAM supervision comes from independent reconstruction losses at each stage — all three stages are trained with full supervision, not only the final output.

**Training loss (multi-supervised):**

$$\mathcal{L}_{total} = \sum_{s=1}^{3} \lambda_s \mathcal{L}_{char}\!\left(y^{(s)}, x_0\right) + \mathcal{L}_{SSIM}\!\left(y^{(3)}, x_0\right)$$

where $\mathcal{L}_{char}$ is the Charbonnier loss (smooth approximation of L1), with stage weights $\lambda_1:\lambda_2:\lambda_3 = 0.4:0.3:0.3$.

**Benchmark results:**

| Task | Dataset | MPRNet PSNR |
|------|---------|------------|
| Image deraining | Rain100L | 42.26 dB |
| Image deblurring | GoPro | 32.66 dB |
| Real noise denoising | SIDD | 42.13 dB |

---

### 2.4 Comprehensive Performance Comparison

**SIDD validation + DND benchmark (SIDD numbers are validation set):**

| Method | SIDD PSNR↑ (val) | SIDD SSIM↑ | DND PSNR↑ | Params | Speed (512²) |
|--------|------------------|-----------|-----------|--------|-------------|
| MPRNet | 42.13 | 0.961 | 39.71 | 20.1M | ~0.5s |
| Restormer | 42.06 **[5]** | 0.956 | 40.99 **[5]** | 26.1M | ~0.9s |
| NAFNet-32 | 42.61 **[4]** | 0.964 | 40.27 **[4]** | 17.1M | ~0.4s |
| NAFNet-64 | **43.14** **[4]** | **0.968** | **41.32** **[4]** | 67.9M | ~1.6s |
| MambaIR | 42.75 **[15]** | 0.965 | — | 26.7M | ~0.8s |

**Rain100L deraining comparison:**

| Method | Rain100L PSNR↑ | Rain100L SSIM↑ |
|--------|---------------|---------------|
| MPRNet | 42.26 | 0.981 |
| Restormer | **42.81** **[5]** | **0.984** |
| NAFNet-32 | 39.43 **[4]** | 0.972 |

> **Engineering recommendations:**
> - **Edge NPU deployment (< 15ms, denoising/deblurring):** Start with NAFNet-32. INT8-quantized on Snapdragon 8 Gen2 it fits comfortably in budget. Restormer's transposed attention requires operator compatibility verification on Qualcomm QNN/SNPE; do not use it as the first candidate.
> - **Offline processing (< 500ms post-capture):** Restormer is the preferred choice for deraining/dehazing/low-light scenes — global attention is more effective for structural degradations. NAFNet trails Restormer by ~3 dB on Rain100L; do not extrapolate NAFNet's denoising numbers to deraining tasks.
> - **Multi-task requirements (one model for multiple degradations):** MPRNet's multi-stage design generalizes more consistently across tasks than single-stage models, but 20M parameters is a constraint at the edge — consider All-in-One approaches (see §3).

---

### 2.5 Loss Function Comparison

| Loss | Mathematical Form | Best Task | Weakness | Typical Weight |
|------|------------------|-----------|----------|----------------|
| L2 (MSE) | $\frac{1}{N}\sum(y-\hat{y})^2$ | Gaussian denoising (precise noise model) | Multi-solution averaging → blurry output | Base loss (not recommended alone) |
| L1 (MAE) | $\frac{1}{N}\sum\|y-\hat{y}\|$ | Denoising, deraining, deblurring (general) | Non-differentiable at 0 | 1.0 (standalone or base) |
| Charbonnier | $\sqrt{(y-\hat{y})^2+\epsilon^2}$ | Deblurring, deraining (heavy degradation) | Needs tuning of $\epsilon$ | 1.0 (L1 replacement) |
| SSIM | $1 - \text{SSIM}(y,\hat{y})$ | Auxiliary loss for structure/edge preservation | Alone can introduce block texture | 0.05–0.1 (auxiliary) |
| LPIPS | $\sum_l\|\phi_l(y)-\phi_l(\hat{y})\|^2$ | Perceptual quality (super-res, deblur) | Slow training; may introduce hallucination | 0.01–0.05 (auxiliary) |
| FFT frequency | $\|\mathcal{F}(y)-\mathcal{F}(\hat{y})\|^1$ | Deblurring (frequency-domain fidelity) | Phase-insensitive | 0.01–0.1 (auxiliary) |

**Recommended default combination (applicable to most ISP restoration tasks):**

$$\mathcal{L} = \mathcal{L}_{Charb} + 0.05 \cdot \mathcal{L}_{SSIM} + 0.01 \cdot \mathcal{L}_{LPIPS}$$

When the task prioritizes perceptual quality (portrait super-resolution, night bokeh), raise $\mathcal{L}_{LPIPS}$ weight to 0.05. When fidelity is paramount (scientific or medical imaging), drop LPIPS entirely and use only Charbonnier + SSIM.

---

## §3 All-in-One Unified Image Restoration (2023–2024)

The engineering motivation for All-in-One is straightforward: running three separate models (denoising, deraining, dehazing) on a phone at 17–26M parameters each is impractical for memory. The more concrete driver is that real-world degradations are often mixed — a rainy-day photo simultaneously has noise and rain streaks, and managing the inference order and parameter tuning for two separate networks is operationally expensive.

### AirNet (CVPR 2022 — All-In-One Image Restoration Network)

**Core idea:** Contrastive Degradation Representation Learning (CDRL, 对比退化表示学习). **[11]**

AirNet uses a two-stage training approach:
1. **Degradation encoder (DADF):** Uses contrastive learning to pull embeddings of same-type degraded images together and push different degradation types apart, automatically learning discriminative degradation representations.
2. **Restoration network:** Conditioned on the degradation embedding, adaptively adjusts the restoration strategy.

**Degradation-aware loss:**
$$\mathcal{L}_{CDRL} = -\log \frac{\exp(\text{sim}(z_i, z_j^+)/\tau)}{\sum_{k} \exp(\text{sim}(z_i, z_k)/\tau)}$$

where $z_i, z_j^+$ are two augmented samples from the same degradation type, $\tau$ is the temperature coefficient, and the denominator sums over all samples (positive and negative).

**Results:** On three tasks — denoising (SIDD), deraining (Rain100L), and dehazing (RESIDE) — the single unified model trails dedicated specialist models by only 0.1–0.3 dB PSNR.

### PromptIR (NeurIPS 2023 — Prompting for All-in-One Image Restoration)

**Core idea:** Introduces learnable prompt tokens (提示向量) as soft degradation-type conditions, requiring no explicit degradation type label at inference. **[12]**

**Prompt generation:**
$$P = \text{PromptGen}(F_{input}) \in \mathbb{R}^{N_p \times d}$$

$N_p=5$ prompt tokens are generated dynamically from the input image's own features (rather than fixed type embeddings), enabling the model to handle mixed degradations (e.g., simultaneous denoising and deraining).

**Prompt injection:** Prompt tokens are concatenated into the Key/Value sequence at Transformer attention layers:

$$\text{Attn}(Q, [K; K_P], [V; V_P])$$

where $K_P, V_P$ are prompt Keys/Values projected from $P$.

**Five-task SOTA (single model):**

| Degradation | Dataset | PromptIR PSNR↑ | Specialist SOTA |
|-------------|---------|---------------|----------------|
| Denoising (σ=15) | CBSD68 | 34.17 | 34.26 (DnCNN) |
| Denoising (σ=25) | CBSD68 | 31.31 | 31.73 (DnCNN) |
| Deraining | Rain100L | 42.22 | 42.81 (Restormer) |
| Dehazing | SOTS | 31.31 | 30.23 (DehazeFormer) |
| Deblurring | GoPro | 33.06 | 33.69 (NAFNet) |

PromptIR surpasses the specialist model on dehazing, demonstrating that multi-task joint training can yield cross-task knowledge transfer.

### InstructIR (ECCV 2024 — Natural Language Instruction-Guided Restoration)

**Core idea:** InstructIR (Conde et al., ECCV 2024) is the first method to bring **natural language instructions** into All-in-One image restoration **[14]**. Users (or the system) can describe restoration intent in human language, and the model adjusts processing strength and strategy accordingly.

The precision of **"remove mild noise"** vs. **"remove heavy noise"** is not achievable in AirNet or PromptIR — those methods receive implicit degradation embeddings, not human-interpretable semantic instructions.

**Instruction-guided mechanism:**

```
Input: degraded image + natural language instruction
       e.g.: "remove heavy noise and slight blur from this photo"

Language encoder (lightweight Sentence Transformer)
         ↓ text embedding t ∈ R^d

Dynamic filter generation (MetaFormer-style):
t → generate token-wise modulation parameters {γ, β}
    injected into image restoration backbone

Image restoration backbone (U-Net + NAFBlock)
         ↓ modulated restoration output
```

The language encoder and restoration backbone are jointly trained so the model genuinely understands instruction semantics rather than merely classifying inputs.

**Performance (five-task PSNR vs. PromptIR):**

| Degradation | Dataset | InstructIR PSNR | PromptIR PSNR |
|-------------|---------|----------------|--------------|
| Denoising (σ=15) | CBSD68 | 34.15 | 34.17 |
| Denoising (σ=25) | CBSD68 | 31.52 | 31.31 |
| Deraining | Rain100L | 42.01 | 42.22 |
| Dehazing | SOTS | 33.35 | 31.31 |
| Deblurring | GoPro | 32.65 | 33.06 |

InstructIR outperforms PromptIR on dehazing and medium noise; overall PSNR is comparable. The advantage is **controllability** — for the same scene, users can switch between conservative and aggressive restoration modes via instruction without retraining. Code: https://github.com/mv-lab/InstructIR

**Direct value for ISP tuning:** Natural language control of ISP parameters is a future direction. The InstructIR framework can be extended to "semanticize ISP parameters" — engineers control denoising strength with high-level instructions like "enhance night clarity while preserving film grain" rather than manually adjusting NR filter parameters.

### MambaIR (ECCV 2024 — State-Space Model for Image Restoration)

**Background:** Mamba (Gu & Dao, NeurIPS 2023) is an efficient hardware implementation of structured state-space sequence models (S4/SSM), modeling long-range sequence dependencies in linear complexity $O(N)$ while approaching Transformer performance on NLP tasks. MambaIR (Guo et al., ECCV 2024) brings Mamba SSM to image restoration. **[15]**

**Core innovations:** Direct visual adaptation of Mamba has two problems: (1) unidirectional scanning destroys 2D spatial symmetry; (2) lack of local feature enhancement (Transformer has local convolutions; vanilla Mamba does not). MambaIR introduces two key fixes:

1. **Local Enhancement Block:** A depth-wise separable convolution runs in parallel with the SSM module, supplementing local high-frequency feature perception (noise, edge sharpness) and compensating for SSM's relative weakness in local awareness despite strong long-range dependency modeling.
2. **Channel Attention:** Reuses NAFNet's SCAM design to improve channel-wise feature interaction at low overhead.

**Advantage:** Compared to Restormer's transposed attention at $O(HW \cdot C^2)$, MambaIR's SSM scan complexity is $O(HW \cdot d)$ ($d$ = state dimension), with lower memory overhead at ultra-high resolution (8MP+). SIDD validation denoising PSNR:

| Method | SIDD PSNR (val) | Params | Year |
|--------|-----------------|--------|------|
| NAFNet-32 | 42.61 dB | 17.1M | 2022 |
| Restormer | 42.06 dB | 26.1M | 2022 |
| **MambaIR** | **42.75 dB** **[15]** | 26.7M | 2024 |

MambaIR achieves 42.75 dB on SIDD validation, surpassing both NAFNet and Restormer. On GoPro deblurring it achieves 33.80 dB, above NAFNet-32's 33.69 dB. Code: https://github.com/csguoh/MambaIR

### RAW Domain vs. YUV Domain End-to-End Restoration

| Comparison | RAW-domain E2E | YUV/sRGB-domain E2E |
|-----------|--------------|-------------------|
| **Input information completeness** | Full sensor information, no irreversible ISP-induced loss | ISP has introduced nonlinearities (Gamma, tone mapping); some shadow detail lost |
| **Noise model** | Poisson-Gaussian mixture: $\sigma^2(I) = k_1 I + k_2$, physically well-defined | sRGB noise is hard to model simply (nonlinearly transformed by Gamma/tone mapping) |
| **Cross-sensor generalization** | Poor — noise parameters $(k_1, k_2)$ vary per sensor; per-device calibration required | Good — sRGB output is relatively standardized |
| **Compute cost** | RAW is 4-channel (RGGB) or more (RGBW), resolution ×4 | YUV 444/420, standard resolution |
| **Representative work** | SID (CVPR 2018), CycleISP (CVPR 2020), SeeInTheDark | NAFNet, Restormer, MPRNet |
| **Production deployment** | Flagship devices (RAW stream access), tightly coupled with hardware ISP | Mid/low-end devices (sRGB only), plug-in AI post-processing |
| **Best scenarios** | Extremely dark / ultra-short exposure / high ISO (greatest SNR benefit) | General quality improvement under normal lighting |

**Noise model note (RAW domain):**

Real sensor noise follows a Poisson-Gaussian mixture (signal-dependent Poisson + independent Gaussian), not AWGN (additive white Gaussian noise):

$$n = \underbrace{n_p}_{\text{Poisson, variance} \propto \text{signal}} + \underbrace{n_g}_{\text{Gaussian read noise, fixed variance}}$$

Conditional variance model: $\sigma^2(x) = k_1 x + k_2$, where $k_1$ (shot noise factor) and $k_2$ (read noise variance) are obtained from sensor calibration. Using AWGN as a proxy for Poisson-Gaussian leads to over-denoising at low ISO (high-SNR regions misidentified as noise) and under-denoising at high ISO (structural noise persists in low-SNR regions).

---

## §4 标定 (Calibration)

### Training Data Collection: Synthetic vs. Real Noise

**Synthetic noise** training uses a noise model to generate noisy training images from clean sources. The standard model is heteroscedastic Gaussian (signal-dependent variance):

```
σ^2(I) = σ_shot^2 * I + σ_read^2
```

Synthetic training is cheap (unlimited training data from any clean image) and allows precise control of noise level. The disadvantage is the domain gap: the simplified noise model does not capture fixed-pattern noise, banding, or cross-channel correlations present in real sensors.

**Real noise** training (using SIDD or similar datasets) closes the domain gap but is limited by dataset size and sensor diversity. Most production DL denoising systems use a combination: pre-train on synthetic noise for broad coverage, then fine-tune on real sensor data.

### Test-Time Adaptation

When deploying a model on a new sensor, test-time adaptation (fine-tuning on a small calibration dataset from the target sensor) can recover 0.5-2 dB PSNR compared to direct transfer. A calibration protocol:

1. Capture a static test scene at ISO 100, 400, 800, 1600, 3200 (5 shots each ISO).
2. Compute per-ISO noise level from uniform regions.
3. Fine-tune for 1000-5000 iterations using synthesized noise matched to the measured parameters.

---

## §5 调参 (Tuning)

### Model Depth vs. Receptive Field vs. Latency

U-Net depth (number of encoder levels) determines the receptive field: a 3-level U-Net with 3x3 convolutions has a receptive field of roughly 64 pixels. For denoising, this is sufficient for most noise patterns. For tasks requiring global context (HDR reconstruction, lens shading correction), 4-5 levels are needed.

Each additional encoder level approximately doubles the receptive field but:
- Doubles the number of parameter-heavy bottleneck convolutions
- Increases latency roughly linearly
- Increases the minimum input size (a 5-level U-Net requires inputs divisible by 32)

The practical latency budget on mobile NPU constrains network depth to 2-3 levels for real-time and 3-4 levels for capture-time quality.

### Loss Weight λ Selection

The λ weights in the combined loss should be selected to balance gradient magnitudes across terms. A common workflow:

1. Train with L1 only as baseline. Record PSNR and visual quality.
2. Add SSIM loss with λ_ssim=0.1. Verify PSNR does not drop by more than 0.1 dB; if it does, reduce λ_ssim.
3. Add VGG loss with λ_vgg=0.01. Inspect outputs for hallucination; if present, reduce λ_vgg.
4. Validate on the human preference study (MOS) to confirm λ values produce user-preferred outputs.

The interaction between SSIM and VGG losses can be non-linear. Joint grid search with 3-5 values per weight is advisable.

---

## §6 Artifacts

### Grid Artifact: Transposed Convolution Checkerboard

The checkerboard artifact arises from uneven overlap in transposed convolution. It manifests as a periodic grid pattern of alternating bright/dark pixels, most visible in smooth regions and flat sky areas.

**Fix**: Replace all transposed convolutions with bilinear upsampling + regular Conv2D. The output quality is equivalent or better, and the artifact disappears completely.

Detection: Compute FFT of the output on a smooth region. Checkerboard artifact produces peaks at Nyquist frequency (±N/2, ±N/2) in the 2D spectrum.

### Color Shift: Wrong Normalization

If training data normalization is inconsistent (e.g., training normalizes inputs to [0,1] but inference inputs are in [0,255]), the network applies the correct operation but in the wrong value range, causing a global color shift or incorrect brightness.

This is a deployment bug rather than a model quality issue, but it can be difficult to diagnose because the output image is not obviously wrong—it just has a color cast.

**Fix**: Normalize inputs to [-1, 1] or [0, 1] consistently. Hardcode normalization constants in the inference wrapper and include a unit test comparing inference wrapper output against training-mode output on a fixed test input.

### Blocking: Patch Boundary Artifact

Models trained on small patches may produce visible block boundaries when applied to full images via tiling. The artifact arises because the model's receptive field does not extend past the patch boundary, so pixels near the edge are processed with insufficient context.

**Fix**: Use overlapping tiles with a 16-32 pixel overlap region and linearly blend the overlap region. Alternatively, train with random crop offsets to expose the model to positions near the image edge.

---

## §7 评测 (Evaluation)

### PSNR/SSIM/LPIPS on Standard Benchmarks

For Gaussian denoising (sigma=25, grayscale):

| Model | BSD68 PSNR (dB) | Params | Year |
|-------|-----------------|--------|------|
| BM3D | 31.07 | — | 2007 |
| DnCNN | 31.73 | 0.56M | 2017 |
| FFDNet | 31.63 | 0.49M | 2018 |
| DRUNet | 32.47 | 32M | 2021 |
| NAFNet | 33.69 | 17M | 2022 |
| Restormer | 33.79 | 26M | 2022 |

For real noise denoising on SIDD validation (color, PSNR/SSIM):

| Model | PSNR (dB) | SSIM | Year |
|-------|-----------|------|------|
| CBM3D | 39.59 | 0.959 | 2012 |
| DnCNN-B | 38.60 | 0.943 | 2017 |
| RIDNet | 41.99 | 0.971 | 2019 |
| MPRNet | 42.13 | 0.961 | 2021 |
| NAFNet | 42.61 | 0.964 | 2022 |
| Restormer | 42.06 | 0.956 | 2022 |

Note: NAFNet achieves state-of-the-art performance with a simplified architecture that removes all non-linear activation functions in the main branch, replacing them with a gating mechanism. This simplification actually improves performance while reducing computational cost.

### LPIPS for Perceptual Quality

PSNR and SSIM measure distortion but do not capture perceptual quality well for highly degraded or restored images. LPIPS is increasingly reported alongside PSNR in ISP papers. For reference:
- Models optimized for PSNR (L2 training) typically have low LPIPS (better perceptual) only relative to L2-trained baselines.
- Models optimized with GAN loss have lowest LPIPS but highest hallucination risk.

### 5.X NTIRE/AIM Competitions: Denoising and Deblurring Track Technology Evolution

#### Image Denoising Track (2023–2025)

NTIRE features both Gaussian denoising and real-noise denoising tracks annually:

| Year | Track | Champion Method | SIDD Benchmark PSNR |
|------|-------|----------------|---------------------|
| 2023 | sRGB real denoising | Restormer ensemble + data augmentation | 40.0 dB+ |
| 2024 | Blind Gaussian denoising | NAFNet-L + frequency-domain loss | 31.7 dB (σ=50) |
| 2025 | Real-scene denoising | MambaIR variants + diffusion refinement | Pending final results |

**Restormer (CVPR 2022 — perennial competition champion):**

Restormer's core innovation is **Transposed Attention** — computing attention across the channel dimension instead of spatial dimension, reducing Transformer compute from O(H²W²) to O(C²):

$$\text{Attn}(Q, K, V) = V \cdot \text{Softmax}(K^T Q / \sqrt{d})$$

where Q, K, V ∈ ℝ^(C×HW) and matrix multiplication unfolds in the channel dimension. This allows Restormer to process 4MP+ high-resolution images while SwinIR hits memory bottlenecks above 2MP.

Competition results:
- SIDD real denoising: PSNR 40.02 dB (Restormer) vs. DnCNN 31.73 dB
- Processing 1080p image: Restormer < 1s (A100), SwinIR > 3s

Code: https://github.com/swz30/Restormer

#### Image Deblurring Track (2023–2025)

**NTIRE motion deblurring track** has been NAFNet's territory:

| Method | GoPro PSNR | Key Feature |
|--------|-----------|-------------|
| DeepDeblur | 29.23 dB | CNN pioneer; slow |
| MPRNet | 32.66 dB | Multi-stage progressive restoration |
| Restormer | 32.92 dB | Channel attention Transformer |
| **NAFNet** | **33.69 dB** | No nonlinear activations; SOTA |
| NAFNet + TTA×8 | Competition best | Geometric self-ensemble |

**NAFNet (ECCV 2022)** — simplicity is the source of its competition advantage:

```python
class NAFBlock(nn.Module):
    def forward(self, x):
        x = self.norm(x)
        # Replace GELU: SimpleGate
        x1, x2 = self.conv(x).chunk(2, dim=1)
        x = x1 * x2  # Element-wise multiplication = gate
        x = self.channel_attn(x)  # Simple channel attention
        return x + shortcut
```

No GELU/ReLU enables more stable training: larger batch sizes, faster convergence; the final PSNR exceeds more complex Transformers.

Code: https://github.com/megvii-research/NAFNet

#### MIPI Competitions: Most Directly ISP-Relevant

**MIPI (Mobile Intelligent Photography & Imaging)** is the competition series most directly relevant to this handbook's Part 2:

| Year/Track | Champion Approach | ISP Takeaway |
|------------|------------------|--------------|
| MIPI 2023 Under-Display Camera (UDC) | MPRNet variants; frequency-domain enhancement | Fixed-pattern UDC blur compensatable via FFT |
| MIPI 2024 RGBW remosaicing | Joint demosaic+denoise network | RAW-domain joint processing outperforms sequential by 0.5–1.0 dB |
| MIPI 2024 Night flare removal | U-Net + frequency filtering | FFT separates low-frequency circular scatter (flare component) |

**RGBW remosaicing track** directly corresponds to mainstream smartphone sensor solutions (Samsung ISOCELL RGBW series): competition results show that joint demosaic+denoise in the RAW domain (rather than sequential processing) consistently yields 0.5–1.0 dB improvement — consistent with Chapter 19's (demosaicing) conclusions.

#### Restormer vs. NAFNet: Capability Boundary Analysis

For ISP engineers choosing between architectures:

| Comparison Dimension | Restormer | NAFNet |
|---------------------|-----------|--------|
| **Best suited for** | Denoising, deraining, dehazing (global statistics) | Deblurring, denoising (local fine structure) |
| **High-resolution support** | Excellent (transposed attention O(C²)) | Excellent (no global attention, pure convolution) |
| **Training stability** | Moderate | Extremely stable (no nonlinear activations) |
| **PSNR ceiling** | Denoising SOTA | Deblurring SOTA |
| **Edge deployment** | Watch attention operator compatibility | More friendly (standard convolution ops) |
| **Status in 2025** | Partially surpassed by MambaIR | Still one of the best choices for edge deblurring |

---

## §8 代码 (Code)

See `ch_e2e_restoration_code.ipynb` in this directory for:
- Synthetic noisy patch generation
- Minimal 2-level U-Net implementation (numpy fallback or torch)
- Training loop demonstration (5 epochs, quick demo)
- Loss curve visualization and visual comparison of noisy/denoised/GT
- PSNR before/after and published benchmark comparison table
- Exercises

---

## §9 Glossary

**U-Net (encoder-decoder + skip connections)**
Proposed by Ronneberger et al. (MICCAI 2015) **[1]** for biomedical image segmentation; now the dominant backbone for ISP image restoration. Core structure: encoder progressively downsamples (resolution /2, channels ×2) → bottleneck extracts global degradation pattern → decoder progressively upsamples → skip connections route high-resolution encoder features directly to the decoder, bypassing the bottleneck to recover detail. Removing skip connections causes 1–3 dB PSNR loss.

**Residual Learning**
Training paradigm from DnCNN **[2]**: the network learns the noise residual rather than the full clean image; clean output = input − predicted residual. Advantage: residual signal has far smaller dynamic range than the original image, leading to more stable gradients and faster convergence. Now the standard training strategy for DL-ISP denoising.

**Noise2Noise Training**
Lehtinen et al. (ICML 2018) **[6]** proved that minimizing expected L2 loss over noisy-noisy pairs (two independent noisy observations of the same scene) is equivalent to minimizing against the clean target. Mathematical basis: $\mathbb{E}_y[\|f(x)-y\|^2]=\|f(x)-\mathbb{E}[y]\|^2+\text{const}$; with zero-mean noise, $\mathbb{E}[y]=y_\text{clean}$. Burst pairs and video frames can both be used in practice. **Limitation**: requires zero-mean noise independent across observations; fixed-pattern noise and JPEG compression artifacts cannot be handled.

**L1 vs. L2 Loss (statistical perspective)**
L1 (MAE) corresponds to Laplacian noise MLE; L2 (MSE) corresponds to Gaussian noise MLE. L2's quadratic penalty on large errors drives the network toward the conditional mean (averaging over multiple solutions → blurry output). L1's linear penalty is closer to the conditional median, producing sharper outputs but potentially amplifying noise. **Practical recommendation**: L1 as the base loss, combined with SSIM (λ=0.1) and VGG perceptual loss (λ=0.01).

**Restormer (Transposed Attention)**
Proposed by Zamir et al. (CVPR 2022) **[5]**. Reshapes Q/K/V to $\mathbb{R}^{HW \times C}$, computes $K^T Q$ as a $C \times C$ attention matrix, avoiding the standard Transformer's $O((HW)^2)$ spatial complexity, enabling efficient processing of 4MP+ images. SIDD denoising PSNR = 42.06 dB; a perennial competition winner.

**NAFNet (Simple Baseline)**
Proposed by Chen et al. (ECCV 2022) **[4]**. Core: removes all conventional nonlinear activations (ReLU/GELU) and replaces complex attention with SimpleGate ($X = X_1 \cdot X_2$, two feature streams multiplied element-wise). SIDD validation PSNR = 42.61 dB; GoPro deblurring PSNR = 33.69 dB — both surpassing more complex Transformer architectures. Preferred model for edge deployment.

**Checkerboard Artifacts**
Periodic grid pattern of alternating bright/dark pixels caused by uneven kernel overlap in transposed convolution (deconvolution) upsampling. Most visible in smooth regions and sky; produces peaks at Nyquist frequency (±N/2) in 2D FFT. **Standard fix**: replace all transposed convolutions with bilinear upsampling + regular Conv2D.

**Test-Time Adaptation (TTA)**
When transferring a pre-trained model to a new sensor, fine-tuning for 1000–5000 iterations on a small calibration dataset from the target sensor recovers 0.5–2 dB PSNR over direct transfer. Standard protocol: capture 5 shots of a static scene at ISO 100/400/800/1600/3200, then fine-tune with synthesized noise matched to the measured parameters.

**AirNet / PromptIR / InstructIR (All-in-One)**
A family of unified restoration models that handle multiple degradation types with a single network. AirNet **[11]** uses contrastive learning to build degradation-type embeddings. PromptIR **[12]** generates learnable prompt tokens from input features to condition the restoration. InstructIR **[14]** accepts natural language instructions, enabling semantic-level control over restoration strength — directly applicable to ISP parameter tuning via human-readable prompts.

**MambaIR (SSM-based Restoration)**
Applies the Mamba structured state-space model (SSM) to image restoration **[15]**, achieving linear $O(N)$ sequence complexity. Addresses two visual adaptation issues of vanilla Mamba — directional scan symmetry and local feature enhancement — with a parallel depth-wise convolution branch. SIDD validation PSNR = 42.75 dB (surpassing NAFNet and Restormer); lower memory overhead than Restormer at 8MP+ resolution.

---

## References

[1] Ronneberger et al., "U-Net: Convolutional Networks for Biomedical Image Segmentation", *MICCAI*, 2015.

[2] Zhang et al., "Beyond a Gaussian Denoiser: Residual Learning of Deep CNN for Image Denoising", *IEEE TIP*, 2017.

[3] Zhang et al., "FFDNet: Toward a Fast and Flexible Solution for CNN-Based Image Denoising", *IEEE TIP*, 2018.

[4] Chen et al., "Simple Baselines for Image Restoration", *ECCV*, 2022.

[5] Zamir et al., "Restormer: Efficient Transformer for High-Resolution Image Restoration", *CVPR*, 2022.

[6] Lehtinen et al., "Noise2Noise: Learning Image Restoration without Clean Data", *ICML*, 2018.

[7] Krull et al., "Noise2Void — Learning Denoising from Single Noisy Images", *CVPR*, 2019.

[8] Zhang et al., "The Unreasonable Effectiveness of Deep Features as a Perceptual Metric", *CVPR*, 2018.

[9] Abdelhamed et al., "A High-Quality Denoising Dataset for Smartphone Cameras", *CVPR*, 2018.

[10] Plötz et al., "Benchmarking Denoising Algorithms with Real Photographs", *CVPR*, 2017.

[11] Li et al., "All-In-One Image Restoration for Unknown Degradations", *CVPR*, 2022.

[12] Potlapalli et al., "PromptIR: Prompting for All-in-One Image Restoration", *NeurIPS*, 2023.

[13] Zhang et al., "Plug-and-Play Image Restoration with Deep Denoiser Prior", *IEEE TPAMI*, 2022.

[14] Conde et al., "InstructIR: High-Quality Image Restoration Following Human Instructions", *ECCV*, 2024.

[15] Guo et al., "MambaIR: A Simple Baseline for Image Restoration with State-Space Model", *ECCV*, 2024.
