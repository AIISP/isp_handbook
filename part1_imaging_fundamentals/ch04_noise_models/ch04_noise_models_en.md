# Part 1, Chapter 04: Noise Models in Camera Sensors

> **Pipeline position:** Foundation for all denoising modules (Ch20 Raw Denoise, Ch34 Deep Denoise)
> **Prerequisites:** Chapter 3 (Sensor Physics — photodiode, pixel well capacity, ADC)
> **Reader path:** All readers

---

## §1 Theory

### 1.1 Where Does Noise Come From?

Every image captured by a digital sensor carries imperfections that are not present in the scene itself. Understanding the physical origin of these imperfections is not an academic exercise — it is the prerequisite for designing any denoising pipeline that actually works. A denoiser that does not match the true noise distribution will either smooth away texture or leave visible grain.

At the highest level, sensor noise has two distinct origins:

1. **Photon arrival is random.** Light is quantized into photons, and even under perfectly steady illumination the number of photons arriving at a pixel in a fixed interval follows a Poisson distribution. This is an irreducible physical reality.
2. **Electronics add noise on top.** The conversion chain — photodiode charge integration → source follower amplifier → column-level ADC — introduces thermal and electronic noise that is independent of the scene brightness.

These two origins produce two qualitatively different noise classes, and the combined model is the foundation of almost all camera noise literature.

---

### 1.2 Photon Shot Noise (Poisson Noise)

Let $\lambda$ be the expected number of photons collected by a pixel during one exposure. The actual photon count $N$ is a random variable:

$$N \sim \text{Poisson}(\lambda)$$

The key property of the Poisson distribution is that its variance equals its mean:

$$\mathbb{E}[N] = \lambda, \qquad \text{Var}(N) = \lambda$$

This means **shot noise is signal-dependent**: bright pixels are noisier in absolute terms, but because $\text{SNR} = \lambda / \sqrt{\lambda} = \sqrt{\lambda}$, bright pixels have better SNR. Shot noise cannot be reduced by better electronics — it is a fundamental quantum limit on measurement.

After charge-to-digital conversion with gain $a$ (electrons per digital number, often called the system gain or conversion gain), the pixel value $I$ has:

$$\text{Var}_{\text{shot}}(I) = a \cdot \mu$$

where $\mu = a\lambda$ is the mean pixel value in digital numbers. Note that $a$ is in units of [DN² / electron] after the full conversion chain, so it folds together quantum efficiency, fill factor, and ADC gain.

---

### 1.3 Read Noise and Thermal Noise (Gaussian Noise)

Independent of the photon signal, the readout electronics contribute a noise floor. Sources include:

- **Thermal (Johnson-Nyquist) noise** in the source follower transistor: $\sigma^2 \propto k_B T / C$
- **1/f (flicker) noise** in MOS transistors, dominant at low frequencies
- **Reset noise** (kTC noise): charge uncertainty when resetting the floating diffusion; in many sensors this is largely cancelled by correlated double sampling (CDS)
- **Quantization noise** from the ADC: $\sigma^2_{\text{quant}} = \Delta^2 / 12$ where $\Delta$ is the LSB step size

The aggregate of all these electronic contributions, after CDS, is well approximated by an additive zero-mean Gaussian:

$$n_{\text{read}} \sim \mathcal{N}(0, \sigma_{\text{read}}^2)$$

Unlike shot noise, $\sigma_{\text{read}}^2$ does not depend on the signal level. It represents the minimum noise floor of the sensor, visible in dark (underexposed) regions.

---

### 1.4 The Unified Poisson-Gaussian (Heteroscedastic) Noise Model

Combining shot noise and read noise, the total noise variance at a pixel with mean value $\mu$ (in digital numbers, linear raw domain) is:

$$\boxed{\sigma^2(\mu) = a\mu + b^2}$$

where:
- $a$ = shot noise coefficient (equal to the system gain in DN/electron)
- $b^2$ = read noise variance ($\sigma_{\text{read}}^2$, in DN²)

