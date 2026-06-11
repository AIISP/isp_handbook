# Part 4, Chapter 01: 3A Control System — Traditional Algorithms and AI Collaboration

> **Pipeline position:** ISP-level controller coordinating three feedback loops: exposure, focus, and white balance
> **Prerequisites:** Chapter 01 (ISP Pipeline Overview), Chapter 03 (Sensor Physics), Chapter 22 (AWB)
> **Reader path:** System Designers, 3A Algorithm Engineers, ISP Tuning Engineers
> **Scope note:** This chapter covers the AWB **control layer** — gain injection timing, closed-loop convergence stability, and 3A coupling (AE/AF/AWB interaction). The AWB **algorithm layer** (Gray World / Bayesian / ML illuminant estimation principles) is fully covered in **Chapter 22**. Recommended reading order: Ch22 (algorithm) → Ch76 (control system).

---

## §1 Theory

### 1.1 3A System Architecture

Modern camera systems embed three tightly coupled feedback loops at the ISP controller level: Auto Exposure (AE), Auto Focus (AF), and Auto White Balance (AWB). Each loop consumes hardware statistics gathered from raw frames and writes actuator commands back into the sensor/lens/ISP pipeline.

```
Sensor RAW frame
       │
       ▼
┌─────────────┐   stats    ┌──────────────────────────────────────┐
│  ISP HW     │──────────►│  3A Controller                        │
│  Statistics │           │  ┌──────┐  ┌──────┐  ┌──────────┐   │
│  Engine     │           │  │  AE  │  │  AF  │  │   AWB    │   │
│  (BPS/IFE)  │           │  └──┬───┘  └──┬───┘  └────┬─────┘   │
└─────────────┘           │     │          │           │          │
                          └─────┼──────────┼───────────┼──────────┘
                                │          │           │
                    ┌───────────┴──┐  ┌────┴────┐  ┌──┴──────────┐
                    │ Sensor gain/ │  │  VCM    │  │  CCM / WB   │
                    │ shutter ctrl │  │  driver │  │  gains      │
                    └──────────────┘  └─────────┘  └─────────────┘
```

**Inter-loop coupling** creates mutual dependencies that must be resolved each frame:

| Coupling pair | Dependency direction | Resolution strategy |
|---|---|---|
| AE → AF | Luma level affects PDAF SNR | AF uses AE-stable flag before fine search |
| AE → AWB | Exposure changes scene color temperature | AWB waits for AE convergence before final gain |
| AF → AWB | Lens position shift alters color fringing | Minimal in practice; mitigated by lateral CA correction |
| AWB → AE | White balance gains alter apparent luma | AE operates on pre-WB raw channels; uses fixed G channel |

**Pipeline delay model.** Statistics collected on frame $N$ are processed by the 3A controller during frame $N+1$ readout, and the resulting parameters are applied to the sensor/ISP for frame $N+2$. This introduces a nominal 2-frame latency:

$$
\text{stat}(N) \xrightarrow{\text{algo}} \text{cmd}(N+1) \xrightarrow{\text{apply}} \text{effect}(N+2)
$$

For a 30 fps capture stream, the round-trip latency is approximately 66 ms. Predictive control is required for fast-moving scenes (see §1.5).

---

### 1.2 Auto Exposure (AE)

#### 1.2.1 Exposure Triangle

The photometric exposure $H$ (lux·s) captured by a pixel is governed by three controllable parameters:

$$
H = \frac{E \cdot t}{N^2}
$$

where $E$ is scene illuminance (lux), $t$ is shutter time (seconds), and $N$ is the aperture f-number. ISO gain $G$ amplifies the resulting signal after integration. The combined EV equation is:

$$
EV = \log_2\!\left(\frac{N^2}{t}\right) = \log_2\!\left(\frac{L \cdot S}{K}\right)
$$

where $L$ is scene luminance (cd/m²), $S$ is ISO arithmetic speed, and $K$ is a calibration constant (typically $K = 12.5$ for reflective metering). A 1-stop change in any single parameter doubles or halves exposure:

$$
\Delta EV = \log_2\!\left(\frac{t_1}{t_2}\right) = \log_2\!\left(\frac{G_2}{G_1}\right) = 2\log_2\!\left(\frac{N_1}{N_2}\right)
$$

#### 1.2.2 ISP Hardware Statistics

Modern ISP front-ends (Qualcomm BPS/IFE, MediaTek IPESYS, HiSilicon IFE) collect the following statistics in hardware before demosaicing:

- **Multi-zone luma histogram:** 16×16 = 256 zones, each accumulating a 256-bin histogram of the green channel. Total memory: 256 × 256 × 4 bytes ≈ 256 KB.
- **Saturation count per zone:** number of pixels above the saturation threshold (e.g., 95% of full well).
- **Global histogram:** 256 bins across the entire frame for overall luma distribution analysis.
- **AWB statistics:** per-zone R, Gr, Gb, B sums for white balance estimation.

#### 1.2.3 Exposure Target and Zone Weighting

The AE target is calibrated to 18% gray (middle gray), corresponding to $Y_{target} = 0.18$ in linear light, or approximately 118 in an 8-bit gamma-encoded output. The measured luma $Y_{meas}$ is a weighted average over zones:

$$
Y_{meas} = \frac{\sum_{i=1}^{256} w_i \cdot \bar{Y}_i}{\sum_{i=1}^{256} w_i}
$$

Zone weights $w_i$ are adapted per scene:

| Region | Default weight | Face detected | Sky region |
|---|---|---|---|
| Center zones | 1.0 | 1.0 | 1.0 |
| Face bounding box | 1.0 | 2.0–4.0 | — |
| Top-quarter sky | 1.0 | 1.0 | 0.3–0.5 |
| Edges | 0.5 | 0.5 | 0.3 |

#### 1.2.4 PI Controller

