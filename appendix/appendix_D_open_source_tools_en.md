# Appendix D — Open-Source ISP Tools | 开源工具参考

> A curated reference of open-source libraries, frameworks, and repositories for ISP algorithm development, research, and prototyping.

---

## D.1 Core Libraries

### rawpy

| Field | Details |
|-------|---------|
| **Tool** | rawpy |
| **Purpose** | RAW file I/O — decode RAW images from 1000+ camera models; Python wrapper around LibRaw |
| **Language** | Python (C++ backend via LibRaw) |
| **URL** | https://github.com/letmaik/rawpy |
| **ISP Modules** | RAW I/O, BLC, white balance, demosaic (provides access to LibRaw's built-in pipeline) |
| **Install** | `pip install rawpy` |

**Key usage for this handbook:**

```python
import rawpy
import numpy as np

with rawpy.imread('image.dng') as raw:
    # Access raw Bayer data
    bayer = raw.raw_image_visible.copy()
    # Built-in postprocess (LibRaw pipeline)
    rgb = raw.postprocess(use_camera_wb=True, output_bps=16)
    # Access black levels per channel
    black_levels = raw.black_level_per_channel
    # Access white balance multipliers
    wb_gains = raw.camera_whitebalance
```

**Used in chapters:** Ch18 (BLC), Ch19 (Demosaic), Ch22 (AWB), Ch25 (LSC).

---

### colour-science

| Field | Details |
|-------|---------|
| **Tool** | colour-science |
| **Purpose** | Comprehensive color science library: color spaces, chromatic adaptation, color appearance models, spectral data |
| **Language** | Python |
| **URL** | https://github.com/colour-science/colour |
| **ISP Modules** | AWB (chromatic adaptation), CCM, color space transforms, Gamma, IQA (ΔE) |
| **Install** | `pip install colour-science` |

**Key usage:**

```python
import colour

# Color space conversion
XYZ = colour.sRGB_to_XYZ(rgb)
Lab = colour.XYZ_to_Lab(XYZ)

# ΔE₀₀ computation
delta_E = colour.delta_E(Lab_ref, Lab_test, method='CIE 2000')

# Chromatic adaptation (von Kries)
XYZ_adapted = colour.chromatic_adaptation(XYZ, XYZ_w, XYZ_wr, method='Von Kries')

# Correlated Color Temperature from chromaticity
CCT = colour.xy_to_CCT(xy, method='Hernandez 1999')
```

**Used in chapters:** Ch05 (Color Science), Ch22 (AWB), Ch23 (CCM), Ch24 (Gamma).

---

### colour-demosaicing

| Field | Details |
|-------|---------|
| **Tool** | colour-demosaicing |
| **Purpose** | Reference implementations of demosaic algorithms: bilinear, Malvar-He-Cutler, DDFAPD, Menon 2007, and more |
| **Language** | Python |
| **URL** | https://github.com/colour-science/colour-demosaicing |
| **ISP Modules** | Demosaic (Ch19) |
| **Install** | `pip install colour-demosaicing` |

**Key usage:**

```python
import colour_demosaicing as cdm

# Bilinear (baseline)
rgb_bilinear = cdm.demosaicing_CFA_Bayer_bilinear(bayer, 'RGGB')

# Malvar-He-Cutler (better quality, low compute)
rgb_mhc = cdm.demosaicing_CFA_Bayer_Malvar2004(bayer, 'RGGB')

# Menon 2007 (high quality)
rgb_menon = cdm.demosaicing_CFA_Bayer_Menon2007(bayer, 'RGGB')
```

**Used in chapters:** Ch19 (Demosaic).

---

### LibRaw

| Field | Details |
|-------|---------|
| **Tool** | LibRaw |
| **Purpose** | Low-level RAW decoding library supporting 1000+ camera models; C++ library underlying rawpy |
| **Language** | C++ |
| **URL** | https://github.com/LibRaw/LibRaw |
| **ISP Modules** | RAW I/O, BLC, demosaic, white balance, output color space |
| **License** | LGPL v2.1 / CDDL 1.0 |

**Notes:** LibRaw provides the most complete RAW decoder available in open source. It supports DNG, CR2, CR3, NEF, ARW, RAF, RW2, and hundreds of other formats. rawpy provides a Pythonic interface; use LibRaw directly (C++) for production pipelines.

---

### OpenISP

| Field | Details |
|-------|---------|
| **Tool** | OpenISP |
| **Purpose** | Full software ISP pipeline implementation in Python; educational reference for all pipeline stages |
| **Language** | Python |
| **URL** | https://github.com/cruxopen/openISP |
| **ISP Modules** | BLC, PDPC, LSC, Demosaic, Denoise (bilateral), AWB (gray world), CCM, Gamma, CSC — full pipeline |
| **License** | MIT |

**Notes:** OpenISP is an educational pipeline. Each stage is implemented as a standalone Python module with clear inputs/outputs. Useful for understanding the sequential data flow through the ISP pipeline. Not optimized for performance but highly readable.

---

## D.2 RAW Processing Applications

### darktable

| Field | Details |
|-------|---------|
| **Tool** | darktable |
| **Purpose** | Open-source professional RAW photo processor and digital darkroom |
| **Language** | C (with GEGL/GIMP integration), OpenCL acceleration |
| **URL** | https://github.com/darktable-org/darktable |
| **ISP Modules** | Full pipeline: demosaic, denoise, AWB, CCM (color calibration), tone curve, lens correction, HDR |
| **License** | GPL v3 |

**Notes:** darktable's scene-referred workflow implements a modern filmic tone mapping pipeline. Its color calibration module (colorchecker-based) is used by professional photographers. The OpenCL backend provides GPU acceleration for real-time preview. Useful reference for studying production-quality implementations of gamma, tone mapping, and color science.

---

### RawTherapee

| Field | Details |
|-------|---------|
| **Tool** | RawTherapee |
| **Purpose** | Open-source cross-platform RAW image processing software |
| **Language** | C++ |
| **URL** | https://github.com/Beep6581/RawTherapee |
| **ISP Modules** | Demosaic (AMaZE, DCB, LMMSE, etc.), denoise (wavelets), AWB, CCM, tone curves, LSC, chromatic aberration correction |
| **License** | GPL v3 |

**Notes:** RawTherapee implements the AMaZE demosaic algorithm (Adaptive Manifolds for Real-Time High-Dimensional Filtering), considered one of the best quality demosaic algorithms for edge fidelity. Source code is a valuable reference for studying production demosaic implementations.

---

### LibCamera

| Field | Details |
|-------|---------|
| **Tool** | libcamera |
| **Purpose** | Open-source camera framework for Linux; provides camera abstraction layer and 3A control |
| **Language** | C++ |
| **URL** | https://github.com/libcamera-org/libcamera |
| **ISP Modules** | 3A control (AE, AWB, AF), pipeline configuration, camera HAL |
| **License** | LGPL v2.1+ |

**Notes:** libcamera is the standard camera framework in Linux (including Raspberry Pi camera stack). Its 3A control algorithms (AE metering, AWB estimation) are well-documented and represent a clean open-source reference for control loop design. Used in Raspberry Pi HQ Camera, many Linux embedded cameras.

---

## D.3 Notable ISP Algorithm Repositories

### ISP-related GitHub Repositories

| Repository | Purpose | Language | URL | ISP Module |
|-----------|---------|----------|-----|-----------|
| **colour-science** | CCM fitting and color science utilities | Python | https://github.com/colour-science/colour | CCM, AWB |
| **noise2noise** (Lehtinen et al.) | Blind denoising without clean targets | Python/PyTorch | https://github.com/NVlabs/noise2noise | Denoising (Ch20) |
| **NAFNet** | Non-linear Activation Free Network for image restoration | Python/PyTorch | https://github.com/megvii-research/NAFNet | DL Denoising, Deblur (Ch35) |
| **Real-ESRGAN** | Real-world blind super-resolution | Python/PyTorch | https://github.com/xinntao/Real-ESRGAN | Super Resolution (Ch36) |
| **BasicSR** | Basic Super-Resolution / Image Restoration toolkit | Python/PyTorch | https://github.com/XPixelGroup/BasicSR | SR, Denoising, Deblur (Part 3) |
| **IQA-PyTorch** | Image quality assessment metrics: PSNR, SSIM, LPIPS, BRISQUE, NIQE, etc. | Python/PyTorch | https://github.com/chaofengc/IQA-PyTorch | IQA (Ch47, Part 4) |
| **PyNET / AIM Learned ISP** | Google's learned ISP pipeline (Pynet-based) | Python/TF | https://github.com/aiff22/PyNET | DL ISP (Ch34) |
| **rawpy-utils** | Utility scripts for batch RAW processing | Python | https://github.com/letmaik/rawpy | RAW I/O, Pipeline |

---

## D.4 Supporting Tools

### NumPy / SciPy

Used throughout for matrix operations, curve fitting, and signal processing. See Appendix A for the mathematical context.

- **URL:** https://numpy.org / https://scipy.org
- **ISP use:** LSC polynomial fitting (scipy.optimize), CCM least squares (numpy.linalg), MTF computation (scipy.fft)

### OpenCV

- **URL:** https://github.com/opencv/opencv
- **ISP use:** Demosaic (`cv2.cvtColor`), image I/O, morphological operations for PDPC, connected components

### scikit-image

- **URL:** https://github.com/scikit-image/scikit-image
- **ISP use:** SSIM, PSNR, peak signal-to-noise ratio, structural similarity

### Imatest (Reference Tool — Commercial)

While not open-source, Imatest is the industry standard for ISP IQA measurement. Its documentation (https://www.imatest.com/docs/) is publicly available and provides detailed explanations of MTF, noise, color, and distortion measurement methodologies referenced throughout this handbook.

---

## D.5 Installation

Install all Python dependencies used in this handbook:

```bash
pip install -r code/requirements.txt
```

Contents of `code/requirements.txt`:

```
rawpy>=0.20
colour-science>=0.4.3
colour-demosaicing>=0.2.4
numpy>=1.24
scipy>=1.10
matplotlib>=3.7
opencv-python>=4.8
scikit-image>=0.21
torch>=2.0
torchvision>=0.15
lpips>=0.1.4
IQA-pytorch>=0.3.7
jupyter>=1.0
ipywidgets>=8.0
tqdm>=4.65
```
