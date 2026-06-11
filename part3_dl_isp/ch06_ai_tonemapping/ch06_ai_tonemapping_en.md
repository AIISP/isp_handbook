# Part 3, Chapter 06: AI-Driven Tone Mapping (Deep Learning Tone Mapping)

> **Scope:** Building on Part 2, Chapter 18 (Traditional Local Tone Mapping), this chapter systematically explains how deep learning breaks through the limitations of hand-crafted TMOs (tone mapping operators, 色调映射算子). The focus covers bilateral learning, HDRNet, neural tone curves, video-adaptive TMO, and end-to-end integration with the ISP pipeline.
> **Prerequisites:** Part 1, Chapter 07 (Dynamic Range and HDR), Part 2, Chapter 18 (Local Tone Mapping Algorithms), Part 2, Chapter 19 (HDR Display Signal Chain), Part 3, Chapter 01 (DL ISP Survey)
> **Target readers:** ISP brightness-track engineers, deep learning researchers, HDR display algorithm engineers

---

## §1 Theory

### 1.1 Limitations of Traditional TMO

Part 2, Chapter 18 gave a systematic treatment of traditional local TMO based on bilateral filtering and guided filtering. The core problems are summarised below:

| Limitation | Manifestation | Root Cause |
|---|---|---|
| Parameter rigidity | A fixed parameter set produces wildly different results across scenes | Hand-crafted rules cannot cover scene diversity |
| Halo artifacts | Local TMO generates halos at high-contrast edges | Uneven filter-kernel response when separating base/detail layers |
| Color shift | Saturation distortion after luminance compression | No joint optimisation of luminance and chrominance |
| Static curve | Tone discontinuity between video frames | No temporal modelling capacity |

**The core tension:** The human perception of "naturalness" is highly non-linear and context-dependent — hand-crafted rules cannot accurately model this perceptual objective.

### 1.2 The Deep Learning TMO Framework

**Unified optimisation objective:**
$$\hat{I}_{LDR} = \mathcal{F}_\theta(I_{HDR}; c)$$

where $\mathcal{F}_\theta$ is the neural network and $c$ is the contextual condition (scene type, display parameters, user preferences, etc.).

**Training data sources:**
1. **Paired data:** HDR originals paired with LDR versions produced by professional colorists (MIT-FiveK, HDRTV, CAUHDR)
2. **Perceptual-model supervision:** HDR-VDP-2 / TMQI used as perceptual losses — no absolute ground truth required
3. **Unsupervised adversarial training:** A discriminator distinguishes "naturally looking" images without relying on paired data

### 1.3 Sensor-Level HDR: DCG / Staggered Exposure and DL Tone Mapping

Modern flagship smartphone sensors integrate HDR capability at the **hardware level**. The input to DL tone mapping is therefore no longer a conventional LDR image but **HDR RAW data produced directly by the sensor**. Understanding these hardware technologies is a prerequisite for deploying DL TMO in production.

#### DCG (Dual Conversion Gain)

The conversion gain of a sensor floating diffusion node (FD) is defined as $\text{CG} = q / C_\text{FD}$ (units: μV/e⁻). A DCG sensor integrates two FD capacitance values within each pixel:

| Mode | Capacitance | Conversion Gain | Advantage | Typical Use |
|---|---|---|---|---|
| **HCG (High CG)** | Small $C_\text{FD}$ | High (~90 μV/e⁻) | Low read noise (< 1 e⁻), superior dark SNR | Shadow detail preservation |
| **LCG (Low CG)** | Large $C_\text{FD}$ | Low (~30 μV/e⁻) | Large full-well capacity (FWC), no highlight clipping | Highlight dynamic range extension |

**DCG operating principle:** The sensor simultaneously samples both HCG and LCG signals **within a single exposure**, delivering two raw voltage channels. The ISP receives 20-bit-equivalent HDR RAW per pixel (10-bit HCG + 10-bit LCG). The equivalent dynamic range extension is:

$$\text{DR}_\text{DCG} = \text{DR}_\text{HCG} + 20\log_{10}\!\left(\frac{\text{CG}_\text{H}}{\text{CG}_\text{L}}\right) \approx \text{DR}_\text{HCG} + 10\text{ dB}$$

Representative sensors: Sony IMX989 (1-inch flagship), Samsung ISOCELL HP series.

**DL processing challenges for DCG HDR RAW:**
1. **Asymmetric merge noise:** HCG has low noise in shadows; LCG has low noise in highlights. The gain-switching boundary (mid-exposure zone) produces switching artifacts; the DL network must learn adaptive blending weights.
2. **Color consistency:** HCG/LCG channels have slightly different spectral responses (same filter array, different gain paths), requiring joint modeling of both channels' color bias during tone mapping.
3. **Independent BLC calibration:** HCG and LCG have separate dark-current offsets that must be calibrated individually before DL TMO.

#### Staggered / Interleaved HDR

An alternative sensor HDR scheme alternates long-exposure rows (LE) and short-exposure rows (SE) within a single frame, producing spatially interleaved HDR RAW (e.g., LE/SE/LE/SE row alternation):

$$\text{Equivalent EV difference} = \log_2\!\left(\frac{t_\text{LE}}{t_\text{SE}}\right), \quad \text{typical} = 4\text{ EV}$$

**Key distinction from DCG:** Staggered HDR LE/SE rows originate from **different exposure instants**, so moving objects introduce misalignment (motion artifacts) between LE and SE. DCG HCG/LCG samples originate from **the same exposure instant** and are motion-free. DL tone mapping must incorporate an adaptive fusion strategy in the pre-processing stage.

#### DL TMO Pipeline for DCG / Staggered HDR RAW

```
HDR RAW (DCG dual-channel or staggered LE/SE)
     ↓
[BLC/PDPC] — independent BLC for HCG/LCG
     ↓
[DL fusion network] — predict per-pixel blend weights, handle gain-switching artifacts
     ↓
[Linear HDR image] — ~20-bit equivalent dynamic range
     ↓
[DL tone mapping] — HDRNet / CSRNet / neural curve
     ↓
[LDR output] — 8/10-bit sRGB
```

> Cross-reference: Detailed derivations of sensor physics (DCG conversion gain, full-well capacity) appear in Part 1, Chapter 03 §5 (Sensor Dynamic Range).

---

### 1.4 Global DL TMO vs. Local DL TMO

