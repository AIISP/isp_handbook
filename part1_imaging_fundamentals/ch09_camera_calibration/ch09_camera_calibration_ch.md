# 第一卷第09章：相机标定（Camera Calibration）

> **定位：** 成像基础标定链路——为LSC、CCM、3D视觉提供标定数据；与第二卷第30章（ISP全流水线标定）互补。
> **前置章节：** 第一卷第02章（光学基础）、第一卷第03章（传感器物理）
> **读者路径：** 算法工程师、系统设计师

---

## §1 原理（Theory）

### 1.1 相机成像模型

相机标定本质上是确定"现实世界的三维点如何映射到传感器上的二维像素坐标"这一变换关系。最常用的模型是**针孔相机模型（Pinhole Camera Model）**，它把相机抽象为一个理想小孔，光线沿直线传播，不考虑透镜厚度和像差。

> **模型假设与物理现实：** 针孔模型是一个理想化的数学框架，定义了几何校正的目标。手机镜头实际上是多片厚透镜系统，存在有限孔径、像差、主光线角变化和传感器封装效应。在中等视场角（FoV < 90°）且单中心投影近似成立时，针孔模型配合畸变模型足以支撑工程精度需求。**ISP 中 LDC/GDC 模块的目标，是将传感器捕捉到的畸变图像通过逆映射"还原"成符合针孔模型的理想图像。** 对于超广角（> 110° FOV）和鱼眼镜头，单纯针孔 + Brown 畸变误差会明显上升，通常改用 Kannala-Brandt 等专用鱼眼投影模型（见 §1.3）。

整个成像过程分为三级坐标系变换：

1. **世界坐标系 → 相机坐标系**（外参，描述相机的位姿）
2. **相机坐标系 → 图像平面坐标系**（投影，描述透视缩放）
3. **图像平面坐标系 → 像素坐标系**（内参，描述传感器的物理参数）

引入**齐次坐标（Homogeneous Coordinates）**可以把上述三步用矩阵连乘统一表达。设世界坐标系中的三维点为 $\mathbf{X}_w = [X, Y, Z, 1]^T$，对应像素坐标为 $\mathbf{u} = [u, v, 1]^T$，则：

$$
s \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}
= \underbrace{\begin{bmatrix} f_x & s & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix}}_{\mathbf{K}}
\underbrace{\begin{bmatrix} \mathbf{R} & \mathbf{t} \end{bmatrix}}_{[\mathbf{R}|\mathbf{t}]}
\begin{bmatrix} X \\ Y \\ Z \\ 1 \end{bmatrix}
$$

其中 $s$ 是尺度因子（在像素坐标中可归一化掉），$\mathbf{K}$ 是**内参矩阵（Intrinsic Matrix）**，$[\mathbf{R}|\mathbf{t}]$ 是**外参（Extrinsic Parameters）**。

**相机坐标系到图像平面的投影**：设相机坐标系中的点为 $(X_c, Y_c, Z_c)$，焦距为 $f$，透视投影给出归一化像面坐标：

$$
x = \frac{X_c}{Z_c}, \quad y = \frac{Y_c}{Z_c}
$$

这一步丢失了深度信息，是不可逆的。

### 1.2 内参矩阵 K

内参矩阵 $\mathbf{K}$ 包含五个参数：

$$
\mathbf{K} = \begin{bmatrix} f_x & s & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix}
$$

各参数物理含义：

- **$f_x, f_y$（焦距，单位：像素）**：焦距 $f$（mm）除以像素尺寸 $p_x, p_y$（mm/pixel）得到。若传感器像素是正方形，$f_x = f_y$；但手机传感器因制造工艺，两者可能有轻微差异（通常小于 1‰）。
- **$c_x, c_y$（主点，Principal Point）**：光轴与传感器平面的交点，理论上在图像中心 $(W/2, H/2)$，实际因镜头组装偏心，会有数到十几个像素的偏移。
- **$s$（斜切参数，Skew）**：描述行列像素轴不垂直的程度。现代 CMOS 传感器几乎都是矩形像素，$s \approx 0$，标定时通常直接固定为 0。

工程上，$f_x, f_y$ 的典型值：手机广角镜头约 1000–2200 pixel，长焦镜头可达 5000 pixel 以上（以 12 MP, 4032×3024 分辨率为例）。

### 1.3 畸变模型

实际镜头不是理想针孔，存在**几何畸变（Lens Distortion）**。不处理畸变，直线会在图像里"弯曲"，后续的 3D 重建、AR 对齐都会引入系统误差。

**径向畸变（Radial Distortion）**：由透镜曲率不均匀引起，沿径向方向对称分布。枕形（Pincushion）畸变 $k > 0$，桶形（Barrel）畸变 $k < 0$。

$$
x' = x(1 + k_1 r^2 + k_2 r^4 + k_3 r^6)
$$
$$
y' = y(1 + k_1 r^2 + k_2 r^4 + k_3 r^6)
$$

其中 $r^2 = x^2 + y^2$，$(x, y)$ 是归一化像面坐标，$(x', y')$ 是加畸变后的坐标，$k_1, k_2, k_3$ 是径向畸变系数。

**切向畸变（Tangential Distortion）**：由透镜与传感器不完全平行引起（镜头组装倾斜）。

$$
x' = x + 2p_1 xy + p_2(r^2 + 2x^2)
$$
$$
y' = y + p_1(r^2 + 2y^2) + 2p_2 xy
$$

$p_1, p_2$ 是切向畸变系数，通常比 $k_1$ 小一个量级。

完整的畸变向量为 $\mathbf{d} = [k_1, k_2, p_1, p_2, k_3]$（OpenCV 默认顺序）。对手机镜头而言，**径向畸变是绝对主导项**，超广角尤为突出；切向畸变次之；高阶 $k_3$ 在超广角中不可忽略。

**薄棱镜畸变（Thin Prism Distortion）**：除 Brown-Conrady 基本项外，对于镜片偏心/倾斜精度要求严苛的高精度场景（多目对齐、SLAM），还需引入薄棱镜项 $s_1, s_2, s_3, s_4$：

$$x' = x + s_1(r^2 + 2x^2) + s_2 \cdot r^2, \quad y' = y + s_3(r^2 + 2y^2) + s_4 \cdot r^2$$

薄棱镜项描述镜片组装偏心/倾斜引起的非对称残差，在单相机拍照应用中通常可忽略（幅值 < 0.1 pixel），但在双目/三目立体匹配和 AR 对齐中残差不可忽视。OpenCV 的 `CALIB_THIN_PRISM_MODEL` 标志支持此参数。

**鱼眼/广角镜头的 Scaramuzza 模型**：当视场角超过 120°，传统多项式模型精度不够，需要用等距投影（Equidistant）或 Scaramuzza 的多项式反射模型，OpenCV 的 `fisheye` 模块实现了 Kannala-Brandt 模型：

$$
r(\theta) = k_1\theta + k_2\theta^3 + k_3\theta^5 + k_4\theta^7
$$

其中 $\theta$ 是入射光线与光轴的夹角，$r$ 是像面上的径向距离。

> **为何只有奇次项？** 投影函数 $r(\theta)$ 必须是奇函数，即满足 $r(-\theta) = -r(\theta)$（中心对称性：与光轴成 $+\theta$ 和 $-\theta$ 角入射的光线，应投影到像面中心的对称两侧，距离相同）。奇函数的泰勒展开只含奇次幂，因此 $\theta^2, \theta^4$ 等偶次项物理上不允许出现，强行加入会破坏中心对称性。

### 1.4 张正友标定法（Zhang's Method）

张正友（Zhengyou Zhang）2000 年提出 **[1]** 的平面标定板方法是目前最广泛使用的标定算法。其核心思路：

**单应矩阵（Homography）**：标定板是平面（令 $Z=0$），世界坐标退化为二维 $(X, Y)$。相机看到的标定板图像与标定板平面之间存在一个 $3\times3$ 的**单应矩阵 $\mathbf{H}$**（8 自由度）：

$$
s\begin{bmatrix}u \\ v \\ 1\end{bmatrix} = \mathbf{H} \begin{bmatrix}X \\ Y \\ 1\end{bmatrix},\quad \mathbf{H} = \mathbf{K}[\mathbf{r}_1\ \mathbf{r}_2\ \mathbf{t}]
$$

其中 $\mathbf{r}_1, \mathbf{r}_2$ 是旋转矩阵 $\mathbf{R}$ 的前两列。

**闭式解（Linear Initialization）**：用至少 4 对对应点，DLT 算法可线性求解 $\mathbf{H}$。拿到 $N$ 张不同姿态的标定板图像，就有 $N$ 个 $\mathbf{H}_i$。每个 $\mathbf{H}_i$ 对内参相关对称矩阵 $\mathbf{B} = \mathbf{K}^{-T}\mathbf{K}^{-1}$ 提供 **2 个线性约束**（利用旋转矩阵正交性），$\mathbf{B}$ 有 6 个元素但受整体缩放约束实际有 5 个自由度，因此 **理论最小张数为 $N \geq 3$**（共 6 个约束）。

> ⚠️ **理论最小值 vs 工程推荐值**：理论上 3 张图可线性求解，但这是无噪声理想情形。实际工程中角点检测误差、标定板平整度、视场覆盖不足等因素使得 3 张结果极不稳定。**工程推荐采集 10–20 张图**，覆盖不同距离（近/中/远）、不同倾斜角（±30° 以上）、标定板充分覆盖图像四角区域；姿态多样性比总张数更重要。

**非线性优化（Refinement）**：以闭式解为初值，用 Levenberg-Marquardt 算法最小化**重投影误差（Reprojection Error）**：

$$
\min_{\mathbf{K}, \mathbf{d}, \{R_i, t_i\}} \sum_{i=1}^{N} \sum_{j=1}^{M} \left\| \mathbf{m}_{ij} - \hat{\mathbf{m}}(\mathbf{K}, \mathbf{d}, R_i, t_i, \mathbf{M}_j) \right\|^2
$$

$\mathbf{m}_{ij}$ 是第 $i$ 张图像上第 $j$ 个角点的检测坐标，$\hat{\mathbf{m}}$ 是用当前参数的预测坐标，$\mathbf{M}_j$ 是标定板上角点的三维坐标。

### 1.5 多相机立体标定

双目相机（Stereo Camera）或多目系统除了各自的内参，还需要标定**外参**：相机之间的旋转 $\mathbf{R}$ 和平移 $\mathbf{t}$，以及描述对极几何的**本质矩阵 $\mathbf{E}$** 和**基础矩阵 $\mathbf{F}$**。

$$
\mathbf{E} = [\mathbf{t}]_\times \mathbf{R}, \quad \mathbf{F} = \mathbf{K}_2^{-T} \mathbf{E} \mathbf{K}_1^{-1}
$$

$[\mathbf{t}]_\times$ 是平移向量 $\mathbf{t}$ 的**反对称矩阵（skew-symmetric matrix）**：

$$
[\mathbf{t}]_\times = \begin{bmatrix} 0 & -t_z & t_y \\ t_z & 0 & -t_x \\ -t_y & t_x & 0 \end{bmatrix}
$$

$\mathbf{E}$ 的秩（rank）为 **2**（非退化情形，$\mathbf{t} \neq \mathbf{0}$），这是本质矩阵的必要代数条件：$\det(\mathbf{E}) = 0$ 且两个非零奇异值相等。$\mathbf{E}$ 和 $\mathbf{F}$ 满足**对极约束（Epipolar Constraint）**：