The AE convergence loop is a discrete-time PI controller operating in EV space:

$$
e_n = \log_2\!\left(\frac{Y_{target}}{Y_{meas,n}}\right)
$$

$$
\Delta EV_n = K_p \cdot e_n + K_i \cdot \sum_{k=0}^{n} e_k
$$

Typical tuning values: $K_p = 0.5$–$0.8$, $K_i = 0.05$–$0.15$. The integrator is clamped to prevent windup when the EV change is saturated at hardware limits. Fast-convergence mode (§1.5) temporarily raises $K_p$.

#### 1.2.5 SoC Vendor Implementations

**Qualcomm Spectra ISP.**
The Spectra ISP front-end (IFE stage) collects BPS statistics in hardware. The Hexagon NPU runs a scene classifier that identifies categories such as backlight, night, portrait, and action, and adjusts the AE zone weight map accordingly. Tuning parameters are stored in Chromatix binary blobs under the key `aec_algo_params`, which include exposure tables, metering mode weights, and convergence speed profiles per scene mode.

The CAMX (Camera Architecture) open-source framework exposes the AE node graph:
- Repository: https://github.com/quic/camx
- CHI-CDK (Camera Hardware Interface CDK): https://github.com/quic/chi-cdk

Within CAMX, the `CAECEngine` class manages the EV computation loop, interfacing with the `IFeatureAEC` plugin interface that third-party OEMs can override.

**MediaTek Imagiq ISP.**
MediaTek's Imagiq ISP (MT6895/MT6983 series) integrates an APU (AI Processing Unit) co-processor that runs a lightweight neural network for predictive AE. Rather than reacting purely to the previous frame's statistics, the APU estimates the next-frame luma based on motion vectors and scene context, reducing overshoot on fast scene transitions.

Anti-banding is enforced by constraining shutter time to integer multiples of the power-line period:
$$
t_{shutter} = \frac{n}{f_{PL}}, \quad n \in \mathbb{Z}^+
$$
where $f_{PL}$ = 50 Hz or 60 Hz (auto-detected via flicker frequency analysis on the luma histogram temporal derivative).

Technology overview: https://www.mediatek.com/technology/imagiq

**HiSilicon Kirin (ZHDR).**
HiSilicon's Kirin 9000 series implements ZHDR (Zero Latency HDR), a hardware feature that captures alternating long/short exposures on a row-by-row basis within a single frame readout. Each odd row uses the primary exposure $t_L$ while each even row uses $t_S = t_L / k$ (where $k$ is the HDR ratio, typically 4–16×). The ISP merges these two sub-images in real time with motion-adaptive blending.

The OpenHarmony Camera HAL exposes camera pipeline configuration for HiSilicon platforms:
- Repository: https://gitee.com/openharmony/drivers_peripheral_camera

#### 1.2.6 AI-Assisted AE

**Neural Auto-Exposure for HDR Object Detection.**
Onzon et al. (CVPR 2021, arXiv:2104.01906) propose a differentiable exposure layer that sits upstream of a detection network. The exposure parameter is optimized end-to-end by backpropagating the detection loss (mAP gradient) through the simulated tone mapping operator. On HDR-COCO scenes, this task-driven AE achieved +3–6% AP improvement over conventional luma-target AE. The key insight is that detection-optimal exposure differs from perceptual middle-gray: the network learns to slightly underexpose bright backgrounds to preserve foreground object contrast.

**Reinforcement Learning AE.**
AE can be formulated as a Markov Decision Process (MDP):
- State: current luma histogram, EV value, scene category embedding
- Action: discrete EV step from $\{-2, -1, -0.5, 0, +0.5, +1, +2\}$ stops
- Reward: $r = -|Y_{meas} - Y_{target}|$ (luma deviation) or detection AP delta

A DQN or PPO agent trained on diverse scene sequences learns to converge faster than a fixed PI controller on distribution-shifted scenes (e.g., tunnel entrance/exit, sports arenas with mixed lighting).

**Learning to See in the Dark.**
Chen et al. (CVPR 2018, arXiv:1805.01934) demonstrated that a U-Net trained on the Sony Imaging Dataset (SID) — pairs of short-exposure RAW and long-exposure reference RAW — can replace ISO amplification in extreme low light. At ISO 51200 and above, the learned amplification introduces significantly less chroma noise and color cast than analog gain, effectively extending the useful ISO range by 1–2 stops.

---

### 1.3 Auto Focus (AF)

#### 1.3.1 AF Methods Comparison

| Method | Principle | Speed | Low-light | Moving subject | Cost |
|---|---|---|---|---|---|
| CDAF (Contrast Detect) | Maximize sharpness metric over VCM scan | Slow (hill-climb) | Poor | Poor | Low |
| PDAF (Phase Detect) | Phase difference of dual-pixel sub-images | Fast (single frame) | Moderate | Good | Medium |
| ToF / Laser | Time-of-flight ranging | Very fast | Excellent | Excellent | High |
| Deep PDAF | CNN-enhanced phase signal | Fast | Good | Good | Medium+NPU |

#### 1.3.2 PDAF Principle

In dual-pixel PDAF, each photodiode is split into left (L) and right (R) sub-pixels masked to receive light from opposite sides of the aperture. For an out-of-focus scene point, the L and R sub-images are laterally shifted by a phase signal $\phi$:

$$
\phi = I_L \star I_R \big|_{\text{peak}} = \Delta x_{LR}
$$

The phase signal is linearly related to defocus:

$$
\Delta x_{LR} = \frac{f^2}{N \cdot d} \cdot \delta z
$$

where $f$ is focal length, $N$ is f-number, $d$ is the baseline between L/R sub-pixels, and $\delta z$ is the defocus distance. A factory-calibrated lookup table (`pd_to_lens_pos`) converts $\phi$ directly to VCM current steps, enabling single-shot focus without a search sweep.

