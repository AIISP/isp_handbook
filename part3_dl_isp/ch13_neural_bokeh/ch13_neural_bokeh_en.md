# Part 3, Chapter 13: Neural Bokeh and Semantic Depth-of-Field Estimation

> **Scope:** This chapter covers deep-learning-based computational bokeh (神经散景) algorithms, from monocular depth estimation to semantics-aware defocus rendering. For traditional computational bokeh see Volume 2, Chapter 27.
> **Prerequisites:** Volume 2, Chapter 27 (Computational Bokeh); Volume 1, Chapter 12 (Depth Sensing); Volume 3, Chapter 1 (DL ISP Overview)
> **Target Readers:** Algorithm engineers, deep learning researchers

---

## §1 Theory

### 1.1 The Optical Nature of Bokeh

Real-lens bokeh (散景) originates from the circle of confusion (CoC, 弥散斑) produced by out-of-focus objects under a large aperture (low f-number). The CoC diameter is:

$$
c = \frac{f^2}{N \cdot (d_o - f)} \cdot \frac{|d_o - d_f|}{d_o}
$$

where $f$ is the focal length, $N$ is the f-number, $d_o$ is the object distance, and $d_f$ is the focus distance. A larger CoC produces stronger background blur.

Smartphone lenses are limited by their physical sensor size (1/1.3" to 1/3"). Even at the widest aperture (f/1.5 to f/1.9), the CoC is far smaller than that of a full-frame DSLR (f/1.2, sensor ≥ 1"). **Computational bokeh (计算散景)** uses algorithms to simulate an equivalent large-aperture effect and bridge this physical gap.

### 1.2 The Relationship Between Depth Estimation and Bokeh

Computational bokeh requires two core modules:

1. **Depth map estimation (景深图估计):** Estimate the distance from each pixel to the camera (relative or absolute).
2. **Depth-aware blur rendering (深度感知虚化渲染):** Apply blur kernels of varying strength to different depth regions according to the depth map.

The introduction of neural networks addresses two key limitations of traditional stereo/ToF approaches:
- A monocular camera cannot directly measure distance; traditional methods rely on dual cameras or laser ranging.
- Segmentation-based "portrait mode" can only handle human-body regions and cannot generalize to complex scenes.

### 1.3 Ambiguity in Monocular Depth Estimation

The mapping from a single RGB frame to absolute depth is an ill-posed problem. Mainstream methods bypass absolute depth and instead estimate:
- **Relative depth (相对深度):** Describes only ordinal front-back relationships; sufficient for bokeh rendering (absolute distance values are not needed).
- **Affine-invariant depth (仿射不变深度):** The scale and offset of depth values are undetermined; common in general-purpose methods such as MiDaS.

For bokeh applications, relative depth is sufficient: knowing which regions are farther or closer than the focal plane is enough to determine blur strength.

### 1.4 The Necessity of Semantic Guidance

Purely depth-based bokeh suffers from several issues:
- **Depth map errors are especially severe at boundaries** (depth bleeding, 深度渗透), causing "halos" at the edges of foreground objects.
- **Fine structures such as hair and fur** have insufficient depth estimation accuracy, leading to jagged edges after rendering.
- **Intra-foreground depth variation** can cause localized blur within faces (e.g., depth difference between the nose tip and ears).

Semantic information (human parsing, instance segmentation) provides high-accuracy boundary masks that compensate for the limited boundary precision of depth maps.

---

## §2 Algorithms

### 2.1 MiDaS: General Depth Estimation via Multi-Dataset Training

**MiDaS** (Mixed Dataset Depth Estimation), proposed by Ranftl et al. (CVPR 2020, extended version IEEE TPAMI 2022), is an important baseline for general-purpose monocular depth estimation.

**Key contributions:**
- Mixed training strategy: simultaneous training on 8 depth datasets with different annotation types (absolute depth, relative depth, point-cloud projections).
- Scale-Shift Invariant Loss (尺度-偏移不变损失):

$$
\mathcal{L}_{\text{ssi}} = \frac{1}{M} \sum_{i} \rho\left( \frac{d_i - s \cdot \hat{d}_i - t}{\sigma} \right)
$$

where $s, t$ are affine parameters, $\rho$ is the Huber loss, and $\sigma$ is a normalization coefficient. This loss allows the predicted depth values to be inconsistent with the ground truth in scale and offset, greatly expanding the range of usable training data.

**MiDaS v3 (DPT backbone):** Uses a Vision Transformer (ViT-L/16) encoder and a Dense Prediction Transformer (DPT) decoder, achieving state of the art on NYUv2 and KITTI.

### 2.2 BokehMe: Combining Neural Rendering with Classical Rendering

**BokehMe** (Peng et al., CVPR 2022) is a landmark work that explicitly fuses neural rendering with physics-based bokeh synthesis:

**Two-stage pipeline:**
1. **Classical rendering stage:** A monocular depth estimation network (DPT backbone) produces a depth map; layered bokeh rendering based on the CoC formula generates a coarse bokeh result.
2. **Neural repair stage:** A lightweight CNN receives the coarse bokeh result, the original sharp image, and a soft segmentation mask, and repairs boundary halos, hair-strand leakage, and other artifacts from classical rendering.

This hybrid design preserves the physical interpretability of classical rendering while leveraging neural networks for perceptual refinement; LPIPS is approximately 15% lower than contemporary pure-CNN bokeh methods.

**Industry portrait-mode pipeline (independent of BokehMe):** Production smartphone portrait mode typically uses a four-module cascade architecture:
1. **Human parsing network:** Predicts foreground masks (body segmentation + fine hair segmentation).
2. **Monocular depth network:** Estimates an affine-invariant relative depth map.
3. **Mask refinement module:** Depth-map-guided CRF (Conditional Random Field) to refine segmentation boundaries.
4. **Bokeh rendering network:** Depth-aware, layered rendering; foreground stays sharp, background is blurred by depth.

**Training data:** Synthetic rendered data (ShapeNet scenes + human body models) + real data from dual-camera phones (main camera with bokeh vs. wide-angle reference).

### 2.3 SBTNet: Selective Bokeh Effect Transformation (CVPRW 2023)

Peng et al. (CVPRW 2023) **[3]** proposed **SBTNet** (Selective Bokeh Effect Transformation), addressing the task of **inter-lens bokeh style transfer** — converting bokeh characteristics produced by one lens (e.g., swirling bokeh spots) into the bokeh style of another lens (e.g., circular bokeh spots), rather than generating bokeh from a sharp image:

- **Bokeh effect transformation task:** Given a source image with specific lens bokeh characteristics, generate an equivalent image with target lens bokeh characteristics.
- **Selective attention mechanism:** Transformer attention identifies bokeh regions in the image and selectively applies style transformation.
- **NTIRE 2023 competition:** Submitted as a solution to the NTIRE 2023 Bokeh Effect Transformation Challenge, achieving strong results.

**Distinction from bokeh rendering:** SBTNet solves "bokeh style transfer" (existing bokeh → different bokeh), while the methods in §2.1–§2.2 solve "bokeh generation" (sharp image → bokeh image). These are fundamentally different task definitions and should not be confused.

### 2.4 Depth-Based Layered Bokeh Rendering

Classic bokeh rendering uses **layered compositing (分层合成)**:

1. Partition the scene into $L$ depth layers (typically $L = 8$–$16$).
2. Apply Gaussian/disc blur of the corresponding CoC size to each layer.
3. Alpha-composite layers from background to foreground (Porter–Duff Over operator).

Depth-aware kernel (深度感知模糊核):

$$
\text{CoC}(d) = \text{clip}\left(\frac{A \cdot f^2 \cdot |d - d_f|}{N \cdot d \cdot (d_f - f)},\ 0,\ r_{\max}\right)
$$

where $A$ is a sensor relative-area scaling factor and $r_{\max}$ is the maximum allowed CoC radius (to prevent excessive blur).

### 2.5 Comparison of Depth Estimation Methods

| Method | Input | Output | Strengths | Limitations |
|--------|-------|--------|-----------|-------------|
| MiDaS (2022) | Monocular RGB | Affine-invariant depth | Strong generalization, multi-scene | Absolute depth inaccurate |
| AdaBins (CVPR 2021) | Monocular RGB | Absolute depth | High indoor accuracy | Poor on outdoor scenes |
| DPT (ICCV 2021) | Monocular RGB | Relative depth | ViT backbone for high accuracy | High compute cost |
| DepthAnything (2024) | Monocular RGB | Relative depth | Trained on 150 M samples | Better for open scenes |
| Stereo disparity | Dual RGB | Absolute disparity | Physically accurate | Requires dual-camera hardware |

---

## §3 Tuning Guide

### 3.1 Impact of Depth Map Quality on Bokeh

Depth map quality is the decisive factor in computational bokeh; tuning priority is higher than rendering parameters:

- **Boundary resolution:** Depth map errors at foreground/background boundaries directly cause depth bleeding (深度渗透); depth refinement (深度细化) must be applied near boundaries.
- **Depth consistency:** Depth within a single object must be smooth to avoid partial face blur; apply semantics-aware smoothing (smooth within segmentation boundaries but not across them).
- **Post-processing:** Guided filter (导向滤波) using the RGB image as the guide can effectively remove blocky artifacts from the depth map.

### 3.2 Segmentation Accuracy and Edge Handling

Fine structures such as hair, fur, and transparent objects are the main sources of segmentation error:

- **Hair segmentation:** Use dedicated fine-grained segmentation networks such as Hair-Net, outputting probability maps (0–1) rather than hard binary masks.
- **Gradient transition mask:** Use a depth-driven soft mask in the foreground/background boundary region:

$$
\alpha(p) = \sigma\left(\frac{d_{\text{focus}} - d(p)}{\tau}\right)
$$

where $\sigma$ is the sigmoid function and $\tau$ is the temperature parameter controlling transition bandwidth (typically $\tau = 0.05$ relative depth units).

- **Blending strategy for hair regions:** For hair strands, use a weighted fusion of depth map weight (0.3) and segmentation confidence weight (0.7) to balance edge accuracy and physical depth accuracy.

### 3.3 Blur Strength Control

User-adjustable parameters:

| Parameter | Meaning | Recommended Range |
|-----------|---------|-------------------|
| Equivalent f-number | Simulated aperture size (f/1.2–f/8) | Selected by user or auto from scene |
| Focus distance | Depth of focal plane (relative value) | Auto-focus on face, or user tap-to-focus |
| Blur intensity scale | Global scale applied to CoC formula output | 0.5–2.0, default 1.0 |
| Maximum CoC radius | Limits maximum blur for distant background | Recommended ≤ 3% of image width |

### 3.4 Real-Time Optimization Strategies

- **Lightweight depth network:** Replace DPT-Large with MiDaS Small (ResNet-18 backbone); inference speed improves ~10×, depth accuracy degrades ~8%.
- **Resolution decoupling:** Run depth/segmentation networks at 1/4 resolution; render at full resolution; upsample depth map with bilinear interpolation and refine with guided filter.
- **Parallelization of bokeh rendering:** Per-layer blur can be computed in parallel, fully utilizing GPU/NPU parallelism.
- **Caching mechanism:** In video bokeh scenarios, cache segmentation masks and depth maps for static background regions; update only foreground regions.

### 3.5 Multi-Camera-Assisted Depth (Dual Camera / ToF Fusion)

When the device has dual cameras or a ToF sensor:

- **Stereo disparity depth** is accurate at close range (< 3 m) but inaccurate at distance.
- **ToF depth** is reliable in low-light/low-texture regions but has low resolution (typically 320×240).
- **Monocular depth** generalizes well across scenes but has scale drift.

Recommended fusion strategy: for close range (< 2 m), rely primarily on stereo/ToF; for far range (> 3 m), rely primarily on monocular depth; linearly interpolate for the middle range.

---

## §4 Artifacts

### 4.1 Bokeh Edge Leakage / Depth Bleeding Halo

**Symptom:** A bright or foreground-colored "halo" appears at the edges of foreground objects (people, flowers) — foreground color "spills" into the blurred background region, or blurred background color "bleeds" into the interior edge of the foreground silhouette, forming a 2–5 pixel wide color fringe (彩色晕边). Most visible at hair-background boundaries with light backgrounds.

**Root cause:** Spatial aliasing in the depth map at foreground/background boundaries: depth values within 3–5 pixels on either side of the boundary are a weighted average of foreground and background depth (influenced by the receptive field of the depth estimation network). This causes aliased pixels to receive CoC radii between foreground and background, producing incorrect mixing of foreground color and blurred background color during rendering. In layered compositing, if depth thresholds (hard decisions) rather than soft masks are used for layer assignment, boundary pixels are randomly assigned to a layer whose blur kernel covers pixels from adjacent layers.

**Diagnosis:** On a test image with known foreground/background boundaries (from high-accuracy segmentation or manual annotation), extract color distributions from 5-pixel bands inside and outside the boundary, and compute the CIE Lab mean variance in the boundary region. If the Lab color difference $\Delta E_{00}$ of 3 pixels inside/outside the boundary is > 5 units and aligns with the background color direction, significant leakage is present. Compare depth-map-guided rendering with direct RGB segmentation rendering; if the former has a wider boundary halo, confirm depth aliasing as the cause.

**Mitigation strategies:**
- Apply segmentation-guided depth boundary refinement (guided filter or DNN refinement): reinforce depth transitions at RGB high-gradient locations to eliminate aliasing regions.
- Dilate the foreground mask outward by 2–4 pixels (morphological dilation) and use it as the layering boundary, assigning all boundary-ambiguous pixels to the foreground layer (rendered at foreground depth, avoiding background blur kernel influence).
- Use continuous alpha transition weights during layered compositing (Sigmoid transition bandwidth $\tau \approx 0.03$) rather than binary depth thresholds, for natural edge transitions.

### 4.2 Foreground Matting Error

**Symptom:** The foreground segmentation mask has obvious errors at fine structures such as hair strands, fur, and translucent fabric — hair strands are classified as background (blurred), causing unnatural localized bokeh in the hair region; or when the background is visible through gaps in hair strands, those gaps are not correctly blurred (the foreground mask keeps the background inside the gaps sharp), creating a "wire mesh" effect.

**Root cause:** General human parsing networks (e.g., DeepLabV3+) have insufficient boundary accuracy for fine structures such as hair/fur/thin lines. The minimum distinguishable unit of semantic segmentation is approximately 8–16 pixels (limited by downsampling stride), while hair strand width is only 1–3 pixels. Binary masks (hard masks) cannot represent the sub-pixel-level transparency of mixed foreground/background in hair regions. Depth estimation errors at facial nose-tip and chin contours combined with segmentation errors cause flickering matting along facial edges.

**Diagnosis:** On test images with fine hair boundaries (portrait datasets such as Portrait-Bokeh), compute the F-measure $F_\beta$ ($\beta = 0.3$, prioritizing Precision to avoid blur spreading into the foreground) of segmentation mask boundaries. If $F_{0.3}$ < 0.85 (evaluated separately on hair regions), segmentation accuracy is insufficient. Visually inspect hair-gap regions — if the background inside gaps is not blurred (remains sharp), it is a mask error.

**Mitigation strategies:**
- Use a dedicated fine-grained hair segmentation network (Hair-Net or MODNet), outputting a continuous probability map (0–1) rather than a hard mask; apply gradient transition in regions where $\alpha \in (0.1, 0.9)$.
- Apply a depth-guided soft mask in hair regions: $\alpha(p) = 0.3 \cdot \alpha_{\text{depth}}(p) + 0.7 \cdot \alpha_{\text{seg}}(p)$, blending depth prior and segmentation prior for improved stability.
- During rendering, allow the foreground in hair boundary regions to participate slightly in background blur (weight 0.2–0.3), to eliminate the "wire mesh" effect while preserving natural hair contours.

### 4.3 Foreground Over-Sharpness vs. Background Transition

**Symptom:** The focused subject appears unnaturally sharp in contrast to the blurred background — the foreground skin texture, after digital sharpening, has MTF50 exceeding 0.6 Nyquist (beyond the physical resolution limit of a real lens), while the transition to blur near the focal plane depth lacks a natural gradient, creating a "foreground sticker" appearance. In the same scene, the hard switch from sharp at 1.5 m to fully blurred at 1.8 m is inconsistent with the gradual depth-of-field falloff of a real large-aperture lens.

**Root cause:** The algorithm treats all pixels inside the foreground segmentation mask as having "zero CoC" (fully sharp), while all background pixels receive CoC radii based on depth. There is no transition zone modeling based on depth-of-field range. If the input image has already been sharpened by the ISP (Unsharp Mask gain > 0.8), the perceived sharpness of the foreground is completely mismatched with the in-lens spherical aberration of a real lens, creating an "over-sharp" appearance.

**Diagnosis:** Compute the MTF curve for the foreground region of the output bokeh image (ISO 12233 method) and compare with a reference image taken by a real large-aperture camera (f/1.2 full-frame) of the same scene. If foreground MTF50 > 1.3× the reference, the foreground is over-sharp. Check CoC radius variation near the focal plane depth (±10% of depth-of-field range) — if it jumps abruptly from 0 to $r > 3$ pixels, the transition zone is missing.

**Mitigation strategies:**
- Apply a slight Gaussian blur ($\sigma \approx 0.5$–$1.0$ pixel) to foreground regions near the focal plane (depth difference $|d - d_f| < \delta$, recommended $\delta = 0.05$ normalized depth units), simulating the focal-depth transition characteristic of a real lens.
- Introduce a continuous CoC gradient zone: apply slight defocus ($r = 0.5$–$2$ pixels) proportional to depth in 3–6 pixels inside the segmentation mask boundary, eliminating the hard-switch appearance.
- If ISP pre-sharpening gain is too strong, locally reduce sharpening weight for the foreground region before bokeh rendering (weighted by distance from the focal plane), matching foreground sharpness to physically realistic bokeh.

### 4.4 Artifact Reference Table

| Artifact Type | Trigger Condition | Typical Symptom | Mitigation |
|--------------|------------------|----------------|------------|
| Edge Leakage (边缘泄漏) | Depth map boundary aliasing, hard-threshold layering | Foreground color spills as halo, 2–5 px fringe | Depth boundary refinement, foreground mask dilation, Sigmoid transition |
| Matting Error (前景抠图错误) | Hair/fur precision insufficient, hard mask | Hair strands blurred, or background in hair gaps not blurred | Soft mask probability map, Hair-Net, depth+segmentation blended weight |
| Over-Sharpness (前景过度清晰) | Zero CoC + ISP sharpening stacked | Foreground "sticker" look, MTF50 exceeds physical limit | Focal-depth slight blur, CoC gradient zone, foreground de-sharpening |
| Intra-face Blur (人脸内部虚化) | Depth estimation variation within face | Nose tip/ear localized blur, inconsistent with eyes | Force single depth for face region, semantics-aware smoothing |
| Kernel Distortion (散景核失真) | Square/Gaussian kernel substituted for physical PSF | Light circles appear square or octagonal | Learnable PSF kernel (BokehMe), circular disc kernel |

---

## §5 Evaluation

### 5.1 Depth Map Evaluation Metrics

| Metric | Formula | Meaning |
|--------|---------|---------|
| AbsRel | $\frac{1}{M}\sum |d_i - \hat{d}_i| / d_i$ | Absolute relative error |
| SqRel | $\frac{1}{M}\sum (d_i - \hat{d}_i)^2 / d_i$ | Squared relative error |
| $\delta_1$ | $\%$ pix s.t. $\max(d/\hat{d},\ \hat{d}/d) < 1.25$ | Threshold accuracy |
| RMSE | $\sqrt{\frac{1}{M}\sum(d_i - \hat{d}_i)^2}$ | Root mean square error |

### 5.2 Bokeh Rendering Evaluation Metrics

| Metric | Description |
|--------|-------------|
| PSNR (background region) | Computed only in the blurred background region; evaluates naturalness of blur |
| SSIM (foreground region) | Computed only in the sharp foreground region; evaluates sharpness fidelity |
| LPIPS (full image) | Perceptual distance; comprehensive evaluation of overall visual quality |
| BokehScore | Dedicated metric: roundness of bokeh light circles vs. real lens light circles |

### 5.3 Edge Quality Evaluation

Edge quality (foreground edge quality, 前景边缘质量) uses F-measure to evaluate the accuracy of segmentation boundaries:

$$
F_\beta = (1 + \beta^2) \cdot \frac{\text{Precision} \cdot \text{Recall}}{\beta^2 \cdot \text{Precision} + \text{Recall}}
$$

Computed separately on fine boundaries (hair regions); $\beta = 0.3$ is recommended (prioritizes Precision to avoid blur regions bleeding into the foreground).

### 5.4 Benchmark Datasets

| Dataset | Source | Characteristics |
|---------|--------|----------------|
| NYUv2 (2012) | Silberman et al. | Indoor RGB-D, 464 scenes |
| DIODE (2019) | Vasiljevic et al. | Mixed indoor/outdoor, LIDAR GT depth |
| EBB (CVPR 2020) | Ignatov et al. | Real phone bokeh pairs (dual-camera system) |
| DPED-Bokeh (2021) | Ignatov et al. | Large-scale phone bokeh dataset |
| Portrait-Bokeh (CVPR 2022) | Peng et al. | Portrait bokeh with fine hair annotations |

### 5.5 Subjective Evaluation Protocol

- **Realism Score (真实感评分):** Viewers rate the similarity of the bokeh effect to real large-aperture lens results (1–5 scale).
- **Edge Naturalness Score:** Emphasizes challenging boundary regions such as hair and translucent glass.
- **Comparison Test with Real Lens:** A reference image of the same scene captured with an f/1.2 full-frame camera is shown side-by-side with the computational bokeh result.

---

## §6 Code Examples

### 6.1 MiDaS Depth Estimation Inference

```python
import torch
import torch.nn.functional as F
import numpy as np

def run_midas_depth(model, transform, image_rgb, device='cpu'):
    """
    Estimate monocular affine-invariant depth map using MiDaS.
    model:     MiDaS model with loaded weights (e.g., midas_v21_small)
    transform: MiDaS input pre-processing transform
    image_rgb: uint8 RGB image (H, W, 3)
    Returns:   Relative depth map float32 (H, W); larger values = closer
    """
    H, W = image_rgb.shape[:2]
    input_tensor = transform(image_rgb).to(device)     # (1, 3, H', W')

    with torch.no_grad():
        depth_pred = model(input_tensor)               # (1, H', W')

    # Upsample back to original resolution
    depth_pred = F.interpolate(
        depth_pred.unsqueeze(1),
        size=(H, W),
        mode='bicubic',
        align_corners=False
    ).squeeze().cpu().numpy()

    # Normalize to [0, 1], 0 = farthest, 1 = nearest
    d_min, d_max = depth_pred.min(), depth_pred.max()
    depth_norm = (depth_pred - d_min) / (d_max - d_min + 1e-6)
    return depth_norm.astype(np.float32)
```

### 6.2 Depth-Aware Bokeh Rendering

```python
import numpy as np
import cv2

def depth_aware_bokeh_render(image, depth_map, focus_depth=0.5,
                              max_blur_radius=15, num_layers=8):
    """
    Layered depth-aware bokeh rendering.
    image:          float32 RGB image, range [0,1], shape (H,W,3)
    depth_map:      float32 normalized depth map (H,W), 0=farthest, 1=nearest
    focus_depth:    focal plane depth value (relative depth, 0-1)
    max_blur_radius:maximum CoC radius (pixels)
    num_layers:     number of depth layers
    Returns:        bokeh-rendered image float32 (H,W,3)
    """
    H, W = image.shape[:2]
    result = np.zeros_like(image)
    weight_acc = np.zeros((H, W, 1), dtype=np.float32)

    depth_layers = np.linspace(0.0, 1.0, num_layers + 1)

    for i in range(num_layers):
        d_low  = depth_layers[i]
        d_high = depth_layers[i + 1]
        d_mid  = (d_low + d_high) / 2.0

        # CoC radius for current layer (linearly mapped from depth difference)
        depth_diff = abs(d_mid - focus_depth)
        blur_radius = min(int(depth_diff * max_blur_radius * 2), max_blur_radius)

        # Layer mask
        layer_mask = ((depth_map >= d_low) & (depth_map < d_high)).astype(np.float32)
        layer_mask = layer_mask[:, :, np.newaxis]

        # Extract layer image
        layer_img = image * layer_mask

        # Apply circular disc blur
        if blur_radius > 1:
            # Generate circular kernel
            kernel_size = blur_radius * 2 + 1
            kernel = np.zeros((kernel_size, kernel_size), np.float32)
            cv2.circle(kernel, (blur_radius, blur_radius), blur_radius, 1.0, -1)
            kernel /= kernel.sum()
            blurred_img = cv2.filter2D(layer_img, -1, kernel)
            blurred_mask = cv2.filter2D(layer_mask, -1, kernel)
        else:
            blurred_img  = layer_img
            blurred_mask = layer_mask

        result     += blurred_img
        weight_acc += blurred_mask

    # Normalize
    result = result / np.clip(weight_acc, 1e-6, None)
    return np.clip(result, 0.0, 1.0).astype(np.float32)
```

### 6.3 Semantics-Guided Depth Refinement

```python
import torch
import torch.nn.functional as F

def semantic_guided_depth_refine(depth, seg_mask, rgb, radius=3, eps=1e-4):
    """
    Joint bilateral filter refinement of the depth map guided by RGB image and semantic mask.
    depth:    (B, 1, H, W) float32 raw depth map
    seg_mask: (B, 1, H, W) float32 foreground probability map [0,1]
    rgb:      (B, 3, H, W) float32 RGB image [0,1]
    Returns:  (B, 1, H, W) refined depth map
    """
    B, _, H, W = depth.shape

    # Build RGB-guided spatial weights (approximate joint bilateral filter)
    # Expand neighborhood
    d = radius
    pad = d
    rgb_pad = F.pad(rgb, [pad]*4, mode='reflect')
    depth_pad = F.pad(depth, [pad]*4, mode='reflect')

    # Collect depth and color for 2d+1 x 2d+1 neighborhood
    patches_rgb   = rgb_pad.unfold(2, 2*d+1, 1).unfold(3, 2*d+1, 1)   # (B,3,H,W,k,k)
    patches_depth = depth_pad.unfold(2, 2*d+1, 1).unfold(3, 2*d+1, 1) # (B,1,H,W,k,k)

    # Color similarity weights
    rgb_center  = rgb.unsqueeze(-1).unsqueeze(-1)   # (B,3,H,W,1,1)
    color_diff  = ((patches_rgb - rgb_center) ** 2).sum(dim=1, keepdim=True)
    color_w     = torch.exp(-color_diff / (2 * 0.1 ** 2))  # sigma_color=0.1

    # Normalize weights
    weight_sum  = color_w.sum(dim=(-2,-1), keepdim=True)
    color_w_n   = color_w / (weight_sum + eps)

    # Weighted depth
    refined = (patches_depth * color_w_n).sum(dim=(-2,-1))   # (B,1,H,W)

    # Foreground region stays sharp; background region uses refined result
    alpha = seg_mask  # foreground=1, background=0
    output = alpha * depth + (1 - alpha) * refined

    return output
```

### 6.4 Soft Segmentation Mask-Driven Bokeh Compositing

```python
import numpy as np
import cv2

def soft_mask_bokeh_composite(sharp_img, blurred_img, soft_mask,
                               edge_feather=5):
    """
    Composite sharp foreground and blurred background using a soft segmentation mask.
    sharp_img:   float32 (H,W,3) original sharp image
    blurred_img: float32 (H,W,3) fully blurred image
    soft_mask:   float32 (H,W)   foreground probability map [0,1], 1=foreground
    edge_feather:edge feathering radius (Gaussian blur sigma)
    Returns:     composited image float32 (H,W,3)
    """
    # Edge feathering: apply Gaussian blur to hard mask to generate soft transition
    mask_feathered = cv2.GaussianBlur(
        soft_mask.astype(np.float32),
        ksize=(0, 0),
        sigmaX=edge_feather
    )
    mask_feathered = np.clip(mask_feathered, 0.0, 1.0)[:, :, np.newaxis]

    # Alpha compositing: sharp foreground + blurred background
    composite = mask_feathered * sharp_img + (1.0 - mask_feathered) * blurred_img
    return composite.astype(np.float32)


def generate_depth_based_mask(depth_map, focus_depth, dof_range=0.1):
    """
    Generate a depth-of-field mask from a depth map (in-focus range = foreground).
    depth_map:   float32 (H,W) normalized depth [0,1]
    focus_depth: focus depth value
    dof_range:   half depth-of-field range (default ±0.1)
    Returns:     soft mask float32 (H,W)
    """
    dist_to_focus = np.abs(depth_map - focus_depth)
    # In-focus area = 1; outer region smoothly transitions via sigmoid
    sigmoid_k = 30.0  # controls transition steepness
    mask = 1.0 / (1.0 + np.exp(sigmoid_k * (dist_to_focus - dof_range)))
    return mask.astype(np.float32)
```

### 6.5 End-to-End Neural Bokeh Network (Demo Architecture)

```python
import torch
import torch.nn as nn

class NeuralBokehNet(nn.Module):
    """
    Simplified neural bokeh network: encoder extracts features → depth head + bokeh rendering head.
    """
    def __init__(self, base_ch=64):
        super().__init__()
        # Shared encoder (simplified ResNet backbone)
        self.encoder = nn.Sequential(
            nn.Conv2d(3, base_ch, 7, stride=2, padding=3),
            nn.BatchNorm2d(base_ch), nn.ReLU(inplace=True),
            nn.Conv2d(base_ch, base_ch*2, 3, stride=2, padding=1),
            nn.BatchNorm2d(base_ch*2), nn.ReLU(inplace=True),
            nn.Conv2d(base_ch*2, base_ch*4, 3, stride=2, padding=1),
            nn.BatchNorm2d(base_ch*4), nn.ReLU(inplace=True),
        )
        # Depth prediction head
        self.depth_head = nn.Sequential(
            nn.Conv2d(base_ch*4, base_ch*2, 3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(base_ch*2, 1, 1),
            nn.Sigmoid()  # output normalized relative depth [0,1]
        )
        # Bokeh mask head (foreground probability)
        self.mask_head = nn.Sequential(
            nn.Conv2d(base_ch*4, base_ch*2, 3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(base_ch*2, 1, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        """
        x: (B, 3, H, W) — input RGB image
        Returns: depth (B,1,H/8,W/8), mask (B,1,H/8,W/8)
        """
        feat = self.encoder(x)
        depth = self.depth_head(feat)
        mask  = self.mask_head(feat)
        return depth, mask

# ─── Example call and output ───────────────────────────────────────
net = NeuralBokehNet()
rgb_image = torch.rand(3, 256, 256)         # single RGB frame (C,H,W)
depth, mask = net(rgb_image.unsqueeze(0))   # rgb_image: (3,H,W) → batch (1,3,H,W)
depth = depth.squeeze().detach().numpy()     # (H/8, W/8), float32, normalized [0,1]
# Output: depth.shape -> (H/8, W/8), larger value = closer to camera

```

---

## References

[1] Ranftl, R., et al. "Towards Robust Monocular Depth Estimation: Mixing Datasets for Zero-shot Cross-dataset Transfer." IEEE TPAMI 2022. (MiDaS)
[2] Peng, J., et al. "BokehMe: When Neural Rendering Meets Classical Rendering." CVPR 2022.
[3] Peng, J., et al. "Selective Bokeh Effect Transformation." CVPRW (NTIRE) 2023.
[4] Ranftl, R., et al. "Vision Transformers for Dense Prediction." ICCV 2021. (DPT)
[5] Bhat, S., et al. "AdaBins: Depth Estimation Using Adaptive Bins." CVPR 2021.
[6] Yang, L., et al. "Depth Anything: Unleashing the Power of Large-Scale Unlabeled Data." CVPR 2024.
[7] Wadhwa, N., et al. "Synthetic Depth-of-Field with a Single-Camera Mobile Phone." ICCV 2019. (Google Portrait Mode; semantics-guided portrait bokeh)
[7b] Wadhwa, N., et al. "Synthetic Shallow Depth of Field with a Single-Camera Mobile Phone." ACM TOG (SIGGRAPH 2018). (Earlier dual-pixel baseline)
[8] Ignatov, A., et al. "PyNET: Camera-to-Camera Image Enhancement." CVPR Workshop 2020. (EBB dataset)
[9] He, K., et al. "Guided Image Filtering." IEEE TPAMI 2013. (Guided filter)
[10] Chen, L., et al. "Rethinking Atrous Convolution for Semantic Image Segmentation." arXiv 2017. (DeepLab series)

## §8 Glossary

| Term | Chinese | Description |
|------|---------|-------------|
| Bokeh | 散景 | Aesthetic defocus effect in out-of-focus regions; derived from Japanese「ボケ」 |
| Circle of Confusion (CoC) | 弥散斑 | Circular light spot formed on the sensor by an out-of-focus point source |
| Depth of Field (DoF) | 景深 | Range of depths in the image that are rendered acceptably sharp |
| Computational Bokeh | 计算散景 | Technology that algorithmically simulates large-aperture bokeh effects |
| Affine-Invariant Depth | 仿射不变深度 | Depth values describe only relative near/far ordering; scale and offset are uncalibrated |
| Depth Bleeding | 深度渗透 | Artifact where depth map boundary errors cause foreground/background color contamination |
| Point Spread Function (PSF) | 点扩散函数 | Function describing an optical system's response to a point source; determines bokeh shape |
| Human Parsing | 人体解析 | Segmentation of a person image into semantic parts: head/body/limbs/hair/etc. |
| Guided Filter | 导向滤波 | Spatial filter that preserves edge structure using a guide image (e.g., RGB) |
| Soft Mask | 软掩膜 | Continuous foreground probability map with values in [0,1], used for smooth edge transitions |
| Layered Compositing | 分层合成 | Bokeh rendering method that partitions the scene by depth, renders each layer, then blends |
| ToF | Time of Flight (飞行时间) | Depth sensing technology that measures distance by timing light-pulse round trips |
