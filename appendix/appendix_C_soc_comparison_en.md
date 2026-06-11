# Appendix C — ISP SoC Comparison (Generic / Public Version) | SoC对比（通用公开版）

> **Public version.** This appendix describes generic ISP SoC categories using non-vendor-specific terminology.
> For vendor-specific pipeline details, register-level configurations, and tuning parameter ranges,
> see the private documentation (`private-repo/vendor_details/`).

---

## C.1 ISP SoC Categories

Modern ISP implementations span a wide range of silicon platforms. They can be broadly categorized by application domain and performance tier:

| Category | Typical Context | Power Envelope | Key Differentiator |
|----------|----------------|---------------|-------------------|
| Mobile SoC Tier 1 | Flagship smartphone | 1–5 W (ISP block) | Multi-camera fusion, AI acceleration, high frame rate HDR |
| Mobile SoC Tier 2 | Mid-range smartphone | 0.5–2 W | Balanced pipeline, moderate AI, cost-optimized |
| Automotive ISP | ADAS, surround-view | 5–20 W | Functional safety (ISO 26262), wide temperature, lane/pedestrian detection pipeline |
| Industrial Camera ISP | Machine vision, inspection | Varies widely | High precision, deterministic pipeline, multi-spectral support |
| Standalone ISP Chip | Compact camera, action cam | 1–10 W | Dedicated silicon, deep tuning access |
| FPGA ISP | Prototyping, low-volume | Flexible | Reconfigurable pipeline, research use |
| Software ISP | PC, cloud processing | CPU/GPU | Maximum flexibility, no hardware constraints |

---

## C.2 Mobile SoC Tier 1 (Flagship)

### Pipeline Capabilities

A typical flagship mobile ISP supports the following pipeline stages in hardware:

```
RAW input
  → BLC (Black Level Correction, per-channel, temperature-compensated)
  → PDPC (Phase Detection Defect Pixel Correction)
  → LSC (Lens Shading Correction, full-field polynomial or mesh)
  → Demosaic (directional/frequency-based, sub-pixel accuracy)
  → Denoise (multi-frame NR: temporal + spatial, often AI-assisted)
  → Sharpening / Edge Enhancement (adaptive, MTF-aware)
  → AWB (gray world + statistical scene prior + AI classification)
  → CCM (3×3 or 3×3+3 affine, illuminant-dependent interpolation)
  → Gamma / Tone Mapping (HDR: multi-segment curve or LUT-based)
  → CSC (RGB to YUV, multiple standard outputs)
  → Output (4K/8K video, burst HDR, computational photography)
```

### Compute Capabilities

- Dedicated ISP hardware accelerators (Giga-operations per second class)
- On-chip NPU (Neural Processing Unit) for AI-assisted modules
- Multi-camera support: typically 3–5 simultaneous camera inputs
- High frame rate: 60–240 fps at 4K with real-time processing
- Multi-frame HDR: 3–9 frame fusion with motion detection

### Key Features (Generic)

- **AI denoise:** Deep learning denoise running on NPU, replacing or augmenting traditional bilateral/BM3D
- **Semantic AWB:** Scene classification to handle challenging illuminants (candlelight, neon, mixed lighting)
- **Computational zoom:** Multi-camera fusion for continuous optical/digital zoom
- **Real-time portrait:** Depth map generation for bokeh rendering
- **Night mode:** Multi-frame alignment + denoise stack (10–30 frames)

### Tuning Complexity

Flagship mobile ISPs typically expose 500–2000+ tuning parameters organized by:
- Per-module (BLC, LSC, CCM, etc.)
- Per-ISO (typically 6–12 ISO points)
- Per-illuminant (D65, TL84, A, etc.)
- Per-scene mode (auto, portrait, night, video)

> For vendor-specific parameter names, register addresses, and recommended tuning ranges,
> see `the vendor-specific private documentation`.

---

## C.3 Mobile SoC Tier 2 (Mid-Range)

### Pipeline Capabilities

Mid-range ISPs cover the essential pipeline with reduced hardware parallelism:

```
BLC → LSC → Demosaic → Denoise → Sharpening → AWB → CCM → Gamma/TM → CSC
```

Notable differences from Tier 1:
- Denoise: typically spatial-only NR (no temporal multi-frame in hardware)
- HDR: limited to 2-frame merge or digital WDR (no 3-frame+)
- AI: limited or no on-chip NPU; AI features may run on main CPU/GPU instead
- Frame rate: typically 30–60 fps at 4K

### Tuning Complexity

