# Part 4, Chapter 22: ISP Power Optimization

> **Scope:** Power modeling, measurement, and tuning for ISP pipelines on mobile SoCs; engineering practice for real-time constraints and thermal throttling.
> **Prerequisites:** Volume 4, Chapter 12 (SoC Hardware Architecture), Volume 4, Chapter 15 (Real-Time Constraints)
> **Target readers:** BSP engineers, Camera system architects, power tuning engineers

> **⚠️ Note:** All data in this chapter are sourced from publicly available materials (Perfetto official documentation, Android AOSP source code, ARM public documentation, academic papers, and industry reports). No proprietary or NDA-protected information from any company is included. All example values are representative ranges drawn from publicly available teardown and benchmark reports.

---

## §1 Theory

### 1.1 CMOS Digital Circuit Power Model

The ISP is one of the largest power consumers in a mobile SoC. Its power dissipation follows the standard CMOS dynamic-static decomposition model:

$$P_\text{total} = P_\text{dynamic} + P_\text{static} + P_\text{short-circuit}$$

**Dynamic power (dominant, approximately 70–85%):**

$$P_\text{dynamic} = \alpha \cdot C_\text{eff} \cdot V_{DD}^2 \cdot f_\text{clk}$$

| Parameter | Description | Typical ISP Value |
|-----------|-------------|-------------------|
| $\alpha$ | Activity factor (switching rate, 0–1) | 0.05–0.20 (depends on algorithm complexity) |
| $C_\text{eff}$ | Effective switching capacitance | Process-dependent; 28nm ≈ 0.5–2 fF/gate |
| $V_{DD}$ | Core supply voltage | 0.65–0.9 V (DVFS range) |
| $f_\text{clk}$ | Clock frequency | IFE: 400–600 MHz, IPE: 300–500 MHz |

**Static power (leakage current):**

$$P_\text{static} = I_\text{leak} \cdot V_{DD}$$

In advanced process nodes (5nm/4nm), the proportion of static power increases. FinFET/GAA device leakage is approximately 20–40% that of 28nm.

**Key insight:** $V_{DD}$ has the greatest impact on power—a 10% voltage reduction yields approximately a 19% reduction in dynamic power (due to the $V^2$ relationship). This is the physical basis of DVFS power savings.

### 1.2 ISP Pipeline Power Distribution

Using the Qualcomm Spectra ISP (based on publicly available SNPE/CamX architecture documentation) as a reference, the ISP pipeline consists of three primary hardware blocks:

```
Sensor → MIPI CSI-2 → IFE → BPS → IPE → Display / Encode
                        ↕        ↕       ↕
                     CDSP/NPU  DDR5   Video
```

| Block | Primary Functions | Typical Share of Total ISP Power |
|-------|-------------------|----------------------------------|
| **IFE** (Image Front End) | Demosaic, BLC, LSC, AWB statistics | 30–40% |
| **BPS** (Bayer Processing Segment) | BPC, ABF denoising, PDAF | 20–30% |
| **IPE** (Image Processing Engine) | NR, EE, CSC, TNR | 30–40% |
| **DDR Bandwidth** (memory access) | Frame buffer read/write | 15–25% (counted separately in memory subsystem) |

> Reference: Qualcomm Snapdragon public architecture white paper (developer.qualcomm.com)

### 1.3 DVFS (Dynamic Voltage and Frequency Scaling)

DVFS is the most fundamental power-saving mechanism in mobile SoCs. ISP blocks typically have independent voltage/frequency operating point tables (VDD and CLK are adjusted jointly).

**Operating point example (based on publicly available Qualcomm documentation style):**

| Performance Level | Frequency Ratio | Voltage $V_{DD}$ | Relative Power |
|-------------------|-----------------|------------------|----------------|
| Turbo | 100% | 0.90 V | 1.00× |
| Nominal | 75% | 0.80 V | ~0.50× |
| SVS (Sustained Video Slow) | 50% | 0.72 V | ~0.22× |
| SVS_L1 | 33% | 0.65 V | ~0.10× |

**Runtime DVFS decision logic (CamX perf hint, public SDK documentation):**

```
High-frame-rate preview (60fps)   → Turbo
Standard preview (30fps)          → Nominal
Background video recording        → SVS
Thermal throttle triggered        → SVS_L1 or disable non-critical modules
```

**DVFS call path (Android kernel, AOSP open source):**
```
Camera HAL → CamX PerfLock → KMD (kernel mode driver) → CPUFreq/DevFreq → PMIC
```

### 1.4 Clock Gating and Power Gating

**Clock Gating:**

The module clock is disabled in two situations to eliminate switching power:

1. **Blanking-interval gating:** The module clock is disabled during intervals when no pixels are being processed (horizontal blanking interval HBI, vertical blanking interval VBI):

