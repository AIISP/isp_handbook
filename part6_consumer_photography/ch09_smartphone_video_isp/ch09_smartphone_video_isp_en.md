# Part 6, Chapter 09: Smartphone Video ISP — Log Mode, 8K Pipeline, and Cinematic Processing

> **Position:** This chapter systematically analyzes the engineering challenges and cinematic shooting capabilities of smartphone video ISP.
> **Prerequisites:** Vol.2 Ch.19 (HDR Display Signal Chain), Vol.2 Ch.21 (EIS/OIS), Vol.6 Ch.1 (Consumer Photography Evolution)
> **Audience:** Algorithm engineers, video engineers, product managers

---

## §1 Video ISP Fundamentals: Fundamental Differences from Still Photography

### 1.1 The Core Tension Between Still and Video ISP

Smartphones share the same sensor and ISP hardware for still photography and video, yet face radically different engineering constraints. Understanding the difference is the logical starting point for building a video ISP system.

**Temporal consistency** is the most fundamental constraint in video ISP. In still photography, each frame can be independently optimized — AWB can jump frame-to-frame, AE can be aggressively adjusted, and denoising can be done offline. But video is a continuous frame stream; any parameter discontinuity is perceived by the human eye as "flicker" or "jump cut." Video 3A (AF/AE/AWB) must respond to scene changes as a smooth curve rather than as a staircase:

$$
P_t = \alpha \cdot P_{t-1} + (1 - \alpha) \cdot P_{\text{target},t}
$$

where $P_t$ is the current frame's parameter (gain, color temperature correction matrix, etc.), $\alpha$ is the smoothing coefficient (typically 0.8–0.95), and $P_{\text{target},t}$ is the computed target value for the current frame.

**Real-time constraint** is the second core tension. 30 fps requires processing each frame within 33 ms; 60 fps requires 16.7 ms; 120 fps only 8.3 ms. Unlike still photo mode, which can sustain hundreds of milliseconds of multi-frame processing (HDR merging, Deep Fusion), video ISP must complete all processing within the single-frame time budget. This strictly constrains algorithm complexity to within the hardware pipeline's throughput capacity.

**Audio-video synchronization (A/V Sync)** is a problem that algorithm engineers easily overlook but that is critically important to product experience. Video frame timestamps must be strictly aligned with audio sample timestamps; a misalignment exceeding 45 ms is perceptible as "lip sync drift." ISP processing latency, video encoder latency, and audio buffer latency must all be managed at the system level with timestamp coordination (e.g., Android MediaSync API).

### 1.2 Frame Rate Selection and Scene Matching

Different frame rates have fundamental differences in motion perception and data volume:

| Frame rate | Use | Motion shutter | Data characteristics |
|------------|-----|----------------|---------------------|
| 24 fps | Cinematic feel, international film standard | 1/48 s (180° shutter rule) | Natural motion blur, most "cinematic" |
| 30 fps | Global mainstream video standard (NTSC system) | 1/60 s | Balanced fluidity and natural feel |
| 60 fps | Smooth everyday recording, esports streaming | 1/120 s | Noticeably smoother, less motion blur |
| 120 fps | Slow-motion footage (4× slow playback) | 1/240 s | Reduced light collection, lower SNR |
| 240 fps | Extreme slow-motion (8× slow playback) | 1/480 s | Heavy noise; higher ISO needed for compensation |
| 4K120fps | Flagship spec (supported since Snapdragon 8 Gen 2) | 1/240 s | ISP bandwidth 4× that of 4K30 |

**The "cinematic feel" of 24 fps** does not originate from an innate human preference, but from a historical legacy standard combined with a specific amount of motion blur. The 180° shutter rule (shutter speed = 1/(2 × frame rate)) at 24 fps yields an exposure time of approximately 1/48 s, producing a specific quantity of motion blur on moving subjects that closely matches audiences' long-established "film-watching experience." One key element of smartphone Cinema Mode (such as iPhone's Cinematic Mode) is accurately simulating the motion blur feel of a 1/48 s shutter in video.

**4K120fps engineering challenge:** Qualcomm's Snapdragon 8 Gen 2 Spectra ISP first supported 4K120fps output in 2022, but at the cost of approximately 4× the internal ISP bandwidth of 4K30fps (~200 Gbps internal bus). Qualcomm achieved this specification via a heterogeneous ISP (Hexagon NPU co-processing), but on flagship phones 4K120fps recording time is typically limited to 3–5 minutes in practice to avoid thermal throttling.

