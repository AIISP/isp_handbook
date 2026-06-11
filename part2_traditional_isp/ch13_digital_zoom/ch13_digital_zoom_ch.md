# 第二卷第13章：数字变焦与图像重采样

> **流水线位置：** ISP 后处理阶段 — 色调映射之后，编码输出之前；数字变焦裁剪在 RAW 域或 YUV 域均可执行
> **前置章节：** 第二卷第04章（锐化）、第三卷第03章（超分辨率 DL 方法）、第二卷第22章（多摄融合）
> **读者路径：** 相机系统算法工程师、ISP 图像质量工程师、超分辨率算法研究员

---

## §1 原理 (Theory)

### 1.1 数字变焦 vs 光学变焦

光学变焦通过移动镜头组改变焦距，物理上改变成像倍率：焦距加倍、FoV 减半、被摄体在传感器上占的像素加倍，MTF 基本不变。数字变焦则是对图像直接裁剪后上采样，焦距和传感器都没动，高频信息没有增加，只是把像素放大了。

这个区别决定了两者的根本差距：数字变焦的 MTF 随倍数线性退化——$k$ 倍数字变焦后有效奈奎斯特频率从 $f_N$ 降到 $f_N / k$，高频细节是真实丢失的，不是插值方法可以完全找回的。超分算法能改善感知质量，但不能凭空恢复物理上没采到的信息。

**对比总结**：

| 特性 | 光学变焦 | 数字变焦 |
|------|---------|---------|
| 成像质量 | 无损（受光学设计限制） | 随倍数增加而下降 |
| 硬件成本 | 高（镜组机械结构） | 低（纯软件/DSP） |
| 体积重量 | 大（变焦镜头组） | 无额外成本 |
| MTF | 接近原生 | 随倍数降低 |
| 适用场景 | 高画质要求 | 便携、成本敏感 |

### 1.2 裁剪-上采样的基本实现

最简单的数字变焦流程：

1. **裁剪（Crop）**：从全分辨率图像中心（或用户指定区域）取 $W/k \times H/k$ 区域。
2. **上采样（Upscale）**：将裁剪区域放大回目标分辨率 $W \times H$。

数学表示：设原始图像 $I$（$W \times H$），$k$ 倍数字变焦后裁剪区域的坐标：

$$
x_{\text{crop}} = \frac{W}{2} - \frac{W}{2k},\quad y_{\text{crop}} = \frac{H}{2} - \frac{H}{2k}
$$

$$
w_{\text{crop}} = \frac{W}{k},\quad h_{\text{crop}} = \frac{H}{k}
$$

随后对裁剪区域 $I_{\text{crop}}$ 进行上采样：

$$
I_{\text{zoom}}(x, y) = \text{Upsample}\left(I_{\text{crop}},\ k\right)
$$

### 1.3 重采样滤波器

上采样的质量完全取决于重采样滤波器（Resampling Filter）的选择：

**双线性插值（Bilinear Interpolation）**：

对非整数坐标 $(x', y')$ 处的值由四个邻近像素线性加权：

$$
I(x', y') = (1-u)(1-v)I_{00} + u(1-v)I_{10} + (1-u)vI_{01} + uvI_{11}
$$

其中 $u = x' - \lfloor x' \rfloor$，$v = y' - \lfloor y' \rfloor$。

- **优点**：计算简单，无振铃（Ringing）。
- **缺点**：等效低通滤波器截止频率较低，上采样后图像模糊，高频细节损失明显。

**双三次插值（Bicubic Interpolation）**：

使用 4×4 邻域内 16 个像素，以三次样条核函数加权：

$$
h(t) = \begin{cases} (a+2)|t|^3 - (a+3)|t|^2 + 1 & |t| \leq 1 \\ a|t|^3 - 5a|t|^2 + 8a|t| - 4a & 1 < |t| < 2 \\ 0 & |t| \geq 2 \end{cases}
$$

通常取 $a = -0.5$（Keys 核，最常用 **[1]**）或 $a = -0.75$（更锐利的双三次变体）。注：Mitchell-Netravali（1988）**[2]** 使用独立的 B、C 参数体系（经典推荐值 $B = C = 1/3$），与单参数 $a$ 体系不能直接对应。

- **优点**：比双线性更锐利，边缘过渡更自然。
- **缺点**：仍有一定模糊，在强边缘处可能出现轻微振铃。

> **双三次 2× 变焦画质量化参考：** 在典型测试图（Kodak、BSD100 等基准）上，2× 数字变焦（裁剪中心 1/4 面积后双三次上采样至原分辨率）相比原始分辨率参考图，PSNR **约下降 2–3 dB**（典型范围，依图像内容而异：纹理丰富场景下降偏大，平滑区域偏小）。这也是超分辨率算法在 2× 任务上的改善空间——SRCNN 等早期 SR 方法相比双三次插值基线提升约 0.5–1.5 dB，EDSR/RCAN 等深度方法可提升约 2–3 dB，基本"填回"双三次损失（见第三卷第03章超分辨率）。因此对 2× 及以上数字变焦，超分辨率模块是恢复感知质量的有效手段；2× 以内变焦双三次画质损失通常 < 1 dB，人眼难以察觉。

**Lanczos 插值**：

以 $\text{sinc}$ 函数的加窗截断形式为核：

$$
L(x) = \begin{cases} \text{sinc}(x) \cdot \text{sinc}(x/a) & |x| < a \\ 0 & |x| \geq a \end{cases}
$$

其中 $\text{sinc}(x) = \sin(\pi x)/(\pi x)$，窗口参数 $a$ 通常取 2 或 3。

- **优点**：频率响应最接近理想低通滤波器，上采样结果最锐利，细节保留最多。
- **缺点**：计算量较大；在强对比度边缘（黑白分界）处可能出现振铃伪影（Ringing/Gibbs Effect）。

**三种滤波器频率响应对比**（截止频率为典型近似值，具体数值依定义方式和核参数而异）：

| 滤波器 | 通带平坦度 | 截止频率（典型近似） | 振铃风险 | 计算量 |
|--------|-----------|---------|---------|-------|
| 双线性 | 好 | 低（约 0.5 $f_N$） | 无 | 最低 |
| 双三次 | 好 | 中（约 0.7 $f_N$） | 低 | 中 |
| Lanczos-2 | 好 | 高（约 0.9 $f_N$） | 中 | 高 |
| Lanczos-3 | 好 | 最高 | 较高 | 最高 |

### 1.4 ISP Demosaic 层数字变焦

在高质量的 ISP 实现中，2× 以内的数字变焦可以在 Demosaic（去马赛克）阶段直接实现，而不是在后处理阶段做裁剪+上采样：

**原理**：Bayer RAW 传感器在 Demosaic 时可以针对目标输出分辨率计算插值系数，使得插值核的中心直接对应到裁剪区域的像素，避免了两次采样（先 Demosaic 到全分辨率再裁剪）引入的质量损失。

**优势**：
- 全像素利用（Full Pixel Utilization）：不浪费传感器的有效像素。
- 减少插值次数：单次插值优于两次插值的级联。
- 在 1.0× ~ 2.0× 变焦范围内质量接近光学变焦。

