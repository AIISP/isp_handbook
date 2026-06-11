# Part 1, Chapter 13: Plenoptic / Light Field Cameras

> **Pipeline position:** Specialized imaging system; raw data structure is fundamentally different from conventional RAW
> **Prerequisites:** Chapter 2 (Optics Basics), Chapter 3 (Sensor Physics), Chapter 9 (Camera Calibration)
> **Reader path:** Systems researchers, algorithm engineers, ISP developers interested in computational photography

---

## §1 Theory

### 1.1 Definition of the Plenoptic Function

The concept of the light field was first proposed by Adelson and Bergen in 1991. They unified all observable light information in a visual scene into a seven-dimensional plenoptic function:

$$P(x, y, z, \theta, \phi, \lambda, t)$$

where $(x, y, z)$ is the three-dimensional spatial coordinate of the observer, $(\theta, \phi)$ is the direction angle of the ray, $\lambda$ is the wavelength, and $t$ is time. This function theoretically provides a complete description of all light information that a human observer can perceive at any position, in any direction, and at any moment.

In practice, however, a seven-dimensional function is extremely difficult to capture and process. Levoy and Hanrahan (1996) and Gortler et al. independently proposed a simplified four-dimensional light field representation in the same year — the two-plane parameterization:

$$L(u, v, s, t)$$

The key insight is that in free space (without occlusion), the radiance along a ray remains constant as it propagates. It is therefore sufficient to uniquely identify a ray by its coordinates on two planes: $(u, v)$ on the camera plane and $(s, t)$ on the focal plane (or reference plane). This parameterization compresses the infinite-dimensional light field into a four-dimensional function that can be practically captured, forming the theoretical foundation of modern light field cameras.

Intuitively: for a given point in space, observations from different angles $(u, v)$ produce slightly different projection positions on the sensor (parallax). It is precisely by recording this angular information that a light field camera can achieve post-capture capabilities such as refocusing and depth estimation.

### 1.2 Hardware Architecture of Light Field Cameras

#### 1.2.1 Lytro Type (Single-Focus Configuration)

The most representative commercial light field camera is the Lytro (launched in 2012) and its professional version, the Illum (2014). The optical structure is:

**Main Lens → Microlens Array (MLA) → Sensor**

- **Main Lens:** Identical to a conventional camera; forms a scene image near the MLA plane (usually slightly defocused).
- **Microlens Array (MLA):** Composed of hundreds of thousands of miniature lenses arranged in a regular grid, each with a diameter of approximately 10–50 μm and a very short focal length (approximately equal to the distance from the microlens to the sensor). The MLA is placed near the rear focal plane of the main lens.
- **Sensor:** Each microlens corresponds to a pixel patch beneath it, typically covering 9×9 to 15×15 pixels.

**Operating principle:** The main lens converges light from different scene depths and forms a blurred image near the MLA plane. Each microlens acts as an "angular separator" — it projects rays passing through different aperture positions (different angles) of the main lens onto different pixels of the sensor beneath it. Thus, the pixel patch beneath each microlens records the light intensities arriving from different angles at that spatial location, forming a local angular view.

#### 1.2.2 Raytrix Type (Multi-Focus Configuration)

Raytrix (Germany) light field cameras use an interleaved arrangement of microlenses with different focal lengths (typically three focal lengths in a repeating cycle). This allows the system to simultaneously capture information at different virtual focus depths in a single exposure, further extending the range over which refocusing is possible, making it suitable for industrial inspection scenarios.

#### 1.2.3 Challenges for Handheld Camera Implementations

The introduction of the MLA imposes a fundamental resolution penalty: if the sensor has $N_{MLA}^2$ microlenses and each has $m \times m$ pixels beneath it, the total pixel count is $N_{MLA}^2 \times m^2$. However, the final rendered spatial image contains only $N_{MLA}^2$ pixels — just $1/m^2$ of the total sensor resolution. This intrinsic resolution–depth-of-field trade-off (Resolution-DOF Trade-off) is the greatest challenge to the commercialization of light field cameras. The first-generation Lytro product ultimately delivered only approximately 1 MP output resolution, far below that of contemporary smartphones.

### 1.3 Computational Imaging Capabilities of the Light Field

Light field data is valuable precisely because it retains the angular dimension that conventional cameras discard, enabling a range of powerful post-processing capabilities.

#### 1.3.1 Post-Capture Refocusing

The simplest refocusing algorithm is **Shift-and-Add**. Given the light field $L(u, v, s, t)$, the image refocused to depth $\alpha$ (normalized with respect to the focal plane) is:

$$E_\alpha(s, t) = \iint L\!\left(u, v,\; s + \alpha(u - u_0),\; t + \alpha(v - v_0)\right) \mathrm{d}u\, \mathrm{d}v$$

Intuitively, applying a depth-proportional shift to sub-aperture views at different angles before summing causes objects at the target depth to align precisely and become sharp, while objects at other depths remain blurred due to misalignment. Setting $\alpha = 0$ produces an all-in-focus image (direct summation without shifting).

Ng (2005) proposed a frequency-domain refocusing algorithm based on the Fourier Slice Theorem in his doctoral dissertation: the Fourier transform of a slanted slice of the light field corresponds to refocused images at different depths, offering substantially higher computational efficiency.

#### 1.3.2 All-in-Focus Images (Extended Depth of Field)

When $\alpha = 0$, all angular views are summed directly, simulating an extremely large aperture (synthetic aperture) that maximizes energy concentration at the principal focal plane. However, because all depths are summed together, a genuinely all-in-focus result is not directly obtained. Practical all-in-focus algorithms typically first estimate a depth map, then select the sharp view corresponding to the appropriate depth for each pixel before compositing.

#### 1.3.3 Depth Estimation