$$
\mathbf{m}_2^T \mathbf{F} \mathbf{m}_1 = 0
$$

左图中的点 $\mathbf{m}_1$，它在右图中的对应点必然落在一条直线（Epipolar Line）上，这是立体匹配加速的理论基础。

立体标定完成后，进行**立体校正（Stereo Rectification）**，使两个相机的图像行对齐（行对应关系成立），然后立体匹配只需逐行扫描，大幅降低计算量。

---

## §2 标定流程（Calibration）

### 2.1 标定板设计

标定板（Calibration Target）的选择直接影响角点检测精度。

**棋盘格（Checkerboard）**：最经典的方案，黑白方格的交叉点定义明确，亚像素精化成熟。缺点是需要人工辨别方向（旋转 90° 有对称性歧义），且在高光照下黑格可能饱和。方格建议尺寸：打印分辨率 ≥ 300 DPI，方格边长覆盖传感器视角的 3–5% 。

**ChArUco 板**：棋盘格 + ArUco 二维码的混合方案，每个方格内嵌独立 ID，即使部分遮挡也能鲁棒检测，且方向唯一确定，无需完整视野即可提取有效角点。在**需要应对部分遮挡或机器人自动化抓取的产线场景**中具有明显优势。经典棋盘格在角点精度上理论上略优（无 ArUco 纹理干扰），且算法成熟稳定；产线实际上两种方案均有应用，选择取决于具体的遮挡风险和精度要求。

**圆点阵列（Circle Grid）**：对称圆点或非对称圆点，圆心定位精度优于角点（拟合椭圆质心，理论上亚像素精度更高）。OpenCV 对应 `findCirclesGrid()`。

**工程要点**：
- 标定板需要**刚性、平整**，喷墨打印贴在纸板上误差大，推荐铝板烤漆或玻璃面板（平整度 < 0.1 mm ）。
- 方格尺寸已知且需精确量测，误差直接影响标定的尺度精度。
- 产线场景可以用 LED 背光透射板，亮度均匀、不受环境光干扰。

### 2.2 图像采集要求

采集质量直接决定标定结果的上限，后续算法无法弥补采集阶段的缺陷。

| 要求 | 推荐做法 |
|------|----------|
| 视场角覆盖 | 标定板角点覆盖整个图像区域（尤其四个角），不能集中在中心 |
| 姿态多样性 | 倾斜 ±30°、距离近中远各若干张，总张数 ≥ 20 |
| 图像清晰度 | 无运动模糊，对焦准确；手持拍摄请上固定支架 |
| 曝光 | 避免过曝（直方图不饱和），棋盘格黑白对比度足够 |
| 张数 | 20–50 张，更多未必更好；保证多样性比数量更重要 |

实际工程中经常犯的错误：所有图都是正面拍、都在同一距离，这样切向畸变和焦距的耦合无法分解，标定结果发散。

### 2.3 角点检测与亚像素精化

OpenCV `findChessboardCorners()` 先用快速角点检测定位初始位置，精度约 1 pixel。然后用 `cornerSubPix()` 做**亚像素精化（Sub-pixel Refinement）**：

在一个小窗口内，利用角点附近梯度场的约束，求解使梯度方向与到角点向量正交的最优位置：

$$
\sum_{\mathbf{q} \in W} (\nabla I(\mathbf{q}) \cdot (\mathbf{q} - \hat{\mathbf{c}})) = 0
$$

这本质上是个最小二乘问题，可以精确到 0.01–0.1 pixel。

```python
import cv2
import numpy as np

# 角点检测与亚像素精化示例
def detect_corners(img, pattern_size=(9, 6)):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    ret, corners = cv2.findChessboardCorners(
        gray, pattern_size,
        flags=cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
    )

    if ret:
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

    return ret, corners
```

### 2.4 OpenCV calibrateCamera 完整流程

```python
import cv2
import numpy as np
import glob
import os

def calibrate_camera(image_dir, pattern_size=(9, 6), square_size=25.0):
    """
    完整相机标定流程
    pattern_size: 棋盘格内角点数 (列, 行)
    square_size: 方格物理尺寸 (mm)
    """
    # 准备世界坐标系下角点坐标（标定板平面 Z=0）
    objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
    objp *= square_size  # 乘以实际物理尺寸

    obj_points = []  # 世界坐标系中的3D点
    img_points = []  # 图像坐标系中的2D点

    images = glob.glob(os.path.join(image_dir, '*.jpg'))
    img_size = None

    for fname in images:
        img = cv2.imread(fname)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_size = gray.shape[::-1]  # (width, height)

        ret, corners = cv2.findChessboardCorners(gray, pattern_size)
        if ret:
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            obj_points.append(objp)
            img_points.append(corners_refined)

    print(f"有效标定图像数: {len(obj_points)} / {len(images)}")

    # 执行标定
    # cv2.CALIB_RATIONAL_MODEL 使用有理数畸变模型（k4,k5,k6），适合广角
    # cv2.CALIB_FIX_K3 如果不需要 k3，可以固定为 0 防止过拟合
    flags = 0  # 默认使用 k1,k2,p1,p2,k3

    rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        obj_points, img_points, img_size,
        None, None, flags=flags
    )

    print(f"RMS 重投影误差: {rms:.4f} pixel")
    print(f"内参矩阵 K:\n{K}")
    print(f"畸变系数 dist: {dist.ravel()}")

    return K, dist, rvecs, tvecs, rms

def compute_reprojection_errors(obj_points, img_points, rvecs, tvecs, K, dist):
    """逐图计算重投影误差，用于质量分析"""
    errors = []
    for i in range(len(obj_points)):
        proj_pts, _ = cv2.projectPoints(obj_points[i], rvecs[i], tvecs[i], K, dist)
        err = cv2.norm(img_points[i], proj_pts, cv2.NORM_L2) / len(proj_pts)
        errors.append(err)
    return errors
```

### 2.5 标定质量验证

**重投影误差（Reprojection Error）**是最直接的标定质量指标：

- **RMS < 0.3 pixel**：优秀，可用于精密测量 
- **RMS 0.3–0.5 pixel**：良好，满足大多数视觉任务 
- **RMS 0.5–1.0 pixel**：勉强可用，建议重新采集 
- **RMS > 1.0 pixel**：标定失败，检查采集质量或检测算法 

逐张查看误差分布，如果某几张误差特别大（outlier），把这几张剔除后重新标定，往往效果改善显著。

---

## §3 调参（Tuning）

### 3.1 内参精度 vs. 畸变模型复杂度的权衡

畸变系数越多，理论上拟合越精确，但也越容易**过拟合（Overfitting）**：参数把采集噪声也拟合进去了，泛化到新图像时表现更差。

工程经验：

| 场景 | 推荐畸变模型 |
|------|------------|
| 手机主摄（FoV < 90°） | $k_1, k_2, p_1, p_2$（4参数） |
| 手机超广角（FoV 120°+） | $k_1, k_2, k_3, p_1, p_2$ 或 fisheye 模型 |
| 工业镜头（低畸变） | $k_1, p_1, p_2$（3参数） |
| 鱼眼镜头（FoV 180°+） | Kannala-Brandt（OpenCV fisheye） |

判断是否需要增加 $k_3$：用 $k_1, k_2$ 标定后，查看图像四角区域的残差，如果系统性偏差较大（>0.5 pixel），说明高阶项不足，加上 $k_3$。

```python
# 固定不用的参数，防止过拟合
flags_conservative = (cv2.CALIB_FIX_K3 |    # 固定 k3=0
                      cv2.CALIB_FIX_K4 |    # 固定 k4=0
                      cv2.CALIB_FIX_K5 |    # 固定 k5=0
                      cv2.CALIB_ZERO_TANGENT_DIST)  # 如果切向畸变可忽略
```

### 3.2 移动端相机标定的工程实践

**产线标定（Factory Calibration）**与**用户端在线标定（In-field Calibration）**策略不同：

- **产线**：控制环境（标准光源、固定支架、精密标定板），目标 RMS < 0.3 pixel。产线标定结果通常写入摄像头模组内的 **EEPROM**（可重复擦写，每颗模组独立存储内参、畸变系数、白平衡初值等），由 ISP 驱动在上电时读取。部分方案写入主板或 ISP 固件分区，而非模组 EEPROM。**OTP/eFuse 通常用于不可更改的传感器 ID、出厂增益补偿等一次性数据，不适合存储可能在维修后更新的相机标定参数。**
- **在线标定**：用户日常拍摄中自动收集关键帧，后台持续优化。主要用于补偿温漂、摔后机械偏移。精度要求稍低，RMS < 0.5 pixel 可接受。

**多帧融合**：同一款机型不同个体的 $f_x, f_y$ 差异通常在 ±1%，主点偏移可达 ±10 pixel，畸变系数 $k_1$ 差异 ±5% 。因此每台机器都需要独立标定，不能共用一组参数。

**遮挡和部分可见**：产线可能出现标定板被部分遮挡的情况，ChArUco 板比棋盘格更能应对。

### 3.3 温度/焦距依赖性处理

镜头的焦距随温度变化而漂移（热胀冷缩），在极端温度（-20°C 工业环境，或 70°C 高温车载场景）下，焦距变化可达 0.5–2%，足以影响精密测量任务。

**处理方案**：
1. 在多个温度点（如 -10°C, 25°C, 50°C）分别标定，建立 $f(T)$ 查表
2. 嵌入温度传感器读数，运行时插值
3. 变焦相机（Zoom Camera）需要在多个焦距档位分别标定

对于变焦镜头，内参是焦距 $l$ 的函数：$f_x(l), f_y(l), c_x(l), c_y(l), \mathbf{d}(l)$，通常用多项式拟合各档标定结果，在 zoom 挡之间插值。

---

## §4 伪影与误差（Artifacts）

### 4.1 畸变未校正导致的几何变形

最常见的问题：图像中直线变弯。手机超广角相机不做畸变校正，建筑物边缘会呈现明显的桶形弯曲；长焦相机则可能有枕形畸变。

影响下游算法的典型场景：
- **特征匹配**：SIFT/ORB 在畸变图像上提取的特征描述子，与校正后图像的描述子不一致，匹配率下降。
- **深度估计**：双目匹配假设行对齐（经过立体校正），但立体校正依赖精确的畸变参数，标定差则深度误差大。
- **增强现实（AR）**：虚拟物体叠加在畸变图像上，透视关系与现实不吻合，出现"漂移"感。

畸变校正后的图像会在边角出现黑色无效区域（因为校正后部分像素超出原图范围），可以用 `cv2.getOptimalNewCameraMatrix()` 裁剪。

### 4.2 标定板平整度不足引起的系统误差

标定板假设是完美平面（$Z=0$）。若标定板有翘曲，世界坐标和真实三维坐标不符，会引入系统误差。

**量化估计**：若标定板在 1000 mm 距离处有 1 mm 翘曲，对焦距的影响约为 $\Delta f / f \approx 1/1000 = 0.1\%$——看似很小，但对精密三角测量任务（要求亚毫米精度）已经不可忽视。

**检测方法**：用平面度仪或三坐标测量机（CMM）测量标定板实际平整度；或者拍多张在不同方位旋转的图像，若某些旋转方向残差系统性偏大，说明标定板有翘曲。

### 4.3 角点检测错误与重投影误差异常

