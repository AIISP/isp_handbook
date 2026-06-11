# Acknowledgements

This handbook was made possible by the support of open-source projects, academic research, and publicly available technical resources. We extend our sincere gratitude to all contributors and the open-source community.

---

## Core Open-Source Resources

The following resources provided first-hand, directly verifiable technical evidence that underpins the quality of this handbook:

### Qualcomm

| Resource | Description | URL |
|----------|-------------|-----|
| **CAMX Camera Framework** | Qualcomm's official open-source camera pipeline framework, BSD-3 license — code can be directly referenced | https://github.com/quic/camx |
| **CHI-CDK** | Camera Hardware Interface Component Development Kit — includes Chromatix XML schema definitions and parameter structures, fully public | https://github.com/quic/chi-cdk |
| **Camera Kernel Driver** | Qualcomm camera kernel driver hosted by the Linux Foundation on CodeLinaro | https://git.codelinaro.org/clo/la/platform/vendor/opensource/camera-kernel |
| **QCamera HAL (AOSP)** | Qualcomm's camera HAL on AOSP — authoritative Android official mirror | https://android.googlesource.com/platform/hardware/qcom/camera/ |
| **Chromatix SDK** | Official Qualcomm camera tuning toolchain page *(free QDN account required)* | https://developer.qualcomm.com/software/chromatix |
| **Spectra ISP Technical Brief** | Official PDF, no login required | https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/qualcomm-spectra-isp.pdf |

### MediaTek

| Resource | Description | URL |
|----------|-------------|-----|
| **Imagiq ISP Technology Overview** | Official technology page with feature and specification overview | https://www.mediatek.com/technology/imagiq |
| **Hot Chips 34 (2022)** | Dimensity 9000 chip architecture paper by MediaTek engineers — **the highest-depth public technical document available** | https://hotchips.org/archives/hc34/ |
| **Linux Kernel MTK ISP Driver** | kernel.org mainline, V4L2 ISP driver source for MT8183/MT8192 | https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/media/platform/mediatek |
| **Kernel Patch Submissions** | patchwork.kernel.org — includes ISP design rationale and architecture discussions | https://patchwork.kernel.org/project/linux-mediatek/list/ |
| **Dimensity 9000 Product Page** | Imagiq 790 ISP specifications | https://www.mediatek.com/products/smartphones-2/dimensity-9000 |
| **Corporate Press Releases** | Launch announcements for each chipset generation | https://corp.mediatek.com/news-events/press-releases/ |

### HiSilicon (海思)

| Resource | Description | URL |
|----------|-------------|-----|
| **OpenHarmony Camera HAL** | Official open-source repository (Gitee) — camera pipeline, buffer management, ISP control interface | https://gitee.com/openharmony/drivers_peripheral_camera |
| **OpenHarmony HiSilicon SoC Code** | Sensor driver stubs and ISP initialization configuration | https://gitee.com/openharmony/device_soc_hisilicon |
| **Google Patents — HiSilicon ISP** | Covers AWB, denoising, HDR tone mapping, XD-Fusion multi-frame fusion — **patents are the richest legally public source of algorithmic detail** | https://patents.google.com/?assignee=HiSilicon+Technologies&q=ISP |
| **CNIPA Patent Database** | Search applicant "海思半导体有限公司", IPC class G06T5 or H04N23 | https://pss-system.cponline.cnipa.gov.cn/ |
| **HuaweiTech Technical Journal** | Engineer-authored articles on Kirin ISP architecture and computational photography | https://www.huawei.com/en/huaweitech |
| **HarmonyOS Camera API Docs** | Application-level camera API — shows the ISP control interface exposed to the OS | https://developer.huawei.com/consumer/en/doc/harmonyos-guides/camera-overview |

---

## General Standards and Platforms

| Resource | Description | URL |
|----------|-------------|-----|
| **Android Camera HAL3 Documentation** | Google's official Camera HAL3 architecture specification | https://source.android.com/docs/core/camera |
| **V4L2 Kernel Interface Docs** | Linux Video for Linux 2 API — standard interface for ISP kernel drivers | https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/v4l2.html |
| **AOSP Camera Framework Source** | Android camera service and HAL abstraction layer | https://android.googlesource.com/platform/frameworks/av/+/refs/heads/main/camera/ |

---

## Datasets and Benchmarks

Algorithm evaluations in this handbook reference the following public datasets:

- **SIDD** (Smartphone ISP Denoising Dataset) — smartphone noise reduction benchmark
- **DND** (Darmstadt Noise Dataset) — real-camera noise dataset
- **MIT FiveK** — image enhancement dataset (5,000 RAW images + expert retouching)
- **Gehler-Shi ColorChecker** — AWB color constancy benchmark
- **DIV2K** — super-resolution training and evaluation dataset

---

## Citation Notice

This handbook follows academic citation standards; all content credits its sources. Open-source code is cited in compliance with respective project licenses (BSD-3, Apache-2.0, GPL-2.0, etc.). Patent content constitutes publicly disclosed information and is cited with patent number and applicant name.

If you find citation errors or omissions, please submit feedback via GitHub Issues.

---

*This handbook is an open-source project. Community contributions are welcome.*
