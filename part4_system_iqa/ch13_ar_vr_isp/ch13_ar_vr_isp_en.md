# Part 4, Chapter 13: AR/VR Display ISP

> **Scope:** This chapter covers the special ISP requirements of XR (eXtended Reality) head-mounted displays: low-latency rendering, inter-pupillary distance correction, chromatic aberration correction, and ATW (Asynchronous TimeWarp).
> **Prerequisites:** Volume 4, Chapter 1 (3A Control System); Volume 2, Chapter 20 (HDR Display Signal Chain)
> **Target Readers:** System engineers, algorithm engineers

---

## §1 Theory

### 1.1 Special Characteristics of XR Head-Mounted Display Imaging Systems

The ISP of AR/VR/MR head-mounted displays (collectively XR, eXtended Reality) faces engineering constraints entirely different from those of traditional smartphones and cameras. The core distinction is: **the display is rendered in real time rather than capturing reality**, but the ISP still needs to process real-time video from front-facing pass-through cameras, eye-tracking camera data, and depth sensor data.

**Key Metric Framework:**

1. **Motion-to-Photon Latency (MTP):** Full end-to-end latency from head movement to pixel update — must be < 20 ms (VR comfort threshold), ideally < 10 ms (no cybersickness). Measured data show that approximately 60% of users experience discomfort when latency exceeds 20 ms (Fernandes & Feiner, 2016).
2. **Pixels Per Degree (PPD):** The human fovea resolves approximately ~60 PPD; XR headsets target >30 PPD; consumer products achieve approximately 20–25 PPD.
3. **Field of View (FOV):** Horizontal FOV is typically 90°–120°; larger FOV makes optical distortion harder to correct, and at equal resolution, results in lower PPD.
4. **Binocular Disparity:** The depth-encoding mechanism for left/right eye views; accurate Inter-Pupillary Distance (IPD) correction directly affects stereo perception comfort.

### 1.2 Optical Distortion Model

The wide-angle optical systems of XR headsets (Fresnel lenses or Pancake folded-optic paths) introduce severe geometric distortion, typically described by the Brown-Conrady model (polynomial distortion model):

$$x_d = x_u(1 + k_1 r^2 + k_2 r^4 + k_3 r^6) + 2p_1 x_u y_u + p_2(r^2 + 2x_u^2)$$
$$y_d = y_u(1 + k_1 r^2 + k_2 r^4 + k_3 r^6) + p_1(r^2 + 2y_u^2) + 2p_2 x_u y_u$$

where $r^2 = x_u^2 + y_u^2$, $(k_1, k_2, k_3)$ are radial distortion coefficients, and $(p_1, p_2)$ are tangential distortion coefficients.

In VR headsets (e.g., the Meta Quest series), $k_1$ is typically negative (barrel distortion), with a typical range of $k_1 \in [-0.2, -0.4]$.

**Chromatic Dispersion Distortion:** Different wavelengths of light refract at different angles in the lens, causing independent distortion parameters $(k_{1R}, k_{1G}, k_{1B}, ...)$ for each RGB channel. Chromatic aberration (CA) is most pronounced at the field edges, reaching 2–4 pixels.

### 1.3 ATW (Asynchronous TimeWarp) Principle

ATW (Asynchronous TimeWarp) is the most important latency compensation technique in XR systems, engineered by Oculus in 2014 (Antonov et al., 2014).

**Problem Background:** GPU rendering of a complete frame (full rasterization + shading) typically takes 5–15 ms. During this time, the head continues to move, causing the displayed image to mismatch the current head pose and inducing visual-vestibular conflict — i.e., cybersickness.

**ATW Principle:** In the very short time window between GPU render completion and display refresh (typically < 2 ms), ATW uses **the most recent head pose sensor data** to apply a 2D reprojection transform to the already-rendered frame, approximately compensating for head movement:

$$\mathbf{p}_{warped} = \mathbf{K} \cdot \Delta\mathbf{R} \cdot \mathbf{K}^{-1} \cdot \mathbf{p}_{rendered}$$

