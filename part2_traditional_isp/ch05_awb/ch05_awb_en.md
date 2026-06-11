# Part 2, Chapter 05: Auto White Balance (AWB)

> **Pipeline position:** After Demosaic; before or coupled with CCM
> **Prerequisites:** Chapter 5 (Color Science), Chapter 19 (Demosaic)
> **Reader path:** All readers
> **Scope note:** This chapter covers the AWB **algorithm layer** (Gray World / Bayesian / ML illuminant estimation). AWB control loop, convergence stability, and coupling with AE/AF are covered in **Part4 Ch76 (3A Control System)**.

---

## §1 Theory

### 1.1 The Color Constancy Problem

The human visual system possesses a remarkable ability: whether under clear daylight (color temperature ~6500 K), indoor incandescent light (2800 K), or fluorescent light (4000 K), we perceive a white sheet of paper as white. This ability is called **color constancy**. A camera sensor lacks this ability — the same white surface may produce an RGB output of `[220, 160, 80]` under incandescent light but `[170, 175, 180]` under daylight.

The mathematical formulation of the color constancy problem comes from Buchsbaum's (1980) classic framework. Let the true reflectance of a scene point be $\rho(\lambda)$, the spectral power distribution of the illuminant be $E(\lambda)$, and the sensor response function for camera channel $c$ be $S_c(\lambda)$. The camera measurement is:

$$
I_c = \int E(\lambda)\,\rho(\lambda)\,S_c(\lambda)\,\mathrm{d}\lambda
$$

When the illuminant $E(\lambda)$ changes, $I_c$ changes but the reflectance $\rho(\lambda)$ does not. **The goal of AWB** is to estimate the illuminant color from the measurements $I_c$ and apply corrective gains so that the image appears as if captured under a standard illuminant (typically D65, color temperature 6504 K).

### 1.2 Illuminant Estimation and AWB Gain Calculation

Let the estimated illuminant RGB mean be $[R_\text{illum},\, G_\text{illum},\, B_\text{illum}]$. The AWB white balance gains are defined as:

$$
[W_R,\, W_G,\, W_B] = \left[\frac{G_\text{illum}}{R_\text{illum}},\; 1.0,\; \frac{G_\text{illum}}{B_\text{illum}}\right]
$$

Using the green channel as reference ($W_G = 1$) is an industry convention because the green channel has the strongest correlation with luminance and the highest signal-to-noise ratio. Multiplying each image pixel by the corresponding channel gain yields the white-balance-corrected image:

$$
I_c^\text{corrected}(x,y) = W_c \cdot I_c(x,y)
$$

In practice, AWB gains are typically applied in the RGB domain after demosaicing, though they can also be applied in the RAW domain (multiplying the R, Gr, Gb, B channels of the Bayer image by their respective gains). Applying gains in the RAW domain avoids introducing color interpolation errors from demosaicing.

### 1.3 Classical Algorithms

#### 1.3.1 Gray World (Buchsbaum 1980)

**Assumption:** The average of all colors in an image is gray, i.e., the three-channel means are equal:

$$
\bar{R} = \bar{G} = \bar{B} = \bar{I}
$$

**Illuminant estimation:** Use each channel's mean directly as the illuminant color estimate; the gains are:

$$
W_R = \frac{\bar{G}}{\bar{R}}, \quad W_G = 1, \quad W_B = \frac{\bar{G}}{\bar{B}}
$$

**Advantages:** Computationally minimal; works reasonably for natural scenes.
**Disadvantages:** Fails severely when the scene color distribution is skewed (e.g., a frame full of red apples or green grass).

**Algorithm pseudocode:**

```
Algorithm: Gray World AWB
Input:  RGB image I[H,W,3], clipped to [0,1]
Output: AWB-corrected image

1. Compute channel means:
   μ_R = mean(I[:,:,0])
   μ_G = mean(I[:,:,1])
   μ_B = mean(I[:,:,2])

2. Compute gains:
   W_R = μ_G / (μ_R + ε)
   W_G = 1.0
   W_B = μ_G / (μ_B + ε)

3. Apply gains:
   I_out[:,:,c] = clip(I[:,:,c] * W_c, 0, 1)

4. Return I_out
```

#### 1.3.2 White Patch / MaxRGB

**Assumption:** The brightest pixel in the image is a white (fully reflective) surface, and its color equals the illuminant color:

$$
W_c = \frac{\max_G}{\max_c}, \quad \text{where } \max_c = \max_{x,y} I_c(x,y)
$$

In practice, the 99th percentile is typically used instead of the absolute maximum to suppress the influence of sensor hot-pixel noise.

**Advantages:** Works well when the scene contains a highly reflective white object (white wall, white paper).
**Disadvantages:** Extremely sensitive to highlight noise; fails badly when no white object exists (e.g., a candlelit scene against a dark background).

#### 1.3.3 Shades-of-Gray / Minkowski Norm

Finlayson and Trezzi (2004) unified Gray World and White Patch into a **Minkowski p-norm framework**:

$$
\left(\frac{1}{N} \sum_{x,y} |I_c(x,y)|^p\right)^{1/p} = k, \quad \forall c \in \{R, G, B\}
$$

- $p = 1$: reduces to Gray World ($L^1$ mean = arithmetic mean)
- $p \to \infty$: reduces to White Patch ($L^\infty$ norm = maximum)
- $p = 6$: empirically optimal trade-off on many datasets

Gain computation:

$$
W_c = \frac{\left(\frac{1}{N}\sum |I_G|^p\right)^{1/p}}{\left(\frac{1}{N}\sum |I_c|^p\right)^{1/p}}
$$

#### 1.3.4 Edge-Based Color Constancy (van de Weijer et al., 2007)

**Motivation:** The statistics are computed from **image gradients** rather than pixel intensities — color edges carry more robust illuminant information than absolute pixel values because edges eliminate the DC component of scene reflectance.

**Core formula (Generalized Gray Edge):** Apply a Gaussian smoothing of order $\sigma$ to the image, compute the $n$-th order derivative, then apply the Minkowski $p$-norm:

$$
\left(\frac{1}{N} \sum_{x,y} \left|\frac{\partial^n I_c^\sigma}{\partial x^n}\right|^p\right)^{1/p} = k
$$

where $I_c^\sigma = I_c * G_\sigma$ is the image smoothed by a Gaussian kernel with standard deviation $\sigma$.

| Parameter combination | Equivalent algorithm |
|----------|---------|
| $n=0, p=1, \sigma=0$ | Gray World |
| $n=0, p\to\infty, \sigma=0$ | White Patch |
| $n=0, p=p, \sigma=0$ | Shades-of-Gray |
| $n=1, p=1, \sigma=\sigma$ | Gray Edge (first-order) |
| $n=2, p=1, \sigma=\sigma$ | Second-order Gray Edge |

This method achieves a median angular error of approximately 3.2° on the Gehler-Shi dataset, a significant improvement over Gray World (6.4°).

#### 1.3.5 Deep Learning Methods

**Barron (2015) — Convolutional Color Constancy:**
Formulates illuminant estimation as 2D log-chrominance density estimation in image space. A CNN performs sliding-window convolution on a log-chrominance histogram, outputs a confidence map, and derives the illuminant estimate through spatial pooling. Achieves ~1.95° mean angular error on the Gehler-Shi dataset, significantly outperforming all classical methods.

**Barron & Tsai (2017) — Fast Fourier Color Constancy (FFCC):**
Moves the color constancy estimation from the spatial domain to the frequency domain. The color constancy problem can be approximated as a cross-correlation between the log-chrominance histogram and a convolutional kernel; FFT accelerates the full-image inference to $O(N \log N)$. Achieves ~1.78° mean angular error (Trimean ≈ 1.01°) on Gehler-Shi while reducing inference time to the millisecond range — well-suited for embedded and mobile real-time deployment **[7]**.

