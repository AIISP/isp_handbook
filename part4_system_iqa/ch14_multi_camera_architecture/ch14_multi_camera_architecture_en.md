# Part 4, Chapter 14: Multi-Camera System Architecture Design and Cross-Path Color Consistency

> **Scope:** This chapter covers multi-camera system architecture (primary + ultra-wide + telephoto + ToF (Time-of-Flight)), cross-camera color consistency, and multi-camera ISP pipeline synchronization.
> **Prerequisites:** Volume 2, Chapter 22 (Multi-Camera Fusion); Volume 4, Chapter 1 (3A Control System)
> **Reader path:** Systems engineers

---

## §1 Theory and Principles

### 1.1 Engineering Drivers for Multi-Camera Systems

Modern flagship smartphones universally adopt multi-camera systems with 3–5 lenses. The core drivers are three:

1. **Focal length coverage:** Ultra-wide (0.5× / 0.6×) + primary (1×) + mid-range (2×–3×) + telephoto (5×–10×), covering 0.5× to 10× optical zoom.
2. **Computational photography (计算摄影):** Multi-frame fusion (primary + auxiliary), large aperture (bokeh), night-scene fusion — achieving image quality unreachable by a single camera.
3. **Depth sensing:** ToF (Time-of-Flight, 飞行时间) or structured light providing depth maps for portrait segmentation, AR anchoring, and autofocus assistance.

**Typical 4-camera configuration (reference: 2024 flagship):**

| Camera | Equivalent focal length | Sensor size | Pixels | Aperture | Function |
|--------|------------------------|-------------|--------|----------|----------|
| Ultra-wide | 14 mm | 1/3.5" | 12 MP | f/2.2 | Landscape/architecture/wide-angle video |
| Primary | 24 mm | 1/1.3" | 50 MP | f/1.8 | General photography workhorse |
| Mid-range | 70 mm | 1/3.5" | 12 MP | f/2.8 | Portrait/medium distance |
| Telephoto | 200 mm | 1/4.4" | 12 MP | f/6.3 | Long telephoto/zoom |

### 1.2 Multi-Camera Hardware Interfaces and SoC Lane Limits

**MIPI CSI-2 (Mobile Industry Processor Interface Camera Serial Interface 2) interface:** Each camera is connected to the SoC ISP via a dedicated MIPI CSI-2 path. Mainstream SoCs (Qualcomm SM8750, Apple A18 Pro) typically support 3–4 physical MIPI interfaces, each with up to 4-lane (D-PHY) or 8-lane (C-PHY) connections.

**Virtual Channel (VC, 虚拟通道) technology:** When physical MIPI interfaces are insufficient, MIPI CSI-2 virtual channels can multiplex multiple data streams over a single physical path (up to 4 VCs), but bandwidth is shared:

$$BW_{total} = \frac{\sum_{i} W_i \times H_i \times FPS_i \times BPP_i}{\eta_{MIPI}}$$

where $\eta_{MIPI}$ is the MIPI protocol efficiency (typically approximately 85%).

**ISP pipeline count:** SoC internal ISP hardware typically has 2–3 independent processing pipelines. With multiple cameras, these must be time-shared or run simultaneously; the primary limiting factor is **memory bandwidth (内存带宽)**.

### 1.3 Multi-Camera Time Synchronization Principles

Multi-camera fusion (e.g., night-scene multi-frame, HDR merging) requires exposure frames from multiple cameras to be strictly time-aligned. Main synchronization schemes:

**Master-Slave hardware sync (主从硬件同步):** The master camera's FSIN (Frame Sync Input/Output, 帧同步信号) outputs a frame sync signal, driving slave cameras to begin exposure at the same moment:

$$|T_{exp\_master} - T_{exp\_slave}| < 1 \text{ line time} \approx 10\text{–}30\mu s$$

**Software timestamp alignment (软件时间戳对齐):** ISP hardware stamps each frame with a high-precision timestamp (μs-level). During post-processing, the most closely matched pair of frames is selected for fusion. This is suitable for offline processing that does not require real-time performance.

### 1.4 Smooth Zoom Switching Theory

