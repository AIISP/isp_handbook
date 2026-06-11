# Part 4, Chapter 19: Reinforcement Learning ISP Parameter Optimization (DRL-ISP: Deep Reinforcement Learning for ISP)

> **Pipeline position:** ISP parameter tuning; task-aware ISP system optimization
> **Prerequisites:** Volume 4, Chapter 6 — Task-Driven ISP; Volume 4, Chapter 1 — 3A System; Volume 3, Chapter 17 — Generative RAW-to-RGB
> **Reader path:** ISP systems engineers, computer vision engineers, camera algorithm researchers

---

## §1 Theory

### 1.1 Framing the ISP Parameter Optimization Problem

Traditional ISP tuning is a time-consuming manual process: algorithm engineers subjectively evaluate images and consult objective metrics as they hand-search across thousands of ISP parameters — tone curves, color matrices, denoising strengths, sharpening coefficients, and more — for an optimal configuration. This commonly takes weeks or even months and depends heavily on individual expertise.

In recent years, research into **automatic ISP parameter optimization** has sought to replace this process with algorithms. Unlike conventional supervised-learning approaches (Volume 4, Chapter 6 — Task-Driven ISP, which trains a network to directly predict ISP parameters), **Deep Reinforcement Learning for ISP (DRL-ISP)** models ISP parameter optimization as a **sequential decision-making** problem:

- **State** $s_t$: the current image and ISP parameter state (this can be a RAW image plus the current parameter settings, or an intermediate processing result);
- **Action** $a_t$: selecting and adjusting a particular ISP parameter (e.g., increasing sharpening strength by $+0.1$, moving a Gamma curve control point);
- **Reward** $r_t$: the improvement in image quality after the action is applied (e.g., PSNR gain, mAP gain, subjective MOS score);
- **Policy** $\pi_\theta(a|s)$: a policy network that selects the optimal action given the current state.

The core advantage of the RL framework over supervised learning is that the **reward signal can be any measurable objective**, including non-differentiable metrics (such as object-detection mAP or face-recognition accuracy), human subjective scores, and even the end-to-end performance of downstream processing pipelines — all of which are difficult to use directly as loss functions in supervised learning.

---

### 1.2 The DRL-ISP Implementation (Onzon et al., 2021)

**DRL-ISP** (Onzon et al., CVPR 2021) is a landmark contribution in this direction. Its design choices and experimental findings reveal both the engineering feasibility and the limitations of applying RL to ISP optimization.

**ISP Toolbox:** An action space consisting of 51 ISP tools is constructed, each tool corresponding to one ISP parameter adjustment operation, for example:
- Brightness adjustment (+ / − step size)
- Color temperature shift (cool / warm direction)
- Local contrast enhancement (CLAHE parameter tuning)
- Sharpening kernel strength adjustment
- Denoising strength fine-tuning
- Tone-mapping curve control-point displacement

**State representation:** Histogram statistics (luminance and individual R/G/B channels) of the current processed image are concatenated with a current-parameter state vector (approximately 50 dimensions) to form the state vector $s_t$, which is fed into a policy network (MLP or lightweight CNN).

**Reward function:** For object-detection tasks, the mAP increment from YOLO is used as the reward:

$$r_t = \text{mAP}(\text{ISP}(x_\text{raw}; \theta_t)) - \text{mAP}(\text{ISP}(x_\text{raw}; \theta_{t-1})) \tag{1}$$

**Experimental results:**
- Object detection task (YOLO on COCO): after DRL-ISP optimization, mAP@0.50 improved from **33.8%** to **36.5%** (+2.7 percentage points);
- Semantic segmentation task (DDRNet on Cityscapes): optimization effect was limited; mIoU improvement < 1%, because semantic segmentation is less sensitive to color than object detection;
- A DRL-ISP trained on simulated RAW generated via Unpaired CycleR2R performed well on simulated RAW but exhibited approximately a **3–5%** accuracy drop on real RAW (caused by the simulated-RAW domain shift).

---

### 1.3 The Role of Inverse ISP (Reverse Pipeline) in DRL-ISP

A key challenge for DRL-ISP is that **the large volume of existing CV training data (e.g., COCO, ImageNet) consists of sRGB images, whereas ISP optimization requires RAW data**. When RAW data is scarce, **inverse ISP (Reverse / Unprocessing ISP)** offers a pathway for synthesizing RAW from sRGB images. (Volume 3, Chapter 17 covers methods such as PyNET and CycleISP in detail; Volume 3, Chapter 19 presents InvISP as a more accurate invertible ISP.)

The DRL-ISP framework employs **Unpaired CycleR2R** — a cycle-consistent inverse ISP — to synthesize simulated RAW data from sRGB inputs:
1. Use the large existing sRGB image collections (COCO, BDD100K, etc.);
2. Convert sRGB images to simulated RAW via CycleR2R;
3. Train the DRL-ISP policy network on the simulated RAW;
4. Deploy on real camera RAW at inference time.

This pipeline has an inherent **simulation-to-real domain gap (Sim-to-Real Gap)**: the simulated RAW produced by CycleR2R cannot faithfully reproduce the non-uniform noise, fixed-pattern noise (FPN), and other characteristics of a real sensor, leading to performance degradation on real RAW. Using InvISP (Volume 3, Chapter 19) can partially narrow this gap, but a fundamental solution requires collecting real RAW data.

