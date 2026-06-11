# ISP 工程经验数字速查表

> 这张表汇总了手册中最有价值的工程经验数字，每条标注来源章节。
> 这些数字来自真实工程场景，不是教科书公式的推导结果。截图发群、打印贴墙、随时查阅。

---

## 一、传感器与噪声

| 指标 | 数值 | 适用条件 | 来源章节 |
|------|------|---------|---------|
| 手机旗舰传感器动态范围 | ~12 EV（~72 dB） | 实验室 ISO 15739 标准测量 | [第一卷第07章](part1_imaging_fundamentals/ch07_dynamic_range_hdr/ch07_dynamic_range_hdr_ch.md) |
| 真实场景可用 DR（vs 标称值） | 缩减 2–4 EV | flare + tone mapping + HDR ghost clip 综合损失 | [第一卷第07章](part1_imaging_fundamentals/ch07_dynamic_range_hdr/ch07_dynamic_range_hdr_ch.md) |
| BLC 基座（10-bit ADC） | 32–128 LSB，典型 64 LSB | 约占满量程 6.25% | [第二卷第01章](part2_traditional_isp/ch01_blc_pdpc/ch01_blc_pdpc_ch.md) |
| BLC 基座（12-bit ADC） | 128–512 LSB，典型 256 LSB | 约占满量程 6.25% | [第二卷第01章](part2_traditional_isp/ch01_blc_pdpc/ch01_blc_pdpc_ch.md) |
| per-channel OB 偏差允许误差 | ±1 DN（8-bit 域） | CCM 调参前的校验阈值 | [第二卷第01章](part2_traditional_isp/ch01_blc_pdpc/ch01_blc_pdpc_ch.md) |
| 散粒噪声 SNR 关系 | SNR = √μ（电子数） | 亮部噪声绝对值大但 SNR 高 | [第一卷第04章](part1_imaging_fundamentals/ch04_noise_models/ch04_noise_models_ch.md) |
| RTS 热像素高 ISO 激活率倍增 | 3–5× | 高增益档 vs 低增益档 DPM 采集 | [第二卷第01章](part2_traditional_isp/ch01_blc_pdpc/ch01_blc_pdpc_ch.md) |

---

## 二、对焦与光学

| 指标 | 数值 | 适用条件 | 来源章节 |
|------|------|---------|---------|
| PDAF 精度（正常光照） | ±1 μm | EV > 6 正常曝光 | [第一卷第09章](part1_imaging_fundamentals/ch09_camera_calibration/ch09_camera_calibration_ch.md) |
| PDAF 精度（弱光退化） | ±5–8 μm | EV < 3，退化约 5× | [第一卷第09章](part1_imaging_fundamentals/ch09_camera_calibration/ch09_camera_calibration_ch.md) |
| 相机标定推荐采集张数 | 10–20 张 | 理论最低 3 张，实工程不可用 | [第一卷第09章](part1_imaging_fundamentals/ch09_camera_calibration/ch09_camera_calibration_ch.md) |
| 艾里斑直径（绿光 550nm） | ~1.21 μm | f/1.8、λ=550nm | [第一卷第02章](part1_imaging_fundamentals/ch02_optics_basics/ch02_optics_basics_ch.md) |
| LSC 增益表尺寸（高通） | 17×13 mesh（Q8.8 定点） | 高通 CamX XML 配置 | [第二卷第08章](part2_traditional_isp/ch08_lsc/ch08_lsc_ch.md) |

---

## 三、AWB 与颜色

| 指标 | 数值 | 适用条件 | 来源章节 |
|------|------|---------|---------|
| AWB 可信统计区间 | 3000–7000 K | 普朗克轨迹附近 | [第二卷第05章](part2_traditional_isp/ch05_awb/ch05_awb_ch.md) |
| McCamy 公式精度 | ±50 K（连续谱），±200–500 K（荧光灯） | 荧光灯属非连续谱，公式失效 | [第一卷第05章](part1_imaging_fundamentals/ch05_color_science_basics/ch05_color_science_basics_ch.md) |
| CCM 残差网络色准提升 | ΔE₀₀ 降低约 0.3–0.5 | 硬件 CCM 后软件后处理层 | [第二卷第06章](part2_traditional_isp/ch06_ccm/ch06_ccm_ch.md) |
| ΔE₀₀ vs ΔE₇₆ 比值 | ΔE₀₀ ≈ 0.60–0.80 × ΔE₇₆ | 量产验收首选 ΔE₀₀ | [第二卷第06章](part2_traditional_isp/ch06_ccm/ch06_ccm_ch.md) |
| 色准量产目标（旗舰） | ΔE₀₀ < 2.0 | ColorChecker 24 色 | [第四卷第08章](part4_system_iqa/ch08_iqa_system/ch08_iqa_system_ch.md) |

---

## 四、降噪

| 指标 | 数值 | 适用条件 | 来源章节 |
|------|------|---------|---------|
| NR_Chroma 强度 vs NR_Luma | 高 2–4 倍 | 彩噪视觉上比亮度噪声更显眼 | [第二卷第03章](part2_traditional_isp/ch03_denoising/ch03_denoising_ch.md) |
| NLM 滤波强度参数 h 经验值 | h = k·σ，k ≈ 0.4 | Buades 2005，实际应在验证集调参 | [第二卷第03章](part2_traditional_isp/ch03_denoising/ch03_denoising_ch.md) |
| AHD Demosaic 误判率 | 显著上升（ISO > 800） | 噪声污染梯度方向估计 | [第二卷第02章](part2_traditional_isp/ch02_demosaic/ch02_demosaic_ch.md) |