Sub-aperture images captured from the same scene point at different angles exhibit parallax. By analyzing epipolar plane images (EPIs) — two-dimensional slices $L(u, s)$ extracted from the light field with $v$ and $t$ fixed — the depth of a scene point is proportional to the reciprocal of the slope of the corresponding line in the EPI:

$$\text{depth} \propto \frac{1}{\text{slope of EPI line}}$$

This is fundamentally identical to the triangulation principle in binocular stereo vision, except that a light field camera simultaneously provides multi-baseline parallax information, making depth estimation more robust.

#### 1.3.4 Synthetic Aperture and View Synthesis

By selecting and summing a specific subset of angular views from the light field, it is possible to simulate any virtual camera position (view synthesis), or to synthesize a large effective aperture that "sees through" foreground occluders such as leaves or fences — a capability with practical significance in surveillance and aerial photography. This concept is closely related to the view synthesis objective of NeRF (Neural Radiance Fields).

### 1.4 Light Field Data Representations and Storage

Light field data can be organized in several equivalent ways; the choice depends on the subsequent algorithm:

| Representation | Description | Applicable Algorithms |
|---|---|---|
| **Sub-Aperture Image Array** | The light field divided into $n_u \times n_v$ spatial images, each corresponding to one angle $(u_i, v_j)$ | Disparity estimation, view synthesis |
| **Raw MLA Image** | Raw sensor data; each microlens subtends one angular patch | Calibration, decoding |
| **Epipolar Plane Image (EPI)** | 2D slice $L(u, s)$ with $v, t$ fixed | Depth estimation |
| **Focal Stack** | A sequence of images at different refocus depths | All-in-focus compositing |

In terms of storage, a typical light field image (Lytro raw format) is approximately 16–40 MB, far larger than a conventional RAW file from a sensor of equivalent size. High-resolution light field video (e.g., the Lytro Immerge VR camera with a 16-camera array) reaches data volumes on the order of terabytes, representing a significant bottleneck in the practical deployment of light field systems.

### 1.5 Deep Learning Advances in Computational Refocusing

Traditional shift-and-add algorithms, owing to their linear nature, produce refocusing quality that is limited by the light field's angular resolution (typically only 9×9 to 15×15 angles). Recent deep learning methods have significantly improved light field reconstruction quality:

- **LFSSR (Light Field Super-Resolution):** Uses consistency constraints between sub-aperture views for joint angular and spatial super-resolution. Representative works include LFSSR (Yeung et al., 2018) and LF-InterNet (Wang et al., 2020).
- **Neural Light Field Rendering:** NeRF (Mildenhall et al., 2020) can be regarded as a neural network parameterization of a continuous light field, implicitly reconstructing the complete light field from sparse views. This is highly complementary to the post-capture refocusing approach of light field cameras.
- **End-to-End Light Field Reconstruction:** End-to-end networks that directly decode raw MLA images into refocused images, avoiding the accumulation of calibration errors inherent in traditional pipelines.

### 1.6 Smartphone Light Field Approaches: Dual-Camera and Multi-Camera Parallax

Due to the resolution penalty of the MLA approach, smartphones have not adopted the traditional light field camera architecture. Instead, they approximate the core functions of a light field using dual-camera or multi-camera modules:

**Equivalent light field perspective from a dual-camera module:** The baseline distance between two main cameras (approximately 10–30 mm) is far larger than the spacing between adjacent microlenses in an MLA (approximately 50–150 μm). This results in larger parallax and higher depth estimation accuracy, at the cost of sparse angular sampling (only 2 viewpoints).

**Apple Portrait Mode:** Uses a dual-camera system (wide + telephoto) or a ToF/LiDAR depth sensor to obtain a depth map, then applies computational blur to background regions (typically depth-based Gaussian/bokeh convolution) to simulate the shallow depth-of-field effect of a large aperture. This is essentially a simplified light field rendering pipeline: depth estimation → layered segmentation → depth-based blur.

**Light field reconstruction from multi-camera arrays:** Although Huawei's Pura/Mate series multi-camera systems (ultra-wide + wide + telephoto + macro) are not strictly light field cameras, their algorithms for super-resolution and night scene fusion conceptually draw on the multi-view fusion ideas of the light field.

**Lytro Immerge (VR Light Field Camera):** The professional VR camera introduced by Lytro in 2015, which used a multi-layer spherical camera array to densely sample the light field on a spherical surface, providing six-degrees-of-freedom (6DoF) view synthesis capability for VR content. This represented an important direction for light field technology in the professional market. Although Lytro ultimately announced the cessation of operations in 2018, the majority of its core engineering team was subsequently hired by Google, which also acquired its principal patent assets (approximately 59 light-field-related patents) — this was an asset acquisition rather than a corporate merger.

---

## §2 Calibration

### 2.1 Geometric Calibration of the Microlens Array

Geometric calibration of the MLA is the central challenge in light field camera calibration. The following parameters must be determined:

1. **MLA Center Grid:** Ideally, the MLA is arranged in a regular hexagonal or square grid. In practice, manufacturing tolerances and installation misalignment cause individual microlens center positions to deviate from their theoretical locations. Calibration typically involves illuminating the sensor with uniform white light and detecting the brightness peak position of each microlens to determine the center grid.
2. **MLA Rotation Angle:** The rotation of the MLA relative to the sensor pixel grid during installation, typically within ±2°, but with a significant effect on decoding accuracy.
3. **Microlens Pitch and Diameter:** Used to establish the mapping between microlens indices and sensor pixel coordinates.

Calibration algorithms typically proceed in two steps: first, a white image (flat-field image) is used to determine the MLA center grid; then, a checkerboard calibration target is used to determine the intrinsic parameters and distortion of the main lens. Dansereau et al. (2013) proposed a complete light field camera toolbox (LFToolbox) that has been widely adopted by the research community.

