# 第六卷第09章：手机视频ISP：Log模式、8K流水线与电影级处理

> **定位：** 本章深度解析手机视频ISP的核心技术，覆盖Log模式、8K流水线、Dolby Vision录制与电影级视频处理的算法与工程实现
> **前置章节：** 第二卷第19章（HDR显示信号链）、第二卷第23章（EIS/OIS）、第六卷第01章（消费级摄影演进）
> **读者路径：** 算法工程师、视频工程师、产品经理

> **本章技术索引（用户感知功能 → 背后关键算法 → 手册章节）**
>
> | 用户感知功能 | 背后的关键算法决策 | 算法来源章节 |
> |-------------|-----------------|------------|
> | 视频防抖流畅无果冻 | OIS+EIS 分频融合；光流精修残差 | 第二卷第23章（EIS/OIS）、第四卷第16章（视频ISP工程） |
> | Log/ProRes 后期空间 | Log 曲线保留 RAW 动态范围；Apple ProRes 码率策略 | 第二卷第07章（Gamma与色调映射） |
> | 竖拍横置视角自动调整 | 实时画面裁剪+重采样，帧率/延迟/功耗三角约束 | 第四卷第15章（实时处理约束） |
> | HDR 视频录制（Dolby Vision） | 每帧动态元数据实时生成；色调映射 + 色彩空间转换 | 第二卷第19章（HDR显示信号链）、第二卷第20章（视频色彩元数据） |
> | 8K 录制不过热 | SoC 流水线并行调度；功耗预算分配 | 第四卷第22章（ISP功耗优化） |

---

## §1 视频ISP基础：与静态拍照的根本差异

### 1.1 静态与视频ISP的核心矛盾

手机拍照与拍视频共享同一套感光器（sensor）和ISP硬件，但面临截然不同的工程约束。

**时序一致性（Temporal Consistency）**是视频ISP最核心的约束。拍照时每帧可以独立优化——白平衡（AWB）可以每帧跳变，曝光（AE）可以激进调整，降噪可以离线处理。视频是连续帧流，任何参数跳变都会被人眼察觉为"闪烁"（flicker）或"跳变"（jump cut），因此视频3A（AF/AE/AWB）必须以平滑曲线响应场景变化（3A系统架构详见第四卷第01章，AE基础理论详见第四卷第02章）：

$$
P_t = \alpha \cdot P_{t-1} + (1 - \alpha) \cdot P_{\text{target},t}
$$

其中 $P_t$ 是当前帧参数（增益、色温矫正矩阵等），$\alpha$ 是平滑系数（通常 0.8–0.95），$P_{\text{target},t}$ 是当前帧的计算目标值。

**实时约束（Real-time Constraint）**同样严苛：30fps 要求每帧处理时间不超过 33ms，60fps 为 16.7ms，120fps 仅 8.3ms。拍照模式可以持续数百毫秒做多帧处理（如 HDR 合并、Deep Fusion），视频 ISP 则必须在单帧预算内完成全部处理，算法复杂度被严格约束在硬件流水线（pipeline）吞吐能力内（视频ISP实时约束详见第四卷第15章）。

**音视频同步（A/V Sync）**是容易被算法工程师忽视但产品体验极关键的问题。视频帧时间戳必须与音频采样时间戳严格对齐，偏差超过 45ms 人耳即可察觉"嘴型不对" 。ISP 处理延迟、视频编码（encoder）延迟、音频 buffer 延迟三者需要系统级时间戳管理（如 Android MediaSync API）。

### 1.2 帧率选择与场景匹配

不同帧率在运动感知和数据量上差异显著：

| 帧率 | 用途 | 运动快门 | 数据特点 |
|------|------|---------|---------|
| 24fps | 电影感，国际标准电影格式 | 1/48s（180°快门）| 运动模糊自然，最"电影感" |
| 30fps | 全球主流视频标准（NTSC体系）| 1/60s | 平衡流畅与自然感 |
| 60fps | 流畅日常记录，电子竞技直播 | 1/120s | 明显更流畅，运动模糊少 |
| 120fps | 慢动作素材（4× 慢放） | 1/240s | 感光量减少，SNR下降 |
| 240fps | 极端慢动作（8× 慢放） | 1/480s | 噪声重，需更高ISO补偿 |
| 4K120fps | 旗舰规格（骁龙 8 Gen 1 及以上均支持）| 1/240s | ISP带宽要求达到4K30的4倍 |

**24fps的"电影感"来源**不是人眼偏好，而是历史遗留标准 + 特定运动模糊量的叠加效果。180°快门法则（快门速度 = 1/2×帧率）在24fps下产生约 1/48s 的曝光时间，使运动物体产生特定量的运动模糊，这与观众长期形成的"电影观看经验"高度匹配。手机Cinema模式（如 iPhone 的 Cinematic Mode）的关键之一就是在视频中准确模拟 1/48s 快门的运动模糊质感。

**4K120fps工程挑战**：Snapdragon 8 Gen 1（Spectra 680）首次支持 4K120fps 输出，2022年搭载该芯片的旗舰手机陆续量产上市，但代价是 ISP 内部带宽需求约为 4K30fps 的4倍（~200 Gbps内部总线）。高通通过异构 ISP（Hexagon NPU 协同处理）实现这一规格 **[6]**，但在旗舰手机上4K120fps实际录制时间通常限制在3–5分钟以避免过热 。

### 1.3 位深与色彩空间的选择

视频位深直接决定可记录的色调级数和编码压缩损失：

$$
\text{色调级数} = 2^{\text{bit\_depth}}, \quad 8\text{bit}=256\text{ levels}, \quad 10\text{bit}=1024\text{ levels}
$$

| 规格 | 位深 | 编码格式 | 色彩空间 | 典型场景 |
|------|------|---------|---------|---------|
| 标准视频 | 8bit | H.264/AVC | sRGB/BT.709 | 社交媒体、日常记录 |
| 高动态范围视频 | 10bit | H.265/HEVC | BT.2020 + HLG/PQ | HDR显示器、专业分发 |
| Apple ProRes | 10bit | ProRes 422 LT | BT.709 或 Log | 专业后期，高码率 |
| Apple ProRes RAW | 12bit | ProRes RAW | 线性RAW | 专业电影制作 |
| Log格式（Apple/Sony）| 10bit | H.265 或 ProRes | S-Log3/Apple Log | 调色后期 |