### 1.4b 基于MTF退化曲线的精确切换点计算

> **P1补充**：切换点的工程依据应来自MTF退化曲线，而非经验估算。

在多摄混合变焦系统中，主摄数字变焦的MTF随倍率 $k$ 退化，而长焦镜头本身的MTF存在物理基准值。两者在某个倍率 $k^*$ 处等效，这即是最优切换点。

#### MTF退化的解析近似

设主摄原生 MTF50 为 $M_0$（单位 lp/mm），$k$ 倍数字变焦后有效空间频率缩减，经双三次插值上采样后的 MTF50 近似为：

$$M_{\text{wide,DZ}}(k) = M_0 \cdot \frac{f_{\text{interp}}(k)}{k}$$

其中 $f_{\text{interp}}(k)$ 为插值滤波器的等效通带因子（双三次约 0.7，Lanczos-2 约 0.9）。实测中通常用以下经验公式拟合：

$$M_{\text{wide,DZ}}(k) \approx M_0 \cdot k^{-\alpha}, \quad \alpha \in [0.85,\ 1.05]$$

$\alpha$ 可从实测 MTF 数据中用最小二乘拟合得到。

#### 切换点计算

设长焦镜头在目标焦距的等效 MTF50 为 $M_{\text{tele}}$（在目标分辨率下，含数字变焦因子），最优切换点满足：

$$M_{\text{wide,DZ}}(k^*) = M_{\text{tele}}$$

$$k^* = \left(\frac{M_0}{M_{\text{tele}}}\right)^{1/\alpha}$$

**数值示例**：设 $M_0 = 3200\ \text{lp/mm}$，$M_{\text{tele}} = 1800\ \text{lp/mm}$（长焦等效），$\alpha = 0.95$：

$$k^* = \left(\frac{3200}{1800}\right)^{1/0.95} \approx 1.778^{1.053} \approx 1.83\times$$

即主摄 1.83× 数字变焦时MTF退化到与长焦等效——这是纯质量最优的切换点。工程上结合低照度（长焦进光量不足）和热稳定性约束，将切换点向后移至 2.0×～2.5×。

#### 照度修正切换点

在低照度场景（EV < $\text{EV}_0$），长焦端噪声显著，等效MTF进一步退化：

$$M_{\text{tele,low}}(\text{EV}) = M_{\text{tele}} \cdot \exp\!\left(-\frac{\text{EV}_0 - \text{EV}}{\Delta \text{EV}}\right)$$

其中 $\Delta \text{EV} \approx 1.5$（经验值）。将 $M_{\text{tele,low}}$ 代入上式，可得照度自适应切换点 $k^*(\text{EV})$，实现比固定阈值更精确的自适应策略。

---

### 1.5 混合变焦系统（Hybrid Zoom）

现代智能手机普遍配备多摄系统，通过主摄（广角）和长焦（Telephoto）摄像头的协同工作实现光学+数字变焦的无缝衔接：

**典型配置示例**（以某旗舰手机为例）：
- 主摄：等效 24mm，1/1.5" 传感器，26MP
- 长焦：等效 85mm，1/3.5" 传感器，12MP（~3.5× 光学）
- 超长焦：等效 230mm，1/4.4" 传感器，12MP（~10× 光学）

**变焦切换策略**：

$$
\text{Camera} = \begin{cases}
\text{主摄} & 1.0 \times \leq z < 2.5 \times \\
\text{主摄数字变焦 / 长焦数字变焦混合} & 2.5 \times \leq z \leq 4 \times \\
\text{长焦} & 4 \times \leq z < 8 \times \\
\text{长焦 + 数字变焦} & z \geq 8 \times
\end{cases}
$$

切换点附近使用双摄融合（Dual Camera Fusion）进行渐变过渡，避免视觉跳变。

**焦段切换迟滞（Switch Hysteresis）**：

仅使用单一切换阈值（如 $z = 2.5\times$）会在阈值附近产生"抖振"（Chattering）问题——用户将变焦倍率反复在 2.4× ~ 2.6× 之间微调时，系统会高频在主摄和长焦之间来回切换，画面出现明显的亮度/色彩跳变。

工程实现中必须引入**双阈值迟滞（Hysteresis Band）**：

$$
\text{切换逻辑} = \begin{cases}
\text{切换至长焦} & z > z_{\text{up}} \text{（如 2.8×）} \\
\text{切换至主摄} & z < z_{\text{down}} \text{（如 2.2×）} \\
\text{保持当前摄像头} & z_{\text{down}} \leq z \leq z_{\text{up}}
\end{cases}
$$

其中 $z_{\text{up}} > z_{\text{down}}$，迟滞带宽 $\Delta z = z_{\text{up}} - z_{\text{down}}$（典型值 0.4× ~ 0.8×）。迟滞带宽越大，切换越稳定，但在迟滞区间内数字变焦质量相对较差（强制使用单摄数字变焦）。

**照度自适应迟滞**：在低照度（EV < EV_threshold）下，长焦进光量不足，应整体上移切换阈值并扩大迟滞带：

```
if EV < EV_threshold:
    z_up   = default_z_up   * 1.4   # 推迟切入长焦
    z_down = default_z_down * 1.3   # 更积极地退出长焦
else:
    z_up, z_down = default_z_up, default_z_down
```

### 1.6 变焦过渡平滑（Zoom Locking）

在实时预览中，用户手动变焦时需要平滑过渡，防止画面抖动（Zoom Jitter）：

**变焦曲线平滑**：对变焦倍率 $z(t)$ 进行一阶低通滤波：

$$
z_{\text{smooth}}(t) = \lambda \cdot z(t) + (1 - \lambda) \cdot z_{\text{smooth}}(t-1)
$$

其中 $\lambda \in [0.1, 0.3]$（$\lambda$ 越小过渡越慢越平滑）。

**双摄切换过渡**：在主摄和长焦切换点附近，对两路图像进行 Alpha 混合：

$$
I_{\text{out}} = \alpha(z) \cdot I_{\text{telephoto}} + (1 - \alpha(z)) \cdot I_{\text{wide}}
$$

其中 $\alpha(z)$ 在切换点附近从 0 平滑变化到 1，过渡区宽度约 0.5×。

### 1.7 AI 超分辨率辅助数字变焦

AI 超分辨率（Super Resolution，SR）模型通过学习低分辨率到高分辨率图像的映射关系，补偿数字变焦带来的高频损失：

**典型网络架构**：
- ESRGAN（Enhanced Super-Resolution GAN）**[6]**：骨干网络为 **RRDBNet**（Residual-in-Residual Dense Block，残差中嵌套残差的稠密块结构），结合对抗损失与感知损失，输出感知质量高，是移动端SR的早期基准。
- RCAN（Residual Channel Attention Network）**[7]**：深度残差通道注意力网络，精度高，计算量较大；移动端部署时通常需要通道裁剪或量化压缩。
- Real-ESRGAN **[12]**：针对实际场景退化（噪声、压缩、模糊）的高阶退化管道训练，泛化性强，2021年在盲图像超分辨率领域成为事实基准。

**2024 年一步扩散模型 SR（One-Step Diffusion SR）**：

