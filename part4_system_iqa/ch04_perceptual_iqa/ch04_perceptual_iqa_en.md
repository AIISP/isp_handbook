# Part 4, Chapter 04: Perceptual Similarity and Image Quality Assessment

> **Pipeline position:** Used throughout the pipeline for quantitative evaluation — from per-module tuning loops to final system benchmarking.
> **Prerequisites:** Chapter 1 (Pipeline Overview), Chapter 5 (Color Science)
> **Reader path:** All readers, especially System Designer and DL Researcher

---

## §1 原理 (Theory)

### 1.1 Why PSNR Is Insufficient

Peak Signal-to-Noise Ratio (PSNR) is the oldest and most widely used distortion metric in ISP and image restoration pipelines. Its appeal is obvious: it has a clean closed-form expression, maps directly to MSE, and larger values always feel like "better". Yet decades of user studies show that PSNR correlates poorly with how humans actually perceive quality.

The core problem is that PSNR treats every pixel deviation as equal, regardless of spatial location, local structure, or perceptual salience. Consider two distorted versions of the same image: a softly blurred version and a sharper version corrupted by high-frequency ringing artifacts. The blurred image may achieve a higher PSNR because its pixel-level error is uniformly small, yet most observers will prefer the ringing image, or consider both roughly equivalent. This is the classic "PSNR(blurry) > PSNR(sharp-with-artifacts)" paradox. In ISP contexts, denoising tuned to maximise PSNR will routinely over-smooth fine texture, remove hair detail, and flatten fabric patterns — all at the cost of human-perceived quality.

The ISP community therefore relies on a hierarchy of quality metrics:

- **Full-Reference (FR)** metrics: a clean reference image is available (lab measurement, synthetic ground truth).
- **No-Reference (NR) / Blind** metrics: no reference; quality predicted from the distorted image alone.
- **Human opinion scores** (MOS): the ground truth — collected through controlled subjective experiments.

---

### 1.2 Full-Reference Metrics

#### PSNR

PSNR is defined as:

$$\text{PSNR}(x, \hat{x}) = 10 \cdot \log_{10} \frac{\text{MAX}^2}{\text{MSE}(x, \hat{x})}$$

where MAX is the maximum pixel value (255 for uint8, 1.0 for float), and MSE is the mean squared error over all pixels and channels. Typical PSNR ranges for lossy-compressed or denoised images lie between 28–42 dB; values above 40 dB are often imperceptible to humans.

PSNR implicitly assumes that distortion is additive, independent, and Gaussian. Real-world ISP distortions — compression blocking, demosaic zipper artefacts, local sharpening halos — violate all three assumptions. PSNR remains useful as a fast sanity-check and as one input in a multi-metric evaluation, but should never be used alone.

#### SSIM — Structural Similarity Index

Wang et al. (2004) proposed SSIM as a principled departure from pixel-level error metrics. The insight is that the human visual system (HVS) is highly adapted to extract structural information from a scene. A useful quality metric should therefore measure the degradation of structure, not just the magnitude of pixel differences.

SSIM decomposes the comparison into three components — luminance, contrast, and structure — computed within a local window:

$$l(x, y) = \frac{2\mu_x \mu_y + C_1}{\mu_x^2 + \mu_y^2 + C_1}$$

$$c(x, y) = \frac{2\sigma_x \sigma_y + C_2}{\sigma_x^2 + \sigma_y^2 + C_2}$$

$$s(x, y) = \frac{\sigma_{xy} + C_3}{\sigma_x \sigma_y + C_3}$$

where $\mu_x, \mu_y$ are local means, $\sigma_x, \sigma_y$ are local standard deviations, $\sigma_{xy}$ is the local cross-covariance, and $C_1, C_2, C_3$ are small stabilising constants (typically $C_3 = C_2/2$). The combined SSIM score is:

$$\text{SSIM}(x, y) = l(x,y)^{\alpha} \cdot c(x,y)^{\beta} \cdot s(x,y)^{\gamma}$$

In the standard formulation $\alpha = \beta = \gamma = 1$, yielding:

$$\text{SSIM}(x, y) = \frac{(2\mu_x\mu_y + C_1)(2\sigma_{xy} + C_2)}{(\mu_x^2 + \mu_y^2 + C_1)(\sigma_x^2 + \sigma_y^2 + C_2)}$$

SSIM ranges from $-1$ to $1$ (in practice, SSIM for natural images is almost always positive; commonly reported range is $[0, 1]$), where $1$ indicates perfect similarity. High-quality reconstructions typically score $> 0.90$. A global SSIM score is the average of local window scores across the image. SSIM is significantly more sensitive to blur and structural degradation than PSNR, and correlates much better with human opinion scores on natural scene distortions.

#### MS-SSIM — Multi-Scale SSIM

A single analysis window in SSIM implicitly fixes the viewing scale. MS-SSIM (Wang et al., 2003) computes SSIM across multiple spatial scales by iteratively low-pass filtering and downsampling the image:

$$\text{MS-SSIM}(x, y) = \left[ l_M(x,y) \right]^{\alpha_M} \cdot \prod_{j=1}^{M} \left[ c_j(x,y) \right]^{\beta_j} \left[ s_j(x,y) \right]^{\gamma_j}$$

where $M = 5$ scales are standard. MS-SSIM is more robust than single-scale SSIM when the display resolution or viewing distance is variable, and achieves higher correlation with MOS on most benchmarks.

#### LPIPS — Learned Perceptual Image Patch Similarity

Zhang et al. (2018, CVPR) demonstrated that deep network feature spaces are a far better perceptual similarity space than hand-crafted metrics. LPIPS computes a weighted distance between activation maps of a pre-trained network:

$$\text{LPIPS}(x, \hat{x}) = \sum_l \frac{1}{H_l W_l} \sum_{h,w} \left\| w_l \odot \left( \phi_l(x)_{hw} - \phi_l(\hat{x})_{hw} \right) \right\|_2^2$$

where $\phi_l$ extracts the feature map at layer $l$ of a VGG-16 or AlexNet backbone, $w_l$ is a learned per-channel weight vector, and $H_l, W_l$ are spatial dimensions at layer $l$. Lower LPIPS means more perceptually similar. The weights $w_l$ are calibrated on the Berkeley-Adobe Perceptual Patch Similarity (BAPPS) dataset, which contains human 2AFC (two-alternative forced choice) judgements.

LPIPS is the metric of choice when evaluating super-resolution, style transfer, and generative ISP models, because it penalises texture hallucinations and semantic inconsistencies that SSIM would not catch.

**LPIPS post-2023: DINOv2-based perceptual metrics**

