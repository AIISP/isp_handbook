# Volume 4 Chapter 07: Computational Photography

> **Version:** v1.0 Draft

> **Pipeline Position:** Computational enhancement layer in the ISP back-end
> **Prerequisites:** Volume 1 Chapter 1 (ISP Pipeline Overview), Volume 2 Chapter 3 (Denoising), Volume 2 Chapter 10 (HDR Frame Merging)
> **Target Audience:** Algorithm engineers, product engineers

---

## §1 Theory: Definition and History of Computational Photography

### 1.1 What Is Computational Photography?

A smartphone sensor has roughly one-eighth the area of a full-frame camera sensor, and its lens is physically constrained from growing larger — yet flagship smartphones released after 2019 can rival entry-level DSLRs in low-light performance, dynamic range, and depth-of-field control. This is not the result of hardware advances alone; it is the result of computation. Capturing multiple frames, aligning them, and merging them — using algorithms to compensate for hardware limitations — is the essence of computational photography: **exchanging computation for hardware**.

Raskar & Tumblin (2011) **[11]** offered an academic definition: "The use of digital computation to capture, process, and display visual information in ways that extend or entirely replace traditional photographic processes." This breaks into three layers: the capture layer (changing how the sensor acquires data), the processing layer (multi-frame fusion, AI enhancement), and the display layer (HDR display, AR overlay). In engineering terms, the Google HDR+ paper (Hasinoff et al., 2016) **[7]** stated it most directly: "Instead of one long exposure, take many short exposures and merge them. The sensor can be small, the individual frame noisy — computation compensates."

### 1.2 Computational Photography vs. Traditional Photography

| Dimension | Traditional Photography | Computational Photography |
|-----------|------------------------|--------------------------|
| Method of overcoming core limits | Better optics, larger sensor | More frames, more compute |
| Dynamic range | Limited by sensor FWC vs. noise floor | Multi-frame HDR merging breaks physical limits |
| Noise control | Larger pixel pitch, low read-noise sensors | Multi-frame aligned averaging (SNR improves by √N) |
| Depth of field | Wide aperture for shallow DoF | Per-pixel depth estimation + synthetic bokeh |
| Resolution | Higher pixel density sensors | Multi-frame super-resolution reconstruction |
| Adaptation to illumination | Raise ISO (at the cost of noise) | Night mode multi-frame denoising + AI enhancement |
| Capture speed | Limited by single-frame exposure time | Trade-off between computational latency and perceptual quality |

### 1.3 The "Capture More, Compute More" Paradigm Shift

The traditional camera hardware roadmap was: larger sensor → lower noise → better image quality. Smartphone computational photography opened an entirely new roadmap: **exchanging computation for hardware**.

Google pioneered this paradigm in HDR+ (Hasinoff et al., 2016):
> "Instead of one long exposure, take many short exposures and merge them. The sensor can be small, the individual frame noisy — computation compensates."

This philosophy is now industry consensus — Apple ProRAW, Samsung Expert RAW, and Huawei Super Night Mode are all variants of it. Pushing a 1/1.56-inch sensor to an experience approaching medium format is achieved through dozens of computational iterations after each shutter press, not through optical system upgrades.

---

## §2 Core Techniques

### 2.1 Computational Photography Technology Map

| Technique | Name | Core Principle | Representative Paper |
|-----------|------|----------------|---------------------|
| Multi-Frame HDR | Multi-Frame HDR | Exposure bracketing + alignment + fusion | Hasinoff et al., SIGGRAPH Asia 2016 |
| Night Mode | Night Mode | Merging many short exposures, √N SNR gain | Liba et al., SIGGRAPH Asia 2019 |
| Portrait Mode | Portrait Mode | Depth estimation + synthetic bokeh | Wadhwa et al., ACM TOG 2018 |
| Computational Zoom | Computational Zoom | Multi-camera fusion + digital super-resolution | Wronski et al., ACM TOG 2019 |
| Computational Flash | Computational Flash | Flash/no-flash pair fusion | Petschnigg et al., SIGGRAPH 2004 |
| Semantic-Driven ISP | Semantic-Driven ISP | Scene understanding → algorithm selection → parameter tuning | Chen et al., CVPR 2021 |

### Portrait Mode: Synthetic Depth-of-Field

A smartphone lens at f/1.8 produces a depth of field that is far shallower than the same field of view on a DSLR, yet still far deeper than the background blur users expect. Portrait Mode estimates a per-pixel depth map and applies spatially varying blur — with increasing blur strength at greater distances from the subject — to synthesize an artificially shallow depth-of-field effect.

**Depth Estimation Methods:**

1. **Dual-pixel / dual-aperture stereo:** Two sub-aperture images (from a dual-pixel sensor or a dual-camera module) provide a stereo baseline. Disparity is estimated via semi-global matching or a learned cost-volume network. Depth accuracy: relative error is typically 2–5% at subject distances of 0.5–3 m **[1]**.