$$E_\text{saved} = P_\text{dynamic} \cdot t_\text{blanking}$$

For a 4K 30fps scenario:
- Horizontal blanking (HBI) accounts for approximately 20–30% of total time
- Vertical blanking (VBI) accounts for approximately 5–10% of total time
- Combined, clock gating can save approximately 25–40% of dynamic power

2. **Module-disable gating:** When a processing module is explicitly disabled (e.g., NR is turned off at low ISO, TNR is disabled for a still-photo capture), the module's clock tree must also be gated. Leaving the clock running through a disabled module wastes dynamic power proportional to the clock tree switching activity even when no useful computation occurs. ISP hardware designs implement a per-module clock-enable register; software must write the clock-gate bit whenever a module is disabled.

**Power Gating:**

When a module is idle for an extended period (e.g., BPS is inactive during video recording), its VDD supply is cut off. Recovery latency is approximately 10–100 µs (pipeline refill required), so power gating is only triggered for long idle intervals (>1 ms).

**Android System-Level Camera Wakelock:**

The Camera driver holds a `PARTIAL_WAKE_LOCK` to prevent the CPU from entering deep sleep. Improper wakelock retention is one of the most common causes of abnormal battery drain in Camera applications (diagnosable via Battery Historian, see §2).

### 1.5 DDR Bandwidth — "The Memory Wall"

The ISP is a bandwidth-intensive block. Using a 108MP sensor (12000×9000) at 30fps as an example:

$$\text{BW}_\text{RAW read} = 12000 \times 9000 \times 30 \times 10\text{bit} / 8 \approx 4.05 \text{ GB/s}$$

Adding TNR reference frame reads/writes, ISP intermediate buffers, and other traffic, the actual DDR bandwidth demand can reach **10–20 GB/s** (single ISP pipeline). LPDDR5 bandwidth is approximately 51 GB/s per channel (LPDDR5-6400 single-channel), or ~102 GB/s dual-channel on typical SoC configurations; the ISP alone consumes approximately 10–20% of dual-channel bandwidth.

**Line buffers vs. full-frame buffers:**

A critical architectural decision that directly impacts DDR power is whether an ISP module uses on-chip **line buffers** (SRAM strips holding a few lines of pixels) or off-chip **full-frame buffers** (entire frames stored in DRAM):

- A module operating purely on line buffers reads/writes only the pixels it currently needs from on-chip SRAM, incurring **zero DDR transactions** for its intermediate data.
- A module that writes an intermediate full frame to DDR and reads it back for the next stage incurs a full-frame round-trip bandwidth cost (~bytes_per_pixel × width × height × fps × 2 for write+read).
- For a 4K 30fps pipeline, replacing one full-frame DDR round-trip with a line-buffer implementation saves approximately **600–1200 MB/s** of DDR bandwidth, which translates to roughly **60–120 mW** of DDR power savings.

Modern ISP hardware pipelines (e.g., Qualcomm IFE, Apple ISP) use deep internal line buffers to allow multi-stage processing within a single pass, explicitly minimizing DDR accesses. Modules that cannot fit in a streaming line-buffer model (e.g., TNR, which needs the prior complete frame) are the primary drivers of DDR bandwidth.

**DDR power estimation (based on public Micron/Samsung datasheets):**

$$P_\text{DDR} \approx \frac{\text{BW}_\text{actual}}{\text{BW}_\text{max}} \times P_\text{DDR,peak}$$

At 40% load, LPDDR5 consumes approximately 600–900 mW (entire memory subsystem including controller and PHY).

### 1.6 Thermal Throttling Model

The relationship between ISP power and junction temperature on a mobile device:

```
P_ISP + P_other → thermal path → T_junction
                                     ↓
                              T_J > T_throttle_1 → scale down to Nominal
                              T_J > T_throttle_2 → scale down to SVS
                              T_J > T_throttle_3 → stop recording / reduce frame rate
```

**Thermal resistance chain (reference: JEDEC/ARM public thermal analysis methodology):**

$$T_J = T_\text{ambient} + P_\text{total} \cdot (\theta_{JC} + \theta_{CA})$$

| Parameter | Description | Typical Value |
|-----------|-------------|---------------|
| $\theta_{JC}$ | Junction-to-case thermal resistance | 0.5–2 °C/W (SoC package) |
| $\theta_{CA}$ | Case-to-ambient thermal resistance | 5–15 °C/W (smartphone without heatsink) |
| $T_\text{throttle}$ | Throttling threshold | Typically 85–95 °C (tunable by OEM) |

**DTRO (Digital Thermal Ring Oscillator):** Qualcomm/MTK SoCs embed multiple DTRO sensors, exposed to user space via the Linux thermal sysfs interface:

```bash
cat /sys/class/thermal/thermal_zone*/temp  # unit: milli-degrees Celsius
```

