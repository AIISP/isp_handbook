# Part 1, Chapter 15: Lensless Imaging

> **Pipeline position:** Imaging system level; replaces the conventional lens + sensor combination
> **Prerequisites:** Chapter 2 (Optics Basics), Chapter 3 (Sensor Physics)
> **Reader path:** Systems researchers, algorithm engineers

---

## Chapter Overview

Lensless imaging is an imaging paradigm that fundamentally overturns the architecture of the traditional camera. Conventional cameras rely on refractive lenses to focus a scene onto a sensor; lensless cameras remove the lens entirely, replacing it with a carefully designed encoding element — such as a random diffuser, a phase mask, or a Fresnel zone plate — placed very close to the sensor. A computational algorithm then reconstructs an image from the encoded measurements captured by the sensor.

The appeal of this approach is that **the optical system can be made extremely thin, extremely light, and extremely low-cost**. When the lens stack is replaced by a thin film — or even a nanostructured layer printed directly onto the sensor cover glass — the Z-axis thickness of the entire camera module can be compressed from the millimeter scale down to the micrometer scale. This has enormous significance for wearable devices, medical endoscopes, smart capsules, patch-based vital-sign monitors, and similar applications.

The price, however, is clear: the raw data captured by the sensor is no longer a directly viewable image but an optically encoded "scrambled" measurement that requires complex computational reconstruction before a usable image can be recovered. This makes a lensless camera fundamentally a **co-designed optical-computational system** — the algorithm engineer's work shifts from the conventional ISP's post-processing optimization to reconstruction algorithm design that is deeply coupled with the underlying optics.

---

## §1 Theory

### 1.1 Motivation and Applications of Lensless Imaging

To understand why lensless imaging is worth studying, it helps first to appreciate the cost of conventional lenses. A standard smartphone lens module is approximately 5–7 mm thick; this dimension is primarily dictated by the focal length of the lens stack and the required back focal distance — light needs sufficient travel distance to be focused onto the focal plane. For consumer smartphones, these 5–7 mm already represent the outcome of repeated negotiations between engineers and product designers. For certain applications, however, even this dimension is too large:

- **Medical endoscopes and capsule endoscopes:** Capsules must pass freely through the esophagus and small intestine, with diameter strictly constrained. A lensless camera can fit the entire imaging head within a 1–2 mm diameter.
- **Wearable and patch devices:** Skin-patch blood oxygen and heart rate monitors must be flat and flexible, with thickness measured in micrometers — a conventional lens cannot be accommodated at all.
- **Smart micro-robots and drones:** In payload-constrained scenarios, camera weight and volume are key constraints.
- **Computational imaging research:** The lensless architecture naturally supports single-shot 3D reconstruction, super-resolution, spectral imaging, and other extended capabilities, making it an important research platform in computational imaging.
- **Industrial and security applications:** The ultra-thin form factor allows cameras to be concealed inside equipment or on structural surfaces such as walls or shelves.

Representative current systems include DiffuserCam (UC Berkeley, 2018), PhlatCam (Rice University, 2020), FlatScope (Rice University, on-chip fluorescence microscopy), and various flat-camera prototypes based on metasurfaces.

### 1.2 Phase Mask / Diffuser Encoding

The most representative implementation of lensless imaging is **phase mask / diffuser coding**. The core idea is as follows:

**Forward imaging model:**

Consider a point source in the scene located at three-dimensional coordinates $(x_0, y_0, z_0)$. It propagates through free space to the sensor plane, passing through a fixed phase mask along the way. Because the phase mask imposes different phase delays on the optical wavefront at different locations, the response of the point source on the sensor is no longer a small spot (Airy disk) but instead an **extended pattern with a unique spatial structure** — this is the **point spread function (PSF)** for that source position.

The sensor measurement $\mathbf{y}$ for an entire scene can be written as:

$$\mathbf{y} = \mathbf{H}\mathbf{x} + \mathbf{n}$$

where:
- $\mathbf{x} \in \mathbb{R}^N$ is the scene to be recovered (flattened into a vector)
- $\mathbf{H} \in \mathbb{R}^{M \times N}$ is the system matrix, formed by the PSF
- $\mathbf{n}$ is sensor noise
- $\mathbf{y} \in \mathbb{R}^M$ is the sensor readout

For a space-invariant system (i.e., the PSF is independent of scene position — a practical approximation), $\mathbf{H}$ has a convolutional structure, giving $\mathbf{y} = h * \mathbf{x} + \mathbf{n}$, which can be computed efficiently via the fast Fourier transform (FFT).

**DiffuserCam architecture (Antipa et al., 2018):**

DiffuserCam is a landmark work in lensless imaging. Its physical structure is remarkably simple: a commercial optical diffuser (cost approximately a few dollars) is placed directly above the CMOS sensor at a distance of roughly 1 mm, with no other optical elements. The diffuser causes a point source to produce a speckle pattern on the sensor that covers the entire chip area.

