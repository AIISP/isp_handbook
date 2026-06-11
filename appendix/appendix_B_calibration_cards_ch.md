# 附录B — 标定卡标准参考 | Calibration Chart Standards

> 本手册所用全部标定卡的快速参考。
> 测量程序请参见各相关章节的§2标定部分。

---

## 总览

标定卡（又称测试卡或靶标）是用于表征ISP模块的物理或数字参考物，每种卡针对特定图像质量属性的测量进行了优化。本附录列出最常见的标定卡、其结构、所产生的指标及所支持的ISP模块。

---

## B.1 Macbeth ColorChecker 24（经典款）

| 字段 | 详情 |
|-------|---------|
| **全称** | Macbeth ColorChecker Classic（X-Rite公司） |
| **用途** | 颜色精度标定、AWB真值、CCM拟合 |
| **结构** | 4×6网格 = 24块彩色色块：第1–2行（12块）自然物体色（肤色/天空/植物等）、第3行（6块）原色与间色、第4行（6块）消色差灰阶（从近白到近黑） |
| **关键色块** | 第4行（底部）：从D18到近黑的灰度阶 |
| **提取指标** | ΔE₀₀（逐色块）、均值/最大ΔE、灰度中性度、CCM拟合残差 |
| **标定模块** | CCM（第二卷第06章）、AWB（第二卷第05章）、Gamma（第二卷第07章） |
| **测量标准** | 光源：D50或D65。推荐观察者：CIE 1931 2°。参考XYZ值来自制造商。 |
| **公开参考** | https://www.xrite.com/categories/calibration-profiling/colorchecker-classic |
| **备注** | 24块色块涵盖一系列自然物体颜色。L形灰度行（色块19–24）对白平衡和中性度评估尤为关键。X-Rite公开了D50/D65下所有24块的CIE Lab参考值。 |

**典型ISP用法（第二卷第06章CCM拟合）：**

```
1. 在D65光照下以RAW格式采集色卡。
2. 提取每块平均RGB（避开色块边缘）。
3. 应用当前流水线直到CCM前阶段。
4. 求解：M_CCM = argmin Σᵢ ΔE²(M · RGB_i^sensor, XYZ_i^reference)
5. 评估：报告均值ΔE₀₀和最大ΔE₀₀。
```

---

## B.2 ISO 12233 / SFRplus

| 字段 | 详情 |
|-------|---------|
| **全称** | ISO 12233:2017 摄影——电子静止图像成像——分辨率和空间频率响应 |
| **用途** | 空间分辨率测量、MTF50特性描述 |
| **结构** | 多个倾斜边缘（5°倾斜）分布于各视场位置 + 双曲线/正弦波形用于目视评估 |
| **关键特征** | 中心和四角处的倾斜边缘区域，用于空间频率响应（SFR/MTF）测量 |
| **提取指标** | MTF50（周期/像素或线对/毫米）、MTF50P、MTF30、空间频率响应曲线 |
| **标定模块** | 锐化（第二卷第04章）、光学/镜头（第一卷第02章）、去马赛克（第二卷第02章） |
| **测量标准** | ISO 12233:2017。软件：Imatest、OpenCV SFR或开源sfr-esfr |
| **公开参考** | https://www.iso.org/standard/71696.html |
| **SFRplus变体** | 添加了高对比度倾斜边缘以实现自动检测，视场均匀性测量。Imatest专用。 |
| **备注** | 倾斜边缘法是MTF测量的行业标准。边缘应倾斜3–7°以实现亚像素采样。需要足够对比度比（≥50:1）。 |

---

## B.3 Siemens星形靶

| 字段 | 详情 |
|-------|---------|
| **全称** | Siemens星（又称：径向分辨率靶） |
| **用途** | 空间分辨率、去马赛克伪影检测、混叠可视化 |
| **结构** | 径向对称图案，黑白扇区交替向中心点收敛。通常为36或72个扇区。 |
| **关键特征** | 随半径减小，空间频率增大。图案变得难以分辨的半径给出分辨率极限。 |
| **提取指标** | 极限分辨率（周期/像素）、混叠可见度、高频处的颜色摩尔纹 |
| **标定模块** | 去马赛克（第二卷第02章）、锐化（第二卷第04章） |
| **测量标准** | ISO 15739，多种实现 |
| **公开参考** | https://en.wikipedia.org/wiki/Siemens_star |
| **备注** | 特别适合检测去马赛克引起的混叠：颜色摩尔纹在星形中心附近表现为彩色条纹。目视检查与定量MTF测量互为补充。 |

---

## B.4 USAF 1951分辨率靶

| 字段 | 详情 |
|-------|---------|
| **全称** | 美国空军1951年MIL-STD-150A分辨率测试卡 |
| **用途** | 极限分辨率测量 |
| **结构** | 各组由3条水平和3条垂直条纹图案组成，空间频率逐渐增大。组别-2至+7，每组包含元素1–6。 |
| **关键特征** | 每个组/元素组合对应特定的空间频率（线对/毫米）。 |
| **提取指标** | 极限分辨率（线对/毫米，即条纹可分辨的最高组/元素） |
| **标定模块** | 光学（第一卷第02章）、去马赛克（第二卷第02章） |
| **公开参考** | https://en.wikipedia.org/wiki/USAF_1951_resolution_test_chart |
| **空间频率公式** | f [lp/mm] = 2^(Group + (Element-1)/6) |
| **备注** | USAF靶主要用于显微镜和科学成像。在消费相机ISP中，ISO 12233倾斜边缘法因其亚像素精度更受青睐，但USAF仍可用于快速目视分辨率检查。 |