### 2.2 Light Field Camera Intrinsics (Main Lens Focal Length + MLA Parameters)

The intrinsic model of a light field camera is more complex than that of a conventional camera, requiring simultaneous characterization of the optical properties of both the main lens and the MLA:

- **Main lens focal length $f_{\text{main}}$:** Determines the overall magnification and field of view of the system.
- **Microlens focal length $f_{\mu}$:** Typically provided by the manufacturer; the distance $d$ from microlens to sensor satisfies $d \approx f_{\mu}$ (thin-lens focusing condition).
- **Distance $F$ from main lens to MLA:** When $F = f_{\text{main}}$, the MLA is at the rear focal plane of the main lens. In this configuration, each microlens receives collimated light from the main lens, and pixels beneath each microlens correspond to different aperture positions of the main lens (standard Plenoptic 1.0 configuration). When $F \neq f_{\text{main}}$ (Plenoptic 2.0 / Focused Plenoptic Camera), the function of the microlenses changes fundamentally: instead of acting purely as aperture angular separators, each microlens serves as a relay optical system that re-images the intermediate real image formed by the main lens near its front focal plane onto the sensor. This "re-imaging of the intermediate image" structure alters the trade-off between angular sampling and spatial sampling, and under certain conditions can significantly improve the effective spatial resolution of the final output image.

### 2.3 Validation of Disparity Estimation Accuracy

The ultimate test of calibration quality is depth estimation accuracy. Common validation methods include:

1. **Planar target test:** Photographing a flat calibration target at a known depth to verify the absolute accuracy and planarity of the depth map.
2. **Stereo cross-validation:** Comparing depth results against a well-calibrated stereo camera on the same scene.
3. **EPI linearity check:** Straight edges in the scene should appear as straight oblique lines in EPI images; the degree of curvature reflects distortion calibration error.

Typical accuracy: the Lytro Illum achieves a relative depth estimation error of approximately 2–5% over the range 0.3–2 m; industrial-grade Raytrix cameras can achieve 0.1 mm absolute accuracy at close range (5–50 cm).

---

## §3 Tuning

### 3.1 Adjusting the Refocusable Depth Range

The refocusable depth range is determined jointly by the depth of field of the main lens and the angular resolution of the MLA:

$$\Delta z_{\text{refocus}} \approx \frac{2 f_{\text{main}}^2}{N^2 \cdot D_{\mu}} \cdot m$$

where $N$ is the f-number of the main lens, $D_{\mu}$ is the microlens aperture, and $m$ is the number of pixels beneath each microlens. Increasing $m$ (finer angular sampling) expands the refocusable range at the cost of spatial resolution.

Tuning recommendations:
- **Close-range scenes** (portraits, product photography): Reduce $m$ (e.g., from 15×15 to 9×9) to improve spatial resolution and reduce the refocusable range (which does not need to be large at close range).
- **Long-range scenes** (surveillance, autonomous driving): Increase $m$ and pair with a telephoto main lens to extend the refocusable range.

### 3.2 Bokeh Rendering Parameters

Computational bokeh rendering based on a light field depth map offers physical consistency advantages over deep-learning-based bokeh. Key tunable parameters:

- **Synthetic aperture size:** Controls the angular range $(u, v) \in [-U_{\max}, U_{\max}]$ used during summation. A larger synthetic aperture produces stronger background blur.
- **Bokeh kernel shape:** By applying non-uniform weighting in the angular domain (rather than uniform summation), different aperture blade shapes can be simulated (circular, hexagonal, octagonal).
- **Foreground occlusion handling:** Bokeh at the edges of foreground objects suffers from occlusion artifacts, which must be suppressed using layered depth rendering or edge-aware filtering.

### 3.3 Multi-View Super-Resolution

The multi-view structure of the light field naturally supports super-resolution reconstruction. Sub-pixel parallax between sub-aperture views provides different samplings of high-frequency information; theoretically, $n \times n$ views can increase resolution by approximately $\sqrt{n}$ times (limited by overlapping information; the improvement is nonlinear).

Typical workflow:
1. Align all sub-aperture views to a reference viewpoint (using optical flow estimation or depth-based view transformation).
2. Perform multi-frame super-resolution fusion in the frequency domain or spatial domain (e.g., Tikhonov-regularized reconstruction).
3. Apply post-processing sharpening to remove blur introduced by the fusion.

---

## §4 Artifacts

### 4.1 Lenslet Pattern Noise

The most prominent artifact in raw MLA images is a regular grid-like pattern. Light-blocking structures exist between adjacent microlenses, and optical vignetting at the edges of each microlens causes the brightness at the periphery of each patch to be significantly lower than at its center.

After decoding, if alignment accuracy is insufficient (calibration error), content from adjacent microlenses becomes misregistered, appearing in refocused images as fine grid lines or "fish-scale" texture.

**Suppression methods:**
- Accurate MLA center calibration with sub-pixel interpolation alignment.
- Apply vignetting correction within each microlens patch on the raw MLA image (analogous to LSC).
- Downweight or discard pixels at patch boundaries during decoding (at the cost of reducing the effective number of angular samples).

### 4.2 Defocus Halo at Refocused Edges

In refocused images, a "halo" often appears near the edges of sharp foreground objects: an anomalous ring of brightness extends outward from the object boundary. The cause is that background regions behind a foreground edge are partially occluded by the foreground to different degrees in different angular views; after summation, this produces a non-uniform penumbra region.

**Suppression methods:**
- Depth-aware bokeh rendering: handle foreground and background separately at depth boundaries to avoid cross-layer mixing.
- Occlusion-aware light field rendering.