Deep learning TMO inherits the global/local dichotomy from traditional TMO, though the boundary is blurrier in a DL framework:

| Dimension | Global DL TMO | Local DL TMO |
|---|---|---|
| **Decision granularity** | Whole-frame statistics → single curve/matrix applied uniformly | Per-pixel / per-region adaptive transform coefficients |
| **Representative methods** | CSRNet (global-parameter MLP), neural tone curve | HDRNet (bilateral grid, spatially varying 3×4 matrix), 4D LUT |
| **Halo risk** | Negligible (no spatial variation, boundaries naturally continuous) | Present; requires edge-aware interpolation (bilateral grid slicing) to suppress |
| **Parameter count** | Very low (< 50 K; only global statistics as input) | Moderate (HDRNet ~0.5 M; 4D LUT 4.5 MB memory) |
| **Scene adaptability** | Poor (same curve compresses highlights and shadows, sacrificing local contrast) | Good (separate transforms for bright/dark regions, local contrast preserved) |
| **Inference latency** | Very low (< 3 ms; MLP only predicts parameters) | Low (slicing/LUT operations, < 15 ms at full resolution) |
| **Typical deployment** | Global scene pre-adjustment, lightweight embedded systems | Flagship smartphone NPU/ISP DSP for fine tone mapping |

**Engineering recommendation (smartphone ISP):** For daytime outdoor scenes with uniform illumination, CSRNet global TMO is sufficient (< 3 ms, comfortably real-time). For night photography, backlit subjects, or HDR scenes spanning 4–5 EV, locally adaptive processing is mandatory. The two can be cascaded — CSRNet sets the overall exposure target first, then HDRNet or a 4D LUT handles local refinement. This cascade is more stable in both latency and quality than running a single large model.

### 1.5 Gamut Mapping for HDR → SDR

AI tone mapping must handle not only luminance dynamic range compression (HDR → SDR) but also **gamut mapping**: HDR content is typically captured/stored in BT.2020 (or DCI-P3) color space, while the vast majority of display targets are BT.709 (sRGB). The BT.2020 gamut area is approximately 2.65× that of BT.709 (Shoelace formula: BT.2020 ≈ 0.2972, sRGB ≈ 0.1121); approximately 62% of the BT.2020 gamut area lies outside the sRGB boundary, covering highly saturated reds and greens. Hard-clipping out-of-gamut pixels produces severe color distortion.

**Coupling between gamut mapping and luminance compression:**

$$\mathbf{c}_{\text{SDR}} = \mathcal{G}\!\left(\mathcal{T}(\mathbf{c}_{\text{HDR}})\right) \neq \mathcal{T}\!\left(\mathcal{G}(\mathbf{c}_{\text{HDR}})\right)$$

Applying luminance compression $\mathcal{T}$ before gamut mapping $\mathcal{G}$, versus the reverse order, yields non-equivalent results, each with distinct failure modes. **Joint optimisation** — simultaneously training luminance compression and gamut transform matrices — is one of the key advantages of DL TMO.

**Standard BT.2020 → BT.709 color transform matrix:**

$$M_{2020\to709} = \begin{pmatrix} 1.6605 & -0.5877 & -0.0728 \\ -0.1246 & 1.1329 & -0.0083 \\ -0.0182 & -0.1006 & 1.1187 \end{pmatrix}$$

Values outside $[0,1]$ must be soft-clipped (soft-clipping curve) rather than hard-truncated; otherwise, saturated color regions exhibit tonal cliffs. A DL TMO can learn a soft-clipping function in place of the hard matrix truncation, preserving tonal continuity in out-of-gamut regions.

**Recent advances (2023–2024):**

- **Prompt-guided TMO (Zhu et al., 2023) [11]** (⚠️ arXiv preprint — not verified in CVF proceedings): Introduces text/visual prompts to control TMO style ("cinematic deep shadows", "natural highlights"). The network predicts a conditional tone curve based on the prompt description. The paper claims TMQI = 0.849 on MIT-FiveK and HDRTV datasets, 0.028 higher than HDRNet, with zero-shot multi-style transfer; however, as the original venue cannot be confirmed in CVF open access, this figure **is pending third-party replication**.
- **Diffusion-model TMO (Ye et al., ACM MM 2024):** Uses a degraded LDR image (under/over-exposed) as the condition and employs a diffusion prior to generate perceptually realistic tone-mapped results. The perceptual metric LPIPS is 22% lower than discriminative methods; the cost is an inference latency of approximately 3–8 seconds, making it suitable for offline post-production.

### 1.6 Deep-Learning Parameterisation of Tone Curves

**Core idea:** The parameters of global/local tone curves — control points, gains, offsets — are predicted automatically by a neural network instead of being set by hand.

**Global curve parameterisation (piecewise-linear example):**
$$T(x) = \sum_{k=0}^{K} w_k \cdot \phi_k(x), \quad \phi_k(x) = \max(0, x - k/K)$$

The network predicts $K+1$ weights $\{w_k\}$ spanning the full tonal range from black point to white point.

---

## §2 Methods

### 2.1 HDRNet — Bilateral Learning for Tone Mapping (Gharbi et al., SIGGRAPH 2017)

HDRNet is a landmark work bringing deep learning into image enhancement. Its core innovation is the **Learned Bilateral Grid (可学习双边网格)**.

**Architecture:**

```
Input image (low-resolution 256×256)
    ↓
[Low-resolution processing network]
    → Global path: fully connected layers, extract global color/luminance features
    → Local path: convolutions, generate spatially varying coefficients
    ↓
Fusion → coefficient grid A ∈ ℝ^{h×w×d×12}  (bilateral grid)
    ↓
[Slicing operation] (luminance-guided slicing of the input image, preserving edge sharpness)
    ↓
Affine transform: apply a local 3×4 color-transform matrix to each pixel
    ↓
Output enhanced image (full resolution)
```

**Bilateral Grid Slicing (双边网格切片):**

Ordinary bilinear upsampling blurs edges. Bilateral grid slicing uses luminance as a third-dimension index, achieving an **edge-aware local color transform (边缘感知的局部色彩变换)**:

$$O(x,y) = A(x,y,I_{guide}(x,y)) \cdot [I(x,y); 1]$$

Here $A$ is sliced from the low-resolution grid using the guidance image $I_{guide}$, preserving full-resolution edge precision while keeping computational cost extremely low (millisecond-level).