---

## B.5 X-Rite ColorChecker Passport Photo 2

| 字段 | 详情 |
|-------|---------|
| **全称** | X-Rite ColorChecker Passport Photo 2 |
| **用途** | 宽色域颜色标定、肤色特性描述、创意色彩匹配 |
| **结构** | 折叠卡上3张图表：（1）经典24色块；（2）创意增强（饱和度提升）色块；（3）白平衡靶（纯白/灰色块） |
| **关键特征** | 小巧形态（护照尺寸）。宽色域色块超出sRGB范围，用于RAW到显示流水线的特性描述。 |
| **提取指标** | ΔE₀₀、肤色准确度、ICC色彩特性描述文件质量 |
| **标定模块** | CCM（第二卷第06章）、AWB（第二卷第05章）、Gamma（第二卷第07章） |
| **公开参考** | https://www.xrite.com/categories/calibration-profiling/colorchecker-passport-photo-2 |
| **备注** | 白平衡靶（4块中性色块）为现场条件下AWB标定提供干净参考。创意增强行用于测试色域映射和鲜艳色彩渲染。 |

---

## B.6 eSFR ISO 12233（倾斜边缘靶）

| 字段 | 详情 |
|-------|---------|
| **全称** | 增强空间频率响应（eSFR）靶，符合ISO 12233:2017 |
| **用途** | 多视场位置MTF测量、横向色差、几何畸变 |
| **结构** | 多个倾斜边缘分布于视场（中心 + 4角 + 中间边缘位置）。包含灰度阶和彩色色块。 |
| **关键特征** | 自动边缘检测实现全视场快速MTF50映射。 |
| **提取指标** | MTF50图（视场均匀性）、色差（横向）、畸变 |
| **标定模块** | 锐化（第二卷第04章）、LSC（第二卷第08章）、光学（第一卷第02章） |
| **测量标准** | ISO 12233:2017附录A（倾斜边缘法） |
| **公开参考** | Imatest eSFR文档：https://www.imatest.com/solutions/esfr-iso-12233/ |
| **备注** | eSFR靶是智能手机相机量产中产线IQA的当前首选标准。其分辨率和色彩色块在单张图中的结合降低了测试夹具的复杂性。 |

---

## B.7 18%灰卡

| 字段 | 详情 |
|-------|---------|
| **全称** | 18%中性灰反射率卡 |
| **用途** | 曝光标定、噪声测量、增益标定 |
| **结构** | 均匀的平整灰色表面，反射率≈18%（摄影量表上约低于中间调1EV） |
| **关键特征** | 光谱中性。提供已知亮度用于绝对曝光标定。 |
| **提取指标** | 绝对曝光（EV）、读出噪声底、ISO X处的SNR、PTC斜率（光子转移系数α） |
| **标定模块** | BLC（第二卷第01章）、噪声模型（第一卷第04章）、AE标定（第四卷第02章） |
| **备注** | 用于噪声模型标定：在不同ISO下采集一系列18%灰色帧。绘制每通道方差vs.均值信号。斜率 = 光子转移系数α；y轴截距≈读出噪声β。这产生泊松-高斯噪声模型参数。参见第一卷第04章§2。 |

---

## B.8 平场（均匀照明视场）

| 字段 | 详情 |
|-------|---------|
| **全称** | 平场/均匀照明靶 |
| **用途** | 镜头阴影特性描述、黑电平标定 |
| **结构** | 非物理卡——均匀积分球或光箱，在全视场产生空间均匀辐亮度 |
| **关键特征** | 采集图像中任何空间非均匀性都归因于光学系统（渐晕）+ 传感器（PRNU） |
| **提取指标** | 每色通道增益图G(x,y)；角-中心比；LSC多项式系数 |
| **标定模块** | LSC（第二卷第08章）、BLC（第二卷第01章） |
| **程序** | （1）在多个光圈和对焦距离下采集平场图。（2）对N帧计算逐像素均值。（3）以中心值归一化：G(x,y) = I_center / I(x,y)。（4）拟合多项式或分段曲面。 |
| **备注** | LSC标定高度依赖光圈（物理渐晕随f/#变化）和对焦距离（微距下光瞳几何变化）。完整的LSC表覆盖全部光圈×对焦距离空间。 |

---

## 汇总表

| 标定卡 | 主要模块 | 关键指标 | 形式 |
|-------|---------------|------------|--------|
| Macbeth ColorChecker 24 | CCM、AWB | ΔE₀₀ | 物理/数字 |
| ISO 12233 / SFRplus | 锐化、光学 | MTF50 | 物理 |
| Siemens星形靶 | 去马赛克、锐化 | 极限分辨率、混叠 | 物理/数字 |
| USAF 1951 | 光学、去马赛克 | lp/mm（目视） | 物理 |
| ColorChecker Passport | CCM、AWB | ΔE₀₀、肤色 | 物理 |
| eSFR ISO 12233 | 锐化、LSC | MTF50视场图 | 物理 |
| 18%灰卡 | BLC、噪声模型、AE | SNR、α、β（噪声参数） | 物理 |
| 平场 | LSC、BLC | 增益图G(x,y) | 积分球 |

---

## B.9 标定流程标准操作规程（Standard Operating Procedure）

