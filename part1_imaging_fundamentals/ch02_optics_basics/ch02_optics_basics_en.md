# Part 1, Chapter 02: Optics Basics for ISP Engineers

> **Pipeline position:** Foundation for LSC (Ch25) and optical aberration correction
> **Prerequisites:** Chapter 1 (ISP Pipeline Overview) — see [ch01_isp_pipeline_overview](../ch01_isp_pipeline_overview/ch01_isp_pipeline_overview_en.md)
> **Reader path:** All readers

---

## §1 Theory

### 1.1 The Thin Lens Model

The most fundamental abstraction of an optical imaging system is the **thin lens model**. The thin lens assumes that the lens thickness is much smaller than the focal length, so that refraction occurs at a single ideal plane. Object distance $d_o$, image distance $d_i$, and focal length $f$ satisfy the **Gaussian thin lens equation**:

$$\boxed{\frac{1}{f} = \frac{1}{d_o} + \frac{1}{d_i}}$$

The **lateral magnification** is defined as the ratio of image height to object height:

$$m = -\frac{d_i}{d_o}$$

The negative sign indicates that the image is inverted relative to the object. For smartphone cameras, $d_o \gg f$ (typically $d_o \sim 1\,\text{m}$, $f \sim 5\,\text{mm}$), so $d_i \approx f$ — the system operates near the infinity-focus condition.

**Numerical example:** For a main camera with focal length $f = 4.4\,\text{mm}$ focused at $d_o = 0.5\,\text{m}$:
$$d_i = \frac{f \cdot d_o}{d_o - f} = \frac{4.4 \times 500}{500 - 4.4} \approx 4.44\,\text{mm}$$

### 1.2 Aperture and f-Number

