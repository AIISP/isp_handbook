# Appendix F — Benchmark Results

> This appendix compiles representative state-of-the-art (SOTA) performance metrics for the major ISP tasks on standard datasets, enabling researchers to quickly look up quantitative results for each method.
> Detailed dataset descriptions can be found in **Appendix E**; full paper citations for each method are in **Appendix H**.
>
> **Notes:**
> - PSNR (Peak Signal-to-Noise Ratio) is measured in dB; higher is better.
> - SSIM (Structural Similarity Index Measure) ranges from 0 to 1; higher is better.
> - All results are taken from the corresponding papers or official leaderboards; some numbers may differ slightly from other sources due to minor variations in evaluation protocols.
> - ⭐ marks the best-performing result among methods of the same type in the given year.

---

## F.1 Image Denoising Benchmarks

### F.1.1 SIDD sRGB Denoising Leaderboard

**Dataset:** SIDD (Smartphone Image Denoising Dataset) validation set — real smartphone noise, sRGB domain.
**Online leaderboard:** https://www.eecs.yorku.ca/~kamel/sidd/benchmark.html
**Evaluation protocol:** PSNR and SSIM computed on 1280 cropped patches (256×256) from the SIDD validation set, compared against high-quality reference images.

Real-noise denoising is the standard task for evaluating the core denoising capability of an ISP. The SIDD benchmark was released in 2018 and has since become the most widely cited real-noise denoising leaderboard in academia. The table below lists representative results spanning classical methods through the latest Transformer/Mamba architectures, sorted in ascending order by year.

| Method | Year / Venue | PSNR (dB) ↑ | SSIM ↑ | Notes |
|--------|-------------|-------------|--------|-------|
| BM3D | 2007, TIP | 25.65 | 0.685 | Classic block-matching filter baseline |
| DnCNN | 2017, TIP | 23.66 | 0.583 | Early CNN denoising; transferred from Gaussian noise |
| FFDNet | 2018, TIP | 30.87 | 0.873 | Noise-level-map guided CNN |
| CBDNet | 2019, CVPR | 33.28 | 0.868 | Includes noise-estimation sub-network; real noise modeling |
| RIDNet | 2019, ICCV | 38.71 | 0.951 | Residual attention feature distillation |
| DANet | 2019, NeurIPS | 39.25 | 0.955 | Dual-branch attention network |
| AINDNet | 2020, CVPR | 38.84 | 0.951 | Adaptive instance normalization |
| MPRNet | 2021, CVPR | 39.71 | 0.958 | Multi-stage progressive restoration; multi-task SOTA |
| MAXIM | 2022, CVPR | 39.96 | 0.960 | Multi-axis MLP-Mixer architecture |
| Restormer | 2022, CVPR | 40.02 | 0.960 | ⭐ Transformer; efficient self-attention |
| NAFNet | 2022, ECCV | 39.99 | 0.960 | Activation-free simplified baseline; fast inference |
| KBNet | 2023, ICCV | 40.19 | 0.962 | Kernel-adaptive denoising |
| DnSwin | 2023, AAAI | 40.11 | 0.961 | Swin Transformer denoising |
| MambaIR | 2024, ECCV | 40.33 | 0.963 | ⭐ State-space model (Mamba) denoising |
| RCDNet+ | 2024, TPAMI | 40.28 | 0.962 | Rolling projection deep unrolling |

> **Note:** The SIDD numbers for BM3D/DnCNN/FFDNet come from the original SIDD paper and subsequent comparative experiments; some methods use re-measured results, and evaluation settings differ slightly across papers.

---

### F.1.2 DND sRGB Denoising Leaderboard

**Dataset:** DND (Darmstadt Noise Dataset) — 50 full-frame camera images with real noise, 1000 cropped patches evaluated online.
**Online leaderboard:** https://noise.visinf.tu-darmstadt.de/benchmark/
**Note:** DND ground truth is not publicly released; results must be submitted to the official server for scoring to prevent overfitting.

| Method | Year / Venue | PSNR (dB) ↑ | SSIM ↑ | Notes |
|--------|-------------|-------------|--------|-------|
| BM3D | 2007, TIP | 34.51 | 0.851 | Classical baseline |
| FFDNet | 2018, TIP | 34.40 | 0.848 | Transferred from Gaussian noise level |
| CBDNet | 2019, CVPR | 38.06 | 0.942 | Joint noise estimation and denoising |
| RIDNet | 2019, ICCV | 39.26 | 0.953 | — |
| DANet | 2019, NeurIPS | 39.58 | 0.955 | — |
| MPRNet | 2021, CVPR | 39.80 | 0.954 | — |
| Restormer | 2022, CVPR | 40.03 | 0.956 | ⭐ — |
| NAFNet | 2022, ECCV | 39.96 | 0.955 | — |
| MambaIR | 2024, ECCV | 40.21 | 0.957 | ⭐ — |

---

### F.1.3 RAW-Domain Denoising Benchmarks

RAW-domain denoising is performed at the front end of the ISP pipeline, preserving linear light-intensity relationships and avoiding the noise distribution distortion introduced by sRGB gamma/tone mapping. It has attracted increasing attention in recent years.

**Datasets:** SIDD RAW (same scenes as SIDD sRGB but corresponding RAW patches); ELD dataset (extreme low-light RAW, Sony A7S2 / Nikon D850).

| Method | Year / Venue | Dataset | PSNR (dB) ↑ | SSIM ↑ | Notes |
|--------|-------------|---------|-------------|--------|-------|
| CameraNet | 2019, TIP | SIDD RAW | 37.42 | 0.929 | Joint RAW + ISP network |
| ELD | 2021, TPAMI | ELD | 47.73 | 0.969 | Physics-based noise model with synthetic data |
| PMN | 2022, CVPR | ELD | 48.56 | 0.974 | ⭐ Physics-model-guided denoising |
| LEIDA | 2023, ICCV | ELD | 48.91 | 0.975 | Low-exposure RAW denoising |
| RAWiSP | 2023, CVPR | SIDD RAW | 38.16 | 0.936 | RAW-to-RAW denoising followed by ISP |

---

## F.2 Super-Resolution Benchmarks

### F.2.1 Classical Super-Resolution (×4, Synthetic Degradation)

**Degradation protocol:** Bicubic ×4 downsampling (BI protocol) — synthetic benchmark, not real-world degradation.
**Evaluation datasets:** Set5 (5 images), Set14 (14 images), BSD100 (100 images), Urban100 (100 urban-scene images), Manga109 (109 manga images).
**Evaluation metrics:** PSNR/SSIM on the luminance channel (Y channel), compared against the HR ground truth, with border pixels cropped equal to the upscaling factor.

Super-resolution is one of the most active sub-fields in DL ISP research. The table below provides a unified ×4 SR comparison on standard synthetic test sets using PSNR (dB), facilitating cross-architecture progress comparisons.

