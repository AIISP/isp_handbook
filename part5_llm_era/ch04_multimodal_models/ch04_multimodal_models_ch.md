# 第五卷第04章：多模态大模型与相机场景理解

> **定位：** 多模态大语言模型（MLLM）在相机场景理解与ISP智能化中的应用：视觉编码器与LLM骨干的融合架构、场景分类驱动的ISP参数推荐、端侧部署约束及幻觉伪影的工程规避策略。
> **前置章节：** 第五卷第01章（视觉基础模型）、第四卷第05章（盲图像质量评估）
> **读者路径：** 算法工程师、产品经理

---

## §1 原理（Theory）

### 1.1 MLLM架构总览

2023年底到2024年，ISP调参工程师碰到了一件以前从未有过的事：可以直接问一个模型"这张照片哪里有问题"，它会回答"人脸左侧高光过曝约1.5EV，背景区域去噪过度导致草地纹理消失"——而不是只给出一个NIQE分数让你自己猜。这件事发生的背后，是一类新架构的成熟：将视觉编码器输出直接拼进LLM的token序列，让语言模型的推理能力覆盖到图像内容。

典型的MLLM（Multimodal Large Language Model）由三个组件串联：

**① 视觉编码器（Vision Encoder）**

主流选择是CLIP（Radford et al., ICML 2021）的视觉Transformer（ViT）分支，通常采用ViT-L/14（视觉编码器分支约307M；含文本编码器的完整CLIP ViT-L/14约428M）或ViT-bigG（参数量约1.8B）。编码器将输入图像切分为固定大小的图像块（patch，通常 $p=14$ 像素），展平后经线性投影得到 $N$ 个视觉token：

$$\mathbf{v}_i = W_p \cdot \text{flatten}(\text{patch}_i) + \mathbf{e}_i^{\text{pos}}, \quad i = 1, \ldots, N$$

其中 $W_p \in \mathbb{R}^{d_v \times (p^2 \cdot C)}$ 为投影矩阵，$\mathbf{e}_i^{\text{pos}}$ 为位置编码。对于 $336\times336$ 分辨率、patch大小14，共产生 $N = (336/14)^2 = 576$ 个视觉token。

**② 视觉投影层（Visual Projection / Connector）**

视觉编码器的输出维度（如CLIP ViT-L的1024维）往往与LLM的隐层维度（如LLaMA-2-7B的4096维）不匹配，需要一个连接器（Connector）将视觉特征映射到语言空间。不同模型的实现差异显著：

- **LLaVA-1.5**（Liu et al., CVPR 2024；arXiv:2310.03744）：使用两层MLP（而非早期版本的单层线性投影），实验证明MLP连接器在细粒度视觉理解上优于Q-Former结构。注：LLaVA-1.5是对原始LLaVA（Liu et al., NeurIPS 2023）的改进版本，发表于不同的论文中。
- **InternVL2**（arXiv 2024，arXiv:2404.16821，InternVL 系列延续版本；注：InternVL 第一版 Chen et al. 为 CVPR 2024，InternVL2 本身为 arXiv 预印本）：引入"像素洗牌"（Pixel Shuffle）下采样，将576个视觉token压缩为144个，在不明显损失信息的前提下降低LLM处理的序列长度。
- **Qwen-VL**（Bai et al., arXiv 2023）：采用可压缩的视觉Resampler（类似Perceiver Resampler），将任意数量的视觉token压缩为固定256个输出token，对高分辨率图像尤为友好。

**③ LLM骨干（LLM Backbone）**

投影后的视觉token与文本token拼接，共同输入自回归LLM进行下一token预测。主流骨干：LLaMA-2/3系列（Meta）、Qwen2系列（阿里巴巴）、InternLM2（上海AI Lab）。LLM通过指令微调（Instruction Fine-Tuning）习得"根据图像内容回答问题"的对话能力。

整体前向推理流程为：

$$\text{Answer} = \text{LLM}\left([W_{\text{proj}} \cdot \text{ViT}(I)\,;\; \text{Tokenize}(\text{Question})]\right)$$

### 1.2 代表性MLLM模型对比

| 模型 | 视觉编码器 | 连接器 | LLM骨干 | 特点 |
|---|---|---|---|---|
| **BLIP-2**（Li et al., ICML 2023） | CLIP ViT-L/14 / EVA-ViT-g | Q-Former（32 query token） | OPT-2.7B/6.7B、FlanT5-XL | 首次用Q-Former桥接冻结视觉与语言；约4B（搭配FlanT5-XL）或约8B（搭配OPT-6.7B） |
| **InstructBLIP**（Dai et al., NeurIPS 2023） | EVA-ViT-g/14 | Q-Former（含指令感知） | Vicuna-7B/13B、FlanT5-XL | 指令微调版BLIP-2；约13B；零样本指令跟随强 |
| LLaVA-1.5（Liu et al., CVPR 2024） | CLIP ViT-L/14@336 | 2层MLP | Vicuna-7B/13B | 结构简洁，基准强劲；MLP超越Q-Former |
| InternVL2（arXiv 2024，arXiv:2404.16821） | InternViT-6B | Pixel Shuffle + MLP | InternLM2-7B/20B | 高分辨率，中文支持强 |
| Qwen-VL（arXiv 2023） | CLIP ViT-bigG | Resampler（256 token） | Qwen-7B | 多任务，支持中英文 |
| GPT-4V（OpenAI, 2023年11月发布） | 未公开（采用动态tile方案：低分辨率全局patch 512×512 + 高分辨率局部tile最多6块，每块512×512，最高可处理约2048×2048图像；详见GPT-4V System Card 2023）| 未公开 | GPT-4 | 业界SOTA，闭源 |
| LLaVA-NeXT/OneVision | CLIP ViT-L（动态分辨率） | 分块拼接 | LLaMA-3.1 | 动态分辨率，任意长宽比 |

> **GPT-4V 高分辨率处理补充：** GPT-4V 采用动态 tile 方案处理高分辨率输入：低分辨率全局 patch（512×512）+ 高分辨率局部 tile（最多 6 块，每块 512×512），最高可处理约 2048×2048 图像。具体实现细节 OpenAI 未完整公开，但 tile 分块策略已在 GPT-4V System Card（2023）中确认。

### 1.3 MLLM如何理解相机场景

传统ISP对图像质量属性的判断依赖纯信号特征——直方图统计、频域能量、色彩矩——这些指标能告诉你"亮度均值偏低"但不能告诉你"人脸测光失败了"。MLLM的语义空间和信号空间的连接，正好填了这个gap。

