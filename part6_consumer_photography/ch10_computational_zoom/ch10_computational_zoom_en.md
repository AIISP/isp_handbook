# Part 6, Chapter 10: Computational Zoom — Full Focal-Length Continuous Coverage Algorithms

> **Position:** This chapter systematically analyzes the hardware architecture and algorithm strategies of multi-camera zoom systems in smartphones.
> **Prerequisites:** Vol.2 Ch.20 (Multi-Camera Fusion), Vol.3 Ch.03 (Super Resolution), Vol.6 Ch.01 (Consumer Photography Evolution)
> **Audience:** Algorithm engineers, product managers, IQA engineers

---

## §1 Multi-Camera Zoom System Architecture: Physical Constraints and Engineering Solutions

### 1.1 Physical Limits of Single-Lens Zoom

Traditional cameras (DSLRs/mirrorless) achieve optical zoom by moving lens groups — mechanical actuation changes the inter-element spacing, allowing the equivalent focal length to vary continuously over a range. A Nikon 24–200mm zoom lens may have a barrel extension travel exceeding 40mm, which is entirely acceptable in a camera body but simply impossible in a flagship smartphone thinner than 8mm.

**Root cause of the thickness constraint**: The main camera sensor in a smartphone is typically 1/1.3"–1" (diagonal approximately 9–15mm). The total track length (TTL) of the accompanying wide-angle lens (equivalent 24–28mm) is already at its limit (approximately 6–7mm). Achieving an equivalent focal length of 50mm (standard) would require increasing the TTL by roughly 20%; achieving 85mm (portrait) would push the optical stack length toward 20mm — far exceeding the phone's total thickness.

**Folded optics (Periscope) is the key innovation that circumvents this constraint** (see §2). Before periscope became mainstream, smartphone manufacturers chose a different route: **simulating continuous zoom by combining an array of fixed-focal-length cameras with software zoom interpolation**.

### 1.2 Multi-Camera Node Architecture

Modern flagship smartphone zoom systems are built around several "optical nodes," each being an independent fixed-focal-length camera module:

**Typical 2024 flagship configuration**:

| Camera | Equivalent FL | Sensor Size | Pixels | Primary Use |
|--------|--------------|-------------|--------|-------------|
| Ultrawide | 13–16mm (0.5–0.6×) | 1/2.5" | 12–50MP | Landscapes, architecture, vlog |
| Main (Wide/1×) | 24–26mm | 1/1.3"–1" | 50–200MP | All-round primary shooter |
| Mid-telephoto (2–3×) | 48–78mm | 1/3.5" | 10–50MP | Portraits, street |
| Periscope telephoto (5×) | 120–130mm | 1/2.5" | 50MP | Distant subjects |
| Periscope super-telephoto (10×) | 240mm | 1/3.5" | 10MP | Extreme reach |

**Samsung Galaxy S24 Ultra (2024) six-node architecture**:

$$
\text{Optical nodes: } 0.6\times \to 1\times \to 2\times \to 3\times \to 5\times \to 10\times
$$

Computational zoom interpolation fills the non-integer zoom levels between adjacent nodes, delivering a continuous 0.6× to 100× zoom experience. The range 0.6×–10× is optical zoom; 10×–100× is digital/super-resolution-enhanced computational zoom.

**Apple iPhone 15 Pro Max (2023) four-node architecture**:

$$
\text{Optical nodes: } 0.5\times \to 1\times \to 2\times \to 5\times
$$

Continuous zoom from 0.5× to 25×; beyond 5× the system relies on super-resolution (SR).

### 1.3 Parameter Space of Multi-Camera Systems

Different camera modules exhibit substantial heterogeneity at both optical and electrical levels. These differences are the core challenge for computational zoom algorithms:

| Parameter Type | Source of Variation | Impact |
|---------------|--------------------|---------|
| Focal length | Lens group design differences | Different field of view (FOV) |
| Aperture (f-number) | Lens aperture-to-focal-length ratio | Depth of field and light throughput |
| Sensor size | Physical sensor dimensions | Equivalent focal length, pixel size |
| Spectral response | CFA filter batch/supplier variation | Different color rendering |
| Lens distortion | Optical design differences per lens | Different geometric warping |
| Parallax | Physical spacing between camera centers | View angle difference in close scenes |

---

