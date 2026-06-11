# Part 2, Chapter 03: Image Denoising

> **Pipeline position:** After Demosaic (or jointly with Demosaic); before Sharpening
> **Prerequisites:** Chapter 4 (Noise Models), Chapter 19 (Demosaic)
> **Reader path:** Algorithm Engineer, DL Researcher

---

## §1 Theory

### 1.1 Mathematical Framework: MAP Estimation

The goal of image denoising is to recover a clean image $x$ from a noisy observation $y$. Assuming an additive white Gaussian noise (AWGN) model:

$$y = x + n, \quad n \sim \mathcal{N}(0, \sigma^2 I)$$

Under the Bayesian framework, denoising is equivalent to computing the **Maximum A Posteriori (MAP) estimate**:

$$\hat{x} = \arg\max_x \, p(x \mid y) = \arg\max_x \, \left[ \log p(y \mid x) + \log p(x) \right]$$

Taking the negative log transforms this into a minimization problem:

$$\hat{x} = \arg\min_x \left[ -\log p(y \mid x) - \log p(x) \right]$$

where:
- **Data fidelity term** $-\log p(y \mid x)$: under AWGN this equals $\|y - x\|^2 / (2\sigma^2)$, i.e., minimizing reconstruction error
- **Image prior term** $-\log p(x)$: encodes prior knowledge about clean images (smoothness, sparsity, self-similarity, etc.)

Different prior assumptions give rise to different families of denoising algorithms:

| Prior assumption | Corresponding algorithms |
|----------|----------|
| Local smoothness (spatial correlation) | Gaussian filter, Bilateral filter |
| Non-local self-similarity | NLM, BM3D |
| Sparse gradients | Total Variation (TV) |
| Deep learning implicit prior | DnCNN, FFDNet, NAFNet |

### 1.2 Classical Filtering Algorithms

#### 1.2.1 Gaussian Filter (Baseline)

The Gaussian filter is the simplest denoising baseline, assuming local image smoothness:

$$\hat{x}(p) = \frac{1}{W} \sum_{q \in \mathcal{N}(p)} G_s(\|p - q\|) \cdot y(q)$$

where $G_s$ is a Gaussian kernel with standard deviation $\sigma_s$. The Gaussian filter treats all pixels equally, blurring both noise and edges. Its PSNR performance is limited (approximately 28–30 dB at $\sigma=25$).

#### 1.2.2 Bilateral Filter

**Source:** Tomasi & Manduchi, "Bilateral filtering for gray and color images," *ICCV 1998*.

The bilateral filter extends spatial neighborhood weighting with an additional **intensity similarity weight**, so that pixels on opposite sides of an edge automatically contribute less:

$$\text{BF}(p) = \frac{1}{W(p)} \sum_{q \in \mathcal{N}(p)} f_s(\|p - q\|) \cdot f_r(|y(p) - y(q)|) \cdot y(q)$$

$$W(p) = \sum_{q \in \mathcal{N}(p)} f_s(\|p - q\|) \cdot f_r(|y(p) - y(q)|)$$

where:
- $f_s(\|p - q\|) = \exp\!\left(-\frac{\|p-q\|^2}{2\sigma_s^2}\right)$: **spatial weight**, controls the neighborhood range
- $f_r(|y(p) - y(q)|) = \exp\!\left(-\frac{(y(p)-y(q))^2}{2\sigma_r^2}\right)$: **range weight**, controls edge-preservation strength

**Parameter interpretation:**
- $\sigma_s$ (spatial standard deviation): controls the filter radius; larger values smooth over a wider area
- $\sigma_r$ (range standard deviation): controls the edge-preservation threshold; larger $\sigma_r$ approaches a pure Gaussian blur; smaller $\sigma_r$ gives stronger edge preservation but weaker noise suppression

The main artifact of the bilateral filter is **gradient reversal** and **halo**: when the spatial $\sigma_s$ is too large, pixels near a strong edge "contaminate" across the edge due to their still-significant spatial weight, producing bright and dark halos on either side.

#### 1.2.3 Non-Local Means (NLM)

**Source:** Buades, Coll & Morel, "A non-local algorithm for image denoising," *CVPR 2005*.

The core insight of NLM is that natural images contain **non-local repetitive structure** — image patches far apart may have nearly identical texture. By exploiting this non-local self-similarity, many "repeated samples" can be collected to estimate the true value at each pixel.

$$\text{NLM}(p) = \sum_{q \in \mathcal{S}} w(p, q) \cdot y(q)$$

$$w(p, q) = \frac{1}{Z(p)} \exp\!\left(-\frac{\|P(p) - P(q)\|^2}{h^2}\right)$$

where:
- $P(p)$: image patch centered at pixel $p$, typically $7\times7$ or $11\times11$
- $\|P(p) - P(q)\|^2$: **weighted Euclidean distance** between two patches (center pixel weighted more heavily)
- $h$: filter strength parameter (bandwidth), $h = k\sigma$ (empirically $k \approx 0.4$)
- $Z(p)$: normalization constant, $Z(p) = \sum_q w(p,q)$
- $\mathcal{S}$: search window (typically $21\times21$ or the full image)

**MAP interpretation of NLM:** The corresponding prior is a **non-parametric sparse prior**. Averaging $K$ independent identically distributed noise samples reduces the noise variance to $\sigma^2/K$.

**Computational complexity:** Naive implementation is $O(N^2 P^2)$ (where $N$ is the number of pixels and $P$ is the patch size). In practice, FFT-based accelerations or integral image techniques reduce this to $O(N P^2)$.

#### 1.2.4 BM3D: The Best Classical Denoising Algorithm

**Source:** Dabov, Foi, Katkovnik & Egiazarian, "Image denoising by sparse 3D transform-domain collaborative filtering," *IEEE TIP 2007*.

BM3D (Block Matching and 3D Filtering) combines non-local self-similarity with transform-domain sparsity. It has long been the state-of-the-art classical algorithm by PSNR. The algorithm proceeds in two stages:

**Stage 1 — Basic Estimate**

1. **Block Matching:** For each reference block, find $M$ most similar blocks within a search window and stack them into a 3D array $\mathbf{Y}^{3D}$ of shape $(P \times P \times M)$.

