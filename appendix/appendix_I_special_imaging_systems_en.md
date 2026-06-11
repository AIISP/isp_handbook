# Appendix I: Special Imaging Systems (Selected Reading)

> **Note**: This appendix covers 5 categories of special imaging systems that go beyond the mainstream smartphone ISP pipeline, encompassing depth sensing, light field cameras, hyperspectral imaging, lensless imaging, and neuromorphic cameras.
> It is intended for readers with research interests in these areas; smartphone ISP algorithm engineers may skip this appendix, or read only the comparison notes relevant to mobile devices.
> Originally Part 1 Ch12–Ch16; migrated here.

---

## I.1 Depth Sensing (深度感知)

> **Original directory**: `part1_imaging_fundamentals/ch12_depth_sensing/`

Depth sensing technology attaches distance information to each pixel, generating a depth map (深度图) or point cloud (点云). It is widely used in smartphones, AR/VR, autonomous driving, and industrial inspection.

### I.1.1 Comparison of the Three Major Technical Approaches

#### 1. Time-of-Flight (ToF, 飞行时间)

An active light source (infrared laser/LED) emits modulated light pulses; the sensor measures the round-trip travel time of photons to compute distance:

$$d = \frac{c \cdot \Delta t}{2}$$

where $c$ is the speed of light and $\Delta t$ is the time difference.

**iTOF (Indirect ToF, 间接 ToF)** uses phase difference rather than direct timing:

$$d = \frac{c}{4\pi f} \cdot \phi$$

where $f$ is the modulation frequency and $\phi$ is the phase difference (0–2π corresponding to the distance range). Mainstream implementations (Sony IMX556, Samsung dToF) use 4-phase sampling (0°/90°/180°/270°) to suppress ambient light interference.

**dToF (Direct ToF / Single-Photon ToF, 直接 ToF)** uses SPAD (Single Photon Avalanche Diode) to directly count photon timestamps, achieving higher precision (sub-millimeter), with representative products including the Apple LiDAR Scanner (iPhone 12 Pro and later) and the Huawei P30 Pro 3D ToF.

#### 2. Structured Light (结构光)

A projector casts a known pattern (speckle / fringe / Gray code) onto the scene; the camera captures the deformed pattern and computes depth via triangulation:

$$d = \frac{f \cdot B}{\Delta x}$$

where $f$ is the focal length, $B$ is the baseline distance between the projector and camera, and $\Delta x$ is the disparity.

**Speckle structured light**: Apple Face ID (TrueDepth front camera), Intel RealSense D415. Irregular speckle patterns provide good correspondence, but signal-to-noise ratio is low in outdoor sunlight.

**Active stereo structured light**: Augments passive stereo with infrared speckle assistance for matching; high precision at close-to-mid range (0.5–3 m).

#### 3. Binocular Stereo Vision (双目立体视觉)

Two calibrated cameras capture the scene simultaneously from different viewpoints; depth is computed from a disparity map (fully passive, no active light source):

$$d = \frac{f \cdot B}{disparity}$$

**Algorithm pipeline:** Epipolar rectification → cost computation (SAD/Census/MC-CNN) → disparity optimization (SGM/StereoSGBM) → depth conversion

**Representative implementations:** OpenCV StereoSGBM, Middlebury benchmark, RAFT-Stereo (deep learning approach).

#### Technology Comparison Table

| Feature | iTOF | dToF | Structured Light | Binocular Stereo |
|---------|------|------|-----------------|-----------------|
| Range | 0.1–5 m | 0.1–30 m | 0.1–3 m | 0.3–∞ |
| Depth accuracy (at 1 m) | 1–5 mm | 0.5–2 mm | 0.5–2 mm | 3–10 mm |
| Outdoor performance | Moderate (ambient light interference) | Good (SPAD filtering) | Poor (sunlight overwhelms) | Excellent (passive) |
| Power consumption | Medium (active IR) | High (SPAD array) | High (projector) | Low (no active light) |
| Typical smartphone use | Rear depth-assisted AF | Front Face ID / LiDAR | Front face recognition | Multi-camera DoF / 3D reconstruction |
| Representative chip/module | Sony IMX556, Samsung VD6281 | Apple LiDAR | PrimeSense → Apple | Qualcomm CV-ISP |

