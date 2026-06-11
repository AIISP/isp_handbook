# Part 6, Chapter 12: Future Consumer Imaging — XR Devices and Spatial Photography

> **Position:** This chapter looks ahead to the imaging system architecture of XR devices and the new paradigm of spatial photography, analyzing ISP design challenges from Apple Vision Pro to Meta Quest 3.
> **Prerequisites:** Vol.6 Ch.01 (Consumer Photography Evolution), Vol.1 Ch.12 (Depth Sensing), Vol.4 Ch.07 (Computational Photography)
> **Audience:** Product managers, algorithm engineers, IQA engineers

---

## §1 XR Imaging Systems Overview

### 1.1 XR Device Classification and Imaging Requirements

**Extended Reality (XR)** is the collective term for Augmented Reality (AR), Virtual Reality (VR), and Mixed Reality (MR). The three categories have fundamentally different demands on their imaging systems:

| Device Type | Representative Products | Camera Role | Key ISP Challenges |
|------------|------------------------|-------------|-------------------|
| VR headset | Meta Quest 2 | Tracking (SLAM) + gesture recognition | Low latency, low light |
| MR headset | Meta Quest 3, Apple Vision Pro | Color passthrough + depth sensing | Color fidelity, < 20ms latency |
| AR glasses | Microsoft HoloLens 2 | Environment understanding, gestures, eye tracking | Wide FOV, real-time semantic segmentation |
| Lightweight AR | Meta Orion (2024 prototype) | Display overlay, no passthrough | Micro-projection optics |

XR device imaging systems differ fundamentally from traditional smartphones: the core metric for smartphone ISPs is "image quality," while the core metric for XR ISPs is **latency** — end-to-end latency exceeding 20ms triggers a vestibulo-ocular reflex (VOR) mismatch that causes motion sickness.

### 1.2 Apple Vision Pro Camera System Architecture

Apple Vision Pro (launched February 2024 at $3,499) carries the most complex sensor array in consumer XR devices to date. Based on Apple Developer documentation and official technical specifications:

**Sensor array (Apple official spec: 12 cameras + 5 sensors + 6 microphones):**
- **Main cameras ×2**: For passthrough video; resolution undisclosed, estimated at 12MP-class
- **Spatial photography cameras ×2**: Dual-lens separation of approximately 60mm; for capturing spatial photos/video
- **Downward-facing cameras ×2**: Hand gesture and physical environment tracking
- **Side cameras ×4**: Enhanced SLAM tracking accuracy
- **LiDAR scanner ×1**: Near-field depth sensing (Apple official spec; distinct from TrueDepth structured light)
- **ToF (Time of Flight) sensor ×1**: Mid-to-far range depth supplementation
- **Infrared cameras ×4**: Eye tracking (two cameras per eye)
- **Microphones ×6**: Spatial audio capture

**Display System:**

Apple Vision Pro uses one **micro-OLED display per eye** with a resolution of **3660×3200 per eye**, at approximately 3,386 ppi — the highest pixel density of any consumer XR device to date. This resolution directly sets the design ceiling for the passthrough camera resolution and ISP processing path: the input camera resolution must exceed the display resolution to avoid upscaling artifacts.

**ISP significance of the Apple M2 + R1 dual-chip architecture:**

Apple Vision Pro uses a dual-SoC design: M2 handles general-purpose computation, while **the R1 chip is dedicated to sensor input processing**. R1's core responsibility is to push all camera, microphone, and sensor data to the display system with ultra-low latency (official figure: 12ms passthrough end-to-end latency). This is a canonical design for XR-dedicated ISP chips — separating sensor fusion from display rendering prevents latency jitter caused by M2's general-purpose scheduling.

### 1.3 Meta Quest 3 Mixed Reality Camera System

Meta Quest 3 (launched October 2023 at $499) is the first mass-market MR headset:

**Sensor configuration:**
- **Color passthrough cameras ×2**: Resolution 18 PPD (Pixels Per Degree); a qualitative leap over the Quest 2's monochrome cameras
- **Depth sensor (IR structured-light projection) ×1**: Working range 0.4–4m
- **Tracking cameras ×2**: Monochrome; for 6DoF (six degrees-of-freedom) position tracking
- **Processor**: Snapdragon XR2 Gen 2 (4nm), including Qualcomm Spectra ISP

