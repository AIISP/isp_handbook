# Part 2, Chapter 10: HDR Capture & Exposure Merging

> **Pipeline position:** Multi-frame ISP module (optional); replaces single-exposure pipeline
> **Prerequisites:** Chapter 4 (Noise Models), Chapter 24 (Gamma/TM)
> **Reader path:** Algorithm Engineer, System Designer

---

## §1 Theory

### 1.1 Scene Dynamic Range vs. Sensor Range

Real-world scenes routinely span 20 or more stops of dynamic range — a sunlit outdoor scene with deep shadows and specular highlights can exceed 100,000:1 luminance ratio. A typical image sensor captures roughly 12–14 stops (for a 12–14 bit ADC with read noise of a few electrons), leaving either the shadows crushed to black or the highlights clipped to white when exposed for a single frame.

**Key relationship:**

```
Dynamic Range (stops) = log2(Lmax / Lmin)
                      = log2(Full-well capacity / Read noise floor)
```

For a sensor with 60,000 e- full-well and 3 e- read noise: DR = log2(60000/3) ≈ 14.3 stops.

A bright outdoor scene may have DR ≈ 20–22 stops. The gap (6–8 stops) is what HDR capture must bridge.

---

### 1.2 Exposure Bracketing

The standard capture strategy is **automatic exposure bracketing (AEB)**: N frames are captured in rapid succession, each at a different exposure value (EV).

| Frame | EV offset | Exposure time ratio | Captures |
|-------|-----------|---------------------|----------|
| 0     | -2 EV     | 1/4 x base          | Highlights |
| 1     |  0 EV     | 1x base             | Midtones |
| 2     | +2 EV     | 4x base             | Shadows |

The total captured range extends by 2 × (N-1) stops beyond what a single exposure provides.

**EV arithmetic:** 1 EV = factor of 2 in exposure (one stop). An EV=-2 frame exposes 4x shorter, preserving highlights; EV=+2 exposes 4x longer, recovering shadows.

---

### 1.3 Camera Response Curve (CRC) Estimation — Debevec & Malik 1997

A real camera's pixel values Z are related to scene irradiance E by the camera response function f:

```
Z_ij = f( E_i * Δt_j )
```

where i indexes pixels and j indexes exposures (with exposure time Δt_j).

Taking logarithms and defining g = ln(f^{-1}):

```
g(Z_ij) = ln(E_i) + ln(Δt_j)
```

This is a linear system that can be solved by least-squares for g(z) at each integer z in [0, 255], subject to a smoothness constraint on g and the normalization g(128) = 0.

**Debevec & Malik objective:**

```
minimize  Σ_i Σ_j [ w(Z_ij) · (g(Z_ij) - ln(E_i) - ln(Δt_j)) ]^2
         + λ Σ_{z=1}^{254} [ w(z) · g''(z) ]^2
```

where w(z) is a weighting function that down-weights saturated/underexposed pixels:

```
         z - z_min          if z <= (z_min + z_max)/2
w(z) = {
         z_max - z          if z > (z_min + z_max)/2
```

This is a "hat" or triangle function with w = 0 at z_min = 0 and z_max = 255.

Once g is recovered, the **radiance map** (HDR floating-point image) is assembled as:

```
ln(E_i) = Σ_j w(Z_ij) · (g(Z_ij) - ln(Δt_j))
          ─────────────────────────────────────
                    Σ_j w(Z_ij)
```

Equivalently in linear domain:

```
HDR_i = Σ_j w(Z_ij) · (Z_ij / Δt_j)
        ────────────────────────────
               Σ_j w(Z_ij)
```

The weight function ensures that saturated pixels (near 0 or 255) contribute minimally, and well-exposed pixels (near mid-gray) contribute maximally.

---

### 1.4 Mertens Exposure Fusion (No CRC Required)

When an accurate CRC is unavailable, or when computational simplicity is preferred, **Mertens et al. (2007)** proposed direct multi-exposure fusion without HDR reconstruction. The merged result is a tone-mapped LDR image, not an HDR radiance map.

For each input exposure j and each pixel i, three quality measures are computed:

| Measure | Symbol | Formula | Captures |
|---------|--------|---------|---------|
| Contrast | C_ij | Laplacian magnitude of luminance | Local detail, texture |
| Saturation | S_ij | Standard deviation of R, G, B channels | Color richness |
| Well-exposedness | E_ij | Gaussian(L_ij; mu=0.5, sigma=0.2) | Avoids clipping |

The per-pixel, per-exposure weight is:

```
W_ij = C_ij^{w_C} * S_ij^{w_S} * E_ij^{w_E}
```

Weights are normalized across exposures:

```
W_ij_norm = W_ij / Σ_k W_ik
```

The fused result is the weighted sum:

```
Fused_i = Σ_j W_ij_norm * I_ij
```

In practice, fusion is performed in a **Laplacian pyramid** to avoid seam artifacts at exposure boundaries.

**Default exponent values:** w_C = w_S = w_E = 1.0. Increasing w_C emphasizes detail, increasing w_E more aggressively avoids clipped regions.

---

### 1.5 Ghost Detection and Removal

When objects move between exposures, the merged image shows **ghosting**: moving objects appear transparent, doubled, or smeared. Two standard approaches:

**1. Optical Flow Alignment**

Compute dense optical flow between frames, warp all frames to a reference frame, then merge. OpenCV `calcOpticalFlowFarneback` or DIS flow are common choices. Limitation: flow estimation itself can fail in saturated regions.

**2. Saturation-Based Ghost Masking**

Use the short-exposure frame as anchor (least motion blur, sharpest). For each pixel, if the weight assigned to a non-reference frame is high but the pixel differs significantly from the reference:

```
ghost_mask_ij = |I_ij - I_ref| > T_ghost  AND  W_ij > T_weight
```

Where ghost is detected, zero out the weight for that frame and renormalize. T_ghost ≈ 0.1–0.2 (normalized), T_weight ≈ 0.3.

**3. Homography Alignment (for camera motion)**

For handheld photography, global homography (2D projective transform) aligns the frames before merge. Works well when the scene is planar or distant, fails for parallax-heavy scenes.

---

### 1.6 Night Mode: Multi-Frame Averaging for SNR Improvement

Night mode captures N frames at identical (or near-identical) exposure, aligns them, and averages them. The signal averages constructively while independent noise averages destructively.

#### SNR ∝ √N Derivation

**Single-frame noise model.** For a single exposure with signal level S (in electrons or normalized units):

- **Shot noise** follows a Poisson distribution with variance equal to the mean: `Var_shot = S`
- **Read noise** is additive Gaussian with variance `σ_r²`
- Total noise variance for a single frame:

```
Var_1 = S + σ_r²
```

Therefore the single-frame SNR is:

```
SNR_1 = S / sqrt(S + σ_r²)
```

**N-frame average.** Average N independent frames, each with signal S and total noise variance `Var_1 = S + σ_r²`:

- Signal of the average: `(N·S) / N = S`  (signal adds coherently, then divides by N)
- Noise variance of the average: since the N frames are independent,

```
Var_N = (N · Var_1) / N²  =  (N · (S + σ_r²)) / N²  =  (S + σ_r²) / N
```

Therefore the N-frame SNR is:

```
SNR_N = S / sqrt((S + σ_r²) / N)
      = S · sqrt(N) / sqrt(S + σ_r²)
      = sqrt(N) · SNR_1
```

**Shot-noise dominated regime.** When `S >> σ_r²` (high light level, negligible read noise):

```
SNR_N ≈ S / sqrt(S / N)  =  sqrt(N · S)  ∝  sqrt(N)
```

**Read-noise dominated regime.** When `S << σ_r²` (very low light, read noise dominates):

```
SNR_N ≈ S · sqrt(N) / σ_r  ∝  sqrt(N)
```

In **both regimes** the SNR scales as `sqrt(N)`. The key result is:

```
SNR_N = √N · SNR_1
```

This is the theoretical SNR gain from N-frame averaging. In practice:
- Alignment error at subpixel level causes a residual noise floor
- Motion between frames (hand tremor, subjects) degrades the gain
- Google Night Sight (SIGGRAPH 2019) uses learned alignment and merge with per-frame noise models

**When to use what:**

| Scenario | Recommended method |
|----------|--------------------|
| Bright outdoor | 3-frame Mertens fusion |
| Handheld night | 8–16 frame align-and-average |
| Static night | Long single exposure |
| Video HDR | Alternating exposures + temporal merge |

---

## §2 Calibration

### 2.1 CRC Calibration

To calibrate the camera response curve:

1. Set camera on tripod, aim at **gray card** or uniformly-lit flat surface
2. Capture 3–15 exposures spanning the full dynamic range (e.g., EV -6 to +6 in 1-stop steps)
3. Sample ~50–200 pixel locations from smoothly-varying regions (avoid specular spots)
4. Run the Debevec–Malik solver to recover g(z) for each color channel separately