### I.1.2 Differences from Traditional ISP

| Dimension | Traditional RGB ISP | Depth Sensor ISP |
|-----------|--------------------|--------------------|
| Sensor output | Bayer RAW (irradiance) | Phase-difference map / timestamps (distance) |
| Processing goal | Color reproduction, denoising, sharpening | Depth computation, noise filtering, hole filling |
| Noise model | Photon shot noise + read noise | Multipath interference, motion blur (phase domain) |
| Key algorithms | Demosaic, AWB, CCM | Phase unwrapping (相位解包), confidence filtering, temporal fusion |
| Output format | YUV / RGB (8/10 bit) | 16-bit depth map (unit: mm) + confidence map |

### I.1.3 Key Algorithms: Phase Unwrapping and Multipath Suppression

**Phase Ambiguity (相位模糊):** Single-frequency iTOF modulation has a range limit ($d_{max} = c/(2f)$); distances beyond the range cause phase folding. Solution: dual-frequency modulation (双频调制), which extends the unambiguous range using the greatest common divisor:

$$d_{unamb} = \frac{c}{2 \cdot GCD(f_1, f_2)}$$

**Multipath Interference (多路径干扰):** Light reflecting off corners or specular surfaces creates indirect paths, causing a ToF pixel to receive aliased signals with multiple arrival times, resulting in systematic depth bias (typically biased toward shorter distances). Suppression methods: amplitude-weighted filtering, and learning-based multipath separation networks (e.g., Su et al., "Frequency-domain ToF Multipath Interference", ICCV 2021).

### I.1.4 Representative Products and Papers

- **Apple LiDAR Scanner**: dToF + SPAD, used for AR scene reconstruction (ARKit) and night-mode photography autofocus
- **Microsoft Azure Kinect**: iTOF (1 MP @ 30 fps) + RGB + microphone array, used for Azure Spatial Anchors
- **Intel RealSense D435i**: Active infrared stereo vision, commonly used for robotic SLAM
- Paper: Gupta et al., "Phasor Imaging: A Generalization of Correlation-Based Time-of-Flight Imaging", ACM ToG 2015

---

## I.2 Light Field Cameras / Plenoptic Cameras (光场相机)

> **Original directory**: `part1_imaging_fundamentals/ch13_plenoptic/`

A light field camera simultaneously records both the **position** and **direction** of light rays in a single exposure, enabling post-capture refocusing and viewpoint change.

### I.2.1 Basic Principles

#### Light Field Theory

The complete light field is represented by the **Lumigraph / 4D light field**:

$$L(x, y, u, v)$$

where $(x, y)$ are main-lens plane coordinates (spatial) and $(u, v)$ are micro-lens plane coordinates (angular). Each micro-lens captures multiple angular samples of the same scene point.

#### Micro-Lens Array Architecture

- **Lytro Illum (MLA type, first-generation light field camera)**: Positions an MLA (Micro-Lens Array, 微透镜阵列) in front of the sensor; each micro-lens covers approximately $k \times k$ pixels (typically $k = 11$–15), providing $k^2$ angular samples, but reducing spatial resolution to $N/k$
- **Focused Plenoptic (焦距堆叠型)**: Places the MLA at a defocused position, enabling flexible trade-off between spatial resolution and angular resolution

**Spatial-angular resolution trade-off formula:**

$$\text{Angular resolution} \times \text{Spatial resolution} = \text{Total pixel count} / k^2$$

### I.2.2 Digital Refocusing Algorithm (重聚焦算法)

Synthesizing an image at an arbitrary focal plane from the 4D light field is called **Shift-and-Add Integration (积分投影)**:

$$I_\alpha(x, y) = \frac{1}{|UV|} \sum_{u,v} L(x - \alpha u, y - \alpha v, u, v)$$

where $\alpha$ is the virtual focus parameter:
- $\alpha = 0$: all rays summed directly (all-in-focus image)
- $\alpha > 0$: foreground in focus
- $\alpha < 0$: background in focus

**Computational complexity:** Naive implementation is $O(N^2 \cdot k^2)$; FFT acceleration reduces this to $O(N^2 \log N)$ (frequency-domain shift-multiply).

### I.2.3 Relationship to Smartphone Multi-Camera Systems

