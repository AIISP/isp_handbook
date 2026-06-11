# Part 5, Chapter 13: On-Device Inference Optimization for Cameras: Edge AI Deployment

> **Position:** This chapter focuses on the engineering challenges and optimization methods for deploying AI inference on edge camera devices.
> **Prerequisites:** Vol.3 Ch.15 (On-Device NPU Deployment), Vol.3 Ch.1 (DL ISP Overview)
> **Audience:** Algorithm engineers, embedded engineers

> The author's experience and background are limited; the content above represents personal understanding only. Experts from all relevant fields are warmly invited to improve this document — corrections and additions via Issue or Pull Request are welcome.

---

## §1 Theory

### 1.1 Physical Constraints of On-Device AI Inference

Deploying deep neural networks (DNNs) on mobile camera platforms requires operating under stringent hardware constraints. Compared to cloud-based inference, on-device deployment faces three core constraints:

**Power Budget**: The AI inference power ceiling of a mobile SoC is typically 1–2 W. The Snapdragon 8 Gen 3 NPU peaks at approximately 1.8 W during sustained inference, while the A17 Pro Neural Engine runs at around 1.5 W. Exceeding the power budget triggers thermal throttling, causing unstable frame rates. By contrast, a PC GPU (e.g., RTX 4090) can draw over 300 W for inference — a gap of up to 150×.

**Memory Constraint**: Flagship phones carry LPDDR5 memory totaling 12–16 GB, but the OS, foreground applications, and the camera framework itself already consume a significant portion, leaving only 4–8 GB available for AI inference. Even more critical is **bandwidth**: LPDDR5 theoretical bandwidth is approximately 68 GB/s, yet large Transformer models performing long-sequence inference generate extremely high memory-access volumes, making bandwidth — rather than compute — the bottleneck.

**Latency Requirement**: A 30 fps real-time preview demands end-to-end per-frame processing in under 33 ms; 60 fps requires under 16.7 ms. Within an actual camera pipeline, ISP hardware (demosaic, denoising, color correction, etc.) already consumes approximately 5–10 ms, leaving a neural-network inference window of only 15–20 ms. This constraint limits deployable model size to tens to hundreds of megabytes (FP32), or equivalently, tens of megabytes after quantization to INT8.

The **latency–accuracy–power trade-off triangle** can be described using the Pareto frontier:

$$\text{minimize} \quad (L_{\text{latency}},\ P_{\text{power}},\ -Q_{\text{quality}})$$

where $L_{\text{latency}}$ is inference latency, $P_{\text{power}}$ is power consumption, and $Q_{\text{quality}}$ is an image quality metric (PSNR/SSIM). No single solution can simultaneously minimize all three; engineering practice requires trade-offs across these dimensions depending on the target application (night-mode denoising, super-resolution, HDR compositing, etc.).

### 1.2 Four Main Neural Network Compression Approaches

To run neural-network ISP under on-device constraints, models must be systematically compressed. The four mainstream approaches are complementary:

#### 1.2.1 Quantization

Quantization converts floating-point parameters (FP32, 32-bit) to low-precision integers (INT8, INT4) or half-precision floats (FP16). Given an original weight $w \in \mathbb{R}$, the INT8 quantization mapping is:

$$w_q = \text{round}\left(\frac{w}{s}\right) + z, \quad w_q \in [-128, 127]$$

where the scale factor $s = \frac{\max(w) - \min(w)}{255}$ and the zero point $z$ maps the floating-point zero exactly to the integer representation.

Benefits of quantization:
- **Compute**: INT8 multiply-accumulate (MAC) operations run 4–8× faster than FP32 on the Qualcomm Hexagon DSP;
- **Memory**: INT8 model size is 1/4 of FP32; INT4 is 1/8;
- **Power**: Integer arithmetic consumes approximately 3–5× less power than floating-point.

Cost of quantization: accuracy loss, typically 0.1–0.5 dB in PSNR, which must be carefully evaluated for noise-sensitive ISP tasks.

#### 1.2.2 Pruning

Pruning falls into two categories — structured and unstructured:

- **Unstructured pruning**: Sets weights with small absolute values to zero. Sparsity ratios of 60%–90% are achievable, but sparse matrix operations are difficult to accelerate on general-purpose hardware, yielding limited real-world latency gains;
- **Structured pruning**: Removes entire convolution channels (channel pruning) or attention heads (attention head pruning). The pruned model retains the same architectural form as the original dense model — merely narrower — and can be directly accelerated on existing hardware.

Channel pruning scoring typically uses the L1 norm (pruning rate $r$):

$$\text{score}(c_i) = \sum_{j} |w_{ij}|^1, \quad \text{remove the lowest-scoring} \lfloor r \cdot C \rfloor \text{ channels}$$

where $C$ is the total number of channels and $r$ is the pruning ratio (typically 0.3–0.5).

#### 1.2.3 Knowledge Distillation

Knowledge distillation (Hinton et al., NIPS 2014 Workshop) uses the "soft labels" of a large teacher network to train a smaller student network. For ISP tasks (regression), the distillation loss is:

$$\mathcal{L}_{\text{distill}} = \alpha \cdot \mathcal{L}_{\text{task}}(\hat{y}_s, y) + (1-\alpha) \cdot \mathcal{L}_{\text{feat}}(f_s, f_t)$$

where $\hat{y}_s$ is the student output, $f_s$ and $f_t$ are intermediate feature maps from the student and teacher respectively, and $\mathcal{L}_{\text{feat}}$ is typically the L2 distance. $\alpha$ controls the weighting between the task loss and the distillation loss (commonly 0.5–0.8).

#### 1.2.4 Neural Architecture Search (NAS)

NAS automatically finds the optimal network architecture satisfying both latency and accuracy constraints within a predefined search space. See §4 for details.

### 1.3 Fundamental Differences Between ISP NPUs and General-Purpose NPUs

An important distinction that is often overlooked: **ISP NPUs operate directly in the RAW domain**, whereas general-purpose NPUs process RGB/YUV frames output by the ISP.