### B.9.1 BLC 黑电平标定 SOP

**目标**：准确测量传感器各通道的暗电流基线，确保 BLC 矫正值在温度/增益条件下精确。

**准备条件**
- 镜头盖盖上或传感器完全遮光（光圈收到最小，使用遮光板）
- 传感器温度稳定后开始（通电后等待 3–5 分钟）
- 增益挡位：覆盖所有 ISO 挡（ISO 100/400/800/1600/3200/6400）

**操作步骤**

| 步骤 | 操作 | 验收标准 |
|------|------|---------|
| 1 | 设定曝光时间 = 0（最短可用值，约 1/32000s），ISO 100 | 确认无光线泄漏 |
| 2 | 连续拍摄 16 帧 RAW，提取 OB（光学黑区）行数据 | OB 区像素值均匀度 σ < 2 DN |
| 3 | 对 16 帧求中值，得到 R/Gr/Gb/B 四通道 BLC offset | 四通道差值 ΔBL < 5 DN |
| 4 | 在 10°C / 25°C / 45°C 三个温度下重复步骤 1–3 | 温度系数 dBLC/dT < 0.5 DN/°C |
| 5 | 对所有 ISO 挡重复，建立 BLC (ISO, T) 二维查找表 | 插值误差 < 1 DN |
| 6 | 将标定结果写入 ISP BLC LUT（Chromatix XML 或 MTK NDD 格式）| 验证图像暗角无色偏 |

**验收标准**：BLC 校正后，18% 灰卡各通道均值比值 R/G = 1.000 ± 0.005（待 AWB 前）

**常见问题排查**

| 症状 | 可能原因 | 处理方法 |
|------|---------|---------|
| OB 行波动大（σ > 5 DN）| 遮光不完全或 VDD 不稳定 | 检查遮光板密封，重新稳压 |
| 四通道 BLC 差异 > 10 DN | 通道间增益不一致 | 检查 PDAF 相位差像素偏置设置 |
| 温度漂移 > 1 DN/°C | 暗电流激活能偏高 | 建立精细温度插值表（5°C 间隔）|
| ISO 高时出现固定图案噪声 | 读出放大器固定偏置 | 逐列 BLC 校正（Column BLC）|

**注意事项**

1. OB 区域行数：建议使用至少 8 行 OB 像素进行均值计算，单行 OB 受相邻像素影响较大。
2. 长曝光 BLC：夜景长曝（>1s）需单独建立长曝光 BLC 表，因为暗电流在长曝光下显著积累。
3. 多帧中值滤波优于均值：中值对突发噪声（宇宙射线、电磁干扰）更鲁棒。

---

### B.9.2 LSC 镜头阴影标定 SOP

**目标**：生成每个焦距/光圈/色温组合下的 LSC 增益网格（17×17 或 33×33），补偿镜头暗角和色偏。

**所需设备**
- 均匀光场箱（积分球或 LED 灯板）：均匀度 > 99%（中心 vs 角落亮度比 < 1%）
- 标定卡：无图案白板（白色纸张或均匀漫反射板）
- 颜色温度可控（D50/D65/A 光源切换）

**操作步骤**

```
Step 1: 光场均匀性验证
  - 拍摄均匀白场（单色，不做任何 ISP 处理）
  - 验证中心 1/3 区域与边缘的亮度比 ≤ 1:1.25（± 20%）
  - 若不均匀：调整光源位置或换用积分球

Step 2: 原始 LSC 测量（无校正）
  - 关闭所有 ISP 模块（BLC 保留，LSC 关闭）
  - 每个光源条件下拍摄 8 帧 RAW，平均降噪
  - 计算增益图：G(x,y) = I_center / I(x,y)
  - 四通道分别计算：G_R, G_Gr, G_Gb, G_B

Step 3: 增益平滑与插值（LSC Mesh 生成）
  - 对 G(x,y) 进行 2D 多项式拟合（5×5 到 7×7 阶）
  - 生成 17×17 或 33×33 网格点增益表
  - 验证：拟合残差 RMS < 0.3%
```

**多焦距 LSC 标定矩阵**

| 焦距等效 | 光圈 | 色温条件 | 目录数量 |
|---------|------|---------|---------|
| 0.6× 超广 | f/2.2 | D65 + A | 2 |
| 1× 主摄 | f/1.8 / f/2.8 / f/4.0 | D65 + A | 6 |
| 3.2× 长焦 | f/2.8 | D65 + A | 2 |

**LSC 增益网格格式说明**

高通 Chromatix 格式（17×17 网格，共 289 个节点）：
```xml
<lsc_r_gain>
  <!-- 17 行 × 17 列，行优先，中心=1.0，角落通常 1.5–3.0 -->
  1.862 1.744 1.632 1.534 1.453 1.389 1.341 1.307 1.291 1.307 1.341 1.389 1.453 1.534 1.632 1.744 1.862
  <!-- ... 其余 16 行 ... -->
</lsc_r_gain>
```

MTK NDD 格式（HW 支持 33×33 网格，精度更高）：
```c
// lsc_table[channel][row][col], channel: 0=R,1=Gr,2=Gb,3=B
uint16_t lsc_table[4][33][33] = { ... };
```

**LSC 与颜色一致性**

色温对 LSC 的影响：R/B 通道阴影在不同色温下分布不同（暖光下 B 通道阴影更深）。因此需要为每个光源建立单独的 LSC 表，并在 ISP 中根据 AWB 估计的色温动态插值。