Smartphone multi-camera systems (dual/triple cameras) are essentially **sparse light field sampling**, while micro-lens arrays provide **dense light field sampling**:

| Feature | Smartphone Multi-Camera | Light Field Camera (MLA) |
|---------|------------------------|--------------------------|
| Number of viewpoints | 2–4 (wide/tele/ultrawide) | $k^2$ (typically 100–400) |
| Baseline | Large (5–20 mm) | Extremely small (μm-scale MLA pitch) |
| Depth estimation accuracy | High (large baseline) | Low (extremely small baseline) |
| Refocus range | Limited (background blur only) | Full scene, arbitrary plane |
| Spatial resolution | Full resolution per camera | Reduced to $1/k$ |
| Computational cost | Stereo matching | Light field decoding + projection integration |

**Smartphone dual-camera bokeh** uses large-baseline stereo depth estimation and supports only background blurring (foreground/background separation), not true light field refocusing. The Lytro Illum can refocus on any arbitrary plane but delivers only approximately 4 MP (equivalent) spatial resolution.

### I.2.4 Differences from Traditional ISP

Traditional ISP processes a single Bayer RAW frame; the light field camera ISP must additionally perform:

1. **MLA calibration**: Determine the center position of each micro-lens (calibration accuracy must be < 0.1 pixel)
2. **Raw light field decoding**: Extract the $(x, y, u, v)$ 4D array from sensor RAW
3. **Disparity estimation**: Estimate per-pixel disparity from multi-view images
4. **Refocus / all-in-focus synthesis**: Shift-and-add or frequency-domain synthesis

### I.2.5 Representative Products and Papers

- **Lytro Illum (2014)**: The most well-known consumer light field camera, now discontinued; the `.lfp` light field file format has an open-source parser
- **Raytrix R5/R29**: Industrial-grade light field cameras used for industrial inspection and research
- **Adobe Light Field Plugin**: Standard post-processing tool for Lytro
- Paper: Ng et al., "Light Field Photography with a Hand-held Plenoptic Camera", Stanford Technical Report CSTR 2005-02
- Paper: Levoy et al., "Light Field Rendering", SIGGRAPH 1996

---

## I.3 Hyperspectral Imaging (高光谱成像)

> **Original directory**: `part1_imaging_fundamentals/ch14_hyperspectral/`

Hyperspectral sensors simultaneously capture images across tens to hundreds of contiguous spectral bands, outputting the complete reflectance spectrum per pixel, enabling the perception of material information beyond visible color.

### I.3.1 Basic Principles

#### Spectral Dimension Definitions

- **Multispectral (多光谱)**: 4–20 discrete bands (e.g., R/G/B/NIR/SWIR), band width 20–100 nm
- **Hyperspectral (高光谱)**: 100–400+ contiguous bands, band width 1–10 nm, covering visible light (400–700 nm) to near-infrared (700–2500 nm)
- **Ultraspectral (超光谱)**: 1000+ bands, primarily used in meteorological satellites and laboratory spectrometers

#### Bayer vs. Hyperspectral CFA

| Feature | Traditional RGB Bayer | Hyperspectral Sensor |
|---------|----------------------|----------------------|
| Number of bands | 3 (R/G/B) | 100–400 |
| Band width | ~100 nm (broadband) | 1–10 nm (narrowband) |
| Spatial resolution | High (full pixel) | Medium–low (multiplexed) |
| Color representation | CIE XYZ → sRGB | Reflectance spectrum λ→R(λ) |
| Data per pixel | 1–2 bytes | 100–800 bytes |

### I.3.2 Imaging Modes

#### Pushbroom / Line Scan Mode (推扫模式)

Advances row by row along the flight/scan direction, collecting the full spectrum of one row of pixels at a time:

```
Sensor: spatial × spectral (2D sensor)
Output: integrated over time into spatial × spatial × spectral (3D data cube)
```

**Advantages:** High SNR (long integration time), good spectral resolution
**Disadvantages:** Requires relative motion, unsuitable for static scenes, spatial-temporal registration errors
**Applications:** Remote sensing satellites (Hyperion, AVIRIS), industrial conveyor belt inspection

#### Snapshot Mode / CTIS (快照模式, Computed Tomography Imaging Spectrometer)