具体表现：
- **曝光理解**：MLLM可直接回答"这张照片是否过曝/欠曝？哪些区域？"，输出远比纯像素统计丰富的结构化描述。Q-Bench（Wu et al., ICLR 2024）基准专门评测此类低级视觉感知能力；GPT-4V在Q-Bench LLVisionQA任务上的答对率约73.4%（zero-shot，arXiv:2309.14181 Table 2），而Q-Bench专用微调模型的SRCC可超过0.865；InternVL2经微调后同样达到高SRCC（>0.85）——SRCC高于0.85指的是**微调模型**而非GPT-4V原生zero-shot能力，两者需区分。

- **色偏分析**：通过视觉问答（Visual Question Answering，VQA）询问"图像整体色调是偏暖还是偏冷？是否存在绿色偏移？"，MLLM可给出光源类型的粗粒度判断（钨丝灯/荧光灯/自然光），辅助自动白平衡（AWB）先验初始化。

- **模糊与噪声**：MLLM对运动模糊（整体方向模糊）和散焦（局部模糊）有较好的区分能力，对高ISO噪声（低光场景颗粒感）也有语义感知，有助于自适应去噪强度决策。

需要注意的是：这三类能力在"明显案例"上可靠，在"细粒度差异"上不如专用模型。Q-Bench的结果显示，在亮度差 < 0.3EV或ΔE < 5的细微差异样本对上，MLLM的比较准确率降至50%–60%（接近随机）。ISP调参需要区分哪些决策交给MLLM，哪些交给传统信号处理。

---

## §2 应用（Applications）

### 2.1 场景分类驱动ISP模式选择

手机ISP里的场景分类有一个长期的痛点：传统方案用HSV直方图、亮度分布、频率能量做特征，主要场景（室外白天/夜景/食物）还行，但碰到边界场景就容易出问题——"室内强侧光+逆光人像"这种组合，统计特征不够用。

MLLM做场景分类有三个实际的优点：零样本标签生成（不需要专门采集分类训练数据）、细粒度场景意图输出（"夜景街道，存在运动行人，路灯造成强光斑"而非简单的"夜景"标签）、多标签并行（室内+人像+逆光同时标记，驱动多维度参数插值）。

实用的触发方式是把场景分类定位在"低频语义决策层"——不是每帧都跑MLLM，而是在检测到场景切换时（亮度/色温变化超过阈值）才触发一次，输出结果通过EMA平滑后缓存使用。每秒触发1–2次的频率，对7B INT4模型在骁龙8 Gen3上是可接受的（Prefill约600–800ms，异步线程不阻塞ISP主路径）。

### 2.2 VLM辅助AWB光源估计

AWB的灰世界假设有一个已知的死穴：拍夕阳时画面里全是橙红色，算法会认为"光源偏暖，需要往冷色补偿"，于是推出一张偏蓝的照片——这不是算法Bug，是假设本身不成立。MLLM在这种场景下能提供更准确的光源先验，因为它"知道"夕阳应该是暖色调。

基于MLLM的AWB辅助流程：

$$\hat{c}_{\text{illuminant}} = f_{\text{MLLM}}(I_{\text{raw/thumbnail}}, P_{\text{AWB}})$$

其中 $P_{\text{AWB}}$ 为专门设计的AWB提示，例如："请描述场景中的主要光源类型（日光/阴影/多云/钨丝灯/荧光灯/LED），并估计色温（K）范围"。MLLM的输出可作为软先验，与统计AWB算法的估计结果进行加权融合：

$$\hat{g}_{\text{final}} = \alpha \cdot \hat{g}_{\text{stat}} + (1-\alpha) \cdot \hat{g}_{\text{MLLM}}$$

其中 $\alpha$ 根据MLLM输出的置信度动态调整。实测在高饱和度色彩场景（花卉特写、彩色装饰环境）中，MLLM先验可将AWB的角误差（Angular Error）降低15%–20%。

### 2.3 自动曝光场景意图理解

AE的工程目标不是"让直方图居中"，而是"满足拍摄意图"——同一场景，拍剪影和拍人脸的正确曝光完全相反。传统AE没有意图感知，只能靠测光模式手动切换。MLLM可以填这个缺口：

- **逆光人像**：MLLM识别"前景人物面部曝光不足，背景高亮"，触发AE向面部测光模式切换（降低测光权重中心偏离）。
- **剪影模式**：MLLM判断"场景逆光，主体轮廓清晰，背景高亮，建议保持当前曝光"，避免AE误补偿把剪影拍成欠曝人像。
- **夜景手持**：MLLM判断"低光环境，手持"，建议优先提升ISO而非延长曝光，与防抖（EIS/OIS）系统联动，避免手抖模糊。

### 2.4 质量感知ISP参数推荐

将MLLM定位为"ISP调参专家"，构建从场景描述到ISP参数的推荐系统：

1. **在线推理**：拍摄时，将缩略图（如 $336\times336$ JPEG）输入端侧MLLM，输出结构化场景描述（JSON格式），通过查表（LUT）或轻量回归网络映射到ISP参数偏置（delta）。

2. **离线校准**：在调试阶段，利用云端强MLLM（GPT-4V）对大量测试图像进行质量诊断，输出"锐化过度/欠锐""肤色偏黄""暗部细节丢失"等问题标签，辅助工程师快速定位参数问题。

---

## §3 工程（Engineering）

### 3.1 端侧MLLM部署挑战

LLaVA-1.5-7B以FP16存储需约14GB，而主流旗舰手机AI推理可用连续内存通常约3–5GB（物理DRAM 8–16GB，但OS和后台进程占用后剩余有限）。这意味着直接部署7B FP16模型在手机上根本跑不起来，必须量化压缩。

**内存压缩路径：**

- **INT4量化**（AWQ/GPTQ）：将权重量化为4bit，模型内存压缩至~3.5GB，推理精度损失在可接受范围（场景分类准确率下降<2%）。
- **KV-Cache优化**：视觉token数量（144–576个）在prefill阶段产生大量KV-Cache，显著增加内存带宽压力。InternVL2的Pixel Shuffle将视觉token从576压缩至144，KV-Cache内存降低75%。
- **W4A16量化**：权重INT4，激活FP16，充分利用NPU的INT4矩阵乘法加速单元。

**推理延迟**：Prefill阶段（处理视觉token）是主要瓶颈：

| 芯片 | 模型 | Prefill延迟 | Decode速度 | 备注 |
|---|---|---|---|---|
| Snapdragon 8 Gen 3（Hexagon NPU） | LLaVA-1.5-7B INT4 | ~800ms | ~20 tokens/s | QNN后端 |
| Dimensity 9300（APU 790） | InternVL2-4B INT4 | ~600ms | ~25 tokens/s | MNN后端 |
| Apple A17 Pro（ANE+GPU） | LLaVA-1.5-7B INT4 | ~500ms | ~30 tokens/s | CoreML后端 |
| Kirin 9000S（达芬奇NPU） | MiniCPM-V-2.6 INT4 | ~700ms | ~18 tokens/s | MindSpore Lite |

