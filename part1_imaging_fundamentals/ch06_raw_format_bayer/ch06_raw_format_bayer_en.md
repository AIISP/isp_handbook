# Part 1, Chapter 06: RAW Format & Image Format System

> **Pipeline position:** Sensor output → RAW data → ISP pipeline entry; the data source for all downstream ISP processing
> **Prerequisites:** Chapter 03 (Image Sensor Physics), Chapter 05 (Color Science Basics)
> **Reader path:** Algorithm engineers, system engineers, tuning engineers

---

## §1 Theory

### 1.1 What Is a RAW Image?

A **RAW image** is the unprocessed digital data from the sensor after ADC (Analog-to-Digital Conversion), before any ISP processing. Each pixel records the intensity of only one color channel (determined by the CFA filter), with a value range of `[0, 2^N - 1]` where N is the ADC bit depth.

The fundamental difference between RAW and JPEG:

```
RAW (linear domain):
  ┌─────────────────────────────────────────────────┐
  │ Sensor → ADC → [black level offset] → linear    │
  │ photon count values                              │
  │ 1 channel per pixel (R or G or B)               │
  │ No Gamma, no demosaicing, no sharpening,         │
  │ no denoising                                     │
  └─────────────────────────────────────────────────┘

JPEG (sRGB display domain):
  ┌─────────────────────────────────────────────────┐
  │ RAW → full ISP pipeline → Gamma → JPEG lossy    │
  │ 3 channels per pixel (R, G, B), sRGB color space│
  │ Irreversible information loss (quantization +   │
  │ lossy compression)                              │
  └─────────────────────────────────────────────────┘
```

**Core value of RAW:**
1. **Maximum dynamic range**: 14-bit RAW has 16,384 levels; JPEG has only 256
2. **Non-destructive post-processing**: All ISP parameters (white balance, tone curve, sharpening) can be re-adjusted
3. **Scientific/industrial use**: Medical imaging, astrophotography, and machine vision require linear light intensity data
4. **ISP tuning**: ISP engineers must work with RAW data to independently validate each module's effect

### 1.2 RAW Data Bit Depth and Packing Formats

Modern sensor ADCs typically output 10–14 bit data, stored and transmitted using various packing schemes:

#### Common Bit Depths

| Bit Depth | Dynamic Range Ceiling | Typical Use |
|-----------|----------------------|-------------|
| 8-bit | 48 dB | Low-end sensors; video YUV |
| 10-bit | 60 dB | Smartphone main camera (MIPI RAW10) |
| 12-bit | 72 dB | Flagship phones (MIPI RAW12), consumer cameras |
| 14-bit | 84 dB | Professional cameras (Canon CR3, Sony ARW) |
| 16-bit | 96 dB | Scientific cameras, medical imaging |

#### MIPI CSI-2 RAW Packing Formats (Smartphone Sensor Standard)

Smartphone sensors transmit RAW data to the ISP over MIPI CSI-2. Common packing formats:

**RAW10 (10-bit packed):** 4 pixels per 5 bytes
```
Byte layout (4 pixels P0–P3):
Byte0: P0[9:2]
Byte1: P1[9:2]
Byte2: P2[9:2]
Byte3: P3[9:2]
Byte4: P3[1:0] | P2[1:0] | P1[1:0] | P0[1:0]
```

**RAW12 (12-bit packed):** 2 pixels per 3 bytes
```
Byte layout (2 pixels P0–P1):
Byte0: P0[11:4]
Byte1: P1[11:4]
Byte2: P1[3:0] | P0[3:0]
```

**RAW16 (16-bit unpacked):** 2 bytes per pixel, high-bit aligned, low bits zero-padded (typically 14-bit data stored in a 16-bit container)

#### Industry Format Reference

```
Sony IMX series         → MIPI RAW10 / RAW12 (depends on resolution and frame rate)
Samsung ISOCELL series  → MIPI RAW10 / RAW12 / RAW14
Qualcomm ISP (Spectra)  → Receives MIPI RAW; outputs Qualcomm proprietary format
DNG files               → 12-bit or 14-bit; optional lossless/lossy compression
```

### 1.3 CFA (Color Filter Array) Patterns

In a RAW image, each pixel records only one color, determined by the CFA. See Chapter 3 §1.6 for detailed physics; here we take an engineering format perspective:

#### Bayer RGGB (Most Common)

```
R  Gr R  Gr R  Gr
Gb B  Gb B  Gb B
R  Gr R  Gr R  Gr
Gb B  Gb B  Gb B
```

