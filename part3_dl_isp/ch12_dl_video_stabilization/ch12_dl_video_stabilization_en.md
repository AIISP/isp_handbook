# Part 3, Chapter 12: Deep Learning Video Stabilization and Temporal Alignment

> **Scope:** This chapter covers deep learning-based video stabilization (视频防抖) algorithms, from optical flow estimation to temporal trajectory smoothing. For hardware Electronic Image Stabilization (EIS) implementation, see Volume 2, Chapter 23.
> **Prerequisites:** Volume 2, Chapter 23 (EIS/OIS), Volume 3, Chapter 8 (DL Video Denoising)
> **Target Readers:** Algorithm engineers

---

## §1 Theoretical Principles

### 1.1 Sources and Classification of Video Shake

Shake/jitter (抖动) in video capture originates from multiple levels:

- **High-frequency hand tremor (高频手抖):** Frequency 5–20 Hz, small amplitude (< 2°), caused by muscle trembling; effectively suppressed by both OIS (Optical Image Stabilization, 光学防抖) and gyroscope-based EIS (Electronic Image Stabilization, 电子防抖)
- **Low-frequency gait-induced shake (低频走路抖动):** Frequency 1–3 Hz, larger amplitude, typical when shooting while walking; limited effectiveness with traditional EIS
- **Impulsive motion (意外碰撞):** Single large-displacement events; traditional smoothing algorithms tend to produce a "jump-cut" sensation
- **Rotation/parallax jitter (旋转/透视抖动):** Pure translation models fail; affine or homography (单应性) estimation is required

The core advantage of deep learning stabilization is the ability to learn **nonlinear trajectory smoothing strategies** from large amounts of "stable video – shaky video" pairs, as well as **semantically aware cropping** for complex motion scenarios — capabilities that pure inertial EIS based on gyroscopes cannot achieve.

### 1.2 Mathematical Framework for Video Stabilization

Let the camera motion of frame $t$ be represented by a transformation matrix $C_t$ (affine or homography), and the raw trajectory be:

$$
P_t = \prod_{i=1}^{t} C_i
$$

The goal of the stabilization algorithm is to estimate a smooth trajectory $\tilde{P}_t$ such that the output frame satisfies:

$$
I_t^{\text{stab}} = \mathcal{W}(I_t, \tilde{P}_t \cdot P_t^{-1})
$$

where $\mathcal{W}$ is the spatial transformation (warp) operator. Classical methods (e.g., L1 optimal trajectory smoothing, Gaussian filter smoothing) solve within linear constraints but cannot handle occlusion, dynamic objects, or compositional cropping requirements.

### 1.3 The Role of Optical Flow in Stabilization

Inter-frame optical flow (光流) provides dense motion field estimation and is the core input for deep learning stabilization. PWC-Net (Sun et al., CVPR 2018) is the preferred lightweight optical flow backbone for mobile DL stabilization due to its efficiency:

- Approximately 8.75M parameters, approximately 17.7 GFLOPs (at 448×384, the resolution used in the original paper's benchmark; at 320×240 ≈ 7.2 GFLOPs)
- Employs cost volume (代价体) + deformable convolution, robust to large displacements
- Inference speed approximately 35 ms/frame (reducible to < 10 ms after Snapdragon 8 Gen2 NPU acceleration)

Separating **background motion** (camera motion) from **foreground motion** (moving objects within the scene) is a critical preprocessing step for stabilization, typically accomplished by fitting a global homography via RANSAC. Note that a single global homography is only strictly valid when the background is planar or at approximately uniform depth (i.e., no significant parallax between near and far scene elements); scenes with strong depth variation require either a multi-homography model or a full 3D parallax handling approach.

---

## §2 Algorithm Methods

### 2.1 DUT: Deep Unsupervised Trajectory Stabilization

**DUT** (Deep Unsupervised Trajectory Stabilization), proposed by Liu et al. (CVPR 2021), is a representative work in DL stabilization.

**Core idea:**
- Unsupervised training: requires no stable-shaky video pairs; self-supervised via the temporal consistency of the video itself
- Dual-stream architecture: Content Stream (content preservation) + Motion Stream (motion prediction)
- Contrastive loss: stabilized adjacent frames should be more similar to each other than the original frames (temporal consistency constraint)

**Loss function:**

$$
\mathcal{L} = \lambda_1 \mathcal{L}_{\text{smooth}} + \lambda_2 \mathcal{L}_{\text{content}} + \lambda_3 \mathcal{L}_{\text{crop}}
$$

- $\mathcal{L}_{\text{smooth}}$: trajectory curvature minimization (second-order difference penalty)
- $\mathcal{L}_{\text{content}}$: perceptual feature consistency (VGG feature L2 distance)
- $\mathcal{L}_{\text{crop}}$: effective field-of-view (有效视野) maximization constraint

### 2.2 StabNet: Online Video Stabilization

Wang et al. (IEEE TIP 2018) proposed **StabNet**, the first convolutional network applied to online (causal, 在线) video stabilization:

- **Online inference:** Uses only past frames (no future frames), suitable for real-time live streaming
- **Sliding window:** Input is a sequence of optical flows from the past $L$ (typically $L=30$) frames
- **LSTM temporal modeling:** Models trajectory history to predict the stabilization transform for the current frame

StabNet's real-time capability (online inference latency < 33 ms/frame) makes it the preferred solution for live streaming scenarios. However, because it cannot use future frames, its trajectory smoothing quality is slightly lower than offline methods.

### 2.3 FuSta: Flow-guided Feature Fusion Stabilization

Liu et al. (CVPR 2021) proposed **FuSta** (Flow-guided Feature Fusion Stabilization), introducing semantic features to assist stabilization:

- **Feature alignment:** Uses optical flow to warp adjacent frame features to the reference frame coordinate system, then fuses with Transformer
- **Dynamic object awareness:** Semantic segmentation masks identify pedestrians/vehicles and down-weight dynamic regions during motion estimation
- **Adaptive cropping (自适应裁剪):** Dynamically determines the cropping ratio based on stabilization quality scores (typical range 10%–20%)

FuSta outperforms traditional methods by approximately 4–6 dB (after Cropping Ratio adjustment) on the DAVIS-STAB and NUS-HHD datasets.

### 2.4 PWC-Net Optical Flow Estimation

**PWC-Net** (Pyramid, Warping, and Cost volume), proposed by Sun et al. (CVPR 2018), is the benchmark for modern lightweight optical flow networks:

**Network architecture:**
1. Feature pyramid: 6-level downsampling, with independent convolutions extracting features at each level
2. Cost volume: correlation matrix between current frame features and warped previous frame features, search range $d$
3. Flow estimator: level-by-level refinement, coarse to fine
4. Context network: DilatedConv post-processing to improve edge accuracy

Cost volume computation:

$$
\text{cv}(\mathbf{x}_1, \mathbf{d}) = \langle f_1(\mathbf{x}_1),\ f_2(\mathbf{x}_1 + \mathbf{d}) \rangle, \quad \|\mathbf{d}\| \leq D
$$

where $f_1, f_2$ are features from the two frames and $D$ is the maximum search radius (typically $D=4$, corresponding to $(2D+1)^2=81$ displacement candidates).

### 2.5 Real-time vs. Offline Stabilization Comparison

| Characteristic | Online (Real-time) Stabilization | Offline Stabilization |
|---------------|----------------------------------|----------------------|
| Latency | < 1 frame (no delay) to 3-frame buffer | Typically 30–60 frame buffer |
| Smoothing quality | Lower (no future frame information) | Higher (global trajectory optimization) |
| Representative methods | StabNet, gyroscope EIS | DUT, FuSta, L1 trajectory |
| Typical applications | Live streaming, video calls | Post-production, short video apps |
| Cropping ratio | Larger (requires headroom margin) | Smaller (precise cropping) |

---

## §3 Tuning Guide

### 3.1 Relationship Between Optical Flow Quality and Stabilization Performance

Optical flow estimation error is the primary bottleneck for stabilization quality. Tuning priorities:

1. **Resolution selection:** Run optical flow estimation at lower resolution (360p or 480p), upsample result for full-resolution warp — saves approximately 75% computation
2. **Dynamic object filtering:** RANSAC inlier threshold recommended 2–4 pixels (too strict loses static regions; too loose gets contaminated by foreground)
3. **Multi-scale cost volume:** For large-displacement scenarios (e.g., recording while running), appropriately increase $D$ (search radius) to avoid optical flow truncation errors

### 3.2 Trajectory Smoothing Parameters

**Gaussian smoothing (fast online solution):**
- Window width $\sigma$: recommended 15–30 frames; too small yields insufficient smoothing, too large increases latency
- Adaptive $\sigma$: dynamically adjusted based on motion magnitude — reduce $\sigma$ during vigorous motion to avoid excessive cropping

**L1 optimal (high-quality offline solution):**
- Solves a constrained optimization problem constraining inter-frame trajectory variation (requires tuning the Lagrange coefficient $\lambda$)
- Recommended range: $\lambda \in [1, 20]$; larger values produce stronger smoothing with more cropping

### 3.3 Cropping Ratio and Compositional Balance

After each stabilization warp, blank areas appear at image edges and must be cropped:

- **Fixed cropping (固定裁剪):** Reserve a 10% margin (standard, i.e., crop 5% from each edge, retaining 0.9× FOV) or 20% margin (strong stabilization, crop 10% from each edge, retaining 0.8× FOV); simple to implement but composition is fixed
- **Adaptive cropping:** Dynamically adjusts the crop rectangle based on the actual warp extent per frame, preserving more effective pixels
- **Virtual gyroscope assistance:** Combines IMU gyroscope data for initial coarse alignment, then DL refinement — can reduce the cropping ratio to 5%–8%

### 3.4 Robustness in Dynamic Scenes

- **Pedestrians/vehicles:** Use semantic segmentation (lightweight DeepLabV3+) to generate dynamic region masks; exclude these regions when computing global motion via RANSAC
- **Fast panning (摇镜, pan shot):** Should not force a pan to be smoothed to a static shot; intentional camera motion must be recognized and preserved
- **Transition frame detection:** Detect shot boundaries (shot boundary detection); reset the stabilization window at scene transitions

### 3.5 NPU Deployment Optimization

| Step | Optimization Strategy |
|------|-----------------------|
| Optical flow network | Quantize to INT8, reduce resolution to 480p |
| Global motion estimation | Limit RANSAC to 50 max iterations with early stopping |
| Image warp | Use bilinear interpolation (vs. bicubic) for 4× speed improvement |
| Trajectory smoothing | Perform on CPU side (negligible compute), does not occupy NPU |

---

## §4 Common Artifacts

### 4.1 Rolling Shutter Amplification (卷帘快门伪影放大)

**Manifestation:** After the stabilization warp is applied, the image displays more pronounced diagonal oblique streaks or "jello" distortion than the original video — vertical lines appear curved or tilted from top to bottom within a frame, and when the distortion direction reverses between adjacent frames, a "vibration" sensation is produced. This is especially prominent when hand-holding and walking quickly or shooting rapidly rotating objects.

**Root cause:** CMOS Rolling Shutter (卷帘快门) exposes rows sequentially; during the readout period of each frame (typically 8–15 ms readout time within a 1/30 s frame period), the camera itself is still moving, causing each row to correspond to a different exposure moment and camera pose. The DL stabilization network estimates a global whole-frame homography transform $\tilde{P}_t \cdot P_t^{-1}$; applying this transform implicitly assumes the entire frame was exposed at the same instant. When the residual between the actual RS offset and the global affine transform is "straightened out," RS distortion is not only uncorrected but may actually be amplified in the opposite direction due to over-compensation. Quantification: if the linearity error of vertical straight lines in the stabilized image exceeds 2% of the image height, significant RS artifacts are present.

**Diagnosis method:** On a test video containing known vertical lines (building edges, door frames), measure the maximum pixel deflection of vertical lines before and after stabilization; if the post-stabilization deflection is > 1.2× the pre-stabilization deflection, RS amplification is present. Alternatively, apply Hough line detection to both input and output frames, and compute the variance of the line angle distribution — RS amplification will increase angle variance.

**Mitigation strategies:**
- Apply per-row RS correction before the global warp: independently estimate the motion offset for each row (based on gyroscope timestamps or optical flow interpolation), correct intra-frame RS, then perform stabilization;
- Include RS simulation samples in DL stabilization network training (synthesize simulated RS images with per-row displacement using gyroscope integration), forcing the network to learn RS-aware stabilization transforms;
- Use a piecewise stabilization scheme with independent affine transforms per group of rows (8 rows per group), refining compensation granularity to the row level.

### 4.2 Over-Cropping (过度裁剪)

**Manifestation:** The effective frame area after stabilization is noticeably smaller than the original frame — when the Cropping Ratio falls below 0.85, the subject is cut off at the edges and compositional quality is lost; in standing portrait shots, the top of the head or feet may be cropped; wide landscape scenes become narrow views. A "composition preservation" subjective score < 3/5 indicates a significant problem.

**Root cause:** The trajectory smoothing in DL stabilization networks (such as DUT) is overly aggressive, forcibly smoothing large-amplitude "intentional motion" in the original trajectory (such as a lateral pan shot) to near-static, causing the lateral or vertical offset of the stabilization warp to be large and requiring increased cropping margin. Online stabilization (StabNet) cannot use future frame information, and accumulated errors during large continuous motion cause the crop frame estimation to be oversized. Fixed cropping ratios (e.g., 10%) cannot adapt to the dynamic variation of actual warp magnitude per frame; when the cropping margin is insufficient at frames with large displacement, black borders are exposed, forcing the cropping ratio to be increased further.

**Diagnosis method:** Compute the actual warp offset magnitude per frame (affine matrix translation component $\sqrt{t_x^2+t_y^2}$); plot a histogram of offset distribution across the entire video; if the 95th percentile offset exceeds the reserved cropping margin (e.g., a 10% budget = 5% per side corresponds to 54 pixels per side at 1080p height, or 96 pixels per side at 1920p width), the fixed cropping scheme will expose black borders at those frames; actual cropping ratio $= \min_t(\text{effective area}/\text{full frame area})$, recommended to remain > 0.88.

**Mitigation strategies:**
- Use adaptive cropping: track the actual effective region boundary of the warp transform per frame in real time, dynamically updating the crop rectangle (driven by the maximum offset of the past 30 frames) rather than using a preset fixed ratio;
- Introduce intentional motion detection: when camera angular velocity (gyroscope) exceeds a threshold (e.g., > 30°/s for > 0.5 s), identify as a pan shot and relax trajectory smoothing constraints for that segment, reducing compensation of intentional motion;
- Use a cropping constraint loss $\mathcal{L}_{\text{crop}} = -\text{log}(\text{CroppingRatio})$ in the DL stabilization network, incentivizing the network to output smaller stabilization warp magnitudes during training.

### 4.3 Residual Low-Frequency Jitter (残留低频抖动)

**Manifestation:** After DL stabilization, video still contains low-frequency periodic oscillation dominated by 0.5–2 Hz (e.g., walking step frequency); the amplitude shows no significant reduction compared to the original video, and the Stability Score improvement is less than 10%. In some cases a "spring-back" sensation appears — slight residual jitter oscillates in the reverse direction after stabilization.

**Root cause:** The cutoff frequency of Gaussian trajectory smoothing overlaps with the walking frequency (1–3 Hz); when the Gaussian window standard deviation $\sigma$ is too small (< 15 frames), the attenuation of 1–3 Hz is insufficient (< 10 dB) and low-frequency jitter passes through the smoothing filter. When $\sigma$ is too large, ringing (overshoot) is introduced, creating reverse offsets on both sides of peaks and producing a "spring-back" sensation. Online stabilization (StabNet, LSTM prediction) with a limited history window ($L = 30$ frames) cannot effectively model low-frequency trajectory components beyond 1 second, resulting in poor suppression of long-period jitter below 1 Hz (such as body vertical oscillation during running).

**Diagnosis method:** Perform spectral analysis (FFT) on the camera trajectory ($P_t$ translation/rotation components) of the stabilized video; if the 0.5–3 Hz band still shows significant peaks (power spectral density > 50% of pre-stabilization), low-frequency jitter has not been effectively suppressed. Compute Stability Score $= 1 - \text{std}(C_t)/\text{mean}(C_t)$, which should be > 0.9; if the sign of adjacent-frame trajectory differences alternates (positive and negative signs alternating), this indicates ringing reverse jitter.

**Mitigation strategies:**
- Adjust Gaussian smoothing $\sigma$ to 20–30 frames, covering the 0.5–3 Hz walking frequency range; however, also check for ringing — it is recommended to first plot the actual stabilized trajectory against the Gaussian smoothing result to avoid introducing overshoot;
- Use L1 optimal trajectory smoothing (offline solution) to replace Gaussian smoothing: $\min_{\tilde{P}} \sum_t\|\tilde{P}_t - P_t\|_1 + \lambda\|\Delta^2\tilde{P}_t\|_1$; L1 regularization does not produce ringing;
- Combine IMU gyroscope data to assist with low-frequency jitter modeling: gyroscope integration provides high-precision low-frequency motion prior, the DL network handles correction of gyroscope integration errors (high-frequency refinement), and their combination can improve stabilization effectiveness by 30–50%.

### 4.4 Common Artifacts Reference Table

| Artifact Type | Trigger Conditions | Typical Manifestation | Mitigation |
|--------------|-------------------|----------------------|-----------|
| RS Amplification (RS伪影放大) | Global affine assumption + row-by-row RS exposure | Vertical lines arc-distorted, more pronounced than before stabilization | Per-row RS correction; RS-aware training samples |
| Over-Cropping (过度裁剪) | Overly aggressive trajectory smoothing; fixed cropping ratio | Effective frame too small; subject cut off at edges | Adaptive cropping; intentional motion recognition; cropping constraint loss |
| Residual Low-Freq Jitter (残留低频抖动) | Gaussian $\sigma$ too small or too large | Step-frequency oscillation remains, or reverse "spring-back" sensation | Adjust $\sigma$ to 20–30 frames; L1 optimal smoothing; IMU assistance |
| Dynamic Object Ghosting (动态物体拖影) | Foreground motion uncompensated | Pedestrian/vehicle edge smearing | Do not warp foreground regions; layered stabilization |
| Border Artifacts (边界伪影) | Zero-padding strategy | Blurry/ghosted bands at frame edges | Reflection padding; border region mask loss |

---

## §5 Evaluation Methods

### 5.1 Objective Metrics

| Metric | Description | Computation |
|--------|-------------|-------------|
| Cropping Ratio (裁剪比) | Proportion of effective output area relative to input frame; higher is better | Output resolution / Input resolution |
| Distortion Score (畸变分数) | Measures deformation of grid points after stabilization; lower is better | Distortion component from homography decomposition |
| Stability Score (稳定性分数) | Consistency of adjacent-frame transformation matrices; higher is better | $1 - \text{std}(C_t)/\text{mean}(C_t)$ |
| NIQE/BRISQUE | Evaluates visual quality of output frames | Standard no-reference IQA |

### 5.2 Composite Score (Bundled Score)

The composite stabilization score proposed by Liu et al.:

$$
S = w_1 \cdot \text{Cropping} + w_2 \cdot (1 - \text{Distortion}) + w_3 \cdot \text{Stability}
$$

Typical weights: $w_1 = w_2 = w_3 = 1/3$; a higher score indicates better overall stabilization quality.

### 5.3 Benchmark Datasets

| Dataset | Characteristics | Scale |
|---------|----------------|-------|
| NUS-HHD | Real handheld videos; no ground-truth stable reference | 150 video clips |
| DAVIS-STAB | Dynamic scenes; manually annotated stable GT | 60 video clips |
| DeepStab | Dataset accompanying the DeepStab paper | 61 stable-unstable video pairs |
| YouTube-UGC | Large-scale user-generated videos; multi-scene | 1500+ video clips |

### 5.4 Subjective Evaluation

- **Video Quality Assessment (VQA, 视频质量问卷):** Observers rate "sense of stability," "composition preservation," and "naturalness of motion" separately on a 5-point scale
- **Paired preference test (成对偏好测试):** Present the evaluated method and baseline method side by side; observers select their preference

---

## §6 Code Examples

### 6.1 OpenCV-based Optical Flow Extraction and Global Motion Estimation

```python
import cv2
import numpy as np

def estimate_global_motion(frame1, frame2, max_corners=500):
    """
    用Lucas-Kanade稀疏光流估计帧间全局仿射变换。
    frame1, frame2: uint8 BGR帧
    返回: 2×3仿射矩阵 (float32)
    """
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    # Shi-Tomasi角点检测
    pts1 = cv2.goodFeaturesToTrack(
        gray1, maxCorners=max_corners,
        qualityLevel=0.01, minDistance=10
    )
    if pts1 is None or len(pts1) < 4:
        return np.eye(2, 3, dtype=np.float32)

    # Lucas-Kanade光流追踪
    pts2, status, _ = cv2.calcOpticalFlowPyrLK(
        gray1, gray2, pts1, None,
        winSize=(21, 21), maxLevel=3
    )
    good1 = pts1[status.ravel() == 1]
    good2 = pts2[status.ravel() == 1]

    if len(good1) < 4:
        return np.eye(2, 3, dtype=np.float32)

    # RANSAC估计全局仿射变换
    M, inliers = cv2.estimateAffinePartial2D(
        good1, good2,
        method=cv2.RANSAC,
        ransacReprojThreshold=3.0
    )
    return M if M is not None else np.eye(2, 3, dtype=np.float32)
```

### 6.2 Trajectory Smoothing (Gaussian Low-pass Filter)

```python
import numpy as np
from scipy.ndimage import gaussian_filter1d

def smooth_trajectory(transforms, sigma=15):
    """
    对变换参数轨迹施加高斯低通滤波。
    transforms: (T, 6) 每帧仿射矩阵参数，顺序 [a,b,c,d,tx,ty]
    sigma:      高斯窗口标准差（帧数单位）
    返回:       平滑后的变换参数 (T, 6)
    """
    # 累计轨迹（积分）
    trajectory = np.cumsum(transforms, axis=0)
    # 高斯平滑
    smoothed = gaussian_filter1d(trajectory, sigma=sigma, axis=0)
    # 还原为逐帧差分
    smoothed_diff = np.diff(smoothed, axis=0, prepend=smoothed[:1])
    return smoothed_diff

def apply_stabilization(frames, transforms, crop_ratio=0.1):
    """
    将平滑后的变换施加到帧序列，并裁剪边缘。
    frames:     list of uint8 BGR帧
    transforms: (T, 6) 平滑后仿射参数
    crop_ratio: 单侧裁剪比例（单边）。crop_ratio=0.05对应"10%裁剪预算"（双侧各5%），
                保留0.90× FOV；crop_ratio=0.10对应"20%裁剪预算"（双侧各10%），
                保留0.80× FOV。
    返回:       稳定后的帧列表
    """
    h, w = frames[0].shape[:2]
    crop_h = int(h * crop_ratio)  # 单边裁剪像素数
    crop_w = int(w * crop_ratio)  # 单边裁剪像素数
    out_h = h - 2 * crop_h
    out_w = w - 2 * crop_w

    stabilized = []
    for i, (frame, params) in enumerate(zip(frames, transforms)):
        M = params.reshape(2, 3)
        # 施加变换
        warped = cv2.warpAffine(frame, M, (w, h),
                                flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_REFLECT)
        # 裁剪边缘
        cropped = warped[crop_h:crop_h+out_h, crop_w:crop_w+out_w]
        stabilized.append(cropped)
    return stabilized
```

### 6.3 Lightweight DL Stabilization Network (Demo Architecture)

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class FlowGuidedStabNet(nn.Module):
    """
    光流引导的轻量防抖网络。
    输入: 当前帧及过去L帧的堆叠光流场 (B, L*2, H, W)
    输出: 当前帧稳定变换的仿射参数 (B, 6)
    """
    def __init__(self, window_len=10, base_ch=32):
        super().__init__()
        in_ch = window_len * 2  # L帧 × 2通道(u,v)

        self.encoder = nn.Sequential(
            nn.Conv2d(in_ch, base_ch, 7, stride=2, padding=3),   # /2
            nn.ReLU(inplace=True),
            nn.Conv2d(base_ch, base_ch * 2, 5, stride=2, padding=2),  # /4
            nn.ReLU(inplace=True),
            nn.Conv2d(base_ch * 2, base_ch * 4, 3, stride=2, padding=1),  # /8
            nn.ReLU(inplace=True),
        )
        self.pool = nn.AdaptiveAvgPool2d(4)
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(base_ch * 4 * 16, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, 6),
        )
        # 初始化为恒等变换
        with torch.no_grad():
            self.fc[-1].weight.zero_()
            self.fc[-1].bias.copy_(torch.tensor(
                [1, 0, 0, 0, 1, 0], dtype=torch.float32))

    def forward(self, flow_seq):
        """
        flow_seq: (B, L*2, H, W) 光流序列
        返回:     (B, 6) 仿射变换参数
        """
        feat = self.encoder(flow_seq)
        feat = self.pool(feat)
        params = self.fc(feat)
        return params

    def warp_frame(self, frame, params):
        """
        用预测的仿射参数warp输入帧。
        frame:  (B, C, H, W)
        params: (B, 6)
        返回:   (B, C, H, W) 稳定后帧
        """
        B = frame.shape[0]
        theta = params.view(B, 2, 3)
        grid = F.affine_grid(theta, frame.size(), align_corners=False)
        return F.grid_sample(frame, grid,
                             mode='bilinear',
                             padding_mode='reflection',
                             align_corners=False)