**伪角点**：图像过曝、噪声大、焦距不够等原因，`findChessboardCorners()` 可能把非角点当角点检测到，或者角点排序错乱。症状：RMS 误差突然很大（>5 pixel），肉眼看误差分布图能发现一两个点离群很远。

**处理方法**：
1. 逐张可视化角点检测结果（用 `drawChessboardCorners()`），肉眼确认
2. 计算每张图的 per-image RMS，剔除 >2× 中位数的图像
3. 适当调整 `findChessboardCorners()` 的 flags 参数（`CALIB_CB_ADAPTIVE_THRESH` 对过曝有帮助）

**主点漂移**：若标定结果中主点 $c_x, c_y$ 偏离图像中心超过图像尺寸的 10%（如 400×300 分辨率图像中心在 (200, 150)，主点偏到 (230, 150)，偏移 15%），需要怀疑是否采集姿态多样性不足。

---

## §5 评测（Evaluation）

### 5.1 重投影误差统计

除了全局 RMS，更细致的分析包括：

```python
import matplotlib.pyplot as plt

def visualize_reprojection_errors(obj_points, img_points, rvecs, tvecs, K, dist):
    all_errors_x = []
    all_errors_y = []

    for i in range(len(obj_points)):
        proj_pts, _ = cv2.projectPoints(obj_points[i], rvecs[i], tvecs[i], K, dist)
        proj_pts = proj_pts.reshape(-1, 2)
        detected = img_points[i].reshape(-1, 2)

        errors = detected - proj_pts
        all_errors_x.extend(errors[:, 0].tolist())
        all_errors_y.extend(errors[:, 1].tolist())

    # 误差分布图
    plt.figure(figsize=(8, 8))
    plt.scatter(all_errors_x, all_errors_y, alpha=0.3, s=5)
    plt.xlabel('Error X (pixel)')
    plt.ylabel('Error Y (pixel)')
    plt.title('Reprojection Error Distribution')
    plt.axhline(0, color='r', linewidth=0.5)
    plt.axvline(0, color='r', linewidth=0.5)
    plt.axis('equal')
    plt.grid(True)
    plt.show()

    rms_x = np.sqrt(np.mean(np.array(all_errors_x)**2))
    rms_y = np.sqrt(np.mean(np.array(all_errors_y)**2))
    print(f"RMS_x: {rms_x:.4f} px, RMS_y: {rms_y:.4f} px")
```

**关注点**：
- 误差在 (0, 0) 附近对称分布，说明无系统性偏差
- $X$ 方向和 $Y$ 方向误差量级相近，$f_x \approx f_y$ 的相机应该如此
- 若某方向误差远大于另一方向，检查是否有行列方向的畸变建模不当

### 5.2 3D 重建精度验证

在已知物理尺寸的场景下，用标定后的相机估计长度，与真值比较：

**板格边长验证**：标定完成后，把标定板当测量对象，用 `solvePnP()` + 内参估计标定板的 6DOF 位姿，然后计算两个已知距离的世界坐标点的重投影距离，与真值比较，误差应 < 0.5%。

**双目基线验证**：立体标定后，用已知长度的刚性物体（如精密标尺），放在双目视野内，三角化得到两端的三维坐标，计算三维欧氏距离，与真值比较。

### 5.3 与 MATLAB Camera Calibrator 结果互验

MATLAB 的 Camera Calibrator Toolbox 是工业界和学术界的参考标准。两套结果互验是消除软件 Bug 的有效手段。

**主要参数对比**：

| 参数 | OpenCV 符号 | MATLAB 符号 | 注意事项 |
|------|------------|------------|----------|
| 焦距 | $f_x, f_y$ | `FocalLength(1), FocalLength(2)` | 单位相同（pixel） |
| 主点 | $c_x, c_y$ | `PrincipalPoint(1), PrincipalPoint(2)` | MATLAB 原点从 (1,1) 开始，OpenCV 从 (0,0) |
| 径向畸变 | $k_1, k_2, k_3$ | `RadialDistortion(1:3)` | 符号定义相同 |
| 切向畸变 | $p_1, p_2$ | `TangentialDistortion(1:2)` | MATLAB 默认不启用，需手动勾选 |

OpenCV 与 MATLAB 主点差异约 0.5 pixel（坐标原点不同导致），通常可以通过 $c_x^{OpenCV} = c_x^{MATLAB} - 0.5$ 转换（有争议，建议以实测为准）。

---

## §6 代码

完整的 Python 实现（包括标定、畸变校正、立体标定、可视化分析）见：

本章配套代码（见本目录 .ipynb 文件）

代码涵盖以下内容：
- 棋盘格角点检测与亚像素精化
- `cv2.calibrateCamera` 完整流程
- 重投影误差可视化（散点图 + 热力图）
- 畸变校正对比图（校正前后）
- 双目立体标定与校正
- 标定结果保存与加载（`.npz` 格式）

---

## §7 QE（量子效率）曲线实测标定

> **声明：本节内容基于 EMVA 1288 公开标准及学术文献，数值均为文献典型参考值，不涉及任何专有测量数据或内部测试结果。**

量子效率（Quantum Efficiency，QE）是传感器光电特性的核心参数，直接决定 ISP 标定链路中白平衡增益范围、色彩校正矩阵（CCM）的设计空间，以及各模块对光谱的响应特性。本节系统介绍 QE 曲线的物理含义、EMVA 1288 标准测量框架、实验流程、开源工具及其在 ISP 中的应用，供传感器评估与 ISP 算法设计参考。

---

### 7.1 QE 的物理定义与重要性

#### 7.1.1 物理定义

量子效率 $\text{QE}(\lambda)$ 定义为：在波长 $\lambda$ 处，**每个入射光子转换为一个光电子的概率**，取值范围 $[0\%, 100\%]$：

$$
\text{QE}(\lambda) = \frac{\text{产生的光电子数}}{\text{入射光子数}} \times 100\%
$$

更严格的工程定义（EMVA 1288 §5.6）：

$$
\text{QE}(\lambda) = \frac{\overline{\mu}_e}{\overline{\mu}_p(\lambda)}
$$

其中 $\overline{\mu}_e$ 为每像素平均光电子数，$\overline{\mu}_p(\lambda)$ 为每像素平均入射光子数。注意 QE 此处为整体光电转换效率，包含了光子穿过微透镜、彩色滤光片（CFA）、钝化层至硅层后的联合效率。

#### 7.1.2 典型 BSI vs FSI 传感器的 QE 对比

根据公开学术文献及供应商公开 datasheet 中的典型参考值：

| 波长 | BSI CMOS 典型 QE | FSI CMOS 典型 QE | 说明 |
|------|-----------------|-----------------|------|
| 400 nm（深蓝） | ~40% | ~25% | 蓝光吸收层较浅，BSI 优势明显 |
| 450 nm（蓝） | ~55% | ~38% | — |
| 550 nm（绿，峰值区） | ~70–80% | ~55–65% | BSI 峰值 QE 约 70–80%（文献典型值） |
| 650 nm（红） | ~60% | ~48% | — |
| 700 nm（深红） | ~50–55% | ~40–45% | — |
| 800 nm（近红外） | ~35% | ~28% | 硅的光吸收截面下降 |
| 900 nm（近红外） | ~12–18% | ~8–12% | 截止区，需 IR 滤光片控制 |

> **数据来源说明**：上表数值为基于公开文献（如 Fossum & Hondongwa 2014 IEEE JEDS、Innocenzi et al. 2016 SPIE、以及 OmniVision/STMicro 公开 white paper）整理的**典型文献参考值**，不代表任何具体产品的实测数据。

BSI（背照式）相对于 FSI（前照式）的 QE 优势源于：光子从芯片背面入射，无需穿过金属互连层，填充因子（Fill Factor）理论上接近 100%，蓝紫光（400–500 nm）提升最为显著。

#### 7.1.3 QE 曲线对 ISP 的影响

QE 曲线直接影响以下 ISP 标定参数：

1. **CCM 矩阵设计**：CIE xyz 色彩匹配函数与传感器光谱响应 $S(\lambda) = \text{QE}(\lambda) \cdot T_\text{CFA}(\lambda) \cdot L(\lambda)$ 的乘积决定传感器的色彩响应，进而影响 CCM 的设计空间和条件数。QE 在 R/G/B 通道的峰值比例决定三通道响应的相对强度。

2. **AWB 增益先验范围**：D65 光源下各通道平均响应之比的倒数即 AWB 增益的先验估计；QE 在蓝光区域较低（与绿、红通道的 QE 差异），意味着 B 通道增益通常最大（典型值 $G_B > G_G > G_R$，但具体值依赖 CFA 透射率和光源）。

3. **RAW 白平衡增益范围预估**：已知 QE(λ) 和典型 CFA 透射率，可以在不拍任何灰卡图的情况下，数值积分估算不同光源下的初始 AWB 增益范围，作为 3A 算法的先验初始化。

4. **LSC 与 QE 非均匀性**：传感器边缘像素因微透镜主光线角（CRA）与镜头出射主光线角不匹配，导致边缘有效 QE 下降（Vignetting 的传感器侧分量），是 LSC 标定中需要与镜头暗角分量区分的系统误差源。

---

### 7.2 EMVA 1288 标准测量框架

#### 7.2.1 标准概述

**EMVA 1288**（European Machine Vision Association Standard 1288）是工业相机传感器性能测量与表征的国际通用标准，目前有效版本为 EMVA 1288 Release 4.0（2021）。标准文档可从官方网站公开下载：

- 官方地址：https://www.emva.org/standards-technology/emva-1288/

EMVA 1288 涵盖：量子效率（QE）、读出噪声、满阱容量（FWC）、暗电流、线性度、动态范围等一整套传感器参数的标准化测量方法，是传感器数据手册中引用频率最高的规范之一。

#### 7.2.2 QE 测量核心方程

根据 EMVA 1288 §5.6，QE(λ) 通过**光子转移曲线（Photon Transfer Curve, PTC）**方法测量，核心推导如下：

**泊松光子统计与散粒噪声分离**：在均匀光场照射下，像素输出信号的均值 $\bar{\mu}_{DN}$ 和方差 $\sigma^2_{DN}$ 满足：

$$
\sigma^2_{\text{shot}} = \frac{\overline{\mu}_{DN}}{K}
$$

其中 $K$ 为系统整体增益（Overall System Gain，单位 $\text{e}^-/\text{DN}$），可通过 PTC 斜率独立测量。

**入射光子数计算**：设均匀照明下，像素面积为 $A_\text{pixel}$（$\text{m}^2$），曝光时间为 $t_\text{exp}$（s），像面辐照度为 $E_\lambda$（$\text{W/m}^2/\text{nm}$），单光子能量为 $E_\text{photon} = hc/\lambda$，则：

$$
\overline{\mu}_p(\lambda) = \frac{E_\lambda \cdot A_\text{pixel} \cdot t_\text{exp} \cdot \lambda}{h \cdot c}
$$

**QE 计算公式（EMVA 1288 §5.6）**：

$$
\boxed{\text{QE}(\lambda) = \frac{\overline{\mu}_{DN} / K}{E_\lambda \cdot A_\text{pixel} \cdot t_\text{exp} \cdot \lambda \;/\; (h \cdot c)}}
$$

展开为常用形式：

$$
\text{QE}(\lambda) = \frac{\sigma^2_{\text{shot}} \cdot K}{E_\lambda \cdot A_\text{pixel} \cdot t_\text{exp}} \cdot \frac{h \cdot c}{\lambda}
$$

