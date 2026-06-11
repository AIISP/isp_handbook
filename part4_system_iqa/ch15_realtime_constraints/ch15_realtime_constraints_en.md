# Part 4, Chapter 15: Real-Time ISP System Constraints: Latency, Buffer, and Power Budget

> **Scope:** This chapter covers real-time ISP engineering constraint analysis: end-to-end latency budget decomposition, memory bandwidth calculation, SoC power budget allocation, and the special challenges of real-time AI ISP.
> **Prerequisites:** Volume 1, Chapter 10 (ISP SoC Hardware Architecture); Volume 4, Chapter 1 (3A Control System)
> **Reader path:** Systems engineers, embedded engineers

---

## §1 Theory and Principles

### 1.1 Engineering Constraint Framework for Real-Time ISP

A real-time ISP system must simultaneously satisfy three classes of hard constraints (硬性约束):

1. **Latency budget (延迟约束):** The upper bound on end-to-end latency from photon hitting the sensor to pixel display/storage. For electronic viewfinders (EVF/preview, 取景器), the requirement is < 50 ms; for XR headsets it is < 20 ms; for machine vision it is < 5 ms.
2. **Memory bandwidth budget (内存带宽约束):** Total ISP read/write DDR bandwidth must not exceed the bandwidth ceiling allocated to the ISP subsystem by the SoC (typically 10–30 GB/s).
3. **Power budget (功耗预算约束):** Total ISP + camera system power must not exceed the Thermal Design Power (TDP, 热设计功耗) allocation. Smartphones typically allow 1–3 W when the camera is active.

These three constraint classes are mutually constraining: lower latency often requires more compute resources (higher power), higher resolution/frame rate increases bandwidth pressure, and stronger AI processing (NPU compute) increases power consumption.

### 1.2 End-to-End Latency Budget Decomposition

**Full ISP pipeline latency nodes:**

```
Light → Sensor exposure → Sensor readout → MIPI transmission → ISP hardware processing → Memory write
     → Post-processing (CPU/GPU/NPU) → Encoding (if needed) → Display/storage
```

Physical root causes of latency at each node:

| Latency node | Formula | Typical value |
|-------------|---------|---------------|
| Sensor exposure | = shutter speed, determined by AE | 1–33 ms (1/1000 s – 1/30 s) |
| Sensor readout (line readout) | $T_{readout} = H_{active} / f_{line}$ | 5–20 ms (Rolling Shutter) |
| MIPI transmission | $T_{MIPI} = W \times H \times BPP / BW_{MIPI}$ | 0.2–1 ms |
| ISP hardware (pipeline) | Approximately 1 frame time (when pipeline is fully loaded) | 16.7 ms @ 60 fps |
| DDR write | = ISP output data volume / DDR bandwidth | 0.5–2 ms |
| CPU/GPU post-processing | Depends on algorithm complexity | 0–10 ms |
| Encoding (H.264/H.265) | Depends on bitrate and hardware capability | 5–15 ms |
| Display scan-out | Approximately 1 frame time (worst case) | 11–16 ms |

**Key insight:** The sensor **readout time** (Rolling Shutter scan time) is typically the largest fixed latency in the pipeline, not the exposure time itself (since downstream processing can begin on the first lines while the exposure is still in progress).

### 1.3 Memory Bandwidth Calculation Model

ISP memory bandwidth demand consists of two parts: **read bandwidth** (reading RAW data, parameter LUTs) and **write bandwidth** (writing processed results).

**Basic bandwidth formula:**
$$BW_{ISP} = W \times H \times FPS \times BPP_{in} \times (1 + r_{overhead})$$

where $r_{overhead}$ is the additional read/write overhead coefficient (denoising requires reading previous frames, multi-frame fusion requires reading history frames, etc.), with typical values of 1.2–2.5.

**Typical scenario calculations:**

| Scenario | Resolution | Frame rate | Bit depth | Read BW | Write BW | Notes |
|----------|-----------|-----------|-----------|---------|----------|-------|
| Preview (primary) | 1920×1080 | 60 fps | 10 bit | 1.2 GB/s | 0.8 GB/s | — |
| Photo (primary) | 8192×6144 | 10 fps | 10 bit | 5.0 GB/s | 3.3 GB/s | Burst bandwidth |
| Video 4K@60 | 3840×2160 | 60 fps | 10 bit | 2.5 GB/s | 1.7 GB/s | Includes TNR previous-frame read |
| 4-camera simultaneous preview | 1920×1080×4 | 30 fps | 10 bit | 2.4 GB/s | 1.6 GB/s | Multi-pipeline ISP |