2. **3D Transform:** Apply a 3D transform to the stack (2D DCT/Hadamard + 1D Hadamard/DFT): $\hat{\mathbf{Y}}^{3D} = \mathcal{T}_{3D}\{\mathbf{Y}^{3D}\}$

3. **Hard Thresholding:** Apply hard thresholding $\lambda_{3D} \cdot \sigma$ to the transform coefficients: $\hat{\mathbf{X}}^{3D}_{\text{ht}} = \mathcal{H}_{\lambda_{3D}\sigma}\{\hat{\mathbf{Y}}^{3D}\}$

4. **Inverse Transform and Aggregation:** Inverse-transform the denoised coefficients back to the spatial domain; weighted-average overlapping blocks to produce the basic estimate $\hat{x}_{\text{basic}}$.

**Stage 2 — Wiener Filtering Refinement**

Use the Stage 1 result as an estimate of the clean signal power spectrum, then apply Wiener filtering to the original noisy image:

$$W = \frac{|\mathcal{T}_{3D}\{\hat{x}_{\text{basic}}\}|^2}{|\mathcal{T}_{3D}\{\hat{x}_{\text{basic}}\}|^2 + \sigma^2}$$

$$\hat{\mathbf{X}}^{3D}_{\text{wien}} = W \cdot \mathcal{T}_{3D}\{y^{3D}\}$$

Wiener filtering preserves frequency components where signal power is strong and suppresses those dominated by noise. Compared to hard thresholding, it produces smoother results. Final PSNR at $\sigma=25$ reaches approximately 29.7 dB (BSDS68 dataset).

#### 1.2.5 Guided Filter

**Source:** He, Sun & Tang, "Guided Image Filtering," *TPAMI 2013*.

The guided filter assumes that within a local window, the output image is a linear function of a guidance image (typically the input itself or another sharp image):

$$q_i = a_k \cdot G_i + b_k, \quad \forall i \in \omega_k$$

where $G_i$ is the guidance image and $a_k, b_k$ are local linear coefficients in window $\omega_k$, solved by minimizing:

$$E(a_k, b_k) = \sum_{i \in \omega_k} \left[ (a_k G_i + b_k - p_i)^2 + \varepsilon a_k^2 \right]$$

The regularization parameter $\varepsilon$ controls edge-preservation: small $\varepsilon$ gives strong edge preservation (approximating bilateral filtering); large $\varepsilon$ approaches Gaussian smoothing. The key advantages of the guided filter are the absence of gradient reversal artifacts and $O(N)$ runtime via integral images — far faster than the bilateral filter.

### §1.1b Correct Use of Poisson-Gaussian Noise within the AWGN Framework

RAW domain noise follows a Poisson-Gaussian mixture model ($\sigma^2(x) = \alpha x + \beta^2$, where $\alpha$ is the shot noise coefficient and $\beta$ is the read noise standard deviation in DN), whereas the classical algorithms described below (Gaussian filter, bilateral filter, NLM, BM3D) are all derived under the AWGN assumption ($n \sim \mathcal{N}(0, \sigma^2)$). The legitimate bridge for applying these algorithms in the RAW domain is the **Variance Stabilizing Transform (VST)**:

**Anscombe Transform (pure Poisson noise):**
$$f_\text{Anscombe}(x) = 2\sqrt{x + 3/8} \quad \Rightarrow \quad \text{Var}[f] \approx 1 \quad \text{(approximately uniform variance)}$$

**Generalized Anscombe Transform (GAT, Poisson + Gaussian mixture):**
$$f_\text{GAT}(x) = \frac{2}{\alpha}\sqrt{\max\!\left(\alpha x + \beta^2 + \frac{3\alpha^2}{8},\, 0\right)}$$

After applying GAT, the output noise approximately follows $\mathcal{N}(0,1)$, and any AWGN denoiser (BM3D, NLM, etc.) can be applied to the transformed data. The signal is then recovered using the **exact unbiased inverse GAT**. This three-step pipeline of GAT + AWGN denoising + inverse GAT is the academically recognized RAW domain classical denoising baseline [Makitalo & Foi, TIP 2013].

> **Engineering note:** Industrial-grade denoisers such as BM3D-SRGB and CBDNet (Guo 2019) perform equivalent VST steps internally. Applying a fixed-$\sigma$ AWGN filter directly to the RAW domain without VST causes over-smoothing in bright regions (where $\sigma$ is underestimated) and under-denoising in dark regions (where $\sigma$ is overestimated) — a classic calibration artifact.

### 1.3 Deep Learning Methods

#### 1.3.1 DnCNN (Zhang 2017)

**Source:** Zhang, Zuo, Chen, Meng & Zhang, "Beyond a Gaussian Denoiser: Residual Learning of Deep CNN for Image Denoising," *IEEE TIP 2017*.

DnCNN reformulates denoising as **residual learning**: instead of predicting the clean image directly, the network learns to predict the noise $\hat{n} = f_\theta(y)$, and the denoised result is $\hat{x} = y - \hat{n}$.

Network architecture: 17 convolutional layers (Conv + BN + ReLU), with a receptive field covering a $35\times35$ region. Training loss:

$$\mathcal{L}(\theta) = \frac{1}{2N} \sum_{i=1}^N \|f_\theta(y_i) - n_i\|^2 = \frac{1}{2N} \sum_{i=1}^N \|f_\theta(y_i) - (y_i - x_i)\|^2$$

DnCNN achieves approximately 31.73 dB PSNR on BSDS68 at $\sigma=25$, outperforming BM3D by about 2 dB.

#### 1.3.2 FFDNet (Zhang 2018)

**Source:** Zhang, Zuo & Zhang, "FFDNet: Toward a Fast and Flexible Solution for CNN-Based Image Denoising," *IEEE TIP 2018*.

FFDNet's innovation is feeding a **noise level map** $M$ as an additional input to the network, enabling a single model to handle arbitrary noise strengths:

$$\hat{x} = f_\theta(y, M)$$

where $M \in \mathbb{R}^{H/2 \times W/2}$ is a spatially varying downsampled noise map (constant for uniform noise). This design allows FFDNet to handle both AWGN and spatially non-uniform noise (e.g., row noise caused by ISO variation). Additionally, FFDNet uses pixel shuffle to decompose the $H\times W$ image into four $H/2 \times W/2$ sub-images, making it approximately 4× faster than DnCNN.

