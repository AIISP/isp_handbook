# Part 2, Chapter 04: Sharpening & Detail Enhancement

> **Pipeline position:** After Denoising; before Tone Mapping
> **Prerequisites:** Chapter 20 (Denoising), Chapter 19 (Demosaic)
> **Reader path:** Algorithm Engineer

---

## §1 Theory

### 1.1 What Is Sharpening

The human visual system is highly sensitive to local contrast near contours. The goal of sharpening algorithms is to amplify these local high-frequency components so that the detail blurred by the optical system, sensor pixel size, and demosaic interpolation can be recovered — increasing the perceived sharpness of the image.

**Frequency-domain perspective:** Sharpening is the complementary operation to denoising. Denoising suppresses noise by attenuating high-frequency components; sharpening enhances detail by boosting high-frequency components. The two operations are placed adjacent in the ISP pipeline (Denoising → Sharpening), forming a frequency balance:

$$
H_\text{sharp}(f) = 1 + \alpha \cdot (1 - H_\text{blur}(f))
$$

where $H_\text{blur}(f)$ is the transfer function of the low-pass filter and $\alpha$ is the sharpening strength. At low frequencies where $H_\text{blur}(f) \approx 1$, the gain is close to 1; at high frequencies where $H_\text{blur}(f) \approx 0$, the gain approaches $1 + \alpha$.

**Perceptual sharpness vs. MTF (Modulation Transfer Function):** MTF50 is defined as the spatial frequency at which contrast modulation drops to 50% (in units of lp/mm or lp/px). Sharpening raises MTF50 by amplifying mid-to-high frequency components, but excessive amplification produces halo artifacts. Perceived visual sharpness does not increase monotonically with MTF50; there is an upper bound on the optimal sharpening parameter.

### 1.2 Unsharp Masking (USM)

USM is the most widely used sharpening algorithm in ISP pipelines, originating from darkroom photography techniques (1930s–1970s).

**Mathematical derivation:**

Let the original image be $I$, and its convolution with a Gaussian kernel $G_\sigma$ of standard deviation $\sigma$ give the low-pass version (the "blur mask"):

$$
I_\text{blur} = G_\sigma * I
$$

The core idea is to add the "high-pass residual" (original minus blurred) back to the original:

$$
S = I + \alpha \cdot \underbrace{(I - I_\text{blur})}_{\text{high-frequency detail}}
$$

Rearranging gives the equivalent form:

$$
S = (1 + \alpha) \cdot I - \alpha \cdot G_\sigma * I
$$

This is equivalent to passing the original image through a **high-frequency boost filter**: low-frequency components are preserved (gain = 1) while high-frequency components are enhanced (gain = $1 + \alpha$).

**Threshold control:** To avoid amplifying noise in flat areas (where noise is uniformly distributed), a threshold parameter $T$ is introduced in practice:

$$
S(x,y) = \begin{cases}
I(x,y) + \alpha \cdot (I(x,y) - I_\text{blur}(x,y)) & \text{if } |I(x,y) - I_\text{blur}(x,y)| > T \\
I(x,y) & \text{otherwise}
\end{cases}
$$

A soft-threshold version (S-curve transition) can also be used to avoid the discontinuity of a hard cutoff.

**Summary of the three core parameters:**

| Parameter | Meaning | Typical range | Effect |
|------|------|---------|------|
| `amount` ($\alpha$) | High-frequency gain multiplier | 0.5–2.0 | Sharpening strength; too high causes halo |
| `radius` ($\sigma$) | Gaussian blur kernel radius (px) | 0.5–3.0 | Spatial scale of sharpening effect |
| `threshold` ($T$) | Minimum response of high-frequency residual | 0–30 (8-bit levels) | Textures below threshold are not sharpened |

### 1.3 Laplacian Sharpening

The Laplacian operator $\nabla^2 I = \frac{\partial^2 I}{\partial x^2} + \frac{\partial^2 I}{\partial y^2}$ is an isotropic second-order differential operator that produces symmetric positive and negative responses near edges:

$$
S = I - \lambda \cdot \nabla^2 I
$$