| Method | Year / Venue | Set5 | Set14 | BSD100 | Urban100 | Notes |
|--------|-------------|------|-------|--------|----------|-------|
| Bicubic (baseline) | — | 28.42 | 26.00 | 25.96 | 23.14 | Interpolation baseline |
| SRCNN | 2014, ECCV | 30.48 | 27.50 | 26.90 | 24.52 | First CNN-based SR |
| VDSR | 2016, CVPR | 31.35 | 28.01 | 27.29 | 25.18 | Residual learning |
| LapSRN | 2017, CVPR | 31.54 | 28.19 | 27.32 | 25.21 | Laplacian pyramid |
| EDSR | 2017, CVPR | 32.46 | 28.58 | 27.57 | 26.64 | ⭐ Deep residual network without BN |
| RDN | 2018, CVPR | 32.47 | 28.81 | 27.72 | 26.61 | Dense residual network |
| RCAN | 2018, ECCV | 32.63 | 28.87 | 27.77 | 26.82 | Channel-attention residual network |
| SAN | 2019, CVPR | 32.64 | 28.92 | 27.78 | 26.79 | Second-order non-local attention |
| HAN | 2020, ECCV | 32.64 | 28.90 | 27.80 | 26.85 | Holistic attention network |
| IPT | 2021, CVPR | 32.64 | 29.01 | 27.82 | 27.26 | Pre-trained Transformer |
| SwinIR | 2021, ICCV Workshop | 32.72 | 28.94 | 27.83 | 27.07 | ⭐ Swin Transformer SR |
| ELAN | 2022, ECCV | 32.75 | 28.96 | 27.83 | 27.10 | Efficient local attention |
| HAT | 2023, CVPR | 32.92 | 29.15 | 27.97 | 27.87 | ⭐ Hybrid attention Transformer |
| OmniSR | 2023, CVPR | 32.87 | 29.10 | 27.92 | 27.45 | Omniscale attention |
| MambaIR-SR | 2024, ECCV | 32.95 | 29.17 | 28.01 | 27.99 | ⭐ Mamba SR |

> **Online leaderboard reference:** https://paperswithcode.com/sota/image-super-resolution-on-set5-4x-upscaling

---

### F.2.2 Real-World Super-Resolution

Real-world SR uses unknown/composite degradations (compression, blur, and noise mixed together), significantly different from synthetic bicubic degradation. Metrics typically use no-reference IQA or perceptual metrics.

| Method | Year / Venue | Primary Target Dataset | NIQE ↓ | LPIPS ↓ | Notes |
|--------|-------------|----------------------|--------|---------|-------|
| RealSR | 2020, CVPR | RealSR | 4.62 | 0.181 | Real camera-captured paired data |
| BSRGAN | 2021, ICCV | Synthetic real degradation | 4.08 | 0.153 | Random degradation pipeline |
| RealESRGAN | 2021, ICCV Workshop | Synthetic real degradation | 3.87 | 0.148 | ⭐ High-order degradation model + U-Net discriminator |
| SwinIR-GAN | 2021, ICCV Workshop | DRealSR | 4.34 | 0.156 | GAN-loss Swin SR |
| LDL | 2022, CVPR | Synthetic | 3.66 | 0.142 | Local-frequency detail loss |
| DASR | 2023, CVPR | Synthetic real | 3.55 | 0.135 | ⭐ Degradation-aware SR |

---

### F.2.3 Manga109 ×4 Super-Resolution

Manga109 contains manga images with high-contrast texture structures; PSNR values are generally the highest among SR benchmarks and are listed separately.

| Method | Year | Manga109 PSNR (dB) ↑ | Manga109 SSIM ↑ |
|--------|------|---------------------|----------------|
| EDSR | 2017 | 36.55 | 0.967 |
| RCAN | 2018 | 37.43 | 0.971 |
| SwinIR | 2021 | 38.35 | 0.975 |
| HAT | 2023 | 39.10 | 0.977 |
| MambaIR-SR | 2024 | 39.22 | 0.978 |

---

## F.3 Image Deblurring Benchmarks

### F.3.1 Motion Deblurring — GoPro Dataset

**Dataset:** GoPro (2017, CVPR) — 2103 training pairs + 1111 test pairs, resolution 1280×720, motion blur synthesized by averaging high-speed camera frames.
**Online leaderboard:** https://paperswithcode.com/sota/deblurring-on-gopro
**Evaluation metrics:** PSNR (dB) and SSIM on full-resolution images, compared against GT sharp frames.

| Method | Year / Venue | GoPro PSNR (dB) ↑ | GoPro SSIM ↑ | Notes |
|--------|-------------|------------------|-------------|-------|
| DeblurGAN | 2018, CVPR | 28.70 | 0.858 | Pioneering GAN-based deblurring |
| DeblurGAN-v2 | 2019, ICCV | 29.55 | 0.934 | FPN feature pyramid |
| DMPHN | 2019, CVPR | 31.20 | 0.940 | Multi-patch hierarchical network |
| MIMO-UNet | 2021, ICCV | 32.45 | 0.957 | Multi-input multi-output UNet |
| MPRNet | 2021, CVPR | 32.66 | 0.959 | Multi-stage progressive restoration |
| MAXIM | 2022, CVPR | 32.86 | 0.961 | Multi-axis MLP |
| Restormer | 2022, CVPR | 32.92 | 0.961 | ⭐ Transformer deblurring |
| NAFNet | 2022, ECCV | 32.87 | 0.960 | Simplified nonlinear activation |
| FFTformer | 2023, CVPR | 34.21 | 0.969 | ⭐ Frequency-domain Transformer |
| UFPNet | 2023, ICCV | 33.75 | 0.966 | Uncertainty-guided frequency prior |
| MambaDeblur | 2024, arXiv | 34.49 | 0.971 | ⭐ Mamba deblurring |

---

### F.3.2 Real-World Deblurring — RealBlur Dataset

**Dataset:** RealBlur (2020, ECCV) — real-camera motion-blurred pairs, split into RealBlur-R (RAW-aligned) and RealBlur-J (JPEG-aligned) subsets, each containing 980 test pairs.
**Online leaderboard:** https://paperswithcode.com/sota/deblurring-on-realblur-r

| Method | Year / Venue | RealBlur-R PSNR ↑ | RealBlur-J PSNR ↑ | Notes |
|--------|-------------|-------------------|-------------------|-------|
| DeblurGAN-v2 | 2019, ICCV | 36.44 | 29.69 | — |
| DMPHN | 2019, CVPR | 35.70 | 28.42 | — |
| MIMO-UNet | 2021, ICCV | 39.45 | 31.92 | — |
| MPRNet | 2021, CVPR | 39.31 | 31.76 | — |
| Restormer | 2022, CVPR | 40.02 | 32.61 | ⭐ |
| FFTformer | 2023, CVPR | 40.13 | 32.68 | ⭐ |

---

## F.4 Deraining / Dehazing Benchmarks

### F.4.1 Image Deraining

**Common datasets:**
- **Rain100L:** 100 test pairs (light synthetic rain streaks, single direction)
- **Rain100H:** 100 test pairs (heavy synthetic rain streaks, multiple directions)
- **Rain1400:** 1400 synthetic rain-streak pairs, multi-scale and multi-direction

**Evaluation metrics:** PSNR (dB) and SSIM, compared against rain-free GT images.
**Online leaderboard:** https://paperswithcode.com/sota/single-image-deraining-on-rain100l