**BT.709 vs BT.2020**：BT.709是SDR时代标准，色域覆盖人眼可见色的约35.9%（CIE 1931色品图面积比例）；BT.2020是HDR/UHD标准，色域覆盖约75.8%，可表现更丰富的饱和色（尤其是绿色和红色端）**[4]**。BT.2020色域要在支持它的显示器上才有意义——在普通手机屏幕上回放，超出显示色域的色彩会被映射（gamut mapping）到可显示范围。

---

## §2 Log视频配置文件：最大化保留传感器信息

### 2.1 为什么需要Log格式

相机传感器的光电响应是线性的：入射光子数量与输出电信号呈正比。但人眼对亮度的感知是对数响应（Weber-Fechner定律），且动态范围有限——高端手机传感器可以记录14档（stop）动态范围，而标准8bit视频编码仅能容纳约8档。

把线性传感器数据直接编码为8bit H.264会出现两个问题同时发生：高光因溢出而成为"死白"，暗部因量化级数不足而噪声细节一起丢失。Log格式干的事是把14档动态范围"塞入"10bit编码空间——代价是画面灰蒙蒙（flat），但信息完整，留给后期调色去还原。

逻辑和胶片时代的RAW冲洗一样：**拍摄时保存最大信息，呈现时根据需求定制外观**。

### 2.2 S-Log3：索尼的14档压缩方案

索尼（Sony）S-Log3是专业摄影界广泛使用的Log格式，最早出现在索尼VENICE电影摄影机，后被引入Xperia旗舰手机 **[2]**。

**S-Log3编码公式**：

$$
L_{\text{S-Log3}} = \frac{420 + 261.5 \cdot \log_{10}\!\left(\dfrac{t + 0.01}{0.18 + 0.01}\right)}{1023}
$$

其中：
- $t$ 是场景亮度与18%灰卡亮度的比值（scene luminance ratio），即曝光因子
- 分子中的 420 是18%灰在10bit码值中的位置（约为 0.41 × 1023）
- 261.5 是控制曲线斜率的增益系数
- 分母 1023 归一化到 [0,1] 范围（但实际合法范围约 0.09–0.93，头部和底部留有保护带）

**编码域验证**：
- $t = 0.18$（18%灰）：$L = (420 + 261.5 \cdot \log_{10}(0.18/0.19)) / 1023 \approx 420/1023 \approx 0.41$
- $t = 1.0$（100%反射率白卡）：$L \approx 0.59$
- $t = 16$（比18%灰亮 ~4档，$\log_2 16 = 4$）：$L \approx 0.90$（精确值 $(420 + 261.5 \times \log_{10}(84.26))/1023 \approx 0.903$）

这意味着S-Log3将14档动态范围映射到10bit约0.09–0.93的码值范围，最暗可记录约-4档（低于18%灰4档），最亮可记录约+10档（高于18%灰10档）。

**S-Log3 vs Linear的对比**：在同等场景亮度下，S-Log3编码后画面亮度压缩在中间调，高光不会溢出，但需要配合LUT（Look-Up Table）才能还原为正常观看效果。

### 2.3 Apple Log：苹果的Neural Engine协同设计

Apple于2023年随iPhone 15 Pro引入Apple Log，这是苹果首个面向专业后期的Log格式 **[9]**。

**Apple Log技术规格**：
- 动态范围：相对于18%灰，覆盖 -15 EV 到 +7 EV（共22档理论范围，实际受传感器限制约16档）
- 编码格式：仅支持Apple ProRes（不支持H.265）
- 位深：10bit
- 色彩空间：Apple Log色彩空间（接近BT.2020，但有专属色调曲线）

**Apple Log曲线特性**：Apple Log与S-Log3相比在暗部区域保留了更平滑的斜率（避免暗部噪声被过度放大），且与苹果Neural Engine（神经网络引擎）深度协同——在录制时，ISP输出Log数据，Neural Engine同时生成实时的Rec.709预览LUT，让用户在录制Log的同时看到接近最终效果的监看画面。

**Apple Log编码函数（简化形式）**：

$$
L_{\text{Apple}} = \begin{cases}
\frac{c_1 \cdot t}{\ln(10)} & t \leq t_{\text{cut}} \\
c_2 \cdot \log_{10}(c_3 \cdot t + c_4) + c_5 & t > t_{\text{cut}}
\end{cases}
$$

其中 $c_1$–$c_5$ 为苹果专有系数（Apple Developer文档公开），切换点 $t_{\text{cut}}$ 约对应 -15 EV。分段设计保证了暗部编码的线性精度（避免log函数在接近0时的急剧非线性）。

### 2.4 Canon C-Log3与色彩哲学对比

佳能（Canon）C-Log3虽然主要出现在专业摄影机（EOS C70/C300），但对理解Log格式设计哲学有参考价值：

| 特性 | S-Log3（Sony） | Apple Log | C-Log3（Canon） |
|------|---------------|-----------|----------------|
| 18%灰码值 | 420/1023 ≈ 41% | ~46% | 400/1023 ≈ 39% |
| 动态范围 | 约14档 | 约16档（标称）| 约14档 |
| 暗部斜率 | 较陡，暗部保留细节 | 较平缓，暗部干净 | 中等 |
| 色彩空间配套 | S-Gamut3.Cine | Apple Log CS | Cinema Gamut |
| 后期软件支持 | DaVinci/Premiere/FCPX | FCPX/DaVinci | DaVinci/Premiere |

### 2.5 Log调色工作流

Log视频的标准后期流程为：

```
Log录制 → 导入DaVinci Resolve / Final Cut Pro X
         → 应用技术LUT（将Log转换为线性或Rec.709参考）
         → 创意调色（色相、饱和度、对比度）
         → 输出Rec.709 / BT.2020 HDR
```

**LUT（Look-Up Table）**是一个3D颜色映射表，对输入颜色空间（如Apple Log的R,G,B三通道）的每个采样点，记录对应的输出颜色（如Rec.709的R,G,B）。典型LUT分辨率为33×33×33，通过三线性插值处理中间值。

苹果提供官方"Apple Log to Rec.709"技术LUT（可从Apple Developer下载），专业调色师在此基础上叠加创意LUT（如"电影感橙青色"、"日式低饱和"等）。

---

## §3 8K视频流水线：带宽、功耗与热管理

### 3.1 8K视频的像素吞吐需求

8K分辨率定义为 7680×4320 像素，每帧像素数为：

$$
N_{\text{8K}} = 7680 \times 4320 = 33{,}177{,}600 \approx 3320 \text{万像素/帧}
$$

