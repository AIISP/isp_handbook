# 附录D — 开源ISP工具参考 | Open-Source ISP Tools

> ISP算法开发、研究和原型验证所用开源库、框架和代码仓库的精选参考。

---

## D.1 核心库

### rawpy

| 字段 | 详情 |
|-------|---------|
| **工具** | rawpy |
| **用途** | RAW文件I/O——解码来自1000+相机型号的RAW图像；LibRaw的Python封装 |
| **语言** | Python（C++后端通过LibRaw） |
| **URL** | https://github.com/letmaik/rawpy |
| **ISP模块** | RAW I/O、BLC、白平衡、去马赛克（提供LibRaw内置流水线的访问接口） |
| **安装** | `pip install rawpy` |

```python
import rawpy
import numpy as np

with rawpy.imread('image.dng') as raw:
    # 访问原始Bayer数据
    bayer = raw.raw_image_visible.copy()
    # 内置后处理（LibRaw流水线）
    rgb = raw.postprocess(use_camera_wb=True, output_bps=16)
    # 访问逐通道黑电平
    black_levels = raw.black_level_per_channel
    # 访问白平衡增益
    wb_gains = raw.camera_whitebalance
```

**使用章节：** 第二卷第01章（BLC）、第二卷第02章（去马赛克）、第二卷第05章（AWB）、第二卷第08章（LSC）。

---

### colour-science

| 字段 | 详情 |
|-------|---------|
| **工具** | colour-science |
| **用途** | 综合颜色科学库：颜色空间、色度适应、颜色外貌模型、光谱数据 |
| **语言** | Python |
| **URL** | https://github.com/colour-science/colour |
| **ISP模块** | AWB（色度适应）、CCM、色彩空间变换、Gamma、IQA（ΔE） |
| **安装** | `pip install colour-science` |

```python
import colour

# 颜色空间转换
XYZ = colour.sRGB_to_XYZ(rgb)
Lab = colour.XYZ_to_Lab(XYZ)

# ΔE₀₀计算
delta_E = colour.delta_E(Lab_ref, Lab_test, method='CIE 2000')

# 色度适应（冯·克里斯）
XYZ_adapted = colour.chromatic_adaptation(XYZ, XYZ_w, XYZ_wr, method='Von Kries')

# 从色度坐标计算相关色温
CCT = colour.xy_to_CCT(xy, method='Hernandez 1999')
```

**使用章节：** 第一卷第05章（颜色科学）、第二卷第05章（AWB）、第二卷第06章（CCM）、第二卷第07章（Gamma）。

---

### colour-demosaicing

| 字段 | 详情 |
|-------|---------|
| **工具** | colour-demosaicing |
| **用途** | 去马赛克算法的参考实现：双线性、Malvar-He-Cutler、DDFAPD、Menon 2007等 |
| **语言** | Python |
| **URL** | https://github.com/colour-science/colour-demosaicing |
| **ISP模块** | 去马赛克（第二卷第02章） |
| **安装** | `pip install colour-demosaicing` |

```python
import colour_demosaicing as cdm

# 双线性（基准）
rgb_bilinear = cdm.demosaicing_CFA_Bayer_bilinear(bayer, 'RGGB')

# Malvar-He-Cutler（质量较好，计算量低）
rgb_mhc = cdm.demosaicing_CFA_Bayer_Malvar2004(bayer, 'RGGB')

# Menon 2007（高质量）
rgb_menon = cdm.demosaicing_CFA_Bayer_Menon2007(bayer, 'RGGB')
```

**使用章节：** 第二卷第02章（去马赛克）。

---

### LibRaw

| 字段 | 详情 |
|-------|---------|
| **工具** | LibRaw |
| **用途** | 支持1000+相机型号的低级RAW解码库；C++库，为rawpy的底层依赖 |
| **语言** | C++ |
| **URL** | https://github.com/LibRaw/LibRaw |
| **ISP模块** | RAW I/O、BLC、去马赛克、白平衡、输出色彩空间 |
| **许可证** | LGPL v2.1 / CDDL 1.0 |