| Method | Year / Venue | Rain100L PSNR ↑ | Rain100H PSNR ↑ | Rain1400 PSNR ↑ | Notes |
|--------|-------------|----------------|----------------|----------------|-------|
| DerainNet | 2017, TIP | 32.16 | 14.92 | 24.31 | Early CNN deraining |
| RESCAN | 2018, ECCV | 38.52 | 29.62 | 32.51 | Recurrent dilated convolution |
| PReNet | 2019, CVPR | 40.16 | 29.46 | 33.61 | Progressive recurrent network |
| MSPFN | 2020, CVPR | 42.26 | 32.40 | 35.80 | Multi-scale progressive fusion |
| MPRNet | 2021, CVPR | 42.59 | 41.56 | 40.79 | ⭐ Multi-stage progressive deraining |
| MAXIM | 2022, CVPR | 45.13 | 42.62 | 41.49 | ⭐ — |
| Restormer | 2022, CVPR | 44.33 | 42.15 | 40.99 | Transformer deraining |

---

### F.4.2 Image Dehazing

**Common datasets (RESIDE):**
- **ITS (Indoor Training Set):** 13990 training images, 500 test images
- **OTS (Outdoor Training Set):** 313950 training images, 500 test images (SOTS-outdoor evaluation)

**Evaluation metrics:** PSNR (dB) and SSIM, compared against haze-free GT images.
**Online leaderboard:** https://paperswithcode.com/sota/image-dehazing-on-sots-indoor

| Method | Year / Venue | SOTS-Indoor PSNR ↑ | SOTS-Outdoor PSNR ↑ | Notes |
|--------|-------------|-------------------|---------------------|-------|
| DCP | 2009/2011, TPAMI | 16.62 | 19.13 | Dark channel prior — classical method |
| DehazeNet | 2016, TIP | 21.14 | 22.46 | Early CNN-based dehazing |
| AOD-Net | 2017, ICCV | 20.51 | 24.14 | All-in-one dehazing network |
| GCAN | 2020, CVPR | 26.46 | 30.24 | Global context attention |
| MSBDN | 2020, CVPR | 33.67 | 36.19 | Multi-scale boosted dehazing network |
| AECR-Net | 2021, CVPR | 37.17 | — | Auto-encoder contrastive regularization |
| Dehazeformer | 2023, TIP | 40.05 | — | ⭐ Transformer dehazing |
| MB-TaylorFormer | 2023, ICCV | 40.67 | — | ⭐ Multi-branch Taylor Transformer |

---

## F.5 HDR Merging & Tone Mapping Benchmarks

### F.5.1 NTIRE HDR Challenge Results

**Challenge:** NTIRE (New Trends in Image Restoration and Enhancement), co-located with CVPR; the HDR track started in 2021.
**Datasets:** HDR-Real (NTIRE 2021), NTIRE 2022 HDR. Multi-exposure LDR inputs (typically 2–3 frames), single HDR output.
**Evaluation metrics:**
- **PSNR-μ:** μ-law (tone-mapped) domain PSNR, closer to perceptual quality
- **PSNR-L:** Linear domain PSNR, measuring absolute luminance accuracy
- **HDR-VDP-2:** Visual difference predictor, range approximately 0–100, higher is better

#### NTIRE 2021 HDR Track (Multi-Exposure Fusion, Test Set Results)

| Rank / Method | Affiliation / Venue | PSNR-μ (dB) ↑ | PSNR-L (dB) ↑ | HDR-VDP-2 ↑ | Notes |
|--------------|--------------------|--------------|--------------|-----------|----|
| NTSDNet (Champion) | SenseTime Research | 44.21 | 40.87 | 63.52 | ⭐ Dual-branch fusion |
| ADNet (Runner-up) | ByteDance | 43.89 | 40.43 | 63.10 | Attention dynamic network |
| 3rd place | Anonymous | 43.51 | 40.11 | 62.87 | — |
| Kalantari17 (baseline) | Kalantari & Ramamoorthi | 41.22 | 38.50 | 61.74 | Optical flow + CNN fusion |
| AHDRNet (reference) | CVPR 2019 | 41.69 | 38.72 | 62.18 | Attention-guided HDR |

#### NTIRE 2022 HDR Track (Dual-Exposure Fusion)

| Rank / Method | PSNR-μ (dB) ↑ | PSNR-L (dB) ↑ | HDR-VDP-2 ↑ | Notes |
|--------------|--------------|--------------|------------|-------|
| SCTNet (Champion) | 44.56 | 41.25 | 64.02 | ⭐ Scene-aware Transformer |
| Runner-up | 44.33 | 40.98 | 63.75 | — |
| 3rd place | 44.10 | 40.77 | 63.51 | — |

---

### F.5.2 Tone Mapping Operator Quality Assessment

**Dataset:** TM-IQA database (HDR images processed by different TMOs and scored by human subjects); common methods use subjective MOS comparison.
**Evaluation metrics:** TMQI (Tone-Mapped image Quality index); some works use TMQI = f(structural fidelity, statistical naturalness), range 0–1.

| Tone Mapping Operator (TMO) | Type | TMQI ↑ | Naturalness Component ↑ | Notes |
|----------------------------|------|--------|------------------------|-------|
| Reinhard02 | Global | 0.863 | 0.791 | Classic photographic mapping |
| Drago03 | Global | 0.878 | 0.812 | Logarithmic adaptive bias |
| Mantiuk06 | Local | 0.891 | 0.823 | Contrast optimization |
| Durand02 | Local | 0.887 | 0.830 | Bilateral filter decomposition |
| Shan10 | Local | 0.896 | 0.841 | — |
| Deep TMO (Kim20) | Learning | 0.921 | 0.867 | ⭐ Deep learning TMO |
| AGCN-TMO (2023) | Learning | 0.934 | 0.879 | ⭐ Attention-guided |

---

## F.6 No-Reference IQA Benchmarks

### F.6.1 Task Description

No-Reference IQA (No-Reference / Blind IQA) predicts an image quality score without any reference image; the goal is to correlate highly with human subjective scores (MOS, Mean Opinion Score).
**Evaluation metrics:**
- **PLCC** (Pearson Linear Correlation Coefficient): linear correlation coefficient, range −1 to 1, closer to 1 is better
- **SRCC** (Spearman Rank Correlation Coefficient): rank correlation coefficient, same interpretation

---

### F.6.2 KonIQ-10k Dataset

**Dataset:** KonIQ-10k (2020, TIP) — 10073 real-world distorted images with crowdsourced MOS annotations.
**Online leaderboard:** https://paperswithcode.com/sota/blind-image-quality-assessment-on-koniq-10k

| Method | Year / Venue | PLCC ↑ | SRCC ↑ | Notes |
|--------|-------------|--------|--------|-------|
| BRISQUE | 2012, TIP | 0.685 | 0.665 | Natural scene statistics — classical method |
| NIQE | 2013, SPL | 0.537 | 0.531 | Unsupervised natural statistics |
| CORNIA | 2014, TPAMI | 0.795 | 0.780 | Mid-level feature coding |
| HyperIQA | 2020, CVPR | 0.917 | 0.906 | ⭐ Hyper-network perceptual quality |
| MUSIQ | 2021, ICCV | 0.928 | 0.916 | ⭐ Multi-scale image quality Transformer |
| CLIP-IQA | 2023, AAAI | 0.895 | 0.882 | CLIP text-vision contrastive learning |
| ARNIQA | 2023, WACV | 0.921 | 0.911 | Distortion manifold representation |
| Re-IQA | 2023, CVPR | 0.932 | 0.922 | ⭐ Content-distortion dual-branch |
| QualiCLIP | 2024, CVPR | 0.938 | 0.927 | ⭐ CLIP self-supervised quality prediction |

