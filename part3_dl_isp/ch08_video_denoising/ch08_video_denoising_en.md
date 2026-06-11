# Part 3, Chapter 08: Deep Learning Video Denoising and Video ISP

> **Positioning:** This chapter provides a systematic treatment of deep learning applied to video denoising and video ISP, covering the temporal signal model, major methods including FastDVDnet, EDVR, and BasicVSR, and the complete pipeline from inter-frame alignment and temporal fusion to RAW video processing.
> **Prerequisites:** Part 2, Chapter 03 (Image Denoising), Part 2, Chapter 12 (Traditional Temporal Noise Reduction TNR), Part 3, Chapter 02 (End-to-End Image Restoration)
> **Target Readers:** Video ISP algorithm engineers, deep learning researchers
> **Scope note:** This chapter covers **deep learning** video denoising methods (FastDVDnet / EDVR / BasicVSR / RVRT / RAW-domain video denoising). Traditional TNR (BMA/optical-flow motion estimation, IIR filtering, Qualcomm MCTF / MediaTek TNR Node implementation) is fully covered in **Part 2, Chapter 12**. §1.1 briefly reviews the traditional baseline for cross-reference.

---

## §1 Theory

### 1.1 Signal Model for Video Denoising

Video denoising is fundamentally an inverse problem: jointly exploiting redundancy in the spatiotemporal domain to recover a clean frame sequence. Unlike single-image denoising, video provides an additional **temporal dimension** of redundancy — pixels corresponding to the same scene location in static regions of adjacent frames theoretically share the same ground-truth value, allowing cross-frame aggregation to suppress noise.

**Basic signal model** (additive white Gaussian noise, AWGN):

$$y_t = x_t + n_t, \quad n_t \sim \mathcal{N}(0, \sigma^2 \mathbf{I})$$

Here $y_t$ is the observed (noisy) image at frame $t$, $x_t$ is the clean frame to be recovered, $n_t$ is zero-mean isotropic Gaussian noise, and $\sigma$ is the noise standard deviation.

**RAW-domain noise model** (Poisson-Gaussian mixture, closer to real sensor behavior):

$$y_t = \alpha \cdot \text{Poisson}\!\left(\frac{x_t}{\alpha}\right) + \mathcal{N}(0, \beta^2)$$

where $\alpha$ is the photon gain and $\beta$ is the read-noise standard deviation. Under high-ISO or low-light conditions the Poisson component dominates; under well-exposed conditions the two terms mix. RAW-domain noise parameters can be measured in advance through noise calibration (噪声标定) during factory testing, or estimated adaptively at runtime.

**Additional complexity of temporal video noise:** In real video, noise is not strictly independent across time — scene motion causes the same scene position to map to different pixel coordinates in different frames. If inter-frame motion is not handled, naively averaging pixel values across time produces motion blur (运动模糊). If motion estimation is inaccurate, ghosting artifacts (残影/鬼影) appear instead. This is precisely the core difficulty that distinguishes video denoising from single-frame denoising.

### 1.2 Core Challenges in Video Denoising

| Challenge | Specific Problem | Traditional Response | Deep Learning Response |
|-----------|-----------------|---------------------|------------------------|
| Inter-frame alignment accuracy | Misregistration due to motion estimation errors | Block matching (BM), optical flow (OF) | Deformable convolution (DCN), implicit alignment |
| Occluded regions | Newly appearing/disappearing areas have no reference correspondence | Weighted fusion to reduce occlusion weight | Attention mechanism for adaptive weighting |
| Fast motion | Optical flow exceeds search range | Multi-scale pyramid search | Multi-scale feature pyramid alignment (PCD) |
| Scene cuts | No preceding frame available after a shot change | Scene detection followed by reset | Implicit state reset in recurrent networks |
| Complex noise | Non-Gaussian, structured noise (e.g., fixed-pattern noise, FPN) | Per-frame processing; temporal NR fails | End-to-end DL denoising in RAW domain |
| Real-time constraints | Limited compute on mobile/embedded platforms | Lightweight block matching | Lightweight networks, knowledge distillation |

### 1.3 Taxonomy of Inter-Frame Alignment Methods

Inter-frame alignment is the prerequisite step in video denoising; its accuracy directly determines the quality of subsequent fusion. Three main categories exist:

**(1) Explicit Optical Flow Warp**

An optical flow estimation network (e.g., PWC-Net, RAFT) first computes the dense flow field $\mathbf{v}_{t \to t+k}$ from reference frame $t$ to neighboring frame $t+k$, and the neighboring frame is then backward-warped via bilinear interpolation:

$$\tilde{y}_{t+k \to t}(p) = y_{t+k}\!\left(p + \mathbf{v}_{t \to t+k}(p)\right)$$

Advantages: physically interpretable; the flow can be supervised independently. Disadvantages: the flow estimation itself carries errors; at discontinuous motion boundaries (occlusion boundaries) the optical flow assumption breaks down, and errors propagate downstream.

**(2) Deformable Convolution Alignment (DCN)**

DCNv2, proposed by Dai et al., lets the network automatically learn sampling offsets $\{\Delta p_k\}$, implicitly achieving spatial alignment:

$$y'(p) = \sum_{k=1}^{K} w_k \cdot m_k \cdot x\!\left(p + p_k + \Delta p_k\right)$$

where $p_k$ are the preset offsets of a standard convolution, while $\Delta p_k$ and modulation coefficients $m_k$ are both predicted by the network. Compared with explicit optical flow, DCN is more robust to occlusion and non-rigid motion, and alignment and feature extraction can be jointly optimized end-to-end.

**(3) Implicit Temporal Fusion (Blind Temporal Fusion)**

Methods such as FastDVDnet abandon explicit alignment entirely, concatenating multiple adjacent frames and feeding them directly into a convolutional network, letting the network learn temporal alignment and fusion implicitly through its receptive field. The cost is that a larger receptive field is required, but alignment error propagation is eliminated and inference is faster.

### 1.4 Optical Flow Alignment vs. Deformable Convolution Alignment: Engineering Trade-offs

The two dominant alignment paradigms differ in interpretability, robustness, and hardware-deployment characteristics:

| Dimension | Optical Flow Warp (OF) | Deformable Convolution (DCN) |
|-----------|----------------------|------------------------------|
| **Modularity** | Flow network (e.g., SpyNet/RAFT) is independently deployable and replaceable | Offset prediction is coupled with feature extraction; inseparable |
| **Interpretability** | Flow vectors have clear physical meaning; easy to visualize and debug | Offsets lack a direct physical interpretation; debugging is harder |
| **Large-motion robustness** | Requires pyramid search; RAFT handles large displacement but has 5M+ parameters | PCD cascade naturally handles large motion; parameters integrated in the main network |
| **Occlusion handling** | Requires explicit forward-backward consistency check for occlusion detection | Modulation weight $m_k$ automatically suppresses occluded sampling points |
| **NPU deployment** | Flow estimation supported by dedicated operators on HVX/APU; warp is simple bilinear interpolation | DCNv2 natively supported in SNPE 2.x; offset prediction branch adds memory bandwidth |
| **Frame latency** | Flow computation ~5–10 ms (720p, SpyNet INT8) | DCN offset prediction < 3 ms (embedded in the main network forward pass, not run independently) |
| **Representative methods** | BasicVSR (SpyNet + warp), RViDeNet | EDVR (PCD DCNv2), BasicVSR++ (flow-guided DCN) |

**Engineering selection guidelines:**
1. **Ample compute, accuracy-first (flagship NPU):** DCN (EDVR/BasicVSR++) — joint optimization of offsets and features yields the best accuracy.
2. **Compute-constrained, latency-sensitive (mid-range device):** SpyNet (lightweight flow, ~1M parameters) + bilinear warp — controllable latency, with hardware-accelerated flow on ISP DSP.
3. **No explicit alignment (ultra-low-power embedded):** FastDVDnet implicit alignment — no alignment error propagation, smallest parameter count; the preferred choice for embedded deployment.
4. **RAW-domain processing:** Direct flow estimation in the Bayer domain suffers from channel non-uniformity; the DCN approach (Bayer-aware DCN in RViDeNet) is preferred.

---

## §2 Main Methods

### 2.1 V-BM4D — Traditional Baseline (Maggioni et al., TIP 2012)

V-BM4D is the video extension of BM3D, generalizing 3D block matching to the spatiotemporal fourth dimension: similar blocks are searched in the spatial domain and, simultaneously, motion-compensated similar blocks are searched across several reference frames in the temporal domain. The resulting 4D array is processed by collaborative sparse-transform filtering (Wiener filtering).

V-BM4D serves as an important comparison baseline for deep learning methods. Its main limitations are: high computational cost for block matching (unsuitable for real-time use), and poor adaptability to fast non-rigid motion. On the Set8 dataset ($\sigma=30$) it achieves approximately 36.05 dB PSNR — the top tier of traditional methods — but is clearly surpassed by approaches such as FastDVDnet.

### 2.2 FastDVDnet (Tassano et al., CVPR 2020)

FastDVDnet is the first deep learning video denoising method to achieve real-time speed without optical flow estimation. Its central idea is to replace the explicit optical-flow-plus-warping pipeline with a **two-stage U-Net**.

**Network architecture:**

The input consists of 5 consecutive frames centered on the current frame $t$, $\{y_{t-2}, y_{t-1}, y_t, y_{t+1}, y_{t+2}\}$, together with a noise-level map $\sigma$. Processing proceeds in two stages:

- **Stage 1** (Denoising-Net): denoises pairs of adjacent frames together with the noise map to produce coarse denoised results. Three parallel Stage-1 sub-networks handle the frame pairs $(t{-}2, t{-}1)$, $(t, t{+}1)$, and $(t{+}1, t{+}2)$:
$$\tilde{f}_{t-1} = f_1(y_{t-2}, y_{t-1}; \sigma), \quad \tilde{f}_{t} = f_1(y_t, y_{t+1}; \sigma), \quad \tilde{f}_{t+1} = f_1(y_{t+1}, y_{t+2}; \sigma)$$

- **Stage 2** (Temporal-Net): fuses the three Stage-1 outputs to produce the final denoised result:
$$\hat{x}_t = f_2(\tilde{f}_{t-1}, \tilde{f}_t, \tilde{f}_{t+1}; \sigma)$$

**Implicit alignment without explicit optical flow:** The Stage-1 U-Net's multi-scale down-sampling and up-sampling yields a large enough receptive field to implicitly perform motion compensation between adjacent frames inside the network. This avoids the propagation of optical flow estimation errors, and Stage-1 weights are **shared** across different frame pairs, keeping the total parameter count at only about 2.5M.

**Performance:** On the Set8 dataset ($\sigma=30$) FastDVDnet achieves 31.68 dB PSNR (color video). On an RTX 2080 Ti it processes $512\times512$ frames at approximately 100 fps, marking a real-time breakthrough for deep learning video denoising.

**Blind vs. non-blind:** FastDVDnet is a **non-blind denoiser** that requires the noise level $\sigma$ as input, but it can be extended to blind denoising via online noise estimation (see §5.3).

### 2.3 EDVR (Wang et al., CVPRW 2019)

EDVR (Enhanced Deformable Convolution for Video Restoration) was the winning solution in the NTIRE 2019 video super-resolution challenge. It introduces two key modules:

**PCD Alignment Module (Pyramid, Cascading and Deformable Convolution):**

To handle large-motion scenarios, PCD uses a **multi-scale pyramid structure** for coarse-to-fine cascaded alignment:

1. Extract a 3-level feature pyramid $\{F_t^l\}_{l=1}^{3}$ from both the reference frame and each neighboring frame ($l=3$ is the lowest resolution);
2. At the coarsest scale $l=3$, concatenate reference-frame features with neighboring-frame features, then use DCNv2 to predict offsets $\Delta p^3$ and apply deformable alignment to the neighboring-frame features;
3. Upsample the aligned result to scale $l=2$, concatenate with features at that scale, and predict offsets $\Delta p^2$ again (the **cascaded** design means each level need only predict residual offsets, reducing the burden per level);
4. Repeat until $l=1$ to obtain aligned features $\hat{F}_{t+k}^1$.

**TSA Fusion Module (Temporal and Spatial Attention Fusion):**

The aligned multi-frame features are weighted by **temporal attention**, allowing the network to learn automatically which regions of which frames are most useful for the current frame:

$$\alpha_{t+k} = \text{Sigmoid}\!\left(\text{Conv}\!\left(\left[\hat{F}_{t+k}^1, F_t^1\right]\right)\right)$$

$$F_{\text{fused}} = \sum_{k \in \mathcal{N}} \alpha_{t+k} \odot \hat{F}_{t+k}^1$$

where $\odot$ denotes element-wise multiplication and $\mathcal{N}$ is the neighborhood window around the reference frame (typically $\pm 2$, i.e., 5 frames). A **spatial attention** module further refines the features after temporal attention fusion.