**LPDDR5 bandwidth ceiling (typical SoC):** LPDDR5-6400 dual-channel provides approximately 102 GB/s total bandwidth (lower-spec variants start from ~60 GB/s); the ISP subsystem is typically allocated 10–20 GB/s.

### 1.4 ISP Pipeline Depth and Throughput

**Pipeline principle:** Modern hardware ISPs use deep pipeline designs (depth typically 12–20 stages), each stage processing one line (Line Buffer, 行缓存 architecture) or one block of data. Through pipeline overlap, **steady-state throughput = 1 frame per frame time**, independent of pipeline depth.

**Pipeline latency:** The minimum time from when the first pixel enters the queue to when the first pixel exits:
$$T_{pipeline\_latency} = N_{stages} \times T_{stage}$$

This is typically tens to hundreds of microseconds — small compared to frame time (16.7 ms @ 60 fps).

**Line Buffer memory requirement:** A 3×3 filter requires 3 line buffers; a 5×5 requires 5; large-kernel filters such as NLM require more:
$$Mem_{LineBuffer} = K_{height} \times W \times BPP \quad \text{(bytes)}$$

### 1.5 Power Budget Allocation Model

SoC power is shared among multiple subsystems within a total TDP (Thermal Design Power):

$$P_{total} = P_{CPU} + P_{GPU} + P_{NPU} + P_{ISP} + P_{DRAM} + P_{Camera} + P_{others}$$

Typical smartphone power budget (everyday photography scenario):
- **Camera module (Sensor + MIPI):** 200–500 mW
- **ISP hardware:** 150–400 mW
- **NPU (AI denoising/SR):** 300–800 mW
- **DRAM access:** 200–400 mW
- **Total ISP-related:** 850–2100 mW

Thermal limit (mobile): sustained power typically must not exceed 2–3 W, otherwise thermal throttling (热降频) is triggered.

---

## §2 Algorithm Methods and System Architecture

### 2.1 Low-Latency ISP Design Architecture

**Low-latency ISP design strategies:**

1. **Pipeline parallelism (流水线并行):** ISP modules (BLC → Demosaic → NR → CCM → Gamma) are connected in a serial pipeline; each module passes processed data to the next as soon as one line is complete, without waiting for the full frame.
2. **Double buffering (双缓冲):** ISP output and CPU/GPU readback use two ping-pong buffers, avoiding waiting latency from read/write contention.
3. **Internal SRAM cache:** Cache frequently-accessed LUTs (LSC gain table, Gamma curve, Demosaic coefficients) in ISP-internal SRAM, avoiding per-line DDR accesses.

### 2.2 Special Challenges of Real-Time AI ISP

**Traditional ISP vs. AI ISP latency comparison:**

| Metric | Traditional hardware ISP | AI ISP (NPU) | Hybrid ISP |
|--------|-------------------------|--------------|------------|
| Processing latency | < 2 ms (hardware pipeline) | 10–50 ms (NPU inference) | 3–8 ms |
| Maximum frame rate | 120 fps+ | 15–30 fps | 60 fps |
| Power | Low (0.15–0.4 W) | High (0.3–1.0 W) | Medium |
| Flexibility | Low (hardware-fixed) | High (software-updatable) | Medium |

**AI ISP real-time solutions:**
- **Asynchronous NPU processing (NPU异步处理):** The NPU processes frame n while the ISP continues processing frame n+1; NPU results are applied with a 1–2 frame delay (suitable for non-real-time preview enhancement)
- **Model lightweighting (模型轻量化):** Use INT8 quantization, model pruning to reduce NPU inference to < 5 ms
- **Early exit mechanism (早退出机制):** Dynamically select a lightweight/standard model based on scene complexity, reducing average power by 30–50%

### 2.3 Memory Bandwidth Optimization Techniques

**Technique 1: Tile Compression (块压缩)**
Apply lossless/near-lossless compression (e.g., ARM AFBC format) to internal ISP data streams, reducing DDR read/write volume:
$$BW_{compressed} = BW_{raw} \times CR_{ratio}, \quad CR_{ratio} \approx 0.4\text{–}0.6$$

