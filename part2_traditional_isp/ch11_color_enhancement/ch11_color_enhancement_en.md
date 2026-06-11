# Part 2, Chapter 11: Color Enhancement and Saturation Adjustment

> **Pipeline position:** Post-CCM color rendering, before CSC output
> **Prerequisites:** Chapter 22 (AWB), Chapter 23 (CCM)
> **Reader path:** Algorithm Engineers, Tuning Engineers

---

## §1 Theory

### 1.1 Color Models: HSL, HSV, and YCbCr

Color enhancement in an ISP pipeline is almost always performed in a perceptually-organized color space rather than directly in linear RGB.  Three representations are commonly used:

**HSV (Hue, Saturation, Value)**

```
H ∈ [0°, 360°)  — position on color wheel
S ∈ [0, 1]       — purity / distance from white
V ∈ [0, 1]       — brightness (max of R, G, B)
```

Conversion from normalized RGB:

```
V  = max(R, G, B)
S  = (V - min(R, G, B)) / V        if V > 0, else 0
H  = (segment offset + (X - Y) / (V - min)) * 60°
```

**HSL (Hue, Saturation, Lightness)**

Lightness L = (max + min) / 2 defines a double cone; saturation is renormalized against L.  HSL is more intuitive for "tinting" operations (adding white or black).

**YCbCr (luma + blue/red chroma)**

In hardware ISPs, color adjustments are overwhelmingly applied in YCbCr space because:
- Y and chroma are already separated after CCM → CSC
- Chroma Cb/Cr axes map cleanly to blue-yellow and red-cyan axes
- Skin tone detection is straightforward in Cb-Cr coordinates
- JPEG/HEIF encoding expects YCbCr, so no extra conversion is needed

The BT.601 forward transform from sRGB:

```
Y  =  0.299·R + 0.587·G + 0.114·B
Cb = -0.169·R - 0.331·G + 0.500·B + 128
Cr =  0.500·R - 0.419·G - 0.081·B + 128
```

Color enhancement modifies Cb and Cr (and sometimes Y) before the inverse transform returns to RGB for display or encoding.

---

### 1.2 Global Saturation Multiplier

The simplest enhancement is a scalar multiplication of the chroma channels around the neutral axis:

$$
Cb' = 128 + \alpha \cdot (Cb - 128)
$$

$$
Cr' = 128 + \alpha \cdot (Cr - 128)
$$

where $\alpha$ is the global saturation gain factor.

| $\alpha$ value | Visual effect |
|---|---|
| 0.0 | Monochrome (grayscale) |
| 0.8 | Desaturated / film look |
| 1.0 | No change (identity) |
| 1.2 | Vivid / punchy colors |
| 1.3 | Maximum vivid (typical smartphone "vivid" mode) |
| > 1.5 | Oversaturation artifacts likely |

**Implementation consideration:** Clipping must be applied after multiplication.  Cb and Cr are 8-bit unsigned integers in JPEG (range 0–255, neutral at 128).  After $\alpha > 1$ multiplication, values can exceed 255 or fall below 0, which must be clamped.

---

### 1.3 Independent Cb/Cr Scaling

Rather than a single scalar $\alpha$, independent gains $\alpha_{Cb}$ and $\alpha_{Cr}$ allow asymmetric chroma adjustments.  This is useful when white balance residuals leave one axis slightly off:

$$
Cb' = 128 + \alpha_{Cb} \cdot (Cb - 128)
$$

$$
Cr' = 128 + \alpha_{Cr} \cdot (Cr - 128)
$$

Typical tuning example: Under tungsten light with a warm scene, $\alpha_{Cb}$ may be increased slightly (e.g., 1.05) to compensate for the cooler appearance of blue objects while $\alpha_{Cr}$ remains at 1.0.

---

### 1.4 Six-Axis Hue Rotation

