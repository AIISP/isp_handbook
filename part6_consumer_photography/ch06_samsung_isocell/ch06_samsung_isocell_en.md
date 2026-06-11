# Part 6, Chapter 06: Samsung ISOCELL, Tetra²pixel, and the AI-ISP Technology Stack

> **Position:** This chapter provides an in-depth analysis of Samsung's ISOCELL sensor technology ecosystem, from pixel isolation processes to ultra-high-resolution pixel binning (Tetra²pixel) and the AI-ISP engine, covering theory, engineering implementation, and tuning guidelines.
> **Prerequisites:** Vol.6 Ch.1 (Consumer Photography Evolution), Vol.1 Ch.6 (RAW Format and CFA), Vol.2 Ch.2 (Demosaicing)
> **Audience:** Algorithm engineers, sensor engineers

---

## §1 ISOCELL Technology Foundation

### 1.1 The Problem with Traditional Pixel Isolation

In conventional CMOS image sensor (CIS) architectures, isolation between adjacent pixels relies on Shallow Trench Isolation (STI) structures. However, as pixel pitch shrinks below 1.2 µm, STI can no longer fully prevent photo-generated electrons from migrating across pixel boundaries — a phenomenon known as **electrical crosstalk**.

Electrical crosstalk manifests along two dimensions:
- **Spatial crosstalk:** Photo-generated electrons from one pixel leak into neighboring pixels, producing blurred edges in the output image.
- **Color crosstalk:** Photo-generated electrons cross CFA (Color Filter Array) boundaries into the wrong color channel, causing green pixels to "contaminate" the red/blue channels and degrading color fidelity.

Quantitatively, traditional STI isolation at 0.9 µm pixel pitch can exhibit color crosstalk of **8%–12%** (Samsung internal test data, 2018), meaning roughly 10% of the signal in the red channel actually originates from leakage out of adjacent green pixels.

### 1.2 ISOCELL: Physical Polymer Wall Isolation

Samsung introduced **ISOCELL (Inter-pixel Isolation Cell)** technology in 2013. The core idea is to construct a physical polymer wall around each pixel, completely replacing the STI approach that relied solely on material electrical properties.

How the isolation wall works:
1. Physically blocks the lateral migration path of photo-generated charge carriers (carrier blocking);
2. Forms an optical cavity, reducing photon scattering between adjacent pixels;
3. Reduces surface recombination near the bottom p-n junction, improving quantum efficiency.

Engineering result: compared to the same-generation conventional process, ISOCELL increases the **Full Well Capacity (FWC) by approximately 30%** while maintaining color crosstalk performance. This effectively raises the maximum photon capacity of each pixel and extends single-frame dynamic range.

### 1.3 ISOCELL Plus (2018): Organic Material Replaces Metal Grid

In 2018, Samsung introduced **ISOCELL Plus**, replacing the isolation wall material from a conventional metal grid to a novel organic material grid. This addressed two major drawbacks of the metal grid:

| Issue | Metal Grid (Original ISOCELL) | Organic Material (ISOCELL Plus) |
|-------|-------------------------------|----------------------------------|
| Photon absorption loss | Metal absorbs a portion of incident light, reducing the number of photons reaching the photodiode | Organic material has a more favorable refractive index and lower reflection loss, increasing light throughput into the pixel by approximately **15%** |
| Adhesion to CFA | Large thermal expansion coefficient mismatch between metal and color filter material leads to interface delamination after thermal cycling | Organic material is compatible with CFA materials, improving manufacturing yield and long-term reliability |

### 1.4 ISOCELL 2.0 (2020): Color Filter Material Upgrade

The core innovation of **ISOCELL 2.0** lies not in the isolation wall but in a reformulation of the Color Filter (CFA) material itself. The next-generation CFA material exhibits a higher photon absorption coefficient for target wavelengths, improving **light absorption efficiency by approximately 12%**, while maintaining a narrower passband across the visible spectrum (400–700 nm), which helps reduce color crosstalk.

Quantitative impact:
$$\text{SNR}_\text{improvement} = 10\log_{10}\left(\frac{\eta_\text{new}}{\eta_\text{old}}\right) \approx 10\log_{10}(1.12) \approx +0.5\ \text{dB}$$