This **heteroscedastic** (signal-dependent variance) model was formally analyzed and validated by Foi et al. (2008) and has become the standard foundation for raw-domain denoising. The term "heteroscedastic" contrasts with a simpler "homoscedastic" (constant-variance) model and is the reason why denoising filters designed for additive white Gaussian noise (AWGN) underperform on real raw images.

**Physical interpretation of the two terms:**
- $a\mu$: grows linearly with signal — shot noise dominates at medium to high exposure
- $b^2$: constant floor — read noise dominates in shadows

The model is fit separately at each ISO level, yielding a pair $(a_{\text{ISO}}, b_{\text{ISO}})$ per ISO setting. In practice, $a$ increases with ISO (the amplifier raises signal and shot noise together), while $b$ may also increase slightly due to amplifier noise.

---

### 1.5 ISO Gain Amplification

ISO gain is an analog and/or digital amplification applied after the photodiode. If the base (ISO 100) conversion gain is $a_0$, then at ISO $g$ (relative to base):

$$a(g) = a_0 \cdot \frac{g}{g_{\text{base}}}$$

The read noise in input-referred electrons stays roughly constant, but in digital numbers after amplification:

$$b^2(g) = b_0^2 \cdot \left(\frac{g}{g_{\text{base}}}\right)^2 + b_{\text{amp}}^2(g)$$

where $b_{\text{amp}}^2(g)$ represents noise added by the amplifier itself at high gain settings. In practice, both $a(g)$ and $b(g)$ are measured empirically via flat-field calibration (see §2) rather than derived purely from first principles.

---

### 1.6 Dark Current

Dark current arises from thermally generated electron-hole pairs in the depletion region of the photodiode, even in the absence of light. The dark current rate $D$ (in electrons/second) follows an Arrhenius relationship with temperature $T$:

$$D \propto \exp\!\left(-\frac{E_g}{2k_B T}\right)$$

where $E_g \approx 1.12\,\text{eV}$ is the silicon bandgap and $k_B$ is Boltzmann's constant. Practically, dark current roughly doubles for every 6–8°C rise in temperature.

For an exposure time $t_{\text{exp}}$, the expected dark electrons per pixel is $D \cdot t_{\text{exp}}$, which also follows Poisson statistics. Dark current matters most in night photography (long exposures) and in thermal cameras. In mobile phones with short exposures at moderate temperatures, dark current is usually dominated by read noise.

Black level subtraction (BLS) removes the mean dark current, but its shot noise remains.

---

### 1.7 Fixed Pattern Noise (FPN)

So far the noise sources described are **temporal** — they vary independently from frame to frame. FPN is **spatial** — it is fixed across frames and appears as:

- **PRNU (Photo Response Non-Uniformity):** pixel-to-pixel variation in sensitivity due to manufacturing variation in photodiode area, oxide thickness, and quantum efficiency. PRNU is multiplicative: $\text{output} = (1 + \delta_{\text{PRNU}}) \cdot I_{\text{true}}$.
- **Column/row FPN:** systematic offset or gain variation along entire columns or rows, introduced by column-parallel ADC mismatch. Visible as vertical or horizontal banding.
- **Dark signal non-uniformity (DSNU):** spatially non-uniform dark current. Some "hot pixels" have dramatically higher dark current and appear as bright outliers in long exposures.

FPN is corrected in the calibration pipeline (flat-field and dark frame correction) rather than by denoising filters. After correction, residual FPN is often small enough to be treated as an additional additive component.

---

### 1.8 The Signal-to-Noise Ratio

Combining shot noise and read noise, the SNR (in linear units, not dB) is:

$$\text{SNR}(\mu) = \frac{\mu}{\sqrt{a\mu + b^2}}$$

This fundamental equation describes the entire dynamic range of the sensor:

- **At low signal** ($\mu \ll b^2/a$): $\text{SNR} \approx \mu / b$ — read-noise limited, SNR rises linearly with $\mu$
- **At medium/high signal** ($\mu \gg b^2/a$): $\text{SNR} \approx \sqrt{\mu/a}$ — shot-noise limited, SNR rises as $\sqrt{\mu}$
- **At saturation** ($\mu \to \mu_{\text{max}}$): dynamic range ceiling

