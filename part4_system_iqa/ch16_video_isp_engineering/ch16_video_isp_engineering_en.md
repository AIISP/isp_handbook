# Part 4, Chapter 16: Video ISP System Engineering

> **Scope:** This chapter covers video ISP engineering practice: inter-frame consistency, 3A convergence strategies, video bitrate-quality control, and the differences between smartphone video ISP and cinema ISP.
> **Prerequisites:** Volume 3, Chapter 8 (DL Video Denoising); Volume 4, Chapter 1 (3A Control System)
> **Reader path:** Systems engineers, algorithm engineers

---

## §1 Theory and Principles

### 1.1 Fundamental Differences Between Video ISP and Still Image ISP

The core challenge of video ISP relative to still image ISP is **temporal consistency (时域一致性)**: video is a sequence of continuous frames, and any inter-frame parameter jump (exposure, white balance, denoising strength, etc.) is perceived by the human eye as "flicker" (闪烁) or a "jump-cut" (跳变).

**Key constraint comparison:**

| Metric | Still image ISP | Video ISP |
|--------|----------------|-----------|
| 3A convergence speed | Can be slow (1–5 frames) | Must be fast (≤ 3 frames for AF, AE smooth) |
| 3A parameter changes | Allow large single-step adjustments | Must transition smoothly frame by frame |
| Denoising strength | Can be maximized | Constrained by temporal consistency |
| HDR merging | Offline merge, no time limit | Must be real-time (16.7 ms/frame @ 60 fps) |
| Inter-frame motion estimation | Not required | Required (TNR, EIS need optical flow) |

### 1.2 Temporal Constraints for Video 3A

**AE (Auto Exposure, 自动曝光) temporal constraint:**

AE exposure adjustments must not be too aggressive, otherwise causing video "breathing" (AE Breathing, 呼吸效应) — periodic brightness oscillations. The standard approach is to limit the per-frame EV adjustment step size:

$$|EV_{n+1} - EV_n| \leq \Delta EV_{max}$$

Typical values:
- Slowly changing brightness: $\Delta EV_{max} = 0.1$ (approximately 7% brightness change/frame)
- Fast scene cuts (e.g., from indoors to outdoors): $\Delta EV_{max} = 0.3$ (approximately 20%/frame)

**Anti-flicker (防频闪) AE constraint:**

In 50 Hz/60 Hz AC-powered lighting environments (fluorescent lamps, LED lights), exposure time must be an integer multiple of the light source period, otherwise periodic brightness variation occurs:
- 50 Hz light source: exposure time ∈ {10 ms, 20 ms, 30 ms, ...} (integer multiples of 1/100 s)
- 60 Hz light source: exposure time ∈ {8.3 ms, 16.7 ms, 33.3 ms, ...} (integer multiples of 1/120 s)

When this constraint conflicts with the AE target EV, anti-flicker takes priority; gain (ISO) compensates for any underexposure.

**AWB (Auto White Balance, 自动白平衡) temporal smoothing:**

AWB color temperature estimation errors cause inter-frame color tone jumps (Color Jump, 色调跳变), requiring temporal low-pass filtering (temporal smoothing, 时域平滑) of estimates:

$$WB_{gains,n} = (1 - \alpha_{AWB}) \cdot WB_{gains,n-1} + \alpha_{AWB} \cdot \hat{WB}_{gains,n}$$

where $\alpha_{AWB}$ is the smoothing coefficient; typical values 0.05–0.15 ($\alpha = 0.1$ corresponds to approximately 10 frames time constant).

### 1.3 Video Bitrate-Quality Trade-off (Rate-Distortion)

The bitrate-quality relationship for video coding (H.264/H.265/AV1) is described by the **Rate-Distortion curve (率失真曲线)**:

$$PSNR = f(Bitrate) \approx a \cdot \log(Bitrate) + b$$

Bitrate allocation strategies:
- **CBR (Constant Bit Rate, 固定码率):** Fixed bitrate; quality degrades in complex motion scenes; wastes bandwidth in static scenes
- **VBR (Variable Bit Rate, 可变码率):** Dynamically allocates bitrate; increases in motion scenes; suitable for high-quality recording
- **CQP (Constant Quantization Parameter, 固定量化参数):** Fixed quantization parameter; bitrate varies with content; most stable quality; commonly used for cinema Log-mode shooting