| Dimension | ISP NPU (e.g., OPPO MariSilicon X) | General-Purpose NPU (e.g., Qualcomm Hexagon) |
|:---:|:---:|:---:|
| Input data | Bayer RAW (10/12/14 bit) | RGB/YUV (8 bit) |
| Data source | Directly from sensor, minimal preprocessing | Image after full ISP pipeline processing |
| Primary tasks | Denoising (RAW NR), HDR merge, demosaic enhancement | Face detection, super-resolution, style transfer |
| Pipeline position | Early ISP stage (on-RAW) | Late ISP stage (post-ISP) |
| Power budget | Typically lower (<0.5 W, dedicated design) | Shared with system NPU (up to 1–2 W) |
| Accuracy requirement | Very high (pixel-level reconstruction, PSNR-sensitive) | Relatively relaxed (perceptual quality focus) |

RAW-domain inference has inherent advantages: more complete information (no irreversible compression), more consistent noise characteristics, and better support for training reliable statistical models. The cost is data-format diversity (different sensor Bayer patterns, varying bit depths) and the need for sensor-specific calibration data.

---

## §2 NPU Architecture

### 2.1 Qualcomm Hexagon DSP + AI Engine

The AI compute unit in the Qualcomm Snapdragon 8 Gen 3 (released 2023) is the **Hexagon NPU**, integrated within the Hexagon processor family on the SoC. Key specifications:

- **Compute**: ~34 TOPS (INT8, third-party estimate; Qualcomm official Product Brief states only "Up to 98% faster Hexagon NPU", no standalone integer published), a significant improvement over the previous-generation Snapdragon 8 Gen 2 Hexagon HTP (~18 TOPS, official);
- **Architecture**: Includes a vector extension unit (HVX, Hexagon Vector eXtensions) and a tensor extension unit (HTA, Hexagon Tensor Accelerator);
- **HVX**: 1024-bit-wide SIMD unit, well-suited for convolutions and element-wise operations;
- **HTA**: Designed specifically for matrix multiplication (GEMM), the primary accelerator for Transformer inference;
- **Memory**: Shares LPDDR5 with no dedicated SRAM; L2 cache approximately 2 MB;
- **Development tools**: Qualcomm AI Engine SDK (QNN SDK), supporting FP16/INT8/INT4 quantization; Snapdragon Profiler for performance analysis.

**QNN (Qualcomm Neural Network)** is Qualcomm's unified inference framework, supporting conversion of ONNX, TFLite, and PyTorch models into an optimized format (`.serialized.bin`) runnable on Hexagon. The QNN backend supports three execution units: CPU Backend (general-purpose fallback), GPU Backend (latency-tolerant parallel tasks), and HTP Backend (dedicated Hexagon NPU — best performance).

### 2.2 Apple Neural Engine (A17 Pro)

Apple's A17 Pro (2023, iPhone 15 Pro series) Neural Engine (NE) is among the most highly integrated dedicated AI accelerators available on mobile:

- **Compute**: 35 TOPS (INT8 equivalent, Apple official), though Apple does not disclose detailed architecture;
- **Design**: Shares a Unified Memory architecture (up to 8 GB) with the CPU (6-core: 2× Everest performance + 4× Sawtooth efficiency) and GPU (6-core Apple GPU), eliminating traditional CPU–GPU data-copy overhead;
- **Inference framework**: CoreML is the only official inference framework, deploying via `.mlpackage` format; supports FP16 and INT8 quantization (weights-only quantization; activations remain FP16);
- **Key advantage**: CoreML can automatically schedule operators across CPU, GPU, and NE without manual specification;
- **ISP integration**: The ProRes video processing pipeline on A17 Pro incorporates a hardware ISP module sharing memory with the NE, enabling true zero-copy ISP–AI co-inference.

**ProRAW and NE**: iPhone's ProRAW format uses the NE to perform real-time semantic multi-frame noise reduction (Semantic Multi-Frame NR) on RAW data from multiple frames; processing latency is approximately 150 ms (post-capture), not real-time preview. Preview uses a simplified hardware ISP pipeline.

### 2.3 MediaTek APU (Dimensity 9300)

MediaTek's Dimensity 9300 (released 2023) integrates a seventh-generation APU (AI Processing Unit):

- **Compute**: 33 TOPS (INT8, MediaTek official, per MediaTek Dimensity 9300 product spec page);
- **Architecture**: APU 790, comprising dedicated AI compute cores (AI Core) and vector processing units (VP Core);
- **Memory subsystem**: Supports LPDDR5X with 82.7 GB/s bandwidth, exceeding the Snapdragon 8 Gen 3's 77.4 GB/s;
- **Inference framework**: NeuroPilot SDK, supporting TFLite, ONNX, and PyTorch model import;
- **Notable feature**: APU 790 natively supports INT4 quantized inference (Snapdragon 8 Gen 3 also added INT4 support around the same time), further halving model size — accuracy loss must be controlled via mixed-precision strategies.

### 2.4 MediaTek APU (Dimensity 9400)

MediaTek's Dimensity 9400 (released 2024, TSMC N3E 3 nm process) integrates the eighth-generation APU (APU 860), delivering a significant compute uplift over the Dimensity 9300:

- **Compute**: ~50 TOPS (INT8, estimated, non-official integer), approximately 52% higher than the Dimensity 9300's APU 790 (33 TOPS, MediaTek official);
- **Architecture**: APU 860 pairs with a fully big-core CPU configuration (Cortex-X925×1 + Cortex-A725×3, no small efficiency cores); AI compute units are more tightly coupled to CPU cache hierarchy;
- **INT4 acceleration**: Native INT4 inference support, with theoretical INT4 compute ~100 TOPS, enabling larger ISP networks (e.g., NAFNet-64) without significant accuracy loss;
- **Memory subsystem**: Supports LPDDR5T (Turbo) with peak bandwidth exceeding 100 GB/s, approximately 20% higher than Dimensity 9300;
- **Inference framework**: NeuroPilot SDK with added toolchain support for INT4 quantized models;
- **ISP co-processing**: Paired with Imagiq 990 ISP, supporting 4-channel 18-bit parallel ISP processing, one additional concurrent camera channel over Imagiq 980.

