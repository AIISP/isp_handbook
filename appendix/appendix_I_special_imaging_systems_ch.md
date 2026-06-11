# 附录 I — 特殊成像系统与高级色彩科学（Special Imaging Systems & Advanced Color Science）

> **说明**：本附录收录 6 个超越手机主流 ISP pipeline 核心课程的扩展专题，包含同色异谱与色彩恒常性、深度感知、光场相机、高光谱成像、无透镜成像和神经形态相机。
> 面向有研究方向需求的读者；手机 ISP 算法工程师可跳过本附录，或仅阅读与手机相关的对比说明。
> 原第一卷第11章至第16章迁入此处。

---

## I.0 同色异谱与色彩恒常性（Metamerism and Color Constancy）

> **原目录路径**：`part1_imaging_fundamentals/ch11_metamerism/`

人眼仅有三种视锥细胞（L、M、S），对宽波段光谱进行积分，将整条光谱压缩为三个标量响应。这种不可逆降维是同色异谱（Metamerism）的成因，使不同光谱分布可产生相同的视觉感知。

### I.0.1 三刺激值与同色异谱对

给定光源光谱 $E(\lambda)$、反射率 $R(\lambda)$ 和 CIE 色匹配函数 $\bar{x}, \bar{y}, \bar{z}$，三刺激值为：

$$X = k \int_{380}^{780} E(\lambda) R(\lambda) \bar{x}(\lambda) \, d\lambda, \quad Y = k \int_{380}^{780} E(\lambda) R(\lambda) \bar{y}(\lambda) \, d\lambda, \quad Z = k \int_{380}^{780} E(\lambda) R(\lambda) \bar{z}(\lambda) \, d\lambda$$

两块表面 $R_1(\lambda)$ 与 $R_2(\lambda)$ 在光源 $E_1$ 下构成同色异谱对的条件：$\Delta R = R_1 - R_2$ 位于 $\{E_1\bar{x}, E_1\bar{y}, E_1\bar{z}\}$ 张成空间的零空间（null space）中。

**同色异谱指数（MI）**：光源从 $E_1$ 切换至 $E_2$ 后两表面的 CIEDE2000 色差。MI < 1 为轻微，1–3 为中等，> 3 为严重（业界经验阈值）。

### I.0.2 ISP 工程影响

| 影响维度 | 具体表现 | 应对措施 |
|---------|---------|---------|
| **多光源 CCM 设计** | 同一传感器在 D65 下校准后，在 A 光（2856 K）下色差变大 | 多光源独立 CCM，按 AWB 估计的色温插值 |
| **Luther 条件** | 传感器光谱灵敏度若非色匹配函数的线性组合，则存在设备同色异谱 | 优化 CFA 滤光片设计；DNN 后校正 |
| **AWB 本质** | AWB 目标是在当前光源下令中性表面的三刺激值接近 D65 下的值 | 统计法/深度学习法估计光源色温 |
| **色彩恒常性** | 人脑自动补偿光源变化，相机不具备此能力 | CCM + AWB 联合优化；多光源验证 |

### I.0.3 色彩恒常性算法框架

色彩恒常性的任务：从图像 $\mathbf{I}$ 中估计光源色度 $\mathbf{e} = (e_R, e_G, e_B)$，再通过增益 $(1/e_R, 1/e_G, 1/e_B)$ 将图像归一化至标准光源。

经典方法对比：

| 方法 | 假设 | 公式 | 局限 |
|------|------|------|------|
| 灰世界（Gray World） | 全图 RGB 均值相等 | $e_c \propto \bar{I}_c$ | 场景颜色分布非均匀时失效 |
| White Patch Retinex | 最亮像素为白色 | $e_c = \max_p I_c(p)$ | 高光饱和、镜面反射干扰 |
| Gamut Mapping | 可行性色域约束 | MIP 求解 | 需预标定色域 |
| 深度学习（C5/NUS） | 数据驱动端到端 | CNN 回归 $e$ | 跨场景泛化需大量数据 |

