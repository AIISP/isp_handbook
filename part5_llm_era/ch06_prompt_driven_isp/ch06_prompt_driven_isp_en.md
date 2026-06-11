# Part 5, Chapter 06: Prompt-Driven ISP Parameter Generation

> **Position:** This chapter focuses on LLM-driven automatic ISP parameter generation and is the algorithmic deep-dive counterpart to Vol. 5 Ch. 03 (LLM-Assisted ISP Tuning). The emphasis is on end-to-end mapping methods from natural-language prompts to structured ISP parameters.
> **Prerequisites:** Vol. 5 Ch. 03 (LLM-Assisted ISP Tuning), Vol. 2 Ch. 05 (AWB), Vol. 2 Ch. 28 (ISP Calibration)
> **Audience:** Algorithm engineer, tuning engineer

> **Frontier content**: Based on 2025-2026 CVPR/ICCV/NeurIPS advances. Engineering deployment cases are actively expanding. Contributions welcome via [Issue](https://github.com/AIISP/isp_handbook/issues).

---

## §1 Theory

### Formal Representation of the ISP Parameter Space

The tunable parameter space of a modern mobile ISP (Image Signal Processor, 图像信号处理器) is far more complex than it appears on the surface. Taking the Qualcomm Snapdragon series as an example, the Chromatix XML configuration file for a single sensor often has more than several thousand parameter nodes. For ease of analysis, the core tuning parameter space can be defined as a vector across six dimensions:

$$\theta = \{G_{AWB}, M_{CCM}, L_{\gamma}, s_{sharp}, s_{NR}, s_{sat}\}$$

where:
- $G_{AWB} = (r_{gain}, b_{gain}) \in \mathbb{R}^2$: auto white balance (AWB, 自动白平衡) gain pair — typically the R gain ranges from ~1.2–2.8 and the B gain from ~1.1–2.5;
- $M_{CCM} \in \mathbb{R}^{3\times3}$: color correction matrix (CCM, 色彩校正矩阵), converting sensor RGB to the sRGB color space;
- $L_{\gamma}: [0,1] \to [0,1]$: gamma lookup table (LUT, 查找表), defining the luminance response curve, typically with 65 or 129 breakpoints;
- $s_{sharp} \in [0, 4]$: sharpness gain scalar (or per-band vector);
- $s_{NR} \in [0, 1]^{N_{ISO}}$: noise reduction (NR, 降噪) strength at each ISO point, typically with 8–16 control points from ISO 50 to ISO 6400;
- $s_{sat} \in [0.5, 2.0]$: global saturation multiplier, or a per-hue saturation vector in HSL space.

The core task of prompt-driven ISP parameter generation (提示词驱动参数生成) is to train or prompt a function:

$$f(P_{text}, I_{ref}) \to \hat{\theta}$$

where $P_{text}$ is a natural-language scene description (e.g., "outdoor midday sunlight scene, vibrant and saturated color style desired"), $I_{ref}$ is an optional reference image, and $\hat{\theta}$ is the generated ISP parameter vector.

### LLM as Parameter Regressor vs. LLM as Search Policy

From a system design perspective, the LLM plays two fundamentally different roles in ISP parameter generation:

**Role 1: Parameter Regressor (参数回归器)**

The LLM is treated as a function that directly maps text descriptions to parameter values. The input prompt is processed by the LLM's auto-regressive generation, which directly outputs parameter values in JSON format. This requires the LLM to internalize extensive prior knowledge of "scene type → parameter values," or to acquire this mapping through fine-tuning on (scene description, ISP parameters, quality score) triplets.

Advantages: fast inference — a single forward pass outputs the parameters. Disadvantages: poor generalization to out-of-distribution scenes, and unable to dynamically adapt to quality feedback.

**Role 2: Search Policy (搜索策略)**

The LLM is treated as a high-level decision-maker in parameter search. At each iteration, the LLM receives a quality description of the current image and the history of parameter trajectories, and outputs suggestions for the direction and magnitude of the next parameter adjustment. The actual parameter update is carried out by an independent optimizer (e.g., line search or Bayesian optimization); the LLM only provides the exploration direction.

Advantages: robust — even if the LLM's magnitude estimate is inaccurate, the external optimizer can correct it. Disadvantages: requires multiple ISP simulation iterations, resulting in higher inference latency.

### Chain-of-Thought ISP Reasoning

Chain-of-Thought (CoT, 思维链) prompting (Wei et al., NeurIPS 2022) yields significant gains for ISP parameter generation. Taking AWB tuning as an example, a CoT reasoning chain can be designed as follows:

1. **Scene analysis**: identify the primary light source type (D65 daylight, Type A tungsten, F11 fluorescent, etc.);
2. **Color temperature estimation**: estimate the scene color temperature (e.g., "outdoor midday is approximately 5500–6500 K");
3. **Color cast diagnosis**: analyze the expected color cast direction with current parameters (e.g., "default gains at this color temperature will produce a blue cast");
4. **Parameter derivation**: infer the adjustment direction for R/B gains based on the relationship between color temperature and default gains;
5. **Magnitude estimation**: estimate the adjustment magnitude based on the color temperature offset (e.g., "color temperature 200 K too high, R gain reduced by approximately 0.05");
6. **Output structured parameters**: generate the final JSON parameter object.

This step-by-step reasoning makes each decision step auditable by humans, greatly reducing hallucination (幻觉) risk — especially critical for parameter generation in key production environments.

### RAG-Augmented Parameter Retrieval Architecture

Retrieval-Augmented Generation (RAG, 检索增强生成) is another mainstream framework for prompt-driven parameter generation. The core idea is to build a large (scene description, ISP configuration) knowledge base, retrieve the most similar historical tuning cases during inference, and provide them as context to the LLM:

$$\hat{\theta} = \text{LLM}\left(P_{text}, \text{TopK-Retrieve}(P_{text}, \mathcal{D}_{params})\right)$$

where $\mathcal{D}_{params} = \{(P_i, \theta_i, q_i)\}_{i=1}^N$ is a database of triplets accumulated by human expert tuning, and $q_i$ is the corresponding quality score (e.g., CLIP-IQA value). The retriever typically uses CLIP or sentence-BERT text embeddings to compute cosine similarity.

The advantage of RAG over pure parameter regression is that knowledge can be incrementally updated (no retraining required), and the LLM can adaptively modify the retrieved cases through in-context reasoning (上下文内推理) to handle new scenes that differ from historical cases.

---

## §2 Methods

### RAG Parameter Retrieval Database Construction

Building a high-quality (scene description, ISP configuration) knowledge base is the core engineering work of the RAG approach. Recommended database structure:

```json
{
  "entry_id": "daylight_outdoor_v3",
  "scene_description": "Outdoor midday direct sunlight, blue sky with white clouds, green vegetation",
  "lighting_condition": "D65, 5800K",
  "sensor_platform": "Sony IMX766, Qualcomm ISP7",
  "isp_params": {
    "awb_gain_r": 1.42,
    "awb_gain_b": 1.68,
    "ccm": [[1.65, -0.38, -0.27], [-0.12, 1.43, -0.31], [0.08, -0.52, 1.44]],
    "gamma_lut": [0, 0.05, 0.14, 0.28, ...],
    "sharpness_gain": 1.8,
    "nr_strength_iso100": 0.35,
    "saturation_global": 1.15
  },
  "quality_scores": {
    "clip_iqa": 0.82,
    "niqe": 3.2,
    "delta_e_colorchecker": 2.1
  },
  "tags": ["outdoor", "daylight", "high_saturation", "landscape"]
}
```

Recommended database scale: cover at least 200 typical scene categories, with multiple quality levels per category (good / average / poor), totaling 1,000–5,000 entries. Retrieval uses a bi-encoder (双路编码器) model with joint embedding of scene descriptions and tags to support semantic similarity search.

### Fine-Tuning-Based End-to-End Parameter Generation

For applications requiring higher precision, supervised fine-tuning (SFT, 有监督微调) can be applied on top of a pretrained LLM (e.g., LLaMA-3, Qwen-2.5), with training data consisting of (scene description, expert tuning result) pairs.

Sample training format:

    <|user|>
    Scene: Indoor office, fluorescent lighting (4000K), close-up shot of a white office desk,
    target: accurate colors, no warm cast, moderate noise reduction.
    Sensor: Samsung GN5.
    Please generate ISP parameters (JSON format).

    <|assistant|>
    <thinking>
    Fluorescent light at 4000K color temperature, cool white tone. Need to slightly lower B gain
    and raise R gain to avoid a blue cast. White subject requires CCM to maintain color accuracy;
    saturation should not be too high. Noise reduction strength moderate.
    </thinking>
    {"awb_gain_r": 1.68, "awb_gain_b": 1.31, "saturation_global": 1.05,
     "sharpness_gain": 1.5, "nr_strength_iso400": 0.55, ...}

For fine-tuning, it is recommended to use LoRA (Low-Rank Adaptation, 低秩适配), training only ~0.1% of the parameters to avoid catastrophic forgetting (灾难性遗忘). A training data scale of 500–2,000 high-quality samples typically yields good generalization.

### Closed-Loop Evaluation: Simulated ISP Quality Feedback

A complete prompt-driven parameter generation system requires a closed-loop evaluation circuit. System architecture:

```
Text Prompt
    ↓
[LLM/RAG] → ISP Params (JSON)
    ↓
[ISP Simulator / Real ISP]
    ↓
Output Image
    ↓
[IQA Module: CLIP-IQA, NIQE, ΔE]
    ↓
Quality Score → Feedback to LLM (next iteration)
```

The ISP simulator can use LibISP, RawPy, or vendor-provided offline simulation tools (e.g., Qualcomm's Chromatix simulator). The quality scores output by the IQA module serve as reward signals that can be used for: (1) reinforcement learning fine-tuning (RLHF style), (2) online few-shot context updates, and (3) automatic selection of high-quality tuning cases to add to the RAG database.

---

## §3 Tuning

### Prompt Template Design for Qualcomm Chromatix XML

Qualcomm Chromatix is the mainstream framework for mobile ISP tuning; its XML configuration file has strict parameter naming conventions. Prompt templates targeting Chromatix XML generation must explicitly specify parameter paths in the output format:

```
System Prompt:
You are an ISP tuning expert specializing in Qualcomm Chromatix ISP parameters.
Output ONLY a valid JSON object with parameter paths matching Chromatix XML schema.
Do NOT invent parameter names. Use ONLY the following allowed parameters:
- awb_gain_r_d65, awb_gain_b_d65 (AWB gains for D65 illuminant)
- ccm_matrix_3x3 (3x3 color correction matrix, row-major)
- gamma_lut_129pt (129-point gamma LUT, values in [0, 1023])
- sharpness_gain_luma (luma channel sharpening gain, range [0, 4.0])
- nr_strength_iso[50/100/200/400/800/1600/3200/6400]

User Prompt Template:
Scene type: {scene_type}
Shooting conditions: lighting={lighting}, ISO={iso_range}, focal length={focal_length}
Target image quality style: {quality_target}
Reference color temperature: {color_temperature}K
Current baseline parameter quality issues (if any): {quality_issues}

Please generate the corresponding Chromatix ISP parameters (JSON format) and briefly
explain the tuning rationale for each major parameter.
```

Concrete tuning example — midday outdoor scene:

**Input prompt:**
"Generate AWB daylight gains for an outdoor midday scene containing blue sky, white clouds, and green vegetation, targeting natural and realistic colors."

**LLM output:**
```json
{
  "awb_gain_r_d65": 1.42,
  "awb_gain_b_d65": 1.71,
  "ccm_matrix_3x3": [[1.68, -0.41, -0.27], [-0.15, 1.48, -0.33], [0.05, -0.48, 1.43]],
  "gamma_lut_129pt": "standard_srgb_2.2",
  "sharpness_gain_luma": 1.7,
  "nr_strength_iso100": 0.30,
  "saturation_global": 1.10,
  "reasoning": "D65 daylight at ~5800K; R gain slightly lower than B gain to balance color temperature.
                CCM maintains standard sRGB gamut. Midday scene has ample light; conservative NR
                strength preserves fine texture detail."
}
```

### Output Format Validation: JSON → Chromatix Parameter Injection

LLM-generated JSON must pass strict validation before being injected into the ISP configuration. Recommended validation pipeline:

1. **Schema validation**: use JSON Schema to validate parameter name legality; reject any parameter keys not on the whitelist;
2. **Range constraint check**: perform physical plausibility boundary checks on each parameter (see §4);
3. **Matrix constraint**: each row of the CCM matrix should sum to ≈1.0 (luminance preservation), and diagonal elements should be positive;
4. **Auto-correction**: out-of-range parameters are automatically clipped to the nearest valid value, with correction logged;
5. **Chromatix XML generation**: use a template engine to convert the validated JSON into valid Chromatix XML nodes.

### Iterative Convergence Strategy

In closed-loop optimization, the following convergence control strategies are recommended:

- **Early stopping condition**: stop iteration when the CLIP-IQA score exceeds a threshold (e.g., 0.75) or Delta-E 2000 < 3.0;
- **Step-size decay**: multiply the LLM-suggested parameter increment by a decay factor $\alpha^t$ as the iteration count increases (recommended $\alpha = 0.85$), to prevent oscillation near the optimum;
- **History awareness**: include the parameters and quality scores from the most recent 3–5 iterations in the prompt to help the LLM sense convergence trends;
- **Rollback mechanism**: if the quality score drops by more than a threshold (e.g., 5%) after an iteration, automatically roll back to the last best parameter configuration.

### §3.1 Prompt-to-ISP Parameter Mapping Examples

The following presents six — extended to eight — concrete examples of typical prompt → ISP parameter mappings, covering common tuning scenarios including brightness, color, noise, contrast, and skin tone. Each case provides intent analysis and the specific ISP parameter adjustment direction, and can be used directly to build a RAG database or CoT prompt template.

| Prompt Example | Intent Analysis | Mapped ISP Parameters |
|---------------|----------------|----------------------|
| "Image is too dark, overall exposure is too low" | Underexposure; global brightness needs to be raised | AE target brightness +0.5 EV; gamma LUT shifted up overall (slope ×1.15); if already overexposed, prioritize AE adjustment over Gamma |
| "Colors look yellowish, white balance is off" | Color temperature too warm (low CCT value); correction toward cool needed | AWB color temperature −500 K; B/R gain ratio +0.12 (boost blue channel, reduce red channel); moderate suppression of warm tones in CCM |
| "Too much noise, image looks rough" | High noise level, NR strength insufficient | NR_Luma_Strength +30 (increase luma noise reduction); NR_Chroma_Strength +20 (increase chroma noise reduction); if ISO > 800, also trigger temporal NR |
| "Image looks gray, low contrast" | Low contrast; gamma curve too flat | S-curve gamma enhancement (midtone contrast +15%); Saturation +0.1 (slight boost to color vibrancy); black point reduced (Black Level −5 LSB) |
| "Skin color looks unnatural, overly orange-yellow" | Skin tone shift (red/orange direction oversaturated) | Fine-tune CCM in skin tone region (reduce red-channel cross gain); skin tone hue rotation −3° (shift toward pink); skin region saturation ×0.92 |
| "Overall image is too green" | Green color cast (green channel gain too high or CCM G-row too strong) | CCM matrix G-row diagonal −0.05 (reduce green response); AWB green channel gain ×0.95; check Bayer green channel gain imbalance (Gr/Gb imbalance) |
| "Night portrait has heavy noise but detail is also blurred" | NR vs. sharpness conflict at high ISO | Activate dedicated parameter group for ISO ≥ 3200: NR_Luma +40, NR_Chroma +35; simultaneously reduce Sharpness_gain from 1.8 to 1.2 (prevent noise from being amplified by sharpening); moderately relax NR within Face ROI to preserve skin texture |
| "HDR scene: highlights overexposed, shadows still too dark" | Insufficient dynamic range compression; tone mapping curve misconfigured | Enable local tone mapping (局部色调映射); reduce gamma slope on highlight side (prevent clipping); shift gamma up on shadow side +8%; review HDR merge weights (long/short exposure fusion ratio) |

**Usage notes:**

1. **Absolute parameter values vary by sensor**: the increments in the table above (e.g., +0.5 EV, +30 NR_Strength) are typical reference values; actual values must be calibrated according to the sensor's characterization curves and the ISP hardware's quantization step size.
2. **Parameter coupling relationships**: when multiple prompts are triggered simultaneously (e.g., "underexposed" and "noisy"), pay attention to parameter coupling — increasing brightness makes noise more visible, so NR strength should be raised in tandem.
3. **Scene-awareness priority**: in portrait scenes, skin tone protection takes precedence over global color adjustment; after the skin enhancement logic is triggered, global saturation adjustment should be applied with the skin region masked out.
4. **Quantization step constraints**: ISP hardware parameters are typically fixed-point numbers (e.g., NR_Strength is a 10-bit integer, AWB gain is Q4.12 fixed-point); floating-point values output by the LLM must be quantized and rounded, which can introduce ±1 LSB errors — increments should be designed in units of the step size when tuning.

---

## §4 Common Failure Modes

Prompt-driven ISP parameter generation encounters a class of failure modes unique to production deployment. Unlike traditional tuning failures (parameter out of range, sensor compatibility errors), LLM-introduced failures have two new characteristics: "linguistic ambiguity" and "model hallucination." The following systematically categorizes three major failure mode types and their mitigation strategies.

### 4.1 Prompt Ambiguity Leading to Wrong Parameter Direction

Natural language is inherently ambiguous; the same description may correspond to completely opposite parameter adjustment directions.

**Typical Case 1: "Enhance the colors"**

- **Ambiguity source**: can be interpreted as (a) increasing global saturation (larger saturation multiplier in HSL space); (b) switching to a wider color gamut (Wide Color Gamut, WCG) mode using P3 color space instead of sRGB; or (c) enhancing color contrast (stronger Color Tone Mapping).
- **Failure consequence**: if the LLM chooses path (a) (excessively boosting global saturation), skin regions will display overly vivid orange-red tones that look unnatural; if path (b) is chosen (switching to WCG), colors will appear oversaturated on displays that do not support P3.
- **Mitigation strategy**: in the system prompt, require the LLM to "confirm intent" before outputting parameters — output an intent-analysis paragraph, and have a human or downstream validation logic confirm the direction is correct before executing parameter injection.

**Typical Case 2: "Make the image sharper / clearer"**

- **Ambiguity source**: can be interpreted as (a) increasing sharpness gain (improving edge contrast); (b) reducing noise (reducing the visual "graininess," making the image look cleaner and clearer); or (c) improving focus accuracy (an AF-level concern that ISP cannot directly address).
- **Failure consequence**: if the LLM chooses path (a) (increasing sharpness) in a high-ISO noisy environment, noise is simultaneously amplified, resulting in an even less clear image.
- **Mitigation strategy**: add "current ISO" and "current estimated noise level" context to the prompt template to guide the LLM in distinguishing the root cause of poor clarity (insufficient sharpening vs. insufficient noise reduction).

**Typical Case 3: "Overall cinematic look and feel"**

- **Ambiguity source**: a cinematic style can map to multiple parameter adjustment directions, including: desaturation + enhanced local contrast (S-curve gamma), switching to a log gamma curve (Cinema LOG mode), adding vignetting, and adding grain simulation.
- **Failure consequence**: different LLM versions may interpret the parameters for "cinematic look" very differently, causing ISP parameters to jump discontinuously between product versions and resulting in poor product consistency.
- **Mitigation strategy**: for highly ambiguous style descriptions, force the LLM to select the best-matching template from a predefined "style template library" (enumerated type rather than open-ended generation), instead of freely generating parameter values.

### 4.2 Closed-Loop Feedback Not Converging

In a closed-loop optimization architecture, inconsistency between the problem described in the prompt and the actual change in image quality can cause the optimization process to oscillate or even diverge.

**Failure Scenario 1: Mismatch between the evaluation dimension and the tuning dimension**

The user feedback says "the image is still noisy," so the LLM continues to increase NR strength. However, the actual image quality problem is no longer random noise but ringing artifacts (振铃伪影) caused by excessive sharpening (which look similar to noise visually but have a completely different cause). Increasing NR strength has no effect on ringing and may even mask it by blurring overall detail, so the next round of feedback remains "unclear," forming a dead loop.

**Mitigation**: Introduce a dedicated artifact classifier (伪影分类器) in the closed loop to distinguish random noise, ringing, blur, color cast, and other failure types, preventing the LLM from attributing the cause of the problem based on vague natural-language descriptions.

**Failure Scenario 2: IQA metric not aligned with user perception**

The closed loop uses CLIP-IQA as the optimization target; the LLM continuously adjusts parameters to improve CLIP-IQA. However, CLIP-IQA is sensitive to semantic content, and certain parameter adjustments (e.g., excessively increasing contrast) may improve CLIP-IQA while producing highlight clipping that is perceptually objectionable. Optimization "converges" at the metric level but actually degrades perceptually.

**Mitigation**: Use multi-metric joint evaluation (see the IQA selection decision tree in §4.3), and set hard guardrails on SSIM and LPIPS to prevent single-metric optimization from degrading other dimensions.

**Failure Scenario 3: Parameter coupling causing a cyclic optimization path**

The LLM raises saturation in round 1 (because "colors are too pale"), lowers saturation in round 2 because of "skin tone too orange," then raises it again in round 3 because "overall colors are pale" — forming parameter oscillation (参数震荡).

**Mitigation**: Record the magnitude and direction of each parameter adjustment in the prompt history context. When the same parameter is detected to reverse direction in consecutive iterations, trigger step-size decay (halve the increment), forcibly shrinking the search radius.

### 4.3 Out-of-Range Issues

LLM-recommended parameter values exceeding the ISP hardware's quantization range are the most direct engineering failure.

**Hardware quantization range table (typical mobile ISP):**

| Parameter | Physical Range | Quantization Precision | Common LLM Out-of-Range Direction |
|-----------|---------------|----------------------|----------------------------------|
| AWB R/B Gain | [1.0, 3.5] | Q4.12 (16-bit fixed-point) | Generates "gain" < 1.0, causing reverse color cast |
| CCM diagonal elements | [0.5, 2.5] | Q2.10 | Generates high-contrast matrix > 3.0, causing color overflow |
| Gamma LUT values | [0, 1023] (10-bit) | Integer | Generates floating-point values (e.g., 1.8) instead of LUT indices — type mismatch |
| NR Luma/Chroma Strength | [0, 100] | 8-bit integer | Generates > 100 or negative values (negative values may be equivalent to maximum in some implementations) |
| Sharpness Gain | [0.0, 4.0] | Q2.8 | Generates > 4.0, causing ringing artifacts or hardware saturation clipping |
| Saturation Global | [0.5, 2.0] | Q1.8 | Generates > 2.5, causing severe color distortion |

**Trade-offs among out-of-range handling strategies:**

- **Direct clamping (Clamp)**: simplest, but may distort the intended parameter effect. For example, if the LLM expects extremely high NR strength (150) to eliminate noise entirely, clamping to 100 may not produce the expected result — and this intent gap is not recorded.
- **Normalized scaling (Normalize)**: normalize LLM absolute outputs to the hardware range, preserving the relative adjustment intent. For example, if one parameter among several exceeds its range, scale the entire parameter increment vector proportionally.
- **Reject and regenerate (Reject & Retry)**: feed the out-of-range information back to the LLM and request regeneration within the valid range. Advantage: the LLM may produce a more meaningful parameter correction. Disadvantage: adds one round of inference latency (~200–800 ms).
- **Production recommendation**: use clamping for minor out-of-range violations (exceeding range by < 10%); use reject-and-regenerate for severe violations (> 30% or type mismatch), and log the trigger frequency — if a particular parameter class violates bounds at a rate > 15%, update the range constraint description in the system prompt.

---

## §5 Artifacts

### Out-of-Range Parameter Values

The most common problem with LLM-generated ISP parameters is out-of-range values. Common dangerous values include:

**Gamma too large (> 2.8) causing highlight clipping (高光剪切)**:
When the generated gamma LUT slope is too steep, brightness values in bright regions overflow 255/1023, producing large areas of dead white (blown highlights). The LLM may aggressively push up gamma under a prompt of "enhance shadow detail" without realizing this simultaneously compresses highlights.

Constraint: the gamma LUT should be a monotonically non-decreasing function within the valid range $[0.7, 2.2]$, with fixed endpoints $L_\gamma(0)=0$, $L_\gamma(1)=1$.

**AWB gain too low (< 1.0)**:
When the LLM misjudges the color cast direction and generates $r_{gain} < 1.0$ or $b_{gain} < 1.0$, the image will develop a reverse color cast. Physically, a gain below 1.0 means truncation rather than amplification, which is unreasonable.

**NR strength out of range**:
When $s_{NR} > 1.0$, some ISP implementations produce undefined behavior, manifesting as global color blurring or blocking artifacts (块状伪影).

### Physically Inconsistent Parameter Combinations

Some parameter values that are individually valid can produce visual anomalies when used together:

**High CCM saturation + high NR strength → color bleed (色彩渗出)**:
Excessively high diagonal elements in the CCM (e.g., $M_{11} > 2.0$) amplify color transitions, while high NR strength blurs color boundaries. The combined effect causes vivid colors to "bleed" into adjacent regions, producing color fringing (彩色光晕) along the edges of highly saturated objects.

**High sharpness + low NR → noise amplification**:
Sharpening algorithms (e.g., Unsharp Masking) are fundamentally high-pass filters. When NR strength is insufficient to suppress underlying noise, sharpening also amplifies image noise, producing obvious high-frequency noise grain. For high-ISO scenes, the LLM should ensure $s_{sharp}$ and $s_{NR}$ satisfy an anti-correlation constraint.

**Mismatched illuminant between AWB and CCM**:
AWB gains calibrated for D65 combined with a CCM calibrated for illuminant A (tungsten), producing a double color-space shift that severely degrades color accuracy.

### Hallucinated Parameter Names

LLMs sometimes generate parameter names that do not exist in the ISP XML schema, for example:

```json
{"awb_auto_daylight_boost": 0.3,   // parameter name does not exist
 "ccm_perceptual_mode": "vivid",   // not a numeric parameter
 "nr_ai_enhance": true}            // boolean parameter not in standard Chromatix
```

Such hallucinations are silently ignored in systems without schema validation, causing the intended tuning to have no effect. Mitigation strategy: explicitly list all valid parameter names in the system prompt, and after each LLM output enforce schema validation (Schema验证) — logging illegal parameter names as errors and feeding them back to the LLM with a request to regenerate.

---

## §6 Evaluation

### Parameter Accuracy Evaluation: Comparison with Expert Baseline

Evaluating the quality of LLM-generated parameters requires comparing them against a human expert tuning baseline (ground truth) on standard test scenes:

**Color accuracy (颜色准确度)**:
Use a ColorChecker SG (140 color patches) to photograph a standard color chart under the target illumination conditions and compute the CIE Delta-E 2000 values for LLM tuning vs. expert tuning. Target: average ΔE 2000 < 4.0 for LLM tuning (expert tuning typically < 2.5).

**Signal-to-noise ratio (SNR, 信噪比)**:
Photograph a uniform gray patch (18% gray) and compare the per-ISO SNR of LLM tuning vs. expert tuning. Target: SNR difference between LLM tuning and expert baseline < 1 dB.

**Modulation transfer function (MTF, 调制传递函数)**:
Use an ISO 12233 test chart to evaluate sharpness and compare the MTF50 (cycles/mm) of LLM tuning vs. expert tuning. Confirm that LLM-generated sharpness parameters do not introduce oversharpening artifacts.

### Blind Evaluation: User Preference Test

The ultimate quality standard is subjective user preference. Recommended blind evaluation procedure:

1. Photograph 10 test images in each of 20 typical scene categories (outdoor daylight, indoor, night, portrait, landscape, etc.);
2. Process the same RAW file with LLM-generated parameters and expert tuning parameters respectively;
3. Randomly present paired images to evaluators in A/B format without revealing which is LLM-generated;
4. Record preference rates and scores on individual quality dimensions (color, noise, sharpness, overall impression);
5. Report preference rates and 95% confidence intervals (95% CI) for LLM tuning vs. expert tuning across different scene categories.

Expected results: for scenes under typical illumination conditions (D65, D50), LLM tuning preference rates of approximately 40–55% (approaching expert level); for extreme illumination (low color temperature tungsten, mixed light sources) or high dynamic range scenes, expert tuning still holds a clear advantage.

### Generalization to Unseen Scenes

Generalization capability is one of the core advantages of the prompt-driven approach. Evaluation plan:

1. Divide test scenes into training-set scene categories (seen) and test-set scene categories (unseen, e.g., underwater photography, medical endoscopy, automotive night vision);
2. On unseen scenes compare: (a) zero-shot LLM generation, (b) RAG retrieval adaptation, (c) 5–20 sample fine-tuning, (d) expert tuning baseline;
3. Plot a sample efficiency curve (few-shot adaptation curve, 少样本适配曲线): x-axis = number of adaptation samples (0, 5, 10, 20, 50, 100), y-axis = CLIP-IQA score.

---

## §7 Code

The companion notebook *See §6 Code section for runnable examples.* implements a complete prompt-driven ISP parameter generation demonstration pipeline:

**Module 1: ISP Parameter Space Definition and Simulator Interface**
Defines the ISP parameter dictionary structure (AWB gains, 3×3 CCM matrix, gamma LUT, sharpness, noise reduction, saturation) and implements a lightweight Python ISP simulator that applies parameters to a synthetic RAW image (Bayer format) and generates an RGB output.

**Module 2: LLM Parameter Generation Interface**
Calls the chat interface of LLaMA-3 (via Ollama local deployment) or Qwen-2.5-7B (via the `transformers` library), passing scene description prompts, parsing the output JSON, and extracting ISP parameters. Demonstrates two prompting strategies: standard prompting (direct parameter generation) and chain-of-thought prompting (step-by-step reasoning followed by parameter generation).

**Module 3: Parameter Validation and Correction**
Implements complete schema validation logic: parameter name whitelist checking, physical boundary constraints (AWB gain [1.0, 3.5], CCM row-sum constraint, gamma monotonicity check), automatic out-of-range correction. Demonstrates the process of hallucinated parameter names being detected and handled.

**Module 4: RAG Retrieval Demo**
Builds a small example database of 50 tuning cases, uses sentence-transformers to compute scene description embeddings, and demonstrates Top-3 retrieval and LLM adaptive generation. Compares the quality of RAG-generated parameters versus zero-shot-generated parameters (via NIQE and CLIP-IQA scores).

**Module 5: Closed-Loop Optimization Demo**
Over 5 iterations of closed-loop optimization, demonstrates the parameter convergence process: LLM generates parameters → ISP simulation → IQA scoring → feedback to LLM → next iteration. Plots the per-iteration CLIP-IQA score and ΔE value change curves, demonstrating convergence characteristics.

**Module 6: Failure Case Analysis**
Demonstrates typical parameter generation failure cases: gamma out-of-range causing highlight clipping, the combined artifact from overly high CCM saturation combined with overly high NR strength, hallucinated parameter names — and the corresponding detection and correction mechanisms.

---

## References

[1] He, J., et al. (2024). *CameraCtrl: Enabling Camera Controllability for Text-to-Video Diffusion Models*. arXiv:2404.02101. (Related work on natural-language control of imaging parameters)

[2] Liang, J., et al. (2024). *LLM-Tuner: Leveraging LLMs for Parameter-Efficient Fine-Tuning of Image Restoration Models*. arXiv:2402.09157. (LLM-assisted image restoration parameter adjustment)

[3] Qualcomm Technologies, Inc. (2023). *Qualcomm Camera HAL Interface (CHI-CDK) Developer Guide — Chromatix Tuning Parameters*. Qualcomm Developer Network. (Chromatix XML parameter specification)

[4] Wei, J., et al. (2022). *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*. NeurIPS 2022. arXiv:2201.11903.

[5] Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS 2020. arXiv:2005.11401.

[6] Brown, T., et al. (2020). *Language Models are Few-Shot Learners* (GPT-3). NeurIPS 2020. arXiv:2005.14165.

[7] Fang, Y., et al. (2023). *CLIP-IQA+: Exploring CLIP for Assessing the Look and Feel of Images*. IEEE TPAMI 2023.

[8] Yang, Q., et al. (2023). *MoE-LLaVA: Mixture of Experts for Large Vision-Language Models*. arXiv:2401.15947.

[9] Hu, E., et al. (2022). *LoRA: Low-Rank Adaptation of Large Language Models*. ICLR 2022. arXiv:2106.09685.

---

## §8 Glossary

| Term | Full Name | Explanation |
|------|-----------|-------------|
| RAG | Retrieval-Augmented Generation | Combines retrieval from a pre-built knowledge database with LLM generation to improve the factual accuracy and domain relevance of outputs; knowledge can be incrementally updated without retraining. |
| Chromatix | Qualcomm Chromatix | Qualcomm Snapdragon ISP's parameter tuning framework; stores sensor-specific ISP parameter configurations in XML format, covering full-pipeline modules including AWB, CCM, NR, and sharpening. |
| Parameter Space | Parameter Space (参数空间) | The high-dimensional vector space formed by all tunable ISP parameters; the dimensionality of a typical mobile ISP parameter space ranges from tens (core parameters) to thousands (full Chromatix parameters). |
| Chain-of-Thought | Chain-of-Thought (CoT, 思维链) | A prompting technique that guides the LLM to show its reasoning process step by step within the prompt, improving accuracy on complex reasoning tasks and reducing hallucination. |
| Hallucination | Hallucination (幻觉) | Content generated by an LLM that is linguistically fluent but factually incorrect; in ISP parameter generation, manifests as generating nonexistent parameter names or physically unreasonable parameter values. |
| LoRA | Low-Rank Adaptation (低秩适配) | A parameter-efficient fine-tuning technique that injects low-rank decomposition matrices into the weight matrices of a pretrained model, achieving domain adaptation with only ~0.1% of the total parameter count as trainable parameters. |
| Delta-E (ΔE) | CIE Delta-E 2000 | The CIE color difference metric; quantifies the perceptual difference between two colors in the uniform color space (CIELAB). ΔE < 1.0 is imperceptible to the human eye; ΔE < 3.0 is an acceptable color-tuning accuracy target. |
| MTF | Modulation Transfer Function (调制传递函数) | Describes the imaging system's ability to reproduce detail at different spatial frequencies; MTF50 denotes the spatial frequency at which the contrast drops to 50%. |
| Parameter Oscillation | Parameter Oscillation (参数震荡) | A closed-loop optimization failure mode in which the same parameter alternates between positive and negative adjustments across consecutive iterations without converging stably; typically caused by prompt ambiguity or parameter coupling relationships not being correctly modeled by the LLM. |
| Schema Validation | Schema Validation (Schema验证) | Structural legality check of LLM-output JSON, including parameter name whitelist, data type matching, and physical range constraints; the critical defense layer against hallucinated parameters being injected into the ISP. |
| Artifact Classifier | Artifact Classifier (伪影分类器) | A lightweight classification network dedicated to identifying image degradation types (random noise / ringing / blur / color cast), used in closed-loop IQA to precisely locate failure types and prevent the LLM from incorrectly attributing the root cause of quality problems. |
| Few-Shot Adaptation | Few-Shot Adaptation (少样本适配) | The capability to rapidly adapt an LLM or RAG system to a new scene type (e.g., underwater photography, automotive night vision) given only a small number (5–20) of annotated target-scene samples. |

---

## §9 Engineering Practice Checklist

The following checklist is intended for engineering acceptance testing before deploying a prompt-driven ISP parameter generation system, ensuring stable operation in production environments.

### 9.1 Pre-Launch Acceptance Items

**LLM side:**
- [ ] System prompt includes a complete parameter name whitelist (all valid Chromatix parameter names)
- [ ] System prompt includes the physical range constraint and data type description for each parameter
- [ ] CoT reasoning mode and direct generation mode have been tested; CoT confirmed to be more accurate in critical scenes (mixed light sources, extreme exposure)
- [ ] Hallucinated parameter name detection rate > 99% (validated on 100 test samples)

**RAG side:**
- [ ] Database covers at least 200 independent scene categories (three-dimensional coverage: lighting condition × subject × ISO level)
- [ ] Top-1 retrieval accuracy on validation set > 70% (Top-3 coverage > 90%)
- [ ] Quality score (CLIP-IQA) distribution of database entries covers high / medium / low tiers (each ≥ 20%)

**Validation pipeline side:**
- [ ] Schema validation interception rate (out-of-range / hallucinated parameters) under stress testing < 5% (a higher rate indicates the system prompt needs optimization)
- [ ] Parameter clamping log is persisted for statistical analysis of high-frequency out-of-range parameters (to guide prompt iteration)
- [ ] Severe out-of-range (> 30%) regeneration trigger latency verified acceptable (< 1.5 seconds)

**Closed-loop optimization side:**
- [ ] Convergence curve reaches target IQA threshold within an average of 5 iterations on the standard test scene set (20 scenes)
- [ ] Parameter oscillation detection logic validated (step-size decay activates when the same parameter reverses direction in 2 consecutive rounds)
- [ ] Rollback mechanism stress-tested (rollback triggered correctly when quality drops > 5%; rollback success rate = 100%)

### 9.2 Quick Reference Cards for Typical Tuning Scenarios

The following quick-reference cards summarize prompt templates and expected parameter directions for the most common tuning scenarios, for engineers to consult rapidly:

**Outdoor daylight scene (D65, 5500–6500 K)**
- Prompt keywords: "outdoor," "daylight," "blue sky"
- Parameter direction: R gain slightly lower than B gain; CCM maintains standard sRGB; gamma standard 2.2; moderate sharpness (1.5–2.0)
- Risk: watch for noise in shadow regions; increase NR when ISO > 200

**Indoor fluorescent scene (F11, 4000 K)**
- Prompt keywords: "indoor," "office," "fluorescent"
- Parameter direction: R gain slightly higher, B gain slightly lower (relative to D65); CCM needs re-calibration for F11; saturation should not be too high
- Risk: fluorescent lights flicker; avoid row-frame aliasing (Anti-Banding must be configured in tandem)

**Night / low-light scene (ISO 1600–6400)**
- Prompt keywords: "night," "low light," "noisy"
- Parameter direction: NR_Luma 60–80, NR_Chroma 50–70; sharpness reduced to 1.0–1.3; gamma shadow side raised; trigger multi-frame NR if available
- Risk: excessive NR causes loss of fine detail (LPIPS degrades); manual review of hair and text regions required

**Backlit / HDR scene**
- Prompt keywords: "backlit," "HDR," "highlights overexposed"
- Parameter direction: enable local tone mapping; highlight-side gamma slope ×0.7; shadow side raised; HDR merge weight long exposure > short exposure
- Risk: HDR merge ghost artifacts (Ghost Artifact); verify that the motion detection module is simultaneously active

**Portrait scene**
- Prompt keywords: "portrait," "face," "skin," "beautification"
- Parameter direction: trigger Face ROI-aware AE/AWB; skin region NR relaxed (preserves texture); skin tone hue shifted toward pink; face-aware sharpening (moderate background blur)
- Risk: over-beautification causes plastic skin appearance (LPIPS degrades in face region); skin protection conflicts with global CCM