#### 1.3.3 NAFNet (Chen 2022)

**Source:** Chen, Chu, Zhang & Sun, "Simple Baselines for Image Restoration," *ECCV 2022*.

NAFNet (Nonlinear Activation Free Network) replaces nonlinear activations such as GELU with a **SimpleGate** mechanism:

$$\text{SimpleGate}(X_1, X_2) = X_1 \odot X_2$$

where $X_1, X_2$ are the two halves of a feature map split along the channel dimension, and element-wise multiplication replaces the activation function. NAFNet also uses Layer Normalization and simplified channel attention, achieving state-of-the-art performance on the SIDD dataset (PSNR 40.30 dB) with inference speed superior to comparable models.

#### 1.3.4 CBDNet (Guo 2019)

**Source:** Guo, S., Yan, Z., Zhang, K., Zuo, W. & Zhang, L., "Toward Convolutional Blind Denoising of Real Photographs," *CVPR 2019*.

CBDNet (Convolutional Blind Denoising Network) is designed for **real-world noise** and uses a cascaded dual-network architecture:

1. **Noise Estimation Subnet:** A 5-layer fully convolutional network that predicts a per-pixel noise standard deviation map $\hat{\sigma}(y)$ directly from the noisy input (output has the same spatial resolution as the input, single channel, representing spatially varying noise intensity).
2. **Non-blind Denoising Subnet:** A U-Net that takes $[y, \hat{\sigma}(y)]$ as joint input and outputs the denoised result $\hat{x}$.

**Asymmetric Loss:** The noise estimation subnet is trained with an asymmetric loss that penalizes underestimation more heavily than overestimation (underestimation leads to insufficient denoising, while overestimation has a smaller perceptual impact):

$$\mathcal{L}_\text{asymm} = \left| \alpha - \mathbf{1}_{[\hat{\sigma}(y) < \sigma(y)]} \right| \cdot \left(\hat{\sigma}(y) - \sigma(y)\right)^2, \quad \alpha \in (0.5, 1)$$

A **Total Variation (TV) regularization** term constrains the estimated noise map to be spatially smooth. On real-noise benchmarks (DND and SIDD), CBDNet significantly outperforms traditional methods and symmetric-loss baselines.

#### 1.3.5 Noise2Noise (Lehtinen 2018)

**Source:** Lehtinen et al., "Noise2Noise: Learning Image Restoration without Clean Data," *ICML 2018*.

Noise2Noise establishes an important result: if noise has zero mean ($\mathbb{E}[n]=0$), then training on pairs of independently noisy images of the same clean scene while minimizing mean squared error is equivalent to training with clean supervision. This makes it possible to train denoising networks **without any clean reference images**, dramatically reducing the data collection burden for real-world denoising. Extensions include Noise2Void (single-image self-supervised) and Blind2Unblind.

### 1.4 Algorithm Performance Comparison

The following table compares PSNR performance and engineering characteristics on the BSDS68 dataset (68 BSD test images, the standard grayscale denoising benchmark):

| Method | PSNR @ σ=15 | PSNR @ σ=25 | PSNR @ σ=50 | Speed (CPU/GPU) | Parameters |
|------|------------|------------|------------|----------------|--------|
| Gaussian filter | 26.0 dB | 24.1 dB | 20.8 dB | Very fast / — | 0 |
| Bilateral filter | 31.1 dB | 28.6 dB | 25.7 dB | Medium / — | 2 |
| NLM | 31.7 dB | 29.4 dB | 26.1 dB | Slow / Fast | 2 |
| BM3D | **31.1 dB** | **29.7 dB** | **27.2 dB** | Slow / Medium | — |
| DnCNN | 31.7 dB | 31.7 dB | 29.2 dB | — / Fast | 556K |
| FFDNet | 31.6 dB | 31.2 dB | 29.2 dB | — / Very fast | 486K |
| NAFNet | 33.0 dB† | 31.0 dB† | — | — / Very fast | 17M |

† NAFNet is primarily evaluated on color real-world noise (SIDD); the grayscale BSDS68 figures are from different variants and are given for reference only.

**Summary:** BM3D is the performance ceiling for parameter-free classical algorithms; DnCNN/FFDNet significantly surpass BM3D with modest parameter counts; large models such as NAFNet achieve the best results on real-world noise but carry higher deployment cost.

### 1.5 Joint Demosaicing and Denoising

**Why processing order matters:** In the standard ISP pipeline, applying demosaicing before denoising has a fundamental drawback — demosaicing mixes the noise from individual color channels into other channels, transforming independent per-channel noise into inter-channel correlated noise and making subsequent denoising harder.

**Gharbi 2016 approach:**

**Source:** Gharbi, Chaurasia, Paris & Durand, "Deep Joint Demosaicking and Denoising," *SIGGRAPH Asia 2016*.

This work proposes a single end-to-end CNN that simultaneously performs demosaicing and denoising, taking a RAW Bayer image as input and outputting a clean RGB image. By operating in the Bayer domain, the network avoids the error accumulation of the two-stage pipeline. Experiments show that the joint network surpasses the sequential "demosaic then denoise" strategy by 1–2 dB PSNR in low-SNR (high ISO) scenarios, with fewer color Moire patterns and color artifacts.

### 1.6 Diffusion Model Denoising (2023–2024)

Diffusion models treat denoising as a stochastic process of iteratively recovering a clean image from a noisy observation. They demonstrate perceptual quality improvements over CNNs on real-world noise.

Score-matching based methods [Song et al., ICLR 2021] blend denoising priors with discriminators, showing significant texture-fidelity advantages on real-noise benchmarks such as SIDD.

**IR-SDE (NeurIPS 2023):** An SDE-based image restoration framework that models the degradation process as an Ornstein–Uhlenbeck process, with restoration performed via a reverse SDE:

$$d\mathbf{x}_t = \theta(\mu - \mathbf{x}_t)\,dt + \sigma\,d\mathbf{W}_t$$

