# 第二卷第01章：黑电平校正与像素缺陷校正（BLC & PDPC）

> **流水线位置（Pipeline position）：** ISP 流水线最前端，紧接 ADC 输出之后，所有其他处理块之前
> **前置章节（Prerequisites）：** 第一卷第03章（传感器物理），第一卷第04章（噪声模型）
---

## §1 原理 (Theory)

### 1.1 BLC — 黑电平校正（Black Level Correction）

#### 1.1.1 为什么暗帧的输出不为零？

遮住镜头拍一张图——理想情况下应该全黑，实际上不是。不是 0，而是一个几十到几百 LSB 的非零底部。这个底部来自三件事叠在一起：

**1. 暗电流（Dark current）**

即使无光照，热激发也会在耗尽层产生电子-空穴对。暗电流密度 $J_\text{dark}$ 遵循阿伦尼乌斯（Arrhenius）关系，近似满足每升温 $\Delta T_2$ 倍增规律：

$$J_\text{dark}(T_2) \approx J_\text{dark}(T_1) \cdot 2^{(T_2 - T_1)/\Delta T_2}$$

其中倍增温度 $\Delta T_2$ 因器件工艺而异，典型范围为 **6–8 °C** **[3][5]**（参见 Janesick 2007，第 5 章；EMVA 1288 §3.6）。以 $\Delta T_2 = 7\ ^\circ\text{C}$ 为例，传感器从 25 °C 升温至 60 °C，暗电流增大约 32 倍。

> **工程注意：** 移动手机拍照曝光时间通常短于 1/30 s，此条件下暗电流对总黑电平的贡献往往小于放大器固定偏移；但视频录制及夜景长曝光场景下，暗电流的温度漂移成为主要误差源，不可忽略。

**2. 固定图案偏移（Fixed-pattern offset，FPN）**

列级与像素级差分放大器存在非零输入参考偏移，在帧间高度可重复，在空间上表现为列纹或块状图案。FPN 是所有 ADC 码率下都存在的稳定偏置，与曝光时间无关。

**3. ADC 基座（ADC pedestal）**

传感器设计中故意在 ADC 输出中加入数字偏置，防止模拟噪声将信号拉至负值后数字编码溢出。典型基座：10 位系统 32–128 LSB（业界通行典型值为 **64 LSB**，约占满量程的 6.25%），12 位系统 128–512 LSB（常见典型值为 **256 LSB**，约占满量程的 6.25%）。具体取值因传感器架构和 ISP 管线裕量而异，过大的基座会压缩有效动态范围。

三者叠加后的总和就是**黑电平（black level）**，有时也叫**光学黑电平（optical black level）**。它是一个稳定的直流偏置，不去除的话，下游所有模块——AWB 的通道比值计算、CCM 的线性变换假设、Gamma 的黑点定义——全都建立在一个偏移的基础上，结果都会跑偏。

#### 1.1.2 光学黑区域（Optical Black Region）

多数图像传感器在阵列边缘保留一圈物理遮光像素带——**光学黑（OB）区域**。OB 像素上方有金属遮光层，无法接收光线，其输出就是当前帧黑电平的真实采样，随温度和增益实时变化。

听起来很完美，但现实里 OB 区域并不总是可靠的。OB 行靠近感光区边缘，PCB layout、电源纹波、模组结构都可能造成漏光；部分 sensor 厂商出于这个顾虑，干脆在 sensor 内部就把 OB 减掉，ISP 拿到的数据里已经没有 OB 行了。这种情况下只能靠标定 LUT。

```
┌──────────────────────────────────────────────────┐
│   OB rows（顶部遮光行，通常 16–32 行）             │
├──────┬───────────────────────────────────────────┤
│ OB   │                                           │
│ cols │     Active imaging area                   │
│（遮  │     （有效成像区域）                       │
│光列）│                                           │
└──────┴───────────────────────────────────────────┘
```

**OB 均值估计——正确做法：截断均值（Trimmed Mean）**

直接对 OB 区域取全局均值是最常见的新手错误。问题在于：

- OB 行靠近有效区域边缘，部分像素受**漏光（light leakage）**污染，信号偏高
- OB 区域中混有**热像素**，会系统性地拉高估计值
- PDAF 传感器在 OB 区域内也有遮光/开窗像素，信号行为和正常 OB 不一样

推荐做法：对每个通道 $c \in \{R, G_r, G_b, B\}$ 使用截断均值：

$$\text{OB}_c = \frac{1}{|P_c'|} \sum_{(i,j) \in P_c'} R(i, j)$$

其中 $P_c'$ 是从 $P_c$（通道 $c$ 的所有 OB 像素）中剔除最低 $\alpha\%$ 和最高 $\beta\%$ 分位后的子集，典型起始值 $\alpha = 5$，$\beta = 10$ （当暗场分布呈高端长尾时，令 $\beta > \alpha$ 可优先抑制热像素和漏光污染；但具体数值应结合实测暗场直方图标定，而非作为通用固定参数）。

**$\alpha$、$\beta$ 参数的标定方法：**

$\alpha$（下截断比例）和 $\beta$（上截断比例）应根据传感器热像素分布直方图确定，**而非固定使用经验值**：

1. 采集 ≥ 100 帧暗场，统计 OB 区域各像素值的分布直方图
2. 下截断 $\alpha$：设置为使下尾（读出噪声尾部）不超过 OB 总像素数 5% 的分位数
3. 上截断 $\beta$：设置为使上尾（热像素异常高值）不超过 0.5% 的分位数——**此值需根据热像素密度调整**：
   - 普通 CIS（热像素 < 0.1%）：$\beta \approx 5–10\%$
   - 高集成 PDAF 传感器（PDAF 相位像素噪声较高）：$\beta$ 可提高至 15–20%，避免 PDAF 像素噪声拉高 OB 均值估计
4. 随温度变化：在 25°C、45°C、60°C 各重复上述流程，建立温度相关的 $(\alpha, \beta)$ 查找表

对于存在行级 FPN 的传感器，还可以进一步细化为**逐行 OB 估计（Row-wise OB estimation）**：

$$\text{OB}_{c,i} = \text{trimmed\_mean}\bigl\{R(i, j) : (i,j) \in P_{c,i}\bigr\}$$

然后对各行估计值应用时域平滑（滑动均值或低通滤波），抑制行间随机噪声后用于对应行的校正。

#### 1.1.3 BLC 公式

BLC 的核心操作是**减去黑电平偏置并截断至零**，与归一化到 $[0,1]$ 是两个独立步骤，不能合并。

**步骤一：偏置减法（Offset subtraction）**

$$R'_c(i,j) = \text{clip}\bigl(R_c(i,j) - B_c,\ 0,\ W_c\bigr)$$

其中：
- $R_c(i,j)$：通道 $c$ 在像素 $(i,j)$ 处的原始 ADC 编码
- $B_c$：通道 $c$ 的黑电平（来自 OB 实时估计或标定 LUT）
- $W_c$：通道 $c$ 的白电平（满阱饱和值，例如 12 位传感器通常为 4095）
- $\text{clip}(\cdot,0,W_c)$：将结果限制在 $[0, W_c]$，防止负值在后续整数运算中下溢

截断到 $[0, W_c]$ 而非 $[0, 1]$，是因为 ISP 硬件流水线通常以整数定点格式传递数据；归一化是独立的浮点转换步骤，视具体平台实现而定。

**步骤二：归一化（Normalization，可选）**

若下游模块需要线性归一化到 $[0, 1]$，则：