**备注：** LibRaw提供了开源中最完整的RAW解码器。支持DNG、CR2、CR3、NEF、ARW、RAF、RW2和数百种其他格式。rawpy提供Pythonic接口；在量产流水线中直接使用LibRaw（C++）。

---

### OpenISP

| 字段 | 详情 |
|-------|---------|
| **工具** | OpenISP |
| **用途** | Python全流水线软件ISP实现；所有流水线阶段的教学参考 |
| **语言** | Python |
| **URL** | https://github.com/cruxopen/openISP |
| **ISP模块** | BLC、PDPC、LSC、去马赛克、去噪（双边）、AWB（灰世界）、CCM、Gamma、CSC——完整流水线 |
| **许可证** | MIT |

**备注：** OpenISP是教学性流水线。每个阶段都作为独立Python模块实现，输入输出明确。可用于理解ISP流水线中的顺序数据流。未针对性能优化，但可读性高。

---

## D.2 RAW处理应用

### darktable

| 字段 | 详情 |
|-------|---------|
| **工具** | darktable |
| **用途** | 开源专业RAW照片处理器和数字暗房 |
| **语言** | C（独立像素流水线，RawSpeed解码RAW），OpenCL加速 |
| **URL** | https://github.com/darktable-org/darktable |
| **ISP模块** | 完整流水线：去马赛克、去噪、AWB、CCM（颜色标定）、色调曲线、镜头校正、HDR |
| **许可证** | GPL v3 |

**备注：** darktable的场景参照工作流实现了现代电影式色调映射流水线。其颜色标定模块（基于ColorChecker）被专业摄影师使用。OpenCL后端为实时预览提供GPU加速。可作为Gamma、色调映射和颜色科学生产质量实现的研究参考。

---

### RawTherapee

| 字段 | 详情 |
|-------|---------|
| **工具** | RawTherapee |
| **用途** | 开源跨平台RAW图像处理软件 |
| **语言** | C++ |
| **URL** | https://github.com/Beep6581/RawTherapee |
| **ISP模块** | 去马赛克（AMaZE、DCB、LMMSE等）、去噪（小波）、AWB、CCM、色调曲线、LSC、色差校正 |
| **许可证** | GPL v3 |

**备注：** RawTherapee实现了AMaZE去马赛克算法（自适应流形实时高维滤波），被认为是边缘保真度最佳的去马赛克算法之一。源代码是研究量产去马赛克实现的宝贵参考。

---

### LibCamera

| 字段 | 详情 |
|-------|---------|
| **工具** | libcamera |
| **用途** | Linux开源相机框架；提供相机抽象层和3A控制 |
| **语言** | C++ |
| **URL** | https://github.com/libcamera-org/libcamera |
| **ISP模块** | 3A控制（AE、AWB、AF）、流水线配置、相机HAL |
| **许可证** | LGPL v2.1+ |

**备注：** libcamera是Linux（包括Raspberry Pi相机栈）的标准相机框架。其3A控制算法（AE测光、AWB估计）有完善文档，代表了控制回路设计的简洁开源参考。用于Raspberry Pi HQ Camera及多款Linux嵌入式相机。

---

## D.3 ISP算法相关代码仓库

### ISP相关GitHub代码仓库

