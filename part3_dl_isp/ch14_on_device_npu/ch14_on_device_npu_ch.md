# 第三卷第14章：端侧神经网络ISP：NPU部署与量化

> **定位：** 本章专注于将DL ISP模型部署到手机NPU的工程实践，覆盖INT8量化、算子融合、内存优化。整体端侧推理框架见第五卷第13章。
> **前置章节：** 第三卷第01章（DL ISP综述）、第三卷第02章（端到端图像复原）
> **读者路径：** 嵌入式工程师、算法工程师

---

> **关于本章数据来源的说明：** 本章涉及的 NPU 推理延迟数据（TOPS 算力、ms/帧延迟）来自高通 SNPE 官方白皮书、联发科 NeuroPilot 文档、MAI（Mobile AI & AIM Workshop）竞赛官方报告，以及 Arm ML Inference Advisor 公开基准。作者没有独立的端侧测试环境，无法自行复现这些数字。芯片每代性能提升较快，书中数字以标注日期为准，具体项目请以平台实测为准。MAI 竞赛（CVPR 系列年度举办）是截至本书成稿时最接近真实部署约束的公开端侧推理评测，推荐作为参考基准。

## §1 理论原理

### 1.1 端侧部署的动机与挑战

DL-ISP 在图像质量上已超越传统 ISP，但从实验室模型到手机 NPU 的实际落地，远不是"转 ONNX 然后部署"那么简单。制约点有三条，且彼此耦合：算力上限、内存带宽天花板、功耗热节流。

主流手机 NPU（高通 Hexagon、华为昇腾、联发科 APU）INT8 算力在中低端 SoC 约 4～15 TOPS，2023–2024 年旗舰已到 34～49 TOPS（第三方估算），但仍远低于数据中心 GPU 的数百 TOPS。一帧 12MP RAW 的 UNet 型 FP32 推理往往需要数百 GFLOPs，不削减绝对无法实时。内存带宽更隐蔽：LPDDR5-6400 双通道约 102 GB/s（低端型号约 60 GB/s 起），但 NPU 片上 SRAM 通常仅几 MB，大中间特征图反复 DRAM 搬运带来的内存墙效应在实测中可使延迟翻倍。功耗热节流最难预判——单次推理可能没问题，但手机摄像会话期间持续 1～3W 以上触发热节流后，前几帧正常而后续帧骤慢的问题在量产设备上非常典型，性能测试必须覆盖连续拍摄场景。

### 1.2 量化的数学基础

量化（Quantization）是将浮点数映射到低精度整数的过程。最常用的是均匀仿射量化（Uniform Affine Quantization）：

$$
x_q = \text{clip}\!\left(\left\lfloor \frac{x}{s} \right\rceil + z,\; q_{\min},\; q_{\max}\right)
$$

其中 $s$ 为缩放因子（scale），$z$ 为零点（zero point），$\lfloor \cdot \rceil$ 表示四舍五入。反量化（dequantization）为：

$$
\hat{x} = s \cdot (x_q - z)
$$

对于INT8量化，$q_{\min}=-128,\; q_{\max}=127$（有符号）。量化误差主要来源于舍入误差（rounding error）和截断误差（clipping error）。

**逐张量量化（per-tensor）** 对整层权重使用单一 $(s, z)$，计算开销小但精度损失大；**逐通道量化（per-channel）** 对每个输出通道独立使用 $(s_c, z_c)$，精度更高，是部署卷积层的主流选择。两种方案的精度差异在ISP任务中可达0.2～0.5 dB PSNR。

### 1.3 量化感知训练（QAT）原理

训练后量化（Post-Training Quantization，PTQ）因缺乏梯度反馈，对激活值分布偏移敏感，精度损失在ISP任务中可达0.5～2 dB PSNR。量化感知训练（Quantization-Aware Training，QAT）在前向传播时插入伪量化节点（fake-quantize node）模拟量化误差，利用直通估计器（Straight-Through Estimator，STE）绕过不可微分的舍入操作传递梯度：

$$
\frac{\partial \mathcal{L}}{\partial x} \approx \frac{\partial \mathcal{L}}{\partial x_q} \cdot \mathbf{1}\!\left[q_{\min} \le \frac{x}{s} \le q_{\max}\right]
$$

经过QAT微调后，模型权重自适应调整以降低量化噪声，通常仅需全量训练的5～10%迭代数即可恢复精度至距离FP32模型0.1～0.2 dB以内。

### 1.4 NPU执行模型

主流NPU采用脉动阵列（Systolic Array）执行矩阵乘加（MAC，Multiply-Accumulate）运算。以高通Hexagon架构为例，其向量扩展（HVX，Hexagon Vector eXtensions）和张量加速器（HTP，Hexagon Tensor Processor）分别处理向量卷积与矩阵乘法。NPU调度器将网络图分割为算子子图，依次加载到片上SRAM并执行，数据在NPU与DRAM间通过DMA控制器传输。

理解NPU执行模型的关键是**算子支持列表（Supported Operator List）**：并非所有PyTorch算子都能在NPU上原生执行，不支持的算子会回退到CPU执行（CPU Fallback），造成严重的数据搬运开销，通常单次CPU Fallback引入的数据搬运延迟可超过算子本身执行时间的10倍。

---

## §2 算法方法

### 2.1 轻量化网络架构设计

#### 2.1.1 深度可分离卷积

MobileNetV2（Sandler等，CVPR 2018）**[1]** 引入的倒置残差块（Inverted Residual Block）和线性瓶颈（Linear Bottleneck）成为轻量化ISP骨干的基础。标准 $k \times k$ 卷积的FLOPs为 $k^2 \cdot C_{in} \cdot C_{out} \cdot H \cdot W$，而深度可分离卷积（Depthwise Separable Convolution，DW-Conv）将其分解为逐深度卷积（depthwise，$k^2 \cdot C_{in} \cdot H \cdot W$）与逐点卷积（pointwise，$C_{in} \cdot C_{out} \cdot H \cdot W$），理论加速比为 $k^2 / (1 + k^2/C_{out})$，对 $3\times 3$ 卷积约为8～9倍。

MobileNetV3（Howard等，ICCV 2019）**[2]** 进一步引入基于硬Sigmoid（h-sigmoid）的轻量注意力（压缩激励，Squeeze-and-Excitation，SE模块变体）与硬Swish（h-swish）激活函数，在ImageNet上以相同计算量超越V2约3.2%的Top-1精度 。在ISP去噪任务上，以MobileNetV3为骨干的网络相比标准UNet可降低延迟约4倍。