$$I_c^\text{BLC}(i,j) = \frac{R'_c(i,j)}{W_c - B_c}$$

> **重要：** 步骤一和步骤二不能合并为 $(R_c - B_c) / (W_c - B_c)$。理由：步骤一的截断操作必须发生在除法之前，否则负值被归一化为负小数，不等价于截断后的 0。此外，许多 ISP 硬件只执行步骤一（整数偏置减法），归一化推迟到 AWB 或 CCM 阶段处理。

**逐通道校正的必要性：** 即使同一芯片上，四个拜耳通道的放大器偏移也可相差 2–8 LSB。对所有通道用同一个黑电平看起来省事，但这个通道失衡会以色偏的形式一路传播下去——四通道 OB 差异（最大减最小）超过 ±0.5 LSB（8-bit 等效），AWB 和 CCM 就会感知到。**[6]**

#### 1.1.4 BLC LUT 索引维度

黑电平随多个物理量变化，标定 LUT 需覆盖所有显著维度。主要索引维度及其工程优先级如下：

| 索引维度 | 物理原因 | 优先级 |
|----------|----------|--------|
| **模拟增益（Analog Gain）** | 放大器偏移随增益线性增大；不同增益档使用不同放大级，各有独立 offset | 必须 |
| **HCG / LCG 转换增益模式** | 高转换增益与低转换增益对应完全不同的差分对配置，黑电平差异可达数十 LSB | 必须（如传感器支持） |
| **HDR 曝光路径** | 多帧 HDR（长曝光帧 / 短曝光帧）各自经过独立读出路径，黑电平不同 | 必须（如 HDR 模式） |
| **传感器工作模式** | 全分辨率 / 4-in-1 binning / PDAF crop 等模式下像素合并逻辑不同 | 重要 |
| **温度** | 暗电流随温度变化；长曝光场景影响显著 | 可选（有 OB 区域时可隐式补偿） |
| **曝光时间** | 长曝光暗电流累积：$B_c(T_\text{exp}) = B_{c,0} + J_c \cdot T_\text{exp}$ | 长曝光必须 |

实际 BLC LUT 的最小推荐结构：

```
blc_table[analog_gain_idx][cg_mode][channel]  →  B_c  (整数, 与 ADC 同位宽)
```

有 OB 区域且启用逐帧 OB 估计时，LUT 作为初始值和温度变化补偿的后备；无 OB 区域时，LUT 是黑电平的唯一来源，需更细致地覆盖温度和曝光时间维度。

#### 1.1.5 信号链中的黑电平误差传播

<div align="center">
  <img src="img/fig1_1_blc_dark_current.png" width="90%" alt="BLC 暗电流特性">
  <br><em>图 1-1：BLC 暗电流特性——左：暗电流随温度指数增长（倍增温度 7°C）；右：暗场直方图显示 OB 分布和热像素分布。</em>
</div>

黑电平误差 $\varepsilon_c = B_c^\text{used} - B_c^\text{true}$ 在流水线中以加性偏置的形式向下游传播。高通平台的工程经验是：AWB 在暗区偏绿往往不是 AWB 算法的锅，而是 BLC 分通道多扣了一点 OB；如果 ISP 用统一值扣各通道，则不同色温下偏色情况不同——这两种现象都指向 BLC。

- **AWB：** 白平衡增益由通道比值确定，$\varepsilon_R \neq \varepsilon_B$ 时感知到的光源色温偏移。10 位系统中 4 LSB 的通道间 OB 误差，在 ISO 3200 下可产生可见色偏。
- **CCM：** 色彩校正矩阵假设输入线性。加性黑电平误差使矩阵计算点偏离线性域，导致色误差（$\Delta E$）升高。
- **Gamma / 色调映射：** 黑点漂移；过校正导致阴影细节硬裁剪，欠校正导致暗部底噪抬高。

---

<div align="center"><img src="img/fig1_2_ob_layout.png" width="85%" alt="图 1.2 — OB 像素布局示意图"></div>
<p align="center"><em>图 1-2　光学黑（OB）像素在 Bayer RAW 布局中的位置示意 / Fig. 1-2 Optical Black (OB) Pixel Layout in Bayer RAW Sensor Array</em></p>

### 1.2 PDPC — 像素缺陷检测与校正（Pixel Defect Detection & Correction）

#### 1.2.1 缺陷分类

像素缺陷来自制造工艺、热应力和辐射损伤，分为**静态缺陷**和**动态缺陷**两大类。之所以要把这两类分开，是因为它们的处理路径完全不同——静态缺陷出厂查表，动态缺陷运行时检测，混用会两头都做不好：

**静态缺陷（Static defects）**
- 在出厂测试时可被稳定检出
- 存储在传感器 OTP（一次性可编程存储）或 ISP NVM 中，形成**出厂缺陷图（factory defect map）**
- 运行时只需查表，零算力开销

**动态缺陷（Dynamic defects）**
- 仅在特定条件下出现：高温下的热像素（温度相关热像素，也称 Hot Column），高增益下的随机电报信号（RTS）噪声像素，长曝光下的新增热像素
- 无法全部预先标定；需在运行时逐帧检测

EMVA 1288 标准（Release 4.0, 2021）**[1]** 将缺陷类型定义如下：

| 缺陷类型 | 行为特征 | 物理成因 |
|----------|----------|----------|
| **热像素（Hot pixel）** | 无论曝光如何始终偏亮，暗场中接近饱和 | 晶体缺陷导致暗电流过大；高温/长曝光下尤为明显 |
| **死像素（Dead pixel）** | 始终偏暗，停留在黑电平附近 | 光电二极管断路或列线断裂 |
| **卡死像素（Stuck pixel）** | 固定在某一中间值，不响应光照变化 | 栅极氧化层损伤；辐射诱导电荷陷阱 |
| **闪烁像素（Blinker）** | 帧间交替出现正常和缺陷状态 | 部分填充的电荷陷阱；RTS 噪声 |
| **簇缺陷（Cluster defect）** | ≥2 个相邻缺陷像素 | 相邻缺陷扩散或制造光刻误差 |

#### 1.2.2 PDAF 像素——不是缺陷！

在相位检测自动对焦（PDAF）传感器中，AF 像素通过遮挡部分微透镜开口来实现相位差测量。这些像素对光线的响应与周边像素不同，在 RAW 图像中表现为规律性的暗点。

**PDAF 像素必须与真实缺陷像素分开处理。** 把 PDAF 遮光像素当作死像素用 PDPC 插值，是量产中常见的配置错误——坐标图搞混了，AF 就哑了。正确做法：

- PDAF 像素位置固定、可预测，出厂固件中有独立的 PDAF 坐标图，与缺陷图分开存储
- 高通 Spectra ISP 有独立的 PDAF Replacement 路径；libcamera/RPi 在 `rpi.af` 模块中处理 PDAF 像素，与 PDPC 路径分离
- 执行顺序：BLC → PDAF 专用校正 → PDPC，不能颠倒

#### 1.2.3 检测方法

**方法一：暗帧法（热/死像素静态检测，适用于标定阶段）**

遮住镜头，在目标温度和增益下采集多帧暗帧（64 帧以上），计算逐像素均值 $\bar{D}(i,j)$ 和全局分布参数：

$$\text{score}_\text{hot}(i,j) = \frac{\bar{D}(i,j) - \bar{D}_\text{global}}{\sigma_{D,\text{global}}}$$

若 $\text{score} > \tau_\text{hot}$（典型 5–10）**[1]**，标记为热像素。死像素用平场图进行对应检测。

**方法二：局部邻域动态检测（运行时）**

对每个像素 $(i,j)$，在 Bayer 域内取同通道 $k \times k$ 邻域（排除中心，步距 2 以跳过异色通道）。固定阈值 $\tau = 3.0$ 只在均匀平场下好用——到了高亮区（散粒噪声大）和暗区（读出噪声主导），误检率会差出好几倍，实际上根本不可用。阈值必须随信号强度自适应调整：

正确的信号自适应检测阈值（参见 Nakamura 2006 第 4 章；Liu et al. 2006）**[4][7]**：

$$T(i,j) = \tau \cdot \sqrt{\sigma_r^2 + k_\text{gain} \cdot \hat{I}(i,j)}$$

其中：
- $\sigma_r^2$：读出噪声方差（固定，来自标定）
- $k_\text{gain}$：当前模拟增益下的散粒噪声系数（$\approx$ 电子/ADC码的转换系数）
- $\hat{I}(i,j)$：当前像素的局部邻域均值（代理为期望信号强度）
- $\tau$：灵敏度控制系数，典型范围 2.5–5.0 ，由调参工程师根据漏检率与误检率指标确定

检测条件：

$$|I(i,j) - \hat{I}(i,j)| > T(i,j)$$

**$k_\text{gain}$ 的物理含义与标定方法：**

$k_\text{gain}$ 是**光子计数方差系数**，理论值等于每光电子在输出 DN 域的方差贡献，即系统增益 $K$ 的倒数：$k_\text{gain} = 1/K \approx a$（散粒噪声系数，见第一卷第04章 §1）。该值与传感器工艺和当前模拟增益档有关，**必须按传感器、按增益档单独标定**，不能使用统一经验值。

**标定流程：**
1. 在积分球下采集多个曝光档位的平场帧对（至少 8 档，覆盖 5%–90% 饱和度）
2. 用差帧法（$\sigma^2 = \text{Var}(I_1 - I_2)/2$）提取每档位的 $\sigma^2$ vs $\bar{I}$ 数据点
3. 在 $\sigma^2$-$\bar{I}$ 坐标中拟合直线 $\sigma^2 = k_\text{gain} \cdot \bar{I} + \sigma_r^2$
4. 斜率即为 $k_\text{gain}$，截距为读出噪声方差 $\sigma_r^2$
5. 对每个模拟增益档（×1, ×2, ×4, ×8…）重复上述步骤，建立 $k_\text{gain}(g_a)$ 查找表

> 工程提示：ISP 运行时按当前增益档查表获取 $k_\text{gain}$，代入信号自适应阈值公式。若 $k_\text{gain}$ 取值偏大（过估散粒噪声），热像素漏检率下降但可能误检正常边缘像素；偏小则漏检增加。建议在不同 ISO 的暗场帧上验证漏检率 < 0.1%、误检率 < 0.01%。

**静态图与动态检测的实际组合策略：**

| 策略 | 延迟 | 覆盖范围 | 算力 |
|------|------|----------|------|
| 仅静态图（OTP/NVM 查表） | 零 | 出厂标定的稳定缺陷 | 极低 |
| 仅动态检测 | 1 帧 | 全覆盖，含温度相关热像素 | 中等 |
| 混合（静态 + 动态） | 零 + 1 帧 | 最优 | 低（静态命中率高，动态仅处理新增） |

工程最佳实践：维护静态缺陷图（定期通过 OTA 或出厂校准更新），同时以保守阈值运行动态检测以捕获高温/高增益下的新增热像素。

#### 1.2.4 校正方法

检测到缺陷后，用邻域估计值替换缺陷像素。所有校正均在 Bayer 域内进行，只使用**同通道**邻域像素，以保持 Bayer 图案完整供下游去马赛克使用。

**方向自适应插值（Direction-adaptive interpolation）**

简单均值或中值替换在边缘区域会引入校正伪影。方向自适应方法根据各方向的梯度大小选择插值方向，在保留边缘信息的同时校正缺陷：

$$I_\text{corr}(i,j) = \sum_{d \in \{H, V, D1, D2\}} w_d \cdot \hat{I}_d(i,j)$$

权重 $w_d \propto 1 / (g_d + \epsilon)$，其中 $g_d$ 是方向 $d$ 上的梯度幅值，$\epsilon$ 防止除零。梯度越小（方向越平坦），该方向的权重越大，插值越可靠。

孤立单像素缺陷的简化公式（Bayer 步距为 2）：

$$\hat{I}_H(i,j) = \frac{I(i, j-2) + I(i, j+2)}{2}, \quad g_H = |I(i, j-2) - I(i, j+2)|$$
$$\hat{I}_V(i,j) = \frac{I(i-2, j) + I(i+2, j)}{2}, \quad g_V = |I(i-2, j) - I(i+2, j)|$$

**中值校正（Median replacement）**

适用于簇缺陷（多个相邻缺陷像素）或快速近似实现，邻域应扩展到 $5 \times 5$ 或更大：

$$I_\text{corr}(i,j) = \text{median}\bigl\{I(r,c) : (r,c) \in \mathcal{N}(i,j),\ (r,c) \notin \text{defect\_map}\bigr\}$$

### RAW 域 vs RGB 域 PDPC 实现差异

PDPC 可以在 Bayer RAW 域或去马赛克后的 RGB 域执行，两种实现各有权衡：

| 维度 | RAW 域 PDPC（推荐）| RGB 域 PDPC |
|------|-----------------|------------|
| 执行时机 | BLC 之后、Demosaic 之前 | Demosaic 之后 |
| 插值参考 | 同色（同通道）相邻像素 | 跨通道 RGB 三邻域 |
| 优势 | 保留 Demosaic 灵活性；避免坏点"烘入"去马赛克输出 | 利用颜色相关性，对孤立热像素的替换更自然 |
| 劣势 | 同色邻域稀疏（Bayer 中每种颜色间距为 2 像素），边缘处插值较粗糙 | 若 Demosaic 已将坏点扩散到多像素，后期纠正不完全 |
| 工业实践 | 高通 Spectra、联发科 Imagiq 均在 RAW 域执行静态 DPM 校正 | 少数平台的动态热像素检测在 RGB 域补充执行 |

 > **工程推荐（手机 ISP 场景）：** 静态坏点图（DPM）校正放在 RAW 域（BLC 后、Demosaic 前），这是高通 Spectra 和联发科 Imagiq 的一致做法。对于无法预标定的动态热像素（高增益下随机出现的 RTS 像素），可以在 RGB 域追加一次轻量级动态检测作为兜底，但不要反过来——把所有 DPC 都推到 RGB 域，坏点扩散到 Demosaic 输出后就很难清干净了。

### 1.3 动态坏点校正（PDPC）进阶

#### 1.3.1 坏点类型速查（补充）

除 §1.2.1 已列出的五类缺陷外，实际量产中还需关注以下两类：

| 缺陷类型 | 物理原因 | 典型表现 |
|----------|---------|---------|
| **行/列缺陷（Row / Column Defect）** | 读出电路或列级放大器故障 | 整行或整列固定图案噪声，BLC 无法消除 |
| **冷像素（Cold Pixel / Dead Pixel）** | 感光层失效或光电二极管断路 | 任何光照下输出恒为零或黑电平值 |

> **量产规格参考：** 坏点数 / 总像素数 < 0.01% （出厂良品率标准）；校正后坏点密度目标 < 0.005% （见 §6.2 评测指标）。

#### 1.3.2 工厂静态坏点标定流程（速查）

```
1. 传感器在暗室中拍摄暗帧（曝光时间 = 最大值，ISO = 最高档）
2. 每个像素值超过阈值 μ + k·σ 判定为热像素（k 典型 3–5）
3. 坏点坐标写入传感器 OTP（一次性可编程存储）或 ISP 寄存器表
4. 良品率统计：坏点数 / 总像素数 < 0.01% 为合格品
```

**关键参数：**
- `DPC_StaticMap[N]`：坏点坐标列表，N 通常 < 2000
- `DPC_StaticThreshold`：热像素判定阈值倍数 $k$（典型 3–5）

#### 1.3.3 PDAF 坏点增益补偿（补充）

§1.2.2 已说明 PDAF 像素不能用标准 PDPC 插值替换。实际工程中，PDAF 专用校正模块的补偿公式为：

$$I_{\text{PDAF\_corrected}} = I_{\text{raw}} \times G_{\text{PDAF}} + \Delta_{\text{offset}}$$

$G_{\text{PDAF}}$ 和 $\Delta_{\text{offset}}$ 由工厂标定，典型值 $G_{\text{PDAF}} \approx 1.2$–$1.5$ ，具体取决于微透镜遮挡比例。

#### 1.3.4 各平台 PDPC 关键参数速查（补充）

| 平台 | 实现方式 | 关键参数 |
|------|---------|---------|
| **高通 Spectra** | BPS Node 硬件 BPC/BCC 模块，静态坏点表加载至 TuningManager；动态检测使用 FMax/FMin 阈值系数（来源：高通 camera tuning 实践文档） | BPC 静态坏点坐标表；动态检测 FMax/FMin 系数（具体 Chromatix 参数名以 BSP 版本为准） |
| **MTK Imagiq** | P1 Pipeline PDPC block，NDD（Noise Distribution Data）文件含静态坏点地图；动态阈值在 ImagiqSimulator 按增益段配置（来源：MTK ISP 调试流程文档） | `pdpc_map_file`（静态坏点表），动态增益段阈值（具体参数名以 BSP 版本为准） |
| **海思麒麟** | ISP 前端校正模块，静态缺陷坐标从 EEPROM 加载 | `hot_pixel_th`（热像素阈值）, `cold_pixel_th`（冷像素阈值）（参数名以实际 HiSilicon ISP SDK 文档为准） |

> 详细平台实现见 §2（平台实现）章节。

---

### 1.4 HDR 多路 BLC/PDPC

Staggered HDR（如双曝光 eSHDR）中，长曝光帧（LEF）和短曝光帧（SEF）经过独立的模拟读出路径，增益设置和暗电流积分时间都不同。两帧必须分别跑各自的 BLC 和 PDPC，然后再合并。

共用一个黑电平是这里最常见的集成错误。两帧增益不同，黑电平本来就不一样，合并后高光区域的色偏找 AWB 调不回来——因为 AWB 估算的是整帧的色温，不会按亮度段分别补偿这种系统性偏差。

---

## §2 平台实现（Platform Implementation）

### 2.1 Qualcomm Spectra ISP

高通 Spectra 系列 ISP（Spectra 480/580/680，对应骁龙 865/888/8 Gen 1 平台）将黑电平校正和缺陷校正分为多个独立硬件块：

- **OBC（Optical Black Correction）：** 实时读取 OB 区域，计算逐通道截断均值，生成 $B_c$；支持 per-row OB estimation 以补偿行级 FPN。参数：`black_level_lock`、`black_level_offset[4]`（四通道）
- **SDPC（Static Defect Pixel Correction）：** 从 EEPROM 加载出厂缺陷坐标表（各代 SoC 上限不同，典型为数百至数千条目，以对应 BSP 文档为准），硬件 LUT 查表，零流水线延迟
- **DDPC（Dynamic Defect Pixel Correction）：** 实时检测热/死像素；阈值寄存器对应高通 BPC/BCC 模块中的最大值阈值系数（FMax）和最小值阈值系数（FMin），用于判断像素是否超过邻域最大/最小值的倍数；支持方向自适应插值（参数名以实际 Chromatix 版本为准，来源：camera tuning 实践文档）

调试工具链：Qualcomm Snapdragon Profiler，以及 Chromatix 调参 XML（BPC/BCC 坏点校正模块对应的调参 XML，具体文件名随 Spectra 版本而异；`chromatix_bpcbcc_v20.xml` 为典型旧版命名，Chromatix 7+ 的参数结构与旧版有差异，应以实际 BSP 中文件名为准）。

### 2.2 MediaTek Imagiq ISP

联发科 Imagiq 5.0+（天玑 9000/9300 平台）ISP 流水线将黑电平校正分为两个阶段：

- **P1 路径（Pre-pipe，RAW 域）：** BLC 在 P1 路径完成，对 OB 区域实时计算逐通道均值，支持 row-wise 修正；MTK 调参通过 ImagiqSimulator 工具加载 tuning 参数文件，OB 相关参数在黑电平校正节配置（具体 JSON key 名因 BSP 版本而异，`AWB_OB` 节为部分版本参考命名，具体 key 名依 BSP 版本而异，以实际 ImagiqSimulator 文档为准）
- **P2 路径（Color path）：** PDPC 在 P2 早期执行，分两级：静态坐标查表 + 动态阈值检测；支持 PDAF 像素独立 bypass 路径
- 调参工具：MSDK（Mobile Solutions Development Kit）/ ImagiqSimulator，通过 ISP tuning table 配置 BLC 及 PDPC 参数（来源：MTK ISP 调试流程 CSDN 文章，2020）

### 2.3 HiSilicon Kirin ISP（海思麒麟）

- **2D 黑电平 Map：** Kirin 990/9000 ISP 支持二维黑电平补偿，即在行方向和列方向上均有独立的黑电平校正系数，适用于行/列 FPN 显著的大底传感器
- **缺陷校正：** 静态缺陷坐标从 EEPROM 加载，动态检测阈值在 ISP 调参工具中按增益段配置
- 对应接口：HAL3 `android.sensor.blackLevelPattern`（4 元素数组，对应 RGGB 四通道）

### 2.4 libcamera / Raspberry Pi PiSP

**架构说明：** libcamera 是开源相机框架，本身**不包含**通用软件 BLC 或 PDPC 实现。它定义了 IPA（Image Processing Algorithm）插件接口，具体算法由各平台的 IPA 模块提供。

对于 Raspberry Pi 系列，硬件 ISP 是 BCM2712 芯片上的 **PiSP（Pixel ISP）** 硬件块（Pi 5）或 Broadcom VC4 GPU 上的 ISP（Pi 4 及更早）。BLC 参数通过 JSON Tuning File 配置：

```json
// 文件：/usr/share/libcamera/ipa/rpi/vc4/imx477.json
// （Raspberry Pi HQ Camera，Sony IMX477 传感器）
{
    "rpi.black_level": {
        "black_level": 4096   // 12-bit sensor, black level = 256 DN in 12-bit (256×16=4096 stored in 16-bit scale)
    }
}
```

libcamera RPi IPA 的 `rpi.black_level` 模块在 `src/ipa/rpi/vc4/data/` 中定义，对应 C++ 实现位于 `src/ipa/rpi/controller/rpi/black_level.cpp`。该实现直接从 OB 行读取统计量，使用硬件 ISP 的 OB 统计块，无需软件逐行循环。

PDPC 对应 `rpi.alsc`（镜头阴影）和 `rpi.dpc` 模块，其中 `rpi.dpc` 通过 `strength` 参数控制动态坏点检测强度（0.0–1.0）：

```json
{
    "rpi.dpc": {
        "strength": 1.0
    }
}
```

> **picamera2 用户注意：** 通过 `Picamera2(tuning=load_tuning_file("imx477.json"))` 加载 tuning 文件时，对应的 BLC 和 PDPC 参数由 libcamera 硬件 IPA 驱动，并非软件 Python 代码执行；Python 层只是传递配置，实际处理在 GPU/硬件 ISP 上完成。

---

## §3 标定 (Calibration)

### 3.1 BLC 标定

**标定流程：**

1. 将传感器置于遮光容器中（镜头完全遮盖），排除所有杂散光
2. 按目标模拟增益档逐一标定（至少覆盖：$\times 1$、$\times 2$、$\times 4$、$\times 8$、$\times 16$、$\times 64$），每档拍摄 32–64 帧暗帧
3. 对每帧计算 OB 区域各通道截断均值，再对多帧取平均以抑制时域噪声
4. 如传感器支持 HCG/LCG 双转换增益，分别在 HCG 和 LCG 模式下标定，两组 LUT 独立存储
5. 如传感器支持多曝光 HDR，对 LEF / SEF 路径分别标定
6. 在各增益档之间拟合分段线性插值，支持非标准增益值的运行时查表

```python
# BLC LUT 最小结构示例（伪代码）
blc_lut = {
    # key: (analog_gain_idx, cg_mode)  cg_mode: 0=LCG, 1=HCG
    # value: [B_R, B_Gr, B_Gb, B_B]  单位: ADC LSB
    (0, 0): [256, 258, 257, 260],   # x1 gain, LCG
    (0, 1): [312, 315, 314, 318],   # x1 gain, HCG
    (1, 0): [264, 266, 265, 268],   # x2 gain, LCG
    # ...
}
```

**EMVA 1288 合规要求：** EMVA 1288 v4.0 标准（§3 Definitions，§4 Measurement conditions）**[1]** 要求分别报告平均暗信号（Mean Dark Signal）、暗信号时域噪声（Temporal Noise of Dark Signal）和暗信号空域非均匀性（DSNU）的标准差。

### 3.2 PDPC 标定

**热像素检测（暗帧法）：**

1. 遮光，将曝光时间设为各支持档位中最大值（最大化热像素信号）
2. 在每档模拟增益下采集 64 帧暗帧
3. 计算逐像素均值 $\bar{D}(i,j)$；若 $\bar{D}(i,j) > \bar{D}_\text{global} + \tau_\text{hot} \cdot \sigma_{D,\text{global}}$，标记为热像素
4. 重复以上步骤覆盖工作温度范围（如 25 °C / 60 °C），高温下出现的热像素单独标记

**死像素检测（平场法）：**

1. 使用积分球或漫射均匀光源，将曝光设为 70–90% 饱和度（EMVA 1288 要求 PRNU 标定在 70–90% 满阱范围内进行，避免低曝光时 SNR 不足导致漏检，也避免高于 90% 时非线性响应干扰检测）
2. 若像素响应低于 $\bar{F}_\text{global} - \tau_\text{dead} \cdot \sigma_{F,\text{global}}$，标记为死像素

**缺陷图格式：**

```python
defect_map = [
    {"row": 120, "col": 345, "type": "hot",   "gain_min": 1},   # 所有增益下存在
    {"row": 512, "col": 789, "type": "hot",   "gain_min": 16},  # 仅高增益出现（温度相关）
    {"row": 233, "col": 410, "type": "dead",  "gain_min": 1},
    {"row": 311, "col": 522, "type": "stuck", "gain_min": 1},
]
```

`gain_min` 字段记录该缺陷从哪个增益级别开始显著，低增益下不激活该条目，减少误判率。

> ⚠️ **增益段分层标定（关键工程要点）：** 坏点（热像素）在不同模拟增益档下的激活率存在显著差异——RTS（随机电报信号）噪声像素在高增益（高 ISO）下的热像素激活概率可比低增益提高 3–5 倍。因此，标准化 DPM 标定流程应**按每档模拟增益单独采集暗帧**：
>
> - 对每个增益档 $g_a \in \{1\times, 2\times, 4\times, 8\times, 16\times\}$ 独立执行热像素检测
> - 生成对应的坏点图 $\text{DPM}_{g_a}$，每张图可能包含不同的坏点集合
> - ISP 在运行时根据当前增益档加载对应的 DPM，而非单一静态坏点图
>
> 若只在低增益下标定 DPM，高 ISO 暗场下会遗漏大量动态热像素，导致噪点残留。

---

## §4 调参 (Tuning)

### 4.1 BLC 调参

**OB 实时估计 vs. 标定 LUT 的切换策略：**

实际工程中这两套机制不是非此即彼，而是分场景组合使用：

- 有 OB 区域且图像质量可靠（无漏光、无 PDAF 污染）：优先使用逐帧 OB 估计，标定 LUT 作为初始值
- 移动端短曝光（< 1/30 s）日常拍照：标定 LUT 通常足够，不必每帧重估；逐帧 OB 估计带来的收益小于额外的电路噪声开销
- 视频录制 / 夜景长曝光：必须使用逐帧 OB 估计以补偿温度漂移；否则视频前几分钟颜色随传感器升温缓慢漂移，很难事后发现
- 无 OB 区域的传感器方案：只能依赖标定 LUT，必须覆盖温度和曝光时间两个维度

**长曝光暗电流补偿：**

曝光时间 $T_\text{exp} > 1\ \text{s}$ 时，需用线性模型补偿暗电流累积：

$$B_c(T_\text{exp}) = B_{c,0} + J_c \cdot T_\text{exp}$$

$J_c$（每秒暗电流速率，单位 LSB/s）需在每档模拟增益和典型温度下单独标定。

### 4.2 PDPC 调参

**信号自适应阈值系数 $\tau$：**

| $\tau$ | 典型效果 |
|--------|----------|
| $< 2.0$ | 误检率高；平滑纹理被涂抹，可见锐度损失 |
| 2.5–3.5 | 通用调参起始点；需结合精确率/召回率权衡 |
| 4.0–5.0 | 保守；仅校正显著缺陷；适合低增益场景 |
| $> 6.0$ | 漏检中等热像素；高增益平场中可见白/黑点 |

调参方法：在已知真值缺陷图的平场和纹理图像上扫描 $\tau$ 从 1.5 到 6.0，绘制 Precision-Recall 曲线，选取 $F_1$ 最大点对应的 $\tau$。注意：$\tau$ 应按增益段分别调优（高增益时散粒噪声增大，需适当提高 $\tau$）。

**邻域半径选择：**

- $3 \times 3$（半径 1，Bayer 步距 2）：孤立单像素缺陷，硬件友好
- $5 \times 5$（半径 2）：卡死像素、闪烁像素
- $7 \times 7$（半径 3）：跨 2–3 像素的簇缺陷

---

## §5 伪影 (Artifacts)

### 5.1 BLC 校正不足（Undercorrection）

**症状：** 阴影区域呈乳白色雾气感，或出现彩色底噪（各通道 OB 值有差异时）。把图像拉到阴影区域放大，本该是纯黑的地方带着颜色。

**根本原因：**
- OB 区域受漏光污染，截断均值仍偏高
- 标定值在高温下已过时（暗电流增大但 LUT 未更新）
- 上截断比例 $\beta$ 设置不足，未充分排除热像素影响

**诊断：** 完整流水线拍摄暗帧，阴影区域均值应接近 0；正向残差超过 1 LSB 则表明校正不足。

### 5.2 BLC 过度校正（Overcorrection）

**症状：** 阴影细节丢失；本应为深灰的像素被截断至 0，阴影区域呈硬黑、无层次感。

**根本原因：**
- OB 均值估计偏高（例如 OB 行靠近有效区域边缘，受部分光照影响反而被下截断剔除）
- 标定 LUT 使用了过于保守（偏大）的黑电平值

**诊断：** 检查深灰卡图像直方图；若 0 附近的峰值超过预期泊松分布宽度，则为过度校正。

### 5.3 PDPC 误检（False Positives）

**症状：** 细腻纹理区域（发丝、布料）被涂抹平滑；散粒噪声在平场中被"校正掉"，导致 SNR 虚假提升。

**根本原因：** $\tau$ 过低；或使用固定阈值而非信号自适应阈值，在高亮区域（散粒噪声大）误检率显著升高。

**诊断：** PDPC 前后对比平场标准差；过校正会将方差压低到理论散粒噪声水平以下（$\sigma^2 < k \cdot \bar{I}$）。

### 5.4 PDPC 漏检（False Negatives）

**症状：** 平滑区域（天空、皮肤）中可见白点或黑点。

**根本原因：** $\tau$ 过高；或出厂缺陷图不完整（高温下新出现的热像素未录入）。

**诊断：** 拍摄暗帧和均匀平场，用已知真值缺陷图计算漏检率。

### 5.5 BLC 时序漂移（视频场景）

**症状：** 长视频录制中渐进色偏，传感器升温过程中最为明显（录制开始后约 3–8 分钟）。这类问题在实验室短测时几乎看不到，只有在真实拍摄场景中才会被用户发现。

**根本原因：** 暗电流随温度升高而增大，但 OB 估计未逐帧更新（或 OB 区域统计被禁用）。

**缓解：** 启用逐帧 OB 均值更新；或从片上温度传感器（通过 `android.sensor.temperature` 或平台私有接口读取）推算暗电流补偿量：

$$\hat{B}_c(T_\text{now}) = B_{c,\text{cal}} \cdot 2^{(T_\text{now} - T_\text{cal}) / \Delta T_2}$$

实际中 $\Delta T_2$ 需在标定时实测，不能直接套用文献中的"倍增温度"，因为它随像素工艺和设计而变化。

**$\Delta T_2$ 的工厂标定方法：**

$\Delta T_2$ 描述黑电平随温度的翻倍温度区间，其值与传感器工艺相关，**不能直接使用文献经验值**（文献值通常针对 65nm BSI 工艺，而现代 40nm/28nm 工艺传感器的 $\Delta T_2$ 可能相差 20–30%）。标定流程：

1. 将相机模组置于温控箱，在 25°C 和 60°C 各采集 ≥ 64 帧暗场（最长曝光时间）
2. 计算逐通道平均黑电平：$\text{BL}_c(25)$ 和 $\text{BL}_c(60)$
3. 反推 $\Delta T_2$：
   $$\Delta T_2 = \frac{60 - 25}{\log_2\!\left(\text{BL}_c(60) / \text{BL}_c(25)\right)} \approx \frac{35}{\log_2\!\left(\text{BL}_c(60) / \text{BL}_c(25)\right)}$$
4. 对四个通道（R/Gr/Gb/B）分别计算 $\Delta T_2$，写入 ISP 参数表
5. 验证：在 40°C 下拍摄暗场，将实测黑电平与 $\hat{B}_c(40)$ 预测值比较，误差应 < 2 DN

> 典型值参考：现代手机 CMOS（40nm BSI 工艺）$\Delta T_2 \approx 5–8°\text{C}$，即温度每升高 5–8°C 黑电平翻倍；比文献常引的 "$\Delta T_2 = 6°\text{C}$"（针对较旧工艺）偏高。

### 5.6 PDAF 像素被误当缺陷校正

**症状：** AF 像素位置出现规律性亮/暗点（Bayer 域可见），或相位差检测失效。

**根本原因：** PDPC 未区分 PDAF 坐标图与缺陷坐标图，将 PDAF 遮光像素识别为死像素并进行插值替换。

**预防：** 在 PDPC 模块的邻域计算中，排除所有 PDAF 像素坐标；PDAF 像素由专用模块处理（见 §1.2.2）。

---

## §6 评测 (Evaluation)

### 6.1 BLC 评测指标

**逐通道残余偏置（Residual DC bias）：**

BLC 之后，拍摄完整流水线暗帧，计算有效区域各通道均值残差：

$$\text{Residual}_c = \frac{1}{|P_{\text{active},c}|} \sum_{(i,j) \in P_{\text{active},c}} R'_c(i,j)$$

**目标：** $|\text{Residual}_c| < 0.5\ \text{LSB}$ ；四通道间最大差值 $< 1.0\ \text{LSB}$ 。

**通道平衡（Cross-channel balance）：** $\max_c \text{Residual}_c - \min_c \text{Residual}_c < 1.0\ \text{LSB}$。

### 6.2 PDPC 评测指标

使用标定真值缺陷图：

$$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}, \quad F_1 = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