where $\Delta\mathbf{R} = \mathbf{R}_{display} \cdot \mathbf{R}_{render}^T$ is the rotational change from render time to display time, and $\mathbf{K}$ is the camera intrinsic matrix.

**ATW Limitations:** ATW can only compensate for **rotational motion** (3 DoF) and cannot compensate for translational motion (6 DoF). A more complete solution is **ASW (Asynchronous SpaceWarp)**, which uses a depth buffer for true 3D reprojection and can handle translational motion, but requires additional depth data and computational resources (Facebook Reality Labs, 2016).

### 1.4 FOV and PPD Calculation

Given display resolution $(W_{px}, H_{px})$ and optical FOV $(\theta_H, \theta_V)$, PPD is calculated as:

$$PPD_H = \frac{W_{px}}{\theta_H}, \quad PPD_V = \frac{H_{px}}{\theta_V}$$

Taking the Apple Vision Pro (micro-OLED, approximately 4K per eye, FOV ~100°) as an example:

$$PPD_H = \frac{3660}{100} \approx 36.6 \text{ PPD}$$

This is close to 60% of the human foveal resolution and is the highest PPD among consumer products (Koulieris et al., 2019).

### 1.5 Foveated Rendering Principle

Based on the visual properties of the human eye: the fovea (approximately 2° visual angle) has the highest resolution; peripheral vision resolution falls off following the rule $\cos^{1.5}(\theta)$ (Campbell & Robson, 1968). By using real-time eye tracking, high-resolution rendering can be concentrated around the gaze point, forming a three-zone rendering structure:

- **Inner zone (~5°):** Full-resolution rendering
- **Middle zone (5°–30°):** 50% resolution
- **Outer zone (>30°):** 25% resolution

This saves 60–70% of GPU compute (Guenter et al., 2012). Eye tracking typically uses near-infrared (NIR) cameras and the Purkinje corneal reflection method, achieving tracking accuracy of approximately 0.5°–1° with latency < 5 ms.

---

## §2 Algorithm Methods and System Architecture

### 2.1 Pass-through ISP Pipeline

Pass-through mode (live camera feed overlay) is the core function of AR headsets (e.g., Apple Vision Pro, Meta Quest 3), requiring real-time compositing of front-facing camera images into the virtual scene.

**Typical Pipeline:**
```
Front-facing camera → MIPI CSI-2 → Hardware ISP
           |
    BLC → Demosaic → Denoising → AWB/AE → CSC
           |
    Distortion correction (LUT) → CA correction → ATW reprojection
           |
    Compositing render engine → Display driver → micro-OLED/LCD
```

**Key Latency Breakdown (reference Apple Vision Pro architecture, Abrash, 2023):**

| Stage | Latency Budget | Notes |
|-------|---------------|-------|
| Sensor exposure/readout | 1–3 ms | Low exposure time requires high ISO compensation |
| MIPI transfer | <0.5 ms | MIPI D-PHY 4-lane |
| Hardware ISP processing | 1–2 ms | Demosaic + NR + AWB |
| Distortion + CA correction | 0.5 ms | Hardware LUT lookup |
| ATW reprojection | <0.5 ms | Dedicated hardware unit |
| Render compositing | 5–10 ms | M2 GPU (Vision Pro) |
| Display scan | 2–3 ms | 90 Hz micro-OLED |
| **Total** | **~12 ms** | Vision Pro measured value |

### 2.2 Apple Vision Pro ISP Architecture Analysis

Based on publicly available technical materials (Apple, 2023; Abrash, 2023) and patent documents, the Vision Pro ISP architecture has the following characteristics:

1. **Dual-chip co-processing:** The M2 chip handles the main ISP and GPU rendering; the R1 chip (dedicated real-time chip) is exclusively dedicated to processing 12 camera feeds, 6 microphones, and sensor data. R1 claims < 12 ms full end-to-end latency.
2. **12 cameras:** Including 2 stereoscopic front-facing cameras (pass-through, 4K resolution), 4 downward-facing tracking cameras, 2 eye-tracking cameras (NIR), 2 LiDAR scanners (Apple official spec), and 2 TrueDepth infrared cameras.
3. **Hardware distortion correction unit:** R1 has a dedicated distortion correction hardware block (ASIC), offloading the GPU and achieving < 0.5 ms correction latency.
4. **Time synchronization bus:** All 12 sensors are aligned via a unified hardware clock, with timestamp precision < 100 μs.

