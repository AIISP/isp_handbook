# Part 2 HDR Reading Guide (HDR学习路径图)

> **Nature of this document: Learning Path Navigation**
> This document is not a standalone technical chapter but a **cross-volume reading roadmap** for HDR-related knowledge.
> HDR core technical content is distributed across the chapters listed below; reading them in order is recommended.

> **Chapter type:** Reading Guide (Navigation Guide); no new theoretical content, pure navigation index
> **Global number:** Ch47 (buffer zone, Ch46–Ch50)
> **Chapters covered:** Ch07 · Ch27 · Ch35 · Ch38 · Ch57 · Ch26 · Ch06
> **Target readers:** All readers (recommended to read this guide before starting any HDR-related chapters)

---

## Why Is This Guide Needed?

HDR (High Dynamic Range) imaging permeates the entire ISP system and is distributed across multiple chapters in this handbook, each approaching the topic from a different level of abstraction. Without a guide, readers can easily get lost between chapters — unclear about which to read first, what scope each chapter covers, and how they combine into a complete HDR imaging system.

The luminance range of a real-world scene can reach **10⁶ : 1** (approximately 20 stops), while a typical camera sensor can only capture **10³ : 1** (approximately 10 stops) in a single frame, and a standard SDR display can only render **10² : 1** (approximately 6–8 stops). The core mission of HDR technology is to bridge the gaps between these three.

---

## I. Full Handbook HDR Chapter Navigation Table

The following table categorizes all HDR-related chapters in the handbook by technical layer, for quick reference:

| Layer | Chapter | Volume | Core Content | Reading Priority |
|-------|---------|--------|--------------|-----------------|
| **Physical Foundation** | Volume 1, Chapter 7 | Part1 | Dynamic range concepts, sensor DR measurement, classical global TMO operators | Required |
| **Acquisition and Merging** | Volume 2, Chapter 11 | Part2 | Multi-exposure HDR frame merging, CRF calibration, ghost removal, RAW-domain MFHDR | Required |
| **Local Tone Mapping** | Volume 2, Chapter 18 | Part2 | CLAHE, bilateral filter TMO, guided filter TMO, local gain map | Recommended |
| **HDR Display Signal Chain** | Volume 2, Chapter 20 | Part2 | PQ/HLG/Dolby Vision, HDR10/HDR10+, EETMO | Required |
| **Wide Color Gamut Pipeline** | Volume 2, Chapter 21 | Part2 | WCG, BT.2020 gamut mapping, HDR+WCG joint pipeline | Recommended |
| **Night Mode Multi-Frame HDR** | Volume 2, Chapter 26 | Part2 | Burst+HDR synthesis, dark-field noise suppression, handheld night mode alignment | Recommended |
| **AI Tone Mapping** | Volume 3, Chapter 7 | Part3 | HDRNet, CSRNet, STAR video TMO, 4D-LUT | Advanced |

> Note: Chapter numbering in this handbook follows the "each volume independently starts from ch01" rule. "Volume 2, Chapter 11" above corresponds to `part2_traditional_isp/ch11_hdr_merge`, and so on. Cross-volume reference format is uniformly written as "Volume N, Chapter M."

---

## II. Five-Chapter Core Relationship Diagram

```
┌─────────────────────────────────────────────────────────────┐
│              Real-World Scene (luminance range 10⁶:1)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
          ┌────────────────────────────────────┐
          │  Physical Dynamic Range Foundation  │
          │      (Volume 1, Chapter 7)          │
          │  Sensor DR measurement, HDR physics │
          │  Classical global TMO:              │
          │  Reinhard / Drago / Mantiuk         │
          └────────────────────────────────────┘
                              │
                              ▼
          ┌────────────────────────────────────┐
          │  Multi-Frame HDR Merging            │
          │    (Volume 2, Chapter 11)           │
          │  EV exposure sequence capture,      │
          │  CRF calibration (Debevec),         │
          │  Irradiance map reconstruction,     │
          │  Ghost removal                      │
          │  RAW-domain MFHDR                   │
          │  (mainstream mobile compute photo)  │
          └────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
  ┌──────────────────────┐       ┌──────────────────────────┐
  │  Local Tone Mapping  │       │   HDR Display Signal Chain │
  │  (Vol. 2, Ch. 18)    │       │   (Vol. 2, Ch. 20)         │
  │  Bilateral filter    │       │  PQ/ST2084, HLG            │
  │  base decomposition  │       │  HDR10 / HDR10+            │
  │  Guided filter TMO   │       │  Dolby Vision dynamic meta │
  │  CLAHE histogram EQ  │       │  End-to-end TMO (EETMO)    │
  │  Local gain map      │       │                            │
  └──────────────────────┘       └──────────────────────────┘
              │                               │
              ▼                               │
  ┌──────────────────────┐                   │
  │  AI-Driven Tone Map  │                   │
  │  (Vol. 3, Ch. 7)     │◄──────────────────┘
  │  HDRNet bilateral    │
  │  grid learning       │
  │  CSRNet neural S     │
  │  curve               │
  │  STAR video temporal │
  │  TMO                 │
  │  4D-LUT end-to-end   │
  │  ISP                 │
  └──────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│         Final Display (HDR screen / SDR backward compat.)    │
└─────────────────────────────────────────────────────────────┘
```