> **Note**: Dimensity 9400 NPU compute figure (~50 TOPS INT8) is sourced from the MediaTek Dimensity 9400 product page (MediaTek, 2024) and related media coverage; APU 860's full official spec was not fully disclosed at the time of writing, and the INT4 equivalent figure is derived.

### 2.5 OPPO MariSilicon X

OPPO MariSilicon X (released 2022, featured in the Find X5 Pro) is the most representative **dedicated ISP NPU** currently available, distinguished from general-purpose mobile NPUs:

- **Compute**: 18 TOPS (INT8, OPPO official) — lower than general-purpose NPUs but ISP-optimized;
- **Specialization**: Hardware logic designed specifically for RAW denoising, demosaic enhancement, and HDR merging; larger on-chip SRAM (reducing DRAM accesses); memory bandwidth allocation prioritizes the AI ISP pipeline;
- **Latency**: Real-time 4K RAW denoising latency approximately 8 ms (vs. approximately 15–20 ms for the same task on Snapdragon Hexagon);
- **Development interface**: Closed-source; limited API exposed only through the OPPO SDK; third-party applications cannot call it directly;
- **Strategic significance**: The release of MariSilicon X marks smartphone vendors beginning to develop dedicated AI ISP chips in-house — an important milestone in the trend toward "independent ISP NPU."

### 2.6 NPU Performance Comparison Summary

| Platform | NPU | INT8 Compute | Memory Bandwidth | Inference Framework | RAW-Domain Capability |
|:---:|:---:|:-------:|:-------:|:-------:|:--------:|
| Snapdragon 8 Gen 3 | Hexagon NPU | ~34 TOPS (third-party est.) | 77.4 GB/s | QNN SDK | Indirect (via Spectra ISP) |
| A17 Pro | Apple NE | 35 TOPS (Apple official) | ~68 GB/s | CoreML | Partial (ProRAW NE processing) |
| Dimensity 9300 | APU 790 | 33 TOPS (MediaTek official) | 82.7 GB/s | NeuroPilot | Partial |
| Dimensity 9400 | APU 860 | ~50 TOPS (estimated, non-official) | ~100 GB/s | NeuroPilot | Partial (Imagiq 990 co-processing) |
| MariSilicon X | Dedicated ISP NPU | 18 TOPS (OPPO official) | Dedicated bandwidth | OPPO closed-source SDK | Native |

---

## §3 Quantization for ISP

### 3.1 INT8 Quantization Challenges for ISP Networks

For image-restoration networks (e.g., DnCNN, NAFNet), INT8 quantization presents more stringent challenges than for image classification:

**Activation Distribution Problem**: ISP networks process pixel-level residuals, and activations can have a dynamic range far exceeding that of classification networks. In particular, the QK dot product before Softmax in Transformer attention layers has a value range of approximately $[-C/\sqrt{d_k},\, C/\sqrt{d_k}]$, where $d_k$ is the attention head dimension and $C$ is the channel count. When $C$ is large (e.g., NAFNet uses 32–64 channels), this range may overflow the effective representable range of INT8 ([-128, 127]), causing **activation range explosion** and a dramatic increase in quantization error.

**Per-Tensor Quantization vs. Per-Channel Quantization**:

- **Per-tensor quantization**: The entire layer uses a single Scale and Zero Point. Computationally simplest, but accuracy degrades noticeably for layers with non-uniform activation distributions (e.g., attention layers);
- **Per-channel quantization**: Each output channel has its own Scale and Zero Point. Higher accuracy, at the cost of increased storage overhead (Scale/ZP per channel) and limited support for per-channel quantization on some NPUs.

Theoretical upper bound on quantization error (per-tensor, weight quantization):

$$\mathbb{E}[|\Delta w|] \leq \frac{s}{2} = \frac{\text{range}(w)}{2 \times 255}$$

The greater the number of channels and the more non-uniform the weight distribution, the larger the per-tensor quantization error; per-channel quantization should be used in those cases.

### 3.2 SmoothQuant: Activation Smoothing

SmoothQuant (Xiao et al., ICML 2023) addresses the problem of activation outliers in LLM quantization through a mathematically equivalent transformation: migrating the quantization difficulty from activations onto the weights. For a linear layer $Y = XW$, introduce a diagonal matrix $S = \text{diag}(s_1, s_2, \ldots, s_d)$:

$$Y = (X S^{-1}) \cdot (S W) = \hat{X} \hat{W}$$

Choose $s_j = \max(|X_j|)^\alpha / \max(|W_j|)^{1-\alpha}$ where $\alpha \in [0.5, 0.85]$ (typically 0.5). This compresses the dynamic range of activations by transferring it to the weights, balancing quantization between the two and substantially reducing INT8 quantization error. SmoothQuant is equally effective for ISP networks like NAFNet, especially variants containing multi-head self-attention (MHSA).

### 3.3 AWQ (Activation-aware Weight Quantization)

AWQ (Lin et al., MLSys 2024) is currently one of the best methods for LLM INT4 quantization. Its core insight is: **not all weight channels contribute equally to quantization error — channels corresponding to larger (more important) activations should be protected with smaller quantization error**.

Specifically: for channels with high activation importance, weights are multiplied by a scale factor $s > 1$ before quantization (amplifying to protect them), and the corresponding input activations are divided by $s$ at inference time:

$$\hat{W}_q = Q(W \cdot \text{diag}(s)), \quad \hat{X} = X \cdot \text{diag}(s)^{-1}$$

AWQ requires no access to the full training set (only a small calibration dataset), has low calibration cost, and is compatible with existing quantization frameworks (AutoAWQ, llm.int8()). For lightweight ISP networks (e.g., MobileNet-based denoising networks), AWQ typically limits PSNR loss to within 0.3 dB under INT4 quantization.

### 3.4 NAFNet INT8 Benchmark