The key insight of DiffuserCam is that, although individual speckle patterns are random, **within a limited field of view, the speckle patterns from point sources at different lateral positions share an approximate translational relationship** (lateral approximate shift-invariance, based on the optical memory effect). This allows the $\mathbf{H}$ matrix to be approximated as cyclic shifts of a single PSF, enabling efficient forward/adjoint operations via FFT. It should be noted that this approximation holds only within a limited lateral field of view; for axial (depth) displacements, the PSF structure changes significantly, so the forward model is often implemented as a layered convolution with "lateral approximate shift-invariance + depth-dependent PSF." Furthermore, DiffuserCam exploits the depth dependence of the diffuser PSF (point sources at different depths produce speckle patterns at different scales) to achieve **single-shot 3D scene reconstruction (volumetric reconstruction)**, which conventional 2D cameras cannot accomplish. The output is a 3D volumetric intensity distribution rather than an explicit 4D light field.

### 1.3 Coded Aperture (Focal Plane Coding)

Another classical approach is the **coded aperture**, which originated in X-ray astronomy and gamma-ray imaging. The principle is to place an aperture mask with a specific transmittance pattern (a binary 0/1 pattern) in the optical path, so that the sensor captures a coded superposition of the scene; a decoding algorithm then recovers the original image.

**Fresnel Zone Plate (FZP):** The most classical coded aperture, whose transmittance pattern consists of concentric rings that diffract and focus incident parallel light. An FZP is essentially a diffractive optical element that can be etched into glass or silicon wafers using micro-nanofabrication, with a thickness of only a few micrometers. Its limitations include: low diffraction efficiency (typically 10%–30%) and ghost artifacts caused by multiple diffraction orders.

**Random coded apertures:** Use random or pseudo-random binary patterns (such as uniformly redundant arrays, URA) as masks. These patterns have favorable autocorrelation properties that make the deconvolution process numerically stable.

**Reconstruction algorithms:** Common reconstruction methods for coded aperture systems include:
- **Wiener filtering:** Inverse filtering of the PSF in the frequency domain, with a Wiener regularization term to suppress noise amplification. Fast but sensitive to PSF errors.
- **Richardson-Lucy iteration (RL):** Iterative deconvolution based on maximum likelihood (Poisson noise model), with multiplicative updates at each step to preserve non-negativity. Widely used in fluorescence microscopy.
- **ADMM (Alternating Direction Method of Multipliers):** Flexibly accommodates a variety of regularization terms (TV, L1 sparsity, non-negativity constraints, etc.) and is the most widely used framework in lensless imaging. Each iteration involves one FFT-based forward operation and one proximal operator step.

### 1.4 Image Reconstruction Algorithms

The reconstruction algorithm is the core of a lensless imaging system; its quality directly determines the usability of the final image. The following is a systematic overview from classical to deep learning methods:

**1.4.1 Wiener Deconvolution**

The frequency-domain expression is:

$$\hat{X}(f) = \frac{H^*(f)}{|H(f)|^2 + \lambda} Y(f)$$

where $\lambda$ is the regularization parameter (the reciprocal of the signal-to-noise ratio) and $H^*$ is the complex conjugate of the PSF spectrum. Wiener filtering can be understood as the optimal linear filter in the minimum mean-square-error sense. Its advantage is extremely fast computation (only two FFTs); its disadvantage is that it assumes additive white Gaussian noise and cannot exploit nonlinear image priors (such as sparsity).

**1.4.2 ADMM Reconstruction with TV Regularization**

The most widely used reconstruction framework for lensless imaging. The optimization objective is:

$$\hat{\mathbf{x}} = \arg\min_{\mathbf{x} \geq 0} \frac{1}{2}\|\mathbf{H}\mathbf{x} - \mathbf{y}\|_2^2 + \lambda \|\nabla \mathbf{x}\|_1$$

where $\|\nabla \mathbf{x}\|_1$ is the total variation (TV) regularization term, which suppresses ringing while preserving edges. ADMM decomposes the original problem into several subproblems solved in alternation:
- **Data fidelity subproblem:** Solved efficiently in the frequency domain via FFT (for a convolutional $\mathbf{H}$)
- **TV proximal subproblem:** Equivalent to isotropic TV denoising, solvable with the Chambolle algorithm

Each iteration has complexity approximately $O(N \log N)$; typically 50–500 iterations are sufficient to converge to acceptable quality.

**1.4.3 Deep Learning Reconstruction**

In recent years, deep neural network-based reconstruction methods have significantly outperformed classical iterative algorithms. Representative approaches include:

- **End-to-end U-Net reconstruction:** The sensor measurement $\mathbf{y}$ is fed directly into a U-Net, which outputs the reconstructed image. The network is trained on large numbers of (measurement, ground-truth) pairs, implicitly learning the PSF inverse mapping and image prior. The advantage is extremely fast inference (a single forward pass, milliseconds); the disadvantage is potential degradation when generalizing to different lighting conditions or unseen scene types.