Moderate: 200–600 tuning parameters. Fewer interpolation dimensions (typically 4–6 ISO points, 3 illuminants).

---

## C.4 Automotive ISP

### Use Case Requirements

Automotive ISP has fundamentally different requirements from mobile:

| Requirement | Mobile | Automotive |
|-------------|--------|-----------|
| Safety standard | None | ISO 26262 ASIL-B/D |
| Temperature range | 0–40°C | -40°C to +85°C |
| Latency | Flexible | Hard real-time (pipeline latency ≤ 1 frame) |
| Dynamic range | 12–14 stops | 120–140 dB (HDR for day→tunnel transitions) |
| Primary output consumer | Human viewer | Computer vision (detection, segmentation) |
| Night vision | Multi-frame stack | Single-frame HDR, NIR support |
| Distortion | Uncorrected acceptable | Must correct for surround-view stitching |

### Pipeline Features

- **High-DR HDR:** Multi-exposure or companding-based WDR with 120+ dB coverage
- **ISP-integrated CV pre-processing:** Some automotive ISPs output pre-processed feature maps alongside or instead of RGB
- **Lens distortion correction:** Fisheye correction for surround-view cameras
- **Deterministic processing:** No frame drops, no quality variation between frames
- **Redundant processing:** Lockstep ISP cores for safety-critical applications

### Typical compute profile

- Power: 5–20 W per ISP block (significantly higher than mobile due to wide-area sensors)
- Multi-camera: 4–12 camera inputs (full surround-view)
- Standards: MIPI CSI-2, FPD-Link, GMSL interfaces

---

## C.5 Industrial Camera ISP

### Characteristics

Industrial machine vision requires:
- **Deterministic exposure control:** Microsecond-accurate trigger and exposure for moving parts inspection
- **High precision color:** Minimal color error for paint defect detection, medical imaging
- **Multi-spectral:** Some systems operate in NIR, UV, or hyperspectral bands
- **Non-standard CFA:** Some industrial sensors use RGGB, RGGB-IR, or monochrome
- **Raw throughput:** Many industrial systems prefer to stream raw data to host PC for offline processing

### Pipeline Philosophy

Unlike mobile ISP, many industrial cameras prefer **minimal in-camera ISP** — perform only essential corrections (BLC, PDPC) and stream RAW or minimally processed data to the host. Full ISP runs in software (e.g., HALCON, OpenCV, proprietary SDK).

---

## C.6 Standalone ISP Chip

### Use Cases
- Action cameras, compact cameras, dashcams, drones
- Use case where application SoC does not include sufficient ISP hardware
- Development kits for camera algorithm prototyping

### Characteristics
- Full ISP pipeline in dedicated silicon
- Deep tuning access via I2C/SPI register interface
- Often paired with a separate application processor
- Power: 1–10 W depending on resolution and feature set

---

## C.7 Software ISP

### Use Cases
- RAW processing on PC (Adobe Lightroom, darktable, RawTherapee)
- Cloud-side photo enhancement
- Algorithm research and prototyping

### Characteristics
- Maximum flexibility — all parameters accessible
- No real-time constraints
- GPU acceleration available for DL modules
- Open-source implementations available (see Appendix D)

---

## C.8 ISP Feature Matrix (Generic)

| Feature | Tier 1 Mobile | Tier 2 Mobile | Automotive | Industrial |
|---------|:---:|:---:|:---:|:---:|
| BLC + PDPC | ✅ | ✅ | ✅ | ✅ |
| LSC (full polynomial) | ✅ | ✅ | ✅ | Varies |
| Directional demosaic | ✅ | ✅ | ✅ | ✅ |
| Multi-frame temporal NR | ✅ | Limited | Varies | No |
| AI denoise (NPU) | ✅ | Limited | Emerging | No |
| 3-frame+ HDR merge | ✅ | Limited | ✅ (companding) | No |
| Semantic AWB | ✅ | No | No | No |
| Computational zoom | ✅ | Limited | No | No |
| Fisheye distortion correction | Limited | No | ✅ | Varies |
| ISO 26262 safety cert | No | No | Required | No |
| Raw streaming (bypass) | Partial | Partial | No | ✅ |

---

## C.9 Tuning Workflow Comparison (Generic)

### Mobile ISP Tuning Workflow (Generic)
```
1. Factory calibration: BLC, LSC, CCM per unit (unit variation calibration)
2. Mass calibration: Per SKU CCM + AWB gains at production line
3. Algo tuning: Per scene mode (auto/night/portrait) parameter adjustment
4. Validation: IQA metrics (MTF50, ΔE, SNR, PSNR/SSIM)
5. OTA update: Post-release parameter refinement
```

