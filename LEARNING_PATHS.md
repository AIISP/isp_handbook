# Learning Paths — ISP Algorithm Handbook

Four curated reading sequences for different engineering backgrounds.
Pick the path that matches your role, then follow the chapter sequence linearly.
All cross-references use the format **Part N Ch M**.

---

## Quick Reference — Appendices

Before starting any path, bookmark these appendices. They are reference material you will return to repeatedly, not sequential reading.

| Appendix | Content | When to Use |
|----------|---------|-------------|
| **Appendix A** — Math Foundations | Linear algebra, convolution, Fourier transform, probability distributions used throughout the book | When a derivation loses you |
| **Appendix B** — Calibration Cards | X-Rite ColorChecker, ISO 12233, slanted-edge MTF cards; how to read calibration data | Before any lab tuning session |
| **Appendix C** — SoC Comparison | Qualcomm Snapdragon, MediaTek Dimensity, Apple A-series, HiSilicon Kirin ISP+NPU specs; correct TOPS figures | When evaluating platform choices |
| **Appendix D** — Open-Source Tools | rawpy, LibRaw, OpenCV ISP, Halide, AOSP Camera2 pointers | When setting up a dev environment |
| **Appendix E** — Datasets | MIT-5K, DIV2K, SIDD, DND, FiveK, PolyU — canonical training/eval sets | When benchmarking a DL method |
| **Appendix F** — Benchmarks | PSNR/SSIM/LPIPS numbers for key methods on standard datasets | When writing a paper or comparing algorithms |
| **Appendix G** — Notation | Symbol definitions used across all 6 volumes (e.g., $\sigma_r$, $\mathbf{M}_{CCM}$) | When notation is ambiguous |
| **Appendix J** — Environment Setup | Conda/pip environment setup, Colab links, tested Python versions | First-time setup only |

---

## Path 1 — ISP Tuning Engineer (调参工程师路径)

**Target audience:** Engineers tuning ISP parameters on Qualcomm/MTK/HiSilicon platforms. You already have access to a platform ISP (CamX, Tuning Tool, AIQE, or equivalent) and need to understand what each module does before touching its knobs.

**Prerequisites:** C/C++ or Python; basic signal processing concepts (convolution, frequency domain); some exposure to camera hardware is helpful but not required.

**Estimated time:** 4–6 weeks at roughly 2 hours/day.

**Expected outcome:** Able to independently diagnose artifacts to the module level, propose parameter changes with a causal explanation, and run a structured tuning cycle without going in circles.

---

### Chapter Sequence

#### Week 1 — Pipeline Mental Model

| Order | Chapter | Why It Matters for Tuning |
|-------|---------|--------------------------|
| 1 | [Part 1 Ch01 — ISP Pipeline Overview](part1_imaging_fundamentals/ch01_isp_pipeline_overview/ch01_isp_pipeline_overview_ch.md) | Build the end-to-end mental model before touching any individual module |
| 2 | [Part 1 Ch03 — Sensor Physics](part1_imaging_fundamentals/ch03_sensor_physics/ch03_sensor_physics_ch.md) | Understand where noise originates; critical for NR tuning |
| 3 | [Part 1 Ch04 — Noise Models](part1_imaging_fundamentals/ch04_noise_models/ch04_noise_models_ch.md) | Shot noise, read noise, FPN — the math behind every NR parameter |
| 4 | [Part 1 Ch06 — RAW Format & Bayer](part1_imaging_fundamentals/ch06_raw_format_bayer/ch06_raw_format_bayer_ch.md) | Why BLC, PDPC, and demosaic exist |
| 5 | [Part 1 Ch05 — Color Science Basics](part1_imaging_fundamentals/ch05_color_science_basics/ch05_color_science_basics_ch.md) | Color spaces, illuminants — prerequisite for AWB and CCM tuning |

#### Week 2 — Core Traditional ISP Modules

| Order | Chapter | Why It Matters for Tuning |
|-------|---------|--------------------------|
| 6 | [Part 2 Ch01 — BLC & PDPC](part2_traditional_isp/ch01_blc_pdpc/ch01_blc_pdpc_ch.md) | First module in the pipeline; global cast bugs start here |
| 7 | [Part 2 Ch08 — LSC (Lens Shading Correction)](part2_traditional_isp/ch08_lsc/ch08_lsc_ch.md) | Vignetting; calibration-driven, easy to verify in the field |
| 8 | [Part 2 Ch02 — Demosaic](part2_traditional_isp/ch02_demosaic/ch02_demosaic_ch.md) | False color, zipper artifacts; understand before enabling NR that interacts with demosaic output |
| 9 | [Part 2 Ch03 — Denoising](part2_traditional_isp/ch03_denoising/ch03_denoising_ch.md) | The module with the most tuning knobs; waxy skin vs. noise tradeoff |
| 10 | [Part 2 Ch04 — Sharpening & Edge Enhancement](part2_traditional_isp/ch04_sharpening/ch04_sharpening_ch.md) | Ringing artifacts; understand USM / edge-map gating |

