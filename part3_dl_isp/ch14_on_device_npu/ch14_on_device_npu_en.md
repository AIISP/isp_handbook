# Part 3, Chapter 14: On-Device Neural ISP: NPU Deployment and Quantization

> **Scope:** This chapter focuses on the engineering practice of deploying DL ISP models to mobile NPUs, covering INT8 quantization, operator fusion, and memory optimization. For the overall on-device inference framework see Volume 5, Chapter 13.
> **Prerequisites:** Volume 3, Chapter 1 (DL ISP Overview); Volume 3, Chapter 2 (End-to-End Image Restoration)
> **Target Readers:** Embedded engineers, algorithm engineers

---

## §1 Theory

### 1.1 Motivation and Challenges of On-Device Deployment

Deep learning ISP (DL-ISP) already surpasses traditional ISP in image quality, but deploying it to the Neural Processing Unit (NPU, 神经网络处理单元) of a mobile SoC faces three fundamental constraints:

**Compute constraint:** The peak throughput of mainstream mobile NPUs (e.g., Qualcomm Hexagon, Huawei Ascend, MediaTek APU, Samsung NPU) spans a wide range — mid/low-range SoCs deliver approximately 4–15 TOPS (INT8), while 2023–2024 flagship SoCs reach 34–49 TOPS (Snapdragon 8 Gen3: ~34 TOPS, third-party est.; Dimensity 9300: 33 TOPS) — far below the hundreds of TOPS of a data-center GPU. Inference of a UNet-style network at FP32 precision on a single 12 MP RAW frame often requires hundreds of GFLOPs, exceeding the real-time processing budget.

**Memory bandwidth constraint:** Mobile LPDDR5-6400 dual-channel bandwidth is approximately 102 GB/s (lower-speed LPDDR5 variants start from ~60 GB/s), and frequent reads and writes of feature maps easily become a bottleneck. On the NPU, on-chip SRAM (Static Random-Access Memory) is typically only a few MB; large intermediate feature maps must be repeatedly transferred to DRAM, creating a severe memory wall (内存墙) problem.

**Power constraint:** The Thermal Design Power (TDP, 热设计功率) of a smartphone limits sustained inference power consumption to typically 1–3 W. Exceeding this threshold triggers thermal throttling (热节流), causing a sudden drop in performance.

### 1.2 Mathematical Foundations of Quantization

Quantization (量化) is the process of mapping floating-point numbers to low-precision integers. The most common form is Uniform Affine Quantization (均匀仿射量化):

$$
x_q = \text{clip}\!\left(\left\lfloor \frac{x}{s} \right\rceil + z,\; q_{\min},\; q_{\max}\right)
$$

where $s$ is the scale factor (缩放因子), $z$ is the zero point (零点), and $\lfloor \cdot \rceil$ denotes rounding. Dequantization (反量化) is:

$$
\hat{x} = s \cdot (x_q - z)
$$

For INT8 quantization, $q_{\min}=-128,\; q_{\max}=127$ (signed). Quantization error mainly comes from rounding error (舍入误差) and clipping error (截断误差).

**Per-tensor quantization (逐张量量化)** uses a single $(s, z)$ pair for an entire layer's weights; low computational overhead but large accuracy loss. **Per-channel quantization (逐通道量化)** uses independent $(s_c, z_c)$ for each output channel; higher accuracy and the mainstream choice for deploying convolutional layers. The accuracy difference between the two schemes can reach 0.2–0.5 dB PSNR on ISP tasks.

### 1.3 Principles of Quantization-Aware Training (QAT)

Post-Training Quantization (PTQ, 训练后量化) is sensitive to activation distribution shifts due to lack of gradient feedback; accuracy loss in ISP tasks can reach 0.5–2 dB PSNR. Quantization-Aware Training (QAT, 量化感知训练) inserts fake-quantize nodes (伪量化节点) during forward propagation to simulate quantization error, and uses the Straight-Through Estimator (STE, 直通估计器) to bypass the non-differentiable rounding operation for gradient propagation:

$$
\frac{\partial \mathcal{L}}{\partial x} \approx \frac{\partial \mathcal{L}}{\partial x_q} \cdot \mathbf{1}\!\left[q_{\min} \le \frac{x}{s} \le q_{\max}\right]
$$

After QAT fine-tuning, model weights adaptively adjust to reduce quantization noise. Typically only 5–10% of the full-training iteration count is needed to restore accuracy to within 0.1–0.2 dB of the FP32 model.

### 1.4 NPU Execution Model

Mainstream NPUs use a Systolic Array (脉动阵列) to execute Multiply-Accumulate (MAC, 乘加运算) operations. Taking the Qualcomm Hexagon architecture as an example, its Hexagon Vector eXtensions (HVX) and Hexagon Tensor Processor (HTP) handle vector convolution and matrix multiplication respectively. The HTP natively supports INT4, INT8, INT16, and FP16 precision types; FP32 computation falls back to the CPU on most Hexagon generations. The NPU scheduler partitions the network graph into operator subgraphs, loads them sequentially to on-chip SRAM, and executes them; data is transferred between the NPU and DRAM via a DMA controller.