2. **DNN monocular depth estimation:** Monocular depth networks (e.g., MiDaS, DPT) infer depth from monocular cues (perspective, texture gradients, occlusion). Faster but less accurate; used as a fallback when stereo information is unavailable.

3. **LiDAR-assisted depth (when available):** ToF LiDAR provides sparse but accurate depth points; a learned completion network densifies the depth map.

**Bokeh Rendering:**

The per-pixel Circle-of-Confusion (CoC) diameter is:

```
CoC(d) = f * |d - d_focus| / (f_N * d)
```

where `f` is the focal length, `f_N` is the f-number (e.g., f_N=1.8 for f/1.8; **note: do not confuse with N, the frame count used elsewhere in this chapter**), `d` is the subject distance, and `d_focus` is the focus distance. The bokeh effect is synthesized by convolving the image with a spatially varying disk kernel of diameter CoC(d). High-quality implementations use layered alpha compositing to correctly handle foreground occlusion.

**Known Limitations:** Depth estimation is unreliable at fine hair, fur, or transparent edges. Edge-adaptive bilateral filtering of the depth map reduces halo artifacts.

---

### Night Mode: Multi-Frame Alignment and Averaging

In low-light conditions, a single long exposure risks motion blur, while a single short exposure is dominated by read noise. Night Mode captures N short-exposure frames and merges them, improving signal-to-noise ratio (SNR) by a factor of √N.

**SNR Derivation:**

**Two-component noise model:**
- Shot noise (Poisson): σ²_shot = S (variance equals the signal in electrons)
- Read noise (Gaussian): σ²_read = σ_r² (constant per pixel; typically 3–6 e⁻ on modern sensors)
- Total single-frame noise variance: σ²_total = σ²_shot + σ²_read = S + σ_r²

**N-frame averaging derivation:**
- Averaged signal: S̄ = (S₁ + S₂ + ... + S_N) / N = S (signal unchanged)
- Averaged noise variance: Var[noise_avg] = N · σ²_total / N² = σ²_total / N
- Therefore: SNR_N = S / sqrt(σ²_total / N) = sqrt(N) · S / sqrt(σ²_total) = sqrt(N) · SNR_1

In the shot-noise-dominated regime (S >> σ_r², typical daylight scene):
  SNR_N ≈ sqrt(N·S) ∝ sqrt(N)

In the read-noise-dominated regime (S << σ_r², extremely dark scene):
  SNR_N ≈ S·sqrt(N)/σ_r ∝ sqrt(N)

**Conclusion:** In both regimes the SNR improvement is sqrt(N).

Let each frame carry signal `s` corrupted by i.i.d. noise `X_i` with variance `σ²`:

```
frame_i = s + X_i,   X_i ~ iid(0, σ²)
```

N-frame mean:

```
mean_N = (1/N) * Σ_i (s + X_i)
       = s + (1/N) * Σ_i X_i
```

By linearity of variance for independent variables:

```
Var(mean_N) = Var( (1/N) * Σ_i X_i )
            = (1/N²) * Σ_i Var(X_i)
            = (1/N²) * N * σ²
            = σ² / N
```

Therefore:

```
SNR_N = s / sqrt(σ²/N) = √N * (s/σ) = √N * SNR_1
```

Every doubling of frame count yields approximately +3 dB (≈3.01 dB) SNR gain (from SNR∝√N, doubling N gives a √2× improvement = 20·log₁₀√2) **[7]**. This is the theoretical upper bound under the assumption of perfect alignment; in practice the gain is slightly lower due to residual alignment error.

**Frame Alignment:**

Frames must be aligned to sub-pixel accuracy before averaging. The standard approach is hierarchical optical flow (e.g., Lucas-Kanade pyramid) or learned alignment (e.g., PWCNet). Alignment accuracy must be < 0.5 px RMS to avoid blurring high-frequency detail. Frames whose alignment error exceeds a threshold are excluded from the merge.

**Ghost Detection:**

Moving objects (hands, leaves, faces) produce ghosting when a pixel is inconsistent across frames. Each candidate frame is compared to the reference frame: if the per-pixel difference exceeds threshold `T_ghost`, that pixel's weight is reduced or excluded from the average. This transforms the naive mean into a robust merge:

```
output(x) = Σ_i w_i(x) * frame_i(x)  /  Σ_i w_i(x)
w_i(x) = exp( -||frame_i(x) - ref(x)||² / T_ghost² )
```

---

### Smart HDR: Exposure Bracketing + Ghost Detection + Tone Mapping

**Capture:** 2–5 exposures are captured at different EVs (e.g., −2, 0, +2 EV). On mobile sensors with rolling shutter, bracketed exposures are taken across consecutive frames with scene-change detection that aborts if the scene moves too much.