---

### 1.4 Evolutionary Algorithm ISP Parameter Search (Comparison and Complementarity)

Reinforcement learning is not the only path to automatic ISP parameter optimization. **Evolutionary algorithms (EA)**, in particular CMA-ES (Covariance Matrix Adaptation Evolution Strategy), are a strong alternative to RL:

| Dimension | DRL-ISP (Reinforcement Learning) | CMA-ES (Evolutionary Algorithm) |
|-----------|----------------------------------|----------------------------------|
| Optimization efficiency | Online updates; relatively high sample efficiency | Lower sample efficiency; requires many evaluations |
| Gradient requirement | Policy gradient (requires differentiable reward approximation) | Gradient-free; directly evaluates black-box reward |
| Convergence stability | Training unstable; sensitive to hyperparameters | Relatively stable; but risk of local optima is higher |
| Parallelism | Can leverage environment parallelism for acceleration | Population is naturally parallelizable |
| Interpretability | Policy-network decisions hard to interpret | Search trajectory intuitive; parameter changes visualizable |

In ISP tuning toolchains (Volume 4, Chapter 10), evolutionary algorithms are commonly used for **global coarse search** (rapidly narrowing the parameter range), while RL is used for **local fine-tuning** (precise optimization in the neighborhood of a good parameter configuration), forming a two-stage optimization pipeline.

---

### 1.5 Reward Function Engineering: Perceptual Quality vs. Downstream Tasks

The design of the reward function in DRL-ISP is the single most important determinant of system effectiveness.

**Perceptual-quality-oriented reward:**
$$r = \text{PSNR}(\text{ISP}(x;\theta), x^*) \quad \text{or} \quad r = -\text{LPIPS}(\text{ISP}(x;\theta), x^*)$$

