# Part 2, Chapter 16: JPEG, HEIF, and AVIF Image Encoding Pipeline

> **Pipeline position:** Final output stage; converts ISP-processed sRGB to compressed container
> **Prerequisites:** Chapter 26 (CSC & Output)
> **Reader path:** Algorithm Engineers, System Engineers

---

## §1 Theory

### 1.1 JPEG Encoding Pipeline

JPEG (Joint Photographic Experts Group, ISO/IEC 10918-1) remains the most widely used image format in smartphone cameras, despite being standardized in 1992. Its ubiquitous hardware acceleration and universal software support make it the default output format on virtually every mobile device.

**JPEG encoding steps:**

```
sRGB input (8-bit per channel)
        │
        ▼
  Color space conversion:  RGB → YCbCr (BT.601)
        │
        ▼
  Chroma downsampling:  4:4:4 → 4:2:2 or 4:2:0
        │
        ▼
  Block partition:  8×8 pixel blocks
        │
        ▼
  Level shift:  subtract 128 from each sample
        │
        ▼
  2D DCT (Discrete Cosine Transform)
        │
        ▼
  Quantization (divide by quantization matrix Q, round to integer)
        │
        ▼
  Zig-zag scan (reorder 64 DCT coefficients)
        │
        ▼
  Run-length encoding (RLE on AC coefficients)
        │
        ▼
  Huffman entropy coding
        │
        ▼
  JFIF container output (.jpg)
```

---

### 1.2 JPEG DCT and Quantization

**2D Discrete Cosine Transform (DCT-II):**

For an 8×8 block of level-shifted pixel values $f(x, y)$:

$$
F(u, v) = \frac{1}{4} C(u) C(v) \sum_{x=0}^{7} \sum_{y=0}^{7} f(x,y) \cos\!\left[\frac{(2x+1)u\pi}{16}\right] \cos\!\left[\frac{(2y+1)v\pi}{16}\right]
$$

where:

$$
C(u) = \begin{cases} 1/\sqrt{2} & u = 0 \\ 1 & u > 0 \end{cases}
$$

The DCT concentrates energy in low-frequency coefficients.  For natural images, the DC term $F(0,0)$ and the first few AC terms carry most of the signal energy.

**Quantization:**

$$
\hat{F}(u, v) = \text{round}\!\left(\frac{F(u, v)}{Q(u, v)}\right)
$$

where $Q(u, v)$ is the quantization matrix entry at position $(u, v)$.  High-frequency coefficients use larger $Q$ values → coarser quantization → more compression → more quality loss.

**Quality factor mapping:**

The standard JPEG quality factor $Q_f \in [1, 100]$ scales the quantization matrix:

$$
Q_{\text{scale}} = \begin{cases}
\lfloor (50 / Q_f) \cdot 100 \rfloor & Q_f < 50 \\
200 - 2 Q_f & Q_f \geq 50
\end{cases}
$$

$$
Q(u, v) = \text{clip}\!\left(\frac{Q_{\text{base}}(u,v) \cdot Q_{\text{scale}} + 50}{100},\ 1,\ 255\right)
$$

| Quality factor | Visual quality | Typical file size (12 MP) |
|---|---|---|
| 100 | Near lossless (DCT only) | ~8–12 MB |
| 95 | Excellent, reference quality | ~4–6 MB |
| 85 | Good, standard camera output | ~2–3 MB |
| 75 | Acceptable, visible artifacts at close inspection | ~1–1.5 MB |
| 60 | Blocky, strong compression | ~0.5–0.8 MB |
| < 50 | Significant blocking, unacceptable | < 0.4 MB |

---

### 1.3 Chroma Subsampling

Human vision is more sensitive to luma (Y) detail than chroma (Cb, Cr) detail.  JPEG exploits this by subsampling the chroma channels before encoding.

**Standard subsampling modes:**

| Mode | Y:Cb:Cr | Chroma resolution | Quality | File size |
|------|---------|-------------------|---------|-----------|
| 4:4:4 | Full resolution all channels | 100% | Highest | Largest |
| 4:2:2 | Cb and Cr at half horizontal resolution | 50% horizontal | Good | Medium |
| 4:2:0 | Cb and Cr at half horizontal and vertical | 25% | Default for photos | Smallest |

Smartphone cameras almost universally use 4:2:0 chroma subsampling for JPEG.  The quality penalty is small for natural images but visible at sharp color edges (e.g., text on a colored background).

