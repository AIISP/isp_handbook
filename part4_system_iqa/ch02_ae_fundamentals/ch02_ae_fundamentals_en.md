# Part 4, Chapter 02: Auto Exposure Fundamentals (自动曝光算法)

> **Pipeline position:** AE is the first control loop in the 3A system to converge; it directly affects SNR and dynamic range utilization.
> **Prerequisites:** Chapter 03 (Sensor Physics), Chapter 07 (HDR)
> **Reader path:** 3A algorithm engineers, ISP tuning engineers

---

## Chapter Overview

Auto Exposure (自动曝光, AE) is one of the most fundamental and critical control loops in a camera system. The core objective of AE is to select the optimal combination of exposure parameters — shutter time, aperture, and ISO — under a given lighting condition, so that the sensor output image brightness approaches a preset target while maximizing the signal-to-noise ratio (SNR) and preserving adequate dynamic range.

Compared with Auto Focus (AF) and Auto White Balance (AWB), AE is typically the first of the 3A loops to converge — generally reaching steady state within 3–5 frames. This is because exposure parameters have an immediate and predictable effect on output brightness, whereas AF requires physical movement of a focus motor and AWB requires multi-frame statistical analysis.

This chapter provides an in-depth treatment of the complete AE algorithm stack: from the physical foundations of the exposure equation, to multi-zone metering strategies, to the implementation details of a PI controller, and to extension schemes for special scenarios such as HDR and anti-banding.

---

## §1 Theory

### 1.1 The Exposure Equation and the EV System

#### Basic Exposure Equation

The photographic exposure $H$ (unit: lux·s) is defined as:

$$H = E \cdot t$$

where $E$ is the image-plane illuminance (lux) and $t$ is the shutter time (seconds). The relationship between image-plane illuminance, scene luminance $L$, f-number $N$, and lens transmittance $T$ is:

$$E = \frac{\pi \cdot T \cdot L}{4 N^2}$$

Therefore the total exposure:

$$H = \frac{\pi \cdot T \cdot L \cdot t}{4 N^2}$$

**Standardized Reflective Metering Equation (ISO 2720):**

ISO 2720 defines the following standard exposure equation for reflected-light meters:

$$\frac{N^2}{t} = \frac{L \cdot S}{K}$$

where:
- $N$: f-number
- $t$: shutter time (seconds)
- $L$: scene luminance (cd/m²)
- $S$: ISO sensitivity
- $K$: metering calibration constant, **standard value $K = 12.5$** (adopted by ISO 2720 and major camera manufacturers for reflective metering)

This equation links scene luminance, exposure parameters, and ISO sensitivity — it is the basis for absolute luminance estimation in AE systems.

#### EV (Exposure Value, 曝光值) System

To map exposure parameters into the logarithmic domain, photography introduced the concept of Exposure Value (曝光值, EV):

$$\text{EV} = \log_2\!\left(\frac{N^2}{t}\right)$$

where:
- $N$: f-number (光圈数), e.g., f/1.8, f/2.8
- $t$: shutter time (seconds), e.g., 1/100s, 1/1000s

Every increase of 1 EV halves the amount of light admitted; every decrease of 1 EV doubles it. The EV system is standardized in **[1]**. Common exposure combination examples:

| EV | Aperture $N$ | Shutter $t$ | Typical scene |
|----|-------------|-------------|---------------|
| 15 | f/8         | 1/500s      | Bright outdoor sunlight |
| 12 | f/4         | 1/250s      | Overcast outdoors |
| 9  | f/2.8       | 1/60s       | Indoor daylight |
| 6  | f/2.0       | 1/15s       | Dusk / golden hour |
| 3  | f/1.8       | 1/4s        | Night street scene |

#### Equivalent Exposure (等效曝光)

The same EV value can be achieved by different $(N, t)$ combinations — these are called equivalent exposures. For example:

$$\frac{f/1.4}{1/1000s} \equiv \frac{f/2.0}{1/500s} \equiv \frac{f/2.8}{1/250s}$$

These three parameter sets share the same EV (equal light admission) but have markedly different effects on depth of field and motion blur.

#### APEX System (Additive System of Photographic Exposure)

APEX (ISO 12232 Additive System of Photographic Exposure) maps all exposure parameters into the base-2 logarithmic domain so that they can be added and subtracted:

$$\text{EV} = A_v + T_v = B_v + S_v$$

| Symbol | Name | Definition | Example |
|--------|------|-----------|---------|
| $A_v$ (Aperture Value) | Aperture value | $A_v = \log_2(N^2) = 2\log_2 N$ | f/2.8 → $A_v = 3$ |
| $T_v$ (Time Value) | Time value | $T_v = -\log_2(t)$ | 1/100s → $T_v \approx 6.64$ |
| $S_v$ (Sensitivity Value) | Sensitivity value | $S_v = \log_2(\text{ISO}/3.125)$ | ISO 100 → $S_v = 5$ |
| $B_v$ (Brightness Value) | Brightness value | $B_v = \log_2(B \cdot S_0/\pi)$ | Logarithmic encoding of scene luminance |

**Engineering significance of APEX:** ISP AE algorithms perform PI control in the EV domain (error = EV_target − EV_current), which is essentially the APEX framework. The exposure step sizes in camera firmware (1/3 EV, 1/6 EV) come directly from the minimum increment units of $\Delta A_v$, $\Delta T_v$, $\Delta S_v$.

**Sunny 16 Rule (empirical exposure guideline):**

Under direct bright outdoor sunlight at f/16, the correct shutter time is approximately the reciprocal of the ISO value:

$$t \approx \frac{1}{\text{ISO}}, \quad N = f/16$$

For example, at ISO 100, shutter ≈ 1/125s (nearest standard stop), corresponding to $\text{EV}_{100} \approx 15$.

**Common scene EV reference ranges (ISO 100 baseline, EV₁₀₀):**

| Scene | EV Range | Notes |
|-------|---------|-------|
| Direct bright sunlight outdoors | EV 14–16 | Sandy beach / snow can reach EV 16 |
| Overcast / diffuse outdoor light | EV 10–13 | Heavy cloud cover |
| Indoor artificial lighting | EV 5–9 | Fluorescent office ≈ EV 7–9 |
| Dusk / early evening outdoors | EV 4–6 | Just after sunset ≈ EV 4 |
| Night / street lighting | EV 0–4 | Deep night without moon can reach EV 0 or below |

#### The Role of ISO (Gain)

ISO is the standardized measure of sensor sensitivity. The definition standard is **ISO 12232:2019** (Digital still cameras — Determination of exposure index, ISO speed ratings, standard output sensitivity, and recommended exposure index) **[1a]**. In digital photography, ISO is approximately proportional to analog gain (the exact coefficient depends on the sensor OETF and output characteristics):

$$\text{ISO} \approx 100 \cdot g \quad \text{(within the ISO 12232:2019 recommended range)}$$

> **Note (ISO 12232:2019):** This standard defines two frameworks — SOS (Standard Output Sensitivity) and REI (Recommended Exposure Index). The actual ISO value is determined by sensor calibration and is not a strict 100× gain relationship. ISO 200 does not equal exactly 2× gain; the actual conversion also depends on the sensor OETF and output characteristics. The formula above is an engineering approximation and must not be used for precise gain calibration.

**Camera gain (dB) ↔ ISO (linear) conversion:**

$$G_{\text{dB}} = 20 \cdot \log_{10}\!\left(\frac{\text{ISO}}{100}\right)$$

Examples: ISO 100 → 0 dB; ISO 200 → 6 dB; ISO 400 → 12 dB; ISO 3200 → 30 dB. Inverse: $\text{ISO} = 100 \times 10^{G_{\text{dB}}/20}$. ISP registers typically express gain in dB or as a linear multiplier; these can be converted to ISO values using the formula above.

Incorporating ISO, the EV system extends to:

$$\text{EV}_{100} = \log_2\!\left(\frac{N^2}{t}\right) - \log_2\!\left(\frac{\text{ISO}}{100}\right)$$

**The cost of increasing ISO:** Every doubling of ISO reduces the SNR by approximately 3 dB (in the shot-noise-dominated regime) **[2]** and simultaneously amplifies Fixed Pattern Noise (FPN, 固定模式噪声) and read-out noise.

#### Optimal Exposure Parameter Selection Strategy

On mobile devices (fixed aperture), the exposure parameter control priority order is:

```
优先级 1：延长快门时间 t（不引入额外噪声，但受运动模糊限制）
         t_max 通常由防抖能力和场景运动速度决定
         典型移动端限制：t ≤ 1/（焦距等效焦距）秒（防手抖）

优先级 2：提高模拟增益 gain_analog（噪声增加较少，因为在 A/D 转换前放大信号）
         典型范围：1× ~ 16×（12 dB）

优先级 3：使用数字增益 gain_digital（在 A/D 后放大，噪声最大，应尽量避免）
         通常作为最后手段，或用于精细调节
```

### 1.2 Metering Systems

Metering (测光) is the perception layer of the AE system, responsible for estimating the current exposure state of a scene from image statistics.

#### Reflective vs. Incident Metering

| Type | Principle | Advantages | Disadvantages |
|------|-----------|-----------|---------------|
| Reflective metering (反射式测光) | Measures light reflected from the subject | Remote measurement; no contact with subject | Affected by subject reflectance (black-cat / white-snow problem) |
| Incident metering (入射式测光) | Measures light falling on the subject | Unaffected by reflectance; absolutely accurate | Requires a light meter placed at the subject's position |

Mobile cameras all use reflective metering and compensate for reflectance differences through scene analysis and weighting strategies.

#### Matrix Metering (矩阵测光, Zone Metering)

The frame is divided into $M \times N$ zones (commonly 8×6 or 16×9). The average luminance $\bar{Y}_i$ is computed for each zone, and a weighted sum yields the global metering value:

$$Y_{\text{metered}} = \frac{\sum_{i=1}^{M \times N} w_i \cdot \bar{Y}_i}{\sum_{i=1}^{M \times N} w_i}$$

The weights $w_i$ are typically determined by zone position, zone variance, and scene content (sky detection, face detection).

**Advantages:** High robustness; suitable for the majority of scenes.
**Disadvantages:** May fail in complex scenes (strong backlighting).

#### Spot Metering (点测光)

Uses only the luminance of the central 1–5% of the frame as the metering basis:

$$Y_{\text{metered}} = \bar{Y}_{\text{center\_spot}}$$

**Applicable scenes:** Stage performances (extreme luminance difference between subject and background); precise control of a specific zone's exposure.

#### Center-Weighted Metering (中央重点测光)

Uses Gaussian weights, with maximum weight at the center and weights approaching zero at the edges:

$$w(x, y) = \exp\!\left(-\frac{(x - x_c)^2 + (y - y_c)^2}{2\sigma^2}\right)$$

where $(x_c, y_c)$ is the frame center and $\sigma$ controls the weight roll-off rate (typical value: 1/4 of the frame width).

#### Face-Priority Metering (人脸优先测光)

After integrating face detection (人脸检测), face regions are assigned the highest weight:

$$w_{\text{face}} = \alpha \cdot \text{confidence}_{\text{face}} \cdot \text{area}_{\text{normalized}}$$

where $\alpha$ is the face weight coefficient (typical value 3–10), `confidence_face` is the detection confidence, and `area_normalized` is the face area normalized relative to the full frame.

**Multi-face handling:** All detected faces are weighted-averaged, with weights proportional to face area and center position.

#### Summary of Metering Mode Applicability

| Metering mode | Recommended scenes | Not suitable for |
|--------------|-------------------|-----------------|
| Matrix metering | Everyday photography, landscapes | Extreme backlighting |
| Spot metering | Stages, high-contrast scenes | Everyday use (complex to operate) |
| Center-weighted | Portraits (subject centered) | Subject off-center |
| Face-priority | Portraits, selfies, video calls | Scenes without faces (requires fallback) |

#### Hardware Luminance Statistics: ISP BPS Statistics Engine

The input to AE software is not raw pixel data but per-frame statistical data automatically accumulated by the ISP **hardware statistics engine** during frame readout. This hardware foundation enables real-time AE operation.

**Qualcomm Spectra BPS Statistics Module (BG Stats / AEC BG):**

BPS (Bayer Processing Segment) performs region-based statistics on RAW Bayer data before demosaic:

```
Sensor RAW frame (frame-level pipeline)
  ↓
BPS Statistics Engine (AEC BG — Background Exposure Statistics)
  Divides the frame into up to 32×32 zones (configurable, Snapdragon 8 Gen series)
  Each zone outputs:
    sum_R, sum_G, sum_B    ← per-channel pixel sums
    count                  ← unsaturated pixel count (saturated pixels excluded automatically)
    saturated_count        ← number of saturated pixels
  ↓
DMA writes statistics data to system memory
  ↓
V-sync interrupt triggers AE software read (typically in SOF callback)
```

**The 3A controller computes zone luminance from statistics:**

$$\bar{Y}_z = \frac{0.299 \cdot \text{sum\_R}_z + 0.587 \cdot \text{sum\_G}_z + 0.114 \cdot \text{sum\_B}_z}{\text{count}_z}$$

Statistics formats across platforms:

| Platform | Statistics format | Grid size | Driver interface |
|----------|------------------|-----------|-----------------|
| Qualcomm Spectra (CamX) | AEC BG Stats | Up to 32×32, configurable | `BGStatsConfig` in `camxtitan17xdefs.h` |
| MediaTek Imagiq (IPESYS) | AE Weight Map | Up to 64×48 | MTK ISP HAL `AEStatConfig` |
| Samsung Exynos (ExynosCamera) | AE Grid Stats | Up to 32×24 | `ExynosCameraParameters.h` |

**Timing guarantee for face AE weights:**

Face detection (typically running on NPU/CPU, latency 15–30 ms) and AE control (per-frame ~1 ms) are not perfectly synchronized. Engineering implementations use the following strategies to ensure timing consistency:

1. **Latency compensation:** The face detector tags each face bounding box with its corresponding frame index. The AE controller applies the matching face weights to the **same frame's statistics**, rather than using the latest face box (which may be from 2–3 frames earlier).
2. **Frame timestamp alignment:** ISP hardware statistics carry SOF timestamps; the face detector attaches corresponding SOF timestamps to its results; the AE thread matches statistics and face boxes by timestamp.
3. **Smooth exit when no face is detected:** When no face is detected for N consecutive frames (typically 5–10), the face weight coefficient $\alpha$ is linearly decayed to zero (rather than immediately cleared) to avoid exposure jumps from abrupt metering mode transitions.

### 1.3 AE Convergence Algorithm

#### Target Luminance: The Origin of 18% Gray

The AE target luminance is based on the photographic standard of "18% reflectance neutral gray." The logarithmic average of many natural scenes with varying reflectances is approximately 18% (i.e., a log-median of about 0.72). Targeting 18% gray therefore optimally utilizes dynamic range in a statistical sense.

In practice, the target luminance $Y_{\text{target}}$ is typically set to 118 after 8-bit quantization (approximately 255 × 0.46, where 0.46 corresponds to 18% under gamma = 2.2).

#### Error Definition (Logarithmic Domain)

The AE error is defined in the logarithmic (EV) domain to ensure linear control characteristics:

$$e[k] = \text{EV}_{\text{target}} - \text{EV}_{\text{current}}[k]$$

where:

$$\text{EV}_{\text{current}} = \log_2\!\left(\frac{Y_{\text{measured}}}{Y_{\text{target}}}\right)$$

#### PI Controller

AE universally employs a PI (Proportional-Integral, 比例-积分) controller. Pure proportional control produces a steady-state error, while PD control tends to introduce high-frequency oscillations in noisy scenes.

**Control law:**

$$\Delta \text{EV}[k] = K_p \cdot e[k] + K_i \cdot \sum_{j=0}^{k} e[j] \cdot T_s$$

where:
- $K_p$: proportional gain — determines response speed
- $K_i$: integral gain — eliminates steady-state error
- $T_s$: sampling time (frame period, e.g., 1/30s)
- $\sum e[j] \cdot T_s$: error integral — accumulates historical deviations

**Physical interpretation:**
- $K_p$ term: the larger the current-frame error, the larger the adjustment (immediate response)
- $K_i$ term: long-term error accumulation → eliminates steady-state offset caused by metering bias

**Parameter impact analysis:**

| Parameter | Too large | Too small |
|-----------|-----------|-----------|
| $K_p$ | Oscillation (overshoot), flickering sensation | Slow convergence (sluggish) |
| $K_i$ | Integrator windup, long-term oscillation | Residual steady-state error |

