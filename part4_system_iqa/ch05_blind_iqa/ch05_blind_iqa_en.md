# Part 4, Chapter 05: Blind Image Quality Assessment (NR-IQA)

> **Pipeline position:** Post-ISP quality gating
> **Prerequisites:** IQA chapter (Part 4), Ch DL Overview
> **Reader path:** DL Researcher, System Designer

---

## §1 原理 (Theory)

### The Blind IQA Problem

In mass production there is no "reference image" — phones on the assembly line produce photos with no paired DSLR ground truth to compare against. This is why Blind IQA (No-Reference Image Quality Assessment) is more important than FR PSNR/SSIM in engineering practice: the model must examine a single image and deliver a quality verdict, exactly like a factory quality inspector.

Image Quality Assessment (IQA) is categorized by the availability of a reference image. Understanding this taxonomy helps select the right tool:

- **Full-Reference (FR-IQA):** A pristine reference image is available (e.g., PSNR, SSIM **[S1]**, LPIPS) — used during algorithm R&D, not applicable in production.
- **Reduced-Reference (RR-IQA):** Only statistical features of the reference are available — a transitional approach that sees little practical use.
- **No-Reference / Blind IQA (NR-IQA):** No reference image is available. The model must assess quality from the distorted image alone — the primary workhorse for production quality control, online filtering, and user experience evaluation.

The objective of a Blind IQA model is to predict human Mean Opinion Scores (MOS). This goal itself determines the difficulty: human perception is subjective, content-dependent, and scene-varying. Approximating this target with statistical features or neural networks inevitably carries limitations, especially when crossing distribution boundaries (e.g., training on JPEG compression artifacts, deploying on ISP rolling-shutter artifacts).

### Classical NR Methods

**BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator, Mittal et al., 2012).** BRISQUE extracts natural scene statistics from the Mean Subtracted Contrast Normalized (MSCN) domain. The key observation is that MSCN coefficients of undistorted natural images follow a Generalized Gaussian Distribution (GGD), and distortions shift this distribution. BRISQUE fits a GGD to the MSCN coefficients and their pairwise products, producing a 36-dimensional feature vector. A support vector regressor (SVR) maps these features to a MOS prediction.

MSCN computation:
```
I_hat(i,j) = I(i,j) - μ(i,j)
I_mscn(i,j) = I_hat(i,j) / (σ(i,j) + C)
```
where μ and σ are local mean and standard deviation estimated with a 7×7 Gaussian window, and C = 1 is a stability constant.

BRISQUE is fast (< 5 ms on CPU) and requires no training data from deep networks, making it suitable as a lightweight first-stage filter.

**NIQE (Natural Image Quality Evaluator, Mittal et al., 2013).** NIQE fits a Multivariate Gaussian (MVG) model to MSCN features from a corpus of natural undistorted images. Quality is measured as the statistical distance (Mahalanobis distance) between the MVG of the test image patches and the reference MVG. NIQE is fully unsupervised — it requires no MOS annotations.

### Deep IQA Evolution

**NIMA (Neural Image Assessment, Talebi & Milanfar, 2018).** NIMA fine-tunes a pre-trained CNN (InceptionV3 or MobileNet) on the AVA aesthetic dataset and the TID2013 technical quality dataset. Unlike prior deep methods that predict a single MOS value, NIMA predicts the full distribution of human ratings (a 10-class histogram). The loss is Earth Mover's Distance (EMD) between predicted and ground-truth rating distributions:

```
EMD(p, q) = sqrt( (1/r) · Σ_k |CDF_p(k) - CDF_q(k)|^r )
```

with r = 2. This is more informative than MSE on the mean score because it captures the variance of human opinion. The mean of the predicted distribution serves as the final quality score.

**HyperIQA (Su et al., 2020).** HyperIQA addresses the problem that distortion severity is content-dependent: noise in a textured region is less visible than the same noise in a smooth sky region. The network uses a hyper-network that generates content-aware local quality prediction weights from a global content understanding module. A ResNet backbone extracts multi-scale features; a hyper-network head produces filters for a local quality predictor that scores local patches; the patch scores are aggregated to a global MOS prediction.

**MUSIQ (Multi-Scale Image Quality Transformer, Ke et al., 2021).** MUSIQ uses a Vision Transformer (ViT) backbone that accepts multi-scale image patches. Unlike ViT which requires fixed-resolution input, MUSIQ uses a spatial and scale embedding to allow flexible input sizes. This is important for IQA because quality artifacts are scale-dependent (blocking at low frequency, noise at high frequency). MUSIQ achieves state-of-the-art SRCC on multiple benchmarks simultaneously.

**CLIP-IQA (Wang et al., 2023).** CLIP-IQA leverages the zero-shot capabilities of Contrastive Language-Image Pre-training (CLIP). The quality score is computed as:

```
score = softmax( CLIP(image) · [CLIP("good photo"), CLIP("bad photo")] )[0]
```

The cosine similarity between the image embedding and two antonym text prompts provides a quality signal without any IQA-specific training. CLIP-IQA+ fine-tunes the model on IQA datasets for improved performance, but the zero-shot version already achieves competitive results on several benchmarks.

### Training Datasets

| Dataset | Distortion Types | Images | MOS Range | Notes |
|---------|-----------------|--------|-----------|-------|
| LIVE | 5 synthetic | 779 | 0–100 | Widely used baseline |
| TID2013 | 24 distortions | 3,000 | 0–9 | Most diverse distortions |
| KADID-10k | 25 distortions | 10,125 | 1–5 | Largest synthetic dataset |
| KonIQ-10k | Authentic | 10,073 | 1–5 | Real-world web images |
| SPAQ | Authentic (mobile) | 11,125 | 0–100 | Smartphone camera output |

For ISP applications, SPAQ and KonIQ-10k are more relevant than synthetic datasets because they contain real-world mobile camera artifacts.

### Generative Model Quality Evaluation: FID

**FID (Frechet Inception Distance, Heusel et al., 2017)** is the standard distribution-level metric for evaluating generated image quality, widely applied to GANs, diffusion models, and other generative pipelines. Unlike per-image quality scores, FID measures the **distributional gap** between a set of generated images and a set of real images in a feature space:

$$\text{FID} = \| \mu_r - \mu_g \|^2 + \text{Tr}\left( \Sigma_r + \Sigma_g - 2\left(\Sigma_r^{1/2} \Sigma_g \Sigma_r^{1/2}\right)^{1/2} \right)$$

where $(\mu_r, \Sigma_r)$ and $(\mu_g, \Sigma_g)$ are the mean and covariance of the Inception-v3 pool3-layer feature distributions of real and generated images respectively. **Lower FID indicates higher generative quality** (greater distribution overlap).

**ISP-relevant applications:**
- **Generative ISP evaluation:** When an ISP pipeline contains a generative module (e.g., super-resolution diffusion model, generative denoising), FID assesses the overall perceptual realism and distributional consistency of the output image set, complementing per-image PSNR/SSIM metrics.
- **Synthetic training data quality verification:** ISP model training commonly uses synthetic RAW-RGB pairs; FID can quantify the distributional gap between synthetic datasets and real camera output, guiding data augmentation strategy.
- **Portrait/night-scene generation mode evaluation:** Commercial smartphone AI portrait reconstruction and night-scene generation output requires FID + MOS dual evaluation rather than PSNR alone.

**Important caveats:** FID requires a sufficiently large sample size (typically >= 5,000 images) to produce a stable estimate; with small samples FID variance is high. FID is not appropriate for per-scene single-image quality judgment — it is only suitable for algorithm/model-level horizontal comparison.

### Open-Source Libraries and Implementation Resources

In practice, engineers do not need to implement these methods from scratch. The following open-source libraries provide production-grade NR-IQA implementations:

#### IQA-PyTorch

