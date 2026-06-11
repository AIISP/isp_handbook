# Part 3, Chapter 10: Deep Learning-Based Video ISP

> **Positioning:** This chapter uses the video ISP system as its central thread, covering the complete technical chain of deformable convolution alignment, temporal consistency (时序一致性) modeling, end-to-end differentiable video ISP, and video super-resolution/enhancement. The focus is on deep-learning-driven transformation of industry-grade video processing pipelines.
> **Prerequisites:** Part 2, Chapter 12 (Traditional Temporal NR), Part 3, Chapter 02 (End-to-End Restoration), Part 3, Chapter 06 (AI Tone Mapping), Part 3, Chapter 08 (Video Denoising)
> **Target Readers:** Video ISP algorithm engineers, system architects

---

## §1 Theory

### 1.1 System-Level Challenges of Video ISP

Single-frame ISP and video ISP differ fundamentally in their processing objectives. A single-frame ISP only needs to produce the best possible quality for the current frame in isolation, whereas a video ISP must simultaneously guarantee per-frame quality and inter-frame consistency. The table below summarizes the core differences:

| Dimension | Single-Frame ISP | Video ISP | Additional Challenge |
|-----------|-----------------|-----------|---------------------|
| Processing unit | Single RAW image | Continuous frame sequence | Must maintain inter-frame state |
| Temporal consistency | Not applicable | Luminance/color/noise must be smooth | Frame-to-frame jumps produce flickering |
| Scene transitions | Not applicable | Cut/fade transitions must be detected | Transition frames must not be fused across shots |
| Real-time constraint | Offline often acceptable | Strict latency at 30/60/120 fps | Latency budget measured in milliseconds |
| Memory bandwidth | Single-frame buffer | Multi-frame buffer (4–7 frames) | DRAM bandwidth pressure multiplied several times over |
| Motion handling | Not required | Motion estimation and compensation are essential | Fast motion and occlusion require robust handling |
| Parameter stability | Per-frame independent optimization | AE/AWB parameters need inter-frame smoothing | Sudden parameter changes cause image jitter |

The central tension in video ISP is the **quality-versus-consistency trade-off**. Exploiting multi-frame information tends to improve per-frame denoising quality; yet the motion-alignment errors introduced by multi-frame fusion can produce ghosting (鬼影) or blurring in moving regions. In an end-to-end deep learning framework, this tension can be systematically relieved by jointly optimizing a per-frame reconstruction loss and an inter-frame consistency loss.

**Real-time performance tiers** form the fundamental engineering constraint of video ISP design:

- **30 fps (33 ms/frame):** Mainstream mobile video capture; the full ISP pipeline must complete on an NPU/DSP.
- **60 fps (16 ms/frame):** High-frame-rate video; strict model complexity requirements.
- **120 fps (8 ms/frame):** Professional Pro video mode; typically only feasible on dedicated on-chip hardware accelerators.
- **Offline post-processing:** No real-time constraint; larger models and bidirectional temporal fusion are viable.

### 1.2 Deformable Convolution (可变形卷积) Principles

Deformable Convolutional Networks (DCN) are the core operator in video alignment tasks. The design motivation stems from the fact that standard convolutions have a fixed receptive field shape and cannot adaptively capture motion targets of varying geometry.

**Standard convolution** at position $p$ produces:

$$y(p) = \sum_{k=1}^{K} w_k \cdot x(p + p_k)$$

where $p_k$ are the predefined regular sampling offsets (e.g., the nine fixed positions $\{(-1,-1), (-1,0), \ldots, (1,1)\}$ of a $3\times3$ kernel), $w_k$ are the corresponding weights, and $K=9$.

**DCNv1** (Dai et al., ICCV 2017) introduces a learnable offset $\Delta p_k$ at each sampling location:

$$y(p) = \sum_{k=1}^{K} w_k \cdot x(p + p_k + \Delta p_k)$$

The offset $\Delta p_k$ is predicted from the feature map by a dedicated convolutional branch. Because it takes real-valued coordinates, bilinear interpolation is used to sample $x$ at sub-pixel positions. This allows the effective receptive field of the convolution kernel to deform adaptively according to the input content.