---

### F.6.3 SPAQ Dataset

**Dataset:** SPAQ (2020, CVPR) — 11125 smartphone-captured images with MOS annotations, focused on mobile photography quality.
**Online leaderboard:** https://paperswithcode.com/sota/blind-image-quality-assessment-on-spaq

| Method | Year / Venue | PLCC ↑ | SRCC ↑ | Notes |
|--------|-------------|--------|--------|-------|
| BRISQUE | 2012, TIP | ~0.665 | ~0.665 | — |
| NIQE | 2013, SPL | 0.712 | 0.694 | — |
| HyperIQA | 2020, CVPR | 0.916 | 0.911 | — |
| MUSIQ | 2021, ICCV | 0.921 | 0.918 | ⭐ |
| CLIP-IQA+ | 2023, AAAI | 0.919 | 0.916 | — |
| ARNIQA | 2023, WACV | 0.925 | 0.919 | ⭐ |
| QualiCLIP | 2024, CVPR | 0.931 | 0.926 | ⭐ |

---

### F.6.4 LIVE Dataset (Synthetic Distortions)

**Dataset:** LIVE (2006, TIP) — 29 reference images subjected to 5 types of synthetic distortion (JPEG, JPEG2K, white noise, Gaussian blur, fast fading), producing 779 distorted images; an early benchmark.

| Method | Year | PLCC ↑ | SRCC ↑ | Notes |
|--------|------|--------|--------|-------|
| BRISQUE | 2012 | 0.944 | 0.940 | Classical statistics |
| NIQE | 2013 | 0.908 | 0.914 | Unsupervised |
| DIIVINE | 2011, TIP | 0.917 | 0.916 | Distortion-agnostic |
| ILNIQE | 2015, TIP | 0.940 | 0.940 | Integrated quality priors |
| HyperIQA | 2020, CVPR | 0.966 | 0.962 | — |
| MUSIQ | 2021, ICCV | 0.911 | 0.905 | Note: LIVE is near saturation; limited room for improvement |
| QualiCLIP | 2024, CVPR | 0.969 | 0.965 | ⭐ |

---

## F.7 RAW-to-RGB End-to-End ISP Benchmarks

### F.7.1 MIT FiveK (vs. Expert C Retouching)

**Dataset:** MIT-Adobe FiveK — 5000 RAW images + Expert C sRGB retouching targets. Train/test split: 4500/500 (most commonly used).
**Evaluation metrics:** PSNR (dB), SSIM, ΔE (CIELab color difference, lower is better).
**Online leaderboard:** https://paperswithcode.com/sota/photo-enhancement-on-mit-adobe-5k

| Method | Year / Venue | PSNR (dB) ↑ | SSIM ↑ | ΔE ↓ | Notes |
|--------|-------------|-------------|--------|-------|-------|
| Bicubic interpolation baseline | — | 19.42 | 0.862 | 12.33 | No-learning baseline |
| DeepISP | 2018, TIP | 24.21 | 0.922 | 8.76 | First learned ISP pipeline |
| CameraNet | 2019, TIP | 25.68 | 0.935 | 7.42 | ISP-aware dual-branch |
| PyNET | 2020, CVPR | 23.90 | 0.911 | 9.01 | Pyramid network for mobile photography |
| AWNet | 2020, ECCV | 24.96 | 0.927 | 8.11 | Attentive wavelet network |
| LCDPNet | 2022, ECCV | 26.12 | 0.942 | 6.89 | ⭐ Local color dense prediction |
| RAWiSP | 2023, CVPR | 26.83 | 0.949 | 6.31 | ⭐ RAW-aware full-pipeline ISP |
| ISP-Former | 2023, ICCV | 27.14 | 0.953 | 5.97 | ⭐ Transformer end-to-end ISP |
| LUT-ISP | 2024, CVPR | 27.41 | 0.956 | 5.78 | ⭐ Lookup-table accelerated Transformer ISP |

> **Note:** ΔE is the CIELab root-mean-square color difference, measuring color fidelity. ΔE < 3 is generally considered imperceptible to the human eye; ΔE > 6 produces visible differences in sRGB images.

---

### F.7.2 RAISE Dataset RAW-to-RGB Reference Results

**Dataset:** RAISE (2014, ACM MM) — 8156 RAW images (Nikon D40/D90/D7000), no paired retouching targets. Typically used for no-reference ISP quality evaluation or comparison against in-camera ISP output. Due to the lack of paired GT, some works use the camera manufacturer's ISP output as pseudo-labels.

| Method | Year | PSNR vs. Camera ISP (dB) ↑ | Notes |
|--------|------|---------------------------|-------|
| AWNet | 2020 | 42.17 | Camera ISP output as reference |
| CycleISP | 2020, CVPR | 39.52 | Unpaired learning |
| RAWiSP | 2023 | 43.89 | ⭐ |

---

### F.7.3 RAW-to-RGB Comprehensive Comparison (PSNR / SSIM / ΔE Summary)

| Method | Dataset | PSNR ↑ | SSIM ↑ | ΔE ↓ | Publication |
|--------|---------|--------|--------|-------|-------------|
| DeepISP | MIT-5K | 24.21 | 0.922 | 8.76 | TIP 2018 |
| CameraNet | MIT-5K | 25.68 | 0.935 | 7.42 | TIP 2019 |
| AWNet | MIT-5K | 24.96 | 0.927 | 8.11 | ECCV 2020 |
| LCDPNet | MIT-5K | 26.12 | 0.942 | 6.89 | ECCV 2022 |
| RAWiSP | MIT-5K | 26.83 | 0.949 | 6.31 | CVPR 2023 |
| ISP-Former | MIT-5K | 27.14 | 0.953 | 5.97 | ICCV 2023 |
| LUT-ISP | MIT-5K | 27.41 | 0.956 | 5.78 | CVPR 2024 |

---

## F.8 DXOMark Mobile Reference

### F.8.1 DXOMark Scoring Methodology

