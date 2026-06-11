# 附录F — 基准测试结果 | Benchmark Results

> 本附录汇总了ISP各主要任务在标准数据集上的代表性最优（SOTA）性能指标，供研究者快速查阅各方法的量化表现。
> 数据集详细介绍见**附录E**；各方法的完整论文引用见**附录H**。
>
> **说明：**
> - PSNR（Peak Signal-to-Noise Ratio，峰值信噪比）单位为 dB，值越高越好。
> - SSIM（Structural Similarity Index Measure，结构相似性指数）范围 0–1，值越高越好。
> - 所有结果均来自对应论文或官方排行榜，部分数字因测试协议细微差异可能与他处略有出入。
> - ⭐ 标注当年同类方法中表现最优的结果。

---

## F.1 图像去噪基准

### F.1.1 SIDD sRGB 去噪排行榜

**数据集：** SIDD（Smartphone Image Denoising Dataset）验证集，真实手机噪声，sRGB 域。
**在线排行榜：** https://www.eecs.yorku.ca/~kamel/sidd/benchmark.html
**评估协议：** 在 SIDD 验证集的 1280 个裁剪块（256×256）上计算 PSNR 和 SSIM，与高质量参考图对比。

真实噪声去噪是评估 ISP 核心去噪能力的标准任务。SIDD 基准于 2018 年发布，目前已成为学术界最广泛引用的真实去噪排行榜。下表列出从传统方法到最新 Transformer/Mamba 架构的代表性结果，按年份升序排列。

| 方法 | 发表年份/会议 | PSNR (dB) ↑ | SSIM ↑ | 备注 |
|------|-------------|-------------|--------|------|
| BM3D | 2007, TIP | 25.65 | 0.685 | 经典块匹配滤波基线 |
| DnCNN | 2017, TIP | 23.66 | 0.583 | 早期 CNN 去噪；此处为高斯噪声迁移 |
| FFDNet | 2018, TIP | 30.87 | 0.873 | 噪声水平图引导 CNN |
| CBDNet | 2019, CVPR | 33.28 | 0.868 | 含噪声估计子网络；真实噪声建模 |
| RIDNet | 2019, ICCV | 38.71 | 0.951 | 残差注意力特征蒸馏 |
| DANet | 2019, NeurIPS | 39.25 | 0.955 | 双分支注意力网络 |
| AINDNet | 2020, CVPR | 38.84 | 0.951 | 自适应实例归一化 |
| MPRNet | 2021, CVPR | 39.71 | 0.958 | 多阶段渐进恢复；多任务 SOTA |
| MAXIM | 2022, CVPR | 39.96 | 0.960 | 多轴 MLP-Mixer 架构 |
| Restormer | 2022, CVPR | 40.02 | 0.960 | ⭐ Transformer；高效自注意力 |
| NAFNet | 2022, ECCV | 39.99 | 0.960 | 无激活函数简化基线；速度快 |
| KBNet | 2023, ICCV | 40.19 | 0.962 | 核自适应去噪 |
| DnSwin | 2023, AAAI | 40.11 | 0.961 | Swin Transformer 去噪 |
| MambaIR | 2024, ECCV | 39.89 | 0.963 | ⭐ 状态空间模型（Mamba）去噪 |
| RCDNet+ | 2024, TPAMI | 40.28 | 0.962 | 滚动投影深度展开 |

> **注：** BM3D/DnCNN/FFDNet 的 SIDD 数字来自原始 SIDD 论文与后续对比实验，部分方法使用了更新的重测结果，不同论文测试设置略有差异。

---

### F.1.2 DND sRGB 去噪排行榜

**数据集：** DND（Darmstadt Noise Dataset），50 张消费相机真实噪声图像（4 台相机：Nikon D600/D800、Sony A7R、Olympus E-M10），1000 个裁剪块在线评估。
**在线排行榜：** https://noise.visinf.tu-darmstadt.de/benchmark/
**注意：** DND 真值不公开，需向官方服务器提交结果获取评分，防止过拟合。

| 方法 | 发表年份/会议 | PSNR (dB) ↑ | SSIM ↑ | 备注 |
|------|-------------|-------------|--------|------|
| BM3D | 2007, TIP | 34.51 | 0.851 | 传统基线 |
| FFDNet | 2018, TIP | 34.40 | 0.848 | 高斯噪声水平迁移 |
| CBDNet | 2019, CVPR | 38.06 | 0.942 | 噪声估计-去噪联合 |
| RIDNet | 2019, ICCV | 39.26 | 0.953 | — |
| DANet | 2019, NeurIPS | 39.58 | 0.955 | — |
| MPRNet | 2021, CVPR | 39.80 | 0.954 | — |
| Restormer | 2022, CVPR | 40.03 | 0.956 | ⭐ — |
| NAFNet | 2022, ECCV | 39.96 | 0.955 | — |
| MambaIR | 2024, ECCV | 40.21 | 0.957 | ⭐ — |

---

### F.1.3 RAW 域去噪基准

RAW 域去噪在 ISP 前端进行，保留线性光强关系，避免 sRGB gamma/色调映射带来的噪声分布变形，近年受到更多关注。

**数据集：** SIDD RAW（与 SIDD sRGB 同场景，但对应 RAW 裁剪块）；ELD 数据集（极低光 RAW，Sony A7S2/Nikon D850）。

| 方法 | 发表年份/会议 | 数据集 | PSNR (dB) ↑ | SSIM ↑ | 备注 |
|------|-------------|--------|-------------|--------|------|
| CameraNet | 2019, TIP | SIDD RAW | 37.42 | 0.929 | RAW+ISP 联合网络 |
| ELD | 2021, TPAMI | ELD | 47.73 | 0.969 | 物理噪声模型合成数据 |
| PMN | 2022, CVPR | ELD | 48.56 | 0.974 | ⭐ 物理模型引导去噪 |
| LEIDA | 2023, ICCV | ELD | 48.91 | 0.975 | 低曝光 RAW 去噪 |
| RAWiSP | 2023, CVPR | SIDD RAW | 38.16 | 0.936 | RAW-to-RAW 去噪再 ISP |

---

## F.2 超分辨率基准

### F.2.1 经典超分辨率（×4，合成降质）

**降质协议：** bicubic ×4 下采样（BI 协议）——合成基准，非真实降质。
**评估数据集：** Set5（5张）、Set14（14张）、BSD100（100张）、Urban100（100张城市场景）、Manga109（109张漫画）。
**评估指标：** 亮度通道（Y 通道）PSNR/SSIM，与 HR 真值对比，边框裁掉与下采样倍数等宽像素。

下表统一列出 ×4 超分在标准合成测试集上的 PSNR（dB），便于横向比较各架构。

| 方法 | 年份/会议 | Set5 | Set14 | BSD100 | Urban100 | 备注 |
|------|---------|------|-------|--------|----------|------|
| Bicubic（基线） | — | 28.42 | 26.00 | 25.96 | 23.14 | 插值基线 |
| SRCNN | 2014, ECCV | 30.48 | 27.50 | 26.90 | 24.52 | 首个 CNN 超分 |
| VDSR | 2016, CVPR | 31.35 | 28.01 | 27.29 | 25.18 | 残差学习 |
| LapSRN | 2017, CVPR | 31.54 | 28.19 | 27.32 | 25.21 | 拉普拉斯金字塔 |
| EDSR | 2017, CVPRW | 32.46 | 28.58 | 27.57 | 26.64 | ⭐ 去掉 BN 的深残差网络 |
| RDN | 2018, CVPR | 32.47 | 28.81 | 27.72 | 26.61 | 密集残差网络 |
| RCAN | 2018, ECCV | 32.63 | 28.87 | 27.77 | 26.82 | 通道注意力残差网络 |
| SAN | 2019, CVPR | 32.64 | 28.92 | 27.78 | 26.79 | 二阶非局部注意力 |
| HAN | 2020, ECCV | 32.64 | 28.90 | 27.80 | 26.85 | 整体注意力网络 |
| IPT | 2021, CVPR | 32.64 | 29.01 | 27.82 | 27.26 | 预训练 Transformer |
| SwinIR | 2021, ICCV Workshop | 32.72 | 28.94 | 27.83 | 27.07 | ⭐ Swin Transformer 超分 |
| ELAN | 2022, ECCV | 32.75 | 28.96 | 27.83 | 27.10 | 高效局部注意力 |
| HAT | 2023, CVPR | 32.92 | 29.15 | 27.97 | 27.87 | ⭐ 混合注意力 Transformer |
| OmniSR | 2023, CVPR | 32.87 | 29.10 | 27.92 | 27.45 | 全尺度注意力 |
| MambaIR-SR | 2024, ECCV | 32.95 | 29.17 | 28.01 | 27.99 | ⭐ Mamba 超分 |

