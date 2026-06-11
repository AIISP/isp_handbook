# Part 3, Chapter 22: All-Weather Multi-Degradation Image Restoration

> **Pipeline position:** DL-ISP post-processing; image quality enhancement under extreme conditions
> **Prerequisites:** Volume 3, Chapter 2 End-to-End Restoration; Volume 3, Chapter 6 Low-Light Enhancement; Volume 3, Chapter 20 Deep Learning Denoising
> **Target readers:** DL researchers, automotive/surveillance ISP engineers, consumer photography algorithm engineers

> **Distinction between this chapter and Volume 3, Chapter 18:**
>
> | Dimension | Volume 3, Chapter 18 All-in-One Restoration | This chapter: All-Weather Multi-Degradation |
> |---|---|---|
> | Degradation types | Known types (denoising/deblurring/SR) | Unknown/mixed (rain/fog/snow/raindrops) |
> | Scene assumption | Laboratory-controlled | Real-world adverse weather |
> | Representative methods | Restormer, DiffIR | TransWeather, WeatherDiffusion |
> | Core challenge | Multi-task unified network | Weather-type recognition + adaptive restoration |
> | Primary audience | DL algorithm researchers | Autonomous driving/surveillance/outdoor camera engineers |

---

## §1 Theory

### 1.1 Problem Definition and Challenges of Multi-Degradation

Traditional image restoration research treats each degradation type (rain, fog, blur, noise, low-light, compression artifacts) as an **independent problem**: rain-removal models process only rain streaks, dehazing models only atmospheric scattering, denoising models only sensor noise. This paradigm achieves excellent results under lab conditions but faces fundamental difficulties in real deployment:

1. **Unknown degradation type:** In real scenes, cameras cannot automatically identify the current degradation type accurately. Rain-fog mixed scenes (rainy day with haze) and low-light noisy scenes involve multiple simultaneous degradations; it is unclear which single-task model to invoke;
2. **High deployment cost:** Maintaining a separate model for each degradation type is impractical on mobile NPUs with simultaneous memory constraints (~100–200 MB); dynamic loading introduces latency;
3. **Interdependence among degradations:** Real-world degradations are often coupled — rain scenes near rain streaks often have accompanying scattering haze, low contrast, and motion blur (rain droplet motion); a standalone rain-removal model cannot handle these composite effects.

The goal of **Universal Restoration (多退化统一复原)** is to design a single model that takes an image with any degradation type as input and outputs a high-quality restored result:

$$\hat{x} = f_\theta(y, d) \quad \text{or} \quad \hat{x} = f_\theta(y)$$

where $d$ is a degradation-type descriptor (degradation-aware design), or in the **blind restoration** setting $d$ is omitted entirely and the network automatically perceives the degradation type.

---

### 1.2 Early Unified Frameworks: MPRNet and Uformer

**MPRNet** (Zamir et al., CVPR 2021) achieves state-of-the-art results simultaneously on deraining, dehazing, and deblurring through Multi-stage Progressive Restoration. Although not an explicitly unified framework, it demonstrates that the same architectural design principles are effective across tasks.

**Uformer** (Wang et al., CVPR 2022) uses a hierarchical U-Net-shaped Transformer (LeWin Transformer Block) for joint multi-task training on denoising, deraining, and dehazing, demonstrating that Transformers' global receptive field is effective across multiple degradation types.

The common limitation of these works is that in multi-task joint training, **gradient interference (梯度干扰)** between tasks causes each task's accuracy to be slightly lower than the corresponding single-task expert model, typically by about 0.2–0.5 dB PSNR.

---

### 1.3 TransWeather (CVPR 2022)

TransWeather (Chen et al., CVPR 2022) is the first Transformer method to handle all weather degradations with a single network:

- **Weather-Type Queries (天气类型查询):** Learnable queries automatically identify the current weather type without manual specification
- **Intra-patch Transformer decoder:** Captures fine degradation textures within patches (rain streak / snowflake edges)
- Degradation model: $\mathbf{y} = \mathbf{x} \odot \mathbf{T} + \mathbf{A}(1-\mathbf{T}) + \mathbf{R}$, where $\mathbf{T}$ is the transmission map, $\mathbf{A}$ is the atmospheric light, and $\mathbf{R}$ is additional rain/snow noise

---

### 1.4 All-in-One (NeurIPS 2023)

Potlapalli et al.'s PromptIR uses a Prompt Encoder to inject degradation-type information into the restoration network:

$$\hat{\mathbf{x}} = f_\theta(\mathbf{y}, \mathbf{p}_k), \quad \mathbf{p}_k = g_\phi(\mathbf{y})$$

where $\mathbf{p}_k$ is a degradation-aware prompt vector and $g_\phi$ is a lightweight degradation classification head.

---

### 1.5 WeatherDiffusion (ECCV 2024)

Diffusion-model-based unified weather removal:
- Conditional diffusion: conditioned on the degraded image, progressively removes weather noise
- Key advantage: high generation quality; no need for explicit weather type labels
- Inference cost: 100-step DDIM sampling on an A100 takes approximately 1.2 s/image (512×512)