其中：
- $h = 6.626 \times 10^{-34}\ \text{J·s}$（普朗克常数）
- $c = 2.998 \times 10^8\ \text{m/s}$（光速）
- $\lambda$：波长（m）
- $K$：系统增益（$\text{e}^-/\text{DN}$），由 PTC 独立标定
- $E_\lambda$：像面辐照度（$\text{W/m}^2$），由功率计测量
- $A_\text{pixel}$：单像素面积（$\text{m}^2$，已知）
- $t_\text{exp}$：曝光时间（s，已知）

> **系统增益 K 的独立标定**：$K$ 通过拍摄不同曝光量的图像对，计算 $\sigma^2_{DN}$ vs $\bar{\mu}_{DN}$ 的斜率（Photon Transfer Curve）独立获得，与 QE 测量解耦，是 EMVA 1288 框架的核心优势。

#### 7.2.3 测量所需设备清单

| 设备类型 | 功能描述 | 关键技术指标 |
|---------|---------|------------|
| **积分球（Integrating Sphere）** | 产生空间均匀的朗伯辐射场；内壁高反射涂层（硫酸钡或聚四氟乙烯）将所有入射光均匀漫射 | 均匀性 < ±1%（出口面），直径通常 10–30 cm |
| **单色仪（Monochromator）** | 从宽谱光源（卤素灯或氙弧灯）中选择特定波长，逐波长扫描 | 波长范围 380–1000 nm，半带宽（FWHM）≤ 5 nm |
| **标准功率计（Optical Power Meter）** | 绝对标定入射辐照度 $E_\lambda$；具备 NIST（或等效计量机构）溯源证书 | 绝对精度 ±0.5%，波长范围覆盖测量区间 |
| **光纤耦合器** | 将单色仪出口与积分球入口连接；减少杂散光 | 低衰减，覆盖 350–1100 nm |
| **温控夹具** | 保持传感器在稳定温度下测量，消除暗电流温度漂移 | 温度稳定度 ±0.5°C |
| **遮光暗箱** | 隔离环境杂散光干扰 | 光泄漏 < 1/10000 信号量 |

---

### 7.3 标定实验流程

> **方法论说明**：本节描述通用 QE 测量流程，基于 EMVA 1288 及公开学术文献的方法，不涉及任何具体传感器型号或内部测量数据。

**Step 1：搭建均匀光场**

将单色仪出口通过光纤耦合至积分球入口端口。积分球出口（光源端口）对传感器提供空间均匀的朗伯辐射。使用空间均匀性测试（扫描积分球出口面的辐照度分布）确认均匀性 $< \pm 2\%$（出口直径内）。

**Step 2：功率计标定入射光谱辐照度 $E(\lambda)$**

在每个测量波长下，用已知响应度 $R(\lambda)$（$\text{A/W}$ 或 $\text{V/W}$）的标准探测器（经计量机构溯源标定）放置在传感器位置，测量辐照度：

$$
E_\lambda = \frac{P_\text{meas}}{A_\text{det}} \quad [\text{W/m}^2]
$$

其中 $P_\text{meas}$ 为功率计读数（W），$A_\text{det}$ 为探测器有效面积（$\text{m}^2$）。此步骤建立波长-辐照度标定曲线 $E(\lambda)$，是 QE 绝对值精度的关键。

**Step 3：逐波长采集图像（380–1000 nm，步长 10 nm）**

将单色仪依次调至 380, 390, 400, ..., 1000 nm。在每个波长下：
- 设置传感器至线性工作区（避免饱和，信号约为满阱的 40–60%）
- 采集多帧图像（≥ 20 帧），用于统计平均和方差计算
- 同步记录曝光时间 $t_\text{exp}$

**Step 4：计算每个波长的平均 DN 值**

对每个波长下的多帧图像，计算感兴趣区域（ROI，通常为图像中心 100×100 像素以避免暗角）的均值和方差：

$$
\bar{\mu}_{DN}(\lambda) = \frac{1}{N_\text{frames}} \sum_{k=1}^{N_\text{frames}} \bar{I}_k(\lambda)
$$

$$
\sigma^2_{DN}(\lambda) = \text{Var}\left[\bar{I}_k(\lambda)\right] - \sigma^2_{\text{read}}
$$

其中 $\sigma^2_\text{read}$ 为读出噪声方差（通过暗帧独立测量），需从总方差中减去。

**Step 5：代入 EMVA 公式计算 QE(λ)**

将 Step 2 得到的 $E_\lambda$、Step 4 得到的 $\bar{\mu}_{DN}(\lambda)$、以及独立标定的系统增益 $K$，代入 §7.2.2 中的 QE 公式，逐波长计算：

$$
\text{QE}(\lambda) = \frac{\bar{\mu}_{DN}(\lambda)}{K} \cdot \frac{h \cdot c}{E_\lambda \cdot A_\text{pixel} \cdot t_\text{exp} \cdot \lambda}
$$

**Step 6：拟合平滑曲线（Savitzky-Golay 滤波）**

由于单色仪步长和测量噪声，原始 QE 点列存在高频波动。用 Savitzky-Golay 滤波器（窗口宽度 5–7 点，多项式阶数 3）平滑：

```python
from scipy.signal import savgol_filter
qe_smooth = savgol_filter(qe_raw, window_length=5, polyorder=3)
```

平滑后的曲线即为最终 $\text{QE}(\lambda)$ 标定结果，可导出为查找表（LUT）供 ISP 使用。

---

### 7.4 开源工具与仿真

#### 7.4.1 EMVA 1288 开源实现

**EMVACameraModel**（GitHub 开源）：提供 EMVA 1288 框架下传感器参数（QE、增益 $K$、读出噪声、FWC）的 Python 实现，可用于：
- 从实测 PTC 数据拟合系统增益 $K$
- EMVA 1288 标准报告自动生成
- 仿真不同 QE 曲线下的传感器信噪比（SNR）

仓库地址：https://github.com/EMVA1288/emva1288（MIT License）

**相关 Python 生态**：
- `colour-science`（https://www.colour-science.org/）：包含光谱积分、CIE 色彩计算、相机光谱响应建模等功能
- `numpy` / `scipy`：数值积分、曲线拟合
- `matplotlib`：QE 曲线可视化

#### 7.4.2 典型 BSI CMOS QE 曲线仿真代码

以下代码基于公开文献典型值，用高斯叠加近似 BSI/FSI CMOS 的 QE 光谱形状，仅用于教学演示和 ISP 算法原型验证，**不代表任何真实传感器测量数据**：

```python
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from scipy.interpolate import PchipInterpolator

# ========================================================
# 典型 BSI/FSI CMOS QE 曲线仿真
# 数据基于公开文献典型参考值（非真实测量数据）
# 参考：Fossum & Hondongwa (2014), EMVA 1288 典型示例
# ========================================================

wavelengths = np.arange(380, 1010, 10)  # 380–1000 nm，步长 10 nm

# ---- BSI 典型控制点（基于文献参考值）----
# 400nm≈40%, 450nm≈55%, 500nm≈68%, 550nm≈75%, 600nm≈70%,
# 650nm≈60%, 700nm≈50%, 750nm≈38%, 800nm≈25%, 900nm≈12%, 950nm≈5%
bsi_ctrl_wl  = np.array([380, 400, 450, 500, 550, 600, 650,
                          700, 750, 800, 850, 900, 950, 1000])
bsi_ctrl_qe  = np.array([ 28,  40,  55,  68,  75,  70,  60,
                           50,  38,  25,  18,  12,   5,   2]) / 100.0

# ---- FSI 典型控制点（基于文献参考值）----
# FSI 蓝光区明显低于 BSI，峰值约在 550–580nm
fsi_ctrl_wl  = np.array([380, 400, 450, 500, 550, 600, 650,
                          700, 750, 800, 850, 900, 950, 1000])
fsi_ctrl_qe  = np.array([ 15,  25,  38,  52,  62,  57,  48,
                           40,  30,  20,  14,   9,   4,   1]) / 100.0

# 使用 PCHIP 插值（保形，不产生龙格震荡）
bsi_interp = PchipInterpolator(bsi_ctrl_wl, bsi_ctrl_qe)
fsi_interp = PchipInterpolator(fsi_ctrl_wl, fsi_ctrl_qe)

qe_bsi = np.clip(bsi_interp(wavelengths), 0, 1)
qe_fsi = np.clip(fsi_interp(wavelengths), 0, 1)

# 加入模拟测量噪声（±1% RMS，仿真实验随机误差）
rng = np.random.default_rng(42)
qe_bsi_noisy = qe_bsi + rng.normal(0, 0.01, len(wavelengths))
qe_fsi_noisy = qe_fsi + rng.normal(0, 0.01, len(wavelengths))

# Savitzky-Golay 平滑（EMVA 建议后处理）
qe_bsi_smooth = savgol_filter(np.clip(qe_bsi_noisy, 0, 1), 5, 3)
qe_fsi_smooth = savgol_filter(np.clip(qe_fsi_noisy, 0, 1), 5, 3)

# ---- 可视化 ----
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 左图：BSI vs FSI QE 曲线
ax = axes[0]
ax.plot(wavelengths, qe_bsi_smooth * 100, 'b-', linewidth=2,
        label='BSI CMOS (典型文献值)')
ax.plot(wavelengths, qe_fsi_smooth * 100, 'r--', linewidth=2,
        label='FSI CMOS (典型文献值)')
ax.axvspan(380, 500, alpha=0.08, color='blue', label='蓝光区')
ax.axvspan(500, 600, alpha=0.08, color='green', label='绿光区')
ax.axvspan(600, 700, alpha=0.08, color='red', label='红光区')
ax.set_xlabel('波长 (nm)', fontsize=12)
ax.set_ylabel('量子效率 QE (%)', fontsize=12)
ax.set_title('典型 BSI vs FSI CMOS QE 曲线\n（文献典型参考值，非实测数据）',
             fontsize=11)
ax.legend(fontsize=10)
ax.set_xlim(380, 1000)
ax.set_ylim(0, 90)
ax.grid(True, alpha=0.3)
ax.set_xticks(np.arange(400, 1001, 100))

# 右图：BSI-FSI 差值（BSI 优势量化）
ax2 = axes[1]
delta_qe = (qe_bsi_smooth - qe_fsi_smooth) * 100
ax2.fill_between(wavelengths, 0, delta_qe, where=(delta_qe > 0),
                 alpha=0.6, color='steelblue', label='BSI 优于 FSI')
ax2.plot(wavelengths, delta_qe, 'steelblue', linewidth=1.5)
ax2.axhline(0, color='k', linewidth=0.8, linestyle='--')
ax2.set_xlabel('波长 (nm)', fontsize=12)
ax2.set_ylabel('ΔQEI BSI−FSI (%)', fontsize=12)
ax2.set_title('BSI 相对 FSI 的 QE 增益\n（蓝光区增益最显著）', fontsize=11)
ax2.legend(fontsize=10)
ax2.set_xlim(380, 1000)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('qe_bsi_fsi_comparison.png', dpi=150, bbox_inches='tight')
plt.show()

# ---- 打印关键波长 QE 值 ----
key_wls = [400, 450, 500, 550, 600, 650, 700, 800, 900]
print("\n关键波长 QE 参考值（文献典型值）：")
print(f"{'波长(nm)':<10} {'BSI QE(%)':<12} {'FSI QE(%)':<12} {'差值(%)':<10}")
print("-" * 44)
for wl in key_wls:
    idx = np.searchsorted(wavelengths, wl)
    bsi_val = qe_bsi_smooth[idx] * 100
    fsi_val = qe_fsi_smooth[idx] * 100
    print(f"{wl:<10} {bsi_val:<12.1f} {fsi_val:<12.1f} {bsi_val-fsi_val:<10.1f}")
```