**DCNv2** (Zhu et al., CVPR 2019) additionally introduces a modulation weight $m_k \in [0,1]$, enabling the network to suppress the contribution of noisy or unreliable sampling points:

$$y(p) = \sum_{k=1}^{K} w_k \cdot m_k \cdot x(p + p_k + \Delta p_k)$$

$m_k$ is predicted by a separate branch and constrained to $[0,1]$ via a Sigmoid activation. DCNv2 effectively learns both "where to sample" ($\Delta p_k$) and "how much to trust each sample" ($m_k$), giving it substantially greater expressive power than DCNv1.

**Application mechanism in video alignment:** The difference between reference-frame features and current-frame features is fed as input to the DCN offset prediction network, which implicitly learns the spatial transformation that warps the reference-frame features into the coordinate system of the current frame. Compared with explicit optical flow estimation, DCN-based alignment has the following advantages:

- End-to-end trainable; alignment errors are back-propagated directly through the reconstruction loss.
- Reasonably robust to occlusion and large displacement ($m_k$ can suppress contributions from occluded regions).
- No separate optical flow network is required, reducing inference overhead.

### 1.3 Methods for Modeling Temporal Consistency

Temporal consistency is the most distinctive requirement that separates video ISP from image ISP. Modeling approaches fall into three broad categories:

**(1) Optical Flow Constraint Loss**

During training, a pre-computed or jointly predicted optical flow $F_{t \to t-1}$ is used to warp the output frame, which is then compared with the previous output frame:

$$\mathcal{L}_{\text{temp}} = \|O_t - \mathcal{W}(O_{t-1}, F_{t \to t-1})\|_1 \cdot M_t$$

Here $\mathcal{W}(\cdot, F)$ denotes backward warping (bilinear sampling) guided by flow $F$, and $M_t$ is the occlusion mask (derived from flow forward-backward consistency checking; occluded pixels are set to 0 to avoid penalizing legitimate content changes). This loss directly penalizes motion-inconsistent changes in the output sequence and effectively suppresses flickering.

**(2) Feature-Domain Temporal Fusion**

Temporal fusion in feature space is more robust than fusion in pixel space, because features are less sensitive to illumination and texture variation than raw pixels, and deep features already carry implicit semantic information that helps distinguish genuine motion from noise fluctuations. The typical approach is to align neighboring-frame features and then fuse them via an attention mechanism:

$$F_{\text{fused}} = \sum_{t \in \mathcal{N}} A_t \cdot F_t^{\text{aligned}}$$

where $A_t$ are the temporal attention weights and $F_t^{\text{aligned}}$ are the aligned reference-frame features.

**(3) Causal and Non-Causal Architecture Design**

Depending on latency constraints, temporal modeling architectures fall into two categories:

- **Causal:** Uses only the current frame and past frames. Suitable for live streaming and low-latency recording. The drawback is limited ability to handle occlusions that only become visible in future frames.
- **Non-causal:** Uses both past and future frames. Suitable for offline post-processing. It trades additional latency (typically 3–5 frames) for richer temporal context, significantly improving quality in complex motion scenarios.

---

## §2 Main Methods

### 2.1 TDAN — Deformable Alignment for Video SR (Tian et al., CVPR 2020)

TDAN (Temporally-Deformable Alignment Network) is an early representative work introducing deformable convolutions into video super-resolution alignment. The core idea is to anchor on the current (low-resolution) frame, predict DCN offsets for each reference frame, and perform feature-level alignment; the aligned multi-frame features are then sent into a reconstruction network for super-resolution.

**Network architecture:**
1. **Feature extraction:** Shared-weight convolutional networks extract features $F_t, F_{t+i}$ from the current frame and each reference frame independently.
2. **Offset prediction:** $F_t$ and $F_{t+i}$ are concatenated and passed through a convolutional layer to predict DCNv1 offsets $\Delta p_{t+i}$.
3. **Deformable alignment:** The predicted offsets are applied via deformable convolution to the reference-frame features $F_{t+i}$, yielding aligned features $\tilde{F}_{t+i}$.
4. **Fusion and reconstruction:** All aligned features are concatenated and passed through a reconstruction network to produce the high-resolution output.

