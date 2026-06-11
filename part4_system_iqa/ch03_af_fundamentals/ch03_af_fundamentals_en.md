# Part 4, Chapter 03: Auto Focus Fundamentals (自动对焦算法)

> **Pipeline position:** AF drives the lens motor to match the image plane to the target distance.
> **Prerequisites:** Chapter 02 (Optics Basics), Chapter 08 (Aberrations & Lens Characterization)
> **Reader path:** 3A algorithm engineers, optical engineers

---

## §1 Theory

### 1.1 Focusing Principles

**Thin Lens Equation (薄透镜成像公式)**

$$\frac{1}{f} = \frac{1}{d_o} + \frac{1}{d_i}$$

where:
- $f$: focal length (焦距)
- $d_o$: object distance (物距) — lens to subject
- $d_i$: image distance (像距) — lens to image sensor

When the object distance changes, the lens must be moved (changing $d_i$) so that the image falls sharply on the sensor plane.

**Circle of Confusion (弥散圆, CoC)**

When the image plane is displaced from the correct position, a point source produces a disc rather than a point — the Circle of Confusion. Its diameter $c$ satisfies:

$$c = \frac{F \cdot |d_i - d_i'|}{d_i'}$$

where $F$ is the aperture diameter (focal length / f-number), $d_i'$ is the actual image distance, and $d_i$ is the sensor-plane-to-lens distance.

The permissible CoC diameter $d$ is typically sensor diagonal / 1500 to 1/1000 (depending on output resolution). When $c > d$, blur is visually detectable.

**Depth of Field (景深, DOF)**

DOF consists of a near (front) and a far (back) zone; the total DOF is:

$$\text{DOF} = \frac{2 \cdot F^2 \cdot N \cdot d \cdot f_s^2}{F^4 - N^2 \cdot d^2 \cdot f_s^2}$$

Simplified (far-field approximation, $f_s \gg F$):

$$\text{DOF} \approx \frac{2 \cdot N \cdot d \cdot f_s^2}{F^2}$$

where:
- $d$: permissible CoC diameter (mm)
- $F$: focal length (mm)
- $N$: f-number (e.g., f/1.8 → $N=1.8$)
- $f_s$: focus distance (m)

Key relationships:
- Larger aperture (smaller $N$) → shallower DOF
- Longer focal length → shallower DOF
- Greater focus distance → deeper DOF

---

### 1.2 CDAF (Contrast Detection Auto Focus, 对比度检测自动对焦)

**Basic Principle**

CDAF analyzes local image contrast to assess focus quality. A sharp image has strong high-frequency content (edges); a blurred image has weak high-frequency content. The search process is a hill-climbing (爬山) algorithm: move the lens, record the contrast value at each position, and find the maximum.

**Common Contrast Operators**

| Operator | Formula | Characteristics |
|----------|---------|-----------------|
| Laplacian | $\sum \|I_{xx}+I_{yy}\|$ | Noise-sensitive, fast response |
| Tenengrad | $\sum(\nabla I_x^2 + \nabla I_y^2)$ | Robust, direction-independent |
| Variance | $\text{Var}(I) = E[I^2] - (E[I])^2$ | Simple; ineffective on uniform regions |
| SML (Sum of Modified Laplacian, 修正Laplacian之和) | $\sum \|2I_{x,y} - I_{x-1,y} - I_{x+1,y}\| + \sum \|2I_{x,y} - I_{x,y-1} - I_{x,y+1}\|$ | Good noise resistance |

**Search Strategies**

- **Full Scan (全程搜索):** Sweep from near to far end, find global maximum. Highest accuracy but slowest (typically 30–50 steps, 300ms–1s).
- **Binary Search (二分搜索):** Halve the search range; assumes a unimodal contrast curve. Can fail in multi-target or mixed near/far scenes.
- **Fibonacci Search (斐波那契搜索):** Faster convergence than binary search for unimodal distributions. Steps required: approximately $\lceil \log_\phi(n) \rceil$ where $\phi \approx 1.618$.
- **Nudge Strategy (轻推):** Small probe steps around the current position, used for video AF micro-adjustment tracking. Motor moves only if the contrast difference exceeds a threshold.

**Applicable Scenes and Limitations**

- Suited for: stationary subjects, adequate lighting (SNR > 20dB), rich texture
- Limitations: moving subjects cause search errors; low-light noise corrupts the contrast curve; requires multiple frames (high latency)