**Anti-windup (防积分饱和):**

```python
# 积分项限幅，防止饱和
integral = clip(integral + e * Ts, -integral_max, integral_max)
```

**Exposure saturation detection and integral freeze:** When $t = t_{\max}$ and $\text{Gain} = \text{Gain}_{\max}$ but the image is still underexposed (extreme low-light scene), the integral term should be frozen (anti-windup) to prevent the control output from exceeding the physical range. When the scene brightens, the integral term is released smoothly from its maximum value to avoid overexposure overshoot.

#### Bang-Bang Control (Large-Error Fast Convergence)

When the error $|e|$ exceeds threshold $e_{\text{thresh}}$ (typical value 1.5 EV), the system switches to bang-bang control:

$$\Delta \text{EV}[k] = \text{sign}(e[k]) \cdot \Delta \text{EV}_{\max}$$

This allows the system to complete a large-range exposure adjustment in 2–3 frames when entering extreme low-light scenes (e.g., entering a tunnel) or extreme highlight scenes, before smoothly switching back to the PI controller for fine convergence.

#### Convergence Stability Analysis

System transfer function (Z-domain):

$$H(z) = K_p + K_i \cdot T_s \cdot \frac{z}{z-1}$$

Closed-loop stability conditions (Jury criterion) require that the characteristic roots lie inside the unit circle. For a typical camera system (single-frame delay):

$$K_p < 2, \quad K_i < \frac{2}{T_s}$$

In practice, with $K_p$ in the range 0.3–0.7 and $K_i$ in the range 0.05–0.2 (Hz), the system converges within 5–10 frames with no noticeable oscillation.

### 1.4 Multi-Frame HDR AE (Auto HDR)

#### Scene Dynamic Range Estimation

The scene dynamic range (DR) is estimated by analyzing the bimodal characteristics of the luminance histogram.

**Histogram bimodal detection algorithm:**
1. Compute the normalized luminance histogram $H(v)$, $v \in [0, 255]$
2. Gaussian smoothing: $\tilde{H}(v) = H(v) * G_\sigma$, $\sigma = 5$
3. Find peaks: detect local maxima satisfying $\tilde{H}'(v) = 0$, $\tilde{H}''(v) < 0$
4. If two peaks $v_1 < v_2$ are detected with $v_2 - v_1 > 80$ (more than approximately 2.5 EV), the scene is classified as high-DR

**Scene DR estimation:**

$$\text{DR}_{\text{scene}} \approx \log_2\!\left(\frac{Y_{99\%}}{Y_{1\%}}\right) \quad [\text{EV}]$$

where $Y_{1\%}$ and $Y_{99\%}$ are the 1st and 99th percentiles of luminance, respectively.

#### Auto HDR Trigger Conditions

```
触发 HDR 的条件（满足任一）：
  1. DR_scene > DR_sensor_single（通常 > 12 EV）
  2. 直方图双峰检测阳性
  3. 高光像素比例 > 5% 且阴影像素比例 > 5%（高光过曝 + 阴影欠曝同时存在）
```

HDR exit conditions (consecutive N frames, for stability):
- DR_scene < DR_sensor_single − 2 EV (hysteresis margin to prevent frequent switching)

#### Exposure Pair Selection

HDR requires choosing the exposure ratio between a long exposure (to capture shadow detail) and a short exposure (to preserve highlight detail):

$$N_{\text{stops}} = \text{DR}_{\text{scene}} - \text{DR}_{\text{sensor\_single}}$$

$$\text{EV}_{\text{long}} = \text{EV}_{\text{target}} + \frac{N_{\text{stops}}}{2}, \quad \text{EV}_{\text{short}} = \text{EV}_{\text{target}} - \frac{N_{\text{stops}}}{2}$$

Typical exposure pairs: $N_{\text{stops}} = 2 \sim 4$ EV (exposure ratios of 1:4 to 1:16).

#### AE Strategy Differences: Staggered HDR vs. Multi-Frame HDR

| Property | Staggered HDR (sensor-level, 传感器级) | Multi-Frame HDR (algorithm-level, 算法级) |
|----------|----------------------------------------|------------------------------------------|
| Frame rate impact | None (two exposures within one frame) | Effective frame rate halved |
| Motion artifacts | Low (time difference extremely small, microsecond-scale) | High (inter-frame time difference is larger) |
| AE adjustment delay | 1 frame | 2 frames |
| Exposure ratio limit | Typically ≤ 4:1 (sensor architecture constraint) | Flexible, up to 16:1 |
| AE strategy | Long-exposure frame used as AE reference | Geometric mean (mid-exposure) used as target |

### 1.5 Anti-Banding (防频闪)

#### Fluorescent Light Flicker Principle

Fluorescent lights (including LED lights with PWM dimming) are driven by mains AC power and flicker periodically at $2 \times f_{\text{AC}}$:
- 50 Hz mains → 100 Hz flicker (China, Europe)
- 60 Hz mains → 120 Hz flicker (USA, Japan)

When the camera shutter time is not an integer multiple of the flicker period, adjacent frames capture different flicker phases, resulting in:
1. Inter-frame luminance jumps ("flickering" sensation in video, Flicker)
2. Horizontal bright/dark bands (Banding) in the image

#### Anti-Banding Shutter Constraint

To eliminate the flicker effect, the shutter time must be an integer multiple of the flicker half-period:

$$t = \frac{k}{2 \times f_{\text{line}}}, \quad k = 1, 2, 3, \ldots$$

where $f_{\text{line}}$ is the mains frequency (50 Hz or 60 Hz):
- 50 Hz environment: $t \in \{1/100, 1/50, 1/33, 1/25, \ldots\}$ s (i.e., 10 ms, 20 ms, 30 ms, 40 ms, …)
- 60 Hz environment: $t \in \{1/120, 1/60, 1/40, 1/30, \ldots\}$ s (i.e., 8.33 ms, 16.67 ms, 25 ms, 33.3 ms, …)

#### Automatic Frequency Detection

In scenes where the mains frequency is unknown (e.g., international travel with frequent country changes), automatic detection methods include:

**Method 1: Time-domain analysis**
- Compare the global luminance changes across consecutive frames; detect periodic fluctuations at 100 Hz or 120 Hz.

**Method 2: Spatial-domain analysis (in-image band detection)**
- Compute the column mean of the image to obtain a 1D luminance curve $P(y)$
- Apply FFT to $P(y)$ and detect the stripe pitch corresponding to the dominant frequency
- Stripe pitch $\Delta y = \frac{t_{\text{row}} \cdot f_{\text{sensor}}}{f_{\text{line}}}$, where $t_{\text{row}}$ is the row period

#### Trade-Off with SNR

Anti-banding constraints reduce the AE system's degrees of freedom. In low-light scenes:
- The optimal shutter time (maximizing SNR) might be 1/80s
- But the anti-banding constraint only permits 1/100s or 1/50s
- Choosing 1/100s → underexposure, requiring higher ISO (SNR decreases by approximately 1.5 dB)

**Solution:** Enforce anti-banding in video mode; in still-photo mode it can optionally be disabled (a single frame is not affected by inter-frame flicker, but may show banding).

### 1.6 AI-Assisted AE

#### Scene Luminance Prediction

Traditional AE is based on the metering result of the current frame and carries a 1–2-frame response delay. AI-assisted AE uses a CNN to predict the optimal EV for the next frame:

**Network architecture:** Lightweight CNN (MobileNetV3 backbone, <1M parameters); input is a RAW/YUV thumbnail downsampled to 64×64; output is the predicted EV offset $\Delta \text{EV}_{\text{pred}}$.

**Training objective:** Minimize the L1 loss between the predicted EV and the manually labeled optimal EV.

#### Task-Driven AE

Traditional AE optimizes for "human-visual-perception-optimal" brightness. However, for machine vision tasks (object detection, face recognition), the optimal exposure differs.

**Onzon et al., CVPR 2021 (arXiv:2104.01906):** Proposes using the performance loss of a downstream task (face detection) as the AE training objective, achieving end-to-end training through a differentiable ISP simulator. Experiments show that task-driven AE improves mAP by approximately 8% in low-light face detection compared with traditional AE.

#### Night-Scene "Virtual AE"