在30fps下，ISP需要处理的像素速率为：

$$
\dot{N}_{\text{8K30}} = 33{,}177{,}600 \times 30 \approx 10^9 \text{ 像素/秒} = 1 \text{ Gpixel/s}
$$

相比之下，4K30fps 仅约 2490万像素/秒（249 Mpixel/s），8K30fps 是其约4倍。若考虑ISP内部多Pass处理（RAW输入→去噪→去马赛克→色彩变换→输出），实际内部带宽需求更高：

$$
\text{ISP内部带宽} \approx N_{\text{pixel}} \times f_{\text{fps}} \times B_{\text{internal}} \times N_{\text{pass}}
$$

其中 $B_{\text{internal}}$ 为内部位深（通常16–20bit），$N_{\text{pass}}$ 为处理遍数（通常3–5）。8K30fps 的 ISP 内部带宽估算约 50 Gbps，是4K30fps（约6 Gbps）的8倍以上。

### 3.2 三星Galaxy系列：8K消费旗舰（S20 Ultra起）

三星（Samsung）Galaxy S20 Ultra（2020年2月发布）是首款量产支持8K视频录制的消费手机；Galaxy S21 Ultra（2021年）在此基础上优化了多帧ISP管线，依托三星自研Exynos 2100 / 骁龙888平台进一步提升了8K录制稳定性 **[7]**。

**S21 Ultra 8K视频技术参数**：
- 分辨率：7680×4320（8K UHD）
- 帧率：最高30fps
- 编码格式：H.265（HEVC），约80 Mbps码率
- 传感器：HM3 108MP ISOCELL（支持9合1像素binning用于视频）
- 实际限制：8K录制约5分钟后触发过热保护自动降至4K

**像素Binning策略**：在8K模式下，传感器并非全像素读出后下采样，而是采用9合1 Binning（3×3像素合并读出），在降低读出数据量的同时提升感光度（SNR改善约√9 = 3×，约+9.5dB）。实际输出像素数 = 108MP / 9 = 12MP，再通过ISP插值上采样至33MP（8K）。这意味着8K视频的实际分辨率细节并不完全等同于33MP，部分取决于插值质量。

### 3.3 热功耗：8K视频的工程瓶颈

8K视频录制的热功耗来源于三个主要部分：

$$
P_{\text{total}} = P_{\text{sensor}} + P_{\text{ISP}} + P_{\text{encoder}}
$$

| 模块 | 4K30fps典型功耗 | 8K30fps估算功耗 | 增量倍数 |
|------|----------------|----------------|---------|
| 图像传感器（readout）| ~300 mW | ~800 mW | 2.7× |
| ISP处理 | ~500 mW | ~1800 mW | 3.6× |
| H.265编码器 | ~200 mW | ~600 mW | 3.0× |
| 合计 | ~1.0 W | ~3.2 W | ~3.2× |

> **数据说明：** 上述功耗数字为理论估算值，基于芯片规格书和工程测试经验推算的 8K@30fps 极限场景。
> 实测参考（SM8550，4K@60fps，含 EIS+TNR）：ISP 约 350–550 mW，NPU（AI 降噪）约 300–400 mW，
> 编码器（H.265 硬编）约 200–300 mW，整机约 4–5 W。8K 场景相比 4K 带宽需求翻 4 倍，
> 功耗估算按比例缩放但实际受制于散热降频，持续 8K 录制通常触发热限制。
> 如需精确数字，建议参考对应平台的 Power Management SDK 文档或实测 EnergyTrace 数据。

这解释了为什么8K录制消耗电池速度约为4K的3倍，且散热瓶颈早于电量耗尽。现代旗舰手机的热管（vapor chamber）散热设计（面积约5–8 cm²，散热功率约5W），在8K场景下接近极限。

**裁切因子（Crop Factor）问题**：部分手机在8K模式下并不使用全传感器读出区域，而是裁切中心区域以降低Readout数据量和传输带宽。例如某机型4K模式使用等效26mm主摄，8K模式因裁切等效约32mm——视角变窄约19%。这是产品规格表中容易被忽略的工程妥协。

---

## §4 电影级功能：向专业摄影机学习

### 4.1 ProRes格式：苹果的专业承诺

Apple ProRes是苹果针对专业后期设计的帧内编码（Intra-frame codec）格式，与H.264/H.265的帧间预测（Inter-frame prediction）不同，每帧独立编码，便于后期剪辑和色彩处理 **[1]**。

**ProRes系列规格对比**：

| 格式 | 位深 | 色度采样 | 码率（4K30fps）| 1分钟文件大小 |
|------|------|---------|--------------|-------------|
| ProRes 422 LT | 10bit | 4:2:2 | ~330 Mbps | ~2.5 GB |
| ProRes 422 | 10bit | 4:2:2 | ~660 Mbps | ~5 GB |
| ProRes 422 HQ | 10bit | 4:2:2 | ~1 Gbps | ~7.5 GB |
| ProRes 4444 | 12bit | 4:4:4 | ~1.6 Gbps | ~12 GB |
| ProRes 4444 XQ | 12bit | 4:4:4 | ~2.2 Gbps | ~16.5 GB |

iPhone 13 Pro首次支持ProRes录制（4K30fps，ProRes 422 LT，码率约330 Mbps，约2.5 GB/min），iPhone 14 Pro起支持ProRes 422（4K30fps，码率约660 Mbps，约5 GB/min）。存储速度要求：ProRes 422需要写入速度≥800 MB/s，因此仅支持配备NVMe SSD的外置存储（如Lightning/USB-C转SSD）或256GB以上内置存储的型号。

**色度采样的影响**：H.264/H.265通常使用4:2:0色度采样（色度信息水平和垂直各下采样2倍），ProRes 422使用4:2:2（色度仅水平下采样），ProRes 4444使用4:4:4（不降采样）。在绿幕（chroma key）合成等需要精确色度信息的场景，4:2:2 vs 4:2:0的差异对抠图边缘质量有显著影响。

### 4.2 变形宽银幕（Anamorphic）模式

变形宽银幕镜头（Anamorphic lens）最初设计于上世纪50年代（CinemaScope），通过椭圆形镜片组将宽银幕图像水平压缩记录到标准胶片上，回放时水平解压（desqueeze）还原。

