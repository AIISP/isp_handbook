# Part 1, Chapter 07: Dynamic Range and HDR Algorithms

> **Pipeline position:** After sensor physics (Ch03); multi-frame fusion and global tone mapping stages in the ISP pipeline
> **Prerequisites:** Chapter 03 (Image Sensor Physics), Chapter 04 (Noise Models)
> **Reader path:** Algorithm Engineers, System Designers, Tuning Engineers

---

## §1 Theory

### 1.1 Dynamic Range Fundamentals

**Definition.** Dynamic range (DR) quantifies the ratio between the maximum and minimum luminance a system can faithfully capture or display:

$$\text{DR} = 20 \times \log_{10}\!\left(\frac{L_{\max}}{L_{\min}}\right) \quad [\text{dB}]$$

Because photographers prefer exposure-stop notation, the same quantity expressed in EV (exposure values) is:

$$\text{DR}_{\text{EV}} = \log_2\!\left(\frac{L_{\max}}{L_{\min}}\right) \quad [\text{stops}], \qquad 1\ \text{EV} \approx 6\ \text{dB}$$

**Human visual system.** The human eye achieves roughly 12–14 EV instantaneously within a single fixation (pupil adaptation takes ~200 ms). Over the full range of dark adaptation — from starlight to sunlight — it spans approximately 24 EV. This remarkable range is enabled by:
- Dual-receptor architecture (rods + cones)
- Local contrast normalization in the retina (lateral inhibition)
- Pupil dilation/constriction (~10× gain, ~3.3 EV)
- Neural gain control in V1

**Real-scene examples.**

| Scene | Approximate DR |
|---|---|
| Overcast indoor | 6–8 EV |
| Indoor with window | ~13 EV |
| Noon outdoor, open shadow | ~17 EV |
| Sunlit snow + deep cave entrance | >20 EV |
| Night street with headlights | ~14 EV |

**Sensor dynamic range limitations.** As established in Chapter 03 §1.5.3, the sensor DR is governed by the full-well capacity $N_{\text{sat}}$ (shot noise at saturation) and the read noise floor $\sigma_{\text{read}}$:

$$\text{DR}_{\text{sensor}} = 20 \times \log_{10}\!\left(\frac{N_{\text{sat}}}{\sigma_{\text{read}}}\right)$$

A typical mobile sensor achieves 70–76 dB (~11–12 EV) at base ISO, falling to 50–55 dB at high ISO where read noise dominates. This is the central motivation for multi-exposure HDR capture.

**Zone System (Ansel Adams).** Adams's Zone System maps scene luminance to eleven discrete exposure zones:

| Zone | Description | Reflectance |
|---|---|---|
| 0 | Pure black, no texture | 0% |
| I | Near black, slight tonality | ~1% |
| II | Textured black (dark leather) | ~2.5% |
| III | Dark shadow with texture | ~5% |
| IV | Dark foliage, shadow side | ~10% |
| **V** | **18% gray, average exposure** | **18%** |
| VI | Light skin, concrete in sun | ~36% |
| VII | Light gray, snow in shadow | ~72% |
| VIII | Textured whites (snow) | ~90% |
| IX | Near white, slight texture | ~96% |
| X | Pure white, specular | 100% |

Zone V (18% gray) is the calibration anchor for photographic exposure meters and is the standard target for AWB and AE algorithms. HDR algorithms must map the full zone range to a renderable output without crushing shadow or clipping highlight texture.

---

### 1.2 Multi-Exposure HDR Fusion

When scene DR exceeds sensor DR, the standard strategy is to capture a **bracketed exposure sequence** $\{I_j\}_{j=1}^{N}$ with exposure times $\{\Delta t_j\}$ spanning the scene luminance range, then fuse them into a single high-DR image.

#### 1.2.1 Debevec-Malik Method (1997)

**Core insight.** If the camera response function (CRF) $f$ maps radiance $E$ to pixel value $Z$:

$$Z_{ij} = f(E_i \cdot \Delta t_j)$$

then taking the log-inverse $g = \ln f^{-1}$:

$$g(Z_{ij}) = \ln E_i + \ln \Delta t_j$$

We know $Z_{ij}$ (observed pixel values) and $\ln \Delta t_j$ (shutter times), and we want to recover both $g(\cdot)$ and the HDR radiance values $\ln E_i$. This is an **over-determined least-squares** problem for pixel $i$ across $j$ exposures.

**Objective function:**

$$\min_{g,\, \ln E_i} \sum_{i=1}^{N_p} \sum_{j=1}^{N_e} w(Z_{ij})\bigl[g(Z_{ij}) - \ln E_i - \ln \Delta t_j\bigr]^2 + \lambda \sum_{z=1}^{254} \bigl[g''(z)\bigr]^2$$

where the second term is a smoothness regularizer on $g$.

**Weight function.** Over- and under-exposed pixels carry less information; the standard hat-shaped weight:

$$w(z) = \begin{cases} z - Z_{\min} & z \leq \frac{Z_{\min}+Z_{\max}}{2} \\ Z_{\max} - z & z > \frac{Z_{\min}+Z_{\max}}{2} \end{cases}$$

**HDR radiance map.** Once $g$ is estimated, the final HDR radiance is computed as a weighted average across all valid exposures:

$$\ln E_i = \frac{\sum_j w(Z_{ij})\bigl[g(Z_{ij}) - \ln \Delta t_j\bigr]}{\sum_j w(Z_{ij})}$$

**Practical notes.**
- Requires at least $N_p \geq P$ sample pixels, where $P = 256$ (8-bit range), typically $N_p = 50$–200 sparse pixels suffice.
- Color cameras solve three independent 1D CRFs (R, G, B channels).
- Exposure ratio 1:4 (2 EV step) is common; smaller steps reduce ghosting risk but require more frames.

#### 1.2.2 Mertens Multi-Exposure Fusion (2007)

Mertens et al. proposed bypassing CRF estimation entirely by fusing LDR images **directly in image space** using a quality-weighted Laplacian pyramid blend. This is computationally simpler and more robust to CRF estimation errors.

**Three quality metrics per pixel $(i,j)$ in image $k$:**

1. **Contrast** $C_k(i,j)$: absolute value of the Laplacian response, measuring local structure richness.

$$C_k(i,j) = \bigl|\nabla^2 I_k(i,j)\bigr|$$

2. **Saturation** $S_k(i,j)$: standard deviation of R, G, B channels, penalizing desaturated (blown or black) regions.

$$S_k(i,j) = \sqrt{\frac{1}{3}\sum_{c} \bigl(I_k^c(i,j) - \bar{I}_k(i,j)\bigr)^2}$$

3. **Well-exposedness** $E_k(i,j)$: Gaussian centered at 0.5 (mid-tone), rewarding pixels close to optimal exposure.

$$E_k(i,j) = \exp\!\left(-\frac{(I_k(i,j) - 0.5)^2}{2\sigma_e^2}\right), \quad \sigma_e = 0.2$$

**Combined weight map:**