**验收标准**：LSC 校正后均匀白场各通道均匀度 σ/μ < 0.5%（边角与中心亮度差 < 2%）

---

### B.9.3 AWB 色温标定 SOP

**目标**：建立传感器 (R/G, B/G) 增益与色温（CCT）的对应关系，确保多光源条件下白平衡准确。

**标定光源参数**

| 光源 | CCT (K) | 标准 | 用途 |
|------|---------|------|------|
| A 光（钨丝灯）| 2856 K | CIE Illuminant A | 室内暖光 |
| TL84（三基色荧光灯）| 4150 K | CIE F11 | 商业照明 |
| D50 | 5003 K | ISO 3664:2000 | 印刷标准 |
| D65 | 6504 K | CIE Illuminant D65 | 日光标准 |
| D75 | 7500 K | 阴天 | 户外阴影 |

**操作步骤**

```
Step 1: 拍摄 ColorChecker（X-Rite 标准色卡），每个光源下拍摄 5 帧 RAW
Step 2: 提取 ColorChecker 中性灰色块（G/H 行 18% 灰 + N9 白）
Step 3: 计算当前 (R/G, B/G) 增益，即实测值
Step 4: 以 G/G = 1.0 为基准，计算目标增益：
        WB_R = G_target_R / G_measured_R
        WB_B = G_target_B / G_measured_B
Step 5: 验证 ColorChecker 24 色块的 ΔE₀₀ < 3.0（AWB 校正后）
Step 6: 建立 CCT → (WB_R, WB_B) 映射表（Chromatix multi-light-source table）
```

**Planckian 轨迹与 AWB 锁定区域**

AWB 算法通常在 CIE 1931 xy 色度图或 u'v' 色度图上定义锁定区域（Locus），传感器测量落入此区域的像素才参与 AWB 统计：

```
典型 AWB 有效区域（u'v' 色度图）：
  2000K–8000K 普朗克轨迹附近 ±0.05 u'v' 范围
  排除高饱和像素（Chroma > 0.6）
  排除过曝像素（Y > 240）和欠曝像素（Y < 16）
```

**光源间插值验证**

在 3500 K（A 与 TL84 之间）拍摄测试，验证插值后 ΔE₀₀ < 4.0，防止插值过冲。

**多光源场景（混合光）处理**

实际场景中常存在混合光（如日光 + 荧光灯），AWB 需要对光源混合比例进行估计：
- 方法一：加权平均（按各光源面积权重）
- 方法二：最优传输距离匹配（Wasserstein 距离）
- 方法三：基于 CNN 的光源估计（参见第三卷第 01 章）

**验收标准**

| 场景 | 指标 | 阈值 |
|------|------|------|
| 单光源标准场景 | ΔE₀₀（18% 灰）| < 1.5 |
| 单光源 ColorChecker | 均值 ΔE₀₀ | < 3.0 |
| 插值中间色温 | ΔE₀₀ | < 4.0 |
| 混合光场景 | ΔE₀₀ | < 5.0 |

---

### B.9.4 CCM 颜色校正矩阵标定 SOP

**目标**：最小化传感器 RGB 到标准 sRGB（或 Display P3）的颜色误差。

**标定参数**
- 标定卡：X-Rite ColorChecker Classic（24 色块）或 ColorChecker Passport（48 色块）
- 参考值来源：colour-science.org 提供的 D65 下各色块 XYZ 值
- 求解方法：最小二乘（OLS）或加权最小二乘（WLS，对中性灰赋予更高权重 ×3）

**数学推导**

设 N 个色块，传感器测量值 $\mathbf{S} \in \mathbb{R}^{N \times 3}$，参考 sRGB 值 $\mathbf{T} \in \mathbb{R}^{N \times 3}$：

$$\mathbf{M} = \arg\min_{\mathbf{M}} \|\mathbf{S} \mathbf{M}^T - \mathbf{T}\|_F^2$$

OLS 解：$\mathbf{M}^T = (\mathbf{S}^T \mathbf{S})^{-1} \mathbf{S}^T \mathbf{T}$

加权 WLS：$\mathbf{M}^T = (\mathbf{S}^T \mathbf{W} \mathbf{S})^{-1} \mathbf{S}^T \mathbf{W} \mathbf{T}$，其中 $\mathbf{W}$ 为对角权重矩阵。

**约束条件**：白色映射为白色（行和约束：$\sum_j M_{ij} = 1, \forall i$）

**CCM 标定的实际权重策略**

```python
# 权重设置示例（Python）
weights = np.ones(24)
weights[18:24] *= 3.0   # 中性灰轴（色块 19–24）权重 ×3
weights[0:3]  *= 2.0    # 皮肤色（色块 1–3）权重 ×2
weights[6:12] *= 1.5    # 自然物体色权重 ×1.5

W = np.diag(weights)
# WLS 求解
M_T = np.linalg.solve(S.T @ W @ S, S.T @ W @ T)
CCM = M_T.T
```

**多光源 CCM**

不同光源下的 CCM 应分别标定，ISP 根据 AWB 估计的色温在多个 CCM 之间插值：

| 光源 | CCM 用途 |
|------|---------|
| A 光（2856 K）| 室内暖光场景 |
| D65（6504 K）| 日光/标准场景 |
| 插值 | 中间色温自动插值 |