The key to understanding the NPU execution model is the **Supported Operator List (算子支持列表):** not all PyTorch operators can execute natively on the NPU. Unsupported operators fall back to CPU execution (CPU Fallback), incurring severe data transfer overhead. A single CPU Fallback typically introduces data transfer latency more than 10× the operator's own execution time.

---

## §2 Algorithms

### 2.1 Lightweight Network Architecture Design

#### 2.1.1 Depthwise Separable Convolution

The Inverted Residual Block (倒置残差块) and Linear Bottleneck (线性瓶颈) introduced by MobileNetV2 (Sandler et al., CVPR 2018) became the foundation for lightweight ISP backbones. The FLOPs of a standard $k \times k$ convolution are $k^2 \cdot C_{in} \cdot C_{out} \cdot H \cdot W$, while Depthwise Separable Convolution (DW-Conv, 深度可分离卷积) decomposes it into a depthwise convolution ($k^2 \cdot C_{in} \cdot H \cdot W$) and a pointwise convolution ($C_{in} \cdot C_{out} \cdot H \cdot W$), with a theoretical speedup of $k^2 / (1 + 1/C_{out})$, approximately 8–9× for $3\times 3$ convolutions.

MobileNetV3 (Howard et al., ICCV 2019) further introduces lightweight channel attention based on hard-Sigmoid (h-sigmoid) — a Squeeze-and-Excitation (SE, 压缩激励) module variant — and hard-Swish (h-swish) activation, surpassing V2 by approximately 3.2% Top-1 accuracy on ImageNet at the same computational cost. For ISP denoising tasks, MobileNetV3-backbone networks reduce latency approximately 4× compared to standard UNet.

#### 2.1.2 Neural Architecture Search for ISP

The MAI Image Signal Processing Pipeline Challenge (CVPR Workshops 2021), proposed by Ignatov et al., drove Neural Architecture Search for ISP (ISP-NAS, 面向ISP的神经架构搜索) targeting mobile NPUs. The main approach constrains the following three conditions in the search space:

1. **FLOPs budget:** Limited to within 100 GFLOPs for 12 MP images.
2. **Operator types:** Use only NPU-natively-supported operators (Conv2D, DW-Conv, Add, Concat, ReLU, etc.), avoiding CPU Fallback.
3. **Feature map resolution strategy:** For high-resolution inputs, use a spatial downsampling (pixel-unshuffle or strided convolution) + upsampling (bilinear or pixel-shuffle) encoder-decoder structure, keeping full-resolution operation within 20% of total FLOPs.

The optimal architectures found by search typically exhibit a "wide and shallow" structure — more channels but fewer layers — which aligns with the NPU's strength in batch matrix operations.

#### 2.1.3 Engineering Practice: OPPO MariSilicon X

OPPO MariSilicon X (released 2022) is a dedicated AI ISP chip designed for mobile photography, with peak throughput of 18 TOPS (OPPO official) and 58 MB on-chip SRAM. Key strategies in its deployment approach include:

- **Tiling (分块处理):** Partition RAW input into overlapping small tiles to fit on-chip memory; overlap width is determined by the network receptive field.
- **Pipeline Parallelism (流水线并行):** Sub-networks for denoising, demosaicing, and color correction execute in a pipelined-parallel manner within the chip, reducing end-to-end latency.
- **Full INT8 inference:** Weights and activations are both quantized to INT8, saving 50% bandwidth compared to FP16 and 75% compared to FP32 — key to achieving real-time 12 MP processing.

### 2.2 INT8 Quantization Workflow

#### 2.2.1 End-to-End Quantization with TFLite

Google TensorFlow Lite (TFLite) provides a complete end-to-end quantization toolchain:

```
FP32 PyTorch model
    → ONNX export (opset 13)
    → TFLite conversion (TFLiteConverter)
    → PTQ (calibration dataset, recommended 100–500 samples)
      or QAT (fake-quantize node fine-tuning)
    → .tflite model (INT8 weights + INT8 activations)
    → Deploy to Android NNAPI / mobile NPU driver
```

The calibration dataset typically takes 100–500 RAW samples from the target scene to collect per-layer activation distributions, enabling determination of optimal $(s, z)$.

#### 2.2.2 Mixed-Precision Quantization

Not all layers are equally sensitive to quantization. In ISP networks, shallow layers (convolutional layers near the RAW input) and output layers are most sensitive to quantization noise, because quantization errors accumulate and amplify through subsequent layers.

The HAWQ (Dong et al., ICCV 2019; HAWQ-V2, NeurIPS 2020) framework uses the trace of the Hessian matrix to measure each layer's sensitivity to quantization error:

$$
\text{sensitivity}(l) = \text{tr}\!\left(\mathbf{H}_l\right)
$$

A larger Hessian trace means the layer is more sensitive to parameter perturbation and should be assigned a higher bit-width. The auto-assigned result typically is: INT8 for input/output layers, INT4 for intermediate bottleneck layers; average bit-width drops to 5–6 bits, latency further decreases 15–20% compared to full INT8, with essentially unchanged accuracy.

### 2.3 Operator Fusion Optimization

Operator Fusion (算子融合) merges multiple consecutive operators into a single NPU kernel, eliminating DRAM reads and writes of intermediate feature maps. It is one of the highest-return optimization techniques in NPU optimization:

- **Conv-BN-ReLU fusion:** Fold the Batch Normalization (BN, 批归一化) scaling parameters $\gamma, \beta$ into the convolution weights $W$ and bias $b$:
  $$W' = \frac{\gamma}{\sqrt{\sigma^2 + \epsilon}} W, \quad b' = \gamma\frac{b - \mu}{\sqrt{\sigma^2 + \epsilon}} + \beta$$
  Then merge with ReLU into a single instruction.
- **Add-ReLU fusion:** Merge the residual addition with the subsequent activation, saving one feature map write-back.
- **Conv-Concat fusion:** When a $1\times 1$ convolution immediately follows channel-dimension concatenation, this is equivalent to parallel grouped convolutions, which can be merged into a grouped convolution (组卷积) to reduce scheduling overhead.

In practice, operator fusion can reduce NPU latency of a typical ISP UNet structure by approximately 25–35%.

### 2.4 Memory Optimization Strategies

#### 2.4.1 Feature Map Lifetime Analysis

In encoder-decoder networks (U-Net-style structures), encoder feature maps must be retained until the corresponding decoder layer uses them. Through carefully designed Liveness Analysis (生命周期分析), non-overlapping feature maps can be allocated to the same memory region (memory reuse), reducing Peak Memory Footprint (峰值内存占用) by 30–50%.

#### 2.4.2 Tiled Inference (分块推理)

For high-resolution inputs (e.g., 12 MP = $4000\times 3000$), partition the image into overlapping tiles (recommended $512\times 512$, overlap = $2\times$ receptive field pixels) for separate inference, then stitch the results. The overlap region is used to eliminate Tile Boundary Artifacts (块边界伪影). Tiled inference reduces peak memory from $O(H \cdot W)$ to $O(T^2)$, where $T$ is the tile size, typically reducing memory footprint by 8–16×.

---

## §3 Tuning Guide

### 3.1 Quantization Accuracy Preservation Strategies

| Tuning Item | Recommended Setting | Notes |
|-------------|--------------------|----|
| Quantization scheme | QAT preferred over PTQ | ISP tasks: QAT can keep PSNR loss within 0.2 dB |
| QAT learning rate | 1/10 of FP32 training LR | Avoid over-adjusting and disrupting converged weights |
| QAT iteration count | 5–10% of total training | Typically 5,000–20,000 steps are sufficient |
| Shallow-layer quantization | INT8 per-channel | Layers 1–3 most sensitive; per-tensor not recommended |
| Activation range statistics | EMA (Exponential Moving Average) | More robust than min-max; avoids outlier influence on range estimation |
| BN folding timing | Complete before QAT starts | Eliminates BN state inconsistency between training and inference |
| Output layer precision | INT8 or INT16 | Output layer quantization error directly affects final image quality |

### 3.2 NPU-Friendly Network Design Principles

The following principles should be followed at the network design stage to maximize NPU utilization:

- **Channel counts as multiples of 8 or 16:** Most NPU vector widths are 8 or 16; aligned channel counts avoid padding waste of compute.
- **Avoid dynamic shapes:** NPUs typically require static input sizes; dynamic shapes trigger CPU-side shape inference, introducing additional latency.
- **Minimize Gather/Scatter-type operators:** Irregular memory access is poorly supported on NPUs; replace with equivalent convolution implementations.
- **Use ReLU6 instead of Sigmoid/Tanh:** The latter are typically implemented via lookup table on NPUs with greater precision loss and slower speed.
- **Control skip connection span:** Long skip connections require long-lived intermediate feature maps consuming on-chip SRAM; recommended span not more than 4 layers.

### 3.3 Latency Analysis and Bottleneck Identification

Use Snapdragon Profiler (Qualcomm), Rockchip NPU SDK Profiler, or Huawei HiAI Foundation's performance analysis tools to analyze the following metrics layer by layer:

1. **Operator execution time:** Find the top-10 most time-consuming operators; check specifically for unexpected CPU Fallbacks.
2. **Memory bandwidth utilization:** If close to the theoretical peak (> 90%), bandwidth is already the bottleneck; optimize feature map sizes or introduce more aggressive downsampling.
3. **NPU utilization:** If below 60%, scheduling overhead or data transfer is typically the main bottleneck; optimize operator fusion.

---

## §4 Artifacts

### 4.1 Quantization Color Shift (量化色彩偏移)

**Symptom:** After INT8 quantization deployment, the image exhibits an obvious overall tonal shift — warm (orange cast) or cool (blue-green cast). Macbeth ColorChecker test $\Delta E_{00}$ degrades > 2 units. The deviation is most pronounced on AWB-calibrated neutral color patches (gray, white), reaching 3–5 $\Delta E_{00}$ units.

**Root cause:** The dynamic range of CCM (color correction matrix) layer weights in ISP networks is significantly larger than other layers (mixed positive/negative values, range up to $[-3, +3]$), while the step size $\Delta = (W_{\max} - W_{\min}) / 255$ of standard per-tensor INT8 quantization is approximately 0.024. For small weights in the range $[-0.1, +0.1]$, precision is severely insufficient (quantization error / weight value > 20%), causing the relative gains in R/G/B channels after the color matrix transform to deviate from FP32 reference values. Quantization error in Gamma/TMO nonlinear layers is further amplified by the curve slope in highlight regions ($I > 0.7$).

