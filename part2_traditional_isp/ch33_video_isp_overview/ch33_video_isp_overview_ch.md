# 第二卷第33章：视频ISP全链路综论

> **流水线位置：** 视频录制通路，从传感器出帧到编码器入流的全链路控制
> **前置章节：** 第二卷第03章（降噪）、第二卷第12章（时域NR）、第二卷第05章（AWB）
---

## §1 视频 ISP 与图像 ISP 的本质区别

### 1.1 核心差异对比

| 维度 | 图像 ISP | 视频 ISP |
|------|---------|---------|
| 时间维度 | 单帧独立处理 | 必须利用帧间时域信息 |
| 噪声抑制 | 空域 NR | 时域 NR（TNR）为核心 |
| 运动处理 | 不考虑 | 运动估计（ME）+ 补偿（MC） |
| 实时约束 | 宽松（后处理可接受）| 严格（录像中断不可接受）|
| 稳定性 | 帧间独立，允许切换 | 场景切换须平滑过渡 |
| 编码耦合 | 输出独立图像 | 输出 YUV 流，与编码器深度耦合 |
| 功耗约束 | 可突发降频 | 必须持续满足帧率，功耗恒定 |
| 内存占用 | 单帧 Buffer | 需要 Reference Frame Buffer（多帧） |

### 1.2 视频 ISP Pipeline 全景

```
Sensor RAW (逐帧)
    │
    ▼
前端校正（BLC/LSC/DPC）  ← 同图像ISP
    │
    ▼
时域降噪（TNR）          ← 视频ISP核心差异点
  ├── 运动估计（ME）：Block Matching / Optical Flow
  ├── 帧间融合：运动补偿时域滤波（MCTF）
  └── 运动置信度掩膜
    │
    ▼
Demosaic → AWB → CCM → Gamma
    │
    ▼
电子防抖（EIS）          ← 视频特有，与TNR耦合
    │
    ▼
编码预处理（YUV格式、色度下采样）
    │
    ▼
H.264 / H.265 / H.266 编码器
```

### 1.3 RAW 视频流水线（电影/专业拍摄）

```
Sensor RAW (12/14bit逐帧)
    │
    ▼
RAW 压缩（BRAW / ARRIRAW / CinemaDNG）
    │
    ▼
离线后期 Debayer → HDR Merge → LOG Curve
    │
    ▼
调色（DaVinci Resolve / ACES 色彩管线）
    │
    ▼
输出至 ProRes / DNxHR / H.265 10bit
```

---

### 1.4 视频编码链路：ISP → NR → EE → YUV → H.265/AV1

视频 ISP 的输出不是独立图像文件，而是直接馈入视频编码器的 YUV 码流。完整链路如下：

```
┌──────────────────────────────────────────────────────────────┐
│  RAW 输入（Sensor → MIPI CSI-2）                               │
│  格式：RAW10 / RAW12 / RAW16，Bayer 排列                        │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  ISP 流水线（硬件实现，逐像素流水）                               │
│  BLC → DPC → LSC → Demosaic → AWB → CCM → Gamma             │
│  + HDR 合并（DOL/多曝）→ 3D-NR（BNR+YNR+TNR）→ EE             │
│  输出格式：YUV420（NV12/NV21）或 YUV422                         │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  编码预处理（可选）                                               │
│  ├── 编码预平滑（Pre-filter Gaussian σ=0.5）：降噪→提升编码效率     │
│  ├── 色度下采样（YUV444→YUV420：视觉无损，码率节省 33%）            │
│  └── Rate Control 初始化（目标码率/QP初值）                       │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  视频编码器（硬件加速器）                                          │
│  H.264 / H.265 (HEVC) / H.266 (VVC) / AV1                   │
│  ├── 帧内预测（Intra）+ 帧间预测（Inter, ME+MC）                  │
│  ├── 变换编码（DCT/DST → 量化 → 熵编码）                          │
│  └── 环路滤波（Deblocking + SAO/ALF）                           │
│  输出格式：MPEG-4 / MP4 / MOV / TS 容器                         │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  码流存储 / 网络传输                                              │
│  Flash 存储（手机本地录像）/ RTSP / RTP / DASH / HLS            │
└──────────────────────────────────────────────────────────────┘
```

**ISP 与编码器的关键接口约束**：

| 约束项 | 说明 | 典型规格 |
|--------|------|---------|
| **YUV 格式对齐** | 编码器通常要求行宽（stride）对齐到 16 或 64 字节边界 | NV12: stride = ALIGN(width, 64) |
| **色度格式** | H.265 Main Profile 要求 YUV420，H.265 Main 10 支持 10-bit | NV12（8-bit），P010（10-bit）|
| **延迟预算** | ISP 到编码器输入的总延迟 < 1 帧（33ms @ 30fps） | ISP 流水线延迟通常 < 5ms |
| **帧率同步** | ISP 输出帧率必须与编码器输入帧率严格匹配 | 通过 VSYNC 硬件同步 |
| **HDR 编码** | HDR 内容需配合 10-bit 编码 + HDR 元数据 SEI 写入 | H.265 Main 10 Profile |

**带宽计算公式**：

$$\text{YUV420 带宽} = W \times H \times \text{fps} \times 1.5\;\text{（字节/秒，B/s）}$$

$$\text{RAW12 带宽} = W \times H \times \text{fps} \times 1.5\;\text{（字节/秒，B/s；12bit packed，每2像素3字节）}$$

| 分辨率 × 帧率 | RAW12 输入带宽 | YUV420（NV12）带宽 | H.265 编码后码率（高质量）|
|--------------|--------------|-------------------|----------------------|
| 1080p @ 30fps | 186 MB/s | 93 MB/s | 20~40 Mbps |
| 1080p @ 60fps | 373 MB/s | 186 MB/s | 40~80 Mbps |
| 4K @ 30fps | 746 MB/s | 373 MB/s | 80~150 Mbps |
| 4K @ 60fps | 1.46 GB/s | 746 MB/s | 150~300 Mbps |
| 4K @ 120fps | 2.93 GB/s | 1.46 GB/s | 300~600 Mbps |
| 8K @ 30fps | 2.98 GB/s | 1.49 GB/s | 400~800 Mbps |
| 8K @ 60fps | 5.97 GB/s | 2.98 GB/s | 800~2000 Mbps |

> **注**：YUV420 带宽 = RAW 带宽的约 1/2（RAW12→YUV8 色度子采样减半），实际还需计入 DDR 往返（ISP 读写 + 编码器读取）的双倍计算。8K@60fps 总 DDR 带宽压力约为 12 GB/s，需高带宽内存（LPDDR5X）配合 AFBC 压缩（通常可降低带宽 40~60%）。

> ⚠️ **注：** 以下 AV1 接口适配内容面向未来规划。截至 2025 年，主流移动端 SoC（高通 SM8650、天玑 9400）均不含 AV1 硬件编码器，当前 ISP→AV1 数据路径仅适用于软件编码场景（CPU/GPU），功耗和帧率约束与硬件编码差异显著。