### 1.3 Bit Depth and Color Space Selection

Video bit depth directly determines the number of recordable tonal levels and coding compression loss:

$$
\text{Tonal levels} = 2^{\text{bit\_depth}}, \quad 8\text{-bit}=256\ \text{levels}, \quad 10\text{-bit}=1024\ \text{levels}
$$

| Specification | Bit depth | Codec | Color space | Typical use |
|---|---|---|---|---|
| Standard video | 8-bit | H.264/AVC | sRGB/BT.709 | Social media, everyday recording |
| HDR video | 10-bit | H.265/HEVC | BT.2020 + HLG/PQ | HDR displays, professional distribution |
| Apple ProRes | 10-bit | ProRes 422 LT | BT.709 or Log | Professional post-production, high bit rate |
| Apple ProRes RAW | 12-bit | ProRes RAW | Linear RAW | Professional filmmaking |
| Log format (Apple/Sony) | 10-bit | H.265 or ProRes | S-Log3/Apple Log | Color grading post-production |

**The fundamental difference between BT.709 and BT.2020:** BT.709 is the SDR-era standard; its color gamut covers approximately 35.9% of the human visible gamut (CIE 1931 chromaticity diagram area ratio). BT.2020 is the HDR/UHD standard; its gamut covers approximately 75.8%, capable of representing richer saturated colors (especially at the green and red ends). But BT.2020's gamut is only meaningful on a display that supports it — on a standard smartphone screen, colors outside the display's gamut are mapped (gamut mapping) to the displayable range.

---

## §2 Log Video Profiles: Maximizing Sensor Information Retention

### 2.1 Why Log Format Is Needed

A camera sensor's photoelectric response is linear: the number of incident photons is proportional to the output electrical signal. But the human eye's perception of luminance is logarithmic (Weber-Fechner law), and its dynamic range is limited — a high-end smartphone sensor can record 14 stops of dynamic range, while standard 8-bit video encoding can accommodate only approximately 8 stops.

**The direct problem:** if linear sensor data is encoded directly into 8-bit H.264, highlight detail is lost due to overflow ("clipped white"), and shadow detail is lost due to insufficient quantization. Log format compresses the 14-stop dynamic range into the 10-bit encoding space through a compression curve. The trade-off is that the image looks flat and gray — but the information is fully preserved, ready for post-production color grading.

**Core philosophy:** Log recording is essentially "**capture the maximum information at shooting time; customize the appearance at rendering time.**" This is the same philosophy as RAW development in the film era.

### 2.2 S-Log3: Sony's 14-Stop Compression Scheme

Sony's S-Log3 is a widely used Log format in professional cinematography, first appearing in the Sony VENICE cinema camera and later introduced into Xperia flagship smartphones.

**S-Log3 encoding formula:**

$$
L_{\text{S-Log3}} = \frac{420 + 261.5 \cdot \log_{10}\!\left(\dfrac{t + 0.01}{0.18 + 0.01}\right)}{1023}
$$

where:
- $t$ is the scene luminance ratio relative to an 18% gray card (scene luminance ratio, i.e., exposure factor)
- 420 in the numerator is the 10-bit code value position for 18% gray (approximately 0.41 × 1023)
- 261.5 is the gain coefficient controlling the curve slope
- Denominator 1023 normalizes to the [0, 1] range (but the practical legal range is approximately 0.09–0.93, with headroom at top and bottom)

**Encoding domain verification:**
- $t = 0.18$ (18% gray): $L \approx 420/1023 \approx 0.41$
- $t = 1.0$ (100% reflectance white card): $L \approx 0.59$
- $t = 16$ (approximately 6.5 stops above 18% gray): $L \approx 0.88$

This means S-Log3 maps 14 stops of dynamic range into the 10-bit code value range of approximately 0.09–0.93. The darkest recordable level is approximately -4 stops below 18% gray; the brightest is approximately +10 stops above.

**S-Log3 vs. linear comparison:** at the same scene luminance, S-Log3 compresses the encoded luminance toward the midtones so highlights do not overflow, but a LUT (Look-Up Table) is required to restore normal viewing appearance.

### 2.3 Apple Log: Apple's Neural Engine Co-Design

Apple introduced Apple Log with the iPhone 15 Pro in 2023 — Apple's first Log format targeting professional post-production.

