# Part 5, Chapter 02: AIGC for Image Restoration and Enhancement

> **Frontier content**: Based on 2025-2026 CVPR/ICCV/NeurIPS advances. Engineering deployment cases are actively expanding. Contributions welcome via [Issue](https://github.com/AIISP/isp_handbook/issues).

> **Pipeline position:** Post-processing backend, SR, deblurring, low-light enhancement
> **Prerequisites:** Ch DL Overview, Ch Noise Reduction, Ch Super-Resolution
> **Reader path:** DL Researcher, Advanced ISP Engineer

---

## §1 原理 (Theory)

### From Discriminative to Generative Models in ISP

Classical deep learning for ISP is discriminative: given a degraded image $y$, a network $f_\theta$ learns to predict the clean image $\hat{x} = f_\theta(y)$ by minimizing a reconstruction loss (L1, L2, SSIM) on paired training data. The network learns a direct mapping from degraded to clean, which is fast at inference but tends to produce over-smooth results — the average over plausible clean images.

Generative AI models for content creation (AIGC — AI-Generated Content) flip this paradigm. Instead of mapping toward a single prediction, they model the full distribution $p(x)$ of clean, high-quality images. Sampling from this distribution conditioned on a degraded observation $y$ produces outputs that are perceptually sharp and natural, at the cost of not necessarily reconstructing the exact original signal.

For ISP, this trade-off is profound: *restoration* (recovering the original signal) and *generation* (creating new but plausible signal) are fundamentally different goals, and AIGC methods blur the boundary between them. Understanding when each is appropriate is essential.

### Diffusion Models: DDPM

Denoising Diffusion Probabilistic Models (Ho et al., 2020) define a two-process model:

**Forward process** (add noise gradually):
$$x_t = \sqrt{\bar{\alpha}_t}\, x_0 + \sqrt{1-\bar{\alpha}_t}\, \varepsilon, \quad \varepsilon \sim \mathcal{N}(0, I)$$

where $\bar{\alpha}_t = \prod_{s=1}^{t}(1 - \beta_s)$ and $\{\beta_t\}_{t=1}^{T}$ is a noise schedule. At $t = T$, $\bar{\alpha}_T \approx 0$ and $x_T \approx \mathcal{N}(0, I)$: the image has been destroyed into pure Gaussian noise.

**Reverse process** (learned denoising):
$$x_{t-1} = \mu_\theta(x_t, t) + \sigma_t z, \quad z \sim \mathcal{N}(0, I)$$

where the neural network $\mu_\theta$ (typically a U-Net) learns to predict the clean image (or equivalently, the noise $\varepsilon$) from a noisy input at step $t$. The model is trained by minimizing:
$$\mathcal{L}_\text{simple} = \mathbb{E}_{t, x_0, \varepsilon}\left[\|\varepsilon - \varepsilon_\theta(x_t, t)\|^2\right]$$

At inference, the reverse process starts from $x_T \sim \mathcal{N}(0, I)$ and iterates T denoising steps to generate a clean sample. With $T = 1000$, the original DDPM generates one image per 1000 forward passes, which is computationally expensive.

### Noise Schedules

The choice of noise schedule $\{\beta_t\}$ controls how quickly information is destroyed:

- **Linear schedule** (Ho et al., 2020): $\beta_t$ increases linearly from $\beta_1 = 10^{-4}$ to $\beta_T = 0.02$. This schedule tends to destroy most signal early and wastes capacity at the tail.
- **Cosine schedule** (Nichol & Dhariwal, 2021): $\bar{\alpha}_t = \cos^2\!\left(\frac{t/T + s}{1+s} \cdot \frac{\pi}{2}\right)$. This destroys signal more uniformly across time steps, improving image quality and training stability.

### Score Matching and Score Functions

An equivalent formulation (Song & Ermon, 2020) views diffusion as learning the **score function** $s_\theta(x, t) \approx \nabla_x \log p_t(x)$ — the gradient of the log probability density with respect to the image. The score points toward regions of higher probability (better images). By following the score (Langevin dynamics), one can sample from $p(x)$.

The score interpretation is useful for **conditional generation**: given observation $y$, we want to sample from $p(x|y) \propto p(y|x) p(x)$. The score decomposes as:
$$\nabla_x \log p(x|y) = \nabla_x \log p(y|x) + \nabla_x \log p(x)$$

This means the unconditional diffusion model provides the image prior term $\nabla_x \log p(x)$, and the degradation model provides the data-fidelity term $\nabla_x \log p(y|x)$. This clean separation enables **training-free** conditional generation for any degradation operator — highly relevant for ISP where degradation types change per use case.

### DDIM: Faster Sampling

Denoising Diffusion Implicit Models (Song et al., 2020) reformulate DDPM as a non-Markovian process, allowing deterministic sampling with far fewer steps. The DDIM update rule:
$$x_{t-1} = \sqrt{\bar{\alpha}_{t-1}}\underbrace{\left(\frac{x_t - \sqrt{1-\bar{\alpha}_t}\,\varepsilon_\theta}{\sqrt{\bar{\alpha}_t}}\right)}_{\hat{x}_0 \text{ prediction}} + \sqrt{1-\bar{\alpha}_{t-1}}\,\varepsilon_\theta$$

With DDIM, 20–50 steps produce comparable quality to DDPM's 1000 steps, reducing inference time by 20–50×. This is critical for real-time or near-real-time ISP applications.

### ControlNet: Conditioned Diffusion for ISP

ControlNet (Zhang et al., 2023) extends a pretrained diffusion model with a trainable copy of the U-Net encoder that accepts conditioning signals (depth maps, edge maps, segmentation masks). The conditioning pathway is connected to the frozen main U-Net via zero-convolution layers, preserving the pretrained image prior while adding spatial control.

For ISP, ControlNet conditioning inputs include:
- **ISP intermediate outputs**: use the output of a fast, low-quality ISP pass as the ControlNet input, and let diffusion generate a high-quality version guided by the structural cues.
- **Depth maps**: for portrait bokeh, condition diffusion on the depth map for consistent subject-aware rendering.
- **Edge maps**: for super-resolution, condition on Canny edges from the LR image to guide texture generation.

### StableSR and DiffBIR

**StableSR** (Wang et al., IJCV 2024) applies latent diffusion (compressing images to a latent space before diffusion) to blind image super-resolution. The low-resolution input is encoded into the latent space, and diffusion restores high-frequency details. A time-aware encoder conditions the diffusion process on the degraded image at each timestep, maintaining structural fidelity while generating realistic textures.

**DiffBIR** (Lin et al., ECCV 2024) two-stage pipeline: (1) a regression-based restoration network removes degradations (denoising, deblurring, JPEG artifact removal) to produce a clean but smooth intermediate; (2) a latent diffusion model generates realistic textures and fine details conditioned on the intermediate. This separation of *fidelity* (stage 1) from *perceptual quality* (stage 2) is an important design principle for ISP.

### The Hallucination vs. Restoration Distinction

This is the central tension in AIGC for ISP:

| Property | Restoration | AIGC Generation |
|---|---|---|
| Goal | Recover original signal $x_0$ | Sample from $p(x\|y)$ |
| PSNR/SSIM | High (close to reference) | Lower (samples ≠ reference) |
| Perceptual quality | May be over-smooth | Typically sharp and natural |
| Faithfulness | High | Can "hallucinate" detail |
| Use case | Forensics, medical, measurement | Photography, social media |

For ISP in smartphones, the perception-distortion trade-off (Blau & Michaeli, 2018) shows that no algorithm can simultaneously maximize both PSNR and perceptual quality — they are fundamentally opposed as distortion approaches zero. Diffusion models operate at the high-perceptual-quality end of this trade-off. The ISP engineer must decide: for the target use case, is a pixel-accurate reconstruction or a perceptually pleasant image more important?

**Hallucination risk in ISP**: diffusion models trained on natural image priors may synthesize texture that was not present in the original scene. In low-light photography, a diffusion SR model may hallucinate facial pores that do not correspond to reality. In surveillance or medical imaging applications, this is unacceptable. Production ISP pipelines should implement hallucination detection (e.g., compare SSIM between restored and reference on a validation set) and fall back to deterministic restoration when fidelity is critical.

### Applications in ISP

- **Low-light enhancement**: diffusion models sample from the distribution of well-lit images conditioned on a dark input, recovering color and detail that signal-processing methods cannot.
- **Deblurring**: score-based priors handle complex natural blur kernels that blind deconvolution methods struggle with.
- **Super-resolution**: 4× and 8× SR with perceptually realistic textures; StableSR, DiffBIR achieve LPIPS scores far below regression-based SR.
- **RAW-to-RGB ISP as diffusion**: treat the full ISP pipeline as a conditional generation problem. A diffusion model trained on (RAW, reference RGB) pairs learns an ISP backend that integrates noise model, demosaicing, tone mapping, and aesthetic enhancement into a single learned process.
- **Style transfer**: condition diffusion on a style reference image to harmonize aesthetic properties across a burst or video.

---

## §2 标定 (Calibration)

**Guidance scale calibration**: conditional diffusion uses a **guidance scale** $\gamma$ (classifier-free guidance, Ho & Salimans, 2022):
$$\tilde{\varepsilon}_\theta(x_t, c) = (1+\gamma)\,\varepsilon_\theta(x_t, c) - \gamma\,\varepsilon_\theta(x_t, \emptyset)$$

Higher $\gamma$ pulls samples toward the conditioning signal at the cost of reduced diversity and potential artifacts. For ISP, $\gamma$ must be calibrated on held-out validation images: a sweep from 1 to 15 with LPIPS and PSNR evaluation identifies the operating point that balances fidelity with perceptual quality for the target use case.

**Domain-specific fine-tuning**: pretrained diffusion models are trained on web images. Camera-specific characteristics (sensor noise pattern, color response, lens aberrations) require fine-tuning on paired data from the target sensor. DreamBooth or LoRA-based fine-tuning on 100–1000 camera-captured image pairs is sufficient to align the model's prior with the camera's output domain.

---

## §3 调参 (Parameter Tuning)

**Guidance scale $\gamma$**: the primary quality-fidelity knob.
- $\gamma = 1$: minimal guidance; samples from unconditional prior; low fidelity
- $\gamma = 7.5$ (typical): balanced perceptual quality and adherence to conditioning
- $\gamma = 15$+: over-guided; may produce saturated colors and unrealistic textures

**Number of denoising steps**: DDPM requires $T=1000$ steps for full quality; DDIM achieves comparable quality in 20–50 steps (20–50× speedup). Further acceleration with flow matching or consistency models can reduce to 4–8 steps. For mobile ISP, 8–16 steps is the practical target.

**Latent vs. pixel space**: pixel-space diffusion (DDPM) is computationally prohibitive for full-resolution ISP. Latent diffusion (Rombach et al., 2022) compresses images by 4–8× before diffusion, reducing compute proportionally. The VAE encoder/decoder adds a small fidelity cost but enables full-HD inference on consumer GPU hardware.

---

## §4 Artifacts

**Hallucination**: the most significant risk. Diffusion models may synthesize fine texture (hair, skin pores, text characters, foliage) that is statistically plausible but physically incorrect. Detection strategy: compare the restored image against the input via SSIM at different spatial scales; large discrepancies in low-frequency structure indicate hallucination.

**Mode collapse in fine-tuned models**: fine-tuning on too-small datasets (fewer than 500 images) with high learning rates causes the model to collapse — it generates similar images regardless of input. Early stopping and validation perplexity monitoring are essential.

**Color shift from diffusion prior**: diffusion models may shift the color balance toward the statistics of their training data (saturated, high-contrast web images). For ISP applications requiring color accuracy (product photography, medical imaging), a post-processing color correction step (matching the output histogram to the input's global chrominance) is necessary.

**Temporal inconsistency in video**: diffusion models generate each frame independently unless explicitly conditioned on adjacent frames. Direct application to video ISP produces flickering. Video diffusion models (Ho et al., 2022) or temporal consistency post-processing are required for video applications.

---

## §5 评测 (Evaluation)

**Generative quality metrics**:
- **FID (Fréchet Inception Distance)**: measures distribution distance between generated and real image sets. Lower is better; typical high-quality diffusion models achieve FID < 5 on standard benchmarks.
- **IS (Inception Score)**: measures the entropy of class predictions. Less reliable than FID; included for completeness.
- **LPIPS (Learned Perceptual Image Patch Similarity)**: measures perceptual distance to a reference. Unlike PSNR/SSIM, LPIPS correlates well with human perception. DiffBIR achieves LPIPS of 0.12–0.18 on blind SR benchmarks, compared to 0.35–0.45 for bicubic upsampling.

**Restoration fidelity metrics**:
- **PSNR**: pixel-level accuracy. Diffusion models typically achieve 1–4 dB lower PSNR than regression-based networks on paired benchmarks — this is the perception-distortion trade-off in action.
- **SSIM**: structural similarity. More tolerant of small positional shifts than PSNR; a better proxy for structural fidelity.

**Human preference studies**: for perceptual ISP tasks, human A/B preference tests are the gold standard. Consistent with the perception-distortion trade-off, users prefer diffusion-based results over regression-based results in blind evaluations despite lower PSNR, except for tasks requiring signal fidelity (e.g., document digitization, measurement imaging).

---

## §6 代码 (Code)

See the accompanying notebook `ch_aigc_code.ipynb` for:
- DDPM forward noise process simulation (T=1000 steps, visualized at t=0, 250, 500, 750, 1000)
- Linear vs. cosine noise schedule comparison
- Conceptual denoising effect and signal recovery
- ISP application discussion with ControlNet conditioning diagram

---

## §7 Diffusion Model Acceleration and Real-Time ISP

### 7.1 Diffusion Inference Acceleration Techniques

The original DDPM requires 1000 reverse denoising steps to generate high-quality images, each requiring a full U-Net forward pass — far too slow for real-time operation on mobile NPUs. Three classes of acceleration techniques form the key path from research to production ISP deployment:

**DDIM (Deterministic Sampling):** Song et al. (2020) replaced DDPM's 1000-step stochastic Markov diffusion with 50-step deterministic non-Markovian sampling, achieving 20× speedup with < 0.5 FID quality loss. Deterministic sampling also provides a bonus: given the same initial noise, output is fully reproducible — essential for ISP parameter tuning and A/B testing.

**Consistency Models:** Song et al. (ICML 2023) train a consistency function that maps any noisy image on a diffusion trajectory directly to the clean image (skip-step generation). Single-step or few-step (2–4 steps) generation achieves quality comparable to DDPM at 100× speedup, suitable for near-real-time mobile processing (e.g., post-capture photo enhancement).
- Reference: Song et al., "Consistency Models", ICML 2023, https://arxiv.org/abs/2303.01469

**Flow Matching:** Lipman et al. (ICLR 2023) replace SDEs (stochastic differential equations) with ODEs (ordinary differential equations), learning straighter probability flow trajectories between data and noise. Straighter trajectories require fewer integration steps: 10-step Flow Matching reaches the quality of 50-step DDPM, with more stable training (lower gradient variance).
- Reference: Lipman et al., "Flow Matching for Generative Modeling", ICLR 2023

**Mobile Inference Latency Comparison (4K ISP input cropped 512×512):**

| Method | Steps | Snapdragon 8 Gen 3 NPU Latency | Use Case |
|--------|-------|-------------------------------|----------|
| DDPM | 1000 | ~30s | Unusable on mobile |
| DDIM | 50 | ~1.5s | Post-capture processing (acceptable) |
| Consistency Model | 4 | ~120ms | Real-time capture mode |
| Flow Matching | 10 | ~300ms | Post-capture processing |

---

### 7.2 Hallucination Detection and Quality Assurance

Diffusion models introduce hallucination risks absent from discriminative methods. Production systems must implement active detection and safe fallback mechanisms.

**Types of Diffusion Hallucinations:**

1. **Geometric hallucination:** Generated non-existent fingers, architectural structures, or repeating textures (common at high guidance strength)
2. **Texture hallucination:** Over-sharpened pseudo-textures ("oil-painting effect") — skin pores and hair strands become unnaturally stylized patterns
3. **Color hallucination:** Color shifts away from the original RAW color distribution; diffusion models push colors toward the high-saturation statistics of training data (web images)

**Detection Metrics and Implementation:**

```python
# Perceptual consistency score (LPIPS distance from input reference)
perceptual_consistency = lpips(output, input_reference)
# Threshold: > 0.3 indicates excessive hallucination
if perceptual_consistency > 0.3:
    output = blend(output, classical_isp_output, alpha=0.5)
```

LPIPS > 0.3 typically corresponds to human-perceptible hallucination regions; adjust the threshold based on the specific application (portrait vs. landscape). For high-fidelity requirements (document scanning, product photography), tighten the threshold to 0.15.

**Safety Net Design (Fallback Mechanism):** Automatically falls back to traditional ISP when DL ISP fails:
- Monitor output BRISQUE score in real time; trigger fallback if it exceeds the normal range (sudden spike)
- Run traditional ISP and diffusion ISP in parallel within the ISP pipeline; blend outputs using quality-weighted soft fusion at the output layer
- For video streams, additionally monitor inter-frame flicker index (temporal variance); route anomalous frames directly to traditional ISP output

---

### 7.3 ControlNet for ISP Parameter Tuning

**Principle:** ControlNet uses RAW images (or ISP intermediate outputs) as spatial conditioning inputs to guide diffusion model generation toward a target image quality style, while preserving the structure and layout of the input. This makes "ISP as a controllable generative process" possible.

**ISP Style Transfer Pipeline:**

1. Collect (RAW, target_JPEG) paired data for the target style — e.g., "Leica style" (high contrast, warm skin tones, shadow grain) or "cinematic" (orange-teal grading, vignetting); 200–500 pairs per style suffice
2. Use RAW as ControlNet conditioning input, target_JPEG as the generation target; fine-tune ControlNet
3. At inference: input RAW + style prompt → generate sRGB output in the corresponding style

**Engineering Constraints and Roadmap:**

| Approach | Current Latency (2025 flagship) | 2026 Target | Use Case |
|----------|---------------------------------|-------------|----------|
| ControlNet + DDIM (50 steps) | ~3s | ~1s | Post-capture processing |
| ControlNet + Consistency (4 steps) | ~500ms | ~150ms | Capture mode |
| ControlNet + Flow Matching (10 steps) | ~800ms | ~250ms | Capture mode |

Current mobile latency of ~500ms (Consistency Model + ControlNet) is acceptable in capture mode on 2025 flagship hardware, but not for real-time preview (requires < 33ms). With improving NPU performance, real-time preview during capture is projected to be feasible by 2026.

**Multi-style switching:** Train multiple lightweight LoRA adapters for different styles and load them dynamically at inference, avoiding storing a separate full ControlNet model per style — significantly reducing storage (each style adds only ~10 MB).

---

### 7.4 Video Temporal Consistency

**Problem:** Frame-independent diffusion generation produces inter-frame inconsistencies (temporal flickering). Due to the stochastic nature of the diffusion process, adjacent frames exhibit subtle differences even in static regions; these accumulate into perceptible flickering in video playback.

**Solutions:**

1. **Neighbor-frame conditioning:** Feed the previous frame's diffusion output (or its intermediate features) as additional conditioning into the current frame's generation process. Implemented by adding a temporal attention module to the ControlNet conditioning pathway.

2. **Optical-flow consistency loss:** During training, compute optical flow between adjacent frames, warp the previous frame to the current frame, and compute a consistency loss:
   $$\mathcal{L}_{\text{temp}} = \|\hat{x}_t^i - \text{warp}(\hat{x}_t^{i-1}, \mathbf{v}_{i-1 \to i})\|_1$$
   where $\mathbf{v}_{i-1 \to i}$ is the optical flow field. This penalizes inter-frame inconsistency while optical flow alignment ensures constraints are applied only to corresponding regions.

3. **Frame interpolation post-processing:** Detect flickering frames (inter-frame difference exceeds threshold) and replace or blend with interpolated frames (DAIN/RIFE). This is the lightest approach — no diffusion model modification needed, deployable as a post-processing plugin to existing video ISP pipelines.

**Evaluation metric:** Use **tOF (temporal Optical Flow warping error)** to quantify flickering: MSE between the optical-flow-warped previous frame and the current frame. Typical values: naive frame-by-frame diffusion tOF ≈ 0.015; with neighbor-frame conditioning tOF ≈ 0.004, approaching traditional video ISP's 0.002–0.003.

---

## §8 Diffusion Foundation Models in Competition: 2023–2025 NTIRE/AIM Analysis

This section combines top competition results to analyze how generative AI methods have landed in image restoration, revealing the patterns of technological evolution.

### 8.1 Competition Landscape: Diffusion Model Entry

Before 2023, NTIRE/AIM competition winners were almost entirely **deterministic** CNN/Transformer methods (NAFNet, Restormer, HAT), optimizing for PSNR/SSIM.

The 2023–2024 turning point:

| Phase | Period | Landmark Method | Change |
|-------|--------|----------------|--------|
| Diffusion entry | 2023 | StableSR, DiffBIR | First diffusion submissions in blind SR/restoration tracks; excellent perceptual scores, PSNR not leading |
| Diffusion dominates perceptual tracks | 2024 | SeeSR, PASD, OSEDiff | NTIRE perceptual quality tracks (LPIPS/NIQE evaluation) began to be dominated by diffusion methods |
| Edge diffusion exploration | 2025 | OSEDiff, SinSR | Competitions see efficiency-constrained one-step/few-step diffusion solutions |

### 8.2 Flagship Competition Methods: Deep Analysis

#### DiffBIR (NTIRE 2023–2024 Blind Restoration)

DiffBIR was the first method to bring ControlNet into blind image restoration and achieve competition results:

```
Input degraded image y
    │
    ├─ [Stage 1: Deterministic prior recovery]
    │   Lightweight Restormer/NAFNet network
    │   Output: Low-noise but blurry initial estimate x̂
    │
    └─ [Stage 2: ControlNet diffusion refinement]
        ControlNet condition: x̂ (from Stage 1)
        Stable Diffusion iterates T steps
        Output: Perceptually realistic, detail-rich x_SR
```

Competition key metrics:
- Urban100 blind SR (×4): LPIPS 0.089 (vs. HAT's 0.134)
- PSNR ~0.8 dB below HAT (fidelity cost)
- Inference time: ~2s/image (A100), 20–50× slower than deterministic methods

Code: https://github.com/XPixelGroup/DiffBIR

#### SeeSR (CVPR 2024 — Best Perceptual Quality)

SeeSR resolves diffusion restoration's biggest pain point — hallucination (generating semantically incorrect details) — via **semantic-aware guidance**:

1. **Degradation-robust tag extraction**: Uses RAM (Recognize Anything Model) to extract coarse semantic tags from degraded images
2. **Fine-grained text embeddings**: Tags → CLIP text encoder → diffusion conditioning signal
3. **Degradation-Aware Estimator (DAE)**: Dedicated network extracting structural priors from low-quality input

Results on RealSR benchmark:
- LPIPS: 0.261 (SeeSR) vs. 0.312 (Real-ESRGAN) vs. 0.289 (StableSR)
- MUSIQ perceptual score: 65.4 (SeeSR) vs. 57.2 (Real-ESRGAN)

Code: https://github.com/cswry/SeeSR

#### SUPIR (2024 — Universal Blind Restoration Milestone)

SUPIR (Scaling Up to Excellence) elevates image restoration to foundation model scale:

```python
# SUPIR workflow
text_description = llm.caption(degraded_img)
# e.g.: "A blurry outdoor photo with people walking"

restored = SUPIR_model(
    degraded_img,
    text_prompt=text_description,      # LLM-generated description
    positive_prompt="high quality, detailed, sharp",
    negative_prompt="blurry, noisy, artifact"
)
```

- **Backbone**: SDXL (2.6B parameters)
- **Key innovation**: LLaVA auto-generates descriptive prompts, eliminating manual prompt engineering
- **Competition value**: Achieved highest perceptual metrics on multiple NTIRE 2024 blind restoration tracks

Code: https://github.com/Fanghua-Yu/SUPIR

#### OSEDiff (2024 — One-Step Diffusion Breakthrough)

**Consistency Distillation** compresses diffusion from 50+ steps to 1 step:

$$\mathcal{L}_{CD} = \mathbb{E}[\lambda(t) \| f_\theta(x_t, t) - f_{\theta^-}(x_{t'}, t') \|^2]$$

where f_θ is the student network, f_{θ⁻} is the EMA teacher, and t' < t is a less-noisy timestep.

Results:
- Perceptual quality retention: 90%+ LPIPS/FID of multi-step methods
- Speed: 2s → 0.1s (A100)
- Strong contender for NTIRE 2025 Efficient tracks

Code: https://github.com/cswry/OSEDiff

### 8.3 AIM Competition: Extended Dimensions of Image Manipulation

**RAW Image SR track (AIM 2024):**
- Direct SR in RAW space, avoiding information loss from ISP pipeline
- Champion approach: ISP-aware joint network; trained in RAW domain, outputs sRGB; Bayer-domain data augmentation
- Directly relevant to this handbook's Part 2: RAW SR = optimal processing point before ISP, avoids irreversible information loss from sRGB quantization

**SAM-guided Shadow Removal:**
- Uses Segment Anything Model (SAM) as shadow segmentation pre-processor
- Demonstrates that **foundation models as auxiliary tools** (not replacements) has become mainstream competition strategy

### 8.4 Limitations of Diffusion Methods in Competition

Despite dominating perceptual tracks, diffusion methods exposed engineering pain points:

| Issue | Description | Solution Direction |
|-------|-------------|-------------------|
| **Inference speed** | 20–50 step diffusion = 10–100× deterministic latency | Distillation (DDIM, DPM-Solver, consistency distillation) |
| **Perception/fidelity trade-off** | LPIPS↑ means PSNR↓; generated details not necessarily "real" | Stronger conditioning; hybrid loss |
| **Hallucination** | Can generate non-existent text/faces/objects | Semantic guidance (SeeSR); content constraint loss |
| **Non-determinism** | Same input, different sample = different outputs | Fixed random seed; deterministic DDIM sampling |
| **GPU memory** | SD-XL needs 12GB+ VRAM | 4-bit quantization; streaming inference; edge distillation |
| **UG2+ instability** | Hallucinated details mislead downstream detectors | Task-aware loss; confidence filtering |

### 8.5 Post-2025 Competition Technology Trend Predictions

1. **Edge diffusion acceleration**: NPU-specific INT8/FP16 diffusion operators; Mamba replacing Transformer attention blocks to reduce memory bandwidth
2. **Multi-modal conditioned restoration**: Text + depth + semantics joint guidance; conversational restoration ("Remove the noise from this photo, keep the background blur")
3. **Video diffusion**: Temporally consistent diffusion (AnimateDiff-style) for video SR/enhancement
4. **RAW-domain foundation models**: Large models pre-trained directly in RAW linear domain, eliminating ISP-introduced information loss
5. **Task-driven metric competitions (UG2+ style expansion)**: Shifting perceptual metrics from LPIPS/FID to downstream visual task accuracy

---

## 参考资料 (References)

- Ho, J. et al. (2020). *Denoising Diffusion Probabilistic Models* (DDPM). arXiv:2006.11239
- Song, J. et al. (2020). *Denoising Diffusion Implicit Models* (DDIM). arXiv:2010.02502
- Song, Y. & Ermon, S. (2020). *Score-Based Generative Modeling through Stochastic Differential Equations*. arXiv:2011.13456
- Nichol, A. & Dhariwal, P. (2021). *Improved Denoising Diffusion Probabilistic Models*. arXiv:2102.09672
- Rombach, R. et al. (2022). *High-Resolution Image Synthesis with Latent Diffusion Models*. arXiv:2112.10752
- Zhang, L. et al. (2023). *Adding Conditional Control to Text-to-Image Diffusion Models* (ControlNet). arXiv:2302.05543
- Wang, X. et al. (2024). *Exploiting Diffusion Prior for Real-World Image Super-Resolution* (StableSR). *Int. J. Comput. Vis. (IJCV)*, 2024. arXiv:2305.07015
- Lin, X. et al. (2024). *DiffBIR: Towards Blind Image Restoration with Generative Diffusion Prior*. *ECCV 2024*. arXiv:2308.15070
- Blau, Y. & Michaeli, T. (2018). *The Perception-Distortion Tradeoff*. CVPR 2018.
- Ho, J. & Salimans, T. (2022). *Classifier-Free Diffusion Guidance*. arXiv:2207.12598

---

## §9 Generative Model Foundations: Comparison

### 9.1 Core Differences: VAE / GAN / Diffusion / Flow Matching

The four mainstream generative model families each make different trade-offs across training stability, sampling speed, image quality, and controllability. The following table provides an ISP engineering comparison:

| Dimension | VAE | GAN | Diffusion | Flow Matching |
|-----------|-----|-----|-----------|---------------|
| **Training objective** | Maximize ELBO (variational lower bound) | Adversarial game (discriminator vs. generator) | Noise prediction ($\ell_2$ loss) or score matching | ODE vector-field regression ($\ell_2$ loss) |
| **Training stability** | High; single optimization objective | Low; prone to mode collapse and oscillation | High; loss decreases monotonically, no adversarial component | High; lower gradient variance than Diffusion |
| **Sampling speed** | Very fast (single forward pass) | Very fast (single forward pass) | Slow (20–1000 iterative steps) | Moderate (10–20 ODE integration steps) |
| **Image quality (FID)** | Moderate; VAE bottleneck causes blurring | High (StyleGAN2 FID < 4) but artifact risk | Best (highest generation diversity) | Comparable to Diffusion, slightly faster |
| **Controllability** | Moderate (latent interpolation) | Moderate (StyleGAN mapping network) | High (CFG, ControlNet, text prompts) | High (conditional ODE with precise control) |
| **Representative models** | VQ-VAE-2, DALL-E 1 | StyleGAN3, BigGAN | DDPM, SDXL, SD3 | FLUX, Stable Flow |
| **ISP use cases** | VAE as encoder in latent diffusion | Noise synthesis (NoiseFlow), style transfer | Blind restoration, SR, night-scene enhancement | Next-gen edge generation (faster convergence) |

**Key engineering conclusion:** For ISP perceptual enhancement tasks (low-light enhancement, super-resolution), Diffusion and Flow Matching deliver the highest quality. GANs retain value in noise synthesis scenarios (see Vol. 5, Ch. 11) for their fast training. VAEs serve primarily as latent-space compression modules embedded in Stable Diffusion architectures, not as standalone generators.

### 9.2 Stable Diffusion Architecture Evolution

From SD v1.5 to FLUX, architectural changes reflect the continual expansion of generative model capabilities for ISP applications:

| Version | Release | Backbone | Parameters | Key Improvement | ISP Capability |
|---------|---------|----------|-----------|-----------------|----------------|
| **SD v1.5** | 2022.10 | U-Net (Conv-based) | 860M | Established latent diffusion framework | Basic SR, style transfer |
| **SDXL** | 2023.07 | Dual U-Net (Base + Refiner) | 2.6B | Larger model, higher resolution (1024²) | Portrait restoration, blind SR |
| **SD 3** | 2024.03 | DiT (Diffusion Transformer) | 2B–8B | MMDiT (multimodal Transformer), Flow Matching | Text-guided restoration, multimodal ISP |
| **FLUX.1** | 2024.08 | DiT + Flow Matching | 12B | Highest quality; stable training; excellent detail fidelity | Extreme perceptual enhancement |

The shift from U-Net to Transformer (DiT) is the core of this evolution: traditional U-Net receptive fields are limited by convolution kernel size, whereas Transformer global attention allows the model to perceive wider image context — particularly critical for ISP tasks requiring global illumination understanding (night scene, HDR).

### 9.3 DiT (Diffusion Transformer) Scalability Advantage

DiT (Peebles & Xie, ICCV 2023) replaces the U-Net backbone with Vision Transformer (ViT), delivering LLM-like scaling properties:

**Core design:**
- Partition images into $p \times p$ patches (e.g., $p=2$), mapped to a token sequence;
- Use standard Transformer blocks (self-attention + feed-forward) instead of U-Net encoder-decoder;
- Timestep $t$ and conditioning signals injected via adaptive layer norm (adaLN-Zero), eliminating explicit skip connections.

**Scalability advantage (ISP perspective):**

| Feature | U-Net | DiT |
|---------|-------|-----|
| Parameter scaling | Add channels/depth (nonlinear) | Add Transformer layers (linear scaling) |
| Compute efficiency (FLOPs/param) | Lower | Proportional to model size, predictable |
| Global receptive field | Only at lowest resolution layers | Global attention at all layers |
| Multimodal conditioning | Via cross-attention (indirect) | Token concatenation (direct, see SD3 MMDiT) |
| Transfer from pre-training | Difficult to reuse LLM weights | Can reuse ViT pre-training, lower training cost |

DiT-XL/2 (largest variant) achieves FID 2.27 on ImageNet 256² generation, outperforming all prior GAN methods, and continues to follow a clear scaling law: larger model → lower FID. This means ISP perceptual quality can be continuously improved by adding compute and parameters — a property GANs do not possess.

---

## §10 AIGC Applications in ISP

### 10.1 Low-Light Enhancement: Zero-DCE vs. DiffLight

**Zero-DCE (Zero-Reference Deep Curve Estimation; Li et al., CVPR 2020)** is the representative discriminative low-light enhancement method. Its core idea models the enhancement process as pixel-level curve adjustment (Light-Enhancement Curve, LE-Curve), requiring no paired data. Multiple non-reference losses (brightness perceptual, color constancy, smoothness regularization) optimize curve parameters end-to-end:

$$\hat{x} = x + A(x) \cdot x \cdot (1 - x)$$

where $A(x)$ is the per-pixel curve coefficient predicted by a lightweight network. The entire model has only 79K parameters; inference takes ~2ms on an iPhone 12 — the canonical choice for real-time mobile low-light enhancement.

**DiffLight (diffusion-based low-light enhancement, representative 2023–2024 works)** conditions on a dark image and samples from the distribution of well-exposed images via reverse diffusion:

$$p(x_0 | y) \propto p(y | x_0) \cdot p(x_0)$$

The diffusion prior $p(x_0)$ is learned from a large collection of normally-exposed images; the degradation likelihood $p(y | x_0)$ models the low-light imaging chain (dark tone + Poisson noise).

**Perceptual quality comparison (LOL/LSRW dataset):**

| Method | PSNR (dB) | SSIM | LPIPS | NIQE | Mobile Inference |
|--------|-----------|------|-------|------|-----------------|
| Zero-DCE | 14.86 | 0.559 | 0.335 | 7.24 | ~2ms |
| RetinexNet | 16.77 | 0.560 | 0.474 | 8.01 | ~5ms |
| SNR-Aware | 21.48 | 0.849 | 0.158 | 6.12 | ~50ms |
| DiffLight (representative) | 18.32 | 0.715 | 0.102 | 4.87 | ~800ms (NPU-accelerated) |

Key observation: DiffLight's PSNR is ~3 dB below SNR-Aware, but both LPIPS and NIQE (no-reference perceptual quality) are superior — a textbook perception-distortion trade-off. In user A/B testing, DiffLight preference is ~15–20% higher in "social sharing" scenarios and ~30% lower in "document archiving" scenarios. This directly guides mobile ISP strategy: enable diffusion enhancement in Social mode, disable in Professional/Original mode.

### 10.2 Super-Resolution: Real-ESRGAN vs. Stable Diffusion SR

**Real-ESRGAN (Wang et al., ICCV 2021 Workshop)** is the current industrial baseline for mobile ISP super-resolution. Its core contribution is the **high-order degradation pipeline** (see Vol. 5, Ch. 11): randomly compositing blur, downsampling, noise, and JPEG compression operators to simulate complex real-world degradations, making the model robust across degradation types. RRDB backbone, ×4 SR, LPIPS = 0.198 on RealSR benchmark.

**SD-based SR (StableSR, DiffBIR, etc.)** leverages Stable Diffusion's strong image prior to achieve LPIPS 0.089–0.12 on the same ×4 SR task — significantly superior perceptual quality over Real-ESRGAN.

**Engineering trade-off comparison:**

| Dimension | Real-ESRGAN | SD-based SR |
|-----------|-------------|-------------|
| PSNR (RealSR ×4) | ~26.4 dB | ~24.8 dB (−1.6 dB) |
| LPIPS (RealSR ×4) | 0.198 | 0.089–0.12 (−50%) |
| Inference latency (4K → 4K) | < 1s (NPU) | 5–30s (50-step DDIM) |
| Hallucination risk | Low | Medium–High (depends on CFG strength) |
| Memory footprint | < 200 MB | 2–6 GB (full SD model) |
| Use case | Real-time / near-real-time | Post-capture, night scene, historical photo restoration |

Conclusion: In 2026 production practice, **Real-ESRGAN serves as the real-time ISP-embedded SR; SD-based SR serves as user-triggered "AI Enhancement" post-capture processing** — the two operate in different tiers rather than as alternatives.

### 10.3 ISP Style Transfer: ControlNet-Based Photography Style

ControlNet provides a structured framework for ISP style transfer: use RAW (or low-quality ISP output) as structural conditioning, use a style description as text conditioning, and generate sRGB output with a target photographic aesthetic.

**Popular photography style LoRA library (community ecosystem formed 2024–2025):**

| Style Type | Representative Characteristics | ControlNet Conditioning | Text Prompt Example |
|-----------|-------------------------------|------------------------|-------------------|
| Leica M film-style | High contrast, warm skin, shadow grain | RAW + depth map | "Leica film portrait, warm skin, grain" |
| Japanese soft-style | Low contrast, green-teal cast, soft highlights | RAW + edge map | "Japanese film, soft highlight, faded" |
| Cinematic teal-orange | Warm highlights, cool shadows (complementary tones) | RAW + segmentation mask | "cinematic teal orange, filmic LUT" |
| B&W documentary | Hard contrast, heavy grain, extreme highlight/shadow clipping | RAW | "Tri-X 400, high contrast, black and white" |

**Engineering implementation notes:**
1. Collect 200–500 (RAW, target JPEG) pairs per style;
2. Freeze Stable Diffusion backbone; train only the ControlNet encoder and corresponding LoRA adapter (~10–30M parameters);
3. Dynamically load LoRA at inference (< 50ms switching time), without storing separate full models per style;
4. In video scenarios, combine with the temporal consistency constraints from §7.4 to suppress per-frame style variation.

### 10.4 Portrait Enhancement: Generative Face Restoration

**GFPGAN (Wang et al., CVPR 2021)** is the foundational work in generative face restoration. The key design embeds a pre-trained GAN's (StyleGAN2) hierarchical face prior into a U-Net restoration network: the U-Net extracts features from the degraded image, which are fused with StyleGAN's face knowledge via SFT (Spatial Feature Transform) layers while preserving input structure (eye and mouth positions). On CelebA-HQ test set for ×8-degraded faces, GFPGAN reduces FID from Real-ESRGAN's 49.9 to 23.1, with notably improved eye and tooth detail restoration.

**CodeFormer (Zhou et al., NeurIPS 2022)** improves on GFPGAN by introducing a VQGAN discrete codebook as a strong face prior: the degraded face is first quantized to the nearest codebook entry, then decoded to high-quality output by a Transformer decoder. The key engineering innovation is the **controllable quality-fidelity trade-off parameter $w \in [0, 1]$**:

$$\hat{x} = w \cdot x_{\text{code}} + (1-w) \cdot x_{\text{encoder}}$$

$w=0$ relies entirely on the encoder (high fidelity, lower quality); $w=1$ relies entirely on the codebook (high quality, may deviate from original identity). Mobile portrait enhancement modes typically set $w \approx 0.7$, balancing perceptual quality with identity preservation.

**CodeFormer mobile deployment path:**
- Full-precision model (PyTorch FP32): ~700 MB;
- After INT8 quantization: ~180 MB;
- Snapdragon 8 Gen 3 NPU inference: ~300ms (1080p portrait crop region 512×512);
- Combined with face detection/segmentation, run only on detected face regions; full-image merge latency < 500ms.

---

## §11 Quality–Fidelity Trade-off in Generative ISP

### 11.1 Perception–Distortion Pareto Frontier

Blau & Michaeli (CVPR 2018) **perception-distortion theorem** provides an information-theoretic impossibility proof: for any restoration algorithm $\hat{x} = f(y)$, let $d = \mathbb{E}[\|x - \hat{x}\|^2]$ (distortion) and $p = d_{\text{perc}}(p_x, p_{\hat{x}})$ (perceptual quality, i.e., divergence between generated and real distributions):

$$d + p \geq d^* \quad \text{(a lower bound exists; both cannot be simultaneously minimized)}$$

This means $(d, p)$ pairs for different algorithms form a Pareto curve:
- **Bottom-left** (low $d$, low $p$): Unachievable region (physical lower bound);
- **Right end** (high $d$, low $p$): DDPM/DDIM — best perceptual quality, high distortion;
- **Middle** (moderate $d$, moderate $p$): GAN methods (ESRGAN);
- **Left end** (low $d$, high $p$): L2 regression — lowest distortion (highest PSNR), poor perceptual quality (over-smoothing).

**ISP engineer decision framework:**

| Application Scenario | Target on Pareto Curve | Recommended Method |
|---------------------|----------------------|-------------------|
| Social sharing, portrait, landscape | Perceptual quality priority (right end) | Diffusion (CFG = 7–10) |
| Product photography, e-commerce | Balanced midpoint | GAN / Diffusion (CFG = 3–5) |
| Documents, QR codes, text | Fidelity priority (left end) | Traditional ISP + lightweight CNN |
| Medical imaging, scientific imaging | Forced fidelity (generation prohibited) | Discriminative methods only, no diffusion |

### 11.2 Hallucination Types and Risks in ISP

Hallucination in generative ISP refers to the model synthesizing information absent in the original scene. Like hallucination in text LLMs, these "fabricated" details are statistically plausible and therefore difficult to detect with simple quality metrics.

**Four main hallucination types:**

1. **Texture hallucination (most common):** Diffusion models generate statistically correct but positionally wrong details in skin pores, brick textures, grass, etc. Typical symptom: zooming in reveals skin texture that is "perfect but unreal," with pore positions inconsistent with the subject's age.

2. **Geometric hallucination:** At high magnification, finger count, architectural corners, and text strokes may be incorrectly generated. This is a known weakness of Stable Diffusion series, related to tokenization and attention's global nature.

3. **Color hallucination:** Training data biased toward high-saturation images causes outputs skewed toward "Instagram style" — even if the original scene is muted, diffusion models "imagine" more vivid colors. Particularly pronounced on neutral tones (white, gray).

4. **Identity hallucination:** In face restoration with heavy degradation (e.g., ×8 SR), the restored face may differ in detail from the original (eye shape, facial contour subtly changed), potentially appearing as a different person in extreme cases. CodeFormer mitigates this by lowering $w$.

### 11.3 Usage Restrictions in Production ISP Products

Current (2025–2026) production mobile ISP restrictions on generative enhancement:

**Explicitly prohibited scenarios:**
- **Medical/scientific imaging apps** (e.g., dermatoscope apps, scientific microscope interfaces): Generated false details can affect diagnosis — strictly prohibited. Some manufacturers restrict professional camera mode APIs from using AI enhancement.
- **Forensic/insurance evidence capture:** Some jurisdictions require an "original evidence chain" for photographs; any AI-generated enhancement is disallowed and requires explicit metadata annotation (see §12.2).
- **Official product photography (color accuracy required):** E-commerce product images require high color accuracy; generative enhancement may alter colors (especially saturation), causing misleading product descriptions.

**Conditionally permitted scenarios (user disclosure required):**
- Social-mode low-light enhancement: Must note "AI Enhanced" in photo metadata or EXIF;
- Portrait beautification (skin smoothing, teeth whitening): Must provide an off switch, and processing intensity must not exceed a threshold (manufacturer self-regulation, no unified standard).

### 11.4 User Preference Research: "AI Feel" vs. "Natural Feel"

Multiple user studies (Adobe, Google, Xiaomi, and others) reveal patterns in user acceptance of generative ISP:

**Key findings (aggregate 2023–2025 survey data):**
- **Overall preference distribution:** In social sharing scenarios, ~62% of users prefer AI-enhanced images (vs. traditional ISP output); ~38% prefer the natural look. In "faithful documentation" scenarios (family photos, ID photos), the preference ratio reverses to 34% vs. 66%.
- **Age differences:** Users aged 18–25 show significantly higher acceptance of AI enhancement than those 45+ (~25 percentage points difference in preference rate).
- **Content dependency:** Landscape images show the highest AI enhancement acceptance (preference rate 71%); face images the lowest (51%); text/document images lowest of all (22%).
- **"AI feel" negative perception threshold:** When diffusion CFG strength $\gamma > 12$, ~40% of users perceive "over-AI-ification" (oil-painting effect, over-sharpening) and give negative ratings. At CFG $\leq 7.5$, negative perception drops below 10%.

These data directly inform commercial ISP default parameter settings: the vast majority of manufacturers target the interval where users perceive "improvement" but cannot perceive "AI-ification."

---

## §12 AIGC Content Safety and Copyright

### 12.1 Watermarking Technology for AI-Generated Images

As AIGC capabilities permeate consumer smartphone cameras, identifying and tracing AI-generated/enhanced images has become an urgent engineering challenge. The mainstream technical approach is **invisible watermarking**.

**Stable Signature (Fernandez et al., ICCV 2023):**

Meta's Stable Signature is one of the most mature diffusion model watermarking schemes. The core idea embeds watermark information in the diffusion model's VAE decoder so that every generated image is visually invisible but reliably detectable by a digital watermark detector:

1. After diffusion inference ends, the output $x_0$ passes through a modified VAE decoder (with watermark embedded during decoding);
2. The watermark is embedded in the pixel domain using spread spectrum, distributed across the full-image frequency components, robust to JPEG compression (QF ≥ 60), cropping (> 50% area retained), and mild noise;
3. Detection: extract steganographic features from the full image, compare against stored watermark key, output confidence > 0.99 (FAR < 0.1%);
4. Each manufacturer/user account can register an independent watermark key, enabling AI-generated content traceability.

**C2PA (Coalition for Content Provenance and Authenticity) Standard:**

The C2PA standard (Content Credentials), promoted jointly by Adobe, Apple, Microsoft, Google, Sony, and others, records content provenance at the image metadata level, including fields for "whether AI-generated or AI-enhanced," "which AI model was used," etc. Complementary to invisible watermarking:
- C2PA metadata is easy to remove (delete EXIF), but reliable in normal circulation paths;
- Invisible watermarks are difficult to remove (require substantial image modification), suitable for forensic scenarios.

### 12.2 Deepfake Detection in Mobile Cameras

Deepfake detection is a hot topic in AI safety, intersecting with mobile ISP in these scenarios:

**Passive detection (analyzing the image itself):**
- Current best-performing Deepfake detection models (e.g., SBI, UniFAD) analyze frequency-domain features of GAN/diffusion-generated images, achieving AUC > 0.95 on FaceForensics++;
- Deploying lightweight detection models (< 10M parameters) on Snapdragon/MediaTek NPUs: < 5ms per-frame detection latency, integrable into real-time video stream analysis.

**Active annotation (platform side):**

| Manufacturer | Technical Implementation | Annotation Location |
|-------------|-------------------------|-------------------|
| **Apple (iOS 18+)** | C2PA Content Credentials embedded in Camera app; AI generation/editing operations recorded in image metadata | "AI Enhanced" badge in Photos info panel |
| **Samsung (Galaxy AI)** | AI-edited photos receive a "Generative Edit" watermark (visible + EXIF record) | Asterisk annotation in Gallery |
| **Google (Pixel 9+)** | Magic Eraser / Best Take operations annotated "AI Edited" in Google Photos | C2PA metadata attached when sharing |

These annotation measures are currently primarily effective "within the manufacturer's own platform" — after export to third-party platforms, metadata retention depends on platform compliance.

### 12.3 Copyright Attribution in ISP Products

Copyright ownership of AI-generated content remains legally contested globally (as of 2026), but several engineering practice standards have emerged on the ISP product side:

**Current legal tendencies (major jurisdictions, 2025 status):**
- **United States:** The U.S. Copyright Office has determined that purely AI-generated content (without human creative choice) is not eligible for copyright protection; AI-assisted works with substantial human creative involvement may receive protection (creative portions belonging to human authors). The act of "taking a photo" in mobile ISP is typically considered sufficient creative involvement.
- **European Union:** AI-assisted works tend to be eligible for copyright, but AI itself cannot be a copyright holder; training data compliance for generative models is governed by the EU AI Act (high-risk systems require transparency declarations).
- **China:** The 2023 Beijing Internet Court "Spring Wind" case confirmed that AI-assisted creative works are eligible for copyright, owned by the person using the AI tool.

**ISP product-side principles:**
1. **User creates, user owns:** Manufacturers explicitly state in ToS that photos generated using AI enhancement features belong to the user; manufacturers make no copyright claim;
2. **Training data compliance:** AI model training data must be licensed (licensed datasets + manufacturer-owned data); avoid training ISP-related models on scraped unauthorized internet images;
3. **Model provenance transparency:** Advanced ISP systems record which version of the AI model was used for enhancement, facilitating compliance auditing.

---

## §13 Edge-Side AIGC Deployment

### 13.1 Inference Acceleration: From Lab to Mobile

Deploying SDXL-scale diffusion models to mobile NPUs faces three challenges: model size (> 2 GB), inference steps (20–50 steps), and numerical precision (FP32 → INT4). The following acceleration techniques collectively address all three:

**SDXL-Turbo (Sauer et al., 2023) — Adversarial Distillation:**

SDXL-Turbo is based on ADD (Adversarial Diffusion Distillation), compressing SDXL from 50 steps to 1–4 steps:
- Teacher model: Pre-trained SDXL (50-step DDIM);
- Student model: Trained via adversarial loss + Score Distillation Sampling (SDS);
- Single-step inference generates 1024² images; quality close to original SDXL (FID increases from 2.22 to 2.95 — perceptually acceptable);
- Inference time (A100 GPU): 50ms (vs. 5.3s for original).

**LCM (Latent Consistency Model; Song et al., 2023) — Consistency Distillation:**

LCM applies consistency models to latent diffusion, reaching SD-XL quality in 2–4 steps:

$$f_\theta(x_t, c, t) \approx x_0 \quad \text{(directly predict clean image from any timestep)}$$

Training objective is the consistency loss:
$$\mathcal{L}_{LC} = \mathbb{E}\left[ d\!\left(f_\theta(x_{t_n}, c, t_n),\; f_{\theta^-}(x_{t_{n-1}}, c, t_{n-1})\right) \right]$$

where $d(\cdot, \cdot)$ is LPIPS distance, ensuring perceptual consistency. LCM-LoRA further injects LCM acceleration capability into any fine-tuned SD model by adding only LoRA weights (~70 MB), without retraining the entire model.

**INT4 Quantization (4-bit Quantization):**

Applying INT4 weight quantization to the diffusion model U-Net/DiT (keeping activations at FP16) achieves 4× memory compression and 2–3× inference speedup, at the cost of minor quality loss:

| Quantization | Model Size | FID Loss | LPIPS Loss | Use Case |
|-------------|-----------|---------|-----------|---------|
| FP32 | Baseline | Baseline | Baseline | Server training |
| FP16 | ×0.5 | < 0.1 | < 0.005 | Server inference |
| INT8 | ×0.25 | ~0.3 | ~0.01 | High-end mobile NPU |
| INT4 | ×0.125 | ~1.2 | ~0.025 | Mainstream mobile NPU |
| INT4 (AWQ) | ×0.125 | ~0.5 | ~0.012 | **Recommended for mobile NPU** |

AWQ (Activation-aware Weight Quantization; Lin et al., 2023) uses activation-distribution-aware channel scaling to significantly improve INT4 quantization quality (FID loss reduced from 1.2 to 0.5).

### 13.2 Flagship Mobile AIGC Inference Performance (2024–2025)

The following data is aggregated from public benchmarks and manufacturer announcements (some estimates; test conditions vary):

| Manufacturer/Model | AIGC Feature | NPU Platform | Inference Time | Model Scale (est.) |
|-------------------|-------------|-------------|--------------|-------------------|
| **OPPO Find X7 Ultra** | AI Eraser (Scene Eraser) | Dimensity 9300 NPU | ~1.2s | ~200M INT8 |
| **vivo X100 Ultra** | AI Portrait SR | Dimensity 9300 + vivo V3 | ~0.8s | ~300M INT8 |
| **Xiaomi 15 Ultra** | AI Night Enhancement | Snapdragon 8 Elite NPU | ~0.9s | ~500M INT4 |
| **Apple iPhone 16 Pro** | Clean Up (object removal) | Apple A18 Pro Neural Engine | ~0.6s | ~150M FP16 |
| **Samsung Galaxy S25 Ultra** | Generative Edit | Snapdragon 8 Elite NPU | ~1.1s | ~400M INT4 |

**Path to achieving the < 1s target:**

Current (2025–2026) flagships largely achieve < 1.5s post-capture AI processing latency. For high-quality multi-step diffusion (text-to-image, complex object generation), latency remains 3–8s. Achieving < 1s edge AIGC requires:

1. **Consistency distillation (LCM/TurboLCM):** Compress inference to ≤ 4 steps;
2. **INT4 quantization + NPU-specific operators:** NPU vendors (Qualcomm AI Engine, MediaTek APU, Apple ANE) all provide dedicated acceleration instructions for Transformer attention computation;
3. **Model pruning:** Remove low-activation channels in diffusion U-Net for specific ISP tasks (typically 20–30% parameters prunable, < 5% quality loss);
4. **Tiled inference:** Partition 4K images into 512×512 tiles, process and merge sequentially, avoiding full-resolution OOM (peak memory issue).

### 13.3 Edge Inference Architecture Summary

```
Mobile camera RAW input
        │
        ├─── [Traditional ISP fast path]
        │    BLC → Demosaic → NR → CCM → Gamma → sRGB
        │    Latency: ~30ms (real-time preview)
        │
        └─── [AI enhancement post-processing, user-triggered]
             sRGB → resolution classification → task routing
                    │
                    ├─ Face detected? → CodeFormer INT4 (4-step LCM)
                    │                   ~300ms on NPU
                    │
                    ├─ Low-light scene? → DiffLight / SNR-Aware
                    │                     ~800ms on NPU
                    │
                    ├─ SR request? → Real-ESRGAN (real-time) or
                    │               SD-based SR (4-step LCM, ~600ms)
                    │
                    └─ Style request? → ControlNet + LoRA
                                        ~500ms on NPU (4-step Consistency)

Final output: enhanced sRGB + C2PA metadata ("AI Enhanced" annotation)
```

Core engineering principles for edge AIGC: **tiered processing** (traditional ISP guarantees real-time preview; AI enhancement is asynchronous post-processing), **task-aware routing** (select the optimal algorithm per scene), **quality safety net** (fall back to traditional ISP output if AI processing fails).

---

## §14 Further Reading and References

[1] Ho, J. et al. (2020). Denoising Diffusion Probabilistic Models (DDPM). arXiv:2006.11239

[2] Song, J. et al. (2020). Denoising Diffusion Implicit Models (DDIM). arXiv:2010.02502

[3] Song, Y. & Ermon, S. (2020). Score-Based Generative Modeling through Stochastic Differential Equations. arXiv:2011.13456

[4] Nichol, A. & Dhariwal, P. (2021). Improved Denoising Diffusion Probabilistic Models. arXiv:2102.09672

[5] Rombach, R. et al. (2022). High-Resolution Image Synthesis with Latent Diffusion Models (Stable Diffusion). arXiv:2112.10752

[6] Zhang, L. et al. (2023). Adding Conditional Control to Text-to-Image Diffusion Models (ControlNet). arXiv:2302.05543

[7] Wang, X. et al. (2024). Exploiting Diffusion Prior for Real-World Image Super-Resolution (StableSR). *Int. J. Comput. Vis. (IJCV)*, 2024. arXiv:2305.07015

[8] Lin, X. et al. (2024). DiffBIR: Towards Blind Image Restoration with Generative Diffusion Prior. *ECCV 2024*. arXiv:2308.15070

[9] Song, Y. et al. (2023). Consistency Models. ICML 2023. arXiv:2303.01469

[10] Lipman, Y. et al. (2023). Flow Matching for Generative Modeling. ICLR 2023. arXiv:2210.02747

[11] Peebles, W. & Xie, S. (2023). Scalable Diffusion Models with Transformers (DiT). ICCV 2023. arXiv:2212.09748

[12] Li, C. et al. (2020). Zero-Reference Deep Curve Estimation for Low-Light Image Enhancement (Zero-DCE). CVPR 2020. arXiv:2001.06826

[13] Wang, X. et al. (2021). GFPGAN: Towards Real-World Blind Face Restoration with Generative Facial Prior. CVPR 2021. arXiv:2101.04061

[14] Zhou, S. et al. (2022). CodeFormer: Towards Robust Blind Face Restoration with Codebook Lookup Transformer. NeurIPS 2022. arXiv:2206.11253

[15] Blau, Y. & Michaeli, T. (2018). The Perception-Distortion Tradeoff. CVPR 2018.

[16] Sauer, A. et al. (2023). Adversarial Diffusion Distillation (SDXL-Turbo). arXiv:2311.17042

[17] Luo, S. et al. (2023). Latent Consistency Models (LCM). arXiv:2310.04378

[18] Lin, J. et al. (2023). AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration. arXiv:2306.00978

[19] Fernandez, P. et al. (2023). The Stable Signature: Rooting Watermarks in Latent Diffusion Models. ICCV 2023. arXiv:2303.15435

[20] Ho, J. & Salimans, T. (2022). Classifier-Free Diffusion Guidance. arXiv:2207.12598

## §15 Glossary

| Term | Full Name | Definition |
|------|-----------|-----------|
| **DDPM** | Denoising Diffusion Probabilistic Model | A generative model based on iterative noise addition (forward process) and denoising (reverse process). Generates high-quality images in ~1000 steps from pure Gaussian noise. |
| **DDIM** | Denoising Diffusion Implicit Model | Deterministic non-Markovian variant of DDPM. Achieves ~20× speedup (50 steps) with < 0.5 FID loss. Enables exact inversion for editing. |
| **CFG** | Classifier-Free Guidance | Technique for conditioning diffusion generation on text/image prompts without a classifier. Higher CFG strength → output closer to prompt, at the cost of diversity and increased hallucination risk. |
| **ControlNet** | Controllable Neural Network | Architecture that adds spatial conditioning (edges, depth, segmentation, RAW) to a frozen diffusion model. Enables structure-preserving style transfer for ISP. |
| **LCM** | Latent Consistency Model | Distilled diffusion model achieving quality close to SDXL in 2–4 steps via consistency distillation. ~100× faster than DDPM. |
| **Flow Matching** | — | ODE-based generative model learning straight probability flow trajectories between data and noise. Faster training and fewer integration steps than SDE-based diffusion. |
| **DiT** | Diffusion Transformer | Diffusion model using ViT backbone instead of U-Net. Follows LLM-like scaling laws; better global receptive field; used in SD3 and FLUX. |
| **INT4 (AWQ)** | Activation-aware Weight Quantization | 4-bit weight quantization with activation-distribution-aware channel scaling. ~4× memory compression vs. FP16; primary quantization strategy for mobile NPU diffusion deployment. |
| **C2PA** | Coalition for Content Provenance and Authenticity | Industry standard for recording AI generation/enhancement metadata in image files. Enables content provenance tracking across platforms. |
| **Perception-Distortion trade-off** | — | Information-theoretic result (Blau & Michaeli, 2018): perceptual quality and signal fidelity (PSNR) cannot be simultaneously maximized. Defines the Pareto frontier of image restoration algorithms. |