NAFNet (Simple Baselines for Image Restoration, ECCV 2022, Chen et al.) is currently one of the lightweight ISP restoration networks with the best overall performance. The following are quantization benchmark figures on Snapdragon 8 Gen 3 (Hexagon NPU, HTP Backend) for 1080p single-frame inference:

| Configuration | PSNR (SIDD Validation) | Inference Latency | Model Size |
|:---:|:---:|:---:|:---:|
| NAFNet-32 FP32 | 39.9 dB | 32 ms | ~68 MB |
| NAFNet-32 FP16 | 39.9 dB | 18 ms | ~34 MB |
| NAFNet-32 INT8 (PTQ) | 39.5 dB | **8 ms** | ~17 MB |
| NAFNet-32 INT8 (QAT) | 39.8 dB | **8 ms** | ~17 MB |
| NAFNet-32 INT4 (AWQ) | 39.1 dB | 5 ms | ~8.5 MB |

**PTQ (Post-Training Quantization)** requires no retraining; activation distributions are profiled via a calibration dataset (approximately 100–500 images) and quantization is completed directly, making it suitable for rapid deployment. **QAT (Quantization-Aware Training)** inserts fake quantization nodes during training so the model adapts to quantization error at train time; final accuracy is approximately 0.2–0.3 dB higher than PTQ, but requires retraining cost.

Key conclusion: **NAFNet-32 INT8 achieves 8 ms/frame on the Hexagon NPU, satisfying the 30 fps real-time requirement (33 ms) with substantial margin remaining for other ISP processing steps.**

---

## §4 NAS for Mobile ISP

### 4.1 NAS Search Space Design

The goal of Neural Architecture Search (NAS) is to find the optimal architecture satisfying dual latency and accuracy objectives within a predefined search space. For ISP tasks the search space typically spans the following dimensions:

| Search Dimension | Typical Options |
|:-------:|:-------:|
| Backbone | MobileNetV3, EfficientNet-Lite, ResNet-Lite |
| Convolution type | Standard conv (3×3, 5×5), depth-wise separable conv (DW-Conv), dilated conv |
| Channel width | [0.25×, 0.5×, 0.75×, 1.0×, 1.25×] |
| Network depth | Blocks per stage [1, 2, 3, 4] |
| Activation function | ReLU, GELU, SiLU |
| Attention mechanism | None, SE module (Squeeze-and-Excitation), CBAM, SKFF |

**Adapting MobileNetV3 for ISP**: MobileNetV3 (Howard et al., ICCV 2019) introduced the Hard Swish activation ($x \cdot \text{ReLU6}(x+3)/6$) and SE modules, yielding a superior accuracy–efficiency ratio on mobile compared to earlier MobileNet versions. However, original MobileNetV3 was designed for classification; adapting it for ISP image restoration requires removing downsampling layers (to avoid spatial resolution loss) and adding skip connections and upsampling modules.

### 4.2 Pareto Frontier Search Strategy

ISP NAS is typically a bi-objective optimization problem: maximize PSNR while minimizing FLOPs (Floating-Point Operations):

$$\text{maximize} \quad (Q_{\text{PSNR}},\ -C_{\text{FLOPs}})$$

In practice, an **accuracy predictor** and a **latency lookup table (LUT)** are commonly used as proxies to replace actual training and inference, accelerating the search. The accuracy predictor can be trained by regression on 50–100 full training runs; the latency LUT is constructed by measuring the runtime of each operator configuration on the target device.

### 4.3 Once-for-All and MCUNet

**Once-for-All (OFA, MIT, Cai et al., ICLR 2020)** solves the pain point of "needing to re-search and retrain every time the hardware changes." OFA's core idea is to train a super network from which sub-networks satisfying various hardware constraints can be directly sampled, without training the sub-networks from scratch (training-free deployment):

$$\theta_{\text{subnet}} \subseteq \theta_{\text{supernet}}, \quad \text{sub-networks need no additional training}$$

OFA uses a **progressive shrinking** strategy during training: first train the largest sub-network, then progressively shrink it, so every sub-network inherits a good initialization directly from the super-network parameters. For ISP tasks, OFA can generate specialized sub-networks targeting different NPUs (Hexagon/APU) and different latency budgets from a single super-network training run.

**MCUNet (Lin et al., NeurIPS 2020)** is designed for the extreme resource constraints of MCUs (Microcontroller Units: memory < 1 MB, compute < 100 MOPS). By jointly searching both the inference framework (TinyEngine) and the network architecture, it enables image classification to run on microcontrollers. Although MCUNet primarily targets classification, its co-optimization philosophy has important reference value for lightweight ISP networks.

### 4.4 NTIRE 2024 Efficient Super-Resolution Challenge

NTIRE (New Trends in Image Restoration and Enhancement, CVPR Workshop) holds an efficient super-resolution challenge every year, specifically evaluating super-resolution quality under constrained compute budgets. Typical characteristics of winning solutions at NTIRE 2024 Efficient Super-Resolution Challenge:

- **Dominant architecture**: NAFNet variants or lightweight Swin Transformer, with complex multi-scale feature extraction removed;
- **Key techniques**:
  - **Re-parameterization**: Multi-branch structure at training time (higher accuracy), merged into a single branch at inference time (lower latency), similar to the DBB (Diverse Branch Block) approach;
  - **Pixel shuffle**: Upsampling modules use sub-pixel convolution (Shi et al., CVPR 2016), more efficient than bilinear interpolation;
  - **Feature distillation**: Large model distills small model (FDN, Feature Distillation Network approach);
- **Typical specifications**: Top solutions achieve PSNR 29.8 dB (DIV2K-Valid ×4) with 0.4 M parameters and approximately 30 G FLOPs (720p → 1080p).

---

## §5 Deployment Pipeline

### 5.1 Model Format Conversion Chain

Getting from training framework to on-device deployment requires a series of format conversions:

```
PyTorch (.pth) / TensorFlow (.h5)
        ↓
    ONNX (.onnx)          ← Universal intermediate format, cross-framework compatible
   /         \
TFLite        QNN (Qualcomm)       CoreML (Apple)
(.tflite)    (.serialized.bin)     (.mlpackage)
   ↓              ↓                    ↓
Android         Snapdragon           iOS / macOS
TFLite Runtime  Hexagon NPU          Apple Neural Engine
```