**参考论文**：Finlayson et al., "Color by Correlation", ECCV 2000；Barron, "Convolutional Color Constancy", ICCV 2015；Afifi et al., "C5: Cross-Camera Convolutional Color Constancy", CVPR 2022

---

## I.1 深度感知（Depth Sensing）

> **原目录路径**：`part1_imaging_fundamentals/ch12_depth_sensing/`

深度感知技术为每个像素附加距离信息，生成深度图（Depth Map）或点云（Point Cloud）。手机、AR/VR、自动驾驶、工业质检均广泛使用。

### I.1.1 三大技术路线原理对比

#### 1. 飞行时间（Time-of-Flight, ToF）

主动光源（红外激光/LED）发射调制光脉冲，传感器测量光子往返时间计算距离：

$$d = \frac{c \cdot \Delta t}{2}$$

其中 $c$ 为光速，$\Delta t$ 为时间差。

**iTOF（间接 ToF）** 利用相位差而非直接计时：

$$d = \frac{c}{4\pi f} \cdot \phi$$

其中 $f$ 为调制频率，$\phi$ 为相位差（0–2π 对应距离量程）。主流方案（Sony IMX556、三星 dToF）采用 4 相位采样（0°/90°/180°/270°）消除背景光干扰。

**dToF（直接 ToF / 单光子 ToF）** 使用 SPAD（Single Photon Avalanche Diode）直接计数光子时间戳，精度更高（mm 级），代表产品：Apple LiDAR Scanner（iPhone 12 Pro+）、华为 P30 Pro 3D ToF。

#### 2. 结构光（Structured Light）

投影仪将已知图案（散斑/条纹/格雷码）投影到场景，相机拍摄变形图案后通过三角测量计算深度：

$$d = \frac{f \cdot B}{\Delta x}$$

其中 $f$ 为焦距，$B$ 为投影仪与相机基线距离，$\Delta x$ 为视差。

**散斑结构光**：Apple Face ID（TrueDepth 前摄）、Intel RealSense D415；不规则散斑图案对应性好，但室外阳光下信噪比低。

**主动立体结构光**：在被动立体基础上补充红外散斑辅助匹配，中近景精度高（0.5–3 m）。

#### 3. 双目立体视觉（Binocular Stereo Vision）

两个标定相机从不同视角同时拍摄，通过视差图计算深度（纯被动，无主动光源）：

$$d = \frac{f \cdot B}{disparity}$$

**算法流程：** 极线校正 → 代价计算（SAD/Census/MC-CNN）→ 视差优化（SGM/StereoSGBM）→ 深度转换

**代表实现：** OpenCV StereoSGBM、Middlebury benchmark、RAFT-Stereo（深度学习方案）。

#### 技术路线对比表

| 特性 | iTOF | dToF | 结构光 | 双目立体 |
|------|------|------|--------|---------|
| 测距范围 | 0.1–5 m | 0.1–30 m | 0.1–3 m | 0.3–∞ |
| 深度精度（1m处） | 1–5 mm | 0.5–2 mm | 0.5–2 mm | 3–10 mm |
| 室外表现 | 中等（背景光干扰） | 较好（SPAD滤波） | 差（太阳光淹没） | 优（被动） |
| 功耗 | 中（主动IR） | 高（SPAD阵列） | 高（投影仪） | 低（无主动光源） |
| 典型手机应用 | 后置深度辅助对焦 | 前置 Face ID / LiDAR | 前置人脸识别 | 多摄景深/3D重建 |
| 代表芯片/模组 | Sony IMX556、三星 VD6281 | Apple LiDAR | Prime Sense → Apple | 高通 CV-ISP |

### I.1.2 与传统 ISP 的差异

| 维度 | 传统 RGB ISP | 深度传感器 ISP |
|------|------------|-------------|
| 传感器输出 | Bayer RAW（辐照度） | 相位差图/时间戳（距离） |
| 处理目标 | 色彩还原、去噪、锐化 | 深度计算、噪声过滤、孔洞填充 |
| 噪声模型 | 光子散粒噪声 + 读出噪声 | 多路径干扰（multipath）、运动模糊（相位域） |
| 主要算法 | Demosaic、AWB、CCM | 相位解包（phase unwrapping）、置信度过滤、时域融合 |
| 输出格式 | YUV / RGB（8/10 bit） | 16-bit 深度图（单位 mm）+ 置信度图 |