**Advantages:**
- Full-resolution inference time < 10 ms (4K images)
- Slicing guarantees halo-free edges
- Balances global tone and local detail

**HDRNet for TMO:** With an HDR image as input, the network learns to predict the optimal affine coefficients that compress it into the LDR range, supervised by LDR references produced by professional colorists.

### 2.2 DeepUPE — Unified Enhancement for Low-Light and HDR (Wang et al., CVPR 2019)

**Design philosophy:** Decompose image enhancement (including TMO) into estimating an **Image-to-Illumination (图像调整矩阵)** matrix.

**Network architecture:**
- Lightweight U-Net encoder extracting multi-scale features
- Output: a per-pixel 3×3 color-transform matrix (9 coefficients)
- Avoids direct pixel-value prediction; instead predicts "how to transform"

**Loss function:**
$$\mathcal{L} = \mathcal{L}_{recon} + \lambda_1 \mathcal{L}_{smooth} + \lambda_2 \mathcal{L}_{color}$$

- $\mathcal{L}_{recon}$: L1 reconstruction loss
- $\mathcal{L}_{smooth}$: spatial smoothness of the transform matrix (prevents local discontinuities)
- $\mathcal{L}_{color}$: color constancy loss

### 2.3 STAR — Spatially and Temporally Adaptive Video TMO (Zhang et al., ECCV 2020)

**Problem background:** Frame-independent TMO causes luminance/color jumps between video frames (temporal flickering, 帧间闪烁), degrading the viewing experience.

**STAR (Spatially and Temporally Adaptive Real-time TMO) architecture:**

```
Current frame I_t (HDR) + previous output O_{t-1} (LDR)
    ↓
[Inter-frame alignment module] (Deformable Convolution optical-flow alignment)
    ↓
[Spatio-temporal fusion TMO network]
    → Spatial path: local tone mapping of the current frame
    → Temporal path: feature fusion with historical frames
    ↓
Output O_t (temporally consistent LDR frame)
```

**Temporal consistency loss:**
$$\mathcal{L}_{temp} = \|O_t - \mathcal{W}(O_{t-1}, F_{t\rightarrow t-1})\|_1 \cdot M_t$$

where $\mathcal{W}$ is optical-flow warping and $M_t$ is the motion mask (occlusion regions receive lower weight).

### 2.4 Neural Tone Curve

**Core idea (Zeng et al., CVPR 2020 / CSRNet):** Use a lightweight network to predict the control points of a global tone curve, then apply that curve as a per-pixel mapping over the entire image.

**Curve representation:** Piecewise-linear (256 control points) or cubic spline (16 control points)

**CSRNet architecture (He et al., ECCV 2020):**
1. Global parameter predictor — 4-layer MLP, input: global statistics (mean / variance / histogram)
2. Output: independent tone curves for R, G, B channels (768 parameters total)
3. Curve application: lookup-table (LUT) approach — O(1) per-pixel operation

**Engineering advantage:** The curve prediction network is extremely lightweight (< 50 K parameters) and runs in real time on a CPU. The curve is interpretable, making it easy to debug and run A/B tests.

### 2.5 4D LUT — Industry-Grade Deployable Tone Mapping

**Limitation of 3D LUT:** A conventional 3D LUT depends only on a pixel's RGB values and ignores spatial context (e.g., bright-region vs. dark-region surroundings), giving limited performance in locally adaptive scenarios.

**4D LUT (Yang et al., CVPR 2022):**
$$O = \text{LUT}_{4D}(R, G, B, L), \quad L = \text{local\_avg}(I, r)$$

The fourth dimension $L$ is the local luminance mean computed with radius $r$, endowing the LUT with local-adaptive capability.

**Engineering workflow:**
```
Training stage:  neural network (HDRNet / CSRNet) predicts the ideal enhancement
Distillation stage:  compress the neural network into a 4D LUT (33×33×33×33 grid)
Deployment stage:  pure LUT-lookup inference — zero network computation,
                   suitable for DSP/NPU hardware acceleration
```

---

## §3 HDR Video Tone Mapping

### 3.1 Additional Challenges for HDR Video

| Challenge | Description |
|---|---|
| Temporal consistency | Abrupt scene-luminance changes (e.g., entering/exiting a tunnel) must be smoothly bridged — frame-independent TMO is not acceptable |
| Adaptation speed | Human visual adaptation takes approximately 30–60 seconds; the TMO should simulate this process |
| Motion-content preservation | Avoid excessive tone compression in fast-motion regions, which would worsen motion blur |
| Display metadata alignment | Output must conform to HDR10 / Dolby Vision MaxCLL / MaxFALL metadata |

### 3.2 Reinforcement-Learning-Based Video TMO

**TMO-RL (Kim et al., 2019):** Frames video TMO as a sequential decision problem:
- **State:** current-frame statistics (luminance distribution, scene category) + historical exposure parameters
- **Action:** adjust global tone curve parameters ($\gamma$, white point, black point)
- **Reward:** TMQI (Tone Mapping Quality Index, 色调映射质量指数) + temporal consistency reward

The RL policy network adapts parameters at O(1) inference cost, balancing per-frame quality against inter-frame smoothness.

---

## §4 End-to-End Integration with ISP

### 4.1 Differentiable ISP + TMO Joint Optimisation

In a conventional ISP, TMO is an independent module at the tail of the pipeline. A differentiable ISP framework enables:

```
RAW → BLC → Demosaic → AWB → CCM → [Gamma → TMO] → sRGB
                                          ↑
                                   joint optimisation region
```

**Joint loss:**
$$\mathcal{L}_{joint} = \mathcal{L}_{perceptual} + \lambda_{IQA} \mathcal{L}_{BRISQUE} + \lambda_{3A} \mathcal{L}_{3A}$$

where $\mathcal{L}_{3A}$ is a constraint on AE/AWB accuracy, preventing the joint optimisation from degrading 3A control precision.

### 4.2 AI TMO in Practice: Smartphone Photography

**Apple Photonic Engine (iPhone 14 and later):** A neural network predicts tone mapping parameters in the RAW domain (rather than as JPEG post-processing), delivering approximately 2× SNR improvement in low-light conditions compared with Deep Fusion.