#### 2.1.2 面向ISP的神经架构搜索

Ignatov等提出的MAI Image Signal Processing Pipeline Challenge（CVPR Workshops 2021）推动了面向手机NPU的ISP网络架构搜索（Neural Architecture Search for ISP，ISP-NAS）。ISP-NAS的搜索空间必须从工程约束出发来定义，而不是从学术性能出发：对12MP图像FLOPs预算控制在100 GFLOPs以内；算子类型严格限制为NPU原生支持集合（Conv2D、DW-Conv、Add、Concat、ReLU等），单个CPU Fallback算子可抵消全部NPU加速收益；高分辨率输入强制采用pixel-unshuffle降分辨率 + pixel-shuffle恢复的编解码结构，将全分辨率运算量控制在总FLOPs的20%以内。

搜索出的最优架构通常呈现"宽浅"结构——通道数较多但层数较少，这与NPU擅长批量矩阵运算的特点吻合。但注意"宽浅"带来的代价是峰值SRAM占用增大，在SRAM仅4MB的中低端SoC上需要额外的分块推理策略。

#### 2.1.3 OPPO MariSilicon X的工程实践

OPPO MariSilicon X（2022年发布）是专为手机ISP设计的独立AI ISP芯片，峰值算力18 TOPS（OPPO 官方数据），片上SRAM 58 MB。其部署方案的关键策略包括：

- **分块处理（Tiling）**：将RAW输入分割为带重叠的小块以适应片上内存，重叠宽度根据网络感受野确定；
- **流水线并行（Pipeline Parallelism）**：去噪、去马赛克、色彩校正等子网络在芯片内部流水线并行执行，减少端到端延迟；
- **全INT8推理**：权重与激活均量化为INT8，相比FP16节省50%带宽，相比FP32节省75%，是实现实时12MP处理的关键。

### 2.2 INT8量化流程

#### 2.2.1 基于TFLite的端到端量化流程

Google TensorFlow Lite（TFLite）提供了完整的端到端量化工具链：

```
FP32 PyTorch模型
    → ONNX导出（opset 13）
    ├→ TFLite转换（TFLiteConverter）
    │      → PTQ（calibration dataset校准，推荐100～500张样本）
    │        或 QAT（伪量化节点微调）
    │      → .tflite模型（INT8权重 + INT8激活）
    │      → 部署至Android NNAPI / 高通SNPE/QNN / 联发科NeuroPilot
    ├→ Core ML转换（coremltools，Apple平台）
    │      → .mlpackage/.mlmodel 模型
    │      → 部署至Apple Neural Engine（ANE, iOS/macOS）
    └→ SNPE/QNN转换（qualcomm_ai_stack）
           → .dlc模型（骁龙Hexagon NPU）
```

校准数据集通常取自目标场景的100～500张RAW样本，用于统计每层激活值的分布，从而确定最优 $(s, z)$。

#### 2.2.2 混合精度量化

并非所有层对量化同等敏感。ISP网络中，浅层（靠近RAW输入的卷积层）和输出层对量化噪声最敏感，因为量化误差会在后续层中累积放大。

HAWQ（Dong等，ICCV 2019；HAWQ-V2，NeurIPS 2020）**[3][4]** 框架利用Hessian矩阵的迹（trace）衡量每层对量化误差的敏感度：

$$
\text{sensitivity}(l) = \text{tr}\!\left(\mathbf{H}_l\right)
$$

Hessian迹越大，说明该层对参数扰动越敏感，应分配更高比特宽度。自动分配的结果通常是：输入输出层INT8，中间瓶颈层INT4，平均比特宽度降至5～6 bit，延迟相比全INT8进一步降低15～20% ，精度基本维持不变。

### 2.3 算子融合优化

算子融合（Operator Fusion）将多个连续算子合并为单一NPU内核（kernel），消除中间特征图的DRAM读写，是NPU优化中收益最高的技术之一：

- **Conv-BN-ReLU融合**：将批归一化（Batch Normalization，BN）的缩放参数 $\gamma, \beta$ 折叠（fold）进卷积权重 $W$ 和偏置 $b$，公式为：
  $$W' = \frac{\gamma}{\sqrt{\sigma^2 + \epsilon}} W, \quad b' = \gamma\frac{b - \mu}{\sqrt{\sigma^2 + \epsilon}} + \beta$$
  再与ReLU合并为单一指令；
- **Add-ReLU融合**：残差连接后的加法与激活合并，减少一次特征图写回；
- **Conv-Concat融合**：在通道维度拼接后立即进行 $1\times 1$ 卷积时，可等价为并行多组卷积，合并为组卷积（Grouped Convolution）减少调度开销。

实测中，算子融合可将典型ISP UNet结构的NPU延迟降低约25～35%。

### 2.4 内存优化策略

#### 2.4.1 特征图生命周期分析

在编解码网络（U-Net型结构）中，编码器特征图需保留至解码器对应层使用。通过精心设计的生命周期分析（Liveness Analysis），可将不重叠的特征图分配到同一内存区域（内存复用），将峰值内存占用（Peak Memory Footprint）降低30～50%。

#### 2.4.2 分块推理（Tiled Inference）

对高分辨率输入（如12MP = $4000\times 3000$），将图像分割为带重叠的小块（推荐 $512\times 512$，重叠 $2\times$ 感受野像素）分别推理，再拼接结果。重叠区域用于消除块边界伪影（Tile Boundary Artifact）。分块推理将峰值内存从 $O(H \cdot W)$ 降至 $O(T^2)$，其中 $T$ 为块尺寸，通常降低内存占用8～16倍。

---

## §3 调参指南

### 3.1 量化精度保持策略

| 调参项 | 推荐设置 | 说明 |
|--------|----------|------|
| 量化方案 | QAT优于PTQ | ISP任务中QAT可将PSNR损失控制在0.2 dB以内 |
| QAT学习率 | FP32训练的1/10 | 避免过度调整破坏已收敛权重 |
| QAT迭代数 | 总训练的5～10% | 通常5000～20000步足够 |
| 浅层量化精度 | INT8 per-channel | 第1～3层对量化最敏感，不建议使用per-tensor |
| 激活范围统计 | EMA（指数移动平均） | 比min-max更稳健，避免异常值影响范围估计 |
| BN折叠时机 | QAT开始前完成 | 消除训练推理的BN状态不一致问题 |
| 输出层精度 | INT8或INT16 | 输出层量化误差直接影响最终图像质量 |

