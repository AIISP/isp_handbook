# Appendix J — Development Environment Setup and Code Reproduction Guide

> **Version:** v1.0 Draft | **Last Updated:** 2026-06

This appendix provides complete environment configuration steps required to run the code examples in each chapter of the handbook.

---

## J.1 System Requirements

### Prerequisites
- **Operating System:** Ubuntu 20.04/22.04 LTS (recommended); Windows 11 + WSL2; macOS 12+
- **Python:** 3.10+ (conda environment management recommended)
- **CUDA:** 11.8 or 12.1 (required for DL chapters; not required for traditional ISP chapters)
- **Memory:** 16 GB RAM minimum, 32 GB recommended (DL model training)
- **GPU:** NVIDIA GPU (>=8 GB VRAM; RTX 3080/4090 recommended)

---

## J.2 Quick Installation (Recommended Path)

### Step 1 — Create conda Environment

```bash
# Create dedicated environment
conda create -n aiisp python=3.10 -y
conda activate aiisp

# Install CUDA support (if NVIDIA GPU available)
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
```

### Step 2 — Install Handbook Dependencies

```bash
git clone https://github.com/AIISP/isp_handbook.git
cd ISP_handbook
pip install -r code/requirements.txt
```

### Step 3 — Verify Installation

```python
import rawpy
import colour
import cv2
import torch

print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"rawpy: OK")
print(f"colour-science: OK")
```

---

## J.3 Per-Volume Dependency Reference

| Volume | Representative Chapters | Additional Dependencies | Notes |
|--------|------------------------|------------------------|-------|
| Vol. 1 | Sensor Physics, Color Science | rawpy, colour-science | No GPU required |
| Vol. 2 | Traditional ISP Algorithms | opencv-python, scipy | No GPU required |
| Vol. 3 | DL Image Restoration | torch, torchvision, timm | GPU required (>=8 GB) |
| Vol. 3 | Super-Resolution | basicsr, facexlib | ESRGAN requires pre-downloaded weights |
| Vol. 4 | IQA | lpips, piqa | Some metrics require GPU |
| Vol. 5 | Multimodal Models | transformers, diffusers | Large models require 24+ GB VRAM |
| Vol. 6 | Consumer Photography Analysis | rawpy, pillow | No GPU required |

---

## J.4 Raspberry Pi 4B + IMX477 Hardware Validation Environment

Core algorithms in Volume 2 have been validated on a Raspberry Pi 4B + IMX477 camera for real RAW pipeline testing.

### Hardware Configuration
- Raspberry Pi 4B (4 GB RAM)
- Raspberry Pi HQ Camera (IMX477, 12.3 MP, 1/2.3" sensor)
- microSD card (64 GB Class 10)

### Software Installation

```bash
# Install on Raspberry Pi
sudo apt update && sudo apt install -y python3-pip libcamera-apps
pip3 install rawpy numpy matplotlib

# Capture RAW image
libcamera-still --raw -o test.jpg
# Generates test.dng file
```

```python
# Read RAW file
import rawpy
with rawpy.imread('test.dng') as raw:
    print(f"Camera model: {raw.camera_icc_profile}")
    print(f"CFA pattern: {raw.color_desc}")
    print(f"RAW shape: {raw.raw_image.shape}")
    print(f"Black level: {raw.black_level_per_channel}")
    print(f"White level: {raw.white_level}")
```

### Validated Chapters
| Chapter | Validation Status | Notes |
|---------|------------------|-------|
| Vol. 2 ch01 BLC | ✅ Passed | IMX477 OB pixel readout verified |
| Vol. 2 ch05 AWB | 🔄 In Progress | Multi-illuminant testing ongoing |
| Remaining chapters | ⏳ Planned | To be validated by priority |

---

## J.5 Frequently Asked Questions

**Q: rawpy installation fails**
```bash
# Linux: install libraw first
sudo apt install libraw-dev
pip install rawpy

# Windows:
pip install rawpy  # usually works directly
```

**Q: CUDA version mismatch**
```bash
# Check CUDA version
nvcc --version
# Install matching PyTorch version: https://pytorch.org/get-started/locally/
```

**Q: colour-science import error**
```bash
pip install colour-science  # note: package name is colour-science, not colour
```

---

## J.6 Code Validation Status Legend

Code examples in each chapter are annotated with the following validation status markers:

| Marker | Meaning |
|--------|---------|
| ✅ Verified | Code confirmed running on Raspberry Pi / GPU server |
| 🔄 Validating | Logic correct; environment validation in progress |
| ⚠️ Unverified | Legacy marker; deprecated in current version |
| ❌ Known Issue | Known bug exists; see ⚠️ annotations within the chapter |

> **Note:** All 35 companion notebooks have been verified with `jupyter nbconvert --execute` and include complete outputs. Code uses synthetic data only — no external datasets required. If you encounter execution issues, please open an Issue.

---

## Glossary

| Term | Description |
|------|-------------|
| RAW | Unprocessed sensor output before ISP processing |
| DNG | Adobe Digital Negative format; common RAW container |
| CFA | Color Filter Array; e.g., RGGB Bayer pattern |
| OB | Optical Black pixels; used for BLC calibration |
