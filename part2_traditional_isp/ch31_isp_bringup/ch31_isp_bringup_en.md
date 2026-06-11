# Part 2, Chapter 31: ISP Bring-up Practical Guide

> **Reader path:** BSP engineers, Camera driver engineers, ISP debug engineers
>
> **Prerequisites:** Volume 2, Chapter 1 (BLC/PDPC), Volume 2, Chapter 3 (Demosaic), Volume 4, Chapter 1 (3A System Overview)
>
> **Information sources:** The content of this chapter is based on open-source Linux kernel drivers (kernel.org), publicly available MIPI Alliance specification summaries, Android AOSP documentation, and the libcamera open-source project (libcamera.org). All example commands come from publicly reproducible toolchains.

---

## Introduction

Bring-up (初始化调通) is the entire process of taking a new camera module from "hardware installed" to "outputting usable images." For ISP engineers, bring-up is often the most time-consuming and experience-dependent stage in the debug chain. A sensor may fail to produce any image for an extended period due to a power-on sequence off by 1 ms, an I2C address with one wrong bit, or MIPI lanes connected in reverse order.

This chapter uses Linux and Android as its dual-platform backbone, and systematically covers the theory, standard procedures, and debug techniques of bring-up across four phases — "hardware communication → RAW data acquisition → ISP pipeline verification → 3A integration" — while providing a comprehensive toolchain reference and a quick-reference troubleshooting table of common problems.

---

## §1 Theory

### 1.1 Definition and Phases of Bring-up

ISP bring-up refers to the complete process of commissioning a new camera hardware system (sensor + lens + ISP SoC) from scratch on the target software stack, enabling it to stably output a video/image stream that meets quality requirements.

A complete bring-up is divided into the following four phases, each with clear acceptance criteria:

| Phase | Objective | Acceptance Criteria |
|-------|-----------|---------------------|
| **Phase 1: Hardware Communication Verification** | Confirm the SoC can communicate normally with the sensor | I2C/SPI can read and write Chip ID |
| **Phase 2: RAW Data Acquisition** | First-frame bring-up | A non-all-black, non-all-white RAW frame can be captured |
| **Phase 3: ISP Pipeline Verification** | Verify each ISP module one by one | RGB/YUV output color is basically correct |
| **Phase 4: 3A System Integration** | AE/AF/AWB closed-loop operation | Exposure, focus, and white balance converge normally under standard scenes |

Each phase has a strict sequential dependency: failure in Phase 1 prevents entry into Phase 2, and so on. In actual engineering practice, skipping phases and debugging directly will greatly increase the difficulty of root-cause analysis.

### 1.2 Linux V4L2 Framework Overview

Linux's camera subsystem is based on the **V4L2 (Video4Linux2)** framework, combined with the **Media Controller** framework to achieve flexible pipeline topology management.

#### 1.2.1 Core Device Nodes

```
/dev/videoX       # Video capture/output node (V4L2 video device)
/dev/v4l-subdevX  # Sub-device node (sensor, CSI receiver, ISP modules)
/dev/mediaX       # Media Controller node (manages the entire pipeline topology)
```

A typical camera pipeline topology is as follows:

```
[sensor subdev] --> [MIPI CSI-2 receiver subdev] --> [ISP subdev] --> [video capture node]
   /dev/v4l-subdev0      /dev/v4l-subdev1             /dev/v4l-subdev2    /dev/video0
```

The full topology can be printed with `media-ctl -p`:

```bash
$ media-ctl -d /dev/media0 -p
```

#### 1.2.2 Typical Sensor Driver Structure

Using `imx258` (Sony 13MP, open-source driver at `drivers/media/i2c/imx258.c`) from the Linux kernel mainline as an example, a standard V4L2 sensor driver needs to implement the following core interfaces:

```c
static const struct v4l2_subdev_ops imx258_subdev_ops = {
    .core  = &imx258_core_ops,   /* s_power */
    .video = &imx258_video_ops,  /* s_stream */
    .pad   = &imx258_pad_ops,    /* enum_mbus_code, get_fmt, set_fmt,
                                    enum_frame_size, get_selection */
};
```

Key callback functions:
- `s_power(sd, on)`: Controls power-on/power-off sequence (DOVDD/AVDD/DVDD + RESET + MCLK)
- `s_stream(sd, enable)`: Starts/stops sensor streaming (writes streaming on/off registers)
- `set_fmt()`: Configures output resolution and pixel format (e.g., `MEDIA_BUS_FMT_SRGGB10_1X10`)

#### 1.2.3 DTS (Device Tree Source) Configuration Example

The sensor's DTS node must describe its physical connection information. The following is a typical 2-lane MIPI CSI-2 sensor configuration (based on publicly available Linux kernel documentation examples):

```dts
&i2c2 {
    clock-frequency = <400000>;  /* I2C Fast Mode: 400 kHz */
    status = "okay";

    camera_sensor: camera@10 {
        compatible = "ovti,ov5675";
        reg = <0x10>;            /* I2C 7-bit address */

        /* Power management */
        avdd-supply   = <&reg_cam_avdd>;   /* Analog supply 2.8V */
        dvdd-supply   = <&reg_cam_dvdd>;   /* Digital core supply 1.2V */
        dovdd-supply  = <&reg_cam_dovdd>;  /* IO supply 1.8V */

        /* Control signals */
        reset-gpios   = <&gpio3 5 GPIO_ACTIVE_LOW>;
        powerdown-gpios = <&gpio3 6 GPIO_ACTIVE_HIGH>;

        /* Master Clock: provided by SoC to sensor */
        clocks = <&ccu CLK_MCLK0>;
        clock-names = "xvclk";
        assigned-clocks = <&ccu CLK_MCLK0>;
        assigned-clock-rates = <24000000>;  /* 24 MHz MCLK */

        port {
            sensor_out: endpoint {
                remote-endpoint = <&mipi_csi_in>;
                data-lanes = <1 2>;          /* 2-lane MIPI */
                clock-lanes = <0>;
                link-frequencies = /bits/ 64 <456000000>;  /* 456 MHz per lane */
            };
        };
    };
};

&mipi_csi {
    status = "okay";
    port {
        mipi_csi_in: endpoint {
            remote-endpoint = <&sensor_out>;
            data-lanes = <1 2>;
            clock-lanes = <0>;
        };
    };
};
```