**Hu et al. (2021) — DeepAWB:**
An end-to-end network that takes a thumbnail of the pre-ISP RAW image as input and directly regresses AWB gains. Key contributions:
1. Multi-illuminant mixture estimation.
2. WB-gain-based data augmentation (synthetic training pairs generated by randomly applying WB offsets during training).
3. Real-time execution on mobile devices (10 ms with MobileNetV2 backbone).

**Major datasets:**

| Dataset | Images | Illuminants | Notes |
|--------|-------|------|------|
| Gehler-Shi (re-processed) | 568 | Single | Most widely used benchmark |
| NUS-8 Camera | 1736 | Single | 8 cameras, indoor + outdoor |
| Cube+ | 1707 | Single | High-resolution RAW format |
| LSMI | 7486 | Multiple | Recent large-scale multi-illuminant dataset |

### 1.3.6 Bayesian Illuminant Estimation and the von Mises-Fisher Prior

The Bayesian framework casts illuminant estimation as a **posterior inference** problem: given the observed image $\mathbf{I}$, infer the posterior distribution over the illuminant direction $\hat{\mathbf{e}} \in \mathbb{S}^2$ (a unit vector on the sphere):

$$p(\hat{\mathbf{e}} \mid \mathbf{I}) \;\propto\; p(\mathbf{I} \mid \hat{\mathbf{e}}) \cdot p(\hat{\mathbf{e}})$$

**Illuminant prior — the von Mises-Fisher distribution**

Natural illuminants cluster near the Planckian locus in normalized RGB chrominance space ($\hat{\mathbf{e}} = \mathbf{e}/\|\mathbf{e}\|$). Their distribution is unimodal and anisotropic. The **von Mises-Fisher (vMF) distribution** is the natural probability distribution on the unit sphere $\mathbb{S}^{d-1}$, with probability density:

$$p(\hat{\mathbf{e}} \mid \boldsymbol{\mu}, \kappa) = C_d(\kappa)\, \exp\!\left(\kappa\, \boldsymbol{\mu}^\top \hat{\mathbf{e}}\right)$$

where:
- $\boldsymbol{\mu} \in \mathbb{S}^{d-1}$ is the **mean direction** (the "typical white light" direction for AWB)
- $\kappa \geq 0$ is the **concentration parameter** ($\kappa = 0$: uniform distribution; $\kappa \to \infty$: point mass at $\boldsymbol{\mu}$)
- $C_d(\kappa)$ is the normalization constant; for $d = 3$ (RGB chrominance):

$$C_3(\kappa) = \frac{\kappa}{4\pi \sinh(\kappa)}$$

The vMF is the spherical analogue of a Gaussian: $\boldsymbol{\mu}$ is the mean direction and $\kappa$ controls the spread. The trajectory of standard illuminants from D65 (6504 K) to A (2856 K) along the Planckian locus is used to fit $\boldsymbol{\mu}$ and $\kappa$ from calibration data.

**Maximum a posteriori (MAP) estimation**

Under the gray-world likelihood (scene colors are on average achromatic), the MAP estimate is:

$$\hat{\mathbf{e}}_\text{MAP} = \arg\max_{\hat{\mathbf{e}} \in \mathbb{S}^2} \left[ \kappa\, \boldsymbol{\mu}^\top \hat{\mathbf{e}} - \frac{\|\mathbf{x} - \mathbf{x}_{\hat{\mathbf{e}}}\|^2}{2\sigma^2} \right]$$

The first term is the vMF prior (pulling the estimate toward the known illuminant distribution); the second term is the gray-world observation likelihood. Their balance is controlled by $\kappa/\sigma^2$:
- $\kappa \gg \sigma^2$: prior dominates; the estimate defaults to the "standard illuminant" (prevents drift in scene-bias situations)
- $\kappa \ll \sigma^2$: likelihood dominates; approximates pure Gray World

**Discrete implementation — illuminant prior LUT**

In practice the vMF prior is discretized into a 2D chrominance LUT (e.g., a 32×32 grid of R/G vs. B/G cells, each storing the log prior density). At AWB candidate scoring, the LUT is accessed via table lookup:

$$\text{score}(\hat{\mathbf{e}}_i) = \underbrace{\log p(\mathbf{I} \mid \hat{\mathbf{e}}_i)}_{\text{gray-world or gamut likelihood}} + \underbrace{\log p(\hat{\mathbf{e}}_i)}_{\text{vMF prior LUT}}$$

Multi-illuminant scenes can be modeled with a mixture of vMF distributions (one component per canonical illuminant: D65, A, TL84, CWF). The "AWB confidence region" used in commercial ISPs is the set of chrominance coordinates where the vMF prior density exceeds a threshold — estimates outside this region are treated as unreliable and trigger fallback to the previous frame's estimate or a safe default gain.

### 1.4 Evaluation Metric: Angular Error

The accuracy of illuminant estimation is measured by the **angular error** — the angle between the estimated and ground-truth illuminant vectors (in degrees):

$$
\varepsilon = \arccos\!\left(\frac{\langle \hat{L}_\text{est},\, \hat{L}_\text{gt} \rangle}{\|\hat{L}_\text{est}\|\cdot\|\hat{L}_\text{gt}\|}\right) \times \frac{180°}{\pi}
$$

where $\hat{L} = [R_\text{illum}, G_\text{illum}, B_\text{illum}]$ is the 3D illuminant vector.

**Reported statistics** typically include: Mean, Median, and Trimean (= $(Q_1 + 2\cdot Q_2 + Q_3)/4$, a weighted average of the 25th, 50th, and 75th percentiles). Trimean is less affected by outlier large errors than the mean, and is currently the preferred single-number metric in academia.

**Benchmark performance (Gehler-Shi dataset, trimean angular error):**

| Algorithm | Mean | Median | Trimean |
|------|------|--------|---------|
| Gray World | 6.36° | 6.28° | 6.28° |
| White Patch | 7.55° | 5.68° | 6.35° |
| Shades-of-Gray (p=6) | 3.40° | 2.57° | 2.93° |
| 1st-order Gray Edge | 3.20° | 2.63° | 2.78° |
| Barron CNN (2015) | 1.95° | 1.22° | 1.46° |
| Hu DeepAWB (2021) | ~1.5° | ~0.9° | ~1.1° |

### 1.5 Color Temperature and the Planckian Locus

**Correlated Color Temperature (CCT)** maps an illuminant color to the temperature value of the closest blackbody radiator on the Planckian locus (in Kelvin).

The spectral power distribution of blackbody radiation is given by Planck's law:

$$
B(\lambda, T) = \frac{2hc^2}{\lambda^5} \cdot \frac{1}{e^{hc/(\lambda k_B T)} - 1}
$$

Projecting $B(\lambda, T)$ at different temperatures $T$ onto CIE 1931 chromaticity coordinates $(u', v')$ traces the **Planckian locus**. Real light sources (fluorescent lamps, LEDs) typically do not lie on the locus; the temperature of the closest point is their CCT.

In practice, the **Robertson method** (1968) is used to compute CCT quickly via linear interpolation in CIE $uv$ chromaticity coordinates, avoiding per-temperature integration.

**Standard illuminant parameters:**

| Illuminant | CCT (K) | CIE $x$ | CIE $y$ | Typical scenario |
|------|---------|---------|---------|---------|
| D65  | 6504    | 0.3127  | 0.3290  | Noon daylight; sRGB standard white point |
| D50  | 5003    | 0.3457  | 0.3585  | Print and color management standard |
| A    | 2856    | 0.4476  | 0.4074  | Tungsten incandescent lamp |
| TL84 | 4000    | 0.3781  | 0.3775  | European/American retail fluorescent |
| F2   | 4230    | 0.3721  | 0.3751  | Wide-band fluorescent |
| CWF  | 4150    | 0.3736  | 0.3723  | U.S. cool-white fluorescent |

**Deriving CCT from AWB gains:**

1. Apply AWB gains to correct the RGB values of a white reference patch → obtain camera RGB coordinates $(R_w, G_w, B_w)$.
2. Use the camera RGB → CIE XYZ conversion matrix (from sensor calibration) to compute XYZ.
3. Compute CIE $u'v'$ from XYZ: $u' = 4X/(X+15Y+3Z)$, $v' = 9Y/(X+15Y+3Z)$.
4. Look up the Robertson table or interpolate the Planckian locus to obtain CCT.

