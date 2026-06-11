# Part 6, Chapter 07: Portrait Mode Across OEMs — Depth Estimation and Bokeh Rendering Technical Comparison

> **Position:** This chapter systematically compares depth estimation and bokeh rendering technologies in mainstream smartphone portrait modes, starting from the physics of depth of field, and analyzing the depth sensing strategies and bokeh rendering algorithms of Apple, Google, Samsung, Xiaomi, and Huawei.
> **Prerequisites:** Vol.2 Ch.25 (Computational Bokeh), Vol.1 Ch.12 (Depth Sensing), Vol.6 Ch.1 (Consumer Photography Evolution)
> **Audience:** Algorithm engineers, product managers, IQA engineers

---

## §1 Background Theory: Depth of Field Physics and the Motivation for Computational Bokeh

### 1.1 Depth of Field Formula

Optical Depth of Field (DOF) describes the spatial range within which objects in a photographic system are considered "in focus." Under the Circle of Confusion (CoC) model, the approximate DOF formula is:

$$\text{DOF} = \frac{2 \cdot f^2 \cdot c \cdot d^2 \cdot F}{f^4 - c^2 \cdot d^2 \cdot F^2}$$

where:
- $f$: lens focal length (mm)
- $c$: maximum acceptable circle of confusion diameter (mm), dependent on output size and viewing distance; standard 35 mm cameras typically use $c = 0.029$ mm
- $d$: distance from subject to lens (m)
- $F$: f-number (F/#)

When $c^2 \cdot d^2 \cdot F^2 \ll f^4$ (i.e., when the aperture is not extremely wide), the formula simplifies to:

$$\text{DOF} \approx \frac{2 \cdot c \cdot d^2 \cdot F}{f^2}$$

From this simplified form, the fundamental challenge of smartphone photography becomes immediately apparent:

| Parameter | Professional DSLR/mirrorless | Smartphone main camera (1/1.28-inch) |
|-----------|------------------------------|--------------------------------------|
| Equivalent focal length $f$ | 85 mm (portrait lens) | 24 mm (equivalent) |
| Physical focal length | 85 mm | **5.6 mm** |
| Maximum aperture | f/1.4 | f/1.8 |
| Typical shooting distance | 2 m | 1 m |

Plugging in numbers:

$$\text{DOF}_\text{DSLR} \approx \frac{2 \times 0.029 \times 4 \times 1.4}{85^2} \approx 0.0032\ \text{m} = 3.2\ \text{mm}$$

$$\text{DOF}_\text{smartphone} \approx \frac{2 \times 0.029 \times 1 \times 1.8}{5.6^2} \approx 0.0033\ \text{m}$$

Wait — the numbers look similar? The key lies in the scale of the "equivalent circle of confusion": a smartphone sensor is approximately **17×** smaller than full-frame, so the same physical CoC diameter translates to a completely different visual size in the final output. Scaling to equivalent output print size, the smartphone's equivalent $c_\text{equiv} \approx 0.029 / 17 \approx 0.0017$ mm, giving:

$$\text{DOF}_\text{smartphone (output-equivalent)} \approx \frac{2 \times 0.029 \times 1 \times 1.8 \times 17}{5.6^2} \approx 56\ \text{mm} = 5.6\ \text{cm}$$

A professional portrait lens at the same output size gives only 3.2 mm. **The equivalent depth of field on a smartphone is approximately 17× that of a full-frame camera**, making natural background blur nearly impossible — which is the fundamental motivation for Computational Bokeh.

### 1.2 Computational Bokeh Pipeline Overview

The standard computational bokeh pipeline (independent of specific implementation):

```
Input image (RGB + optional depth/distance information)
        │
        ▼
Depth Estimation
 ── Stereo disparity / Structured light / ToF / ML monocular / LiDAR
        │
        ▼
Subject Segmentation
 ── Semantic segmentation (person/animal/object) + depth-aware edge refinement
        │
        ▼
Bokeh Rendering
 ── Depth-proportional blur kernel
 ── Occlusion-aware rendering
 ── Aperture shape simulation
        │
        ▼
Compositing
 ── Sharp foreground + blurred background blending
 ── Local color/luminance adjustment (Portrait Lighting)
```

---

## §2 Depth Estimation Methods

### 2.1 Dual-Camera Stereo Disparity (iPhone 7 Plus, 2016)

Apple first mass-produced computational portrait mode on the **iPhone 7 Plus (2016)**, using a wide-angle (28 mm equivalent) + telephoto (56 mm equivalent) dual-camera combination to estimate scene depth via stereo disparity.

**Stereo disparity principle:**

Let a point $P$ in the left (wide-angle) camera coordinate system project to pixel coordinates $(u_L, v_L)$ in the left image and $(u_R, v_R)$ in the right image (telephoto, after focal length normalization). Disparity is defined as:

$$d = u_L - u_R$$

Depth is recovered using the baseline $b$ and focal length $f_L$:

$$Z = \frac{b \cdot f_L}{d}$$

**Engineering constraints of iPhone dual camera:**

- Baseline is limited by the phone width: approximately **16–18 mm** (from the 7 Plus to 15 Pro Max dual-camera separation)
- At a 1 m shooting distance, disparity is only approximately 1–2 pixels, yielding depth accuracy of approximately **±15–25 cm**
- Occlusion: background areas near subject edges are visible in only one camera, causing depth estimation failure and unclean virtual/real segmentation at edges ("halo" artifacts)
- Focal length disparity: the wide and telephoto fields of view differ substantially; view matching requires projective (homographic) warping, which introduces error in non-planar scenes

Apple patent US10250871B2 (2017) describes a layered depth estimation strategy: coarse depth from stereo disparity, edge regions refined by semantic segmentation. Final depth map resolution is approximately 1/4 of the original image.

### 2.2 Monocular ML Depth Estimation (Google Pixel 1, 2016)

Google's breakthrough contribution was achieving portrait mode on the **Pixel 1 (2016)** with a **single camera** (originally named Lens Blur, later upgraded to Portrait Mode). Depth came not from stereo disparity but from deep learning-based monocular depth estimation.

**Network architecture:** Google used a **MobileNet** backbone (MobileNetV1, Howard et al., 2017), fine-tuned via transfer learning for portrait scenes:
- Training data: synthetically rendered portraits (Synthetic, with precise depth labels) + real binocularly captured portraits (Real paired)
- Input: single RGB image (cropped to portrait ROI)
- Output: **relative depth map** — not metric depth (no absolute distance value, only front/back ordering)

Fundamental limitation of monocular depth:

$$Z_\text{metric} = Z_\text{mono} \cdot s + t$$

Scale ($s$) and offset ($t$) cannot be recovered geometrically from a single image and must rely on scene priors (e.g., statistical priors on human face size, or focal length inference). Google's approach depends on human body detection (face/body detection) to provide scale constraints — which is also why early Pixel portrait mode only worked well for human subjects; non-human subjects performed poorly.

**Improvement trajectory:**

| Version | Depth method | Key improvement |
|---------|-------------|-----------------|
| Pixel 1 (2016) | Monocular MobileNet | Portrait only, relies on face prior |
| Pixel 2 (2017) | Dual-core PDAF | Uses PDAF signal to assist depth (similar to Dual Pixel weak stereo) |
| Pixel 4 (2019) | Dual camera + ML | Super-resolution depth + Neural Bokeh |
| Pixel 8 Pro (2023) | LiDAR-assisted + ZoeDepth | Any subject portrait, metric depth |

### 2.3 TrueDepth Structured Light (iPhone X Front Camera, 2017)

Apple introduced the **TrueDepth** structured light system on the front camera of the **iPhone X (2017)**, dedicated to Face ID face recognition and front-facing portrait mode.

**Hardware components:**
- IR dot projector: projects **30,000** infrared structured light points onto the face
- IR camera: captures the infrared image of the distorted structured light pattern
- Flood illuminator: provides uniform infrared illumination as an aid

**Depth calculation principle (triangulation):**

The projector emits a fixed codified pattern from a known position. The IR camera observes the distortion (disparity map) of the pattern relative to a planar calibration reference. Given the baseline distance between projector and camera plus triangulation geometry, each point's depth is computed:

$$Z = \frac{b \cdot f_\text{IR}}{d_\text{pattern}}$$

Depth accuracy: **0.5 mm @ 1 m** (Apple Face ID specification, from Apple WWDC 2017 technical session), far superior to dual-camera stereo (±15 cm).

Limitation: only works at close range (< 70 cm) for front-facing portrait; strong outdoor sunlight can interfere with the infrared pattern (IR flooding from sunlight).

### 2.4 ToF Sensor (Huawei P30 Pro, 2019)

**Time-of-Flight (ToF)** sensor measurement principle: emit an infrared light pulse and measure photon flight time to calculate distance:

$$Z = \frac{c \cdot \Delta t}{2}$$

where $c = 3 \times 10^8$ m/s is the speed of light and $\Delta t$ is the round-trip flight time. Using the Sony IMX316 ToF sensor (as used in the Huawei P30 Pro) as an example:
- Depth accuracy: **approximately 1 cm @ 1 m** (indoor standard conditions)
- Effective range: 0.1–4 m
- Resolution: **240 × 180** (far below the RGB main camera; depth super-resolution up-sampling is required)
- Advantage: active IR emission means it works in low light and nighttime portrait mode equally well

**The necessity of depth super-resolution:** ToF sensor resolution is typically only 1/50–1/100 of the main camera. Merging a 240×180 depth map with a 4000×3000 RGB image produces "depth bleeding" at edges — foreground colors "bleed into" background blur areas. The solution is Joint Bilateral Upsampling (JBU):

$$Z_\text{upsampled}(x, y) = \frac{\sum_{p \in \mathcal{N}} Z_\text{ToF}(p) \cdot \exp\left(-\frac{\|x - p\|^2}{2\sigma_s^2} - \frac{\|I_\text{RGB}(x) - I_\text{RGB}(p)\|^2}{2\sigma_r^2}\right)}{\sum_{p \in \mathcal{N}} \exp(\ldots)}$$

The color similarity term (controlled by $\sigma_r$) ensures that depth interpolation near color boundaries proceeds along color edges rather than across them, suppressing depth bleeding.

### 2.5 LiDAR (iPhone 12 Pro, 2020)

Apple introduced the **LiDAR Scanner** (Light Detection and Ranging) in the **iPhone 12 Pro (2020)**, representing the current highest-specification depth sensing solution in smartphone photography.

Difference from ToF sensors:
- **ToF (indirect measurement):** Emits continuously modulated IR light and calculates flight time via phase shift; suffers from ambiguity with multiple-target reflections.
- **LiDAR (direct measurement):** Emits single laser pulses and measures flight time directly via precision timing (Single Photon Avalanche Diode, SPAD); higher accuracy.

iPhone 14 Pro LiDAR specifications:
- Effective measurement range: **approximately 5 m** (indoor), approximately 3 m outdoors (sunlight interference)
- Depth accuracy: **< 1 cm @ 1 m** (indoor)
- Frame rate: 60 fps (paired with ProMotion 120 Hz display for AR applications)
- Resolution: approximately **320 × 240** SPAD array (Apple has not disclosed this; estimated value)

Core advantages of LiDAR in portrait photography:
1. Low-light/nighttime portrait: LiDAR actively emits light, independent of ambient illumination; dark-scene depth accuracy matches daytime performance.
2. Instant AR: depth latency approximately 1 ms (no feature matching needed); AR objects snap instantly to the real environment.
3. Precise foreground separation: 1 cm-level depth accuracy gives hair-strand-level foreground/background separation a reliable depth prior.

---

## §3 Bokeh Rendering Algorithms

### 3.1 Depth-Proportional Gaussian Blur (Basic Approach)

The simplest computational bokeh implementation: for each background pixel, the blur radius is computed based on the difference between its depth value $Z(x,y)$ and the focus plane depth $Z_f$:

$$r(x,y) = k \cdot \left|\frac{1}{Z_f} - \frac{1}{Z(x,y)}\right| \cdot f^2 / (F \cdot p)$$

where $k$ is a scaling factor and $p$ is the sensor pixel size (after equivalence). A Gaussian blur of radius $r$ is applied to each background pixel:

$$I_\text{blurred}(x, y) = G_r * I(x, y), \quad G_r(u,v) = \frac{1}{2\pi r^2} \exp\left(-\frac{u^2 + v^2}{2r^2}\right)$$

**Limitations:** The Gaussian blur kernel is circularly symmetric and has no occlusion awareness, producing two characteristic artifacts:
1. **Edge halo:** Near foreground subject edges, the color of the blurred background region leaks onto the foreground outline, forming a bright-colored border.
2. **Occlusion error:** Background areas that should be occluded behind near-foreground objects are "contaminated" by the foreground blur signal.

### 3.2 Occlusion-Aware Disk Blur

In a real optical system, bokeh shape is determined by the aperture shape — a circular aperture produces disk-shaped blur spots, not Gaussian roll-off. Improved disk blur:

$$I_\text{disk}(x,y) = \frac{1}{|D_r|} \sum_{(u,v) \in D_r} I(x+u, y+v)$$

where $D_r = \{(u,v) : u^2 + v^2 \leq r^2\}$ is the disk kernel of radius $r$.

The key idea of **Occlusion-Aware Rendering**: during the blur integral, only neighboring pixels with depth greater than (farther than) the current pixel contribute; pixels that are closer do not participate (because they "block" the current pixel):

$$I_\text{occ}(x,y) = \frac{\sum_{(u,v) \in D_r} I(x+u, y+v) \cdot \mathbb{1}[Z(x+u,y+v) \geq Z(x,y) - \delta]}{\sum_{(u,v) \in D_r} \mathbb{1}[Z(x+u,y+v) \geq Z(x,y) - \delta]}$$

$\delta$ is the depth tolerance, preventing depth noise from causing erroneous occlusion.

### 3.3 Neural Bokeh

**Google Neural Bokeh** (Wadhwa et al., CVPR 2018 / SIGGRAPH 2018) is a landmark end-to-end deep learning bokeh rendering work. It trains a generative network aimed at "mimicking the blur of a real full-frame camera" using the weak stereo information from Pixel 2's dual-core PDAF.

Network structure (U-Net variant):
- Input: RGB image + depth map (dual channel) → encoder-decoder architecture
- Intermediate layers: multi-scale feature fusion (Dilated Convolutions)
- Output: directly outputs a rendered bokeh image (end-to-end; no explicit blur kernel computation)

Training data: Dual Pixel left/right sub-pixel disparity used as weakly supervised depth, paired with full-frame camera images of the same scene as the ground-truth reference bokeh.

**Core advantages of Neural Bokeh:**
- Implicitly learns occlusion handling, edge transitions, and bokeh ball shapes without explicit geometric modeling;
- Significantly outperforms explicit algorithms on hair strands, fur, and semi-transparent objects (e.g., wedding veils), since depth estimation is unreliable in these areas and the network can infer segmentation boundaries implicitly from texture features;
- Apple Portrait Lighting (Apple, WWDC 2017) is an early commercial implementation of a similar approach, adding the ability to manipulate face lighting direction.

### 3.4 Aperture Shape Simulation

High-end bokeh systems support simulation of different aperture shapes:
- **Circular aperture:** Produces circular bokeh balls, as in a Sony 35 mm f/1.4;
- **Hexagonal aperture:** As in classic Zeiss lenses, producing hexagonal bokeh balls;
- **Cat-eye bokeh (Coma bokeh):** Circular near the center, elliptical toward the edges, simulating coma aberration;
- **Swirly bokeh:** Simulates the distinctive rotating bokeh of Soviet lenses such as the Helios 44M-4, used in artistic photography.

Implementation: replace the standard disk blur kernel with a template matching the target shape (aperture mask), or apply the aperture's Optical Transfer Function (OTF) in the frequency domain (via FFT multiplication) to impose a specific blur shape. Samsung Galaxy S24 Ultra portrait mode supports post-capture adjustment of bokeh shape (circular/hexagonal/star), which is implemented by switching the OTF kernel and re-rendering.

### 3.5 Samsung Expert RAW and DSLR Connect

Samsung's **Expert RAW** app supports a **DSLR Connect** mode: professional camera photos (transferred via cable or Bluetooth) are combined with the phone's AI processing. Precise depth is extracted from the professional camera's RAW file, then the phone ISP's super-resolution and skin enhancement pipeline re-renders the image. The technical approach essentially outsources "depth acquisition" to professional hardware while completing "rendering and processing" on the phone.

---

## §4 Subject Segmentation

### 4.1 Semantic Segmentation Backbone

Subject segmentation in mainstream portrait modes is based on deep neural networks:

**DeepLabv3+ (Google, 2018)** is the classic architecture for background segmentation:
- Encoder: Xception/MobileNetV2 + Atrous Spatial Pyramid Pooling (ASPP)
- Decoder: bilinear upsampling + skip connection edge refinement
- mIoU ≈ 89% on Portrait Segmentation task (COCO-Person)

**Segment Anything Model (SAM, Meta, ICCV 2023)** represents a new paradigm in universal segmentation:
- Uses promptable segmentation, accepting any prompt such as clicks or bounding boxes
- On mobile, SAM-Mobile (lightweight variant, approximately 10 M parameters) supports < 100 ms inference

### 4.2 Hair-Strand Edge Refinement

Hair strands are the definitive test case for portrait mode quality. Hair strand diameter is approximately 0.06 mm, corresponding to 0.1–0.3 pixels on a smartphone sensor. Depth estimation at hair strands is typically unreliable (depth is confused with the background).

Specialized processing approaches:

**Approach A (depth-independent, color + texture segmentation):** Use high-frequency edge detection (Canny/HED) to find hair outlines in the color domain, then fuse with the semantic segmentation confidence map (confidence map) using weighted blending. In hair regions, color edges are trusted over depth boundaries.

**Approach B (Transparency / Alpha Matte):** Model hair regions as mixed pixels, estimating an Alpha matte:

$$I_\text{mixed}(x,y) = \alpha(x,y) \cdot F(x,y) + (1 - \alpha(x,y)) \cdot B(x,y)$$

where $F$ is the foreground color, $B$ is the background color, and $\alpha \in [0,1]$ is the mixing ratio. By optimizing the $\alpha$ value at each edge pixel, partial transmission of foreground color can be achieved during background blurring, avoiding hard cutoffs at hair outlines. Advances in iPhone 15 Pro portrait mode hair handling primarily derive from refined training of an Alpha Matting network.

### 4.3 Transparent Objects and Glasses

Eyeglasses are the classic challenge for portrait mode:
- Lenses should be transparent (depth connects to background)
- Frames are foreground (same depth as the face)
- Reflective areas on the lens are often erroneously estimated as "infinity" (specular highlights are confused with background)

Approaches by different vendors:
- **iPhone (2022+):** Specifically trained a "glasses-aware" segmentation model that recognizes eyeglass frames as face-associated foreground while keeping lenses transparent (no blur applied);
- **Google Pixel 8:** Uses LiDAR depth + RGB segmentation for joint inference; lens depth is interpolated from neighboring skin depth;
- **Huawei P60 Pro:** XD Portrait algorithm with dedicated recognition and annotation training for eyeglass frames/lenses.

### 4.4 Multi-Person Scenes and Multi-Depth Layers

Portrait mode in multi-person scenes (e.g., group photos) must handle multiple independent depth layers:

1. **Depth ordering:** Sort all persons by depth from the depth map; the nearest person should be sharpest;
2. **Per-subject focus:** Allow users to select which person to focus on in post-capture (as in Samsung Galaxy S24's "refocus after capture" feature), which is essentially re-parameterizing the depth map;
3. **Transition zones:** The airspace between two people needs a smooth blur gradient to avoid abrupt discontinuities in blur level between subjects.

---

## §5 Vendor Comparison

The following comparison uses 2023–2024 flagship devices: iPhone 15 Pro / Pixel 8 Pro / Samsung Galaxy S24 Ultra / Xiaomi 14 Ultra / Huawei P60 Pro.

### 5.1 Depth Acquisition Comparison

| Vendor / Model | Primary Depth Method | Auxiliary Method | Depth Accuracy (estimate) | Night Depth |
|----------------|---------------------|------------------|--------------------------|-------------|
| Apple iPhone 15 Pro | LiDAR (rear) + TrueDepth (front) | ML depth (auxiliary interpolation) | < 1 cm @ 1 m | Excellent (LiDAR active) |
| Google Pixel 8 Pro | ZoeDepth ML + Dual Pixel micro-stereo | PDAF signal assist | ±3 cm @ 1 m | Good (ZoeDepth model) |
| Samsung Galaxy S24 Ultra | Dual Pixel (100% coverage) + ML depth | Dual-camera disparity (telephoto assist) | ±5 cm @ 1 m | Medium (relies on ambient light) |
| Xiaomi 14 Ultra | Dual-camera stereo + ML depth (Leica tuning) | No ToF | ±8 cm @ 1 m | Medium |
| Huawei P60 Pro | ToF + ML depth | Dual-camera disparity | ±2 cm @ 1 m (within ToF range) | Good (ToF active IR) |

### 5.2 Bokeh Rendering Comparison

| Vendor / Model | Bokeh Algorithm | Subject Segmentation | Aperture Simulation Range | Hair Quality | Video Portrait |
|----------------|-----------------|---------------------|--------------------------|--------------|----------------|
| Apple iPhone 15 Pro | Neural Bokeh + physical occlusion model | SAM-style + Alpha Matting | f/1.4–f/16 (adjustable in post) | ★★★★★ (industry best) | Supported (4K30) |
| Google Pixel 8 Pro | Neural Bokeh v3 (end-to-end CNN) | DeepLab + depth weighting | f/1.7–f/16 | ★★★★☆ | Supported (4K30) |
| Samsung Galaxy S24 Ultra | Expert Portrait Engine + aperture shape library | SEMP (Samsung proprietary) + depth-aware | f/1.7–f/22 (hexagonal/circular) | ★★★★☆ | Supported (4K60) |
| Xiaomi 14 Ultra | Leica Natural + Leica Vivid bokeh modes | Leica-tuned segmentation model | f/1.63–f/16 | ★★★☆☆ | Supported (4K30) |
| Huawei P60 Pro | XD Portrait (end-to-end + depth-guided) | XD Fusion + dedicated hair network | f/0.95–f/16 (variable aperture) | ★★★★☆ | Supported (4K30) |

### 5.3 Special Features Comparison

| Vendor / Model | Special Features |
|----------------|-----------------|
| Apple iPhone 15 Pro | **Portrait Lighting** (6 virtual studio lighting effects, real-time face relighting); **Photonic Engine** (multi-frame RAW merge before segmentation, reducing noise-induced edge jitter) |
| Google Pixel 8 Pro | **Best Take** (automatically selects the best expression of each person from multi-frame composites); **Magic Eraser Portrait** (removes background distractions before blurring) |
| Samsung Galaxy S24 Ultra | **Post-capture aperture adjustment** (slide in gallery to adjust blur level after shooting); **Expert RAW DSLR Connect**; **Video Portrait 4K60** |
| Xiaomi 14 Ultra | **Leica Professional Bokeh Mode** (Leica Authentic style rendering including LEITZ lens flare feature simulation); **Variable aperture f/1.63–f/4.0** (physical variable aperture) |
| Huawei P60 Pro | **Physical variable aperture f/0.95–f/4.0** (largest smartphone aperture globally); **RYYB sensor-assisted low-light portrait** |

---

## §6 Code Examples

Full runnable code is available in *See §6 Code section for runnable examples.*, covering:

### 6.1 Single-Image Depth Estimation and Bokeh Rendering Pipeline

```python
# Complete computational bokeh simulation pipeline
import numpy as np
import cv2
from PIL import Image

def estimate_depth_midas(image_rgb, model_type='DPT_Large'):
    """
    Monocular depth estimation using MiDaS.
    Input:  RGB image (H, W, 3)
    Output: relative depth map (H, W); larger values = closer (MiDaS outputs inverse depth)
    """
    import torch
    import torchvision.transforms as transforms

    # Load MiDaS model (pre-downloaded weights required)
    model = torch.hub.load('intel-isl/MiDaS', model_type)
    model.eval()

    transform = torch.hub.load('intel-isl/MiDaS', 'transforms').dpt_transform

    img_tensor = transform(image_rgb).unsqueeze(0)
    with torch.no_grad():
        prediction = model(img_tensor)
        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=image_rgb.shape[:2],
            mode='bicubic', align_corners=False
        ).squeeze()
    depth = prediction.cpu().numpy()
    # Normalize: 0 = farthest, 1 = closest
    depth = (depth - depth.min()) / (depth.max() - depth.min())
    return depth

def depth_aware_bokeh(image, depth_map, focus_depth=0.6,
                      max_blur_radius=25, aperture_shape='circle'):
    """
    Depth-aware bokeh rendering.
    focus_depth:     focal plane depth (0 = farthest, 1 = closest)
    max_blur_radius: maximum blur radius (pixels)
    """
    H, W = image.shape[:2]
    result = image.copy().astype(np.float32)

    # Compute blur radius per pixel (larger depth difference → larger radius)
    blur_strength = np.abs(depth_map - focus_depth)
    blur_radii = (blur_strength * max_blur_radius).astype(int)
    blur_radii = np.clip(blur_radii, 0, max_blur_radius)

    # Layered rendering: group by blur radius (avoids O(N²) per-pixel complexity)
    unique_radii = np.unique(blur_radii[blur_radii > 1])

    layer_accum = np.zeros_like(result)
    weight_accum = np.zeros((H, W, 1), dtype=np.float32)

    for r in unique_radii[::2]:  # process every other level (quality/speed trade-off)
        mask = (blur_radii == r).astype(np.float32)
        kernel_size = 2 * r + 1

        # Apply circular kernel convolution (simulating circular aperture)
        if aperture_shape == 'circle':
            kernel = np.zeros((kernel_size, kernel_size), np.float32)
            cy, cx = r, r
            Y, X = np.ogrid[:kernel_size, :kernel_size]
            circle_mask = (X - cx)**2 + (Y - cy)**2 <= r**2
            kernel[circle_mask] = 1.0 / circle_mask.sum()
        elif aperture_shape == 'hexagon':
            kernel = create_hexagon_kernel(r)

        blurred = cv2.filter2D(image.astype(np.float32), -1, kernel)
        weight = cv2.GaussianBlur(mask, (kernel_size, kernel_size), r/2)
        weight = weight[:, :, np.newaxis]
        layer_accum += blurred * weight
        weight_accum += weight

    # Foreground region (no blur)
    sharp_mask = (blur_radii <= 1).astype(np.float32)[:, :, np.newaxis]
    final = (layer_accum / (weight_accum + 1e-8)) * (1 - sharp_mask) + \
            image.astype(np.float32) * sharp_mask

    return np.clip(final, 0, 255).astype(np.uint8)

def create_hexagon_kernel(r):
    """Create a hexagonal aperture blur kernel (simulates hexagonal bokeh balls)."""
    size = 2 * r + 1
    kernel = np.zeros((size, size), np.float32)
    for y in range(size):
        for x in range(size):
            dx, dy = abs(x - r), abs(y - r)
            # Hexagon test
            if dx <= r and dy <= r * np.sqrt(3)/2 and \
               (dx / r + dy / (r * np.sqrt(3)/2)) <= 1.0:
                kernel[y, x] = 1.0
    kernel /= kernel.sum() + 1e-8
    return kernel
```

### 6.2 Depth Quality Evaluation and Method Comparison

```python
def compare_bokeh_methods(image, ground_truth_depth=None):
    """
    Compare image quality across four bokeh approaches:
    1. Fixed Gaussian blur (no depth awareness)
    2. Depth-proportional Gaussian blur
    3. Depth-proportional disk blur (occlusion-aware)
    4. Neural bokeh (simplified simulation)
    """
    results = {}

    # Method 1: Fixed Gaussian blur (control group)
    results['Fixed Gaussian'] = cv2.GaussianBlur(image, (51, 51), 15)

    # Method 2: Depth-proportional Gaussian blur
    if ground_truth_depth is not None:
        depth = ground_truth_depth
    else:
        depth = estimate_depth_midas(image)  # use MiDaS estimation

    results['Depth-Gaussian'] = depth_aware_bokeh(image, depth,
                                                   aperture_shape='circle')

    # Method 3: Hexagonal aperture
    results['Hexagon-Bokeh'] = depth_aware_bokeh(image, depth,
                                                  aperture_shape='hexagon')

    # Metric: SSIM (edge preservation relative to fully blurred version)
    from skimage.metrics import structural_similarity as ssim
    for name, result in results.items():
        score = ssim(image, result, channel_axis=2)
        print(f"{name}: SSIM with original = {score:.4f}")

    return results
```

The code also demonstrates:
- ZoeDepth (metric depth estimation, kv-jiang/ZoeDepth, arXiv 2023) depth map visualization on real portrait images
- Alpha Matting hair strand segmentation results (using `pymatting` library)
- Zoomed local comparison of each method in "hair edge" regions
- Video portrait mode frame-to-frame depth stability simulation (preventing depth jitter-induced blur flickering)

---

## §7 Artifacts and Tuning Guidelines

### 7.1 Depth Bleeding

**Symptom:** Foreground subject colors (e.g., a person's red clothing) "bleed into" the blurred background region, creating a colored halo around the subject edge in the background.

**Root cause:** Low depth map resolution (ToF/LiDAR); depth discontinuities at color boundaries are smoothed, causing foreground depth values to "spread" into the background region. That region is erroneously treated as "foreground" and no blur is applied.

**Mitigation:** Joint Bilateral Upsampling (JBU); or use RGB color edges as hard constraints on depth boundaries, estimating depth independently on both sides of a color edge.

### 7.2 Bokeh Halo / Ring Effect

**Symptom:** An unnaturally bright outline appears around the foreground subject contour, especially visible in backlit or high-contrast scenes.

**Root cause:** The subject segmentation Alpha matte has $\alpha \approx 0.5$ at the contour. After background blurring, the blended result at the contour is weighted between foreground and background colors incorrectly; if the background is brighter than the foreground, the composite at the contour is brighter than expected, creating a halo.

**Mitigation:** Pre-multiplied alpha compositing — use $\alpha \cdot F + (1-\alpha) \cdot \text{BlurredB}$ instead of $\alpha \cdot F + (1-\alpha) \cdot B$, ensuring the blurred background color (not the original background color) is used at the contour.

### 7.3 Depth Jitter (Video Portrait Mode)

**Symptom:** In video portrait mode, the blur boundary shifts slightly frame-to-frame, causing the background blur depth to fluctuate continuously, visually presenting as background "flickering."

**Root cause:** ML depth estimation (e.g., MiDaS) performs independent inference per frame; the depth estimate for the same spatial location fluctuates between adjacent frames due to random error, causing the foreground/background classification at the edge to toggle frame-by-frame.

**Mitigation:**
1. Temporal depth filtering: $Z_t^* = (1-\lambda) Z_{t-1}^* + \lambda Z_t$ (exponential moving average, $\lambda = 0.3–0.5$);
2. Temporal consistency constraint on segmentation mask (Temporal Consistency Loss training);
3. Prefer physically measured LiDAR/ToF depth (more stable noise characteristics, better temporal consistency).

---

## References

1. **Wadhwa, N., Garg, R., Jacobs, D. E., et al.** (2018). Synthetic shallow depth of field with a single-camera mobile phone. *ACM Transactions on Graphics (SIGGRAPH 2018)*, 37(4), 64. DOI: 10.1145/3197517.3201329.

2. **Apple Inc.** (2017). Portrait Mode Photography. *Apple WWDC 2017 Session 508: Advances in Mobile Camera Technology*. https://developer.apple.com/wwdc17/508

3. **Ranftl, R., Bochkovskiy, A., & Koltun, V.** (2021). Vision transformers for dense prediction (DPT/MiDaS). *ICCV 2021*. https://arxiv.org/abs/2103.13413

3b. **Yang, L., Kang, B., Huang, Z., et al.** (2024). Depth Anything V2. *NeurIPS 2024*. https://arxiv.org/abs/2406.09414 [Compared to Depth Anything V1 (CVPR 2024), V2 uses synthetic data augmentation during training, achieving significantly improved robustness on fine edges and low-light scenes — more suitable for smartphone portrait depth estimation]

4. **Bhat, S. F., Birkl, R., Wofk, D., Wonka, P., & Müller, M.** (2023). ZoeDepth: Zero-shot Transfer by Combining Relative and Metric Depth. *arXiv preprint arXiv:2302.12288*. https://arxiv.org/abs/2302.12288

5. **Kirillov, A., Mintun, E., Ravi, N., et al.** (2023). Segment Anything. *ICCV 2023*. https://arxiv.org/abs/2304.02643

6. **Chen, L. C., Zhu, Y., Papandreou, G., Schroff, F., & Adam, H.** (2018). Encoder-decoder with atrous separable convolution for semantic image segmentation (DeepLabv3+). *ECCV 2018*. https://arxiv.org/abs/1802.02611

7. **Howard, A. G., Zhu, M., Chen, B., et al.** (2017). MobileNets: Efficient convolutional neural networks for mobile vision applications. *arXiv:1704.04861*. https://arxiv.org/abs/1704.04861

8. **Kopf, J., Cohen, M. F., Lischinski, D., & Uyttendaele, M.** (2007). Joint bilateral upsampling. *ACM SIGGRAPH 2007*, 96. DOI: 10.1145/1275808.1276497.

9. **Levin, A., Lischinski, D., & Weiss, Y.** (2008). A closed-form solution to natural image matting. *IEEE TPAMI*, 30(2), 228–242.

10. **DPReview Staff** (2024). Smartphone Portrait Mode Comparison 2024. *DPReview*. https://www.dpreview.com/

---

*Chapter 7 End*

---

## §8 Glossary

**Depth of Field (DOF)**
The spatial range along the optical axis within which objects are considered "in focus" (sharp) in a photographic system, jointly determined by focal length, f-number, subject distance, and circle of confusion size. A smartphone's physical focal length is far smaller than a full-frame camera's, resulting in an equivalent DOF approximately 17× larger — making natural background blur virtually impossible and providing the fundamental motivation for computational bokeh.

**Circle of Confusion (CoC)**
The blur spot (circular diffusion disk) formed on the image plane by a point that is not exactly in focus. When the CoC diameter is smaller than the minimum detail resolvable by the human eye, the object is considered "in focus." The CoC standard depends on the output image size and viewing distance; the 35 mm full-frame standard is approximately 0.029 mm.

**Disparity**
In stereo vision, the horizontal offset (in pixels) between the projections of the same scene point on the left and right camera images. Disparity is inversely proportional to depth: $Z = b \cdot f / d$, where $b$ is the baseline, $f$ is the focal length, and $d$ is the disparity. Dual-camera smartphones have a baseline of approximately 16–18 mm; at a 1 m distance this yields only approximately 1–2 pixels of disparity, giving depth accuracy of approximately ±15–25 cm.

**Bokeh**
From the Japanese 「ボケ」(boke), referring to the out-of-focus blur in areas outside the focal plane and its visual aesthetic. Different lenses produce characteristic bokeh styles (circular, hexagonal, swirly, etc.) depending on the number and shape of aperture blades and their aberration characteristics. Computational bokeh simulates this physical process algorithmically.

**TrueDepth (Structured Light Depth Sensing)**
An active depth sensing system introduced on the front camera of the iPhone X, consisting of an IR dot projector (30,000 points), an IR camera, and a flood illuminator. Depth is obtained by triangulating the displacement of the dot pattern, with accuracy of approximately 0.5 mm @ 1 m. Primarily used for Face ID and front-facing portrait mode.

**Neural Bokeh**
An end-to-end deep learning method for generating bokeh images. Takes an RGB image and depth map as input and directly outputs a rendered bokeh image, without explicit blur kernel computation. Neural bokeh implicitly learns occlusion handling, edge transitions, and bokeh ball shapes; it excels in challenging areas such as hair strands, fur, and semi-transparent objects. Google SIGGRAPH 2018 and Apple Portrait Lighting are representative commercial implementations.

**Alpha Matting**
Modeling image edge pixels as a linear blend of foreground and background ($I = \alpha \cdot F + (1-\alpha) \cdot B$), then optimizing the $\alpha$ value (continuous, 0–1) at each edge pixel to achieve fine foreground/background separation. Compared to binary segmentation ($\alpha \in \{0, 1\}$), Alpha Matting produces more natural transitions in semi-transparent detail areas such as hair and fine fur, and is the core technology for high-quality portrait mode hair segmentation.

**Joint Bilateral Upsampling (JBU)**
Uses color boundary information from a high-resolution RGB image to guide super-resolution interpolation of a low-resolution depth map, aligning depth boundaries with color boundaries to prevent "depth bleeding" (color leakage across object boundaries during low-resolution depth map interpolation). Standard pre-processing for ToF/LiDAR depth map upsampling.

**Depth Bleeding**
A classic artifact in bokeh rendering, in which foreground colors "bleed into" the blurred background region, creating a colored halo at the subject edge. The root cause is insufficient depth map resolution: depth discontinuities at color boundaries are smoothed, causing foreground regions to incorrectly extend into background areas without blur. Significantly mitigated by JBU or RGB edge-based depth post-processing.