> **在线排行榜参考：** https://paperswithcode.com/sota/image-super-resolution-on-set5-4x-upscaling

---

### F.2.2 真实世界超分辨率

真实世界超分使用未知/复合降质（压缩、模糊、噪声混合），与合成 bicubic 降质差距显著，指标通常采用无参考 IQA 或感知指标。

| 方法 | 年份/会议 | 主要目标数据集 | NIQE ↓ | LPIPS ↓ | 备注 |
|------|---------|------------|--------|---------|------|
| RealSR | 2020, CVPR | RealSR | 4.62 | 0.181 | 真实相机对数据 |
| BSRGAN | 2021, ICCV | 合成真实降质 | 4.08 | 0.153 | 随机降质流水线 |
| RealESRGAN | 2021, ICCV Workshop | 合成真实降质 | 3.87 | 0.148 | ⭐ 高阶降质模型+U-Net 判别器 |
| SwinIR-GAN | 2021, ICCV Workshop | DRealSR | 4.34 | 0.156 | GAN 损失 Swin 超分 |
| LDL | 2022, CVPR | 合成 | 3.66 | 0.142 | 局部频谱细节损失 |
| DASR | 2023, CVPR | 合成真实 | 3.55 | 0.135 | ⭐ 退化感知超分 |

---

### F.2.3 Manga109 ×4 超分辨率专项

Manga109 包含漫画图像，高对比度纹理结构，通常 PSNR 最高，单独列出。

| 方法 | 年份 | Manga109 PSNR (dB) ↑ | Manga109 SSIM ↑ |
|------|------|---------------------|----------------|
| EDSR | 2017 | 36.55 | 0.967 |
| RCAN | 2018 | 37.43 | 0.971 |
| SwinIR | 2021 | 38.35 | 0.975 |
| HAT | 2023 | 39.10 | 0.977 |
| MambaIR-SR | 2024 | 39.22 | 0.978 |

---

### F.2.4 NTIRE 2024 超分辨率挑战赛结果

**挑战赛：** NTIRE 2024（CVPR Workshop），SR 赛道涵盖经典 SR（×4 BI 降质）、RAW 图像超分、盲去噪等多个子赛道。
**主办方报告：** Timofte et al., "NTIRE 2024 Challenge on Image Super-Resolution," CVPRW 2024.

**主赛道结果（×4 BI 降质，DIV2K 验证集）：**

| 排名 | 方法描述 | DIV2K PSNR ↑ | 备注 |
|------|---------|-------------|------|
| 🥇 冠军 | HAT 变体 + 大规模自集成 | ~33.30 | Transformer + 多模型投票 |
| 🥈 亚军 | SRFormer 变体 + 知识蒸馏 | ~33.22 | 轻量化 Transformer SR |
| 🥉 季军 | RDN + Mamba Hybrid | ~33.18 | CNN + SSM 混合架构 |

**RAW 超分赛道（手机传感器 RAW）：** 冠军方案采用多阶段 RAW-UNet（去马赛克 + 超分 + Gamma），与 ISP 流水线紧耦合。

**NTIRE 2024 关键观察：**
- 模型自集成（self-ensemble + model-ensemble）是竞赛冠军的核心手段，带来约 +0.15 dB 增益
- Mamba 架构在多个赛道进入 Top-5，验证了 SSM 在超分领域的竞争力
- RAW 超分赛道首次出现：直接从 RAW 域超分辨率（无需先去马赛克）成为新研究方向

---

### F.2.5 视频超分辨率 — REDS4 基准

**数据集：** REDS（Nah et al., CVPRW 2019），常用 REDS4 子集（4 段视频）作为快速验证集。
**降质协议：** ×4 双三次下采样，Y 通道 PSNR。
**在线排行榜：** https://paperswithcode.com/sota/video-super-resolution-on-reds4-4x-upscaling

| 方法 | 年份/会议 | REDS4 PSNR (dB) ↑ | REDS4 SSIM ↑ | 备注 |
|------|---------|-------------------|-------------|------|
| Bicubic（基线） | — | 26.14 | 0.7292 | 插值基线 |
| TOFlow | 2019, IJCV | 27.98 | 0.7990 | 光流时序对齐 |
| EDVR | 2019, CVPRW | **31.09** | 0.8800 | ⭐ 可变形对齐 + 时序融合注意力 |
| BasicVSR | 2021, CVPR | 31.42 | 0.8909 | 双向传播超分 |
| IconVSR | 2021, CVPR | 31.67 | 0.8948 | 关键帧增强 BasicVSR |
| BasicVSR++ | 2022, CVPR | **32.39** | 0.9069 | ⭐ 二阶网格传播 + 可变形对齐 |
| VRT | 2022, TIP | 34.81 | 0.9294 | ⭐ 视频复原 Transformer |
| RVRT | 2022, NeurIPS | 34.92 | 0.9313 | 循环视频复原 Transformer |

> **注：** EDVR（31.09 dB）和 BasicVSR++（32.39 dB）是视频超分领域最常引用的基准值，均来自对应论文的官方复现结果。

---

## F.3 图像去模糊基准

### F.3.1 运动去模糊 — GoPro 数据集

**数据集：** GoPro（2017, CVPR），2103 对训练图像 + 1111 对测试图像，分辨率 1280×720，运动模糊由高速相机帧平均合成。
**在线排行榜：** https://paperswithcode.com/sota/deblurring-on-gopro
**评估指标：** PSNR（dB）和 SSIM，全分辨率图像，与 GT 锐利帧对比。

| 方法 | 年份/会议 | GoPro PSNR (dB) ↑ | GoPro SSIM ↑ | 备注 |
|------|---------|------------------|-------------|------|
| DeblurGAN | 2018, CVPR | 28.70 | 0.858 | GAN 去模糊开创性工作 |
| DeblurGAN-v2 | 2019, ICCV | 29.55 | 0.934 | FPN 特征金字塔 |
| DMPHN | 2019, CVPR | 31.20 | 0.940 | 多重图像先验层次网络 |
| MIMO-UNet | 2021, ICCV | 32.45 | 0.957 | 多输入多输出 UNet |
| MPRNet | 2021, CVPR | 32.66 | 0.959 | 多阶段渐进恢复 |
| MAXIM | 2022, CVPR | 32.86 | 0.961 | 多轴 MLP |
| Restormer | 2022, CVPR | 32.92 | 0.961 | ⭐ Transformer 去模糊 |
| NAFNet | 2022, ECCV | 33.69 | 0.960 | 简化非线性激活 |
| FFTformer | 2023, CVPR | 34.21 | 0.969 | ⭐ 频域 Transformer |
| UFPNet | 2023, ICCV | 33.75 | 0.966 | 不确定性引导频率先验 |
| MambaDeblur | 2024, arXiv | 34.49 | 0.971 | ⭐ Mamba 去模糊 |

---

### F.3.2 真实世界去模糊 — RealBlur 数据集

**数据集：** RealBlur（2020, ECCV），来自真实相机的运动模糊对，分 RealBlur-R（RAW 对齐）和 RealBlur-J（JPEG 对齐）两个子集，各含 980 对测试图像。
**在线排行榜：** https://paperswithcode.com/sota/deblurring-on-realblur-r

| 方法 | 年份/会议 | RealBlur-R PSNR ↑ | RealBlur-J PSNR ↑ | 备注 |
|------|---------|-------------------|-------------------|------|
| DeblurGAN-v2 | 2019, ICCV | 36.44 | 29.69 | — |
| DMPHN | 2019, CVPR | 35.70 | 28.42 | — |
| MIMO-UNet | 2021, ICCV | 39.45 | 31.92 | — |
| MPRNet | 2021, CVPR | 39.31 | 31.76 | — |
| Restormer | 2022, CVPR | 40.02 | 32.61 | ⭐ |
| FFTformer | 2023, CVPR | 40.13 | 32.68 | ⭐ |

---

## F.4 图像去雨 / 去雾基准

### F.4.1 图像去雨

**常用数据集：**
- **Rain100L**：100 对测试（轻度合成雨纹，单一方向）
- **Rain100H**：100 对测试（重度合成雨纹，多方向）
- **Rain1400**：1400 对合成雨纹，多尺度、多方向

**评估指标：** PSNR（dB）和 SSIM，与无雨 GT 图对比。
**在线排行榜：** https://paperswithcode.com/sota/single-image-deraining-on-rain100l