### I.1.3 关键算法：相位解包与多路径抑制

**相位模糊（Phase Ambiguity）：** iTOF 单频调制存在距离量程限制（$d_{max} = c/(2f)$），超出量程的距离产生相位折叠。解决方案：双频调制（dual-frequency），用最大公约数扩展不模糊范围：

$$d_{unamb} = \frac{c}{2 \cdot GCD(f_1, f_2)}$$

**多路径干扰：** 光线在角落/镜面反射产生间接路径，使 ToF 像素接收到多条到达时间的混叠信号，导致深度系统性偏差（通常偏近）。抑制方法：振幅加权滤波、学习型多路径分离网络（如 Su et al., "Frequency-domain ToF Multipath Interference", ICCV 2021）。

### I.1.4 代表产品与论文

- **Apple LiDAR Scanner**：dToF + SPAD，用于 AR 场景重建（ARKit）、摄影夜景对焦
- **Microsoft Azure Kinect**：iTOF（1 MP@30 fps）+ RGB + 麦克风阵列，用于 Azure Spatial Anchors
- **Intel RealSense D435i**：主动红外立体视觉，机器人 SLAM 常用方案
- 论文：Gupta et al., "Phasor Imaging: A Generalization of Correlation-Based Time-of-Flight Imaging", ACM ToG 2015

---

## I.2 光场相机（Plenoptic Camera / Light Field Camera）

> **原目录路径**：`part1_imaging_fundamentals/ch13_plenoptic/`

光场相机在单次曝光中同时记录光线的**位置**和**方向**，实现拍摄后自由改变焦距和视角。

### I.2.1 基本原理

#### 光场理论

完整光场用 **Lumigraph / 4D 光场** 表示：

$$L(x, y, u, v)$$

其中 $(x, y)$ 是主透镜平面（空间坐标），$(u, v)$ 是微透镜平面（角度坐标）。每个微透镜捕获来自同一场景点的多个角度样本。

#### 微透镜阵列架构

- **Lytro Illum（MLA 型，一代光场相机）**：在传感器前放置 MLA（Micro-Lens Array），每个微透镜覆盖约 $k \times k$ 个像素（典型 $k = 11$–15），提供 $k^2$ 个角度样本，但空间分辨率降为 $N/k$
- **焦距堆叠型（Focused Plenoptic）**：将 MLA 放在离焦位置，可在空间分辨率和角度分辨率间灵活权衡

**空间-角度分辨率权衡公式：**

$$\text{角度分辨率} \times \text{空间分辨率} = \text{总像素数} / k^2$$

### I.2.2 重聚焦算法（Digital Refocusing）

从 4D 光场合成任意焦距的图像，称为**积分投影（Shift-and-Add Integration）**：

$$I_\alpha(x, y) = \frac{1}{|UV|} \sum_{u,v} L(x - \alpha u, y - \alpha v, u, v)$$

其中 $\alpha$ 为虚拟焦距参数：
- $\alpha = 0$：所有光线直接叠加（全聚焦图像）
- $\alpha > 0$：前景聚焦
- $\alpha < 0$：背景聚焦

**计算复杂度：** 朴素实现为 $O(N^2 \cdot k^2)$，FFT 加速后可达 $O(N^2 \log N)$（频域 shift-multiply）。

### I.2.3 与手机多摄的关系

手机多摄（双摄/三摄）本质上是**稀疏光场采样**，微透镜阵列则是**密集光场采样**：

| 特性 | 手机多摄 | 光场相机（MLA） |
|------|---------|-------------|
| 视角数量 | 2–4（宽/长/超广角） | $k^2$（典型 100–400） |
| 基线 | 大（5–20 mm） | 极小（μm 级 MLA 间距） |
| 深度估计精度 | 高（大基线） | 低（极小基线） |
| 重聚焦范围 | 有限（仅背景虚化） | 全场景任意 |
| 空间分辨率 | 各摄头全分辨率 | 降低至 $1/k$ |
| 计算成本 | 立体匹配 | 光场解码 + 投影积分 |