#### 1.3.3 Major PDAF Sensor Implementations

**Samsung ISOCELL GN2 (2021):** Implements all-pixel PDAF across 100% of the 50 MP pixel array using Tetrapixel (2×2 binning) architecture. Each 1.4 µm sub-pixel has independent L/R masking. Phase confidence is estimated per-pixel, enabling reliable PDAF even in textured regions.

**Sony IMX989 (2022):** The 1-inch 50 MP sensor deploys Quad-Bayer + PDAF, with phase detection available in every 2×2 cell. The large pixel pitch (3.2 µm native) provides high phase SNR even in sub-lux illumination, supporting PDAF down to approximately EV1.

#### 1.3.4 AI-Assisted AF

Herrmann et al. (ECCV 2020) propose a CNN-based reliability gating network for robust autofocus. The network takes as input the PDAF phase map and the CDAF sharpness map and outputs a per-region reliability score $r \in [0,1]$. The final VCM command blends PDAF and CDAF estimates:

$$
\hat{z} = r \cdot \hat{z}_{PDAF} + (1 - r) \cdot \hat{z}_{CDAF}
$$

This gating reduces focus failures by approximately 15% on challenging scenes (specular reflections, repetitive patterns, low contrast) compared to PDAF-only or CDAF-only approaches.

#### 1.3.5 Kalman Filter for Moving Subjects

For continuous AF on moving subjects, a Kalman filter tracks the lens position trajectory:

$$
\text{State: } \mathbf{x}_k = [z_k,\; \dot{z}_k]^T
$$

$$
\mathbf{x}_{k|k-1} = \mathbf{F} \mathbf{x}_{k-1|k-1}, \quad \mathbf{F} = \begin{bmatrix} 1 & \Delta t \\ 0 & 1 \end{bmatrix}
$$

$$
\mathbf{x}_{k|k} = \mathbf{x}_{k|k-1} + \mathbf{K}_k (z_{meas,k} - \mathbf{H}\mathbf{x}_{k|k-1})
$$

The Kalman gain $\mathbf{K}_k$ balances prediction versus measurement trust. During high-confidence PDAF frames, the innovation covariance is low, increasing measurement weight; during occlusion or low-contrast frames, the predictor relies on the velocity estimate.

#### 1.3.6 AF Hard Cases

| Scenario | Root cause | Mitigation |
|---|---|---|
| Low light (< EV3) | Phase SNR collapses; CDAF hill unreliable | Increase AE exposure first; use laser AF assist |
| Low contrast / blank wall | No sharpness gradient; flat phase map | Search coarse scan; report "AF failed" |
| Moving subject | VCM latency; subject position changed by apply time | Kalman velocity predictor; predictive VCM pre-position |
| Glass / mirror | Specular reflection creates false phase peak | Reliability gating; fallback to CDAF on far plane |
| Repetitive pattern | Multiple false phase correlations | Phase peak disambiguation; use central ROI |
| Macro distance | Calibration LUT extrapolation error at short range | Dedicated macro LUT; manual override |

---

### 1.4 Auto White Balance (AWB)

#### 1.4.1 Gray World Algorithm

The Gray World assumption states that the scene-average color is achromatic. Under this assumption, per-channel correction gains are:

$$
W_R = \frac{\bar{G}}{\bar{R}}, \quad W_B = \frac{\bar{G}}{\bar{B}}
$$

In practice, only "gray candidate" pixels are averaged — pixels satisfying:

$$
\left|\frac{R - G}{R + G + B}\right| < \tau_R \quad \text{and} \quad \left|\frac{B - G}{R + G + B}\right| < \tau_B
$$

where $\tau_R, \tau_B \approx 0.1$–$0.2$. Saturated pixels and pixels on the Planckian Locus boundary are excluded.

#### 1.4.2 Planckian Locus

For a blackbody radiator at color temperature $T$ (Kelvin), the chromaticity traces a curve in $(R/G, B/G)$ space called the Planckian Locus. The curve runs from warm (low CCT, high $R/G$, low $B/G$) to cool (high CCT, low $R/G$, high $B/G$):

| CCT (K) | Illuminant | Approx. $R/G$ | Approx. $B/G$ |
|---|---|---|---|
| 2800 | Tungsten | 1.6–1.8 | 0.5–0.6 |
| 4000 | Warm fluorescent | 1.2–1.4 | 0.7–0.8 |
| 5500 | Daylight D55 | 0.9–1.0 | 0.9–1.0 |
| 6500 | D65 | 0.85–0.90 | 1.0–1.1 |
| 9000 | Shade | 0.7–0.8 | 1.2–1.4 |

AWB estimation projects the scene chromaticity onto the nearest Locus point and interpolates between calibrated illuminant nodes to obtain the final correction gains.

#### 1.4.3 FFCC (Fast Fourier Color Constancy)

Barron & Tsai (CVPR 2017) reformulate color constancy as a classification problem over a quantized $(u, v)$ log-chromaticity histogram, where $u = \log(R/G)$, $v = \log(B/G)$. The classifier is a linear model whose weights are applied as a convolution in the histogram domain. By computing this convolution via FFT, the entire illuminant estimation runs in approximately 5 ms on a mobile CPU — fast enough for per-frame AWB without dedicated hardware.

FFCC was deployed in Google Pixel 1 through Pixel 4 cameras. The paper and supplementary are available at:
https://openaccess.thecvf.com/content_cvpr_2017/papers/Barron_Fast_Fourier_Color_CVPR_2017_paper.pdf

The log-chromaticity histogram $H(u, v)$ is computed as:

$$
H(u, v) = \sum_{p \in \mathcal{P}} \delta\!\left(u - \log\frac{R_p}{G_p}\right) \delta\!\left(v - \log\frac{B_p}{G_p}\right)
$$

