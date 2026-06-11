# Part 2, Chapter 14: Face Detection and Skin Enhancement in ISP

> **Pipeline position:** Parallel processing alongside ISP for AE/AF/AWB assist and portrait beautification
> **Prerequisites:** Chapter 20 (Denoising), Chapter 22 (AWB)
> **Reader path:** Algorithm Engineers, Portrait Mode Engineers

---

## §1 Theory

### 1.1 Role of Face Detection in the ISP Pipeline

Face detection is not only a high-level computer vision feature — it feeds directly into the fundamental ISP control loops:

**AE (Auto Exposure):** Without face-priority metering, a backlit subject will be silhouetted (the metering exposes for the bright background).  Face-priority AE adjusts the exposure target so that the face region's average luminance falls in the correct zone (typically Y = 100–140 for average skin tones).

**AF (Auto Focus):** Subject-tracking AF uses face/eye detection to keep the detected face in focus.  In PDAF systems, the focus algorithm directs the PDAF measurement region to the detected face bounding box.

**AWB (White Balance):** Skin tones occupy a narrow Cb-Cr locus that is predictable across illuminants. Detected skin pixels can anchor the AWB estimator, preventing the white balance from drifting to over-correct for the scene's average color when the subject is under mixed illumination.

**Portrait beautification / skin enhancement:** Detected face region bounding boxes (and optionally per-pixel face parsing masks) define where skin smoothing, brightening, and blemish removal are applied.

---

### 1.2 Face Detectors Used in ISP Context

ISP-context face detection has strict constraints: it must run in real time (≥ 30 fps), consume minimal power, and operate on the mobile NPU/DSP rather than the main CPU.

#### 1.2.1 Viola-Jones (Haar Cascade)

The original real-time face detector (Viola & Jones, 2001), still used in entry-level devices.

- Feature type: Haar wavelets on integral image
- Classification: AdaBoost cascade of weak classifiers
- Detection speed: ~10–15 ms on mobile CPU for 320×240 input
- Limitations: frontal faces only; poor with rotation; requires many cascade stages for robustness

#### 1.2.2 MTCNN (Multi-task Cascaded CNN)

A three-stage CNN pipeline: P-Net (proposal), R-Net (refinement), O-Net (output with landmark detection).

- Input: image pyramid (multiple scales)
- Output: bounding box + 5 facial landmarks (eyes, nose, mouth corners)
- Speed: ~20 ms on mobile NPU for 480×640 input
- Advantage: simultaneously outputs landmarks for face alignment before enhancement

#### 1.2.3 BlazeFace (Google, 2019)

Designed specifically for mobile real-time use on GPU/DSP.

- Input: fixed 128×128 crops extracted from image pyramid
- Architecture: MobileNet-inspired with depthwise separable convolutions; ~270 K parameters
- Output: bounding box + 6 landmarks per face; up to 6 faces per frame
- Speed: 200+ fps on mobile GPU; < 1 MB model size
- Used in: Google Pixel camera, MediaPipe Face Detection

#### 1.2.4 Ultra-Light-Fast-Generic-Face-Detector (Slim-Face)

- Designed for embedded/ISP context with very tight memory and compute budget
- Architecture: slim MobileNetV1 backbone, single-stage SSD-style head
- Model size: < 400 KB (INT8 quantized)
- Speed: ~5 ms on DSP for 320×240 input

---

### 1.3 Skin Pixel Detection in YCbCr

The most robust skin detection approach uses a learned or rule-based locus in the Cb-Cr plane (luma-independent).  Empirical studies show that human skin tones from diverse ethnicities cluster within:

$$
77 < Cb < 127, \quad 133 < Cr < 173
$$

(in BT.601 YCbCr with 8-bit representation, offset at 128)

This forms a roughly rectangular region in the Cb-Cr plane. A more accurate model uses an **elliptical skin locus**:

$$
d_{\text{skin}} = \sqrt{\left(\frac{Cb - \mu_{Cb}}{\sigma_{Cb}}\right)^2 + \left(\frac{Cr - \mu_{Cr}}{\sigma_{Cr}}\right)^2}
$$