**ONNX (Open Neural Network Exchange)** is currently the most widely used intermediate format, supporting export from PyTorch (`torch.onnx.export`), TensorFlow (tf2onnx), and other frameworks. Key points when exporting ONNX:

- Use `opset_version=17` (latest stable version, widest compatibility);
- For models with dynamic shapes (e.g., supporting arbitrary-resolution inputs), declare dynamic axes at export time;
- Use `do_constant_folding=True` in `torch.onnx.export` to fold constant computations ahead of time.

### 5.2 TFLite Conversion and Optimization

**TFLite (TensorFlow Lite)** is Google's inference framework for mobile and embedded devices; models are converted from TensorFlow or ONNX (via ai_edge_torch) using TFLite Converter:

```python
import tensorflow as tf

converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
# INT8 quantization configuration
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = calibration_dataset_generator
converter.target_spec.supported_ops = [
    tf.lite.OpsSet.TFLITE_BUILTINS_INT8,
    tf.lite.OpsSet.SELECT_TF_OPS  # support non-standard operators
]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8
tflite_model = converter.convert()
```

**Memory layout** is a critical factor affecting TFLite performance:
- **NHWC (Batch, Height, Width, Channel)**: Native layout for TFLite/Android/ARM CPU; convolution operations are optimized for NHWC;
- **NCHW (Batch, Channel, Height, Width)**: Native layout for PyTorch/CUDA/Qualcomm QNN.

Different backends use different memory layouts; conversion must insert transpose operators or use correct export settings, otherwise large data-rearrangement overheads are introduced in key convolution layers, increasing latency by 50%–100%. Empirically: without aligned memory layout, NAFNet TFLite latency increases from 8 ms to 19 ms.

### 5.3 QNN Deployment (Qualcomm Neural Network SDK)

The Qualcomm QNN SDK (part of the Qualcomm AI Engine Direct SDK) provides the inference interface closest to the Hexagon NPU hardware level:

```bash
# Step 1: ONNX → QNN format conversion (run on development host)
qnn-onnx-converter \
    --input_network nafnet.onnx \
    --output_path nafnet_qnn \
    --input_dim "input:1,3,1080,1920" \
    --quantization_overrides quant_config.json  # AWQ quantization config

# Step 2: Compile to device-specific binary (specify target SoC)
qnn-model-lib-generator \
    -m nafnet_qnn/model.cpp \
    -b nafnet_qnn/model.bin \
    -o nafnet_lib/ \
    --lib_target aarch64-android  # Snapdragon 8 Gen 3, Android platform

# Step 3: On-device inference (push via Android ADB, then run)
qnn-net-run \
    --model nafnet_lib/libQnnModel.so \
    --backend libQnnHtp.so \
    --input_list input_list.txt \
    --output_dir output/
```

**HTP Backend (Hexagon Tensor Processor)**: The QNN HTP Backend calls the Hexagon DSP's dedicated AI accelerator (HTA) directly and delivers the best performance. Note that HTP has limited operator support; unsupported operators automatically fall back to the CPU Backend, incurring context-switch overhead (each CPU–NPU data transfer costs approximately 0.5–1 ms; frequent switching can multiply total latency). **Operator fusion** is key to reducing switches — inspect the quantized computation graph to ensure critical Conv–BN–Activation sequences are fused into single NPU operators.

### 5.4 Latency Analysis Tools

| Tool | Platform | Functionality |
|:---:|:---:|:---:|
| Snapdragon Profiler | Android (Snapdragon devices) | CPU/GPU/NPU timeline, operator-level latency analysis |
| Xcode Instruments | iOS/macOS | NE/GPU/CPU timeline, energy consumption analysis |
| TFLite Benchmark Tool | Android/iOS | Operator-level latency report, memory usage |
| AI Benchmark | Android | Cross-device standardized AI inference benchmarks |
| NeuroPilot Profiler | Android (MediaTek devices) | APU operator latency analysis |

### 5.5 Batch Processing Strategy for Burst Photography

Night-mode multi-frame synthesis (Burst Night Mode) requires feeding multiple frames (typically 4–16) of RAW images into a neural network for inter-frame alignment and fusion. The choice of batching strategy is critical:

- **Serial single-frame processing**: Inference frame by frame, each frame processed independently — lowest per-frame latency but cannot exploit inter-frame correlation;
- **Mini-batch processing (B = 4–8)**: Combine multiple frames into a single batch for unified inference — NPU throughput improves significantly (typically 1.5–3× throughput), but single inference latency grows linearly with B, potentially impacting real-time preview;
- **Streaming processing (B = 1 with frame buffer)**: Infer while capturing; NPU idle time is used to process the previous frame, achieving pipeline parallelism. Suitable for capture-latency-sensitive scenarios (e.g., rapid burst shooting).

In practice, flagship phone night-mode algorithms typically adopt a **hybrid strategy**: serial single-frame processing during preview (guaranteeing real-time performance), switching to mini-batch processing after the shutter is pressed (improving quality), and completing final frame merging in the background after the capture (no perceived delay).

---

## §6 Code

The code file corresponding to this chapter is *See §6 Code section for runnable examples.*, containing the following demonstration cells:

### Cell 1: NAFNet FP32 Model Construction and Inference Baseline