扩散模型（Diffusion Model）在图像超分辨率领域的最新突破是**一步推理**方法，解决了多步扩散（通常 50~1000 步）无法在移动端实时运行的瓶颈：

- **OSEDiff（2024）**[13]：One-Step Effective Diffusion for Real-World Image Restoration，通过变分评分蒸馏（VSD）将扩散过程压缩至单步，同时引入语义引导保留文本一致性，4× SR 在感知质量指标（LPIPS、DISTS）上超越 Real-ESRGAN。
- **AddSR（2024）**[14]：Accelerating Diffusion-based Blind Super-Resolution with Adversarial Diffusion Distillation，通过对抗扩散蒸馏将扩散推理步数大幅压缩，仅需 2~4 步即可达到 50 步扩散的质量，推理速度相比标准 DDPM SR 提升 10×。
- **SeeSR（2024）**[15]：Towards Semantics-Aware Real-World Image Super-Resolution，引入语义先验（CLIP 文本特征）指导 SR 网络，在人脸、文字等语义区域大幅减少"幻觉式"伪细节，更适合数字变焦拍摄人像场景。

**在数字变焦中的集成方式**：

$$
I_{\text{SR-zoom}}(k) = \text{SR-Model}\left(\text{Crop}(I, 1/k)\right)
$$

相比传统插值，SR 模型可将感知锐利度提升 1~2 倍，在 4×~10× 数字变焦下改善尤为明显。2024 年一步扩散方法进一步将 LPIPS 失真指标（越低越好）相比 GAN-SR 降低约 15~20%（即感知失真减小、感知质量提升），代价是约 1.5~3× 的推理延迟增加。

**主流 SR 方法移动端横向对比（4× Real-World SR 参考基准）**

| 方法 | 年份 | 推理步数 | 移动端延迟（720p, INT8）| LPIPS ↓（RealSR 基准）| 特点 |
|------|------|---------|----------------------|----------------------|------|
| Real-ESRGAN | 2021 | 1（GAN）| ~30–50 ms | 0.24 | 实际退化训练，量产基线 |
| SwinIR | 2021 | 1（回归）| ~80–120 ms | 0.27 | Transformer，精度高 |
| SeeSR | 2024 | 4–20（扩散）| ~200–400 ms | 0.18 | 语义引导，人脸细节优 |
| OSEDiff | 2024 | 1（蒸馏）| ~60–100 ms | 0.19 | 单步扩散，感知质量接近多步 |
| AddSR | 2024 | 2–4（蒸馏）| ~80–150 ms | 0.20 | 对抗蒸馏，速度/质量均衡 |

> 以上延迟和 LPIPS 为综合公开论文数据的近似估算值（论文中测试环境不统一），实际移动端推理时间需在目标 SoC 实测。LPIPS 越低表示感知失真越小（感知质量越好）。

**硬件约束**：移动端 SR 推理需 < 100ms（实时视频要求 < 33ms@30fps），通常采用量化（INT8）或轻量化网络（IMDN、A-ESRGAN-Tiny）。一步扩散 SR 在骁龙 8 Gen 3 NPU 上经 INT8 量化后可达 200~400ms（静态拍照可接受），2025 年有望进入实时视频 SR 应用。

**SR vs 传统插值的选择判据**：

并非所有数字变焦场景都应优先使用 SR 模型，工程上需根据以下维度综合判断：

| 判断维度 | 优先选传统插值 | 优先选 SR 模型 |
|---------|--------------|--------------|
| 变焦倍率 | < 2× | > 3×（尤其 ≥ 4×） |
| 实时性要求 | 视频预览（< 33ms） | 静态拍照（可等待 200ms+） |
| 场景内容 | 低纹理（天空、人脸局部）| 高频纹理（建筑、文字、树叶） |
| 输入质量 | 高 SNR（ISO < 400） | 高 ISO 或暗光（SR 兼顾去噪） |
| 画风要求 | 色彩准确、无幻觉细节 | 感知锐利度优先、可接受轻微幻觉 |

**关键权衡**：SR 模型通过训练数据的统计先验"幻觉式"生成高频细节（Hallucination），在人脸、建筑等语义化区域视觉效果出众，但对于无纹理参考的区域（如高 ISO 下的纯色背景）可能产生错误的纹理幻觉。SeeSR（§1.7）引入语义引导正是为了抑制非语义区域的幻觉。视频实时预览场景因帧间连续性要求，SR 产生的幻觉细节帧间不一致会导致闪烁，此时传统插值+锐化更稳定。

### 1.8 潜望式长焦系统（Periscope Zoom）

OPPO、小米、三星等厂商的旗舰长焦采用潜望棱镜折射光路，实现 5× ~ 10× 光学变焦同时保持手机厚度：

**潜望式光路原理**：入射光通过 45° 棱镜（Periscope Prism）折转 90°，沿手机长轴方向传播，驱动模组纵深大幅增加等效焦距。

**设计挑战**：
- OIS（Optical Image Stabilization）：潜望镜 OIS 需控制棱镜角度而非镜头平移，补偿带宽要求更高。
- 大光比场景：长焦端景深（Depth of Field，DoF）极浅，AF（自动对焦）精度要求严苛（误差 < 5μm）。
- 暗光：长焦端光圈通常为 F2.8 ~ F4.0，进光量不足，需 MFNR 补偿。

---

## §2 标定 (Calibration)

### 2.1 变焦 MTF 标定

不同变焦倍率下的 MTF 标定是评估数字变焦质量的基础：

**设备**：ISO 12233 分辨率测试图 **[8]**、平行光源、精密对焦台。

**步骤**：
1. 在每个变焦倍率（1×、2×、4×、8×、10×）下拍摄 ISO 12233 图卡，确保每次对焦精准。
2. 使用 imatest 或 MTFMapper 提取边缘 MTF 曲线。
3. 记录 MTF50（响应降至 50% 时的空间频率，单位 lp/mm 或 cy/px）。
4. 绘制 MTF50 vs 变焦倍率曲线，与光学变焦基准线对比。

**标定目标**：2× 数字变焦的 MTF50 不低于光学变焦 MTF50 的 70% 。

### 2.2 双摄对齐标定

混合变焦系统需标定主摄和长焦摄像头的相对位姿（Extrinsic Calibration）：

1. 使用棋盘格标定板，在不同距离（0.5m ~ 3m）分别拍摄主摄和长焦图像。
2. 计算旋转矩阵 $R$ 和平移向量 $t$（双目标定）：

$$
x_{\text{telephoto}} = K_T (R x_{\text{wide}} + t)
$$

3. 将标定结果存入 EEPROM，供变焦融合模块使用。
4. 验证：对齐误差应 < 2 像素（在 4× 变焦下）。

---

## §3 调参指南 (Tuning)

### 3.1 重采样滤波器选择建议

| 变焦倍率 | 推荐滤波器 | 理由 |
|---------|-----------|------|
| 1.0× ~ 1.5× | 双线性或双三次 | 倍率低，MTF 损失小，需避免振铃 |
| 1.5× ~ 3× | 双三次（$a=-0.5$） | 平衡锐利度与振铃风险 |
| 3× ~ 6× | Lanczos-2 | 需最大化锐利度补偿 MTF 损失 |
| 6× 以上 | Lanczos-3 + SR | 单纯插值已不足，需 AI 辅助 |