**IQA-PyTorch** (https://github.com/chaofengc/IQA-PyTorch) is the most comprehensive open-source IQA library, covering 40+ FR-IQA and NR-IQA methods under a unified API, fully integrated with the PyTorch ecosystem:

```python
import pyiqa

# Create evaluation models (NR-IQA: no reference image needed)
brisque_model = pyiqa.create_metric('brisque')
nima_model    = pyiqa.create_metric('nima')
clipiqa_model = pyiqa.create_metric('clipiqa')
musiq_model   = pyiqa.create_metric('musiq')

# Score a single image
import torch
from PIL import Image
import torchvision.transforms as T

img = T.ToTensor()(Image.open('test.jpg')).unsqueeze(0)  # [1,3,H,W]

score_brisque = brisque_model(img)   # lower is better (default direction)
score_nima    = nima_model(img)      # higher is better
score_clipiqa = clipiqa_model(img)   # higher is better

# Batch scoring — returns Tensor of shape [B]
scores = musiq_model(img)
```

Key NR-IQA methods available in IQA-PyTorch:

| Method | Type | Notes |
|--------|------|-------|
| BRISQUE | Hand-crafted | Fastest; suitable for online filtering |
| NIQE | Hand-crafted (unsupervised) | No MOS labels needed; good baseline |
| ILNIQE | Hand-crafted | Improved NIQE variant |
| NIMA | CNN (ResNet/InceptionV3) | Predicts full score distribution |
| HyperIQA | CNN + hyper-network | Content-aware quality prediction |
| MUSIQ | Vision Transformer | Multi-scale; flexible input resolution |
| CLIP-IQA / CLIP-IQA+ | CLIP (VLP) | Zero-shot or few-shot quality assessment |
| Q-Bench / Q-Instruct | LLaVA-style MLLM | Multi-modal LLM-based evaluation |
| DBCNN | Dual-stream CNN | Handles synthetic + authentic distortions |
| PaQ-2-PiQ | CNN | Local-to-global quality awareness |

The library's unified `lower_better` flag convention eliminates the need to memorize score direction for each method when comparing across models.

#### Q-Bench / Q-Instruct (Multi-modal LLM IQA)

The Q-Bench series (https://github.com/Q-Future/Q-Bench) elevates IQA to an open-ended question-answering task using Multi-modal Large Language Models (MLLMs):

```python
# Q-Instruct supports natural language quality description
# Prompt: "Describe the quality issues in this image."
# Output: "The image has noticeable motion blur, higher noise in the right region, and a warm color cast."
```

For ISP tuning, this is particularly valuable: beyond a scalar quality score, Q-Instruct provides **interpretable quality descriptions** that help engineers identify the source of quality issues. Integrated into IQA-PyTorch as `pyiqa.create_metric('qinstruct')`.

#### Other Useful Open-Source Resources

| Tool | URL | Highlights |
|------|-----|-----------|
| **piq** | https://github.com/photosynthesis-team/piq | PyTorch, FR+NR, lightweight |
| **image-quality** | https://github.com/ocampor/image-quality | Python, BRISQUE/NIQE, easy to use |
| **scikit-image** | https://scikit-image.org/ | SSIM/PSNR, standard scientific implementation |

#### Recommended ISP Engineer Workflow

```
Fast filter (CPU, < 5ms):  BRISQUE / NIQE
        ↓ ambiguous images
Deep scoring (GPU, < 50ms): HyperIQA / CLIP-IQA+
        ↓ scores near threshold
Manual review + Q-Instruct quality description
        ↓ annotation collection
Periodic NR model fine-tuning (§2 Calibration)
```

---

### Correlation Metrics

Model performance is measured by correlation with human MOS:

- **SRCC (Spearman Rank Correlation Coefficient):** Measures monotonic correlation between predicted scores and MOS. Range [-1, 1], higher is better. Robust to outliers.
- **PLCC (Pearson Linear Correlation Coefficient):** Measures linear correlation after a logistic nonlinear mapping. Range [-1, 1], higher is better.
- **KRCC (Kendall Rank Correlation Coefficient):** Measures concordance of pairwise rankings. More conservative than SRCC, computationally expensive.

For ISP quality gating, SRCC is the most operationally relevant metric because the deployment use case is ranking or thresholding outputs.

---

## §2 标定 (Calibration)

### Fine-tuning to Target Distribution

NR-IQA models trained on generic datasets exhibit domain shift when applied to a specific camera or ISP pipeline. The calibration procedure:

1. **Capture a calibration set:** Collect 200–500 images from the target ISP pipeline spanning the expected quality range (varied lighting, scenes, ISP parameter settings).
2. **Collect MOS annotations:** Present images to 20+ human raters using a paired comparison or absolute category rating protocol. Aggregate via Bradley-Terry model or simple averaging.
3. **Fine-tune the backbone:** Initialize from a pre-trained NR-IQA model (NIMA or HyperIQA), freeze the backbone, and fine-tune only the regression head on the calibration set. If the calibration set is large enough (>500 images), fine-tune all layers with a low learning rate (1e-5).
4. **Validate SRCC** on a held-out set from the same distribution.

### Domain Adaptation: Synthetic to Real

Models trained on synthetic distortion datasets (LIVE, TID2013) tend to fail on real ISP artifacts because ISP degradations (color casts, lens shading, rolling-shutter) are outside the training distribution. Options:

- **Unsupervised domain adaptation:** Align feature distributions using Maximum Mean Discrepancy (MMD) loss between source (synthetic) and target (real ISP) domains.
- **Self-supervised pre-training:** Pre-train on real ISP images with contrastive objectives (e.g., DINO), then fine-tune on a small annotated set.
- **Curriculum learning:** Start training on synthetic distortions, gradually introduce real ISP artifacts.

**Why synthetic-to-real gap is large in ISP contexts.** Standard benchmark distortions (JPEG compression, additive white Gaussian noise, linear blur) are applied globally to clean reference images with known distortion parameters. Real ISP degradations differ in three key ways: (1) they are *spatially heterogeneous* — lens vignetting concentrates at the periphery, rolling-shutter skew is confined to fast-moving regions; (2) they are *interdependent* — ISP gain amplifies noise that is then partially removed by temporal NR, leaving structured residual noise the synthetic pipeline never produces; (3) ISP quality is partly determined by *algorithmic decisions* (demosaic filter choice, tone-mapping curve), not just physical degradation. A model that achieved SRCC 0.93 on LIVE may drop to 0.68 when evaluated on the same camera brand's ISP output.

**Practical workflow for ISP-specific calibration.** A validated three-step protocol used in mobile camera programs:

```
Step 1 — Distribution Audit
  Collect 1,000+ raw ISP output images (8 scene categories × 3 light levels).
  Run baseline model; compute per-category SRCC.
  If any category SRCC < 0.70 → that category needs domain-specific annotation.

Step 2 — Targeted MOS Collection
  For each failing category, run a paired-comparison study: 20 raters × 100 pairs.
  Convert pair wins to continuous MOS via Bradley-Terry model.
  Target: 200–500 annotated images per failing category.

Step 3 — Selective Fine-tuning
  Freeze all backbone layers up to the penultimate block.
  Fine-tune final block + regression head with learning rate 1e-5 for 20 epochs.
  Early-stop on held-out SRCC (10% split from calibration set).
  Re-audit: if worst-category SRCC ≥ 0.80, deploy; otherwise extend annotation.
```

**MMD-based unsupervised adaptation — implementation note.** When MOS annotation budget is exhausted, MMD adaptation provides a no-annotation alternative. The feature-space alignment loss is:

$$\mathcal{L}_{\text{MMD}} = \left\| \frac{1}{n_s}\sum_{i=1}^{n_s}\phi(\mathbf{f}_i^s) - \frac{1}{n_t}\sum_{j=1}^{n_t}\phi(\mathbf{f}_j^t) \right\|^2_\mathcal{H}$$

where $\phi$ maps features to a reproducing kernel Hilbert space (RBH kernel with bandwidth $\sigma$ set by the median heuristic), $n_s$ and $n_t$ are source and target batch sizes, and $\mathbf{f}^s, \mathbf{f}^t$ are intermediate features from the backbone. In practice, applying MMD on the penultimate layer features of HyperIQA with a batch of 64 unlabeled real ISP images improves cross-domain SRCC by approximately 0.05–0.08 with no additional labels.

**SRCC monitoring cadence.** After deployment, SRCC should be re-validated whenever: (a) the ISP algorithm version is updated (new demosaic, NR, or tone-mapping), (b) a new sensor module is integrated, or (c) more than 90 days have elapsed. A SRCC drop exceeding 0.05 on the internal validation set triggers a re-calibration cycle.

---

## §3 调参 (Tuning)

### Threshold Selection for Pass/Fail Gating

The NR score must be mapped to a binary decision (accept/reject) for use as an ISP output gate. Threshold selection involves a precision-recall trade-off:

- **Low threshold (permissive):** More images pass. False accept rate increases. Use when retaking a photo is costly (e.g., medical imaging).
- **High threshold (strict):** More images are rejected. False reject rate increases. Use when image quality is critical (e.g., production quality control).

To set the threshold, plot the ROC curve on the calibration set using ground-truth MOS ≥ 3.5 as the "good quality" label. Select the operating point by the F1 score or by a cost-weighted criterion.

### Ensemble: Speed-Accuracy Balance

A practical ISP quality gate uses a two-stage ensemble:

1. **Stage 1 — BRISQUE (fast filter):** Score all images in < 5 ms on CPU. Reject images with BRISQUE score > threshold_reject (clearly bad quality). Pass images with score < threshold_accept (clearly good quality). Send ambiguous images to Stage 2.
2. **Stage 2 — Deep NR model:** Run the deep model (e.g., HyperIQA or CLIP-IQA) on ambiguous images only. This reduces average inference time to near the Stage 1 cost while maintaining deep-model accuracy on difficult cases.

---

## §4 Artifacts

### Domain Shift

**Description:** NR models trained on synthetic distortions (JPEG, additive noise, blur) assign incorrect scores to real ISP artifacts (lens flare, color moiré, chromatic aberration, rolling-shutter skew). The model's feature space has never seen these patterns during training, so it either ignores them or maps them to incorrect quality predictions.

**Mitigation:** Fine-tune on real ISP data (§2 Calibration). Monitor SRCC drift over time as the ISP pipeline changes; retrigger fine-tuning when drift exceeds a threshold (e.g., SRCC drops by > 0.05).

### Semantic Leakage

**Description:** Deep NR models may learn to score based on scene content rather than image quality. For example, a model might assign high scores to images of sunsets because sunset images in the training set received high MOS ratings, regardless of image quality. This is a form of shortcut learning.

**Mitigation:** Evaluate the model on a semantic-stratified test set: compute per-scene-category SRCC and verify that quality rankings are consistent across scene types. Use scene-debiased training: sample training batches such that each scene category contributes equally.

**Quantifying semantic leakage.** A practical diagnostic: group your evaluation set into scene categories (portrait, landscape, indoor, night, text) and compute within-category SRCC. If a model achieves overall SRCC = 0.90 but per-category SRCC varies from 0.62 (industrial objects) to 0.95 (portrait), the high overall number is inflated by category-level score bias rather than genuine quality sensitivity. The MOS prediction error for long-tail scene types can reach ±1.2 on a 5-point scale in published mobile camera datasets.

**ISP-specific content bias examples:**
- **Night scene over-reward:** Models trained predominantly on daytime data consistently over-score night shots because night shots are rare in training sets and the few examples that appear were well-exposed and thus labeled high-MOS. Aggressive ISP NR in night mode produces "plasticky" texture that MOS raters penalize but models reward as noise-free.
- **Portrait under-penalty:** Portrait images with background bokeh often receive high MOS from human raters regardless of slight subject softness. NR models learn this correlation and fail to penalize ISP demosaic fringing around fine hair detail.
- **Text sharpness insensitivity:** Document and whiteboard captures require very high sharpness MOS from professional users, but consumer training sets contain few such images; models systematically under-score text-sharpness quality issues.

### ISP-Specific Artifact Failure Cases

Beyond general domain shift and semantic leakage, ISP pipelines produce several artifact types that specifically confuse standard NR-IQA models:

**AI denoising smearing ("plasticky skin").** Modern CNN-based or diffusion-based ISP NR modules sometimes over-smooth fine texture (skin pores, fabric weave) while preserving edges, creating a "plastic" appearance that humans find unnatural. BRISQUE and NIQE assign these images *high quality scores* (low BRISQUE, low NIQE distance) because the images are statistically cleaner than natural images — the MSCN coefficient distribution becomes sharper and more Gaussian, moving toward the natural image prior rather than away from it. This is a fundamental failure mode of NSS-based NR metrics for AI-enhanced ISP.

**HDR tone-mapping halo.** Local tone-mapping operators (LTM) used in ISP HDR pipelines can produce luminance halos around high-contrast edges. The halo is a structured artifact at the boundary of bright objects against dark backgrounds. HyperIQA, trained on globally-distorted images (uniform noise, blur), has limited sensitivity to spatially local structured halos because its random-patch training strategy does not systematically sample edge-boundary regions.

**Color moiré from demosaicking.** Fine-pitched patterns (fabric, display grids at a distance) interacting with the Bayer CFA produce colored aliasing patterns. These are high-frequency chromatic artifacts. BRISQUE operates on the grayscale luminance channel only and is completely blind to color moiré. Models need to either operate in full color space or include a dedicated chroma-artifact detection branch.

**Lens shading correction artifacts.** Imperfect LSC calibration leaves a residual vignette (darkened corners) or introduces over-correction that brightens corners beyond the scene's natural luminance. NR models interpret corner darkness as MSCN deviation but may mistake it for a "content" characteristic (e.g., vignette framing) rather than an ISP calibration error.

**Mitigation strategy for ISP-specific artifacts:** Build an ISP-artifact-specific test harness:

1. Curate ~50 examples per artifact type (AI smearing, HDR halo, color moiré, LSC residual).
2. Assign binary labels: artifact present / absent (simpler and more reliable than full MOS for rare artifact categories).
3. Measure area under ROC (AUC) per artifact type for any candidate NR model.
4. For artifact types where AUC < 0.70, augment training with targeted synthetic examples of that artifact type before relying on the model for quality gating.

---

## §5 VLM-IQA — Vision-Language Model Driven Quality Assessment

### Paradigm Shift: From Regression to Visual Question Answering

The NR-IQA methods in §1 (BRISQUE, NIMA, HyperIQA, MUSIQ, CLIP-IQA) all formulate quality assessment as a **scalar regression task**: input an image, output a single float aligned to MOS. This paradigm has three core limitations:

1. **Lack of interpretability**: a score cannot explain *why* quality is poor (noise? blur? chromatic aberration?)
2. **Single perceptual dimension**: a scalar cannot distinguish "uniformly low quality" from "severe local artifact"
3. **Task-specific training required**: each method needs dedicated training on IQA annotation datasets

The rise of Multi-modal Large Language Models (MLLMs) introduces a new paradigm: elevating quality assessment to a **Visual Question Answering (VQA) task**, answering open-ended quality questions within a unified language space.

### Q-Bench (ICLR 2024)

**Q-Bench** (Wu et al., ICLR 2024) systematically evaluates the capability boundary of MLLMs (LLaVA, InstructBLIP, etc.) on low-level visual perception tasks.

**Core finding:** Contemporary MLLMs have general VQA capability but exhibit significant gaps in low-level quality perception. For simple Yes/No questions like "Is this photo blurry?", pre-trained MLLMs achieve only 62–68% accuracy — worse than a dedicated BRISQUE filter.

**Yes/No question paradigm:** Q-Bench decomposes low-level IQA into three question formats:

| Format | Example | Evaluation target |
|--------|---------|-------------------|
| **Binary (Yes/No)** | "Does this image have severe noise?" | Single distortion dimension perception |
| **Open description** | "Describe the quality issues in this image." | Combined low-level perception + language |
| **Comparison** | "Which image has better quality?" | Ranking consistency |

**Q-Instruct dataset:** To close the low-level perception gap, Q-Bench constructs Q-Instruct: 200K+ image–instruction pairs, each containing an image, a quality question, and a detailed answer. After fine-tuning on Q-Instruct, LLaVA-7B achieves 83%+ Yes/No accuracy on quality queries.

**Engineering value:** For ISP tuning engineers, Q-Bench provides a new diagnostic path — instead of abstract scores, the model returns actionable distortion descriptions:

```
Input image → MLLM → "Motion blur detected, high noise in right region, cool color cast"
                   → Specific distortion localization, guiding ISP parameter adjustment
```

### Q-Align (ICML 2024)

**Q-Align** (Wu et al., ICML 2024) solves the remaining challenge from Q-Bench: how to make an MLLM produce **continuous quality scores quantitatively comparable to MOS**?

**Core insight:** An MLLM's next-token prediction head naturally outputs a softmax probability distribution over the vocabulary. Q-Align maps the 5-level MOS scale to discrete tokens, then uses the **weighted sum of the output probabilities of these 5 tokens as the continuous quality score**:

$$\text{score} = \sum_{l \in \mathcal{L}} p(l) \cdot v(l)$$

where $\mathcal{L} = \{\text{bad, poor, fair, good, excellent}\}$, $v(l)$ is the numeric value of each level (1–5), and $p(l)$ is the model's output probability for that token. No separate regression head is attached — quality scoring emerges naturally from the language modeling capability.

**Alignment strategy:** Q-Align fine-tunes LLaVA on a mixed IQA/VQA/AVA dataset, teaching the model to express quality judgments using the 5-level vocabulary while preserving its instruction-following capability.

**Performance:** Q-Align surpasses dedicated NR-IQA methods on multiple benchmarks:

| Benchmark | HyperIQA SRCC | MUSIQ SRCC | CLIP-IQA+ SRCC | **Q-Align SRCC** |
|-----------|-------------|-----------|---------------|----------------|
| KonIQ-10k | 0.917 | 0.916 | 0.895 | **0.940** |
| SPAQ | 0.911 | 0.918 | — | **0.941** |
| LIVE-FB | 0.859 | 0.661 | — | **0.888** |

**Unified multi-task framework:** The same Q-Align model handles Image Quality Assessment (IQA), Video Quality Assessment (VQA), and Aesthetic Assessment (AAA) by switching text prompts — no separate model architecture per task.

### VLM-IQA in ISP Engineering Context

| Category | Representative | Advantage | Limitation | ISP Use Case |
|----------|---------------|-----------|------------|-------------|
| Hand-crafted NR | BRISQUE, NIQE | CPU < 5ms, no GPU | Weak generalization | Online Stage-1 filter |
| Deep CNN/ViT NR | HyperIQA, MUSIQ | High accuracy, cross-domain | GPU required | Offline quality evaluation |
| CLIP-based NR | CLIP-IQA+ | Zero-shot, flexible | Imprecise text alignment | Exploratory evaluation |
| **VLM-IQA** | **Q-Bench, Q-Align** | **Interpretable descriptions + high accuracy** | **Slow inference (> 500ms)** | **Tuning diagnostics, quality report generation** |

> **Scope note:** Q-Bench's multi-modal IQA benchmark methodology directly connects to **Ch82 (IQA Engineering System)** — an automated testing pipeline can call Q-Align to generate batch quality reports, supplementing or replacing traditional human subjective evaluation sessions.

---

## §6 Evaluation

### Published Results

SRCC on standard benchmarks (higher is better).

Note: LIVE = LIVE IQA Database (synthetic distortions); LIVE-FB = LIVE In the Wild Facebook Dataset (authentic in-the-wild images). These are **two different datasets**.

| Method | LIVE(syn) SRCC | TID2013 SRCC | KADID SRCC | KonIQ SRCC | LIVE-FB SRCC | Year |
|--------|----------------|-------------|-----------|-----------|-------------|------|
| BRISQUE | 0.939 | 0.571 | 0.528 | 0.665 | — | 2012 |
| NIQE | 0.908 | 0.322 | 0.374 | 0.531 | — | 2013 |
| NIMA | 0.919 | 0.564 | — | — | — | 2018 |
| HyperIQA | 0.962 | 0.840 | 0.845 | 0.917 | 0.859 | 2020 |
| MUSIQ | 0.911 | 0.773 | 0.875 | 0.916 | 0.661 | 2021 |
| CLIP-IQA+ | 0.953 | 0.864 | 0.894 | 0.895 | — | 2022 |
| Q-Align | — | — | — | **0.940** | **0.888** | 2024 |
| TOPIQ | — | — | — | **0.942** | 0.876 | 2024 |

Key observations:
- BRISQUE performs well on LIVE (single distortion type) but degrades sharply on multi-distortion (TID2013) and authentic (KonIQ) datasets. The SRCC gap between LIVE (0.939) and KonIQ (0.665) quantifies the cost of relying on NSS assumptions that break under real camera artifacts.
- Deep models (HyperIQA, MUSIQ, CLIP-IQA+) generalize far better across dataset types because they learn data-driven quality representations rather than hand-crafted statistical priors.
- CLIP-IQA+ achieves strong cross-dataset performance without dataset-specific architecture design — a direct consequence of CLIP's large-scale vision-language pretraining.
- Q-Align (ICML 2024) surpasses all dedicated NR-IQA methods on authentic datasets (KonIQ, SPAQ) while simultaneously providing interpretable quality descriptions.
- TOPIQ (IEEE TIP 2024) achieves SRCC 0.942 on KonIQ-10k, marginally surpassing Q-Align; inference time (~50 ms GPU) is far faster than Q-Align (~500 ms), making it the best speed-accuracy operating point for offline batch quality evaluation.

### Cross-Dataset Generalization

The most important evaluation for ISP deployment is **cross-dataset generalization**: train on one dataset, evaluate on another. Models that overfit to a single dataset's annotation protocol fail in production. Evaluate:

- Train on KADID-10k (synthetic), test on KonIQ-10k (authentic). SRCC < 0.6 indicates poor generalization.
- Train on SPAQ (mobile), test on camera-specific captures. This is the most realistic proxy for ISP deployment.

---

## §7 Code

See the companion notebook `ch_blind_iqa_code.ipynb` for:

- Generating 10 test images with varying quality levels (GT + 4 distortions at 2 intensities)
- Implementing BRISQUE-inspired MSCN features and computing a quality score
- Scoring all images and plotting score vs. distortion level
- Comparing BRISQUE feature ranking vs. PSNR ranking using SRCC
- Published comparison table and three practical exercises

---

## References

- Mittal, A., Moorthy, A. K., & Bovik, A. C. (2012). **No-reference image quality assessment in the spatial domain.** IEEE Transactions on Image Processing.
- Mittal, A., Soundararajan, R., & Bovik, A. C. (2013). **Making a "completely blind" image quality analyzer.** IEEE Signal Processing Letters.
- Talebi, H., & Milanfar, P. (2018). **NIMA: Neural image assessment.** IEEE Transactions on Image Processing.
- Su, S., Yan, Q., Zhu, Y., et al. (2020). **Blindly assess image quality in the wild guided by a self-adaptive hyper network.** CVPR 2020.
- Ke, J., Wang, Q., Wang, Y., Milanfar, P., & Yang, F. (2021). **MUSIQ: Multi-scale image quality transformer.** ICCV 2021.
- Wang, J., Chan, K. C. K., & Loy, C. C. (2023). **Exploring CLIP for assessing the look and feel of images.** AAAI 2023.
- Zhang, W., Ma, K., Yan, J., Deng, D., & Wang, Z. (2020). **Blind image quality assessment using a deep bilinear convolutional neural network.** IEEE TCSVT. *(DBCNN)*
- Zhang, W., Ma, K., Yang, J., et al. (2021). **Uncertainty-aware blind image quality assessment in the laboratory and wild.** IEEE TIP. *(UNIQUE)*
- **IQA-PyTorch** (chaofengc et al., 2022). Unified perceptual image quality assessment toolbox and benchmark. https://github.com/chaofengc/IQA-PyTorch
- Wu, H., Zhang, E., Liao, L., et al. (2024). **Q-Bench: A Benchmark for General-Purpose Foundation Models on Low-level Vision.** ICLR 2024. https://github.com/Q-Future/Q-Bench
- Wu, H., et al. (2024). **Q-Align: Teaching LMMs for Visual Scoring via Discrete Text-Defined Levels.** ICML 2024. arXiv:2312.17090. https://github.com/Q-Future/Q-Align

---

## §8 Glossary

| Term | Definition |
|------|-----------|
| **NR-IQA** | No-Reference (Blind) IQA — quality assessment without a reference image |
| **MOS** | Mean Opinion Score — aggregate human perceptual quality rating, typically on a 1–5 scale |
| **SRCC** | Spearman Rank Correlation Coefficient — measures monotonic alignment between predicted scores and MOS |
| **PLCC** | Pearson Linear Correlation Coefficient — measures linear correlation after a nonlinear fitting step |
| **MSCN** | Mean Subtracted Contrast Normalized — local normalization of image pixels used in BRISQUE/NIQE |
| **GGD** | Generalized Gaussian Distribution — used to fit the statistical distribution of MSCN coefficients |
| **AGGD** | Asymmetric GGD — captures directional asymmetry of MSCN pairwise products |
| **MVG** | Multivariate Gaussian model — NIQE's reference model of natural image statistics |
| **BRISQUE** | Blind/Referenceless Image Spatial Quality Evaluator (Mittal et al., 2012) |
| **NIQE** | Natural Image Quality Evaluator — fully unsupervised NR method (Mittal et al., 2013) |
| **NIMA** | Neural Image Assessment — CNN-based, predicts full score distribution (Talebi et al., 2018) |
| **HyperIQA** | Content-aware NR-IQA via hyper-network (Su et al., CVPR 2020) |
| **MUSIQ** | Multi-Scale Image Quality Transformer — ViT-based flexible resolution IQA (Ke et al., ICCV 2021) |
| **CLIP-IQA** | CLIP-based zero-shot quality scoring via antonym text prompts (Wang et al., AAAI 2023) |
| **Q-Align** | LLM-based IQA using discrete text-defined quality levels (Wu et al., ICML 2024) |
| **VQA** | Video Quality Assessment — temporal extension of IQA to video sequences |
| **Domain shift** | Performance degradation when model is applied to a distribution different from training data |
| **Semantic leakage** | Model scores based on scene content (e.g. "sunsets = high quality") rather than technical quality |
| **Stage-1 filter** | Fast lightweight model (BRISQUE/NIQE < 5 ms) used to pre-screen images before expensive deep inference |

---

## §9 Classical Blind IQA: Technical Deep Dive

This section provides a deeper technical analysis of BRISQUE, NIQE, and PIQE beyond the §1 overview, focusing on mathematical derivation and engineering implementation details.

### 9.1 BRISQUE — MSCN Statistics and AGGD Fitting

**Natural Scene Statistics foundation.** BRISQUE is grounded in the Natural Scene Statistics (NSS) hypothesis: the Mean Subtracted Contrast Normalized (MSCN) coefficients of undistorted natural images follow a zero-mean, near-Gaussian Generalized Gaussian Distribution (GGD). Any intentional distortion (compression, noise, blur) disrupts this statistical regularity, causing detectable shifts in distribution parameters.

The MSCN coefficients are defined as:

$$\hat{I}(i,j) = \frac{I(i,j) - \mu(i,j)}{\sigma(i,j) + C}$$

where:
- $\mu(i,j) = \sum_{k=-K}^{K}\sum_{l=-L}^{L} w_{k,l} I(i+k, j+l)$, with $w$ a $7 \times 7$ normalized Gaussian window ($\sigma_w = 7/6$)
- $\sigma(i,j) = \sqrt{\sum_{k,l} w_{k,l} [I(i+k,j+l) - \mu(i,j)]^2}$
- $C = 1$ is a small stability constant preventing division by zero (for images in the [0, 255] range; use $C \approx 1/255$ if normalized to [0, 1])

**GGD fitting (applied to MSCN coefficients themselves).** The GGD probability density function:

$$f_{\text{GGD}}(x;\, \alpha, \sigma^2) = \frac{\alpha}{2\beta\,\Gamma(1/\alpha)} \exp\!\left(-\left(\frac{|x|}{\beta}\right)^\alpha\right)$$

where $\beta = \sigma\sqrt{\Gamma(1/\alpha)/\Gamma(3/\alpha)}$, $\alpha$ is the shape parameter, and $\sigma^2$ is the variance. When $\alpha = 2$ this reduces to a Gaussian; when $\alpha = 1$ it becomes a Laplacian. Distortions shift $\alpha$ away from 2: additive noise pushes $\alpha$ downward (heavier tails), while blur pushes $\alpha$ upward (sharper peak).

**AGGD fitting (applied to pairwise products).** For the four pairwise-product maps (horizontal, vertical, main diagonal, anti-diagonal neighbors), an Asymmetric Generalized Gaussian Distribution (AGGD) is fitted:

$$f_{\text{AGGD}}(x;\, \nu, \sigma_l^2, \sigma_r^2) = \frac{\nu}{(\beta_l + \beta_r)\,\Gamma(1/\nu)} \begin{cases} \exp\!\left(-\left(\frac{-x}{\beta_l}\right)^\nu\right) & x < 0 \\ \exp\!\left(-\left(\frac{x}{\beta_r}\right)^\nu\right) & x \geq 0 \end{cases}$$

AGGD introduces separate left and right standard deviations ($\sigma_l, \sigma_r$), capturing the directional asymmetry that distortions (especially JPEG blocking) introduce into local gradient statistics.

**36-dimensional feature vector composition.** Features are extracted at two scales: original resolution and $0.5\times$ downsampled. At each scale:
- 2 parameters from GGD fit of MSCN coefficients: $(\alpha, \sigma^2)$
- 4 directions × 4 parameters each from AGGD fit of pairwise products: $(\nu, \sigma_l^2, \sigma_r^2, \eta_{\text{mean}})$

Total: $(2 + 4 \times 4) \times 2 \text{ scales} = 36$ features. These are fed to a radial-basis-function SVR (parameters cross-validated on LIVE) to predict MOS. The score direction is inverted relative to LIVE annotations: lower BRISQUE score means higher quality.

**BRISQUE limitations in ISP contexts:**
1. Strong dependency on the natural scene assumption: medical imaging, satellite imagery, and ISP-processed images with heavy AI enhancement violate the NSS hypothesis.
2. Insensitive to ISP-specific artifacts (color moiré, lens shading) because these do not materially alter the luminance-channel MSCN distribution.
3. Features extracted from the grayscale luminance channel only; color quality information is completely ignored.
4. LIVE SRCC = 0.939 on synthetic benchmark; drops to 0.665 on KonIQ-10k (authentic mobile images) — a 0.274-point gap that quantifies the NSS assumption cost.

### 9.2 NIQE — Fully Unsupervised MVG Model

**NIQE's no-annotation design.** NIQE (Mittal et al., IEEE Signal Processing Letters 2013) requires **no MOS annotations** at all. Its core assumption is "quality equals naturalness" — the degree of deviation from the natural image statistical distribution measures quality degradation.

**MVG model construction.** Extract NSS feature vectors $\mathbf{f} \in \mathbb{R}^{36}$ (same as BRISQUE) from image patches (typically $96 \times 96$) from a corpus of pristine natural images. Fit a Multivariate Gaussian (MVG) distribution to all patch features:

$$P(\mathbf{f}) = \frac{1}{(2\pi)^{d/2}|\Sigma|^{1/2}} \exp\!\left(-\frac{1}{2}(\mathbf{f}-\boldsymbol{\mu})^\top \Sigma^{-1}(\mathbf{f}-\boldsymbol{\mu})\right)$$

The parameters $(\boldsymbol{\mu}_n, \Sigma_n)$ constitute the "natural image model" and are stored as the reference distribution.

**Quality score computation.** For a test image, extract its NSS features and fit a second MVG $(\boldsymbol{\mu}_t, \Sigma_t)$. NIQE quality score is the generalized Mahalanobis distance between the two MVGs:

$$D = \sqrt{(\boldsymbol{\mu}_t - \boldsymbol{\mu}_n)^\top \left(\frac{\Sigma_t + \Sigma_n}{2}\right)^{-1} (\boldsymbol{\mu}_t - \boldsymbol{\mu}_n)}$$

Larger $D$ means the test image deviates more from the natural image model, i.e., lower quality. Score direction: higher NIQE = worse quality (opposite of most deep methods).

**NIQE engineering value and limitations:**
- Advantages: zero MOS labels required; model is lightweight (stores only one MVG parameter set); the reference MVG can be re-fitted to domain-specific corpora (e.g., only ISP output images from a specific sensor) without any labeling cost.
- Limitations: no sensitivity to aesthetic quality (a sharp but poorly-composed image scores perfectly); SRCC on KonIQ-10k is approximately 0.53, far below deep methods (0.91+); over-sharpened or over-saturated images can receive deceptively low (good) NIQE scores because these enhancements push NSS statistics in the "natural" direction.

### 9.3 PIQE — Block-Level Local Quality Estimation

**PIQE (Perception-based Image Quality Evaluator, Venkatanath et al., 2015)** estimates quality degradation at the *local* region level without relying on any MOS training data.

**Algorithm steps:**

1. **Block segmentation:** Divide the image into non-overlapping $16 \times 16$ blocks.
2. **Active block selection:** Compute local variance per block; retain only blocks with variance above threshold $T_{\text{var}}$ (texture-rich "active" blocks). Flat regions (sky, uniform backgrounds) contribute little to perceived quality and are excluded.
3. **MSCN statistics extraction:** For each active block, fit an asymmetric GGD to the intra-block MSCN coefficients; extract mean $\eta$, left standard deviation $\sigma_l$, right standard deviation $\sigma_r$, and shape parameter $\nu$.
4. **Local distortion estimation:** When $|\eta|$ deviates significantly from zero (as determined by natural image statistics thresholds), flag the block as distorted and compute a local PIQE score $q_k$.
5. **Global quality aggregation:** Global PIQE score = mean of $q_k$ across all distorted active blocks. Higher PIQE = lower quality.

**PIQE vs NIQE vs BRISQUE comparison:**

| Dimension | BRISQUE | NIQE | PIQE |
|-----------|---------|------|------|
| Training data | MOS annotations (LIVE) | Undistorted natural images (no MOS) | No training data |
| Distortion localization | Global scalar only | Global scalar only | Block-level local scores |
| Computational cost | Lowest | Low | Moderate (block-level processing) |
| LIVE SRCC | 0.939 | 0.908 | ~0.87 |
| KonIQ SRCC | 0.665 | 0.531 | ~0.49 |
| ISP use case | Fast global filter | Unsupervised baseline | Local artifact localization |

PIQE's block-level output is useful for ISP spatial uniformity testing: by examining the spatial distribution of per-block PIQE scores, an engineer can identify whether quality degradation is concentrated in specific image regions (e.g., corner darkening from LSC error, center-sharpness fall-off from lens field curvature).

---

## §10 Deep Learning Blind IQA: Detailed Coverage

### 10.1 DBCNN — Dual-Stream CNN for Synthetic and Authentic Distortions

**Background and motivation.** NR-IQA models performing well on synthetic distortion datasets (LIVE, TID2013) often degrade when transferred to authentic ISP scenes, because authentic distortions (camera shake, ISP artifacts, composite degradation) have fundamentally different statistics from the uniform synthetic distortions used in training. DBCNN (Deep Bilinear CNN, Zhang et al., IEEE TCSVT 2020) addresses this via a dual-stream architecture that simultaneously models both distortion families.

**Dual-stream architecture:**

```
Input image
    ├── Stream A: VGG-16 (pre-trained on synthetic distortion datasets)
    │              ↓ feature map F_A ∈ R^{H×W×512}
    └── Stream B: S-CNN (pre-trained on authentic distortion distributions)
                   ↓ feature map F_B ∈ R^{H×W×512}
                              ↓
              Bilinear Pooling
              B = sum_{i,j} F_A(i,j)^T · F_B(i,j)  ∈ R^{512×512}
              → vectorize → sign-sqrt normalization → L2 normalize
                              ↓
                        Fully connected → MOS prediction
```

**Bilinear pooling mechanism.** The bilinear pooling computes the outer-product sum of the two feature maps:

$$\mathbf{B} = \sum_{i,j} \mathbf{f}_A(i,j) \otimes \mathbf{f}_B(i,j)$$

This captures second-order statistical interactions between the two streams, allowing the model to detect "co-occurrence patterns of synthetic features and authentic features" rather than simply concatenating the representations. On KonIQ-10k SRCC = 0.875; on SPAQ SRCC = 0.906.

**ISP engineering value.** DBCNN's superior generalization to authentic ISP artifacts makes it a practical choice for training data curation: running DBCNN as a quality filter over a large pool of raw-RGB pairs before DL-ISP model training reduces the proportion of mislabeled or low-quality training samples.

### 10.2 HyperIQA — Content-Aware Quality via Hyper-network

**Content-dependent distortion visibility.** Identical Gaussian noise ($\sigma^2 = 0.01$) applied to high-frequency textured regions (grass, fabric) is nearly imperceptible, but becomes highly visible on smooth regions (clear sky, skin). A quality predictor with fixed weights treats all image locations identically and averages out this content dependence.

**Three-module architecture:**

$$\hat{q} = f_{\text{local}}\!\left(f_{\text{hyper}}\!\left(f_{\text{global}}(I)\right),\, I_{\text{patches}}\right)$$

1. **Global content understanding** $f_{\text{global}}$: ResNet-50 extracts a global content feature vector $\mathbf{c} \in \mathbb{R}^{2048}$, encoding the scene semantics (portrait, landscape, indoor).
2. **Hyper-network** $f_{\text{hyper}}$: A two-layer MLP takes $\mathbf{c}$ as input and outputs the network weights $\{W_1, W_2, W_3\}$ for the local quality predictor. This is the key innovation: the quality predictor's parameters are dynamically generated per image, not fixed.
3. **Local quality predictor** $f_{\text{local}}$: Parameterized by hyper-network weights, it scores randomly sampled $224 \times 224$ patches. Multiple patch scores are aggregated (mean) to produce the final MOS prediction.

**Training strategy.** Joint optimization of all three modules with $\mathcal{L} = \text{MSE}(\hat{q}, q_{\text{MOS}})$. Random patch sampling acts as data augmentation and prevents the model from relying on fixed spatial locations for quality cues. Batch normalization statistics in the hyper-network and local predictor must be isolated to prevent cross-contamination.

**Performance:** KonIQ-10k SRCC = 0.917; SPAQ SRCC = 0.911; LIVE-FB SRCC = 0.859. Among classical deep NR methods, HyperIQA offers the best cross-dataset generalization prior to the Transformer/VLM era.

### 10.3 MUSIQ — Multi-Scale Image Quality Transformer

**Fixed-resolution limitation.** Standard ViT requires fixed-size patch grids (e.g., $224 \times 224$), so input images must be resized. For IQA this is problematic: downsampling removes high-frequency noise (itself a quality signal), and different resolutions produce inconsistent artifact visibility. MUSIQ (Ke et al., ICCV 2021) preserves the **original image resolution** by operating at multiple scales simultaneously.

**Multi-scale patch strategy.** MUSIQ samples patches at three resolution levels:
- Scale $s_1$ (original resolution): captures high-frequency noise, sharpening artifacts
- Scale $s_2$ ($0.5\times$ downsampled): captures mid-frequency blocking, blur
- Scale $s_3$ ($0.25\times$ downsampled): captures global exposure, color bias

Each patch carries two types of positional embeddings:
- **Spatial position embedding** $\mathbf{e}_{\text{spatial}}(i, j)$: encodes the patch's coordinates in the original image, supporting arbitrary resolutions without a fixed patch grid.
- **Scale embedding** $\mathbf{e}_{\text{scale}}(s)$: encodes which resolution level the patch comes from, enabling the model to distinguish quality features across frequency bands.

**Transformer encoding and aggregation.** All multi-scale patches are concatenated into a sequence and fed into a 12-layer, 12-head Transformer encoder. A learnable [CLS] token is appended; its output representation is mapped to MOS via a linear head:

$$\hat{q} = W \cdot h_{\text{[CLS]}} + b$$

**Performance:**

| Dataset | MUSIQ SRCC | MUSIQ PLCC |
|---------|-----------|-----------|
| KonIQ-10k | 0.916 | 0.928 |
| SPAQ | 0.918 | 0.921 |
| LIVE-FB | 0.661 | 0.693 |
| AVA (Aesthetic) | 0.726 | 0.738 |

MUSIQ's strength on SPAQ (mobile authentic) aligns well with ISP engineering requirements. The LIVE-FB number (0.661) suggests the model is less suited for the in-the-wild Facebook compression-mixed scenario.

### 10.4 TOPIQ — Top-Down Semantics-Guided Distortion Perception (Chen et al., IEEE TIP 2024)

**Motivation.** Human observers prioritize quality evaluation in semantically important regions (face, main subject) over background. Existing methods (HyperIQA, MUSIQ) extract quality signals bottom-up from local features, without a mechanism to weight semantically salient regions more heavily. TOPIQ (Top-down IQA, Chen et al., IEEE TIP 2024) introduces a top-down semantic guidance strategy that mirrors this human perceptual prioritization.

**CFANet architecture.** TOPIQ's core is the Cross-scale Feature Alignment Network (CFANet):

```
Input image
  ↓
High-level semantic feature extraction (pre-trained backbone: CLIP/ResNet-50 deep layers)
  ↓  semantic guidance (top-down)
Mid-level perceptual features (texture, structure)
  ↓  local guidance
Low-level distortion features (noise, compression artifacts) ← modulated by semantic weights
  ↓
Multi-scale fusion → MOS prediction
```

In contrast to bottom-up methods (aggregate local features → global score), TOPIQ first uses high-level semantic features to generate a spatial "importance map," then guides low-level distortion perception to focus on semantically significant regions. This makes quality predictions more aligned with human perceptual weighting.

**Performance:**

| Benchmark | TOPIQ SRCC | TOPIQ PLCC | vs Q-Align |
|-----------|-----------|-----------|-----------|
| KonIQ-10k | **0.942** | **0.946** | Q-Align: 0.940 |
| SPAQ | 0.929 | 0.936 | Q-Align: 0.941 |
| LIVE-FB | 0.876 | 0.879 | Q-Align: 0.888 |
| KADID-10k | 0.920 | 0.923 | — |

TOPIQ achieves SRCC 0.942 on KonIQ-10k, marginally exceeding Q-Align, while running at approximately 50 ms GPU inference — 10× faster than Q-Align's 500 ms. TOPIQ is integrated into IQA-PyTorch as `pyiqa.create_metric('topiq_nr')`.

**ISP engineering value.** TOPIQ's semantic-awareness is particularly useful for camera tuning: artifacts on the main subject (face, primary object) are perceptually more damaging than identical artifacts in the background. TOPIQ's score better reflects this human weighting, reducing the gap between automated quality scores and actual user satisfaction.

### 10.5 ARNIQA — Self-Supervised Distortion Manifold Learning (Agnolucci et al., WACV 2024)

**Motivation.** Most deep NR-IQA methods require large labeled MOS datasets. Human annotation is expensive and introduces subjective variance. ARNIQA (leArning distoRtion maNIfold for Image Quality Assessment, Agnolucci et al., WACV 2024) achieves competitive NR-IQA without any MOS labels during the main training phase.

**Distortion manifold hypothesis.** ARNIQA assumes that images with different distortion types and intensities form a low-dimensional "distortion manifold" in the feature space. By learning a self-supervised representation of this manifold, the model implicitly captures image quality.

**Training procedure:**

1. **Contrastive learning setup:** Apply different distortion types (JPEG, Gaussian noise, blur) and intensities to the same clean image to generate distorted image pairs.
2. **Manifold-aware negative sampling:** Distortion-type-similar, intensity-similar pairs are treated as positive; dissimilar distortion pairs are negatives. This encourages the representation to organize the manifold by distortion type and severity.
3. **Quality score extraction:** After self-supervised pre-training, a lightweight linear probe (or minimal fine-tuning) on a small set of MOS labels maps the learned representation to quality scores.

```
Self-supervised pre-training phase (no MOS needed):
Clean image → [distortion augmentation] → Distorted A (JPEG quality=30)
                                         → Distorted B (JPEG quality=50)
     Contrastive learning (A,B as positive pair; different distortion types as negatives)
                    ↓
     Learn position in "distortion manifold"

Linear probe phase (small MOS set):
Representation → linear regression → MOS prediction
```

**Performance:**

| Benchmark | ARNIQA SRCC | ARNIQA PLCC |
|-----------|-----------|-----------|
| KADID-10k | 0.906 | 0.907 |
| CSIQ | 0.960 | 0.968 |
| LIVE | 0.972 | 0.979 |
| KonIQ-10k (authentic) | 0.842 | 0.855 |

Strong results on synthetic distortion benchmarks (KADID, CSIQ, LIVE); the KonIQ-10k gap versus supervised methods (0.842 vs 0.917 for HyperIQA) reflects the inherent limitation of self-supervised approaches on authentic, compositionally varied real-world images.

**ISP engineering applications:**
- **Novel distortion adaptation:** When ISP introduces new artifact types (AI super-resolution ringing, generative denoising over-smoothing), ARNIQA can be adapted by designing matching distortion augmentations, without the need to collect new MOS annotations.
- **Data-scarce scenarios:** For niche B-to-B camera products with small deployment volumes where large-scale subjective evaluation is infeasible, ARNIQA's few-shot transfer capability provides a rapid path to a domain-specific quality estimator.

---

## §11 VLM-IQA Advanced Details: Q-Bench, Q-Align, and Co-Instruct

### 11.1 Q-Bench Softmax Score Extraction

**The direct number output problem.** Q-Bench (ICLR 2024) establishes that directly prompting an MLLM to output a quality score as a digit is unreliable: models produce non-normalized outputs ("about 7", "moderately high"), and format sensitivity undermines reproducibility.

**Softmax pooling solution.** Q-Bench proposes mapping quality levels to vocabulary tokens and extracting the conditional probability distribution. After the prompt "The overall quality of this image is:", the logit values of four tokens — `good`, `fair`, `poor`, `bad` — are extracted from the next-token prediction:

$$\text{score} = \frac{\sum_{l \in \{\text{good,fair,poor,bad}\}} p(l) \cdot v(l)}{\sum_{l} p(l)}$$

where $v(\text{good})=1$, $v(\text{fair})=0.667$, $v(\text{poor})=0.333$, $v(\text{bad})=0$ (linear spacing), and $p(l)$ is the MLLM's softmax probability for that token. This extraction requires no weight modification (fully zero-shot), produces a continuous differentiable score, and is insensitive to sampling temperature and random seed.

**Q-Bench VQA benchmark composition:**

| Benchmark dataset | Images | Distortion type | Annotation |
|-------------------|--------|----------------|-----------|
| LIVE-FB (LIVE-Qualcomm) | 1,162 | Real mobile camera artifacts | MOS (0–100) |
| KonIQ-10k | 10,073 | Authentic web images | MOS (1–5) |
| SPAQ | 11,125 | Authentic mobile images | MOS (0–100) |
| CSIQ | 866 | 6 synthetic distortions | DMOS |
| TID2013 | 3,000 | 24 synthetic distortions | MOS (0–9) |

### 11.2 Q-Align Five-Level Alignment Strategy

**Extending to 5 levels.** Q-Align (ICML 2024) extends Q-Bench's four-level vocabulary (good/fair/poor/bad) to five levels (excellent/good/fair/poor/bad), aligning with the standard 5-point MOS scale used in psychometric measurement. Numeric mapping:

$$v(\text{excellent})=5,\quad v(\text{good})=4,\quad v(\text{fair})=3,\quad v(\text{poor})=2,\quad v(\text{bad})=1$$

Weighted summation:

$$\hat{q} = \sum_{l \in \mathcal{L}} \text{softmax}(\mathbf{z})_l \cdot v(l)$$

where $\mathbf{z}$ is the logit vector at the five level token positions (softmax over only these five positions rather than the full vocabulary, preventing dilution by irrelevant tokens).

**Fine-tuning data recipe.** Q-Align performs supervised fine-tuning (SFT) on LLaVA-1.5-7B using a mixture of:
- IQA data: KADID-10k, KonIQ-10k, SPAQ (with five-level quality tokens as training targets)
- VQA data: KoNViD-1k, LIVE-VQC, YouTube-UGC (video quality assessment)
- Aesthetic data: AVA (aesthetic scoring)

**Design comparison: CLIP-IQA+ vs Q-Align:**

| Dimension | CLIP-IQA+ | Q-Align |
|-----------|-----------|---------|
| Base model | CLIP ViT-L/14 | LLaVA-1.5-7B |
| Score extraction | Cosine similarity to antonym text embeddings | 5-level token softmax weighted sum |
| Interpretability | Low (score only) | High (can generate quality descriptions) |
| Inference speed | Fast (~50 ms GPU) | Slow (~500 ms GPU) |
| KonIQ SRCC | 0.895 | 0.940 |
| Cross-task capability | IQA only | IQA / VQA / Aesthetic (three tasks) |

### 11.3 Co-Instruct — Multi-Modal Quality Comparison

**Design objective.** Co-Instruct (Wu et al., 2024) targets the quality *comparison* task: given two images, determine which has better quality and provide fine-grained textual justification. This is more directly applicable to real-world ISP A/B testing than single-image scoring.

**Framework.** Co-Instruct builds a quality comparison dataset (Co-Instruct-DB) on top of Q-Instruct, where each sample is $\{\text{image}_A, \text{image}_B, \text{comparison verdict}, \text{detailed explanation}\}$. The fine-tuned MLLM produces outputs of the form:

```
Image B has higher quality than image A: image A exhibits obvious chromatic
aberration in the blue channel, while image B has more accurate color
reproduction and lower noise levels in the shadow regions.
```

This comparison-style output directly serves ISP A/B test automation: rather than just identifying a winner by score delta, the system generates an interpretable parameter comparison report that guides ISP engineer analysis.

**Deployment note.** Co-Instruct inference is even heavier than Q-Align since it processes two images simultaneously. It is suitable only for offline batch A/B testing pipelines, not for latency-sensitive online quality gates. For real-time pairwise ranking, use TOPIQ scores with Wilcoxon signed-rank statistical significance testing (see §13).

---

## §12 No-Reference Video Quality Assessment (VQA)

Blind VQA extends NR-IQA to video: the model must assess quality without a reference, accounting for both per-frame spatial quality and temporal consistency artifacts.

### 12.1 Unique Challenges of Video IQA

Compared to image IQA, video quality assessment faces additional complexity:

- **Temporal artifacts:** Frame-to-frame flickering, temporal noise, motion blur inconsistency, rolling-shutter effect.
- **Compression artifacts:** Blocking artifacts from video encoding, quality fluctuations caused by bitrate variation.
- **Motion consistency:** Stability perception under camera motion and scene motion.
- **Computational efficiency:** Per-frame image IQA is cost-prohibitive at typical video frame rates. A 30 fps requirement implies < 33 ms per frame; FastVQA-B takes ~120 ms on a V100 GPU, failing the real-time constraint; only FasterVQA with INT8 quantization and a 4-frame sampling strategy can reach ~15 ms/frame.

**Key temporal artifacts not present in still images:**
- **Flickering** — frame-to-frame luminance/color oscillation from ISP parameter jumps (AE, AWB convergence)
- **Motion blur inconsistency** — changing blur amount across frames due to AE step changes
- **Temporal noise** — independent noise realizations per frame perceived as "boiling" texture
- **Encoding artifacts** — blocking/ringing introduced by H.265/H.264 low-bitrate compression

### 12.1.1 Smartphone UGC Video: Special ISP Challenges

Smartphone user-generated content (UGC) video is the most direct ISP video quality application. Compared to lab compression distortion datasets, UGC presents unique challenges:

**Challenge 1: Composite ISP + compression degradation.** UGC video simultaneously suffers two degradation layers: temporal noise, motion blur, and color bias from the ISP stage; plus blocking artifacts and quantization noise from H.264/H.265 encoding. Both layers interleave in ways neither ISP-focused nor compression-focused NR models can fully handle. BRISQUE achieves only SRCC 0.657 on KoNViD-1k versus 0.939 on LIVE — a gap directly attributable to composite authentic degradation outside the training distribution.

**Challenge 2: Content diversity induces perceptual bias.** Tolerance for identical distortion levels varies dramatically by UGC content type:
- High-motion content (sports/dance): motion blur is less noticeable, but temporal instability (flickering) is salient.
- Low-motion content (scenery/still life): fine detail noise is highly visible; ISP NR strength sensitivity is extreme.
- Low-light content (night/indoor): ISP gain noise compounds with compression artifacts, causing non-linear perceptual quality deterioration.

Content diversity demands content-aware VQA models (analogous to HyperIQA's hyper-network mechanism).

**Challenge 3: Vertical orientation distribution shift.** Most VQA benchmarks (KoNViD-1k, YouTube-UGC) are predominantly landscape; smartphone UGC is heavily portrait (9:16). Models trained on landscape data exhibit systematic bias on portrait UGC (SRCC reduction ~0.05–0.10).

**Challenge 4: Real-time bitrate fluctuation.** In live streaming contexts, network jitter can drop encoding bitrate from 4 Mbps to 500 Kbps within seconds. Frame-level IQA mean cannot reflect the perceptual impact of temporal quality swings; temporal quality stability metrics (quality variance, quality-drop gradient) must be incorporated.

**Engineering recommendation:** For smartphone UGC video ISP tuning, use LIVE-Qualcomm (208 segments of real smartphone camera video with authentic ISP+compression artifacts) as primary benchmark. Combine with DOVER's technical quality branch (not aesthetic) to isolate ISP parameter impact.

### 12.2 BVQI — Joint Spatial and Temporal Features

**BVQI (Blind Video Quality Index, Chen et al., ACM MM 2022)** is the first method to systematically jointly model spatial and temporal quality in a deep VQA framework.

**Feature extraction:**
- **Spatial branch:** Based on pre-trained CLIP ViT-B/32; extracts spatial quality features $\mathbf{f}_{\text{spatial}} \in \mathbb{R}^{512}$ from keyframes sampled every $N$ frames.
- **Temporal branch:** Computes optical flow between adjacent frames; extracts motion statistics $\mathbf{f}_{\text{temporal}} \in \mathbb{R}^{256}$ (motion magnitude, temporal gradient variance, motion consistency).

**Fusion:**

$$\hat{q}_{\text{video}} = \text{MLP}\!\left([\mathbf{f}_{\text{spatial}};\, \mathbf{f}_{\text{temporal}}]\right)$$

**Performance on KoNViD-1k:**

| Method | SRCC | PLCC |
|--------|------|------|
| BRISQUE (frame-mean) | 0.657 | 0.681 |
| BVQI | 0.891 | 0.895 |
| FastVQA | 0.891 | 0.892 |

### 12.3 FastVQA — Fragment Sampling for Efficient Inference

**FastVQA (Wu et al., ECCV 2022)** achieves high accuracy at reduced compute cost through "Fragment Sampling."

**Fragment Sampling principle.** Divide each frame into an $8 \times 8$ grid; randomly sample a $32 \times 32$ fragment from each grid cell; assemble fragments into a $256 \times 256$ "fragment mosaic" as model input. Compared to direct downsampling, this preserves local high-frequency quality signals (noise texture, sharpness) while maintaining global spatial coverage.

**FasterVQA inference latency:**

| Configuration | Input | Frames | GPU latency (V100) | SRCC (KoNViD-1k) |
|--------------|-------|--------|--------------------|------------------|
| FastVQA-B | Fragment 256 | 8 | 120 ms | 0.891 |
| FastVQA-M (lightweight) | Fragment 224 | 4 | 45 ms | 0.874 |
| FasterVQA | Fragment 128 | 4 | 18 ms | 0.863 |

**Mobile deployment:** FasterVQA with INT8 quantization reaches approximately 15 ms/frame on a Snapdragon 8 Gen 3. Combined with a 4-frame-per-second sampling strategy, near-real-time quality monitoring becomes feasible.

### 12.4 DOVER — Disentangled Technical and Aesthetic Quality

**DOVER (Disentangled Objective Video Quality Evaluator, Wu et al., ICCV 2023)** separates two orthogonal quality dimensions:

- **Technical quality:** Objective physical distortions — noise, blur, compression artifacts, camera shake. Directly linked to device performance and ISP configuration.
- **Aesthetic quality:** Subjective perceptual dimensions — composition, lighting, color harmony. Related to shooting skill and creative intent.

**Disentangled architecture:**

```
Video input
  ├── Technical quality branch (Fragment Sampling + Swin-Tiny)
  │    → q_technical
  └── Aesthetic quality branch (Temporal Sampling + CLIP ViT-B/32)
       → q_aesthetic
         ↓
q_final = w_t · q_technical + w_a · q_aesthetic
(weights w_t, w_a adjustable per deployment scenario)
```

**ISP engineering significance:** DOVER's technical/aesthetic disentanglement is particularly valuable for camera tuning — ISP parameters directly influence the technical quality branch score, while the aesthetic branch reflects shooting quality independent of ISP. For ISP A/B testing, use only the technical quality branch score to avoid aesthetic bias.

### 12.5 VQA Benchmark Datasets

| Dataset | Videos | Duration | Content | MOS Annotation |
|---------|--------|----------|---------|---------------|
| KoNViD-1k | 1,200 | 8 s/clip | UGC web video | MOS (1–5) |
| LIVE-VQC | 585 | 10 s/clip | Mobile camera video | MOS (0–100) |
| YouTube-UGC | 1,380 | 20 s/clip | YouTube UGC | MOS (1–5) |
| LIVE-Qualcomm | 208 | 15 s/clip | Smartphone camera | MOS (0–100) |

For ISP VQA, LIVE-Qualcomm is most directly relevant (authentic smartphone camera artifacts), but its small sample size (208 clips) makes it unreliable as a standalone training set; combining with KoNViD-1k for mixed training is recommended.

**Representative NR-VQA methods overview:**

| Method | Backbone | Temporal modeling | KoNViD-1k SRCC |
|--------|---------|-------------------|----------------|
| BRISQUE (frame-avg) | Hand-crafted | None (naive pooling) | 0.657 |
| TLVQM (Korhonen, 2019) | Hand-crafted | Motion-based features | 0.773 |
| VSFA (Li et al., 2019) | ResNet-50 + GRU | Frame-level GRU | 0.801 |
| BVQI (Chen et al., 2022) | CLIP + optical flow | Spatial+temporal fusion | 0.891 |
| FastVQA (Wu et al., 2022) | Video Swin-T | Fragment sampling | 0.891 |
| DOVER (Wu et al., 2023) | Dual ViT | Tech/aesthetic disentanglement | 0.906 |

---

## §13 ISP Engineering Integration

### 13.1 Online IQA-Triggered Re-Tuning Strategy

**Production-scale quality monitoring loop.** After mass-market camera deployment, real-world usage diversity far exceeds lab test coverage. An NR-IQA-based online monitoring system enables data-driven continuous tuning:

```
User captures → image upload (opt-in/anonymized) → online NR-IQA scoring
                                                          ↓
                                          quality distribution statistics (daily/weekly aggregation)
                                                          ↓
                          if quality distribution drift > threshold → trigger tuning team review
                                                          ↓
                                  automated tuning suggestion → human confirmation → parameter OTA update
```

**Trigger threshold design:**
- **Absolute threshold:** If a scene category's (e.g., night) BRISQUE mean rises by > 5 points versus the baseline version, trigger review.
- **Relative drift:** If current version SRCC (vs. limited user subjective feedback) drops by > 0.05, trigger.
- **Anomaly proportion:** If the proportion of single-day images scoring below threshold exceeds 5%, trigger anomaly alert.

### 13.2 Automated Scoring Pipeline for A/B Testing

**ISP parameter change quality arbitration.** ISP parameter changes (e.g., adjusting Gamma curve, NR strength) traditionally require human subjective evaluation (recruit raters, paired comparison) — typically 1–2 weeks. NR-IQA-based automated pipeline:

```python
# Pseudocode: A/B test automated quality arbitration
def ab_test_iqa(images_A: list, images_B: list,
                metric: str = 'composite') -> dict:
    """
    Composite metric = 0.4*BRISQUE_norm + 0.4*CLIP-IQA + 0.2*HyperIQA
    """
    scores_A = [compute_composite_iqa(img) for img in images_A]
    scores_B = [compute_composite_iqa(img) for img in images_B]

    # Statistical significance test (Wilcoxon signed-rank, paired samples)
    stat, p_value = scipy.stats.wilcoxon(scores_A, scores_B)

    return {
        'A_mean': np.mean(scores_A), 'B_mean': np.mean(scores_B),
        'winner': 'B' if np.mean(scores_B) > np.mean(scores_A) else 'A',
        'p_value': p_value,
        'significant': p_value < 0.05
    }
```

**Note:** Automated IQA arbitration should be validated against human subjective evaluation (SRCC > 0.85) before replacing human evaluation in production decisions.

### 13.3 Batch RAW Sample Quality Filtering (Training Data Curation)

**Problem background.** Deep learning ISP model training quality depends heavily on training data quality. Low-quality RAW samples (overexposure, underexposure, severe blur, sensor malfunction) contaminate the training set. Filtering thousands to tens of thousands of RAW samples requires automated quality filters.

**Three-tier filtering pipeline:**

| Stage | Method | Speed | Filter Target |
|-------|--------|-------|--------------|
| Pre-filter | BRISQUE + histogram statistics (highlights > 30% or shadows > 40% treated as exposure anomaly) | < 5 ms/image | Severe exposure issues, extreme blur |
| Deep filter | HyperIQA (GPU batch processing, batch_size=64) | ~20 ms/image | Mid-range quality issues, content-dependent distortion |
| Semantic review | Q-Instruct (optional, only for borderline samples near threshold) | ~500 ms/image | Generate quality descriptions for human review |

**Diversity preservation.** Beyond quality filtering, apply diversity sampling on passing samples (prevent scene homogeneity): use CLIP embeddings + K-Means clustering; within each cluster, retain Top-N images sorted by quality score descending, ensuring training set covers diverse scene types.

### 13.4 MOS–PSNR/SSIM Correlation Analysis

**SRCC computation:**

$$\text{SRCC} = 1 - \frac{6 \sum_{i=1}^N d_i^2}{N(N^2 - 1)}$$

where $d_i = \text{rank}(\hat{q}_i) - \text{rank}(q_i)$ is the rank difference between predicted and true MOS for sample $i$.

**PLCC computation (with nonlinear mapping).** Since IQA model output ranges may differ from MOS annotation ranges, a logistic nonlinear mapping (VQEG recommendation) is applied before computing PLCC:

$$\hat{q}_{\text{mapped}} = \beta_1 \left(\frac{1}{2} - \frac{1}{1 + \exp(\beta_2(\hat{q} - \beta_3))}\right) + \beta_4 \hat{q} + \beta_5$$

where $\{\beta_i\}$ are fitted by minimizing MSE between mapped predictions and MOS.

**IQA vs FR metrics correlation on authentic data:**

| Metric pair | KonIQ-10k SRCC | Notes |
|-------------|---------------|-------|
| PSNR vs MOS | 0.28 | PSNR has near-zero correlation with MOS on authentic distortions |
| SSIM vs MOS | 0.41 | Marginally better than PSNR, still far below NR methods |
| LPIPS vs MOS | 0.62 | Perceptual distance significantly outperforms traditional FR metrics |
| BRISQUE vs MOS | 0.67 | NR method exceeds FR metrics (without any reference!) |
| HyperIQA vs MOS | 0.917 | Quality ceiling of classical deep NR methods |
| Q-Align vs MOS | 0.940 | Current SOTA |

**Key finding:** In authentic scenarios, **NR-IQA methods (no reference) correlate with MOS far better than FR metrics (PSNR/SSIM)**. PSNR/SSIM are no longer the best choice for measuring ISP quality in real-world conditions.

---

## §14 Benchmark Summary Tables

### 14.1 Image NR-IQA Method Comprehensive Comparison

SRCC/PLCC on KonIQ-10k and SPAQ with typical inference latency (GPU: NVIDIA V100; CPU: Intel Xeon 2.4 GHz):

| Method | Year | KonIQ SRCC | KonIQ PLCC | SPAQ SRCC | SPAQ PLCC | GPU latency | CPU latency | Notes |
|--------|------|-----------|-----------|----------|----------|------------|------------|-------|
| BRISQUE | 2012 | 0.665 | 0.681 | ~0.665 | ~0.681 | — | < 5 ms | No GPU required |
| NIQE | 2013 | 0.531 | 0.543 | — | — | — | < 8 ms | Unsupervised |
| PIQE | 2015 | — | — | — | — | — | < 15 ms | Local quality estimation |
| NIMA (InceptionV3) | 2018 | 0.726 | 0.731 | — | — | ~30 ms | — | Score distribution |
| DBCNN | 2020 | 0.875 | 0.884 | 0.906 | 0.912 | ~35 ms | — | Dual-stream CNN |
| HyperIQA | 2020 | 0.917 | 0.926 | 0.911 | 0.920 | ~40 ms | — | Hyper-network |
| MUSIQ | 2021 | 0.916 | 0.928 | 0.918 | 0.921 | ~55 ms | — | Multi-scale ViT |
| CLIP-IQA+ | 2022 | 0.895 | 0.902 | — | — | ~50 ms | — | CLIP fine-tuned |
| ARNIQA | 2024 | 0.842 | 0.855 | — | — | ~40 ms | — | Self-supervised manifold |
| TOPIQ | 2024 | **0.942** | **0.946** | 0.929 | 0.936 | ~50 ms | — | Top-down semantic guidance |
| Q-Align | 2024 | 0.940 | 0.944 | **0.941** | **0.945** | ~500 ms | — | LLaVA-7B |

**Inference speed note:** Q-Align's 500 ms GPU latency is dominated by the 7B-parameter LLaVA model. On an A100 this can be reduced to ~200 ms, but still far exceeds specialized NR-IQA models; it is suitable for offline batch processing rather than online real-time evaluation.

### 14.2 Video VQA Method Comparison

| Method | Year | KoNViD-1k SRCC | LIVE-VQC SRCC | YouTube-UGC SRCC | GPU latency/frame |
|--------|------|---------------|--------------|-----------------|------------------|
| BRISQUE (frame-avg) | 2012 | 0.657 | 0.607 | 0.382 | — |
| BVQI | 2022 | 0.891 | 0.852 | 0.783 | ~45 ms |
| FastVQA | 2022 | 0.891 | 0.876 | 0.855 | ~18 ms |
| FasterVQA | 2022 | 0.863 | 0.848 | 0.819 | ~8 ms |
| DOVER | 2023 | **0.906** | **0.882** | **0.876** | ~25 ms |

### 14.3 ISP Engineering Deployment Recommendations

| Application scenario | Recommended method | Rationale |
|---------------------|-------------------|-----------|
| Online real-time quality gating (< 10 ms) | BRISQUE | CPU operation, no GPU required |
| Offline batch data curation | HyperIQA (GPU batch) | Best speed-accuracy trade-off |
| A/B test automated arbitration | TOPIQ or MUSIQ | Good cross-dataset generalization, acceptable latency |
| Tuning problem diagnostics | Q-Align + Q-Instruct | Interpretable quality descriptions, distortion localization |
| Video ISP quality evaluation | DOVER (technical quality branch) | Decouples technical/aesthetic; more sensitive to ISP |
| Mobile real-time VQA | FasterVQA INT8 | Meets < 10 ms with 4-frame sampling strategy |

---

> **Engineer's Notes: Blind IQA in Production Mobile Camera Scenarios**
>
> **BRISQUE/NIQE vs Deep NR-IQA — Field Comparison.** In laboratory standardized scenes (uniform illumination, static test charts), BRISQUE and deep models (MUSIQ, HyperIQA) differ by only ~0.05 SRCC. Deployed to field smartphone datasets, the gap widens to 0.15–0.25. Root cause: BRISQUE's NSS assumption based on MSCN statistics fails under night-scene long-exposure non-Gaussian noise, dynamic motion blur, and HDR tone-mapped content. NIQE similarly produces false quality penalties on images after ultra-wide-angle lens geometric distortion correction. Deep models generalize better, but inference latency on Snapdragon 8 Gen 2 is ~18 ms/frame — too slow for real-time preview pipelines. Typically used only for offline quality evaluation reports.
>
> **Scene Content Bias Problem.** IQA models universally exhibit scene content bias: accurate predictions for high-frequency training scenes (faces, sky, vegetation), significantly increased error for long-tail scenes (industrial parts, text, low-contrast haze). MOS prediction error can reach plus or minus 1.2 on a 5-point scale. Engineering practice requires building separate evaluation sets per target application domain (surveillance, medical endoscopy, automotive front cameras), and periodically performing domain adaptation fine-tuning with newly collected real-capture data. Validate cross-sensor transfer performance at least quarterly to prevent silent degradation.
>
> **Lab Accuracy vs. Field Deployment Gap.** Models achieving SRCC > 0.9 on academic benchmarks (LIVE, CSIQ, TID2013) frequently drop to 0.65–0.75 on actual production smartphone images. Three root causes: (1) benchmark distortions are primarily traditional compression/Gaussian noise, lacking AI denoising over-smoothing, HDR haloing, and other novel ISP-era distortions; (2) production images undergo multi-stage post-processing (beautification, sharpening, saturation enhancement) whose distribution diverges from training data; (3) evaluation on a single device cannot cover fixed-pattern noise variation across different manufacturing batch sensors. Establish a "lab accuracy — field accuracy" dual-track monitoring mechanism; when the SRCC gap between the two exceeds 0.1, trigger a model retraining alert.
>
> *References: Mittal et al., "No-Reference Image Quality Assessment in the Spatial Domain," IEEE TIP 2012; Zhang et al., "Blind Image Quality Assessment Using a General Regression Neural Network," IEEE TNN 2011; Ke et al., "MUSIQ: Multi-Scale Image Quality Transformer," ICCV 2021; Wu et al., "Q-Align: Teaching LMMs for Visual Scoring via Discrete Text-Defined Levels," ICML 2024*