**Key field descriptions:**
- `link-frequencies`: MIPI CSI-2 bit rate in Hz; **must be consistent with the sensor register configuration**
- `data-lanes`: Lane numbers start from 1; the order must correspond to the PCB routing
- `clock-lanes`: Clock lane is fixed at 0

### 1.3 MIPI CSI-2 Physical Layer Principles

#### 1.3.1 CSI-2 Protocol Stack

The MIPI CSI-2 protocol stack is divided into four layers from bottom to top:

```
+---------------------------+
|  Application Layer        |  RAW8/RAW10/RAW12/YUV422 and other data formats
+---------------------------+
|  Pixel/Byte Layer         |  Data Type (DT) identifies the data type
+---------------------------+
|  Lane Management Layer    |  Multi-lane data distribution and recombination
+---------------------------+
|  Physical Layer D-PHY / C-PHY  |  Differential signal transmission
+---------------------------+
```

#### 1.3.2 D-PHY Lane Operating Modes

D-PHY has two operating modes; understanding their switching sequence is critical for bring-up:

| Mode | Abbreviation | Voltage Characteristics | Purpose |
|------|--------------|------------------------|---------|
| Low Power | LP | Differential 0~1.2V, single-ended valid | Control signals (LP-11/LP-01/LP-00) |
| High Speed | HS | Differential 100~300mV | High-speed data transmission |

**LP → HS switching sequence (MIPI Alliance D-PHY specification public summary):**

```
LP-11 → LP-01 → LP-00 → HS-0 [SOT] → data transmission → [EOT] → LP-11
```

Common LP→HS switching timeout errors (`mipi: hs_rx_timeout`) are typically caused by:
1. Sensor MCLK not ready (PLL not locked)
2. SoC MIPI receiver-side termination resistor not enabled
3. PCB trace impedance mismatch (target 100Ω differential impedance)

#### 1.3.3 Lane Count and Bandwidth Calculation

MIPI CSI-2 supports 1/2/4/8 lane configurations. Bandwidth calculation formula:

```
Total bandwidth (Gbps) = Number of lanes × Per-lane rate (Gbps/lane)

Minimum required bandwidth = Width × Height × FPS × bits per pixel × 1.15 (approximately 15% overhead)

Example: 4208×3120 @ 30fps RAW10
  = 4208 × 3120 × 30 × 10 × 1.15 ≈ 4.52 Gbps
  → Requires 4-lane @ 1.2 Gbps/lane or 2-lane @ 2.5 Gbps/lane
```

#### 1.3.4 C-PHY Overview

C-PHY is a more efficient physical layer specification introduced by MIPI, using a 3-wire (Trio) transmission format where each symbol carries 2.28 bits of information, providing approximately 2.28× the bandwidth of D-PHY with the same number of lanes. Mainstream high-end mobile SoCs (such as certain Snapdragon platforms) already support C-PHY. C-PHY bring-up differs from D-PHY in its LP/HS switching mechanism and requires reference to the corresponding SoC's BSP documentation.

---

## §2 Debug Flow

### 2.1 Step 1: I2C Communication Verification

Before performing any sensor configuration, the I2C channel reachability must be verified first.

#### 2.1.1 Confirm the I2C Bus Number

```bash
# List all I2C buses in the system
$ i2cdetect -l
i2c-0	i2c         DesignWare HDMI                   I2C adapter
i2c-1	i2c         Tegra I2C adapter                 I2C adapter
i2c-2	i2c         Tegra I2C adapter                 I2C adapter
```

#### 2.1.2 Scan I2C Devices

```bash
# Scan all device addresses (0x03~0x77) on i2c-2
# -y skips interactive confirmation, -r uses read operations (safer)
$ i2cdetect -y -r 2

     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: 10 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
...
```

A response at address `0x10` (not `--`) indicates normal sensor I2C communication.

#### 2.1.3 Read Chip ID for Verification

Using OmniVision series sensors as an example, the Chip ID is usually located at a fixed register address (noted in publicly available datasheets from each vendor). Using OV5675 as an example (I2C address 0x10, 16-bit register address):

```bash
# Read high byte of Chip ID (register address 0x300A)
# i2ctransfer: -y bus number, w3 write 3 bytes (device addr + register high/low byte), r1 read 1 byte
$ i2ctransfer -y 2 w3@0x10 0x30 0x0A r1
0x56

# Read low byte of Chip ID (register address 0x300B)
$ i2ctransfer -y 2 w3@0x10 0x30 0x0B r1
0x75
```

Chip ID = `0x5675`, consistent with the OV5675 datasheet — I2C communication verification passed.

#### 2.1.4 Common I2C Issues

| Error Symptom | Root Cause Analysis | Solution |
|---------------|---------------------|----------|
| `i2cdetect` shows all `--`, no device response | DOVDD/VCC not powered on; I2C bus SCL/SDA pulled down; Reset not released | Use multimeter to measure each power rail; confirm Reset GPIO is high |
| Address is scanned but reading ID returns 0xFF | Sensor is in low-power mode or register access timing is wrong | Send initialization sequence before reading |
| `i2cdetect` shows address but writing register gives NACK | I2C clock frequency too high (some sensors support max 400kHz) | Reduce `clock-frequency` to 100000 |
| Intermittent NACK on continuous read/write | I2C bus capacitance too high, edges not sharp enough | Increase pull-up resistors to 4.7kΩ or shorten traces |

### 2.2 Step 2: Sensor Power-On Sequence

#### 2.2.1 Standard Three-Rail Power Definition