- **Algorithm unrolling networks:** The ADMM or gradient descent iterations are unrolled into a fixed number of neural network layers, where each layer corresponds to one iteration and the regularization parameters are learned by the network. Representative works: LISTA (Learned ISTA), Deep Unrolling for Lensless. These networks inherit the interpretability of classical algorithms while optimizing parameters in a data-driven manner.

- **Physics-informed networks:** Works such as LearnedSensors (Sitzmann et al., 2018) propose jointly optimizing the optical encoding element (PSF shape) and the reconstruction network so that optical design and algorithm design are co-optimized. This is a canonical example of applying differentiable rendering ideas to imaging system design.

- **Diffusion model reconstruction:** Recent work has begun exploring diffusion models as powerful image priors, embedded in lensless imaging reconstruction in a plug-and-play manner, showing strong performance under low-light and high-noise conditions.

**1.4.4 Accuracy of the Forward Model**

Regardless of the reconstruction algorithm used, its performance upper bound is determined by the accuracy of the forward model $\mathbf{H}$. In practical systems, the following factors can cause $\mathbf{H}$ to deviate from the ideal convolution model:
- Spatial variation of the PSF (more pronounced near the sensor edges)
- Temperature drift and mechanical deformation of the diffuser
- Pixel response non-uniformity (PRNU) of the sensor
- Multiple scattering (for thicker scattering media)

### 1.5 Relationship Between Plenoptic and Lensless Imaging

Lensless imaging and light field cameras (Chapter 13) share a profound conceptual connection. Both are typical examples of **computational imaging**: both trade direct focusing for richer light-field information, then recover the desired image representation through computation.

The main difference is:
- A light field camera (microlens array approach) retains the main lens; the microlens array samples the angular directions of the light field at the focal plane.
- A lensless camera removes the main lens entirely; the primary role of the encoding mask is to cause each sensor pixel to receive a mixture of light from different directions and depths in the scene, enabling depth information to be resolved during reconstruction.

DiffuserCam's 3D reconstruction capability and the depth-of-field extension capability of light field cameras can both be described mathematically using a unified light field integral equation. However, because the depth-dependent characteristics of the diffuser PSF are stronger, DiffuserCam typically exhibits more favorable depth discrimination under the same compact optical structure. This advantage, however, is highly dependent on the specific system design, reconstruction prior, signal-to-noise ratio, and evaluation baseline, and cannot be summarized as universally "superior" depth resolution compared to microlens-based light field cameras.

### 1.6 Ultra-Thin Cameras (Metalens / Metasurface)

If the diffuser-based lensless camera represents the route of "abandoning focusing and recovering via algorithm," then the **metasurface flat lens (metalens)** represents a different route: "reimplementing focusing with nanostructures, but achieving extreme thinness."

**Basic principle:** A metalens consists of billions of sub-wavelength nanopillars (typically TiO₂ or GaN, height approximately 600 nm, pitch approximately 300 nm) arranged on a flat substrate according to a designed phase distribution. By controlling the geometry of the nanopillars (diameter, height), the transmitted phase at each location can be precisely tuned (continuously from 0 to 2π), achieving any desired wavefront shaping function at the macroscopic level — including focusing (equivalent to a convex lens), diffusion (equivalent to a diffuser), or arbitrary PSF design.

**Key advantages:**
- Total thickness less than 1 mm; when integrated directly with a CMOS sensor, the module height can be below 2 mm
- Through joint phase–group-delay design (dispersion engineering), chromatic aberration can be significantly suppressed at a number of discrete wavelengths or over a limited continuous bandwidth (achromatic metalens); current broadband achromatic metalenses for the full visible spectrum remain limited by aperture, efficiency, bandwidth, and manufacturing tolerances, and have not yet achieved complete elimination of focal-length variation
- Special PSFs not achievable with conventional refractive optics can be realized (e.g., helical phase, double-helix PSF for 3D localization)

**Current limitations:**
- **Narrow bandwidth:** The efficiency of achromatic metalenses across the full visible spectrum (400–700 nm) remains low; broadband full-color operation is an active research topic
- **High manufacturing cost:** Electron-beam lithography (EBL) or deep-UV lithography (DUV) is required; large-area mass production costs have not yet dropped to consumer level
- **Angle-of-incidence limitations:** For large numerical aperture (NA > 0.5) metalenses, controlling aberrations for obliquely incident light is difficult, limiting the field of view (FOV)
- **Thermal stability:** The phase response of nanostructures has some sensitivity to temperature; high-temperature environments (e.g., automotive applications) require additional calibration

**Relationship to lensless ISP:** Although a metalens system achieves "focusing" through nanostructures, its non-ideal PSF (residual aberrations, chromatic aberration) typically still requires back-end digital correction. This overlaps with the lens distortion correction and chromatic aberration correction modules of conventional ISP. As metalenses move toward practical deployment, ISP engineers will need to design dedicated joint optical-digital correction pipelines for them.

---

## §2 Calibration

### 2.1 PSF Calibration — Point Source Method and Random Speckle Method