#### Week 3 — Color & Tone

| Order | Chapter | Why It Matters for Tuning |
|-------|---------|--------------------------|
| 11 | [Part 2 Ch05 — AWB](part2_traditional_isp/ch05_awb/ch05_awb_ch.md) | Gray world, Bayesian estimation, scene detection; the most-tuned module |
| 12 | [Part 2 Ch06 — CCM (Color Correction Matrix)](part2_traditional_isp/ch06_ccm/ch06_ccm_ch.md) | Least-squares calibration; when to use 3×3 vs. 3×4 |
| 13 | [Part 2 Ch07 — Gamma & Tone Mapping](part2_traditional_isp/ch07_gamma_tonemapping/ch07_gamma_tonemapping_ch.md) | sRGB gamma vs. custom curves; HDR display considerations |
| 14 | [Part 2 Ch11 — Color Enhancement (Hue/Saturation)](part2_traditional_isp/ch11_color_enhancement/ch11_color_enhancement_ch.md) | Vivid mode, skin protection; risks of over-saturation |
| 15 | [Part 2 Ch09 — CSC & Output](part2_traditional_isp/ch09_csc_output/ch09_csc_output_ch.md) | YUV formats, chroma subsampling, output bit depth |

#### Week 4 — Advanced Modules & 3A

| Order | Chapter | Why It Matters for Tuning |
|-------|---------|--------------------------|
| 16 | [Part 2 Ch10 — HDR Merge](part2_traditional_isp/ch10_hdr_merge/ch10_hdr_merge_ch.md) | Multi-frame HDR ghosting, motion estimation, tone compression |
| 17 | [Part 2 Ch12 — Temporal NR (TNR)](part2_traditional_isp/ch12_temporal_nr/ch12_temporal_nr_ch.md) | Motion ghost, trailing artifacts; the most expensive module to debug |
| 18 | [Part 4 Ch01 — 3A System Overview](part4_system_iqa/ch01_3a_system/ch01_3a_system_ch.md) | How AE/AF/AWB interact as a control loop |
| 19 | [Part 4 Ch02 — AE Fundamentals](part4_system_iqa/ch02_ae_fundamentals/ch02_ae_fundamentals_ch.md) | Metering algorithms, exposure decision, ISO/shutter/aperture tradeoffs |
| 20 | [Part 4 Ch03 — AF Fundamentals](part4_system_iqa/ch03_af_fundamentals/ch03_af_fundamentals_ch.md) | Contrast AF, phase AF; focus hunting root causes |

#### Week 5–6 — Quality Metrics, Debugging, and System Integration

| Order | Chapter | Why It Matters for Tuning |
|-------|---------|--------------------------|
| 21 | [Part 4 Ch04 — Perceptual IQA](part4_system_iqa/ch04_perceptual_iqa/ch04_perceptual_iqa_ch.md) | PSNR/SSIM/LPIPS — what metrics actually correlate with tuning goals |
| 22 | [Part 4 Ch08 — IQA System Integration](part4_system_iqa/ch08_iqa_system/ch08_iqa_system_ch.md) | Building a repeatable test bench for tuning evaluation |
| 23 | [Part 4 Ch17 — ISP Tuning Workflow](part4_system_iqa/ch17_isp_tuning_workflow/ch17_isp_tuning_workflow_ch.md) | Structured tuning methodology: how to avoid cycling forever |
| 24 | [Part 4 Ch21 — ISP Artifact Debug](part4_system_iqa/ch21_isp_artifact_debug/ch21_isp_artifact_debug_ch.md) | Symptom → root cause → fix table for the 20 most common artifacts |
| 25 | [Part 4 Ch20 — ISP Parameter Management](part4_system_iqa/ch20_isp_parameter_management/ch20_isp_parameter_management_ch.md) | Version control for tuning data; avoiding parameter regression |
| 26 | [Part 2 Ch30 — ISP Calibration](part2_traditional_isp/ch30_isp_calibration/ch30_isp_calibration_ch.md) | Lab setup, color calibration pipeline, acceptance criteria |
| 27 | [Part 2 Ch31 — ISP Bringup](part2_traditional_isp/ch31_isp_bringup/ch31_isp_bringup_ch.md) | Bringing up a new sensor/platform from scratch |

#### Optional Depth Reading