---

### 1.3 PDAF (Phase Detection Auto Focus, 相位检测自动对焦)

**Dual-Pixel (双像素) Principle**

PDAF sensors split each pixel into left and right (or top and bottom) sub-pixels that receive light passing through the left and right halves of the lens, respectively.

- **Front focus (前焦, Near Focus):** Left sub-pixel image shifted right, right sub-pixel image shifted left → positive phase difference
- **Back focus (后焦, Far Focus):** Left sub-pixel image shifted left, right sub-pixel image shifted right → negative phase difference
- **In focus (合焦):** Both views aligned; phase difference is zero

The phase difference directly indicates both the amount and direction of defocus. No scanning is required — measurement is single-frame.

**Phase Shift to VCM Step Mapping**

$$\Delta\text{step} = k \cdot \text{phase\_shift} + b$$

Sensitivity $k$ and offset $b$ are determined by factory calibration (see §2).

**Depth Estimation**

$$\text{Depth} = \frac{B \cdot F}{D}$$

where:
- $B$: baseline (基线) — spacing between left and right sub-pixels, determined by pixel pitch and microlens design
- $F$: equivalent focal length
- $D$: disparity (视差) — phase difference

**PDAF Pixel Density History**

| Year | Sensor / Product | PDAF Coverage |
|------|-----------------|---------------|
| 2012 | Sony IMX135 | ~5% of pixels are PDAF |
| 2016 | Samsung S3 | 1 PDAF pixel per 2×2 block (~25%) |
| 2019 | Sony IMX586 | Quad-Bayer + embedded PDAF |
| 2021 | Samsung GN2 | 100% all-pixel Dual PD (全像素双 PD) |
| 2022 | Sony IMX989 | 1-inch sensor + full PDAF |

**PDAF Failure Scenarios**

- **Low light (< 1 lux):** SNR too low; noise drowns the phase signal
- **Uniform texture regions:** White walls, clear sky — no phase difference to compute
- **Transparent / reflective surfaces:** Glass panes, mirrors produce false phase signals
- **Motion blur:** Subject movement during integration blurs the phase signal

---

### 1.4 ToF / Laser-Assisted AF

**dToF (Direct Time-of-Flight, 直接飞行时间)**

Emits laser pulses and measures photon round-trip time:

$$\text{Distance} = \frac{c \cdot \Delta t}{2}$$

High accuracy (<5 cm), texture-independent, but higher power consumption; has a blind zone at very close range (<30 cm) in some designs.

**iToF (Indirect Time-of-Flight, 间接飞行时间)**

Emits a modulated continuous wave (e.g., 100 MHz sine wave) and computes distance from the phase difference between transmitted and received signals:

$$\text{Distance} = \frac{c \cdot \phi}{4\pi f_m}$$

where $f_m$ is the modulation frequency and $\phi$ is the measured phase shift. iToF is lower-cost than dToF but susceptible to multipath ambiguity (多径干扰).

**LAHAF (Laser-Assisted Hybrid AF, 激光辅助混合自动对焦)**

Laser ranging provides a coarse distance estimate → narrows the VCM search range from full travel to ±20 steps → greatly accelerates AF in low-light conditions.

Workflow:
```
激光测距(粗) → 换算为 VCM 步数预测位置 → 移动马达到预测位置 → PDAF/CDAF 精调
```

**Applicable Scenarios**

- Dark environments (< 1 lux): works when PDAF fails
- Extreme close-up (< 10 cm): macro scenes
- Textureless subjects (white boards)

---

### 1.5 VCM (Voice Coil Motor, 音圈马达) Control

**VCM Operating Principle**

A VCM uses coil current to generate magnetic force that moves the lens along a track:

$$F = B \cdot I \cdot L$$

where $B$ is the magnetic field strength, $I$ is the coil current, and $L$ is the effective coil length. Displacement is approximately linear with current within the travel range.

**OIS vs. AF Motor Architecture**

- **Separate (分离式):** OIS motor handles optical image stabilization (lateral motion); AF motor handles focusing (axial motion); independent systems.
- **Integrated (集成式, OIS+AF combined):** A single floating suspension supports both lateral (OIS) and axial (AF) motion — common in flagship camera modules.

**Closed-Loop Control (闭环控制)**

A Hall sensor reads the actual lens position, forming a position feedback loop:

```
目标位置 → PID控制器 → 电流驱动 → VCM → 镜头位移
                ↑                        |
              Hall传感器 ←────────────────┘
```