**手机双摄景深** 用大基线双目深度估计，仅支持背景虚化（前景/背景分离），不具备光场重聚焦能力。Lytro Illum 则可对任意平面重聚焦但空间分辨率仅约 4 MP（等效）。

### I.2.4 与传统 ISP 的差异

传统 ISP 处理单个 Bayer RAW 帧，光场相机的 ISP 需额外完成：

1. **MLA 标定**：确定每个微透镜中心位置（标定精度需 < 0.1 pixel）
2. **原始光场解码**：从传感器 RAW 提取 $(x, y, u, v)$ 四维阵列
3. **视差计算**：从多角度图像估计每像素视差
4. **重聚焦/全聚焦合成**：shift-and-add 或频域合成

### I.2.5 代表产品与论文

- **Lytro Illum（2014）**：最著名消费级光场相机，已停产；光场文件格式 `.lfp` 开源解析
- **Raytrix R5/R29**：工业级光场相机，用于工业检测和科研
- **Adobe Light Field Plugin**：Lytro 后期处理标准工具
- 论文：Ng et al., "Light Field Photography with a Hand-held Plenoptic Camera", Stanford Technical Report CSTR 2005-02
- 论文：Levoy et al., "Light Field Rendering", SIGGRAPH 1996

---

## I.3 高光谱成像（Hyperspectral Imaging）

> **原目录路径**：`part1_imaging_fundamentals/ch14_hyperspectral/`

高光谱传感器在数十至数百个连续波段同时采集图像，每像素输出完整的反射率光谱，实现"看见"颜色之外的材质信息。

### I.3.1 基本原理

#### 光谱维度定义

- **多光谱（Multispectral）**：4–20 个离散波段（如 R/G/B/NIR/SWIR），波段宽度 20–100 nm
- **高光谱（Hyperspectral）**：100–400+ 个连续波段，波段宽度 1–10 nm，覆盖可见光（400–700 nm）到近红外（700–2500 nm）
- **超光谱（Ultraspectral）**：1000+ 波段，主要用于气象卫星和实验室光谱仪

#### Bayer vs 高光谱 CFA

| 特性 | 传统 RGB Bayer | 高光谱传感器 |
|------|-------------|------------|
| 波段数 | 3（R/G/B） | 100–400 |
| 波段宽度 | ~100 nm（宽带） | 1–10 nm（窄带） |
| 空间分辨率 | 高（全像素） | 中低（多路复用） |
| 色彩表示 | CIE XYZ → sRGB | 反射率光谱 λ→R(λ) |
| 每像素数据量 | 1–2 字节 | 100–800 字节 |

### I.3.2 成像模式

#### 推扫模式（Pushbroom / Line Scan）

沿飞行/扫描方向逐行推进，每次采集一行像素的全光谱：

```
传感器：空间 × 光谱（2D 传感器）
输出：随时间积分成 空间 × 空间 × 光谱（3D 数据立方体）
```

**优点：** 信噪比高（长积分时间），光谱分辨率好
**缺点：** 需要相对运动，不适合静态场景，存在空间-时间配准误差
**应用：** 遥感卫星（Hyperion、AVIRIS）、工业传送带检测

#### 快照模式（Snapshot / Computed Tomography Imaging Spectrometer, CTIS）

单次曝光捕获 3D 光谱数据立方体（空间 × 空间 × 光谱）：

- **CASSI（Coded Aperture Snapshot Spectral Imager）**：编码孔径 + 色散棱镜，通过压缩感知重建
- **图像滤光片阵列（IMEC mosaic filter）**：在传感器上制备多带窄带滤光片阵列（类 Bayer），类似于多光谱版 Bayer 模式

**优点：** 无须运动，可拍摄动态场景
**缺点：** 空间-光谱分辨率权衡，重建算法复杂

#### 关键参数

