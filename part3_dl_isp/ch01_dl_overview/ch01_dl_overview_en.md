# Part 3, Chapter 01: Deep Learning ISP — Role-Based Overview

> **Pipeline position:** Bridge between Part 2 (traditional) and DL modules
> **Prerequisites:** Chapter 1 (Pipeline Overview), Chapter 20 (Denoising)
> **Reader path:** DL Researcher (core), Algorithm Engineer (strategic overview)

---

## §1 原理 (Theory)

### Why Deep Learning for ISP?

Traditional ISP pipelines are assembled from a sequence of hand-crafted modules, each designed around a specific physical or statistical prior. Demosaicing relies on local color correlation; denoising relies on noise statistics and patch self-similarity; tone mapping relies on luminance histograms and display characteristics. These priors are carefully engineered by domain experts and work well under the conditions they were designed for.

The fundamental limitation of hand-crafted priors is that they are **fixed at design time**. When a new sensor arrives with a different noise profile, or when a scene contains unusual texture statistics, the manually-tuned parameters degrade gracefully but do not adapt. Engineering effort is required to re-tune every module.

Deep learning approaches instead **learn the prior from data**. Given a sufficient dataset of (input, desired output) pairs, a neural network can discover the statistical regularities in images that are relevant to each ISP task. This yields several concrete advantages:

1. **Automatic adaptation**: A model trained on data from a specific sensor captures that sensor's particular noise distribution, spectral response, and demosaicing patterns without manual analysis.
2. **Cross-module optimization**: End-to-end training allows gradients to flow through multiple processing stages simultaneously. The demosaicing step can be jointly optimized with denoising, eliminating the mismatch between sub-optimal intermediate representations.
3. **Capacity scaling**: Model performance scales with dataset size and compute in a predictable way. Collecting more paired data directly improves results without the need for new algorithm design.
4. **Perceptual quality**: DL models can be trained with perceptual loss functions that align with human visual preference rather than pixel-level MSE, a dimension that is very difficult to capture with hand-crafted approaches.

### DL Deployment Mode Taxonomy

A common mischaracterization is that DL ISP means replacing the entire traditional pipeline with a neural network. In practice, three deployment patterns are observed:

**1. Single-Module Drop-in Replacement**
A DL model substitutes one stage while all surrounding stages remain traditional. Example: replacing the BM3D denoiser with a DnCNN or NAFNet while keeping the demosaicing, AWB, and tone mapping stages traditional. This is the lowest-risk approach for production deployment because it limits the scope of regression testing.

**2. Joint Module (Multi-Task Network)**
A single network handles two or more adjacent pipeline stages simultaneously. Joint demosaic-and-denoise CNNs are the canonical example: because demosaicing introduces interpolation artifacts that look similar to high-frequency noise, performing both operations together is substantially more accurate than a sequential pipeline. The network can learn to distinguish genuine texture from Bayer interpolation artifacts.

**3. Full Pipeline Replacement**
A network such as PyNET or CycleISP takes RAW sensor data as input and produces an sRGB image in a single forward pass. This maximizes joint optimization opportunity but creates the highest deployment risk (full regression testing, latency budget for the entire ISP on mobile NPU, and sensitivity to domain shift).

**Hybrid architectures dominate production.** The most widely deployed configuration as of 2024 is a traditional skeleton pipeline (linearization, demosaic, AWB, basic tone mapping) augmented with DL components for the quality-sensitive steps (denoising, sharpness enhancement, HDR reconstruction). This allows the device to fall back to the traditional pipeline if the NPU is unavailable or overloaded, while using DL for quality improvement when resources permit.

### Module-Level DL Categories

| ISP Stage | Traditional | DL Replacement/Augment | Deployment Status |
|-----------|-------------|------------------------|-------------------|
| Demosaic | AHD, LMMSE | Joint Demosaic+Denoise CNN | Production |
| Denoising | BM3D, NLM | DnCNN, FFDNet, NAFNet | Production |
| Super-Resolution | Bicubic, Lanczos | ESRGAN, Real-ESRGAN | Consumer |
| Auto White Balance | Gray World, PCA | Deep WB (Hu 2021) | Research/Production |
| Tone Mapping | Reinhard, Filmic | HDRNet (Gharbi 2017) | Production |
| Sharpening | Unsharp Mask | IRCNN, deconvolution CNN | Partial deployment |
| Noise Estimation | Variance analysis | Blind noise CNN | Research |
| Full Pipeline | Traditional chain | PyNET, CycleISP | Research |