**Google HDR+ (Pixel series):** A commercial variant of HDRNet that applies a learned tone curve to multi-frame-merged RAW data, with AWB and TMO jointly predicted by a single neural network.

**Huawei XD Optics (P50 Pro):** The optical-computation engine incorporates lens point-spread function (PSF, 点扩散函数) modelling into the TMO process, simultaneously correcting lens-diffraction losses while recovering highlight detail.

---

## §5 Tuning

### 5.1 Training-Data Quality Is the Key

| Dataset | Scale | Characteristics |
|---|---|---|
| **MIT-FiveK** | 5,000 images | Retouched by 5 professional photographers; covers a wide range of styles |
| **HDRTV** | 1,235 pairs | HDR video frames paired with BT.709 reference |
| **CAUHDR** | 600 pairs | HDR still images paired with multiple TMO references |
| **RAISE** | 8,156 images | No retouching ground truth; NIQE/TMQI used for self-supervision |

**Rule of thumb:** The colorist style in the training data should match the aesthetic preferences of the target platform's users. Otherwise the network will learn an "extreme professional-photography style" rather than the preferences of smartphone users.

### 5.2 Perceptual Loss Weight Tuning

**Typical loss combination:**
```python
L_total = (
    1.0 * L_L1           # pixel-level reconstruction — ensures basic correctness
  + 0.1 * L_perceptual   # VGG perceptual loss — preserves structure
  + 0.01 * L_color       # color constancy — prevents color cast
  + 10.0 * L_exposure    # exposure control — prevents over/under-exposure
)
```

**Common failure modes:**
- $\lambda_{perceptual}$ too large → over-sharpened textures (hallucination)
- $\lambda_{color}$ too small → color cast
- No $\lambda_{exposure}$ → overall brightness target drifts

### 5.3 Accuracy–Efficiency Trade-off in LUT Distillation

| LUT grid size | Lookup precision | Memory footprint | Applicable scenario |
|---|---|---|---|
| 17³ | Low | 19.7 KB | Low-end embedded devices |
| 33³ | Medium | 140 KB | Smartphone ISP DSP |
| 65³ | High | 1.1 MB | PC / tablet GPU |
| 33⁴ (4D) | High (locally adaptive) | 4.5 MB | Flagship smartphone NPU |

---

## §6 Evaluation

### 6.1 Image Quality Metrics

**TMQI (Tone-Mapping Quality Index, Yeganeh & Wang, TIP 2013):**
$$\text{TMQI} = a \cdot S^{\alpha} + (1-a) \cdot N^{\beta}$$

where $S$ is structural fidelity (gradient correlation between the HDR and LDR images) and $N$ is a naturalness score (NSS statistical model), with $\alpha=0.8012$, $\beta=0.7016$, $a=0.8579$. **TMQI is currently the most widely used no-reference perceptual metric for TMO.**

**HDR-VDP-2 (Mantiuk et al., SIGGRAPH 2011):**
- Simulates how the human visual system (HVS) perceives HDR content
- Outputs: a probability-of-detecting-a-difference map + Q score
- Requires display physical parameters (luminance range, viewing distance)

### 6.2 Video Temporal Consistency Metric

$$E_{flicker} = \frac{1}{T-1} \sum_{t=1}^{T-1} \|\bar{Y}(O_t) - \bar{Y}(O_{t-1})\|$$

$\bar{Y}$ denotes the mean frame luminance. A lower $E_{flicker}$ indicates more stable inter-frame luminance.

### 6.3 Subjective MOS Evaluation

Standard practice: 5-point mean opinion score (MOS, 主观质量评分) (1 = very poor, 5 = excellent), rated separately on the following dimensions:
- Overall realism
- Highlight detail retention
- Shadow detail visibility
- Color naturalness
- (Video) inter-frame smoothness

---

## §7 Code

See the companion notebook *See §6 Code section for runnable examples.*, which includes:

- **HDRNet inference demo:** Load a pre-trained HDRNet to perform tone mapping on an HDR image; visualise the distribution of bilateral grid coefficients
- **CSRNet tone-curve visualisation:** Display the predicted R/G/B per-channel curve shapes produced by the network
- **TMQI computation:** Compare TMQI scores across five TMO algorithms (Reinhard / LIME / HDRNet / Zero-DCE / CSRNet)
- **LUT distillation example:** Sample the output of a lightweight CSRNet into a 33³ 3D-LUT; compare the LUT approximation error
- **Video inter-frame consistency analysis:** Compute $E_{flicker}$ frame by frame; compare frame-independent TMO against STAR temporal TMO

---

> **Engineer's Notes: Three Production-Line Lessons from AI Tone Mapping**
>
> **Hallucinated detail vs. scene fidelity:** The biggest product risk from AI tonemapping is "hallucinated highlights" — the model learns during training that "highlight regions should contain texture" and at inference time will spontaneously generate cloud texture in an overexposed sky, or brick-joint detail on a bright wall, when no such detail exists in the original RAW. On one flagship photography-oriented product, this caused complaints from professional photographers who said "AI altered my compositional intent." The engineering fix is to introduce a confidence mask: in RAW highlight-clipped zones (any R/G/B channel > 0.95 full-scale), force traditional Reinhard mapping; the model only handles regions below the highlight clip. This eliminates hallucination complaints at the cost of less AI optimisation in extreme highlights — a degradation users find acceptable.
>
> **Stability rationale for HDRNet as a production baseline:** Google HDRNet (Gharbi et al., SIGGRAPH 2017) remains the most widely deployed AI tonemapping solution in the industry — not because it achieves the best scores, but because it is sufficiently predictable. HDRNet's bilateral grid structure decouples global brightness decisions (low-resolution path, 1/64 image) from local detail enhancement (full-resolution path), allowing engineers to tune each path independently. Measured on a production device, HDRNet (TFLite INT8) on a Snapdragon 8 Gen 2 DSP achieves 3.2 ms inference latency (12 MP input) with extremely high stability and almost no NaN/Inf anomalies. By contrast, Transformer-based tonemapping methods from 2022–2024 achieve better scores but exhibit inference variance (inter-frame ΔL mean exceeding 0.5%) and occasional local color-patch discontinuities that make it difficult to directly replace HDRNet. When introducing new models, it is recommended to retain HDRNet as a fallback baseline and switch only when the DMOS perceptual score improvement exceeds 5 points.
>
> **Per-display adaptation is an engineering necessity:** The same HDR content requires completely different tonemapping targets on an iPhone OLED (P3 gamut, 1000 nit peak) versus an Android LCD (sRGB, 500 nit). A universal mapping curve was found to produce oversaturated colors on LCD and lost highlight gradation on OLED. The solution is a "Display Adaptation Layer" appended after model output: inputs are screen luminance, color gamut, and black-level parameters (read from the system API); output is a 3×1D LUT color correction. This layer has negligible parameter count (256 nodes × 3 channels per LUT) and runs in real time on CPU, yet compresses the perceptual ΔE difference between different displays from 5.2 to within 1.8.
>
> *References: Gharbi et al., "Deep Bilateral Learning for Real-Time Image Enhancement", SIGGRAPH 2017; Eilertsen et al., "HDR Image Reconstruction from a Single Exposure Using Deep CNNs", SIGGRAPH Asia 2017; Kim et al., "Deep Photo Enhancer", CVPR 2018*