---

### 1.6 Relationship to Volume 3, Chapter 18: Contrastive Learning and Prompt-Driven Methods

AirNet (CVPR 2022) contrastive degradation learning and PromptIR (NeurIPS 2023) visual prompt mechanisms are general-purpose unified restoration frameworks that are **fully covered in Volume 3, Chapter 18**, including detailed mathematical derivations and code implementations.

The weather degradation scenarios in this chapter (rain/fog/snow/raindrops) differ fundamentally from the synthetic degradations in Chapter 18 (noise/blur/JPEG) in the following ways:
- **Different physical mechanisms:** Weather degradations follow the atmospheric scattering model $I(x) = J(x)t(x) + A(1-t(x))$; rain streaks have well-defined physical geometry, while synthetic noise is statistically independent
- **Different degradation sensing approaches:** Weather types (TransWeather) are automatically identified via learnable query vectors, while synthetic degradations are identified via InfoNCE contrastive embeddings
- **Different engineering constraints:** Outdoor cameras and automotive systems face special challenges including inter-frame consistency, extreme lighting conditions, and mixed-weather scenarios

For general multi-degradation contrastive learning / prompt mechanisms, see → **Volume 3, Chapter 18, §2 (Algorithm Methods)**.

---

### 1.7 Restormer Backbone in Weather Restoration

**Restormer** (Zamir et al., CVPR 2022) transposed attention is widely used as the backbone in weather restoration methods including TransWeather and PromptIR. The complete mathematical derivation is in **Volume 3, Chapter 1, §2.3**; the key result is: complexity $O(C^2HW)$ scales linearly with resolution (vs. $O(H^2W^2C)$ for standard spatial attention), making it viable for high-resolution weather images. In multi-task joint training for weather restoration, Restormer combined with GradNorm gradient normalization dynamically adjusts task weights to mitigate inter-task gradient interference.

---

### 1.8 DiffIR Applied to Weather Restoration

**DiffIR** (Xia et al., ICCV 2023) diffusion framework and its detailed derivation are covered in **Volume 3, Chapter 7 (Diffusion Model Restoration)**. In weather restoration scenarios, its two-stage design offers specific advantages: Stage 1 deterministic coarse restoration quickly removes rain streak skeletons and haze layers (~15 ms/frame); Stage 2 compact latent-space diffusion (4–8 DDIM steps) generates weather-specific high-frequency textures (post-rain wet texture, post-haze atmosphere feel), significantly improving perceptual quality (LPIPS average +12–18% vs. Restormer). WeatherDiffusion (ECCV 2024) further adapts the diffusion model as a unified all-weather removal framework without explicit weather type labels, achieving PSNR 38.52 dB on the SOTS-Outdoor dehazing benchmark.

---

### 1.9 Large-Scale Pretrained Unified Restoration: UniRestorer and X-Restormer

**UniRestorer** (Wang et al., CVPR 2024) advances unified restoration toward a large-scale pretraining paradigm: pretrained on 500K images covering 30+ degradation types, using **natural language encoding of degradation type descriptions** (CLIP text encoder) to construct degradation conditions, supporting degradation-type specification via text description. UniRestorer has some generalization ability to unseen degradation types (zero-shot restoration).

**X-Restormer** (a class of CVPR 2025/2026 works) further explores **blind unified restoration without degradation-type annotation**: the network adaptively perceives the degradation type from the input image, processing end-to-end without relying on any external degradation-type information. This represents progress toward a "single end-to-end camera ISP post-processing model."

---

### 1.10 Cross-Method Performance Comparison for All-in-One Methods

The following table summarizes PSNR and model efficiency metrics for mainstream unified image restoration methods on three core tasks (based on published paper data; test sets: noise CBSD68 σ=25, deraining Rain100L, SR Urban100 ×4; parameter count refers to the restoration backbone; speed baseline: RTX 3090, 1080p input):

| Method | Published | Denoising PSNR ↑ | Deraining PSNR ↑ | SR PSNR ↑ | Parameters | Speed (ms) |
|--------|-----------|-----------------|-----------------|-----------|------------|-----------|
| DnCNN (single-task expert) | TIP 2017 | 31.73 | — | — | 0.6M | 8 |
| Restormer (single-task) | CVPR 2022 | 32.00 | 42.34 | — | 26M | 65 |
| MPRNet (multi-task joint) | CVPR 2021 | 31.65 | 42.41 | — | 20M | 58 |
| Uformer (multi-task joint) | CVPR 2022 | 31.79 | 41.96 | — | 51M | 82 |
| AirNet (unified, DCLP) | CVPR 2022 | 31.55 | 41.77 | — | 8.9M | 45 |
| PromptIR (unified, Prompt) | NeurIPS 2023 | **32.31** | **42.74** | **32.97** | 35M | 78 |
| DiffIR (unified, diffusion) | ICCV 2023 | 32.10 | 42.80 | 33.21 | 16M | 250† |
| UniRestorer (pretrained) | CVPR 2024 | 32.18 | 43.12 | 33.45 | 82M | 130 |