**Performance:** REDS4 test-set PSNR of 31.09 dB (official super-resolution task), approximately 20.6M parameters — far exceeding all competing methods at the time.

### 2.4 BasicVSR / BasicVSR++ (Chan et al., CVPR 2021 / CVPR 2022)

**BasicVSR** systematically analyzes four fundamental components of video super-resolution (VSR): propagation (传播), alignment (对齐), aggregation (聚合), and upsampling (上采样), and proposes the simplest effective framework: **bidirectional propagation with optical-flow alignment**.

**Bidirectional propagation formulas:**

Forward hidden state:
$$h_t^{\text{fwd}} = \mathcal{G}\!\left(x_t,\ \text{warp}(h_{t-1}^{\text{fwd}},\ \mathbf{v}_{t \to t-1})\right)$$

Backward hidden state:
$$h_t^{\text{bwd}} = \mathcal{G}\!\left(x_t,\ \text{warp}(h_{t+1}^{\text{bwd}},\ \mathbf{v}_{t \to t+1})\right)$$

The forward and backward hidden states are concatenated and passed into a reconstruction network $\mathcal{R}$:
$$\hat{x}_t = \mathcal{R}\!\left([h_t^{\text{fwd}};\ h_t^{\text{bwd}}]\right)$$

Here $\mathcal{G}$ is a feature extraction and fusion function (ResNet blocks) and $\mathbf{v}_{t \to t-1}$ is the optical flow estimated by SpyNet. Bidirectional propagation lets every frame exploit both past (forward) and future (backward) frame information simultaneously, greatly improving temporal consistency. BasicVSR has only 6.3M parameters and achieves 31.42 dB PSNR on REDS4, offering a notably superior cost-performance ratio compared with EDVR.

**Improvements in BasicVSR++:**

1. **Second-order propagation:** The hidden state aggregates not only the immediately preceding frame but also history cascaded across two frames, enabling stronger modeling of long-range temporal dependencies;
2. **Deformable alignment replaces optical flow:** SpyNet + warp is replaced by DCNv2, with offsets jointly predicted from reference and propagated features;
3. Flow-guided (流引导) deformable convolution is introduced, combining optical flow priors to improve DCN offset initialization.

BasicVSR++ raises PSNR on REDS4 to 32.39 dB while increasing the parameter count only slightly, to 7.3M.

### 2.5 RVRT (Recurrent Video Restoration Transformer, Liang et al., NeurIPS 2022)

RVRT brings the Transformer into video restoration, replacing convolutions with **local window attention** and introducing **Guided Deformable Attention** specifically designed for video temporal sequences.

**Locally-Shifted Window Attention:** Drawing on the shifted-window strategy of SwinIR, self-attention is computed within local windows of video frames, reducing the Transformer's quadratic complexity to linear complexity.

**Temporally Guided Deformable Attention:** The current-frame features serve as queries; attention offsets are predicted from the propagated hidden state (cross-frame information), allowing the Transformer's key-value pairs to dynamically sample relevant positions along the temporal dimension for precise cross-frame information aggregation.

RVRT combines recurrent propagation with Transformers, reaching 40.33 dB PSNR on Vimeo-90K super-resolution — the state of the art at the time. However, its inference speed on 720p video is approximately **1 fps**, which has no practical value on mobile devices. It is best treated as an offline quality ceiling reference or as a teacher model for distilling lighter-weight student networks.

---

## §3 Integration with ISP

### 3.1 RAW-Domain Video Denoising

In a traditional ISP pipeline, the temporal noise reduction (时域降噪, TNR) module typically runs in the RAW domain **before** demosaicing (色彩插值). This has two advantages: first, the RAW-domain noise distribution obeys a physical model (Poisson-Gaussian mixture), enabling accurate noise modeling; second, it prevents demosaicing from spreading noise across color channels (demosaicing is a spatial interpolation operation that introduces inter-channel correlations).

**RViDeNet (Yue et al., CVPR 2020)** is the first end-to-end deep learning RAW video denoising method, with the following key contributions:

- It introduces the **DRV (Dynamic Raw Video)** dataset: paired noisy/clean RAW video sequences captured with a Sony A7R III, covering dynamic scenes (human motion, camera shake), filling the gap of having no publicly available dataset for RAW video denoising;
- It designs a **noise-aware feature alignment** module that performs inter-frame feature alignment directly in the RAW domain (without prior demosaicing), handling the non-uniformity introduced by the Bayer pattern via deformable convolution;
- It explicitly models Poisson-Gaussian noise parameters (simulated gain $K$ and read-noise variance $\sigma_r^2$) in the network, feeding them as noise conditioning signals.

The key difficulty of RAW-domain video denoising lies in the **non-uniformity of the Bayer pattern**: standard convolution cannot directly process the Bayer image (R/G/B channels are sampled at different spatial positions), so the Bayer image must typically be packed (打包) into 4 channels (RGGB) before processing.

### 3.2 Placement of DL Temporal NR in the Video ISP Pipeline

The position of deep learning temporal NR in an ISP pipeline differs from that of traditional TNR:

```
Traditional ISP pipeline (TNR in RAW domain):
RAW → BLC → LSC → [RAW-domain TNR (block matching)] → Demosaic → AWB → CCM → Denoise(2D) → Sharpen → TMO → Encode

Deep learning ISP pipeline (Option A: DL-TNR in RAW domain):
RAW → BLC → LSC → [DL RAW Video NR (e.g. RViDeNet)] → Demosaic → AWB → CCM → TMO → Encode

Deep learning ISP pipeline (Option B: DL-TNR in RGB domain):
RAW → BLC → Demosaic → [DL RGB Video NR (e.g. FastDVDnet/EDVR)] → AWB → CCM → TMO → Encode
```

**Comparison of the two options:**

| Dimension | RAW-domain DL-NR | RGB-domain DL-NR |
|-----------|-----------------|-----------------|
| Noise modeling accuracy | High (close to physical model) | Medium (noise distribution becomes complex after ISP processing) |
| Dataset acquisition difficulty | High (requires paired RAW video) | Low (synthetic noise is relatively easy to generate) |
| Deployment complexity | High (must be embedded in the front end of the ISP) | Low (can be inserted as a post-processing module) |
| Coupling with other ISP modules | Strong (affects subsequent demosaicing etc.) | Weak (independent module) |

### 3.3 Mobile Video ISP in Practice

**Apple Action Mode (iPhone 14, 2022):** Employs a joint processing framework combining electronic image stabilization (EIS) with deep learning video NR. EIS crops the video edges to compensate for camera shake; the deep learning NR then performs temporal multi-frame fusion denoising on the stabilized cropped video, fully exploiting the improved inter-frame alignment after stabilization to deliver high-quality, low-noise output at 2.8K resolution and 60 fps.

