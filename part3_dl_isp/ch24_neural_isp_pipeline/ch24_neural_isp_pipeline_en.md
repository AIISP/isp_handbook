# Part 3, Chapter 24: Neural ISP — End-to-End Pipeline Learning and the Neutral Rendering Paradigm

> **Scope:** This chapter surveys end-to-end learnable ISPs — their theoretical foundations, dominant architectures, and industrial deployments. At the center is the authors' design thesis: **a foundation ISP model should output perceptually authentic (neutral) sRGB, and stylistic rendering should be a separate, downstream stage.** This mirrors the LOG video paradigm in professional cinema and solves a structural contradiction that has plagued mobile ISP design for over a decade.
> **Prerequisites:** Ch01 (DL ISP Overview), Ch16 (Generative RAW-to-RGB), Part 4 Ch06 (Task-Driven ISP)
> **Audience:** ISP algorithm engineers, mobile imaging researchers, autonomous driving perception engineers

---

## §1 Theory and Motivation

### 1.1 Structural Limitations of the Traditional ISP Pipeline

The traditional image signal processor is a hand-crafted, expert-designed directed acyclic graph:

```
Sensor RAW (Bayer)
  │
  ├── DPC  (Defect Pixel Correction)
  ├── BLC  (Black Level Correction)
  ├── LSC  (Lens Shading Correction)
  ├── Demosaic
  ├── AWB  (Auto White Balance)
  ├── CCM  (Color Correction Matrix)
  ├── NR   (Noise Reduction)
  ├── EE   (Edge Enhancement / Sharpening)
  ├── Gamma / Tonemapping
  └── CSC  (Color Space Conversion) → sRGB / YUV
```

This architecture has three structural failure modes that no amount of per-module tuning can fully resolve:

**Failure 1 — Fragmented optimization objectives.** Each module is designed and tuned independently, optimizing a local metric (NR → SNR, EE → MTF50, CCM → ΔE). The global objective — final perceived image quality — is never explicitly optimized. Worse, upstream errors propagate and amplify: false colors introduced by demosaicing are further accentuated by the sharpening module downstream.

**Failure 2 — Limited scene adaptability.** The traditional ISP adapts to scenes through finite LUT tables (per-ISO, per-CCT) with linear interpolation between anchor points. The true scene space (illumination × noise level × motion × semantic content) is far too high-dimensional for finite state machines to cover adequately.

**Failure 3 — Style and fidelity are permanently coupled.** Color style (brand aesthetics, saturation preference, contrast curve) and content fidelity (color accuracy, detail preservation) are adjusted through the same set of parameters. Changing the CCM or gamma curve simultaneously alters both color accuracy and subjective appearance. There is no way to tune one without perturbing the other — a fundamental architectural limitation, not a tuning deficiency.

### 1.2 Neural ISP — A Unified Formulation

An end-to-end learnable ISP replaces the module chain with a single differentiable function $f_\theta$ mapping RAW input $\mathbf{x}$ to output image $\hat{\mathbf{y}}$:

$$\hat{\mathbf{y}} = f_\theta(\mathbf{x})$$

Training minimizes a global loss over a dataset of paired (RAW, reference sRGB) images:

$$\theta^* = \arg\min_\theta\, \mathbb{E}_{\mathbf{x},\mathbf{y}}\!\left[\mathcal{L}\!\left(f_\theta(\mathbf{x}),\, \mathbf{y}_\text{ref}\right)\right]$$

where $\mathbf{y}_\text{ref}$ is a paired reference image (typically a high-quality DSLR capture of the same scene).

| Dimension | Traditional ISP | Neural ISP |
|-----------|----------------|------------|
| Optimization target | Per-module local objective | Global perceptual / task objective |
| Scene adaptation | Finite LUT interpolation | Continuous function approximation |
| Error propagation | Accumulated and amplified | Jointly absorbed during training |
| Style control | Coupled into tuning parameters | Decoupled via conditioning vectors |
| Differentiability | None (no backpropagation) | Fully differentiable (task gradients flow back) |

### 1.3 The Fundamental Tension and the Authors' Thesis

> **The central argument of this chapter:** A Neural ISP foundation model should be designed to output *perceptually authentic (neutral) sRGB*. Stylistic rendering — brand aesthetics, artistic looks, user preference adjustments — belongs to a subsequent, independently deployable stage. This separation is not merely an engineering convenience; it is the architecturally correct design for the next decade of imaging systems.

This argument runs counter to the default practice in the mobile industry, where style and accuracy have historically been collapsed into a single tuned pipeline. We observe that two distinct rendering objectives exist, and that conflating them creates unavoidable compromises:

**Objective A — Perceptually Authentic Rendering**
- Minimizes the distance to physical ground truth (ΔE₀₀ < 2.0 on ColorChecker 24)
- Maximizes downstream information preservation for machine vision (mAP, segmentation IoU)
- Preserves reversibility: given known ISP metadata, the linear RAW signal is recoverable
- Analogy: **LOG encoding in cinema** — maximum dynamic range and color fidelity, designed for downstream grading

**Objective B — Perceptually Aesthetic Rendering**
- Maximizes human observer preference scores (NIMA, MOS)
- Embodies brand color identity (warm/cool bias, contrast curves, saturation preference)
- Deliberately departs from physical ground truth to achieve visual appeal
- Analogy: **Color grading** — applied *on top of* LOG footage to express directorial intent

Blau & Michaeli (CVPR 2018) **[3]** proved theoretically that these two objectives cannot be simultaneously optimal. The *Perception-Distortion Tradeoff* establishes a Pareto frontier: improving perceptual quality (human subjective score) necessarily increases distortion (PSNR/SSIM), and vice versa.

```
Perceptual Quality ↑
                   │  ·Diffusion/GAN outputs (high perception, high distortion)
                   │     ·· Pareto frontier
                   │          ·Neural ISP (neutral rendering zone)
                   │               ·PSNR-optimal (accurate but blurry)
                   └────────────────────────────────→ Distortion D ↑ (lower is better)
```

The correct engineering response to this tradeoff is not to pick a single operating point and claim it is optimal for all use cases. It is to **decouple the two objectives into separate, independently optimizable stages** — exactly the neutral-base + style-layer architecture we advocate.

---

## §2 Regression-Based Neural ISP — PyNet, LiteISPNet, and NTIRE