The reconstruction quality of a lensless imaging system is extremely sensitive to the accuracy of PSF calibration; an accurate PSF is a prerequisite for the reconstruction algorithm to function effectively.

**Point source calibration:**

The most direct PSF measurement method: in a darkroom, a pinhole (diameter approximately 5–50 μm) is placed in front of a light source to approximate a point source, positioned at a distance from the sensor equal to the intended working distance. The point source is then scanned across multiple positions within the sensor's field of view, and the sensor response at each position is recorded.

Advantage: Physically direct — the response at each position is the PSF at that position.
Disadvantage: Time-consuming (requires mechanical scanning); demanding requirements on pinhole brightness and collimation; difficult to implement in low-cost systems.

**Random speckle calibration:**

Uses random intensity patterns generated by a laser speckle or by an LED with a diffuser as calibration targets; PSFs are extracted from multiple frames of measurements through statistical methods. This approach does not require precise positioning, but is more sensitive to the assumption of spatial shift-invariance of the PSF.

**Practical considerations:**
- PSF calibration should be performed at the same sensor gain and exposure time as actual use, to ensure consistent linear operating points
- For systems with significantly space-variant PSFs, multiple positions should be sampled on a grid across the sensor field of view, constructing a piecewise PSF or continuous PSF model
- Saturation must be avoided during calibration (the sensor entering its nonlinear range will corrupt the PSF estimate)

### 2.2 Measurement of the System Matrix H

For very large-scale systems (e.g., high-resolution sensors), directly measuring the complete $\mathbf{H}$ matrix (of size pixels × pixels, potentially $10^6 \times 10^6$) is infeasible. In practice, several approximation strategies are used:

**Convolution approximation:** For a space-invariant system, $\mathbf{H}$ is equivalent to a convolution with a single PSF; only a PSF kernel the same size as the image needs to be stored, and both the forward operation and the transpose operation can be implemented via FFT, reducing complexity from $O(N^2)$ to $O(N \log N)$.

**Block space-variant model:** The field of view is divided into several regions, each approximated with an independent local PSF; reconstruction is performed block by block and then composited. The cost is that smooth transitions must be handled at region boundaries to avoid block artifacts.

**Low-rank approximation:** Exploits the low-rank structure of the PSF (similarity between PSFs at different positions) to decompose $\mathbf{H}$ into a linear combination of a small number of basis PSFs, greatly reducing both storage and computation.

### 2.3 Effect of Calibration Accuracy on Reconstruction Quality

PSF calibration errors (the discrepancy between the $\hat{H}$ used in practice and the true system matrix $H$) directly degrade reconstruction quality, manifesting as:

- **Blur residual:** When the PSF estimate is too large or too small, the reconstructed image shows residual blur, analogous to under- or over-denoising.
- **Ringing artifacts:** Errors in the PSF estimate near zero-crossings in the frequency domain cause instability in inverse filtering, producing ringing fringes near edges in the reconstructed image.
- **Ghost images:** In systems with multiple diffraction orders (e.g., zone plates), if the forward model does not account for higher-order diffraction terms, semi-transparent ghost overlays appear in the reconstructed image.

Based on empirical observations, when the normalized mean-square error (NMSE) of PSF calibration reaches approximately 1%–5%, the PSNR of the reconstructed image may drop by 2–5 dB. However, this quantitative relationship is not a universal law; the actual impact depends on the error structure (random noise type vs. systematic offset), the robustness of the reconstruction algorithm to model mismatch, and scene content, and should not be cited as a fixed mapping applicable across systems.

---

## §3 Tuning

### 3.1 Regularization Parameter Selection (TV, L1, L2)

The regularization parameter $\lambda$ is the most critical tuning knob in lensless reconstruction. Its essence is a balance between **data fidelity** (the reconstructed image, when passed through the forward model, should match the measurements) and **prior constraints** (the reconstructed image should satisfy some form of smoothness or sparsity).

- **$\lambda$ too small:** The data fidelity term dominates; the reconstructed image overfits measurement noise, resulting in severe noise amplification and ringing.
- **$\lambda$ too large:** The regularization term dominates; the reconstructed image is excessively smoothed, fine textures and edges are lost, and PSNR drops accordingly.

Selection methods:
- **L-curve method:** Plot the curve of data residual vs. regularization term norm at different values of $\lambda$; take $\lambda$ at the "corner point."
- **Generalized cross-validation (GCV):** A data-driven $\lambda$ estimation method requiring no ground-truth reference.
- **Rule of thumb:** For a typical DiffuserCam system, the TV regularization parameter $\lambda$ generally falls in the range $10^{-3}$–$10^{-1}$ (for normalized measurements), requiring fine-tuning based on lighting conditions and diffuser characteristics.