### 3.2 NPU友好性网络设计原则

在网络设计阶段应遵循以下原则以最大化NPU利用率：

- **通道数为8或16的倍数**：大多数NPU向量宽度为8或16，通道数对齐可避免填充（padding）浪费算力；
- **避免动态shape**：NPU通常要求静态输入尺寸，动态shape会触发CPU端的shape推断，引入额外延迟；
- **减少Gather/Scatter类算子**：内存访问不规则，NPU支持差，建议改为等价的卷积实现；
- **使用ReLU6替代Sigmoid/Tanh**：后者在NPU上通常以查表方式实现，精度损失较大且速度慢；
- **控制残差连接的跨层距离**：长跳跃连接需长时间保存中间特征图，消耗片上SRAM，建议跨层不超过4层。

### 3.3 延迟分析与瓶颈定位

使用Snapdragon Profiler（高通）、Rockchip NPU SDK Profiler或华为HiAI Foundation的性能分析工具，逐层分析以下指标：

1. **算子执行时间**：找出耗时Top10算子，重点检查是否有意外的CPU Fallback；
2. **内存带宽利用率**：若接近理论峰值（>90%），说明已成为带宽瓶颈，需优化特征图尺寸或引入更激进的下采样；
3. **NPU利用率**：若低于60%，通常说明调度开销或数据搬运是主要瓶颈，需优化算子融合。

---

## §4 部署局限与性能边界（Deployment Limitations）

### 4.1 量化色彩偏移（Quantization Color Shift）

**现象：** INT8 量化部署后，图像整体出现明显的色调偏移——偏暖（橙色调）或偏冷（蓝绿调），Macbeth ColorChecker 色卡测试 $\Delta E_{00}$ 退化 > 2 个单位。在 AWB 已校准的中性色块（灰色、白色）上偏差最为明显，可达 3–5 个 $\Delta E_{00}$ 单位。

**根本原因：** ISP 网络中 CCM（色彩校正矩阵）层权重的动态范围显著大于其他层（正负值混合，范围可达 $[-3, +3]$），而标准 per-tensor INT8 量化的步长 $\Delta = (W_{\max} - W_{\min}) / 255$ 约为 0.024，对量值在 $[-0.1, +0.1]$ 范围内的小权重精度严重不足（量化误差 / 权重值 > 20%），导致色彩矩阵变换后红/绿/蓝通道的相对增益偏离 FP32 参考值。Gamma/TMO 非线性层的量化误差在高光区域（$I > 0.7$）进一步被曲线斜率放大。

**诊断方法：** 用标准 Macbeth ColorChecker（24 色块）图像分别经 FP32 模型和 INT8 量化模型推理，计算各色块的 $\Delta E_{00}$；若灰色系（$L^* \in [20, 90]$, $|a^*| < 2$, $|b^*| < 2$）的 $\Delta E_{00}$ > 2，则存在量化色彩偏移；进一步检查 CCM 层的权重分布直方图，若 per-tensor 量化步长 > 0.02，确认为 CCM 精度不足。

**缓解策略：**
- 对 CCM、AWB 增益矩阵层单独保留 FP16 或 INT16 精度（混合精度量化，mixed-precision quantization），其余卷积层使用 INT8；
- 采用 per-channel 量化替代 per-tensor 量化：每个输出通道独立校准量化参数，消除通道间动态范围差异；
- 量化感知训练（QAT）时对 CCM 权重加 L2 正则（$\lambda = 1\text{e-}4$），压缩动态范围至 $[-1.5, +1.5]$，使 INT8 量化步长缩小约 2 倍，精度误差降至 5% 以下。

### 4.2 INT8 溢出块状色块（INT8 Overflow Blocking）

**现象：** 量化后图像中出现随机分布的 8×8 或 16×16 像素块状色彩异常——某些块呈现纯白（值截断到 255）或纯黑（值截断到 0），或出现与周围完全不同色调的单色块。在高亮度区域（高光）和极低亮度区域（暗部）触发频率最高。

**根本原因：** 当中间激活（activation）层的动态范围超出 INT8 校准范围（$[-128, 127]$ 的截断范围）时，溢出值被截断（clamp）到边界值，传播到后续层形成错误的"饱和"激活。典型触发路径：残差网络（ResNet block）中，若残差分支的输出分布宽尾（如激活值偶发 > 3$\sigma$），per-tensor 校准时选取的 clip range 使用 99th 百分位，遇到极端输入（强光边缘、高对比度文字）时激活超出 clip range，产生截断。

**诊断方法：** 在 NPU 推理时开启激活值溢出检查（如 Qualcomm SNPE 的 `--validate_data_tensors`），记录各层激活溢出率；若某层溢出率 > 0.1%，则该层是块状伪影的根源；用差分图（INT8 输出 - FP32 输出）可视化，若差分图出现局部大幅异常块，结合溢出日志定位具体层。

**缓解策略：**
- 在校准（calibration）时使用更宽松的 clip range（如 99.9th 百分位而非 99th），以减少极端值截断，代价是非极端值的量化精度略降；
- 对溢出率高的激活层单独保留 FP16，或在 QAT 中引入激活值范围约束（GELU/ReLU6 等有界激活），将激活范围限制在固定范围内；
- 在残差连接处添加激活归一化（activation normalization），避免残差积累导致的激活幅度持续增大。

### 4.3 量化精度降级（Quantization Accuracy Degradation）

**现象：** 从 FP32 量化为 INT8 部署后，PSNR 下降 > 1 dB，SSIM 下降 > 0.02，超出工程验收标准（通常要求 PSNR 损失 ≤ 0.3 dB）。在细纹理区域（布料、树叶）和边缘区域（文字边缘）质量退化尤为明显，出现纹理糊化或边缘毛刺。

**根本原因：** INT8 量化（8-bit 整数，256 量化级）相对 FP32（7 位有效数字）精度损失约 $10^{-4}$ 量级，但在 ISP 网络的深层特征中，量化误差通过多层乘累加（MAC）线性叠加，理论分析表明 $L$ 层全连接/卷积的误差累积约为单层误差的 $\sqrt{L}$ 倍（相互独立误差假设）。对于含 BN 层（Batch Normalization）的网络，BN 的缩放系数 $\gamma$ 可达 5–10，量化误差被放大等比倍；Depthwise Separable Conv 的 pointwise 步骤尤其敏感（每个通道权重数量少，量化步长相对于权重分布过粗）。

