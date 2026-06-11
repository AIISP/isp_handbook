# 附录H — 参考文献 | References

> ISP算法手册的主参考文献列表，按主题分类。
> 引用格式为作者-年份。已知完整文献信息均予提供。

---

## H.1 教材 — 成像物理与光学

**[Hecht2017]** Hecht, E., *Optics*（光学，第5版）, Pearson, 2017.
> 经典光学教材。涵盖波动光学、几何光学、像差、干涉、衍射。参见第一卷第02章。

**[Born1999]** Born, M., & Wolf, E., *Principles of Optics*（光学原理，第7版）, Cambridge University Press, 1999.
> 物理光学的全面论述，包括相干理论和成像。第一卷第02章的进阶参考。

**[Holst2011]** Holst, G. C., & Lomheim, T. S., *CMOS/CCD Sensors and Camera Systems*（CMOS/CCD传感器与相机系统，第2版）, JCD Publishing, 2011.
> 传感器物理参考：量子效率、满阱容量、暗电流、噪声来源。参见第一卷第04章。

**[Nakamura2006]** Nakamura, J., *Image Sensors and Signal Processing for Digital Still Cameras*（数码相机的图像传感器与信号处理）, CRC Press, 2006.
> 涵盖CMOS/CCD传感器设计和ISP流水线实现的实践参考。参见第一卷和第二卷。

---

## H.2 噪声模型

**[Foi2008]** Foi et al., "Practical Poissonian-Gaussian noise modeling and fitting for single-image raw-data", *IEEE Transactions on Image Processing*, 2008.
> RAW图像的标准泊松-高斯噪声模型。定义PTC模型σ²(I) = αI + β。参见第一卷第04章。

**[Healey1994]** Healey & Kondepudy, "Radiometric CCD camera calibration and noise estimation", *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 1994.
> CCD噪声标定的早期工作。PTC测量方法的基础。

**[Plotz2017]** Plötz & Roth, "Benchmarking denoising algorithms with real photographs", *CVPR*, 2017.
> 引入DND去噪基准数据集。描述了采集真实噪声-干净图像对的方法。

**[Abdelhamed2018]** Abdelhamed et al., "A high-quality denoising dataset for smartphone cameras", *CVPR*, 2018.
> 引入SIDD数据集。详述了智能手机真实噪声真值的采集方案。参见第二卷第03章、附录E。

---

## H.3 颜色科学

**[Wyszecki1982]** Wyszecki, G., & Stiles, W. S., *Color Science: Concepts and Methods, Quantitative Data and Formulae*（颜色科学：概念、方法、定量数据与公式，第2版）, Wiley, 1982.
> 权威颜色科学参考。涵盖CIE标准、颜色匹配函数、色差公式。参见第一卷第05章。

**[Fairchild2013]** Fairchild, M. D., *Color Appearance Models*（颜色外貌模型，第3版）, Wiley, 2013.
> 颜色外貌模型，包括CIECAM02。涵盖色度适应、颜色恒常性和感知属性。参见第一卷第05章、第二卷第06章。

**[Sharma2005]** Sharma et al., "The CIEDE2000 color-difference formula", *Color Research & Application*, 2005.
> 定义CIEDE2000（ΔE₀₀）色差公式的权威论文。参见第二卷第06章、附录A、附录G。

**[Reinhard2010]** Reinhard, E., et al., *High Dynamic Range Imaging: Acquisition, Display, and Image-Based Lighting*（高动态范围成像：采集、显示与基于图像的照明，第2版）, Morgan Kaufmann, 2010.
> 全面的HDR成像参考。涵盖色调映射、HDR采集和显示。参见第二卷第07章、第二卷第10章。

**[Ebner2007]** Ebner, M., *Color Constancy*（颜色恒常性）, Wiley, 2007.
> 颜色恒常性算法的全面介绍。第二卷第05章AWB的基础。

---

## H.4 传统ISP算法

### 去马赛克

**[Malvar2004]** Malvar et al., "High-quality linear interpolation for demosaicing of Bayer-patterned color images", *ICASSP*, 2004.
> Malvar-He-Cutler（MHC）去马赛克算法。快速，二阶精度。参见第二卷第02章。

**[Menon2007]** Menon et al., "Demosaicing with directional filtering and a posteriori decision", *IEEE Transactions on Image Processing*, 2007.
> DDFAPD去马赛克算法。参见第二卷第02章。