A pixel's channel assignment in raw data is entirely determined by its spatial coordinates:
```python
def get_bayer_channel(row, col, pattern='RGGB'):
    # RGGB: even-row even-col=R, even-row odd-col=Gr,
    #        odd-row even-col=Gb, odd-row odd-col=B
    r, c = row % 2, col % 2
    mapping = {
        'RGGB': {(0,0):'R',  (0,1):'Gr', (1,0):'Gb', (1,1):'B'},
        'BGGR': {(0,0):'B',  (0,1):'Gb', (1,0):'Gr', (1,1):'R'},
        'GRBG': {(0,0):'Gr', (0,1):'R',  (1,0):'B',  (1,1):'Gb'},
        'GBRG': {(0,0):'Gb', (0,1):'B',  (1,0):'R',  (1,1):'Gr'},
    }
    return mapping[pattern][(r, c)]
```

The four Bayer variants (RGGB/BGGR/GRBG/GBRG) are mathematically equivalent, differing only in the channel of pixel (0,0). The ISP must confirm the CFA starting phase when reading sensor data.

#### Quad-Bayer (High-Megapixel Smartphone Sensors)

Quad-Bayer expands each "logical pixel" into a 2×2 block of same-color physical pixels:

```
R  R  Gr Gr
R  R  Gr Gr
Gb Gb B  B
Gb Gb B  B
```

**Remosaic problem:** Quad-Bayer raw data is not standard Bayer format and cannot be directly processed by conventional demosaicing algorithms. The ISP must first perform **Remosaic** (rearranging the 4 same-color sub-pixels back into standard Bayer order) before the normal ISP pipeline can proceed. Remosaic quality directly impacts full-resolution mode image quality.

### 1.4 Major RAW File Formats

Different camera manufacturers use proprietary RAW formats; DNG is the only open standard:

| Format | Vendor/Standard | Bit Depth | Compression | Notes |
|--------|----------------|-----------|-------------|-------|
| **DNG** | Adobe (open standard) | 8–32 bit | Lossless/lossy | TIFF-based; complete metadata; Android Camera2 API support |
| **ARW** | Sony | 12–14 bit | Lossless | Mainstream full-frame camera format |
| **CR3** | Canon | 14 bit | CRAW lossy/lossless | Canon EOS system; HEIF container |
| **NEF** | Nikon | 12–14 bit | Lossless | Contains WB/in-camera VR data |
| **RAF** | Fujifilm | 12–14 bit | Lossless | X-Trans CFA requires special demosaicing |
| **RW2** | Panasonic | 12 bit | Lossless | L-mount system |
| **ORF** | Olympus/OM | 12 bit | Lossless | Micro Four Thirds system |
| **ARQ** | Sony | 42-bit (4-frame composite) | — | Pixel Shift multi-frame SR RAW |
| **BRAW** | Blackmagic | 12 bit | Lossy | Cinema camera format; GPU decode |

#### DNG Format Details

DNG (Digital Negative) is an open RAW standard released by Adobe in 2004, adopted by Google as the RAW output format for the Android Camera2 API:

**DNG file structure (TIFF-EP based):**
```
DNG file
├── IFD0 (main image directory)
│   ├── SubIFD → Full-resolution RAW data (Bayer/linear)
│   │   ├── BlackLevel (per-channel black level)
│   │   ├── WhiteLevel (white level / full well)
│   │   ├── CFAPattern (CFA pattern: RGGB etc.)
│   │   ├── ColorMatrix1/2 (CCM, D65/A illuminant)
│   │   ├── AsShotNeutral (white balance gains at capture)
│   │   └── NoiseProfile (noise model parameters a, b)
│   ├── Thumbnail (embedded preview JPEG)
│   └── EXIF IFD (exposure parameters)
└── Makernote (manufacturer private metadata)
```

**Key DNG metadata fields for ISP calibration:**

```python
import rawpy

raw = rawpy.imread('image.dng')
print(raw.black_level_per_channel)         # [BL_R, BL_Gr, BL_Gb, BL_B]
print(raw.white_level)                      # White level (ADC full scale)
print(raw.camera_white_level_per_channel)   # Per-channel white level after WB
print(raw.color_matrix)                     # 3×3 color matrix (RAW→XYZ)
print(raw.daylight_whitebalance)            # D65 standard white balance coefficients
```

### 1.5 Image Output Format System

The image formats output by the ISP pipeline must balance image quality, compression efficiency, and device compatibility:

#### Static Image Format Comparison

