# Appendix E — Dataset Index | 数据集索引

> Reference table of publicly available datasets used for training, evaluating, and benchmarking ISP algorithms.
> For benchmark results on these datasets, see Appendix F.

---

## E.1 Denoising Datasets

### SIDD — Smartphone Image Denoising Dataset

| Field | Details |
|-------|---------|
| **Dataset** | SIDD (Smartphone Image Denoising Dataset) |
| **Task** | Real-world image denoising |
| **Size** | 30,000 noisy-clean image pairs (320×320 patches); full-size: 160 scene pairs from 5 smartphone cameras |
| **Capture** | 5 smartphone cameras, various ISO (100–3200), multiple lighting conditions |
| **URL** | https://www.eecs.yorku.ca/~kamel/sidd/ |
| **Key metric** | PSNR (dB), SSIM on SIDD validation set (sRGB output) |
| **Notes** | The de facto standard for real-noise denoising benchmarks. Two tracks: sRGB (post-ISP) and RAW (pre-ISP). The SIDD benchmark server hosts an online leaderboard. |

**Used in:** Ch20 (Denoising), Ch34 (DL ISP Overview), Ch35 (E2E Restoration).

---

### DND — Darmstadt Noise Dataset

| Field | Details |
|-------|---------|
| **Dataset** | DND (Darmstadt Noise Dataset) |
| **Task** | Real-world image denoising (sRGB) |
| **Size** | 50 high-resolution images (5336×4008), 1000 patches (512×512) for evaluation |
| **Capture** | 4 consumer cameras; noisy = high-ISO; clean = low-ISO long-exposure reference |
| **URL** | https://noise.visinf.tu-darmstadt.de/ |
| **Key metric** | PSNR, SSIM (online evaluation server — ground truth not public) |
| **Notes** | Ground truth is held on the server; results are submitted for evaluation. Prevents overfitting to test set. Pairs are spatially aligned using homography correction. |
| **License** | Research use only (contact authors for commercial use) |

**Used in:** Ch20 (Denoising).

---

## E.2 RAW Processing Datasets

### MIT FiveK

| Field | Details |
|-------|---------|
| **Dataset** | MIT-Adobe FiveK Dataset |
| **Task** | RAW-to-sRGB / photo retouching; image enhancement |
| **Size** | 5000 RAW images (various cameras); 5 expert-retouched sRGB versions per image |
| **URL** | https://data.csail.mit.edu/graphics/fivek/ |
| **Key metric** | PSNR, SSIM, ΔE against expert C retouching (most commonly used reference) |
| **Notes** | Expert C annotations are the standard reference for learned ISP and photo enhancement papers. Widely used for training RAW-to-RGB learned ISP networks. Input: DNG RAW; Target: Expert C sRGB. |

**Used in:** Ch34 (DL ISP Overview).

---

## E.3 Demosaicing Datasets

### Kodak 24

| Field | Details |
|-------|---------|
| **Dataset** | Kodak PhotoCD Dataset (24 images) |
| **Task** | Demosaic benchmark, image restoration baseline |
| **Size** | 24 lossless PNG images, 768×512 or 512×768 |
| **URL** | http://r0k.us/graphics/kodak/ |
| **Key metric** | PSNR, SSIM on demosaiced output vs. original |
| **Notes** | Classic benchmark. Not captured with a real Bayer CFA — synthetic Bayer patterns are generated from full-color images for demosaic evaluation. Widely used as a general image restoration benchmark. |

**Used in:** Ch19 (Demosaic).

---

### McMaster 18

| Field | Details |
|-------|---------|
| **Dataset** | McMaster Color Image Dataset (18 images) |
| **Task** | CFA demosaicing benchmark |
| **Size** | 18 full-color images, 500×500 |
| **URL** | https://www4.comp.polyu.edu.hk/~cslzhang/CDM_Dataset.htm |
| **Key metric** | CPSNR (color PSNR), SSIM |
| **Notes** | Images selected to contain challenging content for demosaic: fine textures, regular patterns, color edges. Complement to Kodak 24. Standard benchmark for demosaic papers. |

**Used in:** Ch19 (Demosaic).

---

## E.4 Image Quality Assessment Datasets

### LIVE Image Quality Assessment Database

| Field | Details |
|-------|---------|
| **Dataset** | LIVE IQA Database (University of Texas at Austin) |
| **Task** | No-reference and full-reference IQA |
| **Size** | 29 reference images, ~779 distorted images; 5 distortion types: JPEG, JPEG2000, white noise, Gaussian blur, fast fading |
| **URL** | https://live.ece.utexas.edu/research/Quality/subjective.htm |
| **Key metric** | SRCC (Spearman Rank Correlation Coefficient), PLCC (Pearson Linear Correlation Coefficient) vs. DMOS (differential MOS) |
| **Notes** | One of the earliest and most widely cited IQA databases. DMOS (Differential Mean Opinion Score) is the subjective quality annotation. |
| **License** | Free for non-commercial research |

