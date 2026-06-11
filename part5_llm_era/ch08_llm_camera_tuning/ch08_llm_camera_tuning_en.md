# Part 5, Chapter 08: LLM-Driven Automated Camera System Tuning

> **Frontier content**: Based on 2025-2026 CVPR/ICCV/NeurIPS advances. Engineering deployment cases are actively expanding. Contributions welcome via [Issue](https://github.com/AIISP/isp_handbook/issues).

> **This chapter is the upgrade of Vol. 5 Ch. 03.** Ch. 03 introduces LLM as a **knowledge base** — retrieving semantic recommendations for parameter adjustment direction (engineer-led, single-round). This chapter upgrades the paradigm to an **autonomous Agent with sequential decision-making** — the LLM acts as the core controller, reads IQA feedback through tool calls, modifies ISP config files, triggers captures, and iteratively optimizes through a multi-step Markov Decision Process (MDP) until quality metrics converge.
>
> | Capability | Ch. 03 (Knowledge-base assisted) | This chapter (Agent sequential decision) |
> |------------|----------------------------------|------------------------------------------|
> | LLM role | Parameter recommendation engine | Autonomous decision controller |
> | Decision paradigm | Single or few-round interaction | Multi-step MDP, closed-loop iteration |
> | Human involvement | Engineer-led, LLM assists | Fully automatic; humans review final result |
> | Action interface | Text output (JSON delta) | Tool calls (write registers / trigger capture / read IQA) |
> | Convergence guarantee | None | Verifiable convergence via IQA reward signal |
>
> Recommended reading path: Read Ch. 03 first to understand LLM parameter-semantic comprehension, then read this chapter to see how that capability is upgraded into a fully autonomous tuning Agent.

> **Position:** This chapter reframes the ISP camera tuning problem as a sequential decision-making process, introduces an automated tuning system architecture in which an LLM serves as the core Agent, IQA (Image Quality Assessment, 图像质量评估) scores serve as reward signals, and tool calls serve as the action interface, and details the engineering path to deployment on Qualcomm/MTK platforms.
> **Prerequisites:** Vol. 5 Ch. 03 (LLM-Assisted ISP Tuning), Vol. 4 Ch. 17 (ISP Tuning Workflow)
> **Audience:** Tuning engineers, algorithm engineers

---

## §1 Theory

### 1.1 The Nature of Camera Tuning

The parameter space of a modern mobile-platform ISP (Image Signal Processor, 图像信号处理器) is enormous. Taking the Qualcomm Snapdragon ISP (Spectra) as an example, a Chromatix (高通ISP平台参数配置格式) XML configuration file typically contains hundreds of floating-point parameters distributed across the following modules:

- **BLC/PDPC**: black-level offset, bad-pixel correction thresholds (~10–20 parameters)
- **LSC (Lens Shading Correction, 镜头阴影校正)**: per-channel mesh gains (R/GR/GB/B each at 32×24 nodes, ~3,000 parameters)
- **AWB (Auto White Balance, 自动白平衡)**: CCT decision range, R/B gains per illuminant (~50–100 parameters)
- **CCM (Color Correction Matrix, 色彩校正矩阵)**: 3×3 matrix coefficients × multiple illuminants × multiple ISOs (~200 parameters)
- **Denoising (NR, 降噪)**: Luma/Chroma NR strength at each ISO point, flat-region/texture-region differentiation factors (~100–200 parameters)
- **Sharpening (锐化)**: USM (Unsharp Masking, 反锐化掩模) gain per frequency band, overshoot-suppression threshold (~50 parameters)
- **Tone Mapping/Gamma (色调映射/伽马)**: curve control points, local tone mapping (LTM, 局部色调映射) strength (~30–50 parameters)

Taken together, the *effective degrees of freedom* of a complete ISP configuration file easily exceed 500. Traditionally, this work is performed manually by an Imaging Scientist (成像科学家) following this process:

1. **Capture**: shoot test images in standard scenes (ISO gray card, X-Rite ColorChecker, low-light scene)
2. **Evaluate**: visual inspection + tool-aided analysis (color error ΔE, SNR, MTF curves)
3. **Adjust**: map perceived problems to specific parameter deltas based on experience (e.g., "shadow appears green → CCM blue channel +0.02")
4. **Iterate**: repeat the capture–evaluate–adjust loop until all metrics are within target

This cycle typically requires **2–4 weeks** for a new sensor and is heavily dependent on individual engineering expertise.

### 1.2 Modeling Tuning as Sequential Decision-Making

Formally, ISP tuning is highly isomorphic to the sequential decision-making problem in Reinforcement Learning (RL, 强化学习):

- **State** $s_t$: the current ISP parameter vector $\theta_t \in \mathbb{R}^D$ (D on the order of a few hundred) plus the current IQA metric vector $q_t \in \mathbb{R}^M$
- **Action** $a_t$: parameter delta $\Delta\theta_t$, typically adjusting only a small subset of parameters (sparse action)
- **Reward** $r_t$: IQA improvement $r_t = \sum_i w_i \cdot (q_{t+1,i} - q_{t,i})$
- **Policy** $\pi$: given state $s_t$, output action $a_t$

Formally:

$$\pi^* = \arg\max_\pi \mathbb{E}\left[\sum_{t=0}^{T} \gamma^t r_t\right]$$

where $\gamma$ is the discount factor and $T$ is the maximum number of iterations (typically set to 10–20 to control compute cost).

The key distinction from standard RL is: **the LLM serves as the policy function**. The LLM's input is a natural-language description of the current state (IQA scores, histogram statistics, perceptual problem descriptions), and its output is a structured parameter-delta JSON. The prior knowledge accumulated during large-scale pretraining on camera/photography/ISP corpora allows the LLM to propose reasonable initial actions without exploring from scratch — equivalent to an "expert prior" (专家先验) initialization of the policy in RL.

### 1.3 Core Assumptions Behind LLM-as-Tuning-Agent

The theoretical basis for LLM-driven tuning lies in the **implicit causal knowledge** (隐式因果知识) absorbed during training:

- "Parameter–effect" descriptions from camera manuals and tuning documents
- Image quality discussions on photography forums ("overexposed → reduce EV", "color cast → adjust white balance")
- Q&A in ISP developer communities

This implicit knowledge enables the LLM to map perceptual quality descriptions to parameter adjustment recommendations without backpropagation. Note that LLM recommendations are **directional suggestions** (方向性建议) (which parameter to adjust, in which direction); the magnitude precision typically requires further calibration using sensor-specific data.

---

## §2 Reinforcement Learning Approach

### 2.1 State and Action Space Design

**State representation**: the ISP tuning state $s_t$ is designed as a multi-dimensional vector with the following components:

$$s_t = \left[\theta_t^{\text{norm}},\; q_t^{\text{IQA}},\; h_t^{\text{hist}},\; c_t^{\text{context}}\right]$$

- $\theta_t^{\text{norm}}$: normalized ISP parameter vector (each parameter normalized to [0, 1])
- $q_t^{\text{IQA}}$: IQA metric vector, including BRISQUE, NRQM, CLIP-IQA scores, etc.
- $h_t^{\text{hist}}$: image histogram statistics (mean, variance, highlight fraction, shadow fraction for luminance/R/G/B channels)
- $c_t^{\text{context}}$: scene context (illuminant type, scene category, ISO value, etc.)

**Action space**: to avoid the exploration difficulties of a continuous high-dimensional action space, actions are discretized into a set of typical operations:

| Action type | Example | Parameter scope |
|---|---|---|
| AWB gain fine-tuning | R_gain += 0.05 | Global color temperature |
| CCM saturation adjustment | saturation_hue_range += 0.02 | Specific hue range |
| NR strength adjustment | luma_nr_iso1600 += 0.1 | Specific ISO point |
| Gamma curve adjustment | gamma_toe_y += 0.01 | Shadow region |
| Sharpening gain adjustment | sharpening_gain_hf -= 0.05 | High-frequency edges |

**Reward function**: a weighted combination of multiple IQA metrics:

$$r_t = w_1 \cdot \Delta\text{BRISQUE} + w_2 \cdot \Delta\text{NRQM} + w_3 \cdot \Delta\text{CLIP-IQA} + w_4 \cdot \Delta\text{SNR} + w_5 \cdot (-\Delta\text{ΔE})$$

BRISQUE is lower-is-better (negated), NRQM and CLIP-IQA are higher-is-better, SNR is higher-is-better, and color error ΔE is lower-is-better.

### 2.2 Parameter Optimization via LLM Policy

Unlike traditional gradient-based methods (such as the end-to-end differentiable ISP in CameraIQ Neural), the LLM policy is a **non-parametric, gradient-free** optimization approach.

**Limitations of gradient methods**:
- Require differentiable ISP modules; real hardware ISPs are not differentiable
- Require large annotated data pairs (RAW input, sRGB target)
- Optimize pixel-level losses (L1/L2/LPIPS), making it difficult to directly optimize perceptual IQA
- Different sensors require retraining

**Advantages of the LLM policy**:
- No gradients; driven directly by natural-language IQA evaluations
- Leverages ISP domain knowledge accumulated during pretraining, reducing the number of exploration steps
- Interpretable: each action step is backed by natural-language reasoning
- Cross-sensor transfer: only the sensor documentation needs to be swapped out

Formally, the LLM policy can be interpreted as a behavior-cloning initialization within Proximal Policy Optimization (PPO, 近端策略优化):

$$\pi_{\text{LLM}}(a_t \mid s_t) \approx \pi_{\text{expert}}(a_t \mid s_t) \cdot \exp\left(\frac{1}{\beta} A_t\right)$$

where $A_t$ is the advantage function (improvement of the current action over the average policy) and $\beta$ is the temperature parameter controlling how far the policy deviates from the prior.

### 2.3 Comparison with Gradient-Based Methods

| Dimension | Gradient methods (CameraIQ Neural, etc.) | LLM policy method |
|---|---|---|
| Differentiability requirement | Requires differentiable ISP | Not required |
| Data requirements | Large RAW–sRGB pairs | A small number of IQA annotations |
| Optimization objective | Pixel-level loss | Perceptual IQA |
| Cross-sensor generalization | Requires retraining | Prompt engineering adaptation |
| Interpretability | Low (black-box gradients) | High (natural-language reasoning) |
| Tuning speed | Fast (offline batch optimization) | Slower (stepwise iteration) |
| Engineering deployment | Requires training infrastructure | Only needs LLM API |

---

## §3 LLM Agent Architecture

### 3.1 Applying the ReAct Framework to ISP Tuning

ReAct (Reasoning + Acting; Yao et al., ICLR 2023) is currently the most widely used control framework for LLM agents. Its core idea is to interleave reasoning (Thought) and action (Action), forming an observable and auditable decision loop:

```
Thought: [natural-language reasoning about the current state and next action]
Action: [tool call to execute the action]
Observation: [result returned by the tool]
Thought: [reasoning based on the observation]
Action: [next action]
...
```

A typical ReAct trajectory in the ISP tuning scenario follows this pattern:

**Trajectory example: night indoor scene tuning**

```
Observation: Current IQA — BRISQUE=48.2 (target<30), CLIP-IQA=0.51 (target>0.75)
             Image histogram: shadow region mean=35/255 (underexposed)

Thought: The image is globally underexposed; shadow-region detail is lost. The elevated
         BRISQUE score may be caused by over-compressed shadow details due to aggressive NR.
         The first step should be to raise the Gamma toe to improve shadow brightness,
         then observe whether NR needs to be rebalanced.

Action: adjust_params({"gamma_toe_y": +0.015, "gamma_toe_x": +0.005})

Observation: BRISQUE=41.3, CLIP-IQA=0.58
             Shadow region mean=52/255 (improved)
             But: highlight region shows mild clipping (>250/255 share rose from 2% to 8%)

Thought: Shadow improvement is effective, but lifting the Gamma toe caused mild highlight
         clipping. A highlight rolloff needs to be added while preserving the shadow lift.

Action: adjust_params({"gamma_highlight_rolloff": -0.02})

Observation: BRISQUE=33.7, CLIP-IQA=0.68
             Highlight clipping ratio: 2.5% (acceptable)

Thought: Metrics continue to improve. BRISQUE is approaching the target; CLIP-IQA still
         has room to improve. Analyzing color: current AWB color temperature is warm;
         the blue channel is insufficient for this indoor incandescent scene.

Action: evaluate_iqa(image, mode="color_accuracy")

Observation: ΔE=5.2 (target<3.0), blue channel deficiency detected

Action: adjust_params({"awb_gain_b": +0.08})

Observation: BRISQUE=31.2, CLIP-IQA=0.74, ΔE=2.8
             All metrics within target range. Convergence achieved.

Thought: All metrics are within the target range. Tuning has converged. Recording final
         parameter deltas.
Action: commit_params()
```

### 3.2 Tool Definitions (Tool Use)

The LLM Agent interacts with the ISP system through structured tool calls. The core tool set is defined as follows:

| Tool name | Input | Output | Description |
|---|---|---|---|
| `capture_image(params)` | ISP parameter JSON | Image file path | Capture one frame with the specified parameters |
| `evaluate_iqa(image, mode)` | Image path + evaluation mode | IQA metric JSON | Compute BRISQUE/NRQM/CLIP-IQA, etc. |
| `get_histogram(image, channel)` | Image path + channel name | Histogram data | Retrieve luminance/R/G/B histogram statistics |
| `adjust_params(delta_json)` | Parameter delta JSON | New parameter state | Apply parameter adjustments; supports rollback |
| `rollback_params(n_steps)` | Number of steps to roll back | Parameter state | Roll back to the state n steps earlier |
| `commit_params()` | None | Final parameter file | Save current parameters as the final configuration |
| `get_module_description(module)` | Module name | Parameter documentation | Return documentation for the specified ISP module |

Tools are defined in OpenAI Function Calling or LangChain Tool format, enabling the LLM to generate correctly formatted tool-call JSON.

### 3.3 Multimodal LLM Enhancement

Vision-Language Models (VLMs, 视觉语言模型) such as GPT-4V and Claude 3 Vision can process image inputs directly, without relying on the numerical output of IQA tools. A VLM-enhanced agent architecture feeds images directly into the LLM, yielding finer-grained perceptual analysis:

- "There is vignetting in the upper-left corner; luminance uniformity is insufficient — check LSC configuration."
- "Facial skin tones appear yellow; CCM saturation is too high under D50 illuminant."
- "Worm-like artifacts appear on distant foliage textures, possibly caused by over-sharpening."

The semantic descriptions provided by the VLM complement the numerical IQA tools, forming a more complete state observation.

---

## §4 Platform Integration

### 4.1 Qualcomm CIQT Python API Integration

The Qualcomm Camera IQ Tuning Tool (CIQT) is the official tuning tool for the Snapdragon platform and supports a Python scripting interface. An automated tuning agent can integrate with CIQT in the following way:

**Chromatix XML differential patching**: the parameter-delta JSON output by the LLM Agent can be parsed into a differential patch for Chromatix XML. For example:

```
// LLM-output parameter delta
{"awb_gain_r": 1.72, "awb_gain_b": 1.58, "ccm_matrix_d65": [[1.8, -0.5, -0.3], ...]}

// Converted to Chromatix XML patch
<chromatix_awb_parameters>
  <awb_gain_r>1.72</awb_gain_r>
  <awb_gain_b>1.58</awb_gain_b>
</chromatix_awb_parameters>
```

The CIQT Python API can load the updated Chromatix file in the background and trigger a new capture, completing the entire loop without manual intervention.

**Automated capture workflow**:
1. Agent calls `capture_image()` → CIQT API triggers test image capture
2. Image is saved to a local path
3. Agent calls `evaluate_iqa()` → IQA tool analyzes the image
4. Agent generates a parameter delta → CIQT API updates the Chromatix XML
5. Loop until convergence or maximum iteration count is reached

### 4.2 MTK Camera Tool Automation

The MediaTek (联发科) camera platform uses the Camera Tool (CT) for parameter adjustment. The MTK Camera Tool provides an ADB (Android Debug Bridge, Android调试桥) interface that can be invoked via scripts:

```
# Example: push new parameter file via ADB and trigger hot reload
adb push new_params.json /data/vendor/camera/tuning/
adb shell "am broadcast -a com.mtk.camera.RELOAD_TUNING"
```

The tool layer of the LLM Agent wraps the above ADB commands, mapping parameter adjustment actions to concrete platform operations. The MTK platform also supports JSON-format parameter files, making it straightforward for the LLM to generate the target format directly.

### 4.3 CI/CD Automated Tuning Pipeline

An industrial-grade automated tuning system needs to be embedded in a CI/CD (Continuous Integration/Continuous Delivery, 持续集成/持续交付) pipeline:

**Nightly automated tuning runs**:
- Trigger: new firmware version merged → automated tuning job triggered
- Agent executes a tuning loop on the standard test scene set (ISO card, ColorChecker, low-light, portrait)
- Tuning results are automatically committed to the parameter version repository

**Regression testing**:
- After each parameter update, automatically compare against the baseline parameters
- Generate a metric comparison report (BRISQUE, ΔE, SNR comparisons)
- If any scene's metric degrades beyond a threshold (e.g., BRISQUE rises by more than 5%), automatically roll back and alert

**Manual review gate**:
- After the automated tuning results pass, generate a tuning report and send it to imaging engineers
- Engineers manually trigger final release after review
- Critical parameter changes (e.g., large adjustments to the CCM matrix) require mandatory dual review

**Typical pipeline architecture**:

```
Git Push (firmware/params)
  → CI trigger
  → Test device attachment (real device or Simulator)
  → LLM tuning Agent runs (10-20 iteration steps)
  → IQA regression comparison
  → Report generation
  → Manual review
  → Parameters merged to main repository
```

---

## §5 Artifacts (典型问题)

### 5.1 IQA Metric Overfitting

The LLM Agent optimizes numerical IQA metrics (BRISQUE, NRQM, etc.), but these metrics do not always align perfectly with human perception. Typical symptoms:

- **Low BRISQUE score but unnatural-looking image**: aggressively smooth NR settings can lower BRISQUE (eliminating textures misidentified as noise) while simultaneously destroying genuine detail.
- **High CLIP-IQA score but color distortion**: boosting saturation can raise CLIP-IQA scores for "vibrant" scenes, but causes over-saturated skin tones.
- **Good SNR metric but poor dynamic perception**: excessive noise suppression makes images appear to lack realism and tonal gradation.

**Mitigation strategies**:
- Use multi-metric constrained optimization, preventing one metric from improving at the expense of others
- Introduce human perceptual ratings (Mean Opinion Score, MOS, 平均主观评分) as the final validation
- Set parameter change magnitude constraints (maximum delta per step)

### 5.2 Infinite Loops Caused by Parameter Constraint Conflicts

ISP parameters have complex mutual dependencies; some adjustment directions are mutually contradictory and may cause the Agent to fall into a loop:

**Typical scenario**:
- Increase sharpening gain → high-frequency noise increases → IQA demands higher NR strength → NR suppresses detail → IQA demands lower NR → noise increases → loop

**Detection and termination**:
- Parameter state hash tracking: if the current parameter state matches a previous step, declare a loop and force termination
- Action–effect history analysis: the LLM analyzes the historical trajectory in the Thought step to identify periodic patterns
- Hard constraint on maximum number of iterations

### 5.3 Cross-Illumination Parameter Drift

Parameters optimized for a daytime outdoor scene may degrade significantly under nighttime indoor conditions. Parameters at which the LLM Agent converges in a single scene often lack robustness across different illumination conditions.

**Solutions**:
- **Multi-scene joint tuning**: optimize a weighted sum of IQA scores across multiple test scene sets simultaneously
- **Scene-conditioned parameter separation**: use independent parameter tables under different illumination/ISO conditions (the ISP itself supports per-ISO-point interpolation)
- **Regularization constraint**: add an L2 regularization term to penalize deviation from factory-default values, preventing extreme values

### 5.4 LLM Hallucinations and Out-of-Range Parameters

When generating parameter deltas, the LLM may produce values outside the physically plausible range (hallucinations, 幻觉), such as setting CCM matrix elements to 10.0 or other unreasonable values.

**Engineering safeguards**:
- Parameter range validation layer (refuse to execute and return an error when a parameter is out of bounds)
- Magnitude limiting (maximum delta constraint per step)
- Historical mean anchoring (delta relative to current value not to exceed ±20%)

---

## §6 Code

This chapter's §6 provides the following core code examples (runnable locally):

**Notebook structure**:

**Section 1 — Environment setup and ISP simulator**: builds a parameterizable ISP simulator (based on rawpy + OpenCV) that supports real-time adjustment of key parameters such as Gamma, NR strength, and color matrix, serving as the execution environment for the Agent.

**Section 2 — IQA tool definitions**: implements the `evaluate_iqa(image_path)` tool function, integrating BRISQUE computation (via scikit-image) and CLIP-IQA computation (via the open_clip library). The tool is wrapped with the LangChain `@tool` decorator and supports JSON output.

**Section 3 — ReAct Agent construction**: uses LangChain's `create_react_agent` interface to mount ISP parameter adjustment tools (`adjust_isp_params`), IQA evaluation tools (`evaluate_iqa`), and histogram analysis tools (`get_histogram`), with a System Prompt configured to inject ISP domain knowledge.

**Section 4 — Tuning loop demonstration**: runs an Agent tuning loop on a real RAW image, outputs the Thought/Action/Observation trajectory for each step, and visualizes the convergence curves of IQA metrics over iteration steps (BRISQUE descent curve, CLIP-IQA ascent curve).

**Section 5 — Parameter drift experiment**: demonstrates IQA degradation when parameters optimized on a daytime scene are applied to a nighttime scene, comparing the robustness difference between multi-scene joint tuning and single-scene tuning.

**Section 6 — CI/CD integration example**: provides a minimal GitHub Actions YAML template showing how to embed the tuning Agent in a CI pipeline to achieve automated tuning and regression testing after each firmware update.

---

## References

[1] Yao et al., ICLR 2023.
[2] [https://arxiv.org/abs/2210.03629](https://arxiv.org/abs/2210.03629)
[3] ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs
[4] Qin et al., NeurIPS 2023.
[5] [https://arxiv.org/abs/2307.16789](https://arxiv.org/abs/2307.16789)
[6] Mittal et al., IEEE TIP 2012.
[7] Ma et al., IEEE TIP 2017.
[8] Chase, 2022. [https://github.com/langchain-ai/langchain](https://github.com/langchain-ai/langchain)
[9] Shinn et al., NeurIPS 2023.
[10] [https://arxiv.org/abs/2303.11366](https://arxiv.org/abs/2303.11366)

---

## §8 Glossary

| Term | Definition |
|---|---|
| **ReAct** | Reasoning + Acting. An LLM Agent control framework that interleaves natural-language reasoning (Thought) and tool calls (Action), allowing each step's rationale to be inspected and audited by humans. |
| **Tool Use (工具调用)** | The ability of an LLM to interact with external systems through structured interfaces (Function Calling, API calls). In ISP tuning, tools include interfaces for capturing images, computing IQA, and adjusting parameters. |
| **Parameter Drift (参数漂移)** | The phenomenon in which parameters optimized for a specific scene or illumination condition degrade significantly when applied to other scenes. Analogous to distribution shift (分布偏移) in machine learning. |
| **Automated Tuning (自动化调参)** | The process of using algorithms to replace manual human adjustment of ISP parameters, with the goal of matching or surpassing expert hand-tuning quality while drastically reducing the tuning cycle (from weeks to hours). |
| **Chromatix** | The parameter configuration file format (XML) for the Qualcomm Snapdragon ISP platform, containing the complete ISP module parameter tree. |
| **IQA (Image Quality Assessment)** | Image quality assessment, divided into full-reference (FR-IQA) and no-reference (NR-IQA) categories. Automated tuning primarily relies on no-reference IQA as the reward signal. |
| **BRISQUE** | Blind/Referenceless Image Spatial Quality Evaluator. A no-reference IQA metric based on natural scene statistics; lower scores indicate better quality (typical range 0–100). |
| **NRQM** | No-Reference Quality Metric. A no-reference IQA metric optimized for super-resolution/sharpening scenarios; higher scores are better. |
| **CoT (Chain-of-Thought, 思维链)** | A technique that prompts the LLM to reason step by step rather than giving a direct answer, improving accuracy on complex reasoning tasks such as multi-step ISP tuning. |

---

## §9 Deep Dive: Technical Architecture of LLM-Assisted Tuning

### 9.1 Tool Use / Function Calling Patterns

**The basic paradigm of tool calling**

Tool Use (also known as Function Calling) is the foundational component of the LLM Agent architecture. Its core idea is to position the LLM as a **pure decision layer**, while encapsulating all side-effecting operations (parameter modification, image capture, metric computation) as "tool" interfaces that the LLM can call. Compared with having the LLM output parameter values directly, a tool-calling architecture offers the following advantages:

- **Clear boundaries**: the LLM is responsible for "deciding what to do"; the tool layer is responsible for "how to do it concretely" — the two are decoupled
- **Auditability**: every tool call has a complete input/output log, making the tuning decision process fully traceable
- **Replaceability**: the underlying tool implementations (Qualcomm CIQT / MTK Camera Tool / software simulator) can be swapped out independently without affecting the LLM decision layer

**Function Calling specification for ISP tuning tools**

Using the OpenAI Function Calling format as an example, the ISP parameter adjustment tool is defined as follows:

```json
{
  "name": "adjust_isp_params",
  "description": "Adjust ISP parameters. Each call should only adjust a small number of parameters (1-3), observe the effect, then decide the next step.",
  "parameters": {
    "type": "object",
    "properties": {
      "param_deltas": {
        "type": "object",
        "description": "A mapping from parameter names to delta values. Positive means increase, negative means decrease.",
        "additionalProperties": {"type": "number"}
      },
      "reason": {
        "type": "string",
        "description": "The reason for adjusting these parameters (Chain-of-Thought)"
      }
    },
    "required": ["param_deltas", "reason"]
  }
}
```

The `reason` field forces the LLM to output the rationale for its adjustment, naturally implementing the Chain-of-Thought mechanism — the LLM must write out its reasoning chain in the JSON rather than simply outputting numbers, thereby improving decision quality and interpretability.

**Tool-call sequence and state management**

Each tool call returns a new system state, and the LLM maintains an implicit state tracker (implemented via conversation history). A key engineering detail is **state compression** (状态压缩): conversation history grows linearly with the number of iteration steps, and token consumption grows accordingly. When history exceeds 60% of the context window, the historical tool-call sequence should be compressed into a natural-language summary:

```
[Summary of the first 10 tuning steps]
- gamma_toe_y adjusted from 0.00 to +0.015 (shadow brightening)
- awb_gain_b adjusted from 1.50 to 1.58 (correcting blue channel deficiency)
- BRISQUE reduced from 48.2 to 31.2, ΔE reduced from 5.2 to 2.8
- Outstanding unresolved issue: mild highlight clipping (2.5%)
```

### 9.2 ISP-Specific Optimization of the ReAct Framework

**Limitations of the standard ReAct framework**

Standard ReAct (Yao et al., ICLR 2023) performs well on general Agent tasks, but two classes of problems arise when it is applied directly to ISP tuning:

1. **Actions are too fine-grained**: the LLM tends to adjust only one parameter per step, whereas the coupling among ISP parameters requires certain operations to involve multiple parameters simultaneously (e.g., when raising sharpening gain, NR strength should be lowered at the same time to maintain balance).
2. **Observations are information-overloaded**: a complete IQA report contains dozens of metrics, making it difficult for the LLM to correctly attribute causation within a limited context.

**ISP-ReAct optimization strategies**

**Optimization 1: hierarchical action space**

Actions are split into two levels — Macro-Actions and Micro-Actions:

| Level | Example | Parameter scope | When to use |
|------|------|------------|---------|
| Macro-action | `fix_shadow_noise` | NR + Gamma Toe + LSC coordinated | After a specific problem is diagnosed |
| Macro-action | `correct_awb_warm` | AWB R/B gain coordinated adjustment | When color temperature shift is obvious |
| Micro-action | `adjust_single_param` | Single-parameter fine-tuning | During the refinement phase |

Each macro-action is backed by a predefined multi-parameter coordination template; the LLM only needs to choose "which problem to fix," and the template is responsible for generating the concrete multi-parameter deltas.

**Optimization 2: structured Observation summary**

Compress the raw IQA report into a structured diagnostic card to reduce the attribution burden on the LLM:

```
[Quality Diagnostic Card]
- Overall quality: BRISQUE=31.2 (target<30) ⚠ Slightly over target
- Color accuracy:  ΔE=2.8 (target<3.0) ✓ Within target
- Dynamic range:   Highlight clipping=2.5% ⚠ Mild, Shadow clipping=0% ✓
- Noise level:     SNR=41dB (target>40dB) ✓ Within target
- Top unresolved issue: [Mild highlight clipping]
```

The diagnostic card uses visual markers (✓/⚠/✗) to help the LLM quickly identify priorities, avoiding wasting tuning steps on metrics that have already been met.

### 9.3 Chain-of-Thought Prompting for ISP Parameter Diagnosis

**ISP-CoT prompt design**

Chain-of-Thought (CoT, 思维链) prompting improves accuracy on complex reasoning tasks by requiring the LLM to reason "step by step" rather than outputting an answer directly. In ISP tuning, the design of the System Prompt for CoT prompting is critical:

```
You are an expert ISP tuning engineer. When diagnosing image quality issues,
always follow this reasoning chain:

1. OBSERVE: What specific quality issues do you see in the metrics?
   (Focus on metrics that are NOT meeting targets)

2. HYPOTHESIZE: What ISP parameters are most likely causing each issue?
   Use the causal relationships:
   - High BRISQUE in smooth regions → over-smoothing (NR too strong)
   - High BRISQUE in textured regions → under-smoothing (NR too weak) or compression artifacts
   - ΔE > 3.0 in neutral colors → AWB error
   - ΔE > 3.0 in saturated colors → CCM saturation error
   - Highlight clipping → Gamma highlight rolloff too aggressive

3. PRIORITIZE: Which issue has the highest perceptual impact?

4. ACT: Propose the minimal parameter change to address the highest-priority issue.

Always output your reasoning in the "reason" field before specifying param_deltas.
```

This structured CoT prompt significantly reduces "intuitive leap" errors by the LLM — when the LLM must first identify the problem and then trace back to the parameter cause, the directional accuracy of the resulting parameter deltas (based on simulation experiments with published evaluation benchmarks) improves from approximately 65% to approximately 85%.

**Zero-Shot CoT vs. Few-Shot CoT**

| Strategy | Prompt content | First-step accuracy | Applicable scenario |
|------|---------|-----------|---------|
| Zero-Shot CoT | "Let's think step by step" + causal relationship list | ~65% | General scene initialization |
| Few-Shot CoT | 3–5 complete Thought–Action–Observation trajectory examples | ~85% | Known scene types (e.g., night scenes) |
| Hybrid CoT | Zero-Shot + dynamically retrieved similar historical trajectories | ~82% | Covers both new and familiar scenes |

---

## §10 ISP Tuning Agent Design

### 10.1 Full Specification of the State Representation

**Multi-dimensional state vector design**

In the sequential decision-making framework, the completeness of the state representation directly determines the Agent's decision quality. The state vector of the ISP tuning Agent should include the following dimensions:

**Parameter state vector** $\theta_t \in \mathbb{R}^D$ (normalized to [0, 1]):
- Current values of key parameters in each module
- Normalization method: $\theta_{\text{norm}} = (\theta - \theta_{\min}) / (\theta_{\max} - \theta_{\min})$
- In practice, only "tunable parameters" (~20–50) are tracked rather than the full parameter set (500+), reducing the state space dimensionality

**Quality metric vector** $q_t \in \mathbb{R}^M$ (normalized to [0, 1]):
- BRISQUE (normalized: inverse of score/100)
- NRQM (normalized: score/10)
- CLIP-IQA (already in the [0, 1] range)
- ΔE (normalized: (5 − ΔE)/5, so that target ΔE = 0 yields a value of 1)
- SNR (normalized: (SNR − 30)/20, with 30–50 dB as the normal range)

**Image statistics vector** $h_t \in \mathbb{R}^K$:
- Luminance histogram mean, variance, skewness, kurtosis
- Highlight fraction (fraction of pixels with luminance > 240/255)
- Shadow fraction (fraction of pixels with luminance < 16/255)
- Per-color-channel mean (to assess color balance)
- Local contrast (Laplacian variance)

**Scene context vector** $c_t \in \mathbb{R}^P$:
- One-hot encoding of illumination type (daytime / overcast / indoor / night / backlit)
- ISO value (log-normalized)
- Scene category embedding (first 8 principal components of CLIP image encoder output)

### 10.2 Action Space Design: Continuous Parameter Adjustment + Discrete Algorithm Switching

**Continuous action space**

For each tunable parameter $\theta_j$, the action is a delta $\Delta\theta_j \in [-\Delta_{\max,j}, +\Delta_{\max,j}]$, where $\Delta_{\max,j}$ is the maximum single-step adjustment magnitude for the $j$-th parameter (typically set to 5–10% of the parameter range):

$$\theta_{t+1,j} = \text{clip}(\theta_{t,j} + \Delta\theta_j,\, \theta_{\min,j},\, \theta_{\max,j})$$

**Discrete action space: algorithm switching**

Beyond fine-tuning parameters, the ISP also supports discrete algorithm mode switches (which cannot be expressed as continuous deltas):

| Discrete action | Corresponding operation | Trigger condition |
|---------|---------|---------|
| `switch_nr_mode(spatial/temporal)` | Switch denoising algorithm | Motion scene / static scene |
| `enable_hdr_merge()` | Enable multi-frame HDR merge | High dynamic range scene |
| `switch_awb_mode(auto/outdoor/indoor)` | Switch AWB mode | Special illuminant scene |
| `enable_face_nr(on/off)` | Enable face-specific denoising | Portrait scene |

In addition to `param_deltas`, the LLM can output a `mode_switch` field specifying a discrete mode switch; the tool layer is responsible for merging and executing both.

### 10.3 Reward Function Design: Subjective IQA + Objective Metric Combination

**Weighted reward combination**

The tuning reward function must balance multiple quality objectives to avoid overfitting to a single metric:

$$r_t = \underbrace{w_1 \cdot \Delta\text{CLIP-IQA}}_{\text{subjective perception proxy}} + \underbrace{w_2 \cdot (-\Delta\text{BRISQUE}/100)}_{\text{naturalness}} + \underbrace{w_3 \cdot (-\Delta E / 5)}_{\text{color accuracy}} + \underbrace{w_4 \cdot \Delta\text{SNR}/20}_{\text{noise control}} + \underbrace{w_5 \cdot r_{\text{penalty}}}_{\text{constraint penalty}}$$

where the constraint penalty term is:

$$r_{\text{penalty}} = -\lambda_1 \cdot \mathbb{1}[\text{clipping} > 5\%] - \lambda_2 \cdot \mathbb{1}[\Delta\text{hue} > 10°]$$

(a hard penalty is applied when highlight clipping exceeds the threshold or hue shift is too large)

**Weight calibration**

The weights $\{w_i\}$ should be determined via correlation analysis: compute the Spearman rank correlation coefficient between each metric and human MOS, normalize the coefficients as initial weights, then fine-tune through a small number of human subjective experiments. Typical reference values: $w_1=0.35,\; w_2=0.25,\; w_3=0.25,\; w_4=0.10,\; w_5=0.05$.

### 10.4 LLM-RLHF vs. DRL-ISP Comparison

| Dimension | LLM-RLHF tuning | Deep Reinforcement Learning (DRL-ISP) |
|------|--------------|----------------------|
| **Basic paradigm** | Pretrained LLM zero-shot/few-shot inference | Train a policy network from scratch (DQN/PPO) |
| **Data requirements** | None or only a small number of MOS annotations | Large number of (environment interaction, reward) training pairs |
| **Training cost** | None (Prompt Engineering) or lightweight SFT | Thousands to tens of thousands of ISP interactions |
| **Convergence speed** | Typically 5–15 steps (leverages prior knowledge) | Initial random exploration; may require hundreds of interactions |
| **Interpretability** | High (Thought chain is human-readable) | Low (policy network is a black box) |
| **Cross-sensor generalization** | Adapts to new sensors by swapping the system prompt | Requires retraining (Transfer Learning can reduce this burden) |
| **Final accuracy** | Medium–high (limited by LLM's prior accuracy for specific parameter values) | High (can reach optimal with sufficient training) |
| **Production deployment cost** | Low (only needs LLM API) | High (requires maintaining training infrastructure) |

**Practical recommendation**: in scenarios with many sensor variants and short tuning cycles (smartphone OEM annual new models), the rapid launch advantage of the LLM-RLHF approach is significant. In scenarios with few fixed sensors and a pursuit of extreme accuracy (professional cameras, automotive cameras), the long-term optimization precision of DRL-ISP is more competitive. The two approaches can be combined: the LLM provides an initial parameter configuration, and DRL refines it further.

---

## §11 Multimodal Feedback Loop

### 11.1 Feeding ISP Output Images to a VLM for Quality Diagnosis

**VLM as a perceptual diagnostic engine**

Traditional NR-IQA tools (BRISQUE, HyperIQA) output scalar scores and cannot localize specific distortion regions or root causes. Feeding ISP output images directly into a Vision-Language Model (VLM) yields richer perceptual diagnostic information:

```python
# Pseudocode: VLM quality diagnosis tool
def vlm_quality_diagnosis(image_path: str, model: str = "gpt-4-vision") -> dict:
    """
    Call a VLM to perform perceptual diagnosis on ISP output images.
    Returns a structured distortion description and tuning recommendations.
    """
    prompt = """
    You are a professional camera imaging scientist. Please analyze the following
    quality dimensions of this image:

    1. Noise: Is there visible noise? In which regions? Estimate severity (mild/moderate/severe)
    2. Sharpness: Is overall sharpness appropriate? Is there over-sharpening (halo) or blur?
    3. White balance: Is the color temperature accurate? Is there a color cast (warm/cool/green/magenta)?
    4. Exposure: Is the highlight overexposed? Are shadows underexposed? Dynamic range performance?
    5. Color saturation: Are skin tones natural? Is there over-saturation?

    Output the diagnosis in JSON format, including a severity (0-3) and description field for each dimension.
    """
    response = call_vlm_api(image_path, prompt, model=model)
    return parse_json_response(response)
```

**Typical structure of VLM diagnostic output**

```json
{
  "noise": {"severity": 1, "description": "Mild granular noise in shadow regions at ISO 1600; highlight regions are clean"},
  "sharpness": {"severity": 2, "description": "Obvious halo at edges; high-frequency over-sharpening; recommend reducing USM gain"},
  "white_balance": {"severity": 1, "description": "Color temperature ~200K warm; blue channel slightly insufficient"},
  "exposure": {"severity": 0, "description": "Exposure accurate; dynamic range performance good"},
  "saturation": {"severity": 1, "description": "Skin tones slightly over-saturated; recommend reducing skin-tone CCM saturation"}
}
```

The LLM tuning Agent can directly use the VLM diagnostic JSON as an Observation input, prioritizing issues with severity >= 2.

### 11.2 GPT-4V / Claude for ISP Artifact Recognition

**VLM recognition capability for specific ISP artifacts**

By building dedicated Few-Shot prompts, modern VLMs (GPT-4V, Claude 3 Sonnet) are capable of identifying the following ISP-specific artifacts:

| ISP artifact | Example VLM recognition prompt | Root-cause parameter |
|---------|----------------|------------|
| Color moiré (色彩摩尔纹) | "Does the image contain colored stripes or grid-like artifacts?" | Demosaic algorithm parameters |
| Lens vignetting (镜头暗角) | "Are the four corners of the image darker than the center?" | LSC gain deficiency |
| Rolling shutter effect (果冻效应) | "Are moving object edges tilted or distorted?" | Readout rate, EIS parameters |
| Over-sharpening halo (过度锐化Halo) | "Is there a bright halo around high-contrast edges?" | USM gain too high |
| Chromatic aberration (色差) | "Are there colored fringes along high-contrast edges?" | CA correction parameters |
| Blockiness (块状效应) | "Are there 8×8 or 16×16 block patterns in the image?" | JPEG quality factor |

**Limitation note**: VLMs have low recognition rates for subtle artifacts (e.g., sub-pixel-level chromatic aberration). Such fine artifacts still require dedicated tools (e.g., MTF curve analysis). The strength of VLMs lies in **zero-shot recognition** and **natural-language description** of medium-to-severe artifacts.

### 11.3 Automated Log Analysis: Converting ISP Tuning Logs to Natural-Language Summaries

**Problem background**

The ISP tuning process generates large volumes of structured logs (parameter change records, IQA metric time series, A/B test results), from which engineers find it difficult to quickly extract key insights. LLMs can convert these structured logs into readable natural-language summary reports.

**Log summarization prompt template**

```
The following is the complete log of an ISP tuning session. Please generate a concise
tuning report containing:
1. The target scene and initial quality state
2. The main issues identified (sorted by severity)
3. The key adjustment steps executed and their effects
4. The final quality level achieved
5. Any remaining unresolved issues (if any)

Tuning log:
{tuning_log_json}
```

**Output example**

```
## ISP Tuning Report — Night Indoor Scene (2025-03-15)

**Initial state**: BRISQUE=48.2, ΔE=5.2, SNR=38dB — overall quality below target

**Main issues**:
1. Severe underexposure in shadow region (shadow mean=35/255) [High priority]
2. AWB color temperature ~400K too warm; blue channel severely deficient [High priority]
3. Excessive high-frequency noise; NR strength insufficient [Medium priority]

**Execution steps** (8 steps total):
- Steps 1-2: Adjusted Gamma toe to brighten shadows → shadow mean rose from 35 to 52, BRISQUE dropped to 41
- Steps 3-4: Corrected AWB blue gain → ΔE reduced from 5.2 to 2.8
- Steps 5-6: Increased ISO1600 NR strength → noise improved, BRISQUE further reduced to 30.1
- Steps 7-8: Fine-tuned highlight rolloff → highlight clipping reduced from 8% to 1.8%

**Final state**: BRISQUE=29.8 ✓, ΔE=2.6 ✓, SNR=41.2dB ✓

**Remaining issues**: None
```

---

## §12 Automated Tuning Pipeline for Mass-Production Scenarios

### 12.1 Large-Scale Multi-SKU Adaptation Architecture

**Scale of tuning demand for annual new models**

Major smartphone OEMs release 10–30 new models per year, with each model equipped with 1–3 sensors, each requiring independent ISP tuning. Using traditional methods, each model requires 2–4 weeks, and each sensor requires approximately 40–80 person-hours. The full-year workload scale:

$$\text{Total person-hours} = 20 \text{ models} \times 2 \text{ sensors} \times 60 \text{ hours} = 2400 \text{ person-hours} \approx 1.5 \text{ engineer-years}$$

The goal of the LLM automated tuning pipeline is to reduce the per-sensor tuning cycle from 2–4 weeks to 2–3 days, and the manual labor from 60 hours to 5–10 hours (final review only).

**Overall pipeline architecture**

```
New sensor available
    ↓
[Phase 1: Calibration data collection] 2-4 hours
- Standard test scene capture (ColorChecker, ISO card, low-light, portrait, landscape)
- Automated calibration algorithms (LSC calibration, CCM initial matrix computation)
- LLM generates initial parameter configuration based on sensor datasheet
    ↓
[Phase 2: LLM automated tuning] 4-8 hours (runs automatically, no human intervention)
- Automated tuning loop covering all scene categories (10-20 iteration steps per scene)
- Real-time IQA monitoring, tuning reports generated
- Automatic detection of anomalies (newly introduced artifacts, metric oscillation) with logging
    ↓
[Phase 3: Automated benchmarking] 2-3 hours
- Standard benchmark suite run (MTF, SNR, Color Accuracy, Dynamic Range)
- Comparison against reference metrics from the previous generation
- Pass/fail determination report generated
    ↓
[Phase 4: Manual review] 2-4 hours (engineer intervention)
- Review automated reports from Phase 2/3
- Visual inspection of high-priority scenes (faces, night scenes)
- Manual refinement of any failing items
    ↓
[Phase 5: Validation and release]
- Parameters merged to version repository
- Full regression test
- OTA preparation
```

### 12.2 Automated Coverage Validation for Multi-Illuminant Scenes

**Coverage metric**

Quality assurance for mass-production tuning requires that the parameter configuration meets quality thresholds across all scene types actually encountered in production. Automated coverage validation:

1. **Scene category enumeration**: define the scene category matrix that must be validated (illumination type × ISO range × scene content)
2. **Automated capture and scoring**: capture representative images for each scene category and run NR-IQA scoring
3. **Coverage rate calculation**:

$$\text{CoverageRate} = \frac{\text{Number of scene categories meeting threshold}}{\text{Total number of scene categories}} \times 100\%$$

4. **Identification of uncovered scenes**: for scene categories where scoring fails to meet the threshold, automatically trigger a targeted tuning loop

**Key challenges in multi-illuminant validation**

Under different color-temperature illuminants (D65 / Illuminant A / fluorescent F), AWB and CCM performance can differ significantly for the same scene. The automated pipeline must validate each standard illuminant separately under a simulated illumination cabinet (模拟光源箱), and verify that AWB transitions smoothly when illuminants change (to avoid abrupt color jumps).

### 12.3 Designing Human Escalation Points

**When to escalate to human**

An automated tuning pipeline must define clear trigger conditions for human intervention, avoiding two extremes: over-reliance on automation (failing to alert when there are serious problems) or excessive human intervention (losing the benefit of automation).

**Tiered escalation strategy**

| Trigger condition | Severity | Intervention mode | Response time |
|---------|---------|---------|---------|
| BRISQUE > 50 in any scene | Critical | Stop pipeline immediately; notify Level-2 engineer | Within 2 hours |
| Scene coverage rate < 80% | Moderate | Generate report; ask engineer to review uncovered scenes | Within 24 hours |
| Parameter oscillation (same parameter repeatedly alternating over 3 consecutive steps) | Moderate | Stop tuning for that scene; use last stable configuration | Review within 72 hours |
| All metrics pass but a new artifact is found during visual inspection | Low | Log to review queue; no immediate response required | Next version iteration |
| New sensor behaves abnormally (calibration data is an outlier) | High | Pause tuning; notify hardware team to investigate the sensor | Within 4 hours |

---

## §13 Practical Limitations and Future Outlook

### 13.1 The Determinism Problem in LLM Tuning

**Inconsistent outputs for the same prompt**

The LLM's temperature parameter controls output randomness. Even at temperature = 0 (greedy decoding), LLM outputs may still be inconsistent for the following reasons:

- **Floating-point rounding differences**: different batch sizes or hardware precision cause minor differences in logits
- **System prompt sensitivity**: small wording changes in the system prompt can lead to dramatically different parameter suggestions
- **Context length effect**: changes in conversation history length affect the attention weight distribution

**Engineering mitigation measures**

1. **Multi-sample + median**: run LLM inference 3–5 times for the same state and take the median of the suggested deltas for each parameter; this can reduce the variance of parameter suggestions by approximately 60%
2. **Parameter delta magnitude constraints**: clip the LLM's suggested delta values (|Δθ| ≤ Δmax) to prevent a single large-magnitude adjustment
3. **Consistency verification**: if two consecutive suggestions for the same problem point in opposite directions (one suggests +0.05, the next suggests −0.03), trigger a human review
4. **Prompt template version locking**: system prompt templates in the production environment are under strict version control and must not be modified arbitrarily

### 13.2 Comparison with Traditional Numerical Optimization Methods

**Bayesian Optimization (贝叶斯优化, BO)** is another important direction for ISP tuning. A comprehensive comparison with the LLM approach:

| Dimension | LLM tuning | Bayesian Optimization (BO) | Genetic Algorithm (GA) |
|------|---------|--------------|-------------|
| Exploitation of prior knowledge | Strong (LLM pretraining prior) | Moderate (GP prior) | Weak (random initialization) |
| First-step benefit | High (provides direction immediately) | Low (needs exploration phase) | Low (random) |
| High-dimensional parameter space | Limited (LLM struggles with 100+ dimensions) | Moderate (curse of dimensionality; typically < 50 dims) | Poor (gets slower with more dimensions) |
| Constraint handling | Natural (describe constraints in the prompt) | Requires extra design | Complex (violation penalty) |
| Computational cost | Low–moderate (LLM inference) | Moderate (GP fitting) | High (large number of evaluations) |
| Interpretability | High | Low | Low |
| Convergence accuracy | Moderate (subject to prior bias) | High (mathematical guarantee of local optimum) | Moderate (global exploration) |

**Future trend: LLM + BO hybrid method**

The LLM is responsible for identifying the initial exploration direction (using prior knowledge to quickly reach a high-quality region), and BO is responsible for fine-grained optimization within the neighborhood identified by the LLM (compensating for the LLM's lack of numerical precision). This hybrid approach is expected to reach, in 5–10 steps, the quality level that pure BO requires 20–30 steps to achieve.

### 13.3 Trustworthiness Guarantees for LLM in Closed-Loop Systems

**Reliability requirements of closed-loop systems**

When embedding an LLM in a production tuning pipeline (a closed-loop control system), reliability requirements are far higher than for general NLP tasks. The core challenge: how can the probabilistic outputs of an LLM be used reliably in a deterministic engineering system?

**Trustworthiness guarantee mechanisms**

1. **Output Validation Layer**: all LLM outputs pass through formal validation (format correctness, physical plausibility, constraint satisfaction) before execution
2. **Rollback mechanism**: save a snapshot of the current parameter state before each step is executed; if a step causes a key metric to degrade beyond a threshold, automatically roll back
3. **Shadow Mode deployment**: the LLM tuning system runs in "shadow mode" (does not actually modify parameters; only records suggestions) and continuously monitors the consistency between its suggestions and those of human engineers; once consistency reaches a threshold, the system transitions to actual production

**Long-term outlook**

As LLMs are fine-tuned specifically on ISP tuning data (parameter–effect pairs, tuning history trajectories) and as their multimodal capabilities are enhanced (processing RAW images directly instead of relying on IQA numerical outputs), the determinism and accuracy of LLM-based tuning will continue to improve. At the current stage (2025–2026), the most appropriate positioning is "LLM-assisted tuning" rather than "LLM-autonomous tuning" — human engineers retain final decision-making authority, while the LLM handles the bulk of repetitive preliminary tuning work.