**目标：** Recall > 99%，Precision > 95%，$F_1 > 0.97$。

动态检测在不同增益段（低增益 $\times 1$–$\times 4$、中增益 $\times 8$–$\times 16$、高增益 $\times 32$+）分别评测，高增益段通常需要独立调参。

### 6.3 端到端质量指标

- **灰卡 $\Delta E_{00}$：** BLC+PDPC 后拍摄 18% 灰卡，$\Delta E_{00} < 1.0$ （相对 D50 标准白的中性灰参考）
- **平场均匀性：** BLC 后对积分球均匀平场计算逐通道变异系数（CV = $\sigma/\mu$），目标 CV < 2% 
- **EMVA 1288 DSNU：** 暗信号空域非均匀性，$\text{DSNU}_{1288} < 0.5 \%$ 满阱电荷 **[1]**

---

## §7 代码

完整可运行代码见 `ch01_blc_pdpc_notebook.ipynb`，内容包括：

- 合成 512×512 RGGB RAW 图像，含逐通道黑电平偏移及嵌入的热/死像素
- BLC 校正：逐通道截断均值（含上/下截断参数）+ 步骤一（偏置减法）与步骤二（归一化）分离实现
- PDPC：信号自适应阈值动态检测 + 方向自适应插值校正
- PDAF 像素模拟与旁路处理示例
- 校正前后可视化及缺陷位置叠加显示
- 定量指标：逐通道残差偏置、缺陷检测 Precision/Recall/F₁

