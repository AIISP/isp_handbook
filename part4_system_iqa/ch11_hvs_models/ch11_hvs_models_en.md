# Part 4, Chapter 11: Human Visual System (HVS) Models and Perception-Driven ISP Design

> **Scope:** This chapter covers perceptual models of the Human Visual System (HVS, 人类视觉系统) and how HVS constraints are integrated into ISP design: applications of CSF, JND, and visual saliency in IQA.
> **Prerequisites:** Volume 4, Chapter 4 (Perceptual IQA); Volume 1, Chapter 5 (Color Science Fundamentals)
> **Target Readers:** IQA engineers, algorithm engineers

---

## Table of Contents

- [§1 Theory](#1-theory)
- [§2 Algorithm Methods](#2-algorithm-methods)
- [§3 Tuning Guide](#3-tuning-guide)
- [§4 Common Perceptual Artifacts and Failure Modes](#4-common-perceptual-artifacts-and-failure-modes)
- [§5 Evaluation Methods](#5-evaluation-methods)
- [§6 Code Implementation](#6-code-implementation)
- [References](#references)
- [§8 Glossary](#8-glossary)

---

## §1 Theory

### 1.1 Engineering Significance of the Human Visual System

The ultimate end user of ISP algorithms is the human eye. Therefore, the most authoritative standard for measuring ISP output quality is not PSNR (which has limited correlation with human perception), but rather the perceptual quality of the Human Visual System (HVS). Understanding how the HVS works is the foundation for designing perception-driven ISP and IQA.

The HVS visual processing chain begins with the optical system of the eye, passes through the retina photoreceptors, and continues through the lateral geniculate nucleus (LGN), primary visual cortex (V1), and higher visual areas (V2–V5). From an engineering perspective, the most important HVS properties are:

1. **Spatial Frequency Response (CSF):** Sensitivity to sinusoidal gratings at different spatial frequencies, exhibiting a bandpass characteristic
2. **Visual Masking:** Background texture or structure suppresses perception of signals superimposed on it — i.e., the JND (Just Noticeable Difference) effect
3. **Color Perception:** Nonlinear responses of the three types of cone cells (L/M/S), with higher sensitivity to the luminance channel
4. **Visual Saliency:** Attention is automatically drawn to specific visual features (contrast, motion, color oddities)

These properties directly determine which image distortions are visible to the human eye and which are invisible. The goal of perception-driven ISP design is to maximize algorithmic freedom within the "invisible" distortion space, while concentrating computational resources on eliminating the distortion types to which human eyes are most sensitive.

### 1.2 Contrast Sensitivity Function (CSF)

The **CSF (Contrast Sensitivity Function)** describes the detection threshold of the HVS for sinusoidal gratings at different spatial frequencies. The CSF is typically measured through psychophysics experiments: sinusoidal gratings with gradually varying spatial frequencies are presented to subjects, and the minimum perceivable contrast (threshold contrast) is measured.

The reciprocal of the CSF is the contrast sensitivity:
$$CS(f) = \frac{1}{C_{\min}(f)}$$

where $C_{\min}(f)$ is the detection threshold contrast at frequency $f$.

**Classical CSF Model (Mannos-Sakrison, 1974):**

$$H(f) = 2.6(0.0192 + 0.114f) e^{-(0.114f)^{1.1}}$$

where $f$ is in units of cycles/degree (cpd). The CSF peaks at approximately 3–6 cpd; sensitivity drops significantly below 0.5 cpd and above 20 cpd, producing a bandpass shape.

**Converting CPD to cy/px:** Given a display resolution of $d$ pixels/degree:
$$f[\text{cy/px}] = f[\text{cpd}] / d$$

A typical smartphone screen at normal viewing distance (~30 cm) has approximately 50–60 pixels/degree.

**Engineering Significance of CSF for ISP:**
- High-frequency noise (>20 cpd) is nearly invisible at normal viewing distance; excessive denoising is unnecessary
- Mid-frequency detail (3–10 cpd) is where the human eye is most sensitive — the "sensitive zone" for ISP sharpening and denoising
- Low-frequency (<1 cpd) color errors are most easily noticed (e.g., white balance bias)

### 1.3 JND Model (Just Noticeable Difference)

**JND (Just Noticeable Difference, 最小可觉差)** is a fundamental concept in perceptual psychology describing perceptual thresholds. In image quality, JND refers to the amplitude of signal distortion that is just barely perceptible in the presence of a background signal.

**Visual Masking:** JND is influenced by two types of masking effects:

1. **Luminance Masking:** Very high luminance (highlight regions) and very low luminance (shadow regions) raise the JND threshold, making distortions in those areas harder to perceive. The Weber-Fechner Law: $\Delta I / I = k$ (constant) — i.e., the perceived change is relative, not absolute.

2. **Texture Masking:** The richer the background texture (i.e., the more high-frequency content), the harder it is to perceive distortions superimposed on it. In flat areas (sky, walls), the human eye is extremely sensitive; in complex textured areas (grass, hair), tolerance for distortion is high.

**JND Spatial Frequency Model (Liu et al., 2010):**

$$\text{JND}(x, y) = \max[\text{bg}(x,y) \cdot T_L(x,y), T_{\text{textured}}(x,y)]$$

where $T_L$ is the luminance masking threshold, $T_{\text{textured}}$ is the texture masking threshold, and the maximum of the two is taken.

**Applications of JND in ISP:**
- **Lossy compression (JPEG/HEIF):** Introduce quantization noise within the JND range to achieve visually lossless compression
- **Perceptual denoising:** Only noise exceeding the JND threshold is suppressed, protecting detail within the JND range
- **Sharpening control:** Avoid over-sharpening in flat areas (low JND threshold); allow stronger sharpening in textured areas (high JND threshold)

### 1.4 Lateral Inhibition Effects: Mach Bands and Simultaneous Contrast

**Lateral Inhibition** is a fundamental neural mechanism in the HVS where activated photoreceptors suppress the responses of adjacent cells, enhancing edge contrast and creating perceptual illusions at luminance boundaries.

**Mach Bands:** At a luminance ramp edge (a gradual transition between two uniform luminance regions), observers perceive a bright band at the light side of the edge and a dark band at the dark side — even though no such luminance extrema exist in the physical signal. This is caused by lateral inhibition in the retinal ganglion layer. **ISP relevance:** Aggressive tone-mapping curves and gamma adjustments can introduce Mach-band-like artifacts at luminance transitions; perceptual quality metrics that weight edge regions should account for this effect.

**Simultaneous Contrast:** The perceived luminance or color of a region is influenced by its surround. A gray patch appears lighter on a dark background and darker on a light background, even though the physical stimulus is identical. Similarly, a neutral gray patch surrounded by a colored background adopts a perceived tint of the complementary color. **ISP relevance:** Local tone-mapping algorithms that process regions independently can introduce visible simultaneous-contrast artifacts at region boundaries; global-context awareness (e.g., guided filters or bilateral smoothing) is required to suppress these effects.

**ISP Engineering Implications:**
- Avoid creating hard luminance ramps in tone-mapping LUTs; smooth transitions prevent Mach band perception
- HDR-to-SDR tone-mapping should maintain sufficient surround luminance context to avoid simultaneous contrast shifts
- Perceptual IQA models that ignore these lateral-inhibition effects will underestimate artifact visibility near edges and region boundaries

### 1.6 Color Perception and Perceptually Uniform Color Spaces

**Non-uniformity of Human Color Perception:** The CIE XYZ color space is not perceptually uniform. Two points that are equidistant in XYZ space may be perceived as having very different color differences (the green region has small perceived differences; the blue region has large perceived differences).

**Perceptually Uniform Color Spaces:**
- **CIE Lab (CIELAB):** The 1976 standard: $L^*$ (lightness), $a^*$ (red-green axis), $b^*$ (blue-yellow axis). Euclidean distance (Delta E76) in Lab space correlates significantly better with perceived color differences than XYZ space.
- **ICtCp (ITU-R BT.2100):** A perceptually uniform color space for HDR video standards, particularly suited for IQA of HDR content.

**Guidance for ISP Design:** Color correction errors (AWB errors, CCM errors) should be evaluated in Lab space rather than RGB space. The subjectively acceptable threshold of $\Delta E_{00} < 3$ is determined precisely based on the color perception properties of the HVS.

### 1.7 Theoretical HVS Basis of SSIM

**SSIM (Structural Similarity Index)** was designed by Wang et al. (IEEE TIP 2004) based on the following assumptions about the HVS:

1. The HVS perceives images primarily by extracting structural information, rather than making pixel-by-pixel absolute luminance comparisons
2. Luminance, contrast, and structure are mutually independent perceptual dimensions
3. Local statistics (mean, variance, covariance) can effectively characterize these three dimensions

SSIM combines comparisons of these three dimensions as:
$$\text{SSIM}(\mathbf{x}, \mathbf{y}) = \underbrace{\frac{2\mu_x\mu_y + C_1}{\mu_x^2 + \mu_y^2 + C_1}}_{\text{luminance comparison}} \cdot \underbrace{\frac{2\sigma_x\sigma_y + C_2}{\sigma_x^2 + \sigma_y^2 + C_2}}_{\text{contrast comparison}} \cdot \underbrace{\frac{\sigma_{xy} + C_3}{\sigma_x\sigma_y + C_3}}_{\text{structure comparison}}$$

SSIM's design directly reflects the structural perception properties of the HVS, making it a perceptual quality metric that PSNR cannot replace.

---

## §2 Algorithm Methods

### 2.1 CSF-Weighted IQA

**Core Idea of CSF Weighting:** Decompose image distortion by frequency, weight different frequency components according to the CSF, and give higher-weighted frequencies a greater influence on overall perceived quality.

**CSF-PSNR (Perceptually Weighted PSNR):**
1. Decompose the image distortion $\mathbf{e} = \hat{\mathbf{x}} - \mathbf{x}$ in the frequency domain (2D DFT)
2. Weight each frequency component according to the CSF model: $\hat{E}(u,v) = E(u,v) \cdot H(f(u,v))$
3. Transform back to the spatial domain and compute PSNR of the weighted error map

This method is widely used in visual quality evaluation for image compression (JPEG, HEVC).

### 2.2 Visual Attention Model (Itti Model)

**Itti Model (Itti et al., IEEE TPAMI 1998)** is the most influential computational visual attention model, simulating human eye movements and attention mechanisms:

**Architecture:**

1. **Feature Extraction:** Three types of bottom-up features are extracted from the image:
   - **Intensity:** $I = (R + G + B) / 3$
   - **Color:** Red-green opponency $RG = (R-G)/I$; blue-yellow opponency $BY = (B - (R+G)/2)/I$
   - **Orientation:** Gabor filter responses (0°, 45°, 90°, 135° orientations)

2. **Multi-Scale Pyramid:** Each feature type is extracted at 9 scales ($\sigma = 0, \ldots, 8$, corresponding to image downscaling by $2^0$ to $2^8$), forming a Gaussian pyramid.

3. **Center-Surround Difference:** Simulates the receptive field properties of retinal neurons; computes the difference between fine and coarse scales:
   $$\mathcal{F}(c, s) = |\mathcal{G}_c - \mathcal{G}_s|$$
   where $c \in \{2,3,4\}$, $s = c + \delta$, $\delta \in \{3, 4\}$.

4. **Feature Normalization and Fusion:** Each feature map is normalized to [0,1] and fused into the final saliency map via linear weighting:
   $$S = \frac{1}{3}\left(\bar{\mathcal{I}} + \bar{\mathcal{C}} + \bar{\mathcal{O}}\right)$$

**Applications of the Itti Model in ISP:**
- **Region of Interest (ROI) weighting:** Allocate more denoising/enhancement compute budget to high-saliency regions (faces, subjects)
- **Perceptually weighted IQA:** Give higher weight to distortions in high-saliency regions
- **Lossy compression allocation:** Assign more quantization error to low-saliency regions (background, sky)

### 2.3 Deep Saliency Detection: Modern Methods

The limitation of the traditional Itti model is that it uses only bottom-up features and cannot capture semantic saliency (e.g., "there is a person in the image"). Modern deep learning saliency detection methods:

**MR-Net (Multi-Scale Refinement Network):** Multi-scale saliency prediction based on VGG/ResNet features, trained on large-scale eye-tracking datasets such as SALICON.

**DeepGaze II (arXiv 2016):** An eye movement prediction model based on VGG features, capable of predicting the probability distribution of human fixation points. It is one of the most accurate computational visual attention models currently available.

**Integrating Saliency Detection into the ISP Pipeline:**
- Saliency detection typically runs immediately after image acquisition (lightweight models can be used, such as MobileNet-based saliency detector, 10 ms/frame)
- The saliency map output serves as a spatial attention weight map to guide spatially adaptive processing in subsequent ISP modules

### 2.4 LPIPS: Learned Perceptual Distance

**LPIPS (Learned Perceptual Image Patch Similarity, Zhang et al., CVPR 2018)** uses intermediate features of a pre-trained deep network (VGG, AlexNet) to compute the perceptual distance between two images:

$$\text{LPIPS}(\mathbf{x}, \hat{\mathbf{x}}) = \sum_l \frac{1}{H_l W_l} \sum_{h,w} \| \mathbf{w}_l \odot (\phi_l(\mathbf{x})_{h,w} - \phi_l(\hat{\mathbf{x}})_{h,w}) \|_2^2$$

where $\phi_l$ denotes layer-$l$ features and $\mathbf{w}_l$ are learnable channel weights.

The core advantage of LPIPS is that deep network features implicitly encode the structural and semantic information that the HVS attends to. The correlation between LPIPS and subjective perceptual scores (MOS) is significantly higher than that of PSNR and SSIM, and LPIPS is widely adopted in image restoration and GAN generation quality evaluation.

### 2.5 Applications of Perceptual Loss Functions in ISP

The primary way to incorporate HVS constraints into ISP algorithm training is to introduce a perceptual term into the loss function:

**Perceptual Loss (Johnson et al., ECCV 2016):**
$$\mathcal{L}_{\text{perc}} = \sum_l \frac{1}{C_l H_l W_l} \| \phi_l(\hat{\mathbf{x}}) - \phi_l(\mathbf{x}) \|_F^2$$

where $\phi_l$ is typically the relu3_3 or relu4_3 layer feature of VGG-19. Perceptual loss guides the network to produce images that are visually more natural and texturally more realistic, effectively avoiding the over-smoothing caused by L2 loss.

**Style Loss:** A texture statistics matching loss based on Gram matrices, used to control the texture style of the output image (avoiding spurious textures):
$$\mathcal{L}_{\text{style}} = \sum_l \| G_l(\hat{\mathbf{x}}) - G_l(\mathbf{x}) \|_F^2$$

where $G_l = \phi_l^T \phi_l / (C_l H_l W_l)$ is the Gram matrix.

---

## §3 Tuning Guide

### 3.1 CSF Parameters for Perceptual IQA

**CSF Model Parameter Selection:** CSF parameter settings for different application scenarios:

| Application Scenario | Recommended Viewing Distance | Spatial Frequency Range | CSF Peak Frequency |
|----------------------|-----------------------------|-----------------------|--------------------|
| Smartphone (handheld, 30 cm) | 30 cm | 0–60 cpd | 3–6 cpd |
| Desktop monitor (60 cm) | 60 cm | 0–30 cpd | 3–6 cpd |
| Television (2 m) | 200 cm | 0–10 cpd | 2–3 cpd |
| Surveillance display (>5 m) | 500+ cm | 0–5 cpd | 1–2 cpd |

**Practical Recommendation:** When defining ISP perceptual quality metrics, clearly specify the target display device and viewing distance, and select the corresponding CSF parameters.

### 3.2 Setting JND Thresholds

**Empirical JND Threshold Values (8-bit image, range 0–255):**
- Flat regions (e.g., blue sky): JND ≈ 1–2 DN (human eye is extremely sensitive)
- Medium texture regions: JND ≈ 5–15 DN
- Complex texture regions (e.g., foliage): JND ≈ 20–40 DN

**Application in Denoising Strength Control:** Set the noise suppression target such that residual noise amplitude is close to but does not exceed the JND threshold of the current region, achieving "just-invisible" optimal denoising:
- Flat regions: strong denoising required (target residual noise < 2 DN)
- Textured regions: higher residual noise is acceptable (target < 20 DN), avoiding over-smoothing that destroys texture

### 3.3 Balancing Saliency Weights in ISP

**Controlling Saliency Weighting Strength:** Excessive saliency weighting causes background region quality to drop too low (noticeably blurry or noisy), degrading the overall visual impression. Recommended settings:
- Minimum weight (background): 0.3–0.5 (not 0, to ensure basic background quality)
- Maximum weight (subject/face): 1.0
- Smooth weight transitions: apply Gaussian smoothing (σ = 20–50 pixels) to the saliency map to avoid abrupt processing boundaries from sudden weight changes

**Combining with Scene Semantics:** Fuse the outputs of deep learning face detection and object detection with the saliency map to ensure semantic subjects receive high weights.

### 3.4 Hyperparameters for Perceptual Loss

**Selecting Perceptual Loss Layers:**
- **Shallow features (relu1_2, relu2_2):** More sensitive to low-level texture and color; suitable for denoising and color enhancement tasks
- **Deep features (relu3_3, relu4_3):** More sensitive to high-level semantic structure; suitable for super-resolution and image generation tasks

**Weight Balancing:** Perceptual loss is typically combined with reconstruction loss (L1/L2):
$$\mathcal{L} = \mathcal{L}_{\text{rec}} + \lambda_p \mathcal{L}_{\text{perc}}$$

Recommended range for $\lambda_p$: $[0.01, 0.1]$ (to prevent the perceptual loss from dominating and causing color shift). An excessively large $\lambda_p$ will cause the network to produce visually sharp but inaccurate colors.

---

## §4 Common Perceptual Artifacts and Failure Modes

### 4.1 Banding Artifact

**Symptom:** Visible quantization steps appear in flat gradient areas (sky, skin), manifesting as color bands.

**HVS Analysis:** The human eye is extremely sensitive to local contrast in flat areas (low luminance masking); even 1–2 DN quantization error can produce visible banding structures.

**Occurrence Scenarios:** High-compression JPEG (8-bit quantization step size too large); improper dithering when displaying 10-bit HDR content on an 8-bit monitor.

**Solutions:**
- Add dithering noise before quantization to break up quantization steps
- Use perceptual quantization: reduce quantization step size in dark areas and increase it in bright areas (corresponding to luminance masking characteristics)
- Use a perceptually uniform intermediate color space (ICtCp rather than RGB) when converting HDR to SDR (tone mapping)

### 4.2 Waxy Skin Effect

**Symptom:** After portrait processing, the skin loses natural texture and takes on a "wax figure" or "airbrushed" appearance.

**HVS Cause:** The skin is in a region of moderate saliency, and the human eye is extremely sensitive to skin texture (skin is a critical visual recognition object in human evolution). Excessive smoothing removes sebaceous gland texture and pores, causing the skin to lose its sense of realism.

**Solutions:** Set a lower denoising intensity in the face region (limit suppression of high-frequency detail), or use a skin texture perceptual loss to constrain portrait enhancement networks.

### 4.3 Color Fringing / Chromatic Aberration

**Symptom:** Visible colored outlines appear at high-contrast edges (e.g., tree branch vs. sky boundary), typically purple or green.

**HVS Sensitivity:** Edges are central to the structural perception of the human eye; color anomalies at edges (high CSF weight on the low-frequency components of edges) are extremely easy to perceive.

**Cause:** Lens chromatic aberration (longitudinal/lateral chromatic aberration); insufficient CA correction algorithms in the ISP.

**Solutions:** Chromatic aberration correction algorithms detailed in Volume 2, Chapter 24, combined with saliency weighting to prioritize processing of high-contrast edge areas.

### 4.4 Color Shift from Perceptual Loss

**Symptom:** Restoration networks trained with perceptual loss produce output images with a systematic color shift compared to the reference image (e.g., warmer tones, greenish cast).

**Cause:** The VGG feature extractor is trained on ImageNet, and its color response carries the color statistics bias of the ImageNet dataset. Perceptual loss encourages the output image's VGG features to align with the reference image, but VGG is insensitive to color shifts, so color drift remains unconstrained.

**Solutions:** Explicitly add color constraints to the loss function (e.g., L1 loss in Lab space to constrain global color), or use color histogram matching as post-processing.

---

## §5 Evaluation Methods

### 5.1 Subjective IQA Methods

**DSIS (Double Stimulus Impairment Scale):** Evaluators simultaneously view both the reference image and the test image, and rate the degree of impairment of the test image (1–5, where 5 means no impairment). MOS (Mean Opinion Score) is the average score across multiple evaluators.

**ACR (Absolute Category Rating):** Evaluators view only the test image and rate it against an absolute standard (1–5). Suitable for no-reference IQA scenarios.

**SAMVIQ (Subjective Assessment Methodology for Video and Image Quality):** Allows evaluators to freely switch and compare among multiple references; suitable for multi-option comparative evaluation.

**Eye Tracking Experiments:** Use an eye tracker (e.g., Tobii) to record evaluators' fixation points and saccade paths, verifying the prediction accuracy of saliency models. KL divergence and NSS (Normalized Scanpath Saliency) are commonly used evaluation metrics.

### 5.2 Quantitative Validation of HVS Models

**CSF Model Validation:** Compare subjective detection thresholds for sinusoidal gratings at different spatial frequencies with CSF model predictions, and compute the fitting error (RMS error).

**JND Model Validation:** Measure subjective JND under different background texture conditions and compare with model predictions.

**Saliency Model Evaluation Metrics:**
- **AUC (Area Under ROC Curve):** Area under the ROC curve for predicting human fixation points from the saliency map
- **NSS (Normalized Scanpath Saliency):** Normalized score of saliency values at human fixation points relative to the average level
- **CC (Correlation Coefficient):** Correlation coefficient between the predicted saliency map and the eye-tracking density map

### 5.3 Correlation of Perceptual IQA Metrics with Subjective MOS

Evaluating the correlation between IQA metrics and subjective scores is critical. Commonly used evaluation datasets:

| Dataset | Number of Images | Distortion Types | Purpose |
|---------|-----------------|------------------|---------|
| LIVE | 29 ref + 779 dist | Compression/blur/noise | Classic benchmark |
| CSIQ | 30 ref + 866 dist | 6 distortion types | Classic benchmark |
| TID2013 | 25 ref + 3000 dist | 24 distortion types | Multi-distortion |
| KADID-10k | 81 ref + 10125 dist | 25 distortion types | Large-scale |
| PIPAL | 250 ref + 29000 dist | GAN/restoration | Modern benchmark |

Typical Spearman Rank-Order Correlation Coefficient (SROCC) values of each metric with DMOS (Difference MOS) on the LIVE dataset:

| Metric | SROCC (LIVE) | Notes |
|--------|-------------|-------|
| PSNR | ~0.87 | Classic metric; works well for compression noise |
| SSIM | ~0.874 | Structural perception; widely used (Wang et al. 2004) |
| MS-SSIM | ~0.95 | Multi-scale SSIM; more accurate |
| LPIPS | ~0.93 | Learned perceptual distance |
| NIQE (no-reference) | ~0.75 | No reference image required |

---

## §6 Code Implementation

### 6.1 CSF Model and Perceptually Weighted Error

```python
import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional


# ─────────────────────────────────────────────
# CSF Model Implementation
# ─────────────────────────────────────────────

def mannos_sakrison_csf(frequency_cpd: np.ndarray) -> np.ndarray:
    """
    Mannos-Sakrison CSF model (1974).
    frequency_cpd: spatial frequency (cycles per degree)
    Returns: contrast sensitivity (normalized, peak = 1)
    """
    h = 2.6 * (0.0192 + 0.114 * frequency_cpd) * np.exp(-(0.114 * frequency_cpd) ** 1.1)
    return h / h.max()


def frequency_to_cpd(freq_cy_px: np.ndarray,
                     pixels_per_degree: float = 55.0) -> np.ndarray:
    """
    Convert cycles/pixel frequency to cycles/degree.
    pixels_per_degree: pixels per degree (depends on display resolution and viewing distance)
    Smartphone at 30 cm viewing distance: ~55 ppd
    Desktop monitor at 60 cm viewing distance: ~40 ppd
    """
    return freq_cy_px * pixels_per_degree


def compute_csf_weights_2d(height: int, width: int,
                            pixels_per_degree: float = 55.0) -> np.ndarray:
    """
    Compute 2D CSF frequency weight map for an image.
    Used for perceptually weighted frequency-domain error computation.

    Returns: [height, width] float32, CSF weights at each frequency point (centered)
    """
    # Generate frequency grid (cycles/pixel, range [0, 0.5])
    u = np.fft.fftfreq(width)    # [0, +f, ..., -f]
    v = np.fft.fftfreq(height)
    U, V = np.meshgrid(u, v)
    freq_cy_px = np.sqrt(U ** 2 + V ** 2)

    # Convert to CPD
    freq_cpd = frequency_to_cpd(freq_cy_px, pixels_per_degree)
    freq_cpd = np.clip(freq_cpd, 0.1, 60)  # Clip frequency range

    # Compute CSF weights
    csf = mannos_sakrison_csf(freq_cpd)
    return csf.astype(np.float32)


def csf_weighted_mse(img1: np.ndarray, img2: np.ndarray,
                     pixels_per_degree: float = 55.0) -> float:
    """
    CSF-weighted perceptual MSE.
    img1, img2: [H, W] float, range [0,1]
    """
    if img1.ndim == 3:
        # Convert to luminance channel
        img1 = 0.299 * img1[:,:,0] + 0.587 * img1[:,:,1] + 0.114 * img1[:,:,2]
        img2 = 0.299 * img2[:,:,0] + 0.587 * img2[:,:,1] + 0.114 * img2[:,:,2]

    H, W = img1.shape
    # Compute FFT of error
    error = img1 - img2
    error_fft = np.fft.fft2(error)

    # CSF weights
    csf_weights = compute_csf_weights_2d(H, W, pixels_per_degree)

    # Weighted error
    weighted_error_fft = error_fft * csf_weights
    weighted_error = np.fft.ifft2(weighted_error_fft).real

    return np.mean(weighted_error ** 2)


# ─────────────────────────────────────────────
# JND Model Implementation
# ─────────────────────────────────────────────

def compute_jnd_map(luminance: np.ndarray,
                    bg_luminance: Optional[np.ndarray] = None) -> np.ndarray:
    """
    JND threshold map based on luminance masking (simplified version).

    luminance: [H, W] float, normalized luminance [0, 1]
    bg_luminance: [H, W] background luminance (if None, use local blur as substitute)
    Returns: [H, W] JND threshold map (normalized)
    """
    if bg_luminance is None:
        # Use Gaussian blur as a background luminance estimate
        bg_luminance = cv2.GaussianBlur(luminance.astype(np.float32), (15, 15), 5)

    # Luminance masking threshold (piecewise approximation of Weber-Fechner law)
    # T_L(l) = 17 * (1 - sqrt(l/127)) + 3  (for 8-bit images)
    # Normalized version used here
    l = np.clip(bg_luminance, 1e-6, 1.0)
    T_luminance = 0.067 * (1.0 - np.sqrt(l)) + 0.012

    # Texture masking threshold (local standard deviation)
    mean_sq = cv2.GaussianBlur(luminance.astype(np.float32) ** 2, (7, 7), 2)
    mean_val = cv2.GaussianBlur(luminance.astype(np.float32), (7, 7), 2)
    local_var = mean_sq - mean_val ** 2
    T_texture = 0.15 * np.sqrt(np.maximum(local_var, 0))

    # Combined JND threshold (take maximum)
    jnd_map = np.maximum(T_luminance, T_texture)
    return jnd_map.astype(np.float32)


def jnd_weighted_psnr(img_ref: np.ndarray,
                       img_dist: np.ndarray) -> float:
    """
    JND-weighted PSNR: apply larger penalty in low-JND regions (high perceptual sensitivity).

    img_ref, img_dist: [H, W, 3] uint8
    """
    ref_f = img_ref.astype(np.float32) / 255.0
    dist_f = img_dist.astype(np.float32) / 255.0

    # Compute luminance channel
    lum_ref = (0.299 * ref_f[:,:,2] + 0.587 * ref_f[:,:,1] +
               0.114 * ref_f[:,:,0])  # BGR->Y

    # JND map (smaller value = higher perceptual sensitivity)
    jnd_map = compute_jnd_map(lum_ref)

    # JND perceptual weight: smaller JND = larger weight
    weight = 1.0 / (jnd_map + 0.01)
    weight = weight / weight.mean()  # Normalize

    # Weighted MSE
    error = ref_f - dist_f
    lum_error = (0.299 * error[:,:,2] + 0.587 * error[:,:,1] +
                 0.114 * error[:,:,0])
    weighted_mse = np.mean(weight * lum_error ** 2)

    if weighted_mse > 0:
        return 10 * np.log10(1.0 / weighted_mse)
    return float('inf')


# ─────────────────────────────────────────────
# Simplified Itti Visual Saliency Model
# ─────────────────────────────────────────────

class IttiSaliencyMap:
    """
    Simplified Itti-Koch saliency map computation.
    Multi-scale center-surround difference based on intensity,
    color opponency, and orientation features.
    """
    def __init__(self, num_scales: int = 6):
        self.num_scales = num_scales

    def _build_gaussian_pyramid(self, img: np.ndarray) -> list:
        """Build Gaussian pyramid."""
        pyramid = [img.astype(np.float32)]
        for _ in range(self.num_scales - 1):
            pyramid.append(cv2.pyrDown(pyramid[-1]))
        return pyramid

    def _center_surround(self, pyramid: list,
                          center_scale: int,
                          surround_scale: int) -> np.ndarray:
        """Compute center-surround difference."""
        center = pyramid[center_scale]
        surround = pyramid[surround_scale]
        # Upsample to center scale
        h, w = center.shape[:2]
        surround_up = cv2.resize(surround, (w, h),
                                  interpolation=cv2.INTER_LINEAR)
        return np.abs(center - surround_up)

    def compute(self, image: np.ndarray) -> np.ndarray:
        """
        Compute saliency map.
        image: [H, W, 3] uint8 BGR
        Returns: [H, W] float32 saliency map, normalized to [0,1]
        """
        img_f = image.astype(np.float32) / 255.0
        R = img_f[:,:,2]; G = img_f[:,:,1]; B = img_f[:,:,0]

        # Intensity channel
        I = (R + G + B) / 3.0
        I = np.clip(I, 1e-6, 1.0)

        # Color opponency
        RG = (R - G) / I
        BY = (B - 0.5 * (R + G)) / I

        # Build pyramids
        I_pyr = self._build_gaussian_pyramid(I)
        RG_pyr = self._build_gaussian_pyramid(np.clip(RG, 0, 1))
        BY_pyr = self._build_gaussian_pyramid(np.clip(BY, 0, 1))

        # Orientation features (0 and 90 degrees)
        kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.float32)
        ky = kx.T
        orient_0 = np.abs(cv2.filter2D(I, -1, kx))
        orient_90 = np.abs(cv2.filter2D(I, -1, ky))
        O0_pyr = self._build_gaussian_pyramid(orient_0)
        O90_pyr = self._build_gaussian_pyramid(orient_90)

        H_out, W_out = image.shape[:2]

        # Accumulate center-surround differences
        saliency = np.zeros((H_out, W_out), dtype=np.float32)
        pairs = [(2, 5), (2, 6), (3, 6), (3, 7), (4, 7), (4, 8)]
        # Simplified: use only available scale pairs
        available_pairs = [(c, s) for c, s in pairs
                           if s < self.num_scales]
        if not available_pairs:
            available_pairs = [(0, min(2, self.num_scales-1)),
                               (1, min(3, self.num_scales-1))]

        for c, s in available_pairs:
            for pyr in [I_pyr, RG_pyr, BY_pyr, O0_pyr, O90_pyr]:
                if s < len(pyr):
                    cs = self._center_surround(pyr, c, s)
                    cs_resized = cv2.resize(cs, (W_out, H_out),
                                            interpolation=cv2.INTER_LINEAR)
                    saliency += cs_resized

        # Normalize
        if saliency.max() > 0:
            saliency = (saliency - saliency.min()) / (saliency.max() - saliency.min())

        # Gaussian smoothing (simulate visual attention diffusion)
        saliency = cv2.GaussianBlur(saliency, (41, 41), 15)
        if saliency.max() > 0:
            saliency /= saliency.max()

        return saliency


# ─────────────────────────────────────────────
# SSIM Implementation (Sliding Window Version)
# ─────────────────────────────────────────────

def compute_ssim(img1: np.ndarray, img2: np.ndarray,
                 window_size: int = 11,
                 C1: float = 0.0001,
                 C2: float = 0.0009) -> float:
    """
    Standard SSIM computation (sliding window version, aligned with skimage implementation).
    img1, img2: [H, W] float32, range [0,1]
    """
    sigma = 1.5
    kernel_1d = cv2.getGaussianKernel(window_size, sigma)
    kernel_2d = kernel_1d @ kernel_1d.T
    kernel_2d = kernel_2d.astype(np.float32)

    def weighted_avg(x):
        return cv2.filter2D(x, -1, kernel_2d,
                            borderType=cv2.BORDER_REFLECT)

    mu1 = weighted_avg(img1)
    mu2 = weighted_avg(img2)
    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = weighted_avg(img1 ** 2) - mu1_sq
    sigma2_sq = weighted_avg(img2 ** 2) - mu2_sq
    sigma12 = weighted_avg(img1 * img2) - mu1_mu2

    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
               ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))

    return float(ssim_map.mean())


# ─────────────────────────────────────────────
# Perceptual Loss (VGG Features, PyTorch Implementation)
# ─────────────────────────────────────────────

class VGGPerceptualLoss(nn.Module):
    """
    Perceptual loss based on VGG features.
    Uses relu2_2 and relu3_3 layer features.
    """
    def __init__(self, layer_weights: Optional[dict] = None):
        super().__init__()
        import torchvision.models as models
        vgg = models.vgg19(weights=models.VGG19_Weights.IMAGENET1K_V1)
        # VGG19 0-indexed: relu1_2=3, relu2_2=8, relu3_3=15
        self.slice1 = nn.Sequential(*list(vgg.features)[:4])   # [0–3]  → relu1_2
        self.slice2 = nn.Sequential(*list(vgg.features)[4:9])  # [4–8]  → MaxPool + relu2_2
        self.slice3 = nn.Sequential(*list(vgg.features)[9:16]) # [9–15] → MaxPool + relu3_3
        # Freeze VGG parameters
        for param in self.parameters():
            param.requires_grad = False
        self.layer_weights = layer_weights or {
            'relu1_2': 0.1,
            'relu2_2': 0.1,
            'relu3_3': 1.0
        }

    def forward(self, pred: torch.Tensor,
                target: torch.Tensor) -> torch.Tensor:
        """
        pred, target: [B, 3, H, W], range [0,1]
        """
        loss = 0.0
        h1_pred = self.slice1(pred)
        h1_target = self.slice1(target)
        loss += self.layer_weights['relu1_2'] * F.l1_loss(h1_pred, h1_target)

        h2_pred = self.slice2(h1_pred)
        h2_target = self.slice2(h1_target)
        loss += self.layer_weights['relu2_2'] * F.l1_loss(h2_pred, h2_target)

        h3_pred = self.slice3(h2_pred)
        h3_target = self.slice3(h2_target)
        loss += self.layer_weights['relu3_3'] * F.l1_loss(h3_pred, h3_target)

        return loss


def demo_hvs_tools():
    """Quick demo of the HVS toolchain."""
    # Generate test images
    np.random.seed(42)
    H, W = 256, 256
    ref = np.random.rand(H, W, 3).astype(np.float32)
    # Simulate a slight noise distortion
    dist = np.clip(ref + np.random.normal(0, 0.05, ref.shape), 0, 1).astype(np.float32)

    # 1. CSF-weighted MSE
    csf_mse = csf_weighted_mse(ref[:,:,0], dist[:,:,0], pixels_per_degree=55)
    print(f"CSF-weighted MSE = {csf_mse:.6f}")

    # 2. JND-weighted PSNR
    ref_uint8 = (ref * 255).astype(np.uint8)
    dist_uint8 = (dist * 255).astype(np.uint8)
    jnd_psnr = jnd_weighted_psnr(ref_uint8, dist_uint8)
    std_psnr = 10 * np.log10(1.0 / np.mean((ref - dist) ** 2))
    print(f"Standard PSNR = {std_psnr:.2f} dB")
    print(f"JND-weighted PSNR = {jnd_psnr:.2f} dB")

    # 3. Itti saliency map
    saliency_model = IttiSaliencyMap(num_scales=5)
    img_uint8 = (ref * 255).astype(np.uint8)
    saliency = saliency_model.compute(img_uint8)
    print(f"Saliency map: shape={saliency.shape}, "
          f"min={saliency.min():.3f}, max={saliency.max():.3f}")

    # 4. SSIM
    lum_ref = 0.299*ref[:,:,2] + 0.587*ref[:,:,1] + 0.114*ref[:,:,0]
    lum_dist = 0.299*dist[:,:,2] + 0.587*dist[:,:,1] + 0.114*dist[:,:,0]
    ssim_val = compute_ssim(lum_ref, lum_dist)
    print(f"SSIM = {ssim_val:.4f}")


if __name__ == '__main__':
    demo_hvs_tools()
```

---

## References

[1] Mannos, J.L., Sakrison, D.J. (1974). The Effects of a Visual Fidelity Criterion on the Encoding of Images. IEEE Transactions on Information Theory.
[2] Itti, L., Koch, C., Niebur, E. (1998). A Model of Saliency-Based Visual Attention for Rapid Scene Analysis. IEEE TPAMI 1998.
[3] Wang, Z., Bovik, A.C., Sheikh, H.R., Simoncelli, E.P. (2004). Image Quality Assessment: From Error Visibility to Structural Similarity. IEEE TIP 2004. (SSIM)
[4] Zhang, R., Isola, P., Efros, A.A., Shechtman, E., Wang, O. (2018). The Unreasonable Effectiveness of Deep Features as a Perceptual Metric. CVPR 2018. (LPIPS)
[5] Johnson, J., Alahi, A., Fei-Fei, L. (2016). Perceptual Losses for Real-Time Style Transfer and Super-Resolution. ECCV 2016.
[6] Liu, A., Lin, W., Narwaria, M. (2010). Image Quality Assessment Based on Gradient Similarity. IEEE TIP.
[7] Küçükdoğan, H., Barışkan, M.A. (2019). Just Noticeable Distortion Model in Image Quality Assessment: A Survey. Signal Processing: Image Communication.
[8] Küng, U., Koz, A., Dufaux, F. (2021). ICtCp Color Space for HDR Content. ITU-R BT.2100 Background Document.
[9] Sheikh, H.R., Bovik, A.C. (2006). Image information and visual quality. IEEE Transactions on Image Processing, 15(2), 430–444. (VIF)
[10] Bylinskii, Z., et al. (2019). What Do Different Evaluation Metrics Tell Us About Saliency Models? IEEE TPAMI 2019.

## §8 Glossary

| Term | Full Name | Description |
|------|-----------|-------------|
| AUC | Area Under ROC Curve | Area under ROC curve; saliency model evaluation metric |
| CSF | Contrast Sensitivity Function | HVS sensitivity to sinusoidal gratings at different spatial frequencies |
| CPD | Cycles Per Degree | Spatial frequency unit: cycles per degree of visual angle |
| HVS | Human Visual System | The complete visual processing system of the human eye and brain |
| JND | Just Noticeable Difference | The minimum perceivable distortion in the presence of a background signal |
| LPIPS | Learned Perceptual Image Patch Similarity | Deep feature-based perceptual similarity metric |
| LGN | Lateral Geniculate Nucleus | Visual relay nucleus in the thalamus |
| MOS | Mean Opinion Score | Average subjective quality rating across evaluators |
| NSS | Normalized Scanpath Saliency | Normalized saliency score at human fixation points |
| Perceptual Loss | — | Training loss based on deep VGG features |
| ROI | Region of Interest | Selected region of an image for focused processing |
| Saliency Map | — | Heat map predicting the distribution of human visual attention |
| SSIM | Structural Similarity Index | Perceptual image quality metric based on structural comparison |
| V1 | Primary Visual Cortex | First cortical area processing visual information |
| VIF | Visual Information Fidelity | Image quality metric based on natural scene statistics |
| Weber-Fechner Law | — | Logarithmic relationship between perception and stimulus intensity |