Advantages: position accuracy ±2 μm, consistent response, no re-calibration required.

**Open-Loop Control (开环控制)**

No position feedback; relies on a current-to-step calibration table (LUT):
- Factory calibration maps macro and infinity positions to DAC values
- Intermediate positions are linearly interpolated
- Drawbacks: susceptible to temperature, magnetic interference, and gravity (portrait vs. landscape orientation)

**Temperature Drift Compensation (马达温漂补偿)**

VCM coil resistance increases with temperature; the same DAC value drives less current, causing the lens to drift toward the macro position (spring restoring force dominates):

$$R(T) = R_0 \cdot [1 + \alpha(T - T_0)]$$

Compensation method: NTC thermistor reads real-time temperature → look up temperature compensation LUT → adjust reference DAC value.

---

### 1.6 Video AF (Continuous AF, 连续对焦)

**Unique Challenges**

Still-photo AF only needs the final result to be correct. Video AF must additionally satisfy:
1. **No hunting (无跑焦):** No oscillation around the in-focus position
2. **Smooth transitions (平滑过渡):** Focus pulls must be gradual, not abrupt jumps
3. **Fast tracking (快速响应):** Must keep up with subject motion

**Nudge (轻推) Strategy**

Probe the contrast at ±N steps from the current position each frame; move the motor only if the contrast difference exceeds a threshold (prevents noise-triggered motion). The step size is limited by a damping factor:

$$\text{step}_{n+1} = \alpha \cdot \text{step}_{n} + (1-\alpha) \cdot \text{step}_{\text{target}}$$

**Kalman Filter Prediction**

Model the moving subject as a state vector (position + velocity) and apply a Kalman filter to predict the next-frame target position:

$$\hat{x}_{k|k-1} = F \hat{x}_{k-1|k-1}$$
$$P_{k|k-1} = F P_{k-1|k-1} F^T + Q$$

Measurement update (PDAF provides phase-difference measurement $z_k$):
$$K_k = P_{k|k-1} H^T (H P_{k|k-1} H^T + R)^{-1}$$
$$\hat{x}_{k|k} = \hat{x}_{k|k-1} + K_k(z_k - H\hat{x}_{k|k-1})$$

**Scan Prevention (防扫描)**

When video AF detects that the contrast curve is sufficiently flat (subject is stationary), it suppresses full-scan initiation to prevent frame-visible lens excursions.

---

### 1.7 Deep Learning-Based AF

**CNN Defocus Estimation**

A defocused image contains blur kernel information encoding the magnitude and direction of defocus. A CNN can predict defocus direction and magnitude directly from a single frame — no hardware PDAF required:

- Input: RAW or YUV image patch
- Output: defocus magnitude + direction (near / far)
- Advantage: stronger generalization to low-texture and low-light scenes

**Hybrid Decision Gating (Herrmann et al., ECCV 2020)**

A CNN acts as a "gating network" that selects the best AF mode based on scene conditions (illumination, texture, motion):
- High-light, high-texture → PDAF
- Low-light or low-texture → CDAF + laser assist
- Moving subject → Kalman prediction + PDAF

**Semantic Subject Selection (语义主体选择)**

An NPU runs real-time object detection / segmentation to identify the most probable focus subject. Priority order:

```
人脸/眼睛 > 人体 > 宠物 > 运动物体 > 前景最近物体
```

The detected subject ROI is passed to the AF algorithm as the focus window, replacing fixed center-point focusing.

---

### 1.8 Difficult Scene Summary

| Scene | Challenge | Recommended Approach |
|-------|-----------|----------------------|
| Dark (< 1 lux) | Low PDAF SNR; noisy CDAF | Laser / ToF assist + large-step search |
| Low contrast (white wall) | Contrast operators give no response | ToF direct ranging; CNN estimation |
| Moving subject | Phase signal blurred; curve shifts | Kalman prediction; high-frame-rate PDAF |
| Glass / mirror | False PDAF signals | Detect anomalous phase variance; fall back to CDAF |
| Repetitive texture | Multiple CDAF peaks (false maximum) | Enlarge ROI; use low-frequency operator |
| Macro (< 10 cm) | Extremely shallow DOF; high sensitivity | Small steps + laser-assisted positioning |
| Backlit subject (逆光) | Subject underexposed; contrast biased toward background | Semantic segmentation for subject ROI; zoned exposure |
| Video tracking | Hunting (lens oscillation) | Nudge + damping control |

