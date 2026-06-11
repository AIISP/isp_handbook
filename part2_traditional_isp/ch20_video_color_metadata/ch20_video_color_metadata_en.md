# Part 2, Chapter 20: Video Color Metadata & Signaling

> **Position:** HDR Display Signal Chain (Ch. 19) → **Color Metadata Encapsulation & Signaling** (this chapter) → Wide Color Gamut Pipeline (Ch. 21)
> **Prerequisites:** Part 2 Ch. 19 (HDR Display Signal Chain: PQ/HLG/Dolby Vision transfer functions), Part 1 Ch. 05 (Color Science Fundamentals)
> **Audience:** Video ISP engineers, mobile multimedia engineers, streaming platform integration engineers

> **Distinction from Ch. 19:**
> | Dimension | Ch. 19 | This chapter |
> |-----------|--------|--------------|
> | Core question | Mathematical models of PQ/HLG transfer functions | How metadata attaches, propagates, and is parsed |
> | Layer | Signal processing (algorithm layer) | Container formats, protocol stack (engineering layer) |
> | Reader scenario | Implementing PQ/HLG conversion | Packaging MP4/HEVC, integrating with streaming platforms |

---

## §1 Theory

### 1.1 The Hierarchy of Color Metadata

HDR video/image signals carry color description information at multiple layers throughout the signal chain, each layer targeting a different consumer:

```
┌──────────────────────────────────────────────────────────┐
│              Color Metadata Hierarchy                    │
├──────────────────────────────────────────────────────────┤
│  Layer 4: Streaming Platform Metadata                    │
│  (Netflix MDCV/CLLI, YouTube HDR Info, Apple HLS)        │
│                                                          │
│  Layer 3: Container Format Metadata                      │
│  (MP4 colr Box / HEIC/HEIF Metadata / MKV Tags)          │
│                                                          │
│  Layer 2: In-Bitstream Metadata                          │
│  (HEVC SEI: mastering display info / MaxCLL / DV RPU)    │
│                                                          │
│  Layer 1: Bitstream-Level Color Descriptor               │
│  (VUI: color_primaries / transfer_characteristics /      │
│        matrix_coefficients)                              │
└──────────────────────────────────────────────────────────┘
```

**Key principle:** When metadata exists at multiple layers, the "inner layer wins" rule applies — HEVC SEI Mastering Display information takes precedence over the MP4 `colr` Box if the two conflict.

---

### 1.2 Bitstream-Level Color Descriptors (VUI)

H.264, H.265, and AV1 bitstreams carry color descriptions in the **VUI (Video Usability Information)** within the Video Parameter Set (VPS) / Sequence Parameter Set (SPS):

#### 1.2.1 The Color Triplet

| Field | Meaning | Common values |
|-------|---------|---------------|
| `color_primaries` | Gamut primaries (R/G/B/White chromaticity) | 1=BT.709, 9=BT.2020, 12=DCI-P3 |
| `transfer_characteristics` | Transfer function (OETF/EOTF) | 1=BT.709, 16=PQ, 18=HLG |
| `matrix_coefficients` | Y′CbCr conversion matrix | 1=BT.709, 9=BT.2020 non-constant, 0=identity |

Numeric values are defined by ITU-T H.273 (referenced by HEVC) and ISO 23091-2 (referenced by AV1), both sharing the same enumeration.

#### 1.2.2 Standard Triplet for HDR10

HDR10 content must set the following VUI values:

```
color_primaries             = 9   (BT.2020)
transfer_characteristics    = 16  (SMPTE ST 2084 / PQ)
matrix_coefficients         = 9   (BT.2020 non-constant luminance)
```

Any single wrong field causes the decoder to render color incorrectly — the most common symptom is an extremely dark picture or severe color deviation.

#### 1.2.3 Standard Triplet for HLG

```
color_primaries             = 9   (BT.2020)
transfer_characteristics    = 18  (HLG, ARIB STD-B67)
matrix_coefficients         = 9   (BT.2020 non-constant luminance)
```

---

### 1.3 HEVC SEI Metadata

H.265 (HEVC) carries frame-level dynamic metadata through **SEI (Supplemental Enhancement Information)** NAL units. Key SEI types:

#### 1.3.1 Mastering Display Colour Volume SEI (MDCV, SMPTE ST 2086)

Carries the reference display characteristics used during content mastering:

| Field | Description | Typical HDR10 Value |
|-------|-------------|---------------------|
| `display_primaries_x/y[3]` | R/G/B chromaticity (fixed-point, divide by 50000 for CIE xy) | R:(34000,16000), G:(13250,34500), B:(7500,3000) |
| `white_point_x/y` | White point coordinates | (15635, 16450) → D65 |
| `max_display_mastering_luminance` | Peak luminance of mastering display (cd/m², divide by 10000) | 10000000 → 1000 cd/m² |
| `min_display_mastering_luminance` | Minimum luminance of mastering display (cd/m², divide by 10000) | 500 → 0.05 cd/m² |

**Physical meaning:** These parameters describe the **reference monitor used during content creation**, not the playback device. The receiver (TV/phone) uses this data to perform tone mapping.

#### 1.3.2 Content Light Level SEI (CLL, CTA-861.3)

Carries the maximum luminance of the content itself:

$$\text{MaxCLL} = \max_{f \in \text{content}} \max_{p} L(p, f)$$

$$\text{MaxFALL} = \max_{f \in \text{content}} \left( \frac{1}{W \times H} \sum_p L(p, f) \right)$$

where $L(p, f)$ is the linear luminance (cd/m²) of pixel $p$ in frame $f$, and $W \times H$ is the frame resolution.

- **MaxCLL** (Maximum Content Light Level): maximum linear luminance of **any pixel** in the content
- **MaxFALL** (Maximum Frame-Average Light Level): maximum **frame-average luminance** across the entire content

MaxFALL is more useful to receivers for selecting tone-mapping parameters (controlling overall exposure); MaxCLL is used for highlight protection.

#### 1.3.3 Dolby Vision RPU (Reference Processing Unit)

Dolby Vision uses **per-frame dynamic metadata** embedded in HEVC bitstream RPU SEI units:

- **CM (Content Mapping) data**: per-frame tone-mapping parameters (1000+ bytes/frame)
- **Trim passes**: separate tone-mapping curves for displays at different peak luminances (400/600/1000/2000/4000 nit)
- **BDM (Base Display Mapping)**: parameters mapping from content signal domain to reference display domain

Dolby Vision Profile 4 (dual-layer based on BT.2100 PQ) and Profile 8 (single-layer based on HDR10) are the main variants; Profile 8 is the most common in mobile devices today.

#### 1.3.4 HDR10+ Dynamic Metadata (SMPTE 2094-40)

Led by Samsung/Amazon, HDR10+ carries per-frame dynamic tone-mapping metadata (higher precision than HDR10 static metadata):

- Per-frame luminance statistics across spatial zones (3×3 to 5×5 grid)
- Receiver adjusts tone-mapping curve dynamically per frame based on this metadata

---

### 1.4 Color Information in MP4/ISOBMFF Containers

MP4 files convey color metadata through their **Box structure**, complementing the VUI/SEI in the bitstream:

#### 1.4.1 colr Box (Color Parameter Box)

Located under VisualSampleEntry in MP4, this provides the container-layer color description:

```
colr Box structure:
  color_type (4 bytes): 'nclx' (on-screen colors) or 'nclc' (older QuickTime)
  color_primaries        (16-bit uint): same enum as HEVC VUI color_primaries
  transfer_characteristics (16-bit uint): same as HEVC VUI
  matrix_coefficients    (16-bit uint): same as HEVC VUI
  full_range_flag        (1-bit): 0=limited (16-235), 1=full (0-255)
```

The `full_range_flag` is frequently overlooked but has a large impact:
- `0` (Limited Range / TV Range): Y range 16–235, UV range 16–240
- `1` (Full Range / PC Range): Y/U/V range 0–255

Mobile camera recordings are typically `full_range_flag = 0` (broadcast-compatible), but some camera modes output `full_range_flag = 1` (better use of the dynamic range). A mismatch causes the picture to appear noticeably too bright or too dark.

#### 1.4.2 mdcv / clli Boxes (QuickTime Extensions)

Apple platforms use additional `mdcv` and `clli` Boxes in MP4/MOV containers to carry MDCV/CLL information at the container level (equivalent to HEVC SEI, but container-level for legacy decoders that cannot parse SEI):

```
mdcv Box: 16 bytes — 6 × uint16 primary chromaticity + white point + 2 × uint32 max/min luminance
clli Box: 8 bytes — uint32 MaxCLL + uint32 MaxFALL
```