Switching from the primary camera to the telephoto (or ultra-wide) involves significant differences in FOV, distortion, and tone. A direct cut produces a conspicuous "jump."

**Zoom continuity conditions (视觉连续性条件):** At the switch instant $t_0$, the following must be satisfied:
- **Luminance continuity:** $|L_{out}(t_0^-) - L_{out}(t_0^+)| < \Delta L_{jnd}$ (JND ≈ 1/3 EV)
- **Tone continuity:** $\Delta E_{2000}(AWB_{out,before}, AWB_{out,after}) < 2.0$
- **Geometric continuity:** The FOV transition across the switch must be interpolated over 2–3 frames

---

## §2 Algorithm Methods and System Architecture

### 2.1 Multi-Camera ISP System Architecture

**Distributed ISP architecture (分布式ISP架构) (dominant in modern flagships):**

```
                    ┌─────────────────────────────────────────┐
                    │              Application Processor        │
┌──────────┐        │  ┌─────┐   ┌─────┐   ┌─────┐           │
│Ultra-wide│─MIPI──►│  ISP │   │ ISP │   │ ISP │           │
└──────────┘        │  #0   │   │ #1  │   │ #2  │           │
┌──────────┐        │  └──┬──┘   └──┬──┘   └──┬──┘           │
│ Primary  │─MIPI──►│     └─────────┴──────────┘             │
└──────────┘        │              │ DDR Interface              │
┌──────────┐        │         ┌────▼────┐                      │
│Telephoto │─MIPI──►│         │ ISP HW  │                      │
└──────────┘        │         │ Shared  │                      │
┌──────────┐        │         │ Buffer  │                      │
│  ToF     │─MIPI──►│         └────┬────┘                      │
└──────────┘        │              │                            │
                    │         ┌────▼────┐                      │
                    │         │  CPU/   │                      │
                    │         │  GPU/   │                      │
                    │         │  NPU    │                      │
                    └─────────────────────────────────────────┘
```

### 2.2 Cross-Camera Color Consistency Correction

**Problem description:** Different cameras produce visually perceptible color differences in identical scenes due to optical characteristics (lens transmittance, coatings), sensor spectral response curves, and OTP (One-Time-Programmable, 一次性可编程标定数据) variations. The color difference $\Delta E$ can reach 3–8.

**Cross-camera color matching algorithm (Cross-Camera Color Calibration, 跨摄色彩匹配算法):**

Using the primary camera as reference, correct auxiliary camera output with a linear transform (3×3 CCM):

$$\begin{bmatrix} R' \\ G' \\ B' \end{bmatrix}_{aux} = M_{aux \to main} \cdot \begin{bmatrix} R \\ G \\ B \end{bmatrix}_{aux}$$

where $M_{aux \to main}$ is solved by minimizing $\Delta E_{2000}$ between primary and auxiliary camera outputs on a standard color chart (X-Rite ColorChecker 24-patch) using least squares.