---

### 7.5 QE 标定结果的 ISP 应用

#### 7.5.1 从 QE(λ) 推导 AWB 增益先验范围

对于光源 $L(\lambda)$（$\text{W/m}^2/\text{nm}$），CFA 通道 $c \in \{R, G, B\}$ 的传感器响应为：

$$
S_c = \int_{380}^{780} L(\lambda) \cdot \text{QE}_c(\lambda) \cdot T_c^{\text{CFA}}(\lambda) \cdot d\lambda
$$

其中 $T_c^{\text{CFA}}(\lambda)$ 为 CFA 第 $c$ 通道的透射率曲线（可从供应商公开光谱数据获取）。

AWB 增益先验为：

$$
g_c^{\text{prior}} \propto \frac{1}{S_c} \cdot S_G \quad \Rightarrow \quad g_R = \frac{S_G}{S_R},\quad g_B = \frac{S_G}{S_B}
$$

实用意义：在不拍灰卡的条件下，通过数值积分 $\text{QE}(\lambda)$ + $T_c^\text{CFA}(\lambda)$ + $L_{D65}(\lambda)$，可以预估 D65 标准光源下的初始 AWB 增益范围，作为 3A AWB 算法的先验约束（Gain Range Clipping），防止 AWB 收敛到错误极值。

典型 D65 光源下，BSI 传感器的通道响应比 $S_R : S_G : S_B$ 约为 $0.85 : 1.00 : 0.70$（数值视 CFA 设计而定），对应增益先验 $g_R \approx 1.18$，$g_B \approx 1.43$——这与工程中常见的 D65 AWB 增益分布一致，验证了 QE 驱动的先验估算的合理性。

#### 7.5.2 QE 不均匀性对 LSC 标定的影响

LSC（Lens Shading Correction）标定通常假设传感器各像素具有相同的响应，但实际上存在两类不均匀性：

1. **镜头暗角（Optical Vignetting）**：由镜头口径和渐晕效应引起，是 LSC 校正的主要目标。
2. **传感器主光线角效应（CRA Mismatch）**：边缘像素的有效 QE 因微透镜与主光线角不匹配而下降，属于传感器侧的非均匀性。

两者在 LSC 标定中**耦合叠加**，无法从单一平场图中分离。若已知传感器的 CRA vs QE 特性（来自 QE 标定或供应商公开数据），可建立先验模型，辅助将 LSC 增益表分解为光学分量和传感器分量，提高跨光源的 LSC 鲁棒性。

#### 7.5.3 多摄像头 QE 一致性验收

在多摄协同系统（主摄+超广角、主摄+长焦、前后摄融合）中，多个摄像头之间的 QE 差异会影响融合图像的色彩一致性。

工程验收标准（基于公开文献与 EMVA 1288 精度框架）：

$$
\Delta\text{QE}@550\text{nm} < 5\% \quad \Rightarrow \quad \text{同批次传感器验收通过}
$$

> 该 5% 阈值为工程上常引用的经验标准，源于业界对 AWB 后残余色偏 $<\Delta E_{ab}^* = 3$ 的容限要求，具体数值因产品规格而异，最终应以系统级 IQA 测试结果为准。

---

### 7.6 常见测量误差来源

| 误差类型 | 来源描述 | 典型量级 | 缓解方法 |
|---------|---------|---------|---------|
| **积分球均匀性** | 内壁反射不均匀，出口面辐照度存在空间分布梯度 | ±2–3% | 多点标定；增大积分球相对传感器的面积比；使用双端口积分球（监测端口实时校正） |
| **单色仪杂散光** | 单色仪光栅的高阶衍射或散射进入探测通道 | ±0.5–2% | 使用双单色仪（串联）；在 UV 端加长波截止滤片 |
| **暗电流贡献** | 长曝光或高温时热生成电子叠加信号，使 QE 高估 | ±0.5–1% | 测量前暗帧减除（Dark Frame Subtraction）；对比短曝光确认线性 |
| **温度漂移** | 传感器工作产热导致暗电流随时间增大；硅的带隙温度系数使响应红移 | ±1–2%（无温控） | 加温控夹具，等待传感器热稳定（≥10 min预热）；记录测量温度 |
| **功率计绝对标定** | 参考探测器的响应度绝对标定不确定度（NIST 溯源误差） | ±0.5% | 使用经认证计量机构溯源的参考探测器；定期重新送检 |
| **像素 PRNU** | 像素响应非均匀性（Photo Response Non-Uniformity）使 ROI 均值产生偏差 | ±0.3–1% | 选择中心小 ROI（100×100 px）；多帧平均；与平场图归一化 |
| **光纤偏振效应** | 光纤在特定波长下可能引入偏振态变化，影响积分球均匀性 | ±0.5–1%（UV端） | 使用多模保偏光纤；积分球内加散射元件 |

**综合测量不确定度**：将以上各项误差按照独立不确定度合成（RSS）：

$$
u_\text{total} = \sqrt{u_\text{sphere}^2 + u_\text{stray}^2 + u_\text{dark}^2 + u_\text{temp}^2 + u_\text{power}^2 + u_\text{PRNU}^2} \approx \pm 3\text{–}5\%
$$

这意味着在无温控、单端口积分球的基础实验室条件下，QE 绝对值的测量不确定度约为 ±3–5%（$k=2$，95% 置信区间），与 EMVA 1288 报告中典型的不确定度声明一致。

---

### 7.7 参考文献

[1] EMVA 1288 et al., "Standard for Characterization of Image Sensors and Cameras", *官方文档*, 2021. URL: https://www.emva.org/standards-technology/emva-1288/

[2] Fossum et al., "A review of the pinned photodiode for CCD and CMOS image sensors", *IEEE Journal of the Electron Devices Society*, 2014.

[3] Janesick et al., "Scientific Charge-Coupled Devices", *SPIE Press*, 2001.

[4] Holst et al., "CMOS/CCD Sensors and Camera Systems (2nd ed.)", *SPIE Press*, 2011.

[5] Bigas et al., "Review of CMOS image sensors", *Microelectronics Journal*, 2006.

[6] Innocenzi et al., "Quantum efficiency measurements of CMOS image sensors: Methodology and uncertainty analysis", *Proceedings of SPIE*, 2016.

---

[1] Zhang et al., "A flexible new technique for camera calibration", *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 2000.

[2] Bouguet et al., "Camera calibration toolbox for Matlab", *California Institute of Technology*, 2004.

[3] Kannala et al., "A generic camera model and calibration method for conventional, wide-angle, and fish-eye lenses", *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 2006.

[4] Hartley et al., "Multiple View Geometry in Computer Vision (2nd ed.)", *Cambridge University Press*, 2004.

[5] Scaramuzza et al., "A toolbox for easily calibrating omnidirectional cameras", *IEEE/RSJ IROS*, 2006.

## §8 ISP 传感器基础标定（BLC / LSC / CCM / AWB / 线性度 / 噪声 / 坏点）

> 本节聚焦于移动 ISP 产线和工程调试中实际执行的传感器基础标定，与 §2（几何标定）是正交的标定链路。几何标定处理"光线走哪里"，本节处理"光子转换到数字值时的误差、不均匀性和颜色失真"。

---

### 8.1 黑电平标定（BLC Calibration）

**物理背景：** CMOS 传感器在完全遮光条件下仍有暗电流（Dark Current）和读出噪声偏置，使得 ADC 输出的"零信号"不为零，而是一个与增益、温度相关的正偏置量，称为黑电平（Black Level, BL）。不校正黑电平，后续所有信号处理的基准线偏移，AWB、CCM 和噪声模型都会失准。

**标定流程：**

1. 在完全遮光条件下（镜头加盖、或传感器进入光学黑区 OB 行读出模式）拍摄暗帧序列，通常覆盖：
   - 所有工作增益档（ISO 100 / 200 / 400 / 800 / 1600 / 3200 / 6400）
   - 多个曝光时间（最短：1/30000 s，最长：1/30 s，中间选 3–5 档）
   - 室温标定（25°C），高温（50°C）补充标定
2. 对每个（Gain, ET）组合下的暗帧，按四通道（R / Gr / Gb / B）分别计算均值和方差：

$$\text{BL}_{c}(g, T_{\text{exp}}) = \frac{1}{N} \sum_{i} \text{RAW}_{c,i}, \quad c \in \{R, Gr, Gb, B\}$$

3. 拟合黑电平随增益的线性关系（高增益下偏置增加）：

$$\text{BL}(g) = a_0 + a_1 \cdot g$$

4. 若存在明显温度漂移，建立温度补偿表 $\text{BL}(g, T)$，由 ISP 寄存器 `BLC_TEMP_TABLE` 索引（高通 Chromatix）或 `AE_BLC_gain_temperature_table`（联发科 NDD 格式）。

**平台配置：**

| 平台 | 参数名 | 写入位置 |
|------|--------|---------|
| 高通 Spectra | `BLC_R / Gr / Gb / B`（per-channel 14-bit offset） | Chromatix `.bin` → `BlackLevelCorrectionModule` |
| 联发科 Imagiq | `BLC_OFFSET_R/G/B`，支持 per-frame 动态更新 | `module_nvram.xml`，通过 NDD 噪声数据关联 |
| 海思/华为 | `OBOffset_R/Gr/Gb/B`，麒麟 ISP 支持 OB 行实时统计（无需 LUT）| `isp_blc.json`，越影 HAL 驱动读入 |
| 苹果（推测） | BLC 硬件化：A 系芯片传感器接口直接在硬件路径中减去 OB 统计均值，用户不可配置单独 BLC 参数 | — |

**验收指标：** 校正后暗帧四通道均值偏差 < ±1 DN（12-bit），通道间一致性 < 2 DN，Gr/Gb 通道差异（Green Imbalance）< 1 DN。

---

### 8.2 坏点标定（DPC / BPC Calibration）

**物理背景：** 传感器制造工艺缺陷导致少量像素响应异常：热像素（Hot Pixel，永远亮）、死像素（Dead Pixel，永远暗）或粘滞像素（Stuck Pixel）。手机传感器 1.0 µm 像素下，200 MP 传感器允许静态坏点数通常 < 200 个（出厂规格），高增益暗场中动态热像素可能更多。

**标定流程：**

1. **静态坏点图生成**：
   - 在标准增益（×1, ×4, ×16）下分别拍摄 4–8 帧暗帧（遮光），帧间取均值消除随机噪声
   - 计算每个像素与同色通道邻域中值的差异 $\Delta_{ij} = |P_{ij} - \text{median}(N_{ij})|$，超过阈值 $T_{\text{hot}}$（典型 10–15 DN @ 12bit）的像素标记为热像素
   - 拍摄均匀平场（全白），同样统计偏暗像素（Dead Pixel）：$P_{ij} < \mu_{\text{neighbor}} - T_{\text{dead}}$

2. **坏点坐标列表写入 EEPROM/OTP**：
   - 格式：`(row, col, type)` 三元组列表，每颗模组独立存储
   - 高通 Chromatix：`DPC_Static_Defect_Map`，最多支持 2048 个静态坏点
   - 联发科：`PDAF_defect_map.dat` + `BPC_hot_pixel_table`
   - 海思：越影 ISP 驱动加载 `defect_pixel_table.bin` 于 RAW 域预处理