### Automotive ISP Tuning Workflow (Generic)
```
1. Sensor characterization: Full temperature sweep for BLC/noise
2. Optics calibration: Per lens unit LSC + geometric distortion
3. HDR calibration: Exposure ratio and response curve alignment
4. CV-metric tuning: Optimize for detection accuracy, not human IQA
5. Safety validation: Determinism and worst-case analysis
```

---

## C.10 Flagship Mobile Platform Deep Dive

This section provides platform-specific analysis of the three dominant flagship mobile ISP architectures: Qualcomm Snapdragon Spectra, HiSilicon Kirin ISP, and MediaTek Imagiq ISP.

---

### C.10.1 Qualcomm Spectra ISP

#### Overview

The Qualcomm Spectra ISP is the dedicated imaging subsystem of Snapdragon SoCs. Starting with the Snapdragon 888, Qualcomm introduced a **Triple ISP architecture** capable of processing three independent camera data streams simultaneously, enabling concurrent 4K video recording from three cameras.

**Generation Roadmap:**

| Generation | Snapdragon SoC | Key Advancement |
|------------|---------------|----------------|
| Spectra 480 | Snapdragon 865 | Dual ISP, 2 Gpixel/s, first-generation AI-ISP |
| Spectra 580 | Snapdragon 888 | **Triple ISP parallel**, 2.7 Gpixel/s, 30-frame MFNR night mode |
| Spectra (8 Gen1) | Snapdragon 8 Gen1 | **18-bit internal precision**, real-time HDR10+ capture |
| Spectra (8 Gen2) | Snapdragon 8 Gen2 | Upgraded AI multi-frame denoise, semantic-aware HDR |
| Spectra (8 Gen3) | Snapdragon 8 Gen3 | Generative AI integration, real-time 4K HDR10+ at 60 fps |

**Bayer Processing Subsystem (BPS)**

The BPS is a dedicated hardware accelerator that operates independently from the main ISP cores. It handles RAW-domain preprocessing tasks:
- Black Level Correction (BLC)
- Lens Shading Correction (LSC)
- Phase Detection Defect Pixel Correction (PDPC)
- Spatial Bayer-domain noise reduction

The BPS runs concurrently with the main ISP pipeline, delivering pre-processed Bayer data downstream and offloading the main ISP cores, improving overall throughput and power efficiency.

**18-bit Internal Precision (since 8 Gen1)**

The internal data path uses 18-bit fixed-point arithmetic (versus the 14-bit common in earlier designs). This wider precision suppresses quantization noise and tonal banding artifacts during operations that involve large-range manipulations such as HDR exposure fusion and local tone mapping.

#### Tuning Toolchain

Qualcomm uses the **Chromatix XML parameter file** system as the ISP tuning data carrier, paired with the **Camera Tuning Tool (CTT)** graphical interface.

**Chromatix Parameter Dimensions:**
```
Parameter Space = Module × ISO Step × Illuminant × Scene Mode
```

**Primary Chromatix modules:**
- `aec_algo_params`: Auto Exposure Control algorithm parameters
- `awb_algo_params`: Auto White Balance algorithm parameters
- `blc_params`: Black Level Correction parameters
- `lsc_params`: Lens Shading Correction mesh grid
- `hdr_params`: HDR merge curves and blending weights
- `raw_nr_params`: RAW-domain noise reduction strength
- `demosaic_params`: Directional demosaic interpolation weights
- `ccm_params`: Color Correction Matrix per illuminant
- `sharpening_params`: Sharpening strength and frequency-band weights
- `ltm_params`: Local Tone Mapping parameters
- `gamma_params`: Global gamma curve LUT

**ISO dimension:** Typically 8–12 ISO points (e.g., ISO 100 / 200 / 400 / 800 / 1600 / 3200 / 6400 / 12800).

**Illuminant dimension:** Four standard illuminants — Illuminant A (2856 K, incandescent), TL84 (4000 K, cool fluorescent), CWF (4150 K, cool white fluorescent), D65 (6504 K, daylight).

**Scene mode dimension:** Auto, Portrait, Night, Video, Super Slow Motion, and others.

At runtime, the ISP performs bilinear or trilinear interpolation across the ISO and illuminant dimensions to produce smoothly varying parameters. The CTT tool provides a live-preview tuning interface that allows writing modified parameters directly back to the Chromatix XML during a camera session.

#### Key Algorithms

**1. AI-ISP via Hexagon NPU**