---

## 五、时域降噪（TNR）

| 指标 | 数值 | 适用条件 | 来源章节 |
|------|------|---------|---------|
| 帧间对齐误差上限 | ≤ 0.25 px | TNR/HDR 合帧，高于此值 SNR 增益减半 | [第二卷第12章](part2_traditional_isp/ch12_temporal_nr/ch12_temporal_nr_ch.md) |
| 对齐误差导致 SNR 增益减半阈值 | 0.5 px | 对齐精度对 SNR 的非线性影响 | [第二卷第12章](part2_traditional_isp/ch12_temporal_nr/ch12_temporal_nr_ch.md) |
| TNR vs EIS 处理顺序 | **TNR 必须先于 EIS** | EIS 后坐标系不一致，块匹配失效 | [第二卷第12章](part2_traditional_isp/ch12_temporal_nr/ch12_temporal_nr_ch.md) |
| EIS 图像裁剪比 | 10–20% | 导致有效 FOV 缩小 | [第二卷第12章](part2_traditional_isp/ch12_temporal_nr/ch12_temporal_nr_ch.md) |

---

## 六、AE 与 3A

| 指标 | 数值 | 适用条件 | 来源章节 |
|------|------|---------|---------|
| AE Tolerance 推荐范围 | ±3–5% | 防止呼吸效应振荡（Hunting） | [第四卷第01章](part4_system_iqa/ch01_3a_system/ch01_3a_system_ch.md) |
| Anti-Banding 快门约束（50 Hz） | 10ms 整数倍 | 中国、欧洲市场主力频率 | [第四卷第01章](part4_system_iqa/ch01_3a_system/ch01_3a_system_ch.md) |
| Anti-Banding 快门约束（60 Hz） | 8.33ms 整数倍 | 美国、日本、韩国市场 | [第四卷第01章](part4_system_iqa/ch01_3a_system/ch01_3a_system_ch.md) |

---

## 七、DL-ISP 量化与部署

| 指标 | 数值 | 适用条件 | 来源章节 |
|------|------|---------|---------|
| INT8 全量化 vs FP16 带宽节省 | 50% | 相比 FP16，是实现实时 12MP 处理的关键 | [第三卷第14章](part3_dl_isp/ch14_on_device_npu/ch14_on_device_npu_ch.md) |
| QAT vs PTQ PSNR 损失控制 | ≤ 0.2 dB | ISP 任务中 QAT 优于 PTQ | [第三卷第14章](part3_dl_isp/ch14_on_device_npu/ch14_on_device_npu_ch.md) |
| INT8 量化损失（敏感层） | 0.3–0.8 dB PSNR | 最后一层最敏感，建议 INT16 | [第三卷第14章](part3_dl_isp/ch14_on_device_npu/ch14_on_device_npu_ch.md) |
| 视频降噪帧延迟预算（30fps） | ≤ 33 ms | 超过此值无法满足实时约束 | [第三卷第08章](part3_dl_isp/ch08_video_denoising/ch08_video_denoising_ch.md) |
| 视频降噪帧延迟预算（60fps） | ≤ 16 ms | 旗舰高帧率视频场景 | [第三卷第08章](part3_dl_isp/ch08_video_denoising/ch08_video_denoising_ch.md) |
| DL 超分端侧延迟目标（1080p） | < 5 ms（INT8） | NPU 部署 IMDN/RFDN 级轻量模型 | [第三卷第03章](part3_dl_isp/ch03_super_resolution/ch03_super_resolution_ch.md) |
| 手机 NPU 可用显存上限（典型） | 100–200 MB | 多模型加载约束 | [第三卷第22章](part3_dl_isp/ch22_universal_restoration/ch22_universal_restoration_ch.md) |
| 多任务联合训练单任务 PSNR 损失 | ~0.2–0.5 dB | vs 单任务专家模型基线 | [第三卷第22章](part3_dl_isp/ch22_universal_restoration/ch22_universal_restoration_ch.md) |

---

## 八、IQA 与质量评估

| 指标 | 数值 | 适用条件 | 来源章节 |
|------|------|---------|---------|
| MTF50 测量方法 | ISO 12233 倾斜边缘法（SFR） | 空间频率响应，单位 lp/ph | [第四卷第08章](part4_system_iqa/ch08_iqa_system/ch08_iqa_system_ch.md) |
| 1 EV 对应 dB 数 | ≈ 6.02 dB | 换算公式：1 EV = 20·log₁₀(2) | [第一卷第07章](part1_imaging_fundamentals/ch07_dynamic_range_hdr/ch07_dynamic_range_hdr_ch.md) |

---

## 使用说明

- **带 * 的数值**：已在 `VERIFIED_CORRECTIONS.md` 中核实过，可直接引用
- **无 * 的数值**：来自章节中的工程经验描述，使用前建议参阅原章节核实场景适用性
- **更新**：提 [Issue](https://github.com/AIISP/isp_handbook/issues) 或 PR 补充你在实际项目中验证过的工程数字

---

*最后更新：2026-06*
