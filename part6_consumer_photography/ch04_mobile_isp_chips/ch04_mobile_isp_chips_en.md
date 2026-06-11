# Part 6, Chapter 04: Mobile ISP Chip Architecture Comparison (Qualcomm / MediaTek / Apple / Custom)

> **Position:** This chapter provides an engineering-level cross-platform comparison of the four major mobile ISP chip platforms.
> **Prerequisites:** Vol.6 Ch.01 (Consumer Photography Evolution), Vol.1 Ch.10 (ISP SoC Hardware Architecture)
> **Audience:** Algorithm engineers, system designers

---

## §1 ISP Chip Architecture Overview

### 1.1 Fundamental Structure of the ISP Processing Pipeline

The mobile ISP (Image Signal Processor) occupies an independent hardware module within the SoC (System on Chip) and handles all signal processing tasks from sensor RAW data to the final image output. The typical hardware pipeline proceeds as follows:

```
MIPI CSI-2 Input
    │
    ▼
RAW-Domain Pre-processing
  ├─ BLC (Black Level Correction)
  ├─ PDPC (Pixel Defect & Correction)
  └─ LSC (Lens Shading Correction)
    │
    ▼
Demosaicing (Demosaic / Debayer)
    │
    ▼
RAW-Domain Denoising (MFNR / TNR)
    │
    ▼
RGB-Domain Processing
  ├─ AWB (Auto White Balance)
  ├─ CCM (Color Correction Matrix)
  └─ Sharpening (Sharpening / Edge Enhancement)
    │
    ▼
Tone Mapping (Gamma / Tone Mapping)
    │
    ▼
YUV Conversion & Output
  ├─ CSC (Color Space Conversion)
  └─ JPEG/HEIF Encoder
```

Each hardware module is a fully pipelined design, processing data row by row (line buffer) or block by block (tile), to match the sensor output bandwidth. 4K 30 fps (3840×2160, 30 frames/second) requires an ISP throughput of approximately $3840 \times 2160 \times 30 \approx 249$ megapixels per second (Mpix/s); 4K 120 fps requires approximately 996 Mpix/s. 8K 30 fps (7680×4320) requires approximately 994 Mpix/s — comparable to 4K 120 fps — but with stricter intra-frame latency requirements, since each frame has a time window of only 33 ms.

### 1.2 Essential Differences Between Hardware ISP and Software ISP

| Dimension | Hardware ISP (HW-ISP) | Software ISP (SW-ISP) |
|-----------|----------------------|----------------------|
| Latency | <5 ms (real-time preview) | 50–500 ms (offline post-processing) |
| Power consumption | 0.5–2 W (dedicated logic) | 2–8 W (CPU/GPU general-purpose compute) |
| Programmability | Limited (register configuration) | Fully flexible (arbitrary algorithms) |
| Typical application | Real-time viewfinder, video recording | Computational photography post-processing (AI NR, multi-frame fusion) |
| Memory bandwidth | Internal line buffer; no DRAM round-trips | Repeated DRAM reads/writes (bandwidth bottleneck) |

Modern mobile platforms use a **hybrid architecture**: the hardware ISP handles the real-time pipeline, the NPU (Neural Processing Unit) or DSP handles AI inference tasks, and CPU/GPU serve as post-processing supplements. The three subsystems collaborate through shared memory and DMA (Direct Memory Access), forming a heterogeneous compute pipeline.

### 1.3 Bandwidth Requirements Calculation

Using 4K 30 fps RAW12 as an example:

$$BW = W \times H \times fps \times \frac{bpp}{8} \times 2$$

where the factor of 2 represents one read and one write (read RAW, write YUV). Substituting values:

$$BW_{4K30} = 3840 \times 2160 \times 30 \times \frac{12}{8} \times 2 \approx 1.49 \text{ GB/s}$$

When MFNR merges 4 frames, intermediate frames must be buffered in DRAM, multiplying bandwidth by the frame count:

$$BW_{MFNR} \approx 1.49 \times 4 = 5.96 \text{ GB/s}$$