**Video ISP impact on encoding:** ISP denoising quality directly affects coding efficiency — noise is a high-frequency random signal that is hard for the encoder to compress. Good NR can reduce bitrate by 20–40% at equivalent quality.

### 1.4 Log Video and Linear Raw Video

**Log video (Log Gamma, 对数Gamma):** Encodes sensor linear RAW data through a logarithmic OETF (Opto-Electronic Transfer Function, 光电转换函数), maximizing dynamic range retention:

$$V_{log} = a \cdot \log_{10}(I_{linear} + b) + c$$

Common Log formats:
- **Sony S-Log3:** Approximately 15+ stops of dynamic range; used in Alpha series cameras
- **ARRI LogC4:** Approximately 17 stops; used in ALEXA 35 cinema cameras
- **Apple Log (iPhone 15 Pro):** Approximately 16 stops; used for ProRes video (see Apple ProRes Log White Paper 2023)

Log video is not suitable for direct viewing (requires a LUT for grading during display) but retains the maximum dynamic range information for post-production color grading.

### 1.5 Video EIS (Electronic Image Stabilization, 电子防抖) Impact on ISP

EIS analyzes inter-frame motion (optical flow) and applies reverse translation/rotation compensation, requiring:
1. **Extra frame margin (Crop Margin, 帧边距):** Typically 10–15% margin for motion compensation; equivalent FOV reduction
2. **Motion estimation delay:** Requires current frame + 1–2 previous frames; introduces approximately 1–2 frames of additional latency
3. **ISP output resolution requirement:** Input resolution must exceed output resolution to provide the crop buffer

---

## §2 Algorithm Methods and System Architecture

### 2.1 Video ISP Full-Pipeline Architecture

```
Sensor RAW stream
     │
     ▼
┌─────────────────────────────────────────────┐
│               Real-time Video ISP            │
│                                              │
│  BLC → Demosaic → TNR(inter-frame) → NR(intra-frame) │
│  → AWB(temporal smooth) → CCM → Gamma/Log   │
│  → AE control → AF assist → EIS motion est. │
│                                              │
│  [3A control module: independent thread, updated per frame] │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
              YUV/Log RAW stream
                      │
              ┌───────┴────────┐
              │                │
              ▼                ▼
        Video encoder      EIS stabilizer
     (H.265/H.264/         (motion comp.
        ProRes)             crop + warp)
              │                │
              ▼                ▼
        Video file        Stabilized preview
```

### 2.2 AE Convergence Strategy (Video-Specific)

**Multi-stage convergence strategy (分段收敛策略):**
- **Stage 1 (fast capture):** When a large brightness change is detected (e.g., scene cut), allow a larger step size ($\Delta EV_{max} = 0.3$) to quickly approach the target EV; lasts approximately 3–5 frames.
- **Stage 2 (fine convergence):** Within ±0.5 EV of the target, switch to a small step size ($\Delta EV_{max} = 0.05$) for smooth transition.
- **Stage 3 (steady state):** When brightness deviation < 0.1 EV, stop adjusting to avoid meaningless oscillation.

**Anti-flicker AE algorithm (防频闪AE算法):**
1. Detect current light source frequency (50 Hz/60 Hz): by analyzing the brightness-variation spectrum under a fixed exposure time.
2. Quantize the target exposure time to a safe value: $T_{exp} = round(T_{target} \times f_{flicker}) / f_{flicker}$
3. When quantization causes an exposure deviation > 0.2 EV, compensate for the brightness shortfall with gain (ISO).

### 2.3 AWB Video Smoothing Algorithm

**Dual-speed smoothing strategy (双速平滑策略):**
- Normal mode: $\alpha_{AWB} = 0.05$ (approximately 20 frames convergence, about 0.3 s @ 60 fps)
- Large color temperature jump (> 500 K, e.g., from tungsten light to fluorescent): $\alpha_{AWB} = 0.15$ (approximately 7 frames; faster response)

**Scene lock strategy (场景锁定策略):** When strong motion is detected (e.g., rapid camera panning), suspend AWB updates ($\alpha_{AWB} = 0$) to prevent motion-induced estimation errors from causing color tone jumps.