### 3.2 数字变焦与 SR 模块的切换点参数（工程联动缺口补充）

**工程联动缺口：** 章节 §1.7 讨论了 SR 辅助数字变焦，但没有说明在什么倍数下从纯裁剪+插值切换到 SR，以及高通和 MTK 的切换点参数叫什么。

**高通 Spectra 平台的 SR 切换参数：**

在 CamX 节点图（Node Graph）中，数字变焦 SR 的启停由 `DigitalZoom_SRThreshold` 控制，典型默认值为 2.0×（即 2× 以下用双三次插值，2× 以上触发 NPU-SR 节点）。该参数路径：`camxsettings.xml` → `<ZoomSREnableThreshold>`。低照度（EV 低于 `SRLowLightEVThreshold`，典型 4.0 lux）时 SR 自动降级回插值，因为低 SNR 图像上 SR 会放大噪声并产生幻觉纹理。参数对：

```xml
<!-- camxsettings.xml -->
<ZoomSREnableThreshold>2.0</ZoomSREnableThreshold>   <!-- 触发 SR 的最低数字变焦倍率 -->
<SRLowLightEVThreshold>4.0</SRLowLightEVThreshold>    <!-- 低于此 EV 值时关闭 SR -->
<SRMaxZoomRatio>10.0</SRMaxZoomRatio>                  <!-- SR 生效的最大倍率，超过此值退回 Lanczos -->
```

**MTK FeaturePipe 的 SR 切换参数：**

MTK Imagiq 的 AI-SR（AISR）通过 `CameraFeature_AISR_ZoomRatioTrigger` 控制启动倍率（NDD 文件），默认 2.5×。MTK 还提供 `AISR_QualityMode`（枚举：FAST/BALANCED/QUALITY），分别对应不同的推理精度和时延：

```
[AISR]
AISR_Enable                  = 1
AISR_ZoomRatioTrigger        = 2.5      # 触发倍率，低于此值用 Bicubic/Lanczos
AISR_LowLightISOThreshold    = 800      # ISO 超过此值关闭 AISR
AISR_QualityMode             = BALANCED # FAST(<50ms)/BALANCED(<100ms)/QUALITY(<200ms)
```

**切换点与 MTF 退化曲线的关联（见 §1.4b）：**

§1.4b 提供了基于 MTF 退化曲线的精确切换点计算方法。工程上的简化规则是：当数字变焦的 MTF50 退化到原生 MTF50 的 60%~70% 时即可触发 SR（因为 SR 能将感知 MTF50 拉回到约 80%~90%）。对双三次插值滤波器（$f_\text{interp} \approx 0.7$），退化 60% 对应 $k \approx 1.75$×；对 Lanczos-2（$f_\text{interp} \approx 0.9$），退化 60% 对应 $k \approx 2.25$×。这与高通/MTK 默认 2.0×~2.5× 的切换点在工程上吻合。

---

### 3.3 双摄切换点调优

切换点应避免在两种情况下触发：
- **主摄裁剪边缘**：主摄裁剪区域接近传感器边缘时光学质量下降（暗角增加），此时应提早切换到长焦。
- **低照度场景**：长焦进光量不足时，切换点应适当推迟（保留主摄 + 数字变焦的方案）。

**照度自适应切换策略**：

```
if EV < EV_threshold:  # 低照度
    switch_point = default_switch_point * 1.3  # 推迟切换
else:
    switch_point = default_switch_point
```

### 3.4 SR 模型参数

- **推理精度**：INT8 量化（相比 FP32 精度损失 < 0.5 dB PSNR，速度提升 3~4× ）。
- **Tile Size**：对大分辨率图像分块推理，典型 Tile 大小 128×128 ~ 256×256，Overlap 16~32 像素（防止块边界伪影）。
- **强度混合**：SR 模型输出与传统插值输出以权重混合，用于控制锐化强度：

$$
I_{\text{final}} = w_{\text{SR}} \cdot I_{\text{SR}} + (1 - w_{\text{SR}}) \cdot I_{\text{bicubic}}
$$

典型 $w_{\text{SR}} \in [0.6, 0.9]$。

---

## §4 伪影分析 (Artifacts)

### 4.1 锯齿（Aliasing）

**现象**：在高变焦倍率（> 4×）下，细密纹理（布料、砖墙、树叶）出现不规则的锯齿状纹路或摩尔纹（Moiré Pattern），即高频成分被低频成分混叠。

**原因**：裁剪操作使有效采样率降低，若裁剪图像中存在频率 $f > f_N / k$ 的成分，则采样不足产生混叠：

$$
f_{\text{alias}} = |f_{\text{signal}} - n \cdot f_s/k|
$$

**解决方案**：
- 在裁剪前对图像施加抗锯齿低通滤波（Anti-Aliasing Pre-Filter），截止频率设为 $f_N / k$。
- ISP 中可在 Demosaic 级数字变焦时自然引入适当的低通效果。

### 4.2 摩尔纹（Moiré Pattern）

**现象**：拍摄规则纹理（显示屏、织物）时，随变焦倍率变化出现周期性彩色干涉条纹，条纹频率和颜色随变焦倍率改变。

**原因**：场景纹理频率与传感器采样频率的差频产生低频干涉。数字变焦改变有效采样频率，改变了差频位置，使摩尔纹更突出。

**解决方案**：
- 低通预滤波（参考混叠解决方案）。
- 去摩尔纹滤波器（Demoire Filter）：在频域检测摩尔纹频率并选择性压制。

### 4.3 插值振铃（Interpolation Ringing）

**现象**：在高对比度边缘（如黑白交界处）旁边出现明暗条纹（Gibbs 现象），使边缘看起来"光晕"或"描边"。Lanczos 插值尤为明显。

**原因**：Lanczos 核的负旁瓣在边缘处产生过冲（Overshoot）：

$$
I_{\text{ringing}} = h_{\text{Lanczos}} * I_{\text{edge}} \neq I_{\text{ideal\_sharp\_edge}}
$$

**解决方案**：
- 对 Lanczos 核应用 Hann 或 Blackman 窗口函数抑制旁瓣。
- 对边缘区域（$|\nabla I| > T_{\text{edge}}$）局部降低 Lanczos 插值权重，改用双三次。
- Mitchell-Netravali 双三次核（$B=1/3, C=1/3$）在锐利度与振铃之间取得较好平衡。

### 4.4 细节损失（Fine Detail Loss）

**现象**：高变焦倍率后，原本清晰的纹理细节（发丝、远处文字）变得模糊，无法恢复。

**原因**：这是数字变焦的固有限制，非伪影——低于奈奎斯特频率的信息本就未被采样，任何插值算法均无法恢复。

**缓解方案**：
- AI SR 模型通过先验知识（学习到的自然图像统计规律）"幻觉式"补充高频细节（Hallucination），主观感知质量提升，但客观上无真实细节信息增益。
- 使用更高分辨率传感器增加冗余像素（如 50MP 传感器在 2× 变焦时相当于 12.5MP 光学变焦）。

---

## §5 评测方法 (Evaluation)

### 5.1 变焦 MTF 测试