Applicable scenarios for different regularization types:
- **L2 (Tikhonov) regularization:** Computationally simple; produces smooth reconstructed images; suitable when PSF estimation accuracy is high, but blurs edges.
- **L1 sparsity regularization:** Suitable for intrinsically sparse scenes (such as fluorescence imaging with sparse fluorescence markers); not well-suited for natural images.
- **TV (total variation) regularization:** Suppresses ringing while preserving edge sharpness; the first choice for natural image reconstruction; computationally more expensive than L2.
- **Non-local means (NLM) / block matching (BM3D) as plug-and-play priors:** Exploits non-local self-similarity between image patches to further improve reconstruction quality, at the cost of high computational overhead.

### 3.2 Trade-off Between Iteration Count and Reconstruction Quality

Another key parameter for iterative algorithms such as ADMM is the maximum number of iterations $K$.

- **Early iterations (K < 20):** Image outlines are roughly discernible; high-frequency details have not yet converged; overall appearance is blurry.
- **Mid-range iterations (K ~ 50–200):** Most information has been recovered; PSNR is close to optimal; a good accuracy-speed trade-off point for real-time applications.
- **Full convergence (K > 500):** The algorithm converges to the optimal solution, but this is typically unacceptable in real-time systems (single-frame reconstruction may take seconds to minutes).

Acceleration strategies:
- **Adaptive ADMM step size ($\rho$) adjustment:** Dynamically adjusting $\rho$ based on the ratio of primal and dual residuals can reduce the number of iterations by 30%–50%.
- **GPU parallelization:** Both FFT operations and thresholding operations map efficiently to GPU, enabling order-of-magnitude speedup.
- **Warm start:** For video sequences, using the previous frame's reconstruction as the initial value for the current frame significantly reduces the number of convergence iterations.

### 3.3 Training Strategy for Deep Learning Reconstruction Networks

Training lensless reconstruction networks presents several unique challenges:

**Data collection:** The most reliable training data is (measurement, ground-truth) pairs collected on the actual physical system. The standard approach is to place target scenes (calibration patterns, printed natural images) in front of the camera and simultaneously capture with both the lensless camera and a reference camera (a conventional camera with a lens), using the reference camera image as ground truth.

**Sim-to-real gap between simulation training and real testing:** It is also possible to train with simulated data (convolving clean images with the calibrated PSF and adding noise), but due to PSF calibration errors and sensor nonlinearities, models trained on simulated data often show performance degradation on the real system. A small amount of real paired data is typically needed for fine-tuning.

**Loss function selection:**
- **MSE/L2 loss:** Optimizes PSNR but tends to predict the mean, leading to over-smooth images.
- **Perceptual loss (VGG feature loss):** Computes distances in feature space; helps preserve texture details; better visual quality, but PSNR may be slightly lower.
- **Adversarial loss (GAN loss):** Produces the richest details, but training is unstable and may produce hallucinated details, which must be used with caution in medical applications.

**Normalization and preprocessing:** It is recommended to globally normalize the sensor measurements (divide by the maximum value or a percentile) and subtract the mean background (dark frame). The normalization scheme for network inputs has a significant effect on convergence speed.

---

## §4 Artifacts

### 4.1 Ringing and Spatial Oscillation Artifacts

Ringing is the most common artifact in lensless reconstruction. Its root cause is the amplification of PSF spectral zeros or low-value regions during frequency-domain inverse filtering.

**Appearance:** Regular alternating bright and dark fringes appear near strong edges (e.g., light-dark boundaries, text outlines) in the reconstructed image, decaying exponentially with distance from the edge.

**Suppression methods:**
- Introducing sufficient regularization (TV or L1) can effectively suppress ringing, at the cost of slightly smoothed edges.
- Windowing: Weighting the PSF spectrum in the frequency domain, reducing the weight in regions where the PSF spectrum approaches zero; analogous to the $\lambda$ term in Wiener filtering.
- Constraining the reconstructed image to be non-negative ($\mathbf{x} \geq 0$) can indirectly suppress some negative-valued oscillations.

### 4.2 Blur Residual from Inaccurate PSF

When the actual PSF deviates from the calibrated PSF (e.g., due to temperature drift, mechanical vibration, or changes in the gap between the sensor and the diffuser), the reconstructed image shows residual blur, appearing as a generally unsharp image or directional blur in localized regions.

**Diagnostic method:** Analyze the PSF of point-like targets in the reconstructed image (e.g., strong bright spots in the scene) — if their profiles are not ideal point shapes but show tails or smearing, the PSF contains errors.

**Mitigation methods:**
- Periodically recalibrate the PSF (especially in use cases with dramatic temperature changes)
- Introduce a blind deconvolution step in the reconstruction algorithm to simultaneously estimate PSF errors while reconstructing the image
- Deep learning reconstruction networks have some robustness to small PSF variations (because the training data covers a certain range of PSF variation)

### 4.3 Noise Amplification Under Low-Light Conditions

Low-light imaging is a notable weakness of lensless cameras. The fundamental reason is that each sensor pixel in a lensless camera receives a superposition of light from the entire scene (rather than focused light from a single scene point). Each pixel's photon count is not inherently lower than in a conventional camera — but the reconstruction process effectively performs an operation analogous to "stretching," amplifying the noise proportionally.