Quest 3's color passthrough is its core selling point: users see the real world in real time through the cameras while virtual content is overlaid. Unlike looking at the world through an iPhone camera, Quest 3 must achieve **perceptual transparency** — users should not sense that they are "watching a video on a screen" rather than directly viewing reality.

### 1.4 Core XR ISP Requirement Specifications

```
XR ISP Requirements Pyramid (bottom to top):

          ┌─────────────────────────────┐
          │  Semantic Understanding (AI) │  ← Object detection, scene segmentation
          ├─────────────────────────────┤
          │  Color Accuracy             │  ← ΔE < 2, matching reality
          ├─────────────────────────────┤
          │  Depth Accuracy             │  ← mm-level error (near field)
          ├─────────────────────────────┤
          │  Wide FOV (200°+)           │  ← Human horizontal FOV ~200°
          ├─────────────────────────────┤
          │  End-to-end Latency < 20ms  │  ← Bottom layer; most critical
          └─────────────────────────────┘
```

The 20ms latency threshold comes from human physiology: the vestibular system perceives head movement with approximately 10ms latency; the additional latency the visual system can tolerate is approximately 10ms; total approximately 20ms. Beyond this threshold, the visual and vestibular signals mismatch, causing nausea.

---

## §2 Spatial Photography and Stereoscopic Video

### 2.1 Technical Principles of Spatial Video

**Spatial Video** is a new imaging format introduced by Apple with iPhone 15 Pro in 2023, designed for display on Apple Vision Pro. Its technical core is **stereoscopic video** plus depth metadata.

**iPhone 15 Pro / Apple Vision Pro Spatial Video specifications:**

| Parameter | Specification |
|-----------|-------------|
| Capture device | iPhone 15 Pro (main + ultrawide) / Apple Vision Pro built-in dual cameras |
| Baseline distance | iPhone: ~27mm; Vision Pro: ~60mm |
| Resolution | 1920×1080 (per eye) |
| Frame rate | 30fps |
| Encoding format | MV-HEVC (Multi-View High Efficiency Video Coding) |
| Field of view | 180° stereoscopic field |
| Depth range | 0.5m – ∞ |
| File size | ~130MB/minute |

### 2.2 MV-HEVC Encoding Standard

**MV-HEVC (Multi-View HEVC)** is an extension of the ISO/IEC 23008-2 standard, supporting encoding of multiple views within a single bitstream. Apple's spatial video implementation uses two views (left eye/right eye):

```
MV-HEVC bitstream structure:
┌─────────────────────────────────────────────────┐
│  Base View (left eye, independently decodable)   │
│  ┌────────────────────────────────────────────┐  │
│  │  I-frame │ P-frame │ P-frame │ P-frame ... │  │
│  └────────────────────────────────────────────┘  │
│  Dependent View (right eye, inter-view predicted)│
│  ┌────────────────────────────────────────────┐  │
│  │  I-frame │ P-frame + disparity vectors │ ...│  │
│  └────────────────────────────────────────────┘  │
│  Depth Metadata Track (stored as separate track) │
└─────────────────────────────────────────────────┘
```

The right-eye view uses **disparity vectors** from the left eye for inter-view prediction, improving coding efficiency by approximately 30–40% compared to independent dual-stream encoding. Depth metadata is stored as a separate track, allowing the player to perform disparity adjustment (Depth Comfort Adjustment) during display.

### 2.3 ISP Synchronization Challenge: Temporal Alignment of Dual Cameras

The greatest ISP challenge for stereoscopic video is **temporal synchronization of the two camera streams**. The human eye is extremely sensitive to stereo disparity signals — if there is a time offset between the left and right eye images, there is no problem in static scenes, but when fast-moving objects (such as a running pet or a moving person) appear, this causes "ghosting" and breakdown of stereoscopic perception.

**Synchronization requirement analysis:**

At 30fps, frame period T = 33.3ms. If the subject's velocity v = 2m/s (slow walking), the displacement over 33ms is:

```
Δx = v × Δt = 2 m/s × 0.033s ≈ 66mm
```

In a stereoscopic camera with a 60mm baseline, 66mm of displacement exceeds the baseline distance, causing complete failure of stereo matching. Therefore:

**Temporal synchronization requirement: Δt < 10μs (microseconds)**