3. **动态坏点检测（产线不可全标定）**：极端高增益（ISO 3200+）下新出现的热像素，由 ISP 动态 DPC 模块基于梯度检测实时处理，参数 `DPC_Dynamic_Strength` 控制检测敏感度。

**验收指标：** 静态坏点修复率 100%（不允许漏修）；过修复率（误将正常像素改写）< 0.01%；修复后坏点位置处与周边像素差异 < 3 DN。

---

### 8.3 镜头阴影标定（LSC Calibration）

**物理背景：** 镜头暗角（Vignetting）使图像边缘和角落比中心暗，原因包括：①余弦四次方定律（cos⁴ θ 衰减）；②机械暗角（Mechanical Vignetting，光线被镜片边缘遮挡）；③传感器 CRA（Chief Ray Angle）与微透镜主光线角不匹配导致的边缘 QE 下降。LSC 通过乘以增益表来补偿。

**标定流程：**

1. **均匀平场采集**：使用积分球（Integrating Sphere）或均匀漫射板，在标准色温（D65）下拍摄足够亮的平场图（目标信号电平 50%–70% 满阱，避免饱和也避免噪声主导），通常采集 16–32 帧取均值进一步消除空间噪声

2. **增益表生成**：

$$G_{c}(r, s) = \frac{I_{c,\text{center}}}{\bar{I}_{c}(r, s)}, \quad c \in \{R, Gr, Gb, B\}$$

其中 $(r, s)$ 为像素位置，$I_{c,\text{center}}$ 为中心区域（通常取中心 1/9 区域均值）的亮度，$\bar{I}_{c}(r, s)$ 为经多帧平均后的当前位置亮度。生成分辨率通常为 17×13 或 33×25 的稀疏增益表（ISP 运行时双线性插值到全分辨率）。

3. **多光源/多对焦距离标定**：
   - 手机主摄需在 D65、A 光源（2856 K）、CW 荧光灯（4150 K）分别标定，因为不同光谱下传感器 CRA 响应稍有差异
   - 长焦/微距模式下镜头结构变化，LSC 需要随对焦距离和变焦档位分别建表，由 3A 状态机索引

4. **LSC 增益范围约束**：
   - 增益过大处（角落增益 > 3.5×）会显著放大噪声，实践中设置增益上限 `LSC_GAIN_LIMIT = 3.5`，超出部分由更宽 AE 曝光补偿
   - 高通 Chromatix：`LSC_MESH_ROLLOFF_TABLE`（17×13，四通道），支持 16 个光源场景插值
   - 联发科：`mesh_shading_table_R/Gr/Gb/B`，`msf_scene_count` 控制场景数（最多 16 组）
   - 海思：越影平台 `lsc_correction_coeff[channel][row][col]`，支持运行时动态切换光源场景

**验收指标：** LSC 校正后均匀平场中心-角落亮度差 < 5%（R/B 通道容许稍大至 7%）；四通道一致性 < 3%；不同光源下校正后 Shading Ratio < 3%。

---

### 8.4 传感器线性度标定（Linearity Calibration）

**物理背景：** 理想传感器响应应满足 `输出 DN ∝ 入射光子数`（线性），但实际 CMOS 因像素非线性响应、ADC 非线性、FPN 等因素，在低照度或接近饱和处存在偏离，称为非线性误差（Non-linearity Error）。不校正非线性，CCM 矩阵和 AWB 增益仅在一个亮度区间准确，跨亮度范围时色准下降。

**标定方法：**

1. **灰度楔形图（Step Wedge）拍摄**：使用 16–24 档中性灰度色块（NDI ND 0 至 ND 5），由亮到暗覆盖 0.5% 至 95% 满阱，在标准光源和固定色温下顺序曝光

2. **线性度曲线拟合**：

$$R_{\text{ideal}}(\text{EV}) = k \cdot \Phi \cdot t_{\text{exp}}$$

实测响应 $R_{\text{actual}}$ 与理想线性的偏差定义为非线性误差 $\epsilon(L) = R_{\text{actual}}(L) / R_{\text{ideal}}(L) - 1$

3. **校正 LUT 生成**：逆函数 $\text{LUT}_{\text{linear}}[DN] = f^{-1}(DN)$ 写入 ISP 的 Linearization 模块（通常 256–1024 点 LUT），将实际响应映射到线性域

4. **常见非线性来源**：
   - **饱和前压缩（Knee）**：约 85%–95% 满阱附近，像素响应开始压缩，需在线性化 LUT 中区分处理（或提前触发 HDR 模式）
   - **暗部抬升（Pedestal Effect）**：低信号区 ADC 的有限量化精度和 FPN 引入的系统偏差
   - **增益依赖性**：不同 Analog Gain 下线性度略有差异，高增益下线性范围压缩

**平台支持：**
- 高通 Chromatix：`LinearizationModule34`，支持 64-point LUT per channel，随增益三维插值
- 联发科 Imagiq：`lsc_linearization_table`（与 LSC 联合处理）；高增益下 `nonlinear_strength` 参数调节
- EMVA 1288 标准中定义的线性度验收方法为行业通用参考（见 §7）

**验收指标：** 2%–90% 满阱范围内，非线性误差 < ±1%（高端旗舰主摄目标 < ±0.5%）。

---

### 8.5 噪声模型标定（Noise Model Calibration）

**核心模型：** ISP 噪声建模的行业标准是泊松-高斯混合模型（Poisson-Gaussian Mixed Noise Model）：

$$\sigma^2(I) = \alpha \cdot I + \beta$$

其中 $I$ 为信号强度（DN，归一化后），$\alpha$（散粒噪声因子，Photon Shot Noise Coefficient）和 $\beta$（读出噪声方差，Read Noise Variance）是需要标定的两个参数。每个增益档对应一组 $(\alpha_g, \beta_g)$。

> ⚠️ **常见错误：** 用 AWGN（Additive White Gaussian Noise，$\sigma = \text{const}$）近似代替 Poisson-Gaussian 模型，在低照度高增益时误差极大（可达 5–10 dB SNR 偏差），导致降噪网络在真实场景中表现失准。

**标定流程（PTC / Photon Transfer Curve 方法）：**

1. 在均匀平场下，固定色温，改变曝光量（EV 步进 0.5 EV），覆盖信号从 5% 到 90% 满阱，每档拍摄 ≥ 32 帧

2. 对每档曝光，取相邻两帧差图（Difference Frame），消除 FPN 和空间不均匀性，提取纯时域噪声：

$$\sigma^2_{\text{temporal}} = \frac{1}{2} \text{Var}(\text{Frame}_1 - \text{Frame}_2)$$

3. 对每个 Gain 档，绘制 $\sigma^2$ vs. $\bar{I}$（均值）散点图，用线性拟合：

$$\sigma^2 = \hat{\alpha} \cdot \bar{I} + \hat{\beta}$$

斜率 $\hat{\alpha}$ 对应散粒噪声分量，截距 $\hat{\beta}$ 对应读出噪声方差

4. 在所有增益档重复以上步骤，生成噪声参数表：$\{(g_k, \alpha_{g_k}, \beta_{g_k})\}$，存储为噪声模型 LUT

**平台配置：**

| 平台 | 噪声模型数据格式 | 用途 |
|------|-------------|------|
| 高通 Chromatix | `ADRC_NOISE_PROFILE_TABLE`，每 ISO 档存 $(\alpha, \beta)$，由 `NoiseMeasure` 模块标定 | MFNR 权重图、鬼影检测阈值 |
| 联发科 NDD | `NDD_noise_params_gain_table`（核心是 $(\alpha, \beta)$ 表），由标定工具 MTK `NoiseTune` 从 PTC 数据拟合生成 | FeaturePipe NR 强度、AI 降噪先验 |
| 海思越影 | `noise_sigma_table[gain_index][2]`，存 $(\alpha, \beta)$，供 AI NR 模型推理时的噪声先验输入 | Kirin NPU AI-NR |

**验收指标：** 拟合残差 $R^2 > 0.995$；各增益档下实测 $\sigma^2$ 与模型预测偏差 < 5%；$\alpha / \beta$ 随增益单调递增（违反此条件说明存在系统误差）。

---

### 8.6 白平衡增益标定（AWB Initial Calibration）

**定义：** AWB 标定的目标不是运行时的 AWB 算法调试（那是 §3 调参的范畴），而是确定各主要光源下的**白平衡增益先验点**（D65、A、TL84/F11 荧光灯、H 光源）写入 ISP 参数，作为 AWB 算法的初始收敛点和合法增益范围约束。

**标定流程：**

1. 在标准光源箱（Light Box）内的 D65、A、CW（4150 K）、TL84（3000 K）光源下，分别拍摄 X-Rite ColorChecker 24 块色卡（或纯灰色卡 18% 中灰）

2. 对每个光源，在中性灰块上计算 R/G/B 通道均值，白平衡增益 $g_c$ 为：

$$g_R = \frac{\bar{G}}{\bar{R}}, \quad g_G = 1.0, \quad g_B = \frac{\bar{G}}{\bar{B}}$$

3. 将各光源增益点绘制在 RG/BG 平面（AWB 增益空间），用多项式或分段线性曲线拟合**光源轨迹（Illuminant Locus）**，作为 AWB 运行时合法增益区间

4. 验证合法增益区间是否合理：D65 典型值 $g_R \approx 1.6$–$2.1$, $g_B \approx 1.5$–$2.0$；A 光 $g_R \approx 1.1$, $g_B \approx 2.5$–$3.2$（偏红光源，蓝增益需更高）

**色彩准确性验证（CCM 标定前置）：**
AWB 增益标定完成后，用 ColorChecker 拍摄验证 ΔE₀₀（CIE 2000 色差公式）< 5.0（AWB 后，未加 CCM），确认通道增益方向正确后再进行 CCM 矩阵标定。

---

### 8.7 色彩校正矩阵标定（CCM Calibration）

**物理基础：** 传感器的光谱响应曲线与人眼色彩匹配函数（CIE xyz）不匹配，导致相机拍摄的 RGB 值与标准色彩空间（sRGB）存在系统偏差。CCM（Color Correction Matrix）是将相机 RGB 线性变换到 sRGB 的 3×3 矩阵（含偏置项）：

$$\begin{bmatrix} R_{\text{out}} \\ G_{\text{out}} \\ B_{\text{out}} \end{bmatrix} = M_{3\times3} \begin{bmatrix} R_{\text{cam}} \\ G_{\text{cam}} \\ B_{\text{cam}} \end{bmatrix} + \mathbf{b}$$

**标定流程：**

1. 在各主要光源下（至少 D65 + A 光，工程上还会加 TL84），拍摄 ColorChecker 24 色色卡（施加 AWB 增益后的 RAW 线性值）

2. 对每个色块 $i$，建立方程 $M \cdot \mathbf{r}_i \approx \mathbf{t}_i$，其中 $\mathbf{r}_i$ 为相机 RGB 三通道响应，$\mathbf{t}_i$ 为 CIE XYZ 或 sRGB 标准值（来自 ColorChecker 官方测量数据）

3. 最小二乘求解：

$$M^* = \arg\min_M \sum_{i=1}^{24} \left\| M \cdot \mathbf{r}_i - \mathbf{t}_i \right\|_2^2$$