where $\mu$ is the mean attractor (the noisy image), $\theta$ is the mean-reversion rate, and $\sigma$ is the diffusion intensity. This formulation allows end-to-end optimization without separating denoiser training from generator training.

**DiffIR-Denoise:** Within the DiffIR (ICCV 2023) framework, the diffusion process operates only on high-frequency residuals; low-frequency structure is predicted directly by a CNN. This reduces sampling steps from ~1000 to 4, providing an ~250× inference speedup, achieving SIDD PSNR 40.47 dB.

**Engineering limitations:** Even at 4 sampling steps, diffusion model inference latency on mobile platforms (e.g., Snapdragon 8 Elite, approximately 49 TOPS by third-party estimates) remains approximately 80–120 ms per frame, making it unsuitable for real-time preview. The typical deployment path is background offline processing or professional modes (Pro/RAW+ scenarios). With INT4 quantization, some platforms can compress 4-step inference to approximately 40 ms.

---

## §2 Calibration

### 2.1 Noise Model Parameterization

Setting the denoising strength depends on accurate sensor noise modeling (see Chapter 4 for details). Real sensor noise approximately follows a **Poisson-Gaussian mixture model**:

$$\text{Var}[y] = \alpha \cdot x + \beta$$

where:
- $\alpha$ (shot noise coefficient): related to Poisson noise from photon counting; increases with analog gain
- $\beta$ (read noise variance): fixed variance from the sensor readout circuit; weakly dependent on ISO

### 2.2 Flat-Field Calibration Procedure

1. **Capture flat-field images:** At each target ISO (e.g., ISO 100/400/800/1600/3200), shoot N frames (N ≥ 20) of a uniformly illuminated white board with no texture.

2. **Compute mean and variance:** For the N-frame sequence at each pixel, compute the mean $\bar{y}$ and variance $\hat{\sigma}^2$.

3. **Fit the noise curve:** Perform a linear fit to the $(\bar{y}, \hat{\sigma}^2)$ scatter, obtaining $(\alpha_\text{ISO}, \beta_\text{ISO})$ for each ISO.

4. **Map to denoising strength:** Convert the fitted noise parameters to the denoiser's strength parameter:
   - For bilateral / NLM: $h = k \cdot \sqrt{\alpha_\text{ISO} \cdot \bar{y} + \beta_\text{ISO}}$ ($k \approx 0.4$)
   - For FFDNet: pass the noise standard deviation map $\sigma(x,y)$ directly as input

### 2.3 Evaluation Benchmark Datasets

| Dataset | Type | Images | Notes |
|--------|------|--------|------|
| BSDS68 | Synthetic AWGN | 68 | Standard grayscale denoising benchmark, σ=15/25/50 |
| Kodak | Synthetic AWGN | 24 | Standard color benchmark |
| SIDD | Real smartphone noise | 320 scenes | Sony IMX series sensors, with ground truth |
| DND | Real camera noise | 50 scenes | Consumer DSLR, online evaluation |

---

## §3 Tuning

### 3.1 Luma vs. Chroma Denoising Strength

The human visual system **tolerates chroma noise far less than luma noise**. Psychophysical research indicates the perceptual threshold for chroma noise is about 1/3–1/2 that for luma noise. When processing in YCbCr:

- Luma (Y) channel: moderate denoising (preserve texture detail)
- Chroma (Cb/Cr) channels: stronger denoising (aggressively suppress color noise)

Typical strength ratio: $h_{\text{chroma}} \approx 1.5 \times h_{\text{luma}}$

### 3.2 ISO-Adaptive Lookup Table

In engineering practice, a lookup table (LUT) mapping ISO to denoising strength is built and accessed at runtime via linear interpolation on the EXIF ISO value:

```
ISO  |  luma_strength  |  chroma_strength  |  spatial_sigma
-----|-----------------|-------------------|---------------
100  |       5         |        8          |      3
400  |      12         |       18          |      5
800  |      20         |       30          |      7
1600 |      30         |       45          |      9
3200 |      45         |       65          |     12
```

Log-linear interpolation between adjacent ISO stops: $h = h_1 \cdot (\text{ISO}/\text{ISO}_1)^{0.5}$

### 3.3 Texture Protection

For detail-rich texture regions (fabric, hair, leaves), excessive denoising causes texture loss. Common strategies:

1. **High-frequency mask:** Compute local high-frequency energy $E = \|\nabla y\|^2$; reduce denoising strength in regions where $E > T_\text{edge}$.
2. **Local variance guidance:** Use smaller $h$ in regions with high local variance (texture) and larger $h$ in flat regions.
3. **Frequency-domain separation:** Control denoising strength independently in each high-frequency subband (wavelet-domain BM3D naturally supports this).

### 3.4 Identifying Over- and Under-Denoising

| Symptom | Diagnostic | Adjustment |
|------|----------|----------|
| Skin / flat surfaces lose texture, look rubbery / waxy | CPIQ texture retention < 0.8 | Reduce $h$; increase texture protection threshold |
| Fine lines / grid patterns disappear | MTFN high-frequency drop | Reduce $h$ |
| Color speckles visible in uniform areas | CPIQ color noise > 1.5 | Increase chroma $h$ |
| Luma grain visible in uniform areas | SNR < 30 dB @ ISO 800 | Increase luma $h$ |

### 3.5 Platform Spatial NR Key Parameter Comparison

Spatial Noise Reduction (SNR) across the three major mobile ISP platforms:

> **Note on parameter names:** The names below are engineering reference names. Actual parameter names in vendor BSPs change across versions. Qualcomm parameters follow the Chromatix tuning system; MTK parameters follow the NDD (Noise Distribution Data) format; HiSilicon names are representative. Always consult the actual SDK documentation for the target BSP version.

