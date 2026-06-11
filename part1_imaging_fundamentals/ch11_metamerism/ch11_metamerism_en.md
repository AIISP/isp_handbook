# Part 1, Chapter 11: Metamerism and Color Constancy

> **Pipeline position:** Theoretical foundation; influences AWB and CCM design
> **Prerequisites:** Chapter 5 (Color Science Fundamentals)
> **Reader path:** Algorithm engineers, color scientists

---

## §1 Theory

### 1.1 The Physical Nature of Metamerism

Metamerism is one of the most profound yet most easily overlooked phenomena in color science. Its essence is this: **color perception is a process of information compression**. The human eye has only three types of cone cells (L, M, S), each integrating over a broad spectral band to compress an entire spectral curve into three scalar response values. This dimensionality reduction is irreversible, inevitably producing a many-to-one mapping — different spectral distributions can yield exactly the same visual perception. Such a pair is called a metameric pair.

#### 1.1.1 Tristimulus Integration Formula

Given an illuminant spectral power distribution $E(\lambda)$, surface spectral reflectance $R(\lambda)$, and the CIE standard observer color matching functions $\bar{x}(\lambda)$, $\bar{y}(\lambda)$, $\bar{z}(\lambda)$, the tristimulus values are defined as:

$$X = k \int_{380}^{780} E(\lambda)\, R(\lambda)\, \bar{x}(\lambda)\, d\lambda$$

$$Y = k \int_{380}^{780} E(\lambda)\, R(\lambda)\, \bar{y}(\lambda)\, d\lambda$$

$$Z = k \int_{380}^{780} E(\lambda)\, R(\lambda)\, \bar{z}(\lambda)\, d\lambda$$

where $k$ is a normalization constant, typically $k = 100 / \int E(\lambda)\,\bar{y}(\lambda)\,d\lambda$, so that the reference white has $Y=100$.

Two surfaces $R_1(\lambda)$ and $R_2(\lambda)$ form a metameric pair under illuminant $E_1$ if and only if:

$$\int E_1(\lambda)\,[R_1(\lambda) - R_2(\lambda)]\,\bar{x}(\lambda)\,d\lambda = 0$$

$$\int E_1(\lambda)\,[R_1(\lambda) - R_2(\lambda)]\,\bar{y}(\lambda)\,d\lambda = 0$$

$$\int E_1(\lambda)\,[R_1(\lambda) - R_2(\lambda)]\,\bar{z}(\lambda)\,d\lambda = 0$$

Under a different illuminant $E_2$, if these three integrals are not all zero, the color match breaks down. This means $\Delta R(\lambda) = R_1(\lambda) - R_2(\lambda)$ lies in the orthogonal complement (null space) of the space spanned by $\{E_1 \bar{x}, E_1 \bar{y}, E_1 \bar{z}\}$, but when the illuminant changes to $E_2$, $\Delta R$ no longer lies in the new null space and the difference becomes visible.

#### 1.1.2 Metamerism Index

To quantify the color difference of a metameric pair after an illuminant change, CIE defines the **Metamerism Index (MI)**:

$$\text{MI} = \Delta E_{00}(E_1 \to E_2)$$

This is the CIEDE2000 color difference between the two surfaces after switching from the reference illuminant $E_1$ (where they match exactly, $\Delta E_{00}=0$) to a test illuminant $E_2$. A larger MI indicates greater spectral differences between the pair and higher sensitivity to illuminant changes in practice. CIE recommends using $E_1 = $ D65 (daylight) as the reference, with $E_2$ being illuminant A (incandescent), TL84 (fluorescent), etc. As a general guideline, MI < 1 is considered mild, 1–3 moderate, and >3 severe metamerism. (These thresholds represent industry consensus; the CIE standard itself does not prescribe universal numerical criteria, and acceptable ranges depend on the application.)

### 1.2 Illuminant Metamerism vs. Observer Metamerism

Metamerism can be classified along different dimensions. The two most important types are:

#### 1.2.1 Illuminant Metamerism

This is the type most commonly encountered by ISP engineers. Two surfaces match in color under one illuminant (e.g., D65) but no longer match under another (e.g., fluorescent TL84 or LED). The root cause is that the two surfaces have different spectral reflectances; when the illuminant's spectral distribution changes, the weighted integrals change accordingly.

Typical scenario: a red shirt matches a reference color patch under natural light, but the two diverge in color when viewed under fluorescent store lighting. The textile, printing, and cosmetics industries are highly sensitive to this effect. The multi-illuminant CCM design in ISP pipelines is precisely intended to address this problem.

#### 1.2.2 Observer Metamerism

Different observers (people) have individual variations in cone cell spectral sensitivities, arising primarily from: shifts in the peak wavelengths of photopigments, differences in macular pigment density, and differences in lens absorption. Two observers may therefore disagree on whether a given pair of colors matches.

The CIE 1931 standard observer is an average derived from data collected from approximately 17 subjects (Wright: 10, Guild: 7) at a 2° visual field. The 1964 10° supplementary standard observer exhibits even larger inter-observer variability. Observer metamerism is critical in precision color evaluation (such as proofing and hue comparison), but in ISP pipeline design the CIE 2° or 10° standard observer is used as the sole target and individual differences are not explicitly handled.

#### 1.2.3 Device Metamerism

Camera sensors have different spectral sensitivities from the human eye. The discrepancy between them constitutes device metamerism. Even if a camera's output is aligned with human perception under one illuminant via matrix correction (CCM), errors will still appear under illuminants with different spectral content. This is an inherent error source in ISP color management that cannot be fully eliminated by any linear transformation.

### 1.3 Camera–Eye Metameric Error and the Luther Condition

#### 1.3.1 The Luther Condition

If a camera sensor's spectral sensitivities $q_i(\lambda)$ ($i=1,2,3$ for R, G, B channels) are a **linear combination** of the CIE color matching functions $\bar{x}(\lambda)$, $\bar{y}(\lambda)$, $\bar{z}(\lambda)$, the sensor is said to satisfy the **Luther condition** (Luther-Ives condition):

$$\begin{pmatrix} q_1(\lambda) \\ q_2(\lambda) \\ q_3(\lambda) \end{pmatrix} = M \begin{pmatrix} \bar{x}(\lambda) \\ \bar{y}(\lambda) \\ \bar{z}(\lambda) \end{pmatrix}$$

where $M$ is a $3\times 3$ constant matrix. A camera satisfying the Luther condition will produce tristimulus values that agree with human vision for **any spectrum**, regardless of illuminant change — multiplying by $M^{-1}$ perfectly recovers XYZ. Such cameras are called colorimetric cameras.

#### 1.3.2 Deviation in Real Sensors

In practice, the spectral sensitivities of commercial CMOS image sensors are constrained by:
- **Silicon absorption characteristics**: these determine the basic shape at the near-infrared and blue ends;
- **Color filter array (CFA) dyes**: R/G/B filters in Bayer arrays have broadband responses that differ substantially in shape from the color matching functions;
- **Infrared cut filter (IRCF)**: cuts off near-infrared above 700 nm, causing a steep drop in the long-wavelength response of the R channel;
- **Microlens and angular response**: second-order effects.

As a result, real sensor spectral sensitivities cannot be expressed as linear combinations of the CIE CMFs, and the Luther condition is not satisfied. The deviation is typically quantified by **principal component reconstruction error** — projecting the sensor sensitivity onto the subspace spanned by the CMFs and measuring the residual; a larger residual indicates more severe metameric error.

#### 1.3.3 Practical Consequences

For most natural surfaces (vegetation, skin, textiles), the tristimulus values of camera and human eye can be reasonably aligned with a 3×3 CCM, with ΔE < 3 being acceptable. However, for **narrow-band spectral materials**:
- **Fluorescent dyes** (fluorescent chalk, high-visibility vests): emission peaks are extremely narrow; the camera R/G/B integrals diverge significantly from the human eye's $\bar{y}$, $\bar{x}$;
- **LED phosphor emission**: the blue pump peak of white LEDs near 450 nm is extremely sharp; the camera B channel deviates most from $\bar{z}(\lambda)$;
- **Neon signs and gas-discharge sources**: dominated by discrete line spectra, CCM generalization is poor;
- **Fluorescent whitening agents (FWA)**: commonly found in paper and white fabrics; excited by UV, they emit blue-white light, causing the camera to "see" whites as brighter than the human eye does.