### 2.1 Task Definition and Datasets

The canonical regression-based Neural ISP task: given smartphone RAW $\mathbf{x}_\text{phone}$, learn $f_\theta$ such that output $\hat{\mathbf{y}}$ approximates a paired reference DSLR image $\mathbf{y}_\text{DSLR}$:

$$\mathcal{L} = \lambda_1 \|\hat{\mathbf{y}} - \mathbf{y}_\text{DSLR}\|_1 + \lambda_2 \mathcal{L}_\text{perceptual} + \lambda_3 \mathcal{L}_\text{SSIM}$$

**DPED dataset** (Ignatov et al., ICCV 2017): the first large-scale paired dataset for Neural ISP training.
- Capture setup: 4 smartphones + 1 Canon DSLR, synchronized multi-device capture
- ~6,000 paired scenes, several frames per scene
- Challenge: ~±2 pixel misalignment between phone and DSLR viewpoints

**Zurich RAW-to-DSLR (ZRR)** (Ignatov et al., CVPR Workshop 2020): the most widely used Neural ISP benchmark.
- Devices: Huawei P20 (Sony IMX586) → Canon EOS 5D Mark IV
- 46,839 training pairs, 1,204 test pairs
- Cropped to 448×448 patches during training

**NTIRE RAW-to-RGB Challenge** (annual CVPR Workshop, 2019–present): standardized benchmark used for cross-method comparison across the field. In 2022, a perceptual quality track was added alongside the distortion-minimization track — a clear signal of the community's recognition of the two-objective problem.

### 2.2 PyNet — The Multi-Scale Baseline

**PyNet** (Ignatov et al., CVPR Workshop 2020) **[16]** is the most widely cited Neural ISP baseline.

**Architecture**: a multi-level image pyramid decoder.

```
Input: Smartphone RAW [4-channel pack raw, H×W]
  │
  ├── Level 5 (H/16 × W/16): global color / luminance semantics
  ├── Level 4 (H/8  × W/8):  mid-frequency texture
  ├── Level 3 (H/4  × W/4):  fine-grained texture
  ├── Level 2 (H/2  × W/2):  edge enhancement
  └── Level 1 (H    × W):    detail refinement → sRGB output
```

Each level is trained independently before joint fine-tuning (**progressive training strategy**), preventing high-resolution levels from overfitting low-frequency signals in early epochs.

**Loss function**:
$$\mathcal{L}_\text{PyNet} = \underbrace{\|\hat{\mathbf{y}} - \mathbf{y}\|_1}_{L_1} + \underbrace{\sum_l \|\phi_l(\hat{\mathbf{y}}) - \phi_l(\mathbf{y})\|_2^2}_{\text{Perceptual (VGG)}} + \underbrace{\mathcal{L}_\text{color}}_{\text{Color consistency}}$$

**ZRR performance**: PSNR = 22.45 dB, SSIM = 0.80.

### 2.3 LiteISPNet — Alignment-Aware Lightweight Neural ISP

**LiteISPNet** (Zhang et al., ICCV 2021) **[17]** addresses the most practical bottleneck: the 1–3 pixel misalignment in training pairs causes blurry outputs when $L_1$/$L_2$ losses are directly applied.

**Global Color Mapping (GCM) module**: a learnable 3×3 linear transform applied before the backbone, aligning the RAW color distribution to the reference color space:

$$\mathbf{x}' = \text{GCM}(\mathbf{x};\, W_\text{GCM}), \quad W_\text{GCM} \in \mathbb{R}^{3\times3}$$

$W_\text{GCM}$ is estimated from image content — effectively a jointly learned white-balance + CCM.

**Key findings**:
- Correcting alignment error yields +1.2 dB PSNR, more than doubling model capacity
- A 1.1M-parameter backbone outperforms networks 10× larger once alignment is resolved
- **Lesson: data quality (alignment accuracy) matters more than model capacity**

ZRR performance: PSNR = 23.67 dB (+1.22 dB over PyNet), with 90% fewer parameters.

### 2.4 AWNet — Wavelet-Attention Dual-Branch Network

**AWNet** (Liu et al., ECCV Workshop 2020, NTIRE 2020 winner) **[18]** uses a dual-branch strategy:

- **Wavelet branch**: processes high-frequency content (texture, edges) in the wavelet domain
- **Global branch**: processes low-frequency color/luminance in the spatial domain

Cross-branch attention fuses features at multiple scales:

$$\mathbf{F}_\text{out} = \text{Attn}(\mathbf{F}_\text{wavelet},\, \mathbf{F}_\text{global}) \cdot \mathbf{F}_\text{global} + \mathbf{F}_\text{wavelet}$$

The wavelet transform is lossless and invertible, enabling 4× spatial downsampling without discarding high-frequency information — substantially reducing computation on the feature-extraction path.

### 2.5 NTIRE Challenge — Year-by-Year Evolution

| Year | Representative Method | Key Innovation | PSNR@ZRR |
|------|-----------------------|---------------|---------|
| 2019 | MWRCAN | Multi-scale residual channel attention | 20.3 |
| 2020 | AWNet | Wavelet dual-branch + cross-attention | 22.1 |
| 2021 | LiteISPNet | GCM alignment + lightweight backbone | 23.7 |
| 2022 | ELNet | Edge-aware loss + joint optimization | 24.1 |
| 2023 | DiffISP | Diffusion prior + regression refinement | 24.5 (perception track) |

The introduction of a dedicated **perceptual quality track** in 2022 — running alongside the distortion-minimization track — marks the field's formal recognition that these are fundamentally different optimization objectives.

---

## §3 Perceptually Neutral sRGB — Definition, Metrics, and the Tradeoff

### 3.1 Definition of Perceptually Neutral sRGB

**Perceptually neutral sRGB** is an ISP output satisfying:

1. **Color accuracy**: neutral gray scenes produce $(R, G, B)$ equal; mean ΔE₀₀ across ColorChecker 24 patches < 2.0
2. **Luminance accuracy**: for a uniformly spaced luminance staircase, the output luminance response follows the standard sRGB gamma (IEC 61966-2-1) **[1]**
3. **No aesthetic bias**: no imposed warm/cool toning, contrast preference, or saturation deviation
4. **Near-reversibility**: given known ISP parameters (or RAW metadata), the linear RAW-domain signal is approximately recoverable
5. **High bit depth**: stored at ≥ 10-bit (12-bit or 16-bit float recommended), preserving sufficient quantization precision for downstream tone mapping and LUT operations