---

### 1.5 HEIF/HEIC Image Color Metadata

HEIF (High Efficiency Image File Format) is used for still images (iPhone `*.heic`) and is based on ISOBMFF. Color metadata handling is similar to video but with differences:

#### 1.5.1 Color Metadata Paths in HEIF

```
HEIF file (.heic)
  ├── ftyp Box: heic / mif1 / heix
  ├── meta Box
  │     ├── hdlr Box: pict (image type)
  │     └── iprp Box
  │           └── colr Box: nclx (digital gamut) or prof (ICC profile)
  └── mdat Box: HEVC-encoded image data (color triplet in VUI)
```

When both `nclx` and ICC profile coexist, `nclx` takes precedence (digital over ICC).

#### 1.5.2 HDR Images (Gain Map HEIF)

Apple's HDR Photo format (iOS 14.1+) embeds a **Gain Map** inside HEIF:

- Base image: SDR (sRGB, normal brightness)
- Gain Map: a per-pixel luminance gain image (0.0–1.0) indicating which regions should appear brighter than SDR on HDR displays
- Decoding formula (in linear light domain):

$$L_{\text{HDR}}(p) = L_{\text{SDR}}(p) \cdot \text{headroom}^{g(p)}$$

where $\text{headroom}$ is the ratio of HDR peak luminance to SDR reference white (typical value 4–8); $g(p) \in [0, 1]$ is the Gain Map pixel value.

Adobe's Ultra HDR JPEG (JPEG-XT) uses the same principle, embedding the Gain Map in a JPEG APP extension segment.

---

### 1.6 Streaming Platform HDR Specification Requirements

Major streaming platforms have strict metadata specification requirements for HDR content — non-compliance results in automatic downgrade to SDR rendering:

#### 1.6.1 Netflix HDR Specification (Simplified)

| Parameter | HDR10 | Dolby Vision |
|-----------|-------|--------------|
| Bitstream format | HEVC Main10 Profile | HEVC Main10 + Dolby Vision BL/EL or Single Layer |
| color_primaries | 9 (BT.2020) | 9 (BT.2020) |
| transfer_characteristics | 16 (PQ) | 16 (PQ) |
| MDCV | Required; mastering display ≥ 1000 nit | Required (dynamic metadata) |
| MaxCLL | Required | N/A (dynamic per-frame) |
| Minimum MaxCLL | ≥ 400 cd/m² | N/A |

#### 1.6.2 YouTube HDR Specification

YouTube accepts both HDR10 and HLG, auto-detecting from the uploaded content's VUI/SEI:
- No VUI set on upload → YouTube treats as SDR regardless of actual content
- MaxCLL = 0 → treated as not set; YouTube uses default 1000 nit reference
- Gamut labeled BT.709 but content is BT.2020 → color saturation appears low (most common error)

#### 1.6.3 Apple TV+ / FaceTime Requirements

Apple platforms have the most complete Dolby Vision Profile 8 support:
- iPhone-captured Dolby Vision video is encoded as Profile 8.4 (4K/30fps) or 8.1 (FHD)
- Full Dolby Vision Metadata RPU is carried in HEVC SEI
- When shared to non-Apple platforms, the Dolby Vision RPU is typically stripped, automatically falling back to HDR10

---

### 1.7 Gamut and Dynamic Range: Metadata Interactions

Color gamut and dynamic range are two independent dimensions but are frequently transmitted together in the signal chain. Understanding their interaction is essential:

**Four combinations:**

| Dynamic range | Gamut | Standard | Typical scenario |
|---------------|-------|----------|-----------------|
| SDR | BT.709 | BT.1886 | Traditional broadcast, legacy content |
| SDR | P3 | Display P3 | Older iPhone photos, modern phone SDR |
| HDR | BT.2020 | HDR10, PQ | 4K HDR movies, phone HDR video |
| HDR | BT.709 | PQ+709 | Some security/medical HDR (non-standard) |

**Key engineering principle:** HDR gamut (BT.2020) and HDR dynamic range (PQ) almost always appear together, but this is not technically mandatory — HLG can be paired with BT.709 gamut (BT.2100-2 defines HLG+BT.709 as a transitional option).

---

## §2 Calibration

### 2.1 Real-Time MaxCLL/MaxFALL Computation on Mobile

