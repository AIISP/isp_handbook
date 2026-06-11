# Part 2, Chapter 19: HDR Display Signal Chain

> **Pipeline Position:** Display-side final output stage — after tone mapping, before video encoding
> **Prerequisite Chapters:** Part 1, Chapter 07 (Dynamic Range and HDR), Part 2, Chapter 07 (Gamma and Tone Mapping), Part 2, Chapter 10 (HDR Frame Merging), Part 2, Chapter 18 (Local Tone Mapping Algorithms)
> **Target Readers:** Luminance Algorithm Engineers, Video ISP Engineers, Display Engineers

---

## §1 Theory

### 1.1 From Scene to Display: Two Signal Processing Philosophies

Understanding the HDR display signal chain requires clarifying two fundamentally different signal reference frames.

**Scene-Referred:** Signal values directly correspond to physical radiance quantities (linear light) in the scene. Camera RAW files, OpenEXR `.exr` files, and ACES (Academy Color Encoding System) are all scene-referred formats and can represent arbitrary dynamic ranges.

**Display-Referred:** Signal values directly correspond to the luminance output of a display, bounded by the display's peak luminance. sRGB and BT.709 are display-referred: a signal value of 1.0 equals the display's maximum luminance (approximately 100 cd/m²).

**The core tension in the HDR signal chain:** Scene dynamic range can reach $10^5$–$10^7$:1, while even the best HDR displays offer approximately $10^4$–$10^5$:1, and SDR displays only about $10^3$:1. The task of the signal chain is to map scene-referred signals to display-referred signals while **preserving perceived visual quality**.

---

### 1.2 PQ EOTF — SMPTE ST 2084

PQ (Perceptual Quantizer) is the core transfer function used in HDR video (HDR10, Dolby Vision). Developed by Dolby Laboratories and standardized as SMPTE ST 2084:2014.

#### 1.2.1 PQ Design Principle

The design goal of PQ is **perceptually uniform code-word allocation**: using the minimum number of code words (10 bit) to cover the widest possible luminance range (0.001–10,000 cd/m²), subject to the just-noticeable difference (JND) constraints of the human visual system (HVS).

Based on Barten's (1999) contrast sensitivity function (CSF), the JND step count across the range 0.001–10,000 cd/m² is approximately 720, meaning 10 bits (1024 levels) is sufficient for lossless coverage.

#### 1.2.2 PQ EOTF (Electro-Optical Transfer Function)

The EOTF maps the electrical signal $E$ to display luminance $Y$ (cd/m²):

$$Y = 10000 \cdot \left(\frac{\max(E^{1/m_2} - c_1, 0)}{c_2 - c_3 \cdot E^{1/m_2}}\right)^{1/m_1}$$

Constants (as specified in SMPTE ST 2084):
- $m_1 = 0.1593017578125 = 2610/16384$
- $m_2 = 78.84375 = 2523/32$
- $c_1 = 0.8359375 = 3424/4096$ ($= n = 32/4096 \times 107$)
- $c_2 = 18.8515625 = 2413/128$
- $c_3 = 18.6875 = 2392/128$
- Reference white point: 10,000 cd/m² (versus 100 cd/m² for SDR)

#### 1.2.3 PQ OETF (Opto-Electronic Transfer Function, Encoding Side)

The OETF is the inverse of the EOTF; it encodes linear luminance $Y'$ (normalized to $[0,1]$, where 1.0 = 10,000 cd/m²) into the electrical signal $E$:

$$E = \left(\frac{c_1 + c_2 \cdot (Y')^{m_1}}{1 + c_3 \cdot (Y')^{m_1}}\right)^{m_2}$$

**PQ vs. Gamma comparison:**

| Property | Gamma (sRGB) | PQ (ST 2084) |
|----------|-------------|-------------|
| Design basis | Display physical characteristics | Human JND model |
| Reference white luminance | 100 cd/m² | 10,000 cd/m² |
| Dynamic range | ~100:1 | ~1,000,000:1 |
| Absolute luminance | Relative (depends on viewing environment) | Absolute (scene absolute luminance encoded) |
| 10-bit utilization | ~940 valid code words (BT.2100) | ~720 JND steps |

---

### 1.3 HLG — Hybrid Log-Gamma

HLG was jointly developed by BBC and NHK and standardized as ITU-R BT.2100. It is the dominant HDR format for broadcast and streaming.

#### 1.3.1 HLG Design Philosophy

HLG's key advantage is **backward compatibility with SDR displays**: when an HLG signal is played back on an SDR display, the lower segment (Gamma region) renders naturally as SDR content with acceptable appearance; on an HDR display, the logarithmic upper region is used to extend peak luminance.

#### 1.3.2 HLG OETF

Piecewise function:

$$E = \begin{cases}
\sqrt{3} \cdot E' & \text{if } E' \leq \dfrac{1}{12} \\[6pt]
a \cdot \ln(12 E' - b) + c & \text{if } E' > \dfrac{1}{12}
\end{cases}$$

where $E'$ is the normalized linear scene luminance ($0$ to $1$) and $E$ is the encoded signal value ($0$ to $1$). Constants:
- $a = 0.17883277$
- $b = 1 - 4a = 0.28466892$
- $c = 0.55991073$ (continuity constraint)

**Lower segment ($E' \leq 1/12$):** Pure Gamma region ($\gamma = 0.5$, i.e., $E = \sqrt{3E'}$); compatible with SDR Gamma.

