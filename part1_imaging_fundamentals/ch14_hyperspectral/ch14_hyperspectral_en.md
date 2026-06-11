# Part 1, Chapter 14: Hyperspectral Imaging

> **Pipeline position:** Specialized imaging system; beyond RGB three-channel sensing
> **Prerequisites:** Chapter 5 (Color Science), Chapter 3 (Sensor Physics)
> **Reader path:** Systems researchers, color engineers

---

## §1 Theory

### 1.1 Multispectral vs. Hyperspectral: Key Distinctions

Human color perception relies on three types of cone cells corresponding to three broad-band responses (L, M, S) — the physiological basis for the three-channel design of RGB cameras. However, the spectral information in the real world is far richer than three numbers: the reflected spectrum of a leaf has a steep "red-edge" jump near 700 nm, the hemoglobin absorption peak of tumor tissue at 540 nm differs sharply from normal tissue, and the characteristic absorption valley of a mineral can be pinpointed precisely at 2200 nm. A three-channel RGB system completely aliases these details; hyperspectral imaging exists precisely to recover the spectral dimension that has been compressed away.

**Multispectral** typically refers to 4 to 20 discrete bands with bandwidths on the order of 20–100 nm. Canonical examples include the 11 bands of the Landsat remote-sensing satellite and the 5-channel sensor (Blue, Green, Red, Red-Edge, NIR) commonly carried on agricultural UAVs. Each band corresponds to a broadband filter; acquisition efficiency is high, but spectral resolution is limited.

**Hyperspectral** pushes the band count to 100–1000, reduces the bandwidth to 1–10 nm, and provides continuous coverage of a spectral range, yielding true "spectral fingerprints." This fine resolution makes it possible to identify organic functional-group absorption features, quantify chlorophyll ratios in vegetation, and decouple melanin from hemoglobin in skin analysis.

The fundamental difference between the two lies in the trade-off between **spectral resolution** and **spatial resolution**. For a single detector array, acquiring N spectral channels means that each channel receives only 1/N of the photons in the same integration time, reducing the signal-to-noise ratio to $1/\sqrt{N}$; increasing the integration time reduces frame rate, or requires reducing spatial resolution. This is the core design constraint of hyperspectral systems, and the greatest challenge in transitioning from specialized instruments to consumer mobile devices.

**Common spectral ranges:**
- Visible (VIS): 400–700 nm, the range of human visual perception
- Near-infrared (NIR): 700–1100 nm, the extended response range of silicon-based sensors
- Short-wave infrared (SWIR): 1100–2500 nm, requires special detector materials such as InGaAs
- Mid-wave infrared (MWIR) / Long-wave infrared (LWIR): 3–14 μm, the thermal imaging domain (not covered in this chapter)

Consumer smartphone sensors currently operate primarily in the VIS and NIR ranges, while industrial and remote-sensing applications make extensive use of the full VNIR (400–1000 nm) and even SWIR ranges.

---

### 1.2 Types of Hyperspectral Sensors

The core challenge of hyperspectral sensing is **how to allocate sampling resources between the spatial dimensions (x, y) and the spectral dimension (λ)**; the essential differences between various technical approaches lie precisely here.

**(1) Pushbroom / Line Scanner**

Pushbroom is the dominant hyperspectral architecture in aerial and remote-sensing applications. The detector is a two-dimensional array: the horizontal axis corresponds to space (one row of pixels along the across-track direction), while the vertical axis is dispersed by a dispersive element (prism or grating) into the spectral dimension. As the platform (UAV or satellite) flies forward, it scans row by row to achieve two-dimensional spatial coverage, ultimately assembling a three-dimensional data cube (x, y, λ).

Representative products include Headwall Photonics' Photonics series (VIS-NIR, 270 bands, spatial resolution 1–5 cm at 100 m altitude), Specim's AFX10/AFX17 (designed specifically for UAVs), and HySpex (airborne hyperspectral systems from Norsk Elektro Optikk, Norway).

Advantages of pushbroom: high optical efficiency (full aperture utilization) and good SNR. Disadvantages: precise platform motion is required, sensitivity to vibration, and rapid full-frame imaging of stationary targets is not possible.

**(2) Snapshot / Mosaic Spectral Filter**

Analogous to the Bayer CFA (Color Filter Array) in an RGB camera, a snapshot hyperspectral sensor deposits a spectral mosaic filter pattern over the pixel array, allowing a complete spatial-spectral dataset to be acquired in a single exposure (after interpolation). A canonical example is the on-chip spectral sensor developed by imec (Belgium), which directly deposits 16 to 150 narrow-band thin-film interference filter units of different center wavelengths onto CMOS pixels (each filter unit is physically a Fabry-Pérot interferometric filter), forming an on-chip spectral filter mosaic array that completes acquisition in a single exposure.