> †DiffIR speed is for 8-step DDIM sampling; at 4 steps approximately 130 ms with PSNR drop of approximately 0.2 dB.
> SR PSNR is for ×4 single-task comparison; AirNet original paper does not test SR, shown as —.

**Key observations:**
1. PromptIR is the first unified method to **simultaneously surpass the corresponding single-task expert** on all tasks (including SR);
2. DiffIR is slower but leads in perceptual quality (LPIPS); suitable for offline high-quality processing;
3. Unified model parameter counts (35–82M) are significantly larger than single-task models (0.6–26M), reflecting the larger capacity needed for "shared representation learning";
4. Denoising PSNR improves under the unified framework (PromptIR 32.31 > Restormer 32.00), possibly due to the implicit regularization effect of multi-task training.

---

### 1.11 Theoretical Perspective on Multi-Degradation Joint Modeling

From a Bayesian inference perspective, unified restoration can be modeled as:

$$p(x | y) = \int p(x | y, d) \cdot p(d | y) \, \mathrm{d}d \tag{7}$$

where $p(d|y)$ is the posterior distribution over degradation type (estimated by the degradation encoder $E_d$) and $p(x|y,d)$ is the conditional restoration distribution given the degradation type (modeled by the restoration network $f_\theta$). Frameworks such as AirNet and PromptIR are essentially approximations of Eq. (7): first estimating the degradation type (degradation representation), then performing conditional restoration.

In multi-degradation joint training, **gradient balancing (梯度平衡)** is critical: differences in loss magnitude across degradation tasks (e.g., denoising PSNR ~38–40 dB, dehazing ~33–36 dB) cause the joint loss gradient to be dominated by the high-magnitude task. Common solutions are **gradient normalization** or **dynamic task weight adjustment** (GradNorm).

---

## §2 Calibration

### 2.1 All-Weather Restoration Datasets

| Dataset | Weather type | Scale | Source | Access |
|---------|-------------|-------|--------|--------|
| Outdoor-Rain | Rain | 1,800 pairs | Zhang et al., CVPR 2019 | GitHub |
| Snow100K | Snow | 100,000 images | Liu et al., TIP 2018 | Official website |
| RESIDE | Fog/haze | 72,135 pairs | Li et al., TIP 2019 | Official website |
| RainDrop | Raindrops | 1,119 pairs | Qian et al., CVPR 2018 | GitHub |
| AllWeather | Mixed four types | 10,000 training | Valanarasu et al., CVPR 2022 | GitHub |
| WeatherStream | Real weather | 150K frames | Zhang et al., CVPR 2023 | GitHub |

### 2.2 Multi-Task Evaluation Benchmark

| Degradation type | Standard dataset | Evaluation metrics |
|-----------------|-----------------|-------------------|
| Noise (AWGN σ=15/25/50) | CBSD68, Set12 | PSNR/SSIM |
| Rain (Rain100L/H, Rain1400) | Rain100L, Rain100H | PSNR/SSIM |
| Fog (outdoor/indoor) | SOTS-Indoor, SOTS-Outdoor | PSNR/SSIM |
| Motion blur | GoPro, HIDE | PSNR/SSIM |
| Low light | LOL, MIT-FiveK (low-light subset) | PSNR/SSIM/LPIPS |
| JPEG compression | Classic5, LIVE1 | PSNR/SSIM |

### 2.3 Degradation-Awareness Accuracy (Degradation Type Prediction Accuracy)

For unified restoration methods that rely on degradation-type prediction, **degradation-awareness accuracy** is an independent evaluation metric: the Top-1 classification accuracy with which the degradation encoder predicts the degradation type given a degraded image. AirNet reports five-class degradation classification accuracy of approximately **92–95%**; when degradation awareness fails (misclassification), restoration quality drops substantially (approximately 2–5 dB), making the robustness of the degradation encoder a key deployment concern.

---

## §3 Engineering Practice

### 3.1 Mapping Real Degradation Scenarios in Mobile Cameras

| Capture scenario | Main degradation types | Recommended processing priority |
|---|---|---|
| Rainy day shooting | Rain streaks + scattering haze + water-drop blur | Deraining > Dehazing > Deblurring |
| Hazy day | Atmospheric scattering + low contrast | Dehazing + contrast restoration |
| Night handheld | Shot noise + motion blur + low light | Denoising > Low-light enhancement > Deblurring |
| Underwater | Non-uniform scattering + color shift + noise | Descattering + color correction |
| Indoor low-light | High-ISO noise + color noise | RAW-domain denoising (see ch20) |

Deploying a unified restoration model on mobile devices typically faces the following constraints: NPU inference latency < 100 ms (4K image); model size < 50 MB; support for variable input resolution (diverse mobile resolutions).

