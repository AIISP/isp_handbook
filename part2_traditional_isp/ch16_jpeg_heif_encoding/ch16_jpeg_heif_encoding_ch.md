# 第二卷第16章：图像编码输出流水线（JPEG/HEIF/AVIF）

> **流水线位置：** ISP 流水线最终输出阶段 — 色调映射与色彩空间转换之后，写入文件存储之前；编码器通常以独立硬件模块（JPEG HW Encoder / HEVC Encoder）形式集成
> **前置章节：** 第二卷第09章（色彩空间转换与输出）、第二卷第19章（HDR 显示信号链）、第二卷第20章（视频色彩元数据）
> **读者路径：** ISP 图像质量工程师、相机 HAL/Framework 工程师、多媒体编解码工程师

> **摘要**：ISP流水线的最终环节是将处理后的图像压缩编码并写入存储。本章系统介绍JPEG、HEIF/HEIC（基于HEVC）和AVIF（基于AV1）三种主流图像编码格式的编码原理、压缩效率对比、HDR编码方案、Android Camera2 API的输出格式支持，以及编码质量与文件大小的权衡策略。

---

## §1 基本原理 (Theory)

### 1.1 JPEG编码流水线

JPEG从1992年沿用至今 **[1]**，三十年没被替代的原因不是它有多好，而是硬件支持太广泛、兼容性成本太低。HEIF压缩效率是JPEG的两倍，但直到2017年苹果强推iOS 11才开始普及——编码格式的替换阻力不在算法，在生态。理解JPEG的工作方式，既是理解压缩伪影的基础，也是理解为什么HEIF能做到更好的出发点。

**Step 1：色彩空间转换（RGB → YCbCr）**

JPEG将图像从RGB转换为YCbCr（BT.601），将亮度（Y）与色度（Cb, Cr）分离，为后续色度子采样做准备：

$$
\begin{bmatrix} Y \\ C_b \\ C_r \end{bmatrix} = \begin{bmatrix} 0.299 & 0.587 & 0.114 \\ -0.168736 & -0.331264 & 0.5 \\ 0.5 & -0.418688 & -0.081312 \end{bmatrix} \begin{bmatrix} R \\ G \\ B \end{bmatrix} + \begin{bmatrix} 0 \\ 128 \\ 128 \end{bmatrix}
$$

**Step 2：色度子采样（Chroma Subsampling）**

利用人眼对色度分辨率不敏感的特性，对Cb/Cr通道进行下采样：

- **4:4:4**：无下采样，色度分辨率与亮度相同，文件最大，色彩最准确。
- **4:2:2**：水平方向色度下采样2:1，垂直方向不变，文件约减小33%。
- **4:2:0**：水平和垂直各下采样2:1，文件约减小50%，为JPEG默认模式。

4:2:0子采样在色彩边缘处会导致色度偏移（Color Bleeding），尤其在高对比色彩边缘（如红色文字在白底上）明显。

**Step 3：DCT变换（Discrete Cosine Transform）**

将图像划分为8×8像素块，对每个块执行二维DCT-II变换：

$$
F(u, v) = \frac{1}{4} C(u) C(v) \sum_{x=0}^{7} \sum_{y=0}^{7} f(x, y) \cos\frac{(2x+1)u\pi}{16} \cos\frac{(2y+1)v\pi}{16}
$$

其中 $C(0) = 1/\sqrt{2}$，$C(u) = 1$（$u > 0$）。DCT将空间域的像素值转换为频域系数，能量主要集中在低频（左上角）系数。

**Step 4：量化（Quantization）**

DCT系数除以量化矩阵（Quantization Matrix）并取整，实现有损压缩：

$$
F_Q(u, v) = \text{round}\left(\frac{F(u, v)}{Q(u, v)}\right)
$$

（注：ITU-T T.81 标准规定截断取整（truncation towards zero），多数编码器实现为四舍五入（round to nearest）以提升 PSNR，两者在高压缩率时差异可达 1 个量化级。）

量化矩阵 $Q$ 由质量因子（Quality Factor, QF）控制：
- QF越低，$Q(u,v)$ 越大，高频系数越多被量化为零，压缩率越高，质量越低。
- QF=75 时，亮度量化步长（低频）约为8，高频约为50。
- QF=50（参考量化矩阵的基准）：亮度通道 $Q(0,0) = 16$，$Q(7,7) = 99$。

JPEG标准亮度量化矩阵（QF=50基准）：

$$
Q_{\text{luma}} = \begin{bmatrix}
16 & 11 & 10 & 16 & 24 & 40 & 51 & 61 \\
12 & 12 & 14 & 19 & 26 & 58 & 60 & 55 \\
14 & 13 & 16 & 24 & 40 & 57 & 69 & 56 \\
14 & 17 & 22 & 29 & 51 & 87 & 80 & 62 \\
18 & 22 & 37 & 56 & 68 & 109 & 103 & 77 \\
24 & 35 & 55 & 64 & 81 & 104 & 113 & 92 \\
49 & 64 & 78 & 87 & 103 & 121 & 120 & 101 \\
72 & 92 & 95 & 98 & 112 & 100 & 103 & 99
\end{bmatrix}
$$

**Step 5：Z字形扫描与游程编码**

按Z字形（Zigzag）顺序读取量化后的DCT系数（从低频到高频），高频零系数形成长零游程，使用游程编码（RLE）高效表示。

**Step 6：Huffman熵编码（Entropy Coding）**

对游程编码后的符号使用**Huffman熵编码**，分配短编码给高频出现的符号，进一步压缩比特流。JPEG标准定义两种熵编码方式：**Huffman编码**（基准/顺序/渐进模式均支持，是实际中唯一广泛部署的方案）和**算术编码**（Arithmetic Coding，JPEG标准可选，因历史专利原因几乎不被使用）。渐进式（Progressive）与基准式（Baseline）是扫描方式的区别，两者均使用Huffman编码。

### 1.2 JPEG压缩感知影响

**色度子采样色彩渗透（Color Bleeding）**
- 4:2:0下采样后，Cb/Cr在2×2像素块内取均值，导致颜色边缘处（如红色文字）出现半像素级色彩偏移。
- 在锐利色彩边缘（如信号灯、旗帜），可见颜色"晕染"宽度约1～2像素。

**DCT方块效应（Blocking Artifact）**
- QF < 70 时，8×8 DCT块边界处出现可见的方块状不连续，低频背景区域（如天空）最为明显。
- 量化步长越大，块间不连续越强。

**振铃效应（Ringing Artifact）**
- 高频系数被量化为零后，在锐利边缘附近产生类Gibbs振荡（吉布斯现象），表现为边缘两侧的亮暗条纹。

### 1.3 HEIF/HEIC编码

**HEIF**（High Efficiency Image File Format，高效图像文件格式）由MPEG制定，ISO/IEC 23008-12:2017正式发布 **[2]**，是一种**容器格式**，可封装多种编解码器的压缩数据，最常见的实现使用HEVC（H.265）**[3]** 视频编解码器进行帧内编码。**HEIC**（High Efficiency Image Codec）是Apple对HEIF容器的特定实现，专指使用H.265/HEVC帧内编码的图像文件（.heic扩展名），是iOS 11起iPhone的默认拍照格式；HEIF容器本身是通用标准，理论上可承载AV1（即AVIF）等其他编解码器。

**关键特性**

| 特性 | HEIF/HEIC | JPEG |
|------|-----------|------|
| 比特深度 | 8/10/12 bit | 8 bit |
| 色彩范围 | SDR / HDR | SDR |
| Alpha通道 | 支持 | 不支持 |
| 多帧序列 | 支持（Live Photo等） | 不支持 |
| 深度图 | 支持（辅助图像） | 有限支持（EXIF） |
| 典型压缩率 | JPEG的约2× | 基准 |
| 编码延迟 | 软件50-200ms，硬件20ms | 硬件5ms |

