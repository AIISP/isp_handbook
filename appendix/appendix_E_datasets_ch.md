# 附录E — 数据集索引 | Dataset Index

> ISP算法训练、评估和基准测试所用公开数据集的参考表。
> 这些数据集上的基准测试结果请参见附录F。

---

## E.1 去噪数据集

### SIDD — 智能手机图像去噪数据集

| 字段 | 详情 |
|-------|---------|
| **数据集** | SIDD（Smartphone Image Denoising Dataset，智能手机图像去噪数据集） |
| **任务** | 真实世界图像去噪 |
| **规模** | 30,000对噪声-干净图像对（320×320裁剪块）；完整尺寸：**320对全分辨率图像对**（160个场景 × 每场景2次拍摄，来自5款智能手机）；基准评估使用验证集中的1280个裁剪块（256×256） |
| **采集** | 5款智能手机（Apple iPhone 7、Google Pixel、Samsung Galaxy S6 Edge、Motorola Nexus 6、LG G4），各ISO（100–3200），多种光照条件 |
| **URL** | https://www.eecs.yorku.ca/~kamel/sidd/ |
| **关键指标** | SIDD验证集上的PSNR（dB）、SSIM（sRGB输出） |
| **备注** | 真实噪声去噪基准测试的事实标准。两个赛道：sRGB（ISP后）和RAW（ISP前）。基准评估使用验证集中的 **1280 个裁剪块（256×256）**。SIDD基准服务器托管在线排行榜。**注意 SIDD 与 SIDD+ 的区别：** 原始 SIDD（2018）提供 160 个场景、30,000 对裁剪块，测试集真值公开；**SIDD+**（2021扩展版）在此基础上增加了更多相机型号和光照条件覆盖，并提供了更严格的在线评估流程——两者的排行榜分数不可直接交叉比较，论文中须明确注明使用的是 SIDD 还是 SIDD+ 评估协议。 |

**使用章节：** 第二卷第03章（降噪）、第三卷第01章（DL ISP综述）、第三卷第02章（端到端图像复原）。

---

### DND — 达姆施塔特噪声数据集

| 字段 | 详情 |
|-------|---------|
| **数据集** | DND（Darmstadt Noise Dataset，达姆施塔特噪声数据集） |
| **任务** | 真实世界图像去噪（sRGB） |
| **规模** | 50张高分辨率图像（5336×4008），1000个裁剪块（512×512）用于评估 |
| **采集** | 4台消费相机；含噪版本 = 高ISO；干净版本 = 低ISO长曝光参考 |
| **URL** | https://noise.visinf.tu-darmstadt.de/ |
| **关键指标** | PSNR、SSIM（在线评估服务器——真值不公开） |
| **备注** | **DND不提供训练数据**——该数据集仅用于推理评估（inference-only benchmark），不含任何训练集或配对噪声图像供模型训练。研究者须在其他数据集（如SIDD、合成噪声等）上训练模型，再向DND服务器提交推理结果获取评分。真值保存在服务器上，防止对测试集过拟合。图像对使用单应性校正进行空间对齐。 |
| **许可证** | 仅限研究（商业用途请联系作者） |

**使用章节：** 第二卷第03章（降噪）。

---

### RealDN — 真实世界降噪基准数据集

| 字段 | 详情 |
|-------|---------|
| **数据集** | RealDN（Real-world Denoising，Zhang et al., 2023） |
| **任务** | 真实世界图像去噪（sRGB域） |
| **规模** | 约 150 对高质量真实噪声配对图像（多种相机设备，多 ISO 级别） |
| **采集** | 固定三脚架拍摄，低ISO无噪声参考 vs 高ISO含噪图像，精确对齐 |
| **URL** | https://github.com/zhangjin12138/RealDN |
| **关键指标** | PSNR（dB）、SSIM |
| **备注** | 2023年发布，弥补 SIDD 场景偏向手机、DND 真值不公开的不足，适合作为额外泛化评估基准。 |

**使用章节：** 第二卷第03章（降噪）。

---

## E.2 RAW处理数据集

### MIT FiveK