The primary advantage of snapshot sensors is **no motion artifacts** (suitable for handheld or moving targets); they are also compact and highly integrated, making them suitable for embedding in consumer devices. The trade-off is that spatial resolution is affected by the spectral mosaic sampling (analogous to Bayer pattern spatial resolution loss), and spectral crosstalk exists between adjacent mosaic units.

**(3) Tunable Fabry-Pérot**

A Fabry-Pérot interferometer with a tunable cavity length is used as a narrowband filter, scanning wavelength by wavelength to complete spectral acquisition. Each scan captures the full image; the data cube is assembled in the time dimension. Advantages: simple optical structure, flexible band count configuration. Disadvantages: multiple exposures are required, unsuitable for dynamic scenes, and the stability of the MEMS-driven cavity length determines spectral accuracy.

Hamamatsu's (Germany) miniature spectrometer chip (C14384MA, etc.) uses this principle and has been integrated into industrial inspection equipment and some research-grade handheld instruments.

**(4) Computational Spectral Imaging**

By using a coded aperture or random spectral encoding, spectral information is aliased and encoded into a small number of image frames using compressed sensing, then recovered as a complete spectral data cube using sparse reconstruction algorithms (such as ADMM or deep unfolding networks). Representative systems include CASSI (Coded Aperture Snapshot Spectral Imager) and its derivatives.

The advantage of computational imaging is that hyperspectral data can be obtained at a hardware cost approaching that of a 2D camera, making it suitable for scenarios with strict constraints on size and power consumption. The drawbacks are that reconstruction quality depends on the algorithm, computational complexity is high, and robustness on real complex scenes is still under investigation.

---

### 1.3 Smartphone Multispectral Sensors

The multispectral capabilities of consumer mobile devices are rapidly evolving, from initial NIR anti-spoofing auxiliary sensors toward genuine multispectral analysis capability.

**Sony IMX Series and Multispectral Sensor Evolution**

The Sony IMX686 is a 64-megapixel stacked CMOS image sensor using a standard RGGB Bayer array; it does not have multispectral hardware channels. Sony's exploration of multispectral sensors is reflected in other dedicated product lines, such as multispectral sensor solutions targeting industrial and life-sciences markets, which achieve multi-channel perception by overlaying on-chip interference filter mosaics on top of the pixel layer. The typical consumer-grade multispectral sensor approach is to sparsely distribute a small number of narrow-band sensing units (e.g., Violet, Cyan, Red-Edge, NIR) alongside the standard RGB channels, primarily for assisting AWB accuracy (avoiding metamerism), skin tone analysis, and scene illuminant identification, rather than serving as standalone hyperspectral imaging.

**Qualcomm Spectra Multispectral Engine**

The Qualcomm Spectra ISP (integrated in the Snapdragon 8 Gen series) specifically adds multispectral signal processing channels, supporting data fusion with external spectral sensors. Typical applications include: skin health assessment (melanin index, erythema index calculation) combined with UV/NIR auxiliary sensors, and vegetation health index (NDVI) computation based on reflected spectral data.

**Application-Driven Multispectral Features in Smartphones**

- **Skin analysis and beauty:** The difference in reflectance at 630 nm (oxyhemoglobin) and 760 nm (deoxyhemoglobin) is used to estimate skin blood flow; the absorption feature at 540 nm is used to assess melanin content. Such features have appeared in some high-end beauty devices and are expected to be integrated into smartphones.
- **Plant health monitoring:** The NIR/Red ratio (NDVI index) reflects chlorophyll content; consumer smartphones can already implement a simplified NDVI estimate in software by combining NIR auxiliary cameras.
- **Food inspection:** The NIR range (900–1700 nm) contains characteristic absorption peaks of hydrocarbons, proteins, and moisture, making it theoretically suitable for food freshness assessment, though limited by the NIR cut-off filter in smartphone sensors.
- **AR material recognition:** Different materials (metal, plastic, fabric, skin) have unique reflectance signatures in the multispectral domain, which can assist material classification and rendering in AR scenes.
- **Precise AWB/CCM:** Conventional RGB metering cannot distinguish between metameric illuminants; multispectral sensing can significantly improve white balance accuracy under complex illuminants (see Chapter 11 on metamerism for details).

---

### 1.4 Hyperspectral Data Processing Pipeline

The hyperspectral processing pipeline differs fundamentally from RGB ISP; the core distinction is that it operates on a **three-dimensional data cube** (x, y, λ) rather than a two-dimensional image.

**(1) Spectral Calibration**

Raw sensor output must undergo wavelength registration (mapping each channel to its precise center wavelength) and spectral response function (SRF) correction (converting DN values to radiance or reflectance). This is typically accomplished using a monochromator scanning through the wavelength range, or a standard illuminant with a known spectrum.

**(2) Non-Uniformity Correction (NUC)**

Each column of detector elements in a pushbroom sensor has gain and offset variations (spatial non-uniformity); additionally, different spectral channels differ in relative sensitivity (spectral non-uniformity). The standard approach is to capture dark-field and bright-field images under uniform integrating-sphere illumination, then compute gain-offset correction coefficients channel by channel.