**Apple Log technical specifications:**
- Dynamic range: relative to 18% gray, covers -15 EV to +7 EV (22 stops theoretical; approximately 14 stops practical, limited by the sensor)
- Encoding format: Apple ProRes only (H.265 not supported)
- Bit depth: 10-bit
- Color space: Apple Log color space (close to BT.2020, but with a proprietary tone curve)

**Apple Log curve characteristics:** Compared to S-Log3, Apple Log maintains a smoother slope in dark areas (avoiding over-amplification of shadow noise), and is deeply co-designed with Apple's Neural Engine — when recording in Log, the ISP outputs Log data while the Neural Engine simultaneously generates a real-time Rec.709 preview LUT, letting users monitor an approximation of the final result while recording in Log.

**Apple Log encoding function (simplified form):**

$$
L_{\text{Apple}} = \begin{cases}
\frac{c_1 \cdot t}{\ln(10)} & t \leq t_{\text{cut}} \\
c_2 \cdot \log_{10}(c_3 \cdot t + c_4) + c_5 & t > t_{\text{cut}}
\end{cases}
$$

where $c_1$–$c_5$ are Apple's proprietary coefficients (published in Apple Developer documentation) and the switchover point $t_{\text{cut}}$ corresponds to approximately -15 EV. The piecewise design ensures linear precision in shadow encoding (avoiding the sharp nonlinearity of the log function near zero).

### 2.4 Canon C-Log3 and Color Philosophy Comparison

Canon's C-Log3 is primarily found in professional cinema cameras (EOS C70/C300), but provides useful context for understanding Log format design philosophy:

| Feature | S-Log3 (Sony) | Apple Log | C-Log3 (Canon) |
|---------|--------------|-----------|----------------|
| 18% gray code value | 420/1023 ≈ 41% | ~46% | 400/1023 ≈ 39% |
| Dynamic range | ~14 stops | ~14 stops (measured) | ~14 stops |
| Shadow slope | Steeper; shadow detail retained | Gentler; shadows cleaner | Medium |
| Companion color space | S-Gamut3.Cine | Apple Log CS | Cinema Gamut |
| Post software support | DaVinci/Premiere/FCPX | FCPX/DaVinci | DaVinci/Premiere |

### 2.5 Log Color Grading Workflow

The standard post-production workflow for Log video:

```
Log recording → Import into DaVinci Resolve / Final Cut Pro X
              → Apply technical LUT (converts Log to linear or Rec.709 reference)
              → Creative color grading (hue, saturation, contrast)
              → Export Rec.709 / BT.2020 HDR
```

**The essence of a LUT (Look-Up Table)** is a 3D color mapping table that records, for each sampled point in the input color space (e.g., the R, G, B channels of Apple Log), the corresponding output color (e.g., Rec.709 R, G, B). A typical LUT has resolution 33×33×33, using trilinear interpolation for intermediate values.

Apple provides an official "Apple Log to Rec.709" technical LUT (downloadable from Apple Developer). Professional colorists layer creative LUTs on top of this (e.g., "cinematic orange-teal," "Japanese low-saturation") to achieve the desired look.

---

## §3 8K Video Pipeline: Bandwidth, Power, and Thermal Management

### 3.1 Pixel Throughput Demand for 8K Video

8K resolution is defined as 7680×4320 pixels; the pixel count per frame is:

$$
N_{\text{8K}} = 7680 \times 4320 = 33{,}177{,}600 \approx 33.2\ \text{megapixels/frame}
$$

At 30 fps, the ISP must process pixels at a rate of:

$$
\dot{N}_{\text{8K30}} = 33{,}177{,}600 \times 30 \approx 10^9\ \text{pixels/s} = 1\ \text{Gpixel/s}
$$

For comparison, 4K30fps requires only approximately 24.9 Mpixels/s (249 Mpixels/s); 8K30fps is approximately 4× that. Considering ISP internal multi-pass processing (RAW input → denoise → demosaic → color transform → output), the actual internal bandwidth requirement is higher:

$$
\text{ISP internal bandwidth} \approx N_{\text{pixel}} \times f_{\text{fps}} \times B_{\text{internal}} \times N_{\text{pass}}
$$

where $B_{\text{internal}}$ is internal bit depth (typically 16–20 bits) and $N_{\text{pass}}$ is the number of processing passes (typically 3–5). The estimated ISP internal bandwidth for 8K30fps is approximately 50 Gbps — more than 8× that of 4K30fps (approximately 6 Gbps).

### 3.2 Samsung Galaxy S21 Ultra: Pioneering Consumer 8K