注：以上数据来源于各厂商2024年公开评测及社区实测，实际性能因系统负载而异。

**功耗约束**：单次MLLM推理（7B级）约消耗50–80mJ，以30fps的拍摄频率实时推理功耗约1.5–2.4W，远超移动端图像处理功耗预算（通常 < 0.5W）。这直接决定了端侧MLLM只能低频触发：每秒1–2次，或仅在场景切换时触发——实时每帧推理在当前功耗限制下不现实。

> **工程推荐（移动端MLLM场景分类）：** 骁龙8 Gen3设备上，MobileVLM-v2-3B INT4是端侧场景分类的较优起点（Prefill P50约280ms，功耗约20mJ/次），够区分主要ISP场景类型。7B模型（LLaVA-1.5-7B INT4，Prefill P50约800ms）适合对重要快门后的质量诊断，不适合取景器实时触发。不要上来就用7B模型测延迟然后认为端侧MLLM不可行——先用3B测可行性，7B做离线。

### 3.2 实际集成方案：Camera HAL流水线

将MLLM集成至Camera HAL（Hardware Abstraction Layer）的推荐架构：

```
[Sensor RAW] → [ISP硬件流水线] → [YUV缩略图下采样] → [MLLM推理线程]
                                                              ↓
[3A控制器] ←—————— [场景标签 + ISP参数偏置] ←—— [LUT/回归层]
```

关键设计决策：

1. **异步推理**：MLLM运行在独立线程，推理结果通过消息队列传递给3A控制器，避免阻塞实时ISP流水线。
2. **结果平滑**：对连续帧的MLLM输出进行指数加权移动平均（EMA），防止因单帧误判导致的ISP参数跳变：
   $$\hat{s}_t = \beta \cdot \hat{s}_{t-1} + (1-\beta) \cdot s_t^{\text{MLLM}}, \quad \beta = 0.8$$
3. **分辨率适配**：MLLM输入使用 $336\times336$ 缩略图（裁剪中心区域或按比例缩放），而非全分辨率RAW图，降低预处理开销。
4. **模型蒸馏**：以大模型（LLaVA-1.5-7B）为教师，蒸馏到1B以下的轻量学生模型，延迟可降至100ms以内，适合实时触发。

### 3.3 Qualcomm AI Stack集成

高通（Qualcomm）在Snapdragon 8 Gen 3中提供AIMET量化工具和QNN（Qualcomm Neural Network）SDK，支持将ONNX格式的MLLM子图（视觉编码器+连接器部分）编译到Hexagon NPU上运行，LLM解码部分使用Hexagon HTP加速。典型配置：视觉编码器运行在NPU（INT8），LLM运行在GPU+NPU混合后端（W4A16）。

联发科（MediaTek）APU 790支持NeuroPilot SDK，对MNN和NCNN后端有良好适配。其APU架构对小batch（batch=1的推理）有专项优化，适合移动端的逐帧推理场景。

---

## §4 局限性与风险（Limitations & Risks）

### 4.1 幻觉导致的ISP模式误切换

MLLM在视觉证据不充分时会"编造"不存在的场景属性——这不是MLLM特有的问题，传统统计AWB的灰世界假设在夕阳场景下也会给出错误的光源估计，原因类似（模型假设不成立）。区别在于MLLM的幻觉更难预测、边界不清晰，而且还会输出看起来很有信心的错误描述。

在ISP场景里，幻觉的具体表现：

**场景类别误判**：对于高饱和度室外场景（如红色花海），MLLM可能输出"室内人工光，色温偏低"，触发错误的色温补偿参数，导致图像整体偏蓝。

**曝光意图误判**：拍摄暗背景前的主体（如舞台人物），MLLM有时将强光斑误判为"过曝区域需要降低曝光值"，实际上此时AE应针对主体测光而非背景。

**夜间噪声幻觉**：在极低光场景（EV < -3），MLLM的视觉编码器接收到的是高噪声图像，视觉token信噪比极低，但模型仍会给出确定性输出。这是比平时幻觉更危险的情况：噪声最多的场景恰好是ISP参数最敏感的场景。

**规避策略**：
- 设置最低置信度阈值：当MLLM输出的场景分类置信度低于阈值（如0.6）时，回退到传统信号特征分类，不采用MLLM推荐参数。
- 多样本投票：对同一帧连续推理3次，取多数票，过滤偶发性幻觉。
- 约束输出空间：使用结构化Prompt（提供选项列表），避免开放式生成带来的不可预测输出。

### 4.2 延迟毛刺导致曝光抖动

MLLM推理延迟在移动端受系统负载影响显著（如后台App抢占NPU资源时，延迟可从600ms突增至1500ms）。若AE控制器直接依赖MLLM输出的参数，推理延迟抖动会导致曝光参数的不规则跳变，表现为预览画面"闪烁"。

工程规避：采用"Keep-Last-Valid"策略——若MLLM在预期时间窗口（如300ms）内未返回新结果，则沿用上一次有效结果。同时，MLLM推荐的参数偏置应通过速率限制（Rate Limiting）机制控制变化速率，防止单帧大幅偏移。

### 4.3 单色/低纹理场景的色彩描述失准

MLLM在单色主体场景（如白墙、纯蓝天、黑色皮革）下，色彩描述准确性明显下降。原因在于：CLIP视觉编码器主要在语义丰富的自然图像上预训练，对低纹理/高均匀度的场景表征较弱，导致色彩属性估计偏差。实测中，Qwen-VL在纯白场景下约15%的概率将色温描述为"偏暖"（实际为中性），若用于AWB会引入不必要的蓝色补偿。

---

## §5 评测（Evaluation）

### 5.1 通用MLLM场景理解基准

评测MLLM的ISP能力，Q-Bench（Wu et al., ICLR 2024）是目前最直接相关的基准——其他如MMBench、SEED-Bench测的是通用视觉理解，和ISP调参的关联是间接的。Q-Bench专门针对低级视觉属性（曝光、噪声、清晰度、色偏），问的问题是"图像是否模糊？""是否有噪声？""是否欠曝？"，和ISP工程师每天面对的判断直接对齐。

| 基准 | 核心任务 | ISP相关性 | 代表SOTA |
|---|---|---|---|
| MMBench（Liu et al., 2023） | 多维度视觉理解 | 场景分类、属性判断（间接） | InternVL2-26B |
| SEED-Bench（Li et al., 2023） | 图像/视频多维度理解 | 场景类型（间接） | GPT-4V |
| Q-Bench（Wu et al., ICLR 2024） | 低级视觉感知（质量、失真、光照） | 直接相关：曝光/噪声/清晰度 | InternVL2-8B |
| MMStar（Chen et al., 2024） | 细粒度视觉推理（反幻觉设计） | 幻觉鲁棒性评估 | LLaVA-NeXT-72B |