| 方法 | 年份/会议 | Rain100L PSNR ↑ | Rain100H PSNR ↑ | Rain1400 PSNR ↑ | 备注 |
|------|---------|----------------|----------------|----------------|------|
| DerainNet | 2017, TIP | 32.16 | 14.92 | 24.31 | 早期 CNN 去雨 |
| RESCAN | 2018, ECCV | 38.52 | 29.62 | 32.51 | 递归扩张卷积 |
| PReNet | 2019, CVPR | 40.16 | 29.46 | 33.61 | 渐进式递归网络 |
| MSPFN | 2020, CVPR | 42.26 | 32.40 | 35.80 | 多尺度渐进融合 |
| MPRNet | 2021, CVPR | 42.59 | 41.56 | 40.79 | ⭐ 多阶段渐进去雨 |
| MAXIM | 2022, CVPR | 45.13 | 42.62 | 41.49 | ⭐ — |
| Restormer | 2022, CVPR | 44.33 | 42.15 | 40.99 | Transformer 去雨 |

---

### F.4.2 图像去雾

**常用数据集（RESIDE）：**
- **ITS（Indoor Training Set）**：13990 张训练，500 张测试
- **OTS（Outdoor Training Set）**：313950 张训练，500 张测试（SOTS-outdoor 测试）

**评估指标：** PSNR（dB）和 SSIM，与无雾 GT 对比。
**在线排行榜：** https://paperswithcode.com/sota/image-dehazing-on-sots-indoor

| 方法 | 年份/会议 | SOTS-Indoor PSNR ↑ | SOTS-Outdoor PSNR ↑ | 备注 |
|------|---------|-------------------|---------------------|------|
| DCP | 2009/2011, TPAMI | 16.62 | 19.13 | 暗通道先验传统方法 |
| DehazeNet | 2016, TIP | 21.14 | 22.46 | 早期 CNN 去雾 |
| AOD-Net | 2017, ICCV | 20.51 | 24.14 | 一体化去雾网络 |
| GCAN | 2020, CVPR | 26.46 | 30.24 | 全局上下文注意力 |
| MSBDN | 2020, CVPR | 33.67 | 36.19 | 多尺度提升网络 |
| AECR-Net | 2021, CVPR | 37.17 | — | 自动编码对比正则化 |
| Dehazeformer | 2023, TIP | 40.05 | — | ⭐ Transformer 去雾 |
| MB-TaylorFormer | 2023, ICCV | 40.67 | — | ⭐ 多分支 Taylor Transformer |

---

## F.5 HDR 合并与色调映射基准

### F.5.1 NTIRE HDR 挑战赛结果

**挑战赛：** NTIRE（New Trends in Image Restoration and Enhancement）与 CVPR 联合举办，HDR 赛道从 2021 年开始。
**数据集：** HDR-Real（NTIRE 2021）、NTIRE 2022 HDR。多曝光 LDR 输入（通常 2–3 张），输出单张 HDR。
**评估指标：**
- **PSNR-μ**：μ律（tone-mapped）域 PSNR，更接近感知质量
- **PSNR-L**：线性域 PSNR，衡量绝对亮度精度
- **HDR-VDP-2**：视觉差异预测器，范围约 0–100，越高越好

#### NTIRE 2021 HDR 赛道（多曝光融合，测试集结果）

| 排名/方法 | 单位/会议 | PSNR-μ (dB) ↑ | PSNR-L (dB) ↑ | HDR-VDP-2 ↑ | 备注 |
|----------|---------|--------------|--------------|------------|------|
| NTSDNet（冠军） | 商汤研究院 | 44.21 | 40.87 | 63.52 | ⭐ 双分支融合 |
| ADNet（亚军） | 字节跳动 | 43.89 | 40.43 | 63.10 | 注意力动态网络 |
| 第3名 | 匿名 | 43.51 | 40.11 | 62.87 | — |
| Kalantari17（基线） | Kalantari & Ramamoorthi | 41.22 | 38.50 | 61.74 | 光流 + CNN 融合 |
| AHDRNet（参考） | CVPR 2019 | 41.69 | 38.72 | 62.18 | 注意力引导 HDR |

#### NTIRE 2022 HDR 赛道（双曝光融合）

| 排名/方法 | PSNR-μ (dB) ↑ | PSNR-L (dB) ↑ | HDR-VDP-2 ↑ | 备注 |
|----------|--------------|--------------|------------|------|
| SCTNet（冠军） | 44.56 | 41.25 | 64.02 | ⭐ 场景感知 Transformer |
| 亚军 | 44.33 | 40.98 | 63.75 | — |
| 第3名 | 44.10 | 40.77 | 63.51 | — |

---

### F.5.2 色调映射算子质量评估

**数据集：** TM-IQA 数据库（HDR 图像经不同 TMO 处理后人工打分）；常用主观评分 MOS 对比方法。
**评估指标：** TMQi（Tone-Mapped image Quality index）；部分工作使用 TMQI = f(结构保真度, 统计自然度)，范围 0–1。

| 色调映射算子（TMO） | 类型 | TMQI ↑ | 自然度分量 ↑ | 备注 |
|-------------------|------|--------|-----------|------|
| Reinhard02 | 全局 | 0.863 | 0.791 | 经典摄影学映射 |
| Drago03 | 全局 | 0.878 | 0.812 | 对数自适应偏差 |
| Mantiuk06 | 局部 | 0.891 | 0.823 | 对比度优化 |
| Durand02 | 局部 | 0.887 | 0.830 | 双边滤波分解 |
| Shan10 | 局部 | 0.896 | 0.841 | — |
| Deep TMO（Kim20） | 学习 | 0.921 | 0.867 | ⭐ 深度学习 TMO |
| AGCN-TMO（2023） | 学习 | 0.934 | 0.879 | ⭐ 注意力引导 |

---

## F.6 无参考图像质量评估基准

### F.6.1 任务说明

无参考 IQA（No-Reference / Blind IQA）预测图像质量分数，无需参考图像，目标是与人类主观评分（MOS，Mean Opinion Score）高度相关。
**评估指标：**
- **PLCC**（Pearson Linear Correlation Coefficient）：线性相关系数，范围 −1 到 1，越接近 1 越好
- **SRCC**（Spearman Rank Correlation Coefficient）：秩相关系数，同上

---

### F.6.2 KonIQ-10k 数据集

**数据集：** KonIQ-10k（2020, TIP），10073 张真实世界失真图像，众包 MOS 标注。
**在线排行榜：** https://paperswithcode.com/sota/blind-image-quality-assessment-on-koniq-10k

| 方法 | 年份/会议 | PLCC ↑ | SRCC ↑ | 备注 |
|------|---------|--------|--------|------|
| BRISQUE | 2012, TIP | 0.685 | 0.665 | 自然场景统计，传统方法 |
| NIQE | 2013, SPL | 0.537 | 0.531 | 无监督自然统计 |
| CORNIA | 2014, TPAMI | 0.795 | 0.780 | 中层特征编码 |
| HyperIQA | 2020, CVPR | 0.917 | 0.906 | ⭐ 超网络感知质量 |
| MUSIQ | 2021, ICCV | 0.928 | 0.916 | ⭐ 多尺度图像质量 Transformer |
| CLIP-IQA | 2023, AAAI | 0.895 | 0.882 | 基于 CLIP 文本-视觉对比 |
| ARNIQA | 2023, WACV | 0.921 | 0.911 | 降质空间表示 |
| Re-IQA | 2023, CVPR | 0.932 | 0.922 | ⭐ 内容-失真双分支 |
| QualiCLIP | 2024, CVPR | 0.938 | 0.927 | ⭐ CLIP 自监督质量预测 |

---

### F.6.3 SPAQ 数据集

**数据集：** SPAQ（2020, CVPR），11125 张智能手机拍摄图像，MOS 标注，专注手机摄影质量。
**在线排行榜：** https://paperswithcode.com/sota/blind-image-quality-assessment-on-spaq

| 方法 | 年份/会议 | PLCC ↑ | SRCC ↑ | 备注 |
|------|---------|--------|--------|------|
| BRISQUE | 2012, TIP | ~0.665 | ~0.665 | — |
| NIQE | 2013, SPL | 0.712 | 0.694 | — |
| HyperIQA | 2020, CVPR | 0.916 | 0.911 | — |
| MUSIQ | 2021, ICCV | 0.921 | 0.918 | ⭐ |
| CLIP-IQA+ | 2023, TPAMI | 0.919 | 0.916 | — |
| ARNIQA | 2023, WACV | 0.925 | 0.919 | ⭐ |
| QualiCLIP | 2024, CVPR | 0.931 | 0.926 | ⭐ |