**Validation:** Plot g(z) vs z; it should be a smooth, monotonically increasing curve. Significant discontinuities indicate bad samples or sensor nonlinearity.

### 2.2 Exposure Metadata Accuracy

The CRC solver requires accurate exposure times Δt_j from EXIF/metadata. Even small errors (e.g., ±5% in exposure time) cause visible artifacts in the merged radiance map (banding between exposures).

**Check:** Verify that ln(Δt_{j+1}) - ln(Δt_j) matches the intended EV step. For EV step of 2: ln(Δt_{j+1}/Δt_j) should be ln(4) ≈ 1.386.

### 2.3 Alignment Accuracy

Registration error between frames must be below **0.5 pixel** to avoid chromatic fringing and edge artifacts in the merged result.

**Metrics:**
- Compute SSIM between aligned frames in overlapping well-exposed regions
- Measure edge sharpness: sharper = better alignment
- Use ECC (Enhanced Correlation Coefficient) or phase correlation for subpixel accuracy

---

## §3 Tuning

### 3.1 EV Bracket Step

| EV step | Result |
|---------|--------|
| 2 EV (default) | Wide HDR coverage, visible exposure jump in ghosted regions |
| 1 EV | Subtle HDR, smoother weight transitions, less saturation risk |
| 3 EV | Maximum HDR range, difficult ghost removal |

**Recommendation:** Start with 2 EV. Reduce to 1 EV if ghosting artifacts are problematic.

### 3.2 Number of Frames

| N frames | Pros | Cons |
|----------|------|------|
| 2 | Fast, less motion | Limited HDR range (only 1 bracket gap) |
| 3 (default) | Good balance | Standard for most smartphone cameras |
| 5 | Wider range, smoother transitions | Longer capture, more motion risk |

### 3.3 Ghost Threshold Tuning

The ghost detection threshold T_ghost controls sensitivity:

- **T_ghost too small:** Over-detection; stationary objects treated as ghosts, causing clipping artifacts where well-exposed pixels are discarded
- **T_ghost too large:** Under-detection; ghosting artifacts pass through the merge

**Tuning process:** Test with a scene containing both static and moving elements. Binary-search T_ghost to maximize quality on a validation set.

### 3.4 Night Mode Frame Count vs. Motion Blur Trade-off

| N frames | Theoretical SNR gain | Max motion allowed (at 1/30 s base) |
|----------|---------------------|--------------------------------------|
| 4        | 2x (6 dB)           | ~1/120 s worth of motion per frame  |
| 8        | 2.83x (9 dB)        | ~1/240 s                            |
| 16       | 4x (12 dB)          | ~1/480 s                            |

Motion threshold: if estimated inter-frame displacement > 2 pixels, discard that frame rather than average it.

---

## §4 Artifacts

### 4.1 Ghost

**Description:** Moving objects (cars, people, leaves) appear as semi-transparent doubles or smears in the merged image.

**Root cause:** The weight function assigns nonzero weights to the same pixel from frames captured at different times, and the pixel has moved.

**Mitigation:**
- Use shortest-exposure frame as ghost-free reference
- Apply saturation mask: if a pixel is overexposed in the short frame but correct in the long frame, trust the long frame
- Bilateral filtering of weights to smooth sharp ghost edges

### 4.2 Halo

**Description:** Bright luminance aura around high-contrast edges (lamp posts, windows against sky). Caused by the tonemapper, not the HDR merge itself.

**Root cause:** Global tone mapping (e.g., Reinhard) compresses highlights but creates local contrast reversal near bright edges.

**Mitigation:** Use local tone mapping (bilateral tone mapping, guided filter TM). Limit Reinhard key parameter.

### 4.3 Misalignment Stripe (Chromatic Fringing)

**Description:** Colored fringes at edges, especially visible on high-contrast edges. Appears as magenta/cyan stripes.

**Root cause:** Sub-pixel misalignment between frames combined with the CFA pattern. The R, G, B channels misalign by different sub-pixel amounts.

**Mitigation:**
- Improve registration to < 0.3 pixel accuracy
- Apply per-channel alignment independently
- Post-process: defringe filter targeting magenta/cyan at high-contrast edges

### 4.4 Exposure Transition Banding

**Description:** A visible horizontal or irregular band where the weight function transitions abruptly from one exposure frame to another. Often appears as a tonal step in smooth regions (sky gradients).

**Root cause:** The weight function w(z) is not smooth across its support, or the bracket EV step is too large so frames do not overlap well.