**Google Night Sight Video (Pixel 7, 2022):** A deep learning NR solution designed specifically for low-light video. The core technique is **multi-frame DL alignment and fusion**: within the time window corresponding to each output frame, the system applies learnable motion estimation and weighted fusion across multiple frames, achieving real-time (30 fps) video denoising under extremely low light (EV −5 and below). According to Google's technical blog, the temporal fusion module adopts a bidirectional propagation architecture similar to BasicVSR, with extensive INT8 quantization and operator fusion optimizations for the mobile platform.

### 3.4 Codebook-Prior Methods for Low-Light Enhancement: GLARE (ECCV 2024)

All of the above approaches are **discriminative** frameworks — they directly map degraded video to clean video. Starting in 2024, generative-prior methods have begun to be applied to the low-light enhancement task.

**GLARE (Zhou et al., ECCV 2024) [10]** (note: this GLARE refers specifically to low-light *image* enhancement; it is distinct from a same-named de-flare paper also at ECCV 2024) is a low-light image enhancement method based on **VQ codebook retrieval** — not a video diffusion model. Its core idea is to construct an offline vector-quantized codebook (VQ Codebook) from normal-exposure images; at inference time an invertible latent normalizing flow (I-LNF) aligns low-light features into the codebook space, and an adaptive feature transformation module (AFT/AMB) completes the enhancement in a single forward pass without multi-step diffusion sampling.

Key design elements:
- **VQ Codebook:** Built on large-scale normal-exposure images; stores high-quality texture and luminance priors; retrieval is unaffected by low-light degradation.
- **I-LNF (Invertible Latent Normalizing Flow):** Transforms the low-light feature distribution into the codebook space, ensuring correct codeword retrieval.
- **AFT/AMB (Adaptive Feature Transform / Adaptive Mixing Block):** Fuses low-light structural information with the codebook prior; dual decoders separately optimize fidelity and perceptual quality.

**Engineering characteristics:** Single-pass inference has substantially lower compute overhead than diffusion-based methods (e.g., LDM-LLIE requires 100+ sampling steps), making it suitable for on-device real-time or near-real-time low-light preprocessing. GLARE achieves SOTA on LOL and similar benchmarks and has been validated for low-light object-detection preprocessing. For video, it can be applied frame-independently; inter-frame consistency requires additional temporal smoothing.

### 3.5 Mamba Architecture for Video Denoising (2024)

The self-attention mechanism in Transformers has $O(N^2)$ complexity for sequence length $N$, making full-frame attention over high-resolution video frames ($1080p \approx 2M$ pixels) prohibitively expensive. **Mamba** (Gu & Dao, NeurIPS 2023) is based on a Structured State Space Model (SSM, specifically the S4/S6 formulation) and models long-range sequence dependencies in $O(N)$ linear complexity, and it has rapidly been adopted for video denoising.

**Mamba core: Selective State Space (S6)**

The standard linear recurrence:

$$h_t = A h_{t-1} + B x_t, \quad y_t = C h_t$$

where $h_t \in \mathbb{R}^d$ is the hidden state and $A, B, C$ are system matrices. The key innovation of Mamba (S6) is that $B$, $C$, and the discretization step $\Delta$ all become **input-dependent** learnable functions, enabling the model to selectively retain or forget history based on content — a property naturally beneficial for distinguishing moving and static regions in video.

**VideoMamba (Li et al., ECCV 2024) [11] for video denoising:**

VideoMamba extends Mamba's 1D sequence scan to the **3D spatiotemporal domain** via a bidirectional spatiotemporal scan:

$$\text{scan}_\text{ST}(V) = \text{MambaSSM}\!\left(\text{Flatten}_{t,h,w}(V)\right) \oplus \text{MambaSSM}\!\left(\text{Flip}_{t,h,w}(V)\right)$$

The forward scan covers past-frame information; the backward scan covers future-frame information. Their combination is functionally equivalent to BasicVSR's bidirectional propagation but without maintaining explicit frame buffers: the SSM hidden state propagates cross-frame information automatically during the scan.

**Comparison with Transformer/CNN methods (DAVIS 2017, σ=30, color PSNR):**

| Method | Architecture | PSNR (dB) | Parameters | 720p@30fps feasibility |
|--------|-------------|-----------|-----------|------------------------|
| FastDVDnet [1] | CNN (no explicit alignment) | 33.52 | 2.5M | Feasible |
| RVRT [5] | Transformer + recurrence | 36.57 | 10.8M | ⚠️ Slow (~1 fps) |
| VideoMamba (denoising fine-tune) [11] | Mamba SSM | 35.1 | 7.6M | ⚠️ NPU adaptation in progress |

**Engineering significance and limitations:**
- **Advantage:** Linear complexity makes VideoMamba's memory footprint on long sequences (>30 frames) roughly 40% lower than RVRT, which is valuable when long-range temporal context is needed (e.g., slow-motion cross-frame fusion).
- **Current limitation:** The custom CUDA kernel (`selective_scan`) in Mamba's selective SSM has no native operator support on mobile NPUs (Qualcomm HTP, MediaTek APU) as of 2024. Deployment requires decomposing it into an equivalent RNN unrolling, which in practice produces higher latency than FastDVDnet.
- **Research trend (2024):** Follow-on works including MambaVSR and VideoMambaPro are addressing the impact of spatial scan order on image quality (Z-order vs. Hilbert-curve scan). Native NPU operator support is expected to mature in 2025–2026, at which point Mamba-based methods may become practically deployable.

---

## §4 Artifacts

### 4.1 Temporal Flicker

**Symptom:** In the output sequence, static background regions exhibit frame-to-frame jumps in luminance or color (flickering), perceptible to the eye as stroboscopic blinking even when the scene itself is completely stationary. The flicker index $E_{\text{flicker}}$ is noticeably higher than in the undenoised input.

**Root cause:** When the denoising network processes adjacent frames independently (no temporal consistency constraint), each frame's noise estimate differs slightly, causing the network's output luminance at the same scene position to vary between adjacent frames. FastDVDnet-style methods mitigate this through the two-stage U-Net's implicit alignment, but for scenes with large camera motion the per-frame pixel correspondence is imprecise, causing fusion-weight fluctuations that produce flicker.

**Diagnosis:** Compute the sequence mean flicker index $E_{\text{flicker}} = \frac{1}{T-1}\sum|\bar{Y}(\hat{x}_t) - \bar{Y}(\hat{x}_{t-1})|$; use the tOF metric to measure output flow deviation from GT flow; evaluate separately on static-camera segments — persistent flicker there indicates frame-independent processing rather than alignment error.

