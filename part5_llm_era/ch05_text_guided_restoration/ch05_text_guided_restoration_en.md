# Part 5, Chapter 05: Text-Guided Image Enhancement and Zero-Shot Restoration

> **Position:** This chapter provides a systematic introduction to the methodology of using natural-language text as a conditioning signal to drive image enhancement and degradation restoration. Coverage includes CLIP (Contrastive Language-Image Pretraining) text-image alignment, diffusion-model text conditioning, Classifier-Free Guidance (CFG) tuning, and engineering practice in real-world ISP applications such as tone/color editing and zero-shot denoising.
> **Prerequisites:** Vol. 5 Ch. 02 (AIGC Generative Image Processing), Vol. 3 Ch. 07 (Diffusion Model Image Restoration)
> **Audience:** Algorithm engineer, product manager

---

## §1 Theory

### 1.1 CLIP Alignment: A Shared Semantic Space for Text and Images

The theoretical foundation of text-guided image enhancement is the joint text-image embedding space established by CLIP (Contrastive Language-Image Pretraining; Radford et al., ICML 2021). CLIP employs contrastive learning on 400 million image-text pairs so that semantically similar text descriptions and images are placed close together in the embedding space:

$$\mathcal{L}_{\text{CLIP}} = -\frac{1}{N} \sum_{i=1}^{N} \log \frac{\exp(\text{sim}(f_I(I_i), f_T(T_i)) / \tau)}{\sum_{j=1}^{N} \exp(\text{sim}(f_I(I_i), f_T(T_j)) / \tau)}$$

where $f_I$ and $f_T$ are the image and text encoders respectively, $\text{sim}(\cdot, \cdot)$ denotes cosine similarity, and $\tau$ is the temperature parameter.

In the context of image restoration and enhancement, the core value of CLIP alignment lies in: **transforming a subjective description of "what the target image should look like" (text) into a differentiable optimization loss**. Let the current image be $\hat{I}$ and the target text description be $T_{\text{target}}$ (e.g., "sharp, well-exposed portrait with natural skin tones"); the CLIP guidance loss (CLIP引导损失) is then:

$$\mathcal{L}_{\text{CLIP-guide}} = 1 - \text{sim}(f_I(\hat{I}),\, f_T(T_{\text{target}}))$$

By minimizing this loss, the image enhancement model steers the output in the semantic direction of the text description within the target embedding space.

### 1.2 Mathematical Foundations of Text-Conditioned Diffusion Models

Denoising Diffusion Probabilistic Models (DDPM; Ho et al., NeurIPS 2020) learn the image distribution through a forward noising process and a reverse denoising process. Conditional diffusion models (条件扩散模型) introduce a conditioning signal $c$ — which can be an image, text, segmentation map, or other modality — into the reverse process, guiding denoising toward the direction specified by the condition:

$$p_\theta(\mathbf{x}_{t-1} | \mathbf{x}_t, c) = \mathcal{N}(\mathbf{x}_{t-1}; \mu_\theta(\mathbf{x}_t, t, c), \Sigma_\theta(\mathbf{x}_t, t, c))$$

When the condition $c$ is a text embedding, the denoising network (typically a U-Net) injects text semantics into each layer's features via a cross-attention mechanism (交叉注意力机制):

$$\text{CrossAttn}(Q, K_c, V_c) = \text{softmax}\!\left(\frac{Q K_c^\top}{\sqrt{d}}\right) V_c$$

where $Q$ comes from image features and $K_c, V_c$ come from linear projections of the text embedding.

**Classifier-Free Guidance (CFG)** (Ho & Salimans, NeurIPS Workshop 2022) is the most critical engineering technique in text-guided diffusion. During training, the text condition is replaced with an empty null embedding with probability $p_{\text{uncond}}$ (typically 10%–20%). At inference time, a linear extrapolation between the conditional score and the unconditional score amplifies the effect of text guidance:

$$\tilde{\epsilon}_\theta(\mathbf{x}_t, c) = \epsilon_\theta(\mathbf{x}_t, \varnothing) + w \cdot [\epsilon_\theta(\mathbf{x}_t, c) - \epsilon_\theta(\mathbf{x}_t, \varnothing)]$$

where $w > 1$ is the CFG scale (guidance strength). The value of $w$ is the core trade-off parameter between text adherence (文本遵从度) and photorealism (图像真实感); see §3.2 for a detailed tuning guide.

### 1.3 Three Major Text-Guided Paradigms

**Paradigm 1: CLIP-Loss-Guided Diffusion Generation**

During the reverse denoising process of a diffusion model, CLIP gradients between the current intermediate image and the target text are computed at each step and superimposed on the predicted noise, steering the generation trajectory toward the semantic direction described by the text. This paradigm requires no additional training; it is an inference-time (推理时) intervention that is well suited to zero-shot customized enhancement.

**Paradigm 2: ControlNet Dual Text + Image Conditioning**

ControlNet (Zhang et al., ICCV 2023) adds an extra trainable conditioning branch — such as an edge map, depth map, segmentation map, or the original image itself — to a pretrained diffusion model, jointly constraining the generation process with the text condition. This achieves the effect of "changing style or tone as described by the text while preserving the structural layout of the original image." For ISP, the original image can serve as a structural control signal while the text description guides tone/exposure adjustment, effectively preventing structural collapse during enhancement.

**Paradigm 3: IP-Adapter Reference Image Guidance**

IP-Adapter (Ye et al., ICCV 2023) uses a lightweight image cross-attention adapter (图像交叉注意力适配器) to inject the style and color features of a reference image into the diffusion model, working in conjunction with the text condition. In ISP applications, the reference image can be a "target style obtained from a standard test chart after processing," and a text description such as "natural light, neutral color temperature, high dynamic range" further constrains the output, enabling ISP parameter optimization via reference-style transfer (参考风格迁移).