The subtraction sign arises because the Laplacian is negative (valley) on the bright side of a bright edge — subtracting it brightens the bright side — and positive (peak) on the dark side — subtracting it darkens the dark side. The result is bright and dark halos that increase the edge contrast.

In practice, a $3 \times 3$ or $5 \times 5$ Laplacian kernel is used in place of the continuous derivative:

$$
\text{Laplacian kernel:} \quad L = \begin{bmatrix} 0 & 1 & 0 \\ 1 & -4 & 1 \\ 0 & 1 & 0 \end{bmatrix}
$$

Laplacian sharpening is equivalent to USM in the limit $\sigma \to 0$, acting at a very small scale (1–2 pixels), and is typically used for sharpening fine textures.

### 1.4 Edge-Adaptive Sharpening

Applying global USM to flat regions (sky, walls, skin) amplifies noise, producing a "grainy" appearance. Edge-adaptive sharpening uses an edge strength mask to **boost high frequencies only where edges are detected**.

**Edge mask computation:**

The gradient magnitude is:

$$
|\nabla I| = \sqrt{\left(\frac{\partial I}{\partial x}\right)^2 + \left(\frac{\partial I}{\partial y}\right)^2}
$$

Normalized to obtain edge mask $M \in [0, 1]$:

$$
M(x,y) = \min\!\left(\frac{|\nabla I(x,y)|}{M_\text{max}},\; 1\right)
$$

**Adaptive sharpening synthesis:**

$$
S = I + \alpha \cdot M \cdot (I - G_\sigma * I)
$$

Full-strength sharpening is applied at strong edges ($M \approx 1$), while flat regions ($M \approx 0$) receive almost no sharpening.

**Advantages and costs:**
- Advantage: significantly suppresses noise amplification in flat regions
- Cost: requires additional gradient computation; the edge mask threshold must be tuned separately for different ISO values

### 1.5 Skin Protection

Over-sharpening of skin regions makes pores, fine lines, and skin texture appear artificially exaggerated ("rough skin" effect). Skin protection strategy:

1. **Skin color detection:** Use a chrominance ellipse in YCbCr or HSV space to identify skin-colored regions and produce a skin mask $M_\text{skin}$. Typical skin color range in YCbCr (8-bit): $Cb \in [77, 127]$, $Cr \in [133, 173]$.

2. **Reduce sharpening amount:** Scale `amount` to 30–50% of its original value in skin regions, keeping contours sharp while suppressing excessive amplification of pore detail.

3. **Skin-sharpening co-tuning:** In portrait scenes, eyes/eyelashes/hair (non-skin areas) typically call for strong sharpening, while cheeks/forehead (skin areas) should receive reduced sharpening.

### 1.6 Local Contrast Enhancement (LCE)

LCE and sharpening operate at different frequency scales:

| Characteristic | Sharpening (USM) | Local Contrast Enhancement |
|------|-----------------|---------------------------|
| Operating frequency | High (detail, edges, 0.5–3 px scale) | Mid-frequency (texture blocks, 10–50 px scale) |
| Goal | Recover MTF loss | Enhance tonal separation, haze removal |
| Typical operator | Difference of Gaussians (DoG) | Guided filter, bilateral decomposition |
| Primary artifact | Halo (at fine edges) | Gradient reversal (large-scale halo) |

Common LCE algorithms:

**Guided Filter-based LCE:**

$$
I = I_\text{base} + I_\text{detail}
$$

$$
S_\text{LCE} = I_\text{base} + \beta \cdot I_\text{detail}
$$

where $I_\text{base}$ is the low-frequency layer extracted by a guided filter, $I_\text{detail}$ is the high-frequency residual, and $\beta > 1$ enhances detail.

**CLAHE (Contrast Limited Adaptive Histogram Equalization):** Computes a histogram equalization mapping block by block, then blends adjacent block results with bilinear interpolation. Contrast enhancement is achieved while suppressing noise amplification via a maximum slope limit (Clip Limit).

### 1.7 Algorithm Pseudocode