Implementation approaches:
1. **Hardware sync**: The master camera sends a GPIO trigger signal to synchronize the slave camera's VSYNC (vertical sync) signal; achieves nanosecond-level precision.
2. **Frame timestamp alignment**: Record precise timestamps for each frame in the ISP; apply sub-pixel motion compensation in post-processing.
3. **Rolling shutter correction**: Both cameras scan in the same row direction, reducing the rolling shutter geometric distortion differences between left and right eyes.

### 2.4 Dual-Camera Color Matching

Even two cameras of identical hardware specification will differ due to manufacturing process variations:
- **Spectral response mismatch**: ΔλFWHM ≈ 2–5nm
- **Dark current differences**: Different pixel arrays have different FPN (Fixed Pattern Noise) patterns
- **Lens tint differences**: Coating process errors cause subtle color shifts

ISP color matching pipeline:
```
Left RAW → BLC → Demosaic → AWB → CCM(L) → 3D LUT (cross-camera calibration) → Output(L)
Right RAW → BLC → Demosaic → AWB → CCM(R) → 3D LUT (cross-camera calibration) → Output(R)
                                                   ↑
                              Cross-camera mapping matrix calibrated with Macbeth color chart
```

Calibration target: ΔE₀₀ < 1.0 (just-noticeable difference threshold) between both outputs under standard illumination; < 2.0 in motion scenes.

---

## §3 Passthrough Camera ISP

### 3.1 Passthrough User Experience Goals

The goal of MR passthrough is for users to "forget they are wearing a headset" — ideal passthrough should be perceptually indistinguishable from looking directly at the world with the naked eye. This goal has several engineering dimensions:

1. **Latency transparency**: When the user turns their head, the update latency of visual content must remain below the VOR threshold.
2. **Color naturalness**: Color temperature, saturation, and brightness match reality.
3. **Geometric accuracy**: Parallel lines remain parallel; they must not curve due to lens distortion/correction errors.

### 3.2 Latency Budget Breakdown

Breakdown of Apple Vision Pro's officially claimed 12ms passthrough latency (estimated):

```
Sensor exposure ends                               0ms
    ↓  Sensor readout (MIPI CSI-2 transfer)
                                                 +1–2ms
    ↓  ISP processing (R1 chip)
       BLC + Demosaic + WB + NR                  +2–3ms
    ↓  Distortion correction (Warp Map)
       GPU / dedicated hardware                  +1–2ms
    ↓  Display scanline write (MicroOLED)
       Frame buffer → display controller         +3–4ms
    ↓  Photons from MicroOLED → lens → retina
                                                  +1ms
Total: approximately 8–12ms (consistent with Apple's official figure)
```

Meta Quest 3's passthrough latency is approximately 40ms (internal measurements), higher than Vision Pro, because:
1. The Snapdragon XR2 Gen 2's sensor fusion latency is higher than R1's dedicated chip.
2. Quest 3's cameras are physically farther from the eyes, giving a longer optical path requiring larger distortion correction computation.

### 3.3 Passthrough Distortion Correction

Wide-angle cameras (FOV > 100°) in XR headsets inevitably introduce severe **barrel distortion**. Passthrough ISP distortion correction pipeline:

**Step 1: Radial distortion model**

Using the Brown-Conrady distortion model:
```
x_distorted = x(1 + k₁r² + k₂r⁴ + k₃r⁶)
y_distorted = y(1 + k₁r² + k₂r⁴ + k₃r⁶)

where r² = x² + y²
k₁, k₂, k₃ are radial distortion coefficients (factory-calibrated and stored on device)
```

**Step 2: Chromatic aberration correction**

Off-axis rays in wide-angle lenses produce lateral chromatic aberration; the distortion coefficients differ for each RGB channel:

```
k₁(R) ≠ k₁(G) ≠ k₁(B)
```

Correction method: apply a slight scaling transform to R/B channels independently to align channel edges.

**Step 3: Warp Map pre-computation**

Combine distortion correction + chromatic aberration correction + display geometry mapping into a single **Warp Map (deformation lookup table)**: each display pixel maps to the corresponding camera raw pixel coordinates (sub-pixel, using bilinear interpolation). At runtime, only a single texture sampling operation is needed per frame, avoiding per-frame recomputation.

### 3.4 Passthrough Color Calibration

Passthrough color perception is highly complex because **the reference white point changes with the scene**. In an indoor (warm light, CCT ~3000K) and outdoor (daylight, CCT ~6500K) environment, the user's expectations of "natural color" are completely different.