$$\tilde{W}_k(i,j) = C_k(i,j)^{w_C} \cdot S_k(i,j)^{w_S} \cdot E_k(i,j)^{w_E}$$

Normalized: $W_k = \tilde{W}_k / \sum_k \tilde{W}_k$.

**Multi-resolution blending.** To avoid seam artifacts at weight boundaries, weights and images are blended via Laplacian pyramids:

$$\mathcal{L}\{R\}_l = \sum_k W_k^l \cdot \mathcal{L}\{I_k\}_l$$

where $l$ denotes the pyramid level. The final result is reconstructed by collapsing the pyramid.

**Comparison with Debevec-Malik:**

| Aspect | Debevec-Malik | Mertens Fusion |
|---|---|---|
| CRF estimation | Required | Not required |
| Output | HDR radiance (float32) | LDR-space blend (uint8/16) |
| Tone mapping | Separate step needed | Implicit in weighting |
| Computational cost | Higher | Lower |
| Scene motion | Both equally sensitive | Slightly more robust |
| Color accuracy | Physics-grounded | Empirically tuned |

#### 1.2.3 Motion Alignment Problem

Bracketed exposures introduce inter-frame motion from:
- **Rolling shutter distortion:** each exposure row captured at slightly different time
- **Hand tremor:** even with OIS, ~0.3–1 px residual at 50ms bracket interval
- **Scene motion:** people, vehicles, leaves, water

Unaligned fusion produces **ghosting artifacts** — doubled edges or translucent moving objects.

**Optical flow alignment.** Dense optical flow $\mathbf{v}(x,y)$ warps each non-reference exposure toward the reference:

$$I_k^{\text{aligned}}(x,y) = I_k\bigl(x + v_x(x,y),\ y + v_y(x,y)\bigr)$$

Modern approaches use deep flow networks (PWC-Net, RAFT) operating on the LDR stack, achieving sub-pixel accuracy in <10ms on mobile SoCs.

**Ghost detection.** After alignment, residual ghosting is detected via pixel-wise consistency:

$$\text{ghost}(x,y) = \mathbf{1}\!\left[\bigl|I_k^{\text{aligned}}(x,y) - I_{\text{ref}}(x,y)\bigr| > \tau\right]$$

Ghost pixels are excluded from the fusion weight (set to zero) or down-weighted. AHDRNet (§1.5) replaces this heuristic with learned attention masks.

---

### 1.3 Tone Mapping

Tone mapping operators (TMOs) compress the wide dynamic range of an HDR radiance map into the displayable range [0, 1] while preserving perceptual detail.

#### 1.3.1 Global Operators

Global TMOs apply the same monotone function to every pixel, regardless of spatial context.

**Reinhard (2002) — photographic tone reproduction:**

$$L_d = \frac{L_w}{1 + L_w}$$

where $L_w$ is the world luminance normalized by the scene key (log-average luminance). A parametric extension introduces $L_{\text{white}}$, the luminance that maps to 1:

$$L_d = \frac{L_w\!\left(1 + \frac{L_w}{L_{\text{white}}^2}\right)}{1 + L_w}$$

At $L_w \ll L_{\text{white}}$, this reduces to the basic form; at $L_w = L_{\text{white}}$, output approaches 1.

**Drago logarithmic (2003):**

$$L_d = \frac{L_{\max}/100}{\log_{10}(L_{\max}+1)} \cdot \frac{\log(L_w + 1)}{\log\!\left(2 + 8\bigl(\frac{L_w}{L_{\max}}\bigr)^{\log b / \log 0.5}\right)}$$

Parameter $b \in [0.6, 0.9]$ controls the compression bias, with higher values preserving more shadow detail.

**Mantiuk et al. (2006)** models the full human visual system response including contrast sensitivity functions, display luminance, and adaptation levels. Computationally heavier but perceptually optimal for calibrated HDR displays.

#### 1.3.2 Local Operators

Local TMOs adapt the compression at each pixel based on its spatial neighborhood, producing more natural-looking results at the cost of potential **halo artifacts**.

**Bilateral filter decomposition (Durand & Dorsey, 2002):**

1. Decompose $\log L$ into base layer $B$ (large-scale illumination) and detail layer $D$:
   $$B = \text{BilateralFilter}(\log L), \quad D = \log L - B$$