**测量流程**：
1. 拍摄 ISO 12233 测试图卡，焦距固定，分别在 1×、2×、3×、4×、8× 下拍摄。
2. 使用 imatest SFR（Slanted Edge MTF）模块计算各倍率下的 MTF50。
3. 以光学变焦参考线（若有）归一化，绘制"变焦倍率 vs MTF50 百分比"曲线。

**合格标准**：
- 2× 数字变焦：MTF50 ≥ 原生 MTF50 × 0.70 
- 4× 数字变焦：MTF50 ≥ 原生 MTF50 × 0.45 
- 10× 数字变焦（含 SR）：MTF50 ≥ 原生 MTF50 × 0.35 

### 5.2 感知锐利度（Perceived Sharpness）

客观 MTF 与人眼感知锐利度不完全一致。使用 CPIQ（Camera Phone Image Quality）中的感知锐利度指标或 JNDs（Just Noticeable Differences）：

$$
\text{PS}(\text{zoom}) = \int_0^{f_N} W(f) \cdot \text{MTF}(f, \text{zoom}) \, df
$$

其中 $W(f)$ 为人眼视觉敏感度权重函数（CSF，Contrast Sensitivity Function）。

### 5.3 光学等效比较

对于混合变焦系统，评估"数字变焦 + AI SR"在 6× 倍率下与纯光学 6× 长焦的等效质量：

1. 拍摄同一场景，分别使用：主摄 6× 数字变焦（含 SR）和纯 6× 光学长焦。
2. 双盲主观评分（MOS），对比锐利度、细节、噪声三项。
3. 目标：数字变焦+SR 的综合 MOS 不低于纯光学变焦 MOS × 0.85。

### 5.4 变焦过渡平滑度测试

录制从 1× 到 10× 的连续变焦视频，分析：
- 切换点处的亮度/色彩突变（ΔL、ΔC）：应 < 5%。
- 画面抖动（相邻帧图像中心偏移）：应 < 3 像素。
- 主观平滑度 MOS：≥ 4.0 分（1-5 分制）。

---

## §6 参考代码 (Code)

### 6.1 多种重采样插值实现