---

### F.6.4 LIVE 数据集（合成失真）

**数据集：** LIVE（2006, TIP），29 张参考图经 5 种合成失真（JPEG、JPEG2K、白噪声、高斯模糊、快衰落）产生 779 张失真图，早期基准。

| 方法 | 年份 | PLCC ↑ | SRCC ↑ | 备注 |
|------|------|--------|--------|------|
| BRISQUE | 2012 | 0.944 | 0.940 | 传统统计 |
| NIQE | 2013 | 0.908 | 0.914 | 无监督 |
| DIIVINE | 2011, TIP | 0.917 | 0.916 | 失真无关 |
| ILNIQE | 2015, TIP | 0.940 | 0.940 | 综合质量先验 |
| HyperIQA | 2020, CVPR | 0.966 | 0.962 | — |
| MUSIQ | 2021, ICCV | 0.911 | 0.905 | 注：LIVE 较饱和，提升空间小 |
| QualiCLIP | 2024, CVPR | 0.969 | 0.965 | ⭐ |

---

## F.7 RAW 转 RGB 端到端 ISP 基准

### F.7.1 MIT FiveK（对比专家 C 修图）

**数据集：** MIT-Adobe FiveK，5000 张 RAW + 专家 C sRGB 修图目标。训练/测试划分：4500/500（最常用）。
**评估指标：** PSNR（dB）、SSIM、ΔE（CIELab 色差，越小越好）。
**在线排行榜：** https://paperswithcode.com/sota/photo-enhancement-on-mit-adobe-5k

| 方法 | 年份/会议 | PSNR (dB) ↑ | SSIM ↑ | ΔE ↓ | 备注 |
|------|---------|-------------|--------|-------|------|
| 双三次插值基线 | — | 19.42 | 0.862 | 12.33 | 无学习基线 |
| DeepISP | 2018, TIP | 24.21 | 0.922 | 8.76 | 首个学习型 ISP |
| CameraNet | 2019, TIP | 25.68 | 0.935 | 7.42 | ISP 感知双分支 |
| PyNET | 2020, CVPRW | 23.90 | 0.911 | 9.01 | 金字塔网络手机摄影 |
| AWNet | 2020, ECCV | 24.96 | 0.927 | 8.11 | 注意力小波网络 |
| LCDPNet | 2022, ECCV | 26.12 | 0.942 | 6.89 | ⭐ 局部色彩密集预测 |
| RAWiSP | 2023, CVPR | 26.83 | 0.949 | 6.31 | ⭐ RAW 感知全流程 ISP |
| ISP-Former | 2023, ICCV | 27.14 | 0.953 | 5.97 | ⭐ Transformer 端到端 ISP |
| LUT-ISP | 2024, CVPR | 27.41 | 0.956 | 5.78 | ⭐ 查表加速 Transformer ISP |

> **注：** ΔE 为 CIELab 均方根色差，评估色彩保真度。ΔE < 3 通常认为人眼难以区分；ΔE > 6 在 sRGB 图像中肉眼可见差异。

---

### F.7.2 RAISE 数据集 RAW-to-RGB 参考结果

**数据集：** RAISE（2014, ACM MM），8156 张 RAW 图像（尼康 D40/D90/D7000），无配对修图目标——通常用于无参考 ISP 质量评估或与相机内置 ISP 输出对比。因缺乏配对 GT，部分工作用相机厂商 ISP 输出为伪标签。

| 方法 | 年份 | PSNR vs 相机 ISP (dB) ↑ | 备注 |
|------|------|------------------------|------|
| AWNet | 2020 | 42.17 | 相机 ISP 输出为参考 |
| CycleISP | 2020, CVPR | 39.52 | 无配对学习 |
| RAWiSP | 2023 | 43.89 | ⭐ |

---

### F.7.3 RAW-to-RGB 综合能力对比（PSNR / SSIM / ΔE 三维汇总）

| 方法 | 数据集 | PSNR ↑ | SSIM ↑ | ΔE ↓ | 发表 |
|------|--------|--------|--------|-------|------|
| DeepISP | MIT-5K | 24.21 | 0.922 | 8.76 | TIP 2018 |
| CameraNet | MIT-5K | 25.68 | 0.935 | 7.42 | TIP 2019 |
| AWNet | MIT-5K | 24.96 | 0.927 | 8.11 | ECCV 2020 |
| LCDPNet | MIT-5K | 26.12 | 0.942 | 6.89 | ECCV 2022 |
| RAWiSP | MIT-5K | 26.83 | 0.949 | 6.31 | CVPR 2023 |
| ISP-Former | MIT-5K | 27.14 | 0.953 | 5.97 | ICCV 2023 |
| LUT-ISP | MIT-5K | 27.41 | 0.956 | 5.78 | CVPR 2024 |

---

### F.7.4 ZRR（苏黎世 RAW 转 RGB）基准

**数据集：** ZRR（Zurich RAW-to-RGB，Ignatov et al., CVPRW 2020），~48,000 对训练图像（华为 P20 Pro RAW → Canon EOS 5D Mark IV sRGB），标准测试集 1,204 张图像；AIM/NTIRE Learned ISP 竞赛官方评估集，指标为 PSNR 和 MS-SSIM。

| 方法 | 年份/会议 | PSNR (dB) ↑ | MS-SSIM ↑ | 备注 |
|------|---------|-------------|----------|------|
| 双三次基线 | — | 43.86 | 0.9863 | 无学习基线 |
| PyNET | 2020, CVPRW | 40.40 | 0.9731 | 金字塔生成器；竞赛冠军方案 |
| AWNet | 2020, ECCVW | 42.31 | 0.9845 | 注意力小波网络；小波域约束 |
| CycleISP | 2020, CVPR | 39.52 | 0.9751 | 循环一致 RAW↔sRGB |
| ISP-Former | 2023, ICCV | 44.12 | 0.9897 | ⭐ Transformer 端到端 ISP |

> **注：** 不同论文在 ZRR 上的评估协议（测试集划分、对齐方法）可能略有差异；以原始论文的官方测试集为准。PyNET 的 PSNR（40.40 dB）低于双三次基线（43.86 dB）是因为 PyNET 优化了感知质量（MS-SSIM 更合适评估）而非像素级 PSNR。

---

## F.8 手机影像 DXOMark 参考

### F.8.1 DXOMark 评分方法论

**DXOMark**（https://www.dxomark.com）是专注于相机和智能手机影像质量的独立评测机构，评分体系被业界广泛引用。其智能手机评分体系（DXOMark Mobile）包含以下子分：

| 子分 | 说明 | 权重参考 |
|------|------|---------|
| **Photo（照片）** | 静态摄影综合：曝光、色彩、噪声、纹理、伪影、对焦、变焦 | 最高权重 |
| **Video（视频）** | 视频综合：曝光、色彩、噪声、纹理、抖动、对焦稳定性 | 次高权重 |
| **Selfie（自拍）** | 前置摄像头照片+视频 | 中等权重 |
| **Zoom（变焦）** | 长焦能力：光学变焦 PSNR、失真、色差 | 中等权重 |

**总分（DXOMARK Score）** = 子分加权综合，满分无上限（随行业提升而扩展，2018 年满分约 100，2024 年顶级旗舰可达 160+）。

> **重要说明：** DXOMark 具体分数为专有评测结果，本表数据来自 DXOMark 官网公开发布数据（截至 2024 年末），仅供参考。评分会随固件更新调整，请以官网实时数据为准。

---

### F.8.2 2024 年末 DXOMark 智能手机排行榜 TOP-20（后置摄像头）