### 7.1 BLC + PDPC 最小可运行示例

```python
import numpy as np

# ─── 1. 合成 RGGB RAW（12-bit，含逐通道黑电平偏移）─────────────────────────
rng = np.random.default_rng(0)
H, W = 512, 512
raw = rng.integers(64, 4000, size=(H, W), dtype=np.uint16)

# 逐通道黑电平偏移（R/Gr/Gb/B）
blc_offset = {"R": 64, "Gr": 66, "Gb": 65, "B": 67}
raw[0::2, 0::2] += blc_offset["R"]   # R
raw[0::2, 1::2] += blc_offset["Gr"]  # Gr
raw[1::2, 0::2] += blc_offset["Gb"]  # Gb
raw[1::2, 1::2] += blc_offset["B"]   # B
raw = np.clip(raw, 0, 4095)

# 注入 20 个随机坏点
defect_rows = rng.integers(1, H - 1, 20)
defect_cols = rng.integers(1, W - 1, 20)
raw[defect_rows, defect_cols] = 4095  # 热像素（亮坏点）

# ─── 2. BLC：逐通道减去黑电平偏移 ────────────────────────────────────────────
def apply_blc(raw: np.ndarray, offsets: dict) -> np.ndarray:
    out = raw.astype(np.int32)
    out[0::2, 0::2] -= offsets["R"]
    out[0::2, 1::2] -= offsets["Gr"]
    out[1::2, 0::2] -= offsets["Gb"]
    out[1::2, 1::2] -= offsets["B"]
    return np.clip(out, 0, 4095).astype(np.uint16)

raw_blc = apply_blc(raw, blc_offset)

# ─── 3. PDPC：梯度阈值检测 + 方向加权插值校正 ─────────────────────────────────
def pdpc(raw: np.ndarray, threshold: float = 512.0) -> np.ndarray:
    """简化版动态坏点校正：检测孤立异常像素并用邻域插值替换。"""
    out = raw.copy().astype(np.float32)
    # 用 4 邻域均值计算期望值，超过阈值则替换
    neighbors = (
        np.roll(out, 1, axis=0) + np.roll(out, -1, axis=0) +
        np.roll(out, 1, axis=1) + np.roll(out, -1, axis=1)
    ) / 4.0
    diff = np.abs(out - neighbors)
    mask = diff > threshold
    out[mask] = neighbors[mask]
    return np.clip(out, 0, 4095).astype(np.uint16)

raw_corrected = pdpc(raw_blc)

# ─── 4. 验证：检查坏点位置残差 ────────────────────────────────────────────────
residuals = raw_corrected[defect_rows, defect_cols].astype(float)
print(f"坏点校正后均值残差: {residuals.mean():.1f} DN  (目标: < 50 DN)")
print(f"四通道 BLC 残差均值 (R/Gr/Gb/B):")
for ch, (r_sl, c_sl) in zip(
    ["R", "Gr", "Gb", "B"],
    [(slice(0,None,2), slice(0,None,2)), (slice(0,None,2), slice(1,None,2)),
     (slice(1,None,2), slice(0,None,2)), (slice(1,None,2), slice(1,None,2))]
):
    m = raw_blc[r_sl, c_sl].mean()
    print(f"  {ch}: {m:.2f} DN  (目标: < 0.5 LSB 偏差)")
```

