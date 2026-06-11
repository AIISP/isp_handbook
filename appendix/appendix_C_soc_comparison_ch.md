# 附录C — ISP SoC对比（通用公开版）| ISP SoC Comparison (Generic / Public Version)

> **公开版。** 本附录使用非供应商特定术语描述通用ISP SoC类别。
> 供应商特定流水线细节、寄存器级配置和调参范围，
> 请参见私有文档（`私有版本仓库/`）。

---

## C.1 ISP SoC类别

现代ISP实现涵盖广泛的芯片平台。按应用领域和性能档次，大致可分为以下类别：

| 类别 | 典型场景 | 功耗范围 | 关键差异化特性 |
|----------|----------------|---------------|-------------------|
| 移动SoC 一档 | 旗舰智能手机 | 1–5 W（ISP模块，*来源：第三方估算，基于cpu-monkey/AnandTech功耗分析*） | 多摄融合、AI加速、高帧率HDR |
| 移动SoC 二档 | 中端智能手机 | 0.5–2 W（*来源：第三方估算*） | 均衡流水线、适度AI、成本优化 |
| 汽车ISP | ADAS、环视 | 5–20 W（*来源：第三方估算*） | 功能安全（ISO 26262）、宽温度范围、车道/行人检测流水线 |
| 工业相机ISP | 机器视觉、检测 | 差异较大 | 高精度、确定性流水线、多光谱支持 |
| 独立ISP芯片 | 小型相机、运动相机 | 1–10 W | 专用硅、深度调参入口 |
| FPGA ISP | 原型验证、低量产 | 灵活 | 可重配置流水线、研究用途 |
| 软件ISP | PC、云端处理 | CPU/GPU | 最大灵活性、无硬件约束 |

---

## C.2 移动SoC一档（旗舰）

### 流水线能力

典型旗舰移动ISP在硬件中支持以下流水线阶段：

```
RAW输入
  → BLC（黑电平校正，逐通道，温度补偿）
  → PDPC（相位检测坏点校正）
  → LSC（镜头阴影校正，全视场多项式或网格）
  → Demosaic（方向性/频率域，亚像素精度）
  → Denoise（多帧NR：时域+空域，通常AI辅助）
  → Sharpening/Edge Enhancement（自适应，MTF感知）
  → AWB（灰世界 + 统计场景先验 + AI分类）
  → CCM（3×3或3×3+3仿射，光源相关插值）
  → Gamma/Tone Mapping（HDR：多段曲线或LUT）
  → CSC（RGB转YUV，多标准输出）
  → 输出（4K/8K视频、连拍HDR、计算摄影）
```

### 计算能力

- 专用ISP硬件加速器（GOPS级别）
- 片上NPU（神经处理单元）用于AI辅助模块
- 多摄支持：通常3–5路同时摄像头输入
- 高帧率：实时处理下4K 60–240 fps
- 多帧HDR：3–9帧融合，带运动检测

### 关键特性（通用描述）

- **AI去噪：** 深度学习去噪运行于NPU，替换或增强传统双边/BM3D滤波
- **语义AWB：** 场景分类以应对挑战性光源（烛光、霓虹灯、混合光照）
- **计算变焦：** 多摄融合实现连续光学/数字变焦
- **实时人像：** 深度图生成用于散景渲染
- **夜间模式：** 多帧对齐+去噪叠加（10–30帧）

### 调参复杂度

旗舰移动ISP通常暴露500–2000+个调参参数，按以下维度组织：
- 按模块（BLC、LSC、CCM等）
- 按ISO（通常6–12个ISO点）
- 按光源（D65、TL84、A等）
- 按场景模式（自动、人像、夜间、视频）

> 供应商特定参数名称、寄存器地址和推荐调参范围，
> 请参见 `私有版本仓库中的厂商参数文档`。

---

## C.3 移动SoC二档（中端）

### 流水线能力

中端ISP以较低的硬件并行度覆盖核心流水线：

```
BLC → LSC → Demosaic → Denoise → Sharpening → AWB → CCM → Gamma/TM → CSC
```

与一档的主要差异：
- 去噪：通常仅空域NR（硬件中无时域多帧）
- HDR：限于2帧合并或数字WDR（无3帧+）
- AI：片上NPU有限或缺失；AI功能可能在主CPU/GPU上运行
- 帧率：通常4K 30–60 fps

### 调参复杂度

中等：200–600个调参参数。插值维度较少（通常4–6个ISO点，3种光源）。

---

## C.4 汽车ISP

### 使用场景要求

汽车ISP与移动端有本质不同的需求：

| 需求 | 移动 | 汽车 |
|-------------|--------|-----------|
| 安全标准 | 无 | ISO 26262 ASIL-B/D |
| 温度范围 | 0–40°C | -40°C至+85°C |
| 延迟 | 灵活 | 硬实时（流水线延迟≤1帧） |
| 动态范围 | 12–14档 | 120–140 dB（白天→隧道过渡的HDR） |
| 主要输出对象 | 人类观看者 | 计算机视觉（检测、分割） |
| 夜间视觉 | 多帧叠加 | 单帧HDR、NIR支持 |
| 畸变 | 可接受未校正 | 必须校正以用于环视拼接 |