### Key DL Concepts for ISP

**Residual Learning.** Instead of learning the mapping from noisy image to clean image directly, networks learn the *residual* (noise or degradation component). The DnCNN paper by Zhang et al. (2017) showed that this dramatically accelerates convergence and improves performance, because the residual signal occupies a much smaller value range than the full image.

**Attention Mechanisms.** Channel attention (SE-Net style) and spatial attention (CBAM) allow the network to dynamically weight different feature channels or spatial regions. In ISP, channel attention is particularly valuable because different color channels may have different noise levels and should receive different processing.

**U-Net Architecture.** The encoder-decoder architecture with skip connections is the most widely used backbone for ISP tasks. The encoder compresses spatial resolution while increasing channel depth to capture long-range context. The decoder restores spatial resolution. Skip connections from encoder to decoder preserve fine-grained spatial detail that would otherwise be lost. This architecture is used in Restormer, NAFNet, and most recent denoising/restoration models.

**Loss Functions.** The choice of loss function determines what "good" means during training:
- **L2 (MSE)**: Minimizes mean squared error; produces over-smoothed outputs (averages over uncertainty).
- **L1 (MAE)**: Produces sharper results than L2; more robust to outliers.
- **SSIM loss**: Penalizes structural dissimilarity; better preserves edges and textures.
- **Perceptual loss**: Computes feature-level distance using a pretrained VGG network; produces visually sharp results but can introduce hallucinated textures.
- **GAN loss**: Discriminator penalizes blurriness; produces the sharpest outputs but with the highest risk of hallucination.

### Perceptual vs. PSNR Trade-Off

One of the most important insights in DL ISP (formalized by Blau and Michaeli, 2018) is that **distortion metrics and perceptual quality metrics are fundamentally at odds**. A model trained to maximize PSNR (minimize MSE) will produce outputs that are metrically close to the ground truth but visually soft. A model trained with perceptual or GAN losses will produce visually crisp outputs that score lower on PSNR.

This creates a practical dilemma for ISP deployment:

- Automotive and medical imaging applications require **high fidelity** (low distortion): use L1/L2 training.
- Consumer photography applications require **high perceptual quality**: use perceptual/GAN training.
- General-purpose ISP must choose a point on this Pareto frontier.

The LPIPS metric (Zhang et al., 2018) provides a learned perceptual similarity measure that correlates better with human judgment than PSNR/SSIM and is increasingly used alongside them in ISP evaluation.

### Restormer: Transposed Attention for High-Resolution Restoration

Traditional CNNs are constrained by local receptive fields and cannot capture long-range dependencies across a full image. Standard Vision Transformer self-attention has O((HW)²) complexity — for a 4MP image (2000×2000), this requires roughly 10¹³ operations, which is entirely infeasible.

Restormer (Zamir et al., CVPR 2022) solves this with **Transposed Attention**, which shifts the attention dimension from spatial to channel:

$$Q, K, V \in \mathbb{R}^{C \times HW}, \quad \text{Attn} = V \cdot \text{Softmax}\!\left(\frac{K^T Q}{\sqrt{d_C}}\right)$$

The attention matrix is now C×C (only ~16,384 elements at C=128) rather than (HW)×(HW) (~4×10¹² elements at 4MP). This makes full-resolution transformer-based image restoration feasible. Restormer achieves state-of-the-art results on denoising, deblurring, and deraining benchmarks, surpassing prior CNN methods.

### NAFNet: SimpleGate and Nonlinear-Free Design

NAFNet (Chen et al., ECCV 2022) removes all nonlinear activations (ReLU, GELU) from the U-Net backbone and replaces complex attention modules with **SimpleGate**:

$$\text{SimpleGate}(X_1, X_2) = X_1 \odot X_2, \quad X_1, X_2 = \text{split}(\text{Conv}(F), \text{dim=ch})$$

The two feature splits are element-wise multiplied directly, with no sigmoid or softmax. Despite its simplicity, NAFNet-64 achieves PSNR=40.30 dB on SIDD denoising and PSNR=33.69 dB on GoPro deblurring, outperforming more complex Transformer architectures. It is among the preferred backbones for edge ISP deployment as of 2025 due to its low MAC count and hardware-friendly structure.

### LoRA-ISP and InstructIR (ECCV 2024)

**LoRA (Low-Rank Adaptation)** (Hu et al., ICLR 2022) decomposes weight updates into two low-rank matrix products:

$$\Delta W = B A, \quad B \in \mathbb{R}^{d \times r}, \; A \in \mathbb{R}^{r \times k}, \; r \ll \min(d,k)$$

For an ISP network with channel dimension d=k=128 and rank r=4, the trainable parameter count drops from 128²=16,384 to 2×128×4=1,024 — a 94% reduction. **LoRA-ISP** enables:
- Multi-sensor adaptation: shared pretrained backbone + per-sensor LoRA adapters
- Production cost reduction: only <1% of parameters need fine-tuning per new sensor
- Model updates without full retraining

**InstructIR** (Conde et al., ECCV 2024) extends this paradigm by using natural language instructions ("reduce noise to medium level", "enhance fine details") to control ISP network behavior at inference time, enabling a single model to cover multiple processing modes.

### DiffBIR: Two-Stage Diffusion for Blind Restoration (ECCV 2024)

DiffBIR (Lin et al., ECCV 2024) introduces a competition-proven two-stage paradigm:

```
Degraded image → [Stage 1: Deterministic Restoration] → Structural estimate
                          ↓
                 [Stage 2: ControlNet + Diffusion] ← spatial conditions
                          ↓
          Final output with perceptually realistic high-frequency detail
```

Stage 1 uses a lightweight network (e.g., SwinIR or NAFNet) to produce a geometrically correct, if slightly blurry, initial estimate. Stage 2 feeds this estimate to a Stable Diffusion backbone via ControlNet, which injects perceptually realistic high-frequency detail. The separation of structural recovery (Stage 1) from detail synthesis (Stage 2) allows independent tuning of fidelity vs. perceptual quality. The main cost is multi-step diffusion inference (10–50 steps), making DiffBIR suitable for post-capture processing rather than real-time preview.

### Engineering Deployment Constraints: INT8, Latency, and Memory

**Latency and Throughput.** A mobile ISP must process a 12MP RAW frame within the sensor readout time, often under 30ms for video. Full-resolution NAFNet would be far too slow; practical deployment uses:
- Tiled processing with overlap-and-add
- Lightweight backbone (MobileNet-style depthwise separable convolutions)
- FP16 or INT8 quantization for NPU execution

**INT8 Quantization.** FP32 weights are mapped to 8-bit integers (256 levels), with a quantization step size Δ ≈ R/2⁸. Maximum quantization error is R/512. Quantization-Aware Training (QAT) recovers 0.5 dB or more compared to post-training quantization (PTQ) and should be used for production ISP models. On flagship mobile SoCs, INT8 NPU inference consumes approximately 100–500 mW — acceptable for photo capture, though high for continuous video preview.

**Memory Bandwidth.** ISP models processing full-resolution frames move large amounts of data between NPU and DRAM. A rule of thumb: at 30fps 12MP, a 4-channel FP16 intermediate tensor consumes ~12GB/s of bandwidth. Models must be designed to minimize intermediate tensor size and reuse cached feature maps across tiles.

**Power Consumption.** Power-aware design often uses different models for preview (lightweight) and capture (high-quality). The 30fps video budget typically allows only 8–12ms for the DL module(s), with the remainder consumed by sensor readout, traditional ISP stages, and encoder.

**Domain Shift.** A model trained on one sensor may perform poorly on another sensor with a different noise level, pixel size, or color filter array. Production deployment requires either:
- Per-sensor fine-tuning with a small calibration dataset (LoRA approach)
- Noise-level-conditioned models (FFDNet approach) that accept noise sigma as explicit input
- Universal noise model training covering a wide range of sensor characteristics

---

## §2 标定 (Calibration)

### Dataset Curation for ISP DL Training

High-quality paired training data is the most critical resource for DL ISP development. The standard datasets are:

**SIDD (Smartphone Image Denoising Dataset)**: 30,000 noisy-clean image pairs captured with 5 representative smartphone cameras under varied lighting conditions. The clean reference is obtained by averaging multiple captures of a static scene. SIDD is the dominant benchmark for real-noise denoising evaluation.

**DND (Darmstadt Noise Dataset)**: 50 high-resolution images with real camera noise, paired with near-noiseless references obtained using a tripod and long exposure averaging. The test labels are held out by the benchmark authors to prevent overfitting.

**MIT FiveK**: 5,000 RAW images paired with expert-retouched sRGB versions (5 different expert retouchers). Used for learning the full RAW-to-sRGB mapping including aesthetic tone decisions.