```
Algorithm: Edge-Adaptive USM Sharpening
Input:  float32 RGB image I[H,W,3] in [0,1]
        amount α, radius σ (px), threshold T, edge_mask_threshold τ
Output: sharpened image S[H,W,3]

1. Convert to luminance for edge detection:
   Y = 0.299*I[:,:,0] + 0.587*I[:,:,1] + 0.114*I[:,:,2]

2. Compute Gaussian blur:
   I_blur = GaussianFilter(I, sigma=σ)

3. Compute high-frequency residual:
   residual = I - I_blur                    // shape [H,W,3]

4. Compute edge magnitude on Y channel:
   grad_y  = Sobel(Y, axis=0)
   grad_x  = Sobel(Y, axis=1)
   edge_mag = sqrt(grad_x^2 + grad_y^2)
   edge_mask = edge_mag / (max(edge_mag) + ε)  // normalize to [0,1]

5. Apply threshold on residual (suppress weak textures):
   residual_thresh = residual * (|residual| > T)

6. Compute adaptive sharpening:
   boost = α * edge_mask[:,:,newaxis] * residual_thresh
   S = clip(I + boost, 0, 1)

7. Return S
```

---

## §2 Calibration

### 2.1 Sharpness Quantification and MTF50

**MTF (Modulation Transfer Function)** describes the ability of an imaging system to transfer contrast at different spatial frequencies. MTF50 — the spatial frequency at which contrast drops to 50% — is the most widely used single-number resolution metric:

$$
\text{MTF}(f) = \frac{C_\text{output}(f)}{C_\text{input}(f)}, \quad C = \frac{I_\text{max} - I_\text{min}}{I_\text{max} + I_\text{min}}
$$

**Slanted Edge Method (ISO 12233):**

The ISO 12233 test chart contains black-and-white edge targets tilted approximately 5° relative to the sensor rows and columns. By performing sub-pixel alignment and super-resolution reconstruction on the slanted edge, an ESF (Edge Spread Function) finer than the Nyquist frequency is obtained; its derivative gives the LSF (Line Spread Function), which is Fourier-transformed to yield the MTF curve.

**Calibration procedure:**

```
Step 1: Capture an ISO 12233 or Siemens Star test chart
  - Illuminate uniformly with a standard light source (D65 lightbox)
  - Fix camera parameters: low ISO (minimize noise), precise focus
  - Capture ≥3 frames and average the MTF (to suppress random noise)

Step 2: Compute pre-sharpening MTF50
  - Extract the slanted-edge ROI from the ISO 12233 chart
  - Compute the MTF curve using imatest or sfr_edge
  - Record the MTF50 baseline (in lp/px or lp/mm)

Step 3: Apply sharpening and repeat MTF measurement
  - Apply USM to the same image (sweep amount and radius)
  - Plot MTF50 vs. amount; find the maximum amount before halos become visible

Step 4: Visual inspection combined with MTF calibration
  - Visually inspect the center of the Siemens Star for visible halos
  - Record the halo-free maximum MTF50 as the tuning upper bound
```

### 2.2 Siemens Star Test Chart

The Siemens Star consists of concentric isogonal wedge sectors; spatial frequency increases toward the center until it exceeds the Nyquist limit.
- **Sharpening effect assessment:** Observe how the width of the aliasing ring in the center of the Siemens Star changes.
- **Halo detection:** Observe bright/dark overshoots at the edges of the wedge sectors.

### 2.3 Calibration Parameter Record

| Parameter set | MTF50 (lp/px) | Visible halo | SSIM | Notes |
|---------|--------------|-----------|------|------|
| No sharpening (α=0) | Baseline | None | 1.000 | Reference baseline |
| Weak (α=0.5, σ=1.5) | Baseline+X% | None | ≈0.995 | Recommended for everyday scenes |
| Medium (α=1.0, σ=1.5) | Baseline+Y% | Barely visible | ≈0.985 | Standard setting |
| Strong (α=2.0, σ=1.5) | Baseline+Z% | Visible | Drops significantly | Only for print/crop |

> Note: X/Y/Z values must be filled in from actual sensor measurements; MTF50 gain varies significantly with the amount of lens blur.

---

## §3 Tuning

### 3.1 USM Parameter Tuning Table