**Upper segment ($E' > 1/12$):** Logarithmic region, used to compress HDR highlights.

#### 1.3.3 HLG OOTF (Scene-to-Display System Transform)

PQ is display-referred; HLG is scene-referred. The difference lies in the OOTF (Opto-Optical Transfer Function):

$$F_D = \alpha \cdot E_s^{(\gamma-1)} \cdot \overrightarrow{E_s}$$

where $\alpha = L_W / 1000$ ($L_W$ is the display peak luminance in cd/m²), and $\gamma$ varies with ambient luminance conditions (ITU-R BT.2390 recommends $\gamma = 1.2$ for a 1,000 cd/m² display).

---

### 1.4 HDR10 Standard and Static Metadata

**HDR10** is the open HDR standard based on PQ + BT.2020 color gamut, defined by the Consumer Technology Association (CTA):

| Parameter | HDR10 Specification |
|-----------|-------------------|
| Transfer function | PQ (SMPTE ST 2084) |
| Color gamut | ITU-R BT.2020 |
| Bit depth | 10 bit (12 bit recommended) |
| Metadata type | SMPTE ST 2086 (static, fixed for the entire program) |
| Peak luminance range | 540–4,000 cd/m² (1,000 cd/m² is typical) |

#### 1.4.1 SMPTE ST 2086 Static Metadata

HDR10 content carries the following static metadata (one set of values fixed for the entire program):

| Field | Unit | Description |
|-------|------|-------------|
| `max_display_mastering_luminance` | cd/m² | Peak luminance of the mastering monitor |
| `min_display_mastering_luminance` | cd/m² | Minimum luminance of the mastering monitor |
| `max_content_light_level` (MaxCLL) | cd/m² | Maximum single-pixel luminance in the content |
| `max_frame_average_light_level` (MaxFALL) | cd/m² | Maximum frame-average luminance across all frames |
| Color primaries | CIE xy | Chromaticity coordinates of the three primaries + white point |

#### 1.4.2 Computing MaxCLL and MaxFALL

$$\text{MaxCLL} = \max_{\text{all frames}} \max_{(x,y)} L(x,y)$$

$$\text{MaxFALL} = \max_{\text{all frames}} \left( \frac{1}{HW} \sum_{x,y} L(x,y) \right)$$

where $L(x,y)$ is the absolute luminance (cd/m²) after PQ decoding.

**Impact of MaxCLL/MaxFALL on display-side TMO:** Upon receiving the metadata, the display adjusts the parameters of its end-to-end tone mapping operator (EETMO). If MaxCLL greatly exceeds the display's peak luminance, more aggressive highlight compression is required.

---

### 1.5 Dolby Vision

Dolby Vision (DV) is Dolby's proprietary HDR format. Its key improvements over HDR10 are:

**Dynamic metadata (also used in HDR10+):** Tone mapping parameters are specified per frame or per scene rather than being fixed for the entire program. This allows the display-side TMO to be optimized frame by frame, avoiding the over/under-exposure at scene cuts that can occur with HDR10's static metadata.

**Dual-layer architecture (Base Layer + Enhancement Layer):**
- Base Layer (BL): A backward-compatible base layer compatible with HDR10 or SDR (8/10 bit).
- Enhancement Layer (EL): An enhancement layer carrying additional luminance information (12 bit).
- Display reconstruction: $\text{DV Output} = f(\text{BL}, \text{EL}, \text{Dynamic Metadata})$

**DV Profiles:**

| Profile | Peak Luminance | Bit Depth | Typical Use |
|---------|---------------|-----------|------------|
| Profile 4 | 4,000 cd/m² | 12 bit | Cinema |
| Profile 5 | metadata-defined (up to 10,000 cd/m²) | 12 bit | Professional production |
| Profile 8 | 4,000 cd/m² | 10 bit | Streaming (Netflix/Disney+) |
| Profile 9 | 1,000 cd/m² | 10 bit | Mobile devices |

---

### 1.6 End-to-End Tone Mapping (EETMO)

EETMO (End-to-End Tone Mapping Operator) is the final step inside a display device, adapting HDR content to the luminance capabilities of that specific display.

#### 1.6.1 EETMO Inputs and Outputs

- **Input:** PQ-encoded HDR frame + static/dynamic metadata (MaxCLL, MaxFALL, mastering display luminance).
- **Output:** PQ-encoded signal adapted to the target display, with luminance range compressed to fit within the display's capabilities.

#### 1.6.2 BT.2446 Method A — Reference Algorithm for HDR-to-SDR

ITU-R BT.2446:2021 provides a reference tone mapping algorithm (Method A) for converting HDR to SDR:

**Step 1: PQ decode; convert to linear light (cd/m²).**

**Step 2: Luminance compression.**

Map HDR luminance (0–$L_{\text{HDR}}$ cd/m²) to SDR (0–100 cd/m²) using an S-shaped curve:

$$Y_{\text{SDR}} = \frac{Y_{\text{HDR}}}{Y_{\text{HDR}} + a \cdot (Y_{\text{HDR}} / Y_{\text{SDR,peak}})^b}$$

where parameters $a$ and $b$ are derived from MaxCLL and the target display's peak luminance.

**Step 3: Chromatic adaptation (color scaling).**

Use the IPT or ICtCp color space (better perceptual uniformity) to scale colors, preserving hue and relative saturation.

**Step 4: sRGB Gamma encoding.**

Normalize the output (SDR white point = 100 cd/m² → encoded value 1.0) and apply the sRGB OETF.

#### 1.6.3 ICtCp Color Space (HDR Perceptually Uniform Color Space)

Recommended by ITU-R BT.2100 as the intermediate space for HDR tone mapping; more suitable for HDR than CIELab:

$$\begin{bmatrix} L_M \\ M_M \\ S_M \end{bmatrix} = \text{PQ}^{-1}\!\left( M_{\text{LMS}} \cdot \begin{bmatrix} R \\ G \\ B \end{bmatrix} \right)$$

$$\begin{bmatrix} I \\ C_T \\ C_P \end{bmatrix} = M_{\text{ICtCp}} \cdot \begin{bmatrix} L_M \\ M_M \\ S_M \end{bmatrix}$$

The $I$ component corresponds to perceived luminance (strong perceptual uniformity); $C_T$ is the orange-blue axis; $C_P$ is the green-rose axis.

In HDR tone mapping, only the $I$ channel is modified; $C_T$ and $C_P$ are left unchanged, naturally preventing hue shifts.

---

### 1.7 Smartphone HDR Video Pipeline

Taking flagship devices such as iPhone, Pixel, and Xiaomi as examples, the end-to-end HDR video recording and playback pipeline on a smartphone:

```
Capture side:
  Multi-frame HDR merging (Ch27)
  → Linear RAW signal (scene-referred, dynamic range > 10^5:1)
  → HDRNet / bilateral grid tone mapping (Ch07)
  → PQ encoding (ST 2084)
  → Dolby Vision Profile 8 / HDR10 packaging
  → HEVC/AV1 encoding (10-bit)

Playback side:
  HEVC/AV1 decoding
  → PQ decoding (linear cd/m²)
  → Read metadata (MaxCLL, MaxFALL)
  → EETMO adaptation to target screen
    (e.g., iPhone 1200 cd/m² ProMotion display)
  → Display output
```

---

## §2 Calibration

### 2.1 MaxCLL/MaxFALL Calibration for HDR Content

For HDR video captured directly from a camera:

```python
import numpy as np

def compute_maxcll_maxfall(frames_pq):
    """
    frames_pq: list of PQ-encoded frames [0,1]
    Returns MaxCLL and MaxFALL in cd/m²
    """
    max_cll = 0.0
    frame_avgs = []
    for frame in frames_pq:
        # PQ decode to absolute luminance
        lum = pq_eotf(frame) * 10000  # cd/m²
        max_cll = max(max_cll, lum.max())
        frame_avgs.append(lum.mean())
    max_fall = max(frame_avgs)
    return max_cll, max_fall
```

### 2.2 Display EOTF Calibration

Use a colorimeter (e.g., Konica Minolta CS-100A) to measure the display's response curve:

1. Send gray-ramp patterns at PQ code values 0–1023 (10 bit).
2. Measure the actual luminance (cd/m²) for each code value.
3. Compare against the theoretical EOTF from ST 2084; record deviations.
4. If deviation exceeds 2 ΔE (in ICtCp space), correction is required at the OLED/LCD driver layer.

---

## §3 Tuning

### 3.1 MaxCLL Clipping Strategy

| Strategy | Description | Applicable Scenario |
|----------|-------------|-------------------|
| Record actual MaxCLL | Most accurate; enables optimal EETMO | Professional content production |
| Clip to 4,000 cd/m² | Reduces metadata information load; better compatibility | General consumer video |
| Clip to 1,000 cd/m² | Common HDR10 practice; most TVs can handle it | Streaming distribution |

### 3.2 HLG Tuning for SDR Compatibility

HLG's $\gamma$ value affects the appearance on SDR devices:

- $\gamma = 1.2$ (BT.2390 recommendation): 1,000 cd/m² display.
- $\gamma = 1.1$: Dimmer viewing environment.
- $\gamma = 1.3$: Brighter viewing environment (e.g., smartphone in sunlight).

System-level tuning: For the same HLG signal in different viewing environments, the $\gamma$ parameter in the OOTF should be automatically adjusted by the display device based on an ambient light sensor (ITU-R BT.2390).

### 3.3 PQ vs. HLG Selection Guide

| Use Case | Recommended Format | Rationale |
|----------|--------------------|-----------|
| Film / video-on-demand (Netflix/Apple TV+) | Dolby Vision Profile 8 / HDR10 | Dynamic/static metadata; professional-grade quality |
| Live broadcast | HLG | Real-time processing without pre-analysis; SDR device compatibility |
| Smartphone video recording | Dolby Vision Profile 8 | Current mobile mainstream (iPhone Profile 8.4); Profile 9 was for legacy AVC devices and has been superseded by Profile 8 |
| Surveillance video | HLG | No metadata dependency; simpler system |
| Medical imaging | PQ (approximately DICOM GSDF) | Absolute luminance accuracy is paramount |

---

### 3.4 Metadata Generation Timing: HDR10 / HLG / Dolby Vision

A common source of confusion in ISP integration is understanding *which component generates HDR metadata, and when*. The answer differs across the three formats and directly affects metadata accuracy and system latency.

#### 3.4.1 Metadata Generation Location by Format

| Format | Metadata Type | Generation Location | Timing |
|--------|--------------|---------------------|--------|
| HDR10 | MaxCLL / MaxFALL (SMPTE ST 2086 static) | **ISP statistics engine** (real-time per-frame accumulation; written to file header after recording ends) | Computed live during capture; final value injected into container |
| HLG | None (OOTF parameters are inferred by the display automatically) | Not generated | — |
| Dolby Vision | Per-frame dynamic metadata (ST 2094-10 RPU) | **ISP + Dolby licensed DSP, jointly** (ISP supplies per-frame statistics; Dolby library computes trim parameters) | Generated per frame in real time; embedded in HEVC SEI |

**Key conclusions:**
- **HDR10 MaxCLL/MaxFALL is generated by the ISP**, not the HEVC encoder. The encoder has no semantic understanding of content luminance; it simply packages the values already computed by the ISP into SEI headers.
- **Dolby Vision dynamic metadata spans two layers**: the ISP outputs per-frame luminance statistics (histogram, peak luminance), and the Dolby licensed runtime library (running on AP or a dedicated DSP) converts those statistics into RPU EETMO parameters (`knee_point_x/y`, `bezier_curve_anchors`).
- **HLG requires no ISP metadata generation** — one reason HLG has lower power draw during mobile video recording.

#### 3.4.2 MaxCLL/MaxFALL Computation: Per-Frame Accumulation vs. Sliding Window

The computation strategy for MaxCLL and MaxFALL affects the accuracy of the final metadata values.

**Qualcomm Spectra ISP implementation:**

```
Per-frame computation:
  ISP statistics module → output luminance histogram per frame (256 bins)
  MaxCLL_frame = 99.9th-percentile luminance (avoids single-pixel specular highlights inflating the value)
  MaxFALL_frame = frame-average luminance

End-of-recording write:
  MaxCLL = max(MaxCLL_frame) over all frames
  MaxFALL = max(MaxFALL_frame) over all frames
```

**MediaTek Imagiq ISP:**

MediaTek uses a **sliding window (30 frames)** during live recording to update MaxCLL/MaxFALL, preventing transient overexposure frames (e.g., flash-triggered frames) from inflating the reported statistics:

```
MaxCLL_report = max(MaxCLL_frame) in sliding window of last 30 frames
```

> **Qualcomm vs. MTK implementation difference:** Qualcomm accumulates the global maximum over the entire sequence for higher accuracy, but risks contamination by flash frames. MTK's sliding window avoids outlier frame pollution but may miss peak frames that occurred near the start of the recording. The engineering recommendation is to apply a 99.9th-percentile cutoff in the ISP statistics module before taking the sequence maximum — this balances accuracy and robustness.

#### 3.4.3 PQ vs. HLG Decoding Latency

| Transfer Function | Decoding Method | Latency Source | Typical Latency |
|-------------------|----------------|----------------|----------------|
| PQ (HDR10) | LUT or formula EOTF; must read MaxCLL/MaxFALL metadata to determine EETMO parameters | Metadata parsing (read SEI/container header) + EETMO computation | < 1 ms (after static metadata is known, LUT lookup is instant) |
| PQ (Dolby Vision) | Per-frame RPU SEI parsing → reconstruct EETMO curve → apply display-side TMO | Per-frame RPU SEI parse (~200–400 bytes) + curve reconstruction | 3–7 ms/frame (can be pipelined to hide latency) |
| HLG | OOTF formula only (no metadata dependency) | No metadata wait latency | < 0.5 ms |

In real-time editing or preview scenarios (e.g., camera viewfinder), HLG's zero-metadata latency makes it better suited to the live path. PQ's metadata dependency requires a "pre-analysis buffer" (look-ahead of a few frames to establish the metadata baseline) during ISP-direct preview, adding approximately 1–3 frames (33–100 ms at 30 fps) of initialization latency. This also explains why some phones show slightly darker initial frames when HDR video recording is enabled — the first-frame MaxCLL estimate is inaccurate (insufficient statistics have accumulated), so the EETMO parameters are conservative.

---

## §4 Artifacts

### 4.1 HDR Content Overexposed on SDR Displays

**Description:** When HDR10 content is fed directly into an SDR display without EETMO, bright areas are severely overexposed and large amounts of detail are lost.

**Root cause:** A PQ signal value of 1.0 equals 10,000 cd/m². The SDR display interprets this as a Gamma signal; the resulting output luminance exceeds the display's physical capability, and the display automatically clips.

**Mitigation:** The display chain must include EETMO. For devices without HDR support, automatically fall back to an SDR-encoded stream (dual-stream solution: HDR primary stream + SDR compatibility stream).

### 4.2 Saturation Collapse After Tone Mapping

**Description:** After EETMO applies strong compression to bright regions, highly saturated colored objects in those regions (e.g., a red sports car under intense sunlight) exhibit a noticeable loss of color saturation.

**Root cause:** Directly scaling luminance in linear RGB space as $\vec{I}' = k \cdot \vec{I}$ ($k < 1$) scales R, G, and B equally, driving the result toward white (low saturation).

**Mitigation:** Operate in ICtCp space — compress only the $I$ channel (perceived luminance); scale $C_T$ and $C_P$ (chrominance) in proportion to the luminance ratio rather than reducing them equally:

$$C_T' = C_T \cdot \left(\frac{I'}{I}\right)^{0.6}$$