```python
import numpy as np
import cv2
from enum import Enum
from typing import Tuple, Optional


class ResampleMethod(Enum):
    BILINEAR = "bilinear"
    BICUBIC  = "bicubic"
    LANCZOS  = "lanczos"


def digital_zoom(
    image: np.ndarray,
    zoom_factor: float,
    method: ResampleMethod = ResampleMethod.LANCZOS,
    center: Optional[Tuple[float, float]] = None,
) -> np.ndarray:
    """
    数字变焦：裁剪后上采样到原始分辨率。

    Parameters
    ----------
    image       : 输入图像，BGR 或 灰度，uint8
    zoom_factor : 变焦倍率（> 1 为放大），如 2.0 表示 2× 数字变焦
    method      : 重采样方法
    center      : 变焦中心的归一化坐标 (cx, cy)，范围 [0,1]，
                  None 时默认图像中心 (0.5, 0.5)

    Returns
    -------
    变焦后图像，尺寸与输入相同
    """
    if zoom_factor <= 1.0:
        return image.copy()

    H, W = image.shape[:2]

    if center is None:
        cx, cy = 0.5, 0.5
    else:
        cx, cy = center

    # 裁剪区域尺寸
    crop_w = W / zoom_factor
    crop_h = H / zoom_factor

    # 裁剪左上角坐标（确保不越界）
    x1 = int(np.clip(cx * W - crop_w / 2, 0, W - crop_w))
    y1 = int(np.clip(cy * H - crop_h / 2, 0, H - crop_h))
    x2 = int(x1 + crop_w)
    y2 = int(y1 + crop_h)

    cropped = image[y1:y2, x1:x2]

    # 上采样插值
    interpolation_map = {
        ResampleMethod.BILINEAR: cv2.INTER_LINEAR,
        ResampleMethod.BICUBIC:  cv2.INTER_CUBIC,
        ResampleMethod.LANCZOS:  cv2.INTER_LANCZOS4,
    }
    interp = interpolation_map[method]

    zoomed = cv2.resize(cropped, (W, H), interpolation=interp)
    return zoomed


def lanczos_kernel(x: np.ndarray, a: int = 3) -> np.ndarray:
    """
    Lanczos-a 核函数（1D）。

    Parameters
    ----------
    x : 采样位置数组
    a : Lanczos 参数（窗口半宽，通常取 2 或 3）

    Returns
    -------
    核值数组
    """
    result = np.zeros_like(x, dtype=np.float64)
    nonzero = np.abs(x) < a
    xn = x[nonzero]
    # sinc(x) * sinc(x/a)
    pi_x = np.pi * xn
    pi_xa = np.pi * xn / a
    result[nonzero] = (
        np.where(np.abs(xn) < 1e-10, 1.0, np.sin(pi_x) / pi_x) *
        np.where(np.abs(xn / a) < 1e-10, 1.0, np.sin(pi_xa) / pi_xa)
    )
    return result


def compute_mtf(
    image: np.ndarray,
    edge_direction: str = "horizontal",
    roi: Optional[Tuple[int, int, int, int]] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    使用斜边法（Slanted Edge Method）计算图像 MTF。

    Parameters
    ----------
    image          : 输入灰度图像（含有斜边的测试图卡）
    edge_direction : 边缘主方向，"horizontal" 或 "vertical"
    roi            : 感兴趣区域 (x, y, w, h)

    Returns
    -------
    frequencies    : 空间频率数组（cy/px，归一化）
    mtf            : 对应 MTF 值数组
    """
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float64)
    else:
        gray = image.astype(np.float64)

    if roi is not None:
        x, y, w, h = roi
        gray = gray[y:y+h, x:x+w]

    H, W = gray.shape

    # 沿边缘方向计算 ESF（Edge Spread Function，边缘扩展函数）
    if edge_direction == "vertical":
        # 对每行取均值，得到水平方向 ESF
        esf = gray.mean(axis=0)
    else:
        esf = gray.mean(axis=1)

    # ESF 求导得 LSF（Line Spread Function，线扩展函数）
    lsf = np.gradient(esf)

    # LSF 做 FFT 得 OTF，取模得 MTF
    n = len(lsf)
    otf = np.fft.fft(lsf, n=n * 4)  # 零填充提高频率分辨率
    mtf = np.abs(otf[:n * 2])
    mtf = mtf / (mtf[0] + 1e-9)  # 归一化

    frequencies = np.fft.fftfreq(n * 4)[:n * 2]
    frequencies = np.abs(frequencies)

    # 仅取 [0, 0.5] cy/px（奈奎斯特以内）
    valid = frequencies <= 0.5
    return frequencies[valid], mtf[valid]


class HybridZoomSystem:
    """
    混合变焦系统模拟（主摄 + 长焦双摄协同）。
    """

    def __init__(
        self,
        wide_equiv_fl: float = 24.0,   # 主摄等效焦距（mm）
        tele_equiv_fl: float = 85.0,   # 长焦等效焦距（mm）
        switch_zoom: float = 2.5,      # 切换倍率
        transition_width: float = 0.5, # 过渡区宽度（倍率）
    ):
        self.wide_fl = wide_equiv_fl
        self.tele_fl = tele_equiv_fl
        self.optical_ratio = tele_equiv_fl / wide_equiv_fl
        self.switch_zoom = switch_zoom
        self.transition_width = transition_width

    def get_blend_weights(self, zoom_factor: float) -> Tuple[float, float]:
        """
        返回主摄和长焦的混合权重 (w_wide, w_tele)。
        在切换点附近平滑过渡。
        """
        z_low = self.switch_zoom - self.transition_width / 2
        z_high = self.switch_zoom + self.transition_width / 2

        if zoom_factor <= z_low:
            return (1.0, 0.0)
        elif zoom_factor >= z_high:
            return (0.0, 1.0)
        else:
            t = (zoom_factor - z_low) / self.transition_width
            # 使用余弦平滑曲线
            alpha_tele = (1 - np.cos(np.pi * t)) / 2.0
            return (1.0 - alpha_tele, alpha_tele)

    def simulate_zoom(
        self,
        wide_frame: np.ndarray,
        tele_frame: np.ndarray,
        zoom_factor: float,
        output_size: Optional[Tuple[int, int]] = None,
    ) -> np.ndarray:
        """
        模拟混合变焦输出。

        Parameters
        ----------
        wide_frame  : 主摄原始帧
        tele_frame  : 长焦原始帧（已完成视角对齐）
        zoom_factor : 目标变焦倍率
        output_size : 输出尺寸 (W, H)，None 时与主摄同尺寸

        Returns
        -------
        混合变焦输出图像
        """
        H, W = wide_frame.shape[:2]
        if output_size is None:
            output_size = (W, H)

        w_wide, w_tele = self.get_blend_weights(zoom_factor)

        # 主摄数字变焦
        wide_zoomed = digital_zoom(wide_frame, zoom_factor, ResampleMethod.LANCZOS)
        wide_zoomed = cv2.resize(wide_zoomed, output_size)

        # 长焦数字变焦（相对于长焦自身焦距的倍率）
        tele_zoom = zoom_factor / self.optical_ratio
        if tele_zoom > 1.0:
            tele_zoomed = digital_zoom(tele_frame, tele_zoom, ResampleMethod.LANCZOS)
        else:
            tele_zoomed = tele_frame.copy()
        tele_zoomed = cv2.resize(tele_zoomed, output_size)

        # 混合
        if w_tele < 1e-3:
            return wide_zoomed
        elif w_wide < 1e-3:
            return tele_zoomed
        else:
            return cv2.addWeighted(wide_zoomed, w_wide, tele_zoomed, w_tele, 0)


def benchmark_zoom_quality(
    image: np.ndarray,
    zoom_factors: list = [1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0],
) -> dict:
    """
    对比不同插值方法在各变焦倍率下的质量指标。

    Parameters
    ----------
    image        : 参考图像（高质量，用作真值）
    zoom_factors : 待测变焦倍率列表

    Returns
    -------
    results : 字典，包含各方法各倍率的 PSNR 和感知锐利度指标
    """
    results = {}
    methods = [ResampleMethod.BILINEAR, ResampleMethod.BICUBIC, ResampleMethod.LANCZOS]

    for method in methods:
        method_results = []
        for z in zoom_factors:
            if z <= 1.0:
                method_results.append({'zoom': z, 'psnr': float('inf'), 'sharpness': 1.0})
                continue

            zoomed = digital_zoom(image, z, method)

            # 粗略锐利度：Laplacian 方差
            if zoomed.ndim == 3:
                gray = cv2.cvtColor(zoomed, cv2.COLOR_BGR2GRAY)
            else:
                gray = zoomed
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()

            method_results.append({
                'zoom': z,
                'sharpness': lap_var,
            })

        results[method.value] = method_results

    return results


if __name__ == "__main__":
    # 创建测试图像（模拟 ISO 12233 线条图卡）
    test_img = np.zeros((480, 640, 3), dtype=np.uint8)
    # 绘制垂直黑白条纹（测试 MTF）
    for x in range(0, 640, 16):
        test_img[:, x:x+8] = 255
    test_img = cv2.GaussianBlur(test_img, (3, 3), 0)  # 模拟光学模糊

    print("数字变焦质量基准测试")
    print("=" * 50)

    zoom_factors = [2.0, 3.0, 4.0, 6.0, 8.0]
    for method in [ResampleMethod.BILINEAR, ResampleMethod.BICUBIC, ResampleMethod.LANCZOS]:
        print(f"\n{method.value.upper()} 插值:")
        for z in zoom_factors:
            zoomed = digital_zoom(test_img, z, method)
            gray = cv2.cvtColor(zoomed, cv2.COLOR_BGR2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            print(f"  {z:.0f}× 变焦 | 锐利度（Laplacian Var）: {sharpness:.1f}")

    # 混合变焦系统示例
    hybrid = HybridZoomSystem(wide_equiv_fl=24.0, tele_equiv_fl=85.0, switch_zoom=2.5)
    for z in [1.0, 2.0, 2.5, 3.0, 4.0, 5.0]:
        w_wide, w_tele = hybrid.get_blend_weights(z)
        print(f"{z:.1f}× | 主摄权重: {w_wide:.2f}, 长焦权重: {w_tele:.2f}")
```

---

## §7 术语表（Glossary）

**数字变焦（Digital Zoom）**
通过裁剪图像中心区域再上采样到目标分辨率来模拟变焦效果的软件技术。k 倍数字变焦从原始 W×H 图像中裁剪中心 $W/k \times H/k$ 区域，有效像素数降为原来的 $1/k^2$，有效奈奎斯特频率降为 $f_N/k$。光学变焦通过改变焦距物理提升成像倍率，不损失分辨率；数字变焦通过插值补足分辨率，无法恢复上采样丢失的高频信息，MTF 随倍数增加而下降。

**重采样滤波器（Resampling Filter）**
上采样过程中在非整数坐标位置计算像素值的插值核函数。从计算效率和图像质量的权衡，常用三类：**双线性**（2×2邻域线性加权，最快，截止频率低约 $0.5f_N$，无振铃）；**双三次**（4×4邻域三次样条，中等，截止频率约 $0.7f_N$，Keys核 a=-0.5 最常用）；**Lanczos**（sinc×sinc窗，截止频率约 $0.9f_N$，保留高频最好，计算量最大，边缘有振铃）。截止频率值均为典型近似，依定义方式和核参数而异。

**双三次插值（Bicubic Interpolation）**
使用 4×4 共 16 个邻域像素以三次多项式核加权的插值方法。核函数通用形式：$h(t) = (a+2)|t|^3 - (a+3)|t|^2 + 1$（$|t| \leq 1$），参数 $a = -0.5$ 为 Keys（1981）经典值，$a = -0.75$ 为更锐利的变体。Mitchell-Netravali（1988）采用独立的 B、C 参数体系（经典推荐值 $B = C = 1/3$），不与单参数 $a$ 体系直接对应。双三次插值是图像处理软件的默认插值方法，在清晰度与振铃之间取得良好平衡。