**Diagnosis:** Pass a standard Macbeth ColorChecker (24-patch) image through both the FP32 model and the INT8 quantized model; compute $\Delta E_{00}$ for each patch. If $\Delta E_{00}$ > 2 for gray patches ($L^* \in [20, 90]$, $|a^*| < 2$, $|b^*| < 2$), quantization color shift is present. Further inspect the weight distribution histogram of the CCM layer; if per-tensor quantization step size > 0.02, confirm as insufficient CCM precision.

**Mitigation strategies:**
- Retain FP16 or INT16 precision exclusively for CCM and AWB gain matrix layers (mixed-precision quantization, 混合精度量化); use INT8 for remaining convolutional layers.
- Use per-channel quantization instead of per-tensor quantization: independently calibrate quantization parameters for each output channel, eliminating inter-channel dynamic range differences.
- During QAT, add L2 regularization to CCM weights ($\lambda = 1\text{e-}4$), compressing dynamic range to $[-1.5, +1.5]$; this reduces the INT8 quantization step size by approximately 2×, bringing precision error below 5%.

### 4.2 INT8 Overflow Blocking (INT8溢出块状色块)

**Symptom:** After quantization, randomly distributed 8×8 or 16×16 pixel block-shaped color anomalies appear in the image — some blocks are pure white (values clipped to 255) or pure black (values clipped to 0), or appear as solid-color patches completely different in hue from their surroundings. Triggered most frequently in high-brightness regions (highlights) and very low-brightness regions (shadows).

**Root cause:** When the dynamic range of an intermediate activation layer exceeds the INT8 calibration range (the clipping range of $[-128, 127]$), overflow values are clamped to boundary values and propagate to subsequent layers as erroneous "saturated" activations. Typical trigger path: in a ResNet block, if the output distribution of the residual branch has heavy tails (e.g., activations occasionally > $3\sigma$), per-tensor calibration selects a clip range using the 99th percentile. Extreme inputs (strong light edges, high-contrast text) cause activations to exceed the clip range, producing truncation.