**Ghost Detection:** Adjacent exposures are aligned and compared. If a region shows temporal inconsistency (a moving person, a waving flag), only the frame closest to the correct exposure contributes to that region, to avoid ghosting.

**Fusion:** Standard Mertens multi-exposure fusion assigns per-pixel weights according to three quality criteria:
- *Contrast:* Laplacian energy of the exposure image.
- *Saturation:* Standard deviation of the RGB channels.
- *Exposedness:* Gaussian distance from the mid-tone (0.5).

**Tone Mapping:** Maps the fused HDR image into display range. Common operators:
- *Drago:* Logarithmic; suited to very high dynamic range.
- *Reinhard:* `L_display = L / (1 + L)`, perceptually smooth.
- *DNN-based:* Learned tone mapping conditioned on scene semantics; highest quality but most computationally expensive.

**Known Limitations:** Halo artifacts appear at high-contrast edges when the tone-mapping radius is small relative to object size. Using a guided filter or an edge-adaptive solver for the tone-mapping diffusion step mitigates this.

---

### Computational Zoom: Super-Resolution + Optical Zoom

Optical zoom achieves lossless magnification at the cost of hardware (a telephoto lens). Computational zoom uses single-image or multi-image super-resolution to bridge the gaps between discrete optical zoom steps.

- **Single-Image Super-Resolution (SISR):** Learned upsampling (ESRGAN, Real-ESRGAN) recovers perceptually high-frequency detail from a single frame. 2× upsampling works well; 4×+ introduces artifacts.
- **Multi-Frame Super-Resolution:** N slightly shifted frames (from hand tremor) provide sub-pixel diversity. Iterative back-projection or learned fusion networks reconstruct a higher-resolution output. Used in Google Super-Res Zoom.
- **Hybrid Optical + Computational Zoom:** Switches to optical zoom at available discrete focal lengths; super-resolution fills in fractional zoom levels.

---

## §3 Calibration

### Night Mode Alignment Calibration

- **Alignment accuracy threshold:** RMS displacement error < 0.5 px across all regions. Measured by shooting a static grid target under identical conditions and measuring the residual optical flow after alignment.
- **Temporal noise characterization:** Measure read-noise σ at each ISO to set the correct ghost detection threshold `T_ghost = k * σ` (typically k=3–5).

### Portrait Mode Depth Calibration

- **Depth ground truth:** Use an optical profilometer or LiDAR reference at target distances (0.5 m, 1 m, 1.5 m, 2 m, 3 m).
- **Depth accuracy metric:** RMSE between estimated depth and LiDAR ground truth, normalized by ground-truth depth: relative RMSE < 5% **[6]**.
- **Temperature / lens variation:** Repeat calibration at 0°C and 40°C, as lens mechanical properties shift slightly with temperature.

### Computational Zoom Multi-Camera Calibration

- **Parallax Calibration:** The parallax between wide-angle and telephoto depends on the inter-camera baseline (typically 5–15 mm) and scene depth. For close subjects (< 1 m) accurate depth sensing is required to eliminate parallax artifacts. Calibration procedure: shoot a checkerboard target at multiple depth planes (0.5 m, 1 m, 2 m, 5 m) and measure the wide-to-telephoto alignment error.
- **Cross-Camera Color Calibration:** Wide-angle and telephoto lenses differ in AR coating and Chief Ray Angle (CRA), resulting in color temperature offsets of 150–300 K for the same scene. Calibration method: shoot a ColorChecker under D65 illumination, compute a CCM for each camera separately, and align the telephoto color to the wide-angle reference in software.

---

## §4 Tuning

### Night Mode: Choosing the Frame Count N

The choice of N involves three-way trade-offs:

| N   | SNR Gain (dB) | Per-Frame Shutter | Total Capture Time (approx.) | Motion Ghost Risk |
|-----|--------------|-------------------|------------------------------|-------------------|
| 1   | 0            | 1/15 s            | 67 ms                        | Low               |
| 4   | +6           | 1/30 s            | 130 ms                       | Medium            |
| 8   | +9           | 1/60 s            | 133 ms                       | Medium-High       |
| 16  | +12          | 1/100 s           | 160 ms                       | High              |

In practice, N is chosen dynamically: using scene motion estimation and ambient illuminance, the system selects the largest N for which the ghosting probability remains below a threshold.

### Portrait Mode: Blur Radius and Depth Confidence

- When depth confidence is low (σ_d > threshold), reduce the blur radius to avoid edge artifacts rather than applying the full synthetic depth-of-field.
- Tune the confidence-to-blur mapping as a per-device 1D lookup table to match user preferences for the specific bokeh aesthetic.

---

## §5 Limitations and Engineering Pitfalls