### 流水线特性

- **高动态范围HDR：** 多曝光或压缩式WDR，覆盖120+ dB
- **集成CV预处理的ISP：** 部分汽车ISP在RGB旁或代替RGB输出预处理的特征图
- **镜头畸变校正：** 环视摄像头的鱼眼校正
- **确定性处理：** 无丢帧，帧间无质量变化
- **冗余处理：** 安全关键应用的锁步ISP核心

### 典型计算配置

- 功耗：每ISP模块5–20 W（因宽幅传感器而显著高于移动端）
- 多摄：4–12路摄像头输入（全环视）
- 接口：MIPI CSI-2、FPD-Link、GMSL

---

## C.5 工业相机ISP

### 特性

工业机器视觉要求：
- **确定性曝光控制：** 运动零件检测需要微秒精度的触发和曝光
- **高精度颜色：** 喷漆缺陷检测、医学成像所需的最小颜色误差
- **多光谱：** 部分系统工作于NIR、UV或超光谱波段
- **非标准CFA：** 部分工业传感器使用RGGB、RGGB-IR或单色
- **原始吞吐量：** 许多工业系统倾向于将原始数据流传至主机PC进行离线处理

### 流水线理念

与移动ISP不同，许多工业相机倾向于**最少的机内ISP**——仅进行必要校正（BLC、PDPC），将RAW或最小处理的数据流传至主机。完整ISP在软件中运行（如HALCON、OpenCV、专有SDK）。

---

## C.6 独立ISP芯片

### 使用场景
- 运动相机、小型相机、行车记录仪、无人机
- 应用SoC不包含足够ISP硬件的场景
- 相机算法原型开发套件

### 特性
- 专用硅中的完整ISP流水线
- 通过I2C/SPI寄存器接口实现深度调参入口
- 通常与单独的应用处理器配对
- 功耗：1–10 W，取决于分辨率和功能集

---

## C.7 软件ISP

### 使用场景
- PC上的RAW处理（Adobe Lightroom、darktable、RawTherapee）
- 云端照片增强
- 算法研究与原型验证

### 特性
- 最大灵活性——所有参数可访问
- 无实时约束
- DL模块可用GPU加速
- 有开源实现（参见附录D）

---

## C.8 ISP功能矩阵（通用）

| 特性 | 一档移动 | 二档移动 | 汽车 | 工业 |
|---------|:---:|:---:|:---:|:---:|
| BLC + PDPC | ✅ | ✅ | ✅ | ✅ |
| LSC（全多项式） | ✅ | ✅ | ✅ | 差异 |
| 方向性去马赛克 | ✅ | ✅ | ✅ | ✅ |
| 多帧时域NR | ✅ | 有限 | 差异 | 无 |
| AI去噪（NPU） | ✅ | 有限 | 新兴 | 无 |
| 3帧+ HDR合并 | ✅ | 有限 | ✅（压缩式） | 无 |
| 语义AWB | ✅ | 无 | 无 | 无 |
| 计算变焦 | ✅ | 有限 | 无 | 无 |
| 鱼眼畸变校正 | 有限 | 无 | ✅ | 差异 |
| ISO 26262安全认证 | 无 | 无 | 必须 | 无 |
| RAW流传（旁路） | 部分 | 部分 | 无 | ✅ |

---

## C.9 调参工作流对比（通用）

### 移动ISP调参工作流（通用）
```
1. 出厂标定：逐台BLC、LSC、CCM（单台差异标定）
2. 批量标定：产线上逐SKU的CCM + AWB增益
3. 算法调参：逐场景模式（自动/夜间/人像）参数调整
4. 验证：IQA指标（MTF50、ΔE、SNR、PSNR/SSIM）
5. OTA更新：发布后参数精调
```

### 汽车ISP调参工作流（通用）
```
1. 传感器特性描述：BLC/噪声的全温度扫描
2. 光学标定：逐镜头单元的LSC + 几何畸变
3. HDR标定：曝光比和响应曲线对齐
4. CV指标调参：优化检测精度而非人类IQA
5. 安全验证：确定性分析和最坏情况分析
```

---

## C.10 旗舰移动平台深度对比

本节分别介绍三大主流旗舰移动SoC的ISP架构：高通骁龙 Spectra ISP、海思麒麟 ISP 和联发科天玑 Imagiq ISP。

---

### C.10.1 高通 Spectra ISP（Qualcomm Spectra）

#### 架构概述

高通 Spectra ISP 是骁龙 (Snapdragon) SoC 的专属影像子系统。自骁龙888起引入**三路ISP并行架构 (Triple ISP architecture)**，可同时处理三路摄像头数据流，支持多达三颗摄像头同时录制4K视频。

**架构代际演进：**