### 2.3 Optical Distortion Correction: Pre-computed LUT Method

**LUT Generation Workflow:**
1. For each output pixel coordinate $(u_{out}, v_{out})$, compute the corresponding input coordinate $(x_{in}, y_{in})$ via the inverse distortion function
2. Store as a floating-point lookup table (float32), format $W \times H \times 2$
3. At runtime: table lookup + bilinear (or bicubic) interpolation

**Joint Computation of ATW and Distortion:** Merge the ATW rotation transform with distortion correction into a single texture sample, avoiding two memory accesses:

$$\mathbf{p}_{out} = \text{UndistortLUT}\left(\mathbf{K} \cdot \Delta\mathbf{R} \cdot \mathbf{K}^{-1} \cdot \mathbf{p}_{in}\right)$$

### 2.4 Chromatic Aberration (CA) Correction System

CA correction requires applying independent distortion parameters to each of the RGB channels:
- **R channel (~700 nm):** Smallest refractive index; image is slightly enlarged (lighter barrel distortion)
- **G channel (~550 nm):** Reference channel
- **B channel (~450 nm):** Largest refractive index; image is slightly contracted (heavier barrel distortion)

The Apple Vision Pro uses Pancake lenses (folded optical path, Kim et al., 2022), which reduce CA by approximately 50% compared to Fresnel lenses, but digital correction is still required; typical residual CA is approximately 0.5–1 px.

### 2.5 IPD Correction and Stereo Rendering

**Mechanical IPD Adjustment:** Products such as the Meta Quest Pro support mechanical IPD adjustment (55–75 mm range), physically moving the lenses to change pupil alignment.

**Software IPD Correction (Virtual Disparity Adjustment):** For IPD offsets that cannot be precisely matched mechanically, the software approach adjusts the inter-eye baseline of the left/right rendering cameras:

$$d_{IPD\_offset} = IPD_{actual} - IPD_{default}$$
$$\Delta x_{viewport} = d_{IPD\_offset} \cdot \frac{f_{lens}}{IPD_{default}}$$

### 2.6 Multi-Camera Time Synchronization

All cameras in an XR headset must be strictly time-synchronized; typical approaches include:
- **Hardware frame synchronization (VSYNC):** A unified clock signal drives all sensors to expose simultaneously
- **Software timestamp alignment:** The ISP hardware stamps each frame with a high-precision timestamp (μs-level); the rendering engine selects the nearest sensor data based on timestamps

---

## §3 Tuning and Engineering Guidelines

### 3.1 Latency Budget Allocation Principles

MTP latency budget priority: rendering (GPU load) > sensor exposure > ISP processing. Engineering optimization strategies:

1. **Reduce sensor exposure time:** Compensate with automatic gain control (AGC); recommend exposure < 3 ms
2. **Fixed frame rate mode:** Avoid latency jitter from variable refresh rate (VRR); recommend locking to 90 Hz or 120 Hz
3. **Asynchronous sensor readout:** Dedicated chips such as R1 use an independent low-latency path, unaffected by main CPU scheduling

### 3.2 Special ISP Parameter Settings for XR

| Parameter | Typical Smartphone ISP Value | XR Headset Recommendation | Reason |
|-----------|------------------------------|--------------------------|--------|
| AE convergence speed | 5–10 frames | 2–3 frames | Rapid response to scene brightness changes |
| AWB convergence speed | 10–20 frames | 5–10 frames | Prevent color jumps causing discomfort |
| Denoising strength | Medium | Low (latency first) | Avoid temporal NR introducing latency |
| Sharpening strength | Medium | Low | Avoid ringing artifacts degrading immersion |
| HDR mode | On | Off (pass-through) | HDR merge increases latency |

### 3.3 Distortion LUT Calibration Best Practices