---

## §2 Calibration (标定)

### 2.1 PDAF Phase Offset Calibration

**Purpose:** Determine the conversion coefficient $k$ (sensitivity) and offset $b$ mapping phase shift (pixels) to VCM steps.

**Procedure:**
1. Point the camera at a calibration chart (high-contrast pattern, e.g., Siemens Star)
2. At known object distances $d_1, d_2, \ldots, d_n$, measure PDAF phase shifts $P_1, P_2, \ldots, P_n$
3. Record in-focus VCM steps $S_1, S_2, \ldots, S_n$ using CDAF ground-truth focusing
4. Linear fit: $S = k \cdot P + b$ — solve for $k$, $b$ by least squares
5. Write result to OTP (One-Time Programmable) memory

**Temperature Dependence:** $k$ varies slightly with temperature. Flagship products calibrate at three points (0°C, 25°C, 60°C) and interpolate at runtime.

**Acceptance Criteria:**
- Calibration residual RMS < 2 steps
- Coverage validation pass rate (0.1m – ∞) > 95%

---

### 2.2 Hall Sensor Linearity Calibration

**Purpose:** Ensure that the Hall sensor output in closed-loop AF is linearly proportional to actual lens displacement.

**Procedure:**
1. Apply stepped currents to the VCM from macro to infinity
2. Measure actual lens displacement precisely using a laser interferometer (激光测微仪) or micrometrology tool
3. Record the Hall output at each step
4. Fit a linearization LUT: Hall code → actual displacement (μm)
5. Compute nonlinearity; modules exceeding ±3% are rejected

**Gravity Direction Compensation (重力方向补偿):**
- Gravity affects the floating lens position differently in landscape vs. portrait orientation
- A gyroscope or accelerometer senses device attitude → dynamically compensate the Hall zero point

---

### 2.3 Temperature Drift Compensation Calibration

**Symptom:** As temperature rises, VCM coil resistance increases → less current for the same DAC value → lens drifts toward macro (spring restoring force dominates).

**Calibration Method:**
1. Set oven temperatures to -10°C, 0°C, 25°C, 40°C, 60°C
2. At each temperature, run CDAF ground-truth focusing on an infinity target; record DAC value
3. Fit the DAC_infinity(T) curve
4. At runtime, read NTC and apply table-based compensation

**Specification:** Focus accuracy variation across the full temperature range (-10°C to 60°C) < ±5 steps (equivalent CoC change < 0.5×).

---

## §3 Tuning (调校)

### 3.1 CDAF Operator Selection

| Scene | Recommended Operator | Reason |
|-------|---------------------|--------|
| General (high SNR) | Tenengrad | Direction-independent, robust |
| Low light (low SNR) | Variance | Less sensitive to noise |
| High-frequency texture | SML | Preserves fine high-frequency detail |
| Real-time video | Simplified Laplacian (3×3 kernel) | Low computation cost |

**ROI Window Size Tuning:**
- Too small: high susceptibility to local noise; noisy contrast curve
- Too large: includes background; dilutes contrast measurement
- Recommendation: center 1/4 of frame area, or semantic subject ROI

**Search Step Size Tuning:**
- Coarse search step: calculated from DOF, typically 8–16 steps
- Fine search step: 1–2 steps
- Two-pass fine-search range: ±8 steps around the coarse-search peak

---

### 3.2 PDAF Sensitivity Tuning

**Over-sensitive ($k$ too large, Over-sensitive):**
- Symptom: single PDAF move overshoots; oscillates near the in-focus position
- Fix: reduce $k$; add a CDAF fine-tuning pass

**Under-sensitive ($k$ too small, Under-sensitive):**
- Symptom: multiple PDAF moves needed to converge (slow AF)
- Fix: increase $k$; raise the single-move step count ceiling

**Phase Confidence Threshold (相位可信度门限):**
- When phase variance > threshold $\sigma_{max}^2$, the phase signal is deemed unreliable (low light / no texture)
- Fall back to CDAF or laser-assisted mode
- Threshold must be calibrated to the sensor noise floor

---

### 3.3 Video AF Damping Tuning

**Damping coefficient $\alpha$** (0 < α < 1):
- $\alpha \to 0$: fast response but prone to oscillation
- $\alpha \to 1$: smooth, but high tracking latency (suitable for static scenes)
- Recommended: scene-adaptive — reduce $\alpha$ when motion is detected; increase $\alpha$ when static

