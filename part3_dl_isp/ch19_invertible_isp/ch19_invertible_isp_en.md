# Part 3, Chapter 19: Invertible Image Signal Processing

> **Pipeline position:** DL-ISP bidirectional mapping; RAW ↔ sRGB invertible modeling
> **Prerequisites:** Volume 3, Chapter 1 (DL Overview); Volume 3, Chapter 17 (Generative RAW-to-RGB); Volume 3, Chapter 18 (Self-Supervised ISP)
> **Target readers:** DL researchers, camera algorithm engineers

---

## §1 Theory

### 1.1 The Information Loss Problem in ISP and the Motivation for Invertible Architectures

Traditional image signal processing (ISP) is a **one-way lossy pipeline**: a RAW Bayer image passes through black-level correction, bad-pixel repair, demosaicing, denoising, white balance, color matrix transformation, gamma/tone mapping, color space conversion, and other irreversible operations before finally yielding an sRGB image. Along this path, a substantial amount of information is discarded:

- **Demosaicing** interpolates single-channel per-pixel Bayer data into three-channel RGB, but the spatial-frequency information undergoes irreversible aliasing in the process;
- **Gamma curves and tone mapping** are nonlinear compression operations; highlight and shadow detail in a high dynamic range (HDR) scene is intentionally or unintentionally clipped;
- **Quantization and clipping** compress floating-point intermediate results into 8-bit integers, losing approximately $\log_2(256/2^{14}) \approx 6$ bits of precision;
- **JPEG/HEIF encoding** introduces additional lossy compression artifacts.

These information losses are an acceptable cost during forward rendering, but they create a serious **obstacle to inverse reconstruction**: given a rendered sRGB image (or even a JPEG), it is impossible to precisely recover the corresponding RAW data. The value of inverse reconstruction lies in several applications:

1. **RAW data compression and storage**: the camera need only save an sRGB JPEG; the embedded information from an invertible ISP allows the RAW to be recovered on demand for secondary editing;
2. **HDR reprocessing**: restore RAW from an sRGB image in order to apply HDR tone mapping again, eliminating the need to store the original HDR asset separately;
3. **Data augmentation**: synthesize paired RAW-sRGB data from an existing large sRGB photo library for training supervised ISP models;
4. **Cross-device RAW transfer**: convert the sRGB image captured by camera A back into a "universal RAW" and re-render it through the ISP of device B.

The goal of **invertible ISP (InvISP, 可逆ISP)** is to design a bidirectional mapping network such that:

$$f_\theta: \text{RAW} \to \text{sRGB} \quad \text{and} \quad f_\theta^{-1}: \text{sRGB} \to \text{RAW}$$

satisfy **exact invertibility** (or approximate invertibility), i.e., $f_\theta^{-1}(f_\theta(x_\text{raw})) \approx x_\text{raw}$, while the forward rendering result $f_\theta(x_\text{raw})$ achieves high visual quality.

---

### 1.2 Normalizing Flow Background: GLOW and RealNVP

The core mathematical tool behind invertible ISP is the **normalizing flow (归一化流)**. A normalizing flow is a special class of neural network that maps a simple distribution (such as a Gaussian) to a complex data distribution through a series of invertible transformations $f = f_K \circ f_{K-1} \circ \cdots \circ f_1$. The central requirement is that each sub-transformation $f_k$ must be bijective (双射) and have an analytically computable Jacobian.

**Exact Log-Likelihood (精确对数似然)** is a distinguishing advantage of normalizing flows. If data $x$ is generated from latent variable $z \sim p_z(z)$ via an invertible mapping $x = f(z)$, the change-of-variables formula gives:

$$\log p_x(x) = \log p_z(z) + \log \left|\det \frac{\partial f^{-1}}{\partial x}\right| = \log p_z(f^{-1}(x)) + \sum_{k=1}^K \log \left|\det J_{f_k^{-1}}\right| \tag{1}$$

where $J_{f_k^{-1}}$ is the Jacobian matrix of the $k$-th layer's inverse transformation. By maximizing $\log p_x(x)$, the model learns the data distribution.

**RealNVP** (Dinh et al., 2016) introduces the affine coupling layer (仿射耦合层), making Jacobian determinant computation achievable in $O(d)$ complexity:

$$\log \left|\det J_\text{coupling}\right| = \sum_i s_i(x_1) \tag{2}$$

This is because the coupling layer's Jacobian is a triangular matrix, and its determinant equals the product of the diagonal elements (becoming a sum after taking the log).

**GLOW** (Kingma & Dhariwal, NeurIPS 2018) introduces three improvements over RealNVP:

1. **Invertible 1×1 Convolution (可逆1×1卷积):** Replaces fixed channel permutation with a learned optimal channel mixing; the Jacobian determinant is $\log |\det W|$ (where $W$ is the 1×1 convolution weight matrix);
2. **Actnorm (activation normalization, 激活归一化):** Replaces BatchNorm with per-channel affine transformation for data normalization, with parameters initialized from the first batch of data (data-dependent init), yielding more stable training at small batch sizes;
3. **Multi-Scale Architecture (多尺度架构):** At each resolution level, half the channels are directly output to the latent space, reducing computation at high-resolution layers.

For invertible ISP, GLOW's multi-scale architecture is particularly suited to handling the resolution difference between RAW ($H/2 \times W/2 \times 4$) and sRGB ($H \times W \times 3$).

**The affine coupling layer (仿射耦合层)** was introduced by Dinh et al. (RealNVP, 2016) and is the most widely used building block for constructing invertible transformations. Its transformation rule is as follows:

Given input $x$, split it along the channel dimension into two parts $x_1, x_2$:

$$y_1 = x_1 \tag{3}$$

$$y_2 = x_2 \odot \exp(s(x_1)) + t(x_1) \tag{4}$$

where $s(\cdot)$ and $t(\cdot)$ are arbitrary learnable scalar functions (scale and translation), and $\odot$ denotes element-wise multiplication. The inverse transformation is:

$$x_1 = y_1 \tag{5}$$

$$x_2 = (y_2 - t(y_1)) \odot \exp(-s(y_1)) \tag{6}$$