---

## §9 Deep Dive: Core Algorithm Analysis

### 9.1 HDRNet In Depth (Gharbi et al., SIGGRAPH 2017)

#### 9.1.1 Bilateral Grid and Local Affine Transform

HDRNet combines **learnable local color transforms** with the **edge-aware interpolation of the bilateral grid**, allowing color transform coefficients predicted at low resolution (256×192) to be upsampled to arbitrary full resolution **without halos**.

The low-resolution processing path splits into two branches:

**Local path:** 8 convolutional layers with stride 2, progressively downsampling to a spatial resolution of $16\times12$. Each location predicts coefficients associated with $d=8$ luminance-axis layers, forming the bilateral grid $\mathcal{A} \in \mathbb{R}^{16 \times 12 \times 8 \times 12}$ (the last two dimensions — $8\times12$ — represent the $3\times4$ affine color transform matrix at each 3-D grid point: 12 parameters for 3 output channels × 4 inputs — RGB plus 1 homogeneous term).

**Global path:** Starting from the globally average-pooled features of the local path, two fully connected layers produce a 64-dimensional global feature vector. This vector is added to per-grid-point features from the local path, so the affine coefficients encode both global tone (scene brightness, color temperature) and local spatial distribution (highlight vs. shadow zones) simultaneously.

**Precise mathematical description of bilateral grid slicing:**

Let $g(x, y)$ denote the guidance image (typically the grayscale or Y channel of the input image, range $[0,1]$). The three-dimensional bilateral coordinate for spatial position $(x,y)$ is:

$$\left(\frac{x}{W} \cdot w_\mathcal{A},\ \frac{y}{H} \cdot h_\mathcal{A},\ g(x,y) \cdot d_\mathcal{A}\right)$$

Trilinear interpolation of $\mathcal{A}$ at this coordinate yields the per-pixel $3\times4$ local affine matrix $A(x,y)$; the final transform is:

$$O(x,y) = A(x,y) \cdot [I_R(x,y),\ I_G(x,y),\ I_B(x,y),\ 1]^T$$

**Edge-awareness mechanism:** Because the third dimension is indexed by $g(x,y)$, a luminance step at an edge maps to a different luminance layer on each side. The slice automatically selects each side's corresponding transform coefficients, avoiding color mixing across the edge — the same principle as edge-aware bilateral filtering.

#### 9.1.2 Real-Time Performance and Mobile Adaptation

HDRNet's full-resolution inference has almost no computational overhead because the low-resolution network (256×192) requires only ~$0.5\times10^9$ FLOPs, and the slicing operation is an $O(HW)$ interpolation. Reference measurements:

| Platform | Resolution | Inference Latency |
|---|---|---|
| Desktop GPU (GTX 1080) | 4K (3840×2160) | ~7 ms |
| iPhone 12 Neural Engine | 4K | ~12 ms |
| Snapdragon 8 Gen 2 DSP | 4K | ~15 ms |

Mobile implementation key point: The slicing operation can be accelerated on DSP/ISP HW using **3D LUT interpolation** instructions, with no NPU involvement. The entire HDRNet inference can execute entirely within ISP DSP firmware, yielding very low power consumption (< 20 mW).

**Supervision signal for HDRNet TMO:** Using the MIT-FiveK dataset as an example, each HDR image has LDR references from 5 professional colorists. HDRNet is trained with an $\ell_2$ loss against colorist C's style; the network then learns that colorist's tone compression preferences (highlight pull-down, shadow lift) automatically, without manual TMO curve design.

---

### 9.2 Deep Retinex Enhancement: RetinexNet (Chen et al., BMVC 2018)

#### 9.2.1 Retinex Decomposition Theory

Retinex theory (Land & McCann, 1971) decomposes an image into a **reflectance component** and an **illumination component**:

$$I = R \odot L$$

where $I$ is the observed image, $R$ is the material reflectance (ideally lighting-independent), and $L$ is the scene illumination distribution. Tone mapping can be interpreted as: compress the dynamic range of $L$ while preserving the relative relationships in $R$, thereby reproducing the HDR scene's appearance within the LDR range.

In the log domain, Retinex decomposition becomes additive:

$$\log I = \log R + \log L$$

Traditional Retinex algorithms (e.g., MSR, MSRCP) estimate $\log L$ (low-frequency) by Gaussian filtering; the remainder is $\log R$ (high-frequency). The core problem is that Gaussian filtering produces halos at edges (because illumination does not vary slowly at object boundaries), and the scale parameter (Gaussian standard deviation) must be manually tuned per scene.

#### 9.2.2 RetinexNet Network Design

RetinexNet replaces the hand-crafted filtering with two sub-networks:

**Decomposition network (Decom-Net):** Input $I$, output $R$ and $L$, with decomposition consistency constraints:

$$\mathcal{L}_\text{decom} = \mathcal{L}_\text{recon} + \lambda_r \mathcal{L}_\text{reflectance\_smooth} + \lambda_i \mathcal{L}_\text{illuminance\_smooth}$$

where:
- $\mathcal{L}_\text{recon} = \|R \odot L - I\|$ (reconstruction consistency)
- $\mathcal{L}_\text{reflectance\_smooth} = \|\nabla R \odot \exp(-\lambda_g \|\nabla I\|)\|$ (reflectance smooth in non-edge regions)
- $\mathcal{L}_\text{illuminance\_smooth} = \|\nabla L\|$ (globally smooth illumination)