TDAN's main limitation is that single-scale offset prediction has limited capacity for large-displacement motion, and DCNv1's lack of modulation weights makes it insufficiently robust to occlusions. These issues are systematically addressed in the subsequent EDVR.

### 2.2 EDVR's TSA Fusion in Detail (Wang et al., CVPRW 2019)

EDVR (Enhanced Deformable Video Restoration) is a landmark work in video restoration. It introduces the PCD alignment module and the TSA fusion module, achieving state-of-the-art performance on benchmarks such as REDS.

**PCD Alignment (Pyramid, Cascading and Deformable Alignment)**

PCD uses a three-level feature pyramid, predicting and cascading offsets progressively from coarse to fine:

- **Level 3 (coarsest):** Predicts an initial offset $\Delta p^{(3)}$ at 1/4 resolution features.
- **Level 2:** Up-samples $\Delta p^{(3)}$ by $\times 2$ as a prior, predicts a residual offset at 1/2 resolution, and adds it to obtain $\Delta p^{(2)}$.
- **Level 1 (finest):** Uses $\Delta p^{(2)}$ as a prior, predicts the final offset $\Delta p^{(1)}$ at full resolution, and performs the final alignment with DCNv2.

The benefit of cascaded offsets is that the coarse scale handles large displacement while the fine scale compensates for sub-pixel accuracy, combining robustness to large motion with precise alignment.

**TSA Fusion (Temporal and Spatial Attention Fusion)**

Rather than naively averaging aligned multi-frame features, TSA fuses them via joint temporal and spatial attention weighting:

$$F_{\text{fused}} = \sum_{t \in \mathcal{T}} A_t \cdot F_t^{\text{aligned}}$$

**Temporal attention** (frame-level weights): The similarity between each aligned reference-frame feature and the current-frame feature is computed and normalized via softmax to obtain a global contribution weight for each frame:

$$A_t = \text{softmax}\bigl(\text{similarity}(F_t^{\text{aligned}},\ F_{\text{ref}})\bigr)$$

Similarity is obtained by per-pixel dot product followed by global pooling.

**Spatial attention** (pixel-level weights): After temporal weighted fusion, the feature map is further independently weighted at each spatial position to enhance contributions from texture-rich regions and suppress influence from regions with large alignment errors (e.g., motion boundaries).

TSA fusion allows the network to adaptively down-weight frames (or pixels) where alignment is poor, and is the key design that enables EDVR to maintain high quality in complex motion scenarios.

### 2.3 End-to-End Differentiable Video ISP

Designing the full ISP pipeline as differentiable modules and jointly optimizing them end-to-end over video frame sequences is the core direction for deep-learning-driven video ISP.

**CycleISP for Video** (Zamir et al., 2020) extends the cycle-consistency idea to video denoising: the network learns mappings in both RAW→sRGB and sRGB→RAW directions; the cycle-consistency constraint makes synthetic noise more closely resemble the real camera noise distribution, thereby improving denoising performance in real-world scenes. The video version additionally introduces an inter-frame consistency constraint to ensure temporal smoothness of the output frame sequence.

**Differentiable video ISP pipeline:** Traditional ISP modules including BLC, Demosaic, AWB, CCM, and TMO are all replaced with differentiable operators:

- **BLC/LSC:** Simple linear operations; inherently differentiable.
- **Demosaic:** Can be replaced with a learnable convolution (see Part 3, Chapter 02), or an approximately differentiable bilinear interpolation.
- **AWB/CCM:** Matrix multiplication; fully differentiable; parameters provided by a dedicated prediction network.
- **TMO:** Replaced by a differentiable curve network (e.g., STAR from Part 3, Chapter 06) instead of hand-crafted curves.

The joint loss function balances per-frame reconstruction quality and inter-frame consistency:

$$\mathcal{L} = \mathcal{L}_{\text{frame}} + \lambda_{\text{temp}} \cdot \mathcal{L}_{\text{temporal}}$$

where $\mathcal{L}_{\text{frame}}$ is typically a combination of perceptual loss and L1 loss, and $\mathcal{L}_{\text{temporal}}$ is the optical flow warp error.