### 1.4 Impact of Metamerism on AWB and CCM

#### 1.4.1 The Statistical Nature of CCM

Traditional CCM is a 3×3 linear matrix obtained by least-squares fitting on a standard color chart (e.g., Macbeth ColorChecker) **under a specific illuminant**. The optimization objective is:

$$M^* = \argmin_M \sum_{i=1}^{N} \Delta E_{00}\!\left(M \cdot \mathbf{c}_i,\; \mathbf{t}_i\right)$$

where $\mathbf{c}_i$ is the camera RGB and $\mathbf{t}_i$ is the corresponding target Lab value. This is essentially finding an optimal linear transform in the color space for that illuminant; its accuracy depends on the spectral diversity of the training samples and the linearity of the sensor response under that illuminant.

#### 1.4.2 CCM Failure Under Illuminant Changes

When the illuminant switches from the training illuminant (e.g., D65) to TL84 (tri-phosphor fluorescent), the CCM error increases sharply, particularly because:
- TL84's spectrum consists of mercury discharge lines combined with phosphor emission bands: the 546.1 nm mercury green line and the ~611 nm red phosphor emission peak (Eu³⁺ excited, not a mercury line) — the camera G and R channels integrate these sharp narrow-band peaks very differently from the human eye's $\bar{y}$ and $\bar{x}$;
- The CCM trained on D65 broadband illumination assumes a broadband linear relationship; narrow-band spectral input breaks this assumption;
- Systematic color casts under fluorescent lighting — green bias toward yellow, skin tones going green — are the direct perceptual manifestation of this metamerism.

#### 1.4.3 The Necessity of Multi-Illuminant CCM

To mitigate this problem, ISP design employs a **multi-illuminant CCM** strategy:
1. Calibrate separate CCMs (CCM_1 through CCM_N) under $N$ representative illuminants (typically N = 4–6);
2. Record the RGB ratios of gray patches in the RAW image under each illuminant to construct illuminant feature vectors;
3. Establish a lookup relationship from "illuminant feature vector → CCM index."

**Online inference:**
1. The AWB module outputs the current illuminant estimate, including correlated color temperature $T_{cc}$ and optionally an illuminant type label;
2. Perform weighted interpolation between the two (or four) nearest CCMs based on $T_{cc}$:

$$\text{CCM}_{eff} = \alpha \cdot \text{CCM}_i + (1-\alpha) \cdot \text{CCM}_j, \quad \alpha = \frac{T_{cc,j} - T_{cc}}{T_{cc,j} - T_{cc,i}}$$

3. For special illuminants (e.g., TL84 fluorescent), use additional illuminant type features (such as an anomalous G/B ratio) to introduce a classification label that forces a switch to the dedicated CCM, rather than relying solely on color temperature interpolation.

Multi-illuminant CCM can reduce the average ΔE under fluorescent lighting from 5–8 down to 2–4, but still has limitations for extreme narrow-band sources (monochromatic LEDs), where 3D-LUT nonlinear correction becomes necessary.

### 1.5 Spectral Sensitivity Optimization — Spectral Sharpening

#### 1.5.1 Finlayson's Spectral Sharpening Theory

Finlayson et al. (1994) proposed **spectral sharpening**, whose core idea is to apply a linear transform $A$ (a $3\times3$ matrix) to the camera's native RGB space, so that the resulting "sharpened" sensitivities $q'(\lambda) = A\,q(\lambda)$ more closely resemble the CIE CMFs in shape, thereby minimizing the Luther deviation.

The optimization objective can be stated as: among all invertible $3\times3$ matrices $A$, find the transform that minimizes the minimum angular deviation between the sharpened sensitivities and the CMFs:

$$A^* = \argmin_A \sum_{i=1}^{3} \left\| A q_i(\lambda) - \sum_j m_{ij} \bar{f}_j(\lambda) \right\|^2$$

where $\bar{f}_j(\lambda)$ are the CMF basis vectors, $m_{ij}$ are linear mixing coefficients, and the optimization is performed subject to the constraint that $A$ is invertible.

#### 1.5.2 Physical Meaning and Cost of Sharpening

Spectrally, sharpening is mathematically equivalent to **narrowing** the effective spectral response bandwidth of the sensor — making the R channel more focused on long wavelengths and the B channel more focused on short wavelengths, reducing spectral overlap among the three channels. However, this comes at significant cost:

- **SNR reduction**: the sharpening matrix $A$ typically contains negative weights, meaning some channel signals are subtracted and noise is amplified;
- **Dynamic range compression**: the effective full-well capacity utilization decreases;
- **Uneven channel gain**: larger digital gain is required to compensate, further raising the noise floor.

Commercial camera design therefore involves a fundamental trade-off between spectral sharpening (reduced metamerism) and photographic sensitivity. Smartphone cameras that prioritize low-light performance tend to use broader CFA filters and accept larger metameric errors.

#### 1.5.3 Practical Alternatives