A more severe problem arises when the scene contains strong bright sources (e.g., light sources): their scattering patterns cover the entire sensor, drowning out the weak signals from other regions and causing loss of scene information near strong bright points (a high dynamic range challenge).

**Countermeasures:**
- **Higher sensor ISO + lower regularization $\lambda$:** Allows more noise through, avoiding excessive regularization that suppresses signal
- **Multi-frame averaging:** Under static scenes, averaging multiple frames reduces measurement noise before reconstruction
- **Noise-aware regularization:** Adjust the data fidelity term based on a Poisson noise model (the dominant noise type under low light), replacing the L2 norm with KL divergence
- **HDR merging:** Analogous to conventional ISP HDR multi-exposure merging — first perform HDR fusion at the measurement level, then reconstruct

---

## §5 Evaluation

### 5.1 Reconstruction PSNR / SSIM

The reconstruction quality of lensless imaging systems is typically measured by PSNR (peak signal-to-noise ratio) and SSIM (structural similarity), using images captured under the same scene with a reference camera (a standard camera with a lens) as ground truth.

Typical reference figures (based on simulations or controlled laboratory conditions for DiffuserCam-class systems, moderate illumination, $512 \times 512$ resolution; actual values are highly dependent on the test dataset, calibration quality, signal-to-noise ratio, and evaluation methodology, and should not be used as universal benchmarks across publications):
- Wiener deconvolution: PSNR ≈ 22–25 dB, SSIM ≈ 0.55–0.70
- ADMM + TV: PSNR ≈ 25–28 dB, SSIM ≈ 0.70–0.80
- Deep learning reconstruction (U-Net / Unrolled): PSNR ≈ 28–33 dB, SSIM ≈ 0.80–0.90

Note: The viewpoint and exposure of the lensless camera and the reference camera cannot be perfectly matched; ground-truth alignment (including geometric registration and brightness normalization) requires careful handling.

### 5.2 MTF Comparison with Conventional Cameras

MTF (modulation transfer function) is the standard tool for measuring the spatial resolution of an imaging system. When evaluating lensless cameras, the MTF is typically computed on the reconstructed image (using the slanted-edge method, ISO 12233 standard) and compared with a conventional camera of equivalent sensor size.

The best current lensless reconstruction systems achieve an MTF of approximately 0.2–0.4 at the Nyquist frequency $f_{Ny}/2$, while high-quality cameras with lenses can achieve 0.6–0.8 at the same frequency. The gap remains substantial, and this is one of the biggest obstacles to lensless imaging in consumer applications.

Directions for improving the MTF of lensless systems:
- More optimized phase mask design (maximizing PSF condition number)
- More accurate PSF calibration (reducing model error)
- Super-resolution reconstruction (exploiting the optical aliasing characteristics of the diffuser for super-resolution)

### 5.3 Three-Dimensional Reconstruction Accuracy

For lensless systems with 3D reconstruction capability (such as DiffuserCam), evaluation metrics also include:

- **Axial (depth) resolution:** The minimum separation between two depth planes that the system can resolve. Typical value: DiffuserCam achieves an axial resolution of approximately 2–5 mm at a working distance of 50 mm (Antipa et al., Optica 2018 experimentally verified resolvable depth planes separated by 2 mm).
- **Trade-off between lateral resolution and number of depth layers:** 3D reconstruction is an underdetermined problem; there is a fundamental trade-off between lateral resolution and the number of reconstructable depth layers, jointly determined by the sensor pixel count and the depth-dependent characteristics of the PSF.
- **3D localization accuracy (fluorescence microscopy applications):** Measured as the root mean square error (RMSE) of 3D fluorescent point localization; excellent systems can achieve lateral 50–100 nm, axial 100–200 nm (requires high-quality calibrated PSF).

---

## §6 Code

The companion code for this chapter is in *See §6 Code section for runnable examples.*, covering:
- DiffuserCam forward simulation using NumPy/SciPy (convolution measurement generation)
- Wiener deconvolution reconstruction implementation and parameter sweep
- ADMM + TV iterative reconstruction implementation (runnable on CPU/GPU)
- PSF calibration error robustness experiments
- Plots of reconstruction PSNR/SSIM as a function of regularization parameter

---

## References

1. **Antipa, N., Kuo, G., Heckel, R., Mildenhall, B., Bostan, E., Ng, R., & Waller, L.** (2018). DiffuserCam: Lensless single-exposure 3D imaging. *Optica*, 5(1), 1–9. — The most influential work in lensless imaging; proposes using a random diffuser for single-exposure 3D light field reconstruction.

2. **Boominathan, V., Adams, J. K., Robinson, J. T., & Veeraraghavan, A.** (2022). PhlatCam: Designed phase-mask based thin lensless camera. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 44(4), 2002–2016. — Proposes improving reconstruction quality by using an optimally designed phase mask (rather than a random diffuser), representing the direction of optical-algorithm co-design.