**验收标准**
- 所有 24 色块 $\overline{\Delta E_{00}} < 2.5$（sRGB）或 $< 3.0$（Display P3）
- 中性灰轴（N2–N9.5）$\Delta E_{00} < 1.5$
- 皮肤色（色块 1–3）$\Delta E_{00} < 2.0$（面部识别场景尤为重要）

**CCM 验证流程**

```
1. 使用 colour-science Python 库加载 ColorChecker D65 参考值
2. 对标定后图像提取 24 色块均值 RGB
3. 应用 sRGB gamma 反编码（线性化）
4. 将线性 RGB 转 XYZ（via sRGB 矩阵）
5. 转 CIE Lab（D65 白点）
6. 计算每块 ΔE₀₀（CIEDE2000 公式）
7. 输出均值/最大值/各色块散点图
```

---

### B.9.5 DPC 坏点标定 SOP

**目标**：生成出厂静态坏点图（Static DPC Map），用于静态坏点校正。

**坏点类型定义**

| 类型 | 定义 | 检测方法 |
|------|------|---------|
| 热点（Hot Pixel）| 暗场下亮度 > 均值 + 5σ | 暗场拍摄（遮光），找超阈值像素 |
| 死点（Dead Pixel）| 亮场下亮度 < 均值 - 5σ | 亮场拍摄（白场），找超低像素 |
| 卡滞点（Stuck Pixel）| 像素值恒定（无响应）| 多种亮度下值不变 |
| 簇状缺陷（Cluster Defect）| 3×3 内 ≥ 2 个缺陷 | 聚类检测算法 |

**操作步骤**

```
Step 1: 暗场采集
  - 遮光（镜头盖 + 遮光布），曝光 1/30s，ISO 1600
  - 连续拍摄 16 帧 RAW，逐像素中值叠加（抗随机噪声）
  - 计算全图均值 μ 和标准差 σ
  - 热点 Map = { (x,y) | I(x,y) > μ + 5σ }

Step 2: 亮场采集
  - 均匀白场光源（均匀度 > 95%），曝光使直方图峰值约 80% 满幅
  - 连续拍摄 16 帧 RAW，中值叠加
  - 计算全图均值 μ 和标准差 σ
  - 死点 Map = { (x,y) | I(x,y) < μ - 5σ }

Step 3: 卡滞点检测
  - 在 10%、50%、90% 三个曝光级别分别拍摄
  - 卡滞点 = 三个曝光下值差异 < 2 DN 的像素

Step 4: 合并坏点图
  - Static DPC Map = 热点 Map ∪ 死点 Map ∪ 卡滞点 Map
  - 对 Cluster Defect 进行聚类标记（需单独处理策略）

Step 5: 格式转换
  - 转换为 ISP 平台格式（高通：坐标列表 CSV；MTK：bit-mask 或坐标对）
  - 写入 OTP（One-Time-Programmable Memory）或 XML 配置文件
```

**坏点等级分类**

| 等级 | 坏点数量（/MP）| 处理方式 |
|------|--------------|---------|
| A 级（优良）| < 50 | 正常出货，静态 DPC 校正 |
| B 级（合格）| 50–200 | 正常出货，需静态 + 动态 DPC 双校正 |
| C 级（边缘）| 200–500 | 需客户协商，特殊用途可接受 |
| D 级（不合格）| > 500 | 报废或降级使用 |

**验收标准**：出厂静态 DPC 数量 < 100 像素/MP（100 万像素内坏点 < 100 个）；无簇状缺陷（Cluster）

---

### B.9.6 噪声模型标定 SOP（PTC 曲线）

**目标**：测量传感器的光子转移特性，获取泊松-高斯噪声模型参数 (α, β)，用于 ISP 降噪模块调参。

**原理**

泊松-高斯噪声模型：

$$\sigma^2(s) = \alpha \cdot s + \beta$$

其中：
- $s$：像素均值信号（DN）
- $\sigma^2$：像素方差
- $\alpha$：光子转移系数（photon transfer coefficient），斜率，与量子效率和全阱容量有关
- $\beta$：读出噪声方差（固定噪声底），与暗电流、ADC 精度有关

**测量步骤**

```
Step 1: 准备均匀照明场景（18% 灰卡或积分球）
Step 2: 通过改变曝光时间（保持 ISO 固定），采集 10–15 个不同亮度级别
        覆盖范围：从 5% 满幅到 95% 满幅（避开饱和）
Step 3: 每个亮度级别拍摄 32 帧 RAW
Step 4: 对每个亮度级别：
        - 计算 32 帧的逐像素均值 μ（信号）
        - 计算 32 帧的逐像素方差 σ²（噪声）
        - 取图像中心 512×512 区域的 (μ, σ²) 散点
Step 5: 对 (μ, σ²) 数据做线性拟合（OLS）
        - 斜率 = α
        - 截距 = β
Step 6: 对每个 ISO 挡重复，建立 α(ISO)、β(ISO) 表格
```

**PTC 曲线特征分析**

| 区域 | 特征 | 含义 |
|------|------|------|
| 线性区（5%–85% FW）| σ² = αs + β | 正常工作区间 |
| 饱和前驼峰 | σ² 下降 | 接近满阱，泊松统计失效 |
| 截距 | β ≈ read noise² | ADC 噪声 + 热噪声 |

**应用场景**：标定的 (α, β) 参数用于：
1. BM3D、NLM 等经典降噪算法的噪声估计
2. DNN 降噪网络的训练数据噪声合成
3. HDR 多帧融合的最优权重计算