| Feature | Artifact | Root Cause | Mitigation |
|---------|----------|------------|------------|
| Night Mode | Motion blur / ghosting | Subject movement between frames | Ghost detection weight map; exclude outliers |
| Night Mode | Color fringing at edges | Misalignment of chroma channels | Align chroma channels independently |
| Portrait Mode | Halo at hair / fur edges | Depth discontinuities at fine structures | Edge-adaptive bilateral filtering of the depth map |
| Portrait Mode | Incorrect depth at glass | Transparent surfaces confuse stereo matching | Detect transparency; disable blur |
| Smart HDR | Tone-mapping halo | Local tone mapping over-sharpening | Increase diffusion radius or use a guided filter |
| Computational Zoom | Super-resolution ringing at high contrast | ESRGAN over-sharpening | Reduce perceptual loss weight; use SSIM |

---

## §6 Evaluation

### Night Mode

- **SNR improvement vs. √N theory:** Capture uniform gray patches at each value of N; measure SNR per channel. Compare the measured improvement against the √N curve; expect no more than 1 dB below theory due to alignment loss.
- **PSNR gain:** PSNR_N = PSNR_1 + 10 * log10(N) (theoretical). Compare against measured PSNR gain from flat-field captures.
- **Motion ghost rate:** Among test frames containing a moving foreground subject, compute the fraction in which ghosting is visible to a trained evaluator. Target: < 5%.

### Portrait Mode

- **Depth estimation error:** Over 50+ test scenes, report RMSE between the estimated depth map and LiDAR ground truth in both absolute (cm) and relative (%) form.
- **Bokeh naturalness:** Measure BRISQUE and LPIPS (vs. a reference deep-DoF image) on a portrait test set.

---

## §7 Code

See `ch_computational_photography_code.ipynb` in this directory.

---

## §8 Core Algorithm Deep-Dive

### 8.1 Portrait Mode: Depth Estimation Accuracy and Bokeh Quality

- **Comparison of depth estimation sources:**

  | Method | Accuracy | Hardware Required | Near / Far |
  |--------|----------|-------------------|------------|
  | Binocular disparity | Medium (±5 cm @ 1 m) | Dual camera | Good at close range |
  | ToF / LiDAR | High (±1 cm) | ToF sensor | Best at close range |
  | Monocular DNN | Low (relative depth) | No extra hardware | All ranges |
  | PDAF phase map | Low (local) | Phase-detection pixels | Close range |

- **Sensitivity of bokeh quality to depth accuracy:** For a 2 m focus distance, f/1.8 equivalent, 1/1.5" sensor, a depth error of 10 cm causes a CoC error of approximately 2 px; the human-eye detection threshold is approximately 4 px, so depth accuracy must be better than 20 cm at 2 m.

### 8.2 Computational Zoom: Multi-Camera Fusion

- **Seamless zoom principle:** Wide-angle and telephoto are read simultaneously; cross-fading is applied in the transition zone (e.g., 2–3×).
- **Alignment challenges:** Wide-angle and telephoto have a view-angle difference (parallax); nearby objects undergo large displacement.
- **Fusion pipeline:**
  1. Feature-point matching (SuperPoint + LightGlue or traditional ORB)
  2. Homography estimation (RANSAC)
  3. Weighted fusion: $I_{zoom} = (1-\alpha) \cdot \text{warp}(I_{wide}) + \alpha \cdot I_{tele}$, where $\alpha = f(zoom\_ratio)$
- Reference implementation: the ZSL Fusion pipeline open-sourced by Google Camera.

### 8.3 Complete Night-Mode Multi-Frame Pipeline

```
Raw RAW frame sequence (4–30 frames)
    ↓ Reference frame selection (sharpest frame as anchor)
    ↓ Motion estimation (optical flow / block matching)
    ↓ Sub-pixel alignment (bicubic interpolation fine alignment)
    ↓ Temporal weight computation (w_i ∝ motion_confidence_i)
    ↓ Weighted averaging (in RAW domain, preserving color accuracy)
    ↓ Standard ISP pipeline processing
    ↓ AI super-resolution (optional)
    ↓ Output JPEG / HEIF
```

---

## §9 Computational Flash

### 9.1 Flash / No-Flash Pair Fusion Principles

Computational Flash (Petschnigg et al., SIGGRAPH 2004) leverages two images of the same scene:
- **Flash frame:** Sharp detail, but color is shifted toward white and background is overexposed.
- **No-flash frame:** Accurate color and ambient light, but high noise.

Fusion goal: color of the no-flash image + detail of the flash image.

**Bilateral Guided Fusion:**

$$I_{output} = \text{BilateralFilter}(I_{noflash},\ \sigma_s,\ \sigma_r \cdot I_{flash})$$

The flash image serves as the guide image in guided filtering applied to the no-flash image: low-frequency color information is preserved from the no-flash image, while high-frequency detail is "borrowed" from the flash image.