**Joint video 3A optimization:** AE (Auto Exposure) and AWB (Auto White Balance) parameters are jointly predicted under inter-frame smoothness constraints, preventing parameter jumps that would cause image jitter:

$$\mathcal{L}_{3A} = \sum_t \mathcal{L}_{\text{quality}}(\hat{I}_t, I_t^*) + \mu \sum_t \|\theta_t - \theta_{t-1}\|_2^2$$

The second term penalizes abrupt changes in 3A parameters $\theta_t$ (gains, color temperature, etc.) between adjacent frames.

### 2.4 Video Low-Light Enhancement (VideoLLIE)

Low-light video enhancement is particularly important in dark-scene capture. The core challenge is that frame-independent enhancement leads to inter-frame luminance and color inconsistency, producing visible flickering.

**Zero-DCE for Video:** Extends single-frame Zero-DCE's local curve estimation to the video domain by adding a temporal consistency regularization term across frames. The network independently predicts enhancement curve parameters $A_t$ (pixel-wise affine transformation coefficients) for each frame, while constraining the difference between adjacent-frame parameters:

$$\mathcal{L}_{\text{consistency}} = \|A_t - \mathcal{W}(A_{t-1}, F_{t \to t-1})\|_1$$

**Temporal Zero-DCE:** Further incorporates recurrent connections into the $A_t$ prediction network, enabling the current frame's curve parameters to be conditioned on the gain state of historical frames, thereby achieving adaptive inter-frame luminance smoothing. During drastic exposure changes (e.g., moving from indoors to outdoors), the transition is smooth rather than abrupt.

**Recurrent LLIE:** Uses an RNN hidden state $h_t$ to carry historical luminance statistics; the network conditions each frame's prediction on $h_t$ to achieve adaptive gain control:

$$\hat{I}_t, h_{t+1} = f_\theta(I_t^{\text{low}}, h_t)$$

The hidden state $h_t$ encodes the luminance distribution of the preceding frames, enabling the network to distinguish "genuinely dark scenes" from "transiently dark frames caused by motion blur," reducing unnecessary over-amplification.

### 2.5 Video HDR Merging and Tone Mapping

Video HDR processing poses more complex challenges than image HDR: in addition to guaranteeing per-frame HDR fusion quality, smooth inter-frame transitions in luminance and color must also be ensured.

**Video HDR processing pipeline:**

1. **Multi-frame exposure alignment:** Motion-robust alignment (optical flow or DCN) of short- and long-exposure frames to produce an aligned exposure stack.
2. **Ghost-free HDR merging:** Detect motion regions using saturation masks and optical flow consistency checking; fall back to single-exposure frames in motion regions to avoid ghosting artifacts.
3. **Temporal TMO:** Apply a temporally aware tone mapping operator to the merged HDR frame sequence to ensure inter-frame luminance smoothness.

**Motion ghosting** is the critical difficulty in video HDR. The ghost-free HDR merge strategy is:

- Compute optical flow consistency error between the reference exposure frame and the aligned frame; label regions with large error as "motion regions."
- In motion regions, use only the single exposure that best matches the scene's brightness level, avoiding multi-frame fusion artifacts.
- In static regions, perform normal multi-frame HDR merging to maximize the captured dynamic range.

**Temporal TMO (STAR method, Zhang et al., ECCV 2020):** A spatially and temporally adaptive real-time HDR video tone mapping operator. Through an attention mechanism along the temporal dimension, STAR perceives the luminance distribution of historical frames and achieves smooth, content-adaptive tone compression. Detailed principles are covered in Part 3, Chapter 06. This chapter focuses on its integration interface with the video ISP pipeline: STAR takes aligned HDR frames as input and outputs video frames in the SDR/HLG color space, which can be fed directly to an encoder.

---

## §3 Pipeline Engineering

### 3.1 Typical Video ISP Architecture

A complete industry-grade video ISP pipeline is typically organized in the following module order:

```
RAW Video Input
    │
    ▼
[BLC + LSC]            ← Black-level correction, lens shading correction (per-frame, no temporal state)
    │
    ▼
[Spatial Denoising (optional)]  ← Spatial filtering on RAW before Demosaic to reduce chroma noise
    │
    ▼
[Demosaic]             ← Mosaic reconstruction; learnable Demosaic recommended (see Part 3, Chapter 02)
    │
    ▼
[AWB]                  ← White balance gain (inter-frame exponential smoothing: g_t = α·g_t + (1-α)·g_{t-1})
    │
    ▼
[CCM]                  ← Color correction matrix (can be adaptively interpolated with color temperature)
    │
    ▼
[Temporal NR (core)]   ← Multi-frame alignment and fusion denoising (DCN/flow alignment + temporal attention fusion)
    │
    ▼
[TMO / Tone Curve]     ← Temporally aware tone mapping (STAR or differentiable curve network)
    │
    ▼
[Sharpening / Detail Enhancement]  ← Frequency-separation sharpening; temporal smoothing needed to avoid sharpening-strength jumps
    │
    ▼
Encoder (H.265/H.266)
```

Key deep-learning intervention points: Demosaic (learnable), Temporal NR (DCN alignment + attention fusion), TMO (neural curve network), and the end-to-end joint optimization interface.

### 3.2 Scene Transition Detection

Scene transition detection is the "safety net" for video ISP temporal processing: the temporal NR state must be reset at transition frames; otherwise, frames from the preceding scene will contaminate the new scene, producing ghosting.

**Cut detection** (hard scene transition):

A histogram-difference-based method is simple and effective:

$$d_t = \|H_t - H_{t-1}\|_1 > \tau_{\text{cut}}$$

where $H_t$ is the normalized histogram of the current frame (typically computed on the luminance channel), and $\|\cdot\|_1$ is the L1 distance. $\tau_{\text{cut}}$ typically falls in the range 0.3–0.5 (after normalization).

Handling strategy upon detecting a cut frame:
- **Temporal NR:** Clear the frame buffer; degrade to single-frame denoising for the current frame.
- **AE integrator:** Reset the auto-exposure integration state to prevent the previous scene's exposure target from influencing the new scene.
- **AWB gain:** Reset the history state of the smoothing filter.

**Fade detection** (gradual scene transition):

A fade manifests as a continuous monotonic change in global luminance (fade-out: luminance gradually decreases; fade-in: luminance gradually increases). Detection method:

$$\text{fade}_t = \mathbf{1}\left[\left|\bar{L}_t - \bar{L}_{t-1}\right| < \epsilon\right] \cap \left[\sum_{\tau=t-T}^{t} (\bar{L}_\tau - \bar{L}_{\tau-1}) > \tau_{\text{fade}}\right]$$

That is: the per-frame luminance change is small (ruling out rapid exposure adjustments) yet the cumulative change within the window is large. Upon detecting a fade, the temporal NR should reduce its fusion weights, and the AE integrator should track the luminance change in tandem.

**Deep learning-based transition detection:** In recent years, small-CNN approaches have emerged that take the inter-frame feature difference map as input and output a transition probability. The advantage is more content-aware accuracy; the drawback is additional computational overhead.

### 3.3 Latency and Buffer Management

The latency of a video ISP pipeline arises primarily from the multi-frame buffer dependency of the temporal NR module. Different use cases impose different requirements on latency and buffer frame count:

| Processing Mode | Latency (frames) | Buffer Frames | Memory Cost (4K 10-bit) | Applicable Scenario |
|----------------|-----------------|--------------|------------------------|---------------------|
| Single-frame real-time | 0 | 0 | ~25 MB (one frame) | Live streaming, video conferencing |
| Causal 5-frame | 4 | 4 (past) | ~125 MB | Ordinary video recording |
| Bidirectional 7-frame | 3 | 3 (past) + 3 (future) | ~175 MB | Flagship mobile standard mode |
| Sliding window N-frame | N/2 | N | ~25N MB | High-quality offline post-processing |
| Full offline | Unlimited | Entire video | Full-clip storage | Cinema / post-production |

**DRAM bandwidth estimation:** For 4K (3840×2160) 10-bit RAW at 30 fps, one frame occupies approximately 25 MB. The peak read/write bandwidth for a 5-frame buffer is approximately $25\text{ MB} \times 5 \times 2 \times 30 \approx 7.5\text{ GB/s}$, which is a significant pressure on mobile DRAM. This typically requires compressed storage (e.g., AFBC format) or buffering features (rather than raw pixels) in on-chip SRAM.