1. **Calibration environment:** Use a high-precision checkerboard (≥9×7 squares, inter-square spacing error < 0.05 mm) under stable lighting (CRI > 90)
2. **Multi-pose acquisition:** At least 20 angles covering the full FOV (including edge regions)
3. **Temperature compensation:** The optical system has thermal drift characteristics; calibrate at operating temperature (35–45°C)
4. **LUT resolution:** Recommend 64×64 or 128×128 grid (bilinearly interpolated to full resolution at runtime) to balance accuracy and memory

### 3.4 Eye-Tracking NIR Camera Configuration

- **Frame rate:** ≥ 120 fps (~8 ms/frame) to meet < 10 ms tracking latency
- **Exposure:** Fixed short exposure (~0.5 ms), synchronized with high-intensity NIR LED pulses
- **NIR wavelength:** 850 nm or 940 nm (940 nm is less susceptible to solar interference)
- **Safety standard:** Follow IEC 62471:2006 photobiological safety standard; NIR irradiance must be within the Exempt Risk Group

### 3.5 CA Correction Tuning Recommendations

1. **Detection method:** Use a high-contrast black-and-white starburst pattern test chart; observe colored fringing at edges
2. **R/B channel offset:** Should normally be < 2 px; if exceeded, there may be an optical design problem
3. **Temperature effects:** Pancake lens CA exhibits thermal drift; recommend calibrating LUTs at both 20°C and 45°C

---

## §4 Common Artifacts and Problem Analysis

### 4.1 Cybersickness

**Root Cause:** Visual-vestibular sensory mismatch, primarily caused by MTP latency exceeding 20 ms; secondarily by frame rate fluctuation (frame stutter).
**Diagnosis:** Use a high-speed camera (≥1000 fps) to measure actual MTP latency; check whether ATW is correctly enabled and whether GPU load is too high.
**Mitigation:** Reduce render resolution or level of detail (LOD); enable ATW/ASW; apply a comfort zone (reduce peripheral FOV to decrease optical flow).

### 4.2 ATW Edge Ghosting

**Root Cause:** ATW performs only a 2D affine transform and cannot handle parallax changes from nearby objects in the scene; fast translational motion produces content warping.
**Symptom:** Moving objects show trailing artifacts or "rubber-like" deformation at edges, especially noticeable at object boundaries and depth discontinuities.
**Mitigation:** Upgrade to ASW (depth-buffer-based 3D reprojection), or increase GPU frame rate to reduce ATW dependence.

### 4.3 Chromatic Fringing

**Root Cause:** CA LUT calibration error, lens thermal drift causing parameter shift, or individual unit variation from manufacturing tolerances.
**Symptom:** High-contrast edges (e.g., white background with black text) display red-green or purple color bands, most prominent at field edges.
**Quantification:** Use an ISO 12233 test chart; measure the color band width at edges (acceptance criterion: < 1 px).

### 4.4 Stereo Mismatch

**Root Cause:** Left and right eye frame rates out of sync, or ATW left/right eye timestamp difference > 1 ms, causing stereo disparity mismatch and eye strain.
**Symptom:** Fixed objects appear to "float" when fixated; prolonged use causes headaches.
**Diagnosis:** Check the timestamp difference between the two ISP streams; confirm that the frame synchronization signal correctly drives both sensors.

### 4.5 Vignetting

**Root Cause:** Insufficient peripheral light in wide-angle optical systems (cosine-fourth law: $E \propto \cos^4\theta$); insufficient LSC parameters.
**Symptom:** Image corners are noticeably darker; in pass-through mode, this degrades immersion.
**Fix:** Re-collect LSC calibration data across the full FOV (including edges) to ensure gain compensation provides complete coverage.

### 4.6 Motion Blur

**Root Cause:** Exposure time too long (> 3 ms); pass-through images blur during fast head rotations.
**Symptom:** Object edges show horizontal trailing artifacts when the head turns quickly.
**Trade-off:** Shortening exposure time reduces blur but requires higher ISO (more noise); recommend using TNR (temporal noise reduction) with short exposure.

---

## §5 Evaluation Methods

### 5.1 Motion-to-Photon Latency Measurement