| Format | Compression | Bit Depth | Color Space | Typical Use |
|--------|-------------|-----------|-------------|-------------|
| **JPEG** | DCT lossy (YCbCr) | 8-bit | sRGB | Widest compatibility; default phone photo format |
| **HEIF/HEIC** | HEVC/H.265 lossy | 8/10-bit | sRGB/Display P3 | iOS default; 2× better compression than JPEG |
| **AVIF** | AV1 lossy/lossless | 8/10/12-bit | Wide gamut | Next-gen web image format; Chrome/Safari support |
| **PNG** | DEFLATE lossless | 8/16-bit | sRGB | Screenshots/UI; lossless but large files |
| **TIFF** | Lossless/uncompressed | 8/16/32-bit | Any | Professional print/science; DNG is TIFF-based |
| **WebP** | VP8 lossy/VP8L lossless | 8-bit | sRGB | Google web format; Android support |
| **JXL (JPEG XL)** | Lossless/lossy | 8/16/32-bit | Wide gamut HDR | Emerging standard; backward-compatible with JPEG |

#### Video Frame / Camera HAL Intermediate Formats

Within Android Camera HAL and SoC ISP internal pipelines, YUV formats are used to pass image data:

| Format | Subsampling | Description | Typical Use |
|--------|------------|-------------|-------------|
| **YUV 4:2:0 (NV21)** | 4:2:0 | Y plane + interleaved VU plane; Android default | Camera preview/video |
| **YUV 4:2:0 (NV12)** | 4:2:0 | Y plane + interleaved UV plane; V4L2/Linux | SoC ISP output |
| **YUV 4:2:2 (YUYV)** | 4:2:2 | Interleaved Y/U/Y/V; common for USB cameras | UVC camera devices |
| **YUV 4:4:4** | 4:4:4 | Full-resolution chroma; no color loss | Professional video |
| **P010** | 4:2:0, 10-bit | 10-bit version of NV12; HDR video | HDR10/HLG video |
| **RGBA/BGRA** | — | Full channels with alpha; GPU processing | OpenGL/Vulkan textures |

**NV21/NV12 memory layout (4×2 example image):**
```
NV21 (Android default):
  Y plane:  Y00 Y01 Y02 Y03 Y10 Y11 Y12 Y13   ← 8 bytes
  VU plane: V00 U00 V02 U02                    ← 4 bytes (2× downsampled)

NV12 (Linux/SoC):
  Y plane:  Y00 Y01 Y02 Y03 Y10 Y11 Y12 Y13   ← 8 bytes
  UV plane: U00 V00 U02 V02                    ← 4 bytes
```

Note that NV21 and NV12 have **reversed UV order**! A common color error (green faces) often originates from confusing NV21/NV12.

#### HDR Image Formats

With the proliferation of HDR displays, image formats are evolving toward high dynamic range:

| Format | Transfer Function | Color Gamut | Peak Luminance | Notes |
|--------|------------------|-------------|----------------|-------|
| **HDR10** | PQ (ST.2084) | Rec.2020 | 1000 nit (static metadata) | No license fees; widely supported |
| **HDR10+** | PQ | Rec.2020 | 4000 nit (dynamic metadata) | Samsung-driven |
| **Dolby Vision** | PQ | Rec.2020 | 10000 nit (dynamic) | License fee; Apple iPhone support |
| **HLG** | HLG (ITU-R BT.2100) | Rec.2020 | — | Backward-compatible with SDR; broadcast standard |
| **JPEG XL (HDR)** | PQ/HLG | Wide gamut | — | Static HDR image storage |

### 1.6 Format Flow in Android Camera2 API

In the Android Camera2/CameraX architecture, image formats flow through different stages:

```
Sensor output (MIPI RAW10/12)
        ↓
Qualcomm Spectra / MediaTek ISP
        ↓
┌──────────────────────────────────────┐
│ ImageReader / ImageWriter            │
│  ├─ ImageFormat.RAW_SENSOR           │ → DNG save
│  ├─ ImageFormat.YUV_420_888 (NV12)  │ → Preview / video encode
│  ├─ ImageFormat.JPEG                 │ → Photo save
│  └─ ImageFormat.HEIF                 │ → iOS-compatible format
└──────────────────────────────────────┘
        ↓
MediaCodec (H.265/AV1 encoder)
        ↓
MP4 / MOV video file
```

`ImageFormat.RAW_SENSOR` corresponds to the device's native Bayer data (bit depth depends on sensor, typically 10–16 bit, stored in a 16-bit container).