---

## B.10 标定自动化工具推荐

| 工具 | 功能 | 开源 | 平台 |
|------|------|------|------|
| **Imatest** | 全功能标定（LSC/MTF/SNR/ΔE） | 商业 | Windows/Mac |
| **OpenImatest（MATLAB）** | LSC/CCM 开源替代 | 开源 | MATLAB |
| **colour-science Python** | AWB/CCM 矩阵计算 | 开源 | Python |
| **rawpy + NumPy** | BLC/LSC 原始计算 | 开源 | Python |
| **Qualcomm CIQT** | 高通平台全链路标定 | 厂商工具 | Android（高通） |
| **MTK CameraToolkit** | MTK 平台标定接口 | 厂商工具 | Android（MTK） |
| **OpenCV calibrateCamera** | 几何标定（棋盘格）| 开源 | C++/Python |
| **dcraw / LibRaw** | RAW 格式解码 | 开源 | 跨平台 |
| **ExifTool** | 元数据提取（ISO/曝光/CCT）| 开源 | 跨平台 |

**colour-science Python 使用示例（CCM 计算）**

```python
import colour
import numpy as np

# 加载 ColorChecker D65 参考值（CIE Lab）
cc = colour.CCS_COLOURCHECKERS['ColorChecker 2005']
reference_XYZ = colour.colorimetry.sd_to_XYZ(
    cc.data, illuminant=colour.SDS_ILLUMINANTS['D65']
)

# 传感器测量值（已线性化）
sensor_RGB = np.array([...])  # shape: (24, 3)

# 求解 CCM（3×3）
CCM = colour.characterisation.matrix_colour_correction_Finlayson2015(
    sensor_RGB, reference_XYZ
)
print("CCM:\n", CCM)

# 验证 ΔE₀₀
corrected = sensor_RGB @ CCM.T
corrected_Lab = colour.XYZ_to_Lab(corrected)
reference_Lab = colour.XYZ_to_Lab(reference_XYZ)
delta_E = colour.delta_E(corrected_Lab, reference_Lab, method='CIE 2000')
print(f"Mean ΔE₀₀: {delta_E.mean():.3f}, Max ΔE₀₀: {delta_E.max():.3f}")
```

**rawpy + NumPy BLC 计算示例**

```python
import rawpy
import numpy as np

def compute_blc(raw_path, n_frames=16):
    """计算四通道 BLC offset"""
    frames = []
    for i in range(n_frames):
        with rawpy.imread(raw_path) as raw:
            # 提取 Bayer 原始数据（未处理）
            bayer = raw.raw_image_visible.astype(np.float32)
            frames.append(bayer)

    # 中值叠加降噪
    stack = np.stack(frames, axis=0)
    median_frame = np.median(stack, axis=0)

    # 按 Bayer 通道分离（RGGB 格式）
    R  = median_frame[0::2, 0::2]  # 偶行偶列
    Gr = median_frame[0::2, 1::2]  # 偶行奇列
    Gb = median_frame[1::2, 0::2]  # 奇行偶列
    B  = median_frame[1::2, 1::2]  # 奇行奇列

    blc = {
        'R':  float(np.median(R)),
        'Gr': float(np.median(Gr)),
        'Gb': float(np.median(Gb)),
        'B':  float(np.median(B)),
    }
    return blc
```

---

## B.11 标定数据管理规范

### B.11.1 版本命名约定

```
{SensorModel}_{LensModel}_{CCT}_{ISO}_{Date}_v{Major}.{Minor}
例：OV50H_Samsung_LN5_D65_ISO100_20260515_v1.2
```

字段含义：

| 字段 | 说明 | 示例 |
|------|------|------|
| SensorModel | 传感器型号 | OV50H, IMX890, S5KJN1 |
| LensModel | 镜头模组型号 | Samsung_LN5, Largan_80211 |
| CCT | 标定光源色温 | D65, D50, A, TL84 |
| ISO | 标定 ISO 挡 | ISO100, ISO800, AllISO |
| Date | 标定日期（YYYYMMDD）| 20260515 |
| Major.Minor | 版本号 | v1.0, v1.2, v2.0 |

### B.11.2 目录存储结构

```
calibration_data/
├── blc/
│   ├── OV50H_Samsung_LN5_AllISO_20260515_v1.2.csv    # (ISO, T) 二维 BLC 表
│   └── OV50H_Samsung_LN5_LongExp_20260515_v1.0.csv   # 长曝光 BLC 表
├── lsc/
│   ├── main_1x/
│   │   ├── OV50H_Samsung_LN5_D65_f1.8_20260515_v1.2.xml
│   │   ├── OV50H_Samsung_LN5_A_f1.8_20260515_v1.2.xml
│   │   └── OV50H_Samsung_LN5_D65_f2.8_20260515_v1.0.xml
│   ├── ultra_0.6x/
│   │   └── IMX563_Largan_D65_f2.2_20260515_v1.0.xml
│   └── tele_3.2x/
│       └── OV08A_Genius_D65_f2.8_20260515_v1.0.xml
├── awb/
│   ├── OV50H_Samsung_LN5_AllCCT_20260515_v1.2.xml    # CCT→(WB_R,WB_B) 映射
│   └── OV50H_Samsung_LN5_MixedLight_20260515_v1.0.json
├── ccm/
│   ├── OV50H_Samsung_LN5_D65_20260515_v1.2.txt       # 3×3 矩阵
│   └── OV50H_Samsung_LN5_A_20260515_v1.2.txt
├── dpc/
│   ├── OV50H_SN001_DPCmap_20260515_v1.0.bin          # 个体坏点图（每颗传感器）
│   └── OV50H_SN001_DPCmap_20260515_v1.0.csv          # 人类可读格式
├── noise/
│   ├── OV50H_Samsung_LN5_PTC_AllISO_20260515_v1.0.csv # α(ISO), β(ISO) 表
│   └── OV50H_Samsung_LN5_PTC_20260515_report.pdf      # PTC 曲线报告
└── changelog.md  # 版本变更记录
```