The original LPIPS uses ImageNet-supervised VGG/AlexNet features. Since 2023, researchers have explored using self-supervised ViT features (DINOv2, Oquab et al., TMLR 2024) as the LPIPS backbone. Because DINOv2 features are not conditioned on class labels, they are less sensitive to image semantics and respond more purely to distortion type (noise, compression, tone mapping). On the BAPPS 2AFC benchmark, LPIPS-VGG achieves ~72.8% 2AFC accuracy (Zhang et al. CVPR 2018, Table 1); using DINOv2 ViT-L/14 features without retraining the $w_l$ weights yields ~66% — lower than LPIPS-VGG overall, but with better cross-scene generalisation on specific ISP distortion types. For ISP engineering: when evaluating ISP-specific distortions such as HDR tone mapping and AI denoising, DINOv2-based perceptual metrics generalise better across scenes than vanilla LPIPS, and are recommended as a supplementary validation alongside LPIPS for new model evaluations.

#### DISTS — Distribution Shift in Feature Space

Ding et al. (TPAMI 2022) addressed LPIPS's sensitivity to texture swapping. Two images sharing the same texture structure but different texture instances (e.g. two photographs of different marble surfaces) score poorly under LPIPS, yet are perceptually close. DISTS decouples structure similarity and texture similarity in feature space:

$$\text{DISTS}(x, y) = \sum_j \alpha_j \left(1 - \frac{2\mu_{x_j}\mu_{y_j} + c_1}{\mu_{x_j}^2 + \mu_{y_j}^2 + c_1}\right) + \beta_j \left(1 - \frac{2\sigma_{x_j y_j} + c_2}{\sigma_{x_j}^2 + \sigma_{y_j}^2 + c_2}\right)$$

where $\mu, \sigma$ are VGG feature channel means and variances, and $\alpha_j, \beta_j$ are learnable weights. DISTS achieves SRCC = 0.861 on KADID-10k, outperforming LPIPS (0.721), and is more robust to textured noise such as film grain. For ISP sharpening and denoising tuning, DISTS reflects user perception better than LPIPS.

---

### 1.3 No-Reference (Blind) Metrics

#### BRISQUE — Blind/Referenceless Image Spatial Quality Evaluator

Mittal et al. (2012) observed that pristine natural images have predictable statistical distributions when normalised by local mean and variance (Mean Subtracted Contrast Normalised, MSCN):

$$\hat{I}(i,j) = \frac{I(i,j) - \mu(i,j)}{\sigma(i,j) + C}$$

MSCN coefficients of distortion-free images closely follow a Generalised Gaussian Distribution (GGD). Distortions such as blur, noise, and compression shift both the shape parameter and variance of this distribution. BRISQUE extracts 36 features by fitting Asymmetric GGD (AGGD) models to MSCN coefficients and their pairwise products along four orientations. A Support Vector Regressor (SVR) trained on the LIVE database maps these features to a quality score (0–100, lower is better).

BRISQUE requires no reference image and runs efficiently on CPU. Its main limitation is that it was trained on specific distortion types; it performs poorly on content outside its training distribution (e.g. HDR tone mapping, stylised images, medical imagery).

#### NIQE — Natural Image Quality Evaluator

Mittal et al. (2013) also proposed NIQE, a completely unsupervised metric that requires neither reference images nor quality-labelled training data. NIQE builds a multivariate Gaussian (MVG) model of features extracted from corpus of undistorted natural images, then measures the Mahalanobis distance between this model and features extracted from the test image:

$$D(v_1, v_2, \Sigma_1, \Sigma_2) = \sqrt{ (v_1 - v_2)^T \left( \frac{\Sigma_1 + \Sigma_2}{2} \right)^{-1} (v_1 - v_2) }$$

Lower NIQE values indicate better quality. Because NIQE is trained only on pristine natural images (not distorted pairs), it is truly "opinion-free" and generalises well to new distortion types. However, it is calibrated to photographic realism and will penalise intentionally stylised or high-grain images.

#### CLIP-IQA — Zero-Shot Quality via Contrastive Language-Image Pre-Training

Wang et al. (2023, AAAI) leveraged CLIP's joint vision-language embedding space for zero-shot IQA. The method defines antonym text prompts (e.g. "a good photo" / "a bad photo") and uses the cosine similarity between the image embedding and each text embedding as a quality signal. CLIP-IQA requires no IQA-specific training and achieves competitive SRCC on multiple benchmarks, particularly for assessing aesthetics and high-level attributes (sharpness, colorfulness, brightness). Its limitation is sensitivity to semantic content — images of aesthetically rich subjects may score high regardless of technical distortions.

---

### 1.4 Deep Learning IQA Models

#### MUSIQ — Multi-Scale Image Quality Transformer

Ke et al. (2021, ICCV) addressed a practical limitation of CNN-based IQA: fixed-resolution input requirements force resizing or cropping, which itself introduces quality-irrelevant distortions. MUSIQ uses a multi-scale patch-based Vision Transformer that accepts images at their native resolution. Each scale's patches are encoded independently by a shared ViT, and a cross-scale attention mechanism fuses representations across scales. MUSIQ trained on AVA and SPAQ achieves state-of-the-art SRCC on both aesthetic (AVA: 0.726) and technical quality (SPAQ: 0.917) benchmarks. For ISP applications, MUSIQ is valuable as a no-reference proxy for MOS in large-scale parameter sweeps where assembling a human panel is impractical.

#### NIMA — Neural Image Assessment

Talebi and Milanfar (2018) reformulated quality prediction as a distribution estimation problem. Rather than predicting a single scalar quality score, NIMA trains a CNN (InceptionV3 backbone) to predict the full histogram of human opinion ratings $p(s)$ for each rating bin $s \in \{1, ..., 10\}$. The loss function is the Earth Mover's Distance (EMD) between predicted and ground-truth score distributions. The expected quality is then $\hat{q} = \sum_s s \cdot p(s)$. NIMA captures rater disagreement and supports both aesthetic (AVA dataset) and technical quality (TID2013) models.

#### HyperIQA — Hyper Network for Content-Aware IQA

Su et al. (2020, CVPR) argued that local quality is strongly content-dependent: blur on a face is more perceptually salient than blur on a uniform background. HyperIQA uses a two-branch architecture: a content understanding network extracts high-level semantic features, which are used to condition a quality prediction network via a hyper network that dynamically generates quality-sensitive local filters. This approach achieves state-of-the-art SRCC/PLCC on LIVE, CSIQ, KADID-10k, and BID benchmarks at the time of publication.

---

### 1.5 Correlation with MOS: SRCC, PLCC, KRCC