| 字段 | 详情 |
|-------|---------|
| **数据集** | MIT-Adobe FiveK数据集 |
| **任务** | RAW转sRGB / 照片修饰；图像增强 |
| **规模** | 5000张RAW图像（各种相机）；每张图像5个专家修饰的sRGB版本 |
| **URL** | https://data.csail.mit.edu/graphics/fivek/ |
| **关键指标** | 与专家C修饰的PSNR、SSIM、ΔE（最常用的参考） |
| **备注** | 专家C标注是学习ISP和照片增强论文的标准参考。广泛用于训练RAW转RGB的学习型ISP网络。输入：DNG RAW；目标：专家C sRGB。 |

**使用章节：** 第三卷第01章（DL ISP综述）。

---

### ZRR（苏黎世RAW转RGB）

| 字段 | 详情 |
|-------|---------|
| **数据集** | Zurich RAW-to-RGB Dataset（ZRR） |
| **任务** | 学习型手机ISP（RAW → sRGB），端到端相机RAW处理 |
| **规模** | ~48,000 RAW/RGB 训练对；1,204 张测试图像（标准评估集） |
| **拍摄设备** | Canon EOS 5D Mark IV（参考 sRGB）+ 华为 P20 Pro（RAW 输入） |
| **URL** | https://data.vision.ee.ethz.ch/ihnatova/ZRR.html |
| **关键指标** | PSNR（dB）、MS-SSIM；AIM/NTIRE Learned ISP 竞赛标准评估集 |
| **备注** | PyNET（CVPRW 2020）、AWNet 等方法的标准评估数据集；Canon EOS 5D Mark IV 拍摄的 RAW 作为高质量参考（Ignatov et al., 2020）。注意：训练对使用 P20 Pro 短焦/长焦对齐；测试集 1,204 张图像为竞赛固定集。 |

**使用章节：** 第三卷第01章（DL ISP综述）、附录F §F.7。

---

## E.3 去马赛克数据集

### Kodak 24

| 字段 | 详情 |
|-------|---------|
| **数据集** | Kodak PhotoCD数据集（24张图像） |
| **任务** | 去马赛克基准测试、图像复原基准 |
| **规模** | 24张无损PNG图像，768×512或512×768 |
| **URL** | http://r0k.us/graphics/kodak/ |
| **关键指标** | 去马赛克输出与原始图像的PSNR、SSIM |
| **备注** | 经典基准。非真实Bayer CFA采集——从全色图像合成Bayer图案用于去马赛克评估。广泛用作通用图像复原基准。 |

**使用章节：** 第二卷第02章（去马赛克）。

---

### McMaster 18

| 字段 | 详情 |
|-------|---------|
| **数据集** | McMaster彩色图像数据集（18张图像） |
| **任务** | CFA去马赛克基准测试 |
| **规模** | 18张全色图像，500×500 |
| **URL** | https://www4.comp.polyu.edu.hk/~cslzhang/CDM_Dataset.htm |
| **关键指标** | CPSNR（颜色PSNR）、SSIM |
| **备注** | 图像经过选择，包含对去马赛克具有挑战性的内容：精细纹理、规则图案、颜色边缘。Kodak 24的补充。去马赛克论文的标准基准。 |

**使用章节：** 第二卷第02章（去马赛克）。

---

## E.4 图像质量评估数据集

### LIVE图像质量评估数据库

| 字段 | 详情 |
|-------|---------|
| **数据集** | LIVE IQA数据库（德克萨斯大学奥斯汀分校） |
| **任务** | 无参考和全参考IQA |
| **规模** | 29张参考图像，约779张畸变图像；5种畸变类型：JPEG、JPEG2000、白噪声、高斯模糊、快速衰落 |
| **URL** | https://live.ece.utexas.edu/research/Quality/subjective.htm |
| **关键指标** | SRCC（Spearman秩相关系数）、PLCC（Pearson线性相关系数）vs. DMOS（差分MOS） |
| **备注** | 最早且被引用最广泛的IQA数据库之一。DMOS（差分平均意见分）是主观质量标注。 |
| **许可证** | 非商业研究免费 |

**使用章节：** 第四卷第04章（感知IQA）。

---

### TID2013