3. **Kuo, G., Liu, F. L., Grossrubatscher, I., Ng, R., & Waller, L.** (2020). On-chip fluorescence microscopy with a random microlens diffuser. *Optics Express*, 28(6), 8384–8399. — Demonstrates a specific implementation of lensless cameras in on-chip fluorescence microscopy (biomedical applications), with detailed analysis of PSF calibration and reconstruction algorithm practical issues.

4. **Sitzmann, V., Diamond, S., Peng, Y., Dun, X., Boyd, S., Heidrich, W., Heide, F., & Wetzstein, G.** (2018). End-to-end optimization of optics and image processing for achromatic extended depth of field and super-resolution imaging. *ACM Transactions on Graphics (SIGGRAPH)*, 37(4), 114. — Proposes end-to-end joint optimization of optical encoding (metalens/phase plate PSF design) and deep learning reconstruction networks, pioneering the research paradigm of differentiable optical design.

5. **Monakhova, K., Yurtsever, J., Kuo, G., Antipa, N., Yanny, K., & Waller, L.** (2019). Learned reconstructions for practical mask-based lensless imaging. *Optics Express*, 27(20), 28075–28090. — Systematically compares classical iterative algorithms and deep learning reconstruction methods on a real lensless camera, providing a practical engineering selection guide.

6. **Tseng, E., Colburn, S., Whitehead, J., Huang, L., Baek, S. H., Majumdar, A., & Heide, F.** (2021). Neural nano-optics for high-quality thin lens imaging. *Nature Communications*, 12(1), 6493. — Combines neural networks with nano-optical metasurface design to realize a full-color wide-angle ultra-thin camera prototype, representing the latest advances in metalens + AI integration.

---

*This chapter covers the core principles, calibration procedures, tuning strategies, typical artifacts, and evaluation methods of lensless imaging. Readers who wish to study the mathematics of 3D reconstruction in depth are encouraged to read Chapter 13 (Light Field Imaging) and Chapter 4 (Noise Models) alongside this chapter; for general deep learning reconstruction network training methods, refer to the relevant chapters in Part 3 (DL-ISP).*

---

## §8 Glossary

**Lensless Imaging**
An imaging paradigm that completely removes the conventional refractive lens and places only a thin encoding element (diffuser, phase mask, Fresnel zone plate, etc.) in front of the sensor. The sensor captures optically encoded, aliased measurements that must undergo computational reconstruction before a viewable image can be recovered. Compared to conventional cameras, the Z-axis thickness of the optical module in a lensless camera can be compressed from the millimeter scale down to the micrometer scale, making it the core imaging solution for ultra-thin-form-factor applications such as wearables, medical endoscopes, and smart capsules.

**Phase Mask / Diffuser**
The optical encoding element that replaces the conventional lens in lensless imaging. A phase mask imposes specific phase delays on the optical wavefront at different locations, causing a point source to produce an extended pattern (PSF) on the sensor that covers the entire chip — rather than a small spot — thereby encoding scene information into the measurement via convolution. DiffuserCam uses a commercial random diffuser (cost approximately a few dollars); PhlatCam uses an optimally designed phase mask to improve reconstruction quality.

**Point Spread Function (PSF)**
The response pattern formed on the sensor by a single point source in the scene; it is the core of the forward model of a lensless imaging system. For a random diffuser, the PSF is a speckle pattern covering the entire sensor. Key properties of the PSF: (1) within a limited lateral field of view, PSFs at different lateral positions share an approximate translational relationship (lateral approximate shift-invariance, based on the optical memory effect); (2) the PSF structure changes significantly at different depth layers (depth-dependent PSF), which is the physical basis for 3D reconstruction in lensless systems.

**Volumetric Reconstruction**
The capability of a lensless camera (such as DiffuserCam) to reconstruct the 3D scene intensity distribution from a single 2D sensor exposure — exploiting the depth dependence of the diffuser PSF — yielding a 3D volumetric intensity (a stack of 2D images at each depth layer). The output is a 3D volumetric intensity distribution, as distinct from the single 2D image of a conventional camera, and also distinct from the 4D light field $L(x,y,u,v)$ that includes angular dimensions as captured by a light field camera.

**Optical Memory Effect**
A statistical property of scattering media: when a point source undergoes a small lateral displacement (perpendicular to the optical axis), the resulting speckle pattern approximately undergoes the same direction and magnitude of translation, rather than becoming a completely new random pattern. DiffuserCam relies on this effect to ensure lateral approximate shift-invariance of the PSF within a limited field of view, allowing the forward model $\mathbf{H}$ to be approximated as a convolution structure, enabling FFT-based efficient reconstruction. The effective range of the memory effect narrows as the thickness of the scattering medium increases.

**ADMM (Alternating Direction Method of Multipliers)**
The most commonly used iterative optimization framework in lensless imaging reconstruction, used to solve inverse problems with various regularization constraints (TV regularization, L1 sparsity, non-negativity constraints, etc.). ADMM decomposes the original optimization problem into several subproblems solved in alternation: the data fidelity subproblem is solved efficiently in the frequency domain via FFT (for a convolutional forward model); the regularization proximal subproblem (e.g., TV denoising) is solved independently. Each iteration has complexity approximately $O(N\log N)$; convergence typically requires 50–500 iterations.