When recording HDR video on a smartphone, MaxCLL/MaxFALL must be computed in real time within the ISP/encoder pipeline (per frame, with zero additional latency):

**Calibration method:**
1. Before the ISP's tone-mapping stage, compute per-pixel luminance in linear light domain (before PQ encoding) for each frame
2. Maintain a sliding window (e.g., 1 second = 30 frames) of the maximum value
3. Report: `MaxCLL = max over all frames`, `MaxFALL = max of per-frame averages`

**Accuracy requirements:** MaxCLL error within ±5 cd/m² (Netflix requirement), MaxFALL error within ±2 cd/m².

### 2.2 Streaming Platform Metadata Compliance Verification

**Verification toolchain:**
- **MediaInfo** (cross-platform): parses MP4 `colr` Box, `mdcv`, `clli` fields
- **ffprobe**: parses HEVC VUI and SEI:
  ```bash
  ffprobe -v quiet -print_format json -show_streams video.mp4
  # Key fields: color_primaries, color_trc, color_space, color_range
  ```
- **DVAnalyzer** (Dolby): verifies Dolby Vision RPU completeness and compliance

---

## §3 Tuning

### 3.1 Choosing full_range vs limited_range

In mobile ISP engineering, the `full_range_flag` setting is one of the most error-prone parameters:

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| Publish to streaming (Netflix/YouTube) | `limited_range (0)` | Platforms expect broadcast-compatible signal |
| Local phone playback | `full_range (1)` or `limited_range (0)` | Depends on decoder policy |
| Export to professional NLE | `full_range (1)` | Tools like Premiere/DaVinci typically handle Full Range |
| HLG broadcast | `limited_range (0)` | BT.2100 HLG specifies Legal Range (64–940 for 10-bit) |

### 3.2 MDCV Parameter Error Diagnosis

Most common MDCV errors and their effects:

| Error | Symptom | Fix |
|-------|---------|-----|
| max_display_mastering_luminance = 0 | Receiver tone-maps with 0 nit reference, color rendering collapses | Set actual mastering display peak luminance (≥ 400 nit) |
| color_primaries = 1 (BT.709) but content is BT.2020 | Over-saturated or distorted colors | Verify VUI triplet settings |
| Missing CLL SEI | Some TVs refuse to identify content as HDR10 | Force CLL SEI injection at encoding time |

---

## §4 Artifacts

### 4.1 Display Artifacts from Metadata/Content Mismatch

| Artifact type | Root cause | Typical scenario |
|---------------|-----------|-----------------|
| Overall picture too dark (SDR clipping) | Inflated MaxCLL causes receiver to over-compress via tone mapping | Indoor dark scene with spuriously high MaxCLL report |
| Highlights shift blue/purple | BT.2020 primary matrix applied to BT.709 content | Incorrect color_primaries setting |
| Whole-frame brightness offset (×0.8 or ×1.25) | full_range / limited_range mismatch | Capture: full_range; decode: interpreted as limited |
| Saturated colors visibly reduced | BT.2020→BT.709 gamut conversion without gamut mapping | Simple matrix conversion with no gamut mapping |

### 4.2 Dolby Vision Downgrade Artifacts

When the Dolby Vision RPU is stripped and content falls back to HDR10:
- Per-frame dynamic tone-mapping parameters are lost → receiver uses static metadata, potentially losing highlight/shadow detail
- Typical symptom: blown highlights in bright scenes (detail that would have been preserved by dynamic trim passes is clipped)

---

## §5 Evaluation

### 5.1 Metadata Compliance Evaluation

**Quantitative metrics:**
- `color_primaries` / `transfer_characteristics` triplet correctness rate: should be 100% (hard requirement)
- MaxCLL error: compared against HDR luminance analyzer measurement, target < ±5 cd/m²
- MaxFALL error: target < ±2 cd/m²
- `full_range_flag` consistency with actual encoder range setting: should be 100% consistent

**Evaluation tools:**
- `ffprobe` + `python-av` for batch metadata correctness parsing
- HDR Metadata Viewer (open source) for real-time in-stream metadata display
- Professional HDR display + luminance meter: compare reported MaxCLL against measured peak luminance

### 5.2 Color Rendering Accuracy