**Chen et al., CVPR 2018 (arXiv:1805.01934, "Learning to See in the Dark"):** Proposes abandoning the traditional high-ISO approach in favor of capturing RAW data with low ISO and short exposure, then enhancing brightness through a deep-learning network. This effectively implements "virtual exposure compensation" in the RAW domain:

$$I_{\text{enhanced}} = \text{UNet}(I_{\text{RAW\_low}}, \alpha)$$

where $\alpha = \text{EV}_{\text{target}} / \text{EV}_{\text{captured}}$ is the gain ratio.

**Advantage:** Lower ISO produces less noise; the neural network denoises more effectively, and the final SNR exceeds that of the traditional high-ISO approach.

#### Reinforcement Learning for Personalized Exposure Control

Traditional AE converges to a fixed brightness target (typically 18% gray), which cannot adapt to individual user shooting preferences (e.g., preference for high-key portraits or low-key style). Reinforcement learning (RL) formulates exposure control as a sequential decision problem:

- **State $s_t$:** Current-frame histogram features, metering zone luma distribution, EV history
- **Action $a_t$:** EV adjustment $\Delta\text{EV} \in \{-1, -0.5, 0, +0.5, +1\}$ EV
- **Reward $r_t$:** Exposure satisfaction score based on a user preference model (can be distilled from an IQA network or human preference data)

A typical RL policy network is a lightweight MLP (<100K parameters) that takes histogram features as input and outputs Q-values for ε-greedy action selection. Training uses DQN (Deep Q-Network) or PPO, with a reward function that combines perceptual exposure quality with user historical preferences. This approach can learn different exposure preferences across users in the same scene, providing more personalization than a fixed EV target PI controller **[10]**.

#### Semantic Metering (CLIP-Guided)

CLIP (Contrastive Language-Image Pre-training, Radford et al., ICML 2021) embeds images and text into a shared semantic space, providing a foundation for semantically guided AE:

**CLIP-guided metering principle:**
1. The user or a scene classifier provides a semantic description, e.g., "sharp facial detail" or "rich sunset tones"
2. Encode the semantic description as a CLIP text feature $z_{\text{text}} = \text{CLIP\_text}(prompt)$
3. Compute CLIP image features $z_{\text{img}}^{(EV)}$ for estimated images across a range of candidate EVs
4. Select the EV with maximum cosine similarity: $\text{EV}^* = \arg\max_{EV} \langle z_{\text{img}}^{(EV)}, z_{\text{text}} \rangle$

In practice, candidate EV "estimated images" can be generated via fast gamma simulation of the current frame at ±EV offsets, avoiding multiple actual exposures. CLIP-IQA+ (Wang et al., TPAMI 2023) **[11]** demonstrated that CLIP features are highly sensitive to exposure quality and can serve as semantic reward signals for AE.

**Current engineering limitation:** CLIP ViT-L/14 inference takes ~50 ms (A100) or ~200–500 ms on a mobile NPU — too slow for per-frame AE closed-loop control. A practical approach is to use CLIP scoring offline to generate a "semantic target luma lookup table," which the traditional PI controller then queries online.

### 1.7 AE Strategies for Difficult Scenes

| Scene | Main challenge | AE failure mode | Solution |
|-------|---------------|-----------------|---------|
| Backlighting (subject in front of window) | Extremely bright background, dark subject | Subject underexposed (background luminance dominates metering) | Face detection + face-priority metering; or trigger HDR |
| Snow / white sand | High-reflectance scene | Overall underexposure (18%-gray target too low) | Automatic +1 ~ +2 EV compensation (via scene classification) |
| Concert / stage | Strong spotlight + extremely dark background | Subject overexposed | Spot metering + highlight-preservation weighting |
| Tunnel exit | Extremely large scene DR change (~5 EV/second) | Brief overexposure | Bang-bang control + predictive AE |
| Candlelight / warm light source | Low-color-temperature, extremely bright source | Orange light source triggers AE overexposure protection | Color-temperature-aware metering (reduce warm-channel weight) |
| Mixed lighting | Multi-source luminance variation | Average metering pulled high by highlights | Histogram-percentile metering (avoid mean being skewed by extremes) |
| Night vehicle headlights | Moving high-brightness point source | Frequent AE jumps | Temporal filtering + headlight-region exclusion |

---

## §2 Calibration

### 2.1 Camera Response Function (CRF, 相机响应函数) Linearization Calibration

The AE controller assumes a linear relationship (in the log domain) between exposure and sensor output. If the CRF is non-linear, the controller model is inaccurate and convergence oscillations result.

**Calibration procedure:**

1. Use an integrating sphere (积分球) or a standard gray card as a uniform light source.
2. Sweep the exposure parameters from minimum to maximum in 0.5 EV increments.
3. Record the sensor output (RAW mean value) at each exposure point.
4. Fit a log-linear model: $\log_2(Y) = a \cdot \text{EV} + b$
5. Verify linearity ($R^2 > 0.999$); otherwise compensate with a LUT.

**Common sources of non-linearity:**
- Analog gain switching points (gain error when switching from 1× to 2×)
- Effect of read-out noise floor in the low-exposure segment
- Sensor slew-rate-limited saturation in the high-exposure segment

### 2.2 AE Convergence Speed Test

**Test procedure:**
1. Point the camera at a uniform gray card; manually set an extreme exposure (e.g., 3 EV overexposed).
2. Switch to AE mode; record the metered luminance $Y[k]$ for each frame.
3. Compute convergence time $T_{\text{conv}}$: defined as the index of the first frame where $|Y[k] - Y_{\text{target}}| < 5\%$.

**Pass criteria:**
- Mobile real-time preview: $T_{\text{conv}} \leq 15$ frames (@30fps, i.e., 0.5s)
- Video recording mode (requires smooth adjustment): per-frame EV adjustment $\leq 0.3$ EV

---

## §3 Tuning

### 3.1 Metering Zone Weight Map (Zone Weight Map) Tuning

Different metering modes correspond to different weight maps; tuning should be optimized for the target scene:

**Matrix metering weight map tuning principles:**
- Increase the weight of the central zone: suited to portrait scenes with a centered subject.
- Increase the weight of the lower half: suited to landscape photography (the sky zone has high reflectance and easily causes the ground to be underexposed).
- Introduce variance weighting: reduces the influence of bright zones (e.g., sky) on metering.

**Weight map validation tool:** Use a test image library (including typical difficult scenes such as backlighting, snow, concert) to statistically compute the $\Delta \text{EV}$ of the subject zone (deviation from optimal exposure), and optimize the weighted sum for each scene.

### 3.2 PI Controller Parameter Tuning

**Tuning procedure (empirical Ziegler-Nichols method):**

1. Set $K_i$ to 0 and gradually increase $K_p$ until the system sustains constant-amplitude oscillations; at this point $K_p = K_{p,\text{crit}}$ and the oscillation period is $T_{\text{crit}}$.
2. Set $K_p = 0.45 \cdot K_{p,\text{crit}}$, $K_i = 1.2 \cdot K_p / T_{\text{crit}}$ **[5]**.
3. Fine-tune in real scenes, focusing on: scene-transition convergence speed and absence of flickering in static scenes.

### 3.3 Three-Platform AEC Key Parameter Comparison

AEC (Auto Exposure Control) parameters differ significantly across SoC platforms. The following table provides a cross-platform reference:

| Function | Qualcomm CamX / Chromatix | MTK Imagiq / NDD | HiSilicon |
|----------|--------------------------|-----------------|-----------|
| Target luminance | `AEC_TargetLuma` (0–255, 8-bit) | `AETargetMean` (NDD uint8) | `AE_TargetY` (JSON float) |
| ISO upper limit | `AEC_MaxISO` (integer, e.g., 3200) | `AEMaxISO` (NDD integer) | `AE_MaxAnalogGain` (multiplier) |
| Shutter upper limit | `AEC_MaxExpTimeMs` (milliseconds) | `AEMaxExpTime` (µs) | `AE_MaxExposureUs` |
| Metering mode | `AEC_MeteringMode` (enum: CENTER/MATRIX/SPOT) | `AEMeteringMode` (enum) | `AE_MeteringType` |
| Convergence speed | `AEC_StepSize` (EV step, 0.0–1.0) | `AEConvergeSpeed` (fast/medium/slow enum) | `AE_ConvergenceRate` (float) |
| Anti-banding | `AEC_AntiFlickerMode` (50Hz/60Hz/AUTO) | `AEAntiFlickerMode` (NDD enum) | `AE_FlickerDetectEnable` |
| ISO/exposure priority | `AEC_ISOPriority` (ISO_PRIORITY/SHUTTER_PRIORITY/AUTO) | `AEExpPriority` (NDD) | `AE_ExposurePriority` |
| Zone weight map | `AEC_ZoneWeightMap` (9×7 or 16×12 grid XML) | `AEWeightTable` (NDD float array) | `AE_ZoneWeight[]` |