**Hunting Detection and Suppression (Hunting 检测与抑制):**
- If motor direction reverses ≥ 2 times within N consecutive frames → classify as hunting
- Response: freeze position (Hold mode), re-evaluate ROI

---

## §4 Artifacts (典型问题与伪影)

### 4.1 Video Hunting (视频跑焦)

**Symptom:** After focusing, the lens continues to make small back-and-forth movements around the in-focus position; image sharpness oscillates periodically.

**Root Causes:**
- CDAF contrast curve is too flat near the peak; noise continuously flips the perceived best direction
- Damping coefficient $\alpha$ is too small

**Diagnostic Steps:**
1. Capture log: record per-frame contrast value, motor step, and movement direction
2. Plot contrast vs. step curve: assess peak width
3. If peak width < 4 steps (< one DOF unit), increase the CDAF ROI or switch to a lower-frequency operator
4. Increase $\alpha$ (e.g., 0.60 → 0.85) and retest

### 4.2 PDAF False Pull in Glass Scenes (PDAF 玻璃场景误拉焦)

**Symptom:** When shooting subjects behind a glass pane, PDAF is disturbed by reflection signals and focuses on the glass surface instead of the subject.

**Diagnosis:**
- Phase shift values are anomalous (normal range ±30 pixels; glass scenes may show ±5 pixels with high jitter)
- Phase signal variance $\sigma^2$ significantly elevated compared to normal

**Solutions:**
- Add phase consistency check: if standard deviation of phase differences across neighboring pixels > threshold → reduce phase confidence score
- Fall back to CDAF with a stable contrast-based search
- Software-level: detect "reflection scene" flag (e.g., high-brightness specular spot detection)

### 4.3 Low-Light PDAF Noise Contamination (低光 PDAF 噪声污染)

**Symptom:** Under dim lighting, PDAF phase estimation error is large; AF moves to an incorrect position.

**Root Cause:** Insufficient photon count per sub-pixel; shot noise (散粒噪声) overwhelms the phase signal.

**Solutions:**
- Increase PDAF integration window (bin multiple rows of phase values)
- Switch to laser-assisted or CDAF mode (gate condition: luma < 20 in 8-bit)
- Extend PDAF measurement exposure time (in video AF, integrate over 2 frames)

---

## §5 Evaluation (评估方法)

### 5.1 AF Speed Test

**Test Method (ISO standard or vendor specification):**
1. Far-to-near switch: pre-focus camera at infinity, press focus trigger, measure time to achieve focus lock on a near target (e.g., 0.5 m)
2. Timing method: video frame-level (frames from shutter press to "focus locked" × frame interval)
3. Lighting conditions: 100 lux (normal indoor), 10 lux (dim), 1 lux (candlelight)

**Performance Targets:**
- PDAF scenes: < 300 ms (100 lux), < 500 ms (10 lux)
- CDAF scenes: < 800 ms (100 lux)
- Dark scene with laser assist: < 600 ms (1 lux)

### 5.2 AF Accuracy Test

**Static Accuracy:**
- Capture ISO 12233 resolution chart; calculate MTF50 after focusing
- Evaluate: MTF50 at in-focus position / theoretical maximum MTF50 (must be > 80%)

**Dynamic Accuracy:**
- Subject moves laterally at a known speed (e.g., 1 m/s); evaluate continuous AF tracking rate

**Difficult Scene Pass Rate:**
- Low light (1 lux): pass rate > 80%
- Textureless (white board): pass rate > 60% (requires laser assist)
- Glass scene: pass rate > 70%

### 5.3 Video AF Smoothness Evaluation

**Hunting Detection Rate:**
- Record 10 seconds of video; count the number of motor direction reversals
- Pass criterion: < 2 reversals per 10 seconds for a static scene

**Focus Transition Time:**
- Time from start of motor motion to in-focus (MTF50 > 80% of peak)
- Video requirement: < 600 ms (must not be too fast, to avoid a visually jarring pull)

---

## §6 Code Reference (代码参考)

### 6.1 CDAF Hill-Climbing Search Simulation (Python)