**Technique 2: ROI Processing (Region of Interest Processing, 感兴趣区域处理)**
Apply high-precision processing only to regions of interest (e.g., AF detection boxes, face regions); reduce precision elsewhere, saving 25–50% bandwidth.

**Technique 3: Resolution-Tiered Processing (分辨率分层处理)**
Downscale the viewfinder preview to 720p for processing (saving bandwidth); switch to full resolution when capturing a photo.

### 2.4 Power Management Strategies

**Dynamic Voltage and Frequency Scaling (DVFS, 动态电压频率调整):** Dynamically adjust ISP clock frequency based on ISP load (e.g., Qualcomm ISP supports 100 MHz–600 MHz scaling), saving power at low frame rates/low resolutions.

**Camera wake-up strategy (摄像头唤醒策略):** In a multi-camera system, wake only the camera currently in use; keep other cameras in low-power STANDBY state, saving 200–400 mW per camera.

**ISP submodule on/off (ISP子模块开关):** During video preview, disable photo-specific noise enhancement modules (saving 50–100 mW); disable the encoder for viewfinder-only use cases.

### 2.5 Frame Sync and Precise Latency Control

**Frame alignment mechanism (帧对齐机制):** Via the SoC's internal Frame Sync Bus, ensure ISP output frames align with the display VSYNC, preventing tearing artifacts.

**Timestamp precision:** ISP hardware stamps each frame with the SoC system clock (typically 19.2 MHz or 38.4 MHz), with a time resolution of approximately 26–52 ns — far exceeding the frame interval (16.7 ms @ 60 fps).

---

## §3 Tuning and Engineering Guidelines

### 3.1 Latency Budget Decomposition Table (Engineering Template)

**Photo capture scenario (50 MP, 10 fps):**

| Stage | Latency (ms) | Optimizable? | Optimization method |
|-------|-------------|-------------|---------------------|
| AE/AF computation (previous frame) | 16.7 | No (within one frame) | — |
| Sensor exposure | 5–30 | Partially | Use short exposure when scene is bright enough |
| Sensor readout | 50 ms (~50 MP) | No (sensor-fixed) | — |
| MIPI transmission | 0.5 | No | — |
| ISP processing (BLC → output) | 50 ms (overlaps with readout) | Overlapped | Pipeline parallelism |
| DDR write (JPEG buffer) | 2 | No | — |
| JPEG encoding | 10–30 | Yes | Hardware encoder, parallel compression |
| **Storage write (UFS/NVMe)** | 20–80 | Yes | High-speed UFS 3.1/4.0 |
| **Photo total latency** | **~120–200 ms** | — | Perceived: shutter to thumbnail display |

**Video preview scenario (4K@60 fps):**

| Stage | Latency (ms) | Notes |
|-------|-------------|-------|
| Sensor exposure | 1/60 = 16.7 | Overlaps with readout |
| Sensor readout | 16.7 | Full-frame scan |
| MIPI transmission | 0.3 | — |
| ISP processing | 16.7 (pipeline, overlaps with next frame) | Steady-state latency = 1 frame |
| Display driver | 5–10 | DDIC processing + scan-out |
| **Preview total latency** | **~50–60 ms** | Acceptable for normal viewfinder |

### 3.2 Memory Bandwidth Alert Thresholds

When ISP bandwidth demand exceeds 80% of the allocated ceiling, bandwidth optimization measures must be activated:

```
BW_ISP_utilization = BW_measured / BW_allocated
if BW_ISP_utilization > 0.8:
    → Enable AFBC compression
    → Reduce auxiliary camera resolution
    → Reduce TNR buffer frame count
if BW_ISP_utilization > 0.95:
    → Limit frame rate (60 fps → 30 fps)
    → Disable high-resolution auxiliary camera
```

### 3.3 Power-Performance Tuning Strategy

**Scene-adaptive power control (场景自适应功耗控制):**
- Static viewfinder (stable hand-held, low inter-frame difference): reduce ISP refresh rate (60 fps → 30 fps), lowering power by 40%
- High-motion capture (large inter-frame difference): maintain high frame rate to ensure AE/AF responsiveness
- Night mode: disable real-time preview enhancement; dedicate all NPU resources to multi-frame merging to avoid resource contention