## §2 Periscope Telephoto Technology: Optical Principles of Folded Optics

### 2.1 Folded Optics Design

The core concept of the periscope lens is to redirect light incident perpendicular to the phone's rear panel — via a 45° prism or 45° mirror — so that it propagates parallel to the panel. A horizontally arranged lens group then focuses the light onto the sensor.

**Optical path geometry**: Let the phone thickness (i.e., the usable prism dimension) be $d \approx 6\text{mm}$ and the horizontal lens group length be $L$. The system equivalent focal length is:

$$
f_{\text{equiv}} = \frac{f_{\text{sensor}}}{d_{\text{sensor}}} \cdot h_{\text{sensor\_equiv}}
$$

In practice, the periscope structure allows the lens group optical length to extend along the phone's width direction, enabling equivalent focal lengths of 100–200mm (35mm equivalent) — far beyond the phone-thickness constraint.

**Aperture limitation from prism size**: The prism aperture determines maximum light throughput. The entrance aperture of a periscope camera is typically 8×8 mm² (square), slightly smaller than the circular-equivalent aperture of the main camera. As a result, periscope telephoto cameras typically have maximum apertures of f/2.8–f/4.5, larger (slower) than the main camera's f/1.7–f/2.0, meaning less light and weaker low-light performance.

### 2.2 Periscope OIS: Rotating the Prism Rather Than the Lens

Main camera OIS typically shifts the lens group to compensate for hand shake (lens-shift OIS), but the horizontal lens group in a periscope design is heavier and has a longer travel, making it difficult to actuate. The mainstream approach is **prism rotation OIS**:

$$
\theta_{\text{OIS}} = -\frac{1}{2} \theta_{\text{camera\_shake}}
$$

When the prism rotates by $\theta$, the exit ray deflects by $2\theta$ (due to optical reflection properties), so the prism only needs to rotate half the actual shake angle to fully compensate. This mechanical design is simpler (only one optical element rotates), but compensation effectiveness is influenced by the precision of the prism rotation axis.

**Samsung Galaxy S24 Ultra periscope OIS specifications**:
- Compensation angle: ±2.5° (equivalent to ±3° optical compensation in the main camera)
- Actuator: Voice Coil Motor (VCM) + Hall sensor closed-loop control
- Stabilization frequency range: DC ~ 20Hz

### 2.3 Key Flagship Periscope Parameter Comparison

| Model | Periscope Equiv. FL | Aperture | Sensor | Max Optical Zoom |
|-------|--------------------|---------|---------|--------------------|
| Samsung S24 Ultra | 5× (120mm) + 10× (240mm) | f/3.4 / f/4.9 | 50MP / 10MP | 10× |
| iPhone 15 Pro Max | 5× (120mm) | f/2.8 | 12MP | 5× |
| Huawei P60 Pro | 3.5× (90mm) | f/2.1 | 48MP | 3.5× |
| OPPO Find X7 Ultra | 3× (73mm) + 6× (135mm) | f/2.6 / f/4.3 | 50MP / 64MP | 6× |
| Xiaomi 14 Ultra | 5× (120mm) | f/3.0 | 50MP | 5× |

---

## §3 Computational Zoom Between Optical Nodes (Zoom Blending)

### 3.1 Mathematical Framework for Two-Path Blending

Using the 1× main camera (equivalent 26mm) and 3× telephoto (equivalent 78mm) as an example, with a target zoom of 2×:

**Option A: Single-camera crop**
- Use 1× main camera output; apply 2× digital crop to the center region.
- Pros: No multi-camera coordination required. Cons: Effective pixels reduced to 1/4, severe resolution loss.

**Option B: Telephoto downsampling**
- Use 3× telephoto output; downsample to the frame size corresponding to 2× field of view.
- Pros: Uses optical information. Cons: The 3× telephoto captures less of the scene (smaller FOV).

**Option C (optimal): Dual-path blending**
- Wide path: main camera output → crop to 2× FOV → obtain $I_{\text{wide,crop}}$
- Tele path: telephoto output → downsample to 2× FOV → obtain $I_{\text{tele,ds}}$
- Blend:

$$
I_{\text{blend}} = (1 - \alpha) \cdot I_{\text{wide,crop}} + \alpha \cdot I_{\text{tele,ds}}
$$

where $\alpha \in [0, 1]$ is the blending coefficient that smoothly transitions with zoom factor:

$$
\alpha(z) = \text{smoothstep}\!\left(\frac{z - z_{\text{wide}}}{z_{\text{tele}} - z_{\text{wide}}}\right), \quad z \in [z_{\text{wide}}, z_{\text{tele}}]
$$

In production systems, blending typically occurs over a small transition interval (e.g., 1.8×–2.2×) rather than the entire 1×–3× range, to reduce processing overhead.

### 3.2 Field of View Alignment

Due to manufacturing tolerances, assembly errors, and thermal deformation, different cameras do not have FOVs that precisely match their nominal zoom ratios. Precise alignment must be performed before blending:

**Step 1: Geometric correction**
- Each camera's intrinsic parameters (focal length, principal point) and distortion parameters (radial/tangential) are pre-calibrated at the factory and stored in EEPROM.
- The ISP reads the calibration data and applies distortion correction (undistortion) to each image stream based on the calibration results.

**Step 2: Cross-camera homography alignment**
- Farfield scenes (>5m) approximate a projective transformation, describable with a 3×3 homography matrix:

$$
\mathbf{p}_{\text{tele}} = H_{\text{wide} \to \text{tele}} \cdot \mathbf{p}_{\text{wide}}
$$

- $H$ is calibrated at the factory (static homography), but thermal/temporal drift requires **online re-estimation**: SIFT/ORB features are extracted from the current frame, matched between the two image streams, and RANSAC is used to update $H$ (see §5.2 for the real-time calibration approach).

**Step 3: Sub-pixel precision alignment**
- Phase correlation or normalized cross-correlation (NCC) is applied to the blend region to estimate residual sub-pixel offset, ensuring no ghosting at blend boundaries.

### 3.3 Camera Switching Latency and User Experience

**Switching time budget**: When the user's pinch gesture crosses an optical node boundary, the application layer must seamlessly switch signal sources in the viewfinder. If switching takes too long, the user sees the image "freeze and then jump."

Engineering target: camera switching time < 100ms (from start of switch to first stable frame from the new camera).

**Factors affecting switching time**:

| Phase | Typical Duration |
|-------|----------------|
| New camera sensor streaming startup | 20–50ms |
| AE/AWB convergence (pre-lock parameters to accelerate) | 0–30ms (warm-up) |
| Geometric alignment matrix computation | 2–5ms |
| Cross-camera color matching | 3–8ms |
| Total | 25–93ms |

Acceleration strategy: **Camera pre-warm** — when the user's zoom factor approaches the switching threshold, proactively wake the target camera into streaming state (but not yet written to the viewfinder). When the factor actually reaches the threshold, the switch is immediate, saving sensor startup time.

---

## §4 Super-Resolution-Assisted Digital Zoom

### 4.1 Quality Limits of Digital Zoom

When the zoom factor exceeds the maximum optical node (e.g., beyond 10×), the ISP cannot use a longer-focal-length camera to provide optical information and must digitally magnify the output from the longest available telephoto camera. Pure bilinear/bicubic interpolation causes severe blur and detail loss:

$$
\text{Effective spatial frequency (cy/px)} = \frac{f_{\text{Nyquist}}}{z_{\text{digital}}}
$$

For example, 10× optical followed by 3× digital zoom (30× total) yields an effective spatial frequency of only 1/3 of the Nyquist frequency — a large amount of high-frequency detail is lost and the image appears blurred.

Super-resolution (SR) networks aim to **learn a prior for reconstructing high-frequency detail**, recovering high-resolution (HR) detail from a low-resolution (LR) image:

$$
\hat{I}_{\text{HR}} = f_{\text{SR}}(I_{\text{LR}}; \theta)
$$

where $\theta$ are network parameters trained on large numbers of LR-HR pairs.

### 4.2 RealESRGAN: Blind Super-Resolution for Real-World Degradations

Traditional SR networks (e.g., SRCNN, EDSR) are trained on simple bicubic-downsampling degradation models and cannot handle the complex degradations present in real digital zoom (combinations of motion blur, high-ISO noise, and JPEG compression artifacts).

**RealESRGAN** (ICCV 2021 Workshop, Wang et al., Tencent ARC Lab) introduces a **high-order degradation model**:

$$
I_{\text{LR}} = \left[(I_{\text{HR}} \ast k_1) \downarrow_{r_1} + n_1\right] \ast k_2 \downarrow_{r_2} + n_2 \text{ JPEG}
$$

This simulates two rounds of degradation: each round consists of convolution blur ($k_i$) + downsampling ($\downarrow_{r_i}$) + additive noise ($n_i$), followed by JPEG compression artifacts. By randomly sampling these degradation parameters, the training set covers the majority of degradation types encountered in practice.

**Network architecture**: RealESRGAN is based on the RRDB (Residual-in-Residual Dense Block) backbone; the ×4 SR version has approximately 16.7M parameters. With INT8 quantization and NPU acceleration at inference time, it achieves mobile-deployable performance.

**Snapdragon mobile performance** (reference: NTIRE 2024 Mobile SR Track data):
- Snapdragon 8 Gen 3 NPU: lightweight SR network (~1M parameters), ×2 SR, 4K input, approximately 4–6ms/frame
- Flagship SR (~4M parameters), ×4 SR: approximately 15–25ms/frame (suitable for photography; video requires further model compression)

### 4.3 Samsung Space Zoom: Engineering Implementation of 100× Zoom

**Samsung Galaxy S20 Ultra (2020)** first introduced "100× Space Zoom," featuring a 48 MP periscope lens (f/3.5, ~240 mm equivalent) with **4× optical zoom** (not 10×); a 10× hybrid zoom is achieved by combining the periscope with a main-sensor crop. **Samsung Galaxy S21 Ultra (2021)** upgraded to true **10× optical zoom** (folded-optics periscope, HM3 sensor, ~240 mm equivalent) — the first mainstream consumer smartphone to achieve genuine 10× optical zoom. Using S21 Ultra as the example, the 100× Space Zoom breakdown is:
- Optical zoom: 1× → 10× (S21 Ultra periscope, 10× optical, ~240 mm equivalent)
- Periscope sensor crop: 10× → 20× (center crop to ~¼ sensor area equivalent)
- Super-resolution enhancement: 20× → 30× (1.5× SR, ISP on-device AI)
- Deep learning stabilization + SR: 30× → 100× (additional ~3.3× AI SR + stabilization, with noticeable quality degradation)

**Practical analysis of 100× zoom**: At 100×, image quality is fundamentally limited by:
1. **Atmospheric turbulence**: During outdoor long-distance shooting, refractive index fluctuations in the air cause image jitter and blur that algorithms cannot compensate.
2. **Amplified sensor noise**: 100× digital magnification means noise is also amplified 100× at the pixel level, especially severe at high ISO.
3. **Stabilization limits**: Even with OIS + EIS, the equivalent angular resolution at 100× is extremely high; minute shake causes blur.

Practical conclusion: **100× zoom is better suited for "framing" than for detail extraction** — find the location of a distant subject, then reduce zoom to 30×–50× for the actual shot. Samsung's S24 Ultra 100× UI specifically shows a "Best at 50×" prompt, effectively acknowledging that 100× is an extreme reference rather than a practical shooting tool.

### 4.4 Still Photography SR vs. Video SR

| Dimension | Still SR | Video SR |
|-----------|---------|----------|
| Latency budget | 1–3 seconds (user-acceptable) | < 33ms (30fps, real-time) |
| Model complexity | 4–16M parameters | 0.5–2M parameters |
| Temporal consistency | Single frame independent | Requires inter-frame smoothing (otherwise flickering) |
| Multi-frame utilization | Possible (burst SR) | Single frame or limited multi-frame (2–3 frames) |
| Hardware acceleration | NPU offline | ISP hardware pipeline integration |

---

## §5 Cross-Camera Color Consistency

### 5.1 Root Cause Analysis of Color Inconsistency

Shooting the same scene through different cameras may yield images with noticeably different colors, for the following reasons:

**Spectral response differences**: Different batches of CFA (Color Filter Array) filters do not have identical transmittance curves for R/G/B channels, causing the white balance gains (R gain, B gain) to differ between cameras under the same light source.

**Optical characteristic differences**: Telephoto lenses (especially periscope designs) introduce more optical elements into the light path; each element's coating subtly modifies the spectral transmittance, causing the overall color of the telephoto path to appear slightly cooler or warmer.

**Sensor quantum efficiency differences**: Different sensor models (from different suppliers: Sony IMX, Samsung ISOCELL, OmniVision, etc.) have different spectral quantum efficiency (QE) curves.