A global saturation multiplier cannot fix the hue of individual colors; for example, reds may look too orange, or greens may look too cyan, while the rest of the palette is accurate.  The industry standard solution is **6-axis hue control**, where the color wheel is divided into six segments (Red, Yellow, Green, Cyan, Blue, Magenta) and each axis has independent hue rotation $\Delta H$ and saturation scaling $\Delta S$.

**Algorithm:**

1. Convert pixel from YCbCr → HSV (or HSL)
2. Compute hue angle H (0–360°)
3. Determine which of the six segments the pixel falls in (within ±30° of the axis center)
4. Compute a smooth blending weight using a triangular or cosine function:

$$
w(H) = \max\!\left(0,\ 1 - \frac{|H - H_{\text{axis}}|}{30°}\right)
$$

5. Apply the per-axis rotation and saturation adjustment, weighted by $w$:

$$
H' = H + w(H) \cdot \Delta H_{\text{axis}}
$$

$$
S' = S \cdot (1 + w(H) \cdot \Delta S_{\text{axis}})
$$

6. Convert back to YCbCr

The six axis centers are at H = 0° (Red), 60° (Yellow), 120° (Green), 180° (Cyan), 240° (Blue), 300° (Magenta).

**Typical calibration targets:**

| Axis | Common tuning goal | Typical $\Delta H$ |
|------|-------------------|--------------------|
| Red | Shift slightly toward orange for richer reds | +5° to +8° |
| Yellow | Accurate Macbeth yellow patch | ±3° |
| Green | Shift away from yellow-green (more saturated green) | -5° to -10° |
| Blue | Sky punch — deepen blue sky | 0° (saturation boost) |
| Skin tones (Yellow-Red axis) | Protect warmth | +0° to +3° |

---

### 1.5 Luminance-Dependent Saturation Curves

A single global multiplier treats bright highlights and deep shadows identically.  In practice, dark saturated colors look muddy and noisy, while bright saturated colors look garish.  A **luminance-dependent saturation curve** applies a different saturation gain depending on the pixel's luma Y:

$$
\alpha(Y) = \text{LUT}[Y]
$$

where LUT is a 1D table of 256 entries (for 8-bit Y).

Typical curve shape:

```
Saturation gain α
1.3 |             ***
1.2 |         ****   *
1.1 |      ***        *
1.0 | *****            ***
0.9 |                      *
     0        128           255
                  Y (Luma)
```

- **Shadows (Y < 64):** Reduce saturation slightly (α ≈ 0.90) to suppress noise-amplified chroma in dark areas
- **Midtones (Y = 96–192):** Boost saturation (α ≈ 1.2–1.3) for vivid colors
- **Highlights (Y > 220):** Reduce saturation (α ≈ 0.95) to prevent highlight oversaturation (neon artifacts on white objects)

---

### 1.6 Skin Tone Protection

The most important constrained region in color enhancement is the **skin tone locus**.  Skin pixels across all ethnicities form a narrow elliptical cluster in the Cb-Cr plane:

$$
77 < Cb < 127, \quad 133 < Cr < 173
$$

(in 8-bit YCbCr with offsets at 128)

When saturation is boosted globally, skin tones become oversaturated — faces look orange and unnatural.  The solution is to detect skin pixels and apply a **reduced saturation multiplier** within the skin region:

$$
\alpha_{\text{effective}} = \alpha_{\text{global}} \cdot (1 - \beta \cdot m_{\text{skin}})
$$

where $m_{\text{skin}} \in [0, 1]$ is a soft skin mask and $\beta$ controls the strength of skin protection (typically $\beta$ = 0.3–0.5).

The soft skin mask uses a smooth elliptical distance function:

$$
d_{\text{skin}} = \sqrt{\left(\frac{Cb - Cb_{\text{center}}}{\sigma_{Cb}}\right)^2 + \left(\frac{Cr - Cr_{\text{center}}}{\sigma_{Cr}}\right)^2}
$$

$$
m_{\text{skin}} = \max(0,\ 1 - d_{\text{skin}})
$$