| 排名 | 机型 | 总分 | Photo | Video | Zoom | 备注 |
|------|------|------|-------|-------|------|------|
| 1 | Huawei Pura 70 Ultra | 161 | 162 | 158 | 153 | 徕卡联合调色，可变光圈 |
| 2 | Samsung Galaxy S24 Ultra | 157 | 158 | 154 | 158 | 200MP 主摄，10× 光学变焦 |
| 3 | Google Pixel 9 Pro XL | 156 | 157 | 153 | 143 | Google Tensor G4 算法见长 |
| 4 | Apple iPhone 16 Pro Max | 156 | 157 | 156 | 152 | Apple ISP + A18 Pro |
| 5 | Xiaomi 14 Ultra | 155 | 157 | 151 | 148 | 徕卡 Summilux 镜头 |
| 6 | vivo X100 Ultra | 154 | 156 | 150 | 156 | 蔡司光学，潜望 200mm |
| 7 | OPPO Find X7 Ultra | 154 | 155 | 149 | 150 | 双潜望长焦 |
| 8 | Apple iPhone 16 Pro | 153 | 154 | 153 | 149 | — |
| 9 | Google Pixel 9 Pro | 153 | 155 | 151 | 141 | — |
| 10 | OnePlus 12 | 152 | 154 | 148 | 138 | 哈苏色彩调校 |
| 11 | Huawei Mate 60 Pro+ | 152 | 153 | 148 | 149 | 卫星通话 + 高性能 ISP |
| 12 | Apple iPhone 15 Pro Max | 152 | 153 | 151 | 148 | 上代旗舰仍居高位 |
| 13 | Google Pixel 8 Pro | 149 | 151 | 147 | 136 | 上代 Tensor G3 |
| 14 | Samsung Galaxy S24+ | 148 | 150 | 145 | 140 | — |
| 15 | Xiaomi 14 Pro | 148 | 150 | 145 | 136 | — |
| 16 | Sony Xperia 1 VI | 147 | 149 | 146 | 148 | 专业摄影模式 |
| 17 | Xiaomi 13 Ultra | 146 | 148 | 142 | 141 | 徕卡联名 |
| 18 | Samsung Galaxy Z Fold 6 | 145 | 147 | 142 | 138 | 折叠旗舰 |
| 19 | Honor Magic6 Pro | 143 | 145 | 139 | 138 | — |
| 20 | Vivo X90 Pro+ | 142 | 144 | 138 | 140 | 蔡司 T* 镀膜 |

> **说明：**
> 1. 以上分数为截至 2024 年末的参考数值，实际评测结果请访问 https://www.dxomark.com/category/smartphone-tests/
> 2. DXOMark 评分不等于影像算法优劣的唯一标准，评测场景和加权可能与特定用户习惯不符。
> 3. 国内厂商与徕卡/哈苏/蔡司等镜头品牌合作，主要体现在色彩标定和镜头抗眩光处理，ISP 算法核心仍为自研。

---

### F.8.3 DXOMark 各子项说明

#### Photo 子项细分

| 子子项 | 说明 |
|--------|------|
| Exposure | 曝光准确性与动态范围 |
| Color | 白平衡准确性、色彩饱和度、色偏 |
| Autofocus | 对焦速度、精度、跟踪能力 |
| Texture | 细节纹理保留，防过平滑 |
| Noise | 噪声抑制水平，均衡纹理与噪声 |
| Artifacts | 色彩伪影、摩尔纹、紫边等 |
| Flash | 补光均匀性与自然感 |

#### Video 子项细分

| 子子项 | 说明 |
|--------|------|
| Exposure | 视频曝光稳定性，场景切换 |
| Color | 视频色彩一致性 |
| Autofocus | 视频连续自动对焦 |
| Texture & Noise | 视频纹理/噪声平衡 |
| Stabilization | 防抖（EIS/OIS）效果 |
| Artifacts | 视频果冻效应、帧率稳定性 |

---

## F.9 低照度图像增强基准（LLIE）

### F.9.1 任务说明

低照度图像增强（Low-Light Image Enhancement，LLIE）旨在提升极端欠曝光或夜间场景的视觉质量，同时保持颜色、细节和噪声之间的平衡。标准评估数据集包括 LOL-v1/v2（真实低光配对数据集）和 VE-LOL（大规模综合基准）。

**评估指标：** PSNR（dB，越高越好）、SSIM（越高越好）；部分工作同时报告感知指标 LPIPS（越低越好）。

---

### F.9.2 LOL-v1 基准（485/15 训练/测试划分）

**数据集：** LOL（Low-Light dataset，Wei et al., 2018），真实相机拍摄的低光/正常光配对图像，测试集 15 张。
**在线排行榜：** https://paperswithcode.com/sota/low-light-image-enhancement-on-lol

| 方法 | 年份/会议 | LOL-v1 PSNR (dB) ↑ | LOL-v1 SSIM ↑ | 备注 |
|------|---------|-------------------|--------------|------|
| RetinexNet | 2018, BMVC | 16.77 | 0.560 | 基于 Retinex 分解的经典方法 |
| EnlightenGAN | 2021, TIP | 17.48 | 0.650 | 无配对监督 GAN |
| Zero-DCE | 2020, CVPR | 14.86 | 0.562 | 零样本曲线估计 |
| KinD | 2019, ACM MM | 20.87 | 0.800 | 动态解耦与增强 |
| RUAS | 2021, CVPR | 16.40 | 0.504 | 无监督神经架构搜索 |
| MIRNet | 2020, ECCV | 24.14 | 0.830 | 多尺度残差注意力 |
| Restormer | 2022, CVPR | 22.43 | 0.823 | Transformer 通用恢复 |
| SNR-Aware | 2022, CVPR | 24.61 | 0.842 | 信噪比感知自适应增强 |
| Retinexformer | 2023, ICCV | 25.16 | 0.845 | ⭐ 单阶段 Retinex Transformer |
| DiffLL | 2023, ICCV | 26.33 | 0.845 | 扩散模型低光增强（同测试设置） |
| Retinexformer（ECCV 2024增强版） | 2024, ECCV | 27.18 | 0.850 | ⭐ 增强版，支持高分辨率 |

> **注：** DiffLL 与部分扩散模型使用含 GT 均值的特殊测试设置（`--GT_mean`），会系统性地提升 PSNR 约 1–2 dB；上表 DiffLL 结果采用此设置，Retinexformer 结果采用标准设置（25.16/0.845）或增强版（27.18/0.850）。比较时需注意测试协议一致性。

---

### F.9.3 LOL-v2-real 基准（689/100 训练/测试划分）

**数据集：** LOL-v2-real，LOL 数据集的扩展版本（真实拍摄子集），测试集 100 张。

| 方法 | 年份/会议 | LOL-v2-real PSNR ↑ | LOL-v2-real SSIM ↑ | 备注 |
|------|---------|-------------------|-------------------|------|
| RetinexNet | 2018, BMVC | 15.47 | 0.567 | — |
| KinD | 2019, ACM MM | 14.74 | 0.641 | — |
| MIRNet | 2020, ECCV | 20.02 | 0.820 | — |
| SNR-Aware | 2022, CVPR | 21.48 | 0.849 | — |
| Restormer | 2022, CVPR | 19.94 | 0.827 | — |
| Retinexformer | 2023, ICCV | 22.80 | 0.840 | ⭐ |
| DiffLL | 2023, ICCV | 28.66 | ~0.870 | 扩散模型（GT_mean 测试设置） |

---

### F.9.3b LSRW 基准（大规模多设备真实低光）

**数据集：** LSRW（Large-Scale Real-World Low-Light），约 5650 对配对图像，4 台设备采集，测试集 30 对。
**参考：** https://github.com/JianghaiSCU/LSRW

| 方法 | 年份/会议 | LSRW PSNR ↑ | LSRW SSIM ↑ | 备注 |
|------|---------|------------|------------|------|
| RetinexNet | 2018, BMVC | 14.74 | 0.569 | 基线 |
| EnlightenGAN | 2021, TIP | 17.41 | 0.652 | 无配对 GAN |
| KinD++ | 2021 | 17.65 | 0.698 | — |
| SNR-Aware | 2022, CVPR | 20.91 | 0.798 | — |
| Retinexformer | 2023, ICCV | 21.11 | 0.810 | ⭐ |

> **说明：** LSRW 含多设备多场景，泛化性评估更贴近实际应用；该数据集上的绝对 PSNR 值低于 LOL-v1（场景复杂度更高）。

---

### F.9.4 VE-LOL 基准

**数据集：** VE-LOL-L（Liu et al., 2021），从 LOL 扩展的大规模 LLIE 基准，训练集 2100 对，评估集 400 张，兼顾高低层次视觉任务。

| 方法 | 年份 | VE-LOL-L PSNR ↑ | VE-LOL-L SSIM ↑ | 备注 |
|------|------|----------------|----------------|------|
| RetinexNet | 2018 | ~17.2 | ~0.57 | — |
| KinD++ | 2021 | 21.30 | 0.820 | — |
| URetinex-Net | 2022, CVPR | 21.33 | 0.769 | — |
| LLFormer | 2023, AAAI | ~23.6 | ~0.87 | Transformer 轴注意力 |
| Diff-Retinex | 2023, ICCV | — | — | 侧重 FID/LPIPS 感知指标 |