| 代次 | 对应骁龙 | 关键升级 |
|------|---------|---------|
| Spectra 480 | 骁龙865 | 双ISP，2 Gpixel/s，AI-ISP初代 |
| Spectra 580 | 骁龙888 | **三路ISP并行**，2.7 Gpixel/s，MFNR 30帧夜景 |
| Spectra（8 Gen1） | 骁龙8 Gen1 | **18位内部精度**，HDR10+实时采集 |
| Spectra（8 Gen2） | 骁龙8 Gen2 | AI多帧降噪升级，语义分割感知HDR，NPU **34 TOPS** |
| Spectra 80（8 Gen3） | 骁龙8 Gen3 | 生成式AI接入ISP链路，实时4K HDR10+ 60fps，triple 18-bit，NPU **45 TOPS**（官方AI Engine） |
| Spectra 1080（8 Elite） | 骁龙8 Elite | 三ISP 20位精度，端侧生成式图像编辑，NPU **约65 TOPS**（官方称较8 Gen 3快45%，45 TOPS×1.45≈65 TOPS） |

**贝耶处理子系统 (BPS, Bayer Processing Subsystem)** 是独立于主ISP核心的专用RAW域硬件加速器，负责：
- 黑电平校正 (BLC)
- 镜头阴影校正 (LSC)
- 坏点校正 (PDPC)
- Bayer降噪（空域）

BPS与主ISP核心并行工作，将预处理后的Bayer数据交付下游，减轻主ISP负担。

**18位内部精度（8 Gen1起）：** ISP内部数据通路采用18位定点运算（传统平台通常为14位），在高动态范围合并、曝光融合等环节有效抑制量化噪声和色调断层。

#### 调参工具链

高通使用 **Chromatix™ XML 参数文件**体系作为ISP调参载体，配套工具为 **相机调参工具 (CTT, Camera Tuning Tool)**。

**Chromatix参数维度：**
```
参数空间 = 模块 × ISO档位 × 光源类型 × 场景模式
```
- **模块维度（主要Chromatix模块）：**
  - `aec_algo_params`：自动曝光算法参数
  - `awb_algo_params`：自动白平衡算法参数
  - `blc_params`：黑电平校正参数
  - `lsc_params`：镜头阴影校正网格
  - `hdr_params`：HDR合并曲线与权重
  - `raw_nr_params`：RAW域噪声抑制强度
  - `demosaic_params`：去马赛克方向性权重
  - `ccm_params`：颜色校正矩阵（各光源）
  - `sharpening_params`：锐化强度与频率权重
  - `ltm_params`：局部色调映射参数
  - `gamma_params`：全局Gamma曲线LUT
- **ISO维度：** 通常8–12个ISO点（如ISO100/200/400/800/1600/3200/6400/12800）
- **光源维度：** A光（2856 K）、TL84（4000 K）、CWF（4150 K）、D65（6500 K），共4种标准光源
- **场景模式维度：** 自动、人像、夜间、视频、超高速等

各维度之间在运行时进行双线性或三线性插值，实现平滑过渡。CTT工具提供可视化调参界面，支持在真实摄像头预览下实时调整参数并回写XML。

#### 特色算法

**1. AI-ISP（Hexagon NPU加速）**

骁龙 Hexagon 数字信号处理器 (DSP) 兼具NPU功能，为AI-ISP模块提供算力支撑：
- **语义场景分类 (Semantic Scene Classification)：** NPU实时推断场景类别（户外/室内/夜间/逆光等），结果反馈给3A算法（自动曝光、自动白平衡、自动对焦），实现场景感知的曝光决策
- **AI辅助AWB：** 在混合光照、色温偏低的烛光场景下，通过NPU推断光源概率分布，修正传统灰世界算法的偏差

**2. 多帧降噪 (MFNR, Multi-Frame Noise Reduction)**

Spectra 580（骁龙888）开始支持30帧RAW域多帧降噪夜间模式：
- 连续采集30帧RAW图像
- 硬件光流 (Optical Flow) 引擎对帧间目标运动进行亚像素对齐
- 加权时域平均叠加，SNR提升理论上限约 $10\log_{10}(N)$ dB（N=帧数）
- 最终输出单帧高SNR RAW，再经完整ISP流水线处理

**3. 交错式HDR (Staggered HDR)**

Staggered HDR在**传感器级别**实现多曝光交错读出（同一帧内不同行采用不同曝光时间），相对于帧间HDR（短曝光帧和长曝光帧在时序上分离）有以下优势：
- 消除运动鬼影 (Ghost Artifact)：高速运动主体在两路曝光间的位移趋近于零
- 降低系统时延：无需等待完整短曝光帧就绪

**4. 实时语义HDR（8 Gen2起）**

在传统全局色调映射基础上，引入语义分割图（天空/人脸/植被等），对不同语义区域采用差异化的局部色调映射曲线，有效避免天空过曝与暗部欠曝并存的问题。

#### 参考资料

- 高通官方产品页：https://www.qualcomm.com/products/mobile/snapdragon/smartphones/snapdragon-8-series-mobile-platforms/snapdragon-8-gen-3-mobile-platform
- 高通开发者文档（相机）：https://developer.qualcomm.com/docs/camera/
- Spectra ISP白皮书（需注册访问）：https://developer.qualcomm.com/

#### Qualcomm 官方公开资源

##### 开源代码