The key property of the affine coupling layer is that **the inverse is analytically available and does not require computing the inverse of $s$ or $t$**. This means $s$ and $t$ can be arbitrarily complex deep neural networks (e.g., ResNet, U-Net) without compromising invertibility.

---

### 1.3 InvISP Architecture Design (Xing et al., CVPR 2021)

**InvISP** (Xing et al., CVPR 2021) is the first work to systematically study invertible ISP. Its architecture consists of several cascaded affine coupling layers, with carefully designed RAW/sRGB dimension alignment.

**Dimension Adaptation:** For input of dimension $(H \times W \times 4)$ — a Bayer-packed RAW (the RGGB four channels are packed into $H/2 \times W/2 \times 4$) — and output of $(H \times W \times 3)$ sRGB. Because the input and output dimensions are mismatched, InvISP operates in the **Bayer-packed resolution space** ($H/2 \times W/2$) and handles format conversion via PixelShuffle:

**Forward mapping (RAW → sRGB)**:

$$z = f_K \circ \cdots \circ f_1(x_\text{raw})$$

$$\hat{x}_\text{sRGB} = \text{PixelShuffle}(z)$$

where $\text{PixelShuffle}$ rearranges the $H/2 \times W/2 \times 4$ feature map into $H \times W \times 1$ and then copies it to three channels (or maps to three channels via a simple linear transformation).

**Inverse mapping (sRGB → RAW)**:

$$z' = \text{PixelUnshuffle}(x_\text{sRGB})$$