**Qualcomm CamX tuning path:**

Chromatix parameters are stored in `chromatix_aec_ext.xml` and can be visually edited via the Qualcomm Camera IQ Tuning Tool (CIQT). Key path:

```
CamX Pipeline → AECNode → AECAlgorithm
    ├── chromatix_aec_ext.xml       ← Core AEC parameters (target luma/convergence speed/weight map)
    ├── chromatix_aec_adrc.xml      ← ADRC (Adaptive Dynamic Range Compression) parameters
    └── chromatix_sensor_XXXX.xml   ← Sensor-specific exposure constraints
```

**MTK NDD tuning path:**

MTK uses the NDD (Noise Distribution Data) file format to manage AE/AWB/AF parameters uniformly:

```
FeaturePipe/
├── Scenario_xxx.NDD       ← Scene-level NDD (including AE parameters)
│   ├── [AE]
│   │   ├── AETargetMean   = 128
│   │   ├── AEMaxISO       = 3200
│   │   ├── AEConvergeSpeed = MEDIUM
│   │   └── AEAntiFlicker  = AUTO
└── Camera_Device_Info.xml ← Sensor physical parameter binding
```

MTK Camera Tool (via ADB connection) supports real-time NDD parameter injection without reflashing firmware, significantly improving debug efficiency.

**Practical tuning tips:**

- **Qualcomm platform:** `AEC_TargetLuma` is tightly coupled with the tonemap curve — increasing the target luminance without simultaneously lowering the gamma curve's bright segment will cause highlight overexposure.
- **MTK platform:** Setting `AEConvergeSpeed` to FAST in low-light scenes introduces noticeable AE hunting; a per-lux-index segmented strategy for low-light is recommended.
- **HiSilicon:** `AE_MaxExposureUs` must be maintained in sync with anti-banding constraints; otherwise the anti-banding constraint gets truncated by MaxExposure, causing flicker to reappear.

### 3.4 AE Convergence State Machine and Anti-Hunting Engineering

#### 3.4.1 Android HAL3 AE State Machine (6-State Standard)

The Android Camera3 HAL3 specification defines 6 standard AE states. All Android CDD-compliant devices must implement and correctly report these states (source: Android AOSP Camera3 3A Modes and State Transitions **[12]**):

| State constant | Description |
|---------------|-------------|
| `AE_STATE_INACTIVE` | Initial state; device must start in this state at boot; AE algorithm has not yet run |
| `AE_STATE_SEARCHING` | Not converged; actively adjusting exposure parameters; frame brightness is still off target |
| `AE_STATE_CONVERGED` | Good exposure found; parameters **not locked**; HAL may spontaneously leave this state to search for better exposure |
| `AE_STATE_LOCKED` | Locked via `AE_LOCK=true`; parameters frozen until `AE_LOCK=false` |
| `AE_STATE_FLASH_REQUIRED` | Converged, but HAL determines a flash is required for correct exposure in the current scene |
| `AE_STATE_PRECAPTURE` | Executing pre-capture metering sequence (e.g., flash pre-exposure, HDR multi-metering frames) |

**Typical state transition paths:**

```
Power-on initialization:
  INACTIVE → SEARCHING → CONVERGED  (normal convergence path)

Shutter press (with pre-capture):
  CONVERGED → PRECAPTURE → LOCKED → SEARCHING → CONVERGED
                                     (re-search after capture)

AE Lock operation:
  Any state + AE_LOCK=true  →  LOCKED
  LOCKED  + AE_LOCK=false   →  SEARCHING → CONVERGED

Flash scene:
  SEARCHING → FLASH_REQUIRED  (low light, cannot reach target by exposure alone)
  FLASH_REQUIRED + trigger flash → PRECAPTURE → LOCKED
```

> **Engineering note:** `AE_STATE_CONVERGED` does NOT mean parameters are locked — the HAL may still fine-tune exposure in this state (typically within ±0.1 EV). Applications that require truly frozen parameters must explicitly set `AE_LOCK=true` and wait for the `AE_STATE_LOCKED` callback before capturing. Ignoring this detail is the root cause of the "slight brightness jump at capture" bug that many camera apps experience in the CONVERGED state.

#### 3.4.2 Anti-Hunting Control Model

**Convergence update formula (multiplicative form):**

$$\text{exposure}(n) = \text{exposure}(n-1) \times \frac{\text{target}}{\text{mean}} \times \frac{1}{\text{damping}}$$

where:
- $\text{target}$: target luminance (e.g., 118, corresponding to 18% gray)
- $\text{mean}$: current-frame metered luminance average
- $\text{damping}$: damping coefficient, $\text{damping} > 1$

In the log domain this is equivalent to $\Delta\text{EV} = \frac{1}{\text{damping}} \cdot \log_2\!\left(\frac{\text{target}}{\text{mean}}\right)$, i.e., a simplified proportional-only form of the PI controller in §1.3. The `damping` parameter corresponds conceptually to the `AE_Tolerance` parameter in Qualcomm Chromatix (typical tolerance ±3–5%):

| damping value | Convergence speed | Stability | Recommended scene |
|--------------|------------------|-----------|------------------|
| Near 1 (e.g., 1.05) | Fast (3–5 frames) | Prone to oscillation | Fast scene transitions, live streaming |
| Medium (1.2–1.5) | Medium (8–12 frames) | Fairly stable | General photography/video |
| Large (2.0+) | Slow (15+ frames) | Very stable | Surveillance / fixed-scene telephoto |

#### 3.4.3 Four Root Causes of AE Oscillation (Engineering Triage Priority)

AE hunting/flicker in production tuning should be diagnosed in the following priority order:

**Root cause 1: Exposure and gain effective-frame mismatch (highest priority, most common)**

Different hardware parameters take effect with different delays: gain may take 1 frame to take effect while shutter time may take 3 frames. If the AE controller does not account for this difference, controlling both parameters simultaneously causes a state mismatch — the controller assumes both have taken effect, but the shutter is still 2 frames behind. It then re-adjusts gain based on the "already converged" false state; when the shutter finally takes effect the frame goes dark, triggering another round of adjustments, creating a 2–3 frame periodic oscillation.

> **Diagnosis:** Capture per-frame {exposure time, gain, metered mean} via ADB and plot the timing diagram. If the oscillation period exactly equals the exposure effective-frame count, this is almost certainly the root cause. **Fix:** Maintain separate "effective-delay queues" for exposure and gain in the AE controller; only include a parameter in error calculation after it has actually taken effect.

**Root cause 2: AE convergence step size too large**

Per-frame EV adjustment amplitude too large (e.g., >0.5 EV/frame), causing the output to oscillate around the target (overshoot oscillation).

> **Fix:** Reduce the maximum step size, or automatically switch to a smaller step size (e.g., 0.1 EV/frame) when close to the target (error < 1 EV).

**Root cause 3: Sensor effective-frame delay configuration incorrect**

The platform's configured "delay frames" parameter does not match the actual sensor hardware behavior (e.g., configured as 2 frames but the sensor actually needs 3 frames).

> **Diagnosis:** Use an oscilloscope or GPIO trigger to measure the actual number of frames between the MIPI frame header register write moment and the sensor output change moment. **Fix:** Update the `ae_delay_frame` field in the sensor driver to match the measured value.

**Root cause 4: AE tolerance (AE_Tolerance) set too small**

The convergence threshold band is too narrow (e.g., ±1%), causing normal frame-to-frame statistical noise (random metering value jitter from noise) to be misidentified as "not converged," continuously triggering new adjustments.

> **Fix:** Widen the tolerance to ±3–5%, or apply time-domain IIR smoothing to the metered value before using it for convergence determination. The typical engineering recommendation for Qualcomm Chromatix `AE_Tolerance` is ±3% (can be relaxed to ±5% in low light).

#### 3.4.4 Qualcomm Chromatix AEC Convergence Parameter System