This explains why high-end SoCs choose LPDDR5/5X memory (peak bandwidth exceeding 60 GB/s) to support AI computational photography pipelines — not merely for the basic ISP pipeline.

### 1.4 NPU and AI-ISP Integration Trends

Since 2017, mobile AI-ISP has evolved through three stages:

- **Stage 1 (2017–2019):** The NPU independently runs classification/detection tasks; results are passed as metadata to the ISP to adjust parameters (scene-aware AWB, face-region exposure priority)
- **Stage 2 (2020–2022):** The NPU directly processes RAW data; semantic segmentation masks guide region-differentiated ISP processing (sky/face/vegetation each use different NR strength and color preferences)
- **Stage 3 (2023–present):** End-to-end neural networks (E2E NN) participate in the core RAW-to-RGB path; the NPU and hardware ISP run in parallel, with the two outputs weighted and fused in the YUV domain

---

## §2 Qualcomm Spectra ISP

### 2.1 Spectra 780 Architecture (Snapdragon 8 Gen 2)

The Qualcomm Snapdragon 8 Gen 2 (released 2022) integrates the Spectra 780 ISP, the first commercial SoC from Qualcomm to support three 18-bit ISP paths running in parallel. Core specifications:

| Specification | Spectra 780 (Snapdragon 8 Gen 2) |
|---------------|----------------------------------|
| ISP paths | 3 parallel (Triple ISP) |
| Bit depth | 18-bit RAW pipeline |
| Maximum resolution (still) | 200 MP (single path) |
| Video capability | 8K@30fps / 4K@120fps |
| Slow motion | 720p@480fps |
| AI functions | Hexagon DSP + Qualcomm AI Engine |
| MFNR | Hardware-accelerated 4-frame merge |

The significance of the 18-bit internal bus width (vs. 16-bit in previous generations): in high-gain scenes, the tail of the noise distribution is not clipped by insufficient bit depth, preserving more headroom for post-processing compression. Additionally, staggered 3-exposure HDR merging requires internal accumulators with sufficient bit width to prevent overflow in bright regions.

### 2.2 Spectra ISP Generation History

| Generation | SoC | Release Year | Core ISP Features |
|-----------|-----|-------------|-------------------|
| Spectra 380 | Snapdragon 845 | 2018 | Dual ISP 14-bit, 480fps slow motion, AI-assisted scene detection |
| Spectra 580 | Snapdragon 888 | 2021 | Triple ISP 18-bit, multi-camera simultaneous processing, Hexagon 780 |
| Spectra 680 | Snapdragon 8 Gen 1 | 2022 | Triple ISP 18-bit, 4K120fps, AI-NR enters real-time preview stream |
| Spectra 780 | Snapdragon 8 Gen 2 | 2022 | Triple ISP 18-bit, 200 MP, 8K30fps, E2E AI integration |
| Spectra 800 | Snapdragon 8 Gen 3 | 2023 | Triple ISP 18-bit, on-ISP AI super-resolution, real-time semantic NR |
| Spectra 1080 | Snapdragon 8 Elite | 2024 | Triple ISP 20-bit, ~49 TOPS NPU (third-party est.), on-device generative image editing |

A critical bandwidth inflection point came with the Spectra 480 (Snapdragon 888): the upgrade from dual to triple parallel ISP made simultaneous OIS-compensated alignment and multi-camera (wide + main + telephoto) concurrent capture a system design norm, sharply increasing DRAM bandwidth pressure and driving the Snapdragon platform to upgrade to LPDDR5.

### 2.3 CamX-CHI Software Framework

Qualcomm's camera software framework (Camera HAL Framework) uses a two-layer CamX-CHI (Camera eXtension – Camera HAL Interface) architecture:

- **CamX layer:** Hardware Abstraction Layer (HAL), managing ISP register configuration, DMA scheduling, and sensor drivers
- **CHI layer:** Feature2 pipeline engine (DAG – Directed Acyclic Graph), describing algorithm node topology; supports OEM insertion of custom nodes

Feature2 pipeline configurations are described in XML files. Key concepts:

```xml
<Pipeline name="IPEFeature2Preview">
  <Node name="IPE" type="IPENode">
    <InputPort id="0" name="RAW"/>
    <OutputPort id="1" name="YUV"/>
  </Node>
  <Node name="ChiDummyNode" type="CustomNode">
    <!-- OEM custom algorithm node -->
  </Node>
</Pipeline>
```

The **Chromatix tuning system** is the core toolchain for Qualcomm ISP calibration. It stores sensor module parameters (AWB statistics weights, NR strength curves, gamma tables, CCM coefficients) in binary packages (.bin) or XML format, dynamically indexed by the 3A (auto exposure / auto focus / auto white balance) state machine:

```
Scene detection → Mode selection (indoor / outdoor / night / portrait)
    │
    ▼
Chromatix parameter package → ISP register configuration → Image quality output
```

Chromatix parameter calibration typically covers these dimensions: Gain (1×–64×) × Color Temperature (CCT, 2000 K–7500 K) × Exposure time, forming a 3D lookup table (LUT) with bilinear interpolation at runtime.

### 2.4 MFNR (Multi-Frame Noise Reduction) Hardware Acceleration

Qualcomm MFNR is a flagship feature of the Spectra ISP. Its fundamental difference from a pure CPU/GPU implementation is that frame alignment is performed by a dedicated hardware unit, eliminating the bandwidth cost of copying multi-frame RAW data in and out of DRAM.

MFNR workflow:
1. **Trigger phase:** After half-pressing the shutter, the ISP begins accumulating 4 RAW frames in its internal frame buffer
2. **Alignment phase:** An optical flow estimation hardware module computes inter-frame motion vectors at sub-pixel precision to compensate for handheld shake
3. **Fusion phase:** Weighted merge — a confidence map derived from alignment residuals lowers fusion weights for high-residual regions (moving subjects), preventing ghost artifacts
4. **Output phase:** The fused single-frame RAW enters subsequent ISP processing

MFNR theoretical SNR improvement: when merging $N$ aligned frames, signal amplitude adds linearly while noise standard deviation adds as $\sqrt{N}$ (assuming independent inter-frame noise). SNR gain:

$$\text{SNR}_{N\text{ frames}} = \sqrt{N} \cdot \text{SNR}_{1\text{ frame}}$$

4-frame merge yields a theoretical SNR improvement of approximately 6 dB ($20\log_{10}\sqrt{4} = 6.02$ dB).

### 2.5 Hexagon DSP and AI Engine

The Snapdragon AI Engine is a heterogeneous AI compute suite composed of three subsystems:

- **Hexagon DSP (CDSP):** A vector processor for dense multiply-accumulate operations such as convolutions, featuring HVX (Hexagon Vector eXtensions) 128-wide SIMD
- **Adreno GPU:** Targets high-parallelism 2D/3D graphics and AI inference
- **Qualcomm NPU (HTP, Hexagon Tensor Processor):** A hardware deep learning accelerator; the Snapdragon 8 Gen 2 AI Engine reaches 34 TOPS (INT8, Qualcomm official — combined CPU+GPU+HTP+DSP figure)

AI-ISP application examples:
- **Semantic NR:** The NPU performs real-time semantic segmentation of YUV frames (face / sky / plant / background), generating region masks; the ISP noise reduction module applies different strength parameters per region
- **Scene Adaptive ISP:** A CNN classifies scenes (night / backlit / food / document, etc.), triggering a corresponding Chromatix parameter package switch

---

## §3 MediaTek Imagiq ISP

### 3.1 Imagiq 980 Architecture (Dimensity 9300)

The MediaTek Dimensity 9300 (released 2023) integrates the Imagiq 980 ISP, matching flagship Qualcomm Spectra specs for the first time:

| Specification | Imagiq 980 (Dimensity 9300) |
|---------------|------------------------------|
| ISP paths | 3 parallel (Triple ISP) |
| Bit depth | 18-bit (claimed) |
| Maximum resolution (still) | 320 MP |
| Video capability | 8K@30fps / 4K@120fps |
| AI hardware | APU 790 (33 TOPS, MediaTek official) |
| HDR-ISP | Staggered HDR single-frame multi-exposure |