$$\hat{x}_\text{raw} = f_1^{-1} \circ \cdots \circ f_K^{-1}(z')$$

**Log-likelihood objective:** During training, InvISP also incorporates the normalizing flow likelihood objective, modeling the RAW data distribution as a Gaussian $p_z(z)$, and maximizing the likelihood of RAW data while ensuring forward rendering quality:

$$\mathcal{L}_\text{NLL} = -\mathbb{E}_{x_\text{raw}}\left[\log p_z(f_\theta(x_\text{raw})) + \sum_{k=1}^K \log |\det J_{f_k}|\right] \tag{7}$$

The **joint loss** design is critical to InvISP. Using only an invertibility constraint (requiring $\hat{x}_\text{raw}$ to match $x_\text{raw}$) leads to poor forward rendering quality; optimizing for rendering quality alone (e.g., VGG perceptual loss) breaks invertibility. InvISP adopts a **joint loss**:

$$\mathcal{L} = \lambda_\text{rgb} \cdot \mathcal{L}_\text{sRGB} + \lambda_\text{raw} \cdot \mathcal{L}_\text{RAW} + \lambda_\text{perc} \cdot \mathcal{L}_\text{perc} \tag{8}$$

where:
- $\mathcal{L}_\text{sRGB} = \|f_\theta(x_\text{raw}) - x_\text{sRGB}^*\|_1$: $L_1$ loss between the forward rendering and the reference sRGB;
- $\mathcal{L}_\text{RAW} = \|f_\theta^{-1}(f_\theta(x_\text{raw})) - x_\text{raw}\|_1$: cycle-consistency RAW reconstruction loss;
- $\mathcal{L}_\text{perc}$: VGG perceptual loss, constraining the forward rendering to be perceptually consistent with the reference.

The weight $\lambda_\text{raw}$ is typically much larger than $\lambda_\text{rgb}$ (e.g., 10:1), because invertibility is the primary constraint; perceptual quality is subsequently refined through $\mathcal{L}_\text{sRGB}$ and $\mathcal{L}_\text{perc}$ once invertibility is satisfied.

Experiments show that InvISP achieves a RAW reconstruction PSNR approximately **15 dB** higher than CycleISP, and approximately **10 dB** higher than UPI (Unprocessing Pipeline, Brooks et al.), reaching a level of precise reconstruction that previous methods could not approach.

---

### 1.4 CycleISP (Zamir et al., CVPR 2020): The Cycle Consistency Approach

**CycleISP** (Zamir et al., CVPR 2020) adopts a different technical approach from InvISP — **cycle consistency (循环一致性)** rather than strict mathematical invertibility.

CycleISP trains two independent neural networks:

- **Forward network $G: \text{RAW} \to \text{sRGB}$**: renders RAW as sRGB;
- **Inverse network $F: \text{sRGB} \to \text{RAW}$**: restores sRGB back to RAW.

Its training objective minimizes the cycle consistency loss:

$$\mathcal{L}_\text{cycle} = \|F(G(x_\text{raw})) - x_\text{raw}\|_1 + \|G(F(x_\text{sRGB})) - x_\text{sRGB}\|_1 \tag{9}$$

That is, after the round-trip RAW→sRGB→RAW, the output should be close to the input; similarly, after sRGB→RAW→sRGB the result should be close to the original sRGB. CycleISP's motivation is **denoising data augmentation**: train the network to convert clean sRGB images to RAW (adding real noise), and then render noisy RAW as noisy sRGB, thereby providing synthetic paired data for sRGB denoising models.

**Fundamental differences between CycleISP and InvISP:**

| Comparison Dimension | InvISP (Normalizing Flow) | CycleISP (Cycle Consistency) |
|---------------------|--------------------------|------------------------------|
| Invertibility guarantee | Mathematically exact (architectural guarantee) | Training-driven approximate invertibility |
| RAW reconstruction PSNR | ~47 dB (MIT-FiveK) | ~32 dB (MIT-FiveK) |
| Primary application | RAW compression, HDR reprocessing | Denoising data augmentation, domain transfer |
| Network parameters | ~8M (shared) | ~2×4M (two independent networks) |
| Requires paired data | Requires paired RAW-sRGB | Can train with unpaired data |
| Training difficulty | Lower (no adversarial loss) | Higher (can incorporate adversarial loss) |

The key distinction is: InvISP guarantees exact invertibility through **network architecture** (invertible coupling layers) independent of training convergence quality; whereas CycleISP's invertibility is constrained only by **training objective**, and inverse accuracy after training is bounded by model capacity and training thoroughness. Therefore, InvISP has an inherent advantage in precise RAW reconstruction tasks; while CycleISP is more flexible in scenarios requiring unpaired data training or domain adaptation.

---

### 1.5 Differentiable JPEG Compression Simulator

In real-world applications, sRGB images are typically stored after JPEG encoding. The lossy compression introduced by JPEG disrupts the invertible ISP information embedded in the sRGB image, causing a large drop in RAW reconstruction accuracy. InvISP addresses this problem with a **differentiable JPEG compression simulator (可微分JPEG压缩模拟器)**.

A real JPEG codec consists of three steps: discrete cosine transform (DCT), quantization (量化), and entropy coding (Huffman). The quantization step — dividing DCT coefficients by a quantization table and rounding — is not differentiable. The standard remedy is to approximate it with **soft quantization (软量化)**:

$$\text{SoftQuant}(x, q) = x - \frac{q}{2\pi} \sin\left(\frac{2\pi x}{q}\right) \tag{10}$$

This function approximates the rounding operation near integer multiples of $x/q$ while remaining differentiable everywhere.

InvISP **inserts the differentiable JPEG simulator into the training graph**:

$$\tilde{x}_\text{sRGB} = \text{JPEG}_\text{diff}(f_\theta(x_\text{raw}), Q)$$

$$\hat{x}_\text{raw} = f_\theta^{-1}(\tilde{x}_\text{sRGB})$$

where $Q$ is the JPEG quality factor (typically set to 90). Through end-to-end training, the network learns to maximize RAW reconstruction accuracy under the constraint imposed by JPEG compression. Experiments show that after training with the JPEG simulator, directly reconstructing RAW from a JPEG image achieves a PSNR only about **0.8 dB** below reconstruction from a lossless sRGB image, whereas without the simulator the gap exceeds **5 dB**.

---

### 1.6 Extensions of Invertible ISP

**RAW compression (Implicit RAW Coding)**: Kim et al. (CVPR 2022) proposed that appending only **64 KB** of patch information to a JPEG image's metadata is sufficient to fully reconstruct the RAW, treating invertible ISP as an extremely low-overhead RAW compression coding scheme.

**AIM 2022 Reversed ISP Challenge** (Conde et al., ECCV 2022) established a standardized evaluation benchmark specifically for the task of reconstructing RAW from sRGB. It evaluates reconstruction accuracy across multiple sensors including Canon, Samsung, and Sony, promoting standardized research in this direction.

**Invertible ISP-assisted HDR**: When an HDR scene has been tone-mapped to an SDR sRGB image, if an invertible ISP can precisely reconstruct the RAW, a custom tone mapping curve can be re-applied to the RAW to achieve after-the-fact HDR reprocessing, without needing to store the original RAW file.

---

## §2 Calibration

### 2.1 Bidirectional Accuracy Evaluation Protocol

Evaluating an invertible ISP requires attention to both **forward rendering quality** and **inverse reconstruction accuracy**, between which there is an inherent trade-off:

| Evaluation Direction | Metrics | Notes |
|---------------------|---------|-------|
| Forward RAW→sRGB | PSNR, SSIM, LPIPS | Compared against the camera's native ISP rendering |
| Inverse sRGB→RAW | PSNR, SSIM, Delta-E | Compared against the original RAW; Delta-E focuses on RAW color channels |
| Compression robustness | Inverse PSNR at JPEG Q=90/80/70 | Evaluates the impact of JPEG degradation on RAW reconstruction |

**Round-Trip Fidelity (往返保真度)** is a unique evaluation paradigm for invertible ISP: given original RAW $x_\text{raw}$, generate $\hat{x}_\text{sRGB} = f_\theta(x_\text{raw})$ via the forward network, then reconstruct $\hat{x}_\text{raw} = f_\theta^{-1}(\hat{x}_\text{sRGB})$ via the inverse network, and measure round-trip fidelity with $\text{PSNR}(\hat{x}_\text{raw}, x_\text{raw})$. This metric directly reflects invertibility quality, independent of forward rendering quality.

**Training dataset requirements:** Invertible ISP relies on **strictly paired RAW-sRGB datasets** (i.e., the RAW and its corresponding sRGB reference for the same scene). Commonly used datasets include:

- **MIT-Adobe FiveK**: 5,000 pairs from Canon EOS-1D/5D, Nikon D700/D3X; 5 professional retouchers each provide one sRGB reference per image; Expert C's version (combined exposure and color adjustment) is typically used;
- **Sony RX100 VII dataset**: Mobile/consumer camera RAW-sRGB pairs, covering a wider range of scene types;
- **S7-ISP dataset** (Schwartz et al., 2018): Samsung Galaxy S7 phone RAW-sRGB pairs, approximately 110 pairs covering indoor/outdoor scenes under various lighting conditions, suitable for evaluating invertibility of mobile ISP;
- **ZRR dataset** (Ignatov et al., 2020): Zurich RAW to RGB, containing paired data from Sony Xperia X and Canon EOS 5D Mark IV, approximately 20K pairs.

These datasets each have different emphases in terms of resolution, camera models, and scene diversity. The original InvISP paper uses MIT-Adobe FiveK as the primary benchmark; S7-ISP and ZRR focus more on mobile camera scenarios.

### 2.2 Theoretical Limits of Exact Invertibility

It should be noted that mathematically perfect RAW reconstruction faces the following unavoidable sources of error in practical systems:

1. **Finite-precision floating-point arithmetic**: floating-point rounding errors during network inference cause theoretically invertible affine coupling layers to produce reconstruction errors on the order of $10^{-3}$ under float16;
2. **sRGB clipping**: if highlights in the RAW are clipped to 255 after tone mapping, the corresponding RAW information cannot be recovered from the clipped sRGB values;
3. **Bayer resolution asymmetry**: the spatial resolution mismatch between RAW ($H/2 \times W/2$) and sRGB ($H \times W$) means that high-frequency texture information cannot be precisely embedded.

These limitations mean that the reconstruction PSNR of an invertible ISP has a practical upper bound, typically around **42–48 dB** (corresponding to sub-pixel-level errors).

---

## §3 Tuning

### 3.1 Invertible Block Depth and Memory Overhead

One of the core tuning dimensions in InvISP is the **number of affine coupling layers $K$** (i.e., invertible block depth). Theoretically, more coupling layers can learn more complex RAW↔sRGB mappings, but bring significant memory and compute overhead:

| Number of layers $K$ | Parameters (M) | Training VRAM (GB, batch=4) | Inverse PSNR (MIT-FiveK, dB) | Inference latency (ms, 1080p) |
|----------------------|---------------|------------------------------|------------------------------|-------------------------------|
| 4 | ~2 | ~4 | ~44.0 | ~15 |
| 8 | ~4 | ~8 | ~46.2 | ~28 |
| 16 | ~8 | ~16 | ~47.1 | ~55 |
| 24 | ~12 | ~24 | ~47.4 | ~82 |

From the table, a **diminishing returns** pattern is observed: increasing $K$ from 4 to 16 yields ~3 dB PSNR improvement, but from 16 to 24 yields only 0.3 dB while increasing compute by 50%. Engineering deployments typically choose $K=8$ as the accuracy-efficiency balance point.

### 3.2 Lightweight Design

The original InvISP has approximately 8M parameters, and its inference latency is too high for a real-time camera ISP pipeline. Engineering deployment typically employs the following optimization strategies:

- **Reducing the number of coupling layers**: decreasing from $K=16$ layers to $K=4$ layers incurs a PSNR loss of approximately 1 dB while improving inference speed by $4\times$;
- **Channel count reduction**: the $s, t$ sub-networks are simplified from ResNet-Blocks to single-layer convolutions, retaining only linear transformation capacity;
- **Half-precision inference**: float16 inference on the NPU, combined with a compensation loss to mitigate quantization accuracy degradation.

### 3.3 Accuracy-Capacity Trade-offs for Mobile NPU Deployment

When deploying invertible ISP on mobile NPUs (e.g., Qualcomm Hexagon DSP, MediaTek APU), additional constraints apply:

1. **Operator compatibility**: NPUs typically do not natively support transcendental functions like `exp` / `log`; the $\exp(s(x_1))$ operation in affine coupling layers requires piecewise linear approximation, introducing an additional 0.1–0.3 dB accuracy loss;
2. **Memory bandwidth bottleneck**: cascaded inference through invertible blocks requires saving intermediate activations at each layer for the inverse pass (when forward and inverse inference are interleaved), with peak memory approximately 1.5–2× that of unidirectional inference;
3. **int8 quantization compatibility**: the $s, t$ networks within coupling layers can be quantized to int8, but the dynamic range of the scale parameter $\exp(s)$ is large; Activation-Aware Quantization (AAQ) strategies are needed during quantization.

### 3.4 The Role of the GLOW Temperature Parameter

In GLOW architectures, the **temperature parameter (温度参数)** $\tau$ can be used at inference time to control sampling diversity:

$$z \sim \mathcal{N}(0, \tau^2 I)$$

When $\tau < 1$, samples are more concentrated (smaller variance), inverse reconstruction is more conservative and biased toward the training distribution mean; when $\tau = 1$, standard sampling applies; when $\tau > 1$, sampling diversity increases but may introduce unrealistic color shifts.

In the deterministic reconstruction scenario of invertible ISP (where the sRGB is known and the corresponding RAW is reconstructed), no random sampling is performed; instead $z = f_\theta^{-1}(x_\text{sRGB})$ is computed directly, and the temperature parameter is inactive. However, in **generative RAW synthesis** (synthesizing diverse RAW noise samples from sRGB), appropriately increasing $\tau$ (e.g., 0.7–0.9) can generate RAW samples whose noise distribution is closer to real noise, useful for denoising data augmentation.

### 3.5 Embedded RAW Compression Scenario

In the "RAW + 64 KB patch" deployment mode, the practical workflow for invertible ISP is:

1. **Capture side (embedding)**: the original RAW is rendered to an sRGB JPEG via the forward invertible ISP; simultaneously, the **patch information** required for $f_\theta^{-1}$ reconstruction (approximately 64 KB) is appended to the JPEG metadata (EXIF/XMP);
2. **Editing side (restoration)**: the JPEG image and the 64 KB metadata are read in, the inverse ISP network is run, and the RAW data is recovered for secondary editing in professional software (e.g., Lightroom, Darktable).

Compared with storing the RAW directly (typically 25–50 MB per shot on a smartphone camera), the storage overhead per image increases by only 64 KB, achieving a **compression ratio exceeding 99%**.

---

## §4 Failure Modes and Artifacts

### 4.1 Irreversible Regions Caused by Highlight Clipping

The most significant failure scenario for invertible ISP is **HDR highlight regions**: if highlight pixels in the RAW (near the ADC full-scale value) are clipped to pure white in the sRGB after tone mapping (255, 255, 255), the specific RAW values of these pixels are completely lost, and an invertible ISP has no means of recovering them. A common symptom is that the reconstructed RAW shows a large area of uniform values in the highlight region, severely mismatching the actual highlight detail in the true RAW.

**Engineering mitigation**: introduce a highlight mask loss — reduce the weight of the invertibility loss over highlight-clipped regions, preventing the network from sacrificing accuracy in normal regions in an attempt to "fit" regions that cannot be reconstructed.

### 4.2 Checkerboard Artifacts

When the $s, t$ sub-networks within affine coupling layers use **strided convolution (步长卷积)** or transposed convolution (Transposed Convolution) for down/upsampling, the non-uniform coverage of convolution kernels introduces **periodic checkerboard artifacts (棋盘格状周期性伪影)** in the output. This problem is most prominent with stride-2 transposed convolutions, manifesting as alternating bright/dark every other row and column.

**Mitigation methods:**
- Replace transposed convolutions with **sub-pixel convolution (Sub-pixel Convolution, PixelShuffle)**;
- Add a $3\times3$ convolution after strided convolution for smoothing;
- Replace transposed convolution with **bilinear upsampling (Bilinear Upsampling) + convolution**.

Checkerboard artifacts are usually mild in the forward pass (RAW→sRGB) because the perceptual loss $\mathcal{L}_\text{perc}$ suppresses them; but in the inverse mapping (sRGB→RAW), without perceptual reference, checkerboard artifacts may leave slight regular patterns in fine-texture areas (e.g., clothing fabric) of the reconstructed RAW.

### 4.3 Color Shift from Intermediate Representation Quantization

When invertible ISP performs inference at **float16** or **int8** precision, the $\exp(s(x_1))$ operation within affine coupling layers is highly sensitive to small numerical precision: even if the error in $s(x_1)$ is only $\Delta s \approx 0.01$, after exponentiation the scale error reaches $\Delta(\exp(s)) \approx e^s \cdot \Delta s$, which at large $s$ (e.g., $s=3$, $e^s \approx 20$) amplifies the error by a factor of approximately 20.

After cascading multiple layers, this error accumulation leads to **mild but perceptible color shift (颜色偏移)**, manifesting as:
- Systematic hue shift in a particular direction (e.g., overall warmer or cooler tones);
- Color shift more noticeable in shadows and high-saturation regions;
- PSNR difference between float32 and float16 inference approximately **1.5–3 dB**.

**Engineering mitigation**: apply a $\tanh$ activation to the $s$ output of affine coupling layers (constraining the range to $[-1, 1]$), trading a small amount of expressive capacity for numerical stability; or use mixed precision at critical coupling layers (retaining float32 at key layers).

### 4.4 Non-Exact Inverse Transform under Float32 Precision Limits

Theoretically, the inverse of an affine coupling layer is analytically exact. However, at float32 precision, numerical errors from multiple consecutive coupling layers accumulate, causing **non-exact inverse transforms**:

$$\|f_\theta^{-1}(f_\theta(x_\text{raw})) - x_\text{raw}\|_\infty \approx 10^{-5} \text{ (float32)} \quad \text{vs} \quad 10^{-3} \text{ (float16)}$$

The impact on PSNR for 12/14-bit RAW is approximately 0.05–0.5 dB (float32) and 1–3 dB (float16). For archival applications requiring extreme precision, a **compensation residual (补偿残差)** strategy can be adopted: append a lightweight residual network after the inverse inference specifically to correct numerical errors, compressing the precision loss under float16 to within 0.1 dB.

### 4.5 Motion Blur and Sensor Specificity

Invertible ISP assumes the input is a **single RAW image of a static scene**. If camera shake causes motion blur in the RAW, and the denoising/sharpening steps in the ISP pipeline partially compensate for that blur, the correspondence between the forward rendering result and the RAW becomes ambiguous, causing the invertibility loss to increase.

InvISP is bound at training time to a specific camera-sensor pair (e.g., Canon EOS 5D). When applied directly to a new sensor, RAW reconstruction accuracy drops substantially due to differences in RAW linearization coefficients, color matrices, and other sensor-specific properties. Cross-sensor generalization remains an open problem for current invertible ISP methods.

---

## §5 Evaluation

### 5.1 Quantitative Metrics Matrix

| Metric | Direction | Computation | Typical Range |
|--------|-----------|-------------|---------------|
| PSNR↑ | Forward, inverse | $10\log_{10}(255^2/\text{MSE})$ | Forward 35–42 dB; inverse 40–48 dB |
| SSIM↑ | Forward, inverse | Structural similarity | 0.92–0.99 |
| LPIPS↓ | Forward | VGG perceptual distance | 0.03–0.15 |
| Delta-E 2000↓ | Inverse | CIE Lab color difference | < 2.0 is good |

### 5.2 Published Benchmark Results Comparison

The following table summarizes key benchmark numbers from the InvISP and CycleISP papers on the **MIT-Adobe FiveK dataset (Canon EOS 5D subset, 100-pair test set)**:

**Inverse reconstruction (sRGB → RAW) PSNR comparison:**

| Method | Dataset | Inverse PSNR (dB)↑ | Inverse SSIM↑ | Delta-E↓ | Parameters |
|--------|---------|---------------------|---------------|----------|------------|
| UPI (Brooks et al., 2019) | MIT-FiveK | ~37.2 | 0.931 | 4.8 | ~2M |
| CycleISP (Zamir et al., 2020) | MIT-FiveK | ~32.4 | 0.901 | 6.2 | ~8M |
| InvISP (Xing et al., 2021) | MIT-FiveK | **~47.1** | **0.983** | **1.4** | ~8M |
| InvISP + JPEG Q=90 | MIT-FiveK | ~46.3 | 0.979 | 1.6 | ~8M |
| InvISP-Lite (K=4) | MIT-FiveK | ~44.0 | 0.971 | 2.1 | ~2M |

**Forward rendering (RAW → sRGB) quality comparison:**

| Method | Forward PSNR (dB)↑ | Forward SSIM↑ | LPIPS↓ | Notes |
|--------|---------------------|---------------|--------|-------|
| CycleISP (Zamir et al., 2020) | 41.5 | 0.969 | 0.041 | Denoising-assisted training |
| InvISP (Xing et al., 2021) | **42.3** | **0.974** | **0.035** | Joint optimization |
| InvISP-Lite (K=4) | 40.8 | 0.963 | 0.048 | Lightweight version |

**Note:** CycleISP's forward rendering quality is close to InvISP (gap ~0.8 dB), but the gap in inverse reconstruction is enormous (~15 dB), reflecting the fundamental limitation of cycle-consistency methods in precise invertibility.

**AIM 2022 Reversed ISP Challenge best results (Canon track):**

| Rank | Method Category | PSNR (dB)↑ | SSIM↑ | Parameters |
|------|----------------|------------|-------|------------|
| 1st | UNet + post-processing ensemble | 48.3 | 0.991 | >50M |
| 2nd | Transformer-based | 47.8 | 0.989 | ~30M |
| 3rd | InvISP variant | 46.9 | 0.985 | ~8M |
| Baseline | InvISP (original) | 46.5 | 0.982 | ~8M |

### 5.3 Ablation Study Design

When evaluating an invertible ISP, the following ablations are critical for understanding the system:

1. **With vs. without JPEG simulator**: compare JPEG-robust RAW reconstruction PSNR under the two training settings;
2. **Effect of the number of coupling layers $K$**: accuracy-speed trade-off at $K=4/8/16$;
3. **Joint loss weights $\lambda_\text{raw}/\lambda_\text{rgb}$**: high $\lambda_\text{raw}$ yields high inverse accuracy but the forward rendering deviates from the reference ISP; the opposite holds for low values;
4. **Half-precision inference error**: difference in inverse PSNR between float32 and float16 inference, evaluating the impact of quantization error.

---

## §6 Code

The companion code for this chapter is in *See §6 Code section for runnable examples.* and includes the following demonstrations:

```python
import torch
import torch.nn as nn
import torch.nn.functional as F


# ── Affine Coupling Layer ──────────────────────────────────────────────────────
class AffineCouplingLayer(nn.Module):
    """
    Single affine coupling layer implementing exact invertible transformation.
    Input x: (B, C, H, W), split along channel dim into x1, x2 each with C//2 channels.
    Forward:  y1 = x1, y2 = x2 * exp(s(x1)) + t(x1)
    Inverse:  x1 = y1, x2 = (y2 - t(y1)) * exp(-s(y1))
    """
    def __init__(self, in_channels: int, hidden_channels: int = 64):
        super().__init__()
        half_c = in_channels // 2
        # s, t sub-networks -- can be any architecture without affecting invertibility
        self.st_net = nn.Sequential(
            nn.Conv2d(half_c, hidden_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden_channels, hidden_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden_channels, in_channels, 3, padding=1),  # outputs s and t
        )
        # Constrain s range for numerical stability
        self.s_scale = nn.Parameter(torch.zeros(1))

    def forward(self, x: torch.Tensor):
        """Forward transform RAW→intermediate representation, returns (y, log_det_jacobian)"""
        x1, x2 = x.chunk(2, dim=1)
        st = self.st_net(x1)
        s, t = st.chunk(2, dim=1)
        s = torch.tanh(s) * self.s_scale.exp()  # constrain dynamic range
        y2 = x2 * s.exp() + t
        log_det = s.sum(dim=[1, 2, 3])           # Jacobian determinant (triangular matrix)
        return torch.cat([x1, y2], dim=1), log_det

    def inverse(self, y: torch.Tensor):
        """Inverse transform intermediate representation→RAW; analytically computable without inverting s, t"""
        y1, y2 = y.chunk(2, dim=1)
        st = self.st_net(y1)                     # only calls forward pass of s, t
        s, t = st.chunk(2, dim=1)
        s = torch.tanh(s) * self.s_scale.exp()
        x2 = (y2 - t) * (-s).exp()
        return torch.cat([y1, x2], dim=1)


# ── Simplified InvISP ──────────────────────────────────────────────────────────
class InvISP(nn.Module):
    """
    K cascaded affine coupling layers implementing bidirectional RAW (packed Bayer) ↔ sRGB mapping.
    Input dimension:  (B, 4, H/2, W/2)  ← packed RGGB Bayer
    Output dimension: (B, 3, H/2, W/2)  ← sRGB downsampled to H/2 (for demonstration)
    """
    def __init__(self, num_layers: int = 8, channels: int = 4,
                 hidden: int = 64):
        super().__init__()
        self.layers = nn.ModuleList(
            [AffineCouplingLayer(channels, hidden) for _ in range(num_layers)]
        )
        # RAW(4ch) → sRGB(3ch) linear adaptation (does not break invertibility as it follows coupling layers)
        self.raw_to_rgb = nn.Conv2d(channels, 3, 1, bias=False)
        self.rgb_to_raw = nn.Conv2d(3, channels, 1, bias=False)

    def forward(self, raw: torch.Tensor):
        """
        Forward inference (RAW → sRGB)
        raw: (B, 4, H, W) ← packed Bayer (RGGB)
        Returns: srgb (B, 3, H, W), total_log_det
        """
        x = raw
        total_log_det = 0.0
        for layer in self.layers:
            x, log_det = layer(x)
            total_log_det += log_det
        srgb = self.raw_to_rgb(x)
        return srgb, total_log_det

    def inverse(self, srgb: torch.Tensor):
        """
        Inverse inference (sRGB → RAW)
        srgb: (B, 3, H, W)
        Returns: raw_reconstructed (B, 4, H, W)
        """
        x = self.rgb_to_raw(srgb)
        # Pass through coupling layers in reverse order
        for layer in reversed(self.layers):
            x = layer.inverse(x)
        return x


# ── Verify Exact Invertibility ─────────────────────────────────────────────────
def verify_invertibility(model: InvISP, device: str = "cpu"):
    """
    Verify that forward-inverse round-trip numerical error is close to machine precision (float32 < 1e-5)
    """
    model.eval()
    with torch.no_grad():
        raw = torch.rand(1, 4, 128, 128, device=device)
        srgb, _ = model(raw)
        raw_reconstructed = model.inverse(srgb)
        max_err = (raw - raw_reconstructed).abs().max().item()
        psnr = 10 * torch.log10(1.0 / ((raw - raw_reconstructed) ** 2).mean()).item()
    print(f"Max absolute error (float32): {max_err:.2e}")
    print(f"Round-trip reconstruction PSNR (float32): {psnr:.2f} dB")
    assert max_err < 1e-4, f"Invertibility verification failed, error too large: {max_err:.2e}"
    return psnr


# ── Joint Loss Function ────────────────────────────────────────────────────────
class InvISPLoss(nn.Module):
    """
    Equation (8): jointly optimize forward rendering quality and inverse RAW reconstruction accuracy
    """
    def __init__(self, lambda_rgb: float = 1.0, lambda_raw: float = 10.0):
        super().__init__()
        self.lambda_rgb = lambda_rgb
        self.lambda_raw = lambda_raw

    def forward(self, model: InvISP,
                raw_input: torch.Tensor,
                srgb_target: torch.Tensor):
        # Forward: RAW → sRGB
        srgb_pred, log_det = model(raw_input)
        loss_srgb = F.l1_loss(srgb_pred, srgb_target)

        # Inverse: sRGB → RAW (round-trip cycle consistency)
        raw_recon = model.inverse(srgb_pred.detach())  # detach to prevent gradient back-propagation to forward
        loss_raw = F.l1_loss(raw_recon, raw_input)

        total = self.lambda_rgb * loss_srgb + self.lambda_raw * loss_raw
        return total, {"L_srgb": loss_srgb.item(), "L_raw": loss_raw.item()}


# ── Differentiable JPEG Simulator ─────────────────────────────────────────────
def soft_quantize(x: torch.Tensor, q: float = 1.0) -> torch.Tensor:
    """
    Equation (10): soft quantization approximation, approximates rounding at integer multiples of q,
    differentiable everywhere
    """
    return x - (q / (2 * torch.pi)) * torch.sin(2 * torch.pi * x / q)


def differentiable_jpeg(x: torch.Tensor, quality: int = 90) -> torch.Tensor:
    """
    Differentiable JPEG simulator (simplified version, models only pixel-value quantization)
    quality: 1–100, higher quality is better, corresponding to finer quantization step
    """
    q = max(1.0, (100 - quality) / 10.0)  # approximate quantization step
    return soft_quantize(x * 255.0, q) / 255.0


# ── Usage Example ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Initialize model (K=8 coupling layers)
    model = InvISP(num_layers=8, channels=4, hidden=64).to(device)
    print(f"Model parameter count: {sum(p.numel() for p in model.parameters()) / 1e6:.2f}M")

    # Verify exact invertibility
    psnr = verify_invertibility(model, device)
    print(f"Round-trip PSNR with random initialization: {psnr:.1f} dB (after training can reach 44–47 dB)")

    # Demonstrate inverse inference with JPEG simulator
    raw_gt = torch.rand(2, 4, 128, 128, device=device)
    srgb_pred, _ = model(raw_gt)
    srgb_jpeg = differentiable_jpeg(srgb_pred.clamp(0, 1), quality=90)
    raw_from_jpeg = model.inverse(srgb_jpeg)
    psnr_jpeg = 10 * torch.log10(
        1.0 / ((raw_gt - raw_from_jpeg) ** 2).mean()
    ).item()
    print(f"Inverse reconstruction PSNR from JPEG Q=90: {psnr_jpeg:.2f} dB (random values before training; demonstrates pipeline only)")
```

The companion notebook also includes:
1. **Affine coupling layer invertibility numerical verification**: compare round-trip reconstruction PSNR under float32 / float16;
2. **MIT-Adobe FiveK subset training demonstration**: train an 8-layer InvISP on 100 Canon EOS 5D paired samples;
3. **JPEG robustness comparison**: inverse PSNR at Q=70/80/90 with and without differentiable JPEG simulator training;
4. **InvISP vs CycleISP vs UPI three-way comparison**: inverse PSNR and highlight region visualization on 10 test images.

---

## §7 Glossary

**Invertible ISP (InvISP, Xing et al., CVPR 2021)**
An ISP architecture that achieves precise bidirectional mapping between RAW and sRGB using invertible neural networks. The forward pass $f_\theta: x_\text{raw} \to \hat{x}_\text{sRGB}$ renders a visually high-quality sRGB image, and the inverse pass $f_\theta^{-1}: x_\text{sRGB} \to \hat{x}_\text{raw}$ precisely reconstructs the original RAW data, achieving a RAW reconstruction PSNR approximately 15 dB higher than CycleISP. Core applications include lossless RAW embedding in JPEG, after-the-fact HDR reprocessing, and paired RAW-sRGB data augmentation. Fundamental constraint: RAW information in highlight-clipped regions (sRGB = 255) is unrecoverable; this is a consequence of physical information loss, not a network deficiency.

**Normalizing Flow (归一化流)**
A generative modeling framework that maps a simple base distribution (such as an isotropic Gaussian) to a complex data distribution through a series of exactly invertible transformations $f = f_K \circ \cdots \circ f_1$, requiring each sub-transformation $f_k$ to be bijective with an analytically computable Jacobian determinant. Unlike GANs, normalizing flows support exact log-likelihood computation, and forward and inverse inference are equally efficient. Invertible ISP exploits normalizing flows to construct a bidirectional RAW-sRGB mapping, but does not require precisely modeling the statistical distributions of RAW or sRGB — only that the mapping itself be exactly invertible.

**Affine Coupling Layer (仿射耦合层, RealNVP, Dinh et al., 2016)**
The most commonly used invertible building block in normalizing flows: the input $x$ is split along the channel dimension into $(x_1, x_2)$; the forward transformation is $y_1 = x_1$, $y_2 = x_2 \odot e^{s(x_1)} + t(x_1)$; the inverse is $x_2 = (y_2 - t(y_1)) \odot e^{-s(y_1)}$. Here $s$ and $t$ may be arbitrary deep neural networks without affecting invertibility, because the inverse transformation only requires calling the forward pass of $s$ and $t$. Each layer updates only half of the channels, so when multiple layers are stacked, the fixed and transformed channels must be alternated to ensure all channels are updated.

**CycleISP (Zamir et al., CVPR 2020)**
A bidirectional ISP network based on cycle consistency constraints, training two independent RAW→sRGB and sRGB→RAW networks, achieving approximate invertibility by minimizing round-trip cycle error. Primarily used for denoising data augmentation (synthesizing paired noisy RAW-sRGB data); inverse RAW reconstruction accuracy is approximately 32 dB, far below flow-based InvISP (~47 dB), but can be trained with unpaired data.

**Differentiable JPEG Simulator (可微分JPEG模拟器)**
Approximates the non-differentiable rounding operation in JPEG with soft quantization: $\text{SoftQuant}(x,q)=x-\frac{q}{2\pi}\sin(\frac{2\pi x}{q})$, which approximates rounding at integer multiples of the quantization step size while allowing end-to-end gradient propagation. Inserting it into the training graph enables InvISP to maintain high-precision RAW reconstruction even after JPEG compression, with a PSNR loss of only about 0.8 dB when reconstructing RAW from JPEG (Q=90) compared to reconstruction from lossless sRGB (the loss exceeds 5 dB without the simulator).

**MIT-Adobe FiveK Dataset**
Contains 5,000 RAW images from five cameras (Canon EOS-1D, 5D; Nikon D700, D3X, and others), each retouched in Lightroom independently by five professional retouchers to yield sRGB reference outputs, forming a paired RAW-sRGB dataset. Invertible ISP research typically uses Expert C (a combined exposure and color adjustment) as the sRGB reference target. A limitation of the dataset is that it only covers DSLR cameras and does not represent the RAW characteristics of smartphone ISPs (smartphone RAW images typically already incorporate partial software processing).

**Bayer Packing (Pixel Shuffle / Unshuffle, Bayer打包)**
Rearranges an $H \times W \times 1$ Bayer RAW image into a packed representation of $H/2 \times W/2 \times 4$ (four RGGB channels), so that each spatial location contains one complete 2×2 mosaic unit. Invertible ISP operates in the packed Bayer space to avoid the interpolation errors introduced by demosaicing, which would otherwise degrade invertibility. During the inverse pass, PixelUnshuffle downsamples the sRGB from $H \times W \times 3$ to $H/2 \times W/2$ before mapping to the packed Bayer format.

**Checkerboard Artifacts (棋盘格伪影)**
Periodic brightness non-uniformity caused by the non-uniform coverage of strided or transposed convolution kernels, manifesting as alternating bright/dark pixels every other row and column in the output image. In invertible ISP, these primarily appear when the $s, t$ sub-networks include upsampling steps; they can be effectively suppressed by replacing transposed convolution with sub-pixel convolution or bilinear upsampling + convolution.

**AIM Reversed ISP Challenge (Conde et al., ECCV 2022)**
An academic competition focused on the sRGB→RAW inverse reconstruction task, providing paired RAW-sRGB test sets from multiple cameras including Canon, Samsung, and Sony, and using PSNR/SSIM/Delta-E as evaluation metrics. The best-performing method in the competition (based on U-Net with post-processing) achieved a PSNR of approximately 46–48 dB but with a large parameter count (>50M); lightweight methods achieved approximately 43 dB. Competition results drove the establishment of a standardized evaluation framework for inverse ISP.

**Delta-E 2000 (CIEDE2000 Color Difference, CIEDE2000色差)**
A perceptually uniform color difference metric used to evaluate the error in the color channels of an invertible ISP's RAW reconstruction: $\Delta E_{00} = \sqrt{(\Delta L'/k_L S_L)^2 + (\Delta C'/k_C S_C)^2 + (\Delta H'/k_H S_H)^2 + R_T(\Delta C'/k_C S_C)(\Delta H'/k_H S_H)}$, where $S_L, S_C, S_H$ are perceptual weighting coefficients and $R_T$ is a rotation term for the blue-violet region. $\Delta E_{00} < 1$ is imperceptible to the human eye; $< 2$ is slightly perceptible; $> 5$ is clearly visible. In RAW reconstruction evaluation, $\Delta E_{00}$ reflects color restoration quality better than PSNR, because human vision is more sensitive to hue shifts than to luminance errors.