where $\eta$ is the pixel quantum efficiency (QE). A 0.5 dB SNR improvement may seem modest, but for Samsung's multi-frame night photography (Nightography), raising the per-frame baseline SNR reduces the number of frames needed to reach a target SNR, indirectly lowering the probability of motion ghosting.

### 1.5 Key Performance Summary

| Generation | Year | Isolation | FWC Gain | Light Throughput Gain | Color Crosstalk |
|------------|------|-----------|----------|-----------------------|-----------------|
| Traditional STI | ~2012 | Shallow trench | Baseline | Baseline | ~12% |
| ISOCELL | 2013 | Physical polymer wall | +30% | +0% | ~6% |
| ISOCELL Plus | 2018 | Organic material wall | +30% | +15% | ~4% |
| ISOCELL 2.0 | 2020 | Organic wall + new CFA | +30% | +27% | ~3% |

---

## §2 Dual Pixel Phase Detection Autofocus (Dual Pixel PDAF)

### 2.1 Working Principle

The **Dual Pixel PDAF** first introduced in the Samsung Galaxy S7 (2016) represents a paradigm shift in sensor design. Unlike conventional PDAF, which dedicates a subset of pixels exclusively to phase detection, Dual Pixel splits **every imaging pixel** into a left-half photodiode (Left PD) and a right-half photodiode (Right PD).

From an optical perspective, the left half-pixel and right half-pixel receive light entering through the left aperture and right aperture of the lens, respectively. When the subject lies exactly on the focal plane, the light intensity distributions received by the left and right sub-pixels are perfectly symmetrical and the phase difference is zero. When the subject deviates from the focal plane, a systematic phase difference appears between the left and right sub-pixels; the direction of the phase difference indicates the focus direction (front/back focus), and the magnitude is proportional to the defocus amount.

Relationship between phase difference and defocus:

$$d = \frac{\phi \cdot f}{2 \cdot (1/F\#) \cdot p}$$

where:
- $d$: defocus distance (meters)
- $\phi$: phase difference between left and right sub-pixel signals (in pixels)
- $f$: lens focal length
- $F\#$: f-number (aperture)
- $p$: pixel pitch

### 2.2 Significance of 100% PDAF Coverage

Traditional PDAF (e.g., the 693-point PDAF array of the Nikon D850) places dedicated PDAF pixels only at specific locations. These pixels have one side masked by metal, appearing as line-shaped bright/dark defects in the RAW image that must be corrected by a PDAF pixel replacement algorithm, sacrificing actual imaging information.

Dual Pixel's full-pixel coverage delivers three engineering advantages:

1. **AF speed:** On the S7, autofocus time in good light dropped from approximately 0.5 s to **0.03 s** (Samsung official data), a roughly 16× improvement. In scenes with subjects moving at 1/100 s timescales, AF speed determines whether the decisive moment is captured.
2. **Low-light AF:** Phase information is available at every pixel; the algorithm does not need to fall back to contrast-detection (hill-climbing). Reliable phase-based focus is maintained even below -2 EV.
3. **No SNR penalty:** After focus measurement, the left and right sub-pixel signals are simply summed (Left PD + Right PD = full pixel signal), yielding exactly the same sensitivity as a single-pixel design — no photon-collection area is sacrificed.

### 2.3 Performance Comparison with Traditional PDAF

| Metric | Traditional PDAF (2015 flagship) | Dual Pixel (Galaxy S7, 2016) |
|--------|----------------------------------|-------------------------------|
| AF coverage | ~8%–20% (dedicated pixels) | **100%** |
| AF speed (good light) | ~0.5 s | **~0.03 s** |
| Minimum focus luminance (low light) | -1 EV | **-4 EV** (S23 Ultra) |
| RAW data loss | Yes (dedicated pixels require correction) | None |
| Sensor area overhead | Low (few dedicated pixels) | Medium (two sub-PDs per pixel) |

---

## §3 Pixel Binning Technology

### 3.1 Nonapixel: 9-in-1 Binning (2019)

Samsung introduced **Nonapixel** (Nona = nine, pixel = pixel) technology in 2019 on the 108 MP ISOCELL Bright HMX (debuted in the Xiaomi Note 10), combining a 3×3 = 9-pixel block into a single super-pixel.

Binning benefit analysis:

$$\text{SNR}_\text{9-in-1} = \text{SNR}_\text{single} \cdot \sqrt{9} = 3 \times \text{SNR}_\text{single}$$

$$\text{Equivalent pixel area}_\text{merged} = 9 \times A_\text{single}$$

Taking ISOCELL HMX as an example:
- Single pixel pitch = 0.8 µm, area = 0.64 µm²
- After 9-in-1 binning: equivalent pitch = 2.4 µm, area = 5.76 µm² (comparable to the Sony IMX586's 0.8 µm physical pitch with a 2.4 µm equivalent large pixel)
- 108 MP → 12 MP after 9:1 binning
- SNR gain 3× → approximately +9.5 dB, equivalent to approximately **3 stops** of sensitivity improvement

However, the implementation of Nonapixel in the Bayer domain is not a simple summation: within a 9-pixel block, the color distribution across R, G, G, G, G, B channels (a Quad-Bayer oversampled 3×3 block centered on the target pixel) is non-uniform. Channels must be merged separately — not summed across colors — to avoid color errors.

### 3.2 Tetra²pixel (2023): 4-in-1 Binning and the 200 MP ISOCELL HP2

In 2023, Samsung launched the **ISOCELL HP2** (200 MP, used in the Galaxy S23 Ultra), accompanied by **Tetra²pixel** technology that performs 2×2 = 4-pixel binning.

HP2 specifications:
- Resolution: 200 MP (16384 × 12288)
- Pixel pitch: 0.6 µm (full resolution)
- After 4-in-1 binning: 50 MP, equivalent 1.2 µm pixel
- After 16-in-1 binning (4×4): 12.5 MP, equivalent 2.4 µm pixel

Tetra²pixel adaptive switching strategy:

| Lighting condition | Mode | Resolution | Equivalent pixel size |
|--------------------|------|------------|-----------------------|
| Ample daylight (EV ≥ 12) | Full resolution | 200 MP | 0.6 µm |
| Indoor (6 ≤ EV < 12) | 4-in-1 | 50 MP | 1.2 µm |
| Low light / night (EV < 6) | 16-in-1 | 12.5 MP | 2.4 µm |

From a signal processing perspective, the adaptive mode switch is essentially a **dynamic quantization scheme**: in bright scenes, spatial resolution is preserved (trading SNR margin for resolution); in dark scenes, resolution is traded for SNR.

### 3.3 Quad Bayer Demosaicing Challenges

The CFA layout of Tetra²pixel sensors uses the **Quad Bayer** pattern — each 2×2 block of same-color pixels constitutes one logical "large pixel," arranged globally as:

```
R  R  G  G  R  R  G  G
R  R  G  G  R  R  G  G
G  G  B  B  G  G  B  B
G  G  B  B  G  G  B  B
R  R  G  G  ...
R  R  G  G
```

This CFA layout creates difficulties for standard Bayer demosaicing algorithms (such as AHD or DLMMSE):

1. **Aliasing:** In full-resolution mode, there is no cross-color sampling within the 2×2 same-color block. Low-frequency color information can be reconstructed, but high-frequency color detail (e.g., fine colored textures) is inherently under-sampled.
2. **Dedicated Quad Bayer demosaicing algorithms:** The Quad Bayer RAW must first be converted to an equivalent standard Bayer pattern (via neighborhood-difference interpolation), followed by standard demosaicing; alternatively, a joint demosaicing algorithm designed specifically for the 2×2 block structure can be used directly (such as the "Remosaic" pre-processing step described in Samsung ISOCELL white papers).
3. **Remosaic hardware acceleration:** The Exynos/Snapdragon ISPs paired with the HP2 both contain dedicated Remosaic hardware blocks that convert 200 MP Quad Bayer RAW to 200 MP standard Bayer RAW before feeding it to the standard demosaic pipeline. Latency is approximately 15–30 ms (platform-dependent).

The core algorithm of Remosaic can be simplified as: for each pixel located on a Quad Bayer block boundary, gradient-weighted cross-block interpolation replaces the within-block color average, restoring a color-space sampling distribution consistent with standard Bayer.

---

## §4 LOFIC: Single-Frame High Dynamic Range Technology

### 4.1 Dynamic Range Bottleneck of the Standard Pixel Architecture

In the standard 4T pixel architecture, photo-generated electrons transfer from the photodiode (PD) to the floating diffusion node (FD), are amplified by a source follower, and then digitized by an ADC. The charge capacity of the FD node determines the pixel's **Full Well Capacity (FWC)**, typically around **3,000–6,000 e⁻** for a 1.0 µm pixel.

Under strong illumination, the FD node saturates rapidly:

$$\text{Saturation}_\text{time} = \frac{FWC}{Q_\text{photon\_rate}} = \frac{FWC}{E \cdot A_\text{pixel} \cdot \eta \cdot \lambda / (h\nu)}$$

At luminance EV = 15 (bright direct sunlight), the FD saturation time for a 0.6 µm pixel is approximately 1/30,000 s, while exposure time is typically 1/1000 s — resulting in severe highlight clipping. The conventional remedy is to shorten exposure or stop down the aperture, but this sacrifices shadow SNR.

### 4.2 LOFIC Working Principle

**LOFIC (Lateral Overflow Integration Capacitor)** is a pixel architecture innovation that Samsung first mass-produced on the ISOCELL GN2 (2021). Its core feature is an additional lateral capacitor (LC) placed beside the standard FD node.

LOFIC operates in a dual-mode signal path:

**Mode 1: High-Gain Path (HG path — shadows / mid-tones)**
- FD node operates independently; Conversion Gain (CG) remains high (High Conversion Gain, HCG)
- Low read noise (typically 1–2 e⁻ RMS), suitable for shadow detail signals
- Full well capacity limited to FD: approximately 3,000–6,000 e⁻

**Mode 2: Low-Gain Path (LG path — highlights)**
- FD + LC operate in parallel; CG is reduced (Low Conversion Gain, LCG), but total charge capacity expands by approximately **25×** (ISOCELL GN2 specification)
- Capable of accommodating approximately 75,000–150,000 e⁻ without saturating, suitable for bright areas
- Read noise increases (approximately 5–8 e⁻ RMS), but at high signal levels shot noise dominates and read noise is not the limiting factor

### 4.3 Single-Frame HDR Merging

Mathematical model for LOFIC single-frame HDR:

Let the number of photons at a given pixel under standard exposure be $N_\text{photon}$:

$$V_\text{HG}(i,j) = \min\left(N_\text{photon} \cdot \text{CG}_H,\ V_\text{sat,HG}\right) \quad \text{(high gain, FD only)}$$

$$V_\text{LG}(i,j) = N_\text{photon} \cdot \text{CG}_L \quad \text{(low gain, FD+LC, not saturated)}$$

HDR fusion output:

$$V_\text{HDR}(i,j) = \begin{cases}
V_\text{HG}(i,j) / \text{CG}_H & \text{if } V_\text{HG} < \alpha \cdot V_\text{sat,HG} \quad \text{(use high-gain path: precise shadows)} \\
V_\text{LG}(i,j) / \text{CG}_L & \text{if } V_\text{HG} \geq \alpha \cdot V_\text{sat,HG} \quad \text{(switch to low-gain path: accurate highlights)}
\end{cases}$$

where $\alpha = 0.8–0.9$ is the switching threshold (avoids noise discontinuities from switching too close to the saturation point).

**Dynamic range improvement:**

$$\text{DR}_\text{LOFIC} = 20\log_{10}\left(\frac{FWC_\text{LCG}}{\sigma_\text{HCG,read}}\right) \approx 20\log_{10}\left(\frac{150000}{1.5}\right) \approx 100\ \text{dB} \approx 17\ \text{EV}$$

Compared to a standard single pixel (approximately 10 EV), LOFIC pushes single-frame dynamic range to approximately **13–14 EV** in practice (limited by CFA transmittance and ADC bit-width), fully matching traditional multi-frame HDR while eliminating the motion ghosting inherent to multi-frame methods.

### 4.4 LOFIC vs. Multi-Frame HDR Comparison

| Scheme | Dynamic Range | Motion Ghost | Latency | Processing Complexity |
|--------|--------------|--------------|---------|----------------------|
| Single-frame standard | ~10 EV | None | Low | Low |
| Multi-frame HDR (2 frames) | ~13 EV | Present (moving object double image) | Medium | Medium |
| LOFIC single-frame | ~13–14 EV | **None** | Low | Medium (dual-path readout) |
| LOFIC + multi-frame | ~15+ EV | Very low | High | High |

---

## §5 ProVisual Engine and Samsung AI-ISP

### 5.1 Galaxy S24 Compute Platform

The Galaxy S24 Ultra uses Qualcomm's **Snapdragon 8 Gen 3** (TSMC 4nm N4P process), while Samsung uses its own **Exynos 2400** (Samsung 4nm SF4P process) in certain regional variants. Both are paired with Samsung's proprietary imaging DSP to form the complete **ProVisual Engine**.

Hardware compute architecture:

| Compute Unit | Snapdragon 8 Gen 3 | Exynos 2400 | Responsibility |
|----|----|----|-----|
| CPU | Cortex-X4 ×1 + A720 ×5 + A520 ×2 | Cortex-X4 ×1 + A720 ×5 + A520 ×4 | 3A algorithms, scene recognition decisions |
| GPU | Adreno 750 | Xclipse 940 (AMD RDNA 3) | Post-processing, video encoding assist |
| NPU/AI | Hexagon NPU (~34 TOPS, third-party est.) | NPU (~34.7 TOPS, Samsung official) | AI denoising, scene classification, portrait |
| ISP | Spectra ISP (18-bit) | Samsung MIPI ISP | RAW processing pipeline |

### 5.2 AI Scene Optimization

The ProVisual Engine integrates a real-time scene recognition system capable of identifying **120 scene types** before RAW processing begins (far finer granularity than Google Pixel's approximately 30 categories). Scene recognition is based on a lightweight classification network running on the Hexagon NPU, with a latency of approximately **5–10 ms** per frame.

Scene recognition results drive adaptive adjustment of ISP parameters:

```
Scene type    →  ISP tuning strategy
────────────────────────────────────────────────────
Food          →  Saturation +15%, warm color temperature gain, macro sharpening enhanced
Night city    →  Multi-frame NR frame count +4, highlight rollback threshold lowered
Pet (eyes)    →  Subject segmentation enhanced, Eye AF priority activated
Sports        →  Anti-motion blur (AIS) enabled, shutter priority
Documents     →  Keystone correction, super-resolution sharpening
```

### 5.3 On-Sensor RAW AI Denoising

Traditional denoising pipelines operate in the YUV domain, discarding the noise statistical properties of the RAW domain. Samsung has implemented **AI denoising directly in the RAW domain** on the Exynos 2400 platform. The processing flow is:

1. The sensor outputs RAW (Bayer, 12–14 bit) → enters the Samsung MIPI ISP front-end;
2. The NPU receives a sub-sampled RAW image (1/4 resolution) as input to a Noise Reduction Network (NRNet), whose architecture resembles a residual network variant of DnCNN (B. Zhang et al., 2017);
3. The denoising network outputs a noise map (rather than a directly denoised image — residual learning approach) to minimize quantization error;
4. The hardware ISP uses the noise map as a prior (noise prior) to inform subsequent ABF (Adaptive Bayer Filter) and NNF (Noise Noise Filter) parameter adjustments.

The key advantage of this scheme over pure software RAW denoising: **latency increases by only approximately 8 ms** (NPU inference time), without blocking the main imaging pipeline, fitting comfortably within the real-time 4K video frame budget (60 fps = 16.7 ms/frame).

### 5.4 Nightography Night Mode Pipeline

Samsung's **Nightography** (mass-produced from Galaxy S22 onward) complete night photography pipeline (as implemented in the S24 Ultra):

```
Stage 1: Capture Strategy
  ├── Automatic frame count decision: 12 frames at ISO 6400, 24 frames at ISO 12800
  ├── Frame interval: 1/15 s (minimum), paired with EIS (electronic stabilization)
  └── HP2 sensor: 16-in-1 binning → 12.5 MP, equivalent 2.4 µm large pixel

Stage 2: Multi-frame Alignment
  ├── Optical flow estimation: EfficientDet-based motion vector network
  ├── Alignment accuracy: sub-pixel level (1/4 pixel)
  └── Motion mask: removes moving regions to prevent ghosting

Stage 3: Multi-frame Fusion
  ├── Frequency-domain weighted merge
  ├── Reference frame: Frame 1 (lowest latency)
  └── Weight function: σ²_shot → frequency domain noise power spectral density

Stage 4: Post-processing Output
  ├── 50 MP demosaic (Remosaic after 4-in-1 binning)
  ├── AWB + CCM (night-specific color temperature model)
  ├── HDR tone mapping (LOFIC-assisted)
  └── Final output: 12.5 MP (default) or 50 MP (Pro mode)
```

### 5.5 Video Capabilities

Galaxy S24 Ultra video specifications (based on HP2 + Snapdragon 8 Gen 3):

| Specification | Parameter |
|---|---|
| Maximum resolution | 8K @ 30fps (H.265/HEVC), full main camera field of view |
| High frame rate | 4K @ 120fps, HDR10+ supported |
| Log format | LOG Video (professional video mode, retains HDR information for post-production) |
| Slow motion | 1080p @ 240fps, 720p @ 960fps |
| ProVideo | Manual ISO/SS/WB control, optional RAW Video (10-bit HEIF only) |
| Director's View | Simultaneous front + rear multi-camera recording (up to 4 streams), picture-in-picture preview |
| AI denoising (video) | Real-time 4K NR, NPU running continuously, approximately 15% additional power consumption |

---

## §6 Code Examples

Full runnable code is available in *See §6 Code section for runnable examples.*, covering:

### 6.1 Tetra²pixel Quad Bayer Demosaicing Simulation

```python
# Simulating the 200 MP Quad Bayer RAW pattern and 4-in-1 binning for ISOCELL HP2
import numpy as np
import matplotlib.pyplot as plt
from skimage import color

def generate_quad_bayer_raw(height=64, width=64, pattern='RGGB'):
    """
    Generate a simulated Quad Bayer RAW image.
    Quad Bayer: each 2x2 block consists of same-color pixels,
    arranged globally as R R G G / R R G G / G G B B / G G B B.
    """
    raw = np.zeros((height, width), dtype=np.float32)
    # Simulated color light source: R=0.8, G=0.6, B=0.4 (color cast scene)
    signal = {'R': 0.8, 'G': 0.6, 'B': 0.4}
    noise_std = 0.02  # read noise

    for i in range(0, height, 4):
        for j in range(0, width, 4):
            # Quad Bayer 4x4 super-block: R R G G / R R G G / G G B B / G G B B
            raw[i:i+2, j:j+2] = signal['R'] + np.random.normal(0, noise_std, (2,2))
            raw[i:i+2, j+2:j+4] = signal['G'] + np.random.normal(0, noise_std, (2,2))
            raw[i+2:i+4, j:j+2] = signal['G'] + np.random.normal(0, noise_std, (2,2))
            raw[i+2:i+4, j+2:j+4] = signal['B'] + np.random.normal(0, noise_std, (2,2))
    return np.clip(raw, 0, 1)

def quad_bayer_4to1_binning(raw):
    """
    4-in-1 pixel binning: average each 2x2 same-color block in Quad Bayer.
    200 MP → 50 MP equivalent transformation.
    """
    H, W = raw.shape
    binned = np.zeros((H//2, W//2), dtype=np.float32)
    for i in range(0, H, 2):
        for j in range(0, W, 2):
            binned[i//2, j//2] = raw[i:i+2, j:j+2].mean()
    return binned

def remosaic_quad_to_standard_bayer(raw_quad):
    """
    Remosaic: Quad Bayer → Standard Bayer.
    For each 2x2 same-color block, select the top-left pixel as the
    standard Bayer pixel (simplified version).
    An actual implementation requires gradient-weighted interpolation.
    """
    H, W = raw_quad.shape
    raw_bayer = raw_quad[::2, ::2].copy()  # downsample 2x → standard Bayer spacing
    return raw_bayer

# Compare: binning vs remosaic SNR
raw_quad = generate_quad_bayer_raw(height=256, width=256)
raw_binned = quad_bayer_4to1_binning(raw_quad)  # low-light mode output
raw_remosaic = remosaic_quad_to_standard_bayer(raw_quad)  # high-resolution mode output

print(f"Quad Bayer RAW shape: {raw_quad.shape}")
print(f"4-in-1 Binned shape: {raw_binned.shape} (50MP equivalent)")
print(f"Remosaic output shape: {raw_remosaic.shape} (200MP equivalent)")
```

### 6.2 LOFIC HDR Dual-Path Merge Simulation

```python
def simulate_lofic_hdr(scene_linear, fwc_hcg=5000, fwc_lcg=120000,
                        read_noise_hcg=1.5, read_noise_lcg=6.0,
                        cg_ratio=25.0):
    """
    Simulate LOFIC dual-path single-frame HDR merge.
    Input:  scene_linear — linear luminance scene (0~1, 1 = maximum brightness)
    Output: hdr_output   — merged HDR image (linear domain)
    """
    # Map luminance to electron counts (photon counts)
    photons = scene_linear * fwc_lcg  # maximum input fills the LCG path

    # HCG path (high gain, FD only)
    hcg_electrons = np.minimum(photons, fwc_hcg)
    hcg_noise = np.random.normal(0, read_noise_hcg, photons.shape)
    hcg_signal = hcg_electrons + hcg_noise

    # LCG path (low gain, FD + LC)
    lcg_electrons = photons  # LCG path does not saturate (by design)
    lcg_noise = np.random.normal(0, read_noise_lcg, photons.shape)
    lcg_signal = lcg_electrons + lcg_noise

    # Switching threshold: switch at 85% of HCG saturation level
    threshold = 0.85 * fwc_hcg
    use_hcg = hcg_electrons < threshold

    # HDR merge (normalize to [0,1])
    hdr_output = np.where(
        use_hcg,
        hcg_signal / fwc_hcg,   # HCG path: low-noise shadows
        lcg_signal / fwc_lcg    # LCG path: high-capacity highlights
    )
    return np.clip(hdr_output, 0, 1), use_hcg

# Calculate dynamic range
dr_hcg = 20 * np.log10(fwc_hcg / read_noise_hcg)   # ≈ 70 dB ≈ 11.6 EV
dr_lcg = 20 * np.log10(fwc_lcg / read_noise_hcg)   # ≈ 98 dB ≈ 16.3 EV (LOFIC full range)
print(f"HCG dynamic range: {dr_hcg:.1f} dB ({dr_hcg/6:.1f} EV)")
print(f"LOFIC total dynamic range: {dr_lcg:.1f} dB ({dr_lcg/6:.1f} EV)")
```

The code will visualize a noise comparison between the two LOFIC signal paths, the switching-point distribution map, and the SNR-signal curve (Shannon plot) for different Quad Bayer processing modes, aiding understanding of the image quality trade-offs at each operating point.

---

## §7 Artifacts and Tuning Guidelines

### 7.1 Quad Bayer Remosaic Artifacts

**Symptom:** In 200 MP mode, fine colored textures (e.g., fabric, foliage) exhibit color Moiré patterns, because Quad Bayer's color sampling interval near the Nyquist frequency (one color transition every 4 pixels) causes high-frequency color aliasing.

**Mitigation:** Samsung applies a lightweight color de-Moiré network (running on the NPU) after Remosaic, performing targeted filtering in the frequency band most susceptible to color aliasing at 0.6 µm pixel pitch.

### 7.2 LOFIC Switching Noise

**Symptom:** Near the switching threshold (around the HCG/LCG transition point), adjacent pixels within the same frame may fall onto different paths, causing localized noise discontinuities that manifest as a change in granularity within smooth gradient areas.

**Mitigation:** The switching threshold should be set at 80%–90% of HCG full well (not 100%), so the switch to LCG occurs before HCG is fully saturated. A soft blending region should be applied in the transition zone:

$$V_\text{blend} = (1 - w) \cdot V_\text{HCG} + w \cdot V_\text{LCG}, \quad w = \frac{V_\text{HCG} - \theta_1}{\theta_2 - \theta_1}$$

### 7.3 Nonapixel Color Shift

**Symptom:** After 9-in-1 binning in low-light scenes, the image exhibits a green color cast, because within a 3×3 Nona block the number of G pixels (4 or 5) exceeds R pixels (2) and B pixels (2). A direct summation overweights green.

**Mitigation:** After merging each color channel separately, the normal AWB pipeline must still be executed to re-balance white balance gains; it cannot be skipped.

---

## References

1. **Samsung Semiconductor** (2023). *ISOCELL HP2 White Paper: 200MP Mobile Image Sensor with Tetra²pixel Technology*. Samsung Electronics. https://semiconductor.samsung.com/consumer-storage/isocell/hp2/

2. **Samsung Semiconductor** (2021). *ISOCELL GN2: LOFIC Technology for Single-Frame HDR*. Samsung Electronics White Paper.

3. **Samsung Electronics** (2023). *Galaxy S23 Ultra Nightography Pipeline Technical Overview*. Samsung Developer Blog. https://developer.samsung.com/

4. **DPReview Staff** (2023). Samsung Galaxy S23 Ultra In-Depth Review: Sensor Analysis Section. *DPReview*. https://www.dpreview.com/reviews/samsung-galaxy-s23-ultra

5. **Nakamura, J. (Ed.)** (2006). *Image Sensors and Signal Processing for Digital Still Cameras*. CRC Press. (Chapter 3: CMOS pixel architectures and dual conversion gain.)

6. **Fossum, E. R., & Hondongwa, D. B.** (2014). A review of the pinned photodiode for CIS and related cameras. *IEEE Journal of the Electron Devices Society*, 2(3), 33–43.

7. **Park, S., et al.** (2020). A 64Mpixel CMOS image sensor with 0.7µm pixel size using ISOCELL 2.0 technology. *IEEE ISSCC 2020*, 110–111.

8. **Zhang, K., Zuo, W., Chen, Y., Meng, D., & Zhang, L.** (2017). Beyond a Gaussian denoiser: Residual learning of deep CNN for image denoising. *IEEE TPAMI*, 40(7), 1–15.

---

*Chapter 6 End*

---

## §8 Glossary

**ISOCELL (Inter-pixel Isolation Cell)**
Pixel isolation technology introduced by Samsung in 2013. Physical polymer walls are constructed between adjacent pixels to replace traditional Shallow Trench Isolation (STI), reducing inter-pixel electrical crosstalk from approximately 12% to approximately 6% and increasing Full Well Capacity (FWC) by approximately 30%.

**Full Well Capacity (FWC)**
The maximum number of electrons (unit: e⁻) a pixel photodiode can hold before saturating. It is the key parameter determining the upper limit of pixel dynamic range. The larger the FWC, the less likely the pixel saturates under bright light and the wider the single-frame dynamic range. Typical values: 3,000–6,000 e⁻ for a 0.6 µm pixel; equivalent merged pixels at 2.4 µm can exceed 80,000 e⁻.

**Dual Pixel PDAF**
Each imaging pixel is split into a left-half (Left PD) and right-half (Right PD) sub-photodiode. The phase difference between the two sub-pixel signals is used to estimate focus direction and defocus magnitude. The greatest advantage is that 100% of pixels have phase detection capability, yielding extremely fast AF (approximately 0.03 s on the Galaxy S7) with excellent low-light performance. Summing the two sub-pixel signals after focus measurement incurs no sensitivity penalty.

**Nonapixel (9-in-1 pixel binning)**
Samsung's technology for merging 3×3 = 9 adjacent pixels into a single super-pixel, with a SNR gain of √9 = 3× (approximately +9.5 dB) and a 9× increase in effective pixel area. On the ISOCELL HMX (108 MP), the merged output is 12 MP, equivalent to a 2.4 µm large pixel, dramatically improving low-light image quality.

**Tetra²pixel (4-in-1 pixel binning)**
Samsung's technology for merging 2×2 = 4 pixels, applied to the ISOCELL HP2 (200 MP). The merged output is 50 MP (equivalent 1.2 µm) or, with further 16-in-1 binning, 12.5 MP (equivalent 2.4 µm). Uses Quad Bayer CFA layout, requiring a dedicated Remosaic step to convert Quad Bayer RAW to standard Bayer RAW.

**LOFIC (Lateral Overflow Integration Capacitor)**
A pixel architecture technology mass-produced by Samsung on the ISOCELL GN2 (2021). A large-capacity lateral capacitor (LC, approximately 25× the FD capacity) is added alongside the standard floating diffusion node (FD), enabling single-frame HDR dual-path readout: a high-gain path (shadows, low noise) and a low-gain path (highlights, high capacity). This raises pixel dynamic range from approximately 10 EV to approximately 13–14 EV, with no motion ghosting from multi-frame HDR.

**Quad Bayer**
CFA layout used by pixel-binning sensors. Each single-color pixel in traditional Bayer is replaced by a 2×2 (or 3×3) block of same-color pixels, so that pixel binning does not cross color channels. The trade-off is that full-resolution mode requires a Remosaic pre-processing step before outputting standard Bayer RAW, and high-frequency color textures are at risk of aliasing.