```python
import numpy as np
import matplotlib.pyplot as plt

def tenengrad(image_patch):
    """计算 Tenengrad 对比度算子"""
    # Sobel 核
    gx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    gy = gx.T
    from scipy.ndimage import convolve
    dx = convolve(image_patch.astype(np.float32), gx)
    dy = convolve(image_patch.astype(np.float32), gy)
    return np.sum(dx**2 + dy**2)

def simulate_contrast_curve(steps, peak_pos=50, peak_width=15, noise_level=0.02):
    """
    模拟 VCM 步数-对比度曲线（高斯形状 + 噪声）

    Args:
        steps: VCM 步数数组（0-100）
        peak_pos: 合焦位置（步）
        peak_width: 峰宽（步，对应景深）
        noise_level: 相对噪声水平
    Returns:
        contrast: 对比度值数组
    """
    contrast = np.exp(-0.5 * ((steps - peak_pos) / peak_width)**2)
    noise = np.random.normal(0, noise_level, len(steps))
    return contrast + noise

def cdaf_fibonacci_search(contrast_fn, lo=0, hi=100, tol=2):
    """
    斐波那契搜索 CDAF（假设单峰）

    Args:
        contrast_fn: 给定步数返回对比度的函数
        lo, hi: 搜索范围
        tol: 收敛容差（步）
    Returns:
        best_pos: 估计的最佳对焦步数
        history: 搜索历史 [(step, contrast), ...]
    """
    # 生成斐波那契数列直到超过范围
    fibs = [1, 1]
    while fibs[-1] < (hi - lo):
        fibs.append(fibs[-1] + fibs[-2])
    n = len(fibs) - 1

    history = []

    for k in range(n, 1, -1):
        x1 = lo + fibs[k-2]
        x2 = lo + fibs[k-1]
        x1 = min(x1, hi)
        x2 = min(x2, hi)

        c1 = contrast_fn(x1)
        c2 = contrast_fn(x2)
        history.append((x1, c1))
        history.append((x2, c2))

        if c1 < c2:
            lo = x1
        else:
            hi = x2

        if (hi - lo) <= tol:
            break

    best_pos = (lo + hi) // 2
    return best_pos, history

def cdaf_full_scan(contrast_fn, lo=0, hi=100, step=2):
    """全程扫描 CDAF"""
    positions = np.arange(lo, hi+1, step)
    contrasts = [contrast_fn(p) for p in positions]
    best_idx = np.argmax(contrasts)
    history = list(zip(positions, contrasts))
    return positions[best_idx], history

# 演示
if __name__ == "__main__":
    steps_all = np.arange(0, 101)
    true_peak = 42

    # 生成对比度曲线
    contrast_vals = simulate_contrast_curve(steps_all, peak_pos=true_peak,
                                             peak_width=12, noise_level=0.03)
    contrast_fn = lambda s: float(simulate_contrast_curve(
        np.array([s]), peak_pos=true_peak, peak_width=12, noise_level=0.03))

    # 斐波那契搜索
    fib_result, fib_history = cdaf_fibonacci_search(contrast_fn, 0, 100)

    # 全程扫描
    full_result, full_history = cdaf_full_scan(
        lambda s: float(simulate_contrast_curve(np.array([s]), true_peak, 12, 0.03)),
        0, 100, step=2)

    print(f"True peak: {true_peak}")
    print(f"Fibonacci search result: {fib_result} (steps evaluated: {len(fib_history)})")
    print(f"Full scan result: {full_result} (steps evaluated: {len(full_history)})")

    # 绘图
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    axes[0].plot(steps_all, contrast_vals, 'b-', label='Contrast curve')
    fib_steps, fib_c = zip(*fib_history)
    axes[0].scatter(fib_steps, fib_c, c='r', s=30, zorder=5, label=f'Fib search ({len(fib_history)} pts)')
    axes[0].axvline(true_peak, color='g', linestyle='--', label=f'True peak={true_peak}')
    axes[0].axvline(fib_result, color='r', linestyle=':', label=f'Fib result={fib_result}')
    axes[0].set_xlabel('VCM Step')
    axes[0].set_ylabel('Contrast Value')
    axes[0].set_title('CDAF Fibonacci Search')
    axes[0].legend()

    full_steps, full_c = zip(*full_history)
    axes[1].plot(steps_all, contrast_vals, 'b-', label='Contrast curve')
    axes[1].scatter(full_steps, full_c, c='orange', s=30, zorder=5,
                    label=f'Full scan ({len(full_history)} pts)')
    axes[1].axvline(true_peak, color='g', linestyle='--', label=f'True peak={true_peak}')
    axes[1].axvline(full_result, color='orange', linestyle=':', label=f'Full result={full_result}')
    axes[1].set_xlabel('VCM Step')
    axes[1].set_ylabel('Contrast Value')
    axes[1].set_title('CDAF Full Scan')
    axes[1].legend()

    plt.tight_layout()
    plt.savefig('cdaf_search_comparison.png', dpi=150)
    plt.show()
```