Here $x^*$ is a reference standard (the camera vendor's native ISP rendering, a professionally color-graded result). This type of reward steers the ISP toward output closer to the reference, but is constrained by the quality and stylistic bias of that reference.

**Downstream CV task-oriented reward:**
$$r = \Delta\text{mAP} = \text{mAP}(D(f_\text{ISP}(x;\theta))) - \text{mAP}(D(f_\text{ISP}(x;\theta_0)))$$

Here $D$ is an object detector and $\theta_0$ denotes the initial ISP parameters. This type of reward directly optimizes the contribution of the ISP to CV task performance, but may produce "unnatural" ISP renderings that are effective for detectors yet perceptually bizarre to the human eye (e.g., heavily over-contrasted images that boost detection mAP but look harsh).

**Hybrid reward:** In practice a weighted combination of perceptual quality and task performance is typically designed:
$$r = \lambda_\text{perc} \cdot r_\text{perc} + \lambda_\text{task} \cdot r_\text{task}$$

Adjusting the $\lambda$ ratio allows different trade-offs between "perceptually satisfying image quality" and "machine-vision-optimal image quality" — this is in essence the core proposition of Volume 4, Chapter 6, "Task-Aware ISP."

---

### 1.6 Meta-Reinforcement Learning: Rapid Cross-Scene Adaptation

Conventional DRL-ISP trains a policy network for a fixed scene type (e.g., daytime outdoors) and suffers a noticeable performance drop on out-of-distribution scenes such as nighttime or indoor environments. **Meta-Reinforcement Learning (Meta-RL)** provides a framework for "learning how to learn ISP parameter adjustments":

- **Meta-training phase:** Train a meta-policy network $\pi_{\theta^*}$ across diverse scenes (daytime / nighttime / indoor / outdoor), with the goal of finding a policy initialization that can rapidly adapt to any new scene;
- **Fast adaptation phase:** For a new scene, only a small number (5–10) of reward evaluations suffice to complete the policy update $\theta' = \theta^* - \alpha \nabla_\theta J(\pi_{\theta^*})$.

This shares the same framework as Meta-ISP in Volume 3, Chapter 18, with the distinction that the "task" in Meta-RL is to optimize ISP parameters (action space), whereas the "task" in meta-supervised learning is to adapt image quality to a new sensor.

---

## §1-B RL Fundamentals and ISP Mapping Details

### 1b.1 Formalizing ISP Parameter Optimization as a Markov Decision Process (MDP)

Precisely mapping the ISP parameter optimization problem onto the MDP 5-tuple $(S, A, P, R, \gamma)$:

**State Space $S$:**

The state for ISP optimization should encode "the current processing state of the image," encompassing the following information categories:

| Information category | Specific content | Recommended encoding |
|---------------------|-----------------|---------------------|
| Image statistical features | Luminance/color histograms (256 bins × RGGB 4 channels) | Normalized histogram vector, 1024 dimensions |
| Gradient map statistics | Sobel response mean, variance, high-frequency energy | Scalar features, 8 dimensions |
| Face detection results | Face region fraction, face luminance, skin color temperature | Scalar features, 6 dimensions |
| Sensor metadata | ISO, exposure time, CCT (color temperature estimate) | Normalized scalars, 4 dimensions |
| Current ISP parameter state | Current value of each parameter (normalized to [0, 1]) | Parameter vector, 50–100 dimensions |
| Historical quality | Reward values for the preceding 3 frames | Scalar sequence, 3 dimensions |

Typical total state vector dimensionality: approximately 1100–1200 dimensions; can be reduced to 128–256 dimensions via PCA or a lightweight encoder.

**Action Space $A$:**

ISP parameter adjustments can be designed as:

- **Discrete actions:** Each parameter has $k$ predefined adjustment increments (e.g., $\{-0.2, -0.1, 0, +0.1, +0.2\}$); total number of actions = number of parameters × $k$. Advantages: stable policy learning (PPO/DQN both applicable); disadvantage: precision limited by step resolution.
- **Continuous actions:** Each parameter outputs a continuous value; the policy network outputs $\mu$ and $\sigma$ (Gaussian policy). Advantages: strong expressive power; disadvantage: requires SAC/TD3 or other continuous-action algorithms; training is less stable.
- **Hybrid actions:** First discretely select the parameter category, then continuously output the adjustment magnitude. Closest to engineering practice, but implementation is complex.

**Multi-Dimensional Simultaneous Action:**
Outputting adjustments to all parameters at once (adjusting all parameters in a single step) vs. adjusting one parameter per step (sequential adjustment). Experiments show: when the number of parameters is < 20, multi-dimensional simultaneous actions converge faster; when the number of parameters is > 50, sequential adjustment (adjusting high-impact parameters first) is more stable.

**Transition Probability $P$:**

In ISP optimization, $P(s_{t+1}|s_t, a_t)$ is in practice deterministic (same input image + same parameter adjustment → same output image), so explicit modeling of the transition probability is not required — only the ability to execute the ISP pipeline (simulated or real) to observe the next state.

**Discount Factor $\gamma$:**

ISP optimization is typically a short-horizon decision problem (the optimization goal is the final image quality within 10–50 steps); $\gamma = 0.95–0.99$ is a typical setting. A larger $\gamma$ makes the policy more "patient" (willing to accept short-term negative-reward actions in exchange for long-term gains, e.g., temporarily reducing sharpening to achieve more accurate colors, then re-increasing sharpening).

### 1b.2 Engineering Considerations for State Space Design

**Advantages of histograms as state:**
- Rotation/translation invariance: histograms of the same scene under different compositions are similar, improving policy generalization
- Moderate dimensionality: 256 × 4 = 1024 dimensions; sufficient information with manageable size
- Semantic alignment with ISP operations: a brightness adjustment directly corresponds to a global shift of the histogram

**Why sensor metadata is necessary:**

The same image statistical features (e.g., a particular histogram shape) correspond to different optimal ISP parameters at different ISO values: ISO 6400 requires stronger denoising (sacrificing detail), whereas ISO 100 should preserve maximum detail. A policy without ISO metadata cannot distinguish these two situations and will learn an average strategy across all ISO levels (unsuitable for any particular ISO).

**Role of historical frame quality:**

ISP parameter adjustments typically require multiple steps to reach the optimum (e.g., first adjust exposure, then white balance, then sharpening). The single-step state cannot determine whether the process is converging or oscillating. By including the reward history from the preceding $k$ frames, the policy can detect oscillation and proactively smooth the trajectory.

### 1b.3 Reward Function Engineering in Detail

**Full-Reference Reward:**

$$r_{FR} = w_1 \cdot \text{SSIM}(I_{out}, I_{ref}) - w_2 \cdot \text{LPIPS}(I_{out}, I_{ref})$$

where $I_{ref}$ is a reference image retouched by a professional photographer or a vendor's standard rendering. This type of reward requires a paired dataset (RAW + reference sRGB), which is expensive to obtain, but provides the most accurate training signal.

**No-Reference Reward:**

$$r_{NR} = -\text{NIQE}(I_{out}) \quad \text{or} \quad r_{NR} = -\text{BRISQUE}(I_{out})$$

No reference image is needed; training is possible on large volumes of unpaired RAW. Limitation: NIQE/BRISQUE are based on statistical priors and may give low scores to AI-enhanced images (e.g., diffusion-model super-resolution results), even when the subjective perceptual quality is high.

**RLHF-Style Reward (Human Feedback Reward Model):**

Modeling the ISP reward as a human preference model, inspired by RLHF (Reinforcement Learning from Human Feedback) used in large language models (Christiano et al., 2017):

1. **Data collection phase:** Apply different ISP parameter configurations to the same RAW image; collect pairwise human preference annotations ("Image A looks better than Image B")
2. **Reward model training phase:** Train a reward model $r_\phi(I)$ to fit human preference scores (Bradley-Terry model or Elo rating)
3. **RL training phase:** Use the trained $r_\phi$ as the reward signal to train the ISP parameter optimization policy $\pi_\theta$

The advantage of this scheme is that the reward is directly aligned with human aesthetics, free from the inconsistency between PSNR/SSIM and human perception. The cost is high data-collection expense (typically requiring thousands of pairwise annotations).

**Multi-Objective Reward:**

$$r_{multi} = \lambda_{quality} \cdot r_{quality} + \lambda_{exposure} \cdot \mathbb{1}[EV \in [EV_{min}, EV_{max}]] + \lambda_{wb} \cdot \mathbb{1}[CCT \in [2500\text{K}, 8000\text{K}]]$$

The indicator-function terms ensure that optimization does not produce extreme exposures (all-black / all-white) or extreme white balance shifts, acting as safety constraints.

### 1b.4 Comparison with Supervised Learning and LLM-Based Tuning

| Dimension | Supervised Learning ISP | DRL-ISP | LLM-Driven ISP Tuning (Volume 5, Chapter 3) |
|-----------|------------------------|---------|----------------------------------------------|
| Optimization target | Fixed loss function (L1 / SSIM / LPIPS) | Arbitrary measurable reward (including non-differentiable metrics) | Adjustment intent expressed in natural language |
| Data requirements | Large volumes of paired RAW–sRGB data | No-reference reward can bypass the paired data requirement | Few-shot examples + LLM priors |
| Training efficiency | High (batch gradient descent) | Low (sample efficiency is the primary bottleneck) | Medium (high inference cost but no training needed) |
| Inference speed | Fast (single forward pass) | Requires multi-step interaction (10–50 steps) | Slow (LLM inference, second-scale latency) |
| Interpretability | Low (black-box end-to-end) | Medium (action sequence can be visualized) | High (LLM outputs natural-language explanations) |
| Adapting to new scenes | Requires retraining | Meta-RL fast adaptation (5–10 steps) | No retraining; describe new requirements in a prompt |
| Known works | DeepISP, AWB-Net, etc. | Onzon et al. CVPR 2021 | ISP-GPT, CamCtrl, etc. |

### 1b.5 Real-World Deployment Challenges

**Sim-to-Real Gap:**

Policies trained on simulated RAW (generated by inverse ISP / CycleR2R) suffer performance degradation when inferring on real camera RAW. Root causes:
- Irregular FPN (fixed-pattern noise) of real sensors
- ADC nonlinearity (the real sensor's response curve does not fully match the model assumptions)
- Lens vignetting and chromatic aberration are only approximately modeled in the inverse ISP

Mitigation strategies:
1. **Domain Randomization:** During training, randomly inject real noise characteristics (FPN, random dark current, randomized lens vignetting) into simulated RAW
2. **Fine-tuning on Real RAW:** RL fine-tuning using a small number of real RAW–reward pairs (Sim-to-Real Transfer), analogous to the standard practice in robot learning
3. **Better Inverse ISP:** Replace CycleR2R with InvISP (Volume 3, Chapter 19) to generate higher-quality simulated RAW and narrow the Sim-to-Real Gap

**Convergence Speed:**

DRL-ISP typically requires $10^4$–$10^6$ ISP evaluations to converge from a random policy to an effective policy. Each evaluation requires a complete ISP execution (even a lightweight software ISP takes tens of milliseconds), so total training time can range from hours to days. Parallelization strategy: multiple ISP instances (each processing a different image) collect data simultaneously, using an Actor-Critic parallel sampling framework (e.g., IMPALA) to accelerate training.

**Safety Constraints:**

Design considerations to prevent the policy from outputting extreme parameters (e.g., setting all pixels to pure black or white):
- Hard parameter bounds: clamp parameters to a safe range in the post-action processing step
- Penalty reward: give a large penalty ($r = -10$) when the mean of the Y channel of the output image falls below 5% or exceeds 95%
- Constrained MDP (CMDP): use the Lagrangian method to maximize reward subject to constraint satisfaction

### 1b.6 Training Pipeline

**Complete DRL-ISP training pipeline:**

```
[Phase 1: Dataset Construction]
    ① Collect or synthesize a RAW dataset (real RAW or simulated RAW from inverse ISP)
    ② If full-reference reward is needed: collect paired RAW–reference sRGB data; OR
       If RLHF reward is needed: collect pairwise human preference annotations
       (A vs. B, approximately 5000+ pairs)

[Phase 2: Reward Model Training (RLHF route only)]
    ① Train reward model r_φ(I) to fit human preferences
    ② Validate reward model prediction accuracy on a held-out test set (target > 75%)

[Phase 3: Policy Pre-training (optional)]
    ① Supervised pre-training of the policy network (imitating manual tuning action sequences)
    ② Goal: give RL a good initialization point to reduce exploration time

[Phase 4: RL Training]
    ① Train the policy network using PPO (discrete actions) or SAC (continuous actions)
    ② Each episode: perform T=20–50 parameter adjustment steps on one RAW image
    ③ Each step: run ISP(RAW, θ_t) → compute reward r_t → update policy
    ④ Every N episodes: evaluate policy quality on the validation set; record reward curve
    ⑤ Convergence criterion: validation reward changes < 1% within 200 consecutive episodes

[Phase 5: Deployment]
    Mode A (look-up table): map policy network outputs to a finite set of ISP Profiles
    (K=10–50 scene categories); at runtime look up by scene recognition result
    Mode B (online inference): deploy a lightweight policy network (< 5M parameters)
    on the NPU; inference takes approximately 2 ms per frame
```

### 1b.7 Platform Integration: Look-up Table vs. Online Inference

| Deployment mode | Implementation | Applicable scenarios | Advantages | Cost |
|-----------------|---------------|---------------------|------------|------|
| Offline look-up table | R&D-phase RL search; results consolidated into ISP Profiles | Static scene categories; stable production scenarios | Zero online computation overhead | Cannot adapt to new scenes |
| Online lightweight inference | 2–5M parameter policy network deployed on NPU; per-frame inference | Dynamic scenes (changing light, motion scenes) | Real-time self-adaptation | 2–5 ms/frame NPU overhead |
| Hybrid mode | Offline Profiles + online fine-tuning (delta adjustment) | Flagship cameras | Balance of performance and overhead | High implementation complexity |

The mainstream approach of current smartphone manufacturers (Huawei Kirin + ISP / Qualcomm Spectra) is the **offline look-up table**: RL and evolutionary algorithms complete the parameter search during R&D, and the results are embedded in the firmware as a "scene → ISP Profile" mapping table. The end device only performs scene recognition + table lookup at runtime, without running RL inference.

---

## §2 Calibration

### 2.1 Policy Network Evaluation Protocol

Evaluation of a DRL-ISP policy network should cover the following dimensions:

1. **Final-state quality:** The improvement in the target metric (PSNR / mAP / MOS) of the ISP-rendered image relative to the initial state after $T$ optimization steps;
2. **Convergence step count:** The number of optimization steps required to reach 95% of the final performance (fewer is better, directly affecting feasibility for real-time applications);
3. **Cross-scene generalization:** Performance on test scenes outside the training distribution, measuring the policy's generalization ability;
4. **Comparison against random search / evolutionary algorithms:** Quantifying the advantage of RL over simple baselines.

### 2.2 Effect of Inverse ISP Quality on DRL-ISP

DRL-ISP performance is highly sensitive to the quality of the inverse ISP. Calibration steps:
1. On simulated RAW paired with real RAW (generated via inverse ISP), compare the noise statistical distributions of simulated and real RAW (KL divergence);
2. Run DRL-ISP on both simulated and real RAW separately, and compare the gap in target-metric improvement (this gap quantifies the domain-shift effect of the inverse ISP);
3. Narrow the domain gap by fine-tuning the policy network (using a small number of real RAW–mAP pairs as few-shot adaptation data), analogous to the standard practice in Sim-to-Real transfer.

---

## §3 Engineering Practice

### 3.1 ISP Toolbox Design Principles

The design of the action space (ISP Toolbox) in DRL-ISP is a critical engineering choice that directly affects learning efficiency:

- **Atomic operation design:** Each action should correspond to a single, independent, and predictable parameter adjustment (e.g., "brightness +5%"); avoid strong coupling between actions;
- **Step-size gradation:** Include both coarse-adjustment actions (large step size) and fine-adjustment actions (small step size) for the same parameter, allowing the policy to first locate a good region coarsely, then refine;
- **Reversibility:** Every forward action should have a corresponding inverse action ("brightness +5%" paired with "brightness −5%"), enabling the policy to undo mistaken decisions;
- **Prior constraints:** Apply parameter boundary constraints (e.g., sharpening strength not exceeding 2.0) to prevent generating parameter combinations that produce visually obvious distortions.

### 3.2 Integration with Hardware ISP

Integration of DRL-ISP into mobile camera systems typically follows one of two modes:

**Online fine-tuning mode:** After capture, DRL-ISP runs a fast inference pass on the NPU using a policy network of approximately 5M parameters (inference latency around 2 ms), predicts the optimal parameter adjustment, and applies it to the next frame or triggers an ISP parameter refresh (suitable for real-time dynamic adjustment in video/preview scenarios).

**Offline tuning mode:** For different scene categories (daytime, nighttime, indoor, sports, etc.), DRL-ISP pre-searches for the optimal parameter combination offline and consolidates the results into **scene-specific ISP parameter profile files (ISP Profiles)**. At runtime, an AI scene-recognition module selects the corresponding ISP Profile; no online RL inference is required.

The second mode is the mainstream deployment approach adopted by current smartphone manufacturers (Huawei, Xiaomi, OPPO). DRL-ISP is primarily used during the **offline tuning phase** (R&D stage) rather than being deployed at runtime.

---

## §4 Typical Failure Modes

### 4.1 Local Optima and Sparse Rewards

The ISP parameter space is high-dimensional and multi-modal (many parameter combinations show negligible differences in reward), making it easy for RL policies to get stuck in local optima. A typical symptom is that the policy cycles repeatedly among a small set of actions (e.g., oscillating between brightness +5% and −5%) without exploring regions with better parameters. Solutions: introduce entropy regularization (e.g., the maximum-entropy RL of the SAC algorithm) to encourage policy diversity; or use hierarchical RL (first select a parameter category, then select the specific adjustment magnitude) to reduce the dimensionality of the action space.

### 4.2 Divergence Between the Reward Function and Human Perception

A DRL-ISP trained with mAP as the reward may learn ISP parameters that are "useful for the detector but uncomfortable to the human eye" (e.g., extremely high contrast and strong saturation that make detection targets more prominent but render the overall image visually harsh). For consumer photography applications, perceptual quality constraints (e.g., a lower bound on BRISQUE) should be added as hard constraints rather than reward terms, preventing the policy from escaping the acceptable range of human visual quality.

### 4.3 Sample Efficiency and Online Learning Limitations

The application of model-based RL (Model-Based RL) to ISP parameter optimization is constrained by the fact that ISP pipelines are typically hardware-accelerated black boxes (gradients through ISP operations are unavailable). Building a differentiable ISP surrogate model of sufficient accuracy is difficult, so the optimal parameters learned on the surrogate model often fail to transfer to the real ISP.

---

## §5 Evaluation Methods

### 5.1 Two-Dimensional Evaluation Matrix

A comprehensive evaluation of DRL-ISP must cover the following two independent dimensions:

| Dimension | Metric | Evaluation method |
|-----------|--------|------------------|
| Perceptual image quality | PSNR / SSIM / LPIPS / MOS | Comparison against the vendor's native ISP rendering; human subjective scoring |
| Downstream task performance | mAP (detection) / mIoU (segmentation) / Top-1 Acc (classification) | Standard benchmarks: COCO / Cityscapes / ImageNet |

The optimal parameters for the two dimensions do not necessarily coincide (see the perceptual–task trade-off discussion in §1.5). It is recommended to plot a **Perceptual–Task Pareto Curve (Pareto Frontier)** to visually display the two-dimensional performance trade-off under different $\lambda$ ratios.

### 5.2 Policy Generalization Evaluation

Evaluate the generalization from training scenes (daytime outdoors, synthetic noise) to test scenes (nighttime, indoor, rainy):

1. The percentage drop in reward on test scenes relative to training scenes (> 30% indicates poor generalization);
2. Fast adaptation step count: starting from the initial policy, the number of additional optimization steps required to reach 90% of the training-scene performance on the test scene.

---

## §6 Code

The companion code for this chapter is in *See §6 Code section for runnable examples.*, which includes the following demonstrations:

1. **ISP Toolbox implementation:** Implements 20 basic ISP tool actions (coarse and fine adjustments for brightness / contrast / color temperature / saturation / sharpening), with visualization of histogram changes and image appearance changes before and after applying each individual action;
2. **Simplified DRL-ISP training:** On a COCO subset (100 images), using YOLO-v5-nano mAP as the reward, trains a 15-step policy network with the PPO algorithm, displaying the reward curve and a before/after mAP comparison;
3. **Inverse ISP domain-shift experiment:** Runs the same DRL-ISP policy on a real RAW and a CycleR2R-generated simulated RAW of the same scene, compares the performance gap between the two RAW types, and quantifies the Sim-to-Real Gap;
4. **Evolutionary algorithm vs. DRL comparison:** Uses CMA-ES to search for optimal parameters in the same action space and with the same reward function, comparing the convergence speed and final mAP of DRL-ISP and CMA-ES.

---

## §7 Key Paper Analyses

### 7.1 Onzon et al., CVPR 2021 (DRL-ISP Representative Work)

**Full title:** "Neural Auto-Exposure for High-Dynamic Range Object Detection" (Onzon, E., Mannan, F., Fathima, N., Zhang, N., & Heide, F., CVPR 2021)

**Core contributions:**
- Models automatic ISP parameter optimization as an RL problem (MDP); first published at CVPR
- Constructs a discrete action space of 51 tools covering a complete ISP parameter adjustment operation set
- Uses mAP increment on an object-detection task as the reward, demonstrating that RL can optimize non-differentiable downstream metrics
- Validated on the COCO dataset: after DRL-ISP optimization, YOLO mAP@0.50 improves from 33.8% to 36.5% (+2.7 pp)

**Limitations and follow-on work:**
- Trained only on simulated RAW (generated by Unpaired CycleR2R); performance drops approximately 3–5% on real RAW
- The choice of action space scale (51 tools) lacks systematic analysis; convergence behavior with larger action spaces (200+ tools) is unstudied
- mIoU improvement on semantic segmentation (DDRNet on Cityscapes) is < 1%, indicating limited RL effectiveness for downstream tasks with low perceptual sensitivity

### 7.2 CURL: Contrastive URL-based Image Enhancement

**Overview (Fang et al., 2021):**
CURL (Contrastive Unsupervised Representation Learning for image enhancement) uses contrastive learning to train an image enhancement policy without paired reference images. Through an InfoNCE contrastive loss, the network learns a consistent feature representation between pre- and post-enhancement images, which then guides parameter adjustment.

Relationship to DRL-ISP: CURL is not a strict RL method, but its "unsupervised reward signal design" philosophy provides a reference for no-reference reward function design in DRL-ISP — using a contrastive loss in place of statistical metrics such as NIQE/BRISQUE, which is more robust on AI-enhanced images.

### 7.3 RL-Based Camera Exposure Control Papers

**Automatic Exposure in the Wild (Liu et al., 2020):**
Models the automatic exposure problem as RL, using the error between a target luminance and the current luminance as the reward, deployed on real camera hardware (Sony IMX586). Key finding: RL-based AE responds faster than a traditional PI controller in rapidly changing scenes (quickly moving between bright and dark areas), but converges more slowly in static scenes (the RL policy is not sufficiently "aggressive").

**CAMCtrl (Wu et al., 2023):**
Uses a large language model as a camera parameter controller, mapping user intent ("make it a bit brighter") to camera parameter adjustments, combined with RL fine-tuning to improve instruction execution accuracy. This represents the convergence trend of LLM + RL in the domain of ISP parameter control.

---

## §8 Glossary

**DRL-ISP (Onzon et al., CVPR 2021)**
Deep Reinforcement Learning for ISP: models ISP parameter optimization as a sequential decision-making problem; a policy network $\pi_\theta(a|s)$ selects action $a_t$ from a 51-tool ISP action space based on the current image state $s_t$, trained with the object-detection mAP increment (Equation 1) as the reward signal. The representative work (Onzon et al., CVPR 2021) achieves a mAP@0.50 improvement from 33.8% to 36.5% (+2.7 pp) on YOLO object detection. Its core technical value: the reward function can be any measurable non-differentiable metric, removing the requirement for an end-to-end differentiable ISP pipeline.

**Unpaired CycleR2R (Inverse ISP Data Synthesis)**
A method for synthesizing simulated RAW data from unpaired sRGB images using cycle consistency: two mutually inverse networks, $G_{s2r}$ (sRGB→RAW) and $G_{r2s}$ (RAW→sRGB), are jointly optimized via an adversarial loss combined with a cycle-consistency loss ($G_{r2s}(G_{s2r}(x_\text{srgb})) \approx x_\text{srgb}$). No paired RAW–sRGB data is required; each domain's images are collected independently. In DRL-ISP, CycleR2R is used to convert large sRGB datasets (COCO) into simulated RAW for training. Its inherent limitation: the noise statistics of the simulated RAW differ from those of real sensors (domain shift), causing the policy performance on real RAW to degrade by approximately 3–5%.

**ISP Toolbox**
The discrete action space defined in DRL-ISP: composed of atomic ISP parameter adjustment operations (e.g., brightness +5%, color temperature −100 K, sharpening +0.1), where each "tool" corresponds to an independently executable parameter adjustment. Toolbox design principles: atomicity (single effect per tool), reversibility (forward and inverse actions always paired), step-size gradation (coarse + fine), and prior constraints (parameter boundaries). The 51-tool action space (Onzon et al.) is a typical scale for object-detection optimization scenarios; for perceptual tuning scenarios, the toolbox must be extended to include more tools related to color and Gamma curves.

**Policy Gradient (PPO / SAC)**
Optimization methods used to train policy networks in reinforcement learning. PPO (Proximal Policy Optimization) constrains the policy update step size via a clipped surrogate objective function, yielding stable training well suited to the small-batch-sample regime of ISP optimization. SAC (Soft Actor-Critic) maximizes the sum of expected reward and policy entropy, encouraging exploration and preventing premature convergence to local optima in the ISP parameter space. DRL-ISP predominantly uses PPO because the ISP toolbox constitutes a discrete action space, which PPO handles natively.

**Perceptual–Task Pareto Trade-off**
An inherent trade-off in ISP optimization between human perceptual image quality (PSNR / LPIPS / MOS) and machine-vision task performance (mAP / mIoU): the ISP parameters that maximize detection mAP (high contrast, strong edge enhancement) are generally not perceptually optimal (over-sharpened details, color distortion), and vice versa. By adjusting the hybrid reward weight $\lambda$, different operating points can be generated that together form a Pareto Frontier. In consumer photography scenarios (humans capturing and viewing images), the operating point should lean toward the perceptual side; in autonomous driving and surveillance scenarios (machines viewing images), it should lean toward the task side.

**Evolutionary Algorithm ISP Search (CMA-ES)**
Covariance Matrix Adaptation Evolution Strategy: a gradient-free black-box optimization algorithm that maintains a mean and covariance matrix over the parameter distribution, iteratively generates a "population" of candidate solutions, and updates the distribution based on evaluation results. In ISP parameter optimization, CMA-ES evaluates the reward (mAP / PSNR) for each parameter set and adaptively shifts the search distribution toward high-quality parameter regions. Compared with DRL, CMA-ES requires no policy network training and is straightforward to implement; however, each evaluation requires a complete ISP execution, making its sample efficiency roughly $10\times$ lower than RL. In practice CMA-ES is commonly used for offline global parameter search, while RL is used for online fine-tuning.

**Sim-to-Real Gap**
The discrepancy in statistical properties between simulated data (e.g., simulated RAW synthesized by inverse ISP) and real collected data (real camera RAW), which causes the policy / model trained on simulated data to degrade in performance on real data. Sources: non-uniform gain, fixed-pattern noise (FPN), ADC nonlinearity, and other real-sensor characteristics that cannot be fully reproduced by inverse ISP. Mitigation strategies: Domain Randomization (randomly perturbing simulated data statistics during training), Domain Adaptation (fine-tuning the policy network on a small amount of real RAW), and improving inverse ISP accuracy (replacing CycleR2R with InvISP, which narrows the Sim-to-Real gap by approximately 2–3 dB PSNR).

**Offline Tuning vs. Online Adaptation**
Two deployment modes for ISP parameter optimization. **Offline tuning:** during the R&D phase, DRL or evolutionary algorithms search for optimal parameters across large volumes of scene data, and the results are consolidated into a set of scene-specific ISP Profiles (e.g., daytime / nighttime / HDR); at runtime, AI scene recognition invokes the matching profile — the mainstream approach of manufacturers such as Huawei and OPPO, where parameter optimization is completed during R&D and adds no on-device computational overhead. **Online adaptation:** the device runs a lightweight policy network in real time and dynamically adjusts parameters based on the current scene — faster response and stronger adaptability, but requires NPU support for lightweight RL inference (approximately 2–5 ms per frame), making it an important direction for the next generation of AI ISP.

---

## References

[1] Onzon, E., Mannan, F., Fathima, N., Zhang, N., & Heide, F. (2021). Neural Auto-Exposure for High-Dynamic Range Object Detection. In *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 2021. arXiv:2104.01906.

[2] Tseng, E., Yu, F., Yang, Y., Mannan, F., Tok, K., Nowrouzezahrai, D., ... & Heide, F. (2019). Hyperparameter optimization in black-box image processing using differentiable proxies. *ACM Transactions on Graphics (SIGGRAPH)*, 38(4), 1–14. — A differentiable proxy model approach for ISP black-box hyperparameter optimization, complementary to DRL-ISP from the gradient-based direction.

[3] Hansen, N., & Ostermeier, A. (2001). Completely derandomized self-adaptation in evolution strategies. *Evolutionary Computation*, 9(2), 159–195. — The original CMA-ES paper; the foundational tool for gradient-free global ISP parameter search.

[4] Schulman, J., Wolski, F., Dhariwal, P., Radford, A., & Klimov, O. (2017). Proximal policy optimization algorithms. *arXiv preprint arXiv:1707.06347*. — The PPO algorithm; the primary reinforcement learning algorithm for training the DRL-ISP policy network, stable and sample-efficient.

[5] Fan, Q., Chen, D., Yuan, L., Hua, G., Yu, N., & Chen, B. (2022). Decouple learning for parameterized image operators. *Proceedings of the European Conference on Computer Vision (ECCV)*, 69–84. — A parameter-decoupling method for ISP parameter learning, providing a theoretical basis for parameter independence in DRL-ISP toolbox design.

[6] Robidoux, N., Yu, M., Florez-Arango, J. L., & Brown, M. S. (2021). End-to-end high dynamic range camera pipeline optimization. *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 9712–9720. — End-to-end HDR camera pipeline optimization; complementary work to DRL-ISP in the joint ISP–CV optimization direction.

[7] Onzon, E., et al. "Neural Auto-Exposure," CVPR 2021. — The representative DRL-ISP work; uses object-detection mAP increment as the reward; YOLO mAP@0.50 improves from 33.8% to 36.5%.

[8] Christiano, P., et al. "Deep reinforcement learning from human preferences," NeurIPS 2017. — The foundational RLHF paper; the reward model training methodology is transferable to ISP perceptual quality modeling.

[9] Liu, T., et al. "Automatic Exposure in the Wild: Learning Scene Luminance for Camera Exposure," ECCV 2020. — Industrial application of RL for camera exposure control; validated on real Sony sensors.

[10] Haarnoja, T., et al. "Soft Actor-Critic: Off-Policy Maximum Entropy Deep Reinforcement Learning with a Stochastic Actor," ICML 2018. — The SAC algorithm; the recommended RL algorithm for continuous-action ISP optimization; maximum-entropy RL prevents the policy from premature convergence.

[11] Finn, C., Abbeel, P., & Levine, S. "Model-Agnostic Meta-Learning for Fast Adaptation of Deep Networks (MAML)," ICML 2017. — The meta-learning framework; provides the theoretical basis for cross-scene fast adaptation of ISP parameter optimization using meta-RL.

---

## Chapter Summary

DRL-ISP models ISP parameter optimization as a Markov decision process and applies reinforcement learning (PPO / SAC) to search for the optimal parameter policy within a discrete or continuous ISP tool action space, using non-differentiable metrics such as object-detection mAP as the reward. The representative work (Onzon et al., CVPR 2021) achieves a 2.7 pp mAP improvement on object detection (33.8% → 36.5%). Its core technical value lies in breaking the requirement for end-to-end differentiability, permitting arbitrary measurable metrics — including human subjective scores via RLHF — to serve as optimization objectives. The mainstream engineering deployment mode is **offline tuning + scene-specific ISP Profiles**: DRL / CMA-ES searches for optimal parameters during R&D, and the corresponding profile is invoked at runtime by AI scene recognition, introducing no online RL computation overhead. The principal limitations are the Sim-to-Real Gap of the inverse ISP (constrained by simulated RAW quality) and the perceptual–task trade-off (the mAP-optimal ISP is not necessarily the perceptually optimal one). Future directions include meta-reinforcement learning (fast cross-scene adaptation) and large-model reward modeling (replacing manual MOS annotation with perceptual scores from vision–language models as reward signals).

**Related chapters:** This chapter forms a complementary triangle with Volume 5, Chapter 3 (LLM-Driven ISP Tuning), Volume 3, Chapter 17 (Generative RAW-to-RGB), and Volume 4, Chapter 6 (Task-Aware ISP): RL optimizes discrete parameters, LLM provides semantic guidance, and generative models supply high-quality synthetic data.
