# Part 2, Chapter 12: Temporal Noise Reduction for Video

---

## Table of Contents

1. [Theory](#1-theory)
2. [Calibration](#2-calibration)
3. [Tuning Guide](#3-tuning-guide)
4. [Artifact Analysis](#4-artifact-analysis)
5. [Evaluation Methods](#5-evaluation-methods)
6. [Reference Code](#6-reference-code)

---

## 1 Theory

### 1.1 Why Spatial Noise Reduction Is Not Enough

Spatial noise reduction (spatial NR, SNR) suppresses noise within a single frame by applying neighborhood filtering — in essence, averaging noise across the spatial domain. In video, however, spatial NR faces two fundamental contradictions:

**The smoothing-detail trade-off**: Increasing denoising strength (enlarging the filter kernel) inevitably destroys spatial high-frequency detail, causing visible blur; reducing the strength leaves noticeable noise residual. The signal-to-noise ratio (SNR) ceiling of a single frame is bounded by spatial sampling density.

**Unused temporal redundancy**: Adjacent video frames exhibit extremely strong temporal correlation (temporal redundancy 时间冗余). For a stationary region, pixels at the same location in consecutive frames should theoretically be identical; any difference is purely noise. If multiple aligned frames are accumulated and averaged, the noise — being a zero-mean random process — is reduced by $\sqrt{N}$ in standard deviation after averaging $N$ frames, while the true signal is perfectly preserved.

**Temporal noise reduction (temporal NR, TNR 时域降噪)** exploits this inter-frame temporal redundancy by using historical frame information to assist current-frame denoising, theoretically delivering a large SNR gain without sacrificing spatial resolution.

**Principle of temporal SNR improvement**:

Let the pixel value at frame $n$ be:

$$
I(n) = S + \eta(n)
$$

where $S$ is the true signal and $\eta(n) \sim \mathcal{N}(0, \sigma^2)$ is independent, identically distributed noise. Averaging $N$ frames:

$$
\hat{S} = \frac{1}{N} \sum_{n=1}^N I(n) = S + \frac{1}{N}\sum_{n=1}^N \eta(n)
$$

The noise standard deviation after averaging is $\sigma / \sqrt{N}$, and SNR improves by a factor of $\sqrt{N}$.

### 1.2 The Core TNR Formula

The fundamental operation of temporal noise reduction is a motion-adaptive exponential moving average (EMA 指数滑动平均):

$$
Y_{\text{out}}(n) = \alpha(n) \cdot Y_{\text{in}}(n) + (1 - \alpha(n)) \cdot Y_{\text{ref}}(n-1)
$$

where:
- $Y_{\text{in}}(n)$: pixel value of the current frame $n$
- $Y_{\text{ref}}(n-1)$: motion-compensated reference frame (previous frame warped to the current frame's coordinate system)
- $\alpha(n) \in [0, 1]$: motion-adaptive blending factor (运动自适应混合系数)
- $Y_{\text{out}}(n)$: output (denoised) pixel value, which also serves as the reference for the next frame

**Key constraints**:
- Stationary regions (no motion): $\alpha \rightarrow 0$ — heavy temporal averaging, strong denoising
- Moving regions: $\alpha \rightarrow 1$ — use current frame exclusively, avoiding motion ghosting (鬼影)

### 1.3 Motion Estimation

Motion estimation (ME 运动估计) is the core challenge of temporal NR; it must find pixel-level correspondences between frames.

**Method 1: Block Matching (块匹配)**

The current frame is divided into blocks (typically 4×4 to 8×8 pixels in hardware ISP implementations). A search is performed in the reference frame to find the best-matching block for each, yielding a motion vector (MV 运动向量) per block:

$$
\text{MV}(b) = \arg\min_{(d_x, d_y)} \text{SAD}(b, d_x, d_y)
$$

$$
\text{SAD}(b, d_x, d_y) = \sum_{(x,y) \in b} |Y_{\text{cur}}(x, y) - Y_{\text{ref}}(x+d_x, y+d_y)|
$$

SAD (sum of absolute differences 绝对差值和) is the most commonly used block-matching cost function. The search range is typically ±16 to ±32 pixels.

**Method 2: Optical Flow (光流法)**

Dense optical flow (稠密光流) computes a motion vector $\mathbf{v}(x,y) = (u, v)$ for every pixel, based on the brightness constancy assumption (亮度守恒假设):

$$
I(x, y, t) = I(x+u, y+v, t+1)
$$

The corresponding optical flow constraint equation (Horn-Schunck equation):

$$
I_x u + I_y v + I_t = 0
$$

where $I_x, I_y$ are spatial gradients and $I_t$ is the temporal gradient. Optical flow is more accurate than block matching but more computationally expensive; it is commonly used for offline processing, while block matching is better suited to ISP hardware implementation.

**Method 3: Phase Correlation (相位相关)**

Based on the Fourier transform, global motion is estimated via the frequency-domain cross-power spectrum, making it well-suited to camera-translation scenarios:

$$
R(u, v) = \mathcal{F}^{-1}\left\{\frac{F_1(\omega) \cdot F_2^*(\omega)}{|F_1(\omega) \cdot F_2^*(\omega)|}\right\}
$$

---

### 1.4 Motion-Adaptive Blending

The motion-adaptive (运动自适应) mechanism dynamically adjusts $\alpha$ based on the measured amount of motion.

**Step 1: Compute frame difference**

$$
D(x, y) = |Y_{\text{cur}}(x, y) - Y_{\text{ref\_aligned}}(x, y)|
$$

**Step 2: Normalize the motion metric**

$$
M(x, y) = \min\left(1,\ \frac{D(x, y)}{T_{\text{motion}}}\right)
$$

where $T_{\text{motion}}$ is the motion decision threshold (typical values: 8–16 at low light, 16–32 at normal exposure).

**Step 3: Compute blending coefficient**

$$
\alpha(x, y) = \alpha_{\min} + (\alpha_{\max} - \alpha_{\min}) \cdot M(x, y)
$$

Typical parameters: $\alpha_{\min} = 0.05 \sim 0.15$ (stationary regions), $\alpha_{\max} = 0.9 \sim 1.0$ (moving regions).

**Intuitive interpretation**:
- Fully stationary pixel ($D \approx 0$): $\alpha \approx \alpha_{\min}$ — the historical frame contributes 85%–95% of the weight, aggressively averaging away noise.
- Fast-moving pixel ($D$ large): $\alpha \approx 1$ — the current frame is used entirely, introducing no ghosting.

---

### 1.5 Motion-Compensated Temporal Filtering (MCTF)

MCTF (motion-compensated temporal filtering 运动补偿时域滤波) extends block matching by first aligning frames before filtering, offering greater accuracy than a simple frame-difference approach:

$$
Y_{\text{MCTF}}(n) = \alpha \cdot Y(n) + \frac{(1-\alpha)}{2}\left[Y_{\text{comp}}(n-1) + Y_{\text{comp}}(n+1)\right]
$$

where $Y_{\text{comp}}(n\pm1)$ are the pixel values of the preceding and following frames after motion-compensated warping to frame $n$'s coordinate system. Bidirectional temporal filtering improves denoising further, but introduces latency (it requires a future frame) and is therefore not suitable for real-time preview; it is commonly used in video post-processing.

---

### 1.6 Kalman Filter Temporal Denoising

The Kalman filter (卡尔曼滤波) models pixel luminance as a state variable and achieves optimal estimation through a predict-update cycle.

**State equations** (stationarity assumption):

$$
\hat{Y}_k^- = \hat{Y}_{k-1}
$$

$$
P_k^- = P_{k-1} + Q
$$

**Update equations**:

$$
K_k = \frac{P_k^-}{P_k^- + R}
$$

$$
\hat{Y}_k = \hat{Y}_k^- + K_k (Y_k^{\text{obs}} - \hat{Y}_k^-)
$$

$$
P_k = (1 - K_k) P_k^-
$$

where:
- $Q$: process noise covariance (represents the rate of scene change)
- $R$: observation noise covariance (corresponds to the image sensor noise variance $\sigma^2$)
- $K_k$: Kalman gain ($K \rightarrow 0$ trusts history; $K \rightarrow 1$ trusts the current observation)

When $Q \ll R$, the Kalman filter degenerates into heavy temporal averaging (strong denoising). When motion causes $P_k^-$ to grow, $K_k$ increases, automatically giving more weight to the current frame.

---

### 1.7 Hardware Architecture: The ISP TNR Block

In mobile-platform ISPs (such as Qualcomm Spectra, MediaTek Imagiq, and Samsung SIRC), temporal noise reduction is typically implemented as a dedicated hardware module:

```
RAW/YUV Input
    │
    ▼
┌─────────────────────────────────┐
│         TNR Hardware Block       │
│                                 │
│  ┌──────────┐  MV  ┌─────────┐ │
│  │  Motion  │─────▶│ Motion  │ │
│  │Estimation│      │Compen-  │ │
│  │(Blk Match│      │sation   │ │
│  └──────────┘      └────┬────┘ │
│       ▲                 │      │
│       │         Reference Align│
│  ┌────┴────┐      ┌────▼────┐ │
│  │  Frame  │◀─────│Temporal │ │
│  │ Buffer  │      │ Blend   │ │
│  │         │      │(α blend)│ │
│  └─────────┘      └─────────┘ │
└─────────────────────────────────┘
    │
    ▼
Denoised Frame Output
```

**Frame buffer requirement**: TNR requires storing at least one full-resolution reference frame. For 1080p YUV420 this is approximately 3 MB; for 4K YUV420 it is approximately 12 MB. This is a significant contributor to hardware cost.

### 1.8 Integration Order with EIS

EIS (electronic image stabilization 电子图像稳定) compensates for camera shake by cropping and warping the image. The processing order of TNR and EIS is critically important.

**Correct order**: TNR → EIS

**Rationale**: TNR relies on inter-frame pixel alignment, while EIS performs cropping and affine transforms on the image. If EIS is applied first, corresponding pixels across frames already lie within different fields of view, and the block-matching search range and coordinate reference frames are both corrupted. By applying TNR first — aligning inter-frame motion in the original (pre-stabilization) coordinate system — and then handing off to EIS for camera-motion compensation, the two stages operate without interfering with each other.

### 1.9 TNR vs. Multi-Frame Noise Reduction (MFNR)

| Characteristic | Temporal NR (TNR) | Multi-Frame NR (MFNR) |
|----------------|-------------------|----------------------|
| Use case | Real-time video preview/recording | Still photography |
| Number of frames | Continuous (infinite recursive) | Limited (4–16 frames) |
| Latency requirement | Real-time (≤ 1 frame delay) | Longer wait acceptable |
| Alignment accuracy | Block matching (real-time) | Feature-point / optical-flow (high precision) |
| Hardware requirement | Dedicated TNR block + frame buffer | CPU/DSP post-processing |
| Motion handling | Motion-adaptive blending | Reject motion regions |
| Equivalent frame count | Infinite accumulation (exponential decay weights) | Fixed N frames |

---

## 2 Calibration

### 2.1 Noise Parameter Calibration

The motion decision threshold $T_{\text{motion}}$ and blending coefficient range $[\alpha_{\min}, \alpha_{\max}]$ must be calibrated against the sensor's actual noise characteristics.

**Step 1: Estimate sensor noise variance**

Capture a stationary scene in no-light or very dark conditions and compute the per-pixel inter-frame variance:

$$
\sigma^2_{\text{noise}}(x, y) = \frac{1}{N-1}\sum_{n=1}^{N}(I_n(x,y) - \bar{I}(x,y))^2
$$

This produces a noise variance table (噪声方差表) at different ISO (gain) settings, which serves as the basis for setting the motion decision threshold.

**Step 2: Threshold calibration**

$T_{\text{motion}}$ must be greater than the frame-difference standard deviation caused by noise alone, $\sigma_{\text{diff}} = \sqrt{2} \sigma_{\text{noise}}$. A typical setting is:

$$
T_{\text{motion}} \approx 3 \sigma_{\text{diff}} = 3\sqrt{2} \sigma_{\text{noise}}
$$

**Step 3: ISO-indexed parameter table**

| ISO | $\sigma_{\text{noise}}$ (typical) | $T_{\text{motion}}$ | $\alpha_{\min}$ |
|-----|----------------------------------|---------------------|-----------------|
| 100 | 2–4 LSB | 8–16 | 0.10 |
| 400 | 5–8 LSB | 16–24 | 0.12 |
| 1600 | 10–15 LSB | 28–40 | 0.15 |
| 6400 | 20–30 LSB | 50–70 | 0.20 |

### 2.2 Motion Estimation Accuracy Verification

Verify block-matching accuracy using a calibration scene with known motion (e.g., a motorized translation stage carrying a test pattern):

1. Translate the calibration pattern at known velocities (e.g., 2 px/frame, 5 px/frame, 10 px/frame).
2. Compare the motion vectors output by block matching against the ground-truth displacements; compute MEE (motion estimation error).
3. Adjust the search range and cost function until MEE < 1 px (sub-pixel accuracy).

---

## 3 Tuning Guide

### 3.1 Key Parameter Hierarchy

```
TemporalNR
├── Enable                  # Master switch
├── MotionAdaptive
│   ├── MotionThreshold     # Motion decision threshold (ISO-adaptive)
│   ├── AlphaMin            # Blending coefficient lower bound for still regions [0.05, 0.20]
│   ├── AlphaMax            # Blending coefficient upper bound for moving regions [0.85, 1.00]
│   └── SoftTransitionWidth # Transition width from still to moving (frame-diff value range)
├── BlockMatching
│   ├── BlockSize           # Block size (pixels): 8, 16, 32
│   ├── SearchRange         # Search range (±pixels): 8, 16, 32
│   └── MVSmoothness        # Motion vector smoothness (prevents abrupt MV changes)
├── LumaChromaControl
│   ├── LumaTNRStrength     # Luma channel denoising strength [0, 1]
│   └── ChromaTNRStrength   # Chroma channel denoising strength [0, 1] (typically > luma)
└── ISOAutoTable            # Lookup table for auto-switching parameters by ISO
```

### 3.2 ISO-Segment Tuning Strategy

**Low ISO (< 400)**:
- Moderate TNR strength, $\alpha_{\min} = 0.10$
- Noise is low; primary purpose is eliminating sensor readout noise

**Mid ISO (400–1600)**:
- Increased TNR strength, $\alpha_{\min} = 0.12$; $T_{\text{motion}}$ increases linearly with ISO
- Raise chroma channel denoising strength (color noise appears before luma noise)

**High ISO (> 3200)**:
- Maximum TNR strength, $\alpha_{\min} = 0.18 \sim 0.25$
- Moderately increase $T_{\text{motion}}$ to prevent noise being misclassified as motion
- Enable dedicated chroma denoising (Chroma TNR strength > Luma TNR strength)

### 3.3 Tuning for Motion Scenes

**Fast-motion scenes (sports, running)**:
- Reduce $\alpha_{\min}$ (prevent the historical-frame inertia from being too strong, which causes ghosting)
- Narrow the search range (fast motion makes block matching prone to false matches)
- Optionally reduce TNR strength, trading some denoising for sharpness

**Camera-shake scenes (handheld capture)**:
- Rely on global motion estimation (全局运动估计) to first compensate for camera shake
- Then apply local motion adaptation to distinguish foreground motion from background motion

### 3.4 Coordination with Spatial NR (SNR)

Temporal and spatial noise reduction are typically cascaded:

**Recommended order**: TNR → SNR (spatial refinement)

Rationale: TNR uses temporal information to eliminate the majority of noise first; SNR then performs a final cleanup of residual noise. If SNR is applied first, it will smooth out inter-frame differences and interfere with TNR's motion detection.

---

## 4 Artifact Analysis

### 4.1 Ghosting (鬼影)

**Symptom**: Moving objects (a person's arm, scrolling text, a fast-moving car) leave semi-transparent motion trails or "shadows" — visually similar to a long-exposure image.

**Cause**: The $\alpha$ value in motion regions fails to rise rapidly to 1, and still-scene pixels from the historical frame are blended into the current moving pixels:

$$
Y_{\text{out}} = \alpha Y_{\text{cur}} + (1-\alpha) Y_{\text{prev}}
$$

When $\alpha = 0.5$, the previous-frame ghost is clearly superimposed.

**Diagnosis**: Inspect the edges of a moving object against a still background. A trailing edge ("comet tail") indicates ghosting.

**Solutions**:
- Lower the motion detection trigger threshold $T_{\text{motion}}$ (detect motion more sensitively).
- Directly set $\alpha = 1.0$ for any region with a non-zero motion vector (hard decision).
- Increase $\alpha_{\max}$ (closer to 1.0) to ensure moving regions use the current frame entirely.

### 4.2 Noise Residual in Stationary Regions

**Symptom**: In high-noise scenes (high ISO), clearly stationary regions (walls, sky) still exhibit noticeable noise grain — insufficient TNR effectiveness.

**Cause**: $\alpha_{\min}$ is set too high (e.g., 0.3), providing insufficient temporal averaging (effective average of only $1/(1-\alpha_{\min}) \approx 1.4$ frames).

**Solutions**:
- Lower $\alpha_{\min}$ (e.g., to 0.10–0.12) to increase the temporal integration frame count.
- Verify that noise variance calibration is accurate and that $T_{\text{motion}}$ is not too low (causing noise to be misclassified as motion).

### 4.3 Edge Ghosting (边缘鬼影)

**Symptom**: High-contrast edges (text, building outlines) exhibit doubled or multiple contours, especially during slight camera shake.

**Cause**: Block matching fails to align precisely at edges (sub-pixel error). The alignment offset causes the edge positions in the current frame and reference frame to not coincide; their blend produces a double-edge artifact.

**Solutions**:
- Increase $\alpha$ in high-gradient regions ($|\nabla I| > T_{\text{edge}}$) to favor the current frame.
- Use sub-pixel-accurate block matching (bilinear interpolation of the reference frame).
- Strengthen the motion vector smoothness constraint to prevent abrupt MV changes between adjacent blocks.

### 4.4 Color Flickering (色彩闪烁)

**Symptom**: Under fluorescent lighting (50 Hz/60 Hz strobe) or LED lighting, the image exhibits periodic luminance or color oscillation that TNR cannot fully suppress.

**Cause**: Fluorescent lamp flicker causes systematic inter-frame luminance variation. TNR's frame-difference threshold misclassifies this as "motion" and cannot effectively suppress it.

**Solutions**:
- Add flicker detection and inter-frame gain equalization (anti-banding correction 防闪烁校正) before TNR.
- Synchronize the shutter speed with the AC frequency ($t_{\text{shutter}} = n / f_{\text{AC}}$).

---

## 5 Evaluation Methods

### 5.1 Temporal SNR (tSNR 时域信噪比)

tSNR is the most direct measure of temporal denoising effectiveness. It quantifies inter-frame noise in a stationary scene:

$$
\text{tSNR} = 20 \log_{10}\left(\frac{\bar{I}}{\sigma_{\text{temporal}}}\right)\ \text{dB}
$$

$$
\sigma_{\text{temporal}} = \sqrt{\frac{1}{N}\sum_{n=1}^{N}(I_n - \bar{I})^2}
$$

where $\bar{I}$ is the multi-frame mean and $\sigma_{\text{temporal}}$ is the inter-frame standard deviation.

**Measurement scene**: Capture a stationary uniform patch (e.g., an 18% gray card) at different ISO values; record the tSNR with TNR on and off. TNR should deliver a tSNR improvement of 3–8 dB depending on ISO.

### 5.2 Flicker Frequency Analysis

For stationary regions after TNR, apply FFT analysis to single-pixel time series to check for periodic noise components (e.g., 50 Hz/60 Hz and harmonics):

$$
F(\omega) = \sum_{n=0}^{N-1} I_n e^{-j2\pi\omega n/N}
$$

If $|F(50\text{ Hz}/f_{\text{fps}})|$ exceeds the noise floor by more than 10 dB, flicker suppression is insufficient.

### 5.3 Motion Sharpness Test

Evaluates the impact of TNR on moving-object sharpness:

1. Capture a resolution test pattern (horizontal/vertical lines) moving at a constant velocity $v$ px/frame.
2. Compute the MTF (modulation transfer function 调制传递函数) along the direction of motion:

$$
\text{MTF}(f) = \frac{|\text{Contrast}(f)_{\text{output}}|}{|\text{Contrast}(f)_{\text{input}}|}
$$

3. Target: at $v = 5$ px/frame, MTF at Nyquist/2 spatial frequency > 0.3; at $v = 10$ px/frame, MTF > 0.2.

### 5.4 Ghost Artifact Subjective Evaluation

- Prepare a standard ghosting test sequence (white text scrolling on a black background; rapid hand waving).
- Have 5 evaluators give subjective scores on a 1–5 scale (1 = severe ghosting, 5 = no ghosting).
- Pass criterion: MOS ≥ 4.0.

### 5.5 Comprehensive Evaluation Matrix

| Test Item | Metric | Pass Criterion |
|-----------|--------|---------------|
| Stationary scene denoising | tSNR improvement | ≥ 4 dB (ISO 1600) |
| Motion sharpness | MTF @ Nyq/2, v = 5 px/f | ≥ 0.3 |
| Ghosting (subjective) | MOS | ≥ 4.0 |
| Color flickering | Flicker frequency component | < noise floor + 6 dB |
| Edge ghosting | Double-edge pixel ratio | < 2% |

---

## 6 Reference Code

### 6.1 Basic Temporal Noise Reduction Implementation

```python
import numpy as np
import cv2
from typing import Optional, Tuple


class TemporalNR:
    """
    运动自适应时域降噪器（Motion-Adaptive Temporal Noise Reduction）。

    支持逐帧递推，适用于视频流实时处理。
    """

    def __init__(
        self,
        alpha_min: float = 0.10,
        alpha_max: float = 0.95,
        motion_threshold: float = 16.0,
        soft_transition: float = 16.0,
        block_size: int = 16,
        search_range: int = 16,
    ):
        """
        Parameters
        ----------
        alpha_min         : 静止区域混合系数下限（越小降噪越强）
        alpha_max         : 运动区域混合系数上限（越大运动越清晰）
        motion_threshold  : 运动判决帧差阈值（LSB，需根据 ISO 标定）
        soft_transition   : 从静止到运动的过渡宽度（帧差值域）
        block_size        : 块匹配块大小（像素）
        search_range      : 块匹配搜索范围（±像素）
        """
        self.alpha_min = alpha_min
        self.alpha_max = alpha_max
        self.motion_threshold = motion_threshold
        self.soft_transition = soft_transition
        self.block_size = block_size
        self.search_range = search_range
        self._reference_frame: Optional[np.ndarray] = None

    def process_frame(self, frame_yuv: np.ndarray) -> np.ndarray:
        """
        处理单帧，返回时域降噪后的帧。

        Parameters
        ----------
        frame_yuv : 输入帧，YUV420 或 YUV（shape: H×W×3），uint8

        Returns
        -------
        降噪后的帧，同输入格式
        """
        if self._reference_frame is None:
            self._reference_frame = frame_yuv.copy()
            return frame_yuv.copy()

        # 提取亮度分量用于运动估计
        if frame_yuv.ndim == 3:
            Y_cur = frame_yuv[:, :, 0].astype(np.float32)
            Y_ref = self._reference_frame[:, :, 0].astype(np.float32)
        else:
            Y_cur = frame_yuv.astype(np.float32)
            Y_ref = self._reference_frame.astype(np.float32)

        # 运动补偿（使用块匹配）
        Y_ref_aligned = self._block_matching_align(Y_cur, Y_ref)

        # 计算帧差
        diff = np.abs(Y_cur - Y_ref_aligned)

        # 运动自适应混合系数
        alpha = self._compute_alpha(diff)

        # 时域混合
        output = frame_yuv.copy().astype(np.float32)
        ref_aligned = self._reference_frame.copy().astype(np.float32)

        if frame_yuv.ndim == 3:
            alpha_3ch = alpha[:, :, np.newaxis]  # 广播到 3 通道
            output = alpha_3ch * output + (1 - alpha_3ch) * ref_aligned
        else:
            output = alpha * output + (1 - alpha) * ref_aligned

        output = np.clip(output, 0, 255).astype(np.uint8)

        # 更新参考帧
        self._reference_frame = output.copy()
        return output

    def _compute_alpha(self, diff: np.ndarray) -> np.ndarray:
        """
        根据帧差计算每像素混合系数 alpha。
        静止区域 alpha → alpha_min，运动区域 alpha → alpha_max。
        """
        # 归一化：[0, 1]
        motion_degree = np.clip(
            (diff - self.motion_threshold) / self.soft_transition,
            0.0, 1.0
        )
        alpha = self.alpha_min + (self.alpha_max - self.alpha_min) * motion_degree
        return alpha.astype(np.float32)

    def _block_matching_align(
        self,
        cur: np.ndarray,
        ref: np.ndarray,
    ) -> np.ndarray:
        """
        简化块匹配对齐：对每个块找最优平移运动向量，
        将参考帧变形对齐到当前帧坐标系。

        注意：生产环境中使用专用硬件块匹配加速。
        """
        H, W = cur.shape
        bs = self.block_size
        sr = self.search_range
        aligned = ref.copy()

        for y in range(0, H - bs, bs):
            for x in range(0, W - bs, bs):
                cur_block = cur[y:y+bs, x:x+bs]
                best_sad = float('inf')
                best_dy, best_dx = 0, 0

                for dy in range(-sr, sr + 1, 2):  # 步长 2 加速搜索
                    for dx in range(-sr, sr + 1, 2):
                        ry, rx = y + dy, x + dx
                        if ry < 0 or ry + bs > H or rx < 0 or rx + bs > W:
                            continue
                        ref_block = ref[ry:ry+bs, rx:rx+bs]
                        sad = np.sum(np.abs(cur_block - ref_block))
                        if sad < best_sad:
                            best_sad = sad
                            best_dy, best_dx = dy, dx

                # 用最优 MV 填充对齐帧
                ry, rx = y + best_dy, x + best_dx
                ry = np.clip(ry, 0, H - bs)
                rx = np.clip(rx, 0, W - bs)
                aligned[y:y+bs, x:x+bs] = ref[ry:ry+bs, rx:rx+bs]

        return aligned

    def reset(self):
        """重置参考帧（场景切换时调用）"""
        self._reference_frame = None

    def update_iso_params(self, iso: int):
        """
        根据 ISO 值自动更新降噪参数。

        Parameters
        ----------
        iso : 当前曝光 ISO 值
        """
        if iso <= 400:
            self.alpha_min = 0.10
            self.motion_threshold = 12.0
        elif iso <= 1600:
            self.alpha_min = 0.12
            self.motion_threshold = 20.0
        elif iso <= 6400:
            self.alpha_min = 0.15
            self.motion_threshold = 35.0
        else:
            self.alpha_min = 0.20
            self.motion_threshold = 55.0


def compute_temporal_snr(
    frames: list,
    roi: Optional[Tuple[int, int, int, int]] = None,
) -> float:
    """
    计算时域 SNR（Temporal SNR，tSNR），单位 dB。

    Parameters
    ----------
    frames : 静止场景的多帧图像列表（灰度或 BGR，uint8）
    roi    : 感兴趣区域 (x, y, w, h)，None 时使用全图

    Returns
    -------
    tSNR 值（dB）
    """
    if len(frames) < 2:
        raise ValueError("至少需要 2 帧")

    # 提取灰度
    gray_frames = []
    for f in frames:
        if f.ndim == 3:
            gray_frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32))
        else:
            gray_frames.append(f.astype(np.float32))

    stack = np.stack(gray_frames, axis=0)  # shape: (N, H, W)

    if roi is not None:
        x, y, w, h = roi
        stack = stack[:, y:y+h, x:x+w]

    mean_frame = stack.mean(axis=0)
    temporal_std = stack.std(axis=0)

    # 避免除零
    valid = temporal_std > 1e-6
    snr_map = np.zeros_like(mean_frame)
    snr_map[valid] = mean_frame[valid] / temporal_std[valid]

    mean_snr = snr_map[valid].mean()
    tsnr_db = 20.0 * np.log10(mean_snr + 1e-9)
    return float(tsnr_db)


def demo_tnr_pipeline():
    """时域降噪流水线演示"""
    tnr = TemporalNR(alpha_min=0.10, alpha_max=0.95, motion_threshold=16.0)

    # 模拟视频帧序列
    np.random.seed(42)
    base_frame = np.random.randint(80, 180, (480, 640, 3), dtype=np.uint8)
    frames_noisy = []
    frames_denoised = []

    for i in range(30):
        # 添加高斯噪声（模拟 ISO 800）
        noise = np.random.normal(0, 12, base_frame.shape).astype(np.float32)
        noisy = np.clip(base_frame.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        # 第 15 帧模拟运动（局部区域变化）
        if i >= 15:
            noisy[100:200, 200:300] = np.clip(
                base_frame[100:200, 200:300].astype(np.float32) + 50 + noise[100:200, 200:300],
                0, 255
            ).astype(np.uint8)

        frames_noisy.append(noisy)

        # 应用时域降噪
        denoised = tnr.process_frame(noisy)
        frames_denoised.append(denoised)

    # 计算 tSNR
    static_region = (50, 50, 100, 100)  # 静止区域 ROI
    tsnr_before = compute_temporal_snr(frames_noisy[:15], roi=static_region)
    tsnr_after = compute_temporal_snr(frames_denoised[:15], roi=static_region)

    print(f"TNR 前 tSNR: {tsnr_before:.1f} dB")
    print(f"TNR 后 tSNR: {tsnr_after:.1f} dB")
    print(f"tSNR 提升:   {tsnr_after - tsnr_before:.1f} dB")
    return frames_denoised


if __name__ == "__main__":
    demo_tnr_pipeline()
```

---

## References

1. Kokaram, A. C. (1993). *Motion Picture Restoration: Digital Algorithms for Artefact Suppression in Degraded Motion Picture Film and Video*. Springer.

2. Dabov, K., Foi, A., Katkovnik, V., & Egiazarian, K. (2007). Video denoising by sparse 3D transform-domain collaborative filtering. *Proceedings of SPIE*, 6696, 606–606.

3. Buades, A., Coll, B., & Morel, J.-M. (2005). A non-local algorithm for image denoising. *Proceedings of CVPR*, 2, 60–65.

4. Liu, C., & Freeman, W. T. (2010). A high-quality video denoising algorithm based on reliable motion estimation. *Proceedings of ECCV*.

5. Wiegand, T., Sullivan, G. J., Bjontegaard, G., & Luthra, A. (2003). Overview of the H.264/AVC video coding standard. *IEEE Transactions on Circuits and Systems for Video Technology*, 13(7), 560–576.

6. Zoran, D., & Weiss, Y. (2011). From learning models of natural image patches to whole image restoration. *Proceedings of ICCV*, 479–486.

7. Kalman, R. E. (1960). A new approach to linear filtering and prediction problems. *Journal of Basic Engineering*, 82(1), 35–45.

8. Horn, B. K. P., & Schunck, B. G. (1981). Determining optical flow. *Artificial Intelligence*, 17(1–3), 185–203.

---

---

> **Handoff note:** This chapter covers **traditional TNR** methods (BMA / optical flow motion estimation, IIR filtering, Qualcomm MCTF / MTK TNR Node / HiSilicon TNR engineering implementations). Deep learning-based video denoising methods (FastDVDnet / EDVR / RVRT, etc.) and performance comparisons with traditional approaches are covered in **Ch59 (DL Video Denoising & Video ISP)**, which opens with a brief recap of this chapter's traditional baselines.

*End of Chapter 29 | Next chapter: Chapter 30 — Digital Zoom & Image Resampling*