---

## §2 Measurement

### 2.1 Perfetto — System-Level Tracing

**Perfetto** is Android 9+'s official system performance tracing framework, fully open source (AOSP). Documentation: [perfetto.dev](https://perfetto.dev).

**Key Perfetto data sources for Camera power analysis:**

| Data Source | Information Provided | Config Keyword |
|-------------|----------------------|----------------|
| `power` | SoC power domain state, DVFS frequency/voltage | `power` |
| `thermal` | Temperature from all thermal sensors | `thermal` |
| `android.hardware.camera` | Camera HAL call timing | `atrace` |
| `ion/dma-buf` | ISP buffer allocation/release | `memory` |
| `kgsl` | GPU/GPUMMU (used by some ISP implementations) | `gpu` |

**Standard command to capture a Camera Perfetto trace (Android ADB, AOSP documentation):**

```bash
# 1. Configure trace config
adb shell perfetto \
  -c - --txt \
  -o /data/misc/perfetto-traces/camera_power.pftrace \
<<EOF
buffers: {
    size_kb: 262144
    fill_policy: DISCARD
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "power/cpu_frequency"
            ftrace_events: "power/cpu_idle"
            ftrace_events: "thermal/thermal_zone_trip"
            ftrace_events: "android_fs/android_fs_dataread_start"
            atrace_categories: "camera"
            atrace_categories: "hal"
            atrace_categories: "power"
        }
    }
}
data_sources: {
    config {
        name: "android.power"
        android_power_config {
            battery_poll_ms: 100
            collect_power_rails: true
        }
    }
}
duration_ms: 10000
EOF

# 2. Pull the trace file
adb pull /data/misc/perfetto-traces/camera_power.pftrace .

# 3. Analyze in browser (ui.perfetto.dev)
# Drag and drop the .pftrace file to visualize
```

**Finding ISP power clues in Perfetto UI:**
- Search for `kgsl_pwr_set_state` or `kmd_event` (ISP KMD events)
- Observe the correlation between `camera.*` thread timing and `cpu_frequency` operating points
- Check whether inter-frame intervals show ISP stalls (occur when DDR bandwidth is insufficient)

### 2.2 Battery Historian — Battery Statistics

**Battery Historian** is Google's open-source battery usage visualization tool (GitHub: google/battery-historian), using Android `bugreport` data.

**Usage workflow:**

```bash
# 1. Reset battery statistics (run before testing)
adb shell dumpsys batterystats --reset

# 2. Run the Camera test scenario (e.g., record video for 10 minutes)

# 3. Export bugreport
adb bugreport /tmp/bugreport_camera.zip

# 4. Analyze with Battery Historian
# Option 1: Google Cloud version (no login required)
# https://bathist.ef.lc/

# Option 2: Run locally with Docker
docker run -d -p 9999:9999 gcr.io/android-battery-historian/stable:3.1 --port 9999
# Open browser at http://localhost:9999 and upload bugreport.zip
```

**Identifying Camera power issues in Battery Historian:**

| Metric | Location | Meaning |
|--------|----------|---------|
| Camera ON duration | "Camera" row | Actual time the camera was active |
| WakeLock | "WakeLock" row | Whether `CameraService` wakelock was properly released |
| Foreground/Background app | "Foreground app" row | Camera application lifecycle |
| Battery level | Top line chart | Slope of battery drain curve before/after camera use |

**Camera WakeLock analysis (`dumpsys` command, AOSP documentation):**

```bash
adb shell dumpsys batterystats | grep -A 5 "Camera"
# Example output (public format):
# Camera: 10m 23s 451ms (4 times)
#   Package: com.android.camera2
```

### 2.3 ARM Streamline

ARM Streamline is the performance analyzer within ARM DS (Development Studio), supporting PMU hardware counter collection for Cortex-A CPUs, Mali GPUs, and MMU-600. Documentation is fully public (developer.arm.com/tools-and-software/embedded/arm-development-studio).

**Relevant ISP counters (Mali/MMU):**

| Counter | Description | Power Optimization Use |
|---------|-------------|------------------------|
| `GPU_ACTIVE` | GPU active cycles | Determines GPU-based ISP load |
| `MMU_STALL` | MMU stall cycles | ISP stalls caused by insufficient DDR bandwidth |
| `L2_READ_BEATS` | L2 read transactions | ISP frame buffer memory access volume |
| `CPU_CYCLES` | CPU cycles | CPU overhead from ISP driver |

### 2.4 Monsoon Power Monitor

**Monsoon** is the industry-standard hardware current meter (monsoon.com, publicly available for purchase), with a 5 kHz sampling rate, ±0.2 mA accuracy, and USB passthrough power support.

**Standard Camera power measurement procedure (based on Monsoon public documentation):**