**诊断方法：** 逐层记录 FP32 与 INT8 推理的激活差异（Cosine Similarity），找出 Cosine Similarity < 0.99 的层，即为精度退化主要来源层；在这些层切换为 FP16 后重新测试 PSNR，若 PSNR 恢复到 FP32 的 ±0.1 dB 以内，则确认该层是精度瓶颈；对 BN 的 $\gamma > 3$ 的层单独标记为"高增益层"，优先保护。

**缓解策略：**
- 量化感知训练（QAT）：在 FP32 训练收敛后，插入"模拟量化"（fake quantization）节点在前向传播中引入量化误差，反向传播使网络适应量化噪声（通常微调 3–5 个 epoch）；
- BN 融合（BN-folding）后再量化：将 BN 的参数吸收进前一层卷积权重（$W' = \gamma/\sqrt{\sigma^2+\epsilon} \cdot W$），消除独立 BN 层的放大效应；
- 通道对齐填充（NPU 要求通道数为 16 的倍数）时，填充的零通道对应输出权重置零（mask），屏蔽填充通道引入的零点偏移误差。

### 4.4 常见伪影对照表

| 伪影类型 | 触发条件 | 典型表现 | 缓解方法 |
|---------|---------|---------|---------|
| 量化色彩偏移（Color Shift） | CCM 层 per-tensor INT8 精度不足 | 整体色调偏暖 / 偏冷，$\Delta E_{00}$ > 2 | CCM 层 FP16、per-channel 量化、QAT 正则 |
| 块状色块（Overflow Blocking） | 激活超出 clip range 截断 | 8×8 或 16×16 像素块状纯白或异色块 | 宽松 clip range（99.9%）、激活范围约束、FP16 保护层 |
| 精度降级（Accuracy Degradation） | BN 放大量化误差、多层累积 | PSNR 下降 > 1 dB，纹理糊化边缘毛刺 | QAT 微调、BN-folding、通道 padding mask |
| 分块边界伪影（Tiling Artifact） | 全局归一化、重叠不足 | 规则网格状亮度 / 色彩不连续 | 重叠 ≥ 1.5× 感受野、余弦窗混合、移除全局 BN |
| 热节流帧率波动（Throttling Jitter） | NPU 持续满负荷，温度限流 | 前几帧延迟正常，后续突增 2× | 预留 30% 算力余量、低功耗调度模式 |

---

## §5 评测方法

### 5.1 延迟基准测试规范

端侧延迟评测需在目标设备上进行，不可在PC端仿真替代。标准测试流程：

1. **热机预热**：连续推理50次后开始计时，避免JIT编译（Just-In-Time Compilation）缓存冷启动开销；
2. **多次取中位数**：推理100次取P50延迟，P95用于评估帧率稳定性抖动；
3. **频率锁定**：使用`adb shell`锁定CPU/GPU/NPU频率，消除DVFS（Dynamic Voltage and Frequency Scaling）影响；
4. **端到端延迟**：包括内存分配、数据搬运（Host→NPU→Host）、算子执行的总时间，而非仅算子执行时间。

### 5.2 图像质量评估基准

量化后的图像质量需在标准数据集上全面评估：

| 指标 | 工具/数据集 | 目标阈值 |
|------|-------------|----------|
| PSNR | MIT-Adobe FiveK、SIDD | 量化引入损失 ≤0.3 dB |
| SSIM | 同上 | 量化引入损失 ≤0.005 |
| $\Delta E_{00}$ | Macbeth ColorChecker色卡 | ≤0.5 色差单位 |
| 噪声功率谱（NPS） | ISO 15739标准 | 量化前后差异 ≤5% |
| 边缘MTF | ISO 12233分辨率图卡 | 量化前后MTF50差异 ≤2% |

### 5.3 功耗测试

使用Monsoon功率监控仪（外部精密电流计）或芯片内置功耗传感器（Android `BatteryStats` / `PowerManager`），记录：

- **平均功耗**：连续推理1分钟的平均值，用于评估续航影响；
- **峰值功耗**：最大瞬时功耗，用于评估热节流风险；
- **能效比（Performance per Watt）**：以PSNR增益（相对传统ISP的提升量）除以功耗（mW）衡量。

---

## §6 代码实现

### 6.1 轻量化ISP网络（PyTorch）

```python
import torch
import torch.nn as nn


class DepthwiseSeparableConv(nn.Module):
    """深度可分离卷积块，NPU友好设计：通道数对齐、ReLU6激活"""
    def __init__(self, in_ch, out_ch, stride=1):
        super().__init__()
        # 通道数对齐到8的倍数，满足NPU向量宽度要求
        out_ch = ((out_ch + 7) // 8) * 8
        self.dw = nn.Conv2d(in_ch, in_ch, 3, stride=stride,
                            padding=1, groups=in_ch, bias=False)
        self.pw = nn.Conv2d(in_ch, out_ch, 1, bias=False)
        self.bn = nn.BatchNorm2d(out_ch)
        self.act = nn.ReLU6(inplace=True)   # NPU友好激活，避免Sigmoid/Tanh

    def forward(self, x):
        return self.act(self.bn(self.pw(self.dw(x))))


class LightweightISPNet(nn.Module):
    """
    轻量化ISP网络，面向NPU部署。
    输入: (B, 4, H, W) RGGB格式RAW（pixel-unshuffle后）
    输出: (B, 3, H, W) sRGB图像
    """
    def __init__(self, in_ch=4, out_ch=3, base_ch=32):
        super().__init__()
        # 编码器：步长卷积降分辨率，减少全分辨率算子数量
        self.enc1 = DepthwiseSeparableConv(in_ch, base_ch)
        self.enc2 = DepthwiseSeparableConv(base_ch, base_ch * 2, stride=2)
        self.enc3 = DepthwiseSeparableConv(base_ch * 2, base_ch * 4, stride=2)
        # 瓶颈层（全部在1/4分辨率执行，算力开销最小）
        self.bottleneck = nn.Sequential(
            DepthwiseSeparableConv(base_ch * 4, base_ch * 4),
            DepthwiseSeparableConv(base_ch * 4, base_ch * 4),
        )
        # 解码器：双线性上采样（避免转置卷积的棋盘伪影和NPU不兼容问题）
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

### 6.2 QAT量化感知训练

```python
import torch.ao.quantization as tq  # torch.quantization 自 PyTorch 2.0 起已废弃