Mobile camera sensors typically require three power rails:

| Power Name | Typical Voltage | Supply Range | Description |
|------------|-----------------|--------------|-------------|
| **DOVDD** (IO supply) | 1.8 V | 1.7~1.9 V | Drives I2C and MIPI IO, must match SoC IO voltage level |
| **AVDD** (Analog supply) | 2.8 V | 2.6~3.0 V | Supplies pixel array and analog circuitry |
| **DVDD** (Digital core supply) | 1.05~1.2 V | ±5% | Supplies digital logic and PLL |

#### 2.2.2 Standard Power-On Sequence

Linux kernel sensor drivers typically control power-on in the following order within `s_power(sd, 1)` (using mainline driver `imx258` as a reference pattern):

```
T=0ms:    DOVDD power on (1.8V)
T=1ms:    AVDD power on (2.8V)
T=2ms:    DVDD power on (1.2V)
T=3ms:    MCLK enabled (24MHz)
T=4ms:    RESET# pulled high (reset released)
T=8ms:    Wait for sensor initialization to complete (>= 5ms, see datasheet for specifics)
T=8ms+:   I2C accessible (initialization register sequence can be written)
```

Corresponding kernel driver code pattern (reference from kernel.org public driver):

```c
static int sensor_power_on(struct sensor_dev *sensor)
{
    int ret;

    /* 1. Enable DOVDD */
    ret = regulator_enable(sensor->dovdd);
    if (ret) return ret;
    usleep_range(1000, 1200);  /* Wait for stabilization */

    /* 2. Enable AVDD */
    ret = regulator_enable(sensor->avdd);
    if (ret) goto err_avdd;
    usleep_range(1000, 1200);

    /* 3. Enable DVDD */
    ret = regulator_enable(sensor->dvdd);
    if (ret) goto err_dvdd;
    usleep_range(1000, 1200);

    /* 4. Enable MCLK */
    ret = clk_prepare_enable(sensor->xvclk);
    if (ret) goto err_clk;
    usleep_range(1000, 1200);

    /* 5. Release RESET (pull high) */
    gpiod_set_value_cansleep(sensor->reset_gpio, 0);  /* ACTIVE_LOW */
    usleep_range(5000, 6000);  /* Wait for sensor internal PLL lock */

    return 0;
    /* ... error handling ... */
}
```

#### 2.2.3 Common Causes of Power-On Failure

1. **DVDD short circuit**: Excessive DVDD current triggers PMIC over-current protection — monitor each rail with a current meter
2. **RESET signal polarity reversed**: `GPIO_ACTIVE_LOW` in DTS does not match actual hardware
3. **MCLK frequency deviation**: Actual MCLK is not 24MHz (measure with oscilloscope or frequency counter)
4. **Incorrect power-on order**: Some sensors require DOVDD to power on before DVDD; reversing the order can cause latch-up

### 2.3 Step 3: MIPI CSI Link Establishment

#### 2.3.1 Configure Media Pipeline

Under the V4L2 framework, use `media-ctl` to configure the pipeline:

```bash
# View current media topology
$ media-ctl -d /dev/media0 -p

# Set sensor subdev format (3840x2160, SRGGB10, 30fps)
$ media-ctl -d /dev/media0 \
  --set-v4l2 '"ov5675 2-0010":0[fmt:SRGGB10_1X10/3840x2160@1/30]'

# Set MIPI CSI receiver format (matching sensor output)
$ media-ctl -d /dev/media0 \
  --set-v4l2 '"csi2rx":0[fmt:SRGGB10_1X10/3840x2160]'

# Establish link: sensor → csi2rx (enable link)
$ media-ctl -d /dev/media0 \
  --links '"ov5675 2-0010":0 -> "csi2rx":0[1]'
```

#### 2.3.2 Start Streaming with v4l2-ctl

```bash
# View formats supported by the sensor
$ v4l2-ctl -d /dev/video0 --list-formats-ext

# Set output format (consistent with pipeline)
$ v4l2-ctl -d /dev/video0 \
  --set-fmt-video=width=3840,height=2160,pixelformat=RG10

# Capture 1 frame and save to file
$ v4l2-ctl -d /dev/video0 \
  --stream-mmap \
  --stream-count=1 \
  --stream-to=frame0.raw

# Continuously capture and display frame rate (verify streaming stability)
$ v4l2-ctl -d /dev/video0 \
  --stream-mmap \
  --stream-count=100
```

#### 2.3.3 Interpreting MIPI Errors in dmesg

```bash
# Real-time monitor MIPI/CSI-related kernel log
$ dmesg -w | grep -iE "csi|mipi|ov5675|imx258"
```

Common MIPI error log messages and their meanings:

```
# ECC error: 1-bit bit flip on Lane 0 (correctable)
[12.345] csi2rx: 1-bit ECC error on lane 0, corrected

# ECC fatal error: 2-bit bit flip (uncorrectable, usually a physical layer issue)
[12.346] csi2rx: 2-bit ECC error on lane 0, uncorrectable

# CRC error: data packet CRC check failed
[12.347] csi2rx: CRC error on virtual channel 0

# Lane alignment timeout: excessive skew between multiple lanes
[12.348] csi2rx: lane alignment timeout

# HS Rx timeout: sensor did not enter HS mode properly
[12.349] csi2rx: HS receive timeout on data lane 0

# FIFO overflow: SoC processing speed cannot keep up with sensor output rate
[12.350] csi2rx: FIFO overflow, frame dropped
```

#### 2.3.4 Common CSI Link Problem Diagnosis

| Error Type | Root Cause | Debug Method |
|------------|------------|--------------|
| Lane alignment timeout | PCB lane length mismatch > 5mm | Measure D+/D- waveforms with oscilloscope; request layout PCB revision |
| ECC/CRC errors | Missing termination resistors; EMI interference | Add 100Ω differential termination at lane end; investigate PCB routing |
| HS Rx timeout | MCLK not oscillating; PLL lock failure | Check MCLK waveform; read sensor PLL lock status register |
| Unstable frame rate / frame drops | link-frequencies configuration inconsistent with sensor register PLL setting | Recalculate pixel clock and MIPI bit rate |