- [Part 2 Ch14 — Face & Skin Enhancement](part2_traditional_isp/ch14_face_skin_enhancement/ch14_face_skin_enhancement_ch.md) (if your product targets portrait)
- [Part 2 Ch28 — Anti-Banding](part2_traditional_isp/ch28_anti_banding/ch28_anti_banding_ch.md) (if your platform has banding issues under artificial light)
- [Part 4 Ch22 — ISP Power Optimization](part4_system_iqa/ch22_isp_power_optimization/ch22_isp_power_optimization_ch.md) (if power budget is a constraint)
- [Part 4 Ch23 — Scene-Adaptive Parameter Switching](part4_system_iqa/ch23_scene_adaptive_params/ch23_scene_adaptive_params_ch.md) (for multi-mode ISP products)

#### Key Notebooks

| Notebook | What You Will Run |
|----------|------------------|
| `QUICK_START.ipynb` | Synthetic RAW → JPEG end-to-end; see every step before reading chapters |
| Part 2 Ch02 notebook | Demosaic algorithm comparison |
| Part 2 Ch05 notebook | AWB Gray World vs. Bayesian experiment |
| Part 2 Ch07 notebook | Gamma and tone mapping curve visualization |
| Part 4 Ch01 notebook | 3A control loop simulation |

---

## Path 2 — DL-ISP Algorithm Researcher (深度学习ISP研究者路径)

**Target audience:** ML/CV researchers working on image restoration, denoising, super-resolution, or enhancement for camera pipelines. You know PyTorch and standard vision benchmarks but are new to the camera-specific constraints (RAW domain, ISP pipeline interaction, on-device deployment).

**Prerequisites:** PyTorch or TensorFlow; solid understanding of CNNs and attention; familiar with PSNR/SSIM as metrics; linear algebra at undergraduate level.

**Estimated time:** 6–8 weeks at roughly 1.5 hours/day.

**Expected outcome:** Able to formulate a research problem in the ISP domain with physically grounded noise/color models, evaluate results with appropriate metrics, and understand what "production deployment" means for a DL-ISP method.

---

### Chapter Sequence

#### Phase 1 — Physical Grounding (Weeks 1–2)

These chapters provide the physics constraints that separate camera-specific DL from generic image restoration.

| Order | Chapter | Why It Matters for Research |
|-------|---------|---------------------------|
| 1 | [Part 1 Ch01 — ISP Pipeline Overview](part1_imaging_fundamentals/ch01_isp_pipeline_overview/ch01_isp_pipeline_overview_ch.md) | Understand the data flow your model must fit into |
| 2 | [Part 1 Ch04 — Noise Models](part1_imaging_fundamentals/ch04_noise_models/ch04_noise_models_ch.md) | Poisson-Gaussian noise, signal-dependent variance — the foundation of every denoising paper |
| 3 | [Part 1 Ch03 — Sensor Physics](part1_imaging_fundamentals/ch03_sensor_physics/ch03_sensor_physics_ch.md) | Where the noise physics comes from; motivates noise model design choices |
| 4 | [Part 1 Ch05 — Color Science Basics](part1_imaging_fundamentals/ch05_color_science_basics/ch05_color_science_basics_ch.md) | Color spaces, chromatic adaptation — needed to understand CCM and white balance in RAW-domain training |
| 5 | [Part 1 Ch06 — RAW Format & Bayer](part1_imaging_fundamentals/ch06_raw_format_bayer/ch06_raw_format_bayer_ch.md) | RAW data layout, bit depth, why training on RAW differs from training on RGB |
| 6 | [Part 1 Ch07 — Dynamic Range & HDR](part1_imaging_fundamentals/ch07_dynamic_range_hdr/ch07_dynamic_range_hdr_ch.md) | Why a single exposure is insufficient; motivates burst and HDR methods |

#### Phase 2 — DL-ISP Methods (Weeks 3–5)