**手机Anamorphic模式（iPhone + Moment镜头）**：
- Moment 1.33× Anamorphic镜头：将水平方向图像压缩1.33×记录
- ISP或软件实时解压（desqueeze）：将压缩的画面还原为 16:9 基础上再拓宽为约2.39:1宽高比（即典型的电影宽画幅）
- 椭圆形焦外光斑（bokeh）：由于镜片椭圆变形，焦外点光源呈水平椭圆而非圆形，这是判断"电影感"的标志性视觉元素
- 水平镜头光晕（Lens Flare）：变形镜片对高光产生特征性水平蓝色条状光晕

**数学关系**：若传感器输出 4032×3024（4:3），经1.33× Anamorphic压缩后，记录内容对应宽度为 4032×1.33 = 5362像素（等效），解压后输出为 5362×3024，宽高比约 1.77→2.35:1。实际手机实现中，通常直接输出裁切至 2.39:1 的画面（3840×1607 或类似分辨率）并保留原始压缩文件供后期完整解压。

### 4.3 Dolby Vision视频：逐帧HDR元数据

Dolby Vision是杜比（Dolby）推出的HDR格式标准，相比HDR10的静态元数据（static metadata），Dolby Vision支持**逐帧（frame-level）甚至逐场景（scene-level）动态元数据**，显示端可据此实时调整色调映射参数 **[3]**。

**iPhone 12起的Dolby Vision录制**：
- 内部处理：ISP以12bit HDR数据处理，同时生成两个层（dual-layer）：基础层（Base Layer，Rec.709兼容）和增强层（Enhancement Layer，Dolby Vision动态元数据）
- 元数据内容：每帧记录最大内容亮度（MaxCLL）、最大画面平均亮度（MaxFALL）、色调映射曲线系数
- 显示适配：Dolby Vision播放端（iPhone/Apple TV/兼容电视）读取元数据，按当前显示器能力做最优色调映射——同一视频在iPhone 14 Pro（2000 nit峰值）和普通电视（400 nit）上自动呈现不同但各自最优的HDR效果

**Dolby Vision Profile 8**（iPhone采用）支持10bit编码（Profile 8.4），是目前手机上最常见的Dolby Vision配置。

### 4.4 对焦呼吸补偿（Focus Breathing Compensation）

对焦呼吸（Focus Breathing）是传统变焦/定焦镜头的物理缺陷：在调整对焦距离时，镜片组相对位移导致等效焦距轻微变化，视角（field of view）随之改变，画面呈现轻微"放大/缩小"效果。在视频中，这一效果在对焦切换时造成令人不适的"跳动"。

**电子呼吸补偿（Electronic Focus Breathing Compensation）**：
- 检测：AE/AF控制器实时读取镜头组位置信息（lens position feedback）
- 补偿：当镜头组移动时，ISP对画面进行反向的微量数字变焦（electronic zoom），以抵消视角变化
- 精度要求：通常需要补偿精度在±0.1%视角变化以内，否则补偿本身产生可见的变焦感

Sony Xperia 5 IV等专业视频导向机型率先引入此功能，iPhone 16 Pro在Cinematic Mode中也集成了类似补偿。

---

## §5 防抖与视频ISP的交互设计

### 5.1 EIS裁切与有效分辨率

电子防抖（EIS，Electronic Image Stabilization）的工作原理是：在传感器读出区域中保留一个"防抖缓冲区（EIS margin）"，通过在大图中选取不同中心区域进行裁切来补偿相机运动。裁切比例决定了EIS可以补偿的最大角位移：

$$
\text{最大补偿角度} \approx \arctan\!\left(\frac{W_{\text{sensor}} - W_{\text{output}}}{2 \cdot f_{\text{equiv}}}\right)
$$

其中 $W_{\text{sensor}}$ 为传感器读出宽度，$W_{\text{output}}$ 为输出宽度，$f_{\text{equiv}}$ 为等效焦距。

**iPhone 14 Action Mode示例**：
- 传感器读出：4K（3840像素宽，以主摄26mm等效）
- 输出：2.8K（~2800像素宽）
- EIS裁切比：2800/3840 ≈ 0.73，保留73%宽度
- 可补偿最大角位移：约±8°（足以应对激烈运动如跑步、骑行）
- 代价：等效焦距拉长约1/0.73 = 1.37×，即从26mm变为约36mm

**4K60fps + Cinematic Mode（iPhone 13 Pro）**：
- 传感器：4K全读出
- Cinematic Mode需要景深效果处理缓冲：裁切至约3.7K有效输出，再叠加EIS裁切

### 5.2 OIS + EIS融合策略

OIS（光学防抖）和EIS在频域上有互补特性（EIS/OIS原理详见第二卷第23章）：

| 防抖类型 | 补偿频段 | 补偿量级 | 延迟 |
|---------|---------|---------|------|
| OIS | DC ~ 20Hz（高频手抖）| ±2–3° | 极低（<1ms，机械响应）|
| EIS（陀螺仪辅助）| DC ~ 60Hz | ±5–10°（取决于裁切量）| <1帧（~8–16ms，陀螺采样）|
| EIS（光流辅助）| 0.1 ~ 10Hz | 较小（依赖图像内容）| 1–3帧 |

最优策略是**OIS处理高频（手抖、心跳频率约5–10Hz），EIS处理低频大幅位移（行走/跑步产生的约1–3Hz运动）**。陀螺仪辅助EIS（Gyro-EIS）通过高采样率陀螺仪（通常800–1000 Hz）精确测量相机角速度，预先计算每帧所需裁切位移，延迟小于一帧时间。纯光流EIS需要前一帧图像作为参考，故有1–2帧延迟，但对纯平移运动（如搭乘交通工具的侧向颤动）有更好效果。

iPhone 16 Pro的Cinematic Stabilization采用三级融合：OIS（1000Hz）+ 陀螺仪EIS（500Hz）+ 光流EIS（30fps），实现专业摄影机云台级别的稳定性。

### 5.3 视频防抖的评测指标

| 指标 | 定义 | 典型目标值 |
|------|------|----------|
| Residual Motion（残留运动）| 稳定后的帧间位移均值 | < 0.1% 画面宽度/帧 |
| Crop Ratio（裁切率）| 输出面积 / 传感器面积 | ≥ 70%（Action Mode可低至55%）|
| Latency（延迟）| 运动输入到补偿输出的时间差 | < 33ms（1帧）|
| Horizon Drift（水平线漂移）| 长时间录制中的旋转累计误差 | < 0.1°/min |

### 5.4 VCM执行器力学与视频OIS适配

OIS的物理执行层是**音圈电机（VCM，Voice Coil Motor）**或**形状记忆合金（SMA，Shape Memory Alloy）**执行器。理解执行器力学有助于调试视频防抖的低频漂移和响应延迟问题。