**HEVC编码核心技术**
- **CTU（Coding Tree Unit）** 替代JPEG的8×8块，CTU大小可达64×64，自适应块划分。
- **帧内预测（Intra Prediction）** 35种预测模式（HEVC）/67种（VVC），利用相邻已编码像素预测当前块，比JPEG DCT更高效。
- **变换（Transform）** DCT-II 用于绝大多数块（4×4至32×32）；DST-I 仅用于4×4亮度帧内预测块（HEVC规范§7.5.5）。注：DST-VII 是 VVC/H.266（2020年）多变换选择（MTS）引入的变换类型，HEVC 并未使用 DST-VII。

**iOS采用HEIF的时间线**
- WWDC 2017：iOS 11默认启用HEIF拍照（需要A10及以上处理器的Hardware HEVC编码器）。
- 兼容性考虑：分享时自动转换为JPEG。

**Android支持**
- Android 10（API 29）起，MediaCodec支持HEVC硬件编解码。
- Android 11起，`ImageFormat.HEIF` 在Camera2中可查询是否支持。

### 1.4 AVIF编码

**AVIF**（AV1 Image File Format）由Alliance for Open Media（AOMedia）于2019年发布 **[5]**，基于AV1视频编解码器（开源、免版税）**[4]**。

**与HEIF/HEIC的对比**

| 特性 | AVIF | HEIF/HEIC |
|------|------|-----------|
| 编解码器 | AV1 | HEVC |
| 开源/免版税 | 是 | 否（HEVC专利费） |
| 压缩效率 | 略优于HEIF（典型场景） | 优于JPEG 2× |
| 编码速度 | 软件 200–1000ms（12MP）/ 硬件 AV1 编码器 30–80ms | 硬件 HEVC 约 20ms（12MP） |
| 硬件支持 | 增长中（骁龙 8 Gen 3 / Dimensity 9300 起内置 HW AV1 编码器）| 成熟（骁龙 865+ / Dimensity 1000+）|
| 解码硬件 | 手机端 2021+ 机型大多支持 HW AV1 解码 | 广泛支持 |
| 浏览器支持 | Chrome 85+, Firefox 93+, Safari 16+ | Safari, iOS |

> **ISP 集成说明**：截至 2024 年，Android Camera2 中 AVIF 编码通过 `ImageFormat.AVIF`（Android 12 API 32+）或 `MediaCodec` 软件编码器路径实现；高通骁龙 8 Gen 3（SM8650）和 MTK Dimensity 9300 均内置 AV1 硬件编码加速，将 12MP AVIF 编码延迟从软件的 500–1000ms 压缩至 30–50ms，达到量产实用门槛。与 HEVC 相比，相同质量条件下 AVIF 文件体积约小 20–30%，但同等画质 AVIF 编码延迟仍比 HEVC 高约 50%（硬件路径对比）。

**AV1核心优势**
- 更精细的量化参数控制：AV1的量化索引（q_index）范围为0~255，共256个离散级别；HEVC量化参数（QP）范围为0~51，共52个离散级别。
- 更多帧内预测模式（56种角度预测 + 非方向预测；AV1将8个基础方向各细化7个步长角度得到56种角度模式，VVC才有67种）。
- 基于分区的滤波（Loop Filter、CDEF、Restoration Filter），减少方块效应和振铃效应。

### 1.4b JPEG量化表详解：QF=85的实际量化矩阵

> **P1补充**：量化表是JPEG有损压缩的核心，理解QF参数到量化步长的映射对调参至关重要。

#### QF到量化矩阵的转换公式（IJG/libjpeg标准）

libjpeg（IJG标准实现）使用以下公式将质量因子QF映射到缩放比例 $S$：

$$S = \begin{cases} \dfrac{5000}{\text{QF}} & \text{QF} < 50 \\[8pt] 200 - 2 \cdot \text{QF} & \text{QF} \geq 50 \end{cases}$$

每个量化步长由基准矩阵（QF=50时的标准矩阵）缩放得到：

$$Q_{ij} = \max\!\left(1,\ \min\!\left(255,\ \left\lfloor \frac{Q_{ij}^{\text{base}} \cdot S + 50}{100} \right\rfloor\right)\right)$$

#### QF=85的亮度量化矩阵（实际值）

由 $S = 200 - 2 \times 85 = 30$ 代入基准矩阵：

$$Q_{\text{luma}}^{85} = \begin{bmatrix}
 5 &  3 &  3 &  5 &  7 & 12 & 15 & 18 \\
 4 &  4 &  4 &  6 &  8 & 17 & 18 & 17 \\
 4 &  4 &  5 &  7 & 12 & 17 & 21 & 17 \\
 4 &  5 &  7 &  9 & 15 & 26 & 24 & 19 \\
 5 &  7 & 11 & 17 & 20 & 33 & 31 & 23 \\
 7 & 11 & 17 & 19 & 24 & 31 & 34 & 28 \\
15 & 19 & 23 & 26 & 31 & 36 & 36 & 30 \\
22 & 28 & 29 & 29 & 34 & 30 & 31 & 30
\end{bmatrix}$$

**关键观察**：
- DC分量（左上角 $Q_{00} = 5$）量化步长小，亮度信息高保真（由 $S=30$ 代入基准值16：$\lfloor(16\times30+50)/100\rfloor=5$）
- 高频分量（右下角 $Q_{77} = 30$）步长中等，QF=85下高频仍有明显压缩
- 相比QF=50（$Q_{00} = 16$，$Q_{77} = 99$），QF=85的量化步长约为其 $5/16 \approx 0.31$ 倍（低频）到 $30/99 \approx 0.30$ 倍（高频）

#### 量化表优化（自定义量化表）

标准基准矩阵并非最优。针对特定场景的量化表优化（Custom Quantization Table）可以在相同文件大小下获得更好的感知质量：

**感知优化量化表（基于CSFD视觉权重）**：
- 对人眼敏感的中频（DCT系数 $u+v = 2$～$5$）降低步长（提高精度）
- 对人眼不敏感的高频对角线区域（$u+v > 8$）增大步长（更激进压缩）
- 工具：`MozJPEG`（Mozilla）的感知优化量化表在相同VMAF下文件约小 5–15%

**平台实现**：libjpeg-turbo 支持 `jpeg_add_quant_table()` 自定义量化表；Android Camera2 的 `CaptureRequest.JPEG_QUALITY` 底层调用 HAL JPEG编码器，厂商HAL可注入自定义量化表（高通 Spectra JPEG 硬件编码器支持可编程量化矩阵）。

### 1.4c HEIF Gain Map与Apple Adaptive HDR

> **P1补充**：HEIF的HDR能力不仅限于10bit编码，Apple从iOS 17/macOS Sonoma起引入了基于**Gain Map**的Adaptive HDR方案，是当前移动端HDR图像的重要技术方向。

#### Gain Map原理

Gain Map（增益图）方案将一张图像同时携带SDR和HDR两套显示所需的信息，核心结构为：

```
HEIF容器
  ├── 主图像（Primary Image）：标准SDR/SDR-like编码（BT.709/sRGB，8bit）
  └── Gain Map图像（Auxiliary Image）：单通道增益图，低分辨率（可下采样到1/4）
      存储每像素的HDR/SDR亮度比值（对数域）
```

HDR重建公式（显示侧）：

$$I_{\text{HDR}}(x, y) = I_{\text{SDR}}(x, y) \cdot 2^{G(x,y) \cdot H_{\text{factor}}}$$

其中 $G(x,y) \in [0, 1]$ 为归一化增益图像素值，$H_{\text{factor}}$ 为全局增益缩放因子（元数据中存储，典型值对应峰值约 $1.5$～$4.0$ stops）。

**关键优点**：
- SDR设备直接使用主图像，完全兼容（无需额外解码路径）
- HDR设备叠加Gain Map恢复高亮细节，实现自适应HDR（Adaptive HDR）
- Gain Map可大幅下采样（1/4分辨率），额外存储开销约15–25%（相对于SDR基础图）