with $Cb_{\text{center}} = 102$, $Cr_{\text{center}} = 153$, $\sigma_{Cb} = 25$, $\sigma_{Cr} = 20$ as typical starting values.

**Adaptive skin locus:** The skin Cb-Cr cluster shifts with CCT (color temperature of the scene illuminant).  Under tungsten (2800 K), skin has higher Cr; under daylight (6500 K), Cr is lower.  A production system reads the current AWB CCT estimate and shifts the skin ellipse center accordingly.

---

### 1.7 Vivid Mode vs. Natural Mode

Most smartphone cameras expose two color rendering presets:

| Mode | $\alpha$ global | 6-axis tuning | Skin protection | Target audience |
|------|----------------|---------------|-----------------|-----------------|
| Natural | 1.0–1.05 | Minimal corrections | None needed | Professionals, RAW+JPEG users |
| Standard | 1.10–1.15 | Moderate | Moderate | Default consumer |
| Vivid | 1.20–1.30 | Aggressive (boost blue sky, green foliage) | Strong | Social media, casual users |

The tradeoff: **vivid mode improves punch and appeal on social media but degrades ΔE₀₀ accuracy** on ColorChecker.  Calibration reports must always specify which rendering mode was active.

---

## §2 Calibration

### 2.1 ColorChecker Validation

**Standard reference target:** Macbeth ColorChecker Classic (24 patches), or X-Rite ColorChecker Passport.

**Procedure:**

1. Capture the chart under a D65 or D50 standard illuminant (use a light booth)
2. Ensure AWB is disabled (use manual daylight white balance) or the chart includes a neutral patch for AWB lock
3. Measure the sRGB values of each patch in the processed image
4. Compare against the CIECAM-based reference sRGB values provided by X-Rite
5. Compute ΔE₀₀ for each patch

**Acceptance criteria:**

| Metric | Target |
|--------|--------|
| Mean ΔE₀₀ (all 24 patches) | < 3.0 |
| Skin-tone patches (patches 1–4) | < 2.0 |
| Neutral patches (patches 19–24) | < 1.5 |
| Max ΔE₀₀ (any single patch) | < 6.0 |

### 2.2 Per-Scene-Mode Tuning

Each scene mode (portrait, landscape, night, food, etc.) requires separate color enhancement tuning because the expected content and color priorities differ:

| Scene mode | Typical tuning |
|---|---|
| Portrait | Skin protection ON, moderate saturation (α = 1.1) |
| Landscape | Blue/green boost (sky + foliage), α = 1.25 |
| Food | Warm tone shift (red/yellow axis boost), α = 1.20 |
| Night | Reduce saturation (α = 0.95) to suppress noise amplification |
| Document | Desaturate almost to grayscale (α = 0.5–0.7) |

### 2.3 Hue Calibration Using Macbeth Chart

For 6-axis hue calibration:

1. Measure each Macbeth patch's measured H vs. reference H
2. Compute $\Delta H_{\text{measured}}$ for each major axis
3. Apply the negative correction: $\Delta H_{\text{correction}} = -\Delta H_{\text{measured}}$
4. Verify the corrected result reduces ΔE₀₀

Typical iteration: 3 rounds of measure → adjust → re-measure converges to within ΔE₀₀ < 2.0.

---

## §3 Tuning

### 3.1 Saturation Factor Sweep

Start tuning with a sweep of the global saturation factor on a representative image set (ColorChecker, outdoor landscape, portrait, low-light):

```
α sweep:  0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4
```

Score each result for:
- ColorChecker ΔE₀₀ (lower = better accuracy)
- Subjective preference rating (1–5) on a panel of ≥5 evaluators
- Skin tone naturalness (specific skin ΔE₀₀)

The optimal α balances preference (typically peaks at 1.15–1.25) vs. accuracy.

### 3.2 Luminance Saturation Curve Shape