| Order | Chapter | Why It Matters for Research |
|-------|---------|---------------------------|
| 7 | [Part 3 Ch01 — DL-ISP Overview](part3_dl_isp/ch01_dl_overview/ch01_dl_overview_ch.md) | Taxonomy of the field; where your work fits |
| 8 | [Part 3 Ch20 — DL Denoising Overview](part3_dl_isp/ch20_dl_denoising_overview/ch20_dl_denoising_overview_ch.md) | Survey of denoising methods from DnCNN to NAFNet |
| 9 | [Part 3 Ch21 — Image Denoising: DL Methods](part3_dl_isp/ch21_image_denoising_dl/ch21_image_denoising_dl_ch.md) | Method details, training setups, benchmark numbers |
| 10 | [Part 3 Ch03 — Super-Resolution](part3_dl_isp/ch03_super_resolution/ch03_super_resolution_ch.md) | SRCNN → EDSR → Real-ESRGAN → diffusion SR; degradation model design |
| 11 | [Part 3 Ch05 — Low-Light Image Enhancement](part3_dl_isp/ch05_llie/ch05_llie_ch.md) | LLIE datasets, paired vs. unpaired training, perceptual losses |
| 12 | [Part 3 Ch06 — AI Tone Mapping](part3_dl_isp/ch06_ai_tonemapping/ch06_ai_tonemapping_ch.md) | Learning TMO from HDR content; loss function design |
| 13 | [Part 3 Ch07 — Diffusion-Based Restoration](part3_dl_isp/ch07_diffusion_restoration/ch07_diffusion_restoration_ch.md) | Score-based models for blind restoration; current state of the art |
| 14 | [Part 3 Ch02 — End-to-End Restoration](part3_dl_isp/ch02_e2e_restoration/ch02_e2e_restoration_ch.md) | Joint optimization across ISP stages; RAW-to-RGB end-to-end pipelines |
| 15 | [Part 3 Ch22 — Universal Restoration](part3_dl_isp/ch22_universal_restoration/ch22_universal_restoration_ch.md) | All-in-one degradation models; PromptIR and related work |
| 16 | [Part 3 Ch08 — Video Denoising](part3_dl_isp/ch08_video_denoising/ch08_video_denoising_ch.md) | Temporal consistency, optical flow in denoising networks |
| 17 | [Part 3 Ch11 — DL Burst Night Mode](part3_dl_isp/ch11_burst_dl_night/ch11_burst_dl_night_ch.md) | Multi-frame alignment and fusion; the Google Night Sight architecture |
| 18 | [Part 3 Ch19 — Invertible ISP](part3_dl_isp/ch19_invertible_isp/ch19_invertible_isp_ch.md) | RAW ↔ RGB invertible mapping; useful for data augmentation |
| 19 | [Part 3 Ch24 — Neural ISP Pipeline](part3_dl_isp/ch24_neural_isp_pipeline/ch24_neural_isp_pipeline_ch.md) | Full neural replacement of traditional ISP; survey and analysis |

#### Phase 3 — Evaluation & Deployment (Weeks 6–7)

| Order | Chapter | Why It Matters for Research |
|-------|---------|---------------------------|
| 20 | [Part 4 Ch04 — Perceptual IQA](part4_system_iqa/ch04_perceptual_iqa/ch04_perceptual_iqa_ch.md) | FR metrics: PSNR, SSIM, LPIPS, MS-SSIM; which metric to report and why |
| 21 | [Part 4 Ch05 — Blind IQA (NR-IQA)](part4_system_iqa/ch05_blind_iqa/ch05_blind_iqa_ch.md) | NIQE, BRISQUE, MUSIQ, Q-Align — NR metrics for unpaired evaluation |
| 22 | [Part 4 Ch11 — HVS Models](part4_system_iqa/ch11_hvs_models/ch11_hvs_models_ch.md) | Why perceptual losses work; JND, CSF, masking |
| 23 | [Part 3 Ch14 — On-Device NPU Deployment](part3_dl_isp/ch14_on_device_npu/ch14_on_device_npu_ch.md) | Quantization, INT8/INT4, latency vs. quality tradeoff on mobile SoCs |
| 24 | [Part 3 Ch16 — Generative RAW-to-RGB](part3_dl_isp/ch16_generative_raw_rgb/ch16_generative_raw_rgb_ch.md) | GAN/diffusion-based ISP simulation; synthetic data generation |
| 25 | [Part 3 Ch17 — Self-Supervised ISP](part3_dl_isp/ch17_self_supervised_isp/ch17_self_supervised_isp_ch.md) | Noise2Noise, Noise2Void, blind-spot networks; training without clean targets |

#### Phase 4 — LLM Era (Week 8, optional but recommended)

| Order | Chapter | Why It Matters for Research |
|-------|---------|---------------------------|
| 26 | [Part 5 Ch01 — Foundation Models for Imaging](part5_llm_era/ch01_foundation_models/ch01_foundation_models_ch.md) | CLIP, DINO, ImageBind applied to image quality and restoration |
| 27 | [Part 5 Ch05 — Text-Guided Restoration](part5_llm_era/ch05_text_guided_restoration/ch05_text_guided_restoration_ch.md) | ControlNet, IP-Adapter for guided ISP; current research directions |
| 28 | [Part 5 Ch07 — RAW Foundation Models](part5_llm_era/ch07_raw_foundation_models/ch07_raw_foundation_models_ch.md) | Pre-training on RAW data; emerging research area |
| 29 | [Part 5 Ch11 — Synthetic Data for ISP](part5_llm_era/ch11_synthetic_data/ch11_synthetic_data_ch.md) | Camera noise simulators, ISP simulation for dataset generation |