### 2.4 Step 4: First Frame Bring-up

#### 2.4.1 Capture RAW Frames with yavta

```bash
# Install yavta (advanced V4L2 test tool)
$ git clone https://git.ideasonboard.org/yavta.git && cd yavta && make

# Capture 1 frame RAW10 (packed, 3840x2160)
$ ./yavta -n 4 -c1 -f SRGGB10P -s 3840x2160 \
  --file=capture-#.raw /dev/video0
```

#### 2.4.2 Quick RAW Frame Preview

```bash
# Use raw2rgbpnm to convert RAW to previewable PNM format
# (raw2rgbpnm from https://git.recoil.org/rawtools/raw2rgbpnm)
$ raw2rgbpnm -s 3840x2160 -f RGGB -b 10 capture-0.raw preview.ppm

# Or use ImageMagick for rough RAW frame parsing (assumes debayered)
$ convert -size 3840x2160 -depth 10 gray:capture-0.raw preview.png
```

#### 2.4.3 Bayer Pattern Identification

The Bayer pattern (拜尔图案) of a RAW image determines the correctness of demosaic. The four common arrangements:

```
RGGB:  R G R G ...    GRBG:  G R G R ...
       G B G B ...           R B R B ...

BGGR:  B G B G ...    GBRG:  G B G B ...
       G R G R ...           B R B R ...
```

**Quick diagnosis method:** On the first RAW frame, use a program to extract and compute the mean values of: even-row even-column, even-row odd-column, odd-row even-column, and odd-row odd-column pixels. When photographing a neutral gray target under natural light:

- If the (0,0) position channel mean is >> the other three → that channel is R (RGGB start)
- If two channel means are close and highest → they are G (green channels)
- If one channel mean is lowest → that channel is B

When the Bayer pattern is misconfigured, the image will exhibit fixed color cast (e.g., green/purple, or magenta).

#### 2.4.4 First Frame Anomaly Diagnosis

| Frame State | Possible Cause | Next Step |
|-------------|----------------|-----------|
| **All-black frame** (all pixels ≤ black level) | BLC offset too large; sensor not in streaming state; exposure set to 0 | Check BLC setting; confirm streaming-on register; set maximum gain + exposure |
| **All-white/saturated frame** (all pixels saturated) | Exposure + gain far exceeds normal; sensor analog gain step error | Set AE target to auto; manually set lower exposure value |
| **Fixed pattern (FPN)** | Sensor initialization not complete; streaming timing issue with reset logic | Check completeness of sensor initialization register sequence |
| **Half-frame / stitching error** | Buffer size calculation error; stride misalignment | Check `bytesperline` calculation in V4L2 format |
| **Image upside down** | MIPI lane polarity reversal (P/N swapped); sensor VFLIP register not configured | Try writing VFLIP register in sensor driver |
| **Image horizontally mirrored** | MIPI data lane order reversed (Lane0↔Lane1); sensor HMIRROR not configured | Check `data-lanes` order in DTS against schematic; write HMIRROR register |

### 2.5 Step 5: Incremental Verification of Basic ISP Modules

**Verification principle:** Enable only one ISP module at a time; bypass (旁路) all others. Verify incrementally.

#### 2.5.1 BLC (Black Level Correction) Verification

**Objective:** Confirm that the optical black (OB, Optical Black) region mean is within a reasonable range.