| 字段 | 详情 |
|-------|---------|
| **数据集** | Tampere图像数据库2013 |
| **任务** | 全参考IQA |
| **规模** | 25张参考图像，3000张畸变图像（24种畸变类型 × 5个等级） |
| **URL** | http://www.ponomarenko.info/tid2013.htm |
| **关键指标** | SRCC、PLCC vs. MOS |
| **备注** | 最全面的传统IQA数据集。24种畸变类型，包括噪声、压缩、几何、颜色畸变。MOS由3个国家的971名观察者收集。 |
| **许可证** | 研究免费（CC风格，需注明来源） |

**使用章节：** 第四卷第04章（感知IQA）。

---

### KADID-10k

| 字段 | 详情 |
|-------|---------|
| **数据集** | KADID-10k（康斯坦茨图像数据库） |
| **任务** | 全参考IQA |
| **规模** | 81张参考图像，10,125张畸变图像（25种畸变类型 × 5个等级） |
| **URL** | https://database.mmsp-kn.de/kadid-10k-database.html |
| **关键指标** | SRCC、PLCC vs. DMOS |
| **备注** | 最大的传统畸变IQA数据集。通过Amazon Mechanical Turk众包标注。涵盖25种畸变类型，包括TID2013的所有类型及额外类别。 |

**使用章节：** 第四卷第04章（感知IQA）。

---

### KonIQ-10k

| 字段 | 详情 |
|-------|---------|
| **数据集** | KonIQ-10k（Hosu et al., IEEE TIP 2020） |
| **任务** | 无参考IQA（NR-IQA），真实失真场景下的主观质量预测 |
| **规模** | 10,073张真实互联网图像（来自YFCC100M公开图库），每张图像约120名观察者评分 |
| **URL** | http://database.mmsp-kn.de/koniq-10k-database.html |
| **关键指标** | SRCC、PLCC vs. MOS（均值意见分） |
| **备注** | 目前规模最大的真实失真 NR-IQA 数据集之一。与 LIVE/TID2013 等合成畸变数据集不同，KonIQ-10k 图像来自真实拍摄场景（包含压缩、运动模糊、噪声等真实失真），更适合评估 ISP 输出图像在真实条件下的感知质量。CLIP-IQA、Q-Align 等模型均在此数据集上报告评估结果。 |

**使用章节：** 第四卷第04章（感知IQA）、第五卷第04章（多模态模型）。

---

## E.5 超分辨率数据集

### DIV2K

| 字段 | 详情 |
|-------|---------|
| **数据集** | DIV2K — 多样化2K分辨率数据集 |
| **任务** | 图像超分辨率（×2、×3、×4、×8） |
| **规模** | 1000张高分辨率图像（2K，约1080p或更高）；800训练/100验证/100测试 |
| **URL** | https://data.vision.ee.ethz.ch/cvl/DIV2K/ |
| **关键指标** | PSNR（dB）、Y通道SSIM（YCbCr） |
| **备注** | 图像超分辨率的标准训练数据集。下采样版本用作低分辨率输入。与Flickr2K（2650张图像）配对形成DF2K，是最常用的训练集。 |

**使用章节：** 第三卷第03章（超分辨率）。

---

### RealSR

| 字段 | 详情 |
|-------|---------|
| **数据集** | RealSR — 真实世界超分辨率数据集 |
| **任务** | 真实世界图像超分辨率（基于变焦的配对） |
| **规模** | 596对LR-HR图像对，以不同焦距采集（×2、×3、×4） |
| **URL** | https://github.com/csjcai/RealSR |
| **关键指标** | PSNR、SSIM、LPIPS |
| **备注** | 与合成超分数据集不同，RealSR使用真实光学变焦机制采集LR-HR配对。使用单应性对齐。捕获真实世界退化（镜头模糊、传感器噪声、压缩）。比双三次下采样数据集更真实的基准测试。 |

**使用章节：** 第三卷第03章（超分辨率）。

---

## E.6 低照度图像增强数据集

### LOL — 低照度数据集