| Parameter | Conservative (weak) | Standard | Aggressive (strong) | Tuning principle |
|------|----------|------|----------|---------|
| `amount` | 0.3–0.5 | 0.8–1.2 | 1.5–2.5 | Fix radius first, then adjust amount |
| `radius` (px) | 0.5–1.0 | 1.0–2.0 | 2.0–3.5 | Match to target detail scale |
| `threshold` | 2–5 | 8–15 | 20–30 | Higher ISO requires higher threshold |
| `edge_mask_thr` | 0.05 | 0.1 | 0.2 | Affects extent of edge protection |

**Recommended tuning sequence:**
1. Set `amount=0`; confirm the MTF50 baseline with the Siemens Star.
2. Fix `radius=1.5` (empirical value for most 1/2.3"–1" sensors), sweep `amount` until halos just begin to appear.
3. Reduce that amount by 20%, then decrease `threshold` until noise in flat regions starts to coarsen.
4. Increase threshold by 30% as the final baseline parameter.

### 3.2 ISO-Adaptive Sharpening

At high ISO, stronger image noise causes USM to amplify noise granules as well, producing a "crunchy" grainy appearance. Sharpening strength should be automatically reduced with increasing ISO:

$$
\alpha_\text{ISO} = \alpha_\text{base} \cdot \max\!\left(1 - \frac{\log_2(ISO / ISO_\text{base})}{\Delta_\text{ISO}},\; \alpha_\text{min}\right)
$$

Typical parameters: $\alpha_\text{base} = 1.0$, $ISO_\text{base} = 100$, $\Delta_\text{ISO} = 5$ (reduces to 0 at 5 stops above base), $\alpha_\text{min} = 0.2$.

**ISO reference values:**

| ISO | Recommended amount | Recommended threshold | Notes |
|-----|------------|---------------|------|
| 50–200 | 1.0–1.5 | 5–10 | Low noise; aggressive sharpening acceptable |
| 400–800 | 0.7–1.0 | 10–15 | Moderate sharpening; raise threshold |
| 1600–3200 | 0.4–0.7 | 15–22 | Noise reduction priority; significantly raise threshold |
| 6400+ | 0.2–0.4 | 22–30 | Minimal sharpening; rely primarily on edge mask |

### 3.3 Content-Adaptive Tuning

**Scene types and sharpening strategies:**

| Scene | Recommended strategy | Special considerations |
|------|---------|---------|
| Landscape / architecture | Global strong sharpening (amount=1.5, σ=1.5) | Watch for noise amplification in sky regions |
| Portrait | Edge-adaptive + skin protection (amount=0.5 on skin) | Can locally boost eyes/hair |
| Macro / product | Small radius (σ=0.8–1.0) for fine sharpening | Avoid over-sharpening surface material texture |
| Night / low light | Very low amount or off; amount ≤ 0.3 | Noise amplification risk is extreme |
| Video | 30–50% lower than stills (video magnifies inter-frame flicker) | Ensure per-frame parameter consistency |

### 3.4 Halo Threshold

Halo (overshoot) is the most typical artifact of over-sharpening: white overshoot on the bright side of a high-contrast edge and black overshoot on the dark side. Halo visibility is positively correlated with:

- **Excessive `amount`:** Values > 2.0 almost always produce visible halos.
- **Large `radius`:** Radius > 3 px makes halos spatially wider and more noticeable.
- **High edge contrast:** High-contrast edges (e.g., black-and-white lines) are more prone to halos than low-contrast ones.

**Halo detection condition (empirical formula):**

$$
\text{Halo visible} \iff \alpha \cdot (1 - e^{-\sigma^2/2}) > \text{Halo}_{thr} \approx 0.05 \text{ (normalized)}
$$

In practice, visibility is confirmed by visual scoring: a trained evaluator can detect overshoots of 5–8 levels (8-bit) on a standard display at 100% zoom.

---

## §4 Artifacts

### 4.1 Oversharpening Halo

**Appearance:** Bright white rings and dark black rings appear on either side of high-contrast edges (tree branches, building outlines), resembling badly processed black-and-white photographic prints.

**Cause:** The high-frequency residual of USM is largest in magnitude at edges. If $\alpha$ is too large, the bright side exceeds 1 after addition (clipped to a bright stripe) and the dark side drops below 0 (clipped to a dark stripe). Even without clipping, the enhanced bright-dark contrast on either side of the edge is perceptually noticeable.