- **CAMX 相机框架 (Camera eXtension Framework)**
  https://github.com/quic/camx
  Qualcomm 官方 GitHub，BSD-3 开源许可，包含完整相机流水线节点实现

- **CHI-CDK (Camera Hardware Interface Component Development Kit)**
  https://github.com/quic/chi-cdk
  Chromatix XML schema 定义和参数结构，Qualcomm 官方开源

- **Camera Kernel Driver (CodeLinaro)**
  https://git.codelinaro.org/clo/la/platform/vendor/opensource/camera-kernel
  Qualcomm 相机内核驱动，Linux Foundation 托管

- **QCamera HAL (AOSP Mirror)**
  https://android.googlesource.com/platform/hardware/qcom/camera/
  AOSP 上的高通相机 HAL 代码，权威可引用

##### 官方技术文档

- **Qualcomm Spectra ISP 技术概述**
  https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/qualcomm-spectra-isp.pdf

- **Chromatix SDK 开发者页面**
  https://developer.qualcomm.com/software/chromatix
  *(需要注册 Qualcomm Developer Network 账号)*

- **Camera Developer Tools 总览**
  https://developer.qualcomm.com/software/camera-developer-tools

- **骁龙8 Gen 3 摄影技术页**
  https://www.qualcomm.com/products/mobile/snapdragon/smartphones/snapdragon-8-series/snapdragon-8-gen-3-mobile-platform

---

### C.10.2 海思麒麟 ISP（HiSilicon Kirin ISP）

#### 架构概述

海思麒麟 ISP 是华为旗舰手机的专属影像处理核心，随麒麟 SoC 代际演进持续迭代。

**ISP代际演进：**

| 代次 | 对应麒麟 SoC | 关键升级 |
|------|------------|---------|
| ISP 3.0 | 麒麟 960 | 双ISP，第一代移动AI辅助ISP雏形 |
| ISP 4.0 | 麒麟 970 | NPU辅助降噪，首款移动AI芯片 |
| ISP 5.0 | **麒麟 980** | **业界首款AI-ISP**，双ISP + NPU协同架构 |
| ISP 5.0+ | **麒麟 990 5G** | **业界首批三路ISP之一**（2019年），2.4 Gpixel/s |
| ISP 6.0 | 麒麟 9000 | XD-Fusion Pro，语义分割NR，4K HDR视频 |

**三路ISP（Triple ISP，麒麟990 5G，2019年）**

麒麟990 5G是业界首批搭载三路ISP的移动SoC之一（同期联发科天玑1000亦于2019年推出三路ISP，早于高通骁龙888的2020年发布），三路ISP合计吞吐量达2.4 Gpixel/s，支持：
- 三路独立摄像头同时处理
- 主摄超高分辨率连拍
- 超级夜景多帧叠加期间后置广角/长焦同步取景

#### RYYB 彩色滤波阵列

麒麟旗舰（Mate 30 Pro起）配套传感器采用非标准 **RYYB（红-黄-黄-蓝）彩色滤波阵列 (CFA)**，替代传统RGGB：

- Y（黄色）滤光片透过率约为绿色滤光片的2倍（黄色 = 红色 + 绿色通道透过），显著提升低光进光量
- RYYB传感器的等效进光量相比同规格RGGB可提升约40%
- **代价：** Y通道中混入红色光，无法直接提取纯绿色信号，去马赛克时需**AI辅助从Y通道重建G通道**（$G = Y - R$，其中R为插值得到的红色分量），算法复杂度显著高于标准Bayer

ISP在RAW域须针对RYYB矩阵专门设计颜色重建算法，NPU辅助修正色彩偏差。

#### 调参工具链

麒麟ISP的调参工具为内部工具 **HiTuning Tool**（非公开），仅授权给华为认证的ODM/调参合作伙伴使用。

**标定流程（通用描述）：**
1. **ColorChecker标定：** 使用 X-Rite ColorChecker 色板拍摄多光源照片，建立光源相关 CCM（颜色校正矩阵）
2. **ISO-12233分辨率板：** 测量MTF50，建立锐化参数曲线
3. **平场校正 (Flat-field Calibration)：** 对均匀光场拍摄，提取LSC网格校正镜头阴影
4. **噪声模型标定：** 暗场拍摄，拟合传感器噪声模型（泊松+高斯混合）

由于工具非公开，第三方开发者无法直接访问麒麟ISP底层参数。

#### 特色算法

**1. 超清引擎 (XD-Fusion Pro, eXtreme Definition Fusion)**

XD-Fusion Pro 是麒麟9000引入的计算摄影统筹框架，将 ISP + NPU + CPU + GPU 四个计算单元协同调度：
- **语义分割感知降噪：** NPU对图像进行逐像素语义分割（天空/皮肤/植被/建筑等），对不同语义类别施加差异化降噪强度
  - 皮肤区域：柔和降噪，保留毛孔等微纹理
  - 天空区域：强力降噪，消除色彩噪点
  - 植被区域：方向性降噪，保留叶片边缘纹理
- **4倍超分辨率上采样：** 基于AI的4× SR重建，用于计算变焦和照片放大
- **多摄融合：** 宽角+长焦像素级配准融合