#### Key Notebooks

| Notebook | What You Will Run |
|----------|------------------|
| `QUICK_START.ipynb` | Understand the full ISP pipeline before modeling it |
| Part 3 Ch03 notebook | SR: interpolation vs. learned upsampling comparison |
| Part 4 Ch01 notebook | 3A simulation — understanding what your model replaces |

---

## Path 3 — Mobile Camera System Architect (移动相机系统架构师路径)

**Target audience:** Senior engineers and technical leads designing end-to-end camera pipeline architectures, evaluating ISP+NPU integration choices, or making platform selection decisions. This path is reference-style, not sequential — read the sections relevant to your current decision, not cover to cover.

**Prerequisites:** 3+ years in camera or imaging; comfortable reading platform architecture documentation; basic familiarity with both hardware and algorithm perspectives.

**Estimated time:** 3–4 weeks of selective reading; keep this list as a reference checklist.

**Expected outcome:** Clear mental model of where the complexity lives in a modern mobile camera stack; ability to evaluate architectural tradeoffs with chapter-level citations; vocabulary to communicate across hardware, algorithm, and software teams.

---

### Reading Map by Decision Type

#### Architectural Foundations

| Chapter | Decision It Informs |
|---------|-------------------|
| [Part 1 Ch01 — ISP Pipeline Overview](part1_imaging_fundamentals/ch01_isp_pipeline_overview/ch01_isp_pipeline_overview_ch.md) | Pipeline stage sequencing; where to insert hardware accelerators |
| [Part 1 Ch10 — SoC & Hardware Accelerators](part1_imaging_fundamentals/ch10_soc_hardware/ch10_soc_hardware_ch.md) | ISP hardware blocks: line buffers, HW demosaic, HW TNR — constraints you cannot change |
| [Part 4 Ch18 — Camera HAL Architecture](part4_system_iqa/ch18_camera_hal_architecture/ch18_camera_hal_architecture_ch.md) | Android Camera2/HIDL/AIDL stack; where software meets hardware |
| [Part 4 Ch14 — Multi-Camera Architecture](part4_system_iqa/ch14_multi_camera_architecture/ch14_multi_camera_architecture_ch.md) | Spatial sync, temporal sync, parallax handling in multi-lens systems |
| [Part 4 Ch15 — Real-Time Constraints](part4_system_iqa/ch15_realtime_constraints/ch15_realtime_constraints_ch.md) | Frame budget calculation, DDR bandwidth, pipeline stall analysis |
| [Part 2 Ch31 — ISP Bringup](part2_traditional_isp/ch31_isp_bringup/ch31_isp_bringup_ch.md) | What the first-week-on-a-new-platform checklist looks like |

#### Sensor & Optics Selection

| Chapter | Decision It Informs |
|---------|-------------------|
| [Part 1 Ch03 — Sensor Physics](part1_imaging_fundamentals/ch03_sensor_physics/ch03_sensor_physics_ch.md) | Pixel size, full-well capacity, QE — the fundamental tradeoff table |
| [Part 1 Ch17 — Sensor Binning](part1_imaging_fundamentals/ch17_sensor_binning/ch17_sensor_binning_ch.md) | Quad-Bayer, Nona-Bayer pixel array modes; readout architecture impact |
| [Part 1 Ch02 — Optics Basics](part1_imaging_fundamentals/ch02_optics_basics/ch02_optics_basics_ch.md) | F-number, diffraction limit, depth of field — optical system constraints |
| [Part 1 Ch08 — Optics Aberrations](part1_imaging_fundamentals/ch08_optics_aberrations/ch08_optics_aberrations_ch.md) | CA, coma, field curvature — when to correct in optics vs. in ISP |
| [Part 6 Ch05 — Huawei RYYB](part6_consumer_photography/ch05_huawei_ryyb/ch05_huawei_ryyb_ch.md) | RYYB sensor design tradeoffs; the cost of breaking Bayer convention |
| [Part 6 Ch06 — Samsung ISOCELL](part6_consumer_photography/ch06_samsung_isocell/ch06_samsung_isocell_ch.md) | Pixel-level innovations: ISOCELL Plus, Tetracell, ISOCELL Zoom |

#### Computational Photography Architecture