In dB: $\text{SNR}_{\text{dB}} = 20 \log_{10}(\text{SNR})$. A sensor with $a = 0.01$ DN/e⁻, $b = 5$ DN, and $\mu_{\text{max}} = 4095$ DN achieves roughly 50 dB SNR at full scale — typical of a consumer sensor at base ISO.

---

### 1.9 Noise at Different Pipeline Stages

The Poisson-Gaussian model applies in the **linear raw domain** (after black level subtraction, before any nonlinear transform). As the image passes through the pipeline, the noise distribution changes:

| Stage | Noise Character |
|---|---|
| Linear raw (after BLS) | Poisson-Gaussian: $\sigma^2 = a\mu + b^2$ |
| After gamma / tone curve | Variance stabilized; no longer Poisson-Gaussian |
| After demosaic | Noise is spatially correlated (interpolation spreads noise) |
| After JPEG / YCbCr transform | Color channel noise partially decorrelated |
| sRGB output | Noise is signal-dependent + correlated + non-Gaussian |

This is why raw-domain denoising (Ch20) is more principled than sRGB-domain denoising: the noise model is known analytically. Deep learning approaches (Brooks et al., CVPR 2019; Abdelhamed et al., ICCV 2019; Lehtinen et al., ICML 2018) often work in raw or simulate the raw noise distribution.

---

## §2 Calibration

### 2.1 Flat Field Calibration Procedure

The parameters $(a, b^2)$ for each ISO cannot be measured from a single image — they require a statistical estimation procedure. The standard method is **flat field calibration**:

**Equipment needed:** Uniform illumination source (integrating sphere, evenly-lit diffuser, or gray card under stable light). The key requirement is spatial uniformity — any vignetting or illumination gradient will bias the variance measurement.

**Procedure:**

**Step 1 — Capture flat field images at multiple exposures.**
For each ISO setting (e.g., ISO 100, 400, 1600, 6400):
- Capture $N \geq 20$ frames at a series of exposures $E_1 < E_2 < \ldots < E_K$ that cover the usable dynamic range (from just above dark floor to just below saturation).
- Use RAW format, disable all in-camera processing.

**Step 2 — Compute mean and variance per patch.**
For each exposure $E_k$, select $M$ non-overlapping patches of size $P \times P$ (typically $P = 32$) from the center of the image (avoiding vignetting at edges). For each patch:
$$\mu_k = \frac{1}{P^2} \sum_{i,j} I_{k,i,j}, \qquad \sigma^2_k = \frac{1}{P^2 - 1} \sum_{i,j} (I_{k,i,j} - \mu_k)^2$$

Alternatively, use two frames at the same exposure and compute $\sigma^2 = \frac{1}{2}\text{Var}(I_1 - I_2)$ to remove FPN contributions.

**Step 3 — Plot variance vs. mean and fit the linear model.**
The $K \times M$ pairs $(\mu, \sigma^2)$ should lie on the line $\sigma^2 = a\mu + b^2$. Apply linear regression:
```python
coeffs = np.polyfit(means, variances, 1)  # [slope, intercept]
a_fit  = coeffs[0]    # shot noise coefficient
b2_fit = coeffs[1]    # read noise variance
```
Check the fit residuals. Outliers near saturation ($\mu > 0.95 \mu_{\text{max}}$) should be excluded. Negative intercepts indicate measurement error — increase the number of patches.

**Step 4 — Repeat at each ISO to build the noise curves $a(\text{ISO})$ and $b(\text{ISO})$.**

### 2.2 EMVA1288 Standard

The European Machine Vision Association standard **EMVA 1288** (current release: 4.0) defines a rigorous, vendor-neutral procedure for characterizing industrial and scientific cameras. Key parameters it measures include:

- Quantum efficiency (QE) vs. wavelength
- Conversion gain $K$ (DN/e⁻)
- Dark noise $\sigma_d$ (electrons)
- Saturation capacity $\mu_{p,\text{sat}}$ (electrons)
- Dynamic range (ratio of saturation to dark noise)
- Signal-to-noise ratio vs. exposure