**Chen et al. RAW-sRGB dataset (CVPR 2018)**: Paired indoor and outdoor scenes shot at multiple exposure levels, used for learning the RAW-to-sRGB pipeline.

### Domain Gap: Lab Data vs. Production Sensor

Even when training data is collected carefully, a domain gap often exists between lab collection conditions and production deployment:

- **Noise distribution**: Lab captures may use a limited range of ISO values; production scenes span 100-12800 ISO.
- **Lens optics**: Blur kernels vary with aperture, focal length, and field position. A model trained at f/1.8 may not generalize to f/8.
- **Scene statistics**: Lab datasets often overrepresent charts, faces, and landscapes. Production scenes include edge cases (flare, extreme contrast, partial occlusion) that are underrepresented.

Mitigation strategies:
- Use production sensor hardware for data collection, not reference cameras.
- Collect data across the full ISO and shutter speed range.
- Monitor per-scene-type performance metrics in validation.

### Augmentation Strategies for RAW Data

Standard image augmentation (horizontal/vertical flip, rotation by multiples of 90°) is safe for RAW data because it preserves the Bayer pattern structure. **Rotation by arbitrary angles is not safe** because it breaks the Bayer CFA alignment.

RAW-specific augmentations:
- **Gain augmentation**: Multiply RAW by a random scalar to simulate different exposure levels.
- **Noise injection**: Add synthetic Poisson-Gaussian noise with parameters drawn from a calibrated noise model to augment ISO coverage.
- **White balance jitter**: Apply random multiplicative gains per channel to augment lighting condition diversity.

---

## §3 调参 (Tuning)

### Learning Rate Schedules for ISP Models

ISP models are typically trained with Adam optimizer starting at lr=1e-4 or 2e-4 and decayed using one of:

- **Cosine annealing**: Smooth decay following a half-cosine curve, reaching near-zero at the end of training. Works well for most ISP tasks and is used in NAFNet and Restormer training.
- **Step decay**: Multiply LR by 0.5 every N epochs. Simpler to reason about; used in many DnCNN-family models.
- **Warm restarts**: Periodically reset LR to its peak value; allows the optimizer to escape local minima. Useful when training on heterogeneous multi-task datasets.

A common practical issue is that ISP models trained with cosine annealing must be re-trained from scratch if training is extended, because the learning rate profile is tied to the total number of steps. Warm restarts avoid this constraint.

### Loss Function Selection

| Task | Recommended Loss | Rationale |
|------|-----------------|-----------|
| Denoising (fidelity) | L1 | Sharper than L2; robust to outlier pixels |
| Denoising (perceptual) | L1 + 0.1 * SSIM | Adds structural constraint |
| Super-resolution | L1 + 0.01 * VGG | Perceptual loss avoids over-smoothing |
| Full pipeline RAW-sRGB | L1 + 0.1 * SSIM + 0.01 * VGG | Multi-objective balance |
| Joint training with GAN | L1 + adversarial | Only if perceptual sharpness is priority |

Note: L2 loss should be avoided when the goal is visible image quality. Its tendency to produce blurry outputs is severe enough that even simple L1 outperforms it on perceptual metrics.

### Batch Size and Patch Size Guidelines

ISP training uses random patch crops rather than full images because:
- Full 12MP images do not fit in GPU memory at typical batch sizes.
- Patch training provides data augmentation (each crop is a different sample).
- Convolutional networks are translation-equivariant; patch training generalizes to full-image inference.

Practical guidelines:
- **Patch size 128x128**: Minimum for most ISP tasks; sufficient for local texture recovery.
- **Patch size 256x256**: Recommended for tasks requiring moderate context (HDR reconstruction, sharpening).
- **Patch size 512x512**: Used for models with large receptive fields (Restormer on full-image tasks).
- **Batch size**: Limited by VRAM. For 256x256 patches on 24GB GPU, batch 16-32 is typical.

Small batch sizes (batch 4-8) require careful learning rate reduction to maintain stable gradient estimates.

---

## §4 Artifacts

### DL Overfitting: Generalization Failure to Unseen Sensors

A DL ISP model can achieve excellent PSNR on its validation set while failing on a sensor it was not trained on. This failure mode is more dangerous than traditional ISP degradation because the failure may not be visually obvious at first glance — the output looks like a plausible photograph but contains systematic errors.

Symptoms: color casts on specific hues, texture hallucination in smooth regions, or complete failure on certain ISO ranges that were absent from training data.