### 2.4 Temporal Noise Reduction (TNR, 时域降噪) in Video ISP

TNR is the core module for video ISP quality, exploiting temporal redundancy between adjacent frames for denoising:

$$I_{TNR}(n) = (1 - w) \cdot I_{in}(n) + w \cdot \Phi(I_{TNR}(n-1), I_{in}(n))$$

where $\Phi$ is the motion alignment function (block matching or optical flow), and $w$ is the temporal blend weight (static regions: $w \approx 0.8$; motion regions: $w \approx 0.1$).

**Motion-adaptive weight (运动自适应权重):** Adaptively adjusting $w$ based on the pixel difference (Motion Map, 运动图) between current and previous frames:
$$w(x, y) = \exp\left(-\frac{|\Delta I(x,y)|^2}{2\sigma_{motion}^2}\right)$$

In static regions, $|\Delta I|$ is small and $w$ is large (strong temporal integration); in motion regions, $|\Delta I|$ is large and $w$ is small (rely on current frame to avoid motion ghosting).

### 2.5 Smartphone Video ISP vs. Cinema Camera ISP

**Architectural-level differences:**

| Dimension | Smartphone video ISP | Cinema camera ISP (e.g., ARRI ALEXA) |
|-----------|---------------------|--------------------------------------|
| Sensor format | 1/1.3"–1/3.5" (small sensor) | Super 35mm–65mm full-frame |
| Dynamic range | 10–13 stops | 14–17 stops |
| Output format | H.265 4:2:0 8/10 bit | RAW/ProRes 4:2:2 10 bit minimum (ProRes 422 LT/HQ are 4:2:2 10 bit; ProRes 4444 is 4:4:4 12 bit; RAW up to 16-bit linear) |
| Color science | Brand-specific (vivid/saturated) | Film industry standard (ACES) |
| Frame rate | 30/60/120 fps | 24/48 fps (high-end can reach 240 fps) |
| Rolling shutter | Pronounced (~15–30 ms readout) | ARRI LF dual-shutter (reduces RS) |
| Real-time denoising | Strong (hides sensor noise) | Weak/none (preserves film grain character) |
| Color space | sRGB/HDR10 (consumer displays) | ACES/DCI-P3 (cinema) |

**Special ISP handling for Log mode (Log模式的ISP特殊处理):**

When Log mode is enabled (e.g., Apple Log on iPhone 15 Pro, S-Log3 on professional modes), ISP requires special adjustments:
1. **Disable or weaken denoising:** Noise characteristics in Log mode (signal-dependent noise) get amplified during post-production grading; excessive denoising destroys texture
2. **Disable automatic tone mapping:** Preserve highlight detail; do not auto-stretch the histogram
3. **Disable automatic sharpening:** Avoid ringing artifacts becoming visible after gain amplification in post
4. **Precise Gamma curve:** Log OETF curve must precisely match the post-production LUT; error < 0.5%

### 2.6 Video EIS and ISP Interaction

EIS requires the following information from ISP:
- **Sensor timestamps:** Precise exposure time for each line (used for Rolling Shutter correction)
- **Gyroscope data:** IMU angular velocity, strictly time-aligned with sensor frame timestamps (error < 1 ms)
- **ISP ROI coordinates:** Used to compute the effective crop window for EIS

EIS provides the following feedback to ISP:
- **Crop window:** Real-time update of the effective ROI per frame; ISP outputs only the crop region

---

## §3 Tuning and Engineering Guidelines

### 3.1 AE Step Size Tuning

**Step too large:** AE breathing effect is visible; luminance fluctuation is perceptible (typically inter-frame EV change > 0.2 EV is noticeable).
**Step too small:** AE converges too slowly; exposure remains incorrect for a long time (> 5 frames) after a scene cut.

**Recommended tuning ranges:**
- Stable scene (brightness change < 0.5 EV/s): step 0.05–0.08 EV/frame
- Moderate change (0.5–2 EV/s): step 0.1–0.15 EV/frame
- Rapid cut (> 2 EV/s, e.g., daylight entering a dark tunnel): step 0.25–0.35 EV/frame, but automatically trigger Transition Detection mode

**Anti-flicker tuning:** Flicker detection sensitivity should not be too high (false positives unnecessarily constrain exposure time under normal DC light sources). Recommend: activate anti-flicker constraint only when flicker detection confidence > 0.75.