**AV1 编码的视频 ISP 适配**：AV1（AOMedia Video 1）于 2018 年正式发布，相较 H.265 平均节省约 30% 码率。高通方面，Snapdragon 8 Gen 2（2022年）率先引入 AV1 硬件**解码**，Snapdragon 8 Gen 3（2023年）同样仅支持 AV1 硬件**解码**；高通官方已表示移动端可能跳过 AV1 编码直接迈向 VVC，截至 Snapdragon 8 Elite（2024年）移动版 SoC 仍未加入 AV1 硬件**编码**。联发科方面，天玑 9200（2022年）已支持 AV1 硬件**解码**，天玑 9300（2023年）同样仅支持 AV1 硬件**解码**（MediaTek 官方规格页：Video Encoding 仅列 H.264/HEVC，AV1 在 Video Playback 列）；截至目前主流移动 SoC 均未正式量产 AV1 硬件**编码**。ISP 侧需注意：
- AV1 要求 YUV420 10-bit（P010 格式）以获得最优压缩效率
- AV1 的环路滤波（CDEF + Restoration Filter）对 ISP 输出的噪声分布更敏感，过强 YNR 会导致 CDEF 效果下降
- AV1 编码延迟（lookahead buffer）通常比 H.265 大 2–4 帧，需在系统延迟预算中预留

**ISP → 编码器零拷贝（Zero-Copy）缓冲路径架构**

上表中 DDR 带宽数字揭示了一个系统设计关键约束：在 4K@60fps 场景下，ISP 每秒需要向 DDR 写出 746 MB 的 YUV 数据，编码器再从 DDR 读入这 746 MB。若以传统"写入 → CPU 复制 → 读出"路径，同一块数据在 DDR 上被访问 4 次（ISP 写、CPU 读源、CPU 写目标、Encoder 读），实际 DDR 带宽消耗是理论值的 2–4 倍，且引入软件复制延迟（通常 0.5–2 ms/帧）。

零拷贝路径通过 **DMA-BUF 共享缓冲机制**消除中间复制：

```
                    ┌─────────────────────────────────────┐
                    │         共享 DMA-BUF 物理帧缓冲        │
                    │   （ISP 写端 = 编码器读端，同一块 DDR）  │
                    └─────────────┬───────────────────────┘
                                  │ 物理地址相同，不做拷贝
              ┌───────────────────┼───────────────────────┐
              │                   │                       │
      ┌───────▼──────┐    ┌───────▼──────┐    ┌──────────▼──────┐
      │   ISP HW     │    │  3A 统计读取  │    │  Video Encoder  │
      │（产生 YUV 帧） │    │（仅统计数据） │    │（消费 YUV 帧）   │
      └──────────────┘    └──────────────┘    └─────────────────┘
```

**Linux 平台实现**：基于 `dma_buf` 框架，ISP 驱动分配 `DMA_HEAP` 或 `ION` 缓冲后，将 `dma_buf fd` 传递给编码器（V4L2 `VIDIOC_QBUF` with `V4L2_MEMORY_DMABUF`）。ISP 写完一帧后通过 `dma_buf_signal_fence` 释放 "producer fence"，编码器等到 fence 信号后立即读取，全程零拷贝、零 CPU 介入。

**Android 平台实现**：通过 `AHardwareBuffer` / `Gralloc` 分配的 `GraphicBuffer`，相机 HAL 的 ISP 输出直接写入 Gralloc buffer，`MediaCodec` 通过 `Surface` 接口接收同一块 buffer（即 `setInputSurface()` 路径）。编码器在 `Surface` 消费方读取 buffer，不做内存复制。

**零拷贝路径的工程收益与约束**：

| 维度 | 传统拷贝路径 | 零拷贝路径 |
|------|------------|----------|
| DDR 带宽（4K@60fps YUV）| ≈ 2.98 GB/s（双倍读写）| ≈ 1.49 GB/s（写一次读一次）|
| CPU 占用 | 高（memcpy 占用 1–2 CPU 核）| 极低（仅 fence 信令）|
| 帧延迟 | +0.5–2 ms（软件复制时间）| +0.1 ms 以内（fence 开销）|
| AFBC 兼容性 | ISP→CPU 路径不支持 AFBC 压缩 | ISP 直接输出 AFBC 压缩格式，编码器原生读入，带宽再降 40–60% |
| 调试难度 | buffer 状态可在 CPU 侧直接检查 | 需借助 `dmabuf_heap_info` 或 systrace 分析 fence 状态 |

**工程注意事项**：
1. ISP 和编码器的 Gralloc/ION 堆必须兼容（不同 SoC 可能有独立 ISP Heap 和 Codec Heap，地址空间不共享导致零拷贝失效）
2. 多帧 burst 或 TNR 需要 N 帧 Ping-Pong Buffer（N=2–3），总帧缓冲大小 = N × 帧大小；4K@60fps P010 格式约 48 MB/帧，3 帧缓冲需预留 144 MB
3. EIS 场景下引入 Look-Ahead Buffer（通常 3–5 帧），编码器需等待 EIS 确认裁剪参数后才能读取帧数据，零拷贝路径延迟从 <1 帧变为 3–5 帧（100–167 ms @ 30fps），是实时直播场景的主要延迟来源

### 1.5 4K/8K 视频 ISP 带宽详细计算

**内存带宽总需求**（含 TNR 参考帧读写）：

$$\text{总 DDR 带宽} = \underbrace{W \times H \times \text{fps} \times B_{in}}_{\text{RAW 读入}} + \underbrace{W \times H \times \text{fps} \times B_{yuv}}_{\text{YUV 写出}} + \underbrace{N_{ref} \times W \times H \times \text{fps} \times B_{yuv}}_{\text{TNR 参考帧读写}}$$

其中 $B_{in}$ 为 RAW 每像素字节数（RAW12 packed = 1.5），$B_{yuv}$ 为 YUV420 每像素字节数（1.5），$N_{ref}$ 为 TNR 参考帧数（通常 1–2）。

**4K@60fps 示例**（$N_{ref} = 2$）：

$$\text{总带宽} = 3840 \times 2160 \times 60 \times (1.5 + 1.5 + 2 \times 1.5) \approx 5.97\;\text{GB/s}$$

实际设计中还需加上 3A 统计数据、ISP 中间缓存（Ping-Pong Buffer）等开销，总 DDR 需求约为理论值的 1.3–1.5 倍。旗舰手机 LPDDR5-6400 双通道带宽约 **102 GB/s**（64-bit × 2ch，6400 MT/s；低端型号约 60 GB/s 起），远超 8K@30fps 约 15 GB/s 需求，配合 AFBC 压缩（压缩率约 0.5）带宽余量充裕（注：早期资料中"17 GB/s"为单通道 LPDDR4X 水平，"68–77 GB/s"为单通道或低速型号数据，均非 LPDDR5-6400 双通道实际规格）。

---

## §2 全书视频 ISP 技术路线图

手册里视频 ISP 相关内容分散在四卷，下面按技术方向和适用场景整理成路线图，帮你快速定位：