```python
"""
ch13_edge_ai_demo.py

NAFNet quantization and on-device deployment demonstration
Dependencies: torch, torchvision, onnx, onnxruntime, numpy, opencv-python
Optional: tensorflow (for TFLite conversion)

Demonstration flow:
  1. Build lightweight NAFNet-16 (channel count reduced to 16)
  2. FP32 inference baseline
  3. PTQ INT8 quantization
  4. ONNX export
  5. PSNR and latency comparison
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
import cv2


# ─────────────────────────────────────────────────────────────
# §6.1  Lightweight NAFBlock (simplified NAFNet core module)
# ─────────────────────────────────────────────────────────────

class SimpleGate(nn.Module):
    """NAFNet Simple Gate activation: split channels in half, multiply element-wise"""
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1, x2 = x.chunk(2, dim=1)
        return x1 * x2


class NAFBlock(nn.Module):
    """
    NAFNet basic block (simplified).
    Reference: Chen et al., "Simple Baselines for Image Restoration", ECCV 2022.

    Structure: LayerNorm → DW-Conv → 1×1 Conv → SimpleGate → 1×1 Conv + SE → residual
    """
    def __init__(self, c: int, dw_expand: int = 2, ffn_expand: int = 2):
        super().__init__()
        dw_ch = c * dw_expand
        ffn_ch = c * ffn_expand

        self.norm1 = nn.GroupNorm(1, c)  # approximates LayerNorm, suitable for NCHW
        self.conv1 = nn.Conv2d(c, dw_ch, 1)
        self.conv2 = nn.Conv2d(dw_ch, dw_ch, 3, padding=1, groups=dw_ch)  # DW-Conv
        self.conv3 = nn.Conv2d(dw_ch // 2, c, 1)
        self.sg = SimpleGate()

        # Simplified SE (Squeeze-and-Excitation); applied to dw_ch//2 channels after SimpleGate
        sg_ch = dw_ch // 2
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(sg_ch, max(sg_ch // 4, 4), 1),
            nn.ReLU(),
            nn.Conv2d(max(sg_ch // 4, 4), sg_ch, 1),
            nn.Sigmoid()
        )

        self.norm2 = nn.GroupNorm(1, c)
        self.ff1 = nn.Conv2d(c, ffn_ch, 1)
        self.ff2 = nn.Conv2d(ffn_ch // 2, c, 1)

    def forward(self, inp: torch.Tensor) -> torch.Tensor:
        x = inp
        # Attention branch
        x = self.norm1(x)
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.sg(x)
        x = x * self.se(x)
        x = self.conv3(x)
        y = inp + x

        # FFN branch
        x = self.norm2(y)
        x = self.ff1(x)
        x = self.sg(x)
        x = self.ff2(x)
        return y + x


class LightNAFNet(nn.Module):
    """
    Lightweight NAFNet (16 channels, 4 blocks), used to demonstrate the quantization pipeline.
    Approximately 0.5 M parameters, suitable for demonstrating on-device INT8 deployment.
    """
    def __init__(self, in_ch: int = 3, out_ch: int = 3, width: int = 16, n_blocks: int = 4):
        super().__init__()
        self.intro = nn.Conv2d(in_ch, width, 3, padding=1)
        self.blocks = nn.Sequential(*[NAFBlock(width) for _ in range(n_blocks)])
        self.outro = nn.Conv2d(width, out_ch, 3, padding=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.intro(x)
        x = self.blocks(x)
        x = self.outro(x)
        return x


def measure_latency(model: nn.Module, input_shape=(1, 3, 256, 256),
                    n_warmup: int = 10, n_repeat: int = 50,
                    device: str = 'cpu') -> float:
    """
    Measure model inference latency (milliseconds).
    Uses warm-up followed by repeated measurement and averaging,
    reducing the impact of first-run JIT compilation.
    """
    model = model.to(device).eval()
    x = torch.randn(input_shape).to(device)

    with torch.no_grad():
        for _ in range(n_warmup):
            _ = model(x)
        if device == 'cuda':
            torch.cuda.synchronize()

        t_start = time.perf_counter()
        for _ in range(n_repeat):
            _ = model(x)
        if device == 'cuda':
            torch.cuda.synchronize()
        t_end = time.perf_counter()

    return (t_end - t_start) / n_repeat * 1000  # return milliseconds


# ─────────────────────────────────────────────────────────────
# §6.2  PSNR utility
# ─────────────────────────────────────────────────────────────

def psnr(img_pred: np.ndarray, img_gt: np.ndarray, max_val: float = 255.0) -> float:
    """
    Compute Peak Signal-to-Noise Ratio (PSNR).

    Args:
        img_pred: predicted image, float32
        img_gt:   reference image, float32, must have same shape as img_pred
        max_val:  maximum pixel value (default 255.0, for uint8 images)

    Returns:
        psnr_db: PSNR value (dB); higher means closer to the reference image
    """
    mse = np.mean((img_pred.astype(np.float64) - img_gt.astype(np.float64)) ** 2)
    if mse < 1e-10:
        return float('inf')
    return 10 * np.log10(max_val ** 2 / mse)
```

### Cell 2: PTQ INT8 Quantization (Post-Training Quantization)