### 3.2 Analysis of Actual Performance Degradation When Deploying Multiple Tasks with One Model

When pushing unified restoration models into production systems in real industrial deployment, there is often a significant performance gap between academic benchmark results and engineering measurements. The main causes and countermeasures are summarized below:

**Phenomenon 1: Domain shift between real and synthetic degradations**
- Academic benchmark "deraining" test sets (Rain100L) use regular straight-line synthetic rain, while real rainy images include complex effects such as raindrop refraction halos, window water marks, and motion blur trails;
- A model with PSNR 42+ dB on Rain100L may receive only "average" subjective scores on real rainy mobile photos;
- **Countermeasure:** Mix 5–10% of real degradation images into the training set (weak supervision or unsupervised), and use perceptual loss (LPIPS) and GAN loss to reduce domain sensitivity.

**Phenomenon 2: Negative transfer between tasks**
- In unified models for some task combinations (e.g., simultaneous denoising + SR), **negative transfer (负迁移)** occurs: SR guides the network to "generate" new pixels, while denoising guides removal of high-frequency content — conflicting optimization directions;
- PromptIR mitigates negative transfer via task-specific prompt vectors, but simultaneous denoising vs. SR training is still 0.1–0.3 dB below training each alone in practice;
- **Countermeasure:** Group physically similar degradations together (denoising + deraining: both "remove random interference"); keep reconstruction tasks like SR in a separate group to reduce conflicts.

**Phenomenon 3: Degradation intensity generalization failure**
- Models train with discrete noise levels $\sigma \in \{15, 25, 50\}$, but real camera noise follows a continuous distribution; when the test noise level falls between training values (e.g., $\sigma = 35$), the unified model may underperform the interpolated result from expert models trained at $\sigma = 25$ and $\sigma = 50$;
- **Countermeasure:** Use continuous uniform sampling of noise level $\sigma \sim U[0, 70]$ during training (similar to FFDNet design), and feed noise level or degradation intensity as a continuous conditional input (not just implicitly sensed via the degradation encoder).

**Phenomenon 4: Uneven multi-task accuracy after mobile quantization**
- INT8 quantization affects PSNR differently for different degradation tasks: denoising (mainly low-frequency processing) loses approximately −0.2 dB; deraining (requires high-precision high-frequency edge detection) can lose up to −0.6 dB;
- Quantization-sensitive layers in unified models (transposed attention Q/K/V softmax, degradation encoder L2 normalization) are recommended to keep in FP16; all other layers use INT8 for mixed-precision quantization;
- Measured mixed-precision (FP16 attention + INT8 elsewhere) on flagship SoC is 2.1× faster than full FP16, 15% slower than full INT8, with PSNR loss of only −0.1 dB (vs. full FP16).

---

### 3.3 Cascade vs. Unified: Engineering Selection

In engineering selection, **cascaded expert models** (first deraining → then dehazing → then denoising) and **unified single models** each have advantages and disadvantages:

| Strategy | Advantages | Disadvantages |
|---|---|---|
| Cascaded expert models | Best accuracy at each step; independently updatable | Degradation-type detection errors cascade; multiple inference passes = high latency |
| Unified single model | Single inference; avoids intermediate result errors | Average accuracy slightly below expert models (~0.3 dB); training data must cover all degradation types |

Industry trends favor **large unified models** for main degradations, supplemented by expert fine-tuning for special scenarios (e.g., extreme night scenes).

---

## §4 Failure Modes

### 4.1 Degradation Type Prediction Failure

When the degradation type is out-of-distribution (OOD, 域外), the degradation encoder misclassifies it, causing the restoration network to apply the wrong restoration strategy and producing output worse than no processing at all. Typical case: motion blur misidentified as mild noise; applying denoising makes the blur worse. Engineering mitigation: set a confidence threshold; below the threshold, fall back to lightweight general restoration or skip processing.

### 4.2 Training Data Degradation Distribution Shift

Unified restoration models are typically trained on synthetic degradation data (synthetic rain, synthetic fog, etc.), while real-scene degradation distributions (e.g., real atmospheric scattering, real camera sensor noise) have significant domain shift from synthetic data. Real-rain streak directionality and light source interaction effects are very different from simple random straight-line synthetic rain, leading to noticeably worse performance on real images compared to laboratory metrics.

### 4.3 Over-Restoration (过复原)

If a unified restoration model still applies restoration processing to mildly degraded images (e.g., ISO 100 sunny day photos), it may incorrectly smooth genuine textures (fabric, wood grain) mistaking them for noise, degrading image quality. Engineering practice avoids unnecessary processing of high-quality images by placing a **quality detection pre-stage** (IQA to determine whether restoration is needed).

### 4.4 Temporal Flickering in Video