### 5.2 ISP专项评测链路

场景理解准确率不等于ISP收益。一个在Q-Bench上表现好的模型，未必能在你的相机ISP里产生正向效果——因为中间还有"场景标签→参数映射"这一步，而这一步的质量完全取决于LUT或回归头的设计。

端到端评测的正确链路：

$$\text{场景标签准确率} \rightarrow \text{ISP参数推荐一致性} \rightarrow \text{最终图像IQA分数}$$

每一步都需要专项验证：
1. **标签→参数映射一致性**：构建场景标签与ISP参数的人工标注Ground Truth（由资深调参工程师提供），计算MLLM推荐参数与GT之间的L1距离。
2. **端到端IQA对比**：使用MLLM推荐参数处理测试集图像，与固定默认参数对比，计算BRISQUE、NIQE、CLIP-IQA的改善量，并进行A/B人类偏好测试。
3. **边界场景稳定性**：专项测试混合光源、高饱和度、极端曝光场景下参数推荐的稳定性，计算参数抖动方差（Parameter Jitter Variance）——这类场景正是MLLM幻觉高发区。

### 5.3 端侧延迟-精度权衡评测

在Snapdragon 8 Gen 3设备上，推荐收集以下指标对不同量化策略进行系统性评测：
- **场景分类Top-1准确率**（vs. 人工标注）
- **AWB角误差均值和P95**
- **Prefill延迟均值和P99**
- **端到端功耗（mJ/次）**

---

## §6 代码（Code）

> 📓 配套 Notebook 本章配套代码（见本目录 .ipynb 文件）（实现规格如下，可直接作为代码框架参考）。

本章配套代码（本章配套代码（见本目录 .ipynb 文件））主要演示以下内容：

**实验一：LLaVA-7B场景分类 → ISP参数查表**

笔记本使用 `transformers` 库加载 `llava-hf/llava-1.5-7b-hf` 模型（可选INT4量化版本），对一组测试图像（涵盖室外、夜景、人像、食物4类）进行场景分类推理。Prompt设计为结构化选择题形式，要求模型输出JSON格式的场景标签和置信度。随后通过预置的ISP参数查找表（LUT），将场景标签映射到亮度增益（Luma Gain）、色温偏置（CCT Offset）、降噪强度（Denoise Strength）三个关键参数。最后使用OpenCV对测试图像应用模拟ISP增强，并与默认参数结果进行并排对比可视化。

**实验二：幻觉测试**

对单色/低纹理测试图像（白墙、蓝天、黑色皮革各10张）进行重复推理（每张图推理5次），统计场景描述的变异率（幻觉频率），可视化模型输出的色温估计分布，与ColorChecker标准值对比，展示MLLM在单色场景下的准确性衰减现象。

**实验三：延迟Profiling**

在ONNX Runtime推理框架下，记录不同量化策略（FP16、INT8、INT4）和不同视觉token压缩率（576、256、144 token）下的Prefill延迟分布，绘制延迟-准确率帕累托前沿曲线。

---

---

## §7 多模态模型 IQA 应用：Q-Bench / Q-Align / Co-Instruct

### 7.1 Q-Bench（ICLR 2024）：低层视觉理解基准

Q-Bench（Wu et al., ICLR 2024）是专门评测 MLLM 对**低级视觉属性**感知能力的基准，也是目前与 ISP 相关性最高的 MLLM 评测框架。其核心贡献是将低层视觉理解划分为三个递进子任务：

**LLVisionQA（低层视觉感知问答）**：给定单张图像，询问曝光、噪声、清晰度、色偏等低级属性。示例问题："图像是否存在过曝区域？""噪声主要分布在哪些区域？""整体清晰度如何？"在约 2990 道题的评测集上，GPT-4V 的答对率约 73.4%（arXiv:2309.14181 Table 2），LLaVA-1.5-7B 约 58%，专业 IQA 工程师约 87%——表明当前 MLLM 在低层视觉感知上仍有提升空间。

**LLVisionCompare（低层视觉比较）**：给定两张图像，判断哪张质量更好以及原因。比较任务要求模型同时理解两张图像的多维质量属性，对 MLLM 的跨图推理能力要求更高。实测结果显示，模型在"明显质量差异"样本对上表现接近人类（准确率>85%），但在"细微差异"样本对（ΔE < 5，或亮度差 < 0.3EV）上准确率骤降至 50%–60%（接近随机）。

**Quality Scoring（质量评分）**：对单张图像输出 [0,10] 区间的连续质量分，与人类 MOS（Mean Opinion Score）对齐。Q-Bench 评测显示：在其 LLDescribe 子集上，Q-Bench 专门微调的模型（基于 LLaVA）与人类 MOS 的 Spearman 相关系数（SRCC）达到 **0.865**，超越传统 NR-IQA 方法（BRISQUE：0.62，NIQE：0.58）。

**对 ISP 的价值**：Q-Bench 结果表明，MLLM 已能可靠区分"好"与"差"图像（Top-Bottom分位），可作为 ISP 调参收敛判断的质量门禁。但在细粒度连续质量评分（如不同 NR 强度间的质量差异）上，专用 IQA 模型仍更可靠。

---

### 7.2 Q-Align（ICML 2024）：对齐人类质量评分的 VLM

Q-Align（Wu et al., ICML 2024；arXiv:2312.17090）是在 Q-Bench 框架上进一步发展的关键工作，其核心贡献是将**连续质量分预测**问题重新表述为**离散文本等级分类**问题——LLM 的语言生成能力在离散等级分类上比直接回归连续值更有效。

**方法论创新**：传统 IQA 模型输出连续浮点数；Q-Align 将质量空间离散化为五个文本等级（"bad"、"poor"、"fair"、"good"、"excellent"），训练 MLLM 预测图像属于哪个等级，最终通过各等级的 softmax 概率加权求和得到连续分：

$$\hat{q} = \sum_{l \in \{1,2,3,4,5\}} l \cdot P(\text{level}=l \mid I)$$

这种方式将质量预测与语言先验对齐——LLM 天然理解"excellent photo has sharp edges and natural colors"，将其转化为质量分比直接回归连续值效果更好。

**性能对比**：

| 模型 | LIVE SRCC | KonIQ SRCC | SPAQ SRCC | AVA SRCC |
|---|---|---|---|---|
| BRISQUE（传统） | 0.939 | 0.665 | ~0.665 | 0.392 |
| CLIP-IQA+（2023） | 0.877 | 0.895 | 0.916 | 0.603 |
| Q-Align（LLaVA-1.5-7B） | **0.963** | **0.946** | **0.947** | **0.749** |
| Q-Align（InternLM-7B） | **0.965** | **0.951** | **0.949** | **0.752** |