Note on the 320 MP resolution specification: the highest sensor shipped in a phone is 200 MP (e.g., ISOCELL HP2); 320 MP is a hardware ceiling reserved for future sensor generations.

### 3.2 FeaturePipe Architecture

The MediaTek camera software framework (MTK Camera HAL) uses a FeaturePipe (Feature Pipeline) architecture, also describing algorithm nodes as a DAG. The key difference from Qualcomm's CamX-CHI is:

- **Higher degree of plug-in modularity:** Each Feature loads as an independent dynamic library (.so) with a standardized interface; OEMs/ODMs can replace the core denoising plugin without recompiling the HAL
- **NDD calibration system:** MediaTek uses NDD (Noise Distribution Data) to describe the sensor noise model (replacing Qualcomm's noise profile), fitted from measured dark frames using calibration tools for higher fidelity to the real sensor

FeaturePipe key nodes (example: night scene capture):
```
MIPI RAW Input
    │
    ├─ P1 Node (ISP hardware node: BLC / LSC / AWB statistics)
    │
    ├─ MFNR Node (Multi-frame RAW fusion, 4–8 frames)
    │
    ├─ YNR Node (YUV-domain denoising, APU-accelerated)
    │
    └─ JPEG Node (encoding output)
```

### 3.3 APU Integration and AI Denoising

The integration of MediaTek's APU (AI Processing Unit) with the ISP is demonstrated in:

**AI-AWB:** Traditional AWB relies on gray-world assumptions or white-patch detection, with larger errors in complex mixed-illuminant scenes. MediaTek's AI-AWB trains a lightweight CNN that takes AWB statistics histograms as input and outputs a color temperature estimate and gain adjustment. Color accuracy improves by approximately 15% in fluorescent + tungsten mixed-light scenes (internal test data, per Imagiq 980 technical white paper).

**APU-accelerated YNR (luminance-domain denoising):** APU 790 supports INT8/INT4 inference. The YNR network is a lightweight U-Net variant that takes 16×16 tile YUV data as input and outputs a denoising confidence map, fed back to the hardware NR module to dynamically adjust filter strength.

### 3.4 Staggered HDR Architecture

The Imagiq HDR-ISP uses Staggered exposure mode: within a single frame readout period, the rolling shutter sensor exposes row by row with different rows using different exposure times (long-exposure rows / short-exposure rows alternating). The ISP performs HDR merging in real time during readout, without needing multi-frame buffering.

| HDR Mode | Timing | Advantages | Disadvantages |
|---------|--------|-----------|--------------|
| Multi-frame HDR | Consecutive multi-shot | Each frame exposure independently optimized | Motion ghosting, reduced frame rate |
| Staggered HDR | Single-frame row-level alternation | Complete within one frame; less motion ghosting | Vertical-direction resolution difference |
| DOL-HDR | Dual-exposure simultaneous readout | Real-time HDR preview | Sensor bandwidth doubles |

### 3.5 Architectural Differences from Qualcomm Spectra

| Comparison Dimension | Qualcomm Spectra 780 | MediaTek Imagiq 980 |
|---------------------|---------------------|---------------------|
| Tuning system | Chromatix (binary packages) | NDD + XML parameters |
| NR architecture | Hardware MFNR (fixed 4 frames) | FeaturePipe configurable frame count (4–8 frames) |
| AI integration depth | HTP (independent NPU) + ISP separated | APU directly participates in ISP nodes |
| Software openness | CamX-CHI (OEM requires Qualcomm-authorized toolchain) | FeaturePipe plugins (relatively more open) |
| HDR approach | Software HDR+ (multi-frame post-processing) | Hardware Staggered HDR (real-time) |
| Power characteristics | ISP power ~1.2–1.8 W (estimated) | ISP + APU co-processing, dynamic power management |

---

## §4 Apple ISP (A-Series Chips)

### 4.1 Deep-Coupled Architecture: ISP and Neural Engine Are Inseparable

The core design philosophy of Apple's ISP, and its greatest difference from Qualcomm/MediaTek, is **vertical hardware-software integration**: Apple simultaneously designs the SoC, the operating system (iOS), the camera application (Camera.app), and the sensor firmware. The data path between the ISP and the Neural Engine (NE) is a proprietary hardware bus that does not pass through the general memory bus.

A17 Pro (iPhone 15 Pro, 2023) ISP specifications (source: Apple WWDC 2023):
- Neural Engine: 35 TOPS (INT8, Apple official)
- Real-time ML inference: 3 simultaneous real-time ML models running during 4K ProRes recording
- Secure Enclave direct connection: Face ID depth maps (LiDAR/structured-light point clouds) complete biometric feature extraction before entering main memory; raw depth data never leaves the Secure Enclave

### 4.2 ProRes 4K Video Recording

The iPhone 13 Pro (2021) was the first iPhone to support Apple ProRes video recording, which requires a dedicated hardware ProRes encoder on-chip:

| Device | Maximum ProRes Specification | Internal Storage Requirement |
|--------|------------------------------|------------------------------|
| iPhone 13 Pro | 4K@30fps ProRes (256 GB and above) | ~6 GB/min |
| iPhone 14 Pro | 4K@30fps ProRes (all capacities) | — |
| iPhone 15 Pro | 4K@60fps ProRes + Log encoding | ~12 GB/min |

ProRes encoder characteristics: ProRes is a lossless/near-lossless compression format (~13–14 bits per pixel), requiring the encoder to sustain approximately 2–3 GB/s of real-time write bandwidth. Apple chose to integrate the ProRes encoder within the ISP subsystem rather than relying on the general-purpose video encoding engine (VideoToolbox), ensuring low-latency real-time encoding even at 4K 60 fps.

### 4.3 Always-On ISP (Sub-ISP Power-Saving Design)

Apple A-series SoCs contain an independent low-power sub-ISP responsible for the camera viewfinder (live preview stream):

- **Main ISP:** Handles still capture/video recording; high performance, high power, wakes on demand
- **Sub-ISP (Always-On ISP):** Maintains the viewfinder preview, running at ~60–120 MHz with power consumption < 100 mW
- The separated design allows maintaining a real-time preview without waking the large main ISP, extending battery life

### 4.4 Secure Enclave and Biometric Integration

Face ID (facial recognition) depth processing flow:

```
IR dot projector → IR sensor array → Dedicated depth processing hardware
                                            │
                                            ▼  (direct connection; bypasses main memory)
                                    Secure Enclave
                                    (biometric template matching)
                                            │
                                            ▼
                                  Pass / Reject result (1-bit output)
```

The raw depth map data (IR dot image) is processed entirely within the Secure Enclave and destroyed upon completion; it is never exposed to the iOS operating system or any application. This requires, at the engineering level, a **hardwired dedicated channel** from the depth sensor to the Secure Enclave within the ISP — a security guarantee that software-only ISP implementations cannot achieve.

### 4.5 Competitive Advantages of Apple's ISP

The engineering advantages of vertical integration go beyond specification numbers:

1. **Cross-layer optimization:** The iOS camera API (AVFoundation) can precisely control ISP timing; the "burst priority frame" selection algorithm in Camera.app communicates directly with the ISP frame buffer, without a generic HAL intermediary layer
2. **System-level denoising:** Photonic Engine (introduced 2022) accesses both RAW frames and neural network semantic features simultaneously, completing ML-guided denoising before RAW-to-RGB conversion — a quality that depends on the low-latency private bus between the ISP and the Neural Engine
3. **Power efficiency:** AnandTech 2023 testing shows A17 Pro camera recording power (~3.2 W) is lower than comparable Snapdragon 8 Gen 2 devices (~4.1 W) at similar image quality

---

## §5 Custom AI-ISP Chips

### 5.1 OPPO MariSilicon X

OPPO MariSilicon X (released 2021) is the first independent AI-ISP co-processor specifically designed for smartphone cameras, working in parallel alongside the main SoC (Snapdragon 888):

| Specification | MariSilicon X |
|---------------|---------------|
| Process node | 6 nm EUV (TSMC) |
| NPU throughput | 18 TOPS (INT8, OPPO official, dedicated to image AI) |
| Memory bandwidth | Independent LPDDR5 interface (peak bandwidth 51.2 GB/s) |
| Video capability | 4K AI video denoising @30fps real-time |
| Display output | Full HDR video chain (capture → processing → display) |
| 5K video | 5K@30fps (beyond 4K standard) |

The key innovation of MariSilicon X is its **private LPDDR5 interface**: the main SoC's DRAM bandwidth (LPDDR5 ~44 GB/s) is contested by GPU, CPU, display, Wi-Fi, AI, and other subsystems — during peak capture periods, AI-ISP receives only approximately 10–15 GB/s of effective bandwidth. MariSilicon X includes a dedicated LPDDR5 channel used exclusively for image AI processing, eliminating bandwidth contention.

### 5.2 vivo V2 Chip

The vivo V2 (2022, used in the X80 Pro) is another dedicated AI-ISP co-processor:

| Specification | vivo V2 |
|---------------|---------|
| Process node | 6 nm |
| Core function | Real-time AI denoising, HDR video processing |
| Slow-motion assistance | Extreme 7680fps slow-motion auxiliary compute |
| On-chip memory | Integrated SRAM cache (reduces DRAM access) |
| Primary partner SoCs | Snapdragon 8 Gen 1 / Dimensity 9000 |

The primary role of V2 is **real-time video AI denoising**: the Snapdragon/Dimensity main SoC's ISP is already near its bandwidth ceiling when recording 4K HDR video; V2 acts as a bypass processing unit that receives the ISP's output YUV video stream, applies AI denoising, and writes the result back — while the main SoC handles only encoding and compression.

### 5.3 Samsung Exynos ISP (Exynos 2400)

The Samsung Exynos 2400 (2023, with integrated Exynos ISP) features:

- **ISP integration:** The ISP is fully integrated in the Exynos SoC and not offered as a standalone chip, unlike the OPPO/vivo approach
- **NPU acceleration:** The Exynos 2400 NPU reaches ~34.7 TOPS (MCD NPU, INT8; Samsung official), supporting AI super-resolution and AI denoising
- **ISOCELL compatibility:** The Exynos ISP is specifically designed with a driver layer for ISOCELL Gen 3 sensors (Adaptive Pixel, switching between full-pixel and multi-pixel binning modes), supporting seamless switching between high-resolution pixel modes (Nona, Nonapixel)

### 5.4 Cross-Platform Comparison of Major Platforms

| Platform | NPU Throughput | Max Still Resolution | 8K Video | Dedicated AI Bandwidth | Signature Feature |
|---------|---------------|---------------------|---------|----------------------|------------------|
| Snapdragon 8 Gen 3 Spectra 800 | ~34 TOPS (third-party est.) | 200 MP | Yes, 8K30 | No (shared LPDDR5) | Real-time semantic NR, AI SR |
| Snapdragon 8 Elite Spectra 1080 | ~49 TOPS (third-party est.) | 320 MP | Yes, 8K30 | No (shared LPDDR5T) | Triple ISP 20-bit, AI Super Res, on-device generative editing |
| Dimensity 9300 Imagiq 980 | 33 TOPS (APU 790, MediaTek official) | 320 MP | Yes, 8K30 | No (shared LPDDR5) | Staggered HDR, AI-AWB |
| Dimensity 9400 Imagiq 990 | ~50 TOPS (APU 890, estimated, non-official integer) | 320 MP+ | Yes, 8K30 | No (shared LPDDR5T) | Quad ISP parallel, INT4 native acceleration |
| Apple A17 Pro ISP | 35 TOPS (Apple official) | — | No (4K max) | Yes (private bus) | Photonic Engine, ProRes 4K60 |
| Apple A18 Pro ISP | 35 TOPS (Apple official) | — | No (4K max) | Yes (private bus) | Camera Control, 4K@120fps, Visual Intelligence |
| OPPO MariSilicon X | 18 TOPS (OPPO official) | — | No (auxiliary) | Yes (independent LPDDR5) | Dedicated AI NR, 5K video |
| vivo V2 | ~6 TOPS (estimated) | — | No (auxiliary) | Integrated SRAM | Real-time video NR, 7680fps assist |
| Exynos 2400 integrated ISP | ~34.7 TOPS (Samsung official) | 200 MP | Yes, 8K30 | No (shared) | AI SR, ISOCELL adaptation |

> **Note:** TOPS (Tera Operations Per Second) figures are not directly comparable across vendors due to differences in operation definitions and precision (INT8/INT4/FP16). The table above is for cross-platform reference only.

---

## §6 Code: ISP Benchmark Simulation

Companion notebook: *See §6 Code section for runnable examples.*

### 6.1 Notebook Content Overview

The notebook uses Python to simulate equivalent ISP operation processing latency and memory bandwidth requirements under different hardware models, without relying on real chips, with the goal of quantifying the impact of architectural choices on system performance.

**Cell 1: Basic ISP operation latency modeling**

```python
import numpy as np
import time

# Simulate Bayer RAW images at different resolutions
resolutions = {
    "4K": (3840, 2160),
    "8K": (7680, 4320),
    "200MP": (16000, 12500),
}

def simulate_demosaic_latency(h, w, hardware_mpps):
    """
    hardware_mpps: hardware ISP throughput in megapixels/second (Mpix/s)
    """
    total_pixels = h * w
    latency_ms = (total_pixels / 1e6) / hardware_mpps * 1000
    return latency_ms

# Spectra 780 estimated throughput (~2000 Mpix/s peak)
spectra_mpps = 2000
imagiq_mpps = 2200  # Dimensity 9300 estimate (including APU acceleration)

for name, (h, w) in resolutions.items():
    lat_spectra = simulate_demosaic_latency(h, w, spectra_mpps)
    lat_imagiq = simulate_demosaic_latency(h, w, imagiq_mpps)
    print(f"{name}: Spectra={lat_spectra:.1f}ms, Imagiq={lat_imagiq:.1f}ms")
```

**Cell 2: MFNR memory bandwidth requirements analysis**

```python
def mfnr_bandwidth(h, w, bpp, fps, num_frames):
    """Compute required memory bandwidth for MFNR (GB/s)"""
    pixels_per_frame = h * w
    bytes_per_frame = pixels_per_frame * bpp / 8
    # Read num_frames frames + write 1 merged result frame
    total_bytes_per_capture = bytes_per_frame * (num_frames + 1)
    # fps represents captures per second (burst scenario)
    bw_gbps = total_bytes_per_capture * fps / 1e9
    return bw_gbps

scenarios = [
    ("4K 30fps MFNR-4", 2160, 3840, 12, 30, 4),
    ("200MP single MFNR-4", 12500, 16000, 12, 1, 4),
    ("8K 30fps MFNR-4", 4320, 7680, 12, 30, 4),
]

for name, h, w, bpp, fps, nf in scenarios:
    bw = mfnr_bandwidth(h, w, bpp, fps, nf)
    print(f"{name}: {bw:.2f} GB/s")
```

**Cell 3: Theoretical SNR improvement vs. frame count**

```python
import matplotlib.pyplot as plt

frames = np.arange(1, 17)
snr_gain_db = 10 * np.log10(frames)  # 10*log10(N)

plt.figure(figsize=(8, 4))
plt.plot(frames, snr_gain_db, 'b-o', label='Theoretical SNR gain (dB)')
plt.axhline(y=6.02, color='r', linestyle='--', label='4 frames: +6.02 dB')
plt.axhline(y=9.03, color='g', linestyle='--', label='8 frames: +9.03 dB')
plt.xlabel('Number of merged frames N')
plt.ylabel('SNR gain (dB)')
plt.title('MFNR theoretical SNR gain vs. frame count')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig('mfnr_snr_gain.png', dpi=150)
```

**Cell 4: Power-performance trade-off visualization for different architectures**

A Python-generated radar chart compares Spectra / Imagiq / Apple ISP / MariSilicon X across five dimensions — resolution, AI throughput, power efficiency, software ecosystem, and dedicated bandwidth — with relative scores. Implementation details are provided in the notebook comments.

---

## §7 References

1. Qualcomm. *Snapdragon 8 Gen 2 Mobile Platform: Product Brief*. Qualcomm Technologies, Inc., 2022. [Public white paper]
2. Qualcomm. *Spectra ISP Architecture Overview — Hot Chips 34*. 2022. [IEEE Hot Chips public presentation]
3. MediaTek. *Dimensity 9300: Imagiq 980 ISP Technical Overview*. MediaTek Inc., 2023. [Official press release and technical documentation]
4. Apple Inc. *WWDC 2023 Session 102: What's New in Camera Capture*. developer.apple.com, 2023. [Public developer documentation]
5. Apple Inc. *WWDC 2022 Session 110429: Discover advancements in iOS camera capture*. 2022. [Public developer documentation]
6. OPPO. *MariSilicon X: The World's First Smartphone Imaging NPU*. OPPO Official, 2021. [Official technical documentation]
7. vivo. *V2 Imaging Chip: Technical Overview*. vivo Official, 2022. [Official press release]
8. Samsung. *Exynos 2400 Official Specifications*. Samsung Semiconductor, 2023. [Official specifications page]
9. AnandTech. *Qualcomm Snapdragon 8 Gen 2 Deep Dive*. AnandTech, 2022. [Independent review]
10. Xia X. et al. *Semantic-Guided Multi-Frame ISP for Mobile Devices*. CVPR Workshop on AI for Image Quality, 2023. [Academic reference]

---

## §8 Glossary

| Term | Full Name / Explanation |
|------|------------------------|
| **Spectra ISP** | Qualcomm's dedicated ISP integrated in Snapdragon SoCs, iterating through Spectra generations (380 → 780 → 800) |
| **Imagiq** | MediaTek's ISP subsystem brand integrated in Dimensity SoCs; current flagship is Imagiq 980 |
| **CamX-CHI** | Camera eXtension / Camera HAL Interface; Qualcomm's two-layer camera software framework architecture |
| **FeaturePipe** | MediaTek Camera HAL's pipeline engine that describes algorithm nodes as a DAG, supporting plug-in extensibility |
| **MariSilicon** | OPPO's custom AI-ISP co-processor; MariSilicon X is the first commercial version (6 nm, 18 TOPS, OPPO official) |
| **MFNR** | Multi-Frame Noise Reduction; improves SNR by aligning and merging multiple RAW frames |
| **Hexagon DSP** | Qualcomm Snapdragon's digital signal processor, featuring HVX vector extensions for AI inference and media processing |
| **Chromatix** | Qualcomm's ISP tuning system; stores image quality parameters as multi-dimensional LUTs, dynamically indexed by the 3A state machine |
| **NDD** | Noise Distribution Data; MediaTek's sensor noise calibration data format |
| **APU** | AI Processing Unit; MediaTek's AI accelerator integrated in Dimensity SoCs; Dimensity 9300's APU 790 reaches 33 TOPS (MediaTek official); Dimensity 9400's APU 890 reaches ~50 TOPS (estimated, non-official integer) |
| **Neural Engine** | Apple's dedicated AI accelerator in A-series SoCs; reaches 35 TOPS (Apple official) in A17 Pro; A18 Pro also 35 TOPS (Apple official) |
| **Staggered HDR** | A hardware HDR capture mode with row-level alternating exposures within a single frame readout period; no multi-frame buffering required |
| **Secure Enclave** | Apple's independent secure processor within the chip; Face ID raw depth data is processed and destroyed here, never entering main memory |
| **ProRes** | Apple's professional video codec format; near-lossless compression; 4K ProRes recording supported from iPhone 13 Pro onward |
| **TOPS** | Tera Operations Per Second; the unit for AI compute throughput, typically referring to matrix multiply-accumulate throughput at INT8 precision |