---

## §4 Tuning

### 4.1 Temporal Consistency Weight Tuning

The temporal consistency loss weight $\lambda_{\text{temp}}$ directly determines the model's operating point on the trade-off between per-frame quality and inter-frame smoothness.

**Tuning guidelines:**

| $\lambda_{\text{temp}}$ Value | Typical Behavior | Applicable Scenario |
|------------------------------|-----------------|---------------------|
| 0 (disabled) | Visible inter-frame flickering; noise jumps in fast-motion regions | Baseline single-frame model only |
| 0.05–0.1 | Light constraint; fast-motion scenes largely flicker-free | Action video, sports broadcasting |
| 0.1–0.3 | Standard setting; optimal balance for everyday video | Main mobile video profile |
| 0.5–1.0 | Strong constraint; extremely smooth but fast motion may be blurred | Slow-motion, interview programs |

**Tuning procedure:**
1. Build a test video set covering different motion speeds (slow / fast / extreme).
2. Compute $E_{\text{flicker}}$ and PSNR curves for each value of $\lambda_{\text{temp}}$.
3. Subject to $E_{\text{flicker}}$ meeting the product specification (typically mean difference $< 0.5$ DN), select the $\lambda_{\text{temp}}$ that maximizes PSNR.
4. Separately validate on fast-motion video to confirm no motion blur is introduced.

**Adaptive $\lambda_{\text{temp}}$:** An advanced approach makes $\lambda_{\text{temp}}$ adapt to the scene's motion level. In regions with large optical flow magnitude (fast motion), reduce $\lambda_{\text{temp}}$ to avoid the temporal constraint impeding natural motion changes; in static regions, increase $\lambda_{\text{temp}}$ to reinforce consistency.

### 4.2 DCN Offset Range Clamping

Without constraints, the offsets $\Delta p_k$ predicted by deformable convolution can diverge to extreme values when training is insufficient, causing sampling positions to fall outside the image boundary or producing severe misalignment.

**Observed failure modes:**
- Excessively large offsets ($|\Delta p_k| > 32$ pixels): Reference frames are incorrectly aligned to completely irrelevant regions, introducing motion blur and ghosting.
- Oscillating offsets: Predicted offsets for adjacent frames point in opposite directions, causing "jitter" artifacts in the output.
- Out-of-boundary sampling: Bilinear interpolation pads with zeros outside the image boundary, causing black stripes near edges.

**Clamping strategies:**

1. **Hard clamping:** Apply a `tanh` activation after the DCN offset output and multiply by a maximum offset $\delta_{\max}$:
   $$\Delta p_k^{\text{clipped}} = \delta_{\max} \cdot \tanh(\Delta p_k^{\text{raw}})$$
   Typically $\delta_{\max} = 16$ pixels for 1080p (approximately 1.5% of image width).

2. **Offset regularization loss:** Add an offset magnitude penalty to the training loss:
   $$\mathcal{L}_{\text{offset}} = \gamma \sum_{k} \|\Delta p_k\|_2^2$$
   This encourages the network to use large offsets only when necessary.

3. **Per-level pyramid clamping:** Coarse levels permit a larger range ($\pm 32$) while fine levels permit a smaller range ($\pm 4$), so that large displacement is handled at the coarse scale and the fine scale performs only precise fine-tuning.

### 4.3 Scene Transition Threshold

The scene transition detection threshold $\tau_{\text{cut}}$ is the operating point balancing precision and recall.

**Comparison of error type consequences:**

| Error Type | Trigger Condition | Perceptual Consequence | Severity |
|-----------|------------------|----------------------|---------|
| False Positive | Normal motion mis-classified as a transition | Temporal NR is reset; denoising quality briefly degrades | Minor |
| False Negative | Genuine transition not detected | Previous scene frames linger; visible ghosting artifacts | Severe |

Since false negatives are far more costly than false positives, in practice $\tau_{\text{cut}}$ is set conservatively low (prefer false positives over false negatives).

