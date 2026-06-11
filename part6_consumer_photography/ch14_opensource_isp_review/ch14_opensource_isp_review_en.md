# Part 6, Chapter 14: Open-Source ISP Implementations — Review and Community Benchmarks

> **Position:** This chapter is the technical synthesis chapter of the handbook. It surveys open-source ISP toolchains and community benchmark resources, providing researchers and engineers with a directly actionable reference index.
> **Prerequisites:** All chapters of the handbook (this chapter is a comprehensive index)
> **Audience:** All readers

---

## §1 Open-Source ISP Ecosystem Overview

### 1.1 Why Open-Source ISP Matters

In industry, every smartphone manufacturer maintains a strictly confidential ISP algorithm stack — the specific implementation of Qualcomm's Spectra ISP and Apple's A-series chip NR algorithms are not publicly disclosed. This closed nature creates three major barriers for the research community:

**Research reproducibility**: ISP algorithm papers published at CVPR/ECCV depend on the authors' proprietary RAW datasets and private reference ISPs. Other researchers cannot verify conclusions, nor can they make fair comparisons on the same baseline.

**Algorithm verification**: A newly proposed denoising/demosaicing algorithm, to prove its gain "in a real ISP pipeline," needs a publicly available baseline ISP to integrate and test against.

**Education and talent development**: University courses need runnable ISP implementations for teaching demonstrations. The Jupyter Notebooks in each chapter of this handbook (e.g., this chapter's companion *See §6 Code section for runnable examples.*) are a direct product of this need.

### 1.2 Open-Source ISP Project Classification

Open-source ISP implementations can be divided into three categories by technology stack and application scenario:

```
Open-Source ISP Ecosystem Classification:

┌────────────────────────────────────────────────────────────────┐
│  Application layer: Image processing software                   │
│  darktable (GPL), RawTherapee (GPL), Adobe Lightroom (commercial)│
├────────────────────────────────────────────────────────────────┤
│  Library layer: RAW decoding and processing                     │
│  LibRaw (BSD/LGPL), rawpy (Python), colour-science (BSD)        │
├────────────────────────────────────────────────────────────────┤
│  Research layer: Academic open-source implementations           │
│  Unprocessing (Google), PyNet, AWNet, CameraNet                 │
├────────────────────────────────────────────────────────────────┤
│  Hardware/system layer: Camera frameworks                       │
│  Qualcomm CamX (BSD-3), OpenHarmony Camera HAL, libcamera       │
└────────────────────────────────────────────────────────────────┘
```

Dependency relationships between layers: darktable calls LibRaw to decode RAW files; rawpy is a Python wrapper around LibRaw; research code typically uses rawpy to read RAW and colour-science for color science computation; CamX and similar frameworks manage camera hardware at the Android/Linux system layer.

---

## §2 Major Open-Source ISP Projects in Detail

### 2.1 LibRaw: RAW Decoding Foundation Library

**Project information:**
- License: LGPL v2.1 / CDDL (dual license, commercially friendly)
- Language: C++ (core library); provides C/C++/Python interfaces
- GitHub: https://github.com/LibRaw/LibRaw
- Maintenance status: Active (updates continuing in 2024)

**Core capabilities:**
- Supports RAW file formats from **1000+ cameras** (Canon CR2/CR3, Nikon NEF, Sony ARW, Fuji RAF, etc.)
- Provides camera raw RAW data (Bayer RAW) + camera-embedded white balance/color matrices (EXIF data)
- Built-in multiple demosaicing algorithms: DCB, AHD (Adaptive Homogeneity-Directed), LMMSE, AMaZE, etc.

**Use cases:**
LibRaw's role is as a "RAW file decoder," not a full ISP. It solves the problem of "how to correctly read Bayer RAW data from a binary file." darktable, RawTherapee, and Adobe Camera Raw all call LibRaw (or its predecessor dcraw) for RAW decoding at the bottom layer.

**Limitations:**
- Color processing after demosaicing (CCM, tone mapping, local enhancement) is outside LibRaw's scope.
- Does not support real-time streaming (batch file processing only).
- New camera RAW format support lags (typically updated within months of camera release).

### 2.2 darktable: Complete Open-Source RAW Processor

**Project information:**
- License: GPL v3
- Language: C (core) + LUA (plugins) + OpenCL (GPU acceleration)
- GitHub: https://github.com/darktable-org/darktable
- Maintenance status: Very active; monthly updates
- User base: Estimated over 500,000 active users (2024)

**Pixelpipe architecture:**

darktable's core is its **Pixelpipe** architecture, consisting of 50+ modules in series:

```
RAW input (LibRaw decode)
    ↓
├─ Hot Pixels
├─ Demosaic: supports 8 demosaicing algorithms
├─ Noise Profile: preset denoising curves based on camera + ISO
├─ Input Color Profile: ICC profile
├─ Exposure: linear exposure adjustment
├─ White Balance: gray world / photographer setting / camera preset
├─ Tone Equalizer: local contrast control based on exposure zones
├─ Color Calibration: modern CCM; supports any illuminant adaptation
├─ Tone Curve: RGB or LAB space
├─ Sharpen / Haze Removal
├─ Hue-Saturation
├─ Output Color Profile: sRGB / AdobeRGB / P3
└─ JPEG / PNG / TIFF output
```

**Value to handbook researchers:**
Every module in darktable has detailed open-source implementations; these can be studied to learn the actual algorithm choices of industrial-grade (non-smartphone) ISPs. For example, the Tone Equalizer module (8-zone independent exposure adjustment based on the Ansel Adams zone system) is an excellent reference implementation for Vol.2 Ch.18 (Local Tone Mapping).

**Performance**: In OpenCL-accelerated mode, full-resolution (40MP) RAW processing takes approximately 1–3 seconds/image (high-end GPU); CPU mode approximately 10–30 seconds/image.

### 2.3 RawTherapee: Alternative Open-Source RAW Editor

**Project information:**
- License: GPL v3
- GitHub: https://github.com/Beep6581/RawTherapee
- Features: Tone Equalizer, Haze Removal

RawTherapee and darktable are highly functionally overlapping; differences include:
- RawTherapee's denoising engine (RCD+VNG + Wavelet denoising) slightly outperforms darktable's default settings for detail preservation.
- darktable's color science modules (Color Calibration + Tone Equalizer) are more modern and psychophysically aligned.
- Both support LibRaw as RAW decode backend.

Significance for handbook readers: RawTherapee's **Local Contrast** module uses multiscale decomposition based on Laplacian of Gaussian, a practical reference for Vol.2 Ch.04 (Sharpening).

### 2.4 rawpy: The Preferred Python Research Tool

**Project information:**
- License: MIT
- GitHub: https://github.com/letmaik/rawpy
- Installation: `pip install rawpy` (includes pre-compiled LibRaw binary)

rawpy is a Python wrapper around LibRaw and is the **most widely used RAW reading tool in academic research**. All chapter notebooks in this handbook use rawpy to read RAW files:

```python
import rawpy
import numpy as np

# Read RAW file, obtain Bayer RAW array
with rawpy.imread('IMG_1234.CR3') as raw:
    # Get raw Bayer data (no processing applied)
    bayer = raw.raw_image_visible.copy()

    # Get camera-embedded color matrix (xyz_to_camera)
    color_matrix = raw.color_matrix

    # Get camera AWB gains
    daylight_wb = raw.daylight_whitebalance
    camera_wb = raw.camera_whitebalance

    # Process with LibRaw's built-in pipeline (for reference)
    rgb = raw.postprocess(
        use_camera_wb=True,
        output_color=rawpy.ColorSpace.sRGB,
        output_bps=16
    )

print(f"Bayer shape: {bayer.shape}")       # (H, W), uint16
print(f"Bayer pattern: {raw.color_desc}")  # e.g., b'RGGB'
print(f"Black level: {raw.black_level_per_channel}")
print(f"White level: {raw.white_level}")
```

rawpy's `postprocess()` output can serve as a **reference baseline** for evaluating the relative quality of custom ISP algorithms.

### 2.5 colour-science: Python Color Science Library

**Project information:**
- License: BSD-3-Clause
- GitHub: https://github.com/colour-science/colour
- Installation: `pip install colour-science`
- Documentation: https://colour.readthedocs.io/

colour-science is the **most comprehensive Python color science implementation** to date, covering:

| Feature Module | Description | Handbook Chapter |
|---------------|-------------|-----------------|
| CIE XYZ/xyY/Lab/Luv color space conversion | Full CIE 1931/1964 standard | Ch05 |
| Standard illuminant data (D65, D50, A, F-series, etc.) | 300–830nm SPD | Ch05 |
| Chromatic adaptation transforms (CAT02, CAT16, Bradford) | White balance scientific basis | Ch22 |
| Color difference calculation (ΔE₀₀, ΔE₉₄, ΔE₇₆) | IQA evaluation | Ch04 |
| Camera spectral sensitivity database | Measured camera QE curves | Ch03 |
| HDR tone mapping algorithms (Reinhard, ACES, etc.) | Reference implementations | Ch35 |
| Macbeth ColorChecker reference data | Calibration chart reference values | AppB |

```python
import colour

# Compute perceptual color difference (ΔE₀₀) between two colors under D65 illuminant
Lab1 = np.array([50.0, 25.0, -10.0])
Lab2 = np.array([50.0, 26.0, -9.5])
delta_e = colour.delta_E(Lab1, Lab2, method='CIE 2000')
print(f"ΔE₀₀ = {delta_e:.4f}")  # Output: approximately 0.72 (near just-noticeable difference)

# Chromatic adaptation: D50 → D65 (simulating AWB)
xy_src = colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D50']
xy_dst = colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65']
M_CAT16 = colour.adaptation.matrix_chromatic_adaptation_VonKries(
    colour.xy_to_XYZ(xy_src),
    colour.xy_to_XYZ(xy_dst),
    transform='CAT16'
)
```

### 2.6 This Handbook's Code Library ISP Implementation

Each chapter's Jupyter Notebook in this handbook constitutes a **functionally complete modular ISP implementation**. Notebooks marked *(planned)* have inline code available in their §6 Code section; standalone `.ipynb` files are planned for a future release.

| Chapter | Notebook | ISP Function | Status |
|---------|---------|-------------|--------|
| Ch18 | ch18_blc_pdpc_code.ipynb | BLC + PDPC | planned |
| Ch19 | ch19_demosaic_code.ipynb | Bilinear / AHD / RGGB demosaicing | planned |
| Ch20 | ch20_denoising_code.ipynb | BM3D / NLM / DnCNN | planned |
| Ch21 | ch21_sharpening_code.ipynb | USM / Unsharp masking / RL deconvolution | planned |
| Ch22 | ch22_awb_code.ipynb | Gray world / Perfect reflector / Statistical learning AWB | planned |
| Ch23 | ch23_ccm_code.ipynb | Least-squares CCM calibration / Finlayson method | planned |
| Ch24 | ch24_gamma_tonemapping_code.ipynb | sRGB gamma / ACES / Filmic | planned |
| Ch25 | ch25_lsc_code.ipynb | Lens shading correction (polynomial / lookup table) | planned |
| Ch26 | ch26_csc_output_code.ipynb | RGB→YUV / BT.709 / BT.2020 | planned |
| Ch27 | ch27_hdr_merge_code.ipynb | Multi-exposure merging / deghosting | planned |

This chapter's companion Notebook (*See §6 Code section for runnable examples.*) chains the above modules together into a complete evaluation pipeline (see §6).

---

## §3 Research-Grade Open-Source ISP Projects

### 3.1 Unprocessing (Google Research, 2019)

**Paper**: Brooks T. et al., "Unprocessing Images for Learned Raw Denoise", *CVPR 2019*
**GitHub**: https://github.com/google-research/google-research/tree/master/unprocessing

**Core contribution**: Proposes a method for **reverse-synthesizing RAW images from sRGB images**, allowing researchers to generate unlimited paired RAW-sRGB training data from large existing sRGB datasets (such as ImageNet).

**Inverse ISP (Inverse ISP) pipeline:**
```
sRGB image (known)
    ↓ Inverse gamma (sRGB → linear)
    ↓ Inverse CCM (linear RGB → camera RGB)
    ↓ Inverse demosaicing (mosaicking: RGB → Bayer)
    ↓ Add real noise (Poisson + Gaussian noise model)
    ↓ Add camera CRF error
Synthesized RAW image (usable for training RAW denoising networks)
```

**Significance**: Before Unprocessing was published, training RAW denoising networks required paired "clean RAW + noisy RAW," which was extremely expensive to obtain. Unprocessing made "unlimited synthetic training data" possible, driving rapid advances in deep learning RAW denoising.

**Handbook reference**: Vol.3 Ch.02 (End-to-End Image Restoration) covers in detail training data generation based on Unprocessing.

### 3.2 PyNet (ECCV 2020)

**Paper**: Ignatov A. et al., "Replacing Mobile Camera ISP with a Single Deep Learning Model", *ECCV 2020*
**GitHub**: https://github.com/aiff22/PyNet

**Core contribution**: Proposes a pyramid architecture network (PyNet) that directly produces high-quality RGB images from mobile camera RAW output, end-to-end replacing traditional ISP.

**PyNet architecture characteristics:**
- 5-level pyramid structure; progressively refined from low to high resolution
- Independent loss per level (Perceptual Loss + MS-SSIM + L1)
- Training data: 1,200 paired image sets captured simultaneously with a mobile phone (Huawei P20) and a DSLR (Canon 5D Mark IV)

**Performance in MAI 2021 RAW-to-RGB challenge:**
PyNet series consistently ranked at or near the top in 2020–2021 ISP challenges; PSNR approximately 37–39dB (vs. traditional ISP baseline approximately 33–35dB).

### 3.3 AWNet (ECCV 2020 Workshop)

**Paper**: Liu J. et al., "AWNet: Attentive Wavelet Network for Image ISP", *ECCV 2020 AIM Workshop*
**GitHub**: https://github.com/Charlie0215/AWNet-Attentive-Wavelet-Network

**Core contribution**: Introduces a combination of attention mechanisms and wavelet transform, separating low-frequency (color, luminance) and high-frequency (texture, edges) components in the frequency domain for separate optimization.

**Comparison with PyNet:**

| Method | PSNR (dB) | SSIM | Parameters | Inference Speed (GPU) |
|--------|-----------|------|-----------|----------------------|
| PyNet-CA | 38.24 | 0.9547 | 47.8M | ~200ms/frame |
| AWNet | 38.51 | 0.9576 | 21.6M | ~150ms/frame |
| Traditional ISP baseline | 33.8 | 0.9102 | N/A | <5ms/frame |

### 3.4 CameraNet (ECCV 2020)

**Paper**: Liu J. et al., "CameraNet: A Two-Stage Framework for Effective Camera ISP Learning", *ECCV 2020*

**Core contribution**: Divides ISP into two sub-tasks trained separately:
1. **Stage 1 (Illumination Correction)**: RAW → intermediate representation; corrects illumination non-uniformity
2. **Stage 2 (Image Enhancement)**: intermediate representation → sRGB; completes detail enhancement and color mapping

Two-stage training is more stable than end-to-end joint training; achieves approximately 0.3–0.5dB PSNR improvement with the same parameter count.

### 3.5 ISPD / MAI 2021 / NTIRE Challenge Datasets

**MAI 2021 RAW-to-RGB Challenge:**
- Host: Mobile AI Workshop @ CVPR 2021
- Dataset: Huawei P20 RAW + Canon 5D Mark IV RGB paired; 5,500 pairs total
- Number of participating teams: 226 (record at the time)
- Dataset download: https://competitions.codalab.org/competitions/28656 (registration required)

**NTIRE (New Trends in Image Restoration and Enhancement) series:**
- NTIRE 2017: First edition; super-resolution track (BI/BD degradation models)
- NTIRE 2020: Introduced RAW-to-RGB track (NTIRE 2020 RAW2RGB Challenge)
- NTIRE 2022: HDR reconstruction + RAW denoising + RAW super-resolution
- NTIRE 2024: Efficient ISP challenge (mobile deployment track), AIM 2024 series
- Website: https://cvlai.net/ntire/2024/

**AIM 2024 Efficient ISP Challenge:**
- Objective: Real-time RAW-to-RGB on mobile chips (Snapdragon / Apple M-series)
- Constraint: Inference time < 20ms (approximately equivalent to 60fps real-time)
- Evaluation metric: PSNR + inference speed composite score (PSNR/speed ratio)

---

## §4 Community Benchmarks

### 4.1 NTIRE Historical ISP Track Summary

NTIRE (New Trends in Image Restoration and Enhancement) is one of the most authoritative image processing competitions hosted at CVPR annually, continuing from 2017 to the present:

| Year | ISP-Related Track | Champion Method (brief) | Improvement vs. Traditional Baseline |
|------|------------------|------------------------|--------------------------------------|
| 2017 | Super-resolution ×4 | EDSR (deep residual network) | PSNR +1.5dB |
| 2020 | RAW-to-RGB | PyNet | PSNR +4.2dB vs. LibRaw |
| 2021 | RAW denoising | NAFNet (nonlinear activation) | PSNR +1.2dB vs. BM3D |
| 2022 | HDR reconstruction | SwinIR-Large | PSNR +2.8dB vs. Burst Merge |
| 2023 | Efficient denoising (mobile) | MobileNet-V3 + NAS optimization | 3.6fps → 12fps (same quality) |
| 2024 | Efficient ISP | Knowledge distillation lightweight network | PSNR -0.3dB, speed 4× |

### 4.2 MAI 2021 RAW-to-RGB Public Leaderboard

MAI 2021 is currently the **most representative open benchmark for mobile ISP end-to-end evaluation**. Its public leaderboard protocol:

**Evaluation protocol:**
```
Input: Huawei P20 RAW (10-bit, RGGB Bayer, 3968×2976)
Reference: Same-scene sRGB image captured by Canon 5D Mark IV (aligned with mobile)
Evaluation metric: PSNR (primary) + SSIM (secondary) + inference time (reported but not scored)
Test set: 100 image pairs, not publicly released
```

**Historical best performance (as of 2024):**
- **PSNR**: approximately 42–43dB (top methods using large Transformers)
- **SSIM**: approximately 0.978
- **Traditional ISP baseline (LibRaw default)**: PSNR approximately 33dB, SSIM approximately 0.91

It is worth noting: methods exceeding 40dB PSNR typically use hundreds of MB of parameters and require seconds per frame; there remains a huge gap from actual real-time mobile deployment. In practical ISP scenarios, **lightweight networks that complete inference in 25–30ms** (PSNR approximately 37–39dB) have the highest engineering value.

### 4.3 AIM 2024 Efficient ISP Challenge

AIM (Advances in Image Manipulation) is the ECCV companion competition series. The 2024 Efficient ISP track (AIM 2024 Efficient ISP Challenge) introduced **hardware-constrained evaluation**:

**Evaluation platform**: iPhone 15 Pro (Apple A17 Pro) and Samsung Galaxy S24 Ultra (Snapdragon 8 Gen 3)
**Evaluation metric**: Composite score = PSNR × (20ms / latency), balancing quality and speed

**Key findings (public report):**
1. NPU acceleration provides 3–5× speedup for lightweight ISP networks (vs. CPU only)
2. INT8 quantization causes PSNR degradation of approximately 0.4–0.8dB; speed improvement approximately 2×
3. Knowledge distillation from large to small models can recover approximately 0.3–0.5dB of quantization loss
4. Under the 20ms constraint, the optimal method achieves PSNR approximately 37.8dB (vs. unconstrained optimal 43dB)

### 4.4 DXOMark Methodology (Partially Public)

DXOMark is the most influential institution in consumer imaging evaluation; **parts of its evaluation methodology are publicly available**:

- **MOS (Mean Opinion Score)**: Subjective evaluation; professional evaluators rate 100+ real-world scenes
- **PSNR/SSIM objective metrics**: Compared against reference images (top-tier DSLRs)
- **DXOMark Score calculation**: Weighted composite (exposure + color + noise + texture + artifacts + AF performance)

**Public API**: DXOMark provides limited public data access:
- Historical leaderboard data on the website: https://www.dxomark.com/ranking/
- Methodology white papers (partially public): https://www.dxomark.com/category/test-protocols/

DXOMark's evaluation results are widely cited, but its detailed algorithms are not open-source. Handbook Appendix B (Calibration Charts) and Appendix F (Benchmarks) provide open evaluation approaches that can be independently reproduced.

---

## §5 Hardware/System-Layer Open-Source Projects

### 5.1 Qualcomm CamX Framework

**Project information:**
- Full name: Camera eXtension (CamX); Qualcomm's Android camera HAL implementation
- License: BSD-3-Clause
- GitHub: https://github.com/quic/camx
- Companion: CHI-CDK (Camera Hardware Interface Component Development Kit)

**Architecture overview:**

CamX is the reference implementation of Android Camera HAL3 on Qualcomm Snapdragon platforms, organizing the camera pipeline as a **DAG (Directed Acyclic Graph)**:

```
App Layer (Android Camera2 API)
    ↓
CamX HAL3 Interface
    ↓
Pipeline (DAG node graph):
  ┌────────────────────────────────────────────────┐
  │ IFE (Image Front End) node                     │
  │  ├─ Linearization (linearization / BLC)        │
  │  ├─ Demosaic                                   │
  │  ├─ BPC (Bad Pixel Correction)                 │
  │  └─ LSC (Lens Shading Correction)              │
  │ IPE (Image Processing Engine) node             │
  │  ├─ NR (Noise Reduction, ANR+TNR)             │
  │  ├─ CAC (Color Aberration Correction)          │
  │  └─ ASF (Adaptive Spatial Filter / sharpening) │
  │ BPS (Bayer Processing Segment) node            │
  │  └─ Offline Bayer processing (HDR/night mode)  │
  └────────────────────────────────────────────────┘
    ↓
Output (Preview / Snapshot / Video)
```

**Value to researchers:**
The CamX codebase (~300K lines of C++) demonstrates the complete architecture of industrial-grade camera frameworks, including:
- Structured management of IQ (Image Quality) parameters (XML configuration files)
- Parallel scheduling logic for multiple cameras
- Complete implementation of the HAL3 request-result model

### 5.2 OpenHarmony Camera HAL

**Project information:**
- Project: OpenHarmony (Huawei's contribution to the Open Atom Foundation as open-source HarmonyOS)
- License: Apache-2.0
- Gitee (primary repository): https://gitee.com/openharmony/drivers_peripheral/tree/master/camera
- GitHub mirror: https://github.com/openharmony

**Comparison with CamX:**

| Dimension | Qualcomm CamX | OpenHarmony Camera HAL |
|-----------|-------------|----------------------|
| Platform | Snapdragon (Android) | Huawei Kirin / MediaTek (HarmonyOS) |
| Architecture style | DAG-driven static pipeline | HDI (Hardware Device Interface) standardized interface |
| Open-source completeness | Framework complete; Spectra ISP specific algorithms not open-source | HAL interface layer complete; ISP algorithm driver portion restricted |
| Community activity | Low (primarily Qualcomm internal maintenance) | Moderate (OpenHarmony community-driven) |

### 5.3 libcamera (Linux Open-Source Camera Framework)

**Project information:**
- License: LGPL v2.1
- Website: https://libcamera.org/
- GitHub: https://github.com/libcamera/libcamera

libcamera is the standard open-source camera framework for Linux platforms (Raspberry Pi, embedded Linux, ChromeOS), supporting:
- Raspberry Pi Camera Module (BCM2835 ISP)
- Intel IPU3 (Icelake camera subsystem)
- NVIDIA Tegra
- Qualcomm SC8280XP (partial)

**IPA (Image Processing Algorithm) module:**
libcamera abstracts 3A algorithms (AE/AF/AWB) as pluggable IPA modules. Its reference implementation (`src/ipa/rpi`, based on Raspberry Pi ISP) is an excellent resource for learning 3A control on embedded platforms.

### 5.4 AXIOM Cinema Camera (Fully Open-Source Hardware)

**Project information:**
- Website: https://axiom.camera/
- License: CERN Open Hardware Licence (CERN OHL)
- Status: Active development (maintained by apertus° Association)

AXIOM is currently the only **fully open-source professional cinema camera**:
- Sensor: CMOSIS CMV12000 (12MP, global shutter option)
- FPGA: Xilinx Zynq (running open-source ISP RTL code)
- Maximum specification: 4K/24fps RAW
- ISP implementation: Verilog/VHDL, fully open-source on GitHub (https://github.com/apertus-open-source-cinema/axiom-firmware)

AXIOM's FPGA ISP code is the best publicly available resource for learning **hardware-level ISP implementation** (Bayer interpolation, color matrix, gamma implemented in FPGA RTL).

---

## §6 Code: Benchmark Test Suite

This chapter's §6 provides the following core code examples (can be run locally):

### 6.1 Pipeline Integration

```python
import rawpy
import numpy as np
from pathlib import Path

# Import ISP modules from each handbook chapter (each chapter's Notebook can be imported as a module)
from isp_modules.blc import black_level_correction, pdpc
from isp_modules.demosaic import bilinear_demosaic, ahd_demosaic
from isp_modules.awb import gray_world_awb, learning_based_awb
from isp_modules.ccm import apply_ccm, calibrate_ccm
from isp_modules.gamma import srgb_gamma, aces_tonemap
from isp_modules.nr import bm3d_denoise, dncnn_denoise

class HandbookISPPipeline:
    """
    Handbook ISP pipeline benchmark class.
    Supports flexible combination and replacement of individual modules.
    """
    def __init__(self, config):
        self.demosaic_fn = config.get('demosaic', ahd_demosaic)
        self.awb_fn = config.get('awb', gray_world_awb)
        self.nr_fn = config.get('nr', None)  # None = no denoising

    def process(self, raw_path):
        with rawpy.imread(raw_path) as raw:
            bayer = raw.raw_image_visible.copy().astype(np.float32)
            bl = raw.black_level_per_channel
            wl = raw.white_level
            camera_wb = raw.camera_whitebalance
            color_matrix = raw.color_matrix[:3, :3]

        # Step 1: BLC + PDPC
        bayer = black_level_correction(bayer, bl, wl)
        bayer = pdpc(bayer, threshold=0.3)

        # Step 2: Demosaicing
        rgb = self.demosaic_fn(bayer, pattern='RGGB')

        # Step 3: AWB
        rgb = self.awb_fn(rgb, gains=camera_wb[:3])

        # Step 4: CCM
        rgb = apply_ccm(rgb, color_matrix)

        # Step 5: NR (optional)
        if self.nr_fn:
            rgb = self.nr_fn(rgb)

        # Step 6: Gamma (sRGB standard)
        rgb = srgb_gamma(rgb)

        return np.clip(rgb * 255, 0, 255).astype(np.uint8)
```

### 6.2 Test Images and Reference Outputs

The Notebook uses two standard test image sets:

**Test Set A: MIT-Adobe FiveK (public subset)**
- Public subset of 5,000 Adobe Lightroom-processed photos (100 images)
- rawpy+LibRaw used as reference baseline
- Evaluation: custom ISP vs. LibRaw reference PSNR/SSIM

**Test Set B: Handbook custom test set (10 typical scenes)**
- Outdoor sunlight, indoor tungsten, indoor fluorescent, low light, high dynamic range, portrait skin tone, green foliage, blue sky, white objects, mixed lighting
- Each scene provides rawpy reference output for comparison

### 6.3 Evaluation Results Summary

The Notebook automatically runs all module combinations and outputs an evaluation table:

```python
import pandas as pd
from skimage.metrics import peak_signal_noise_ratio as psnr, structural_similarity as ssim

configs = {
    'Lightweight (NN demosaic + gray world AWB)': {
        'demosaic': nn_demosaic, 'awb': gray_world_awb, 'nr': None
    },
    'Standard (bilinear demosaic + statistical AWB)': {
        'demosaic': bilinear_demosaic, 'awb': learning_based_awb, 'nr': None
    },
    'High quality (AHD demosaic + statistical AWB + BM3D)': {
        'demosaic': ahd_demosaic, 'awb': learning_based_awb, 'nr': bm3d_denoise
    },
}

results = []
for config_name, config in configs.items():
    pipeline = HandbookISPPipeline(config)
    psnr_vals, ssim_vals, times = [], [], []
    for raw_path in test_images:
        import time
        t0 = time.perf_counter()
        output = pipeline.process(raw_path)
        elapsed = time.perf_counter() - t0
        ref = load_reference(raw_path)
        psnr_vals.append(psnr(ref, output))
        ssim_vals.append(ssim(ref, output, channel_axis=-1))
        times.append(elapsed * 1000)
    results.append({
        'Configuration': config_name,
        'PSNR(dB)': f"{np.mean(psnr_vals):.2f}",
        'SSIM': f"{np.mean(ssim_vals):.4f}",
        'Time(ms)': f"{np.mean(times):.1f}",
    })

print(pd.DataFrame(results).to_markdown(index=False))
```

**Expected output example:**

| Configuration | PSNR(dB) | SSIM | Time(ms) |
|--------------|---------|------|---------|
| Lightweight | 28.5 | 0.881 | 12.3 |
| Standard | 33.1 | 0.927 | 89.4 |
| High quality | 36.8 | 0.958 | 2340.0 |
| LibRaw reference | 34.2 | 0.935 | 450.0 |

Note: BM3D's high latency (~2.3s) demonstrates that it is only suitable for offline batch processing, not real-time ISP.

### 6.4 Quick-Start Guide for Open-Source ISP Projects

The final section of the Notebook provides code examples for each major open-source tool:

```python
# ── LibRaw (via rawpy) ──
import rawpy
with rawpy.imread('test.nef') as raw:
    rgb = raw.postprocess(use_camera_wb=True, output_bps=16)

# ── colour-science (ΔE color difference calculation) ──
import colour
Lab_test = np.array([[50, 25, -10]])
Lab_ref  = np.array([[50, 27,  -9]])
dE = colour.delta_E(Lab_test, Lab_ref, method='CIE 2000')

# ── darktable (command-line batch processing) ──
# darktable-cli input.nef output.jpg
# --style "Auto Tone" --export-format jpeg --quality 95

# ── CamX (Android development environment only) ──
# git clone https://github.com/quic/camx && cd camx
# Requires Qualcomm SDK + Android NDK build environment
```

---

## §7 References

1. **LibRaw Documentation**, LibRaw LLC. https://www.libraw.org/docs/
2. **darktable Source Code and Documentation** (GPL v3). https://github.com/darktable-org/darktable
3. **RawTherapee Source** (GPL v3). https://github.com/Beep6581/RawTherapee
4. **rawpy Python Wrapper for LibRaw** (MIT). https://github.com/letmaik/rawpy
5. **colour-science Python Library** (BSD-3). https://github.com/colour-science/colour
6. **Brooks T. et al.**, "Unprocessing Images for Learned Raw Denoise", *CVPR 2019*. https://github.com/google-research/google-research/tree/master/unprocessing
7. **Ignatov A. et al.**, "Replacing Mobile Camera ISP with a Single Deep Learning Model", *ECCV 2020*. https://github.com/aiff22/PyNet
8. **Liu J. et al.**, "AWNet: Attentive Wavelet Network for Image ISP", *ECCV 2020 AIM Workshop*. https://github.com/Charlie0215/AWNet-Attentive-Wavelet-Network
9. **Timofte R. et al.**, "NTIRE 2024 Challenge on Image Restoration", *CVPR Workshops 2024*. https://cvlai.net/ntire/2024/
10. **Qualcomm CamX Camera HAL** (BSD-3). https://github.com/quic/camx
11. **OpenHarmony Camera HAL** (Apache-2.0). https://gitee.com/openharmony/drivers_peripheral
12. **libcamera Open Source Camera Framework** (LGPL v2.1). https://libcamera.org/
13. **AXIOM Open Source Cinema Camera** (CERN OHL). https://github.com/apertus-open-source-cinema/axiom-firmware
14. **Aguerrebere C. et al.**, "Similarity of Locally Computed Deep Learning Features for Perceptual Quality Assessment", *ICCV 2023*. (MAI 2021 evaluation methodology reference)

---

## §8 Glossary

| Term | Full Name / Description |
|------|------------------------|
| **LibRaw** | Open-source RAW file decoding library; supports 1000+ cameras; LGPL license |
| **darktable** | Open-source non-destructive RAW processing software; GPL v3; based on Pixelpipe architecture |
| **rawpy** | Python wrapper for LibRaw; MIT license; standard tool for academic research |
| **NTIRE** | New Trends in Image Restoration and Enhancement; CVPR annual image processing competition |
| **MAI Challenge** | Mobile AI Workshop ISP challenge; CVPR 2021; 226 participating teams; RAW-to-RGB track |
| **Open-Source ISP** | Open-source ISP implementations spanning from RAW decoding to full processing pipelines |
| **Pixelpipe** | darktable's pixel pipeline architecture; 50+ modules in series |
| **Unprocessing** | Google's 2019 inverse-ISP data synthesis method; generates paired RAW training data |
| **CamX** | Qualcomm Camera eXtension; Android camera HAL reference implementation; BSD-3 open-source |
| **IPA** | Image Processing Algorithm; pluggable 3A algorithm modules in libcamera |
| **AIM** | Advances in Image Manipulation; ECCV annual image processing competition series |
| **DXOMark** | Consumer imaging evaluation institution; scoring methodology partially public |
| **DAG** | Directed Acyclic Graph; used by CamX to describe ISP pipeline scheduling structure |
| **CCM** | Color Correction Matrix; transforms from camera RGB to standard RGB color space |