Apple Vision Pro's solution (inferred):
- Use ambient light sensor to estimate scene color temperature (CCT) in real time.
- Dynamically adjust passthrough AWB target and saturation mapping.
- Keep skin tones invariant; apply slight saturation boost (+10–15%) to other colors, compensating for the perceptual gap between MicroOLED display and direct viewing.

---

## §4 AI-Enhanced XR Imaging

### 4.1 XR Scene Semantic Understanding

AR overlay functionality in XR devices is highly dependent on semantic understanding of the physical world:
- **Plane detection**: Identify floors, table surfaces, walls — provide "landing zones" for AR content.
- **Object recognition**: Identify furniture, screens, human bodies — enable intelligent occlusion.
- **Body pose tracking**: Real-time estimation of user hand/body posture.

Apple visionOS scene understanding API (ARKit for visionOS) uses **neural-network-driven plane detection**, which is more accurate than traditional RANSAC-based point cloud plane fitting on textureless planes (white walls, untextured floors), with lower computational cost.

### 4.2 Neural Rendering and Avatar Capture

**Neural rendering** in XR has its core application in **photorealistic avatars**:

Apple Vision Pro's Persona feature uses the built-in multi-camera array (including eye-tracking IR cameras) to capture the user's face in real time:
1. Structured-light IR cameras reconstruct 3D facial geometry (approximately 5,000-vertex face mesh).
2. Color cameras capture skin texture.
3. A **NeRF (Neural Radiance Field)-inspired appearance model** handles dynamic texture changes in facial expressions.
4. Renders the user's virtual avatar in real time for FaceTime video calls.

**Special ISP requirements for Avatar capture:**
- Infrared camera ISP must accurately process structured light patterns (suppress ambient IR interference, enhance structured-light fringe contrast).
- Color camera AWB must be highly accurate for skin tones (ΔE₀₀ < 0.5), because any color shift makes the avatar "look unlike the person."

### 4.3 3D Gaussian Splatting (3DGS) Real-Time Reconstruction

**3D Gaussian Splatting (3DGS)** is a revolutionary work published by Kerbl et al. at SIGGRAPH 2023 (*3D Gaussian Splatting for Real-Time Radiance Field Rendering*). Compared to NeRF, which requires hours of training and seconds per frame to render, 3DGS achieves:
- **Training**: High-quality 3D scene reconstruction in minutes (GPU)
- **Real-time rendering**: 100fps or above (NVIDIA RTX 3090)

3DGS applications in XR:
1. **Rapid scene reconstruction**: User scans a room with an XR device (30 seconds), instantly generating an interactive 3D Gaussian scene.
2. **Remote telepresence**: The far end captures the speaker with multi-cameras; 3DGS reconstructs in real time and renders from any viewpoint for the near end.
3. **AR occlusion culling**: 3DGS provides a dense depth map for correctly occluding AR objects that are blocked by real objects.

**3DGS requirements on XR ISP:**
- Input camera frames require precise calibration (intrinsic matrix K, distortion coefficients d).
- High color consistency requirements: exposure/AWB changes between frames cause 3DGS color noise (Color Floaters).
- On-device 3DGS reconstruction for XR requires NPU acceleration (currently ~20fps on Snapdragon Gen 3).

### 4.4 Real-Time Semantic Segmentation for AR Occlusion

AR occlusion is one of the core challenges of mixed reality: when virtual objects are occluded by real objects, the correct occlusion relationship must be rendered; otherwise AR content will "pass through" real objects, breaking immersion.

Implementation pipeline:
```
Depth sensor → Dense depth map (512×512)
                     ↓
Color camera → Semantic segmentation (MobileNetV3-Small, running on NPU) → Object mask
                     ↓
Depth map × Semantic mask → Occlusion layer
                     ↓
AR rendering composite: virtual object → occlusion layer blend → final frame
```

---

## §5 Consumer XR Product Trends

### 5.1 Lightweight AR Glasses: Meta Orion (2024 Prototype)

In September 2024, Meta CEO Mark Zuckerberg unveiled the **Orion AR glasses** prototype at Meta Connect, the closest to a "final product form" of true AR glasses to date:

**Technical specifications (public information):**
- **Display**: Silicon carbide (SiC) waveguide display, FOV approximately 70°
- **Processing**: ASIC compute puck (wrist-worn), connected wirelessly
- **Sensors**: EMG (electromyography) gesture recognition wristband
- **Cameras**: Outward-facing cameras for scene understanding; **no color passthrough** (display overlays the real world directly)
- **Weight**: Approximately 98g (glasses body), close to ordinary eyeglasses

Orion's ISP design focus is not passthrough but:
- **SLAM cameras**: 6DoF tracking; registration accuracy within waveguide FOV < 0.1°
- **Gesture recognition**: Hybrid EMG + camera input
- **Eye tracking**: For foveated rendering (reduces GPU power consumption)

### 5.2 Smart Glasses: Ray-Ban Meta (Action Camera Form Factor)

In contrast to Orion's high-tech approach, **Ray-Ban Meta smart glasses** (September 2023, $299) take a pragmatic route:

**Technical positioning**: Action camera + voice assistant in eyeglasses form factor; **no display, no passthrough**

**Camera specifications:**
- 12MP front camera (no optical zoom)
- 1080p/60fps video recording
- Four built-in microphones; supports Meta AI voice interaction
- Supports Instagram/Facebook live streaming

**ISP characteristics:**
- Ultra-compact form factor (frame thickness ~5mm) limits the optical path
- Relies on Meta's cloud AI processing (photo upload for automatic enhancement after capture)
- On-device ISP performs only basic processing (BLC, demosaicing, basic AWB); advanced functions run in the cloud

### 5.3 Convergence Trends: Smartphones and XR

Over the next 2–3 years (outlook as of end-2024), smartphones and XR glasses will converge deeply:

**Apple's roadmap (inferred):**
- iPhone as the computational hub for XR glasses (analogous to Apple Watch depending on iPhone)
- iPhone's ProRAW multi-frame processing improves XR glasses capture quality
- iPhone's A18 Pro ISP delivers real-time quality enhancement for glasses via wireless low-latency protocol

**Google's roadmap (Android XR):**
- Android XR platform (released 2024, based on Android 15)
- Gemini AI integrated into XR device ISP post-processing
- Samsung Galaxy Ring + Galaxy XR glasses for health + imaging convergence

**Key technical challenges:**
```
Challenge                Current State           Target (2027)
────────────────────────────────────────────────────────────────
Battery life             1–2 hours              All-day
Glasses weight           80–300g                < 50g (close to ordinary eyeglasses)
Waveguide FOV            50–70°                 > 100°
Passthrough latency      12–40ms                < 8ms
Camera quality           720p–1080p             4K spatial video
```

---

## §6 Code: Spatial Video Simulation

This chapter's §6 provides the following core code examples (can be run locally):

### 6.1 Synthetic Stereo Pair Generation

```python
import numpy as np
import cv2
from PIL import Image

def generate_depth_map(h, w, min_depth=0.5, max_depth=10.0):
    """Simulate a log-normal distribution depth map (for simulation use)"""
    depth = np.exp(np.random.uniform(np.log(min_depth), np.log(max_depth), (h, w)))
    return depth.astype(np.float32)

def warp_image_by_disparity(img, disparity):
    """Horizontally shift image pixels by disparity (simplified version)"""
    h, w = img.shape[:2]
    map_x = np.clip(
        np.meshgrid(np.arange(w), np.arange(h))[0] - disparity,
        0, w - 1
    ).astype(np.float32)
    map_y = np.meshgrid(np.arange(w), np.arange(h))[1].astype(np.float32)
    return cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR)

def generate_stereo_pair(image_or_path, baseline_mm=60, focal_mm=26,
                          sensor_width_mm=7.6, image_width=1920):
    """
    Synthesize a stereo pair from a monocular image (for simulation, not real dual-camera).
    image_or_path: image file path (str) or already-loaded numpy image array
    baseline_mm: baseline distance (mm); Apple Vision Pro ~60mm
    Returns: (left_img, right_img, disparity_map)
    """
    # Support both file path and pre-loaded image array
    if isinstance(image_or_path, str):
        img = cv2.imread(image_or_path)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {image_or_path}")
    else:
        img = (image_or_path * 255).astype(np.uint8) if image_or_path.dtype != np.uint8 else image_or_path
    h, w = img.shape[:2]

    # Compute focal length in pixels
    focal_px = focal_mm * image_width / sensor_width_mm  # ≈6600 px

    # Generate disparity map (assume scene depth follows log-normal distribution)
    depth_map = generate_depth_map(h, w, min_depth=0.5, max_depth=10.0)

    # Disparity = baseline * focal / depth
    disparity = (baseline_mm / 1000.0) * focal_px / depth_map

    # Generate right-eye view from disparity (horizontal shift)
    right_img = warp_image_by_disparity(img, disparity)

    return img, right_img, disparity
```