#### Apple Adaptive HDR（ISO/NHK Gain Map标准，ISO 21496-1）

Apple在iOS 17引入的 **Adaptive HDR**（也称 **HDR Gain Map**）遵循ISO/NHK正在推进的 ISO 21496-1 Gain Map标准草案，具体技术特征：

| 参数 | Apple实现 | 说明 |
|------|---------|------|
| 主图像色彩空间 | Display P3，8bit | iPhone默认拍照色彩空间 |
| Gain Map分辨率 | 1/2 到 1/4 原始分辨率 | 视HDR内容复杂度动态选择 |
| Gain Map编码 | HEVC单通道，10bit | 高精度，避免量化导致的增益跳变 |
| 最大增益 | `HDRGainMapHeadroom`，典型1.5–3.0 stops | 以stops（EV）为单位存储在EXIF |
| 显示自适应 | 根据屏幕峰值亮度线性插值增益 | 600 nit屏与1200 nit屏呈现不同强度 |

**EXIF元数据字段（Apple扩展）**：
```
MakerNote 或 XMP:
  HDRGainMapHeadroom: 2.0  // 最大增益(stops)
  GainMapVersion: 65536
  BaseRenditionIsHDR: 0    // 主图像是否为HDR（0=SDR）
```

#### Adobe/Google的Gain Map实现（Ultra HDR JPEG）

Google在Android 14引入 **Ultra HDR**（基于JPEG+Gain Map），结构与Apple类似但载体为JPEG：

```
Ultra HDR JPEG结构：
  ├── 标准JPEG（SDR，BT.709）         → 所有解码器可读
  └── JPEG XMP元数据中嵌入Gain Map图像 → HDR解码器读取并重建
```

Ultra HDR已被纳入Android 14+ `ImageWriter` API（`ImageFormat.JPEG_R`），适用于HDR截图、HDR相册浏览。

### 1.5 HDR图像编码

随着智能手机支持HDR拍摄，HDR内容的编码存储成为新挑战。

**P010格式**
- 10bit YUV 4:2:0格式，每个分量占16bits（高10位有效，低6位未定义（实现上通常填零，但规范不保证））。
- 常用于HDR视频帧缓冲，也用于RAW→HDR处理链路中的中间格式。
- Android `ImageFormat.YCBCR_P010`（API 33+）。

**HDR10静态元数据**
- **MaxCLL**（Maximum Content Light Level）：整个内容中单像素最大亮度（nits）。
- **MaxFALL**（Maximum Frame-Average Light Level）：所有帧中帧平均亮度的最大值。
- 元数据编码在HEIF/MP4容器的HDR静态元数据盒（`mdcv`/`clli`）中。

**Dolby Vision**
- 12bit HDR格式，支持动态元数据（逐帧/逐场景调整）。
- 需要Dolby授权，iPhone 12+支持拍摄Dolby Vision视频。

**HLG（Hybrid Log-Gamma）**
- 不需要静态元数据，兼容SDR显示器（向下兼容）。
- 传输函数（OETF，场景线性光 E' → 编码信号 E，依据BT.2100 **[10]**）：