The Snapdragon Hexagon DSP incorporates NPU capabilities that power AI-ISP modules:

- **Semantic Scene Classification:** The NPU classifies scenes in real time (outdoor / indoor / night / backlit / etc.) and feeds results back into the 3A control loop (AEC, AWB, AF). This enables scene-aware exposure metering — for example, detecting high-contrast backlit scenes before the ISP saturates highlights.
- **AI-assisted AWB:** In challenging mixed or low-color-temperature lighting (candlelight, neon signs), the NPU infers an illuminant probability distribution to correct the bias of conventional gray-world algorithms.

**2. Multi-Frame Noise Reduction (MFNR)**

Spectra 580 (Snapdragon 888) and later support 30-frame RAW MFNR for night mode:
- 30 consecutive RAW frames are captured in burst
- A hardware optical flow engine performs sub-pixel inter-frame alignment
- Weighted temporal averaging stacks the aligned frames; the theoretical SNR gain upper bound is approximately $10\log_{10}(N)$ dB (N = number of frames)
- The merged high-SNR RAW frame then passes through the complete ISP pipeline

**3. Staggered HDR**

Staggered HDR implements multi-exposure at the **sensor level**: within a single frame, different rows are read out with different exposure times (interleaved row readout). Compared to frame-sequential HDR (where a short-exposure frame and a long-exposure frame are separated in time):
- **Ghost artifact elimination:** The displacement of fast-moving subjects between the two exposure paths approaches zero, since both exposures occur within the same frame period
- **Reduced system latency:** No waiting for a complete separate short-exposure frame

**4. Real-time Semantic HDR (since 8 Gen2)**

Building on global tone mapping, semantic segmentation maps (sky / face / foliage / etc.) are used to apply per-class local tone mapping curves, preventing simultaneous sky overexposure and shadow underexposure that global operators cannot resolve.

#### References

- Qualcomm Snapdragon 8 Gen3 product page: https://www.qualcomm.com/products/mobile/snapdragon/smartphones/snapdragon-8-series-mobile-platforms/snapdragon-8-gen-3-mobile-platform
- Qualcomm developer documentation (Camera): https://developer.qualcomm.com/docs/camera/
- Qualcomm developer portal (Spectra whitepapers, registration required): https://developer.qualcomm.com/

#### Qualcomm Official Public Resources

##### Open-Source Code

- **CAMX Camera eXtension Framework**
  https://github.com/quic/camx
  Official Qualcomm GitHub, BSD-3 open-source license, complete camera pipeline node implementation

- **CHI-CDK (Camera Hardware Interface Component Development Kit)**
  https://github.com/quic/chi-cdk
  Chromatix XML schema definitions and parameter structures, official Qualcomm open source

- **Camera Kernel Driver (CodeLinaro)**
  https://git.codelinaro.org/clo/la/platform/vendor/opensource/camera-kernel
  Qualcomm camera kernel driver, hosted by Linux Foundation

- **QCamera HAL (AOSP Mirror)**
  https://android.googlesource.com/platform/hardware/qcom/camera/
  Qualcomm camera HAL code mirrored on AOSP, authoritative reference

##### Official Technical Documents

- **Qualcomm Spectra ISP Technical Overview**
  https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/qualcomm-spectra-isp.pdf

- **Chromatix SDK Developer Page**
  https://developer.qualcomm.com/software/chromatix
  *(requires free QDN account registration)*

- **Camera Developer Tools Overview**
  https://developer.qualcomm.com/software/camera-developer-tools

- **Snapdragon 8 Gen 3 Imaging Technology Page**
  https://www.qualcomm.com/products/mobile/snapdragon/smartphones/snapdragon-8-series/snapdragon-8-gen-3-mobile-platform

---

### C.10.2 HiSilicon Kirin ISP

#### Overview

The HiSilicon Kirin ISP is the proprietary imaging engine of Huawei's flagship smartphones, co-evolving with the Kirin SoC generations.

**ISP Generation Roadmap:**

| Generation | Kirin SoC | Key Advancement |
|------------|-----------|----------------|
| ISP 3.0 | Kirin 960 | Dual ISP, early NPU-assisted denoise |
| ISP 4.0 | Kirin 970 | NPU-aided NR, first mobile AI chip |
| ISP 5.0 | **Kirin 980** | **Industry-first AI-ISP**, dual ISP + deep NPU integration |
| ISP 5.0+ | **Kirin 990 5G** | **Industry-first Triple ISP** (2019), 2.4 Gpixel/s combined |
| ISP 6.0 | Kirin 9000 | XD-Fusion Pro, per-class semantic NR, 4K HDR video |