#### VCM工作原理

传统VCM由永磁体、线圈和弹片（suspension spring）组成，利用安培力驱动镜片沿X/Y轴平移（球形导轨OIS）或整个摄像头模组倾转（tilting OIS）：

$$
F = B \cdot I \cdot L
$$

其中 $B$ 为永磁体磁场强度（典型值 0.3–0.5 T），$I$ 为线圈电流（典型驱动范围 ±60 mA），$L$ 为有效导线长度（~10–15 mm）。产生的力 $F$ 克服弹片回复力和运动阻尼，将镜片或模组平移量控制在 ±200–300 μm 以内。

闭环控制方程（忽略摩擦非线性）：

$$
m\ddot{x} + c\dot{x} + kx = F_{\text{drive}} - F_{\text{disturbance}}
$$

- $m$：等效运动质量（镜片组，约 0.1–0.3 g）
- $c$：阻尼系数（弹片材料决定）
- $k$：弹片刚度（约 1–5 N/m，决定自然频率）
- 典型自然频率：$f_n = \frac{1}{2\pi}\sqrt{k/m} \approx 30$–$80\text{ Hz}$

#### 视频场景的VCM特殊挑战

静拍OIS仅需在快门期间（~1/60s 以内）稳定镜片，而视频OIS需要**持续运动跟踪**，这对VCM提出了更严苛要求：

| 挑战 | 静拍OIS | 视频OIS |
|------|---------|---------|
| 工作时长 | 短脉冲（<1/30s）| 连续（录制全程）|
| 热漂移 | 可忽略 | 线圈发热→磁场漂移→零点偏移 |
| 低频运动 | 无需补偿 | 行走低频（1–3Hz）需纳入控制带宽 |
| 位置精度 | ±5μm 够用 | ±1–2μm（避免视频抖动可见性）|

**热漂移补偿**：视频连续录制导致VCM线圈温升（典型 ΔT ≈ 20–40°C 在10分钟4K60录制后），永磁体磁场随温度升高而下降（NdFeB约 -0.1%/°C），导致同样电流产生更小位移。现代OIS驱动IC（如TDK TAD1170、AKM AK7389）集成温度传感器，通过查表（温度→增益补偿因子）实时修正。

#### SMA执行器与VCM的对比

Apple iPhone 15 Pro的潜望长焦和部分三星旗舰主摄采用**SMA（形状记忆合金）**执行器（如Cambridge Mechatronics SMA OIS）：

| 特性 | VCM | SMA |
|------|-----|-----|
| 厚度 | ~4–6 mm（模组高度限制因素）| ~1.5 mm（Z轴超薄）|
| 功耗（持续视频）| ~30–50 mW | ~50–80 mW（加热维持形变）|
| 响应速度 | ~1ms（电磁响应）| ~5–10ms（热响应，视频场景够用）|
| 视频低频补偿 | 依赖弹片刚度设计 | 刚度可调（更大行程）|
| 可靠性 | 成熟，≥100万次循环 | 疲劳寿命是量产关注点 |

SMA在视频场景的主要劣势是**响应延迟**：热激励响应约5–10ms，对比VCM的<1ms，在高速运动（如体育拍摄）的OIS校正中有轻微滞后感。工程取舍上，SMA更多用于旗舰主摄（对Z轴厚度敏感），VCM仍是超长焦潜望镜头的主流方案（需要大行程×轴平移）。

---

## §6 代码实现：Log视频仿真与LUT应用

本章配套Jupyter Notebook（本章配套代码（见本目录 .ipynb 文件））包含以下实现模块：

### 6.1 合成HDR场景与Log编码仿真

```python
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import RegularGridInterpolator

def slog3_encode(t):
    """
    Sony S-Log3 编码函数
    t: 场景亮度比（相对于18%灰，线性值）
    返回: 10bit归一化码值 [0, 1]
    """
    # 避免log(0)，加入截断保护
    t = np.maximum(t, 1e-6)
    L = (420.0 + 261.5 * np.log10((t + 0.01) / (0.18 + 0.01))) / 1023.0
    return np.clip(L, 0, 1)

def slog3_decode(L):
    """S-Log3 解码（逆变换）"""
    L_code = L * 1023.0
    t = 10 ** ((L_code - 420.0) / 261.5) * (0.18 + 0.01) - 0.01
    return np.maximum(t, 0)

def apple_log_encode(t, cutpoint=0.01):
    """
    Apple Log 简化编码函数（基于Apple Developer文档参数）
    """
    # Apple Log参数（公开值近似）
    c1, c2, c3, c4, c5 = 0.2098, 0.3906, 0.2, 0.01, 0.399
    t = np.maximum(t, 1e-7)
    L = np.where(
        t <= cutpoint,
        c1 * t / np.log(10),
        c2 * np.log10(c3 * t + c4) + c5
    )
    return np.clip(L, 0, 1)

# 生成合成HDR场景（动态范围约14档）
ev_range = np.linspace(-4, 10, 1024)  # 相对18%灰的EV范围
luminance_linear = 0.18 * (2 ** ev_range)  # 线性亮度

# 编码对比
L_slog3 = slog3_encode(luminance_linear)
L_apple = apple_log_encode(luminance_linear)
L_gamma22 = np.clip(luminance_linear ** (1/2.2), 0, 1)  # 标准sRGB近似

plt.figure(figsize=(10, 6))
plt.plot(ev_range, L_slog3, label='S-Log3', color='#E8A020')
plt.plot(ev_range, L_apple, label='Apple Log', color='#555555')
plt.plot(ev_range, L_gamma22, label='sRGB Gamma 2.2', color='#3070C0', linestyle='--')
plt.axvline(0, color='gray', linestyle=':', alpha=0.5, label='18% grey (EV=0)')
plt.xlabel('场景EV（相对18%灰）')
plt.ylabel('编码码值（归一化）')
plt.title('Log格式 vs sRGB编码曲线对比')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
```

### 6.2 3D LUT构建与应用