**(3) Atmospheric Correction**

For remote-sensing applications, the radiation received by the sensor includes atmospheric scattering and absorption components, which must be converted to surface reflectance. Common methods include FLAASH (based on the MODTRAN radiative transfer model) and the 6S model. For near-field (low-altitude UAV, indoor) applications, empirical correction using a white reference target is typically used directly.

**(4) Spectral Unmixing**

Due to the presence of mixed pixels (especially in remote sensing), the spectrum of a single pixel is a linear or nonlinear mixture of multiple endmembers. Linear unmixing expresses the pixel spectrum **y** as:
```
y = A × s + noise
```
where A is the endmember matrix (N×K, N bands, K endmembers) and s is the abundance vector (subject to non-negativity and sum-to-one constraints). Typical algorithms include Fully Constrained Least Squares (FCLS) and Sparse Unmixing by Variable Splitting and Augmented Lagrangian (SUnSAL).

**(5) Band Selection and Dimensionality Reduction**

Among 100+ bands there is substantial redundancy. Principal Component Analysis (PCA), Linear Discriminant Analysis (LDA), and Minimum Noise Fraction (MNF) can compress the data to 10–20 principal components, dramatically reducing downstream computation while retaining discriminant information.

**(6) Classification and Target Detection**

Standard methods for hyperspectral classification range from traditional SVM-based spectral classification, to spatial-spectral joint convolutional neural networks (3D-CNN, Hybrid CNN), to recent Transformer architectures (SpectralFormer). Classification accuracy is typically measured by Overall Accuracy (OA) and the Kappa coefficient.

Comparison with RGB ISP: RGB ISP demosaicing is essentially spatial interpolation; hyperspectral spectral demosaicing is interpolation in the spectral dimension — the principles are analogous, but the exploitation of spectral correlation differs. RGB ISP processes two-dimensional signals; hyperspectral processing operates on three-dimensional data cubes, with substantially higher memory and compute requirements.

---

### 1.5 Relationship Between Hyperspectral and RGB

**Dimensionality Reduction from Hyperspectral to RGB (Forward Problem)**

The RGB response of a camera can be viewed as a weighted integral of hyperspectral data along the spectral dimension:

```
R = ∫ I(λ) · r(λ) dλ ≈ M_R · s
G = ∫ I(λ) · g(λ) dλ ≈ M_G · s
B = ∫ I(λ) · b(λ) dλ ≈ M_B · s
```

where I(λ) is the incident spectrum, r(λ)/g(λ)/b(λ) are the camera's spectral response functions (SRFs), and s is the discretized spectral vector. In matrix form:

```
RGB = M × s
```

M is a 3×N matrix (3 channels, N bands). This transformation is lossy: N-dimensional spectral information is compressed to 3-dimensional color values, and extensive spectral detail is irreversibly lost.

**Inversion from RGB to Hyperspectral (Inverse Problem)**

This is a severely underdetermined problem: estimating N unknowns (N >> 3) from 3 known values. Prior constraints must be introduced:
- **Statistical prior:** Exploit the low-dimensional manifold structure of natural spectra; solve in a low-dimensional space after PCA reduction.
- **Sparsity prior:** Natural spectra can be sparsely represented by a small number of basis functions.
- **Deep learning prior:** End-to-end trained spectral super-resolution networks.

Representative deep learning methods:
- **HSCNN (Hyperspectral Super-resolution CNN):** The first work to apply CNN to RGB-to-hyperspectral reconstruction; established the baseline at the NTIRE Spectral Super-Resolution Challenge.
- **SSRNet (Spectral Super-Resolution Network):** Uses non-local attention mechanisms to capture long-range spectral correlations; achieves MRAE of approximately 2–3% on the ICVL dataset.
- **MST++ (Multi-stage Spectral-wise Transformer):** Transformer-based per-spectrum attention; winner of the NTIRE 2022 Spectral Reconstruction from RGB Challenge.

This class of techniques is commonly referred to in practice as **spectral upsampling**, which can provide approximate spectral estimates for devices without hyperspectral hardware, useful for improving color rendering accuracy (e.g., spectral rendering in CG) and for precise CCM computation.

---

### 1.6 Applications

**Precision Agriculture Remote Sensing**

The Normalized Difference Vegetation Index (NDVI = (NIR - Red) / (NIR + Red)) is the most widely used vegetation health indicator, requiring only red and near-infrared bands. Hyperspectral further enables computation of chlorophyll content (based on absorption features at 550 nm and 680 nm), leaf water content (based on water absorption peaks at 970 nm and 1450 nm), and nitrogen content (based on features at 1510 nm and 1680 nm), enabling precision fertilization and early disease warning.

**Medical Imaging**