| Function | Qualcomm CamX / Chromatix | MTK Imagiq / NDD | HiSilicon |
|----------|--------------------------|-----------------|-----------|
| SNR master switch | `ANR_Enable` | `NREnabled` (NDD bool) | `SNR_Enable` |
| Luma NR strength | `ANR_LumaFilter` (LUT over ISO) | `NRLumaStrength[ISOLevel]` | `SNR_LumaStrength` |
| Chroma NR strength | `ANR_ChromaFilter` (LUT over ISO) | `NRChromaStrength[ISOLevel]` | `SNR_ChromaStrength` |
| Texture protection threshold | `ANR_TextureThreshold` (gradient magnitude) | `NRTextureProtectThr` | `SNR_TextureMask` |
| Filter kernel size | `ANR_FilterKernel` (5/7/9/11×11) | `NRKernelSize` (NDD enum) | `SNR_KernelRadius` |
| Skin protection | `ANR_SkinEnable` + `ANR_SkinMask` | `NRSkinProtect` (NDD bool) | `SNR_FaceSkinProtect` |
| Processing domain | `ANR_ApplyOnRAW` (bool) | `NRApplyDomain` (RAW/YUV) | `SNR_ProcessDomain` |
| ISO adaptive LUT | `ANR_ISOAutoTable` (Chromatix XML) | `NRISOTable` (NDD array) | `SNR_ISOParam[]` |

**Qualcomm Chromatix SNR tuning path (reference naming; actual XSD/XML structure depends on BSP version):**

```
chromatix_anr_ext.xml
├── ANR_Enable        = 1
├── ANR_ISOAutoTable
│   ├── [ISO=100]  LumaFilter=0.30, ChromaFilter=0.45, TextureThr=20
│   ├── [ISO=400]  LumaFilter=0.50, ChromaFilter=0.70, TextureThr=15
│   ├── [ISO=1600] LumaFilter=0.75, ChromaFilter=0.90, TextureThr=10
│   └── [ISO=6400] LumaFilter=0.90, ChromaFilter=1.00, TextureThr=8
├── ANR_SkinEnable    = 1
└── ANR_SkinMaskThreshold = 0.65   # chroma-plane skin ellipse detection threshold
```

> **Tuning note:** Qualcomm's `ANR_TextureThreshold` directly controls the texture/flat-region boundary — set too high and flat regions retain visible grain; set too low and texture regions are over-smoothed (watercolor effect). MTK's `NRTextureProtectThr` uses different units (0–255 integer) and cannot be numerically compared with Qualcomm's gradient-magnitude-based value.

### 3.6 Qualcomm ANR Internal Sub-module Structure

Qualcomm ANR (Advanced Noise Reduction) performs multi-scale filtering on both luma and chroma channels. It consists of four cascaded sub-modules (source: Qualcomm Snapdragon Camera Architecture documentation; Chromatix tuning practice articles, 2024):

| Sub-module | Function | Key parameters |
|------------|----------|----------------|
| **Basic Level** | High/mid/low frequency noise separation filtering; controls overall NR strength | `ANR_BasicLevel_Luma`, `ANR_BasicLevel_Chroma` |
| **Base Functions** | Defines adaptive filter thresholds based on pixel difference; larger pixel difference → lower filter weight | `ANR_BaseFunc_Threshold` (difference threshold, 0–255) |
| **LNR (Lens Noise Reduction)** | Scales Base Functions threshold based on pixel distance from image center; compensates for increased optical noise at lens edges | `ANR_LNR_Enable`, `ANR_LNR_RadiusTable[]` |
| **False Colors** | Detects and removes color noise at edges (pseudo-color), preventing Demosaic residual false colors from being amplified by NR | `ANR_FalseColors_Enable`, `ANR_FalseColors_Strength` |

> **Engineering implication:** LNR makes ANR spatially aware — the denoising threshold at the image corners is automatically relaxed (because lens-edge optical noise is inherently larger), removing the need to manually tune two separate parameter sets. The False Colors sub-module is tightly coupled with Demosaic: when you change the sensor or Demosaic algorithm, recheck `ANR_FalseColors_Strength` first.

### 3.7 Qualcomm HNR (Hybrid Noise Reduction, Snapdragon 845/865+)

**HNR (Hybrid Noise Reduction)** is a frequency-spatial fusion NR module introduced with Snapdragon 845, complementing rather than replacing ANR:

- **Composition:** DCT frequency-domain NR + gradient smoothing + spatial-domain fusion; targets high-frequency luma noise only (does not process chroma)
- **Pipeline position difference:**
  - **Snapdragon 845 / 855:** HNR is at the end of BPS (Blink Processing Stage), effective only on the **capture** path (preview/video do not pass through BPS)
  - **Snapdragon 865+:** HNR moved to the beginning of IPE (Image Processing Engine), effective on **preview, capture, and video** paths
- **Division of labor with ANR:** ANR handles both luma and chroma with broadband spatial filtering; HNR focuses on high-frequency luma noise in the frequency domain. Cascading both produces cleaner high-ISO results.
- **Key parameters:** `HNR_Enable`, `HNR_DCT_Threshold` (DCT coefficient threshold), `HNR_Blend_Ratio` (frequency-domain vs. spatial-domain output blend ratio)

> **Upgrade trap:** When upgrading from 855 to 865 platform, HNR moves from BPS-end to IPE-start, meaning the same HNR parameters will take effect in preview for the first time. If previous tuning only validated capture quality, the preview path may show over-smoothing or high-frequency detail loss. Always re-run the SNR-ISO curve on preview + video paths before shipping.

Source: Qualcomm Snapdragon 865 Camera Architecture Overview; Chromatix ISP ANR/HNR module analysis (CSDN, 2024).

---

## §4 Artifacts

### 4.1 Plastic Skin Effect

**Cause:** Skin texture frequencies overlap with low-frequency noise. Excessive spatial denoising erases micro-texture (pores, fine lines) along with noise.

**Appearance:** Portrait skin appears smooth like plastic or wax, lacking natural texture.

**Mitigation:** Use a skin color detection mask to reduce denoising strength in skin regions; or apply texture synthesis techniques after denoising to compensate.

### 4.2 Watercolor Effect

**Cause:** NLM or BM3D finds many similar patches in fine-texture regions (grass, hair) and performs strong weighted averaging, flattening the random phase of the weak texture and producing regions of uniform color — resembling a watercolor painting.

**Appearance:** Fine texture becomes unnatural, flat color patches that lack realism.

**Mitigation:** Reduce the search window size or the number of similar blocks $M$; introduce adaptive denoising strength in texture regions.

### 4.3 Halo