2. Compress only the base layer: $B' = \gamma \cdot B$, where $\gamma < 1$
3. Reconstruct: $L_d = \exp(B' + D)$

The bilateral filter preserves edges (unlike Gaussian smoothing), so the halos are reduced. However, strong compression can still produce halo ringing at high-contrast edges.

#### 1.3.3 Image-Adaptive 3D LUT (Zeng et al., CVPR 2020)

A 3D LUT maps each input RGB triplet $(r, g, b)$ to an output triplet via trilinear interpolation in a $N\times N\times N$ table (typically $N=33$). Fixed 3D LUTs are scene-agnostic.

Zeng et al. make the LUT adaptive by predicting a **linear combination of $K$ basis LUTs** from image statistics:

$$\text{LUT}_{\text{adaptive}} = \sum_{k=1}^{K} w_k \cdot \text{LUT}_k$$

A lightweight MobileNet backbone (operating at $128\times 128$) predicts the blending weights $\{w_k\}_{k=1}^{K}$ from the input image. Key properties:

- Fully differentiable through trilinear interpolation
- $K=3$ basis LUTs sufficient for most photographic transformations
- Model size $<1$ MB; inference $<1$ ms at 1080p on GPU
- Can represent any invertible color transform (tone, color, saturation)

The differentiable 3D LUT application:

```python
def apply_lut_3d(lut, image):
    """
    lut: (N, N, N, 3) float32 LUT table
    image: (H, W, 3) float32 in [0, 1]
    returns: (H, W, 3) transformed image
    """
    N = lut.shape[0]
    # Scale image coords to LUT index space
    img_scaled = image * (N - 1)
    # Integer floor indices
    idx = img_scaled.astype(int).clip(0, N - 2)
    # Fractional weights
    frac = img_scaled - idx
    fr, fg, fb = frac[..., 0], frac[..., 1], frac[..., 2]
    ir, ig, ib = idx[..., 0], idx[..., 1], idx[..., 2]
    # Trilinear interpolation
    c000 = lut[ir,   ig,   ib  ]
    c100 = lut[ir+1, ig,   ib  ]
    c010 = lut[ir,   ig+1, ib  ]
    c001 = lut[ir,   ig,   ib+1]
    c110 = lut[ir+1, ig+1, ib  ]
    c101 = lut[ir+1, ig,   ib+1]
    c011 = lut[ir,   ig+1, ib+1]
    c111 = lut[ir+1, ig+1, ib+1]
    out = (c000 * (1-fr)*(1-fg)*(1-fb) +
           c100 * fr*(1-fg)*(1-fb) +
           c010 * (1-fr)*fg*(1-fb) +
           c001 * (1-fr)*(1-fg)*fb +
           c110 * fr*fg*(1-fb) +
           c101 * fr*(1-fg)*fb +
           c011 * (1-fr)*fg*fb +
           c111 * fr*fg*fb)
    return out
```

---

### 1.4 HDRNet: Deep Bilateral Learning (Gharbi et al., SIGGRAPH 2017)

**Reference:** Gharbi, M., Chen, J., Barron, J. T., Hasinoff, S. W., & Durand, F. (2017). Deep Bilateral Learning for Real-Time Image Enhancement. *ACM SIGGRAPH 2017 (TOG)*.
GitHub: https://github.com/google/hdrnet

#### 1.4.1 Motivation

Global tone curves apply the same mapping to every pixel regardless of spatial context. This fails in several important cases:

- **Noise visibility:** in textured regions, noise is masked by texture; in smooth sky regions, the same noise is conspicuous. A global curve applies identical denoising strength everywhere.
- **Local exposure:** a portrait where the subject is properly exposed but the background is blown requires spatially-varying compression.
- **Color correction:** skin tones may need different correction than sky or foliage in the same image.

**Bilateral grid (Paris & Durand, 2006).** The bilateral grid lifts a 2D image into a 3D space $(x, y, \ell)$ where $\ell$ is luminance. Linear convolutions in this 3D space yield edge-aware (bilateral) filtering when sliced back to 2D: pixels at the same spatial location but different luminance (i.e., across a sharp edge) are processed independently.

**HDRNet** replaces hand-crafted bilateral filters with **learned bilateral grid coefficients** predicted by a CNN, achieving arbitrary per-pixel adaptive transforms while maintaining the edge-preserving property of the bilateral grid. The key innovation: run the expensive CNN at low resolution, then apply results at full resolution via differentiable slicing — cost is nearly independent of output resolution.

#### 1.4.2 Architecture Overview

```
Input (full-res, H×W×3)
        │
        ├──────────────────────────┐
        │ Downsample to 256×256    │ Full-res pass-through
        │                          │
        ▼                          ▼
   S-Net (Low-res)          Guidance Network
   256×256×3 → ...          H×W×3 → H×W×1
        │                          │
        ▼                          │
   Bilateral Grid                  │
   [B, 8, 16, 12, 12]              │
        │                          │
        └──────────┬───────────────┘
                   ▼
            Slicing Layer
         (trilinear interpolation)
                   │
                   ▼
         Per-pixel Affine Coeffs
              [B, H, W, 12]
                   │
                   ▼  + full-res input
         Per-pixel Affine Transform
              [B, H, W, 3]
                   │
                   ▼
           Enhanced Output
```

#### 1.4.3 Low-Resolution S-Net (Layer-by-Layer)

Input: $256 \times 256 \times 3$ downsampled image.

**Local feature extraction (Splat pathway):**

```
Conv(3→16,   3×3, stride=1, BN, ReLU) → 256×256×16
Conv(16→32,  3×3, stride=2, BN, ReLU) → 128×128×32
Conv(32→64,  3×3, stride=2, BN, ReLU) →  64×64×64
Conv(64→64,  3×3, stride=2, BN, ReLU) →  32×32×64
Conv(64→64,  3×3, stride=2, BN, ReLU) →  16×16×64
```

**Global feature extraction:**

```
GlobalAvgPool → 64
FC(64→64, ReLU)
FC(64→64, ReLU)
FC(64→64, ReLU)
```

The global features are broadcast and concatenated with the local $16\times16\times64$ features, enabling the network to condition local decisions on the overall scene statistics (e.g., globally bright outdoor scenes vs. dark indoor scenes).

**Bilateral grid output:**

```
Conv(128→96, 1×1, BN, ReLU) → 16×16×96
Reshape → [B, 8, 16, 12, 12]
```

**Bilateral grid dimension breakdown:**
- Spatial: $12\times12$ (after reshape; note the 16×16 conv output is reshaped with depth absorbing some spatial)
- Luminance depth: 8 slices covering [0, 1] luminance range
- Per-cell coefficients: 12 values = a $3\times4$ affine matrix (3 output channels, 4 inputs = R, G, B, 1)

Total bilateral grid: $8 \times 12 \times 12 \times 12 = 13{,}824$ coefficients per image.

#### 1.4.4 Full-Resolution Guidance Network

The guidance network produces a single-channel **luminance proxy map** at full resolution, which is used to index into the luminance (depth) dimension of the bilateral grid during slicing:

```python
# Guidance network architecture
# Input: full-resolution RGB (H, W, 3)
x = Conv2d(3, 1, kernel_size=1)(input)    # (H, W, 1)
x = BatchNorm2d(1)(x)
x = ReLU()(x)
x = Conv2d(1, 1, kernel_size=1)(x)        # (H, W, 1)
guidance = Tanh()(x) * 0.5 + 0.5          # (H, W, 1), range [0, 1]
```

**Why learnable vs. fixed gray-world luminance.** A fixed luminance conversion (e.g., $\ell = 0.299R + 0.587G + 0.114B$) is designed for colorimetric accuracy, not for driving edge-aware processing. A learned $1\times1$ convolution can discover a task-optimal luminance proxy — for example, weighting red channel more for portrait skin-edge detection, or blue channel for sky-horizon segmentation. The tanh activation prevents saturation in extreme-luminance regions and keeps the guidance gradient-friendly during training.

#### 1.4.5 Slicing Operation

The slicing operation performs **trilinear interpolation** of the bilateral grid at coordinates determined by the spatial position $(x, y)$ and the per-pixel guidance value (luminance proxy):

```python
import torch
import torch.nn.functional as F

def bilateral_slice(bilateral_grid, guide):
    """
    bilateral_grid: [B, 12, 8, H_grid, W_grid]  # (coeff, depth, h, w)
    guide:          [B, H, W]                     # in [0, 1]
    returns:        [B, H, W, 12]                 # full-res affine coefficients
    """
    B, H, W = guide.shape
    H_grid, W_grid = bilateral_grid.shape[-2], bilateral_grid.shape[-1]

    # Normalized spatial coordinates in [-1, 1] for grid_sample
    xs = (torch.arange(W, dtype=torch.float32, device=guide.device) + 0.5) / W
    ys = (torch.arange(H, dtype=torch.float32, device=guide.device) + 0.5) / H
    grid_y, grid_x = torch.meshgrid(ys, xs, indexing='ij')

    # Depth coordinate from guidance (guide in [0,1] → z in [-1,1])
    z = guide * 2.0 - 1.0        # [B, H, W]

    # Stack into sampling grid: [B, H, W, 3] = (x, y, z)
    grid_x_n = grid_x.unsqueeze(0).expand(B, -1, -1) * 2.0 - 1.0
    grid_y_n = grid_y.unsqueeze(0).expand(B, -1, -1) * 2.0 - 1.0
    sampling_grid = torch.stack([grid_x_n, grid_y_n, z], dim=-1)  # [B, H, W, 3]
    sampling_grid = sampling_grid.unsqueeze(1)                      # [B, 1, H, W, 3]

    # bilateral_grid: [B, 12, 8, H_g, W_g] — treat coeff dim as channels
    # F.grid_sample with 5D input performs trilinear interpolation
    coeffs = F.grid_sample(
        bilateral_grid,           # [B, 12, 8, H_g, W_g]
        sampling_grid,            # [B, 1, H, W, 3]
        mode='bilinear',
        padding_mode='border',
        align_corners=False
    )  # → [B, 12, 1, H, W]
    coeffs = coeffs.squeeze(2).permute(0, 2, 3, 1)  # [B, H, W, 12]
    return coeffs
```

**Intuition behind the slicing operation:**

- A bright pixel (guide $\approx$ 1) maps to the top layers of the bilateral grid ($z \approx 1$), where the network has learned coefficients appropriate for highlights.
- A dark pixel (guide $\approx$ 0) maps to the bottom layers, pulling coefficients tuned for shadows.
- Two pixels at the same spatial location but on opposite sides of a sharp edge (e.g., a white wall next to a dark window frame) have **different guidance values** and therefore sample **different depth layers** of the bilateral grid. They receive different affine transforms, even though they are spatially adjacent.
- This is precisely the edge-preserving property of bilateral filtering, now learned rather than hand-crafted.

#### 1.4.6 Per-Pixel Affine Transform

Each pixel receives a $3\times4$ affine transformation matrix derived from its 12 sliced coefficients:

```python
def apply_affine(coeffs, input_image):
    """
    coeffs:      [B, H, W, 12]  — per-pixel affine coefficients
    input_image: [B, H, W, 3]   — full-resolution RGB in [0, 1]
    returns:     [B, H, W, 3]   — transformed image
    """
    B, H, W, _ = coeffs.shape

    # Reshape coefficients to 3×4 matrices
    coeffs_3x4 = coeffs.view(B, H, W, 3, 4)  # [B, H, W, 3, 4]

    # Homogeneous input: append 1 to each pixel's RGB
    ones = torch.ones(B, H, W, 1, device=input_image.device)
    input_hom = torch.cat([input_image, ones], dim=-1)  # [B, H, W, 4]

    # Per-pixel matrix-vector multiply
    # output[b,h,w,c] = sum_i coeffs_3x4[b,h,w,c,i] * input_hom[b,h,w,i]
    output = torch.einsum('bhwci,bhwi->bhwc', coeffs_3x4, input_hom)
    return output  # [B, H, W, 3]
```

The $3\times4$ structure enables the transform to express:
- **Tone adjustment** (diagonal): per-channel gamma/exposure changes
- **Color correction** (off-diagonal): equivalent to a per-pixel CCM, enabling local white balance
- **Brightness shift** (bias column, 4th column): additive illumination adjustment

This is strictly more expressive than any global curve or fixed CCM.

#### 1.4.7 Training Setup

**Dataset.** MIT-FiveK (Bychkovsky et al., CVPR 2011): 5,000 Adobe DNG RAW photographs captured with Canon/Nikon DSLRs across diverse scenes and lighting conditions. Five professional retouchers (Experts A–E) independently edited each image in Adobe Lightroom. HDRNet uses **Expert C** as the training target, split as:
- Train: 4,500 images
- Test: 500 images

Dataset URL: https://data.csail.mit.edu/graphics/fivek/

**Loss function:**

$$\mathcal{L} = \|f_\theta(I) - I^*\|_2^2$$

where $f_\theta$ is the HDRNet, $I$ is the input (sRGB JPEG of the RAW, auto-processed), and $I^*$ is the Expert C retouched target. The L2 loss is computed in sRGB space after clamping to [0, 1].

**Training hyperparameters:**
- Optimizer: Adam, $\text{lr} = 1\times10^{-4}$, $\beta_1=0.9$, $\beta_2=0.999$
- Batch size: 1 (full-resolution images vary in size)
- Data augmentation: random crop $512\times512$, horizontal flip, color jitter

**Results on MIT-FiveK (PSNR, dB):**

| Method | PSNR | Speed at 1080p |
|---|---|---|
| Bychkovsky et al. (2011) | 22.5 | N/A |
| WVM (Farbman et al.) | 23.1 | ~2 s |
| **HDRNet** | **24.6** | **40 ms (GPU)** |
| Deep Photo (Lore et al.) | 24.7 | ~10 min |
| Image-Adaptive 3D LUT | 25.1 | <1 ms |

HDRNet achieves near state-of-the-art quality at real-time speed — the key differentiator for production deployment.

#### 1.4.8 Industrial Adoption and Variants

**Architectural variants:**

| Method | Key innovation | Venue |
|---|---|---|
| Google Photos HDR+ (Hasinoff et al., 2016) | Multi-frame align+merge, same team | SIGGRAPH Asia 2016 |
| AHDRNet (Yan et al., 2019) | Attention-guided HDR, handles ghosts | CVPR 2019 |
| Image-Adaptive 3D LUT (Zeng et al., 2020) | LUT-form bilateral learning | CVPR 2020 / TPAMI 2021 |
| CLUT-Net (Li et al., 2022) | Cascaded LUT for video | ACM MM 2022 |
| STAR (Xu et al., 2022) | Spatio-temporal bilateral for video | ECCV 2022 |

**Mobile deployment profile:**

| Component | Parameters | Latency (Hexagon DSP, 12MP) |
|---|---|---|
| Bilateral grid | 13,824 coefficients | — |
| S-Net backbone | ~500K | 4–6 ms |
| Guidance network | ~1K (two 1×1 convs) | <0.5 ms |
| Slicing + affine | O(H×W) ops | 1–2 ms |
| **Total** | **~500K** | **~5–10 ms** |

All major Android OEMs (Huawei, Xiaomi, OPPO, Samsung) deploy bilateral grid variants. The typical production integration:
1. Lightweight scene classifier (MobileNetV3, ~1M params) identifies scene category (portrait, landscape, night, food, etc.)
2. Scene category routes to a pre-trained coefficient network or selects basis LUT weights
3. Bilateral grid is inferred once per frame at low-res ($256\times256$)
4. Slicing and affine transform run on DSP/NPU at full resolution

**ISP integration flow:**

```
RAW sensor output
      │
      ▼
Traditional ISP pipeline
(demosaic, denoise, AWB, CCM, gamma)
      │
      ▼
Intermediate sRGB image ──────────────► Scene Classifier
      │                                        │
      │                               scene category label
      │                                        │
      └──────────────────────────────► HDRNet / Adaptive LUT
                                               │
                                               ▼
                                       Enhanced sRGB
                                               │
                                               ▼
                                      Display gamma / JPEG encode
```

#### 1.4.9 Comparison Table

| Method | Edge preservation | Scene-adaptive | Real-time | Local tone perception |
|---|---|---|---|---|
| Global gamma curve | No | No | Yes | No |
| Bilateral filter TM | Yes | No | Partial | Partial |
| Fixed 3D LUT | No | No | Yes | Partial |
| Adaptive 3D LUT | No | Yes | Yes | Partial |
| **HDRNet** | **Yes** | **Yes** | **Yes** | **Yes** |

HDRNet is the only method in this table that achieves all four desiderata simultaneously. The edge preservation comes from the bilateral grid slicing; scene-adaptivity comes from the CNN backbone; real-time performance comes from the low-resolution processing strategy; local tone perception comes from the per-pixel affine transform.

---

### 1.5 Deep Learning HDR Reconstruction

Beyond tone mapping of known HDR content, deep learning methods can **reconstruct HDR from a single LDR image**, hallucinating the clipped highlights and crushed shadows.

**SingleHDR (Liu et al., CVPR 2020).** Proposes a two-stage pipeline: (1) a de-quantization and linearization network reverses the camera's in-camera JPEG pipeline, (2) a hallucination network in-paints saturated highlight regions using learned scene priors. Trained on paired synthetic HDR/LDR data.

**HDR-GAN (Niu et al., AAAI 2021).** Applies conditional GAN training with a U-Net generator. The discriminator operates in the tone-mapped domain, supervising perceptual realism rather than pixel-level accuracy. Produces sharper, more detailed highlight in-painting compared to L2-trained methods, at the cost of occasional GAN artifacts.

**AHDRNet (Yan et al., CVPR 2019).** Addresses the multi-frame ghosting problem via **spatial attention**. For each non-reference frame, a dilated residual attention block computes a pixel-wise attention map:

$$A_k = \sigma\bigl(f_{\text{att}}([I_k^{\text{aligned}}, I_{\text{ref}}])\bigr), \quad k \neq \text{ref}$$

The final HDR radiance is:

$$E = f_{\text{merge}}\!\left(I_{\text{ref}},\, A_1 \odot I_1^{\text{aligned}},\, A_2 \odot I_2^{\text{aligned}}\right)$$

Ghost pixels receive near-zero attention weights, cleanly excluding motion-corrupted regions without explicit optical flow. AHDRNet achieves state-of-the-art HDR quality on the Kalantari et al. (2017) benchmark dataset.

---

### 1.6 HDR Display Standards

As HDR capture matures, display ecosystems have converged on several competing standards:

| Standard | Metadata | EOTF | Color gamut | Bit depth | Notes |
|---|---|---|---|---|---|
| HDR10 | Static (per-content) | PQ (ST.2084) | BT.2020 | 10-bit | Open standard, mandatory for UHD Blu-ray |
| HDR10+ | Dynamic (per-frame/scene) | PQ | BT.2020 | 10-bit | Samsung/Amazon open standard |
| Dolby Vision | Dynamic (per-frame) | PQ | BT.2020 | 12-bit | Licensed; requires Dolby hardware |
| HLG | None (scene-referred) | HLG (BT.2100) | BT.2020 | 10-bit | BBC/NHK; backward compatible with SDR displays |
| Advanced HDR | Dynamic (Philips) | PQ | BT.2020 | 10-bit | Rarely deployed |

**PQ (Perceptual Quantizer, SMPTE ST 2084)** maps absolute luminance (0–10,000 nits) to a perceptually uniform code value, allocating more bits near the JND (just-noticeable difference) threshold. This enables 10-bit representation to cover the full HDR luminance range without visible banding.

**HLG (Hybrid Log-Gamma)** uses a log-linear curve that maps naturally to standard SDR displays without metadata, enabling a single broadcast signal to serve both SDR and HDR televisions.

ISP pipelines targeting HDR display must include a **display mapping** stage that converts the internal HDR radiance representation to the target display standard, applying appropriate tone mapping for the display's peak luminance (400–2000 nits for current HDR TVs).

---

## §2 Calibration

### 2.1 CRF Calibration (Debevec-Malik)

1. Mount camera on tripod; eliminate all scene motion.
2. Capture $N = 5$–9 bracketed exposures at 1–2 EV intervals, covering at least 6 EV total range.
3. Record precise shutter times from EXIF (or controlled test bench); avoid floating-point rounding.
4. Sample $N_p = 100$ pixels uniformly across the mid-exposure image, ensuring $>20$% of pixels per channel are neither saturated nor black.
5. Solve the Debevec-Malik least-squares system (§1.2.1) with $\lambda = 10$–50.
6. Validate: plot the recovered $g(\cdot)$ curves; they should be monotone and smooth. Check that $g(128) \approx \ln(E_{\text{mid}})$.

### 2.2 HDRNet Production Calibration

Deploying HDRNet in a production ISP requires calibrating the coefficient network to the target camera/ISP chain. The workflow:

1. **Scene capture.** Photograph 200–2000 calibration scenes spanning the target quality dimensions: exposure range, scene DR, subject types (portrait, landscape, night, food). Include bracketed exposures for ground-truth HDR construction.

2. **Expert reference preparation.** Have professional retouchers edit representative images in Adobe Lightroom or Photoshop, establishing target appearance. Alternatively, use perceptual quality metrics to select the best of multiple ISP configurations as pseudo-ground-truth.

3. **Fine-tuning strategy.**
   - If data $> 500$ images: full fine-tune, lr $= 1\times10^{-5}$ from ImageNet pre-trained backbone.
   - If data $= 50$–500 images: freeze S-Net backbone (feature extractor), train only the bilateral grid prediction head and guidance network (lr $= 1\times10^{-4}$).
   - If data $< 50$ images: regularize strongly; consider adapter layers only.

4. **Export for deployment.**
   ```
   PyTorch → ONNX export → TFLite conversion → Hexagon DSP/NPU library
   ```
   Verify numerical equivalence at each conversion step (max pixel error $< 1/255$).

5. **Online inference.** A scene classifier routes each frame to the appropriate pre-computed coefficient network. The classifier typically runs at 5–10 fps; coefficient networks run per-frame at full frame rate.

---

## §3 Tuning

### 3.1 Bilateral Grid Resolution

The bilateral grid spatial resolution ($H_g \times W_g$) and luminance depth ($D$) control the locality of the learned transform:

- **Too small** (e.g., $4\times4\times4$): the network degenerates toward a global curve — no spatial adaptation. Use when scene illumination is spatially uniform.
- **Too large** (e.g., $64\times64\times32$): the network memorizes training examples; coefficients become noisy on out-of-distribution inputs. Inference cost also increases.
- **Default:** $12\times16\times8$ — sufficient for regional adaptation (sky vs. foreground) without over-fitting. Start here and adjust based on validation PSNR.

### 3.2 Guidance Network Depth

The default 2-layer $1\times1$ guidance network is sufficient for most scenes. Consider increasing depth (add one $3\times3$ depthwise separable conv with $3\times3$ receptive field) when:
- Content contains fine-grained luminance edges (text, fences)
- The network confuses luminance edges with color edges (e.g., red sky at sunset)

Do not increase guidance network width without also increasing bilateral grid depth; otherwise the additional capacity is wasted.

### 3.3 Tone Compression Aggressiveness

Add a perceptual loss term to the training objective to control visual aggressiveness:

$$\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{L2}} + \lambda_{\text{perc}} \cdot \mathcal{L}_{\text{VGG}} + \lambda_{\text{hdr}} \cdot \mathcal{L}_{\text{HDR}}$$