| 字段 | 详情 |
|-------|---------|
| **数据集** | LOL（Low-Light dataset，低照度数据集） |
| **任务** | 真实低照度图像增强（LLIE） |
| **规模** | LOL-v1：500对（485训练 + 15测试）；LOL-v2-real：689训练 + 100测试；LOL-v2-synthetic：900训练 + 100测试 |
| **采集** | 真实相机在不同曝光条件下拍摄配对图像（低光 / 正常光）；v2-synthetic通过噪声合成生成 |
| **URL** | https://daooshee.github.io/BMVC2018website/ |
| **关键指标** | PSNR（dB）、SSIM，与正常光参考图对比 |
| **备注** | 低照度增强领域使用最广泛的基准数据集。v1测试集（15张）结果波动较大，v2-real（100张）更稳健。注意：使用`--GT_mean`测试设置的方法PSNR会系统偏高约1–2 dB，对比结果时须确认测试协议一致性。 |

**使用章节：** 第三卷第05章（LLIE）。附录F §F.9有完整基准排行。

---

## E.6.1 近年新增低照度数据集（2023–2024）

### LSRW — 大规模真实世界弱光数据集

| 字段 | 详情 |
|-------|---------|
| **数据集** | LSRW（Large-Scale Real-World Low-Light）低光真实世界数据集 |
| **任务** | 真实低照度图像增强（LLIE），覆盖室内/室外多场景 |
| **规模** | 约 5650 对配对图像（4 台不同设备采集） |
| **采集** | Huawei Mate 40 Pro / P40 Pro / Samsung Galaxy S21 Ultra / iPhone 12 Pro Max，各低光/正常光配对 |
| **URL** | https://github.com/JianghaiSCU/LSRW |
| **关键指标** | PSNR（dB）、SSIM，与正常光参考对比 |
| **备注** | 2022年发布，覆盖多设备多场景，弥补 LOL 数据集场景单一的不足。测试集 30 对。 |

**使用章节：** 第三卷第05章（LLIE）。

---

## E.7 去模糊数据集

### GoPro — 运动去模糊数据集

| 字段 | 详情 |
|-------|---------|
| **数据集** | GoPro 运动去模糊数据集（Nah et al., 2017） |
| **任务** | 图像运动去模糊 |
| **规模** | 3214对（2103训练 + 1111测试），分辨率1280×720 |
| **采集** | 使用GoPro Hero 4 Black以240fps拍摄，对连续帧平均合成模糊图像；对应清晰帧为单帧GT |
| **URL** | https://github.com/SeungjunNah/DeepDeblur-PyTorch |
| **关键指标** | PSNR（dB）、SSIM，全分辨率与GT锐利帧对比 |
| **备注** | 图像去模糊领域的标准基准。模糊由高速视频帧平均合成，比真实手持抖动模糊更均匀但仍能反映运动模糊特征。在线排行榜：https://paperswithcode.com/sota/deblurring-on-gopro |

**使用章节：** 第三卷第02章（端到端图像复原）。附录F §F.3.1有完整基准排行。

---

### RealBlur — 真实世界运动去模糊数据集

| 字段 | 详情 |
|-------|---------|
| **数据集** | RealBlur（Rim et al., ECCV 2020） |
| **任务** | 真实世界图像运动去模糊 |
| **规模** | RealBlur-R（RAW域对齐）和 RealBlur-J（JPEG域对齐）各 3758 对训练 + 980 对测试 |
| **采集** | 真实相机拍摄，固定场景下长/短曝光配对；使用单应性变换精确对齐 |
| **URL** | https://github.com/rimchang/RealBlur |
| **关键指标** | PSNR（dB）、SSIM，分 RealBlur-R 和 RealBlur-J 两子集报告 |
| **备注** | 相比 GoPro 合成模糊，RealBlur 来自真实相机抖动，更能反映手持拍摄去模糊的实际难度。两个子集分别在 RAW 对齐和 JPEG 对齐上评估，适合检验方法对不同域的泛化性。 |

**使用章节：** 第三卷第02章（端到端图像复原）。附录F §F.3.2有完整基准排行。

---

## E.7.1 视频超分辨率数据集

### REDS — 真实世界视频超分辨率数据集

| 字段 | 详情 |
|-------|---------|
| **数据集** | REDS（REalistic and Diverse Scenes dataset，Nah et al., CVPRW 2019） |
| **任务** | 视频超分辨率（×4）、视频去模糊 |
| **规模** | 300 段视频序列（240 训练 + 30 验证 + 30 测试），每段 100 帧，分辨率 1280×720（HR）/ 320×180（LR） |
| **URL** | https://seungjunNah.github.io/Datasets/reds_dataset.html |
| **关键指标** | PSNR（dB）、SSIM，Y 通道 |
| **备注** | NTIRE 2019/2021 视频复原挑战赛官方数据集；涵盖复杂运动、快速模糊和多种场景。常用 REDS4 子集（4 段视频）作为快速验证集，其余用于训练。 |