The flat-field variance-mean procedure described above is the core of the EMVA 1288 photon transfer curve (PTC) method. While EMVA 1288 targets machine vision cameras, the methodology is directly applicable to mobile and consumer sensors.

### 2.3 Building Per-ISO Noise Curves

After fitting $(a_i, b_i^2)$ at each ISO $g_i$, store as a lookup table:

| ISO | $a$ (DN/e⁻ equiv.) | $b$ (DN) |
|-----|---------------------|----------|
| 100 | 0.001 | 1.2 |
| 400 | 0.004 | 2.0 |
| 1600 | 0.016 | 4.5 |
| 6400 | 0.064 | 10.1 |

These curves are embedded in the ISP as a noise model look-up table (NR-LUT) and used by the denoising module to set spatially adaptive filter strength.

---

## §3 Tuning

### 3.1 Using the Noise Model in the Denoising Pipeline

The noise model parameters $(a, b^2)$ at the current ISO determine the **expected noise level** at every pixel:

$$\hat{\sigma}(\mu) = \sqrt{a\mu + b^2}$$

A well-designed denoiser uses $\hat{\sigma}(\mu)$ to set its local filter strength. Pixels in dark regions (small $\mu$, dominated by $b^2$) require aggressive smoothing. Pixels in bright regions (large $\mu$, $a\mu \gg b^2$) need a lighter touch because they already have good SNR and contain more texture.

### 3.2 ISO-Dependent Threshold Lookup Table

In traditional ISP pipelines (bilateral filter, NLM, BM3D-style block matching), the denoising threshold is typically parameterized as a multiple of $\hat{\sigma}$:

$$T = k_{\text{NR}} \cdot \hat{\sigma}(\mu)$$

The tuning parameter $k_{\text{NR}}$ is set per ISO:

| ISO | $k_{\text{NR}}$ (luma) | $k_{\text{NR}}$ (chroma) | Notes |
|-----|------------------------|--------------------------|-------|
| 100 | 1.0 | 1.5 | Clean; minimal NR |
| 400 | 1.5 | 2.5 | Mild NR |
| 1600 | 2.5 | 4.0 | Moderate NR |
| 6400 | 4.0 | 6.0 | Aggressive NR; watch texture |
| 25600 | 5.0 | 8.0 | Maximum NR; plastic risk |

Chroma thresholds are typically set higher than luma because chroma noise is more perceptually objectionable and chroma channels contain less high-frequency texture information.

### 3.3 Artifact Trade-offs: Over- and Under-Denoising

**Over-denoising ($k_{\text{NR}}$ too large):**
- Loss of fine texture: hair, fabric weave, skin pores become blurred or smooth ("plastic skin" effect)
- Edge ringing if the denoiser is frequency-domain based
- Loss of perceived sharpness even if edges are preserved

**Under-denoising ($k_{\text{NR}}$ too small):**
- Visible grain in uniform areas (sky, skin, out-of-focus backgrounds)
- Chroma mottling (colored speckles) in dark regions
- Amplified noise after sharpening (see Ch21)

**Practical tuning workflow:**
1. Start with $k_{\text{NR}} = 1.0$ at all ISOs as baseline
2. Increase until grain disappears in flat patches (sky region of standard test scene)
3. Check texture retention on Siemens star / Dead Leaves chart
4. Verify with subjective visual review at 100% crop

---

## §4 Artifacts

### 4.1 Hot Pixels

Hot pixels are individual photodiodes with abnormally high dark current — often 10–100× the median. They appear as bright white or colored dots in long exposures or high-ISO shots, even in dark regions. Prevalence increases with:

- Sensor age (radiation damage creates crystal defects)
- Temperature (dark current rate doubles every ~8°C)
- Exposure time (longer integration accumulates more dark current)

**Correction:** Hot pixel correction (PDPC — Pixel Defect and Point Correction) maps defective pixel addresses in factory calibration and replaces them with interpolated values from neighbors. Residual hot pixels visible after PDPC are typically masked in a runtime map updated at sensor characterization.

### 4.2 Banding and Fixed Pattern Noise