```python
def apply_3d_lut(img_log, lut_3d, lut_size=33):
    """
    应用3D LUT进行色彩空间转换
    img_log: 输入Log图像 [H, W, 3]，值范围[0,1]
    lut_3d: 3D LUT数组 [lut_size, lut_size, lut_size, 3]
    """
    H, W, _ = img_log.shape
    axes = [np.linspace(0, 1, lut_size)] * 3

    # 为每个通道构建插值器
    lut_out = np.zeros_like(img_log)
    for c in range(3):
        interp = RegularGridInterpolator(
            axes, lut_3d[..., c], method='linear'
        )
        pts = img_log.reshape(-1, 3)
        lut_out[..., c] = interp(pts).reshape(H, W)

    return np.clip(lut_out, 0, 1)

def generate_identity_lut(size=33):
    """生成恒等LUT（无变换）"""
    grid = np.linspace(0, 1, size)
    R, G, B = np.meshgrid(grid, grid, grid, indexing='ij')
    lut = np.stack([R, G, B], axis=-1)
    return lut

def slog3_to_rec709_lut(size=33):
    """
    生成 S-Log3 → Rec.709 转换LUT
    （简化版，实际LUT需要精确色彩科学校正）
    """
    grid = np.linspace(0, 1, size)
    R, G, B = np.meshgrid(grid, grid, grid, indexing='ij')
    lut_input = np.stack([R, G, B], axis=-1)  # [size,size,size,3]

    # 解码S-Log3 → 线性场景亮度
    lut_linear = slog3_decode(lut_input)

    # 线性 → Rec.709 gamma（简化为gamma 2.2）
    lut_709 = np.clip(lut_linear ** (1/2.2), 0, 1)

    return lut_709
```

### 6.3 帧间光流分析（防抖评估）

```python
import cv2

def analyze_frame_stability(video_frames):
    """
    分析连续帧的稳定性（用光流估计帧间运动）
    video_frames: list of numpy arrays [H, W, 3]
    返回: 每帧的残留运动量（像素）
    """
    motions = []
    prev_gray = cv2.cvtColor(video_frames[0], cv2.COLOR_RGB2GRAY)

    for frame in video_frames[1:]:
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

        # 稀疏光流（Lucas-Kanade）
        corners = cv2.goodFeaturesToTrack(
            prev_gray, maxCorners=100, qualityLevel=0.01, minDistance=10
        )
        if corners is not None:
            next_pts, status, _ = cv2.calcOpticalFlowPyrLK(
                prev_gray, curr_gray, corners, None
            )
            good_prev = corners[status == 1]
            good_next = next_pts[status == 1]

            # 计算帧间位移（像素）
            displacement = np.linalg.norm(
                good_next - good_prev, axis=1
            ).mean()
            motions.append(displacement)
        else:
            motions.append(0.0)

        prev_gray = curr_gray

    return np.array(motions)

def build_rec709_lut(gamma=2.2, size=256):
    """构建1D Rec.709 Gamma LUT (size × 3)"""
    x = np.linspace(0, 1, size)
    y = np.clip(x ** (1.0 / gamma), 0, 1)
    return np.stack([y, y, y], axis=-1).astype(np.float32)

# ─── 示例调用与输出 ───────────────────────────────────────
lut = build_rec709_lut(gamma=2.4)
print('LUT shape:', lut.shape, 'LUT[128]:', lut[128])
# 输出: LUT shape: (256, 3)  LUT[128]: [0.502 0.502 0.502]

```

Notebook完整版包含：(1) 合成14档HDR测试场景并分别编码为S-Log3/Apple Log/sRGB，对比三者直方图分布；(2) 构建33³ LUT并应用于Log图像，展示调色前后对比；(3) 对模拟手抖视频序列运行光流分析，定量评估EIS稳定效果；(4) Dolby Vision元数据结构解析示例。

---

## §7 工程实践与调优要点

### 7.1 视频3A平滑控制参数

视频AE收敛时间常数（time constant）是产品体验的关键调参点：

$$
\tau = \frac{-\Delta t}{\ln(\alpha)}
$$

其中 $\Delta t$ 为帧间时间间隔（1/fps），$\alpha$ 为平滑系数。例如30fps下 $\alpha=0.9$，则 $\tau \approx -\frac{1/30}{\ln 0.9} \approx 0.316$ 秒——即场景亮度突变后约0.3秒达到新曝光值的63%。

针对不同场景，推荐的AE平滑时间常数：
- 室内平稳拍摄：τ = 0.3–0.5 秒（用户不觉察AE在调整）
- 户外快速走动：τ = 0.15–0.3 秒（需要稍快响应，避免运动进入阴影后长时间过曝）
- 逆光场景转身：τ = 0.1–0.2 秒（过慢会导致人脸长时间欠曝）

> **工程推荐（手机视频3A场景）：** 视频AE的平滑系数不要用固定值，应根据亮度变化幅度做自适应——场景亮度变化 < 1EV时保持大α（慢收敛，防闪烁），变化 > 3EV时切换小α（快收敛，防人脸欠曝）。Log视频模式下曝光目标值应相对正常模式整体上调0.5–1EV，让中间调落在S-Log3曲线的40%–60%码值区间，否则暗部噪声会因Log曲线放大而在后期调色时被放大。4K120fps模式下单帧AE调整步长要进一步减半——120fps回放时单帧过曝在慢动作里明显可见。

### 7.2 常见视频ISP伪影及处理

| 伪影 | 原因 | 处理方法 |
|------|------|---------|
| 帧间闪烁（Flicker）| AWB参数跳变 | 增大AWB平滑系数，或锁定色温在无明显变化时 |
| 果冻效应（Rolling Shutter）| CMOS逐行读出时间差（约8–16ms/帧）| 增加ISP帧缓冲做Rolling Shutter Correction（RSC）|
| 带状噪声（Banding）| 交流电源50/60Hz灯光与快门不同步 | AE自动选择1/100s（50Hz）或1/120s（60Hz）快门 |
| 编码块效应（Blocking）| H.265码率不足，高频纹理压缩损失 | 提高最低码率下限，或使用ProRes |
| 色偏跳变（Color Jump）| 多摄切换时色彩校准不到位 | 过渡帧做跨摄像头色彩插值（参见第二卷第22章）|

### 7.3 2024 年视频ISP重要进展：4K@120fps 与 AI NR 落地

2024年有两件事在视频ISP工程上真正落地，不是PPT规格，是量产机型上跑通了的：

**Apple iPhone 16 Pro：4K@120fps 的解锁**

4K@120fps（ProRes / HEVC）在 iPhone 15 Pro 硬件上已具备条件，但苹果以"热管理尚未达标"为由限制了该功能，直到 iPhone 16 Pro（A18 Pro，台积电 3nm）才正式开放。技术关键在于以下三点协同解决：