**Thermal throttling protection:** When SoC core temperature exceeds 45°C, progressively reduce ISP clock frequency to prevent sudden frame-rate drops (which may be perceived as stuttering). Recommend a 4-level thermal management scheme:
- T < 40°C: Normal operation
- 40°C ≤ T < 45°C: Warning; reduce NPU frequency
- 45°C ≤ T < 50°C: Reduce ISP + NPU frequency; limit maximum resolution
- T ≥ 50°C: Limit frame rate to 15 fps; disable auxiliary cameras

### 3.4 AI ISP Latency Optimization in Practice

**Problem scenario:** An AI denoising model (UNet-type) requires 25 ms/frame for NPU inference; at 4K@30 fps (33 ms/frame), real-time processing is infeasible.

**Solutions:**
1. **Resolution proxy (分辨率代理):** NPU infers at 1080p (7 ms); outputs a Guidance Map used for full-resolution bilateral filtering; total time < 10 ms.
2. **Temporal frame skipping (时域跳帧):** NPU processes 1 out of every 2 frames; intermediate frames are extrapolated via motion compensation; effective processing rate 12.5 fps → equivalent 30 fps output.
3. **Quantization compression (量化压缩):** FP16 → INT8 quantization improves NPU inference speed by 1.8× (requires NAS re-training to recover quantization precision loss).

---

## §4 Common Artifacts and Problem Analysis

### 4.1 Frame Rate Jitter (帧率抖动)

**Symptom:** Preview video frame rate is unstable; occasional excessively long frame intervals (perceived as stuttering).
**Root cause:** ISP processing or NPU inference occasionally exceeds the frame time budget, delaying the next frame.
**Diagnosis:** Capture frame time distribution using `adb shell dumpsys media.camera` or Android Systrace; check whether P99 latency is out of spec.
**Fix:** Set FIFO scheduling priority for ISP/NPU; reduce CPU/bandwidth contention with background tasks.

### 4.2 Memory Bandwidth Contention Causing Frame Drops (内存带宽竞争导致的帧丢失)

**Symptom:** Under heavy load (simultaneous video recording + live streaming + AI beautification), the frame drop rate rises.
**Root cause:** Multiple subsystems (ISP, GPU, CPU, encoder) simultaneously compete for DDR bandwidth; ISP memory access times out.
**Diagnosis:** Use SoC vendor bandwidth monitoring tools (Qualcomm QPST, MTK APTool) to measure actual bandwidth usage per module.
**Fix:** Configure QoS (Quality of Service, 服务质量) priorities with ISP at the highest priority; or throttle background task DDR access.

### 4.3 Rolling Shutter Jello Effect (果冻效应)

**Symptom:** Rapidly moving objects in video appear skewed or wavy (especially during lateral camera panning).
**Root cause:** CMOS sensors read out line by line (Rolling Shutter); during the readout time (approximately 5–20 ms) the scene has already moved.
**Quantification:** $Skew = V_{motion} \times T_{readout}$ (pixels); typical value 10–30 px (1080p, fast panning).
**Mitigation:** Global Shutter (全局快门) sensor (synchronous readout, no skew); EIS (Electronic Image Stabilization, 电子防抖) partially corrects via motion compensation; reduce readout time (high-speed sensor).

### 4.4 Thermal Throttling from Excessive Power (功耗过高导致热降频)

**Symptom:** During prolonged (> 5 minutes) continuous video recording, frame rate gradually drops from 60 fps to 30 fps or even 15 fps.
**Root cause:** ISP + NPU + encoder under sustained high load; SoC temperature exceeds the thermal limit, triggering automatic throttling protection.
**Monitoring:** `adb shell cat /sys/class/thermal/thermal_zone*/temp` to monitor temperatures across thermal zones.
**Optimization:** Reduce NPU workload on non-critical paths (e.g., AI beautification can run at lower precision during video recording); improve thermal design (graphene thermal pads).

### 4.5 ISP Pipeline Stall (ISP流水线停顿)

**Symptom:** ISP output frames occasionally show partial data anomalies (all-black lines or repeated lines).
**Root cause:** ISP Line Buffer cannot fetch data from DDR quickly enough (insufficient DDR bandwidth burst), causing pipeline stall and garbled output.
**Diagnosis:** Check the ISP hardware's overflow/underflow counters to confirm whether Line Buffer overflow events are recorded.

---