```

### 6.4 Optical Flow for Video Stabilization: Sparse LK and Dense PWC-Net

```python
import cv2
import numpy as np
import torch
import torch.nn.functional as F


def estimate_affine_transform(prev_frame, curr_frame):
    """Estimate 2×3 affine matrix (translation+rotation) via sparse Lucas-Kanade flow."""
    gray_p = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    gray_c = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    pts  = cv2.goodFeaturesToTrack(gray_p, 200, 0.01, 10)
    pts2, st, _ = cv2.calcOpticalFlowPyrLK(gray_p, gray_c, pts, None)
    M, _ = cv2.estimateAffine2D(pts[st[:, 0] == 1], pts2[st[:, 0] == 1])
    return M.astype(np.float32)  # shape (2, 3)


def compute_pwcnet_flow(model, img1, img2, scale=0.5):
    """
    Compute dense optical flow from img1→img2 using a pre-loaded PWC-Net model.
    model:  PWCNet instance with loaded weights (.eval() mode)
    img1, img2: (B, 3, H, W) float32 tensor, range [0, 1]
    scale:  down-sample ratio for speed (0.5 = half resolution)
    returns: (B, 2, H, W) flow field in pixel displacement units at original resolution
    """
    H, W = img1.shape[2], img1.shape[3]
    if scale != 1.0:
        img1_s = F.interpolate(img1, scale_factor=scale, mode='bilinear', align_corners=False)
        img2_s = F.interpolate(img2, scale_factor=scale, mode='bilinear', align_corners=False)
    else:
        img1_s, img2_s = img1, img2

    with torch.no_grad():
        flow_s = model(img1_s, img2_s)  # (B, 2, H*scale, W*scale)

    if scale != 1.0:
        flow = F.interpolate(flow_s, size=(H, W), mode='bilinear', align_corners=False)
        flow = flow / scale  # correct displacement magnitude after upsampling
    else:
        flow = flow_s

    return flow