---

## §2 Calibration

### 2.1 Calibration Objectives and Physical Meaning

AWB calibration (also called white balance calibration or illuminant calibration) aims to establish, under known standard illuminants, a mapping between the camera's RGB response and the "correct" gains. This serves as a prior or verification reference for the runtime AWB algorithm.

### 2.2 Required Hardware

**Standard Light Booth:**
A controlled lighting environment providing multiple standard spectral power distributions. Industrial standard illuminants typically include: D65 (daylight simulator), A (tungsten), TL84 (retail fluorescent), CWF (cool-white fluorescent), and UV (ultraviolet). The light booth should carry ISO 3664 or ANSI PH2.30 certification.

**18% Gray Card:**
A neutral gray reference panel with 18% reflectance (approximately $L^* \approx 50$). Common specifications: Kodak Gray Card, X-Rite ColorChecker gray patch. Key requirements:
- Three-channel reflectance difference $\Delta \rho < 0.5\%$ (neutrality)
- Lambertian surface (uniform brightness, no directional reflectance)

**Spectroradiometer:**
Used to measure the precise spectral power distribution of the light source, providing ground-truth CCT (accuracy ±10 K). Common models: Konica Minolta CS-2000, Photo Research PR-788.

### 2.3 Calibration Procedure

```
Step 1: Set up the calibration environment
  - Place the gray card at the center of the light booth at the distance specified
  - Ensure no ambient stray light contamination (use blackout cloth)
  - Use the spectroradiometer to record the actual CCT and uv chromaticity of the light source

Step 2: Capture reference images
  - Lock exposure (AE lock); fix ISO at a low value (typically ISO 100)
  - Disable in-camera AWB (set to manual white balance or RAW without applied gains)
  - Capture ≥5 frames per light source; average to reduce noise

Step 3: Compute ground-truth gains
  - Select an ROI (region of interest) over the gray card area (excluding edges)
  - Compute per-channel means over the ROI: μ_R, μ_G, μ_B
  - Ground-truth gains: W_R = μ_G / μ_R, W_G = 1, W_B = μ_G / μ_B

Step 4: Build the calibration table
  - Repeat Steps 1–3 for each standard illuminant
  - Output format: (CCT, W_R, W_B) key-value pairs forming an AWB calibration curve

Step 5: Verification and cross-validation
  - Apply the calibration gains to the images; visually confirm the gray card appears neutral
  - Compute ΔE of the corrected three-channel means (should be < 1.0)
```

### 2.4 Example Multi-Illuminant Calibration Table

| Illuminant | CCT (K) | W_R (gain) | W_B (gain) | Notes |
|------|---------|-----------|-----------|------|
| A    | 2856    | 0.52      | 2.10      | Tungsten; strong warm bias |
| TL84 | 4000    | 0.72      | 1.58      | Commercial fluorescent |
| F7   | 6500    | 0.98      | 1.05      | Broad-spectrum fluorescent (near daylight) |
| D65  | 6504    | 1.00      | 1.00      | Standard reference point |
| D75  | 7504    | 1.08      | 0.88      | Overcast daylight |

> Note: The values above are typical examples; actual values differ significantly by sensor model.

---

## §3 Tuning

### 3.1 AWB Convergence Speed vs. Stability Trade-off

Running AWB frame-by-frame in a video stream creates a fundamental tension between **fast response** and **inter-frame stability**:
- Too fast → AWB jumps abruptly on illuminant changes, causing "color hunting" in video
- Too slow → Color offset persists for seconds after a scene change; poor user experience

An **IIR temporal smoothing filter** is the standard solution:

$$
W_c^\text{smooth}[n] = \alpha \cdot W_c^\text{raw}[n] + (1-\alpha) \cdot W_c^\text{smooth}[n-1]
$$

$\alpha$ is the smoothing factor (step size / damping factor). Typical values:
- Static scene (no motion detected): $\alpha \approx 0.05$ (slow convergence; stability priority)
- Heavy motion or scene cut: $\alpha \approx 0.3$ (fast response)
- Large jump detection: when $|W_c^\text{raw}[n] - W_c^\text{smooth}[n-1]| > \delta$, force $\alpha = 0.8$ to accelerate tracking

### 3.2 AWB Pixel Selection (Pixel Masking)

Not all pixels contribute useful information for illuminant estimation. The following pixels should be excluded:

| Excluded type | Condition | Reason |
|---------|---------|------|
| Overexposed pixels | Any channel > 0.95 | Saturated; color information unreliable |
| Underexposed pixels | Luminance < 0.02 | SNR too low in shadows |
| Highly saturated pixels | Color saturation > threshold | Highly saturated patches don't represent illuminant |
| Skin pixels (optional) | Within the skin chrominance ellipse | Skin uses a dedicated AWB strategy |

### 3.3 Scene Awareness and Priority Modes

**Face/skin-tone priority mode:**
When a face is detected, prioritize correcting skin tone into the natural skin tone range (CIE Lab: $L^* \in [50,80]$, $a^* \in [10,25]$, $b^* \in [8,20]$) rather than pursuing an overall gray-world balance.

**Indoor/outdoor classification:**
Automatically determine the scene type from the following features and select the corresponding AWB strategy:
- Exposure time / f-number ratio (outdoor illuminance is much higher)
- Estimated CCT distribution from AWB (daylight > 5500 K; indoor < 4500 K)
- Sky/vegetation detection (color + texture classifier)

**Candlelight preservation mode:**
At very low color temperatures (< 2500 K), full correction would destroy the scene atmosphere. A CCT lower limit can be set (e.g., 3000 K); below this temperature the image is processed as if at 3000 K, preserving the warm ambiance.

### 3.4 Quantitative Tuning Principles: Objective IQA over Pure Subjectivity

#### 3.4.1 The Subjectivity-Driven Anti-Pattern

AWB tuning in many teams relies entirely on visual inspection: an engineer compares two images, adjusts a parameter, and requests a subjective score from an evaluation team. This workflow has well-documented failure modes in production ISP engineering:

- **Oscillating parameters:** Engineer A tunes the gain to a value; Engineer B perceives it as "too warm" and reverts it; the parameter cycles across software versions with no record of why the original value was chosen.
- **Cross-scene regression:** Parameters optimized for skin-tone scenes degrade sky or foliage rendering, but incomplete coverage of the test set means the regression is only discovered after release.
- **No versioned baseline:** "The new version looks better" cannot be verified quantitatively; release decisions rest on individual authority rather than data.

#### 3.4.2 Quantitative Tuning Protocol

```
Before tuning:
  1. Run the IQA evaluation script on the standard test scene set
     (≥50 images covering D65 / TL84 / A illuminants and multiple scene categories)
  2. Record baseline metrics:
       ΔE₀₀ (white-balance color error, gray card)
       ΔE_skin (skin-tone color error, Macbeth skin patches)
       Angular Error (illuminant estimation, if ground truth available)
       Video gain std-dev (AWB stability over 30-second clips)
  3. Commit the metric vector to the version database (parameter version + metric vector)

During tuning:
  4. After each parameter change, immediately run an incremental evaluation
     on the affected subset of scenes.
  5. Flag any metric regression > threshold (e.g., ΔE₀₀ > 0.3) as a
     "risk modification" requiring human review before merging.

After tuning:
  6. Run the full evaluation before release; generate a new-vs-old comparison report.
  7. Allow the change into the mainline only when at least one key metric improves
     by at least the minimum significant difference (MSD):
       ΔE₀₀ improvement ≥ 0.3, or CCT estimation improvement ≥ 30 K.
```

**Core AWB tuning metrics and acceptance criteria (flagship tier):**