写成矩阵形式：$M^* = (\mathbf{T} \mathbf{R}^T)(\mathbf{R} \mathbf{R}^T)^{-1}$，其中 $\mathbf{R} \in \mathbb{R}^{3 \times 24}$，$\mathbf{T} \in \mathbb{R}^{3 \times 24}$

4. **多 CCM（Multi-CCM）策略**：对不同光源分别标定矩阵 $M_{D65}$, $M_A$, $M_{TL84}$，运行时根据 AWB 估计的色温 CCT 在矩阵之间线性插值

5. **矩阵条件数检验**：高条件数（$\kappa(M) > 10$）意味着矩阵对测量噪声敏感，色准易受传感器噪声干扰。可通过调整 AWB 增益先验点或改用正则化最小二乘（Tikhonov 正则化）降低条件数（参见第二卷第06章§3.2）

**验收指标：** ColorChecker 24 块 ΔE₀₀ 平均值 < 3.0（D65 光源），最大值 < 6.0；饱和色（第1–6行）单独统计 ΔE₀₀ < 5.0；中性灰列（第6列 6 块）色差 < 1.5。

**平台参数位置：**
- 高通 Chromatix：`ChromaticityModule` → `CCM_Matrix_D65 / CCM_Matrix_A`，随 AWB CCT 插值
- 联发科：`color_correction_transform_matrix[3][3]` + `color_range_adjust`
- 海思越影：`ccm_coef[light_source_index][3][3]`，光源索引由 AWB 输出映射

---

### 8.8 各标定模块的工厂产线集成

手机摄像模组（Camera Module Assembly）出厂前，上述标定通常在自动化标定产线上按以下顺序串行执行，每台模组独立标定写入 EEPROM/OTP：

```
1. 上电自检（Power-On Self Test）
     └── 传感器 ID、I²C 通信、基本帧率验证

2. 暗场采集 → BLC 标定
     └── 覆盖 5 个增益档 × 2 个曝光点 = 10 组暗帧
     └── 计算 BLC_R/Gr/Gb/B，写入 EEPROM

3. 坏点标定 → 静态坏点图生成
     └── 暗场热像素检测 + 平场死像素检测
     └── 坏点列表写入 EEPROM（≤ 200 个 @ 200MP）

4. 平场采集 → LSC 标定（D65 主标 + A 光辅标）
     └── 生成 17×13 四通道增益表，写入 EEPROM

5. 传感器线性度验证
     └── 快速 PTC（3 个曝光点），确认非线性误差 < 2%

6. 噪声参数标定（全增益 PTC）
     └── 拟合 (α, β)，写入 ISP 调试参数（非 EEPROM，而是固件分区）

7. AWB 增益点标定（标准光源箱）
     └── D65 / A 两光源增益点写入 ISP

8. CCM 矩阵标定
     └── ColorChecker 24 色，最小二乘，ΔE₀₀ < 3.0 合格
     └── CCM 写入 ISP Chromatix / NDD 参数包

9. 整体验收拍摄
     └── 在 D65 下拍摄标准化色卡 + 分辨率靶标，自动判读合格/不合格
```

典型单台模组标定时间：**30–90 秒**（高端旗舰因多光源、多增益覆盖更全，通常 60–90 s；中端机型可压缩至 30–45 s）。

**产线标定数据管理：** 每台模组的 SN（序列号）与标定结果绑定存档，用于售后追溯。云端标定数据库记录批次统计分布，异常聚集（如某批次 BLC 集体偏高）触发供应商质量警报。

---

## §9 术语表（Glossary）

**针孔相机模型（Pinhole Camera Model）**
将相机抽象为理想小孔的中心投影模型，描述三维世界坐标系中的点通过透视投影映射到二维像素坐标系的几何关系：$s\mathbf{u} = \mathbf{K}[\mathbf{R}|\mathbf{t}]\mathbf{X}_w$。针孔模型是 CV 标定的数学基础，但不描述镜头厚度、像差和传感器封装效应。ISP 中 LDC/GDC 模块的目标，就是将真实镜头（偏离针孔模型）的图像通过非线性逆映射"还原"成理想针孔图像。对 FOV > 110° 的超广角和鱼眼镜头，单纯针孔模型误差显著上升，需改用 Kannala-Brandt 等专用模型。

**内参矩阵（Intrinsic Matrix, K）**
描述从相机坐标系中归一化像面坐标到像素坐标的线性映射，包含 5 个参数：焦距 $f_x, f_y$（像素单位）、主点 $c_x, c_y$（光轴与传感器交点）、斜切参数 $s$（现代传感器通常为 0）。典型手机主摄 12 MP（4032×3024）：$f_x \approx 1100$–$2200$ px，$c_x \approx 2016$ px，$c_y \approx 1512$ px；主点偏心通常在 ±15 px 以内。内参随对焦距离轻微变化（变焦相机各档独立标定），随温度有热漂移（极端温差 ±2% 量级）。

**外参（Extrinsic Parameters）**
描述从世界坐标系到相机坐标系的刚体变换：旋转矩阵 $\mathbf{R}$（3×3，$\text{SO}(3)$）和平移向量 $\mathbf{t}$（3×1）。外参是标定过程的副产品（每张标定图像对应一组外参），描述标定板在相机视野中的位姿。多相机系统中，两相机之间的外参（相对旋转和平移）是立体标定的核心输出，决定对极几何精度。

**齐次坐标（Homogeneous Coordinates）**
在 $n$ 维空间中引入额外一维使得透视投影等非线性变换可以用矩阵乘法统一表达的坐标表示。三维点 $(X, Y, Z)$ 在齐次坐标下表示为 $(X, Y, Z, 1)^T$，二维像素 $(u, v)$ 表示为 $(u, v, 1)^T$。齐次坐标允许将透视投影、旋转、平移合并为一次矩阵乘法操作，是投影几何的核心工具。

**径向畸变（Radial Distortion）**
由透镜曲率不均匀引起、以光轴为中心对称分布的几何像差，沿径向方向叠加。Brown-Conrady 模型：$x' = x(1 + k_1 r^2 + k_2 r^4 + k_3 r^6)$，$r^2 = x^2 + y^2$。$k_1 < 0$ 为桶形畸变（广角镜头，图像向内凸），$k_1 > 0$ 为枕形畸变（长焦镜头，图像向外凸）。径向畸变是手机镜头最主导的畸变项，超广角镜头中 $k_1$ 可达 $-0.2$ 量级；$k_3$ 在视场角 > 100° 时不可忽略。

**切向畸变（Tangential Distortion）**
由透镜平面与传感器平面不完全平行（装调倾斜）引起的非对称畸变：$\Delta x = 2p_1 xy + p_2(r^2+2x^2)$，$\Delta y = p_1(r^2+2y^2) + 2p_2 xy$。切向畸变系数 $p_1, p_2$ 通常比径向系数小一个量级（$|p_1|, |p_2| < 0.005$）。现代自动化镜头模组装配精度较高，切向畸变在多数手机主摄中对画质影响可忽略，但精密测量和立体视觉中不可省略。

**薄棱镜畸变（Thin Prism Distortion）**
由镜片组装偏心/倾斜引起的非对称残余畸变，模型含系数 $s_1, s_2, s_3, s_4$，描述图像平面内类似薄棱镜效应的整体拉伸或压缩。幅值通常 < 0.1 pixel，对单相机拍照应用可忽略；在双目/三目立体匹配、AR 对齐和 SLAM 等需要高精度几何对齐的应用中，薄棱镜残差不可忽视。OpenCV `CALIB_THIN_PRISM_MODEL` 标志支持该项标定。

**张正友标定法（Zhang's Calibration Method）**
Zhengyou Zhang（2000）提出的平面标定板标定方法，通过多张不同位姿的棋盘格图像联合求解相机内参和畸变系数。核心原理：每张图提取单应矩阵 $\mathbf{H}$，每个 $\mathbf{H}$ 对内参相关矩阵 $\mathbf{B} = \mathbf{K}^{-T}\mathbf{K}^{-1}$ 提供 2 个线性约束，理论最小 3 张可线性求解（$\mathbf{B}$ 有 5 个自由度），工程推荐 10–20 张覆盖不同距离和倾角。已集成到 OpenCV `calibrateCamera()` 中，是工业界和学术界最广泛使用的标定方案。

**单应矩阵（Homography Matrix, H）**
描述两个平面之间点对点映射关系的 $3\times3$ 矩阵（8 自由度，因整体缩放不确定）。在张正友标定法中，标定板为平面（$Z=0$），相机图像与标定板平面之间的映射可用单应矩阵 $\mathbf{H} = \mathbf{K}[\mathbf{r}_1\ \mathbf{r}_2\ \mathbf{t}]$ 描述。至少 4 对对应点可用直接线性变换（DLT）算法求解 $\mathbf{H}$。

**Kannala-Brandt 鱼眼模型**
Kannala 和 Brandt（2006）提出的适用于大视场角（鱼眼/超广角）镜头的投影模型：$r(\theta) = k_1\theta + k_2\theta^3 + k_3\theta^5 + k_4\theta^7$，其中 $\theta$ 为入射光线与光轴夹角，$r$ 为像面径向距离。多项式仅含奇次项，因投影函数必须为奇函数（$r(-\theta) = -r(\theta)$，满足中心对称性）。OpenCV `fisheye` 模块实现了该模型，适用于 FOV > 120° 的超广角和鱼眼镜头标定，Brown 模型在此范围精度明显不足。

**重投影误差（Reprojection Error）**
标定质量的核心定量指标：用当前标定参数将世界坐标系中的三维角点重投影到图像平面，计算与检测到的二维角点之间的 RMS 欧氏距离，单位 pixel。优秀标定 < 0.3 px，工程可接受 < 0.5 px，> 1.0 px 需重新标定。逐图分析误差分布可识别异常图像（拍摄质量差、运动模糊等），剔除离群图后重标通常显著改善结果。

**亚像素精化（Sub-pixel Refinement）**
角点检测精化至亚像素精度的算法，基于角点附近梯度场的约束：$\sum_{\mathbf{q} \in W}(\nabla I(\mathbf{q}) \cdot (\mathbf{q} - \hat{\mathbf{c}})) = 0$（角点处梯度方向与到角点向量正交）。OpenCV `cornerSubPix()` 实现此算法，可将角点定位精度从 ~1 pixel 提升至 0.01–0.1 pixel，是高精度标定的必要前处理步骤。

**本质矩阵（Essential Matrix, E）**
编码两相机之间旋转和平移关系、不含相机内参的几何约束矩阵：$\mathbf{E} = [\mathbf{t}]_\times \mathbf{R}$，其中 $[\mathbf{t}]_\times$ 为平移向量的反对称矩阵，$\mathbf{R}$ 为旋转矩阵。本质矩阵的秩为 **2**（非退化情形），两个非零奇异值相等，$\det(\mathbf{E}) = 0$。本质矩阵满足对极约束：$\mathbf{m}_2^T \mathbf{E} \mathbf{m}_1 = 0$（$\mathbf{m}_1, \mathbf{m}_2$ 为归一化相机坐标）。

**基础矩阵（Fundamental Matrix, F）**
本质矩阵的像素坐标版本，编码两相机内参和外参的综合约束：$\mathbf{F} = \mathbf{K}_2^{-T} \mathbf{E} \mathbf{K}_1^{-1}$。同样满足对极约束 $\mathbf{m}_2^T \mathbf{F} \mathbf{m}_1 = 0$（$\mathbf{m}_1, \mathbf{m}_2$ 为像素坐标的齐次表示）。基础矩阵的秩也为 2，可由至少 7 对对应点求解（7 点算法），工程上常用 8 点算法（RANSAC 加速）。