# ─── Usage example 1: sparse LK affine transform ─────────────────────────────
frame_prev = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
frame_curr = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
M = estimate_affine_transform(frame_prev, frame_curr)
# Output: M.shape → (2, 3), float32 affine matrix (translation + rotation)

# ─── Usage example 2: dense PWC-Net flow ─────────────────────────────────────
# model = PWCNet().eval()  # load pre-trained weights before calling
# t1 = torch.from_numpy(frame_prev).float().permute(2,0,1).unsqueeze(0) / 255.0
# t2 = torch.from_numpy(frame_curr).float().permute(2,0,1).unsqueeze(0) / 255.0
# flow = compute_pwcnet_flow(model, t1, t2, scale=0.5)
# Output: flow.shape → (1, 2, 256, 256), pixel displacement (dx, dy) per location

```

---

## References

1. Liu, S., et al. **"Deep Unsupervised Learning for Video Stabilization (DUT)."** CVPR 2021.
2. Wang, M., et al. **"Deep Online Video Stabilization with Multi-grid Warping Transformation Learning (StabNet)."** IEEE TIP 2018.
3. Liu, Z., et al. **"FuSta: Flexible and Unified Video Stabilization (FuSta)."** CVPR 2021.
4. Sun, D., et al. **"PWC-Net: CNNs for Optical Flow Using Pyramid, Warping, and Cost Volume."** CVPR 2018.
5. Xu, S., et al. **"Blind Video Temporal Consistency via Deep Video Prior."** NeurIPS 2021.
6. Yu, J., Ramamoorthi, R. **"Robust Video Stabilization by Optimization in CNN Weight Space."** CVPR 2020.
7. Grundmann, M., et al. **"Calibration-free Rolling Shutter Removal."** ICCP 2012.
8. Liu, F., et al. **"Content-preserving Warps for 3D Video Stabilization."** ACM TOG 2009.
9. Dosovitskiy, A., et al. **"FlowNet: Learning Optical Flow with Convolutional Networks."** ICCV 2015.
10. Teed, Z., Deng, J. **"RAFT: Recurrent All-Pairs Field Transforms for Optical Flow."** ECCV 2020.

## §8 Glossary

| Term | Chinese | Explanation |
|------|---------|-------------|
| Video Stabilization | 视频防抖 | Technology that eliminates or reduces unintended inter-frame motion in video |
| Electronic Image Stabilization (EIS) | 电子防抖 | Stabilization achieved through digital cropping/warping, without moving optical elements |
| Optical Image Stabilization (OIS) | 光学防抖 | Hardware stabilization that compensates for camera motion by shifting lens groups |
| Optical Flow | 光流 | Dense velocity field describing pixel motion between frames |
| Homography | 单应性 | Projective transformation between two planes; 8 degrees of freedom |
| Cost Volume | 代价体 | Correlation matrix between two-frame features across displacement space; core component of PWC-Net |
| Trajectory Smoothing | 轨迹平滑 | Applying low-pass filtering to the camera motion trajectory to eliminate jitter |
| Rolling Shutter Effect | 果冻效应 | Image distortion caused by row-by-row exposure in CMOS rolling shutter sensors |
| Cropping Ratio | 裁剪比 | Proportion of the effective frame retained after stabilization relative to the original resolution |
| Online Stabilization | 在线防抖 | Real-time stabilization using only current and historical frames (no future frames) |
| Offline Stabilization | 离线防抖 | High-quality stabilization using the complete video sequence (including future frames) |
| RANSAC | RANSAC | Random Sample Consensus algorithm; used for robust global motion estimation |