---

> **工程师手记：黑电平和坏点，量产里的第一道坑**
>
> **BLC 的温度漂移比教科书写的更顽固。** 理论上 OB（Optical Black）区域的像素值就是当前温度下的暗电流基准，减去它就完成了黑电平校正。实际量产里，问题出在「OB 区域估计的时机」：每帧图像的 OB 行采集时温度已经比帧中间高了（传感器自加热），用帧尾 OB 减帧首曝光像素会有 0.5–1 档的欠校正，表现为暗场轻微偏灰（俗称"灰雾"）。处理方法是用前几帧的 OB 均值做 IIR 滤波（时间常数约 10–30 帧），或者在工厂标定时测量三个温度点（-5°C/25°C/50°C）建温度查表。高通 Spectra 的 BPS 有硬件 OB 统计单元，直接输出逐帧 OB 均值；MTK 则需要在 HAL 层用软件 IIR 补偿。
>
> **per-channel BLC 偏差是偏色最常见的"冤假错案"。** 调 CCM 调了很久颜色还是偏，往往根本原因是 R/Gr/Gb/B 四个通道的 OB offset 标定有偏差（尤其是 Gr 和 Gb 的 offset 不对称）。Gr-Gb 不平衡会在中性灰图像上造成奇偶行颜色交替的细纹，高分辨率下才看得出来，低分辨率 preview 里几乎察觉不到。工程 checklist：在开始 CCM 调参之前，先拍暗场图验证四通道 OB 均值是否与标定表一致，差异应在 ±1 DN（8-bit 域）以内。
>
> **坏点图的静态 vs 动态策略，不同厂商选择差异很大。** MTK 的工厂标定流程生成 NDD（Noise Distribution Data）文件，其中包含静态坏点地图；高通用 `.bin` 格式的静态 BPC map。两者都支持动态坏点检测（运行时梯度判断），但动态检测的阈值（`DPC_Threshold`）如果设太低，细纹理区域的边缘像素会被误判为坏点，导致软纹理被抹平——这是锐度下降但明明没调 NR 的典型场景。工程经验：动态 DPC 只用于捕捉出厂后新产生的「热像素」（高温下才出现的临时缺陷），对于稳定坏点，静态地图更可靠、代价更小。
>
> *参考：Janesick et al., "Scientific Charge-Coupled Devices", SPIE Press, 2007；EMVA Standard 1288（传感器标定标准）；观熵 CSDN《BLC 与 DPC 工程实践》，2024。*