Mitigations: Evaluate on a hold-out sensor not seen during training. Use noise-level conditioning to generalize across ISO. Implement test-time adaptation with small fine-tuning datasets per new sensor.

### Hallucination: Plausible but Incorrect Textures

Models trained with perceptual or adversarial losses may "invent" fine texture detail that was not present in the original scene. This is perceptually pleasing in consumer photography but is unacceptable in scientific, forensic, or medical applications.

Example: a DL super-resolution model may render a blurry text region as sharp, readable characters — but with incorrect letter shapes. The output is perceptually sharp but semantically wrong.

Detection: Compare DL output to ground truth at the pixel level in regions of fine texture. Evaluate on a dataset containing known-content patterns (resolution charts, OCR text panels).

### DL Brittleness: Failures Under Distribution Shift

DL ISP models are sensitive to inputs outside their training distribution. Common failure triggers:

- **Extreme lighting**: Very dark scenes (stars, candlelight) or very bright scenes (direct sun, specular highlights) may not be represented in training data.
- **Novel lens flare patterns**: Flare is highly lens-dependent; a model trained without flare examples will not handle it gracefully.
- **Unusual color temperatures**: Light sources far outside the standard 2000-6500K range (sodium vapor, certain LEDs) can cause AWB and demosaic failures.

Mitigation: comprehensive augmentation during training, and a traditional fallback for conditions that trigger low-confidence detection.

---

## §5 评测 (Evaluation)

### Full-Reference Metrics

For tasks where a ground-truth clean image exists (denoising, super-resolution), standard quantitative metrics are:

**PSNR (Peak Signal-to-Noise Ratio)**: Measures pixel-level fidelity in dB. Higher is better. A difference of 0.5 dB is considered meaningful; 1 dB is clearly visible.

**SSIM (Structural Similarity Index)**: Measures luminance, contrast, and structure similarity. Ranges from 0 to 1; higher is better. More correlated with visual quality than PSNR for heavily degraded images.

**LPIPS (Learned Perceptual Image Patch Similarity)**: Uses AlexNet or VGG features to measure perceptual distance. Lower is better. Best correlation with human judgments of "looks better." Essential for evaluating GAN-based and perceptual-loss models.

Standard benchmarks:
- **Denoising**: SIDD validation set (real noise, smartphones), DND benchmark (real noise, DSLRs), BSD68 (synthetic Gaussian noise, sigma=25/50)
- **Super-resolution**: Set5, Set14, BSD100, Urban100 (synthetic), RealSR (real)
- **Full pipeline**: MIT FiveK, Chen et al. RAW-sRGB dataset

### Model Complexity Metrics

For production deployment, accuracy metrics must be evaluated alongside:

| Metric | Measurement | Target (mobile) |
|--------|-------------|-----------------|
| Parameters | Count | < 2M for real-time |
| FLOPs (for 1MP input) | Multiply-Adds | < 50 GMACs |
| Latency (NPU, INT8) | ms per frame | < 30ms |
| Memory bandwidth | GB/s | < 10 GB/s |

### Human Preference Study

For consumer ISP, objective metrics are necessary but not sufficient. Human preference studies (pairwise comparisons using a Mean Opinion Score protocol) are conducted to validate that metric improvements translate to user preference.

Key design considerations for ISP preference studies: use naive (non-expert) raters, diverse scene types, and control for display calibration. Online crowdsourcing studies (Amazon Mechanical Turk) are commonly used for scale but introduce display calibration uncertainty.

---

## §6 代码

See *See §6 Code section for runnable examples.* in this directory for:
- Synthetic ISP test image generation and traditional pipeline baseline
- TinyResDenoiser: a minimal 3-layer residual CNN demonstrating the residual learning concept
- Parameter table and comparison visualization
- FLOPs/parameter count and published PSNR comparison table
- Exercises

---

## §7 Top Competitions & Technical Development Trends

Top academic competitions are among the most important drivers of progress in Low-Level Vision. The image restoration and enhancement challenges held at CVPR, ICCV, and ECCV attract the world's best teams from academia and industry. Their winning solutions typically become industry standards within six months.

### 7.1 Major Competition Series Overview

#### NTIRE (New Trends in Image Restoration and Enhancement)

NTIRE is organized by Professor Radu Timofte (ETH Zurich / University of Würzburg) and held annually at CVPR. It is the largest and most influential competition series in low-level vision:

| Year | Track Count | Key Technical Breakthrough |
|------|------------|---------------------------|
| 2023 | 14 tracks | HAT (Hybrid Attention Transformer) dominated SR; NAFNet/Restormer ruled denoising/deblurring |
| 2024 | 20+ tracks | Diffusion models entered competitions (DiffBIR, SeeSR); foundation model fusion emerged |
| 2025 | 25+ tracks (largest to date) | Mamba (SSM) rises; OSEDiff achieves one-step diffusion SR |

Official: https://cvlai.net/ntire/2025/

#### UG2+ (Uncontrolled to General AI)

UG2+ focuses on **task-driven image restoration** — optimizing for downstream perception accuracy (object detection, face recognition, autonomous driving) rather than PSNR/SSIM.

Core philosophy: "Restoration is a means; perception is the goal."

Key tracks:
- Fog/haze scene object detection restoration
- Backlit/night face recognition enhancement
- Autonomous driving perception enhancement (rain/fog/snow)
- Compressed video action recognition

Official: https://ug2challenge.github.io/

#### AIM (Advances in Image Manipulation)

AIM is organized by ETH at ICCV (odd years) and ECCV (even years):

| Year | Notable Tracks | Winning Techniques |
|------|---------------|-------------------|
| AIM 2023 @ ICCV | Night flare removal, 6K UHD SR, image harmonization | NAFNet variants; FFT-based flare separation |
| AIM 2024 @ ECCV | Real-world video SR, RAW image SR, bokeh rendering, image matting | Diffusion-enhanced VSR; ViTMatte; depth-guided bokeh |

#### MIPI (Mobile Intelligent Photography & Imaging)

MIPI focuses on smartphone photography and is co-located with ECCV/CVPR:

| Year/Track | Winning Approach | ISP Relevance |
|------------|-----------------|---------------|
| MIPI 2023 Under-Display Camera restoration | MPRNet variants; frequency-domain enhancement | Fixed-pattern UDC blur compensatable via FFT |
| MIPI 2024 RGBW remosaicing | Joint demosaic+denoise network | Joint RAW-domain processing outperforms sequential by 0.5–1.0 dB |
| MIPI 2024 Night flare removal | U-Net + frequency filtering | FFT separates low-frequency circular scatter component |

---

### 7.2 Architecture Evolution Roadmap

Competitions reflect three paradigm shifts in low-level vision architectures:

```
2020–2021: CNN Era
  └─ RRDB (ESRGAN), MPRNet, CBAM attention
  └─ Characteristics: local receptive field, high throughput

2021–2023: Transformer Era
  └─ SwinIR (2021) → Restormer (2022) → NAFNet (2022) → HAT (2023)
  └─ Characteristics: global attention, major PSNR gains; still discriminative training

2023–2025: Diffusion / Foundation Model Era
  └─ StableSR (IJCV 2024) → DiffBIR (ECCV 2024) → SeeSR (2024) → OSEDiff (2024)
  └─ SUPIR (2024): SD-XL + LLM captions → universal blind restoration
  └─ MambaIR (2024): State space model, linear complexity, extending to video
  └─ Characteristics: perceptual quality far exceeds CNN; high compute; generation vs. restoration trade-off
```

**Representative PSNR progress (Set5 ×4 SR benchmark):**

| Method | Year | PSNR (dB) | Notes |
|--------|------|-----------|-------|
| RRDB (ESRGAN) | 2018 | 32.73 | Good perceptual quality, PSNR sacrificed |
| SwinIR | 2021 | 32.93 | First Transformer to surpass CNN |
| HAT | 2023 | 33.04 | ImageNet pre-training provides additional gains |
| HAT-L | 2023 | 33.18 | Large model + large data |
| SeeSR | 2024 | — | LPIPS dramatically better; PSNR slightly lower |
| OSEDiff | 2024 | — | One-step diffusion; balances perception/fidelity |

---

### 7.3 Annual Winning Technologies: Deep Analysis

#### 2023: HAT + NAFNet Era

**HAT (Hybrid Attention Transformer)** — NTIRE 2023 SR champion, core innovations:

1. **Overlapping Cross-Attention (OCA)**: Computes cross-window attention in overlapping windows, overcoming SwinIR's window boundary information barrier
2. **Channel Attention**: Parallel channel-dimension attention captures global statistics
3. **ImageNet Pre-training**: Large-scale pre-training significantly improves downstream restoration (+0.15–0.3 dB)