**使用章节：** 第三卷第03章（超分辨率）、第三卷第02章（端到端图像复原）。

---

### Vimeo-90K — 视频插帧与超分辨率数据集

| 字段 | 详情 |
|-------|---------|
| **数据集** | Vimeo-90K（Xue et al., IJCV 2019） |
| **任务** | 视频超分辨率、视频插帧（VFI）、视频去噪、光流估计 |
| **规模** | 89,800 个三帧短序列（每段 3 帧，448×256），64,612 训练 / 7,824 测试 |
| **URL** | http://toflow.csail.mit.edu/ |
| **关键指标** | PSNR（dB）、SSIM，Y 通道 |
| **备注** | 来自 Vimeo 网站的高质量短视频片段，经严格筛选，内容多样（场景、运动类型丰富）。是视频超分（如 EDVR、BasicVSR）和视频插帧（如 DAIN、RIFE）的标准训练/评估集。 |

**使用章节：** 第三卷第03章（超分辨率）、第三卷第02章（端到端图像复原）。

---

## E.8 颜色恒常性/AWB数据集

### Gehler-Shi（渲染光谱数据集）

| 字段 | 详情 |
|-------|---------|
| **数据集** | Gehler颜色恒常性数据集（又称：SFU Grey Ball数据集，Shi的重新标注版本） |
| **任务** | 计算颜色恒常性/AWB真值 |
| **规模** | 568张图像（Canon 1D和5D）；每张图像有光源颜色真值 |
| **URL** | http://www.cs.sfu.ca/~colour/data/shi_gehler/ |
| **关键指标** | 估计光源与真值光源之间的角误差（度）；均值、中值、最优25%、最差25%角误差 |
| **备注** | 颜色恒常性算法的标准基准。Shi用更精确的光源测量重新标注了Gehler的原始数据集。真值：场景光源下灰球或ColorChecker白色块的RGB。 |
| **许可证** | 仅限研究 |

**使用章节：** 第二卷第05章（AWB）。

---

## E.9 数据集汇总表

| 数据集 | 任务 | 规模 | 关键指标 | URL |
|---------|------|------|-----------|-----|
| SIDD | 真实去噪 | 3万裁剪块 | PSNR/SSIM | york.ca/sidd |
| DND | 真实去噪 | 1000裁剪块 | PSNR/SSIM | visinf.tu-darmstadt.de |
| RealDN | 真实去噪（2023） | ~150对 | PSNR/SSIM | github/zhangjin12138 |
| MIT FiveK | RAW转RGB | 5000 RAW | PSNR/ΔE | csail.mit.edu |
| Kodak 24 | 去马赛克/复原 | 24张图像 | PSNR/SSIM | r0k.us |
| McMaster 18 | 去马赛克 | 18张图像 | CPSNR/SSIM | polyu.edu.hk |
| LIVE | FR+NR IQA | 779张图像 | SRCC/PLCC | utexas.edu |
| TID2013 | FR IQA | 3000张图像 | SRCC/PLCC | ponomarenko.info |
| KADID-10k | FR IQA | 10125张图像 | SRCC/PLCC | mmsp-kn.de |
| KonIQ-10k | NR IQA（真实失真） | 10073张图像 | SRCC/PLCC | mmsp-kn.de/koniq |
| DIV2K | 超分辨率 | 1000张HR | PSNR/SSIM | ethz.ch |
| RealSR | 真实超分 | 596对 | PSNR/LPIPS | github/csjcai |
| LOL-v1 | 低照度增强 | 500对 | PSNR/SSIM | daooshee.github.io |
| LOL-v2-real | 低照度增强 | 789对（689训练+100测试） | PSNR/SSIM | daooshee.github.io |
| LSRW | 低照度增强（2022） | ~5650对 | PSNR/SSIM | github/JianghaiSCU |
| GoPro | 运动去模糊 | 3214对 | PSNR/SSIM | github/SeungjunNah |
| RealBlur | 真实运动去模糊 | 980对测试（×2子集） | PSNR/SSIM | github/rimchang |
| REDS | 视频超分/去模糊 | 300段×100帧 | PSNR/SSIM | seungjunNah.github.io |
| Vimeo-90K | 视频超分/插帧 | 89800段三帧序列 | PSNR/SSIM | toflow.csail.mit.edu |
| Gehler-Shi | AWB/颜色恒常性 | 568张图像 | 角误差 | cs.sfu.ca |