Key convergence-related parameters in Qualcomm AEC9/AEC10 (source: Qualcomm AEC9 tuning guide **[14]**):

| Parameter | Meaning | Tuning direction |
|-----------|---------|-----------------|
| `Fast Convergence Skip` | Skip frames during fast-convergence phase (run AE every N frames) | Decrease → faster convergence, higher power |
| `Slow Convergence Skip` | Skip frames during slow-convergence phase (near convergence) | Increase → more power efficient, slower response |
| `lux_index` | Illuminance index based on TL84 400 lux; used to build trigger intervals | Set different AE behavior per illuminance segment |
| Three-segment luma target | High light (55) → medium light (50→45) → low light (40→25) | Lowering the low-light target reduces gain noise |
| `MinTargetAdjRatio` | safe_target convergence lower bound (typical: 0.6) | Prevents AE from over-darkening the image |
| `MaxTargetAdjRatio` | safe_target convergence upper bound (typical: 2.0) | Prevents AE from over-brightening and clipping highlights |

> **lux_index and luma_target coupling logic:** Higher lux_index means brighter scene; target luminance drops from 55 down to 25. In strong light, the sensor risks highlight overload — a lower target preserves headroom for the tonemap. In low light, the target is also lowered to avoid pushing gain to the maximum and introducing heavy noise.

---

## §4 Artifacts

### 4.1 Flicker / Banding (频闪/条纹)

**Cause:** Shutter time is not aligned to an integer multiple of the fluorescent-light flicker period.

**Diagnosis:** After recording video, extract the per-frame global mean and observe whether there is a periodic fluctuation at 100/120 Hz; alternatively, apply column-mean FFT to a single frame to detect spatial banding.

**Remediation:**
- Confirm that the anti-banding constraint is correctly activated for the target mains frequency.
- Check the shutter-time quantization precision (integer-multiple error of the row period $t_{\text{row}}$).

### 4.2 Overexposure Clipping (过曝截断)

**Cause:** The target luminance is set too high, or the highlight-preservation weight is insufficient.

**Diagnosis:** Count the percentage of highlight-saturated pixels per frame; recommended threshold: $< 0.5\%$ (excluding specular reflection points).

**Remediation:**
- Lower the target luminance $Y_{\text{target}}$ (e.g., from 118 to 108).
- Introduce highlight-aware weighting: when a highlight zone is detected, reduce the target luminance.

### 4.3 AE Hunting (AE闪烁)

**Cause:** $K_p$ is too large; exposure and gain effective-frame mismatch; AE_Tolerance set too small; or the scene luminance itself has periodic variation (e.g., alternating tree shadows while driving).

**Triage priority:** Follow the four root causes in §3.4.3 in order: (1) effective-frame mismatch → (2) step size too large → (3) sensor delay configuration wrong → (4) tolerance too small.

**Remediation:**
- Check the actual effective-frame count for exposure and gain separately; maintain independent delay compensation queues in the AE controller (diagnose first).
- Widen `AE_Tolerance` to ±3–5% (see §3.4.4 for Qualcomm Chromatix recommended values).
- Reduce $K_p$ (trade-off: slower convergence).
- Apply temporal low-pass filtering to the metering result (exponential smoothing): $Y_{\text{filtered}}[k] = \alpha Y[k] + (1-\alpha)Y_{\text{filtered}}[k-1]$, $\alpha = 0.3 \sim 0.5$.

---

## §5 Evaluation

### 5.1 DXOMARK Metering Accuracy Tests

DXOMARK AE evaluation items include:

| Test item | Evaluation method | Pass criterion |
|-----------|------------------|----------------|
| Lux-level accuracy | Change illuminance in an integrating sphere by multiples; measure AE response | EV error $\leq \pm 0.5$ EV |
| Brightness uniformity (Uniformity) | Measure luminance standard deviation across different zones of the frame | $\sigma_Y < 5$ DN (8-bit) |
| Convergence speed | Step response test (from extremely dark to normal light) | $T_{\text{conv}} < 0.5$ s |
| Flicker robustness | Record video under 100/120 Hz light source; analyze inter-frame luminance variation | Variation $\Delta Y < 2\%$ |

### 5.2 Typical Illuminance Level Test Table

| Illuminance (lux) | Scene description | Expected shutter | Expected ISO |
|-------------------|------------------|-----------------|-------------|
| 100,000 | Direct bright sunlight | 1/4000s | 50 |
| 10,000 | Overcast outdoors | 1/500s | 100 |
| 1,000 | Indoor fluorescent lighting | 1/100s | 200 |
| 100 | Dusk indoors | 1/30s | 800 |
| 10 | Night indoors | 1/10s | 3200 |
| 1 | Candlelight | 1/4s | 6400 |

---

## §6 Code Reference

### 6.1 PI Controller Simulation (Python)

```python
import numpy as np
import matplotlib.pyplot as plt

class AEController:
    """
    自动曝光 PI 控制器仿真

    控制律：delta_EV[k] = Kp * e[k] + Ki * integral(e)
    在对数（EV）域操作，保证线性控制特性
    """

    def __init__(self, Kp=0.5, Ki=0.1, Ts=1/30.0,
                 ev_min=-3.0, ev_max=3.0,
                 integral_max=2.0):
        self.Kp = Kp
        self.Ki = Ki
        self.Ts = Ts                   # 采样时间（帧时间）
        self.ev_min = ev_min           # 最小 EV 偏移
        self.ev_max = ev_max           # 最大 EV 偏移
        self.integral_max = integral_max

        self.integral = 0.0            # 积分累积量
        self.ev_current = 0.0          # 当前 EV

        # Bang-bang 参数
        self.bangbang_threshold = 1.5  # EV
        self.bangbang_step = 1.0       # EV/frame

    def compute(self, Y_measured, Y_target=118.0):
        """
        计算 AE 调整量

        Args:
            Y_measured: 当前帧测光亮度（8-bit，0-255）
            Y_target:   目标亮度（默认 118，对应 18% 灰）

        Returns:
            delta_ev: EV 调整量（正值 = 增加曝光）
        """
        # 避免 log(0)
        Y_measured = max(Y_measured, 1e-6)

        # 计算 EV 误差（对数域）
        e = np.log2(Y_target / Y_measured)

        # Bang-bang 控制（大误差快速收敛）
        if abs(e) > self.bangbang_threshold:
            delta_ev = np.sign(e) * self.bangbang_step
            # 大误差时清零积分，防止切回 PI 后的积分冲击
            self.integral = 0.0
            return np.clip(delta_ev, self.ev_min, self.ev_max)

        # PI 控制
        self.integral += e * self.Ts
        # Anti-windup：积分项限幅
        self.integral = np.clip(self.integral,
                                -self.integral_max,
                                self.integral_max)

        delta_ev = self.Kp * e + self.Ki * self.integral

        return np.clip(delta_ev, self.ev_min, self.ev_max)

    def apply_ev(self, delta_ev):
        """更新当前 EV"""
        self.ev_current = np.clip(self.ev_current + delta_ev,
                                  -10.0, 10.0)
        return self.ev_current


def simulate_ae(scene_ev=0.0, init_ev=-3.0, n_frames=60,
                Kp=0.5, Ki=0.1):
    """
    模拟 AE 收敛过程

    Args:
        scene_ev: 场景 EV（真实亮度对应的 EV）
        init_ev:  初始 AE EV（模拟从极暗进入正常场景）
        n_frames: 仿真帧数
    """
    controller = AEController(Kp=Kp, Ki=Ki)
    controller.ev_current = init_ev

    ev_history = []
    y_history = []

    Y_target = 118.0

    for k in range(n_frames):
        # 模拟传感器输出（假设 CRF 线性）
        # Y_measured = Y_target * 2^(scene_ev - ev_current)
        ev_diff = scene_ev - controller.ev_current
        Y_measured = Y_target * (2 ** ev_diff)
        Y_measured = np.clip(Y_measured, 0, 255)

        ev_history.append(controller.ev_current)
        y_history.append(Y_measured)

        # AE 调整
        delta_ev = controller.compute(Y_measured, Y_target)
        controller.apply_ev(delta_ev)

    return np.array(ev_history), np.array(y_history)


# 收敛曲线可视化
if __name__ == "__main__":
    ev_hist, y_hist = simulate_ae(
        scene_ev=0.0, init_ev=-3.0, n_frames=60,
        Kp=0.5, Ki=0.1
    )

    frames = np.arange(len(ev_hist))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))

    ax1.plot(frames, ev_hist, 'b-o', markersize=3, label='EV current')
    ax1.axhline(y=0, color='r', linestyle='--', label='EV target')
    ax1.set_xlabel('Frame'); ax1.set_ylabel('EV')
    ax1.set_title('AE PI Controller Convergence'); ax1.legend()
    ax1.grid(True)

    ax2.plot(frames, y_hist, 'g-o', markersize=3, label='Y measured')
    ax2.axhline(y=118, color='r', linestyle='--', label='Y target (118)')
    ax2.set_xlabel('Frame'); ax2.set_ylabel('Luminance (8-bit)')
    ax2.legend(); ax2.grid(True)

    plt.tight_layout()
    plt.savefig('ae_convergence.png', dpi=150)
    print("Convergence plot saved to ae_convergence.png")
```

