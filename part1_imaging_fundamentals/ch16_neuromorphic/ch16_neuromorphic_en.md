# Part 1, Chapter 16: Neuromorphic Cameras (Neuromorphic / Event Camera)

> **Pipeline position:** Novel sensor paradigm; replaces or complements conventional frame cameras
> **Prerequisites:** Chapter 3 (Sensor Physics), Chapter 1 (ISP Pipeline Overview)
> **Reader path:** Researchers, systems engineers

---

## §1 Theory

### 1.1 Working Principle of Event Cameras

The logic of a conventional frame camera is a periodic cycle of "global exposure — readout — processing": regardless of whether the scene is changing, a new image frame is refreshed at fixed intervals. This paradigm carries over the design philosophy of the film era and is essentially a uniform temporal sampling of visual information, not demand-driven sampling.

Event cameras overturn this logic entirely. Their inspiration comes from the biological retina: photoreceptor cells in the retina do not send images to the brain at a fixed frame rate; instead, they generate spike signals only when local brightness changes. An event camera is an engineering simulation of this mechanism — each pixel is an independent, asynchronous sensing unit that continuously monitors its log-luminance. Once the change exceeds a preset threshold $C$, the pixel immediately outputs an **event**.

The complete representation of a single event is a four-tuple:

$$e_k = (x_k,\ y_k,\ t_k,\ p_k)$$

- $(x_k, y_k)$: pixel coordinates of the triggered event
- $t_k$: precise timestamp of the event (microsecond resolution)
- $p_k \in \{+1, -1\}$: polarity — $+1$ indicates a brightness increase, $-1$ a brightness decrease

The entire sensor outputs not a sequence of 2D images, but a continuous, asynchronous event stream. There is no concept of a frame, no exposure time, no row scanning — each pixel acts independently on its own time axis.

**Mathematical description of the trigger condition:** Let the log-luminance of pixel $(x,y)$ at time $t$ be $L(x,y,t) = \ln I(x,y,t)$. The trigger condition is:

$$\Delta L(x,y,t) = L(x,y,t) - L(x,y,t_{\text{last}}) \geq p \cdot C$$

where $t_{\text{last}}$ is the time of the pixel's last trigger event and $C$ is the contrast threshold, with typical values of $0.1 \sim 0.5$. Because triggering is based on **logarithmic** luminance change, the corresponding relative linear brightness change is approximately $e^C - 1$: $C=0.1$ corresponds to about 10.5% brightness change, $C=0.5$ corresponds to about 65%. In real devices, the ON threshold (brightness increase) and the OFF threshold (brightness decrease) may be asymmetric, and there is typically about 10%–30% threshold variation across pixels due to fabrication non-uniformity.

This "on-demand triggering" mechanism brings two fundamental advantages: first, scene regions that are not moving produce no events at all, making the data naturally sparse; second, the faster a region moves, the more events it generates — temporal resolution is determined by the physical response speed of the pixel, not the frame rate.

### 1.2 Comparison with Conventional Frame Cameras

The most direct way to understand the value of event cameras is to compare them with conventional frame cameras along key dimensions:

| Dimension | Conventional Frame Camera | Event Camera |
|-----------|--------------------------|--------------|
| **Temporal resolution** | Frame period (typical 33 ms @ 30 fps) | Single-event latency < 1 μs |
| **Dynamic range** | 70–80 dB (ordinary CMOS) | ~140 dB |
| **Motion blur** | Unavoidable for high-speed motion | Theoretically zero motion blur |
| **Data rate** | Fixed (resolution × frame rate × bit depth) | Adaptive (approaches zero when scene is static) |
| **Power consumption** | ~100–500 mW (including ISP) | ~10 mW (sensor alone) |
| **Latency** | Frame period + readout + ISP pipeline | Output immediately upon event trigger |
| **Data format** | Regular 2D pixel array | Unstructured event point cloud |
| **Lighting conditions** | Noisy or saturated under bright or dim light | Operates normally across wide dynamic range |

The dynamic range difference is particularly striking. Conventional CMOS image sensors saturate under strong light and are noise-dominated in the dark; the usable range is approximately 70–80 dB. High-end HDR sensors can achieve over 100 dB through multi-exposure merging, but at the cost of reduced frame rate and complex ISP pipelines. Event cameras achieve approximately 140 dB in dynamic range because the logarithmic response curve naturally compresses a wide range of intensities; capturing direct sunlight and a dark interior simultaneously poses almost no challenge.