**[Getreuer2011]** Getreuer, "Malvar-He-Cutler linear image demosaicking", *Image Processing On Line*, 2011.
> 含完整算法推导和代码的开放获取IPOL论文。参见第二卷第02章。

**[Zhang2005]** Zhang & Wu, "Color demosaicking via directional linear minimum mean square-error estimation", *IEEE Transactions on Image Processing*, 2005.
> LMMSE去马赛克；参见RawTherapee实现。

### 去噪

**[Dabov2007]** Dabov et al., "Image denoising by sparse 3-D transform-domain collaborative filtering", *IEEE Transactions on Image Processing*, 2007.
> BM3D算法。最先进的非局部去噪。参见第二卷第03章。

**[Buades2005]** Buades et al., "A non-local algorithm for image denoising", *CVPR*, 2005.
> NL-means算法。非局部去噪的基础。参见第二卷第03章。

**[Tomasi1998]** Tomasi & Manduchi, "Bilateral filtering for gray and color images", *ICCV*, 1998.
> 双边滤波器——保边空间去噪。参见第二卷第03章。

### 白平衡

**[Buchsbaum1980]** Buchsbaum, "A spatial processor model for object colour perception", *Journal of the Franklin Institute*, 1980.
> 颜色恒常性的灰世界假设。参见第二卷第05章。

**[Joze2012]** Joze & Drew, "Exemplar-based color constancy and multiple illumination", *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 2012.
> 颜色恒常性方法综述。参见第二卷第05章。

**[Cheng2014]** Cheng et al., "Illuminant estimation for color constancy: why spatial-domain methods work and the role of the color distribution", *Journal of the Optical Society of America A*, 2014.

### 镜头阴影校正

**[Goldman2010]** Goldman, "Vignette and exposure calibration and compensation", *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 2010.
> 渐晕模型与标定。参见第二卷第08章。

### 色彩校正矩阵

**[Finlayson2015]** Finlayson & Mackiewicz, "Optimization of colour correction matrices", *IS&T/SPIE Electronic Imaging*, 2015.
> CCM优化策略。参见第二卷第06章。

---

## H.5 深度学习ISP

**[Chen2018]** Chen et al., "Learning to see in the dark", *CVPR*, 2018.
> See-in-the-Dark（SID）网络。极低光照下端到端RAW转RGB。参见第三卷第02章。

**[Ignatov2020]** Ignatov et al., "AIM 2020 challenge on learned image signal processing pipeline", *ECCV Workshops*, 2020.
> 学习型ISP竞赛。回顾多种端到端ISP方法。参见第三卷第01章。

**[Zamir2022]** Zamir et al., "Restormer: Efficient transformer for high-resolution image restoration", *CVPR*, 2022.
> 基于Transformer的图像复原架构。参见第三卷第02章。

**[Chen2022]** Chen et al., "Simple baselines for image restoration (NAFNet)", *ECCV*, 2022.
> NAFNet架构；SIDD基准上的强力结果。参见第三卷第02章、附录D。

**[Liang2021]** Liang et al., "SwinIR: Image restoration using swin transformer", *ICCV Workshops*, 2021.
> SwinIR；用于图像复原的Swin Transformer。参见第三卷第02章、第三卷第03章。

**[Wang2021]** Wang et al., "Real-ESRGAN: Training real-world blind super-resolution with pure synthetic data", *ICCV Workshops*, 2021.
> Real-ESRGAN；实用的盲超分辨率。参见第三卷第03章、附录D。

**[Lehtinen2018]** Lehtinen et al., "Noise2Noise: Learning image restoration without clean data", *ICML*, 2018.
> 无干净目标图像的去噪。参见第二卷第03章、附录D。

**[Zhang2017]** Zhang et al., "Beyond a Gaussian denoiser: Residual learning of deep CNN for image denoising", *IEEE Transactions on Image Processing*, 2017.
> DnCNN。残差学习用于去噪。参见第二卷第03章、第三卷第01章。

**[Cai2023]** Cai et al., "Retinexformer: One-stage Retinex-based Transformer for Low-light Image Enhancement", *ICCV*, 2023.
> Retinexformer；单阶段 Retinex Transformer 低光增强，在 LOL-v1/v2、SMID 等多项基准上达到 SOTA。参见第三卷第05章、附录E、附录F §F.9。