Intraoperative **fluorescence hyperspectral imaging** can display tumor boundaries in real time (based on emission spectra of targeted fluorescent dyes); **oxygen saturation imaging** uses the absorption differences of HbO₂ and Hb near 540 nm / 580 nm / 630 nm for non-invasive assessment of tissue perfusion; **dermatological diagnosis** with multispectral dermoscopes (such as SIAscope) can distinguish the spatial distributions of melanin, collagen, and hemoglobin, assisting in early melanoma diagnosis.

**Remote Sensing Mineral Mapping**

The SWIR range (1000–2500 nm) contains the characteristic hydroxyl (OH-) absorption peaks of numerous minerals. NASA's AVIRIS sensor, with 224 bands in this range, has made automated mapping of copper porphyry alteration zones and hydrothermal mineralization areas a reality, bringing a revolutionary improvement in mineral exploration efficiency.

**Industrial Quality Inspection**

Food foreign-body detection (glass fragments have different NIR spectra from food), pharmaceutical tablet coating uniformity inspection (hyperspectral imaging of API distribution), and print ink authentication (differences in NIR absorption between inks expose counterfeits).

**Consumer Skin Analysis**

High-end beauty devices (such as HiMirror and Neutrogena Skin360) have already integrated multispectral LED arrays to analyze pore size, wrinkles, pigmentation spots, and vascular visibility from skin reflectance images captured under different wavelength illumination. As the cost of on-chip spectral filters from companies such as imec continues to decline, the integration of such functionality into smartphones is a relatively clear trend.

---

## §2 Calibration

### 2.1 Spectral Response Function (SRF) Calibration

**Calibration objective:** Determine the center wavelength λ_c, full width at half maximum (FWHM), and peak response of each spectral channel of the sensor, establishing the conversion relationship from DN values to radiance (or reflectance).

**Standard procedure:**

1. **Monochromator scanning:** A tunable monochromator outputs narrow-band light at a known wavelength (accuracy ±0.1 nm), which illuminates a uniform diffuse reflectance target (Spectralon white panel). The full spectral range is scanned step by step (e.g., 400–1000 nm, 1 nm step size), recording the response curve of each sensor channel. This method achieves the highest accuracy and is the instrument-grade standard.

2. **LED matrix method:** Multiple narrow-band LEDs at known peak wavelengths (FWHM < 15 nm) are used; the SRF is reconstructed by linear interpolation. Lower cost, suitable for batch production-line calibration; accuracy is slightly below the monochromator method (wavelength error approximately ±2–3 nm).

3. **Outdoor calibration using natural spectra:** Known-spectrum standard targets (such as a Macbeth ColorChecker combined with spectrophotometer measurements) are used in natural daylight; the equivalent SRF is solved via simultaneous equations. Suitable for field calibration of consumer devices that cannot be disassembled, but accuracy is affected by environmental illuminant stability.

**Special note:** In a pushbroom sensor, the SRF of each column of detector elements may differ, requiring **per-column calibration** that produces an SRF data cube.

---

### 2.2 Non-Uniformity Correction (Spatial + Spectral)

**Spatial non-uniformity** arises from manufacturing variation in detector elements, manifesting as uneven dark current and Photo Response Non-Uniformity (PRNU).

**Two-Point Correction** is the most widely used method:
- Capture uniform images at low illumination (dark field, DN_dark) and high illumination (bright field, DN_bright)
- Correction formula: `DN_corrected = (DN_raw - DN_dark) / (DN_bright - DN_dark) × K`
- where K is the target normalization coefficient (e.g., full-scale value)

**Spectral non-uniformity** refers to differences in relative sensitivity between spectral channels at the same spatial location, and is similarly eliminated by per-channel gain correction under uniform integrating-sphere illumination.

Pushbroom systems also require attention to **stripe noise**: because each column of detector elements is read out at different time intervals, platform vibration and illumination instability introduce systematic column-to-column offsets. Destriping algorithms typically operate in the frequency domain (FFT along the flight direction, filtering out horizontal frequency components) or via moment correction (moment matching).

---

### 2.3 White Reference Correction Under Standard Illumination

For reflectance measurements, **relative correction** is typically used:
```
Reflectance = (DN_target - DN_dark) / (DN_white - DN_dark)
```
where DN_white is the signal from a Spectralon white panel (nominal reflectance >99%) under the same illumination conditions.

White reference correction requires stable illumination. For pushbroom systems, the white reference must be acquired in the same flight strip as the target, or an **in-flight solar reference mirror** is used for real-time referencing. White balance in mobile devices is essentially a simplified white reference correction for RGB channels; multispectral devices must perform spectral white balancing independently across all N channels.

---

## §3 Tuning

### 3.1 Spectral Resolution vs. SNR Trade-off

There is a fundamental **etendue–noise trade-off** between spectral resolution (FWHM) and signal-to-noise ratio (SNR):