### 4.3 Fundamental Limitation of the Resolution–Depth-of-Field Trade-off

This is a physical constraint of light field cameras, not an artifact that can be fully eliminated. Given a fixed total sensor pixel count, every doubling of angular resolution reduces spatial resolution by the same factor. Deep learning super-resolution can partially mitigate this tension, but is bounded by the information entropy of the light field image and cannot improve resolution without limit.

In practical product design, this trade-off means that light field cameras struggle to compete with high-resolution smartphones in the consumer market, and are better suited for applications where depth information is more valuable than spatial resolution — such as industrial inspection, scientific research, and professional VR/AR.

---

## §5 Evaluation

### 5.1 Sharpness Assessment of Refocused Images

Quality evaluation of refocused images must consider:

- **In-focus sharpness:** MTF (Modulation Transfer Function) or SFR (Spatial Frequency Response) of the focused region, identical to conventional cameras, used to quantify resolution loss at the target depth relative to the raw sensor resolution.
- **Naturalness of out-of-focus blur:** Subjective quality of the bokeh effect, assessable using no-reference image quality metrics such as BRISQUE and NRQM, or quantified through user studies (MOS scores).
- **Focal plane depth accuracy:** When refocusing to a specified depth, the deviation between the actual sharp plane and the target depth, measured using a calibration target at known depth.

### 5.2 Depth Map Accuracy

| Metric | Description |
|---|---|
| **Absolute Relative Error (AbsRel)** | $\frac{1}{N}\sum |d_{\text{pred}} - d_{\text{gt}}| / d_{\text{gt}}$ |
| **RMSE** | Root mean square error of depth predictions (mm) |
| **$\delta < 1.25$** | Fraction of pixels for which the ratio of predicted depth to ground truth falls within $[1/1.25, 1.25]$ |

Evaluation dataset: The HCI 4D Light Field Benchmark (Honauer et al., 2016) is the most widely used standard dataset for light field depth estimation, containing both synthetic and real scenes with per-pixel ground truth depth maps.

### 5.3 Comparison with Conventional Camera + Post-Processing Bokeh

| Dimension | Light Field Camera (Lytro type) | Conventional Camera + Dual-Camera / Depth Bokeh |
|---|---|---|
| Spatial resolution | Low ($1/m^2$ penalty) | High (full sensor resolution) |
| Depth estimation accuracy | Moderate (depends on angular resolution) | Moderate (dual-camera parallax or ToF) |
| Physical consistency of refocusing | High (true light field) | Moderate (requires accurate depth estimation) |
| Foreground occlusion handling | Supported in principle; difficult in practice | Difficult (artifacts at depth discontinuities) |
| Cost / size | High (precision MLA fabrication) | Low (built into smartphones) |
| Consumer market suitability | Low | High |

Conclusion: Light field cameras hold theoretical advantages in physical consistency and computational photography flexibility. However, constrained by resolution penalties and hardware costs, the consumer market has been taken over by solutions combining multi-camera setups with AI-based depth estimation. The core ideas — multi-view light field capture and computational reconstruction — continue to evolve through smartphone multi-camera modules, NeRF, 3DGS, and related directions, and remain important in AR/VR, autonomous driving, and industrial inspection.

---

## §6 Code

The companion notebook for this chapter is *See §6 Code section for runnable examples.*.

Code contents include:
1. Simulated generation of a four-dimensional light field (using Python + NumPy)
2. Implementation of the shift-and-add refocusing algorithm
3. EPI visualization and depth estimation demonstration
4. MLA decoding workflow in the style of LFToolbox

---

## §7 Artifact Analysis

The imaging chain of a light field camera (main lens → microlens array → sensor → digital resampling) introduces a class of artifacts that do not appear in conventional cameras. The following subsections analyze their causes and mitigation strategies.

### 7.1 Microlens Crosstalk

**Cause**

When the f-number of the main lens does not match the f-number of the MLA, the half-angle of the incident light cone exceeds the acceptance angle of a single microlens, causing light to spill over into adjacent microlens regions (crosstalk).

Key constraint:

$$\frac{D_{cone}}{2} = \frac{d_{MLA}}{2 \cdot F_{main}} \leq \frac{d_{MLA} - d_{gap}}{2}$$

where $D_{cone}$ is the diameter of the light cone projected onto the MLA plane, $d_{MLA}$ is the microlens pitch, and $d_{gap}$ is the inter-microlens gap (determined by the fill factor).

**Integer-ratio constraint:** The ratio of microlens pitch $d_{MLA}$ to pixel pitch $d_{px}$ must be an integer ($d_{MLA} / d_{px} \in \mathbb{Z}^+$); otherwise the number of pixels beneath each microlens is unequal, causing systematic fringe artifacts (Moiré) during sub-aperture image resampling.

**Post-processing mitigation:** Calibrating each microlens's pixel coverage individually (via white image calibration) and using interpolated boundary transitions (bilinear transition width $w_{border} = 1$–$2\,\text{px}$) rather than hard truncation during decoding can reduce the resolution loss due to crosstalk by approximately 30%.

### 7.2 Refocusing Blur

Digital refocusing is implemented by shifting sub-aperture images at different angles by an offset $\delta$ and then summing:

$$I_{refocus}(\mathbf{x},\, \alpha) = \frac{1}{N_u N_v}\sum_{u,v} L\!\left(\mathbf{x} - \alpha \cdot \mathbf{d}_{uv},\, u, v\right)$$

where $\alpha$ is the refocusing parameter ($\alpha = 0$ corresponds to the sensor focal plane) and $\mathbf{d}_{uv}$ is the spatial displacement vector corresponding to the angular offset.

**EPI slope error amplification:** A slope estimation error $\varepsilon_{slope}$ in the EPI is amplified by a factor of $|\alpha|$ after refocusing:

$$\sigma_{refocus} = |\alpha| \cdot \varepsilon_{slope} \cdot d_{px}$$

When $|\alpha| > 2$ (deep refocusing), even a 0.1-pixel slope estimation error causes 0.2 px of additional blur, which compounds with the original defocus blur and significantly degrades the perceived sharpness of the refocused image.

**Engineering constraint:** The effective refocusing range is typically limited to $|\alpha| \leq 1.5$, corresponding to a depth range of approximately $\pm 30\%$ of the depth of field on either side of the sensor focal plane.

### 7.3 Disparity Discontinuity

**Cause of "ghost edges"**

At scene depth discontinuities (foreground boundaries), different angular sub-aperture images exhibit different occlusion relationships: some angles can see the background while others are blocked by the foreground. A naive shift-and-add operation introduces background residuals from occluded regions, resulting in "ghost edges."

**Occlusion handling strategies:**

1. **Depth-segmented occlusion-aware summation:** First estimate a depth map, partition the scene into multiple depth layers, sum each layer independently, then composite.
2. **Multi-angle visibility voting:** For each spatial location, count visibility across all $N_u \times N_v$ angular samples and down-weight or discard occluded samples (apply reduced weight when visibility < 50%).
3. **Cost-function regularization:** Add an occlusion-aware regularization term (e.g., anisotropic total variation, TV) to the EPI depth estimation to keep depth estimates sharp at edges.

### 7.4 Spatial Resolution Loss (Resolution–Angle Trade-off)

This is the most fundamental physical constraint of light field cameras, and can be quantified as follows:

Let the total sensor pixel count be $M_{total} = N_{px}^2$, with $m \times m$ pixels beneath each microlens (angular resolution); then:

| Parameter | Value |
|---|---|
| Total microlens count (spatial resolution) | $N_{MLA} = N_{px} / m$ |
| Number of spatial pixels | $N_{MLA}^2 = N_{px}^2 / m^2$ |
| Number of angular samples | $m^2$ |
| Spatial resolution loss factor | $1/m^2$ |

Typical parameters (Lytro Illum, measured): sensor approximately 40 MP ($N_{px} \approx 6325$), $m = 14$ (14×14 pixels per microlens), giving $N_{MLA} \approx 6325/14 \approx 452$ microlenses and a spatial resolution of approximately $452 \times 452 \approx 0.2\,\text{MP}$ — a loss of approximately 200× relative to the raw sensor pixel count ($m^2 = 196 \approx 200$). This is the fundamental reason why light field cameras cannot compete with high-resolution smartphones in the consumer market.

### 7.5 Per-Microlens Vignetting

Microlenses at the periphery of the sensor receive incomplete light cones due to large chief-ray angles (main-lens aberrations), causing systematic brightness vignetting. Unlike the global LSC correction applied in conventional cameras, light field cameras require **independent brightness correction for each microlens:**

$$I_{corrected}(i, x, y) = \frac{I_{raw}(i, x, y)}{G_{vignette}(i, x, y)}$$

where $i$ is the microlens index, $(x, y)$ are the relative pixel coordinates within that microlens, and $G_{vignette}(i, x, y)$ is obtained from white-image calibration (typically stored as a sparse lookup table, approximately 50–200 KB compressed).

---

## §8 Calibration & Evaluation

### 8.1 White Image Calibration

White image calibration is both the first and the most critical step in the light field camera calibration pipeline:

**Calibration procedure:**

1. Place a uniform diffuser in front of the sensor (Lambertian integrating sphere or ground glass) and capture a uniform white-field raw image.
2. Fit a Gaussian to the brightness peak of each microlens patch to extract the microlens center coordinates $(c_{x,i},\, c_{y,i})$.
3. Build the complete microlens center grid mapping (approximately 30k–100k microlenses).
4. Record the pixel coverage range and the relative brightness weight of each pixel for every microlens.

**Microlens center extraction accuracy:** The center coordinate error must be $< 0.1\,\text{px}$; otherwise systematic grid artifacts (grid Moiré) appear in the sub-aperture images.

**Thermal drift compensation:** The thermal expansion coefficient of a microlens array is approximately $10\,\text{ppm/°C}$; over an operating temperature range of $\Delta T = 40\,°\text{C}$, the corresponding displacement is approximately $0.4\,\mu\text{m}$ (about 0.1 px at a 4 μm pixel pitch). Production devices must be calibrated at multiple temperature points spanning the operating range, and a temperature sensor is used to interpolate compensation at runtime.

### 8.2 Per-Microlens Principal Point Calibration

Assembly tolerances between the main lens and the MLA cause the optical axis direction to differ from one microlens to another (each microlens effectively has an independent "principal point offset"). Calibration method:

- Photograph a pinhole target at a known distance, and fit a Gaussian to the EPI slope for each microlens.
- Treat the entire MLA as a calibration target and fit a polynomial model to the principal-point offset field $(δ_x(i,j),\, δ_y(i,j))$.

Accuracy requirement: principal point residual $< 0.05\,\text{px}$, to ensure that sub-aperture image alignment accuracy meets stereo matching requirements.

### 8.3 Depth Accuracy Evaluation

**Dual-plane target method:**

1. Place a flat calibration board at two known distances $d_1, d_2$ in front of the camera (e.g., 0.5 m and 1.0 m).
2. Reconstruct depth maps of the two planes using the light field depth estimation algorithm.
3. Compute the error statistics between estimated and ground-truth depths:

$$\varepsilon_{depth} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} \left( \hat{d}_i - d_{true} \right)^2}$$

**Production target:** $\varepsilon_{depth} < 1\,\text{mm}$ @ $d = 1\,\text{m}$ (corresponding to a relative error of $< 0.1\%$).