When a unified restoration model processes video frame-by-frame independently, degradation-type prediction results may jitter between adjacent frames (frame $t$ predicted as "light fog," frame $t+1$ as "heavy fog"), causing sudden changes in restoration strength and visible temporal flickering artifacts. For video scenarios, **temporal consistency constraints** should be applied:
- Apply exponential moving average (EMA) over time to the degradation-type prediction results to stabilize predictions;
- Add L1/Warp consistency loss on adjacent-frame feature maps in the loss function;
- Or directly use a video unified restoration model (e.g., Video-AirNet) with joint temporal modeling of degradations.

### 4.5 Confusion Between Snow and White Scenes

Snowflake degradation and the texture of white clothing, white building walls are highly similar at the low-level feature level (both are high-frequency white regions with brightness near 255), causing the degradation encoder to misidentify scene content as snowflake degradation in white scenes and over-process, producing artifacts where white textures are erased. Mitigation: include hard negative samples of white scenes (white walls / white clothes / snow fields) during training to improve the degradation encoder's ability to distinguish snowflakes vs. white scenes.

---

## §5 Evaluation

### 5.1 Main Method PSNR/SSIM Benchmarks

**Deraining (Test1200):**
| Method | PSNR ↑ | SSIM ↑ |
|--------|--------|--------|
| DerainNet | 28.96 | 0.893 |
| TransWeather | 34.81 | 0.958 |
| PromptIR | 36.37 | 0.965 |

**Dehazing (SOTS-Outdoor):**
| Method | PSNR ↑ | SSIM ↑ |
|--------|--------|--------|
| DehazeNet | 21.14 | 0.847 |
| TransWeather | 34.81 | 0.982 |
| WeatherDiffusion | 38.52 | 0.991 |

### 5.2 Multi-Task Composite Score

It is recommended to report the **average PSNR/SSIM across all degradation types** as the composite metric for unified restoration models, while also reporting per-degradation metrics to identify which degradation types are weaknesses.

### 5.3 Composite Degradation Evaluation

The most important for real deployment but most lacking in the academic literature is **composite degradation evaluation**: co-occurring rain + fog (rain-fog dataset, e.g., RainFog synthesis) or noise + low-light (extremely dark night scene). It is recommended to build custom composite degradation test sets to compare the subjective quality difference between unified restoration models and the best-performing cascade approach.

---

## §6 Code

The companion code for this chapter is in *See §6 Code section for runnable examples.* and includes the following demonstrations:

1. **Degradation contrastive learning demo:** On synthetic degradation images of three types (noise / rain / fog), visualize the t-SNE feature distribution of the degradation encoder before and after training, showing how contrastive learning separates the three degradation clusters;
2. **PromptIR prompt vector interpolation:** Demonstrate linear interpolation effects between noise prompt $P_\text{noise}$ and low-light prompt $P_\text{lowlight}$, visualizing restoration results under different mixing coefficients $\alpha$;
3. **Unified model vs. expert model comparison:** Run unified restoration model (simplified AirNet) and corresponding expert models on Rain100L and CBSD68; compare PSNR differences;
4. **Degradation type prediction visualization:** Feed different degradation images and visualize the degradation encoder's prediction confidence; show misclassification cases for OOD degradations.

### 6.1 Weather Type Detection and Adaptive Restoration Example

```python
# Weather type detection + adaptive restoration (PromptIR-style)
import torch
import torch.nn as nn

class WeatherTypeEncoder(nn.Module):
    """Lightweight weather type classification head, outputs degradation-aware prompt vector"""
    def __init__(self, in_channels=3, prompt_dim=64, num_weather=4):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, padding=1), nn.ReLU(),
            nn.AdaptiveAvgPool2d(8),
            nn.Flatten(),
            nn.Linear(32*64, 128), nn.ReLU(),
        )
        self.weather_head = nn.Linear(128, num_weather)   # rain/snow/fog/raindrop
        self.prompt_head = nn.Linear(128, prompt_dim)

    def forward(self, x):
        feat = self.backbone(x)
        weather_logits = self.weather_head(feat)        # [B, 4]
        prompt = self.prompt_head(feat)                  # [B, 64]
        return weather_logits, prompt

# Inference example
encoder = WeatherTypeEncoder()
degraded = torch.randn(1, 3, 256, 256)
weather_logits, prompt = encoder(degraded)
weather_type = torch.argmax(weather_logits, dim=1)
types = ['rain', 'snow', 'fog', 'raindrop']
print(f"Detected weather type: {types[weather_type.item()]}")
```

---

## §7 Deployment Checklist

### 7.1 Pre-Launch Verification Items for Automotive/Surveillance Scenarios

Before deploying an all-weather restoration model in safety-critical scenarios such as autonomous driving perception and traffic surveillance, the following verifications are required:

| Verification item | Acceptance criterion | Notes |
|---|---|---|
| No quality degradation on clear, undegraded images | PSNR loss < 0.1 dB (vs. original) | Over-restoration guard activated |
| Light rain/fog restoration effect | SSIM ≥ 0.92 | Corresponds to traffic visibility > 200 m |
| Extreme heavy rain restoration | Subjective score ≥ 3/5 | PSNR has limited reference value |
| Degradation type misclassification rate | Top-1 error rate < 8% | Including mixed-weather test samples |
| Temporal consistency | Adjacent-frame LPIPS < 0.05 | Prevents flickering artifacts |
| NPU inference latency | P99 < 80 ms (1080p) | Including pre/post-processing time |
| Memory footprint | Peak < 300 MB | Co-existing with perception models |
| Quantization accuracy loss | INT8/FP16 vs FP32 PSNR < 0.3 dB | Mixed-precision scheme |