The illuminant estimate $(u^*, v^*)$ is:

$$
(u^*, v^*) = \arg\max_{(u,v)} \left( H \star W \right)(u, v)
$$

where $W$ is the learned weight kernel. The FFT convolution theorem gives:

$$
H \star W = \mathcal{F}^{-1}\!\left[\mathcal{F}[H] \cdot \overline{\mathcal{F}[W]}\right]
$$

#### 1.4.4 Deep White-Balance Editing

Afifi & Brown (CVPR 2020, arXiv:2003.12704) address the common case where an image has been rendered with a wrong white balance. Their network learns a set of 3D color lookup tables (LUTs), one per target illuminant category, and interpolates among them based on the input image's estimated illuminant. This allows post-capture AWB correction on processed (non-RAW) images, which is not possible with simple gain multiplication.

#### 1.4.5 AWB Hard Cases

| Scenario | Root cause | Mitigation |
|---|---|---|
| Mixed illuminants | Multiple light sources with different CCTs | Spatial illuminant segmentation; per-region gains |
| Neon / LED signs | Highly saturated non-Planckian chromaticity | Saturated pixel exclusion; chroma-constrained estimation |
| Golden hour | CCT ~2000 K, outside typical Locus table range | Extended Locus table; semantic sky mask to exclude |
| Underwater | Blue-green cast dominant; no neutral reference | Scene detection → fixed underwater preset |
| Green screen | Large green surface biases gray world heavily | Color-uniform region exclusion; foreground masking |
| Candlelight | Very low CCT, small and flickering source | Illuminant stability filter; fallback to prior estimate |
| Flash + ambient | Dual illuminant in near/far zones | Flash zone masking; background-only AWB estimation |

---

### 1.5 3A Co-scheduling and Frame Delay Model

#### 1.5.1 Pipeline Delay Diagram

```
Frame:        N-1          N           N+1          N+2
              ─────────────────────────────────────────────►  time
Sensor:    [readout]   [readout]   [readout]   [readout]
              │           │
              │      stats(N-1)
              │           │
              │           ▼
ISP HW:              [IFE stats]
                          │
                          ▼
3A algo:             [process stats(N-1)]
                          │  cmd(N)
                          ▼
Sensor reg:               [apply cmd(N)]
                                          │
                                          ▼
Effect:                              [visible in N+2]
```

#### 1.5.2 Predictive AE for Scene Transitions

On abrupt scene transitions (e.g., tunnel entrance/exit), waiting 2 frames for the feedback loop to measure the new luma causes transient over/underexposure. Predictive AE uses a scene-change detector:

$$
\Delta H_{hist} = \text{KL}\!\left(P_{hist,N} \,\|\, P_{hist,N-1}\right) > \theta_{scene}
$$

When a scene change is detected, the controller immediately applies a feed-forward step based on the histogram mode shift, bypassing the normal integrator. The integrator state is also reset to prevent accumulated error from the previous scene.

#### 1.5.3 Gain Scheduling (Fast vs. Stable Mode)

The PI controller operates in two modes depending on the current error magnitude:

$$
K_p = \begin{cases} 1.0 & |\Delta EV| > 2.0 \text{ stops (fast convergence)} \\ 0.5 & |\Delta EV| \leq 0.5 \text{ stops (stable)} \\ 0.75 & \text{otherwise (transition)} \end{cases}
$$

The integrator is enabled only in stable mode to avoid overshoot during fast convergence. Transition between modes uses hysteresis to prevent chattering.

---

## §2 Calibration

### 2.1 AE Calibration

**CRF Linearity Validation.** The Camera Response Function (CRF) maps scene radiance to pixel values. AE algorithms assume a linear relationship between exposure and luma in RAW space. Validation is performed by capturing a flat-field scene (integrating sphere or uniform illuminator) at multiple known exposure steps (e.g., 0.5 EV increments from EV4 to EV12) and verifying that the measured RAW luma doubles per stop:

$$
\text{Linearity error} = \left|\frac{Y_{EV+1}}{Y_{EV}} - 2.0\right| \times 100\%
$$

Acceptable linearity error is typically less than 2%.

**Convergence Speed Test.** A step-change target is presented (e.g., LED panel switched from 100 lux to 10,000 lux). The number of frames to reach within 10% of the new target luma is recorded. Typical specifications: fewer than 10 frames at 30 fps.

**DXOMARK Lux-Level Accuracy.** Exposure accuracy is validated at standard lux levels (1, 10, 100, 1000, 10,000 lux) on an 18% gray card. The DXOMARK methodology measures exposure error in EV (ΔEV) relative to the photometric reference. Acceptable ΔEV < 0.3 at all lux levels.

### 2.2 AF Calibration

**PDAF Phase Offset Calibration.** The `pd_to_lens_pos` lookup table maps phase signal $\phi$ to VCM current steps. It is built at the factory using a multi-step procedure:

1. Mount the module on a collimator bench at known object distances ($d_1, d_2, \ldots, d_k$).
2. For each distance, move the VCM to the best-focus position (verified by CDAF peak).
3. Record the phase signal $\phi_i$ at the best-focus VCM position.
4. Fit a polynomial $\text{VCM}(\phi) = a_0 + a_1 \phi + a_2 \phi^2$ to the $(phi_i, \text{VCM}_i)$ pairs.

**Hall Sensor Linearity.** Closed-loop VCM drivers use a Hall sensor to measure lens position. Linearity is verified across the full travel range by applying known current steps and measuring Hall output. Non-linearity above 1% triggers a compensation LUT.

**Temperature Drift Compensation.** VCM actuator stiffness and Hall sensor offset vary with temperature (typically –30°C to +85°C for automotive). A temperature coefficient table is stored in OTP and applied at runtime:

$$
\text{VCM}_{comp}(T) = \text{VCM}_{cal} + \alpha \cdot (T - T_{cal})
$$