- Halving the FWHM → halves the photon count per channel → SNR decreases by $\sqrt{2}$ (when shot noise dominates)
- A typical hyperspectral system (10 nm FWHM, 1000 µs integration time) achieves an SNR of approximately 200–500:1, significantly lower than the >1000:1 of an RGB system

Tuning strategies:
1. **Band binning:** For bands outside the region of interest, average 2–4 adjacent bands to find the application-optimal point between spectral resolution and SNR. For example, chlorophyll analysis requires 5 nm precision near 680 nm, while the 800–900 nm region can tolerate 20 nm.
2. **Adaptive integration time:** For mobile snapshot sensors, the integration time can be increased for dark scenes (at the cost of reduced frame rate) or gain can be increased (at the cost of relatively larger read noise).
3. **Optimal band selection:** For specific applications (e.g., skin analysis requiring only 6–8 key bands), select the optimal subset through band importance analysis and discard redundant bands, achieving near-full-band performance under constrained computational resources.

---

### 3.2 Fusion Strategies with RGB Channels

Consumer-grade multispectral sensors typically have low-resolution multispectral channels (auxiliary sensor, spatial resolution 1/4 to 1/16 of the main RGB camera) and high-resolution RGB channels, necessitating **spatial-spectral fusion**:

- **Guided upsampling:** The RGB image is used as a guide, and its spatial high-frequency information is used to improve the spatial resolution of multispectral channels (analogous to RGB-guided depth map super-resolution). Joint Bilateral Upsampling (JBU) is the classical method; deep learning approaches include DSen2 and HighRes-net.
- **Color-guided spectral refinement:** RGB and multispectral images share similar spatial structure (homogeneous regions, edge positions); joint regularization can combine the spectral accuracy of multispectral with the spatial sharpness of RGB.
- **AWB assistance:** Multispectral channels directly provide illuminant spectral estimation without relying on RGB color statistics, reducing AWB color temperature error from 200–300 K to 50–100 K.

---

### 3.3 Application-Adaptive Band Selection

The spectral requirements differ enormously across applications. Using all channels uniformly wastes computational resources and may introduce interference from irrelevant bands.

**Band selection methods:**
- **Information criteria:** Maximize mutual information (MI) of the selected subset or minimize redundancy via Maximum Relevance Minimum Redundancy (mRMR)
- **Recursive Feature Elimination (RFE):** Iteratively remove the least important bands based on feature weights from SVM or random forest classifiers
- **Attention mechanisms:** Use channel attention modules (SE-Net, CBAM) in end-to-end training to automatically learn band weights

Practical tuning recommendation: before device shipment, optimize the band combination for the target application scenario (e.g., skin analysis, vegetation detection, food inspection), and fix the result as a device-specific "Spectral Profile." On the device, run only the selected key channel subset in low-power mode.

---

## §4 Artifacts

### 4.1 Spectral Aliasing

When the SRFs of adjacent spectral channels overlap excessively (FWHM > channel spacing), the signal in a single channel contains spectral leakage from adjacent channels, causing distortion of the spectral curve (shifted feature peak positions, reduced peak heights).

**Sources:**
- Insufficient suppression of sidelobes in snapshot sensor interference filters
- Stray light in the optical system mixing broadband light into narrow-band channels
- Optical crosstalk between mosaic units

**Suppression methods:**
- Design stage: improve the rectangular factor of interference filters (roll-off slope), targeting a rectangular factor > 0.8
- Correction stage: construct a channel-to-channel crosstalk matrix C (C_ij represents the proportion of channel j leaking into channel i), then correct via matrix inversion or regularized least squares

---

### 4.2 Stripe Noise (Pushbroom Scan Non-Uniformity)

The most characteristic artifact of pushbroom systems: vertical stripes along the flight direction in the image (each column of pixels corresponds to a fixed detector element whose gain offset accumulates into visible stripes).

**Causes:**
1. Incomplete correction of detector element gain/offset differences (PRNU/DSNU)
2. Temperature variation during flight causing detector operating-point drift
3. Vibration causing instantaneous response non-uniformity

**Removal algorithms:**
- **Moment matching:** Force all columns to have equal mean and standard deviation (assuming image row statistics should be uniform)
- **Frequency-domain filtering:** Stripes appear as horizontal lines in the Fourier domain (periodic signal along the column direction); notch filters remove the corresponding frequency components
- **Variational destriping:** Model stripes as additive low-frequency noise; use TV regularization to separate them from the true spatial variation of the scene

---

### 4.3 Atmospheric Absorption Band Interference

The Earth's atmosphere has strong absorption at specific wavelengths (primarily due to H₂O, O₂, CO₂, and O₃):
- 940 nm and 1140 nm: strong water vapor absorption bands
- 762 nm: O₂-A absorption band
- 1380 nm, 1900 nm: strong water vapor absorption bands (SWIR)

The sensor signal in these bands is extremely low (SNR < 10) and cannot reflect the true surface reflectance. These bands must be **masked** in hyperspectral data analysis and excluded from classification and spectral matching calculations.