### B.11.3 变更控制规范

**黄金版本冻结时间节点**

| 项目阶段 | 标定数据状态 | 变更权限 |
|---------|------------|---------|
| EVT（工程验证测试）| 初始版本，允许频繁更新 | 工程师直接修改 |
| DVT-A（设计验证测试 A）| 功能完整版，变更需 Review | 需 ISP 主管审核 |
| DVT-B（设计验证测试 B）| 冻结候选版，仅允许 Bug Fix | 需 ECN 流程 |
| PVT（生产验证测试）| **冻结版本**，原则上不允许修改 | 需 ECN + 客户确认 |
| MP（量产）| **量产黄金版**，绝对不允许修改 | 需 ECN + 多方签字 |

**ECN（工程变更通知）模板**

```
ECN-YYYYMMDD-NNN
变更内容：LSC D65 f/1.8 增益表更新（解决角落亮度不足 3% 问题）
影响模块：LSC
影响范围：主摄 1x 所有批次
变更前版本：OV50H_Samsung_LN5_D65_f1.8_20260501_v1.1
变更后版本：OV50H_Samsung_LN5_D65_f1.8_20260515_v1.2
验证记录：见附件 LSC_Validation_20260515.pdf
审核签字：[ISP 主管] [光学主管] [测试主管]
```

### B.11.4 标定数据质量审计

定期（每季度）对标定数据进行审计，检查以下项目：

```
审计清单：
□ 所有量产传感器型号均有对应标定数据
□ 标定数据版本与量产 ISP 固件版本一致
□ DPC Map 为个体标定（非共用）
□ BLC 表覆盖所有 ISO 挡和温度点
□ LSC 表覆盖所有焦距/光圈/色温组合
□ AWB 表覆盖 2000K–8000K 范围
□ CCM 至少有 D65 和 A 光两组
□ PTC 噪声参数文档齐全
□ changelog.md 记录所有版本变更
□ 备份存储到版本控制系统（Git LFS）
```

---

## B.12 各平台标定数据格式参考

### B.12.1 高通（Qualcomm）Chromatix 格式

高通 ISP 使用 Chromatix XML 格式存储所有标定参数。主要模块对应节点：

| 模块 | XML 节点 | 格式说明 |
|------|---------|---------|
| BLC | `<black_level_correction>` | 四通道偏置值 + 温度/ISO 查找表 |
| LSC | `<lens_rolloff_config>` | 17×17 网格，每通道 289 个 uint16 值 |
| AWB | `<awb_algo_config>` | 多光源增益 + 色温区间 |
| CCM | `<color_correction_matrix>` | 3×3 float 矩阵，带温度插值 |
| DPC | `<bad_pixel_correction>` | 静态坏点坐标列表 |

**LSC XML 示例片段**

```xml
<lens_rolloff_config>
  <rolloff_table_size>17</rolloff_table_size>
  <r_gain type="float" length="289">
    1.862 1.744 1.632 1.534 1.453 1.389 1.341 1.307 1.291
    1.307 1.341 1.389 1.453 1.534 1.632 1.744 1.862
    <!-- ... 共 289 个值（17×17 行优先）... -->
  </r_gain>
  <gr_gain type="float" length="289"> ... </gr_gain>
  <gb_gain type="float" length="289"> ... </gb_gain>
  <b_gain type="float" length="289">  ... </b_gain>
</lens_rolloff_config>
```

### B.12.2 MTK（MediaTek）NDD 格式

MTK ISP 使用 NDD（Native Device Driver）C 头文件格式存储标定参数。

**BLC NDD 格式示例**

```c
// imx890_blc_table.h
typedef struct {
    uint16_t r_offset;
    uint16_t gr_offset;
    uint16_t gb_offset;
    uint16_t b_offset;
} BLC_ENTRY;

// ISO → BLC 查找表（6 个 ISO 挡 × 3 个温度点）
static const BLC_ENTRY blc_lut[3][6] = {
    // T = 10 degrees C
    { {64, 65, 65, 63}, {66, 67, 67, 65} },
    // T = 25 degrees C
    { {64, 65, 65, 63}, {67, 68, 68, 66} },
    // T = 45 degrees C
    { {65, 66, 66, 64}, {69, 70, 70, 68} },
};
```

### B.12.3 三星（Samsung）Exynos SEHF 格式

三星 Exynos ISP 使用 SEHF（Samsung Exynos HAL Format）JSON 格式：