**2. 多帧降噪 (MFNR)**

麒麟ISP的MFNR流程：
- 连续采集4–8帧RAW图像
- 硬件光流引擎执行帧间亚像素对齐
- 加权时域平均：近期帧权重大，运动区域权重降低（防鬼影）
- 对齐结果在RAW域叠加，再经完整ISP链路输出

**3. HDR方案组合**

麒麟ISP支持三种HDR采集方案，可根据场景动态选择：
- **ZHDR（零延迟HDR，Zero-delay HDR）：** 传感器交替行读出，相邻行曝光时间不同，在单帧内实现多曝光采集，无时序延迟，适合高速运动场景
- **LS-HDR（长短帧HDR，Long-Short HDR）：** 传统双帧HDR，长曝光帧捕捉暗部，短曝光帧捕捉亮部，帧间时序差异可能导致运动主体鬼影
- **交错式HDR (Staggered HDR)：** 与ZHDR类似的传感器级多曝光方案，提升帧内动态范围

#### 参考资料

- 华为官方麒麟9000介绍：https://consumer.huawei.com/en/campaign/kirin9000/
- AnandTech 麒麟980深度分析（Mate 20系列评测）：https://www.anandtech.com/show/13371/huawei-mate-20-mate-20-pro-review/4
- Linux内核HiSilicon ISP驱动（开源参考）：https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/media/platform/hisilicon

### 海思麒麟 (HiSilicon Kirin) 公开资源

**OpenHarmony 开源代码（Gitee）**
- Camera HAL 驱动代码：https://gitee.com/openharmony/drivers_peripheral_camera
  OpenHarmony 官方仓库，含摄像头流水线、缓冲区管理、ISP 控制接口定义

- HiSilicon SoC 设备代码：https://gitee.com/openharmony/device_soc_hisilicon
  含传感器驱动 stub 和 ISP 初始化配置

**专利数据库（技术细节最丰富的公开资料）**
- Google Patents 海思 ISP 专利检索：https://patents.google.com/?assignee=HiSilicon+Technologies&q=ISP
  涵盖 AWB、AE、去噪、HDR 色调映射、XD-Fusion 多帧融合等算法专利

- 国家知识产权局（CNIPA）：https://pss-system.cponline.cnipa.gov.cn/
  搜索申请人"海思半导体有限公司" + 分类号 G06T5/H04N23

**华为官方技术资料**
- HuaweiTech 技术期刊（工程师撰写）：https://www.huawei.com/en/huaweitech
  含麒麟 ISP 架构、计算摄影、AI-ISP 等工程师文章

- HarmonyOS Camera API 文档：https://developer.huawei.com/consumer/en/doc/harmonyos-guides/camera-overview
  应用层摄像头 API，展示 ISP 向 OS 暴露的控制接口

**Linux 内核驱动**
- kernel.org HiSilicon 媒体驱动（机顶盒 SoC）：https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/media/platform/hisilicon
  注：主线 Linux 包含海思机顶盒 ISP 驱动；麒麟手机 ISP 未开源

- Linux 内核邮件列表 HiSilicon 补丁：https://lore.kernel.org/linux-media/?q=hisilicon

---

### C.10.3 联发科天玑 Imagiq ISP（MediaTek Imagiq）

#### 架构概述

联发科 Imagiq ISP 是天玑 (Dimensity) SoC 系列的影像处理引擎，自Imagiq 2.0起持续演进，在旗舰Dimensity平台上对标高通和麒麟。

**Imagiq代际演进：**

| 代次 | 对应天玑/平台 | 关键升级 |
|------|------------|---------|
| Imagiq 2.0 | Helio P70 | 双ISP，AI辅助降噪初步集成 |
| Imagiq 5.0 | **天玑1000** | **三路ISP**（2019年），AI-NR，4K HDR |
| Imagiq 790 | **天玑9000** | 320 MP支持，HDR-Vivid首发 |
| Imagiq 890 | **天玑9200** | 杜比视界 (Dolby Vision) 实时采集，900 Mpixel/s |
| Imagiq 990 | **天玑9300** | 4K 120fps HDR视频，实时AI超分，APU 790 **46 TOPS**（官方INT8规格） |
| Imagiq 1090 | **天玑9400** | 生成式AI接入影像链路，APU 910 **50+ TOPS** |

**三路ISP并行（Triple ISP，天玑1000，2019年）**

天玑1000与麒麟990 5G同年（2019年）引入三路ISP，是最早支持三路并行ISP的移动平台之一。天玑9200三路ISP合计吞吐量达900 Mpixel/s。

#### 调参工具链

联发科ISP调参工具为 **MTK相机调参工具 (APMCT, APM Camera Tuning Tool)**，在保密协议 (NDA) 下向合作OEM/ODM授权。

**NVRAM XML参数文件：** 与高通Chromatix类似，联发科使用NVRAM（非易失性随机存取存储器）XML文件存储ISP调参参数，参数按模块和维度组织，烧录至设备NVRAM分区。