**Dynamic white balance consistency:** When multiple cameras operate simultaneously, all cameras must be forced to use the **same AWB gains** (derived from the primary camera's AWB estimate). Each camera estimating AWB independently is prohibited, to prevent color temperature jumps.

**Cross-camera AWB CCT mismatch quantification:** Due to differences in spectral transmittance curves, sensor spectral responses, and coating characteristics between ultra-wide and telephoto lenses, even when using the same AWB target, different cameras can exhibit a **200–500 K CCT bias** for the same scene (the ultra-wide vs. telephoto pair is the most typical case). This bias causes a visually perceptible tone jump (ΔE > 2.0) on a direct cut. Compensation therefore requires per-color-temperature-node cross-camera CCMs (see §2.2) calibrated at multiple nodes (2800 K, 4000 K, 6500 K) and interpolated at runtime based on the primary camera's AWB color temperature estimate — a single global CCM is insufficient.

### 2.3 Smooth Zoom Switching System

**Switch decision (切换判决):** Based on the current focal length request, determine whether a cross-camera switch is needed:

```
User focal length request z → determine whether current physical camera can cover it
                 → if z < z_threshold_wide: switch to ultra-wide
                 → if z > z_threshold_tele: switch to telephoto
                 → otherwise: digital zoom on current camera
```

**Smooth transition strategy (切换过渡策略):**

1. **Alpha blending (Crossfade, Alpha混合):** Within 2 frames before and after the switch, apply alpha blending:
$$I_{out}(t) = (1 - \alpha(t)) \cdot I_{from}(t) + \alpha(t) \cdot I_{to}(t)$$
where $\alpha(t)$ linearly increases from 0 to 1.

2. **Exposure pre-alignment (曝光预对齐):** Start adjusting the target camera's exposure N frames (typically 3–5) before the switch to match the primary camera, reducing luminance jump.

3. **Geometric alignment (几何对齐):** Use a pre-calibrated inter-camera homography matrix (Homography) to align the auxiliary camera image to the primary camera viewpoint before blending.

### 2.4 MIPI Virtual Channel (VC) Multiplexing

**Use case:** When ultra-wide and depth sensor share the same MIPI physical path, VC IDs distinguish data streams:

```
Physical MIPI path:  [VC0: Ultra-wide RAW12] [VC1: ToF depth] [VC2: ToF confidence] ...
ISP parsing:         Demux by VC ID to corresponding ISP modules
```

**Bandwidth estimate (4K@30 fps example):**
$$BW = 3840 \times 2160 \times 30 \times 10 \text{ bit} \approx 2.49 \text{ Gbps}$$

MIPI CSI-2 4-lane D-PHY @4.5 Gbps/lane has a theoretical bandwidth of 18 Gbps — ample headroom. However, when multiple streams are transmitted simultaneously, total bandwidth must be calculated precisely to avoid saturation.

### 2.5 ToF Depth Sensor ISP Integration

ToF sensor output is **raw time-of-flight data** (Raw ToF), requiring a dedicated ISP module:

1. **ToF correction:** Multi-path interference (MPI, 多径干扰) removal, thermal drift correction, pixel gain correction
2. **Depth computation:** $d = \frac{c \cdot \Delta\phi}{4\pi f_{mod}}$, where $\Delta\phi$ is the phase difference and $f_{mod}$ is the modulation frequency
3. **Depth filtering:** Bilateral filtering (edge-preserving denoising), temporal filtering (stabilizing the depth map)
4. **Alignment:** Spatially align the ToF depth map to the RGB camera (extrinsic calibration + reprojection)

### 2.6 Multi-Camera 3A Linkage

**AE linkage (AE联动):** The EV target for all cameras is determined by a unified scene brightness estimate. Each camera independently adjusts its exposure parameters within its own aperture/ISO range, but the final image brightness target is shared.

**AF linkage (AF联动):** The primary camera's focus-distance estimate can be shared with other cameras, and the ToF depth map provides full-scene depth information to assist rapid autofocus on all cameras (Depth-Assisted AF, 深度辅助对焦).

---

## §3 Tuning and Engineering Guidelines

### 3.1 OTP Calibration Data Management

Each camera is programmed with OTP data at the factory, including:
- **LSC (Lens Shading Correction, 镜头阴影校正):** Per-channel gain tables (typically 16×16 or 32×32 grids)
- **WB calibration data:** AWB gain baselines under standard illuminants (D65/A light)
- **CCM:** Color correction matrix under standard illuminants

**Cross-camera OTP management principle:** Maintain a "primary camera reference coordinate system" at the system level. All auxiliary camera OTPs are expressed as "offsets relative to the primary camera," making it easy to update auxiliary camera calibration when the primary camera is upgraded.

### 3.2 Cross-Camera Color Matching Calibration Procedure

1. **Standard environment:** D65 illuminant (precise CCT ≈ 6504 K; note: 5000–6500 K is a broad daylight range description — D65 is specifically 6504 K, D50 is 5003 K; do not confuse the two), illuminance 800–1200 lux, using an X-Rite ColorChecker Classic 24-patch chart.
2. **Simultaneous capture:** All cameras capture the chart simultaneously, ensuring identical lighting conditions.
3. **ROI alignment:** Use color chart corner detection to precisely match patch ROIs across cameras.
4. **Solve CCM:** For each color patch, minimize $\sum_i \Delta E_{2000}(C_{main,i}, M \cdot C_{aux,i})$.

**Acceptance criterion:** After correction, primary-auxiliary color difference $\bar{\Delta E}_{2000} < 2.0$, per-patch maximum $\Delta E_{2000,max} < 4.0$.

### 3.3 Zoom Switching Threshold Tuning

Setting the switching threshold requires balancing:
- **Too early:** Less digital zoom (better quality) but frequent switching degrades user experience
- **Too late:** More digital zoom (poorer quality) but fewer switches

**Recommended strategy (primary at 1×, telephoto at 3×):**
- Primary to telephoto: switch at 2.8× (0.2× margin; cover with primary digital zoom)
- Telephoto back to primary: switch at 2.5× (0.3× hysteresis to prevent oscillation — Hysteresis, 滞后策略)
- In high-shake conditions, widen the hysteresis zone (±0.3× → ±0.5×)

### 3.4 Multi-Pipeline ISP Memory Bandwidth Optimization

When multiple ISP pipelines run simultaneously, memory bandwidth often becomes the bottleneck:

**Optimization strategies:**
1. **Interleaving (交错处理):** Multiple ISP pipelines interleave DDR accesses to avoid simultaneous read/write conflicts.
2. **Internal SRAM cache:** Cache frequently-accessed data (LSC LUT, 3A statistics) in ISP-internal SRAM to reduce DDR accesses.
3. **Reduce auxiliary ISP bit depth:** For auxiliary cameras that only assist metering/focus (not active capture), reduce processing bit depth (e.g., 10 bit → 8 bit) to save bandwidth.
4. **Asynchronous wake-up (异步唤醒):** Wake the target camera only when the zoom ratio approaches a switching threshold; keep other cameras in low-power standby otherwise.

### 3.5 ToF-RGB Alignment Error Calibration

Sources of spatial alignment error between ToF depth map and RGB:
- **Extrinsic error:** Calibration error for the relative pose (6 DoF extrinsics) between ToF and RGB cameras
- **Temporal error:** Misaligned timestamps between ToF and RGB frames (recommended < 1 ms)
- **Resolution mismatch:** ToF sensors are typically low-resolution (e.g., 320×240); the depth map must be upsampled to match RGB resolution

**Acceptance criterion:** Depth alignment error < 5 cm at 1 m; < 15 cm at 3 m.

---

## §4 Common Artifacts and Problem Analysis

### 4.1 Zoom Switching Jerk (变焦切换跳变)

**Symptom:** When zooming near the switching threshold, an instantaneous jump in brightness, tone, or sharpness occurs.
**Root cause:** Large exposure parameter discrepancy before/after switch (luminance jump), AWB gain discrepancy (tone jump), or geometric alignment error (content jump).
**Fix:** Strengthen pre-switch alignment (3–5 frames early exposure alignment), increase the hysteresis interval, add more alpha-blend transition frames.

### 4.2 Cross-Camera Color Inconsistency (跨摄色彩不一致)

**Symptom:** During continuous zoom, the same object shows a perceptible color shift when the camera switches (skin-tone shifts are most noticeable).
**Root cause:** Cross-camera CCM calibration error, or CCM cannot fully match at different color temperatures.
**Fix:** Calibrate a separate CCM at multiple color temperature nodes (2800 K, 4000 K, 6500 K) and interpolate based on AWB color temperature at run time.

### 4.3 Multi-Camera Ghost Artifacts (双摄"鬼影")

**Symptom:** Multi-camera fusion images exhibit double contours or transparent overlapping shadows.
**Root cause:** Frame timestamps from the two camera pipelines are not aligned, or a moving object shifts beyond the alignment tolerance between frames.
**Fix:** Disable fusion in motion regions (detected via optical flow or frame differencing); use a single frame from the primary camera directly.

### 4.4 ToF Depth Flying Pixels (ToF深度边缘飞点)

**Symptom:** Depth values at object edges in the depth map contain noise outliers (flying pixels, 飞点) that degrade effects such as portrait background blur.
**Root cause:** ToF pixels receive mixed light from foreground and background (mixed pixel, 混合像素); phase ambiguity produces incorrect depth values.
**Fix:** Use dual-frequency ToF (two modulation frequencies) and filter flying pixels with consistency checks; or apply RGB texture-guided depth upsampling.

### 4.5 MIPI Virtual Channel Data Corruption (MIPI虚拟通道数据错乱)

**Symptom:** One camera stream exhibits in-frame data anomalies (certain rows display data from another camera).
**Root cause:** Incorrect VC ID configuration, or MIPI timing instability causing packet mixing.
**Diagnosis:** Use a MIPI protocol analyzer (e.g., Tektronix DSA8300) to capture physical-layer waveforms and inspect VC fields.

---

## §5 Evaluation Methods

### 5.1 Cross-Camera Color Consistency Evaluation

**Standard test:** Capture an X-Rite ColorChecker under D65 illuminant; measure L*a*b* values for each patch from primary and auxiliary cameras:
$$\Delta E_{2000}^{avg} = \frac{1}{N}\sum_{i=1}^{N} \Delta E_{2000}(C_{main,i}, C_{aux,i})$$
**Acceptance criterion:** $\Delta E_{2000}^{avg} < 2.0$, $\Delta E_{2000}^{max} < 4.0$

### 5.2 Zoom Switching Smoothness Evaluation

**Objective metrics:** In a continuous-zoom video, measure the step changes in brightness, color temperature, and sharpness within one frame before and after each switch:
- Luminance: $|\Delta EV| < 0.3$
- Color temperature: $|\Delta CCT| < 200 K$
- Sharpness (edge response MTF50): change < 15%

**Subjective evaluation:** 10 observers watch the zoom-switching video on a calibrated display and score 1–5; acceptance criterion: mean score ≥ 4.

### 5.3 Multi-Camera Time Synchronization Accuracy Evaluation

**Rolling-shutter strobe method:** Use an LED strobe light source (known frequency); all cameras capture simultaneously. The positional offset of bright/dark fringe patterns is used to back-calculate the time alignment error, with accuracy of ±0.5 line time.

### 5.4 ToF Accuracy Evaluation

Use a standard depth accuracy test fixture (Lambertian target board at known distances: 0.5 m / 1 m / 2 m / 3 m / 5 m):
- **Absolute accuracy:** $|d_{measured} - d_{true}| < 2\%$
- **Standard deviation:** $\sigma_d < 1\%$ (repeated measurement)

---

## §6 Code Examples

### 6.1 Cross-Camera Color Consistency Correction Matrix Solution

```python
import numpy as np
from scipy.optimize import minimize
from typing import List, Tuple

def compute_deltaE2000(lab1: np.ndarray, lab2: np.ndarray) -> float:
    """
    Compute CIE ΔE2000 color difference (simplified version;
    full version: see ISO 11664-6).

    Args:
        lab1, lab2: CIE L*a*b* color values, shape=(3,)

    Returns:
        deltaE: ΔE2000 value
    """
    # Simplified ΔE2000 (hue-weighting terms omitted; suitable for fast engineering estimate)
    dL = lab1[0] - lab2[0]
    da = lab1[1] - lab2[1]
    db = lab1[2] - lab2[2]

    # Full ΔE2000 requires kL, kC, kH weights; simplified here to ΔE76
    return np.sqrt(dL**2 + da**2 + db**2)


def solve_cross_camera_ccm(
    rgb_main: np.ndarray,
    rgb_aux: np.ndarray
) -> np.ndarray:
    """
    Solve the 3x3 color transform matrix (CCM) from auxiliary to primary camera
    using least squares.

    Args:
        rgb_main: Primary camera patch RGB values, shape=(N_patches, 3), float64, range [0,1]
        rgb_aux: Auxiliary camera patch RGB values, shape=(N_patches, 3)

    Returns:
        M: 3x3 CCM matrix satisfying rgb_main ≈ M @ rgb_aux
    """
    # Least squares: min ||rgb_main - rgb_aux @ M.T||_F^2
    # Analytical solution: M.T = (rgb_aux.T @ rgb_aux)^{-1} @ rgb_aux.T @ rgb_main
    M_T, _, _, _ = np.linalg.lstsq(rgb_aux, rgb_main, rcond=None)
    M = M_T.T
    return M


def apply_cross_camera_ccm(
    image: np.ndarray,
    M: np.ndarray
) -> np.ndarray:
    """
    Apply a 3x3 CCM color transform to an image.

    Args:
        image: Input image, shape=(H, W, 3), float32, range [0,1]
        M: 3x3 CCM matrix

    Returns:
        corrected: Color-corrected image
    """
    h, w = image.shape[:2]
    flat = image.reshape(-1, 3)  # (H*W, 3)
    corrected_flat = (M @ flat.T).T  # (H*W, 3)
    corrected = corrected_flat.reshape(h, w, 3)
    return np.clip(corrected, 0.0, 1.0).astype(np.float32)


# Demo: solve CCM using ColorChecker 24-patch data
def demo_ccm_calibration():
    np.random.seed(42)
    N_patches = 24

    # Simulate primary camera standard patch values (ground truth)
    rgb_main = np.random.rand(N_patches, 3).astype(np.float64)

    # Simulate auxiliary camera with slight color deviation (random 3x3 perturbation)
    true_M_inv = np.eye(3) + np.random.randn(3, 3) * 0.05
    rgb_aux = (true_M_inv @ rgb_main.T).T

    # Solve CCM
    M = solve_cross_camera_ccm(rgb_main, rgb_aux)

    # Evaluate correction quality
    rgb_corrected = (M @ rgb_aux.T).T
    errors = np.linalg.norm(rgb_corrected - rgb_main, axis=1)
    print(f"RGB RMS error after CCM correction: {errors.mean():.4f}")
    print(f"CCM matrix:\n{M}")
    return M
```

### 6.2 Zoom Switching Smooth Transition (Alpha Blending)

```python
import numpy as np
import cv2
from typing import Optional

def zoom_switch_alpha_blend(
    frame_from: np.ndarray,
    frame_to: np.ndarray,
    alpha: float,
    homography: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Alpha-blend two camera frames during a zoom switch.

    Args:
        frame_from: Frame from the camera being switched away from, uint8 BGR
        frame_to: Frame from the camera being switched to, uint8 BGR
        alpha: Blend weight [0, 1]; 0 = use entirely from, 1 = use entirely to
        homography: Homography matrix aligning frame_to to frame_from viewpoint (optional)

    Returns:
        blended: Blended image
    """
    if homography is not None:
        h, w = frame_from.shape[:2]
        frame_to_aligned = cv2.warpPerspective(
            frame_to, homography, (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE
        )
    else:
        frame_to_aligned = frame_to

    blended = cv2.addWeighted(
        frame_from, 1.0 - alpha,
        frame_to_aligned, alpha, 0
    )
    return blended


def zoom_switch_controller(
    current_zoom: float,
    target_zoom: float,
    cameras: dict
) -> str:
    """
    Determine which camera to use at the current focal length (with hysteresis).

    Args:
        current_zoom: Current zoom multiplier
        target_zoom: User-requested zoom multiplier
        cameras: Coverage range per camera, e.g.
                 {'wide': (0.5, 1.5), 'main': (1.5, 3.0), 'tele': (3.0, 10.0)}

    Returns:
        selected_camera: Name of the camera to use
    """
    # Simplified: select the best camera for the target zoom
    for cam_name, (zoom_min, zoom_max) in cameras.items():
        if zoom_min <= target_zoom <= zoom_max:
            return cam_name
    # Out of range: select the nearest
    return sorted(cameras.items(),
                  key=lambda x: min(abs(target_zoom - x[1][0]),
                                    abs(target_zoom - x[1][1])))[0][0]


# Memory bandwidth calculation utility
def compute_mipi_bandwidth(
    cameras: list
) -> float:
    """
    Compute total MIPI bandwidth requirement for a multi-camera system.

    Args:
        cameras: Camera configuration list; each item is
                 {'W': int, 'H': int, 'fps': int, 'bpp': int}

    Returns:
        total_bw_gbps: Total bandwidth (Gbps)
    """
    total_bps = 0
    for cam in cameras:
        bps = cam['W'] * cam['H'] * cam['fps'] * cam['bpp']
        total_bps += bps
        print(f"  {cam.get('name', 'Camera')}: "
              f"{cam['W']}x{cam['H']}@{cam['fps']}fps "
              f"{cam['bpp']}bit = {bps/1e9:.2f} Gbps")

    # MIPI protocol overhead (~15%)
    effective_bw = total_bps / 0.85
    print(f"  Total bandwidth incl. protocol overhead: {effective_bw/1e9:.2f} Gbps")
    return effective_bw / 1e9


if __name__ == "__main__":
    cameras = [
        {'name': 'Ultra-wide', 'W': 4032, 'H': 3024, 'fps': 30, 'bpp': 10},
        {'name': 'Primary',    'W': 8192, 'H': 6144, 'fps': 30, 'bpp': 10},
        {'name': 'Telephoto',  'W': 4032, 'H': 3024, 'fps': 30, 'bpp': 10},
        {'name': 'ToF',        'W': 320,  'H': 240,  'fps': 30, 'bpp': 16},
    ]
    print("Multi-camera MIPI bandwidth requirement:")
    total_bw = compute_mipi_bandwidth(cameras)

    demo_ccm_calibration()
```

---

## References

1. Delbrück, T., & Lichtsteiner, P. (2010). "Fast sensory motor control based on event-based hybrid neuromorphic-procedural system." *ISCAS 2010*.
2. Heide, F., et al. (2014). "FlexISP: A flexible camera image processing framework." *ACM SIGGRAPH Asia*, 33(6).
3. Liang, C.K., et al. (2011). "Programmable aperture photography: multiplexed light field acquisition." *ACM SIGGRAPH*, 27(3).
4. Qualcomm Technologies (2023). "Snapdragon 8 Gen 3 Camera Architecture." Qualcomm Technologies White Paper.
5. Sony Semiconductor Solutions (2023). "IMX989: 1-inch stacked CMOS image sensor." Technical Datasheet.
6. MIPI Alliance. (2022). "MIPI CSI-2 Specification v4.0." MIPI Alliance Standard.
7. Chen, L.C., et al. (2018). "Encoder-Decoder with Atrous Separable Convolution for Semantic Image Segmentation (DeepLab v3+)." *ECCV 2018*.
8. Hasinoff, S.W., et al. (2016). "Burst photography for high dynamic range and low-light imaging on mobile cameras." *ACM SIGGRAPH Asia*.
9. Liu, Y., et al. (2021). "UDC-UNet: Under-Display Camera Image Restoration via U-Shape Dynamic Network." *ECCV Workshop*.
10. He, K., et al. (2010). "Single image haze removal using dark channel prior." *IEEE TPAMI*, 33(12).

---

## §8 Glossary

| Term | Full Name | Meaning |
|------|-----------|---------|
| VC | Virtual Channel | MIPI CSI-2 virtual channel; multiplexes multiple data streams over a single physical path |
| OTP | One-Time Programmable | One-time-programmable memory storing camera calibration data |
| CCM | Color Correction Matrix | Color correction matrix |
| CCT | Correlated Color Temperature | Correlated color temperature |
| JND | Just Noticeable Difference | Just-noticeable-difference perceptual threshold |
| ToF | Time-of-Flight | Time-of-flight depth sensor |
| FSIN | Frame Sync Input/Output | Frame synchronization signal for multi-camera hardware sync |
| Hysteresis | — | Hysteresis strategy; prevents oscillation near switching thresholds |
| Alpha Blend | — | Alpha blending; weighted superposition of two image streams |
| ΔE2000 | — | CIE 2000 color difference formula; perceptually linearized color difference metric |
| MTF50 | Modulation Transfer Function at 50% | Spatial frequency at 50% modulation transfer; measures sharpness |
| LSC | Lens Shading Correction | Lens shading correction |
| Flying Pixel | — | Depth outlier at object edges in ToF depth maps caused by mixed-pixel phase ambiguity |