where $\mathcal{L}_{\text{HDR}} = \|\mu(f_\theta(I)) - \mu(I^*)\|_2$ is computed in the $\mu$-law tone-mapped domain ($\mu = 5000$), emphasizing highlight recovery. Increasing $\lambda_{\text{hdr}}$ from 0 to 0.1 typically improves highlight detail at the cost of slight shadow noise amplification.

### 3.4 Multi-Frame HDR Tuning Parameters

| Parameter | Typical range | Effect |
|---|---|---|
| Exposure ratio | 1:4 (2 EV) vs. 1:8 (3 EV) | Larger ratio covers more DR; smaller reduces ghosting |
| Number of frames | 2–5 | More frames = better DR coverage; more ghosting risk |
| Optical flow max displacement | 16–64 px | Larger handles fast motion; slower alignment |
| Ghost detection threshold $\tau$ | 0.05–0.20 | Lower = more conservative (keep less motion content) |
| Laplacian pyramid levels | 4–6 | More levels = smoother blending; slightly softer |

---

## §4 Artifacts

### 4.1 Ghost Artifacts in Multi-Frame HDR

**Cause.** Moving objects (people, vehicles, foliage) appear at different positions across the bracketed exposure sequence. After fusion, each position contributes a semi-transparent ghost of the object.