For near-field (indoor, low-altitude UAV) applications, the atmospheric path is short (< 100 m), and the effect is negligible. In spaceborne remote sensing (path > 10 km), it must be precisely removed using an atmospheric correction model.

---

## §5 Evaluation

### 5.1 Spectral Accuracy (RMSE, Spectral Angle)

**Root Mean Square Error (RMSE)** measures the band-by-band absolute error between reconstructed and reference spectra:
```
RMSE = sqrt( (1/N) × Σ (s_pred(λ_i) - s_ref(λ_i))^2 )
```
Units are the same as the reflectance dimension (0–1); a high-quality reconstruction typically achieves RMSE < 0.01 (i.e., < 1%).

**Spectral Angle Mapper (SAM)** measures the angle between two spectral vectors, insensitive to brightness scale and focused on spectral shape similarity:
```
SAM = arccos( (s_pred · s_ref) / (||s_pred|| × ||s_ref||) )
```
Units are radians or degrees. As an empirical reference: < 0.05 rad generally indicates reasonably consistent spectral shape; > 0.1 rad often indicates a non-negligible difference. However, these two values are only empirical references, not universal standards — the acceptable threshold for a specific application should be determined by task type, sensor characteristics, data preprocessing pipeline, and the reference spectral library, and should not be compared directly across different publications. SAM is the core similarity measure for judging material match in hyperspectral classification.

**Mean Relative Absolute Error (MRAE):**
```
MRAE = (1/N) × Σ |s_pred(λ_i) - s_ref(λ_i)| / s_ref(λ_i)
```
Used to evaluate spectral super-resolution networks; the evaluation standard of the NTIRE Challenge.

---

### 5.2 Comparison with Reference Spectrometers

The absolute accuracy of hyperspectral sensors is validated by comparison with laboratory-grade spectrophotometers or spectroradiometers (such as PerkinElmer Lambda 1050, ASD FieldSpec 4):

1. Acquire measurements of the same known-spectrum target (e.g., Macbeth ColorChecker 24-patch, Spectralon white panel, specific chemical samples) under the same illumination conditions
2. Compute the systematic error (bias) and random error (RMSE) for each band
3. Verify wavelength registration accuracy (peak wavelength error should be < 1 nm)

For mobile multispectral sensors with few bands (< 20), comparison is typically made against handheld spectrometers (such as Nix Color Sensor, SCiO); achieving reflectance error < 5% at 10–15 key wavelengths is considered acceptable.

---

### 5.3 Downstream Task Classification Accuracy

Spectral accuracy is an intermediate metric; final evaluation should be based on downstream task performance:

**Remote sensing classification** (benchmarked on standard datasets such as Indian Pines, Pavia University):
- Overall Accuracy (OA): target > 90%
- Kappa coefficient: target > 0.88
- Average Accuracy (AA) per class

**Food inspection:** False Positive Rate (FPR) and False Negative Rate (FNR)
**Skin analysis:** Agreement with dermatologist diagnoses (Cohen's Kappa)
**Vegetation monitoring:** Correlation coefficient (R²) between vegetation indices such as NDVI and ground-truth measurements (target > 0.9)

**Speed / Power evaluation:** For embedded deployment, processing latency (ms/frame), power consumption (mW), and memory footprint (MB) must also be evaluated to ensure real-time requirements on mobile devices are met.

---

## §6 Code

See the companion notebook: *See §6 Code section for runnable examples.*

The notebook contains the following demonstrations:
1. Simulated hyperspectral data cube generation (based on the CAVE dataset or synthetic spectra)
2. Simulation of stripe noise in pushbroom sensors and destriping
3. PCA-based hyperspectral dimensionality reduction and visualization (false-color composite)
4. Linear spectral unmixing (FCLS algorithm)
5. Spectral upsampling from RGB to hyperspectral (based on a simplified HSCNN)
6. NDVI computation and vegetation health map generation
7. SAM spectral angle evaluation implementation

---

## References

1. **Bioucas-Dias, J. M., et al.** (2012). *Hyperspectral Unmixing Overview: Geometrical, Statistical, and Sparse Regression-Based Approaches*. IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing, 5(2), 354–379. — Authoritative survey of the hyperspectral unmixing field, covering geometric, statistical, and sparse approaches.

2. **Gevaert, C. M., et al.** (2015). *Combining UAV-based hyperspectral imagery and machine learning for high-resolution forest mapping*. Remote Sensing, 7(11), 14405–14430. — Systematic study of UAV multispectral/hyperspectral sensing in precision agriculture and forest mapping.

3. **Yokoya, N., Grohnfeldt, C., & Chanussot, J.** (2017). *Hyperspectral and multispectral data fusion: A comparative review of the recent literature*. IEEE Geoscience and Remote Sensing Magazine, 5(2), 29–56. — Comprehensive comparison of spatial-spectral fusion methods, covering matrix factorization, Bayesian methods, and deep learning.

4. **Sony Semiconductor Solutions** (2023). *Stacked CMOS Image Sensor Technology and Multispectral Sensing Direction*. Sony Semiconductor Solutions Corporation Technical Report. — Reference for Sony's multispectral sensor technology roadmap (note: the IMX686 is a standard 64MP RGB Bayer sensor; multispectral solutions are reflected in Sony's industrial and dedicated product lines).