Three parameters define the curve shape:
- **Shadow knee** (Y at which shadow reduction begins): typically Y = 50–80
- **Highlight knee** (Y at which highlight reduction begins): typically Y = 200–220
- **Peak boost** (α at midtone): typically 1.15–1.30

Adjust shadow knee first to eliminate noisy chroma in dark patches, then adjust highlight knee to prevent neon artifacts on bright objects.

### 3.3 Six-Axis Fine-Tuning Sequence

Recommended tuning order:
1. **Neutral axis** (patches 19–24): Verify no tint shift
2. **Red axis**: Align Macbeth red patch
3. **Yellow axis**: Align Macbeth yellow; check skin patch 2
4. **Green axis**: Align Macbeth green; check foliage image
5. **Blue axis**: Align Macbeth blue; check sky image
6. **Cyan/Magenta**: Fine-adjust if residual error remains

---

## §4 Artifacts

### 4.1 Oversaturation Clipping

**Description:** Highly saturated objects (red flowers, bright yellow toys) develop a blown-out, flat look where the chroma exceeds the gamut boundary and clips.

**Root cause:** After Cb/Cr multiplication, the back-converted R, G, or B value exceeds 255. Clamping at this stage creates a flat region with no texture.

**Mitigation:**
- Limit $\alpha$ to a safe maximum (≤ 1.3 for most gamuts)
- Apply gamut compression before clipping: soft-clip near the boundary rather than hard-clip
- Reduce $\alpha$ via the luminance curve for bright pixels (Y > 200)

### 4.2 Hue Shift in Skin Tones

**Description:** When global saturation is increased above 1.2 without skin protection, faces acquire an orange or reddish-orange cast.

**Root cause:** Skin tones on the Red-Yellow axis are shifted toward more saturated red by the uniform Cr boost.

**Mitigation:**
- Enable skin tone protection mask
- Reduce $\Delta H$ on the Red and Yellow axes to neutral
- Verify skin ΔE₀₀ < 2.0 in standard evaluation

### 4.3 Noise Amplification in Shadows

**Description:** Dark areas show colored speckles (chroma noise) that are invisible at $\alpha = 1.0$ but become visible at $\alpha > 1.1$.

**Root cause:** Low-light pixels have inherent Cb/Cr noise. Multiplying by $\alpha > 1$ amplifies both signal and noise.

**Mitigation:**
- Apply luminance-dependent curve: reduce α in shadows (Y < 64)
- Ensure spatial NR has already reduced chroma noise before color enhancement

### 4.4 Color Fringing at High-Contrast Edges

**Description:** Colored fringes (halo-like color artifacts) appear at the edges of high-contrast objects after hue rotation.

**Root cause:** The hue computation involves atan2, which is sensitive to noise in low-saturation pixels near edges. Hue rotation on noisy edge pixels creates a colored fringe.

**Mitigation:**
- Apply hue rotation only when local saturation $S > S_{\min}$ (e.g., $S_{\min} = 0.1$)
- Use a soft mask that gates hue operations on low-saturation pixels

---

## §5 Evaluation

### 5.1 ColorChecker ΔE₀₀

The primary accuracy metric. ΔE₀₀ (CIEDE2000) accounts for perceptual non-uniformity in CIELab and is more meaningful than ΔE₉₄ or simple RGB Euclidean distance.

**Formula (simplified):**