### 6.2 Histogram Bimodal Detection (Scene DR Estimation)

```python
import numpy as np
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d

def estimate_scene_dr(image_gray: np.ndarray) -> dict:
    """
    通过直方图双峰检测估计场景动态范围

    Args:
        image_gray: 灰度图像（uint8 或 float，值域 [0, 255]）

    Returns:
        result: dict，包含 DR 估计值、是否触发 HDR、峰值位置
    """
    # 计算归一化直方图
    hist, bin_edges = np.histogram(
        image_gray.flatten(), bins=256, range=(0, 256), density=True
    )

    # 高斯平滑（抑制噪声）
    hist_smooth = gaussian_filter1d(hist.astype(float), sigma=5)

    # 寻找峰值（最小峰高度和间距过滤噪声峰）
    peaks, properties = find_peaks(
        hist_smooth,
        height=np.max(hist_smooth) * 0.05,   # 最小峰高：最大值的 5%
        distance=30,                           # 最小峰间距：30 bins（约 1 EV）
        prominence=np.max(hist_smooth) * 0.03 # 最小显著性
    )

    # 百分位数 DR 估计
    flat = image_gray.flatten()
    p1 = np.percentile(flat, 1)
    p99 = np.percentile(flat, 99)

    # 避免 log(0)
    p1 = max(p1, 1.0)
    p99 = max(p99, p1 + 1.0)

    dr_ev = np.log2(p99 / p1)

    # 双峰检测
    is_bimodal = len(peaks) >= 2
    if is_bimodal:
        peak_gap = peaks[-1] - peaks[0]  # bins
        ev_gap = peak_gap / (256 / 14)   # 粗略转换为 EV（假设 14 EV 全动态范围）
        is_bimodal = ev_gap > 2.5        # 峰值间距 > 2.5 EV 才判定

    # HDR 触发条件
    sensor_dr_single = 12.0  # 典型单帧传感器动态范围（EV）
    trigger_hdr = (dr_ev > sensor_dr_single) or is_bimodal

    # 高光/阴影像素比例
    total = flat.size
    highlight_ratio = np.sum(flat > 240) / total
    shadow_ratio = np.sum(flat < 15) / total
    if highlight_ratio > 0.05 and shadow_ratio > 0.05:
        trigger_hdr = True

    return {
        'dr_ev': dr_ev,
        'trigger_hdr': trigger_hdr,
        'is_bimodal': is_bimodal,
        'n_peaks': len(peaks),
        'peak_positions': peaks.tolist(),
        'highlight_ratio': highlight_ratio,
        'shadow_ratio': shadow_ratio
    }


# 使用示例
if __name__ == "__main__":
    # 生成模拟双峰直方图图像（逆光场景）
    np.random.seed(42)
    # 背景（高亮）和前景（阴影）各占一半
    background = np.random.normal(200, 20, (480, 320)).clip(0, 255)
    foreground = np.random.normal(50, 15, (480, 320)).clip(0, 255)
    image = np.concatenate([background, foreground], axis=1).astype(np.uint8)

    result = estimate_scene_dr(image)

    print(f"Scene DR: {result['dr_ev']:.2f} EV")
    print(f"Trigger HDR: {result['trigger_hdr']}")
    print(f"Bimodal histogram: {result['is_bimodal']}")
    print(f"Highlight ratio: {result['highlight_ratio']:.1%}")
    print(f"Shadow ratio: {result['shadow_ratio']:.1%}")
```

### 6.3 Anti-Banding Shutter Quantization

```python
def quantize_shutter_to_antibanding(
    t_optimal: float,
    ac_freq: float = 50.0,
    prefer_shorter: bool = True
) -> float:
    """
    将最优快门时间量化到最近的防频闪合法值

    Args:
        t_optimal:      AE 计算出的最优快门时间（秒）
        ac_freq:        市电频率（50 或 60 Hz）
        prefer_shorter: True = 选择更短的合法快门（防过曝），
                        False = 选择更长的合法快门（优先 SNR）

    Returns:
        t_legal: 防频闪合法快门时间（秒）
    """
    # 最短合法快门 = 闪烁半周期
    t_unit = 1.0 / (2.0 * ac_freq)  # 1/100s (50Hz) 或 1/120s (60Hz)

    # 计算最优快门对应的整数倍
    k_float = t_optimal / t_unit
    k_floor = max(1, int(np.floor(k_float)))
    k_ceil  = k_floor + 1

    t_floor = k_floor * t_unit
    t_ceil  = k_ceil  * t_unit

    if prefer_shorter:
        # 优先选择更短（防止过曝），除非过短导致欠曝 > 0.5 EV
        ev_diff_floor = np.log2(t_optimal / t_floor)  # 正值 = 欠曝
        if ev_diff_floor > 0.5:
            return t_ceil   # 欠曝太多，选更长的
        return t_floor
    else:
        # 优先选择更长（最大化 SNR）
        ev_diff_ceil = np.log2(t_ceil / t_optimal)    # 正值 = 过曝
        if ev_diff_ceil > 0.5:
            return t_floor  # 过曝太多，选更短的
        return t_ceil


# 示例
if __name__ == "__main__":
    t_opt = 1.0 / 85.0   # 最优快门 1/85s

    t_50hz = quantize_shutter_to_antibanding(t_opt, ac_freq=50.0)
    t_60hz = quantize_shutter_to_antibanding(t_opt, ac_freq=60.0)

    print(f"最优快门: 1/{1/t_opt:.0f}s = {t_opt*1000:.2f}ms")
    print(f"50 Hz 防频闪: 1/{1/t_50hz:.0f}s = {t_50hz*1000:.2f}ms "
          f"(ΔEV = {np.log2(t_50hz/t_opt):+.2f})")
    print(f"60 Hz 防频闪: 1/{1/t_60hz:.0f}s = {t_60hz*1000:.2f}ms "
          f"(ΔEV = {np.log2(t_60hz/t_opt):+.2f})")
```

---

## Chapter Summary

This chapter presented the complete technical system of the auto exposure algorithm:

1. **Exposure equation and the EV system:** Established a log-linear model relating exposure parameters (aperture, shutter, ISO) to sensor output, laying the foundation for controller design.
2. **Metering systems:** From matrix metering to face-priority metering — each mode is suited to different scenes and should be selected flexibly according to the shooting intent.
3. **AE convergence algorithm:** The PI controller operating in the log domain is the core of AE stability; bang-bang control handles large-error scenarios; anti-windup ensures long-term stability.
4. **HDR AE:** Histogram bimodal detection and DR estimation are the key triggers for HDR mode; exposure pair selection must balance highlight preservation with shadow recovery.
5. **Anti-banding:** Quantizing shutter time to integer multiples of the flicker half-period is the fundamental constraint for eliminating banding; a trade-off between SNR and anti-banding is required.
6. **AI-assisted AE:** Task-driven AE and deep-learning night-scene enhancement represent the frontier directions of AE algorithm research.

> **Next chapter preview:** Chapter 25 will introduce the theoretical foundations of Auto White Balance (AWB), including color temperature estimation, the gray-world assumption, and statistical white balance algorithms.

---

## §7 Glossary