Samsung's **Galaxy S21 Ultra** (released 2021) was the first consumer smartphone to mass-produce 8K video recording, powered by Samsung's Exynos 2100 / Snapdragon 888 platform.

**S21 Ultra 8K video technical parameters:**
- Resolution: 7680×4320 (8K UHD)
- Frame rate: up to 30 fps
- Codec: H.265 (HEVC), approximately 80 Mbps bit rate
- Sensor: HP3 108 MP ISOCELL (9-in-1 pixel binning for video)
- Practical limit: 8K recording triggers thermal protection and automatically drops to 4K after approximately 5 minutes

**Pixel binning strategy:** In 8K mode, the sensor does not read out all pixels and then downsample. Instead, it uses 9-in-1 binning (3×3 pixel merge readout), reducing readout data volume while improving sensitivity (SNR improvement approximately √9 = 3×, approximately +9.5 dB). Actual output pixel count = 108 MP / 9 = 12 MP, then interpolated up to 33 MP (8K) by the ISP. This means that the actual resolution detail of 8K video is not fully equivalent to 33 MP — it depends in part on interpolation quality.

### 3.3 Thermal Power: The Engineering Bottleneck of 8K Video

The thermal power consumption of 8K video recording comes from three main components:

$$
P_{\text{total}} = P_{\text{sensor}} + P_{\text{ISP}} + P_{\text{encoder}}
$$

| Module | Typical 4K30fps power | Estimated 8K30fps power | Multiplier |
|--------|----------------------|------------------------|-----------|
| Image sensor (readout) | ~300 mW | ~800 mW | 2.7× |
| ISP processing | ~500 mW | ~1800 mW | 3.6× |
| H.265 encoder | ~200 mW | ~600 mW | 3.0× |
| Total | ~1.0 W | ~3.2 W | ~3.2× |

This explains why 8K recording drains the battery approximately 3× faster than 4K, and why thermal throttling is reached before the battery runs out. The vapor chamber cooling in modern flagship phones (area approximately 5–8 cm², cooling capacity approximately 5 W) approaches its limit under 8K workloads.

**Crop factor issue:** Some phones in 8K mode do not use the full sensor readout area; instead they crop the center region to reduce readout data volume and transfer bandwidth. For example, one flagship uses an equivalent 26 mm main camera in 4K mode, but in 8K mode the crop produces an equivalent approximately 32 mm — the field of view narrows by approximately 19%. This is an engineering trade-off easily overlooked in product specifications.

---

## §4 Cinematic Features: Learning from Professional Cinema Cameras

### 4.1 ProRes Format: Apple's Professional Commitment

Apple ProRes is an intra-frame codec format designed by Apple for professional post-production. Unlike H.264/H.265 inter-frame prediction, each frame is independently encoded, making it convenient for post-production editing and color processing.

**ProRes series specifications:**

| Format | Bit depth | Chroma sampling | Bit rate (4K30fps) | File size per minute |
|--------|-----------|----------------|-------------------|---------------------|
| ProRes 422 LT | 10-bit | 4:2:2 | ~330 Mbps | ~2.5 GB |
| ProRes 422 | 10-bit | 4:2:2 | ~660 Mbps | ~5 GB |
| ProRes 422 HQ | 10-bit | 4:2:2 | ~1 Gbps | ~7.5 GB |
| ProRes 4444 | 12-bit | 4:4:4 | ~1.6 Gbps | ~12 GB |
| ProRes 4444 XQ | 12-bit | 4:4:4 | ~2.2 Gbps | ~16.5 GB |

The iPhone 13 Pro was the first to support ProRes recording (4K30fps, ProRes 422 LT, approximately 1.7 GB/min). From iPhone 14 Pro onward, ProRes 422 is supported (4K30fps, approximately 3.4 GB/min). Storage speed requirement: ProRes 422 requires write speeds ≥ 800 MB/s, so it only works with external storage equipped with NVMe SSD (via Lightning/USB-C) or internal storage of 256 GB or above.

**Impact of chroma subsampling:** H.264/H.265 typically uses 4:2:0 chroma subsampling (chroma information downsampled 2× both horizontally and vertically). ProRes 422 uses 4:2:2 (chroma downsampled horizontally only). ProRes 4444 uses 4:4:4 (no downsampling). In scenarios requiring accurate chroma information such as green-screen (chroma key) compositing, the difference between 4:2:2 and 4:2:0 has a significant impact on matte edge quality.