**部分开源资源：**
- 联发科HAL层代码在AOSP (Android Open Source Project) 中部分公开
- kernel.org上可查阅天玑平台Linux内核摄像头驱动
- MTK Camera HAL3：https://android.googlesource.com/

**标定流程：**
1. **ColorChecker标定：** 多光源CCM建立
2. **平场校正：** LSC网格提取
3. **噪声模型：** 暗场帧噪声曲线拟合（泊松+读出噪声）
4. **MTF测量：** ISO-12233分辨率板，锐化参数与MTF响应挂钩

#### 特色算法

**1. AI处理引擎 (APE, AI Processing Engine)**

Imagiq的AI模块依托天玑SoC内置的 **APU (AI Processing Unit)** 运行：
- **AI-NR（AI降噪）：** 采用类似超分辨率生成对抗网络 (ESRGAN-style) 的端到端降噪网络，在APU上实时推断，对RAW或YUV域图像进行盲降噪，效果优于传统时域NR
- **AI-SR（AI超分辨率）：** 基于深度学习的超分辨率重建，用于计算变焦场景的数字放大，图像细节保真度高于传统双三次插值
- **语义分割：** NPU推断逐像素语义图（天空/皮肤/建筑/绿植），结果用于：
  - 区域自适应降噪强度控制
  - 区域差异化色调映射
  - 实时散景人像分割

**2. 双摄图像融合 (DCIF, Dual Camera Image Fusion)**

DCIF（双摄像头图像融合）是Imagiq的硬件级多摄融合模块：
- 对宽角摄像头和长焦摄像头的图像进行**硬件像素级配准 (Pixel Registration)**
- 无需主处理器参与，ISP硬件直接完成视差估计与融合
- 应用场景：计算变焦（宽角补充长焦细节）、夜景多摄融合（宽角高感提升SNR，长焦提供细节）

**3. HDR-Vivid 与杜比视界 (Dolby Vision)**

- **HDR-Vivid（天玑9000，Imagiq 790首发）：** 中国标准HDR格式（中国超高清视频产业联盟制定），Imagiq 790是业界首款移动SoC级支持HDR-Vivid格式实时采集
- **杜比视界 (Dolby Vision)（天玑9200起）：** 在Imagiq 890引入硬件级杜比视界实时采集能力，视频帧内元数据逐帧生成，ISP链路输出符合杜比视界规范的HDR10+增强流

**4. 天玑开放资源架构 (Dimensity Open Resource Architecture, 2023)**

联发科2023年推出ORA（开放资源架构），允许OEM厂商在HAL层注入自定义算法：
- OEM可绕过联发科默认ISP算法，插入自研的AI降噪、色彩调校等模块
- 接口以标准Camera HAL3扩展插件形式提供，无需修改内核驱动
- 小米、OPPO等厂商已基于此架构部署自研ISP算法（如小米MIUI ISP）

#### 参考资料

- 联发科Imagiq官方技术页：https://www.mediatek.com/technology/imagiq
- 天玑9200产品页：https://i.mediatek.com/dimensity-9200
- Imagiq 790发布新闻稿：https://corp.mediatek.com/news-events/press-releases/mediatek-imagiq-790-brings-flagship-camera-innovations-to-premium-5g-smartphones

### 联发科 (MediaTek) 公开资源

**官方产品与技术页面**
- MediaTek Imagiq ISP 技术总览：https://www.mediatek.com/technology/imagiq
- 天玑9000产品页（Imagiq 790 ISP规格）：https://www.mediatek.com/products/smartphones-2/dimensity-9000
- 企业新闻稿索引：https://corp.mediatek.com/news-events/press-releases/
- 天玑9200发布（Imagiq 890 / Dolby Vision）：https://corp.mediatek.com/news-events/press-releases/mediatek-launches-dimensity-9200

**学术与技术会议**
- **Hot Chips 34（2022）** — 联发科工程师发表天玑9000芯片架构（含Imagiq ISP），最高深度的公开技术文献：https://hotchips.org/archives/hc34/

**开源内核驱动**
- Linux 内核 MediaTek ISP 驱动（kernel.org mainline）：https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/media/platform/mediatek
- MediaTek 内核补丁提交记录（含ISP设计说明）：https://patchwork.kernel.org/project/linux-mediatek/list/
- V4L2 内核接口文档（MediaTek ISP 暴露给用户空间的接口）：https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/v4l2.html

**Android 相机框架**
- Android Camera HAL3 官方文档：https://source.android.com/docs/core/camera
- AOSP 相机框架源码：https://android.googlesource.com/platform/frameworks/av/+/refs/heads/main/camera/

---

## C.11 三平台横向对比表

### C.11.1 架构与能力对比