> Note: Volume 2, Chapter 20 (display signal chain) sits alongside Ch35/Ch57 — it focuses on signal format engineering standards rather than TMO algorithms themselves. The two paths converge at the display side. Volume 2, Chapter 26 (night mode multi-frame) is a mobile-specific extension of Chapter 11 and is not separately expanded in the diagram above.

---

## III. One-Sentence Positioning for Each Chapter

**Volume 1, Chapter 7 — Dynamic Range and HDR Fundamentals**
> Establishes conceptual foundation: the physical meaning and measurement methods of sensor DR (SNR curve, DSNU/PRNU), the essential difference between HDR and SDR, and the mathematical principles of global tone mapping operators (Reinhard/Drago/Mantiuk).
> Does NOT cover: multi-frame synthesis → Volume 2, Chapter 11; local TMO → Volume 2, Chapter 18; display standards → Volume 2, Chapter 20; AI methods → Volume 3, Chapter 7.

**Volume 2, Chapter 11 — HDR Frame Merging**
> Solves "how to synthesize an HDR image from multiple photos at different EV exposures": camera response function (CRF) calibration (Debevec estimation), irradiance map reconstruction, ghost removal, RAW-domain multi-frame HDR merging (MFHDR).
> The output of this chapter is a linear irradiance map, which still requires TMO before it can be rendered on a standard display.

**Volume 2, Chapter 18 — Local Tone Mapping**
> Solves the "loss of detail in global TMO" problem: bilateral filter base decomposition, guided filter TMO, CLAHE adaptive histogram equalization, detail layer enhancement and local gain map.
> This chapter focuses exclusively on TMO algorithms targeting SDR displays; it does not cover HDR display standards (→ Volume 2, Chapter 20).

**Volume 2, Chapter 20 — HDR Display Signal Chain**
> Solves "how HDR content is correctly displayed on HDR screens": PQ perceptual quantization curve / ST 2084 standard, HLG hybrid log-gamma (broadcast scenario), HDR10/HDR10+ static/dynamic metadata, Dolby Vision dynamic metadata, end-to-end tone mapping (EETMO).
> This chapter focuses on signal formats and display standards; TMO algorithms are covered in Volume 2, Chapter 18.

**Volume 2, Chapter 21 — Wide Color Gamut Pipeline**
> Solves "the color gamut expansion challenges that accompany HDR": BT.2020 color gamut coverage, WCG pipeline design, HDR+WCG joint tone/gamut mapping, and backward-compatibility strategy with SDR/BT.709.

**Volume 2, Chapter 26 — Night Mode Multi-Frame HDR**
> HDR-focused treatment for mobile night scenes: handheld multi-frame alignment (optical flow/feature matching), dark-field noise suppression, Burst+HDR joint synthesis — the engineering implementation of Volume 2, Chapter 11 in computational photography scenarios.

**Volume 3, Chapter 7 — AI-Driven Tone Mapping**
> Uses deep learning to replace or enhance traditional TMO: HDRNet bilateral grid learning, CSRNet neural S-curve adjustment, STAR video temporal TMO, 4D-LUT end-to-end ISP tone mapping.
> Can be understood as the deep learning upgrade of the local TMO in Volume 2, Chapter 18.

---

## IV. HDR Technology Roadmap: From Scene Luminance to Final Display

The following is an end-to-end flowchart of a complete HDR pipeline, covering acquisition, processing, encoding, and display stages:

```
┌──────────────────────────────────────────────────────────┐
│  STEP 1: Scene Luminance Capture                          │
│                                                          │
│  Real scene (Luminance: 0.001 cd/m² ~ 100,000 cd/m²)     │
│        │                                                 │
│        ├─ Single-frame capture (limited by sensor         │
│        │    ~12–14 stops DR)                              │
│        └─ Multi-frame/multi-exposure capture              │
│             (AE bracket / RAW burst)                     │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 2: RAW-Domain HDR Merging (Vol. 2, Ch. 11 / Ch. 26) │
│                                                          │
│  Multi-EV sequence ──► CRF calibration                   │
│                    ──► Irradiance map reconstruction      │
│  RAW burst       ──► Alignment (optical flow)            │
│                  ──► Ghost detection & removal           │
│                  ──► Weighted merging (exposure fusion)  │
│                                                          │
│  Output: Linear HDR irradiance map                       │
│          (32-bit float / 16-bit RAW HDR)                 │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 3: Tone Mapping (TMO)                               │
│                                                          │
│  Global TMO (Volume 1, Chapter 7)                        │
│    Reinhard: L_d = L / (1 + L)                           │
│    Drago: logarithmic adaptive compression               │
│    Mantiuk: perceptual contrast model                    │
│                                                          │
│  Local TMO (Volume 2, Chapter 18)                        │
│    Bilateral filter base decomp ──► detail enhance       │
│                               ──► local gain map         │
│    CLAHE block-adaptive histogram equalization           │
│    Guided filter TMO (edge-preserving)                   │
│                                                          │
│  AI TMO (Volume 3, Chapter 7)                            │
│    HDRNet bilateral grid / CSRNet neural curve / 4D-LUT  │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 4: Color Gamut Mapping (Volume 2, Chapter 21)       │
│                                                          │
│  Scene-referred (Linear) ──► Display-referred            │
│  BT.2020 → BT.709 (SDR target)                           │
│  BT.2020 → BT.2020 (HDR target, preserve wide gamut)     │
│  Joint tone/gamut mapping (HDR+WCG pipeline)             │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 5: HDR Signal Encoding and Transmission            │
│          (Volume 2, Chapter 20)                          │
│                                                          │
│  HDR display targets:                                    │
│    PQ/ST2084 EOTF ──► HDR10 (static metadata             │
│                            MaxCLL/MaxFALL)               │
│                   ──► HDR10+ (dynamic metadata,          │
│                            per-scene)                    │
│                   ──► Dolby Vision (per-frame            │
│                            dynamic metadata)             │
│                                                          │
│  Broadcast/live targets:                                 │
│    HLG (hybrid log-gamma, SDR backward compatible)       │
│                                                          │
│  SDR compatible output:                                  │
│    EETMO (end-to-end tone mapping, HDR→SDR fallback)     │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 6: Final Display                                    │
│                                                          │
│  HDR display (peak luminance 600–4000 nits,              │
│               EOTF = PQ/HLG)                             │
│  SDR display (peak luminance 100–400 nits,               │
│               EOTF = sRGB/BT.1886)                       │
│  Mobile screen (HDR10/Dolby Vision certified,            │
│                 local dimming)                           │
└──────────────────────────────────────────────────────────┘
```

---

## V. Quick Comparison of the Three Major HDR Transmission Standards

| Parameter | HDR10 | HLG | Dolby Vision |
|-----------|-------|-----|--------------|
| **EOTF** | PQ / ST 2084 | HLG (hybrid log-gamma) | PQ / ST 2084 |
| **Bit depth** | 10-bit | 10-bit (broadcast) / 12-bit (streaming) | 12-bit (full precision) |
| **Metadata type** | Static (MaxCLL / MaxFALL) | No metadata | Dynamic (per-frame / per-scene) |
| **Metadata delivery** | HDMI InfoFrame / SEI | None | RPU (auxiliary bitstream) |
| **Peak luminance target** | 1000 nits (common) / up to 10,000 nits | 1000 nits (reference display) | Up to 10,000 nits (spec), 4000 nits (typical) |
| **SDR backward compatibility** | No (requires EETMO) | Yes (HLG signal usable on SDR display, slightly dim) | No (requires EETMO / SDR base layer) |
| **Licensing / cost** | Free open standard (HDMI Forum) | Free open standard (BBC + NHK) | Commercial license (Dolby Laboratories) |
| **Primary application** | Streaming (Netflix/Disney+/Apple TV+), UHD Blu-ray | Broadcast TV (live, satellite), YouTube HDR | Premium streaming (Netflix/Apple TV), cinema, high-end phones |
| **Color gamut** | BT.2020 (content-defined) / BT.709 (some content) | BT.2020 | BT.2020 (mandatory) |
| **Dynamic metadata support** | No (HDR10+ extension adds this) | No | Yes (core feature) |
| **Hardware support** | Widest — virtually all HDR devices | Widely adopted in broadcast equipment, moderate consumer display support | Requires Dolby Vision-certified chip, lower coverage than HDR10 |