**Diagnosis:** Enable activation overflow checking during NPU inference (e.g., Qualcomm SNPE's `--validate_data_tensors`); record per-layer activation overflow rates. If a layer's overflow rate > 0.1%, that layer is the source of block artifacts. Visualize with a difference map (INT8 output − FP32 output); if the difference map shows locally large abnormal blocks, use overflow logs to identify the specific layer.

**Mitigation strategies:**
- Use a more permissive clip range during calibration (e.g., 99.9th percentile instead of 99th) to reduce extreme-value truncation, at the cost of slightly lower quantization precision for non-extreme values.
- For activation layers with high overflow rates, retain FP16, or introduce activation range constraints in QAT (GELU/ReLU6 and other bounded activations), fixing the activation range to a bounded interval.
- Add activation normalization at residual connections to prevent continual amplitude growth from residual accumulation.

### 4.3 Quantization Accuracy Degradation (量化精度降级)

**Symptom:** After quantizing from FP32 to INT8 for deployment, PSNR drops > 1 dB and SSIM drops > 0.02, exceeding engineering acceptance criteria (typically requiring PSNR loss ≤ 0.3 dB). Quality degradation is especially pronounced in fine-texture regions (fabric, leaves) and edge regions (text edges), manifesting as texture smearing or edge ringing.

**Root cause:** INT8 quantization (8-bit integer, 256 quantization levels) has a precision loss of approximately $10^{-4}$ magnitude relative to FP32 (7 significant digits), but in deep feature layers of ISP networks, quantization errors accumulate linearly through multi-layer MAC operations. Theoretical analysis shows that error accumulation across $L$ layers of fully-connected/convolutional operations is approximately $\sqrt{L}$ times the single-layer error (assuming independent errors). For networks with BN (Batch Normalization) layers, the BN scaling coefficient $\gamma$ can reach 5–10, amplifying quantization error by the same factor. The pointwise step of Depthwise Separable Conv is especially sensitive (each channel has few weights; quantization step is coarse relative to the weight distribution).

**Diagnosis:** Record per-layer activation differences between FP32 and INT8 inference (Cosine Similarity); identify layers where Cosine Similarity < 0.99 as the primary sources of accuracy degradation. Switch these layers to FP16 and re-test PSNR; if PSNR recovers to within ±0.1 dB of FP32, confirm that layer as the precision bottleneck. Mark layers with BN $\gamma > 3$ as "high-gain layers" for priority protection.

**Mitigation strategies:**
- Quantization-Aware Training (QAT): after FP32 training converges, insert "fake quantization" nodes to introduce quantization error in the forward pass; backpropagation adapts the network to quantization noise (typically fine-tune for 3–5 epochs).
- Quantize after BN folding: absorb BN parameters into the preceding convolutional layer weights ($W' = \gamma/\sqrt{\sigma^2+\epsilon} \cdot W$), eliminating the amplification effect of independent BN layers.
- When channel-alignment padding (NPU requires channel counts as multiples of 16) adds zero channels, set the corresponding output weights to zero (mask), shielding zero-point offset errors introduced by padding channels.

### 4.4 Artifact Reference Table

| Artifact Type | Trigger Condition | Typical Symptom | Mitigation |
|--------------|------------------|----------------|------------|
| Quantization Color Shift (色彩偏移) | CCM layer per-tensor INT8 insufficient precision | Overall warm/cool tonal shift, $\Delta E_{00}$ > 2 | CCM layer FP16, per-channel quantization, QAT regularization |
| Overflow Blocking (块状色块) | Activation exceeds clip range and is truncated | 8×8 or 16×16 pixel blocks of pure white or abnormal color | Wider clip range (99.9%), activation range constraints, FP16 protection layers |
| Accuracy Degradation (精度降级) | BN amplifies quantization error, multi-layer accumulation | PSNR drops > 1 dB, texture smearing, edge ringing | QAT fine-tuning, BN-folding, channel padding mask |
| Tiling Artifact (分块边界伪影) | Global normalization, insufficient overlap | Regular grid-like brightness/color discontinuity | Overlap ≥ 1.5× receptive field, cosine window blending, remove global BN |
| Throttling Jitter (热节流帧率波动) | NPU sustained at full load, temperature limiting | First few frames normal latency, subsequent sudden 2× increase | Reserve 30% compute headroom, low-power scheduling mode |

---

## §5 Evaluation

### 5.1 Latency Benchmarking Protocol

On-device latency evaluation must be performed on the target device; PC simulation cannot substitute. Standard test procedure:

1. **Warm-up (热机预热):** Run 50 consecutive inferences before timing starts, to avoid JIT (Just-In-Time Compilation) cache cold-start overhead.
2. **Multiple runs, take median:** Run inference 100 times; take P50 latency; P95 is used to evaluate frame rate stability jitter.
3. **Frequency locking:** Use `adb shell` to lock CPU/GPU/NPU frequency, eliminating DVFS (Dynamic Voltage and Frequency Scaling, 动态电压频率调整) effects.
4. **End-to-end latency:** Total time including memory allocation, data transfer (Host→NPU→Host), and operator execution — not just operator execution time alone.

### 5.2 Image Quality Assessment Benchmarks

Quantized image quality must be comprehensively evaluated on standard datasets:

| Metric | Tool / Dataset | Target Threshold |
|--------|---------------|-----------------|
| PSNR | MIT-Adobe FiveK, SIDD | Quantization-induced loss ≤ 0.3 dB |
| SSIM | Same as above | Quantization-induced loss ≤ 0.005 |
| $\Delta E_{00}$ | Macbeth ColorChecker chart | ≤ 0.5 color difference units |
| Noise Power Spectrum (NPS) | ISO 15739 standard | Difference before/after quantization ≤ 5% |
| Edge MTF | ISO 12233 resolution chart | MTF50 difference before/after quantization ≤ 2% |

### 5.3 Power Consumption Testing

Use a Monsoon power monitor (external precision ammeter) or chip-internal power sensors (Android `BatteryStats` / `PowerManager`), recording:

- **Average power consumption:** Average over 1 minute of continuous inference, for evaluating battery life impact.
- **Peak power consumption:** Maximum instantaneous power, for evaluating thermal throttling risk.
- **Performance per Watt (能效比):** Measured as PSNR gain (improvement relative to traditional ISP) divided by power consumption (mW).

---

## §6 Code Implementation

### 6.1 Lightweight ISP Network (PyTorch)

```python
import torch
import torch.nn as nn


class DepthwiseSeparableConv(nn.Module):
    """Depthwise separable convolution block, NPU-friendly design: channel alignment, ReLU6 activation"""
    def __init__(self, in_ch, out_ch, stride=1):
        super().__init__()
        # Align channel count to multiples of 8 to satisfy NPU vector width requirement
        out_ch = ((out_ch + 7) // 8) * 8
        self.dw = nn.Conv2d(in_ch, in_ch, 3, stride=stride,
                            padding=1, groups=in_ch, bias=False)
        self.pw = nn.Conv2d(in_ch, out_ch, 1, bias=False)
        self.bn = nn.BatchNorm2d(out_ch)
        self.act = nn.ReLU6(inplace=True)   # NPU-friendly activation; avoids Sigmoid/Tanh

    def forward(self, x):
        return self.act(self.bn(self.pw(self.dw(x))))


class LightweightISPNet(nn.Module):
    """
    Lightweight ISP network designed for NPU deployment.
    Input: (B, 4, H, W) RGGB-format RAW (after pixel-unshuffle)
    Output: (B, 3, H, W) sRGB image
    """
    def __init__(self, in_ch=4, out_ch=3, base_ch=32):
        super().__init__()
        # Encoder: stride convolutions reduce resolution, minimizing full-resolution operator count
        self.enc1 = DepthwiseSeparableConv(in_ch, base_ch)
        self.enc2 = DepthwiseSeparableConv(base_ch, base_ch * 2, stride=2)
        self.enc3 = DepthwiseSeparableConv(base_ch * 2, base_ch * 4, stride=2)
        # Bottleneck layers (all executed at 1/4 resolution; minimal compute cost)
        self.bottleneck = nn.Sequential(
            DepthwiseSeparableConv(base_ch * 4, base_ch * 4),
            DepthwiseSeparableConv(base_ch * 4, base_ch * 4),
        )
        # Decoder: bilinear upsampling (avoids checkerboard artifacts of transposed conv
        # and NPU incompatibility issues)
        self.up2 = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False)
        self.dec2 = DepthwiseSeparableConv(base_ch * 4 + base_ch * 2, base_ch * 2)
        self.up1 = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False)
        self.dec1 = DepthwiseSeparableConv(base_ch * 2 + base_ch, base_ch)
        self.out_conv = nn.Conv2d(base_ch, out_ch, 1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)
        b  = self.bottleneck(e3)
        d2 = self.dec2(torch.cat([self.up2(b), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return torch.sigmoid(self.out_conv(d1))
```

### 6.2 QAT Quantization-Aware Training

```python
import torch.ao.quantization as tq  # torch.quantization deprecated since PyTorch 2.0


def prepare_qat_model(model: nn.Module) -> nn.Module:
    """
    Prepare QAT model: fuse BN and insert fake-quantize nodes.
    Note: must be called after the model has converged, typically after FP32 training completes.
    """
    model.train()
    # Step 1: Fold Conv-BN (must be done before inserting fake-quantize nodes)
    model = tq.fuse_modules(model, [
        ['enc1.pw', 'enc1.bn', 'enc1.act'],   # PW-Conv + BN + ReLU6 (valid Conv-BN-ReLU pattern)
        ['enc2.pw', 'enc2.bn', 'enc2.act'],   # DW-Conv layers have no separate BN in this arch
        ['enc3.pw', 'enc3.bn', 'enc3.act'],
    ], inplace=True)
    # Step 2: Configure quantization scheme: weights per-channel, activations per-tensor (EMA statistics)
    model.qconfig = tq.QConfig(
        activation=tq.default_fake_quant,
        weight=tq.default_per_channel_weight_fake_quant
    )
    # Step 3: Insert fake-quantize nodes
    tq.prepare_qat(model, inplace=True)
    return model


def qat_train(model, train_loader, val_loader, epochs=5, lr=1e-4):
    """QAT fine-tuning training loop"""
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.L1Loss()
    model = prepare_qat_model(model)

    for epoch in range(epochs):
        model.train()
        for raw, gt in train_loader:
            optimizer.zero_grad()
            pred = model(raw)
            loss = criterion(pred, gt)
            loss.backward()
            # Gradient clipping: gradients can be unstable in early QAT stages
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

        # Validation phase: disable fake-quantize statistics update; inference only
        model.eval()
        with torch.no_grad():
            val_psnrs = []
            for raw, gt in val_loader:
                pred = model(raw)
                mse = torch.mean((pred - gt) ** 2).item()
                val_psnrs.append(-10 * torch.log10(torch.tensor(mse)).item())
            print(f"Epoch {epoch+1}/{epochs}, Val PSNR: {sum(val_psnrs)/len(val_psnrs):.2f} dB")

    return model


def export_int8_tflite(model: nn.Module, save_path: str):
    """Export INT8 inference model as ONNX (can subsequently convert to TFLite or SNPE format)"""
    model.eval()
    # Freeze BN statistics (must be called after QAT training completes)
    model.apply(torch.nn.intrinsic.qat.freeze_bn_stats)
    int8_model = tq.convert(model.eval(), inplace=False)
    dummy_input = torch.zeros(1, 4, 512, 512)
    torch.onnx.export(
        int8_model, dummy_input, save_path,
        opset_version=13,
        input_names=['raw_rggb'],
        output_names=['rgb_output'],
        dynamic_axes={'raw_rggb': {2: 'height', 3: 'width'}}
    )
    print(f"INT8 ONNX model exported to {save_path}")
```

### 6.3 Tiled Inference with Cosine Window Blending

```python
import numpy as np


def cosine_window_2d(h: int, w: int) -> np.ndarray:
    """Generate 2D cosine window for smooth tile boundary blending"""
    wy = np.hanning(h + 2)[1:-1].reshape(-1, 1)
    wx = np.hanning(w + 2)[1:-1].reshape(1, -1)
    return (wy * wx)[..., np.newaxis]   # (h, w, 1)


def tiled_inference(model, raw_image: np.ndarray,
                    tile_size: int = 512, overlap: int = 64,
                    device: str = 'cpu') -> np.ndarray:
    """
    Tiled inference: supports NPU inference for arbitrary-resolution RAW images.
    raw_image: shape (H, W, 4), dtype float32, RGGB channel order
    returns: shape (H, W, 3), dtype float32, sRGB output
    """
    H, W, C = raw_image.shape
    output    = np.zeros((H, W, 3), dtype=np.float32)
    weight_map = np.zeros((H, W, 1), dtype=np.float32)
    step = tile_size - overlap

    model.eval()
    with torch.no_grad():
        for y in range(0, H, step):
            for x in range(0, W, step):
                y_end = min(y + tile_size, H)
                x_end = min(x + tile_size, W)
                tile  = raw_image[y:y_end, x:x_end]   # (th, tw, 4)
                th, tw = tile.shape[:2]

                # Zero-pad to tile_size (NPU requires static shape)
                pad_h = tile_size - th
                pad_w = tile_size - tw
                tile_pad = np.pad(tile, ((0, pad_h), (0, pad_w), (0, 0)))

                # Inference
                inp = (torch.from_numpy(tile_pad)
                       .permute(2, 0, 1).unsqueeze(0).float().to(device))
                out = model(inp).squeeze(0).permute(1, 2, 0).cpu().numpy()

                # Crop to original tile size and blend with weights
                out_crop = out[:th, :tw]
                window = cosine_window_2d(th, tw)
                output[y:y_end, x:x_end]     += out_crop * window
                weight_map[y:y_end, x:x_end] += window

    return np.clip(output / (weight_map + 1e-8), 0.0, 1.0)
```

### 6.4 Latency and Peak Memory Profiling

```python
import time
import torch


def profile_latency(model: nn.Module,
                    input_shape=(1, 4, 512, 512),
                    warmup: int = 50, repeat: int = 100,
                    device: str = 'cpu') -> dict:
    """
    Model latency benchmark (following §5.1 specification: warm-up → lock frequency → median statistics)
    """
    model.eval().to(device)
    dummy = torch.randn(*input_shape).to(device)

    # Warm-up
    with torch.no_grad():
        for _ in range(warmup):
            _ = model(dummy)

    # Formal timing
    latencies = []
    with torch.no_grad():
        for _ in range(repeat):
            if device == 'cuda':
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            _ = model(dummy)
            if device == 'cuda':
                torch.cuda.synchronize()
            latencies.append((time.perf_counter() - t0) * 1000)   # ms

    latencies.sort()
    result = {
        'p50_ms': latencies[repeat // 2],
        'p95_ms': latencies[int(repeat * 0.95)],
        'min_ms': latencies[0],
    }
    print(f"P50: {result['p50_ms']:.2f} ms | P95: {result['p95_ms']:.2f} ms")
    return result


def profile_memory(model: nn.Module, input_shape=(1, 4, 512, 512)) -> int:
    """Compute model peak memory footprint (CPU-side estimate)"""
    total = sum(p.numel() * p.element_size() for p in model.parameters())
    # Estimate activation memory: approximately 4× input tensor size (empirical for encoder-decoder)
    input_bytes = 1
    for s in input_shape:
        input_bytes *= s
    input_bytes *= 4   # float32
    estimated_activation = input_bytes * 4
    print(f"Weight memory: {total/1e6:.2f} MB | Activation estimate: {estimated_activation/1e6:.2f} MB")
    return total + estimated_activation

# ─── Example call and output ───────────────────────────────────────
# Model forward inference example (RAW pack input: 4-channel RGGB → RGB output)
model = LightweightISPNet()
x = torch.randn(1, 4, 256, 256)
out = model(x)
print(out.shape)
# Output: torch.Size([1, 3, 256, 256])

```

---

---

## §7 HiSilicon Kirin NPU for ISP Deployment

### 7.1 Architecture Overview

The ISP NPU embedded in Huawei's Kirin SoCs differs substantially from Qualcomm's Hexagon and MediaTek's APU in design philosophy. Rather than maximizing general-purpose matrix-multiply throughput, the Kirin NPU is tightly coupled with the ISP hardware pipeline, prioritizing low-latency RAW-domain data transfer over raw TOPS numbers.

**Key architectural characteristics:**
- Kirin 9000/9010 (Kirin 9000s) uses the Da Vinci architecture with a Big+Tiny dual-core NPU cluster.
- The NPU connects to the ISP hardware via a dedicated DMA channel, allowing RAW-domain data to bypass DDR round-trips — in contrast to Qualcomm Hexagon's memory-copy model.
- Inference framework: HiAI Foundation (newer) / HiAI DDK (legacy). Models are distributed in `.om` format (Huawei-proprietary; broadly analogous to ONNX but not interchangeable).

### 7.2 Operator Support Constraints (Engineering-Critical)

| Operator | Support Status | Recommended Workaround |
|----------|---------------|----------------------|
| Deformable Conv | Not supported (as of HiAI 6.0) | Replace with standard 3×3 Conv + spatial attention approximation |
| PixelShuffle (large scale) | Severe performance drop at 4× and above | Split into two sequential 2× stages |
| Dynamic Shape | Limited to pre-registered resolution slots | Compile separate fixed-resolution models |
| GroupNorm | Not supported | Replace with LayerNorm or BatchNorm |
| SiLU / GELU | Version-dependent; verify compatibility table | Substitute ReLU or LeakyReLU |

Networks such as Restormer and NAFNet commonly use deformable convolutions; these must be eliminated at the architecture design stage, not after `atc` compilation fails.

### 7.3 Quantization Toolchain

- HiAI Foundation supports W8A8 (INT8 weights + INT8 activations) quantization via the `hiai_model_builder` API.
- QAT integration requires: PyTorch → ONNX export → `.om` compilation via Huawei `atc` (Atlas Tensor Compiler) with quantization-aware compilation flags.
- Typical conversion chain: `PyTorch → ONNX → .om` (using `atc --framework=5`).

### 7.4 Platform Comparison: Qualcomm vs. MediaTek vs. HiSilicon

| Dimension | Qualcomm Hexagon HTP | MediaTek APU | HiSilicon NPU |
|-----------|---------------------|--------------|--------------|
| Custom operators | HVX intrinsics supported | C-Model operator extension | `.om` operator library; extension heavily restricted |
| ISP data path | Memory sharing via Spectra ISP | Memory sharing via MDLA | Direct DMA connection; lowest latency |
| Developer documentation | SNPE/QNN fully public | NeuroPilot SDK public | HiAI docs require registered developer account |
| Device availability | Global flagship mainstream | Domestic flagship mainstream | Huawei/Honor devices only |

> **Engineer's note:** The two most common deployment pitfalls on Kirin platforms are (1) deformable convolution is unsupported — avoid it at network design time; and (2) weak dynamic shape support requires pre-compiling multiple resolution variants and implementing resolution-switching logic in the HAL layer, since ISP scenarios switch between resolutions (e.g., 1080p preview vs. 4K capture).

*References:* Huawei Developer Community, HiAI DDK documentation; Kirin 990/9000 NPU architecture whitepapers (2020–2022); Huawei CVPR 2022 poster on ISP NPU optimization.

---

## References

[1] Sandler, M., Howard, A., Zhu, M., Zhmoginov, A., & Chen, L.-C. "MobileNetV2: Inverted Residuals and Linear Bottlenecks." CVPR 2018.
[2] Howard, A., Sandler, M., Chu, G., et al. "Searching for MobileNetV3." ICCV 2019.
[3] Dong, Z., Yao, Z., Gholami, A., Mahoney, M. W., & Keutzer, K. "HAWQ: Hessian AWare Quantization of Neural Networks with Mixed-Precision." ICCV 2019.
[4] Dong, Z., Yao, Z., Cai, Y., et al. "HAWQ-V2: Hessian Aware trace-Weighted Quantization of Neural Networks." NeurIPS 2020.
[5] Jacob, B., Kligys, S., Chen, B., et al. "Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference." CVPR 2018.
[6] Ignatov, A., Van Gool, L., & Timofte, R. "Replacing Mobile Camera ISP with a Single Deep Learning Model." CVPR Workshops 2020.
[7] Ignatov, A., et al. "Learned Smartphone ISP on Mobile NPUs with Deep Learning, Mobile AI 2021 Challenge: Report." CVPR Workshops 2021.
[8] Nagel, M., Fournarakis, M., Amjad, R. A., et al. "A White Paper on Neural Network Quantization." arXiv:2106.08295, 2021.
[9] OPPO Research Institute. "MariSilicon X: Redefining Mobile Photography with a Dedicated AI ISP." OPPO Technical Report, 2022.
[10] Krishnamoorthi, R. "Quantizing Deep Convolutional Networks for Efficient Inference: A Whitepaper." arXiv:1806.08342, 2018.

## §8 Glossary

| Abbreviation | Full Term | Brief Description |
|-------------|-----------|------------------|
| NPU | Neural Processing Unit (神经网络处理单元) | Mobile SoC module dedicated to deep learning inference |
| QAT | Quantization-Aware Training (量化感知训练) | Method of simulating quantization error during training to reduce accuracy loss |
| PTQ | Post-Training Quantization (训练后量化) | Fast quantization method without retraining; larger accuracy loss |
| STE | Straight-Through Estimator (直通估计器) | Gradient approximation trick to bypass non-differentiable rounding operations |
| TDP | Thermal Design Power (热设计功率) | Maximum heat dissipation power during sustained chip operation |
| DW-Conv | Depthwise Separable Convolution (深度可分离卷积) | Lightweight structure decomposing standard convolution into depthwise and pointwise steps |
| NAS | Neural Architecture Search (神经架构搜索) | Automated method for designing neural network structures |
| MAC | Multiply-Accumulate (乘加运算) | Basic compute unit of deep learning; count measures network computational cost |
| SRAM | Static Random-Access Memory (静态随机存储器) | On-chip high-speed cache; small capacity but fast speed |
| DRAM | Dynamic Random-Access Memory (动态随机存储器) | Mobile main memory (LPDDR series); large capacity but slower speed |
| DVFS | Dynamic Voltage and Frequency Scaling (动态电压频率调整) | Dynamically adjusts chip frequency based on load to balance performance and power |
| HVX | Hexagon Vector eXtensions (Hexagon向量扩展) | SIMD vector instruction set for Qualcomm Hexagon DSP |
| HTP | Hexagon Tensor Processor (Hexagon张量加速器) | Core of Qualcomm Hexagon NPU; responsible for matrix operation acceleration |
| ONNX | Open Neural Network Exchange (开放神经网络交换格式) | Cross-framework model exchange standard |
| TFLite | TensorFlow Lite | Google's lightweight inference framework for mobile devices |
| SNPE | Snapdragon Neural Processing Engine | Qualcomm inference SDK targeting the Snapdragon platform |
| SE | Squeeze-and-Excitation (压缩激励模块) | Channel attention-based feature enhancement mechanism |
| NPS | Noise Power Spectrum (噪声功率谱) | Objective metric measuring image noise frequency characteristics (ISO 15739) |
| MTF | Modulation Transfer Function (调制传递函数) | Standard metric measuring resolution of optical/imaging systems |
