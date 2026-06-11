# Part 2, Chapter 24: Chromatic Aberration Correction (Lateral TCA and Axial LCA)

> **Scope:** This chapter dissects the physical origins of chromatic aberration and its correction algorithms — the geometric-mapping correction of lateral TCA, the depth-dependent characteristics of axial LCA, and joint calibration methods for lens distortion and chromatic aberration.
> **Prerequisites:** Volume 1, Chapter 2 (Optics Basics); Volume 1, Chapter 8 (Optical Aberrations and Lens Calibration)
> **Target Readers:** Algorithm engineers, optical engineers

---

## Table of Contents

1. [Chromatic Aberration Physical Model](#1-chromatic-aberration-physical-model)
2. [TCA Lateral Chromatic Aberration Calibration and Correction](#2-tca-lateral-chromatic-aberration-calibration-and-correction)
3. [LCA Axial Chromatic Aberration Software Correction](#3-lca-axial-chromatic-aberration-software-correction)
4. [Common Artifact Analysis](#4-common-artifact-analysis)
5. [Evaluation Methods](#5-evaluation-methods)
6. [Code Examples](#6-code-examples)
7. [References](#7-references)
8. [Glossary](#8-glossary)

---

## 1 Chromatic Aberration Physical Model

### 1.1 Refractive Index Dispersion and the Cauchy Formula

The root cause of Chromatic Aberration (CA) is that the Refractive Index $n$ of optical glass varies with wavelength $\lambda$, i.e., Dispersion. The classical Cauchy formula (Cauchy, 1836) describes the relationship between refractive index and wavelength:

$$
n(\lambda) = A + \frac{B}{\lambda^2} + \frac{C}{\lambda^4} + \cdots
$$

where $A, B, C$ are Cauchy coefficients determined by the glass material. For most optical glass, retaining the first two terms achieves accuracy of $\Delta n < 0.0001$ in the visible range.

The more precise Sellmeier equation (Sellmeier, 1871) is widely adopted by lens design software:

$$
n^2(\lambda) - 1 = \sum_{i=1}^{3} \frac{B_i \lambda^2}{\lambda^2 - C_i}
$$

Dispersion strength is quantified by the **Abbe Number** $V_d$:

$$
V_d = \frac{n_d - 1}{n_F - n_C}
$$

where $n_d$ (587.6 nm, helium yellow line), $n_F$ (486.1 nm, hydrogen blue line), and $n_C$ (656.3 nm, hydrogen red line) are the refractive indices at their respective wavelengths. A larger $V_d$ (e.g., crown glass $V_d > 55$) means less dispersion; a smaller $V_d$ (e.g., flint glass $V_d < 40$) means more dispersion. Lens design achieves achromatic correction by pairing positive and negative lens groups (Doublet / Triplet).

### 1.2 Geometric Model of TCA (Lateral Chromatic Aberration)

Transverse Chromatic Aberration (TCA), also called Lateral Chromatic Aberration, refers to the **lateral displacement** of the principal ray landing positions (i.e., the focusing positions) of different wavelengths on the image plane, meaning that image magnification varies with wavelength.

The geometric effect of TCA: a single object point in the scene is imaged at different lateral positions in the red (R), green (G), and blue (B) channels, causing Color Fringing at edges. The magnitude of TCA depends on:

- **Field angle**: TCA is zero on-axis (image center) and increases with field angle, most prominent at the image corners;
- **Focal length**: Short focal length (ultra-wide-angle) lenses are compact and difficult to correct for CA; typical corner TCA is 3–10 pixels;
- **Aperture**: TCA is relatively unaffected by aperture (primarily a geometric optics effect);
- **F-number**: A small F-number (large aperture) typically worsens axial chromatic aberration.

For a typical smartphone wide-angle lens (equivalent 24 mm, $F/1.8$), the R-B channel displacement can reach 3–8 pixels in corner regions (at 12 MP resolution), visibly noticeable at high-contrast edges (e.g., black-and-white checkerboard, branches against sky).

The mathematical model for TCA uses a radial polynomial to describe the scaling deviation of each channel relative to the reference channel (typically G channel):

$$
r'_{ch}(r) = r \cdot \left(1 + \alpha_1^{ch} r^2 + \alpha_2^{ch} r^4 + \alpha_3^{ch} r^6\right)
$$

where $r = \sqrt{u^2 + v^2}$ is the normalized distance from the pixel to the image center, and $\alpha_1^{ch}, \alpha_2^{ch}, \alpha_3^{ch}$ are the TCA polynomial coefficients of the R or B channel relative to the G channel.

### 1.3 Geometric Model of LCA (Axial Chromatic Aberration)

Longitudinal Chromatic Aberration (LCA), also called axial chromatic aberration, refers to different wavelengths focusing at different positions **along the optical axis** (Z-axis): blue light has a shorter focal length (focus closer to the lens) and red light has a longer focal length (focus farther from the lens).

Image manifestations of LCA:
- At the focal plane, non-reference wavelengths form a Circle of Confusion (CoC), producing a blurred color halo;
- Typical appearance: an object that is sharp in the green channel will show slight blurring and color fringing in the blue and red channels;
- LCA is present **both at the image center and edges** (unlike TCA, which is zero on-axis);
- LCA severity is aperture-dependent: a larger aperture (smaller F-number) produces a larger CoC, making LCA more pronounced.

Optical quantification of LCA: axial focal difference $\Delta f_{BG}$ between blue and green, and $\Delta f_{RG}$ between red and green. Typical smartphone lens values:

$$
\Delta f_{BG} \approx -15 \sim -30 \ \mu m, \quad \Delta f_{RG} \approx +10 \sim +20 \ \mu m
$$

The corresponding CoC diameter at the image plane (sensor pixel pitch $p_x = 1.0$–1.4 μm):

$$
d_{CoC} = \frac{D_{aperture} \cdot |\Delta f|}{f^2} \approx \frac{|\Delta f|}{f \cdot F\#}
$$

With $\Delta f = 20$ μm, $f = 5$ mm, $F/1.8$: $d_{CoC} \approx 2.2$ μm $\approx 1.6$ pixels, slightly visible in 12 MP images.

---

## 2 TCA Lateral Chromatic Aberration Calibration and Correction

### 2.1 Calibration Target and Data Acquisition

TCA calibration typically uses a checkerboard or circle grid calibration target. By precisely locating the feature point coordinates in each color channel, the positional offsets between channels are quantified.

**Calibration procedure:**
1. Under uniform diffuse illumination (integrating sphere or LED light box), capture 15–20 images of the calibration target covering different field angle positions;
2. Perform sub-pixel corner detection (`cv2.findChessboardCornersSB`) separately on the R, G, and B channels of each image;
3. Using the G channel corner coordinates as reference, compute the offsets $\Delta u_{ch}(u, v), \Delta v_{ch}(u, v)$ of the R and B channel corners;
4. Fit the offset data to a radial polynomial model (typically 2–3 terms).

**Key considerations:**
- The calibration target must have high contrast and high precision (laser printing error < 0.1 mm);
- Capture at multiple temperatures to characterize TCA changes caused by temperature (thermal expansion of the lens changes refractive index distribution);
- Some systems use LED monochromatic light sources (illuminating R, G, B separately) to directly measure the independent distortion of each channel, achieving higher accuracy.

### 2.2 Joint Distortion + TCA Calibration

TCA correction is performed after distortion correction, or jointly calibrated with distortion. The Brown–Conrady distortion model is extended to:

**Per-channel independent calibration model:**

$$
\begin{pmatrix} u_{ch} \\ v_{ch} \end{pmatrix} = (1 + k_1^{ch} r^2 + k_2^{ch} r^4 + k_3^{ch} r^6)
\begin{pmatrix} u_n \\ v_n \end{pmatrix} + \text{tangential terms}
$$

where $u_n, v_n$ are the normalized coordinates after distortion correction, $r^2 = u_n^2 + v_n^2$, and each color channel (R, G, B) has an independent set of distortion coefficients.

In engineering practice, to reduce parameter dimensionality, the TCA model typically only models the differences in the R and B channels relative to the G channel; the G channel uses the standard distortion model.

### 2.3 Bilinear Interpolation Remapping Correction

Correction is implemented using a Look-Up Table (LUT) combined with bilinear interpolation via `cv2.remap`:

1. Offline computation of the source coordinates $(u_{src}^{ch}, v_{src}^{ch})$ in each channel for each output pixel $(u, v)$:
   - G channel: apply standard distortion correction mapping;
   - R/B channels: apply extended distortion mapping including TCA;
2. Save the mappings as float32 $H \times W$ map images (Map1 for x, Map2 for y);
3. At runtime, call `cv2.remap(channel, map1, map2, cv2.INTER_LINEAR)` to resample each channel.

**Memory and performance:** Each channel's map images occupy $H \times W \times 2 \times 4$ bytes (two float32 map images); approximately 122 MB at 4K resolution. An embedded optimization uses fixed-point 16-bit map images, halving memory with < 0.1 pixel accuracy loss.

Qualcomm Spectra ISP and MediaTek Imaging ISP both provide hardware-level joint LUT correction for Lens Shading + TCA, completing both Lens Shading Correction (LSC) and TCA remapping in a single pass — saving 2–4 ms compared to software solutions (@12MP).

### 2.4 Local Adaptive TCA Correction

Since TCA varies with focal length (zoom lenses), focus distance, and temperature, fixed LUTs have residual errors. Adaptive approaches:

- **Feature-point-based online TCA estimation**: Extract high-contrast edges from multiple regions of each frame, detect the R-B channel edge position offsets, and update TCA parameters in real time;
- **Scene-based auto-calibration**: Use edges of white objects (plant edges, white wall edges) as online calibration references, updating TCA polynomial coefficients every N frames.

---

## 3 LCA Axial Chromatic Aberration Software Correction

### 3.1 Frequency Domain Characteristics of LCA

The image manifestation of LCA is that different color channels have different levels of blur, corresponding in the frequency domain to differences in each channel's MTF (Modulation Transfer Function). If the G channel is correctly focused, R and B channels — due to axial defocus — have stronger low-frequency MTF response and weaker high-frequency MTF response compared to the G channel. This means they are effectively low-pass filtered relative to G:

$$
I_{ch}(u,v) \approx I_G(u,v) * h_{ca}^{ch}(u,v)
$$

where $h_{ca}^{ch}$ is the equivalent Point Spread Function (PSF) caused by LCA, approximated as a Gaussian:

$$
h_{ca}^{ch}(r) = \frac{1}{2\pi \sigma_{ch}^2} \exp\left(-\frac{r^2}{2\sigma_{ch}^2}\right), \quad
\sigma_{ch} = \frac{d_{CoC}^{ch}}{2\sqrt{2\ln 2}}
$$

### 3.2 Inverse Filtering and Regularized Correction

Software LCA correction can be viewed as a Deconvolution problem: recovering a sharp image from blurred R/B channels. Direct Inverse Filtering severely amplifies noise and requires regularization.

**Wiener Filter:**

$$
\hat{I}_{ch}(k_x, k_y) = \frac{H^*_{ca}(k_x, k_y)}{|H_{ca}(k_x, k_y)|^2 + \text{SNR}^{-1}} \cdot I_{ch}(k_x, k_y)
$$

where $H_{ca}$ is the Fourier transform of the Gaussian PSF, and $\text{SNR}$ is the signal-to-noise ratio estimate (in low-light scenes where SNR is small, correction strength is automatically reduced to avoid noise amplification).

**Practical simplified approach — Unsharp Masking (USM) approximation:**

$$
I_{corr}^{ch} = I_{ch} + \alpha_{ch} \cdot (I_{ch} - G_\sigma * I_{ch})
$$

where $G_\sigma$ is Gaussian blur (kernel width matching the LCA CoC), and $\alpha_{ch}$ is the sharpening strength (R: 0.2–0.4, B: 0.1–0.3, G: 0). This method is computationally simple but noise-sensitive; it requires adaptive adjustment of $\alpha_{ch}$ based on noise estimation.

### 3.3 Depth-Assisted LCA Correction

Since LCA severity varies with focus distance (near-field CoC > far-field), introducing depth estimation enables local adaptive correction:

1. Estimate the depth of field (DoF) of each region from the AF (Auto-Focus) motor position;
2. Calculate the theoretical LCA CoC size for that region based on depth;
3. Adaptively adjust inverse filtering strength: at the focal point, correction is strong (CoC close to 0, no correction needed); at out-of-focus regions, correction is weaker (to avoid over-correction).

This approach is particularly effective in portrait photography: the background bokeh region is intentionally blurred, so LCA correction is not needed there — avoiding unwanted color edge enhancement in the background.

### 3.4 RAW Domain LCA Correction

Compared to RGB domain correction, performing LCA correction in the RAW domain offers advantages:

- Avoids cross-channel aliasing introduced by demosaicing; subsequent demosaic can produce better results from more accurate RAW data;
- LCA magnitude in the RAW domain (Bayer format) is generally consistent with the RGB domain, but the Bayer pattern requires separate processing of the R, Gr, Gb, and B sub-channels.

RAW domain TCA correction: Apply sub-pixel correction (bilinear interpolation + scaling) to the R and B channel pixel positions in the Bayer image; the G channel remains unchanged, achieving inter-channel alignment, followed by the standard demosaic pipeline.

---

## 4 Common Artifact Analysis

### 4.1 Over-Correction Fringing

**Appearance:** After TCA correction, the original red outer edge becomes a blue outer edge, or the color of the fringe is reversed.

**Root Cause:** TCA correction coefficient estimation error (inaccurate calibration, or actual TCA deviating from calibrated values due to focus distance or temperature), causing the correction amount to exceed the actual TCA.

**Mitigation:**
- Calibrate across the full temperature range (-10°C to 50°C), establishing a temperature-segmented LUT;
- Introduce a correction strength upper limit (Clip): limit the single remapping offset to no more than $\pm 5$ pixels;
- Implement online deviation detection: if the corrected fringe color reverses, automatically reduce correction strength.

### 4.2 Purple Fringing / Blue Fringing

**Appearance:** Under bright backgrounds (incandescent lamps, sun direction), purple or blue color halos appear at high-contrast edges (e.g., the boundary between foliage and sky) — similar in appearance to TCA fringing but with different physical causes.

**Root Cause:** Purple Fringing is mainly caused by a combination of factors:
- Near-UV/near-IR light penetrating the CFA color filters (especially the B channel); when the image is overexposed, it shifts toward purple;
- Strong lens coma and spherical aberration at large apertures, causing local light spots;
- LCA axial CoC causing blue/purple light overflow at extreme brightness differences.

**Distinguishing TCA from Purple Fringing:**
- TCA fringing: the color is a combination of pure red and blue edges, distributed regularly with increasing field angle, precisely measurable on a standard checkerboard calibration target;
- Purple Fringing: predominantly purple, mainly at edges of strongly overexposed areas, not prominent on standard calibration targets.

**Mitigation:**
- Dedicated Purple Fringing treatment: Desaturation combined with hue recognition — selectively reduce color saturation at edge regions where purple/blue saturation exceeds a threshold;
- CFA filter coating optimization: cut UV light, suppress the B channel's purple response (requires hardware cooperation from lens/sensor).

### 4.3 Color Ringing from Over-Sharpening

**Appearance:** After LCA correction (inverse filtering), Color Ringing appears at high-contrast edges — fringe stripes of opposite color appear on both sides of the edge.

**Root Cause:** The inverse filtering in LCA correction (such as USM sharpening) amplifies high-frequency components in the presence of noise; the Gibbs effect introduces ringing at edges.

**Mitigation:**
- Edge-Aware correction: moderately reduce LCA correction strength in edge regions;
- Noise-adaptive regularization: dynamically adjust the Wiener filter's $\text{SNR}$ estimate based on local noise level; weaken correction in low-SNR regions;
- Co-design LCA correction with the denoising step to avoid correcting after denoising (which would result in lost high frequencies).

### 4.4 Interaction Artifacts with Adjacent Modules

**TCA correction and LSC (Lens Shading Correction) interaction:** TCA remapping changes pixel spatial positions; in regions with large LSC gain gradients (corners), this may introduce luminance discontinuities. The correct approach is to perform TCA correction first and then apply LSC gains, or merge the TCA and LSC mappings into a single LUT (joint correction).

**TCA correction and Demosaic ordering:** It is recommended to perform TCA correction in the RAW domain before Demosaic, to avoid frequency aliasing introduced by Demosaic mutually reinforcing TCA color fringing.

---

## 5 Evaluation Methods

### 5.1 TCA Fringe Width Measurement

**Test target:** Use a high-contrast black-and-white calibration target (checkerboard or starburst chart) to measure color fringe width at various field angle positions.

**Measurement method:**
1. Extract a profile line (approximately 10 pixels wide) perpendicular to the checkerboard edge;
2. Fit the edge position (at half-maximum or maximum gradient) in the R and B channels;
3. TCA = R channel edge position $-$ B channel edge position, in pixels;
4. Measure at least 8 edges at multiple field angle positions (image center, radius 0.5, edges), and compute mean and variance.

**Typical metrics:**
- Before correction: edge TCA 3–10 pixels (ultra-wide-angle lenses);
- After correction: < 1 pixel (good system);
- Target: residual TCA < 0.5 pixels; the perceptible threshold for the human eye is approximately 1–2 pixels (depending on print/display resolution).

### 5.2 Chromatic Aberration ΔE Quantification

At edges of high-contrast black targets (e.g., black dots) on a uniform white background, measure the color fringe intensity in CIE L\*a\*b\* color space:

$$
\Delta E_{ab} = \sqrt{(\Delta L^*)^2 + (\Delta a^*)^2 + (\Delta b^*)^2}
$$

Typical ΔE values for TCA-induced color fringes:
- Uncorrected: ΔE = 5–20 (clearly visible, distinguishable by the naked eye on a 4K display);
- After correction: ΔE < 2 (generally invisible to the naked eye);
- Excellent system: ΔE < 1.

### 5.3 MTF Cross-Channel Consistency (LCA Evaluation)

LCA causes inconsistent MTF across color channels. Evaluation method:
- Compute MTF separately for R, G, B channels on a slanted edge (Slanted Edge, ISO 12233:2017);
- Compare the MTF difference across channels at key frequencies (e.g., 50% of Nyquist frequency);
- When LCA correction is effective, the MTF difference across three channels should be less than 5%.

### 5.4 Subjective Evaluation

Test scenes:
- High-contrast scenes (black-and-white line patterns, foliage against sky edges);
- Semi-backlit portraits (common Purple Fringing scenario);
- Ultra-wide-angle architecture (maximum edge TCA).

Scoring dimensions (1–5 scale):
- Color fringe visibility;
- Purple fringe / blue fringe intensity;
- Edge sharpness after correction (presence of ringing).

---

## 6 Code Examples

The following code implements TCA measurement from a checkerboard calibration target and bilinear interpolation TCA correction based on `cv2.remap`. All code runs directly.

```python
"""
Chromatic Aberration (TCA) calibration and correction demo
Dependencies: numpy>=1.20, opencv-python>=4.5, scipy>=1.7
Usage: python ch22_tca_demo.py
"""

import cv2
import numpy as np
from typing import Tuple, Dict, Optional
from scipy.optimize import curve_fit


# ──────────────────────────────────────────────
# 1. Generate synthetic test image with TCA
# ──────────────────────────────────────────────

def generate_tca_image(width: int = 800,
                        height: int = 600,
                        tca_alpha_r: float = 0.00008,
                        tca_alpha_b: float = -0.00006) -> np.ndarray:
    """
    Generate a synthetic checkerboard image with radial TCA (BGR).

    Principle:
        Apply different radial scaling to R and B channels (simulating TCA),
        while G channel remains in original position as reference.

    Parameters:
        tca_alpha_r : TCA radial coefficient for R channel (positive = outward expansion)
        tca_alpha_b : TCA radial coefficient for B channel (negative = inward contraction)

    Returns:
        img_tca : BGR uint8 checkerboard image with TCA
    """
    # Generate high-resolution checkerboard (source image, no distortion)
    tile = 50
    checker = np.zeros((height, width), dtype=np.uint8)
    for iy in range(0, height, tile):
        for ix in range(0, width, tile):
            if (iy // tile + ix // tile) % 2 == 0:
                checker[iy:iy+tile, ix:ix+tile] = 230

    # Apply radial scaling (TCA) to R and B channels
    cx, cy = width / 2.0, height / 2.0

    # Build pixel coordinate grid
    us = np.arange(width, dtype=np.float32) - cx
    vs = np.arange(height, dtype=np.float32) - cy
    uu, vv = np.meshgrid(us, vs)                    # (H, W)
    r2 = (uu**2 + vv**2) / (cx**2 + cy**2)         # normalized r^2

    def shifted_map(alpha: float) -> Tuple[np.ndarray, np.ndarray]:
        """Compute source coordinate map after TCA offset"""
        scale = 1.0 / (1.0 + alpha * r2)           # Inverse mapping scale factor
        map_x = (uu * scale + cx).astype(np.float32)
        map_y = (vv * scale + cy).astype(np.float32)
        return map_x, map_y

    map_rx, map_ry = shifted_map(tca_alpha_r)
    map_bx, map_by = shifted_map(tca_alpha_b)

    # G channel: use original image directly
    ch_g = checker.copy()
    # R channel: radial outward expansion
    ch_r = cv2.remap(checker, map_rx, map_ry, cv2.INTER_LINEAR)
    # B channel: radial inward contraction
    ch_b = cv2.remap(checker, map_bx, map_by, cv2.INTER_LINEAR)

    img_tca = cv2.merge([ch_b, ch_g, ch_r])         # BGR
    return img_tca


# ──────────────────────────────────────────────
# 2. Per-channel corner detection and TCA measurement
# ──────────────────────────────────────────────

def detect_corners_per_channel(img: np.ndarray,
                                board_size: Tuple[int, int] = (7, 7)
                                ) -> Optional[Dict[str, np.ndarray]]:
    """
    Perform checkerboard corner detection separately on R, G, B channels of a BGR image.

    Parameters:
        board_size : number of interior corners in the checkerboard (cols, rows), excluding border squares

    Returns:
        corners_dict : {'R': (N,2), 'G': (N,2), 'B': (N,2)} corner coordinates
                       Returns None if detection fails for any channel
    """
    channels = {'B': img[:, :, 0], 'G': img[:, :, 1], 'R': img[:, :, 2]}
    corners_dict = {}

    flags = (cv2.CALIB_CB_ADAPTIVE_THRESH |
             cv2.CALIB_CB_NORMALIZE_IMAGE |
             cv2.CALIB_CB_FILTER_QUADS)

    for ch_name, ch_img in channels.items():
        ret, corners = cv2.findChessboardCorners(ch_img, board_size, flags)
        if not ret:
            print(f"  [{ch_name}] Corner detection failed, check checkerboard visibility")
            return None

        # Sub-pixel refinement
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.01)
        corners_sub = cv2.cornerSubPix(ch_img, corners, (5, 5), (-1, -1), criteria)
        corners_dict[ch_name] = corners_sub.reshape(-1, 2)

    return corners_dict


def measure_tca(corners_dict: Dict[str, np.ndarray],
                img_shape: Tuple[int, int]) -> Dict[str, np.ndarray]:
    """
    Compute TCA offset vectors for R and B channels relative to G channel.

    Returns:
        tca_stats : {
            'R_G_offset': (N,2)  # R-G offset (du, dv) in pixels
            'B_G_offset': (N,2)  # B-G offset (du, dv) in pixels
            'radii': (N,)        # Normalized distance of each corner from image center
        }
    """
    H, W = img_shape
    cx, cy = W / 2.0, H / 2.0

    corners_g = corners_dict['G']
    corners_r = corners_dict['R']
    corners_b = corners_dict['B']

    rg_offset = corners_r - corners_g   # (N, 2)
    bg_offset = corners_b - corners_g

    # Normalized radius
    radii = np.sqrt(((corners_g[:, 0] - cx) / cx)**2 +
                    ((corners_g[:, 1] - cy) / cy)**2)

    return {
        'R_G_offset': rg_offset,
        'B_G_offset': bg_offset,
        'radii': radii
    }


# ──────────────────────────────────────────────
# 3. Fit TCA radial polynomial
# ──────────────────────────────────────────────

def fit_tca_polynomial(corners_g: np.ndarray,
                        offsets: np.ndarray,
                        img_shape: Tuple[int, int],
                        degree: int = 2) -> np.ndarray:
    """
    Fit polynomial model of TCA offsets as a function of normalized radius.

    Model:
        offset_radial(r) = alpha_1 * r^3 + alpha_2 * r^5  (for degree=2)
        (radial component; TCA is zero on-axis, so no constant term)

    Parameters:
        corners_g : G channel corner coordinates (N, 2)
        offsets   : channel offset vectors (N, 2), i.e., R-G or B-G
        degree    : polynomial degree

    Returns:
        coeffs : fitted coefficients [alpha_1, ..., alpha_degree]
    """
    H, W = img_shape
    cx, cy = W / 2.0, H / 2.0

    # Compute radial distance (pixels)
    dx = corners_g[:, 0] - cx
    dy = corners_g[:, 1] - cy
    r = np.sqrt(dx**2 + dy**2)

    # Compute radial offset component (toward/away from center)
    r_safe = np.where(r > 1.0, r, 1.0)
    radial_offset = (offsets[:, 0] * dx / r_safe +
                     offsets[:, 1] * dy / r_safe)   # positive = radially outward

    # Normalize r to [0, 1]
    r_norm = r / np.sqrt(cx**2 + cy**2)

    # Build design matrix (odd power terms, since TCA(0)=0)
    A = np.column_stack([r_norm**(2*i+1) for i in range(1, degree+1)])

    coeffs, _, _, _ = np.linalg.lstsq(A, radial_offset, rcond=None)
    return coeffs


# ──────────────────────────────────────────────
# 4. Build TCA correction map and apply remap
# ──────────────────────────────────────────────

def build_tca_correction_map(img_shape: Tuple[int, int],
                              tca_alpha_r: float,
                              tca_alpha_b: float
                              ) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    """
    Build OpenCV remap maps for R and B channels based on TCA radial coefficients.

    Parameters:
        tca_alpha_r : TCA coefficient for R channel (positive = correction needs inward shrink)
        tca_alpha_b : TCA coefficient for B channel (negative = correction needs outward expansion)

    Returns:
        maps_r : {'map_x': ..., 'map_y': ...}
        maps_b : {'map_x': ..., 'map_y': ...}
    """
    H, W = img_shape
    cx, cy = W / 2.0, H / 2.0

    us = np.arange(W, dtype=np.float32) - cx
    vs = np.arange(H, dtype=np.float32) - cy
    uu, vv = np.meshgrid(us, vs)
    r2_norm = (uu**2 + vv**2) / (cx**2 + cy**2)

    def make_map(alpha: float):
        """
        TCA correction inverse map: input coordinates for output coordinates (u, v)
        Correction = apply scaling opposite to original TCA direction
        """
        # Correction scaling = inverse of 1 / (1 + alpha * r^2), i.e., multiply by (1 + alpha * r^2)
        scale = 1.0 - alpha * r2_norm     # first-order approximate inverse transform
        map_x = (uu * scale + cx).astype(np.float32)
        map_y = (vv * scale + cy).astype(np.float32)
        return map_x, map_y

    map_rx, map_ry = make_map(tca_alpha_r)
    map_bx, map_by = make_map(tca_alpha_b)

    return ({'map_x': map_rx, 'map_y': map_ry},
            {'map_x': map_bx, 'map_y': map_by})


def apply_tca_correction(img: np.ndarray,
                          tca_alpha_r: float,
                          tca_alpha_b: float) -> np.ndarray:
    """
    Apply TCA correction to a BGR image (R and B channels remapped independently, G unchanged).

    Parameters:
        img          : uint8 BGR input image
        tca_alpha_r  : TCA coefficient for R channel (calibrated value, same sign convention as generate_tca_image)
        tca_alpha_b  : TCA coefficient for B channel

    Returns:
        img_corrected : uint8 BGR corrected image
    """
    H, W = img.shape[:2]
    maps_r, maps_b = build_tca_correction_map((H, W), tca_alpha_r, tca_alpha_b)

    ch_b, ch_g, ch_r = cv2.split(img)

    # R channel: apply R channel TCA correction map
    ch_r_corr = cv2.remap(ch_r, maps_r['map_x'], maps_r['map_y'],
                           interpolation=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REPLICATE)
    # B channel: apply B channel TCA correction map
    ch_b_corr = cv2.remap(ch_b, maps_b['map_x'], maps_b['map_y'],
                           interpolation=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REPLICATE)
    # G channel unchanged
    img_corrected = cv2.merge([ch_b_corr, ch_g, ch_r_corr])
    return img_corrected


# ──────────────────────────────────────────────
# 5. Edge TCA quantification utility functions
# ──────────────────────────────────────────────

def measure_fringe_width_at_edge(img: np.ndarray,
                                  row: int,
                                  col_range: Tuple[int, int],
                                  channel_pair: Tuple[str, str] = ('R', 'B')
                                  ) -> float:
    """
    Measure the edge position offset (in pixels) between two channels at a horizontal edge
    in the specified row of the image.

    Method: Within the column range specified by col_range, find the maximum gradient
    position in each channel and compute the difference between the two channel edge positions.

    Parameters:
        row         : row number for measurement
        col_range   : (col_start, col_end) column search range
        channel_pair: ('R', 'B') the channel pair to measure

    Returns:
        offset : channel A edge position - channel B edge position (pixels, positive = A is to the right)
    """
    ch_map = {'B': 0, 'G': 1, 'R': 2}
    c0, c1 = col_range

    ch_a_idx = ch_map[channel_pair[0]]
    ch_b_idx = ch_map[channel_pair[1]]

    profile_a = img[row, c0:c1, ch_a_idx].astype(np.float32)
    profile_b = img[row, c0:c1, ch_b_idx].astype(np.float32)

    # Compute first derivative (gradient)
    grad_a = np.abs(np.gradient(profile_a))
    grad_b = np.abs(np.gradient(profile_b))

    # Edge position = maximum gradient location (sub-pixel refinement via parabola interpolation)
    def subpixel_peak(grad: np.ndarray) -> float:
        pk = int(np.argmax(grad))
        if 1 <= pk <= len(grad) - 2:
            denom = 2 * grad[pk] - grad[pk-1] - grad[pk+1]
            if abs(denom) > 1e-6:
                return pk + (grad[pk-1] - grad[pk+1]) / (2 * denom)
        return float(pk)

    pos_a = subpixel_peak(grad_a)
    pos_b = subpixel_peak(grad_b)
    return pos_a - pos_b


# ──────────────────────────────────────────────
# 6. Main demo function
# ──────────────────────────────────────────────

def main():
    print("=" * 62)
    print("  Chromatic Aberration (TCA) Calibration and Correction Demo")
    print("=" * 62)

    IMG_W, IMG_H = 800, 600
    # Simulate R channel expanding outward, B channel contracting inward (typical TCA pattern)
    TRUE_ALPHA_R = 0.00008
    TRUE_ALPHA_B = -0.00006
    BOARD_SIZE = (7, 7)     # 7x7 interior corners checkerboard

    # -- 1. Generate test image with TCA --
    img_tca = generate_tca_image(IMG_W, IMG_H, TRUE_ALPHA_R, TRUE_ALPHA_B)
    print(f"\n[1] Synthetic TCA checkerboard image: {IMG_W}x{IMG_H}")
    print(f"    Ground truth TCA: R_alpha={TRUE_ALPHA_R:.5f}, B_alpha={TRUE_ALPHA_B:.5f}")

    # -- 2. Per-channel corner detection and TCA measurement --
    print("\n[2] Per-channel checkerboard corner detection ...")
    corners_dict = detect_corners_per_channel(img_tca, BOARD_SIZE)

    if corners_dict is not None:
        tca_data = measure_tca(corners_dict, (IMG_H, IMG_W))
        rg_offset = tca_data['R_G_offset']
        bg_offset = tca_data['B_G_offset']
        radii     = tca_data['radii']

        # Compute radial TCA magnitude (as a function of image radius)
        rg_radial = np.sqrt(np.sum(rg_offset**2, axis=1))
        bg_radial = np.sqrt(np.sum(bg_offset**2, axis=1))

        print(f"    Detected {len(radii)} corner pairs")
        print(f"    R-G mean offset: {np.mean(rg_radial):.3f} px, "
              f"max: {np.max(rg_radial):.3f} px")
        print(f"    B-G mean offset: {np.mean(bg_radial):.3f} px, "
              f"max: {np.max(bg_radial):.3f} px")

        # Corner region TCA (radius > 0.7)
        edge_mask = radii > 0.7
        if edge_mask.sum() > 0:
            print(f"    Corner region (r>0.7) R-G: {np.mean(rg_radial[edge_mask]):.3f} px, "
                  f"B-G: {np.mean(bg_radial[edge_mask]):.3f} px")
    else:
        print("    Corner detection failed; skipping TCA measurement (using ground truth for correction)")

    # -- 3. Apply TCA correction (using known ground truth parameters) --
    print("\n[3] Applying TCA correction (cv2.remap) ...")
    img_corrected = apply_tca_correction(img_tca, TRUE_ALPHA_R, TRUE_ALPHA_B)

    # -- 4. Evaluate correction effectiveness (R-B edge displacement) --
    print("\n[4] Correction effectiveness evaluation (edge TCA comparison):")

    # Select a checkerboard edge slightly to the right of center (mid-field region)
    test_row = IMG_H // 2
    test_col_range = (IMG_W // 2 + 50, IMG_W // 2 + 150)

    offset_before = measure_fringe_width_at_edge(
        img_tca, test_row, test_col_range, ('R', 'B'))
    offset_after  = measure_fringe_width_at_edge(
        img_corrected, test_row, test_col_range, ('R', 'B'))

    print(f"    Measurement position: row={test_row}, col_range={test_col_range}")
    print(f"    R-B edge offset before correction: {offset_before:.3f} px")
    print(f"    R-B edge offset after correction:  {offset_after:.3f} px")
    print(f"    TCA suppression rate: {(1 - abs(offset_after) / max(abs(offset_before), 1e-6)) * 100:.1f}%")

    # -- 5. Image visualization (optional) --
    print("\n[5] Visual comparison (optional, uncomment to save):")
    print("    # cv2.imwrite('tca_before.png', img_tca)")
    print("    # cv2.imwrite('tca_after.png', img_corrected)")
    # cv2.imwrite("tca_before.png", img_tca)
    # cv2.imwrite("tca_after.png", img_corrected)

    # -- 6. Full-image multi-position TCA statistics --
    print("\n[6] Full-image multi-position TCA statistics:")
    offsets_before = []
    offsets_after  = []
    # Sample at multiple field positions
    test_positions = [
        (IMG_H // 4,     (50, 150)),                          # Top
        (IMG_H // 2,     (50, 150)),                          # Center-left
        (IMG_H // 2,     (IMG_W-150, IMG_W-50)),              # Center-right
        (3 * IMG_H // 4, (50, 150)),                          # Bottom
        (IMG_H // 2,     (IMG_W // 2, IMG_W // 2 + 100)),     # Center
    ]
    for row_t, col_range_t in test_positions:
        ob = measure_fringe_width_at_edge(img_tca, row_t, col_range_t)
        oa = measure_fringe_width_at_edge(img_corrected, row_t, col_range_t)
        offsets_before.append(abs(ob))
        offsets_after.append(abs(oa))

    print(f"    Mean fringe width before correction: {np.mean(offsets_before):.3f} px")
    print(f"    Mean fringe width after correction:  {np.mean(offsets_after):.3f} px")
    print(f"    Overall TCA suppression rate: {(1 - np.mean(offsets_after) / max(np.mean(offsets_before), 1e-6)) * 100:.1f}%")


if __name__ == "__main__":
    main()
```

**Parameter Tuning and Extension Notes:**

| Parameter | Recommended Value | Notes |
|---|---|---|
| TCA polynomial degree | 2–3 | Ultra-wide-angle lenses typically need 3 terms; standard lenses 2 terms suffice |
| Number of calibration images | 15–25 | Cover full field of view including corners; avoid capturing only the center |
| Sub-pixel corner refinement window | (5,5)–(9,9) | Larger = higher accuracy but more computation |
| remap interpolation method | `INTER_LINEAR` | Use `INTER_LANCZOS4` for high accuracy requirements; approx. 4x the computation |
| Map precision | float32 | Embedded can use int16 (precision ~1/64 pixel, saves 50% memory) |

---

## 7 References

1. Cauchy, A. L. (1836). *Sur la dispersion de la lumière*. Bulletin des Sciences Mathématiques, 14, 6–10. (Cauchy dispersion formula).
2. Sellmeier, W. (1871). *Zur Erklärung der abnormen Farbenfolge im Spectrum einiger Substanzen*. Annalen der Physik und Chemie, 219(6), 272–282.
3. Zhang, Z. (2000). *A Flexible New Technique for Camera Calibration*. **IEEE TPAMI**, 22(11), 1330–1334.
4. Brown, D. C. (1966). *Decentering Distortion of Lenses*. **Photogrammetric Engineering**, 32(3), 444–462.
5. Malvar, H. S., He, L., & Cutler, R. (2004). *High-Quality Linear Interpolation for Demosaicing of Bayer-Patterned Color Images*. **ICASSP 2004**.
6. Heikkila, J., & Silven, O. (1997). *A Four-step Camera Calibration Procedure with Implicit Image Correction*. **CVPR 1997**, 1106–1112.
7. He, K., Sun, J., & Tang, X. (2013). *Guided Image Filtering*. **IEEE TPAMI**, 35(6), 1397–1409.
8. ISO 12233:2017. *Photography — Electronic still picture imaging — Resolution and spatial frequency responses*. International Organization for Standardization.
9. Jähne, B., & Haußecker, H. (Eds.). (2000). *Computer Vision and Applications*. Academic Press. (Chapter on lens aberrations).
10. Conrady, A. E. (1919). *Decentred Lens-Systems*. **Monthly Notices of the Royal Astronomical Society**, 79(5), 384–390. (Brown–Conrady distortion model).

---

## 8 Glossary

| Term | Full Name | Description |
|---|---|---|
| Chromatic Aberration | Chromatic Aberration (CA) | Different wavelengths image at different positions due to optical system dispersion |
| TCA | Transverse Chromatic Aberration | Lateral chromatic aberration; different wavelengths have lateral (X-Y) positional offsets on the image plane |
| LCA | Longitudinal Chromatic Aberration | Axial chromatic aberration; different wavelengths focus at different positions along the optical axis (Z) |
| Abbe Number | Abbe Number ($V_d$) | Quantitative indicator of glass dispersion; larger value = less dispersion |
| Dispersion | Dispersion | Physical phenomenon of refractive index varying with wavelength |
| CoC | Circle of Confusion | Defocus spread function equivalent size |
| PSF | Point Spread Function | Describes the optical system's imaging response to a point light source |
| MTF | Modulation Transfer Function | System spatial resolution response in the frequency domain |
| Distortion | Distortion | Radial/tangential geometric deformation; independent from CA but often jointly calibrated |
| Remap | Remap | Geometric correction operation that resamples image pixels via inverse mapping interpolation |
| LSC | Lens Shading Correction | Compensates for luminance falloff at lens corners |
| Purple Fringing | — | Purple/blue halo at bright edges; mixed causes (TCA + saturation + spherical aberration) |
| Wiener Filter | — | Wiener filter; optimal frequency-domain inverse filter balancing noise suppression |
| USM | Unsharp Masking | Commonly used for approximate LCA correction via frequency-domain enhancement |
| DoF | Depth of Field | The range in front and behind the focal plane that appears sharp in the image |
| CFA | Color Filter Array | Color filter array on the sensor (e.g., Bayer pattern) |
| Demosaic | — | Reconstructs full-color RGB image from single-channel Bayer RAW data |