def prepare_qat_model(model: nn.Module) -> nn.Module:
    """
    准备QAT模型：融合BN并插入伪量化节点。
    注意：须在模型收敛后调用，通常在FP32训练完成后。
    """
    model.train()
    # Step 1: 折叠Conv-BN（必须在插入伪量化节点之前）
    model = tq.fuse_modules(model, [
        ['enc1.pw', 'enc1.bn', 'enc1.act'],   # PW-Conv + BN + ReLU6（有效的Conv-BN-ReLU融合模式）
        ['enc2.pw', 'enc2.bn', 'enc2.act'],   # DW-Conv层在本架构中无独立BN，不参与融合
        ['enc3.pw', 'enc3.bn', 'enc3.act'],
    ], inplace=True)
    # Step 2: 配置量化方案：权重per-channel，激活per-tensor（EMA统计）
    model.qconfig = tq.QConfig(
        activation=tq.default_fake_quant,
        weight=tq.default_per_channel_weight_fake_quant
    )
    # Step 3: 插入伪量化节点
    tq.prepare_qat(model, inplace=True)
    return model


def qat_train(model, train_loader, val_loader, epochs=5, lr=1e-4):
    """QAT微调训练循环"""
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
            # 梯度裁剪：QAT初期梯度可能不稳定
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

        # 验证阶段：关闭伪量化统计更新，仅做推理
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
    """导出INT8推理模型为ONNX（后续可转TFLite或SNPE格式）"""
    model.eval()
    # 冻结BN统计量（QAT训练完成后必须调用）
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
    print(f"INT8 ONNX模型已导出至 {save_path}")
```

### 6.3 分块推理与余弦窗混合

```python
import numpy as np


def cosine_window_2d(h: int, w: int) -> np.ndarray:
    """生成二维余弦窗，用于平滑块边界混合"""
    wy = np.hanning(h + 2)[1:-1].reshape(-1, 1)
    wx = np.hanning(w + 2)[1:-1].reshape(1, -1)
    return (wy * wx)[..., np.newaxis]   # (h, w, 1)