**Triple ISP (Kirin 990 5G, 2019)**

The Kirin 990 5G was the industry's first mobile SoC with a Triple ISP (debuting in 2019, concurrent with MediaTek's Dimensity 1000). The three ISP cores combine for 2.4 Gpixel/s throughput, enabling simultaneous processing of three camera streams, high-resolution burst capture, and MFNR stacking while wide-angle and telephoto cameras remain active.

#### RYYB Color Filter Array

Flagship Kirin SoCs (from Mate 30 Pro onward) pair with sensors using a non-standard **RYYB (Red-Yellow-Yellow-Blue) Color Filter Array (CFA)** in place of conventional RGGB:

- Yellow (Y) filter transmittance is approximately 2× that of a green filter, because yellow passes both red and green wavelengths (Y = R + G). This substantially raises the sensor's photon collection per pixel in low light.
- Equivalent light intake can be approximately 40% higher than a same-size RGGB sensor under identical exposure conditions.
- **Trade-off:** The Y channel captures a mixture of red and green light. A pure green signal cannot be extracted directly. Demosaicing RYYB requires **AI-assisted G-channel reconstruction from Y** (approximating $G \approx Y - R$, where R is an interpolated red component). This is algorithmically more complex than standard Bayer demosaic and necessitates NPU inference to correct residual color errors.

#### Tuning Toolchain

The Kirin ISP tuning tool is **HiTuning Tool**, an internal instrument not publicly released. Access is restricted to Huawei-authorized ODM partners and camera tuning contractors.

**Calibration procedure (generic description):**
1. **ColorChecker calibration:** Multi-illuminant shots with an X-Rite ColorChecker chart to build illuminant-dependent CCMs
2. **ISO-12233 resolution chart:** MTF50 measurement to inform sharpening parameter curves
3. **Flat-field calibration:** Uniform illuminated field shots to extract the LSC mesh (vignetting correction)
4. **Noise model characterization:** Dark-frame shots to fit a per-ISO sensor noise model (Poisson + Gaussian mixture)

Because the tool is non-public, third-party developers cannot directly access Kirin ISP bottom-level parameters.

#### Key Algorithms

**1. XD-Fusion Pro (eXtreme Definition Fusion)**

XD-Fusion Pro is the unified computational photography orchestration framework introduced in Kirin 9000. It coordinates ISP, NPU, CPU, and GPU as a heterogeneous compute pipeline:

- **Per-class semantic NR:** The NPU performs per-pixel semantic segmentation (sky / skin / foliage / architecture / etc.) and applies class-differentiated noise reduction:
  - Skin regions: soft NR preserving pore-level micro-texture
  - Sky regions: aggressive NR eliminating chroma noise
  - Foliage regions: directional NR preserving leaf-edge texture
- **4× AI super-resolution:** NPU-based SR reconstruction for computational zoom and photo upscaling
- **Multi-camera fusion:** Wide-angle and telephoto pixel-level registration and blending

**2. Multi-Frame Noise Reduction (MFNR)**

Kirin ISP MFNR pipeline:
- 4–8 consecutive RAW frames captured in burst
- Hardware optical flow engine performs sub-pixel inter-frame alignment
- Weighted temporal averaging: more recent frames carry higher weight; motion-region weights are suppressed to prevent ghosting
- Merged high-SNR RAW passes through the complete ISP pipeline for final output

**3. HDR Solution Portfolio**

Kirin ISP supports three HDR capture methods, selected dynamically by scene:

- **ZHDR (Zero-delay HDR):** Sensor-level alternating-row readout — adjacent rows use different exposure times within a single frame. No inter-frame time gap; eliminates motion ghost artifacts entirely. Best for fast-moving subjects.
- **LS-HDR (Long-Short frame HDR):** Traditional two-frame HDR — one long-exposure frame captures shadows, one short-exposure frame captures highlights. Subject motion between frames can introduce ghosting artifacts.
- **Staggered HDR:** Similar to ZHDR, a sensor-level multi-exposure scheme with interleaved readout, maximizing within-frame dynamic range.

#### References

- Huawei Kirin 9000 official product page: https://consumer.huawei.com/en/campaign/kirin9000/
- AnandTech Kirin 980 in-depth analysis (Huawei Mate 20 Pro review): https://www.anandtech.com/show/13371/huawei-mate-20-mate-20-pro-review/4
- Linux kernel HiSilicon ISP driver (open-source reference): https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/media/platform/hisilicon

### HiSilicon Kirin Public Resources