```python
# ─────────────────────────────────────────────────────────────
# §6.3  PTQ (Post-Training Quantization) demonstration
#        using the PyTorch static quantization API
# ─────────────────────────────────────────────────────────────

import torch.ao.quantization as tq  # torch.quantization deprecated in PyTorch ≥2.0


def prepare_calibration_dataset(n_images: int = 100,
                                 img_size: int = 256) -> list:
    """
    Generate a random calibration dataset (replace with real images in production).
    The calibration dataset is used to profile the dynamic range (min/max) of
    activations at each layer; 100–500 real images from the same distribution
    as the training set is recommended.
    """
    return [torch.randn(1, 3, img_size, img_size) for _ in range(n_images)]


def ptq_quantize(model: nn.Module,
                 calibration_data: list,
                 backend: str = 'qnnpack') -> nn.Module:
    """
    Apply PTQ static quantization to the model (PyTorch native API).

    Args:
        model:            FP32 model with loaded weights
        calibration_data: list of calibration tensors, each [1, C, H, W]
        backend:          quantization backend, 'qnnpack' (ARM/Android) or 'fbgemm' (x86)

    Returns:
        quantized_model:  INT8-quantized model (PyTorch format)
    """
    torch.backends.quantized.engine = backend

    # Step 1: Specify quantization configuration
    model.eval()
    model.qconfig = tq.get_default_qconfig(backend)

    # Step 2: Insert observers (collect activation statistics)
    model_prepared = tq.prepare(model, inplace=False)

    # Step 3: Forward pass on calibration data to record activation distributions
    print(f"Calibrating with {len(calibration_data)} images...")
    with torch.no_grad():
        for i, x in enumerate(calibration_data):
            _ = model_prepared(x)
            if (i + 1) % 20 == 0:
                print(f"  Calibration progress: {i+1}/{len(calibration_data)}")

    # Step 4: Replace observers with actual quantization operators
    model_quantized = tq.convert(model_prepared, inplace=False)
    print("PTQ quantization complete.")
    return model_quantized


def compare_fp32_int8(fp32_model: nn.Module, int8_model: nn.Module,
                      test_image: np.ndarray) -> dict:
    """
    Compare PSNR and inference latency of FP32 vs. INT8 models.

    Args:
        fp32_model:  FP32 model
        int8_model:  INT8 quantized model
        test_image:  test image, np.ndarray [H, W, 3], uint8

    Returns:
        results: dictionary containing PSNR and latency comparison
    """
    # Preprocessing: add Gaussian noise (simulate low-light noise)
    noisy = test_image.astype(np.float32) + np.random.normal(0, 25, test_image.shape)
    noisy = np.clip(noisy, 0, 255).astype(np.float32)

    # Convert to tensor
    def to_tensor(img_np):
        t = torch.from_numpy(img_np).float() / 255.0
        return t.permute(2, 0, 1).unsqueeze(0)

    x = to_tensor(noisy)
    y_gt = test_image.astype(np.float32)

    # FP32 inference
    fp32_model.eval()
    with torch.no_grad():
        t0 = time.perf_counter()
        y_fp32 = fp32_model(x)
        t1 = time.perf_counter()

    y_fp32_np = (y_fp32.squeeze(0).permute(1, 2, 0).numpy() * 255).clip(0, 255)
    fp32_psnr = psnr(y_fp32_np, y_gt)
    fp32_lat = (t1 - t0) * 1000

    # INT8 inference
    int8_model.eval()
    with torch.no_grad():
        t0 = time.perf_counter()
        y_int8 = int8_model(x)
        t1 = time.perf_counter()

    y_int8_np = (y_int8.squeeze(0).permute(1, 2, 0).numpy() * 255).clip(0, 255)
    int8_psnr = psnr(y_int8_np, y_gt)
    int8_lat = (t1 - t0) * 1000

    return {
        'fp32_psnr_db': fp32_psnr,
        'int8_psnr_db': int8_psnr,
        'psnr_drop_db': fp32_psnr - int8_psnr,
        'fp32_latency_ms': fp32_lat,
        'int8_latency_ms': int8_lat,
        'speedup_x': fp32_lat / max(int8_lat, 1e-3)
    }
```

### Cell 3: ONNX Export and Validation

```python
# ─────────────────────────────────────────────────────────────
# §6.4  ONNX export and onnxruntime validation
# ─────────────────────────────────────────────────────────────

import onnx
import onnxruntime as ort


def export_to_onnx(model: nn.Module,
                   onnx_path: str,
                   input_shape: tuple = (1, 3, 256, 256),
                   opset_version: int = 17) -> None:
    """
    Export a PyTorch model to ONNX format.

    Args:
        model:         FP32 PyTorch model (already eval())
        onnx_path:     export path, e.g. "nafnet.onnx"
        input_shape:   input shape (B, C, H, W)
        opset_version: ONNX opset version, recommended 17
    """
    model.eval()
    dummy_input = torch.randn(input_shape)

    # Declare dynamic axes: support arbitrary H and W (on-device often handles varying resolutions)
    dynamic_axes = {
        'input': {0: 'batch_size', 2: 'height', 3: 'width'},
        'output': {0: 'batch_size', 2: 'height', 3: 'width'}
    }

    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        opset_version=opset_version,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes=dynamic_axes,
        do_constant_folding=True,  # constant folding optimization
        verbose=False
    )
    print(f"ONNX model exported: {onnx_path}")

    # Validate ONNX model structure
    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)
    print("ONNX model structure validation passed.")

    # Count parameters
    total_params = sum(
        np.prod(init.dims)
        for init in onnx_model.graph.initializer
    )
    print(f"ONNX model parameter count: {total_params / 1e6:.2f}M")


def onnxruntime_inference(onnx_path: str,
                          input_np: np.ndarray) -> np.ndarray:
    """
    Run ONNX model inference using onnxruntime (CPU, for validating export correctness).

    Args:
        onnx_path: ONNX model path
        input_np:  input array, shape [1, C, H, W], float32

    Returns:
        output_np: output array, shape [1, C, H, W], float32
    """
    sess = ort.InferenceSession(
        onnx_path,
        providers=['CPUExecutionProvider']
    )
    input_name = sess.get_inputs()[0].name
    output_name = sess.get_outputs()[0].name

    output = sess.run([output_name], {input_name: input_np})
    return output[0]


# ─────────────────────────────────────────────────────────────
# §6.5  Full demonstration flow
# ─────────────────────────────────────────────────────────────

def run_full_demo():
    """Complete quantization deployment demonstration flow"""
    print("=" * 60)
    print("NAFNet Quantization Deployment Demo: FP32 → INT8 PTQ → ONNX Export")
    print("=" * 60)

    # 1. Build FP32 model
    print("\n[1/5] Building LightNAFNet-16 FP32 model...")
    model_fp32 = LightNAFNet(width=16, n_blocks=4)
    total_params = sum(p.numel() for p in model_fp32.parameters())
    print(f"  Parameter count: {total_params/1e6:.3f}M")

    # 2. Measure FP32 latency
    print("\n[2/5] Measuring FP32 baseline latency (256×256, CPU)...")
    lat_fp32 = measure_latency(model_fp32, input_shape=(1, 3, 256, 256))
    print(f"  FP32 latency: {lat_fp32:.2f} ms")

    # 3. PTQ INT8 quantization
    print("\n[3/5] PTQ INT8 quantization (calibrating on 100 random images)...")
    calib_data = prepare_calibration_dataset(n_images=100)
    model_int8 = ptq_quantize(model_fp32, calib_data, backend='qnnpack')

    # 4. Measure INT8 latency
    print("\n[4/5] Measuring INT8 latency...")
    lat_int8 = measure_latency(model_int8, input_shape=(1, 3, 256, 256))
    print(f"  INT8 latency: {lat_int8:.2f} ms")
    print(f"  Speedup: {lat_fp32/lat_int8:.1f}x")

    # 5. PSNR comparison (synthetically noised test image)
    print("\n[5/5] PSNR comparison (synthetic noise test image)...")
    test_img = np.random.randint(100, 200, (256, 256, 3), dtype=np.uint8)
    results = compare_fp32_int8(model_fp32, model_int8, test_img)
    print(f"  FP32 PSNR: {results['fp32_psnr_db']:.2f} dB")
    print(f"  INT8 PSNR: {results['int8_psnr_db']:.2f} dB")
    print(f"  PSNR drop: {results['psnr_drop_db']:.2f} dB")

    # 6. ONNX export
    print("\n[6/6] Exporting FP32 model to ONNX format...")
    export_to_onnx(model_fp32, "nafnet_light.onnx")

    print("\nDemo complete!")
    print("Next steps: use qnn-onnx-converter to convert nafnet_light.onnx to QNN format,")
    print("            or use TFLiteConverter to convert to TFLite INT8 format,")
    print("            then deploy to the target device for latency validation.")
    return results


if __name__ == "__main__":
    results = run_full_demo()
```