| 对比维度 | 高通 Spectra（8 Gen3） | 海思麒麟（麒麟9000） | 联发科 Imagiq（天玑9200） |
|---------|----------------------|-------------------|------------------------|
| **ISP路数** | 三路并行（自SD888起） | 三路并行（自K990 5G起，2019） | 三路并行（自D1000起，2019） |
| **内部精度** | 18位（自8 Gen1起） | 未公开（估计14–16位） | 未公开（估计14位） |
| **专用RAW处理** | BPS（独立硬件子系统） | 无独立BPS（集成于主ISP） | 无独立BPS（集成于主ISP） |
| **AI加速器** | Hexagon DSP/NPU | 达芬奇 (Da Vinci) NPU | APU（AI处理单元） |
| **NPU算力（INT8）** | **45 TOPS**（8 Gen3，官方AI Engine；骁龙X Elite为75 TOPS，系另一产品）| 未公开（麒麟9000，约20 TOPS估计）| 未公开（天玑9200，APU 780；46 TOPS属APU 790即天玑9300）|
| **MFNR帧数** | 30帧（SD888起） | 4–8帧 | 4–8帧 |
| **CFA支持** | 标准RGGB/RYYB（通过传感器） | RGGB + 专属RYYB支持 | 标准RGGB + 部分RYYB支持 |
| **最大像素吞吐** | ~3.2 Gpixel/s（*来源：第三方估算，高通未公开此指标*） | 2.4 Gpixel/s（K990 5G，*来源：公开资料，华为发布会官方数据*） | 900 Mpixel/s（D9200三路合计，*来源：公开资料，联发科天玑9200发布会*） |
| **HDR方案** | Staggered HDR | ZHDR + LS-HDR + Staggered | HDR-Vivid + Dolby Vision |

### C.11.2 调参工具链对比

| 对比维度 | 高通 Spectra | 海思麒麟 | 联发科 Imagiq |
|---------|------------|---------|-------------|
| **调参工具** | Chromatix CTT | HiTuning Tool | APMCT |
| **参数文件格式** | XML（Chromatix） | 未公开 | NVRAM XML |
| **工具可及性** | ODM/OEM合作方，需NDA | 内部工具，不对外 | ODM/OEM合作方，需NDA |
| **ISO维度点数** | 8–12点 | 未公开（约6–10点） | 未公开（约6–10点） |
| **光源类型** | A / TL84 / CWF / D65（4种） | A / TL84 / CWF / D65（类似） | A / TL84 / D65（类似） |
| **开源/公开程度** | 部分AOSP HAL | 极少（Linux驱动部分） | 部分AOSP HAL + ORA开放接口 |
| **自定义算法注入** | 有限（通过HAL插件） | 不支持 | **ORA架构（2023）支持HAL级注入** |

### C.11.3 特色算法对比

| 特色算法 | 高通 Spectra | 海思麒麟 | 联发科 Imagiq |
|---------|------------|---------|-------------|
| 多帧RAW降噪 | MFNR（30帧，SD888+） | MFNR（4–8帧） | MFNR（4–8帧） |
| AI降噪架构 | Hexagon NPU（深度学习） | 达芬奇NPU（深度学习） | APU + ESRGAN风格网络 |
| 语义分割降噪 | 部分支持（8 Gen2+） | 完整语义类别分类 | 完整语义类别分类 |
| AI超分辨率 | 支持（Hexagon） | 4× XD-Fusion SR | AI-SR（APU） |
| 多摄硬件融合 | 支持（三路ISP协同） | XD-Fusion Pro（ISP+NPU） | DCIF（硬件像素配准） |
| HDR防鬼影方案 | Staggered HDR（传感器级） | ZHDR（传感器级） | 交错式HDR |
| 专属HDR格式 | HDR10+（实时采集） | 无专属格式 | HDR-Vivid + Dolby Vision |
| 生成式AI | 支持（8 Gen3，实验性） | 不适用（业务中断） | 支持（D9400 Imagiq 1090） |

---

## C.12 补充说明

### NPU TOPS 速查表（2022–2024 旗舰 SoC，INT8）

> TOPS = Tera Operations Per Second，以 INT8 精度计算。各厂商披露口径不统一：苹果公布独立整数，高通/三星/联发科仅公布相对提升百分比，具体数字可信度见表内标注。

