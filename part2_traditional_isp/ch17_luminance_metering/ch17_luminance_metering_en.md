# Part 2, Chapter 17: Scene Luminance Analysis and Perceptual Metering

> **Pipeline Position:** 3A Control Layer — AE Statistics Collection Module, operating in RAW-domain or YUV-domain statistical analysis stage
> **Prerequisite Chapters:** Part 1, Chapter 03 (Sensor Physics), Part 1, Chapter 07 (Dynamic Range and HDR), Part 2, Chapter 07 (Gamma and Tone Mapping), Part 4, Chapter 02 (Auto Exposure Algorithm Fundamentals)
> **Target Readers:** 3A Algorithm Engineers, Luminance Tuning Engineers, ISP System Engineers
> **Scope note:** This chapter covers the **luminance statistics analysis layer** (histogram analysis, metering mode image analysis algorithms, perceptual metering weights). Exposure control decisions, exposure triangle calculation, and PID convergence loop are covered in **Part4 Ch77 (Auto Exposure Fundamentals)**.

---

## §1 Theory

### 1.1 Perceptual Luminance Models

#### 1.1.1 Physical Luminance vs. Perceived Brightness

Physical luminance (measured in cd/m²) is an objective, measurable quantity, whereas **perceived brightness** is a subjective quantity produced by the human visual system (HVS). The nonlinear relationship between these two quantities forms the starting point for all metering algorithm design.

**Weber–Fechner Law (Differential Perception):**

$$\Delta E = k \cdot \frac{\Delta I}{I}$$

Here $I$ is the background luminance, $\Delta I$ is the minimum perceptible luminance difference, and $k \approx 0.02$ (JND ≈ 2%). This law implies that in dark regions, even a tiny luminance change is perceptible, whereas in bright regions a much larger absolute luminance change is needed to produce an equivalent perceptual difference.

**Stevens' Power Law (Absolute Brightness Perception):**

$$\Psi = k \cdot I^{0.33}$$

Here $\Psi$ is perceived brightness; the exponent 0.33 is the compression factor with which the visual system handles wide dynamic range. This relationship is one of the physiological justifications for choosing $\gamma \approx 1/3$ in Gamma encoding.

**Practical Approximation (CIE L*):**

The $L^*$ component of CIELAB is the most widely used engineering approximation of perceived brightness:

$$L^* = \begin{cases}
116 \cdot \left(\dfrac{Y}{Y_n}\right)^{1/3} - 16 & \text{if } \dfrac{Y}{Y_n} > 0.008856 \\
903.3 \cdot \dfrac{Y}{Y_n} & \text{otherwise}
\end{cases}$$

where $Y$ is linear luminance and $Y_n$ is the white-point luminance. $L^*$ maps $[0, 100]$ to a perceptually uniform brightness space. AE systems often express the target brightness in terms of $L^*$ rather than raw linear pixel values.

#### 1.1.2 The APEX Exposure System

APEX (Additive system of Photographic EXposure) maps all exposure-related quantities to a base-2 logarithmic domain, so that addition and subtraction correspond to multiplication and division of exposure:

| APEX Quantity | Symbol | Definition | Example |
|---------------|--------|------------|---------|
| Aperture Value | $A_v = \log_2 N^2$ | $N$ = f-number | f/2.0 → $A_v$ = 2 |
| Time Value | $T_v = \log_2(1/t)$ | $t$ = shutter time (s) | 1/250s → $T_v$ = 8 |
| Speed Value | $S_v = \log_2(\text{ISO}/3.125)$ | — | ISO 100 → $S_v$ = 5 |
| Brightness Value | $B_v = \log_2(L/1.0752)$ | $L$ = scene luminance (cd/m²) | — |
| Exposure Value | $E_v = A_v + T_v$ | conventional EV | — |

The exposure equation in the APEX domain reduces to a simple linear relationship:

$$E_v = B_v + S_v$$

This means: **scene brightness value + ISO gain value = required exposure value**. The core task of an AE algorithm is to estimate $B_v$ from statistical data and then compute the optimal combination of $(A_v, T_v, S_v)$ to achieve the target $E_v$.

#### 1.1.2b Complete EV Derivation from Scene Luminance

Combining the four APEX equations yields the complete mapping from scene luminance $L$ (cd/m²) to the exposure triangle ($N$, $t$, ISO):

$$E_v = A_v + T_v = B_v + S_v$$

Expanding into physical quantities:

$$\log_2 N^2 + \log_2 \frac{1}{t} = \log_2 \frac{L}{1.0752} + \log_2 \frac{\text{ISO}}{3.125}$$

Rearranging gives the normalized Exposure Value at ISO 100:

$$\boxed{EV_{100} = \log_2 \frac{L \cdot S_{\text{ISO}}}{K}}$$

where:
- $EV_{100}$ is the ISO-100-normalized exposure value
- $S_{\text{ISO}}$ is the camera ISO sensitivity (100 for ISO 100)
- $K$ is the metering calibration constant; ISO 2720 specifies $K = 12.5$ (calibrated to an 18%-reflectance gray card for reflected-light metering)

**Direct formula from scene luminance to exposure triangle:**

$$\frac{N^2}{t} = \frac{L \cdot \text{ISO}}{K} = \frac{L \cdot \text{ISO}}{12.5}$$

Engineering implication: given $L$ (estimated from metering statistics) and a target ISO, compute $N^2/t$ directly. The AE algorithm's core task is then to allocate this "exposure factor" among the three parameters according to a priority policy (shutter-priority / aperture-priority / ISO-priority).

**Numerical examples:**

| Scene Luminance $L$ | ISO | Required $N^2/t$ | Typical Parameters |
|---------------------|-----|------------------|--------------------|
| 4000 cd/m² (sunny outdoor) | 100 | 32000 | f/5.6, 1/1000 s |
| 400 cd/m² (bright indoor) | 100 | 3200 | f/4.0, 1/200 s |
| 40 cd/m² (dim indoor) | 800 | 2560 | f/2.0, 1/640 s |
| 4 cd/m² (night street) | 3200 | 1024 | f/2.0, 1/256 s |

#### 1.1.3 Scene Key (Representative Scene Brightness)

The critical parameter in photographic metering is the **midtone brightness of the scene** — Zone V (18% gray) in Ansel Adams' Zone System. The AE objective is to map the "representative brightness" of the scene to this target zone:

$$L_{\text{target}} = 0.18 \cdot L_{\text{max\_encodable}}$$

In practice, the definition of "representative brightness" is what differentiates metering algorithms:
- **Average Metering:** Full-frame average luminance; susceptible to extreme values.
- **Center-Weighted Metering:** Higher weight on the central region; suited for portraiture.
- **Matrix/Evaluative Metering:** Multi-zone weighting combined with scene content analysis.
- **Spot Metering:** Metering only in a very small area around the focus point; precise control.

---

### 1.2 Internal Algorithm of Multi-Zone Matrix Metering