The exponent 0.6 approximates the Hunt effect (enhanced color perception at high luminance).

### 4.3 PQ Low-Bitrate Quantization Noise

**Description:** In very dark regions (< 0.01 cd/m²), the code-word spacing of 10-bit PQ is already very small (about 0.0001 cd/m²). However, HEVC encoding at low quality settings applies further quantization, causing visible luminance banding in dark areas.

**Mitigation:**
- Use 12-bit encoding (increases code-word density in dark regions).
- Apply light dithering (noise injection) to dark regions before PQ encoding, randomizing quantization error instead of allowing it to form bands.
- At the encoder level, reduce the quantization step size (lower QP) in dark regions.

### 4.4 HLG Scene-Cut Luminance Jump

**Description:** During scene cuts in HLG video, if the average luminance differs significantly between the two scenes, the playback-side OOTF system $\gamma$ cannot adjust fast enough, causing a visible luminance jump.

**Mitigation:** At the encoding side, apply per-scene OOTF target normalization to HLG content (ensuring consistent luminance across scenes during SDR decoding), or provide scene-level metadata to guide OOTF parameter transitions.

---

## §5 Evaluation

### 5.1 EETMO Quality Evaluation

**Technical metrics:**

| Metric | Description | Target |
|--------|-------------|--------|
| ΔE (ICtCp) | ICtCp distance between output luminance/color and a reference TMO | < 2.0 JND |
| Highlight protection rate | Proportion of highlight information retained vs. hard clipping | > 90% |
| Shadow enhancement rate | Proportion of shadow detail with improved visibility | > 80% |
| Hue fidelity | Proportion of samples with subjective hue shift < 2° | > 95% |

**Subjective evaluation (MOS):**
- Comparison group: HDR10 original vs. EETMO output on target SDR display.
- Evaluation dimensions: naturalness, highlight handling, shadow detail, overall tonal impression.
- Evaluators: 20+ people using professionally calibrated HDR/SDR displays.

### 5.2 PQ Calibration Accuracy

Use a professional colorimeter to verify the display EOTF's conformance to the ST 2084 specification:

```
Test method: VESA DisplayHDR certification test suite
Pass criteria:
  - Peak luminance error < 10%
  - Dark luminance (< 5 cd/m²) deviation < 0.5 ΔE (ICtCp)
  - MaxCLL point luminance accuracy > 95%
```

---

## §6 Code

See the companion notebook *See §6 Code section for runnable examples.*, which includes:

- Python implementation of PQ EOTF/OETF (precisely matching SMPTE ST 2084)
- HLG OETF/OOTF implementation (ITU-R BT.2100)
- Automated MaxCLL/MaxFALL computation tool for HDR10 content
- BT.2446 Method A HDR→SDR EETMO reference implementation
- ICtCp color space conversion (including PQ decoding sub-step)
- Comparative visualization of PQ / HLG / sRGB transfer functions
- Smartphone HDR video pipeline simulation (Dolby Vision Profile 8 style)

---

## References

[1] SMPTE, "ST 2084:2014 — High Dynamic Range Electro-Optical Transfer Function of Mastering Reference Displays," 2014.

[2] ITU-R, "BT.2100 — Image parameter values for high dynamic range television for use in production and international programme exchange," 2018.

[3] ITU-R, "BT.2390 — High dynamic range television for production and international programme exchange," 2022.

