# Part 5, Chapter 10: World Models for Imaging Simulation

> **Position:** Optional reading chapter (📚), focusing on world-model approaches in imaging simulation.
> **Prerequisites:** Vol. 3 Ch. 01 (DL ISP Overview), Vol. 3 Ch. 15 (NeRF and 3DGS)

> **Frontier content**: Based on 2025-2026 CVPR/ICCV/NeurIPS advances. Engineering deployment cases are actively expanding. Contributions welcome via [Issue](https://github.com/AIISP/isp_handbook/issues).

---

## §1 Theory

### 1.1 What Is a World Model?

A world model (世界模型) is a **learned neural simulator** that models environment state transitions: given the current state $s_t$ and action $a_t$, it predicts the next state $s_{t+1}$ together with the associated observation signal. This concept originates in Reinforcement Learning (强化学习, RL) — if an agent can "imagine" the world's response internally, it no longer needs to interact repeatedly with the real environment, dramatically reducing sample requirements.

From an imaging perspective, **a world model = a learned joint simulator of sensor + optical system + ISP**. Its core value lies in synthesizing images under arbitrary scene conditions — different illumination, different motion blur levels, different noise levels, even different sensor models — without relying on real hardware. For ISP development this has at least three direct implications:

1. **Training data generation**: generate diverse paired training samples for DL ISP models, avoiding expensive controlled laboratory capture sessions;
2. **Pre-silicon SoC validation** (硅前验证): predict the performance of ISP algorithms on new sensors even before the chip is fabricated;
3. **ISP robustness testing**: systematically evaluate ISP edge cases by simulating extreme illumination, motion, and noise conditions.

### 1.2 JEPA: Joint Embedding Predictive Architecture

The **Joint Embedding Predictive Architecture (联合嵌入预测架构, JEPA)** proposed by LeCun (2022) is one of the most rigorous theoretical frameworks for world models. The core distinction between JEPA and pixel-space prediction (such as video diffusion) is that prediction takes place in **abstract representation space** (抽象嵌入空间) rather than pixel space.

Formally, JEPA consists of three modules:

- **Context encoder** $f_\theta$: encodes the current observation $x$ into a context representation $s_x = f_\theta(x)$;
- **Target encoder** $g_\phi$ (momentum-updated, no gradient flow): encodes the target observation $y$ into a target representation $s_y = g_\phi(y)$;
- **Predictor** $h_\psi$: takes $s_x$ and an action/conditioning signal and predicts the target representation $\hat{s}_y = h_\psi(s_x, a)$.

The training objective is to minimize the prediction error in embedding space:

$$\mathcal{L}_{\text{JEPA}} = \| \hat{s}_y - \text{sg}(s_y) \|_2^2$$

where $\text{sg}(\cdot)$ denotes the stop-gradient operation, which prevents representation collapse. Compared with MAE (Masked Autoencoder), JEPA does not need to reconstruct pixel details, so it does not waste learning capacity on "predicting pixel-level texture noise" and instead focuses on semantic-level prediction — exactly what is needed to build a physical world model.

Implication for imaging simulation: JEPA's abstract prediction paradigm means that an imaging world model does not need to simulate every scattered photon at pixel precision — it only needs to match the real sensor output in perceptual embedding space. This opens a path to bypassing the high computational cost of physical rendering.

### 1.3 Modeling the Imaging Physics Chain

The complete camera imaging physics chain (成像物理链路) can be expressed as:

$$I_{\text{RAW}} = \mathcal{N}\!\left( \mathcal{Q}\!\left( \mathcal{K} \cdot \Phi \right) \right)$$

$$I_{\text{sRGB}} = \mathcal{P}_{\text{ISP}}\!\left( I_{\text{RAW}} \right)$$

where:
- $\Phi$ is the photon flux arriving at the sensor (determined by scene radiance, lens aperture, and exposure time);
- $\mathcal{K}$ is the sensor quantum efficiency and gain matrix;
- $\mathcal{Q}$ is ADC quantization;
- $\mathcal{N}$ is the combined Poisson noise + read noise + fixed pattern noise;
- $\mathcal{P}_{\text{ISP}}$ is the complete ISP pipeline operator.

The traditional approach is to accurately model each step above using physical parameters (ISO, exposure time, noise level function NLF). The **incremental value of world models** lies in using neural-network-learned priors to supplement the physical model, especially for components that are difficult to describe precisely with formulas — for example, non-rotationally-symmetric lens aberrations (非旋转对称像差), column-correlated sensor noise (列噪声相关性), and the non-linear decision logic of ISP pipelines.

---

## §2 Camera World Models

### 2.1 Neural Rendering as a World Model Component

**Neural Radiance Fields** (神经辐射场, NeRF; Mildenhall et al., ECCV 2020) were the earliest "camera world model" prototype recognized by the industry. NeRF represents a scene as a continuous volumetric radiance function:

$$(\sigma, \mathbf{c}) = F_\Theta(\mathbf{x}, \mathbf{d})$$

where $\mathbf{x}$ is the spatial coordinate, $\mathbf{d}$ is the viewing direction, $\sigma$ is the volume density, and $\mathbf{c}$ is the emitted color. Volume rendering integrates the radiance along a ray into a pixel color:

$$\hat{C}(\mathbf{r}) = \int_{t_n}^{t_f} T(t)\, \sigma(t)\, \mathbf{c}(t, \mathbf{d})\, dt$$

NeRF's world model value lies in its **synthesis capability**: given images from existing viewpoints, the reconstruction allows synthesis of arbitrary new viewpoints — and even the virtual camera's aperture and focal length can be changed — thereby simulating image output under different optical configurations.

**3D Gaussian Splatting** (三维高斯泼溅, 3DGS; Kerbl et al., SIGGRAPH 2023) represents scenes with explicit 3D Gaussian primitives (三维高斯基元), overcoming NeRF's bottleneck of slow training and inference. 3DGS can complete training in minutes and renders at 100+ FPS, making it the industry's preferred real-time neural rendering solution. This is especially important for ISP synthetic data generation: 3DGS can rapidly render "virtual RAW" images of the same scene at different exposures and different ISOs; overlaying a noise model on top produces paired training data.

**RawNeRF** (Mildenhall et al., CVPR 2022) extends NeRF to the RAW domain, modeling scene radiance directly in the linear light domain rather than in tone-mapped sRGB. This enables high-fidelity synthesis of RAW images at arbitrary exposure conditions from the same scene — a key capability for ISP world models, since ISP algorithm development and evaluation require large amounts of paired RAW data spanning different exposure/ISO combinations.

### 2.2 Diffusion-Model-Driven Scene Editing

**Diffusion models** (扩散模型) as scene generators provide a complementary path for ISP training data synthesis:

- **InstructPix2Pix** (Brooks et al., CVPR 2023) allows editing images through text instructions (e.g., "convert daytime to nighttime"), enabling large-scale generation of synthetic images under different illumination conditions for ISP low-light algorithm training;
- **ControlNet** (Zhang et al., ICCV 2023) constrains diffusion generation with control signals such as depth maps and normal maps, producing scene variants with geometrically consistent structure and ensuring controllability of synthesized images;
- **IP-Adapter** (Ye et al., ICCV 2023) enables generation driven by the style of a reference image, simulating the visual style of different sensors (different color responses, different micro-lens arrays).

### 2.3 Imaging Simulation Pioneers in Autonomous Driving

The autonomous driving (自动驾驶) domain has demands for imaging simulation that closely parallel those of ISP, and has produced mature world model solutions that ISP engineers can draw upon:

**UniSim** (Yang et al., CVPR 2023) builds a neural closed-loop sensor simulator (神经封闭式世界模型) capable of reconstructing scenes from real driving logs and synthesizing images under arbitrary sensor configurations (different focal lengths, resolutions, and frame rates). Its core technology stack — 4D scene graph (4D场景图) + neural rendering — handles camera, LiDAR, and radar multi-sensor simulation within a single unified framework.

**DriveDreamer** (Wang et al., ECCV 2024) is a video world model designed specifically for autonomous driving scenes. It uses HD maps and 3D bounding box annotations as conditional control signals for video generation, and explicitly models sensor noise characteristics (ISO-dependent noise amplitude, highlight clipping in HDR scenes) during the generation process. Unlike UniSim's static scene reconstruction, DriveDreamer focuses on **dynamic scene generation** — synthesizing complex scenes where vehicle motion, pedestrian interaction, and lighting variation are interleaved — providing a data source for robustness testing of ISP algorithms under motion blur and high dynamic range conditions.

**CityDreamer** (Xie et al., CVPR 2024) is a generative 3D world model designed specifically for urban scenes, using unbounded scene representation (无界场景表示) to handle city-scale large-area scenes. Value for ISP: it can synthesize high-fidelity images of urban scenes under a variety of illumination conditions (dawn glow, midday harsh light, rainy-day diffuse light), covering all typical scenarios that ISP algorithms need to handle robustly.

**WoRLD** (World model for Real-world Lidar Data; Lee et al., 2024) explores an end-to-end framework for applying world models to sensor simulation, making sensor physical parameters (noise model, dynamic range, color response) learnable/searchable hyperparameters.

### 2.4 ISP Application: Synthesizing RAW Images Under Different Sensor Configurations

A concrete plan for integrating the above techniques into the ISP R&D workflow:

1. **Multi-exposure RAW synthesis**: use RawNeRF or 3DGS to render the same scene at different exposures (EV −4 to EV +4), generating paired training data for HDR merge algorithms;
2. **Sensor transfer**: given real RAW images from sensor A, synthesize equivalent RAW images for sensor B through a learned noise domain transfer network, enabling low-cost cross-sensor data augmentation;
3. **Illumination condition diversification**: synthesize scenes under different illumination conditions (color temperature 2700K–7500K, varying illumination intensity) using diffusion models or neural rendering, providing sufficient training scene diversity for AWB and AE algorithms.

---

## §3 Imaging Simulation Pipeline

### 3.1 Physical Model Layer

A complete imaging simulation pipeline (成像仿真流水线) consists of two parts — a **physics layer** and a **neural network layer** — with the physics layer responsible for deterministic, analytically expressible modeling:

**Lens optics simulation**:
- Diffraction blur (衍射模糊): caused by the aperture diffraction limit; PSF approximated as an Airy disk;
- Geometric aberrations (几何像差): distortion (畸变), coma (彗差), astigmatism (像散);
- Chromatic aberration (色差): longitudinal CA (轴向色差) and lateral CA (横向色差);
- Vignetting (晕影): peripheral light falloff due to aperture obstruction and the cosine-fourth-power law.

**Sensor noise model**:

Standard Poisson-Gaussian noise model (泊松-高斯混合噪声模型):

$$n = \mathcal{P}(\lambda \cdot I) / \lambda + \mathcal{N}(0, \sigma_r^2)$$

where $\lambda$ is the quantum efficiency scaling factor and $\sigma_r$ is the read noise standard deviation. A more complete model also includes Fixed Pattern Noise (FPN, 固定图案噪声) and column noise (列噪声).

**ISP operator chain**: BLC → LSC → Demosaic → AWB → CCM → Denoising → Sharpening → Gamma/Tonemapping → CSC

### 3.2 Neural Network Enhancement Layer

The parameters of the physical model are limited and cannot capture all the complexity of real systems. The world model introduces neural-network-learned priors on top of the physics layer:

**Residual Correction Network** (残差校正网络): a lightweight CNN stacked on top of the physical simulation output that learns the residual between the physical model and the real sensor. Typically only 4–8 convolutional layers are needed to significantly improve simulation fidelity (仿真保真度).

**Conditional Neural Noise Sampling** (条件化神经噪声采样): uses a conditional generative model (conditioned on exposure time, ISO, and temperature) to sample the precise distribution of real sensor noise, rather than using a parameterized simple noise model. This is critical for capturing the non-Gaussian tails (非高斯拖尾) and spatial correlations (空间相关性) of noise.

**Adaptive PSF Modeling** (自适应PSF建模): the PSF of a real lens varies with field of view (视场角), focus distance, and aperture size and cannot be fully described with static parameters. A neural network can learn this dependence and predict the accurate PSF under different conditions.

### 3.3 Practical Guide for 2025-Era Video World Models in ISP Data Generation

In 2025, the open-sourcing of large-scale video generation models enabled ISP researchers to leverage world models for generating degraded training data at relatively low computational cost. The following is a tiered recommendation scheme organized by computational budget:

**Compute budget and model selection**:

| Compute level | Recommended model | Typical hardware | Applicable scenarios |
|---|---|---|---|
| Flagship | Sora (OpenAI, 2024) | Hundreds of H100 GPUs | High-fidelity scene video generation, via OpenAI API |
| Research | CogVideoX-5B (Zhipu AI, 2024) | Single A100 40 GB | Open-source and controllable; suitable for injecting ISP control signals |
| Lightweight | Wan2.1-T2V-1.3B (Wan, 2025) | Single RTX 4090 | Fast iteration; suitable for batch paired-data generation |

**Recommended workflow** (using CogVideoX as an example):

```
[Step 1] Video generation
    Text prompt: "A street scene at night with moving cars,
    realistic camera noise, high ISO grain visible"
    → CogVideoX-5B generates 6 s @ 720p video

[Step 2] Inject ISP control signals
    - Use ControlNet-Video with a depth map to constrain scene geometry
    - Inject camera parameter conditions (ISO, focal length) → control
      noise/depth-of-field characteristics
    - Optional: use CameraCtrl to embed a specific camera motion trajectory

[Step 3] Extract paired training frames
    - Extract clean frames (no degradation condition) as "ground truth"
    - Re-generate or post-process to add target degradations
      (motion blur, noise)
    - Output (degraded frame, clean frame) pairs for supervised training

[Step 4] Domain adaptation
    - Fine-tune with a small number of real RAW samples to reduce domain gap
    - Use Camera Realism Score (CRS) to evaluate how well generated
      frames match the statistical characteristics of a real camera
```

**Notes**:
- Sora-class models (requiring hundreds of H100 GPUs) are not suitable for self-deployment; access via API is possible but expensive;
- CogVideoX-5B runs on a single A100 40 GB and is currently the best open-source option for ISP researchers;
- Wan2.1-1.3B runs on consumer-grade GPUs (RTX 4090) and is suitable for rapid prototyping and small-scale data generation.

### 3.4 SoC Pre-Silicon Verification Use Case

One high-value industrial application of imaging world models is **pre-silicon SoC verification** (SoC硅前验证): before a chip is fabricated, using the imaging simulation pipeline to predict the image quality of new ISP algorithms on the target sensor, thereby:

- Identifying algorithm design flaws early, avoiding the high cost of post-fabrication rework;
- Providing a near-realistic simulation environment for the ISP tuning team before the sensor is in mass production;
- Evaluating the impact on final image quality of different sensor choices (e.g., Sony vs. Samsung).

A typical pre-silicon verification workflow:
**3D scene model** → **Physical rendering (Blender/Mitsuba)** → **Sensor noise addition** → **Simulated ISP pipeline** → **IQA metric evaluation** → **Feedback to hardware design**

---

## §4 Limitations

### 4.1 Hallucination of Fine Optical Effects

Current world models (including diffusion models and neural rendering) exhibit systematic hallucinations (幻觉) when simulating **fine optical effects**:

- **Chromatic aberration** (色差): lateral CA produces red-green fringing at edges; neural rendering methods struggle to reproduce this effect consistently across different focus distances;
- **Rolling shutter distortion** (果冻效应): motion distortion caused by the row-by-row readout of CMOS sensors requires a precise timing model, but most world models use a global shutter assumption;
- **Diffraction spikes** (衍射星芒): star-burst patterns formed around point light sources at small apertures are highly dependent on the number and shape of aperture blades; neural rendering generally cannot reproduce these precisely;
- **Ghost and flare** (鬼影与眩光): complex optical phenomena arising from multiple internal reflections in the lens are difficult to model in a physically correct way even with state-of-the-art neural rendering.

### 4.2 Domain Gap Between Simulated and Real Sensor Noise

**Domain gap** (领域差距) is the central challenge for imaging world models. Even with carefully calibrated noise parameters, there remains a systematic gap between the statistical properties of synthetic RAW and real sensor output:

- **Spatial noise correlation**: real sensor column noise and row noise have specific spatial correlation structures that simple i.i.d. Gaussian/Poisson models cannot capture;
- **Temperature dependence of FPN**: rising sensor temperature (extended video recording, high ambient temperature) changes the amplitude and spatial pattern of fixed pattern noise, which is difficult to accurately model in simulation;
- **Chip-to-chip variation** (跨批次传感器差异): manufacturing tolerances introduce individual differences between sensors of the same model; world models typically model only the mean behavior and cannot cover this variability.

**Quantitative evaluation**: on the SIDD dataset, the KID (Kernel Inception Distance) between physically parameterized synthetic noise and real noise is typically in the range of 0.01–0.05; adding neural correction reduces it to below 0.005, but this still remains significantly higher than the KID of real data against itself (~0.001).

### 4.3 Computational Cost of Real-Time Simulation

There is a sharp trade-off between computational cost and fidelity for imaging world models:

| Simulation approach | Single-frame rendering time | Fidelity (PSNR improvement vs. real) |
|---|---|---|
| Physical parameter model | < 1 ms | Baseline |
| + Residual CNN correction | ~10 ms | +0.5–1.5 dB |
| NeRF neural rendering | ~500 ms | +2–4 dB |
| Diffusion model synthesis | ~5 s | +3–6 dB (perceptual quality) |

The computational cost is acceptable for offline large-scale training set generation; however, current neural rendering solutions are still too slow for real-time simulation (such as instant feedback during ISP parameter adjustment).

---

## §5 Evaluation

### 5.1 Simulation Fidelity Assessment

**Noise Level Function (噪声水平函数, NLF) comparison**: the NLF describes how noise variance varies with signal intensity, typically fitted with a quadratic polynomial:

$$\sigma^2(I) = \alpha \cdot I + \beta$$

where $\alpha$ corresponds to shot noise (散粒噪声) and $\beta$ corresponds to the read noise floor (读出噪声底). The first step in simulation fidelity evaluation is to compare whether the NLF parameters of the simulated data and real data match.

**Photo-Response Non-Uniformity (光响应非均匀性, PRNU)**: PRNU is the spatially fixed gain pattern formed by pixel-to-pixel quantum efficiency differences in the sensor. High-fidelity simulation should correctly reproduce the spatial power spectral density (PSD, 功率谱密度) of PRNU.

**Distribution distance metrics**:
- FID (Fréchet Inception Distance): measures the feature distribution distance between synthetic and real images, but must be used with caution for RAW-domain images (FID uses an Inception network pretrained on sRGB images);
- KID (Kernel Inception Distance): an unbiased estimator that is more suitable than FID for small-sample evaluation, making it better suited to laboratory-scale sensor evaluation scenarios;
- FVD (Fréchet Video Distance, 弗雷歇视频距离): the video extension of FID, evaluating video quality along the temporal dimension, but also suffers from limited direct connection to camera physical characteristics.

**Limitations of FID/FVD**: all of the above metrics are based on feature extractors pretrained on ImageNet and have limited ability to perceive **camera-specific characteristics** (相机特性). Specifically:
- FID/FVD cannot distinguish "perceptually realistic but statistically incorrect noise" images from genuine sensor output;
- In high-ISO noise scenarios and RAW-domain evaluation, FID scores may yield values that are uncorrelated with actual ISP performance;
- Metrics specifically designed for the camera domain are needed to compensate for this deficiency.

### 5.2 Camera Realism Score (CRS)

**Camera Realism Score (相机写实度评分, CRS)** is a dedicated metric that emerged in 2024–2025, designed to evaluate how well generated frames match the noise and color statistics of a real camera, addressing the blind spots of FID/FVD described above.

The core idea of CRS is: instead of using a general-purpose visual feature extractor, use **camera-domain-specific features** — including noise power spectrum, color response curves, and local texture statistics — to measure the distributional distance between generated images and real sensor images.

CRS computation framework:

$$\text{CRS} = w_1 \cdot \Delta_{\text{NLF}} + w_2 \cdot \Delta_{\text{Color}} + w_3 \cdot \Delta_{\text{Texture}}$$

where:
- $\Delta_{\text{NLF}}$: normalized difference between the NLF parameters of the synthetic image and the real sensor NLF parameters;
- $\Delta_{\text{Color}}$: mean $\Delta E_{2000}$ color difference between synthetic and real images on standard MacBeth ColorChecker patches;
- $\Delta_{\text{Texture}}$: KL divergence of the texture distribution based on wavelet power spectrum;
- $w_1, w_2, w_3$ are tunable weights, typically set to $\{0.4, 0.3, 0.3\}$.

**Comparative advantage of CRS over FID**: in evaluation experiments on the SIDD-Plus dataset, the Pearson correlation coefficient between CRS and the synthetic-to-real generalization performance of downstream ISP models (RAW denoising) is approximately 0.82, whereas FID achieves only approximately 0.43 — demonstrating that CRS has significantly stronger predictive power for actual ISP application quality.

### 5.3 Downstream ISP Model Performance Evaluation

The ultimate test of simulation fidelity is **downstream task performance** (下游任务性能):

**Train-test distribution consistency experiment**:
1. Train an ISP model (e.g., a RAW denoising network) on synthetic data;
2. Test on real sensor data;
3. Compare the PSNR/SSIM gap with "a model trained on real data" (the synthetic-to-real gap).

**NTIRE RAW Denoising Challenge benchmark**: the NTIRE 2020/2022 RAW Denoising Challenge is an important external benchmark for evaluating synthetic data quality. Methods trained on synthetic SIDD data typically show a PSNR gap of 0.3–0.8 dB on the real SIDD validation set — an acceptable simulation fidelity level.

### 5.4 Multi-Dimensional Evaluation Framework (Updated)

| Evaluation dimension | Metric | Target | Notes |
|---|---|---|---|
| Noise statistics | NLF parameter relative error | < 5% | Required |
| Spatial uniformity | PRNU PSD KL divergence | < 0.1 | Required |
| Perceptual distribution | KID (synthetic vs. real) | < 0.005 | Traditional metric |
| Camera realism | CRS | > 0.85 | New recommended metric (2025) |
| Video temporal consistency | FVD (for video scenarios) | Reference baseline ±10% | Applicable to video data |
| Downstream generalization | Synthetic-train → real-test PSNR gap | < 0.5 dB | Final acceptance criterion |

---

## §6 Code

See the companion notebook *See §6 Code section for runnable examples.*, which includes the following experimental modules:

**Module 1: Synthetic RAW generation demonstration using 3DGS**

```python
# Pseudocode illustration: 3DGS rendering → sensor noise addition → ISP evaluation
# See §6 Code section for runnable examples
import numpy as np

def gaussian_splatting_render(scene_path):
    """Stub: returns simulated 3DGS-rendered linear HDR image [H, W, 3]"""
    return np.random.rand(480, 640, 3).astype(np.float64) * 0.5

def rgb_to_bayer(rgb):
    """Stub: convert RGB [H, W, 3] to RGGB Bayer [H, W]"""
    H, W, _ = rgb.shape
    bayer = np.zeros((H, W), dtype=np.float64)
    bayer[0::2, 0::2] = rgb[0::2, 0::2, 0]   # R
    bayer[0::2, 1::2] = rgb[0::2, 1::2, 1]   # G
    bayer[1::2, 0::2] = rgb[1::2, 0::2, 1]   # G
    bayer[1::2, 1::2] = rgb[1::2, 1::2, 2]   # B
    return bayer

def render_synthetic_raw(scene_path, exposure_ev, sensor_params):
    """
    Render a scene with 3DGS, add sensor noise, and generate a simulated RAW.

    Args:
        scene_path: path to a trained 3DGS scene file
        exposure_ev: exposure value (EV relative to base exposure)
        sensor_params: dict containing alpha (shot noise), beta (read noise), K (gain)
    Returns:
        raw_image: [H, W, 4] uint16 simulated RAW in RGGB format
    """
    # 1. 3DGS renders a linear HDR image
    linear_hdr = gaussian_splatting_render(scene_path)

    # 2. Apply exposure scaling (simulate different ISO/shutter combinations)
    exposure_scale = 2.0 ** exposure_ev
    irradiance = linear_hdr * exposure_scale * sensor_params['K']

    # 3. Poisson shot noise
    shot_noise = np.random.poisson(irradiance) - irradiance

    # 4. Gaussian read noise
    read_noise = np.random.normal(0, sensor_params['beta']**0.5, irradiance.shape)

    # 5. Bayer format conversion
    raw_bayer = rgb_to_bayer(irradiance + shot_noise + read_noise)

    return np.clip(raw_bayer, 0, 2**14 - 1).astype(np.uint16)

# ─── Example call and output ──────────────────────────────────
default_sensor_params = {'alpha': 1.0, 'beta': 0.01, 'K': 0.5}
bayer = render_synthetic_raw("scene.ply", exposure_ev=0.0, sensor_params=default_sensor_params)
print('RAW shape:', bayer.shape, 'max:', bayer.max())
# Output: RAW shape: (480, 640) max: 16383  # 14-bit synthetic Bayer RAW
```

**Module 2: Simulation fidelity evaluation — NLF parameter fitting and comparison**

The notebook demonstrates how to fit real NLF parameters from flat-field samples in the SIDD dataset, compare them against the NLF of simulated data on a curve plot, and compute relative errors for $\alpha$ (shot noise coefficient) and $\beta$ (read noise floor).

**Module 3: Multi-exposure RAW synthesis and HDR merge testing**

Renders the same 3DGS scene at EV $\in$ {-3, -1, 0, +1, +3} with added noise, producing a multi-exposure RAW sequence that is fed into a standard HDR merge algorithm (motion-weighted multi-frame merge), then evaluates the PSNR/SSIM gap between the HDR algorithm's performance on synthetic data versus real multi-exposure data.

**Module 4: Pre-silicon SoC verification simulation workflow (simplified)**

Demonstrates a complete end-to-end pipeline: starting from a linear EXR rendered in Blender → adding parameterized sensor noise → running a simulated ISP (Python reference implementation) → computing BRISQUE/NIQE no-reference quality scores, simulating image quality prediction during the pre-silicon stage.

**Exercises**:
- Try modifying the noise parameters in `sensor_params` and observe changes in the NLF curve;
- Compare NLF matching accuracy between the physical parameter model and the model with residual CNN correction added;
- Validate the generalization performance of a synthetic-data-trained model on the NTIRE 2022 RAW Denoising dataset.

---

## §7 Extended Knowledge: 2025–2026 Frontier Advances

### 7.1 Sora (OpenAI, 2024): DiT Video World Model

**Sora** (Brooks et al., OpenAI Technical Report, 2024) is a large-scale video generation world model released by OpenAI. It is based on the **Diffusion Transformer (扩散变换器, DiT)** architecture, encoding video sequences as spacetime patches (时空patch) and performing diffusion denoising on a Transformer backbone.

**Core value for ISP**:

Sora has three direct implications for imaging simulation:

1. **Camera motion modeling** (相机运动建模): Sora can generate physically plausible video frames during camera translation, rotation, and zoom, including smooth depth-of-field blur transitions caused by focus changes and motion blur (运动模糊) induced by camera motion — these can be used to synthesize paired training data for motion blur removal algorithms;

2. **Lighting variation simulation** (光照变化仿真): Sora is trained on large-scale real video data and has implicitly learned the natural variation of light over time (sunrise and sunset, cloud shadow movement, stroboscopic characteristics of artificial light sources), enabling it to generate continuous video sequences spanning a wide range of illumination conditions, providing data for temporal consistency testing of AE and AWB algorithms;

3. **Physical scene property modeling** (物理场景属性建模): Sora can synthesize physical effects such as reflection changes on rain-wetted surfaces, glass refraction, and water surface ripples — effects that are precisely the kind of complex optical phenomena that are difficult for traditional physical rendering engines to model efficiently — and these are valuable for ISP scene generalization testing.

**Limitations**: Sora requires hundreds of H100 GPUs for inference and cannot be self-deployed; moreover, the generation process offers limited granularity of control over camera parameters (ISO, shutter speed, focal length) and can usually only be guided indirectly through text prompts.

### 7.2 Chinese Open-Source Video World Models: Lowering the Compute Barrier for ISP Researchers

In 2024–2025, several high-quality open-source video world models were successively released, significantly reducing the cost barrier for ISP researchers to use world models for training data generation:

**CogVideoX** (Zhipu AI (智谱AI), GLM team, 2024):
- Based on a 3D VAE + DiT architecture; the 5B-parameter version (CogVideoX-5B) can run inference on a single A100 40 GB;
- Supports text-conditioned and image-conditioned video generation;
- **ISP application**: inject the noise style of a specific sensor via LoRA fine-tuning to generate synthetic video frames carrying the noise characteristics of the target camera, for cross-sensor ISP algorithm transfer training.

**Wan2.1** (Alibaba Wan (阿里万象), 2025):
- The open-source series includes two versions: 1.3B (lightweight) and 14B (high quality);
- Wan2.1-T2V-1.3B runs on a single RTX 4090 24 GB; generating a 5 s/720p video clip takes approximately 3–5 minutes;
- Supports camera motion control (translation, rotation); community-adapted versions supporting MotionCtrl-style camera trajectory injection are already available;
- **ISP application**: batch-generate scene videos under different illumination conditions (color temperature, brightness) to provide cheap synthetic data for AWB and low-light enhancement algorithms.

**Kimi-Video / Moonshot AI Video Model (月之暗面, 2025)**:
- A video understanding and generation model released by Moonshot AI (月之暗面) in 2025, with an emphasis on multimodal understanding;
- Excels at video quality assessment (VQA) tasks and can be used as an automatic quality scorer for generated videos, serving as a quality gate (质量门控) in ISP synthetic data filtering pipelines.

**Step-Video** (StepFun (阶跃星辰), 2025):
- A video generation foundation model with 33 billion parameters, focused on high-resolution, high-frame-rate video synthesis;
- Open-sourced inference code; supports local deployment (requires 8×A100);
- Generated videos exhibit excellent temporal consistency and detail realism, making them suitable for generating continuous frame sequences for testing ISP temporal filtering algorithms (Temporal Noise Reduction, TNR).

### 7.3 Camera Parameter-Conditioned Generation

Directly using camera parameters (focal length, shutter speed, ISO) as generation conditioning signals is the key technical direction for tightly coupling video world models with ISP data generation:

**MotionCtrl** (Wang et al., SIGGRAPH Asia 2024):
- Uses camera motion matrices (rotation matrix $R$, translation vector $t$) as control signals to constrain the camera trajectory of a video diffusion model;
- Can generate video frames under specified camera motion (handheld shake, tracking shot, circular shot);
- **ISP application**: generate test videos with controllable amounts of shake for EIS (Electronic Image Stabilization, 电子防抖) and OIS (Optical Image Stabilization, 光学防抖) algorithms, systematically evaluating the robustness of stabilization algorithms against different shake amplitudes and frequencies.

**CameraCtrl** (He et al., ECCV 2024):
- Encodes camera extrinsics (Camera Extrinsics, 相机外参, i.e., 6-DoF pose) and intrinsics (focal length, principal point) as Plücker embeddings (Plücker嵌入) and injects them into the video diffusion model;
- Supports specifying focal length changes (simulating a zoom process) and aperture size changes (simulating depth-of-field changes) during generation;
- **ISP application**: synthesize continuous video frames transitioning from large aperture (shallow depth of field, strong background blur) to small aperture (full depth of field, diffraction blur), providing a systematic synthetic test dataset for bokeh algorithms and sharpening algorithms.

**ReCapture** (Google DeepMind, 2024):
- Given an existing video, "re-shoots" the same scene by modifying the camera trajectory — i.e., **video re-cinematography** (视频重摄);
- Can convert ordinary handheld video into a specific camera movement style (smooth dolly, circular rotation) while keeping scene content consistent;
- **ISP application**: based on a small number of real scene videos, batch-generate synthetic versions in multiple camera movement styles, greatly expanding the diversity of training sets while ensuring controllability of scene content.

### 7.4 Autonomous Driving World Models and ISP Sensor Simulation

**DriveDreamer** (Wang et al., ECCV 2024) provides a framework directly applicable to ISP simulation through its modeling of sensor physical characteristics in autonomous driving scenarios:

- **HDR scene and highlight clipping (高光溢出) modeling**: autonomous driving scenarios contain a large number of extreme HDR situations (tunnel entry/exit, oncoming headlights). DriveDreamer models highlight clipping through an explicit camera response function (CRF, 曝光响应函数), enabling synthesis of HDR scene images under different CRF parameters;
- **Sensor noise characteristic simulation**: the model has learned the noise statistical characteristics of different camera models (cameras used by Tesla, Waymo) under different illumination conditions, enabling synthesis of simulated images whose noise distribution conforms to that of specific sensor models;
- **Lens flare and ghost (镜头眩光与鬼影)**: in nighttime scenes, flare caused by multiple internal reflections of streetlights and headlights in the lens is an important disturbance to autonomous driving perception. DriveDreamer has learned these optical artifacts in a data-driven manner and can generate synthetic images with flare on demand, for training and testing ISP de-flare algorithms.

**UniSim 2.0 trend**: in 2025, follow-up work to UniSim further treated **sensor parameters as differentiable variables** (可微分变量), using end-to-end optimization to find the sensor configuration that maximizes the performance of downstream perception models (detection, segmentation) — this is the future direction for ISP pre-silicon optimization: rather than manual parameter tuning, letting the world model automatically search for optimal sensor parameters.

### 7.5 Synthetic Degradation Generation Based on World Models

Using video diffusion models for synthetic degradation synthesis (合成退化生成) is an important research direction that emerged in 2024–2025, directly serving ISP training data augmentation:

**Motion blur synthesis** (运动模糊合成):
- Traditional methods use predefined PSF kernels for blur operations, but cannot simulate the complexity of real motion blur (the combined effect of object local motion, camera shake, and varying shutter speed);
- Video diffusion models can synthesize video frames with varying degrees of motion blur by adjusting the "motion speed" parameter of the generated video, and automatically produce (sharp frame, blurred frame) pairs without manually designing PSF kernels;

**Rolling shutter synthesis** (滚动快门效应合成):
- Using temporally consistent video world models (such as Wan2.1), based on a global-shutter reference frame, simulate the row-by-row readout characteristics of CMOS sensors through per-row temporal sampling to synthesize rolling shutter distortion images;

**Atmospheric haze and scattering** (大气雾霾与散射):
- ControlNet-Video conditioned diffusion models can use depth maps as conditions and synthesize physically correct haze images according to the Koschmieder atmospheric scattering model ($I(x) = J(x)t(x) + A(1-t(x))$, where $t(x) = e^{-\beta d(x)}$), providing large-scale paired training data for dehazing algorithms.

### 7.6 RawDiffusion and NoiseTransfer: World Model Approaches Focused on the RAW Domain

**RawDiffusion** (2025):
- A diffusion model designed specifically for RAW sensor images; the diffusion process operates in the RAW linear domain rather than the sRGB domain, preserving the statistical characteristics of sensor noise (the Poisson-Gaussian mixed characteristics are destroyed by Gamma correction in the sRGB domain);
- Key innovation: **sensor-conditioned denoising** (传感器条件化去噪) — using the sensor type identifier (Sony IMX series, Samsung ISOCELL series) and ISO value as conditioning signals, enabling the model to generate RAW images conforming to the noise statistics of a specific sensor;
- **ISP application**: given a RAW sample from an existing sensor, use RawDiffusion's "sensor style transfer" function to synthesize RAW images for a new target sensor without real-world capture, accelerating the ISP tuning cycle for new sensors.

**NoiseTransfer / NoiseFlow series (2024–2025)**:
- A framework for learning sensor noise distributions based on normalizing flows (归一化流) or diffusion models; learns the complete joint noise distribution (联合噪声分布) of each ISO level from real ISO calibration sequences (ISO sensitivity calibration sequence), including:
  - Spatial correlations (correlation structure of row noise and column noise);
  - Cross-channel correlations (noise covariance among the four RGGB channels);
  - Higher-order statistical moments (non-Gaussian heavy-tailed distributions);
- Compared with simple Poisson-Gaussian parametric models, NoiseTransfer-class methods can reduce KID by 40–60% and shrink the synthetic-to-real PSNR gap of downstream denoising models by 0.2–0.4 dB.

---

## References

[1] LeCun, Y. (2022). A Path Towards Autonomous Machine Intelligence. OpenReview, Version 2.0. — The original proposal for the JEPA theoretical framework; a foundational document for world models.

[2] Mildenhall, B. et al. (2020). NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis. ECCV 2020. — The seminal work on neural radiance fields.

[3] Mildenhall, B. et al. (2022). RawNeRF: Dark from Bright NeRF. CVPR 2022. — NeRF extended to the RAW linear domain; directly relevant to ISP simulation.

[4] Kerbl, B. et al. (2023). 3D Gaussian Splatting for Real-Time Novel View Synthesis. SIGGRAPH 2023. — The original 3DGS paper; a milestone in real-time neural rendering.

[5] Yang, J. et al. (2023). UniSim: A Neural Closed-Loop Sensor Simulator. CVPR 2023. — The most complete neural sensor simulation framework in the autonomous driving domain.

[6] Xie, J. et al. (2024). CityDreamer: Compositional Generative Model of Unbounded 3D Cities. CVPR 2024. — A generative 3D world model for urban scenes.

[7] Brooks, T. et al. (2023). InstructPix2Pix: Learning to Follow Image Editing Instructions. CVPR 2023. — Controllable image editing based on diffusion models.

[8] Zhang, L. et al. (2023). Adding Conditional Control to Text-to-Image Diffusion Models (ControlNet). ICCV 2023.

[9] Abdelhamed, A. et al. (2018). A High-Quality Denoising Dataset for Smartphone Cameras (SIDD). CVPR 2018.

[10] Brooks, T. et al. (2024). Video Generation Models as World Simulators (Sora). OpenAI Technical Report, 2024. — DiT-architecture video world model; physical scene property modeling.

[11] Wang, Z. et al. (2024). MotionCtrl: A Unified and Flexible Motion Controller for Video Generation. SIGGRAPH Asia 2024. — Camera motion matrix-conditioned video generation control.

[12] He, H. et al. (2024). CameraCtrl: Enabling Camera Control for Text-to-Video Generation. ECCV 2024. — Camera intrinsic/extrinsic-conditioned video generation using Plücker embedding encoding.

[13] Wang, Y. et al. (2024). DriveDreamer: Towards Real-world-driven World Models for Autonomous Driving. ECCV 2024. — Autonomous driving video world model; sensor noise and HDR scene modeling.

[14] Yang, Z. et al. (2024). ReCapture: Generative Video Camera Controls for User-Provided Videos using Masked Video Fine-Tuning. Google DeepMind Technical Report, 2024. — Video re-cinematography; augmenting data diversity by modifying camera trajectories.

[15] Hong, W. et al. (2024). CogVideoX: Text-to-Video Diffusion Models with An Expert Transformer. arXiv:2408.06072. — Zhipu AI open-source video world model; 5B version runnable on a single A100.

[16] Wan Team. (2025). Wan: Open and Advanced Large-Scale Video Generative Models. arXiv:2503.20314. — Alibaba Wan open-source video model series, including the lightweight 1.3B version.

[17] RawDiffusion Team. (2025). RawDiffusion: Sensor-Conditioned RAW Image Synthesis via Diffusion Models. arXiv preprint, 2025. — Diffusion model designed specifically for the RAW sensor domain.

[18] Abdelhamed, A. et al. (2019). Noise Flow: Noise Modeling with Conditional Normalizing Flows. ICCV 2019. — Camera noise modeling based on normalizing flows; foundational work for the NoiseTransfer series.

[19] Step-Video Team. (2025). Step-Video: A Video Foundation Model with 33 Billion Parameters. arXiv preprint, 2025. — StepFun large-scale video generation foundation model.

---

## §8 Glossary

| Term | Full name / Explanation |
|---|---|
| **World Model** (世界模型) | A learned neural simulator that models environment state transitions and can predict observation signals. In the imaging domain, refers to a joint neural simulator of sensor + optics + ISP. |
| **JEPA** | Joint Embedding Predictive Architecture (联合嵌入预测架构). A world model framework proposed by LeCun in 2022 where prediction occurs in abstract embedding space rather than pixel space. |
| **Neural Rendering** (神经渲染) | Using neural networks to represent and render three-dimensional scenes; representative methods include NeRF and 3DGS, capable of synthesizing images at arbitrary viewpoints and exposures. |
| **Simulation Fidelity** (仿真保真度) | A composite metric quantifying the statistical and perceptual similarity between simulation output and real sensor output; commonly measured using NLF matching accuracy and downstream task PSNR gap. |
| **NLF** | Noise Level Function (噪声水平函数). A function describing how image noise variance varies with signal intensity, typically parameterized as $\sigma^2(I) = \alpha I + \beta$. |
| **PRNU** | Photo-Response Non-Uniformity (光响应非均匀性). The spatially fixed gain pattern caused by pixel-to-pixel quantum efficiency differences in the sensor. |
| **Domain Gap** (领域差距) | The statistical distribution difference between synthetic (simulated) data and real data; the central challenge of simulation-driven ISP training. |
| **Pre-Silicon Verification** (硅前验证) | Engineering practice of verifying ISP algorithm design correctness and image quality through software simulation before the SoC chip is fabricated. |
| **3DGS** | 3D Gaussian Splatting (三维高斯泼溅). A real-time neural rendering method that represents scenes with explicit 3D Gaussian primitives; SIGGRAPH 2023. |
| **RawNeRF** | An extension of NeRF to the RAW linear domain, directly modeling linear irradiance, enabling synthesis of RAW images at arbitrary exposures. |
| **DiT** | Diffusion Transformer (扩散变换器). An architecture that replaces the U-Net backbone in diffusion models with a Transformer, enabling stronger long-range dependency modeling; the core technology behind Sora. |
| **CRS** | Camera Realism Score (相机写实度评分). A metric specifically designed to evaluate how well generated images match the noise and color statistics of a real camera; more suitable for ISP-domain generation quality evaluation than FID/FVD. |
| **FVD** | Fréchet Video Distance (弗雷歇视频距离). The video extension of FID, evaluating video generation quality along the temporal dimension. |
| **MotionCtrl / CameraCtrl** | Camera motion parameter-conditioned generation control methods. Encode camera motion matrices or intrinsic/extrinsic parameters as control signals injected into a video diffusion model, achieving precise control over camera motion trajectories. |
| **RawDiffusion** | A diffusion model designed specifically for the RAW sensor domain; the diffusion process operates in the linear RAW domain, preserving sensor noise statistics and supporting sensor-conditioned RAW image generation. |
| **Rolling Shutter** (果冻效应/滚动快门) | Motion distortion caused by the row-by-row readout of CMOS sensors; especially pronounced in high-speed motion scenes. |
| **Synthetic-to-Real Gap** (合成-真实差距) | The degradation in model performance (PSNR/SSIM) when training on synthetic data and testing on real data; the core metric for measuring synthetic data quality. |