> **HDR10+** is a Samsung-led upgrade extension of HDR10 that introduces dynamic metadata (per-scene), free to license, backward compatible with HDR10, and an open alternative to Dolby Vision.

---

## VI. HDR Image Quality Assessment Quick Reference

HDR image quality assessment cannot simply reuse SDR metrics like PSNR/SSIM; perceptual-domain or HDR-specific metrics are required.

### 6.1 Commonly Used Assessment Metrics

| Metric | Full Name | Use Case | Tool/Implementation | Typical Threshold |
|--------|-----------|----------|---------------------|-------------------|
| **μ-PSNR** | Tone-Mapped PSNR | TMO output quality, HDR reconstruction assessment | OpenCV + custom script | >40 dB is good |
| **HDR-VDP-3** | HDR Visual Difference Predictor 3 | Perceptual distortion detection, HDR compression quality assessment | MATLAB/Python (official release) | Q score >7.5 is good |
| **TMQI** | Tone-Mapped Quality Index | Specifically evaluates structural fidelity and statistical naturalness of TMO output | MATLAB official implementation | >0.85 is excellent |
| **SSIM** | Structural Similarity | Preliminary SDR-domain assessment (not recommended as sole HDR metric) | scikit-image | >0.95 as reference |
| **PU-PSNR** | Perceptually Uniform PSNR | Computes PSNR in perceptually uniform space, suitable for HDR | Included in HDR-VDP toolkit | >40 dB is good |
| **FLIP** | ꟻLIP (perceptual difference map) | Real-time rendering / HDR frame difference visualization | NVIDIA official Python package | Mean error <0.1 |

### 6.2 Recommended Assessment Toolchain

```
HDR image pair (reference + test image)
        │
        ├─ Format normalization (.hdr / .exr → OpenEXR 32-bit float)
        │        Tools: OpenImageIO (oiiotool), ImageMagick, dcraw
        │
        ├─ Post-tone-mapping assessment (μ-PSNR / TMQI)
        │        Applicable: evaluating TMO algorithm output quality
        │        Note: TMO choice affects results; fix the reference TMO
        │
        ├─ Perceptual-domain assessment (HDR-VDP-3 / PU-PSNR)
        │        Applicable: compression artifacts, contrast distortion,
        │                    HDR encode/decode quality
        │        Tool: http://hdrvdp.sourceforge.net/
        │
        └─ Video sequence assessment (add temporal stability metrics)
                 Metrics: inter-frame TMQI variance, temporal SSIM diff
                 Applicable: evaluating flicker suppression in STAR-style video TMO
```

### 6.3 Important Notes

- HDR-VDP-3 requires specifying display parameters (peak luminance, black level, viewing distance); results are strongly tied to the display device, so comparison experiments must fix the display parameters.
- μ-PSNR is highly sensitive to the choice of TMO; publications must clearly state the TMO used and its parameters.
- TMQI balances two sub-metrics — "structural fidelity" and "statistical naturalness" — and it is recommended to report both individually rather than only the composite score.

---

## VII. Common HDR Tuning Pitfalls

### Pitfall 1: Highlight Clipping

**Symptom:** In a synthesized HDR image, large areas of the highlights appear as pure white with all detail completely lost.

**Causes:**
- Saturated pixels were not correctly excluded from the contribution during multi-exposure merging
- The coverage of the shortest-exposure frame is insufficient; the brightest areas still exceed the sensor's full-well capacity

**Solutions:**
- During CRF reconstruction, set the weight of pixels with Z > 0.95×Z_max to zero (Debevec weight function)
- Add a shorter exposure bracket (e.g., EV-3 or shorter)
- Enable RAW-domain "highlight recovery": interpolate using non-overexposed channels

**Related chapter:** Volume 2, Chapter 11 — §Saturated Pixel Handling

---

