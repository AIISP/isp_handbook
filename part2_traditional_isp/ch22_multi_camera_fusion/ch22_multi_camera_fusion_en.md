# Vol. 2 Ch. 22: Multi-Camera Fusion and Stitching

> **Scope:** This chapter covers the core algorithms for multi-camera image fusion — disparity estimation, feature-point alignment, exposure consistency, multi-spectral fusion, and seam elimination. It forms the foundation for computational zoom and night-mode multi-frame fusion in multi-camera systems.
> **Prerequisites:** Vol. 1 Ch. 3 (Sensor Physics); Vol. 2 Ch. 1 (BLC); Vol. 2 Ch. 11 (HDR Multi-Frame Merging)
> **Target Readers:** Algorithm engineers, camera system engineers

---

## Table of Contents

1. [Multi-Camera System Geometry and Calibration Equations](#1-multi-camera-system-geometry-and-calibration-equations)
2. [Disparity Estimation Algorithms](#2-disparity-estimation-algorithms)
3. [Exposure Consistency and Color Alignment](#3-exposure-consistency-and-color-alignment)
4. [Common Artifact Analysis](#4-common-artifact-analysis)
5. [Evaluation Methods](#5-evaluation-methods)
6. [Code Examples](#6-code-examples)
7. [References](#7-references)
8. [Glossary](#8-glossary)

---

## 1 Multi-Camera System Geometry and Calibration Equations

### 1.1 Multi-Camera System Architecture Overview

Modern smartphones typically integrate 2–4 cameras. Common configurations include: a main camera (Wide, equivalent focal length 24–28 mm), an ultra-wide-angle camera (Ultra-Wide, equivalent 12–16 mm), a telephoto camera (Tele, equivalent 50–100 mm), and a periscope telephoto camera (Periscope Tele, equivalent 100–300 mm). These cameras differ significantly in sensor size, pixel pitch, aperture, and other parameters. Before fusion, three categories of problems must be addressed: Geometric Alignment, Photometric Consistency, and Temporal Synchronization.

Primary application scenarios for Multi-Camera Fusion (多摄融合, MCF):
- **Computational Zoom**: Smooth interpolation between the focal lengths of the main camera and the telephoto camera, filling the optical magnification gap;
- **Night Mode Multi-Camera Fusion**: Using different exposure combinations to suppress noise and extend dynamic range;
- **Depth-Assisted Bokeh**: Generating a depth map from dual-camera disparity to drive defocus rendering.

### 1.2 Camera Intrinsic Model

The Intrinsic Matrix $\mathbf{K}$ of a single camera projects a 3D point $\mathbf{X}_c = (X, Y, Z)^\top$ in the camera coordinate system to image pixel coordinates $(u, v)$:

$$
\begin{pmatrix} u \\ v \\ 1 \end{pmatrix} = \mathbf{K} \begin{pmatrix} X/Z \\ Y/Z \\ 1 \end{pmatrix}, \quad
\mathbf{K} = \begin{pmatrix} f_x & s & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{pmatrix}
$$

where $f_x, f_y$ are the focal lengths in pixel units, $(c_x, c_y)$ is the principal point, and $s$ is the image plane skew parameter (usually 0).

Lens Distortion is modeled using the Brown–Conrady model, which corrects normalized camera coordinates $(x, y)$ to:

$$
x_d = x(1 + k_1 r^2 + k_2 r^4 + k_3 r^6) + 2p_1 xy + p_2(r^2 + 2x^2)
$$

where $r^2 = x^2 + y^2$, $k_1, k_2, k_3$ are radial distortion coefficients, and $p_1, p_2$ are tangential distortion coefficients. Ultra-wide-angle lenses typically require more radial terms ($k_4, k_5, k_6$) or use a fisheye equidistant projection model.

### 1.3 Extrinsic Model and Relative Pose

The relative geometric relationship between two cameras is described by Extrinsic Parameters: a rotation matrix $\mathbf{R} \in SO(3)$ and a translation vector $\mathbf{t} \in \mathbb{R}^3$, which transform a point in camera 1's coordinate system to camera 0's coordinate system:

$$
\mathbf{X}_{c_0} = \mathbf{R} \mathbf{X}_{c_1} + \mathbf{t}
$$

Extrinsic calibration is typically performed by capturing multiple-pose images of a checkerboard target, solved using the method of Zhang (IEEE TPAMI 2000). Accuracy requirements: rotation angle error < 0.05°, translation error < 0.1 mm.

### 1.4 Essential Matrix and Fundamental Matrix

The **Essential Matrix** $\mathbf{E}$ describes the epipolar geometric constraint between two calibrated cameras:

$$
\mathbf{E} = [\mathbf{t}]_\times \mathbf{R}
$$

where $[\mathbf{t}]_\times$ is the skew-symmetric matrix of $\mathbf{t}$. Corresponding points $\mathbf{x}_1, \mathbf{x}_2$ in normalized coordinates satisfy:

$$
\mathbf{x}_2^\top \mathbf{E} \mathbf{x}_1 = 0
$$

The **Fundamental Matrix** $\mathbf{F}$ operates directly on pixel coordinates, incorporating the intrinsic parameters into the constraint:

$$
\mathbf{F} = \mathbf{K}_2^{-\top} \mathbf{E} \mathbf{K}_1^{-1}
$$

In engineering practice, the 8-point algorithm (Longuet-Higgins, Nature 1981) combined with RANSAC (Fischler & Bolles, CACM 1981) is commonly used to robustly estimate $\mathbf{F}$ from feature point matches. The 5-point algorithm (Nistér, IEEE TPAMI 2004) is used when higher accuracy is required.

### 1.5 Disparity Equation and Depth Recovery

In a standard stereo system, the horizontal distance between the optical centers of the two cameras is called the Baseline $B$, the focal length is $f$, and the horizontal offset of a corresponding point in the left and right images at world depth $Z$ is the Disparity $d$:

$$
d = \frac{f \cdot B}{Z} \quad \Longrightarrow \quad Z = \frac{f \cdot B}{d}
$$

The relationship between depth error and disparity error is:

$$
\Delta Z = \frac{f \cdot B}{d^2} \Delta d = \frac{Z^2}{f \cdot B} \Delta d
$$

Typical smartphone dual-camera baseline $B = 5$–20 mm. At close range ($Z < 0.5$ m), depth estimation accuracy is limited, making it suitable primarily for generating auxiliary depth maps rather than precise ranging. A telephoto secondary camera ($B \approx 20$ mm) has better depth resolution at mid-to-far range (1–5 m).

### 1.6 Stereo Rectification

To simplify disparity search to a one-dimensional horizontal scan, the stereo images must undergo Epipolar Rectification. After rectification, the corresponding epipolar lines of both images are coplanar and horizontally aligned. The Bouguet algorithm (implemented in OpenCV `cv2.stereoRectify`) generates rectification maps $\mathbf{H}_1, \mathbf{H}_2$ such that the epipolar row alignment error is < 0.5 pixels. Image distortion introduced by rectification is handled using bilinear interpolation or Lanczos resampling to reduce aliasing.

---

## 2 Disparity Estimation Algorithms

### 2.1 Block Matching

Block Matching (BM) is the earliest and still widely used local disparity estimation method. For each pixel $(u, v)$ in the reference image, it searches within the range $[d_{\min}, d_{\max}]$ on the same row of the target image to find the disparity candidate with the minimum matching cost.

Common matching cost functions:

| Cost Function | Formula | Characteristics |
|---|---|---|
| SAD (Sum of Absolute Differences) | $\sum_{(i,j)\in W} \|I_L(u+i,v+j) - I_R(u+i-d,v+j)\|$ | Fast computation, sensitive to illumination changes |
| SSD (Sum of Squared Differences) | $\sum (I_L - I_R)^2$ | More sensitive to noise |
| NCC (Normalized Cross-Correlation) | $\frac{\sum(I_L-\bar{I}_L)(I_R-\bar{I}_R)}{\sigma_{I_L}\sigma_{I_R}}$ | Robust to mean shift |
| Census Transform | Hamming distance of local binary encoding | Robust to noise and uneven illumination |

The Census Transform (Zabih & Woodfill, ECCV 1994) generates a binary string by comparing each pixel in an $N\times N$ neighborhood against the center pixel, with the matching cost being the Hamming Distance. This is widely used on embedded platforms. Weaknesses of local block matching: poor accuracy in low-texture regions (sky, white walls), occluded regions, and at disparity discontinuity edges.

### 2.2 Semi-Global Matching (SGM)

SGM was proposed by Hirschmüller (IEEE TPAMI 2008) and introduces global smoothness constraints while remaining computationally tractable, significantly improving disparity quality in occluded and low-texture regions.

SGM independently performs one-dimensional dynamic programming in multiple directions (typically 8 or 16), then sums the cost volumes from all directions:

$$
S(p, d) = \sum_{r} L_r(p, d)
$$

The path cost recursion along direction $r$ is:

$$
L_r(p, d) = C(p, d) + \min\begin{cases}
L_r(p-r, d) \\
L_r(p-r, d\pm 1) + P_1 \\
\min_k L_r(p-r, k) + P_2
\end{cases} - \min_k L_r(p-r, k)
$$

$P_1$ controls small disparity changes (±1), and $P_2$ controls large disparity jumps. These are usually adaptively adjusted: $P_2$ is reduced at gradient-strong edges to allow depth discontinuities, and increased in flat regions to enforce smoothness.

**Platform Implementation:** Qualcomm Snapdragon 8 Gen series accelerates SGM through the Spectra ISP hardware unit; MediaTek Dimensity series supports real-time SGM disparity maps through the HW Depth Engine. On mobile, hardware SGM can complete disparity estimation over a 64-disparity range at full resolution (4000×3000) in < 30 ms.

### 2.3 Deep Learning Disparity Estimation: RAFT-Stereo

RAFT-Stereo (Lipson et al., 3DV 2021) extends the optical flow estimation framework RAFT to the stereo disparity task, achieving a D1-all score of 1.96% on the KITTI 2015 leaderboard (at time of publication).

**Key Design:**
- **Correlation Volume**: Extracts left and right image features $f_L, f_R \in \mathbb{R}^{H/8 \times W/8 \times C}$, constructs a 4D correlation volume with 4-level pooling for multi-scale matching cost queries;
- **Iterative Update**: Uses a ConvGRU (Convolutional Gated Recurrent Unit) to iteratively refine the disparity estimate, querying the correlation volume for contextual information at each iteration;
- **Convex Upsampling**: Recovers the $1/8$-resolution disparity map to full resolution, more accurate at edges than bilinear interpolation.

Mobile deployment strategies: (1) Reduce feature resolution to $1/4$; (2) Reduce GRU iterations (12→4); (3) Replace ResNet encoder with MobileNetV3 backbone; (4) INT8 quantized inference.

### 2.4 Disparity Post-Processing

1. **Left-Right Consistency Check**: Compute disparity with both left and right images as reference; if the difference exceeds 1 pixel, mark as an invalid pixel (low confidence);
2. **Sub-pixel Refinement**: Fit a parabola to the disparity cost curve to achieve 0.25-pixel accuracy;
3. **Hole Filling**: Fill invalid regions using the median disparity of surrounding background pixels;
4. **Guided Filter (He et al., IEEE TPAMI 2013)**: Use the reference image as a guide to perform edge-preserving smoothing of the disparity map, with radius $r=5$–20 and regularization coefficient $\epsilon=0.01$–0.1.

---

## 3 Exposure Consistency and Color Alignment

### 3.1 Multi-Camera Gain Alignment

Due to differences in sensor type, lens transmittance, aperture, etc., different cameras exhibit systematic offsets in their raw digital output values (Digital Number, DN) under the same scene brightness, requiring Radiometric Calibration.

**Exposure normalization factor:**

$$
k = \frac{t_0 \cdot g_0}{t_1 \cdot g_1}
$$

where $t_0, g_0$ are the main camera's exposure time and gain, and $t_1, g_1$ are the secondary camera's parameters. In practice, the calibration captures an 18% gray card or Macbeth ColorChecker, compares the average RAW DN values of the same color patch across the two cameras, and fits a piecewise linear Per-Channel Gain function via least squares to compensate for lens vignetting and CFA response differences.

### 3.2 CCM Cross-Camera Color Consistency

Due to differences in lens transmittance spectrum and Color Filter Array (CFA) response, each camera has a different color space. Direct fusion produces color mismatch artifacts.

Let the main camera's Color Correction Matrix (CCM) be $\mathbf{M}_0$ and the secondary camera's CCM be $\mathbf{M}_1$. The alignment transform from the secondary camera to the main camera reference space is:

$$
\mathbf{I}_{aligned} = \mathbf{M}_0 \mathbf{M}_1^{-1} \mathbf{I}_{cam1}
$$

Complete transform chain (including white balance gains $wb$):

$$
\mathbf{I}_{ref} = \mathbf{M}_0 \cdot \text{diag}(wb_0) \cdot \mathbf{I}_{cam0}
$$
$$
\mathbf{I}_{aligned} = \mathbf{M}_0 \cdot \text{diag}(wb_0) \cdot \mathbf{M}_0 \mathbf{M}_1^{-1} \cdot \text{diag}(wb_1)^{-1} \cdot \mathbf{I}_{cam1}
$$

This matrix can be pre-computed offline; the embedded implementation only requires a single 3×3 matrix multiplication. Forcing the main and secondary cameras to use the same AWB gains (using the main camera as reference) can further simplify the process, typically achieving color error ΔE < 1.5 CIE76.

### 3.3 HDR Wide Dynamic Range Dual-Camera Fusion

**Spatial HDR**: Main camera at normal exposure + secondary camera at short exposure (typically 2–4 EV difference), fused after disparity alignment. This simultaneously covers highlights and shadow details, and is superior to single-camera temporal HDR (no motion ghosting risk).

Fusion weights following the hat-function from Debevec & Malik (SIGGRAPH 1997):

$$
W(z) = \begin{cases}
z - z_{\min} & z \leq \frac{z_{\min}+z_{\max}}{2} \\
z_{\max} - z & z > \frac{z_{\min}+z_{\max}}{2}
\end{cases}
$$

Re-projecting the secondary camera into the main camera coordinate system (using disparity map $d(u,v)$):

$$
u' = u - d(u,v), \quad v' = v
$$

(Rectified coordinates; disparity is horizontal only.) For non-rectified systems, a complete reprojection equation is required.

### 3.4 Laplacian Pyramid Fusion

Aligned multi-camera images are fused using Laplacian Pyramid Fusion (Burt & Adelson, ACM TOG 1983) to eliminate seams caused by brightness differences:

1. Build a Laplacian pyramid $\{L_k^{(i)}\}$ for each input image;
2. Build a Gaussian pyramid $\{G_k^{W}\}$ for the weight mask;
3. Fuse level by level: $\hat{L}_k = \sum_i G_k^{W(i)} \cdot L_k^{(i)}$;
4. Reconstruct the fused image level by level, starting from the lowest-frequency layer (the Gaussian residual).

In practice, 3–5 pyramid levels are used. This significantly eliminates seams caused by low-frequency brightness differences while preserving high-frequency texture detail.

---

## 4 Common Artifact Analysis

### 4.1 Disparity Ghosting

**Appearance:** Moving objects appear as double images (ghosts) in the fused image, or near-field objects show double contours at their edges.

**Root Cause:** Disparity estimation errors cause inaccurate reprojection of the secondary camera, so the corresponding regions of the main and secondary cameras come from different scene positions.

**Mitigation:**
- Introduce a Confidence Map: use secondary camera data only in regions with reliable disparity; fall back to main-camera-only output in low-confidence regions (occlusions, low texture);
- Motion Segmentation: reduce or disable fusion weights in moving regions;
- Temporal consistency filtering: filter unreliable disparities using disparity consistency across adjacent frames.

### 4.2 Seam Visibility

**Appearance:** In multi-camera stitched images, abrupt lines of brightness or color change appear in the field-of-view (FOV) transition zone.

**Root Cause:** Exposure inconsistency (synchronization issues with exposure time and AGC gain), residual color space alignment error, or geometric misalignment causing structural texture offsets.

**Mitigation:**
- Force hardware-synchronized exposure capture for main and secondary cameras (Hardware Sync Capture);
- Design a gradual weight transition zone (Blend Zone) in the switching region; recommended width is 2–5% of image resolution;
- Gradient-guided optimal seam finding (Seam Carving), selecting seams along low-gradient paths (Kwatra et al., SIGGRAPH 2003).

### 4.3 Color Inconsistency

**Appearance:** The same object appears noticeably different in color between the main and secondary camera regions (shifted blue or yellow).

**Root Cause:** CCM calibration error, white balance deviation (main and secondary cameras' AWB algorithms produce different outputs), or lens coating differences causing different color temperature responses.

**Mitigation:**
- Perform global Histogram Matching before tone mapping;
- Force main and secondary cameras to use the same AWB gains (using the main camera as reference);
- Regular online re-calibration, adaptively adjusting cross-camera gains using gray regions in the scene.

### 4.4 Geometric Misalignment

**Appearance:** Structural offsets (double edges) appear in the stitching region, more obvious in close-range or large-disparity scenes.

**Root Cause:** Insufficient extrinsic calibration accuracy (assembly tolerances cause actual $\mathbf{R}, \mathbf{t}$ to deviate from calibrated values), thermal deformation, or Rolling Shutter effects causing differences in exposure timing.

**Mitigation:**
- Add an Online Self-Calibration mechanism in addition to factory calibration;
- Global Homography fine-tuning compensation, effective when deviation is < 5 pixels;
- Use Global Shutter sensors or hardware-synchronized triggering to reduce Rolling Shutter differences.

---

## 5 Evaluation Methods

### 5.1 Geometric Alignment Objective Metrics

- **EPE (End-Point Error)**: Mean absolute error between the predicted disparity map and the LiDAR or structured-light ground truth, in pixels;
- **D1-all**: Percentage of pixels where disparity error > 3 pixels and relative error > 5% (KITTI 2015 standard);
- **Bad-X%**: Percentage of pixels with error exceeding X pixels (commonly Bad-1, Bad-2, Bad-4).

### 5.2 Fused Image Quality Objective Metrics

- **SSIM (Structural Similarity Index)**: Measures structural, luminance, and contrast consistency between the fused image and the reference image (Wang et al., IEEE TIP 2004); range [0, 1], higher is better;
- **PSNR (Peak Signal-to-Noise Ratio)**: Measures overall signal fidelity, in dB;
- **ΔE (CIEDE2000)**: Quantifies color deviation of corresponding color patches between the main and secondary cameras in CIE L\*a\*b\* color space; ΔE < 2 is the perceptually acceptable threshold.

### 5.3 Subjective Evaluation Protocol

Subjective evaluation is recommended using Double-Blind A/B Testing:

| Evaluation Dimension | Scoring Criteria |
|---|---|
| Seam naturalness | 1–5 (5 = completely invisible) |
| Color consistency | 1–5 (5 = no visible color difference) |
| Motion ghosting | 1–5 (5 = no ghosting) |
| Overall fusion quality | 1–5 |

**Test Scene Coverage:** 18% gray card (color consistency), checkerboard (geometric accuracy), moving hand (ghosting), window backlighting (HDR fusion), night scene (low SNR), distant architecture (seam).

---

## 6 Code Examples

The following code demonstrates stereo disparity computation based on OpenCV, comparing StereoBM (block matching) and StereoSGBM (semi-global matching), and includes photometric alignment utility functions. The code runs directly and depends on `opencv-python` and `numpy`.

```python
"""
Multi-camera disparity estimation comparison: StereoBM vs StereoSGBM
Requirements: opencv-python>=4.5, numpy>=1.20
Usage: python ch20_stereo_demo.py
"""

import cv2
import numpy as np
import time
from typing import Tuple


# ──────────────────────────────────────────────
# 1. Synthetic stereo test image generation
# ──────────────────────────────────────────────

def generate_synthetic_stereo(width: int = 640,
                               height: int = 480,
                               true_disparity: int = 16) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate a synthetic stereo image pair for algorithm validation without real data.

    Method:
        - Left image: random rectangular texture scene + Gaussian noise
        - Right image: left image shifted horizontally by true_disparity pixels

    Returns:
        left_gray, right_gray: uint8 grayscale images
    """
    rng = np.random.default_rng(42)

    # Generate textured scene (random rectangles)
    scene = np.zeros((height, width), dtype=np.uint8)
    for _ in range(80):
        x1 = rng.integers(0, width - 40)
        y1 = rng.integers(0, height - 40)
        x2 = min(x1 + rng.integers(15, 70), width)
        y2 = min(y1 + rng.integers(15, 70), height)
        val = rng.integers(40, 220)
        scene[y1:y2, x1:x2] = val

    # Overlay gradient background (add low-frequency texture)
    grad_x = np.linspace(30, 80, width, dtype=np.float32)
    grad_y = np.linspace(20, 60, height, dtype=np.float32)
    background = np.outer(grad_y, np.ones(width)) + np.outer(np.ones(height), grad_x)
    scene = np.clip(scene.astype(np.float32) + background * 0.3, 0, 255).astype(np.uint8)

    # Add Gaussian noise to left image
    noise_l = rng.normal(0, 4, scene.shape)
    left_gray = np.clip(scene.astype(np.float32) + noise_l, 0, 255).astype(np.uint8)

    # Right image = left image shifted horizontally (simulates d=true_disparity pixels disparity)
    right_gray = np.zeros_like(left_gray)
    right_gray[:, :width - true_disparity] = left_gray[:, true_disparity:]
    noise_r = rng.normal(0, 3, scene.shape)
    right_gray = np.clip(right_gray.astype(np.float32) + noise_r, 0, 255).astype(np.uint8)

    return left_gray, right_gray


# ──────────────────────────────────────────────
# 2. StereoBM block-matching disparity estimation
# ──────────────────────────────────────────────

def compute_disparity_bm(left: np.ndarray,
                          right: np.ndarray,
                          num_disparities: int = 64,
                          block_size: int = 15) -> Tuple[np.ndarray, float]:
    """
    Compute disparity map using StereoBM (block matching).

    Parameters:
        left, right      : uint8 grayscale input images, must have the same size
        num_disparities  : disparity search range, must be a positive integer multiple of 16
        block_size       : matching window size, must be odd, recommended 9–21

    Returns:
        disp_norm  : uint8 normalized disparity map (0–255, for visualization)
        elapsed_ms : algorithm runtime (milliseconds)
    """
    assert num_disparities % 16 == 0, "numDisparities must be a multiple of 16"
    assert block_size % 2 == 1 and block_size >= 5, "blockSize must be odd and >= 5"

    stereo = cv2.StereoBM.create(numDisparities=num_disparities,
                                  blockSize=block_size)
    # Pre-filter (normalize contrast)
    stereo.setPreFilterType(cv2.STEREO_BM_PREFILTER_XSOBEL)
    stereo.setPreFilterCap(31)
    stereo.setPreFilterSize(9)
    # Post-processing
    stereo.setUniquenessRatio(15)     # Uniqueness constraint, filters ambiguous matches
    stereo.setSpeckleWindowSize(100)  # Connected-component noise removal window
    stereo.setSpeckleRange(32)        # Allowed disparity variation range

    t0 = time.perf_counter()
    raw = stereo.compute(left, right)   # Output is 16x fixed-point (int16)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    disp_float = raw.astype(np.float32) / 16.0
    disp_float[disp_float < 0] = 0     # Set invalid disparities to 0
    disp_norm = cv2.normalize(disp_float, None, 0, 255,
                               cv2.NORM_MINMAX).astype(np.uint8)
    return disp_norm, elapsed_ms


# ──────────────────────────────────────────────
# 3. StereoSGBM semi-global matching disparity estimation
# ──────────────────────────────────────────────

def compute_disparity_sgbm(left: np.ndarray,
                            right: np.ndarray,
                            num_disparities: int = 64,
                            block_size: int = 5,
                            use_3way: bool = True) -> Tuple[np.ndarray, float]:
    """
    Compute disparity map using StereoSGBM (semi-global block matching).

    Parameters:
        block_size  : recommended 3–11 (odd); smaller = higher edge accuracy but noisier
        use_3way    : True uses pseudo-global 3WAY mode (higher accuracy),
                      False uses standard 8-direction SGBM (faster)

    Tuning guidance:
        P1 = 8 * cn * bs^2  (small disparity penalty)
        P2 = 32 * cn * bs^2 (large disparity penalty)
        P2 / P1 should be kept at 4–6 to balance smoothness and edge preservation
    """
    cn = 1  # grayscale image channel count
    bs = block_size
    P1 = 8 * cn * bs * bs
    P2 = 32 * cn * bs * bs
    mode = (cv2.StereoSGBM_MODE_SGBM_3WAY if use_3way
            else cv2.StereoSGBM_MODE_SGBM)

    stereo = cv2.StereoSGBM.create(
        minDisparity=0,
        numDisparities=num_disparities,
        blockSize=bs,
        P1=P1,
        P2=P2,
        disp12MaxDiff=1,          # Left-right consistency check max tolerance (pixels)
        uniquenessRatio=10,        # Uniqueness constraint
        speckleWindowSize=100,
        speckleRange=32,
        preFilterCap=63,
        mode=mode
    )

    t0 = time.perf_counter()
    raw = stereo.compute(left, right)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    disp_float = raw.astype(np.float32) / 16.0
    disp_float[disp_float < 0] = 0
    disp_norm = cv2.normalize(disp_float, None, 0, 255,
                               cv2.NORM_MINMAX).astype(np.uint8)
    return disp_norm, elapsed_ms


# ──────────────────────────────────────────────
# 4. Evaluation metrics: EPE and Bad-X%
# ──────────────────────────────────────────────

def compute_epe(disp_pred_norm: np.ndarray,
                disp_gt: np.ndarray,
                disp_range: int,
                valid_mask: np.ndarray = None) -> float:
    """
    Compute End-Point Error (mean absolute disparity error).

    Parameters:
        disp_pred_norm : uint8 normalized disparity map [0, 255] (returned by compute_disparity_*)
        disp_gt        : float32 ground truth disparity map (actual pixel values)
        disp_range     : disparity range used for normalization
        valid_mask     : valid pixel mask (True = valid)
    """
    disp_pred = disp_pred_norm.astype(np.float32) / 255.0 * disp_range
    err = np.abs(disp_pred - disp_gt.astype(np.float32))
    if valid_mask is not None:
        err = err[valid_mask]
    return float(np.mean(err))


def compute_bad_pct(disp_pred_norm: np.ndarray,
                    disp_gt: np.ndarray,
                    disp_range: int,
                    threshold: float = 3.0,
                    valid_mask: np.ndarray = None) -> float:
    """
    Compute Bad-X% metric (percentage of pixels with error exceeding threshold pixels).
    """
    disp_pred = disp_pred_norm.astype(np.float32) / 255.0 * disp_range
    err = np.abs(disp_pred - disp_gt.astype(np.float32))
    if valid_mask is not None:
        err = err[valid_mask]
    return float(np.mean(err > threshold) * 100.0)


# ──────────────────────────────────────────────
# 5. Photometric alignment (cross-camera gain normalization)
# ──────────────────────────────────────────────

def photometric_align_gain(img_src: np.ndarray,
                            img_ref: np.ndarray) -> np.ndarray:
    """
    Global gain photometric alignment: adjust img_src brightness mean to match img_ref.

    Applicable scenario: small exposure difference (< 1 EV), no significant HDR distribution difference.
    """
    mean_ref = float(np.mean(img_ref))
    mean_src = float(np.mean(img_src))
    if mean_src < 1e-6:
        return img_src.copy()
    gain = mean_ref / mean_src
    aligned = np.clip(img_src.astype(np.float32) * gain, 0, 255).astype(np.uint8)
    return aligned


def photometric_align_histogram(img_src: np.ndarray,
                                 img_ref: np.ndarray) -> np.ndarray:
    """
    Per-channel histogram matching photometric alignment: map img_src histogram to match img_ref.

    Applicable scenario: large exposure difference or obvious tone bias.
    Supports grayscale (2D) and color images (3D).
    """
    def _match_channel(src_ch: np.ndarray, ref_ch: np.ndarray) -> np.ndarray:
        src_vals, src_counts = np.unique(src_ch.ravel(), return_counts=True)
        ref_vals, ref_counts = np.unique(ref_ch.ravel(), return_counts=True)
        src_cdf = np.cumsum(src_counts).astype(np.float64)
        src_cdf /= src_cdf[-1]
        ref_cdf = np.cumsum(ref_counts).astype(np.float64)
        ref_cdf /= ref_cdf[-1]
        # Build mapping using linear interpolation: src CDF value -> ref gray value
        mapped = np.interp(src_cdf, ref_cdf, ref_vals)
        lut = np.zeros(256, dtype=np.uint8)
        np.put(lut, src_vals.astype(int), mapped.astype(np.uint8))
        return lut[src_ch]

    if img_src.ndim == 2:
        return _match_channel(img_src, img_ref)

    result = np.zeros_like(img_src)
    for c in range(img_src.shape[2]):
        result[:, :, c] = _match_channel(img_src[:, :, c], img_ref[:, :, c])
    return result


# ──────────────────────────────────────────────
# 6. Main demo function
# ──────────────────────────────────────────────

def main():
    print("=" * 62)
    print("  Multi-camera disparity estimation: StereoBM vs StereoSGBM (synthetic data)")
    print("=" * 62)

    WIDTH, HEIGHT, TRUE_DISP = 640, 480, 16
    NUM_DISP = 64

    # Generate test images
    left, right = generate_synthetic_stereo(WIDTH, HEIGHT, TRUE_DISP)
    gt_disp = np.full((HEIGHT, WIDTH), float(TRUE_DISP), dtype=np.float32)
    # Right side has no valid disparity (corresponding region in right image is black-filled)
    valid_mask = np.ones((HEIGHT, WIDTH), dtype=bool)
    valid_mask[:, WIDTH - TRUE_DISP:] = False
    print(f"Image size: {WIDTH}x{HEIGHT}, ground truth disparity: {TRUE_DISP} px, valid pixels: {valid_mask.sum()}")

    # -- StereoBM --
    d_bm, t_bm = compute_disparity_bm(left, right,
                                       num_disparities=NUM_DISP,
                                       block_size=15)
    epe_bm   = compute_epe(d_bm, gt_disp, NUM_DISP, valid_mask)
    bad3_bm  = compute_bad_pct(d_bm, gt_disp, NUM_DISP, threshold=3.0, valid_mask=valid_mask)

    # -- StereoSGBM --
    d_sgbm, t_sgbm = compute_disparity_sgbm(left, right,
                                              num_disparities=NUM_DISP,
                                              block_size=5,
                                              use_3way=True)
    epe_sgbm  = compute_epe(d_sgbm, gt_disp, NUM_DISP, valid_mask)
    bad3_sgbm = compute_bad_pct(d_sgbm, gt_disp, NUM_DISP, threshold=3.0, valid_mask=valid_mask)

    # -- Print comparison table --
    print(f"\n{'Algorithm':<15}{'Time(ms)':<12}{'EPE(px)':<12}{'Bad-3%':<10}")
    print("-" * 49)
    print(f"{'StereoBM':<15}{t_bm:<12.1f}{epe_bm:<12.3f}{bad3_bm:<10.2f}")
    print(f"{'StereoSGBM':<15}{t_sgbm:<12.1f}{epe_sgbm:<12.3f}{bad3_sgbm:<10.2f}")

    # -- Photometric alignment demo --
    print("\nPhotometric alignment comparison (simulating secondary camera underexposed at 0.7x):")
    img_dark = (left.astype(np.float32) * 0.65).astype(np.uint8)
    aligned_gain = photometric_align_gain(img_dark, left)
    aligned_hist  = photometric_align_histogram(img_dark, left)

    def mae(a, b):
        return float(np.mean(np.abs(a.astype(float) - b.astype(float))))

    print(f"  Original error (MAE):            {mae(img_dark, left):.2f}")
    print(f"  After gain alignment (MAE):      {mae(aligned_gain, left):.2f}")
    print(f"  After histogram alignment (MAE): {mae(aligned_hist, left):.2f}")

    print("\n[Tip] To save disparity map visualizations, uncomment the following lines:")
    print("  cv2.imwrite('disp_bm.png', d_bm)")
    print("  cv2.imwrite('disp_sgbm.png', d_sgbm)")

    # cv2.imwrite("disp_bm.png", d_bm)
    # cv2.imwrite("disp_sgbm.png", d_sgbm)


if __name__ == "__main__":
    main()
```

**Key Parameter Tuning Notes:**

| Parameter | StereoBM Recommended | StereoSGBM Recommended | Notes |
|---|---|---|---|
| `numDisparities` | 64–128 | 64–256 | Must be a multiple of 16; determined by camera baseline and scene depth |
| `blockSize` | 9–21 (odd) | 3–11 (odd) | Larger = smoother, but lower edge accuracy |
| `P1` | N/A | $8 \cdot bs^2$ | SGM small disparity penalty, affects smoothness |
| `P2` | N/A | $32 \cdot bs^2$ | SGM large disparity penalty, affects discontinuous edges |
| `uniquenessRatio` | 10–15 | 5–15 | Uniqueness threshold; higher = sparser but more reliable disparity map |
| `speckleWindowSize` | 50–200 | 50–200 | Small connected-component (noise) removal window size |

---

## 7 References

1. Hirschmüller, H. (2008). *Stereo Processing by Semiglobal Matching and Mutual Information*. **IEEE TPAMI**, 30(2), 328–341.
2. Lipson, L., Teed, Z., & Deng, J. (2021). *RAFT-Stereo: Multilevel Recurrent Field Transforms for Stereo Matching*. **3DV 2021**. arXiv:2109.07547.
3. Nistér, D. (2004). *An Efficient Solution to the Five-Point Relative Pose Problem*. **IEEE TPAMI**, 26(6), 756–770.
4. Zhang, Z. (2000). *A Flexible New Technique for Camera Calibration*. **IEEE TPAMI**, 22(11), 1330–1334.
5. Burt, P. J., & Adelson, E. H. (1983). *A Multiresolution Spline with Application to Image Mosaics*. **ACM TOG**, 2(4), 217–236.
6. Debevec, P. E., & Malik, J. (1997). *Recovering High Dynamic Range Radiance Maps from Photographs*. **SIGGRAPH 1997**, 369–378.
7. He, K., Sun, J., & Tang, X. (2013). *Guided Image Filtering*. **IEEE TPAMI**, 35(6), 1397–1409.
8. Kwatra, V., et al. (2003). *Graphcut Textures: Image and Video Synthesis Using Graph Cuts*. **SIGGRAPH 2003**, 277–286.
9. Wang, Z., et al. (2004). *Image Quality Assessment: From Error Visibility to Structural Similarity*. **IEEE TIP**, 13(4), 600–612.
10. Zabih, R., & Woodfill, J. (1994). *Non-parametric Local Transforms for Computing Visual Correspondence*. **ECCV 1994**, 151–158.
11. Fischler, M. A., & Bolles, R. C. (1981). *Random Sample Consensus: A Paradigm for Model Fitting with Applications to Image Analysis and Automated Cartography*. **CACM**, 24(6), 381–395.

---

## 8 Glossary

| Term | Full Name | Description |
|---|---|---|
| Disparity | Disparity | Horizontal pixel offset of a corresponding point in the left and right images |
| Baseline | Baseline | Distance between the optical centers of two cameras (millimeters) |
| Extrinsic Parameters | Extrinsic Parameters | Rotation matrix and translation vector describing the relative position and orientation of cameras |
| Intrinsic Parameters | Intrinsic Parameters | Matrix describing the camera's focal length, principal point, and other optical parameters |
| Essential Matrix | Essential Matrix | 3×3 matrix encoding the epipolar geometric constraint of a calibrated stereo camera pair |
| Fundamental Matrix | Fundamental Matrix | Epipolar constraint matrix incorporating intrinsic parameters, operating on pixel coordinates |
| Epipolar Rectification | Epipolar Rectification | Geometric transform aligning stereo image epipolar lines horizontally to simplify disparity search |
| SGM | Semi-Global Matching | Semi-global matching; solves for disparity via multi-directional dynamic programming |
| EPE | End-Point Error | Mean absolute error between a disparity map and ground truth (pixels) |
| D1-all | — | KITTI benchmark disparity metric: percentage of pixels with error > 3 px and relative error > 5% |
| CCM | Color Correction Matrix | Maps the camera color space to a reference color space |
| HDR | High Dynamic Range | Scene luminance contrast exceeding the recordable range of a single exposure |
| CFA | Color Filter Array | Color filter array on the sensor (e.g., Bayer pattern) |
| AWB | Auto White Balance | Estimates and compensates for illuminant color temperature |
| FOV | Field of View | Camera field of view angle |
| DN | Digital Number | Digitally quantized value output by the sensor |
| Ghosting | — | Double image of the same object in a fused image due to alignment errors |
| Seam | — | The boundary line between different camera regions in a multi-camera stitched image |
| Confidence Map | — | Per-pixel reliability score of the disparity map, used to filter invalid disparities |