### 7.2 Mobile ISP Integration Notes

When integrating all-weather restoration into a mobile ISP pipeline, coordination with other modules is a key engineering challenge:

**1. Interaction with 3A**
- AE (Auto Exposure) in night-rain scenarios tends toward over-exposure compensation, making rain streaks brighter and harder to remove; it is recommended not to trigger the deraining module before AE convergence, or to apply secondary luminance correction after deraining;
- AWB in foggy conditions may shift color temperature estimation due to low-saturation scenes; it is recommended to run the dehazing module before AWB or decouple them.

**2. Ordering with HDR Merge**
- Multi-frame HDR merging should be performed before all-weather restoration: the merged image has higher SNR, giving better deraining/dehazing results;
- The reverse order (restore first then HDR merge) causes textures generated by restoration to appear as ghosting during multi-frame alignment.

**3. Processing Resolution Strategy**
- For 100-megapixel sensors, full-resolution inference is too expensive; it is recommended to infer at 1/4 resolution (approximately 25-megapixel equivalent) and upsample the output for fusion;
- Edge blur introduced by upsampling can be compensated for by sharpening via guided filtering (Guided Upsampling) using the original-resolution image.

### 7.3 Model Version Management and A/B Testing Recommendations

For iterating unified restoration models, the following A/B testing process is recommended:

1. **Blind subjective scoring:** Recruit 20+ evaluators; present them with A/B versions of real weather photos in a blind forced-choice (Forced Choice) test; a preference rate difference > 60:40 is considered statistically significant (p < 0.05, binomial test);
2. **Automated regression testing:** Automatically compute BRISQUE/NIQE/CLIP-IQA on an internal real-degradation test set (at least 500 images covering all weather types) to monitor whether the new model introduces regression;
3. **Gradual rollout:** First deploy the new model to 1% of user traffic, monitor user feedback (complaint rate/photo deletion rate) for 48 hours, then expand the proportion.

---

## §8 Glossary

**AirNet (Li et al., CVPR 2022)**
All-in-one Image Restoration Network: the first framework for unified restoration of arbitrary unknown degradations via contrastive degradation representation learning (DCLP). Degradation encoder $E_d$ uses InfoNCE contrastive loss to cluster images of the same degradation type (without needing degradation-type labels); restoration network $f_\theta$ uses $E_d(y)$ as a cross-attention condition to adaptively select the restoration strategy. Average PSNR across noise/rain/fog tasks is approximately 1.2 dB higher than previous multi-task methods, only approximately 0.3 dB below expert models.

**PromptIR (Potlapalli et al., NeurIPS 2023)**
Transfers NLP Prompt Learning to image restoration: learns visual prompt vectors $P_d \in \mathbb{R}^{L \times C}$ for each degradation type and injects them into intermediate layers of a Restormer backbone network at inference. Prompt vectors of different degradations can be linearly interpolated for composite degradations: $P_\text{mix}=\alpha P_{d_1}+(1-\alpha)P_{d_2}$. First unified restoration model to simultaneously surpass expert models on all tasks. Prompt vector parameter count is tiny (<<1M); freezing the base network parameters allows supporting new degradation types at almost zero cost.

**TransWeather (Chen et al., CVPR 2022)**
First single Transformer network to unify processing of all weather degradations (rain/fog/snow/raindrops). Core innovation: Weather-Type Queries — learnable queries automatically identify the current weather type at inference without manual specification of degradation labels. Degradation model follows unified physics formula $\mathbf{y} = \mathbf{x} \odot \mathbf{T} + \mathbf{A}(1-\mathbf{T}) + \mathbf{R}$, enabling the network to handle all weather degradations in a unified framework.

**WeatherDiffusion (ECCV 2024)**
Diffusion-model-based unified all-weather removal method. Takes the degraded image as conditional input; progressively removes weather noise via the reverse diffusion process; no explicit weather type label needed to handle composite weather degradations. High generation quality (PSNR/SSIM better than discriminative methods); trade-off is higher inference cost (100-step DDIM sampling on A100 approximately 1.2 s/image at 512×512).

**Degradation Contrastive Learning (DCLP, 退化对比学习)**
Key component of AirNet: defines any two images of the same degradation type as a positive pair and images of different degradation types as a negative pair; trains the degradation encoder with InfoNCE loss $\mathcal{L}_{DCLP}$ to make its feature space automatically cluster by degradation type. Learns degradation-aware representations without human degradation-type annotations. Analogous to SimCLR/MoCo in self-supervised visual representation learning, except augmentation strategies (data augmentation) are replaced by degradation types (physical degradations).