---

## 工程推荐

BLC 是整条 ISP 流水线最上游的标定步骤——它错了，后面所有模块的色彩基础全都建立在偏移的坐标系上，CCM 调多准也救不回来。

| 场景 | 推荐方案 | 典型约束 | 备注 |
|------|---------|---------|------|
| 传感器 Bring-up（初次调试） | 先跑暗场四通道 OB 均值，验证 R/Gr/Gb/B 各自的黑电平值，再开 CCM | OB 偏差 < ±1 DN（8-bit 域） | BLC 不对就别调 CCM，调了也是白调 |
| 量产 OB 标定 | 每档模拟增益独立采集 ≥32 帧暗场，截断均值写入 LUT；HCG/LCG 分开标 | LUT 至少覆盖 ×1/×2/×4/×8/×16 五档 | 共用一张 LUT 跨增益，误差随增益放大，高 ISO 偏色明显 |
| 车载 / 户外长时工作 | 温控箱测 25°C / 60°C 两点，反推 ΔT₂，写温度补偿表；启用逐帧 OB IIR | 温漂误差目标 < 2 DN（60°C 下） | 移动手机短曝光可省，但车载/监控不能省 |
| 高 ISO 热像素（动态 DPC） | 静态 DPM 兜底 + 保守动态阈值（τ 4.0–5.0）；按增益段分档配置阈值 | 静态图 < 2000 坐标条目 / 传感器 | τ 过低会把细纹理误判为坏点，锐度下降但 NR 没动 |
| HDR 双曝合并（LEF/SEF） | LEF 和 SEF 各用独立 BLC LUT；PDPC 也分路处理后再合并 | 两帧增益差通常 4–16 倍 | 共用黑电平是 HDR 场景最常见的集成错误 |