| 仓库 | 用途 | 语言 | URL | ISP模块 |
|-----------|---------|----------|-----|-----------|
| **colour-science** | CCM拟合和颜色科学工具 | Python | https://github.com/colour-science/colour | CCM、AWB |
| **noise2noise**（Lehtinen et al.） | 无干净目标的盲去噪 | Python/PyTorch | https://github.com/NVlabs/noise2noise | 去噪（第二卷第03章） |
| **NAFNet** | 非线性激活无网络，用于图像复原 | Python/PyTorch | https://github.com/megvii-research/NAFNet | DL去噪、去模糊（第三卷第02章） |
| **Real-ESRGAN** | 真实世界盲超分辨率 | Python/PyTorch | https://github.com/xinntao/Real-ESRGAN | 超分辨率（第三卷第03章） |
| **BasicSR** | 基础超分辨率/图像复原工具包 | Python/PyTorch | https://github.com/XPixelGroup/BasicSR | SR、去噪、去模糊（第三卷） |
| **IQA-pytorch** | 图像质量评估指标：PSNR、SSIM、LPIPS、BRISQUE、NIQE等 | Python/PyTorch | https://github.com/chaofengc/IQA-PyTorch | IQA（第四卷第04章） |
| **PyNET / AIM Learned ISP** | Google的学习ISP流水线（基于Pynet） | Python/TF | https://github.com/aiff22/PyNET | DL ISP（第三卷第01章） |
| **rawpy（批量处理示例）** | rawpy 官方仓库内含批量RAW处理用法示例；无独立 rawpy-utils 仓库 | Python | https://github.com/letmaik/rawpy | RAW I/O、流水线 |
| **Infinite-ISP** | 完整可仿真 ISP 流水线（RTL 级 + Python 参考实现），含 BLC、DPC、LSC、Demosaic、NR、CCM、Gamma 全链路，支持 FPGA 综合 | Python + SystemVerilog | https://github.com/10x-Engineers/Infinite-ISP | 完整流水线（教学/硬件原型） |

---

## D.4 支持工具

### NumPy / SciPy

全书广泛用于矩阵运算、曲线拟合和信号处理。数学背景参见附录A。

- **URL：** https://numpy.org / https://scipy.org
- **ISP用途：** LSC多项式拟合（scipy.optimize）、CCM最小二乘（numpy.linalg）、MTF计算（scipy.fft）

### OpenCV

- **URL：** https://github.com/opencv/opencv
- **ISP用途：** 去马赛克（`cv2.cvtColor`）、图像I/O、PDPC的形态学运算、连通组件分析

### scikit-image

- **URL：** https://github.com/scikit-image/scikit-image
- **ISP用途：** SSIM、PSNR、峰值信噪比、结构相似性

### ExifTool

- **URL：** https://github.com/exiftool/exiftool（命令行版）/ https://exiftool.org
- **ISP用途：** 从RAW/JPEG/DNG文件中提取或写入EXIF元数据（ISO、曝光时间、f/#、色温估计、GPS等）；批量重命名、元数据迁移；脚本化标定数据管理
- **安装：** `brew install exiftool`（macOS）/ `apt install libimage-exiftool-perl`（Linux）/ Windows二进制包直接下载
- **许可证：** Artistic License 1.0

### dcraw

- **URL：** https://www.dechifro.org/dcraw/（已停止维护，最终版本9.28）/ 建议改用 LibRaw 替代
- **ISP用途：** 早期最广泛使用的RAW解码命令行工具；支持700+相机型号；仍是大量遗留脚本的依赖基础
- **备注：** dcraw已不再维护，新项目建议使用LibRaw（C++）或rawpy（Python）替代。dcraw在Linux发行版包管理器中仍可用（`apt install dcraw`）。

### Imatest（参考工具——商业软件）

虽非开源，但Imatest是ISP IQA测量的行业标准。其文档（https://www.imatest.com/docs/）公开可用，提供了本手册全文参考的MTF、噪声、颜色和畸变测量方法的详细说明。

---

## D.5 2023–2024 新增重要工具

### NAFNet

- **URL：** https://github.com/megvii-research/NAFNet
- **ISP用途：** 高效图像复原网络，在SIDD去噪、GoPro去模糊等多项基准上达到SOTA；无非线性激活设计使其部署友好
- **使用章节：** 第三卷第02章（端到端图像复原）、附录F §F.1

### BasicSR

- **URL：** https://github.com/XPixelGroup/BasicSR
- **ISP用途：** 超分辨率/去噪/去模糊通用训练框架；内置EDSR、ESRGAN、Real-ESRGAN等多个SOTA实现；支持分布式训练
- **安装：** `pip install basicsr`
- **使用章节：** 第三卷第03章（超分辨率）、附录D §D.3