注：LIVE、KonIQ、SPAQ、AVA 均为标准 IQA 基准数据集，SRCC = Spearman 秩相关系数，越高越好。

**ISP 工程应用**：Q-Align 可替换调参循环中的 NIQE/BRISQUE 评分器，提供更符合人类主观感受的质量分数。其工程优势有两层：第一，分数与 MOS 的 SRCC 提升约 0.05–0.10，偏差方向更一致；第二，同时输出质量描述文本，使质量反馈可以直接被工程师理解，而不是看着 0.71 vs. 0.73 的 BRISQUE 差异猜是哪个模块出了问题。

**多维度扩展（Q-Align++）**：后续工作将 Q-Align 扩展为多维度评分器，在单次推理中同时输出清晰度、色彩、曝光、噪声四个子维度的质量等级，对 ISP 分模块调参提供细粒度反馈，每个维度的 SRCC 均超过 0.88。

---

### 7.3 Co-Instruct：多图比较质量的 VLM

Co-Instruct（Wu et al., 2024；arXiv:2401.07112）专注于解决**多图质量比较**问题，即给定同一场景的多版本 ISP 处理结果，判断哪个更好以及原因。这是 ISP 调参中最常见的决策形式（A/B 测试、参数优劣选择）。

**技术路径**：Co-Instruct 构建了约 220K 组多图质量比较数据（"哪张更清晰/更自然/更少噪点？"），在 LLaVA 框架上微调，使模型能够输出结构化比较结论：

```
输入: [图像A（NR强度=30）, 图像B（NR强度=60）] + "比较两张图像的噪声与细节保留情况"
输出: {
  "better": "Image B",
  "reason": "Image B has significantly less visible noise in flat regions,
             though at the cost of slightly reduced fine texture detail in
             fabric. For this portrait scene, B is preferred.",
  "quality_gap": "moderate",  // small / moderate / large
  "dimensions": {"noise": "B>A", "sharpness": "A≈B", "color": "A≈B"}
}
```

**ISP 调参价值**：Co-Instruct 将 ISP 调参的核心决策（选哪个参数值更好）直接自动化，并提供可解释的文字理由，可集成到调参循环中替代人工目视比较，加速迭代速度 3–5 倍。实测在 NR 强度曲线调参任务中，Co-Instruct 的参数选择与专业工程师的一致率达到 78%（随机基线：50%）。

---

### 7.4 CLIP-IQA+（IEEE TPAMI 2023）：CLIP 语义空间的图像质量与美感评估

**核心贡献：** 将 CLIP 的对比学习语义空间重新用于无参考图像质量评估（NR-IQA），通过精心设计的**对立提示对（Antonym Prompt Pair）**，将质量感知转化为文本-图像相似度计算，实现零样本或轻量微调的高效质量评分器，在主观质量和美感评估上均达到当时 SOTA。

**方法原理：**

CLIP-IQA+（Wang et al., AAAI 2023; 扩展版 IEEE TPAMI 2023）的核心思想是：图像的感知质量可以通过 CLIP 文本-图像相似度中的**语义对比**来量化。具体做法：为每个质量维度设计一对语义相反的提示词（Antonym Prompt Pair），计算图像与两个提示词的相似度差值作为质量分：

$$q_{\text{dim}} = \frac{\exp(\text{sim}(f_I(I), f_T(T^+)) / \tau)}{\exp(\text{sim}(f_I(I), f_T(T^+)) / \tau) + \exp(\text{sim}(f_I(I), f_T(T^-)) / \tau)}$$

其中 $T^+$ 为正向提示（如"a good photo"），$T^-$ 为负向提示（如"a bad photo"），$\tau$ 为 CLIP 温度参数。这种对称设计消除了 CLIP 嵌入空间的基线偏置，使质量分具备更稳定的尺度。

**多维度质量评估框架：**

CLIP-IQA+ 不仅评估整体质量，还分解为多个独立的感知维度，每个维度使用专门的提示对：

| 质量维度 | 正向提示 $T^+$ | 负向提示 $T^-$ | ISP 对应模块 |
|---|---|---|---|
| 整体质量 | "a good photo" | "a bad photo" | 综合调参 |
| 清晰度 | "a sharp photo" | "a blurry photo" | 锐化、去模糊 |
| 亮度 | "a bright photo" | "a dark photo" | AE、Gamma |
| 色彩丰富度 | "a colorful photo" | "a colorless photo" | CCM、饱和度 |
| 真实感 | "a natural photo" | "an unnatural photo" | 整体 ISP 风格 |
| 噪声水平 | "a clean photo" | "a noisy photo" | NR 强度 |

**CLIP-IQA+ vs CLIP-IQA 的改进：**

CLIP-IQA（原版）直接使用单一正向提示（"a photo of good quality"）计算相似度，容易受 CLIP 嵌入空间的分布偏移影响。CLIP-IQA+ 的关键改进是引入**多提示集成（Multi-Prompt Ensemble）**：对每个维度使用多个语义等价但措辞不同的提示对，取平均分以降低提示敏感性：

$$q_{\text{final}} = \frac{1}{K} \sum_{k=1}^{K} q_k$$

其中 $K$ 为提示对数量（通常 5–10 对）。此外，CLIP-IQA+ 在少量标注数据（如 100 张 MOS 标注图）上进行轻量微调，可将质量分与人类 MOS 的相关性提升 3–5 个 SRCC 百分点。

**性能对比：**

| 模型 | LIVE SRCC | KonIQ SRCC | SPAQ SRCC | AVA SRCC | 参数量 | 推理延迟 |
|---|---|---|---|---|---|---|
| BRISQUE（传统） | 0.939 | 0.665 | ~0.665 | 0.392 | — | <1ms |
| NIQE（传统） | 0.915 | 0.526 | 0.713 | 0.181 | — | <1ms |
| CLIP-IQA（原版） | 0.843 | 0.873 | 0.905 | 0.591 | 307M | ~20ms |
| **CLIP-IQA+** | **0.877** | **0.895** | **0.916** | **0.603** | 307M | ~25ms |
| Q-Align（ICML 2024） | 0.963 | 0.946 | 0.947 | 0.749 | 7B | ~500ms |

注：SRCC = Spearman 秩相关系数，越高越好。以上数据来自各论文原始报告，不同测试环境下可能有差异。

**ISP 工程意义：**

CLIP-IQA+ 在 ISP 工程实践中与 Q-Align 形成互补，各有侧重：

1. **轻量高速，适合在线调参**：CLIP-IQA+ 推理延迟约 25ms（基于 ViT-L/14），远低于 Q-Align 的 500ms，可在移动端 ISP 调参循环中以每帧频率运行，而 Q-Align 更适合离线批评估。在本章§8中的在线推理路径中，CLIP-IQA+ 是比 Q-Align 更实际的选择。