**Mitigation:**
- Reduce `amount` (most direct)
- Reduce `radius` (narrows the halo width)
- Introduce halo clamping: limit `boost = clip(α*residual, -H_max, +H_max)`
- Use an edge-adaptive mask that restricts the boost to the edge center rather than extending beyond the edge

### 4.2 Noise Amplification

**Appearance:** After sharpening, flat regions (sky, walls) show clearly visible granularity; noise dots become "crunchy." This is especially pronounced at high ISO.

**Cause:** The high-frequency residual $I - G_\sigma * I$ contains noise spectral components whenever noise is present; multiplying by $\alpha$ amplifies the noise by the same factor.

**Mitigation:**
- Increase `threshold` (most common), preventing low-amplitude residuals (which contain noise) from being amplified
- Denoise before sharpening (the ISP pipeline is already designed this way)
- Automatically reduce `amount` at high ISO (§3.2 ISO-adaptive)
- Use an edge-adaptive mask to protect flat regions

### 4.3 Ringing

**Appearance:** Ripple-like bright-dark oscillating fringes near sharp edges, rather than a single halo overshoot. Usually visible near the high-frequency end corresponding to the sharpening `radius`.

**Cause:** Gibbs phenomenon — when an ideal sharpening response is approximated by a finite-bandwidth filter (including a Gaussian kernel), the spatial oscillations at edges result from frequency-domain truncation. Equivalently, the frequency response of USM may not be monotone at the high-frequency end and can exhibit gain peaks, amplifying certain frequency components of the ringing.

**Mitigation:**
- Use a Gaussian kernel (smoother frequency-domain rolloff than a rectangular kernel)
- Avoid `radius < 0.5` (very small kernels produce stronger frequency-domain truncation oscillations)
- Apply mild post-sharpening low-pass smoothing (at the cost of slight detail loss)

### 4.4 Skin Crunchiness

**Appearance:** In portraits, pores and fine lines on facial skin are excessively amplified, making the skin look like orange-peel texture — unnatural and lacking the qualities of real skin. Common when an automatic skin-softening feature is absent.

**Cause:** Skin texture spatial frequencies happen to fall in the range where USM provides the strongest boost (σ=1–2 px), and the local contrast of skin regions is sufficient to exceed `threshold` and be fully amplified.

**Mitigation:**
- Skin detection + skin protection mask (§1.5)
- Reduce `amount` and/or increase `threshold` separately in portrait mode
- After skin smoothing, restrict sharpening gain in the skin frequency range

---

## §5 Evaluation

### 5.1 MTF50 Measurement (Before and After Sharpening)

**Procedure:**
1. Capture "no sharpening" and "sharpened" images of an ISO 12233 chart under identical lighting and camera conditions.
2. Compute MTF50 for both images using the slanted-edge algorithm (sfr_edge / imatest).
3. Report the MTF50 improvement (as a percentage) and the MTF curve shape.

**Typical results:** Weak sharpening (amount=0.5) improves MTF50 by approximately 10–20%; medium sharpening (amount=1.0) by 25–40%; strong sharpening (amount=2.0) can reach 50–70%, but typically accompanied by visible halos.

### 5.2 SSIM (Structural Similarity Index)

SSIM jointly measures luminance, contrast, and structural similarity — a better proxy for human perception than PSNR:

$$
\text{SSIM}(x, y) = \frac{(2\mu_x\mu_y + c_1)(2\sigma_{xy} + c_2)}{(\mu_x^2 + \mu_y^2 + c_1)(\sigma_x^2 + \sigma_y^2 + c_2)}
$$

**Key reasons why over-sharpening reduces SSIM:**

- Halos introduce bright/dark biases near edges, affecting the local mean term $\mu_x$.
- Noise amplification increases local variance $\sigma_x^2$, but the covariance $\sigma_{xy}$ with the reference image decreases.
- Net effect: even when the image "looks sharper," SSIM is often lower than for the original or a lightly sharpened version.

**Observed patterns (reference values):**