**Primary Failure Scenarios:**
- Subject is beyond the effective range of the flash (> 3 m): the flash and no-flash frames differ too much in brightness for fusion to succeed.
- Moving objects: inter-frame subject displacement causes ghosting.
- Reflective surfaces (glasses, mirrors): the flash creates specular highlights that cannot be correctly fused.

---

## §10 Semantic-Driven Computational Photography

### 10.1 Scene Understanding → Algorithm Selection → Parameter Tuning

Modern computational photography systems are driven by **semantic understanding**, adaptively selecting algorithms and parameters based on the scene:

```
Input RAW frame
    ↓ Semantic analysis (AI Scene Understanding)
    Output: scene labels + confidence scores
    (face / night / motion / backlight / food / document / ...)
    ↓ Algorithm selection
    Night   → activate multi-frame merge + AI denoising
    Face    → activate skin enhancement + face AF weighting
    Motion  → disable long-exposure night mode; use single-frame high ISO
    Backlit → activate HDR mode
    ↓ Parameter tuning
    Dynamically adjust denoising strength, sharpening coefficient, tone-mapping curve
    ↓ Output enhanced image
```

### 10.2 Challenges of Semantic-Driven Computational Photography

**Asymmetric cost of misclassification:**
- Misclassifying a motion scene as a static night scene → multi-frame long exposure produces motion blur; very poor user experience.
- Misclassifying a night scene as a motion scene → slightly lower image quality but no obvious failure; acceptable.

Therefore the error cost for semantic classification is asymmetric, and a conservative strategy (preferring not to activate aggressive algorithms) generally outperforms an aggressive one.

**Concurrent multi-label:** The same scene can simultaneously trigger multiple semantic labels (night + face + backlit), requiring priority rules to avoid parameter conflicts.

---

## §11 Hardware Acceleration Trends

### 11.1 Hardware Evolution in Computational Photography

| Era | Primary Processing Unit | Representative Computational Photography Feature | Typical Latency |
|-----|------------------------|--------------------------------------------------|----------------|
| 2010–2015 | CPU (ARM Cortex-A) | HDR merge (2 frames), denoising | 500 ms – 2 s |
| 2016–2018 | GPU (Mali / Adreno) | Multi-frame denoising (4–8 frames), depth estimation | 100–500 ms |
| 2019–2021 | Dedicated NPU / DSP | Night mode (16–30 frames), AI super-resolution | 50–200 ms |
| 2022– | Dedicated ISP Silicon | Real-time AI ISP, neural rendering | < 33 ms (30 fps real-time) |

**Trends in dedicated ISP silicon:**
- Google Tensor G3 ISP: integrates a dedicated neural network acceleration block that runs AI models directly in the ISP pipeline.
- Apple A17 Pro ISP: supports real-time ProRAW processing.
- Qualcomm Snapdragon 8 Gen 3 Spectra ISP: integrates the Hexagon NPU (approximately **34 TOPS**, third-party estimate; Qualcomm has not published an independent integer TOPS figure and officially states only "98% improvement" — see Appendix C §C.9) tightly coupled with the ISP; multi-frame processing performance is significantly improved over the predecessor 8 Gen 2 (total AI Engine approximately **34 TOPS**, including CPU+GPU+NPU+DSP, per Qualcomm official figures).

### 11.2 Computational Efficiency Gains from CPU to Dedicated Silicon

Processing efficiency evolution for multi-frame denoising (8 frames, 12 MP). The following figures are typical engineering reference values, sourced from Qualcomm Snapdragon technical white papers and industry benchmarks; actual values vary by implementation and workload:
- CPU (ARM A77 @ 2.8 GHz): approximately 1.2 s
- GPU (Adreno 660): approximately 280 ms
- NPU (Hexagon 780): approximately 85 ms
- Dedicated ISP block (Spectra 680): approximately 22 ms (approaching the 33 ms real-time 30 fps threshold)

---

## §12 Limitations and Extensions of Evaluation Metrics

### 12.1 Shortcomings of PSNR

Traditional image quality assessment relies primarily on PSNR (Peak Signal-to-Noise Ratio), but this has clear limitations in computational photography:

- **PSNR is a full-reference metric:** It requires comparison against a standard reference image, whereas the "correct output" in computational photography is not unique (different stylistic night-mode enhancements can all be correct).
- **PSNR does not correlate with subjective perception:** Two images that differ by 2 dB in PSNR may look far more different to human observers than two other images that differ by 5 dB in PSNR.
- **PSNR favors smoothness:** Multi-frame averaging improves PSNR, but excessive smoothing loses detail, making the subjective image quality worse.

### 12.2 Evaluation Metrics Specific to Computational Photography