| 章节（卷内编号）| 所在卷 | 技术方向 | 适用场景 | 计算复杂度 | 部署形态 |
|----------------|--------|---------|---------|-----------|---------|
| 第二卷第12章 时域降噪（TNR）| 第二卷 | 传统运动补偿滤波（MCTF/IIR）| 实时视频、边缘部署 | 低（可硬件化）| ISP HW |
| 第二卷第23章 EIS/OIS | 第二卷 | 陀螺仪融合 + 电子防抖 | 手持视频防抖 | 低 | ISP HW |
| 第二卷第25章 RAW 视频/电影 | 第二卷 | RAW 录制 + 离线后期 | 电影/专业拍摄 | 离线 | 工作站 |
| 第二卷第26章 Burst/夜景视频 | 第二卷 | 多帧融合 + 快速 Demosaic | 夜景视频 | 中 | ISP HW + NPU |
| 第三卷第08章 DL 视频降噪 | 第三卷 | 深度学习时序网络（FastDVDnet/RViDeNet）| 云端处理/旗舰手机 NPU | 高 | NPU / GPU |
| 第三卷第10章 DL 视频 ISP | 第三卷 | 端到端神经 ISP（RAW→YUV）| AI 驱动替代传统流水线 | 高 | NPU / GPU |
| 第三卷第12章 DL 视频稳定 | 第三卷 | 深度学习光流 + 去抖 | AI 视频防抖 | 高 | NPU |
| 第四卷第16章 视频 ISP 工程 | 第四卷 | 系统工程（延迟/带宽/功耗）| 芯片/系统设计 | — | 系统层 |
| 第六卷第09章 手机视频 ISP | 第六卷 | 产品化落地 | 消费级手机视频 | 中 | ISP HW + NPU |

> **阅读提示**：若只关注传统算法，重点读第二卷各章；若关注深度学习替代，重点读第三卷；若关注芯片/系统设计，重点读第四卷第14章（多摄系统架构设计）。

---

## §3 全书视频 ISP 内容详细导引

| 章节 | 章节编号 | 主题 | 定位 | 建议读者 |
|------|---------|------|------|---------|
| [ch12_temporal_nr](../../part2_traditional_isp/ch12_temporal_nr/) | 第二卷第12章 | 视频时域降噪（TNR） | 传统方法：MCTF/IIR/ME | 所有视频ISP工程师 |
| [ch23_eis_ois](../../part2_traditional_isp/ch23_eis_ois/) | 第二卷第23章 | 电子/光学防抖（EIS/OIS）| 帧间稳定与裁切机制 | 视频ISP工程师 |
| [ch25_raw_video_cinema](../../part2_traditional_isp/ch25_raw_video_cinema/) | 第二卷第25章 | RAW 视频与电影拍摄 | LOG曲线/RAW编解码/ACES | 影视/专业相机工程师 |
| [ch26_burst_night_mode](../../part2_traditional_isp/ch26_burst_night_mode/) | 第二卷第26章 | Burst/夜景模式 | 多帧对齐融合、HDR视频 | 夜景算法工程师 |
| [ch08_video_denoising](../../part3_dl_isp/ch08_video_denoising/) | 第三卷第08章 | DL 视频降噪 | FastDVDnet、扩散模型视频复原 | DL研究者 |
| [ch10_video_isp](../../part3_dl_isp/ch10_video_isp/) | 第三卷第10章 | 基于 DL 的视频 ISP | 端到端视频质量增强 | DL研究者 |
| [ch12_dl_video_stabilization](../../part3_dl_isp/ch12_dl_video_stabilization/) | 第三卷第12章 | DL 视频稳定 | 深度学习防抖/去抖 | DL研究者 |
| [ch16_video_isp_engineering](../../part4_system_iqa/ch16_video_isp_engineering/) | 第四卷第16章 | 视频 ISP 系统工程 | 延迟/Buffer/功耗/编码器接口 | 系统工程师 |

---

## §4 核心技术概念对比

### 4.1 传统时域 NR vs DL 视频降噪

| 对比维度 | 传统时域 NR（MCTF/IIR）| DL 视频降噪（FastDVDnet 等）|
|----------|----------------------|--------------------------|
| **PSNR 提升**（典型值）| +2 ~ 4 dB（ISO 3200） | +4 ~ 7 dB（ISO 3200） |
| **实时性**（4K30fps）| 可硬件化，实时 | GPU/NPU 可实时，CPU 无法实时 |
| **Ghosting（鬼影率）**| 中等（ME 失效时易出现）| 低（时序注意力抑制运动错误）|
| **部署门槛** | 极低，ISP HW 直接支持 | 高，需 NPU ≥ 10 TOPS |
| **场景适应性** | 需调参（快速运动易失效）| 强（训练数据覆盖多场景）|
| **功耗**（参考值）| < 100 mW（硬件模块）**[3]** | 1~5 W（NPU 推理）**[3]** |
| **内存需求** | 1~2 帧 Reference Buffer | 3~5 帧（时序网络窗口） |
| **对暗光的改善** | 中等，噪声模型固定 | 强，可端到端学习噪声特征 |
| **工程成熟度** | 极高，量产验证多年 | 中，2022 年后逐步量产 |

### 4.2 EIS 传统方法 vs DL 视频稳定

| 对比维度 | 陀螺仪 EIS | DL 光流稳定 |
|----------|-----------|-----------|
| 传感器依赖 | 需陀螺仪硬件 | 纯视觉，无需额外传感器 |
| 延迟 | 低（硬件级）| 高（需缓冲多帧）|
| 裁切率 | 固定（通常 10~15%） | 可变，内容自适应 |
| 滚动快门校正 | 内置 | 需额外网络分支 |
| 量产程度 | 主流旗舰标配 | 2024 年后逐步上量 |

---

## §5 视频 ISP 系统约束速查

### 5.1 典型帧率/分辨率下的系统约束

| 分辨率 × 帧率 | RAW 带宽（12bit）| YUV 带宽（NV12）| TNR Buffer 需求 | 典型端到端延迟 | 参考功耗（ISP）|
|--------------|----------------|----------------|----------------|--------------|--------------|
| 1080p @ 30fps | 186 MB/s | 93 MB/s | 2 × 8 MB | < 33 ms | 200~400 mW |
| 1080p @ 60fps | 373 MB/s | 186 MB/s | 2 × 8 MB | < 16 ms | 400~600 mW |
| 4K @ 30fps | 746 MB/s | 373 MB/s | 2 × 32 MB | < 33 ms | 600 mW ~ 1.2 W |
| 4K @ 60fps | 1.46 GB/s | 746 MB/s | 2 × 32 MB | < 16 ms | 1.2 ~ 2.5 W |
| 4K @ 120fps | 2.93 GB/s | 1.46 GB/s | 3 × 32 MB | < 8 ms | 2.5 ~ 4 W |
| 8K @ 30fps | 2.98 GB/s | 1.49 GB/s | 2 × 128 MB | < 33 ms | 3 ~ 5 W |

> **注**：以上为典型估算值，实际数值取决于 SoC 内存带宽压缩率（如 AFBC）、DDR 位宽和频率配置。功耗数字基于作者对公开 SoC 产品规格（高通 Snapdragon 8 Gen 系列 ISP 功耗分解）和 JEDEC LPDDR5 功耗模型的综合估算，并非来自单一官方数据源；实测值请参考具体平台 Power Profiler 工具测量结果。

### 5.2 关键设计约束

- **端到端延迟**：录像模式通常要求 Sensor 到编码器输入 < 1 帧延迟（33ms @ 30fps）
- **帧同步**：TNR 的参考帧更新必须与曝光参数（AE/AWB）变更严格同步，否则引发亮度闪烁
- **场景切换**：检测到场景切换（如切换镜头）时须立即清空 TNR 历史帧，否则出现鬼影
- **EIS 缓冲**：EIS 需要 look-ahead 缓冲（通常 4~8 帧），会引入额外延迟，须在延迟预算内分配

---

## §6 视频 ISP 核心质量指标