### Pitfall 2: SDR Device Compatibility Failure (Incorrect SDR Fallback)

**Symptom:** HDR content on an SDR screen appears severely overexposed or has abnormal colors; overall brightness is unusable.

**Causes:**
- PQ-encoded signal is sent directly to an SDR display (PQ on an SDR display maps reference white at ~203 nits, resulting in extremely dark or abnormal output)
- EETMO (end-to-end tone mapping) or HLG fallback path is not implemented

**Solutions:**
- For broadcast scenarios, prefer HLG (naturally backward compatible with SDR)
- For streaming scenarios, provide an SDR version alongside the HDR main stream (dual stream or EETMO dynamically generated)
- In Dolby Vision, use the "SDR base layer" architecture for backward compatibility

**Related chapter:** Volume 2, Chapter 20 — §EETMO; Volume 2, Chapter 20 — §HLG Backward Compatibility

---

### Pitfall 3: Multi-Frame Merging Ghost Artifacts

**Symptom:** Moving objects in the synthesized HDR image exhibit ghosting (semi-transparent residual images), most pronounced on leaves, water surfaces, and pedestrians.

**Causes:**
- Motion exists between frames in the multi-exposure sequence; direct weighted averaging causes moving objects to appear at different positions in different exposure images

**Solutions:**
- **Detection method:** Compute per-frame luminance deviation maps relative to the reference frame; pixels exceeding the threshold are marked as ghost regions
- **Optical flow method:** First estimate inter-frame optical flow (e.g., FlowNet/PWC-Net), align then merge; suitable for rigid motion
- **Reference-frame method (Reference-based HDR):** Use the middle-exposure frame as reference; non-reference frames contribute only in non-ghost regions
- **Deep learning method:** AHDRNet, HDR-GAN, and similar end-to-end networks learn ghost region handling implicitly

**Related chapter:** Volume 2, Chapter 11 — §Ghost Removal; Volume 3, Chapter 2 — §End-to-End HDR Reconstruction

---

### Pitfall 4: PQ Peak Luminance Parameter Misconfiguration

**Symptom:** HDR10 content appears too dark on an HDR display, or highlight regions are incorrectly clipped.

**Causes:**
- MaxCLL (Maximum Content Light Level) and MaxFALL (Maximum Frame Average Light Level) are set inconsistently with the actual content
- The peak luminance of the reference display during production (e.g., 1000 nits) does not match the target display (e.g., 600 nits), and no adaptive tone mapping was applied

**Solutions:**
- Accurately measure or compute the true MaxCLL/MaxFALL of the content and write them into HDMI InfoFrame / SEI
- During content production, perform "display adaptive TMO" targeting the peak luminance of the intended display
- Use HDR10+ or Dolby Vision dynamic metadata to allow the display device to adapt automatically

**Related chapter:** Volume 2, Chapter 20 — §HDR10 Metadata; Volume 2, Chapter 20 — §Display Adaptive TMO

---

### Pitfall 5: Local TMO Halo Artifacts

**Symptom:** After local tone mapping, prominent bright/dark halo rings appear around high-contrast edges (e.g., window frames, tree trunks).

**Causes:**
- Inaccurate base layer estimation by the bilateral or guided filter; spatial smoothing radius too large at edges
- Local gain map changes abruptly at edges

**Solutions:**
- Reduce the spatial kernel radius (σ_s) of the bilateral filter; increase the range kernel radius (σ_r)
- Switch to guided filter (Guided Filter) to replace bilateral filter for better edge preservation
- Apply additional edge-aware smoothing (e.g., WLS filter) on the gain map
- AI TMO (HDRNet) implicitly avoids halo issues by learning the bilateral grid

**Related chapter:** Volume 2, Chapter 18 — §Halo Suppression; Volume 3, Chapter 7 — §HDRNet

---

### Pitfall 6: Video TMO Temporal Flickering

**Symptom:** After frame-by-frame tone mapping of an HDR video, abrupt luminance changes between adjacent frames produce a subjective "flickering" perception.

**Causes:**
- Independent per-frame estimation of the global gain factor causes gain jumps between adjacent frames
- Scene cuts or camera motion cause rapid changes in the histogram distribution

**Solutions:**
- Apply temporal low-pass filtering to the global gain factor (first-order exponential smoothing: α = 0.1~0.3)
- Use video-specific TMO (STAR, etc.) that explicitly models temporal stability constraints
- Handle scene cut points separately to avoid gain smoothing across shot boundaries