| Metric | Measurement method | Acceptance criterion |
|--------|-------------------|---------------------|
| White balance ΔE₀₀ | Gray card under D65 / TL84 / A | < 1.5 (single illuminant); < 2.5 (full CCT range) |
| CCT estimation error | Robertson CCT vs. reference instrument | < ±150 K (single standard illuminant, controlled lab) |
| Skin-tone ΔE₀₀ | Macbeth skin patches | < 2.0 |
| Video inter-frame ΔE jump | Per-frame ΔE standard deviation (static scene) | < 0.5 |
| Color hunting events | 30-second video automated detection | < 2 events / 30 s |

> **CCT ±150 K caveat:** This accuracy holds under single-illuminant, uniform gray-card conditions in a controlled booth. Under mixed illuminants the error can reach ±300–500 K; under fluorescent lamps (TL84/CWF) the non-continuous spectrum introduces a systematic Δuv offset that degrades CCT estimates even on precision instruments by ±50–100 K; under low light (ISO > 1600) photon noise inflates CCT error to ±200–400 K. All three platforms (Qualcomm, MTK, HiSilicon) achieve similar accuracy under standard conditions; differences emerge at edge illuminant conditions.

### 3.5 Three-Platform AWB Key Parameter Comparison

| Parameter function | Qualcomm CamX / Chromatix | MTK Imagiq / NDD | HiSilicon Kirin |
|--------------------|--------------------------|-----------------|-----------------|
| White balance gains | `AWB_GainR/GainB` (CIQT XML) | `NDD_AWBGainR/B` (NDD config) | `ISP_AWB_RGain/BGain` (JSON) |
| Gr/Gb balance | `AWB_GainGr/GainGb` (4-channel independent) | `NDD_AWBGainGr/Gb` (must adjust together) | `ISP_AWB_GrGain/GbGain` |
| Illuminant mode switching | `AWB_LightSourceMode` (enum: D65/A/F/LED) | `AWBLightSourceTable` (enum table) | `AWB_IlluminantType` |
| CCT output | `LensInfo.AWBColorTemperature` (K, EXIF) | `AWBOutputColorTemp` (metadata) | `Metadata::AWBCCTEst` |
| CCT clamp range | `AWB_CCTLow/High` (e.g., 2000–8000 K) | `AWBCCTRange[min,max]` (NDD) | `AWB_CCTClampMin/Max` |
| Algorithm selection | Gray World / Gamut / ML configurable | Built-in Gamut + NDD prior | HiSilicon proprietary Multi-patch |
| Temporal smoothing strength | `AWBDecay` (0.0–1.0) | `AWBTemporalFilter` (frame count) | `AWB_StabilizeWeight` |
| Valid pixel mask | `AWB_LumaLow/High` (luminance window) | `AWBPixelMaskLuma` (NDD range) | `AWB_ValidPixelRange` |
| Multi-illuminant detection | `AWB_MultiIlluminantEnable` (bool) | `AWBMultiIlluminant` (NDD bool) | `AWB_MultiLightEnable` |
| Memory color enhancement | `MCE_Enable` + Cb-Cr zone params (independent module, after CCM) | Via `DAY_LOCUS_OFFSET` in AWB stage | `ISP_MCE_Enable` |
| White-point locus offset | N/A | `DAY_LOCUS_OFFSET` (along Planckian locus) / `GM_OFFSET_WF` (green-magenta axis) | N/A |
| Skin color protection (SCE) | `SCE_Enable` + H/S range params (runs after MCE) | N/A | `ISP_SCE_Enable` |

> **Tuning note:** Qualcomm `AWB_GainR/B` are referenced to `GreenGain = 1.0`. MTK `NDD_AWBGainR/B` must be adjusted **together** with `NDD_AWBGainGr/Gb` to maintain Gr/Gb balance — an imbalance > 0.03 produces green/magenta cross-row artifacts on flat gray surfaces.

**Qualcomm CamX chromatix XML tuning path:**

```
CamX Pipeline → AWBNode → AWBAlgorithm
    ├── chromatix_awb_ext.xml          ← main AWB algorithm parameters
    │   ├── AWBIlluminantData[]        ← per-illuminant Rg/Bg center coordinates
    │   ├── AWBGamutBoundary           ← gamut constraint boundary (polygon vertices)
    │   ├── AWBDecay                   ← IIR smoothing coefficient (0.05–0.3)
    │   └── AWBCCTLow/High             ← CCT output clamp range
    └── chromatix_sensor_XXXX.xml      ← sensor-specific R/G/B channel sensitivities
```

Typical AWB gain structure (D65, 2800 lux measured values):
```xml
<AWBIlluminantEntry illuminant="D65">
    <RGain>1.82</RGain>     <!-- R channel gain (relative to G = 1.0) -->
    <GrGain>1.00</GrGain>   <!-- Gr = reference 1.0 -->
    <GbGain>1.00</GbGain>   <!-- Gb ≈ 1.0; minor imbalance needs correction -->
    <BGain>1.47</BGain>     <!-- B channel gain -->
    <CCT>6504</CCT>         <!-- corresponding color temperature in K -->
</AWBIlluminantEntry>
<AWBIlluminantEntry illuminant="A">
    <RGain>2.45</RGain>
    <GrGain>1.00</GrGain>
    <GbGain>1.00</GbGain>
    <BGain>0.95</BGain>
    <CCT>2856</CCT>
</AWBIlluminantEntry>
```

**MTK NDD tuning path:**

```
Scenario_XXXX.NDD
├── [AWB]
│   ├── NDD_AWBGainR     = 1.82   # R channel gain (D65 reference)
│   ├── NDD_AWBGainGr    = 1.00   # must be balanced with Gb
│   ├── NDD_AWBGainGb    = 1.02   # Gr/Gb imbalance > 0.03 requires correction
│   ├── NDD_AWBGainB     = 1.47   # B channel gain
│   ├── AWBTemporalFilter = 8     # frame smoothing window (8 frames ≈ 0.27 s @ 30 fps)
│   └── AWBCCTRange      = [2000, 8000]
```

**MTK Day Locus Offset mechanism:**

MTK lacks an independent MCE module; "color preference" (e.g., preserving warmth or preferred hues) is implemented inside the AWB estimation stage via two parameters:

- `DAY_LOCUS_OFFSET`: controls the shift of the AWB white-point target along the Planckian locus. A positive value shifts the target toward higher CCT (cooler image); a negative value retains more warmth.
- `GM_OFFSET_WF`: controls the shift perpendicular to the Planckian locus (green-magenta axis, i.e., the Δuv direction). Combined with `GM_OFFSET_THR_WF` (activation threshold), this allows retaining a slight preferred color cast under street lamps or fluorescent sources without over-correcting to pure white.

These two parameters together determine the "preferred white-point landing position" in MTK's architecture, equivalent in purpose to Qualcomm's post-CCM MCE module, but applied earlier (inside the AWB estimator rather than after the CCM).

### 3.6 AWB–CCM Coupling Dependency

**Important constraint:** The CCM (Color Correction Matrix) is calibrated for a specific color temperature. The color temperature assumed by AWB and the color temperature at which the CCM was calibrated must match; otherwise a systematic color shift will appear.

In practice, two approaches are used:

1. **Multi-CCT CCM interpolation:** Calibrate a separate CCM for each standard color temperature (e.g., 2856 K / 4000 K / 6504 K); at runtime, linearly interpolate between CCMs based on the AWB-estimated CCT.
2. **Fixed white-point CCM:** Fix the CCM calibrated to D65; AWB is responsible for correcting all illuminants to a state close to D65, and the D65 CCM is applied uniformly.

---

## §4 Artifacts

### 4.1 Color Cast under Mixed Illuminants

**Appearance:** A scene lit simultaneously by daylight (window) and fluorescent light (room interior) causes the AWB algorithm to estimate a compromise illuminant, leaving the daylight zone biased blue and the fluorescent zone biased green — neither is accurate.

**Root cause:** Classical AWB algorithms assume a single illuminant (Single Illuminant Assumption) and cannot handle multi-illuminant scenes.

**Mitigation:**
- Apply local AWB (Local AWB) per image region, estimating the illuminant separately for different areas.
- Use a multi-illuminant estimation network (e.g., a deep model trained on the LSMI dataset).