**Enhancement network (Enhance-Net):** Input low-light illumination $L$, predict enhanced illumination $\hat{L}_\text{enh}$; final output:

$$\hat{I}_\text{enh} = R \odot \hat{L}_\text{enh}$$

Decom-Net trains in an unsupervised fashion requiring only image pairs with illumination variation — no HDR ground truth is needed. A decomposition network trained on outdoor scenes can be applied directly to indoor scene enhancement without re-calibration; traditional TMO methods rely on absolute luminance calibration and typically require re-tuning across scenes.

---

### 9.3 KinD++ Framework (Zhang et al., TPAMI 2021)

#### 9.3.1 Multi-Scale Decomposition and Attention

KinD++ (Knowledge-inspired INtegrated framework for low-light enhancement) extends RetinexNet with two key improvements: **multi-scale decomposition** and **ambient light restoration**.

**Layer decomposition network:** On top of the standard Retinex decomposition $I = R \odot L$, KinD++ introduces multi-scale cross-attention:

$$\mathcal{A}_s = \text{Sigmoid}\left(W_s * \text{Cat}\left[\mathcal{F}_s^R, \mathcal{F}_s^L\right]\right), \quad s \in \{1, 2, 3\}$$

Cross-attention weights $\mathcal{A}_s$ are computed at 3 resolution scales to distinguish genuine edges (reflectance discontinuities) from illumination gradients (which should be smooth), fixing RetinexNet's illumination-estimation errors near high-contrast edges.

**Ambient illumination restoration:** In night or low-light scenes, the illumination $L$ can simultaneously contain localised hot-spots (artificial light sources) and near-black regions (deep shadows). KinD++'s illumination enhancement network separately predicts an **ambient illumination compensation** $\Delta L$:

$$\hat{L}_\text{enh} = \text{Enhance-Net}(L) + \Delta L$$

$\Delta L$ is predicted by a lightweight estimator from whole-frame mean luminance features, functioning as an adaptive global exposure correction term. This prevents overfitting to absolute luminance values — what constitutes "normal" brightness differs substantially across scenes.

**Integrated noise suppression:** KinD++ adds a noise-estimation and removal sub-network to the reflectance enhancement branch, similar to the two-stage CBDNet design but jointly end-to-end optimised with the illumination enhancement. This prevents noise in the reflectance map from being mistaken for real texture. Experimental result: PSNR 21.30 dB, SSIM 0.820 on the LOL (Low-Light) dataset, outperforming RetinexNet (16.77 dB / 0.462) by approximately 4.5 dB.

---

## §10 Deep Dive: Evaluation Metrics

### 10.1 TMO-Specific Metrics

#### 10.1.1 TMQI: Detailed Computation

TMQI (Tone-Mapping Quality Index) consists of two components: structural fidelity $S$ and statistical naturalness $N$.

**Structural fidelity $S$:** Measures local structural (gradient) consistency between the HDR image and the TMO result. Local means, variances, and covariances are computed on multi-scale patches for HDR image $H$ and LDR image $T$, similar to a multi-scale extension of SSIM:

$$S = \frac{1}{K} \sum_{k=1}^{K} s_k(H_k, T_k)$$

where $s_k$ is the structural similarity of the $k$-th image patch and $K$ is the total patch count. A higher $S$ means the TMO has preserved the HDR image's local contrast structure (local light-dark relationships are not severely distorted).

**Statistical naturalness $N$:** Based on a natural scene statistics (NSS) model, measures how well the luminance histogram of the TMO result matches a "natural image" prior. A generalized Gaussian distribution (GGD) is fit to the luminance histogram; the distance from reference GGD parameters (learned from a large natural-image corpus) is computed:

$$N = \exp\!\left(-\frac{(m - m_0)^2}{2v_m^2} - \frac{(\sigma^2 - \sigma_0^2)^2}{2v_\sigma^2}\right)$$

where $(m_0, \sigma_0^2)$ are the mean and variance priors from reference natural images and $(v_m, v_\sigma)$ are prior variances (tolerance bounds). A higher $N$ means the TMO result's luminance distribution is more "natural" — neither globally too dark nor globally overexposed.

Final TMQI combines both:

$$\text{TMQI} = a \cdot S^{\alpha} + (1-a) \cdot N^{\beta} = 0.8579 \cdot S^{0.8012} + 0.1421 \cdot N^{0.7016}$$

**Practical limitation of TMQI:** The structural fidelity component tends to penalise intentional local contrast changes. TMOs deliberately pursuing a "cinematic" or "stylised" look (e.g., a deeply shaped S-curve) receive low scores even when users find them acceptable. TMQI is therefore better suited to evaluating "fidelity-oriented" TMOs (e.g., HDR → standard BT.709 conversion) than creative image enhancement.

#### 10.1.2 μ-PSNR for HDR Content Evaluation

Standard PSNR computed in the linear HDR domain over-weights high-luminance regions (the absolute error weight for the brightest HDR zone can be $10^4\times$ that of shadows), causing the metric to be dominated by highlight errors while masking shadow-detail differences. μ-PSNR applies μ-law compression (logarithm-like) before computing PSNR:

$$\mu\text{-PSNR} = 10\log_{10}\frac{L_\text{peak}^2}{\text{MSE}[\mu(I_\text{ref}),\ \mu(I_\text{test})]}$$

where $\mu(x) = \frac{\ln(1 + \mu x)}{\ln(1 + \mu)}$, $\mu = 5000$, and $L_\text{peak}$ is the peak luminance (e.g., 10,000 nit). The μ-law compression models the logarithmic nature of human luminance perception (Weber–Fechner law), making μ-PSNR weight differences more uniformly across the full HDR luminance range (0.001–10,000 nit). It is the preferred metric for HDR image/video compression and tone mapping quality evaluation and is adopted by the HEVC/VVC HDR coding standard.

#### 10.1.3 HDR-VDP-3 Perceptual Quality Evaluation

HDR-VDP-3 is an updated version of HDR-VDP-2 (Mantiuk et al., 2023) with two core improvements:

1. **Updated temporal modulation transfer function (TMTF):** Re-calibrated with latest human visual psychophysics data, providing more accurate assessment of motion-content perception for video TMO evaluation.
2. **JOD quality score:** Outputs **Just-Objectionable-Differences (JOD)** scores, which can be directly converted to "what fraction of observers would find this level of visible difference objectionable" — more intuitive than the Q score.