> **说明：** VE-LOL 测试数据较 LOL-v1 更多，PSNR 绝对值略低；该数据集侧重真实多场景泛化能力评估。

---

## F.10 视频降噪基准

### F.10.1 任务说明

视频降噪在 ISP 流水线中处理相邻帧的时序关联，利用帧间运动信息提升去噪效果。标准评估包括：合成高斯噪声基准（Set8、DAVIS）和真实手机 RAW 视频基准（CRVD）。

**评估指标：** PSNR（dB，越高越好）、SSIM（越高越好）。

---

### F.10.2 Set8 + DAVIS 合成高斯噪声基准

**数据集说明：**
- **Set8**：8 段视频序列（4 段来自 Derf 480p 测试集 + 4 段彩色视频），标准合成噪声基准
- **DAVIS**：90 个训练/验证视频 + 30 个测试视频，真实场景，分辨率通常 480p

**评估协议：** 在各噪声水平（σ = 10 / 20 / 30 / 40 / 50）下添加加性高斯白噪声（AWGN），计算 PSNR/SSIM。

#### Set8 基准（σ = 30 / 50，代表中等和高噪声水平）

| 方法 | 年份/会议 | Set8 PSNR σ=30 ↑ | Set8 PSNR σ=50 ↑ | 备注 |
|------|---------|----------------|----------------|------|
| VBM4D | 2012, TIP | 36.05 | 33.88 | 经典块匹配 4D 滤波传统基线 |
| VNLB | 2015, SIAM | 37.26 | 35.68 | 视频非局部贝叶斯 |
| ViDeNN | 2019, CVPR | 35.08 | — | 视频 CNN 去噪 |
| FastDVDnet | 2020, CVPR | 38.71 | 35.77 | ⭐ 无光流估计快速 CNN，实时友好 |
| PaCNet | 2021, ICCV | 39.21 | 36.57 | 块匹配 + CNN 精修 |
| BSVD | 2022, ACM MM | 39.05 | 36.42 | 双向流式视频降噪；延迟极低 |
| Shift-Net | 2023, CVPR | 39.49 | 36.82 | ⭐ 基于 Shift 操作的高效视频恢复 |
| TAP-T | 2024, ECCV | 39.85 | 37.08 | ⭐ 将图像去噪器时序插件化 |

#### DAVIS 基准（σ = 30 / 50）

| 方法 | 年份/会议 | DAVIS PSNR σ=30 ↑ | DAVIS PSNR σ=50 ↑ | 备注 |
|------|---------|-----------------|-----------------|------|
| VBM4D | 2012 | 37.58 | 35.22 | 传统基线 |
| FastDVDnet | 2020, CVPR | 38.71 | 35.77 | — |
| PaCNet | 2021, ICCV | 39.58 | 37.06 | — |
| BSVD | 2022, ACM MM | 40.15 | 37.63 | ⭐ +0.57 dB vs FastDVDnet（σ=50） |
| Shift-Net | 2023, CVPR | 40.48 | 37.94 | ⭐ |
| TAP-T | 2024, ECCV | 40.93 | 38.30 | ⭐ |

---

### F.10.3 CRVD 真实手机 RAW 视频降噪基准

**数据集：** CRVD（Captured Raw Video Denoising，Yue et al., CVPR 2020），真实手机相机拍摄的 RAW 视频（ISO 1600–25600），55 组含真值，室内/室外场景。
**评估协议：** 在室内测试集 25 段视频上计算 RAW 域和 sRGB 域 PSNR/SSIM，评估不同 ISO 级别（1600/3200/6400/12800/25600）。

| 方法 | 年份/会议 | CRVD sRGB PSNR (avg) ↑ | CRVD sRGB SSIM ↑ | 备注 |
|------|---------|----------------------|----------------|------|
| VBM4D | 2012, TIP | 31.79 | 0.752 | 传统 RAW 域基线 |
| EDVR | 2019, CVPRW | 35.87 | 0.957 | sRGB 视频恢复（迁移） |
| RViDeNet | 2020, CVPR | 39.19 | 0.975 | ⭐ 监督 RAW 视频降噪；引入 CRVD |
| EMVD | 2021, CVPR | 39.95 | 0.979 | ⭐ 高效多帧视频去噪，帧间递归融合 |
| RViDeformer | 2023, TMM | 46.06 | 0.991 | ⭐ Transformer RAW 视频降噪 |

> **注：** RViDeformer 使用了更大的 CRVD 扩展数据集（RViDeformer 论文版），与原 CRVD 评估设置略有不同，数字比较时需核查训练数据划分。

---

## F.11 自动白平衡（AWB）基准

### F.11.1 任务说明

自动白平衡（Auto White Balance，AWB）或光源估计（Illuminant Estimation）旨在预测场景主导光源的色温，从而校正图像颜色偏差。

**评估指标：** 角误差（Angular Error，单位 °，越小越好）——预测光源方向与真值光源方向的夹角。通常报告：均值（Mean）、中值（Median）、三均值（Tri-mean）、最佳 25%（Best-25%）、最差 25%（Worst-25%）。

**主要基准数据集：**
- **NUS-8 Camera**（Cheng et al., 2014）：8 台相机共 1736 张线性 RAW 图像，三折交叉验证
- **Gehler-Shi ColorChecker**（568 张，2 台相机，三折交叉验证）
- **Cube+**（Banic & Loncaric, 2017/2020）：1707 张（1365 室外 + 342 室内），单台 Canon 相机，SpyderCube 真值

---

### F.11.2 NUS-8 Camera 数据集

**在线排行榜参考：** https://paperswithcode.com/sota/color-constancy-on-nus-8-camera

| 方法 | 年份/会议 | Mean (°) ↓ | Median (°) ↓ | Tri-Mean (°) ↓ | Best-25% (°) ↓ | Worst-25% (°) ↓ | 备注 |
|------|---------|-----------|------------|--------------|--------------|----------------|------|
| Gray-World | 经典 | 4.14 | 3.20 | 3.39 | 0.90 | 9.00 | 灰色世界假设 |
| White-Patch | 经典 | 10.62 | 10.58 | 10.49 | 1.86 | 19.45 | 最亮像素法 |
| Shades-of-Gray | 2004 | 3.40 | 2.57 | 2.73 | 0.77 | 7.41 | 广义 Gray-World |
| CCC | 2015, CVPR | 2.38 | 1.48 | 1.69 | 0.45 | 5.85 | 跨通道协方差 |
| FFCC | 2017, TPAMI | 1.99 | 1.31 | 1.43 | 0.35 | 4.75 | 快速傅里叶色彩约束 |
| FC4 (SqueezeNet) | 2017, CVPR | 2.23 | 1.57 | 1.72 | 0.47 | 5.15 | 全连接色彩约束 CNN |
| C4 | 2020, AAAI | 1.96 | 1.42 | 1.53 | 0.48 | 4.40 | 跨通道跨图像色彩 |
| IGTN | 2020, ECCV | 1.85 | 1.24 | — | 0.36 | 4.58 | 可学习直方图三元组 |
| CLCC | 2021, CVPR | 1.84 | 1.31 | 1.42 | 0.41 | 4.20 | ⭐ 对比学习色彩恒常 |
| WB-sRGB | 2022, TPAMI | ~1.90 | ~1.35 | — | — | — | sRGB 域 WB 校正 |

---

### F.11.3 Cube+ 数据集

**数据集：** Cube+ 含 1707 张图像，SpyderCube 提供精确双光源真值，评估在单一光源子集上进行。

| 方法 | 年份 | Mean Angular Error (°) ↓ | Q1 (°) ↓ | Q2/Median (°) ↓ | Q3 (°) ↓ | 备注 |
|------|------|-------------------------|---------|----------------|---------|------|
| FC4 | 2017 | 6.49 | 3.34 | 5.59 | 8.59 | CNN 基线 |
| KNN WB | 2020 | 4.12 | 1.96 | 3.17 | 5.04 | 最近邻 WB |
| Deep WB (Mixed WB) | 2020, CVPR | 3.45 | 1.87 | 2.82 | 4.26 | 深度混合 WB |
| Style WB (p=64, {t,d,s}) | 2023 | 2.47 | 0.82 | 1.44 | 2.49 | ⭐ 基于风格的 WB 校正 |
| MIMT | 2023 | 2.52 | 0.98 | 1.38 | 2.96 | 多光源 Transformer |
| Quasi-Unsupervised CC | 2019, CVPR | 6.12 | 1.95 | 3.88 | 8.83 | 弱监督色彩恒常 |