| Chapter | Decision It Informs |
|---------|-------------------|
| [Part 4 Ch07 — Computational Photography](part4_system_iqa/ch07_computational_photography/ch07_computational_photography_ch.md) | Burst processing, multi-frame fusion, computational zoom architecture |
| [Part 4 Ch09 — 3A Advanced Topics](part4_system_iqa/ch09_3a_advanced_topics/ch09_3a_advanced_topics_ch.md) | Multi-zone metering, scene detection, ML-assisted 3A |
| [Part 2 Ch22 — Multi-Camera Fusion](part2_traditional_isp/ch22_multi_camera_fusion/ch22_multi_camera_fusion_ch.md) | Fusion algorithms for wide+tele+ultra-wide systems |
| [Part 2 Ch26 — Burst Night Mode](part2_traditional_isp/ch26_burst_night_mode/ch26_burst_night_mode_ch.md) | Frame selection, alignment, fusion stack for night photography |
| [Part 2 Ch27 — Bokeh & Portrait Mode](part2_traditional_isp/ch27_bokeh_portrait/ch27_bokeh_portrait_ch.md) | Depth estimation, segmentation, synthetic aperture rendering |
| [Part 6 Ch02 — Night Sight / HDR+](part6_consumer_photography/ch02_night_sight_hdrplus/ch02_night_sight_hdrplus_ch.md) | Google's burst HDR+ architecture end-to-end; the reference implementation |
| [Part 6 Ch03 — Apple Deep Fusion](part6_consumer_photography/ch03_apple_deep_fusion/ch03_apple_deep_fusion_ch.md) | Apple's multi-frame neural processing architecture |

#### AI/NPU Integration

| Chapter | Decision It Informs |
|---------|-------------------|
| [Part 3 Ch14 — On-Device NPU Deployment](part3_dl_isp/ch14_on_device_npu/ch14_on_device_npu_ch.md) | Quantization loss, INT8 vs. INT4, latency on Snapdragon/Dimensity/A-series |
| [Part 5 Ch13 — Edge AI for Camera](part5_llm_era/ch13_edge_ai/ch13_edge_ai_ch.md) | NPU scheduling, ISP+NPU pipeline integration, power envelope |
| [Part 6 Ch04 — Mobile ISP Chips](part6_consumer_photography/ch04_mobile_isp_chips/ch04_mobile_isp_chips_ch.md) | Qualcomm Spectra, MediaTek Imagiq, Apple ISP — functional block comparison |
| **Appendix C** — SoC Comparison | Side-by-side ISP+NPU specs for current SoC lineup |

#### Quality & Testing

| Chapter | Decision It Informs |
|---------|-------------------|
| [Part 4 Ch08 — IQA System](part4_system_iqa/ch08_iqa_system/ch08_iqa_system_ch.md) | Building a regression test system for ISP quality; acceptance criteria |
| [Part 4 Ch10 — ISP Testing Toolchain](part4_system_iqa/ch10_isp_testing_toolchain/ch10_isp_testing_toolchain_ch.md) | Lab equipment, test charts, automated capture scripts |
| [Part 4 Ch17 — Tuning Workflow](part4_system_iqa/ch17_isp_tuning_workflow/ch17_isp_tuning_workflow_ch.md) | How tuning cycles are structured; who owns each stage |
| [Part 4 Ch21 — Artifact Debug](part4_system_iqa/ch21_isp_artifact_debug/ch21_isp_artifact_debug_ch.md) | Systematic debugging process; reduces time-to-root-cause |

#### Video & Emerging Use Cases

| Chapter | Decision It Informs |
|---------|-------------------|
| [Part 2 Ch33 — Video ISP Overview](part2_traditional_isp/ch33_video_isp_overview/ch33_video_isp_overview_ch.md) | Video-specific requirements: deinterlace, temporal consistency, GBR sync |
| [Part 4 Ch16 — Video ISP Engineering](part4_system_iqa/ch16_video_isp_engineering/ch16_video_isp_engineering_ch.md) | Frame budget under video constraints; 4K/8K pipeline feasibility |
| [Part 6 Ch09 — Smartphone Video ISP](part6_consumer_photography/ch09_smartphone_video_isp/ch09_smartphone_video_isp_ch.md) | Log format, color science in video, stabilization integration |
| [Part 4 Ch13 — AR/VR ISP](part4_system_iqa/ch13_ar_vr_isp/ch13_ar_vr_isp_ch.md) | Latency requirements for MR/XR pipelines; ISP in HMDs |

---

## Path 4 — Interview Prep / ISP Fundamentals (面试备考 / ISP基础路径)

**Target audience:** Students, recent graduates, or engineers from adjacent domains (display, video codec, perception) preparing for camera algorithm or ISP engineering interviews at phone OEMs, camera IP vendors, or automotive Tier-1 suppliers.

**Prerequisites:** Undergraduate linear algebra and probability; some programming experience; no prior ISP knowledge assumed.

**Estimated time:** 2–3 weeks, focusing on depth over breadth. Read each chapter with the goal of being able to explain it to an interviewer from first principles.