**Consequences**: During zoom transitions (e.g., switching from 1× to 3×), unmatched colors cause a sudden color shift visible to the user — a major product experience defect.

### 5.2 Factory Static Color Calibration

At the factory, using a standard light source (D65) and a standard color target (X-Rite ColorChecker), each camera is independently calibrated with a CCM (Color Correction Matrix):

$$
\mathbf{c}_{\text{corrected}} = M_{\text{CCM}} \cdot \mathbf{c}_{\text{raw}}
$$

**Cross-camera color anchoring strategy**: The main camera (1×) is used as the color reference (anchor). The color transformation matrix $M_{i \to \text{wide}}$ of each auxiliary camera relative to the main camera is calibrated:

$$
M_{i \to \text{wide}} = M_{\text{CCM,wide}} \cdot M_{\text{CCM},i}^{-1}
$$

During real-time processing, the auxiliary camera output is first converted through $M_{i \to \text{wide}}$ before being blended with the main camera image, ensuring color consistency.

### 5.3 Online Real-Time Color Re-calibration

Static factory calibration cannot adapt to the following dynamic changes:
- **Temperature drift**: Sensor temperature rise (up to 15–30°C during video recording) alters dark current and color response.
- **Rapid changes in illuminant color temperature**: Moving from outdoors to indoors drops the illuminant color temperature from 6500K to 3000K; each camera's AWB response speed differs slightly.
- **Component aging**: Long-term use causes subtle changes in CFA transmittance.

**Online re-calibration approach**:

During zoom transition frames (typically a "dual-stream mode" where both cameras are read simultaneously), the ISP samples color statistics from the overlapping region in both images:

$$
\hat{g} = \arg\min_{g} \left\| \text{hist}_1(\text{region}) - \text{hist}_2(g \cdot \text{region}) \right\|^2
$$

where $g$ is a 3-dimensional color gain correction factor (one per R/G/B channel), estimated by minimizing the difference between the luminance/chrominance histograms of the overlapping region in both images. This process completes in approximately 2–5ms in ISP hardware.

**Stability constraint on color anchoring**: The correction factor cannot be adjusted without limits; otherwise, accumulated color drift occurs during long recordings. In practice, the maximum correction per frame is constrained:

$$
|g_t - g_{t-1}| \leq \Delta g_{\max} \approx 0.02\text{ (max 2% adjustment per frame)}
$$

### 5.4 Color Consistency Evaluation Methods

| Metric | Definition | Typical Pass Threshold |
|--------|-----------|----------------------|
| ΔE2000 (color difference) | CIE ΔE2000 in LAB color space | ΔE < 2.0 at zoom transition |
| Gray axis deviation | Deviation of neutral gray in the ab plane | < 1.5 |
| Luminance mismatch | Y-channel difference between two paths for the same scene | < 5% |
| Transition flash | Peak inter-frame color difference before/after switch | < ΔE 4.0 |

---

## §6 Code Implementation: Computational Zoom Simulation

This chapter's companion Jupyter Notebook (*See §6 Code section for runnable examples.*) contains the following modules:

### 6.1 Dual-Camera Zoom Blending Simulation