**Related chapter:** Volume 3, Chapter 7 — §STAR Video TMO

---

## VIII. Recommended Reading Paths

**Path A — ISP Algorithm Engineer (full-pipeline understanding)**
```
Volume 1, Chapter 7 (physical foundation)
  → Volume 2, Chapter 11 (multi-frame merging)
    → Volume 2, Chapter 18 (local TMO)
      → Volume 2, Chapter 20 (display chain)
        → Volume 3, Chapter 7 (AI TMO)
```

**Path B — Deep Learning Researcher (focus on AI methods)**
```
Volume 1, Chapter 7 §1–§2 (quick intro to DR physics, ~20 min)
  → Volume 2, Chapter 18 (traditional TMO baseline, establish comparison reference)
    → Volume 3, Chapter 7 (AI methods full chapter, in-depth reading)
```

**Path C — Display / Signal Engineer**
```
Volume 1, Chapter 7 §1 (conceptual overview)
  → Volume 2, Chapter 20 (full chapter: PQ/HLG/HDR10/Dolby Vision)
    → Volume 2, Chapter 21 (WCG color gamut pipeline)
```

**Path D — Mobile Computational Photography Engineer**
```
Volume 2, Chapter 11 (merging implementation)
  → Volume 2, Chapter 26 (night mode multi-frame HDR)
    → Volume 2, Chapter 18 (local TMO)
      → Volume 3, Chapter 7 (AI TMO end-to-end)
```

**Path E — HDR Video Engineer**
```
Volume 2, Chapter 20 (display chain and standards)
  → Volume 2, Chapter 18 (TMO algorithms)
    → Volume 3, Chapter 7 §STAR (video temporal TMO)
```

---

## IX. Knowledge Dependency Notes

| Dependency | Description |
|------------|-------------|
| Volume 2, Chapter 11 → Volume 1, Chapter 7 | Understanding "why multi-frame merging is needed" requires knowledge of sensor DR limitations (§1–§2) |
| Volume 2, Chapter 18 → Volume 2, Chapter 11 | The typical input to local TMO is the linear irradiance map output by Chapter 11, or a high-DR RAW frame |
| Volume 2, Chapter 20 → independently readable | Signal standards engineers can skip Chapters 7/11/18 and read Chapter 20 directly; coupling with TMO algorithm chapters is weak |
| Volume 2, Chapter 21 → Volume 2, Chapter 20 | The WCG pipeline is tightly integrated with HDR signal standards; reading Chapter 20 first is recommended |
| Volume 2, Chapter 26 → Volume 2, Chapter 11 | Night mode multi-frame is a mobile-specific extension of Chapter 11; the underlying principles are the same |
| Volume 3, Chapter 7 → Volume 2, Chapter 18 | The design objectives and evaluation metrics of AI TMO directly correspond to traditional local TMO; reading Chapter 18 first is recommended |
| Volume 3, Chapter 7 → Volume 2, Chapter 11 | The end-to-end ISP section of Chapter 7 involves the complete RAW-to-display chain; Chapter 11 background makes it easier to understand |

---

## X. Quick Index of Related Standards and References

| Standard / Reference | Content | Corresponding Chapter |
|---------------------|---------|----------------------|
| SMPTE ST 2084:2014 | PQ EOTF definition (perceptual quantization curve) | Volume 2, Chapter 20 |
| ITU-R BT.2100 | HDR television signal standard (includes PQ and HLG) | Volume 2, Chapter 20 |
| ITU-R BT.2408 | HDR content production operation guidelines | Volume 2, Chapter 20 |
| Debevec & Malik 1997 | CRF calibration and HDR irradiance map reconstruction | Volume 2, Chapter 11 |
| Reinhard et al. 2002 | Global/local Reinhard TMO | Volume 1, Chapter 7; Volume 2, Chapter 18 |
| Farbman et al. 2008 | WLS filter (edge-preserving smoothing) | Volume 2, Chapter 18 |
| Gharbi et al. 2017 | HDRNet (bilateral grid learning) | Volume 3, Chapter 7 |
| Eilertsen et al. 2017 | HDR-VDP assessment framework survey | Volume 4 (IQA chapters) |

---

*This guide chapter has no companion code notebook (pure navigation content). For runnable code examples of the HDR pipeline, refer to the *See §6 Code section for runnable examples.* files in each corresponding chapter.*