**Expected outcome:** Able to answer "walk me through the ISP pipeline" coherently; explain the tradeoff in 5 core modules; describe the 3A control loop; define key IQA metrics; discuss one DL-ISP method in detail.

---

### Core Reading List (Minimum Viable ISP Knowledge)

Complete these in order. Do not skip to Part 3 before finishing the first two blocks.

#### Block 1 — Pipeline & Physics (Days 1–5)

| Day | Chapter | Interview Topics It Covers |
|-----|---------|--------------------------|
| 1 | [Part 1 Ch01 — ISP Pipeline Overview](part1_imaging_fundamentals/ch01_isp_pipeline_overview/ch01_isp_pipeline_overview_ch.md) | "Walk me through a RAW-to-JPEG pipeline" |
| 2 | [Part 1 Ch03 — Sensor Physics](part1_imaging_fundamentals/ch03_sensor_physics/ch03_sensor_physics_ch.md) | "What is shot noise? What is read noise? How does ISO affect noise?" |
| 3 | [Part 1 Ch04 — Noise Models](part1_imaging_fundamentals/ch04_noise_models/ch04_noise_models_ch.md) | "What is the Poisson-Gaussian noise model?" |
| 4 | [Part 1 Ch05 — Color Science Basics](part1_imaging_fundamentals/ch05_color_science_basics/ch05_color_science_basics_ch.md) | "What is a color space? What is white balance? What is chromatic adaptation?" |
| 5 | [Part 1 Ch06 — RAW Format & Bayer](part1_imaging_fundamentals/ch06_raw_format_bayer/ch06_raw_format_bayer_ch.md) | "What is a Bayer pattern? Why does demosaic produce color?" |

#### Block 2 — Core ISP Modules (Days 6–12)

| Day | Chapter | Interview Topics It Covers |
|-----|---------|--------------------------|
| 6 | [Part 2 Ch01 — BLC & PDPC](part2_traditional_isp/ch01_blc_pdpc/ch01_blc_pdpc_ch.md) | "What is black level correction? What are hot pixels?" |
| 7 | [Part 2 Ch02 — Demosaic](part2_traditional_isp/ch02_demosaic/ch02_demosaic_ch.md) | "Bilinear vs. AHD demosaic — what is the tradeoff?" |
| 8 | [Part 2 Ch03 — Denoising](part2_traditional_isp/ch03_denoising/ch03_denoising_ch.md) | "BM3D vs. NLM vs. DL denoising — advantages and disadvantages" |
| 9 | [Part 2 Ch04 — Sharpening](part2_traditional_isp/ch04_sharpening/ch04_sharpening_ch.md) | "What is unsharp masking? What causes edge ringing?" |
| 10 | [Part 2 Ch05 — AWB](part2_traditional_isp/ch05_awb/ch05_awb_ch.md) | "Gray World algorithm — assumptions and failure cases" |
| 11 | [Part 2 Ch06 — CCM](part2_traditional_isp/ch06_ccm/ch06_ccm_ch.md) | "What is a color correction matrix? How is it calibrated?" |
| 12 | [Part 2 Ch07 — Gamma & Tone Mapping](part2_traditional_isp/ch07_gamma_tonemapping/ch07_gamma_tonemapping_ch.md) | "What is gamma encoding? Why is sRGB gamma not a pure power function?" |

#### Block 3 — 3A & Quality (Days 13–17)

| Day | Chapter | Interview Topics It Covers |
|-----|---------|--------------------------|
| 13 | [Part 4 Ch01 — 3A System Overview](part4_system_iqa/ch01_3a_system/ch01_3a_system_ch.md) | "What is the 3A control loop? How do AE, AF, AWB interact?" |
| 14 | [Part 4 Ch02 — AE Fundamentals](part4_system_iqa/ch02_ae_fundamentals/ch02_ae_fundamentals_ch.md) | "What is metering? How is exposure value calculated?" |
| 15 | [Part 4 Ch04 — Perceptual IQA](part4_system_iqa/ch04_perceptual_iqa/ch04_perceptual_iqa_ch.md) | "What is SSIM? When does PSNR disagree with human perception?" |
| 16 | [Part 4 Ch17 — ISP Tuning Workflow](part4_system_iqa/ch17_isp_tuning_workflow/ch17_isp_tuning_workflow_ch.md) | "How is ISP tuning structured in a production program?" |
| 17 | [Part 4 Ch21 — ISP Artifact Debug](part4_system_iqa/ch21_isp_artifact_debug/ch21_isp_artifact_debug_ch.md) | "If skin looks waxy, which module do you investigate first?" |

#### Block 4 — DL-ISP Awareness (Days 18–21)