Captures the 3D spectral data cube (spatial × spatial × spectral) in a single exposure:

- **CASSI (Coded Aperture Snapshot Spectral Imager, 编码孔径快照光谱成像仪)**: Coded aperture + dispersive prism, reconstructed via compressed sensing
- **Image filter array (IMEC mosaic filter)**: Narrow-band multi-band filter arrays fabricated on the sensor (Bayer-like), analogous to a multispectral Bayer pattern

**Advantages:** No motion required, can capture dynamic scenes
**Disadvantages:** Spatial-spectral resolution trade-off, complex reconstruction algorithms

#### Key Parameters

| Parameter | Definition | Typical Value |
|-----------|-----------|---------------|
| Number of bands | Number of spectral samples | 100–400 |
| Spectral resolution (FWHM) | Full width at half maximum of a single band | 1–10 nm |
| Spatial resolution | Spatial pixel size (GSD) | 1–30 m (satellite); 0.01–1 mm (industrial) |
| Noise Equivalent Reflectance (NEdR) | Minimum detectable reflectance difference | 0.1–1% (high-quality systems) |
| Data cube size | spatial × spatial × bands | 512×512×200 ≈ 50 MB |

### I.3.3 Differences from Traditional ISP

Traditional RGB ISP targets color reproduction; hyperspectral ISP targets **spectral quantitative accuracy**:

| Processing Step | RGB ISP | Hyperspectral ISP |
|----------------|---------|-------------------|
| Dark field / gain correction | BLC + PRNU | Per-band independent dark field and flat-field correction |
| Denoising | 2D spatial denoising | 3D joint spatial-spectral denoising (striping noise) |
| Geometric correction | Lens distortion | Dispersion correction (different bands have different spatial offsets) |
| Radiometric calibration | White balance (estimated) | Absolute radiometric calibration (DN → reflectance, requires calibration panel) |
| Output | 8/10-bit YUV/RGB | 16-bit floating-point reflectance cube |

**Striping noise (条带噪声)** is the typical artifact of pushbroom hyperspectral imaging: uneven response across detector columns causes vertical stripes, requiring per-column gain-offset correction (Moment Matching).

### I.3.4 Typical Application Scenarios

| Application Domain | Detection Target | Key Spectral Bands |
|-------------------|-----------------|-------------------|
| Food safety inspection | Mold, pesticide residues, foreign matter | Near-infrared 900–1700 nm |
| Medical / dermatology | Melanoma, oxygenated hemoglobin | Visible 500–900 nm |
| Agricultural remote sensing | Vegetation index (NDVI), pests and diseases | Red edge 680–740 nm |
| Mineral exploration | Mineral composition identification | SWIR 1400–2500 nm |
| Semiconductor inspection | Silicon wafer defects | Near-infrared 1000–1600 nm |
| Art authentication | Pigment composition, restoration traces | Full spectrum 400–2500 nm |

### I.3.5 Representative Products and Papers

- **Specim FX10/FX17**: Industrial pushbroom hyperspectral cameras (400–1000 nm / 900–1700 nm)
- **IMEC mosaic hyperspectral sensor**: Snapshot type, integratable into smartphone-form-factor devices
- **Headwall Photonics Nano-Hyperspec**: UAV-mounted hyperspectral system
- Paper: Bioucas-Dias et al., "Hyperspectral Unmixing Overview", IEEE JSTARS 2012
- Paper: Mäkinen et al., "Generalized Anscombe Transformation for Poisson-Gaussian Noise Model", Signal Processing 2013 (theoretical foundation for hyperspectral denoising)

---

## I.4 Lensless Imaging (无透镜成像)

> **Original directory**: `part1_imaging_fundamentals/ch15_lensless/`

Lensless cameras replace the conventional lens with coded diffractive optical elements (diffuser, phase mask, coded aperture), eliminating bulky optical systems and reconstructing images computationally. Their extremely thin form factor (< 1 mm) makes them suitable for wearable devices, biomedical endoscopes, and covert cameras.

### I.4.1 Basic Principles

#### Forward Imaging Model

The imaging process of a lensless system is a linear convolution:

$$\mathbf{y} = \mathbf{H} \mathbf{x} + \mathbf{n}$$