| Sharpening strength | PSNR (dB) | SSIM | Subjective score (MOS) |
|---------|----------|------|--------------|
| No sharpening | — (reference) | 1.000 | 3.0/5 |
| Weak (α=0.5) | ↓ ~1–2 dB | ≈0.992 | 4.0/5 |
| Medium (α=1.0) | ↓ ~3–4 dB | ≈0.975 | 4.3/5 (peak) |
| Strong (α=2.0) | ↓ ~6–8 dB | ≈0.940 | 3.5/5 (declining) |

> Note: PSNR decreases because the reference (ground truth) contains no halos; both SSIM and MOS peak at medium sharpening and decline together with excessive sharpening.

### 5.3 Subjective Scoring (MOS Studies)

Subjective image quality assessment (Mean Opinion Score) is the gold standard in perceptual sharpness research.

**ACR (Absolute Category Rating) method:**
- Observers view images on a calibrated display (D65 white point, approximately 120 cd/m²).
- Each image is rated on a 5-point scale (1 = poor, 5 = excellent).
- At least 15 observers; the mean is the MOS.

**Evaluation criteria:**
- Edge sharpness (primary objective)
- Texture naturalness (avoid skin crunchiness, noisy grain)
- Halo visibility (negative scoring factor)
- Overall image quality (composite impression)

**Common datasets:**

| Dataset | Content | Notes |
|--------|------|------|
| LIVE IQA | 779 distorted images (including blur/sharpening) | With MOS annotations; suitable for algorithm evaluation |
| KADID-10k | 10125 distorted images (81 distortion types) | Large-scale; includes sharpening-type distortions |
| TID2013 | 3000 distorted images (24 distortion types) | Bi-directional test (sharpening + under-sharpening) |

---

## §6 Code

See *See §6 Code section for runnable examples.*

---

## References

1. **Russ, J. C.** (2011). *The Image Processing Handbook*, 6th ed. CRC Press. — Chapter 8 covers the history and implementation of USM in detail, including its darkroom photography origins (1930s) and digital adoption (1970s Photoshop).

2. **Gonzalez, R. C., & Woods, R. E.** (2018). *Digital Image Processing*, 4th ed. Pearson. — §3.6 on sharpening filters, covering the complete mathematical derivation of the Laplacian operator and USM.

3. **ISO 12233:2017.** Photography — Electronic still picture imaging — Resolution and spatial frequency responses. International Organization for Standardization. — International standard for MTF measurement; defines the slanted-edge method.

4. **Ferzli, R., & Karam, L. J.** (2009). A no-reference objective image sharpness metric based on the notion of just noticeable blur (JNB). *IEEE Transactions on Image Processing*, 18(4), 717–728. — JNB no-reference sharpness metric; quantifies the just-noticeable blur threshold.

5. **Wang, Z., Bovik, A. C., Sheikh, H. R., & Simoncelli, E. P.** (2004). Image quality assessment: From error visibility to structural similarity. *IEEE Transactions on Image Processing*, 13(4), 600–612. — Original SSIM paper; analyzes the effect of sharpening and blur on image quality metrics.

6. **Polesel, A., Ramponi, G., & Mathews, V. J.** (2000). Image enhancement via adaptive unsharp masking. *IEEE Transactions on Image Processing*, 9(3), 505–510. — Adaptive USM, dynamically adjusting sharpening strength based on local variance; a classic implementation of edge-adaptive sharpening.

7. **He, K., Sun, J., & Tang, X.** (2013). Guided image filtering. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 35(6), 1397–1409. — Guided filter, the core tool for LCE; excellent edge preservation and fast execution.

8. **Pizer, S. M., et al.** (1987). Adaptive histogram equalization and its variations. *Computer Vision, Graphics, and Image Processing*, 39(3), 355–368. — Original CLAHE paper; the contrast-limited extension of adaptive histogram equalization.

9. **Kuo, C. J., & Tsai, C. M.** (2012). *Principles of Digital Image Synthesis.* — Includes a detailed derivation of skin detection in YCbCr (ellipse model).

10. **Barten, P. G. J.** (1999). *Contrast Sensitivity of the Human Eye and Its Effects on Image Quality.* SPIE Press. — Human contrast sensitivity function (CSF); explains the nonlinear relationship between perceived sharpness and MTF50.

---

*Chapter 21 of the ISP Algorithm Handbook — Part 2: Traditional ISP Algorithms*