### 4.2 AWB Oscillation (Hunting)

**Appearance:** AWB gains jump back and forth between adjacent frames during video capture, causing continuous slight flickering of image color.

**Root cause:** Inherent randomness in AWB estimation combined with an IIR filter parameter that is too large ($\alpha$ too high).

**Tuning direction:**
- Reduce $\alpha$ (increase temporal smoothing); typical value down to 0.03–0.08.
- Add a dead band for gain changes: update the gain only when $|ΔW_c| > 0.02$.
- Ensure the AWB statistics region (ROI) remains stable across consecutive frames; avoid statistics region jumps caused by foreground motion.

### 4.3 Dominant Color Bias

**Appearance:** When photographing a frame full of red apples, the Gray World algorithm outputs $W_R < 1$ because the overall R channel mean is high, darkening the red apples and causing the whole image to appear bluish.

**Root cause:** The gray world assumption breaks down in scenes with a strong dominant color.

**Mitigation:**
- Use a higher Minkowski $p$ value ($p = 6$ or $p = 10$) to reduce the statistical weight of low-brightness pixels.
- Exclude highly saturated pixels from the statistics.

### 4.4 Yellow-Orange Cast under Tungsten Illumination

**Appearance:** In a tungsten incandescent environment (CCT ~2800 K), if AWB fails to correctly estimate the illuminant, the image shows a pronounced yellow-orange cast and white objects appear dingy.

**Cause:** The tungsten spectrum is heavily skewed toward long wavelengths (red/yellow), requiring a large gain correction of approximately $W_R \approx 0.5$, $W_B \approx 2.0$. If the algorithm over-estimates CCT (biased toward daylight), the correction is insufficient.

**Tuning direction:** Ensure the calibration table covers the 2800 K point; use nearest-neighbor interpolation (not extrapolation) for camera RGB chromaticity falling in the tungsten region.

### 4.5 Green Cast under Tree Shade

**Appearance:** Images captured in tree shade appear greenish.

**Cause:** Leaves strongly reflect green wavelengths while transmitting green light (chlorophyll peaks near ~500 nm and ~670 nm), increasing the spectral power density in the green band of the light reaching the scene. This is a genuine illuminant color change, though users typically expect AWB to correct it.

---

## §5 Evaluation

### 5.1 Standard Benchmark Datasets

**Gehler-Shi dataset (Shi & Funt, 2010 re-processed):**
568 RAW-format images; each was captured with a Macbeth ColorChecker present in the scene, providing precise ground-truth illuminant color. This is the most widely cited benchmark in the color constancy literature.

**NUS-8 Camera dataset (Cheng et al., 2014):**
Approximately 200 images from each of 8 different cameras, totaling 1736 images; covers a broader range of sensor differences.

### 5.2 Metric Computation

For a test set of $N$ images with angular errors $\varepsilon_i$ sorted as $\varepsilon_{(1)} \le \varepsilon_{(2)} \le \cdots \le \varepsilon_{(N)}$:

$$
\text{Mean} = \frac{1}{N}\sum_{i=1}^N \varepsilon_i
$$

$$
\text{Median} = \varepsilon_{(N/2)}
$$

$$
\text{Trimean} = \frac{Q_1 + 2\cdot Q_2 + Q_3}{4}, \quad Q_k = \varepsilon_{(kN/4)}
$$

$$
\text{Best-25\%} = \text{Mean of bottom-quartile errors (easy cases)}
$$

$$
\text{Worst-25\%} = \text{Mean of top-quartile errors (hard cases)}
$$

**Why prefer Trimean:** Trimean is more robust than the mean (not inflated by a few large outliers) and more informative than the median (accounts for the quartile distribution). It is the currently recommended single-number reporting metric in the color constancy literature.

### 5.3 Real-Scene Visual Evaluation

Laboratory angular error is only a necessary condition. Practical ISP tuning also requires:

| Evaluation item | Method | Pass criterion |
|---------|------|---------|
| Gray card white balance | Shoot an 18% gray card under the target illuminant; measure corrected ΔE | $\Delta E_{00} < 2.0$ |
| Skin tone naturalness | Photograph standard subjects; visual or ColorChecker assessment of skin regions | Skin falls within natural skin-tone ellipse |
| Color fidelity | Photograph an X-Rite ColorChecker Classic 24-patch chart | Mean $\Delta E_{00} < 3.0$ |
| Video stability | Record 30 seconds of a fixed scene; compute per-frame AWB gain variation | Gain standard deviation < 0.01 |
| Scene-change response | Record the number of frames for AWB to converge after switching from indoor to outdoor | Convergence time < 2 seconds |

### 5.4 3A System Joint Evaluation (AE/AWB/AF)

AWB does not operate in isolation; it works in concert with Auto Exposure (AE) and Auto Focus (AF) in the 3A system. Evaluation should include:
- AWB stability under AE variation (±2EV exposure compensation)
- AWB consistency across a burst sequence (color variation between frames of the same scene)

---

## §6 Code

See `ch05_awb_notebook.ipynb` for runnable examples.

---

## §7 Mixed Illuminants and Fluorescent Spectra

### 7.1 Mixed-Illuminant AWB Decomposition

**Problem:** An indoor scene simultaneously illuminated by window daylight (D65) and tungsten room lamps (illuminant A) invalidates the single-illuminant assumption on which classical AWB is built. A single globally estimated CCT produces a compromise gain vector that is wrong in both regions of the frame.

**Dual-illuminant decomposition:** Model the effective white-balance gain vector as a convex combination of two canonical illuminant gains:

$$\mathbf{g}_\text{mix} = \alpha \cdot \mathbf{g}_{L_1} + (1-\alpha) \cdot \mathbf{g}_{L_2}$$

**Implementation:** Partition the image into region-of-interest tiles; compute the per-tile chrominance centroid; cluster tiles into two illuminant-dominant groups (e.g., window zone vs. room interior zone); estimate per-group CCT; blend gains by area weight. This approach is described in Gijsenij et al. **[IEEE TPAMI 2011]**.

### 7.2 Fluorescent Lamp Tri-Line Spectra: AWB Failure and Repair

**Root cause:** Fluorescent lamps (TL84 / CWF) have an SPD consisting of three narrow discrete peaks at approximately 436 nm (blue), 546 nm (green), and 611 nm (red), superimposed on a weak continuous background. The camera sensor's spectral response function $S_c(\lambda)$ integrates this discrete-line SPD differently from the way the CIE color-matching functions integrate it; the result is that the camera's RGB triplet for a white surface under TL84 is systematically displaced from the blackbody locus, even though a human observer would judge the surface as white.

**Failure mode:** Gray World applied to a TL84 scene produces a green-biased estimate. Gray Edge and Bayesian estimators that use only CCT as the illuminant descriptor are not immune: single-parameter CCT lookup treats TL84 as "a slightly green 4000 K daylight source" and applies a correction in the wrong direction, making the output *more* green.

**Repair strategies:**

1. Add a dedicated calibration entry for TL84 (and separately for CWF) in the AWB CCT–gain LUT.
2. Use CCT + Δuv as a two-parameter illuminant descriptor (§7.2.1).
3. Trigger a dedicated gain group using the G/B ratio as a fluorescent detection feature.

#### 7.2.1 Physical Root Cause: Large Δuv Shift and Narrow-Band Spectrum

The core issue is not inaccurate CCT estimation but that **the illuminant chromaticity point is systematically displaced from the Planckian locus**, shifted toward green. This displacement is quantified as **Δuv** — the perpendicular distance from the illuminant chromaticity to the locus in CIE 1976 $u'v'$ space:

- **TL84** (CIE F11, European commercial fluorescent): CCT ≈ 4000 K, narrow tri-band spectrum, Δuv biased positive (toward green), typical value **+0.008 to +0.012**.
- **CWF** (CIE F2, U.S. cool-white fluorescent): CCT ≈ 4150 K, broad-band spectrum, Δuv biased positive, typical value **+0.005 to +0.010**.