**Detection and mitigation.**
- Pre-alignment with optical flow reduces rigid motion ghosts but fails for deformable objects (faces, hands).
- AHDRNet spatial attention (§1.5) produces soft exclusion masks that degrade gracefully on partially overlapping motion.
- Conservative heuristic: if $|I_k^{\text{aligned}} - I_{\text{ref}}| > \tau$, replace with reference-only exposure for that pixel (sacrifices DR at motion pixels).

**Evaluation.** Ghost artifact magnitude is measured by the Ghost-Free Rate (GFR): the fraction of pixels in moving regions where the fused output is within $\pm5\%$ of the reference exposure value.

### 4.2 Halo Effect from Local Tone Mapping

**Cause.** Local TMOs with large spatial support (bilateral filter, guided filter) create a bright ring around dark objects on a bright background (light halo) or a dark ring around bright objects (dark halo). This occurs when the filter's luminance range is inconsistent across an edge.

**Mitigation in HDRNet.** Because the guidance network encodes a fine-grained per-pixel luminance proxy, the bilateral grid slicing assigns different coefficients to each side of an edge naturally. The slicing interpolation is smooth (trilinear), so there is no discontinuity to create a ringing artifact. The effective spatial support of the learned filter adapts automatically to local texture frequency.

**Residual halos** can still appear if the bilateral grid spatial resolution is too coarse relative to the halo-generating edge length. Increasing $H_g$ and $W_g$ by 2× typically eliminates visible halos in these cases.

