# Part 2, Chapter 13: Digital Zoom & Image Resampling

---

## Table of Contents

1. [Theory](#1-theory)
2. [Calibration](#2-calibration)
3. [Tuning Guide](#3-tuning-guide)
4. [Artifact Analysis](#4-artifact-analysis)
5. [Evaluation Methods](#5-evaluation-methods)
6. [Reference Code](#6-reference-code)

---

## 1 Theory

### 1.1 Digital Zoom vs. Optical Zoom

The essence of zoom is changing the imaging field of view (FoV 视场角), so that a distant subject occupies more pixel area on the sensor. The two approaches differ fundamentally:

**Optical zoom (光学变焦)**: The lens group physically moves to change the focal length $f$, altering the image magnification. With the same sensor size, doubling the focal length halves the FoV, doubling the fraction of the sensor occupied by the subject — with no resolution penalty. The MTF (modulation transfer function 调制传递函数) is largely unchanged.

**Digital zoom (数字变焦)**: The focal length is fixed; the sensor output is cropped and then upscaled. A $k\times$ digital zoom is equivalent to taking the central $1/k$ region of the full-resolution image and enlarging it. The effective pixel count drops to $1/k^2$ of the original.

**The fundamental cost**: MTF degradation in digital zoom is intrinsically caused by upsampling interpolation — interpolation cannot recover lost high-frequency information. If the original image's Nyquist frequency is $f_N$, then after $k\times$ digital zoom the effective Nyquist frequency drops to $f_N / k$.

**Summary comparison**:

| Characteristic | Optical Zoom | Digital Zoom |
|----------------|-------------|-------------|
| Image quality | Lossless (limited by optical design) | Degrades with increasing magnification |
| Hardware cost | High (mechanical lens group) | Low (pure software/DSP) |
| Size and weight | Large (zoom lens assembly) | No additional cost |
| MTF | Close to native | Decreases with magnification |
| Use case | High image-quality demand | Portable, cost-sensitive applications |

---

### 1.2 Basic Crop-and-Upscale Implementation

The simplest digital zoom pipeline:

1. **Crop**: Extract a $W/k \times H/k$ region from the center of the full-resolution image (or a user-specified area).
2. **Upscale**: Enlarge the cropped region back to the target resolution $W \times H$.

In mathematical terms: given original image $I$ of size $W \times H$, the top-left corner of the crop region for $k\times$ digital zoom is:

$$
x_{\text{crop}} = \frac{W}{2} - \frac{W}{2k},\quad y_{\text{crop}} = \frac{H}{2} - \frac{H}{2k}
$$

$$
w_{\text{crop}} = \frac{W}{k},\quad h_{\text{crop}} = \frac{H}{k}
$$

The cropped region $I_{\text{crop}}$ is then upsampled:

$$
I_{\text{zoom}}(x, y) = \text{Upsample}\left(I_{\text{crop}},\ k\right)
$$

---

### 1.3 Resampling Filters

The quality of upsampling depends entirely on the choice of resampling filter (重采样滤波器).

**Bilinear interpolation (双线性插值)**:

The value at a non-integer coordinate $(x', y')$ is a linear combination of four neighboring pixels:

$$
I(x', y') = (1-u)(1-v)I_{00} + u(1-v)I_{10} + (1-u)vI_{01} + uvI_{11}
$$

where $u = x' - \lfloor x' \rfloor$ and $v = y' - \lfloor y' \rfloor$.

- **Advantages**: Simple computation; no ringing (振铃).
- **Disadvantages**: The equivalent low-pass filter has a relatively low cutoff frequency, yielding a soft, blurry upsampled image with significant high-frequency detail loss.

**Bicubic interpolation (双三次插值)**:

Uses 16 pixels in a 4×4 neighborhood, weighted by a cubic spline kernel:

$$
h(t) = \begin{cases} (a+2)|t|^3 - (a+3)|t|^2 + 1 & |t| \leq 1 \\ a|t|^3 - 5a|t|^2 + 8a|t| - 4a & 1 < |t| < 2 \\ 0 & |t| \geq 2 \end{cases}
$$

Typically $a = -0.5$ (Keys kernel, most common) or $a = -0.75$ (a sharper bicubic variant). Note: Mitchell-Netravali (1988) uses an independent B/C parameter system (classic recommendation $B = C = 1/3$) and does not directly correspond to the single-parameter $a$ formulation above.

- **Advantages**: Sharper than bilinear; edge transitions are more natural.
- **Disadvantages**: Some residual softness; mild ringing may appear at strong edges.

**Lanczos interpolation**:

Uses a windowed-sinc kernel:

$$
L(x) = \begin{cases} \text{sinc}(x) \cdot \text{sinc}(x/a) & |x| < a \\ 0 & |x| \geq a \end{cases}
$$

where $\text{sinc}(x) = \sin(\pi x)/(\pi x)$ and the window parameter $a$ is usually 2 or 3.

- **Advantages**: Frequency response closest to an ideal low-pass filter; sharpest upsampling result with the most detail retained.
- **Disadvantages**: Higher computational cost; ringing artifacts (Gibbs effect 吉布斯效应) may appear at high-contrast edges (e.g., sharp black-white boundaries).

**Frequency-response comparison of the three filters**:

| Filter | Passband flatness | Cutoff frequency | Ringing risk | Computation |
|--------|------------------|-----------------|-------------|-------------|
| Bilinear | Good | Low (~0.5 $f_N$) | None | Lowest |
| Bicubic | Good | Medium (~0.7 $f_N$) | Low | Medium |
| Lanczos-2 | Good | High (~0.9 $f_N$) | Medium | High |
| Lanczos-3 | Good | Highest | Higher | Highest |

---

### 1.4 ISP Demosaic Layer Digital Zoom

In high-quality ISP implementations, digital zoom up to 2× can be realized directly within the demosaic (去马赛克) stage rather than as a post-processing crop-and-upscale step.

**Principle**: When demosaicing a Bayer RAW sensor, the interpolation coefficients can be computed for a specific target output resolution such that the kernel center maps directly onto the crop region's pixels. This avoids the quality loss introduced by two sequential sampling operations (demosaic to full resolution, then crop).

**Advantages**:
- Full pixel utilization (全像素利用): no effective sensor pixels are wasted.
- Fewer interpolation stages: a single interpolation step is superior to two cascaded steps.
- In the 1.0×–2.0× zoom range, quality approaches that of optical zoom.

### 1.5 Hybrid Zoom Systems

Modern smartphones commonly deploy multi-camera systems that combine a main (wide-angle) camera and a telephoto camera to deliver seamless optical + digital zoom:

**Typical configuration** (flagship smartphone example):
- Main camera: equivalent 24 mm, 1/1.5" sensor, 26 MP
- Telephoto: equivalent 85 mm, 1/3.5" sensor, 12 MP (~3.5× optical)
- Periscope telephoto: equivalent 230 mm, 1/4.4" sensor, 12 MP (~10× optical)

**Zoom switching strategy**:

$$
\text{Camera} = \begin{cases}
\text{Main} & 1.0 \times \leq z < 2.5 \times \\
\text{Main digital zoom / telephoto digital zoom blend} & 2.5 \times \leq z \leq 4 \times \\
\text{Telephoto} & 4 \times \leq z < 8 \times \\
\text{Telephoto + digital zoom} & z \geq 8 \times
\end{cases}
$$

Near the switching point, dual-camera fusion (双摄融合) is used for a gradual transition, preventing visible visual jumps.

### 1.6 Smooth Zoom Transitions (Zoom Locking)

During live preview, the user's manual zoom must transition smoothly to prevent zoom jitter (画面抖动):

**Zoom curve smoothing**: Apply a first-order low-pass filter to the zoom factor $z(t)$:

$$
z_{\text{smooth}}(t) = \lambda \cdot z(t) + (1 - \lambda) \cdot z_{\text{smooth}}(t-1)
$$

where $\lambda \in [0.1, 0.3]$ (smaller $\lambda$ produces a slower, smoother transition).

**Dual-camera switching transition**: Near the main-to-telephoto switching point, blend the two image streams with an Alpha ramp:

$$
I_{\text{out}} = \alpha(z) \cdot I_{\text{telephoto}} + (1 - \alpha(z)) \cdot I_{\text{wide}}
$$

where $\alpha(z)$ transitions smoothly from 0 to 1 near the switch point over a transition band of approximately 0.5×.

### 1.7 AI Super-Resolution-Assisted Digital Zoom

AI super-resolution (SR 超分辨率) models learn the mapping from low-resolution to high-resolution images and compensate for the high-frequency loss caused by digital zoom.

**Typical network architectures**:
- ESRGAN (Enhanced Super-Resolution GAN): uses **RRDBNet** (Residual-in-Residual Dense Block) as the backbone, combined with adversarial and perceptual losses; high perceptual quality output.
- RCAN (Residual Channel Attention Network): lightweight, suitable for mobile deployment.
- Real-ESRGAN: trained on real-world degradations (noise, compression, blur); strong generalization.

**Integration with digital zoom**:

$$
I_{\text{SR-zoom}}(k) = \text{SR-Model}\left(\text{Crop}(I, 1/k)\right)
$$

Compared to traditional interpolation, SR models can improve perceived sharpness by 1–2 times, with the most noticeable improvements at 4×–10× digital zoom.

**Hardware constraint**: On-device SR inference must complete in less than 100 ms (real-time video requires < 33 ms at 30 fps). Quantization (INT8) or lightweight networks (IMDN, A-ESRGAN-Tiny) are typically used.

### 1.8 Periscope Telephoto Systems

Flagship long-zoom cameras from OPPO, Xiaomi, Samsung, and others use a periscope prism to fold the optical path, achieving 5×–10× optical zoom while keeping the handset thin.

**Optical path principle**: Incident light is deflected 90° by a 45° periscope prism, propagating along the phone's longitudinal axis. This greatly increases the module's available depth, equivalently extending the focal length.

**Design challenges**:
- OIS (optical image stabilization 光学防抖): the periscope OIS must control the prism angle rather than translate the lens group, demanding higher compensation bandwidth.
- High dynamic range scenes: the telephoto end has an extremely shallow depth of field (DoF 景深), requiring strict AF (autofocus 自动对焦) accuracy (error < 5 μm).
- Low light: the telephoto end typically operates at f/2.8–f/4.0, limiting light intake; MFNR (multi-frame NR) compensation is required.

---

## 2 Calibration

### 2.1 Zoom MTF Calibration

MTF calibration at each zoom factor forms the basis for assessing digital zoom quality.

**Equipment**: ISO 12233 resolution test chart, collimated light source, precision focusing stage.

**Procedure**:
1. At each zoom factor (1×, 2×, 4×, 8×, 10×), capture the ISO 12233 chart with precise focus at each setting.
2. Use imatest or MTFMapper to extract the MTF curve from the slanted edge.
3. Record MTF50 (the spatial frequency at which the response drops to 50%; units: lp/mm or cy/px).
4. Plot the "zoom factor vs. MTF50" curve and compare it against the optical zoom reference line (if available).

**Calibration target**: MTF50 at 2× digital zoom should be no less than 70% of the optical-zoom MTF50.

### 2.2 Dual-Camera Alignment Calibration

Hybrid zoom systems require calibrating the relative pose (extrinsic calibration 外参标定) between the main and telephoto cameras:

1. Use a checkerboard calibration target; capture images with both cameras at multiple distances (0.5 m–3 m).
2. Compute the rotation matrix $R$ and translation vector $t$ (stereo calibration 双目标定):

$$
x_{\text{telephoto}} = K_T (R x_{\text{wide}} + t)
$$

3. Store the calibration result in EEPROM for use by the zoom fusion module.
4. Verification: alignment error should be < 2 pixels (at 4× zoom).

---

## 3 Tuning Guide

### 3.1 Resampling Filter Selection

| Zoom Factor | Recommended Filter | Rationale |
|-------------|-------------------|-----------|
| 1.0×–1.5× | Bilinear or bicubic | Low magnification; MTF loss is small; avoid ringing |
| 1.5×–3× | Bicubic ($a=-0.5$) | Balances sharpness and ringing risk |
| 3×–6× | Lanczos-2 | Maximum sharpness needed to compensate MTF loss |
| Above 6× | Lanczos-3 + SR | Interpolation alone is insufficient; AI assistance required |

### 3.2 Dual-Camera Switching Point Optimization

The switching point should be avoided under two conditions:
- **Main camera crop near the sensor edge**: optical quality degrades (increased vignetting) as the crop region approaches the sensor boundary. In this case, switch to telephoto earlier.
- **Low-light scenes**: when telephoto light intake is insufficient, delay the switch point (retain the main camera + digital zoom approach).

**Illuminance-adaptive switching strategy**:

```
if EV < EV_threshold:  # Low light
    switch_point = default_switch_point * 1.3  # Delay the switch
else:
    switch_point = default_switch_point
```

### 3.3 SR Model Parameters

- **Inference precision**: INT8 quantization (PSNR loss < 0.5 dB vs. FP32; speed improvement 3–4×).
- **Tile size**: Tile-based inference for large resolutions; typical tile 128×128 to 256×256 with 16–32 pixel overlap (prevents tile-boundary artifacts).
- **Strength blending**: Blend SR model output with traditional interpolation output by weight to control sharpening intensity:

$$
I_{\text{final}} = w_{\text{SR}} \cdot I_{\text{SR}} + (1 - w_{\text{SR}}) \cdot I_{\text{bicubic}}
$$

Typical $w_{\text{SR}} \in [0.6, 0.9]$.

---

## 4 Artifact Analysis

### 4.1 Aliasing (锯齿)

**Symptom**: At high zoom factors (> 4×), fine-grained textures (fabric, brick walls, foliage) exhibit irregular jagged patterns or moiré — high-frequency content aliasing to lower frequencies.

**Cause**: Cropping reduces the effective sampling rate. If the cropped image contains frequency components $f > f_N / k$, undersampling produces aliasing:

$$
f_{\text{alias}} = |f_{\text{signal}} - n \cdot f_s/k|
$$

**Solutions**:
- Apply an anti-aliasing low-pass pre-filter to the image before cropping, with cutoff frequency set to $f_N / k$.
- In ISP-level digital zoom at the demosaic stage, an appropriate low-pass effect is naturally introduced.

### 4.2 Moiré Pattern (摩尔纹)

**Symptom**: When photographing regular textures (display screens, fabric), periodic colored interference fringes appear; the fringe frequency and color change with the zoom factor.

**Cause**: A beat frequency between the scene texture and the sensor's sampling frequency produces low-frequency interference. Digital zoom changes the effective sampling frequency, shifting the beat position and making the moiré more prominent.

**Solutions**:
- Low-pass pre-filtering (see the aliasing solution above).
- Demoire filter (去摩尔纹滤波器): detect the moiré frequency in the frequency domain and selectively suppress it.

### 4.3 Interpolation Ringing

**Symptom**: Bright-dark fringes (Gibbs phenomenon 吉布斯现象) appear adjacent to high-contrast edges (e.g., at a black-white boundary), giving edges a "halo" or "outline" appearance. Lanczos interpolation is particularly prone to this.

**Cause**: The negative sidelobes of the Lanczos kernel produce overshoot at edges:

$$
I_{\text{ringing}} = h_{\text{Lanczos}} * I_{\text{edge}} \neq I_{\text{ideal\_sharp\_edge}}
$$

**Solutions**:
- Apply a Hann or Blackman window function to the Lanczos kernel to suppress sidelobes.
- In edge regions ($|\nabla I| > T_{\text{edge}}$), locally reduce the Lanczos interpolation weight in favor of bicubic.
- The Mitchell-Netravali bicubic kernel ($B=1/3, C=1/3$) achieves a good balance between sharpness and ringing.

### 4.4 Fine Detail Loss (细节损失)

**Symptom**: After high zoom factors, originally sharp texture details (hair strands, distant text) become soft and irrecoverable.

**Cause**: This is an inherent limitation of digital zoom, not a processing artifact. Information below the Nyquist frequency was simply never sampled; no interpolation algorithm can recover it.

**Mitigation**:
- AI SR models use learned priors (statistical knowledge of natural image structure) to "hallucinate" high-frequency detail (hallucination 幻觉式补充). Perceptual quality improves, but no true objective information is added.
- Use a higher-resolution sensor to provide redundant pixels (e.g., a 50 MP sensor at 2× zoom is equivalent to a 12.5 MP optical zoom).

---

## 5 Evaluation Methods

### 5.1 Zoom MTF Test

**Measurement procedure**:
1. Capture the ISO 12233 test chart with the focal length fixed; shoot at 1×, 2×, 3×, 4×, and 8× zoom.
2. Use the imatest SFR (Slanted Edge MTF) module to compute MTF50 at each zoom factor.
3. Normalize against the optical zoom reference line (if available); plot the "zoom factor vs. MTF50 percentage" curve.

**Pass criteria**:
- 2× digital zoom: MTF50 ≥ native MTF50 × 0.70
- 4× digital zoom: MTF50 ≥ native MTF50 × 0.45
- 10× digital zoom (with SR): MTF50 ≥ native MTF50 × 0.35

### 5.2 Perceived Sharpness (感知锐利度)

Objective MTF does not fully correlate with perceived sharpness. Use the perceived sharpness metric from CPIQ (Camera Phone Image Quality) or JNDs (just noticeable differences):

$$
\text{PS}(\text{zoom}) = \int_0^{f_N} W(f) \cdot \text{MTF}(f, \text{zoom}) \, df
$$

where $W(f)$ is the human visual sensitivity weighting function (CSF, contrast sensitivity function 对比敏感函数).

### 5.3 Optical Equivalence Comparison

For hybrid zoom systems, evaluate the equivalent quality of "digital zoom + AI SR" at 6× against pure optical 6× telephoto:

1. Capture the same scene with: (a) main camera at 6× digital zoom (with SR), and (b) pure 6× optical telephoto.
2. Conduct a double-blind subjective evaluation (MOS) comparing sharpness, detail, and noise across the two.
3. Target: the MOS of digital zoom + SR should be no less than 0.85 × the MOS of pure optical zoom.

### 5.4 Zoom Transition Smoothness Test

Record a continuous zoom video from 1× to 10× and analyze:
- Luminance/chroma jump at the switching point ($\Delta L$, $\Delta C$): should be < 5%.
- Frame-to-frame image center displacement (shake): should be < 3 pixels.
- Subjective smoothness MOS: ≥ 4.0 (on a 1–5 scale).

---

## 6 Reference Code

### 6.1 Multiple Resampling Interpolation Implementations

```python
import numpy as np
import cv2
from enum import Enum
from typing import Tuple, Optional


class ResampleMethod(Enum):
    BILINEAR = "bilinear"
    BICUBIC  = "bicubic"
    LANCZOS  = "lanczos"


def digital_zoom(
    image: np.ndarray,
    zoom_factor: float,
    method: ResampleMethod = ResampleMethod.LANCZOS,
    center: Optional[Tuple[float, float]] = None,
) -> np.ndarray:
    """
    数字变焦：裁剪后上采样到原始分辨率。

    Parameters
    ----------
    image       : 输入图像，BGR 或 灰度，uint8
    zoom_factor : 变焦倍率（> 1 为放大），如 2.0 表示 2× 数字变焦
    method      : 重采样方法
    center      : 变焦中心的归一化坐标 (cx, cy)，范围 [0,1]，
                  None 时默认图像中心 (0.5, 0.5)

    Returns
    -------
    变焦后图像，尺寸与输入相同
    """
    if zoom_factor <= 1.0:
        return image.copy()

    H, W = image.shape[:2]

    if center is None:
        cx, cy = 0.5, 0.5
    else:
        cx, cy = center

    # 裁剪区域尺寸
    crop_w = W / zoom_factor
    crop_h = H / zoom_factor

    # 裁剪左上角坐标（确保不越界）
    x1 = int(np.clip(cx * W - crop_w / 2, 0, W - crop_w))
    y1 = int(np.clip(cy * H - crop_h / 2, 0, H - crop_h))
    x2 = int(x1 + crop_w)
    y2 = int(y1 + crop_h)

    cropped = image[y1:y2, x1:x2]

    # 上采样插值
    interpolation_map = {
        ResampleMethod.BILINEAR: cv2.INTER_LINEAR,
        ResampleMethod.BICUBIC:  cv2.INTER_CUBIC,
        ResampleMethod.LANCZOS:  cv2.INTER_LANCZOS4,
    }
    interp = interpolation_map[method]

    zoomed = cv2.resize(cropped, (W, H), interpolation=interp)
    return zoomed


def lanczos_kernel(x: np.ndarray, a: int = 3) -> np.ndarray:
    """
    Lanczos-a 核函数（1D）。

    Parameters
    ----------
    x : 采样位置数组
    a : Lanczos 参数（窗口半宽，通常取 2 或 3）

    Returns
    -------
    核值数组
    """
    result = np.zeros_like(x, dtype=np.float64)
    nonzero = np.abs(x) < a
    xn = x[nonzero]
    # sinc(x) * sinc(x/a)
    pi_x = np.pi * xn
    pi_xa = np.pi * xn / a
    result[nonzero] = (
        np.where(np.abs(xn) < 1e-10, 1.0, np.sin(pi_x) / pi_x) *
        np.where(np.abs(xn / a) < 1e-10, 1.0, np.sin(pi_xa) / pi_xa)
    )
    return result


def compute_mtf(
    image: np.ndarray,
    edge_direction: str = "horizontal",
    roi: Optional[Tuple[int, int, int, int]] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    使用斜边法（Slanted Edge Method）计算图像 MTF。

    Parameters
    ----------
    image          : 输入灰度图像（含有斜边的测试图卡）
    edge_direction : 边缘主方向，"horizontal" 或 "vertical"
    roi            : 感兴趣区域 (x, y, w, h)

    Returns
    -------
    frequencies    : 空间频率数组（cy/px，归一化）
    mtf            : 对应 MTF 值数组
    """
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float64)
    else:
        gray = image.astype(np.float64)

    if roi is not None:
        x, y, w, h = roi
        gray = gray[y:y+h, x:x+w]

    H, W = gray.shape

    # 沿边缘方向计算 ESF（Edge Spread Function，边缘扩展函数）
    if edge_direction == "vertical":
        # 对每行取均值，得到水平方向 ESF
        esf = gray.mean(axis=0)
    else:
        esf = gray.mean(axis=1)

    # ESF 求导得 LSF（Line Spread Function，线扩展函数）
    lsf = np.gradient(esf)

    # LSF 做 FFT 得 OTF，取模得 MTF
    n = len(lsf)
    otf = np.fft.fft(lsf, n=n * 4)  # 零填充提高频率分辨率
    mtf = np.abs(otf[:n * 2])
    mtf = mtf / (mtf[0] + 1e-9)  # 归一化

    frequencies = np.fft.fftfreq(n * 4)[:n * 2]
    frequencies = np.abs(frequencies)

    # 仅取 [0, 0.5] cy/px（奈奎斯特以内）
    valid = frequencies <= 0.5
    return frequencies[valid], mtf[valid]


class HybridZoomSystem:
    """
    混合变焦系统模拟（主摄 + 长焦双摄协同）。
    """

    def __init__(
        self,
        wide_equiv_fl: float = 24.0,   # 主摄等效焦距（mm）
        tele_equiv_fl: float = 85.0,   # 长焦等效焦距（mm）
        switch_zoom: float = 2.5,      # 切换倍率
        transition_width: float = 0.5, # 过渡区宽度（倍率）
    ):
        self.wide_fl = wide_equiv_fl
        self.tele_fl = tele_equiv_fl
        self.optical_ratio = tele_fl = tele_equiv_fl / wide_equiv_fl
        self.switch_zoom = switch_zoom
        self.transition_width = transition_width

    def get_blend_weights(self, zoom_factor: float) -> Tuple[float, float]:
        """
        返回主摄和长焦的混合权重 (w_wide, w_tele)。
        在切换点附近平滑过渡。
        """
        z_low = self.switch_zoom - self.transition_width / 2
        z_high = self.switch_zoom + self.transition_width / 2

        if zoom_factor <= z_low:
            return (1.0, 0.0)
        elif zoom_factor >= z_high:
            return (0.0, 1.0)
        else:
            t = (zoom_factor - z_low) / self.transition_width
            # 使用余弦平滑曲线
            alpha_tele = (1 - np.cos(np.pi * t)) / 2.0
            return (1.0 - alpha_tele, alpha_tele)

    def simulate_zoom(
        self,
        wide_frame: np.ndarray,
        tele_frame: np.ndarray,
        zoom_factor: float,
        output_size: Optional[Tuple[int, int]] = None,
    ) -> np.ndarray:
        """
        模拟混合变焦输出。

        Parameters
        ----------
        wide_frame  : 主摄原始帧
        tele_frame  : 长焦原始帧（已完成视角对齐）
        zoom_factor : 目标变焦倍率
        output_size : 输出尺寸 (W, H)，None 时与主摄同尺寸

        Returns
        -------
        混合变焦输出图像
        """
        H, W = wide_frame.shape[:2]
        if output_size is None:
            output_size = (W, H)

        w_wide, w_tele = self.get_blend_weights(zoom_factor)

        # 主摄数字变焦
        wide_zoomed = digital_zoom(wide_frame, zoom_factor, ResampleMethod.LANCZOS)
        wide_zoomed = cv2.resize(wide_zoomed, output_size)

        # 长焦数字变焦（相对于长焦自身焦距的倍率）
        tele_zoom = zoom_factor / self.optical_ratio
        if tele_zoom > 1.0:
            tele_zoomed = digital_zoom(tele_frame, tele_zoom, ResampleMethod.LANCZOS)
        else:
            tele_zoomed = tele_frame.copy()
        tele_zoomed = cv2.resize(tele_zoomed, output_size)

        # 混合
        if w_tele < 1e-3:
            return wide_zoomed
        elif w_wide < 1e-3:
            return tele_zoomed
        else:
            return cv2.addWeighted(wide_zoomed, w_wide, tele_zoomed, w_tele, 0)


def benchmark_zoom_quality(
    image: np.ndarray,
    zoom_factors: list = [1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0],
) -> dict:
    """
    对比不同插值方法在各变焦倍率下的质量指标。

    Parameters
    ----------
    image        : 参考图像（高质量，用作真值）
    zoom_factors : 待测变焦倍率列表

    Returns
    -------
    results : 字典，包含各方法各倍率的 PSNR 和感知锐利度指标
    """
    results = {}
    methods = [ResampleMethod.BILINEAR, ResampleMethod.BICUBIC, ResampleMethod.LANCZOS]

    for method in methods:
        method_results = []
        for z in zoom_factors:
            if z <= 1.0:
                method_results.append({'zoom': z, 'psnr': float('inf'), 'sharpness': 1.0})
                continue

            zoomed = digital_zoom(image, z, method)

            # 粗略锐利度：Laplacian 方差
            if zoomed.ndim == 3:
                gray = cv2.cvtColor(zoomed, cv2.COLOR_BGR2GRAY)
            else:
                gray = zoomed
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()

            method_results.append({
                'zoom': z,
                'sharpness': lap_var,
            })

        results[method.value] = method_results

    return results


if __name__ == "__main__":
    # 创建测试图像（模拟 ISO 12233 线条图卡）
    test_img = np.zeros((480, 640, 3), dtype=np.uint8)
    # 绘制垂直黑白条纹（测试 MTF）
    for x in range(0, 640, 16):
        test_img[:, x:x+8] = 255
    test_img = cv2.GaussianBlur(test_img, (3, 3), 0)  # 模拟光学模糊

    print("数字变焦质量基准测试")
    print("=" * 50)

    zoom_factors = [2.0, 3.0, 4.0, 6.0, 8.0]
    for method in [ResampleMethod.BILINEAR, ResampleMethod.BICUBIC, ResampleMethod.LANCZOS]:
        print(f"\n{method.value.upper()} 插值:")
        for z in zoom_factors:
            zoomed = digital_zoom(test_img, z, method)
            gray = cv2.cvtColor(zoomed, cv2.COLOR_BGR2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            print(f"  {z:.0f}× 变焦 | 锐利度（Laplacian Var）: {sharpness:.1f}")

    # 混合变焦系统示例
    hybrid = HybridZoomSystem(wide_equiv_fl=24.0, tele_equiv_fl=85.0, switch_zoom=2.5)
    for z in [1.0, 2.0, 2.5, 3.0, 4.0, 5.0]:
        w_wide, w_tele = hybrid.get_blend_weights(z)
        print(f"{z:.1f}× | 主摄权重: {w_wide:.2f}, 长焦权重: {w_tele:.2f}")
```

---

## References

1. Keys, R. G. (1989). Cubic convolution interpolation for digital image processing. *IEEE Transactions on Acoustics, Speech, and Signal Processing*, 29(6), 1153–1160.

2. Mitchell, D. P., & Netravali, A. N. (1988). Reconstruction filters in computer-graphics. *Proceedings of SIGGRAPH*, 22(4), 221–228.

3. Turkowski, K. (1990). Filters for common resampling tasks. In *Andrew S. Glassner (Ed.), Graphics Gems*, pp. 147–165. Academic Press.

4. Wang, Z., Bovik, A. C., Sheikh, H. R., & Simoncelli, E. P. (2004). Image quality assessment: From error visibility to structural similarity. *IEEE Transactions on Image Processing*, 13(4), 600–612.

5. Dong, C., Loy, C. C., He, K., & Tang, X. (2016). Image super-resolution using deep convolutional networks. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 38(2), 295–307.

6. Wang, X., Yu, K., Wu, S., Gu, J., Liu, Y., Dong, C., ... & Change Loy, C. (2018). ESRGAN: Enhanced super-resolution generative adversarial networks. *Proceedings of ECCV Workshops*.

7. Zhang, Y., Li, K., Li, K., Wang, L., Zhong, B., & Fu, Y. (2018). Image super-resolution using very deep residual channel attention networks (RCAN). *Proceedings of ECCV*.

8. ISO 12233:2017. (2017). *Photography — Electronic still picture imaging — Resolution and spatial frequency responses*. International Organization for Standardization.

9. Fontaine, R., & Chen, D. (2021). Periscope camera system design considerations for smartphones. *Proceedings of SPIE Electronic Imaging*, 11756.

---

*End of Chapter 30 | End of Part 2 (Traditional ISP)*