```python
import numpy as np
import cv2
import matplotlib.pyplot as plt
from scipy.ndimage import zoom as scipy_zoom

def simulate_dual_camera_zoom(img_wide, img_tele, zoom_factor,
                               wide_focal=26.0, tele_focal=78.0):
    """
    Simulate blended output from a dual-camera system (1× wide + 3× tele)
    at the specified zoom factor.

    img_wide: main camera image [H, W, 3], equivalent 26mm focal length
    img_tele: telephoto image [H, W, 3], equivalent 78mm (1/3 FOV of wide)
    zoom_factor: target zoom factor (1.0 ~ 3.0)
    wide_focal: main camera equivalent focal length (mm)
    tele_focal: telephoto equivalent focal length (mm)

    Returns: blended zoom image [H', W', 3]
    """
    H, W = img_wide.shape[:2]
    tele_ratio = tele_focal / wide_focal  # = 3.0

    # Wide path: crop to target field of view
    crop_ratio = wide_focal / (zoom_factor * wide_focal)  # = 1/zoom_factor
    crop_h = int(H * crop_ratio)
    crop_w = int(W * crop_ratio)
    cy, cx = H // 2, W // 2
    y1, y2 = cy - crop_h//2, cy + crop_h//2
    x1, x2 = cx - crop_w//2, cx + crop_w//2
    img_wide_crop = img_wide[y1:y2, x1:x2]
    img_wide_resized = cv2.resize(img_wide_crop, (W, H), interpolation=cv2.INTER_CUBIC)

    # Tele path: downsample to target FOV (keep center zoom/tele_ratio fraction)
    tele_crop_ratio = zoom_factor / tele_ratio
    tc_h = int(H * tele_crop_ratio)
    tc_w = int(W * tele_crop_ratio)
    ty1, ty2 = cy - tc_h//2, cy + tc_h//2
    tx1, tx2 = cx - tc_w//2, cx + tc_w//2

    if tele_crop_ratio <= 1.0:
        img_tele_crop = img_tele[ty1:ty2, tx1:tx2]
        img_tele_resized = cv2.resize(img_tele_crop, (W, H), interpolation=cv2.INTER_CUBIC)
    else:
        # zoom < 1 (should not occur in 1×~3× range; protective fallback)
        img_tele_resized = cv2.resize(img_tele, (W, H), interpolation=cv2.INTER_CUBIC)

    # Compute blending coefficient (smoothstep transition)
    t = (zoom_factor - wide_focal/wide_focal) / (tele_ratio - 1.0)  # [0,1]
    t = np.clip(t, 0, 1)
    alpha = t * t * (3.0 - 2.0 * t)  # smoothstep

    # Blend
    img_blend = (1 - alpha) * img_wide_resized.astype(np.float32) \
              + alpha * img_tele_resized.astype(np.float32)

    return np.clip(img_blend, 0, 255).astype(np.uint8), alpha

# Visualize output at different zoom levels
zoom_levels = [1.0, 1.5, 2.0, 2.5, 3.0]
fig, axes = plt.subplots(1, len(zoom_levels), figsize=(20, 4))
for ax, z in zip(axes, zoom_levels):
    # Assumes img_wide, img_tele are already loaded
    result, alpha = simulate_dual_camera_zoom(img_wide, img_tele, z)
    ax.imshow(result)
    ax.set_title(f'{z}× (α={alpha:.2f})')
    ax.axis('off')
plt.suptitle('Dual-Camera Zoom Blending Simulation (1× Wide + 3× Tele)')
plt.tight_layout()
plt.show()
```

### 6.2 Super-Resolution-Assisted Digital Zoom (ESRGAN-based)

```python
def digital_zoom_with_sr(img_base, zoom_factor, optical_max=3.0,
                          sr_model=None):
    """
    When zoom exceeds the maximum optical ratio, use a super-resolution
    network to enhance digital zoom.

    img_base: longest telephoto camera image (3× optical)
    zoom_factor: target zoom (3× ~ 9×)
    optical_max: maximum optical zoom ratio (3.0)
    sr_model: super-resolution network (ESRGAN or lightweight variant)
    """
    H, W = img_base.shape[:2]
    digital_scale = zoom_factor / optical_max  # required digital magnification

    # Step 1: Crop target region
    crop_ratio = 1.0 / digital_scale
    crop_h = int(H * crop_ratio)
    crop_w = int(W * crop_ratio)
    cy, cx = H // 2, W // 2
    img_crop = img_base[cy-crop_h//2:cy+crop_h//2,
                        cx-crop_w//2:cx+crop_w//2]

    if sr_model is not None:
        # Step 2: SR network inference (requires pre-loaded ONNX or TFLite model)
        img_sr = sr_model.infer(img_crop)
    else:
        # Fallback: bicubic interpolation
        img_sr = cv2.resize(img_crop, (W, H), interpolation=cv2.INTER_CUBIC)

    return img_sr

# Comparison: bicubic vs SR-assisted
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
# Original (3× optical)
axes[0].imshow(img_tele)
axes[0].set_title('3× Optical')
# 6× bicubic (pure crop + interpolation)
img_bilinear = digital_zoom_with_sr(img_tele, 6.0, sr_model=None)
axes[1].imshow(img_bilinear)
axes[1].set_title('6× Bicubic Interpolation')
# 6× SR-enhanced (if model is available)
# img_sr = digital_zoom_with_sr(img_tele, 6.0, sr_model=sr_net)
# axes[2].imshow(img_sr)
axes[2].set_title('6× SR-Enhanced (RealESRGAN)')
for ax in axes:
    ax.axis('off')
plt.tight_layout()
plt.show()
```