At the ISP software level, spectral sharpening can be interpreted as introducing a regularization term during CCM computation that penalizes large off-diagonal coefficients in the matrix — a form of "soft sharpening." Another direction is to directly optimize CFA dye spectra to be narrower during sensor fabrication (as explored in Samsung ISOCELL's SPAD architecture), which is a fundamental hardware-level solution.

### 1.5.A CRI/Ra Color Rendering Index and Its Relationship to Metamerism

#### Definition of CRI (Color Rendering Index)

The **Color Rendering Index (CRI)**, or **Ra** for its general index, is a metric defined by the CIE to quantify how faithfully a light source renders the colors of objects, on a scale from 0 to 100, where 100 indicates perfect agreement with a reference source (blackbody radiation for low color temperatures, or a D-series daylight simulator for high color temperatures).

**Ra** is defined over eight CIE standard Munsell samples (R1–R8). For each sample, the CIELAB color difference $\Delta E_{i}^*$ is computed between the test illuminant and the reference illuminant; individual rendering indices and the general index are then:

$$R_i = 100 - 4.6 \cdot \Delta E_i^*, \quad i = 1, \ldots, 8$$

$$Ra = \frac{1}{8} \sum_{i=1}^{8} R_i$$

Individual $R_i$ values are not clipped at 100 and may be negative. $Ra \geq 90$ is considered excellent (museum, hospital, photographic studio standard); $Ra \geq 80$ is good (general indoor lighting); $Ra < 60$ is poor.

#### Connection Between CRI and Metamerism

CRI and metamerism measure two perspectives of the same underlying phenomenon:

| Dimension | CRI/Ra | Metamerism Index (MI) |
|-----------|--------|-----------------------|
| **Focus** | Illuminant's ability to render object colors | Stability of a metameric pair's color match across illuminants |
| **Computation basis** | 8 standard samples vs. reference illuminant | Color difference of a metameric pair under different illuminants |
| **Core link** | Low-CRI illuminants (Ra < 80) tend to have narrow-band SPDs that amplify metamerism | High MI indicates the pair is highly sensitive to narrow-band spectral features |

Low-CRI illuminants (e.g., older fluorescent lamps with Ra ≈ 60–70, high-pressure sodium lamps with Ra ≈ 20) have SPDs dominated by a few narrow emission peaks. Under such sources, differences between metameric pairs are amplified: small reflectance differences at specific wavelengths can yield dramatically different weighted integrals when the illuminant energy is concentrated in those narrow bands. By contrast, high-CRI sources (daylight, high-Ra LEDs) have more continuous SPDs and exhibit comparatively smaller metamerism effects.

#### R9 and ISP Skin Tone Rendering

Beyond Ra, CIE defines extended rendering indices R9–R15. **R9 (saturated red)** is of particular importance to ISP engineers:

$$R9 = 100 - 4.6 \cdot \Delta E_9^*$$

R9 measures how faithfully a source renders highly saturated reds — hues close to skin tones and lip colors. Many LED products with Ra ≥ 80 have R9 < 0 (severe distortion) because those LEDs emit insufficient radiant power in the 600–650 nm red band.

**Impact on ISP:**
- Under LEDs with low R9 (typical cool-white LED: R9 commonly 0–30), the red component of skin tones (oxyhemoglobin absorption trough near 540–580 nm) produces a larger Luther deviation between the camera R channel and the human eye L cones, increasing skin tone color error when the D65-CCM is applied to such sources;
- ISP multi-CCM strategies should treat low-R9 LEDs (typically cool-white LEDs at 5000–6500 K) as a separate calibration illuminant rather than sharing a CCM with D65;
- Studio lighting selection should favor fixtures with Ra > 95 and R9 > 50 to reduce metamerism-induced systematic color bias and ease the ISP color reproduction burden.

#### LED Illumination and CRI: A Detailed Analysis

Modern white LEDs typically employ a "blue pump + yellow phosphor" architecture, producing an SPD consisting of:
1. A blue pump peak (approximately 445–460 nm; very narrow, FWHM approximately 20–30 nm);
2. A broad yellow-green phosphor emission band (approximately 500–700 nm, peak near 550–560 nm).

This SPD structure has three consequences for ISP color management:
- **Excess green**: radiant power in the 500–580 nm green region (phosphor main emission) is high; camera G channel Luther deviation is maximized in this direction;
- **Deficient red**: radiant power in the 600–650 nm red region (phosphor tail) is low; R9 is depressed, and the camera R channel has limited ability to sense red objects;
- **Blue pump peak**: the sharp 450 nm peak creates the largest Luther deviation between the camera B channel and the human eye's $\bar{z}(\lambda)$.

These three factors combine to make LED illumination the most demanding scenario for ISP color reproduction, and the primary application context for multi-CCM strategies, 3D-LUT correction, and illuminant classifiers.

### 1.6 Fluorescent Materials and Special Spectral Scenarios

#### 1.6.1 Mechanism of Fluorescent Whitening Agents (FWA)

Fluorescent Whitening Agents (FWAs), also known as Optical Brightening Agents (OBAs), are widely present in white paper, white shirts, detergents, and many everyday objects. Their mechanism is to absorb ultraviolet light (approximately 300–400 nm) and re-emit it as blue-white visible light (emission band approximately 420–470 nm, with peak typically at 430–450 nm), making whites appear "whiter" — in effect, compensating for the slightly yellowish tint of white substrates by emitting extra blue light.

#### 1.6.2 Asymmetric Response Between Camera and Human Eye

- **Human eye**: insensitive to UV, perceiving only the visible emission from FWAs; white objects appear bright and clean;
- **Camera sensor**: typically has an IRCF to block near-infrared, but the UV/near-UV cutoff (350–400 nm) depends on the specific design; some sensors retain residual response near 400 nm;
- **Key asymmetry**: under illuminants containing UV components (daylight, some fluorescent lamps), the camera may "see" the B channel of FWA-treated objects as stronger than what the human eye perceives, causing white paper to appear blue-shifted or overexposed in the camera output.

#### 1.6.3 Effect on AWB and Color Reproduction

If FWA-containing white paper is used as the white reference point for AWB estimation, the AWB algorithm can be "deceived": it mistakes the blue-shifted FWA emission for the true illuminant color temperature, and then applies a warm correction to the entire image, causing a global yellow bias. High-accuracy AWB algorithms need to verify the spectral purity of white regions, or use a dedicated reference white (ceramic white without FWA) for calibration.

---

## §2 Calibration

### 2.1 Metamerism Index (MI) Measurement Procedure

Engineering measurement of the camera–eye metamerism level requires the following steps:

1. **Acquire spectral reflectance data**: use a spectrophotometer (e.g., Konica Minolta CM-700d) to measure the spectral reflectance curve $R_i(\lambda)$ of each patch on the test chart, wavelength range 360–740 nm, step size 10 nm.
2. **Calculate reference tristimulus values**: under reference illuminant $E_1$ (D65), use the CIE 1931 standard observer CMFs to compute $[X, Y, Z]_{E_1}$ for each patch, then convert to Lab space to obtain reference colors $L_1^*, a_1^*, b_1^*$.
3. **Camera capture and correction**: shoot the chart with the camera under the same illuminant, apply CCM correction to obtain camera-reproduced Lab values $L_c^*, a_c^*, b_c^*$, and compute $\Delta E_{00}$ (for reference evaluation, not the metamerism index).
4. **Switch to test illuminant**: under test illuminant $E_2$ (A / TL84 / LED), repeat steps 2–3 and compute $\Delta E_{00}(E_1 \to E_2)$; this is the metamerism index MI for that patch.
5. **Statistical summary**: compute the mean and maximum across all patches, reporting both average MI and worst-case MI, with particular attention to saturated colors and special material patches.

### 2.2 Multi-Illuminant Color Difference Statistical Evaluation

Industrial-standard multi-illuminant color difference testing typically covers the following standard illuminant combinations:

| Illuminant Code | Color Temperature / Type | Typical Scene |
|-----------------|--------------------------|---------------|
| D65 | 6504 K, daylight | Outdoor, standard evaluation |
| D50 | 5003 K, daylight | Printing, graphic design |
| A | 2856 K, tungsten | Household incandescent |
| TL84 | 4000 K, tri-phosphor fluorescent | European retail |
| CWF (F2) | 4230 K, cool white fluorescent | North American retail |
| LED BB | ~5000–6500 K | Modern office/commercial |

Recommended statistical metrics:
- **Mean ΔE00**: average across all patches under each illuminant;
- **P95 ΔE00**: 95th percentile, reflecting worst-case performance;
- **Color vector plot**: visualizes the direction and magnitude of color shift for each patch using arrows, helping to identify systematic biases.

### 2.3 Use of Spectral Reflectance Databases

Publicly available spectral datasets used for CCM optimization and metamerism analysis include:

- **Munsell 400-chip dataset** (Parkkinen et al., 1989): covers the full Munsell color system, 1257 spectra in total;
- **NCS Natural Color System spectral library**: industrial color standard;
- **Spectral Imaging Dataset** (Foster et al.): hyperspectral images of real scenes, 400–720 nm;
- **IES TM-30 illuminant spectral library**: covers 100+ commercial illuminants.

When these datasets are used for CCM optimization instead of relying solely on 24-patch Macbeth charts, generalization to natural scenes is significantly improved, and cross-illuminant metamerism risk can be quantitatively assessed.

---

## §3 Tuning

### 3.1 Multi-CCM Interpolation for Metamerism Mitigation

Multi-CCM interpolation is currently the most widely used approach to metamerism in smartphone ISPs. The basic workflow is as follows:

**Offline calibration phase:**
1. Calibrate CCM_1 through CCM_N separately under $N$ representative illuminants (typically N = 4–6);
2. Record the RGB ratios of gray patches in the camera RAW under each illuminant to construct illuminant feature vectors;
3. Establish a lookup relationship from "illuminant feature vector → CCM index."

**Online inference phase:**
1. The AWB module outputs the current illuminant estimate, including color temperature $T_{cc}$ and an optional illuminant type label;
2. Perform weighted interpolation between the two (or four) nearest CCMs based on $T_{cc}$:

$$\text{CCM}_{eff} = \alpha \cdot \text{CCM}_i + (1-\alpha) \cdot \text{CCM}_j, \quad \alpha = \frac{T_{cc,j} - T_{cc}}{T_{cc,j} - T_{cc,i}}$$

3. For special illuminants (e.g., TL84 fluorescent), use additional illuminant type features (such as an anomalous G/B ratio) to introduce a classification label that forces a switch to the dedicated CCM, rather than relying solely on color temperature interpolation.

**Note:** Interpolation is only valid along the color temperature dimension. TL84 and an LED of the same correlated color temperature have completely different spectral compositions; relying on color temperature interpolation alone will produce incorrect results. An illuminant type classifier is therefore indispensable.

### 3.2 Dedicated Tuning for Problematic Illuminants (TL84/LED)

#### 3.2.1 TL84 Fluorescent Tuning Notes

TL84 is particularly problematic because it contains both the 546.1 nm mercury green emission line and the ~611 nm red phosphor emission peak (the two have different physical mechanisms: the former is a mercury atomic line spectrum, the latter is a broadband emission peak from Eu³⁺ phosphor):

- **Green shift correction**: the camera G channel over-responds to the 546 nm mercury line, causing green scenes to appear overall greener and more yellow; the G→G term in the dedicated CCM typically needs to be appropriately reduced;
- **Skin tone correction**: skin tones are most prone to going green under TL84; it is recommended to separately evaluate ΔE on facial regions during calibration and apply skin-tone region-weighted optimization to the CCM;
- **Identification feature**: in the RAW before white balance, the G/(R+B) ratio in gray regions is significantly higher under TL84 than under D65, and can serve as a classification feature.

#### 3.2.2 LED Illuminant Tuning Notes

Modern LED sources come in many varieties (cool white, warm white, colored, RGBW), and the tuning challenges include:

- **Phosphor blue pump peak**: the sharp peak near 450 nm causes the camera B channel to deviate most from the human eye's $\bar{z}(\lambda)$; sky blue and purple are the hardest colors to reproduce under LED;
- **Batch variation**: the spectrum of LEDs with the same specification may drift across manufacturing batches; CCM optimization should use a statistical distribution rather than a single spectrum;
- **Mixed-light scenes**: indoor environments commonly involve "LED overhead lighting + daylight window" mixed illumination; a single-illuminant model cannot describe this, requiring mixed-light AWB or zone-based AWB.

### 3.3 3D-LUT as an Alternative

When a 3×3 linear CCM cannot meet accuracy requirements, a 3D-LUT (three-dimensional look-up table) provides nonlinear correction capability:

- **Advantages of 3D-LUT**: allows independent correction for any region of the color space, unconstrained by linearity; for colors that are severely distorted in specific regions (fluorescent colors, metallic colors), a 3D-LUT can make targeted corrections;
- **Typical specification**: 17×17×17 nodes (in Lab or HSL space), trilinear interpolation between nodes;
- **Calibration method**: shoot a large number of color patches (300+ colors recommended, covering high-saturation boundaries) under the target illuminant, then fit the LUT nodes using an optimization algorithm (e.g., radial basis function RBF or scattered data interpolation);
- **Cost**: storage and computation are significantly higher than a linear CCM; storing multiple LUT sets for multi-illuminant use and switching them in real time adds engineering difficulty;
- **Engineering practice**: most smartphone ISPs use 3D-LUT as a "tone refinement" stage after CCM — the CCM handles the primary color reproduction and the LUT corrects residual CCM errors and local saturated-color bias.

---

## §4 Artifacts

### 4.1 Systematic Color Casts Under Fluorescent Lighting

Fluorescent lighting (TL84/CWF) is the scenario where metamerism-induced artifacts are most concentrated. Typical manifestations include:

**Green-yellow cast:** The 546 nm green line of fluorescent lamps is strongly picked up by the camera G channel, and a D65-calibrated CCM cannot compensate for this. Green foliage and green backgrounds take on a yellow-green tint. Visually this creates a "stale" appearance, and is particularly objectionable in food photography.

**Skin hue shift toward green:** The red component in human skin tones (hemoglobin absorption trough near 540–580 nm) is amplified by the TL84 green line, combined with the camera's Luther deviation in that spectral region, causing skin tones to shift toward green on the a* axis — in severe cases the shift exceeds ΔE > 5.

**White point drift:** If AWB is based on a D65 white point model, its estimate under TL84 is inaccurate; the global white balance error compounds the CCM error, further worsening the color cast.

**Identification and diagnosis:** On a color difference vector plot, TL84-induced color casts appear as a systematic elevation in the green channel with most patches shifting along the +b* (yellow) axis; the shifts are consistent in direction, distinguishing them from random noise.

### 4.2 Color Distortion Under LED Lighting

The special spectral structure of LED lighting causes the following artifacts:

**Blue-violet distortion:** The 450 nm blue pump peak of LEDs corresponds to the region where the camera B channel is most sensitive, but also where the deviation from the CMF $\bar{z}(\lambda)$ is greatest. This causes saturation or hue errors in blue garments and sky blue; the common manifestation is "blue going purple" or "blue going green."

**Over-saturation of whites:** The yellow phosphor emission of warm white LEDs (2700–3000 K) causes white regions to appear warm after CCM processing, but this does not conform exactly to the CCM model for tungsten (illuminant A), leaving the result in an interpolation "gap" that causes white areas to appear orange.

**Flicker interaction:** The timing difference between high-frequency PWM-driven LEDs and the camera's rolling shutter can cause inter-frame color inconsistency, manifesting as color "stripes" or "banding" artifacts. In severe cases this requires joint handling with anti-banding algorithms.

### 4.3 Color Distortion from Special Materials

**Fluorescent (neon) colors:** Fluorescent yellow, fluorescent orange, and similar high-visibility colors (common in sportswear and safety vests) contain fluorescent dyes whose reflectance spectra show apparent reflectance exceeding 100% in certain bands (extra energy from fluorescent emission). The camera response to these colors far exceeds the linear range assumed by CCM, causing hue shifts and luminance clipping, typically manifesting as "fluorescent yellow becoming plain yellow with the fluorescent quality lost."

**Metallic colors:** Metallic paints (e.g., automotive metallic silver) have highly directional reflection (extremely narrow BRDF peak), and their spectral composition changes significantly with incident angle. A CCM calibrated as an average across angles cannot cover all angles; local hue shifts in highlight regions are common.

**Pearlescent and interference materials:** Pearlescent colors in cosmetics (e.g., color-shifting lip products) use thin-film interference to create structural colors that vary with angle. The spectral response changes dramatically with viewing angle; cameras typically capture the color at only one angle and cannot reproduce the "color-shifting" effect perceived by the human eye.

---

## §5 Evaluation

### 5.1 Multi-Illuminant ΔE00 Statistics

Multi-illuminant color accuracy evaluation is the core metric in ISP color quality reports. The following procedure is recommended:

**Test charts:**
- **Macbeth ColorChecker Classic (24 patches)**: mandatory; provides full color coverage and skin tones;
- **ColorChecker SG (140 patches)**: adds boundary colors and highly saturated patches;
- **X-Rite Flexi fluorescent chart** or **fluorescent color samples**: specifically for testing fluorescent material metamerism;
- **Custom special material charts**: targeted at scenarios relevant to the product (e.g., textiles, food, automotive).

**Evaluation metrics:**
$$\overline{\Delta E_{00}} = \frac{1}{N} \sum_{i=1}^{N} \Delta E_{00,i}$$

$$\Delta E_{00}^{P95} = \text{95th percentile of } \left\{\Delta E_{00,i}\right\}$$

Industry reference standards for consumer cameras: $\overline{\Delta E_{00}} < 3$ (good), $< 2$ (excellent); professional cameras target $< 1.5$.

### 5.2 Metamerism Index Calculation

For a specific pair of patches (e.g., a standard reference sample vs. an actual production sample), the metamerism index is calculated as follows:

1. Measure the tristimulus values of both samples under D65 and the test illuminant (A / TL84 / LED);
2. Confirm that $\Delta E_{00} < 0.5$ under D65 (called a "near match" or "engineering metameric pair");
3. Compute $\Delta E_{00}$ under the test illuminant; this is the MI for that illuminant;
4. Report multiple indices: MI_A (illuminant A MI), MI_TL84 (TL84 MI), etc.

Note: Strict metamerism requires $\Delta E = 0$ under the reference illuminant, but in engineering practice an "engineering metamerism" definition of $\Delta E < 1$ is acceptable to avoid introducing spurious MI values from calibration errors.

### 5.3 Special Material Chart Testing

For materials with high metamerism risk, a dedicated test chart is recommended containing the following categories:

| Category | Typical Samples | Test Focus |
|----------|-----------------|------------|
| Fluorescent colors | Fluorescent yellow/orange/pink samples | Effect of fluorescent emission on B channel |
| Metallic colors | Silver, gold, copper coatings | Directional reflection and CCM failure |
| FWA whites | FWA-containing white paper vs. ceramic white | FWA interference with AWB |
| Nanostructural colors | Color-shifting films, pearlescent pigments | Angular dependence |
| Special printing inks | Spot color (Pantone) prints | Print metamerism |

Each category of sample is shot under at least 3 illuminants (D65, TL84, LED BB). The cross-illuminant color shift vectors and ΔE00 are reported, forming a "metamerism risk matrix" as part of the product color quality record.

---

## §6 Code

The accompanying code for this chapter is available in: *See §6 Code section for runnable examples.*

The code includes:
- Simulation of metameric pair generation (searching for metameric pairs in the Munsell dataset);
- Tristimulus integration calculation (given spectral reflectance and illuminant data);
- Quantification of camera Luther condition violation (PCA residual analysis);
- Multi-illuminant ΔE00 evaluation script (input chart spectral data, output cross-illuminant color difference statistics table);
- CCM interpolation demonstration (comparison of color temperature interpolation vs. illuminant type classifier switching).

---

## References

1. **CIE 80:2001** — *Colorimetry of Self-Luminous Displays and Related Components*. CIE Publication 80, 2001. (Official CIE standard for metamerism index definition and measurement methods.)

2. **Finlayson, G. D., Drew, M. S., & Funt, B. V. (1994)** — "Spectral sharpening: sensor transformations for improved color constancy." *Journal of the Optical Society of America A*, 11(5), 1553–1563. (Foundational paper on spectral sharpening.)

3. **Hunt, R. W. G., & Pointer, M. R. (2011)** — *Measuring Colour* (4th ed.). Wiley. (Classic reference on color measurement; detailed coverage of metamerism.)

4. **Fairchild, M. D. (2013)** — *Color Appearance Models* (3rd ed.). Wiley-IS&T Series. (Comprehensive reference on color appearance models, observer metamerism, and chromatic adaptation transforms.)

5. **Vrhel, M. J., Gershon, R., & Iwan, L. S. (1994)** — "Measurement and analysis of object reflectance spectra." *Color Research & Application*, 19(1), 4–9. (Classic source for the Munsell spectral reflectance database.)

6. **Westland, S., Ripamonti, C., & Cheung, V. (2012)** — *Computational Colour Science Using MATLAB* (2nd ed.). Wiley-IS&T. (Provides engineering implementation references for multi-illuminant CCM optimization and metamerism evaluation; widely cited in the ISP engineering community.)

---

## §8 CIECAM02 Color Appearance Model

### 8.1 Why Color Appearance Models Are Needed

CIE XYZ and CIE Lab describe colors under **reference viewing conditions** (a specific illuminant and a specific background luminance level), but human color perception is influenced by additional factors: **adaptation state** (the degree to which the eye has adapted to the current illuminant), **background luminance** (relative brightness of the surrounding environment), and **color appearance mode** (object mode vs. illuminant mode). A Color Appearance Model (CAM) builds on tristimulus values to model these additional perceptual variables and predict the subjective color experience of an observer under specific viewing conditions.

For ISP engineers, the most direct application of CIECAM02 is **perceptual prediction for HDR images on smartphones**: the luminance range of an HDR scene (0.01–10000 cd/m²) far exceeds the design range of CIE Lab (approximately 1–1000 cd/m²), and Lab's uniformity breaks down at extreme luminance levels. CIECAM02 uses nonlinear compression and background luminance normalization to maintain better perceptual uniformity over a wider luminance range.

### 8.2 CIECAM02 Full Computation

CIECAM02 (CIE 159:2004) consists of the following five steps:

**Step 1: Von Kries Chromatic Adaptation Transform**

Convert tristimulus values $[X, Y, Z]$ to the HPE cone space $[L, M, S]$ (Huntington-Pointer-Estevez space, an approximation of human cone sensitivities):

$$\begin{pmatrix} L \\ M \\ S \end{pmatrix} = M_{\text{HPE}} \begin{pmatrix} X \\ Y \\ Z \end{pmatrix}$$

Then perform complete chromatic adaptation to the illuminant white point $[L_w, M_w, S_w]$, mapping the sample color to a reference white (D50 or D65):

$$L_c = \frac{L}{L_w} \cdot Y_w \cdot \frac{F_L}{100}, \quad M_c = \frac{M}{M_w} \cdot Y_w \cdot \frac{F_L}{100}, \quad S_c = \frac{S}{S_w} \cdot Y_w \cdot \frac{F_L}{100}$$

where $F_L$ is the luminance adaptation factor and $Y_w$ is the reference white luminance (typically normalized to 100). CIECAM02's chromatic adaptation is more accurate than CIE Lab's equal-energy illuminant assumption because the Von Kries transform is performed in cone space (diagonal matrix), more closely matching human eye physiology.

**Step 2: Non-linear Compression**

Simulates the nonlinear response of cone cells (including saturation at high stimulus intensities):

$$L_A' = \frac{400 \cdot (F_L L_c / 100)^{0.42}}{(F_L L_c / 100)^{0.42} + 27.13} + 0.1$$

$M_A'$ and $S_A'$ are computed analogously. This nonlinear compression function is approximately linear at low luminance and saturates at high luminance, mimicking the response characteristics of retinal photoreceptors (similar to the Michaelis-Menten equation).

**Step 3: Opponent Color Channels**

Compute achromatic and two opponent color channels from the compressed cone responses, simulating the color opponency (red-green, yellow-blue) mechanism of the visual system:

$$a = L_A' - 12 M_A' / 11 + S_A' / 11$$
$$b = (L_A' + M_A' - 2 S_A') / 9$$

Achromatic response:
$$A = \left(2 L_A' + M_A' + S_A'/20 - 0.305\right) \cdot N_{\text{BB}}$$

where $N_{\text{BB}}$ is a background luminance normalization coefficient.

**Step 4: Perceptual Attribute Computation**

Six perceptual attributes are derived from the opponent channels:

- **Lightness $J$**: $J = 100 \cdot \left(A / A_w\right)^{c z}$, where $c$ (0.69 for average surround), $z$, and $A_w$ are determined by viewing conditions;
- **Chroma $C$**: $C = t^{0.9} \cdot \sqrt{J/100} \cdot (1.64 - 0.29^n)^{0.73}$, where $t = \sqrt{a^2 + b^2} \cdot 50000 / (13 N_C)$;
- **Hue angle $h$**: $h = \arctan(b/a)$, range $[0°, 360°)$;
- **Hue quadrature $H$**: maps hue angle $h$ to a uniform hue scale of 0–400;
- **Brightness $Q$** (absolute perceptual luminance): $Q = (4/c) \cdot \sqrt{J/100} \cdot (A_w + 4) \cdot F_L^{0.25}$;
- **Colorfulness $M$** (absolute chroma sensation): $M = C \cdot F_L^{0.25}$.

In smartphone ISP the most commonly used attributes are $J$ (for luminance mapping), $C$ (for saturation control), and $h$ (for hue correction), forming the **JCh perceptually uniform color space**.

### 8.3 CIECAM02 vs. CIE Lab: Uniformity at Different Luminance Levels

CIE Lab was designed for a reference white of $Y_w = 100$ (approximately 1000 cd/m² display); when applied to HDR scenes with a wider luminance range, its uniformity degrades significantly:

| Luminance level (Y, cd/m²) | Lab $\Delta E_{00}$ uniformity | CIECAM02 $\Delta J$ uniformity | Remarks |
|----------------------------|---------------------------------|--------------------------------|---------|
| 5–100 (SDR normal range) | Good (within design range) | Good | Both comparable |
| 0.01–5 (deep shadows) | Poor ($L^*$ expands; spacing distorted) | Better (nonlinear compression compensates) | Lab uniformity poor at low luminance |
| 100–1000 (bright highlights) | Moderate | Better | Lab slightly under-compressed in highlights |
| 1000–10000 (HDR peak) | Poor ($L^*$ design ceiling ~100; out of range) | Good ($J$ designed to cover this range) | Lab cannot be used directly |

For HDR tone mapping in ISP, CIECAM02's $J$ channel provides a more uniform perceptual luminance scale than $L^*$, especially in the 0.01–5 cd/m² deep-shadow range (the typical luminance range of night-scene HDR). A $\Delta J = 1$ corresponds to an approximately constant perceptual difference, whereas $\Delta L^* = 1$ corresponds to a perceptual difference at this luminance level that is far larger than the same numerical difference in the highlight region.

---

## §9 CAM16 and ICtCp

### 9.1 CAM16: A Simplified Model for Engineering Applications

**CAM16 (Li et al., 2017)** is a simplified revision of CIECAM02, primarily correcting numerical instability at extremely high/low luminance levels and simplifying the chromatic adaptation transform matrix:

$$M_{\text{CAM16}} = \begin{pmatrix} 0.401288 & 0.650173 & -0.051461 \\ -0.250268 & 1.204414 & 0.045854 \\ -0.002079 & 0.048952 & 0.953127 \end{pmatrix}$$

**CAM16-UCS (Uniform Color Space)** is the companion perceptually uniform color space for CAM16, analogous to CIECAM02-UCS:

$$J' = \frac{(1+100 \cdot 0.007) J}{1 + 0.007 J}, \quad M' = \frac{\ln(1 + 0.0228 M)}{0.0228}$$

$$a_M = M' \cos h, \quad b_M = M' \sin h$$

The advantage of CAM16-UCS is that $J'$, $a_M$, $b_M$ form a near-Euclidean space where color differences can be approximated by Euclidean distance ($\Delta E_{CAM16} = \sqrt{\Delta J'^2 + \Delta a_M^2 + \Delta b_M^2}$), giving accuracy comparable to CIEDE2000 with simpler computation.

**Engineering applications:** CAM16 is widely used in HDR image quality assessment (IQA) and HDR tone mapping quality evaluation, and forms the basis of the color appearance model companion to the BT.2100 HDR standard. In HDR composite quality evaluation for smartphone ISP, CAM16-UCS color differences better reflect human observer perception of local color distortion in HDR images than Lab color differences.

### 9.2 ICtCp (ITU-R BT.2100): Designed for HDR/WCG

**ICtCp** is a color space designed by Dolby for HDR and Wide Color Gamut (WCG) displays, adopted by ITU-R BT.2100 as the perceptual color encoding standard for HDR video. The three components are:

- **I (Intensity)**: analogous to CIECAM02's $J$, but encoded using PQ (Perceptual Quantizer) or HLG (Hybrid Log-Gamma) nonlinear transfer functions, covering the full HDR luminance range of 0.0001–10000 cd/m²;
- **Ct (Tritan confusion, blue-yellow axis)**: corresponds to the human eye's blue-yellow opponent axis (Tritan axis, short-wavelength cone dominated);
- **Cp (Protan confusion, red-green axis)**: corresponds to the human eye's red-green opponent axis (Protan axis).

**Complete computation (PQ-encoded version):**

Starting from linear BT.2020 RGB:

$$\begin{pmatrix} L' \\ M' \\ S' \end{pmatrix} = M_1 \begin{pmatrix} R \\ G \\ B \end{pmatrix}$$

where $M_1$ is the chromaticity conversion matrix from BT.2020 to LMS (via CIE XYZ).

Apply PQ nonlinear compression to each LMS component (modeling the perceptual luminance response of the Barten model):

$$L^* = \text{PQ}(L') = \left(\frac{c_1 + c_2 (L'/L_p)^n}{1 + c_3 (L'/L_p)^n}\right)^m$$

where $c_1 = 0.8359375$, $c_2 = 18.8515625$, $c_3 = 18.6875$, $n = 0.15930176$, $m = 78.84375$, $L_p = 10000$ cd/m² (PQ standard peak luminance).

Then apply matrix $M_2$ to convert to ICtCp:

$$\begin{pmatrix} I \\ C_t \\ C_p \end{pmatrix} = M_2 \begin{pmatrix} L^* \\ M^* \\ S^* \end{pmatrix}$$

where $M_2 = \begin{pmatrix} 0.5 & 0.5 & 0 \\ 1.6137 & -3.3234 & 1.7097 \\ 4.3780 & -4.2455 & -0.1325 \end{pmatrix}$ (approximate values).

### 9.3 Advantages of ICtCp Over CIE Lab in ISP HDR Pipelines

| Comparison dimension | CIE Lab | ICtCp |
|----------------------|---------|-------|
| **Luminance range** | SDR (~0.1–1000 cd/m², design center ~100 cd/m²) | HDR (0.0001–10000 cd/m², full HDR range) |
| **Color uniformity** | Uniform within SDR; fails at HDR extremes | Better uniformity across full HDR range |
| **Luminance-chroma separation** | Partial ($L^*$ has residual correlation with $a^*, b^*$) | $I$ nearly orthogonal to $C_t, C_p$ (a design goal of ICtCp) |
| **Color difference computation** | Requires CIEDE2000 (complex formula) | Euclidean distance is a good approximation (simpler) |
| **HDR video standard** | Not a standard HDR color space | Officially specified by ITU-R BT.2100 |
| **ISP hardware support** | Widely available (existing chip IP) | Growing; some DSPs already include PQ conversion IP |

**Practical ISP applications:**

- **HDR tone mapping lightness operations**: performing luminance mapping in ICtCp's $I$ channel rather than in $L^*$ produces less color shift in highlights, because $I$ is more orthogonal to $C_t, C_p$;
- **HDR composite quality evaluation**: after multi-frame HDR merging, computing color differences in ICtCp space better predicts human observer perception of merge artifacts on HDR displays than Lab color differences;
- **WCG (P3/BT.2020) color correction**: ICtCp is natively based on BT.2020 primaries and supports wide color gamut; Lab is based on the sRGB primaries under D65/D50 and requires additional conversion for WCG.

---

## §10 Engineering Impact of Metamerism in ISP

### 10.1 Quantitative Analysis of CCM Failure Across Illuminants

Section §1 explained the mechanism of D65-CCM failure under fluorescent lighting at a theoretical level. This section provides a more precise mathematical analysis to help engineers understand the magnitude of failure and determine the necessity of a multi-CCM strategy.

**CCM failure from a linear algebra perspective:**

Let the camera sensor sensitivity be $Q = [q_1, q_2, q_3]^T \in \mathbb{R}^{3 \times \Lambda}$ (where $\Lambda$ is the number of wavelength samples), the ideal CMF be $\bar{F} = [\bar{x}, \bar{y}, \bar{z}]^T \in \mathbb{R}^{3 \times \Lambda}$, and the CCM $M^* \in \mathbb{R}^{3 \times 3}$ satisfy:

$$M^* Q \mathbf{r} \approx \bar{F} \mathbf{r} \quad \forall \mathbf{r} \in \mathcal{R}$$

where $\mathbf{r} \in \mathbb{R}^\Lambda$ is the reflectance spectrum and $\mathcal{R}$ is the effective reflectance space under the training illuminant.

When the illuminant switches from $E_1$ (D65) to $E_2$ (TL84), the equivalent reflectance $\mathbf{r}^{E_1} = E_1 \odot \mathbf{r}$ becomes $\mathbf{r}^{E_2} = E_2 \odot \mathbf{r}$. The difference vector $\Delta \mathbf{r} = E_2 \odot \mathbf{r} - E_1 \odot \mathbf{r}$ lies outside the null space of the D65-CCM, and therefore:

$$M^* Q (E_2 \odot \mathbf{r}) \neq \bar{F} (E_2 \odot \mathbf{r})$$

The magnitude of failure depends on the size of the component of $\Delta \mathbf{r}$ that lies outside the CCM training space.

**Typical failure magnitudes (Macbeth ColorChecker 24 patches, D65 CCM applied to TL84 test):**

| Patch type | $\Delta E_{00}$ under D65 | $\Delta E_{00}$ under TL84 | Metamerism Index MI |
|------------|---------------------------|----------------------------|---------------------|
| Neutral gray (patches 19–24) | 1.2 | 2.8 | 1.6 |
| Red (patch 15) | 1.5 | 5.2 | 3.7 |
| Green (patch 14) | 1.8 | 6.8 | 5.0 |
| Skin tone (patch 6) | 1.3 | 4.1 | 2.8 |
| Blue (patch 13) | 2.0 | 4.9 | 2.9 |

Green and red patches exhibit severe metamerism (MI > 3) under TL84 — directly corresponding to the green bias and green skin tones commonly observed under fluorescent lighting. A multi-CCM strategy can reduce these MI values to below 2.

### 10.2 Luther Error Quantification for Camera QE Curves vs. CIE 1931 CMF

**Quantum Efficiency (QE)** curves describe the sensor's photon-to-electron conversion ratio at each wavelength, and are equivalent (up to a calibration constant) to the spectral sensitivity.

**Quantification method:**

1. Measure the target sensor's QE curves $[Q_R(\lambda), Q_G(\lambda), Q_B(\lambda)]$ (wavelength step 5–10 nm, range 380–780 nm);
2. Orthogonally project the QE curves onto the three-dimensional subspace spanned by the CIE CMFs and compute the residual:

$$\epsilon_i = Q_i(\lambda) - \text{Proj}_{\text{CMF}}[Q_i(\lambda)], \quad i = R, G, B$$

3. Quantify the degree of Luther condition violation using the $\ell_2$ norm of the residual relative to the QE curve norm:

$$\text{Luther Error}_i = \frac{\|\epsilon_i\|_2}{\|Q_i\|_2}$$

**Typical Luther Error magnitudes for mainstream smartphone sensors (2024, approximate values):**

| Sensor type | $\text{Luther Error}_R$ | $\text{Luther Error}_G$ | $\text{Luther Error}_B$ |
|-------------|------------------------|------------------------|------------------------|
| Sony IMX989 (1 inch) | ~0.18 | ~0.12 | ~0.21 |
| Samsung GN2 (1/1.12 inch) | ~0.22 | ~0.14 | ~0.25 |
| Ideal colorimetric camera | 0 | 0 | 0 |
| Human visual system (CIE 1931) | 0 (by definition) | 0 (by definition) | 0 (by definition) |

A larger Luther Error indicates a larger cross-illuminant color error that cannot be corrected by a single linear CCM. The B channel error is typically the largest, because the spectral width of the blue CFA dye differs most from $\bar{z}(\lambda)$: $\bar{z}(\lambda)$ has a sharp single peak near 450 nm, while commercial blue dyes typically have a broader bell-shaped distribution.

---

## §11 Standard Observer Limitations and Individual Variation

### 11.1 Age Bias of the CIE 1931 2° Observer

The CIE 1931 standard observer was derived from experiments with approximately 17 young observers (Wright: 10 subjects, Guild: 7 subjects; most aged 20–30) conducted in the 1920s–1930s, and carries known systematic biases.

**Lens yellowing:** Short-wavelength absorption by the human eye's crystalline lens increases with age (lens protein accumulation enhances absorption near 400–450 nm — "lens yellowing"):

| Age group | Short-wave (400–450 nm) effective transmittance | Effect on blue perception |
|-----------|--------------------------------------------------|--------------------------|
| 20–30 (CIE 1931 baseline) | 100% (baseline) | Baseline |
| 40–50 | ~80% | Slight reduction in blue perception |
| 60–70 | ~55% | Noticeably reduced blue; whites appear slightly yellow |
| 80+ | ~35% | Severe impact on short-wavelength perception |

**Engineering consequence:** An ISP color pipeline designed for the CIE 1931 2° standard observer is optimal for young observers. For products targeting older user demographics, the observer age distribution can be incorporated as a weighting factor during color tuning — slightly reducing the blue-enhancement amount — to improve color experience satisfaction for middle-aged and older users.

### 11.2 CIE 1964 10° Observer

The **CIE 1964 Supplementary Standard Colorimetric Observer** is based on a larger sample (~50 observers) and a 10° visual field (fovea + para-foveal region):

- **Larger visual field**: 10° more closely corresponds to normal viewing (e.g., the angle subtended by a photograph at typical viewing distance), whereas 2° corresponds to only about 3.5 cm at 1 m;
- **Stiles-Burch experiments**: the 10° observer's color matching experiments (Stiles & Burch, 1959) used a larger sample, reducing the sampling bias of the 2° observer;
- **Blue end differences**: the 10° CMF's $\bar{z}(\lambda)$ is higher at 400–450 nm than the 2° CMF (the para-foveal region has no macular pigment and absorbs less blue light);
- **Red end differences**: the 10° CMF's $\bar{x}(\lambda)$ at 620–700 nm is slightly higher than the 2° CMF.

**Practical selection for ISP engineering:**
- **Color calibration (CCM)**: typically uses the 2° observer (international standard);
- **Subjective IQA experiments**: if test images fill the entire screen (> 10° visual angle), use the 10° observer to compute reference colors to avoid systematic bias;
- **Display colorimetry**: DCI-P3 and sRGB standards are based on the 2° observer, but for close-up viewing of a large TV screen (> 10° visual angle), the 10° observer is more appropriate.

---

## §12 Color Constancy Algorithm Principles

### 12.1 Physical and Mathematical Foundations of Color Constancy

**Color constancy** refers to the human visual system's ability to perceive the surface color of objects as stable despite changes in illuminant — a white piece of paper "looks" white under both daylight and incandescent light, even though the spectral distribution reaching the retina is completely different.

**Diagonal model of illuminant change:**

Under the linear approximation of Von Kries adaptation theory, when the illuminant changes from $E_1$ to $E_2$, the change in camera RGB output is approximately a **diagonal matrix transform** (multiplicative white balance gains):

$$\begin{pmatrix} R_2 \\ G_2 \\ B_2 \end{pmatrix} \approx \begin{pmatrix} k_R & 0 & 0 \\ 0 & k_G & 0 \\ 0 & 0 & k_B \end{pmatrix} \begin{pmatrix} R_1 \\ G_1 \\ B_1 \end{pmatrix}$$

where $k_R, k_G, k_B$ are diagonal gains depending on the relative SPDs of $E_1$ and $E_2$. This approximation holds when: (1) the sensor response functions are sufficiently narrow-band; (2) surface reflectances are Lambertian; and (3) the illuminant is spatially uniform.

**AWB implication:** The essence of AWB is to estimate the current illuminant's $(k_R, k_G, k_B)$ and normalize it (so that a white object's RGB output ratio is $1:1:1$), thereby executing a linear approximation of color constancy. This is the mathematical foundation of the AWB algorithms in Part 2, Chapter 5.

**Limitations of the diagonal model:**

Real imaging does not satisfy the diagonal model assumptions:
- Broadband sensor response (Bayer filter broadband): illuminant change is not perfectly equivalent to a diagonal multiplication; higher-order error terms exist;
- Spectral nonlinearities in reflectance: some materials (fluorescent, metallic) exhibit directional reflection or fluorescent emission, violating the linear Lambertian assumption;
- Multi-illuminant scenes: different scene regions have different illuminants, which a single diagonal matrix cannot describe (requiring zone-based AWB).

Experiments show that prediction error of the diagonal model on standard natural spectrum datasets (e.g., Munsell charts) is approximately 5–10% (angular error), which is also the typical residual error order of magnitude for most AWB algorithms.

### 12.2 From Neuroscience to Engineering Algorithms

Color constancy algorithms draw extensively from neuroscience research on the color adaptation mechanisms of the visual system:

**Land's Retinex theory (1971):** Edwin Land proposed Retinex (Retina + Cortex): the visual system infers color by analyzing the relative luminance ratios across different scene regions, rather than absolute luminance values. Retinex algorithms segment the scene into regions, compute each region's reflectance (by dividing out an estimated local illuminance), and achieve color constancy.

**Gray World Assumption:** Assumes that the average of all colors in a natural scene is close to neutral gray ($\bar{R} = \bar{G} = \bar{B}$). When the scene mean deviates from gray, the illuminant has a color cast; normalizing gains to bring the mean back to gray corrects it. This is the simplest color constancy algorithm and works reasonably well for color-diverse natural scenes, but fails when the color distribution is skewed (an entirely green forest, an entirely red brick wall).

**White Patch Retinex:** Assumes the brightest region in the scene corresponds to a white reflector; uses the brightest-region RGB as the illuminant estimate and normalizes it to white. Works well for highly saturated scenes, but produces severe errors when no true white region exists (e.g., a nighttime blue-toned scene).

**Learning-based methods:** Neural networks trained to predict illuminant color from RAW images — representative approaches include SqueezeNet-AWB and C4 (Cross-Channel Covariance). On multi-camera datasets such as NUS 8-Camera and Cube+, the angular error reaches 1.5°–2.0°, significantly outperforming traditional algorithms (~3°–5°).

**Partial adaptation in ISP:** The human eye under a new illuminant does not fully adapt to neutral white but retains a partial "memory" of the original illuminant color temperature. This effect was quantitatively modeled by Fairchild (1996). The corresponding ISP practice is to not push white balance gains all the way to $1:1:1$, but to retain part of the illuminant color (leaving warm scenes with a warm tone), matching user expectations of "naturalness." A typical implementation linearly interpolates between the full white balance gain $k$ and the identity:

$$k_{\text{applied}} = (1 - \alpha) \cdot \mathbf{1} + \alpha \cdot k_{\text{full}}, \quad \alpha \in [0.7, 0.9]$$

---

## §13 Extended References

[7] Li, C. et al. (2017). Comprehensive colour appearance model (CIECAM16). *Color Research & Application*, 42(6), 703–718. — CAM16 original paper.

[8] Lu, A. et al. (2017). ICtCp colour space and its compression performance for high dynamic range and wide colour gamut imagery. *SMPTE Motion Imaging Journal*. — Original design paper for ICtCp.

[9] ITU-R BT.2100 (2018). Image parameter values for high dynamic range television for use in production and international programme exchange. — HDR standard specification incorporating ICtCp.

[10] Fairchild, M. D. (1996). Considering the "Surround" in CIECAM97s. *Color Research & Application*, 21(5), 371–377. — Partial adaptation theory in chromatic adaptation models.

[11] Land, E. H. (1971). Lightness and Retinex theory. *Journal of the Optical Society of America*, 61, 1–11. — Original paper on Retinex color constancy.

[12] CIE 159:2004 — A Colour Appearance Model for Colour Management Systems: CIECAM02. — Complete CIECAM02 specification.

[13] Stiles, W. S. & Burch, J. M. (1959). NPL Colour-matching Investigation: Final Report. *Optica Acta*, 6(1), 1–26. — Experimental data source for the CIE 1964 10° observer.

---

## §8 Glossary

**Metamerism**
The phenomenon in which color stimuli with different spectral distributions produce identical color perception under certain conditions. The root cause is that the human eye has only three types of cone cells (L, M, S), compressing an entire spectral curve into three scalar response values — the irreversible dimensionality reduction makes many-to-one mapping inevitable. Two metameric stimuli have equal tristimulus values under one illuminant but may produce significant color differences under another. This is the central challenge driving multi-illuminant CCM design and AWB robustness in ISP pipelines.

**Tristimulus Values (XYZ)**
The three scalar values defined by CIE 1931 to describe color: $X = k\int E(\lambda)R(\lambda)\bar{x}(\lambda)\,d\lambda$, with $Y$ and $Z$ defined analogously. Together, $X$, $Y$, $Z$ fully determine the color perceived by the human eye (under the CIE standard observer assumption). The $Y$ component equals the photometric quantity (luminance/reflectance); $\bar{y}(\lambda)$ is the CIE spectral luminous efficiency function $V(\lambda)$. After normalization, $Y=100$ corresponds to the reference white.

**Color Matching Functions (CMF)**
The spectral sensitivity functions $\bar{x}(\lambda)$, $\bar{y}(\lambda)$, $\bar{z}(\lambda)$ of the CIE standard observer, describing the amounts of three primary stimuli needed to match each wavelength of monochromatic light at a 2° (CIE 1931) or 10° (CIE 1964) visual field. CMFs are the fundamental mathematical tools of color science. The physical meaning of CCM is to apply a linear transform to the sensor response to approximate the linear relationship defined by the CMFs.

**Metamerism Index (MI)**
A metric quantifying the color difference of a metameric pair after an illuminant change: the CIEDE2000 color difference $\Delta E_{00}$ between two surfaces that match exactly under reference illuminant $E_1$ (typically D65) after switching to test illuminant $E_2$ (A, TL84, LED, etc.). A larger MI indicates greater spectral differences and higher sensitivity to illuminant changes. MI < 1 is mild, 1–3 moderate, >3 severe (industry experience values; the CIE standard does not prescribe universal threshold criteria).

**Luther Condition (Luther-Ives Condition)**
If the spectral sensitivities $q_i(\lambda)$ of a camera sensor are linear combinations of the CIE color matching functions, the sensor satisfies the Luther condition. A camera satisfying this condition yields tristimulus values consistent with human vision for any spectrum and can recover colors perfectly by multiplying by a fixed matrix. Real CMOS sensors fail to satisfy the Luther condition due to CFA dyes, the IRCF, and other factors — this is the fundamental reason CCM exists and why cross-illuminant color errors cannot be completely eliminated.

**Spectral Sharpening**
A method proposed by Finlayson et al. (1994) that applies a linear transform $A$ to the camera's native RGB to make the transformed sensitivity shapes more closely resemble the CIE CMFs (i.e., narrowing spectral overlap between channels), thereby reducing Luther deviation. The cost is that the matrix $A$ typically contains negative weights, significantly reducing SNR. Direct application of spectral sharpening is rare in actual ISP engineering; the more common approach is multi-CCM with scene-adaptive switching, accepting some metameric error in exchange for photographic performance.

**Illuminant Metamerism**
The phenomenon where two objects match in color under one illuminant but do not match under another. This is the type most commonly encountered by ISP engineers: D65-calibrated CCM fails under TL84 fluorescent lighting, causing green tones to shift toward yellow and skin tones to go green. The root cause is that the two objects have different spectral reflectance curves, so the weighted integrals change when the illuminant spectrum changes. Multi-illuminant CCM strategy is the primary engineering countermeasure.

**Observer Metamerism**
Individual variation in cone cell spectral sensitivities among different people (shifts in photopigment peak wavelengths, macular pigment density, lens absorption, etc.) means two observers may disagree on whether a given color pair matches. The CIE 1931 standard observer is an average derived from data collected by Wright (10 subjects) and Guild (7 subjects), and serves as the unified reference for colorimetry. ISP pipelines are typically designed only for the standard observer, without explicitly addressing individual differences.

**Device Metamerism**
Color mismatch caused by the difference in spectral sensitivities between camera sensors and human vision (Luther condition not satisfied): the camera is aligned with human vision via CCM under one illuminant, but errors reappear when the illuminant changes. This is an inherent, unresolvable error source in ISP color management that cannot be fully eliminated by linear transforms; the nonlinear correction capability of 3D-LUT can partially compensate for this limitation.

**Multi-Illuminant CCM**
A strategy of calibrating separate CCMs under multiple standard illuminants (A, D50, D65, TL84, CWF, LED, etc.) and obtaining an effective CCM by color temperature interpolation (recommended on the Mired scale or in the CIE 1960 uv chromaticity diagram) after AWB estimates the current color temperature. For non-blackbody illuminants such as TL84 and LEDs, color temperature interpolation alone is insufficient; an illuminant type classifier must be introduced to force switching to a dedicated CCM, eliminating the systematic color cast caused by spectral composition differences.

**TL84 (CIE F11 Standard Illuminant)**
A tri-phosphor fluorescent lamp commonly used in European retail, with a correlated color temperature of approximately 4000 K. Its spectrum is a superposition of mercury discharge lines and rare-earth phosphor emission bands: the **546.1 nm** mercury green line (line spectrum) and the **~611 nm** red phosphor (Eu³⁺:Y₂O₃) emission peak (broadband) — the two have different physical mechanisms. These two peaks are the key bands that cause the greatest deviation between the camera G and R channels and the human eye, making CCM most prone to failure.

**Fluorescent Whitening Agent (FWA; also Optical Brightening Agent, OBA)**
Organic fluorescent compounds widely present in white paper, white fabrics, and detergents. They absorb near-UV light (excitation peak ~340–380 nm) and emit in the blue-violet region (emission band ~420–470 nm, peak typically at 430–450 nm), visually making white appear "whiter and bluer." If a camera sensor has residual response to UV/near-UV, the B channel of FWA-treated objects will be abnormally enhanced, interfering with AWB estimation and causing warm compensation that shifts the overall image tone toward yellow.

**Spectral Reflectance ($R(\lambda)$)**
Describes the ratio at which an object's surface reflects light at each wavelength (range 0–1; materials with fluorescent emission may exhibit apparent reflectance exceeding 1); it is the physical carrier of color. Metamerism is fundamentally two different $R(\lambda)$ curves producing the same tristimulus values under a specific illuminant–observer combination. Precise color management requires spectral data, not merely tristimulus values.

**3D-LUT (Three-Dimensional Look-Up Table)**
A nonlinear color mapping tool that divides the input color space (e.g., R, G, B) into a uniform three-dimensional grid, stores target color values at each node, and processes inter-node values by trilinear interpolation. Typical specification: 17×17×17 nodes. A 3D-LUT can independently correct any region of the color space, compensating for metameric residuals and saturated-color bias that a 3×3 linear CCM cannot address. It is an important nonlinear complement to linear CCM in the ISP color management pipeline.