### 4.3 3D LUT Color Gamut Clipping

**Cause.** When input pixels are outside the training distribution (saturated primaries, extreme color casts), the learned LUT may map them to values outside [0, 1], causing hard clipping.

**Mitigation.** Apply a soft-clip function before display encoding:

```python
def soft_clip(x, knee=0.9):
    """
    x:    input tensor, any shape, float32
    knee: point above which soft compression begins
    returns: output in [0, 1] with smooth compression above 'knee'
    """
    # Below knee: identity
    # Above knee: asymptotically approaches 1 (Reinhard-style)
    above_knee = x > knee
    x_soft = torch.where(
        above_knee,
        knee + (1.0 - knee) * (x - knee) / (1.0 + (x - knee) / (1.0 - knee)),
        x
    )
    return x_soft.clamp(0.0, 1.0)
```

The equivalent closed form for all $x > 0$: $\text{clip\_soft}(x) = x / (1 + x)$ (Reinhard operator applied pointwise). This removes hard clipping artifacts while preserving in-gamut color accuracy.

---

## §5 Evaluation

### 5.1 Metrics

| Metric | Domain | Description | Higher is better |
|---|---|---|---|
| PSNR | sRGB | Peak signal-to-noise ratio, dB | Yes |
| $\mu$-PSNR | Tone-mapped | PSNR computed after $\mu$-law tone mapping ($\mu=5000$); emphasizes HDR quality | Yes |
| SSIM | sRGB | Structural similarity index, emphasizes luminance+contrast+structure | Yes |
| HDR-VDP-2 | Perceptual | Visibility of difference map, calibrated to human CSF; produces quality score Q | Yes |
| LPIPS | Deep features | Learned perceptual image patch similarity; correlates well with human ratings | No (lower is better) |
| Ghost-Free Rate | Moving regions | Fraction of motion pixels fused without visible ghosting | Yes |

### 5.2 Benchmark Datasets

| Dataset | Images | Type | Notes |
|---|---|---|---|
| MIT-FiveK | 5,000 | RAW + expert retouches | Standard benchmark for tone/color enhancement |
| HDRI Haven | ~1,000 | Outdoor HDR panoramas (EXR) | Free, CC0 licensed; good for TMO evaluation |
| NTIRE HDR 2021/2022 | 1,494 | Multi-exposure brackets + HDR GT | Competition dataset; diverse scenes |
| SICE | 589 | Multi-exposure LDR sequences | Specifically designed for exposure fusion |
| RAISE | 8,156 | RAW images | Large-scale, no HDR ground truth; used for generalization testing |
| Kalantari et al. (2017) | 89 | 3-exposure brackets + HDR GT | Standard HDR reconstruction benchmark |

### 5.3 Reporting Conventions

When reporting HDR algorithm results, always specify:
1. Whether PSNR is computed in linear HDR domain, tone-mapped domain ($\mu$-PSNR), or sRGB
2. Which tone mapping operator was used for visualization comparisons
3. Whether evaluation is on the full test set or only static (no-motion) subsets
4. The expert annotator used (for MIT-FiveK, Expert A through E produce different targets)

---

## §6 Code

The companion notebook *See §6 Code section for runnable examples.* implements the full pipeline described in this chapter. Key cells:

### 6.1 Loading Multi-Exposure RAW Sequences

```python
import rawpy
import numpy as np
from pathlib import Path

def load_raw_exposure(raw_path):
    """Load a RAW file and return linear RGB (no gamma, no white balance)."""
    with rawpy.imread(str(raw_path)) as raw:
        rgb = raw.postprocess(
            use_camera_wb=True,
            half_size=False,
            no_auto_bright=True,
            output_bps=16,           # 16-bit linear output
            gamma=(1, 1),            # Linear gamma
            demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD
        )
    return rgb.astype(np.float32) / 65535.0  # Normalize to [0, 1]

# Load bracketed sequence: [-2, 0, +2] EV
exposure_paths = sorted(Path('data/bracket/').glob('*.dng'))
exposures = [load_raw_exposure(p) for p in exposure_paths]
shutter_times = [0.004, 0.016, 0.064]  # seconds: 1/250, 1/60, 1/15
```