**High-Speed Camera Method (highest hardware accuracy):**
Use a ≥1000 fps high-speed camera to simultaneously capture: (a) an IMU indicator light fixed to the headset (triggered by head movement), and (b) the changes on the headset display. Compute latency precisely using frame differencing, with an error of approximately ±1 ms.

**Software Timestamp Method:**
Insert timestamp markers at each node of the ISP/rendering pipeline to gather latency distribution statistics at each stage; suitable for engineering debugging.

### 5.2 Geometric Distortion Residual Evaluation

Use a standard checkerboard chart (GB/T 19897.1) to detect corner coordinate residuals after correction:
- **Acceptance criteria:** RMS < 0.5 px (central region); < 1.0 px (edge region)
- **Tools:** OpenCV `cv2.calibrateCamera()` + `cv2.undistortPoints()`

### 5.3 Binocular Disparity Consistency

Fix a calibration object at a known depth (1 m distance) and measure the horizontal disparity between corresponding points in the left and right eye images:
- **Theoretical value:** $disparity = f \cdot IPD / Z$
- **Acceptance criterion:** Measured value deviates from theoretical by < 0.5 px

### 5.4 Actual PPD Measurement

Using a variable spatial frequency sinusoidal grating, measure the minimum resolvable spatial frequency $f_{max}$ (lp/px) and calculate:
$$PPD_{measured} = f_{max} \times \frac{W_{px}}{\theta_H}$$

### 5.5 Chromatic Aberration Evaluation

Using the black-and-white starburst region of an ISO 12233 resolution test chart, compute the lateral offset of RGB channel luminance curves (in pixels).

---

## §6 Code Examples

### 6.1 Brown-Conrady Distortion Correction LUT Generation

```python
import numpy as np
import cv2
from typing import Tuple

def generate_undistort_lut(
    width: int, height: int,
    K: np.ndarray,
    dist_coeffs: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate an undistortion mapping LUT for the given camera intrinsics and distortion coefficients.

    Args:
        width, height: output image resolution
        K: camera intrinsic matrix (3x3), float64
        dist_coeffs: Brown-Conrady distortion coefficients [k1, k2, p1, p2, k3]

    Returns:
        map_x, map_y: float32 coordinate mapping tables, shape=(height, width)
    """
    map_x, map_y = cv2.initUndistortRectifyMap(
        cameraMatrix=K,
        distCoeffs=dist_coeffs,
        R=None,
        newCameraMatrix=K,
        size=(width, height),
        m1type=cv2.CV_32FC1
    )
    return map_x, map_y


def generate_chromatic_aberration_lut(
    width: int, height: int,
    K: np.ndarray,
    dist_r: np.ndarray,
    dist_g: np.ndarray,
    dist_b: np.ndarray
) -> dict:
    """
    Generate separate CA correction LUTs for each RGB channel.

    Args:
        dist_r/g/b: independent distortion coefficients for each channel

    Returns:
        {'R': (map_x, map_y), 'G': ..., 'B': ...}
    """
    luts = {}
    for channel, dist in [('R', dist_r), ('G', dist_g), ('B', dist_b)]:
        map_x, map_y = cv2.initUndistortRectifyMap(
            K, dist, None, K, (width, height), cv2.CV_32FC1
        )
        luts[channel] = (map_x, map_y)
    return luts


def apply_chromatic_aberration_correction(
    image: np.ndarray,
    luts: dict
) -> np.ndarray:
    """
    Apply per-channel CA correction. image is in BGR format.
    """
    result = np.zeros_like(image)
    # BGR channel indices: B=0, G=1, R=2
    channel_map = {'B': 0, 'G': 1, 'R': 2}
    for ch_name, (map_x, map_y) in luts.items():
        ch_idx = channel_map[ch_name]
        result[:, :, ch_idx] = cv2.remap(
            image[:, :, ch_idx], map_x, map_y,
            interpolation=cv2.INTER_LINEAR
        )
    return result


# Example: typical VR headset parameters
if __name__ == "__main__":
    W, H = 1920, 1080
    fx, fy = 900.0, 900.0
    cx, cy = W / 2.0, H / 2.0
    K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1.0]], dtype=np.float64)

    # Typical VR headset barrel distortion coefficients
    dist_g = np.array([-0.30, 0.12, 0.0, 0.0, -0.02])  # G channel (reference)
    # R/B channels have slight differences (chromatic dispersion)
    dist_r = dist_g * np.array([0.98, 1.02, 1.0, 1.0, 0.98])  # R slightly smaller
    dist_b = dist_g * np.array([1.02, 0.98, 1.0, 1.0, 1.02])  # B slightly larger

    luts = generate_chromatic_aberration_lut(W, H, K, dist_r, dist_g, dist_b)

    # Verify LUT memory usage
    map_x_r, map_y_r = luts['R']
    mem_mb = (map_x_r.nbytes + map_y_r.nbytes) * 3 / 1024 / 1024
    print(f"CA LUT total memory: {mem_mb:.1f} MB (3 channels, float32)")
```