For 12-bit RAW data, the typical OB mean should be **64 ± 16 DN** (refer to the sensor datasheet's OB target for the specific value).

```python
import numpy as np

# Load RAW frame (assuming RGGB, 12-bit, width 4208, height 3120)
raw = np.fromfile("frame0.raw", dtype=np.uint16).reshape(3120, 4208)

# Typical sensor reserves OB rows at the top or left of the image (e.g., top 8 rows)
ob_rows = raw[:8, :]  # Take the first 8 rows as the OB region

print(f"OB mean: {ob_rows.mean():.1f} DN")
print(f"OB std dev: {ob_rows.std():.2f} DN")
print(f"Expected range: 48~80 DN (12-bit)")

# Verify after subtracting BLC
blc_offset = ob_rows.mean()
raw_blc = raw.astype(np.int32) - int(blc_offset)
raw_blc = np.clip(raw_blc, 0, 4095)
print(f"After BLC - min: {raw_blc.min()}, max: {raw_blc.max()}")
```

**Anomaly criteria:**
- OB mean > 200 DN → Abnormal BLC setting or sensor OB register not configured
- OB mean < 10 DN → Sensor has already applied BLC internally; no external BLC needed

#### 2.5.2 LSC (Lens Shading Correction) Verification

**Objective:** Confirm that the corner-to-center brightness attenuation (Rolloff) matches expectations.

```python
# Calculate corner-to-center brightness ratio (using the Gr channel as example)
H, W = raw_blc.shape
# Extract Gr channel (even rows, odd columns in RGGB)
gr = raw_blc[0::2, 1::2]

# Define center and corner regions (each 100x100 pixels)
hw, ww = gr.shape
margin = 50
center_mean = gr[hw//2-margin:hw//2+margin, ww//2-margin:ww//2+margin].mean()
tl_mean = gr[:margin*2, :margin*2].mean()
tr_mean = gr[:margin*2, -margin*2:].mean()
bl_mean = gr[-margin*2:, :margin*2].mean()
br_mean = gr[-margin*2:, -margin*2:].mean()

print(f"Corner/center brightness ratio (Rolloff):")
print(f"  Top-left:     {tl_mean/center_mean:.3f}")
print(f"  Top-right:    {tr_mean/center_mean:.3f}")
print(f"  Bottom-left:  {bl_mean/center_mean:.3f}")
print(f"  Bottom-right: {br_mean/center_mean:.3f}")
# Normal values are typically 0.55~0.85 (depending on the lens)
# If below 0.4, LSC must be enabled
```

#### 2.5.3 Demosaic Verification

**Objective:** RGB image after demosaic should have basically correct colors (green objects appear green, red objects appear red).

Quick verification method:
1. Photograph a standard Macbeth color checker (if available) or white paper with colored objects
2. Apply bilinear interpolation demosaic (minimum computation) to get an RGB image
3. Open and preview with ImageMagick or Python PIL

```bash
# Use dcraw for quick demosaic preview of the RAW file
# (dcraw supports many RAW formats, suitable for debug purposes)
$ dcraw -v -w -o 1 -q 0 -T capture-0.dng
# -w: use white balance metadata
# -o 1: sRGB output
# -q 0: bilinear demosaic (fastest)
# -T: output TIFF
```

**Demosaic anomaly characteristics:**
- **Color checkerboard / moiré pattern**: Bayer pattern configuration error (see §2.4.3)
- **Image overall green cast**: Bayer starting point error (treating G channel as R/B)
- **Colored fringing at detail edges (zipper artifact)**: Normal phenomenon; can be improved with a higher-quality demosaic algorithm

#### 2.5.4 AWB Initial Verification

**Objective:** Under D65 standard illuminant (natural daylight), white objects should approach neutral white (R≈G≈B) with AWB enabled.

```bash
# Use v4l2-ctl to read current AWB gain values
$ v4l2-ctl -d /dev/video0 --get-ctrl=red_balance
red_balance: 512

$ v4l2-ctl -d /dev/video0 --get-ctrl=blue_balance
blue_balance: 418

# Under D65 illuminant, normal R:G:B ≈ 1.6:1.0:1.4 gains
# AWB gains should be in the range 256~1024 (Q8 format)
```

If AWB cannot converge, check the following in order:
1. Whether the CCM (Color Correction Matrix) has loaded calibration values specific to this sensor
2. Whether the AWB algorithm's gray-world assumption is applicable to the current scene
3. Whether the exposure is reasonable (both overexposure and underexposure will cause AWB deviation)

---

## §3 Toolchain

### 3.1 Open-Source Debug Tools Overview

| Tool | Primary Use | Platform | How to Obtain |
|------|-------------|----------|---------------|
| **v4l2-ctl** | Sensor control, format setting, RAW frame capture, control query | Linux | `apt install v4l-utils` |
| **media-ctl** | Media pipeline topology view and configuration | Linux | `apt install v4l-utils` |
| **v4l2-compliance** | V4L2 driver compliance testing | Linux | `apt install v4l-utils` |
| **i2cdetect** | Scan I2C bus devices | Linux | `apt install i2c-tools` |
| **i2cget / i2cset** | Single I2C register read/write | Linux | `apt install i2c-tools` |
| **i2ctransfer** | Compound I2C transactions (write address + read data) | Linux | `apt install i2c-tools` |
| **yavta** | Advanced V4L2 capture and control testing | Linux | `git clone https://git.ideasonboard.org/yavta.git` |
| **raw2rgbpnm** | Quick RAW-to-PNM conversion for preview | Linux | GitHub: linuxtv/v4l-utils auxiliary |
| **dcraw** | RAW decode + demosaic preview | Linux/Mac/Win | `apt install dcraw` |
| **cam** | libcamera command-line client | Linux | Compile from libcamera source |
| **qcam** | libcamera Qt GUI preview | Linux | Compile from libcamera source |
| **gst-launch-1.0** | GStreamer pipeline testing (including libcamerasrc) | Linux | `apt install gstreamer1.0-tools` |
| **adb** | Android device debugging | Android | Android SDK Platform Tools |
| **systrace** | Android camera pipeline performance analysis | Android | Android SDK |

### 3.2 v4l-utils Detailed Usage

`v4l-utils` is the most essential toolset for Linux camera bring-up.

#### 3.2.1 v4l2-compliance — Driver Compliance Testing

After completing new driver development, it **must** pass `v4l2-compliance` testing:

```bash
# Run full compliance test on /dev/video0
$ v4l2-compliance -d /dev/video0 -f

# Test a subdev
$ v4l2-compliance -z /dev/media0 -e "ov5675 2-0010"

# Example output (passing):
# Total: 47, Succeeded: 47, Failed: 0, Warnings: 2
```

Common compliance failures:
- `VIDIOC_ENUM_FRAMESIZES` not implemented → add `enum_frame_size` callback
- Buffer type not correctly set → check `queue_setup` implementation

#### 3.2.2 media-ctl Pipeline Configuration Script

In actual projects, the pipeline configuration is typically written as a shell script:

```bash
#!/bin/bash
# setup_camera_pipeline.sh
# Configure the complete pipeline: OV5675 → MIPI CSI → ISP → Video

MEDIA_DEV=/dev/media0
SENSOR="ov5675 2-0010"
CSI_RX="csi2rx"
ISP="isp0"
VIDEO=/dev/video0

FMT="SRGGB10_1X10"
WIDTH=2592
HEIGHT=1944

# 1. Set sensor output format
media-ctl -d $MEDIA_DEV \
  --set-v4l2 "\"$SENSOR\":0[fmt:${FMT}/${WIDTH}x${HEIGHT}@1/30]"

# 2. Set CSI receiver input/output format
media-ctl -d $MEDIA_DEV \
  --set-v4l2 "\"$CSI_RX\":0[fmt:${FMT}/${WIDTH}x${HEIGHT}]"
media-ctl -d $MEDIA_DEV \
  --set-v4l2 "\"$CSI_RX\":1[fmt:${FMT}/${WIDTH}x${HEIGHT}]"

# 3. Set ISP input/output format (RAW in → YUV out)
media-ctl -d $MEDIA_DEV \
  --set-v4l2 "\"$ISP\":0[fmt:${FMT}/${WIDTH}x${HEIGHT}]"
media-ctl -d $MEDIA_DEV \
  --set-v4l2 "\"$ISP\":1[fmt:YUYV8_1X16/${WIDTH}x${HEIGHT}]"

# 4. Enable all links
media-ctl -d $MEDIA_DEV \
  --links "\"$SENSOR\":0->\"$CSI_RX\":0[1]"
media-ctl -d $MEDIA_DEV \
  --links "\"$CSI_RX\":1->\"$ISP\":0[1]"
media-ctl -d $MEDIA_DEV \
  --links "\"$ISP\":1->\"video0\":0[1]"

echo "Pipeline setup complete. Run: v4l2-ctl -d $VIDEO --stream-mmap"
```

### 3.3 libcamera Debug Framework

libcamera (https://libcamera.org/) is a modern open-source camera framework for the Linux platform, designed to replace the traditional V4L2 + userspace ISP debug model.

#### 3.3.1 libcamera Architecture

```
User application layer: cam / qcam / GStreamer / Android HAL
        ↓
libcamera core library (Camera Manager, Camera, Stream, Request)
        ↓
Pipeline Handler (SoC-specific pipeline drivers, e.g., rkisp1, ipu3, vimc)
        ↓
IPA (Image Processing Algorithms, trusted isolated algorithm module)
        ↓
V4L2 kernel drivers
```

The IPA module is responsible for 3A algorithms, separated from the pipeline handler. It can be an open-source implementation (e.g., Raspberry Pi IPA) or a proprietary binary.

#### 3.3.2 cam Command-Line Tool Usage

```bash
# List all available cameras in the system
$ cam -l
Available cameras:
1: Internal Camera [ov5675 2-0010]

# View stream configurations supported by the camera
$ cam -c 1 --info

# Capture 10 frames and save to PPM files
$ cam -c 1 --capture=10 --file=frame#.ppm

# Specify stream configuration (resolution and format)
$ cam -c 1 -s width=1920,height=1080,pixelformat=RGB888 --capture=1

# Output frame statistics (luminance histogram, etc., requires IPA support)
$ cam -c 1 --capture=30 -v
```

#### 3.3.3 libcamera IPA Module Debugging

For libcamera bring-up of a new sensor, a corresponding tuning configuration file must be created for the sensor:

```yaml
# /usr/share/libcamera/ipa/rkisp1/ov5675.yaml (example structure)
version: 1
algorithms:
  - BlackLevelCorrection:
      black_level: 4096   # BLC target value normalized to 16-bit
  - Lux: {}
  - AGC:
      min_shutter: 100    # Minimum exposure time in μs
      max_shutter: 33333  # Maximum exposure time in μs (corresponding to 30fps)
      min_analogue_gain: 1.0
      max_analogue_gain: 16.0
  - AWB:
      mode: auto
  - CCM: {}
  - GammaToneCurve: {}
```

### 3.4 Android Camera HAL Bring-up

#### 3.4.1 Android Camera Software Stack

```
Camera App (Camera2 API)
    ↓
CameraService (frameworks/av/services/camera/)
    ↓
Camera HAL3 Interface (hardware/interfaces/camera/)
    ↓
Camera HAL Implementation (vendor/xxx/camera/)
    ↓
Kernel V4L2 Driver
```

#### 3.4.2 HAL Enumeration Verification

```bash
# Verify whether the HAL correctly enumerates cameras on an Android device
$ adb shell dumpsys media.camera

# Example output:
# Camera 0 (BACK):
#   Facing: BACK
#   Number of streams: 3
#   ...

# View Camera HAL logs
$ adb logcat -s CameraService:V Camera3Device:V \
  android.hardware.camera.provider@2.4-service:V

# Capture a frame (requires triggering via camera app or CTS test)
$ adb shell am start -a android.media.action.STILL_IMAGE_CAMERA
```

#### 3.4.3 CTS (Compatibility Test Suite) Camera Testing

```bash
# Run Camera CTS tests to verify HAL implementation
$ cts-tradefed run cts -m CtsCameraTestCases \
  --test android.hardware.camera2.cts.CaptureRequestTest

# Run quick smoke test
$ cts-tradefed run cts -m CtsCameraTestCases \
  --test android.hardware.camera2.cts.StillCaptureTest#testSingleCapture
```

---

## §4 Common Bring-up Troubleshooting

The following table covers typical problems across all bring-up phases, ordered by frequency of occurrence.

| # | Symptom | Possible Cause | Diagnostic Command / Method | Resolution Direction |
|---|---------|----------------|----------------------------|----------------------|
| 1 | `i2cdetect` shows all `--`, no device response | DOVDD not powered on; Reset not released; I2C address wrong | `cat /sys/kernel/debug/regulator/dovdd/state`; oscilloscope on RESET pin | Check power tree and DTS GPIO polarity |
| 2 | I2C address is scanned but reading Chip ID returns 0x00 or 0xFF | Wrong register address width (8-bit vs 16-bit); sensor in low-power mode | Use `i2ctransfer` to manually construct 16-bit address read/write transactions | Confirm sensor register address width; send soft reset command before reading ID |
| 3 | `dmesg` shows `hs_rx_timeout` | MCLK not ready; MIPI termination not enabled; sensor PLL not locked | `dmesg \| grep -i "clk\|pll\|mipi"`; oscilloscope on MCLK waveform | Confirm MCLK frequency and enable timing; check SoC MIPI receiver-side registers |
| 4 | `dmesg` shows continuous ECC errors | PCB lane length mismatch (Δ > 5mm); MIPI trace impedance mismatch | Measure D+/D- resistance to ground on each lane; contact PCB layout to confirm length matching | Compensate lane delay (some SoCs support software deskew); request PCB revision |
| 5 | `v4l2-ctl --stream-mmap` reports `RESOURCE_BUSY` | Pipeline link not established; another process holds the video node | `media-ctl -p`; `fuser /dev/video0` | First run `media-ctl` to establish links; kill the occupying process |
| 6 | Capture succeeds but image is **all black** (all pixels ≤ BLC) | Sensor not in streaming state; exposure/gain set to 0; BLC offset too large | `v4l2-ctl --get-ctrl=exposure`; read sensor streaming register | Check streaming-on register write in `s_stream` callback; manually set maximum gain |
| 7 | Image is **all white / saturated** | Initial gain too large; extreme exposure before AE convergence | `v4l2-ctl --set-ctrl=exposure_absolute=100` (force low exposure) | During early bring-up, disable AE and manually set conservative exposure + gain |
| 8 | Image has **overall green or purple cast** | Bayer pattern configuration error (RGGB vs GRBG, etc.) | Analyze RAW four-channel means (see §2.4.3) | Modify `mbus_code` in DTS or driver to the correct Bayer format |
| 9 | Image is **upside down** | MIPI lane polarity reversal (P/N swapped); sensor VFLIP register not configured | Check MIPI lane P/N connections in schematic and PCB netlist | Write sensor VFLIP register as software compensation; or request hardware PCB fix |
| 10 | Image is **horizontally mirrored** | MIPI data lane order reversed (Lane0↔Lane1); sensor HMIRROR not configured | Check consistency of DTS `data-lanes` order with schematic | Modify DTS `data-lanes = <2 1>` to swap order; or write HMIRROR register |
| 11 | Image has **horizontal stripe noise** (row noise / FPN) | Sensor initialization sequence incomplete (OTP not loaded); DVDD ripple too large | Oscilloscope on DVDD ripple (should be < 20mV); confirm OTP initialization code | Load complete initialization register sequence per sensor datasheet; improve power filtering |
| 12 | Image has **vertical stripe pattern** (column noise) | Non-uniform analog ADC offset; sensor requires column BLC calibration | Read sensor column gain calibration registers | Execute the column BLC calibration procedure required by the sensor vendor |
| 13 | **Frame rate below expectation** (e.g., expected 30fps, actual 15fps) | link-frequencies misconfigured (insufficient bandwidth); ISP processing timeout; multi-exposure HDR mode accidentally enabled | `v4l2-ctl --get-parm`; `dmesg` for frame interval log | Recalculate MIPI bit rate; check ISP processing time; confirm HDR mode setting |
| 14 | **AWB cannot converge**, image persistently color-shifted | CCM parameters not loaded (using calibration data from wrong sensor); AWB gray-world assumption fails in non-natural scenes | Print current CCM matrix values; photograph under standard illuminant | Load CCM calibration file for the correct sensor; check AWB algorithm's scene adaptability |
| 15 | **Focus not working** (AF not converging) | VCM (Voice Coil Motor) driver not loaded; AF statistics region misconfigured; lens travel mechanically limited | `v4l2-ctl --list-ctrls \| grep focus`; check VCM I2C communication | Confirm VCM driver is loaded; check AF ROI configuration; measure VCM coil impedance |
| 16 | **One camera cannot be enumerated in a multi-camera system** | Shared I2C address conflict; MIPI switch misconfigured | `i2cdetect` scan on both buses; check MIPI mux control signals | Assign independent I2C buses or different I2C addresses to each sensor |
| 17 | Android HAL **camera enumeration failed** (`dumpsys media.camera` has no output) | HAL .so not loaded; manifest misconfigured; SELinux denying access | `adb logcat -s android.hardware.camera.provider`; `adb shell dmesg` | Check `android.hardware.camera.provider@2.4-service` startup state; check sepolicy rules |

---

## §5 Advanced Bring-up Techniques

### 5.1 Fast Root-Cause Identification via MIPI Error Registers

Most SoC MIPI CSI receivers provide error status registers that can be read directly:

```bash
# Read MIPI CSI error status register (i.MX8M Plus as example, address is illustrative)
# Actual addresses must be looked up in the SoC's public Reference Manual
$ devmem2 0x32E30060 w   # CSI2RX ERROR register

# Read CSI statistics via debugfs (supported by some SoCs)
$ cat /sys/kernel/debug/csi2rx/statistics
frame_count: 1024
ecc_1bit_errors: 0
ecc_2bit_errors: 0
crc_errors: 0
frame_sync_errors: 0
```

### 5.2 Real-Time Preview with GStreamer

In libcamera or direct V4L2 scenarios, GStreamer can be used for real-time preview to help quickly assess image quality:

```bash
# Preview directly from V4L2 device (YUV format)
$ gst-launch-1.0 v4l2src device=/dev/video0 \
  ! video/x-raw,width=1920,height=1080,format=NV12 \
  ! videoconvert \
  ! autovideosink

# Preview via libcamera (requires gstreamer1.0-libcamera)
$ gst-launch-1.0 libcamerasrc \
  ! video/x-raw,width=1920,height=1080,format=NV12 \
  ! videoconvert \
  ! fpsdisplaysink video-sink=autovideosink sync=false

# Preview while simultaneously saving (T-branch pipeline)
$ gst-launch-1.0 libcamerasrc \
  ! tee name=t \
  t. ! queue ! videoconvert ! autovideosink \
  t. ! queue ! videoconvert ! x264enc ! mp4mux ! filesink location=test.mp4
```

### 5.3 Bring-up Checklist

Before entering the ISP tuning stage, a complete bring-up should execute the following checklist:

```
[ ] DOVDD/AVDD/DVDD voltages measured within spec range (±5%)
[ ] MCLK frequency confirmed with oscilloscope/frequency counter (error < 100ppm)
[ ] I2C can read the correct Chip ID
[ ] Sensor initialization register sequence written completely (consistent with FAE-provided init seq)
[ ] MIPI lane count matches DTS data-lanes configuration
[ ] link-frequencies calculated value is consistent with sensor register PLL configuration
[ ] v4l2-compliance 0 failures
[ ] Can capture a non-all-black, non-all-white RAW frame
[ ] OB mean is within reasonable range (48~80 DN for 12-bit)
[ ] Bayer pattern identified correctly
[ ] RGB preview image colors are basically correct (demosaic passes)
[ ] AWB roughly converges under standard illuminant
```

---

## §6 Reference Resources

All technical content in this chapter is based on the following public resources. Readers can access the original documentation via the links below:

### Open-Source Code Repositories

| Resource | URL | Description |
|----------|-----|-------------|
| Linux kernel sensor drivers | https://github.com/torvalds/linux/tree/master/drivers/media/i2c | Mainline sensor driver code (imx258, ov5675, ov13858, etc.) |
| v4l-utils | https://git.linuxtv.org/v4l-utils.git | v4l2-ctl, media-ctl, v4l2-compliance source code |
| libcamera | https://git.libcamera.org/libcamera/libcamera.git | Complete libcamera framework |
| yavta | https://git.ideasonboard.org/yavta.git | Advanced V4L2 test tool |

### Official Documentation

| Resource | URL |
|----------|-----|
| V4L2 API documentation | https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/v4l2.html |
| Media Controller API | https://www.kernel.org/doc/html/latest/userspace-api/media/mediactl/media-controller.html |
| Linux Camera Subsystem | https://www.kernel.org/doc/html/latest/driver-api/media/index.html |
| MIPI Alliance CSI-2 specification (public summary) | https://www.mipi.org/specifications/csi-2 |
| Android Camera HAL3 interface | https://source.android.com/docs/core/camera |
| libcamera documentation | https://libcamera.org/api-html/ |

---

## Glossary

| Term | Full Name | Description |
|------|-----------|-------------|
| **V4L2** | Video4Linux2 | Linux video capture/output driver framework, second version |
| **subdev** | Sub-Device | V4L2 sub-device representing an independent module in the pipeline (sensor, ISP, etc.) |
| **Media Controller** | — | Linux media controller framework for managing and configuring camera pipeline topology |
| **DTS** | Device Tree Source | Device tree source file describing hardware connection information for the Linux kernel |
| **MIPI CSI-2** | Camera Serial Interface 2 | MIPI Alliance-defined camera data transfer interface standard, second version |
| **D-PHY** | D Physical Layer | Most common MIPI CSI-2 physical layer, using differential signal transmission |
| **C-PHY** | C Physical Layer | Newer MIPI physical layer, uses 3-wire trio transmission for higher bandwidth efficiency |
| **HS mode** | High Speed Mode | D-PHY high-speed data transfer mode, differential swing ~200mV |
| **LP mode** | Low Power Mode | D-PHY low-power control mode, used for control signals and lane state switching |
| **ECC** | Error Correction Code | Error correction code in MIPI CSI-2 packet header, can correct 1-bit errors |
| **CRC** | Cyclic Redundancy Check | Cyclic redundancy check used to verify data packet integrity |
| **MCLK** | Master Clock | Master clock provided by the SoC to the sensor, typically 24MHz |
| **DOVDD** | Digital I/O Supply Voltage | Sensor IO supply, typically 1.8V, matching SoC GPIO voltage level |
| **AVDD** | Analog Supply Voltage | Sensor analog supply, typically 2.8V, powering the pixel array |
| **DVDD** | Digital Core Supply Voltage | Sensor digital core supply, typically 1.0~1.2V, powering digital logic |
| **OB** | Optical Black | Optically blocked pixel region used to measure BLC offset |
| **BLC** | Black Level Correction | Black level correction to eliminate fixed offset from sensor readout circuitry |
| **LSC** | Lens Shading Correction | Lens shading correction to compensate for corner darkening due to lens optical properties |
| **CCM** | Color Correction Matrix | Color correction matrix converting sensor RGB to a standard color space |
| **AWB** | Auto White Balance | Auto white balance to estimate and compensate for illuminant color temperature |
| **AE** | Auto Exposure | Auto exposure to control shutter time and gain for proper image brightness |
| **AF** | Auto Focus | Auto focus to control lens focal length for sharp subject rendering |
| **3A** | AE + AF + AWB | Collective term for the three major automatic control systems in a camera |
| **IPA** | Image Processing Algorithms | Trusted isolated module in libcamera responsible for 3A algorithms |
| **HAL** | Hardware Abstraction Layer | Hardware abstraction layer in Android connecting the Camera2 API to underlying drivers |
| **VCM** | Voice Coil Motor | Voice coil motor, the actuator that drives lens movement in AF modules |
| **FPN** | Fixed Pattern Noise | Fixed pattern noise produced by non-uniform sensor fabrication |
| **DNG** | Digital Negative | Open RAW image format defined by Adobe, widely used in debug tools |
| **skew** | Lane Skew | Timing offset between MIPI lanes, primarily caused by unequal PCB trace lengths |
| **bring-up** | — | The complete process of commissioning new hardware/drivers from scratch to a usable state |

---

## Chapter Summary

The essence of ISP bring-up is a **layer-by-layer verification** engineering process:

1. **Do not skip layers**: I2C communication must be confirmed first, then the first frame, then image quality.
2. **Use tools effectively**: `i2c-tools`, `v4l-utils`, and `libcamera` cover the entire bring-up chain; mastering them can reduce debug time from days to hours.
3. **Isolate first, then integrate**: Each ISP module (BLC/LSC/Demosaic/AWB) should be bypassed and verified individually to prevent inter-module interference from obscuring the true problem.
4. **Record phenomena**: Every debug session should save `dmesg` output, RAW frames, and key register states to provide a basis for subsequent problem tracing.
5. **Hardware problems cannot be fully compensated by software**: Hardware issues such as MIPI lane skew and power supply ripple must be thoroughly resolved during the bring-up stage; otherwise they will persist as probabilistic failures in mass production.

The next chapter (Volume 2, Chapter 30) will build on the bring-up foundation of this chapter to provide an in-depth introduction to **ISP system-level tuning methodology**, including calibration toolchains, image quality assessment (IQA) frameworks, and tuning strategies for different application scenarios.