### 6.2 Debevec-Malik CRF Estimation

```python
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import lsqr

def estimate_crf_debevec(images, shutter_times, n_samples=100, smoothness=10.0):
    """
    images:        list of (H, W) float32 arrays in [0, 1] (single channel)
    shutter_times: list of exposure durations in seconds
    Returns: g (256-element array mapping Z → ln E), log_irradiance
    """
    H, W = images[0].shape
    P = 256         # 8-bit range
    N = len(images)

    # Sample pixel locations uniformly
    rng = np.random.default_rng(42)
    y_idx = rng.integers(0, H, n_samples)
    x_idx = rng.integers(0, W, n_samples)

    Z = np.stack([
        (img[y_idx, x_idx] * 255).astype(int).clip(0, 255)
        for img in images
    ], axis=1)  # (n_samples, N)

    log_dt = np.log(shutter_times)

    def weight(z):
        z_mid = 128
        w = np.where(z <= z_mid, z + 1, 256 - z)
        return w.astype(float)

    # Build overdetermined system A * x = b
    n_eq = n_samples * N + P + 1
    n_var = P + n_samples
    A = lil_matrix((n_eq, n_var), dtype=np.float64)
    b = np.zeros(n_eq)

    row = 0
    for i in range(n_samples):
        for j in range(N):
            z = Z[i, j]
            w = weight(z)
            A[row, z] = w
            A[row, P + i] = -w
            b[row] = w * log_dt[j]
            row += 1

    # Smoothness constraint: minimize second derivative of g
    for z in range(1, P - 1):
        w = weight(z)
        A[row, z - 1] = w * smoothness
        A[row, z    ] = -2 * w * smoothness
        A[row, z + 1] = w * smoothness
        row += 1

    # Fix middle value: g(128) = 0
    A[row, 128] = 1
    row += 1

    x, *_ = lsqr(A.tocsr(), b, iter_lim=1000)
    g = x[:P]
    log_E = x[P:]
    return g, log_E

# Apply CRF estimation per channel
crf_r, _ = estimate_crf_debevec([e[:, :, 0] for e in exposures], shutter_times)
crf_g, _ = estimate_crf_debevec([e[:, :, 1] for e in exposures], shutter_times)
crf_b, _ = estimate_crf_debevec([e[:, :, 2] for e in exposures], shutter_times)
```

### 6.3 Mertens Multi-Exposure Fusion

```python
import cv2
import numpy as np

def mertens_fusion(images):
    """
    images: list of (H, W, 3) float32 arrays in [0, 1]
    Returns: fused (H, W, 3) float32 image
    """
    merger = cv2.createMergeMertens(
        contrast_weight=1.0,
        saturation_weight=1.0,
        exposure_weight=1.0
    )
    imgs_u8 = [np.clip(img * 255, 0, 255).astype(np.uint8) for img in images]
    fused = merger.process(imgs_u8)
    return np.clip(fused, 0.0, 1.0)

fused_ldr = mertens_fusion(exposures)
```

### 6.4 Reinhard Global Tone Mapping

```python
import numpy as np

def reinhard_tonemap(hdr_image, key=0.18, delta=1e-6, l_white=None):
    """
    hdr_image: (H, W, 3) float32 HDR radiance map (linear)
    key:       scene key value (default 0.18 = 18% gray)
    l_white:   luminance that maps to pure white (None = no burn)
    Returns:   tone-mapped (H, W, 3) float32 in [0, 1]
    """
    luminance = 0.2126 * hdr_image[..., 0] + 0.7152 * hdr_image[..., 1] + 0.0722 * hdr_image[..., 2]

    # Log-average luminance (scene key)
    log_avg_lum = np.exp(np.mean(np.log(luminance + delta)))

    # Scale luminance to key value
    L_scaled = (key / log_avg_lum) * luminance

    if l_white is None:
        L_d = L_scaled / (1.0 + L_scaled)
    else:
        L_d = L_scaled * (1.0 + L_scaled / l_white**2) / (1.0 + L_scaled)

    # Scale RGB proportionally
    scale = np.where(luminance > delta, L_d / (luminance + delta), 0.0)
    tonemapped = hdr_image * scale[..., np.newaxis]
    return np.clip(tonemapped, 0.0, 1.0)
```

### 6.5 Simplified HDRNet in PyTorch

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class SNetBlock(nn.Module):
    def __init__(self, in_ch, out_ch, stride=1):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, stride=stride, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True)
        )
    def forward(self, x):
        return self.conv(x)

class HDRNet(nn.Module):
    def __init__(self, grid_h=12, grid_w=16, depth=8, n_coeffs=12):
        super().__init__()
        self.grid_h = grid_h
        self.grid_w = grid_w
        self.depth  = depth
        self.n_coeffs = n_coeffs

        # Low-res S-Net
        self.local_net = nn.Sequential(
            SNetBlock(3,  16, stride=1),
            SNetBlock(16, 32, stride=2),
            SNetBlock(32, 64, stride=2),
            SNetBlock(64, 64, stride=2),
            SNetBlock(64, 64, stride=2),   # → 16×16×64
        )
        self.global_net = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(64, 64), nn.ReLU(inplace=True),
            nn.Linear(64, 64), nn.ReLU(inplace=True),
            nn.Linear(64, 64), nn.ReLU(inplace=True),
        )
        self.grid_head = nn.Sequential(
            nn.Conv2d(128, depth * n_coeffs, 1),
        )

        # Full-res guidance
        self.guidance = nn.Sequential(
            nn.Conv2d(3, 1, 1, bias=False),
            nn.BatchNorm2d(1),
            nn.ReLU(inplace=True),
            nn.Conv2d(1, 1, 1),
            nn.Tanh(),
        )

    def forward(self, x_full, x_low=None):
        B, C, H, W = x_full.shape
        if x_low is None:
            x_low = F.interpolate(x_full, size=(256, 256), mode='bilinear', align_corners=False)

        # S-Net local features: [B, 64, 16, 16]
        local_feat = self.local_net(x_low)

        # Global features: [B, 64, 1, 1]
        global_feat = self.global_net(local_feat).view(B, 64, 1, 1)
        global_feat = global_feat.expand(-1, -1, local_feat.shape[2], local_feat.shape[3])

        # Concatenate and predict grid
        combined = torch.cat([local_feat, global_feat], dim=1)  # [B, 128, 16, 16]
        grid_raw = self.grid_head(combined)                      # [B, depth*n_coeffs, 16, 16]
        grid = grid_raw.view(B, self.depth, self.n_coeffs,
                             grid_raw.shape[2], grid_raw.shape[3])  # [B, D, 12, H_g, W_g]

        # Guidance map: [B, 1, H, W]
        guide = self.guidance(x_full)
        guide = guide * 0.5 + 0.5  # tanh → [0, 1]

        # Bilateral slice
        coeffs = self._bilateral_slice(grid, guide.squeeze(1))  # [B, H, W, 12]

        # Apply per-pixel affine
        output = self._apply_affine(coeffs, x_full.permute(0, 2, 3, 1))  # [B, H, W, 3]
        return output.permute(0, 3, 1, 2).clamp(0, 1)

    def _bilateral_slice(self, grid, guide):
        B, D, NC, Hg, Wg = grid.shape
        _, H, W = guide.shape
        # Permute grid to [B, NC, D, Hg, Wg] for grid_sample
        grid_p = grid.permute(0, 2, 1, 3, 4)  # [B, 12, D, Hg, Wg]
        # Normalized coordinates
        xs = (torch.arange(W, device=guide.device).float() + 0.5) / W * 2 - 1
        ys = (torch.arange(H, device=guide.device).float() + 0.5) / H * 2 - 1
        gy, gx = torch.meshgrid(ys, xs, indexing='ij')
        gz = guide * 2.0 - 1.0
        gx = gx.unsqueeze(0).expand(B, -1, -1)
        gy = gy.unsqueeze(0).expand(B, -1, -1)
        sample_grid = torch.stack([gx, gy, gz], dim=-1).unsqueeze(1)  # [B, 1, H, W, 3]
        sliced = F.grid_sample(grid_p, sample_grid,
                               mode='bilinear', padding_mode='border',
                               align_corners=False)      # [B, 12, 1, H, W]
        return sliced.squeeze(2).permute(0, 2, 3, 1)    # [B, H, W, 12]

    def _apply_affine(self, coeffs, image):
        B, H, W, _ = image.shape
        mat = coeffs.view(B, H, W, 3, 4)               # [B, H, W, 3, 4]
        ones = torch.ones(B, H, W, 1, device=image.device)
        img_h = torch.cat([image, ones], dim=-1)        # [B, H, W, 4]
        out = torch.einsum('bhwci,bhwi->bhwc', mat, img_h)
        return out