Human opinion is the ultimate quality reference. Subjective experiments produce a Mean Opinion Score (MOS) for each distorted image. When evaluating whether a metric correlates with MOS across a dataset, three rank-correlation statistics are standard:

- **SRCC** (Spearman Rank Correlation Coefficient): measures monotonic rank correlation; robust to outliers and non-linear relationships. Values range $[-1, 1]$; $> 0.9$ is considered excellent.
- **PLCC** (Pearson Linear Correlation Coefficient): measures linear correlation after a 4-parameter logistic mapping of predicted scores; sensitive to the scale and linearity of predictions.
- **KRCC** (Kendall Rank Correlation Coefficient): measures the proportion of concordant vs. discordant pairs; more conservative than SRCC, often $\approx 0.7\times$ SRCC numerically.

SRCC is most commonly reported in IQA papers as the primary correlation indicator, with PLCC as a secondary check for calibration quality.

---

### 1.6 Metric Selection Guide

| Scenario | Recommended metric(s) | Rationale |
|---|---|---|
| ISP version A/B comparison (lab, reference available) | SSIM + LPIPS | SSIM catches structural loss; LPIPS catches texture hallucinations |
| Denoising / NR evaluation (reference available) | PSNR + SSIM | Well-understood; easy to reproduce |
| Super-resolution or generative ISP | LPIPS (primary) + PSNR (secondary) | LPIPS correlates better with human preference for high-frequency content |
| No reference available (field images) | BRISQUE or NIQE | Deployable without ground truth |
| User preference modelling / tuning for aesthetics | MOS + SRCC | Captures subjective distribution; essential for camera tuning |
| Evaluating semantic task (detection, OCR) | Task accuracy (AP, WER) | Perceptual metrics do not proxy task metrics |
| Cross-distortion-type benchmark (academic) | SRCC/PLCC on LIVE / TID2013 | Standard leaderboard comparison |

---

## §2 标定 (Calibration)

### 2.1 Why Subjective Calibration Matters

No objective metric — however well-designed — can replace direct human feedback. All leading NR and FR metrics have been calibrated or validated against MOS datasets. When deploying an ISP on a new device or target application (social media, surveillance, medical imaging), the set of perceptually important attributes shifts. A metric calibrated on Gaussian noise and JPEG compression (LIVE) will not necessarily correlate with quality degradation from a computational photography HDR merger or a neural denoiser.

Calibration in this context means: (1) collecting MOS scores relevant to your distortion types and use case, and (2) verifying that your chosen metric actually correlates with those scores (SRCC > 0.85 is a reasonable threshold).

### 2.2 ITU-T P.910 MOS Methodology

The ITU-T P.910 recommendation defines the standard single-stimulus absolute category rating (ACR) protocol for image quality:

1. **Stimuli preparation:** Prepare reference and distorted images at target display resolution. Randomise presentation order to prevent context bias.
2. **Rating scale:** Five-point ACR scale: 5 = Excellent, 4 = Good, 3 = Fair, 2 = Poor, 1 = Bad.
3. **Observer panel:** At least 15 naive observers (not image-processing experts). Screen for normal or corrected-to-normal vision.
4. **Environment:** Controlled room lighting (D65 illuminant, 200 lux ambient), standardised viewing distance (3–6× picture height for monitors).
5. **Training session:** Show a few anchor stimuli (clearly bad and clearly good) before the test session.
6. **Score aggregation:** MOS = mean of valid ratings per image. Apply outlier rejection (ratings more than 2 standard deviations from the mean are excluded).

A modified double-stimulus impairment scale (DSIS) is used when a visible reference is shown side-by-side. DSIS ratings are more sensitive to subtle degradations but require more time per trial.

### 2.3 Practical Tools

For internal ISP quality studies, three practical approaches are common:

- **MUSIQ** (Multi-Scale Image Quality Transformer, Ke et al. 2021) can be used as a proxy for MOS when running a large-scale sweep without human panels; it produces reliable relative rankings on natural-scene content.
- **Custom crowdsourcing** via platforms (MTurk, Scale AI): pair-comparison (2AFC) is more reliable than direct rating when the quality differences are subtle. Collect at least 5 independent ratings per stimulus pair and apply inter-rater agreement (Krippendorff's $\alpha > 0.6$).
- **Internal tooling:** Build a simple web tool with side-by-side A/B display, randomised order, and rating export. Even 8–10 trained engineers can produce a useful relative ranking for ISP tuning decisions.

---

## §3 调参 (Tuning)

### 3.1 Integrating Metrics into the ISP Tuning Loop

Modern ISP tuning is increasingly data-driven. Given a set of calibration scenes captured under controlled conditions, the tuning loop iterates:

1. Apply candidate parameter set $\theta$ to the ISP.
2. Compute SSIM and LPIPS against reference images.
3. Update $\theta$ using gradient-free optimisation (Bayesian optimisation, CMA-ES) or, for differentiable ISP modules, gradient descent.

A typical combined objective is:

$$\mathcal{L}(\theta) = \lambda_1 \cdot (1 - \text{SSIM}) + \lambda_2 \cdot \text{LPIPS} + \lambda_3 \cdot \text{PSNR\_loss}$$

where $\lambda_1, \lambda_2, \lambda_3$ are trade-off weights tuned per module type. For denoising modules, a common starting point is $\lambda_1 = 0.5, \lambda_2 = 0.5, \lambda_3 = 0$. For sharpening modules, increasing $\lambda_2$ relative to $\lambda_1$ pushes the tuner toward perceptually sharper textures.

### 3.2 When PSNR and LPIPS Give Conflicting Guidance

PSNR and LPIPS frequently disagree when evaluating super-resolution, generative denoisers, and aggressive sharpening:

- **PSNR prefers smooth/blurry outputs**: a mean-regressed reconstruction minimises MSE but averages away fine texture, yielding high PSNR and low perceptual quality.
- **LPIPS prefers textured outputs**: a stochastic or GAN-based reconstruction that synthesises plausible texture achieves better LPIPS but higher pixel-level error (lower PSNR).

The practical rule: in a production ISP targeting human viewing, **use LPIPS as the primary optimisation target** once baseline PSNR is acceptable (e.g. PSNR > 30 dB). Use PSNR as a guard rail to prevent catastrophic pixel-level degradation. If LPIPS improves but PSNR drops more than 1–2 dB below baseline, inspect the outputs manually — the improvement may be texture hallucination rather than genuine quality gain.

### 3.3 Threshold Selection for "Acceptable" Quality

Rather than optimising a continuous score, ISP tuning often needs a hard pass/fail gate. Empirically derived thresholds for natural scene images:

| Metric | Minimum acceptable | Notes |
|---|---|---|
| SSIM | > 0.85 | Below 0.80 indicates visible structural degradation |
| LPIPS (AlexNet) | < 0.15 | Above 0.25 is clearly perceptible |
| BRISQUE | < 40 | Higher values indicate strong distortion presence |
| PSNR (color camera) | > 32 dB | For final ISP output vs. ground truth |

These are starting points, not universals. Always validate thresholds against your specific content and user population.

### 3.4 Metric Selection Decision Tree

In ISP tuning and evaluation practice, engineers face a large menu of available metrics. The following decision tree provides a systematic selection framework.

#### 3.4.1 Decision Tree

```
Is a clean reference image (ground truth) available?
│
├─ [Reference available] → Use Full-Reference (FR-IQA) metrics
│   │
│   ├─ Need high-fidelity perceptual evaluation?
│   │   ├─ Sensitive to texture/detail/style transfer? → LPIPS (feature-space perceptual distance)
│   │   └─ Need to assess both structure and texture consistency? → DISTS (dual structure+texture)
│   │
│   ├─ Need fast computation and interpretability?
│   │   ├─ Multi-scale robustness (variable resolution/viewing distance)? → MS-SSIM
│   │   └─ Single scale sufficient (standard tuning loop)? → SSIM
│   │
│   └─ Only need simple baseline/quick sanity check? → PSNR
│       (Note: PSNR does not reflect perceptual quality; use only as a guard rail)
│
└─ [No reference available] → Use No-Reference (NR-IQA) metrics
    │
    ├─ General natural-scene quality assessment?
    │   ├─ No training data (fully blind)? → NIQE (natural statistics model)
    │   └─ Small distorted training set available? → BRISQUE (spatial statistics + SVR)
    │
    ├─ Training dataset available, need learned assessment?
    │   ├─ Content-aware (face/texture differences salient)? → HyperIQA (dynamic prediction)
    │   └─ Multi-scale input required (arbitrary resolution)? → MUSIQ (Transformer)
    │
    └─ VLM/large-model resources available, targeting state-of-the-art?
        └─ → Q-Align (MLLM-based quality/aesthetic alignment, ICLR 2024)
            (supports quality scoring, aesthetic assessment, and text description modes)
```

#### 3.4.2 Metric Sensitivity to ISP Distortion Types

Different metrics respond very differently to ISP-specific distortions. The table below summarises engineering experience:

| Metric | Noise sensitivity | Blur sensitivity | Color shift sensitivity | Blocking sensitivity | Best-fit tuning scenario |
|--------|------------------|-----------------|------------------------|---------------------|--------------------------|
| PSNR | High | Medium | Low | Medium | Quick sanity check, quantifying overall distortion magnitude |
| SSIM | Medium | High | Low | High | Structural integrity, denoising/deblurring tuning |
| LPIPS | Medium | High | Medium | Medium | Generative ISP, super-resolution perceptual quality |
| DISTS | Medium | High | High | Medium | Texture + color dual assessment, CCM/AWB fine-tuning |
| BRISQUE | High | High | Low | High | No-reference fast scanning, production image quality inspection |

Key notes:
- **Color-blind zone**: PSNR and SSIM are insensitive to color temperature drift (AWB misalignment) because they are primarily luminance-based. For AWB tuning, always add DISTS or per-channel SSIM as a supplement.
- **BRISQUE dual high sensitivity**: Makes it an ideal tool for quickly detecting whether NR strength is too low (too much noise) or compression ratio too high (visible blocking).
- **LPIPS high blur sensitivity**: Compared to PSNR, LPIPS is more sensitive to detail loss from skin smoothing or over-denoising; recommended as a supplementary metric for portrait skin enhancement tuning.

#### 3.4.3 Arbitration Rules When PSNR and SSIM Disagree

In ISP tuning practice, PSNR and SSIM frequently give conflicting verdicts:

**Case 1: High PSNR, low SSIM**
- Typical cause: local structural degradation (ringing artefacts, demosaic false colour, local over-sharpening) with small pixel-level MSE overall.
- **Ruling: trust SSIM.** Structural degradation is visually obvious; the high PSNR is a false positive. Inspect the sharpening/demosaic parameter range.

**Case 2: Low PSNR, high SSIM**
- Typical cause: global luminance shift or mild tone change (e.g. Gamma curve adjustment) causes systematically large pixel differences, but structural relationships are preserved.
- **Ruling: confirm with human eye.** If visually acceptable and SSIM > 0.90, ignoring a 1–2 dB PSNR drop is reasonable.

**Case 3: Both PSNR and SSIM are high, but LPIPS is poor**
- Typical cause: a generative super-resolution or deep denoiser has synthesised visually "unrealistic" texture (texture hallucination) that pixel-level metrics cannot detect.
- **Ruling: trust LPIPS** and trigger manual inspection. This is the most common "metric trap" in generative ISP.

#### 3.4.4 Production IQA Pipeline Threshold Tiers

In a mass-production environment, a three-tier gating strategy is recommended:

**Tier 1 — Automatic pass (no human intervention)**
- SSIM > 0.92 AND LPIPS < 0.12 AND BRISQUE < 35
- Meaning: image quality is excellent; proceed to the next stage.

**Tier 2 — Manual sampling required (yellow-light warning)**
- 0.85 ≤ SSIM ≤ 0.92, or 0.12 ≤ LPIPS ≤ 0.20, or 35 ≤ BRISQUE ≤ 50
- Meaning: metrics are in the boundary zone; sample 10–20% for human confirmation.

**Tier 3 — Automatic rejection (red-light failure)**
- SSIM < 0.85 OR LPIPS > 0.25 OR BRISQUE > 55
- Meaning: visibly obvious distortion present; block release and re-tune.

> **Important**: the thresholds above are calibrated for natural daylight scenes (rich colour, moderate texture density). For low-light night scenes (elevated noise floor) and HDR merge scenes (dynamic range exceeding standard statistics), thresholds must be relaxed; establish separate reference baselines per scene category.

#### 3.4.5 Per-Module Metric Combination Recommendations

**Denoising module tuning**

Denoising is the scenario where PSNR and perceptual quality disagree most sharply. Over-denoising raises PSNR (noise is suppressed, pixel error shrinks) while degrading LPIPS (texture detail is smoothed out).

Recommended combination:
1. **Primary**: SSIM (structural fidelity) + LPIPS (texture loss)
2. **Guard rail**: PSNR > 30 dB (prevents under-denoising)
3. **Decision logic**: subject to PSNR > 30 dB, maximise SSIM × 0.4 + (1 − LPIPS) × 0.6
4. **Manual checkpoint**: when NR_Luma_Strength > 50, force manual inspection of hair/fibre/fabric texture regions

**Sharpening / USM module tuning**

Over-sharpening fails via ringing artefacts and halos. Both appear well in SSIM, but PSNR may falsely rise due to contrast enhancement from sharpening.

Recommended combination:
1. **Primary**: SSIM (detects structural damage from ringing/halos)
2. **Auxiliary**: BRISQUE (detects over-sharpening statistical anomalies in the no-reference regime)
3. **Hard constraint**: SSIM must not fall below 0.95× the reference (unsharpened) version

**AWB / CCM colour tuning**

Colour tuning is the scenario where both PSNR and SSIM are least sensitive, since both are primarily luminance-based. Colour metrics require dedicated treatment.

Recommended combination:
1. **Primary**: minimum per-channel SSIM (min(SSIM_R, SSIM_G, SSIM_B)), or DISTS (more sensitive to colour shifts)
2. **Auxiliary**: ΔE₂₀₀₀ colour difference (quantifies colour reproduction accuracy against standard colour chart reference)
3. **Perceptual threshold**: ΔE₂₀₀₀ < 3 is imperceptible; ΔE₂₀₀₀ > 6 is a clearly visible colour cast

**Super-resolution / neural denoising tuning**

Generative methods (GAN- or diffusion-based SR) produce outputs that differ pixel-by-pixel from the reference yet are perceptually plausible. PSNR significantly underestimates perceptual quality in this regime.

Recommended combination:
1. **Primary**: LPIPS (perceptual distance) + MUSIQ or HyperIQA (blind assessment)
2. **Auxiliary**: FID (Fréchet Inception Distance, evaluates how close the output distribution is to natural images)
3. **Decision principle**: PSNR is not a primary optimisation target; use only as a floor guard (PSNR > 25 dB to prevent catastrophic distortion)

#### 3.4.6 Composite Score and Drift Monitoring

**Weighted composite score**

For different tuning objectives, define a composite quality score $Q_{\text{composite}}$:

$$Q_{\text{composite}} = w_1 \cdot \text{SSIM} + w_2 \cdot (1 - \text{LPIPS}) + w_3 \cdot \frac{\text{PSNR} - \text{PSNR}_{\min}}{\text{PSNR}_{\max} - \text{PSNR}_{\min}}$$

Typical weight settings:
- Denoising: $w_1 = 0.35, w_2 = 0.50, w_3 = 0.15$
- Sharpening: $w_1 = 0.60, w_2 = 0.30, w_3 = 0.10$
- Compression: $w_1 = 0.40, w_2 = 0.40, w_3 = 0.20$

**Quarterly metric drift monitoring**

As the ISP algorithm evolves, metric-to-perception correlations drift (training data distribution changes, new distortion types are introduced). Recommended quarterly checks:
- Recompute reference baselines with the latest ISP version.
- Update BRISQUE/NIQE reference distributions (both are sensitive to scene content distribution).
- Verify that LPIPS weights (VGG/AlexNet) remain correlated with the current dominant distortion types.

**NR metrics as CI gates — known risks**

When using BRISQUE/NIQE as hard gates in a CI pipeline, watch for:
1. **Scene distribution drift**: if the test set gains many low-light night scenes, NR metric means shift systematically; use relative thresholds ("≤ X% worse than baseline") rather than absolute values.
2. **Batch contamination**: if uncalibrated scenes (factory fixtures, resolution test charts) enter the test batch, NR metrics will produce anomalously low scores and generate false failures. Filter input content before running CI.
3. **Multi-camera fusion artefacts**: at fusion seam boundaries (wide/main/tele switch), BRISQUE may fire much higher than for single-camera frames; set looser thresholds specifically for seam regions.

---

## §3b VLM-Based IQA: Q-Bench and Q-Align

The emergence of Multimodal Large Language Models (MLLMs) opens a qualitatively new paradigm for IQA: instead of predicting a scalar score from image features, an MLLM can answer open-ended quality questions about an image in natural language, then be aligned to produce calibrated numeric scores.

### Q-Bench (ICLR 2024)

Wu et al. (2024, ICLR) introduced Q-Bench, a benchmark for evaluating the low-level visual perception abilities of MLLMs. It consists of three tasks: (1) **LLVisionQA** — open-ended low-level question answering (e.g. "Is this image sharp?", "What distortions are present?"); (2) **LLDescribe** — generating accurate textual descriptions of image quality; (3) **Quality Scoring** — predicting a MOS-aligned numeric score. Q-Bench revealed that off-the-shelf MLLMs such as GPT-4V and InstructBLIP already have substantial low-level visual perception capability, but their quality scores are not well-calibrated against human MOS. The benchmark provides a standardised evaluation protocol for MLLM-based quality perception.

### Q-Align (ICML 2024)

Wang et al. (2024, ICML) proposed Q-Align, a training methodology that fine-tunes a general-purpose MLLM (mPLUG-Owl2) to predict image quality and aesthetic scores by aligning the model's text output with discrete quality level labels (Bad / Poor / Fair / Good / Excellent). The key insight is that MLLMs should be trained to output quality ratings in the tokenised text space — not as regression targets — to leverage the full generative capability of the language model. Q-Align achieves state-of-the-art performance on KonIQ-10k (SRCC = 0.921), SPAQ (SRCC = 0.917), and AVA (SRCC = 0.752), while also supporting aesthetic assessment and text description in a unified model.

**ISP engineering implications of VLM-based IQA:**
- Q-Align can serve as a high-fidelity proxy for MOS in large-scale ISP parameter sweeps, reducing the need for expensive human evaluation campaigns.
- The model's language output (e.g. "The image is blurry in the background but sharp on the subject") provides qualitative diagnostics not available from scalar metrics.
- Deployment constraint: Q-Align requires a 7B-parameter MLLM backbone; inference latency is ~500 ms per image on a single GPU — suitable for offline evaluation pipelines but not real-time tuning loops.
- For mobile photography quality assessment specifically, the SPAQ fine-tuned variant of Q-Align is recommended over the generic model.

---

## §4 Artifacts

### 4.1 PSNR Failure Modes

**Blur reward**: PSNR rewards smooth outputs that minimise MSE. A Gaussian-blurred image (σ = 2) of a sharp scene may achieve PSNR = 35 dB while looking visibly soft. A sharp reconstruction with occasional ringing may score PSNR = 33 dB but appear preferable to most observers. This is the primary reason PSNR alone is insufficient for evaluating denoising and SR pipelines.

**Clipping insensitivity**: PSNR is symmetric around zero error. A blown highlight (pixel clipped from 250 to 255) and a crushed shadow (pixel compressed from 5 to 0) contribute equal MSE, yet have very different perceptual and semantic consequences.

### 4.2 SSIM Failure Modes

**Hue shift blindness**: SSIM is typically computed on luminance (Y channel) only. A global hue shift — for example, a color temperature error in AWB — leaves luminance statistics nearly unchanged, resulting in a high SSIM score despite a clearly visible color cast. For color quality in ISP, compute SSIM separately on each channel and report the minimum, or use a color-weighted variant.

**Window size sensitivity**: The default 11×11 Gaussian window in SSIM can miss small structural errors (e.g. demosaic false color on fine diagonal edges) or be over-sensitive to alignment errors in the reference.

**Spatial averaging mask**: SSIM's final score averages over all windows, including homogeneous regions where both images score 1.0. A small strongly-distorted region (e.g. face with compression blocking) can be diluted by large uniform sky, leading to optimistic global scores.

### 4.3 LPIPS Failure Modes

**Semantic sensitivity**: LPIPS uses high-level VGG features that encode semantic content. Two images of different objects but with similar textures may score low LPIPS despite being semantically different. Conversely, a spatially shifted version of an image (e.g. 1-pixel global translation) can score high LPIPS even though the images are nearly identical — LPIPS is not shift-invariant.

**Geometric distortion insensitivity**: LPIPS tolerates small geometric warps that preserve local feature distributions. Lens distortion correction artefacts (barrel/pincushion residuals) may not be penalised adequately.

**Backbone dependency**: LPIPS with AlexNet weights and LPIPS with VGG weights do not always agree on rank ordering. Always specify which backbone was used when reporting results.

### 4.4 NR Metric Failure Modes

**BRISQUE on out-of-distribution content**: BRISQUE was trained on LIVE database distortions (Gaussian blur, JPEG, noise, JPEG2000, fast-fading). It fails on HDR content, astrophotography, medical images, infrared imagery, and artistic/stylised images — content whose NSS statistics differ fundamentally from natural daylight scenes.

**NIQE penalising high-grain aesthetics**: NIQE is calibrated on clean photographic images. Film-grain aesthetics, intentional high-ISO looks, and deliberate under-exposure all lower NIQE scores even when the images are aesthetically intentional and preferred by the target audience.

**CLIP-IQA semantic leakage**: CLIP-IQA scores are strongly influenced by the semantic content of the image (beautiful landscapes score high regardless of noise level). This makes it unreliable for comparing different distortion types applied to the same scene.

---

## §5 评测 (Evaluation)

### 5.1 Standard Benchmarks

Three databases dominate the IQA literature:

**LIVE (Sheikh et al., 2006)**: 779 distorted images from 29 reference images; 5 distortion types (JPEG, JPEG2000, Gaussian blur, white noise, fast-fading channel). Subjects: 161 observers, ~25 ratings per image. The oldest and most widely used benchmark; however, its 5 distortion types do not cover modern ISP artefacts.

**TID2013 (Ponomarenko et al., 2015)**: 3000 distorted images from 25 reference images; 24 distortion types including noise, blur, color distortions, and JPEG. 971 observers, 524k pairwise comparisons. TID2013 is the most comprehensive classical benchmark but was collected primarily in Eastern European lab settings; mean ratings can be noisier than LIVE.

**KADID-10k (Lin et al., 2019)**: 10,125 distorted images from 81 reference images; 25 distortion types at 5 severity levels. Crowdsourced MOS via Amazon MTurk; the largest uniform-distortion benchmark. KADID-10k is particularly useful for evaluating NR metrics because of its scale and diversity.

**SPAQ (Fang et al., CVPR 2020)**: 11,125 images captured by smartphones in real-world conditions, with MOS collected from 84 observers under standardised viewing conditions. SPAQ is currently the closest NR-IQA benchmark to real mobile ISP output distribution. Its distortion sources span the full mobile ISP pipeline (defocus blur, low-light noise, HDR over-exposure, JPEG compression). Compared to the synthetic distortions in LIVE/TID2013, SPAQ evaluation results are more predictive of ISP engineering optimisation outcomes. When validating NR metrics for mobile photography quality, SPAQ-based SRCC should be the primary reporting metric.

### 5.2 Published SRCC/PLCC Numbers

Representative results from published papers (SRCC / PLCC):

| Method | LIVE | TID2013 | KADID-10k |
|---|---|---|---|
| PSNR | 0.866 / 0.872 | 0.687 / 0.678 | 0.676 / 0.681 |
| SSIM | 0.948 / 0.945 | 0.777 / 0.795 | 0.724 / 0.718 |
| MS-SSIM | 0.951 / 0.956 | 0.830 / 0.834 | 0.802 / 0.803 |
| LPIPS (VGG) | 0.932 / 0.928 | 0.670 / 0.706 | 0.721 / 0.735 |
| DISTS (FR) | 0.954 / 0.960 | 0.830 / 0.845 | 0.861 / 0.867 |
| BRISQUE (NR) | 0.939 / 0.942 | 0.567 / 0.571 | 0.528 / 0.534 |
| NIQE (NR) | 0.908 / 0.902 | 0.313 / 0.386 | 0.374 / 0.428 |
| HyperIQA (NR) | 0.962 / 0.966 | 0.840 / 0.858 | 0.852 / 0.845 |
| MUSIQ (NR) | — / — | — / — | — / — |
| Q-Align (NR) | — / — | — / — | — / — |

Note: NR numbers are particularly sensitive to training set overlap. Always check that your evaluation set does not overlap with the metric's training set. MUSIQ and Q-Align are primarily evaluated on in-the-wild datasets (KonIQ-10k, SPAQ, AVA) rather than the classical synthetic-distortion benchmarks above.

### 5.3 Building Your Own IQA Pipeline

For production ISP evaluation, a lightweight but robust pipeline:

1. **Collect reference scenes**: 30–100 carefully selected scenes covering your target use cases (portrait, landscape, low-light, backlit, high-texture). Capture with a calibrated reference camera or RAW+reference rig.

2. **Select your distortion set**: Choose distortions representative of your ISP failure modes — not generic LIVE distortions.

3. **Compute FR metrics**: Run PSNR, SSIM, and LPIPS on your distorted vs. reference pairs. Store results in a CSV with per-scene breakdowns.

4. **Run NR metrics on field images**: For images captured without a reference, use BRISQUE and NIQE to flag anomalies.

5. **Periodic MOS collection**: Run a quarterly 2AFC study with 10–15 observers on a 50-image stratified sample. Track SRCC between your automated metrics and MOS over time. If SRCC drops below 0.85, recalibrate your metric weights.

6. **Regression tests**: Integrate SSIM and BRISQUE into your CI pipeline with thresholds from §3.3. A merge that degrades average SSIM by > 0.01 on the reference set triggers a flag for human review.

---

## §6 代码 (Code)

See [`ch04_iqa_notebook.ipynb`](ch04_iqa_notebook.ipynb) for a self-contained walkthrough of:
- Generating synthetic distortion variants of a reference image
- Computing PSNR, SSIM, and LPIPS for each variant
- Visualising metric disagreements (the blur/artefact paradox)
- Computing SRCC between metric rankings

---

## §7 Glossary

| Term | Definition |
|------|------------|
| **FR-IQA** | Full-Reference Image Quality Assessment. Requires a clean reference image alongside the distorted image. |
| **NR-IQA / Blind IQA** | No-Reference IQA. Predicts quality from the distorted image alone without ground truth. |
| **MOS** | Mean Opinion Score. The average of human rating scores for a given image; the ground truth in IQA research. |
| **SRCC** | Spearman Rank Correlation Coefficient. Measures monotonic rank correlation between predicted scores and MOS; range $[-1, 1]$. |
| **PLCC** | Pearson Linear Correlation Coefficient. Measures linear correlation after a 4-parameter logistic mapping. |
| **KRCC** | Kendall Rank Correlation Coefficient. Measures concordant vs. discordant pairs; numerically $\approx 0.7 \times$ SRCC. |
| **PSNR** | Peak Signal-to-Noise Ratio (dB). Based on MSE; high values indicate low pixel-level error but do not guarantee perceptual quality. |
| **SSIM** | Structural Similarity Index. Decomposes comparison into luminance, contrast, and structure components; range $[-1, 1]$, practical range $[0, 1]$. |
| **MS-SSIM** | Multi-Scale SSIM. Extends SSIM across 5 spatial scales for display-resolution robustness. |
| **LPIPS** | Learned Perceptual Image Patch Similarity. Feature-space distance using a VGG or AlexNet backbone calibrated on human 2AFC judgements; lower = more similar. |
| **DISTS** | Distribution Shift in Feature Space. Decouples structure and texture similarity in VGG feature space; more robust than LPIPS to texture swapping and film grain. |
| **BRISQUE** | Blind/Referenceless Image Spatial Quality Evaluator. Uses MSCN coefficient statistics and SVR; score 0–100, lower = better. |
| **NIQE** | Natural Image Quality Evaluator. Opinion-free; measures Mahalanobis distance from a natural image MVG model; lower = better. |
| **MUSIQ** | Multi-Scale Image Quality Transformer. ViT-based NR-IQA accepting native-resolution images via cross-scale attention. |
| **HyperIQA** | Hyper network IQA. Content-aware NR model using a hyper network to generate dynamic quality-sensitive filters. |
| **NIMA** | Neural Image Assessment. Predicts the full distribution of human quality ratings using EMD loss; outputs expected score and rater disagreement. |
| **Q-Bench** | MLLM low-level visual perception benchmark (ICLR 2024 Spotlight); evaluates QA, description, and quality scoring tasks. |
| **Q-Align** | MLLM fine-tuned on discrete quality level tokens for calibrated MOS prediction (ICLR 2024). |
| **SPAQ** | Smartphone Photography Attribute and Quality dataset. 11,125 real smartphone images with MOS; most representative NR-IQA benchmark for mobile ISP. |
| **ACR** | Absolute Category Rating. Single-stimulus 5-point rating protocol defined by ITU-T P.910. |
| **DSIS** | Double-Stimulus Impairment Scale. Paired reference+distorted rating; more sensitive to subtle degradations than ACR. |
| **2AFC** | Two-Alternative Forced Choice. Observers pick the better of two stimuli; more reliable than direct rating for subtle quality differences. |
| **EMD** | Earth Mover's Distance (Wasserstein distance). Loss function used by NIMA to compare rating distributions. |
| **FID** | Fréchet Inception Distance. Measures the distance between output image distribution and natural image distribution; used to evaluate generative ISP models. |
| **MSCN** | Mean Subtracted Contrast Normalised. Normalised image coefficients whose statistics BRISQUE and NIQE model. |
| **GGD / AGGD** | Generalised Gaussian Distribution / Asymmetric GGD. Statistical model fitted to MSCN coefficients in BRISQUE. |

---

## §8 Engineering Recommendations

The following thresholds and rules are derived from ISP production experience with natural daylight scenes on mobile cameras. They are starting points — always validate against your specific content, device, and user population.

### 8.1 Metric Thresholds for ISP Pass/Fail Gates

| Metric | Auto-pass threshold | Warning threshold | Auto-fail threshold |
|--------|--------------------|--------------------|---------------------|
| SSIM | > 0.92 | 0.85 – 0.92 | < 0.85 |
| LPIPS (AlexNet) | < 0.12 | 0.12 – 0.20 | > 0.25 |
| BRISQUE | < 35 | 35 – 50 | > 55 |
| PSNR | > 35 dB | 30 – 35 dB | < 28 dB |
| ΔE₂₀₀₀ (colour) | < 3 | 3 – 6 | > 6 |

### 8.2 Per-Module Primary Metric Recommendations

| ISP Module | Primary metric | Guard-rail metric | Notes |
|------------|---------------|-------------------|-------|
| Denoising | SSIM + LPIPS (joint) | PSNR > 30 dB | PSNR-only tuning over-smooths texture |
| Sharpening / USM | SSIM | BRISQUE | PSNR can rise falsely with contrast boost |
| Super-resolution | LPIPS | PSNR > 25 dB | PSNR underestimates generative SR quality |
| AWB / CCM | DISTS or per-channel SSIM | ΔE₂₀₀₀ | PSNR and SSIM are colour-blind |
| HDR merging | SSIM + LPIPS | NIQE | BRISQUE may misfire on HDR statistics |
| Compression (JPEG/HEIF) | SSIM + PSNR | BRISQUE | Balance fidelity and file-size constraints |

### 8.3 Practical Deployment Notes

1. **Metric-MOS recalibration**: Run a 2AFC human study quarterly on a 50-image stratified sample. If SRCC between your automated metric and MOS drops below 0.85, recalibrate metric weights rather than adjust thresholds.

2. **SPAQ over LIVE for mobile ISP**: When validating NR metrics on mobile photography, report SRCC on SPAQ rather than LIVE. LIVE's synthetic distortions underrepresent the real ISP failure modes (HDR ghost, defocus transition, AI denoising over-smoothing).

3. **LPIPS backbone choice**: Use VGG-16 for final evaluation reports (higher MOS correlation); use AlexNet for training-time perceptual loss (4–6× faster, avoids GPU memory pressure in the training loop).

4. **Q-Align for large-scale sweeps**: When tuning ISP parameters across 1000+ scene variants without a human panel, Q-Align is the highest-fidelity automated proxy for MOS currently available. Use the SPAQ-fine-tuned variant for mobile photography.

5. **CI pipeline guard**: Use relative thresholds for NR metrics in CI (e.g. "BRISQUE must not increase more than 5 points vs. the previous release baseline"), not absolute thresholds. Absolute NR thresholds break when the test scene set distribution changes.

6. **Color metrics are mandatory for AWB/CCM**: Neither PSNR nor SSIM catches a 3-point ΔE₂₀₀₀ colour error. Always add ΔE₂₀₀₀ or DISTS to any colour module evaluation loop.

---

> **Engineer's Note: Perceptual Quality Metric Trade-offs**
>
> **LPIPS vs. SSIM correlation with human preference**: In practical ISP tuning, LPIPS typically achieves Spearman correlation of 0.75–0.85 with subjective MOS, while SSIM achieves only 0.55–0.65. The root cause: SSIM equally weights luminance, contrast, and structure components, missing high-frequency texture distortion; LPIPS operates in the deep feature space of VGG/AlexNet and catches edge ringing, colour drift, and similar perceptual defects. When a denoising network is trained to optimise SSIM, the result is typically over-smoothed — detail is destroyed and MOS actually drops. Switching to LPIPS as the perceptual loss raises subjective scores noticeably, though PSNR in textured regions will dip 0.5–1.5 dB. This trade-off is not a bug; it is the fidelity-vs-perceptual-quality tension baked into every ISP.
>
> **VGG vs. AlexNet feature layer selection**: In the LPIPS reference implementation, VGG-16's conv3_3 layer features are more sensitive to over-sharpening halos and smearing artefacts typical of mobile ISP, with ~8% higher correlation than AlexNet relu2 features on those distortion types. However, VGG inference is 4–6× slower than AlexNet. Recommended practice: use AlexNet LPIPS in the training loop to control GPU memory and training time; use VGG LPIPS for final evaluation reports. Verify that the two backbones agree on rank ordering before reporting.
>
> **MOS variance and experiment design**: Cross-rater MOS standard deviation is typically ±0.4–0.6. A MOS difference smaller than 0.3 between two algorithm versions is statistically insignificant — never make a version decision on it. To reduce variance: standardise display device (same phone screen or calibrated monitor), ambient illuminance (200–400 lux), viewing distance (25 cm for phone, 50 cm for monitor), and use double-blind randomised comparison design. Panel size should be at least 20 observers, with at least 5 trained expert reviewers. Internal quick-validation with 10 people is acceptable, but always report confidence intervals to avoid mistaking noise for algorithmic gain.
>
> *References: Zhang et al., "The Unreasonable Effectiveness of Deep Features as a Perceptual Metric," CVPR 2018; Wang et al., "Image Quality Assessment: From Error Visibility to Structural Similarity," IEEE TIP 2004; ITU-R BT.500-13, "Methodologies for the Subjective Assessment of the Quality of Television Images"*

---

## 参考资料 (References)

1. Wang, Z., Bovik, A. C., Sheikh, H. R., & Simoncelli, E. P. (2004). Image quality assessment: From error visibility to structural similarity. *IEEE Transactions on Image Processing*, 13(4), 600–612.

2. Wang, Z., Simoncelli, E. P., & Bovik, A. C. (2003). Multiscale structural similarity for image quality assessment. *Asilomar Conference on Signals, Systems and Computers*, Vol. 2, pp. 1398–1402.

3. Zhang, R., Isola, P., Efros, A. A., Shechtman, E., & Wang, O. (2018). The unreasonable effectiveness of deep features as a perceptual metric. *CVPR 2018*.

4. Mittal, A., Moorthy, A. K., & Bovik, A. C. (2012). No-reference image quality assessment in the spatial domain. *IEEE Transactions on Image Processing*, 21(12), 4695–4708. (BRISQUE)

5. Mittal, A., Soundararajan, R., & Bovik, A. C. (2013). Making a "completely blind" image quality analyzer. *IEEE Signal Processing Letters*, 20(3), 209–212. (NIQE)

6. Wang, J., Chan, K. C. K., & Loy, C. C. (2023). Exploring CLIP for assessing the look and feel of images. *AAAI 2023*. (CLIP-IQA)

7. Talebi, H., & Milanfar, P. (2018). NIMA: Neural image assessment. *IEEE Transactions on Image Processing*, 27(8), 3998–4011.

8. Su, S., Yan, Q., Zhu, Y., Zhang, C., Ge, X., Sun, J., & Zhang, Y. (2020). Blindly assess image quality in the wild guided by a self-adaptive hyper network. *CVPR 2020*. (HyperIQA)

9. Sheikh, H. R., Sabir, M. F., & Bovik, A. C. (2006). A statistical evaluation of recent full reference image quality assessment algorithms. *IEEE Transactions on Image Processing*, 15(11), 3440–3451. (LIVE database)

10. Ponomarenko, N., et al. (2015). Image database TID2013: Peculiarities, results and perspectives. *Signal Processing: Image Communication*, 30, 57–77.

11. Lin, H., et al. (2019). KADID-10k: A large-scale artificially distorted IQA database. *QoMEX 2019*.

12. Ke, J., Wang, Q., Wang, Y., Milanfar, P., & Yang, F. (2021). MUSIQ: Multi-scale image quality transformer. *ICCV 2021*.

13. Ding, K., Ma, K., Wang, S., & Simoncelli, E. P. (2022). Image quality assessment: Unifying structure and texture similarity. *IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI)*, 44(5), 2567–2581. (DISTS)

14. Fang, Y., Zhu, H., Zeng, Y., Ma, K., & Wang, Z. (2020). Perceptual quality assessment of smartphone photography. *CVPR 2020*. (SPAQ dataset)

15. Oquab, M., et al. (2024). DINOv2: Learning robust visual features without supervision. *Transactions on Machine Learning Research (TMLR)*. (DINOv2)

16. Wu, H., Zhang, Z., Zhang, E., et al. (2024). Q-Bench: A benchmark for general-purpose foundation models on low-level vision. *ICLR 2024 (Spotlight)*. arXiv:2309.14181

17. Wang, H., et al. (2024). Q-Align: Teaching LMMs for visual scoring via discrete text-defined levels. *ICLR 2024*. arXiv:2312.17090