This stands in contrast to *perceptually aesthetic sRGB*, which deliberately departs from physical ground truth to maximize human preference scores — at the cost of increased ΔE and reduced reversibility.

### 3.2 Quantitative Metrics for Neutral Rendering

**Metric 1 — Color accuracy (CIEDE2000 ΔE₀₀)**:

$$\Delta E_{00} = \sqrt{\left(\frac{\Delta L'}{k_L S_L}\right)^2 + \left(\frac{\Delta C'}{k_C S_C}\right)^2 + \left(\frac{\Delta H'}{k_H S_H}\right)^2 + R_T}$$

Neutral rendering target: mean ΔE₀₀ < 2.0 on ColorChecker 24 (human perception threshold ≈ 1.0 JND **[2]**).

**Metric 2 — Relative luminance error (RLE)**:

$$\text{RLE} = \frac{1}{N}\sum_{i=1}^{N} \left|\frac{L'_\text{out}(i) - L'_\text{ref}(i)}{L'_\text{ref}(i)}\right|$$

Measured against the 18-step gray wedge defined in ISO 15739 **[2]**.

### 3.3 Why the Neutral Base Requires High Bit Depth

This constraint is frequently overlooked in traditional ISP engineering, but becomes critical once the neutral base is decoupled from the style layer. The argument is straightforward: any downstream operation applied to the neutral base — tone curve adjustments, 3D LUT mapping, color grading — operates on the quantization grid inherited from the neutral base. Reducing that grid prematurely forecloses precision that cannot be recovered.

**Quantization error cascades through downstream rendering**

When a traditional ISP outputs 8-bit sRGB, gamma encoding compresses the full dynamic range onto a uniform 0–255 quantization grid. If this 8-bit result serves as the style layer's input, any subsequent operation (curve lift, LUT lookup, tone shift) compounds quantization errors already present in the neutral base, producing visible banding and gradient loss in shadows and gradients.

Consider a +0.5 EV shadow lift applied by the style layer:
- **8-bit input**: the shadow zone (luminance 0–15, ≈4.7% of range) contains only ~12 usable code values
- **12-bit input**: the same luminance zone contains ~200 usable code values — **16× more precision**

The downstream style layer cannot invent precision that was discarded upstream.

**Direct analogy to LOG video**

The cinema industry resolved this same problem in the 2000s by moving from 8-bit to 10-bit LOG encoding. The reason is identical:

| Format | Bit depth | Effective dynamic range | Grading headroom |
|--------|-----------|------------------------|-----------------|
| 8-bit sRGB | 8-bit | ~6 stops | Minimal (<15 steps in sky/shadow) |
| 10-bit LOG (S-Log3 / Log-C) | 10-bit | 15+ stops | Standard professional grading |
| 12-bit RAW | 12-bit | 12–14 stops | High (DI / professional color) |
| 16-bit linear (EXR) | 16-bit float | Effectively unbounded | VFX / compositing standard |

A neutral ISP base targeting professional-grade downstream style rendering should match at least the headroom of 10-bit LOG.

**3D LUT sampling density is directly constrained by bit depth**

Style rendering is typically implemented via a 3D LUT with $N^3$ nodes. For a standard $33^3$ LUT, the sampling interval across an input range of $[0,\, 2^B - 1]$ is:

$$\Delta_\text{LUT} = \frac{2^B - 1}{N - 1}$$

- **8-bit input**: $\Delta = 255/32 \approx 8$ code values between adjacent LUT nodes — 8 uninterpolated steps per color axis
- **12-bit input**: $\Delta = 4095/32 \approx 128$ — but color variation is continuous; trilinear interpolation between nodes is highly accurate
- **16-bit float input**: interpolation precision is bounded only by floating-point representation

In practical terms: **high bit-depth input eliminates the banding and color contour artifacts** that appear when an aggressive style LUT is applied to an 8-bit neutral base.

**Recommended bit-depth specifications for the neutral base**

| Use case | Recommended bit depth | Storage format | Notes |
|----------|-----------------------|----------------|-------|
| Consumer real-time preview | 10-bit | P010 / YUV 10-bit | Minimum for live style preview |
| Professional still photography | 12-bit | DNG 12-bit linear | Standard Lightroom / Capture One workflow |
| Cinema / high-end video | 12-bit LOG | ProRes 4444 / ARRIRAW | Industry color grading standard |
| Neural ISP internal representation | 16-bit float | FP16 tensor | Full inference precision; quantize at output |
| Scientific / industrial inspection | 16-bit linear | TIFF 16-bit | Maximum quantization, lossless |

**Design rule**: the neutral base should target **FP16 internally during inference → 12-bit at output storage**. 8-bit output is appropriate only for immediate display, not as input to a style rendering stage. Neural ISP training losses should be computed in the high-bit-depth representation to prevent quantization noise from corrupting gradient signals.

**Metric 3 — Hue deviation (ΔH)**:
Isolates hue rotation from luminance/saturation changes. Measured as the angular displacement of each ColorChecker patch in the CIELAB $a^*b^*$ plane. Target: |ΔH| < 5°.

### 3.3 The Perception-Distortion Tradeoff

Blau & Michaeli (CVPR 2018) **[3]** proved that for any restoration algorithm, the achievable (perception quality P, distortion D) pair is bounded by a Pareto frontier:

$$P \geq g(D), \quad g(\cdot) \text{ monotonically decreasing}$$

**What this means for ISP design:**
- **Distortion minimum** (highest PSNR): output is the conditional expectation $\mathbb{E}[\mathbf{y}|\mathbf{x}]$ — pixel-accurate but visually blurry
- **Perception maximum**: output follows the natural image distribution — visually sharp but pixel-deviant (GAN/diffusion outputs)
- **Neutral rendering**: a specific operating point on the Pareto frontier where color accuracy (low ΔE) is prioritized over visual sharpness

The neutral rendering zone is neither the PSNR-optimal point nor the perception-optimal point. It is the zone that best preserves the information content of the original scene — maximizing what can be recovered by subsequent processing stages.

---

## §4 The Neutral-Base + Style-Layer Paradigm

### 4.0 Technical Paradigm vs. Commercial Paradigm — A Necessary Distinction

Before examining the architecture in detail, it is necessary to draw a clear line between two design routes that appear superficially similar but are fundamentally different in both intent and generalizability.

**The commercial paradigm (Xiaomi Leica Authentic Moment M9 mode as the representative case)**

Xiaomi trained a RAW-to-RGB style transfer network on hundreds of thousands of actual Leica M9 photographs, producing a model that renders smartphone captures with Leica M9 color characteristics. This is a legitimate and deliverable product experience — and a meaningful artifact of a brand licensing partnership.

Viewed from the perspective of technical generalizability, however, this route has fundamental limitations:
- **Non-reproducible**: it requires hundreds of thousands of photographs from the target camera system — a resource unavailable to most developers, research institutions, and novel sensor platforms
- **Single-style lock-in**: a model trained on M9 photographs outputs only M9 style; supporting a new look requires new data collection and full retraining of the entire pipeline
- **Non-composable**: there is no mechanism to combine styles, interpolate between looks, or apply personalized adjustments from the same base representation
- **Commercial dependency**: the definition of "correct style" is controlled by the brand partner, leaving the technology team with no independent evolution path

**The technical paradigm (the architecture this book advocates)**

```
Commercial paradigm:
  RAW ──[single coupled network]──→ Leica M9-style sRGB
              ↑
     Requires M9 photo data; produces only one style

Technical paradigm:
  RAW ──[Foundation ISP]──→ Neutral sRGB (high bit depth)
                                      │
                         ┌────────────┼────────────┐
                         ↓            ↓            ↓
                  Brand style vec  User embedding  Task adapter
                  (Leica / HB / …)  (personal)   (detection / seg)
```

The central claim of the technical paradigm: **the Foundation ISP does exactly one thing — map RAW to a physically grounded, high-bit-depth, neutral sRGB. Style is the concern of whoever is downstream. It is not the foundation model's job.**

| Dimension | Commercial paradigm | Technical paradigm |
|-----------|--------------------|--------------------|
| Cost of a new style | Re-collect data + re-train Foundation | Train only a new Style Layer vector |
| Number of supported styles | Bounded by data collection capacity | Unbounded (vector space is interpolable) |
| Multi-task support | Difficult (one network, one output form) | Natural (same base serves all downstreams) |
| Interpretability | Black box (why this color?) | Explicit (style = inspectable vector offset) |
| Generalizability | Restricted to partner platforms | Any camera, any scene, any downstream task |

This is not a dismissal of the commercial route — in specific product contexts, end-to-end brand style replication is a sound engineering decision. **But the choice of technical architecture should not be influenced by the appeal of commercial outcomes.** Neutral-base + style-layer decoupling is the more general, more scalable, and more maintainable technical architecture. It is the long-term correct direction.

### 4.1 The Authors' Design Thesis (Restated Clearly)

> **We argue that the next generation of imaging systems should be built on a two-stage architecture:**
>
> **Stage 1 (Foundation ISP model):** A neural ISP trained to produce perceptually authentic, neutral sRGB — color-accurate, unbiased, reversible. This is the "ground truth" rendering layer.
>
> **Stage 2 (Style rendering layer):** A separately trained, independently deployable module that maps neutral sRGB to a target stylistic output — brand look, user preference, artistic filter, or task-specific adaptation.
>
> Style and accuracy have been conflated in traditional ISPs because the hardware was incapable of running two inference passes. That constraint no longer exists. The architectural separation we describe is not aspirational — it is already present in every leading smartphone imaging system, in various stages of maturity. The field simply has not yet made this separation explicit and principled.

**The cinema analogy:**

```
Cinema workflow (LOG video paradigm):
  Shoot → LOG encoding (neutral, maximum dynamic range)
                  ↓
          Color grade (add directorial / brand style)

Neural ISP neutral-base paradigm:
  RAW → Foundation ISP (neutral sRGB, maximum accuracy)
                  ↓
          Style rendering (brand look / user preference / task adaptation)
```

The reason LOG encoding works is that it makes no irreversible decisions about style at the moment of capture. Every bit of information is preserved. The colorist — or in our case, the downstream style module — has complete creative freedom starting from a known, consistent, physically grounded base.

The same logic applies to Neural ISP. A foundation model that outputs neutral sRGB gives every downstream consumer — human editor, brand style engine, detection network, generative model — the same clean, consistent, information-rich starting point.

### 4.2 Formal Framework: Neutral Rendering Regularization in Uni-ISP

**Uni-ISP** (Ma et al., CUHK, arXiv 2024) **[4]** provides the most complete academic formalization of the neutral-base + style-decoupled architecture.

**Core idea**: Camera-specific style is injected via a learnable device embedding vector $\mathbf{e}_\text{cam}$. When this vector is set to zero ($\mathbf{e}_\text{cam} = \varnothing$), the network degenerates into a standard $\text{XYZ} \to \text{sRGB}$ transform — mathematically neutral rendering.

**Neutral Rendering Regularization (NRR) loss**:

$$\mathcal{L}_\text{NRR} = \|\underbrace{s(\mathbf{I}_a)}_{\text{standard sRGB}} - \underbrace{g(\mathbf{I}_a,\, \varnothing)}_{\text{zero-embedding output}}\|_1 + \|\underbrace{s^{-1}(\mathbf{L}_a)}_{\text{standard inverse}} - \underbrace{h(\mathbf{L}_a,\, \varnothing)}_{\text{inverse zero-embedding}}\|_1$$

where $s(\cdot)$ is the standard sRGB↔XYZ color transform, $g(\cdot, \mathbf{e})$ is the forward ISP network conditioned on device embedding $\mathbf{e}$, and $h(\cdot, \mathbf{e})$ is its inverse.

The NRR loss anchors the $\mathbf{e}_\text{cam}=\varnothing$ behavior to the IEC 61966-2-1 sRGB standard, while allowing non-zero device embeddings to learn arbitrary camera-specific style deviations.

**Experimental results** (MAE↓, ZRR test set):

| Configuration | MAE ↓ | ΔE₀₀ ↓ |
|--------------|--------|---------|
| Without NRR | 0.0412 | 3.18 |
| With NRR | **0.0371 (−9.9%)** | **2.54 (−20.1%)** |

The improvement confirms that anchoring to neutral rendering does not reduce the model's ability to learn device-specific style — it actually improves the representation quality by providing a well-grounded reference frame.

### 4.3 FourierISP — Frequency-Domain Style-Structure Decoupling

**FourierISP** (He et al., AAAI 2024) **[5]** implements the two-stage architecture in the frequency domain:

$$\hat{\mathbf{y}} = \mathcal{F}^{-1}\!\left[\underbrace{f_\text{style}(|\mathcal{F}(\mathbf{x})|)}_{\text{Amplitude spectrum → color/tone}} \cdot \underbrace{e^{j\angle\mathcal{F}(\mathbf{x})}}_{\text{Phase spectrum preserves structure}}\right]$$

**Key insight**: the phase spectrum of the Fourier transform carries structural information (edges, shapes, spatial layout); the amplitude spectrum carries global tonal and color information. These map cleanly onto our two-stage separation:

- **Structure branch**: operates on phase spectrum → demosaicing, denoising, detail preservation
- **Style branch**: operates on amplitude spectrum → color/tone mapping

Because the two branches are independent, **swapping the Style branch weights changes the rendering style without affecting image structure quality**. This is the neural equivalent of swapping a color grade while keeping the edit.

### 4.4 ISPDiffuser — Diffusion-Based Style Decoupling

**ISPDiffuser** (Zheng et al., arXiv 2025) **[6]** models RAW-to-sRGB as a conditional diffusion process with explicit stage separation:

1. **Luminance structure reconstruction** (deterministic): $\hat{\mathbf{y}}_L = f_\text{struct}(\mathbf{x}_\text{raw})$ — recovers luminance/structure
2. **Color style sampling** (stochastic diffusion): $\hat{\mathbf{y}}_{ab} \sim p(\mathbf{y}_{ab}|\hat{\mathbf{y}}_L,\, \mathbf{c}_\text{style})$ — samples color in CIELAB $a^*b^*$ channels conditioned on a style vector

This decomposition mirrors the HVS's separate luminance (Y) and chrominance (Cb, Cr) processing channels. The style vector $\mathbf{c}_\text{style}$ can be set to zero (neutral → standard XYZ→sRGB color) or conditioned on brand embeddings, user exemplar images, or semantic labels.

### 4.5 Samsung Modular Neural ISP

**Modular Neural ISP** (Liang et al., Samsung Research, 2021) **[7]** demonstrates the paradigm at production scale:

```
RAW → [AWB module] → [CCM module] → [Tonemapping module] → sRGB
         ↑ param p₁      ↑ param p₂      ↑ param p₃
                   ↑ Style controller
              (user preference label → parameter set {p₁, p₂, p₃})
```

Each module is a differentiable function. A style controller network maps user preference labels ("warm / high-contrast / saturated") to a parameter set that instantiates the corresponding rendering. At inference, swapping style parameters takes negligible compute overhead.

This architecture underpins Samsung's Expert RAW "neutral baseline" mode — described in their official documentation as a mode designed to "hold a more neutral baseline that you can refine rather than correct."

---

## §5 Perception-Driven ISP for Autonomous Driving

### 5.1 The Irreconcilable Conflict Between Aesthetics and Accuracy

Autonomous driving poses an ISP optimization problem that is qualitatively different from consumer photography:

| Dimension | Consumer ISP | Perception-Driven ISP |
|-----------|-------------|----------------------|
| Optimization objective | Human preference (NIMA/MOS) | Detection mAP, segmentation IoU |
| Noise handling | Aggressive smoothing (visual cleanliness) | Preserve high-frequency detail useful for classification |
| Sharpening | Moderate (avoid haloing) | High — edges are critical for detectors **[8]** |
| Color saturation | Medium–high (brand aesthetics) | Medium–low (reduce domain shift) |
| Dynamic range | Local tone mapping (visual appeal) | Preserve global linearity (protect weak-signal targets) |

An empirical study by Shermeyer et al. (J. Imaging 2023) **[9]** found:
- Tuning sharpening alone improved pedestrian detection mAP by **+14.43%**
- Contrast adjustment produced ±10% mAP swings across different detection architectures
- The ISP configuration that maximized aesthetic quality scores was *not* the configuration that maximized detection accuracy

This confirms that the perception-aesthetic tradeoff is not merely theoretical — it has immediate, measurable consequences for system-level performance.

### 5.2 AdaptiveISP — Reinforcement Learning for Perception-Optimal ISP

**AdaptiveISP** (NeurIPS 2024) **[10]** uses deep RL to select the optimal ISP module combination and parameters per frame:

**State**: per-frame image features (luminance histogram + edge density + color moments)
**Action**: select which ISP modules to activate and their parameter values
**Reward**: downstream object detector mAP (measured by YOLOv8)

**Key findings**:
- Most frames only need 2–3 active ISP modules to achieve optimal detection performance
- Complex HDR scenes require the full pipeline; simple outdoor scenes can skip most processing
- Single-frame inference latency < 1ms on Jetson AGX

The RL agent learns a session-specific policy: for a given camera and deployment environment, it discovers the minimal ISP processing that maximizes downstream task accuracy — without any human-defined quality metric.

### 5.3 Design Principles for Perception-Oriented ISP

**Principle 1 — Information preservation over visual beautification.**
Any irreversible information compression in the ISP (aggressive denoising, highlight clipping, low-bit quantization) may eliminate weak signals that are critical for downstream perception tasks. The design objective is to maximize information content available for feature extraction, not to maximize human perceptual quality.

**Principle 2 — Differentiable ISP enables end-to-end joint optimization.**
If the ISP is fully differentiable, gradients from the detector loss can propagate back to ISP parameters, enabling joint end-to-end optimization:

$$\theta^*_\text{ISP}, \phi^*_\text{det} = \arg\min_{\theta, \phi} \mathcal{L}_\text{det}\!\left(f_\phi(f_\theta(\mathbf{x}_\text{raw})),\, \mathbf{y}_\text{label}\right)$$

**Principle 3 — The Tesla FSD extreme case.**
Tesla FSD V12 replaced the full perception stack (from camera pixels to control outputs) with a single end-to-end neural network **[11]**. The ISP output feeds directly into the neural network with no intermediate human-aesthetic optimization. "Image quality" is defined entirely by what the downstream network learns to be useful — human aesthetics are irrelevant.

This is the logical extreme of perception-driven ISP design: the ISP exists not to produce images that humans find pleasing, but to produce representations that neural networks find informative. The neutral-base paradigm naturally supports this use case — a neutral, accurate representation is the most information-rich input a downstream model can receive.

### 5.4 ISP-Agnostic Representations (DiR, CVPR 2024)

**DiR** (Guo et al., CVPR 2024) **[12]** learns ISP-agnostic feature representations through self-supervised learning — features that remain stable across different ISP configurations. The method improves generalization across object detection, blind image restoration, and instance segmentation.

This result provides important support for the neutral-base paradigm: a neutral ISP that maps RAW to a physically grounded sRGB produces features that are more generalizable than an aesthetically tuned ISP, which introduces arbitrary, ISP-specific statistical biases into the feature space.

---

## §6 Industry Practice — Neutral Base and Look Filters

### 6.1 Industry Convergence on Three-Layer Architecture

Across Xiaomi × Leica, OPPO × Hasselblad, vivo × ZEISS, Apple, and Samsung, high-end mobile ISP design has converged on a three-layer rendering architecture that directly instantiates the neutral-base + style-layer paradigm:

```
Layer 1: Neutral / Authentic Base Rendering
  → Maximizes color accuracy (ΔE₀₀ < 2.0), physically grounded
  → Suitable for RAW export, machine vision, downstream editing

Layer 2: Brand Style Layer (Look / Filter)
  → Overlays brand-specific color aesthetics (tone, contrast, saturation curves)
  → Multiple user-selectable presets

Layer 3: Neural Style Simulation (highest compute cost, selective activation)
  → Full RAW-to-RGB neural network trained on authentic device captures
  → Simulates a specific physical camera system's rendering characteristics
```

This convergence is not accidental. It reflects the practical discovery — through years of tuning and user research — that style and accuracy should be managed separately.

### 6.2 Xiaomi × Leica — Three Generations of Evolution

**Generation 1 (Xiaomi 12S Ultra, 2022)**:
- **Leica Authentic Look**: neutral base layer — color-accurate, with intentional mild vignetting (preserving Leica lens character)
- **Leica Vibrant Look**: brand style layer — enhanced saturation and contrast
- Implementation: jointly calibrated CCM + multi-segment gamma curves, tuned by Leica engineers against physical reference measurements

**Generation 2 (Xiaomi 13/14/15 series)**:
- 13 Leica Looks preset styles (three base tones × contrast variants)
- AI night scene enhancement integrated with Neural ISP denoising model

**Generation 3 (Xiaomi 17 Ultra by Leica, December 2025) — Leica Authentic Moment (徕卡一瞬)**:

This generation introduces a fully realized Layer 3 (neural style simulation) — the most complete instantiation of style-layer separation in current consumer products.

- **M3 mode (black-and-white film simulation)**: simulates the Leica 2025 MONOPAN 50 black-and-white film stock
  - Not a simple desaturation; models the film's full spectral response function and tonal curve
  - Per-pixel grain distribution correlated with scene luminance — every image produces a unique grain signature
  - Correctly maps distinct hues to distinct grayscale values (shallow blue vs. deep blue are separated, not merged)

- **M9 mode (CCD color simulation)**: replicates the rendering characteristics of the Leica M9 (full-frame CCD)
  - Training data: **hundreds of thousands** of actual Leica M9 photographs captured by Xiaomi
  - Architecture: on-device RAW-to-RGB Style Transfer neural network (not a post-capture filter)
  - Key property: daylight white balance locked by design — the color temperature bias is intentional and scene-dependent
  - Semantic understanding: the network infers object-light relationships to prevent luminance inversion artifacts **[13]**

**Architectural significance**: The M9 mode plants style inside the RAW-to-RGB mapping function itself, not as a post-processing overlay. This is the technically cleanest realization of Layer 3 neural style simulation in any shipping consumer product.

### 6.3 Apple — Photographic Styles and ProRAW

Apple's approach prioritizes **user-visible control over the style layer** while maintaining a well-defined neutral base:

**iPhone 13–15 (First-generation Photographic Styles)**:
- 5 presets: Standard (neutral base), Rich Contrast, Vibrant, Warm, Cool
- **Critical design decision**: styles are applied during capture by the ISP, not as post-processing filters
  - Advantage: the ISP can make spatially intelligent adjustments (e.g., warm skin tones without warming the sky)
  - Cost: styles on iPhone 13–15 were baked in at capture time and could not be re-edited

**iPhone 16+ (Next-generation Photographic Styles)**:
- 14+ presets, including a new **"Neutral"** undertone — the most explicitly labeled neutral base in any consumer product
- **Major advance: styles are re-editable after capture** — compressed intermediate rendering parameters are retained in the DNG container
- Standard mode recalibrated to a "more naturally faithful base"

**ProRAW** (iPhone 12 Pro and later):
- A linear DNG that preserves the computational photography pipeline results (Smart HDR, spatial noise processing) in a near-neutral form
- The closest implementation of "pure neutral base for downstream editing" in the consumer market
- Used by professional photographers as the starting point for their own style rendering

### 6.4 OPPO × Hasselblad — Natural Color Calibration

OPPO's collaboration with Hasselblad most explicitly articulates the two-layer architecture at the product communication level:

**Hasselblad Natural Color Calibration** (neutral base layer):
- Reference device: Hasselblad X2D 100C medium-format camera
- Calibration process: shoot standard color targets across multiple illuminants; optimize OPPO's CCM + tone curves to minimize ΔE₀₀ relative to X2D reference captures
- Available in Pro Mode as "Natural Color" rendering

**Hasselblad Master Mode** (brand style layer):
- Actively matches the X2D's characteristic color rendering — including Hasselblad's historically recognized slight blue-green offset
- XPAN cinematic widescreen mode, Cinestill 800T film simulation (Layer 3 neural style)

**Find X9 eight-channel spectral sensor** (2024):
- 24 spectral measurements per frame enable physically accurate AWB (no statistical assumptions)
- Provides the hardware foundation for neutral base rendering — neutral AWB is necessary for neutral sRGB output

### 6.5 vivo × ZEISS — ZEISS Natural Color

**ZEISS Natural Color** (neutral base): "Professional optimization of tones faithfully reproduces what the human eye sees for the ultimate in fidelity" — product documentation — with explicit ΔE₀₀ targeting as the design metric.

**ZEISS Vivid** (style layer): enhanced saturation, with particular optimization for human skin tones and natural greens.

**vivo V3 chip**: the ZEISS Natural Color computation is hardware-accelerated in the on-chip ISP, enabling real-time neutral rendering without software overhead.

### 6.6 Samsung — Expert RAW and 3D ISP

**Standard camera AI mode** (aesthetic priority): scene semantic segmentation (sky / people / vegetation / food) → per-region independent color optimization. The output is explicitly designed to maximize casual user appeal.

**Expert RAW** (neutral base tool): Samsung developed a new AI-based 3D ISP — a neural pipeline that "produces raw data that looks very natural when users load it in editing apps like Adobe Lightroom" **[14]**.

Official documentation describes Expert RAW as designed to "hold a more neutral baseline that you can refine rather than correct" — a direct statement of the neutral-base philosophy we advocate.

**The Samsung case makes an important general point**: even a manufacturer known for maximally aesthetic, "punchy" output has built a separate neutral-base mode for professional users. The demand for both layers is real, and the separation is architecturally necessary.

---

## §7 Implementation

### 7.1 Neural ISP Training Pipeline

```python
import torch
import torch.nn as nn
import torch.nn.functional as F


class GlobalColorMapping(nn.Module):
    """Learnable 1×1 conv that aligns RAW pack color distribution to reference space."""
    def __init__(self, in_channels=4, out_channels=3):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=True)

    def forward(self, x):
        return self.conv(x)


class LiteUNet(nn.Module):
    """Lightweight U-Net backbone (LiteISPNet style)."""
    def __init__(self, in_channels=3, out_channels=3, base_ch=32):
        super().__init__()
        self.enc = nn.Sequential(
            nn.Conv2d(in_channels, base_ch, 3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(base_ch, base_ch * 2, 3, stride=2, padding=1), nn.ReLU(inplace=True),
        )
        self.dec = nn.Sequential(
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False),
            nn.Conv2d(base_ch * 2, base_ch, 3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(base_ch, out_channels, 1),
        )

    def encode(self, x): return self.enc(x)
    def decode(self, f): return self.dec(f)


def perceptual_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Placeholder perceptual loss (L1 in pixel space). Replace with VGG features in production."""
    return F.l1_loss(pred, target)


class NeuralISP(nn.Module):
    """
    Two-stage Neural ISP with neutral base output
    and optional style conditioning.
    """
    def __init__(self, style_dim=64):
        super().__init__()
        # Global Color Mapping: aligns RAW color distribution to reference space
        self.gcm = GlobalColorMapping(in_channels=4, out_channels=3)
        # Backbone: lightweight U-Net for structure/detail restoration
        self.backbone = LiteUNet(in_channels=3, out_channels=3)
        # Style injection via FiLM conditioning (scale + bias)
        self.style_encoder = nn.Linear(style_dim, 2 * 64)

    def forward(self, raw_pack, style_vec=None):
        """
        Args:
            raw_pack:  [B, 4, H//2, W//2]  — packed RGGB raw
            style_vec: [B, style_dim] or None  (None → neutral base mode)
        """
        x = self.gcm(raw_pack)                  # color-aligned intermediate
        features = self.backbone.encode(x)

        if style_vec is not None:
            scale, bias = self.style_encoder(style_vec).chunk(2, dim=-1)
            features = features * (1 + scale[..., None, None]) \
                                + bias[..., None, None]

        return self.backbone.decode(features)    # neutral or styled sRGB


def neutral_rendering_regularization(model, raw_imgs, standard_srgb):
    """
    NRR loss: when style_vec=None, output should approximate
    the standard XYZ→sRGB transform (IEC 61966-2-1 physical ground truth).
    """
    neutral_output = model(raw_imgs, style_vec=None)
    return nn.L1Loss()(neutral_output, standard_srgb)


def train_step(model, optimizer, batch):
    raw, target_srgb, neutral_ref, style_label = batch

    # Primary loss: learn device-specific style
    output = model(raw, style_vec=style_label)
    loss_style = nn.L1Loss()(output, target_srgb) + \
                 0.1 * perceptual_loss(output, target_srgb)

    # NRR: anchor neutral-embedding behavior to physical ground truth
    loss_nrr = neutral_rendering_regularization(model, raw, neutral_ref)

    loss = loss_style + 0.2 * loss_nrr
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    return loss.item()
```

### 7.2 Pack RAW Preprocessing

```python
def pack_raw_bayer(raw_bayer, cfa_pattern='RGGB'):
    """
    Pack single-channel Bayer RAW into 4-channel [R, Gr, Gb, B] tensor.
    Input must be BLC-corrected and normalized to [0, 1].
    """
    H, W = raw_bayer.shape
    pack = torch.zeros(4, H // 2, W // 2)
    if cfa_pattern == 'RGGB':
        pack[0] = raw_bayer[0::2, 0::2]   # R
        pack[1] = raw_bayer[0::2, 1::2]   # Gr
        pack[2] = raw_bayer[1::2, 0::2]   # Gb
        pack[3] = raw_bayer[1::2, 1::2]   # B
    return pack
```

### 7.3 Mobile Deployment Tradeoffs

| Configuration | Parameters | ZRR PSNR | Latency (Cortex-X3) | Use case |
|--------------|-----------|---------|---------------------|---------|
| PyNet | 47M | 22.45 dB | ~180ms | Offline post-processing |
| LiteISPNet | 1.1M | 23.67 dB | ~12ms | Real-time preview |
| MobileISP (INT8) | 0.8M | 22.98 dB | ~6ms | 30fps video ISP |
| GCM-only | 0.01M | 21.5 dB | <1ms | Ultra-low-power mode |

The style layer adds negligible overhead: a 64-dim FiLM conditioning vector requires ~0.01ms for evaluation, enabling real-time style switching with no perceptible latency cost.

---

## §8 Future Directions

### 8.1 Foundation RAW Models as ISP Backbones

See Ch07 (RAW Foundation Models). A RAW-domain foundation model pretrained on millions of diverse scenes can serve as the backbone for neutral-base rendering with minimal per-device fine-tuning (hundreds of paired samples rather than tens of thousands). This dramatically reduces the cost of deploying Neural ISP on new sensor platforms.

### 8.2 Sensor-Parameter-Conditioned ISP

**ParamISP** (CVPR 2024) **[15]** conditions the ISP network on EXIF metadata (ISO, shutter speed, aperture, focal length), enabling accurate generalization to unseen ISO and exposure combinations without per-configuration calibration. This is the parametric equivalent of the device embedding vector in Uni-ISP: instead of style, the conditioning vector encodes capture parameters.

### 8.3 Unified Foundation ISP for Human and Machine Vision

**UniISP** (arXiv 2026) **[19]** proposes a single ISP framework optimizing for both human visual quality and downstream machine vision accuracy through a Hybrid Attention Module + Feature Adapter. This is the most direct technical instantiation of the argument that neutral rendering maximizes utility across both use cases — a neutral base is neither maximally aesthetic nor maximally task-specific, but it is the most informative starting point for both.

### 8.4 User-Personalized Neutral Bases

The next frontier is extending the device embedding in Uni-ISP to a **user preference embedding** — learned from individual editing histories (Lightroom adjustments, filter selections, manual color grading) to define a personalized "neutral reference" for each user. A professional photographer's neutral base differs from a casual user's, and both differ from a machine vision system's. Personalized neutral rendering makes this difference explicit and learnable.

---

## §9 References

[1] IEC 61966-2-1, "Multimedia systems — Colour management — Default RGB colour space (sRGB)", 1999. https://www.iec.ch/

[2] Sharma G. et al., "The CIEDE2000 color-difference formula", *Color Research & Application*, 2005.

[3] Blau Y. & Michaeli T., "The Perception-Distortion Tradeoff", *CVPR 2018*. https://arxiv.org/abs/1711.06077

[4] Ma Y. et al., "Uni-ISP: Unifying the Learning of ISPs from Multiple Cameras", *arXiv*, 2024. https://arxiv.org/abs/2406.01003

[5] He A. et al., "Enhancing RAW-to-sRGB with Decoupled Style Structure in Fourier Domain", *AAAI 2024*. https://dl.acm.org/doi/10.1609/aaai.v38i3.27985

[6] Zheng Q. et al., "ISPDiffuser: Learning RAW-to-sRGB Mappings with Texture-Aware Decoupled Framework", *arXiv 2025*. https://arxiv.org/abs/2503.19283

[7] Liang Z. et al., "Modular Neural Image Signal Processing", Samsung Research, 2021. https://github.com/SamsungLabs/modular_neural_isp

[8] Shermeyer J. et al., "Impact of ISP Tuning on Object Detection", *Journal of Imaging*, 2023. DOI: 10.3390/jimaging9120260

[9] Li Y. et al., "Overview and Empirical Analysis of ISP Parameter Tuning for Visual Perception in Autonomous Driving", *PMC*, 2021.

[10] Jiang W. et al., "AdaptiveISP: Learning an Adaptive Image Signal Processor for Object Detection", *NeurIPS 2024*. https://arxiv.org/abs/2410.22939

[11] Tesla FSD Chip Architecture, WikiChip Fuse, 2019. https://fuse.wikichip.org/news/2707/

[12] Guo C. et al., "Learning Degradation-Independent Representations for Camera ISP Pipelines", *CVPR 2024*. https://openaccess.thecvf.com/content/CVPR2024/html/Guo_Learning_Degradation-Independent_Representations_for_Camera_ISP_Pipelines_CVPR_2024_paper.html

[13] IT之家, "小米17 Ultra by Leica评测", December 2025. https://www.ithome.com/0/908/142.htm

[14] Samsung Newsroom, "Experts Talk: Expert RAW App", 2022. https://news.samsung.com/global/experts-talk-collaborating-on-the-galaxy-s22-series-expert-raw-app

[15] Nam S. et al., "ParamISP: Learned Forward and Inverse ISPs using Camera Parameters", *CVPR 2024*. https://cvpr.thecvf.com/virtual/2024/poster/29264

[16] Ignatov A. et al., "PyNET: Replacing Mobile Camera ISP with a Single Deep Learning Model", *CVPR Workshop 2020*. https://arxiv.org/abs/2002.05509

[17] Zhang Y. et al., "Learning RAW-to-sRGB Mappings with Inaccurately Aligned Supervision", *ICCV 2021*.

[18] Liu J. et al., "AWNet: Attentive Wavelet Network for Image ISP", *ECCV Workshop 2020*. https://arxiv.org/abs/2010.10546

[19] Zhang et al., "UniISP: A Unified ISP Framework for Both Human and Machine Vision", *arXiv 2026*. https://arxiv.org/abs/2605.07359

---

## §10 Glossary

| Term | Definition |
|------|------------|
| **Perceptually Neutral sRGB** | ISP output minimizing ΔE₀₀ with no aesthetic bias; the LOG-video equivalent for still photography |
| **Perception-Distortion Tradeoff** | CVPR 2018 theoretical result: human preference quality and pixel-level distortion metrics (PSNR/SSIM) cannot be simultaneously optimized |
| **Neutral Rendering Regularization (NRR)** | Uni-ISP loss term anchoring zero-embedding network output to the IEC 61966-2-1 standard sRGB transform |
| **Pack RAW** | 4-channel RGGB tensor formed by separating Bayer sub-channels; standard Neural ISP input format |
| **Global Color Mapping (GCM)** | LiteISPNet preprocessing module: learnable 3×3 linear transform aligning RAW color distribution to reference space |
| **Style-Structure Decoupling** | Decomposing RAW-to-RGB into two independent sub-problems: structure/detail restoration and color/tone style rendering |
| **Perception-Driven ISP** | ISP designed to maximize downstream machine vision task accuracy (mAP, IoU) rather than human aesthetic quality |
| **Leica Authentic Moment (徕卡一瞬)** | Xiaomi 17 Ultra's on-device neural RAW-to-RGB style simulation; M9 mode trained on hundreds of thousands of actual Leica M9 photographs |
| **Photographic Styles** | Apple iPhone ISP-time style system; from iPhone 16, styles are re-editable post-capture via retained rendering parameters |
| **NTIRE RAW-to-RGB Challenge** | Annual CVPR Workshop benchmark for cross-method Neural ISP comparison; added a perceptual quality track from 2022 |
| **AdaptiveISP** | NeurIPS 2024: deep RL agent selecting per-frame ISP module combinations to maximize downstream detection mAP |
| **LOG encoding** | Cinema paradigm: camera output preserves maximum dynamic range and color fidelity for downstream color grading; direct analogy to neutral-base Neural ISP |