### IQA-pytorch（图像质量评估工具包）

- **URL：** https://github.com/chaofengc/IQA-PyTorch
- **ISP用途：** 统一接口计算PSNR、SSIM、MS-SSIM、LPIPS、BRISQUE、NIQE、FID等20+指标；支持批量评估
- **安装：** `pip install IQA-pytorch`
- **使用章节：** 第四卷第04章（感知IQA）

### Retinexformer

- **URL：** https://github.com/caiyuanhao1998/Retinexformer
- **ISP用途：** 基于 Retinex 理论的单阶段 Transformer 低光增强网络，在 LOL-v1/v2、SMID 等多项基准上达到 SOTA（2023 ICCV，2024 ECCV 增强版）；同时支持曝光校正等任务
- **安装：** `git clone + pip install -r requirements.txt`
- **使用章节：** 第三卷第05章（LLIE）、附录F §F.9

### MambaIR

- **URL：** https://github.com/csguoh/MambaIR
- **ISP用途：** 基于状态空间模型（Mamba/SSM）的图像复原框架，在 SIDD 去噪、×4 超分辨率等任务上超越 Restormer（2024 ECCV）；为新一代高效序列建模提供开源参考
- **安装：** `pip install causal-conv1d mamba-ssm`（需 CUDA 11.6+）
- **使用章节：** 第三卷第02章（端到端复原）、附录F §F.1

---

## D.6 安装

安装本手册使用的全部Python依赖：

```bash
pip install -r code/requirements.txt
```

`code/requirements.txt` 内容：

```
rawpy>=0.22
colour-science>=0.4.4
colour-demosaicing>=0.2.4
numpy>=1.26
scipy>=1.12
matplotlib>=3.8
opencv-python>=4.9
scikit-image>=0.22
torch>=2.2
torchvision>=0.17
lpips>=0.1.4
IQA-pytorch>=0.3.8
basicsr>=1.4.2
jupyter>=1.0
ipywidgets>=8.1
tqdm>=4.66
```

---

## 习题

**练习 1（理解）**
rawpy 是 LibRaw 的 Python 封装，而 LibRaw 本身是 dcraw 的 C++ 重写版本。两者在 API 设计上有显著差异：LibRaw 直接暴露 C++ 对象（`libraw_data_t` 结构体），而 rawpy 提供了面向对象的 Python 接口。请分析以下场景各自应使用哪种工具更合适：（1）在 Python 研究脚本中批量读取 RAW 文件并提取 Bayer 阵列数据；（2）在 C++ 嵌入式系统中集成 RAW 解码功能；（3）需要对 LibRaw 的 demosaic 算法进行修改和调试。两种工具在处理超大 RAW 文件（>100MB）时的内存效率有何差异？

**练习 2（分析/比较）**
IQA-PyTorch 库实现了 SSIM 等多种图像质量指标。在使用中发现，IQA-PyTorch 计算的 SSIM 值与 scikit-image 的 `compare_ssim()` 在同一图像对上可能存在约 0.01–0.02 的数值差异。请分析造成这一差异的可能原因：（1）边界填充方式（reflect vs. constant）；（2）高斯权重窗口大小（11×11 vs. 7×7）；（3）动态范围归一化（数据范围 [0,1] vs. [0,255]）。如何编写单元测试来验证自己实现的 SSIM 与参考实现的一致性？

**练习 3（实践）**
使用 rawpy 加载一张 RAW 文件，分别用以下三种方式处理并比较输出差异：（1）`raw.postprocess()` 默认参数（rawpy 自动 demosaic + 色调映射）；（2）`raw.raw_image_visible` 直接获取 Bayer 阵列，手动实现双线性插值 demosaic；（3）`raw.postprocess(use_camera_wb=True, no_auto_bright=True)` 使用相机白平衡但禁用自动亮度。比较三种输出的 PSNR 差异，分析 rawpy 默认处理与"中性"处理之间有多大差距。