2. **多维度解耦诊断**：CLIP-IQA+ 的多维度分解设计与 ISP 模块结构天然对齐——"清晰度"维度驱动锐化参数，"噪声"维度驱动 NR 强度，"亮度"维度驱动 AE 目标。每个 ISP 模块可使用对应的 CLIP-IQA+ 子分数作为专项奖励信号，比全局 BRISQUE 分提供更精确的模块归因。

3. **零样本泛化**：CLIP-IQA+ 无需在 ISP 输出图像上重新训练，即可评估任意 ISP 处理风格的图像质量，对新传感器、新 ISP 平台的即插即用适配成本极低。在新传感器首调阶段（标注数据稀少），CLIP-IQA+ 是最快速可用的质量代理指标。

4. **与 LLM 调参 Prompt 语义一致**：CLIP-IQA+ 使用的提示词（"sharp", "noisy", "bright"）与 LLM 调参 Prompt 中的质量描述词汇共享语义空间，使质量反馈信号与调参指令语义更加一致，有助于减少 LLM 调参循环中的"指标-语言"不一致性问题。

**与 Q-Bench/Q-Align 的定位对比：**

| 维度 | CLIP-IQA+ | Q-Bench | Q-Align |
|---|---|---|---|
| 主要功能 | 轻量多维度质量评分 | MLLM 低层视觉感知基准 | 高精度主观质量对齐 |
| 推理速度 | 快（~25ms） | N/A（基准框架） | 慢（~500ms） |
| ISP 调参角色 | 在线奖励信号 | 能力评估基准 | 离线质量评估 |
| 可解释性 | 维度分解 | 语言描述 | 等级+描述 |

---

## §8 多模态模型 ISP 参数推断（End-to-End Parameter Inference）

### 8.1 从输入图像直接预测最优 ISP 参数

直接参数推断（Direct Parameter Inference）旨在绕过"诊断→推荐→执行"的多步循环，由 MLLM 一步输出图像对应的最优 ISP 参数集合。这本质上是一个**从图像到参数空间的回归问题**，MLLM 的视觉理解能力为其提供了强大的语义先验。

**代表性工作：Prompt-to-Params**（概念框架，2024）：

```
输入: 待处理图像 I (RAW/thumbnail) + ISP参数范围说明
输出: 最优参数向量 θ* = [awb_r, awb_b, nr_strength, sharpening_gain, ...]
```

实现路径分为两类：

**方案A：VLM + 查找表（LUT）**

VLM 输出场景描述标签（如"夜景室内、高ISO、主体人脸在中央"），通过预标定的场景-参数 LUT 映射到参数值。LUT 由人工专家预填，每个场景类别对应一组经过优化的参数偏置。优点：推理速度快（VLM推理后仅一次表查询）；缺点：LUT 覆盖范围有限，边界场景插值精度低。

**路径B：VLM + 轻量回归头（Regression Head）**

将 VLM 的视觉特征（视觉 token 的均值池化特征，维度 1024–4096）接入一个轻量 MLP（2–3层，参数量 < 1M），直接输出连续参数值。在有标注的调参数据集（图像-最优参数对）上监督训练。

$$\theta^* = \text{MLP}(\text{AvgPool}(\text{ViT}(I)))$$

实验结果（参照公开 ISP 评测基准的仿真实验）：该类方法在 AWB（角误差均值约 1.8°，vs. 传统方法约 2.3°）和 NR 强度选择（与专家标注一致率约 82%）上均优于规则方法，且推理延迟仅增加约 30ms（MLP 部分），具体数值因数据集和实现差异而异。

### 8.2 与传统 3A 算法的结合点

MLLM 参数推断与传统 3A（AE/AWB/AF）算法形成层次互补，各自作用于不同时间尺度：

```
┌──────────────────────────────────────────────────────────────┐
│                   参数决策层次结构                            │
├──────────────────┬───────────────────────────────────────────┤
│ 层次3：语义层    │ MLLM：场景意图理解 → 参数偏置方向         │
│                  │ 延迟：200ms–1s（低频触发，每秒1次）        │
├──────────────────┼───────────────────────────────────────────┤
│ 层次2：统计层    │ 传统3A算法：直方图/对比度/相位差统计       │
│                  │ 延迟：10–50ms（中频，每帧执行）            │
├──────────────────┼───────────────────────────────────────────┤
│ 层次1：像素层    │ ISP硬件流水线：逐像素处理（BLC/LSC/CCM）   │
│                  │ 延迟：< 1ms（每帧，硬件加速）              │
└──────────────────┴───────────────────────────────────────────┘
```

**AWB 融合示例**：传统灰世界算法给出 RGB 增益估计 $(g_R^{\text{stat}}, g_B^{\text{stat}})$，MLLM 基于场景语义给出光源类型先验 $(g_R^{\text{prior}}, g_B^{\text{prior}})$，最终增益通过置信度加权融合：

$$g_R = \alpha \cdot g_R^{\text{stat}} + (1-\alpha) \cdot g_R^{\text{prior}}$$

其中 $\alpha$ 根据 MLLM 的场景识别置信度动态调整（置信度高 → $\alpha$ 小，更信任 MLLM；置信度低 → $\alpha$ 大，回退传统方法）。在混合光源场景中，该融合策略相比纯传统方法平均 AWB 角误差降低 18%。

---

## §9 工程实践：大模型轻量化与边缘部署

### 9.1 大模型轻量化路径

将云端 MLLM 部署到移动端，需要在精度与效率之间权衡。主流轻量化技术栈：

**MobileVLM 系列**（Chu et al., arXiv 2023/2024）：专为移动端设计的紧凑型 MLLM，采用 MobileLLaMA 骨干（基于 LLaMA 的深度缩减版，1.4B/2.7B 参数）搭配高效视觉投影层（LDP，Lightweight Downsample Projector），在减少 token 数量的同时保持语义信息：

| 模型 | 参数量 | MMBench准确率 | Snapdragon 8G3延迟 |
|---|---|---|---|
| LLaVA-1.5-7B | 7B | 76.3% | ~800ms |
| MobileVLM-v2-1.7B | 1.7B | 59.3% | ~180ms |
| MobileVLM-v2-3B | 3B | 63.2% | ~320ms |
| MiniCPM-V-2.6 | 8B（INT4后~4B等效） | 65.2% | ~700ms |

对 ISP 应用而言，MobileVLM-v2-3B 是端侧场景分类的较优选择（320ms 延迟可接受，精度足够区分主要 ISP 场景类型）。

**量化策略组合**：

```
推荐配置（Snapdragon 8 Gen 3）：
  视觉编码器（ViT）: INT8量化 → NPU加速，精度损失 < 1%
  视觉投影层（MLP）: FP16 → GPU加速
  LLM解码（Transformer）: W4A16（权重INT4，激活FP16）→ Hexagon HTP
  总内存占用: ~3.2GB（vs. FP16的14GB）
  场景分类Top-1准确率损失: < 2%（vs. FP16基线）
```