| Metric | Type | Applicable Scenario | Limitation |
|--------|------|---------------------|------------|
| PSNR | Full-reference, pixel-level | Denoising baseline | Weak correlation with subjective perception |
| SSIM | Full-reference, structural similarity | Deblurring evaluation | Insensitive to fine texture |
| LPIPS | Full-reference, perceptual distance | Night mode, super-resolution quality | Requires reference image; slower to compute |
| NIQE | No-reference, statistical model | Large-scale automated evaluation | Biased toward specific styles |
| BRISQUE | No-reference, MSCN statistical features (spatial domain) | Quick quality screening | Not suitable for AI-enhanced images |
| MOS | Subjective scoring | Final quality acceptance | Time-consuming; high cost |
| Task-driven metrics | mAP / OCR accuracy, etc. | Machine vision applications | May diverge from human perception |

**Recommended evaluation framework:**
- R&D phase: PSNR + SSIM + LPIPS (full-reference, paired test set)
- Large-scale automated evaluation: NIQE + BRISQUE (no-reference)
- Product acceptance: MOS (subjective, 50+ evaluators)
- Machine vision applications: task-driven metrics

---

## §13 Research Frontiers

### 13.1 Neural Radiance Fields (NeRF) in Computational Photography

The core idea of Neural Radiance Fields (NeRF, Mildenhall et al., 2020) — using a neural network to implicitly represent a 3D scene and support high-quality rendering from arbitrary viewpoints — is being introduced into several directions of computational photography:

**NeRF + HDR Imaging (RawNeRF, Mildenhall et al., 2022):**
- Learns a NeRF from multiple RAW images at different exposures, outputting an HDR neural radiance field.
- Supports novel-view RAW/HDR image synthesis at arbitrary exposure.
- Solves the ghosting problem of traditional multi-exposure HDR (NeRF internally handles occlusion).

**NeRF + Night Scene (NeRF in the Dark, RawNeRF):**
- Captures sparse viewpoints in extremely dark scenes (ISO 6400+); NeRF uses multi-view consistency constraints to filter noise.
- Equivalent to multi-frame denoising, but from different viewpoints rather than the same viewpoint.

**Limitations:** NeRF training is slow (minutes to hours); inference is fast but capture still requires multiple viewpoints, making it unsuitable for single-shot mobile photography.

### 13.2 Diffusion Models in the Capture Pipeline

The high-quality image generation capability of generative diffusion models is being applied to:

- **Diffusion-based denoising (DiffIR, Xia et al., 2023):** Models denoising as a conditional diffusion process, conditioned on the noisy image to generate a clean image; quality surpasses discriminative methods, but inference latency is high (approximately 200–800 ms on an NPU).
- **Diffusion super-resolution (StableSR, Wang et al., IJCV 2024):** Uses the generative prior of Stable Diffusion for super-resolution; 4× super-resolution results approach real high-resolution images.
- **Capture-time guided diffusion:** Running a lightweight diffusion model at capture time to guide ISP parameter selection in real time — still at the research stage; significant engineering challenges remain.

---

## §14 Recent Advances: 2023–2025

### 14.1 3D Gaussian Splatting and Computational Photography

**3D Gaussian Splatting (3DGS, Kerbl et al., SIGGRAPH 2023)** is the most important 3D scene representation breakthrough since NeRF, with the core advantage of **real-time rendering**: on an NVIDIA RTX 3090, vanilla NeRF (Mildenhall et al., 2020) takes approximately 10 s/frame, while 3DGS achieves < 33 ms/frame (>30 fps), a gap exceeding 300×; compared to accelerated NeRF variants such as Instant-NGP (~100 ms/frame), 3DGS still holds a 3–5× speed advantage **[12]**.

**Application directions in computational photography:**

1. **3D-aided depth for synthetic DoF:** Reconstructing a 3DGS scene from a small number of multi-view images (3–5) extracts a high-accuracy depth map for portrait-mode bokeh rendering. Superior to monocular DNN depth estimation, inferior to ToF (but requires no additional hardware).

2. **GaussianEditor (Chen et al., ICCV 2023):** Text-guided 3D scene editing enabling precise deletion and replacement of background objects, extending "background replacement" to 3D-consistent edits.

3. **SpacetimeGaussians (Li et al., CVPR 2024):** Extends 3DGS to dynamic scenes, supporting 4D Gaussian representation reconstructed from multi-frame video — with direct application potential in multi-camera slow-motion (bullet-time) scenarios.

**Engineering constraints:** 3DGS reconstruction requires 5–10 multi-view images and is unsuitable for single-shot scenarios; current mobile GPU memory (8–12 GB) still poses challenges for real-time 3DGS rendering; practical deployment is expected to become feasible in 2025–2026 as GPU architectures advance.

---

### 14.2 Video Computational Photography: AI Video ISP