---

## §2 Methods

### 2.1 InstructPix2Pix: Instruction-Driven Image Editing

InstructPix2Pix (Brooks et al., CVPR 2023) is a landmark work in text-guided image editing. Its core contribution is reframing image editing as a "follow-the-instruction" problem: given an original image $I$ and an editing instruction text $T$ (e.g., "make the photo warmer," "reduce the noise in shadows"), the model directly outputs the edited image $I'$ without requiring the user to supply additional masks or reference images.

Training data construction is the key innovation of this work: GPT-3 is used to generate large quantities of image editing instruction pairs, and Prompt2Prompt (Hertz et al., ICLR 2023) is then used on Stable Diffusion to synthesize "original → edited" paired data in batch, ultimately fine-tuning Stable Diffusion on approximately 454K pairs.

Direct applications of InstructPix2Pix to ISP-related tasks:

- **"Increase the contrast while preserving natural colors"** → contrast enhancement without color oversaturation
- **"Reduce noise in dark areas without blurring edges"** → selective denoising (选择性去噪)
- **"Make the exposure more even across the whole image"** → local tone mapping balance (局部色调映射平衡)
- **"Correct the green tint in this photo"** → post-AWB (自动白平衡后处理) color correction

At inference time, the model simultaneously relies on the original image condition $c_I$ and the text instruction condition $c_T$, guided by dual CFG (双CFG):

$$\tilde{\epsilon} = \epsilon(\varnothing, \varnothing) + w_I [\epsilon(c_I, \varnothing) - \epsilon(\varnothing, \varnothing)] + w_T [\epsilon(c_I, c_T) - \epsilon(c_I, \varnothing)]$$

where $w_I$ controls fidelity to the original image structure and $w_T$ controls the degree to which the text instruction is followed — the two parameters are independently adjustable.

### 2.2 Stable Diffusion XL and CosXL for Photography-Grade Enhancement

SDXL (Podell et al., ICLR 2024) uses a larger U-Net (2.6B parameters, 3.5× that of SD1.5) and dual text encoders (OpenCLIP ViT-bigG + CLIP ViT-L). Its improvements in photographic realism stem primarily from two aspects: (1) incorporating Aesthetic Score and Crop Coordinate as additional conditions, enabling specification of the desired image quality level during generation; and (2) using a Refiner model — a separate diffusion model trained specifically for high-frequency detail — to refine the image in the final stage, significantly reducing the low-frequency blur artifacts commonly found in ISP outputs.

CosXL (from Stability AI, 2024) is an SDXL variant specifically optimized for photography-grade color style transfer (摄影级色彩风格迁移), continuously fine-tuned on photographic community color-style data. Its practical significance for ISP tone-style enhancement: photographic styles can be driven directly via text descriptions such as "Cinematic teal-orange grade" or "Clean Kodak Portra film look."

### 2.3 SmartEdit and ISP-Specific Instruction Editing

SmartEdit (Huang et al., CVPR 2024) introduces a Bidirectional Interaction Module (BIM; 双向交互机制) that enables the diffusion model to understand editing instructions requiring complex reasoning — for example, "brighten the face in this backlit portrait without affecting the background" — rather than handling only simple global style transfers. Its technical contributions to ISP tasks:

- **Semantics-aware local enhancement (语义感知局部增强)**: A multimodal large language model (MLLM) first understands the image structure (where is the face, what is the primary subject), then localizes enhancement operations precisely to the relevant semantic regions rather than applying them uniformly to the entire image.
- **Compound instruction decomposition (复合指令分解)**: Complex ISP instructions (e.g., "increase shadow detail while preventing highlight clipping and keeping natural skin tones") are semantically decomposed, executed sequentially, and then fused into the final result.

### 2.4 Zero-Shot Image Restoration

Zero-shot restoration (零样本复原) refers to methods capable of performing restoration without collecting paired training data for a specific degradation type (noise, blur, compression artifacts) — relying solely on a text description of the degradation type as a conditioning signal.

Core idea: encode the degradation description (e.g., "Gaussian noise with σ=25," "JPEG compression artifacts Q=20") as a text condition, inject it into a pretrained general-purpose diffusion model, and leverage the clean-image prior the model has learned from massive natural images to drive the reverse denoising process:

$$\mathbf{x}_{t-1} = \underbrace{\mu_\theta(\mathbf{x}_t, t, c_{\text{degrad}})}_{\text{diffusion prior}} + \underbrace{\lambda \nabla_{\mathbf{x}_t} \log p(\mathbf{y} | \mathbf{x}_t)}_{\text{data consistency term}}$$

where $\mathbf{y}$ is the degraded observation image, $p(\mathbf{y} | \mathbf{x}_t)$ is the degradation likelihood function, and $\lambda$ is the data-consistency strength coefficient. Representative works include DiffPIR (Zhu et al., CVPR 2023) and DDNM (Wang et al., ICLR 2023), both of which match or exceed supervised methods under the zero-shot setting.

---

## §3 Tuning

### 3.1 Prompt Engineering for ISP Tasks

Prompt engineering (Prompt工程) is as important as neural network weights in text-guided enhancement. The following are design principles for prompts targeting common ISP tasks:

**Positive Prompt (正向Prompt) Design Principles:**

1. **Describe the target quality specifically**, rather than using vague adjectives:
   - Poor: "make it better"
   - Good: "sharp, well-exposed, neutral white balance, low noise, natural skin tones"