$$
m_{\text{skin}} = \max\!\left(0,\ 1 - d_{\text{skin}}\right)
$$

Typical parameters for daylight (D65): $\mu_{Cb} = 102$, $\mu_{Cr} = 153$, $\sigma_{Cb} = 25$, $\sigma_{Cr} = 20$.

**Adaptive skin locus:** The skin cluster shifts with the scene's color temperature (CCT):

| CCT | $\mu_{Cb}$ shift | $\mu_{Cr}$ shift |
|-----|-----------------|-----------------|
| 2800 K (tungsten) | –5 (more blue) | +8 (more red) |
| 4000 K (fluorescent) | –2 | +3 |
| 6500 K (daylight) | Baseline | Baseline |
| 7500 K (overcast) | +3 | –4 |

A production system reads the AWB-estimated CCT and applies the corresponding shift to $\mu_{Cb}, \mu_{Cr}$.

---

### 1.4 Skin Enhancement Operations

Once the face region is detected and the skin mask is computed, a set of per-pixel operations is applied within the face bounding box, gated by the skin mask.

#### 1.4.1 Skin Smoothing (Bilateral Filtering)

Skin smoothing reduces the visibility of pores, fine lines, and blemishes while preserving larger facial features and non-skin details (eyebrows, lips, eyes).

**Guided bilateral filter:** Use the edge-preserved structure of the non-skin-masked image as the guide to filter only the smooth skin region:

$$
I_{\text{smooth}}(p) = \frac{1}{W_p} \sum_{q \in \mathcal{N}(p)} I(q) \cdot \exp\!\left(-\frac{|p-q|^2}{2\sigma_s^2}\right) \cdot \exp\!\left(-\frac{|I(p)-I(q)|^2}{2\sigma_r^2}\right)
$$

Typical parameters:
- $\sigma_s$ (spatial sigma): 5–15 pixels (larger = smoother, more blur)
- $\sigma_r$ (range sigma): 15–25 (luminance units, 0–255 scale; smaller = more edge-preserving)

The output is blended with the original using the skin mask:

$$
I_{\text{out}} = m_{\text{skin}} \cdot I_{\text{smooth}} + (1 - m_{\text{skin}}) \cdot I
$$

This ensures that non-skin areas (eyes, eyebrows, lips, hair) are not blurred.

#### 1.4.2 Skin Brightening / Whitening

Luminance boost applied to the skin region:

$$
Y_{\text{bright}}(p) = \text{clip}\!\left(Y(p) + \beta_{\text{bright}} \cdot m_{\text{skin}}(p),\ 0,\ 255\right)
$$

where $\beta_{\text{bright}}$ controls the strength (typically 5–20 luma units for subtle to visible brightening).

**Chroma protection:** Apply brightening only to Y; do not modify Cb or Cr.  Modifying Cb/Cr during brightening causes an unnatural color shift (skin becomes desaturated or shifts hue).

#### 1.4.3 Blemish Removal

Blemishes (acne spots, moles, dark spots) appear as local dark patches with high local contrast.  Detection:

1. Compute local mean $\mu_{\text{local}}$ and local std $\sigma_{\text{local}}$ in a small window (7×7 to 15×15)
2. Flag blemish candidate if $(Y - \mu_{\text{local}}) < -\alpha_{\text{blemish}} \cdot \sigma_{\text{local}}$ AND $m_{\text{skin}} > 0.5$
3. Replace the flagged pixel with the local mean: $Y_{\text{out}} = (1-w) \cdot Y + w \cdot \mu_{\text{local}}$

This is a localized luminance equalization within the skin region.

#### 1.4.4 Face Contour Sharpening

Selective sharpening is applied **outside** the skin mask but **within** the face bounding box — targeting the edges of facial features (eye creases, eyebrow detail, lip contour):

$$
I_{\text{sharp}} = I + \lambda_s \cdot (1 - m_{\text{skin}}) \cdot \text{unsharp\_mask}(I)
$$

where $\lambda_s$ controls sharpening strength and the $(1-m_{\text{skin}})$ mask restricts sharpening to non-skin edges.

---

### 1.5 Face Detection Confidence and Multi-Face Handling

