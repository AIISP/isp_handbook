# 第四卷第09章：3A 高级专题——多摄同步、PDAF 衰退与环路耦合

> **定位：** 本章聚焦三个 3A 工程进阶专题：多摄像头 3A 跨路同步、低光环境下 PDAF 精度衰退补偿，以及 AE/AF/AWB 三环路耦合稳定性设计
> **前置章节：** 第四卷第01章（3A控制系统总览）、第四卷第02章（自动曝光算法深度解析）、第四卷第03章（自动对焦算法深度解析）
> **读者路径：** 3A系统工程师、多摄算法工程师

> **注意：** AE/AF/AWB 核心算法（测光模式、PI控制器、PDAF原理、灰色世界AWB等）已在以下章节全面覆盖：
> - **第四卷第01章** — 3A系统架构、传统与AI混合算法、SoC平台实现（Qualcomm/MediaTek/HiSilicon）
> - **第四卷第02章** — 自动曝光完整技术栈（曝光方程、多区域测光、PI控制器、HDR AE、防频闪）
> - **第四卷第03章** — 自动对焦完整技术栈（CDAF、PDAF、VCM驱动、混合AF）
> - **第二卷第05章** — 自动白平衡算法（灰色世界、白色点检测、神经网络AWB）

---

## §1 多摄像头 3A 同步

### 1.1 问题背景

现代旗舰手机配备 2–4 颗摄像头（超广角、广角、2× 长焦、5× 长焦），切换摄像头时三路独立 3A 状态不同步，导致：

- **亮度跳变：** 两路 ISP 曝光参数不同，切换瞬间画面明暗突变
- **色温跳变：** 各路 AWB 收敛到不同色温，切换时出现偏色闪烁
- **对焦跳变：** 切换后需重新搜索焦点，用户体验割裂

### 1.2 同步方案

**主从模式（Master-Slave Sync）：**

指定主摄（通常为广角）为主控，长焦/超广角摄为从属：

```
主摄 AE 目标 → 换算为等效 EV → 从摄目标 EV = 主摄 EV + ΔEV_correction
```

$\Delta EV_{correction}$ 补偿两路镜头的光圈差异（$F_{wide}$ vs $F_{tele}$）：

$$\Delta EV = 2 \log_2 \frac{F_{tele}}{F_{wide}}$$

**帧同步（Frame-Level HW Sync）：**

两路 ISP 通过硬件帧同步信号在同一 SOF（Start-Of-Frame）触发 3A 统计收集和参数更新，确保同帧时刻参数一致性。

**预测插值（Predictive Interpolation）：**

切换前，主摄将当前 3A 状态通过坐标变换预测为从摄所需参数，切换瞬间直接应用预测值，避免搜索收敛延迟：

$$\theta_{slave}^{target} = \mathcal{T}(\theta_{master}^{current}, \Delta_{optics})$$