5. **Imec** (2023). *Snapshot Hyperspectral Imaging Solutions: On-chip Spectral Filters for Industrial and Consumer Applications*. imec Technical Report. — Implementation principles and performance specifications of snapshot on-chip spectral filters, representing the frontier of consumer-end hyperspectral mass production.

---

*Key terms: hyperspectral imaging, multispectral, spectral unmixing, pushbroom sensor, snapshot spectral sensor, spectral angle mapper (SAM), NDVI, spectral super-resolution, non-uniformity correction, stripe noise*

---

## §8 Glossary

**Hyperspectral Imaging**
An imaging technique that acquires 100–1000 extremely narrow bands (typical FWHM 1–10 nm) over a continuous spectral range, outputting a three-dimensional data cube (x, y, λ). The fundamental difference from multispectral (4–20 broadband channels) lies in spectral resolution: hyperspectral can capture "spectral fingerprints," resolving organic functional-group absorption features, vegetation pigment ratios, and other fine spectral differences that are indistinguishable by RGB. The trade-off is that each channel receives only 1/N of the photons of the full band, so SNR is significantly lower than an RGB camera.

**Multispectral**
An imaging technique that acquires 4–20 discrete broadband bands (typical FWHM 20–100 nm), positioned between RGB (3 channels) and hyperspectral (100+ channels). Canonical examples are the 11 bands of the Landsat remote-sensing satellite and the 5-channel agricultural UAV sensor (Blue/Green/Red/Red-Edge/NIR). Low band count, high acquisition efficiency, suitable for scenarios requiring more information than RGB but without the need for high spectral resolution.

**Pushbroom Scanner / Line Scanner**
The dominant hyperspectral architecture in aerial and remote-sensing applications: a two-dimensional detector array whose horizontal axis corresponds to the spatial direction (one row of pixels) and whose vertical axis is dispersed by a prism/grating into the spectral dimension; the platform moves forward and scans row by row, assembling a three-dimensional data cube. High optical efficiency and good SNR, but requires precise platform motion, is sensitive to vibration, and cannot rapidly capture full-frame images of stationary targets.

**Snapshot Spectral Sensor**
A spectral mosaic filter array (analogous to the Bayer CFA for RGB) deposited over the CMOS pixel array, allowing spatial-spectral data to be acquired in a single exposure without platform motion. imec's on-chip spectral sensor is the representative example: narrow-band thin-film interference filter units (physically Fabry-Pérot interferometric filters) are deposited on CMOS pixels to form an on-chip spectral filter mosaic array achieving 16–150-band snapshot acquisition. Advantages: no motion artifacts, compact; trade-offs: spatial resolution is affected by mosaic sampling, and spectral crosstalk exists between adjacent channels.

**Fabry-Pérot Interferometric Filter**
An optical element that achieves spectral selection through multi-beam interference between two parallel reflective surfaces: only wavelengths satisfying the cavity-length resonance condition transmit with high efficiency; all other wavelengths are suppressed by reflection, producing a narrow bandpass response. Each filter unit in imec's on-chip spectral sensor is based on this principle — the center wavelength is set by controlling the thin-film cavity length (deposition thickness); a tunable Fabry-Pérot (MEMS-driven cavity) supports wavelength-by-wavelength scanning.

**Spectral Response Function (SRF)**
A curve describing the response intensity of each spectral channel of the sensor to incident light at different wavelengths, parameterized by center wavelength λ_c and FWHM. The SRF is the calibration basis for converting DN values to radiance/reflectance, and must be precisely calibrated using a monochromator scan or LED matrix method. In a pushbroom sensor, the SRF of each column of detector elements may differ, requiring per-column calibration.

**Non-Uniformity Correction (NUC)**
A correction procedure to eliminate differences in gain (PRNU) and offset (DSNU) between pixels in the detector array. The standard method is Two-Point Correction: dark-field (low illumination) and bright-field (uniform integrating-sphere illumination) images are captured; gain and offset correction coefficients are computed per pixel to normalize all pixels to a unified response baseline. Hyperspectral sensors require, in addition to spatial non-uniformity correction, spectral non-uniformity correction (per-channel gain differences).