**Confidence threshold:** A face detector outputs a confidence score per bounding box.  Only boxes above a threshold $\tau$ (e.g., 0.6 for BlazeFace) trigger beautification.  Too low a threshold causes false positives (applying skin smoothing to non-face regions); too high misses faces under challenging conditions (profile, partial occlusion).

**Multiple faces:** When multiple faces are detected:
- Apply skin smoothing to all detected faces independently
- Priority AE/AF is typically restricted to the largest (closest) face or the face nearest the frame center
- Skin mask is the union of all individual face skin masks

**Face tracking:** To avoid flickering enhancement (different faces detected each frame), apply a temporal bounding-box IIR filter:

$$
\text{box}_{n} = 0.8 \cdot \text{box}_{n-1} + 0.2 \cdot \text{box}_{\text{detected}, n}
$$

---

### 1.6 Privacy Considerations

Face detection in ISP operates on raw frames in the sensor ISP pipeline; the processed metadata (face positions, landmarks) does not leave the device in a well-designed system:

- Face bounding box coordinates are used by AE/AF/AWB and beautification on-device; they are not included in EXIF metadata by default
- Face landmark coordinates used for alignment should not be stored in the image file
- Android Camera2 API: `STATISTICS_FACE_DETECT_MODE_FULL` reports landmarks to the app; ISPs should be configurable to suppress this in privacy-sensitive modes
- On-device ML inference (BlazeFace on NPU) runs without requiring cloud connectivity; no face images are uploaded for detection

---

## §2 Calibration

### 2.1 Skin Locus Calibration Across Skin Tones and CCTs

**Procedure:**

1. Recruit subjects representing a range of skin tones (Fitzpatrick scale I–VI)
2. Photograph each subject under D65, D50, 4000K, 2800K illuminants using a light booth
3. For each image, manually annotate a 20×20 pixel skin patch on each subject's cheek
4. Record the mean Cb, Cr of each annotated patch
5. Fit an ellipse (minimum-volume bounding ellipse) to the cluster of (Cb, Cr) points per CCT
6. Store the ellipse parameters ($\mu_{Cb}$, $\mu_{Cr}$, $\sigma_{Cb}$, $\sigma_{Cr}$) as a function of CCT

**Acceptance criterion:** The calibrated locus should achieve > 95% skin pixel recall on the calibration set with < 5% false positive rate on non-skin patches.

### 2.2 Face Detection Confidence Threshold

**Procedure:**

1. Evaluate face detection on a standard benchmark (FDDB — Face Detection Data in the Wild, or WiderFace)
2. Sweep confidence threshold from 0.3 to 0.9
3. Measure precision and recall at each threshold
4. Select the threshold that achieves the target operating point (e.g., recall ≥ 0.90 at precision ≥ 0.85)

---

## §3 Tuning

### 3.1 Smoothing Strength Per Mode

| Mode | $\sigma_s$ | $\sigma_r$ | Blend $\alpha$ | Description |
|------|-----------|-----------|----------------|-------------|
| Natural | 0 | — | 0 | No skin smoothing |
| Subtle | 5 | 20 | 0.3 | Pore reduction only |
| Normal beauty | 8 | 18 | 0.6 | Default beauty mode |
| Strong beauty | 12 | 15 | 0.9 | Aggressive smoothing |

**Tuning process:** A/B test on a panel of ≥ 10 evaluators with paired comparison (original vs. enhanced). Select the $\sigma_s / \sigma_r / \alpha$ combination with the highest preference rating that does not score below 3.0 ("natural") on a naturalness scale.

### 3.2 Brightening Intensity

| Scene | $\beta_{\text{bright}}$ | Notes |
|---|---|---|
| Outdoor daylight (well-lit) | 5–8 | Subtle brightening only |
| Indoor normal lighting | 8–15 | Moderate lift |
| Dim indoor / night portrait | 15–25 | Significant lift needed |

Brightening should be adaptive to the current face region luma — if the skin region is already at Y > 200, do not apply brightening (already bright enough).

---

## §4 Artifacts

### 4.1 Over-Smoothing (Plastic / Waxy Skin)

**Description:** Faces appear unnaturally smooth, losing pore texture and fine detail. The effect is described as "plastic skin" or "waxy" by users.