def tiled_inference(model, raw_image: np.ndarray,
                    tile_size: int = 512, overlap: int = 64,
                    device: str = 'cpu') -> np.ndarray:
    """
    分块推理：支持任意分辨率RAW图像的NPU推理。
    raw_image: shape (H, W, 4), dtype float32, RGGB通道顺序
    返回: shape (H, W, 3), dtype float32, sRGB输出
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

                # 零填充到tile_size（NPU要求静态shape）
                pad_h = tile_size - th
                pad_w = tile_size - tw
                tile_pad = np.pad(tile, ((0, pad_h), (0, pad_w), (0, 0)))

                # 推理
                inp = (torch.from_numpy(tile_pad)
                       .permute(2, 0, 1).unsqueeze(0).float().to(device))
                out = model(inp).squeeze(0).permute(1, 2, 0).cpu().numpy()

                # 裁剪到原始块大小，加权混合
                out_crop = out[:th, :tw]
                window = cosine_window_2d(th, tw)
                output[y:y_end, x:x_end]     += out_crop * window
                weight_map[y:y_end, x:x_end] += window

    return np.clip(output / (weight_map + 1e-8), 0.0, 1.0)
```

### 6.4 延迟与峰值内存Profiling

```python
import time
import torch


def profile_latency(model: nn.Module,
                    input_shape=(1, 4, 512, 512),
                    warmup: int = 50, repeat: int = 100,
                    device: str = 'cpu') -> dict:
    """
    模型延迟基准测试（遵循5.1节规范：预热→锁频→中位数统计）
    """
    model.eval().to(device)
    dummy = torch.randn(*input_shape).to(device)

    # 热机预热
    with torch.no_grad():
        for _ in range(warmup):
            _ = model(dummy)

    # 正式计时
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
    """统计模型峰值内存占用（CPU端估算）"""
    total = sum(p.numel() * p.element_size() for p in model.parameters())
    # 估算特征图内存：以输入张量大小的4倍近似（编解码结构经验值）
    input_bytes = 1
    for s in input_shape:
        input_bytes *= s
    input_bytes *= 4   # float32
    estimated_activation = input_bytes * 4
    print(f"权重内存: {total/1e6:.2f} MB | 激活估算: {estimated_activation/1e6:.2f} MB")
    return total + estimated_activation

# ─── 示例调用与输出 ───────────────────────────────────────
# 模型前向推理示例（RAW pack 输入：4通道RGGB → RGB输出）
import torch.nn as nn
model = LightweightISPNet()
x = torch.randn(1, 4, 256, 256)
out = model(x)
print(out.shape)
# 输出: torch.Size([1, 3, 256, 256])

```

---

## §7 2024–2025 年旗舰 SoC NPU 新进展

> **背景：** 骁龙 8 Gen3（2023Q4 量产）和天玑 9300（2023Q4 量产）在 NPU 架构上有重要迭代，直接影响 DL-ISP 的可行性边界。

### 旗舰 SoC NPU 算力横向对比（2023–2025）

| 芯片 | NPU 单元 | INT8 峰值算力 | 制造商 | 数据来源 |
|------|---------|-------------|--------|---------|
| 骁龙 8 Gen 3 | Hexagon HTP（790）| **~34 TOPS** | 高通 | 第三方估算（cpu-monkey）；官方仅称"HTP提升98%"，未公布整数 |
| 骁龙 8 Elite | Hexagon HTP（NPU Gen 3）| **~49 TOPS** | 高通 | 第三方估算；官方未公布手机版独立TOPS |
| Apple A17 Pro | Apple Neural Engine | **35 TOPS** | 苹果 | 苹果官方发布会数据（iPhone 15 Pro，2023） |
| Kirin 9000s | Da Vinci NPU（Big+Tiny）| **~20 TOPS** | 海思/华为 | 第三方综合估算；官方未公布 |
| 天玑 9300 | APU 790 | **~33 TOPS** | 联发科 | 第三方估算（cpu-monkey）；官方未公布整数 |

> **注意**：高通官方从未对手机版骁龙芯片公布独立 NPU TOPS 整数（详见附录 C §C.9）；苹果 A17 Pro 的 35 TOPS 是官方发布数据；其余数值均为第三方测评综合估算，仅供参考。各平台 TOPS 定义（INT8 vs INT4 混合 vs 综合AI Engine）口径不统一，跨平台直接比较需谨慎。

### 7.1 骁龙 8 Gen3 Hexagon NPU

**算力提升：** 骁龙 8 Gen3 的 Hexagon NPU 峰值算力约 **34 TOPS**（INT8，第三方估算；高通官方 Snapdragon 8 Gen 3 Mobile Platform Product Brief 仅称《Hexagon NPU 提升 98%》，未公布独立 TOPS 整数，详见附录C §C.9），而 8 Gen2 Hexagon HTP 约 **18 TOPS**（官方）；以总 AI Engine 口径（CPU+GPU+NPU 联合基准）计，8 Gen2 约 34 TOPS，提升约 98%。注意 HTP 单元独立 TOPS 与总 AI Engine TOPS 为不同口径，不可混用。

**架构关键改进：**

| 改进点 | 8 Gen2 | 8 Gen3 | ISP 影响 |
|--------|--------|--------|---------|
| INT8 算力 | 约 **18 TOPS**（Hexagon 780 HTP单元，官方；含CPU+GPU综合约34 TOPS） | 约 **34 TOPS**（第三方估算，附录C §C.9）| 轻量 DL-ISP 实时处理窗口扩大 |
| FP16 算力 | ~17 TFLOPS | ~22.5 TFLOPS | 扩散模型 FP16 推理延迟降低约 25% |
| 片上 SRAM（TCM） | ~8 MB（Hexagon 780，Chips and Cheese） | ~4 MB（Hexagon 790 Scalar Accelerator，工程实测推断；第三方来源，官方未公开） | 8 Gen3 片上可用容量实际缩小，tile 重叠边界策略不变 |
| Sparse 加速 | 无 | **2× 稀疏加速** | 配合权重剪枝可额外获得 2× 效果，轻量模型收益显著 |
| INT4 支持 | 有限 | **原生 INT4** | W4A8 量化方案（权重 4bit，激活 8bit）工程可行 |

**ISP 工程意义：** 约34 TOPS（第三方估算）的 INT8 算力下，参数量约 17M 的 DiffIR-S 型网络在 DDIM 20 步配置下，512² 推理延迟估算降至约 20–40s（仍不适合实时，但后台异步处理体验明显改善）。轻量 CNN（如 Zero-DCE++ 0.49K 参数）实时处理已进入亚毫秒级别（< 0.5ms @ 720p）。

**SNPE/QNN 新特性（配套 Snapdragon Neural Processing SDK v2.x）：**
- 原生支持 INT4/FP8 量化方案，无需手动 workaround
- 动态形状（Dynamic Shape）支持改善，可处理非固定分辨率输入（需 Hexagon NN 后端）
- 算子覆盖扩展：Attention（SDPA，Scaled Dot-Product Attention）、LayerNorm、GeLU 原生支持，减少 CPU Fallback

### 7.2 天玑 9300 APU 790

**算力提升：** 天玑 9300 的 APU 790 峰值算力约 **33 TOPS**（INT8，第三方评测综合估算；联发科官方 Product Brief 未公布独立整数 TOPS，33 TOPS 为 cpu-monkey 等第三方来源），与骁龙 8 Gen3 的约 34 TOPS 处于同一量级。

**架构关键改进：**

| 改进点 | 天玑 9200（APU 690）| 天玑 9300（APU 790）| ISP 影响 |
|--------|---------------------|---------------------|---------|
| INT8 算力 | ~4.8 TOPS | **~33 TOPS**（第三方估算） | DL-ISP 推理预算跨代扩大约 7× |
| INT4 支持 | 部分 | **完整 INT4** | 结合 W4A8，内存减少约 70% |
| 大模型推理 | 无官方支持 | **支持 ≤13B LLM**（INT4）| LLM 辅助 ISP 调参在旗舰机上具备硬件基础 |
| 内存带宽 | ~77 GB/s | **~100 GB/s**（LPDDR5T）| 大特征图搬运瓶颈改善约 30% |
| 异构调度 | 基础 | **NPU+CPU 协同调度**优化 | CPU Fallback 开销降低 |

**NeuroPilot 新特性（天玑 9300 配套 SDK）：**
- INT4 量化推理正式生产就绪，提供 INT4 校准工具
- 支持 LoRA 轻量微调模型的端侧快速加载（面向个性化 ISP）
- 增加 Transformer Attention 算子的原生 APU 支持

### 7.3 海思昇腾 ISP NPU（华为 Kirin 系列）

华为麒麟系列 SoC 中的 ISP NPU 与通用昇腾架构在设计目标上存在显著差异，其 ISP 加速单元更强调与 ISP 硬件流水线的深度耦合，而非通用矩阵乘法吞吐量。

**架构特点**：
- 麒麟 9000/9010（Kirin 9000s）搭载独立的 Da Vinci 架构 NPU，分为 Big/Tiny 两核组合
- ISP NPU 与 ISP 硬件通过专用 DMA 通道直连，RAW 域数据无需经过 DDR 往返（与高通 Hexagon 的内存拷贝模型不同）
- 推理框架：HiAI Foundation（新版）/ HiAI DDK（老版），对外接口为 `.om` 格式模型（类似 ONNX 但华为专有）

**算子支持限制（工程关键）**：

| 算子 | 支持状态 | 替代方案 |
|------|---------|---------|
| Deformable Conv | 不支持（截至 HiAI 6.0） | 用标准 3×3 Conv + 空间注意力近似 |
| PixelShuffle（大因子） | 4× 以上性能下降显著 | 拆分为 2× + 2× 两阶段 |
| Dynamic Shape | 仅支持有限档位 | 固定分辨率模型 |
| GroupNorm | 不支持 | 替换为 LayerNorm 或 BN |
| SiLU/GELU | 需查版本兼容表 | 改为 ReLU/LeakyReLU |

**量化工具链**：
- HiAI Foundation 支持 W8A8（权重/激活均 INT8）量化，通过 `hiai_model_builder` 接口导出
- QAT 训练框架对接：需将 PyTorch 模型先转 ONNX，再用华为 `atc`（Atlas Tensor Compiler）工具做量化感知编译
- 典型转化链：PyTorch → ONNX → `.om` 模型（通过 `atc --framework=5`）

**与高通/联发科平台的关键差异**：

| 维度 | 高通 Hexagon HTP | 联发科 APU | 海思 NPU |
|------|----------------|-----------|---------|
| 算子定制 | 支持 HVX intrinsics | C-Model 扩展算子 | .om 算子库，扩展受限 |
| ISP 直连 | 通过 Spectra 内存共享 | 通过 MDLA 内存共享 | DMA 直连，延迟最低 |
| 开发文档 | SNPE/QNN 公开完整 | NeuroPilot SDK 公开 | HiAI 文档需注册开发者 |
| 量产可及性 | 全球主流旗舰 | 国产旗舰主流 | 华为/荣耀机型专用 |

> **工程师手记**：在华为平台上部署 ISP AI 模块，最常遇到的坑是 deformable conv 不支持——Restormer 和 NAFNet 均有此类算子，需要在网络设计阶段就规避，而不是等到 `atc` 报错时再反工。另一个高频坑是 `.om` 模型的 dynamic shape 支持薄弱，ISP 场景中分辨率随拍照模式切换（1080p 预览 vs 4K 拍照），需要预先编译多档位模型并在 HAL 层做切换逻辑。

*参考*：华为开发者社区 HiAI DDK 文档；Kirin 990/9000 NPU 架构白皮书（2020–2022）；华为 CVPR 2022 海报论文 ISP NPU 优化相关工作。

### 7.4 2024–2025 年端侧 DL-ISP 能力边界更新

基于新 SoC 能力，更新可行性判断（以旗舰 SoC 为基准）：

| DL-ISP 任务 | 2022 年旗舰（骁龙 8 Gen1） | 2023–2024 旗舰（8 Gen3 / 天玑 9300）| 趋势 |
|------------|--------------------------|--------------------------------------|------|
| 轻量 CNN 降噪（Zero-DCE++ 类）| 实时（< 5ms） | 亚毫秒（< 1ms）| 普及化 |
| 中等 CNN 降噪（SNR-Aware 类，720p）| ~110ms（勉强可用）| ~25ms（体验良好）| 从可用到优秀 |
| 轻量 Transformer ISP（< 5M 参数）| ~80–150ms | ~30–60ms | 进入实用窗口 |
| 扩散模型（DDIM 20 步，512²）| 分钟级，不可用 | ~20–60s（后台可用）| 后台处理可行 |
| LCM 4 步推理（512²）| ~5–15 分钟 | ~5–15s | 后台快速处理 |
| W4A8 量化大模型（1–7B 参数 LLM）| 不可用 | ~1–5 token/s（文字，非图像）| 语言辅助调参初步可行 |

**关键结论（2025 年）：**
1. **轻量 CNN LLIE/降噪**（< 5M 参数，INT8）在旗舰机上已实现毫秒级实时处理
2. **中等 Transformer ISP**（5–20M 参数）进入 50ms 以内实用窗口
3. **扩散模型**在手机端仍以后台异步处理为主，实时化需等待新一代 NPU（> 100 TOPS INT8 级别）或更激进的步数压缩（1–2 步高质量采样）
4. **W4A8 量化**成为旗舰手机 DL-ISP 部署的主流方案，兼顾内存效率与精度

> **工程推荐（手机ISP场景）：** 如果是新项目从零开始选量化方案，从 QAT + per-channel INT8 + BN-folding 开始，而不是先做 PTQ 再查问题——PTQ 在 ISP 任务上精度损失超过 0.5 dB 的情况极为常见，排查原因反而费时。CCM 相关层（动态范围大、小权重多）单独保留 FP16，其余 INT8，这个混合精度组合几乎不增加部署复杂度，但可将色差 ΔE₀₀ 从 3–5 单位降回 1 以内。骁龙 8 Gen3 以上机型优先测试 W4A8，约34 TOPS INT8 算力下（第三方估算）中等 Transformer ISP 实测延迟普遍在 30–60ms，比 INT8 再降 30%。

> ⚠️ **说明：** 上述算力数字来自高通/联发科官方发布会资料（公开来源）。延迟估算为基于模型规模和算力的理论推算，实际值受内存带宽、算子融合程度、驱动版本等因素影响，可能有 2–3 倍差异。精确 benchmark 须在目标设备上实测。

---

> **工程师手记：INT8 量化不是免费的午餐，也不是你想避开就能避开的**
>
> **INT8 量化的质量损失不是固定的——它和你量化的哪一层有关系。** 全网络一刀切 INT8，Batch Normalization 融合前后的激活层是最敏感的地方（尤其是 Softmax 和 Sigmoid 在边界值处），通常会损失 0.3–0.8 dB PSNR。但如果分层量化，把对精度敏感的前两层和最后一层保留 FP16，只把中间层 INT8，质量损失可以降到 0.1 dB 以内。高通 Hexagon NPU 的量化工具（SNPE Quantizer）支持逐层敏感性分析（Layer Sensitivity Analysis）——先跑一遍全网络量化，找出 PSNR 损失最大的几层，只把那几层改回 FP16，这是工程上的标准流程，不是直觉猜哪层敏感。
>
> **高通 Hexagon DSP 和联发科 APU 的精度特性不同，同一个 INT8 模型在两个平台上质量可能差 0.5–1.5 dB。** 这不是哪个平台"差"——是量化粒度和数值对齐方式不同。Hexagon 默认使用对称量化（symmetric quantization，零点 = 0），APU 支持非对称量化（asymmetric，零点可以偏移）。对于激活值分布明显偏向单侧的层（如 ReLU 后的激活大多数是正数），非对称量化精度更好。工程上的含义是：在高通平台量化得很好的模型，直接拿到 MTK 平台可能有可见的质量退化，需要针对 APU 重新跑量化校准（Calibration Dataset 是同一套，但量化参数需要重新搜索）。
>
> **移动端 NPU 的内存带宽，比算力更容易成为瓶颈。** 一个典型的 3× 超分网络在 4K 分辨率下，中间层 feature map 的大小是输入的 4–16 倍，需要频繁在片上 SRAM 和片外 LPDDR 之间搬运。高通 Snapdragon 8 Gen 3 的 Hexagon NPU 有约 4MB 的 Scalar Accelerator 片上缓存，如果网络的中间层 feature map 超过这个大小，就需要 tile processing（分块处理），引入额外的 halo（分块边界的 overlap 数据），实测延迟会比理论峰值高 30–50%。设计 ISP 的 DL 模块时，控制单层 feature map 大小在 2MB 以内（配合 tile）是保持 NPU 高效率的重要工程约束。
>
> *参考：OPPO 研究院《MariSilicon X NPU 架构与模型部署实践》公众号，2024；vivo 影像算法研究部《V2 芯片 AI-ISP 量化部署》公众号，2024；Qualcomm SNPE 量化工具文档（公开版），2024。*

---

## 插图

![model compression methods](img/fig_model_compression_methods_ch.png)

*图1. 模型压缩方法分类示意*

![npu deployment tradeoff](img/fig_npu_deployment_tradeoff_ch.png)

*图2. NPU部署精度与速度权衡关系*

![npu power efficiency](img/fig_npu_power_efficiency_ch.png)

*图3. NPU功耗效率对比*

![quantization accuracy tradeoff](img/fig_quantization_accuracy_tradeoff_ch.png)

*图4. 量化精度与准确率权衡关系*



---
![on device npu deploy](img/fig_on_device_npu_deploy_ch.png)

*图5. 端侧NPU部署流程*

![samsung npu architecture](img/fig_samsung_npu_architecture_ch.png)

*图6. 三星NPU架构示意*

---

## 习题

**练习 1（理解）**
INT8 量化相比 FP32 将权重和激活值从 32 位压缩到 8 位，理论上可减少 4× 内存占用和 2–4× 推理延迟，但会引入量化精度损失。对于图像复原任务（去噪/超分），INT8 量化通常导致 PSNR 损失约 0.3–0.8 dB。请分析：(a) 量化精度损失为何在图像复原任务中比分类任务更敏感（从输出类型和损失函数角度分析）；(b) 对称量化（symmetric）和非对称量化（asymmetric）的差异，以及哪种更适合去噪网络的激活值分布；(c) 混合精度量化（部分层 INT8，部分层 FP16）的典型策略是什么，哪些层通常需要保留更高精度。

**练习 2（分析）**
不同层对量化精度损失的敏感程度不同，通常网络的最后一层（输出层）对量化最为敏感。请分析：(a) 为什么输出层量化误差比中间层量化误差对最终 PSNR 的影响更大（从误差累积和输出范围的角度分析）；(b) 去噪网络中残差连接（residual connection）在量化时的特殊挑战（两路数值范围可能差异较大，影响量化粒度选择）；(c) 高通 SNPE 和联发科 NeuroPilot 在处理量化敏感层时的典型工程做法（如逐层量化校准、敏感层豁免）有何异同（基于公开文档分析）。

**练习 3（编程）**
用 PyTorch 实现一个简单的 INT8 线性量化函数（Post-Training Quantization，PTQ 的基础操作）。输入：FP32 张量 x，量化位宽 bits=8，输出：量化后再反量化的 FP32 张量（模拟量化误差）。步骤：计算 x 的 min/max，确定缩放因子 scale 和零点 zero_point，量化为 int8，再反量化回 float32。在一个简单卷积层的权重上运行，计算量化前后权重的 SNR（信噪比）和最大绝对误差。

**练习 4（工程决策）**
将一个 SIDD 去噪模型（NAFNet 轻量版，FP32 PSNR = 39.8 dB）部署到骁龙 8 Gen 3 NPU，目标延迟 < 15ms（1080p 输入），目标量化精度损失 < 0.5 dB PSNR。请给出量化部署的工程步骤：(a) 使用高通 SNPE 量化工具链的基本流程（模型转换、校准数据准备、量化配置）；(b) 如果 INT8 全网量化导致 PSNR 损失 0.9 dB（超出目标），如何通过敏感层分析定位导致损失最大的层并将其保留为 FP16；(c) 在 INT8 量化后延迟仍为 18ms 时，可以通过哪些网络结构裁剪（减少通道数、删除层）进一步优化而不超出 0.5 dB PSNR 损失预算。

## 推荐开源仓库

> 本章内容以概念和理论为主；以下开源仓库提供了对应算法的参考实现，建议配合阅读。

| 仓库 | 说明 | 适用内容 |
|------|------|---------|
| [MNN](https://github.com/alibaba/MNN) | 阿里巴巴出品的轻量级移动端推理框架，支持 ARM/NPU/GPU，提供量化工具和 Android/iOS 部署示例 | 第3节（移动端推理框架） |
| [ncnn](https://github.com/Tencent/ncnn) | 腾讯开源的高性能移动端神经网络前向框架，纯 C++ 无依赖，支持骁龙 GPU/DSP 后端 | 第3节（移动端推理框架） |
| [TensorFlow Lite](https://github.com/tensorflow/tensorflow/tree/master/tensorflow/lite) | Google TFLite，支持 Android NNAPI 委托（含高通 HTA/HTP），量化工具链成熟 | 第4节（量化工具链） |
| [AIMET](https://github.com/quic-ai/aimet) | 高通 AI Model Efficiency Toolkit，提供 PTQ/QAT/剪枝工具，与 SNPE 深度集成 | 第4节（量化精度优化） |

## 参考文献

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

## §8 术语表

| 英文缩写 | 中文全称 | 简要说明 |
|----------|----------|----------|
| NPU | 神经网络处理单元 | 专用于深度学习推理的手机芯片模块 |
| QAT | 量化感知训练 | 训练时模拟量化误差以减少精度损失的方法 |
| PTQ | 训练后量化 | 无需重训练的快速量化方法，精度损失较大 |
| STE | 直通估计器 | 绕过不可微分舍入操作的梯度近似技巧 |
| TDP | 热设计功率 | 芯片持续工作时最大散热功率 |
| DW-Conv | 深度可分离卷积 | 将标准卷积分解为逐深度与逐点卷积的轻量结构 |
| NAS | 神经架构搜索 | 自动化设计神经网络结构的方法 |
| MAC | 乘加运算 | 深度学习的基本计算单元，数量衡量网络计算量 |
| SRAM | 静态随机存储器 | 芯片片上高速缓存，容量小但速度快 |
| DRAM | 动态随机存储器 | 手机主内存（LPDDR系列），容量大但速度慢 |
| DVFS | 动态电压频率调整 | 根据负载动态调节芯片频率以平衡性能与功耗 |
| HVX | Hexagon向量扩展 | 高通Hexagon DSP的SIMD向量指令集 |
| HTP | Hexagon张量加速器 | 高通Hexagon NPU核心，负责矩阵运算加速 |
| ONNX | 开放神经网络交换格式 | 跨框架模型交换标准 |
| TFLite | TensorFlow Lite | Google面向移动端的轻量化推理框架 |
| SNPE | Snapdragon Neural Processing Engine | 高通面向Snapdragon平台的推理SDK |
| SE | 压缩激励模块 | 基于通道注意力的特征增强机制 |
| NPS | 噪声功率谱 | 衡量图像噪声频率特性的客观指标（ISO 15739） |
| MTF | 调制传递函数 | 衡量光学/图像系统分辨率的标准指标 |