**[Jiang2023]** Jiang et al., "Low-Light Image Enhancement with Wavelet-based Diffusion Models", *NeurIPS*, 2023.
> DiffLL；基于小波扩散模型的低光增强，LLIE 领域扩散模型应用代表工作。注意：使用 `--GT_mean` 测试设置，PSNR 系统偏高约 1–2 dB。参见附录F §F.9。

**[Mildenhall2020]** Mildenhall et al., "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis", *ECCV*, 2020.
> NeRF；用多层感知机隐式表示三维场景并通过可微体渲染合成新视角。引入神经辐射场概念，是三维场景表示与计算摄影的基础性工作。参见第三卷第15章（NeRF与3D高斯散射）。

**[Ho2020]** Ho et al., "Denoising diffusion probabilistic models", *NeurIPS*, 2020.
> DDPM；使用迭代扩散的基础生成模型。参见第五卷。

**[Radford2021]** Radford et al., "Learning transferable visual models from natural language supervision (CLIP)", *ICML*, 2021.
> CLIP；对比语言-图像预训练。视觉-语言对齐的基础模型。参见第五卷第01章。

**[Kirillov2023]** Kirillov et al., "Segment anything (SAM)", *ICCV*, 2023.
> SAM（Segment Anything Model，分割一切模型）；可提示分割基础模型。参见第五卷第01章。

**[Wang2019EDVR]** Wang et al., "EDVR: Video restoration with enhanced deformable convolutional networks", *CVPR Workshops (NTIRE)*, 2019.
> EDVR；可变形卷积对齐 + 时序注意力融合。视频超分和视频降噪的核心基准，REDS4 ×4 PSNR = 31.09 dB。参见第三卷第08章（视频降噪）、附录F §F.2.5。

**[Chan2022BasicVSR]** Chan et al., "BasicVSR++: Improving video super-resolution with enhanced propagation and alignment", *CVPR*, 2022.
> BasicVSR++；双向传播 + 光流对齐。REDS4 ×4 PSNR = 32.39 dB，视频超分领域最常引用的强基线之一。参见附录F §F.2.5。

---

## H.6 图像质量评估

**[Wang2004]** Wang et al., "Image quality assessment: From error visibility to structural similarity", *IEEE Transactions on Image Processing*, 2004.
> SSIM。被引用最多的IQA论文。参见第四卷。

**[Zhang2018]** Zhang et al., "The unreasonable effectiveness of deep features as a perceptual metric", *CVPR*, 2018.
> LPIPS。通过深度特征衡量感知相似度。参见第四卷第04章。

**[Mittal2012]** Mittal et al., "No-reference image quality assessment in the spatial domain", *IEEE Transactions on Circuits and Systems for Video Technology*, 2012.
> BRISQUE。盲空间域NR-IQA。参见第四卷第04章。

**[Zhang2015]** Zhang et al., "A feature-enriched completely blind image quality evaluator", *IEEE Transactions on Image Processing*, 2015.
> IL-NIQE。自然图像质量评估器。参见第四卷第04章。

**[Fang2020]** Fang et al., "Perceptual quality assessment of smartphone photography", *CVPR*, 2020.
> SPAQ数据集与模型。参见第四卷第04章。

**[Wu2024QBench]** Wu et al., "Q-Bench: A Benchmark for General-Purpose Foundation Models on Low-Level Vision", *ICLR 2024 (Spotlight)*. arXiv:2309.14181.
> Q-Bench；评测 MLLM（GPT-4V、InstructBLIP 等）的低层视觉感知能力，含 LLVisionQA（问答）、LLDescribe（文字描述）、Quality Scoring（MOS 对齐评分）三项任务。GPT-4V zero-shot 答对率约 73.4%，与人类专家（约88%）仍有差距。参见第四卷第04章、第五卷第03章。