Matrix metering (called Matrix Metering by Nikon and Evaluative Metering by Canon) is the dominant metering mode in modern cameras and smartphone ISPs. Its internals are far more sophisticated than they appear.

#### 1.2.1 Zone Partitioning and Luminance Statistics

The frame is divided into $M \times N$ zones (typical range: 16×16 to 64×64). For each zone $(i, j)$, the mean luminance is computed:

$$\bar{Y}_{ij} = \frac{1}{|R_{ij}|} \sum_{(x,y) \in R_{ij}} Y(x,y)$$

where $Y(x,y)$ is either the Y component of YUV or the mean of the Green channel in the RAW domain.

#### 1.2.2 Multi-Factor Weight Fusion per Zone

The weight $w_{ij}$ assigned to each zone is the product of multiple factors:

$$w_{ij} = w_{ij}^{\text{pos}} \cdot w_{ij}^{\text{face}} \cdot w_{ij}^{\text{focus}} \cdot w_{ij}^{\text{highlight}}$$

**Position weight $w_{ij}^{\text{pos}}$ (spatial prior):**

```
The center region receives the highest weight, decaying toward the edges via a Gaussian:
w_pos(i,j) = exp(-((i-H/2)²+(j-W/2)²) / (2σ²))
σ ≈ 0.25 × min(H,W)
```

**Face region weight $w_{ij}^{\text{face}}$:**
- When a face is detected: weight of zones overlapping the face bounding box is boosted by 2–4×.
- Face metering target: map the skin region luminance to $L^* = 60$–$70$ (slightly above midtone).
- No face detected: $w^{\text{face}} = 1.0$ (no boost applied).

**Focus point weight $w_{ij}^{\text{focus}}$:**
- Weight near the focus region is boosted by 1.5–2×.
- Reflects the metering priority given to the "subject the user is interested in."

**Highlight suppression weight $w_{ij}^{\text{highlight}}$:**

$$w_{ij}^{\text{highlight}} = \begin{cases}
0.2 & \text{if } \bar{Y}_{ij} > 0.95 \cdot Y_{\max} \quad \text{(overexposed highlights downweighted)} \\
1.0 & \text{otherwise}
\end{cases}$$

#### 1.2.3 Weighted Average and EV Estimation

Final representative scene luminance:

$$\bar{Y}_{\text{scene}} = \frac{\sum_{ij} w_{ij} \cdot \bar{Y}_{ij}}{\sum_{ij} w_{ij}}$$

Conversion to the EV domain:

$$B_v = \log_2\!\left(\frac{\bar{Y}_{\text{scene}} / Y_{\text{max}} \cdot L_{\text{display\_max}}}{1.0752}\right)$$

The target exposure value $E_v^{\text{target}} = B_v + S_v$ is fed into the AE PI controller to update exposure parameters.

#### 1.2.4 Scene Type Recognition and Weight Adaptation

Modern matrix metering incorporates a lightweight scene classifier:

```
Inputs: luminance histogram + per-zone highlight ratio + per-zone contrast
→ Classification output: {backlit, front-lit, low-light, high dynamic range, uniform, point source}
→ Each scene type maps to a preset weight template
```

Examples:
- **Backlit scene (dark foreground / bright background):** Increase foreground weight in the center zone; reduce highlight weight in the background.
- **Low-light scene (full-frame mean < 20/255):** Lower the highlight clipping threshold to avoid overexposure.
- **High-contrast scene (HDR):** Trigger multi-frame AEB or HDR frame-merging strategy.

---

### 1.3 Histogram-Based AE Target Analysis

Histogram analysis is a powerful complement to matrix metering, particularly for detecting overexposure/underexposure and measuring dynamic range utilization.

#### 1.3.1 Luminance Histogram Normalization and Integration

Let the luminance histogram be $H[k]$ ($k = 0, \ldots, 255$); the normalized probability density is:

$$p[k] = \frac{H[k]}{\sum_k H[k]}$$

Cumulative distribution function (CDF):

$$F[k] = \sum_{j=0}^{k} p[j]$$

**Highlight Clipping Ratio:**

$$r_{\text{high}} = 1 - F[240]$$

When $r_{\text{high}} > 0.02$ (2% of pixels overexposed), the AE system triggers a reduce-exposure correction.

**Shadow Clipping Ratio:**

$$r_{\text{low}} = F[15]$$

When $r_{\text{low}} > 0.05$ (5% of pixels underexposed), the AE system triggers an increase-exposure correction.

#### 1.3.2 Histogram-Based AE Target

Derive the target exposure from the expected CDF shape:

$$k_{\text{target}} = \arg\min_k \left| F[k] - 0.50 \right|$$

Map $k_{\text{target}}$ to the target brightness (18% gray ≈ 117/255):

$$\Delta E_v = \log_2\!\left(\frac{117}{k_{\text{target}}}\right)$$

Adjust exposure parameters by $\Delta E_v$. This approach works well when scene luminance is roughly uniform, but must be combined with content analysis for bimodal histograms (backlit scenes).

#### 1.3.3 Histogram Analysis for Multi-Peak Scenes

For complex scenes with multiple distinct luminance regions (e.g., an indoor portrait against a bright window), histogram peak detection can identify them:

```python
from scipy.signal import find_peaks

peaks, properties = find_peaks(H_smooth, height=0.02 * H_max,
                                distance=30, prominence=0.01 * H_max)
if len(peaks) >= 2:
    # Bimodal: likely a backlit scene
    foreground_peak = peaks[0]   # dark peak (foreground subject)
    background_peak = peaks[-1]  # bright peak (background)
    # AE target prioritizes foreground; highlights may clip
    target_brightness = foreground_peak + 20  # foreground brightening offset
```

---

### 1.4 Engineering Implementation of Face-Priority Metering

#### 1.4.1 Face Brightness Target

The skin brightness target varies by skin tone, but typical target ranges in sRGB space are:

| Skin Type | $L^*$ Target | Approximate sRGB Y |
|-----------|-------------|---------------------|
| Light (Fitzpatrick I–II) | 65–75 | 0.37–0.52 |
| Medium (III–IV) | 55–65 | 0.26–0.37 |
| Dark (V–VI) | 45–55 | 0.17–0.26 |

In engineering practice, a **fixed target** of $L^* = 62$ is often used (suitable for most common skin tones), with a user-adjustable offset (±10 $L^*$) to accommodate individual variation.

#### 1.4.2 Multi-Face Brightness Arbitration

When multiple faces are present in the scene, a "primary face" must be selected for metering:

```
Priority order:
1. The face closest to the focus point (primary AF subject)
2. The largest face bounding box (nearest person)
3. The face nearest the center of the frame

Weighting strategy: primary face weight = 0.6; remaining faces share the rest
```

#### 1.4.3 Foreground/Background Luminance Separation

When the luminance difference between the face and background exceeds 2 EV, foreground/background separated metering is triggered:

$$\Delta EV_{\text{face-bg}} = |\log_2(\bar{L}_{\text{face}}) - \log_2(\bar{L}_{\text{bg}})|$$

> ⚠️ **Note:** $\bar{L}$ in the formula above denotes **linear scene luminance**, not gamma-encoded pixel values $Y$. If $\log_2$ is applied directly to sRGB/Rec.709-encoded values, the EV difference is compressed by a factor of approximately 2.2 (since $Y \approx L^{1/2.2}$), causing the trigger threshold to be inaccurate. ISP implementations should compute this in the RAW linear domain or after inverse-gamma correction.

If $\Delta EV_{\text{face-bg}} > 2$:
- **Option A (face priority):** Set exposure to meet the face brightness target; background may clip or underexpose.
- **Option B (HDR trigger):** Multi-frame AEB followed by frame merging to preserve full detail.
- The choice is made by the scene detection module.

---

### 1.5 AI-Assisted Intelligent Metering

AI metering in flagship smartphones is not a revolutionary new architecture. The underlying logic across Google Pixel Night Sight, iPhone 13 Subject-Aware AE, and Xiaomi Ultra scene recognition is essentially the same: a **lightweight classifier + rule engine**. True end-to-end neural AE hits engineering constraints — black-box non-tunability, high annotation cost, poor generalization on edge cases. Most production AI-AE systems therefore follow Architecture A (classifier-assisted), with Architecture B (end-to-end prediction) reserved mainly for night-scene boundary conditions.

#### 1.5.1 Two AI Metering Architectures

**Architecture A: Lightweight Classifier + Rule Engine Enhancement**

A lightweight CNN (typically < 1 MB, MobileNet backbone) is added on top of conventional matrix metering. It processes a low-resolution input (e.g., $64 \times 48$) and produces a "scene semantic vector" — a 6-dimensional probability vector over categories such as {portrait, landscape, night, high-dynamic, low-light, backlit}. This vector then drives dynamic adjustment of zone weight templates and EV offset:

$$EV_{\text{final}} = EV_{\text{matrix}} + f(\mathbf{p}_{\text{scene}}, \Delta_{EV})$$

where $\mathbf{p}_{\text{scene}}$ is the scene classification probability vector and $\Delta_{EV}$ is an offline-calibrated EV correction table indexed by scene category.

**Advantages:** Interpretable, extremely low compute (< 1 ms NPU inference), easy to tune. Typical deployment: Qualcomm Spectra platform Scene Intelligence AE module integrated into the CamX AEC node.

**Architecture B: End-to-End Neural AE Prediction**

The image itself (low resolution, e.g., $128 \times 96$) is fed directly to a network that outputs a target EV (or exposure triangle parameters):

$$\hat{EV} = f_{\theta}(I_{\text{preview}})$$

Network structure: lightweight CNN (SqueezeNet or MobileNetV3 backbone) + regression head, trained on professionally annotated "optimal exposure" datasets (typically 100 k+ images).

**Advantages:** Better generalization on complex scenes (multiple faces, complex lighting, artistic photography). **Disadvantages:** Higher inference latency (NPU ≈ 2–5 ms), large annotation requirement, black-box and difficult to tune.

#### 1.5.2 Google Pixel Night Sight Metering Strategy

Google Night Sight (introduced with Pixel 3 in 2018) innovates in metering by decoupling "multi-frame exposure decision" from "metering statistics" for extreme low-light scenes (< 3 lux), where conventional metering is unreliable due to very weak signal:

1. **Fast preview metering:** A short-exposure (< 1/100 s) + high-ISO (3200+) preview frame estimates the scene luminance distribution (despite very low SNR, sufficient to determine the brightness range).
2. **Target exposure decision:** Based on predicted scene luminance, select the optimal exposure time (typically 10–33 ms, i.e., 1/100 s–1/30 s) × frame count for multi-frame AEB.
3. **Frame alignment + merging:** Aligned multi-frame captures (typically 6–15 frames) are merged in the RAW domain using Wiener-filter-type fusion, equivalently extending SNR.
4. **Post-merge re-metering:** After producing a high-SNR merged image, metering is performed again (now reliable statistics) to guide the final tone-mapping step.

#### 1.5.3 Apple Subject-Aware AE

iOS 15+ (iPhone 13 onward) introduced Vision framework-based subject-aware AE that extends face recognition to also identify pets, plants, text, and other subjects. Different brightness targets are used for different subject types:

| Subject Type | $L^*$ Target Range | Notes |
|--------------|-------------------|-------|
| Face (skin) | 60–70 | Tiered by skin tone |
| Pet (cat/dog face) | 45–65 | Large reflectance variation in animal fur |
| Text / document | 75–85 | Maximize text legibility |
| Plant (green leaves) | 55–65 | Avoid overexposure that loses green detail |
| No subject (landscape) | 50–60 (scene mean) | Falls back to matrix metering |

---

### 1.6 Metering Strategy for Flickering Scenes (Neon / Stage Lights)

Flickering light sources are a classic challenge for metering systems. Fixed-threshold strategies produce severe exposure oscillation, and dedicated strategies are needed.

#### 1.6.1 Classification of Flickering Light Sources

| Source Type | Flicker Frequency | Characteristics | Main Challenge |
|-------------|-------------------|----------------|----------------|
| Mains-powered fluorescent / LED | 100/120 Hz (2× mains frequency) | Periodic, stable amplitude | Frame rate out of sync with flicker → inconsistent exposure |
| Neon signs | 50/60 Hz (transformer frequency) | Strong flicker, large amplitude (> 50% variation) | Frame-to-frame luminance difference > 1 EV |
| Stage / DMX lighting | 0.5–50 Hz (programmable) | Non-periodic, rapid transitions | AE PI controller cannot respond quickly enough |
| LED panels / display backgrounds | 120–480 Hz (PWM) | High frequency; banding visible at low frame rates | Banding + metering error |

#### 1.6.2 Anti-Flicker AE for Mains-Frequency Sources

The standard anti-flicker strategy locks exposure time to an integer multiple of the power cycle:

$$t_{\text{exposure}} = n \cdot T_{\text{flicker}}, \quad n \in \{1, 2, 3, \ldots\}$$

where $T_{\text{flicker}} = 1/(2 f_{\text{mains}})$ (10 ms for 50 Hz mains, ≈ 8.33 ms for 60 Hz mains). When exposure time equals an integer multiple of the flicker period, the sensor integrates the same number of complete light-intensity cycles in every exposure interval, eliminating frame-to-frame luminance variation.

**Constraint:** Exposure time is discretized to an arithmetic series (10 ms, 20 ms, 30 ms, …), removing continuous control. ISPs typically compensate luminance by adjusting analog gain rather than fine-tuning exposure time.

#### 1.6.3 Strategies for Non-Periodic Flickering (Neon / Stage Lights)