**调试要点：**

- **暗场均匀性验证（BLC 正确性快速判断）**：BLC 完成后拍满幅暗场，对有效区域逐通道计算均值残差，目标 |Residual_c| < 0.5 LSB，四通道最大差值 < 1.0 LSB。若某通道残差系统性偏正（偏灰），先查 OB 区域是否漏光或截断参数 β 设置不足；偏负（过校正）则检查标定 LUT 是否用了偏大的参考值。这一步应在每次传感器换型或 OTP 更新后必跑。

- **DPC 阈值分增益段标定**：动态 PDPC 阈值 τ 不能全局一个值——低增益散粒噪声小，τ 可以低（2.5–3.5）；高增益散粒噪声增大，τ 必须提高（4.0–5.0），否则纹理区像素被大量误判为热像素。标定方法：在 ×1/×8/×32 三档分别扫 τ 1.5→6.0，用已知真值缺陷图绘制 Precision-Recall 曲线，选各档 F₁ 最大点。平台参数对照：高通 BPS 的 BPC/BCC 模块中对应 FMax/FMin 系数，MTK ImagiqSimulator 按增益段配置动态阈值。

- **多温度 BLC 表生成**：建议在 -5°C / 25°C / 50°C 三点采集暗场，拟合每通道的暗电流斜率 J_c（单位 LSB/s），写入温度-增益二维 LUT。运行时用片上温度传感器（`android.sensor.temperature` 或平台私有接口）插值查表，补偿视频录制前几分钟传感器自加热造成的渐进色偏。注意：ΔT₂ 必须实测，40nm BSI 工艺与文献 65nm 数据偏差可达 20–30%，不能直接套用。

**何时不值得做精细 BLC 标定：** 短曝光（< 1/30 s）的移动端日常拍照场景，暗电流对黑电平的贡献通常小于放大器固定偏移；此时用出厂标定 LUT + 逐帧 OB 均值即可，不必建温度查表。精细温度补偿表的投入主要值得在以下场景：视频录制（连续工作 > 5 分钟）、曝光时间 > 1 s 的夜景长曝、以及工作温度跨度 > 30°C 的车载/户外相机。

---

## 插图

![blc temperature drift](img/fig_blc_temperature_drift_ch.png)
*图1. 黑电平随温度漂移示意图——暗电流随温度的指数增长关系与 OB 区域估计（图片来源：Janesick et al., SPIE Press, 2007）*

![dark current model](img/fig_dark_current_model_ch.png)
*图2. 暗电流模型——像素暗电流与曝光时间的线性关系及泊松分布（图片来源：EMVA, EMVA Standard 1288, 2021）*

![pdpc detection threshold](img/fig_pdpc_detection_threshold_ch.png)
*图3. PDPC 信号自适应检测阈值示意图——固定阈值与信号自适应阈值在不同信号强度下的对比（图片来源：Nakamura et al., CRC Press, 2006）*

![blc dark current](img/fig1_1_blc_dark_current.png)
*图4. BLC 暗电流特性——左：暗电流随温度指数增长（倍增温度 7°C）；右：暗场直方图显示 OB 分布和热像素分布（图片来源：作者，ISP手册，2024）*

![ob layout](img/fig1_2_ob_layout.png)
*图5. 光学黑（OB）像素在 Bayer RAW 布局中的位置示意——OB 行位于传感器边缘，物理遮光保证无光照输出等于真实黑电平（图片来源：作者，ISP手册，2024）*

![blc histogram](img/blc_histogram.png)
*图6. BLC 前后直方图对比——黑电平校正将 RAW 直方图整体左移对齐零点，消除通道间黑电平偏差，展示校正前后四通道（R/Gr/Gb/B）直方图分布变化（图片来源：作者自绘）*

![blc pdpc result](img/blc_pdpc_result.png)
*图7. BLC/PDPC 处理结果对比——黑电平校正与坏点校正联合处理前后的 RAW 图像对比，展示热像素消除和暗场均匀性改善效果（图片来源：作者自绘）*

---

## 习题

**练习 1（理解）**
传感器存在光学黑区域（OB）和标定黑电平 LUT 两种黑电平来源。请说明二者的适用场景及优先级：在哪些条件下应优先使用逐帧 OB 均值而非出厂标定值？温度升高 14 °C 时，若暗电流倍增温度 ΔT₂ = 7 °C，黑电平理论上会变化多少倍？请结合 EMVA 1288 中 DSNU 的定义分析 FPN 对逐通道 OB 均值的干扰。

**练习 2（计算）**
某 12 位 CMOS 传感器的四通道标定黑电平为 R = 256 DN、Gr = 260 DN、Gb = 258 DN、B = 254 DN。一帧图像中 R 通道某像素的 RAW 值为 1024 DN，Gr 通道某像素为 512 DN。

1. 分别计算两个像素经 BLC 后的线性化值（直接相减，结果不截断到负数）。
2. 若 Gr 通道 OB 区域在当前温度下实测均值为 272 DN（较标定值偏高 12 DN），更新后的 BLC 结果是多少？
3. 在 10 位等效分辨率下（右移 2 位），4 LSB 的逐通道 OB 误差对 ISO 3200 高增益图像的亮度偏差百分比大约是多少（假设满幅值 1023 DN）？

**练习 3（编程）**
实现一个静态坏点掩码的生成与修复流程：

- 输入：暗场 RAW 图像（16 位灰度，形状 `(H, W)`），黑电平 `ob = 256`，热像素检测阈值 `hot_thresh = 600`，死像素检测阈值 `dead_thresh = 20`
- 输出：坏点掩码 `defect_mask`（布尔型，`True` 表示缺陷像素）和修复后图像 `corrected`
- 修复方式：对每个缺陷像素，用其同色通道（Bayer RGGB 分布中与其颜色相同的）最近四邻域均值替换
- 要求：不使用循环遍历每个像素（允许使用 `scipy.ndimage` 或向量化操作）；输出坏点总数