where:
- $\mathbf{y}$: sensor measurements (RAW image)
- $\mathbf{H}$: point spread function (PSF, 点扩展函数) matrix, determined by the diffractive optical element
- $\mathbf{x}$: scene image to be reconstructed
- $\mathbf{n}$: sensor noise

The shape of the PSF is determined by the diffraction mask design. A conventional camera PSF is a sharp Airy disk; a lensless camera PSF is an artificially designed **spatially multiplexed** pattern (speckle / spiral / Gray code).

#### Three Lensless Architectures

**1. Coded Aperture (编码孔径)**
A transparent/opaque aperture pattern is placed at the lens position; aperture coding enables spectral/depth multiplexing. Originally used in X-ray astronomical telescopes (HETE-2), now extended to visible light.

**2. Speckle Diffuser — DiffuserCam (散斑扩散器)**
Antipa et al. (2018) proposed attaching an inexpensive frosted-glass speckle diffuser directly to the sensor, forming a shift-invariant PSF (BCCB matrix structure), with FFT-accelerated reconstruction:

$$\hat{\mathbf{x}} = \arg\min_x \frac{1}{2}\|\mathbf{y} - \mathbf{H}\mathbf{x}\|^2 + \lambda \text{TV}(\mathbf{x})$$

Solved with ADMM; each step requires only FFT operations, complexity $O(N \log N)$.

**3. Phase Mask (相位掩模)**
Sub-wavelength phase structures (e.g., Fresnel lens variants) fabricated by lithography control the phase rather than the amplitude of light. FlatCam (Chan et al., 2016) uses a separable phase mask, making the PSF separable in horizontal and vertical directions and simplifying reconstruction.

### I.4.2 Reconstruction Algorithm Comparison

| Algorithm | Complexity (per step) | Convergence | Noise robustness | Representative implementation |
|-----------|----------------------|-------------|-----------------|-------------------------------|
| Direct inverse filtering | $O(N \log N)$ | 1 step | Poor (ill-posed) | scipy.signal.deconvolve |
| Gradient descent + TV | $O(N \log N)$/step | Slow (100+ steps) | Moderate | TF/PyTorch custom implementation |
| ADMM | $O(N \log N)$/step | Fast (within 50 steps) | Good | DiffuserCam open-source code |
| Unrolled network | Fixed forward pass | 1 inference | Excellent | LearnedPrimalDual |

### I.4.3 PSF Engineering Design Principles

A high-quality lensless PSF should have:
1. **Shift-invariance**: Simplifies reconstruction to a convolution inverse problem
2. **Uniform spectral coverage**: PSF power spectrum should be as flat as possible (avoiding spectral holes that cause under-determination)
3. **High autocorrelation peak-to-sidelobe ratio (PSL ratio)**: Reduces cross-correlation reconstruction artifacts
4. **Alignment tolerance**: Minor misalignment between mask and sensor should not cause drastic PSF changes

### I.4.4 Differences from Traditional ISP

| Dimension | Traditional Camera | Lensless Camera |
|-----------|-------------------|-----------------|
| Optical system | Multi-element glass lens group (5–10 mm thick) | Diffractive mask (< 1 mm) |
| Sensor RAW | Approximately sharp image (small PSF) | Heavily blurred / coded measurement |
| Core ISP task | Color reproduction, denoising | Computational reconstruction (deconvolution) |
| Real-time capability | Real-time (ASIC pipeline) | Limited (GPU/NPU reconstruction, ~hundreds of ms) |
| Field of view | Constrained by lens (typically 30–120°) | Up to 180° (depending on mask design) |
| Image quality | Professional photography grade | Currently ~0.1–1 MP equivalent |

### I.4.5 Use Cases and Representative Products

**Applicable scenarios:**
- Ultra-thin wearable cameras (integrated within smart glasses frames)
- Medical endoscopes (diameter < 1 mm)
- Insect compound-eye bionic sensors
- Research: holographic reconstruction, X-ray / gamma-ray imaging