---

## E.10 数据集使用说明

### 许可证注意事项

本处列出的大多数数据集**仅限研究用途**。在将任何数据集用于商业目的前，请核实其许可证条款。要点：

- **MIT FiveK：** 研究用途；原始RAW文件的Adobe许可证请查阅。
- **SIDD：** 基准服务器提交结果公开；数据集下载需要注册。
- **DIV2K：** 非商业研究免费。
- **Gehler-Shi：** 研究用途。

### 下载数据集

使用提供的URL。对于大型数据集（SIDD、DIV2K），考虑直接下载到服务器：

```bash
# 示例：从ETH下载DIV2K训练集HR
wget http://data.vision.ee.ethz.ch/cvl/DIV2K/DIV2K_train_HR.zip
unzip DIV2K_train_HR.zip -d data/DIV2K/

# 示例：下载Kodak 24
for i in $(seq -w 1 24); do
    wget http://r0k.us/graphics/kodak/kodak/kodim${i}.png -P data/kodak/
done
```

### 数据目录约定

本手册假设数据集存储在：

```
data/
├── sidd/
├── dnd/
├── mit_fivek/
├── kodak/
├── mcmaster/
├── live/
├── tid2013/
├── kadid10k/
├── div2k/
├── realsr/
├── lol/            # LOL-v1 和 LOL-v2（子目录分别放 v1/v2-real/v2-synthetic）
├── gopro/          # GoPro 去模糊（train/ + test/ 子目录）
├── realblur/       # RealBlur-R 和 RealBlur-J（子目录分别放 RealBlur_R/RealBlur_J）
├── reds/           # REDS 视频超分（train_sharp/ + train_blur/ + val/ + test/ 子目录）
├── vimeo_90k/      # Vimeo-90K（sequences/ 子目录）
└── gehler_shi/
```

请相应更新各章节笔记本中的路径。

---

## 习题

**练习 1（理解）**
SIDD（Smartphone Image Denoising Dataset）的真值图像（ground truth）获取方法是对同一静止场景连续拍摄多张含噪图像并求平均，而非使用 HDR 合成或参考无噪声相机。请解释：为什么用多帧平均而非 HDR 方法获取真值？在什么条件下多帧平均的结果才近似无噪声（泊松噪声的期望 E[X̄] 收敛到 λ 所需的帧数）？当场景存在微小运动（如空调风吹动窗帘）时，多帧平均真值会引入什么问题？

**练习 2（分析/比较）**
LOL（Low-Light Object）数据集有两个版本：LOL-v1 收集了 500 对低光/正常光图像（实拍，部分场景含轻微运动），LOL-v2 分为 LOL-v2-real（689 对真实数据）和 LOL-v2-synthetic（1000 对合成数据）。请分析：LOL-v1 和 LOL-v2-real 的场景类型有何差异（室内 vs. 室外比例、人工光 vs. 自然光比例）？LOL-v2-synthetic 的合成方法是什么？在同一个低光增强模型上，分别在 v1 和 v2-real 测试集上评测，PSNR 数字为何不可直接跨数据集比较？

**练习 3（实践）**
从 SIDD Medium Dataset 中随机选取 10 对图像（含噪/无噪对），使用 BM3D 和 DnCNN（预训练模型）分别处理含噪图像，计算 PSNR 和 SSIM 与真值的差距。分析：（1）两种方法在不同 ISO 级别（ISO 1600 vs. ISO 6400）下性能变化趋势；（2）SIDD 中哪种手机型号的噪声特性对两种方法的难度差异最大；（3）PSNR 高的结果是否在视觉上一定更好（观察 BM3D 的过平滑现象）。