**Mitigation:**
- Add a temporal consistency loss during training: $\mathcal{L}_{\text{temp}} = \|O_t - \mathcal{W}(O_{t-1}, F_{t\to t-1})\|_1 \cdot M_t$, with weight $\lambda_{\text{temp}} \in [0.1, 0.3]$;
- Introduce a hidden-state smoothing constraint in BasicVSR-style bidirectional propagation;
- Apply post-hoc per-frame mean-luminance normalization (histogram matching) to the output sequence to eliminate systematic drift.

### 4.2 Ghosting Artifacts from Motion Estimation Failure

**Symptom:** The edges of moving objects (pedestrians, vehicles, hands) exhibit semi-transparent double-images — foreground object contours are blurred, and background content bleeds through from beneath. Multi-frame fusion actually degrades quality in motion regions relative to single-frame denoising.

**Root cause:** Optical flow estimation or DCN alignment breaks down at occlusion boundaries, in fast motion (displacement exceeding the search range), and in non-rigid motion (e.g., flapping fabric). Incorrect alignment in failure regions causes content from a wrong frame to be merged, producing ghosting. In EDVR's PCD alignment, if the coarse-scale ($l=3$) offset prediction error exceeds the correction capacity of finer scales, the cascaded error manifests as residual ghosting in the output.

**Diagnosis:** Visualize the DCN offset field (arrow heat map); check whether offset directions and magnitudes in motion regions are plausible. Compute a Ghost Score $= \frac{1}{|\mathcal{M}|}\sum_{p\in\mathcal{M}}|\hat{x}_p - x_p^{\text{ref}}|$ where $\mathcal{M}$ is the motion mask.

**Mitigation:**
- Strengthen attention weight suppression in motion regions within the TSA fusion module: let $\alpha_{t+k} \to 0$ for motion regions, falling back to single-frame processing;
- For regions with low flow confidence (forward-backward flow consistency error above a threshold), force use of the reference frame rather than the aligned frame;
- Augment the training data with deliberately misaligned samples to improve robustness against ghosting.

### 4.3 Motion Edge Oversmoothing

**Symptom:** Edges of fast-moving objects (running pedestrians, spinning fan blades) show directional smearing, with detail loss and edge sharpness noticeably lower than in static regions.

**Root cause:** Temporal fusion across multiple frames at motion edges averages edge positions from different time instants, effectively applying a low-pass filter along the motion direction. Even with accurate alignment, a moving object's position shifts across the $\pm2$-frame time window, causing the merged edge to spread. Networks trained with L2 loss are especially prone to outputting "safe" mean solutions that exacerbate edge blurring.

**Diagnosis:** Compute per-frame MTF (modulation transfer function) on a fast-motion sequence; compare MTF50 between motion regions and static regions. A difference exceeding 15% indicates significant motion-edge oversmoothing.

**Mitigation:**
- Replace pure L2 loss with L1 + gradient loss to preserve high-frequency edge content;
- Reduce the number of temporal fusion frames in high-confidence motion regions (optical flow magnitude > 8 pixels/frame), falling back to 3-frame instead of 5-frame fusion;
- Append a sharpening module (Unsharp Mask or learnable sharpening filter) after the network to selectively recover motion-edge detail.

### 4.4 Cross-Frame Color Drift

**Symptom:** Adjacent frames of the denoised video show subtle but perceptible differences in color temperature or saturation at the same scene location, especially in mixed-illumination scenes (incandescent + daylight) or during AWB gain transitions between frames.

**Root cause:** When the network operates in the sRGB domain and the AWB gain exhibits small inter-frame fluctuations (during the transition phase of exponential smoothing $g_t = \alpha g_t + (1-\alpha)g_{t-1}$), temporal fusion blends frames with different color temperatures, producing inconsistent output colors in adjacent frames. In RAW-domain methods (RViDeNet), unnormalized AWB across frames produces similar effects.

**Diagnosis:** Extract per-channel (R/G/B) mean values for each frame and plot as a time series. A high-frequency oscillation (adjacent-frame mean difference > 0.01 DN, normalized) indicates color drift.

**Mitigation:**
- Before multi-frame fusion, normalize all frames to the reference frame's AWB gain space;
- Introduce a cross-frame color consistency loss constraining the mean color difference between adjacent frames in non-motion regions;
- For RAW-domain methods, perform AWB normalization before frame alignment to ensure all frames share the same color space during fusion.

### 4.5 Artifact Summary Table

| Artifact type | Trigger condition | Typical symptom | Mitigation |
|--------------|------------------|----------------|------------|
| Temporal flicker | No temporal constraint; frame-independent processing | Static background luminance jumps | Temporal consistency loss; bidirectional propagation hidden state |
| Motion ghosting | DCN/flow alignment failure | Semi-transparent double image on moving objects | TSA motion-region weight suppression; flow-confidence filtering |
| Motion-edge smearing | Multi-frame averaging; L2 loss | Directional trail blur on fast-motion edges | L1 + gradient loss; reduce frame count in motion regions |
| Cross-frame color drift | AWB inter-frame fluctuation; unnormalized | Adjacent-frame color temperature/saturation mismatch | AWB normalization preprocessing; color consistency loss |
| Shot-cut residual | Shot-change detection miss | Previous scene content bleeds into early frames of new scene | Lower shot-change detection threshold; reset frame buffer |

---

## §5 Tuning

### 5.1 Choosing the Number of Reference Frames

Increasing the number of reference frames introduces more temporal information but raises latency and memory overhead, and the marginal benefit diminishes beyond a certain frame count. In practice a trade-off between quality and real-time performance must be made:

| Frame count | Representative method | PSNR gain (vs. single frame, Set8 σ=30) | Theoretical latency | GPU memory (1080p) | Applicable scenario |
|------------|----------------------|----------------------------------------|--------------------|--------------------|---------------------|
| 1 (single frame) | DnCNN | Baseline (~30.0 dB) | Lowest | ~0.5 GB | Real-time hardware acceleration |
| 2 (current + 1 previous) | Simple recursive NR | +0.5–0.8 dB | Low | ~0.8 GB | Low-latency streaming |
| 5 (±2 frames) | FastDVDnet | +1.2–1.5 dB | Medium (~2-frame delay) | ~2 GB | Mobile mainstream |
| 7 (±3 frames) | EDVR (5-frame) / BasicVSR | +1.5–1.8 dB | Medium-high | ~3 GB | PC-side post-processing |
| 11+ | BasicVSR++ bidirectional | +2.0–2.5 dB | High (buffering needed) | ~6 GB | Offline processing |