### 2.3 AWB Calibration

**Planckian Locus Capture.** A ColorChecker chart is illuminated at multiple CCTs (2856 K / CIE A, 4150 K / CWF, 6504 K / D65, and additional 3200 K and 5000 K points). For each illuminant, the neutral patches (rows 4 of the ColorChecker) are averaged to establish the $(R/G, B/G)$ coordinates of that illuminant. These points define the calibrated Locus in the device-specific color space.

**Joint CCM and AWB Optimization.** The Color Correction Matrix (CCM) and AWB gains interact: applying AWB gains before the CCM modifies the effective CCM. The joint optimization minimizes the total color error $\Delta E_{00}$ across all ColorChecker patches simultaneously:

$$
\min_{W_R, W_B, \mathbf{M}_{ccm}} \sum_{p=1}^{24} \Delta E_{00}\!\left(\mathbf{M}_{ccm} \begin{bmatrix} W_R R_p \\ G_p \\ W_B B_p \end{bmatrix},\; \text{Lab}_{ref,p}\right)
$$

Typically solved with Levenberg-Marquardt over a 9-dimensional parameter space ($W_R, W_B$ + 9 CCM coefficients minus 3 normalization constraints).

---

## §3 Tuning

### 3.1 AE Tuning

**Zone Weight Maps per Scene Mode.** Different capture modes require different weight maps:

| Scene mode | Priority weighting |
|---|---|
| Portrait | Face zones: 3×; background: 0.5× |
| Landscape | Top (sky): 0.3×; center: 1.0×; bottom (ground): 0.8× |
| Spot metering | Single center zone: 10×; all others: 0.0× |
| Sports / action | Motion-region adaptive: tracked subject zone: 2× |
| Night | Clipping tolerance loosened; center-weighted |

**Clipping Tolerance.** The maximum allowable saturation ratio before reducing exposure:

$$
\text{clip\_tolerance} = \frac{\text{saturated pixels}}{\text{total pixels}} < \tau_{clip}
$$

Typical $\tau_{clip}$ = 1–5% for standard photography, relaxed to 10% for HDR capture modes.

**Convergence Speed per Mode.** Video recording requires slower convergence ($K_p$ = 0.2–0.3) to prevent visible exposure jumps between frames. Still capture can use aggressive convergence ($K_p$ = 0.8–1.0) during the preview-to-capture transition.

### 3.2 AF Tuning

**Contrast Operator Selection.** Multiple sharpness metrics are available for CDAF:

| Operator | Formula | Characteristics |
|---|---|---|
| Laplacian | $\nabla^2 I = I_{xx} + I_{yy}$ | Sensitive to noise; good for high-frequency targets |
| Tenengrad | $\sqrt{G_x^2 + G_y^2}$ | Robust; standard choice |
| Variance | $\sigma^2(I)$ | Simple; low discrimination for smooth textures |
| Brenner | $\sum (I(x+2,y) - I(x,y))^2$ | Fast; good for periodic targets |

**PDAF Sensitivity Threshold.** The minimum phase SNR required to trust the PDAF estimate. Set too low: false convergence on noise. Set too high: excessive fallback to CDAF and slow AF speed.

**Search Range.** The VCM scan range for CDAF hill-climbing. Wider range finds more distant subjects but increases AF time. The range is split into coarse scan (large steps) and fine scan (small steps near the coarse peak).

### 3.3 AWB Tuning

**Gray Polygon Width vs. Accuracy Trade-off.** The gray polygon defines the chromaticity region accepted as "possible illuminant." A wider polygon accepts more pixels (more averaging, lower variance) but risks including colored objects as gray candidates. A narrow polygon is precise but can fail in low-texture scenes.

**CCT Constraint Range.** Production cameras typically constrain the estimated CCT to [2500 K, 10000 K] to prevent runaway AWB under exotic illuminants. The constraint is implemented as a soft clamp on the Locus projection distance.

---

## §4 Artifacts

### 4.1 AE Flicker and Banding

Fluorescent and LED lighting flickers at twice the power-line frequency ($f_{PL}$): 100 Hz at 50 Hz mains, 120 Hz at 60 Hz mains. When the shutter time is not a multiple of $1/(2 f_{PL})$, the captured frame integrates a non-integer number of flicker cycles, creating horizontal banding.

**Anti-banding constraint:**

$$
t_{shutter} \in \left\{\frac{n}{2 f_{PL}}\right\}_{n=1,2,3,\ldots}
$$

At 50 Hz, valid shutter times include 1/100s, 1/200s, 1/400s, 1/800s, etc. The AE controller selects the nearest allowed shutter time to the unconstrained optimum, accepting up to ±0.5 EV penalty.

Auto-detection of $f_{PL}$: the temporal derivative of the global luma histogram is analyzed for peaks at 100 Hz or 120 Hz using a short-time DFT over 16–32 consecutive frames.

### 4.2 AWB Hunting

AWB hunting occurs when the controller oscillates between two gain estimates, visible as a color shift every few frames. This typically occurs under mixed illuminants where the gray pixel selection alternates between two illuminant candidates.

**Temporal smoothing:**

$$
W_{n+1} = \alpha \cdot W_n + (1 - \alpha) \cdot W_{target,n}
$$

with $\alpha \approx 0.85$–$0.95$ for video mode. This exponential moving average smooths gain transitions. For still capture, $\alpha$ is reduced to 0.3–0.5 to allow rapid convergence before the shutter fires.

Additionally, a scene-change detector (based on luma or chromaticity histogram KL-divergence) can reset the smoother state when a genuine illuminant change is detected, preventing lag after walking into a differently lit room.

### 4.3 AF Hunting in Video

In video mode, continuous AF with standard PDAF sensitivity leads to perceptible focus "breathing" — small lens oscillations around the best-focus position as the controller corrects phase noise. Mitigation strategies:

- **Nudge strategy:** apply VCM commands only when phase error exceeds a dead-band threshold $|\phi| > \phi_{dead}$. Typical $\phi_{dead}$ = 5–10% of full-range phase.
- **Reduced video AF sensitivity:** lower the phase-to-VCM gain by 50–70% compared to still mode.
- **Temporal phase filtering:** average the phase estimate over 3–5 frames before commanding the VCM, trading tracking speed for stability.

---

## §5 Evaluation

### 5.1 Metrics Table

| Metric | Definition | Target specification |
|---|---|---|
| AE accuracy ΔEV | $|\log_2(Y_{meas}/Y_{target})|$ at steady state | < 0.3 EV at all lux levels |
| AE convergence | Frames to reach within 10% of target luma | < 10 frames at 30 fps |
| AF speed (still) | Time from half-press to focus lock (seconds) | < 0.3 s (bright); < 0.8 s (dim) |
| AF PDAF linearity $R^2$ | Correlation of phase signal vs. true defocus | > 0.995 |
| AF accuracy | Focus error at capture (cm at 1 m) | < 2 cm for portrait |
| AWB $\Delta E_{00}$ | CIEDE2000 error on neutral patches | < 3.0 $\Delta E_{00}$ |
| AWB consistency | Max $\Delta E_{00}$ variation across illuminants | < 1.5 $\Delta E_{00}$ |

### 5.2 Test Scenes

- **AE lux sweep:** 1 lux (candlelight) to 100,000 lux (direct sunlight), logarithmic 0.5-stop steps.
- **AF distance sweep:** 10 cm (macro) to infinity, standard targets (Siemens star, ISO 12233 chart).
- **AWB illuminant matrix:** CIE A (2856 K), CWF (4150 K), TL84 (4000 K), D65 (6504 K), D75 (7504 K), shade.
- **3A interaction test:** abrupt scene transition (dark room to bright window), face entry/exit.

---

## §6 Code

Companion notebook: *See §6 Code section for runnable examples.*

### 6.1 AE PI Controller Simulation

```python
import numpy as np
import matplotlib.pyplot as plt

def simulate_ae_pi(scene_luma_sequence, y_target=0.18,
                   kp=0.6, ki=0.08, ev_min=-2, ev_max=10):
    """
    Simulate AE PI controller over a sequence of scene luma values.

    Parameters
    ----------
    scene_luma_sequence : array-like
        Ground-truth scene luma at each frame (linear, 0-1 scale).
    y_target : float
        Target luma (18% gray = 0.18 linear).
    kp, ki : float
        Proportional and integral gains.
    ev_min, ev_max : float
        EV clamping range.

    Returns
    -------
    ev_history : np.ndarray
        Applied EV at each frame.
    luma_history : np.ndarray
        Measured luma at each frame.
    """
    n_frames = len(scene_luma_sequence)
    ev = 0.0          # initial EV (relative, 0 = middle gray)
    integrator = 0.0
    ev_history = np.zeros(n_frames)
    luma_history = np.zeros(n_frames)

    # Pipeline delay buffer (2-frame delay)
    ev_buffer = [0.0, 0.0]

    for i, scene_luma in enumerate(scene_luma_sequence):
        # Apply EV from 2 frames ago (pipeline delay)
        ev_applied = ev_buffer[0]
        ev_buffer.pop(0)

        # Measured luma: scene_luma * 2^(ev_applied)
        # Clamp to [0, 1] to simulate sensor saturation
        measured = np.clip(scene_luma * (2.0 ** ev_applied), 0.0, 1.0)
        luma_history[i] = measured

        # Error in EV space
        if measured > 0:
            error = np.log2(y_target / measured)
        else:
            error = 4.0  # max correction on black frame

        # Fast-convergence gain scheduling
        kp_eff = 1.0 if abs(error) > 2.0 else (0.5 if abs(error) < 0.5 else kp)

        # PI update
        integrator += ki * error
        integrator = np.clip(integrator, -3.0, 3.0)  # anti-windup
        delta_ev = kp_eff * error + integrator

        # Update EV with clamping
        ev = np.clip(ev + delta_ev, ev_min, ev_max)
        ev_history[i] = ev

        # Push new EV into delay buffer
        ev_buffer.append(ev)

    return ev_history, luma_history


# Example: step scene change from luma=0.01 (dark) to luma=0.5 (bright)
scene = np.concatenate([np.full(30, 0.01), np.full(60, 0.5)])
ev_hist, luma_hist = simulate_ae_pi(scene)

fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
axes[0].plot(luma_hist, label='Measured luma')
axes[0].axhline(0.18, color='r', linestyle='--', label='Target (18% gray)')
axes[0].set_ylabel('Luma (linear)')
axes[0].legend()
axes[0].set_title('AE PI Controller — Step Scene Change')
axes[1].plot(ev_hist, label='Applied EV', color='orange')
axes[1].set_ylabel('EV (relative)')
axes[1].set_xlabel('Frame index')
axes[1].legend()
plt.tight_layout()
plt.savefig('ae_pi_simulation.png', dpi=150)
plt.show()
```

### 6.2 Planckian Locus Visualization