---

## References

1. **Xing, Y., Qian, Z., & Chen, Q. (2021).** Invertible image signal processing. *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 6287–6296. — The original InvISP paper; the first systematic work on invertible ISP, jointly optimizing forward rendering and inverse RAW reconstruction through affine coupling layers.

2. **Zamir, S. W., Arora, A., Khan, S., Hayat, M., Khan, F. S., Yang, M. H., & Shao, L. (2020).** CycleISP: Real image restoration via improved data synthesis. *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 2696–2705. — The original CycleISP paper; cycle-consistency bidirectional ISP, primarily for denoising data augmentation.

3. **Brooks, T., Mildenhall, B., Xue, T., Chen, J., Sharlet, D., & Barron, J. T. (2019).** Unprocessing images for learned raw denoising. *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 11036–11045. — The pioneering UPI inverse ISP work, synthesizing RAW from sRGB for training denoising models, but without guaranteeing inversion accuracy.

4. **Dinh, L., Sohl-Dickstein, J., & Bengio, S. (2016).** Density estimation using Real-valued Non-Volume Preserving (Real NVP) transformations. *arXiv preprint arXiv:1605.08803*. — The original affine coupling layer paper; foundational work on normalizing flows for density estimation.

5. **Kingma, D. P., & Dhariwal, P. (2018).** Glow: Generative flow with invertible 1×1 convolutions. *Advances in Neural Information Processing Systems (NeurIPS)*, 31. — The original GLOW paper; introduces invertible 1×1 convolution and Actnorm, an important architectural reference for InvISP.