**Cause:** The bilateral filter's spatial $\sigma_s$ is too large. Near strong edges (e.g., backlit portrait silhouettes), pixels on both sides still carry significant spatial distance weights, causing intensity to "bleed" across the edge and form bright/dark halos.

**Appearance:** Bright or dark bands appear next to high-contrast edges that are inconsistent with the background.

**Mitigation:** Reduce $\sigma_s$; switch to the guided filter (halo-free); skip bilateral filtering in regions with known strong edges.

### 4.4 Color Bleeding

**Cause:** After strong chroma noise reduction, color information diffuses from objects across edges into neighboring areas.

**Appearance:** The color of highly saturated objects (red flowers, blue sky) "bleeds" onto the edges of adjacent objects, forming a colored glow.

**Mitigation:** Apply chroma NR in the YCbCr domain and use luma edges as a guidance image to constrain chroma diffusion; replace pure spatial smoothing with the guided filter.

### 4.5 Fixed Pattern Noise Amplification

**Cause:** The sensor's column/row Fixed Pattern Noise (FPN) is not correctly identified as noise during high-gain denoising and is instead treated as a weak signal — preserved or even enhanced.

**Appearance:** Horizontal or vertical striping appears in uniform regions after denoising, especially visible in shadows.

**Mitigation:** Subtract the calibrated FPN template in the ISP front end (after BLC); or identify the periodic frequency components of FPN in the frequency domain and filter them out separately.

---

## §5 Evaluation

### 5.1 Evaluation Metrics

| Metric | Full name | Range | Notes |
|------|------|------|------|
| PSNR | Peak Signal-to-Noise Ratio | 20–45 dB | Based on MSE; limited correlation with human perception |
| SSIM | Structural Similarity | 0–1 | Considers luminance, contrast, and structure |
| LPIPS | Learned Perceptual Image Patch Similarity | 0–1 (lower is better) | Based on deep features; strongly correlates with human perception |
| NIQE | Natural Image Quality Evaluator | No-reference | Assesses natural statistics; no clean reference needed |

### 5.2 Published PSNR Comparison

**BSDS68 Grayscale Denoising (PSNR, dB):**

| Method | σ=15 | σ=25 | σ=50 | Reference |
|------|------|------|------|----------|
| Gaussian filter | 26.0 | 24.1 | 20.8 | — |
| Bilateral filter | 31.1 | 28.6 | 25.7 | Tomasi 1998 |
| NLM | 31.7 | 29.4 | 26.1 | Buades 2005 |
| BM3D | 31.1 | 29.7 | 27.2 | Dabov 2007 |
| DnCNN | 31.7 | 31.7 | 29.2 | Zhang 2017 |
| FFDNet | 31.6 | 31.2 | 29.2 | Zhang 2018 |
| NAFNet-32 | — | — | — | Chen 2022 |

**SIDD Color Real-Noise Denoising (PSNR, dB):**

| Method | PSNR | SSIM | Reference |
|------|------|------|----------|
| CBM3D | 39.59 | 0.957 | Dabov 2007 |
| DnCNN-C | 38.03 | 0.932 | Zhang 2017 |
| FFDNet-C | 39.99 | 0.960 | Zhang 2018 |
| NAFNet-32 | 40.30 | 0.9700 | Chen 2022 |
| NAFNet-64 | 40.51 | 0.9722 | Chen 2022 |

### 5.3 Noise–Sharpness Trade-off Curve

There is a fundamental **trade-off between noise suppression and detail preservation**. The standard approach is:

1. Run denoising at multiple strength levels $h = [0, 5, 10, 20, 40, 80]$.
2. Compute PSNR (noise score) and MTF50 (sharpness score) at each level.
3. Plot a Pareto frontier with MTF50 on the x-axis and PSNR on the y-axis.

The engineering operating point is typically the "knee" of the Pareto frontier where the absolute slope equals 1 — i.e., the point that yields the maximum noise reduction per unit of sharpness sacrificed.

---

## §6 Code

See *See §6 Code section for runnable examples.*

---

## §7 Multi-Frame NR Implementation Across Platforms

This section compares the multi-frame noise reduction (MFNR) architectures of three major mobile ISP platforms, examining their hardware co-processing, frame alignment, merge strategy, and AI enhancement designs.

### 7.1 Qualcomm MFNR (Multi-Frame Noise Reduction)

- **Architecture:** ZSL (Zero Shutter Lag) ring buffer stores the last N RAW frames continuously
- **Frame count:** Up to 30 frames in night mode (Spectra 580+); typically 4–8 frames for standard shots
- **Alignment:** Hardware optical flow on Hexagon DSP; block-matching with sub-pixel accuracy
- **Merge:** Weighted temporal average in RAW domain; pixel weights based on motion confidence map
- **Noise model:** $\sigma^2(I) = \alpha I + \beta$ (Poisson + read noise); $\alpha, \beta$ calibrated per sensor per ISO, stored in Chromatix
- **Integration with HDR:** MFNR runs within each exposure bracket before HDR merge
- Reference: Qualcomm Snapdragon 8 Gen 1 technical white paper

### 7.2 HiSilicon XD-Fusion MFNR

- **Architecture:** NPU-ISP co-processing; ISP captures RAW frames, NPU handles alignment + merge
- **Frame count:** 4–8 frames standard; extended long exposure for "night mode" (stitches multiple 1-second exposures)
- **Semantic-aware merge:** NPU segments each frame into semantic regions (sky / person / foliage / text); applies different temporal weights per class
  - Static backgrounds: high temporal weight (maximum noise averaging)
  - Moving subjects: low temporal weight (prevent ghosting), compensated by spatial NR
- **AI texture synthesis:** Regions where motion prevents temporal averaging are enhanced by NPU using learned texture priors
- **Noise model:** Similar Poisson-Gaussian model, but noise sigma estimated per-region using NPU-based content analysis
- Reference: Huawei Developer Conference 2020, Kirin 9000 Camera Architecture session

### 7.3 MediaTek AINR (AI Noise Reduction)