---

### 1.4 HEIF / HEIC

HEIF (High Efficiency Image File Format, ISO/IEC 23008-12) is a container format that wraps HEVC (H.265) image codec.

**Key advantages over JPEG:**

- ~2× better compression at perceptually equivalent quality: HEIF at quality setting ~60 is comparable to JPEG at quality ~85
- Native 10-bit HDR support (JPEG is limited to 8-bit)
- HDR10 and HLG metadata
- Alpha channel support (JPEG does not support alpha)
- Image sequences and animations (like APNG but in a compact format)
- Multi-resolution image stacks (thumbnail + full resolution in one file)
- Depth maps, portrait segmentation masks stored alongside the main image

**Encoding internals:**

HEIF uses the HEVC intra-frame coding mode.  Instead of a block DCT like JPEG, HEVC uses:
- **CTU (Coding Tree Unit):** 64×64 hierarchical partition (vs. JPEG's fixed 8×8)
- **Intra prediction:** predicts each block from neighboring reconstructed blocks before DCT
- **CABAC entropy coding:** context-adaptive arithmetic coder (significantly better than Huffman)
- **4:2:0 chroma subsampling** (default) or **4:4:4** (for better quality)

**Platform support:**
- iOS: default capture format since iOS 11 (iPhone 7, 2017)
- Android: supported in Android 9+ (encoding), Android 10+ (decoding via MediaCodec)
- Windows: support added in Windows 10 April 2018 Update (requires HEVC codec pack)

---

### 1.5 AVIF

AVIF (AV1 Image File Format) uses the AV1 video codec for still image compression.  AV1 is the open-source successor to HEVC developed by the Alliance for Open Media (Google, Netflix, Mozilla, Apple, Amazon, and others).

**Advantages over HEIF:**
- Often 5–20% better compression than HEIF at equal perceptual quality
- Fully open-source and royalty-free
- HDR support (10-bit, 12-bit HDR10, HLG, PQ)
- Wide color gamut (BT.2020)

**Disadvantages:**
- Software encoding is slow: 500 ms to several seconds for a 12 MP image without hardware AV1 encoder
- Hardware AV1 encoders are present in newer SoCs (Snapdragon 8 Gen 3, Apple A17 Pro) but not universal

**Browser/ecosystem support:** Chrome 85+, Firefox 93+, Safari 16+ (macOS/iOS).  Growing but not yet ubiquitous in camera apps.

---

### 1.6 HDR Output Encoding

When the camera captures an HDR scene (see Chapter 27), the output must encode the extended dynamic range.

**P010 format (10-bit YUV 4:2:0):**

P010 stores Y in the high 10 bits of a 16-bit value (little-endian), with Cb/Cr interleaved at half resolution.  It is the standard format for HDR video on Android (`ImageFormat.YCBCR_P010`).

**HDR10 static metadata:**

| Metadata field | Meaning |
|---|---|
| MaxCLL | Maximum content light level (cd/m²): brightest single pixel in content |
| MaxFALL | Maximum frame average light level (cd/m²): average luminance of brightest frame |
| Mastering display primaries | Color gamut of the mastering display |
| MinLuminance / MaxLuminance | Display luminance range |

HDR10 uses the PQ (Perceptual Quantizer / SMPTE ST 2084) electro-optical transfer function (EOTF):

$$
V = \left(\frac{c_1 + c_2 L^{m_1}}{1 + c_3 L^{m_1}}\right)^{m_2}
$$

where $L$ is the normalized linear light level (0 to 1, where 1 = 10,000 cd/m²), and:
$c_1 = 0.8359375$, $c_2 = 18.8515625$, $c_3 = 18.6875$, $m_1 = 0.1593017578$, $m_2 = 78.84375$.

**Dolby Vision Profile 5 (mobile-optimized):**

Single-layer (no backward compatible SDR base layer), BT.2020 color primaries, IPT-PQ color space, 12-bit depth.  Supported on iPhone 12 Pro and later.

---

### 1.7 Android Camera2 API Output Formats

```java
// JPEG capture
CaptureRequest.Builder builder = ...
builder.set(CaptureRequest.JPEG_QUALITY, (byte) 85);
builder.set(CaptureRequest.JPEG_ORIENTATION, 90);
// ImageFormat.JPEG in ImageReader

// HEIF capture (Android 10+)
// ImageFormat.HEIF is not a direct format; use MediaMuxer + HEIC encoder
// Or use ContentResolver with MIME type "image/heif"

// RAW capture
// ImageFormat.RAW_SENSOR: 16-bit per pixel, Bayer pattern, no ISP processing
// ImageFormat.RAW10: 10-bit packed Bayer
// ImageFormat.RAW12: 12-bit packed Bayer

// HDR (P010)
// ImageFormat.YCBCR_P010: 10-bit YUV 4:2:0
```

---

### 1.8 Encoding Latency

| Format | Hardware-accelerated | Software-only |
|---|---|---|
| JPEG (8-bit, 12 MP) | ~5 ms | ~20 ms |
| HEIF/HEIC (12 MP) | ~20 ms (NPU/H.265 HW encoder) | ~100–300 ms |
| AVIF (12 MP) | ~100 ms (HW AV1, when available) | ~500 ms to 2+ seconds |
| RAW DNG write | ~10 ms (DMA write) | ~10 ms |

JPEG's low latency explains why it remains the default format for burst photography.  HEIF is used for standard captures where latency tolerance is higher.  AVIF remains mostly a web delivery format and is rarely used as a primary camera capture format.

---

## §2 Calibration

### 2.1 Quality Factor Target Per Mode

The quality factor must be tuned per capture mode to balance file size, quality, and latency:

| Capture mode | Recommended JPEG Q | Recommended HEIF Q | Notes |
|---|---|---|---|
| Social share / quick capture | 82–85 | 50–55 | Small file, fast share |
| Standard photo | 88–92 | 60–65 | Good balance |
| Archive / professional | 95 | 75–80 | Maximum quality |
| Burst (10+ frames/s) | 80–85 | N/A (JPEG only) | Latency critical |
| Panorama | 90–95 | 70 | Large output file |

### 2.2 Bitrate Budget for Video Mode

For video recording, encoding bitrate (not quality factor) is the primary control:

| Mode | Resolution | Bitrate | Notes |
|---|---|---|---|
| SD 720p 30fps | 1280×720 | 8 Mbps | Entry-level |
| HD 1080p 30fps | 1920×1080 | 16–20 Mbps | Standard |
| 4K 30fps | 3840×2160 | 40–60 Mbps | High quality |
| 4K 60fps | 3840×2160 | 80–100 Mbps | High motion |
| 4K HDR (HEVC) | 3840×2160 | 50–80 Mbps | HDR10 / Dolby Vision |

---

## §3 Tuning

### 3.1 JPEG Quality Per Scenario

**Tuning process:**

1. Capture a test set covering multiple scene types (landscape, portrait, low-light, text, fine detail)
2. Encode each image at Q = 70, 75, 80, 85, 90, 95
3. Measure SSIM and BRISQUE at each quality level
4. Identify the minimum Q at which SSIM > 0.97 and no visible blocking artifacts
5. Select that Q as the default for the target application

**File size reference for 12 MP camera (~3:2 aspect ratio, 4032×3024):**

```
Q = 95:  5.5–8.0 MB
Q = 90:  3.5–5.0 MB
Q = 85:  2.0–3.0 MB
Q = 80:  1.5–2.0 MB
Q = 75:  1.0–1.5 MB
```

### 3.2 HEIF vs. JPEG Decision Logic

```
Scene mode = ?
  ├── Burst capture        → JPEG (latency critical)
  ├── Night mode           → HEIF (preserve HDR detail)
  ├── Portrait mode        → HEIF (depth map + portrait mask in same file)
  ├── Standard photo       → HEIF if Android 10+ / iOS, else JPEG
  └── Share to social      → JPEG (universal compatibility)
```

---

## §4 Artifacts

### 4.1 JPEG Blocking (DCT Block Artifact)

**Description:** At low quality factors (Q < 70), the image shows a visible 8×8 grid pattern, most pronounced in smooth gradient regions (sky, skin).

**Root cause:** Heavy quantization of the DCT coefficients removes mid-frequency terms, leaving only low-frequency components.  The 8×8 block boundaries become visible because each block is decoded independently.

**Mitigation:**
- Increase quality factor (Q ≥ 80 for photographic content)
- Post-process with a **deblocking filter**: apply a mild low-pass filter along 8×8 block boundaries; this is standard in HEVC/H.265 but not in JPEG
- Switch to HEIF/AVIF which use larger CTU blocks (no 8×8 grid artifact)

### 4.2 HEIF Ringing at Low Bitrate

**Description:** At very low HEIF quality settings (Q < 40), fine-detail edges show oscillatory ringing halos (Gibbs phenomenon), similar to JPEG mosquito noise but at different spatial scales.

**Root cause:** HEVC intra-prediction and transform coding also introduce ringing when high-frequency DCT coefficients are zeroed out.  Ringing is more visible in HEVC at very low bitrates because larger CTU blocks create larger ringing zones.

**Mitigation:**
- Use quality setting ≥ 50 for HEIF
- Apply in-loop deblocking and SAO (Sample Adaptive Offset) in the HEVC encoder (enabled by default)

### 4.3 Chroma Bleeding (4:2:0 at Color Edges)

**Description:** At sharp color transitions (red text on white background, colored objects with hard edges), the color appears to bleed outward by 1–2 pixels.

**Root cause:** 4:2:0 chroma subsampling averages Cb/Cr over 2×2 pixel areas.  At a sharp color edge, the averaged Cb/Cr value is spread across adjacent pixels, causing color to bleed into adjacent luma areas.

**Mitigation:**
- Use 4:4:4 chroma subsampling for text and graphics content (not photographs)
- Apply pre-subsampling anti-aliasing to the Cb/Cr channels

### 4.4 Color Space Mismatch (BT.601 vs BT.709)

**Description:** Images appear slightly desaturated or with a different hue when displayed on BT.709 calibrated monitors, even though the JPEG looks correct on the camera screen.

**Root cause:** JPEG/JFIF assumes BT.601 YCbCr coefficients, while modern displays use BT.709 (sRGB).  If the ISP converts using BT.709 coefficients but writes a JFIF header (implying BT.601), the decoder applies incorrect inverse coefficients.

**Mitigation:**
- Ensure the JPEG YCbCr conversion uses BT.601 coefficients when writing JFIF format
- Use EXIF color space tag (`Exif.Photo.ColorSpace = sRGB = 1`) to signal the output color space
- For HEIF: use ICC profile or the HEIF `ColourInformationBox` to specify the exact color space

---

## §5 Evaluation

### 5.1 SSIM (Structural Similarity Index)

SSIM measures the structural similarity between the original uncompressed image and the compressed output, accounting for luminance, contrast, and structure:

$$
\text{SSIM}(x, y) = \frac{(2\mu_x \mu_y + C_1)(2\sigma_{xy} + C_2)}{(\mu_x^2 + \mu_y^2 + C_1)(\sigma_x^2 + \sigma_y^2 + C_2)}
$$

where $\mu_x, \mu_y$ are local means, $\sigma_x^2, \sigma_y^2$ are local variances, $\sigma_{xy}$ is local cross-covariance, and $C_1, C_2$ are stability constants.

SSIM ranges from –1 to 1, with 1 = identical.

**Interpretation:**

| SSIM | Visual quality |
|---|---|
| > 0.98 | Imperceptible difference |
| 0.95–0.98 | Minor differences visible on close inspection |
| 0.90–0.95 | Visible artifacts in some regions |
| < 0.90 | Clearly degraded image quality |

### 5.2 BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator)

BRISQUE is a no-reference perceptual quality metric that measures distortion of local normalized luminance coefficients from their expected natural scene statistics.

- **Lower BRISQUE = better quality** (score 0 = perfect, score 100 = severely distorted)
- Does not require a reference image (blind metric)
- Sensitive to JPEG blocking, blur, and noise artifacts

**Target BRISQUE scores:**

| Quality | BRISQUE |
|---|---|
| Pristine natural image | 20–35 |
| Good quality JPEG (Q=85) | 30–45 |
| Moderate JPEG (Q=75) | 45–60 |
| Poor JPEG (Q=60) | 60–80 |

### 5.3 File Size vs. Quality Pareto Curve

For a given scene type, the optimal quality setting lies on the **Pareto front** of the (file size, SSIM) trade-off curve.  The knee of the curve — where additional file size provides diminishing SSIM improvement — identifies the optimal quality setting.

Plot SSIM vs. log(file_size) for Q = 60, 70, 75, 80, 85, 90, 95, 100.  The knee typically falls at Q = 80–88 for JPEG and Q = 55–70 for HEIF.

### 5.4 Encode/Decode Latency

Measure wall-clock latency for encoding a 12 MP image at the target quality on the target device:

- **Encode latency:** Time from raw ISP output buffer available to encoded file written to storage
- **Decode latency:** Time from file read start to decoded RGB buffer available for display

**Target for default photo capture:**
- Encode: < 100 ms end-to-end (including ISP post-processing)
- Decode for preview: < 50 ms (thumbnail), < 200 ms (full resolution)

---

## §6 Code

```python
"""
ch33_jpeg_heif_encoding.py
Demonstrates:
  - JPEG encoding with PIL at different quality levels
  - SSIM and file size measurement
  - Quality-size-SSIM Pareto curve generation
  - DCT visualization for a single 8x8 block
  - PQ (SMPTE ST 2084) EOTF for HDR encoding
"""

import numpy as np
import io
import math
from PIL import Image


# ------------------------------------------------------------------ #
# §6.1  JPEG quality-size sweep                                      #
# ------------------------------------------------------------------ #

def encode_jpeg_to_buffer(img_pil: Image.Image, quality: int) -> bytes:
    """Encode a PIL image to JPEG in memory and return the bytes."""
    buf = io.BytesIO()
    img_pil.save(buf, format='JPEG', quality=quality, subsampling=2)  # 2=4:2:0
    return buf.getvalue()


def encode_jpeg_444_to_buffer(img_pil: Image.Image, quality: int) -> bytes:
    """Encode with 4:4:4 chroma subsampling (subsampling=0)."""
    buf = io.BytesIO()
    img_pil.save(buf, format='JPEG', quality=quality, subsampling=0)
    return buf.getvalue()


def compute_ssim(img_a: np.ndarray, img_b: np.ndarray) -> float:
    """
    Compute mean SSIM between two uint8 RGB images (simplified, single-scale).
    For production use: skimage.metrics.structural_similarity
    """
    a = img_a.astype(np.float64)
    b = img_b.astype(np.float64)

    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2
    window = 11

    ssim_values = []
    H, W, C = a.shape
    for c in range(C):
        plane_a = a[:, :, c]
        plane_b = b[:, :, c]
        # Compute local statistics using box filter approximation
        from scipy.ndimage import uniform_filter
        mu_a   = uniform_filter(plane_a, size=window)
        mu_b   = uniform_filter(plane_b, size=window)
        sig_a2 = uniform_filter(plane_a**2, size=window) - mu_a**2
        sig_b2 = uniform_filter(plane_b**2, size=window) - mu_b**2
        sig_ab = uniform_filter(plane_a * plane_b, size=window) - mu_a * mu_b

        ssim_map = ((2*mu_a*mu_b + C1) * (2*sig_ab + C2)) / \
                   ((mu_a**2 + mu_b**2 + C1) * (sig_a2 + sig_b2 + C2) + 1e-12)
        ssim_values.append(float(ssim_map.mean()))

    return float(np.mean(ssim_values))


def jpeg_quality_sweep(
    img_pil: Image.Image,
    qualities: list = None,
) -> list:
    """
    Sweep JPEG quality factor and measure SSIM and file size.

    Returns list of dicts with keys: quality, ssim, size_kb, bpp
    """
    if qualities is None:
        qualities = [60, 70, 75, 80, 85, 88, 90, 92, 95, 100]

    original = np.array(img_pil.convert('RGB'))
    H, W = original.shape[:2]
    results = []

    for q in qualities:
        jpeg_bytes = encode_jpeg_to_buffer(img_pil, q)
        decoded = np.array(Image.open(io.BytesIO(jpeg_bytes)).convert('RGB'))
        ssim  = compute_ssim(original, decoded)
        size_kb = len(jpeg_bytes) / 1024.0
        bpp     = (len(jpeg_bytes) * 8) / (H * W)
        results.append({'quality': q, 'ssim': ssim,
                        'size_kb': size_kb, 'bpp': bpp})
        print(f"  Q={q:3d}  SSIM={ssim:.4f}  {size_kb:7.1f} KB  {bpp:.3f} bpp")

    return results


# ------------------------------------------------------------------ #
# §6.2  2D DCT visualization on one 8x8 block                       #
# ------------------------------------------------------------------ #

def dct2d_8x8(block: np.ndarray) -> np.ndarray:
    """
    Compute the 2D DCT-II of an 8x8 block (level-shifted by -128).
    Returns 8x8 float64 DCT coefficients.
    """
    assert block.shape == (8, 8)
    f = block.astype(np.float64) - 128.0

    # Separable DCT: apply 1D DCT to rows, then to columns
    N = 8
    dct_coeff = np.zeros((N, N), dtype=np.float64)
    for u in range(N):
        Cu = (1.0 / math.sqrt(2)) if u == 0 else 1.0
        for v in range(N):
            Cv = (1.0 / math.sqrt(2)) if v == 0 else 1.0
            s = 0.0
            for x in range(N):
                for y in range(N):
                    s += f[x, y] * (math.cos((2*x+1)*u*math.pi/16) *
                                    math.cos((2*y+1)*v*math.pi/16))
            dct_coeff[u, v] = 0.25 * Cu * Cv * s
    return dct_coeff


def idct2d_8x8(coeffs: np.ndarray) -> np.ndarray:
    """Inverse 2D DCT-II (IDCT) of 8x8 coefficients. Returns level-shifted block."""
    N = 8
    f = np.zeros((N, N), dtype=np.float64)
    for x in range(N):
        for y in range(N):
            s = 0.0
            for u in range(N):
                Cu = (1.0 / math.sqrt(2)) if u == 0 else 1.0
                for v in range(N):
                    Cv = (1.0 / math.sqrt(2)) if v == 0 else 1.0
                    s += (Cu * Cv * coeffs[u, v] *
                          math.cos((2*x+1)*u*math.pi/16) *
                          math.cos((2*y+1)*v*math.pi/16))
            f[x, y] = 0.25 * s
    return f + 128.0


# ------------------------------------------------------------------ #
# §6.3  JPEG quantization matrix (standard luminance)                #
# ------------------------------------------------------------------ #

JPEG_QUANT_LUMA_Q50 = np.array([
    [16, 11, 10, 16, 24, 40, 51, 61],
    [12, 12, 14, 19, 26, 58, 60, 55],
    [14, 13, 16, 24, 40, 57, 69, 56],
    [14, 17, 22, 29, 51, 87, 80, 62],
    [18, 22, 37, 56, 68,109,103, 77],
    [24, 35, 55, 64, 81,104,113, 92],
    [49, 64, 78, 87,103,121,120,101],
    [72, 92, 95, 98,112,100,103, 99],
], dtype=np.float32)


def scale_quant_matrix(base: np.ndarray, quality: int) -> np.ndarray:
    """
    Scale the base quantization matrix by a JPEG quality factor.
    Returns the scaled quantization matrix (values clipped to [1, 255]).
    """
    if quality < 50:
        scale = 5000 / quality
    else:
        scale = 200 - 2 * quality
    Q = np.floor((base * scale + 50) / 100).astype(np.float32)
    return np.clip(Q, 1, 255)


# ------------------------------------------------------------------ #
# §6.4  PQ (SMPTE ST 2084) EOTF for HDR                             #
# ------------------------------------------------------------------ #

def pq_eotf_forward(L: np.ndarray) -> np.ndarray:
    """
    PQ (Perceptual Quantizer) forward EOTF: linear light → encoded signal V.

    L : normalized linear light (0.0 to 1.0, where 1.0 = 10,000 cd/m2)
    Returns V in [0, 1] (signal value for 10-bit/12-bit encoding)
    """
    m1 = 0.1593017578125
    m2 = 78.84375
    c1 = 0.8359375
    c2 = 18.8515625
    c3 = 18.6875

    Lm1 = np.power(np.maximum(L, 0.0), m1)
    V = np.power((c1 + c2 * Lm1) / (1.0 + c3 * Lm1), m2)
    return V


def pq_eotf_inverse(V: np.ndarray) -> np.ndarray:
    """
    PQ inverse EOTF: encoded signal V → normalized linear light L.
    """
    m1 = 0.1593017578125
    m2 = 78.84375
    c1 = 0.8359375
    c2 = 18.8515625
    c3 = 18.6875

    Vm2 = np.power(np.maximum(V, 0.0), 1.0 / m2)
    L = np.power(np.maximum(Vm2 - c1, 0.0) / (c2 - c3 * Vm2), 1.0 / m1)
    return L


# ------------------------------------------------------------------ #
# §6.5  Quality–size–SSIM comparison                                 #
# ------------------------------------------------------------------ #

def print_quality_table(results: list) -> None:
    """Print a formatted quality vs. SSIM vs. file size table."""
    print(f"\n{'Quality':>8} {'SSIM':>8} {'Size (KB)':>10} {'BPP':>7}")
    print("-" * 40)
    for r in results:
        print(f"{r['quality']:>8d} {r['ssim']:>8.4f} {r['size_kb']:>10.1f} {r['bpp']:>7.3f}")


# ------------------------------------------------------------------ #
# §6.6  Demo                                                         #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    import sys

    img_path = sys.argv[1] if len(sys.argv) > 1 else None

    if img_path:
        img_pil = Image.open(img_path).convert('RGB')
    else:
        # Synthetic test image: gradient + random texture
        rng  = np.random.default_rng(42)
        arr  = np.zeros((256, 256, 3), dtype=np.uint8)
        # Horizontal gradient
        for x in range(256):
            arr[:, x, 0] = x          # red gradient
        arr[:, :, 1] = rng.integers(50, 200, (256, 256))  # random green (texture)
        arr[:, :, 2] = 128            # constant blue
        img_pil = Image.fromarray(arr)

    print("JPEG quality sweep (4:2:0 chroma subsampling):")
    results = jpeg_quality_sweep(img_pil, qualities=[60, 70, 75, 80, 85, 90, 95])
    print_quality_table(results)

    # Find the knee of the Pareto curve
    prev_ssim = 0.0
    knee_quality = 85
    for r in results:
        gain = r['ssim'] - prev_ssim
        if gain < 0.005 and r['quality'] > 75:
            knee_quality = r['quality']
            break
        prev_ssim = r['ssim']

    print(f"\nRecommended quality (Pareto knee): Q = {knee_quality}")

    # DCT visualization on a single block
    print("\nDCT coefficient example (8x8 block from synthetic image):")
    block = np.array(img_pil.convert('L'))[0:8, 0:8]
    dct_coeffs = dct2d_8x8(block)
    print(f"  DC coefficient F(0,0) = {dct_coeffs[0,0]:.2f}")
    print(f"  Max AC coefficient    = {np.max(np.abs(dct_coeffs[1:])):.2f}")
    print(f"  Fraction of energy in top-left 2x2: "
          f"{np.sum(dct_coeffs[:2,:2]**2) / np.sum(dct_coeffs**2):.2%}")

    # Quantization matrix at Q=85
    Q85 = scale_quant_matrix(JPEG_QUANT_LUMA_Q50, quality=85)
    print(f"\nQuantization matrix at Q=85 (DC entry): {Q85[0,0]:.0f}")
    print(f"Quantization matrix at Q=85 (HF entry [7,7]): {Q85[7,7]:.0f}")

    # PQ curve example
    L_values = np.array([0.0, 0.01, 0.1, 0.5, 1.0])
    V_values = pq_eotf_forward(L_values)
    print("\nPQ EOTF forward (normalized linear → encoded signal):")
    for L, V in zip(L_values, V_values):
        nits = L * 10000
        print(f"  {nits:7.1f} cd/m2  →  V = {V:.4f}  "
              f"(10-bit code: {int(V*1023+0.5):4d})")
```

---

## References

- **Wallace, G. K. (1992).** The JPEG Still Picture Compression Standard. *IEEE Transactions on Consumer Electronics*, 38(1).
- **Sullivan, G. J., Ohm, J., Han, W., & Wiegand, T. (2012).** Overview of the High Efficiency Video Coding (HEVC) Standard. *IEEE Transactions on Circuits and Systems for Video Technology*, 22(12), 1649–1668.
- **Chen, Y. et al. (2018).** Algorithm Description of Joint Exploration Test Model 7 (JEM 7). *ISO/IEC JTC1/SC29/WG11 JVET-G1001.*
- **SMPTE ST 2084:2014.** High Dynamic Range Electro-Optical Transfer Function of Mastering Reference Displays. (PQ EOTF)
- **AV1 Bitstream & Decoding Process Specification.** Alliance for Open Media. https://aomedia.org/av1/specification/
- **ISO/IEC 23008-12:2017.** High efficiency coding and media delivery in heterogeneous environments — Part 12: Image File Format. (HEIF standard)
- **Android ImageFormat reference:** https://developer.android.com/reference/android/graphics/ImageFormat
- **libjpeg-turbo (high-performance JPEG):** https://libjpeg-turbo.org/
