# Part 2, Chapter 27: Computational Bokeh Portrait Mode Rendering

> **Scope:** This chapter covers the complete Bokeh Portrait Mode (计算散景人像模式) pipeline for single-camera, dual-camera, and ToF-based systems — from dual-camera disparity-to-depth estimation and foreground segmentation, to spatially-varying convolution with circular/lens-aperture blur kernels (PSFs) and bokeh ball rendering. Deep learning semantic bokeh is covered in Volume 3, Chapter 13.
> **Prerequisites:** Volume 2, Chapter 22 (Multi-Camera Fusion); Volume 1, Chapter 12 (Depth Sensing)
> **Target Readers:** Algorithm engineers

---

## Table of Contents

1. [Physical Bokeh Model](#1-physical-bokeh-model)
2. [Depth Map Computation](#2-depth-map-computation)
3. [Computational Blur Rendering](#3-computational-blur-rendering)
4. [Common Artifacts and Issues](#4-common-artifacts-and-issues)
5. [Evaluation Methods](#5-evaluation-methods)
6. [Code Examples](#6-code-examples)
7. [References](#7-references)
8. [Glossary](#8-glossary)

---

## §1 Physical Bokeh Model

### 1.1 The Thin Lens Equation and In-Focus Imaging

The optical imaging of a camera lens follows the Thin Lens (薄透镜) equation, which describes the fundamental relationship between Object Distance (物距, do), Image Distance (像距, di), and Focal Length (焦距, f):

```
1/f = 1/do + 1/di
```

When the image sensor plane falls precisely on the image plane, the subject at that object distance forms a sharp image. For objects not at the focus plane, their image spreads into a blurry circle known as the **Circle of Confusion (COC, 弥散斑)**.

### 1.2 Circle of Confusion (COC) Diameter Formula

Let the focus distance be ds (the object distance corresponding to the focal point from the sensor plane), and the aperture diameter be A. Then the COC diameter of a point source at object distance do on the sensor is:

```
COC_diameter = A × |di - ds| / di

where:
  di: image distance corresponding to object distance do (computed from the thin lens equation: di = f×do / (do - f))
  ds: image distance corresponding to the focus point (when the focus distance is do_focus: ds = f×do_focus / (do_focus - f))
  A:  effective aperture diameter of the lens = f / (f/#)
```

**Far-field simplification (do >> f):**

```
COC ≈ (f / (f/#)) × |do - do_focus| / do
```

This formula reveals the three control parameters of bokeh amount:
1. **Focal length f**: Longer focal length → larger COC (stronger background blur)
2. **Aperture f/#**: Smaller f/# (larger aperture) → larger COC
3. **Object distance difference |do - do_focus|**: The farther the subject is from the focus plane, the stronger the blur

### 1.3 Relationship Between f/# and Bokeh Amount

The f/# (F-Number, 光圈数) is defined as the ratio of focal length to effective aperture diameter:

```
f/# = f / A
```

Bokeh amount is proportional to A (aperture diameter), i.e., inversely proportional to f/#. Engineering reference table of common lens apertures vs. background blur amount:

| f/# | Relative Bokeh Amount (COC ratio) | Typical Use Case |
|-----|-----------------------------------|------------------|
| f/1.4 | 5.7× | Cinema large-aperture prime lens, strong blur |
| f/1.8 | 4.4× | Mainstream choice for portrait photography |
| f/2.8 | 2.8× | Maximum aperture of zoom lenses |
| f/4.0 | 2.0× | Standard reference |
| f/8.0 | 1.0× | Reference baseline |

### 1.4 Physical Aperture Constraints of Smartphones

The physical dimensions of a smartphone's main camera determine the fundamental limitation of its optical bokeh. Taking a typical flagship smartphone main camera as an example:
- Sensor size: 1/1.3 inch (approximately 9.6 mm × 7.2 mm)
- Equivalent focal length: 24 mm (35 mm full-frame equivalent)
- Actual focal length: approximately 5.8 mm
- Maximum aperture: f/1.8
- Actual aperture diameter: 5.8 / 1.8 ≈ 3.2 mm

By comparison, a 35 mm full-frame camera with an 85 mm f/1.8 lens:
- Actual aperture diameter: 85 / 1.8 ≈ 47 mm

The smartphone's actual aperture diameter is approximately 3.2/47 ≈ 1/15 that of a full-frame camera, and the bokeh amount (COC) is approximately 1/15. This physical gap cannot be compensated by optical means and can only be simulated through Computational Photography (计算摄影).

---

## §2 Depth Map Computation

### 2.1 Dual-Camera Disparity-to-Depth Estimation (SGM Algorithm)

A Dual Camera (双摄) system computes subject depth through the disparity (视差) between two cameras, and is currently the primary depth source for bokeh in mainstream flagship smartphones.

**Disparity-depth relationship (stereo geometry):**

```
depth = f_pixel × baseline / disparity

where:
  f_pixel:   focal length (in pixels)
  baseline:  dual-camera baseline distance (horizontal distance between the two optical centers; typically 8–15 mm)
  disparity: horizontal pixel offset of the same point between the left and right images
```

**Semi-Global Matching (SGM, 半全局匹配)** (Hirschmüller, *IEEE TPAMI*, 2008) is the industry-standard algorithm for dual-camera disparity estimation. The core idea of SGM is to approximate the 2D global energy minimization problem as 1D dynamic programming along multiple directions (8–16 scan lines), balancing accuracy and computational efficiency.

**SGM energy function:**

```
E(D) = Σ_p [C(p, Dp) + Σ_{q∈Nb(p)} P1×[|Dp-Dq|=1] + Σ_{q∈Nb(p)} P2×[|Dp-Dq|>1]]

where:
  C(p, d):  matching cost at pixel p with disparity d (e.g., Census Transform or AD-Census)
  P1:       smoothness penalty for disparity changes of ±1 (encourages smooth transitions)
  P2:       global penalty for disparity changes > 1 (P2 > P1, suppresses jumps)
  Nb(p):    neighborhood of pixel p
```

**Engineering parameters:**
- Disparity search range: 0–192 disparity (corresponding to near distances of 0.3 m to infinity)
- Matching cost: Census Transform (5×5 window) or AD+Census combination, robust to illumination changes
- Smoothness parameters: P1 = 10–15, P2 = 50–100 (adjusted according to scene)
- Post-processing: Left-Right Consistency Check (left-right consistency check) to discard occluded disparities; median filter (5×5) to remove isolated noise

**Depth accuracy specification:** For portrait mode at the standard shooting distance of ~2 m, a dual-camera system (8–15 mm baseline) should achieve absolute depth accuracy of **±5–10 cm** (standard deviation). At this accuracy level the resulting COC error is < 4 px, which is below the visibility threshold for bokeh edge artifacts (Halo_width ≈ COC × depth_error_fraction; COC < 4 px avoids visually noticeable double-edge halos).

### 2.2 Single-Camera Monocular Depth Estimation (MiDaS)

In scenarios with only a single camera (or where semantically-enhanced depth is required), Monocular Depth Estimation (单目深度估计) networks can be used.

**MiDaS v2** (Ranftl et al., *CVPR*, 2020) is a widely used zero-shot monocular depth estimation model, trained on 10+ mixed datasets with strong generalization capability.

Key design of MiDaS v2:
- Backbone network: ResNeXt-101 or DPT (Dense Prediction Transformer, higher accuracy version)
- Loss function: Scale-Shift Invariant Loss (尺度平移不变损失), because depth scales across different datasets are not comparable
- Output: Relative Depth (相对深度) rather than absolute depth (in meters); scale estimation is required via reference objects (known-size facial/body parts)

**Primary limitations of monocular depth:**
- Output is relative depth (no absolute physical scale); scale recovery is needed for bokeh rendering
- Higher depth uncertainty compared to stereo disparity, especially in textureless regions
- Depth map resolution is typically lower than the image (usually 1/4 to 1/2 resolution); edges are less precise

### 2.3 ToF Depth Alignment

A Time-of-Flight (ToF, 飞行时间) sensor directly measures the photon round-trip time, providing absolute depth values (in meters) with approximately 1–5% accuracy (depending on SNR).

**Engineering challenges of using ToF depth for bokeh:**
1. **Resolution mismatch:** ToF sensor resolution is low (typically 320×240); upsampling to main camera resolution is required
2. **Disparity alignment:** The ToF sensor and main camera have different optical centers; projective transformation alignment requires extrinsic camera calibration
3. **Depth edge artifacts (飞点):** At object depth boundaries, ToF sensors produce depth flying points due to Multi-path Interference (多路径反射); these must be corrected using a Joint Bilateral Filter (联合双边滤波) guided by the RGB image
4. **Near-range saturation:** Most ToF sensors have reduced accuracy at distances < 0.3 m

**Joint Bilateral Upsampling (JBU, 联合双边引导上采样):**

```
D_fine(p) = Σ_{q∈N(p)} w_spatial(p,q) × w_range(p,q) × D_coarse(q)

w_spatial(p,q) = exp(-‖p-q‖² / 2σ_s²)   (spatial Gaussian kernel)
w_range(p,q)   = exp(-‖I(p)-I(q)‖² / 2σ_r²)  (RGB-guided kernel)
```

JBU uses the edge information of the high-resolution RGB image to guide the upsampling of the low-resolution depth map, aligning depth edges with image edges. It is the standard tool for ToF depth refinement (Kopf et al., *SIGGRAPH 2007*).

---

## §3 Computational Blur Rendering

### 3.1 Spatially-Varying PSF Convolution

Based on the depth map, pixels outside the Depth of Field (DoF, 景深) need to have blur applied in proportion to their COC diameter. Since the COC radius differs for different pixels, the blur kernel (PSF, Point Spread Function) is spatially variant and cannot be implemented with a simple full-image convolution.

**Engineering implementation strategy: Layered (分层) blur:**

Quantize the depth map into K depth intervals (layers); each layer is convolved with a circular Gaussian kernel corresponding to its COC diameter, then composited in depth order:

```
K=8 layers (typical configuration):
  Layer 0:   Near foreground (COC ≈ 0, sharp, focus subject)
  Layer 1–3: Defocused foreground (COC increasing)
  Layer 4:   Focus plane (COC ≈ 0, sharp)
  Layer 5–7: Defocused background (COC increasing, typically maximum)
```

Each layer is convolved independently, then composited in depth Z-order (far to near), with near layers overwriting far layers.

**Circular COC blur kernel (Disk PSF):**

The physical optical bokeh PSF is a circular uniform disk (determined by the aperture shape), but directly using disk convolution produces hard circular edges that look unnatural in computational bokeh (real lenses soften these edges via diffraction and aberrations). In practice, the following are commonly used:
- **Circular Gaussian:** Center-weighted with smooth edges; COC radius corresponds to σ = r/2–r/3
- **Gaussian Mixture Disk (二维高斯混合):** Strong center + ring-shaped edge, simulating the edge light intensity of a real aperture
- **Bokeh Balls (散景球):** Point light sources (highlight regions) produce bokeh with a distinctive shape (circular, polygonal); special handling is required (see Section 3.4)

### 3.2 Alpha Matting Foreground Feathering

Depth maps have depth discontinuities at foreground/background boundaries. If a full-resolution blur is applied per-layer directly according to depth, the foreground edges exhibit a sharp "pasted" appearance (Hard Edge), inconsistent with the gradual effect of real optical defocus.

**Alpha Matting (前景分割羽化)** is the standard method for resolving this issue:

1. **Foreground Segmentation:** Obtain a binary foreground mask from the depth map and/or semantic information. Common semantic segmentation networks used for portrait foreground extraction include **DeepLabv3+** (Chen et al., *ECCV* 2018) and **BiSeNet** (Yu et al., *ECCV* 2018), achieving person-class mIoU > 90% on COCO; mobile-quantized variants (MobileViT-based) run at ~40–80 ms on smartphone NPUs.
2. **Alpha Matting:** Extend the binary mask into a continuous alpha value (0 = background, 1 = foreground, 0–1 = transition zone)
   - Methods: KNN Matting (He et al., *CVPR* 2010), Shared Matting (Gastal & Oliveira, *SIGGRAPH* 2010)
3. **Gradual compositing:**

```
output(p) = α(p) × foreground_layer(p) + (1 - α(p)) × background_blurred(p)
```

The blur amount in the edge transition zone (semi-transparent pixels) is interpolated by alpha:

```
blur_sigma(p) = (1 - α(p)) × σ_background + α(p) × σ_foreground
```

### 3.3 Bilateral Guided Filter Depth Refinement

Depth Refinement (深度精化) of the raw depth map before rendering is the key step for improving bokeh edge quality.

**Guided Filter (引导滤波)** (He et al., *ECCV* 2010 / *TPAMI* 2013):

```
output = GF(guide=I_rgb, input=D_raw, r=8, eps=0.1²)
```

The guided filter uses the RGB image as a guide to perform edge-preserving smoothing of the depth map:
- At image edges (large RGB variation): depth retains its original value (edges are not spread)
- In flat texture regions (small RGB variation): depth is smoothed (reducing depth noise)

**Choosing between Joint Bilateral Filter and Guided Filter:**
- Guided Filter: Linear time complexity O(N), no iteration, suitable for real-time implementation
- Joint Bilateral: O(Nr²), computationally heavier, but slightly better edge preservation
- Practical engineering (real-time smartphone bokeh): typically uses the guided filter or its hardware-accelerated variant

### 3.4 Bokeh Ball (散景球) Light Leakage Prevention

Point light sources or specular highlight regions appear as distinct circular (or aperture-blade-determined polygonal) bokeh balls under large aperture. Computational bokeh must correctly render this effect while avoiding two classes of artifacts:

**Foreground Bokeh Light Leakage (前景高光泄漏):**
When a foreground (sharp) object occludes a background bokeh ball, if the blur processing order is incorrect, the background bokeh ball will "bleed" onto the foreground object (physically incorrect for aperture effects).

**Engineering solution (Occlusion-Aware Bokeh, 遮挡感知散景渲染):**
1. Sort the scene by depth; render starting from the farthest layer
2. Before blurring each layer, extract bokeh ball candidates from the highlights of that layer
3. When rendering bokeh balls, check whether their position is occluded by a foreground depth layer (via depth map Z-test)
4. Clip the bokeh ball's contribution in occluded regions

**Color Bleeding Prevention (颜色出血防护):**
Under large COC blur, foreground object color spreads toward the background (forward leakage) or background color seeps into the foreground edge (reverse leakage) — both are called Color Bleeding (颜色出血) or Color Fringing. Depth-Aware Blur (深度感知模糊) suppresses this effect by limiting the blur range across depth boundaries (see Section 4.1).

---

## §4 Common Artifacts and Issues

### 4.1 Foreground Edge Color Bleeding (渗色)

**Symptom description:**
The edge regions of a foreground object (portrait subject) are contaminated by background colors, or background colors (blue sky, green foliage) seep into the foreground outline. This is especially pronounced in high-contrast scenes (dark foreground on a white background).

**Physical nature:**
In a real large-aperture lens, the light rays from the foreground and background physically overlap on the sensor in out-of-focus regions (photon-level mixing), so the foreground outline naturally includes background light contributions. If computational bokeh simply composites the foreground with a blurred background in layers, this physical effect cannot be simulated; but if cross-depth mixing is used, unnatural color bleeding results.

**Engineering countermeasures:**
- **Depth edge weight control:** Reduce the blending weight at cross-depth boundaries (|D(p) - D(q)| > threshold)
- **Foreground Alpha refinement:** In transition zones (foreground α between 0.1–0.9), use KNN Matting for precise alpha estimation to prevent the foreground outer contour from sampling background colors
- **Edge-guided post-processing:** Apply a Bilateral Filter to the bokeh result, using the edges of the original sharp image as guidance to repair color contamination at edges

### 4.2 Double-Edge Halo at Depth Discontinuities

**Symptom description:**
At depth map discontinuities (e.g., the boundary between a portrait subject's side silhouette and the background), the composite result shows a ring of bright/dark halo (Halo), typically appearing as a "dirty edge" effect.

**Root cause:**
- Depth estimation at object edges is inaccurate (foreground/background depth aliasing, "Depth Bleeding")
- The layer boundary before blurring does not align with the actual image semantic boundary, making the composite boundary between the sharp and blurred layers visible
- Alpha Matting errors cause background blur seepage into the foreground feathering zone

**Quantitative analysis:**
"Double-edge halo" width is positively correlated with depth map accuracy and COC radius:
```
Halo_width ≈ COC_background × depth_error_fraction
```
With 1% depth map error and background COC=40px, halo width can range from approximately 0.4 px (visually acceptable) to 4 px (clearly visible).

**Engineering countermeasures:**
- High-precision Matting (KNN Matting error < 3% alpha error)
- Depth map edge refinement (guided filter or SGM sub-pixel refinement)
- Expand the gradual transition width of "deep/shallow" boundaries to 5–10 px (rather than sharp boundaries)

### 4.3 Portrait Hair Edge Distortion

**Symptom description:**
In portrait mode, the fine structure of hair (or animal fur) appears unnatural after bokeh compositing:
- Over-foregroundized hair: The hair region is entirely sharp, inconsistent with the natural edge defocus of a real lens
- Under-foregroundized hair: The hair region is partially blurred, producing a "transparent" appearance (hair disappears)

**Root cause:**
Hair is a typical fine semi-transparent structure. The precision of Alpha Matting approaches the resolution limit at hair-strand scale (1–3 pixels wide). The depth map in hair regions is usually inaccurate (insufficient depth sensor resolution).

**Engineering countermeasures:**
- Fine-grained hair matting: Combine semantic segmentation (face detection) with color-based matting algorithms (e.g., Closed-form Matting, Deep Matting)
- Hair-specific channel processing: Apply a dedicated mild blur strategy for detected hair regions (Hair Segmentation) rather than fully depth-driven blur
- Refer to Volume 3, Chapter 13 for the deep learning portrait bokeh solution (providing pixel-level semantic accuracy)

---

## §5 Evaluation Methods

### 5.1 Subjective Double-Blind Test (vs. Physical Optics)

Subjective evaluation is the ultimate criterion for validating computational bokeh quality. Standard double-blind test design:

**Test protocol:**
1. Use a physical large-aperture lens (e.g., 85 mm f/1.8 full-frame) to shoot reference images (ground-truth physical bokeh)
2. Shoot the same scene using the smartphone's computational bokeh mode
3. Randomly order the two sets of images, invite 20+ non-expert observers to provide preference ratings (MOS, Mean Opinion Score)
4. A separate expert group (5–10 photographers) evaluates:
   - Bokeh ball shape realism (1–5 points)
   - Foreground edge naturalness (1–5 points)
   - Overall blur amount and realism (1–5 points)

**Reference benchmarks (industry-grade standards):**
- MOS > 4.0: Indistinguishable from physical bokeh; excellent
- MOS 3.5–4.0: Close to physical bokeh; good
- MOS < 3.0: Visible artificial appearance; optimization required

### 5.2 EBD (Edge Blur Detection) Evaluation

EBD (Edge Blur Detection, 边缘模糊检测) is an objective metric for quantifying edge blur quality, detecting the naturalness of foreground edges in the bokeh result.

**EBD calculation method:**
1. Extract horizontal edge profiles of 30 px width at foreground edges of both the reference physical bokeh and the computational bokeh
2. Compute the gradient of the edge profiles, and analyze the width of the gradient profile (wider = more blurred, narrower = sharper)
3. Compare the edge gradient profile shapes of the computational bokeh and the physical reference:

```
EBD_score = 1 - ‖profile_calc - profile_ref‖₁ / ‖profile_ref‖₁
```

Higher EBD_score (closer to 1) means the foreground edge is closer to physical bokeh.

### 5.3 Portrait Edge ΔE Color Difference Evaluation

Quantify the color accuracy of foreground edges (avoiding color bleeding) by computing ΔE2000 color difference between the computational bokeh result and the reference in the edge transition zone.

**Workflow:**
1. Select 10–20 foreground/background boundary pixel strips (5 px wide, 50 px long)
2. In Lab color space, compute ΔE2000 at each pixel between the computational bokeh and the physical reference
3. Compute the mean and P95 of ΔE2000 within the edge strips:
   - Mean ΔE2000 < 2.0: Good (edge colors essentially accurate)
   - Mean ΔE2000 < 1.0: Excellent (colors accurate)
   - P95 ΔE2000 > 5.0: Significant local color bleeding present (unacceptable)

---

## §6 Code Examples

The following Python code implements a bokeh rendering pipeline for COC computation and spatially-varying Gaussian blur, and can be run directly.

```python
"""
计算散景演示：COC计算 + 空间变化高斯模糊 + Alpha合成
依赖：numpy, scipy (pip install numpy scipy)
"""

import numpy as np
from scipy.ndimage import gaussian_filter, zoom


# =============================================================================
# 1. 光学参数与 COC 计算
# =============================================================================

class ThinLensModel:
    """
    薄透镜光学模型，计算 COC 直径

    参数:
        focal_mm:    焦距（毫米），如 5.8mm（手机主摄实际焦距）
        f_number:    光圈数（F/#），如 1.8
        sensor_w_mm: 传感器宽度（毫米），用于像素尺寸计算
        img_w_px:    图像宽度（像素）
    """

    def __init__(self, focal_mm: float = 5.8,
                 f_number: float = 1.8,
                 sensor_w_mm: float = 9.6,
                 img_w_px: int = 4000):
        self.f_mm = focal_mm
        self.f_num = f_number
        self.aperture_mm = focal_mm / f_number   # 光圈直径（mm）
        self.pixel_size_mm = sensor_w_mm / img_w_px
        self.img_w_px = img_w_px

    def focus_distance_to_image_dist(self, obj_dist_mm: float) -> float:
        """薄透镜方程：物距→像距（mm）"""
        if obj_dist_mm <= self.f_mm + 1e-6:
            return 1e9  # 物体在焦平面内侧，无实像
        return self.f_mm * obj_dist_mm / (obj_dist_mm - self.f_mm)

    def coc_diameter_mm(self, obj_dist_mm: float,
                        focus_dist_mm: float) -> float:
        """
        计算指定物距处的 COC 直径（毫米）

        参数:
            obj_dist_mm:   被摄体物距（mm）
            focus_dist_mm: 当前对焦距离（mm）
        返回:
            coc_mm: COC 直径（毫米，绝对值）
        """
        di_obj   = self.focus_distance_to_image_dist(obj_dist_mm)
        di_focus = self.focus_distance_to_image_dist(focus_dist_mm)
        coc_mm = abs(self.aperture_mm * (di_obj - di_focus) / di_obj)
        return coc_mm

    def coc_diameter_px(self, obj_dist_mm: float,
                        focus_dist_mm: float) -> float:
        """COC 直径（像素单位）"""
        return self.coc_diameter_mm(obj_dist_mm, focus_dist_mm) / self.pixel_size_mm

    def gaussian_sigma_px(self, coc_px: float) -> float:
        """将 COC 直径（px）转换为高斯模糊 σ（px），σ = coc/4"""
        return max(coc_px / 4.0, 0.0)


def demo_coc_table(lens: ThinLensModel, focus_m: float = 1.5):
    """打印 COC 直径随物距变化的表格"""
    focus_mm = focus_m * 1000.0
    print(f"\n--- COC 直径表（焦距={lens.f_mm}mm, f/{lens.f_num:.1f}, 对焦距离={focus_m}m）---")
    print(f"{'物距(m)':>10}  {'COC(mm)':>10}  {'COC(px)':>10}  {'σ_gauss(px)':>14}")
    print("-" * 52)
    distances = [0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
    for d_m in distances:
        d_mm = d_m * 1000.0
        coc_mm = lens.coc_diameter_mm(d_mm, focus_mm)
        coc_px = lens.coc_diameter_px(d_mm, focus_mm)
        sigma  = lens.gaussian_sigma_px(coc_px)
        print(f"{d_m:10.1f}  {coc_mm:10.4f}  {coc_px:10.2f}  {sigma:14.2f}")


# =============================================================================
# 2. 合成测试深度图与图像
# =============================================================================

def generate_test_scene(height: int = 256, width: int = 384,
                        focus_dist_m: float = 1.5) -> tuple:
    """
    生成合成人像场景：前景人物（~1.5m）+ 背景（3–8m）

    返回:
        rgb:       彩色图像，shape (H, W, 3)，float32，[0,1]
        depth_m:   深度图（米），shape (H, W)，float32
        alpha_fg:  前景 alpha 掩码，shape (H, W)，float32，[0,1]
    """
    rng = np.random.default_rng(7)

    # --- 背景：渐变天空 + 绿植 ---
    y_idx, x_idx = np.mgrid[:height, :width]
    sky_r = 0.5 + 0.3 * (1 - y_idx / height)
    sky_g = 0.6 + 0.2 * (1 - y_idx / height)
    sky_b = 0.85 + 0.1 * (1 - y_idx / height)
    sky = np.stack([sky_r, sky_g, sky_b], axis=-1)

    # 绿植纹理（低频噪声）
    noise = gaussian_filter(rng.random((height, width)), sigma=8.0)
    foliage_mask = (noise > 0.55) & (y_idx > height * 0.5)
    foliage_col = np.array([0.2, 0.5, 0.15])
    bg = sky.copy()
    bg[foliage_mask] = foliage_col

    # --- 前景：简化人像轮廓（椭圆+矩形模拟头身） ---
    cx, cy_head = width // 2, height // 3
    cy_body = height * 2 // 3
    head_rx, head_ry = width // 8, height // 6
    body_rx, body_ry = width // 5, height // 3

    # 头部椭圆
    head_mask = ((x_idx - cx) / head_rx) ** 2 + ((y_idx - cy_head) / head_ry) ** 2 <= 1.0
    # 身体椭圆
    body_mask = ((x_idx - cx) / body_rx) ** 2 + ((y_idx - cy_body) / body_ry) ** 2 <= 1.0
    fg_hard = head_mask | body_mask

    # 皮肤/衣服颜色
    skin_color = np.array([0.85, 0.65, 0.52])
    shirt_color = np.array([0.25, 0.35, 0.7])
    fg_rgb = np.where(head_mask[:, :, np.newaxis], skin_color, shirt_color)

    # 合成 RGB
    rgb = np.where(fg_hard[:, :, np.newaxis], fg_rgb, bg).astype(np.float32)

    # --- 深度图 ---
    # 背景深度：3–8m（从近到远渐变），前景：1.3–1.7m（含景深变化）
    depth_bg = 3.0 + 5.0 * (y_idx / height)
    depth_fg = focus_dist_m + 0.2 * (x_idx / width - 0.5)  # 轻微深度变化
    depth_m = np.where(fg_hard, depth_fg, depth_bg).astype(np.float32)

    # --- 前景 Alpha（软边缘）---
    dist_to_fg = np.ones((height, width)) * 1e6
    from scipy.ndimage import distance_transform_edt
    dist_inside = distance_transform_edt(fg_hard)
    dist_outside = distance_transform_edt(~fg_hard)
    feather_px = 8
    alpha_fg = np.clip((dist_inside - dist_outside + feather_px) / (2 * feather_px),
                       0.0, 1.0).astype(np.float32)

    return rgb, depth_m, alpha_fg


# =============================================================================
# 3. 分层空间变化散景渲染
# =============================================================================

def render_bokeh(rgb: np.ndarray,
                 depth_m: np.ndarray,
                 alpha_fg: np.ndarray,
                 lens: ThinLensModel,
                 focus_dist_m: float = 1.5,
                 n_layers: int = 8,
                 max_sigma_px: float = 25.0) -> np.ndarray:
    """
    分层空间变化散景渲染

    参数:
        rgb:          输入图像，shape (H, W, 3)，float32，[0,1]
        depth_m:      深度图（米），shape (H, W)，float32
        alpha_fg:     前景 alpha，shape (H, W)，float32，[0,1]
        lens:         薄透镜模型实例
        focus_dist_m: 对焦距离（米）
        n_layers:     深度分层数
        max_sigma_px: 最大高斯σ（像素），限制极值
    返回:
        bokeh:        散景渲染结果，shape (H, W, 3)，float32
    """
    H, W = rgb.shape[:2]
    focus_mm = focus_dist_m * 1000.0

    # 计算每像素 COC σ
    coc_map = np.zeros((H, W), dtype=np.float32)
    for y in range(0, H, 4):  # 步长4加速（实际实现为向量化）
        for x in range(0, W, 4):
            d_mm = float(depth_m[y, x]) * 1000.0
            coc_px = lens.coc_diameter_px(d_mm, focus_mm)
            sigma = min(lens.gaussian_sigma_px(coc_px), max_sigma_px)
            coc_map[y:y+4, x:x+4] = sigma

    # 向量化计算（覆盖未填充像素）
    d_mm_map = depth_m * 1000.0
    # 近似：远场 COC 公式（do >> f）
    f_mm = lens.f_mm
    A_mm = lens.aperture_mm
    px_size = lens.pixel_size_mm
    focus_mm_val = focus_mm

    di_obj   = f_mm * d_mm_map / np.maximum(d_mm_map - f_mm, f_mm * 0.01)
    di_focus = f_mm * focus_mm_val / max(focus_mm_val - f_mm, f_mm * 0.01)
    coc_mm_map = np.abs(A_mm * (di_obj - di_focus) / np.maximum(di_obj, 1e-6))
    coc_px_map = coc_mm_map / px_size
    sigma_map = np.clip(coc_px_map / 4.0, 0.0, max_sigma_px)

    print(f"  COC σ 统计：min={sigma_map.min():.2f}px  max={sigma_map.max():.2f}px  "
          f"mean={sigma_map.mean():.2f}px")

    # 深度分层
    depth_min = depth_m.min()
    depth_max = depth_m.max()
    layer_edges = np.linspace(depth_min, depth_max + 0.01, n_layers + 1)

    # 从最远层开始合成（Z-order 从远到近）
    composite = np.zeros((H, W, 3), dtype=np.float32)
    composite_alpha = np.zeros((H, W), dtype=np.float32)

    for layer_idx in range(n_layers - 1, -1, -1):
        d_lo = layer_edges[layer_idx]
        d_hi = layer_edges[layer_idx + 1]
        layer_mask = (depth_m >= d_lo) & (depth_m < d_hi)

        if not layer_mask.any():
            continue

        # 该层的平均 σ
        layer_sigma = float(sigma_map[layer_mask].mean())

        # 对整图 RGB 施加该层 σ 的高斯模糊
        blurred = np.stack([
            gaussian_filter(rgb[:, :, c], sigma=layer_sigma)
            for c in range(3)
        ], axis=-1)

        # 该层的 alpha（在深度范围内为1，其余为0，软边缘）
        layer_alpha = layer_mask.astype(np.float32)
        layer_alpha = gaussian_filter(layer_alpha, sigma=2.0)  # 软化层边界

        # 按深度 Z-order 混合（从远到近覆盖）
        for c in range(3):
            composite[:, :, c] = (layer_alpha * blurred[:, :, c] +
                                  (1 - layer_alpha) * composite[:, :, c])
        composite_alpha = layer_alpha + (1 - layer_alpha) * composite_alpha

    # 前景清晰层覆盖（α-matting合成）
    fg_clear = rgb  # 焦点处前景使用清晰原图
    for c in range(3):
        composite[:, :, c] = (alpha_fg * fg_clear[:, :, c] +
                               (1 - alpha_fg) * composite[:, :, c])

    return np.clip(composite, 0.0, 1.0)


# =============================================================================
# 4. 完整演示
# =============================================================================

def demo_bokeh_pipeline():
    print("=== 计算散景演示：COC计算 + 分层空间变化模糊 ===\n")

    # 定义镜头模型（模拟旗舰手机主摄，实际焦距+等效模拟大光圈）
    # 使用 1.8mm 等效孔径（模拟 f/1.8 手机真实散景）
    lens_real = ThinLensModel(focal_mm=5.8, f_number=1.8,
                               sensor_w_mm=9.6, img_w_px=384)

    # 模拟全幅等效 f/1.8（夸大散景效果演示）
    lens_sim = ThinLensModel(focal_mm=5.8, f_number=0.4,
                              sensor_w_mm=9.6, img_w_px=384)

    focus_m = 1.5
    demo_coc_table(lens_real, focus_m=focus_m)
    demo_coc_table(lens_sim, focus_m=focus_m)

    # 生成合成场景
    print(f"\n生成合成人像场景（256×384）...")
    rgb, depth_m, alpha_fg = generate_test_scene(
        height=256, width=384, focus_dist_m=focus_m)

    print(f"场景统计：")
    print(f"  RGB 均值：R={rgb[:,:,0].mean():.3f}  G={rgb[:,:,1].mean():.3f}  B={rgb[:,:,2].mean():.3f}")
    print(f"  深度范围：{depth_m.min():.2f}–{depth_m.max():.2f} 米")
    print(f"  前景 α 均值：{alpha_fg.mean():.3f}（前景面积占比）")

    # 散景渲染
    print(f"\n执行分层散景渲染（{8}层，对焦距离={focus_m}m）...")
    bokeh_result = render_bokeh(
        rgb, depth_m, alpha_fg, lens_sim,
        focus_dist_m=focus_m, n_layers=8, max_sigma_px=20.0)

    # 质量验证
    print(f"\n--- 渲染结果验证 ---")
    print(f"输出尺寸：{bokeh_result.shape}")
    print(f"输出值域：[{bokeh_result.min():.4f}, {bokeh_result.max():.4f}]")

    # 前景区域清晰度验证（高α区域应接近原图）
    fg_mask = alpha_fg > 0.9
    if fg_mask.any():
        diff_fg = np.abs(bokeh_result[fg_mask] - rgb[fg_mask]).mean()
        print(f"前景清晰区域（α>0.9）与原图平均差：{diff_fg:.4f}  （应 < 0.02）")

    # 背景模糊量验证（低α低深度区域应有明显模糊）
    bg_mask = (alpha_fg < 0.1) & (depth_m > 4.0)
    if bg_mask.any():
        # 比较原图与散景结果在背景区域的局部方差（方差越小=越模糊）
        var_orig = np.var(rgb[bg_mask])
        var_bokeh = np.var(bokeh_result[bg_mask])
        print(f"背景区域（α<0.1，深度>4m）方差：原图={var_orig:.5f}  散景={var_bokeh:.5f}")
        if var_bokeh < var_orig:
            print(f"  背景方差减少比：{(1 - var_bokeh/var_orig)*100:.1f}%  ✓ 背景模糊有效")

    # COC参考值输出
    print(f"\n--- 关键物距 COC 参考（模拟镜头）---")
    for d_m in [0.5, 1.0, 1.5, 2.5, 5.0]:
        coc = lens_sim.coc_diameter_px(d_m * 1000, focus_m * 1000)
        sig = lens_sim.gaussian_sigma_px(coc)
        status = "（对焦）" if abs(d_m - focus_m) < 0.05 else ""
        print(f"  {d_m:.1f}m：COC={coc:.1f}px, σ={sig:.1f}px {status}")

    print("\n演示完成！")
    return bokeh_result


if __name__ == '__main__':
    result = demo_bokeh_pipeline()
```

**Running instructions:**
```bash
pip install numpy scipy
python ch25_demo.py
```

**Expected output key metrics:**
- Foreground sharp region (α > 0.9) average difference from original < 0.02 (foreground remains sharp)
- Background region variance reduction ratio > 60% (background blur is effective)
- COC diameter variation with object distance conforms to thin lens equation expectations

---

## §7 References

1. Hirschmüller, H., "Stereo Processing by Semiglobal Matching and Mutual Information," *IEEE Transactions on Pattern Analysis and Machine Intelligence*, vol. 30, no. 2, pp. 328–341, 2008.

2. Ranftl, R. et al., "Towards Robust Monocular Depth Estimation: Mixing Datasets for Zero-Shot Cross-Dataset Transfer," *IEEE CVPR*, 2020.

3. Kopf, J. et al., "Joint Bilateral Upsampling," *ACM SIGGRAPH*, vol. 26, no. 3, 2007.

4. He, K. et al., "Guided Image Filtering," *IEEE ECCV*, 2010; *IEEE TPAMI*, vol. 35, no. 6, pp. 1397–1409, 2013.

5. He, K. et al., "A Global Sampling Method for Alpha Matting," *IEEE CVPR*, pp. 2049–2056, 2011.

6. Gastal, E.S.L. and Oliveira, M.M., "Shared Sampling for Real-Time Alpha Matting," *Computer Graphics Forum (SIGGRAPH)*, vol. 29, no. 2, pp. 575–584, 2010.

7. Wadhwa, N. et al., "Synthetic Shallow Depth of Field on a Light-Field Phone Camera," *ACM Transactions on Graphics (SIGGRAPH)*, vol. 37, no. 4, 2018.

8. Shen, X. et al., "Automatic Portrait Segmentation for Image Stylization," *Computer Graphics Forum*, vol. 35, no. 2, 2016.

9. Demers, J., "Depth of Field: A Survey of Techniques," in *GPU Gems*, NVIDIA, 2004, ch. 23.

10. Levin, A. et al., "A Closed-Form Solution to Natural Image Matting," *IEEE CVPR*, pp. 61–68, 2006.

---

## §8 Glossary

| Term | Full Name | Description |
|------|-----------|-------------|
| Bokeh | Bokeh (散景) | The blur effect in out-of-focus regions under a large aperture (from Japanese ボケ) |
| COC | Circle of Confusion | The blurry circle formed on the sensor by an out-of-focus point source |
| PSF | Point Spread Function | Describes the image form of a point source (i.e., the blur kernel) |
| f/# | F-Number | Aperture number; focal length divided by effective aperture diameter |
| DoF | Depth of Field | The range of object distances that form a sharp image |
| Thin Lens Equation | Thin Lens Equation | 1/f = 1/do + 1/di; describes the relationship between object distance, image distance, and focal length |
| SGM | Semi-Global Matching | Semi-global matching; the industry-standard algorithm for stereo disparity estimation |
| ToF | Time of Flight | Directly measures depth by measuring photon round-trip time |
| JBU | Joint Bilateral Upsampling | Guided upsampling using the RGB image to refine low-resolution depth maps |
| Alpha Matting | Alpha Matting | Pixel-level feathering of foreground segmentation; estimates alpha values in semi-transparent transition zones |
| Color Bleeding | Color Bleeding | An artifact in bokeh compositing where foreground/background colors bleed into each other |
| Bokeh Ball | Bokeh Ball | A distinct circular light spot from a point source/highlight under large aperture |
| Halo | Halo | A light halo artifact at object edges, caused by depth estimation or compositing errors |
| Disparity | Disparity | The horizontal pixel offset of the same point between the left and right images in a dual-camera system |
| MOS | Mean Opinion Score | Mean opinion score; a standard quantification method for subjective quality evaluation |
| EBD | Edge Blur Detection | Edge blur detection; an objective metric for quantifying edge transition naturalness |
| RS | Rolling Shutter | Rolling shutter; timing effects caused by row-by-row CMOS sensor readout |
| MAD | Multi-path Interference Artifact | ToF multi-path reflection artifact causing depth flying points at depth edges |
| Guided Filter | Guided Filter | Edge-preserving filter guided by a reference image; linear time complexity |