- **Architecture:** APU (AI Processing Unit) runs CNN denoising model; ISP handles spatial NR, APU handles AI NR
- **Single-frame AI NR:** CNN denoiser (based on FFDNet/NAFNet architecture) processes Y channel at full resolution; runs at 30fps on APU 6.0
- **Multi-frame path:** MFNR engine aligns 4–8 RAW frames; merged result fed to CNN for final refinement
- **Video NR:** Temporal NR for video uses motion-compensated filtering; AI model runs on consecutive frames with motion vector guidance
- **INT8 quantization:** Model quantized to INT8 for APU deployment; color accuracy preserved by processing in luma-only domain
- Reference: https://www.mediatek.com/technology/imagiq ; Dimensity 9300 AI camera white paper

### 7.4 Platform Comparison

| Feature | Qualcomm MFNR | HiSilicon XD-Fusion | MediaTek AINR |
|---------|--------------|--------------------|--------------------|
| Max frame count | 30 frames (night) | 4–8 frames + long exposure | 4–8 frames + single-frame AI |
| Alignment method | Optical flow (Hexagon DSP) | Optical flow (ISP+NPU) | Motion vectors (hardware) |
| Merge domain | RAW domain | RAW domain + semantic-aware | RAW domain → AI refinement |
| AI enhancement | Post-merge AI denoising | Semantic segmentation-guided merge | CNN denoising (APU) |
| Video support | Temporal filter (TF) | Motion-compensated temporal NR | Real-time AI video NR |
| Night mode strategy | Large frame accumulation | Ultra-long exposure + NPU synthesis | AI single-frame + multi-frame combo |

---

## §8 Glossary

**MAP Estimation (Maximum A Posteriori Estimation)**
Under the Bayesian framework, denoising is equivalent to solving $\hat{x} = \arg\max_x [p(y|x) \cdot p(x)]$, simultaneously maximizing the likelihood (data fidelity) and the prior (image prior). Different prior assumptions — local smoothness, non-local self-similarity, sparse gradients, deep learning implicit priors — give rise to distinct families of denoising algorithms.

**Poisson-Gaussian Noise**
The noise model for real sensors in the RAW domain: $\text{Var}[y] = \alpha x + \beta^2$, where $\alpha$ is the shot noise coefficient (related to the Poisson statistics of photon counting, increasing with gain) and $\beta$ is the read noise standard deviation in DN (weakly dependent on ISO). Compared to pure AWGN, this signal-dependent model more accurately describes how noise varies with signal intensity, and forms the theoretical basis for ISO-adaptive NR strength calibration.

**Bilateral Filter**
An edge-preserving filter proposed by Tomasi & Manduchi (1998) that augments spatial weights with a range weight $f_r$, automatically suppressing contributions from pixels with large intensity differences across edges. Parameters: spatial standard deviation $\sigma_s$ (controls filter radius) and range standard deviation $\sigma_r$ (controls edge preservation strength). Principal defects: gradient reversal and halo when $\sigma_s$ is too large.

**Non-Local Means (NLM)**
Proposed by Buades, Coll & Morel (2005), NLM exploits non-local repetitive structure (similar patches at distant locations) to perform weighted-average denoising. Weights are determined by the weighted Euclidean distance between patches: $w(p,q) \propto \exp(-\|P(p)-P(q)\|^2/h^2)$. The optimal ratio between filter strength $h$ and noise level $\sigma$ depends on patch size, distance definition, and image normalization — there is no single universal empirical formula.

**BM3D (Block Matching and 3D Filtering)**
Proposed by Dabov et al. (2007), combining non-local self-similarity with transform-domain sparsity: block matching constructs a 3D stack for each reference block, a 3D transform is applied and hard-thresholding denoising performed (Stage 1), followed by Wiener filtering refinement using the Stage 1 result (Stage 2). BM3D was long the highest-PSNR classical algorithm on standard AWGN benchmarks (BSD68).

**DnCNN (Zhang 2017)**
A residual learning denoising network with 17 layers and 64 channels. The network learns to predict noise $\hat{n}$; the denoised result is $\hat{x} = y - \hat{n}$. Layer structure: layer 1 Conv+ReLU (no BN), layers 2–16 Conv+BN+ReLU (BN between Conv and ReLU), layer 17 Conv (no BN/ReLU). Theoretical receptive field: 35×35 (17 stacked 3×3 stride-1 convolutions). PSNR on BSD68: ~31.73 dB at σ=15, ~29.23 dB at σ=25.

**FFDNet (Zhang 2018)**
Takes a Noise Level Map $M$ as additional network input, allowing a single model to handle arbitrary noise strengths (uniform or spatially varying). Input processing uses pixel unshuffle — decomposing an $H\times W$ image into four $H/2\times W/2$ sub-images concatenated along the channel dimension — which is the inverse of the pixel shuffle used in super-resolution upsampling; do not confuse the two.

**NAFNet (Chen 2022)**
An extremely simple image restoration network that replaces nonlinear activations such as GELU with SimpleGate ($X_1 \odot X_2$, element-wise product of two channel halves), combined with Layer Normalization and simplified channel attention. NAFNet-32 achieves PSNR ~39.99 dB (SSIM ~0.9699) on SIDD; NAFNet-64 achieves ~40.30 dB (SSIM ~0.9700). Primarily benchmarked on real-color-noise datasets (SIDD, DND); no official AWGN BSDS68 figures are available.

**CBDNet (Guo 2019)**
A cascaded dual-network for real-world denoising: a noise estimation subnet predicts the per-pixel noise map, and a non-blind denoising subnet (U-Net) uses the estimated map as joint input. An asymmetric loss penalizes noise underestimation more heavily than overestimation.

**Noise2Noise (Lehtinen 2018)**
Proves that if noise has zero mean ($\mathbb{E}[n]=0$), training on pairs of independently noisy images of the same clean scene while minimizing MSE is equivalent in expectation to clean-supervised training. This enables denoising network training without any clean reference images, spawning Noise2Void, Blind2Unblind, and other self-supervised approaches.

**Plastic Skin Effect**
A typical portrait denoising artifact: skin micro-texture (pores, fine lines) overlaps in frequency with low-frequency noise; excessive spatial NR erases both, leaving skin that looks smooth like plastic or wax. Mitigation: use a skin color detection mask to reduce NR strength in skin regions, or apply texture synthesis post-denoising to restore micro-texture.