**Gradient Balancing (GradNorm, 梯度平衡)**
Technique for resolving loss magnitude imbalance across tasks in multi-task joint training: dynamically adjusts per-task loss weight $\lambda_k(t)$ so that each task's gradient $\|\nabla_\theta \mathcal{L}_k\|$ is approximately equal, preventing high-PSNR tasks (small magnitude, small gradient) from being dominated by low-PSNR tasks (large magnitude, large gradient). GradNorm update rule (Chen et al., 2018): $\lambda_k \leftarrow \lambda_k \cdot (\bar{g}/g_k)^\alpha$, where $\bar{g}$ is the mean gradient norm across all tasks and $\alpha$ is a balancing hyperparameter.

**Atmospheric Scattering Model (Haze Model, 大气散射模型)**
Physical basis for image dehazing: hazy image $I(x) = J(x) \cdot t(x) + A \cdot (1-t(x))$, where $J(x)$ is the haze-free scene radiance, $A$ is the global atmospheric light (大气光), and $t(x)=e^{-\beta d(x)}$ is the transmission map ($\beta$ = scattering coefficient, $d(x)$ = scene depth from camera). Dehazing is equivalent to estimating $A$ and $t(x)$ and recovering $J(x)$. Deep learning dehazing methods directly learn the end-to-end mapping $f_\theta(I) \to J$, or explicitly estimate $A$ and $t(x)$. The atmospheric scattering model assumes a uniform atmosphere ($\beta$ isotropic) and is not suitable for rain-fog mixed scenes (local perturbation of scattering by rain streaks).

**MPRNet (Zamir et al., CVPR 2021)**
Multi-stage Progressive Restoration: multi-stage progressive image restoration network achieving state-of-the-art results at the time on deblurring (GoPro PSNR 32.66 dB), deraining (Rain100L 48.16 dB), and denoising (SIDD 39.71 dB). Progressively refines restoration through multi-resolution stages (Coarse→Fine); final stage fuses early features (CSFF, Cross-Stage Feature Fusion). Although not an explicit unified restoration framework, it demonstrates that the same architectural design can be effective across degradation types, making it an important baseline for subsequent unified restoration work.

**Composite Degradation (混合退化)**
Multiple co-occurring degradation types in real scenes (e.g., rain + fog + motion blur), representing the ultimate target scenario for unified restoration frameworks. PromptIR handles composite degradations via prompt vector linear interpolation (Eq. 3), but the linear interpolation assumption is that each degradation effect is independent in feature space, which has limited effectiveness for strongly coupled degradations (e.g., rain-fog, where rain streaks themselves are local scattering). The most effective current approach for composite degradation is to decompose the composite degradation into independent components (physics-model constrained), restore each independently, then fuse.

**Over-Restoration Guard (过复原防护)**
An engineering protection mechanism that performs pre-stage quality detection on input images to avoid unnecessary restoration processing (which degrades quality) on high-quality images. Typically uses a no-reference IQA score (BRISQUE/NIQE) or an ISO/exposure-based quality estimator to set processing switches. In mobile ISP, this logic is typically integrated in the Scene Detection (AI Scene Detection) module: bypass unified restoration for clear/low-ISO scenes; activate the corresponding restoration pathway for rain/fog/night scenes.