On a professional HDR display with BT.2020 color gamut, evaluate color difference between the test video and a reference:
- Color error metric: $\Delta E_{2000}$ in the ICtCp color space (recommended by BT.2124 for HDR — more accurate than CIELab $\Delta E$ in high dynamic range scenarios)
- Target: $\Delta E_{\text{ICtCp}} < 3$ (acceptable), $< 1.5$ (excellent)

---

## §6 Code

See companion notebook *See §6 Code section for runnable examples.* for:

1. **VUI triplet parsing**: batch read color triplets from MP4 files using `ffprobe`, verify compliance
2. **MaxCLL/MaxFALL computation**: NumPy-based per-frame luminance statistics, compared against `ffmpeg` auto-computed values
3. **Gain Map HEIF parsing**: read Apple HDR Photo Gain Map data and reconstruct the HDR version
4. **full_range conversion**: manually convert between full_range and limited_range, compare visual quality differences

---

## §7 Glossary

**VUI (Video Usability Information)**
A supplementary field set in H.264/H.265 SPS that describes video signal characteristics, including the `color_primaries`, `transfer_characteristics`, and `matrix_coefficients` triplet — the most fundamental color rendering guidance for decoders.

**SEI (Supplemental Enhancement Information)**
Non-mandatory supplementary data units in HEVC/H.264 bitstreams, carrying frame-level metadata such as MDCV (Mastering Display Colour Volume), CLL (Content Light Level), and Dolby Vision RPU.

**colr Box**
The color parameter Box in MP4/ISOBMFF containers, declaring the color encoding method at the container level — either `nclx` type (digital color parameters) or `prof` type (ICC profile reference).

**Gain Map**
An HDR encoding method that layers a per-pixel luminance gain image on top of an SDR base image. Both Apple Ultra HDR Photo (HEIF Gain Map) and Adobe Ultra HDR JPEG use this approach, achieving dual compatibility: HDR-capable devices apply the gain; SDR devices ignore it.

**MaxCLL (Maximum Content Light Level)**
The maximum linear luminance (cd/m²) of any single pixel in the content, defined by CTA-861.3. Used by receivers for highlight protection in tone mapping.

**MaxFALL (Maximum Frame-Average Light Level)**
The maximum frame-average luminance (cd/m²) across the entire content. Better reflects overall picture brightness than MaxCLL, and has greater influence on the receiver's tone-mapping exposure parameters.

**Dolby Vision RPU (Reference Processing Unit)**
Dolby Vision's per-frame dynamic metadata, embedded in HEVC SEI extension segments. Carries tone-mapping trim pass parameters for displays at different peak luminances — the core differentiating capability of Dolby Vision relative to HDR10.

**ICtCp Color Space**
A perceptually uniform HDR color space defined in the Annex of BT.2100 (I = intensity, Ct = yellow-blue axis, Cp = red-green axis). More accurate than CIELab for predicting color differences in high dynamic range conditions. $\Delta E_{\text{ICtCp}}$ is recommended by BT.2124 as the color difference metric for HDR content.

**Limited Range / Full Range**
- Limited Range (TV Range): Y values 16–235 (8-bit), 64–940 (10-bit), corresponding to 0%–100% luminance
- Full Range (PC Range): Y/U/V values 0–255 (8-bit), 0–1023 (10-bit)

Incorrect `full_range_flag` setting is one of the most common metadata bugs in mobile HDR video.

---

## References

[1] ITU-R BT.2100-2 (2018). Image parameter values for high dynamic range television for use in production and international programme exchange. ITU-R.

[2] SMPTE ST 2086:2018. Mastering Display Colour Volume. SMPTE.

[3] CTA-861.3-A (2015). HDR Static Metadata Extensions. CTA.

[4] SMPTE ST 2094-40. Application #4 of SMPTE ST 2094 (HDR10+ Dynamic Metadata). SMPTE.

[5] ITU-R BT.2124-0 (2019). Objective metric for the assessment of the potential visibility of colour differences in television. ITU-R.

[6] Apple Inc. (2021). HEIF Gain Map Specification (ISO/IEC 21496-1 submission draft).

[7] ISO/IEC 14496-12:2022. ISO base media file format. ISO/IEC.

[8] Dolby (2021). Dolby Vision Streams Within the ISOBMFF File Format. Dolby Labs Technical White Paper.

[9] ITU-T H.273 (2021). Coding-independent code points for video signal type identification. ITU-T.