| Term | Full name / Chinese | Definition |
|------|---------------------|-----------|
| AE | Auto Exposure (自动曝光) | Control loop that automatically selects exposure parameters to achieve a target image brightness |
| EV | Exposure Value (曝光值) | Log-base-2 measure of exposure: $\text{EV} = \log_2(N^2/t)$ |
| LV | Light Value (亮度值, $B_v$) | Log-base-2 measure of scene luminance; part of the APEX system |
| EC | Exposure Compensation (曝光补偿) | User-applied offset to the AE target, expressed in EV steps (e.g., +1 EV, −0.7 EV) |
| ISO | International Organization for Standardization sensitivity rating | Standardized measure of sensor sensitivity; doubling ISO doubles gain but also amplifies noise |
| Metering (测光) | Luminance measurement | Process of estimating scene exposure state from image statistics |
| AE Lock (AE锁定) | Auto Exposure Lock | Freezes current exposure parameters; corresponds to `AE_STATE_LOCKED` in Android HAL3 |
| Anti-banding (防频闪) | Flicker suppression | Constraining shutter time to integer multiples of the AC flicker half-period to prevent banding |
| AE Hunting (AE振荡) | Exposure oscillation | Periodic oscillation of image brightness due to excessive gain or improper delay compensation |
| HDR | High Dynamic Range | Imaging technique that captures scenes with dynamic range exceeding single-exposure sensor capability |
| Staggered HDR | Sensor-level HDR | Two exposures within a single frame period using sensor-level time interleaving |
| PDAE | Phase-Detection Auto Exposure | Using PDAF phase-difference statistics to assist exposure control |
| lux-index | Illuminance index | Relative illuminance index used by Qualcomm Chromatix to parameterize AE behavior vs. light level |
| Bang-bang control | On-off control | Maximum-effort control strategy used for large AE errors to achieve fast convergence |
| Anti-windup | Integral clamping | Clamping the PI controller's integral term to prevent integrator windup and output saturation |
| CRF | Camera Response Function | The nonlinear mapping from scene radiance to sensor output; must be linearized for AE accuracy |
| SOS | Standard Output Sensitivity | ISO 12232:2019 sensitivity definition based on standard output level |
| REI | Recommended Exposure Index | ISO 12232:2019 sensitivity definition based on manufacturer recommendation |

---

## §8 Engineering Recommendations

AE engineering success depends not on algorithm choice but on parameter configuration logic — a well-tuned parameter table for a given device can remain valid for years.

| Scene / requirement | Recommended configuration | Key parameter | Notes |
|--------------------|--------------------------|---------------|-------|
| Daytime general photography | Matrix metering + center weighting | `AE_ROI_Weight` matrix | Auto-switch to face-center weighting when face detection is active; fall back to matrix otherwise |
| Backlit / high-contrast scenes | Multi-zone segmented metering + local EV offset | `AE_EV_Offset` scene branch | Do not solve backlighting with global EV offset — selecting the correct metering zone is the real fix |
| Video recording / stabilization | Reduce convergence speed 50–70%, temporal IIR smoothing | `AE_Temporal_Speed` | Preview can converge quickly; recording requires smooth inter-frame brightness transitions; two separate parameter tables |
| Indoor fluorescent lighting | Force anti-banding to 10 ms steps (50 Hz market) | `AE_Flicker_Mode` | China/Europe: 50 Hz; USA: 60 Hz (8.33 ms); international releases must include both configurations |
| Low-light / night mode | Slow convergence + allow slightly dark EV | `AE_LowLight_Bias` | Low-light target should be slightly below the standard target — high ISO noise looks worse than a slightly dark image |
| Pro mode / manual exposure | Disable AE; expose all three axes (EV/ISO/Shutter) | — | Never retain any AE auto-intervention in pro mode; this is a top source of user complaints |

**Debug priorities:**

- **Anti-flicker testing must be done under fluorescent lights, not LED lights:** LED lights typically flicker far above 50/60 Hz and usually do not trigger AE banding. Traditional fluorescent tubes (T8/T5) are the correct test targets. Many teams switched offices to LED lighting and found their anti-flicker tests were no longer valid.
- **Quantify AE step size with "brightness jump per frame" metrics, not subjective evaluation:** Record the frame sequence from severe overexposure (+2 EV) back to normal; count frames where brightness drops more than 2 DN/frame (8-bit) — more than 5 such frames indicates the step is too large and produces visible jitter. Also test the recovery from underexposure (−2 EV): if total frame count exceeds 20 frames, the step size is too small and response is too slow. Test both directions.
- **AE Lock is a state that must be tested independently:** After half-press triggers AE Lock, manually pan to an overexposed area — brightness should not change. After releasing, AE recovery must not produce a brightness jump. The Lock/Unlock state machine transition is often untested during light-source parameter tuning and only discovered after user complaints about "brightness jumping at capture."

**When NOT to build scene-adaptive AE:** If the product line has only one or two models, scene classification inference adds >10 ms latency, or maintaining multiple AE parameter tables carries high engineering cost — maintaining two solid parameter tables (daytime + night) with thorough EV offset tuning often delivers better production stability. Adaptive AE is worth the investment on flagship devices; cost-effectiveness on mid-range devices needs careful evaluation.

---

## Extended Reading

AE tuning has no one-size-fits-all solution — PI parameters vary widely across devices and scenes. Tuning is fundamentally about finding the optimal balance between convergence speed and stability for the specific device. When encountering AE hunting, first check whether the root cause is the integral anti-windup design or the metering zone being dominated by anomalous brightness, before adjusting $K_p$ and $K_i$.

Anti-banding in low-light is a high-frequency complaint point; incorrect shutter quantization precision directly causes horizontal banding under fluorescent lights. Automatic frequency detection (50 Hz vs. 60 Hz) logic is best implemented at the hardware statistics layer rather than relying on software guessing.

Task-driven AE (discussed in more detail in Part 4, Chapter 6) is an interesting direction, but CLIP inference latency on mobile devices is not yet practical for real-time use. Offline generation of a "semantic target luma lookup table" is the currently viable engineering route.

---

## References

[1] CIPA, "DC-004: Sensitivity of digital cameras," Camera & Imaging Products Association (CIPA), 2003.

[1a] ISO, "ISO 12232:2019 — Photography — Digital still cameras — Determination of exposure index, ISO speed ratings, standard output sensitivity, and recommended exposure index," International Organization for Standardization, 2019.

[2] Foi et al., "Practical Poissonian-Gaussian noise modeling and fitting for single-image raw-data," *IEEE Trans. Image Processing*, 2008.

[3] ANSI, "PH2.7-1986: American national standard for photography — Photographic exposure guide," American National Standards Institute, 1986.

[4] IEC, "61966-2-1:1999: Multimedia systems and equipment — Colour measurement and management — Part 2-1: Colour management — Default RGB colour space — sRGB," International Electrotechnical Commission, 1999.

[5] Åström et al., *Computer Controlled Systems: Theory and Design*, 3rd ed. Prentice Hall, 1997.

[6] EMVA, "Standard 1288: Standard for Characterization of Image Sensors and Cameras, Release 4.0," European Machine Vision Association, 2021.

[7] Onzon et al., "Neural Auto-Exposure for High-Dynamic Range Object Detection," *CVPR*, 2021. arXiv:2104.01906.

[8] Chen et al., "Learning to see in the dark," *CVPR*, 2018. arXiv:1805.01934.

[9] DXOMARK, "DXOMARK Camera Test Protocol v4," DXOMARK, 2022. URL: https://www.dxomark.com/category/test-protocols/

[10] Yang et al., "Personalized Exposure Control Using Adaptive Metering and Reinforcement Learning," *IEEE Transactions on Visualization and Computer Graphics*, vol. 25, no. 10, pp. 2953–2968, 2019. DOI: 10.1109/TVCG.2018.2864401.

[11] Wang et al., "Exploring CLIP for assessing the look and feel of images (CLIP-IQA+)," *IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI)*, 2023.

[12] Android AOSP, "Camera3 3A Modes and State Machines," Android Open Source Project, 2024. URL: https://aosp.org.cn/docs/core/camera/camera3_3Amodes

[13] Horizon Robotics Developer Community, "Luminance control in imaging — AE oscillation root cause analysis," developer.horizon.auto.

[14] Qualcomm AEC9 Tuning Guide (public excerpt), "AEC9/AEC10 convergence parameter description," 2023. URL: https://xxzs.cn/archives/1537905

[15] ISP Tuning WeChat account, "Backlit scene AE handling: backlight compensation and ROI metering," nxrte.com.

---

*ISP Handbook — Part 4: System Engineering & IQA*
*Chapter 24: Auto Exposure Fundamentals*