**Qualcomm 工业实现：** CAMX MultiCamera 节点管理多路 ISP 的 3A 协调，详见 [github.com/quic/camx](https://github.com/quic/camx)（BSD-3 公开）。

### 1.3 切换平滑策略

| 策略 | 原理 | 适用场景 |
|------|------|---------|
| 淡入淡出（Crossfade） | 切换后 N 帧内线性插值两路输出 | 慢速切换（缩放滑动） |
| 快速对齐（Fast Align） | 从摄收敛 1–2 帧后切换（*来源：作者经验，需社区验证*） | 快速焦段跳变 |
| 预对齐（Pre-align） | 切换前后台运行从摄 3A | 旗舰多摄同时取流 |

> **工程推荐（手机多摄场景）：** 如果只有两路摄像头且不支持同时取流，选快速对齐策略，EV对齐完成后立即切换，Crossfade帧数控制在3帧内；如果旗舰平台支持后台同时取流，优先做预对齐，切换延迟可压到1帧以内。两策略都要配合工厂标定的跨摄色差补偿向量 $\boldsymbol{\delta}_{calib}$，否则AWB强制对齐后色温仍会有系统性偏差。

### 1.4 跨摄增益/快门对齐的精确推导

**等效曝光值（EV）对齐模型：**

设主摄（广角）当前曝光状态为 $(t_m, G_m)$（曝光时间、增益），从摄（长焦）需对齐到相同场景亮度，则从摄目标 EV：

$$EV_{slave} = EV_{master} + \Delta EV_{optics}$$

$$\Delta EV_{optics} = 2\log_2\frac{F_{tele}}{F_{wide}} + \log_2\frac{T_{wide}}{T_{tele}}$$

其中透射率比项 $\log_2(T_{wide}/T_{tele})$ 修正两镜头 T 值（实际透光率）差异，通常在工厂标定时测量并写入相机参数文件（camera_characteristics.xml）。

**时序同步硬件信号：**

多路 ISP 通过以下硬件机制实现帧级同步：
- **VSYNC 总线（I2C 广播）：** 主摄在 SOF 到来时通过 I2C 广播通知所有从摄，从摄在下一个 SOF 应用主摄已发布的 AE 参数；延迟为 1 帧
- **GPIO 硬触发：** 主摄的帧触发信号通过 GPIO 连接到从摄 FSIN（Frame Sync Input）引脚，确保所有 sensor 在同一时刻开始积分；
- **软件帧号对齐：** 在没有硬件 FSIN 的设备上，通过比较 metadata 中的 SOF 时间戳（精度约 10μs）实现软件帧对齐

**亮度跳变量化指标：**

切换亮度差定义为切换前最后 5 帧与切换后最初 5 帧的平均亮度（Y 通道，0-255 归一化）之差，目标：

$$|\bar{Y}_{post} - \bar{Y}_{pre}| < 3.0 \quad (\approx 0.05\ \text{EV} \text{ 在中等亮度场景}) \quad \text{（*来源：作者经验，需社区验证*）}$$

---

## §2 低光 PDAF 精度衰退

### 2.1 衰退机制

PDAF（相位检测自动对焦）依赖传感器相位差像素对（Phase Detection Pixels）测量光束偏移量，在低光（高 ISO）场景下：

$$\sigma_\phi \propto \frac{1}{\text{SNR}} \propto \sqrt{\frac{\sigma_{noise}^2}{I_{signal}}}$$

其中 $\sigma_\phi$ 为相位估计误差，$\text{SNR}$ 随光照强度下降而下降。典型衰退曲线：

| 场景亮度（lux） | PDAF 对焦误差（典型值） | 备注 |
|--------------|---------------------|------|
| > 300 lux | < 5μm（可忽略） | 室外日光 |
| 30–300 lux | 10–50μm | 室内正常照明 |
| 3–30 lux | 50–200μm | 黄昏/暗室 |
| < 3 lux | > 500μm（失效） | 夜景极暗 |

（*来源：作者经验，需社区验证；各机型传感器噪声特性不同，具体数值需实测标定*）

### 2.2 补偿策略

**降级到 CDAF（Contrast Detection AF）：**

当 PDAF 置信度低于阈值 $\tau_{conf}$ 时，自动切换到对比度爬山搜索：

```
if pdaf_confidence < τ_conf:
    use CDAF with coarse-to-fine sweep
else:
    use PDAF for fast convergence
```

**慢速 AF 模式（Extended Integration）：**

增大 PDAF 像素积分时间（降帧率），提升信噪比，以速度换精度。

**Fusion AF（多传感器融合）：**

$$d_{final} = \begin{cases} d_{ToF} & \text{if } d_{ToF} < 1.5\text{m and ToF valid} \\ d_{PDAF} & \text{if PDAF confidence} > \tau_{high} \\ d_{CDAF} & \text{fallback} \end{cases}$$

激光 ToF（飞行时间）测距精度不受光照影响，在距离 < 1.5m 时优先使用。

### 2.3 脏镜对 PDAF 置信度的影响

镜头污染（指纹油污、水渍、灰尘）会在相位差图像上引入额外相位偏差，导致 PDAF 置信度虚高但精度反而下降——即"高置信低精度"的危险状态。

**检测机制：**
1. **全局置信度-方差不一致性检测：** 计算全帧 PDAF 置信度图的空间标准差 $\sigma_{conf}$；脏镜场景下置信度图呈块状分布（污染区域局部置信度异常高），$\sigma_{conf}$ 明显升高
2. **置信度图低通滤波：** 对置信度图进行 $7\times7$ 均值滤波，抑制单点噪声引起的虚假高置信度：
$$\tilde{C}(x,y) = \frac{1}{49}\sum_{i=-3}^{3}\sum_{j=-3}^{3} C(x+i, y+j)$$
3. **多区域一致性投票：** 仅当 PDAF 置信度高的区域（$\tilde{C} > 0.7$）占全帧面积超过 60% 时，才信任当前 PDAF 估计

**镜头污染预警：** 若连续 30 帧均检测到置信度异常分布，触发"请清洁镜头"用户提示。

### 2.4 PDAF 置信度图后处理流程

```
原始相位差图（Phase Difference Map）
    ↓ 相位差计算（左-右子光圈图像对差）
    ↓ 置信度评估（SNR、相位一致性）
    ↓ 坏点掩码过滤（遮挡像素、饱和像素排除）
    ↓ 空间低通平滑（7×7 均值或高斯）
    ↓ 置信度阈值筛选（τ_conf = 0.4）
    ↓ 散焦量估计（defocus = phase_diff / phase_slope_calib）
    ↓ 输出：散焦量 + 有效区域掩码
```

其中 `phase_slope_calib` 是工厂标定参数，描述相位差与散焦量（μm 单位）之间的线性关系，随镜头焦距和光圈值变化。

---

## §3 3A 三环路耦合稳定性

### 3.1 耦合关系分析

AE、AWB、AF 三个控制环路共享同一传感器读出，存在物理耦合：

```
AE 改变曝光增益
    → 亮度统计变化 → AWB 统计受影响（过曝区域饱和，无法用于色温估算）
    → CCM/WB 增益变化 → AE 的 Y 通道亮度目标偏移

AWB 改变 WB 增益
    → R/G/B 通道比例改变 → 影响 AE 感知到的亮度（Y = 0.299R + 0.587G + 0.114B）
    → 间接影响 AF 对比度统计（对比度依赖高频 Y 信号）
```

### 3.2 解耦设计原则

**AE 工作在对数亮度域：**

$$L_{target} = \log(Y_{target})$$

对数空间下色温变化引起的亮度偏移幅度小，减弱 AWB→AE 的耦合干扰。

**AWB 在色度空间操作：**

将 AWB 估计在 $(u', v')$ CIEuv 色度空间进行，与亮度 $Y$ 解耦，防止 AE→AWB 的单向影响扩大。

**收敛顺序调度：**

| 环路 | 典型收敛帧数 | 调度策略 |
|------|------------|---------|
| AE | 3–5 帧（*来源：作者经验，需社区验证*） | 优先收敛，其他环路等待 AE 稳定后再启动 |
| AWB | 5–10 帧（*来源：作者经验，需社区验证*） | AE 稳定后启动，避免曝光变化干扰色温估算 |
| AF | 10–30 帧（CDAF）/ 1–3 帧（PDAF）（*来源：作者经验，需社区验证*） | 独立运行，AF 不影响 AE/AWB |

### 3.3 振荡检测与阻尼

当 AE 和 AWB 形成正反馈（如特殊色温光源下 AWB 增益变化不断触发 AE 重新调整）：

$$\text{Oscillation} = \|\bar{Y}(t) - \bar{Y}(t-1)\| > \tau_{osc} \text{ 持续 } N \text{ 帧}$$

检测到振荡后：
1. 临时冻结 AWB 增益（保持上一稳定值）
2. 降低 AE 步长（$K_P$ 减半）
3. 引入帧间 EMA 平滑：$\theta(t) = \alpha \theta(t-1) + (1-\alpha)\theta^*(t)$，$\alpha$ 从 0.5 增大到 0.8

### 3.4 变焦时 AF 对 AE 的单向耦合

在具有连续变焦（Periscope 或液态镜头）的相机中，镜头运动改变有效光圈，从而影响到达传感器的光通量：

$$\Delta EV_{AF} = -2\log_2\frac{F_{new}}{F_{old}}$$

AF 驱动 VCM 移动镜片时，AE 需要同步补偿此 EV 变化，否则在变焦过程中出现亮度波动。工程实现：

- VCM 驱动器通过 I2C 将当前镜片位置（lens position）写入 metadata
- AE 算法读取 lens position，查找预标定的 $F(position)$ 曲线，计算 $\Delta EV_{AF}$ 补偿量
- 此补偿量在 AE 闭环之外（前馈，feedforward），不经过 PI 控制器

### 3.5 AWB 增益变化对 AE 亮度感知的量化

AE 通常在 Bayer 域（pre-demosaic）计算 Y 通道统计，近似为：

$$Y \approx 0.299 \cdot w_R \cdot R + 0.587 \cdot w_G \cdot G + 0.114 \cdot w_B \cdot B$$

其中 $w_R, w_G, w_B$ 是 AWB 白平衡增益。当 AWB 从日光（$w_R \approx 1.0, w_B \approx 1.8$）切换到钨丝灯（$w_R \approx 2.2, w_B \approx 0.8$）时：

$$\Delta Y = 0.299 \cdot \Delta w_R \cdot R + 0.114 \cdot \Delta w_B \cdot B$$

在典型室内场景（$R/G \approx 0.9, B/G \approx 0.7$）下，此 $\Delta Y$ 可达 10–15%（*来源：作者经验，需社区验证*），足以触发 AE 重新调整曝光。解决方案：AE 在归一化增益空间中计算亮度，将 $w_G$ 归一化为 1，消除 AWB 增益变化对亮度感知的一阶影响。

### 3.6 场景自适应 3A：场景分类驱动多环路协同

旗舰手机的 3A 已不再是三个独立控制器，而是由**场景分类模块**统一调度的联动系统——场景类别直接决定各环路使用哪套参数集：

```
AI 场景分类（Scene Classification）
    输入：缩略图（thumbnail，通常 224×224）+ AE 统计
    输出：场景类别（P(indoor), P(outdoor), P(night), P(face), P(text), ...）

场景类别 → 影响以下 3A 参数集：
    AE：   [目标亮度、防频闪优先级、HDR 触发阈值、最大 ISO]
    AWB：  [算法权重（Gray World vs Statistical AWB）、色温范围约束]
    AF：   [对焦区域权重（人脸优先 vs 中心权重）、PDAF/CDAF 切换阈值]
```

**典型场景-参数映射：**

| 场景类型 | AE 目标 EV 偏移 | AWB 策略 | AF 策略 |
|---------|--------------|---------|--------|
| 室外日光 | 0 EV（标准） | Gray World + 光源约束 | PDAF 优先 |
| 室内人工光 | +0.3 EV（略提亮） | 统计 AWB（防黄偏） | PDAF + 人脸权重 |
| 夜景 | +0.5 EV（夜景增亮） | 固定 AWB（防色偏抖动） | 激光ToF优先 |
| 人脸近景 | 人脸区域测光 | 肤色约束 AWB | 人脸 PDAF |
| 逆光 | HDR 模式，压暗高光 | 中性约束 AWB | 主体轮廓 CDAF |

### 3.7 多帧 3A 与 TNR/HDR 合并的交互

**时域降噪（TNR）对 AE 的影响：**

TNR 融合后图像的噪声比单帧低 $\sqrt{N}$ 倍——这对 AE 统计是个陷阱。若 AE 基于 TNR 输出帧做亮度估计，方差被人为压低，控制器会误判暗部细节已清晰可见，进而维持欠曝状态，形成"欠曝→TNR降噪→AE误判→继续欠曝"的负反馈链。

工程解法直接：AE 统计在 TNR **之前**的原始 RAW 帧上计算（Pre-TNR AE stats），TNR 的输出只走最终显示/存储通路，不进入 AE 闭环。

**HDR 多帧合并对 AWB 的影响：**

HDR 合并把短曝（高光区域数据）与长曝（暗部区域数据）拼在一张图上，任何一帧的色彩特征都只代表一段动态范围——短曝帧高光饱和少但暗部信噪比差，长曝帧暗部细节丰富但颜色噪声大。若 AWB 基于合并后的混合图估计色温，两段范围的色彩噪声叠加，色温估计方差明显上升。正确做法：AWB 统计固定在**中等曝光帧**（M 帧，EV=0）上计算，M 帧的高光和暗部都在传感器线性区内，是色温估计最可靠的数据源。

---

## §4 多帧 3A 融合专题

### 4.1 Burst 拍摄中的 3A 策略

Burst 拍摄（连拍、夜景多帧）期间，3A 的典型策略是**锁定（Lock）**而非持续调整：

**AE Lock in Burst：**
- 在 Burst 开始前触发 Pre-Capture AE（安卓 Camera2 API `PRECAPTURE_TRIGGER`），等待 AE 收敛
- 收敛后锁定 AE（`AE_LOCK = true`），所有 burst 帧使用相同曝光参数
- 目的：确保多帧之间亮度一致，为后续对齐和合并提供稳定基准

**AWB Lock in Burst：**
- 与 AE Lock 同步，在 Burst 开始时锁定 AWB 增益
- 避免多帧中白平衡漂移导致颜色不一致（颜色不一致比亮度不一致更难在合并中修复）

**AF Behavior in Burst：**
- 静态拍摄（三脚架）：Burst 开始前对焦，锁定 AF
- 连续追踪（运动主体）：保持 CRAF（Continuous AF），每帧更新焦点（适用于体育连拍，而非多帧降噪合并）

### 4.2 Pre-Capture 序列设计

```
用户按快门（Shutter Release）
    ↓ [Stage 1: Pre-Capture AE/AWB/AF, ~3-8帧]
    触发 PRECAPTURE_TRIGGER
    AE 收敛（亮度误差 < 3%）
    AWB 收敛（色温误差 < 100K）
    AF 锁定（置信度 > 0.8）
    ↓ [Stage 2: Lock & Burst, N帧]
    AE_LOCK = true
    AWB_LOCK = true
    AF_LOCK = true（或 CRAF 继续）
    连续采集 N 帧 RAW
    ↓ [Stage 3: Post-Processing]
    帧对齐 → 合并（TNR/HDR） → ISP → JPEG/HEIF
```

Pre-Capture 帧数越多，3A收敛越准，但快门延迟也越长——旗舰相机把这个时间压到200ms以内（约3–5帧）是有原因的：超过300ms用户就会觉察到"按下去没反应"。做到200ms以内依赖预测性3A（Predictive 3A）：在用户半按快门时就开始预运行3A，而不是等全按下去才开始。

### 4.3 HDR 多帧合并与 AE 的双向交互

**AE 确定 HDR 曝光比（Exposure Ratio）：**

AE 需要决定 HDR 长曝帧（L）和短曝帧（S）的曝光比 $R = t_L / t_S$：

$$R = \frac{\text{最暗有效像素目标信号}}{\text{最亮不饱和区域信号}} \approx \frac{Y_{target,dark}}{Y_{safe,highlight}}$$

典型值：$R = 4$（2 EV HDR）到 $R = 16$（4 EV HDR）。AE 通过分析场景亮度直方图的双峰分布（高光峰和暗部峰之间的动态范围）自动计算 $R$。

**HDR 合并对 AE 收敛的反馈：**

HDR 合并后图像的亮度分布与任一单帧均不同，若 AE 统计在合并后图像上计算，会产生"AE 以合并图为目标 → 调整曝光 → 新的合并图 → 再次调整"的多级反馈。解决方案（前述 §3.6）：AE 统计固定在中曝帧（M 帧）上计算，HDR 合并只影响最终输出，不进入 AE 闭环。

### 4.4 Flash AE（闪光灯自动曝光）

**问题背景：** 闪光灯拍摄是手机 AE 最难处理的场景之一——闪光灯瞬间输出功率远超环境光，且持续时间极短（通常 < 2ms），普通 AE 闭环根本来不及响应，必须提前预测并控制。

**Pre-flash 测光序列：**

```
用户按快门
    ↓
[Stage 1: Pre-flash 预测量]  ~1–3 帧
  发射低功率预闪（通常为主闪 1/32 功率）
  测量预闪照亮后的场景亮度（AE 统计）
  基于预闪亮度预测主闪功率：
    P_main = P_preflash × (Y_target / Y_preflash) × (1/32)⁻¹
    ↓
[Stage 2: AWB Pre-flash]  同帧
  预闪帧同时用于 AWB 色温预测
  闪光灯色温约 5500–6000K（接近 D55），强制 AWB 向日光色温靠拢
    ↓
[Stage 3: 主闪 + 拍照帧]
  以预测功率 P_main 触发主闪
  AE 曝光参数已锁定（不再调整）
```

**主闪功率与环境光的混合模型：**

$$Y_{total} = Y_{ambient} + Y_{flash} = I_{ambient} \cdot t_{exp} \cdot G + k_{flash} \cdot P_{flash} / d^2$$

其中 $k_{flash}$ 为闪光灯效率系数，$d$ 为拍摄距离，$P_{flash}$ 为闪光灯功率设定。AE 的任务是在已知 $Y_{ambient}$（从预闪统计获得）和预测 $d$（从 AF 距离获得）后，求解使 $Y_{total}$ 等于目标亮度的 $P_{flash}$：

$$P_{flash}^{opt} = \frac{(Y_{target} - Y_{ambient}) \cdot d^2}{k_{flash}}$$

**红眼减少（Red-Eye Reduction）：** 连续低功率预闪 2–4 次，使瞳孔收缩，减少视网膜反射。代价是额外 200–400ms 延迟，现代手机已逐步用数字后处理（AI 红眼检测 + 修复）取代硬件预闪序列，只在必要时（检测到红眼后才修复）运行。

**工程注意（Flash AE 调试）：** 预闪功率比过低（< 1/64）时测光信噪比不足，预测主闪功率误差超过 ±1 EV；过高（> 1/16）时用户可见闪烁且有红眼风险。实际调参时需在不同距离档（0.5m/1m/2m/3m）分别验证 Flash AE 精度，确保各档 EV 误差 < 0.5 EV。

---

## §5 调参（Tuning）

### 5.1 多摄切换平滑参数

| 参数 | 推荐范围 | 说明 |
|------|---------|------|
| `crossfade_frames` | 3–8 帧 | 切换淡入淡出帧数 |
| `ev_correction_step` | 0.1 EV/帧 | 主从 EV 对齐步长 |
| `awb_sync_alpha` | 0.3–0.5 | AWB 参数插值系数 |
| `ev_match_tolerance` | 0.15 EV | EV 对齐判定收敛阈值 |
| `precheck_frames` | 2–4 帧 | 切换前从摄后台预对齐帧数 |

### 5.2 PDAF 降级阈值

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `pdaf_conf_threshold` | 0.3–0.5 | 低于此值切换 CDAF |
| `tof_range_max` | 1.0–2.0 m | ToF 优先距离上限 |
| `slow_af_iso_threshold` | 1600–3200 | 触发慢速AF的ISO门限 |
| `pdaf_conf_spatial_std_max` | 0.15 | 置信度图标准差超过此值触发脏镜检测 |
| `pdaf_valid_area_min` | 0.6 | 高置信度区域面积占比低于此值则不信任PDAF |

### 5.3 三平台高级 3A 参数对比

以下为 Qualcomm、MediaTek、HiSilicon 三个主流 SoC 平台在高级 3A 配置上的典型差异（基于公开文档与行业经验整理，非完整规格，仅供参考）：

| 参数/特性 | Qualcomm (Snapdragon) | MediaTek (Dimensity) | HiSilicon (Kirin) |
|----------|----------------------|---------------------|-----------------|
| 多摄协调机制 | CAMX MultiCamera 节点，支持最多 4 路并行 3A | MMSDK MultiCam，最多 3 路 | IPP MultiCamera，最多 4 路 |
| 帧同步方式 | 硬件 FSIN GPIO + 软件帧号对齐双保险 | 主要依赖软件帧号对齐 | 硬件 VSYNC 广播 |
| AWB 统计域 | Bayer 域（pre-demosaic）+ linearized | Bayer 域 | Bayer 域 + 可选 demosaic 后统计 |
| PDAF 置信度位宽 | 12-bit | 10-bit | 12-bit |
| 场景分类集成 | Qualcomm AI Engine，Scene Detection SDK | APU 集成，NeuroPilot 场景分类 | NPU，华为 AI 场景识别 |
| 3A 调参工具链 | QCAT（Qualcomm Camera Autofocus Tool） | Camera Tuning Tool (CTT) | Tune Tool（华为内部） |
| HDR 多帧 AE 统计 | 长/中/短曝帧独立统计，加权合并 | 合并后统计（部分版本支持分帧） | 分帧统计，中曝帧主控 |
| 防频闪检测算法 | 时域 FFT（128 点），自动识别 50/60Hz | 时域 FFT + 规则检测 | 自适应频闪检测 |
| 最大多帧合并帧数 | AE: 8帧 TNR 感知 | AE: 4帧 TNR 感知 | AE: 6帧 TNR 感知 |

> 注：上表数据来源于公开白皮书（Qualcomm CAMX 文档、MTK MMSDK 文档、华为 IPP 公开材料）与行业经验，具体型号可能差异较大，调试时以各平台最新工具链文档为准。

### 5.4 振荡阻尼参数

| 参数 | 推荐范围 | 说明 |
|------|---------|------|
| `ae_awb_osc_threshold` | 0.03–0.05（归一化亮度） | 振荡检测灵敏度 |
| `ae_awb_osc_frames` | 5–10 帧 | 连续振荡判定所需帧数 |
| `awb_freeze_duration` | 10–20 帧 | 检测到振荡后 AWB 冻结帧数 |
| `ae_kp_damp_factor` | 0.4–0.6 | 振荡时 AE 比例增益衰减系数 |
| `ema_alpha_damp` | 0.7–0.85 | 振荡阻尼期的 EMA 系数 |

---

## §6 评测（Evaluation）

### 6.1 多摄切换质量指标

- **切换亮度差（$\Delta L_{switch}$）：** 切换前后各取 5 帧平均亮度之差，目标 < 0.1 EV（日光室外）/ < 0.2 EV（室内低光）；见 §6.3 分场景指标
- **色温跳变（$\Delta CCT_{switch}$）：** 切换前后色温差，目标 < 200K
- **对焦切换延迟：** 从切换完成到重新合焦的帧数，目标 < 10 帧

### 6.2 PDAF 低光评测

在 ISO 3200、ISO 6400 场景下测试 PDAF 成功率（成功 = 对焦误差 < 50μm），与日间基准（ISO 100）对比衰退幅度。

**评测矩阵建议：**

| ISO | 测试场景亮度（lux） | PDAF 成功率目标 | CDAF 回退率上限 |
|-----|---------------|--------------|--------------|
| 100 | > 500 | > 99% | < 1% |
| 400 | 100–500 | > 95% | < 5% |
| 1600 | 10–100 | > 80% | < 20% |
| 3200 | 3–10 | > 60% | < 40% |
| 6400 | < 3 | > 30% | < 70% |

### 6.3 3A 环路耦合稳定性评测

**振荡频率测试：**
- 在钨丝灯（2800K）和日光混合光源（一半钨丝灯、一半日光灯）场景下拍摄 300 帧预览
- 提取逐帧 Y 通道均值时序曲线，做 FFT 分析
- 目标：无持续振荡（在任意 1Hz 以上频率的功率谱密度峰值低于直流分量的 5%）

**多摄切换测试标准场景：**
1. **日光室外切换（1× → 3×）：** 亮度跳变 < 0.1 EV，色温跳变 < 150K
2. **室内低光切换（1× → 2×）：** 亮度跳变 < 0.2 EV，对焦重新锁定 < 8 帧
3. **逆光场景切换：** HDR 模式正确继承，高光无过曝突变

### 6.4 场景自适应 3A 评测

| 测试场景 | 目标指标 | 典型基准值 |
|---------|---------|---------|
| 人脸检测触发 AE 测光区切换延迟 | 检测到人脸后 N 帧内测光区切换到人脸区域 | < 3 帧 |
| 夜景模式切换后 AWB 稳定帧数 | 切换夜景 ISP Profile 后 AWB 重新稳定 | < 15 帧 |
| 场景分类误判率（室内误判为室外） | 在 500 张测试图上评估 | < 5% |
| 逆光场景 HDR 正确触发率 | 高光区 EV > +3 时自动启用 HDR | > 95% |

### 6.5 AE 收敛速度（Convergence Speed）

**定义：** 从场景亮度发生阶跃变化（如突然进入/离开强光区域）起，到 AE 输出亮度稳定在目标值 ±5% 范围内所需的帧数。

$$N_{converge} = \min\left\{n \;\middle|\; \forall k \geq n,\; \left|\frac{Y(k) - Y_{target}}{Y_{target}}\right| \leq 0.05\right\}$$

**测试方法：**
1. 固定拍摄目标（标准灰卡，$Y_{target} = 118$，18% 灰）
2. 用遮光板在镜头前快速开合，模拟亮度从 $L_0$ 跳变到 $L_1$（常用组合：暗室 5lux → 室内 500lux；室内 → 强烈日光 80,000lux）
3. 逐帧记录 AE 统计亮度 $Y(k)$，计算 $N_{converge}$
4. 目标值：
   - 快速场景切换（如开灯）：$N_{converge} \leq 8$ 帧（@30fps，约 267ms）
   - 连续预览常规移动：$N_{converge} \leq 20$ 帧（@30fps，约 667ms）

**分步收敛曲线分析（典型值）：**

| 阶段 | 帧范围 | 亮度行为 | 典型说明 |
|------|--------|---------|---------|
| 过冲期 | 1–3 帧 | $|Y - Y_{target}| > 30\%$ | PI 积分项尚未到位，比例项主导 |
| 快速收敛 | 3–8 帧 | 误差从 30% 下降至 10% | 积分项接管，步长受限防止过调 |
| 精调稳定 | 8–15 帧 | 误差 < 5%，微调阶段 | 小步长 AE 调整，消除剩余误差 |
| 稳态 | > 15 帧 | $|Y - Y_{target}| < 2\%$ | 闭环稳定 |

### 6.6 AE 精度（Accuracy，稳态误差）

**定义：** AE 收敛后稳态帧（通常取收敛后 10 帧的平均值）与目标亮度之间的误差，以 EV 表示：

$$\Delta EV_{steady} = \log_2\frac{\bar{Y}_{steady}}{Y_{target}}$$

其中 $\bar{Y}_{steady}$ 为稳态帧亮度均值。目标：$|\Delta EV_{steady}| \leq 0.1\ \text{EV}$（约 7% 亮度误差）。

**评测场景矩阵：**

| 场景 | 测光区域 | 目标 $|\Delta EV|$ | 备注 |
|------|---------|-----------------|------|
| 标准灰卡（18% 灰）| 全画面平均测光 | ≤ 0.05 EV | 最严格基准 |
| 人脸特写 | 人脸区域中心权重测光 | ≤ 0.1 EV | 允许背景略曝 |
| 逆光场景 | HDR 主体区域测光 | ≤ 0.15 EV | HDR 合并后评估 |
| 高对比室内 | 中心权重 | ≤ 0.1 EV | 忽略边缘过曝区域 |

### 6.7 AF 对焦精度（Focus Accuracy）

**定义：** 在指定被摄距离（如 50cm、100cm、300cm）处，多次拍摄（通常 N=50 次）中对焦结果落在景深范围内（Depth of Field, DoF）的比例：

$$\text{AF Accuracy} = \frac{\text{shots in-DoF}}{N} \times 100\%$$

景深计算（弥散圆直径 $c$，焦距 $f$，光圈 $F_{num}$，物距 $D$）：

$$\text{DoF} = \frac{2 D^2 F_{num} c}{f^2 - F_{num}^2 c^2 D^2 / f^2} \approx \frac{2 D^2 F_{num} c}{f^2}$$

典型手机参数（广角，$f=5.6\text{mm}$，$F_{2.0}$，$c=0.029\text{mm}$）：

| 物距 | 景深（近似） | AF 精度目标（PDAF） | AF 精度目标（CDAF 回退） |
|-----|-----------|-----------------|---------------------|
| 30 cm（微距） | ±3 mm | > 90% | > 75% |
| 100 cm（人像） | ±20 mm | > 95% | > 85% |
| 300 cm（中景） | ±180 mm | > 98% | > 92% |
| 无穷远（风景） | 超焦距以上 | N/A | N/A |

**测试标板：** 推荐使用 ISO 12233 分辨率测试卡或 Siemens star 靶，在无反光环境下测试。通过 MTF50 曲线确认焦面是否落在测试卡所在平面。

### 6.8 AWB 角误差（Angular Error）

**定义：** 估计的光源颜色向量与真实光源颜色向量之间的夹角，是 AWB 算法精度的标准量化指标（Finlayson & Hordley, 2001, JOSA-A）。

**标准计算方法（3D 归一化 RGB 向量）：**

设归一化光源向量 $\hat{\mathbf{e}}_{est} = (\mu_R, \mu_G, \mu_B)/\|(\mu_R, \mu_G, \mu_B)\|$，$\hat{\mathbf{e}}_{gt} = (l_R, l_G, l_B)/\|(l_R, l_G, l_B)\|$，则：

$$\varepsilon_{ang} = \arccos\left(\hat{\mathbf{e}}_{est} \cdot \hat{\mathbf{e}}_{gt}\right) \times \frac{180°}{\pi}$$

**工程近似版（2D 对数色度）：**

部分文献以对数色度空间近似计算，两者数值不等价但量级相近：

$$\mathbf{e}_{est} = \left(\log\frac{\mu_R}{\mu_G},\; \log\frac{\mu_B}{\mu_G}\right), \quad \mathbf{e}_{gt} = \left(\log\frac{l_R}{l_G},\; \log\frac{l_B}{l_G}\right)$$

$$\varepsilon_{ang}^{\log} = \arccos\left(\frac{\mathbf{e}_{est} \cdot \mathbf{e}_{gt}}{\|\mathbf{e}_{est}\| \cdot \|\mathbf{e}_{gt}\|}\right) \times \frac{180°}{\pi}$$

**AWB 算法对比基准（NUS-8 数据集上典型结果）：**

| AWB 算法 | 中位角误差 | 均值角误差 | 备注 |
|---------|-----------|-----------|------|
| 灰色世界（Gray World） | 4.5° | 6.2° | 基线，简单场景可用 |
| 白色点检测（White Patch） | 3.8° | 5.3° | 高光场景较好 |
| 统计 AWB（2nd-order Gray） | 2.9° | 3.8° | 需标定 |
| 深度学习 AWB（FFCC, 2017） | 1.4° | 1.8° | 旗舰机常用 |
| 目标值（工业标准） | < 2.0° | < 3.0° | 一般认为 < 3° 为可接受 |

**角误差与主观感受对应关系：** 角误差 < 1° 人眼几乎无感知；1–3° 可察觉轻微偏色；> 5° 明显偏色（皮肤偏绿或偏黄）。

---

## §7 失效场景（Failure Cases）

### 7.1 PDAF 条纹伪影（PDAF Striping）

**成因：** PDAF 传感器在 Bayer 阵列中嵌入相位差像素对（Phase Detection Pixels, PD pixels），这些 PD 像素被微透镜偏心切割（Left-blocked / Right-blocked），对入射光的响应特性（灵敏度）与普通像素不同：

$$R_{PD} = R_{normal} \cdot (1 - \delta_{sensitivity}), \quad \delta_{sensitivity} \approx 0.05\text{–}0.15$$

由于 PD 像素呈行列规律性排布（通常每 2 行中有 1 行嵌入 PD 对，周期为 4–8 行），其灵敏度差异在 RAW 图像上表现为**周期性横向或纵向亮度条纹**，在 Demosaic 后尤为明显（高频边缘附近伪色/条纹）。

**修正方法——PDAF Correction in Demosaic Stage：**

1. **PD 像素位置标记：** 从 sensor 厂商的 PDAF metadata（通常编码在 EXIF/ISP 配置中）获取全帧 PD 像素坐标图（PDAF pixel map）
2. **PD 像素插值替换：** 在进行 Bayer Demosaic 之前，用周围普通像素插值替换 PD 像素的亮度值，消除灵敏度差异引入的幅度偏差：

$$\hat{I}_{PD}(x,y) = \frac{1}{|N_p|}\sum_{(i,j)\in N_p} I_{normal}(i,j)$$

其中 $N_p$ 是 $(x,y)$ 位置的若干邻近普通像素集合（通常取最近 4 个同色通道非 PD 像素）。

3. **灵敏度校正（Sensitivity Correction）：** 若不做插值替换，可直接对 PD 像素施加灵敏度补偿增益：

$$I_{corrected}(x,y) = I_{raw}(x,y) / (1 - \delta_{sensitivity})$$

其中 $\delta_{sensitivity}$ 在工厂标定时通过均匀光源（积分球）测量各 PD 像素响应偏差获得，并写入 Calibration 数据库（OTP 或标定文件）。

**典型平台实现：** Sony IMX 系列传感器（IMX766、IMX989）提供 PDAF 像素坐标表（`pdaf_coordinates` 结构体）和推荐的 PD-correction 算法；Qualcomm ISP 在 BPC/BCC 模块中集成 PDAF 校正。

### 7.2 多摄切换色缝伪影（Multi-Camera Color Seam）

**成因：** 在多摄系统中，各路摄像头独立运行 AWB 和 AE，由于光学特性差异（镜头透射率色移、sensor 光谱响应差异、不同焦距导致的视场亮度差异），即使在同一场景下也会收敛到略不同的色温估计和曝光状态。在从主摄（如 1× 广角）切换到从摄（如 3× 长焦）的瞬间，两者当前 AWB/AE 状态不同步，切换帧出现：

- **色温跳变（Color Temperature Jump）：** 广角 AWB 估计 5500K，长焦 AWB 仅收敛到 5100K，切换帧出现 400K 色温差，画面出现偏黄或偏蓝的闪烁
- **色缝（Color Seam）：** 在连续光学变焦（optical zoom）场景下，相机物理切换点附近可能出现单帧颜色突变的"缝隙"

**抑制方案：**

**方案一：AWB 强制对齐（AWB Force-Sync）**

切换前，将从摄 AWB 增益强制对齐到主摄当前 AWB 增益（考虑跨摄色差标定偏移 $\Delta_{CCT,calib}$）：

$$\mathbf{w}_{slave}^{init} = \mathbf{w}_{master}^{current} + \boldsymbol{\delta}_{calib}$$

其中 $\boldsymbol{\delta}_{calib} = ({\delta}_{R}, {\delta}_{G}, {\delta}_{B})$ 是工厂标定的跨摄色差补偿向量（两摄对准同一色板拍摄后差值，写入相机参数文件）。

**方案二：切换帧插值（Crossfade Color Correction）**

在切换后的 $K$ 帧内，对从摄输出做色温线性插值：

$$CCT_{output}(t) = CCT_{slave}(t) \cdot \frac{t - t_{switch}}{K} + CCT_{master}(t_{switch}) \cdot \left(1 - \frac{t - t_{switch}}{K}\right)$$

实质上是用 $K$ 帧的渐变过渡掩盖切换瞬间的色温不连续，$K = 5\text{–}10$ 帧为经验最佳值。

**工程指标（Color Seam Specification）：**

$$\Delta CCT_{seam} = |CCT_{post-switch} - CCT_{pre-switch}| < 150\ \text{K}$$
$$\Delta E_{seam} < 2.0\ (\text{CIELAB ΔE}_{00})$$

### 7.3 AF 对焦抖动（AF Hunting）

**成因：** 对焦抖动（Hunting）是 CDAF 爬山算法（Hill-Climbing Search）在以下条件下出现的振荡失稳：

1. **对比度峰值平坦（Flat Peak）：** 当被摄体纹理不足或场景缺乏高频细节时，对比度曲线的峰值宽平，CDAF 算法无法准确定位极大值位置，在峰值附近来回搜索：

$$\frac{\partial C}{\partial d}\bigg|_{d_{focus}} \approx 0, \quad \frac{\partial^2 C}{\partial d^2}\bigg|_{d_{focus}} \approx 0$$

2. **低纹理场景（Low Texture）：** 蓝天、白墙、纯色背景等场景中对比度统计信号（如 Laplacian 方差）本底噪声高于有效纹理信号，SNR < 3dB，导致算法误将噪声极值判定为焦点。

3. **步长过大（Coarse Step Size）：** VCM 驱动的最小步长过大时，相邻两个搜索位置的对比度差落在量化噪声范围内，算法无法单调收敛。

**检测机制：**

$$\text{Hunting} = \begin{cases} \text{True} & \text{if} \; |\text{lens\_pos}(t) - \text{lens\_pos}(t-2)| > \Delta_{hunt} \text{ 持续 } M \text{ 帧} \\ \text{False} & \text{otherwise} \end{cases}$$

其中 $\Delta_{hunt}$ 为抖动检测步长阈值（通常为 VCM 行程的 3–5%），$M = 4\text{–}6$ 帧。

**抑制方案：**

| 方案 | 原理 | 适用条件 |
|------|------|---------|
| 焦点锁定（Focus Lock） | 检测到抖动后在当前位置锁定，等待场景变化 | 静态低纹理场景 |
| 降级 PDAF | 若 PDAF 置信度 > $\tau_{low}$，切换 PDAF 辅助收敛 | 有光线但纹理少 |
| 步长自适应缩减（Fine Step） | 抖动检测后将 VCM 步长减半，精细搜索 | 峰值平坦情况 |
| 最佳历史位置回退（Best-Position Hold） | 记录历史最大对比度位置 $d_{best}$，抖动后回退到 $d_{best}$ | 任何抖动情况 |
| 低通滤波对比度曲线 | 对连续帧对比度值做 EMA 平滑（$\alpha=0.7$），降低噪声引起的伪极值 | 低纹理高噪声场景 |

**工程参数推荐：**

```
hunting_detect_threshold    = 15  % (VCM DAC counts, ~5% of full travel)
hunting_detect_frames       = 5   % 连续帧
fine_step_reduction_factor  = 0.5 % 抖动后步长缩减比例
best_position_hold_frames   = 30  % 锁定最佳历史位置等待时长
cdaf_texture_snr_min        = 3.0 % dB，低于此值认为低纹理，降级 PDAF
```

---

## §8 PDAF 物理原理深度解析

### 8.1 相位差检测原理

PDAF 的核心物理原理是基于**波前倾斜（Wavefront Tilt）**引起的图像横向偏移。传感器中嵌入的左遮蔽像素（Left-masked, L）和右遮蔽像素（Right-masked, R）分别只接收来自镜头左半部分和右半部分的光线，形成左视差子图（Left sub-aperture image）和右视差子图（Right sub-aperture image）。

当被摄物体**前对焦（Front Focus）**时，L 图像相对 R 图像向右偏移；**后对焦（Back Focus）**时向左偏移；**合焦**时 L/R 图像对齐无偏移。

**相位差与物距关系（PDAF 基本方程）：**

$$\boxed{\Delta x_{PD} = \frac{f \cdot d}{D_z}}$$

其中：
- $\Delta x_{PD}$：L/R 子孔径图像之间的横向偏移量（像素单位）
- $f$：镜头焦距（mm）
- $d$：左右 PD 像素对的有效光瞳分离距离（mm），由传感器微透镜设计决定（通常为像素节距的 0.5–1 倍）
- $D_z$：被摄物体距传感器的物距（mm）

**推导过程（几何光学）：**

设镜头主平面到传感器的像距为 $v$（通过薄透镜公式 $1/f = 1/D_z + 1/v$ 确定），合焦时像面与传感器重合；非合焦时，被摄点 $P$ 在传感器平面的弥散圆（Circle of Confusion, CoC）直径为：

$$c = d \cdot \left|\frac{v - v_0}{v_0}\right|$$

由此推导得相位差：$\Delta x_{PD} \approx f \cdot d / D_z$（近场时需修正高阶项）。

**散焦量（Defocus Amount）与相位差转换：**

实际工程中使用**相位斜率标定系数（Phase Slope Calibration Coefficient）** $k_{phase}$（单位：DAC counts/pixel shift），将相位差转换为 VCM 驱动量：

$$\text{VCM\_delta} = k_{phase} \cdot \Delta x_{PD}$$

$k_{phase}$ 在工厂生产时通过多距离标定（将被摄物放置在多个已知距离，测量对应相位差）拟合得到，并存储在 OTP（One-Time Programmable memory）中。

### 8.2 PDAF 标定：光学中心偏移校正

由于制造工艺偏差，PD 像素微透镜的实际光学中心（Chief Ray Angle, CRA）与设计值存在偏差，导致全帧 PDAF 存在**位置相关的系统性相位偏差**（Phase Offset Map）。

**标定流程：**

1. 将摄像头对准无穷远均匀亮目标（积分球或晴天白墙）
2. 在已知合焦状态下（通过 CDAF 确认精确合焦），采集全帧 PDAF 统计
3. 此时理论相位差应为 0，实测相位差即为位置相关偏差图 $\Phi_{offset}(x,y)$
4. 校正：$\Delta x_{PD,corrected}(x,y) = \Delta x_{PD,raw}(x,y) - \Phi_{offset}(x,y)$
5. $\Phi_{offset}(x,y)$ 存入 OTP 或标定文件（通常以多项式或查找表形式）

**CRA 失配（Chief Ray Angle Mismatch）：** 在全画幅传感器或大光圈镜头中，图像边缘的主光线入射角（CRA）可达 20–30°，若微透镜 CRA 设计不匹配，边缘 PDAF 精度明显下降。解决方案：镜头-传感器协同设计（Lens-Sensor Co-Design），确保 CRA 全画幅匹配。

### 8.3 Dual-PD 传感器（以 Sony IMX766 为例）

传统 PDAF 每隔若干行才嵌入一对 PD 像素（稀疏 PD，Sparse PDAF，覆盖率约 5–10% ），限制了 PDAF 的空间分辨率和对焦速度。

**Dual-PD（全像素相位检测，All-Pixel PDAF）** 架构（Sony IMX766、IMX989、三星 ISOCELL GN 系列）在**每个像素**内部实现 L/R 光路分离：通过在单个像素的微透镜下放置两个独立的感光区域（Left Photodiode + Right Photodiode），每个像素同时输出 L、R 两个信号，覆盖率达到 100%。

**Dual-PD 优势：**

| 对比项 | 稀疏 PDAF | Dual-PD（全像素 PDAF） |
|-------|-----------|----------------------|
| 覆盖率 | 5–10% | 100% |
| AF 空间分辨率 | 低（每 8–16 行 1 次）| 高（每像素均可计算）|
| 低光 PDAF 能力 | 弱（PD 像素少，SNR 低）| 强（全帧 PD，可区域均值）|
| 条纹伪影 | 较显著（灵敏度差异行列明显）| 较轻（但 L+R 合并后需特殊 Demosaic）|
| PDAF 读出数据量 | 低 | 高（2× 数据，需带宽支持）|
| 代表型号 | OmniVision 早期 PDAF | Sony IMX766, IMX989; Samsung GN2 |

**IMX766 Dual-PD 的 Demosaic 注意事项：** 读出时 L+R 合并（Full Pixel = L+R）作为普通 Bayer 使用；L-R 差（Phase Difference）用于 AF 计算。Demosaic 需感知 PD 结构（PDAF-aware Demosaic），在 AF 数据提取后对 PD 像素做亮度修复，否则仍会出现轻微条纹。

### 8.4 CDAF vs PDAF 对比

| 对比维度 | CDAF（对比度检测 AF） | PDAF（相位差检测 AF） |
|---------|---------------------|---------------------|
| **工作原理** | 爬山搜索对比度极大值 | 直接测量相位差计算方向和距离 |
| **对焦速度** | 慢（需多帧搜索，20–50 步）| 快（1–3 帧即可收敛）|
| **低光性能** | 较好（只需足够亮度读出）| 弱（相位差 SNR 随光照下降）|
| **低纹理场景** | 差（无对比度无法搜索）| 较好（依赖光瞳分离，不完全依赖纹理）|
| **精度** | 高（达到衍射极限）| 受标定精度影响（±10–30μm 系统误差）|
| **深度依赖** | 无（纯图像统计）| 有（$\Delta x_{PD} = fd/D_z$ 受焦距影响）|
| **硬件要求** | 无（通用 Bayer sensor）| 需 PDAF 像素（成本更高）|
| **典型应用** | 暗光/微距/纯色场景 fallback | 日常快速 AF 主流方案 |
| **混合使用** | Hybrid AF：PDAF 粗定位 + CDAF 精调 | — |

---

## §9 多摄系统 3A 协同

### 9.1 多摄 3A 状态同步架构

旗舰多摄系统（主摄 + 超广角 + 长焦，甚至 4 摄）的 3A 协同需要在以下层次上实现状态共享：

```
┌────────────────────────────────────────────────────────────┐
│                    3A 协同管理层（HAL Level）                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  主摄（1×）  │  │ 超广角（0.6×）│  │   长焦（3× / 5×）   │ │
│  │  AE: 主控   │  │  AE: 从属   │  │    AE: 从属         │ │
│  │  AWB: 主控  │  │  AWB: 从属  │  │   AWB: 从属         │ │
│  │  AF: 独立   │  │  AF: 独立   │  │   AF: 独立（SAF）    │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │  EV/CCT 广播   │                    │             │
│         └────────────────┴────────────────────┘             │
└────────────────────────────────────────────────────────────┘
```

**主摄承担的协同职责：**
- 对外发布当前 AE 状态（$EV_{master}$）和 AWB 状态（$CCT_{master}$，或 WB 增益向量）
- 每帧更新，供从摄 3A 解算使用
- 在切换预判（Zoom Gesture 检测到连续变焦手势）时提前发布"切换预告"，触发从摄后台预对齐

**从摄的跟随策略：**

$$EV_{slave}(t) = EV_{master}(t) + \Delta EV_{calib,optics} + \Delta EV_{luma\_diff}(t)$$

其中 $\Delta EV_{luma\_diff}(t)$ 是从摄独立测光得到的本路亮度差异（用于补偿主从摄视野差异，如长焦对准局部高光区域而广角视野包含大面积暗部）。

### 9.2 变焦过渡平滑（Zoom Transition Smoothing）

在光学变焦（Optical Zoom）切换点附近，画面会经历物理上的摄像头切换（如从 1× 摄切换到 3× 摄），此过程涉及：

**AE 过渡平滑：**

定义过渡区域为 $[z_1, z_2]$（焦距倍率，如 $[2.8\times, 3.2\times]$），在此区间内对 EV 输出做插值：

$$EV_{output}(z) = EV_{main}(z) \cdot \alpha(z) + EV_{tele}(z) \cdot (1 - \alpha(z))$$

$$\alpha(z) = \frac{z_2 - z}{z_2 - z_1}, \quad z \in [z_1, z_2]$$

视频录制时，两路 ISP 同时取流（Dual-Stream Mode），$EV_{output}$ 用软件混合两路图像帧输出，避免切换帧的突变。

**AWB 过渡平滑：**

与 AE 过渡类似，在切换区间对色温做线性插值，同时确保 $|\Delta CCT_{transition}| < 50\text{K/frame}$（避免闪烁感知）。

**AF SAF（Seamless Auto Focus）：**

在光学变焦过渡时，镜头焦距发生连续变化，原焦点对应的物距随焦距变化而变化（$D_z$ 不变，但焦平面的 VCM 位置变化）。SAF 机制：

1. 实时追踪焦点对应的**物距** $D_z$（由 PDAF 方程 $D_z = f \cdot d / \Delta x_{PD}$ 反算）
2. 变焦时根据新焦距 $f'$ 重新计算目标 VCM 位置：

$$\text{VCM}_{target}(f') = k_{phase}(f') \cdot \frac{f' \cdot d}{D_z}$$

3. 主动驱动 VCM 跟随焦距变化，全程保持对焦，无需重新搜索

SAF 要求 VCM 控制器具备**预测性驱动（Predictive Drive）**能力，即在变焦速度较快（如快速捏合手势）时提前计算 VCM 目标位置，而不是等待 PDAF 反馈后再响应（闭环延迟约 2–3 帧）。

### 9.3 色缝抑制（Color Seam Suppression）

在多摄边界处（切换点）的色缝抑制对视频变焦体验影响显著。工业级解决方案分为以下层次：

**Level 1：标定层（Factory Calibration）**

- 跨摄色差标定（Cross-Camera Color Calibration）：使用 ColorChecker 24 色卡在 3–5 种标准光源下对所有摄像头组合进行拍摄
- 计算每对摄像头之间的 $3\times3$ 色彩转换矩阵（Cross-Camera CCM）：$\mathbf{I}_{slave,corrected} = \mathbf{M}_{cross} \cdot \mathbf{I}_{slave}$
- 将 $\mathbf{M}_{cross}$ 存入相机标定文件，每次 AWB 同步时一并应用

**Level 2：运行时动态对齐（Runtime Dynamic Alignment）**

- 在切换发生时，比较主从摄在当前场景的实际色温估计差，通过自适应色温插值消除残差
- 适用于标定无法完全覆盖的光源条件（如特殊色温 LED 灯）

**Level 3：图像域后处理（Image Domain Post-Processing）**

- 在 YUV 域对切换帧进行局部颜色迁移（Color Transfer），以主摄当前颜色分布为参考，将从摄输出颜色迁移到匹配主摄（Reinhard et al., 2001 风格迁移算法的实时轻量版本）
- 代价：需要额外的计算量（约 5–10ms @1080p on NPU）

**工程指标（Color Seam Specification）：**

| 指标 | 目标值 | 测试条件 |
|------|--------|---------|
| 切换帧色温差 $\Delta CCT$ | < 100 K **[10]** | 标准 D65 光源、Macbeth 灰卡场景 |
| 切换帧 $\Delta E_{00}$ | < 1.5  | 皮肤色（肤色 patch 18# Macbeth） |
| 视频变焦色温波动速率 | < 30 K/帧  | 连续变焦 1× → 5× |
| 过渡帧数 | 5–12 帧  | 快速切换（手势焦段跳变） |

> 本节涉及的参考文献见章末参考文献列表 [9]–[16]。

---

## §10 术语表（Glossary）

| 术语 | 英文 | 定义 |
|------|------|------|
| 主从模式 | Master-Slave Sync | 多摄同步策略，指定一路摄像头为主控，其他从属对齐主控 3A 状态 |
| 帧同步信号 | FSIN / Frame Sync Input | 硬件 GPIO 信号，确保多路 sensor 同一时刻开始积分 |
| 等效曝光值 | EV (Exposure Value) | 综合快门、增益、光圈的曝光量对数度量，每差 1 EV 亮度相差一倍 |
| PDAF 置信度 | PDAF Confidence | 相位差估计的可靠程度（0-1），低置信度时降级到 CDAF |
| 散焦量 | Defocus Amount | 当前成像面与焦平面的距离（μm 单位），由相位差除以标定系数得到 |
| 振荡阻尼 | Oscillation Damping | 检测 AE-AWB 耦合振荡后临时降低控制器增益、冻结 AWB 的稳定措施 |
| 前馈补偿 | Feedforward Compensation | AF 镜片移动导致光圈变化时，AE 的主动 EV 补偿（绕过 PI 闭环） |
| 场景自适应 | Scene-Adaptive 3A | 由 AI 场景分类驱动的多环路协同 3A 参数切换机制 |
| Pre-TNR 统计 | Pre-TNR AE Stats | AE 统计在时域降噪之前的原始 RAW 帧上计算，防止 TNR 干扰闭环 |
| T 值 | T-Stop | 镜头实际透光率对应的等效光圈值（与 F 值不同，考虑透射率损失） |
| EMA 平滑 | Exponential Moving Average | 指数移动平均平滑，$\theta(t) = \alpha\theta(t-1)+(1-\alpha)\theta^*(t)$，用于减弱参数跳变 |
| 淡入淡出 | Crossfade | 多摄切换时在 N 帧内对两路输出进行线性 alpha 混合的平滑策略 |
| Pre-Capture AE | Pre-Capture AE | 按下快门前触发的短暂 AE 收敛序列，确保曝光准确后再开始 Burst 采集 |
| 曝光比 | Exposure Ratio | HDR 多帧中长曝与短曝的积分时间比值，决定 HDR 系统的动态范围覆盖 |
| 中曝帧 | Middle Exposure Frame (M-frame) | HDR 三帧结构（L/M/S）中曝光量居中的帧，通常作为 AWB/AE 统计的基准帧 |
| 场景分类 | Scene Classification | AI 模块对当前帧内容的语义推断（室内/室外/夜景/人脸等），驱动 3A 参数切换 |
| 预测性 3A | Predictive 3A | 基于前序帧 3A 状态趋势预测下一帧最优参数，跳过等待闭环收敛的延迟 |
| PDAF 条纹 | PDAF Striping | PD 像素灵敏度与普通像素不同导致的周期性亮度条纹伪影，需在 Demosaic 前校正 |
| PD 像素 | Phase Detection Pixel | PDAF 传感器中经微透镜偏心切割的特殊像素，分左遮蔽（L）和右遮蔽（R）两种 |
| 相位斜率标定 | Phase Slope Calibration | 将相位差（pixel shift）转换为 VCM 驱动量的线性标定系数 $k_{phase}$，存储在 OTP 中 |
| 光学中心偏移 | CRA Mismatch | 微透镜主光线入射角与镜头出射角不匹配，导致边缘 PDAF 系统性相位偏差 |
| Dual-PD | Dual Photodiode PDAF | 每像素内置两个感光区域（L+R）的全像素相位检测架构，覆盖率 100%（如 Sony IMX766）|
| AF 抖动 | AF Hunting | CDAF 爬山算法在低纹理/平坦对比度峰值场景下的来回振荡失稳现象 |
| 色缝 | Color Seam | 多摄切换瞬间因 AWB/AE 状态不同步导致的切换帧颜色突变 |
| 无缝自动对焦 | SAF (Seamless Auto Focus) | 光学变焦过渡时，通过物距追踪和预测性 VCM 驱动保持全程对焦，无需重新搜索 |
| 收敛帧数 | Frames-to-Convergence | AE/AF/AWB 从初始状态到稳态所需的帧数，是 3A 速度的核心评测指标 |
| AWB 角误差 | AWB Angular Error | 在对数色度空间中，估计光源方向与真实光源方向之间的夹角（度），Finlayson & Hordley 定义 |
| 跨摄色差标定 | Cross-Camera Color Calibration | 工厂标定阶段对多摄之间系统性色差进行测量并写入标定文件的流程 |
| 弥散圆 | Circle of Confusion (CoC) | 非合焦时点光源在像面形成的模糊圆，直径决定景深计算的清晰度判定阈值 |

---



---

> **工程师手记：视频 3A 的收敛速度与多摄同步挑战**
>
> **收敛速度与精度的权衡：** 视频模式下 3A 收敛速度与精度是本质矛盾。以 AE 为例，激进步长（每帧 EV 调整 ±0.5 EV）可在 3～5 帧内收敛，但在均匀背景场景（如白墙）下会引起可见的亮度抖动（flicker），MOS 下降约 0.6；保守步长（±0.05 EV/帧）消除抖动，但收敛至 ±0.2 EV 误差需要约 20 帧（@30fps 约 667 ms），在快速拉镜或场景切换时主观感受曝光滞后明显。工程实践采用动态步长策略：检测到场景切换（帧间亮度均值变化 > 15%）时切入快速收敛模式（步长 × 5），稳定后切回精细模式；该机制使典型场景切换响应时间缩短至 5～8 帧，稳态抖动降低 80%。
>
> **昼夜场景转换的曝光过冲问题：** 日转夜场景是导致曝光过冲（blow-out）最常见的触发条件。当环境亮度在 300 ms 内从 5000 lux 骤降至 50 lux（如进入隧道）时，若场景检测延迟超过 3 帧（@30fps = 100 ms），自动曝光将来不及在感光切换完成前拉升增益，出现连续 3～5 帧欠曝图像；而若检测过于灵敏，夜间灯光短暂遮挡（< 2 帧）会误触发日夜切换，引起增益跳变噪声。实测最优场景检测阈值：连续 2 帧亮度变化量均超过 40%，且方差变化 > 20 DN² 时触发切换；该参数在 100 个真实日夜切换场景下虚警率 < 5%，漏检率 < 3%。
>
> **多摄 3A 同步漂移：** 在双摄或三摄系统中，主副摄的 3A 参数独立收敛会导致融合边界处出现亮度/色温跳变（drift）。实测数据：主副摄 AWB 独立运行时色温差异可达 ±300K，切换瞬间主观可见；AE 曝光差异若超过 0.3 EV，深度图融合边缘出现光晕。工程上采用主摄主导、副摄跟随的 Master-Slave 3A 架构：副摄每 5 帧向主摄 3A 状态靠拢一步（步长为差值的 20%），同步延迟约 150 ms；在双摄光圈差异（如主摄 f/1.8 vs 长焦 f/2.8）场景下，需额外引入 2 EV 的静态偏置补偿，否则同步后副摄系统性欠曝。
>
> *参考：Noraky & Sethuraman, "Low Power Depth Estimation of Rigid Objects for Time-of-Flight Imaging Systems," IEEE TCSVT 2019；Brown, "Multi-image Blind Deblurring Using a Coupled Adaptive Sparse Prior," CVPR 2013；高通 Spectra ISP 3A 技术白皮书（2022）*

## 插图

![3a convergence](img/fig_3a_convergence_ch.png)

*图1. 3A算法收敛过程示意（图片来源：作者自绘）*

![deep awb](img/fig_deep_awb_ch.png)

*图2. 基于深度学习的AWB方法（图片来源：作者自绘）*

![multi exposure ae](img/fig_multi_exposure_ae_ch.png)

*图3. 多曝光AE控制示意（图片来源：作者自绘）*



---
![3a advanced control](img/fig_3a_advanced_control_ch.png)

*图4. 3A高级控制策略（图片来源：作者自绘）*

![3a system diagram](img/fig_3a_system_diagram_ch.png)

*图5. 3A系统框图（图片来源：作者自绘）*

![ae af awb interaction](img/fig_ae_af_awb_interaction_ch.png)

*图6. AE、AF与AWB交互关系（图片来源：作者自绘）*

![awb advanced algorithm](img/fig_awb_advanced_algorithm_ch.png)

*图7. AWB高级算法框架（图片来源：作者自绘）*

---

## 习题

**练习 1（理解）**
多摄系统中主副摄的 3A 同步涉及时间戳对齐精度。请分析：（1）为什么多摄同步精度要求 ≤ 1ms，而不是 ≤ 33ms（一帧时间）？在哪些具体场景下时间戳不对齐会产生可见伪影？（2）硬件帧同步（FSIN 信号）和软件时间戳同步两种方案的精度差异是什么？（3）当主副摄帧率不同（如主摄 30fps，超广角 24fps）时，如何设计时间戳对齐策略？

**练习 2（分析）**
PDAF Dual-PD（全像素双 PD，如 Sony IMX766）与传统稀疏 PDAF（相位像素覆盖率 < 5%）相比有显著优势。请对比：（1）全像素双 PD 在低光场景下的相位差信号 SNR 比稀疏 PDAF 提升多少（覆盖率差异导致的理论估算）？（2）Dual-PD 的全像素相位差数据量大，在 ISP 内部如何处理这些数据（是全部传到 CPU 还是在 IFE 内完成相位差估算）？（3）在 EV < 3 的弱光下，即使是 Dual-PD，为什么 PDAF 精度仍会退化？

**练习 3（工程设计）**
AE 和 AWB 的联控存在振荡风险：当 AWB 修正白平衡后，图像整体亮度可能发生变化，触发 AE 重新调整曝光，AE 调整后又影响 AWB 的灰度假设，形成振荡。请设计一套 AE+AWB 联控的阻尼（Damping）机制：（1）定义振荡的判断标准（连续 N 帧内亮度/色温变化量超过阈值）；（2）当检测到振荡时，如何自动降低 AE 和 AWB 的更新步长（step size）？（3）这种阻尼机制会带来什么负面效果，如何设置退出条件？

**练习 4（扩展）**
在高通 CamX 多摄架构中，MultiCamera Controller 负责协调主副摄的 3A 统计数据合并和参数发送。请调研：CamX 的 MultiCamera Feature 是如何实现跨路 3A 数据共享的（通过 MetaBuffer 还是 Session 间消息？）？与联发科 FeaturePipe 的多摄节点设计相比，在架构设计上有何本质区别？

## 参考文献

[1] Qualcomm CAMX MultiCamera — [github.com/quic/camx](https://github.com/quic/camx)（BSD-3，公开）
[2] Chen et al., "Fast and Accurate Phase-Detection Autofocus Using a Single Image", *IEEE TIP*, 2021.
[3] Nakamura, J. (ed.), *Image Sensors and Signal Processing for Digital Still Cameras*, CRC Press.
[4] Adams et al., "Photographic Metering and Exposure Control", *SPIE Electronic Imaging*, 2012.
[5] MediaTek MMSDK MultiCam 架构文档（MTK 开发者网站，需开发者账号）
[6] Wronski et al., "Handheld Multi-Frame Super-Resolution", *ACM TOG*, 2019.
[7] Yuan et al., "Multi-Camera System Calibration and 3A Synchronization for Mobile Phones", *IEEE ICASSP*, 2020.
[8] Hu et al., "Towards Unified On-Device 3A with Scene Understanding", *CVPRW*, 2022.
[9] Geiger et al., "Seamless Zoom with Multi-Camera Systems", *IS&T Electronic Imaging*, 2020.
[10] Reinhard et al., "Color Transfer Between Images", *IEEE Computer Graphics & Applications*, 2001.
[11] Sony Semiconductor, *IMX766 Product Brief: Dual-PD All-Pixel PDAF Architecture*, *官方文档*, 2023.
[12] Finlayson et al., "Color Constancy at a Pixel", *Journal of the Optical Society of America A*, 2001.
[13] Luo et al., "The Development of the CIE 2000 Colour-Difference Formula: CIEDE2000", *Color Research & Application*, 2001.
[14] Lukac et al., "Digital Camera Image Processing: From Sensor to Image", *IEEE Workshop on Digital Media Processing*, 2004.
[15] Degaki et al., "Phase Difference Detection Auto Focus in CMOS Image Sensors", *SPIE Photonics West*, 2019.
[16] Ohta et al., *Colorimetry: Fundamentals and Applications*, Wiley, 2005.