---

### 6.2 PDAF Phase Signal Model (Python)

```python
import numpy as np

def generate_pdaf_signal(image_row, disparity_pixels):
    """
    模拟 PDAF 双像素相位差信号

    原理：左子像素图像相当于从略偏左角度拍摄，
          右子像素图像相当于从略偏右角度拍摄。
          失焦时两路图像有横向位移（disparity）。

    Args:
        image_row: 1D 理想清晰图像行（numpy array）
        disparity_pixels: 失焦引起的像素级位移（正=前焦，负=后焦）
    Returns:
        left_view: 左子像素采样信号
        right_view: 右子像素采样信号
        phase_shift_estimate: 估计的相位差
    """
    n = len(image_row)
    x = np.arange(n)

    # 左右视差模拟（亚像素插值）
    shift = disparity_pixels / 2.0

    from scipy.ndimage import shift as ndshift
    left_view  = ndshift(image_row.astype(float),  shift, mode='nearest')
    right_view = ndshift(image_row.astype(float), -shift, mode='nearest')

    # 加入传感器噪声
    noise_std = 2.0  # 8-bit 单位
    left_view  += np.random.normal(0, noise_std, n)
    right_view += np.random.normal(0, noise_std, n)

    # 相位差估计：互相关法
    phase_shift_estimate = estimate_phase_shift_xcorr(left_view, right_view)

    return left_view, right_view, phase_shift_estimate

def estimate_phase_shift_xcorr(left, right, max_shift=20):
    """
    通过互相关估计相位差

    Args:
        left, right: 左右子像素信号
        max_shift: 最大搜索范围（像素）
    Returns:
        estimated_shift: 估计的相位差（像素，正值=前焦）
    """
    left_norm  = (left  - np.mean(left))  / (np.std(left)  + 1e-6)
    right_norm = (right - np.mean(right)) / (np.std(right) + 1e-6)

    # 仅在 [-max_shift, +max_shift] 范围内搜索
    xcorr = np.correlate(left_norm, right_norm, mode='full')
    center = len(xcorr) // 2
    search_xcorr = xcorr[center - max_shift : center + max_shift + 1]

    peak_offset = np.argmax(search_xcorr) - max_shift
    return float(peak_offset)

def pdaf_to_vcm_step(phase_shift, k, b):
    """
    相位差到 VCM 步数转换

    Args:
        phase_shift: 估计的相位差（像素）
        k: 灵敏度（标定值）
        b: 偏置（标定值）
    Returns:
        delta_step: 需要移动的 VCM 步数（正=向 macro，负=向 infinity）
    """
    return k * phase_shift + b

# 演示
if __name__ == "__main__":
    # 生成测试图像行（边缘图案）
    n = 256
    image_row = np.zeros(n)
    image_row[80:100] = 200  # 白色边缘
    image_row[150:160] = 200
    image_row = image_row + np.random.normal(0, 1, n)  # 底噪

    # 测试不同失焦量
    test_disparities = [-8, -4, -2, 0, 2, 4, 8]  # 像素

    print(f"{'True Disparity':>15} | {'Estimated Disparity':>20} | {'Error':>8}")
    print("-" * 50)

    for true_disp in test_disparities:
        left, right, estimated = generate_pdaf_signal(image_row, true_disp)
        error = estimated - true_disp
        print(f"{true_disp:>15.1f} | {estimated:>20.2f} | {error:>8.2f}")

    # 模拟 VCM 步数映射（标定参数示例）
    k_calibrated = 3.5   # 步/像素
    b_calibrated = 0.0   # 无偏置

    print(f"\n使用标定参数 k={k_calibrated}, b={b_calibrated}")
    print(f"相位差 +5 像素 → VCM 步数: {pdaf_to_vcm_step(5.0, k_calibrated, b_calibrated):.1f}")
    print(f"相位差 -3 像素 → VCM 步数: {pdaf_to_vcm_step(-3.0, k_calibrated, b_calibrated):.1f}")
```

---

### 6.3 Kalman Filter for Video AF Tracking (Python)