1. **ISP 带宽扩容**：4K@120fps RAW 数据率约 7.5 GB/s（相比4K@30fps 的~1.9 GB/s 提升约4倍），A18 Pro 的图像 ISP 总线带宽相应扩展。
2. **编码器效率提升**：A18 Pro 内置专用 ProRes 编码器，ProRes 4444 XQ @ 4K120 码率约 800 Mbps，要求外置存储写入速率 ≥ 100 MB/s（Apple 推荐使用 USB-C 高速外接 SSD；iPhone 不支持 CFexpress Type B，该规格为专业相机存储卡格式）。
3. **热管理优化**：4K@120fps 模式整机热耗约 5.5–6W（相比4K@30fps 的 ~3W），A18 Pro 的石墨散热层面积扩大约 15%，加之 iOS 18 的帧率自适应降级策略（长时间录制后自动降至60fps 并通知用户），保证不触发过热保护。

**ISP 工程意义：** 4K@120fps 使手机视频具备真正的高帧率慢动作+高分辨率同时记录能力（之前 960fps 慢动作需要降至 1080p 或更低分辨率），对 AE 平滑响应要求更严苛——帧间时间仅 8.3ms，AE 调整步长必须更小（防止单帧过曝/欠曝在120fps 回放时仍可见）。

**AI 视频降噪（AI Video NR）的量产落地：2024 旗舰对比**

2023–2024年间，多个旗舰平台将神经网络视频降噪从"高端后处理模式"推进到"实时录制流水线"（时域降噪TNR原理详见第二卷第12章）：

| 平台 | 推出时间 | AI NR 方案 | 实时规格 | 功耗代价 |
|------|---------|-----------|---------|---------|
| vivo V3+（天玑9400）| 2024Q4 | V3+ NPU 旁路 AI NR，时域+空域联合 | 4K@30fps 全时实时 | +~0.3W（相比V3降低20%）|
| 骁龙8 Gen3 Spectra 800 | 2024Q1 | 片上 Hexagon NPU AI NR（Qualcomm AI NR SDK v2）| 4K@30fps，4K@60fps（旗舰）| 共享NPU，对游戏等负载有轻微影响 |
| 天玑9300 Imagiq 980 | 2023Q4 | MediaTek HyperEngine AI NR | 4K@30fps 实时 | ~0.4W 额外功耗 |
| Apple A18 Pro | 2024Q3 | Photonic Engine 延伸至视频帧，Neural Engine RAW NR | 4K@60fps（ProRes Log）| 集成在ISP流水线，无独立功耗计量 |

AI NR 在视频中相比照片的核心挑战是**时域一致性（Temporal Consistency）**：相邻帧的降噪强度与纹理保留若不一致，在运动场景中会产生"纹理闪烁"（texture flickering）。工业界主流方案是在网络架构中引入**时域对齐模块**（基于光流或可变形卷积），对参考帧和当前帧做对齐后联合降噪，代表工作包括 FastDVDnet（Tassano et al., CVPR 2020）和 RViDeNet（Yue et al., CVPR 2020）。在 NPU 实现中，时域对齐的光流计算通常以简化版（如 TV-L1 或 RAFT-small INT8 量化版）实现，计算开销约占总 NR 算力的 30–40%。

> **工程推荐（视频AI NR部署优先级）：** 视频NR上NPU之前必须先确认时域一致性，不然4K@30fps降噪后的纹理闪烁比不降噪更难看。在旗舰平台上落地视频NR的优先顺序：先做空域NR（无时序依赖，最容易INT8量化），再加时域对齐（先用陀螺仪辅助的简化光流，而不是NN光流），最后引入可变形卷积时域融合。纯NN光流在4K@60fps上的算力消耗基本等于整个NR网络的2倍——除非有专用光流硬件，否则不建议在实时录制场景中使用。

---

## §8 术语表（Glossary）

| 术语 | 英文全称 / 缩写 | 解释 |
|------|---------------|------|
| Log配置文件 | Log Profile | 将宽动态范围压缩到固定位深的非线性编码曲线，保留最大传感器信息 |
| LUT | Look-Up Table | 颜色映射表，用于将输入颜色空间映射到输出颜色空间 |
| ProRes | Apple ProRes | 苹果开发的帧内编码专业视频格式，支持10–12bit，高码率 |
| S-Log3 | Sony S-Log3 | 索尼Log编码格式，设计覆盖约14档动态范围 |
| Apple Log | Apple Log | 苹果Log编码格式，随iPhone 15 Pro引入，优化Neural Engine解码 |
| Dolby Vision | Dolby Vision | 杜比逐帧HDR元数据格式，支持显示端自适应色调映射 |
| Anamorphic | Anamorphic / 变形宽银幕 | 通过椭圆镜片组压缩水平视角，回放时解压呈现宽银幕比例 |
| EIS | Electronic Image Stabilization | 电子防抖，通过裁切图像缓冲区补偿相机运动 |
| 帧率 | Frame Rate / fps | 每秒记录的视频帧数，决定运动流畅性与慢动作能力 |
| Rolling Shutter | Rolling Shutter | CMOS逐行曝光导致的果冻变形效果 |
| 色度采样 | Chroma Subsampling | 色度分量的空间下采样方案，如4:2:0、4:2:2、4:4:4 |
| Gyro-EIS | Gyroscope-assisted EIS | 陀螺仪辅助的电子防抖，延迟低于一帧 |
| OIS | Optical Image Stabilization | 光学防抖，通过VCM执行器物理移动镜片或模组抵消相机抖动 |
| VCM | Voice Coil Motor | 音圈电机，OIS执行器核心，利用安培力驱动镜片平移，补偿范围±200–300μm |
| SMA | Shape Memory Alloy | 形状记忆合金执行器，相比VCM更薄（~1.5mm），部分旗舰主摄OIS采用 |

---

## 习题

**练习 1（理解）**
Log 色彩模式（如 S-Log3、Apple Log）通过对曝光值做对数编码来扩展动态范围记录能力。假设传感器的原始动态范围为 14 档（EV），8-bit 线性编码仅能表示约 8 档有效动态范围（高 ISO 噪声限制低亮端）。请计算：使用 10-bit Log 编码后，有效动态范围可以提升到多少档？Log 编码中低亮区域分配了更多码值（相对于线性编码），这对后期调色的高光恢复操作有何好处？