**Used in:** Ch47 (Perceptual IQA).

---

### TID2013

| Field | Details |
|-------|---------|
| **Dataset** | Tampere Image Database 2013 |
| **Task** | Full-reference IQA |
| **Size** | 25 reference images, 3000 distorted images (24 distortion types × 5 levels) |
| **URL** | http://www.ponomarenko.info/tid2013.htm |
| **Key metric** | SRCC, PLCC vs. MOS |
| **Notes** | The most comprehensive traditional IQA dataset. 24 distortion types including noise, compression, geometric, color distortions. MOS collected from 971 observers across 3 countries. |
| **License** | Free for research (CC-style, attribution required) |

**Used in:** Ch47 (Perceptual IQA).

---

### KADID-10k

| Field | Details |
|-------|---------|
| **Dataset** | KADID-10k (Konstanz Image Database) |
| **Task** | Full-reference IQA |
| **Size** | 81 reference images, 10,125 distorted images (25 distortion types × 5 levels) |
| **URL** | https://database.mmsp-kn.de/kadid-10k-database.html |
| **Key metric** | SRCC, PLCC vs. DMOS |
| **Notes** | Largest traditional distortion-based IQA dataset. Crowdsourced via Amazon Mechanical Turk. Covers 25 distortion types including all types in TID2013 plus additional categories. |

**Used in:** Ch47 (Perceptual IQA).

---

## E.5 Super-Resolution Datasets

### DIV2K

| Field | Details |
|-------|---------|
| **Dataset** | DIV2K — Diverse 2K Resolution Dataset |
| **Task** | Image super-resolution (×2, ×3, ×4, ×8) |
| **Size** | 1000 high-resolution images (2K, ~1080p or higher); 800 train / 100 val / 100 test |
| **URL** | https://data.vision.ee.ethz.ch/cvl/DIV2K/ |
| **Key metric** | PSNR (dB), SSIM on Y channel (YCbCr) |
| **Notes** | Standard training dataset for image SR. Downsampled versions are used as LR inputs. Paired with Flickr2K (2650 images) to form DF2K, the most common training set. |

**Used in:** Ch36 (Super Resolution).

---

### RealSR

| Field | Details |
|-------|---------|
| **Dataset** | RealSR — Real-World Super-Resolution Dataset |
| **Task** | Real-world image super-resolution (zoom-based pairs) |
| **Size** | 596 LR-HR image pairs captured at different focal lengths (×2, ×3, ×4) |
| **URL** | https://github.com/csjcai/RealSR |
| **Key metric** | PSNR, SSIM, LPIPS |
| **Notes** | Unlike synthetic SR datasets, RealSR uses a real optical zoom mechanism to capture LR-HR pairs. Aligned using homography. Captures real-world degradation (lens blur, sensor noise, compression). More realistic benchmark than bicubic-downsampled datasets. |

**Used in:** Ch36 (Super Resolution).

---

## E.6 Low-Light Image Enhancement (LLIE) Datasets

### LOL — Low-Light Dataset

| Field | Details |
|-------|---------|
| **Dataset** | LOL (Low-Light dataset) |
| **Task** | Real-world low-light image enhancement (LLIE) |
| **Size** | LOL-v1: 500 pairs (485 train + 15 test); LOL-v2-real: 689 train + 100 test; LOL-v2-synthetic: 900 train + 100 test |
| **Capture** | Real camera paired captures at different exposure settings (low-light / normal-light); v2-synthetic generated via noise synthesis |
| **URL** | https://daooshee.github.io/BMVC2018website/ |
| **Key metric** | PSNR (dB), SSIM vs. normal-light reference |
| **Notes** | The most widely used benchmark for low-light image enhancement. The v1 test set (15 images) shows higher result variance; v2-real (100 images) provides more robust evaluation. Note: methods that use the `--GT_mean` test setting may show systematically inflated PSNR by ~1–2 dB — confirm protocol consistency when comparing results. |

**Used in:** Vol. 3 Ch05 (LLIE). See Appendix F §F.9 for full benchmark rankings.

---

## E.6.1 Recent LLIE Datasets (2023–2024)

### LSRW — Large-Scale Real-World Low-Light Dataset

| Field | Details |
|-------|---------|
| **Dataset** | LSRW (Large-Scale Real-World Low-Light dataset) |
| **Task** | Real-world low-light image enhancement (LLIE), covering diverse indoor and outdoor scenes |
| **Size** | ~5,650 paired images (captured with 4 different devices) |
| **Capture** | Huawei Mate 40 Pro / P40 Pro / Samsung Galaxy S21 Ultra / iPhone 12 Pro Max; paired low-light / normal-light captures |
| **URL** | https://github.com/JianghaiSCU/LSRW |
| **Key metric** | PSNR (dB), SSIM vs. normal-light reference |
| **Notes** | Released in 2022. Multi-device, multi-scene coverage addresses the limited scene diversity of LOL. Test set: 30 pairs. |