### 8.4 Angular Resolution Evaluation (EPI Slope Accuracy)

EPI slope accuracy directly determines disparity estimation accuracy, which in turn affects refocusing quality and depth map precision. Test method:

- Use a flat target at a precisely known depth (accuracy $< 0.1\,\text{mm}$).
- Extract the EPI from the target region, estimate the slope $s_{est}$ by linear fitting, and compare with the theoretical slope $s_{theory}$.
- Disparity accuracy: $\sigma_{disp} = |s_{est} - s_{theory}| < 0.1\,\text{px}$.

### 8.5 Toolchain

| Tool | Language | Primary Function |
|---|---|---|
| **Light Field Toolbox** (Dansereau et al.) | MATLAB | Complete light field processing pipeline: white image calibration, decoding, refocusing, depth estimation |
| **lfptools** | Python | Lytro LFP format parsing, raw light field extraction |
| **lytro-mfdb** | Python | Multi-focus light field database management |
| **LFBM5D** | C++/MATLAB | Light field denoising (5D BM3D extension) |
| **LFSRCheckPoint** | Python/PyTorch | Collection of light field super-resolution models (AAAI/ECCV series) |

---

## §9 Engineering Practice: Plenoptic Approximations in Smartphones

True plenoptic cameras face insurmountable physical limitations on smartphones: limited sensor size, high MLA fabrication cost, and severe resolution loss. Contemporary smartphones therefore employ a variety of approximation strategies to achieve the core capabilities of a light field camera without using an MLA.

### 9.1 Dual-Camera Depth-of-Field Compositing vs. True Light Field

**True light field cameras:** The MLA baseline is $0.1$–$0.5\,\text{mm}$ (pitch of a single microlens), providing dense angular sampling but an extremely short baseline, which limits depth resolution.

**Smartphone dual-camera stereo approach:**

| Parameter | Light Field Camera (MLA) | Smartphone Dual-Camera |
|---|---|---|
| Baseline | $0.1$–$0.5\,\text{mm}$ | $6$–$12\,\text{mm}$ |
| Angular samples | $100$–$200$ directions | $2$ (two cameras) |
| Depth resolution | Low (short baseline) | Moderate (long baseline, but only 2 views) |
| Implementation | Physical MLA | Independent lenses and sensors |
| Bokeh implementation | True light field refocusing | Depth-map-guided bokeh rendering |

The "Portrait Mode" on smartphones is in essence: **dual-camera stereo depth estimation + software bokeh rendering**, not light field refocusing. The perceptual difference is that light field refocusing preserves the true PSF defocus shape (continuously varying with depth) within the in-focus region, whereas software bokeh typically uses a fixed-radius disc kernel, producing unnatural transitions.

### 9.2 ToF + RGB Supplemental Approach (iPhone LiDAR Solution)

iPhone 13 Pro and later models include Apple's custom dToF (direct time-of-flight) LiDAR, fused with the RGB main camera:

- **Depth range:** 0–5 m (effective indoors), accuracy approximately $\pm 1\,\text{cm}$ @ 1 m
- **Resolution:** approximately 320×240 (far below the RGB main camera); requires depth super-resolution upsampling
- **RGB-D fusion:** Using the RGB edge map as guidance, apply guided joint bilateral filtering to upsample the depth map to RGB resolution (12 MP)
- **Effect:** Achieves a per-pixel depth map that simulates post-capture light field refocusing (focus adjustment); depth map quality under low light exceeds that of pure dual-camera solutions

**Limitation:** dToF SNR degrades under strong sunlight (> 100 klux); depth estimation beyond 5 m (outdoors) deteriorates.

### 9.3 Multi-Camera Light Field Approximation (Triple-Camera Parallax Fusion)

Flagship devices such as the Xiaomi 11 Ultra and vivo X90 Pro include ultra-wide (0.6×) / main (1×) / telephoto (3.2×) triple cameras, approximating light field properties as follows:

- **Three-viewpoint parallax:** The three focal-length images, after image registration (homography + optical flow fine-alignment), form a three-viewpoint light field approximation.
- **Multi-focal-length fusion:** Extracts the sharp region from each focal length and composites an all-in-focus image, simulating post-capture focus adjustment.
- **Limitation:** The baselines of the three cameras are fixed in one direction (typically vertical), providing parallax information in only one dimension — a true two-dimensional viewpoint array is not achievable.

### 9.4 Representative Commercial Light Field Camera Products

| Product | Manufacturer | Type | Status | Key Features |
|---|---|---|---|---|
| **Lytro Illum** | Lytro (ceased operations) | Consumer | Discontinued (2018) | First consumer light field camera; 40 Megarays; post-capture refocusing |
| **Raytrix R42** | Raytrix | Industrial | Available | 42 MP; multi-focus MLA; industrial 3D metrology |
| **Pelican Imaging** | Pelican (acquired) | Smartphone module | Discontinued | $4 \times 4$ camera array; early mobile light field module |
| **Ricoh Theta Z1** | Ricoh | Panoramic | Available | 360° light field video; VR content production |
| **Holographic Display Camera** | Meta Reality Labs | Research prototype | Research stage | Light field imaging inside AR/VR headsets; view synthesis research |