```python
import numpy as np
# 输入: raw_dark (H, W) uint16, ob=256, hot_thresh=600, dead_thresh=20
# 输出: defect_mask (H, W) bool, corrected (H, W) uint16
```

**练习 4（工程分析）**
在高通 Spectra ISP 平台上，BLC 相关寄存器包含 `BLS_OB_Level_R/Gr/Gb/B`（标定黑电平）和 `BLS_OB_Enable`（是否启用在线 OB 估计）；MTK ISP 对应参数为 `OB_offset_R/Gr/Gb/B`。某工程师在标定后发现 Raw 图像暗部出现淡红色偏（其余通道正常），同时 OB 在线估计已关闭（`BLS_OB_Enable = 0`）。请分析最可能的根因（不少于 2 条），并说明如何通过调整 `BLS_OB_Level_R` 和 `BLS_OB_Level_Gr` 的差值来量化和修正该色偏；最后说明在 HDR 双曝光（LEF/SEF）场景下，为何两路曝光必须各自独立设置 OB_offset。

---

## 参考文献

[1] EMVA, "EMVA Standard 1288 Release 4.0 — Standard for Characterization of Image Sensors and Cameras", *官方文档*, 2021. URL: https://www.emva.org/standards-technology/emva-1288/

[2] Janesick, "Scientific Charge-Coupled Devices", *SPIE Press*, 2001.

[3] Janesick, "Photon Transfer: DN → λ", *SPIE Press*, 2007.

[4] Nakamura (Ed.), "Image Sensors and Signal Processing for Digital Still Cameras", *CRC Press*, 2006.

[5] Holst et al., "CMOS/CCD Sensors and Camera Systems (2nd ed.)", *SPIE Press / JCD Publishing*, 2011.

[6] Farrell et al., "Digital camera simulation", *Applied Optics*, 2012.

[7] Liu et al., "Noise estimation from a single image", *CVPR*, 2006.

[8] Karaimer et al., "A software platform for manipulating the camera imaging pipeline", *ECCV*, 2016.

## §8 术语表（Glossary）

**黑电平（Black Level）/ 光学黑电平（Optical Black Level）**
入射光子数为零时，图像传感器像素 ADC 输出的非零偏置值，由暗电流、固定图案偏移（FPN）和 ADC 基座三者叠加构成。黑电平是 ISP 流水线最前端必须去除的直流偏置，不去除将导致所有下游处理（AWB、CCM、Gamma）在错误的线性基点上工作，最终表现为阴影底噪抬高或色偏。

**暗电流（Dark Current）**
即使无光照，CMOS 像素耗尽层中热激发产生的自由电子积累，遵循 Arrhenius 关系。硅 CMOS 暗电流倍增温度 ΔT₂ 典型为 6–8 °C，即传感器每升温约 7 °C，暗电流约翻倍。长曝光（> 1 s）和视频录制场景中，暗电流随温度的漂移是黑电平误差的主要来源，需通过逐帧 OB 估计或温度模型补偿。

**固定图案噪声偏移（Fixed-Pattern Noise Offset, FPN）**
列级与像素级差分放大器存在的非零输入参考偏移，帧间高度可重复，在图像空间上表现为列纹或块状图案，与曝光时间无关。FPN 是黑电平的稳定加性成分，可通过标定 LUT 在 BLC 中一并消除。

**ADC 基座（ADC Pedestal）**
传感器设计中故意叠加在 ADC 输出上的数字偏置，目的是防止模拟噪声将信号拉入负值后导致整数编码溢出（underflow）。典型范围因架构而异：10 位系统约 32–128 LSB，12 位系统约 128–512 LSB；过大的基座会压缩有效动态范围。

**光学黑区域（Optical Black Region, OB）**
传感器边缘的物理遮光像素带，像素上方覆盖金属遮光层，无法接收光线，其输出等于当前帧真实黑电平的采样。OB 区域用于逐帧、实时估计随温度和增益变化的黑电平，是最准确的在线黑电平来源，优先级高于标定 LUT。

**截断均值（Trimmed Mean）**
剔除样本分布两端极端值后的均值估计方法：排除最低 α% 和最高 β% 分位的像素后，对剩余样本取均值。在 OB 黑电平估计中，当暗场分布呈高端长尾（热像素、漏光污染）时，取 β > α（如 β=10%，α=5%）可增强对高端异常像素的抑制。具体参数需结合暗场直方图实测标定。

**BLC 误差传播（BLC Error Propagation）**
黑电平残余误差 ε_c（使用值与真值之差）以加性偏置形式向 ISP 下游传播：影响 AWB（通道间 ε 差异导致光源色温偏移）、CCM（偏离线性工作点导致色差 ΔE 升高）、Gamma/色调映射（黑点漂移）。10 位系统中 4 LSB 的逐通道 OB 误差在 ISO 3200 下即可产生可见色偏。

**像素缺陷（Pixel Defect）**
由制造工艺缺陷、热应力或辐射损伤导致的像素响应异常。分为**静态缺陷**（出厂测试中稳定检出，存储于 OTP/NVM）和**动态缺陷**（仅在特定温度、增益或曝光条件下出现，需运行时检测）。主要类型包括热像素（暗场接近饱和）、死像素（始终偏暗）、卡死像素（固定中间值）、闪烁像素（帧间交替异常）和簇缺陷（≥2 相邻缺陷）。

**热像素（Hot Pixel）**
无论曝光条件如何，始终输出异常高信号（暗场接近饱和）的缺陷像素，成因是像素内部晶体缺陷导致泄漏电流过大，暗电流极高。热像素在高温和长曝光下尤为明显，部分仅在特定温度/增益组合下出现（温度相关热像素）。识别方法：暗场下统计逐像素均值，异常高频/高值像素即为热像素。

**PDAF 像素（Phase Detection Autofocus Pixel）**
通过遮挡部分微透镜开口实现相位差测量的自动对焦像素，在 RAW 图像中表现为规律性的暗点，位置固定且可预测。PDAF 像素不是缺陷，**不能**用 PDPC 插值替换（否则破坏相位差信息），须由专用 PDAF 校正模块独立处理，在 BLC 之后、PDPC 之前完成。

**信号自适应检测阈值（Signal-Adaptive Detection Threshold）**
动态 PDPC 中根据局部信号强度调整的缺陷检测阈值：$T(i,j) = \tau \cdot \sqrt{\sigma_r^2 + k_\text{gain} \cdot \hat{I}(i,j)}$，包含固定读出噪声项和随信号增大的散粒噪声项。相比固定阈值，信号自适应阈值可避免在高亮区域（散粒噪声大）过度误检和在暗区（读出噪声主导）漏检，是工程实现的推荐做法。

**方向自适应插值（Direction-Adaptive Interpolation）**
PDPC 中用于替换缺陷像素的算法：在水平、垂直、两条对角线方向上分别估计邻域均值，权重与对应方向梯度的倒数成正比（梯度越小方向越平坦则权重越大）。相比简单均值或中值替换，方向自适应插值在边缘区域能避免引入方向性模糊伪影，保留图像锐度。

**EMVA 1288**
欧洲机器视觉协会（EMVA）发布的图像传感器和相机表征标准，规范了暗信号（Dark Signal）、DSNU（暗信号空域非均匀性）、PRNU（光响应非均匀性）、SNR 等关键图像质量参数的测量方法和报告格式。PDPC 标定中的热/死像素检测流程应符合 EMVA 1288 的测量条件要求（§4 Measurement conditions）。

**HDR 多路 BLC（Multi-Exposure BLC for HDR）**
在 Staggered HDR（双曝光 eSHDR）中，长曝光帧（LEF）和短曝光帧（SEF）经过独立读出路径，具有不同的增益和暗电流积分时间，必须对每条曝光路径独立执行 BLC，才能保证 HDR 合并的线性度。共用黑电平是常见错误，会在合并后高光区域引入无法在 AWB 后消除的色偏。