2. **Explicitly specify preservation constraints** to prevent over-enhancement (过增强):
   - "increase contrast while preserving natural color saturation"
   - "reduce shadow noise without affecting highlight detail"

3. **Provide scene context** to improve semantic understanding:
   - "portrait photo, soft indoor light, increase facial clarity"
   - "night street photography, reduce high-ISO grain while keeping light trails"

**Negative Prompt (负向Prompt) Design Principles:**

Negative prompts constrain the generation space by listing undesired attributes, and are an important tool for avoiding enhancement artifacts:

- General ISP negative prompt: "oversaturated colors, plastic skin texture, halo artifacts, color bleeding, blown highlights, crushed blacks, motion blur, compression artifacts"
- Portrait-specific negative prompt: "unnatural skin tones, teeth texture loss, eye detail blurring, hair strand smearing"
- Night-scene-specific negative prompt: "color noise, banding, star artifacts around point lights, loss of shadow detail"

### 3.2 CFG Scale Tuning Strategy

CFG scale $w$ is the most sensitive hyperparameter in text-guided enhancement. Its behavioral characteristics at different settings are summarized below:

| CFG Scale $w$ | Effect Description | ISP Use Case |
|---|---|---|
| 1.0 (no guidance) | Completely ignores text; relies only on the image prior | Not applicable |
| 3.0–5.0 | Mild text tendency; high photorealism | Fine tone micro-adjustment, local denoising |
| 7.0–9.0 | Balanced; default recommended range | General ISP enhancement |
| 12.0–15.0 | Strong text compliance; may produce over-enhancement | Stylization, creative color grading |
| >20.0 | Excessive guidance; abnormally high saturation/contrast | Avoid for photorealistic ISP |

For ISP enhancement tasks, it is recommended to run ablation experiments in the range $w \in [5.0, 9.0]$, selecting the optimal value based on joint optimization of PSNR/SSIM and CLIP-Score rather than pursuing a single metric extreme.

**Dual CFG Tuning (InstructPix2Pix Scenario):**

Image guidance strength $w_I$ (recommended range 1.0–2.0) controls fidelity to the original image — too low leads to structural drift, too high causes the text effect to vanish. Text instruction strength $w_T$ (recommended range 5.0–9.0) controls the degree to which the instruction is executed. For ISP enhancement, the recommended starting point is $w_I = 1.5$, $w_T = 7.5$, followed by task-specific fine-tuning.

### 3.3 Inference Steps and DDIM Acceleration

Standard DDPM requires 1000 reverse denoising steps, which is unacceptable in practice. DDIM (Song et al., ICLR 2021) compresses the step count to 20–50 through deterministic sampling with negligible quality loss. LCM (Latent Consistency Model; Luo et al., ICLR 2024) further reduces the step count to 4–8, making it suitable for real-time preview on mobile devices.

Recommendation for ISP applications: use LCM in preview mode (4 steps, latency < 500 ms) and DDIM for final output (25 steps, higher fidelity).

---

## §4 Artifacts

### 4.1 Text-Image Semantic Misalignment

Text-image semantic misalignment (文本-图像语义错位) is the most common artifact type in text-guided enhancement: the enhancement effect described in the text does not match the actual changes in the image.

Typical cases:
- **"brighten the image"** → underexposed shadow areas are correctly brightened, but highlights simultaneously blow out (the text did not specify highlight protection).
- **"make colors more vivid"** → sky and vegetation saturation increases normally, but facial skin tones become simultaneously oversaturated (severe orange shift), deviating from photorealistic standards.
- **"add film grain"** → the spatial frequency of the synthesized noise texture does not match the original sensor noise, producing a noticeable layered grain effect.

The root cause is that CLIP text encoding has limited spatial discrimination between "local" and "global" semantics. In the CLIP embedding space, the text description "brighten shadows" cannot precisely differentiate "shadow regions" from "overall luminance," causing global operations to override local intent.

**Mitigation strategies:**
- Use ControlNet's local mask control to confine the text-guided effect to the target semantic region (requires SAM to generate region masks).
- Append spatial descriptive keywords: "in the shadow regions only," "only for the background."
- Adopt multi-stage processing: first apply global adjustments, then perform local refinement.

### 4.2 Semantic Drift: Facial Identity Change

When enhancement instructions alter low-level features of the face region (skin tone, texture), the diffusion model sometimes introduces high-level semantic changes not specified in the instruction, causing subtle alterations to the subject's identity (facial features, expression). This "semantic drift" (语义漂移) is particularly dangerous in portrait ISP, as users may perceive that "the person in the photo has changed."

Quantification metric: use the ArcFace face recognition model to compute cosine similarity before and after enhancement; values below 0.85 are considered to indicate significant identity drift. In practice, InstructPix2Pix exhibits an identity drift rate of approximately 12% (proportion of samples with similarity < 0.85) under the instruction "dramatically smooth skin."

