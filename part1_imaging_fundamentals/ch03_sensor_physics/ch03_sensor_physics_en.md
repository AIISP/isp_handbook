# Part 1, Chapter 03: Image Sensor Physics

> **Pipeline position:** The sensor is the data source of the ISP pipeline; understanding sensor physics is a prerequisite for correct parameter tuning
> **Prerequisites:** Chapter 02 (Optics Basics)
> **Reader path:** Algorithm engineers, system engineers, tuning engineers

---

## §1 Theory

### 1.1 Photoelectric Conversion: From Photons to Electrons

#### 1.1.1 Fundamentals of the Photoelectric Effect

Modern image sensors are based on the **Internal Photoelectric Effect**: valence-band electrons in a silicon crystal absorb photon energy and are excited into the conduction band, generating a free electron-hole pair.

The photon energy must satisfy:

$$E_\text{photon} = \frac{hc}{\lambda} \geq E_g(\text{Si}) \approx 1.12 \text{ eV}$$

Where:
- $h = 6.626 \times 10^{-34}$ J·s (Planck's constant)
- $c = 3 \times 10^8$ m/s (speed of light)
- $\lambda$ is the photon wavelength
- $E_g(\text{Si}) = 1.12$ eV (silicon bandgap energy, corresponding to a cutoff wavelength of ≈ 1100 nm)

**Spectral response range:** Silicon sensors respond from 300 nm (near-UV) to 1100 nm (near-IR), with the visible range (400–700 nm) falling within the peak response region.

#### 1.1.2 Quantum Efficiency (QE)

**Quantum Efficiency** is defined as the number of electrons generated per incident photon:

$$\text{QE}(\lambda) = \frac{\text{number of electrons generated}}{\text{number of incident photons}}$$

QE curves for practical CMOS sensors:
- Green channel (~550 nm) peak QE: BSI sensors can reach 70–80%
- Blue channel (~450 nm) QE is limited by surface recombination: FSI ≈ 30–40%, BSI improved to 50–60%
- Near-IR (700–850 nm) QE gradually decreases; an IR-cut filter is required to block this range

#### 1.1.3 Full Well Capacity (FWC)

The maximum charge that can accumulate in a single pixel (number of electrons) is called the **Full Well Capacity**:

$$\text{FWC} \propto C_\text{FD} \cdot V_\text{swing}$$

Where $C_\text{FD}$ is the Floating Diffusion node capacitance and $V_\text{swing}$ is the voltage swing.

| Pixel Size | Typical FWC | Typical Application |
|-----------|------------|-------------------|
| 1.0 μm  | 4,000–6,000 e⁻  | Ultra-high-resolution mobile sensors (200MP) |
| 1.4 μm  | 8,000–12,000 e⁻ | Mainstream mobile main camera (1/1.3"–1/1.5" format) |
| 2.4 μm  | 20,000–30,000 e⁻| Professional cameras / security cameras |
| 4.0 μm  | 50,000–80,000 e⁻| Industrial cameras / scientific instruments |

**FWC directly determines the upper limit of dynamic range:** A larger FWC permits higher SNR and greater dynamic range (DR = 20 · log₁₀(FWC / dark noise) dB).

---

### 1.2 CMOS Pixel Architecture

#### 1.2.1 4T Pixel (Four-Transistor Pixel)

Modern CMOS image sensors almost universally employ the **4T pixel architecture** (4-Transistor Pixel), which consists of:

```
Photon
  ↓
┌─────────────────┐
│  Photodiode (PPD) │  ← Photoelectric conversion, charge accumulation
└────────┬────────┘
         │ TX (Transfer Gate)
         ↓
┌─────────────────┐
│  Floating Diffusion (FD)   │  ← Charge-to-voltage conversion node (C_FD)
└────────┬────────┘
         │
     ┌───┴───┐
     │  RST  │  ← Reset transistor (clears FD)
     └───────┘
         │
     ┌───┴───┐
     │  SF   │  ← Source follower (impedance conversion, voltage buffer)
     └───────┘
         │
     ┌───┴───┐
     │  SEL  │  ← Row select transistor (column line addressing)
     └───────┘
         ↓
      Column readout line
```

**Key advantage of 4T:** Uses a **Pinned Photodiode (PPD)** combined with Correlated Double Sampling (CDS), which significantly suppresses reset noise (kTC noise) and is the foundation for achieving low readout noise.

**Correlated Double Sampling (CDS) noise suppression:**

$$V_\text{signal} = V_\text{reset} - V_\text{data}$$

By reading the difference between the reset level and the signal level, the common kTC noise term is cancelled, reducing readout noise to as low as 1–3 e⁻ RMS.

#### 1.2.2 Conversion Gain (CG)

Conversion gain is defined as the voltage change per electron:

$$\text{CG} = \frac{q}{C_\text{FD}} \quad [\text{μV/e}^-]$$

Where $q = 1.602 \times 10^{-19}$ C (electron charge) and $C_\text{FD}$ is the floating diffusion capacitance.

- **High Conversion Gain (High CG):** Smaller $C_\text{FD}$, each electron produces a larger voltage → lower readout noise, suitable for low-light photography
- **Low Conversion Gain (Low CG):** Larger $C_\text{FD}$, larger FWC → better highlight detail, wider dynamic range

High-end modern sensors (e.g., Sony IMX989) support **Dual Conversion Gain (DCG)** switching: switch to High CG in low light, switch to Low CG in bright light, balancing both ends.

---

### 1.3 FSI vs BSI: Two Sensor Architectures

#### 1.3.1 Front-Side Illumination (FSI)

```
Photon ↓ ↓ ↓
───────────────────
Metal interconnect layers (M1/M2/M3) ← Block part of the incident light
───────────────────
Silicon substrate (photodiode)
───────────────────
```

**Advantages:** Mature process, lower cost
**Disadvantages:** Metal interconnect layers block incident light, poor blue-channel QE, difficult to scale down pixel size

#### 1.3.2 Back-Side Illumination (BSI)

```
Photon ↓ ↓ ↓
───────────────────
Silicon substrate (photodiode) ← Light enters photodiode directly
───────────────────
Metal interconnect layers (M1/M2/M3) ← Moved to the bottom, no light blocking
───────────────────
```

**Advantages:** Significantly improved QE (especially in the blue channel), dramatically better low-light performance
**Disadvantages:** More complex process (requires wafer bonding), higher cost

**Sony Exmor R (first BSI release in 2009)** was a milestone in the transition of mobile sensors from FSI to BSI. Reference:
https://www.sony-semicon.com/en/technology/mobile/exmor-r.html

#### 1.3.3 Stacked CMOS

Stacked CMOS is a further evolution of BSI, fabricating the **pixel layer** and **logic/ISP layer** separately and then bonding them together:

```
Photon ↓
─────────────────────────────
Pixel die (Top Die): Photodiode + pixel circuit
─────────────────────────────  ← Cu-Cu Bonding
Logic die (Bottom Die): ADC + DRAM / ISP circuit
─────────────────────────────
```

**Advantages:**
- Pixel layer uses a process optimized for photoelectric conversion (90 nm or above)
- Logic layer uses an advanced logic process (28 nm / 16 nm), improving ADC speed and ISP compute
- DRAM can be integrated in the logic layer (e.g., Sony IMX586's DRAM layer), enabling ultra-high-speed readout (960fps slow motion)

Representative products:
- **Sony IMX989** (1-inch, 2022): https://www.sony-semicon.com/en/products/is/mobile/imx989.html
- **Samsung ISOCELL HP2** (200MP, 2023): https://semiconductor.samsung.com/us/consumer-storage/internal-ssd/

---

### 1.4 Pixel Array Readout Modes

#### 1.4.1 Rolling Shutter vs Global Shutter

| Feature | Rolling Shutter (RS) | Global Shutter (GS) |
|---------|---------------------|---------------------|
| **Operation** | Row-by-row exposure; exposure start times are not synchronized across rows | All pixels expose simultaneously |
| **Jello Effect** | Present (image distortion when camera/subject moves rapidly) | Absent |
| **Flash compatibility** | Poor (requires electronic front curtain) | Good |
| **Pixel complexity** | Low (4T is sufficient) | High (requires additional storage capacitor, typically 6T or 7T) |
| **FWC / Dark noise** | Better | FWC decreases due to storage capacitor; dark noise slightly higher |
| **Typical applications** | Virtually all mobile cameras | Industrial cameras, drones (anti-jello), some flagship phones (OPPO Find X7) |

**Cause of the jello effect:** A rolling shutter takes several milliseconds to scan from the first row to the last (approximately 10–30 ms for a 1080p sensor). When the camera pans quickly, the exposure moments of the top and bottom rows differ, causing vertical lines to tilt diagonally.

#### 1.4.2 Column-Parallel ADC

Modern CMOS sensors assign one ADC per column (Column-Parallel ADC). N columns perform analog-to-digital conversion simultaneously; readout time is proportional to the number of pixel rows and independent of the number of columns.

Typical ADC scheme: **Ramp / Single-Slope ADC**

```
Reference ramp voltage V_ramp(t) = V_start - k·t

Comparator: when V_pixel > V_ramp(t), output toggles → record counter value N
Digital output: N = (V_pixel - V_start) / k  → ADC code
```

Precision: 10–14 bit per column ADC; speed: Multi-Slope ADC can achieve 14 bit @ 100 MHz clock.

---

### 1.5 Sensor Specification Framework

#### 1.5.1 Optical Format

Sensor size is described using a "fraction-of-an-inch" format (a legacy from the vidicon tube era); the actual diagonal is approximately 2/3 of the nominal value:

| Format Designation | Actual Diagonal | Typical Resolution | Representative Product |
|-------------------|----------------|-------------------|----------------------|
| 1/4"    | 4.0 mm   | 8MP      | Low-end mobile front camera |
| 1/2.8"  | 6.3 mm   | 50MP     | Mid-range mobile main camera |
| 1/1.56" | 11.2 mm  | 50MP     | Flagship main camera (Samsung GN2) |
| 1/1.28" | 13.8 mm  | 50MP     | Large-sensor flagship (Sony IMX989 predecessor) |
| 1"      | 16 mm    | 50.3MP   | Sony IMX989 (Xiaomi 13 Ultra) |

#### 1.5.2 Pixel Size and Quad-Bayer Pixel Binning

Mobile sensor pixel sizes are typically 0.7–1.4 μm. Used individually, the SNR is low, so in practice **Pixel Binning** is employed:

- **Quad-Bayer (4-in-1):** 4 × 0.7 μm pixels merged into one equivalent 1.4 μm pixel; FWC ×4, SNR theoretically improves by 6 dB
- **Nona-Bayer (9-in-1):** 9 pixels merged; common in 108MP/200MP sensors (Samsung ISOCELL HM series)

SNR improvement after binning (in the photon shot-noise-dominated regime):

$$\text{SNR}_\text{bin} = \sqrt{N} \cdot \text{SNR}_\text{single}$$

For $N = 4$ (Quad), SNR improves by 6 dB; for $N = 9$, it improves by 9.5 dB.

#### 1.5.3 Dynamic Range (DR)

$$\text{DR} = 20 \cdot \log_{10}\left(\frac{\text{FWC}}{\sigma_\text{dark}}\right) \quad [\text{dB}]$$

Where $\sigma_\text{dark}$ is the equivalent readout noise (in electrons).

| Sensor Type | Typical DR |
|------------|-----------|
| Low-end mobile (1/4", FSI) | 55–60 dB (approx. 9–10 EV) |
| Flagship mobile (1/1.3", BSI Stacked) | 70–75 dB (approx. 12–13 EV) |
| Full-frame camera (Sony A7 series) | 80–85 dB (approx. 14–15 EV) |
| Professional cinema camera (ARRI ALEXA 35) | 93 dB (approx. 17 EV) |

---

### 1.6 Color Filter Array (CFA) and Micro-Lens Array

#### 1.6.1 Bayer CFA

Standard Bayer array (invented by Bryce Bayer in 1976; patent expired):

```
R  Gr R  Gr
Gb B  Gb B
R  Gr R  Gr
Gb B  Gb B
```

G pixels occupy 50% (the human eye is most sensitive to green), while R and B each occupy 25%. Gr and Gb each occupy half of their respective rows/columns; theoretically they should be equal. The difference between them (Gr-Gb Imbalance) is one of the defects that the ISP must correct.

#### 1.6.2 RYYB (Huawei Kirin Sensor)

The RYYB array co-developed by Huawei and Sony (first introduced in the Huawei P30 Pro, 2019):

```
R  Y  R  Y
Y  B  Y  B
```

Yellow (Y = R+G, transmitting both red and green light) replaces some of the green pixels in the Bayer pattern, allowing more photons to pass through. The theoretical increase in light intake is approximately 40%.

**Trade-off:** Demosaicing is more complex — the yellow channel contains R+G aliasing, which is difficult to decouple, and color accuracy degrades in low light. See Chapter 19 (Demosaicing) §7 Special CFA section for details.

#### 1.6.3 Micro-Lens Array (MLA)

A micro-convex lens is placed above each pixel to focus incident light onto the center of the photodiode, reducing optical crosstalk and angular sensitivity in peripheral pixels.

Micro-lens design must be matched to the lens **Chief Ray Angle (CRA)**:
- Center pixels: CRA ≈ 0°, symmetric micro-lens design
- Edge pixels: CRA can reach 15–25°; the micro-lens must use an **off-center design**, tilted toward the lens optical axis

CRA mismatch causes color shift and brightness reduction at the image edges. When selecting a camera module, the sensor CRA curve must be verified against the lens CRA curve to ensure compatibility.

---

### 1.7 Overview of Sensor Noise Sources

(Detailed analysis in Chapter 04; a summary is provided here)

| Noise Type | Physical Origin | Characteristics | Primary Impact |
|-----------|----------------|----------------|---------------|
| **Photon Shot Noise** | Quantum statistical fluctuation in photon arrival | $\sigma = \sqrt{N_\text{photon}}$, Poisson distribution | Neutral noise in highlights; cannot be eliminated |
| **Readout Noise** | Amplifier thermal noise + ADC quantization noise | Fixed value (1–5 e⁻), signal-independent | Dominant noise in the shadows |
| **Dark Current Noise** | Thermally generated electron-hole pairs | Increases exponentially with temperature; significant in long exposures | Hot pixels, tonal drift |
| **Fixed Pattern Noise (FPN)** | Process variation in pixel/column amplifiers | Spatially fixed; repeatable frame-to-frame | Streaks, pixel non-uniformity |
| **Photo Response Non-Uniformity (PRNU)** | Spatial variation in QE / micro-lens | Multiplicative noise (scales proportionally with signal) | Fixed texture visible in bright scenes |

---

## §2 Calibration

### 2.1 Dark Frame Calibration

**Purpose:** Measure the baseline characteristics of the sensor under dark (no-light) conditions: black level, readout noise, and hot pixel map.

**Standard procedure (refer to EMVA 1288: https://www.emva.org/standards-technology/emva-1288/):**

1. Cover the lens (fully dark environment)
2. Capture multiple frames at various exposure times and gain settings (e.g., average over 64 frames)
3. Extract:
   - **Mean black level:** $\mu_\text{dark}$ (per channel independently)
   - **Readout noise:** $\sigma_\text{read} = \text{std}(\text{dark frames})$
   - **Hot pixel map:** pixels exceeding $\mu + 5\sigma$ are flagged as hot pixels

### 2.2 Flat Field Calibration

**Purpose:** Measure spatial uniformity (LSC baseline), quantum efficiency, and PRNU.

**Standard procedure:**
1. Use an integrating sphere to provide spatially uniform diffuse illumination
2. Capture frames at multiple exposure levels, covering 10%–90% of saturation
3. Extract:
   - **Pixel Response Non-Uniformity (PRNU):** $\sigma_\text{PRNU} / \mu_\text{flat}$ (unit: %)
   - **LSC gain map:** normalized response at each spatial position (used for ch25 LSC calibration)
   - **Linearity curve:** relationship between output DN and incident photon count (validates dynamic range)

### 2.3 Photon Transfer Curve (PTC)

The PTC is the most important calibration curve for characterizing sensor performance; it reveals the dominant noise component in each operating region:

$$\sigma^2_\text{total} = \sigma^2_\text{read} + \frac{1}{K^2} \cdot \bar{\mu} + \sigma^2_\text{PRNU} \cdot \bar{\mu}^2$$

Where $K$ is the system gain ($K = \text{CG}^{-1}$, in units of DN/e⁻) and $\bar{\mu}$ is the mean DN value.

| Region | Dominant Noise | PTC Slope (log-log) |
|--------|---------------|-------------------|
| Dark (low μ) | Readout noise | 0 (noise is constant) |
| Mid-light | Photon shot noise | 0.5 ($\sigma \propto \sqrt{\mu}$) |
| Bright (near saturation) | PRNU | 1 ($\sigma \propto \mu$) |
| Saturation | FWC limited | Noise decreases, μ stops increasing |

PTC calibration simultaneously extracts four key parameters: CG, FWC, readout noise, and PRNU.

---

## §3 Tuning

### 3.1 Impact of Sensor Parameters on ISP Tuning

Sensor physical parameters directly determine the tuning headroom and difficulty of each ISP module:

| Sensor Characteristic | Directly Affected ISP Modules | Tuning Recommendation |
|----------------------|------------------------------|----------------------|
| Low readout noise (< 2 e⁻) | NR strength can be reduced, preserving more detail | Reduce dark-region NR strength coefficients |
| Large FWC | Higher dynamic range ceiling; Gamma can be more linear | Reduce highlight compression; preserve highlight gradation |
| High PRNU | PRNU texture visible in bright scenes | Improve LSC correction accuracy; verify PRNU is below 1% |
| Strong dark current | Black level drifts during long exposures | Enable per-frame OB estimation; update BLC dynamically |
| Large CRA mismatch | Edge color shift, residual LSC error | Per-channel LSC; if too severe, replace the module |
| Quad-Bayer binning | Color aliasing introduced by Remosaic | Validate Remosaic quality in full-resolution mode |

### 3.2 Gain Chain: Analog Gain vs Digital Gain

The ISP's ISO is composed of three gain stages:

```
Sensor Analog Gain
        ↓
In-Sensor Digital Gain (supported by some sensors)
        ↓
ISP Digital Gain
```

**Tuning principles:**
1. **Maximize analog gain first** (e.g., Sony IMX series; maximum analog gain is typically 16×–64×): analog gain amplifies the signal before the ADC, so readout noise is amplified proportionally, and the equivalent input-referred noise remains unchanged
2. **Avoid over-relying on digital gain:** digital gain is applied after the ADC and only amplifies the signal along with quantization error; SNR is not improved. However, when analog gain has reached its maximum, digital gain is the only option
3. **Prefer longer exposure over higher gain:** when motion blur is not a risk, increasing integration time (shutter speed) is preferable to raising ISO

---

## §4 Artifacts

### 4.1 Gr-Gb Channel Imbalance

**Symptom:** Subtle row-direction or column-direction streaking (zebra pattern) visible in the RAW image; color noise appears after demosaicing.

**Cause:** In the Bayer array, Gr (in the same row as R) and Gb (in the same row as B) should theoretically have identical responses. However, due to minor differences in the column readout circuitry, a fixed offset exists between them (typically 1–4 DN).

**Correction:** Add a Gr-Gb equalization module after BLC to enforce $\text{Gb} = (\text{Gr} + \text{Gb}) / 2$.

### 4.2 Column Fixed Pattern Noise (Column FPN)

**Symptom:** Vertical banding visible in dark-field images, with a period of 1 or 2 columns (Bayer-aligned).

**Cause:** Inconsistent bias currents in the column amplifiers produce a column-level fixed offset.

**Correction:** Use the per-column mean from the OB (optical black) region as the FPN correction value for each column; alternatively, apply a row-by-row correction algorithm using the column mean minus the global mean.

### 4.3 Vignetting and CRA Mismatch

**Symptom:** Corner brightness is lower than the center; the blue/red channels show different corner attenuation compared to the green channel (color shading).

**Cause:**
- Natural vignetting (cos⁴θ): see ch25 LSC §1.1
- CRA mismatch: the lens chief ray angle exceeds the design range of the sensor micro-lenses, reducing light collection efficiency in corner pixels

**Correction:** LSC (ch25); in severe cases, a matched sensor-lens combination must be reselected.

### 4.4 Rolling Shutter Skew (Jello Effect)

**Symptom:** Vertical lines tilt when panning rapidly; "wobble" or "bow" distortion appears during fast vertical motion.

**Cause:** The rolling shutter exposes each row at a different start time; see §1.4.1.

**Mitigation:** Increase sensor readout speed (reduce inter-row delay); use Electronic Image Stabilization (EIS) to compensate in post-processing; adopt global shutter in flagship sensors.

---

## §5 Evaluation

### 5.1 Fundamental Sensor Performance Metrics

Measured according to the EMVA 1288 standard (https://www.emva.org/standards-technology/emva-1288/):

| Metric | Measurement Method | Typical Flagship Value |
|--------|-------------------|----------------------|
| Readout Noise | PTC dark-end extrapolation | 1.5–3 e⁻ |
| Full Well Capacity (FWC) | PTC saturation point | 8,000–15,000 e⁻ (1.4 μm pixel) |
| Peak Quantum Efficiency | Monochromator + integrating sphere | 60–75% (550 nm, BSI) |
| Dynamic Range | DR = 20 log₁₀(FWC/σ_read) | 70–75 dB |
| PRNU | Std dev / mean across bright-field frames | < 1% (high-quality sensors) |
| Dark Current | Multi-exposure-time extrapolation | < 1 e⁻/s @ 25°C |

### 5.2 Relationship to ISP Tuning

Sensor performance metrics define the **constraint boundaries** for ISP tuning — they are not adjustable knobs. Tuning engineers should measure and record the above metrics before beginning any tuning session, in order to distinguish "hardware ceiling" from "tuning-improvable headroom." No amount of tuning effort can exceed the physical limits of the sensor.

---

## §6 Main Sensor Platform Reference

### 6.1 Sony Exmor / IMX Series

Sony is the dominant supplier in the mobile sensor market. Key models (in order of release):

| Model | Release Year | Resolution / Format | Highlights | Reference |
|-------|------------|--------------------|-----------|---------  |
| IMX586 | 2018 | 48MP / 1/2" | First flagship with Quad-Bayer | https://www.sony-semicon.com/en/products/is/mobile/imx586.html |
| IMX700 | 2020 | 50MP / 1/1.28" | Huawei P40 Pro, RYYB | — |
| IMX766 | 2021 | 50MP / 1/1.56" | OPPO Find X3 Pro | https://www.sony-semicon.com/en/products/is/mobile/imx766.html |
| IMX989 | 2022 | 50.3MP / 1" | Xiaomi 13 Ultra, 1-inch flagship | https://www.sony-semicon.com/en/products/is/mobile/imx989.html |

### 6.2 Samsung ISOCELL Series

Samsung supplies its own sensors and leads in the high-resolution (100MP+) segment:

| Model | Resolution / Format | Highlights |
|-------|--------------------|-----------|
| HM2 | 108MP / 1/1.33" | Nona-Bayer 9-in-1 binning |
| HP1 | 200MP / 1/1.22" | First commercial 200MP sensor |
| GN2 | 50MP / 1/1.12" | Full-coverage dual-pixel PDAF |
| HP2 | 200MP / 1/1.3" | Galaxy S23 Ultra |

Official technical overview: https://semiconductor.samsung.com/us/consumer-storage/internal-ssd/
ISOCELL technology blog: https://semiconductor.samsung.com/us/consumer-storage/blog/

### 6.3 OmniVision / SK Hynix

OmniVision ships in large volumes for mid-range/low-end phones and front cameras. Public specifications for some models are available at https://www.ovt.com/products/.

---

## References

1. **EMVA Standard 1288 (Release 4.0)** — Industry standard for sensor calibration and performance measurement
   https://www.emva.org/standards-technology/emva-1288/

2. **Sony Semiconductor Solutions — Exmor RS / Stacked CMOS Technology Overview**
   https://www.sony-semicon.com/en/technology/mobile/index.html

3. **Samsung ISOCELL Technology Overview**
   https://semiconductor.samsung.com/us/consumer-storage/blog/

4. **Nakamura, J. (Ed.). (2006). *Image Sensors and Signal Processing for Digital Still Cameras*. CRC Press.** — Classic sensor textbook with detailed derivations of 4T pixel, CDS, and PTC

5. **El Gamal, A., & Eltoukhy, H. (2005). CMOS Image Sensors. *IEEE Circuits and Devices Magazine*, 21(3), 6–20.**
   DOI: 10.1109/MCD.2005.1438751

6. **Fossum, E. R. (1997). CMOS Image Sensors: Electronic Camera-on-a-Chip. *IEEE Transactions on Electron Devices*, 44(10), 1689–1698.**
   DOI: 10.1109/16.628824 — Foundational paper on CDS and CMOS sensor architecture

7. **Holst, G. C., & Lomheim, T. S. (2011). *CMOS / CCD Sensors and Camera Systems* (2nd ed.). SPIE Press.**

8. **Wang Naizhao. *Da Hua Cheng Xiang* (Demystifying Imaging).** — The most comprehensive popular-science book on camera imaging in Chinese, covering sensor physics fundamentals


---

## §1 Theory (Extended Sections)

### 1.8 Photon Shot Noise

The arrival of photons at a photodiode is fundamentally an independent random process governed by **Poisson statistics**. If the expected number of arriving photons is $\mu_p$, then the actual photon count $N_p \sim \text{Poisson}(\mu_p)$ has variance equal to its mean:

$$\sigma_p^2 = \mu_p$$

After quantum efficiency conversion, the number of photoelectrons $N_e \sim \text{Poisson}(\text{QE} \cdot \mu_p)$, and the **photon shot noise** variance is:

$$\boxed{\sigma_\text{shot}^2 = \mu_\text{signal}} \quad [\text{e}^-]^2$$

where $\mu_\text{signal}$ is the mean signal electron count. Shot noise defines the **shot-noise limit** -- the theoretical SNR ceiling -- and **cannot be eliminated by any algorithm**. The only way to improve SNR against shot noise is to increase the signal (larger aperture, longer exposure, or larger pixels).

When shot noise dominates, SNR is:

$$\text{SNR}_\text{shot} = \frac{\mu_\text{signal}}{\sigma_\text{shot}} = \sqrt{\mu_\text{signal}}$$

---

### 1.9 Readout Noise

Readout noise is the hard ceiling on low-light image quality -- it sets the noise floor when the signal approaches zero, and no denoising algorithm can go below this floor. It originates in the analog signal chain (source follower, column amplifiers) and the ADC quantization process. It is additive noise, independent of signal level, well approximated by a Gaussian distribution:

$$n_\text{read} \sim \mathcal{N}(0, \sigma_\text{read}^2)$$

The main components and their physical mechanisms:

| Noise Component | Physical Mechanism | Typical Magnitude |
|-----------------|-------------------|------------------|
| **Thermal noise (Johnson-Nyquist)** | Random motion of hot carriers in the MOSFET channel, power spectral density $S_v = 4kTR$ | Dominant |
| **1/f noise (Flicker noise)** | Carrier trapping/de-trapping at the MOSFET oxide interface; power spectral density proportional to 1/f | Dominant at low frequencies |
| **kTC noise (Reset noise)** | Thermal noise on FD after reset: $\sigma_{kTC}^2 = kTC_\text{FD}$; **eliminated by CDS** | Eliminated by CDS |
| **RTS noise (Random Telegraph Signal)** | Two-state threshold voltage jumps of the SF transistor due to individual carrier traps at the MOS interface | 0.5-20 e- equivalent amplitude; most visible at high ISO |
| **ADC quantization noise** | Discretization error: $\sigma_q^2 = \text{LSB}^2/12$ | Negligible at high bit depths |

The source follower thermal noise, referred back to the input:

$$\sigma_\text{SF}^2 = \frac{4kT\gamma}{g_m} \cdot \Delta f \cdot \frac{1}{C_\text{FD}^2}$$

where $\gamma \approx 2/3$ for long-channel MOSFETs, $g_m$ is the transconductance, $\Delta f$ is the bandwidth, and $C_\text{FD}$ is the floating diffusion capacitance.

---

### 1.10 Dark Current and Dark Noise

Even under fully darkened conditions, thermal excitation spontaneously generates electron-hole pairs in the silicon lattice that accumulate in the photodiode. This is called **dark current**, and its temperature dependence follows the Arrhenius model:

$$I_\text{dark} \propto T^{3/2} \exp\!\left(-\frac{E_g}{2kT}\right)$$

where $E_g \approx 1.12$ eV (silicon bandgap), $k = 8.617 \times 10^{-5}$ eV/K (Boltzmann constant), and $T$ is absolute temperature (K). The empirical rule: **dark current doubles for every ~6-8 degrees C rise in temperature**.

Dark current itself also follows Poisson statistics, so the **dark current shot noise** is:

$$\sigma_\text{dark}^2 = I_\text{dark} \cdot t_\text{exp} / q \quad [\text{e}^-]^2$$

where $t_\text{exp}$ is the integration time. Under long-exposure or high-temperature conditions, dark current noise can exceed readout noise.

**Dark Signal Non-Uniformity (DSNU)** is defined as the spatial non-uniformity of pixel dark current values, manifesting as a fixed bright-spot pattern in dark-field images (hot pixels). It is a form of additive fixed pattern noise.

---

### 1.11 Fixed Pattern Noise

**Fixed Pattern Noise (FPN)** is spatially fixed noise caused by process variation in pixels and readout circuits. It is frame-to-frame repeatable (unlike temporal noise) and falls into two categories:

**1. Photo Response Non-Uniformity (PRNU)**

PRNU is the characteristic whereby different pixels produce different signals from identical illumination -- essentially a spatial variation in pixel gain:

$$\text{DN}_{i,j} = G_{i,j} \cdot \bar{\mu}_\text{signal} + \text{offset}_{i,j}$$

where $G_{i,j}$ is the normalized gain of pixel $(i,j)$ (ideal value: 1.0). PRNU is quantified as:

$$\text{PRNU} = \frac{\sigma_{G}}{\bar{G}} \times 100\%$$

PRNU is **multiplicative noise** -- the stronger the signal, the larger the absolute deviation it causes. Under uniform bright illumination it appears as a fixed spatial texture (cloud-like or grid-like patterns).

**2. Dark Signal Non-Uniformity (DSNU)**

DSNU is the spatial variation in pixel dark current values -- an **additive noise** independent of signal level:

$$\text{DSNU} = \sigma_{I_\text{dark}} \quad [\text{e}^-/\text{s}]$$

---

### 1.12 Complete Noise Model

The total noise variance of a CMOS image sensor is the sum of four independent noise sources:

$$\boxed{\sigma_\text{total}^2 = \sigma_\text{shot}^2 + \sigma_\text{read}^2 + \sigma_\text{dark}^2 + \sigma_\text{FPN}^2}$$

Expanded as a function of signal level:

$$\sigma_\text{total}^2 = \underbrace{\mu_\text{signal} + \sigma_\text{read}^2 + I_\text{dark} \cdot t_\text{exp}/q}_{\text{temporal noise}} + \underbrace{(\text{PRNU} \cdot \mu_\text{signal})^2}_{\text{spatial noise}}$$

**Temporal vs. Spatial Noise.** The first three terms (shot noise, readout noise, dark current shot noise) are **temporal noise** -- random fluctuations in a single pixel across repeated reads, reducible by multi-frame averaging (by $1/\sqrt{N}$). The PRNU term is **spatial noise** -- pixel-to-pixel response non-uniformity that cannot be reduced by multi-frame averaging. In single-frame ISP denoising both appear as pixel-value deviations and are modeled jointly; in multi-frame applications (HDR fusion, super-resolution) they must be strictly distinguished.

**Poisson-Gaussian Noise Model [7]**

The simplified form widely used in ISP algorithms (PRNU nonlinearity neglected, dark current absorbed into the bias term):

$$\boxed{\sigma^2(x) = ax + b^2}$$

where:
- $x$ is the pixel intensity (DN value)
- $a = 1/K$ ($K$ is system gain in e-/DN), corresponding to the shot noise term
- $b^2 = \sigma_\text{read}^2 / K^2 + \sigma_\text{dark}^2$, corresponding to the noise floor; $b$ is the equivalent readout noise standard deviation (DN)

This form is precisely the Photon Transfer Curve (PTC) model defined by the **EMVA 1288 standard [1]**, and is the foundation for sensor calibration and RAW denoising parameter generation.

> **Warning -- Model limitation:** The Poisson-Gaussian model treats all noise as spatially i.i.d. It does **not** model: (1) column ADC fixed offset (column FPN), (2) PRNU spatial texture, (3) RTS hot-pixel flickering, (4) banding noise from row-level circuit mismatch. These structured components must be handled by dedicated correction modules (BLC, PDPC, column FPN correction) before applying Poisson-Gaussian denoising.

---

### 1.13 Dynamic Range

Dynamic range (DR) is defined as the ratio of the largest to the smallest distinguishable signal:

$$\text{DR} = 20 \cdot \log_{10}\!\left(\frac{\text{FWC}}{\sigma_\text{noise\_floor}}\right) \quad [\text{dB}]$$

where $\sigma_\text{noise\_floor} = \sqrt{\sigma_\text{read}^2 + \sigma_\text{dark}^2}$ is the dark noise floor and FWC is the full well capacity (maximum accumulated electrons).

| Sensor Type | Typical DR |
|-------------|-----------|
| Low-end smartphone (1/4 inch, FSI) | 55-60 dB (~9-10 EV) |
| Flagship smartphone (1/1.3 inch, stacked BSI) | 70-75 dB (~12-13 EV) |
| Full-frame camera (Sony A7 series) | 80-85 dB (~14-15 EV) |
| Professional cinema camera (ARRI ALEXA 35) | ~102 dB (~17 EV, ARRI LogC4 official data) |
| Raspberry Pi IMX477 (1/2.3 inch) | ~66 dB (~11 EV) |

---

## §2 Calibration (Extended)

### 2.1 Photon Transfer Curve (PTC) Calibration -- Full Procedure

PTC calibration is the standard method for measuring system gain $K$, readout noise $\sigma_\text{read}$, FWC, and PRNU, per the EMVA 1288 specification [1].

**Required equipment:**
- Integrating sphere or flat-field illuminator: provides spatially uniform, controllable-brightness diffuse illumination
- Temperature chamber (optional): for Arrhenius dark current calibration

**Calibration steps:**

1. **Environment preparation:** Fix the sensor-to-light-source distance; disable all ISP processing (BLC/LSC/NR off); use RAW 12-bit output.

2. **Capture flat-field frame pairs:** At each exposure level, capture at least 2 frames; exposure levels should uniformly cover 5%-95% of saturation (10-15 levels recommended).

3. **Compute mean and variance at each exposure level:**
   $$\bar{\mu}_k = \frac{1}{2}(\bar{I}_{k,1} + \bar{I}_{k,2})$$
   $$\sigma_k^2 = \frac{\text{Var}(I_{k,1} - I_{k,2})}{2}$$
   The frame-difference method eliminates spatial fixed-pattern noise.

4. **Fit the PTC curve:** Fit a line $\sigma^2 = a\mu + b$ to the $\sigma^2$ vs. $\mu$ scatter plot:
   - Slope $a = 1/K$ yields system gain $K$ [e-/DN]
   - Intercept $b = \sigma_\text{read}^2 / K^2$ yields readout noise $\sigma_\text{read}$ [e-]

5. **Extract FWC:** The saturation point where $\bar{\mu}$ stops increasing with exposure is the FWC (DN); multiply by $K$ to convert to electrons.

**System gain measurement formula:**

$$K = \frac{\bar{\mu}_\text{signal}}{\sigma_\text{shot}^2} = \frac{\Delta\mu}{\Delta\sigma^2} \quad [\text{e}^-/\text{DN}]$$

Obtained directly from the PTC slope: $K = 1/a$.

---

### 2.1b Dual Conversion Gain (DCG / HCG+LCG) PTC Calibration

Modern sensors (e.g., Sony IMX989, Samsung ISOCELL HP3) support **Dual Conversion Gain (DCG)**, switching between high-gain (HCG) and low-gain (LCG) modes to extend effective dynamic range. Multi-frame HDR fusion (long/short exposure blending) similarly involves two separate noise parameter sets. **The two CG modes must be calibrated independently:**

- **HCG mode** (small $C_\text{FD}$, high CG): noise parameters $(a_\text{HCG}, b_\text{HCG})$; low shot-noise coefficient, low readout noise -- suited for low light (high ISO range)
- **LCG mode** (large $C_\text{FD}$, low CG): noise parameters $(a_\text{LCG}, b_\text{LCG})$; large FWC, wide dynamic range -- suited for highlights (low ISO range)

**Multi-CG calibration workflow:**

1. Independently repeat the PTC acquisition for each CG mode to obtain $(a_\text{HCG}, b_\text{HCG})$ and $(a_\text{LCG}, b_\text{LCG})$
2. For multi-frame HDR (long/short exposure), calibrate each channel independently
3. During HDR fusion, use per-channel measured noise parameters (not uniform weights) for optimal noise suppression:
   $$w_\text{long} = \frac{1/\sigma^2_\text{long}}{1/\sigma^2_\text{long} + 1/\sigma^2_\text{short}}, \quad w_\text{short} = 1 - w_\text{long}$$
4. The CG-switch ISO crossover point must be calibrated to ensure noise model transitions smoothly

> **Engineering note:** If a "noise step" (abrupt noise texture change) appears near the DCG switch point, the HCG/LCG noise models are not smoothly interpolating across the ISO crossover. Use alpha-blending to linearly blend the two parameter sets over the switch range.

---

### 2.2 PRNU Calibration

**Purpose:** Extract the per-pixel gain deviation map $G_{i,j}$ for flat-field correction (FFC).

**Steps:**

1. Illuminate the sensor with an integrating sphere, exposing to **70-90% of saturation** (75-80% recommended). PRNU signal is proportional to signal strength; at too low saturation, PRNU contribution is masked by readout noise. At 70-90% saturation the SNR of PRNU contribution over readout noise exceeds 10 dB.
2. Capture $N \geq 32$ frames; compute per-pixel mean to eliminate temporal noise:
   $$\bar{F}_{i,j} = \frac{1}{N}\sum_{n=1}^{N} I_{i,j,n}$$
3. Compute the normalized gain map:
   $$G_{i,j} = \frac{\bar{F}_{i,j}}{\frac{1}{MN}\sum_{i,j}\bar{F}_{i,j}}$$
4. PRNU quantification:
   $$\text{PRNU} = \frac{\text{std}(G)}{\text{mean}(G)} \times 100\%$$

---

### 2.3 DSNU Calibration

**Purpose:** Extract the dark current spatial distribution map for hot pixel detection and defective pixel flagging.

**Steps:**

1. Cover the lens completely (fully dark); sensor at operating temperature (e.g., 35 degrees C).
2. Capture $N \geq 64$ frames at the longest integration time; compute per-pixel mean:
   $$\bar{D}_{i,j} = \frac{1}{N}\sum_{n=1}^{N} D_{i,j,n}$$
3. Compute per-pixel dark current deviation: $\Delta D_{i,j} = \bar{D}_{i,j} - \bar{\bar{D}}$ (referenced to the full-image mean)
4. Hot pixel detection: pixels where $|\Delta D_{i,j}| > 5\sigma_\text{read}$ are flagged as hot pixels and written into the Defective Pixel Map (DPM).

---

### 2.4 Dark Current Temperature Calibration

Repeat the DSNU calibration at multiple temperatures $T_k$ and fit the Arrhenius curve:

$$\ln(I_\text{dark}) = \ln(A) + \frac{3}{2}\ln(T) - \frac{E_g}{2k} \cdot \frac{1}{T}$$

The fitted parameters yield dark current predictions at arbitrary temperatures, enabling online black-level compensation that tracks temperature drift.

---

## §3 Tuning (Extended)

### 3.3 Noise Model Parameter Lookup Table

A common engineering mistake is treating the noise model parameters $(a, b)$ as constants. In practice, both parameters change nonlinearly with ISO gain: $a$ scales linearly with gain; $b$ scales linearly with gain (so $b^2$ grows as the square of gain); at high temperature, $b$ rises additionally due to dark current. RAW denoising algorithms (BM3D, DnCNN, NAFNet, etc.) require the current-frame noise parameters as input -- a complete ISO x temperature 2D LUT must be built through factory PTC calibration:

| ISO | Temperature | $a$ (shot noise coeff.) | $b$ (noise floor std, DN) | Readout noise $\sigma_r$ [e-] |
|-----|------------|------------------------|--------------------------|------------------------------|
| 100  | 25 C | 0.0062 | 1.8  | 1.9  |
| 400  | 25 C | 0.0248 | 7.1  | 2.1  |
| 1600 | 25 C | 0.0992 | 28.4 | 2.3  |
| 6400 | 25 C | 0.397  | 114  | 2.6  |
| 1600 | 50 C | 0.0992 | 52.1 | 2.3  |

Note: $a$ scales linearly with ISO; $b$ scales linearly with gain ($b^2$ scales as gain squared); at high temperature $b$ increases additionally due to dark current.

**Typical sensor specification comparison:**

| Sensor | Format | Readout Noise [e-] | FWC [e-] | DR [dB] | PRNU [%] |
|--------|--------|-------------------|----------|---------|---------|
| IMX477 (RPi HQ Cam) | 1/2.3 inch BSI | 1.8 | 7,900 | 73 | < 0.8 |
| IMX989 (1-inch flagship, 50.3 MP) | 1 inch BSI | 1.4 | 12,000 | 79 | < 0.5 |
| IMX766 (mobile main camera) | 1/1.56 inch BSI | 2.1 | 8,500 | 72 | < 1.0 |
| OV5647 (RPi Camera v1) | 1/4 inch FSI | 4.5 | 4,200 | 59 | < 2.0 |
| Industrial camera (typical) | 1/1.8 inch | 5.0-8.0 | 15,000-40,000 | 65-74 | < 1.5 |

---

## §4 Artifacts (Extended)

### 4.5 Hot Pixels and Defective Pixels (Detail)

**Hot pixels** are pixels with dark current far above the array mean; they appear as bright spots in dark-field images during long exposures or at high temperatures.

Primary causes: lattice defects (dislocations, doping non-uniformity) that increase local density of mid-gap states and thermal generation rates; radiation damage (space cameras, X-ray detectors); manufacturing process variation.

**Defective Pixel Correction (DPC / PDPC):**

```
Detection:  |I_{i,j} - median(N8(i,j))| > threshold  -> flag as defective pixel
Correction: I_{i,j} <- median(N8(i,j))               (N8: 8-neighborhood)
            or: I_{i,j} <- bilinear interpolation of (top, bottom, left, right)
```

The defective pixel map (DPM) is written to OTP memory at the factory; the ISP reads it in each frame for **static PDPC**. **Dynamic PDPC** can detect transient hot pixels that appear only under certain conditions (e.g., new hot spots at high gain).

### 4.6 Banding Noise (Detail)

**Row Fixed Pattern Noise (Row FPN)** appears as horizontal banding; **Column Fixed Pattern Noise (Column FPN)** appears as vertical streaks.

Row FPN originates from uneven bias currents in the row readout circuitry or from thermal gradients across the sensor. Column FPN arises from mismatch in the column ADC ramp reference voltages and column amplifier offsets.

Three commonly used correction algorithms:

1. **OB-row correction (row FPN):** The mean of the OB region in each row serves as the row-level offset correction:
   $$I'_{i,j} = I_{i,j} - \left(\frac{1}{N_\text{OB}} \sum_{j \in \text{OB}} I_{i,j} - \text{BL}_\text{global}\right)$$

2. **Column mean subtraction (column FPN):** Use the column means of a fully dark frame as a per-column correction LUT; subtract the corresponding column correction value from each frame.

3. **Frequency-domain filtering:** Analyze the power spectrum along the row/column direction; identify banding frequencies; apply a notch filter to suppress them.

### 4.7 Long-Exposure Thermal Bloom

Under long exposures (> 2 s) or high ambient temperature (sensor junction temperature > 60 degrees C), dark current generates a slowly-varying temperature gradient pattern (**thermal bloom**) in the image.

The sensor center (near power-dissipating circuitry) is slightly brighter than the edges, producing a low-frequency radiant bright haze superimposed on the image background. Mitigation approaches:
- Reduce sensor clock frequency (lowers self-heating)
- Limit maximum integration time
- Allow inter-frame cooling intervals during long-exposure shooting
- Use **dark frame subtraction**: capture a fully occluded dark frame at the same integration time as the signal frame; subtract to cancel thermal noise

### 4.8 PRNU Correction Residual Artifacts

Mismatch between the LSC gain map and the actual scene illuminant is the most common source of PRNU residual texture. These issues are typically invisible in the test lab (controlled integrating sphere); they appear in real-world scenes, especially when switching from daylight to fluorescent lighting.

Typical causes: calibration light source color temperature differs significantly from the shooting scene; LSC table not re-calibrated after firmware update; sensor batch changed (PRNU distribution shifted); long-term sensor aging (PRNU slowly drifts).

**Diagnostic method:** Capture averaged frames of a uniform scene and analyze the spatial frequency distribution. If PRNU exceeds 1.5% and visible texture appears, re-calibrate the LSC.

---

## §5 Evaluation (Extended)

### 5.1b EMVA 1288 Measurement Protocol (Full)

EMVA 1288 (European Machine Vision Association Standard 1288) [1] is the international standard for measuring industrial and scientific camera sensor performance. Core measurement flow:

1. **Dark-field measurement:** Dark frames at multiple exposure levels; extract $\mu_d$ (dark mean) and $\sigma_d^2$ (dark variance)
2. **Bright-field measurement:** Paired flat-field frames; extract $\mu_y$, $\sigma_y^2$ (using the frame-difference method)
3. **PTC fitting:** $\sigma_y^2 - \sigma_d^2 = (1/K)(\mu_y - \mu_d) + \sigma_q^2$
4. **Extract key parameters:** $K$, $\sigma_\text{read}$, FWC, PRNU, QE (QE requires a monochromator with known photon flux)

### 5.2b SNR10 Metric (Full Derivation)

SNR10 is defined as the signal level at which SNR equals exactly 10 dB (using the noise model $\sigma^2(x) = ax + b^2$):

$$\text{SNR}(x) = \frac{x}{\sqrt{ax + b^2}} = \sqrt{10} \approx 3.16$$

Solving $\text{SNR}^2 = 10$: $x^2 = (ax + b^2) \cdot 10$, giving:

$$x_\text{SNR10} = \frac{10a + \sqrt{(10a)^2 + 4 \cdot 10 b^2}}{2}$$

SNR10 reflects sensor usability at very low light -- smaller values are better.

### 5.3b Dynamic Range Measurement (Full Formula)

$$\text{DR} = 20 \cdot \log_{10}\!\left(\frac{\mu_\text{sat} - \mu_d}{\sigma_\text{noise\_floor}}\right) \quad [\text{dB}]$$

where $\mu_\text{sat}$ is the saturation DN value, $\mu_d$ is the black level, and $\sigma_\text{noise\_floor} = b$ (noise floor standard deviation from PTC intercept).

### 5.4b PRNU Measurement

$$\text{PRNU} = \frac{\text{std}(\hat{G})}{\text{mean}(\hat{G})} \times 100\%$$

where $\hat{G}_{i,j} = \bar{F}_{i,j} / \bar{\bar{F}}$, and $\bar{F}$ is the multi-frame-averaged flat-field image.

### 5.5b Typical Acceptance Thresholds (Extended Table)

| Metric | Industrial Camera (high quality) | Flagship Mobile Sensor | RPi IMX477 |
|--------|----------------------------------|----------------------|------------|
| Readout Noise | <= 5 e- | <= 2.5 e- | <= 2.0 e- |
| PRNU | <= 1% | <= 1% | <= 0.8% |
| Dark Current @ 25 C | <= 5 e-/s | <= 2 e-/s | <= 1.5 e-/s |
| Dynamic Range | >= 60 dB | >= 70 dB | >= 66 dB |
| Hot Pixel Fraction | <= 0.01% | <= 0.005% | <= 0.01% |

---

## §7 Glossary

**CMOS Image Sensor (CIS)**
An image sensor manufactured using Complementary Metal-Oxide-Semiconductor (CMOS) process technology, where each pixel cell integrates both a photodiode and readout transistors. Supports on-chip analog signal processing and ADC. Characteristics: low power consumption, high integration density, random access. Has fully superseded CCD as the dominant solution for mobile cameras.

**4T Pixel Architecture (Four-Transistor Pixel)**
The mainstream pixel design in modern CMOS sensors. Contains four transistors: Pinned Photodiode (PPD), Transfer Gate (TX), Reset transistor (RST), Source Follower (SF), and Row Select transistor (SEL). The pinned structure eliminates dark current, and CDS suppresses kTC noise, achieving readout noise as low as 1-3 e- RMS.

**Pinned Photodiode (PPD)**
A pixel structure combining the photodiode with a transfer gate (TX). The depletion region is fully "pinned," enabling complete transfer of signal charge to the floating diffusion node (FD) with no residual charge lag. PPD is the key enabler of low dark current and low readout noise in 4T pixel architectures.

**Floating Diffusion (FD)**
The high-impedance node at the TX transistor drain, used to temporarily store signal charge transferred from the PPD. Charge is converted to voltage via the conversion gain $\text{CG} = q/C_\text{FD}$. Smaller $C_\text{FD}$ means higher conversion gain, lower readout noise (HCG mode), but also smaller FWC.

**Correlated Double Sampling (CDS)**
A pixel readout technique that samples both the reset level ($V_\text{rst}$) and the signal level ($V_\text{sig}$) of the FD, outputting their difference $V_\text{out} = V_\text{rst} - V_\text{sig}$ to eliminate FD reset kTC noise and fixed-pattern noise. CDS can reduce readout noise to 1-3 e- RMS.

> **Warning -- CDS limitations:** CDS eliminates kTC (reset) noise and offset FPN. It does **not** eliminate: (1) source-follower thermal noise (1/f and Johnson noise from the SF transistor), (2) column ADC fixed offset (column FPN), (3) PRNU (pixel gain variation), (4) hot pixels (DSNU), (5) RTS noise.

**Conversion Gain (CG)**
The voltage change at the FD node caused by a single photoelectron: $\text{CG} = q / C_\text{FD}$, in units of V/e- (engineering: uV/e-). High Conversion Gain (HCG) = small $C_\text{FD}$: low readout noise, suited for low light. Low Conversion Gain (LCG) = large $C_\text{FD}$: large FWC, suited for highlights. Dual Conversion Gain (DCG) sensors switch between both modes to extend dynamic range.

**Quantum Efficiency (QE)**
The probability that each incident photon generates one electron in the photodiode: $\text{QE}(\lambda) = N_{e^-}/N_\text{photon} \in [0,1]$, wavelength-dependent. Peak QE near green light (~550 nm); modern BSI sensors reach 70-80% peak QE. QE directly determines signal strength and the shot-noise-limited SNR ceiling.

**Back-Side Illumination (BSI)**
Metal interconnect layers (BEOL) are moved to the back of the silicon substrate; light enters from the front (unobstructed) side directly to the photodiode, increasing fill factor from 20-40% (small-pixel FSI) to 80-95% (modern flagship BSI). Significantly improves low-light sensitivity. Nearly all modern flagship mobile sensors use BSI; further evolved into stacked BSI (pixel layer and circuit layer bonded in separate dies).

**Full Well Capacity (FWC)**
The maximum charge a pixel can accumulate before saturation, in units of e-. FWC sets the signal ceiling; together with readout noise it determines dynamic range: $\text{DR} = 20\log_{10}(\text{FWC}/\sigma_\text{noise\_floor})$. Typical flagship mobile sensors (1-inch) have FWC ~8,000-15,000 e-, far below full-frame cameras (50,000-100,000 e-).

**Photon Shot Noise**
The fundamental noise from the quantum randomness of photon arrival at the photodiode. Photoelectron count follows Poisson statistics; noise variance equals signal mean: $\sigma_\text{shot}^2 = \mu_{e^-}$, $\text{SNR} = \sqrt{\mu_{e^-}}$. Shot noise is the physically irreducible noise lower bound (shot-noise limit); SNR can only be improved by increasing signal (larger aperture, longer exposure, larger pixel).

**Readout Noise**
Additive Gaussian noise from the analog signal chain (SF, column amplifiers) and ADC, expressed as equivalent input-referred electrons e- RMS. Signal-independent. Main sources: SF thermal noise, 1/f flicker noise, ADC quantization noise. Modern BSI sensors at ISO 100: readout noise as low as 1-3 e- RMS; in high-gain mode, sub-electron levels are achievable.

**Random Telegraph Signal Noise (RTS)**
Two-state threshold-voltage jumps of the SF transistor caused by individual carrier trapping and de-trapping at the MOS interface, causing individual pixels to randomly flicker between adjacent frames. Amplitude: 0.5-20 e- (depends on CG and process). Most prominent at very low light (high ISO). Deep-learning denoising models (CBDNet, Restormer) must explicitly model RTS noise.

**Dark Current**
Thermally generated electron-hole pairs that accumulate in the photodiode under zero illumination, following the Arrhenius equation: $I_\text{dark} \propto T^{3/2} \exp(-E_g/2kT)$. Doubles approximately every 6-8 degrees C. Increases image DC bias (requires BLC) and introduces additional shot noise. For long-exposure scenarios, a co-timed dark frame must be captured and subtracted.

**Fixed Pattern Noise (FPN)**
Spatially fixed noise from manufacturing variation in pixels and readout circuits; repeatable frame-to-frame. Two categories: (1) PRNU -- per-pixel gain variation, multiplicative, increases with signal; (2) DSNU -- per-pixel dark current variation, additive, signal-independent. Row FPN (horizontal banding) and column FPN (vertical streaks) are special forms from readout-circuit mismatch.

**Photo Response Non-Uniformity (PRNU)**
The characteristic whereby different pixels produce different responses to the same illumination; quantified as PRNU = std(G) / mean(G) x 100%, typically < 1%. PRNU is multiplicative noise; appears as fixed spatial texture in uniform scenes. Corrected by flat-field correction (FFC). LSC and PRNU overlap physically in calibration -- a spatially uniform light source is required to separate them.

**Dark Signal Non-Uniformity (DSNU)**
Spatial variation in pixel dark current values; additive noise appearing as a fixed bright-spot pattern (hot pixels) in dark-field images. DSNU is defined as the standard deviation of the multi-frame-averaged dark frame, in e-/s. Hot pixels must be flagged in the DPM at the factory and corrected in real time by the PDPC module.

**Photon Transfer Curve (PTC)**
The calibration curve describing the relationship between sensor signal variance $\sigma^2$ and mean $\mu$: $\sigma^2 = (1/K)\mu + \sigma_\text{read}^2/K^2$. PTC slope $1/K$ yields system gain $K$ (e-/DN); the intercept yields readout noise; the saturation point yields FWC. The frame-difference method eliminates FPN interference. This is the core measurement method specified by EMVA 1288.

**System Gain (K)**
The overall electron-to-digital-code conversion factor of the sensor system, in units of e-/DN, combining conversion gain CG, column amplifier gain, and ADC gain. $K = 1 / (\text{PTC slope})$. Typical mobile sensors at ISO 100: $K \approx 0.3$-$1.0$ e-/DN; decreases at higher ISO.

**Poisson-Gaussian Noise Model**
The noise statistical approximation widely used in ISP denoising algorithms: $\sigma^2(x) = ax + b^2$, where $x$ is pixel intensity (DN), $a = 1/K$ is the shot noise term, and $b^2 = \sigma_\text{read}^2/K^2$ is the noise floor. Noise parameters $(a, b)$ are determined by EMVA 1288 PTC calibration and serve as inputs to denoising algorithms (BM3D, DnCNN, NAFNet).

**EMVA 1288 Standard**
Published by the European Machine Vision Association (EMVA), the standardized image sensor performance measurement specification (current version: 4.0). Defines standardized methods for extracting system gain, readout noise, FWC, PRNU, DSNU, dark current, and quantum efficiency from PTC curves. The authoritative reference for sensor selection, calibration, and acceptance testing. Core measured quantities: K, sigma_read, FWC, PRNU, SNR_max, DR, QE.

**Signal-to-Noise Ratio (SNR)**
The ratio of signal to noise, typically in dB: $\text{SNR} = 20\log_{10}(\mu/\sigma)$. In the shot-noise-dominated regime, $\text{SNR} = \sqrt{\mu_{e^-}}$. SNR10 is the signal level at which SNR just equals 10 dB (3.16:1), reflecting the low-light usability lower bound of a sensor.

**Dynamic Range (DR)**
The ratio of the largest to the smallest distinguishable signal: $\text{DR} = 20\log_{10}(\text{FWC}/\sigma_\text{noise\_floor})$, in dB or EV (1 EV ~ 6 dB). DR is constrained by both FWC (upper limit) and the noise floor (lower limit). DCG and multi-frame HDR fusion effectively extend the equivalent DR beyond a single exposure.

**Optical Black (OB)**
Sensor pixels covered by opaque masking material (typically the first few rows/columns per frame) used to estimate the current frame black level offset in real time: $\text{BL}_c^\text{online} = \text{mean}(\text{OB region})$. OB enables accurate BLC by tracking temperature/humidity-driven black level drift, more accurately than relying solely on factory LUTs.

**ADC SNR Limit**
An N-bit ADC has a theoretical maximum SNR of:
$$\text{SNR}_\text{ADC} = 6.02N + 1.76 \quad [\text{dB}]$$
For a 12-bit ADC: SNR ~ 74 dB; for 14-bit: ~86 dB. In practice, effective number of bits (ENOB) is lower due to ADC non-linearity. Sensor DR should be matched to ADC bit depth to avoid quantization noise becoming the dominant noise floor.
