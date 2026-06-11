# Part 1, Chapter 12: Depth Sensing

> **Pipeline position:** Depth map generation module; output feeds downstream modules such as bokeh/AR/3D reconstruction
> **Prerequisites:** Chapter 2 (Optics Fundamentals), Chapter 3 (Sensor Physics), Chapter 9 (Camera Calibration)
> **Reader path:** Algorithm engineers, system engineers

---

Depth sensing is one of the core capabilities of modern computational photography. From portrait bokeh on smartphones to obstacle detection in autonomous vehicles, from spatial localization in augmented reality (AR) to three-dimensional measurement in industrial inspection, obtaining precise depth information about a scene has become a fundamental requirement in an ever-growing range of applications. Unlike conventional RGB imaging, depth sensing faces a central challenge: how do we reliably recover the distance from a camera to objects in three-dimensional space from the two-dimensional projected data of a sensor?

This chapter systematically introduces the fundamental principles, calibration procedures, tuning strategies, common artifacts, and evaluation frameworks for the mainstream depth sensing technologies — Time-of-Flight (ToF), Structured Light, Stereo Vision, and Monocular Depth Estimation — and discusses engineering practices for multi-technology fusion.

---

## §1 Theory

### 1.1 Classification of Depth Sensing Technologies

Depth sensing technologies can be divided into two broad categories — **active** and **passive** — depending on whether they emit light into the scene.

**Active depth sensing** relies on the interaction between self-emitted light and the scene to measure depth. Typical technologies include:
- Time-of-Flight (ToF): measures the round-trip time or phase shift of light pulses or modulated light
- Structured Light: projects known patterns and infers depth from the degree of pattern deformation
- LiDAR (Light Detection and Ranging): high-precision point cloud scanning, mainly used in autonomous driving

**Passive depth sensing** uses only natural or ambient scene light. Typical technologies include:
- Stereo Vision: triangulation from disparity between two cameras
- Monocular Depth Estimation: single camera + deep learning inference

Key parameter comparisons across technologies are shown in Table 1-1:

| Technology | Accuracy | Range | Power | Ambient Light Robustness | Typical Applications |
|------------|----------|-------|-------|--------------------------|----------------------|
| dToF | 1–5 cm | 0.5–200 m | High | Medium | Autonomous driving, iPad LiDAR |
| iToF | 0.5–2 cm | 0.1–10 m | Medium | Weak (fails in strong light) | Smartphone portrait, AR |
| Structured Light | 0.1–1 mm | 0.1–3 m | Medium | Weak (fails outdoors) | Face ID, industrial inspection |
| Stereo Vision | 0.1–2% | 0.3–100 m | Low | Strong | Smartphone bokeh, drones |
| Monocular Estimation | Relative depth | Unlimited | Low | Strong | Lightweight mobile scenarios |

---

### 1.2 Time-of-Flight (ToF)

ToF technology uses the constant speed of light to calculate depth by measuring the round-trip time of a light signal. Depending on the modulation scheme, ToF is divided into **direct ToF (dToF)** and **indirect ToF (iToF)**.

#### 1.2.1 Direct ToF (dToF)

dToF emits extremely short laser pulses and precisely measures the time interval $t$ from emission to detection of the pulse reflected from the target. The depth formula is:

$$Z = \frac{c \cdot t}{2}$$

where $c \approx 3 \times 10^8 \text{ m/s}$ is the speed of light; the factor of 2 accounts for the round-trip path.

To precisely measure nanosecond-level time differences, dToF typically uses Single-Photon Avalanche Diode (SPAD) arrays as detectors, paired with Time-to-Digital Converters (TDC) to achieve picosecond-level time resolution. The LiDAR Scanner introduced in Apple iPad Pro and iPhone 12 Pro uses a dToF approach, with a measurement range of up to 5 m indoors and centimeter-level accuracy within 0.5 m.

**The core limitations of dToF** are high detector unit cost, low spatial resolution (typical SPAD array resolution is on the order of 256×256), and degraded signal-to-noise ratio under strong ambient light.

#### 1.2.2 Indirect ToF (iToF)

iToF does not directly measure time; instead it uses Continuous Wave Modulation (CWM) to measure the **phase shift** between the emitted and received light and thereby indirectly calculate depth.

Let the modulation frequency be $f_{\text{mod}}$. The emitted sinusoidally modulated light can be expressed as $S(t) = A \cos(2\pi f_{\text{mod}} t)$. After traveling a round-trip distance of $Z$, the returned signal acquires a phase delay $\phi$ relative to the emitted signal:

$$\phi = \frac{4\pi f_{\text{mod}} Z}{c}$$

Therefore the depth formula is:

$$Z = \frac{c}{4\pi f_{\text{mod}}} \cdot \phi$$

In practice, iToF sensors typically use four-phase sampling (0°, 90°, 180°, 270°) to acquire in-phase ($I$) and quadrature ($Q$) components. The phase shift is computed using the arctangent function:

$$\phi = \arctan\left(\frac{Q}{I}\right)$$

Substituting into the depth formula:

$$Z = \frac{c}{4\pi f_{\text{mod}}} \cdot \arctan\left(\frac{Q}{I}\right)$$

The amplitude (indicating reflectivity) is:

$$A = \sqrt{I^2 + Q^2}$$

Taking the Sony IMX556 as an example, at a modulation frequency of $f_{\text{mod}} = 20$ MHz, the Maximum Unambiguous Range (MUR) for single-frequency continuous-wave iToF is:

$$Z_{\max} = \frac{c}{2 f_{\text{mod}}} = \frac{3 \times 10^8}{2 \times 20 \times 10^6} = 7.5 \text{ m}$$

When the target distance exceeds $Z_{\max}$, the phase wraps by $2\pi$, causing depth ambiguity. Real systems often use multi-frequency modulation or phase unwrapping methods to extend the unambiguous range.

Devices such as the Huawei P30 Pro and Xiaomi 10 Ultra integrate iToF sensors, primarily for portrait depth assistance and AR functions within a 3–5 m range.

**The main challenges of iToF include:**

1. **Multipath Interference (MPI)**: light rays that undergo multiple reflections between objects before arriving at the sensor are superimposed, causing phase measurement bias. This is particularly severe near glass surfaces, mirrors, and corners.
2. **Motion blur**: four-phase sampling requires exposures at different moments; if moving objects are present, the four frames are inconsistent with each other, causing depth errors.
3. **Strong-light saturation**: intense ambient infrared light outdoors (sunlight contains significant 850–940 nm infrared content) swamps the iToF modulated signal, rendering the measurement invalid.

---

### 1.3 Structured Light

Structured light projects **known encoded patterns** onto a scene and infers depth from the **deformation** of the patterns on object surfaces using triangulation.

#### 1.3.1 Triangulation Principle

Let $B$ be the baseline distance between the projector and the camera, $f_p$ the projector focal length, $f_c$ the camera focal length, and $d = u_p - u_c$ the disparity between the projector pixel coordinate $u_p$ and the camera pixel coordinate $u_c$. The depth is:

$$Z = \frac{B \cdot f_c}{d}$$

This has the same form as the stereo vision formula, with the difference that the "second camera" is replaced by the projector. Because the projected pattern encoding is known, finding correspondences in structured light is more robust than feature matching in stereo vision, making it suitable for textureless surfaces.

#### 1.3.2 Encoding Schemes

Common structured light encoding schemes include:

- **Random speckle**: PrimeSense technology (later acquired by Apple); Apple Face ID uses this scheme, projecting **more than 30,000** invisible infrared speckle dots (Apple's official description: "more than 30,000 invisible dots"), obtaining depth by matching the speckle pattern. Advantage: single-frame capture, suitable for dynamic scenes (face recognition). Limitation: relatively limited depth resolution.
- **Phase-shift fringe**: projects multiple sets of sinusoidal fringes (typically 3–4 frames at different phases) and recovers high-accuracy depth maps through phase unwrapping. Depth accuracy can reach 0.1 mm, but multi-frame capture is required, making it unsuitable for dynamic scenes; mainly used in industrial inspection.
- **Binary coding**: Gray code and similar sequential encoding; each position has a unique binary code. Robust but requires multi-frame capture.

#### 1.3.3 Accuracy-Range Trade-off

Structured light achieves extremely high accuracy at short range (0.1–1.5 m), but as distance increases the disparity $d$ decreases and depth accuracy degrades rapidly (accuracy is proportional to $Z^2$). Furthermore, because it relies on an active light pattern, signal-to-noise ratio under strong outdoor ambient light is very low; practical usage is typically limited to indoor or short-range scenarios.

---

### 1.4 Stereo Vision

Stereo vision uses two cameras to photograph the same scene from different angles, then finds corresponding pixel pairs (**matching**) to compute **disparity**, and recovers depth from disparity.

#### 1.4.1 Fundamental Depth-Disparity Formula

Let $B$ be the baseline (distance between optical centers), $f$ the camera focal length, and $d$ the horizontal coordinate difference of corresponding points in the left and right images (disparity). The depth is:

$$Z = \frac{f \cdot B}{d}$$

The depth resolution (how depth error changes with distance) is:

$$\frac{\partial Z}{\partial d} = -\frac{f \cdot B}{d^2} = -\frac{Z^2}{f \cdot B}$$

This means **depth accuracy degrades as the square of the distance**; near-range measurements are accurate while far-range errors are large. Increasing the baseline $B$ or focal length $f$ improves far-range accuracy, but smartphone form factors constrain the baseline to typically 15–35 mm.

#### 1.4.2 Stereo Matching Algorithms

The core challenge is finding correct corresponding pixel pairs in the left and right images. Leading algorithms include:

**Semi-Global Matching (SGM)**, proposed by Hirschmuller (2008), is the classic algorithm that best balances accuracy and efficiency. Its core idea is to perform dynamic programming along one-dimensional cost paths, aggregating costs from multiple directions (typically 8):

$$L_r(p, d) = C(p, d) + \min \begin{cases} L_r(p-r, d) \\ L_r(p-r, d-1) + P_1 \\ L_r(p-r, d+1) + P_1 \\ \min_{i} L_r(p-r, i) + P_2 \end{cases} - \min_k L_r(p-r, k)$$

where $C(p,d)$ is the matching cost at pixel $p$ and disparity $d$ (typically computed with Census transform or SAD), $P_1$ and $P_2$ are smoothness penalty terms, and $r$ is the direction vector.

The final disparity map is selected from the multi-direction aggregated cost using a Winner-Take-All (WTA) strategy.

**Confidence filtering** is a key post-processing step for improving stereo quality:
- Left-Right Consistency Check: compute depth from the left view and from the right view separately; mark as invalid where they disagree
- Uniqueness Check: if the cost difference between the best and second-best disparity is too small, the match is unreliable
- Textureless region detection: regions with very low local variance produce untrustworthy matches

#### 1.4.3 Stereo Implementation in Smartphones

Constrained by smartphone form factors, typical smartphone stereo implementations use:
- **Main + ultra-wide**: large disparity but distortion correction is needed; commonly used to assist portrait bokeh
- **Main + telephoto**: large difference in field of view, requiring image normalization; suitable for medium-to-long range depth

Because smartphone stereo baselines are short (typically 10–30 mm), accuracy within 0.5 m is adequate but errors become significant beyond 1 m. High-end smartphones therefore typically combine stereo with ToF or structured light.

---

### 1.5 Monocular Depth Estimation

Estimating depth from a single RGB image is an inherently ill-posed problem — in theory, the same two-dimensional image can correspond to infinitely many three-dimensional scene configurations. Deep learning mitigates this by learning scene priors (object sizes, perspective rules, texture gradients, etc.).

#### 1.5.1 Self-Supervised Learning Methods

**Monodepth2** (Godard et al., 2019) is a representative work in self-supervised monocular depth estimation. Its core idea is to use the ego-motion between adjacent frames in a video sequence as the supervisory signal, training the depth network via a photometric reconstruction loss without requiring ground-truth depth annotations:

$$\mathcal{L}_p = \alpha \frac{1 - \text{SSIM}(I_t, \hat{I}_t)}{2} + (1-\alpha) \|I_t - \hat{I}_t\|_1$$

where $\hat{I}_t$ is the target frame reconstructed from the predicted depth and an adjacent frame via bilinear interpolation, and $\text{SSIM}$ is the structural similarity measure.

**PackNet** (Guizilini et al., CVPR 2020) introduced Pack/Unpack rearrangement modules: the Pack operation packs a local spatial neighborhood of the feature map into the channel dimension (essentially a spatial-to-channel rearrangement, analogous to pixel_unshuffle) as a lossless replacement for strided convolution downsampling, avoiding loss of spatial detail; Unpack is the inverse operation for decoder upsampling. The overall network is still based on a 2D convolutional U-Net architecture, not 3D convolution, achieving accuracy close to supervised learning on the KITTI dataset.

#### 1.5.2 Supervised Learning Methods

**MiDaS** (Ranftl et al., 2020) addresses inconsistent depth annotation scales across different datasets through mixed multi-dataset training, achieving robust generalization to diverse scenes. **DPT** (Dense Prediction Transformer, Ranftl et al., 2021) introduces the Vision Transformer (ViT) into dense prediction tasks, using global attention mechanisms to capture long-range dependencies, significantly surpassing purely CNN-based methods in depth estimation accuracy.

#### 1.5.3 Scale Ambiguity

The fundamental limitation of monocular depth estimation is **scale ambiguity**: the network output is a relative depth map and the absolute scale cannot be determined. Engineering solutions include:
- Introducing reference objects of known size (e.g., the ground plane, lane markings)
- Fusing IMU data to estimate absolute scale
- Aligning with sparse LiDAR point clouds (Depth Completion)

---

### 1.6 Multi-Technology Fusion

In real products, a single depth technology often cannot meet all-scenario requirements. Multi-technology fusion exploits the strengths of each technology while compensating for their respective weaknesses.

#### 1.6.1 ToF + RGB Stereo Fusion

A typical architecture fuses the dense-but-noisy iToF depth map with the high-resolution-but-unstable-at-range stereo depth map:

$$Z_{\text{fused}}(p) = \frac{w_{\text{ToF}}(p) \cdot Z_{\text{ToF}}(p) + w_{\text{stereo}}(p) \cdot Z_{\text{stereo}}(p)}{w_{\text{ToF}}(p) + w_{\text{stereo}}(p)}$$

where the confidence weight $w(p)$ is given by the respective confidence maps. ToF confidence is typically positively correlated with the amplitude map $A = \sqrt{I^2 + Q^2}$; stereo confidence is negatively correlated with the left-right consistency error.

#### 1.6.2 Depth Completion

Using sparse LiDAR point clouds (or sparse ToF measurements) combined with RGB images, a neural network completes a dense depth map. This is a common approach in autonomous driving. Representative works include CSPN (Cheng et al., 2018) and PENet (Hu et al., 2021).

---

## §2 Calibration

### 2.1 ToF Sensor Calibration

iToF sensors exhibit systematic phase biases, whose main sources include:

**Phase nonlinearity (wiggling error)**: Because real iToF sensors contain non-sinusoidal harmonic components, the phase-to-depth mapping is not perfectly linear, manifesting as periodic oscillation in the depth value around the true distance (typically with amplitude 1–3 cm). The calibration method is to collect data using a precision flat target at various distances, then fit a polynomial correction curve for the phase-to-true-distance mapping, or pre-store a look-up table (LUT) for per-pixel compensation.

**Fixed Pattern Noise (FPN)**: The phase offset differs systematically across sensor pixels. By collecting dark frames of a uniformly reflecting surface (e.g., an integrating sphere) and subtracting them at runtime, the impact of FPN can be substantially reduced.

**Amplitude-dependent error**: Variations in target reflectivity cause the received signal amplitude to vary, and amplitude changes introduce additional phase offsets. A correction model must be built under different amplitude conditions.

**Temperature drift calibration**: The phase offset of ToF sensors changes with temperature (approximately 0.1–0.5 cm/°C). Data must be collected at multiple temperature points (e.g., 0°C, 25°C, 50°C) to build a temperature-to-depth correction model.

### 2.2 RGB–Depth Extrinsic Calibration

Depth maps and RGB images typically come from different sensors. Calibrating the **extrinsic parameters** between them — rotation matrix $R$ and translation vector $t$ — is required to project the depth map into the RGB camera coordinate system and achieve pixel-level RGB-D alignment (depth registration).

Standard procedure:
1. Use a checkerboard or dot-grid calibration target; extract corner/center image coordinates separately in the RGB and depth cameras
2. Use PnP (Perspective-n-Point) or direct linear transform methods to solve for the intrinsic parameters (if not yet calibrated) and extrinsic parameters of each camera
3. Jointly optimize the relative pose of the RGB and depth cameras by minimizing reprojection error:

$$[R, t] = \arg\min \sum_i \left\| x_i^{\text{RGB}} - \pi_{\text{RGB}}\left(R \cdot \pi_{\text{depth}}^{-1}(x_i^{\text{depth}}, Z_i) + t\right) \right\|^2$$

4. For iToF sensors, also ensure time synchronization with the RGB camera (typically within the same frame or within 1 ms); otherwise, minute handheld motion will cause alignment errors.

### 2.3 Depth Accuracy Verification

After calibration, depth accuracy must be systematically verified. A common method is to place a precision flat target at known distances (e.g., 0.3 m, 0.5 m, 1.0 m, 1.5 m, 2.0 m, 3.0 m), compare the measured depth values in the target region against the true distances, and plot an **accuracy vs. range curve**.

Standard metrics include:
- **Mean Absolute Error (MAE)**: $\text{MAE} = \frac{1}{N}\sum |Z_{\text{pred}} - Z_{\text{gt}}|$
- **Root Mean Square Error (RMSE)**: $\text{RMSE} = \sqrt{\frac{1}{N}\sum (Z_{\text{pred}} - Z_{\text{gt}})^2}$
- **Systematic bias**: the mean error, reflecting residual systematic error after calibration
- **Accuracy degradation with range** (typically iToF achieves ~5–10 mm accuracy at 1 m, degrading to 20–30 mm at 3 m)

---

## §3 Tuning

### 3.1 ToF Integration Time vs. Accuracy/Noise Trade-off

The SNR of each iToF acquisition is determined by the number of photons received, which is proportional to the integration time. Increasing integration time improves SNR and reduces depth noise, but introduces the following side effects:

- **Motion blur**: when integration time is too long, moving targets shift position during the four-phase acquisition, causing depth errors (typical symptom: depth "ghost" at moving edges)
- **Strong-light saturation**: in intense ambient light, long integration causes pixel saturation and completely invalidates the depth
- **Increased power consumption**: the longer the integration time, the greater the emitted power–time product and battery drain

Practical tuning strategies:
- **Dual integration time strategy**: short integration (~100 μs) for close range or high-reflectance regions; long integration (~400 μs) for far range or low-reflectance regions; adaptively switch based on the amplitude map
- **HDR mode**: multi-exposure merging (analogous to RGB HDR); use short-exposure results for high-amplitude regions, long-exposure results for low-amplitude regions
- **Integration time upper bound**: typically derived from the maximum allowable motion (e.g., for face motion at 0.5 m/s with a 5 mm allowed depth error, back-calculate the integration time upper bound)

### 3.2 Depth Map Filtering (Temporal + Spatial)

Raw ToF depth maps are noisy (high-frequency random noise) and contain flying pixels at edges; multi-level filtering is required:

**Spatial filtering:**
- **Bilateral filter**: balances spatial distance and depth value similarity, smoothing noise while preserving depth edges:

$$Z_{\text{filtered}}(p) = \frac{\sum_{q \in \Omega} G_s(\|p-q\|) \cdot G_r(|Z(p)-Z(q)|) \cdot Z(q)}{\sum_{q \in \Omega} G_s(\|p-q\|) \cdot G_r(|Z(p)-Z(q)|)}$$

- **Joint bilateral filter (cross bilateral filter)**: uses edge information from the high-resolution RGB image to guide depth map filtering, preventing the depth filter from crossing true depth boundaries due to depth map noise

**Temporal filtering:**
- **Exponential Moving Average (EMA)**: $Z_t = \alpha Z_{\text{raw},t} + (1-\alpha) Z_{t-1}$, $\alpha \in [0.3, 0.7]$; suitable for static scenes, can significantly reduce inter-frame noise
- **Motion-adaptive temporal filtering**: when motion is detected, increase $\alpha$ (trust the current frame more); when static, decrease $\alpha$ (make full use of historical frames); avoids depth trailing on moving objects

### 3.3 Confidence Map Threshold Setting

The confidence map is a key auxiliary output for depth quality assessment, used to mark unreliable depth pixels. Common confidence sources:

- **iToF amplitude map**: amplitude $A = \sqrt{I^2 + Q^2}$ below a threshold (e.g., < 50–100 counts, sensor-dependent) indicates a signal too weak to trust
- **Stereo confidence**: regions where the left-right consistency error $|d_L - d_R| > \epsilon$ (typically $\epsilon = 1$ pixel) are marked as invalid
- **Depth gradient**: excessively large spatial gradients in the depth map often indicate flying pixels or occlusion boundaries and can assist filtering

Threshold setting requires balancing **valid pixel rate** against **depth accuracy**: setting the threshold too low (too strict) discards large numbers of valid pixels, creating holes; setting it too high (too loose) retains many noisy pixels, degrading downstream applications (e.g., bokeh with incorrect depth causing background leakage).

Recommended tuning procedure:
1. Collect statistics of amplitude/confidence distributions under standard scenes (flat target + textured target)
2. Using RMSE as the optimization objective, sweep the threshold parameter and plot the RMSE vs. valid-pixel-rate curve
3. Select the appropriate operating point for the application scenario (e.g., portrait bokeh prioritizes valid pixel coverage of the human body region, even if some noise pixels are retained)

---

## §4 Artifacts

### 4.1 Flying Pixels

Flying pixels (also called edge artifacts or mixed pixels) are among the most common artifacts in depth sensing, appearing at depth-discontinuous boundaries (e.g., foreground object edges). Their physical cause is that the ToF sensor pixel or the stereo matching search window straddles both foreground (near) and background (far) at the boundary, yielding a depth value intermediate between the two and forming "floating" spurious depth points.

**Manifestation**: a ring of transition pixels appears at object edges in the depth map, with depth values belonging to neither foreground nor background. In depth visualizations these appear as scattered point cloud, and in bokeh applications they cause a halo artifact (background leakage) along the foreground silhouette.

**Mitigation methods**:
- Post-process the depth edges with erosion, discarding several pixels near the boundary
- Use precise RGB edges (from semantic segmentation or edge detection) to replace mixed-pixel regions in the depth map
- Use joint bilateral filtering guided by RGB edges to prevent depth smoothing across true depth discontinuities

### 4.2 Multipath Interference (MPI)

Multipath interference is a systematic error unique to iToF and structured light systems, occurring when light reaches the sensor after multiple reflections (e.g., in corners, behind glass, from smooth metallic surfaces). Because the sensor receives a superposition of direct and multi-bounce reflected light, the measured phase is a weighted mixture of multiple paths, causing depth bias (typically underestimating distance, i.e., the measured distance is smaller than the true distance).

**MPI correction methods**:
- **Sparse deconvolution**: assuming sparse scene depth, recover true multi-depth components through L1-regularized deconvolution
- **Multi-frequency ToF**: use multiple modulation frequencies; exploit the phase relationships between frequencies to separate the direct component from multipath components
- **Deep learning methods**: train an end-to-end network to directly predict MPI-corrected depth maps from multi-frame ToF raw data (IQ maps), e.g., Agresti et al., 2019

### 4.3 Ambient Light Saturation (iToF Failure in Strong Light)

The core operating principle of iToF sensors depends on phase sampling of modulated light, not direct measurement of total photon count. However, when the infrared content (850–940 nm band) of broadband ambient light (sunlight) is too strong, it occupies the sensor's dynamic range, causing:

- **Pixel saturation**: ambient light fills the pixel's full well capacity, completely swamping the modulated light signal
- **Sharply degraded SNR**: even without saturation, excessive background signal reduces the relative signal strength of the modulated light to extremely low levels

**Countermeasures**:
- **Narrow-band filter**: mount a 10–20 nm bandwidth narrow-band filter in front of the sensor, allowing only light matching the source wavelength to pass; this suppresses most sunlight. The cost is increased lens assembly cost and thickness.
- **Higher modulation frequency**: increasing $f_{\text{mod}}$ reduces the integration time (while maintaining the same MUR condition), thereby reducing ambient light accumulation
- **Differential measurement**: some sensors support alternating on/off sampling of the modulated light within the same exposure cycle; differencing cancels stable background light components

### 4.4 Depth Estimation Errors from Motion Blur

iToF four-phase sampling requires sequential exposure at different phase moments (time gaps can range from hundreds of microseconds to several milliseconds). If moving objects are present, they occupy different positions in each phase frame; the phase computed from the superimposed frames no longer corresponds to any real distance, producing systematic depth errors.

In stereo vision, if a time difference exists between the left and right cameras (non-synchronized triggering), moving objects occupy different positions in the left and right frames, causing incorrect disparity calculations and thus incorrect depth.

**Mitigation strategies**:
- **Global shutter sensor**: all pixels expose simultaneously, eliminating motion artifacts introduced by rolling shutters
- **Shorten sampling interval**: compress the total time window for four-phase sampling as much as frame rate allows
- **Moving object detection and masking**: use optical flow or frame differencing to detect motion regions, mark depth values in those regions as low-confidence, and down-weight or ignore them in downstream processing

---

## §5 Evaluation

### 5.1 Depth Accuracy Metrics

The most commonly used numerical metrics for depth accuracy evaluation are:

**Root Mean Square Error (RMSE):**

$$\text{RMSE} = \sqrt{\frac{1}{N}\sum_{i=1}^{N}\left(Z_{\text{pred},i} - Z_{\text{gt},i}\right)^2}$$

RMSE is more sensitive to large errors, reflecting occasional large deviation problems; it is suitable for evaluating worst-case system performance.

**Mean Absolute Error (MAE):**

$$\text{MAE} = \frac{1}{N}\sum_{i=1}^{N}\left|Z_{\text{pred},i} - Z_{\text{gt},i}\right|$$

MAE is more robust to outliers (flying pixels), reflecting typical error levels.

**Threshold Accuracy (δ):**

$$\delta_n = \frac{1}{N}\left|\left\{i \,\middle|\, \max\left(\frac{Z_{\text{pred},i}}{Z_{\text{gt},i}}, \frac{Z_{\text{gt},i}}{Z_{\text{pred},i}}\right) < 1.25^n \right\}\right|$$

$\delta_{<1.25}$ (i.e., $n=1$) is the fraction of pixels where the ratio of predicted to ground-truth depth (or its reciprocal) is within $[1/1.25, 1.25]$; this is the most commonly used accuracy metric in monocular depth estimation. $\delta_{<1.25^2}$ and $\delta_{<1.25^3}$ correspond to progressively more relaxed error tolerances.

**Relative Error (REL):**

$$\text{REL} = \frac{1}{N}\sum_{i=1}^{N}\frac{\left|Z_{\text{pred},i} - Z_{\text{gt},i}\right|}{Z_{\text{gt},i}}$$

Relative error eliminates the effect of distance, making it suitable for unified evaluation across different range scales.

### 5.2 Depth Coverage

Depth coverage (fill rate) measures the fraction of valid depth pixels:

$$\text{Coverage} = \frac{\text{number of valid depth pixels}}{\text{total image pixels}} \times 100\%$$

In practice, the definition of "valid depth pixel" must incorporate the confidence threshold: only pixels with confidence above the set threshold count as valid and participate in accuracy calculation. There is a natural trade-off between coverage and accuracy: lowering the confidence threshold increases coverage but introduces more erroneous pixels, raising RMSE.

A complete evaluation report should provide RMSE-vs-Coverage curves at various confidence thresholds, rather than a single number.

### 5.3 Robustness Evaluation

Engineering-grade depth sensing systems also require systematic evaluation under various interference conditions:

- **Strong ambient light test**: evaluate depth validity rate and accuracy under 100,000 lux natural light (sunny outdoor midday) and 10,000 lux strong indoor lighting
- **Multi-device interference test**: multiple ToF devices of the same type operating simultaneously; evaluate depth errors caused by mutual interference (applicable to multi-person AR scenarios such as conference rooms)
- **Multipath scene test**: evaluate the magnitude of MPI errors in scenes with strong multipath (corners, glass display cases, etc.)
- **Motion test**: evaluate depth errors caused by motion blur when the measured target moves at 0.5 m/s, 1.0 m/s, and 2.0 m/s
- **Temperature stability test**: verify that calibrated depth accuracy meets specification at 0°C, 25°C, and 50°C ambient temperatures

---

## §6 Code

The accompanying code for this chapter is available in: *See §6 Code section for runnable examples.*

Code examples cover the following:
1. **iToF depth calculation simulation**: compute phase and depth from four-phase raw data (I₀°, I₉₀°, I₁₈₀°, I₂₇₀°), visualize phase noise
2. **SGM stereo matching**: implementation based on OpenCV's `StereoSGBM`, demonstrating disparity map computation and post-processing
3. **Depth accuracy evaluation**: compute RMSE, MAE, $\delta_{<1.25}$, and other metrics; plot accuracy-vs-range curves
4. **Bilateral filter depth smoothing**: compare noise levels of raw vs. filtered depth maps
5. **MiDaS monocular depth inference**: invoke a pre-trained MiDaS model to estimate a relative depth map for an arbitrary RGB image

---

## References

1. **Hansard, M., Lee, S., Choi, O., & Horaud, R. (2012).** *Time-of-Flight Cameras: Principles, Methods and Applications*. Springer Briefs in Computer Science. — Systematic overview of ToF technology, covering the principles, noise models, and calibration methods of dToF and iToF.

2. **Hirschmuller, H. (2008).** Stereo processing by semiglobal matching and mutual information. *IEEE Transactions on Pattern Analysis and Machine Intelligence, 30*(2), 328–341. — Original SGM paper; one of the most important classic works in stereo matching.

3. **Godard, C., Mac Aodha, O., Firman, M., & Brostow, G. J. (2019).** Digging into self-supervised monocular depth estimation. *ICCV 2019*. (Monodepth2) — Representative work in self-supervised monocular depth estimation, introducing key techniques such as minimum photometric error and auto-masking.

4. **Ranftl, R., Lasinger, K., Hafner, D., Schindler, K., & Koltun, V. (2020).** Towards robust monocular depth estimation: Mixing datasets for zero-shot cross-dataset transfer. *IEEE Transactions on Pattern Analysis and Machine Intelligence*. (MiDaS) — Milestone work achieving cross-scene generalization through mixed multi-dataset training.

5. **Scharstein, D., & Szeliski, R. (2002).** A taxonomy and evaluation of dense two-frame stereo correspondence algorithms. *International Journal of Computer Vision, 47*(1–3), 7–42. — Foundational survey establishing the taxonomy of stereo vision algorithms; proposed the Middlebury evaluation benchmark still in use today.

6. **Agresti, G., Minto, L., Marin, G., & Zanuttigh, P. (2019).** Unsupervised domain adaptation for ToF data denoising with adversarial learning. *CVPR 2019*. — Joint correction of iToF multipath interference and noise using deep learning, demonstrating the potential of data-driven methods in ToF calibration.

---

*Author's note: Depth sensing is a rapidly evolving field. As SPAD array resolution continues to increase (dToF arrays are rapidly advancing from tens of thousands of pixels toward megapixel-class; Sony and other manufacturers have released high-resolution dToF sensors for both industrial and consumer markets) and Transformer-based stereo matching methods (RAFT-Stereo, UniMatch, etc.) approach LiDAR-level accuracy, the depth sensing capability of smartphone platforms is expected to reach a new level within the next 2–3 years. The deep integration of ToF and computational photography is a direction well worth continued attention.*

---

## §8 Glossary

**Depth Sensing**
The general term for technologies that acquire three-dimensional depth information of a scene from sensor data, divided into active and passive categories. Active methods emit their own light source (ToF, structured light, LiDAR); passive methods use only natural light (stereo vision, monocular depth estimation). Depth maps are key intermediate results in the ISP computational photography pipeline, used by downstream modules such as portrait bokeh, AR spatial localization, and 3D reconstruction.

**Time-of-Flight (ToF)**
A class of technologies that use the constant speed of light to calculate target distance by measuring the round-trip time or phase shift of a light signal. Divided into direct ToF (dToF, directly measuring pulse round-trip time) and indirect ToF (iToF, measuring modulated light phase shift). ToF is the mainstream depth sensing approach in current smartphones and tablets (Apple iPad LiDAR, Huawei/Xiaomi iToF).

**Direct ToF (dToF)**
Emits nanosecond-scale ultrashort laser pulses; uses a SPAD array and TDC to precisely measure round-trip time $t$; depth $Z = c \cdot t / 2$. Advantages: wide measurement range (up to 5–200 m), no range ambiguity. Disadvantages: high SPAD array cost, lower resolution (typically 256×256). The LiDAR Scanner in Apple iPad Pro/iPhone is a dToF implementation.

**Indirect ToF (iToF)**
Uses continuous wave modulation (CWM) to measure the phase shift between emitted and reflected light to indirectly compute depth: $Z = c \phi / (4\pi f_{\text{mod}})$. The maximum unambiguous range for single-frequency continuous-wave iToF is $Z_{\max} = c / (2 f_{\text{mod}})$ (e.g., 20 MHz modulation gives 7.5 m). Requires four-phase sampling (0°/90°/180°/270°); subject to multipath interference, motion blur, and strong-light saturation. Rear-facing ToF on Huawei/Xiaomi smartphones uses iToF.

**Maximum Unambiguous Range (MUR)**
The maximum distance an iToF system can correctly measure without phase wrapping, given by $Z_{\max} = c / (2 f_{\text{mod}})$. Higher modulation frequency gives better range resolution but reduces MUR. Real systems often extend the unambiguous range through multi-frequency modulation or phase unwrapping.

**SPAD (Single-Photon Avalanche Diode)**
The core detector component in dToF: uses avalanche breakdown to detect the arrival time of individual photons, paired with a TDC (Time-to-Digital Converter) to achieve picosecond-level time resolution. SPAD array resolution is the key bottleneck limiting dToF imaging quality, and is rapidly advancing from hundreds of thousands of pixels toward the megapixel class.

**Structured Light**
Projects known encoded patterns (random speckle, fringe, Gray code, etc.) onto a scene; uses the deformation of the pattern on object surfaces to compute depth via triangulation. The TrueDepth camera in Apple Face ID uses a random speckle scheme, projecting more than 30,000 invisible infrared dots (Apple's official description: "more than 30,000 invisible dots"). Structured light achieves very high near-range accuracy (down to 0.1 mm) but is limited to indoor/close-range use; SNR degrades sharply under strong outdoor ambient light.

**Triangulation**
The depth recovery principle shared by stereo vision and structured light: using the angular difference (disparity $d$) of two observation points at known poses (two cameras, or camera + projector) viewing the same scene point, depth is recovered geometrically as $Z = f \cdot B / d$. Depth accuracy degrades as the square of distance ($\partial Z / \partial d = -Z^2 / fB$): high accuracy at close range, large errors at far range.

**Disparity**
In stereo vision, the horizontal pixel coordinate difference $d = u_L - u_R$ of the same scene point in the left and right images. Disparity is inversely proportional to depth ($Z = fB/d$): larger disparity means closer depth. The core challenge in computing disparity is stereo matching — finding corresponding pixel pairs in left and right images; textureless regions and occlusions are the main failure scenarios.

**Semi-Global Matching (SGM)**
The classic stereo matching algorithm proposed by Hirschmuller (2008), achieving the best balance between accuracy and computational efficiency. The core idea is to aggregate matching costs along 8 directions using one-dimensional dynamic programming, with penalty terms $P_1$ and $P_2$ constraining disparity smoothness, and a Winner-Take-All strategy to produce the final disparity map. OpenCV's `StereoSGBM` is a widely used implementation and forms a common algorithmic basis for smartphone bokeh depth maps.

**Multipath Interference (MPI)**
A systematic error unique to iToF systems: light reaches the sensor after multiple reflections and is superimposed, causing the measured phase to be a weighted mixture of multiple paths, resulting in underestimated depth. Most severe near glass, in corners, and on mirror-like metallic surfaces. Correction methods include multi-frequency ToF, sparse deconvolution, and end-to-end deep learning correction.

**Monocular Depth Estimation**
A deep learning method for estimating depth from a single RGB image. Because the same 2D image theoretically corresponds to infinitely many 3D configurations, the problem is fundamentally ill-posed; networks estimate depth through supervised (MiDaS, DPT) or self-supervised (Monodepth2, PackNet) learning by leveraging scene priors (object size patterns, perspective relationships, texture gradients). The core limitation is scale ambiguity — the output is relative depth and absolute scale cannot be directly determined.

**Pack/Unpack Operations (core modules in PackNet)**
Lossless down/upsampling operations proposed by Guizilini et al. (CVPR 2020): Pack rearranges a local spatial neighborhood ($r \times r$ region) of the feature map into the channel dimension (analogous to pixel_unshuffle), reducing resolution while preserving all spatial information; Unpack is the inverse for decoder upsampling. The operation is fundamentally a spatial-to-channel dimension rearrangement, not 3D convolution; the overall architecture remains 2D convolutional U-Net. Compared to traditional strided convolution or pooling, Pack avoids the loss of fine-grained spatial information during downsampling.

**Scale Ambiguity**
The fundamental limitation of monocular depth estimation: without an external scale reference, the depth network cannot determine absolute distance from a single image and can only output relative depth ratios. Solutions include: introducing reference objects of known size (ground plane, lane markings), fusing IMU data, and aligning with sparse LiDAR point clouds (depth completion).

**Depth Completion**
The task of fusing sparse depth measurements (sparse LiDAR point clouds, sparse ToF samples) with RGB images through a neural network to generate a dense depth map. RGB image texture and edge information guides depth propagation in unmeasured regions. Representative works include CSPN (Cheng et al., 2018) and PENet (Hu et al., 2021).

**Flying Pixels**
Artifact pixels at depth-discontinuous boundaries in depth maps, whose depth values lie between foreground and background; they appear as "floating" points in depth visualizations and cause background leakage halo artifacts along foreground silhouettes in bokeh applications. Caused by ToF pixels or stereo matching windows simultaneously covering foreground and background at boundaries. Mitigation methods include edge erosion and RGB-guided depth edge replacement.

**Joint Bilateral Filter (Cross Bilateral Filter)**
A filtering method that uses edge/texture information from a high-resolution RGB image as a guide to filter a low-resolution depth map. The precise edges in the RGB image guide the depth filter to avoid crossing true depth discontinuities, smoothing depth noise while preserving depth edges. It is one of the core operators in RGB-D fusion depth map post-processing.

**Depth Registration (Depth-RGB Alignment)**
Projecting the depth map generated by a depth sensor (ToF, structured light) into the RGB camera coordinate system via extrinsic parameters (rotation matrix $R$, translation vector $t$) to achieve pixel-level depth-color correspondence, which is a prerequisite for RGB-D fusion and 3D reconstruction. The calibration procedure jointly optimizes the intrinsic and extrinsic parameters of both sensors by minimizing reprojection error using a checkerboard calibration target.