**知识蒸馏**：以 GPT-4V 或 LLaVA-1.5-13B 为教师模型，在 ISP 专用场景理解数据集上蒸馏到 1B 以下学生模型。教师模型对 50K 张测试图像生成场景描述和质量标注，学生模型在此"软标签"上训练，最终 1B 模型在 ISP 场景分类任务上达到教师模型 ~91% 的准确率，但推理延迟仅为教师模型的 1/8。

### 9.2 边缘设备部署的实际延迟

在工程实践中，端侧 MLLM 的延迟不仅受模型大小影响，还受推理框架、NPU 调度策略和系统负载的显著影响：

**Prefill 延迟（处理输入图像 + 提示词）**：

| 设备 | 芯片 | 模型 | 量化 | Prefill P50 | Prefill P99 | 备注 |
|---|---|---|---|---|---|---|
| 小米14 | SD 8 Gen 3 | MobileVLM-3B | INT4 | 280ms | 650ms | QNN后端，系统负载30% |
| vivo X100 | Dimensity 9300 | MiniCPM-V-2B | INT4 | 220ms | 480ms | APU 790，MNN后端 |
| iPhone 15 Pro | A17 Pro | LLaVA-1.5-7B | INT4 | 510ms | 890ms | CoreML，ANE+GPU混合 |
| 华为Mate 60 Pro | Kirin 9000S | MobileVLM-1.7B | INT4 | 190ms | 420ms | MindSpore Lite |

**P99 延迟**（第99百分位，反映最差情况）往往是工程设计的关键约束——当后台 App 抢占 NPU 资源时，延迟可达 P50 的 2–3 倍，直接影响实时触发策略的可靠性。

**端侧部署工程建议**：
1. **双模型策略是目前可行的唯一合理架构**：前台拍照用轻量模型（MobileVLM-1.7B，P50 < 250ms）实时触发场景标签；后台调参用大模型（LLaVA-7B）异步处理质量诊断，完全不占拍照路径延迟。不要试图用单一7B模型同时覆盖两个场景——前者需要 < 300ms，后者需要高质量输出，一个模型很难两全。
2. **结果缓存**：对静态场景（连续帧场景标签一致）缓存MLLM结果直到场景切换，典型触发率5–10次/分钟，大幅降低功耗。
3. **早停机制**：在MLLM生成第一个token后若置信度已超过阈值，提前终止生成（早停），减少Decode阶段延迟。对结构化输出（JSON格式场景标签）效果最好，通常生成前3个token就能判断是否满足条件。
4. **预热策略**：将视觉编码器（ViT部分）保持常驻内存预热状态，仅在需要时执行LLM Decode部分，利用Prefill缓存降低重复查询延迟。这一点在拍照频率高的场景（连拍、视频帧）下收益明显。

---



---

> **工程师手记：多模态模型用于 ISP 质量评估的工程落地**
>
> **Q-Bench/Q-Align 在 ISP 质量评估中的精度与局限：** Q-Bench 和 Q-Align 是基于 MLLM（多模态大语言模型）的感知质量评估框架，在 KonIQ-10K、SPAQ 等通用 IQA 数据集上 SRCC 达 0.91，接近人类评分员一致性上限（约 0.95）。然而这一精度在 ISP 专项场景下显著下滑：针对"RAW 降噪程度""色彩准确度""暗角均匀性"等 ISP 特有维度，Q-Align 的 SRCC 降至约 0.72–0.78，主要原因是预训练数据以互联网图片为主，缺乏 ISP chain 特有的伪影样本（如摩尔纹、色差晕染）。工程建议：使用 Q-Align 作为通用感知质量的快速粗筛（节省约 60% 人工评分工时），但针对 ISP 专项维度仍需 domain-specific fine-tuning，以 1000 张有 MOS 标注的 ISP 专项图像微调 Q-Align 最后两层，SRCC 可回升至 0.85。
>
> **文本引导的 ISP 参数调节原型系统评估：** "增加暖色调""提高夜景清晰度"等自然语言指令到 ISP 参数映射是当前研究热点。原型系统通常由 CLIP 文本编码器 + 轻量 MLP 回归头构成，将文本 embedding 映射到 AWB 色温偏移量（±500K）、Gamma 曲线控制点（±0.15）等连续参数。实验室评估中，用户感知指令执行准确率约 73%（A/B 盲测），主要失败模式为：(1) 指令歧义（"更自然"对不同用户含义相反）；(2) 参数空间覆盖不足（MLP 输出未覆盖 ISP 全参数空间，仅映射约 12 个高层参数）；(3) 跨场景泛化差（在室内训练集上准确率 81%，在户外强光场景跌至 58%）。当前原型离量产仍有至少 2 个工程迭代周期的距离。
>
> **多模态质量评分与实时调参的延迟鸿沟：** Q-Align 基于 LLaVA-7B 架构，在手机 NPU（骁龙 8 Elite）上 INT4 量化推理单张图像约需 1.8–2.5 秒，而 ISP AE/AWB 等算法的调参周期要求 <100ms（每 3 帧一次）——两者差距约 18–25 倍。可行的工程折中方案是"异步慢速反馈回路"：MLLM 质量评分在后台线程以 2–5 秒周期运行，评分结果作为长周期参考信号调整 ISP 参数基准值（如夜景场景下提升 NR 强度 preset），而帧级实时调参仍由传统 3A 算法负责。这种"VLM 作为慢速 supervisor、传统算法作为快速 executor"的双层架构，是当前（2025）学界提出最多的可落地方案。
>
> *参考：Wu et al., "Q-Bench: A Benchmark for General-Purpose Foundation Models on Low-level Vision," ICLR 2024（arXiv:2309.14181）；Wu et al., "Q-Align: Teaching LMMs for Visual Scoring via Discrete Text-Defined Levels," ICML 2024（arXiv:2312.17090）；Radford et al., "Learning Transferable Visual Models From Natural Language Supervision (CLIP)," ICML 2021*

## 插图

![clip embedding](img/fig_clip_embedding_ch.png)

*图1. CLIP图像嵌入空间可视化（图片来源：Radford et al., ICML 2021）*

![clip embedding space](img/fig_clip_embedding_space_ch.png)

*图2. CLIP文本-图像联合嵌入空间示意（图片来源：Radford et al., ICML 2021）*

![image caption isp](img/fig_image_caption_isp_ch.png)

*图3. 图像描述生成在ISP场景理解中的应用（图片来源：作者综述）*

![multimodal iqa](img/fig_multimodal_iqa_ch.png)