**Used in:** Vol. 3 Ch05 (LLIE).

---

## E.7 Image Deblurring Datasets

### GoPro — Motion Deblurring Dataset

| Field | Details |
|-------|---------|
| **Dataset** | GoPro Motion Deblurring Dataset (Nah et al., 2017) |
| **Task** | Image motion deblurring |
| **Size** | 3,214 pairs (2,103 train + 1,111 test), resolution 1280×720 |
| **Capture** | GoPro Hero 4 Black at 240 fps; blurry images synthesized by averaging consecutive frames; corresponding sharp single frame used as ground truth |
| **URL** | https://github.com/SeungjunNah/DeepDeblur-PyTorch |
| **Key metric** | PSNR (dB), SSIM at full resolution vs. ground truth sharp frame |
| **Notes** | The standard benchmark for image deblurring. Blur is synthesized by averaging high-speed video frames — more uniform than real hand-shake blur but still representative of motion blur characteristics. Online leaderboard: https://paperswithcode.com/sota/deblurring-on-gopro |

**Used in:** Vol. 3 Ch02 (E2E Image Restoration). See Appendix F §F.3.1 for full benchmark rankings.

---

### RealBlur — Real-World Motion Deblurring Dataset

| Field | Details |
|-------|---------|
| **Dataset** | RealBlur (Rim et al., ECCV 2020) |
| **Task** | Real-world image motion deblurring |
| **Size** | RealBlur-R (RAW-domain aligned) and RealBlur-J (JPEG-domain aligned): 3,758 train + 980 test pairs each |
| **Capture** | Real camera captures; long/short exposure pairs of static scenes; precisely aligned using homography transform |
| **URL** | https://github.com/rimchang/RealBlur |
| **Key metric** | PSNR (dB), SSIM; reported separately for RealBlur-R and RealBlur-J subsets |
| **Notes** | Compared to GoPro's synthesized blur, RealBlur captures genuine camera shake, better reflecting real-world handheld deblurring difficulty. The two subsets evaluate alignment in RAW and JPEG domains respectively, making it suitable for testing cross-domain generalization. |

**Used in:** Vol. 3 Ch02 (E2E Image Restoration). See Appendix F §F.3.2 for full benchmark rankings.

---

## E.7.1 Video Super-Resolution Datasets

### REDS — Realistic and Diverse Scenes Dataset

| Field | Details |
|-------|---------|
| **Dataset** | REDS (REalistic and Diverse Scenes dataset, Nah et al., CVPRW 2019) |
| **Task** | Video super-resolution (×4), video deblurring |
| **Size** | 300 video clips (240 train + 30 val + 30 test), 100 frames each, resolution 1280×720 (HR) / 320×180 (LR) |
| **URL** | https://seungjunNah.github.io/Datasets/reds_dataset.html |
| **Key metric** | PSNR (dB), SSIM on Y channel |
| **Notes** | Official dataset for NTIRE 2019/2021 Video Restoration Challenges. Contains complex motion, fast blur, and diverse scenes. The REDS4 subset (4 clips) is commonly used as a fast validation set; remaining clips are used for training. |

**Used in:** Vol. 3 Ch03 (Super Resolution), Vol. 3 Ch02 (E2E Image Restoration).

---

### Vimeo-90K — Video Frame Interpolation and Super-Resolution Dataset

| Field | Details |
|-------|---------|
| **Dataset** | Vimeo-90K (Xue et al., IJCV 2019) |
| **Task** | Video super-resolution, video frame interpolation (VFI), video denoising, optical flow estimation |
| **Size** | 89,800 three-frame sequences (3 frames each, 448×256); 64,612 train / 7,824 test |
| **URL** | http://toflow.csail.mit.edu/ |
| **Key metric** | PSNR (dB), SSIM on Y channel |
| **Notes** | High-quality short clips sourced from Vimeo, rigorously filtered for content diversity (varied scenes and motion types). Standard training and evaluation set for video SR (e.g., EDVR, BasicVSR) and video frame interpolation (e.g., DAIN, RIFE). |

**Used in:** Vol. 3 Ch03 (Super Resolution), Vol. 3 Ch02 (E2E Image Restoration).

---

## E.8 Color Constancy / AWB Datasets

### Gehler-Shi (Rendered Spectra Dataset)