**[Wang2024QAlign]** Wang et al., "Q-Align: Teaching LMMs for Visual Scoring via Discrete Text-Defined Levels", *ICML*, 2024. arXiv:2312.17090.
> Q-Align；将 mPLUG-Owl2 等通用 MLLM 通过离散质量等级标签（Bad/Poor/Fair/Good/Excellent）对齐微调，在 KonIQ-10k（SRCC=0.921）、SPAQ（SRCC=0.917）、AVA（SRCC=0.752）上达到 SOTA，支持图像质量+美学评估统一模型。注意勿与 Q-Bench（ICLR 2024）混淆：Q-Bench 是评测基准，Q-Align 是微调方法。参见第四卷第04章、第五卷第03章。

---

## H.7 数据集

**[Ponomarenko2015]** Ponomarenko et al., "Image database TID2013: Peculiarities, results and perspectives", *Signal Processing: Image Communication*, 2015.
> TID2013数据集。参见附录E。

**[Lin2019]** Lin et al., "KADID-10k: A large-scale artificially distorted IQA database", *IEEE QoMEX*, 2019.
> KADID-10k数据集。参见附录E。

**[Agustsson2017]** Agustsson & Timofte, "NTIRE 2017 challenge on single image super-resolution: Dataset and study", *CVPR Workshops*, 2017.
> DIV2K数据集。参见附录E。

**[Wei2018]** Wei et al., "Deep retinex decomposition for low-light enhancement", *BMVC*, 2018.
> RetinexNet与LOL数据集（LOL-v1）。参见附录E §E.6、附录F §F.9。

**[Yang2020]** Yang et al., "From fidelity to perceptual quality: A semi-supervised approach for low-light image enhancement", *CVPR*, 2020.
> LOL-v2数据集。参见附录E §E.6。

**[Nah2017]** Nah et al., "Deep multi-scale convolutional neural network for dynamic scene deblurring", *CVPR*, 2017.
> GoPro去模糊数据集。参见附录E §E.6、附录F §F.3.1。

**[Sheikh2006]** Sheikh et al., "A statistical evaluation of recent full reference image quality assessment algorithms", *IEEE Transactions on Image Processing*, 2006.
> LIVE IQA数据库。29张参考图像，~779张畸变图像，5种畸变类型。参见附录E §E.4、附录F §F.6.4。

**[Ignatov2020PyNET]** Ignatov et al., "Replacing mobile camera ISP with a single deep learning model", *CVPR Workshops*, 2020.
> ZRR（苏黎世RAW转RGB）数据集与PyNET方法；Canon EOS 5D Mark IV 参考 sRGB + 华为 P20 Pro RAW。参见附录E §E.2、附录F §F.7.4。

---

## H.8 标准与技术报告

**[IEC61966]** IEC 61966-2-1:1999, *Multimedia systems and equipment — Colour measurement and management — Part 2-1: Default RGB colour space — sRGB*, International Electrotechnical Commission, 1999.
> sRGB标准。定义sRGB传递函数和基色。参见第二卷第07章。

**[ITU-R BT.709]** ITU-R BT.709-6:2015, *Parameter values for the HDTV standards for production and international programme exchange*, International Telecommunication Union, 2015.
> Rec. 709标准。HDTV基色、传递函数。参见第二卷第07章。

**[ITU-R BT.2020]** ITU-R BT.2020-2:2015, *Parameter values for ultra-high definition television systems for production and international programme exchange*, International Telecommunication Union, 2015.
> Rec. 2020 / BT.2020。UHD/HDR视频的宽色域标准。参见第二卷第21章。

**[ITU-R BT.2100]** ITU-R BT.2100-2:2018, *Image parameter values for high dynamic range television for use in production and international programme exchange*, International Telecommunication Union, 2018.
> HDR标准：HLG和PQ（ST 2084）传递函数。参见第二卷第07章、第二卷第19章。

**[ISO12233]** ISO 12233:2017, *Photography — Electronic still picture imaging — Resolution and spatial frequency responses*, International Organization for Standardization, 2017.
> 倾斜边缘MTF测量标准（现行版本2017年）。参见第二卷第04章、附录B。

**[EMVA1288]** EMVA, "Standard for Characterization of Image Sensors and Cameras (EMVA 1288 Release 4.0)", 官方文档, 2021. URL: https://www.emva.org/standards-technology/emva-1288/
> 定义机器视觉相机的PTC测量、噪声模型标定、SNR特性描述。参见第一卷第04章。

---

## H.9 公开课程与教程