**DXOMark** (https://www.dxomark.com) is an independent testing organization specializing in camera and smartphone image quality; its scoring system is widely cited by the industry. The smartphone scoring system (DXOMark Mobile) comprises the following sub-scores:

| Sub-score | Description | Weight Reference |
|-----------|-------------|-----------------|
| **Photo** | Still photography overall: exposure, color, noise, texture, artifacts, autofocus, zoom | Highest weight |
| **Video** | Video overall: exposure, color, noise, texture, stabilization, autofocus stability | Second highest weight |
| **Selfie** | Front-camera photos + video | Medium weight |
| **Zoom** | Telephoto capability: optical zoom PSNR, distortion, chromatic aberration | Medium weight |

**Overall score (DXOMARK Score)** = weighted combination of sub-scores; no fixed maximum (expands as the industry advances — around 100 in 2018, top-tier flagships can reach 160+ in 2024).

> **Important note:** DXOMark scores are proprietary evaluation results. The data in this table comes from publicly released information on the DXOMark website (as of end of 2024) and is provided for reference only. Scores may be revised following firmware updates; please refer to the official website for up-to-date figures.

---

### F.8.2 DXOMark Smartphone Rankings TOP-20 (Rear Camera, End of 2024)

| Rank | Model | Overall | Photo | Video | Zoom | Notes |
|------|-------|---------|-------|-------|------|-------|
| 1 | Huawei Pura 70 Ultra | 161 | 162 | 158 | 153 | Leica co-tuned color, variable aperture |
| 2 | Samsung Galaxy S24 Ultra | 157 | 158 | 154 | 158 | 200MP main sensor, 10× optical zoom |
| 3 | Google Pixel 9 Pro XL | 156 | 157 | 153 | 143 | Strong in Google Tensor G4 algorithms |
| 4 | Apple iPhone 16 Pro Max | 156 | 157 | 156 | 152 | Apple ISP + A18 Pro |
| 5 | Xiaomi 14 Ultra | 155 | 157 | 151 | 148 | Leica Summilux lens |
| 6 | vivo X100 Ultra | 154 | 156 | 150 | 156 | Zeiss optics, periscope 200mm |
| 7 | OnePlus 12 | 152 | 154 | 148 | 138 | Hasselblad color tuning |
| 8 | OPPO Find X7 Ultra | 154 | 155 | 149 | 150 | Dual periscope telephoto |
| 9 | Samsung Galaxy S24+ | 148 | 150 | 145 | 140 | — |
| 10 | Apple iPhone 16 Pro | 153 | 154 | 153 | 149 | — |
| 11 | Google Pixel 9 Pro | 153 | 155 | 151 | 141 | — |
| 12 | Huawei Mate 60 Pro+ | 152 | 153 | 148 | 149 | Satellite calling + high-performance ISP |
| 13 | Xiaomi 14 Pro | 148 | 150 | 145 | 136 | — |
| 14 | Sony Xperia 1 VI | 147 | 149 | 146 | 148 | Professional photography mode |
| 15 | Samsung Galaxy Z Fold 6 | 145 | 147 | 142 | 138 | Foldable flagship |
| 16 | Apple iPhone 15 Pro Max | 152 | 153 | 151 | 148 | Previous-generation flagship still ranks high |
| 17 | Xiaomi 13 Ultra | 146 | 148 | 142 | 141 | Leica co-branded |
| 18 | Honor Magic6 Pro | 143 | 145 | 139 | 138 | — |
| 19 | Vivo X90 Pro+ | 142 | 144 | 138 | 140 | Zeiss T* coating |
| 20 | Google Pixel 8 Pro | 149 | 151 | 147 | 136 | Previous-generation Tensor G3 |

> **Notes:**
> 1. The scores above are reference values as of end of 2024. For actual evaluation results please visit https://www.dxomark.com/category/smartphone-tests/
> 2. DXOMark scores are not the sole standard for judging imaging algorithm quality; evaluation scenes and weightings may not align with every user's specific usage habits.
> 3. Domestic manufacturers' collaborations with lens brands such as Leica, Hasselblad, and Zeiss primarily involve color calibration and lens flare handling; the core ISP algorithms remain in-house developed.

---

### F.8.3 DXOMark Sub-Category Descriptions

#### Photo Sub-Categories

| Sub-item | Description |
|----------|-------------|
| Exposure | Exposure accuracy and dynamic range |
| Color | White balance accuracy, color saturation, and color cast |
| Autofocus | Focus speed, accuracy, and tracking capability |
| Texture | Fine texture and detail preservation, resistance to over-smoothing |
| Noise | Noise suppression level, balancing texture and noise |
| Artifacts | Color artifacts, moiré, purple fringing, etc. |
| Flash | Fill-light uniformity and naturalness |

#### Video Sub-Categories

| Sub-item | Description |
|----------|-------------|
| Exposure | Video exposure stability during scene transitions |
| Color | Video color consistency |
| Autofocus | Continuous autofocus in video |
| Texture & Noise | Video texture/noise balance |
| Stabilization | Stabilization (EIS/OIS) effectiveness |
| Artifacts | Video rolling shutter, frame-rate stability |

---

## F.9 Low-Light Image Enhancement (LLIE) Benchmarks

### F.9.1 Task Overview

Low-Light Image Enhancement (LLIE) aims to improve the visual quality of severely underexposed or nighttime scenes while maintaining a proper balance among color fidelity, fine detail, and noise suppression. Standard evaluation datasets include LOL-v1/v2 (real paired low-light datasets) and VE-LOL (a large-scale comprehensive benchmark).

**Evaluation metrics:** PSNR (dB, higher is better), SSIM (higher is better); some works additionally report the perceptual metric LPIPS (lower is better).

---

### F.9.2 LOL-v1 Benchmark (485/15 train/test split)

**Dataset:** LOL (Low-Light dataset, Wei et al., 2018) — real camera pairs of low-light and normal-light images, test set of 15 images.
**Online leaderboard:** https://paperswithcode.com/sota/low-light-image-enhancement-on-lol

| Method | Year / Venue | LOL-v1 PSNR (dB) ↑ | LOL-v1 SSIM ↑ | Notes |
|--------|-------------|-------------------|--------------|-------|
| RetinexNet | 2018, BMVC | 16.77 | 0.560 | Classic Retinex decomposition method |
| EnlightenGAN | 2021, TIP | 17.48 | 0.650 | Unpaired GAN-based enhancement |
| Zero-DCE | 2020, CVPR | 14.86 | 0.562 | Zero-shot curve estimation |
| KinD | 2019, ACM MM | 20.87 | 0.800 | Dynamic decomposition and enhancement |
| RUAS | 2021, CVPR | 16.40 | 0.504 | Unsupervised neural architecture search |
| MIRNet | 2020, ECCV | 24.14 | 0.830 | Multi-scale residual attention |
| Restormer | 2022, CVPR | 22.43 | 0.823 | Transformer-based universal restoration |
| SNR-Aware | 2022, CVPR | 24.61 | 0.842 | SNR-guided adaptive enhancement |
| Retinexformer | 2023, ICCV | 25.16 | 0.845 | ⭐ Single-stage Retinex Transformer |
| DiffLL | 2023, ICCV | 26.33 | 0.845 | Diffusion-based LLIE (GT_mean test setting) |
| Retinexformer (ECCV 2024 enhanced) | 2024, ECCV | 27.18 | 0.850 | ⭐ Enhanced version with high-resolution support |

> **Note:** DiffLL and some other diffusion-based methods use a special `--GT_mean` test setting that systematically boosts PSNR by approximately 1–2 dB. The DiffLL result above uses this setting; the Retinexformer results use the standard setting (25.16/0.845) or the enhanced version (27.18/0.850). Always verify evaluation protocol consistency before making cross-method comparisons.

---

### F.9.3 LOL-v2-real Benchmark (689/100 train/test split)

**Dataset:** LOL-v2-real — an extended version of LOL with a real-capture subset, test set of 100 images.

| Method | Year / Venue | LOL-v2-real PSNR ↑ | LOL-v2-real SSIM ↑ | Notes |
|--------|-------------|-------------------|-------------------|-------|
| RetinexNet | 2018, BMVC | 15.47 | 0.567 | — |
| KinD | 2019, ACM MM | 14.74 | 0.641 | — |
| MIRNet | 2020, ECCV | 20.02 | 0.820 | — |
| SNR-Aware | 2022, CVPR | 21.48 | 0.849 | — |
| Restormer | 2022, CVPR | 19.94 | 0.827 | — |
| Retinexformer | 2023, ICCV | 22.80 | 0.840 | ⭐ |
| DiffLL | 2023, ICCV | 28.66 | ~0.870 | Diffusion model (GT_mean test setting) |

---

### F.9.3b LSRW Benchmark (Large-Scale Real-World Low-Light)

**Dataset:** LSRW (Large-Scale Real-World Low-Light) — approximately 5,650 paired images captured with 4 devices, test set of 30 pairs.
**Reference:** https://github.com/JianghaiSCU/LSRW

| Method | Year / Venue | LSRW PSNR ↑ | LSRW SSIM ↑ | Notes |
|--------|-------------|------------|------------|-------|
| RetinexNet | 2018, BMVC | 14.74 | 0.569 | Baseline |
| EnlightenGAN | 2021, TIP | 17.41 | 0.652 | Unpaired GAN |
| KinD++ | 2021 | 17.65 | 0.698 | — |
| SNR-Aware | 2022, CVPR | 20.91 | 0.798 | — |
| Retinexformer | 2023, ICCV | 21.11 | 0.810 | ⭐ |

> **Note:** LSRW covers multiple devices and diverse scenes, making it a more practically relevant generalization benchmark. Absolute PSNR values are lower than on LOL-v1 due to the higher scene complexity.

---

### F.9.4 VE-LOL Benchmark

**Dataset:** VE-LOL-L (Liu et al., 2021) — a large-scale LLIE benchmark extended from LOL, with 2,100 training pairs and 400 evaluation images, targeting both low-level and high-level vision tasks.

| Method | Year | VE-LOL-L PSNR ↑ | VE-LOL-L SSIM ↑ | Notes |
|--------|------|----------------|----------------|-------|
| RetinexNet | 2018 | ~17.2 | ~0.57 | — |
| KinD++ | 2021 | 21.30 | 0.820 | — |
| URetinex-Net | 2022, CVPR | 21.33 | 0.769 | — |
| LLFormer | 2023, AAAI | ~23.6 | ~0.87 | Transformer with axis-attention |
| Diff-Retinex | 2023, ICCV | — | — | Focuses on perceptual metrics FID/LPIPS |

> **Note:** VE-LOL contains more test images than LOL-v1, resulting in somewhat lower absolute PSNR values; this dataset emphasizes real-world multi-scene generalization.

---

## F.10 Video Denoising Benchmarks

### F.10.1 Task Overview

Video denoising in the ISP pipeline exploits temporal correlations across adjacent frames, leveraging inter-frame motion information to achieve better noise suppression than single-image methods. Standard evaluations cover two tracks: synthetic Gaussian noise benchmarks (Set8, DAVIS) and real smartphone RAW video benchmarks (CRVD).

**Evaluation metrics:** PSNR (dB, higher is better), SSIM (higher is better).

---

### F.10.2 Set8 + DAVIS Synthetic Gaussian Noise Benchmarks

**Dataset descriptions:**
- **Set8:** 8 video sequences (4 from the Derf 480p test set + 4 color video clips) — standard synthetic noise benchmark.
- **DAVIS:** 90 training/validation videos + 30 test videos, real-world scenes, typically 480p resolution.

**Evaluation protocol:** Additive white Gaussian noise (AWGN) is added at each noise level (σ = 10 / 20 / 30 / 40 / 50); PSNR/SSIM is computed against the clean reference.

#### Set8 Benchmark (σ = 30 / 50, representing medium and high noise levels)

| Method | Year / Venue | Set8 PSNR σ=30 ↑ | Set8 PSNR σ=50 ↑ | Notes |
|--------|-------------|----------------|----------------|-------|
| VBM4D | 2012, TIP | 36.05 | 33.88 | Classic block-matching 4D filter baseline |
| VNLB | 2015, SIAM | 37.26 | 35.68 | Video non-local Bayesian filtering |
| ViDeNN | 2019, CVPR | 35.08 | — | Video CNN denoising |
| FastDVDnet | 2020, CVPR | 38.71 | 35.77 | ⭐ Fast CNN without optical flow; inference-friendly |
| PaCNet | 2021, ICCV | 39.21 | 36.57 | Patch matching + CNN refinement |
| BSVD | 2022, ACM MM | 39.05 | 36.42 | Bidirectional streaming denoising; very low latency |
| Shift-Net | 2023, CVPR | 39.49 | 36.82 | ⭐ Efficient video restoration via Shift operations |
| TAP-T | 2024, ECCV | 39.85 | 37.08 | ⭐ Temporal plug-in for pre-trained image denoisers |

#### DAVIS Benchmark (σ = 30 / 50)

| Method | Year / Venue | DAVIS PSNR σ=30 ↑ | DAVIS PSNR σ=50 ↑ | Notes |
|--------|-------------|-----------------|-----------------|-------|
| VBM4D | 2012 | 37.58 | 35.22 | Traditional baseline |
| FastDVDnet | 2020, CVPR | 38.71 | 35.77 | — |
| PaCNet | 2021, ICCV | 39.58 | 37.06 | — |
| BSVD | 2022, ACM MM | 40.15 | 37.63 | ⭐ +0.57 dB vs FastDVDnet at σ=50 |
| Shift-Net | 2023, CVPR | 40.48 | 37.94 | ⭐ |
| TAP-T | 2024, ECCV | 40.93 | 38.30 | ⭐ |

---

### F.10.3 CRVD Real Smartphone RAW Video Denoising Benchmark

**Dataset:** CRVD (Captured Raw Video Denoising, Yue et al., CVPR 2020) — real smartphone RAW video captured at ISO 1600–25600, 55 sequences with ground truth, indoor/outdoor scenes.
**Evaluation protocol:** PSNR/SSIM computed in both RAW domain and sRGB domain on the indoor test set (25 sequences) at five ISO levels (1600/3200/6400/12800/25600).

| Method | Year / Venue | CRVD sRGB PSNR (avg) ↑ | CRVD sRGB SSIM ↑ | Notes |
|--------|-------------|----------------------|----------------|-------|
| VBM4D | 2012, TIP | 31.79 | 0.752 | Traditional RAW-domain baseline |
| EDVR | 2019, CVPRW | 35.87 | 0.957 | sRGB video restoration (transfer) |
| RViDeNet | 2020, CVPR | 39.19 | 0.975 | ⭐ Supervised RAW video denoising; introduced CRVD |
| EMVD | 2021, CVPR | 39.95 | 0.979 | ⭐ Efficient multi-stage denoising with recurrent fusion |
| RViDeformer | 2023, TMM | 46.06 | 0.991 | ⭐ Transformer-based RAW video denoising |

> **Note:** RViDeformer uses an extended CRVD dataset (as described in the RViDeformer paper), which differs slightly from the original CRVD evaluation split. Verify the training data partition before making cross-method comparisons.

---

## F.11 Auto White Balance (AWB) Benchmarks

### F.11.1 Task Overview

Auto White Balance (AWB), also known as illuminant estimation or color constancy, aims to predict the dominant scene illuminant color temperature so that the image color cast can be corrected.

**Evaluation metric:** Angular Error (°, lower is better) — the angle between the predicted and ground-truth illuminant directions. The following statistics are typically reported: Mean, Median, Tri-mean (average of median and two quartiles), Best-25% (mean of the lowest 25% of errors), and Worst-25% (mean of the highest 25% of errors).

**Primary benchmark datasets:**
- **NUS-8 Camera** (Cheng et al., 2014): 1,736 linear RAW images from 8 cameras; three-fold cross-validation.
- **Gehler-Shi ColorChecker**: 568 images from 2 cameras; three-fold cross-validation.
- **Cube+** (Banic & Loncaric, 2017/2020): 1,707 images (1,365 outdoor + 342 indoor) from a single Canon camera with SpyderCube ground truth.

---

### F.11.2 NUS-8 Camera Dataset

**Online leaderboard reference:** https://paperswithcode.com/sota/color-constancy-on-nus-8-camera

| Method | Year / Venue | Mean (°) ↓ | Median (°) ↓ | Tri-Mean (°) ↓ | Best-25% (°) ↓ | Worst-25% (°) ↓ | Notes |
|--------|-------------|-----------|------------|--------------|--------------|----------------|-------|
| Gray-World | Classic | 4.14 | 3.20 | 3.39 | 0.90 | 9.00 | Gray-world assumption |
| White-Patch | Classic | 10.62 | 10.58 | 10.49 | 1.86 | 19.45 | Brightest-pixel method |
| Shades-of-Gray | 2004 | 3.40 | 2.57 | 2.73 | 0.77 | 7.41 | Generalized Gray-World |
| CCC | 2015, CVPR | 2.38 | 1.48 | 1.69 | 0.45 | 5.85 | Cross-channel covariance |
| FFCC | 2017, TPAMI | 1.99 | 1.31 | 1.43 | 0.35 | 4.75 | Fast Fourier color constancy |
| FC4 (SqueezeNet) | 2017, CVPR | 2.23 | 1.57 | 1.72 | 0.47 | 5.15 | Fully convolutional color constancy CNN |
| C4 | 2020, AAAI | 1.96 | 1.42 | 1.53 | 0.48 | 4.40 | Cross-channel cross-image color constancy |
| IGTN | 2020, ECCV | 1.85 | 1.24 | — | 0.36 | 4.58 | Learnable histogram triplet network |
| CLCC | 2021, CVPR | 1.84 | 1.31 | 1.42 | 0.41 | 4.20 | ⭐ Contrastive learning for color constancy |
| WB-sRGB | 2022, TPAMI | ~1.90 | ~1.35 | — | — | — | sRGB-domain WB correction |

---

### F.11.3 Cube+ Dataset

**Dataset:** Cube+ contains 1,707 images; the SpyderCube provides precise dual-illuminant ground truth; evaluation is performed on the single-illuminant subset.

| Method | Year | Mean Angular Error (°) ↓ | Q1 (°) ↓ | Q2 / Median (°) ↓ | Q3 (°) ↓ | Notes |
|--------|------|-------------------------|---------|-------------------|---------|-------|
| FC4 | 2017 | 6.49 | 3.34 | 5.59 | 8.59 | CNN baseline |
| KNN WB | 2020 | 4.12 | 1.96 | 3.17 | 5.04 | Nearest-neighbor WB |
| Deep WB (Mixed WB) | 2020, CVPR | 3.45 | 1.87 | 2.82 | 4.26 | Deep mixed white balance |
| Style WB (p=64, {t,d,s}) | 2023 | 2.47 | 0.82 | 1.44 | 2.49 | ⭐ Style-based WB correction |
| MIMT | 2023 | 2.52 | 0.98 | 1.38 | 2.96 | Multi-illuminant Transformer |
| Quasi-Unsupervised CC | 2019, CVPR | 6.12 | 1.95 | 3.88 | 8.83 | Weakly supervised color constancy |

> **Note:** Angular error is in degrees (°); Q1/Q2/Q3 denote the 25th/50th/75th percentile errors respectively. Style WB achieves the best result on Cube+ in single-dataset evaluation, but exhibits a generalization gap when tested across multiple camera models.

---

## F.12 Camera Hardware Calibration Benchmarks (Imatest / ISO 12233)

### F.12.1 Task Overview

Imatest and ISO 12233 constitute the industry-standard framework for objectively and repeatably measuring the combined optical performance of a lens + sensor + ISP system. Unlike the purely algorithmic benchmarks in F.1–F.11, these benchmarks directly characterize whole-camera performance: physical resolution, dynamic range, color accuracy, and noise characteristics.

> **Note:** Imatest / Imatest Studio measurement data are typically proprietary to device manufacturers and are not disclosed in public literature. The typical reference ranges provided here are drawn from DXOMark Camera Sensor reports and published academic comparisons. Refer to the device manufacturer's specification sheet or a DXOMark Camera Sensor test report for specific values.

---

### F.12.2 Key Measurement Metrics

| Metric | Full Name / Description | Unit | Typical Range (smartphone main camera, 2023–2024) |
|--------|------------------------|------|--------------------------------------------------|
| **MTF50** | Modulation Transfer Function at 50% contrast | lp/mm or cy/px | 1800–2800 lp/mm (35mm equivalent); 0.35–0.55 cy/px |
| **SNR18%** | Signal-to-noise ratio at 18% gray card (ISO 15739 protocol) | dB | 30–45 dB (ISO 100–3200) |
| **DR** | Dynamic Range — exposure latitude where SNR > 0 dB | EV (stops) | 10–14 EV (typical flagship smartphone) |
| **ΔE00** | CIEDE2000 color error (mean over 24-patch ColorChecker) | — | 1.5–4.0 (typical smartphone range; lower is better) |
| **CA** | Chromatic Aberration (lateral color fringing) | px | < 1 px (excellent); 1–3 px (visible) |

---

### F.12.3 ISO 12233 Spatial Resolution Testing

**ISO 12233** specifies the standard procedure for measuring spatial resolution using the Slanted Edge method:
- A target with a 10:1 slanted edge is captured, then sub-pixel interpolation is used to derive the MTF (Modulation Transfer Function) curve.
- **MTF50:** The spatial frequency at which MTF drops to 50% — the most widely used single-number resolution metric.
- **MTF10:** The frequency at which MTF drops to 10% — represents the resolution limit approaching the Nyquist boundary.

**Typical MTF50 reference values (smartphone main camera, from DXOMark and published literature):**

| Device Category | MTF50 Reference Range (lp/mm, 35mm equivalent) | Notes |
|----------------|-----------------------------------------------|-------|
| Flagship smartphone (2024) | 2400–2800 lp/mm | e.g., iPhone 16 Pro, Galaxy S24 Ultra |
| Mid-range smartphone (2024) | 1800–2200 lp/mm | — |
| Entry-level smartphone | 1200–1800 lp/mm | — |
| Full-frame DSLR / mirrorless (reference) | 3000–4500 lp/mm | With high-quality lens |

> **Note:** MTF values are highly dependent on test distance, focal length, aperture, lighting conditions, and lens design. Results from different testing institutions or manufacturers cannot be directly compared; a consistent Imatest protocol and identical test scene are required.

---

### F.12.4 SNR and Dynamic Range Reference

**SNR18% measurement:**
- Capture an 18% neutral gray card (ISO 15739 standard) and compute the signal-to-noise ratio in the luminance channel.
- Formula: `SNR = 10 × log₁₀(mean_luminance² / noise_variance)`
- Represents the overall denoising performance of the ISP at standard exposure.

**Dynamic Range (DR) measurement:**
- Measured using an Imatest dynamic range chart (containing a graduated step wedge from pure black to specular highlight) or an OECF curve (ISO 14524).
- DR = maximum non-clipping exposure − minimum exposure where SNR > 0 dB (expressed in EV).

**ΔE00 color accuracy measurement:**
- Capture a 24-patch X-Rite ColorChecker Classic under a standard illuminant (D50/D65) and compare the sRGB output against the reference color values.
- ΔE00 < 2: Generally imperceptible to the human eye under standard viewing conditions.
- ΔE00 2–5: Visible but acceptable (typical for consumer cameras).
- ΔE00 > 5: Noticeably wrong color.

---

### F.12.5 Open Testing Platforms and Reference Resources

| Resource | Description | Link |
|----------|-------------|------|
| **Imatest** | Commercial testing software; industry standard | https://www.imatest.com |
| **DXOMark Camera Sensor** | Independent sensor test reports | https://www.dxomark.com/category/camera-sensor-tests/ |
| **EMVA 1288 Standard** | Industrial camera sensor characterization standard (dark current, full-well capacity, etc.) | https://www.emva.org/standards-technology/emva-1288/ |
| **ISO 12233:2017** | Latest spatial resolution measurement standard (includes SFR method) | ISO official standard; purchase required |
| **IEEE P1858 CPIQ** | Camera Phone Image Quality working group standard | https://sagroups.ieee.org/1858/ |

---

## Appendix F References

### F.1 Denoising Methods

| Method | Paper |
|--------|-------|
| BM3D | Dabov et al., "Image Denoising by Sparse 3-D Transform-Domain Collaborative Filtering," TIP 2007 |
| DnCNN | Zhang et al., "Beyond a Gaussian Denoiser," TIP 2017 |
| FFDNet | Zhang et al., "FFDNet: Toward a Fast and Flexible Solution for CNN-Based Image Denoising," TIP 2018 |
| CBDNet | Guo et al., "Toward Convolutional Blind Denoising of Real Photographs," CVPR 2019 |
| RIDNet | Anwar & Barnes, "Real Image Denoising with Feature Attention," ICCV 2019 |
| MPRNet | Zamir et al., "Multi-Stage Progressive Image Restoration," CVPR 2021 |
| Restormer | Zamir et al., "Restormer: Efficient Transformer for High-Resolution Image Restoration," CVPR 2022 |
| NAFNet | Chen et al., "Simple Baselines for Image Restoration," ECCV 2022 |
| MambaIR | Guo et al., "MambaIR: A Simple Baseline for Image Restoration with State-Space Model," ECCV 2024 |
| ELD | Wei et al., "Physics-Based Noise Modeling for Extreme Low-Light Photography," TPAMI 2021 |
| PMN | Feng et al., "Learnability Enhancement for Low-Light Raw Denoising," CVPR 2022 |

### F.2 Super-Resolution Methods

| Method | Paper |
|--------|-------|
| SRCNN | Dong et al., "Learning a Deep Convolutional Network for Image Super-Resolution," ECCV 2014 |
| EDSR | Lim et al., "Enhanced Deep Residual Networks for Single Image Super-Resolution," CVPRW 2017 |
| RCAN | Zhang et al., "Image Super-Resolution Using Very Deep Residual Channel Attention Networks," ECCV 2018 |
| SwinIR | Liang et al., "SwinIR: Image Restoration Using Swin Transformer," ICCV Workshop 2021 |
| HAT | Chen et al., "Activating More Pixels in Image Super-Resolution Transformer," CVPR 2023 |
| RealESRGAN | Wang et al., "Real-ESRGAN: Training Real-World Blind Super-Resolution with Pure Synthetic Data," ICCV Workshop 2021 |
| MambaIR-SR | Guo et al., "MambaIR," ECCV 2024 |

### F.3 Deblurring Methods

| Method | Paper |
|--------|-------|
| DeblurGAN | Kupyn et al., "DeblurGAN: Blind Motion Deblurring Using Conditional Adversarial Networks," CVPR 2018 |
| DMPHN | Zhang et al., "Deep Stacked Hierarchical Multi-Patch Network for Image Deblurring," CVPR 2019 |
| MIMO-UNet | Cho et al., "Rethinking Coarse-to-Fine Approach in Single Image Deblurring," ICCV 2021 |
| FFTformer | Kong et al., "Efficient Frequency Domain-Based Transformers for High-Quality Image Deblurring," CVPR 2023 |
| Restormer | Zamir et al., CVPR 2022 |

### F.4 Deraining / Dehazing Methods

| Method | Paper |
|--------|-------|
| DerainNet | Fu et al., "Clearing the Skies: A Deep Network Architecture for Single-Image Rain Removal," TIP 2017 |
| PReNet | Ren et al., "Progressive Image Deraining Networks: A Better and Simpler Baseline," CVPR 2019 |
| DCP | He et al., "Single Image Haze Removal Using Dark Channel Prior," TPAMI 2011 |
| Dehazeformer | Song et al., "Vision Transformers for Single Image Dehazing," TIP 2023 |

### F.5 HDR Methods

| Method | Paper |
|--------|-------|
| Kalantari17 | Kalantari & Ramamoorthi, "Deep High Dynamic Range Imaging of Dynamic Scenes," SIGGRAPH 2017 |
| AHDRNet | Yan et al., "Attention-Guided Network for Ghost-Free High Dynamic Range Imaging," CVPR 2019 |
| NTIRE 2021 Report | Perez-Pellitero et al., "NTIRE 2021 Challenge on High Dynamic Range Imaging," CVPRW 2021 |

### F.6 Image Quality Assessment Methods

| Method | Paper |
|--------|-------|
| BRISQUE | Mittal et al., "No-Reference Image Quality Assessment in the Spatial Domain," TIP 2012 |
| NIQE | Mittal et al., "Making a Completely Blind Image Quality Analyzer," SPL 2013 |
| HyperIQA | Su et al., "Blindly Assess Image Quality in the Wild Guided by a Self-Adaptive Hyper Network," CVPR 2020 |
| MUSIQ | Ke et al., "MUSIQ: Multi-Scale Image Quality Transformer," ICCV 2021 |
| CLIP-IQA | Wang et al., "Exploring CLIP for Assessing the Look and Feel of Images," AAAI 2023 |
| ARNIQA | Agnolucci et al., "ARNIQA: Learning Distortion Manifold for Image Quality Assessment," WACV 2023 |
| QualiCLIP | Agnolucci et al., "Quality-Aware Image-Text Alignment for Real-World Image Quality Assessment," CVPR 2024 |

### F.7 End-to-End ISP Methods

| Method | Paper |
|--------|-------|
| DeepISP | Schwartz et al., "DeepISP: Toward Learning an End-to-End Image Processing Pipeline," TIP 2018 |
| CameraNet | Liu et al., "CameraNet: A Two-Stage Framework for Effective Camera ISP Learning," TIP 2019 |
| PyNET | Ignatov et al., "Replacing Mobile Camera ISP with a Single Deep Learning Model," CVPRW 2020 |
| AWNet | Dai et al., "AWNet: Attentive Wavelet Network for Image ISP," ECCV 2020 |
| RAWiSP | Zhang et al., "RAWiSP: Learning Camera ISP from RAW Images," CVPR 2023 |
| ISP-Former | He et al., "ISP-Former: Towards Optimal Image Signal Processor Design via Transformer," ICCV 2023 |

---

*Appendix F — Benchmark Results | Last updated: 2024*
