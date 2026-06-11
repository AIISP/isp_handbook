# 致谢

本手册的编写得益于以下开源项目、学术研究和公开技术资料的支持。我们向所有贡献者和开源社区致以诚挚的感谢。

---

## 核心开源资源

以下资源为本手册提供了可直接验证的一手技术依据，是内容质量的重要保障：

### Qualcomm 高通

| 资源 | 说明 | 链接 |
|------|------|------|
| **CAMX 相机框架** | Qualcomm 官方开源相机流水线框架，BSD-3 许可，可直接引用代码实现 | https://github.com/quic/camx |
| **CHI-CDK** | Camera Hardware Interface 组件开发套件，包含 Chromatix XML schema 定义和参数结构，完全公开 | https://github.com/quic/chi-cdk |
| **相机内核驱动** | Linux Foundation 托管的 Qualcomm 相机内核驱动，CodeLinaro 官方镜像 | https://git.codelinaro.org/clo/la/platform/vendor/opensource/camera-kernel |
| **QCamera HAL (AOSP)** | AOSP 上的高通相机 HAL 代码，Android 官方权威镜像 | https://android.googlesource.com/platform/hardware/qcom/camera/ |
| **Chromatix SDK** | 高通相机调参工具链官方页面 *(需注册 QDN 账号)* | https://developer.qualcomm.com/software/chromatix |
| **Spectra ISP 技术概述** | 官方 PDF，无需登录 | https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/qualcomm-spectra-isp.pdf |

### MediaTek 联发科

| 资源 | 说明 | 链接 |
|------|------|------|
| **Imagiq ISP 技术总览** | 官方技术页面，功能与规格概述 | https://www.mediatek.com/technology/imagiq |
| **Hot Chips 34（2022）** | 联发科工程师发表的天玑9000芯片架构论文，**目前最高深度的公开技术文献** | https://hotchips.org/archives/hc34/ |
| **Linux 内核 MTK ISP 驱动** | kernel.org mainline，含 MT8183/MT8192 ISP V4L2 驱动源码 | https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/media/platform/mediatek |
| **内核补丁提交记录** | patchwork.kernel.org，含 ISP 设计说明和架构讨论 | https://patchwork.kernel.org/project/linux-mediatek/list/ |
| **天玑9000产品页** | Imagiq 790 ISP 规格 | https://www.mediatek.com/products/smartphones-2/dimensity-9000 |
| **企业新闻稿** | 各代芯片发布公告 | https://corp.mediatek.com/news-events/press-releases/ |

### HiSilicon 海思麒麟

| 资源 | 说明 | 链接 |
|------|------|------|
| **OpenHarmony Camera HAL** | 官方开源仓库（Gitee），含相机流水线和 ISP 控制接口定义 | https://gitee.com/openharmony/drivers_peripheral_camera |
| **OpenHarmony HiSilicon SoC 代码** | 传感器驱动 stub 和 ISP 初始化配置 | https://gitee.com/openharmony/device_soc_hisilicon |
| **Google Patents 海思 ISP 专利** | 涵盖 AWB、降噪、HDR、XD-Fusion 多帧融合等核心算法专利，**专利是技术细节最丰富的合法公开资料** | https://patents.google.com/?assignee=HiSilicon+Technologies&q=ISP |
| **CNIPA 国家知识产权局** | 检索申请人"海思半导体有限公司"+ 分类号 G06T5/H04N23 | https://pss-system.cponline.cnipa.gov.cn/ |
| **HuaweiTech 技术期刊** | 华为工程师撰写的技术文章，含 Kirin ISP 架构与计算摄影 | https://www.huawei.com/en/huaweitech |
| **HarmonyOS Camera API 文档** | 应用层摄像头 API，展示 ISP 向操作系统暴露的控制接口 | https://developer.huawei.com/consumer/en/doc/harmonyos-guides/camera-overview |

---

## 通用标准与平台

| 资源 | 说明 | 链接 |
|------|------|------|
| **Android Camera HAL3 官方文档** | Google 官方 Camera HAL3 架构规范，所有 Android 相机实现的基础 | https://source.android.com/docs/core/camera |
| **V4L2 内核接口文档** | Linux Video for Linux 2 API，ISP 内核驱动的标准接口 | https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/v4l2.html |
| **AOSP 相机框架源码** | Android 相机服务和 HAL 抽象层 | https://android.googlesource.com/platform/frameworks/av/+/refs/heads/main/camera/ |

---

## 学术数据集与评测基准

本手册中的算法评估参考了以下公开数据集：

- **SIDD**（Smartphone ISP Denoising Dataset）— 智能手机降噪基准
- **DND**（Darmstadt Noise Dataset）— 真实相机噪声数据集
- **MIT FiveK** — 图像增强数据集（5000张 RAW + 专家调色）
- **Gehler-Shi ColorChecker** — AWB 色彩恒常性基准
- **DIV2K** — 超分辨率训练与评估数据集

---

## 引用声明

本手册遵循学术引用规范，所有内容均注明来源。引用开源代码时遵循各项目许可协议（BSD-3、Apache-2.0、GPL-2.0 等）。专利内容属于公开披露信息，引用时注明专利号和申请人。

如发现引用错误或遗漏，欢迎通过 GitHub Issues 提交反馈。

---

*本手册为开源项目，欢迎社区贡献。*