**NAFNet's competition advantages:**
- Removes all nonlinear activations (ReLU/Sigmoid) → more stable training
- Simple gating: `X = X1 * σ(X2)` replaces complex attention
- SOTA on GoPro deblurring and SIDD denoising benchmarks

#### 2024: Diffusion Model Fusion

**DiffBIR** introduced the two-stage competition paradigm:

```
Degraded image → [Stage 1: Deterministic Restoration] → Initial estimate
                            ↓
                   [Stage 2: Diffusion Refinement] ← ControlNet
                            ↓
              Final output with perceptually realistic details
```

**SeeSR's innovation**: Uses DINO + tag captions as semantic prior for the diffusion model, preventing hallucinated content:

```python
tags = tag_extractor(degraded_img)  # "outdoor, building, sky, tree"
text_embed = text_encoder(tags)
sr_output = diffusion_model(degraded_img, condition=text_embed)
```

#### 2025: Mamba + One-Step Diffusion

**MambaIR** — linear time complexity O(N) vs. Transformer's O(N²):

$$h_t = \overline{A} h_{t-1} + \overline{B} x_t, \quad y_t = C h_t$$

**Visual Selective Scanning (VSS)**: 4-directional scan of 2D images (horizontal, vertical, two diagonals) — equivalent to global receptive field.

**OSEDiff** compresses diffusion from 20–50 steps to 1 step via **Consistency Distillation**:
- Perceptual quality retains 90%+ of multi-step methods
- 20× inference speedup
- Critical for efficiency-constrained competition tracks

---

### 7.4 UG2+: Lessons from Task-Driven Restoration

Key findings from UG2+ (2023–2025):
1. **Highest PSNR restoration ≠ highest detection mAP** — traditional L2 loss misaligns with perception task objectives
2. **Joint training** (restore+detect end-to-end) consistently outperforms separate training
3. **Diffusion models are unstable in UG2+** — hallucinated details can mislead detectors

ISP engineering implication: the ultimate optimization target is user experience (face recognition rate, scene classification accuracy), not isolated PSNR/SSIM.

---

### 7.5 Competition-Driven ISP Engineering Practice

| Competition Technology | ISP Deployability | Key Challenge |
|-----------------------|------------------|---------------|
| Transformer (SwinIR/HAT) | Feasible on flagship chips (A17/8 Gen 3) | Memory bandwidth; attention compute |
| NAFNet | Highly feasible (low MACs) | Already deployed in several phone ISPs |
| Diffusion (DiffBIR) | Cloud processing feasible; edge experiments in 2025 | Multi-step inference latency; requires distillation |
| OSEDiff (one-step) | Edge deployment possible ~2026 | NPU operator support; model quantization |
| MambaIR | High edge potential (linear complexity) | Hardware SSM operators not yet mature |
| RetinexFormer (night) | Deployed in Huawei/Xiaomi flagships | Interface design with ISP pipeline |

---

Further discussion of LLM and diffusion foundation model deployment paths in ISP is covered in Part 5 (Chapters 56–58).

---

---

## §7 Glossary

**End-to-End ISP**
A neural network that takes RAW sensor data as input and produces a final sRGB (or display-ready) image in a single forward pass, replacing the entire traditional modular pipeline. Examples: PyNET (Ignatov et al., CVPRW 2020), CycleISP (Zamir et al., CVPR 2020). Maximizes joint optimization opportunity but carries the highest deployment risk.

**Degradation Model**
A mathematical description of how an ideal image is corrupted by a specific degradation process. For noise: y = x + n, where x is the clean image and n ~ N(0, σ²). For blur: y = k * x + n, where k is the blur kernel. The degradation model defines the training data generation process and the inverse problem the DL model must solve.

**QAT (Quantization-Aware Training)**
A training technique where quantization operations are simulated during the forward pass using fake-quantize layers. The model learns weights that remain accurate after actual quantization to INT8 (or lower precision). QAT consistently outperforms post-training quantization (PTQ) by 0.3–0.8 dB PSNR on ISP tasks and is recommended for production deployment.

**NAFNet (Nonlinear Activation Free Network)**
An image restoration backbone (Chen et al., ECCV 2022) that removes all nonlinear activations and replaces complex attention with SimpleGate (element-wise product of two feature splits). Achieves state-of-the-art on SIDD denoising (PSNR=40.30 dB) and GoPro deblurring. Preferred for edge deployment due to low MACs and hardware-friendly operations.