### 6.2 ATW Homography Matrix Computation

```python
import numpy as np
import cv2
import time

def compute_atw_homography(
    K: np.ndarray,
    R_render: np.ndarray,
    R_display: np.ndarray
) -> np.ndarray:
    """
    Compute the rotation-compensation homography matrix required for ATW.

    Args:
        K: camera intrinsic matrix (3x3)
        R_render: rotation matrix at render time (camera-to-world), 3x3
        R_display: rotation matrix at display time, 3x3

    Returns:
        H: 3x3 homography matrix for image reprojection
    """
    # Incremental rotation: from render time to display time
    # delta_R = R_display * R_render^T
    delta_R = R_display @ R_render.T

    # ATW homography: H = K * delta_R * K^{-1}
    K_inv = np.linalg.inv(K)
    H = K @ delta_R @ K_inv
    return H


def apply_atw(
    rendered_frame: np.ndarray,
    H: np.ndarray
) -> np.ndarray:
    """
    Apply ATW transform to a rendered frame.

    Args:
        rendered_frame: rendered image, uint8 BGR format
        H: ATW homography matrix

    Returns:
        warped: ATW-corrected image
    """
    h, w = rendered_frame.shape[:2]
    warped = cv2.warpPerspective(
        rendered_frame, H, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE  # Fill borders with nearest pixels to reduce black edges
    )
    return warped


def benchmark_atw_latency(n_trials: int = 1000) -> float:
    """Measure ATW matrix computation latency (excluding warpPerspective)."""
    K = np.eye(3, dtype=np.float64)
    K[0, 0] = K[1, 1] = 900.0
    K[0, 2], K[1, 2] = 960.0, 540.0

    # Simulate 0.3-degree head movement
    theta = np.radians(0.3)
    R_r = np.eye(3)
    R_d = np.array([
        [np.cos(theta), 0, np.sin(theta)],
        [0, 1, 0],
        [-np.sin(theta), 0, np.cos(theta)]
    ])

    t0 = time.perf_counter()
    for _ in range(n_trials):
        _ = compute_atw_homography(K, R_r, R_d)
    t1 = time.perf_counter()

    avg_ms = (t1 - t0) * 1000 / n_trials
    print(f"ATW matrix computation average latency: {avg_ms:.4f} ms (n={n_trials})")
    return avg_ms


# PPD calculation utility
def compute_ppd(resolution_px: int, fov_deg: float) -> float:
    """Calculate pixels per degree (PPD)."""
    return resolution_px / fov_deg


if __name__ == "__main__":
    # Apple Vision Pro parameters (approximate values)
    ppd = compute_ppd(resolution_px=3660, fov_deg=100)
    print(f"Vision Pro PPD (horizontal): {ppd:.1f}")

    benchmark_atw_latency()
```

### 6.3 MTP Latency Budget Analysis Tool