[4] ITU-R, "BT.2446 — Methods for conversion and display adaptation between high dynamic range (HDR) and standard dynamic range (SDR) content," 2021.

[5] Barten, P. G. J. (1999). *Contrast sensitivity of the human eye and its effects on image quality*. SPIE Press.

[6] Miller, S., Nezamabadi, M., & Daly, S. (2013). Perceptual signal coding for more efficient usage of bit codes. *SMPTE Motion Imaging Journal*, 122(4).

[7] Funt, B., & Shi, L. (2010). The rehabilitation of MaxRGB. *Proc. IS&T/SID Color Imaging Conference*.

[8] CTA, "CTA-861-H:2022 — A DTV Profile for Uncompressed High Speed Digital Interfaces," 2022.

[9] Dolby Laboratories. (2017). *Dolby Vision: Encoding and Distribution Guidelines*. (Public white paper)

[10] Ebner, F. (1998). *Derivation and modelling hue uniformity and development of the IPT color space*. PhD Thesis, RIT.

[11] Reinhard, E., et al. (2010). *High Dynamic Range Imaging* (2nd ed.). Morgan Kaufmann. Part IV: Display.

[12] ITU-R BT.2408:2022 — Operational practices in HDR television production.

[13] SMPTE 2094-40:2016 — Dynamic Metadata for Color Volume Transform — Application #4 (Samsung HDR10+).

[14] Apple Inc. (2021). *ProRes RAW White Paper*. https://www.apple.com/final-cut-pro/docs/Apple_ProRes_RAW.pdf

[15] Dolby Laboratories. (2020). *Dolby Vision for Streaming: Encoding and Distribution Guidelines v2.2*.

[16] VESA. (2023). *DisplayHDR 2.0 Specification*.

[17] Zhao, H., et al. (2021). HDR10+ vs. Dolby Vision: A Systematic Comparison of Dynamic Metadata HDR Formats. *SMPTE Motion Imaging Journal*, 130(6).

---

## §7 Glossary

**Scene-Referred vs. Display-Referred**
Two fundamentally different signal reference frames. **Scene-referred** signal values correspond to physical scene radiance (linear light), independent of the display device; dynamic range can reach $10^5$–$10^7$:1. Representative formats: OpenEXR, ACES, camera RAW. **Display-referred** signal values correspond to the actual luminance output of a display device, bounded by the display's peak luminance. Representative formats: sRGB (reference white 100 cd/m²), HDR10 (reference white 10,000 cd/m²). The central task of the HDR signal chain is to map from scene-referred to display-referred while preserving visual quality.

**PQ (Perceptual Quantizer) — SMPTE ST 2084**
HDR transfer function developed by Dolby Laboratories and standardized as SMPTE ST 2084 in 2014. Designed according to Barten's (1999) contrast sensitivity function (CSF), the goal is perceptually uniform code-word allocation across 0.001–10,000 cd/m²: 10-bit (1024 levels) covers approximately 720 JND steps. Core characteristic: **absolute luminance encoding** (signal value 1.0 = 10,000 cd/m², independent of viewing environment). PQ is the standard transfer function for both HDR10 and Dolby Vision. Its fundamental distinction from sRGB Gamma: PQ is designed around human visual perception; Gamma was designed to compensate for CRT display physics.

**HLG (Hybrid Log-Gamma) — ITU-R BT.2100**
HDR transfer function jointly developed by BBC and NHK, standardized as ITU-R BT.2100. The dominant format for broadcast and streaming HDR. Core design: **backward compatibility with SDR** — the lower segment ($E' \leq 1/12$) uses a power function $E = \sqrt{3E'}$ ($\gamma = 0.5$), which SDR displays interpret naturally; the upper segment ($E' > 1/12$) uses logarithmic compression $E = a\ln(12E'-b)+c$ ($a=0.17883277$, $b=0.28466892$, $c=0.55991073$). Key distinction from PQ: HLG is scene-referred (relative luminance), while PQ is display-referred (absolute luminance). HLG requires no metadata; PQ requires MaxCLL/MaxFALL metadata for EETMO.

**HDR10 and Static Metadata (SMPTE ST 2086)**
Open HDR standard based on PQ + BT.2020 color gamut. Static metadata SMPTE ST 2086 contains: mastering monitor peak/minimum luminance, primary chromaticity coordinates, **MaxCLL** (maximum single-pixel luminance in the content), and **MaxFALL** (maximum frame-average luminance). "Static" means the entire program shares one set of metadata — when scene luminance varies significantly, EETMO accuracy is inferior to per-frame dynamic metadata (Dolby Vision).

**Dolby Vision and Dynamic Metadata**
Dolby's proprietary HDR format. Key improvements over HDR10: **dynamic metadata** (per-frame or per-scene tone mapping parameters), enabling display-side EETMO to be optimized frame by frame, avoiding the over/under-exposure at scene cuts seen with HDR10 static metadata. **Dual-layer architecture**: Base Layer (BL, 8/10 bit, HDR10 or SDR compatible) + Enhancement Layer (EL, 12 bit, carrying additional luminance information). Profile 8 (10 bit, HEVC, streaming mainstream) and Profile 9 (10 bit, HEVC, mobile legacy, now largely superseded by Profile 8) are the most common consumer configurations.

**EETMO (End-to-End Tone Mapping Operator)**
The final tone mapping step inside a display device, adapting HDR content (PQ-encoded + metadata) to the luminance capability of that specific display. Input: PQ-encoded HDR frame + MaxCLL/MaxFALL + mastering display information. Output: PQ signal adapted to the target display (luminance range compressed to fit within display capabilities). ITU-R BT.2446:2021 provides a reference algorithm for HDR→SDR (Method A), comprising an S-shaped luminance compression curve + ICtCp color scaling + sRGB output encoding.

**ICtCp Color Space**
Perceptually uniform color space recommended by ITU-R BT.2100 for HDR intermediate processing. Developed by Dolby based on Ebner's (1998) IPT color space, replacing the power function (exponent ≈ 0.43) in IPT with the PQ EOTF. Designed for HDR wide-color-gamut (BT.2020) applications. The $I$ component is perceived luminance (strong perceptual uniformity); $C_T$ (orange–blue axis) and $C_P$ (green–rose axis) are chrominance components. In HDR tone mapping, only the $I$ channel is modified; $C_T$ and $C_P$ are held constant, naturally preventing hue shifts — superior to directly scaling luminance in linear RGB space.

**MaxCLL and MaxFALL**
Two key luminance statistics in HDR10 static metadata. **MaxCLL** (Maximum Content Light Level): maximum absolute luminance of any single pixel in the content (cd/m²), $\text{MaxCLL} = \max_\text{all frames}\max_{x,y} L(x,y)$. **MaxFALL** (Maximum Frame Average Light Level): maximum frame-average luminance across all frames, $\text{MaxFALL} = \max_\text{all frames}\frac{1}{HW}\sum_{x,y}L(x,y)$. The display uses these to configure EETMO parameters — when MaxCLL greatly exceeds the display's peak luminance, more aggressive highlight compression is triggered; MaxFALL reflects overall brightness and governs mid-tone mapping.

---