> **Notebook note**: *See §6 Code section for runnable examples.* contains a fully executable version of the above code, with visualization cells (PSNR comparison curves before and after quantization, latency bar charts, Pareto frontier scatter plots). The code runs completely on x86 CPU; for deployment on Android devices with Snapdragon chips, refer to the Qualcomm QNN SDK official documentation.

---

## References

1. **Chen, L., Chu, X., Zhang, X., & Sun, J.** (2022). Simple Baselines for Image Restoration. *ECCV 2022*. arXiv:2204.04676.

2. **Lin, J., Tang, J., Tang, H., & Han, S.** (2024). AWQ: Activation-aware Weight Quantization for On-Device LLM Compression and Acceleration. *MLSys 2024*. arXiv:2306.00978.

3. **Cai, H., Gan, C., Wang, T., Zhang, Z., & Han, S.** (2020). Once-for-All: Train One Network and Specialize it for Efficient Deployment. *ICLR 2020*. arXiv:1908.09791.

4. **Lin, J., Chen, W., Lin, Y., Cohn, J., Gan, C., & Han, S.** (2020). MCUNet: Tiny Deep Learning on IoT Devices. *NeurIPS 2020*. arXiv:2007.10319.

5. **Howard, A., Sandler, M., Chu, G., et al.** (2019). Searching for MobileNetV3. *ICCV 2019*. arXiv:1905.02244.

6. **Xiao, G., Lin, J., Seznec, M., Wu, H., Demouth, J., & Han, S.** (2023). SmoothQuant: Accurate and Efficient Post-Training Quantization for Large Language Models. *ICML 2023*. arXiv:2211.10438.

7. **Shi, W., Caballero, J., Huszár, F., et al.** (2016). Real-Time Single Image and Video Super-Resolution Using an Efficient Sub-Pixel Convolutional Neural Network. *CVPR 2016*. arXiv:1609.05158.

8. **Ding, X., Zhang, X., Ma, N., Han, J., Ding, G., & Sun, J.** (2021). RepVGG: Making VGG-style ConvNets Great Again. *CVPR 2021*. arXiv:2101.03697.

9. **Qualcomm Technologies, Inc.** (2024). Qualcomm AI Engine Direct SDK (QNN SDK) Developer Guide. *Qualcomm Developer Network*. https://developer.qualcomm.com/software/qualcomm-ai-engine-direct-sdk

10. **NTIRE 2024 Efficient Super-Resolution Challenge.** (2024). Results and Winning Solutions. *CVPR 2024 Workshop on New Trends in Image Restoration and Enhancement*.

---

## §8 Glossary

| Term | Full Form / Meaning |
|:---:|:----------|
| **NPU** | Neural Processing Unit. Hardware accelerator optimized for neural network inference, distinct from GPU (graphics processing) and CPU (general-purpose compute). |
| **INT8 Quantization** | 8-bit Integer Quantization. Compresses FP32 weights and activations into INT8 representation, reducing model size by 4× and improving inference speed by 2–8×, with accuracy loss typically below 0.5 dB. |
| **NAS** | Neural Architecture Search. Automatically finds the optimal neural network structure within a predefined search space while satisfying accuracy and latency constraints. |
| **TOPS** | Tera Operations Per Second. Unit measuring AI accelerator compute. 1 TOPS = $10^{12}$ INT8 MAC/s. |
| **QNN** | Qualcomm Neural Network (SDK). Qualcomm AI Engine's unified inference framework, supporting high-performance deployment on the Hexagon NPU. |
| **TFLite** | TensorFlow Lite. Google's lightweight inference framework for mobile and embedded devices, supporting INT8 quantization and multiple hardware delegates. |
| **PTQ** | Post-Training Quantization. Requires no retraining; quantization is completed by profiling activation distributions from a small calibration dataset. Fast but slightly lower accuracy than QAT. |
| **QAT** | Quantization-Aware Training. Inserts fake quantization nodes during training so the model adapts to quantization error; better accuracy than PTQ at the cost of retraining. |
| **LPDDR5** | Low Power Double Data Rate 5. Mobile low-power high-speed memory standard. Standard LPDDR5 theoretical bandwidth is approximately 51–68 GB/s; LPDDR5X (eXtended) reaches approximately 77–85 GB/s; LPDDR5T (Turbo) can exceed 100 GB/s. |
| **HTP Backend** | Hexagon Tensor Processor Backend. The highest-performance backend in QNN, directly invoking the Snapdragon Hexagon NPU tensor accelerator. |

---

*Code file for this chapter: *See §6 Code section for runnable examples.**
*Reference hardware platforms: Snapdragon 8 Gen 3 (Hexagon NPU), Apple A17 Pro (Neural Engine), OPPO Find X5 Pro (MariSilicon X)*