```
[Monsoon]──Main battery rail──[Phone]
     ↓
Monsoon HVPM Software (Windows/Mac, free download)
     ↓
.mfg sample file → analyze current vs. time waveform
```

**Measurement scenario specification (industry-standard methodology, used publicly by DXOMARK/AnandTech, etc.):**
1. Disable WiFi/cellular/Bluetooth (eliminate interference)
2. Fix screen brightness at 200 nit
3. Warm up for 2 minutes (reach thermal steady state)
4. Record 5 minutes of 4K 30fps → compute average current × 4.35V to obtain mW

### 2.5 Linux Thermal Sysfs (No Dedicated Tools Required)

```bash
# View all thermal sensors (Android shell or Linux)
for zone in /sys/class/thermal/thermal_zone*; do
    type=$(cat "$zone/type" 2>/dev/null)
    temp=$(cat "$zone/temp" 2>/dev/null)
    echo "$type: $((temp/1000))°C"
done

# View throttling trip points
cat /sys/class/thermal/thermal_zone0/trip_point_0_temp  # milli-degrees Celsius

# View ISP-related clock frequencies (Qualcomm SoC)
cat /sys/kernel/debug/clk/cam_cc_ife_0_clk/measure  # debugfs, requires root

# View DVFS frequency operating points
cat /sys/class/devfreq/*/available_frequencies
```

---

## §3 Tuning

### 3.1 CamX Performance Configuration (Qualcomm Public SDK Documentation)

The Qualcomm CamX framework controls performance policy through `camxsettings.xml` (on-device path: `/vendor/etc/camera/`). The format of this file is fully documented in the Qualcomm Camera SDK.

**Key power-related settings:**

```xml
<!-- camxsettings.xml selected fields (format from public Qualcomm Camera SDK documentation) -->

<!-- ISP clock limit: lower the frequency cap to save power -->
<setting name="IFEClockLimitInMHz">  <!-- default 600; can be set to 400 in power-saving mode -->
  <default>600</default>
</setting>

<!-- Frame rate cap -->
<setting name="MaxFPSForPreview">
  <default>30</default>  <!-- 60→30 saves approximately 20% ISP power -->
</setting>

<!-- TNR enable control -->
<setting name="EnableTNR">
  <default>1</default>  <!-- disabling TNR saves 15–25% IPE power -->
</setting>

<!-- Background camera power-saving mode -->
<setting name="EnableCameraIdlePowerCollapse">
  <default>1</default>  <!-- power collapse IPE when preview is idle -->
</setting>
```

### 3.2 Frame Rate and Resolution Strategy

**Impact of frame rate on power ($P \propto f$):**

| Scenario | Frame Rate | Relative ISP Power | Strategy |
|----------|------------|--------------------|----------|
| 4K 60fps video | 60fps | 1.00× | High power; thermal management required |
| 4K 30fps video | 30fps | ~0.55× | Standard high quality |
| 1080p 30fps video | 30fps | ~0.25× | Power-saving mode |
| Preview (recording stopped) | 30fps | ~0.15× | Very low power |

**Resolution downscaling (binning) for power savings:**

A 108MP sensor typically enables 9-in-1 binning during preview (12MP output), reducing the pixel count processed by IFE to 1/9 and correspondingly cutting power consumption significantly.

### 3.3 ISP Output Format Selection

**Impact of YUV format on bandwidth:**

| Output Format | Bits/Pixel | Bandwidth (1080p 30fps) | Notes |
|---------------|------------|--------------------------|-------|
| NV12/NV21 | 12 bit/px | ~180 MB/s | Standard format, broad compatibility |
| YUV 4:2:2 | 16 bit/px | ~238 MB/s | +32% bandwidth |
| RGBA8888 | 32 bit/px | ~475 MB/s | Special use cases only |
| HEIF (after hardware encode) | ~2–4 bit/px | Storage format, not a real-time stream | Final compressed output |

**Recommendation:** Use NV12 for the preview path; use hardware encoders for JPEG/HEIF encoding (saves 80–90% encoding energy compared to CPU software encoding).

### 3.4 TNR Power Trade-offs

TNR (Temporal Noise Reduction) is the most power-hungry module in the IPE because it requires:
- Reading in the previous reference frame (+100% DDR read bandwidth)
- Motion estimation (ME, computationally intensive)
- Weighted frame blending

**TNR power control strategy:**

```
ISO low  (< 800)    → TNR off (noise not significant; blending unnecessary)
ISO mid  (800–3200) → TNR on, ME precision set to medium
ISO high (> 3200)   → TNR on, ME precision set to full (image quality priority)
Thermal throttle    → TNR downgraded to 2-frame blending (reduce ME computation)
```

### 3.5 Key Tuning Parameter Comparison Across Three Platforms