| 参数 | 定义 | 典型值 |
|------|------|-------|
| 波段数（Bands） | 光谱采样数量 | 100–400 |
| 光谱分辨率（FWHM） | 单波段半峰全宽 | 1–10 nm |
| 空间分辨率 | 空间像素尺寸（GSD） | 1–30 m（卫星）；0.01–1 mm（工业） |
| 噪声等效反射率（NEdR） | 最小可检测反射率差 | 0.1–1%（优质系统） |
| 数据立方体大小 | 空间×空间×波段 | 512×512×200 ≈ 50 MB |

### I.3.3 与传统 ISP 的差异

传统 RGB ISP 以色彩还原为目标，高光谱 ISP 以**光谱定量精度**为目标：

| 处理步骤 | RGB ISP | 高光谱 ISP |
|---------|---------|----------|
| 暗场/增益校正 | BLC + PRNU | 每波段独立暗场、平场校正 |
| 去噪 | 2D 空间去噪 | 3D 空间-光谱联合去噪（条带噪声）|
| 几何校正 | 镜头畸变 | 色散校正（不同波段有不同空间偏移）|
| 辐射标定 | 白平衡（估算） | 绝对辐射标定（DN → 反射率，需定标板）|
| 输出 | 8/10-bit YUV/RGB | 16-bit 浮点反射率立方体 |

**条带噪声（Striping）** 是推扫式高光谱的典型伪影：探测器各列响应不均导致垂直条纹，需逐列增益-偏置校正（Moment Matching）。

### I.3.4 典型应用场景

| 应用领域 | 检测目标 | 关键波段 |
|---------|---------|---------|
| 食品安全检测 | 霉变、农药残留、异物 | 近红外 900–1700 nm |
| 医疗/皮肤科 | 黑色素瘤、氧合血红蛋白 | 可见光 500–900 nm |
| 农业遥感 | 植被指数（NDVI）、病虫害 | 红边 680–740 nm |
| 矿物勘探 | 矿物成分识别 | 短波红外 1400–2500 nm |
| 半导体检测 | 硅晶圆缺陷 | 近红外 1000–1600 nm |
| 艺术品鉴定 | 颜料成分、修复痕迹 | 全光谱 400–2500 nm |

### I.3.5 代表产品与论文

- **Specim FX10/FX17**：工业推扫式高光谱相机（400–1000 nm / 900–1700 nm）
- **IMEC mosaic 高光谱传感器**：快照式，可集成到手机形态设备
- **Headwall Photonics Nano-Hyperspec**：无人机载高光谱系统
- 论文：Bioucas-Dias et al., "Hyperspectral Unmixing Overview", IEEE JSTARS 2012
- 论文：Mäkinen et al., "Generalized Anscombe Transformation for Poisson-Gaussian Noise Model", Signal Processing 2013（高光谱去噪理论基础）

---

## I.4 无透镜成像（Lensless Imaging）

> **原目录路径**：`part1_imaging_fundamentals/ch15_lensless/`

无透镜相机用编码衍射光学元件（Diffuser、Phase Mask、Coded Aperture）替代传统镜头，消除笨重的光学系统，通过计算重建图像。极薄形态（< 1 mm）使其适用于可穿戴设备、生物医学内窥镜和隐形摄像机。

### I.4.1 基本原理

#### 前向成像模型

无透镜系统的成像过程为线性卷积：

$$\mathbf{y} = \mathbf{H} \mathbf{x} + \mathbf{n}$$

其中：
- $\mathbf{y}$：传感器测量值（RAW 图像）
- $\mathbf{H}$：点扩展函数（PSF）矩阵，由衍射光学元件决定
- $\mathbf{x}$：待重建的场景图像
- $\mathbf{n}$：传感器噪声

PSF 的形状由衍射掩模设计决定。传统相机 PSF 是尖锐的艾里斑，无透镜相机 PSF 是人工设计的**空间复用**图案（散斑/螺旋/格雷码）。

#### 三类无透镜架构