---

## §2 Calibration

### 2.1 DNG Metadata Calibration

DNG files embed calibration data. ISP algorithm engineers must extract the following fields when reading a DNG:

| DNG Tag | Meaning | Calibration Use |
|---------|---------|----------------|
| `BlackLevel` | Per-channel black level | BLC starting point (see Chapter 18) |
| `WhiteLevel` | White level (ADC full scale) | BLC normalization denominator |
| `ColorMatrix1/2` | RAW→XYZ matrix (D65/A illuminant) | CCM reference (see Chapter 23) |
| `CameraCalibration1/2` | Individual camera calibration matrix | Compensates sensor batch variation |
| `AsShotNeutral` | AWB-estimated neutral value at capture | AWB initialization |
| `NoiseProfile` | Noise model parameter pairs (a, b) | Poisson-Gaussian noise model calibration (see Chapter 4) |
| `LensShading` | Lens shading gain map | LSC reference (see Chapter 25) |

**rawpy example for reading DNG metadata:**
```python
import rawpy
import numpy as np

with rawpy.imread('sample.dng') as raw:
    # Black level and white level
    blc = raw.black_level_per_channel      # [R, Gr, Gb, B]
    wl = raw.white_level                    # White level

    # Raw Bayer data
    bayer = raw.raw_image_visible.copy()   # uint16 Bayer image

    # Normalize to [0, 1]
    bayer_norm = (bayer.astype(np.float32) - np.min(blc)) / (wl - np.min(blc))
    bayer_norm = np.clip(bayer_norm, 0, 1)

    # CFA pattern
    print(raw.raw_pattern)  # e.g., [[0,1],[3,2]] = RGGB
```

### 2.2 Format Compatibility Validation

ISP engineers integrating a new sensor must validate format field correctness:

1. **CFA phase validation**: Shoot a white wall; check whether the (0,0) pixel in RAW matches the CFA configuration (for RGGB, the R channel value should be highest)
2. **Black level validation**: Shoot a dark frame with the lens covered; check whether the per-channel mean matches the `BlackLevel` tag (±2 LSB)
3. **White level validation**: Shoot a uniformly lit near-saturating white field; check whether the brightest pixel is close to the `WhiteLevel` value

---

## §3 Tuning

### 3.1 RAW Bit Depth Impact on ISP Tuning

| Bit Depth | Black Level Estimation Accuracy | Color Accuracy | Recommended Strategy |
|-----------|--------------------------------|----------------|---------------------|
| 10-bit | ±1 LSB = 0.1% of full scale | Strong AWB gains can cause quantization banding | OB region mean filtering to reduce estimation noise |
| 12-bit | ±1 LSB = 0.024% of full scale | Sufficiently precise | Standard BLC procedure |
| 14-bit | ±1 LSB = 0.006% of full scale | Extremely precise | More refined dark-region color adjustments possible |

**Quantization banding in 10-bit RAW:** When AWB applies a 2× gain to the blue channel, the 10-bit quantization step is magnified to 2 display levels. In low-saturation blue areas (e.g., sunny shadows) this can produce visible gradient banding. Solutions:
1. Add low-level dither noise after RAW-domain gain
2. Use 14-bit internal processing precision even when the sensor only outputs 10-bit

### 3.2 HEIF vs. JPEG Output Selection

| Scenario | Recommended Format | Reason |
|----------|-------------------|--------|
| Everyday photo storage | HEIF/HEIC | Half the file size at equivalent quality; 10-bit wide gamut support |
| Wide sharing/web upload | JPEG | Maximum compatibility; all devices/platforms support |
| Professional post-processing | DNG + JPEG dual save | DNG preserves all RAW data; JPEG for quick preview |
| HDR video recording | HEVC (P010) | 10-bit HDR support; H.265 high encoding efficiency |

---

## §4 Artifacts

### 4.1 CFA Phase Error

**Symptom:** Large areas of incorrect color across the entire image (green-dominant or overall magenta shift); colors are completely wrong.

**Cause:** The ISP reads RAW data with an incorrect CFA starting coordinate (e.g., RGGB is treated as BGGR), causing the demosaicing to swap R/B channels.

**Diagnosis:** In the debug interface, force display of RAW channel distribution; confirm that the value of pixel (0,0) matches the CFA configuration.

### 4.2 JPEG Quantization Blocking Artifacts

**Symptom:** Rectangular 8×8-pixel blocks appear in uniform image regions, especially pronounced at low bitrates (high compression) and in dark areas.