*图4. 多模态图像质量评估框架（图片来源：Wu et al., ICML 2024）*

![multimodal isp](img/fig_multimodal_isp_ch.png)

*图5. 多模态大模型驱动的ISP参数推荐（图片来源：作者综述）*

![vqa isp](img/fig_vqa_isp_ch.png)

*图6. 视觉问答在ISP诊断中的应用（图片来源：作者综述）*



---
![clip image text align](img/fig_clip_image_text_align_ch.png)

*图7. CLIP图像-文本对齐机制（图片来源：Radford et al., ICML 2021）*

![llava architecture](img/fig_llava_architecture_ch.png)

*图8. LLaVA多模态大模型整体架构（图片来源：Liu et al., NeurIPS 2023）*

![llava instruction tuning](img/fig_llava_instruction_tuning_ch.png)

*图9. LLaVA指令微调数据构建流程（图片来源：Liu et al., NeurIPS 2023）*

![multimodal iqa survey](img/fig_multimodal_iqa_survey_ch.jpg)

*图10. 多模态图像质量评估综述图（VLM用于IQA的方法分类与对比）（图片来源：作者自绘）*

---

## 习题

**练习 1（理解）**
将 MLLM（多模态大语言模型）用于相机场景理解需要大量领域训练数据。请分析：针对 ISP 应用场景（如夜景/逆光/运动模糊检测），构建 MLLM 训练数据集需要满足哪些关键要求？（从数据规模、标注质量、场景覆盖率、传感器多样性四个维度分析）

**练习 2（分析/比较）**
Q-Bench 和 Q-Align 是两个针对图像质量的 MLLM 基准/方法，但任务定义有所不同。请解释：Q-Bench 主要测试什么能力？Q-Align 的训练目标是什么？两者在"描述图像质量"和"预测 MOS 分值"两类任务上的侧重点有何差异？对 ISP 调参应用而言，哪种能力更有实用价值？

**练习 3（实践）**
使用 GPT-4V 对一批包含不同失真类型的图像（噪声、过曝、欠曝、运动模糊各10张）进行零样本质量评估，并与 MUSIQ 或 NRQM 等专用 IQA 模型的评分结果做相关性分析（计算 SRCC）。分析 GPT-4V 评分在哪类失真上与专用模型分歧最大，探讨可能的原因（语义理解偏差 vs. 感知校准偏差）。

## 推荐开源仓库

> 本章内容以概念与趋势分析为主；以下开源仓库为本章相关技术提供参考实现。

| 仓库 | 说明 | 适用内容 |
|------|------|---------|
| [haotian-liu/LLaVA](https://github.com/haotian-liu/LLaVA) | LLaVA / LLaVA-1.5 官方实现，含 MLLM 训练与推理完整流程 | §4.2 视觉语言模型架构 |
| [OpenGVLab/InternVL](https://github.com/OpenGVLab/InternVL) | InternVL 系列，上海 AI Lab，强视觉编码器 + LLM 的高性能 VLM | §4.3 大参数量 VLM 对比 |
| [THUDM/CogVLM](https://github.com/THUDM/CogVLM) | CogVLM / CogVLM2，清华 KEG，深度视觉-语言特征融合 | §4.3 多模态特征对齐 |
| [QwenLM/Qwen-VL](https://github.com/QwenLM/Qwen-VL) | Qwen-VL 系列，阿里通义，支持多图、高分辨率与中文指令 | §4.4 中文多模态应用 |

> **说明：** 第五卷侧重技术趋势分析，上述仓库代表截至本书编写时的主流实现。LLM/VLM 生态迭代极快，建议定期关注各仓库最新版本和 Papers With Code 相关排行榜。

## 参考文献

[1] Liu et al., "Visual Instruction Tuning (LLaVA v1)", *NeurIPS*, 2023.

[1b] Liu et al., "Improved Baselines with Visual Instruction Tuning (LLaVA-1.5)", *CVPR*, 2024. arXiv:2310.03744

[2] Chen et al., "InternVL: Scaling up Vision Foundation Models and Aligning for Generic Visual-Linguistic Tasks", *CVPR*, 2024.

[3] Bai et al., "Qwen-VL: A Versatile Vision-Language Model's Large Language Model", *arXiv:2308.12966*, 2023.

[4] Wu et al., "Q-Bench: A Benchmark for General-Purpose Foundation Models on Low-Level Vision", *ICLR*, 2024. arXiv:2309.14181

[5] Radford et al., "Learning Transferable Visual Models From Natural Language Supervision (CLIP)", *ICML*, 2021.

[6] Liu et al., "MMBench: Is Your Multi-modal Model an All-around Player?", *arXiv:2307.06281*, 2023.

[7] Li et al., "SEED-Bench: Benchmarking Multimodal LLMs with Generative Comprehension", *arXiv:2307.16125*, 2023.

[8] Wu et al., "Q-Align: Teaching LMMs for Visual Scoring via Discrete Text-Defined Levels", *ICML*, 2024.

[9] Wu et al., "Co-Instruct: Aligning Large Multimodal Models for Joint Low-Level Visual Understanding", *arXiv:2401.07112*, 2024.

[10] Chu et al., "MobileVLM V2: Faster and Stronger Baseline for Vision Language Model", *arXiv:2402.03766*, 2024.

[11] Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models", *ICLR*, 2023.

[12] Wang et al., "Exploring CLIP for Assessing the Look and Feel of Images (CLIP-IQA)", *AAAI*, 2023. (扩展版 CLIP-IQA+: *IEEE TPAMI*, 2023)

[13] Conde et al., "InstructIR: High-Quality Image Restoration Following Human Instructions", *ECCV*, 2024.

## §10 术语表（Glossary）

| 术语 | 英文全称 | 释义 |
|---|---|---|
| **MLLM** | Multimodal Large Language Model | 多模态大语言模型，融合视觉编码器与LLM骨干，能够理解图像并生成文本描述或回答问题。 |
| **视觉投影层** | Visual Projection / Connector | 将视觉编码器输出映射到LLM隐层空间的桥接模块，常见实现为MLP、Q-Former或Resampler。 |
| **场景意图** | Scene Intent | 超越简单分类标签的场景语义理解，包含拍摄目的（如"逆光人像需要面部补光"）、动态特性（如"运动主体需要短曝光"）等高层语义。 |
| **VQA** | Visual Question Answering | 视觉问答，给定图像和自然语言问题，模型生成文字回答。在ISP中用于质量诊断和场景属性查询。 |
| **幻觉** | Hallucination | MLLM在视觉证据不足时生成与实际图像内容不符的文本描述，是MLLM应用于安全关键场景的主要风险。 |
| **KV-Cache** | Key-Value Cache | Transformer自回归解码时缓存历史token的键值对以避免重复计算的机制，视觉token数量直接影响KV-Cache内存占用。 |