| SoC | NPU | NPU算力（INT8 TOPS） | 发布年份 | 可信度 | 来源 |
|-----|-----|-------------------|---------|-------|------|
| 骁龙8 Gen 2 | Hexagon 780 | **34 TOPS** | 2022 | ★★★☆ 第三方一致 | cpu-monkey；高通官方仅公布相对提升，第三方估算约34 TOPS |
| 骁龙8 Gen 3 | Hexagon NPU | **45 TOPS** | 2023 | ★★★★ 官方AI Engine | 高通骁龙8 Gen 3官方发布页；Spectra 80 triple 18-bit ISP |
| 骁龙8 Elite（8至尊版） | Hexagon NPU | **约65 TOPS** | 2024 | ★★★☆ 官方相对值 | 高通官方称"较8 Gen 3快45%"；45 TOPS×1.45≈65 TOPS |
| 天玑9300 | APU 790 | **46 TOPS** | 2023 | ★★★★ 官方INT8规格 | 联发科APU 790官方规格；Imagiq 990 ISP |
| 天玑9400 | APU 910 | **50+ TOPS** | 2024 | ★★★☆ 官方发布 | 联发科天玑9400发布会；Imagiq 1090 ISP |
| Apple A16 Bionic | Neural Engine（16核） | **17 TOPS** | 2022 | ★★★★★ 官方 | Apple iPhone 14 Pro 发布会官方公告 |
| Apple A17 Pro | Neural Engine（16核） | **35 TOPS** | 2023 | ★★★★★ 官方 | Apple 官方新闻稿；iPad mini A17 Pro 规格页 |
| Apple A18 Pro | Neural Engine（16核） | **38 TOPS** | 2024 | ★★★★☆ 官方/第三方 | Apple iPhone 16 Pro发布；较A17 Pro小幅提升（PhoneArena/Nanoreview确认38 TOPS）|
| Exynos 2400 | GNPU+SNPU | **34.7 TOPS** | 2024 | ★★★☆ 官方规格页 | 三星Exynos 2400官方规格页；NPU单元34.7 TOPS |
| 麒麟9000S | 达芬奇架构2.0（3核） | **N/A**（未公开；中芯7nm工艺制裁限制） | 2023 | ★☆☆☆ 未公开 | 华为/海思未公布；中芯国际N+2工艺，受出口管制 |
| OPPO MariSilicon X | 独立影像NPU（6nm） | **18 TOPS (INT8)** | 2021 | ★★★★★ 官方 | OPPO INNO DAY 2021 官方新闻稿；11.6 TOPS/W |

> ⚠️ **TOPS数字注意事项**
>
> **骁龙8 Gen 3 (45 TOPS)：** 此为高通官方发布页面公布的AI Engine算力。注意：高通 Snapdragon X Elite（PC笔记本芯片）为75 TOPS，是另一款完全不同的产品，不可混淆。
>
> **"官方快XX%"与TOPS整数的换算：** 骁龙8 Elite官方仅称"较8 Gen 3快45%"，换算得约65 TOPS。此类相对值换算时需确认基准芯片的TOPS数。三星"14.7×更快AI"同理——该倍数基于特定基准测试，不等于TOPS整数的相同倍数。
>
> **苹果公布的TOPS数字透明度最高**（A16=17 TOPS，A17 Pro=35 TOPS，A18 Pro=38 TOPS；A18 Pro在Neural Engine架构上有小幅升级）。其他厂商数字如使用相对提升百分比换算，建议注明换算方式。

1. **保密性说明：** 上述高通/麒麟/联发科的具体寄存器参数、调参范围、内部算法实现细节均受各供应商NDA保护，本附录仅汇总公开技术资料和公开发布的白皮书信息。

2. **麒麟业务现状：** 受美国出口管制影响，麒麟9000系列（台积电5nm代工）为目前最新可规模量产的高端麒麟SoC。后续麒麟9000s（华为Mate 60 Pro，中芯国际7nm工艺）已于2023年发布，但产能受限，ISP规格未完整公开。

3. **调参工具获取：** 三家平台的调参工具均需签署NDA并通过厂商合作伙伴资质审核方可获得，个人开发者和学术机构通常无法直接获取。

4. **AOSP参考代码：** 高通和联发科均向AOSP贡献了部分Camera HAL代码，可作为学习参考，但这部分代码不含核心ISP参数调优逻辑。

---

> **注意：** 本附录有意避免提及特定供应商或芯片名称（除C.10–C.11外）。
> 供应商特定对比（流水线阶段数、专有算法名称、
> 具体调参参数列表）请参见 `私有版本仓库/` 中的私有文档。

---

## 习题

**练习 1（理解）**
高通 Snapdragon 8 Gen 3 和联发科 Dimensity 9300 是 2024 年两款主流旗舰 SoC，两者均集成了 ISP 和 NPU。根据公开规格，请对比以下 ISP 功能维度：（1）最高支持的同时活跃摄像头数量（三摄同时预览）；（2）支持的最高视频分辨率/帧率；（3）AI 降噪（AINR）的集成方式（ISP 内置 vs. NPU 独立处理）。分析在这三个维度上，两款平台的设计哲学有何不同？

**练习 2（分析/比较）**
NPU 算力的 TOPS 数值是手机厂商常见的营销数字，但存在诸多注意事项。请解释：（1）INT4 精度下的 TOPS 与 INT8 精度下的 TOPS 数值相同吗？厂商通常用哪种精度报告最大值？（2）第三方估算（如 cpu-monkey、Nanoreview）与芯片厂商官方数据的可信度差异；（3）骡龙 X Elite（PC 笔记本，75 TOPS）与骡龙8 Gen 3（手机，45 TOPS）是不同产品——为什么引用手机 NPU 算力时不能混用 PC 芯片规格？两款芯片在 TDP、制程和应用场景上有何本质差异？

**练习 3（实践）**
设计一个在实际手机上测量 NPU 有效算力的方法。使用 AI Benchmark 或 MobileAIBench 等公开工具，在同一型号手机的骁龙 8 Gen 3 平台上运行标准 MobileNet-V3 推理测试，记录推理延迟和测试工具报告的等效算力。与官方公布数据（45 TOPS）对比：实测结果是否接近官方值？在连续推理 5 分钟后，热降频对推理延迟和等效算力有多大影响？