**Weather-Type Queries (天气类型查询)**
Core design in TransWeather: a set of learnable query vectors is introduced in the Transformer decoder, each corresponding to one weather degradation type (rain/fog/snow/raindrops). Through cross-attention with image features, the network automatically determines the dominant weather type in the current image among these queries, without external weather label input. This mechanism is principally similar to object detection queries in visual Transformers (DETR's object queries), and is a representative design that fuses "classification" and "restoration" within a single attention mechanism.

**Negative Transfer (负迁移)**
A harmful interference phenomenon in multi-task learning: conflicting optimization objectives between certain tasks cause joint training to hurt performance on some tasks compared to training each task alone. In unified image restoration, denoising (reducing high frequencies) and super-resolution (enhancing high frequencies) are the canonical negative-transfer task pair. Identifying and mitigating negative transfer is one of the core challenges in unified restoration model design. Mitigation techniques include: task grouping (group similar degradation types), gradient projection (PCGrad: remove gradient conflict components between tasks), and task-specific adapters.

---

## §9 Chapter Summary and Outlook

### 9.1 Technology Development Trajectory

The all-weather multi-degradation restoration technology covered in this chapter has undergone rapid iteration since 2021:

| Phase | Time | Representative method | Core breakthrough |
|---|---|---|---|
| Multi-task joint training | 2021–2022 | MPRNet, Uformer | Same architecture effective across tasks |
| Degradation-aware unified restoration | 2022 | AirNet, TransWeather | Contrastive learning / weather queries auto-perceive degradation type |
| Prompt-driven unified restoration | 2023 | PromptIR | First to surpass expert models on all tasks simultaneously |
| Diffusion-model unified restoration | 2023–2024 | DiffIR, WeatherDiffusion | Large perceptual quality improvement; generates high-frequency details |
| Large-scale pretraining | 2024+ | UniRestorer | Zero-shot generalization; text-driven degradation conditions |

### 9.2 Open Problems and Future Directions

1. **Real-scene generalization:** The domain shift between synthetic degradation data and real weather scenes is the biggest bottleneck today. Future directions include: more realistic physics-based degradation synthesis models (light transport simulation), and self-supervised/unsupervised training on unpaired real data.

2. **Extreme composite degradations:** Current methods suffer dramatic performance drops when rain + fog + low-light + motion blur appear simultaneously. How to decompose and restore strongly coupled composite degradations without degradation-type annotation is the core problem for next-generation unified restoration frameworks.

3. **Video temporal consistency:** Directly extending image-level unified restoration to video produces prominent inter-frame inconsistency. Video unified restoration models need to balance temporal modeling (optical flow alignment, temporal attention) with per-frame restoration quality.

4. **Large model deployment on edge devices:** Large-scale pretrained models such as UniRestorer (82M+ parameters) remain an engineering challenge for efficient deployment on mobile NPUs. Knowledge distillation (compressing large model knowledge into 5–10M parameter small models) is the most promising direction.

5. **Joint optimization with perception tasks:** In autonomous driving, the ultimate purpose of restoration models is to improve perception accuracy (object detection/segmentation), not human-visible PSNR. Restoration models optimized for perception tasks (Task-Driven Restoration) is an important research direction for automotive ISP (see Volume 4, Chapter 5).

---

## References

[1] Li, B., Liu, X., Hu, P., Wu, Z., Lv, J., & Peng, X. (2022). All-in-one image restoration for unknown corruption. CVPR, 17452–17462. — AirNet original paper; degradation contrastive learning + degradation-guided restoration; unified framework for arbitrary unknown degradations.
[2] Potlapalli, V., Zamir, S. W., Khan, S., & Khan, F. S. (2023). PromptIR: Prompting for all-in-one blind image restoration. NeurIPS, 36. — PromptIR original paper; visual prompt learning for unified image restoration; first to surpass expert models on all tasks simultaneously.
[3] Zamir, S. W., Arora, A., Khan, S., Hayat, M., Khan, F. S., Yang, M. H., & Shao, L. (2021). Multi-stage progressive image restoration. CVPR, 14821–14831. — MPRNet multi-stage progressive restoration; important baseline and precursor work for unified restoration.
[4] Wang, Z., Cun, X., Bao, J., Zhou, W., Liu, J., & Li, H. (2022). Uformer: A general U-shaped transformer for image restoration. CVPR, 17683–17693. — Uformer hierarchical Transformer unified restoration; demonstrates universality of Transformer architecture across degradation types.
[5] Chen, H., et al. (2022). TransWeather: Transformer-based restoration of images degraded by adverse weather conditions. CVPR. — TransWeather: first single-network Transformer unifying all weather degradations; weather-type query mechanism as core innovation.
[6] He, K., Sun, J., & Tang, X. (2011). Single image haze removal using dark channel prior. IEEE TPAMI, 33(12), 2341–2353. — Dark channel prior dehazing classic algorithm; traditional estimation baseline for the atmospheric scattering model; provides physical background for subsequent deep learning dehazing methods.
[7] Chen, Z., Badrinarayanan, V., Lee, C. Y., & Rabinovich, A. (2018). GradNorm: Gradient normalization for adaptive loss balancing in deep multitask networks. ICML, 794–803. — GradNorm gradient normalization; fundamental method for automatically balancing gradient magnitudes across tasks in multi-task joint training.
[8] Zamir, S. W., Arora, A., Khan, S., Hayat, M., Khan, F. S., & Yang, M. H. (2022). Restormer: Efficient transformer for high-resolution image restoration. CVPR, 5728–5739. — Restormer transposed attention original paper; reduces complexity from $O(H^2W^2)$ to $O(C^2)$; standard backbone for unified restoration frameworks like PromptIR.
[9] Xia, B., Zhang, Y., Wang, S., et al. (2023). DiffIR: Efficient diffusion model for image restoration. ICCV, 13095–13105. — DiffIR two-stage diffusion unified restoration; compact latent-space diffusion in 4–8 steps; diffusion model baseline for multi-task unified restoration.
[10] Wang, Z., Zhang, J., Chen, R., Wang, W., & Luo, P. (2024). Restoring vision in adverse weather conditions with patch-based denoising diffusion models. IEEE TPAMI, 46(4), 2346–2359. — Patch-based diffusion model for adverse weather restoration; explores generalization of diffusion models on real (non-synthetic) weather degradations; reference for real-scene validation in unified restoration.
[11] Zhang, H., et al. (2023). WeatherStream: Light transport automation of single image deweathering. CVPR. — WeatherStream real weather dataset; 150K frames of real weather images; benchmark for real-scene evaluation of all-weather restoration.