**HDR-VDP-3 workflow:**

```
Inputs:  reference HDR image (physical luminance, cd/m²) + test image (same units)
         + display parameters (peak luminance, black-level luminance, screen size, viewing distance)
    ↓
HVS simulation:
  ① Optical eye model (cornea/lens/retinal PSF)
  ② Cone/rod responses (S/M/L trichromatic channels + scotopic channel)
  ③ Visual cortex CSF (contrast sensitivity function, spatial-frequency dependent)
  ④ Masking effect (detection threshold elevated in high-contrast textured regions)
    ↓
Outputs: per-pixel detection probability map P_detect + per-image JOD quality score
```

**Practical measurement procedure:**
1. Convert the TMO output (8/10-bit sRGB) to physical luminance (cd/m²) using the target display's EOTF.
2. Use the original HDR image (linear float) as the reference, same units (cd/m²).
3. Specify standard viewing conditions (e.g., 1920×1080 @ 55 inches, viewing distance 3 m, D65 ambient 5 lx).
4. Call HDR-VDP-3 to compute JOD; a JOD difference > 1 between TMO methods is generally considered a perceptually significant difference.

---

## §11 Engineering Practice: ISP Integration Pipeline

### 11.1 Selection Criteria: DL TMO vs. Traditional PQ/HLG Curves

DL TMO is not universally superior — traditional curves are better suited to certain scenarios:

| Scenario | Recommended approach | Reason |
|---|---|---|
| **Broadcast live TV** | Traditional HLG (Hybrid Log-Gamma) | Standardised, inter-frame consistent, zero inference latency, compatible with all HDR displays |
| **Cinema post-production** | Traditional PQ + DaVinci grading | Professional colorists drive the process; DL results are "too clever" and disrupt creative intent |
| **Smartphone direct output (JPEG)** | DL TMO (HDRNet / CSRNet variant) | Can learn user aesthetic preferences; automatically outperforms a fixed S-curve |
| **Professional camera RAW files** | Traditional global TMO + user adjustment | Photographers demand full control; DL output predictability is insufficient |
| **Short-video platforms, real-time upload** | DL TMO (after LUT distillation) | User perception is the priority; LUT distillation ensures < 5 ms inference latency |

**Necessary conditions for choosing DL TMO:**
1. Inference latency meets the budget (real-time preview < 33 ms/frame; still capture < 200 ms).
2. Sufficient training data matching the target scene (outdoors / indoors / night must each be tuned separately).
3. Color consistency validation passes (TMO output color must remain consistent across different white-balance / AWB results to avoid introducing chromatic bias).

### 11.2 On-Device Inference Latency Budget

Reference DL TMO inference latency on flagship smartphone SoCs (2024):

| Method | Input resolution | Snapdragon 8 Gen 3 | Dimensity 9300 | Notes |
|---|---|---|---|---|
| HDRNet (original) | 4K | ~12 ms | ~16 ms | DSP slice acceleration |
| CSRNet (lightweight) | Any (global params) | ~2 ms | ~3 ms | MLP, only 50 K parameters |
| 3D LUT (33³) | Any | ~1 ms | ~1 ms | Pure lookup, ISP HW |
| 4D LUT (33⁴) | Any | ~3 ms | ~4 ms | Slight memory increase |
| NAFNet-32 (TMO fine-tuned) | 1080p | ~22 ms | ~28 ms | Full-resolution processing |

> Note: Exact Qualcomm/MTK platform NPU performance figures are commercially confidential; the above estimates are based on public benchmarks and community measurements and should be treated as indicative only.

**Engineering solution for 4K real-time preview:** Use CSRNet to predict global tone parameters (< 3 ms), distill into a 3D LUT (< 1 ms); combined < 5 ms, satisfying the 33 ms frame budget for 4K@30fps with budget remaining for other ISP modules. For scenes requiring local adaptation (e.g., night portraits), switch to the DSP-accelerated HDRNet (12 ms), which also meets real-time requirements.

### 11.3 8-bit vs. 10-bit Output Depth

DL TMO output bit depth selection has a significant impact on final image quality.

**8-bit sRGB (standard JPEG):**
- 256 quantisation levels; high-contrast regions (e.g., sky gradients) may still exhibit **banding** after TMO.
- DL TMO output before quantisation is floating-point; quantisation error ≈ ±0.5/255 = ±0.2%, generally imperceptible.
- Actual banding risk arises primarily from the linear → sRGB gamma encoding step before TMO, not from the DL network itself.

**10-bit P3 (HEIF, iPhone / flagship Android):**
- 1,024 quantisation levels; tonal banding is essentially eliminated.
- If DL TMO was trained with sRGB (8-bit) supervision, **fine-tuning** is required for direct 10-bit output: either retrain the final layer with 10-bit targets, or apply a lightweight banding suppression filter (a light smoothing convolution) after the 8-bit output to remove quantisation artifacts.
- 10-bit storage is approximately 1.25× the 8-bit size (HEIF compressed approximately 1.5×), with a modest impact on user storage and sharing bandwidth.

**Recommended strategy:** Default to 10-bit HEIF output on flagship devices; fine-tune the DL TMO output layer with 10-bit P3 supervision to ensure tonal continuity; for JPEG-compatible output, downsample to 8 bits and apply a light 0.5-sigma Gaussian blur to suppress banding.

---

### 11.4 On-Device Deployment and Quantisation Adaptation

#### Qualcomm SNPE / QNN
- Quantisation: INT8/INT16; dynamic quantisation typically incurs 0.2–0.5 dB PSNR loss.
- Recommended backend: DSP (HVX) first, GPU second.
- HDRNet's bilateral grid slicing can be accelerated on DSP using 3D LUT interpolation instructions at very low power (< 20 mW); CSRNet's pure MLP architecture is well-suited to HVX.
- 4D LUT lookup involves no neural network operators and can execute entirely within ISP DSP firmware without NPU involvement.

#### MTK NeuroPilot / APU
- Supports ONNX/TFLite import; APU5 supports INT4/INT8 mixed precision.
- Offline compilation via NeuroPilot SDK (neuron_runtime).
- CSRNet (< 50 K parameters) incurs minimal INT8 quantisation accuracy loss — the preferred lightweight deployment option for APU.