> **Engineering Field Notes: Metadata Mis-labeling and EOTF Mismatch in the HDR Display Pipeline**
>
> **MaxCLL/MaxFALL mis-labeling causing display overexposure:** HDR10 static metadata (SMPTE ST 2086 + CTA-861.3) requires MaxCLL (maximum single-pixel luminance across the content, in nits) and MaxFALL (maximum frame-average luminance). A common engineering error is deriving MaxCLL directly from the linear-domain ISP output peak without excluding transient overexposure frames (flash-triggered frames, AE anomaly frames). Such frames can inflate MaxCLL to 8,000–10,000 nit when the actual scene peak is only 1,500 nit. Downstream HDR TVs and phones then apply tone mapping with 8,000 nit as the reference, compressing the image by 20–30% relative to correctly labeled content. The fix: apply a 99.9th-percentile cutoff to the per-frame PQ luminance histogram before computing MaxCLL, eliminating flash-frame contamination.
>
> **HLG vs. PQ transfer function selection for scene type:** HLG's core advantage is no absolute luminance metadata dependency and strong broadcast compatibility, making it suitable for live streaming and surveillance. PQ (SMPTE ST 2084) encodes absolute luminance (0–10,000 nit), optimized for cinematic mastering and high-end displays. In mobile testing, HLG content encoded with Android MediaCodec and played back on an SDR television exhibited ~15% darker mid-tones than native SDR capture (measured white average dropped from 130 cd/m² to 110 cd/m²) due to improper HLG-to-SDR OOTF. PQ in the same scene lost ~5% highlight detail because the tone mapping parameter (`peak_luminance=1000 nit`) was set too high for the content. For mobile-camera HDR video at peak luminance ≤ 1,000 nit, HLG is recommended as the default for best SDR compatibility.
>
> **EOTF mismatch causing highlight clipping:** When the ISP outputs PQ-encoded data but the display driver's EOTF configuration has not been updated (e.g., after a software update that failed to refresh the `gralloc` metadata field), the display decodes the PQ signal as sRGB/gamma 2.2. All highlights with PQ code value > 600 (corresponding to ~200 nit and above) are linearly clipped to white. On Qualcomm Android platforms, this bug appears when `qdcm_calib_data.xml` is misconfigured; the symptom is "HDR video highlights appear white." Diagnosis: `adb shell dumpsys SurfaceFlinger | grep -i "eotf"` to inspect the current EOTF setting; use Qualcomm Display Calibration Tool to verify that `output_transfer_function` is `PQ` rather than `GAMMA_2_2`. On HiSilicon Kirin platforms, the analogous issue occurs when `hdr_metadata_type` is not switched from HDR10 to HLG, causing the display pipeline to apply an HDR10 tone mapper to HLG content and producing ~0.5 EV of mid-tone overexposure.
>
> *References: ITU-R BT.2100, 2018; SMPTE ST 2084, 2014; CTA-861.3, 2015.*

## Figures

![hdr display pipeline](img/fig_hdr_display_pipeline_ch.png)
*Figure 1. Full architecture of the HDR display signal chain, from scene-referred RAW to PQ/HLG-encoded output. (Source: author, ISP Handbook, 2024)*

![hdr metadata](img/fig_hdr_metadata_ch.png)
*Figure 2. HDR static metadata (SMPTE ST 2086) structure: MaxCLL, MaxFALL, and mastering display luminance parameters. (Source: SMPTE, ST 2086, 2018)*

![hdr pq hlg display](img/fig_hdr_pq_hlg_display_ch.png)
*Figure 3. Luminance rendering comparison of PQ and HLG transfer functions on displays with different peak luminance levels. (Source: ITU-R, BT.2100, 2018)*

![hdr standards comparison](img/fig_hdr_standards_comparison_ch.png)
*Figure 4. Comparison of mainstream HDR standards: HDR10, HLG, and Dolby Vision — transfer functions, bit depth, and metadata types. (Source: author, ISP Handbook, 2024)*

![sdr to hdr mapping](img/fig_sdr_to_hdr_mapping_ch.png)
*Figure 5. HDR-to-SDR tone mapping relationship, showing the S-shaped luminance compression curve of BT.2446 Method A. (Source: ITU-R, BT.2446, 2021)*

![display pipeline](img/fig_display_pipeline_ch.png)
*Figure 6. Full display pipeline block diagram for HDR video playback, from PQ decoding through EETMO adaptation to the target display. (Source: author, ISP Handbook, 2024)*

![eotf curves](img/fig_eotf_curves_ch.png)
*Figure 7. PQ EOTF and HLG EOTF transfer function curves, showing the luminance–code-value relationship for both HDR formats. (Source: SMPTE, ST 2084, 2014)*

![hdr display standards](img/fig_hdr_display_standards_ch.png)
*Figure 8. HDR display standards specifications: peak luminance, color gamut, and bit depth in industry certification requirements. (Source: author, ISP Handbook, 2024)*

![hdr sdr mapping](img/fig_hdr_sdr_mapping_ch.png)
*Figure 9. End-to-end HDR-to-SDR tone mapping (EETMO) process, illustrating highlight compression and color scaling steps. (Source: ITU-R, BT.2446, 2021)*

---

## §8 Deep Dive: Engineering Implementation and Industry Applications

### 8.1 PQ EOTF Engineering Details

#### 8.1.1 10-bit Encoding Precision: Minimum Luminance Resolution

PQ EOTF encoding precision varies significantly across the luminance range. Let the 10-bit code word $n \in \{0, 1, \ldots, 1023\}$ correspond to normalized signal $E = n / 1023$. The luminance difference between adjacent code words (minimum luminance resolution) is:

$$\Delta Y(n) = Y_{\text{EOTF}}\!\left(\frac{n+1}{1023}\right) - Y_{\text{EOTF}}\!\left(\frac{n}{1023}\right)$$

**Very dark region (~0.005 nit) derivation:**

At $Y \approx 0.005$ cd/m², the derivative of the PQ EOTF (sensitivity of luminance to code word) is extremely low. Numerical evaluation:

- Code word $n = 1$ ($E \approx 0.000977$) corresponds to $Y_1 \approx 1.78 \times 10^{-5}$ cd/m²
- Code word $n = 2$ corresponds to $Y_2 \approx 1.85 \times 10^{-5}$ cd/m²
- Minimum resolution ≈ $0.007 \times 10^{-3}$ cd/m² (0.007 mcd/m²)

Near 0.005 nit (5 mcd/m²):
- Corresponding code word range ≈ $n \approx 40$–$45$; code word spacing ≈ $\Delta Y \approx 0.2$ mcd/m²

**This means 10-bit PQ has a quantization step of ~0.005 nit in dark regions**, precisely matching the JND threshold in Barten's model at that luminance level (~0.005–0.01 nit) — achieving perceptually lossless encoding.

**PQ code word lookup table for key luminance levels (every 100 nit up to 10,000 nit):**

| Luminance (nit) | PQ Code Word (10-bit) | Normalized E | Note |
|----------------|----------------------|-------------|------|
| 0 | 0 | 0.0000 | Absolute black |
| 1 | 106 | 0.1036 | Typical shadow reference |
| 10 | 257 | 0.2513 | Dim interior |
| 50 | 380 | 0.3714 | SDR white point reference |
| 100 | 441 | 0.4310 | SDR peak |
| 200 | 503 | 0.4912 | Entry-level HDR |
| 300 | 534 | 0.5219 | — |
| 400 | 557 | 0.5442 | — |
| 500 | 575 | 0.5618 | Mid-range HDR TV |
| 600 | 591 | 0.5774 | — |
| 700 | 604 | 0.5906 | — |
| 800 | 616 | 0.6020 | — |
| 900 | 627 | 0.6125 | — |
| **1000** | **636** | **0.6217** | **Typical HDR10 mastering luminance** |
| 1100 | 645 | 0.6303 | — |
| 1200 | 653 | 0.6381 | iPhone 15 Pro peak |
| 1500 | 674 | 0.6589 | Flagship OLED TV |
| 2000 | **700** | 0.6843 | VESA DisplayHDR 2000 |
| 3000 | 731 | 0.7146 | — |
| **4000** | **754** | **0.7368** | **Dolby Cinema screen** |
| 5000 | 772 | 0.7548 | — |
| 10000 | 823 | 0.8047 | PQ full scale |

**Key observation:** The range 0–1,000 nit uses 636 code words (62% of the range), while 1,000–10,000 nit uses only 187 code words (18%). This matches the human visual system's higher sensitivity at low-to-mid luminance levels.

#### 8.1.2 MaxCLL/MaxFALL Measurement in Real Products

In a smartphone ISP, MaxCLL and MaxFALL are computed in real time by the **ISP statistics engine**, not as offline post-processing.

**MaxCLL statistics implementation:**

The ISP statistics module tracks a global rolling maximum of HDR luminance per frame:

```python
# Pseudo-code: MaxCLL computation in the ISP statistics engine
def update_maxcll(frame_linear_luma, current_maxcll):
    # Convert linear luminance to absolute cd/m² using camera scene luminance calibration
    frame_cdm2 = frame_linear_luma * scene_luminance_scale
    frame_max = frame_cdm2.max()
    return max(current_maxcll, frame_max)
```