**1. 编码孔径（Coded Aperture）**
将透明/不透明孔径图案置于镜头位置，通过孔径编码实现光谱/深度多路复用。传统 X 射线天文望远镜（HETE-2）最早使用，现扩展至可见光。

**2. 散斑扩散器（DiffuserCam）**
Antipa et al. (2018) 提出将廉价磨砂玻璃散斑扩散器贴合传感器，形成平移不变 PSF（BCCB 矩阵结构），利用 FFT 加速重建：

$$\hat{\mathbf{x}} = \arg\min_x \frac{1}{2}\|\mathbf{y} - \mathbf{H}\mathbf{x}\|^2 + \lambda \text{TV}(\mathbf{x})$$

ADMM 求解，每步仅需 FFT 运算，复杂度 $O(N \log N)$。

**3. 相位掩模（Phase Mask）**
光刻制备亚波长相位结构（如菲涅耳透镜变体），控制光的相位而非振幅。FlatCam（Chan et al., 2016）使用 separable phase mask，使 PSF 在水平和垂直方向可分离，简化重建。

### I.4.2 重建算法对比

| 算法 | 复杂度（每步） | 收敛性 | 噪声鲁棒性 | 代表实现 |
|------|------------|-------|----------|---------|
| 直接逆滤波 | $O(N \log N)$ | 1 步 | 差（病态） | scipy.signal.deconvolve |
| 梯度下降 + TV | $O(N \log N)$/步 | 慢（百步+） | 中 | TF/PyTorch 手写 |
| ADMM | $O(N \log N)$/步 | 快（50步内） | 好 | DiffuserCam 开源代码 |
| 展开网络（Unrolled） | 固定前向传播 | 1次推理 | 优 | LearnedPrimalDual |

### I.4.3 PSF 工程设计原则

优良的无透镜 PSF 应具备：
1. **平移不变性（Shift-invariance）**：简化重建为卷积逆问题
2. **均匀频谱覆盖**：PSF 功率谱应尽量平坦（避免频谱空洞导致欠定）
3. **高自相关峰值旁瓣比（PSL ratio）**：减少互相关重建伪影
4. **对准容差**：掩模与传感器的微小对准误差不应导致 PSF 剧变

### I.4.4 与传统 ISP 的差异

| 维度 | 传统相机 | 无透镜相机 |
|------|---------|---------|
| 光学系统 | 多片玻璃镜组（5–10 mm 厚） | 衍射掩模（< 1 mm） |
| 传感器 RAW | 近似清晰图像（小 PSF） | 高度模糊/编码测量 |
| ISP 核心任务 | 色彩还原、去噪 | 计算重建（反卷积）|
| 实时性 | 实时（ASIC 流水线） | 受限（GPU/NPU 重建，百毫秒级）|
| 视场角 | 受镜头限制（通常 30–120°） | 可达 180°（取决于掩模设计）|
| 图像质量 | 专业摄影级 | 当前约 0.1–1 MP 等效 |

### I.4.5 适用场景与代表产品

**适用场景：**
- 超薄可穿戴相机（智能眼镜帧内集成）
- 医疗内窥镜（直径 < 1 mm）
- 昆虫复眼仿生传感器
- 科研：全息重建、X 射线/伽马射线成像