**Restormer (Efficient Transformer for High-Resolution Restoration)**
A Transformer-based image restoration model (Zamir et al., CVPR 2022) that uses Transposed Attention — computing attention across the channel dimension rather than spatial positions. This reduces complexity from O((HW)²) to O(C²·HW), enabling efficient processing of full-resolution images.

**LoRA (Low-Rank Adaptation)**
A parameter-efficient fine-tuning method (Hu et al., ICLR 2022) that decomposes weight updates as ΔW = BA where rank r ≪ min(d, k). Applied to ISP, it enables per-sensor adaptation with <1% of total parameters, making multi-sensor production deployment economical without full retraining.

---

## §8 Engineering Recommendations

The following guidelines are distilled from production ISP deployment experience and competition results. They are intended for algorithm engineers making architecture and training decisions.

**1. Start with Single-Module Replacement**
Do not attempt to replace the full ISP pipeline in the first iteration. Deploy DL in the one or two stages where it provides the greatest quality benefit (typically denoising and super-resolution). Validate thoroughly before expanding scope. Full pipeline replacement requires full regression testing and increases failure attribution complexity.

**2. Budget Latency Before Selecting Architecture**
Fix the latency target before selecting a model. For 30fps video on a flagship SoC: the DL window is typically 8–12ms. Measure on the target NPU with INT8 at 1080P before committing to an architecture. NAFNet-32 (~0.3M parameters) fits comfortably in this window; Restormer-Small may require tiling.

**3. Use QAT, Not PTQ, for Production**
Post-training quantization (PTQ) is convenient but loses 0.5–1.0 dB on ISP tasks. Always use quantization-aware training for production models. Budget two to three additional training epochs for QAT fine-tuning after FP32 convergence.

**4. Collect Data on the Production Sensor**
Domain shift from a reference camera to the production sensor is the most common cause of field failures. All training data for sensor-specific tasks (denoising, demosaic) should be collected on the exact production sensor hardware across the full ISO range.

**5. Use LoRA for Multi-Sensor Adaptation**
When the same base model must serve multiple sensor variants (e.g., main camera + ultra-wide), train per-sensor LoRA adapters rather than separate models. The shared backbone captures generalizable image priors; the LoRA modules capture per-sensor noise and color characteristics. Total storage footprint is dramatically reduced.

**6. Align Loss Function with the Deployment Use Case**
For automotive, medical, or forensic applications requiring pixel-level fidelity: train with L1 or L1+SSIM. For consumer photography where perceptual quality matters more than PSNR: add a VGG perceptual loss term (weight 0.01–0.1). Do not use pure L2 loss — it produces systematically blurry outputs that users notice.

**7. Implement a Traditional Fallback**
Every DL ISP module should have a traditional algorithm fallback that activates when: (a) NPU utilization exceeds a threshold, (b) scene conditions trigger low-confidence detection, or (c) the DL module returns a result outside expected range. This prevents catastrophic failure in corner cases.

---

## 参考资料

- Chen, C. et al. "Learning to See in the Dark." CVPR 2018.
- Chen, C. et al. "Camera-to-RAW: Learning RAW-to-sRGB Mappings." CVPR 2018.
- Zamir, S. W. et al. "CycleISP: Real Image Restoration via Improved Data Synthesis." CVPR 2020.
- Ignatov, A. et al. "PyNET: Replacing Mobile Camera ISP with a Single Deep Learning Model." CVPRW 2020.
- Zhang, K. et al. "Beyond a Gaussian Denoiser: Residual Learning of Deep CNN for Image Denoising." TIP 2017. (DnCNN)
- Zhang, K. et al. "FFDNet: Toward a Fast and Flexible Solution for CNN-Based Image Denoising." TIP 2018.
- Chen, L. et al. "Simple Baselines for Image Restoration." ECCV 2022. (NAFNet)
- Gharbi, M. et al. "Deep Bilateral Learning for Real-Time Image Enhancement." SIGGRAPH 2017. (HDRNet)
- Hu, Y. et al. "Exposure Correction Model to Enhance Image Quality." CVPR 2021. (Deep WB)
- Blau, Y. and Michaeli, T. "The Perception-Distortion Tradeoff." CVPR 2018.
- Zhang, R. et al. "The Unreasonable Effectiveness of Deep Features as a Perceptual Metric." CVPR 2018. (LPIPS)
- MIT FiveK dataset: Bychkovsky, V. et al. CVPR 2011.
- SIDD dataset: Abdelhamed, A. et al. CVPR 2018.