**Representative products and open-source projects:**
- **DiffuserCam** (UC Berkeley): [github.com/Waller-Lab/DiffuserCam](https://github.com/Waller-Lab/DiffuserCam)
- **FlatCam** (Rice University): Fresnel phase-mask lensless camera
- **Rambus pixel-array lensless sensor**: Commercial exploration stage

**Representative papers:**
- Antipa et al., "DiffuserCam: Lensless Single-exposure 3D Imaging", Optica 2018
- Chan et al., "FlatCam: Thin, Lensless Cameras using Coded Aperture and Computation", IEEE TPAMI 2017

---

## I.5 Neuromorphic / Event Cameras (神经形态相机 / 事件相机)

> **Original directory**: `part1_imaging_fundamentals/ch16_neuromorphic/`

An event camera (Dynamic Vision Sensor, DVS, 动态视觉传感器) is a bio-inspired sensor where each pixel independently monitors local luminance changes and asynchronously outputs an event only when luminance exceeds a threshold, rather than outputting full frames at a fixed frame rate.

### I.5.1 Basic Principles

#### Event Generation Model

Each pixel $(x, y)$ outputs an event $e = (x, y, t, p)$ at time $t$ if and only if:

$$\log I(x, y, t) - \log I(x, y, t_{prev}) \geq C \cdot p$$

where:
- $I(x, y, t)$: log-luminance of the pixel
- $C$: contrast threshold (typically 0.1–0.5, adjustable)
- $p \in \{+1, -1\}$: polarity (luminance increase: +1, decrease: −1)
- $t_{prev}$: timestamp of the last event fired by this pixel

The event stream is an **asynchronous sparse point cloud** with microsecond-level temporal resolution (independent of frame rate).

#### Traditional Camera vs. Event Camera

| Feature | Traditional Frame Camera | Event Camera |
|---------|------------------------|--------------|
| Output format | Frames (synchronous, global/rolling shutter) | Event stream (asynchronous, sparse) |
| Temporal resolution | Inverse of frame rate (1/30–1/1000 s) | Microsecond-level (1–100 μs) |
| Dynamic range | 60–70 dB (typical) | 120–140 dB |
| Motion blur | Prominent at high speed | None (asynchronous output) |
| Data volume (static scene) | Full frame (large) | Minimal (almost no events) |
| Data volume (high-speed motion) | Full frame (fixed) | Concentrated at motion regions (high) |
| Absolute luminance information | Yes | No (changes only) |
| Power consumption | High (fixed frame rate driven) | Low (event-driven, nearly zero power when idle) |

### I.5.2 Event Data Processing Methods

#### Event Frame Representation (事件帧表示)

The simplest preprocessing: accumulate events within a time window $[t_0, t_0 + \Delta t]$ by polarity into a frame:

$$F(x, y) = \sum_{e \in \Delta t} p_e \cdot \delta(x - x_e, y - y_e)$$

Drawback: microsecond-level temporal information is lost, but this format enables use of conventional CNN processing.

#### Time Surface (时间面)

Records the timestamp of the most recent event at each pixel (exponentially decaying weight):

$$S(x, y) = \exp\left(-\frac{t - t_{last}(x,y)}{\tau}\right)$$

Preserves local temporal information; suitable for corner detection and optical flow estimation.

#### Voxel Grid (体素格)

Quantizes the event stream into a spatiotemporal voxel grid:

$$V(x, y, b) = \sum_{e: t_n(e)=b} p_e \cdot \delta(x-x_e, y-y_e)$$

where $b$ is the time-bin index (analogous to video frames); this is the most commonly used input representation for deep learning methods.

#### Spiking Neural Networks (SNN, 脉冲神经网络)

A natural framework for directly processing asynchronous event streams; each synaptic connection activates only upon event arrival, achieving extremely high energy efficiency. Representative works: EST (Event Spike Tensor), Spiking ResNet.

### I.5.3 High-Speed Motion Capture Applications

The microsecond temporal resolution of event cameras makes them ideal for high-speed motion capture:

| Application | Frame Camera Limitation | Event Camera Solution |
|------------|------------------------|----------------------|
| High-speed table tennis trajectory (> 300 km/h) | Motion blur | Direct trajectory reconstruction from event stream |
| High-speed UAV obstacle avoidance | 33 ms latency (30 fps) | < 1 ms response |
| Corneal tracking (eye tracker) | Requires dedicated high-speed camera (1000 fps) | Event camera @ 1/10 power consumption |
| High-speed industrial inspection (> 1000 fps) | Frame storage bandwidth bottleneck | Sparse event stream with low bandwidth |

### I.5.4 Differences from Traditional ISP

The data processing pipeline of an event camera is fundamentally different from traditional ISP:

| Step | Traditional ISP | Event Camera Processing |
|------|----------------|------------------------|
| Sensor readout | Global/rolling shutter synchronous frame readout | Asynchronous event bus (AER protocol) |
| Denoising | Spatial filtering (NLM/BM3D) | Event denoising: neighborhood temporal correlation filtering (isolated event noise) |
| Spatial processing | Bayer demosaic | Event frame / voxel grid generation |
| Motion processing | Optical flow (post-processing) | Optical flow embedded in real time within event stream (no inter-frame latency) |
| Output | Image frames | Event stream / reconstructed image / optical flow field |

**Lack of absolute luminance information** is the fundamental limitation of event cameras: they cannot be used for metering, white balance, color reproduction, or other traditional ISP tasks. Hybrid cameras (DAVIS, which simultaneously outputs frames and events) serve as a transitional solution.

### I.5.5 Key Algorithms: Optical Flow Estimation and Image Reconstruction

#### Event Optical Flow

EV-FlowNet (Zhu et al., 2018) feeds event frames into a U-Net-type network to predict optical flow, and was the first to demonstrate on the MVSEC dataset that event camera optical flow is comparable to traditional PWC-Net.

#### Video Reconstruction (Events → Frames)

E2VID (Rebecq et al., 2019) uses a recurrent neural network (ConvLSTM) to reconstruct high-dynamic-range video frames from the event stream, significantly outperforming conventional frame cameras in scenes with > 100 dB dynamic range.

### I.5.6 Representative Products and Papers

**Representative sensors:**
- **DAVIS346** (iniVation): Frame + event dual mode, 346×260 resolution, widely used in research
- **Prophesee Metavision EVK4**: 1 MP event sensor (1280×720), highest-resolution commercial product
- **Samsung DVS (Dynamic Vision Sensor)**: Integrated as an auxiliary camera in select Samsung flagship smartphones (motion-detection-assisted autofocus)
- **Sony IMX636**: Sony's first commercial QVGA event sensor, for industrial robotics applications

**Representative papers:**
- Lichtsteiner et al., "A 128×128 120 dB 15 μs Latency Asynchronous Temporal Contrast Vision Sensor", IEEE JSSC 2008 (original DVS paper)
- Gallego et al., "Event-based Vision: A Survey", IEEE TPAMI 2022 (survey)
- Rebecq et al., "Events-to-Video: Bringing Modern Computer Vision to Event Cameras", CVPR 2019
- Zhu et al., "EV-FlowNet: Self-Supervised Optical Flow Estimation for Event-based Cameras", RSS 2018

---

## I.6 Comprehensive Comparison of Special Imaging Systems

| Feature | Depth Sensing | Light Field Camera | Hyperspectral Imaging | Lensless Imaging | Event Camera |
|---------|--------------|-------------------|----------------------|-----------------|--------------|
| Captured information dimensions | Spatial (2D) + Depth (1D) | Spatial (2D) + Angular (2D) | Spatial (2D) + Spectral (1D) | Spatial (2D) (coded) | Spatial (2D) + Time (continuous) |
| Primary applications | AR / face recognition / autonomous driving | Post-capture refocusing / depth | Food / medical / remote sensing | Wearables / endoscopes | High-speed motion / robotics |
| Relevance to smartphone ISP | High (assisted AF / bokeh) | Low (specialized equipment) | Low (limited NIR applications) | Very low (research stage) | Low (limited Samsung applications) |
| Computational reconstruction demand | Medium (depth post-processing) | High (4D light field decoding) | High (spectral unmixing) | Very high (deconvolution reconstruction) | Medium (event frame conversion) |
| Commercial maturity | High (ubiquitous in smartphones) | Low (Lytro discontinued) | Medium (industrial applications) | Low (research stage) | Medium (industrial early adoption) |

---

*This appendix was migrated from Part 1 Ch12–Ch16 and substantially expanded. The `_ch.md` files in the original ch12–ch16 directories are the detailed chapter versions; this appendix is the condensed engineering reference edition.*
