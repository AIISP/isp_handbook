# 附录 J — 开发环境搭建与代码复现指南

> **最后更新：** 2026-06

本附录提供运行手册各章节代码示例所需的完整环境配置步骤。

---

## J.1 基础环境要求

### 系统要求
- **操作系统：** Ubuntu 20.04/22.04 LTS（推荐）；Windows 11 + WSL2；macOS 12+
- **Python：** 3.10+（建议用 conda 管理）
- **CUDA：** 11.8 或 12.1（DL章节需要，传统ISP章节不需要）
- **内存：** 16 GB RAM 最低，32 GB 推荐（DL模型训练需要）
- **GPU：** NVIDIA GPU（>=8 GB VRAM，推荐 RTX 3080/4090）

---

## J.2 快速安装（推荐路径）

### Step 1 — 创建 conda 环境

```bash
# 创建专用环境
conda create -n aiisp python=3.10 -y
conda activate aiisp

# 安装 CUDA（如有 NVIDIA GPU）
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
```

### Step 2 — 安装手册依赖

```bash
git clone https://github.com/AIISP/isp_handbook.git
cd ISP_handbook
pip install -r code/requirements.txt
```

### Step 3 — 验证安装

```python
import rawpy
import colour
import cv2
import torch

print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"rawpy: OK")
print(f"colour-science: OK")
```

---

## J.3 分章节依赖说明

| 卷 | 典型章节 | 额外依赖 | 说明 |
|----|---------|---------|------|
| 第一卷 | 传感器物理、颜色科学 | rawpy, colour-science | 无需 GPU |
| 第二卷 | 传统ISP算法 | opencv-python, scipy | 无需 GPU |
| 第三卷 | DL图像复原 | torch, torchvision, timm | 需要 GPU（>=8 GB） |
| 第三卷 | 超分辨率 | basicsr, facexlib | ESRGAN 需要预下载权重 |
| 第四卷 | IQA | lpips, piqa | 部分指标需 GPU |
| 第五卷 | 多模态模型 | transformers, diffusers | 大模型需要 24+ GB VRAM |
| 第六卷 | 消费摄影分析 | rawpy, pillow | 无需 GPU |

---

## J.4 树莓派 4B + IMX477 硬件验证环境

手册第二卷核心算法通过树莓派 4B + IMX477 摄像头进行真实 RAW 流水线验证。

### 硬件配置
- 树莓派 4B（4GB RAM）
- Raspberry Pi HQ Camera（IMX477，12.3 MP，1/2.3" 传感器）
- microSD 卡（64 GB Class 10）

### 软件安装

```bash
# 在树莓派上安装
sudo apt update && sudo apt install -y python3-pip libcamera-apps
pip3 install rawpy numpy matplotlib

# 拍摄 RAW 图像
libcamera-still --raw -o test.jpg
# 生成 test.dng 文件
```

```python
# 读取 RAW
import rawpy
with rawpy.imread('test.dng') as raw:
    print(f"相机型号: {raw.camera_icc_profile}")
    print(f"CFA图案: {raw.color_desc}")
    print(f"RAW尺寸: {raw.raw_image.shape}")
    print(f"黑电平: {raw.black_level_per_channel}")
    print(f"白电平: {raw.white_level}")
```

### 已验证章节
| 章节 | 验证状态 | 说明 |
|------|---------|------|
| 第二卷 ch01 BLC | ✅ 验证通过 | IMX477 OB 像素读取正确 |
| 第二卷 ch05 AWB | 🔄 进行中 | 多光源测试中 |
| 其余章节 | ⏳ 计划中 | 按优先级逐步验证 |

---

## J.5 常见问题

**Q: rawpy 安装失败**
```bash
# Linux：先安装 libraw
sudo apt install libraw-dev
pip install rawpy

# Windows：
pip install rawpy  # 通常直接可用
```

**Q: CUDA 版本不匹配**
```bash
# 检查 CUDA 版本
nvcc --version
# 按实际版本安装对应 PyTorch：https://pytorch.org/get-started/locally/
```

**Q: colour-science 导入错误**
```bash
pip install colour-science  # 注意是 colour-science 不是 colour
```

---

## J.6 代码验证状态说明

手册各章节代码示例的验证状态标注如下：

| 标记 | 含义 |
|------|------|
| ✅ 已验证 | 代码在树莓派/GPU服务器上实际运行确认 |
| 🔄 验证中 | 代码逻辑正确，环境验证进行中 |
| ⚠️ 未验证 | 历史遗留标记，当前版本已弃用 |
| ❌ 已知问题 | 存在已知 bug，见章节内的⚠️标注 |

> **说明：** 手册的 35 个配套笔记本已通过 `jupyter nbconvert --execute` 验证执行，均有完整输出。代码使用纯合成数据，无需外部数据集。如发现执行问题，欢迎通过 Issue 报告。

---

## 术语表

| 术语 | 说明 |
|------|------|
| RAW | 传感器原始输出，未经 ISP 处理 |
| DNG | Adobe 数字负片格式，常见 RAW 格式 |
| CFA | 颜色滤波阵列，如 RGGB Bayer 排列 |
| OB | 光学黑（Optical Black），用于 BLC 标定 |

## 习题

**练习1（动手实践）** 按照本附录的环境配置步骤，在本地完成以下验证：安装 rawpy 库并成功读取一张 DNG 文件（可使用任意网络上公开的 DNG 样本），打印其 Bayer 阵列尺寸和黑电平值。

**练习2（环境调试）** 如果在安装 `rawpy` 时遇到"libraw not found"错误，有哪些可能的解决方案？在 Windows/Linux/macOS 三个平台上各有什么不同的处理方式？