**Engineering recommendation:** Mobile real-time video NR typically uses 3–5 frames; offline enhancement (e.g., short-video editing) can use 7–11 frames for higher quality.

### 5.2 Tuning for Motion Scene Adaptability

**Optical flow confidence threshold (for methods with explicit optical flow alignment):**

Optical flow networks typically output uncertainty estimates for the flow (or confidence can be computed via a forward-backward flow consistency check):

$$c(p) = \exp\!\left(-\frac{\|\mathbf{v}_{t\to t+1}(p) + \mathbf{v}_{t+1\to t}(\tilde{p})\|^2}{2\tau^2}\right)$$

where $\tilde{p} = p + \mathbf{v}_{t\to t+1}(p)$ is the warped coordinate and $\tau$ is the confidence temperature parameter (typical value 1.0). In low-confidence regions (occlusions, fast motion), the **temporal fusion weight should be reduced**, falling back to purely spatial denoising to avoid ghosting:

$$w_{\text{temporal}}(p) = c(p) \cdot w_{\text{base}}$$

**Tuning guidelines:**
- $\tau$ too small: too many regions are classified as low-confidence, temporal information is underutilized, PSNR drops;
- $\tau$ too large: poor-quality alignments are accepted, ghosting/double-image artifacts appear;
- In practice, first visualize flow heat maps and output ghosting on a motion test sequence (e.g., DAVIS sequences with fast motion), then manually binary-search for $\tau$.

**TSA attention heat map analysis (for EDVR-type methods):**

Visualize the temporal attention weights $\alpha_{t+k}$ output by the TSA module. A correctly trained model should exhibit:
1. $\alpha$ values in motion regions significantly lower than in static backgrounds;
2. Near occlusion boundaries, $\alpha$ decays smoothly rather than abruptly (to avoid blocking artifacts).

If motion-region $\alpha$ values are anomalously high (the network is incorrectly assigning high weight to misaligned frames), this usually means the proportion of dynamic scenes in the training data is insufficient.

### 5.3 Blind Noise Level Estimation

In real deployment the noise level $\sigma$ is often unknown or time-varying (e.g., ISO switching due to changing light during video recording). Common online $\sigma$ estimation methods:

**Method 1: MAD estimator based on pixel differences**

$$\hat{\sigma} = \frac{\text{median}(|y_{t,\text{HF}}|)}{0.6745}$$

where $y_{t,\text{HF}}$ is the high-frequency component of the current frame extracted by a high-pass filter (e.g., the highest-frequency subband of the Haar wavelet). This method has extremely low computational cost and is suitable for real-time embedded scenarios.

**Method 2: Frame-difference estimation (for static scenes)**

When the camera is stationary, the inter-frame difference $\delta_t = y_t - y_{t-1}$ consists mainly of noise:

$$\hat{\sigma} = \frac{1}{\sqrt{2}} \cdot \text{std}(\delta_t)$$

This applies to static shot segments during video recording and can be combined with a motion detection module for automatic switching.

**Method 3: Noise-conditional network**

Camera ISP metadata (ISO, exposure time, gain values) is mapped via calibration to parameters $(\alpha, \beta)$ and fed as a noise conditioning vector into networks supporting conditional input (such as FastDVDnet), replacing the need to estimate $\sigma$. This is the most reliable approach in engineering practice for mobile video ISP.

---

## §6 Evaluation

### 6.1 Standard Datasets

| Dataset | Scale | Resolution | Noise type | Primary use |
|---------|-------|-----------|------------|-------------|
| Set8 | 8 video sequences (~250 frames/sequence) | 240p–480p | AWGN (σ=10/20/30/40/50) | Video denoising academic benchmark, most widely cited |
| DAVIS 2017 | 90+ sequences, ~6700 frames total | 480p / 1080p | Synthetic AWGN or real noise | High-quality real scenes with dense motion annotations |
| REDS | 300 sequences × 100 frames | 720p | Real degradation (blur + noise) | Official NTIRE video SR/restoration dataset |
| Vimeo-90K | 91,701 7-frame short sequences | 448×256 | AWGN / real degradation | General-purpose training & testing benchmark for video SR/NR |
| DRV (Dynamic Raw Video) | 200+ scene-paired RAW sequences | 720p RAW | Real sensor noise | Dedicated dataset for RAW-domain video denoising |

**Dataset selection advice:** When comparing methods, report results on REDS4 (4 official test sequences) and the Vimeo-90K test set as a priority, enabling direct comparison with existing literature. Deployment-oriented evaluation should additionally validate generalization on DRV or self-collected real-noise video.

### 6.2 Key Evaluation Metrics

**PSNR / SSIM (averaged per frame):** Basic image quality metrics computed independently per frame then averaged over the sequence; they do not reflect inter-frame continuity:

$$\text{PSNR}_{\text{seq}} = \frac{1}{T} \sum_{t=1}^{T} 10 \log_{10}\!\frac{255^2}{\text{MSE}(x_t, \hat{x}_t)}$$

**tOF (temporal Optical Flow consistency):** Measures temporal consistency of the output video by computing the difference between the inter-frame optical flow field of the output sequence and that of the ground-truth sequence:

$$\text{tOF} = \frac{1}{T-1} \sum_{t=1}^{T-1} \|\mathbf{v}_t^{\hat{x}} - \mathbf{v}_t^{x}\|_1$$

A smaller tOF indicates better motion consistency in the output video and less susceptibility to flickering.

**Flicker Index (闪烁指数):** A more intuitive metric for inter-frame luminance consistency:

$$E_{\text{flicker}} = \frac{1}{T-1} \sum_{t=1}^{T-1} \left|\bar{Y}(\hat{x}_t) - \bar{Y}(\hat{x}_{t-1})\right|$$

where $\bar{Y}(\cdot)$ is the mean luminance of the frame (Y channel). In real product evaluation, the flicker index often correlates more closely with subjective user perception than PSNR and should be given particular attention.

**Temporal SSIM (T-SSIM):** SSIM computed on a 3D volume formed by 3 consecutive frames, simultaneously capturing spatial structure and temporal continuity; more comprehensive than per-frame SSIM.

### 6.3 Comparison of Major Methods

The data below are sourced from the original papers for each method and publicly available reproductions. Test conditions differ slightly across papers (REDS uses a ×4 super-resolution task; Vimeo-90K uses ×4 super-resolution; Set8 uses video denoising at σ=30).