$$
\Delta E_{00} = \sqrt{\left(\frac{\Delta L'}{k_L S_L}\right)^2 + \left(\frac{\Delta C'}{k_C S_C}\right)^2 + \left(\frac{\Delta H'}{k_H S_H}\right)^2 + R_T \cdot \frac{\Delta C'}{k_C S_C} \cdot \frac{\Delta H'}{k_H S_H}}
$$

where $S_L, S_C, S_H$ are weighting functions and $R_T$ is the rotation term.  In practice, use `skimage.color.deltaE_ciede2000` or `colormath`.

**Targets per rendering mode:**

| Mode | Mean ΔE₀₀ | Skin ΔE₀₀ |
|------|-----------|-----------|
| Natural | < 3.0 | < 2.0 |
| Standard | < 4.0 | < 2.5 |
| Vivid | < 6.0 | < 3.0 |

### 5.2 Gamut Coverage

Measure the percentage of the sRGB gamut (or DCI-P3) that is covered by the rendered output on a standard gamut test image:

```
Gamut coverage = Area(convex hull of rendered colors in xy chromaticity)
                 ─────────────────────────────────────────────────────
                 Area(target gamut triangle in xy)
```

Target: > 95% of sRGB.  Vivid modes may push to 105% (slight gamut expansion).

### 5.3 Skin Tone ΔE₀₀

Evaluate on a dedicated skin tone test chart (e.g., the SkinTone Board or custom patches measured with a spectrophotometer). Target ΔE₀₀ < 2.0 for the full set of skin tone patches.

### 5.4 Subjective Preference Score (ACR-HR)

Use the ITU-T ACR (Absolute Category Rating) scale on a panel of ≥ 10 evaluators:

| Score | Meaning |
|-------|---------|
| 5 | Excellent |
| 4 | Good |
| 3 | Fair |
| 2 | Poor |
| 1 | Bad |

Target mean score ≥ 3.5 for the default rendering mode.

---

## §6 Code

```python
"""
ch28_color_enhancement.py
Demonstrates:
  - Global saturation adjustment in YCbCr
  - 6-axis hue rotation in HSV
  - Skin tone protection mask
  - ColorChecker ΔE00 evaluation
"""

import numpy as np
import cv2
from typing import Tuple

# ------------------------------------------------------------------ #
# §6.1  YCbCr saturation adjustment (global + luminance-dependent)   #
# ------------------------------------------------------------------ #

def adjust_saturation_ycbcr(
    img_bgr: np.ndarray,
    alpha: float = 1.2,
    luma_curve: np.ndarray | None = None,
) -> np.ndarray:
    """
    Apply global or luminance-dependent saturation boost in YCbCr.

    Parameters
    ----------
    img_bgr   : uint8 BGR image
    alpha     : global saturation multiplier (1.0 = identity)
    luma_curve: optional 256-element float array; luma_curve[Y] overrides alpha
                for that luma level (enables luminance-dependent saturation)

    Returns
    -------
    uint8 BGR image with adjusted saturation
    """
    # Convert to YCbCr (OpenCV uses offset-128 convention; range 0–255)
    ycbcr = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)  # note: OpenCV is YCrCb
    Y, Cr, Cb = cv2.split(ycbcr)

    Y_f  = Y.astype(np.float32)
    Cb_f = Cb.astype(np.float32)
    Cr_f = Cr.astype(np.float32)

    # Compute effective alpha per pixel
    if luma_curve is not None:
        # luma_curve is indexed by Y value (0–255)
        alpha_map = luma_curve[Y]    # shape = (H, W), float32
    else:
        alpha_map = np.full_like(Y_f, fill_value=alpha)

    # Chroma adjustment: shift to neutral-0 center, scale, shift back
    Cb_adj = 128.0 + alpha_map * (Cb_f - 128.0)
    Cr_adj = 128.0 + alpha_map * (Cr_f - 128.0)

    # Clamp to valid range
    Cb_adj = np.clip(Cb_adj, 0, 255).astype(np.uint8)
    Cr_adj = np.clip(Cr_adj, 0, 255).astype(np.uint8)

    ycbcr_adj = cv2.merge([Y, Cr_adj, Cb_adj])
    return cv2.cvtColor(ycbcr_adj, cv2.COLOR_YCrCb2BGR)


def build_luma_saturation_curve(
    shadow_knee: int   = 64,
    highlight_knee: int = 210,
    peak_alpha: float  = 1.25,
    shadow_alpha: float = 0.90,
    highlight_alpha: float = 0.95,
) -> np.ndarray:
    """
    Build a 256-element luminance-dependent saturation curve.

    Returns float32 array indexed by Y (0–255).
    """
    lut = np.ones(256, dtype=np.float32)
    for y in range(256):
        if y < shadow_knee:
            # Linear interpolation from shadow_alpha at Y=0 to peak_alpha at shadow_knee
            t = y / shadow_knee
            lut[y] = shadow_alpha + t * (peak_alpha - shadow_alpha)
        elif y < highlight_knee:
            # Hold at peak_alpha in midtones
            lut[y] = peak_alpha
        else:
            # Linear decrease from peak_alpha at highlight_knee to highlight_alpha at Y=255
            t = (y - highlight_knee) / (255 - highlight_knee)
            lut[y] = peak_alpha + t * (highlight_alpha - peak_alpha)
    return lut


# ------------------------------------------------------------------ #
# §6.2  6-Axis hue rotation in HSV space                             #
# ------------------------------------------------------------------ #

# Six axis centers in degrees: R, Y, G, C, B, M
AXIS_CENTERS_DEG = np.array([0.0, 60.0, 120.0, 180.0, 240.0, 300.0])
AXIS_NAMES       = ["Red", "Yellow", "Green", "Cyan", "Blue", "Magenta"]


def six_axis_hue_rotation(
    img_bgr: np.ndarray,
    delta_h: np.ndarray,       # shape (6,), degrees, rotation per axis
    delta_s: np.ndarray,       # shape (6,), saturation multiplier delta per axis
    half_width_deg: float = 30.0,
) -> np.ndarray:
    """
    Apply 6-axis independent hue rotation and saturation adjustment.

    Parameters
    ----------
    img_bgr       : uint8 BGR image
    delta_h       : hue rotation per axis [R, Y, G, C, B, M] in degrees
    delta_s       : saturation scale delta per axis (0.0 = no change)
    half_width_deg: half-width of triangular influence window per axis

    Returns
    -------
    uint8 BGR image
    """
    # Convert to float32 HSV; H in [0, 360), S in [0, 1], V in [0, 1]
    img_f32 = img_bgr.astype(np.float32) / 255.0
    hsv = cv2.cvtColor(img_f32, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[:, :, 0].copy(), hsv[:, :, 1].copy(), hsv[:, :, 2].copy()

    H_out = H.copy()
    S_out = S.copy()

    for i, center in enumerate(AXIS_CENTERS_DEG):
        dH = delta_h[i]
        dS = delta_s[i]
        if dH == 0.0 and dS == 0.0:
            continue

        # Compute angular distance (handle wrap-around at 0/360)
        diff = np.abs(H - center)
        diff = np.minimum(diff, 360.0 - diff)

        # Triangular weight function
        weight = np.clip(1.0 - diff / half_width_deg, 0.0, 1.0)

        H_out = H_out + weight * dH
        S_out = S_out * (1.0 + weight * dS)

    # Wrap hue to [0, 360)
    H_out = H_out % 360.0
    S_out = np.clip(S_out, 0.0, 1.0)

    hsv_out = np.stack([H_out, S_out, V], axis=2)
    result_f32 = cv2.cvtColor(hsv_out, cv2.COLOR_HSV2BGR)
    return np.clip(result_f32 * 255.0, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ #
# §6.3  Skin tone protection mask                                     #
# ------------------------------------------------------------------ #

def compute_skin_mask_ycbcr(
    img_bgr: np.ndarray,
    cb_center: float = 102.0,
    cr_center: float = 153.0,
    sigma_cb: float  = 25.0,
    sigma_cr: float  = 20.0,
) -> np.ndarray:
    """
    Compute a soft skin mask from a BGR image using the Cb-Cr locus.

    Returns a float32 mask in [0, 1] where 1.0 = fully in skin region.
    """
    ycbcr = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    _, Cr, Cb = cv2.split(ycbcr)

    Cb_f = Cb.astype(np.float32)
    Cr_f = Cr.astype(np.float32)

    d = np.sqrt(
        ((Cb_f - cb_center) / sigma_cb) ** 2 +
        ((Cr_f - cr_center) / sigma_cr) ** 2
    )
    mask = np.clip(1.0 - d, 0.0, 1.0)
    return mask


def saturation_with_skin_protection(
    img_bgr: np.ndarray,
    alpha_global: float   = 1.25,
    skin_protection: float = 0.4,
) -> np.ndarray:
    """
    Boost global saturation while protecting skin-tone pixels.

    skin_protection: fraction by which saturation boost is reduced on skin pixels
                     (0.0 = no protection, 1.0 = full suppression of boost on skin)
    """
    skin_mask = compute_skin_mask_ycbcr(img_bgr)  # (H, W) float32 in [0,1]

    ycbcr = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    Y, Cr, Cb = cv2.split(ycbcr)

    Cb_f = Cb.astype(np.float32)
    Cr_f = Cr.astype(np.float32)

    # Per-pixel effective alpha: reduced on skin
    alpha_map = alpha_global * (1.0 - skin_protection * skin_mask)
    alpha_map = np.maximum(alpha_map, 1.0)   # never reduce below identity on skin

    Cb_adj = np.clip(128.0 + alpha_map * (Cb_f - 128.0), 0, 255).astype(np.uint8)
    Cr_adj = np.clip(128.0 + alpha_map * (Cr_f - 128.0), 0, 255).astype(np.uint8)

    ycbcr_adj = cv2.merge([Y, Cr_adj, Cb_adj])
    return cv2.cvtColor(ycbcr_adj, cv2.COLOR_YCrCb2BGR)


# ------------------------------------------------------------------ #
# §6.4  Quick ColorChecker ΔE₀₀ evaluation                          #
# ------------------------------------------------------------------ #

def rgb_to_lab(rgb_linear: np.ndarray) -> np.ndarray:
    """Convert Nx3 linear sRGB (0–255 uint8) to CIELab via XYZ (D65)."""
    rgb = rgb_linear.astype(np.float32) / 255.0

    # Linearize sRGB (gamma decode)
    linear = np.where(rgb <= 0.04045,
                      rgb / 12.92,
                      ((rgb + 0.055) / 1.055) ** 2.4)

    # sRGB → XYZ (D65)
    M = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]], dtype=np.float32)
    xyz = linear @ M.T   # (N, 3)

    # XYZ → Lab
    xyz_n = np.array([0.95047, 1.00000, 1.08883], dtype=np.float32)
    f_xyz = xyz / xyz_n
    f = np.where(f_xyz > 0.008856,
                 f_xyz ** (1.0 / 3.0),
                 7.787 * f_xyz + 16.0 / 116.0)

    L = 116.0 * f[:, 1] - 16.0
    a = 500.0 * (f[:, 0] - f[:, 1])
    b = 200.0 * (f[:, 1] - f[:, 2])
    return np.stack([L, a, b], axis=1)


def delta_e_00_simplified(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """
    Compute ΔE₀₀ between two Nx3 CIELab arrays.
    Simplified (kL = kC = kH = 1.0).
    For production use: skimage.color.deltaE_ciede2000
    """
    L1, a1, b1 = lab1[:, 0], lab1[:, 1], lab1[:, 2]
    L2, a2, b2 = lab2[:, 0], lab2[:, 1], lab2[:, 2]

    dL = L2 - L1
    C1 = np.sqrt(a1**2 + b1**2)
    C2 = np.sqrt(a2**2 + b2**2)
    C_bar = (C1 + C2) / 2.0
    C_bar7 = C_bar ** 7
    G = 0.5 * (1.0 - np.sqrt(C_bar7 / (C_bar7 + 25.0**7)))
    a1p = a1 * (1.0 + G)
    a2p = a2 * (1.0 + G)
    C1p = np.sqrt(a1p**2 + b1**2)
    C2p = np.sqrt(a2p**2 + b2**2)
    dCp = C2p - C1p

    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0
    dhp = np.where(np.abs(h2p - h1p) <= 180, h2p - h1p,
                   np.where(h2p <= h1p, h2p - h1p + 360, h2p - h1p - 360))
    dHp = 2.0 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp / 2.0))

    L_bar = (L1 + L2) / 2.0
    SL = 1.0 + 0.015 * (L_bar - 50.0)**2 / np.sqrt(20.0 + (L_bar - 50.0)**2)
    Cp_bar = (C1p + C2p) / 2.0
    SC = 1.0 + 0.045 * Cp_bar
    SH = 1.0 + 0.015 * Cp_bar

    dE = np.sqrt((dL / SL)**2 + (dCp / SC)**2 + (dHp / SH)**2)
    return dE


# ------------------------------------------------------------------ #
# §6.5  Demo: compare natural vs vivid rendering                     #
# ------------------------------------------------------------------ #

def demo_color_enhancement(img_bgr: np.ndarray) -> dict:
    """
    Run the full color enhancement comparison pipeline.

    Returns dict with keys: 'natural', 'standard', 'vivid'
    """
    luma_curve = build_luma_saturation_curve(
        shadow_knee=64, highlight_knee=210, peak_alpha=1.25,
        shadow_alpha=0.90, highlight_alpha=0.95
    )

    results = {}

    # Natural mode: minimal enhancement
    results['natural'] = adjust_saturation_ycbcr(img_bgr, alpha=1.0)

    # Standard mode: moderate saturation + luminance curve
    results['standard'] = adjust_saturation_ycbcr(img_bgr, alpha=1.0,
                                                   luma_curve=luma_curve)

    # Vivid mode: 6-axis boost + global saturation + skin protection
    delta_h = np.array([0.0,  3.0, -5.0,  0.0, 0.0, 0.0])  # R, Y, G, C, B, M
    delta_s = np.array([0.05, 0.0,  0.10, 0.05, 0.15, 0.0])
    vivid_hue = six_axis_hue_rotation(img_bgr, delta_h, delta_s)
    results['vivid'] = saturation_with_skin_protection(
        vivid_hue, alpha_global=1.25, skin_protection=0.4
    )

    return results


if __name__ == "__main__":
    import sys
    img_path = sys.argv[1] if len(sys.argv) > 1 else "test_portrait.jpg"
    img = cv2.imread(img_path)
    if img is None:
        # Fallback: create a synthetic test image with a skin-tone patch
        img = np.zeros((256, 256, 3), dtype=np.uint8)
        img[64:192, 64:192] = [80, 120, 200]   # warm skin tone (BGR)
        img[0:64, 0:256]    = [30, 30, 220]    # red region
        img[192:256, 0:256] = [50, 150, 50]    # green region

    results = demo_color_enhancement(img)
    for mode, out in results.items():
        out_path = f"output_{mode}.jpg"
        cv2.imwrite(out_path, out)
        print(f"Saved {mode} -> {out_path}")

    print("Color enhancement demo complete.")
```

---

## References

- **Sharma, G., Wu, W., & Dalal, E. N. (2005).** The CIEDE2000 Color-Difference Formula: Implementation Notes, Supplementary Test Data, and Mathematical Observations. *Color Research & Application*, 30(1), 21–30.
- **Poynton, C. (2012).** *Digital Video and HD: Algorithms and Interfaces*, 2nd ed. Morgan Kaufmann.
- **International Color Consortium. (2022).** ICC Profile Format Specification v4.4. https://www.color.org/
- **Cheung, V., Westland, S., Connah, D., & Ripamonti, C. (2004).** A comparative study of the characterisation of colour cameras by means of neural networks and polynomial transforms. *Coloration Technology*, 120(1), 19–25.
- **OpenCV Color Conversions:** https://docs.opencv.org/4.x/de/d25/imgproc_color_conversions.html
- **X-Rite ColorChecker Reference Data:** https://www.xrite.com/service-support/color-data-software