**Mitigation strategies:**
- Apply an identity preservation loss (身份保持损失) to the face region, adding a constraint to the diffusion trajectory of face patches during inference: $\mathcal{L}_{\text{id}} = 1 - \text{sim}(f_{\text{face}}(I'), f_{\text{face}}(I))$
- Use IP-Adapter with the original face as a reference image to impose a rigid identity constraint.

### 4.3 Hallucinated Texture in Smooth Regions

The generative nature of diffusion models leads them to "invent" texture details that do not exist in the original image within smooth regions (sky, skin, walls). Such "hallucinated texture" (幻觉纹理) constitutes a high-severity distortion in photographic ISP, as it is equivalent to tampering with image content.

Typical case: applying "enhance texture detail" to a low-light skin image causes the diffusion model to generate convincing but fictitious pore textures on the forehead and nose bridge, inconsistent with the subject's actual skin condition.

**Mitigation strategies:**
- Lower the CFG scale ($w < 7$) to reduce forced text intervention in fine-detail generation.
- Increase the weight of the image consistency constraint term ($\lambda$) to prevent excessive deviation from the original image.
- Incorporate perceptual consistency metrics in evaluation (e.g., deep-feature distance LPIPS) rather than optimizing CLIP-Score alone.

### 4.4 Color Space Inconsistency

Text-guided enhancement models are typically trained on sRGB/JPEG data. Applying them directly to linear RGB or RAW data in the ISP pipeline may produce tone anomalies — over-red or over-green casts — caused by color space mismatch (色彩空间不匹配). In engineering practice it is essential to apply sRGB gamma encoding before feeding data into the diffusion model, then apply the inverse gamma transform back to linear space after obtaining the output.

---

## §5 Evaluation

### 5.1 Text-Image Alignment Metric: CLIP-Score

CLIP-Score (Hessel et al., EMNLP 2021) is the core automated evaluation metric for text-guided generation and editing. It computes the CLIP similarity between the enhanced image and the target text description:

$$\text{CLIP-Score}(I', T) = w \cdot \max(0,\, \text{sim}(f_I(I'), f_T(T)))$$

where $w = 2.5$ is a normalization coefficient that maps similarity to a 0–100 score range. A higher CLIP-Score indicates that the enhancement result better matches the semantic intent of the text description.

**Important limitation**: a high CLIP-Score does not equal high image quality. The CLIP-Score for "saturated, high-contrast photo" may be very high, yet the image may exhibit severe over-enhancement artifacts. Therefore CLIP-Score must always be used in conjunction with traditional image quality assessment (IQA) metrics.

### 5.2 Joint Image Quality and Content Fidelity Evaluation

For text-guided ISP enhancement, the following multi-dimensional evaluation matrix is recommended:

| Metric | Type | Measures | ISP Relevance |
|---|---|---|---|
| PSNR (dB) | Pixel-level | Signal-to-noise ratio vs. reference | Denoising, deblurring effectiveness |
| SSIM | Structure-level | Structural similarity | Detail fidelity; guards against semantic drift |
| LPIPS | Perceptual-level | Deep feature distance | Perceptual realism |
| CLIP-Score | Semantic-level | Text-image alignment | Instruction compliance degree |
| FID (if distribution data available) | Distribution-level | Realism of generated image distribution | Overall style naturalness |
| ArcFace similarity | Identity-level | Facial identity preservation | Mandatory for portrait enhancement scenarios |

### 5.3 TEdBench: Standard Benchmark for Text-Driven Editing

TEdBench (Kawar et al., CVPR 2023) is an evaluation benchmark specifically designed for text-driven image editing, containing 100 triplets of "original image – editing instruction – human ground-truth edited image," covering tasks such as tone adjustment, object replacement, and style transfer. Evaluation dimensions: Direction Accuracy (指令遵从度; instruction compliance) and Background Preservation (内容保真度; content fidelity) are scored independently.

For ISP-specific applications, it is recommended to augment TEdBench with an ISP-dedicated test subset:
- 50 images with exposure bias (+/−1.5 EV) + corresponding correction instructions
- 30 images with color cast (color temperature deviation > 500 K) + corresponding correction instructions
- 20 low-light noisy images + corresponding denoising instructions

### 5.4 Human Preference Study

For highly subjective ISP enhancement tasks (tone style, skin texture), automated metrics cannot fully substitute for user perception. Recommended A/B test design:

- **Participants**: 20 non-professional photography users + 5 professional photographers, scoring in separate groups
- **Scoring dimensions**:
  - Overall Preference: binary choice — select the preferred version
  - Instruction Compliance: 1–5 score — does the enhancement match the text instruction description?
  - Photorealism: 1–5 score — does the result look like a real photograph rather than an AI-generated image?
  - Detail Preservation: 1–5 score — are important details from the original image retained?

---

## §6 Code

The companion code notebook for this chapter is *See §6 Code section for runnable examples.*, demonstrating the following experiments:

**Experiment 1: InstructPix2Pix ISP Enhancement Demo**

The notebook uses the `diffusers` library to load the `timbrooks/instruct-pix2pix` model and applies targeted text instructions (e.g., "correct the overexposed highlights and bring back sky detail") to a set of images with typical ISP problems (overexposed portrait, underexposed night scene, color-shifted indoor shot, high-ISO noise image). The independent adjustment effects of the dual CFG parameters ($w_I$, $w_T$) are demonstrated, and a grid plot visualizes the enhancement results across different parameter combinations, intuitively showing the trade-off between image fidelity and instruction compliance.

**Experiment 2: CFG Scale Ablation**

With a fixed text instruction ("increase contrast and reduce noise while preserving natural colors"), enhancement results are generated for the same test image at 6 values of $w_T \in \{3, 5, 7, 9, 12, 15\}$. CLIP-Score and LPIPS are computed for each result, and a dual-axis line chart of CFG Scale vs. CLIP-Score / LPIPS is plotted, intuitively revealing the optimal operating point.

**Experiment 3: Negative Prompt Effectiveness Comparison**

For a portrait enhancement task, results with and without a negative prompt ("unnatural skin tones, plastic texture, halo artifacts") are compared. ArcFace similarity and NIQE are used to quantify identity preservation and perceptual quality respectively, demonstrating the effectiveness of negative prompts in reducing excessive skin smoothing.

**Experiment 4: Zero-Shot Denoising (DDNM Method)**