```python
import numpy as np

class AFKalmanFilter:
    """
    视频 AF 用 Kalman 滤波器

    状态向量: [位置(步), 速度(步/帧)]
    测量值: VCM 步数（来自 PDAF 或 CDAF）
    """

    def __init__(self, initial_pos=50.0, process_noise=1.0, measurement_noise=4.0):
        """
        Args:
            initial_pos: 初始位置（VCM 步）
            process_noise: 过程噪声方差（目标运动不确定性）
            measurement_noise: 测量噪声方差（PDAF 测量误差）
        """
        # 状态向量：[位置, 速度]
        self.x = np.array([[initial_pos], [0.0]])

        # 状态协方差矩阵
        self.P = np.eye(2) * 10.0

        # 状态转移矩阵（匀速运动模型）
        self.F = np.array([[1, 1],
                           [0, 1]], dtype=float)

        # 测量矩阵（只观测位置）
        self.H = np.array([[1, 0]], dtype=float)

        # 过程噪声矩阵
        self.Q = np.eye(2) * process_noise
        self.Q[1, 1] *= 0.1  # 速度噪声较小

        # 测量噪声矩阵
        self.R = np.array([[measurement_noise]])

    def predict(self):
        """预测下一帧位置"""
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return float(self.x[0])

    def update(self, measurement):
        """
        用 PDAF 测量值更新状态

        Args:
            measurement: 测量到的 VCM 目标步数
        Returns:
            filtered_pos: 滤波后的位置估计
        """
        z = np.array([[measurement]])

        # 创新（Innovation）
        y = z - self.H @ self.x

        # 创新协方差
        S = self.H @ self.P @ self.H.T + self.R

        # Kalman 增益
        K = self.P @ self.H.T @ np.linalg.inv(S)

        # 状态更新
        self.x = self.x + K @ y

        # 协方差更新
        I = np.eye(2)
        self.P = (I - K @ self.H) @ self.P

        return float(self.x[0])

    @property
    def position(self):
        return float(self.x[0])

    @property
    def velocity(self):
        return float(self.x[1])

# 演示：跟踪运动目标
if __name__ == "__main__":
    np.random.seed(42)
    n_frames = 60

    # 真实目标位置（缓慢从 30 步移动到 70 步）
    true_positions = np.linspace(30, 70, n_frames)
    true_positions += np.random.normal(0, 0.5, n_frames)  # 目标微小抖动

    # PDAF 测量（有噪声）
    measurements = true_positions + np.random.normal(0, 3.0, n_frames)

    kf = AFKalmanFilter(initial_pos=30.0, process_noise=2.0, measurement_noise=9.0)

    predicted_positions = []
    filtered_positions = []

    for i in range(n_frames):
        pred = kf.predict()
        filtered = kf.update(measurements[i])
        predicted_positions.append(pred)
        filtered_positions.append(filtered)

    # 评估
    filtered_arr = np.array(filtered_positions)
    rmse = np.sqrt(np.mean((filtered_arr - true_positions)**2))
    meas_rmse = np.sqrt(np.mean((measurements - true_positions)**2))

    print(f"测量噪声 RMSE:  {meas_rmse:.2f} 步")
    print(f"Kalman 滤波后 RMSE: {rmse:.2f} 步")
    print(f"噪声压制比: {meas_rmse/rmse:.1f}×")
```

---

## Chapter Summary

| Topic | Key Points |
|-------|-----------|
| CDAF | Hill-climb to maximum contrast; Fibonacci search is most efficient; video requires damping |
| PDAF | Single-frame directional defocus measurement; requires calibrated $k$, $b$; fails in low-light / glass |
| ToF / Laser | Coarse ranging in dark scenes; hybrid with PDAF for speed |
| VCM | Closed-loop Hall feedback for high accuracy; NTC temperature drift compensation |
| Video AF | Nudge + damping; Kalman filter for moving subjects |
| DL AF | CNN defocus estimation; NPU semantic subject selection |
| Calibration | PDAF phase-to-step linear fit; full-temperature DAC compensation |

> **Further Reading**
> - Herrmann et al., "Learning to Autofocus", CVPR 2020
> - Tang et al., "Phase Detection Autofocus Using Dual Pixel Sensors", IEEE Trans. 2018
> - ISO 16505:2015 – Autofocus test methods for digital cameras
> - Chapter 26 (3A Coordination and Scene-Adaptive Control, 3A 联动与场景自适应)