```python
import numpy as np
import matplotlib.pyplot as plt
from colour import xy_to_CCT, CCT_to_xy_Kang2002

# Compute Planckian Locus in CIE xy space, then convert to (R/G, B/G)
# using a simplified D65-normalized sRGB primaries matrix.
# Note: exact (R/G, B/G) values depend on the sensor spectral response.

def planckian_locus_xy(cct_range):
    """Return CIE xy coordinates along Planckian Locus."""
    xy_list = []
    for cct in cct_range:
        xy = CCT_to_xy_Kang2002(cct)
        xy_list.append(xy)
    return np.array(xy_list)

def xy_to_rg_bg(xy_array, M_xyz_to_rgb=None):
    """
    Convert CIE xy to (R/G, B/G) using XYZ->linear-sRGB matrix.
    Assume Y=1 (normalize to equal-energy white).
    """
    if M_xyz_to_rgb is None:
        # sRGB D65 inverse matrix (XYZ -> linear RGB)
        M_xyz_to_rgb = np.array([
            [ 3.2406, -1.5372, -0.4986],
            [-0.9689,  1.8758,  0.0415],
            [ 0.0557, -0.2040,  1.0570]
        ])
    rg_bg = []
    for xy in xy_array:
        x, y = xy
        # Convert to XYZ (Y=1)
        X = x / y
        Y = 1.0
        Z = (1 - x - y) / y
        xyz = np.array([X, Y, Z])
        rgb = M_xyz_to_rgb @ xyz
        rgb = np.clip(rgb, 1e-6, None)
        rg_bg.append((rgb[0] / rgb[1], rgb[2] / rgb[1]))
    return np.array(rg_bg)

cct_range = np.arange(2500, 10001, 100)
xy_locus = planckian_locus_xy(cct_range)
rg_bg_locus = xy_to_rg_bg(xy_locus)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Left: CIE xy
axes[0].plot(xy_locus[:, 0], xy_locus[:, 1], 'b-', linewidth=2)
for cct, xy in zip(cct_range[::10], xy_locus[::10]):
    axes[0].annotate(f'{cct}K', xy, fontsize=7, color='gray')
axes[0].set_xlabel('CIE x')
axes[0].set_ylabel('CIE y')
axes[0].set_title('Planckian Locus — CIE xy')
axes[0].grid(True, alpha=0.3)

# Right: (R/G, B/G) sensor space
axes[1].plot(rg_bg_locus[:, 0], rg_bg_locus[:, 1], 'r-', linewidth=2)
for cct, rg_bg in zip(cct_range[::10], rg_bg_locus[::10]):
    axes[1].annotate(f'{cct}K', rg_bg, fontsize=7, color='gray')
axes[1].set_xlabel('R/G')
axes[1].set_ylabel('B/G')
axes[1].set_title('Planckian Locus — Sensor (R/G, B/G) space')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('planckian_locus.png', dpi=150)
plt.show()
```

### 6.3 Simplified FFCC AWB via FFT-Domain Histogram

```python
import numpy as np
from scipy.ndimage import gaussian_filter

def compute_log_chroma_histogram(image_rgb, bins=64, log_range=(-2.5, 2.5)):
    """
    Compute 2D log-chromaticity histogram H(u, v) where
    u = log(R/G), v = log(B/G).

    Parameters
    ----------
    image_rgb : np.ndarray, shape (H, W, 3), dtype float32, range [0,1]
    bins : int
        Number of histogram bins per axis.
    log_range : tuple
        (min, max) of log-chromaticity range.

    Returns
    -------
    hist : np.ndarray, shape (bins, bins)
    edges : tuple of (u_edges, v_edges)
    """
    R, G, B = image_rgb[..., 0], image_rgb[..., 1], image_rgb[..., 2]
    eps = 1e-6
    # Only use pixels where G > threshold (avoid noise in dark pixels)
    valid = G > 0.02
    u = np.log(R[valid] / (G[valid] + eps) + eps)
    v = np.log(B[valid] / (G[valid] + eps) + eps)

    hist, u_edges, v_edges = np.histogram2d(
        u, v, bins=bins,
        range=[log_range, log_range]
    )
    return hist.astype(np.float32), (u_edges, v_edges)


def ffcc_estimate_illuminant(image_rgb, weight_kernel=None,
                              bins=64, log_range=(-2.5, 2.5)):
    """
    Estimate illuminant gains (W_R, W_B) using FFCC-style
    FFT-domain histogram convolution.

    Parameters
    ----------
    image_rgb : np.ndarray, shape (H, W, 3), float32 [0,1]
    weight_kernel : np.ndarray or None
        Pre-trained weight kernel of shape (bins, bins).
        If None, use a Gaussian centered at (0,0) as a placeholder
        (equivalent to Gray World assumption).

    Returns
    -------
    W_R, W_B : float
        Per-channel gain estimates (multiply R and B to neutralize).
    """
    hist, (u_edges, v_edges) = compute_log_chroma_histogram(
        image_rgb, bins=bins, log_range=log_range
    )

    if weight_kernel is None:
        # Placeholder: Gaussian kernel centered at origin (Gray World)
        kernel = np.zeros((bins, bins), dtype=np.float32)
        cy, cx = bins // 2, bins // 2
        weight_kernel = gaussian_filter(
            np.eye(bins, bins) * 0 + (np.arange(bins) == cy)[:, None],
            sigma=3.0
        )
        weight_kernel = gaussian_filter(weight_kernel, sigma=3.0)
        weight_kernel /= weight_kernel.sum()

    # FFT-domain convolution
    H_fft = np.fft.fft2(hist)
    W_fft = np.fft.fft2(weight_kernel)
    response = np.fft.ifft2(H_fft * np.conj(W_fft)).real

    # Find peak
    peak_idx = np.unravel_index(np.argmax(response), response.shape)
    u_est = u_edges[peak_idx[0]] + (u_edges[1] - u_edges[0]) / 2
    v_est = v_edges[peak_idx[1]] + (v_edges[1] - v_edges[0]) / 2

    # Convert log-chromaticity to gains
    # u* = log(R_ill/G_ill) -> W_R = exp(-u*) to neutralize
    W_R = np.exp(-u_est)
    W_B = np.exp(-v_est)

    return W_R, W_B


# Demo on a synthetic image with tungsten-like cast (high R, low B)
np.random.seed(42)
H, W = 480, 640
synthetic = np.random.rand(H, W, 3).astype(np.float32)
# Simulate tungsten illuminant: R gain 1.6, B gain 0.6
synthetic[..., 0] = np.clip(synthetic[..., 0] * 1.6, 0, 1)
synthetic[..., 2] = np.clip(synthetic[..., 2] * 0.6, 0, 1)

W_R, W_B = ffcc_estimate_illuminant(synthetic)
print(f"Estimated W_R = {W_R:.3f}, W_B = {W_B:.3f}")
print(f"Expected approx W_R ≈ {1/1.6:.3f}, W_B ≈ {1/0.6:.3f}")
```