In practice, ISP hardware computes local maximums over **statistics blocks** (e.g., $256 \times 256$ pixels), then takes the global maximum:

$$\text{MaxCLL} = \max_{i,j} \left[ \max_{(x,y) \in \text{block}_{ij}} L_{\text{PQ-decoded}}(x,y) \right]$$

**MaxFALL statistics implementation (sliding window):**

$$\text{MaxFALL} = \max_{t=1}^{T} \left( \frac{1}{H \cdot W} \sum_{x=1}^{H} \sum_{y=1}^{W} L_t(x,y) \right)$$

In video recording, $T$ is the total number of recorded frames. For live streaming, the implementation typically uses a sliding window of the past $N = 30$–$60$ frames to track the maximum frame-average luminance.

> **Engineering note:** When the scene contains intense point light sources (e.g., direct sun in frame), MaxCLL can reach the sensor saturation ceiling (potentially $10^6$ nit at ISO 100). Production implementations typically cap MaxCLL at 10,000 nit to prevent metadata outliers from corrupting downstream display behavior.

---

### 8.2 HLG System Gamma and Display Luminance

#### 8.2.1 BT.2100 System Gamma Formula

BT.2100 defines the HLG OOTF system gamma as:

$$\gamma = 1.2 + 0.42 \cdot \log_{10}\!\left(\frac{L_W}{1000}\right)$$

where $L_W$ is the display peak luminance (cd/m²). At different peak luminances:

| Display Peak $L_W$ (nit) | System Gamma $\gamma$ | Practical Meaning |
|-------------------------|----------------------|------------------|
| 300 | 0.98 | Near-linear; closest to SDR display behavior |
| 600 | 1.11 | Mild nonlinearity; entry-level HDR |
| 1000 | **1.20** | **BT.2100 standard reference value** |
| 2000 | 1.33 | Significant nonlinearity |
| 4000 | 1.45 | Strong nonlinearity; large peak perception boost |

The system gamma $\gamma$ is applied in the HLG OOTF:

$$F_D(x,y) = \alpha \cdot \left[E_s(x,y)\right]^{\gamma - 1} \cdot \overrightarrow{E_s}(x,y)$$

where $\alpha = L_W$ (display peak luminance), $E_s$ is the scene-referred linear signal (normalized to $[0,1]$), and $\overrightarrow{E_s}$ denotes vector application to each RGB channel independently.

#### 8.2.2 Rendered Output Luminance of HLG on Different Screens

The table below gives the actual output luminance (cd/m²) of an HLG signal on 600/1000/2000 nit screens, where scene signal $E_s$ ranges from 0 (scene black) to 1 (scene reference white):

| Scene Signal $E_s$ | HLG Signal $E$ | 600 nit output (nit) | 1000 nit output (nit) | 2000 nit output (nit) |
|--------------------|----------------|---------------------|----------------------|----------------------|
| 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 0.083 (= 1/12) | 0.500 | 40.1 | 62.5 | 118.7 |
| 0.100 | 0.548 | 47.2 | 73.4 | 139.4 |
| 0.200 | 0.702 | 89.0 | 138.2 | 262.5 |
| 0.300 | 0.790 | 127.9 | 198.4 | 376.8 |
| 0.400 | 0.849 | 165.8 | 257.1 | 488.2 |
| 0.500 | 0.892 | 203.1 | 314.9 | 598.5 |
| 0.600 | 0.927 | 239.8 | 371.8 | 706.4 |
| 0.700 | 0.956 | 275.5 | 427.2 | 811.4 |
| 0.800 | 0.982 | 310.4 | 481.4 | 914.4 |
| 0.900 | 1.004 | 344.6 | 534.3 | 1015.5 |
| **1.000** | **1.000** | **375.0** | **581.4** | **1105.0** |

**Key observations:**
1. HLG signal $E = 1.0$ on a 1,000 nit display renders to ~581 nit, **not to peak luminance** — this is intentional (HLG reserves headroom for specular highlights in brighter scenes).
2. A 2,000 nit screen has a larger system gamma (1.33), causing **darker mid-tones relative to a 1,000 nit screen** but greatly extended highlight range.
3. A 600 nit screen has system gamma close to 1 (1.11); the output is nearly linear and provides the best SDR compatibility.

#### 8.2.3 HLG Inverse EOTF Implementation

The HLG display-side EOTF (electrical signal $E$ → display luminance $F_D$) consists of two steps:

**Step 1: Inverse OETF (BT.2100 Table 5 HLG reference EOTF)**

Piecewise inverse function:

$$E_s = \begin{cases}
\dfrac{E^2}{3} & \text{if } E \leq 0.5 \\[8pt]
\dfrac{\exp\!\left(\dfrac{E - c}{a}\right) + b}{12} & \text{if } E > 0.5
\end{cases}$$

where $a = 0.17883277$, $b = 0.28466892$, $c = 0.55991073$ (same constants as in the OETF).

**Step 2: OOTF (apply system gamma)**

$$F_D = L_W \cdot E_s^{\gamma}$$

where $L_W$ is the display peak luminance and $\gamma$ is computed from the formula above.

**Python reference implementation:**

```python
import numpy as np

def hlg_eotf(E, L_W=1000.0):
    """HLG EOTF: electrical signal E [0,1] → display luminance F_D (cd/m²)"""
    a, b, c = 0.17883277, 0.28466892, 0.55991073
    # Step 1: inverse OETF → linear scene signal
    E_s = np.where(
        E <= 0.5,
        E**2 / 3.0,
        (np.exp((E - c) / a) + b) / 12.0
    )
    # Step 2: system gamma
    gamma = 1.2 + 0.42 * np.log10(L_W / 1000.0)
    F_D = L_W * np.power(np.maximum(E_s, 1e-10), gamma)
    return F_D
```

---

### 8.3 Dolby Vision Profile Comparison

#### 8.3.1 Technical Parameters by Profile

| Profile | Color Space | Transfer Function | Bit Depth | Architecture | Typical Use |
|---------|------------|------------------|-----------|-------------|------------|
| **Profile 4** | BT.2020 | PQ (ST 2084) | 10-bit | Dual-layer (BL HDR10 + EL DV RPU) | Older spec; HDR10-compatible dual-layer |
| **Profile 5** | IPTPQc2 | PQ (ITP) | 10-bit | Single-layer (no EL) | Professional production/streaming; no backward compatibility |
| **Profile 8** | BT.2020 | PQ (ST 2084) | 10-bit | Single-layer (HDR10/SDR compatible) | Streaming (Netflix/Disney+/Apple TV+) |
| **Profile 9** | BT.2020 | PQ (ST 2084) / SDR | 8-bit | Single-layer AVC (H.264) | Legacy mobile devices (superseded by Profile 8) |

**Profile 4 (dual-layer BL+EL):** The BL is a standard HDR10 signal (BT.2020 + PQ); the EL carries Dolby Vision's proprietary RPU dynamic metadata. Devices without DV support decode the BL as HDR10; DV-capable devices use the EL for frame-accurate EETMO.

**Profile 5 (IPTPQc2 single-layer):** Uses Dolby's proprietary IPTPQc2 color space (based on IPT + PQ; better hue uniformity than BT.2020 RGB + PQ), but **contains no compatibility layer** and requires a dedicated DV decoder. Used in professional reference monitors (e.g., Sony BVM-HX310).

**Profile 8 (backward-compatible):** The dominant consumer Dolby Vision format. A single video file is correctly decoded by both HDR10 devices (ignoring DV metadata) and Dolby Vision devices (using dynamic metadata for precise per-frame EETMO).

#### 8.3.2 iPhone Dolby Vision Recording: Technical Implementation

iPhone 12 and later support **Dolby Vision Profile 8.4** (mobile-specific sub-profile) video recording. Key technical aspects:

**Dual-exposure frame merging → PQ encoding:**

1. Rear camera captures in **dual-exposure RAW** mode (short + long exposure, or PDAF frame + main frame).
2. ISP completes HDR frame merging (Part 2, Ch10) and outputs a linear HDR signal.
3. ISP-internal tone mapping (Apple proprietary algorithm) compresses the dynamic range.
4. **PQ OETF encoding** to 10-bit BT.2020 color space.