The **f-number** (also called the aperture value, f/# , or $N$) is defined as the ratio of focal length to entrance pupil diameter $D$:

$$N = \frac{f}{D}$$

A smaller f-number means a larger aperture and more light admitted. Adjacent stops differ by a factor of $\sqrt{2}$, corresponding to a one-stop (1 EV) exposure difference. Typical smartphone main cameras have $N = 1.8$; flagship devices can reach $N = 1.4$.

**Light collection vs. f-number:** The illuminance delivered by the lens to the sensor (light flux per unit area) is proportional to:

$$E \propto \frac{1}{4 N^2}$$

Stopping down from f/1.8 to f/4 therefore reduces light collection by approximately $\left(\frac{4}{1.8}\right)^2 \approx 4.9\times$.

### 1.3 Depth of Field

In front of and behind the focus plane there exists a region of "acceptably sharp" focus — the **depth of field (DoF)**. Using the circle of confusion diameter $c$ as the acceptability criterion, the near and far depth limits $D_n$ and $D_f$ are:

$$D_n = \frac{d_o \cdot (d_o - f)}{f^2 / (N \cdot c) + (d_o - f)}$$

$$D_f = \frac{d_o \cdot (d_o - f)}{f^2 / (N \cdot c) - (d_o - f)}$$

A useful engineering approximation (valid when $d_o \ll H$, i.e., not near the hyperfocal distance):

$$\text{DoF} \approx \frac{2 N c \cdot d_o^2}{f^2}$$

The **hyperfocal distance** $H$: focusing at this distance renders everything from $H/2$ to infinity within the depth of field:

$$H = \frac{f^2}{N \cdot c} + f \approx \frac{f^2}{N \cdot c}$$

**ISP implication:** The Bokeh / Portrait mode in smartphones simulates shallow depth of field in software using a depth map. Understanding the physical DoF limits helps define the valid range for software simulation.

### 1.4 Diffraction Limit

The wave nature of light sets an upper bound on the resolution of any imaging system. Even with a perfect, aberration-free lens, a point source forms an **Airy disk** at the focal plane due to diffraction through the circular aperture. The Rayleigh criterion gives the minimum resolvable angular separation:

$$\theta_{\min} = 1.22 \frac{\lambda}{D}$$

The corresponding Airy disk radius at the focal plane is:

$$r_{\text{Airy}} = 1.22 \frac{\lambda}{D} \cdot f = 1.22 \lambda N$$

**Numerical example:** With $\lambda = 550\,\text{nm}$ and $N = 1.8$:
$$r_{\text{Airy}} = 1.22 \times 550 \times 10^{-9} \times 1.8 \approx 1.21\,\mu\text{m}$$

Contemporary smartphone sensors have pixel pitches of approximately $0.7$–$1.0\,\mu\text{m}$, so the Airy disk diameter (~$2.4\,\mu\text{m}$) spans roughly 2–3 pixels. Stopping down reduces aberrations, but when $N > 4$ diffraction begins to dominate — further stopping down actually makes the image softer. This is the **diffraction-limited** regime.

### 1.5 MTF and OTF

The **Modulation Transfer Function (MTF)** describes how well an optical system transfers contrast at different spatial frequencies. It is the core metric for evaluating lens resolution.

The **Point Spread Function (PSF)** describes the image of a point source through the optical system. The **Optical Transfer Function (OTF)** is the Fourier transform of the PSF:

$$\text{OTF}(f_x, f_y) = \mathcal{F}\{\text{PSF}\}(f_x, f_y)$$

MTF is the magnitude of the OTF:

$$\text{MTF}(f) = |\text{OTF}(f)| = \frac{|\mathcal{F}\{\text{PSF}\}(f)|}{|\mathcal{F}\{\text{PSF}\}(0)|}$$

MTF = 1 means perfect contrast transfer; MTF = 0 means that spatial frequency is completely lost. Industry practice commonly uses **MTF50** (the spatial frequency at which contrast falls to 50%) as an "equivalent resolution" metric, in units of lp/mm or cy/px.

**Diffraction-limited MTF for an ideal aberration-free circular aperture:**

$$\text{MTF}_{\text{diffraction}}(f) = \frac{2}{\pi}\left[\arccos\left(\frac{f}{f_c}\right) - \frac{f}{f_c}\sqrt{1-\left(\frac{f}{f_c}\right)^2}\right]$$

where the cutoff frequency is $f_c = D/(\lambda f) = 1/(\lambda N)$. The MTF of any real lens is always below this diffraction limit.

### 1.6 Lens Aberrations

The degree to which a real lens deviates from the ideal thin lens is characterized by its **aberrations**. ISP engineers should be familiar with the following types:

#### 1.6.1 Radial Distortion

The most common geometric aberration. The displacement of an image point from its ideal position is a function of radius $r$ from the optical axis:

$$x_d = x_u \left(1 + k_1 r^2 + k_2 r^4 + k_3 r^6\right)$$
$$y_d = y_u \left(1 + k_1 r^2 + k_2 r^4 + k_3 r^6\right)$$

where $(x_u, y_u)$ are the ideal (undistorted) normalized image coordinates, $(x_d, y_d)$ are the actual (distorted) coordinates, and $r^2 = x_u^2 + y_u^2$.

- **Barrel distortion:** $k_1 < 0$; the image contracts toward the center, and straight lines bow outward at the edges. Common at the wide-angle end.
- **Pincushion distortion:** $k_1 > 0$; the image expands outward, and straight lines bow inward toward the center. Common at the telephoto end.

#### 1.6.2 Tangential Distortion

Caused by imperfect parallelism between the lens and sensor planes (tilt):

$$\Delta x = 2p_1 x_u y_u + p_2(r^2 + 2x_u^2)$$
$$\Delta y = p_1(r^2 + 2y_u^2) + 2p_2 x_u y_u$$

Tangential distortion coefficients $p_1, p_2$ are usually much smaller than radial distortion coefficients. The full OpenCV distortion model is $[k_1, k_2, p_1, p_2, k_3]$ — five coefficients.

#### 1.6.3 Chromatic Aberration

Glass refractive index varies with wavelength (dispersion), causing light of different colors to have different focal lengths.

- **Longitudinal (axial) CA:** Different colors focus at different points along the optical axis. It manifests as color fringing when the lens is defocused and cannot be eliminated at the focal plane.
- **Lateral (transverse) CA:** Different colors have different magnification at the focal plane, manifesting as colored "purple fringing" at high-contrast edges. Lateral CA can be corrected in post-processing by applying a different scale factor to each color channel.

#### 1.6.4 Other Higher-Order Aberrations

| Aberration | Physical Cause | Visual Appearance |
|-----------|---------------|-------------------|
| Spherical aberration | On-axis; rays at different apertures focus at different distances | Overall blur; degrades mid-to-high frequency MTF |
| Coma | Off-axis; asymmetric convergence of ray bundle | Point sources appear as comet tails |
| Astigmatism | Different focal lengths in tangential and sagittal planes | Point sources appear as cross-shaped blur |
| Field curvature | Best focus surface is curved rather than flat | Center sharp but edges blurred (or vice versa) |

Modern smartphone lenses use multiple aspherical elements and ED (extra-low dispersion) glass to suppress these aberrations.

### 1.7 Vignetting and the Cos⁴ Law

The reduction in brightness toward the image corners is the **vignetting** effect, caused by three overlapping factors:

1. **Natural vignetting:** A purely geometric-optical effect. Off-axis light arriving at angle $\theta$ experiences reduced projected aperture area and reduced solid angle, each contributing a $\cos\theta$ factor, plus an additional $\cos\theta$ from the sensor element's tilt — giving a total of:

$$E(\theta) = E_0 \cos^4\theta$$

2. **Mechanical vignetting:** Barrel, aperture stop, and other mechanical structures obstruct obliquely incident beams.

3. **Pixel vignetting:** The sensor's microlenses have reduced efficiency for non-normal incidence, related to the CRA (chief ray angle).

LSC (Lens Shading Correction, Ch25) compensates for vignetting using a pre-computed gain table, which must be calibrated separately at multiple aperture values and color temperatures.

---

## §2 Calibration

### 2.1 Checkerboard Calibration (Zhang 1999)

Zhengyou Zhang's planar checkerboard calibration method (1999) is the most widely used camera intrinsic calibration approach in industry, integrated into OpenCV as `calibrateCamera()`.

**Method principle:**

The camera intrinsic matrix $\mathbf{K}$ maps normalized camera coordinates to pixel coordinates:

$$\mathbf{K} = \begin{pmatrix} f_x & s & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{pmatrix}$$

where $f_x, f_y$ are focal lengths in pixels, $(c_x, c_y)$ is the principal point, and $s$ is the skew coefficient (typically 0).

For each checkerboard image, each detected corner provides one constraint equation. A single image provides corner count × 2 constraints (x and y each). Multiple images at different poses are combined to solve jointly for $\mathbf{K}$ and distortion coefficients $[k_1, k_2, p_1, p_2, k_3]$, then refined with Levenberg-Marquardt nonlinear optimization.

**Calibration workflow:**

1. **Hardware setup:** Print a high-contrast checkerboard (9×6 inner corners recommended; square size 25–30 mm) on a rigid flat board, ensuring flatness.
2. **Image capture:** Photograph at 15–30 different positions, angles, and distances, ensuring the checkerboard covers the image corners and center. Avoid motion blur; use fixed exposure.
3. **Corner detection:** `cv2.findChessboardCorners()` + `cv2.cornerSubPix()` refines corner positions to sub-pixel accuracy.
4. **Calibration solve:** `cv2.calibrateCamera(obj_points, img_points, img_size)` returns `K`, `dist`, `rvecs`, `tvecs`.
5. **Quality assessment:** Reprojection error < 0.5 pixel is excellent; < 1.0 pixel is acceptable.

```python
# Core calibration call
ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
    obj_points,   # 3D world coordinates (planar checkerboard, z=0)
    img_points,   # corresponding 2D pixel coordinates
    img_size,     # image size (width, height)
    None, None    # initial guess
)
# dist = [k1, k2, p1, p2, k3]
```

### 2.2 MTF Measurement (ISO 12233 Slanted Edge Method)

The **ISO 12233 slanted edge method** is the most commonly used non-parametric MTF measurement approach:

1. Under uniform illumination, photograph a high-contrast black-and-white slanted edge tilted at 3°–10° from vertical.
2. Extract the sub-pixel edge spread function (ESF) along the direction perpendicular to the edge.
3. Differentiate the ESF to obtain the line spread function (LSF), then apply a Fourier transform to obtain the MTF.

Commonly used tools include `imatest` (commercial), `SFRplus`, dead leaves patterns, and the open-source Python `slanted_edge_mtf` library.

### 2.3 Chromatic Aberration Measurement

Use a chromatic edge test chart (such as the enhanced ISO 12233 version) or a custom R/G/B split test chart:

- **Lateral CA:** Measure edge position offset separately for the R/G/B channels; report in pixels.
- **Longitudinal CA:** Measure MTF50 separately for each channel; focal plane offsets manifest as shifted MTF curves between channels.

### 2.4 Vignetting Measurement

Use a uniform diffuse light field (integrating sphere or softbox):

1. Capture a uniformly lit white-field image at the target aperture, ensuring no scene structure.
2. Divide each pixel value by the center reference value to obtain a relative gain map.
3. Repeat at multiple apertures (f/1.8, f/2.8, f/4) and color temperatures (2856 K, 5000 K, 6500 K) to generate a multi-dimensional LSC table.

---

## §3 Tuning

### 3.1 Timing of Distortion Correction in the Pipeline

Distortion correction can be placed at two positions in the ISP pipeline:

| Position | Advantages | Disadvantages |
|---------|-----------|---------------|
| **Pre-ISP (RAW stage)** | All downstream modules operate in the correct coordinate system; distortion does not affect demosaic/denoise | Bilinear interpolation on RAW reduces color accuracy; adds RAW pre-processing latency |
| **Post-ISP (RGB/YUV stage)** | Better interpolation quality in RGB space; only one pass | Demosaic and other modules processed the distorted image, with slight effect on edge handling |

Mobile ISP chips (e.g., Qualcomm Spectra, MediaTek Imagiq) typically provide a mesh warp hardware unit that performs joint distortion and CA correction at the post-ISP stage with very low latency.

### 3.2 LSC Table Generation and Interpolation

LSC gain tables are typically $M \times N$ grids (e.g., $17 \times 13$ or $33 \times 25$) storing R/Gr/Gb/B channel gains at each node. Generation steps:

1. Apply median filtering to the white-field image to remove noise.
2. Normalize each pixel value to the image center value, then invert to obtain gain.
3. Bicubic downsample the gain map to the target grid resolution.
4. Ensure all gain values ≥ 1.0 (the center brightness must not be reduced).

**Multi-illuminant interpolation:** In practice, the ISP linearly interpolates between cold and warm white-field LSC tables based on the current AWB-estimated color temperature, avoiding color cast differences across illuminants.

### 3.3 Choosing the Distortion Model Order

| Model | Parameters | Applicable Scenario |
|-------|-----------|---------------------|
| $k_1$ only (1st order) | 1 | Low-distortion lenses with equivalent focal length > 35mm |
| $k_1, k_2$ (2nd order) | 2 | Most standard lenses (recommended default) |
| $k_1, k_2, k_3$ (3rd order) | 3 | Wide-angle/ultra-wide lenses (distortion > 5%) |
| Fisheye model (equidistant/equisolid) | 4 | Fisheye lenses with FOV > 120° |

High-order models tend to overfit when calibration data contains noise. Use reprojection error on a validation set as the stopping criterion.

---

## §4 Artifacts

### 4.1 Barrel / Pincushion Distortion

**Barrel distortion** is most pronounced on ultra-wide-angle lenses (equivalent focal length < 24 mm) and fisheye lenses. When photographing buildings, horizons, or other scenes containing straight lines, the lines are bent, which is visually unpleasant.

**Pincushion distortion** is common at the telephoto end of zoom lenses. In portrait photography, the edges of the face bow inward, creating a subtle distortion.

After correction, **black borders** can appear at the image corners, requiring cropping. This reduces the effective field of view and wastes pixels.

### 4.2 Purple Fringing

Purple or magenta color fringe appearing at high-contrast edges (e.g., branches against a bright sky, window frame edges) is the typical manifestation of **lateral chromatic aberration**. The physical root cause is that different wavelengths of light converge at slightly different positions on the sensor plane, causing sub-pixel offsets between color channels at edges.

Purple fringing is most pronounced at large apertures (f/1.8) and high-contrast scenes. The digital correction method applies a sub-pixel radial-direction scale offset to the R and B channels relative to G, which eliminates most lateral CA.

### 4.3 Vignetting

Corner brightness falling below center brightness is most visible at large apertures. Smartphone cameras have large chief ray angles (CRA), making pixel-level vignetting particularly pronounced. Excessive LSC correction can amplify corner noise (since gain > 1 amplifies noise proportionally), requiring a trade-off between luminance uniformity and noise uniformity.

### 4.4 Bokeh Ball Shape

Background point light sources (e.g., nighttime city lights) form bokeh balls in shallow depth-of-field photography. An ideal circular aperture produces round bokeh balls; polygonal aperture blades (e.g., hexagonal, octagonal) produce correspondingly shaped bokeh, with the number and shape of blades being one of the aesthetic considerations in lens design. Software Bokeh must algorithmically simulate this effect.

---

## §5 Evaluation

### 5.1 Reprojection Error

The standard quantitative metric for calibration quality. For each image in the calibration set, the solved $\mathbf{K}$, $\text{dist}$, $[\mathbf{R}|\mathbf{t}]$ are used to reproject 3D world corners back to 2D, and the Euclidean distance to the detected 2D corners is computed. The RMS over all corners is:

$$\text{ReprojError} = \sqrt{\frac{1}{N}\sum_{i=1}^{N}\left\|\mathbf{p}_i - \hat{\mathbf{p}}_i\right\|^2}$$

| Level | Reprojection Error |
|------|--------------------|
| Excellent | < 0.3 px |
| Good | 0.3–0.5 px |
| Acceptable | 0.5–1.0 px |
| Recalibrate | > 1.0 px |

### 5.2 MTF50 Measurement Procedure (ISO 12233)

MTF50 (spatial frequency at which MTF = 0.5) is the most commonly used single-number sharpness metric. Measurement steps:

1. Under controlled illumination (uniform, color temperature 5500 K), photograph an ISO 12233 or SFRplus test chart.
2. Select ROIs with slanted edges at the image center and all four corners.
3. Use the slanted-edge MTF algorithm (Fourier-based ESF → LSF → MTF) to compute MTF curves for each ROI.
4. Read the spatial frequency at MTF = 0.5; report in lp/mm or cy/px (cycles per pixel).
5. Analyze the **corner-to-center MTF ratio** to assess field uniformity; a ratio < 0.5 indicates severely insufficient corner resolution.

### 5.3 DXOMark Lens Score System

DXOMark's lens score for smartphones and interchangeable-lens cameras is composed of the following sub-metrics:

| Sub-metric | Meaning |
|-----------|---------|
| Sharpness | Spatially weighted MTF, in Mpix |
| Transmission | Measured aperture vs. nominal f/# |
| Chromatic Aberration | Lateral CA magnitude (in pixels) |
| Vignetting | Corner brightness loss relative to center (in EV) |
| Distortion | Maximum distortion magnitude (%) |

DXOMark scores are weighted averages across multiple apertures and focal lengths (for zoom lenses), and can serve as a reference for engineering acceptance criteria.

---

## §6 Code

See [`ch02_code.ipynb`](ch02_code.ipynb)

The notebook includes:
- Thin lens Gaussian PSF simulation (blur effects at different f-numbers)
- Barrel/pincushion distortion grid visualization
- OpenCV `undistort` demonstration
- MTF curve plotting (contrast vs. spatial frequency for different blur levels)
- Diffraction limit calculation and reprojection error simulation

---

## References

1. **Zhang, Z. (1999).** "A Flexible New Technique for Camera Calibration." *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 22(11), 1330–1334. — Foundational paper for checkerboard calibration.

2. **Brown, D. C. (1966).** "Decentering Distortion of Lenses." *Photogrammetric Engineering*, 32(3), 444–462. — Original paper on radial and tangential distortion models.

3. **Bouguet, J.-Y.** "Camera Calibration Toolbox for MATLAB." Caltech Vision Lab. — Algorithmic basis for OpenCV calibration.

4. **Forsyth, D. A. & Ponce, J. (2002).** *Computer Vision: A Modern Approach*, Chapter 1–2. — Classic textbook on camera models and projective geometry.

5. **OpenCV Documentation.** "Camera Calibration and 3D Reconstruction." https://docs.opencv.org/stable/d9/d0c/group__calib3d.html

6. **ISO 12233:2017.** "Photography — Electronic still picture imaging — Resolution and spatial frequency responses." — MTF measurement standard.

7. **Born, M. & Wolf, E. (2013).** *Principles of Optics*, 7th ed., Chapter 8–9. — Authoritative mathematical reference for diffraction theory and PSF/OTF.

8. **CMU 15-463: Computational Photography.** Ioannis Gkioulekas. Lecture 3: Optics and Cameras. — Clear teaching material on lens imaging and MTF.

9. **Malacara, D. (Ed.) (2007).** *Optical Shop Testing*, 3rd ed. — Practical reference for optical measurement.

10. **Smith, W. J. (2008).** *Modern Optical Engineering*, 4th ed. McGraw-Hill. — Classic reference for engineering lens design.