**Vertical banding** arises from column-level ADC mismatch in column-parallel readout architectures. Each column has a slightly different offset or gain, creating periodic stripes.

**Horizontal banding** arises from row addressing timing noise — each row is read out at a slightly different time and picks up periodic power supply noise (e.g., 60 Hz).

**Correction strategies:**
- Factory calibration: measure and subtract per-column offset maps
- Runtime: use dark frame subtraction with optical black (OB) pixels
- Frequency-domain filtering if banding has a known frequency

After calibration, residual FPN appears as structured spatial noise that denoising filters (which assume spatial independence) struggle with. Dedicated de-banding filters operating in the frequency domain are needed.

### 4.3 Chroma Noise vs. Luma Noise

Luma noise is perceived as grain — tolerable at moderate levels, similar to film grain. Chroma noise manifests as colored speckles (random red/green/blue patches) that are far more objectionable to human observers, especially in skin tones and sky regions.

The higher perceptual weight of chroma noise motivates:
- Separate luma/chroma denoising thresholds (as in §3.2)
- Processing in a luminance-chrominance color space (YCbCr, Lab, YUV)
- More aggressive chroma NR in the sRGB post-processing stage

### 4.4 Noise Amplification from Demosaic Interaction

Demosaicing interpolates missing color channels, but it also spatially correlates what was originally independent per-pixel noise. After demosaic, noise samples at neighboring pixels are no longer independent — the correlation structure depends on the demosaic kernel. If the denoiser assumes i.i.d. noise (as most BM3D / NLM implementations do), it underestimates the effective noise at high frequencies and misses correlated noise patterns.

Deep learning denoisers (e.g., trained on SIDD or DND) implicitly learn the post-demosaic noise correlation from data. Traditional pipelines should apply noise estimation after accounting for the demosaic correlation kernel.

---

## §5 Evaluation

### 5.1 PSNR on Public Benchmarks

Two standard benchmarks dominate raw-domain denoising evaluation:

**SIDD (Smartphone Image Denoising Dataset)** — Abdelhamed et al., CVPR 2018. Contains aligned noisy/clean image pairs from 5 smartphone cameras at multiple ISO and lighting conditions. The benchmark provides a validation set (with public ground truth) and a test server. PSNR and SSIM on SIDD are the de facto standard metrics for raw and sRGB denoising.

**DND (Darmstadt Noise Dataset)** — Plotz and Roth, CVPR 2017. 50 real scenes captured with consumer cameras at high ISO paired with low-noise reference images. The test set ground truth is not public — results are submitted to an online server, preventing overfitting. PSNR on DND is widely reported.

Typical top-tier deep denoiser performance (as of 2024): PSNR > 39 dB on SIDD sRGB, > 48 dB on DND. Note that PSNR is measured after the full ISP; raw-domain PSNR numbers are not directly comparable.

### 5.2 Visual Noise Grain Test Methodology

Quantitative metrics do not fully capture perceptual quality. Standard visual test procedures:

1. **Uniform patch test:** Capture a 18% gray card or sky region at each ISO. At 100% crop, count visible grain. A scoring rubric: 1 (invisible) → 5 (severe).
2. **Dead Leaves chart:** Measures texture transfer function (TTF) and noise simultaneously. Allows plotting of the signal-to-noise ratio in texture vs. noise power.
3. **ISO 12232 SFR + NPS measurement:** Spatial frequency response (sharpness) and noise power spectrum measured together to characterize the sharpness-noise trade-off.

### 5.3 Noise vs. Sharpness Trade-off

Denoising and sharpening are antagonistic: any filter that reduces noise also reduces high-frequency signal. The trade-off is often visualized as a curve in (NPS, MTF) space at each ISO. An ideal denoiser moves along the Pareto front — reducing noise without MTF loss. Most practical denoisers trade some MTF for noise reduction.

### 5.4 Mean Opinion Score (MOS)

For perceptual evaluation, human observer studies use MOS on a 1–5 scale: subjects rate patches or full scenes for perceived noise. MOS correlates better with user satisfaction than PSNR, especially at high ISO where grain texture matters. Industry tuning pipelines run MOS studies with internal panels to set final $k_{\text{NR}}$ values per product.