### 6.4 PDAF Phase Signal Simulation and VCM Step Prediction

```python
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import correlate

def simulate_pdaf_phase(defocus_um, f_mm=5.0, fnum=1.8,
                        baseline_um=1.4, pixel_pitch_um=0.8):
    """
    Simulate PDAF phase signal (pixel shift) for a given defocus.

    Parameters
    ----------
    defocus_um : float or array
        Defocus distance in micrometers (positive = front focus).
    f_mm : float
        Focal length in mm.
    fnum : float
        Aperture f-number.
    baseline_um : float
        Baseline between L/R sub-pixel centers in micrometers.
    pixel_pitch_um : float
        Pixel pitch in micrometers.

    Returns
    -------
    phase_pixels : float or array
        Phase signal in pixels (L-R sub-image shift).
    """
    f_um = f_mm * 1000.0  # focal length in um
    # Phase shift formula: delta_x = baseline * defocus / (f * fnum * 2)
    # Simplified thin-lens approximation
    phase_um = (baseline_um / (2.0 * fnum)) * (defocus_um / f_um) * f_um
    phase_pixels = phase_um / pixel_pitch_um
    return phase_pixels


def phase_to_vcm_steps(phase_pixels, pd_to_vcm_slope=15.0, vcm_offset=512):
    """
    Convert phase signal to VCM DAC step using linear calibration.

    Parameters
    ----------
    phase_pixels : float or array
        Phase signal in pixels.
    pd_to_vcm_slope : float
        Calibrated slope (VCM steps per pixel of phase).
    vcm_offset : int
        VCM position at infinity focus.

    Returns
    -------
    vcm_steps : int or array
        Target VCM DAC value.
    """
    return (vcm_offset + pd_to_vcm_slope * phase_pixels).astype(int)


# Simulate over a range of defocus values
defocus_range = np.linspace(-500, 500, 200)  # ±500 um defocus
phase_signal = simulate_pdaf_phase(defocus_range)
vcm_commands = phase_to_vcm_steps(phase_signal)

fig, axes = plt.subplots(1, 2, figsize=(12, 4))

axes[0].plot(defocus_range, phase_signal)
axes[0].axhline(0, color='k', linestyle='--', linewidth=0.8)
axes[0].axvline(0, color='k', linestyle='--', linewidth=0.8)
axes[0].set_xlabel('Defocus (µm)')
axes[0].set_ylabel('Phase signal (pixels)')
axes[0].set_title('PDAF Phase Signal vs. Defocus')
axes[0].grid(True, alpha=0.3)

axes[1].plot(defocus_range, vcm_commands)
axes[1].set_xlabel('Defocus (µm)')
axes[1].set_ylabel('VCM DAC steps')
axes[1].set_title('VCM Command via pd_to_lens_pos LUT')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('pdaf_phase_vcm.png', dpi=150)
plt.show()

# Verify linearity
r2 = np.corrcoef(defocus_range, vcm_commands)[0, 1] ** 2
print(f"PDAF linearity R² = {r2:.6f}")
```

---

## References

1. Barron, J. T., & Tsai, Y. T. (2017). Fast Fourier color constancy. *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)*. https://openaccess.thecvf.com/content_cvpr_2017/papers/Barron_Fast_Fourier_Color_CVPR_2017_paper.pdf

2. Onzon, E., Rameau, F., & Jeong, J. (2021). Neural auto-exposure for high-dynamic range object detection. *CVPR 2021*. arXiv:2104.01906. https://arxiv.org/abs/2104.01906

3. Chen, C., Chen, Q., Xu, J., & Koltun, V. (2018). Learning to see in the dark. *CVPR 2018*. arXiv:1805.01934. https://arxiv.org/abs/1805.01934

4. Afifi, M., & Brown, M. S. (2020). Deep white-balance editing. *CVPR 2020*. arXiv:2003.12704. https://arxiv.org/abs/2003.12704

5. Herrmann, C., Bowen, R. S., & Zabih, R. (2020). Robust autofocus. *ECCV 2020*. https://link.springer.com/chapter/10.1007/978-3-030-58604-1_29

6. Qualcomm CAMX (Camera Architecture). Open-source ISP/camera pipeline framework. https://github.com/quic/camx

7. Qualcomm CHI-CDK (Camera Hardware Interface CDK). https://github.com/quic/chi-cdk

8. MediaTek Imagiq ISP Technology. https://www.mediatek.com/technology/imagiq

9. OpenHarmony Camera HAL (HiSilicon/Kirin platform camera driver). https://gitee.com/openharmony/drivers_peripheral_camera

10. Android Camera HAL3 Interface Specification. https://source.android.com/docs/core/camera

11. Samsung ISOCELL GN2 Product Page. https://semiconductor.samsung.com/us/consumer-storage/internal-ssd/

12. Sony IMX989 Sensor Announcement. Sony Semiconductor Solutions press release, 2022.

13. ITU-R BT.2408 (2017). Operational Practices in HDR Television Production.

14. ISO 15739:2013. Photography — Electronic still-picture imaging — Noise measurements.

15. DXOMARK Protocol — Mobile category: AE accuracy and convergence methodology. https://www.dxomark.com/dxomark-camera-test-protocol-explained/

---

*End of Chapter 23*