**[Szeliski2022]** Szeliski, R., *Computer Vision: Algorithms and Applications*（计算机视觉：算法与应用，第2版）, Springer, 2022. URL: https://szeliski.org/Book/
> 全面的计算机视觉教材。包含图像形成、传感器和图像处理章节。参见第一卷。

**[Brown2019]** Brown, M. S., "Understanding the in-camera image processing pipeline for computer vision", *CVPR Tutorial*, 2019. URL: https://www.eecg.utoronto.ca/~mbrown/CVPR2019_ISP_tutorial.html
> 从计算机视觉角度对ISP流水线的系统性综述，适合入门参考。

**[Imatest Documentation]** Imatest LLC, "Imatest Documentation", 官方文档, 2023. URL: https://www.imatest.com/docs/
> 涵盖MTF、噪声、颜色、畸变及其他IQA测量方法的公开文档。手册全文评估方法的主要参考。

**[colour-science Documentation]** colour-science.org contributors, "colour — Colour Science for Python", 官方文档, 2023. URL: https://colour.readthedocs.io/
> 全面的颜色科学库文档，每个函数均附数学背景。参见第一卷第05章、第二卷第05章、第二卷第06章。

**[Stanford CS231n]** Li et al., *CS231n: Convolutional Neural Networks for Visual Recognition*, Stanford University, 2017. URL: http://cs231n.stanford.edu/
> 视觉识别深度学习课程。参见第三卷DL ISP。

---

## H.10 重要综述论文

**[Kaur2021]** Kaur et al., "A survey on image restoration: Insights and future directions", *Image and Vision Computing*, 2021.
> 传统和深度学习图像复原方法综述。

**[Liu2020]** Liu et al., "Deep learning for pixel-level image fusion: Recent advances and future prospects", *Information Fusion*, 2020.

**[Zamir2020]** Zamir et al., "Learning enriched features for real image restoration and enhancement", *ECCV*, 2020.
> MIRNet；多尺度特征学习用于复原。

**[Chen2021]** Chen et al., "Pre-trained image processing transformer", *CVPR*, 2021.
> IPT；用于多种图像复原任务的Transformer。

---

## H.11 平台技术文档与公开资源

> 本节收录各主要平台的**官方公开**技术文档、开源代码、新闻稿和公开演讲。
> 所有链接均指向公开可访问资源，引用不涉及内部保密资料。

### 高通（Qualcomm）

**[Qualcomm-CamX-OSS]** Qualcomm Technologies Inc., "CAMX — Camera eXtension Open Source Framework (BSD-3-Clause-Clear)", 官方文档, 2022. URL: https://github.com/quic/camx

**[Qualcomm-Spectra480]** Qualcomm Technologies Inc., "Qualcomm Spectra 480 ISP Technical Reference — Robotics RB5 Platform", 官方文档, 2023. URL: https://docs.qualcomm.com/bundle/publicresource/topics/80-88500-4/124_Qualcomm_Spectra_480.html

**[Qualcomm-Spectra-ISP-Infographic]** Qualcomm Technologies Inc., "Qualcomm Spectra ISP Infographic (Snapdragon 820)", 官方文档, 2016. URL: https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/snap820_spectraisp_infographic_fnl.pdf

**[Qualcomm-8Gen1-Brief]** Qualcomm Technologies Inc., "Snapdragon 8 Gen 1 Mobile Platform Product Brief", 官方文档, 2021. URL: https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/snapdragon-8-gen-1-mobile-platform-product-brief.pdf

**[Qualcomm-Spectra580-Blog]** Qualcomm Technologies Inc., "Triple Down on the Future of Photography with Qualcomm Snapdragon 888", 博客, 2020. URL: https://www.qualcomm.com/news/onq/2020/12/triple-down-future-photography-qualcomm-snapdragon-888

**[Qualcomm-Imaging-Whitepaper]** Qualcomm Technologies Inc., "Breakthrough Mobile Imaging Experiences — Whitepaper", 官方文档, 2015. URL: https://www.qualcomm.com/media/documents/files/whitepaper-breakthrough-mobile-imaging-experiences.pdf

### 联发科（MediaTek）

**[MTK-HotChips34]** Wang et al., "MediaTek Dimensity 9000 Architecture", *IEEE Hot Chips 34*, 2022. URL: https://hc34.hotchips.org/assets/program/conference/day2/Mobile%20and%20Edge/HC2022.Mediatek.EricbillWang.v08.pptx.pdf