**Tuning procedure:**
1. Build a test video set with annotated ground-truth transition points, covering hard cuts, soft cuts, fade-outs, and fade-ins.
2. Sweep $\tau_{\text{cut}} \in [0.1, 0.6]$ and compute the ROC curve (TPR vs. FPR) for each value.
3. Select the operating point according to product tolerance: typically require TPR > 95% (miss rate < 5%), minimizing FPR under this constraint.
4. Set separate thresholds or train an adaptive detector for different content types (fast-motion sports, slow-paced documentaries, animation).

---

## §5 Evaluation

### 5.1 Temporal Consistency Metrics

Beyond traditional per-frame quality metrics (PSNR, SSIM), video ISP requires dedicated temporal consistency evaluation metrics:

**(1) $E_{\text{flicker}}$: Inter-Frame Luminance Difference**

$$E_{\text{flicker}} = \frac{1}{T-1} \sum_{t=1}^{T-1} \left|\bar{L}(O_t) - \bar{L}(O_{t-1})\right|$$

where $\bar{L}(O_t)$ is the mean luminance of the $t$-th output frame (typically computed on the Y channel). Smaller $E_{\text{flicker}}$ indicates more stable inter-frame luminance. This metric is simple and intuitive, but it does not distinguish "luminance changes genuinely caused by scene brightness variation" from "flickering introduced by the algorithm." An improved version first aligns frames with optical flow before computing the difference.

**(2) tOF (Temporal Optical Flow Consistency)**

Measures the consistency between the estimated optical flow of the output frames and a reference motion field (derived from a high-accuracy optical flow algorithm or ground-truth motion information):

$$\text{tOF} = \frac{1}{T-1} \sum_{t} \|F(O_t, O_{t-1}) - F_{\text{gt},t}\|_2$$

A low tOF indicates that the motion structure in the output frames is consistent with the real scene.

**(3) Warping Error $E_{\text{warp}}$**

$$E_{\text{warp}} = \frac{1}{T-1} \sum_{t} \left\|O_t - \mathcal{W}(O_{t-1}, F_{\text{gt},t})\right\|_1 \cdot M_t$$

$M_t$ is the non-occlusion mask (difference is computed only in non-occluded regions). $E_{\text{warp}}$ directly quantifies the consistency of the output frames along motion trajectories, making it the most direct metric for assessing flickering in temporal NR and video enhancement algorithms.

### 5.2 Video Quality Benchmarks

| Dataset | Task Type | Resolution | Primary Metrics | Characteristics |
|---------|-----------|-----------|----------------|----------------|
| REDS | Video SR / Deblurring | 720p | PSNR / SSIM | High frame rate, multiple degradation types |
| Vimeo-90K | Video SR / Temporal NR | 448×256 | PSNR / SSIM | Large scale, standard benchmark |
| DAVIS 2017 | Video NR / Restoration | 1080p | PSNR + tOF | Contains real motion annotations |
| HDRTV | Video HDR Tone Mapping | 4K | TMQI + $E_{\text{flicker}}$ | Real HDR video content |
| SMOID | Low-Light Video Enhancement | 1080p | PSNR + $E_{\text{flicker}}$ | Paired real low-light / normal-light video |
| CameraMotion | Handheld Mobile Video ISP | Multiple resolutions | PSNR + User MOS | Simulates real mobile capture conditions |

In real product evaluation, **subjective evaluation (MOS, Mean Opinion Score)** carries equal weight to objective metrics — particularly for artifacts such as flickering, ghosting, and color jumps, where the correlation between subjective perception and objective metrics is not always consistent.

### 5.3 Real-Time Requirements

| Resolution | Frame Rate Target | Total Latency Budget | ISP Compute Budget | Notes |
|-----------|------------------|---------------------|--------------------|-------|
| 1080p | 30 fps | 33 ms | 15–20 ms | Mainstream mobile video |
| 1080p | 60 fps | 16 ms | 8–10 ms | High-frame-rate recording |
| 4K | 30 fps | 33 ms | 20–25 ms | Flagship mobile standard |
| 4K | 60 fps | 16 ms | 10–12 ms | High-frame-rate 4K |
| 4K | 120 fps | 8 ms | 4–5 ms | Pro high-frame-rate mode |