| 指标 | 含义 | 典型工具/方法 |
|------|------|-------------|
| **VMAF** | Netflix 视觉质量指标，综合 VIF/DLM/Motion 特征 | `ffmpeg -vf libvmaf` |
| **BVQI / FastVQA** | 盲视频质量评估（无参考）| [FastVQA GitHub](https://github.com/VQAssessment/FastVQA-and-FasterVQA) |
| **TNR Ghost Ratio** | 鬼影像素占比（运动区域）| 自制测试序列 + 手动标注 |
| **EIS 稳定性** | 残留抖动量（像素级，频域分析）| Gyro-GT 比对 + 频谱分析 |
| **编码 PSNR/SSIM** | 编码后视觉质量 | FFmpeg + SSIM filter |
| **Flicker 指数** | 帧间亮度/色度跳变量 | 逐帧 L/a/b 均值曲线分析 |
| **时域 NIQE** | 视频帧序列的无参考感知质量 | MATLAB Video Quality Toolbox |
| **运动清晰度** | 运动区域边缘的 MTF 保持率 | 运动测试卡 + MTF 工具 |

---

## §7 视频 ISP 主要 Artifact 快速诊断

| Artifact | 现象描述 | 根本原因 | 来源章节 | 应急措施 |
|----------|---------|---------|---------|---------|
| TNR 鬼影 | 运动对象拖影，轮廓模糊 | ME 失效，运动区域被误融合 | 第二卷第12章 §4 | 降低 TNR 强度或关闭 |
| EIS 裁切失真 | 边缘扭曲/黑边/果冻效应 | EIS 裁切参数或 RS 校正异常 | 第二卷第23章 §4 | 降低 EIS 激进度 |
| 编码 Block 效应 | 低码率方块噪声 | 码率不足或 QP 过高 | 第四卷第16章 §4 | 提高目标码率 |
| 色彩闪烁 | AWB 在视频中跳变 | AWB 时域平滑不足 | 第二卷第05章 §5 | 加强 AWB 时域阻尼 |
| Flicker 条纹 | 荧光灯/LED 频率干扰 | Anti-banding 未对齐电网频率 | 第二卷第28章 §2 | 固定曝光时间至 1/50s 或 1/60s |
| 亮度跳变 | 切换镜头或运动时亮度突变 | AE 收敛过快 + TNR 帧未清空 | 第四卷第02章 §3 | 增大 AE 时域平滑系数 |
| 暗角随时间变化 | LSC 参数未随镜头 OIS 位置更新 | OIS 位移改变 LSC 中心 | 第二卷第08章 §3 | 动态更新 LSC 中心坐标 |
| 滚动快门果冻 | 高速运动时画面倾斜/弯曲 | CMOS 逐行曝光 RS 效应 | 第二卷第23章 §2 | 提高 Sensor 帧率或使用 GS Sensor |

---

## §8 读者路径推荐

根据读者背景，推荐最短有效阅读路径：

### 8.1 算法工程师路径（重点：算法原理与调参）

```
本章（全局概览）
    ↓
第二卷第12章 时域降噪 TNR（传统基线）
    ↓
第三卷第08章 DL 视频降噪（深度学习方法）
    ↓
第三卷第10章 DL 视频 ISP（端到端方案）
    ↓
第四卷第16章 系统工程（约束边界）
```

**预计阅读量**：~4 章核心 + 按需扩展

### 8.2 系统/硬件工程师路径（重点：约束、带宽、接口）

```
本章（全局概览 + §5 系统约束速查）
    ↓
第四卷第16章 视频 ISP 系统工程（主攻）
    ↓
第二卷第12章 TNR（了解算法对 Buffer 的需求）
    ↓
第二卷第23章 EIS/OIS（延迟与裁切设计）
```

**预计阅读量**：~3 章核心，算法细节按需

### 8.3 产品/调优工程师路径（重点：Artifact 诊断与参数调整）

```
本章（§7 Artifact 速查 + §9 参数速查）
    ↓
第六卷第09章 手机视频 ISP（产品化经验）
    ↓
第二卷第12章 TNR §4（鬼影调参）
    ↓
第二卷第28章 Anti-banding（Flicker 处理）
```

**预计阅读量**：~3 章 + 按 Artifact 类型跳转

### 8.4 DL 研究者路径（重点：模型结构与训练数据）

```
第二卷第12章 TNR（了解传统基线，明确改进空间）
    ↓
第三卷第08章 DL 视频降噪（主攻）
    ↓
第三卷第10章 DL 视频 ISP（端到端方向）
    ↓
第三卷第12章 DL 视频稳定（防抖方向）
```

**预计阅读量**：~4 章，重点第三卷

---

## §9 关键参数速查：各平台视频 ISP 参数名对照

以下列出各平台在视频 ISP 调参中常用参数，方便跨平台工程师快速映射概念。

### 9.1 时域降噪（TNR）参数

| 概念 | 高通（Qualcomm）| 联发科（MTK）| 海思/麒麟（HiSilicon）| 说明 |
|------|---------------|------------|----------------------|------|
| TNR 强度（整体）| `TNR_MotionThreshold` / `TNRStrength` | `NR_TNR_Strength` | `TnrStrengthLevel` | 全局时域降噪力度 |
| 运动阈值 | `TNR_MotionSAD` | `TNR_MotionSADThresh` | `TnrMotionThresh` | SAD 低于此值认为静止 |
| 运动区域NR系数 | `TNR_MotionBlendFactor` | `TNR_MotionWeight` | `TnrMotionBlendRatio` | 运动区域时域融合权重 |
| 静止区域NR系数 | `TNR_StillBlendFactor` | `TNR_StillWeight` | `TnrStillBlendRatio` | 静止区域时域融合权重 |
| 参考帧数 | `TNR_RefFrameCount` | `TNR_NumRefFrames` | `TnrRefFrameNum` | 用于融合的历史帧数 |
| 场景切换检测 | `TNR_SceneChangeThresh` | `TNR_SceneDetectTh` | `TnrSceneChangeLevel` | 触发 Buffer 清空的阈值 |

### 9.2 电子防抖（EIS）参数

| 概念 | 高通（Qualcomm）| 联发科（MTK）| 海思/麒麟（HiSilicon）| 说明 |
|------|---------------|------------|----------------------|------|
| EIS 使能 | `EIS_Enable` | `EisEnable` | `EisOnOff` | 总开关 |
| 裁切率 | `EIS_CropRatio` | `EisCropFactor` | `EisCropPercent` | 画面裁切比例（0.85~0.9）|
| 平滑强度 | `EIS_SmoothingFactor` | `EisFilterStrength` | `EisSmoothLevel` | 稳定滤波强度 |
| RS 校正 | `RS_CorrectionEnable` | `EisRSCorrection` | `RsCorrEnable` | 滚动快门畸变校正开关 |
| Look-ahead 帧数 | `EIS_LookaheadFrames` | `EisLookAheadNum` | `EisDelayFrames` | 预缓冲帧数（影响延迟）|

### 9.3 视频 AWB 时域平滑参数

| 概念 | 高通（Qualcomm）| 联发科（MTK）| 海思/麒麟（HiSilicon）| 说明 |
|------|---------------|------------|----------------------|------|
| AWB 时域阻尼 | `AWB_VideoConvergeSpeed` | `AwbVideoConvergeFactor` | `AwbVideoSmoothRatio` | 视频模式收敛速度 |
| 色温跳变抑制 | `AWB_CCTDeltaThresh` | `AwbJumpDetectTh` | `AwbCctJumpLevel` | 防止色温突变 |
| 帧间增益平滑 | `AWB_GainSmoothingFactor`| `AwbGainLPFCoeff` | `AwbGainSmoothCoef` | R/B Gain 低通滤波系数 |

> **使用说明**：以上参数名均为典型命名，不同 SoC 版本可能有所差异。具体调参方法参见各章节对应小节及平台 Tuning Guide 文档。

---

## §10 视频 ISP 发展趋势（2024–2026）

| 趋势方向 | 现状 | 近期进展 |
|---------|------|---------|
| NPU 加速 TNR | 旗舰手机逐步落地（如 Pixel 9、iPhone 16）| 传统 HW TNR + DL 后处理混合架构成主流 |
| 端到端视频 ISP | 研究领先，量产探索中 | 手机厂商开始 AB 测试（2024）|
| 4K 120fps 普及 | 高端旗舰已支持 | 中端 SoC（骁龙7系/天玑8200）2025 下探 |
| 视频 HDR（Dolby Vision）| 旗舰标配 | 实时 Tone Mapping 算法持续优化 |
| AI 视频防抖 | Pixel 系列已量产 | 低算力平台适配成关键问题 |
| 生成式视频修复 | 研究阶段 | 扩散模型视频 Deblur/SR 2024 年快速进展 |

---

## §11 延伸阅读

- **书籍**：《Digital Video Concepts, Methods, and Metrics》— Shahriar Akramullah
- **论文综述**：*Deep Learning for Video Super-Resolution: A Survey*（IEEE TPAMI 2023）
- **开源项目**：
  - [FastDVDnet](https://github.com/m-tassano/fastdvdnet)（DL 视频降噪参考实现）
  - [BasicVSR++](https://github.com/ckkelvinchan/BasicVSR_PlusPlus)（视频超分/复原框架）
  - [RAFT](https://github.com/princeton-vl/RAFT)（光流估计，EIS/TNR ME 基础）
- **标准文档**：
  - ITU-T H.265 (HEVC) 主档规范
  - SMPTE ST 2084（HDR PQ 曲线标准）
  - DCI P3 / BT.2020 色域标准

---

*本章是视频 ISP 导引章，无独立代码 Notebook。*
*各子主题代码见对应章节的 本章配套代码（见本目录 .ipynb 文件）。*

---

## §12 视频 ISP 全链路伪影分析（Artifact Analysis）

视频 ISP 伪影的核心特征是**时域可见性**——单帧图像看起来正常，帧间的不一致却会在播放时被人眼察觉。以下逐类分析主要伪影成因、检测方法与工程抑制策略。

### 12.1 时域闪烁（Temporal Flicker）

**成因**

CMOS 传感器采用逐行滚动读出（Rolling Shutter），每行读出时间差约为 $t_{row} = T_{frame} / N_{rows}$。当 AE 控制器在帧与帧之间频繁调整曝光量（尤其在低频交流光源环境，如 50 Hz 荧光灯），曝光量的微小变化叠加滚动读出的时序偏差，会产生全帧亮度震荡——即"闪烁"。

**检测**

帧差直方图方差法：

$$\sigma^2 = \frac{1}{N} \sum_{i=1}^{N} \left( Y_i - \bar{Y} \right)^2$$

其中 $Y_i$ 为第 $i$ 帧归一化全局平均亮度，$\bar{Y}$ 为滑动窗口均值（窗口长度 $W=8$ 帧）。工程判定阈值：$\sigma^2 > 0.5$（归一化0–255尺度下等价 $> 0.008$）时判定为可见闪烁。

**抑制策略**

1. **AE 帧同步收敛**：将 AE 增益/曝光更新严格锁定到 VSYNC 边沿，避免帧内修改。
2. **Anti-banding 补偿**：检测光源频率（50/60 Hz），将快门时间固定为整数倍周期（1/100 s、1/120 s），消除光源调制残差。
3. **AE 收敛速率限幅**：相邻帧曝光变化量 $\Delta EV < 0.1\,\text{EV/frame}$，通过 P-I 控制器平滑。

### 12.2 运动模糊（Motion Blur）

运动模糊是快门开启期间目标位移导致的像素积分模糊，其水平像素宽度为：

$$B_{px} = \frac{v_{obj} \cdot t_{exp}}{d_{scene}} \cdot f_{px}$$

其中 $v_{obj}$ 为目标速度（m/s），$t_{exp}$ 为曝光时间（s），$d_{scene}$ 为目标距传感器距离（m），$f_{px}$ 为焦距对应的像素数（px/m）。

**工程近似**：对于手持视频（1×变焦，主摄 26mm 等效），目标距离 3m 处，步行速度 1.5 m/s，曝光 1/60 s 时：

$$B_{px} \approx \frac{1.5 \times (1/60)}{3} \times 3500 \approx 29\,\text{px}$$

此模糊量已明显超过人眼可接受阈值（约 5–10 px @ 1080p）。

**多帧防抖残余模糊**：EIS（电子防抖）补偿机身抖动引发的模糊，但对**目标自身运动**无效。量产中常见"防抖后运动对象仍模糊"的投诉，根因在于此。解决方向：帧率提升（120fps 模式）或 AI 运动去模糊后处理。

### 12.3 TNR 鬼影（Ghost Artifact）

时域降噪（TNR）依赖运动估计（ME）将参考帧像素对齐到当前帧，若 ME 失败（如遮挡、快速运动、重复纹理误匹配），混合后图像中会出现**双重轮廓**（"鬼影"）——目标在当前位置和参考帧位置各有一个半透明副本。

**成因分析**

MVRef 误配准：参考向量 $\mathbf{v}_{ref}$ 偏离真实运动向量 $\mathbf{v}_{true}$ 超过 2 px 时，两帧叠加后边缘扩散超过可见阈值（约 1 px @ 1080p）。

**SSIM 置信度门控（核心工程手段）**

对每个 8×8 块计算参考帧对齐后的局部 SSIM：

$$\text{SSIM}_{block} = \frac{(2\mu_c\mu_r + C_1)(2\sigma_{cr} + C_2)}{(\mu_c^2 + \mu_r^2 + C_1)(\sigma_c^2 + \sigma_r^2 + C_2)}$$

判断逻辑：

| $\text{SSIM}_{block}$ | 混合策略 |
|---|---|
| $\geq 0.92$ | 全 TNR 混合（$\alpha_{TNR} = 0.7–0.85$） |
| $0.85–0.92$ | 降权混合（$\alpha_{TNR} = 0.3–0.5$） |
| $< 0.85$ | 切换到单帧模式（$\alpha_{TNR} = 0$） |

此门控策略可将鬼影出现率降低 80% 以上，代价是快速运动区域 TNR 增益暂时失效（约 1–3 帧）。

### 12.4 AWB 跳变（AWB Jump）

**现象**：视频录制过程中光源变化（如室外走进室内），AWB 算法快速收敛导致白平衡增益在 1–2 帧内突变，画面出现明显偏色切换——即"跳变"。

**IIR 平滑策略**：

$$G_{wb}^{(t)} = \alpha \cdot G_{wb,\,target}^{(t)} + (1 - \alpha) \cdot G_{wb}^{(t-1)}$$

视频模式推荐 $\alpha = 0.02–0.05$（对比拍照模式 $\alpha = 0.1–0.3$）。在 $\alpha = 0.03$ 时，阶跃响应达到 95% 的帧数约为：

$$N_{95\%} = \frac{\ln(0.05)}{\ln(1 - 0.03)} \approx 98\,\text{帧} \approx 3.3\,\text{s} \;(\text{@30fps})$$

此平滑窗口足以掩盖大多数光源变化场景，且不会引起用户可察觉的"色温漂移"。

### 12.5 视频去噪过平滑（Over-Smoothing）

时域 + 空域联合 NR 在强降噪参数下，运动区域的高频细节（毛发、纹理、文字边缘）会被误判为运动噪声而过滤，导致运动对象"涂抹感"。

**运动掩码引导的自适应 NR 强度**：

$$\sigma_{NR}(x,y) = \sigma_{NR,\,max} \cdot (1 - M_{motion}(x,y)) + \sigma_{NR,\,min} \cdot M_{motion}(x,y)$$

其中 $M_{motion} \in [0,1]$ 为运动概率掩码（由光流幅值归一化得到）。典型参数：$\sigma_{NR,\,max} = 3.0$（静止区域），$\sigma_{NR,\,min} = 0.5$（运动区域）。

运动掩码可由轻量级光流网络（如 PWC-Net-tiny，参数量 < 1M）在 NPU 上实时计算，延迟约 1 ms @ 1080p。

### 12.6 编码伪影（Blocking / Ringing）

H.265/H.266 等基于 DCT 的视频编码在低码率下会引入：

- **块效应（Blocking）**：8×8 / 16×16 CTU 边界处亮度/色度不连续
- **振铃效应（Ringing）**：强边缘附近的 Gibbs 现象，表现为暗纹/亮纹交替

**ISP 预处理缓解策略**：在编码前对原始帧施加轻微低通预处理（编码预平滑，Pre-filter）：

$$I_{prefilter} = I_{raw} * G(\sigma = 0.5\,\text{px})$$

其中 $G(\sigma)$ 为高斯核。此操作将高频噪声能量转移到编码器更容易处理的低频区域，在相同码率下 PSNR 提升约 0.3–0.5 dB，VMAF 提升约 1–2 分。 代价是轻微损失原始分辨率（MTF50 下降约 2–3%），工程中需根据码率档位动态开关。

---

## §13 视频 ISP 评测体系（Evaluation）

视频 ISP 质量评测需同时覆盖**空域质量**（单帧保真度）和**时域稳定性**（帧间一致性）。

### 13.1 时域稳定性指标

**帧间亮度方差（Temporal Luminance Variance）**

$$\sigma_Y = \sqrt{\frac{1}{T} \sum_{t=1}^{T} \left( \bar{Y}_t - \frac{1}{T}\sum_{t'=1}^{T} \bar{Y}_{t'} \right)^2}$$

其中 $\bar{Y}_t$ 为第 $t$ 帧的全局平均亮度（归一化 0–255）。量产验收标准：**$\sigma_Y < 0.5$**（静态场景、均匀光照下）。

**时域 SSIM（TSSIM）**

将传统 SSIM 扩展到相邻帧：

$$\text{TSSIM}(t) = \text{SSIM}(I_t,\, I_{t-1})$$

取 $T-1$ 帧的平均值作为稳定性得分。优秀阈值：$\text{TSSIM} > 0.92$（静态背景区域）。 运动区域需通过光流 warping 补偿后再计算，避免正常运动导致 TSSIM 虚低。

### 13.2 运动清晰度：动态 MTF

**测试方法**：使用 ISO 12233 动态 MTF 测试卡，以固定帧率（30fps/60fps/120fps）在传送带上移动，测量运动场景下的空间频率响应。

**量产目标**：

| 帧率 | 运动速度 | 目标 MTF50 |
|---|---|---|
| 30 fps | 10 px/frame | $> 0.20\,\text{lp/px}$ |
| 60 fps | 10 px/frame | $> 0.25\,\text{lp/px}$ |
| 120 fps | 10 px/frame | $> 0.32\,\text{lp/px}$ |

MTF50 低于阈值通常说明快门时间过长（运动模糊主导）或 NR 过强（过平滑主导）。

### 13.3 视频 SNR（VSNR）

$$\text{VSNR} = 10 \cdot \log_{10}\!\left(\frac{\overline{S}^2}{\sigma_{temporal}^2}\right) \quad \text{[dB]}$$

其中 $\overline{S}$ 为信号均值（均匀灰场亮度），$\sigma_{temporal}^2$ 为同一静态场景下连续 $T=30$ 帧的**时域噪声方差**。VSNR 直接反映 TNR 效果（区别于空域 SNR 受 NR 影响）。

**按 ISO 分档量产目标**：

| ISO | VSNR 目标 |
|---|---|
| ISO 100 | $> 48\,\text{dB}$ |
| ISO 400 | $> 42\,\text{dB}$ |
| ISO 800 | $> 35\,\text{dB}$ |
| ISO 3200 | $> 28\,\text{dB}$ |

### 13.4 VMAF（Video Multi-Method Assessment Fusion）

Netflix 开发的综合视频质量感知指标，融合以下子特征：

- **SSIM**：结构相似度
- **VIF（Visual Information Fidelity）**：基于 HVS 信息保真度
- **ADM（Anti-Distortion Metric）**：细节保留程度
- **Motion Score**：场景运动量（用于模型加权）

使用 SVM 回归将上述特征映射到 [0, 100] 分值，训练集来自 Netflix 内部大规模主观评分数据库。

**量产验收分级**：**[1]**

| VMAF 分值 | 质量等级 |
|---|---|
| $> 85$ | 优秀（Excellent） |
| $75–85$ | 良好（Good） |
| $60–75$ | 可接受（Acceptable） |
| $< 60$ | 差（Poor） |

工具链：`ffmpeg -i ref.mp4 -i dist.mp4 -lavfi libvmaf vmaf_output.json`（基于 libvmaf v2.0）。

### 13.5 KVQ（Kwai 视频质量评分）

KVQ（Kwai Video Quality metric）发表于 CVPR 2024，是针对 UGC（用户生成内容）短视频的**盲参考视频质量评估**指标（Blind VQA），无需参考视频即可预测主观质量分。

**方法要点**：

- 骨干网络：Swin Transformer V2，提取帧级多尺度特征
- 时域建模：Temporal Difference Network，建模相邻帧差异分布
- 质量感知训练：在快手内部 150k 条带主观 MOS 标注的短视频上训练
- 指标：Pearson 相关系数（PLCC）> 0.91，Spearman 相关（SRCC）> 0.90 **[2]**

KVQ 特别针对以下 UGC 失真类型有较高鉴别力：压缩伪影、欠曝噪声、运动模糊、TNR 过平滑，适合手机视频 ISP 量产调优。**[2]**

### 13.6 量产测试标准流程

```
Step 1 — 均匀光场测试（灰卡，D65 标准光源，ISO 100–6400 阶梯）
         → 测量 VSNR、帧间亮度方差 σ_Y、TNR 收敛帧数

Step 2 — 动态清晰度测试（ISO 12233 动态 MTF 卡，30/60/120fps）
         → 测量各帧率/运动速度下 MTF50

Step 3 — 色彩稳定性测试（X-Rite 24 色卡，D65→A 光源切换）
         → 测量 AWB IIR 收敛时间、色温跳变量（ΔCCTs）

Step 4 — 标准视频序列（EBU Tech 3299 测试序列 + Netflix Open Content）
         → 测量 VMAF、TSSIM、时域 SNR

Step 5 — 暗光视频测试（Lux = 1/3/10，钨丝灯/荧光灯/LED）
         → 重点测量闪烁σ²、鬼影出现率、过平滑指数（NIQE变化量）
```

---

## §14 视频 ISP 与 3A 的协同（System Integration）

### 14.1 视频模式 AE：速度与稳定性权衡

**P-I 控制器模型**

视频 AE 控制器通常采用比例-积分（PI）结构：

$$\Delta EV^{(t)} = K_p \cdot e^{(t)} + K_i \cdot \sum_{\tau=0}^{t} e^{(\tau)}$$

其中误差 $e^{(t)} = Y_{target} - Y_{mean}^{(t)}$（归一化亮度）。

**量产推荐参数**：$K_p = 0.15$，$K_i = 0.03$（30fps 录像模式）。

此参数组合的阶跃响应特性：

| 参数 | 值 |
|---|---|
| 稳态误差 | 0 |
| 超调量 | < 5% |
| 2% 稳定时间 | 约 12 帧（0.4 s @ 30fps） |
| 单帧最大变化量 | $\Delta EV_{max} < 0.12$ |

参数过激（$K_p > 0.3$）会导致曝光震荡（"AE 呼吸效应"）；过保守（$K_p < 0.05$）则导致 AE 收敛过慢，场景切换后亮度过暗/过曝持续数秒。

**场景切换检测**：当帧间亮度差 $|\Delta Y| > 0.15$ 时，临时切换到更激进参数（$K_p = 0.4$，单帧快速收敛），收敛后恢复正常参数，避免"AE 迟钝"投诉。

### 14.2 视频模式 AWB：IIR 时间常数设计

**核心约束**：

| 场景 | 推荐 $\alpha$ | 理由 |
|---|---|---|
| 静止视频（室内固定光） | 0.02–0.03 | 最大程度平滑，防止轻微闪烁诱发AWB漂移 |
| 运动视频（户外移动） | 0.04–0.05 | 允许适度跟踪光照变化 |
| 场景切换（大 ΔCCTs） | 临时 0.15–0.20 | 快速适应后回落到正常 α |

**锁定策略**：当 AF 锁定（用户半按快门录像）时，AWB 同步锁定，防止因 AE 变化带来的色温估计扰动。

### 14.3 视频连续 AF（CDAF）与对焦拉锯抑制

**CDAF 基本流程**：

1. 计算当前帧 ROI 区域高频能量：$F = \sum_{x,y} |\nabla^2 I(x,y)|^2$（拉普拉斯能量）
2. 比较 $F^{(t)}$ 与前后帧 $F^{(t-1)}$，判断对焦方向（爬山算法）
3. 步长自适应：远离焦点时大步（40–80 步进），接近时小步（5–10 步进）

**对焦拉锯（Focus Hunting）抑制**：

对焦拉锯是 CDAF 在焦点附近反复振荡的现象，在主体运动或 AE 变化时尤为明显。抑制策略：

- **滞后阈值**：仅当清晰度变化 $|\Delta F / F| > 3\%$ 时才触发马达步进
- **锁定计时器**：连续 $N=5$ 帧清晰度稳定（$\sigma_F < 1\%$）后进入 AF Lock，锁定期间暂停 AF 搜索
- **运动-AF 解耦**：检测到主体快速运动时（光流幅值 > 20 px/frame），暂停 AF，待运动停止后重启搜索

### 14.4 多摄切换平滑（Multi-Camera Seamless Zoom）

高端手机变焦录像中，主摄（1×）切换到长焦（3×/5×）是高频用户操作。无感切换的核心工程指标：

**曝光同步**：切换前后曝光量差 $|\Delta EV| < 0.3$，超出时预先调整被切换摄像头的 AE 至目标附近（预收敛）。

**白平衡同步**：切换前将目标摄像头 AWB 增益拉近到主摄当前增益（在切换前 5–10 帧开始靠拢），切换时色温差 $|\Delta CCT| < 200\,K$。

**帧同步**：两摄传感器帧同步误差 < 1 ms（使用 MIPI FS/FE 同步信号）。

**量产测试标准**：录制 30 s 变焦视频，在 1×↔3× 反复切换 10 次，盲评评分（1–5 分）≥ 4.0 为合格，切换帧 VMAF 跌落 < 5 分。

---

## §15 术语表（Glossary）

**VMAF（Video Multi-Method Assessment Fusion）**
Netflix 开发并开源（libvmaf）的综合感知视频质量指标，通过融合 SSIM、VIF（Visual Information Fidelity）、ADM（Anti-Distortion Metric）等子指标，并用 SVM 回归拟合主观评分，最终输出 [0,100] 的综合质量分值。VMAF v2.0 在 4K HDR 内容上经过重新训练，是当前流媒体行业事实上的视频质量评测标准。

**TSSIM（Temporal SSIM）**
将经典 SSIM（Structural Similarity Index）应用于视频相邻帧之间，度量帧间结构一致性的时域扩展指标。TSSIM 高表示视频时域平稳（无闪烁、无跳变），是评估 AE/AWB 稳定性和 TNR 鬼影的核心量化工具。

**TNR（Temporal Noise Reduction，时域降噪）**
利用视频时间轴上多帧之间的强相关性（同一静止场景的时间样本近似为同分布随机变量），通过运动估计对齐 + 加权融合抑制随机热噪声。TNR 是视频 ISP 中降噪效果最显著的模块（理论上 $N$ 帧融合可得 $\sqrt{N}$ 倍 SNR 提升），也是鬼影伪影的主要来源。

**CDAF（Contrast Detection Auto Focus，对比度检测自动对焦）**
通过分析图像清晰度梯度（拉普拉斯能量、Tenenbaum 梯度等）判断当前对焦位置是否在景深范围内，并驱动镜头马达向清晰度最大值方向移动的对焦方式。相比 PDAF（相位检测 AF），CDAF 无需专用像素，但收敛速度较慢，在视频连续 AF 中通常与 PDAF 融合使用。

**KVQ（Kwai Video Quality metric）**
快手国际版（Kwai）技术团队于 CVPR 2024 提出的盲参考视频质量评估指标（Blind VQA），无需参考视频即可预测 UGC 短视频的感知质量分。网络架构结合 Swin Transformer V2 骨干与时域差分建模，在快手内部 150k 条带主观评分的短视频数据集上训练，对压缩伪影、噪声、运动模糊、过平滑等失真类型有较高鉴别力。

**AE 呼吸效应（AE Breathing / Exposure Oscillation）**
视频录制中 AE 控制器参数过于激进（比例系数 $K_p$ 过大）时，曝光量在目标值附近反复震荡的现象，表现为画面亮度"一明一暗"周期性变化。通过合理设置 P-I 控制器参数（典型 $K_p = 0.15$）和最大单帧变化量限幅（$\Delta EV_{max} < 0.12$）可有效抑制。

**EIS（Electronic Image Stabilization，电子防抖）**
通过陀螺仪测量机身运动，利用数字裁切（Digital Crop）或光流 Warp 补偿帧间位移，实现视频防抖的纯软件/DSP 算法。EIS 补偿机身抖动引发的全局运动，不能补偿拍摄主体自身运动导致的运动模糊。区别于 OIS（光学防抖），OIS 通过物理移动镜组实现，两者在旗舰机中通常协同使用（OIS+EIS 混合防抖）。

**Rolling Shutter（卷帘快门）**
CMOS 传感器逐行读出的机制，每行采样时刻不同（行间隔约 $30\,\mu\text{s}$），导致快速运动场景出现"果冻效应"（Jello Effect）。视频 ISP 中 AE 闪烁、EIS 校正残差均与 Rolling Shutter 特性密切相关。部分旗舰传感器（如 Sony IMX989）支持 Global Shutter 模式以消除此问题。

---

## 进入第三卷之前

第二卷做的事，用一句话总结：在已知的物理边界和有限的算力预算内，用规则和近似把每一个问题解到"够用"的程度。去马赛克不能违反奈奎斯特，降噪不能制造不存在的信号，AWB不能让增益覆盖整个色度空间——每个模块背后都有一条不可逾越的物理约束，工程师的工作是在约束内找最优的近似。

这套方法论极其稳固。它已经运行了二十年，在数十亿台设备上通过了考验。但它有一个根本性的局限：每个模块的设计假设是独立的，优化目标是局部的，没有全局联合优化的机制。去马赛克假设图像是分段光滑的，降噪假设噪声是高斯分布的，AWB假设场景颜色均值为灰——这些假设在大多数场景下成立，在少数极端场景下会同时失效，而且彼此之间不通气。

第三卷的出发点不是颠覆这些模块，而是问一个不同的问题：如果允许网络同时看到输入和期望输出，端到端学习能不能绕过这些独立假设，找到传统流水线找不到的联合最优解？以及，这个代价是多少，工程上怎么接入？

---

> **工程师手记：视频ISP的时间连续性优先原则**
>
> **时序连续性高于单帧质量：** 视频ISP与图片ISP的根本区别在于：观众对帧间抖动的容忍度极低，而对单帧细节损失的容忍度相对较高。实践中见过多个案例——把图片ISP算法直接移植到视频链路，单帧PSNR提升了0.8 dB，但30 fps实拍时AE增益在±3 EV场景中每帧跳动幅度达到0.12 EV，观感上比旧算法差。参数平滑是强制性要求，不是可选优化：曝光时间步长须经低通滤波（典型时间常数3–5帧），白平衡增益在色温突变场景限速在每帧不超过50 K，降噪强度变化须滑动平均。时序连续性评估指标包括帧间亮度方差、色温时间序列的一阶差分均值，这两项应与PSNR/SSIM并列进入视频ISP质量看板。
>
> **视频调色流水线的接入点设计：** 专业视频工作流中，ISP输出通常接入调色系统（DaVinci Resolve、Baselight等）的一级校色节点之前。ISP工程师需要明确：若交付LOG视频（Log-C、S-Log3、V-Log），编码前须保证至少12-bit精度，因为LOG编码本身会将16 bit原始数据压缩到编解码器容忍的范围，量化噪声会在调色拉伸操作后放大。实测显示，10 bit LOG编码在大幅提亮时（+3 EV）会出现约1.5 DN的量化台阶可见性，12 bit可降至0.3 DN以下。视频ISP应在输出阶段提供至少一路12 bit LOG bypass路径，供后期使用，同时提供一路8 bit SDR路径供直出监看。
>
> **LOG视频到LUT转换的精度要求：** LOG-to-Display LUT（3D LUT，通常33×33×33节点）的生成精度直接决定色彩还原上限。节点间距过大会导致高饱和色（RED、BLUE通道>90%编码值）出现色相偏移，典型偏移量在3–5°之间，肉眼在面部皮肤色还原中可察觉。工程建议：LUT生成时对饱和色区域插入额外节点（65×65×65局部），转换误差从平均ΔE 0.8降至ΔE 0.3；LUT文件格式优先使用.cube（64 bit浮点），不使用.3dl（16 bit定点），避免在极端曝光区间引入截断误差。
>
> *参考：Charles Poynton, "Digital Video and HD: Algorithms and Interfaces", 2nd ed., Morgan Kaufmann 2012；Sony "S-Log3 Technical Paper", 2014；ARRI "LogC3 White Paper", 2022*

## 插图

![isp pipeline understanding](img/fig_isp_pipeline_understanding_ch.png)
*图1. ISP管线整体理解框架，从传感器物理模型到输出编码的各模块功能定位与依赖关系综述（图片来源：作者，ISP手册，2024）*

![video isp pipeline](img/fig_video_isp_pipeline_ch.png)
*图2. 视频ISP处理管线架构，展示时域降噪、EIS防抖、帧率控制与视频编码的协同处理流程（图片来源：作者，ISP手册，2024）*

![video isp vs still](img/fig_video_isp_vs_still_ch.png)
*图3. 视频ISP与静态图像ISP的关键差异对比，从帧率约束、时域一致性要求与功耗预算等维度分析两者设计取舍（图片来源：作者，ISP手册，2024）*

![video pipeline overview](img/fig_video_pipeline_overview_ch.png)
*图4. 视频处理管线全景概览，涵盖前端RAW处理、中端色彩还原、后端视频增强与压缩编码的层级结构（图片来源：作者，ISP手册，2024）*

![video quality metrics](img/fig_video_quality_metrics_ch.png)
*图5. 视频质量评估指标体系，对比PSNR、SSIM、VMAF与主观MOS评分在不同失真类型下的相关性（图片来源：作者，ISP手册，2024）*

## 习题

**练习1（理解）** 视频 ISP 与静态图像 ISP 的核心差异在于时间维度的利用。列举视频管线中三个与"时间"相关的模块，并说明各模块利用时序信息的方式（帧间对齐 vs. 帧间融合 vs. 防抖）。

**练习2（计算）** 一段 4K@60fps HDR10 视频，bit depth 为 10-bit，未压缩的原始码率是多少 Mbps？若目标存储码率为 80 Mbps（H.265），压缩比约为多少？

**练习3（工程分析）** EIS（电子防抖）在裁剪 10% 视频边缘后，有效 FOV 会缩小多少（以对角线计）？若原始为 108° FOV，防抖后 FOV 是多少？说明为什么高端旗舰手机通常将 OIS+EIS 组合而非单独使用 EIS。

## 参考文献

[1] Li et al., "VMAF: The Journey Continues", *博客/公众号*, 2018. URL: https://netflixtechblog.com/vmaf-the-journey-continues-44b51ee9ed12

[2] Lu et al., "KVQ: Kwai Video Quality Assessment for Short-form Videos", *CVPR*, 2024.

[3] Tassano et al., "FastDVDnet: Towards Real-Time Deep Video Denoising Without Flow Estimation", *CVPR*, 2020.

[4] ISO, "ISO 12233:2017 — Photography — Electronic Still-Picture Imaging — Resolution and Spatial Frequency Responses", *官方文档*, 2017.

[5] Chen et al., "An Overview of Core Coding Tools in the AV1 Video Codec", *IEEE Transactions on Circuits and Systems for Video Technology*, 2020.

[6] Sullivan et al., "Overview of the High Efficiency Video Coding (HEVC) Standard", *IEEE Transactions on Circuits and Systems for Video Technology*, 2012.

[7] ARM Ltd., "Arm Frame Buffer Compression (AFBC) v1.3 Specification", *官方文档*, 2021.

[8] Yang et al., "Efficient Video Denoising via Spatiotemporal Modeling with Adaptive Deformable Networks", *IEEE Transactions on Circuits and Systems for Video Technology*, 2024.