### 4.2 Anamorphic Mode

Anamorphic lenses were originally designed in the 1950s (CinemaScope). Elliptical lens elements horizontally compress the wide-screen image for recording onto standard film; the image is horizontally de-squeezed (desqueezed) during playback to restore the full aspect ratio.

**Smartphone Anamorphic mode (iPhone + Moment lens):**
- Moment 1.33× Anamorphic lens: horizontally compresses the image by 1.33×
- ISP or software real-time desqueeze: restores the compressed image from 16:9 base to approximately 2.39:1 (typical cinematic widescreen ratio)
- Elliptical bokeh: because of the elliptical lens distortion, out-of-focus point light sources are horizontal ellipses rather than circles — the signature visual element of "cinematic feel"
- Horizontal lens flare: the anamorphic element produces characteristic horizontal blue streak flares on highlights

**Mathematical relationship:** If the sensor outputs 4032×3024 (4:3), after 1.33× anamorphic compression the recorded content corresponds to an equivalent width of 4032×1.33 = 5362 pixels. After desqueeze the output is 5362×3024, aspect ratio approximately 1.77→2.35:1. In practice, smartphones typically output an image cropped to 2.39:1 (3840×1607 or a similar resolution) and retain the original compressed file for complete post-production desqueeze.

### 4.3 Dolby Vision Video: Per-Frame HDR Metadata

Dolby Vision is Dolby's HDR format standard. Unlike HDR10's static metadata, Dolby Vision supports **per-frame (or per-scene) dynamic metadata**, allowing the display to adjust tone mapping parameters in real time.

**Dolby Vision recording from iPhone 12 onward:**
- Internal processing: ISP processes 12-bit HDR data while simultaneously generating two layers: a Base Layer (Rec.709-compatible) and an Enhancement Layer (Dolby Vision dynamic metadata)
- Metadata content: per-frame recording of maximum content light level (MaxCLL), maximum frame-average light level (MaxFALL), and tone mapping curve coefficients
- Display adaptation: Dolby Vision playback devices (iPhone / Apple TV / compatible TVs) read the metadata and apply the optimal tone mapping for the current display's capabilities — the same video automatically presents a different but individually optimal HDR rendering on an iPhone 14 Pro (2000 nit peak) vs. an ordinary TV (400 nit)

**Dolby Vision Profile 8** (used by iPhone) supports 10-bit encoding (Profile 8.4) and is the most common Dolby Vision configuration on smartphones.

### 4.4 Focus Breathing Compensation

Focus breathing is a physical defect of traditional zoom/prime lenses: adjusting focus distance causes slight mechanical displacement of the lens group, subtly changing the equivalent focal length and therefore the field of view — the image appears to slightly "zoom in/out." In video, this produces an uncomfortable "jump" during focus transitions.

**Electronic Focus Breathing Compensation:**
- Detection: the AE/AF controller reads real-time lens group position feedback
- Compensation: when the lens group moves, the ISP applies a counter micro-zoom (electronic zoom) to cancel the field-of-view change
- Precision requirement: compensation precision typically needs to be within ±0.1% field-of-view change; otherwise the compensation itself generates a visible zoom effect

Sony Xperia 5 IV and other professionally video-oriented devices pioneered this feature; iPhone 16 Pro integrates similar compensation in Cinematic Mode.

---

## §5 Stabilization and Its Interaction with Video ISP Design

### 5.1 EIS Crop and Effective Resolution

Electronic Image Stabilization (EIS) works by retaining a "stabilization buffer margin" within the sensor readout area, compensating for camera motion by selecting different crop centers within the larger frame. The crop ratio determines the maximum angular displacement EIS can compensate:

$$
\text{Max compensable angle} \approx \arctan\!\left(\frac{W_{\text{sensor}} - W_{\text{output}}}{2 \cdot f_{\text{equiv}}}\right)
$$

where $W_{\text{sensor}}$ is the sensor readout width, $W_{\text{output}}$ is the output width, and $f_{\text{equiv}}$ is the equivalent focal length.

**iPhone 14 Action Mode example:**
- Sensor readout: 4K (3840 pixels wide, equivalent 26 mm main camera)
- Output: 2.8K (~2800 pixels wide)
- EIS crop ratio: 2800/3840 ≈ 0.73, retaining 73% of width
- Maximum compensable angular displacement: approximately ±8° (sufficient for vigorous motion such as running and cycling)
- Trade-off: equivalent focal length lengthens by approximately 1/0.73 = 1.37×, i.e., 26 mm becomes approximately 36 mm