> **Engineering note (smartphone ISP and computational photography):** MLA-based plenoptic cameras are a non-viable path for consumer smartphones — the Lytro Illum used a 40 MP sensor but each sub-aperture view had an actual output of only 541×434 ≈ 0.23 MP, in exchange for 14×14 = 196 angular directions. In the pixel-count arms race of smartphones this trade is simply not worth making; furthermore, the spatial–angular trade-off is a hard optical diffraction constraint that will not improve with manufacturing process advances. For smartphone ISP engineers, the value of light field theory lies in revealing the essence of multi-view information: a physical MLA is not needed — dual-camera parallax is sufficient. The practical path is: dual/triple-camera stereo depth estimation (baseline 6–12 mm, relative error 1–2% within 3 m) → ToF supplementing low-light / low-texture regions → depth-map-guided software bokeh rendering. Additional note: if a future proposal suggests "building an MLA into a smartphone module," the LSC calibration volume will grow from 2D to 4D (spatial $(x,y)$ × sub-aperture selection $(u,v)$), increasing calibration time and storage cost by an order of magnitude — a hidden cost that must be factored in when assessing feasibility. The true high-value deployment of light field theory on smartphone platforms is **NeRF / 3DGS multi-frame fusion reconstruction** (using the smartphone as a temporally sparse view capture device). Industrial 3D inspection scenarios (smartphone screen module defect inspection, MEMS, chip wire bonding) remain the genuine market niche for MLA-based cameras, which is why Raytrix and similar companies continue to operate.

---

## §10 Glossary

**Light Field (Light Field / Plenoptic Function)**
A high-dimensional function describing the intensity of rays propagating in any direction from any position in space. The complete Plenoptic Function is 7-dimensional: $L(x, y, z, \theta, \phi, \lambda, t)$, corresponding respectively to spatial position (three dimensions), propagation direction (two spherical-coordinate dimensions), wavelength, and time. In computational light field photography, the commonly used **two-plane parameterization** simplifies this to the 4D form $L(u, v, s, t)$, where $(u, v)$ are lens-plane coordinates and $(s, t)$ are sensor-plane coordinates. This is the mathematical foundation of both the Lumigraph and the light field camera imaging model.

**Microlens Array (MLA)**
An optical element consisting of thousands to hundreds of thousands of miniature convex lenses arranged in a dense array, placed between the rear focal plane of the main lens and the sensor. The core function of the MLA is to map rays incident from different angles at different positions on the main lens pupil onto different spatial locations on the sensor, thereby encoding angular information (directional dimension) as spatial information (pixel position) — enabling a single exposure to record the complete 4D light field. The ratio of MLA pitch ($100$–$200\,\mu\text{m}$) to sensor pixel pitch ($3$–$5\,\mu\text{m}$) is approximately $14$–$50$, which determines the number of angular samples per microlens.

**Epipolar Plane Image (EPI)**
A 2D slice $L(u, s)$ cut from the light field along the $(u, s)$ direction after fixing the $(v, t)$ dimensions. In the EPI, the projections of the same physical point in the scene at different viewpoints ($u$) form a straight line, whose slope $\rho$ is inversely proportional to the object depth $d$: $d \propto 1/\rho$. The EPI is the core analytical tool for light field depth estimation: depth discontinuities manifest as abrupt slope changes, occluded regions exhibit slope interruptions, and dense depth maps can be estimated directly from EPIs via structure tensors or convolutional neural networks to sub-pixel accuracy ($\sigma < 0.1\,\text{px}$).

**Digital Refocusing (Digital Refocusing / Synthetic Aperture Refocusing)**
A post-capture light field refocusing operation: different angular sub-aperture images are displaced by different amounts $\delta_{uv} = \alpha \cdot (u, v)$ and then averaged, synthesizing a sharp image corresponding to the focal plane at refocusing parameter $\alpha$. $\alpha = 0$ corresponds to the original sensor focal plane; $\alpha \neq 0$ corresponds to digitally changing the focus distance. The physical interpretation of this operation is equivalent to integrating all ray contributions at a specific depth plane in the light field — rays from in-focus scene points align coherently across angular views after displacement (signal reinforcement), while rays from out-of-focus points are misaligned (blur spreading) — thereby achieving post-capture adjustable focus.

**Sub-Aperture Image**
A complete 2D spatial image obtained from the 4D light field by fixing the angular parameters $(u_i, v_j)$, equivalent to a view of the entire scene from a specific direction. An array of $n_u \times n_v$ sub-aperture images constitutes a regular viewpoint array (typically $7 \times 7$ or $9 \times 9$); the pixel displacement (parallax) between adjacent views is proportional to scene depth. Sub-aperture images are the fundamental data organization format for light field stereo matching, multi-view super-resolution (LFSSR), and disparity estimation.

**Microlens Crosstalk**
The physical phenomenon of light leaking between adjacent microlenses, caused by a mismatch between the main-lens f-number and the MLA f-number that causes the incident light cone to exceed the acceptance angle of a single microlens. Crosstalk reduces the purity of angular sampling (each "angular sample" is contaminated by neighboring angles), effectively reducing the light field's angular resolution and depth estimation accuracy. Crosstalk severity is quantified by the **Angular Crosstalk Ratio (ACR)**; ACR $< 5\%$ has negligible impact on depth estimation.

**EPI Slope**
The slope $\rho = \Delta s / \Delta u$ of the scene-point trajectory line in an epipolar plane image. Its physical meaning is the spatial displacement per unit angular offset (i.e., the parallax), and it is inversely proportional to scene depth: $d = f_{MLA} \cdot B / (\rho \cdot d_{px})$, where $B$ is the main-lens baseline (equivalent aperture diameter), $f_{MLA}$ is the microlens focal length. EPI slope accuracy directly determines light field depth estimation quality; production calibration requires slope error $< 0.1\,\text{px}$.

**Plenoptic 1.0**
The standard light field camera configuration, in which the MLA is placed at the rear focal plane of the main lens ($F = f_{\text{main}}$). Each microlens records the angular distribution of rays arriving at one spatial position from the main lens pupil. The representative product is the first-generation Lytro. The inherent penalty is that the effective output spatial resolution is only $1/m^2$ of the total sensor pixels.