**HEVC dual-layer encoding:**

iPhone uses two independent H.265 (HEVC) video streams packaged in a single `.MOV` file:

- **Base Layer (BL):** HDR10-compatible 10-bit PQ stream (Profile 8's HDR10 portion)
- **Enhancement Layer (EL) / Metadata Layer:** Dolby Vision dynamic metadata stream, specifying per-frame EETMO parameters

```
.MOV file structure (Dolby Vision Profile 8.4):
  ├── Video Track 1 (HEVC, 10-bit, BT.2020 PQ)  ← HDR10 compatible
  ├── Video Track 2 (HEVC, Dolby Vision metadata) ← DV dynamic metadata
  ├── Audio Track (AAC)
  └── Metadata: MaxCLL, MaxFALL (static, for HDR10 fallback decoding)
```

**Per-frame dynamic metadata contents:** Each frame carries SMPTE ST 2094-10 metadata including:
- `signal_peak_luminance`: peak PQ signal luminance for this frame
- `target_display_peak_luminance`: target display peak luminance (for EETMO adaptation)
- `tone_mapping_params`: S-curve anchor points (typically 3–5 control points)

#### 8.3.3 Dolby Vision Certification Requirements for Smartphone OEMs

Dolby Vision certification imposes the following technical requirements on smartphone manufacturers (based on Dolby's public licensing guidelines):

**Recording-side certification:**

| Requirement | Specification |
|-------------|--------------|
| Recording color gamut | BT.2020 (P3 coverage ≥ 90%) |
| Transfer function | PQ (accuracy < 0.5 ΔE in ICtCp) |
| Dynamic metadata | Generated per frame (≥ 24 fps) |
| Peak luminance | ISP output equivalent ≥ 1,000 nit |
| HDR frame merging | Multi-frame HDR fusion (motion artifacts < 2% of frames) |

**Playback-side certification:**

| Requirement | Specification |
|-------------|--------------|
| Display peak luminance | ≥ 800 nit (typical certified display) |
| EETMO accuracy | ΔE (ICtCp) vs. Dolby reference EETMO < 2.0 |
| Color gamut coverage | DCI-P3 ≥ 90% (typically ≥ 98%) |
| Bit depth | 10-bit panel driver |
| Frame rate | 60 Hz without frame drop (4K Dolby Vision playback) |

Xiaomi 14 Ultra, vivo X100 Pro, and other flagship devices have passed Dolby Vision Profile 8 dual certification for recording and playback, supporting **12-bit internal processing** downsampled to 10-bit for output encoding.

---

### 8.4 HDR-to-SDR Tone Mapping (Downgrade Path)

#### 8.4.1 BT.2408 Operational Practice Guidelines

ITU-R BT.2408:2022 (*Operational practices in HDR television production*) provides practical guidelines for broadcast-grade HDR→SDR downgrade:

**Core principle:** SDR downgrade should not be an afterthought — it should be generated in sync with HDR during the mastering stage. BT.2408 recommends:

1. **Scene absolute luminance alignment:** SDR reference white = 203 cd/m² (not the conventional 100 cd/m²). This value originates from the normative anchor point unifying HLG/PQ luminance: in the HLG system, scene reference white maps to 203 cd/m² display luminance, corresponding to approximately 58% of the PQ encoding range (203/10000 ≈ 2%), rather than from empirical measurements of modern TV brightness.

2. **Highlight protection zone:** The HDR content range 203–10,000 nit (roughly the top 30% of PQ code words) maps to 100%–120% in SDR (allowing brief near-white peaks), via a soft shoulder curve rather than hard clipping.

3. **Mid-tone protection:** 18% reflectance gray (typical mid-grey) in HDR corresponds to ~203 × 0.18 = 36.5 cd/m² (PQ code value ~490); after SDR downgrade it should land at 38%–42% signal level (visually "correct exposure").

**BT.2408 recommended SDR downgrade curve (parametric S-curve):**

$$Y_{\text{SDR}} = \frac{Y_{\text{HDR}} \cdot (1 + \alpha \cdot Y_{\text{HDR}} / Y_{\text{peak,HDR}})}{1 + \alpha \cdot Y_{\text{HDR}} / Y_{\text{peak,HDR}}}$$

This is a Michaelis–Menten form; $\alpha$ controls the shoulder inflection point (typical $\alpha = 6$–$12$).

#### 8.4.2 SMPTE 2094-40: Samsung HDR10+

HDR10+ is a **dynamic metadata** extension jointly developed by Samsung and Amazon, standardized as SMPTE 2094-40:

- Fully backward-compatible with HDR10 (static ST 2086 metadata as fallback)
- Dynamic metadata embedded as **SEI (Supplemental Enhancement Information)** messages in the HEVC/AVC bitstream
- Per-frame or per-scene dynamic range compression curve (Bezier spline, typically 3–5 knot points)

**HDR10+ to SDR luminance mapping ($L_{\text{out}} = f(L_{\text{in}})$):**

$$L_{\text{out}} = L_{\text{SDR,peak}} \cdot \frac{L_{\text{in}}^{\gamma_{\text{curve}}}}{L_{\text{in}}^{\gamma_{\text{curve}}} + k \cdot L_{\text{in,pivot}}^{\gamma_{\text{curve}}}}$$

where:
- $L_{\text{SDR,peak}} = 100$ cd/m² (SDR peak)
- $L_{\text{in,pivot}}$: curve inflection luminance (determined by `distribution_maxrgb_percentiles` in dynamic metadata, typically the $p_{99.5}$ percentile luminance)
- $\gamma_{\text{curve}}$: Bezier curve shape parameter (derived from spline knots in metadata)
- $k$: overall luminance scale factor

#### 8.4.3 Quantifying Perceptual Loss in BT.2020-to-sRGB Gamut Compression

When HDR content (BT.2020 color gamut) is compressed to SDR (sRGB / BT.709 gamut), colors outside sRGB require remapping. The perceptual cost varies significantly with method.

**Loss sources:**

BT.2020 exceeds BT.709 by approximately **62%** of the BT.2020 gamut area (CIE xy chromaticity diagram; BT.2020 area 0.2972, BT.709 area 0.1121, excess = 0.1851, fraction = 0.1851/0.2972 ≈ 62%). This means ~62% of the HDR color gamut requires remapping during SDR compression.

**Gamut mapping method comparison (perceptual loss in ΔE 2000):**

| Gamut Mapping Method | Mean ΔE 2000 (BT.2020→sRGB) | Hue Preservation | Saturation Loss | Application |
|---------------------|---------------------------|-----------------|----------------|-------------|
| Clipping | 4.2 | Low | High | Fast but poor quality |
| ICC Perceptual Intent | 2.1 | High | Moderate | General purpose |
| BT.2446 Gamut Compression | 1.8 | High | Moderate–Low | Broadcast standard |
| ACES Reference Gamut Compression | 1.4 | Excellent | Low | Film/VFX production |
| HDR10+ Gamut MMR (matrix + LUT) | 1.6 | High | Low | Best consumer-grade |

**Subjective perceptibility thresholds:** ΔE 2000 < 1.0 = "no perceptible difference"; 1.0–2.0 = "slight difference (visible to professionals)"; > 3.0 = "obvious color distortion." ACES and HDR10+ MMR approach the just-noticeable-difference threshold.

---

### 8.5 ISP Output-Side HDR Encoding Pipeline

#### 8.5.1 End-to-End Data Flow: RAW to Container

A flagship smartphone HDR video recording pipeline, from CMOS sensor to packaged file:

```
┌─────────────────────────────────────────────────────────────────┐
│  CMOS Sensor Output                                              │
│  RAW Bayer, 14-bit, linear, dynamic range > 80 dB               │
└──────────────────────┬──────────────────────────────────────────┘
                       │  Dual-exposure / multi-frame HDR
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  ISP Front-End (fully linear domain)                             │
│  BLC → PDPC → LSC → dual-exposure HDR merge → Demosaic → Denoise│
│  Color space: sensor native → BT.2020 linear (CCM)              │
│  Bit depth: 14-bit → 16-bit (internal) → 14-bit                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │  Linear HDR, BT.2020, 16-bit
                       │  Dynamic range: ~10^5:1 (~16.6 stops)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  Local Tone Mapping (optional, depends on recording mode)        │
│  · HDR record mode: skip TMO, preserve full DR → PQ encoding     │
│  · SDR record mode: HDRNet / Guided Filter TMO → sRGB Gamma      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  HDR Encoding (HDR recording path)                               │
│  PQ OETF (ST 2084): linear [0, 10000 nit] → E [0, 1]            │
│  Color space: BT.2020 retained                                   │
│  Bit depth: 10-bit (consumer) / 12-bit (professional ProRes HQ)  │
│  MaxCLL / MaxFALL statistics (ISP engine, real-time)             │
└──────────────────────┬──────────────────────────────────────────┘
                       │  10-bit PQ BT.2020 YCbCr (4:2:0)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  Video Encoder (Codec)                                           │
│  H.265 HEVC Main 10 Profile / H.266 VVC                         │
│  Chroma subsampling: 4:2:0 (consumer) / 4:2:2 (professional)    │
│  Bitrate: 10-bit 4K HLG ~50 Mbps; 10-bit 4K HDR10 ~60 Mbps     │
│  (Apple ProRes 422 HQ reference: ~1.4 Gbps at 4K30)             │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  Container Packaging                                             │
│  Format: .MOV (Apple) / .MP4 (Android)                          │
│  Metadata injection:                                             │
│    - SMPTE ST 2086 (static: MaxCLL, MaxFALL, color primaries)    │
│    - Dolby Vision Profile 8 SEI (dynamic: per-frame EETMO params)│
│    - HDR10+ SEI (SMPTE 2094-40, per-scene Bezier curve)          │
└─────────────────────────────────────────────────────────────────┘
```

#### 8.5.2 iPhone ProRes Video HDR Metadata Injection

Apple iPhone 14 Pro and later support **Apple ProRes 422 HQ** HDR video recording. Metadata injection process:

**ProRes container metadata structure:**

ProRes uses a QuickTime `.MOV` container; HDR metadata is injected through the following atoms:

1. **`colr` Atom (Color Parameter Box):**
   - `color_primaries = 9` (BT.2020)
   - `transfer_characteristics = 16` (PQ / ST 2084)
   - `matrix_coefficients = 9` (BT.2020 non-constant luminance)

2. **`mdcv` Atom (Mastering Display Color Volume, corresponds to SMPTE ST 2086):**
   ```
   display_primaries_x/y: BT.2020 primary chromaticity coordinates (x,y)
   white_point_x/y: D65 white point
   max_display_mastering_luminance: 1000 (nit)
   min_display_mastering_luminance: 0.005 (nit)
   ```

3. **`clli` Atom (Content Light Level: MaxCLL + MaxFALL):**
   - Values updated in real time by the ISP statistics engine during recording (rolling maximum); written to the file header after recording ends.

4. **Dolby Vision extension (Profile 8.4):**
   - Per-frame HEVC SEI (type `user_data_registered_itu_t_t35`, country code = 0xB5, provider code = 0x003B)
   - Payload: Dolby Vision RPU (Reference Processing Unit), containing per-frame EETMO control points

---

### 8.6 Engineering Constraints in Smartphone HDR Video Recording

#### 8.6.1 Thermal Throttling and Its Impact on Peak Luminance

HDR video recording is one of the most thermally demanding sustained workloads on a smartphone (ISP + video encoder + storage write all active simultaneously). As SoC temperature rises, DVFS triggers **thermal throttling**, degrading HDR quality.

**Impact of thermal throttling on HDR:**

| SoC Junction Temperature | ISP Mode | HDR Impact |
|--------------------------|----------|-----------|
| < 75°C | Full performance | HDR fully functional; MaxCLL > 1,000 nit normal output |
| 75–85°C | Light throttle | Frame rate may drop to 24 fps (from 30 fps); peak luminance unaffected |
| 85–95°C | Moderate throttle | HDR merge algorithm simplified (2-frame → single-frame tone map); dynamic metadata generation accuracy reduced |
| > 95°C | Heavy throttle | **Automatic downgrade to SDR recording**; ISP shuts down the HDR pipeline to reduce power |

**Measured peak luminance degradation:**

On a typical flagship (Snapdragon 8 Gen 2) recording 4K HDR continuously for 5 minutes, ISP clock frequency reduces by ~30% due to thermal throttling. HDR merge accuracy degrades, and measured MaxCLL drops from ~1,200 nit at the start of recording to approximately **900 nit** (~−25%). This is one of the primary engineering challenges in consumer smartphone HDR video.

**Mitigation strategies:**
- Hardware: vapor chamber (VC) heat spreader to maximize contact area
- Software: monitor SoC temperature in real time; proactively reduce encoding frame rate (rather than reducing HDR quality) when light throttle begins
- Usage: cool the device before recording; avoid continuous recording under direct sunlight

#### 8.6.2 Bitrate Requirements for HDR Video Encoding

HDR video incurs additional bitrate compared to SDR from two sources:
1. **Bit depth increase** (8-bit SDR → 10-bit HDR): +25% information content
2. **Gamut expansion** (BT.709 → BT.2020): wider gamut contains more complex chrominance information; harder to encode efficiently

**Typical bitrate comparison (HEVC H.265, 4K@30fps):**

| Format | Color Space | Bit Depth | Typical Bitrate | Relative |
|--------|------------|-----------|----------------|---------|
| 8-bit SDR (BT.709 sRGB) | 4:2:0 8-bit | — | 25–35 Mbps | 1× |
| 10-bit HLG (BT.2020) | 4:2:0 10-bit | — | **45–55 Mbps** | ~1.6× |
| 10-bit HDR10 (BT.2020 PQ) | 4:2:0 10-bit | — | **50–65 Mbps** | ~1.8× |
| 10-bit Dolby Vision Profile 8 | 4:2:0 10-bit | — | **55–70 Mbps** | ~2× |
| Apple ProRes 422 HQ SDR | 4:2:2 10-bit | — | ~800 Mbps | ~25× |
| Apple ProRes 422 HQ HDR | 4:2:2 10-bit | — | ~1,400 Mbps | ~45× |

**H.266 VVC improvement:** At equivalent perceptual quality, VVC achieves ~40–50% better compression efficiency than HEVC. 10-bit 4K HDR10 bitrate can drop to ~30–40 Mbps. As of 2025, most smartphone hardware encoders do not yet fully support VVC.

**Storage capacity reference:**

| Format | Bitrate (Mbps) | 1-min file size | Recording time on 64 GB |
|--------|---------------|----------------|------------------------|
| 8-bit SDR 4K30 | 30 | 225 MB | ~47 min |
| 10-bit HDR10 4K30 | 60 | 450 MB | ~23 min |
| Apple ProRes HQ HDR 4K30 | 1,400 | 10.5 GB | ~1.6 min |

#### 8.6.3 HDR Downgrade Strategy in Low-Power Mode

When the device enters **Low Power Mode / Battery Saver**, the system limits HDR recording capabilities. Downgrade policies by vendor:

| Power Level | Apple iPhone | Qualcomm Reference Platform | Samsung Galaxy |
|-------------|-------------|----------------------------|---------------|
| Light saving (< 20% battery) | Maintain full HDR; limit frame rate (60 fps → 30 fps) | Disable HDR10+; retain HDR10 | Disable HDR10+; retain HDR10 |
| Moderate saving (< 15% battery) | Disable ProRes HDR recording; retain HEVC HDR | Force SDR recording | Force SDR; limit 4K → 1080P |
| Heavy saving (< 10% battery) / low battery mode | Full downgrade to SDR; limit to 1080P30 | Minimum quality mode | Minimum quality mode |

**Dolby Vision recording power overhead:**

The additional power draw of Dolby Vision relative to HDR10 comes primarily from **dynamic metadata generation** (per-frame EETMO parameter computation, running on Dolby's licensed DSP/NPU algorithm), typically adding ~**50–100 mW** (1–3% of the total recording power of ~3–5 W). At low battery levels, dynamic metadata generation is the first HDR feature disabled; the system degrades to static HDR10.