**4K60fps + Cinematic Mode (iPhone 13 Pro):**
- Sensor: full 4K readout
- Cinematic Mode requires a depth-of-field processing buffer: crops to approximately 3.7K effective output, then further EIS crop is applied on top

### 5.2 OIS + EIS Fusion Strategy

OIS (Optical Image Stabilization) and EIS have complementary frequency-domain characteristics:

| Stabilization type | Compensation band | Compensation magnitude | Latency |
|--------------------|--------------------|----------------------|---------|
| OIS | DC ~ 20 Hz (high-frequency hand tremor) | ±2–3° | Extremely low (<1 ms, mechanical response) |
| EIS (gyroscope-assisted) | DC ~ 60 Hz | ±5–10° (depending on crop) | <1 frame (~8–16 ms, gyroscope sampling) |
| EIS (optical flow-assisted) | 0.1 ~ 10 Hz | Smaller (depends on image content) | 1–3 frames |

The optimal strategy is **OIS handles high-frequency content (hand tremor, heartbeat at approximately 5–10 Hz) and EIS handles low-frequency large displacements (walking/running at approximately 1–3 Hz motion)**. Gyroscope-assisted EIS (Gyro-EIS) uses a high-sample-rate gyroscope (typically ≥ 1 kHz) to precisely measure camera angular velocity, pre-computing the required crop displacement per frame, with latency less than one frame period. Pure optical flow EIS requires the previous frame as reference, yielding 1–2 frames of latency, but provides better handling of pure translational motion (e.g., lateral vibration from riding in a vehicle).

iPhone 16 Pro's Cinematic Stabilization employs three-level fusion: OIS (1000 Hz) + Gyro-EIS (500 Hz) + optical flow EIS (30 fps), achieving professional cinema gimbal-level stability.

### 5.3 Video Stabilization Evaluation Metrics

| Metric | Definition | Typical target |
|--------|------------|----------------|
| Residual Motion | Mean inter-frame displacement after stabilization | < 0.1% of frame width per frame |
| Crop Ratio | Output area / sensor area | ≥ 70% (Action Mode may drop to 55%) |
| Latency | Time from motion input to corrected output | < 33 ms (1 frame) |
| Horizon Drift | Accumulated rotational error over long recording | < 0.1°/min |

---

## §6 Code Implementation: Log Video Simulation and LUT Application

The companion Jupyter Notebook (*See §6 Code section for runnable examples.*) includes the following implementation modules:

### 6.1 Synthetic HDR Scene and Log Encoding Simulation

```python
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import RegularGridInterpolator

def slog3_encode(t):
    """
    Sony S-Log3 encoding function.
    t: scene luminance ratio (relative to 18% gray, linear value)
    Returns: 10-bit normalized code value [0, 1]
    """
    # Clamp to avoid log(0)
    t = np.maximum(t, 1e-6)
    L = (420.0 + 261.5 * np.log10((t + 0.01) / (0.18 + 0.01))) / 1023.0
    return np.clip(L, 0, 1)

def slog3_decode(L):
    """S-Log3 decoding (inverse transform)"""
    L_code = L * 1023.0
    t = 10 ** ((L_code - 420.0) / 261.5) * (0.18 + 0.01) - 0.01
    return np.maximum(t, 0)

def apple_log_encode(t, cutpoint=0.01):
    """
    Apple Log simplified encoding function (based on published Apple Developer documentation parameters)
    """
    # Apple Log parameters (approximate published values)
    c1, c2, c3, c4, c5 = 0.2098, 0.3906, 0.2, 0.01, 0.399
    t = np.maximum(t, 1e-7)
    L = np.where(
        t <= cutpoint,
        c1 * t / np.log(10),
        c2 * np.log10(c3 * t + c4) + c5
    )
    return np.clip(L, 0, 1)

# Generate a synthetic HDR scene (dynamic range approximately 14 stops)
ev_range = np.linspace(-4, 10, 1024)  # EV range relative to 18% gray
luminance_linear = 0.18 * (2 ** ev_range)  # linear luminance

# Encoding comparison
L_slog3 = slog3_encode(luminance_linear)
L_apple = apple_log_encode(luminance_linear)
L_gamma22 = np.clip(luminance_linear ** (1/2.2), 0, 1)  # standard sRGB approximation

plt.figure(figsize=(10, 6))
plt.plot(ev_range, L_slog3, label='S-Log3', color='#E8A020')
plt.plot(ev_range, L_apple, label='Apple Log', color='#555555')
plt.plot(ev_range, L_gamma22, label='sRGB Gamma 2.2', color='#3070C0', linestyle='--')
plt.axvline(0, color='gray', linestyle=':', alpha=0.5, label='18% grey (EV=0)')
plt.xlabel('Scene EV (relative to 18% gray)')
plt.ylabel('Encoded code value (normalized)')
plt.title('Log Format vs. sRGB Encoding Curve Comparison')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
```