**Spectral Unmixing**
The process of decomposing the spectrum of a mixed pixel into its constituent endmembers (pure material spectra) and their abundances (mixing proportions). Linear mixing model: $\mathbf{y} = A\mathbf{s} + \mathbf{n}$, where $A$ is the endmember matrix and $\mathbf{s}$ is the abundance vector (subject to non-negativity and normalization constraints). Typical algorithms include Fully Constrained Least Squares (FCLS) and SUnSAL. Mixed pixels are ubiquitous in remote-sensing scenes; unmixing is the key step for extracting the precise composition of surface materials.

**Spectral Angle Mapper (SAM)**
A measure of the shape similarity between two spectral vectors, computed as the angle between them: $\text{SAM} = \arccos\!\left(\frac{\mathbf{s}_1 \cdot \mathbf{s}_2}{\|\mathbf{s}_1\|\|\mathbf{s}_2\|}\right)$. SAM is insensitive to brightness scale changes (differences in illumination intensity) and reflects only spectral shape differences, making it suitable for material matching across different illumination conditions. A smaller SAM value indicates greater similarity; it is the standard similarity measure in hyperspectral classification and target detection. The discrimination threshold should be determined based on the task and data conditions; there is no universal fixed standard.

**Normalized Difference Vegetation Index (NDVI)**
$\text{NDVI} = (\text{NIR} - \text{Red}) / (\text{NIR} + \text{Red})$, which quantifies vegetation health by exploiting the strong absorption of chlorophyll in red light (~660 nm) and high reflectance in the near-infrared (~780–900 nm). NDVI values range from -1 to +1; healthy dense vegetation approximately 0.6–0.9, sparse vegetation approximately 0.2–0.4, bare soil/water near 0 or negative. The most widely used vegetation health indicator in agricultural remote sensing and precision agriculture; requires only red and near-infrared bands.

**Spectral Super-Resolution / Spectral Upsampling**
The inverse problem of recovering a hyperspectral data cube from low-spectral-resolution input (such as RGB three channels). This problem is severely underdetermined (estimating N >> 3 unknowns from 3 knowns) and requires spectral statistical priors (PCA low-dimensional manifold, sparse basis) or end-to-end deep learning priors. Representative methods: HSCNN (first to apply CNN to RGB-to-hyperspectral reconstruction), SSRNet (non-local attention mechanism), MST++ (winner of NTIRE 2022 Spectral Reconstruction from RGB Challenge, based on per-spectrum attention Transformer). In practice, provides approximate spectral estimates for devices without hyperspectral hardware, useful for precise color rendering and CCM computation.

**Mean Relative Absolute Error (MRAE)**
The standard evaluation metric for spectral super-resolution reconstruction accuracy: $\text{MRAE} = \frac{1}{N} \sum_i |s_\text{pred}(\lambda_i) - s_\text{ref}(\lambda_i)| / s_\text{ref}(\lambda_i)$. MRAE averages the relative error across bands, eliminating the influence of absolute reflectance magnitude differences between bands. It is the official evaluation standard of the NTIRE Spectral Super-Resolution Challenge.

**Hyperspectral Data Cube**
The core data structure of hyperspectral imaging: a three-dimensional array $(x, y, \lambda)$ where $x/y$ are spatial dimensions and $\lambda$ is the spectral dimension. A typical remote-sensing hyperspectral data cube (1000×1000 spatial pixels, 200 bands, 16-bit) is approximately 400 MB; a single-frame snapshot sensor data cube (512×512, 32 bands) is approximately 16 MB. Processing complexity is far higher than for two-dimensional RGB images.

**Stripe Noise / Banding**
The most characteristic artifact of pushbroom hyperspectral sensors: periodic vertical stripes along the flight direction, caused by incomplete correction of per-column detector element gain/offset differences (PRNU/DSNU) or operating-point drift from temperature changes. Removal methods include moment matching (forcing all column statistics to be equal), frequency-domain notch filtering (eliminating column-periodic signals in the FFT domain), and variational destriping (TV regularization to separate stripes from true scene spatial variation).

**Atmospheric Correction**
A key step in remote-sensing hyperspectral processing: converting the sensor-received radiance (which includes atmospheric scattering and absorption components) to true surface reflectance. Common methods: FLAASH (based on the MODTRAN radiative transfer model), 6S model. The atmosphere has strong absorption at 940 nm and 1140 nm (water vapor), 762 nm (O₂-A), and other bands; SNR at these bands is extremely low, and they are typically masked in data analysis. Near-field applications (low-altitude UAV, indoor) can use white-panel relative correction as a substitute for atmospheric physical models.

**Spatial-Spectral Fusion**
A technique that fuses low-spatial-resolution multispectral/hyperspectral data with high-spatial-resolution panchromatic/RGB data to simultaneously improve both spatial resolution and spectral channel count. Typical methods include matrix factorization (MNF-based), Bayesian fusion, and deep-learning guided upsampling. For the multispectral-RGB fusion scenario in consumer smartphones, Joint Bilateral Upsampling (JBU) is the classical algorithm, while deep learning approaches such as DSen2 achieve higher accuracy.