$$
E = \begin{cases} \sqrt{3E'} & 0 \leq E' \leq 1/12 \\ a \ln(12E' - b) + c & E' > 1/12 \end{cases}
$$

其中 $a=0.17883277$，$b=0.28466892$，$c=0.55991073$。

### 1.6 Android Camera2 API输出格式

Camera2 API通过 `ImageFormat` 枚举定义输出格式：

| 格式 | ImageFormat常量 | API Level | 说明 |
|------|----------------|-----------|------|
| JPEG | `JPEG` (256) | 21 | 最兼容，硬件加速 |
| HEIF | `HEIF` (1212500294) | 29 | 需设备支持HEVC编码 |
| RAW_SENSOR | `RAW_SENSOR` (32) | 21 | 16bit Bayer RAW |
| RAW10 | `RAW10` (37) | 21 | 10bit压缩RAW（MIPI格式） |
| YUV_420_888 | `YUV_420_888` (35) | 21 | 未压缩YUV，用于自定义处理 |
| PRIVATE | `PRIVATE` (34) | 23 | 硬件加速预览，不可直接访问 |

HEIF输出需要配合 `CaptureRequest.JPEG_ORIENTATION` 设置图像旋转方向。

### 1.7 质量-文件大小权衡

**JPEG质量因子与文件大小关系（典型12MP图像）**

| QF | 文件大小（典型） | 感知质量 | 适用场景 |
|----|----------------|----------|----------|
| 95 | ~8MB | 接近无损 | 专业摄影存档 |
| 85 | ~3MB | 高质量 | 日常拍照（主流设置） |
| 75 | ~1.5MB | 良好 | 社交分享 |
| 60 | ~800KB | 可接受 | 网络预览图 |
| 50 以下 | <500KB | 明显失真 | 缩略图 |

**JPEG QF 85 ≈ HEIF QF 60（主观质量相当）** ：
- 相同主观质量下，HEIF文件约为JPEG的40%～60% 。
- 对于存储空间受限的设备（如64GB入门级手机），HEIF显著降低存储压力。

**编码延迟对比** ：
- JPEG（硬件加速）：~5ms（大多数主流SoC）
- HEIF（软件H.265编码）：50～200ms（依赖CPU性能）
- HEIF（硬件H.265 NPU/视频编码器）：~20ms
- AVIF（软件AV1）：200ms～2000ms（显著慢于HEIF）
- AVIF（硬件AV1编码器，如Pixel 6+）：~30ms

---

## §2 标定 (Calibration)

### 2.1 质量因子标定（感知质量标定）

不同QF设置的感知质量与文件大小权衡需要针对目标用户场景进行标定：

**标定流程**
1. 选取代表性测试图像集（≥50张，涵盖人像、风景、夜景、文字等场景）。
2. 对每张图像以QF=50到QF=100步进5，分别编码并解码。
3. 计算客观指标（PSNR、SSIM、VMAF）。
4. 进行MOS主观评测（5名以上评测者）。
5. 绘制质量-文件大小帕累托曲线，确定最优QF点。

**针对HEIF的标定**
- HEIF的QP（量化参数）与JPEG QF映射关系：$\text{QP}_{\text{HEVC}} \approx 63 - 0.6 \times \text{QF}_{\text{JPEG}}$（近似，有效范围 QF ∈ [50, 75]；QF > 75时公式低估QP，实际应通过主观测试标定）。
- 建议使用VMAF（Video Multi-Method Assessment Fusion）替代PSNR，更符合人眼感知。

### 2.2 色度子采样模式选择

| 应用场景 | 推荐子采样 | 原因 |
|----------|------------|------|
| 日常拍照 | 4:2:0 | 最小文件，色彩损失不明显 |
| 含文字的截图 | 4:4:4 | 避免文字边缘色彩渗透 |
| HDR内容 | 4:2:0（10bit） | 兼顾效率与HDR精度 |
| 医疗/科学图像 | 4:4:4 无损 | 严格色彩精度要求 |

---

## §3 调参指南 (Tuning)

### 3.1 JPEG质量设置

主摄默认 QF=85 是行业共识，这个值在感知质量和文件大小之间的帕累托点相对好，绝大多数日常照片在这里看不到明显伪影（*来源：AOSP Camera2 默认值及主流 HAL 实现，见 `android.hardware.camera2.CaptureRequest.JPEG_QUALITY`；具体 OEM 值需通过 AOSP 代码审查或厂商文档确认*）。QF=95 只在用户主动开启专业存储模式时用，文件会比 QF=85 大 2～3 倍但感知差异很小——多数情况下是浪费存储空间的占位符。不要把 QF=100 当"无损"用，JPEG QF=100 仍然是有损压缩，只是量化步长变成了1。

**Android Camera2 API**

```java
captureRequestBuilder.set(CaptureRequest.JPEG_QUALITY, (byte) 85);
```

> **工程推荐**：分享路径不要在相机HAL层降质量，在相册应用层做。原因是HAL层降质量是二次有损（先压一次 QF=85 存储，再压一次 QF=75 分享），二次压缩会让方块效应在边缘大幅累积，不如一次直接从原始数据压 QF=75。

**libjpeg/libjpeg-turbo调参**

- 渐进式 JPEG（Progressive）比基准式（Baseline）文件略小（约 3%），但对 ISP 工程师来说意义不大——手机上的 JPEG 硬件编码器通常只输出 Baseline。
- 对 Cb/Cr 通道单独设置更低 QF（色度视觉敏感度低于亮度，可节省约 10% 文件大小），这是 libjpeg-turbo 层面的优化，Camera HAL 层未必暴露这个参数。

### 3.2 HEIF编码参数

**主要参数**

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| 量化参数QP | 28～35 | QP=28对应高质量，QP=35对应中等质量 |
| 编码速度预设 | medium/fast | 影响编码延迟 |
| 色彩空间 | BT.2020（HDR）/ BT.709（SDR） | 宽色域内容使用BT.2020 |
| 位深 | 10bit（HDR）/ 8bit（SDR） | — |

**MediaCodec参数（Android）**

```java
MediaFormat format = MediaFormat.createVideoFormat(
    MediaFormat.MIMETYPE_VIDEO_HEVC, width, height);
format.setInteger(MediaFormat.KEY_COLOR_FORMAT,
    MediaCodecInfo.CodecCapabilities.COLOR_FormatYUVP010);  // 10bit HDR
format.setInteger(MediaFormat.KEY_BIT_RATE, targetBitrate);
format.setInteger(MediaFormat.KEY_FRAME_RATE, 1);  // 静态图像
format.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 0);  // 全I帧
```

### 3.3 HDR编码工作流参数

| 参数 | 典型值 | 说明 |
|------|--------|------|
| MaxCLL | 1000 nits（HDR10）| 根据实际内容测量 |
| MaxFALL | 400 nits | 场景均值 |
| 传输函数 | PQ（HDR10）/ HLG | HLG兼容性更好 |
| 色域 | BT.2020 | HDR宽色域标准 |

---

## §4 伪影分析 (Artifacts)

### 4.1 JPEG方块效应（DCT Blocking）

QF < 70 时，8×8 块内高频 DCT 系数几乎全被量化为零，块间出现不连续——天空、皮肤这类低纹理区域里最明显，出现规则的 8×8 方格。

消费级场景不要低于 QF=70，这基本上是共识。解码侧去块滤波（检测 8×8 块边界处的梯度不连续，平滑滤波但保护真实边缘）可以改善，但不能彻底消除——低质量编码造成的信息损失不可逆，去块只是视觉上的掩盖。

### 4.2 HEIF振铃效应（HEVC Ringing）

HEVC 的 CTU 尺寸大（最大 64×64），块效应比 JPEG 弱，但低码率时振铃效应（类 Gibbs）更明显——锐利边缘两侧的亮/暗光晕在文字和建筑线条上肉眼可见。HEVC 内置 SAO（Sample Adaptive Offset）滤波器可以部分抑制，低码率时效果有限。

QP 下限不低于 28 是工程经验值，QP=30 以上振铃开始明显，QP=35 以上在高对比度边缘基本不可接受。

### 4.3 色度子采样色彩渗透（Chroma Bleeding）

4:2:0 把 2×2 像素块的 Cb/Cr 合并为单值，颜色边缘处颜色向邻近区域渗透（1～2 个色度采样单元，即 2～4 个亮度像素宽）。红色文字在白底上的橙色晕边是最常被测试的场景。

相机拍照场景通常不受这个问题困扰（自然场景颜色边缘柔和），屏幕截图和文档扫描才是高风险场景。如果应用场景覆盖截图或文档，用 4:4:4 或 4:2:2。在色度下采样前对 Cb/Cr 做低通滤波（而非简单均值）可以减少混叠，但多数 ISP 硬件不提供这个参数。

### 4.4 编码延迟过高（High Encoding Latency）

软件 H.265 编码 HEIF 的延迟在 50～200ms，软件 AV1 编码 AVIF 在 200ms～2s——这不是调参可以解决的问题，是算法复杂度决定的。

> **工程推荐**：拍照实时路径只用 JPEG 或硬件 HEIF（高通 Hexagon DSP / 联发科 APU，约 20ms）。HEIF 软件路径和 AVIF 放到后台异步转码，不阻塞快门响应。连拍场景更激进——全程 JPEG，拍完再批量转码。AV1 硬件编码器在 2021 年后开始普及（Pixel 6+ 约 30ms），之前所有 AVIF 都只适合后台离线处理。

---

## §5 评测方法 (Evaluation)

### 5.1 压缩质量客观评测

**PSNR（Peak Signal-to-Noise Ratio）**

$$
\text{PSNR} = 10 \log_{10} \frac{255^2}{\text{MSE}}
$$

其中 $\text{MSE}$ 为重建图像与原始图像的均方误差。PSNR > 40dB 对应高质量，PSNR > 35dB 对应可接受质量 。局限：与人眼感知相关性有限。

**SSIM（Structural Similarity Index）**

$$
\text{SSIM}(x, y) = \frac{(2\mu_x\mu_y + c_1)(2\sigma_{xy} + c_2)}{(\mu_x^2 + \mu_y^2 + c_1)(\sigma_x^2 + \sigma_y^2 + c_2)}
$$

SSIM值范围 $[0, 1]$，> 0.95 为高质量 。比PSNR更符合人眼感知 **[7]**。

**VMAF（Video Multi-Method Assessment Fusion，Netflix）** **[9]**
- 融合多种感知特征（VIF、DLM等）的机器学习质量指标。
- 与PSNR相比，对压缩失真的主观感知相关性更高，工业界应用广泛。
- VMAF > 90 对应高质量（近乎无损感知）。

**MS-SSIM（Multi-Scale SSIM）**
- 在多个尺度（5个分辨率层级）计算SSIM，比单尺度SSIM更鲁棒。

### 5.2 压缩效率评测（RD曲线）

绘制率失真曲线（Rate-Distortion Curve）对比不同编码格式：
- 横轴：比特率（bits/pixel）或文件大小（bytes）
- 纵轴：PSNR 或 VMAF
- 对比点：在相同VMAF（如VMAF=90）下，各格式的文件大小；以JPEG为基准，计算HEIF/AVIF的压缩比增益。

典型结论（高质量拍照场景，12MP）：
- HEIF：JPEG的约40%～55%文件大小（相同主观质量）
- AVIF：JPEG的约35%～50%文件大小（相同主观质量）

### 5.3 编码延迟评测

测量不同格式在目标设备上的编码时间：
- 测量方法：100次重复取均值，排除初次调用开销（冷启动）。
- 区分软件编码与硬件编码路径。
- 报告P50（中位数）和P99（尾部延迟）。

### 5.4 HDR编码准确性评测

- 将HDR图像编码为HEIF（10bit PQ），解码后与原始HDR帧对比PSNR（以nits为单位计算）。
- 检查HDR元数据（MaxCLL/MaxFALL）的准确写入和读取（使用 `exiftool` 或 `MediaMetadataRetriever`）。

---

## §6 代码示例 (Code)

### 6.1 JPEG编码（Python / Pillow / libjpeg-turbo）

```python
import numpy as np
from PIL import Image
import io
import time

def encode_jpeg(image_rgb: np.ndarray,
                quality: int = 85,
                subsampling: int = 2,
                progressive: bool = False) -> bytes:
    """
    JPEG编码。

    Args:
        image_rgb: RGB格式图像，uint8，shape (H, W, 3)
        quality: JPEG质量因子 (1-95, Pillow使用1-95范围)
        subsampling: 0=4:4:4, 1=4:2:2, 2=4:2:0
        progressive: 是否使用渐进式JPEG

    Returns:
        jpeg_bytes: JPEG压缩数据
    """
    pil_image = Image.fromarray(image_rgb, mode='RGB')
    buffer = io.BytesIO()

    pil_image.save(
        buffer,
        format='JPEG',
        quality=quality,
        subsampling=subsampling,
        progressive=progressive,
        optimize=True  # 优化Huffman表
    )
    buffer.seek(0)
    return buffer.read()


def decode_jpeg(jpeg_bytes: bytes) -> np.ndarray:
    """JPEG解码，返回RGB numpy数组。"""
    buffer = io.BytesIO(jpeg_bytes)
    pil_image = Image.open(buffer)
    return np.array(pil_image)


def benchmark_jpeg_quality(image_rgb: np.ndarray,
                            quality_range: range = range(50, 100, 5)) -> list:
    """
    扫描JPEG质量因子，记录文件大小和编码时间。
    """
    results = []
    for qf in quality_range:
        start = time.perf_counter()
        jpeg_data = encode_jpeg(image_rgb, quality=qf)
        elapsed_ms = (time.perf_counter() - start) * 1000

        results.append({
            "quality": qf,
            "size_kb": len(jpeg_data) / 1024,
            "encode_ms": elapsed_ms
        })
        print(f"QF={qf:3d}: {len(jpeg_data)/1024:.1f} KB, {elapsed_ms:.1f} ms")
    return results
```

### 6.2 质量指标计算（PSNR / SSIM / MS-SSIM）

```python
import numpy as np
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr

def compute_image_quality_metrics(original: np.ndarray,
                                   compressed: np.ndarray,
                                   data_range: int = 255) -> dict:
    """
    计算压缩图像质量指标。

    Args:
        original: 原始图像（RGB，uint8）
        compressed: 压缩重建图像（RGB，uint8）
        data_range: 像素值范围（8bit为255）

    Returns:
        metrics: 包含PSNR、SSIM、各通道PSNR的字典
    """
    psnr_value = psnr(original, compressed, data_range=data_range)

    ssim_value = ssim(
        original, compressed,
        channel_axis=2,
        data_range=data_range
    )

    # 分通道PSNR（评估色度失真）
    channel_names = ['R', 'G', 'B']
    channel_psnr = {}
    for i, ch in enumerate(channel_names):
        channel_psnr[ch] = psnr(
            original[:, :, i], compressed[:, :, i],
            data_range=data_range
        )

    # 计算比特率（每像素比特数，bpp）
    # 需要已知文件大小
    h, w = original.shape[:2]
    total_pixels = h * w

    return {
        "psnr": float(psnr_value),
        "ssim": float(ssim_value),
        "channel_psnr": channel_psnr,
        "resolution": (w, h),
        "total_pixels": total_pixels
    }


def compare_formats(image_rgb: np.ndarray) -> None:
    """
    对比JPEG不同质量设置的压缩效果。
    """
    from io import BytesIO

    print(f"原始图像: {image_rgb.shape}, {image_rgb.nbytes/1024:.0f} KB (未压缩)")
    print("-" * 70)
    print(f"{'格式':<20} {'文件大小(KB)':<15} {'PSNR(dB)':<12} {'SSIM':<10}")
    print("-" * 70)

    # JPEG不同质量
    for qf in [60, 75, 85, 92, 95]:
        jpeg_data = encode_jpeg(image_rgb, quality=qf, subsampling=2)
        reconstructed = decode_jpeg(jpeg_data)
        metrics = compute_image_quality_metrics(image_rgb, reconstructed)
        print(f"JPEG QF={qf:<10} {len(jpeg_data)/1024:<15.1f} "
              f"{metrics['psnr']:<12.2f} {metrics['ssim']:<10.4f}")

    # JPEG 4:4:4 vs 4:2:0
    jpeg_444 = encode_jpeg(image_rgb, quality=85, subsampling=0)
    jpeg_420 = encode_jpeg(image_rgb, quality=85, subsampling=2)
    r_444 = decode_jpeg(jpeg_444)
    r_420 = decode_jpeg(jpeg_420)
    m_444 = compute_image_quality_metrics(image_rgb, r_444)
    m_420 = compute_image_quality_metrics(image_rgb, r_420)
    print(f"{'JPEG QF=85 4:4:4':<20} {len(jpeg_444)/1024:<15.1f} "
          f"{m_444['psnr']:<12.2f} {m_444['ssim']:<10.4f}")
    print(f"{'JPEG QF=85 4:2:0':<20} {len(jpeg_420)/1024:<15.1f} "
          f"{m_420['psnr']:<12.2f} {m_420['ssim']:<10.4f}")
```

### 6.3 HEIF编码（Android Camera2伪代码 / Python pillow-heif）

```python
# 使用pillow-heif库进行HEIF编码（Python示例）
# 安装: pip install pillow-heif

def encode_heif(image_rgb: np.ndarray,
                quality: int = 60,
                bit_depth: int = 8) -> bytes:
    """
    HEIF图像编码。

    Args:
        image_rgb: RGB图像，uint8
        quality: HEIF质量参数 (0-100)，
                 对应HEVC QP：QP ≈ 63 - 0.6 * quality（近似，quality ∈ [50, 75]有效）
        bit_depth: 位深，8 或 10

    Returns:
        heif_bytes: HEIF压缩数据
    """
    try:
        import pillow_heif
        from PIL import Image
        import io

        pillow_heif.register_heif_opener()

        pil_image = Image.fromarray(image_rgb, mode='RGB')
        buffer = io.BytesIO()
        pil_image.save(buffer, format='HEIF', quality=quality)
        buffer.seek(0)
        return buffer.read()
    except ImportError:
        print("请安装 pillow-heif: pip install pillow-heif")
        return b""


def encode_heif_android_pseudo() -> str:
    """
    Android Camera2 HEIF编码伪代码（Kotlin/Java逻辑描述）。
    """
    android_code = """
    // Kotlin伪代码：Android Camera2 HEIF输出配置

    // 1. 检查设备是否支持HEIF输出
    val characteristics = cameraManager.getCameraCharacteristics(cameraId)
    val configs = characteristics.get(
        CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP
    )
    val heifSupported = configs?.isOutputSupportedFor(ImageFormat.HEIF) ?: false

    if (heifSupported) {
        // 2. 创建ImageReader（HEIF格式）
        val imageReader = ImageReader.newInstance(
            captureWidth, captureHeight,
            ImageFormat.HEIF,
            maxImages = 2
        )

        // 3. 配置CaptureRequest
        val captureRequest = captureSession.device.createCaptureRequest(
            CameraDevice.TEMPLATE_STILL_CAPTURE
        ).apply {
            addTarget(imageReader.surface)
            set(CaptureRequest.JPEG_QUALITY, 85.toByte()) // 复用此字段控制HEIF质量
            set(CaptureRequest.JPEG_ORIENTATION, getOrientation())
        }

        // 4. 从ImageReader获取Image，转为字节流
        imageReader.setOnImageAvailableListener({ reader ->
            val image = reader.acquireLatestImage()
            val buffer = image.planes[0].buffer
            val heifBytes = ByteArray(buffer.remaining())
            buffer.get(heifBytes)
            // 保存heifBytes到文件
            image.close()
        }, backgroundHandler)
    }
    """
    return android_code
```

### 6.4 RD曲线绘制与格式对比

```python
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import io

def plot_rd_curve(image_rgb: np.ndarray,
                  output_path: str = "rd_curve.png") -> None:
    """
    绘制JPEG不同质量设置的率失真曲线。

    Args:
        image_rgb: 原始RGB测试图像
        output_path: 输出图表路径
    """
    qualities = list(range(30, 96, 5))
    sizes_kb = []
    psnr_values = []
    ssim_values = []

    h, w = image_rgb.shape[:2]
    total_pixels = h * w

    for qf in qualities:
        # 编码
        jpeg_bytes = encode_jpeg(image_rgb, quality=qf)
        # 解码
        reconstructed = decode_jpeg(jpeg_bytes)
        # 计算指标
        metrics = compute_image_quality_metrics(image_rgb, reconstructed)

        bpp = len(jpeg_bytes) * 8 / total_pixels
        sizes_kb.append(len(jpeg_bytes) / 1024)
        psnr_values.append(metrics["psnr"])
        ssim_values.append(metrics["ssim"])

    # 绘图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    ax1.plot(sizes_kb, psnr_values, 'b-o', label='JPEG')
    ax1.set_xlabel('文件大小 (KB)')
    ax1.set_ylabel('PSNR (dB)')
    ax1.set_title('率失真曲线（PSNR）')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # 标注关键QF点
    for i, qf in enumerate(qualities):
        if qf in [60, 75, 85, 95]:
            ax1.annotate(f'QF={qf}',
                         xy=(sizes_kb[i], psnr_values[i]),
                         xytext=(5, 5), textcoords='offset points',
                         fontsize=8)

    ax2.plot(sizes_kb, ssim_values, 'r-s', label='JPEG')
    ax2.set_xlabel('文件大小 (KB)')
    ax2.set_ylabel('SSIM')
    ax2.set_title('率失真曲线（SSIM）')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"RD曲线已保存至 {output_path}")
    plt.show()


def encode_and_compare_formats(image_rgb: np.ndarray) -> None:
    """完整格式对比，包含去块效应处理演示。"""
    import cv2

    # 低质量JPEG（演示方块效应）
    jpeg_low = encode_jpeg(image_rgb, quality=40)
    recon_low = decode_jpeg(jpeg_low)

    # 去块效应滤波（后处理）
    recon_low_bgr = recon_low[:, :, ::-1]  # RGB → BGR
    deblocked = cv2.fastNlMeansDenoisingColored(
        recon_low_bgr, None, h=3, hColor=3,
        templateWindowSize=7, searchWindowSize=21
    )

    print("低质量JPEG方块效应演示：")
    print(f"  原始JPEG QF=40 文件大小: {len(jpeg_low)/1024:.1f} KB")
    metrics_low = compute_image_quality_metrics(image_rgb, recon_low)
    print(f"  PSNR（未去块）: {metrics_low['psnr']:.2f} dB")
    metrics_deblocked = compute_image_quality_metrics(
        image_rgb, deblocked[:, :, ::-1]
    )
    print(f"  PSNR（去块后）: {metrics_deblocked['psnr']:.2f} dB")
    print(f"  SSIM改善: {metrics_deblocked['ssim'] - metrics_low['ssim']:.4f}")


# 主程序入口
if __name__ == "__main__":
    # 加载测试图像
    test_img_path = "test_image.png"
    try:
        img_pil = Image.open(test_img_path).convert('RGB')
        img_np = np.array(img_pil)
    except FileNotFoundError:
        # 生成合成测试图像
        print("未找到测试图像，生成合成测试图像...")
        img_np = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        # 添加一些结构（梯度 + 边缘）
        for i in range(0, 1080, 8):
            img_np[i, :, :] = np.clip(img_np[i, :, :] + 40, 0, 255)

    print(f"测试图像分辨率: {img_np.shape[1]}×{img_np.shape[0]}")
    print()

    # 质量基准测试
    print("=== JPEG质量扫描 ===")
    compare_formats(img_np)
    print()

    # 绘制RD曲线
    print("=== 生成RD曲线 ===")
    plot_rd_curve(img_np, "jpeg_rd_curve.png")
```

---

---

## §7 JPEG-XL 与新兴编码格式

### 7.1 JPEG-XL 概述

**JPEG-XL**（JXL）由 ISO/IEC 联合技术委员会（JPEG 组织）于 2022 年正式发布（ISO/IEC 18181），目标是成为下一代通用图像格式，兼顾高质量静态图和动画，支持无损/有损双模式。

**编码架构核心技术：**
- **模块化编码（Modular Coding）**：对整数精度图像（无损路径）使用基于上下文自适应熵编码（ANS）的模块化压缩。
- **VarDCT 编码（有损路径）**：对浮点/高精度内容使用可变 DCT 块大小（8×8 到 512×512）+ 量化 + ANS 熵编码。
- **感知量化**：基于 XYB 色彩空间（人眼感知优化的 LMS 变换域），量化噪声在视觉上不可见。
- **渐进解码（Progressive Decoding）**：可生成小文件的低质量预览，随数据增加逐步提升质量。

**与 JPEG/HEIF/AVIF 的关键对比：**

| 特性 | JPEG | HEIF (HEVC) | AVIF (AV1) | JPEG-XL |
|------|------|-------------|------------|---------|
| 无损压缩 | 不支持（仅 JPEG-LS） | 支持（有限） | 支持 | 原生支持 |
| 有损效率（vs JPEG） | 基准 | ~2× | ~2.1× | ~2–3× |
| JPEG 无损转码 | — | 需重新编码 | 需重新编码 | **零损失转码** |
| 色深 | 8 bit | 8/10/12 bit | 8/10/12 bit | 最高 32 bit |
| HDR 支持 | 否 | 是 | 是 | 是（线性光） |
| 动画支持 | MJPEG | 是（HEIF序列）| 是 | 是（原生帧序列）|
| 开源/免版税 | 是 | 否（HEVC专利）| 是 | 是 |
| 浏览器支持 | 全支持 | Safari/iOS | Chrome 85+/Firefox 93+/Safari 16+ | Chrome 91+(flag), Safari 17+ |
| 手机硬件编码 | 成熟 | 成熟 | 增长中 | 尚无专用硬件 |

**JPEG 零损失转码（Lossless JPEG Transcoding）：**

JPEG-XL 的独特能力——可将已有 JPEG 文件无损转码为 JXL 格式（bitstream reconstruction），文件大小减少约 **20–25%**，且可从 JXL 完全还原原始 JPEG 比特流（byte-for-byte identical）。这对海量 JPEG 存档的存储优化价值极大。

### 7.2 手机端编码格式路线图

| 时间节点 | 主流格式 | 推动力 |
|---------|---------|-------|
| 2022年以前 | JPEG（主流）+ HEIF（iOS默认）| HEIF iOS 11引入；Android厂商跟进 |
| 2022–2024 | HEIF/HEIC + AVIF（推广中）| Chrome AVIF支持；Android 12+ |
| 2025年+ | JPEG-XL（受限支持） + AVIF（主流 Android）| 浏览器软件支持增长，待硬件跟进 |

**工程建议**：2025年时间节点的现实是，手机相机应用的默认存储格式选 HEIF（iOS/Android 高端机都有硬件编码器，延迟可控），兼容性问题靠分享时自动转 JPEG 解决。AVIF 目前适合后台离线存档，不适合放在拍照关键路径。JPEG-XL 硬件编码器没有，浏览器支持仍残缺，工程上没有部署条件——做技术储备可以，但不要进量产路线图。

---

## §8 术语表（Glossary）

**DCT-II（离散余弦变换-II型，Discrete Cosine Transform Type-II）**
JPEG编码的核心变换，将8×8空间域像素块映射为频域系数。正交归一化DCT-II的外部系数为1/4，直流项修正因子C(0)=1/√2，C(k)=1（k>0），确保变换矩阵的正交性。实际编码器通常采用快速整数近似（如AAN算法）实现，与浮点标准公式等价。

**量化矩阵（Quantization Matrix）**
JPEG编码中控制每个DCT频率系数压缩粗细的矩阵。低频系数（左上角）量化步长小，高频系数步长大，符合人眼对低频信息更敏感的特性。质量因子QF越低，矩阵各元素越大，高频系数被量化为零的比例越高，压缩率越大，方块效应越明显。

**HEIF（High Efficiency Image Format，高效图像格式）**
由MPEG制定的容器格式，ISO/IEC 23008-12:2017正式发布。通常以HEVC（H.265）作为图像压缩编解码器（此时文件扩展名为.heic），支持10/12位深度、HDR、Alpha通道、多帧序列。典型压缩效率为JPEG的约2倍。Apple于iOS 11（2017）起将HEIF作为默认拍照格式。

**HEVC帧内预测模式（HEVC Intra Prediction Modes）**
HEVC亮度分量支持35种帧内预测模式：1种DC模式（邻近像素均值）、1种Planar模式（平面函数）、33种角度预测模式（覆盖±45°范围的方向性预测）。VVC（H.266）将角度模式扩展至65种，合计67种，以更细粒度捕获图像方向性纹理，提升压缩效率。

**AV1量化索引（AV1 q_index）**
AV1视频/图像编码器的量化控制参数，范围为0~255（256个离散级别）。与HEVC的QP（0~51，52级）相比，AV1的量化精度更细。q_index=0对应最高质量（最小量化步长），q_index=255对应最低质量。注意AV1还支持基于图像分割的差分量化（delta_q），在不同区域使用不同量化级别。

**AVIF（AV1 Image File Format）**
基于AV1视频编解码器的开源免版税图像格式，由Alliance for Open Media于2019年发布。压缩效率略优于HEIF，典型文件大小为JPEG的35%~50%（相同主观质量）。支持HDR、宽色域、Alpha通道，软件编码速度较慢（200ms~2s），随AV1硬件编码器普及（2021年后）实用性逐步提升。

**HLG OETF（混合对数伽马光电转换函数，Hybrid Log-Gamma Opto-Electronic Transfer Function）**
BT.2100标准定义的HLG传输函数，方向为场景线性光E' → 编码信号E（相机端使用）。低光部分（0≤E'≤1/12）采用平方根曲线E=√(3E')（兼容SDR），高光部分（E'>1/12）采用对数曲线E=a·ln(12E'-b)+c，参数a=0.17883277，b=0.28466892，c=0.55991073为BT.2100固定值。HLG OETF不同于EOTF（显示端：编码信号→显示亮度），需注意方向区分。

**P010格式（10位YUV 4:2:0）**
HDR视频/图像常用像素格式。每分量用16位存储（高10位有效，低6位未定义（实现上通常填零，但规范不保证））。平面结构：全分辨率Y平面 + 半分辨率UV交错平面。Android API 33+对应`ImageFormat.YCBCR_P010`，iOS对应`kCVPixelFormatType_420YpCbCr10BiPlanarVideoRange`，是HDR10和Dolby Vision内容的标准编码格式。

**PSNR / SSIM / VMAF（压缩质量评测指标）**
三种主流图像压缩质量指标。**PSNR**（峰值信噪比）= 10·log₁₀(255²/MSE)，>40dB为高质量；优点简单，缺点与主观感知相关性有限。**SSIM**（结构相似性）基于亮度/对比度/结构三分量，范围[0,1]，>0.95为高质量；比PSNR更符合人眼感知。**VMAF**（Netflix出品）融合VIF、DLM等多种感知特征，与人眼感知相关性优于PSNR，>90为高质量。

**率失真曲线（Rate-Distortion Curve，RD曲线）**
以文件大小（比特率）为横轴、质量指标（PSNR或VMAF）为纵轴的格式压缩效率对比曲线。在相同质量点（如VMAF=90），RD曲线越靠左的格式压缩效率越高。典型结论：HEIF和AVIF的RD曲线均位于JPEG左侧，表明在相同主观质量下，HEIF/AVIF文件约为JPEG的40%~55%。

**色度渗透（Chroma Bleeding）**
4:2:0色度下采样导致的颜色扩散伪影。Cb/Cr在2×2像素块内取均值，锐利颜色边缘处颜色向邻近区域渗透（典型宽度1~2个色度采样单元即2~4个亮度像素）。常见于红色文字在白底上的场景，表现为边缘出现橙色/粉色晕染。缓解方法：对色彩精度要求高的场景（截图、文档）使用4:4:4子采样。

---



---

> **工程师手记：JPEG/HEIF 编码质量调参的工程陷阱**
>
> **质量因子与量化表的非线性关系：** JPEG 的 `quality` 参数（0-100）并非线性映射到比特率——libjpeg 实现中，quality=75 对应的量化步长约为 quality=95 的 4 倍，而主观画质差距往往不成比例。实际项目中，我们针对手机主摄最终落地 quality=92（亮度量化矩阵 DC 系数步长为 2，AC 高频系数步长为 8-16），既能将 12MP 图像压缩到 3-4 MB，又使 SSIM 维持在 0.96 以上。高通 Snapdragon 平台的 JPEG 硬件编码器（Fastrpc JPEG）默认采用标准 JPEG Annex K 量化表，可通过 `mm-still` 配置覆写；MTK 平台通过 `MTKJpeg` HAL 层参数 `JPEG_QUALITY` 直接传递，但实测同等 quality 值下码率比高通大约高 8-12%，需要在手机 BSP 调试期间独立标定各平台的质量-码率曲线后再统一产品规格。
>
> **4:2:0 与 4:4:4 色度采样的实际影响：** 移动端主摄输出几乎全部采用 YCbCr 4:2:0，色度通道水平和垂直各降采样 2 倍，理论上对自然景物的感知损失极小（人眼空间色度分辨率约为亮度的 1/4），但在红/绿色饱和边缘（如花卉、UI 截图）处会出现色彩晕染（chroma bleeding）。HEIF（基于 HEVC 的 `hevc_image`）在 A 系芯片（Apple VTCompressionSession）和骁龙 8 Gen2 的 Hexagon DSP 编码路径上均支持 4:2:2 及 4:2:0 切换；测试表明，对文字截图或 UI 图像使用 4:2:2 可将色彩 PSNR 提升约 1.5 dB，但文件体积增大约 20%。产品定义时须区分"照片场景"与"截图场景"分别配置采样格式。
>
> **跨平台 HEIF 编码器差异与兼容性坑：** Apple A 系和 M 系芯片的 HEIF 编码器（VideoToolbox hevc/heic）内置了基于 VMAF 的自适应质量调度，同等 `AVVideoQualityKey=0.8` 设置下输出码率会随场景复杂度浮动 30-50%，而高通 C2 (Codec2) HEIF 路径的码率控制以固定 QP 为主（默认 QP=28），HDR 场景下高光细节压缩偏激进。联发科 Helio/Dimensity 平台的 HEIF 硬件编码器在实测中发现：当输入图像含 10-bit HDR 元数据时，若未显式设置 `color_primaries=9 (BT.2020)`，编码器会静默回退到 8-bit 输出并丢弃 HDR metadata，导致后续显示链 tone mapping 失效，该问题在 MTK Android 12 BSP v1.3 之前的版本中普遍存在。
>
> *参考：Wallace, G.K., "The JPEG Still Picture Compression Standard", IEEE Transactions on Consumer Electronics, 1992；Muhit et al., "HEIF: High Efficiency Image File Format", ISO/IEC 23008-12, 2017；大话成像《手机JPEG编码调参实战》（微信公众号，2023）*

## 插图

![compression quality tradeoff](img/fig_compression_quality_tradeoff_ch.png)
*图1. 压缩质量与码率权衡曲线——JPEG/HEIF/AVIF 在不同压缩质量因子下的 PSNR-码率曲线（图片来源：Wallace et al., IEEE Transactions on Consumer Electronics, 1992）*

![dct basis functions](img/fig_dct_basis_functions_ch.png)
*图2. DCT 基函数可视化——8×8 离散余弦变换的 64 个基函数图样，从低频（左上）到高频（右下）的频率分布（图片来源：Wallace et al., IEEE Transactions on Consumer Electronics, 1992）*

![jpeg compression pipeline](img/fig_jpeg_compression_pipeline_ch.png)
*图3. JPEG 压缩编码流水线——色彩空间转换、色度下采样、DCT 变换、量化、Zigzag 扫描与 Huffman 熵编码的完整流程（图片来源：ISO/IEC, ISO/IEC 10918-1, 1994）*

![jpeg compression steps](img/fig_jpeg_compression_steps_ch.png)
*图4. JPEG 压缩各步骤示意图——原始像素块到 DCT 系数矩阵，再到量化后稀疏系数的逐步变换过程（图片来源：Wallace et al., IEEE Transactions on Consumer Electronics, 1992）*

![jpeg heif comparison](img/fig_jpeg_heif_comparison_ch.png)
*图5. JPEG 与 HEIF 格式对比图——相同视觉质量下 JPEG 与 HEIF（HEVC 编码）的文件大小对比，HEIF 约节省 50% 存储（图片来源：ISO/IEC, ISO/IEC 23008-12, 2017）*



---
![compression ratio quality](img/fig_compression_ratio_quality_ch.png)
*图6. 压缩比与质量关系散点图——不同编码格式在典型场景图像上的压缩比与主观/客观质量评分分布（图片来源：Seshadrinathan et al., IEEE TIP, 2010）*

![dct basis](img/fig_dct_basis_ch.png)
*图7. DCT 基向量示意图——一维 8 点 DCT 基函数的余弦波形，展示各频率系数对应的空间频率（图片来源：Wallace et al., IEEE Transactions on Consumer Electronics, 1992）*

![heif vs jpeg](img/fig_heif_vs_jpeg_ch.png)
*图8. HEIF 与 JPEG 文件格式对比——容器结构、色彩深度支持、HDR/Alpha 通道能力与多帧图像序列存储特性对比（图片来源：Sullivan et al., IEEE TCSSVT, 2012）*

![jpeg pipeline](img/fig_jpeg_pipeline_ch.png)
*图9. JPEG 编解码完整流水线图——编码端（YCbCr 转换→DCT→量化→熵编码）与解码端（熵解码→反量化→IDCT→色彩转换）的对称结构（图片来源：ISO/IEC, ISO/IEC 10918-1, 1994）*

---

## 习题

**练习 1（理解）**
JPEG 编码的核心是将图像分割为 8×8 块，对每块执行离散余弦变换（DCT），然后用量化步长矩阵 $Q$ 对 DCT 系数取整（丢弃高频细节）。质量因子 QF 决定量化步长：QF 越低，步长越大，高频信息损失越多。

1. 解释为何 JPEG 压缩产生的"块效应"（Blocking Artifact）与 8×8 DCT 块边界有关：当 QF 很低时，相邻块之间的高频 DCT 系数几乎全部被量化为 0，块内被还原为少数低频分量，边界处为何出现不连续？
2. HEIF（基于 HEVC/H.265 帧内编码）为何在相同视觉质量下文件更小？从编码单元（Coding Unit，可变大小 4×4–64×64）和帧内预测角度解释其优势。
3. JPEG 的 4:2:0 色度二次采样（Chroma Subsampling）为何能在视觉上无明显损失的同时减少约 50% 的色度数据量？人眼对亮度和色度分辨率的感知差异如何支撑这一设计？

**练习 2（计算）**
一张 12MP（4000×3000）的 RGB 图像（3 通道，8 位）：

1. 原始未压缩大小是多少字节（RGB 24 位，不含文件头）？
2. 若 JPEG QF = 80 输出文件约 2.5 MB，压缩比（原始大小 / 压缩大小）是多少？
3. 若 HEIF 在同等主观质量（PSNR ≈ 42 dB）下文件约 1.2 MB，HEIF 相对 JPEG 的文件大小减少了多少百分比？
4. 对于一个 8×8 亮度块，若 QF = 80 时亮度量化矩阵的直流（DC）步长为 2，某块的 DC 系数为 127.3，量化后取整为多少？反量化后的 DC 系数恢复为多少，量化误差是多少？

**练习 3（编程）**
分析不同 JPEG 质量因子（QF = 10、30、50、70、90）下的块效应与 PSNR：

- 输入：`image` — 形状 `(H, W, 3)` 的 uint8 BGR 图像（推荐使用 512×512 测试图）；质量因子列表 `quality_list = [10, 30, 50, 70, 90]`
- 输出：每个 QF 对应的 PSNR（dB）和文件大小（KB）；可视化 QF = 10 的块效应（提取块边界处的水平截面曲线）
- 要求：使用 `cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, qf])` 压缩，再用 `cv2.imdecode` 解码；PSNR 计算使用 `cv2.PSNR` 或手动计算

```python
import numpy as np
import cv2
# 输入: image (H,W,3) uint8 BGR, quality_list=[10,30,50,70,90]
# 输出: results dict {qf: {'psnr': float, 'size_kb': float}}
```

**练习 4（工程分析）**
高通 Spectra ISP 通过 Camera HAL 的 `ANDROID_JPEG_QUALITY`（Android Camera2 API，范围 1–100，对应 JPEG 质量因子）控制 JPEG 编码质量；HEIF 编码通过 `ANDROID_HEIF_QUALITY` 或 MediaCodec HEVC 编码器的 `BITRATE` 参数控制。MTK ISP 中 JPEG 编码参数为 `JPEG_Quality`（同 Android API 映射）。某产品团队将默认拍照 JPEG 质量从 95 降至 85，以减少 12MP 照片的平均文件大小（从约 6 MB 降至约 2 MB），但用户反馈在打印 A4 大尺寸照片时出现可见块效应。

1. 分析 QF = 85 在屏幕浏览（手机屏幕 ~400 PPI）和大尺寸打印（A4 @ 300 DPI，对应约 2480×3508 像素）两种观看条件下，块效应可见性差异的原因（从空间频率和观察距离角度）。
2. 建议针对"大尺寸打印"场景的 JPEG 质量设置（给出具体 QF 值），或建议改用 HEIF 格式的理由（同等画质下 HEIF QF 对应的典型文件大小）。
3. 若硬件 JPEG 编码器（Spectra ISP 内置）在 QF > 95 时硬件加速不可用（需切换到软件编码，延迟从 50 ms 增加到 300 ms），工程上如何平衡画质与延迟？是否有折衷方案（如 QF = 92 + HEIF 备选）？

---

## 参考文献

[1] Wallace, "The JPEG still picture compression standard", *IEEE Transactions on Consumer Electronics*, 1992.

[2] ISO/IEC, "ISO/IEC 23008-12:2017 — High efficiency coding and media delivery — Part 12: Image File Format (HEIF)", *官方文档*, 2017.

[3] Sullivan et al., "Overview of the High Efficiency Video Coding (HEVC) standard", *IEEE Transactions on Circuits and Systems for Video Technology*, 2012.

[4] Chen et al., "An overview of core coding tools in the AV1 video codec", *PCS*, 2018.

[5] Alliance for Open Media, "AVIF specification", *官方文档*, 2019. URL: https://aomediacodec.github.io/av1-avif/

[6] Mukherjee et al., "The latest open-source video codec", *SPIE Optics + Photonics*, 2013.

[7] Wang et al., "Image quality assessment: From error visibility to structural similarity", *IEEE Transactions on Image Processing*, 2004.

[8] Seshadrinathan et al., "Study of subjective and objective quality assessment of video", *IEEE Transactions on Image Processing*, 2010.

[9] Li et al., "Toward a practical perceptual video quality metric", *博客/公众号*, 2016. URL: https://netflixtechblog.com

[10] ITU-R, "BT.2100-2 — Image parameter values for high dynamic range television for use in production and international programme exchange", *官方文档*, 2018.

[11] Google, "Android Camera2 API reference — ImageFormat", *官方文档*, 2021. URL: https://developer.android.com/reference/android/graphics/ImageFormat

[12] Apple, "WWDC 2017 Session 508: Advances in Camera Capture & Photo Segmentation", *官方文档*, 2017.

[13] ISO/IEC, "ISO/IEC 18181:2022 — Information technology — JPEG XL Image Coding System", *官方文档*, 2022.

[14] Alakuijala et al., "JPEG XL next-generation image compression architecture and coding tools", *SPIE Applications of Digital Image Processing*, 2019.