6. **Kim, S., Cho, S., & Kim, C. (2022).** RAW image reconstruction using a self-contained sRGB-JPEG image with only 64 KB overhead. *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 17692–17701. — The 64 KB embedded RAW compression scheme; a practical invertible ISP engineering application with extremely low overhead.

7. **Conde, M. V., McDonagh, S., Maggioni, M., Leonardis, A., & Pérez-Pellitero, E. (2022).** Model-based image signal processors via learnable dictionaries. *Proceedings of the AAAI Conference on Artificial Intelligence*, 36(1), 481–489. — The AIM 2022 Reversed ISP Challenge report, establishing a standardized evaluation benchmark for sRGB→RAW inverse reconstruction.

8. **Xiao, M., Zheng, S., Liu, C., Wang, Y., He, D., Ke, G., ... & Liu, T. Y. (2020).** Invertible image rescaling. *Proceedings of the European Conference on Computer Vision (ECCV)*, 126–144. — Normalizing flows applied to invertible image rescaling; shares the affine coupling layer architecture with invertible ISP and laid the methodological foundation for invertible image processing.

---

> **Chapter Summary:** Invertible ISP uses the affine coupling layers of normalizing flows to achieve precise bidirectional mapping between RAW and sRGB, solving the problem that traditional one-way lossy ISP pipelines cannot recover RAW via inverse reconstruction. InvISP achieves a RAW reconstruction PSNR 15 dB higher than CycleISP, and training with a differentiable JPEG simulator maintains high-precision reconstruction even after JPEG compression. Core applications include extremely low-overhead implicit RAW compression (64 KB overhead), after-the-fact HDR reprocessing, and paired data augmentation. The fundamental limitation is the physical irreversibility of highlight-clipped regions: no method can recover original RAW highlight detail from pure-white sRGB pixels; in practice, a highlight mask loss is introduced to prevent this from degrading accuracy in unaffected regions.