## §5 Evaluation Methods

### 5.1 End-to-End Latency Measurement

**Method 1 (LED + high-speed camera):** Synchronize an LED with a phone control signal; a high-speed camera (> 500 fps) captures LED on/off and screen changes, with accuracy of approximately ±2 ms.

**Method 2 (software timestamps):** Inject timestamps at the HAL layer; analyze per-node latency distribution via `atrace` or `systrace`; suitable for engineering root-cause analysis.

**Method 3 (Android CameraX API):** `CaptureResult.SENSOR_TIMESTAMP` records sensor timestamps; compare with display timestamps to measure full-pipeline latency.

### 5.2 Memory Bandwidth Measurement

Use SoC vendor PMU (Performance Monitoring Unit, 性能监控单元) counters:
- Qualcomm: `adb shell cat /sys/bus/platform/drivers/msm_bus/...`
- MTK: `adb shell perfmonitor start`
- Universal: Android `BandwidthInfo` API (Android 12+)

### 5.3 Power Measurement

- **Hardware power meter:** Series-connect a precision resistor or power analyzer (e.g., Monsoon M600) in the camera power supply line to directly measure current.
- **Software estimate:** `adb shell cat /sys/class/power_supply/battery/current_now` (accuracy ±50 mA).
- **SoC internal power sensor:** Qualcomm DCVS (Dynamic Clock and Voltage Scaling, 动态电压频率调整) framework provides subsystem power estimates.

### 5.4 Frame Rate Stability (Jitter Evaluation)

Continuously capture 300 frames; compute statistical distribution of inter-frame intervals:
- $T_{mean}$: Mean inter-frame interval (target value = 1/FPS)
- $T_{p99}$: 99th percentile inter-frame interval (acceptance criterion: < 2 × $T_{mean}$)
- $T_{max}$: Maximum inter-frame interval (acceptance criterion: < 3 × $T_{mean}$)

---

## §6 Code Examples

### 6.1 ISP Latency Budget Calculation Tool

```python
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np

@dataclass
class ISPStage:
    """Latency description for a single processing stage in the ISP pipeline."""
    name: str
    latency_ms: float
    parallel_with_prev: bool = False  # Whether this stage runs in parallel with the previous one
    optional: bool = False            # Whether this stage can be disabled
    power_mw: float = 0.0             # Power consumption of this stage (mW)

def compute_pipeline_latency(stages: List[ISPStage]) -> dict:
    """
    Compute total ISP pipeline latency (respecting parallel relationships).

    Returns:
        {'total_ms': float, 'critical_path': List[str], 'power_mw': float}
    """
    total_latency = 0.0
    total_power = 0.0
    critical_path = []

    for i, stage in enumerate(stages):
        if stage.parallel_with_prev and i > 0:
            # Parallel stage: take the max of current and previous (do not add)
            prev_latency = stages[i-1].latency_ms
            extra = max(0, stage.latency_ms - prev_latency)
            total_latency += extra
        else:
            total_latency += stage.latency_ms
            critical_path.append(stage.name)
        total_power += stage.power_mw

    return {
        'total_ms': total_latency,
        'critical_path': critical_path,
        'power_mw': total_power
    }


def compute_bandwidth_requirement(
    width: int, height: int, fps: int, bpp: int,
    overhead_factor: float = 1.3
) -> dict:
    """
    Compute memory bandwidth requirement for a single ISP pipeline.

    Args:
        width, height: Image resolution
        fps: Frame rate
        bpp: Bits per pixel (RAW input)
        overhead_factor: Bandwidth overhead factor (TNR, fusion, extra reads/writes)

    Returns:
        {'read_gbps': float, 'write_gbps': float, 'total_gbps': float}
    """
    # Read bandwidth: raw RAW data
    read_bps = width * height * fps * bpp * overhead_factor
    # Write bandwidth: processed output (typically RGB24 or YUV420, lower effective bpp)
    output_bpp = 12  # YUV420 = 12 bpp
    write_bps = width * height * fps * output_bpp

    return {
        'read_gbps': read_bps / 1e9,
        'write_gbps': write_bps / 1e9,
        'total_gbps': (read_bps + write_bps) / 1e9
    }


# Video preview latency analysis example
preview_stages = [
    ISPStage("Sensor exposure",      16.7, parallel_with_prev=False, power_mw=400),
    ISPStage("Sensor readout",       16.7, parallel_with_prev=True,  power_mw=0),  # overlaps exposure
    ISPStage("MIPI transmission",     0.3, parallel_with_prev=False, power_mw=50),
    ISPStage("BLC + Demosaic",        0.5, parallel_with_prev=False, power_mw=80),
    ISPStage("NR denoising",          1.0, parallel_with_prev=False, power_mw=120),
    ISPStage("AWB + CCM + Gamma",     0.5, parallel_with_prev=False, power_mw=60),
    ISPStage("YUV encode output",     0.3, parallel_with_prev=False, power_mw=30),
    ISPStage("Display scan-out",     11.1, parallel_with_prev=False, power_mw=200),
]

result = compute_pipeline_latency(preview_stages)
print(f"\nVideo preview end-to-end latency analysis:")
print(f"  Total latency: {result['total_ms']:.1f} ms")
print(f"  Total power:   {result['power_mw']:.0f} mW")

# Bandwidth analysis
bw = compute_bandwidth_requirement(3840, 2160, 60, 10, overhead_factor=1.5)
print(f"\n4K@60fps ISP bandwidth requirement:")
print(f"  Read BW:  {bw['read_gbps']:.2f} Gbps")
print(f"  Write BW: {bw['write_gbps']:.2f} Gbps")
print(f"  Total BW: {bw['total_gbps']:.2f} Gbps")
```