### 三星（Samsung）

**[Samsung-ISOCELL-Tech]** Samsung Semiconductor, "ISOCELL Mobile Image Sensor — Official Technology Overview", 官方文档, 2023. URL: https://semiconductor.samsung.com/image-sensor/mobile-image-sensor/

**[Samsung-ISOCELL-HP2-IISW]** Choi S. et al. (Samsung Electronics), "World Smallest 200MP CMOS Image Sensor with 0.56μm Pixel Equipped with Novel Deep Trench Isolation Structure", *International Image Sensor Workshop (IISW)*, 2023. [Paper R1.3] URL: https://imagesensors.org/Past%20Workshops/2023%20Workshop/2023%20Papers/R1.pdf

### 苹果（Apple）

**[Apple-ProRAW-Developer]** Apple Inc., "Capturing Photos in RAW and Apple ProRAW Formats", 官方文档, 2023. URL: https://developer.apple.com/documentation/avfoundation/capturing-photos-in-raw-and-apple-proraw-formats

**[Apple-ProRes-RAW-Whitepaper]** Apple Inc., "Apple ProRes RAW White Paper", 官方文档, 2020. URL: https://www.apple.com/final-cut-pro/docs/Apple_ProRes_RAW.pdf

### 华为（Huawei）

**[Huawei-RYYB-Community]** Huawei Consumer, "Tech Class #11: Three Minutes to Understand RYYB Sensor", 博客, 2019. URL: https://consumer.huawei.com/en/community/details/topicId-10303/

**[Huawei-AISP-Patent]** Huawei Technologies Co., Ltd., "US Patent 11,625,815: Image Processor and Method Using AI Models for ISP Pipeline", 专利文献, 2023. URL: https://patents.justia.com/patent/11625815

**[OpenHarmony-Camera-HAL]** OpenHarmony Project, "Camera HAL Driver Source Code — drivers_peripheral_camera", 官方文档, 2023. URL: https://gitee.com/openharmony/drivers_peripheral_camera

### OPPO

**[OPPO-MariSilicon-X-Press]** OPPO, "OPPO Unveils 6nm Cutting-edge Imaging NPU — MariSilicon X", 官方文档, 2021. URL: https://www.oppo.com/en/newsroom/press/oppo-imaging-npu-marisilicon-x/

### vivo

**[vivo-V1-Launch]** Gizmochina, "vivo V1 officially launched as the company's first self-developed ISP chip", 博客, 2021. URL: https://www.gizmochina.com/2021/09/06/vivo-v1-isp-chip-launched/

**[vivo-V2-Official]** vivo Global, "vivo releases V2 chip: a Newly Updated ISP", 官方文档, 2022. URL: https://www.vivoglobal.ph/a-Newly-Updated-ISP/

### Google

**[Google-HDRPlus-Paper]** Hasinoff et al., "Burst Photography for High Dynamic Range and Low-Light Imaging on Mobile Cameras", *ACM SIGGRAPH Asia*, 2016. URL: http://graphics.stanford.edu/papers/hdrp/hasinoff-hdrplus-sigasia16-preprint.pdf

### 开放标准

**[AOSP-Camera-HAL3]** Android Open Source Project, "Camera HAL3 Interface Specification", 官方文档, 2023. URL: https://source.android.com/docs/core/camera

**[MIPI-CSI2]** MIPI Alliance, "MIPI CSI-2 Specification (Public Summary)", 官方文档, 2023. URL: https://www.mipi.org/specifications/csi-2

**[Linux-V4L2]** Linux Kernel, "Video for Linux 2 (V4L2) Documentation", 官方文档, 2023.

---

## H.12 2024 年重要进展补充

> 本节收录 CVPR / ECCV / NeurIPS / ICLR 2024 中与 ISP 算法手册核心主题直接相关的重要论文，
> 按主题分类，格式与正文保持一致。

### 超分辨率（Super-Resolution）