**Lanczos 插值**
以 sinc 函数的加窗截断形式为核的高质量插值方法：$L(x) = \text{sinc}(x) \cdot \text{sinc}(x/a)$（$|x| < a$），其中 $\text{sinc}(x) = \sin(\pi x)/(\pi x)$，窗口参数 $a$ 通常取 2（Lanczos-2）或 3（Lanczos-3）。$a$ 越大，频率响应越接近理想低通滤波器，但计算量越大且振铃效应越显著。Lanczos 是 ISP 高质量数字变焦和图像缩放的首选算法，尤其在 3× ~ 10× 变焦范围内比双三次效果明显更好。

**混合变焦系统（Hybrid Zoom）**
多摄相机系统中，将主摄（广角）与长焦镜头协同工作实现光学+数字无缝变焦的方案。在各镜头的光学覆盖范围内使用光学变焦（无损），超过单镜头范围时切换到数字变焦或双摄融合（Dual Camera Fusion）。切换点附近通过 Alpha 混合（$I_\text{out} = \alpha(z) I_\text{telephoto} + (1-\alpha(z)) I_\text{wide}$）平滑过渡，避免视觉跳变。现代旗舰手机通常配备广角（等效24mm）、中焦（等效85mm）、超长焦（等效230mm）三镜头覆盖 1× ~ 10× 以上变焦范围。

**潜望式长焦（Periscope Zoom）**
通过 45° 棱镜将入射光折转 90° 沿手机长轴方向传播的长焦结构，可在手机厚度有限的条件下实现 5× ~ 10× 光学变焦。主要设计挑战包括：OIS（光学防抖）需控制棱镜角度而非镜头平移；长焦端景深极浅（DoF 极小），AF 精度要求严苛（误差 < 5μm）；大光圈受限（通常 F2.8 ~ F4.0），暗光需 MFNR 补偿。代表产品：OPPO Find X2 Pro（10× 潜望）、小米 12S Ultra（5× 潜望，等效 120 mm）。

**MTF50（50% 调制传递函数）**
调制传递函数（MTF）下降到 50% 时对应的空间频率（单位 lp/mm 或 cy/px），是评估镜头/ISP 分辨率的核心指标。数字变焦标定目标：2× 数字变焦的 MTF50 不低于等倍光学变焦 MTF50 的 70%。测量工具：imatest 或 MTFMapper 结合 ISO 12233 测试卡（倾斜边缘法）。MTF50 vs 变焦倍率曲线可直观展示数字变焦质量随倍率的退化规律。

**AI 超分辨率辅助变焦（SR-Assisted Digital Zoom）**
通过深度学习超分辨率（Super Resolution）模型补偿数字变焦高频损失的技术：$I_\text{SR-zoom}(k) = \text{SR-Model}(\text{Crop}(I, 1/k))$。代表网络：ESRGAN（对抗损失，感知质量高）、RCAN（轻量，移动端适用）、Real-ESRGAN（针对复合退化训练）。相比传统插值，SR 可将感知锐利度提升 1~2 倍，4× ~ 10× 变焦效果改善最为显著。移动端部署约束：推理延迟 < 100ms（视频实时 < 33ms@30fps），通常采用 INT8 量化或轻量化网络（IMDN、A-ESRGAN-Tiny）。

---

> **工程师手记：无缝变焦，用户看到的"顺滑"背后是多少工程的代价**
>
> **多摄切换瞬间的色调跳变，是用户录视频时最常投诉的场景之一。** 广角和长焦摄像头用的是不同的 sensor、不同的镜头，AWB 收敛到的白平衡增益通常差了 3–8%（尤其在混合光源下），AE target 也有偏差。两摄各自独立跑 3A，在 1× 切 2× 的帧上，颜色、亮度同时跳变，非常明显。行业标准解法是"切换前预对齐"：检测到即将切换（用户手指在触摸拉焦或 zoom ratio 过阈值），在切换前 10–15 帧启动 ISP 参数渐变，让主摄的 AWB gain 和 AE target 向辅摄方向靠拢；切换完成后辅摄继续独立跑 3A，但初始值已经接近稳态，不需要大幅收敛。苹果 ProRes 录像模式下的 multi-cam seamless zoom 是业内公认做得最好的，核心就是这个预对齐机制加上严格的帧同步。
>
> **纯数字变焦（裁剪+插值）在超过 2× 后分辨率损失已经非常明显，但用户接受的上限取决于显示屏。** 12MP 图像裁剪到 1/4 区域后只剩 3MP，插值回 12MP 的锐度损失等效于把相机分辨率降低了 4 倍——这在 6.7 英寸 OLED 屏幕上 100% 放大观看时肉眼可见。超分辨率（SR）模块在这里的作用是用学习到的高频先验知识"猜"出丢失的细节，典型 2× SR 能把感知锐度提升约 30–40%（基于 NIQE 评分），但在低纹理区域（天空、墙壁）仍有"过度平滑+振铃"的副作用。工程上通常在 1×–2× 范围内用光学变焦覆盖，2×–10× 用双摄视差 + SR，10× 以上才是纯数字变焦 + SR——让 SR 只在"有信息可以恢复"的信噪比条件下工作，而不是在已经全是噪声的 10× 裁剪图上做无效增强。
>
> **切换延迟（Switching Latency）是一个被忽视的工程指标。** 光学变焦切换需要启动辅摄 sensor、等待曝光稳定（通常 2–4 帧）、完成 3A 收敛（再等 3–5 帧），总计约 200–400ms。在这段时间里，画面要么卡帧、要么用纯数字变焦填充过渡帧。苹果 iPhone 15 Pro 的三摄 system 里，长焦摄像头保持常开状态（即使不在前景显示），始终维持 3A 收敛，这样切换延迟可以降到 1–2 帧（30–60ms），代价是长焦 sensor 的功耗始终开着（约增加 60–100mW）。这是一个典型的"功耗换体验"决策，低端机不值得这样做，旗舰机在合适。
>
> *参考：多镜头可见光相机变焦流畅性测量方法及应用，中国光学，2025；iResearch666《多摄变焦切换工程实践》腾讯云，2025；大话成像《手机多摄 seamless zoom 技术解析》公众号，2025。*

---

## 插图

![digital zoom quality](img/fig_digital_zoom_quality_ch.png)
*图1. 数字变焦画质退化示意图——不同变焦倍率下图像分辨率与锐度的退化对比（图片来源：Dong et al., IEEE TPAMI, 2016）*

![super resolution springer](img/fig_super_resolution_springer_ch.png)
*图2. 超分辨率技术综述框架图——单帧 SR、多帧 SR 和基于学习的 SR 方法分类与主要代表算法（图片来源：Keys et al., IEEE TASSP, 1981）*

![zoom algorithm comparison](img/fig_zoom_algorithm_comparison_ch.png)
*图3. 变焦插值算法对比——最近邻、双线性、双三次（Bicubic）、Lanczos 插值在图像边缘与纹理细节上的效果差异（图片来源：Mitchell et al., ACM SIGGRAPH, 1988）*



---
![computational zoom sensor](img/fig4_computational_zoom_sensor_ch.png)
*图4. 计算变焦传感器架构图——多摄变焦系统中广角/长焦摄像头 RAW 对齐、多帧融合与输出的协作流程（图片来源：作者自绘）*