---

## §6 Code

See *See §6 Code section for runnable examples.* in the same directory for:

- Simulated flat-field images at ISO 100 → 6400
- Noise model fitting via variance-mean regression
- SNR vs. mean signal plots
- Per-ISO noise level comparison visualizations
- Three exercises on noise model extension

---

## References

### Foundational Papers

1. **Foi, A., Trimeche, M., Katkovnik, V., & Egiazarian, K. (2008).** Practical Poissonian-Gaussian noise modeling and fitting for single-image raw-data. *IEEE Transactions on Image Processing*, 17(10), 1737–1754.
   - Establishes the heteroscedastic $\sigma^2 = a\mu + b^2$ model; derives variance-stabilizing transforms for raw images.

2. **Brooks, T., Mildenhall, B., Xue, T., Chen, J., Sharlet, D., & Barron, J. T. (2019).** Unprocessing images for learned raw denoising. *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, pp. 11036–11045.
   - Shows how to synthesize realistic raw noise by inverting the ISP; uses the Poisson-Gaussian model to generate training data.

3. **Abdelhamed, A., Lin, S., & Brown, M. S. (2018).** A high-quality denoising dataset for smartphone cameras. *CVPR*, pp. 1692–1700.
   - Introduces the SIDD benchmark dataset; characterizes noise in real smartphone sensors.

4. **Abdelhamed, A., Afifi, M., Timofte, R., & Brown, M. S. (2019).** NTIRE 2019 challenge on real image denoising: Methods and results. *CVPR Workshops*.
   - Survey of real-world noise modeling approaches.

5. **Abdelhamed, A., Brubaker, M. A., & Brown, M. S. (2019).** Noise flow: Noise modeling with conditional normalizing flows. *Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)*, pp. 3165–3173.
   - Models camera noise distribution with normalizing flows; demonstrates that the simple Gaussian approximation has limits at extreme ISOs.

6. **Lehtinen, J., Munkberg, J., Hasselgren, J., Laine, S., Karras, T., Aittala, M., & Aila, T. (2018).** Noise2Noise: Learning image restoration without clean data. *Proceedings of the 35th International Conference on Machine Learning (ICML)*, PMLR 80, pp. 2965–2974.
   - Shows that denoising networks can be trained on pairs of noisy images without clean targets, provided noise is zero-mean.

7. **Plotz, T., & Roth, S. (2017).** Benchmarking denoising algorithms with real photographs. *CVPR*, pp. 1586–1595.
   - Introduces the DND benchmark; methodology for capturing paired noisy/clean images using exposure difference.

### Standards and Calibration References

8. **EMVA Standard 1288 Release 4.0 (2021).** Standard for characterization and presentation of specification data for image sensors and cameras. European Machine Vision Association. Available at: [https://www.emva.org/standards-technology/emva-1288/](https://www.emva.org/standards-technology/emva-1288/)
   - Defines the photon transfer curve (PTC) method for noise characterization; the reference standard for industrial camera metrology.

9. **Janesick, J. R. (2007).** *Photon Transfer DN → λ*. SPIE Press.
   - Comprehensive treatment of the photon transfer curve, shot noise, and read noise in CCD and CMOS sensors.

### Datasets

10. **SIDD Dataset:** [https://www.eecs.yorku.ca/~kamel/sidd/](https://www.eecs.yorku.ca/~kamel/sidd/) — Smartphone Image Denoising Dataset with benchmark server.
11. **DND Benchmark:** [https://noise.visinf.tu-darmstadt.de/](https://noise.visinf.tu-darmstadt.de/) — Darmstadt Noise Dataset with online evaluation server.

### Textbook References

12. **Forsyth, D., & Ponce, J. (2011).** *Computer Vision: A Modern Approach* (2nd ed.). Prentice Hall. Chapter 1 (Image formation) and Chapter 7 (Feature detection) cover noise in image formation models.
13. **Nakamura, J. (Ed.) (2006).** *Image Sensors and Signal Processing for Digital Still Cameras*. CRC Press. Chapters 3–5 cover dark current, noise sources, and signal chain.