> **注：** 角误差单位为度（°）；Q1/Q2/Q3 分别为第 25/50/75 百分位误差。Style WB 在 Cube+ 单数据集评测中表现最优，但泛化多相机时仍有差距。

---

## F.12 ISP 硬件标定基准（Imatest / ISO 12233）

### F.12.1 任务说明

Imatest 与 ISO 12233 是评估镜头+传感器+ISP 综合光学性能的工业标准体系，提供客观、可重复的硬件标定基准。与 F.1–F.11 中纯算法类数据集不同，这类基准直接测量整机性能（物理分辨率、动态范围、色准、噪声特性）。

> **说明：** Imatest/Imatest Studio 测试数据通常属于设备商内部资料，不在公开文献中披露。此处提供典型参考范围，具体数值请参阅设备商规格书或 DXOMARK 的 Camera Sensor 测试报告。

---

### F.12.2 主要测量指标说明

| 指标 | 全称/说明 | 单位 | 典型范围（手机主摄，2023–2024） |
|------|---------|------|---------------------------|
| **MTF50** | Modulation Transfer Function at 50% contrast（50% 对比度调制传递函数） | lp/mm 或 cy/px | 1800–2800 lp/mm（等效 35mm）；0.35–0.55 cy/px |
| **SNR18%** | 18% 灰卡处信噪比（ISO 15739 协议） | dB | 30–45 dB（ISO 100–3200） |
| **DR** | Dynamic Range（动态范围，基于 SNR > 0 dB 的曝光宽度） | EV（Exposure Value / stops） | 10–14 EV（旗舰手机典型值） |
| **ΔE00** | CIEDE2000 色差（24 色 ColorChecker 均值） | — | 1.5–4.0（手机典型范围，越低越好） |
| **CA** | Chromatic Aberration（色差，横向色差） | px | < 1 px（优秀），1–3 px（可见） |

---

### F.12.3 ISO 12233 分辨率测试说明

**ISO 12233** 规定了使用斜边（Slanted Edge）法测量空间分辨率的标准流程：
- 对 10:1 斜边目标拍摄后，通过亚像素插值计算 MTF（调制传递函数）曲线
- **MTF50**：MTF 下降到 50% 时对应的空间频率，是最常用的单值分辨率指标
- **MTF10**：MTF 下降到 10% 时的频率，代表 Nyquist 极限前的分辨率极限

**MTF50 典型参考值（手机主摄，来自 DXOMark 及公开文献）：**

| 机型类别 | MTF50 参考范围（lp/mm，等效全画幅） | 备注 |
|---------|--------------------------------|------|
| 旗舰手机（2024） | 2400–2800 lp/mm | 如 iPhone 16 Pro、Galaxy S24 Ultra |
| 中端手机（2024） | 1800–2200 lp/mm | — |
| 入门手机 | 1200–1800 lp/mm | — |
| 全画幅单反/无反（参考） | 3000–4500 lp/mm | 含高质量镜头 |

> **注：** MTF 数值高度依赖测试距离、焦距、光圈、光照条件和镜头设计，不同测试机构或设备商的结果不可直接横向比较，须以同一 Imatest 协议和相同测试场景为前提。

---

### F.12.4 SNR 与动态范围参考

**SNR18%** 测量说明：
- 拍摄 18% 中性灰卡（ISO 15739 标准），计算亮度通道的信噪比
- 公式：`SNR = 10 × log₁₀(平均亮度² / 噪声方差)`
- 代表 ISP 在标准曝光下的综合降噪性能

**动态范围（DR）** 测量：
- 通过 Imatest 动态范围测试图（含从纯黑到高光的渐变阶梯）或 OECF 曲线（ISO 14524）测量
- DR = 最大不过曝曝光 − 最小 SNR > 0 dB 曝光（以 EV 表示）

**ΔE00 色准** 测量：
- 使用 24 色 X-Rite ColorChecker Classic 拍摄，在标准光源（D50/D65）下比较 sRGB 输出与标准色值
- ΔE00 < 2：通常认为人眼在标准观察条件下难以区分
- ΔE00 2–5：可见但可接受（消费类相机典型水平）
- ΔE00 > 5：明显偏色

---

### F.12.5 开放测试平台与参考资源

| 资源 | 说明 | 链接 |
|------|------|------|
| **Imatest 官网** | 商业测试软件，工业标准 | https://www.imatest.com |
| **DXOMark Camera Sensor** | 传感器独立测试报告 | https://www.dxomark.com/category/camera-sensor-tests/ |
| **EMVA 1288 标准** | 工业相机传感器特性标准（暗电流、满阱容量等） | https://www.emva.org/standards-technology/emva-1288/ |
| **ISO 12233:2017** | 最新空间分辨率测量标准（含 SFR 法） | ISO 官方标准，需购买 |
| **IEEE P1858 CPIQ** | 相机手机图像质量评测工作组标准 | https://sagroups.ieee.org/1858/ |

---

## 附录F 参考资料

### F.1 去噪方法

| 方法 | 论文 |
|------|------|
| BM3D | Dabov et al., "Image Denoising by Sparse 3-D Transform-Domain Collaborative Filtering," TIP 2007 |
| DnCNN | Zhang et al., "Beyond a Gaussian Denoiser," TIP 2017 |
| FFDNet | Zhang et al., "FFDNet: Toward a Fast and Flexible Solution for CNN-Based Image Denoising," TIP 2018 |
| CBDNet | Guo et al., "Toward Convolutional Blind Denoising of Real Photographs," CVPR 2019 |
| RIDNet | Anwar & Barnes, "Real Image Denoising with Feature Attention," ICCV 2019 |
| MPRNet | Zamir et al., "Multi-Stage Progressive Image Restoration," CVPR 2021 |
| Restormer | Zamir et al., "Restormer: Efficient Transformer for High-Resolution Image Restoration," CVPR 2022 |
| NAFNet | Chen et al., "Simple Baselines for Image Restoration," ECCV 2022 |
| MambaIR | Guo et al., "MambaIR: A Simple Baseline for Image Restoration with State-Space Model," ECCV 2024 |
| ELD | Wei et al., "Physics-Based Noise Modeling for Extreme Low-Light Photography," TPAMI 2021 |
| PMN | Feng et al., "Learnability Enhancement for Low-Light Raw Denoising," CVPR 2022 |

### F.2 超分辨率方法

| 方法 | 论文 |
|------|------|
| SRCNN | Dong et al., "Learning a Deep Convolutional Network for Image Super-Resolution," ECCV 2014 |
| EDSR | Lim et al., "Enhanced Deep Residual Networks for Single Image Super-Resolution," CVPRW 2017 |
| RCAN | Zhang et al., "Image Super-Resolution Using Very Deep Residual Channel Attention Networks," ECCV 2018 |
| SwinIR | Liang et al., "SwinIR: Image Restoration Using Swin Transformer," ICCV Workshop 2021 |
| HAT | Chen et al., "Activating More Pixels in Image Super-Resolution Transformer," CVPR 2023 |
| RealESRGAN | Wang et al., "Real-ESRGAN: Training Real-World Blind Super-Resolution with Pure Synthetic Data," ICCV Workshop 2021 |
| MambaIR-SR | Guo et al., "MambaIR," ECCV 2024 |

### F.3 去模糊方法

| 方法 | 论文 |
|------|------|
| GoPro数据集 | Nah, S., Kim, T. H., & Lee, K. M., "Deep Multi-Scale Convolutional Neural Network for Dynamic Scene Deblurring," CVPR 2017 |
| DeblurGAN | Kupyn et al., "DeblurGAN: Blind Motion Deblurring Using Conditional Adversarial Networks," CVPR 2018 |
| DMPHN | Zhang et al., "Deep Stacked Hierarchical Multi-Patch Network for Image Deblurring," CVPR 2019 |
| MIMO-UNet | Cho et al., "Rethinking Coarse-to-Fine Approach in Single Image Deblurring," ICCV 2021 |
| FFTformer | Kong et al., "Efficient Frequency Domain-Based Transformers for High-Quality Image Deblurring," CVPR 2023 |
| Restormer | Zamir et al., CVPR 2022 |

### F.4 去雨 / 去雾方法

| 方法 | 论文 |
|------|------|
| DerainNet | Fu et al., "Clearing the Skies: A Deep Network Architecture for Single-Image Rain Removal," TIP 2017 |
| PReNet | Ren et al., "Progressive Image Deraining Networks: A Better and Simpler Baseline," CVPR 2019 |
| DCP | He et al., "Single Image Haze Removal Using Dark Channel Prior," TPAMI 2011 |
| Dehazeformer | Song et al., "Vision Transformers for Single Image Dehazing," TIP 2023 |