### 6.2 3D LUT Construction and Application

```python
def apply_3d_lut(img_log, lut_3d, lut_size=33):
    """
    Apply a 3D LUT for color space conversion.
    img_log: input Log image [H, W, 3], values in [0, 1]
    lut_3d:  3D LUT array [lut_size, lut_size, lut_size, 3]
    """
    H, W, _ = img_log.shape
    axes = [np.linspace(0, 1, lut_size)] * 3

    # Build an interpolator for each channel
    lut_out = np.zeros_like(img_log)
    for c in range(3):
        interp = RegularGridInterpolator(
            axes, lut_3d[..., c], method='linear'
        )
        pts = img_log.reshape(-1, 3)
        lut_out[..., c] = interp(pts).reshape(H, W)

    return np.clip(lut_out, 0, 1)

def generate_identity_lut(size=33):
    """Generate an identity LUT (no transformation)."""
    grid = np.linspace(0, 1, size)
    R, G, B = np.meshgrid(grid, grid, grid, indexing='ij')
    lut = np.stack([R, G, B], axis=-1)
    return lut

def slog3_to_rec709_lut(size=33):
    """
    Generate an S-Log3 → Rec.709 conversion LUT.
    (Simplified version; a production LUT requires rigorous color science correction.)
    """
    grid = np.linspace(0, 1, size)
    R, G, B = np.meshgrid(grid, grid, grid, indexing='ij')
    lut_input = np.stack([R, G, B], axis=-1)  # [size, size, size, 3]

    # Decode S-Log3 → linear scene luminance
    lut_linear = slog3_decode(lut_input)

    # Linear → Rec.709 gamma (simplified as gamma 2.2)
    lut_709 = np.clip(lut_linear ** (1/2.2), 0, 1)

    return lut_709
```

### 6.3 Inter-Frame Optical Flow Analysis (Stabilization Evaluation)

```python
import cv2

def analyze_frame_stability(video_frames):
    """
    Analyze the stability of consecutive frames using optical flow.
    video_frames: list of numpy arrays [H, W, 3]
    Returns: array of residual motion magnitudes (pixels) per frame
    """
    motions = []
    prev_gray = cv2.cvtColor(video_frames[0], cv2.COLOR_RGB2GRAY)

    for frame in video_frames[1:]:
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

        # Sparse optical flow (Lucas-Kanade)
        corners = cv2.goodFeaturesToTrack(
            prev_gray, maxCorners=100, qualityLevel=0.01, minDistance=10
        )
        if corners is not None:
            next_pts, status, _ = cv2.calcOpticalFlowPyrLK(
                prev_gray, curr_gray, corners, None
            )
            good_prev = corners[status == 1]
            good_next = next_pts[status == 1]

            # Compute mean inter-frame displacement (pixels)
            displacement = np.linalg.norm(
                good_next - good_prev, axis=1
            ).mean()
            motions.append(displacement)
        else:
            motions.append(0.0)

        prev_gray = curr_gray

    return np.array(motions)
```

The full Notebook includes: (1) synthesize a 14-stop HDR test scene and encode it as S-Log3/Apple Log/sRGB, comparing the histograms of all three; (2) build a 33³ LUT and apply it to Log images, showing before/after color grading comparisons; (3) run optical flow analysis on a simulated hand-held shaky video sequence and quantitatively evaluate EIS stabilization effectiveness; (4) Dolby Vision metadata structure parsing example.

---

## §7 Engineering Practice and Tuning Guidelines

### 7.1 Video 3A Smoothing Control Parameters

The video AE convergence time constant is a critical tuning parameter for product experience:

$$
\tau = \frac{-\Delta t}{\ln(\alpha)}
$$

where $\Delta t$ is the inter-frame time interval (1/fps) and $\alpha$ is the smoothing coefficient. For example, at 30 fps with $\alpha = 0.9$, $\tau \approx -\frac{1/30}{\ln 0.9} \approx 0.316$ s — meaning after an abrupt scene luminance change, approximately 0.3 s is needed to reach 63% of the new exposure value.