# Instantiate and run
model = HDRNet(grid_h=12, grid_w=16, depth=8, n_coeffs=12)
model.eval()
with torch.no_grad():
    test_input = torch.rand(1, 3, 1080, 1920)
    enhanced = model(test_input)
    print(f"Output shape: {enhanced.shape}")   # (1, 3, 1080, 1920)
```

### 6.6 PSNR Evaluation

```python
import numpy as np
import torch

def compute_psnr(pred, target, max_val=1.0):
    """
    pred, target: numpy arrays or torch tensors, same shape
    Returns: PSNR in dB
    """
    if isinstance(pred, torch.Tensor):
        pred = pred.detach().cpu().numpy()
        target = target.detach().cpu().numpy()
    mse = np.mean((pred.astype(np.float64) - target.astype(np.float64))**2)
    if mse == 0:
        return float('inf')
    return 10 * np.log10(max_val**2 / mse)

def compute_mu_psnr(pred, target, mu=5000, max_val=1.0):
    """PSNR in mu-law tone-mapped domain, for HDR evaluation."""
    def mu_law(x):
        return np.log(1 + mu * x) / np.log(1 + mu)
    return compute_psnr(mu_law(pred), mu_law(target), max_val=1.0)
```

---

## References

1. Debevec, P. E., & Malik, J. (1997). Recovering high dynamic range radiance maps from photographs. *ACM SIGGRAPH 1997*, pp. 369–378.

2. Mertens, T., Kautz, J., & Van Reeth, F. (2007). Exposure fusion. *15th Pacific Conference on Computer Graphics and Applications (Pacific Graphics 2007)*, pp. 382–390.

3. Reinhard, E., Stark, M., Shirley, P., & Ferwerda, J. (2002). Photographic tone reproduction for digital images. *ACM SIGGRAPH 2002*, pp. 267–276.

4. **Gharbi, M., Chen, J., Barron, J. T., Hasinoff, S. W., & Durand, F. (2017). Deep bilateral learning for real-time image enhancement. *ACM Transactions on Graphics (SIGGRAPH 2017)*, 36(4).** GitHub: https://github.com/google/hdrnet

5. Zeng, H., Cai, J., Li, L., Cao, Z., & Zhang, L. (2020). Learning image-adaptive 3D LUTs for high performance photo enhancement. *IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI)*, 2020.

6. Yan, Q., Gong, D., Zhang, P., Shi, J., Zhang, Y., & Robles-Kelly, A. (2019). Attention-guided network for ghost-free high dynamic range imaging. *IEEE Conference on Computer Vision and Pattern Recognition (CVPR 2019)*.

7. Liu, Y. L., Lai, W. S., Chen, Y. S., Kao, Y. L., Yang, M. H., Chuang, Y. Y., & Huang, J. B. (2020). Single-image HDR reconstruction by learning to reverse the camera pipeline. *IEEE Conference on Computer Vision and Pattern Recognition (CVPR 2020)*.

8. Hasinoff, S. W., Sharlet, D., Geiss, R., Adams, A., Barron, J. T., Kainz, F., Chen, J., & Levoy, M. (2016). Burst photography for HDR and low-light imaging on mobile cameras. *ACM SIGGRAPH Asia 2016*, 35(6).

9. Paris, S., & Durand, F. (2006). A fast approximation of the bilateral filter using a signal processing approach. *European Conference on Computer Vision (ECCV 2006)*, pp. 568–580.

10. Bychkovsky, V., Paris, S., Chan, E., & Durand, F. (2011). Learning photographic global tonal adjustment with a database of input/output image pairs. *IEEE Conference on Computer Vision and Pattern Recognition (CVPR 2011)*. MIT-FiveK dataset: https://data.csail.mit.edu/graphics/fivek/

11. Niu, Y., Wu, J., Liu, W., Guo, W., & Lau, R. W. H. (2021). HDR-GAN: HDR image reconstruction from multi-exposure LDR images with large motions. *AAAI 2021*.

12. Durand, F., & Dorsey, J. (2002). Fast bilateral filtering for the display of high-dynamic-range images. *ACM SIGGRAPH 2002*, pp. 257–266.

13. Drago, F., Myszkowski, K., Annen, T., & Chiba, N. (2003). Adaptive logarithmic mapping for displaying high contrast scenes. *Computer Graphics Forum (Eurographics 2003)*, 22(3), pp. 419–426.

14. Adams, A. (1948). *The Negative: Exposure and Development* (Zone System). Morgan & Morgan.

---

> **Chapter scope note:**
> This chapter covers dynamic range concepts, sensor DR measurement, HDR fundamentals, and classical tone mapping operators.
> The following topics are **out of scope** here — see the referenced chapters instead:
> - Multi-frame HDR fusion (motion detection, ghost suppression, exposure merging) → **Ch27 HDR Merge**
> - Local adaptive tone mapping (CLAHE / Retinex / Guided Filter TM) → **Ch35 Local Tone Mapping**
> - HDR display signal chain (PQ / HLG / Dolby Vision) → **Ch38 HDR Display Pipeline**
> - AI-driven tone mapping (Deep TMO / HDRNet) → **Ch57 AI-Driven Tone Mapping**