**Mitigation:**
- Increase weight function overlap (reduce EV step or widen hat function)
- Process fusion in Laplacian pyramid (Mertens method) instead of pixel-wise blend
- Smooth weight maps spatially before blending

---

## §5 Evaluation

### 5.1 Tone-Mapped Quality: PSNR and HDR-VDP-2

**PSNR** measures pixel-level fidelity of the tone-mapped HDR result vs. a reference (e.g., a professionally processed HDR reference):

```
PSNR = 10 * log10(MAX^2 / MSE)
```

**HDR-VDP-2** (Mantiuk et al. 2011) is a perceptually-calibrated metric that models human visual system response to HDR content. It outputs:
- Q score: 0–100 (higher = less visible difference)
- Probability map: shows spatially where artifacts are visible

HDR-VDP-2 is more meaningful than PSNR for HDR because it accounts for local adaptation and contrast sensitivity.

### 5.2 Ghost Artifact Detection Rate

Evaluate on a dataset with known ground-truth ghost-free merged images:

```
Precision = TP / (TP + FP)   # fraction of detected ghosts that are real
Recall    = TP / (TP + FN)   # fraction of real ghosts that are detected
F1        = 2 * P * R / (P + R)
```

A good ghost detector achieves F1 > 0.85 on typical scenes.

### 5.3 SNR Improvement (Night Mode)

Measure SNR on a flat gray patch in the merged image:

```
SNR = 20 * log10(mu / sigma)   [dB]
```

where mu = mean pixel value, sigma = standard deviation (noise).

Plot SNR vs N_frames and compare to the theoretical line:

```
SNR(N) = SNR(1) + 10 * log10(N)
```

The gap between measured and theoretical SNR reveals the alignment quality and motion contamination.

---

## §6 Code

See *See §6 Code section for runnable examples.* for complete runnable implementation (7 cells, 0-indexed):

- Cell 0: Imports — numpy, scipy.ndimage, matplotlib; optional rawpy and isp_utils handled with try/except
- Cell 1: Synthetic HDR scene generation and 3-frame bracketed exposure simulation (EV -2/0/+2); visualizes the 3 input frames
- Cell 2: Mertens weight maps — computes and visualizes W_contrast (Laplacian), W_saturation (RGB std), and W_exposure (Gaussian) separately for all 3 frames (9 maps total)
- Cell 3: Laplacian pyramid fusion — implements `mertens_pyramid_fusion` and compares pyramid-fused result vs. simple average
- Cell 4: SNR vs N frames — simulates and plots SNR_N = sqrt(N) * SNR_1 with matched theoretical and simulated curves
- Cell 5: Tuning parameters reference block (EV step, N frames, ghost threshold, pyramid levels, exposure sigma)
- Cell 6: Full visualization dashboard (input frames, fused result, weight maps strip, SNR gain bar chart), PSNR/SSIM evaluation, and 3 exercises

---

## §7 HDR Implementation on Major ISP Platforms

### 7.1 HDR Mode Classification

```
HDR Types
├── Hardware Staggered HDR (sensor-level)
│   ├── DOL-HDR (Digital Overlap HDR): different exposure times per row within one frame
│   ├── SHDR (Staggered HDR): alternating frames at different exposures (odd=long, even=short)
│   └── LS-HDR (Long-Short): 2-frame merge
├── Software Multi-Frame HDR (application-level)
│   ├── AEB (Auto Exposure Bracketing): burst capture at different exposures
│   └── MFHDR: automatic alignment and merge
└── Single-Frame HDR
    ├── GTM/LTM (tone mapping)
    └── AI single-frame HDR recovery
```

---

### 7.2 Qualcomm Staggered HDR

- **Hardware support:** Spectra ISP has a dedicated HDR Combine block in the BPS subsystem
- **Staggered HDR (SHDR):** Sensor outputs long + short exposure frames interleaved; ISP receives them in a single data stream and automatically separates them
- **3-frame HDR:** Long (L) + Medium (M) + Short (S) exposure: $\text{HDR} = w_L \cdot L + w_M \cdot M + w_S \cdot S$ where weights are computed per-pixel based on saturation
- **Merge formula (simplified):**
  - Where $L < \text{sat\_thresh}_L$: use $L$ (best SNR)
  - Where $L \geq \text{sat\_thresh}_L$ and $M < \text{sat\_thresh}_M$: blend to $M$
  - Where $M \geq \text{sat\_thresh}_M$: use $S$