![digital zoom pipeline](img/fig_digital_zoom_pipeline_ch.png)
*图5. 数字变焦处理流程图——从 RAW 裁剪到上采样插值、超分辨率增强的完整数字变焦 ISP 管线（图片来源：Turkowski et al., Graphics Gems, 1990）*

![super resolution framework](img/fig_super_resolution_framework_ch.png)
*图6. 深度学习超分辨率网络架构示意图——SRCNN/ESRGAN/RCAN 等代表性 SR 模型的网络结构与特征提取方式（图片来源：Zhang et al., RCAN, ECCV, 2018）*



---
![resolution vs zoom](img/fig_resolution_vs_zoom_ch.png)
*图7. 分辨率与变焦倍率关系曲线——光学变焦与数字变焦在不同倍率下的等效分辨率对比（图片来源：Wang et al., IEEE TIP, 2004）*

![zoom quality comparison](img/fig_zoom_quality_comparison_ch.png)
*图8. 变焦画质综合对比图——光学变焦、数字变焦裁剪与 SR 增强在 MTF50 和主观画质上的综合评估（图片来源：Dong et al., IEEE TPAMI, 2016）*

![zoom sharpness](img/fig_zoom_sharpness_ch.png)
*图9. 变焦锐度分析图——不同变焦算法在 Siemens Star 测试图上的 MTF 曲线与锐度衰减特性（图片来源：Wang et al., IEEE TIP, 2004）*

![computational zoom sensor](img/fig_computational_zoom_sensor_ch.jpg)
*图10. 数字变焦与传感器成像关系示意图——裁剪区域与等效焦距的关系，展示不同变焦倍率下传感器有效像素区域及对应等效焦距的变化（图片来源：作者自绘）*

---

## 习题

**练习 1（理解）**
双三次插值（Bicubic Interpolation）使用 4×4 邻域像素计算输出值，其核函数在频域表现为比双线性插值更宽的通带和更好的旁瓣抑制。

1. 从频率响应角度解释，为何双三次插值在放大图像时比双线性插值更清晰（MTF50 更高），同时又更容易产生振铃（ringing）伪影？
2. Lanczos 插值相比双三次插值的优势是什么？Lanczos-2 与 Lanczos-3 在通带宽度和旁瓣抑制上的差异如何影响图像放大质量？
3. 数字变焦（裁剪 + 上采样）与光学变焦在以下方面的根本差异：（a）奈奎斯特频率；（b）裁剪区域的像素总数；（c）信噪比（考虑传感器散粒噪声）。

**练习 2（计算）**
一个 4000×3000 像素的传感器，使用数字变焦 2× 进行裁剪缩放：

1. 裁剪区域的像素尺寸是多少（中心裁剪，保持宽高比）？
2. 裁剪后上采样回 4000×3000，等效的角分辨率损失是多少（以奈奎斯特频率的比值表示）？
3. 若同时开启 EIS（电子防抖）需要 10% 的额外裁剪余量，则 2× 数字变焦 + EIS 叠加后，实际的有效像素从原始 4000×3000 变为多少？（提示：EIS 裁剪在数字变焦裁剪后再叠加，计算等效裁剪比例）

**练习 3（编程）**
实现双三次插值图像放大：

- 输入：`image` — 形状 `(H, W)` 的 float32 灰度图，值域 [0, 1]；放大系数 `scale = 2.0`
- 输出：`upscaled` — 形状 `(int(H*scale), int(W*scale))` 的 float32 图像
- 要求：使用 `cv2.resize(image, dsize, interpolation=cv2.INTER_CUBIC)` 实现；对比 `INTER_LINEAR`（双线性）的 PSNR 差异（在合成下采样图像上测试）；输出两种方法的 PSNR 值

```python
import numpy as np
import cv2
# 输入: image (H,W) float32, scale=2.0
# 输出: upscaled_cubic (H*scale, W*scale) float32
#        upscaled_linear (H*scale, W*scale) float32
#        psnr_cubic, psnr_linear (floats)
```

**练习 4（工程分析）**
在高通 Spectra ISP 和 Camera HAL 中，数字变焦通过 `ANDROID_SCALER_CROP_REGION`（Android Camera2 API）控制裁剪区域，插值算法由 ISP 硬件固定执行（双三次）；EIS 补偿也在相同流水线中叠加额外裁剪。某工程师在启用 2× 数字变焦并同时开启 EIS 后，发现视频分辨率虽然仍为 1080P，但边缘锐度明显下降，比单独 2× 变焦时更模糊。

1. 定量分析 EIS 额外 10% 裁剪在 2× 数字变焦基础上叠加后，总的 FOV 损失比例，以及等效的"实际变焦倍数"是多少（考虑两次裁剪的乘积效应）？
2. 若 MTK 平台的 `EIS_MaxCropRatio = 0.12`（EIS 最大 12% 裁剪），开启 3× 数字变焦 + EIS 后，有效像素相比原始传感器分辨率减少了多少百分比？
3. 如何在 Camera HAL 层通过动态调整 `ANDROID_SCALER_CROP_REGION` 坐标，在变焦过程中实现平滑的 1×→3× 变焦过渡（而非跳变），并保证 EIS 区域不超出裁剪边界？

---

## 参考文献

[1] Keys, "Cubic convolution interpolation for digital image processing", *IEEE Transactions on Acoustics, Speech, and Signal Processing*, 1981.

[2] Mitchell et al., "Reconstruction filters in computer-graphics", *SIGGRAPH*, 1988.

[3] Turkowski, "Filters for common resampling tasks", *Graphics Gems*, 1990.

[4] Wang et al., "Image quality assessment: From error visibility to structural similarity", *IEEE Transactions on Image Processing*, 2004.

[5] Dong et al., "Image super-resolution using deep convolutional networks", *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 2016.

[6] Wang et al., "ESRGAN: Enhanced super-resolution generative adversarial networks", *ECCV Workshops*, 2018.

[7] Zhang et al., "Image super-resolution using very deep residual channel attention networks (RCAN)", *ECCV*, 2018.

[8] ISO, "ISO 12233:2017 — Photography — Electronic still picture imaging — Resolution and spatial frequency responses", *官方文档*, 2017.

[9] Fontaine et al., "Periscope camera system design considerations for smartphones", *Proceedings of SPIE Electronic Imaging*, 2021.

[10] Dong et al., "RCAN-it: Rethinking Image Super-Resolution Training", *arXiv:2201.11279*, 2022.

[11] Liang et al., "SwinIR: Image Restoration Using Swin Transformer", *ICCV Workshops*, 2021.

[12] Wang et al., "Real-ESRGAN: Training Real-World Blind Super-Resolution with Pure Synthetic Data", *ICCV Workshops*, 2021.

[13] Wu et al., "OSEDiff: One-Step Effective Diffusion Network for Real-World Image Super-Resolution", *NeurIPS*, 2024.

[14] Xie et al., "AddSR: Accelerating Diffusion-based Blind Super-Resolution with Adversarial Diffusion Distillation", *arXiv:2404.01717*, 2024.

[15] Wu et al., "SeeSR: Towards Semantics-Aware Real-World Image Super-Resolution", *CVPR*, 2024.