**Total Variation Regularization (TV)**
The most commonly used image prior term in ADMM reconstruction; the optimization objective is $\|\nabla\mathbf{x}\|_1$ (the sum of the L1 norms of image gradients), used to preserve image edges while suppressing noise and ringing. Compared to L2 (Tikhonov) regularization, TV produces piecewise-smooth reconstruction results that are better suited to natural images. Compared to L1 sparsity regularization, TV does not require the scene itself to be sparse, making it more general.

**Algorithm Unrolling / Unrolled Network**
A deep learning reconstruction architecture that unrolls a fixed number of iterations of an iterative optimization algorithm (such as ADMM or ISTA) into neural network layers, where each layer corresponds to one iteration of the algorithm, and the regularization parameters and step sizes are learned end-to-end. Unrolled networks inherit the interpretability and physical constraints of classical algorithms, while optimizing hyperparameters in a data-driven manner. This is one of the mainstream deep learning approaches in lensless reconstruction that balances interpretability and performance. Representative works: LISTA (Learned ISTA), Deep Unrolling for Lensless Imaging.

**Metasurface**
A two-dimensional optical element consisting of billions of sub-wavelength nanostructures (nanopillars, nanoholes, etc.) arranged in a designed spatial distribution on a flat substrate. By controlling the geometric parameters of the nanostructures (diameter, height, pitch), the phase (continuously tunable from 0 to $2\pi$), amplitude, and polarization of transmitted light can be precisely controlled at the sub-wavelength scale, achieving arbitrary wavefront shaping at the macroscopic level, with thickness of only a few hundred nanometers to micrometers. Metasurfaces are the core technological platform for realizing ultra-thin flat lenses (metalenses).

**Metalens (Ultra-thin Flat Lens)**
A flat lens based on the metasurface principle: by arranging sub-wavelength nanopillars of materials such as TiO₂ or GaN (typical height approximately 600 nm, pitch approximately 300 nm), a precisely computed phase distribution is imparted to incident light, achieving focusing, diffusion, or arbitrary PSF functions of conventional refractive optics at the macroscopic level, with total thickness less than 1 mm. Unlike the "abandon focusing, recover computationally" route of lensless diffuser cameras, the metalens represents the "reimplement focusing with nanostructures, achieve extreme thinness" route. Current challenges: low efficiency for broadband achromatic operation, high large-area manufacturing cost, limited field of view at large NA.

**Achromatic Metalens**
A metasurface lens design that uses joint phase–group-delay design (dispersion engineering) to give the lens the same focal length for different wavelengths at a number of discrete wavelengths or over a limited continuous bandwidth. The underlying principle is to introduce negative dispersion (group delay dispersion) into the metasurface, compensating for the positive dispersion inherent in diffractive optical elements (the tendency for focal length to shorten with decreasing wavelength). Current broadband achromatic metalenses for the full visible spectrum (400–700 nm) remain limited by aperture, efficiency, bandwidth, and manufacturing tolerances, and have not yet achieved complete elimination of focal-length variation; this is an active research topic in nano-optics.

**PSF Calibration**
The process of experimentally measuring the system point spread function in lensless imaging; it is a prerequisite for the reconstruction algorithm to function effectively. Common methods include: the point source method (scanning a pinhole across field positions in a darkroom and recording the sensor response at each position) and the random speckle calibration method (extracting the PSF from multiple frames of random patterns through statistical methods). PSF calibration accuracy directly determines the upper bound of reconstruction quality: calibration errors lead to residual blur, ringing artifacts, or ghost images. Practical systems must account for the effect of temperature drift and mechanical deformation on the PSF, and calibration should be performed under the intended use conditions.

**Wiener Deconvolution**
A linear reconstruction method that performs inverse filtering of the PSF in the frequency domain: $\hat{X}(f) = H^*(f)/[|H(f)|^2 + \lambda] \cdot Y(f)$, where $\lambda$ is the regularization parameter (reciprocal of the signal-to-noise ratio). Wiener filtering is the optimal linear estimator in the minimum mean-square-error sense, and is computationally very fast (only two FFTs required). Its disadvantages are that it assumes additive white Gaussian noise and cannot exploit nonlinear image priors (such as sparsity or non-negativity); reconstruction quality is generally lower than ADMM+TV iterative methods.

**Plug-and-Play Prior (PnP)**
A methodology that treats any established image denoiser (such as BM3D, DnCNN, or a diffusion model) as an implicit regularization prior, "plugging" it into an iterative reconstruction framework such as ADMM or gradient descent. In lensless imaging, PnP allows powerful natural image statistical priors (such as non-local self-similarity) to be exploited while keeping the physical forward model of the iterative algorithm unchanged; it typically outperforms conventional TV regularization under low-light and high-noise conditions. Recent work has also explored using diffusion models as PnP priors for lensless reconstruction.