**OpenHarmony Open Source (Gitee)**
- Camera HAL driver code: https://gitee.com/openharmony/drivers_peripheral_camera
  Official OpenHarmony repo; camera pipeline, buffer management, ISP control interface

- HiSilicon SoC device code: https://gitee.com/openharmony/device_soc_hisilicon
  Sensor driver stubs and ISP initialization configuration

**Patent Databases (richest public technical source)**
- Google Patents — HiSilicon ISP patents: https://patents.google.com/?assignee=HiSilicon+Technologies&q=ISP
  Covers AWB, AE, denoising, HDR tone mapping, XD-Fusion multi-frame fusion algorithms

- CNIPA (China National IP Administration): https://pss-system.cponline.cnipa.gov.cn/
  Search: applicant="海思半导体有限公司", IPC=G06T5 or H04N23

**Huawei Official Technical Resources**
- HuaweiTech technical journal (engineer-authored): https://www.huawei.com/en/huaweitech
  Articles on Kirin ISP architecture, computational photography, AI-ISP

- HarmonyOS Camera API documentation: https://developer.huawei.com/consumer/en/doc/harmonyos-guides/camera-overview
  Application-level camera API, shows ISP control interface exposed to OS

**Linux Kernel Drivers**
- kernel.org HiSilicon media drivers (set-top-box SoCs): https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/media/platform/hisilicon
  Note: mainline Linux includes HiSilicon STB ISP drivers; Kirin mobile ISP is not open-sourced

- Linux kernel mailing list — HiSilicon patches: https://lore.kernel.org/linux-media/?q=hisilicon

---

### C.10.3 MediaTek Imagiq ISP

#### Overview

MediaTek Imagiq is the imaging engine of the Dimensity SoC series. It has evolved steadily from Imagiq 2.0 to flagship-tier Imagiq 1090, competing directly with Qualcomm and HiSilicon at the high end.

**Imagiq Generation Roadmap:**

| Generation | Dimensity / Platform | Key Advancement |
|------------|---------------------|----------------|
| Imagiq 2.0 | Helio P70 | Dual ISP, early AI-NR integration |
| Imagiq 5.0 | **Dimensity 1000** | **Triple ISP** (2019), AI-NR, 4K HDR |
| Imagiq 790 | **Dimensity 9000** | 320 MP sensor support, HDR-Vivid first mobile SoC |
| Imagiq 890 | **Dimensity 9200** | Dolby Vision real-time capture, 900 Mpixel/s (3-ISP combined) |
| Imagiq 990 | **Dimensity 9300** | 4K 120 fps HDR video, real-time AI super-resolution |
| Imagiq 1090 | **Dimensity 9400** | Generative AI integration into the imaging pipeline |

**Triple ISP (Dimensity 1000, 2019)**

MediaTek introduced Triple ISP on the Dimensity 1000, concurrent with the HiSilicon Kirin 990 5G in 2019. The Dimensity 9200 (Imagiq 890) achieves a combined throughput of 900 Mpixel/s across its three ISP cores.

#### Tuning Toolchain

MediaTek's ISP tuning tool is the **MTK Camera Tuning Tool (APMCT, APM Camera Tuning)**, distributed under NDA to authorized OEM and ODM partners.

**NVRAM XML parameter files:** Similar in concept to Qualcomm's Chromatix, MediaTek stores ISP tuning parameters in NVRAM XML files organized by module and dimension. These files are flashed to the device's NVRAM partition during production calibration and can be updated via OTA.

**Partial open-source resources:**
- MediaTek contributes portions of its Camera HAL to AOSP
- Dimensity platform Linux kernel camera drivers are available on kernel.org
- MTK Camera HAL3 reference: https://android.googlesource.com/

**Calibration procedure:**
1. **ColorChecker calibration:** Multi-illuminant CCM construction
2. **Flat-field calibration:** LSC mesh extraction from uniform illuminated shots
3. **Noise model characterization:** Dark-frame noise curve fitting (Poisson + readout noise)
4. **MTF measurement:** ISO-12233 resolution chart; sharpening parameters are tied to measured MTF response

#### Key Algorithms

**1. AI Processing Engine (APE)**

Imagiq AI modules run on the **APU (AI Processing Unit)** embedded in Dimensity SoCs:

- **AI-NR (AI Noise Reduction):** An end-to-end denoising network architecturally similar to ESRGAN (Enhanced Super-Resolution GAN) operates on the APU for real-time inference. It performs blind denoising on RAW or YUV data, typically outperforming classical temporal NR on single-frame or short-burst inputs.
- **AI-SR (AI Super-Resolution):** A deep-learning SR network reconstructs high-resolution detail for computational zoom digital upscaling, yielding substantially better texture fidelity than bicubic interpolation.
- **Semantic segmentation:** The NPU infers a per-pixel semantic map (sky / skin / architecture / vegetation) used for:
  - Region-adaptive noise reduction strength
  - Per-class tone mapping curve application
  - Real-time bokeh portrait segmentation

**2. Dual Camera Image Fusion (DCIF)**

DCIF is a hardware-level multi-camera fusion module:
- Performs **hardware pixel registration** between wide-angle and telephoto camera inputs
- Disparity estimation and fusion execute entirely in ISP hardware without requiring the application processor
- Use cases: computational zoom (wide-angle supplementing telephoto detail), night-scene multi-camera fusion (wide-angle high ISO improves SNR, telephoto preserves spatial detail)

**3. HDR-Vivid and Dolby Vision**

- **HDR-Vivid (Dimensity 9000, Imagiq 790 — first mobile SoC):** HDR-Vivid is the Chinese national HDR standard (defined by the UHD Alliance of China). Imagiq 790 was the first mobile SoC to support HDR-Vivid format in real-time in-camera capture.
- **Dolby Vision (from Dimensity 9200):** Imagiq 890 adds hardware Dolby Vision real-time capture. Per-frame dynamic metadata is generated within the ISP pipeline, and the output conforms to Dolby Vision specifications (HDR10+ enhanced stream with frame-level metadata).

**4. Dimensity Open Resource Architecture (ORA, 2023)**

MediaTek's ORA initiative allows OEM manufacturers to inject custom algorithms at the HAL layer:
- OEMs can bypass MediaTek's default ISP algorithm blocks and insert proprietary AI denoise, color processing, or tone mapping modules
- The interface is exposed as standard Camera HAL3 extension plugins, requiring no kernel driver modifications
- Manufacturers such as Xiaomi and OPPO have deployed proprietary ISP algorithms (e.g., Xiaomi MIUI ISP pipeline) using this mechanism

#### References

- MediaTek Imagiq technology overview: https://www.mediatek.com/technology/imagiq
- Dimensity 9200 product page: https://i.mediatek.com/dimensity-9200
- Imagiq 790 press release: https://corp.mediatek.com/news-events/press-releases/mediatek-imagiq-790-brings-flagship-camera-innovations-to-premium-5g-smartphones

### MediaTek Public Resources

**Official Product and Technology Pages**
- MediaTek Imagiq ISP technology overview: https://www.mediatek.com/technology/imagiq
- Dimensity 9000 product page (Imagiq 790 ISP specs): https://www.mediatek.com/products/smartphones-2/dimensity-9000
- MediaTek corporate press releases: https://corp.mediatek.com/news-events/press-releases/
- Dimensity 9200 launch (Imagiq 890 / Dolby Vision): https://corp.mediatek.com/news-events/press-releases/mediatek-launches-dimensity-9200

**Academic and Technical Conferences**
- **Hot Chips 34 (2022)** — MediaTek engineers presented Dimensity 9000 chip architecture (including Imagiq ISP); highest-depth public technical document: https://hotchips.org/archives/hc34/

**Open-Source Kernel Drivers**
- Linux kernel MediaTek ISP driver (mainline): https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/media/platform/mediatek
- MediaTek kernel patch submissions (includes ISP design rationale): https://patchwork.kernel.org/project/linux-mediatek/list/
- V4L2 kernel interface documentation: https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/v4l2.html

**Android Camera Framework**
- Android Camera HAL3 official documentation: https://source.android.com/docs/core/camera
- AOSP camera framework source code: https://android.googlesource.com/platform/frameworks/av/+/refs/heads/main/camera/

---

## C.11 Three-Platform Side-by-Side Comparison

### C.11.1 Architecture and Capability Matrix