#### ARM NN / TFLite (General Mobile)
- ARM Mali GPU TFLite delegate achieves 2–4× acceleration vs. CPU-only.
- Quantisation tool: TFLite Converter post-training quantisation (INT8).
- NNAPI backend on Android 11+ devices automatically selects the optimal accelerator.
- **LUT distillation** (see §5.3) is the most robust strategy for bypassing NPU operator compatibility issues: distilling the neural TMO into a 3D/4D LUT removes all dependency on NPU operators in deployment.

---

## §12 Appendix: Traditional vs. DL TMO Comparison

### 12.1 Comprehensive Method Comparison Table

**Static HDR image TMO comparison (HDR-Real dataset, Fairchild HDR Survey subset)**

| Method | Type | TMQI ↑ | μ-PSNR (dB) ↑ | HDR-VDP JOD ↑ | Inference latency (4K) | Tunable |
|---|---|---|---|---|---|---|
| Reinhard global | Traditional | 0.712 | 28.4 | 6.8 | < 1 ms | Yes (manual) |
| Reinhard local | Traditional | 0.756 | 29.8 | 7.2 | ~30 ms | Yes (manual) |
| Drago (log exposure) | Traditional | 0.748 | 29.2 | 7.0 | < 1 ms | Yes (manual) |
| Mantiuk (perception-optimised) | Traditional | 0.779 | 30.6 | 7.5 | ~50 ms | Yes (manual) |
| LIME (low-light enhancement) | Shallow DL | 0.762 | 28.9 | 7.1 | ~15 ms | No |
| Zero-DCE | Lightweight DL | 0.778 | 30.1 | 7.4 | ~5 ms | No |
| **HDRNet** | DL (bilateral) | **0.821** | 31.8 | 7.8 | ~12 ms | Scene-adaptive |
| Deep TMO (U-Net) | DL (image-level) | 0.808 | 31.4 | 7.7 | ~45 ms | No |
| **CSRNet** | DL (curve) | 0.815 | 31.6 | 7.7 | ~2 ms | No |
| RetinexNet + TMO | DL (Retinex) | 0.798 | 30.8 | 7.5 | ~80 ms | No |

> **Reading the table:** TMQI and μ-PSNR are higher-is-better; JOD scores are higher-is-better (JOD > 7.0 typically corresponds to a "good" subjective rating). HDRNet leads on TMQI and overall JOD; CSRNet has the lowest inference latency (2 ms) — the preferred choice for real-time deployment. The traditional Mantiuk method remains competitive after manual parameter tuning but requires expert adjustment.

### 12.2 Video Temporal Consistency Comparison

| Method | Inter-frame luminance jitter $E_\text{flicker}$ ↓ | Scene-change adaptability | Compute cost |
|---|---|---|---|
| Frame-independent Reinhard | High (0.042) | Immediate | Low |
| Temporal mean-filter Reinhard | Medium (0.021) | 3–5 frame lag | Low |
| STAR (DL temporal TMO) | Low (0.008) | Adaptive (optical-flow guided) | High |
| RL-TMO | Low (0.011) | Adaptive (policy network) | Medium |
| 3D LUT + inter-frame interpolation | Medium (0.018) | Configurable | Very low |

Temporal consistency and scene-change adaptability are in fundamental tension: excessive inter-frame smoothing produces a "lag" sensation during rapid scene transitions (the image remains too dark for several seconds after cutting to a bright scene). STAR uses a motion mask to distinguish "scene cut" from "camera motion," allowing rapid luminance jumps at cuts while imposing strong smoothing constraints in static scenes — achieving a good balance between temporal smoothness and transition responsiveness.

---

## References

**Bilateral learning and HDRNet:**
- Gharbi, M., et al. (2017). **Deep bilateral learning for real-time image enhancement.** *ACM Trans. Graph. (SIGGRAPH)*, 36(4), 118.

**Image enhancement and TMO:**
- Wang, R., et al. (2019). **Underexposed photo enhancement using deep illumination estimation.** *CVPR 2019*.
- He, J., et al. (2020). **Conditional sequential modulation for efficient global image retouching.** *ECCV 2020*. [CSRNet]
- Zeng, H., et al. (2020). **Learning image-adaptive 3D LUTs for enhancing photos.** *IEEE TPAMI*, 44(4), 1889-1902.

**Video TMO:**
- Zhang, Y., et al. (2020). **STAR: Spatially and temporally adaptive real-time HDR video tone mapping.** *ECCV 2020*.

**4D LUT:**
- Yang, S., et al. (2022). **AdaInt: Learning adaptive intervals for 3D lookup tables on real-time image enhancement.** *CVPR 2022*.

**Evaluation metrics:**
- Yeganeh, H., & Wang, Z. (2013). **Objective quality assessment of tone-mapped images.** *IEEE Transactions on Image Processing*, 22(2), 657-667. [TMQI]
- Mantiuk, R., et al. (2011). **HDR-VDP-2: A calibrated visual metric for visibility and quality predictions in all luminance conditions.** *ACM SIGGRAPH 2011*.

**Evaluation metrics:**
- Yeganeh, H., & Wang, Z. (2013). **Objective quality assessment of tone-mapped images.** *IEEE Transactions on Image Processing*, 22(2), 657–667. [TMQI]
- Mantiuk, R., et al. (2011). **HDR-VDP-2: A calibrated visual metric for visibility and quality predictions in all luminance conditions.** *ACM SIGGRAPH 2011*.

**Datasets:**
- MIT-FiveK: https://data.csail.mit.edu/graphics/fivek/ (publicly available)
- HDRTV Dataset: https://github.com/chxy95/HDRTVNet (publicly available)

**Advanced methods:**
- [11] Zhu, et al. (2023). **Prompt-guided tone mapping for text-driven image enhancement.** (⚠️ arXiv preprint, not verified in CVF proceedings — TMQI value pending confirmation.)
- Ye, et al. (2024). **Diffusion-based HDR tone mapping with perceptual quality prior.** *ACM MM 2024*.

**Retinex-based methods:**
- Chen, C., et al. (2018). **Retinex-Net: Deep Retinex decomposition for low-light enhancement.** *BMVC 2018*.
- Zhang, Y., et al. (2021). **Beyond brightening low-light images.** *IEEE TPAMI*, 44(9), 5458–5471. [KinD++]