**立体校正（Stereo Rectification）**
将双目相机图像重投影使两幅图像的行严格对齐的变换，使得左图中任意点在右图中的对应点必然在同一水平行（极线约束），将立体匹配从 2D 搜索降为 1D 行扫描，大幅减少计算量。立体校正由 OpenCV `stereoRectify()` 实现，输出的校正映射（rectification maps）通过 `remap()` 应用于图像。

**单应性约束（Homography Constraint）**
利用平面标定板（$Z=0$）的约束，建立相机图像与标定板平面之间的射影对应关系。每对对应点给出 2 个线性方程，4 对点可线性求解单应矩阵 $\mathbf{H}$（8 个自由度）。在张正友标定法中，每个 $\mathbf{H}$ 对内参矩阵提供 2 个线性约束，是整个标定算法的核心中间步骤。

**EEPROM（标定数据存储）**
手机相机模组内用于存储工厂标定数据的可重复擦写存储器（Electrically Erasable Programmable Read-Only Memory），通常集成在摄像头模组 FPC 上，通过 I²C 接口与 ISP 驱动通信。存储内容：相机内参（$f_x, f_y, c_x, c_y$）、畸变系数（$k_1, k_2, p_1, p_2, k_3$）、LSC 增益表、AWB 初始参考点等。与 OTP/eFuse（一次性可编程，用于传感器 ID 等永久参数）不同，EEPROM 在维修更换模组后可重新写入标定数据。

**ChArUco 标定板**
棋盘格（Chessboard）与 ArUco 二维码标记混合的标定目标，每个方格内嵌独立 ID 的 ArUco 标记。相比纯棋盘格，ChArUco 板的核心优势在于**局部可见性**：即使标定板被部分遮挡或超出视野，可见的 ArUco 标记仍能提供有效的角点坐标（每个 ArUco 标记周围有 4 个棋盘角点，位置唯一确定）；方向无歧义性（棋盘格旋转 180° 无法区分）。适合机器人自动化产线和受遮挡场景；经典棋盘格角点精度理论上略优，在无遮挡的受控环境中仍广泛使用。

---



---

> **工程师手记：相机标定的工程阈值与温漂陷阱**
>
> **重投影误差验收阈值：** 相机标定完成后，通常以重投影误差（Reprojection Error，RPE）衡量标定质量。对于ISP参数校准（尤其是多摄对齐、AR叠加、测距应用），RPE验收标准应严格设定为 < 0.5像素；部分高精度AR场景要求 < 0.3像素。产线标定时若RPE超标，常见原因包括：靶图平整度不足（允差 < 0.1mm）、标定帧覆盖角度不足（建议覆盖±30°俯仰+水平）、光线不均匀导致角点检测偏移。一个容易忽视的细节是：RPE是对整批标定帧取平均，个别帧大误差可被平均稀释，应同时检查帧间RPE分布的离散度（P95 < 1.0px）。
>
> **温度导致标定漂移：** 手机主摄常用f/1.8–f/2.2塑料非球面镜头，其热膨胀系数约60–90 ppm/°C，远高于玻璃（约8 ppm/°C）。在镜头等效焦距约5mm时，温度每升高1°C，后焦距偏移约2μm，对应图像平面横向主点漂移约0.1–0.3像素。实测从常温25°C到高温50°C（手机满载场景），主点漂移累积可达2–5像素，足以引起多摄视差对齐失效。工程应对策略：一是在OTP中存储多温度点标定数据（至少25°C、40°C两点），ISP根据NTC温度传感器实时插值；二是设计热稳定校正块，定期（每30秒或温升ΔT > 5°C）触发软件矫正。
>
> **出厂标定与现场更新频率：** 出厂标定（Factory Calibration）在产线恒温环境下完成，精度最高，但设备寿命期内受跌落、老化等影响会逐步偏移。现场标定更新（Field Calibration）依赖用户无感知触发，常见策略是利用运动视频中的静止特征点做自校准（online calibration），精度通常比出厂低0.2–0.5像素。实践中出厂标定有效期约6–12个月，超过此周期若无自校准保障，多摄3D测距误差会超出产品规格。
>
> *参考：Zhang, Z. "A Flexible New Technique for Camera Calibration", IEEE TPAMI 2000；Bradski & Kaehler "Learning OpenCV 3", Ch.18；Apple Vision Pro Spatial Audio Calibration Technical Note（2023）*

## 插图

![calibrationeckerboard](img/fig_calibration_checkerboard_ch.png)
*图1. 相机标定棋盘格靶标示意图（图片来源：Zhang, "A flexible new technique for camera calibration", IEEE TPAMI, 2000）*

![calibration target types](img/fig_calibration_target_types_ch.png)
*图2. 常用相机标定靶标类型对比（棋盘格、圆点阵列、AprilTag等）（图片来源：作者自绘）*

![calibration workflow](img/fig_calibration_workflow_ch.png)
*图3. 相机内参/外参标定完整流程图（图片来源：Bouguet, "Camera Calibration Toolbox for Matlab", 2004）*

![lens distortion models](img/fig_lens_distortion_models_ch.png)
*图4. 径向畸变与切向畸变（Brown-Conrady模型）示意图（图片来源：Brown, "Decentering distortion of lenses", Photogrammetric Engineering, 1966）*

![reprojection error distribution](img/fig_reprojection_error_distribution_ch.png)
*图5. 标定重投影误差分布图（图片来源：作者自绘）*

---

## 习题

**练习 1（理解）**
相机标定的核心输出是内参矩阵 $\mathbf{K}$ 和畸变系数 $(k_1, k_2, p_1, p_2)$。请说明：(a) 内参矩阵中 $f_x$ 与物理焦距（mm）的换算关系是什么，手机广角镜头 $f_x \approx 1400\,\text{pixel}$、像素尺寸 $1.0\,\mu\text{m}$ 时，等效物理焦距约为多少 mm？(b) 切向畸变系数 $p_1, p_2$ 的物理来源是什么？手机镜头的 $|p_1|, |p_2|$ 通常比单反镜头大一个量级，原因是什么（参考本章塑料镜片组装公差分析）？(c) 为什么标定时需要从多个角度拍摄棋盘格，而不是只拍一张？

**练习 2（计算）**
某相机内参：$f_x = 1800\,\text{px}$，$f_y = 1800\,\text{px}$，$c_x = 2016\,\text{px}$，$c_y = 1512\,\text{px}$，径向畸变系数 $k_1 = -0.12$，$k_2 = 0.05$（$k_3 = 0$），切向畸变系数 $p_1 = p_2 = 0$。对于世界坐标系中的点 $\mathbf{X}_w = (0.3, 0.2, 1.5)\,\text{m}$（外参为单位矩阵，即相机坐标系与世界坐标系重合），请计算：(a) 归一化相机坐标 $(x, y) = (X_c/Z_c, Y_c/Z_c)$；(b) $r^2 = x^2 + y^2$，加畸变后坐标 $(x', y')$（使用 $k_1 r^2 + k_2 r^4$）；(c) 最终像素坐标 $(u, v) = (f_x x' + c_x, f_y y' + c_y)$。

**练习 3（编程）**
用 Python + OpenCV 完成棋盘格相机标定并计算重投影误差：(a) 生成或拍摄 10 张以上不同角度的 7×7 棋盘格图像（可从 OpenCV 官方样例数据集下载）；(b) 用 `cv2.findChessboardCorners` + `cv2.calibrateCamera` 标定内参和畸变系数；(c) 对每张标定图计算重投影误差（`cv2.projectPoints` 将 3D 角点投影回图像，与检测到的 2D 角点计算 L2 距离），打印所有图像的平均重投影误差（良好标定应 < 0.5 pixel）；(d) 用 `cv2.undistort` 对一张测试图执行去畸变，对比直线是否变直。

**练习 4（工程分析）**
手机 ISP 的 LDC（Lens Distortion Correction）模块通常在出厂时烧录标定参数，而不是运行时实时标定。请分析：(a) 出厂烧录方案对温度变化（塑料镜头折射率温漂）和跌落冲击（镜头组装偏移）的鲁棒性如何？(b) 鱼眼镜头（FoV > 180°）为什么不能使用 Brown-Conrady 模型，通常改用什么模型？(c) 双摄（广角 + 长焦）之间的相对外参标定误差对哪些应用功能（如立体虚化、AR 对齐）影响最直接？

## 参考文献

[1] Zhang et al., "A flexible new technique for camera calibration", *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 2000. （张正友标定法原始论文，单平面棋盘格方法的理论基础）

[2] Bouguet et al., "Camera Calibration Toolbox for Matlab", *California Institute of Technology*, 2004. URL: http://www.vision.caltech.edu/bouguetj/calib_doc/ （最广泛使用的相机标定工具箱，实现了张正友方法）

[3] Brown et al., "Decentering distortion of lenses", *Photogrammetric Engineering*, 1966. （径向+切向畸变模型 Brown-Conrady 原始论文）

[4] Bradski et al., "Learning OpenCV: Computer Vision with the OpenCV Library", *O'Reilly Media*, 2008. （OpenCV 相机标定 API 标准参考，含 `calibrateCamera`、`stereoCalibrate` 实现说明）

[5] Kannala et al., "A generic camera model and calibration method for conventional, wide-angle, and fish-eye lenses", *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 2006. （Kannala-Brandt 鱼眼镜头标定模型，OpenCV `fisheye` 模块所基于的理论）

[6] Geiger et al., "Automatic camera and range sensor calibration using a single shot", *IEEE ICRA*, 2012. （单次拍摄标定方案，适合自动驾驶多传感器融合场景）

[7] Scaramuzza et al., "A toolbox for easily calibrating omnidirectional cameras", *IEEE/RSJ IROS*, 2006. （全向相机 OCamCalib 标定工具箱，适用于鱼眼和全景相机）

[8] Garrido-Jurado et al., "Automatic generation and detection of highly reliable fiducial markers under occlusion", *Pattern Recognition*, 2014. （ArUco 标记原始论文，ChArUco 板的基础）

[9] Heikkila et al., "A four-step camera calibration procedure with implicit image correction", *IEEE CVPR*, 1997. （早期全面的畸变校正流程，包含切向畸变的完整处理）

[10] Hartley et al., "Multiple View Geometry in Computer Vision (2nd ed.)", *Cambridge University Press*, 2004. （多视图几何经典教材，基础矩阵、本质矩阵、单应性矩阵的理论体系）

[11] Li et al., "StereoISP: Rethinking Image Signal Processing for Dual Camera Systems", *arXiv:2211.07390*, 2022. （手机双摄 ISP 与立体匹配联合框架，利用双目 RAW 对生成去马赛克和去噪后的 RGB 图像）
<!-- REF-AUDIT: [11] 原文 "Lu et al., Wide-baseline stereo-matching for mobile ISP, IEEE TIP, 2022" 未能查实（可能为虚构引用）→ 替换为可查实的同主题相近工作 arXiv:2211.07390；如有更精确引用请手动修正 -->

[12] MIPI Alliance, "MIPI CSI-2 Specification v4.0", *官方文档*, 2023. URL: https://www.mipi.org/specifications/csi-2 （移动端传感器接口规范，标定数据传输与 EEPROM 读取的协议基础）