### 6.2 Depth Estimation and Visualization

```python
def stereo_depth_estimation(left_img, right_img, focal_px, baseline_m):
    """
    Use OpenCV Semi-Global Block Matching (SGBM) to estimate disparity map → depth map.
    """
    stereo = cv2.StereoSGBM_create(
        minDisparity=0, numDisparities=128,
        blockSize=5, P1=8*3*5**2, P2=32*3*5**2,
        disp12MaxDiff=1, uniquenessRatio=15,
        speckleWindowSize=100, speckleRange=32,
        preFilterCap=63, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY
    )
    disparity = stereo.compute(
        cv2.cvtColor(left_img, cv2.COLOR_BGR2GRAY),
        cv2.cvtColor(right_img, cv2.COLOR_BGR2GRAY)
    ).astype(np.float32) / 16.0

    # Disparity → depth (meters)
    depth = (focal_px * baseline_m) / (disparity + 1e-6)
    return depth
```

### 6.3 MV-HEVC Metadata Structure Simulation

The Notebook uses Python dict structures to simulate MV-HEVC dual-view metadata storage, including:
- Left/right view frame data (numpy arrays)
- Disparity vector field (per-block, for right-eye prediction efficiency estimation)
- Depth metadata track (16-bit depth map, arranged per HEVC Annex F format)
- File size estimation: based on actual MV-HEVC encoding efficiency parameters

### 6.4 Simulation Results Visualization

Final Notebook output:
- Left and right eye views side-by-side comparison
- Disparity map heatmap (Jet colormap)
- Error distribution histogram: SGBM estimated depth vs. synthesized GT depth
- Simulated Apple Vision Pro disparity adjustment: demonstrates disparity adaptation for near-sighted/far-sighted users by adjusting virtual baseline

---

## §7 References

1. **Apple Vision Pro Technical Overview**, Apple Developer Documentation, 2024. https://developer.apple.com/documentation/visionos
2. **Meta Quest 3 White Paper: Mixed Reality with Color Passthrough**, Meta, 2023. https://www.meta.com/quest/quest-3/
3. **Kerbl B. et al.**, "3D Gaussian Splatting for Real-Time Radiance Field Rendering", *ACM SIGGRAPH 2023*. https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/
4. **MV-HEVC (Multi-View HEVC)**, ISO/IEC 23008-2:2020 Amendment 2, ITU-T H.265.
5. **Apple R1 Chip Architecture**, Apple Newsroom, 2023. https://www.apple.com/newsroom/
6. **Meta Orion AR Glasses Technical Preview**, Meta Connect 2024. https://about.fb.com/news/
7. **Ray-Ban Meta Smart Glasses**, Meta AI, 2023. https://www.ray-ban.com/usa/meta-smart-glasses
8. **Brown D.C.**, "Close-range camera calibration", *Photogrammetric Engineering*, 1971.

---

## §8 Glossary

| Term | Full Name / Description |
|------|------------------------|
| **XR** | Extended Reality; collective term for AR/VR/MR |
| **Spatial Video** | Stereoscopic video format designed for XR headset display; includes left/right eye views |
| **Passthrough** | Video see-through; real world is displayed in real time on the headset screen via cameras |
| **MV-HEVC** | Multi-View High Efficiency Video Coding; multi-view video encoding standard |
| **Stereoscopic** | Stereoscopic vision/photography; uses binocular disparity to create depth perception |
| **Visual Latency** | Time from physical motion to visual perception; XR requires < 20ms |
| **3DGS** | 3D Gaussian Splatting; efficient 3D scene reconstruction and rendering method |
| **SLAM** | Simultaneous Localization and Mapping; real-time device localization and map construction |
| **VOR** | Vestibulo-Ocular Reflex; physiological mechanism that stabilizes gaze during head movement |
| **Warp Map** | Pre-computed distortion correction lookup table; used for real-time GPU texture sampling |
| **Baseline** | Physical distance between the two lenses of a stereoscopic camera; determines depth perception range |
| **FOV** | Field of View |