**Root cause:** Bilateral filter spatial sigma $\sigma_s$ too large, or blending alpha too high (close to 1.0).  Also occurs when the skin mask bleeds into areas that should preserve texture (eyebrow region, lip area).

**Mitigation:**
- Limit $\sigma_s \leq 10$ for natural modes
- Reduce blending alpha to 0.5–0.7
- Ensure the skin mask correctly excludes eyebrows and lip areas

### 4.2 Skin Mask Bleed (Non-Skin Areas Smoothed)

**Description:** Regions adjacent to skin (hair, background, clothing) receive inappropriate skin smoothing, appearing blurred.

**Root cause:** The skin mask is too permissive at the boundaries, or the face bounding box is used directly without per-pixel skin segmentation.

**Mitigation:**
- Use the full skin mask (Cb-Cr ellipse) rather than the bounding box for smoothing gating
- Apply a morphological erosion to the skin mask before use to shrink boundaries
- Use face parsing (semantic segmentation into: skin, hair, eyes, lips, background) for precise region control

### 4.3 Unnatural Skin Tone Shift

**Description:** After brightening, skin takes on a slightly desaturated or greenish cast. Or after skin smoothing, the skin region appears slightly cooler/warmer than the original.

**Root cause:** Luma operations (brightening) affect the apparent hue when Y changes while Cb/Cr are fixed in non-linear color spaces.  Bilateral filtering can introduce slight chroma blur.

**Mitigation:**
- Apply bilateral filtering only to Y channel; copy Cb/Cr directly with sub-sampled bilateral smoothing
- Brightening: always modify only Y, never touch Cb or Cr
- Verify skin ΔE₀₀ before and after enhancement

### 4.4 False-Positive Skin Detection

**Description:** Non-face skin-tone regions (wood furniture, tan walls) receive skin smoothing.

**Root cause:** Skin locus detection has no spatial constraint — it identifies any YCbCr pixel matching the skin ellipse, including non-face objects.

**Mitigation:**
- Gate skin smoothing by the face bounding box: only apply within detected face region ± margin
- Use face-parsing mask rather than pure Cb-Cr detection

---

## §5 Evaluation

### 5.1 Face Detection Rate on Standard Benchmarks

**FDDB (Face Detection Data in the Wild):**
- 2845 images, 5171 annotated faces
- Standard metric: Discrete score (Precision/Recall) and Continuous score (IoU-weighted)
- Target: AP > 0.85 at IoU threshold 0.5

**WiderFace:**
- 32,203 images, 393,703 annotated faces across Easy/Medium/Hard splits
- Target: AP ≥ 0.90 (Easy), ≥ 0.85 (Medium), ≥ 0.70 (Hard)

### 5.2 Skin Tone ΔE₀₀ Accuracy

**Before and after enhancement:**

1. Capture reference portrait under D65 standard illuminant
2. Measure skin patch mean Lab values before enhancement
3. Apply skin enhancement pipeline
4. Measure skin patch Lab values after enhancement
5. Compute ΔE₀₀ between before and after

**Target:** ΔE₀₀ (before vs. after) < 2.0 for normal mode, < 3.0 for strong beauty mode.

A shift > 3.0 ΔE₀₀ is perceptibly unnatural and should be rejected.

### 5.3 Naturalness Subjective Score

Use forced-choice preference test (original vs. enhanced) and naturalness rating (1–5 scale):

| Score | Descriptor |
|---|---|
| 5 | Completely natural, imperceptibly enhanced |
| 4 | Subtly improved, clearly still natural |
| 3 | Visibly enhanced but acceptable |
| 2 | Noticeably artificial ("beauty filter" look) |
| 1 | Unnatural, plastic, waxy |

Target: Mean naturalness score ≥ 3.5 for normal mode, ≥ 3.0 for strong beauty mode.

---

## §6 Code