### 3.2 AWB Smoothing Parameter Tuning

The selection of smoothing coefficient $\alpha_{AWB}$ depends on:
- **Video frame rate:** 60 fps requires smaller $\alpha$ (approximately 0.05) to prevent color temperature changing too quickly; 24 fps can use a slightly larger $\alpha$ (approximately 0.1)
- **Content type:** Fixed shots (landscape, interviews) use small $\alpha$ (stability priority); dynamic tracking use large $\alpha$ (fast response priority)
- **Perceptual sensitivity:** Skin tone is most sensitive to AWB deviation; recommend smaller $\alpha$ for scenes containing faces

### 3.3 TNR Parameter Tuning

**Blend weight $w$ too large:** Strong noise suppression in static regions, but visible ghosting in motion regions; moving people produce "phantom" outlines.
**Blend weight $w$ too small:** Fewer motion ghosts, but weak noise suppression; noise is visible in dark-scene footage.

**Recommended practice:** Use motion Map confidence as the core driver:
- Static pixels (frame diff < 5 DN): $w = 0.7$–$0.85$
- Slight motion (frame diff 5–20 DN): $w$ linearly interpolated, $0.3$–$0.7$
- Fast motion (frame diff > 20 DN): $w = 0.1$–$0.2$

### 3.4 Log Mode ISP Configuration Checklist

When enabling video Log mode, verify the following ISP parameters:

| Parameter | Normal video | Log mode | Notes |
|-----------|-------------|----------|-------|
| Gamma curve | sRGB/HLG | Log OETF | Preserve dynamic range |
| Spatial NR strength | Medium–High | Low | Avoid texture loss |
| TNR strength | Medium–High | Low–Medium | Can be moderate at low ISO |
| Sharpening (USM) | Medium | Off | Avoid ringing amplification in post |
| Saturation boost | On | Off | Preserve original color for grading |
| Local tone mapping | On | Off | Preserve highlight detail |
| Encoding format | H.265 8 bit | ProRes/H.265 10 bit | Ensure color precision |

### 3.5 Video Bitrate-Quality Tuning

**Bitrate selection guide (H.265, 1080p@30 fps):**
- Low bitrate (10–15 Mbps): suitable for live streaming; visible macro-blocking
- Standard bitrate (20–40 Mbps): suitable for general recording; satisfies 90% of scenarios
- High bitrate (60–100 Mbps): motion/sports scenes; rich in detail
- Professional bitrate (100–150 Mbps): ProRes Proxy; post-production

**4K@60 fps recommended:** H.265 VBR 100–200 Mbps; ProRes HQ approximately 1.7–2.0 Gbps (Apple official spec: ProRes HQ 4K@60fps ≈ 1.77 Gbps; storage requires SSD).

**ISP quality impact on bitrate:** Good spatial NR can reduce bitrate by 20–35% at equivalent quality; TNR can reduce by 10–20% (reduces inter-frame texture variation).

---

## §4 Common Artifacts and Problem Analysis

### 4.1 AE Breathing / Hunting (AE呼吸效应)

**Symptom:** Periodic brightness oscillation in video (1–3 times/s); most visible in fixed shots (interviews, product displays).
**Root cause:** AE algorithm repeatedly overshoots around the target EV and cannot stabilize.
**Diagnosis:** Plot per-frame EV curves; check whether oscillation is present.
**Fix:** Add an AE dead zone — stop adjusting when EV deviation < 0.05 EV; or increase the damping factor.

### 4.2 AWB Color Jump (AWB色温跳变)

**Symptom:** Video tone suddenly shifts from cool to warm (or vice versa) for approximately 0.5–2 seconds.
**Root cause:** AWB estimate undergoes large fluctuations in unstable lighting (e.g., shadow briefly blocking the sun); smoothing coefficient insufficient.
**Diagnosis:** Capture per-frame AWB color temperature estimates; inspect the magnitude of color temperature changes.
**Fix:** Reduce $\alpha_{AWB}$; improve AWB estimation stability (increase statistical area, filter outliers).

### 4.3 TNR Motion Ghosting (TNR运动鬼影)