- **Ghost removal:** Per-pixel motion detection; where motion is detected, prefer shorter exposure to avoid ghosting
- **LTM:** Local Tone Mapping divides the frame into tiles (32×32), computes per-tile histogram, applies a spatially-varying curve
- Reference: Qualcomm Snapdragon 8 Gen 2 camera feature page

---

### 7.3 HiSilicon ZHDR + LS-HDR

- **ZHDR (Zero-delay HDR):** Hardware reads out alternating rows at different exposure times within one frame; no temporal motion between exposures → near-zero ghosting
  - Odd rows: long exposure (maximum SNR in shadows)
  - Even rows: short exposure (prevents highlight clipping)
  - ISP reconstructs full-resolution HDR via spatial interpolation between rows
- **LS-HDR:** 2-frame (long + short) merge for higher dynamic range than ZHDR
- **XD-Fusion HDR:** NPU detects moving subjects; dynamic regions use short-exposure content; static regions use long-exposure
- **Local tone mapping:** Multi-scale Laplacian pyramid (5 levels); each level compressed independently
- **Output:** 10-bit HDR10 with MaxCLL/MaxFALL metadata; Dolby Vision compatible (Kirin 9000)
- Reference: Huawei P50 Pro camera architecture; HDC 2021 camera session slides

---

### 7.4 MediaTek HDR-Vivid + Dolby Vision

- **HDR-Vivid:** China national HDR standard (T/UHD 005-2020); MediaTek Dimensity 9000 was the first mobile SoC to support HDR-Vivid capture
  - Dynamic metadata per scene: content light levels, display mapping hints
  - Wider color gamut: BT.2020 primaries
- **Dolby Vision capture:** From Dimensity 9200; ISP generates Dolby Vision IQ metadata per frame
- **Staggered HDR:** Supports DOL-HDR sensors (2-frame and 3-frame); dedicated HDR Fusion Engine in Imagiq ISP
- **MFHDR:** Multi-frame alternating exposure bracketing; optical flow alignment; up to 3-frame stack
- **AI-HDR:** APU classifies scene; selects optimal HDR strategy (SHDR vs MFHDR vs single-frame LTM)
- Reference: https://corp.mediatek.com/news-events/press-releases/mediatek-imagiq-790-brings-flagship-camera-innovations-to-premium-5g-smartphones; https://i.mediatek.com/dimensity-9200

---

### 7.5 Platform Comparison

| Feature | Qualcomm Spectra | HiSilicon Kirin | MediaTek Imagiq |
|---------|-----------------|-----------------|-----------------|
| Staggered HDR | ✓ (SHDR, 2–3 frames) | ✓ (ZHDR row-level + LS-HDR) | ✓ (DOL-HDR, 2–3 frames) |
| Multi-frame HDR | ✓ (MFHDR, up to 9 frames) | ✓ (XD-Fusion HDR) | ✓ (MFHDR, 3 frames) |
| Ghost removal | Motion detection + short-exposure priority | NPU semantic segmentation + motion detection | Optical flow motion map + short-exposure priority |
| Local tone mapping | LTM (tile-adaptive) | Laplacian multi-scale pyramid | Bilateral guided filter LTM |
| HDR standard support | HDR10, HLG, Dolby Vision | HDR10, Dolby Vision | HDR10, HDR-Vivid, Dolby Vision |
| AI HDR | ✓ (Cognitive ISP) | ✓ (XD-Fusion) | ✓ (APU AI-HDR) |

---

## References

- **Debevec, P. & Malik, J. (1997).** Recovering High Dynamic Range Radiance Maps from Photographs. *SIGGRAPH 1997.*
- **Mertens, T., Kautz, J., & Van Reeth, F. (2007).** Exposure Fusion. *Pacific Graphics 2007.*
- **Mantiuk, R., Kim, K. J., Rempel, A. G., & Heidrich, W. (2011).** HDR-VDP-2: A calibrated visual metric for visibility and quality predictions in all luminance conditions. *SIGGRAPH 2011.*
- **Liba, O., Murthy, K., Yun-Ta Tsai, et al. (2019).** Handheld Mobile Photography in Very Low Light. *SIGGRAPH Asia 2019.* (Google Night Sight)
- **Reinhard, E., Stark, M., Shirley, P., & Ferwerda, J. (2002).** Photographic Tone Reproduction for Digital Images. *SIGGRAPH 2002.*
- **OpenCV HDR Tutorial:** https://docs.opencv.org/4.x/d3/db7/tutorial_hdr_imaging.html