**Google Pixel 8 Video Boost (2023):** Extends the HDR+ multi-frame algorithm to video:
- Each video frame undergoes multi-frame RAW merging on the Tensor G3 TPU (equivalent to 30 HDR+ operations per second).
- Video Boost requires offline processing (batch processing after recording on-device or in the cloud); it is not a real-time pipeline.
- Measured SNR improvement for night-mode video: approximately 3–4 dB vs. single-frame HDR.

**Kuaishou KVQ (ECCV 2024) and video quality enhancement:**
- Kinetic Video Quality model: combines spatial and temporal blind quality assessment.
- Applicable to quality-driven adaptive denoising in computational photography video post-processing.
- SRCC = 0.891 on KoNViD-1k; SRCC = 0.833 on YT-UGC.

**Real-time AI video ISP hardware trends (2024–2025):**

| Platform | Video AI ISP Capability | Key Hardware |
|----------|------------------------|--------------|
| Apple A17 Pro | Real-time 4K ProRes + Dolby Vision | Neural Engine 35 TOPS (Apple official) + dedicated Video Processor |
| Qualcomm Snapdragon 8 Gen 3 | Real-time 8K HDR10+ video + AI-NR | Hexagon NPU + Spectra ISP tight coupling |
| Google Tensor G3 | Video Boost (offline TPU processing) | Dedicated ISP acceleration block + Edge TPU |
| MediaTek Dimensity 9300 | Real-time 4K 120 fps AI denoising | APU 790 (33 TOPS, MediaTek official) |

---

### 14.3 Neural Image Compression and Computational Photography

Traditional JPEG/HEIF compression assumes the image has already been processed by the ISP. **Neural Image Compression** attempts to jointly optimize compression and ISP processing:

**Representative works:**
- **Cheng et al. (CVPR 2020):** Attention-mechanism-based neural compression; PSNR exceeds BPG (HEVC Intra) by approximately 1.5 dB at the same bit rate **[14]**.
- **MLIC (Li et al., CVPR 2023):** Multi-Reference Entropy Model; compression efficiency approaching the limit of human visual sensitivity.
- **RAW-domain joint compression (Rawquant, ECCV 2024):** Directly compresses RAW data and integrates ISP processing into the decoder, avoiding the double information loss of ISP followed by compression.

**Engineering significance:** The core pain point of ProRAW files (25–95 MB) is their large size. If neural compression can reduce ProRAW MAX (48 MP) from 75 MB to < 20 MB without sacrificing post-processing headroom, it would be an important breakthrough for consumer computational photography.

---

### 14.4 Generative Priors in Computational Photography

**Problem:** In extreme low light (ISO 12800+), even 30-frame merging cannot recover sufficient detail because noise masks most high-frequency information.

**Generative prior approach:**

$$I_{restored} = \arg\min_I \underbrace{\|I - I_{noisy}\|^2}_{\text{data fidelity}} + \lambda \cdot \underbrace{(-\log p_{DM}(I))}_{\text{diffusion model prior}}$$

where $p_{DM}(I)$ is the probability density of a pre-trained diffusion model over clean natural images.

**Representative works:**
- **DiffBIR (Lin et al., ECCV 2024):** Two-stage pipeline: discriminative network for degradation removal + diffusion model for detail hallucination. Outperforms Real-ESRGAN in real scenes but controversial for texture hallucination (generated detail is not real).
- **OSEDiff (Wu et al., NeurIPS 2024):** Single-step diffusion super-resolution; inference latency reduced from 400 ms to 40 ms on an NPU via INT8 quantization + step distillation.
- **SUPIR (Yu et al., CVPR 2024):** Scales up to 20B parameters for general-purpose image restoration; robust to complex combinations of degradations.

**Engineering constraint:** The "detail" generated by diffusion models is fundamentally model prior, not real scene information. In forensic photography, medical imaging, and other contexts where authenticity is required, generative methods carry ethical risks. Consumer photography applications should include informed-consent disclosures.

---

## §15 Glossary