Recommended AE smoothing time constants for different scenarios:
- Indoor steady shooting: τ = 0.3–0.5 s (user does not notice AE adjusting)
- Outdoor brisk walking: τ = 0.15–0.3 s (faster response needed to avoid overexposure when moving into shade)
- Backlit scene rotation: τ = 0.1–0.2 s (too slow causes prolonged underexposure of the face)

### 7.2 Common Video ISP Artifacts and Remedies

| Artifact | Cause | Remedy |
|----------|-------|--------|
| Inter-frame flicker | AWB parameter jump | Increase AWB smoothing coefficient, or lock color temperature when no significant change |
| Jello effect (Rolling Shutter) | CMOS line-by-line readout time offset (~8–16 ms/frame) | Add ISP frame buffer for Rolling Shutter Correction (RSC) |
| Banding noise | AC power 50/60 Hz lighting out of sync with shutter | AE automatically selects 1/100 s (50 Hz) or 1/120 s (60 Hz) shutter |
| Blocking artifacts | H.265 bit rate too low; high-frequency texture compression loss | Raise minimum bit rate floor, or use ProRes |
| Color jump | Color calibration mismatch on multi-camera switching | Interpolate colors between cameras over transition frames (see Vol.1 Ch.10) |

---

## §8 Glossary

| Term | Full name / abbreviation | Explanation |
|------|--------------------------|-------------|
| Log profile | Log Profile | A nonlinear encoding curve that compresses wide dynamic range into a fixed bit depth, retaining maximum sensor information |
| LUT | Look-Up Table | A color mapping table used to map an input color space to an output color space |
| ProRes | Apple ProRes | Apple's intra-frame professional video codec, supporting 10–12 bit at high bit rates |
| S-Log3 | Sony S-Log3 | Sony's Log encoding format, designed to cover approximately 14 stops of dynamic range |
| Apple Log | Apple Log | Apple's Log encoding format, introduced with iPhone 15 Pro, optimized for Neural Engine decoding |
| Dolby Vision | Dolby Vision | Dolby's per-frame HDR metadata format, supporting display-adaptive tone mapping |
| Anamorphic | Anamorphic / Widescreen | Uses elliptical lens elements to compress the horizontal field of view; playback desqueezes to produce a widescreen aspect ratio |
| EIS | Electronic Image Stabilization | Compensates for camera motion by cropping the image buffer |
| Frame rate | Frame Rate / fps | Number of video frames recorded per second; determines motion fluidity and slow-motion capability |
| Rolling Shutter | Rolling Shutter | Jello/skew distortion caused by CMOS line-by-line exposure over time |
| Chroma subsampling | Chroma Subsampling | Spatial downsampling scheme for chroma components, e.g., 4:2:0, 4:2:2, 4:4:4 |
| Gyro-EIS | Gyroscope-assisted EIS | Gyroscope-assisted electronic stabilization; latency less than one frame |

---

## §9 References

1. Apple Inc., "Apple ProRes White Paper" (2022), Apple Developer Documentation. https://developer.apple.com/documentation/avfoundation/apple_prores
2. Sony Corporation, "S-Log3/S-Gamut3 Specification" (2014), Sony Professional. Public technical specification document.
3. Dolby Laboratories, "Dolby Vision for Content Creators" (2023), Dolby Professional. https://professional.dolby.com/
4. ITU-R BT.2020, "Parameter values for ultra-high definition television systems for production and international programme exchange" (2015). ITU standard.
5. ITU-R BT.709, "Parameter values for the HDTV standards for production and international programme exchange" (2015). ITU standard.
6. Qualcomm, "Snapdragon 8 Gen 2 Mobile Platform Specification" (2022). Qualcomm official product specification.
7. Samsung Electronics, "Galaxy S21 Ultra Camera Technical Brief" (2021). Samsung official technical document.
8. SMPTE ST 2084:2014, "High Dynamic Range Electro-Optical Transfer Function of Mastering Reference Displays." SMPTE standard (PQ curve definition).
9. Apple Inc., "WWDC 2023 - Discover log video in your app" (2023). Apple Developer. https://developer.apple.com/videos/play/wwdc2023/
10. Wronski, B. et al., "Handheld Multi-Frame Super-Resolution" (2019). SIGGRAPH 2019. [HDR+ technology foundations, related to temporal processing in video ISP]