| Feature | Qualcomm CamX | MTK Imagiq | HiSilicon Yueyingr |
|---------|---------------|------------|--------------------|
| Performance level control | `PerfLock hint` + `camxsettings.xml` | `MMSDK perfservice` | HiISP `HiISP perf profile` |
| DVFS frequency limit | `IFEClockLimitInMHz` | `ISPClkRate` (NDD) | `ISP_CLK_LEVEL` |
| TNR enable/disable | `EnableTNR` | `TNR_Enable` (NDD) | `TNR_Enable` |
| Thermal throttle response | `ThermalMitigationLevel` | `ThermalScenario` | `ISP_ThermalLevel` |
| Wakelock management | `CameraService` wakelock (AOSP standard) | Same | Same |

---

## §4 Common Power Issues

### 4.1 Thermal Throttling During Extended Video Recording

**Symptom:** After approximately 10–20 minutes of 4K 60fps recording, the frame rate automatically drops to 30fps or intermittent frame drops occur.

**Root cause:** The cumulative heat generated by ISP plus peripheral blocks (display, encoder) exceeds the throttle threshold.

**Diagnosis:**
```bash
# Monitor temperature (Android shell)
watch -n 1 "cat /sys/class/thermal/thermal_zone*/temp | tr '\n' ' '"

# Check throttle events (in Perfetto trace)
# Search for "thermal_zone_trip" events
```

**Mitigation:**
- Reduce recording resolution (4K→1080p, power reduction of 50–70%)
- Enable `EnableCameraIdlePowerCollapse`
- Optimize device thermal design (heat pipes, graphite thermal spreader)

### 4.2 Camera Wakelock Not Released

**Symptom:** After the user exits the Camera application, the phone continues to run hot and exhibits abnormal battery drain.

**Root cause:** The Camera HAL or application-layer wakelock is not properly released, leaving the ISP driver in a partially awake state.

**Diagnosis (Battery Historian):**
1. Export bugreport; examine the "WakeLock" row in Battery Historian
2. Check whether the `CameraService` wakelock persists after the application exits

**Diagnosis (ADB real-time):**
```bash
adb shell dumpsys power | grep -A 3 "PARTIAL_WAKE_LOCK.*camera"
# Expected normal state: no camera-related wakelock after Camera is closed
```

### 4.3 Frame Drops Due to Insufficient ISP Bandwidth

**Symptom:** Irregular frame drops occur in high-frame-rate (60fps) or high-resolution scenarios, even when CPU/GPU are not busy.

**Root cause:** DDR bandwidth is contended by other blocks (display, AI, video encoder), causing ISP DMA wait times to exceed the frame period.

**Diagnosis (Perfetto):**
- Observe `bw_hwmon` events in the Perfetto trace
- Check ISP frame timestamp intervals: stable 16.67ms (60fps) vs. occasional 33ms (dropped frame)

### 4.4 AI ISP NPU Power Stacking

**Symptom:** When AI denoising (NPU-based) is active, total power consumption exceeds expectations and thermal throttling triggers more quickly.

**Root cause:** When ISP and NPU run concurrently, their power dissipations add up; NPU memory bandwidth competes with the ISP.

**Mitigation:**
- Schedule NPU inference and ISP processing in a pipelined, non-concurrent manner
- Disable AI denoising at low ISO (let traditional hardware ISP NR handle it)

### 4.5 Flash/Strobe Current Spike

**Symptom:** A brief current spike occurs when taking a photo (up to 500mA–1A), which may trigger PMIC undervoltage protection.

**Root cause:** When the LED flash charging circuit is undersized, the instantaneous current draw pulls down the battery voltage, destabilizing the SoC.

**Diagnosis (Monsoon waveform):** The current spike at the moment of capture is clearly visible in the Monsoon sampling waveform.

---

## §5 Evaluation

### 5.1 Power Measurement Methodology

**Standard measurement specification (industry-standard, reference: DXOMARK/AnandTech public methodology):**

1. **Environmental conditions:** Room temperature 25±2°C, ADB connected (USB charging disabled), screen brightness 200 nit
2. **Warm-up:** Start measuring after running the test scenario for 2 minutes (avoids cold-start effects)
3. **Measurement duration:** ≥5 minutes (thermal steady state)
4. **Repetitions:** 3 runs; report the mean

**Power efficiency metrics:**

| Metric | Formula | Meaning |
|--------|---------|---------|
| mW/fps | $P_\text{total} / \text{fps}$ | Energy cost per frame |
| mW/(MP/s) | $P_\text{total} / (W \times H \times fps / 10^6)$ | Energy cost per megapixel |
| mW/TOPS | $P_\text{NPU} / \text{TOPS}_\text{measured}$ | AI compute efficiency |

### 5.2 Industry Public Reference Values