Compute budget allocation principle: ISP computation typically accounts for 60–70% of the total per-frame processing latency (the remainder goes to sensor readout and the encoder). Deep learning models must be quantized (INT8/INT4) on the target NPU/ISP hardware to meet the above budgets.

---

## §6 Code

Refer to the companion notebook *See §6 Code section for runnable examples.*, which covers the following modules, each with complete runnable code:

**Module 1: DCNv2 Offset Field Visualization**
- Run forward inference on a two-frame video sequence containing a moving target to obtain the per-sampling-point offsets $(\Delta x_k, \Delta y_k)$.
- Display the offset field as a quiver (arrow) heatmap: static-background offsets approach zero, while moving-target offsets align in direction and magnitude with the motion velocity.
- Simultaneously visualize the spatial distribution of modulation weights $m_k$, illustrating how weights are suppressed in occluded regions.

**Module 2: TSA Temporal Attention Weight Visualization**
- Extract the attention weight map $A_t$ for each reference frame from the TSA fusion module of an EDVR model.
- Show that in motion regions the current-frame weight is highest, while in static regions the weights across frames are relatively uniform.
- Compare reconstruction results with and without TSA, and quantify TSA's effect on suppressing ghosting in motion regions.

**Module 3: Temporal Consistency Loss Implementation**
```python
def temporal_consistency_loss(O_t, O_prev, flow_t, occ_mask):
    """
    O_t:      current frame output [B, C, H, W]
    O_prev:   previous frame output [B, C, H, W]
    flow_t:   optical flow F_{t->t-1} [B, 2, H, W]
    occ_mask: non-occlusion mask [B, 1, H, W], 0 in occluded regions
    """
    O_prev_warped = bilinear_warp(O_prev, flow_t)  # backward warp
    diff = torch.abs(O_t - O_prev_warped) * occ_mask
    return diff.mean()
```
- Includes complete implementations of `bilinear_warp` and occlusion mask generation.
- Compares training curves with and without this loss, showing the change in $E_{\text{flicker}}$.

**Module 4: $E_{\text{flicker}}$ Computation and Comparison**
- Run inference on a test video with both "frame-independent processing" and "temporal modeling processing."
- Compute per-frame $E_{\text{flicker}}$ and plot it as a time series, directly showing the degree of improvement in temporal consistency.
- Annotate scene transition frames to verify the effectiveness of the transition detection module.

**Module 5: Scene Transition Detection Visualization**
- Compute per-frame histogram differences $d_t$ over a test video sequence.
- Plot the $d_t$ time series and annotate the $\tau_{\text{cut}}$ threshold line.
- Display detection results (true positives / false positives) for different values of $\tau_{\text{cut}}$, supporting threshold selection.

---

## References

- Dai, J., et al. (2017). **Deformable convolutional networks.** ICCV 2017. [DCNv1 original paper, proposes learnable sampling offsets]
- Zhu, X., et al. (2019). **Deformable ConvNets v2: More deformable, better results.** CVPR 2019. [DCNv2, introduces modulation weights]
- Tian, Y., et al. (2020). **TDAN: Temporally-deformable alignment network for video super-resolution.** CVPR 2020. [First systematic application of DCN alignment in video SR]
- Wang, X., et al. (2019). **EDVR: Video restoration with enhanced deformable convolutional networks.** CVPRW 2019. [PCD + TSA, landmark work in video restoration]
- Zhang, Y., et al. (2020). **STAR: Spatially and temporally adaptive real-time HDR video tone mapping.** ECCV 2020. [Temporally adaptive HDR tone mapping]
- Zamir, S. W., et al. (2020). **CycleISP: Real image restoration via improved data synthesis.** CVPR 2020. [Cycle-consistent video ISP]
- Li, C., et al. (2021). **NTIRE 2021 challenge on video super-resolution.** CVPRW 2021. [Video SR challenge survey covering comparison of mainstream methods]
- Chen, C., et al. (2019). **Seeing motion in the dark.** ICCV 2019. [Pioneering work on video low-light enhancement]
- Eilertsen, G., et al. (2017). **HDR image reconstruction from a single exposure using deep CNNs.** ACM TOG 2017. [Single-frame HDR reconstruction, foundational reference for video HDR]