**[Wu2024SeeSR]** Wu et al., "SeeSR: Towards Semantics-Aware Real-World Image Super-Resolution", *CVPR 2024*, pp. 25456–25467. [[Paper](https://openaccess.thecvf.com/content/CVPR2024/html/Wu_SeeSR_Towards_Semantics-Aware_Real-World_Image_Super-Resolution_CVPR_2024_paper.html)]
> SeeSR；将 CLIP 提取的语义特征注入扩散模型先验，实现语义感知的真实世界超分辨率，有效抑制错误纹理幻觉。参见第三卷第03章。

**[Sun2024CoSeR]** Sun et al., "CoSeR: Bridging Image and Language for Cognitive Super-Resolution", *CVPR 2024*, pp. 25868–25878. [[Paper](https://openaccess.thecvf.com/content/CVPR2024/html/Sun_CoSeR_Bridging_Image_and_Language_for_Cognitive_Super-Resolution_CVPR_2024_paper.html)]
> CoSeR；利用图像-语言多模态理解在超分中注入场景语义先验，防止全局语义细节的遗漏，对人脸、文字等语义区域效果显著。参见第三卷第03章。

**[Zheng2024SARD]** Zheng et al., "Self-Adaptive Reality-Guided Diffusion for Artifact-Free Super-Resolution", *CVPR 2024*, pp. 25806–25816. [[Paper](https://openaccess.thecvf.com/content/CVPR2024/html/Zheng_Self-Adaptive_Reality-Guided_Diffusion_for_Artifact-Free_Super-Resolution_CVPR_2024_paper.html)]
> 自适应现实引导扩散超分；通过真实感引导扩散采样路径抑制扩散模型常见的伪影，提升真实世界超分的感知-保真均衡。参见第三卷第03章。

---

### 图像复原与降噪（Restoration / Denoising）

**[Guo2024MambaIR]** Guo et al., "MambaIR: A Simple Baseline for Image Restoration with State-Space Model", *ECCV 2024*, pp. 222–241. [[Paper](https://link.springer.com/chapter/10.1007/978-3-031-72649-1_13)] [[arXiv](https://arxiv.org/abs/2402.15648)]
> MambaIR；将状态空间模型（SSM / Mamba）引入图像复原，以线性计算复杂度实现接近全局感受野，在 SIDD Benchmark 去噪（**40.36 dB**，当前 SOTA）及超分任务上超越 NAFNet 和 Restormer。参见第三卷第02章、附录F §F.1.1。

**[Lin2024DiffBIR]** Lin et al., "DiffBIR: Toward Blind Image Restoration with Generative Diffusion Prior", *ECCV 2024*. [[Paper](https://link.springer.com/chapter/10.1007/978-3-031-73202-7_25)] [[arXiv](https://arxiv.org/abs/2308.15070)]
> DiffBIR；两阶段盲复原框架——先用回归网络抑制退化，再用 ControlNet 引导扩散模型生成细节；统一处理盲超分、盲去噪、盲去模糊等多种任务。参见第三卷第07章。

**[Jiang2024AutoDIR]** Jiang et al., "AutoDIR: Automatic All-in-One Image Restoration with Latent Diffusion", *ECCV 2024*, pp. 340–359. [[Paper](https://link.springer.com/chapter/10.1007/978-3-031-73661-2_19)]
> AutoDIR；基于开放词汇场景理解自动检测图像退化类型，无需人工指定退化种类，用潜在扩散完成多退化联合复原。参见第三卷第07章。

**[Chihaoui2024BIRD]** Chihaoui et al., "Blind Image Restoration via Fast Diffusion Inversion", *NeurIPS 2024*. [[Paper](https://proceedings.nips.cc/paper_files/paper/2024/hash/3d13d910b48ac2e672a32cfdf98be1bf-Abstract-Conference.html)] [[arXiv](https://arxiv.org/abs/2405.19572)]
> BIRD；同时优化退化算子参数和复原图像，利用大步长快速扩散反演压缩计算量，实现真正意义上的盲复原（无需预知退化类型或参数）。参见第三卷第07章。

**[Tu2024BIRD-D]** Tu et al., "Taming Generative Diffusion Prior for Universal Blind Image Restoration", *NeurIPS 2024*, pp. 21172–21206. [[Paper](https://proceedings.nips.cc/paper_files/paper/2024/hash/25869dbf7682272357bc2cbbf860e1c8-Abstract-Conference.html)] [[arXiv](https://arxiv.org/abs/2408.11287)]
> BIR-D；以可优化卷积核模拟多种退化算子，结合预训练 DDPM 生成先验实现通用盲复原，无需特定退化类型假设。参见第三卷第07章。

---

### 低光图像增强（Low-Light Image Enhancement）

**[Zhou2024GLARE]** Zhou et al., "GLARE: Low Light Image Enhancement via Generative Latent Feature based Codebook Retrieval", *ECCV 2024*. [[Paper](https://link.springer.com/chapter/10.1007/978-3-031-73195-2_3)] [[arXiv](https://arxiv.org/abs/2407.12431)]
> GLARE；从正常光照图像学习 VQ 码本先验，通过可逆潜变量归一化流（I-LNF）+ 自适应频率变换/调制（AFT/AMB）实现高质量低光增强，**非**视频扩散模型，本质是图像级码本检索方法。参见第三卷第05章、附录F §F.9。

**[Jiang2024LightenDiffusion]** Jiang et al., "LightenDiffusion: Unsupervised Low-Light Image Enhancement with Latent-Retinex Diffusion Models", *ECCV 2024*. [[Paper](https://link.springer.com/chapter/10.1007/978-3-031-73195-2_10)] [[arXiv](https://arxiv.org/abs/2407.08939)]
> LightenDiffusion；将 Retinex 物理分解（反射率 + 光照）嵌入潜在扩散框架实现无监督低光增强，无需低光-正常光配对数据，以一致性损失对齐跨域特征。参见第三卷第05章。

**[Chobola2024CoLIE]** Chobola et al., "Fast Context-Based Low-Light Image Enhancement via Neural Implicit Representations", *ECCV 2024*. [[Paper](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/11739.pdf)] [[arXiv](https://arxiv.org/abs/2407.12511)]
> CoLIE；使用神经隐式表示对逐图像亮度上下文建模，推理速度显著优于基于扩散的方法，适合高分辨率实时应用场景。参见第三卷第05章。

---

### 图像质量评估（Image Quality Assessment）

**[Chen2024PromptIQA]** Chen et al., "PromptIQA: Boosting the Performance and Generalization for No-Reference Image Quality Assessment via Prompts", *ECCV 2024*. [[Paper](https://link.springer.com/chapter/10.1007/978-3-031-73232-4_14)] [[arXiv](https://arxiv.org/abs/2403.04993)]
> PromptIQA；通过可学习提示（prompt）注入差异化评估需求，提升 NR-IQA 对新场景、新退化类型的泛化能力，在 KonIQ / SPAQ / LIVE 等多个基准上超越前代方法。参见第四卷第04章。

**[You2024DepictQA]** You et al., "Depicting Beyond Scores: Advancing Image Quality Assessment through Multi-modal Language Models", *ECCV 2024*, pp. 259–276. [[Paper](https://link.springer.com/chapter/10.1007/978-3-031-72970-6_15)] [[arXiv](https://arxiv.org/abs/2312.08962)]
> DepictQA；基于多模态大语言模型的描述式 IQA，突破传统单一分数局限，输出详细语言质量描述，支持比较式和单幅评估，为 LMM 驱动的 IQA 奠定基础。参见第四卷第04章、第五卷第03章。

**[Shin2024QCN]** Shin et al., "Blind Image Quality Assessment Based on Geometric Order Learning", *CVPR 2024*. [[Paper](https://openaccess.thecvf.com/content/CVPR2024/papers/Shin_Blind_Image_Quality_Assessment_Based_on_Geometric_Order_Learning_CVPR_2024_paper.pdf)]
> QCN（Quality Comparison Network）；利用质量比较变换器（CT）和分数枢轴在嵌入空间中按质量排序特征向量，以几何有序学习提升 BIQA 鲁棒性。参见第四卷第04章。

## 习题

**练习1（文献查阅）** 本附录中引用了 Restormer（CVPR 2022）和 NAFNet（ECCV 2022）。查阅各论文摘要，概括两者在模型结构上的核心区别：Restormer 的 Transformer 注意力机制是如何针对高分辨率图像优化的？NAFNet 如何在保持性能的同时大幅减少计算量？

**练习2（追踪最新进展）** 以"super resolution CVPR ECCV 2024"为关键词，搜索一篇 2024 年发表的超分辨率论文，对比其在 Set5 数据集 ×4 超分辨率任务上的 PSNR 与本附录中列出的 ESRGAN/Real-ESRGAN 的结果，说明技术进步幅度。