**Plenoptic 2.0 (Focused Plenoptic Camera)**
A light field camera configuration in which the MLA is displaced from the rear focal plane of the main lens ($F \neq f_{\text{main}}$). Each microlens acts as a relay optical system that re-images the intermediate real image formed by the main lens near its front focal plane onto the sensor. This "re-imaging of the intermediate image" structure alters the spatial–angular sampling trade-off, and under appropriate conditions can significantly improve effective spatial resolution at the cost of a reduced number of angular samples and a narrower refocusable range.

**White Image Calibration**
The foundational step of light field camera calibration: illuminating the sensor with uniform white light (via an integrating sphere or ground glass diffuser) to capture a flat-field raw image, then fitting the brightness peak of each microlens patch to extract the MLA center grid. Center coordinate accuracy must be $< 0.1\,\text{px}$; otherwise systematic grid Moiré artifacts appear in the decoded sub-aperture images. Production systems require multi-temperature calibration to compensate for thermal drift of the MLA.

**Megaray**
A unit of light field data volume introduced by Lytro, denoting the total number of independently captured rays (angular samples × spatial pixels), as distinct from the conventional notion of pixels. The first-generation Lytro captured approximately 11 Megarays; the Illum approximately 40 Megarays. The final rendered image resolution is far lower (approximately 1 MP and 0.2 MP, respectively) due to the angular sampling cost.

**HCI 4D Light Field Benchmark**
A standard evaluation dataset for light field depth estimation published by Honauer et al. (ACCV 2016), containing both synthetic scenes (with precise per-pixel ground-truth depth) and real scenes, including challenging cases such as occlusions, reflections, and fine structures. The standard metrics are Absolute Relative Error (AbsRel), RMSE, and $\delta < 1.25$; it is the primary reference for comparing light field depth algorithms.

**Light Field Super-Resolution (LFSSR)**
Uses the sub-pixel parallax between sub-aperture views — which provides complementary high-frequency information — for joint angular-domain and spatial-domain super-resolution reconstruction via deep learning (e.g., LFSSR, LF-InterNet). Theoretically, $n \times n$ views can provide approximately $\sqrt{n}$-fold resolution improvement, though the actual gain is nonlinear due to overlapping information between views.

**Neural Radiance Field (NeRF)**
A neural network method proposed by Mildenhall et al. (2020) for implicitly reconstructing a three-dimensional scene from sparse views; it can be regarded as a neural network parameterization of a continuous 4D light field. NeRF's view synthesis objective is highly complementary to the post-capture refocusing and view synthesis capabilities of light field cameras: light field cameras densely sample the light field through physical hardware, while NeRF implicitly infers the light field from sparse views through learning, representing an extension of the light field concept into the deep learning era.

---

## Illustrations

![light field 4d](img/fig_light_field_4d_ch.png)
*Figure 1. Schematic diagram of the four-dimensional light field (plenoptic function) parameterization. (Source: Levoy et al., "Light field rendering", SIGGRAPH, 1996)*

![light field camera](img/fig_light_field_camera_ch.png)
*Figure 2. Structural schematic of a light field camera (microlens array type). (Source: Ng, "Fourier slice photography", SIGGRAPH, 2005)*

![plenoptic camera types](img/fig_plenoptic_camera_types_ch.png)
*Figure 3. Comparison of plenoptic camera types: Plenoptic 1.0 vs. Plenoptic 2.0 architecture. (Source: Dansereau et al., "Decoding, calibration and rectification for lenselet-based plenoptic cameras", CVPR, 2013)*

![refocus depth chart](img/fig_refocus_depth_chart_ch.png)
*Figure 4. Example depth map from a light field camera for post-capture refocusing. (Source: Honauer et al., "A dataset and evaluation methodology for depth estimation on 4D light fields", ACCV, 2016)*

![refocusing depth](img/fig_refocusing_depth_ch.png)
*Figure 5. Schematic illustration of digital refocusing principles. (Source: Ng, "Fourier slice photography", SIGGRAPH, 2005)*

## References

1. **Adelson, E. H., & Bergen, J. R. (1991).** The plenoptic function and the elements of early vision. *Computational Models of Visual Processing*, 3–20. MIT Press.
   — The foundational paper on the plenoptic function, defining the seven-dimensional framework for representing visual information.

2. **Levoy, M., & Hanrahan, P. (1996).** Light field rendering. *Proceedings of SIGGRAPH 1996*, 31–42.
   — Proposed the two-plane parameterization of the four-dimensional light field, establishing the theoretical foundation of light field rendering.

3. **Ng, R. (2005).** Fourier slice photography. *ACM Transactions on Graphics (SIGGRAPH 2005)*, 24(3), 735–744. And Ng's Stanford doctoral dissertation *Digital Light Field Photography* (2006).
   — The direct theoretical source of the Lytro commercial light field camera; proposed the Fourier slice refocusing algorithm.

4. **Wanner, S., & Goldluecke, B. (2013).** Variational light field analysis for disparity estimation and super-resolution. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 36(3), 606–619.
   — A systematic framework for light field disparity estimation and super-resolution; an important reference for EPI analysis methods.

5. **Dansereau, D. G., Pizarro, O., & Williams, S. B. (2013).** Decoding, calibration and rectification for lenselet-based plenoptic cameras. *CVPR 2013*.
   — Complete calibration workflow for light field cameras; the companion LFToolbox is open source (MATLAB).

6. **Honauer, K., Johannsen, O., Kondermann, D., & Goldluecke, B. (2016).** A dataset and evaluation methodology for depth estimation on 4D light fields. *ACCV 2016*.
   — The HCI 4D light field depth estimation benchmark; the standard reference dataset for evaluating light field depth algorithms.