### 6.3 Cross-Camera Color Consistency Correction

```python
def compute_color_correction(img_ref, img_target, region_mask=None):
    """
    Compute color correction gains from the target camera to the reference
    camera (main camera).

    img_ref: reference image (main camera, 1×), RGB float32 [0,1]
    img_target: image to correct (telephoto, view-aligned), RGB float32 [0,1]
    region_mask: overlap region mask; if None, uses center region

    Returns: 3-dimensional color gain correction vector [r_gain, g_gain, b_gain]
    """
    if region_mask is None:
        H, W = img_ref.shape[:2]
        margin = H // 4
        region_mask = np.zeros((H, W), dtype=bool)
        region_mask[margin:-margin, margin:-margin] = True

    ref_pixels = img_ref[region_mask]
    tgt_pixels = img_target[region_mask]

    # Compute per-channel mean ratio (simple gain correction)
    gains = np.mean(ref_pixels, axis=0) / (np.mean(tgt_pixels, axis=0) + 1e-8)

    # Limit correction range (avoid aggressive over-correction)
    gains = np.clip(gains, 0.8, 1.25)

    return gains

def apply_color_correction(img, gains):
    """Apply color gain correction."""
    corrected = img * gains[np.newaxis, np.newaxis, :]
    return np.clip(corrected, 0, 1)

# Demonstrate color correction effect
gains = compute_color_correction(img_wide_aligned, img_tele_aligned)
img_tele_corrected = apply_color_correction(img_tele_aligned, gains)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
axes[0].imshow(img_wide_aligned)
axes[0].set_title('Main Camera (Color Reference)')
axes[1].imshow(img_tele_aligned)
axes[1].set_title('Telephoto (Before Correction)')
axes[2].imshow(img_tele_corrected)
axes[2].set_title(f'Telephoto (After Correction, gains={gains.round(3)})')
for ax in axes:
    ax.axis('off')
plt.show()
```

The full Notebook also includes: (1) simulation of a 6-node zoom system with visualization of FOV coverage for each node; (2) calculation of the equivalent SNR penalty at each focal length (accounting for noise amplification from crop and SR upscaling); (3) color consistency evaluation (ΔE2000 calculation); (4) SSIM and PSNR comparison before and after zoom using OpenCV.

---

## §7 Product Tuning and Artifact Analysis

### 7.1 Common Artifacts in Computational Zoom

| Artifact | Description | Trigger Scenario | Solution |
|----------|------------|-----------------|----------|
| Color jump | Sudden color shift when switching cameras | Illumination change + AWB not converged | Online color correction + larger smoothing window |
| Ghosting | Double image in blending region | Parallax region (close subjects) | Depth-aware blending (force single-camera for close range) |
| Resolution cliff | Noticeable sharpness gap at the switch point | 1×→3× transition | Widen transition interval + SR compensation |
| SR artifacts | Super-resolution hallucinating false detail | Smooth textures (skin, sky) | Fidelity regularization loss, limit SR gain |
| Near-scene parallax shift | Misalignment in dual-camera image for close subjects | Close-up subjects | Force single-camera output, no blending |
| Noise level jump | Different cameras have different low-light SNR; noise character changes at switch | Night zoom | Unify noise intensity (smooth sigma curve) |

### 7.2 Close-Scene Parallax Handling

Parallax is the most troublesome problem in multi-camera systems for close-range photography. When the shooting distance $d$ is small, the view angle difference $\delta$ caused by the inter-camera baseline $b$ (typically about 10–20mm) becomes non-negligible:

$$
\delta \approx \arctan\!\left(\frac{b}{d}\right) \approx \frac{b}{d} \text{ (small angle approximation)}
$$

For example, with $b = 15\text{mm}$ and $d = 0.5\text{m}$: $\delta \approx 1.7°$ — in the main camera FOV of 77° (26mm equivalent), this view angle difference corresponds to approximately 2.2% of FOV, or about $0.022 \times 4000 = 88$ pixels of offset — far beyond the range that registration algorithms can accurately correct.