| Term | Full English Name | Definition |
|------|-------------------|------------|
| **Computational Photography** | Computational Photography | Imaging technology that uses computation to produce images beyond the physical limits of optics; the new paradigm of exchanging computation for hardware |
| **Synthetic Depth-of-Field** | Synthetic Depth-of-Field | Computational bokeh technique that simulates large-aperture shallow DoF via depth estimation + spatially varying convolution kernels |
| **Circle of Confusion** | Circle of Confusion (CoC) | The blur circle formed on the sensor by an out-of-focus object; its diameter determines the degree of bokeh: $\text{CoC}(d) = f \cdot |d-d_f|/(N \cdot d)$ |
| **Multi-Frame Super-Resolution** | Multi-Frame Super-Resolution | Technology that uses sub-pixel shifts between frames (from hand tremor or deliberate movement) to reconstruct a higher-resolution image than any single frame |
| **Ghost Artifact** | Ghost Artifact | In multi-frame merging, moving objects shift between frames and produce a translucent double image in the final output |
| **Exposure Fusion** | Exposure Fusion | Pixel-quality-weighted fusion of multiple images at different exposure values, an HDR processing approach that requires no global HDR tone mapping |
| **Guided Filter** | Guided Filter | A filter that uses a sharp image as a guide to perform edge-preserving smoothing on another image (e.g., a depth map or noisy image) |
| **3D Gaussian Splatting** | 3DGS | A 3D reconstruction method that represents scenes with anisotropic 3D Gaussian primitives, supporting real-time (< 33 ms/frame) novel-view rendering |
| **Neural Radiance Field** | Neural Radiance Field (NeRF) | Implicitly represents the radiance and density of a 3D scene using an MLP; supports high-quality novel-view synthesis from sparse views |
| **Neural Image Compression** | Neural Image Compression | End-to-end trained neural networks replacing JPEG/HEIF for image compression; maintains higher perceptual quality at lower bit rates |
| **Computational Zoom** | Computational Zoom | A hybrid zoom technique combining optical zoom (discrete focal-length switching) and digital super-resolution (continuous zoom interpolation) |
| **Semantic-Driven ISP** | Semantic-Driven ISP | An intelligent imaging pipeline that adaptively adjusts ISP algorithms and parameters based on scene semantic understanding (face / night / motion / food) |
| **Generative Prior** | Generative Prior | Implicit knowledge about the natural image distribution encoded in a pre-trained generative model (VAE, diffusion model), used as a regularization term in image restoration |
| **Video Boost** | Video Boost | The offline video HDR+ enhancement feature in the Google Pixel series; performs multi-frame RAW merging on video frames using the Tensor chip's TPU |

---



---

## Figures

![comp photo map](img/fig_comp_photo_map_ch.png)

*Figure 1. Computational photography technology landscape (Source: original illustration by the authors)*

![night mode snr](img/fig_night_mode_snr_ch.png)

*Figure 2. Night mode SNR analysis (Source: original illustration by the authors)*



---
![burst photography](img/fig_burst_photography_ch.png)

*Figure 3. Burst photography principles (Source: original illustration by the authors)*

*Figure 4. Computational photography processing pipeline (Source: original illustration by the authors)*

![computational photography survey](img/fig_computational_photography_survey_ch.png)

*Figure 5. Computational photography technology survey framework (Source: original illustration by the authors)*



---
![comp photo hardware evolution](img/fig_comp_photo_hardware_evolution_ch.png)

*Figure 6. Computational photography hardware evolution timeline (Source: original illustration by the authors)*

![multiframe pipeline detail](img/fig_multiframe_pipeline_detail_ch.png)

*Figure 7. Multi-frame processing pipeline detailed flow (Source: original illustration by the authors)*

![night mode quality](img/fig_night_mode_quality_ch.png)

*Figure 8. Night mode image quality comparison (Source: original illustration by the authors)*

## References

[1] Wadhwa et al., "Synthetic Depth-of-Field with a Single-Camera Mobile Phone", *ACM TOG*, 2018.

[2] Liba et al., "Handheld Mobile Photography in Very Low Light", *ACM TOG*, 2019.

[3] Wronski et al., "Handheld Multi-Frame Super-Resolution", *ACM TOG*, 2019.

[4] Mertens et al., "Exposure Fusion", *Pacific Graphics*, 2007.

[5] Reinhard et al., "High Dynamic Range Imaging", 2nd ed., Morgan Kaufmann, 2010.

[6] Ranftl et al., "Towards Robust Monocular Depth Estimation: Mixing Datasets", *IEEE TPAMI*, 2022.

[7] Hasinoff et al., "Burst Photography for High Dynamic Range and Low-Light Imaging on Mobile Cameras", *ACM TOG*, 2016.

[8] Petschnigg et al., "Digital Photography with Flash and No-Flash Image Pairs", *ACM TOG*, 2004.

[9] Mildenhall et al., "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis", *ECCV*, 2020.

[10] Mildenhall et al., "NeRF in the Dark: High Dynamic Range View Synthesis from Noisy Raw Images", *CVPR*, 2022.

[11] Raskar et al., "Computational Photography: Mastering New Techniques for Lenses, Lighting, and Sensors", A K Peters/CRC Press, 2011.

[12] Kerbl et al., "3D Gaussian Splatting for Real-Time Radiance Field Rendering", *ACM TOG*, 2023.

[13] Lin et al., "DiffBIR: Towards Blind Image Restoration with Generative Diffusion Prior", *ECCV*, 2024. arXiv:2308.15070

[14] Cheng et al., "Learned Image Compression with Discretized Gaussian Mixture Likelihoods and Attention Modules", *CVPR*, 2020.

[15] Yu et al., "SUPIR: Scaling Up to Excellence: Practicing Model Scaling for Photo-Realistic Image Restoration In the Wild", *CVPR*, 2024.