**AWB misclassification mechanism:** In (R/G, B/G) chrominance space the fluorescent white point is displaced toward green (lower R/G). A traditional single-parameter CCT lookup misidentifies TL84 as a "green-shifted 4000 K daylight" and applies a correction in the anti-green direction. Because the displacement was in the green direction, the correction moves the output further green — or overshoots to produce a magenta cast. This is a parameter-space error: single-parameter CCT cannot describe the full two-dimensional illuminant chromaticity. The fix requires CCT + Δuv as co-registered parameters **[16]**.

**Metamerism effect:** Under conditions where a TL84 lamp and a blackbody at the same CCT produce nearly identical camera RGB outputs for a white surface (camera metamerism), the calibration gains derived from the blackbody standard will be applied to the fluorescent scene with a systematic error. This occurs because $\int S_c(\lambda) E_\text{TL84}(\lambda) d\lambda \neq \int S_c(\lambda) E_\text{BB}(\lambda) d\lambda$ even when the two illuminants appear visually equivalent to the human observer (because the observer integrates with the CIE color-matching functions, not $S_c$). This phenomenon appears systematically whenever the test illuminant differs spectrally from the calibration illuminant **[16]**.

> **Warning:** The CCT-only Robertson approximation is unreliable for fluorescent illuminants. Two fluorescent lamps with substantially different visual appearances may map to nearly the same CCT; the actual difference is correctly captured only in Δuv. Engineering documentation should always report (CCT, Δuv) pairs for fluorescent sources, never CCT alone.

#### 7.2.2 Fluorescent AWB Calibration Strategy

**Key principle — TL84 and CWF must be calibrated independently.**

Fluorescent calibration points must not be replaced by interpolation between D65 and A entries. The illuminant chromaticity of TL84/CWF lies off the blackbody interpolation line in (R/G, B/G) space; interpolated gains carry a systematic Δuv-direction error that manifests as residual green cast after correction.

Recommended calibration illuminant sequence (ascending CCT order):

| Illuminant | CCT (K) | Type | Calibration necessity |
|------------|---------|------|-----------------------|
| H / U30 | ~2300 K | Horizon / warm incandescent variant | Recommended (extreme-warm indoor) |
| A | 2856 K | Tungsten incandescent | **Required** |
| TL84 | 4000 K | European commercial fluorescent | **Required (independent)** |
| CWF | 4150 K | U.S. cool-white fluorescent | **Required (independent)** |
| D50 | 5003 K | Print standard | Recommended |
| D65 | 6504 K | Noon daylight / sRGB standard | **Required** |
| D75 | 7504 K | Overcast daylight | Recommended |

For each illuminant, record both the (R/G, B/G) chrominance coordinates **and** the Δuv value. Construct a **CCT–Δuv dual-parameter white-point table**. A single-parameter CCT lookup table is an incomplete implementation for fluorescent sources.

#### 7.2.3 Fluorescent Gamut Tuning Strategy

AWB algorithms use a "confidence region" (gamut) to determine which pixels are valid samples for illuminant estimation. A typical white-region gamut is defined by three constraints:

$$|B - G| < a, \quad |R - G| < b, \quad |B - G| + |R - G| < c$$

where $a$, $b$, $c$ are tunable parameters that define the acceptance window for white pixels in the calibration coordinate system.

**Core tuning direction for fluorescent sources: expand the boundary in the green direction.** Because fluorescent illuminant white points are systematically displaced toward green (lower R/G in (R/G, B/G) space), the default gamut boundaries — optimized for blackbody-locus illuminants — exclude the fluorescent white point as "anomalous." The algorithm then substitutes the nearest accepted illuminant (typically daylight), which produces the characteristic green cast.

Correct tuning approach:
- Increase parameter $b$ (relax the $|R-G|$ constraint) to allow green-shifted white points into the confidence region.
- Increase parameter $c$ (relax the total deviation constraint).
- **Do not** uniformly expand all boundaries; this admits incorrect white points in scene-dominant-color situations and worsens bias in those cases.

**Δuv correction (high-end platforms):** Qualcomm Chromatix supports per-illuminant Δuv offset configuration in `AWBIlluminantData`, providing direct green-cast correction for fluorescent sources without relying solely on gamut expansion. This is the most accurate path on the Qualcomm platform.

#### 7.2.4 Three-Platform Fluorescent AWB Comparison

| Dimension | Qualcomm (CamX / Chromatix) | MTK (Imagiq / NDD) | HiSilicon (Kirin) |
|-----------|-----------------------------|--------------------|-------------------|
| Dedicated fluorescent module | Yes: TL84 / CWF treated as independent illuminant types in `AWBIlluminantData`, each with a separate calibration entry | Yes: TL84 / CWF listed as independent entries in `AWBIlluminantTable` (IQ Tuning flow) | **No:** fluorescent merged with AHD (warm-light group including tungsten); no independent detection module |
| Gamut configuration | `AWBGamutBoundary` defined by polygon vertices; fine-grained per-direction control | White-region statistics + error-pixel filter; fluorescent direction adjustable via `AWBGamutTolerance` | Handled internally; no documented independent a/b/c parameters |
| Δuv offset correction | Supported: per-illuminant Δuv offset in `AWBIlluminantData`; independent segment configuration | No public independent Δuv parameter; indirect adjustment via `GM_OFFSET_WF` (green-magenta axis) | Relies on CCM matrix tuning or 3D CLUT (CLUT) bypass for color cast correction |
| Fluorescent debug path | In CIQT: inspect WB-point distribution, confirm TL84/CWF chromaticity inside gamut; adjust `IlluminantData` + Δuv | XML adjustment + Imagiq tool WB-point visualization; reference TL84/CWF independent calibration entries | Confirm AWB calibration white-point coverage includes fluorescent CCT range; suppress green via CCM green-channel coefficient; no dedicated bypass |
| Engineering complexity | Medium (good tool support; parameter semantics clear) | Medium (requires understanding non-intuitive `GM_OFFSET_WF` meaning) | High (fluorescent green cast must be addressed at the CCM/CLUT layer) |

**HiSilicon special case:** On HiSilicon ISPs there is no independent fluorescent detection module. TL84 and AHD (Automatic Hue Detection, covering warm sources including tungsten) are processed together. The two-level correction path is:
1. **AWB gains:** Generic illuminant-adaptive gains that do not discriminate the Δuv difference between fluorescent and incandescent sources.
2. **CCM / CLUT bypass correction:** Fluorescent green cast (especially the TL84 bias) is handled by adjusting the CCM green-channel coefficients or applying a 3D look-up table mapping.

The debug sequence on HiSilicon is therefore: **verify AWB calibration white points cover the fluorescent CCT range → adjust CCM to suppress green channel → do not search for a dedicated fluorescent bypass (none exists).** Engineers transitioning from Qualcomm or MTK frequently waste time looking for a Δuv parameter that does not exist on this platform.

---