**Cause:** JPEG DCT quantization step size is too large, causing inter-block discontinuities.

**ISP mitigation:** Apply a mild smoothing pass to low-frequency flat regions before JPEG encoding; choose an appropriate JPEG Quality parameter (typically 85–95).

### 4.3 NV21/NV12 Confusion (Color Error)

**Symptom:** Abnormal image colors: faces appear green, or the blue/red channels are globally swapped.

**Cause:** YUV data produced as NV21 is consumed as NV12 (or vice versa), causing U/V channel inversion.

**Diagnosis:** Check the Android `ImageFormat` enum value: NV21 = 17 (a variant of `YUV_420_888`); NV12 is not a standard Android enum — distinguish via stride/pixelStride.

### 4.4 Quad-Bayer Remosaic Failure

**Symptom:** In full-resolution mode (no pixel binning), the image exhibits a color grid-pattern noise, or the apparent resolution is far below the rated value.

**Cause:** Poor Remosaic algorithm quality; differences between the 4 same-color sub-pixels are not properly handled (especially pronounced at edges).

**Tuning recommendation:** Compare MTF50 between binning mode and full-resolution (Remosaiced) mode on a standard resolution test chart; verify that Remosaic does not introduce additional resolution loss.

---

## §5 Evaluation

### 5.1 RAW Quality Assessment

| Evaluation Dimension | Method | Target |
|---------------------|--------|--------|
| Black level accuracy | Dark frame per-channel mean vs. DNG BlackLevel tag | Deviation < 1 LSB |
| White level validation | Near-saturating flat field brightest pixel | ≥ 95% × WhiteLevel |
| CFA phase | Per-channel mean ordering under white flat field | Matches CFA pattern |
| Bit depth validity | Bright flat field histogram — no comb pattern | No visible quantization banding |
| Noise model conformance | PTC curve (see Chapter 3 §2.3) | σ² vs. μ fits Poisson-Gaussian model |

### 5.2 Output Format Quality Assessment

| Format | Quality Evaluation Method | Key Metric |
|--------|--------------------------|-----------|
| JPEG | SSIM/PSNR vs. lossless reference; DXOMark | PSNR > 40 dB (Quality 90) |
| HEIF | File size comparison vs. equivalent JPEG; VMAF | Compression ratio ≥ 1.5× JPEG (same SSIM) |
| DNG | Metadata completeness check; Adobe DNG Validator | Passes validation; imports correctly in Lightroom |
| NV21/YUV | Color deviation (ΔE) vs. sRGB reference | ΔE₀₀ < 3.0 |

---

## §6 Code

See *See §6 Code section for runnable examples.* in this directory for:

- Reading a DNG file and extracting the raw Bayer data (rawpy)
- Visualizing Bayer channel distribution (per-channel false-color display)
- Parsing DNG metadata (BlackLevel, WhiteLevel, ColorMatrix, NoiseProfile)
- NV21 ↔ RGB format conversion (numpy implementation)
- JPEG/HEIF compression quality comparison (PSNR vs. file size)
- Quad-Bayer sub-sampling illustration

---

## References

1. **Adobe DNG Specification 1.7.1** (2023) — Complete DNG format specification with all tag definitions.
   https://helpx.adobe.com/camera-raw/using/adobe-dng-converter.html

2. **MIPI Alliance CSI-2 Specification v3.0** — Defines RAW8/10/12/14/16/20 packing formats.
   https://www.mipi.org/specifications/csi-2

3. **Google Camera HAL3 / Camera2 API Documentation.**
   https://source.android.com/docs/core/camera

4. **IEC 61966-2-1 (sRGB standard)** — sRGB color space and EOTF definition.

5. **ITU-R BT.2100-2 (2018)** — HDR transfer functions PQ and HLG.
   https://www.itu.int/rec/R-REC-BT.2100/en

6. **rawpy Python library** (wrapping LibRaw) — for reading RAW/DNG files.
   https://github.com/letmaik/rawpy

7. **ExifTool** — View/edit metadata in any camera RAW format.
   https://exiftool.org/

8. **Nakamura, J. (Ed.). (2006).** *Image Sensors and Signal Processing for Digital Still Cameras.* CRC Press. Chapter 2: Sensor interfaces and data formats.

9. **libheif** — Open-source HEIF/HEIC codec library.
   https://github.com/strukturag/libheif

10. **Alakuijala, J. et al. (2019).** "JPEG XL next-generation image compression architecture and coding tools." *SPIE Applications of Digital Image Processing XLII*, vol. 11137.