| Dimension | Qualcomm Spectra (8 Gen3) | HiSilicon Kirin (9000) | MediaTek Imagiq (9200) |
|-----------|--------------------------|----------------------|----------------------|
| **ISP count** | Triple (since SD888) | Triple (since K990 5G, 2019) | Triple (since D1000, 2019) |
| **Internal precision** | 18-bit (since 8 Gen1) | Undisclosed (est. 14–16-bit) | Undisclosed (est. 14-bit) |
| **Dedicated RAW subsystem** | BPS (independent hardware) | Integrated in main ISP | Integrated in main ISP |
| **AI accelerator** | Hexagon DSP / NPU | Da Vinci NPU | APU (AI Processing Unit) |
| **MFNR frame count** | Up to 30 (SD888+) | 4–8 frames | 4–8 frames |
| **CFA support** | Standard RGGB / RYYB (via sensor) | RGGB + dedicated RYYB AI demosaic | Standard RGGB + limited RYYB |
| **Peak pixel throughput** | ~3.2 Gpixel/s (estimated) | 2.4 Gpixel/s (K990 5G, 3-core) | 900 Mpixel/s (D9200, 3-core) |
| **HDR methods** | Staggered HDR | ZHDR + LS-HDR + Staggered | HDR-Vivid + Dolby Vision |
| **Max supported resolution** | ~200 MP (SD8 Gen2) | ~50 MP burst (K9000) | 320 MP (D9000 Imagiq 790) |

### C.11.2 Tuning Toolchain Matrix

| Dimension | Qualcomm Spectra | HiSilicon Kirin | MediaTek Imagiq |
|-----------|-----------------|----------------|----------------|
| **Tuning tool** | Chromatix CTT | HiTuning Tool | APMCT |
| **Parameter file format** | Chromatix XML | Undisclosed | NVRAM XML |
| **Tool availability** | ODM/OEM partners (NDA) | Internal only, no external access | ODM/OEM partners (NDA) |
| **ISO interpolation points** | 8–12 | Undisclosed (~6–10 estimated) | Undisclosed (~6–10 estimated) |
| **Standard illuminants** | A / TL84 / CWF / D65 (4 types) | A / TL84 / CWF / D65 (similar) | A / TL84 / D65 (similar) |
| **Open-source exposure** | Partial AOSP HAL | Minimal (Linux driver fragments) | Partial AOSP HAL + ORA open interface |
| **Custom algorithm injection** | Limited (HAL plugin) | Not supported | **ORA architecture (2023) — HAL-level injection** |

### C.11.3 Signature Algorithm Matrix

| Algorithm | Qualcomm Spectra | HiSilicon Kirin | MediaTek Imagiq |
|-----------|-----------------|----------------|----------------|
| Multi-frame RAW NR | MFNR (30-frame, SD888+) | MFNR (4–8 frames) | MFNR (4–8 frames) |
| AI denoise architecture | Hexagon NPU (DL network) | Da Vinci NPU (DL network) | APU + ESRGAN-style network |
| Semantic segmentation NR | Partial (8 Gen2+) | Full per-class segmentation | Full per-class segmentation |
| AI super-resolution | Supported (Hexagon) | 4× XD-Fusion SR | AI-SR (APU) |
| Multi-camera hardware fusion | Triple ISP coordination | XD-Fusion Pro (ISP + NPU) | DCIF (hardware pixel registration) |
| Ghost-free HDR method | Staggered HDR (sensor-level) | ZHDR (sensor-level) | Interleaved HDR |
| Proprietary HDR format | HDR10+ (real-time capture) | None proprietary | HDR-Vivid + Dolby Vision |
| Generative AI | Supported (8 Gen3, experimental) | N/A (business discontinued) | Supported (D9400 Imagiq 1090) |

---

## C.12 Additional Notes

1. **Confidentiality:** Vendor-specific register-level parameters, detailed tuning ranges, and internal algorithm implementations for Qualcomm, HiSilicon, and MediaTek are covered by NDA. This appendix summarizes only publicly available technical materials and published white papers.

2. **HiSilicon business status:** Due to U.S. export controls, the Kirin 9000 series (TSMC 5nm) was the last high-end Kirin produced at scale with leading-edge process nodes from TSMC. The Kirin 9020 (Huawei Mate 60 Pro, SMIC 7nm-class process) launched in 2023 with constrained production volumes; its full ISP specifications have not been publicly disclosed.

3. **Tuning tool access:** All three platforms require NDA execution and vendor partner qualification before granting access to their tuning tools. Individual developers and academic institutions generally cannot obtain these tools through standard channels.

4. **AOSP reference code:** Qualcomm and MediaTek both contribute portions of their Camera HAL implementations to AOSP, which can be studied for architectural reference. However, these code contributions do not include the core ISP parameter tuning logic or algorithm implementations.

---

> **Note:** Sections C.1–C.9 of this appendix intentionally avoid mentioning specific vendor or chip names.
> Sections C.10–C.11 provide the vendor-specific deep-dives based solely on publicly available information.
> For pipeline stage counts, proprietary algorithm internals, and specific tuning parameter lists,
> refer to the private documentation in `private-repo/`.