For non-mains-periodic flicker (neon signs at 50 Hz but with variable duty cycle and amplitude; stage lights fully non-periodic), simple anti-flicker cannot solve the problem. The following combined strategies are used in production:

**Strategy 1: Temporal Metering Smoothing**

Apply stronger temporal low-pass filtering to metering results to suppress metering jitter caused by flicker:

$$EV_{\text{metering}}^{(t)} = (1-\beta) \cdot EV_{\text{metering}}^{(t-1)} + \beta \cdot EV_{\text{raw}}^{(t)}$$

In flickering scenes, reduce $\beta$ from the normal range (≈ 0.3–0.5) to 0.05–0.15. The cost is slower AE response (approximately 20–40 frames to converge).

**Strategy 2: Inter-Frame Difference Detection for Flicker Identification**

Monitor variance of global luminance across consecutive frames to detect flickering scenes and automatically switch to low-$\beta$ mode:

```python
def detect_flicker(ev_history, window=10):
    if len(ev_history) < window:
        return False
    ev_window = ev_history[-window:]
    ev_variance = np.var(ev_window)
    # Normal scene variance < 0.01 EV²; flicker scene variance > 0.05 EV²
    return ev_variance > FLICKER_VARIANCE_THRESHOLD  # typical 0.03 EV²
```

**Strategy 3: Temporal Histogram Accumulation**

Accumulate weighted luminance histograms over $K$ consecutive frames (typical $K = 3$–$5$) and use the time-averaged histogram to compute the AE target:

$$H_{\text{accum}}[l] = \sum_{k=0}^{K-1} \alpha_k \cdot H^{(t-k)}[l], \quad \sum \alpha_k = 1$$

Multi-frame integration averages out histogram drift caused by inter-frame flicker, stabilizing the AE target. Qualcomm Spectra `AEC_HistogramBins` supports multi-frame histogram accumulation (default 1 frame; 3–5 frames recommended for flickering scenes).

**Strategy 4: AE Lock Guidance**

For extreme stage-light flicker (e.g., DMX lights with frequent on/off transitions), the system can detect flicker and prompt the user to engage **AE Lock** (freeze exposure at the current value), combined with a relatively fast shutter (> 1/200 s) to capture instantaneous poses without instability from continuous auto-exposure.

#### 1.6.4 Platform Parameter Configuration

| Platform | Flicker Detection Parameter | Flicker Metering Strategy Parameter |
|----------|-----------------------------|-------------------------------------|
| Qualcomm CamX | `AEC_AntiFlickerMode = Auto` (auto-detect 50/60 Hz) | `AEC_FlickerTemporalSmooth` (recommended 0.1), `AEC_HistAccumFrames` (recommended 3) |
| MediaTek Imagiq | `AEAntiFlicker = ENUM_AUTO` | `AEFlickerSmoothingFactor` (float, 0.1–0.2) |
| HiSilicon Yueying | `AE_FlickerMode = AUTO` | `AE_FlickerSmoothGain` (recommended 0.15) |

> **Tuning note:** `AntiFlickerMode = Auto` relies on spectral analysis (FFT of the per-frame global luminance sequence) and may misfire outdoors or under mixed light sources. In known non-fluorescent environments (outdoor sunlight), set the mode to `DISABLED` manually to avoid unnecessary discretization of exposure time.

---

## §2 Calibration

### 2.1 Metering Target Brightness Calibration