### 6.2 Power Budget Allocation Optimizer

```python
from scipy.optimize import linprog
import numpy as np

def optimize_power_budget(
    total_budget_mw: float,
    modules: list,
    quality_weights: list,
    min_power: list,
    max_power: list
) -> np.ndarray:
    """
    Allocate power to maximize weighted image quality subject to a total
    power budget constraint.

    Args:
        total_budget_mw: Total power budget (mW)
        modules: List of module names
        quality_weights: Per-module power-quality gain weights
                         (higher = increasing power yields more quality improvement)
        min_power: Per-module minimum power (mW)
        max_power: Per-module maximum power (mW)

    Returns:
        allocated_power: Array of allocated power per module (mW)
    """
    n = len(modules)
    # Objective: maximize sum(quality_weights[i] * power[i])
    # linprog minimizes, so negate
    c = [-w for w in quality_weights]

    # Constraint: total power <= total_budget
    A_ub = [np.ones(n)]
    b_ub = [total_budget_mw]

    # Variable bounds
    bounds = list(zip(min_power, max_power))

    result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')

    if result.success:
        print(f"\nPower budget optimization result (total budget: {total_budget_mw} mW):")
        for name, power in zip(modules, result.x):
            print(f"  {name:20s}: {power:.0f} mW")
        print(f"  Actual total power: {sum(result.x):.0f} mW")
        return result.x
    else:
        print(f"Optimization failed: {result.message}")
        return np.array(min_power)


# AI ISP capability analysis
def analyze_ai_isp_capability(
    model_latency_ms: float,
    frame_time_ms: float,
    strategy: str = "async"
) -> dict:
    """
    Analyze AI ISP model real-time capability at a given frame rate.

    Args:
        model_latency_ms: AI model inference latency (ms)
        frame_time_ms: Target frame time (ms) = 1000/FPS
        strategy: 'sync' (must process every frame) | 'async' (frame skipping allowed)

    Returns:
        capability: Capability analysis result
    """
    if strategy == "sync":
        achievable = model_latency_ms <= frame_time_ms
        fps_capacity = 1000 / model_latency_ms
        skip_factor = 1
    else:  # async: allow frame skipping, process 1 out of N frames
        skip_factor = np.ceil(model_latency_ms / frame_time_ms)
        fps_capacity = 1000 / frame_time_ms  # output frame rate unchanged
        achievable = True

    return {
        'achievable': achievable,
        'fps_capacity': fps_capacity,
        'skip_factor': skip_factor,
        'added_latency_ms': model_latency_ms
    }


if __name__ == "__main__":
    # Power optimization example
    optimize_power_budget(
        total_budget_mw=2000,
        modules=['Sensor', 'ISP_HW', 'NPU_Denoise', 'GPU_Preview', 'Encoder'],
        quality_weights=[1.0, 2.0, 3.5, 1.5, 1.0],
        min_power=[200, 150, 0, 100, 80],
        max_power=[500, 400, 800, 400, 200]
    )

    # AI ISP capability analysis
    cap = analyze_ai_isp_capability(
        model_latency_ms=25, frame_time_ms=33.3, strategy="async"
    )
    print(f"\nAI ISP capability analysis: {cap}")
```