Another transformative advantage is temporal resolution. For a 1000 fps high-speed camera, the temporal resolution is 1 ms — filming a flying bullet still produces trails. An event camera's single-pixel response latency is in the microsecond range; for virtually any "high-speed" scenario encountered in practice, temporal resolution can be treated as effectively infinite.

Event cameras are not without trade-offs, however: their output format is completely incompatible with traditional computer vision algorithms, and processing event streams requires dedicated representation methods and algorithms — this is discussed in detail below.

### 1.3 Commercial Event Camera Products

Current commercially available event cameras come primarily from the following vendors:

**iniVation (Switzerland)**

iniVation is a pioneer in the event camera field; it originates from the research group of Professor Tobi Delbruck at the University of Zurich. Representative products:

- **DAVIS346:** Resolution 346×260; simultaneously outputs an event stream and ordinary grayscale frames (DAVIS = Dynamic and Active-pixel Vision Sensor); the most widely used hybrid sensor in academia, supporting USB3 high-speed transfer; temporal resolution approximately 1 μs, dynamic range > 120 dB.
- **DVXplorer:** Pure event sensor; resolution 640×480; focused on high-speed motion capture scenarios.

**Prophesee (France)**

Prophesee specializes in the Metavision series of industrial-grade event sensors, with a product line ranging from low-power embedded to high-resolution industrial inspection:

- **IMX636** (co-developed with Sony): Resolution 1280×720; dynamic range > 120 dB; event latency < 1 μs; extremely low power consumption. IMX636 is a representative product from the Sony–Prophesee collaboration, marking the entry of the world's leading consumer-grade image sensor manufacturer into the event camera field with advanced stacked CMOS technology, and pushing event cameras from research-grade devices toward volume supply. It should be noted that iniVation and Prophesee had already commercially mass-produced multiple generations of industrial and research-grade event sensors (DVS128, DAVIS240, Gen3/Gen4, etc.) before IMX636; the significance of IMX636 lies primarily in the involvement of mainstream consumer-grade manufacturing infrastructure.
- **EVK4:** Resolution 1280×720; Prophesee's own evaluation kit; rapid prototyping is possible together with the Metavision SDK.

**Samsung**

Samsung has studied DVS (Dynamic Vision Sensor) architectures based on standard CMOS processes and has published several process integration papers; no large-scale commercial products are available yet, but it demonstrates the interest of consumer electronics giants in this space.

**Sony**

The IMX636, as the result of the Sony–Prophesee collaboration, marks an important milestone in event cameras transitioning from the laboratory to mass production. Sony's manufacturing process expertise and supply chain capabilities will substantially lower the cost barrier for event sensors.

**Typical parameter comparison:**

| Model | Resolution | Dynamic Range | Event Latency | Power | Notes |
|-------|-----------|---------------|---------------|-------|-------|
| DAVIS346 | 346×260 | >120 dB | ~1 μs | ~170 mW | Hybrid frame + events |
| DVXplorer | 640×480 | >120 dB | ~1 μs | ~100 mW | Pure events, low latency |
| IMX636 | 1280×720 | >120 dB | <1 μs | ~10 mW | Volume consumer grade |
| EVK4 | 1280×720 | >120 dB | <1 μs | ~200 mW | Industrial evaluation kit |

### 1.4 Event Stream Representation Methods

The raw event stream is a sparse point set in space-time and cannot be fed directly into conventional CNN or frame-processing algorithms. To bridge event cameras with the existing computer vision ecosystem, researchers have proposed several representation methods, each with its own trade-offs.

**(1) Event Frame Accumulation**

Within a fixed time window $[t_0, t_0 + \Delta t]$, all events are accumulated by coordinate into a 2D image:

$$F(x,y) = \sum_{k: (x_k,y_k)=(x,y),\ t_k \in [t_0, t_0+\Delta t]} p_k$$

Positive-polarity events count as $+1$ and negative-polarity as $-1$, yielding a "pseudo-frame" that can be processed by conventional image algorithms. This method is simple to implement, but the choice of time window is a trade-off: a window that is too long produces motion blur (the same problem as a frame camera); a window that is too short yields too few events and a sparse image.

**(2) Event Voxel Grid**

The time dimension is also discretized into $B$ time bins, constructing a 3D tensor $V \in \mathbb{R}^{B \times H \times W}$:

$$V_b(x,y) = \sum_k p_k \cdot \max\left(0, 1 - \left| \frac{t_k - t_b}{\Delta t_b} \right|\right) \cdot \mathbf{1}_{(x_k,y_k)=(x,y)}$$

where $t_b$ is the center timestamp of the $b$-th time bin; bilinear interpolation ensures continuity along the time axis. The voxel grid retains more temporal information than the event frame and is the most commonly used input representation for current deep learning methods, at the cost of $B$ times the memory footprint (typically $B = 5 \sim 10$).

**(3) Surface of Active Events (SAE) / Time Surface**

Each pixel stores the timestamp of the most recent event at that location:

$$\mathcal{T}(x,y,p) = t_k \quad \text{where } k = \arg\max_{k': (x_{k'},y_{k'})=(x,y),\ p_{k'}=p} t_{k'}$$

Separate time surfaces can be constructed for positive and negative polarity. Because recent events update the timestamps, the SAE forms an "event age map" on which edges and motion trajectories are clearly visible; it is commonly used for optical flow estimation and feature tracking.

**(4) Event Polarity Frame**

Positive-polarity and negative-polarity events are accumulated separately into two channels, forming a two-channel image. This representation explicitly separates brightness-increase and brightness-decrease information, which is more informative for certain applications (such as motion direction estimation).

**Comparison of representation methods:**

| Representation | Dimensions | Temporal Info Retained | Memory | Common Use Cases |
|----------------|-----------|----------------------|--------|-----------------|
| Event frame accumulation | 2D | Low (temporal order lost) | Low | Rapid prototyping |
| Voxel grid | 3D | Medium (discretized) | Medium | Deep learning input |
| Time surface (SAE) | 2D×2 | High (relative timing) | Low | Optical flow, tracking |
| Polarity frame | 2D×2 | Low | Low | Motion direction estimation |

### 1.5 Image Reconstruction from Events

Although event cameras do not directly output grayscale images, many applications still require reconstructing a visualizable intensity image — for example in pure-event systems with no frame camera, or when event results must be passed to downstream algorithms that depend on images.

**E2VID (Events-to-Video)**

Rebecq et al. (2019) proposed E2VID, which uses a recurrent convolutional neural network (RCNN) to reconstruct high-quality intensity images from event streams. The core idea is that the event stream records the temporal derivative of log-intensity; integrating it over time recovers the intensity variation. The RCNN maintains hidden state across time via ConvLSTM units, implicitly performing this integration.

The network input is an event voxel grid representation; the output is a grayscale frame for the corresponding time interval. E2VID's reconstruction quality under high dynamic range and high-speed scenarios significantly surpasses conventional camera frames, especially when the conventional camera is completely saturated or heavily motion-blurred.

**FireNet**

FireNet (Scheerlinck et al., WACV 2020) is an efficient neural network for real-time event image reconstruction. Like E2VID it belongs to the events-to-image reconstruction family, but it is not a direct lightweight version of E2VID. FireNet uses extensive depth-wise separable convolutions and similar techniques to design an independent lightweight encoder-decoder module from scratch; compared to E2VID's multi-scale recurrent U-Net architecture it has a distinct design philosophy, reducing parameter count and computation by approximately one order of magnitude while maintaining high reconstruction quality, enabling real-time operation on embedded platforms such as Jetson.

**Physics-based integration methods**

Another class of methods directly exploits the physical meaning of events: since each event represents a $\pm C$ change in log-intensity, integrating events along the time axis yields a relative intensity change map. Combined with an initial frame (a synchronized frame from DAVIS or an estimated initial value), the absolute intensity can be tracked over time. These methods require no training data but are sensitive to noise accumulation.

**Application: high-speed slow-motion synthesis**

Exploiting the microsecond temporal resolution of event cameras, hundreds of "virtual frames" can be inserted between two ordinary image frames to achieve a super-slow-motion video effect without the expensive equipment and large storage requirements of a conventional high-speed camera.

### 1.6 Event Camera + Frame Camera Fusion

Systems that rely solely on event cameras face a practical challenge: when the scene is static, no events are generated and there is no way to know the current absolute intensity values — yet conventional frame cameras perform best precisely in static scenes. The two sensor types are naturally complementary, so hybrid fusion architectures have attracted considerable attention.

**DAVIS architecture: on-chip fusion**

The core characteristic of the DAVIS (Dynamic and Active-pixel Vision Sensor) sensor is that each pixel unit internally integrates a dual-path readout circuit: the photocurrent generated by a single photodiode is simultaneously fed into two parallel circuits — an asynchronous event detection path (DVS path, triggered by log-luminance changes) and a synchronous active-pixel frame readout path (APS path, sampling absolute luminance to generate image frames). This is not a simple combination of two independent pixel arrays; it is dual-function fusion implemented within a single pixel. This design guarantees perfect spatial alignment (no parallax) and precise temporal synchronization between frames and events.

**Motion deblurring**

Motion blur in conventional cameras at high speeds is fundamentally the time integral of luminance over the exposure duration. Event cameras record the intensity change trajectory during the exposure at microsecond precision, enabling the sharp "instantaneous" image to be recovered by inversion. The EDI (Event-based Double Integral) method proposed by Pan et al. (2019) exploits this idea exactly: the blurry image and the events from the corresponding time interval are jointly optimized to reconstruct a sharp frame.

**HDR video synthesis**

The ~140 dB dynamic range of event cameras far exceeds that of conventional CMOS. Fusing the two can generate a video stream that simultaneously has high frame rate and high dynamic range, without the multi-exposure sequences required by conventional HDR merging algorithms.

**High-speed super-resolution**

Combining the absolute intensity reference provided by the frame camera with the temporal detail provided by the event camera, low-frame-rate video can be super-resolved in the time dimension to synthesize video sequences at 1000 fps and above, while preserving the spatial resolution of the conventional camera.

### 1.7 ISP Perspective: How to Process Event Data

From the perspective of a traditional ISP engineer, event cameras require almost none of the classic ISP pipeline — no Bayer demosaicing, no white balance, no color matrix, no gamma compression. However, event data is not completely clean; it still requires a dedicated pre-processing pipeline:

**Hot-pixel filtering**

Some pixels, due to manufacturing defects or leakage currents, continuously trigger events at very high rates even with no luminance change, forming "hot pixels." A hot pixel's event frequency is far higher than that of normal pixels; it can be eliminated by computing per-pixel event frequency statistics and masking pixels with abnormally high rates.

**Temporal correlation denoising**

Real luminance-change events typically have spatial-temporal continuity (neighboring pixels trigger at nearby times), whereas random noise events are spatially and temporally isolated. Temporal correlation filters (e.g., "nearest-neighbor temporal filter") can effectively distinguish signal from noise: if an event has no other events in its spatial neighborhood within a time window $\Delta t$, it is classified as noise and discarded.

**Time surface computation**

Converting the event stream into a time surface (SAE) is the entry point for many downstream algorithms — this step is analogous to the format conversion step in conventional ISP (Raw → RGB, analogous to Events → Time Surface).

**Event rate control**

Under strong illumination, fast motion, or low-threshold settings, the event rate may exceed the system processing bandwidth (typical upper limit approximately $10^7 \sim 10^8$ events/s). In such cases, adaptive threshold adjustment or event subsampling is needed to control the data volume — analogous to frame rate control in conventional ISP.

---

## §2 Calibration

### 2.1 Intrinsic Calibration of Event Cameras

The intrinsic calibration of an event camera (focal length, principal point, distortion coefficients) follows the same principle as for conventional cameras, but the data collection method is different — since a static checkerboard image cannot be captured directly, motion must be used to trigger events that "reveal" the calibration board.

**Calibration procedure:**

1. Wave a checkerboard or a flashing LED array in front of the camera to trigger events.
2. Accumulate events over a period of time into an event frame, then extract corners or circle centers from it.
3. Solve for intrinsics using the Zhang method (or similar) on corner correspondences from multiple poses.

The `dv-calib` tool provided by iniVation and the Kalibr toolbox both support event camera intrinsic calibration. Prophesee's Metavision SDK also integrates a calibration module based on flashing patterns.

**Notes:**

- Low-contrast regions produce few events; corner detection may be unstable. It is recommended to calibrate under uniform illumination.
- Event cameras typically have lower pixel counts than conventional cameras and larger pixel sizes; distortion is usually mild, but calibration is still needed for accuracy.

### 2.2 Joint Extrinsic Calibration of RGB and Event Cameras

Hybrid sensors such as DAVIS share a single pixel array for the frame camera and the event camera; in the ideal case the extrinsic matrix is the identity (perfect alignment). For independent RGB camera + event camera systems (e.g., an RGB-E stereo setup), the rotation matrix $R$ and translation vector $t$ between the two must be calibrated.

The calibration method is to fix the system and acquire data synchronously: the frame camera captures a static checkerboard; the event camera side obtains corresponding corner events by waving the checkerboard or using a flashing pattern. The extrinsics are then solved by using corresponding point pairs to solve the PnP problem.

The Kalibr toolbox supports camera-event joint calibration and is currently the most widely used tool in academia.

### 2.3 Contrast Threshold Calibration

The contrast threshold $C$ is the most critical internal parameter of an event camera; it directly affects the event rate, dynamic range utilization, and noise level. Due to fabrication variations, the actual threshold may exhibit 10%–30% within-chip non-uniformity around its nominal value.

**Threshold calibration method:**

1. Use a uniform-luminance LED panel (adjustable brightness) that increases or decreases brightness at a known rate; measure the actual trigger threshold of each pixel.
2. Build a per-pixel threshold map, which is used in subsequent event processing to compensate for non-uniformity.

In practical engineering, precise per-pixel threshold calibration is cumbersome; typically only the global average threshold is calibrated, and within-chip non-uniformity is treated as noise.

---

## §3 Tuning

### 3.1 Contrast Threshold Setting

Setting the contrast threshold $C$ is central to tuning an event camera system. It is fundamentally a trade-off between signal-to-noise ratio and event rate:

- **Threshold too low** ($C < 0.1$): Background noise and minor vibrations also trigger events; the event rate surges; effective information is buried in noise; system bandwidth may be overloaded.
- **Threshold too high** ($C > 0.5$): Only dramatic luminance changes trigger events; slow motion or low-contrast targets may go completely undetected; the dynamic range advantage cannot be fully utilized.

**Practical recommendations:**

| Application Scenario | Recommended Threshold $C$ | Notes |
|---------------------|--------------------------|-------|
| High-speed collision detection | 0.3–0.5 | Focus on dramatic changes; suppress background |
| Slow gesture recognition | 0.1–0.2 | Capture subtle motion |
| Outdoor automotive driving | 0.2–0.3 | Balance noise and sensitivity |
| Starfield / extreme low-light | 0.05–0.1 | Low threshold; requires stronger noise filtering |

Many modern event cameras support bias register configuration: the threshold can be adjusted equivalently by tuning on-chip circuit bias currents, without requiring recalibration.

### 3.2 Noise Filter Parameters

The key parameter of the temporal correlation filter is the **correlation time window** $\Delta t_{noise}$ — the temporal neighborhood size used to classify an event as noise.

- $\Delta t_{noise}$ too small: Normal sparse events are also misclassified as noise and discarded.
- $\Delta t_{noise}$ too large: Random noise events that happen to fall near signal events within the time window are not filtered out.

A typical setting is $\Delta t_{noise} = 1 \sim 10$ ms; the specific value depends on the expected motion speed. Fast-motion scenarios (dense events) can use a smaller value; slow-motion scenarios (sparse events) require a larger value.

### 3.3 Time Window Size

When converting the event stream to a frame representation, the time window $\Delta t_{frame}$ is analogous to the "exposure time" of a conventional camera:

- **Fixed time window:** Events are segmented at fixed time intervals (e.g., $\Delta t = 10$ ms); simple and straightforward, but event density varies widely at different motion speeds.
- **Fixed event count window:** Each segment is cut after accumulating a fixed number of events (e.g., $N = 1000$); guarantees uniform event density per frame, but segment durations are unequal.
- **Adaptive window:** Dynamically adjusted based on scene dynamics — lengthen the window to wait for events when the scene is static; shorten it to avoid pile-up when motion is intense.

In deep learning applications, fixed event count windows typically outperform fixed time windows because the information density of the network input is more uniform, making training more stable.

---

## §4 Artifacts

### 4.1 Hot Pixels

Hot pixels in event cameras manifest as: specific pixels continuously generating events at extremely high frequencies (up to the kHz range), completely uncorrelated with scene events from surrounding pixels. The cause is persistent charge accumulation inside the pixel due to leakage current, which continuously trips the threshold comparator circuit.

**Identification method:** Collect events for 1–5 seconds in a darkroom (no luminance change) or against a pure black background; compute per-pixel event frequency; pixels with abnormally high frequency (e.g., more than 5 times the mean) are hot pixels.

**Handling methods:**
1. Build a coordinate blacklist of hot pixels and filter them in real time.
2. Lower the operating temperature (elevated temperature worsens leakage).
3. Replace the sensor (for severe cases).

Both iniVation's DV software and Prophesee's Metavision SDK include built-in hot pixel filtering modules that can automatically detect and mask them.

### 4.2 Texture-Related False Events

When the camera itself vibrates or undergoes slight jitter, regions with high spatial-frequency texture (such as fine grids or fabric weaves) generate large numbers of events due to changes in the alignment relationship between the texture and the pixel grid — producing "texture noise" events unrelated to actual motion.

The hallmark of this type of artifact is that the event distribution is highly correlated with the scene texture, exhibiting periodic or grid-like patterns, and bursting suddenly when the camera jitters.

**Suppression methods:**
- Moderately increase the contrast threshold to filter out minor texture changes.
- Install optical image stabilization (OIS/EIS) on the camera to reduce the excitation source.
- In post-processing, identify and remove event clusters exhibiting texture-correlated spatial distribution patterns.

### 4.3 Leakage Events at Dynamic Range Boundaries

When the scene contains extremely strong light sources (e.g., direct sunlight, explosion flashes), the charge in the photodiode may overflow (blooming), corrupting neighboring pixels. Under extremely dark conditions, thermal noise can be equivalent to random photons, causing random triggering near the threshold.

These leakage events typically exhibit a diffuse pattern (strong-light blooming) or uniform random distribution (dark-field thermal noise) and can be identified through spatial morphology analysis:
- Event frequency in the strong-light center region is abnormally high, with predominantly positive polarity (continuous saturation state).
- Dark-field noise events are randomly distributed in space with no directional clustering.

---

## §5 Evaluation

### 5.1 Standard Datasets

The event camera field has established several widely recognized benchmark datasets covering different scenes and tasks:

**MVSEC (Multi Vehicle Stereo Event Camera Dataset)**

Published by Zhu et al. (2018); includes outdoor scenes such as driving and drone flight; provides LiDAR depth ground truth and IMU data. It was the most commonly used event camera autonomous driving benchmark in the early period. Resolution is relatively low (DAVIS 240C, 240×180).

**DSEC (Dynamic Stereo Event Camera Dataset)**

Published by Gehrig et al. (2021); designed for driving scenarios; uses high-resolution Prophesee sensors (640×480) paired with stereo RGB cameras and LiDAR; provides multiple types of ground truth including optical flow and depth. It is the current mainstream benchmark for event camera research in autonomous driving.

**EventAID**

A comprehensive dataset focused on image reconstruction and enhancement tasks; includes synthetic data (from the ESIM event simulator) and real-world captured data; paired with high-frame-rate reference video as ground truth for reconstruction quality.

**N-Caltech 101 / N-MNIST**

Traditional Caltech 101 and MNIST datasets converted to event data through camera motion; an introductory benchmark for event camera object recognition tasks.

### 5.2 Reconstructed Image Quality Assessment

Image reconstruction quality for event cameras is assessed using the same metrics as conventional image quality assessment:

- **PSNR (peak signal-to-noise ratio):** The reconstructed image PSNR is computed relative to a high-frame-rate reference image captured synchronously; a typical excellent level is approximately 30–35 dB.
- **SSIM (structural similarity):** Measures the overall similarity between the reconstructed image and the reference image in terms of structure, luminance, and contrast.
- **LPIPS (learned perceptual image patch similarity):** A perceptual quality metric based on deep features, more aligned with human visual perception.

When evaluating, note that images reconstructed by event cameras typically lack an absolute brightness reference; metrics must be computed after brightness alignment, otherwise results will be artificially low.

### 5.3 High-Speed Scene Tracking Accuracy

Evaluation of event cameras on high-speed target tracking tasks typically includes:

- **Feature tracking accuracy:** Using ground-truth trajectories from a high-speed camera (500 fps+) as reference, computing the endpoint error (EPE) of event-based tracking results.
- **Optical flow estimation error (EPE):** Compared against LiDAR projection ground truth on datasets such as DSEC.
- **Latency:** The time from when target motion occurs to when the system outputs a detection result; reflects the core advantage of event cameras. Excellent systems can achieve perception latency < 1 ms.

---

## §6 Code

The companion code for this chapter is in *See §6 Code section for runnable examples.*, containing the following experiments:

1. **Event stream visualization:** Read `.aedat4` or `.raw` format event files; generate event frame and time surface visualizations.
2. **Hot pixel detection and filtering:** Compute per-pixel event frequency; automatically identify hot pixels and filter them.
3. **Event frame vs. voxel grid:** Compare the two representation methods under different time window sizes.
4. **E2VID inference demo:** Load a pre-trained E2VID model; reconstruct intensity images from public dataset samples and compare with reference frames.

Dependencies: `dv-processing` (iniVation), `metavision_sdk` (Prophesee), `torch`, `h5py`, `numpy`, `matplotlib`.

---

## References

1. **Gallego G, Delbrück T, Orchard G, et al.** "Event-based Vision: A Survey." *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 44(1): 154–180, 2022. — The most comprehensive survey in the event camera field, covering principles, representation methods, algorithms, and applications; essential reading for newcomers.

2. **Rebecq H, Ranftl R, Koltun V, Scaramuzza D.** "High Speed and High Dynamic Range Video with an Event Camera." *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 43(6): 1964–1980, 2019. — The original E2VID paper; proposes using a recurrent neural network to reconstruct high-quality video frames from event streams.

3. **iniVation.** "DAVIS346 Datasheet and Technical Reference." iniVation AG, 2023. https://inivation.com/support/

4. **Prophesee / Sony.** "IMX636 Event-based Vision Sensor Product Brief." Sony Semiconductor Solutions Corporation, 2022. — Specification sheet for the world's first event sensor capable of volume consumer-grade production.

5. **Gehrig M, Aarents W, Gehrig D, Scaramuzza D.** "DSEC: A Stereo Event Camera Dataset for Driving Scenarios." *IEEE Robotics and Automation Letters*, 6(3): 4947–4954, 2021. — Paper describing the high-resolution driving-scenario event camera dataset.

6. **Zhu A Z, Thakur D, Özaslan T, et al.** "The Multivehicle Stereo Event Camera Dataset: An Event Camera Dataset for 3D Perception." *IEEE Robotics and Automation Letters*, 3(3): 2032–2039, 2018. — The MVSEC dataset paper; an early benchmark for event camera autonomous driving research.

---

*Authors: ISP Algorithm Handbook Project Team | Last updated: 2026-05*

---

## §8 Glossary

**Event Camera / Neuromorphic Camera**
An asynchronous vision sensor designed by analogy with the working principle of the biological retina. Each pixel independently monitors its log-luminance change; once the change exceeds the preset contrast threshold $C$, the pixel immediately outputs an event four-tuple $(x, y, t, p)$. Unlike the periodic global readout of conventional frame cameras, event cameras trigger asynchronously on demand — producing no data when the scene is unchanged, and responding at microsecond temporal resolution when high-speed motion occurs. Core advantages: dynamic range > 120 dB, temporal resolution < 1 μs, low power consumption, no motion blur.

**Event**
The basic information unit output by an event camera, represented as a four-tuple $e_k = (x_k, y_k, t_k, p_k)$: $(x_k, y_k)$ is the triggered pixel coordinate, $t_k$ is a microsecond-precision timestamp, and $p_k \in \{+1, -1\}$ is the polarity (positive indicates a brightness increase; negative indicates a brightness decrease). The entire sensor outputs a continuous, asynchronous event stream rather than frames.

**Contrast Threshold ($C$)**
The minimum log-luminance change required to trigger an event: $\Delta L = \ln(I_\text{new}/I_\text{old}) \geq p \cdot C$. Because triggering is based on log-luminance, the corresponding linear brightness change is approximately $e^C - 1$ ($C=0.1$ ≈ 10.5%, $C=0.5$ ≈ 65%). Typical values: 0.1–0.3. In real devices, ON/OFF thresholds may be asymmetric, and there is typically about 10%–30% variation across pixels. A lower threshold gives higher sensitivity but more noise; a higher threshold responds only to dramatic changes.

**Event Stream**
The raw output of an event camera: a continuous, asynchronous, irregularly timed sequence of events. Completely different from conventional frames (2D pixel arrays), an event stream is a sparse point set in space-time with no fixed frame rate; it approaches an empty stream when the scene is static and is event-dense during fast motion. Processing event streams requires dedicated representation methods and algorithms.

**Event Frame Accumulation**
A simple representation method that accumulates all events in a fixed time window into a 2D image by coordinate: $F(x,y) = \sum_{k:(x_k,y_k)=(x,y)} p_k$. Simple to implement and amenable to conventional computer vision algorithms, but loses temporal ordering information. The time window choice is a precision vs. density trade-off: too long produces motion blur; too short yields a sparse image.

**Event Voxel Grid**
An event representation method that discretizes the time dimension into $B$ time bins, constructing a 3D tensor $V \in \mathbb{R}^{B \times H \times W}$ with bilinear interpolation to ensure temporal continuity. Retains more temporal information than an event frame; the most commonly used input representation for current deep learning methods, at the cost of $B$ times the memory footprint (typically $B=5\sim10$).

**Surface of Active Events (SAE) / Time Surface**
A 2D map storing the timestamp of the most recent triggered event at each pixel, with separate maps for positive and negative polarity: $\mathcal{T}(x,y,p) = \max_{k'} t_{k'}$ (satisfying coordinate and polarity conditions). The SAE forms an "event age map" on which edges and motion trajectories are clearly visible; a commonly used representation for optical flow estimation and feature tracking.

**DAVIS (Dynamic and Active-pixel Vision Sensor)**
A hybrid sensor architecture from iniVation in which each pixel integrates two parallel readout circuits: an asynchronous event detection path (DVS path, triggered by log-luminance changes) and a synchronous active-pixel frame readout path (APS path). Both paths share a single photodiode, guaranteeing perfect spatial alignment and precise temporal synchronization between frames and events. The representative product DAVIS346 (346×260, > 120 dB dynamic range) is the most widely used hybrid sensor in academia.

**E2VID (Events-to-Video)**
A method proposed by Rebecq et al. (2019) that uses a recurrent convolutional neural network (ConvLSTM) to reconstruct high-quality grayscale video from event streams. Core idea: the event stream records the temporal derivative of log-intensity; the RCNN implicitly integrates it through its hidden state to recover intensity variation, outputting a grayscale frame for the corresponding time interval. Network input is a voxel grid; the architecture is a multi-scale recurrent U-Net. Reconstruction quality under high dynamic range and high-speed scenarios far exceeds that of conventional cameras.

**FireNet**
An efficient event image reconstruction network proposed by Scheerlinck et al. (WACV 2020). Like E2VID, it belongs to the events-to-image reconstruction family, but uses extensive depth-wise separable convolutions and related techniques to build an independent lightweight encoder-decoder architecture — not a direct simplified version of E2VID. Compared to E2VID, it reduces parameter count and computation by approximately one order of magnitude while maintaining high reconstruction quality, enabling real-time operation on embedded platforms such as Jetson.

**Hot Pixel**
An abnormal pixel that, due to manufacturing defects or internal leakage current, continuously generates events at extremely high frequencies (up to the kHz range) even in the absence of luminance change. Identification method: collect events in a dark-field condition; compute per-pixel event frequency; pixels with abnormally high frequency are hot pixels. Handling method: build a hot-pixel coordinate blacklist and filter in real time. Both iniVation's DV software and Prophesee Metavision SDK include built-in hot pixel filtering modules.

**Temporal Correlation Filter**
A denoising filter that exploits the fact that real luminance-change events have spatial-temporal continuity (neighboring pixels trigger at nearby times) while random noise events are spatially and temporally isolated. If an event has no other events in its spatial neighborhood within the time window $\Delta t_{noise}$, it is classified as noise and discarded. Typical $\Delta t_{noise} = 1 \sim 10$ ms; the value should be tuned based on the expected motion speed.

**DSEC Dataset (Dynamic Stereo Event Camera Dataset)**
A high-resolution driving-scenario event camera standard benchmark dataset published by Gehrig et al. (2021), using Prophesee 640×480 sensors paired with stereo RGB cameras and LiDAR, providing multiple ground truths including optical flow and depth. It is the current mainstream benchmark for autonomous driving event camera research, supporting multi-task evaluation including optical flow estimation and object detection.

**EDI (Event-based Double Integral)**
A method proposed by Pan et al. (2019) for recovering motion-blurred images using event data. The blurry image from a conventional camera is fundamentally the time integral of luminance over the exposure duration. Event cameras record the intensity change trajectory during the exposure at microsecond precision; by jointly optimizing the blurry image and the corresponding events, the sharp instantaneous image can be recovered — achieving event-assisted motion deblurring.