**Engineering solutions**:
- Set a close-range threshold (typically determined by autofocus distance): when AF detects focus distance < 1m, force single-camera output (no dual-camera blending).
- Some manufacturers use depth maps (from ToF sensors or stereo estimation) for region-based blending — dual-camera for distant areas, single-camera for near areas.

### 7.3 Evaluation Metric System

Systematic evaluation framework for computational zoom quality:

| Metric Category | Specific Metric | Test Method |
|----------------|----------------|-------------|
| Resolution | MTF50 (cycles/pixel) at each zoom | Siemens star / slanted edge |
| Noise | SNR (dB) at each zoom vs lux level | Gray patch NR measurements |
| Color | ΔE2000 between zoom levels | X-Rite ColorChecker sequence |
| Transition smoothness | Peak color variance in transition frames | Video recording at transition zoom |
| Close-range artifacts | Parallax misalignment in pixels | Checkerboard at 30/50/100cm |
| SR quality | SSIM / LPIPS (perceptual similarity) | Standard SR benchmark images |

---

## §8 Glossary

| Term | Full Name / Abbreviation | Explanation |
|------|------------------------|-------------|
| Periscope zoom | Periscope Zoom | Lens design using folded optics to achieve super-telephoto, enabling equivalent 100–200mm focal lengths in ultra-thin phones |
| Space Zoom | Space Zoom (Samsung brand name) | Commercial name for Samsung flagship multi-camera zoom system; supports up to 100× |
| Cross-camera color calibration | Cross-Camera Color Calibration | Calibration and real-time correction algorithms to eliminate color differences between different cameras |
| Digital zoom | Digital Zoom | Virtual zoom beyond optical nodes, achieved via cropping and interpolation/super-resolution |
| Zoom blending | Zoom Blending | Weighted blending of outputs from two adjacent optical-node cameras to achieve smooth zoom transition |
| OIS | Optical Image Stabilization | Optical stabilization via physical movement of lens elements or prism to compensate for hand shake |
| Super-resolution | Super Resolution / SR | Algorithm for reconstructing high-resolution detail from low-resolution images; used to assist digital zoom |
| Homography | Homography | 3×3 matrix describing the projective transformation between two images; used for cross-camera alignment |
| Parallax | Parallax | View angle difference when the same scene is captured from different camera positions; especially prominent for close subjects |
| RealESRGAN | Real-World ESRGAN | Blind super-resolution network for real-world image degradations (ICCV 2021 Workshop, Tencent ARC) |
| Optical node | Optical Node | Each independent fixed-focal-length camera module in a multi-camera zoom system, corresponding to a specific zoom ratio point |

---

## §9 References

1. Samsung Electronics, "Galaxy S20 Ultra Space Zoom Technical Specification" (2020). Samsung official product release documentation.
2. Samsung Electronics, "Galaxy S24 Ultra Camera System" (2024). Samsung official product technical brief.
3. Apple Inc., "iPhone 15 Pro Camera System" (2023), Apple Newsroom. https://www.apple.com/newsroom/2023/09/
4. Wang, X. et al., "Real-ESRGAN: Training Real-World Blind Super-Resolution with Pure Synthetic Data" (2021). ICCV 2021 Workshop. arXiv:2107.10833.
5. Ren, B. et al., "NTIRE 2024 Challenge on Efficient Super-Resolution: Methods and Results" (2024). CVPR 2024 Workshop. arXiv:2404.09965.
6. Wronski, B. et al., "Handheld Multi-Frame Super-Resolution" (2019). SIGGRAPH 2019. ACM Trans. Graphics 38(4).
7. Liang, J. et al., "SwinIR: Image Restoration Using Swin Transformer" (2021). ICCV 2021 Workshop. arXiv:2108.10257.
8. Apple Inc., "WWDC 2023 - Capture with the iPhone camera system" (2023). Apple Developer. https://developer.apple.com/videos/play/wwdc2023/
9. Zhang, Z. et al., "Learning RAW-to-sRGB Mappings with Inaccurately Aligned Supervision" (2021). ICCV 2021. [Cross-camera color alignment related]
10. Wang, J. et al., "Zoom to Perceive Better: No-Reference Point Cloud Quality Assessment via Exploring Effective Multiscale Feature" (2024). IEEE TCSVT. [Note: original citation described this as image SR; the actual paper with this title is about point cloud quality assessment; please verify intended reference]