```json
{
  "calibration_version": "1.2",
  "sensor_id": "S5KHP3",
  "blc": {
    "r_offset": 64,
    "gr_offset": 65,
    "gb_offset": 65,
    "b_offset": 63,
    "iso_lut": [
      {"iso": 100,  "r": 64, "gr": 65, "gb": 65, "b": 63},
      {"iso": 400,  "r": 66, "gr": 67, "gb": 67, "b": 65},
      {"iso": 800,  "r": 68, "gr": 69, "gb": 69, "b": 67},
      {"iso": 1600, "r": 71, "gr": 72, "gb": 72, "b": 70},
      {"iso": 3200, "r": 75, "gr": 76, "gb": 76, "b": 74},
      {"iso": 6400, "r": 82, "gr": 83, "gb": 83, "b": 81}
    ]
  },
  "lsc": {
    "grid_size": 17,
    "r_gain":  [1.862, 1.744],
    "gr_gain": [1.523, 1.432],
    "gb_gain": [1.521, 1.430],
    "b_gain":  [1.901, 1.788]
  }
}
```

---

## B.13 现场标定快速指南

### B.13.1 产线标定（ATE 自动测试设备）流程

在量产阶段，标定操作由 ATE（Automatic Test Equipment）自动执行，每颗模组标定时间目标 < 30 秒。

**典型产线标定序列（时序）**

```
T=0s    上料、通电、初始化
T=3s    BLC 暗场采集（4 帧，遮光）
T=7s    LSC 亮场采集（4 帧，均匀光场）
T=12s   AWB 参考采集（色温光源切换，2×2 帧）
T=18s   OTP 写入（BLC + LSC + AWB 增益）
T=22s   验证读回（OTP CRC 校验）
T=25s   下料
总计：约 25–30 秒/颗
```

**产线标定与实验室标定的差异**

| 项目 | 实验室标定 | 产线标定 |
|------|----------|---------|
| 帧数 | 8–32 帧 | 4–8 帧（速度优先）|
| 温度控制 | 精确控温（±1°C）| 室温（±5°C）|
| 光源精度 | 标准光源（±50 K）| LED 仿真（±100 K）|
| 验证项目 | 全项验证 | 关键指标快速验证 |
| 操作人员 | 工程师 | 操作员（ATE 全自动）|

### B.13.2 OTP 数据结构

OTP（One-Time Programmable）存储器通常集成在摄像头模组内，存储个体标定数据。

**典型 OTP Map（按字节地址）**

```
地址 0x0000–0x000F：模组信息（制造商 ID、传感器 ID、日期）
地址 0x0010–0x001F：BLC 数据（4 通道 × 2 字节 = 8 字节 + CRC）
地址 0x0020–0x02FF：LSC 数据（17×17×4 通道 × 2 字节 ≈ 2312 字节）
地址 0x0300–0x030F：AWB 数据（WB_R、WB_B × 5 光源 = 20 字节）
地址 0x0310–0x031F：模组校验和（CRC-16）
```

**OTP 写入注意事项**

1. OTP 为一次性写入，写入错误无法修正，需 100% 验证后再写。
2. 写入前必须进行 CRC 计算，写入后必须读回比对。
3. 部分平台支持 OTP 分区，允许在保留旧数据的同时写入新分区（Shadowing）。

---

## 习题

**练习 1（理解）**
X-Rite ColorChecker Classic 的 24 个色块选取遵循特定原则：覆盖自然场景中频繁出现的颜色（肤色、天空蓝、草绿、中性灰阶），同时在 CIELAB 色彩空间中较为均匀分布。请分析：在 24 个色块中，哪 6 个色块对 CCM 标定最为关键？为什么纯饱和色（高饱和红/绿/蓝）不被选为主要标定色块？如果需要针对肤色还原专门增强标定，应如何扩展 ColorChecker？

**练习 2（分析/比较）**
Slanted Edge 测试卡用于测量相机系统的 MTF。为了获得准确的 MTF 测量结果，斜边（通常倾斜约 5–10 度）需要满足最低对比度要求。请分析：为什么斜边的倾角选择 5–10 度而不是 1 度或 45 度？如果对比度低于约 10:1，MTF 测量误差会如何放大（与 ESF 插值精度的关系）？ISO 12233 标准对 Slanted Edge 测量的最低场景对比度要求是多少？

**练习 3（实践）**
使用 OpenCV 检测棋盘格角点并评估标定精度。用相机拍摄一张 8×6 棋盘格标定板，调用 `cv2.findChessboardCorners()` 检测角点，再用 `cv2.cornerSubPix()` 进行亚像素精化。测量：（1）角点检测的成功率（不同光照/角度下）；（2）亚像素精化前后的角点定位精度差异（以像素为单位）；（3）使用标定结果对原图做去畸变处理后，棋盘格直线的直线度误差（以像素为单位）。

---

## 参考文献

1. **ISO 17321-1:2012** — Graphic technology and photography: Colour characterisation of digital still cameras (DSCs)
2. **IEC 62341-6-1** — Organic light emitting diode (OLED) displays: Measurement of optical and electro-optical parameters
3. **EMVA Standard 1288** (Edition 4.0, 2021) — Standard for characterisation and presentation of specifications for machine vision sensors and cameras
4. **X-Rite** ColorChecker 参考数据集: https://www.xrite.com/service-support/new_colorchecker_color_standards
5. **colour-science** Python 库文档: https://colour.readthedocs.io/
6. **Imatest** 文档库: https://www.imatest.com/docs/
7. **SMIA（Standard Mobile Imaging Architecture）** CCI 寄存器规范（MIPI Alliance）
8. 第二卷第01章（BLC）、第二卷第08章（LSC）、第二卷第05章（AWB）、第二卷第06章（CCM）详细算法推导参见本手册对应章节。