| Field | Details |
|-------|---------|
| **Dataset** | Gehler Color Constancy Dataset (also: SFU Grey Ball Dataset, Shi's reannotation) |
| **Task** | Computational color constancy / AWB ground truth |
| **Size** | 568 images (Canon 1D and 5D); per-image ground truth illuminant color |
| **URL** | http://www.cs.sfu.ca/~colour/data/shi_gehler/ |
| **Key metric** | Angular error (degrees) between estimated and ground truth illuminant; Mean, Median, Best 25%, Worst 25% angular error |
| **Notes** | The standard benchmark for color constancy algorithms. Shi re-annotated Gehler's original dataset with more accurate illuminant measurements. Ground truth: RGB of a gray sphere or ColorChecker white patch under scene illuminant. |
| **License** | Research use only |

**Used in:** Ch22 (AWB).

---

## E.9 Dataset Summary Table

| Dataset | Task | Size | Key Metric | URL |
|---------|------|------|-----------|-----|
| SIDD | Real denoising | 30K patches | PSNR/SSIM | york.ca/sidd |
| DND | Real denoising | 1000 patches | PSNR/SSIM | visinf.tu-darmstadt.de |
| RealDN | Real denoising (2023) | ~150 pairs | PSNR/SSIM | github/zhangjin12138 |
| MIT FiveK | RAW-to-RGB | 5000 RAW | PSNR/ΔE | csail.mit.edu |
| Kodak 24 | Demosaic/restoration | 24 images | PSNR/SSIM | r0k.us |
| McMaster 18 | Demosaic | 18 images | CPSNR/SSIM | polyu.edu.hk |
| LIVE | FR+NR IQA | 779 images | SRCC/PLCC | utexas.edu |
| TID2013 | FR IQA | 3000 images | SRCC/PLCC | ponomarenko.info |
| KADID-10k | FR IQA | 10125 images | SRCC/PLCC | mmsp-kn.de |
| DIV2K | Super-resolution | 1000 HR | PSNR/SSIM | ethz.ch |
| RealSR | Real SR | 596 pairs | PSNR/LPIPS | github/csjcai |
| LOL-v1 | Low-light enhancement | 500 pairs | PSNR/SSIM | daooshee.github.io |
| LOL-v2-real | Low-light enhancement | 789 pairs (689 train+100 test) | PSNR/SSIM | daooshee.github.io |
| LSRW | Low-light enhancement (2022) | ~5,650 pairs | PSNR/SSIM | github/JianghaiSCU |
| GoPro | Motion deblurring | 3,214 pairs | PSNR/SSIM | github/SeungjunNah |
| RealBlur | Real motion deblurring | 980 test pairs (×2 subsets) | PSNR/SSIM | github/rimchang |
| REDS | Video SR / deblurring | 300 clips × 100 frames | PSNR/SSIM | seungjunNah.github.io |
| Vimeo-90K | Video SR / interpolation | 89,800 three-frame sequences | PSNR/SSIM | toflow.csail.mit.edu |
| Gehler-Shi | AWB/color constancy | 568 images | Angular error | cs.sfu.ca |

---

## E.10 Dataset Usage Notes

### License Considerations

Most datasets listed here are for **research use only**. Before using any dataset for commercial purposes, verify its license terms. Key points:

- **MIT FiveK:** Research use; check Adobe license for original RAW files.
- **SIDD:** Benchmark server submissions are public; dataset download requires registration.
- **DIV2K:** Free for non-commercial research.
- **Gehler-Shi:** Research use.

### Downloading Datasets

Use the provided URLs. For large datasets (SIDD, DIV2K), consider downloading directly to the server:

```bash
# Example: Download DIV2K train HR (from ETH)
wget http://data.vision.ee.ethz.ch/cvl/DIV2K/DIV2K_train_HR.zip
unzip DIV2K_train_HR.zip -d data/DIV2K/

# Example: Download Kodak 24
for i in $(seq -w 1 24); do
    wget http://r0k.us/graphics/kodak/kodak/kodim${i}.png -P data/kodak/
done
```

### Data Directory Convention

This handbook assumes datasets are stored at:

```
data/
├── sidd/
├── dnd/
├── mit_fivek/
├── kodak/
├── mcmaster/
├── live/
├── tid2013/
├── kadid10k/
├── div2k/
├── realsr/
├── lol/            # LOL-v1 and LOL-v2 (subdirs: v1 / v2-real / v2-synthetic)
├── lsrw/           # LSRW multi-device low-light dataset
├── gopro/          # GoPro deblurring (train/ + test/ subdirs)
├── realblur/       # RealBlur-R and RealBlur-J (subdirs: RealBlur_R / RealBlur_J)
├── reds/           # REDS video SR (train_sharp/ + train_blur/ + val/ + test/ subdirs)
├── vimeo_90k/      # Vimeo-90K (sequences/ subdir)
└── gehler_shi/
```

Update paths in each chapter's notebook accordingly.