```python
from dataclasses import dataclass
from typing import List

@dataclass
class LatencyStage:
    name: str
    latency_ms: float
    is_parallel: bool = False  # Whether this stage runs in parallel with others

def compute_mtp_latency(stages: List[LatencyStage]) -> float:
    """Compute end-to-end MTP latency (sum of serial stages)."""
    total = sum(s.latency_ms for s in stages if not s.is_parallel)
    parallel_max = max(
        (s.latency_ms for s in stages if s.is_parallel), default=0
    )
    return total + parallel_max


# Typical XR headset latency budget
xr_stages = [
    LatencyStage("Sensor exposure", 2.0),
    LatencyStage("MIPI transfer", 0.3),
    LatencyStage("ISP hardware processing", 1.5),
    LatencyStage("Distortion/CA correction", 0.5),
    LatencyStage("Render compositing (GPU)", 7.0),
    LatencyStage("ATW reprojection", 0.4),
    LatencyStage("Display scan", 2.2),  # 1/90 Hz ≈ 11 ms, but scan latency ~2 ms
]

total_mtp = compute_mtp_latency(xr_stages)
print(f"\nMTP Latency Budget Breakdown:")
for s in xr_stages:
    print(f"  {s.name:30s}: {s.latency_ms:.1f} ms")
print(f"  {'Total':30s}: {total_mtp:.1f} ms")
print(f"  {'Target threshold':30s}:  20.0 ms  ({'PASS' if total_mtp < 20 else 'FAIL'})")
```

---

## References

[1] Antonov, M., et al. (2014). "Asynchronous Timewarp." Oculus VR Technical Blog. https://developer.oculus.com/blog/asynchronous-timewarp/
[2] Facebook Reality Labs. (2016). "Asynchronous SpaceWarp." Oculus Developer Blog.
[3] Guenter, B., et al. (2012). "Foveated 3D graphics." ACM Trans. Graphics (SIGGRAPH Asia), 31(6), 164.
[4] Abrash, M. (2023). "Creating Apple Vision Pro: The Display System." Apple Tech Talks, WWDC 2023.
[5] Apple Inc. (2023). "Apple Vision Pro Technical Overview." Apple Developer Documentation.
[6] Kim, J., et al. (2022). "Optical design of pancake lens for compact VR headset." Optics Express, 30(18), 32961–32973.
[7] Fernandes, A.S., & Feiner, S.K. (2016). "Combating VR sickness through subtle dynamic field-of-view modification." IEEE Symposium on 3D User Interfaces (3DUI).
[8] Koulieris, G.A., et al. (2019). "Near-Eye Display and Tracking Technologies for Virtual and Augmented Reality." Computer Graphics Forum (Eurographics), 38(2), 493–519.
[9] Campbell, F.W., & Robson, J.G. (1968). "Application of Fourier analysis to the visibility of gratings." J. Physiology, 197(3), 551–566.
[10] IEC 62471:2006. "Photobiological safety of lamps and lamp systems." International Electrotechnical Commission.

## §8 Glossary

| Term | Full Name | Description |
|------|-----------|-------------|
| ATW | Asynchronous TimeWarp | Rotation-based latency compensation; applies 2D reprojection between render and display |
| ASW | Asynchronous SpaceWarp | Depth-buffer-based 3D reprojection latency compensation; handles translational motion |
| IPD | Inter-Pupillary Distance | Distance between pupils; affects stereo disparity comfort |
| PPD | Pixels Per Degree | Pixels per degree of visual angle; measures angular display resolution |
| FOV | Field of View | Angular extent of the visible scene; typically specified as horizontal/vertical/diagonal |
| CA | Chromatic Aberration | Color fringing caused by wavelength-dependent refraction in lenses |
| MTP | Motion-to-Photon | End-to-end latency from head motion to pixel emission |
| Pass-through | — | Real-time camera video overlay to simulate AR effect |
| Foveated Rendering | — | Gaze-contingent rendering: full resolution at gaze point, reduced at periphery |
| NIR | Near-Infrared | Near-infrared band commonly used for eye tracking (850/940 nm) |
| XR | eXtended Reality | Umbrella term for VR/AR/MR |
| LUT | Look-Up Table | Pre-computed coordinate mapping table for distortion correction |
| Pancake | — | Folded-optic lens design; reduces headset thickness and chromatic aberration |
| Cybersickness | — | Motion sickness induced by visual-vestibular sensory conflict |