Use an 18% gray card (standard Macbeth ColorChecker patch #20):

```
Steps:
1. Place the 18% gray card under a uniform diffuse illuminant
   (e.g., integrating sphere, 6500 K, CRI ≥ 95).
2. Fix ISO 100; set manual exposure so the sensor linear output is
   approximately 40–50% of saturation.
3. Record the YUV Y-channel mean at this setting → this value defines
   the AE target brightness Y_target.
4. Write Y_target into the AE parameter table
   (typically 128/255 or normalized 0.18).
```

### 2.2 Offline Calibration of Zone Weights

The zone weights for matrix metering are typically tuned as follows:

1. **Collect a test set:** Cover portrait, landscape, backlit, low-light, and night-scene categories with 200+ images each; professional photographers provide reference exposures (ground-truth EV).
2. **Loss function:** Minimize the mean squared error between predicted and reference EV:
   $$\mathcal{L} = \sum_{\text{scene}} \left( EV_{\text{predicted}} - EV_{\text{reference}} \right)^2$$
3. **Optimization method:** Gradient descent or grid search (weight parameter count is typically < 100, so exhaustive search or Bayesian optimization is feasible).

### 2.3 A/B Test Calibration of Face Brightness Target

Conduct a user study before mass production to determine the face brightness target:
- Show 50+ evaluators side-by-side comparisons at different face brightness levels ($L^*$ = 55 / 60 / 65 / 70).
- Choose the $L^*$ value with the highest satisfaction rate as the default target.
- Calibrate separately for Asian, Caucasian, and dark-skin subject groups.

---

## §3 Tuning

### 3.1 Exposure Target Offset (EV Compensation)

Users can shift overall exposure by ±3 EV; internally this is implemented by directly modifying $Y_{\text{target}}$:

$$Y_{\text{target}}' = Y_{\text{target}} \cdot 2^{\Delta EV}$$

Typical presets:
- **Portrait mode:** +0.3 EV (brighter face; shadows can be relaxed).
- **Landscape mode:** 0 EV (faithful luminance reproduction).
- **Night mode:** −0.5 EV (protect highlights; prevent light sources from blowing out).

### 3.2 Highlight Protection Strength

Controls the $r_{\text{high}}$ trigger threshold and response speed:

| Parameter | Conservative (reduce overexposure) | Standard | Aggressive (prefer underexposure) |
|-----------|-----------------------------------|----------|----------------------------------|
| Highlight clipping threshold | 0.01 (1%) | 0.02 (2%) | 0.05 (5%) |
| Highlight zone downweight factor | 0.1 | 0.2 | 0.4 |
| EV reduction step size | 0.5 EV/frame | 0.3 EV/frame | 0.2 EV/frame |

### 3.3 Zone Weight Map and Face Detection Bounding Box Integration

**Engineering coupling gap:** §1.2.2 describes the role of face weight $w_{ij}^{\text{face}}$ but does not explain how face detection bounding-box coordinates are mapped to the zone weight table, or what the specific platform parameters are.

**Mapping mechanism:**

The zone weight map used in matrix metering is a 2-D integer matrix (15×15 on Qualcomm, 9×9 on MediaTek). Face detection provides normalized coordinates $(x_1, y_1, x_2, y_2) \in [0,1]^4$. The AE module maps these to grid indices and multiplies the covered cells by the face weight scale `AEC_FaceWeightScale`.

**Mapping formula (Qualcomm 15×15 weight table example):**

$$i_{\text{face}} = \text{round}\!\left(x_{\text{face\_center}} \times 14\right), \quad j_{\text{face}} = \text{round}\!\left(y_{\text{face\_center}} \times 14\right)$$

Range of cells covered by the face bounding box:

$$i \in \left[\lfloor x_1 \times 14 \rfloor,\ \lceil x_2 \times 14 \rceil\right], \quad j \in \left[\lfloor y_1 \times 14 \rfloor,\ \lceil y_2 \times 14 \rceil\right]$$

Covered cells: weight = original position weight × `AEC_FaceWeightScale` (typical 2.0–4.0). Uncovered cells are unchanged.

**Two-platform parameters for face-weight switching:**

| Function | Qualcomm Chromatix Parameter | MediaTek NDD Parameter |
|----------|------------------------------|------------------------|
| Face weight multiplier | `AEC_FaceWeightScale` (float, typical 2.0–4.0) | `AEFaceWeight` (NDD float, typical 2.0–3.5) |
| Face detection confidence threshold | `AEC_FaceDetectConfidenceThresh` (float [0,1], typical 0.75–0.85) | `AEFaceConfidenceThreshold` (NDD float, 0.7–0.8) |
| Face weight temporal smoothing | `AEC_FaceWeightSmoothTC` (time constant in frames, typical 5–10) | `AEFaceWeightSmoothFrames` (NDD int, 5–8) |
| Multi-face primary selection | `AEC_FaceSelectMode` (enum: Largest/Closest/Centered) | `AEFaceSelectStrategy` (NDD enum) |
| Face weight fade-out on loss | `AEC_FaceWeightFadeoutFrames` (frames to ramp back to 1.0, typical 10–20) | `AEFaceWeightFadeFrames` (NDD int) |

**Handling detection rate lower than ISP frame rate:**

Face detection runs at 15–30 fps (NPU inference limit) while the ISP runs at 30–120 fps. Between detections, the Qualcomm AE node uses the **last valid result** (Hold Last Valid), applying temporal smoothing via `AEC_FaceWeightSmoothTC` to prevent sudden jumps. MediaTek uses `AEFaceWeightSmoothFrames` similarly. If no updated detection result arrives within `AEC_FaceDetectTimeout` (typically 10 frames ≈ 333 ms at 30 fps), the system treats the face as lost and ramps the weight back to 1.0 over `AEC_FaceWeightFadeoutFrames` frames, preventing an abrupt transition back to pure matrix metering.

**Recommended face weight multipliers by scene:**

| Scene | Recommended Multiplier |
|-------|------------------------|
| Dedicated portrait mode | 3–4× |
| General photography | 2–2.5× |
| Video recording | 1.5–2× (avoids frequent oscillation) |
| No face (landscape/architecture) | 1.0× (pure matrix metering) |

> **Engineering recommendation:** Use matrix metering + histogram assist (`α = 0.7`) as the default path. Do not enable the scene classifier prematurely — a misclassification is worse than no classification at all, and matrix metering is already adequate for most indoor, front-lit, and outdoor scenes. Disable face weights when face detection confidence is below 0.8; fall back to matrix metering rather than letting a false-positive "face" skew the entire frame's exposure. In video mode, cap face weight at 2×; exceeding this value in multi-person scenes almost invariably causes exposure oscillation. Only two situations truly warrant histogram-dominant mode (`α ≤ 0.5`): low-light scenes (full-frame mean < 30/255) and bimodal backlit scenes — in both cases the weighted mean is itself incorrect input and should not be trusted.

### 3.4 Histogram vs. Matrix Metering Fusion Priority

Fusion strategy when matrix metering and histogram metering disagree:

$$EV_{\text{final}} = \alpha \cdot EV_{\text{matrix}} + (1-\alpha) \cdot EV_{\text{histogram}}$$

Typical value: $\alpha = 0.7$ (matrix takes priority); in low-light scenes $\alpha = 0.5$ (histogram is more reliable).

---

### 3.5 Metering Luma Target and Gamma Curve Coupling

**Engineering coupling gap:** The first half of this chapter defines `AEC_TargetLuma` (typical 110–130/255), but does not explain that this target value must be updated in tandem when the Gamma curve changes — otherwise the system will be systematically over- or under-exposed.

**Coupling principle:**

AE statistics sample luminance $Y$ in the **Gamma-encoded YUV domain** (or the RAW domain, depending on platform configuration). If the sensor linear-domain true luminance is $L_{\text{linear}}$, then after Gamma encoding:

$$Y = \text{clip}\!\left(255 \cdot L_{\text{linear}}^{1/\gamma},\ 0,\ 255\right)$$

The linear luminance corresponding to AE target value $Y_{\text{target}}$:

$$L_{\text{target,linear}} = \left(\frac{Y_{\text{target}}}{255}\right)^{\gamma}$$

**When Gamma changes from 2.2 to 2.4 (darker output):** with the same $Y_{\text{target}} = 120$, the corresponding linear luminance drops from 0.196 to 0.174 — a reduction of ≈ 12% in actual captured light, causing the output image to be **systematically underexposed by ≈ 0.17 EV**. The AE system reports "target reached," but the viewer sees a noticeably darker image. This is the classic decoupling fault between metering and tone.

**Coupling formula:**

If Gamma changes from $\gamma_{\text{ref}}$ (typically 2.2) to $\gamma_{\text{new}}$, the corrected target is:

$$Y_{\text{target,new}} = 255 \cdot \left(\frac{Y_{\text{target,ref}}}{255}\right)^{\gamma_{\text{ref}} / \gamma_{\text{new}}}$$

**Example:** $Y_{\text{target,ref}} = 120$, $\gamma_{\text{ref}} = 2.2$, $\gamma_{\text{new}} = 2.4$:

$$Y_{\text{target,new}} = 255 \cdot \left(\frac{120}{255}\right)^{2.2/2.4} = 255 \cdot 0.471^{0.917} \approx 124$$

When Gamma becomes darker, the target value should be raised from 120 to ≈ 124 to maintain constant perceived brightness.

**Practical handling:**

Most platforms bind `AEC_TargetLuma` and Gamma parameters under the **same profile (scene mode)**, so both are updated simultaneously on a mode switch rather than independently. In Qualcomm Chromatix, `luma_target` and `gamma_table` both belong to the same `[ISO_lux_trigger]` segment under `chromatix_params` — if Gamma is modified, always check `luma_target` in the same trigger segment. MediaTek is the same: `GammaTable` and `AETargetLuma` reside in the same NDD profile. **Modifying Gamma in isolation without checking `luma_target` is one of the most common tuning errors.**

---

### 3.6 Anti-Banding Constraints on Exposure Time and AE Search Space

**Engineering coupling gap:** The anti-banding (anti-flicker) principle is introduced in §1.6, but the chapter does not explain the specific constraints it places on the AE controller's search space, nor how those constraints affect AE convergence behavior.

**Constraint mechanism:**

Under a 50 Hz mains supply, fluorescent and LED illuminants flicker at 100 Hz. Exposure time must be an integer multiple of 10 ms to integrate complete light-intensity cycles:

$$t_{\text{exposure}} \in \{10\text{ ms},\ 20\text{ ms},\ 30\text{ ms},\ \ldots\}$$

This **discretizes** the AE controller's continuous exposure-time search space into an arithmetic series, with the following engineering implications:

1. **Reduced AE resolution:** Under normal conditions the AE can adjust exposure time in increments of 0.1–0.5 ms (especially useful at low light for fine convergence). With anti-banding enabled, the minimum step becomes 10 ms — near an optimal exposure of about 1/200 s (5 ms), no fine control is possible and AE must rely on ISO gain to compensate.

2. **Increased oscillation risk:** When the scene's optimal exposure time falls between two quantized values (e.g., between 10 ms and 20 ms), AE will oscillate between the two and use analog gain to compensate, generating a sawtooth exposure-gain oscillation (the "breathing effect").

3. **Delayed convergence in low light:** In low light the optimal exposure time may be 33 ms. Anti-banding constrains the choices to 30 ms or 40 ms: 30 ms underexposes, and 40 ms requires waiting for the next allowable window. The number of convergence steps increases from a normal 5–8 frames to 10–15 frames.

**Qualcomm platform parameter configuration:**

```xml
<!-- chromatix_aec_ext.xml -->
<AEC_AntiFlickerMode>Auto</AEC_AntiFlickerMode>          <!-- Auto/50Hz/60Hz/Disabled -->
<AEC_AntiFlickerExpUnit>10000</AEC_AntiFlickerExpUnit>    <!-- Exposure quantization unit, μs (50 Hz = 10000 μs) -->
<AEC_UseGainForFineAdj>1</AEC_UseGainForFineAdj>         <!-- 1 = use gain for fine-grained compensation with anti-banding -->
<AEC_GainAdjMaxRatio>1.5</AEC_GainAdjMaxRatio>           <!-- Maximum gain compensation ratio (limits noise increase) -->
```

**MediaTek platform:**

```
[AE]
AEAntiFlicker           = ENUM_AUTO     # Auto/50Hz/60Hz/OFF
AEAntiFlickerUnit       = 10000         # μs; 10 ms for 50 Hz
AEFineTuneByGain        = 1             # fine adjustment via gain rather than exposure time
AEMaxGainForFineTune    = 1.5           # gain compensation upper bound
```

**Tuning note:** The gain compensation ceiling for `AEFineTuneByGain` (MediaTek) / `AEC_UseGainForFineAdj` (Qualcomm) should not be set too high — a 1.5× gain boost corresponds to ≈ 3.5 dB additional noise. In extremely dark scenes, disabling anti-banding (`Mode = Disabled`) and allowing continuous exposure time search is recommended; handle banding in post-processing (banding detection + correction) rather than constraining the front-end.

---

### 3.7 Three-Platform Metering Key Parameter Reference

| Function | Qualcomm CamX / Chromatix | MediaTek Imagiq / NDD | HiSilicon Yueying |
|----------|--------------------------|----------------------|-------------------|
| Metering enable | `AEC_Enable` (CamX AEC node) | `AEEnabled` (NDD bool) | `AE_Enable` |
| Metering mode | `AEC_MeteringMode` (enum: Center/Spot/Matrix/Face) | `AEMeteringMode` (NDD enum) | `AE_MeterMode` |
| Zone weight table | `AEC_ZoneWeightMap[15×15]` (Chromatix XML, float weights) | `AEZoneWeight[N][N]` (NDD int matrix; Dimensity supports 9×9) | `AE_WeightMap[]` |
| Face metering weight | `AEC_FaceWeightScale` (float, typical 2.0–4.0) | `AEFaceWeight` (NDD float) | `AE_FacePriority` |
| Target brightness | `AEC_TargetLuma` (8-bit, typical 110–130; adaptive via lux-index LUT) | `AETargetLuma` (NDD int, typical 118) | `AE_LumaTarget` |
| Statistics domain | `AEC_StatsType` (Y channel from YUV / weighted R+G+B) | `AEStatsChannel` (NDD: Y/RGB weighted) | `AE_StatsType` |
| Highlight protection | `AEC_HighlightBias` (downweight coefficient for highlight zones) | `AEHighlightSuppression` (NDD float) | `AE_HLProtect` |
| Histogram statistics | `AEC_HistogramBins` (256 bins; per-zone histogram supported) | `AEHistBins` (256, configurable ROI) | `AE_HistConfig` |
| Anti-flicker | `AEC_AntiFlickerMode` (Auto/50Hz/60Hz; detects mains frequency) | `AEAntiFlicker` (NDD enum) | `AE_FlickerMode` |

**Chromatix XML example (Qualcomm, zone weight table, center-weighted metering):**

```xml
<!-- chromatix_aec_ext.xml -->
<metering_weight_map>
  <!-- 15×15 weight table; center region higher than edges -->
  <!-- Row 1 (top edge, low weight) -->
  <row>1 1 1 1 1 1 1 1 1 1 1 1 1 1 1</row>
  <!-- Row 5 (near center, higher weight) -->
  <row>1 2 3 4 5 6 7 6 5 4 3 2 1 1 1</row>
  <!-- Row 8 (center, highest weight) -->
  <row>1 2 4 6 8 10 12 10 8 6 4 2 1 1 1</row>
  ...
</metering_weight_map>
<face_weight_scale>3.0</face_weight_scale>
<target_luma>120</target_luma>
```

> **Tuning notes:**
> - Qualcomm `AEC_ZoneWeightMap` has a fixed size of 15×15 (shared with AF statistics blocks). MediaTek Dimensity supports a variable-ROI 9×9 map. When porting weight tables between platforms, the weights must be resampled to match the different grid resolutions.
> - Face weight multipliers above 4× will cause exposure to oscillate among different faces in multi-person scenes. Limit the face weight to 2–2.5× in multi-face contexts; it may be raised to 3–4× in single-subject portrait mode.
> - `AEC_AntiFlickerMode = Auto` relies on flicker detection; it can misfire outdoors or under LED backlighting. Fix the setting manually for specific known environments.

---

## §4 Artifacts

### 4.1 Backlight Underexposure

**Description:** A bright background (e.g., a window or outdoor sky) dominates the overall metering result, causing the foreground subject to be severely underexposed.

**Detection:** Bimodal histogram with foreground mean < 60/255, background mean > 200/255, and $\Delta EV > 3$.

**Mitigation:**
- Activate face-priority metering to redirect the exposure target to the foreground face.
- If the contrast exceeds the sensor's dynamic range, recommend that the user switch to HDR mode.
- Guide the user to use a fill light or reflector.

### 4.2 Specular Highlight Clipping

**Description:** In night scenes, point light sources such as lamp bulbs or streetlights occupy only a small fraction of pixels but are extremely bright. Because their area is too small to influence metering statistics, the highlight protection mechanism is not triggered, and these regions blow out.

**Mitigation:** Monitor cumulative saturated pixel area for bright spots — when more than 0.5% of pixels are fully saturated, trigger a −0.3 EV correction.

### 4.3 Metering Region Misidentification

**Description:** Face detection misses a face or falsely detects a bright object as a face. The face weight is then applied to the wrong region, causing the final exposure to deviate from the intended result.

**Mitigation:** The face detection confidence threshold used by the AE metering stage should be higher than that used on the display side. A detection score > 0.8 is recommended before enabling face weights for metering (the display side may use 0.5).

### 4.4 AE Convergence Oscillation

**Description:** An overly large PI controller integration term, or a scene whose brightness oscillates near a threshold (e.g., walking while hand-holding), causes exposure to jump back and forth between two settings.

**Mitigation:** Introduce a dead band: when $|\Delta EV| < 0.2$, do not update parameters. In video mode, limit the per-frame EV change to $\leq 0.1$ EV.

---

## §5 Evaluation

### 5.1 AE Accuracy Metrics

**Absolute EV Error:**

$$\varepsilon_{EV} = |EV_{\text{predicted}} - EV_{\text{reference}}|$$

Target: $\varepsilon_{EV} < 0.5$ EV at the 90th percentile over the reference exposure set.

**Face Brightness Error:**

$$\varepsilon_{L^*} = |L^*_{\text{face\_output}} - L^*_{\text{target}}|$$

Target: $\varepsilon_{L^*} < 5$ (deviation from the $L^*$ target of 62).

### 5.2 Highlight and Shadow Protection Rates

**Highlight protection rate:** In the "highlight test set" (scenes containing lights or sky), the percentage of output images where the highlight clipping ratio $r_{\text{high}} < 2\%$. Target: > 90%.

**Shadow protection rate:** In the "shadow test set," the percentage of samples where the mean luminance of dark regions is > 20/255. Target: > 85%.

### 5.3 Convergence Speed

| Scene Change | Target Convergence Frames | Measurement Method |
|--------------|--------------------------|-------------------|
| Entering a dark room (3 EV drop) | ≤ 10 frames | Record video; count frames from the change frame to the stable frame |
| Leaving a dark room (3 EV rise) | ≤ 5 frames | Same as above |
| Minor change (< 0.5 EV) | ≤ 3 frames | — |

### 5.4 Subjective Evaluation Protocol

```
Test image set: 50+ scenes (portrait / landscape / backlit / night / high dynamic range)
Evaluation dimensions:
  1. Is the overall brightness appropriate? (1–5 score)
  2. Is the face clearly visible? (1–5 score)
  3. Are there obvious overexposed or underexposed areas? (Yes / No)
Evaluators: ≥ 30 people; report mean and variance
Targets: overall brightness mean score ≥ 3.8/5; no obvious overexposure in > 90% of cases
```

---

## §6 Code

See the companion notebook *See §6 Code section for runnable examples.*, which includes:

- A complete Python implementation of multi-zone matrix metering (per-zone luminance statistics + multi-factor weight fusion)
- Histogram analysis utilities (highlight/shadow clipping rate, bimodal peak detection)
- Perceptual luminance $L^*$ computation and face brightness deviation analysis
- A simulation of AE PI controller convergence
- Visualizations: weight heat maps, EV convergence curves, histogram target analysis

---

---

## §7 Glossary

**Weber–Fechner Law**
A psychophysical law describing the relationship between perceptual differences and physical stimulus intensity: $\Delta E = k \cdot \Delta I / I$, where $I$ is background luminance, $\Delta I$ is the just-noticeable difference (JND), and $k \approx 0.02$ is Weber's constant (an empirical approximation for photopic vision at moderate luminance levels). Implication: the perceptual system is sensitive to relative rather than absolute changes; small luminance changes in dark regions are easily perceived. The value of $k$ varies with luminance level, adaptation state, and other conditions; it is not a universal physical constant.

**Stevens' Power Law**
A psychophysical law relating perceived magnitude to the absolute intensity of a physical stimulus: $\Psi = k_s \cdot I^{\beta}$, where $\beta \approx 0.33$ is the empirical exponent for luminance perception and $k_s$ is the Stevens power-law coefficient (distinct from Weber's $k \approx 0.02$). Stevens' law qualitatively explains the compressive nonlinearity with which the human eye responds to wide dynamic range. Note: the sRGB encoding gamma (≈ 1/2.2 ≈ 0.45) was not derived directly from the Stevens exponent 0.33. The primary purpose of sRGB encoding gamma is to compensate for the nonlinear EOTF of CRT displays (≈ 2.2); the two values are numerically different (0.33 ≠ 0.45) and must not be conflated.

**APEX Exposure System (Additive system of Photographic EXposure)**
A framework that maps aperture ($A_v = \log_2 N^2$), shutter ($T_v = \log_2(1/t)$), ISO sensitivity ($S_v = \log_2(\text{ISO}/3.125)$), and scene brightness ($B_v$) to a common base-2 logarithmic domain, so that the exposure equation reduces to $E_v = B_v + S_v$ (linear addition). ISO 100 corresponds to $S_v = 5$ (because $100/3.125 = 32 = 2^5$). APEX enables embedded AE implementations to perform arithmetic in log domain, avoiding floating-point multiplications.

**CIE L* (Perceptually Uniform Lightness Component)**
The lightness component of the CIELAB color space, designed to approximate the nonlinear perceptual response of the human eye. For high-luminance values ($Y/Y_n > (6/29)^3 \approx 0.008856$), it uses cube-root compression: $L^* = 116 \cdot (Y/Y_n)^{1/3} - 16$; for low luminance it uses a linear approximation: $L^* = 903.3 \cdot (Y/Y_n)$. $L^*$ maps $[0, 100]$ to a perceptually uniform space. AE systems commonly use $L^* = 62$ as the face metering target (corresponding to the midtone-bright region for most common skin tones).

**Matrix/Evaluative Metering**
A metering mode that divides the frame into $M \times N$ zones, computes per-zone luminance statistics, and performs a weighted average fusing position weights (Gaussian center prior), face weights (detected regions boosted 2–4×), focus-point weights (1.5–2×), and highlight suppression weights (overexposed zones downweighted to 0.2) to estimate representative scene luminance and target EV. Compared with average metering (global mean) and spot metering (precise single-point), matrix metering incorporates scene-content analysis and is the dominant AE metering strategy in modern smartphone ISPs.

**18% Gray (Zone V)**
The photographic metering reference standard: the midtone corresponds to 18% reflectance (Zone V in Ansel Adams' Zone System). The core AE objective is to map the scene's "representative brightness" to this midtone, targeting sensor output at approximately 40–50% of saturation. An 18% gray card is used to calibrate the AE target brightness $Y_{\text{target}}$, which typically corresponds to a normalized luminance of 0.18 or an 8-bit encoded value of approximately 117/255.

**Highlight Clipping Ratio**
$r_{\text{high}} = 1 - F[240]$, where $F$ is the cumulative distribution function of the luminance histogram and $F[240]$ is the cumulative fraction of pixels with values ≤ 240. When $r_{\text{high}} > 0.02$ (more than 2% of pixels near overexposure), the AE system triggers a reduce-exposure correction. A threshold that is too low causes normal highlights to be darkened; a threshold that is too high permits severe clipping. The optimal value should be tuned separately for different target scenes (night, indoor, etc.).

**Backlit Scene**
A scene in which background luminance far exceeds foreground luminance (e.g., an indoor portrait in front of a window). Characteristics: bimodal histogram, foreground mean < 60/255, background mean > 200/255, $\Delta EV > 3$. Conventional average metering is dominated by the background, causing the foreground face to be severely underexposed. Modern ISPs address this through face-priority metering, foreground/background separated exposure, or triggering HDR multi-frame merging.

**AE PI Controller**
A proportional-integral controller whose input is the exposure error $\Delta EV$. The proportional term provides rapid response; the integral term eliminates steady-state error. A large integration gain causes oscillation (exposure jumping between two settings). Oscillation is suppressed by introducing a dead band (no parameter update when $|\Delta EV| < 0.2$); in video mode the per-frame EV change is limited to ≤ 0.1 EV to avoid visible exposure breathing.

---

> **Engineer's Notes: Metering is asking "who speaks for this frame?"**
>
> **The essence of a metering mode is a weighted vote across image regions.** The ISP statistics module divides the frame into $M \times N$ blocks (typically 5×5 or 16×16), computes a histogram for each block, and computes a weighted average "current brightness" for the AE controller. Different metering modes differ only in the weight matrix: spot metering sets 1–2 blocks to weight 1 and the rest to 0; center-weighted gives higher weight to the center; matrix metering distributes weight uniformly across the full frame; face metering sets the face ROI blocks to 5–10× weight. This means **switching metering mode is switching weight tables, not switching algorithms**. The most common bug in production is writing the weight table in the wrong format (e.g., row-major vs. column-major for MTK weight config), causing the entire frame's exposure to be biased in one direction. Engineers often spend time suspecting the AE controller before discovering the weight table is transposed.
>
> **Backlit scenes are the most typical failure case for average metering — but the fix is not switching metering modes.** When shooting an indoor subject in front of a bright window, average metering is dominated by the background sky and underexposes the face. The correct engineering solution is not to manually switch to spot metering, but to have the AE system automatically detect the high-contrast backlit condition (bimodal histogram), and automatically shift the weight toward the face region — this is exactly what scene-aware AE does in modern smartphones: face detection outputs an ROI → AE module dynamically adjusts weights → face exposure is correct. Without face guidance, average metering + backlit scene = "crisp background, black face."
>
> **The root cause of AE oscillation (breathing effect) is too small a dead band, not too large a gain step.** Many engineers repeatedly adjust `AE_Step_Size` or gain allocation strategy when debugging AE convergence issues, and get worse results each time. The true problem is usually that `AE_Tolerance` (dead band) is set too small: AE detects that luminance exceeds target by 0.5%, triggers a micro-adjustment, but the control parameter is discrete and the actual adjustment rounds to the nearest step — overshooting the target; the next frame reverses, and the oscillation continues. The fix is to widen the tolerance to ±3–5% (AE does not move when brightness is within ±3% of target, and only begins adjusting outside this range). Horizon (Horizon Robotics) J3/J5 platform AE tuning documentation explicitly identifies this problem; the default `Tolerance` value is often set too small.
>
> *References: Horizon Robotics Developer Community, "Talking about brightness control in imaging," lanzhe, 2024-04-07; iResearch666, "3A algorithms in smartphone photography: AE/AWB optimization," CSDN, 2025; Qualcomm CIQT AE Tuning Guide (public edition), Qualcomm, 2023.*

---

## §8 Illustrations

![ae auto exposure control](img/fig_ae_auto_exposure_control_ch.png)
*Figure 1. Overall auto-exposure control system framework, showing the complete control loop from metering statistics to exposure parameter output. (Source: author, ISP Handbook, 2024)*

![ae exposure strategy](img/fig_ae_exposure_strategy_ch.png)
*Figure 2. AE exposure triangle strategy diagram illustrating coordinated ISO/shutter/aperture adjustment. (Source: author, ISP Handbook, 2024)*

![ae metering algorithm](img/fig_ae_metering_algorithm_ch.png)
*Figure 3. Internal flow of matrix metering algorithm: zone partitioning, multi-factor weight fusion, and weighted mean computation. (Source: author, ISP Handbook, 2024)*

![ae metering modes](img/fig_ae_metering_modes_ch.png)
*Figure 4. Comparison of major metering modes: coverage areas for average, center-weighted, matrix, and spot metering. (Source: author, ISP Handbook, 2024)*

![metering zone weights](img/fig_metering_zone_weights_ch.png)
*Figure 5. Example zone weight heat map for matrix metering: highest weight at center, decaying toward edges via a Gaussian. (Source: author, ISP Handbook, 2024)*

![ev calculation](img/fig_ev_calculation_ch.png)
*Figure 6. APEX exposure system EV calculation diagram: logarithmic-domain mapping from scene luminance to exposure triangle parameters. (Source: author, ISP Handbook, 2024)*

![face weighted metering](img/fig_face_weighted_metering_ch.png)
*Figure 7. Face-priority metering: effect on exposure target after boosting the face region weight. (Source: author, ISP Handbook, 2024)*

![histogram metering](img/fig_histogram_metering_ch.png)
*Figure 8. Histogram-based AE target analysis: CDF analysis and highlight/shadow clipping ratio detection. (Source: author, ISP Handbook, 2024)*

---

## References

- ISO 12232:2019 — Photography — Digital still cameras — Determination of exposure index, ISO speed ratings, standard output sensitivity, and recommended exposure index.
- Adams, A. (1948). *The Negative* (Zone System). Little, Brown.
- Bayer, B. E. (1976). **Color imaging array.** US Patent 3,971,065.
- CIE 15:2004 — Colorimetry (3rd ed.). CIE, Vienna.
- Stevens, S. S. (1957). **On the psychophysical law.** *Psychological Review*, 64(3), 153–181.
- Nikon Corporation. (2005). **3D Color Matrix Metering II** — Product technical description (public product documentation).
- Canon Inc. (2018). **Intelligent Tracking and Recognition (iTR AF)** — EOS product technical documentation.
- Reinhard, E., et al. (2010). *High Dynamic Range Imaging* (2nd ed.). Morgan Kaufmann. Chapter 4: Tone Mapping.
- He, K., Sun, J., & Tang, X. (2013). **Guided image filtering.** *IEEE TPAMI*, 35(6), 1397–1409.
- Google AI Blog (2020). **Night Sight: Seeing in the Dark on Pixel Phones.** https://ai.googleblog.com (public blog post)