> **Field Note: The Real Pitfalls of Fluorescent AWB**
>
> **Pitfall 1 — The root cause is Δuv, not CCT.**
> Fluorescent lamps (TL84/CWF) are systematically displaced from the Planckian locus in CIE 1976 $u'v'$ space toward green. TL84's typical Δuv is +0.008 to +0.012. An AWB that only looks up CCT (4000 K) treats TL84 as "a slightly green 4000 K daylight source" and applies a compensating anti-green correction — which makes the output *more* green, or even magenta (overcorrection). The correct fix is to register TL84's chromaticity point with its Δuv offset and maintain a CCT + Δuv dual-parameter table. Using CCT alone to characterize a fluorescent illuminant is like specifying a geographic location using only latitude.
>
> **Pitfall 2 — TL84 and CWF must be calibrated independently; recycling D65 is producing future bugs.**
> TL84 (European commercial fluorescent) and CWF (U.S. cool-white fluorescent) differ by only 150 K in CCT (4000 K vs. 4150 K), but their SPDs are different and their Δuv values differ slightly. Interpolating between D65 and A calibration entries to "synthesize" a fluorescent calibration point is incorrect: the fluorescent chromaticity lies off the blackbody interpolation line, so the interpolated gain has a systematic Δuv-direction error. HiSilicon is a special case: it has no independent fluorescent module, so TL84 color drift is addressed at the CCM layer. Qualcomm and MTK both support independent TL84/CWF entries — use them.
>
> **Pitfall 3 — Gamut boundaries are the invisible trap; the fix is different on each platform.**
> The AWB confidence region excludes pixels whose chrominance falls outside the gamut defined by $|R-G| < b$, $|B-G| < a$, $|R-G|+|B-G| < c$. Fluorescent white points fall outside default gamuts tuned for blackbody-locus sources. When the fluorescent white point is excluded, the algorithm substitutes the nearest accepted illuminant (daylight), producing the characteristic green image. The fix is to increase $b$ (relax the R-G constraint) to allow the green-shifted white point in. On Qualcomm this is done via the `AWBGamutBoundary` polygon in Chromatix; on MTK via `AWBGamutTolerance` + `GM_OFFSET_WF`. The two platforms use different parameter semantics; do not port numerical values directly between them.
>
> *References: carlyleliu, "ISP RAW-domain AWB deep dive," carlyleliu.github.io, 2021 [16]; SigmaStar, "SSD238X IQ Tuning Reference," comake.online [17]; CIE Publication 15.3:2004, "Colorimetry" [18].*

### 7.3 Video AWB Stability: IIR Jitter Suppression

Video AWB runs the illuminant estimator on every frame and feeds the result through a temporal IIR filter before applying gains:

```python
# AWB IIR temporal smoothing (prevent inter-frame jumps)
alpha = 0.05           # convergence speed; smaller = more stable
g_r_smooth = alpha * g_r_new + (1 - alpha) * g_r_prev
g_b_smooth = alpha * g_b_new + (1 - alpha) * g_b_prev
# Extreme-scene detection: accelerate convergence on large jumps
if abs(g_r_new - g_r_prev) > threshold:
    alpha = 0.3        # fast tracking
```

The effective time constant of the filter at 30 fps is approximately $\tau = 1/(30 \cdot \alpha)$ seconds:
- $\alpha = 0.05 \Rightarrow \tau \approx 0.67$ s (stable, slow)
- $\alpha = 0.3 \Rightarrow \tau \approx 0.11$ s (fast response on scene cuts)

**Adaptive alpha strategy:**
- Compute the frame-to-frame illuminant estimate change $\Delta \hat{e}$ (angular distance in chrominance space).
- If $\Delta \hat{e} < \theta_\text{stable}$ (e.g., 2°): use low $\alpha$ (stability mode).
- If $\Delta \hat{e} > \theta_\text{fast}$ (e.g., 10°): use high $\alpha$ (track mode).
- Intermediate values: linear interpolation between $\alpha_\text{low}$ and $\alpha_\text{high}$.

---

## Engineering Recommendations

AWB is fundamentally a three-way trade-off between algorithm accuracy, robustness to edge-case illuminants, and skin-tone protection. Once the core algorithm is selected, 90% of the remaining engineering effort is in special-scene validation and targeted debugging.

| Scenario / requirement | Recommended approach | Key parameters | Notes |
|------------------------|---------------------|----------------|-------|
| Standard mass-production main camera | Gamut mapping + statistical prior | `AWB_LightSource` anchor table | Do not use pure Gray World — green-grass / blue-sky scenes will fail |
| High skin-tone accuracy (portrait mode) | ML-AWB or C5 | Sensor-specific training data | C5 (CVPR 2022) achieves Angular Error ≈ 1.5° on real RAW, near human perceptual threshold |
| Ultra-wide / telephoto secondary camera | Sync CCT from main camera + local fine-tuning | `AWB_Sync_Mode` | Multi-camera consistency takes priority over single-camera accuracy; hard sync is more stable than algorithmic alignment |
| Video live-stream; inter-frame stability priority | Increase temporal smoothing; relax single-frame accuracy | `AWB_Temporal_Speed` | Flickering is more objectionable to users than mild color offset; slowing convergence by 0.3–0.5 steps typically gives a better perceptual result |
| Mixed illuminants (indoor window scene) | Per-region CCT statistics + multi-illuminant estimation | Platform-specific; no standard parameter name | Huawei XMAGE / OPPO zone-based solutions; standard platforms require custom implementation or post-processing |

**Debugging checklist:**

- **Angular Error and subjective evaluation must run in parallel.** Angular Error < 2° does not guarantee pleasing skin tones. Capture a dedicated portrait set (cold / warm / deep / light skin tones under D65, TL84, A) and score skin tone subjectively alongside the angular error metric.
- **Lock memory-color parameters before mass production.** `AWB_MemoryColor` (Qualcomm) / `AWB_ColorTolerance` (MTK) set protection intervals for skin tones, sky blue, and grass green. Once the product is in mass production these parameters are very hard to change — improving skin tone often regresses foliage or sky. Include the key memory-color test scenes in regression testing from the start of tuning.
- **Validate fluorescent scenes separately.** TL84 (4000 K, narrow-band) is the most common AWB failure illuminant because its narrow green-band peak causes statistical estimators to overestimate CCT. Standard test: photograph a Macbeth gray ramp under TL84; the three-channel means of the neutral gray patches should agree within ±3 DN (8-bit). Deviation > 5 DN indicates the 4000 K anchor point needs dedicated calibration.
- **When not to use ML-AWB:** For mid-to-low-end platforms where the sensor model changes every product cycle and there is no infrastructure to collect sensor-specific multi-illuminant RAW training data, the maintenance cost of ML-AWB (retraining on sensor change, poor edge-case generalization) exceeds its accuracy benefit. Traditional Gamut Mapping + thorough edge-case tuning is the more stable mass-production path.

---

## §8 Glossary

**Color Constancy**
The ability of the human visual system to perceive object colors as stable under different illumination conditions (e.g., white paper appears white under both tungsten and daylight). Camera sensors lack this ability; AWB algorithms compensate by estimating the illuminant color and applying gain corrections. The mathematical framework was established by Buchsbaum (1980).

**Gray World Assumption**
A color constancy prior proposed by Buchsbaum (1980): the spatial average of all colors in a natural image equals gray (i.e., three-channel means are equal). This allows each channel mean to serve directly as an illuminant estimate; gains are $W_c = \bar{G}/\bar{c}$. Computationally minimal, but fails severely in scenes with a strong dominant color (red flowers, green grass, etc.).

**White Patch / MaxRGB**
Assumes the brightest pixel in the scene is a white (fully reflective) surface; its color equals the illuminant. Gains: $W_c = \max_G / \max_c$. In practice the 99th percentile replaces the absolute maximum to suppress sensor hot pixels. Effective when the scene contains a highly reflective white object; fails when no such object is present.

**Shades-of-Gray (Minkowski p-norm color constancy)**
Finlayson & Trezzi (2004) unify Gray World ($p=1$) and White Patch ($p \to \infty$) under the Minkowski $L^p$ norm: $\left(\frac{1}{N}\sum |I_c|^p\right)^{1/p}$ is equal across channels. $p=6$ is a commonly cited empirical setting that performs well on several datasets, but the optimal $p$ varies across datasets, sensors, and scene conditions — it is not a universal constant.

**Generalized Gray Edge**
van de Weijer et al. (2007) extended the Minkowski framework to image gradients ($n=1, 2$), unifying pixel-statistics-based ($n=0$) and gradient-based color constancy algorithms into a single parameterized family. The key insight: image gradients eliminate the DC component of scene reflectance and carry more robust illuminant information than raw pixel values. The first-order variant ($n=1, p=1$) achieves a Trimean angular error of ~2.78° on Gehler-Shi, significantly better than Gray World (6.28°).