The following data are sourced from public review sites such as AnandTech, GSMArena, and Notebookcheck, as well as chip vendor datasheets:

| Scenario | Typical Power Range | Source Type |
|----------|--------------------|-------------|
| Camera preview (1080p 30fps) | 300–600 mW | Public teardown reports |
| 4K 30fps video recording | 1200–2500 mW | Public benchmarks |
| 4K 60fps video recording | 2500–4500 mW | Public benchmarks |
| AI denoising (NPU-accelerated) | +200–500 mW | Public papers/reports |
| Photo capture (single-frame JPEG) | 500ms pulse ≈ 50–150 mJ | Public methodology estimate |

> Note: The values above are typical ranges; actual values vary depending on SoC model, algorithm implementation, and scene content.

### 5.3 Typical Power Distribution (Public Academic Reference)

Based on IEEE public papers (e.g., ISSCC mobile SoC papers) and industry analysis reports, the approximate breakdown of total device power in a video recording scenario is:

```
Total device power (4K video) = 100%
├── Display                  ~25–35%
├── CPU (driver + algorithm) ~15–20%
├── ISP hardware             ~20–30%
├── Video encoder            ~10–15%
├── NPU (AI features)        ~5–15% (depends on whether enabled)
├── DDR memory subsystem     ~10–15%
└── Wireless (WiFi/4G streaming) ~5–10% (depends on network usage)
```

---

## §6 Code

### 6.1 Parsing Camera Power Events from a Perfetto Trace (Python)

The following code uses the official Perfetto Python SDK (`perfetto` package, installable via pip, fully open source):

```python
"""
parse_camera_power.py
Analyze Camera power-related events using the Perfetto Python API.

Dependency: pip install perfetto
Documentation: https://perfetto.dev/docs/analysis/trace-processor
"""

from perfetto.trace_processor import TraceProcessor

def analyze_camera_power(trace_path: str):
    """Analyze power-related events from a Camera Perfetto trace."""
    tp = TraceProcessor(trace=trace_path)

    # 1. Query CPU frequency change events
    print("=== CPU Frequency Operating-Point Changes ===")
    freq_query = """
    SELECT
      ts / 1e9 AS time_sec,
      cpu,
      value AS freq_khz
    FROM counter c
    JOIN counter_track t ON c.track_id = t.id
    WHERE t.name = 'cpufreq'
    ORDER BY ts
    LIMIT 20
    """
    df_freq = tp.query(freq_query).as_pandas_dataframe()
    print(df_freq.to_string(index=False))

    # 2. Query CPU time consumed by Camera-related threads
    print("\n=== Camera Thread CPU Utilization ===")
    camera_cpu_query = """
    SELECT
      t.name AS thread_name,
      p.name AS process_name,
      SUM(s.dur) / 1e9 AS total_cpu_sec
    FROM sched_slice s
    JOIN thread t ON s.utid = t.utid
    JOIN process p ON t.upid = p.upid
    WHERE p.name LIKE '%camera%' OR t.name LIKE '%CamX%' OR t.name LIKE '%cam%'
    GROUP BY t.utid
    ORDER BY total_cpu_sec DESC
    LIMIT 10
    """
    df_camera = tp.query(camera_cpu_query).as_pandas_dataframe()
    print(df_camera.to_string(index=False))

    # 3. Query thermal sensor temperature trends
    print("\n=== Thermal Sensor Temperature Trend ===")
    thermal_query = """
    SELECT
      ts / 1e9 AS time_sec,
      t.name AS sensor_name,
      c.value / 1000.0 AS temp_celsius
    FROM counter c
    JOIN counter_track t ON c.track_id = t.id
    WHERE t.name LIKE '%thermal%' OR t.name LIKE '%tsens%'
    ORDER BY ts
    LIMIT 30
    """
    df_thermal = tp.query(thermal_query).as_pandas_dataframe()
    print(df_thermal.to_string(index=False))

    tp.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python parse_camera_power.py <trace.pftrace>")
    else:
        analyze_camera_power(sys.argv[1])
```

### 6.2 ISP DDR Bandwidth Estimation Script