```python
"""
ch31_face_skin_enhancement.py
Demonstrates:
  - Skin pixel detection in YCbCr (elliptical locus)
  - Guided bilateral filter for skin smoothing
  - Luminance brightening with chroma protection
  - Blemish detection and removal
"""

import numpy as np
import cv2


# ------------------------------------------------------------------ #
# §6.1  Skin pixel detection in YCbCr                                #
# ------------------------------------------------------------------ #

def compute_skin_mask(
    img_bgr: np.ndarray,
    mu_cb: float    = 102.0,
    mu_cr: float    = 153.0,
    sigma_cb: float = 25.0,
    sigma_cr: float = 20.0,
) -> np.ndarray:
    """
    Compute a soft skin mask from a BGR image using the Cb-Cr elliptical locus.

    Returns float32 mask (H, W) in [0, 1]; 1.0 = fully in skin region.
    """
    # OpenCV YCrCb channel order: [Y, Cr, Cb]
    ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    Y  = ycrcb[:, :, 0].astype(np.float32)
    Cr = ycrcb[:, :, 1].astype(np.float32)
    Cb = ycrcb[:, :, 2].astype(np.float32)

    d = np.sqrt(
        ((Cb - mu_cb) / sigma_cb) ** 2 +
        ((Cr - mu_cr) / sigma_cr) ** 2
    )
    mask = np.clip(1.0 - d, 0.0, 1.0)
    return mask


def apply_cct_shift(
    mu_cb: float,
    mu_cr: float,
    cct: float,
) -> tuple:
    """
    Adjust skin locus center for the current color temperature (CCT in Kelvin).
    Returns adjusted (mu_cb, mu_cr).
    """
    if cct <= 2800:
        return mu_cb - 5.0, mu_cr + 8.0
    elif cct <= 4000:
        t = (cct - 2800) / (4000 - 2800)
        return mu_cb + t * 3.0 - 5.0, mu_cr - t * 5.0 + 8.0
    elif cct <= 6500:
        t = (cct - 4000) / (6500 - 4000)
        return mu_cb + t * 2.0 - 2.0, mu_cr - t * 3.0 + 3.0
    else:
        t = min((cct - 6500) / 1000.0, 1.0)
        return mu_cb + 3.0 * t, mu_cr - 4.0 * t


# ------------------------------------------------------------------ #
# §6.2  Bilateral filter skin smoothing                              #
# ------------------------------------------------------------------ #

def skin_smoothing(
    img_bgr: np.ndarray,
    skin_mask: np.ndarray,
    sigma_s: float = 8.0,
    sigma_r: float = 18.0,
    blend: float   = 0.6,
) -> np.ndarray:
    """
    Apply bilateral filter skin smoothing, blended by the skin mask.

    Parameters
    ----------
    img_bgr   : uint8 BGR input image
    skin_mask : float32 (H, W) in [0, 1]
    sigma_s   : spatial sigma for bilateral filter (pixels)
    sigma_r   : range sigma (luma units, 0-255 scale)
    blend     : blend strength (0 = no change, 1 = full filtered)

    Returns
    -------
    uint8 BGR image
    """
    d = max(5, 2 * int(np.ceil(sigma_s)) + 1)
    smoothed = cv2.bilateralFilter(img_bgr, d=d,
                                   sigmaColor=sigma_r,
                                   sigmaSpace=sigma_s)

    mask_3ch = np.stack([skin_mask, skin_mask, skin_mask], axis=2)
    effective_blend = blend * mask_3ch

    img_f  = img_bgr.astype(np.float32)
    smo_f  = smoothed.astype(np.float32)
    result = img_f + effective_blend * (smo_f - img_f)
    return np.clip(result, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ #
# §6.3  Skin brightening with chroma protection                      #
# ------------------------------------------------------------------ #

def skin_brightening(
    img_bgr: np.ndarray,
    skin_mask: np.ndarray,
    beta: float = 12.0,
) -> np.ndarray:
    """
    Boost luma in skin regions; do not modify Cb/Cr.

    beta : maximum luma lift (luma units, 0-255 scale)
    """
    ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    Y  = ycrcb[:, :, 0].astype(np.float32)
    Cr = ycrcb[:, :, 1]
    Cb = ycrcb[:, :, 2]

    # Only brighten pixels that are not already at max luma
    brightness_boost = beta * skin_mask * (1.0 - Y / 255.0)
    Y_bright = np.clip(Y + brightness_boost, 0, 255).astype(np.uint8)

    ycrcb_out = cv2.merge([Y_bright, Cr, Cb])
    return cv2.cvtColor(ycrcb_out, cv2.COLOR_YCrCb2BGR)


# ------------------------------------------------------------------ #
# §6.4  Blemish detection and removal                                #
# ------------------------------------------------------------------ #

def blemish_removal(
    img_bgr: np.ndarray,
    skin_mask: np.ndarray,
    window_size: int   = 11,
    threshold_k: float = 1.2,
    strength: float    = 0.8,
) -> np.ndarray:
    """
    Detect and soften dark blemishes within the skin region.

    window_size : local neighborhood size for mean/std computation
    threshold_k : std deviations below local mean to flag as blemish
    strength    : blend weight toward local mean (0 = no removal, 1 = full)
    """
    ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    Y  = ycrcb[:, :, 0].astype(np.float32)
    Cr = ycrcb[:, :, 1]
    Cb = ycrcb[:, :, 2]

    kernel = np.ones((window_size, window_size), dtype=np.float32) / (window_size ** 2)
    local_mean = cv2.filter2D(Y, -1, kernel)
    local_sq_mean = cv2.filter2D(Y ** 2, -1, kernel)
    local_std = np.sqrt(np.maximum(local_sq_mean - local_mean ** 2, 0))

    blemish_map = np.where(
        (Y < local_mean - threshold_k * local_std) & (skin_mask > 0.5),
        strength * skin_mask,
        0.0
    ).astype(np.float32)

    Y_out = np.clip(Y + blemish_map * (local_mean - Y), 0, 255).astype(np.uint8)

    ycrcb_out = cv2.merge([Y_out, Cr, Cb])
    return cv2.cvtColor(ycrcb_out, cv2.COLOR_YCrCb2BGR)


# ------------------------------------------------------------------ #
# §6.5  Face contour sharpening (outside skin mask)                  #
# ------------------------------------------------------------------ #

def face_contour_sharpening(
    img_bgr: np.ndarray,
    skin_mask: np.ndarray,
    face_bbox: tuple = None,
    strength: float = 0.5,
) -> np.ndarray:
    """
    Apply unsharp masking to non-skin facial features within the face bbox.

    face_bbox: (x, y, w, h) bounding box in image coordinates
    strength : sharpening strength (0 = no effect, 1 = full unsharp mask)
    """
    img_f = img_bgr.astype(np.float32)
    blurred = cv2.GaussianBlur(img_bgr, (5, 5), sigmaX=1.5).astype(np.float32)
    sharpened = np.clip(img_f + strength * (img_f - blurred), 0, 255)

    non_skin = np.clip(1.0 - skin_mask, 0.0, 1.0)
    face_region = np.zeros_like(non_skin)
    if face_bbox is not None:
        fx, fy, fw, fh = face_bbox
        margin = 20
        face_region[
            max(0, fy - margin):min(img_bgr.shape[0], fy + fh + margin),
            max(0, fx - margin):min(img_bgr.shape[1], fx + fw + margin)
        ] = 1.0
    else:
        face_region[:] = 1.0

    blend_mask = non_skin * face_region
    blend_3ch  = np.stack([blend_mask] * 3, axis=2)

    result = img_f + blend_3ch * (sharpened - img_f)
    return np.clip(result, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ #
# §6.6  Full skin enhancement pipeline                               #
# ------------------------------------------------------------------ #

def full_skin_enhancement_pipeline(
    img_bgr: np.ndarray,
    cct: float = 6500.0,
    mode: str  = 'normal',
    face_bbox: tuple = None,
) -> np.ndarray:
    """
    Full skin enhancement pipeline.

    Steps:
      1. Compute skin mask (CCT-adaptive)
      2. Restrict mask to face bbox if available
      3. Skin smoothing (bilateral)
      4. Skin brightening
      5. Blemish removal
      6. Face contour sharpening

    Parameters
    ----------
    img_bgr  : uint8 BGR portrait image
    cct      : estimated CCT from AWB in Kelvin
    mode     : 'subtle', 'normal', or 'strong'
    face_bbox: optional (x, y, w, h) from face detector
    """
    params = {
        'subtle': dict(sigma_s=5,  sigma_r=20, blend=0.30, beta=6.0,  sharp=0.3),
        'normal': dict(sigma_s=8,  sigma_r=18, blend=0.60, beta=12.0, sharp=0.5),
        'strong': dict(sigma_s=12, sigma_r=15, blend=0.85, beta=20.0, sharp=0.4),
    }
    p = params.get(mode, params['normal'])

    mu_cb, mu_cr = apply_cct_shift(102.0, 153.0, cct)
    skin_mask = compute_skin_mask(img_bgr, mu_cb=mu_cb, mu_cr=mu_cr)

    if face_bbox is not None:
        fx, fy, fw, fh = face_bbox
        margin = 20
        face_region = np.zeros_like(skin_mask)
        face_region[
            max(0, fy - margin):min(img_bgr.shape[0], fy + fh + margin),
            max(0, fx - margin):min(img_bgr.shape[1], fx + fw + margin)
        ] = 1.0
        skin_mask = skin_mask * face_region

    result = img_bgr.copy()
    result = skin_smoothing(result, skin_mask,
                            sigma_s=p['sigma_s'], sigma_r=p['sigma_r'],
                            blend=p['blend'])
    result = skin_brightening(result, skin_mask, beta=p['beta'])
    result = blemish_removal(result, skin_mask)
    result = face_contour_sharpening(result, skin_mask,
                                     face_bbox=face_bbox,
                                     strength=p['sharp'])
    return result


# ------------------------------------------------------------------ #
# §6.7  Demo                                                         #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    import sys

    img_path = sys.argv[1] if len(sys.argv) > 1 else None
    if img_path:
        img = cv2.imread(img_path)
    else:
        # Synthetic portrait-like image
        img = np.zeros((256, 256, 3), dtype=np.uint8)
        img[40:210, 60:200] = [130, 160, 200]   # skin-tone patch (BGR)
        img[100:110, 110:120] = [80, 100, 120]  # dark blemish
        img[80:100, 90:110]   = [30, 30, 30]    # left eye
        img[80:100, 150:170]  = [30, 30, 30]    # right eye

    print("Running skin enhancement pipeline (daylight 6500K, normal mode)...")
    enhanced = full_skin_enhancement_pipeline(img, cct=6500.0, mode='normal')

    cv2.imwrite("original.jpg", img)
    cv2.imwrite("enhanced_normal.jpg", enhanced)

    enhanced_tungsten = full_skin_enhancement_pipeline(img, cct=2800.0, mode='normal')
    cv2.imwrite("enhanced_tungsten.jpg", enhanced_tungsten)

    skin_mask = compute_skin_mask(img)
    cv2.imwrite("skin_mask.jpg", (skin_mask * 255).astype(np.uint8))

    print(f"Skin mask coverage: {skin_mask.mean()*100:.1f}% of pixels")
    print("Saved: original.jpg, enhanced_normal.jpg, enhanced_tungsten.jpg, skin_mask.jpg")
```

---

## References

- **Viola, P. & Jones, M. (2001).** Rapid Object Detection Using a Boosted Cascade of Simple Features. *CVPR 2001.*
- **Zhang, K., Zhang, Z., Li, Z., & Qiao, Y. (2016).** Joint Face Detection and Alignment Using Multitask Cascaded Convolutional Networks. *IEEE Signal Processing Letters*, 23(10), 1499–1503. (MTCNN)
- **Bazarevsky, V. et al. (2019).** BlazeFace: Sub-millisecond Neural Face Detection on Mobile GPUs. *arXiv:1907.05047.*
- **He, K., Sun, J., & Tang, X. (2013).** Guided Image Filtering. *IEEE TPAMI*, 35(6), 1397–1409.
- **Tomasi, C. & Manduchi, R. (1998).** Bilateral Filtering for Gray and Color Images. *ICCV 1998.*
- **Kovac, J., Peer, P., & Solina, F. (2003).** Human Skin Colour Clustering for Face Detection. *EUROCON 2003.*
- **FDDB Benchmark:** http://vis-www.cs.umass.edu/fddb/