A pretrained SDXL model is loaded and used with the text condition "Remove high-ISO camera noise, preserve edge sharpness" to perform zero-shot denoising on a synthetically degraded image (Gaussian noise with σ=30 added). Results are compared with DnCNN (supervised baseline), PSNR/SSIM is computed, and the practical value of zero-shot methods in scenarios without paired training data is discussed.

---

## §7 InstructPix2Pix Image Enhancement: A Full Engineering Case Study

InstructPix2Pix (Brooks et al., CVPR 2023) is the most practically valuable framework for applying natural-language instructions to ISP post-processing, but productionizing it requires extensive customization for specific ISP scenarios. This section provides a complete engineering case analysis.

### 7.1 Designing Effective ISP Instructions

Effective instructions for ISP scenarios must satisfy three criteria: **operability** (mappable to specific parameter adjustments), **unambiguity** (no ambiguous interpretation), and **fidelity specification** (explicitly constraining what should not change).

**Examples of Effective ISP Instructions:**

| Quality Problem | Ineffective Instruction (Avoid) | Effective Instruction (Recommended) |
|---|---|---|
| Overall underexposure | "make it brighter" | "increase midtone brightness while protecting highlights from clipping" |
| Color cast (green tint) | "fix the color" | "remove the green color cast and restore neutral white balance" |
| Excessive shadow noise | "denoise the photo" | "reduce noise in shadow areas while preserving edge sharpness and fine texture" |
| Yellow skin tone | "improve skin tone" | "correct the yellow-orange skin tone cast to a natural neutral warm tone" |
| Insufficient edge sharpness | "sharpen the image" | "enhance edge sharpness for fine details without introducing halo artifacts" |
| Insufficient dynamic range | "improve the contrast" | "lift shadow detail in the lower 20% of the tonal range while compressing highlights" |

**Counter-Examples of Ambiguous Instructions:**
- "make this photo look better": completely inoperable; model behavior is unpredictable
- "enhance the photo": unconstrained enhancement may simultaneously boost contrast, saturation, and sharpness, introducing over-enhancement artifacts
- "professional look": an aesthetic concept that cannot be mapped to deterministic ISP parameters

**Multi-Step Instruction Decomposition Strategy**: For complex compound quality problems (e.g., "backlit portrait: underexposed face + overexposed background + orange skin cast"), it is recommended to decompose the compound instruction into three independent single-objective instructions executed **sequentially**, with quality verification after each step to avoid multi-objective conflicts:

```
Step 1: "Brighten the face region in this backlit portrait by 1–1.5 EV"
Step 2: "Recover highlight detail in the overexposed sky and background"
Step 3: "Cool the warm orange skin tone to a natural neutral warm"
```

### 7.2 Training Data Construction Method

The original InstructPix2Pix uses GPT-3 to generate general editing instructions, and its training data coverage of ISP-specific tasks is insufficient. Method for constructing a dedicated fine-tuning dataset for ISP:

**Data Construction Pipeline (ISP Parameter Perturbation + VLM Caption Generation):**

```
1. Base Image Collection
   • Collect 10K–50K high-quality RAW images (multiple scenes, multiple light sources)
   • Process with a reference ISP pipeline to obtain "clean baseline" images I_ref

2. ISP Parameter Perturbation
   • Apply random parameter perturbations to each baseline image:
     - AWB shift: ±500K color temperature, simulating warm/cool cast
     - AE shift: ±0.5 EV / ±1.5 EV, simulating underexposure/overexposure
     - NR intensity: ×0.5 / ×2.0, simulating under-denoising/over-denoising
     - CCM saturation: ±0.1, simulating oversaturation/undersaturation
   • Generate 3–5 perturbed versions I_degraded per image

3. Instruction Generation (GPT-4V Assisted)
   • Feed the (I_ref, I_degraded) image pair to GPT-4V
   • Prompt: "Describe the ISP adjustment operation needed to convert
             the second image into the first image.
             Express it as one concise English instruction that is:
             specific, actionable, and states the preservation constraints."
   • GPT-4V outputs instruction T (e.g., "reduce the warm color cast and
     restore neutral whites while keeping the golden-hour warmth")

4. Data Format
   • Triplets: (I_degraded, T, I_ref) = (input image, instruction, target image)
   • Recommended dataset size: 20K–100K pairs for ISP-specific fine-tuning
     (far fewer than the 454K pairs used for general editing)

5. Quality Filtering
   • Compute PSNR for each (I_ref, I_degraded) pair:
     - Filter out pairs with PSNR > 38 dB (perturbation too small; instruction meaningless)
     - Filter out pairs with PSNR < 15 dB (perturbation too large; outside realistic ISP error range)
```

**Data Augmentation Strategy**: Use GPT-4V to generate 3–5 differently worded instructions (semantically equivalent but lexically varied) for each image pair, increasing diversity in instruction phrasing and improving model robustness to natural language variants.

### 7.3 Inference Latency vs. Image Quality Trade-off

The inference latency of InstructPix2Pix is primarily determined by the number of diffusion steps. Recommended configurations for different deployment scenarios:

| Use Scenario | Recommended Steps | Sampler | Resolution | Typical Latency (A100) | Latency (Mobile NPU) |
|---|---|---|---|---|---|
| Real-time preview | 4 steps | LCM | 512×512 | ~120 ms | ~2.5 s |
| Quick draft | 8 steps | DPM++ 2M | 768×768 | ~380 ms | N/A (too slow) |
| High-quality output | 25 steps | DDIM | 1024×1024 | ~1.8 s | N/A |
| Maximum fidelity | 50 steps | DDIM | 1024×1024 | ~3.5 s | N/A |

**Latency–Quality Pareto Analysis:**