**Angular Error**
The standard accuracy metric for color constancy: the angle (in degrees) between the estimated and ground-truth illuminant vectors. Reported statistics include Mean, Median, and Trimean (= $(Q_1 + 2Q_2 + Q_3)/4$). Trimean is more robust than the mean to outlier large errors and is the currently preferred single-number metric in the literature. For the right-skewed angular error distribution, $\text{Median} \leq \text{Trimean} \leq \text{Mean}$.

**Gehler-Shi Dataset**
The most widely used color constancy benchmark, comprising 568 RAW images each captured with a Macbeth ColorChecker in the scene; ground-truth illuminant color is derived from the known reflectances of the checker's neutral patches (Shi & Funt 2010 re-processed version). Note that the ground truth is estimated, not directly measured from a spectroradiometer.

**Correlated Color Temperature (CCT)**
Maps an illuminant chromaticity to the temperature (in Kelvin) of the nearest blackbody radiator on the Planckian locus. Standard illuminants: D65 = 6504 K, A = 2856 K, TL84 = 4000 K. CCT alone does not fully characterize an illuminant: two sources with the same CCT but different spectral power distributions (e.g., TL84 vs. a blackbody at 4000 K) differ in their Δuv value and require different AWB gains. Robertson (1968) provides the engineering-standard fast CCT computation via linear interpolation in CIE $uv$.

**Planckian Locus**
The curve in a CIE chromaticity diagram traced by blackbody (Planckian) radiators across all temperatures. CCT is computed by finding the closest point on the locus. Real illuminants such as fluorescent lamps and LEDs typically lie off the locus; their displacement is quantified by Δuv.

**Δuv (delta uv)**
The signed perpendicular distance from an illuminant's CIE 1976 $u'v'$ chromaticity to the Planckian locus. Positive Δuv indicates a green shift; negative Δuv indicates a magenta shift. TL84 has Δuv ≈ +0.008 to +0.012; CWF has Δuv ≈ +0.005 to +0.010. Engineering documentation for fluorescent sources should always report (CCT, Δuv) pairs.

**AWB Gain (White Balance Gain)**
The core correction parameters: $[W_R, W_G, W_B] = [G_\text{illum}/R_\text{illum},\; 1.0,\; G_\text{illum}/B_\text{illum}]$, referenced to the green channel (industry convention). Gains may be applied in the post-demosaic RGB domain or directly in the RAW Bayer domain (the RAW-domain approach avoids introducing demosaic interpolation errors).

**IIR Temporal Smoothing**
The standard anti-jitter method for video AWB: $W_c^\text{smooth}[n] = \alpha W_c^\text{raw}[n] + (1-\alpha)W_c^\text{smooth}[n-1]$. Smaller $\alpha$ means slower convergence and better stability (typical static-scene value 0.03–0.08); larger $\alpha$ (e.g., 0.3) is used adaptively on detected scene cuts to accelerate tracking.

**Color Hunting (AWB Oscillation)**
A video artifact in which AWB gains oscillate between adjacent frames, producing continuous slight color flickering. Root cause: inherent randomness in the per-frame illuminant estimate combined with an IIR smoothing coefficient $\alpha$ that is too large. Remedies: reduce $\alpha$; add a gain dead band (update only when $|\Delta W_c| > 0.02$).

**Fast Fourier Color Constancy (FFCC)**
Barron & Tsai (CVPR 2017): reformulates color constancy as a cross-correlation in log-chrominance space, exploiting FFT to reduce inference to $O(N \log N)$. Trimean angular error ≈ 1.01° on Gehler-Shi; millisecond-range inference, suitable for mobile real-time deployment.

**NUS-8 Camera Dataset**
Cheng et al. (CVPR 2014) large-scale color constancy benchmark: ~200 images from each of 8 different cameras, 1736 images total. Covers sensor-to-sensor variation; useful for evaluating cross-camera generalization (unlike Gehler-Shi, which uses only one or two cameras).

---

## References

1. **Buchsbaum, G.** (1980). A spatial processor model for object colour perception. *Journal of the Franklin Institute*, 310(1), 1–26. — Foundational paper on color constancy; introduces the gray world assumption mathematical framework.

2. **van de Weijer, J., Schmid, C., Verbeek, J., & Larlus, D.** (2007). Edge-based color constancy. *IEEE Transactions on Image Processing*, 16(7), 1536–1545. — Generalized Gray Edge algorithm; unifies gradient-based color constancy into a single framework.

3. **Finlayson, G. D., & Trezzi, E.** (2004). Shades of gray and colour constancy. *12th Color Imaging Conference*, 37–41. — Minkowski p-norm framework; unifies Gray World and White Patch into a single formula.

4. **Shi, L., & Funt, B.** (2010). Re-processed version of the Gehler color constancy dataset. Technical report, Simon Fraser University. — The most widely used color constancy benchmark dataset.

5. **Barron, J. T.** (2015). Convolutional color constancy. *Proceedings of ICCV 2015*, 379–387. — CNN method that first substantially outperformed classical algorithms on the Gehler-Shi dataset (mean angular error 1.95°).

6. **Hu, Y., Wang, B., & Lin, S.** (2017). FC4: Fully convolutional color constancy with confidence-weighted pooling. *CVPR 2017*. — Fully convolutional AWB network with confidence-weighted pooling.

7. **Barron, J. T., & Tsai, Y. T.** (2017). Fast Fourier Color Constancy. *CVPR 2017*. — FFT-based color constancy estimation; achieves ~1.78° mean angular error on Gehler-Shi at millisecond inference speed.

8. **Afifi, M., & Brown, M. S.** (2020). Deep White-Balance Editing. *CVPR 2020*. — Post-ISP sRGB white-balance correction trained on camera-rendered images.

9. **Cheng, D., Price, B., Cohen, S., & Brown, M. S.** (2014). Effective learning-based illuminant estimation using simple features. *CVPR 2014*. — NUS-8 Camera dataset; large-scale color constancy benchmark across 8 cameras.

10. **Robertson, A. R.** (1968). Computation of correlated color temperature and distribution temperature. *Journal of the Optical Society of America*, 58(11), 1528–1535. — Robertson method; engineering standard for fast CCT computation.

11. **Ebner, M.** (2007). *Color Constancy*. Wiley. — Systematic monograph on color constancy theory.

12. **Wang, W., et al.** (2022). C5: Cross-Camera Convolutional Color Constancy. *CVPR 2022*. — Cross-camera domain adaptation for ML-AWB; achieves Angular Error ≈ 1.5° on real RAW data.

13. **Lo, Y., et al.** (2022). CLCC: Contrastive Learning for Color Constancy. *ECCV 2022*. — Contrastive learning for cross-camera domain adaptation; Median Angular Error 1.48° on NUS-8.

14. **Wang, J., et al.** (2023). Exploring CLIP for Assessing the Look and Feel of Images. *AAAI 2023*. — CLIP-IQA; SRCC ≈ 0.85–0.87 on general IQA datasets; requires in-domain validation before applying to ISP-specific AWB evaluation.

15. **Wu, H., et al.** (2024). Q-Bench: A Benchmark for General-Purpose Foundation Models on Low-level Vision. *ICLR 2024*. arXiv:2309.14181. — Multimodal foundation model benchmark for low-level vision quality assessment.

16. **carlyleliu** (2021). ISP RAW-domain AWB deep dive. carlyleliu.github.io. — Fluorescent lamp Δuv displacement and metamerism analysis; engineering reference for TL84/CWF calibration.

17. **SigmaStar** (internal). SSD238X IQ Tuning Reference Manual. comake.online. — Fluorescent calibration workflow and gamut parameter configuration.

18. **CIE Publication 15.3:2004**. Colorimetry, 3rd edition. Commission Internationale de l'Éclairage, 2004. — CIE standard illuminant F-series SPDs and Δuv definition.

19. **Gijsenij, A., Gevers, T., & van de Weijer, J.** (2011). Computational color constancy: Survey and experiments. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 33(9), 1861–1882. — Comprehensive survey of color constancy algorithms including multi-illuminant decomposition.

---

*Chapter 22 of the ISP Algorithm Handbook — Part 2: Traditional ISP Algorithms*