| Method | Year | REDS4 PSNR (dB) | Vimeo-90K PSNR (dB) | Set8 PSNR (dB, σ=30) | Parameters | Inference speed (720p) |
|--------|------|-----------------|--------------------|-----------------------|-----------|------------------------|
| V-BM4D | 2012 | — | — | 36.05 | — | Very slow (minutes) |
| FastDVDnet | 2020 | — | — | 31.68 (color) | 2.5M | Fast (~100 fps) |
| EDVR | 2019 | 31.09 | 37.61 | — | 20.6M | Medium (~3 fps) |
| BasicVSR | 2021 | 31.42 | 37.18 | — | 6.3M | Medium (~10 fps) |
| BasicVSR++ | 2022 | 32.39 | 37.79 | — | 7.3M | Medium (~8 fps) |
| RVRT | 2022 | 34.81 | 40.33 | — | 10.8M | Slow (~1 fps) |

> **Note:** FastDVDnet and the EDVR/BasicVSR family address different primary tasks (the former is evaluated mainly on video denoising, the latter mainly on video super-resolution), so missing entries in certain columns are expected. Cross-method comparisons should be conducted on the same task.

---

## §7 Code

See the companion notebook *See §6 Code section for runnable examples.*, which covers:

1. **FastDVDnet 5-frame temporal denoising inference demo**
   - Load a pretrained model, read a video frame sequence, and run inference with a sliding window of 5 frames
   - Visualize the noisy input frame, denoised output frame, and per-frame PSNR curve
   - Support different input noise levels $\sigma$ to observe the network's response to noise

2. **EDVR PCD alignment visualization (DCN offset field heat map)**
   - Extract the deformable convolution offsets $\{\Delta p_k\}$ from each pyramid level of the EDVR PCD module
   - Visualize offset vectors as a quiver plot and compare with optical flow estimates
   - Analyze offset distributions separately in motion regions and static regions

3. **BasicVSR bidirectional propagation feature visualization**
   - Export PCA projections of the forward hidden state $h_t^{\text{fwd}}$ and backward hidden state $h_t^{\text{bwd}}$
   - Visualize the complementary information captured by the two propagation directions (forward captures historical context; backward captures future context)

4. **Set8 benchmark PSNR evaluation script**
   - Automatically download the Set8 dataset and synthesize Gaussian noise at different $\sigma$ levels
   - Batch-run FastDVDnet inference and output per-frame PSNR/SSIM and sequence averages
   - Save results as CSV for easy comparison with paper tables

5. **tOF temporal consistency computation**
   - Estimate inter-frame optical flow for the output sequence using RAFT
   - Compute tOF and flicker index $E_{\text{flicker}}$ and compare against GT video
   - Visualize optical flow residual heat maps to localize temporally inconsistent regions

---

## References

- Tassano, M., Delon, J., & Veit, T. (2020). **FastDVDnet: Towards real-time deep video denoising without flow estimation.** *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 2020.

- Wang, X., Chan, K. C. K., Yu, K., Dong, C., & Loy, C. C. (2019). **EDVR: Video restoration with enhanced deformable convolutional networks.** *CVPR Workshops (NTIRE)*, 2019.

- Chan, K. C. K., Wang, X., Yu, K., Dong, C., & Loy, C. C. (2021). **BasicVSR: The search for essential components in video super-resolution and beyond.** *CVPR*, 2021.

- Chan, K. C. K., Zhou, S., Xu, X., & Loy, C. C. (2022). **BasicVSR++: Improving video super-resolution with enhanced propagation and alignment.** *CVPR*, 2022.

- Liang, J., Fan, Y., Xiang, X., Ranjan, R., Ilg, E., Green, S., ... & Timofte, R. (2022). **Recurrent video restoration transformer with guided deformable attention.** *Advances in Neural Information Processing Systems (NeurIPS)*, 35. [RVRT]

- Yue, Z., Yong, H., Zhao, Q., Meng, D., & Zhang, L. (2020). **Supervised raw video denoising with a benchmark dataset on dynamic scenes.** *CVPR*, 2020. [RViDeNet]

- Maggioni, M., Katkovnik, V., Egiazarian, K., & Foi, A. (2012). **Video denoising, deblocking and enhancement through separable 4-D nonlocal spatiotemporal transforms.** *IEEE Transactions on Image Processing*, 21(9), 3952–3966. [V-BM4D]

- Dai, J., Qi, H., Xiong, Y., Li, Y., Zhang, G., Hu, H., & Wei, Y. (2017). **Deformable convolutional networks.** *ICCV*, 2017. [DCNv2 foundational work]

- Sun, D., Yang, X., Liu, M. Y., & Kautz, J. (2018). **PWC-Net: CNNs for optical flow using pyramid, warping, and cost volume.** *CVPR*, 2018.

- Zhou, H., Ou, J., Wei, P., Huang, W., Liu, J., Luo, W., & Li, H. (2024). **GLARE: Low-light image enhancement via generative latent feature based codebook retrieval.** *ECCV*, 2024. arXiv:2407.12431. [10]

- Li, K., Li, X., Wang, Y., He, Y., Wang, Y., Wang, L., & Qiao, Y. (2024). **VideoMamba: State space model for efficient video understanding.** *ECCV*, 2024. [11]

- Liu, Z., Ning, J., Cao, Y., Wei, Y., Zhang, Z., Lin, S., & Hu, H. (2022). **Video Swin Transformer.** *CVPR*, 2022. [12]

---

## §8 On-Device Deployment and Quantization

> **Latency budget for video denoising:** The latency budget for video denoising is extremely tight — 30 fps video requires ≤ 33 ms per frame; 60 fps requires ≤ 16 ms. This is fundamentally different from single-frame image restoration (which typically tolerates 100–200 ms). All on-device schemes below are predicated on meeting the 30 fps real-time constraint.

### 8.1 Qualcomm SNPE / QNN

- Quantization support: INT8/INT16; dynamic quantization typically incurs a 0.2–0.5 dB PSNR penalty.
- Recommended backend: DSP (HVX) first, GPU second.
- FastDVDnet and other purely convolutional architectures are HVX-friendly. EDVR's deformable convolution (DCNv2) requires confirming native support in SNPE 2.x (supported since SNPE 2.x).
- The multi-frame temporal buffer (typically 3–5 frames) must be maintained in NPU memory; evaluate the fit between DSP L2 cache size (~1–8 MB) and the frame buffer footprint.

### 8.2 MediaTek NeuroPilot / APU