One chapter per day. Focus on understanding the core idea and one key paper per topic, not exhaustive coverage.

| Day | Chapter | Interview Topics It Covers |
|-----|---------|--------------------------|
| 18 | [Part 3 Ch01 — DL-ISP Overview](part3_dl_isp/ch01_dl_overview/ch01_dl_overview_ch.md) | "How does DL-ISP differ from traditional ISP?" |
| 19 | [Part 3 Ch03 — Super-Resolution](part3_dl_isp/ch03_super_resolution/ch03_super_resolution_ch.md) | "What is SRCNN? What does the degradation model do in Real-ESRGAN?" |
| 20 | [Part 3 Ch14 — On-Device NPU Deployment](part3_dl_isp/ch14_on_device_npu/ch14_on_device_npu_ch.md) | "What is INT8 quantization? What is the accuracy drop?" |
| 21 | [Part 6 Ch02 — Night Sight / HDR+](part6_consumer_photography/ch02_night_sight_hdrplus/ch02_night_sight_hdrplus_ch.md) | "How does Google Night Sight work at a high level?" |

---

### Interview Checklist — Can You Answer These?

Use these as self-test questions after finishing each block.

**Pipeline & Physics**
- [ ] Name all stages of a typical mobile ISP pipeline in order.
- [ ] Explain why noise variance is signal-dependent in a CMOS sensor.
- [ ] What does the D50 illuminant represent and why is it used in color calibration?

**Core Modules**
- [ ] Why does bilinear demosaic produce false color at diagonal edges?
- [ ] What is the waxy-skin tradeoff in denoising, and how do spatial/bilateral filters address it?
- [ ] Under what scene conditions does Gray World AWB fail?
- [ ] Derive the 3×3 CCM from a set of measured vs. reference color patches (least-squares form).
- [ ] What is the difference between gamma correction and tone mapping?

**3A & Quality**
- [ ] Sketch a block diagram of the AE control loop, including feedback and integration time.
- [ ] What is the SSIM formula, and which image degradation does it fail to penalize?
- [ ] Name three common ISP artifacts and identify which module is the likely source of each.

**DL-ISP**
- [ ] What is the signal-dependent noise model used to generate synthetic training data for raw denoising?
- [ ] Why does a model trained on RGB images often fail when applied to RAW?
- [ ] What does INT8 quantization mean, and what is a typical PSNR drop vs. FP32 for a denoising network?

---

### Additional Reference Reading (Non-Sequential)

These chapters are not required for interviews but add depth if time allows:

- [Part 1 Ch07 — Dynamic Range & HDR](part1_imaging_fundamentals/ch07_dynamic_range_hdr/ch07_dynamic_range_hdr_ch.md) (for HDR-related roles)
- [Part 2 Ch10 — HDR Merge](part2_traditional_isp/ch10_hdr_merge/ch10_hdr_merge_ch.md) (for flagship camera roles)
- [Part 2 Ch12 — Temporal NR](part2_traditional_isp/ch12_temporal_nr/ch12_temporal_nr_ch.md) (for video camera roles)
- [Part 2 Ch08 — LSC](part2_traditional_isp/ch08_lsc/ch08_lsc_ch.md) (for calibration-focused roles)
- [Part 4 Ch05 — Blind IQA](part4_system_iqa/ch05_blind_iqa/ch05_blind_iqa_ch.md) (for IQA-focused roles)
- [Part 6 Ch03 — Apple Deep Fusion](part6_consumer_photography/ch03_apple_deep_fusion/ch03_apple_deep_fusion_ch.md) (for computational photography roles)

---

## Path Comparison Summary

| Dimension | Path 1: Tuning Engineer | Path 2: DL Researcher | Path 3: System Architect | Path 4: Interview Prep |
|-----------|------------------------|----------------------|--------------------------|----------------------|
| Starting chapter | Part 1 Ch01 | Part 1 Ch01 | Part 1 Ch01 or Part 4 Ch18 | Part 1 Ch01 |
| Estimated time | 4–6 weeks | 6–8 weeks | 3–4 weeks (selective) | 2–3 weeks |
| Reading style | Sequential | Sequential | Reference / on-demand | Sequential with self-tests |
| Heaviest volume | Part 2 (Traditional ISP) | Part 3 (DL-ISP) | Part 4 + Part 6 | Part 1 + Part 2 |
| Key appendix | Appendix B (Calibration) | Appendix E (Datasets) | Appendix C (SoC) | Appendix G (Notation) |
| Primary output | Tuning skill + debug skill | Research formulation + evaluation | Architectural judgment | Interview readiness |

---

*This file was last updated: 2026-06-11. Chapter list reflects the published state of the handbook as of that date.*