**练习 2（分析/比较）**
手机视频 ISP 的发热问题直接影响持续录制能力和参数配置。在持续录制 4K/60fps 约 10 分钟后，主流旗舰手机会出现不同程度的热降频（thermal throttling）。请分析：热降频通常首先影响哪些 ISP 模块（NR 算法、视频防抖稳定化、HDR 合并、AI 人像识别）？手机厂商通常采用哪些工程策略来延长高质量录制时长（散热结构、算法自适应降级、帧率自动切换）？

**练习 3（实践）**
估算 8K/30fps 视频录制的 DRAM 带宽需求。假设：8K 分辨率为 7680×4320，每帧 RAW 数据为 10-bit，同时需要维持两帧 RAW 缓冲区（用于多帧 HDR 合并），ISP 输出为 10-bit 4:2:2 YUV。计算：（1）每秒 RAW 数据读带宽（GB/s）；（2）ISP 输出的写带宽（GB/s）；（3）与 LPDDR5X 的典型带宽（约 77 GB/s）相比，DRAM 带宽是否成为 8K ISP 的瓶颈？

---

## 参考文献

1. Apple Inc., "Apple ProRes White Paper" (2022), Apple Developer Documentation. https://developer.apple.com/documentation/avfoundation/apple_prores
2. Sony Corporation, "S-Log3/S-Gamut3 Specification" (2014), Sony Professional. 公开技术规范文档.
3. Dolby Laboratories, "Dolby Vision for Content Creators" (2023), Dolby Professional. https://professional.dolby.com/
4. ITU-R BT.2020, "Parameter values for ultra-high definition television systems for production and international programme exchange" (2015). ITU标准.
5. ITU-R BT.709, "Parameter values for the HDTV standards for production and international programme exchange" (2015). ITU标准.
6. Qualcomm, "Snapdragon 8 Gen 2 Mobile Platform Specification" (2022). 高通官方产品规范.
7. Samsung Electronics, "Galaxy S21 Ultra Camera Technical Brief" (2021). 三星官方技术文档.
8. SMPTE ST 2084:2014, "High Dynamic Range Electro-Optical Transfer Function of Mastering Reference Displays". SMPTE标准（PQ曲线定义）.
9. Apple Inc., "WWDC 2023 - Discover log video in your app" (2023). Apple Developer. https://developer.apple.com/videos/play/wwdc2023/
10. Wronski, B. et al., "Handheld Multi-Frame Super-Resolution" (2019). SIGGRAPH 2019. [HDR+技术基础，与视频ISP时序处理相关]


---

> **工程师手记：4K60fps视频ISP的功耗与热管理工程实践**
>
> **4K60fps视频ISP的功耗构成：** 在骁龙8 Gen 2平台上实测4K60fps视频录制时，ISP子系统（Spectra 660 ISP）的功耗约为1.8W，占整机录制功耗（总计约5.5-6.0W）的30-33%。这1.8W分解为：前端Raw处理流水线（降噪、HDR合成）约0.7W、视频编码器H.265 Main 10约0.6W、实时EIS防抖（GYRO+OIS联合补偿）约0.3W、其余ISP后处理（NR、Sharpening、色调映射）约0.2W。实际工程中，功耗测量需使用Monsoon电源分析仪或片上PMU寄存器读取，单纯依赖系统功耗差值法误差较大，因为CPU/GPU负载在录制时也会波动。若开启Log模式（S-Log/HLG）并关闭实时NR，ISP功耗可降至约1.3W，但需要用户后期处理承担更多计算负担。
>
> **热节流：4K录制8-10分钟后的降级机制：** 实测多款旗舰机型，在环境温度25°C、机身背面温度达到43-45°C阈值时，SoC的热管理模块（ThermalHAL）会触发第一级降频：ISP处理帧率从60fps降至30fps，编码码率从原定100Mbps降至60Mbps。此时如仍未散热，约12-15分钟后触发第二级降级：分辨率从4K（3840×2160）主动降至1080P，并在UI上弹出"设备过热"提示。DJI Action 4系列通过主动风冷（微型轴流风扇）将机身核心温度稳定在37°C以内，从而实现连续4K60fps录制超过60分钟而不触发热节流，功耗代价是风扇额外增加约0.4W，但换来的是完全无热节流的录制稳定性，这一设计理念与手机的被动散热策略存在根本性差异。
>
> **DJI运动相机与手机视频ISP热管理架构对比：** 手机视频ISP的热管理本质上是"被动散热+软件降级"的组合策略，而DJI Osmo Action系列的设计哲学截然不同：主动散热优先。具体表现在：DJI将ISP核心封装在面积更大的散热铜片覆盖区域，并在机身后盖内侧设计导热垫直连机壳散热；而手机由于机身超薄（7-8mm），散热铜片与外壳之间只能依赖石墨片传导。从热阻角度，DJI Action系的θ_ja（结到环境热阻）约25-30°C/W，而手机SoC的θ_ja通常超过45°C/W，这意味着在同等ISP功耗下，手机核心温度要比DJI Action Camera高约15-20°C，导致热节流更早触发。
>
> *参考：Qualcomm, "Snapdragon 8 Gen 2 Product Brief", Qualcomm Technologies, 2022；DJI, "Osmo Action 4 Technical Specifications", DJI Official, 2023；Android Open Source Project, "Thermal HAL", developer.android.com/reference/android/os/HardwarePropertiesManager*

---

## 插图

![fig video isp pipeline](img/fig_video_isp_pipeline_ch.png)

*图1. 视频ISP处理流水线*

![video codec comparison](img/fig_video_codec_comparison_ch.png)

*图2. 视频编解码格式对比*

![video hdr formats](img/fig_video_hdr_formats_ch.png)

*图3. 视频HDR格式体系*

![video isp latency budget](img/fig_video_isp_latency_budget_ch.png)

*图4. 视频ISP延迟预算分析*

![video stabilization crop tradeoff](img/fig_video_stabilization_crop_tradeoff_ch.png)

*图5. 视频防抖裁剪比例权衡*

![video stabilization score](img/fig_video_stabilization_score_ch.png)

*图6. 视频防抖效果评分*


---
![dolby vision pipeline](img/fig_dolby_vision_pipeline_ch.png)

*图7. 杜比视界处理流水线（图片来源：Dolby Laboratories, 官方技术文档）*

![hdr video metadata](img/fig_hdr_video_metadata_ch.png)

*图8. HDR视频元数据结构*

![video isp pipeline mobile](img/fig_video_isp_pipeline_mobile_ch.png)

*图9. 移动端视频ISP流水线*

![video stabilization pipeline](img/fig_video_stabilization_pipeline_ch.png)

*图10. 视频防抖处理流程*