### 6.3 Memory Bandwidth Monitoring Tool (Android ADB)

```python
import subprocess
import time
import re

def monitor_isp_bandwidth_android(duration_s: int = 10) -> list:
    """
    Monitor ISP memory bandwidth on an Android device via ADB
    (requires root or engineering mode).

    Returns:
        bandwidth_samples: List of samples, each {'time_s': float, 'bw_gbps': float}
    """
    samples = []
    cmd = "adb shell cat /sys/kernel/debug/bw_hwmon/*/mbps"

    for i in range(duration_s * 2):  # 500 ms sampling interval
        try:
            result = subprocess.run(
                cmd.split(), capture_output=True, text=True, timeout=2
            )
            mbps_values = [
                float(v) for v in result.stdout.strip().split('\n')
                if v.strip().replace('.', '').isdigit()
            ]
            if mbps_values:
                total_gbps = sum(mbps_values) / 1000.0
                samples.append({
                    'time_s': i * 0.5,
                    'bw_gbps': total_gbps
                })
        except Exception:
            pass
        time.sleep(0.5)

    if samples:
        bw_values = [s['bw_gbps'] for s in samples]
        print(f"Bandwidth statistics ({duration_s}s):")
        print(f"  Mean: {np.mean(bw_values):.2f} Gbps")
        print(f"  Peak: {np.max(bw_values):.2f} Gbps")
        print(f"  P95:  {np.percentile(bw_values, 95):.2f} Gbps")

    return samples
```

---

## References

1. Qualcomm Technologies. (2023). "Snapdragon 8 Gen 3 Camera and ISP Architecture." Technical White Paper.
2. ARM Ltd. (2022). "LPDDR5X Memory Bandwidth Optimization for Mobile SoC." ARM Developer Documentation.
3. MIPI Alliance. (2022). "MIPI CSI-2 Specification v4.0." MIPI Alliance.
4. Zhang, L., et al. (2021). "Real-time AI ISP: Challenges and Solutions for Mobile Deployment." *arXiv:2111.09736*.
5. Chen, C.H., et al. (2019). "Camera Pipeline Latency Analysis for Augmented Reality." *IEEE VR 2019*.
6. Heide, F., et al. (2014). "FlexISP: A Flexible Camera Image Processing Framework." *ACM SIGGRAPH Asia*.
7. Liu, J., et al. (2022). "NightHawk: ISP Pipeline Optimization for Low-Light Mobile Photography." *IEEE TCSVT*.
8. Google LLC. (2023). "Tensor G3: ISP Architecture for Pixel 8." Google AI Blog.
9. Apple Inc. (2022). "A16 Bionic: Neural Engine and ISP Architecture." Apple Silicon Platform.
10. MediaTek. (2023). "Dimensity 9300 Camera Architecture Technical Brief." MediaTek.

---

## §8 Glossary

| Term | Full Name | Meaning |
|------|-----------|---------|
| TDP | Thermal Design Power | Thermal design power; the baseline power rating for chip cooling design |
| DVFS | Dynamic Voltage and Frequency Scaling | Dynamically adjust voltage and frequency to balance performance and power |
| AFBC | ARM Frame Buffer Compression | ARM frame buffer compression; reduces DDR bandwidth |
| Rolling Shutter | — | Line-by-line sensor readout; causes the jello/skew effect on moving subjects |
| Global Shutter | — | Synchronous full-frame readout; no motion distortion |
| Line Buffer | — | Internal ISP buffer holding a few rows of pixels for pipeline processing |
| Double Buffering | — | Ping-pong buffer scheme to avoid read/write contention |
| QoS | Quality of Service | DDR access priority policy |
| PMU | Performance Monitoring Unit | Hardware performance counter unit |
| Thermal Throttling | — | Automatic performance reduction when temperature exceeds the thermal limit |
| ROI | Region of Interest | A sub-region processed at higher precision to save resources |
| TNR | Temporal Noise Reduction | Temporal denoising using inter-frame correlation |
| EVF | Electronic ViewFinder | Electronic viewfinder |
| Jitter | — | Frame interval instability |