**Watercolor Effect**
A typical artifact of NLM or BM3D in fine-texture regions (grass, hair): the algorithm finds many similar patches for strong weighted averaging, flattening the random phase of weak textures and producing regions of uniform color — resembling a watercolor painting. Mitigation: reduce the search window size or the number of similar blocks $M$, or apply adaptive NR strength in texture regions.

**SIDD (Smartphone Image Denoising Dataset)**
A real-world smartphone noise benchmark using multiple Sony IMX series sensors at various ISO settings and scenes (~30,000+ paired noisy/clean image pairs). SIDD is the primary benchmark for real-noise denoising evaluation; results in color sRGB space are not directly comparable with AWGN synthetic benchmarks (BSD68).

---

## §9 Engineering Recommendations

Spatial NR deployment decisions require simultaneously satisfying three constraints: target SNR gain, available compute budget, and acceptable detail loss ceiling. All three must be met simultaneously for the parameters to be correct.

| Scenario | Recommended approach | Typical latency | Notes |
|----------|---------------------|----------------|-------|
| Real-time preview, low ISO (< 400) | Lightweight bilateral / Guided NR | < 1 ms/frame (1080p) | Low noise level; excessive NR loses detail |
| Capture mode, ISO 400–1600 | FFDNet / NAFNet-S (INT8) | 3–8 ms/frame, NPU | Moderate luma strength; slightly stronger chroma; validate with Macbeth low-saturation patches |
| Night mode / post multi-frame merge | NAFNet-B or CBDNet (offline) | 15–40 ms/frame | Multi-frame merge already reduces noise by √N; spatial NR on top — avoid over-smoothing |
| Video recording (real-time TNR) | Temporal NR (TNR) + lightweight spatial | Requires TNR hardware | Spatial NR is residual supplement; TNR is the primary workhorse |
| Offline post-processing / cloud | BM3D (reference grade) | 500 ms+/frame | Use as tuning reference baseline; not for real-time paths |

**Key tuning notes:**

- **Start luma NR low, chroma NR can be more aggressive:** Increase `NR_Luma_Strength` one notch at a time while monitoring fine detail (hair, fabric). `NR_Chroma_Strength` at 2–3× luma is generally safe, but above 4× capture a Macbeth chart and check whether low-saturation patches lose color.
- **ISO-adaptive NR curve is the tuning focus, not a fixed value:** Noise models differ between ISO 200 and ISO 3200. NR strength should interpolate with ISO, not jump — jump points create visible "noise discontinuities" in captured sequences. Qualcomm platforms use a NR vs. ISO LUT; MTK uses multi-segment interpolation tables for `NR_Luma_Gain`.
- **Two parallel acceptance metrics:** PSNR measures noise suppression; MTF50 (or SFR) measures detail preservation. Optimizing PSNR alone produces "blurry-clean images" where both noise and detail disappear. Typical requirement: MTF50 should not drop more than 10% relative to the no-NR baseline.

**When DL NR is not worth deploying:** If compute has been consumed by other AI modules (SR, portrait, HDR), or the platform NPU has less than ~2 ms budget remaining, a well-tuned bilateral filter is more stable than an under-quantized DL NR model. An INT8-quantized DL NR at very low SNR (ISO > 6400) can produce blocky artifacts that look worse than traditional filtering.

---

## References

1. **Tomasi, C. & Manduchi, R.** (1998). Bilateral filtering for gray and color images. *ICCV 1998*, 839–846.

2. **Buades, A., Coll, B. & Morel, J.M.** (2005). A non-local algorithm for image denoising. *CVPR 2005*, Vol. 2, 60–65.

3. **Dabov, K., Foi, A., Katkovnik, V. & Egiazarian, K.** (2007). Image denoising by sparse 3D transform-domain collaborative filtering. *IEEE Transactions on Image Processing*, 16(8), 2080–2095.

4. **Zhang, K., Zuo, W., Chen, Y., Meng, D. & Zhang, L.** (2017). Beyond a Gaussian Denoiser: Residual Learning of Deep CNN for Image Denoising. *IEEE Transactions on Image Processing*, 26(7), 3142–3155.

5. **Zhang, K., Zuo, W. & Zhang, L.** (2018). FFDNet: Toward a Fast and Flexible Solution for CNN-Based Image Denoising. *IEEE Transactions on Image Processing*, 27(9), 4608–4622.

6. **Chen, L., Chu, X., Zhang, X. & Sun, J.** (2022). Simple Baselines for Image Restoration. *ECCV 2022*. arXiv:2204.04676.

7. **Lehtinen, J. et al.** (2018). Noise2Noise: Learning Image Restoration without Clean Data. *ICML 2018*. arXiv:1803.04189.

8. **Gharbi, M., Chaurasia, G., Paris, S. & Durand, F.** (2016). Deep Joint Demosaicking and Denoising. *SIGGRAPH Asia 2016*, 35(6), 1–12.

9. **He, K., Sun, J. & Tang, X.** (2013). Guided Image Filtering. *IEEE TPAMI*, 35(6), 1397–1409.

10. **Guo, S., Yan, Z., Zhang, K., Zuo, W. & Zhang, L.** (2019). Toward Convolutional Blind Denoising of Real Photographs. *CVPR 2019*.

11. **Abdelhamed, A., Lin, S. & Brown, M.S.** (2018). A High-Quality Denoising Dataset for Smartphone Cameras (SIDD). *CVPR 2018*.

12. **Plotz, T. & Roth, S.** (2017). Benchmarking Denoising Algorithms with Real Photographs (DND). *CVPR 2017*.

13. **Song, Y. et al.** (2021). Score-Based Generative Modeling through Stochastic Differential Equations. *ICLR 2021*. arXiv:2011.13456.

14. **Luo, Z. et al.** (2023). Image Restoration with Mean-Reverting Stochastic Differential Equations (IR-SDE). *ICML 2023*. arXiv:2301.09482.

15. **Xia, Z. et al.** (2023). DiffIR: Efficient Diffusion Model for Image Restoration. *ICCV 2023*. arXiv:2303.09472.

16. **Makitalo, M. & Foi, A.** (2013). Optimal Inversion of the Generalized Anscombe Transformation for Poisson-Gaussian Noise. *IEEE Transactions on Image Processing*, 22(1), 91–103.