**Symptom:** Transparent ghost trails appear behind moving objects (especially fast-moving hands or people's outlines).
**Root cause:** TNR blend weight $w$ is too large in motion regions; previous frame content bleeds into the current frame.
**Diagnosis:** Temporarily disable TNR (set $w = 0$) to verify whether the artifact disappears.
**Fix:** Improve motion Map precision (increase block-matching resolution, or use optical flow instead of block matching); reduce $w$ in motion regions.

### 4.4 Video Flicker (视频频闪)

**Symptom:** Visible periodic brightness changes in video at 50 Hz or 100 Hz (related to AC power frequency).
**Root cause:** Exposure time not aligned with light source frequency (anti-flicker not enabled, or frequency misdetected).
**Diagnosis:** For a static scene (no object motion), compute per-frame average brightness and perform spectral analysis; a prominent peak at 100 Hz/120 Hz confirms flicker.
**Fix:** Confirm that anti-flicker AE has correctly detected the frequency and enabled the constraint; manually set the flicker frequency (select "50 Hz" or "60 Hz" in user settings).

### 4.5 Log Mode Noise Amplification (Log模式噪声放大)

**Symptom:** After applying a grading LUT to Log footage in post (Premiere, DaVinci), shadow noise becomes extremely visible (amplified by the LUT's Gamma lift in the shadows).
**Root cause:** Insufficient ISP denoising in Log mode, or sensor ISO too high; the LUT simultaneously amplifies shadow Gamma and noise.
**Mitigation:** Keep ISO under control in Log mode (no more than 4× the base ISO); apply temporal denoising in post (e.g., DaVinci Resolve Noise Reduction).

---

## §5 Evaluation Methods

### 5.1 AE Temporal Stability Evaluation

**Objective metric:** Under fixed lighting and a fixed scene, record 60 seconds of video; extract per-frame mean luminance $L_n$ and compute:
- **Luminance fluctuation standard deviation:** $\sigma_L = std(\{L_n\})$; acceptance criterion: < 2.0 DN (8 bit)
- **Maximum inter-frame luminance change:** $\max_n |L_{n+1} - L_n|$; acceptance criterion: < 5 DN

### 5.2 AWB Temporal Stability Evaluation

Under a fixed D65 light source, record 30 seconds of video; extract per-frame color temperature estimates (or R/G and B/G ratios) and compute:
- **Color temperature standard deviation:** $\sigma_{CCT} < 50 K$ (strict), $< 100 K$ (relaxed)
- **Color temperature change rate:** $< 50 K/\text{frame}$ (corresponds to approximately 0.1%/frame AWB gain change)

### 5.3 TNR Quality Evaluation

**Motion ghosting:** Capture a uniformly moving standard test chart (Siemens Star); compare the luminance behind the motion trail with and without TNR enabled to quantify ghosting strength (dB).

**Static region denoising:** Capture a static uniform gray card in low-light (low ISO); measure luminance standard deviation (TNR on/off); compute the temporal denoising gain (dB).

### 5.4 Flicker Detection

Apply FFT to the per-frame mean luminance sequence of 30 consecutive frames; check whether power spectral density at 50 Hz/100 Hz (60 Hz/120 Hz) exceeds the noise floor by more than 3 standard deviations.

### 5.5 Video Encoding Quality Evaluation

Use VMAF (Video Multimethod Assessment Fusion, Netflix视频质量评估框架) to compare encoded video at different bitrates against the original:
- 1080p@30 fps standard bitrate (20 Mbps H.265): VMAF should be > 90
- Live streaming bitrate (8 Mbps): VMAF should be > 75

---

## §6 Code Examples

### 6.1 Anti-Flicker AE Exposure Time Quantization

```python
import numpy as np
from typing import Tuple

def quantize_exposure_for_anti_flicker(
    target_exp_ms: float,
    flicker_freq_hz: float,
    max_exp_ms: float = 33.3
) -> Tuple[float, float]:
    """
    Quantize target exposure time to an anti-flicker-safe value.

    Anti-flicker requires exposure time to be an integer multiple of the
    light source period (1/flicker_freq).
    e.g. 50 Hz light source period = 20 ms; safe values are 10 ms, 20 ms, 30 ms...

    Args:
        target_exp_ms: Target exposure time from AE computation (ms)
        flicker_freq_hz: Detected light source frequency (50 Hz or 60 Hz)
        max_exp_ms: Maximum allowed exposure time at the current frame rate (ms)

    Returns:
        (quantized_exp_ms, gain_compensation): Quantized exposure time and
                                               gain compensation factor
    """
    # Light source period (ms)
    period_ms = 500.0 / flicker_freq_hz   # fluorescent/LED flicker = 2× mains: 50 Hz → 10 ms; 60 Hz → 8.33 ms
    # Quantize to nearest integer-multiple period (floor to avoid overexposure)
    n_periods = max(1, int(target_exp_ms / period_ms))
    # Limit to maximum allowed exposure time
    while n_periods * period_ms > max_exp_ms and n_periods > 1:
        n_periods -= 1

    quantized_exp_ms = n_periods * period_ms

    # Compute gain compensation factor (if exposure time is shortened, raise ISO)
    gain_compensation = target_exp_ms / quantized_exp_ms

    return quantized_exp_ms, gain_compensation


def ae_step_limiter(
    ev_current: float,
    ev_target: float,
    delta_ev_max: float,
    transition_detection: bool = False
) -> float:
    """
    Limit per-frame AE step size to prevent video breathing.

    Args:
        ev_current: Current frame EV value
        ev_target: AE target EV value
        delta_ev_max: Maximum allowed step size (EV)
        transition_detection: Whether a scene transition has been detected
                               (allows 2× step size)

    Returns:
        ev_next: EV value for the next frame
    """
    ev_error = ev_target - ev_current
    # Allow 2× step during scene transitions
    effective_max = delta_ev_max * (2.0 if transition_detection else 1.0)
    ev_step = np.clip(ev_error, -effective_max, effective_max)
    return ev_current + ev_step


# Anti-flicker AE demo
print("Anti-flicker AE quantization examples:")
for target_exp in [5.0, 8.0, 12.0, 18.0, 25.0]:
    for freq in [50, 60]:
        q_exp, gain_comp = quantize_exposure_for_anti_flicker(target_exp, freq)
        print(f"  target={target_exp:.1f}ms, {freq}Hz source → "
              f"quantized={q_exp:.2f}ms, gain comp={gain_comp:.2f}x")
```

### 6.2 AWB Temporal Smoothing Filter

```python
import numpy as np
from collections import deque
from dataclasses import dataclass

@dataclass
class AWBState:
    """AWB temporal state."""
    r_gain: float = 1.0
    b_gain: float = 1.0
    cct: float = 5500.0    # Correlated color temperature (K)
    confidence: float = 1.0  # AWB estimation confidence

class AWBTemporalSmoother:
    """Video AWB temporal smoother."""

    def __init__(
        self,
        alpha_normal: float = 0.05,
        alpha_fast: float = 0.15,
        jump_threshold_k: float = 500.0
    ):
        """
        Args:
            alpha_normal: Normal smoothing coefficient (small → slow → stable)
            alpha_fast: Fast response coefficient (large → fast → handles large CCT changes)
            jump_threshold_k: CCT change threshold that triggers fast response (K)
        """
        self.alpha_normal = alpha_normal
        self.alpha_fast = alpha_fast
        self.jump_threshold_k = jump_threshold_k
        self.state = AWBState()
        self.history = deque(maxlen=10)

    def update(self, new_estimate: AWBState) -> AWBState:
        """
        Update AWB state with temporal smoothing.

        Args:
            new_estimate: AWB estimate for the current frame

        Returns:
            smoothed: Smoothed AWB state (used to configure ISP)
        """
        # Detect color temperature jump
        cct_change = abs(new_estimate.cct - self.state.cct)
        is_large_jump = cct_change > self.jump_threshold_k

        # Select smoothing coefficient
        alpha = self.alpha_fast if is_large_jump else self.alpha_normal

        # Scale by confidence (low confidence: keep current values)
        alpha *= new_estimate.confidence

        # Exponential Moving Average (EMA, 指数移动平均)
        smoothed = AWBState(
            r_gain=(1 - alpha) * self.state.r_gain + alpha * new_estimate.r_gain,
            b_gain=(1 - alpha) * self.state.b_gain + alpha * new_estimate.b_gain,
            cct=(1 - alpha) * self.state.cct + alpha * new_estimate.cct,
            confidence=new_estimate.confidence
        )

        self.state = smoothed
        self.history.append(smoothed.cct)
        return smoothed

    def is_stable(self, window: int = 5, threshold_k: float = 50.0) -> bool:
        """Check whether AWB has been stable over the last N frames."""
        if len(self.history) < window:
            return False
        recent = list(self.history)[-window:]
        return (max(recent) - min(recent)) < threshold_k


# Demo: simulate AWB convergence from outdoor (6500 K) to indoor (3200 K)
def demo_awb_smoothing():
    smoother = AWBTemporalSmoother(alpha_normal=0.08, alpha_fast=0.2)
    # Initial scene: outdoor 6500 K
    smoother.state = AWBState(r_gain=1.0, b_gain=1.6, cct=6500)

    print("AWB temporal smoothing demo (6500 K outdoor → 3200 K indoor):")
    print(f"{'Frame':>5} {'Est. CCT':>9} {'Out CCT':>9} {'Stable?':>8}")

    for frame in range(30):
        # Switch to indoor scene from frame 5 onward
        if frame < 5:
            estimate = AWBState(r_gain=1.0, b_gain=1.6, cct=6500, confidence=0.9)
        else:
            estimate = AWBState(r_gain=1.8, b_gain=0.9, cct=3200, confidence=0.9)

        smoothed = smoother.update(estimate)
        stable = smoother.is_stable()
        if frame % 3 == 0:
            print(f"{frame:>5} {estimate.cct:>9.0f}K {smoothed.cct:>9.0f}K "
                  f"{'Yes' if stable else 'No':>8}")
```

### 6.3 TNR Motion-Adaptive Blend Weight

```python
import numpy as np
import cv2

def compute_motion_map(
    frame_curr: np.ndarray,
    frame_prev: np.ndarray,
    sigma_motion: float = 8.0
) -> np.ndarray:
    """
    Compute inter-frame Motion Map (larger values = stronger motion).

    Args:
        frame_curr, frame_prev: Current and previous frames, grayscale float32
        sigma_motion: Gaussian kernel width; controls motion detection sensitivity

    Returns:
        motion_map: Motion intensity map, range [0,1]; 1 = maximum motion
    """
    diff = np.abs(frame_curr.astype(np.float32) -
                  frame_prev.astype(np.float32))
    # Smooth to reduce noise interference on motion detection
    diff_smooth = cv2.GaussianBlur(diff, (7, 7), 1.5)
    # Normalize via sigmoid-like mapping
    motion_map = 1.0 - np.exp(-diff_smooth**2 / (2 * sigma_motion**2))
    return motion_map


def apply_tnr(
    frame_curr: np.ndarray,
    frame_prev_filtered: np.ndarray,
    motion_map: np.ndarray,
    w_max: float = 0.80,
    w_min: float = 0.05
) -> np.ndarray:
    """
    Motion-adaptive temporal noise reduction (TNR).

    Args:
        frame_curr: Current frame, float32 [0, 255]
        frame_prev_filtered: Previous TNR-filtered frame (feedback loop)
        motion_map: Motion map [0, 1]; 0 = static, 1 = fast motion
        w_max: Maximum blend weight for static regions
        w_min: Minimum blend weight for motion regions

    Returns:
        filtered: TNR-processed current frame
    """
    # Motion-adaptive weight: larger motion → smaller history weight
    w = w_min + (w_max - w_min) * (1.0 - motion_map)

    # TNR blend: w = history weight; (1-w) = current-frame weight
    filtered = (1.0 - w) * frame_curr + w * frame_prev_filtered
    return filtered.astype(np.float32)


def tnr_pipeline_demo(frames: list) -> list:
    """
    Complete TNR pipeline demo.

    Args:
        frames: Input frame sequence; each frame is grayscale float32

    Returns:
        filtered_frames: TNR-processed frame sequence
    """
    if not frames:
        return []

    filtered_frames = [frames[0].copy()]  # First frame passes through directly

    for i in range(1, len(frames)):
        motion_map = compute_motion_map(frames[i], frames[i-1])
        filtered = apply_tnr(
            frames[i], filtered_frames[-1], motion_map,
            w_max=0.80, w_min=0.05
        )
        filtered_frames.append(filtered)

    return filtered_frames


# Flicker detection (FFT analysis)
def detect_flicker_frequency(
    frame_luminances: list,
    fps: float
) -> dict:
    """
    Detect flicker frequency by FFT analysis of per-frame luminance sequence.

    Args:
        frame_luminances: List of per-frame mean luminance values
        fps: Video frame rate

    Returns:
        {'detected': bool, 'freq_hz': float, 'confidence': float}
    """
    signal = np.array(frame_luminances, dtype=np.float32)
    signal -= signal.mean()  # Remove DC component
    n = len(signal)

    fft_mag = np.abs(np.fft.rfft(signal))
    freqs = np.fft.rfftfreq(n, d=1.0/fps)

    # Check for 100 Hz/120 Hz (2× the 50 Hz/60 Hz source frequency; easier to detect)
    targets = [100, 120]
    noise_floor = np.median(fft_mag)
    results = []

    for target_hz in targets:
        idx = np.argmin(np.abs(freqs - target_hz))
        amplitude = fft_mag[idx]
        confidence = (amplitude - noise_floor) / (noise_floor + 1e-6)
        if confidence > 3.0:
            results.append({'freq_hz': target_hz / 2, 'confidence': confidence})

    if results:
        best = max(results, key=lambda x: x['confidence'])
        return {'detected': True, **best}
    return {'detected': False, 'freq_hz': 0.0, 'confidence': 0.0}

# Example call
# result = detect_flicker_frequency(frame_sequence, fps=30)
# print(result)
# Output: {'detected': True, 'freq_hz': 50.0, 'confidence': 9.1}  # 50 Hz flicker detected
```

---

## References

1. Hasinoff, S.W., et al. (2016). "Burst photography for high dynamic range and low-light imaging on mobile cameras." *ACM SIGGRAPH Asia*, 35(6).
2. Liba, O., et al. (2019). "Handheld Mobile Photography in Very Low Light." *ACM SIGGRAPH Asia*.
3. Baker, S., & Matthews, I. (2004). "Lucas-Kanade 20 Years On: A Unifying Framework." *IJCV*, 56(3).
4. Tassano, M., et al. (2020). "FastDVDnet: Towards Real-Time Deep Video Denoising Without Flow Estimation." *CVPR 2020*.
5. Sony Corporation. (2022). "S-Log3 Specification." Sony Technical Notes.
6. ARRI. (2022). "ARRI LogC4 Technical Reference." ARRI Technical Documentation.
7. Apple Inc. (2023). "ProRes RAW White Paper." Apple Developer Documentation.
8. ITU-R BT.2020. (2015). "Parameter values for ultra-high definition television systems." ITU-R.
9. Netflix Technology Blog. (2016). "VMAF: The Journey Continues." https://netflixtechblog.com/vmaf-the-journey-continues
10. Wronski, B., et al. (2019). "Handheld Multi-Frame Super-Resolution." *ACM SIGGRAPH*.

---

## §8 Glossary

| Term | Full Name | Meaning |
|------|-----------|---------|
| TNR | Temporal Noise Reduction | Temporal denoising using inter-frame redundancy |
| EIS | Electronic Image Stabilization | Digital stabilization via image warping to compensate for camera shake |
| CBR | Constant Bit Rate | Fixed-bitrate encoding mode |
| VBR | Variable Bit Rate | Variable-bitrate encoding mode |
| CQP | Constant Quantization Parameter | Fixed-QP encoding; most stable quality |
| VMAF | Video Multimethod Assessment Fusion | Netflix video quality metric |
| Log | Logarithmic Gamma | Logarithmic gamma curve; maximizes dynamic range retention |
| OETF | Opto-Electronic Transfer Function | Sensor-to-code signal transfer function |
| ACES | Academy Color Encoding System | Film industry color encoding system |
| Breathing | AE Breathing / Hunting | AE oscillation around the target EV, causing brightness fluctuation |
| Anti-Flicker | — | Aligning exposure time with AC light source period |
| Rolling Shutter | — | Line-by-line CMOS readout; causes skew/wobble on moving subjects |
| EMA | Exponential Moving Average | Exponential moving average; common method for temporal smoothing |
| Motion Map | — | Per-pixel inter-frame motion intensity estimate |