- Supports ONNX/TFLite import; APU5 supports INT4/INT8 mixed precision.
- Use NeuroPilot SDK for offline compilation (`neuron_runtime`).
- BasicVSR's bidirectional propagation requires future frames (frame buffering); real-time applications should switch to a unidirectional propagation variant or limit the window size.

### 8.3 ARM NN / TFLite (Generic Mobile)

- ARM Mali GPU with TFLite delegate achieves 2–4× acceleration over CPU-only.
- Quantization tool: TFLite Converter post-training quantization (INT8).
- NNAPI backend on Android 11+ automatically selects the best available accelerator.
- Temporal state ($h_t$) in recurrent video denoising models must be maintained as an external tensor in TFLite (via the TFLite stateful RNN interface) to avoid per-frame state reconstruction overhead.

### 8.4 Mobile Video Denoising Latency Reference

| Method | Architecture | 720p@30fps feasibility | Key constraint |
|--------|-------------|----------------------|----------------|
| FastDVDnet (5-frame, INT8) | Pure CNN, no optical flow | Feasible (flagship NPU < 20 ms) | 5-frame buffer ~30 MB |
| BasicVSR (unidirectional, INT8) | Recurrent propagation + optical flow | Needs optimization (flow ~10 ms) | SpyNet must be quantized separately |
| EDVR (3-frame, INT8) | DCN alignment + TSA | Feasible on flagship; infeasible on mid-range | DCN operator latency is unstable |
| RViDeNet (RAW domain, INT8) | RAW 4-channel + DCN | Needs RAW-domain ISP embedding | Must integrate before demosaicing |

---

## §9 Glossary

**FastDVDnet**
The first deep learning video denoising method capable of real-time inference without optical flow estimation, proposed by Tassano et al. (CVPR 2020) [1]. It takes 5 consecutive frames centered on the current frame as input and processes them with a two-stage U-Net: Stage 1 denoises adjacent frame pairs (with shared weights); Stage 2 fuses the three Stage-1 outputs to produce the final result. The network achieves implicit inter-frame motion compensation through its large receptive field, with only ~2.5M parameters. Achieves 31.68 dB PSNR on Set8 (σ=30, color) at approximately 100 fps on an RTX 2080 Ti. **Non-blind denoiser** that requires the noise level $\sigma$ as input.

**EDVR (Enhanced Deformable Convolution for Video Restoration)**
Proposed by Wang et al. (CVPRW 2019, NTIRE 2019 winner) [2]. Contains two core modules: the **PCD alignment module** (multi-scale pyramid cascaded deformable convolution for large-motion scenes) and the **TSA fusion module** (temporal + spatial attention for adaptive multi-frame feature weighting). Approximately 20.6M parameters; REDS4 PSNR 31.09 dB. The representative work introducing deformable convolution into video restoration.

**Deformable Convolution (DCNv1 / DCNv2)**
DCNv1 introduced by Dai et al. (ICCV 2017) [8]: learnable position offsets $\Delta p_k$ are added to the standard convolution grid, enabling adaptive spatial sampling. DCNv2 (Zhu et al., CVPR 2019) extends this with a modulation scalar $m_k \in [0,1]$ per sampling point, allowing the network to automatically suppress occluded or invalid sampling locations: $y'(p) = \sum_k w_k \cdot m_k \cdot x(p + p_k + \Delta p_k)$. Versions used in EDVR and BasicVSR++ are DCNv2.

**BasicVSR / BasicVSR++**
Proposed by Chan et al. (CVPR 2021/2022) [3][4]. **BasicVSR** [3] adopts **bidirectional propagation** (forward + backward hidden state recurrence) with SpyNet optical flow alignment; 6.3M parameters; REDS4 PSNR 31.42 dB. **BasicVSR++** [4] introduces **second-order propagation** (aggregating history across two frames) and replaces optical flow with deformable convolution; 7.3M parameters; REDS4 PSNR 32.39 dB. Bidirectional propagation formula: $h_t^{\text{fwd}} = \mathcal{G}(x_t, \text{warp}(h_{t-1}^{\text{fwd}}, \mathbf{v}_{t\to t-1}))$.

**RVRT (Recurrent Video Restoration Transformer)**
Proposed by Liang et al. (NeurIPS 2022) [5]. Introduces Transformers into video restoration via locally-shifted window attention (borrowing from SwinIR) and **Guided Deformable Attention** (propagated hidden state predicts attention offsets, enabling dynamic cross-frame sampling). Vimeo-90K super-resolution PSNR 40.33 dB [5]. Inference speed ~1 fps at 720p [5] — useful as an offline quality ceiling or for distilling lightweight models, not for real-time deployment.

**V-BM4D**
Proposed by Maggioni et al. (TIP 2012) [7]. Extends BM3D to the spatiotemporal fourth dimension: similar blocks are searched spatially while motion-compensated similar blocks are searched across adjacent frames in the temporal domain, forming a 4D array for collaborative sparse-transform filtering (Wiener filtering). Achieves ~36.05 dB PSNR on Set8 (σ=30) [7] (grayscale; not directly comparable to color results). The top traditional baseline; computationally too expensive for real-time use.

**PCD Alignment (Pyramid Cascading Deformable Alignment)**
EDVR's multi-scale alignment strategy for large-motion scenes: three-level feature pyramids are extracted from reference and neighboring frames; deformable convolution offsets are predicted starting from the coarsest scale ($l=3$) and progressively refined upward, with each level predicting only residual offsets (cascade design reduces per-level burden). The pyramid structure enables PCD to handle motion exceeding a single-level receptive field.

**RAW-Domain Video Denoising**
Performing temporal denoising directly on RAW sensor data before demosaicing. Advantages: noise obeys the Poisson-Gaussian physical model ($\sigma^2(I) = \alpha I + \beta^2$), enabling accurate modeling; prevents demosaicing from spreading noise across color channels. Representative work: RViDeNet (Yue et al., CVPR 2020) [6], which also introduces the first RAW video denoising dataset (DRV). Key challenge: the Bayer pattern's non-uniformity requires packing the Bayer image into 4 channels (RGGB) before standard convolution can be applied.

**tOF (Temporal Optical Flow Consistency)**
A metric for measuring the temporal consistency of a restored video sequence: $\text{tOF} = \frac{1}{T-1}\sum_{t=1}^{T-1}\|\mathbf{v}_t^{\hat{x}} - \mathbf{v}_t^{x}\|_1$. Compares the inter-frame optical flow of the output sequence against that of the ground-truth sequence. Smaller tOF indicates better motion consistency and lower susceptibility to flickering. Complementary to per-frame PSNR/SSIM for capturing temporal quality.