**代表产品与开源项目：**
- **DiffuserCam**（UC Berkeley）：[github.com/Waller-Lab/DiffuserCam](https://github.com/Waller-Lab/DiffuserCam)
- **FlatCam**（Rice University）：菲涅耳相位掩模无透镜相机
- **Rambus 像素阵列无透镜传感器**：商业化探索阶段

**代表论文：**
- Antipa et al., "DiffuserCam: Lensless Single-exposure 3D Imaging", Optica 2018
- Chan et al., "FlatCam: Thin, Lensless Cameras using Coded Aperture and Computation", IEEE TPAMI 2017

---

## I.5 神经形态相机（Neuromorphic / Event Camera）

> **原目录路径**：`part1_imaging_fundamentals/ch16_neuromorphic/`

事件相机（Event Camera / Dynamic Vision Sensor, DVS）是一种仿生传感器，每个像素独立监测局部亮度变化，仅在亮度超过阈值时异步输出事件，输出格式为稀疏异步事件流而不是同步全帧图像。

### I.5.1 基本原理

#### 事件生成模型

每个像素 $(x, y)$ 在时刻 $t$ 输出事件 $e = (x, y, t, p)$，当且仅当：

$$\log I(x, y, t) - \log I(x, y, t_{prev}) \geq C \cdot p$$

其中：
- $I(x, y, t)$：像素对数亮度
- $C$：对比度阈值（典型 0.1–0.5，可调）
- $p \in \{+1, -1\}$：极性（亮度增加 +1，减少 −1）
- $t_{prev}$：该像素上次触发事件的时间戳

事件流为**异步稀疏点云**，时间分辨率达微秒级（与帧率无关）。

#### 传统相机 vs 事件相机

| 特性 | 传统帧相机 | 事件相机 |
|------|---------|---------|
| 输出格式 | 帧（同步，全局快门/滚动快门） | 事件流（异步，稀疏）|
| 时间分辨率 | 帧率倒数（1/30–1/1000 s） | 微秒级（1–100 μs）|
| 动态范围 | 60–70 dB（典型） | 120–140 dB |
| 运动模糊 | 高速时明显 | 无（异步输出）|
| 数据量（静止场景） | 全帧（大） | 极少（几乎无事件）|
| 数据量（高速运动） | 全帧（固定） | 集中于运动区域（高）|
| 绝对亮度信息 | 有 | 无（仅变化量）|
| 功耗 | 高（固定帧率驱动） | 低（事件驱动，空闲时几乎无功耗）|

### I.5.2 事件数据处理方法

#### 事件帧表示（Event Frame）

最简单的预处理：将时间窗口 $[t_0, t_0 + \Delta t]$ 内的事件按极性累积成帧：

$$F(x, y) = \sum_{e \in \Delta t} p_e \cdot \delta(x - x_e, y - y_e)$$

缺点：丢失微秒级时间信息，但便于借用传统 CNN 处理。

#### 时间面（Time Surface）

记录每像素最近一次事件的时间戳（指数衰减加权）：

$$S(x, y) = \exp\left(-\frac{t - t_{last}(x,y)}{\tau}\right)$$

保留局部时序信息，适用于角点检测和光流估计。

#### 体素格（Voxel Grid）

将事件流量化到时间-空间体素格：

$$V(x, y, b) = \sum_{e: t_n(e)=b} p_e \cdot \delta(x-x_e, y-y_e)$$

其中 $b$ 为时间仓编号（类比视频的帧），是深度学习方法最常用的输入表示。

#### 脉冲神经网络（SNN）

直接处理异步事件流的天然框架，每个突触连接仅在事件到达时激活，能效极高。代表工作：EST（Event Spike Tensor）、Spiking ResNet。

### I.5.3 高速运动捕捉应用

事件相机的微秒时间分辨率使其成为高速运动捕捉的理想选择：

| 应用 | 帧相机限制 | 事件相机方案 |
|------|---------|----------|
| 高速乒乓球轨迹（> 300 km/h） | 运动模糊 | 事件轨迹直接重建 |
| 无人机高速飞行避障 | 延迟 33 ms（30fps） | < 1 ms 反应 |
| 角膜追踪（眼动仪） | 需专用高速相机（1000 fps） | 事件相机 @ 功耗 1/10 |
| 高速工业检测（> 1000 fps） | 帧存储带宽限制 | 稀疏事件流低带宽 |

### I.5.4 与传统 ISP 的差异

事件相机的数据处理流水线与传统 ISP 完全不同：

| 步骤 | 传统 ISP | 事件相机处理 |
|------|---------|-----------|
| 传感器读出 | 全局/滚动快门同步读帧 | 异步事件总线（AER协议）|
| 去噪 | 空间滤波（NLM/BM3D） | 事件去噪：邻域时间相关性过滤（孤立事件噪声）|
| 空间处理 | Bayer Demosaic | 事件帧/体素格生成 |
| 运动处理 | 光流（后处理） | 光流实时嵌入事件流（无帧间延迟）|
| 输出 | 图像帧 | 事件流 / 重建图像 / 光流场 |

事件相机不携带绝对亮度信息，无法用于测光、白平衡、色彩还原等传统 ISP 任务。混合相机（DAVIS，同时输出帧和事件）是过渡方案。

### I.5.5 关键算法：光流估计与图像重建

#### 事件光流

EV-FlowNet（Zhu et al., 2018）将事件帧输入 U-Net 型网络预测光流，在 MVSEC 数据集上首次验证事件相机光流可与传统 PWC-Net 媲美。

#### 视频重建（Events → Frames）

E2VID（Rebecq et al., 2019）使用循环神经网络（ConvLSTM）从事件流重建高动态范围视频帧，在 100+ dB 动态范围场景下显著优于传统帧相机。

### I.5.6 代表产品与论文

**代表传感器：**
- **DAVIS346**（iniVation）：帧+事件双模式，346×260 分辨率，广泛用于研究
- **Prophesee Metavision EVK4**：1 MP 事件传感器（1280×720），最高分辨率商用产品
- **Samsung DVS（动态视觉传感器）**：集成在三星部分旗舰手机辅助相机（运动检测辅助对焦）
- **Sony IMX636**：Sony 首款商用 QVGA 事件传感器，工业机器人应用

**代表论文：**
- Lichtsteiner et al., "A 128×128 120 dB 15 μs Latency Asynchronous Temporal Contrast Vision Sensor", IEEE JSSC 2008（DVS 原始论文）
- Gallego et al., "Event-based Vision: A Survey", IEEE TPAMI 2022（综述）
- Rebecq et al., "Events-to-Video: Bringing Modern Computer Vision to Event Cameras", CVPR 2019
- Zhu et al., "EV-FlowNet: Self-Supervised Optical Flow Estimation for Event-based Cameras", RSS 2018

---

## I.6 综合对比

| 特性 | 同色异谱/色彩恒常性 | 深度感知 | 光场相机 | 高光谱成像 | 无透镜成像 | 事件相机 |
|------|-----------------|---------|---------|----------|---------|---------|
| 捕获信息维度 | 光谱×3维 → 视觉感知 | 空间(2D) + 深度(1D) | 空间(2D) + 角度(2D) | 空间(2D) + 光谱(1D) | 空间(2D)（编码） | 空间(2D) + 时间（连续）|
| 主要应用 | AWB/CCM/颜色科学 | AR/人脸识别/自动驾驶 | 后期重聚焦/深度 | 食品/医疗/遥感 | 可穿戴/内窥镜 | 高速运动/机器人 |
| 与手机ISP关联度 | 极高（AWB/CCM核心） | 高（辅助对焦/景深） | 低（专业设备） | 低（NIR有限应用） | 极低（研究阶段） | 低（三星部分应用）|
| 计算重建需求 | 低（矩阵运算） | 中（深度后处理） | 高（4D光场解码） | 高（光谱解混） | 极高（反卷积重建） | 中（事件帧转换）|
| 商业成熟度 | 高（所有相机） | 高（手机普及） | 低（Lytro已停产） | 中（工业应用） | 低（研究阶段） | 中（工业起步）|

---

*本附录由第一卷第11章至第16章迁入并大幅扩充。原 ch11–ch16 目录下的 `_ch.md` 文件为详细章节版本，本附录为精简工程参考版。*

## 习题

**练习1（理解）** 从商业成熟度角度，本附录涵盖的 6 类特殊成像系统中，哪两类在手机 ISP 中已有实际应用？各举一个具体产品或应用场景。

**练习2（分析）** 光场相机（Lytro）的"先拍照后对焦"特性，在算法层面依赖什么核心数据结构？与 PDAF 的深度估计方法相比，光场相机的计算代价为何更高？

**练习3（工程分析）** 神经形态相机（事件相机）的输出是像素级事件流而非帧。试分析：将事件相机输出接入传统帧级 ISP 管线需要解决的主要技术挑战是什么？举一个可能的应用场景说明其相对于普通相机的优势。