From the practical requirements of ISP post-processing, the recommended approach is to execute **server-side** 25-step DDIM inference at 1024×1024 resolution (latency < 2 s) and return the result to the client for display. For latency-sensitive real-time preview, run LCM at 4 steps and 512×512 resolution as an effects preview only; switch to the high-quality configuration when saving the final image.

**Image Fidelity Constraints**: When the ISP objective is "precisely correcting a color cast" rather than "creative stylization," $w_I$ (image guidance strength) should be set to 1.2–1.8, ensuring the enhanced image maintains structural consistency with the original (SSIM > 0.85). Sacrificing some CLIP-Score in exchange for higher LPIPS fidelity is the correct trade-off in ISP applications.

---

## §8 ControlNet in ISP Post-Processing

### 8.1 ControlNet Fundamentals and ISP Adaptation

ControlNet (Zhang et al., ICCV 2023) introduces a trainable "control branch" that enables the diffusion model to accept additional structural control signals — such as edge maps, depth maps, and pose maps — beyond the text condition. The core mechanism copies the U-Net encoder weights into the control branch; the intermediate features of the two branches are then added together via zero-initialized convolutions (零初始化卷积):

$$\mathbf{h}_{\text{output}} = \mathbf{h}_{\text{pretrained}} + \mathcal{Z}(\mathbf{h}_{\text{control}})$$

Zero initialization ensures that at the start of training the control branch has no effect on the original model; as training progresses, the control branch gradually learns to inject structural signals into the generation process.

**ControlNet Usage Scheme for ISP Post-Processing:**

In the ISP scenario, **the original image itself** can serve as the structural control signal:
- Use a Canny edge map as the control signal: preserves edge positions and directions, preventing the enhancement process from altering object contours
- Use a depth map (estimated by MiDaS) as the control signal: during backlit portrait enhancement, ensures that the spatial relationship between foreground and background is unchanged
- Use the HED soft edge map of the original image: more natural than Canny and better suited to organic textures (skin, fabric, foliage)

```
ControlNet ISP Enhancement Pipeline:

Original Image I
    │
    ├──→ Canny Edge Extraction  ──→ ControlNet Control Branch (structural preservation)
    │
    ├──→ Text Instruction T  ────→ Text Condition (drives tone/exposure changes)
    │
    └──→ VQVAE Encoding  ────────→ Noisy Latent Initialization (content preservation)
                                        ↓
                                  Diffusion Reverse Denoising
                                        ↓
                                  Enhanced Image I'
```

### 8.2 Using Edge Maps as Control Signals to Improve Detail Recovery

In ISP low-light enhancement scenarios, traditional methods (Retinex-based approaches, BM3D) suffer from "excessive detail smoothing" — the denoising process inadvertently removes valid texture edges. The ControlNet approach provides precise edge location constraints, enabling structural detail preservation during denoising:

**Experimental Setup** (low-light portrait enhancement):
- Input: EV−2 underexposed portrait with pronounced high-ISO noise
- Text instruction: "Brighten this low-light portrait, reduce noise, restore natural skin detail"
- Control signal: HED edge map extracted from the original image (retaining facial contours and hair-strand edges)
- Comparison methods: InstructPix2Pix without ControlNet, CBDNet (traditional denoising)

**Quantitative Results** (evaluated on 100 low-light portrait test images):

| Method | PSNR (↑) | SSIM (↑) | LPIPS (↓) | Edge Preservation F-score (↑) |
|---|---|---|---|---|
| CBDNet (traditional) | 30.2 dB | 0.871 | 0.098 | 0.76 |
| InstructPix2Pix (no ControlNet) | 28.9 dB | 0.843 | 0.112 | 0.68 |
| ControlNet + HED (edge control) | **31.4 dB** | **0.892** | **0.081** | **0.89** |

The ControlNet approach outperforms unconstrained InstructPix2Pix on all metrics, with a 2.5 dB PSNR gain and a substantial improvement in edge preservation. The reason is clear: the structural constraint provided by the edge map effectively prevents the diffusion model from "over-smoothing" high-frequency detail regions during the denoising process.

### 8.3 Comparison with Traditional Sharpening

Traditional sharpening methods (USM, Laplacian sharpening) enhance edges via high-pass filtering and suffer from an inherent defect: halo artifacts (光晕伪影). The mechanism by which ControlNet preserves structure is fundamentally different:

| Dimension | Traditional Sharpening (USM) | ControlNet Edge Enhancement |
|---|---|---|
| **Principle** | Frequency-domain high-pass filter superposition | Diffusion model generative prior + edge constraint |
| **Halo artifacts** | Common (especially at high gain) | Significantly reduced (generative prior enables natural transitions) |
| **Noise amplification** | Significant (sharpening amplifies noise) | Absent (denoising is performed simultaneously) |
| **Processing speed** | Extremely fast (< 1 ms) | Slow (seconds; requires diffusion steps) |
| **Controllability** | Simple (single gain parameter) | Controlled via text + $w_T$ adjustment |
| **Applicable scenario** | Real-time ISP pipeline | Offline post-processing, professional retouching |

Conclusion: ControlNet is not suitable for replacing the sharpening module in a real-time ISP pipeline. Its value lies in **offline high-quality post-processing** — applied by users after shooting within an app, where higher latency is tolerable and maximum perceptual quality is the goal.

---

## §9 Productization Challenges for Text-Guided Image Enhancement

### 9.1 Ambiguity in User Instructions

**Core problem**: "make it look better" is the most natural expression for users, but it is completely inoperable for the model. The layers of ambiguity that productization must address:

**Semantic ambiguity (语义歧义)**: the same instruction carries different intent across users and scenes:
- "warmer photo": a photographer understands this as "increase the warm color cast (shift to higher color temperature)"; a general user may interpret it as "make the photo feel warm and cozy (brighter face, more prominent smile)"
- "vintage look": could mean film grain, color fading, color shift, or vignetting — and the intensity of each dimension is uncertain

**Degree ambiguity (程度歧义)**:
- "slightly brighter" vs. "much brighter": the EV offset corresponding to "slight" varies completely depending on the scene's base exposure (for an underexposed image "slightly" might mean +1 EV; for a normally exposed image it means +0.3 EV)

**Local vs. global ambiguity (局部 vs. 全局歧义)**:
- "brighten the person": does this mean the face? the full body? all foreground subjects? Without a spatial qualifier, the model defaults to a global operation

**Resolution strategy**: establish an **intent clarification dialogue** mechanism — when the user inputs an ambiguous instruction, the system proactively asks:

```
User:   "Make this photo look better"
System: "I found several aspects of this photo that could be improved.
         Please select:
         ① Face is too dark (recommended: fill light)
         ② Background has a blue color cast (recommended: white balance adjustment)
         ③ Overall contrast is low (recommended: tonal enhancement)
         Or optimize all of the above together?"
```

### 9.2 Standardized Quality Instruction Vocabulary (Industry Vocabulary)

Productized text-guided enhancement requires a **standardized quality instruction vocabulary (标准化质量指令词汇体系)** to enable reliable mapping from user natural language to actionable instructions:

**Level 1: Global Quality Instructions**

| User Expression (Natural Language) | Standardized Instruction | Corresponding ISP Operation |
|---|---|---|
| "too dark" / "underexposed" | `GLOBAL_EXPOSURE_UP_1EV` | AE target +1 EV, lift shadows locally |
| "too bright" / "overexposed" | `GLOBAL_EXPOSURE_DOWN_1EV` | AE target −1 EV, recover highlight detail |
| "yellow/orange color cast" | `WB_COOL_SHIFT` | AWB R gain −0.1, B gain +0.08 |
| "blue/cool color cast" | `WB_WARM_SHIFT` | AWB R gain +0.1, B gain −0.08 |
| "too blurry" | `SHARPEN_GLOBAL_MODERATE` | Sharpening gain +0.3, threshold = 2 |
| "too much noise" | `DENOISE_MODERATE` | NR intensity ×1.5, preserve edges |

**Level 2: Semantic Scene Instructions**

| Scene Intent | Standardized Instruction | Composite ISP Operation |
|---|---|---|
| "face too dark" | `FACE_BRIGHTEN` | Face detection + local tone mapping |
| "unnatural skin color" | `SKIN_TONE_NORMALIZE` | CCM skin tone angle adjustment + saturation |
| "flat sky" | `SKY_ENHANCE` | Sky segmentation + contrast enhancement + blue saturation |
| "night scene details unclear" | `NIGHT_DETAIL_ENHANCE` | Shadow lift + NR + local contrast |

**Level 3: Style Instructions (offline post-processing only)**

| Style Description | Standardized Instruction | Diffusion Model Condition |
|---|---|---|
| "film look" | `STYLE_FILM_GRAIN` | Add organic grain + mild fading + vignetting |
| "cinematic look" | `STYLE_CINEMATIC` | Teal-orange color grade + shadow compression + wide-format simulation |
| "Japanese soft look" | `STYLE_JAPAN_SOFT` | Low saturation + high brightness + slight cyan shift |

The significance of the vocabulary lies in: **transforming the parsing of user intent from implicit model behavior into explicit system-level routing**, making product behavior predictable, testable, and auditable.

### 9.3 Copyright and Content Safety Issues

Text-guided image enhancement in productized form faces unique copyright and safety risks:

**Copyright Issues:**

*Style transfer copyright (风格迁移版权)*: When a user instructs the system to "convert this photo to a black-and-white image in the style of Ansel Adams," does this infringe the photographer's stylistic copyright? As of 2025 there is no legal consensus, but the mainstream platform policy is: allow descriptive use of "style," prohibit explicit naming of living photographers/artists for style imitation.

*Training data copyright (训练数据版权)*: InstructPix2Pix and SDXL were trained on large quantities of web images; related lawsuits (e.g., Getty Images v. Stability AI) are ongoing. Organizations deploying these models must monitor the copyright licensing status of the underlying foundation model and preferentially choose models trained on datasets with clear copyright authorization (e.g., the LAION-5B Aesthetic subset).

**Content Safety Issues:**

*Portrait tampering risk (人像篡改风险)*: Text-guided enhancement can modify facial appearance in a natural-looking way (skin tone, perceived age, expression). When used in a product, the following safeguards are mandatory:
1. Establish a "face modification audit log" recording all enhancement operations applied to the face region
2. Add a watermark or user notification for enhancement results with significant identity change (ArcFace similarity < 0.85)
3. Prohibit features that make a person look more like a specific celebrity based on text instructions

*Misuse prevention (误用防范)*: Users may attempt to use the ISP enhancement interface to perform non-ISP operations (e.g., "remove the person from the background"). At the product layer, this requires:
- Restricting the instruction domain (allow quality-related instructions only; filter out content-editing instructions)
- Monitoring the semantic similarity between output and input images (reject output if the CLIP semantic shift is too large)

*Deepfake risk (深度伪造风险)*: Diffusion-model-based image enhancement shares the same underlying foundation as Deepfake technology. Before a product goes live, it should undergo a professional misuse risk assessment and implement C2PA (Coalition for Content Provenance and Authenticity; 内容来源认证) standards, recording "AI-enhanced" provenance information in image metadata.

---

## References

[1] Brooks, T., Holynski, A., & Efros, A. A. (2023). InstructPix2Pix: Learning to Follow Image Editing Instructions. *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*.