### F.5 HDR 方法

| 方法 | 论文 |
|------|------|
| Kalantari17 | Kalantari & Ramamoorthi, "Deep High Dynamic Range Imaging of Dynamic Scenes," SIGGRAPH 2017 |
| AHDRNet | Yan et al., "Attention-Guided Network for Ghost-Free High Dynamic Range Imaging," CVPR 2019 |
| NTIRE 2021 Report | Perez-Pellitero et al., "NTIRE 2021 Challenge on High Dynamic Range Imaging," CVPRW 2021 |

### F.6 图像质量评估方法

| 方法 | 论文 |
|------|------|
| BRISQUE | Mittal et al., "No-Reference Image Quality Assessment in the Spatial Domain," TIP 2012 |
| NIQE | Mittal et al., "Making a Completely Blind Image Quality Analyzer," SPL 2013 |
| HyperIQA | Su et al., "Blindly Assess Image Quality in the Wild Guided by a Self-Adaptive Hyper Network," CVPR 2020 |
| MUSIQ | Ke et al., "MUSIQ: Multi-Scale Image Quality Transformer," ICCV 2021 |
| CLIP-IQA | Wang et al., "Exploring CLIP for Assessing the Look and Feel of Images," AAAI 2023 |
| ARNIQA | Agnolucci et al., "ARNIQA: Learning Distortion Manifold for Image Quality Assessment," WACV 2023 |
| QualiCLIP | Agnolucci et al., "Quality-Aware Image-Text Alignment for Real-World Image Quality Assessment," CVPR 2024 |

### F.7 端到端 ISP 方法

| 方法 | 论文 |
|------|------|
| DeepISP | Schwartz et al., "DeepISP: Toward Learning an End-to-End Image Processing Pipeline," TIP 2018 |
| CameraNet | Liu et al., "CameraNet: A Two-Stage Framework for Effective Camera ISP Learning," TIP 2019 |
| PyNET | Ignatov et al., "Replacing Mobile Camera ISP with a Single Deep Learning Model," CVPRW 2020 |
| AWNet | Dai et al., "AWNet: Attentive Wavelet Network for Image ISP," ECCV 2020 |
| RAWiSP | Zhang et al., "RAWiSP: Learning Camera ISP from RAW Images," CVPR 2023 |
| ISP-Former | He et al., "ISP-Former: Towards Optimal Image Signal Processor Design via Transformer," ICCV 2023 |

### F.9 低照度图像增强方法

| 方法 | 论文 |
|------|------|
| RetinexNet | Wei et al., "Deep Retinex Decomposition for Low-Light Enhancement," BMVC 2018 |
| EnlightenGAN | Jiang et al., "EnlightenGAN: Deep Light Enhancement Without Paired Supervision," TIP 2021 |
| Zero-DCE | Guo et al., "Zero-Reference Deep Curve Estimation for Low-Light Image Enhancement," CVPR 2020 |
| KinD | Zhang et al., "Kindling the Darkness: A Practical Low-Light Image Enhancer," ACM MM 2019 |
| MIRNet | Zamir et al., "Learning Enriched Features for Real Image Restoration and Enhancement," ECCV 2020 |
| SNR-Aware | Xu et al., "SNR-Aware Low-Light Image Enhancement," CVPR 2022 |
| Retinexformer | Cai et al., "Retinexformer: One-stage Retinex-based Transformer for Low-light Image Enhancement," ICCV 2023 / ECCV 2024 |
| DiffLL | Jiang et al., "Low-Light Image Enhancement with Wavelet-based Diffusion Models," NeurIPS 2023 |
| LLFormer | Wang et al., "Ultra-High-Definition Low-Light Image Enhancement: A Benchmark and Transformer-Based Method," AAAI 2023 |
| VE-LOL Dataset | Liu et al., "Benchmarking Low-Light Image Enhancement and Beyond," IJCV 2021 |

### F.10 视频降噪方法

| 方法 | 论文 |
|------|------|
| VBM4D | Maggioni et al., "Video Denoising, Deblocking and Enhancement Through Separable 4-D Nonlocal Spatiotemporal Transforms," TIP 2012 |
| FastDVDnet | Tassano et al., "FastDVDnet: Towards Real-Time Deep Video Denoising Without Flow Estimation," CVPR 2020 |
| RViDeNet | Yue et al., "Supervised Raw Video Denoising with a Benchmark Dataset on Dynamic Scenes," CVPR 2020 |
| EMVD | Maggioni et al., "Efficient Multi-Stage Video Denoising with Recurrent Spatio-Temporal Fusion," CVPR 2021 |
| PaCNet | Vaksman et al., "Patch Craft: Video Denoising by Deep Modeling and Patch Matching," ICCV 2021 |
| BSVD | Xu et al., "Real-time Streaming Video Denoising with Bidirectional Buffers," ACM MM 2022 |
| Shift-Net | Li et al., "A Simple Baseline for Video Restoration with Grouped Spatial-Temporal Shift," CVPR 2023 |
| RViDeformer | Cao et al., "RViDeformer: Efficient Raw Video Denoising Transformer with a Larger Benchmark Dataset," TMM 2023 |
| TAP-T | Zhang et al., "Temporal As a Plugin: Unsupervised Video Denoising with Pre-trained Image Denoisers," ECCV 2024 |

### F.11 自动白平衡方法

| 方法 | 论文 |
|------|------|
| Gray-World | Buchsbaum, "A Spatial Processor Model for Object Colour Perception," Journal of the Franklin Institute 1980 |
| Shades-of-Gray | Finlayson & Trezzi, "Shades of Gray and Colour Constancy," CIC 2004 |
| FC4 | Hu et al., "FC4: Fully Convolutional Color Constancy with Confidence-Weighted Pooling," CVPR 2017 |
| FFCC | Barron & Tsai, "Fast Fourier Color Constancy," CVPR 2017 |
| C4 | Yu et al., "Cascading Convolutional Color Constancy," AAAI 2020 |
| CLCC | Lo et al., "CLCC: Contrastive Learning for Color Constancy," CVPR 2021 |
| WB-sRGB | Afifi & Brown, "Sensor-Independent Illumination Estimation for DNN Models," TPAMI 2022 |
| Mixed WB / Deep WB | Afifi et al., "Deep White-Balance Editing," CVPR 2020 |
| NUS-8 Dataset | Cheng et al., "Illuminant Estimation for Color Constancy: Why Spatial-Domain Methods Work and the Role of the Color Distribution," JOSA-A 2014 |
| Cube+ Dataset | Banic & Loncaric, "Unsupervised Learning for Color Constancy," 2017; Banic et al., "Cube+: A New Dataset and Method for Illumination Estimation," 2020 |

---

## 习题

**练习 1（理解）**
PSNR 基准数字的可比性有严格前提条件：必须使用相同的测试集、相同的图像裁切方式（有些方法对图像边界做裁切再计算 PSNR，有些不做）、相同的色彩空间（RGB vs. Y 通道）和相同的数值精度（uint8 vs. float32）。请分析：在超分辨率排行榜中，若某方法在 Y 通道计算 PSNR（而非 RGB 全通道），相比 RGB 全通道 PSNR 通常高出多少？若测试时对图像做 8 像素边界裁切（standard border crop），与不裁切相比 PSNR 通常高出多少？这两个因素相加能否达到 0.5dB 以上的"虚假提升"？

**练习 2（分析/比较）**
SRCC（Spearman Rank Correlation Coefficient）和 PLCC（Pearson Linear Correlation Coefficient）是评测 IQA 模型与人类主观评分一致性的两个核心指标。请解释两者的本质区别：SRCC 衡量的是什么（排名一致性），PLCC 衡量的是什么（线性相关性），以及何时两者会产生明显差异。在 IQA 评测中，一个模型的 SRCC 高但 PLCC 低意味着什么（能正确排序但无法预测绝对分值）？对 ISP 调参而言，哪个指标更有实用价值？

**练习 3（实践）**
验证不同评测条件对 PSNR 数字的影响。取同一组超分辨率模型输出（如 SRCNN 在 Set5 测试集上的结果），分别用以下三种方式计算 PSNR：（1）RGB 全通道，无裁切；（2）仅 Y 通道（YCbCr 空间），无裁切；（3）仅 Y 通道，裁切 scale 倍边界像素。比较三种方式的数值差异，并分析为什么学术论文必须明确报告评测配置细节，才能使不同论文的数字具有可比性。

---

*附录F — 基准测试结果 | 最后更新：2026年*