```python
"""
isp_bandwidth_calc.py
ISP pipeline DDR bandwidth demand estimator.

No external dependencies required.
"""

def calc_isp_bandwidth(
    width: int,
    height: int,
    fps: float,
    bit_depth: int = 10,
    tnr_enabled: bool = True,
    yuv_output: bool = True,
    safety_factor: float = 1.3,  # DDR bandwidth headroom factor
) -> dict:
    """
    Compute DDR bandwidth demand for the ISP pipeline.

    Returns:
        dict: per-path bandwidth (MB/s) and total demand
    """
    pixels_per_frame = width * height
    bytes_raw = pixels_per_frame * bit_depth / 8

    # RAW input read bandwidth
    bw_raw_read = bytes_raw * fps / 1e6  # MB/s

    # YUV output write bandwidth (NV12: 12 bit/px = 1.5 bytes/px)
    bw_yuv_write = pixels_per_frame * 1.5 * fps / 1e6 if yuv_output else 0

    # TNR reference-frame read + current-frame write (2× YUV bandwidth)
    bw_tnr = bw_yuv_write * 2 if tnr_enabled else 0

    # ISP internal intermediate buffer (approx. one YUV frame)
    bw_internal = bw_yuv_write * 0.5

    bw_total_raw = bw_raw_read + bw_yuv_write + bw_tnr + bw_internal

    return {
        "raw_read_MB_s":    round(bw_raw_read, 1),
        "yuv_write_MB_s":   round(bw_yuv_write, 1),
        "tnr_MB_s":         round(bw_tnr, 1),
        "internal_MB_s":    round(bw_internal, 1),
        "total_MB_s":       round(bw_total_raw, 1),
        "with_margin_MB_s": round(bw_total_raw * safety_factor, 1),
    }


if __name__ == "__main__":
    scenarios = [
        ("4K 60fps TNR on",   3840, 2160, 60, 10, True),
        ("4K 30fps TNR on",   3840, 2160, 30, 10, True),
        ("1080p 30fps TNR",   1920, 1080, 30, 10, True),
        ("108MP single shot", 12000, 9000,  1, 10, False),
    ]

    print(f"{'Scenario':<25} {'RAW_rd':>8} {'YUV_wr':>8} {'TNR':>8} {'Total':>8} {'w/margin':>9}")
    print("-" * 70)
    for name, w, h, fps, bits, tnr in scenarios:
        r = calc_isp_bandwidth(w, h, fps, bits, tnr)
        print(f"{name:<25} {r['raw_read_MB_s']:>7.0f} {r['yuv_write_MB_s']:>7.0f} "
              f"{r['tnr_MB_s']:>7.0f} {r['total_MB_s']:>7.0f} {r['with_margin_MB_s']:>8.0f}")
    print("(unit: MB/s)")
```

---

## §7 Further Reading

### 7.1 NPU vs. ISP Power Trade-offs

As AI ISP becomes mainstream, some algorithms are migrating from dedicated ISP hardware to NPU execution:

| Algorithm | ISP Hardware Execution | NPU Execution | Power Trade-off |
|-----------|------------------------|---------------|-----------------|
| Traditional denoising (BM3D-like) | Dedicated circuit, low power | Feasible, flexible | ISP wins by ~3–5× |
| AI denoising (DnCNN) | Not supported (no NN accelerator) | NPU excels | NPU is required |
| Traditional demosaic | ISP fixed-function, low power | Feasible but wasteful | ISP wins by ~10× |
| AI demosaic | Not supported | NPU can do it | NPU (suited for offline scenarios) |

**Conclusion:** For any module that ISP hardware can handle, prefer the ISP (3–10× better power efficiency). Only migrate to the NPU for AI algorithms that ISP hardware does not support.

### 7.2 Always-On Camera Ultra-Low-Power Design

Always-on cameras in IoT and wearable devices require ISP standby power on the order of **1–10 mW** (vs. 0.5–2 W for smartphone ISPs).

Implementation approaches:
- **Minimal ISP pipeline:** Retain only BLC + Demosaic + compression; remove NR/EE/TNR
- **Low resolution:** 320×240 @ 5fps — pixel throughput is only 0.3% of 1080p 30fps
- **Event-triggered:** Sensor stays in standby (µA level) most of the time; the ISP wakes up only when motion or a face is detected
- **Representative chips:** Nordic nRF9160 (integrated camera ISP, ~5 mW active), OmniVision OV02B10 (ultra-low-power sensor)

### 7.3 Event Cameras (Neuromorphic Cameras)

Event cameras (e.g., Sony IMX636, Prophesee Metavision) do not output frames; instead they output a stream of per-pixel brightness change events:

$$\text{Event} = (x, y, t, p) \quad p \in \{+1, -1\}$$

**Power advantage:** In static scenes there is almost no output (vs. a conventional camera outputting full frames every period); in dynamic scenes the power consumption is only **1/10–1/100** that of a conventional camera.

**ISP implications:** Event cameras do not require a traditional ISP pipeline (no Bayer pattern, no AWB/CCM), but they demand entirely new event-stream processing algorithms (event denoising, frame reconstruction).

---

## References