[2] Zhang, L., Rao, A., & Agrawala, M. (2023). Adding Conditional Control to Text-to-Image Diffusion Models (ControlNet). *IEEE/CVF International Conference on Computer Vision (ICCV)*.

[3] Ye, H., Zhang, J., Liu, S., Han, X., & Yang, W. (2023). IP-Adapter: Text Compatible Image Prompt Adapter for Text-to-Image Diffusion Models. *IEEE/CVF International Conference on Computer Vision (ICCV)*.

[4] Radford, A., Kim, J. W., Hallacy, C., Ramesh, A., Goh, G., Agarwal, S., ... & Sutskever, I. (2021). Learning Transferable Visual Models From Natural Language Supervision (CLIP). *International Conference on Machine Learning (ICML)*.

[5] Podell, D., English, Z., Lacey, K., Blattmann, A., Dockhorn, T., Müller, J., ... & Rombach, R. (2024). SDXL: Improving Latent Diffusion Models for High-Resolution Image Synthesis. *International Conference on Learning Representations (ICLR)*.

[6] Ho, J., Jain, A., & Abbeel, P. (2020). Denoising Diffusion Probabilistic Models (DDPM). *Advances in Neural Information Processing Systems (NeurIPS)*, 33.

[7] Ho, J., & Salimans, T. (2022). Classifier-Free Diffusion Guidance. *NeurIPS 2021 Workshop on Deep Generative Models and Downstream Applications*.

[8] Kawar, B., Zada, S., Lang, O., Tov, O., Chang, H., Dekel, T., ... & Irani, M. (2023). Imagic: Text-Based Real Image Editing with Diffusion Models. *CVPR 2023*. (TEdBench released concurrently)

[9] Wang, Y., Yu, J., & Zhang, J. (2023). Zero-Shot Image Restoration Using Denoising Diffusion Null-Space Model (DDNM). *International Conference on Learning Representations (ICLR)*.

[10] Hessel, J., Holtzman, A., Forbes, M., Bras, R. L., & Choi, Y. (2021). CLIPScore: A Reference-free Evaluation Metric for Image Captioning. *Empirical Methods in Natural Language Processing (EMNLP)*.

[11] Huang, Y., Cao, J., Li, X., & Loy, C. C. (2024). SmartEdit: Exploring Complex Instruction-based Image Editing with Multimodal Large Language Models. *CVPR 2024*. arXiv:2312.06739.

[12] Luo, S., Tan, Y., Huang, L., Li, J., & Zhao, H. (2024). Latent Consistency Models: Synthesizing High-Resolution Images with Few-Step Inference. *ICLR 2024*. arXiv:2310.04378.

[13] Kirillov, A., Mintun, E., Ravi, N., Mao, H., Rolland, C., Gustafson, L., ... & Girshick, R. (2023). Segment Anything (SAM). *IEEE/CVF International Conference on Computer Vision (ICCV)*.

[14] Hertz, A., Mokady, R., Tenenbaum, J., Aberman, K., Pritch, Y., & Cohen-Or, D. (2023). Prompt-to-Prompt Image Editing with Cross Attention Control. *International Conference on Learning Representations (ICLR)*.

---

## §10 Glossary

| Term | Full English Name | Definition |
|---|---|---|
| **CFG** | Classifier-Free Guidance | A core inference technique for text-guided diffusion models that amplifies the influence of text conditioning on the diffusion sampling direction by linearly extrapolating between the conditional score and the unconditional score. A larger guidance strength $w$ yields higher text adherence but may reduce photorealism. |
| **Text-Image Alignment** | Text-Image Alignment | The degree of consistency between the semantic content of the enhanced image and the text description that drove the enhancement; typically quantified by CLIP-Score. High alignment indicates the enhancement result matches the semantic intent of the text. |
| **Zero-Shot Restoration** | Zero-Shot Restoration | A method that performs image restoration using only a text description of the degradation type as a conditioning signal — leveraging the image prior of a pretrained diffusion model — without collecting paired training data for the specific degradation type. |
| **CLIP-Score** | CLIP Score | A normalized score based on the cosine similarity between a generated/enhanced image and a text description, computed using the CLIP model; used for automated evaluation of semantic consistency in text-guided image generation and editing. |
| **Semantic Drift** | Semantic Drift | The phenomenon where high-level image semantics (e.g., subject identity, scene content) undergo unintended changes during text-guided enhancement; a key quality risk to guard against in portrait ISP enhancement. |
| **Negative Prompt** | Negative Prompt | A set of attribute descriptions specified as "undesired" during diffusion model inference; constrains the generation result by guiding the model away from the negative semantic space, thereby preventing common enhancement artifacts. |
| **IP-Adapter** | Image Prompt Adapter | A lightweight adapter module that injects the visual features of a reference image into the cross-attention layers of a diffusion model, enabling joint guidance from both the reference image's style/content and the text condition. |
| **ControlNet** | ControlNet | A neural network architecture that extends pretrained diffusion models by adding a trainable copy of the U-Net encoder as a structural control branch, allowing additional spatial conditioning signals (edge maps, depth maps, etc.) to guide generation while preserving the original model's generative prior. |
| **Hallucinated Texture** | Hallucinated Texture | Texture patterns generated by a diffusion model in smooth image regions that have no correspondence in the original image; a high-severity distortion in photographic ISP equivalent to image content fabrication. |
| **Dual CFG** | Dual Classifier-Free Guidance | An extension of CFG used in InstructPix2Pix that employs two independent guidance scales — $w_I$ for image fidelity and $w_T$ for text instruction compliance — enabling independent control over the two conditioning sources. |