1. Google LLC. *Perfetto Documentation* (2024). [https://perfetto.dev/docs/](https://perfetto.dev/docs/)
2. Google LLC. *Battery Historian* (2023). GitHub: google/battery-historian.
3. ARM Ltd. *ARM Development Studio — Streamline Performance Analyzer*. [https://developer.arm.com/tools-and-software/embedded/arm-development-studio](https://developer.arm.com/tools-and-software/embedded/arm-development-studio)
4. Qualcomm Technologies. *Qualcomm Camera SDK Documentation* (2023). developer.qualcomm.com.
5. JEDEC Standard JESD235D: *High Bandwidth Memory DRAM (HBM)* (2021). jedec.org.
6. Abadal, S. et al. "Computing Graph Neural Networks: A Survey from Algorithms to Accelerators." *ACM Computing Surveys* (2021). — Reference for NPU vs. ISP power efficiency comparison methodology.
7. Capra, M. et al. "An Updated Survey of Efficient Hardware Architectures for Accelerating Deep Convolutional Neural Networks." *Future Internet* (2020). — Framework for AI ISP chip power analysis.
8. Samsung Semiconductor. *LPDDR5 / LPDDR5X Product Brief* (2023). samsung.com/semiconductor.
9. Monsoon Solutions Inc. *Monsoon HVPM User Manual*. monsoon.com.
10. Galloway, M. et al. "An Energy Perspective on Camera Processing in Modern Smartphones." *IEEE Transactions on Mobile Computing* (2022). — Public academic reference for camera power distribution.
11. Gallego, G. et al. "Event-Based Vision: A Survey." *IEEE TPAMI* 44(1):154–180 (2022). — Event camera survey.

---

## §8 Glossary

**DVFS (Dynamic Voltage and Frequency Scaling)**
A technique that reduces power dissipation by simultaneously lowering the operating frequency and core supply voltage. Because dynamic power is proportional to $V^2 \cdot f$, combined voltage-and-frequency reduction is far more effective than frequency reduction alone. On modern SoCs, the ISP, CPU, and GPU each have independent DVFS domains that can be adjusted individually.

**Clock Gating**
Disabling a logic block's clock signal when the block is inactive (e.g., during horizontal/vertical blanking intervals) to eliminate switching power (driving the $\alpha$ term in $\alpha \cdot C \cdot V^2 \cdot f$ to zero). Simple to implement, it is the most widely used low-power technique.

**Power Gating**
Cutting the VDD supply to a module that has been idle for an extended period to eliminate leakage current. More thorough in power savings than clock gating, but power-on recovery takes additional time (10–100 µs), so it is only applied to modules that are idle for long intervals.

**IFE (Image Front End)**
The front-end processing block of the Qualcomm Spectra ISP. It receives RAW data from the MIPI CSI-2 interface and performs front-end operations including BLC, demosaic, LSC, and AWB statistics. Accounts for approximately 30–40% of total ISP power.

**DDR Bandwidth**
The memory bandwidth consumed by the ISP pipeline reading and writing frame buffers; a significant component of ISP power consumption. In a typical 4K 60fps + TNR scenario, ISP DDR bandwidth demand is approximately 10–20 GB/s, representing approximately 10–20% of total dual-channel LPDDR5 bandwidth (~102 GB/s for LPDDR5-6400).

**Perfetto**
Android 9+'s built-in system-level performance tracing framework, fully open source in AOSP (perfetto.dev). Can trace CPU frequency, Camera HAL call timing, memory bandwidth, thermal sensors, and more — the preferred tool for Camera power analysis.

**Battery Historian**
Google's open-source Android battery usage visualization tool (github.com/google/battery-historian), based on `bugreport` data. Can analyze Camera WakeLock behavior, per-application power share, and battery drain curves.

**WakeLock**
An Android power management construct that prevents the system from entering deep sleep. The Camera service holds a `PARTIAL_WAKE_LOCK` to keep the ISP driver running. Improper wakelock retention is a common cause of background battery drain in Camera applications.

**Thermal Throttling**
A protection mechanism that automatically reduces ISP/CPU/GPU frequencies when the SoC junction temperature approaches its safety limit. Throttle trigger status can be monitored via the Linux thermal sysfs interface. Extended 4K video recording is the scenario most likely to trigger thermal throttling.

**TNR (Temporal Noise Reduction)**
An ISP module that eliminates random noise by blending frames across time. It is the module with the highest power and bandwidth overhead in the IPE. Each frame requires reading in a reference frame (+100% DDR read bandwidth) and running motion estimation. Can be disabled at low ISO or during thermal throttling to save power.

**Monsoon Power Monitor**
The industry-standard hardware current meter. Connected in series on the main power rail, it samples current in real time at 5 kHz with ±0.2 mA accuracy. The industry-standard tool for measuring Camera power consumption.

**PerfLock (Performance Lock)**
The mechanism in Qualcomm's CamX framework for requesting a specific ISP performance operating point. The application layer requests a particular frequency/voltage level (Turbo/Nominal/SVS) from the driver layer via the HAL, balancing performance requirements against power consumption.
