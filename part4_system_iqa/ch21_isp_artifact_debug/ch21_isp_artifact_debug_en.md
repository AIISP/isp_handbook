# Part 4, Chapter 21: ISP Artifact Analysis and Debug Methodology

> **Scope:** This chapter provides a systematic classification of ISP artifacts (image artifacts), root-cause analysis, and debug methodology, covering diagnostic workflows for typical artifacts (color cast, ghosting, moiré, ringing, noise texture).
> **Prerequisites:** Volume 4, Chapter 17 (ISP Tuning Workflow), Volume 4, Chapter 10 (ISP Testing Toolchain)
> **Target Readers:** Algorithm engineers, IQA engineers

---

## §1 Theory

### 1.1 Definition and Classification Framework for ISP Artifacts

**ISP artifacts** (image artifacts) are visual anomalies that do not exist in the real scene but are introduced by algorithmic defects, parameter errors, hardware limitations, or calibration errors during ISP processing. Effective artifact analysis requires establishing a systematic classification framework to rapidly locate root causes.

**Two dimensions of artifact classification:**
1. **By source ISP module:** Identify which processing module introduced the anomaly.
2. **By visual appearance:** Describe the symptom observed by the human eye, facilitating on-site communication.

**ISP module source × visual appearance classification matrix:**

| ISP Module | Typical Artifact | Visual Appearance |
|---|---|---|
| BLC (Black Level Correction) | Global color cast / green shift / red shift | Abnormal overall color tone; uniform regions show a color bias |
| PDPC (Pixel Defect Correction) | Bright spots / dark spots | Scattered fixed white or black spots across the image |
| LSC (Lens Shading Correction) | Vignetting / bright spot | Dark corners or an abnormally bright center spot |
| Demosaic | Moiré / false color / zipper artifacts | Rainbow-colored fringes in fine-texture regions; false-color (green/magenta) fringing at edges |
| NR (Noise Reduction) | Over-smoothing / texture loss / waxy appearance | Skin loses pore detail and looks "plastic"; or noise grain is unnatural |
| AWB (Auto White Balance) | Color cast / gray-scale color bias | White scenes appear overall yellowish, bluish, or greenish |
| CCM (Color Correction Matrix) | Specific gamut shift | Red shifts toward orange, green shifts toward yellow, etc. |
| Gamma / Tone Mapping | Overexposure / underexposure / highlight clipping | Highlight regions have no detail (dead white); shadows crushed to black |
| TNR (Temporal Noise Reduction) | Motion ghost | Transparent residual ghost behind moving objects; abnormal motion blur |
| Sharpening | Ringing / halo / over-sharpening | White or black halos at edges; white fringing at high-contrast edges |
| HDR merge | Ghost / color banding / alignment error | Double contours in moving regions; colored fringes in highlights |
| CA Correction (Chromatic Aberration) | Purple / green fringing | Purple or green fringe along high-contrast edges (e.g., tree branches against sky); caused by lens lateral chromatic aberration |
| EIS (Electronic Image Stabilization) | Distortion / jello effect | Bent edges on moving objects in video; tilted horizontal lines |

### 1.2 Layered Model for Root-Cause Analysis

The root causes of ISP artifacts can be divided into four layers:

```
Layer 1: Parameter layer   → Tuning errors (NR strength too high, AWB range configured incorrectly)
Layer 2: Calibration layer → Calibration errors (inaccurate BLC value, insufficient LSC gain)
Layer 3: Algorithm layer   → Inherent algorithm defect (poor demosaic edge handling)
Layer 4: Hardware layer    → Sensor defects, MIPI timing issues, ISP hardware bugs
```

**Root-cause analysis principle:** Investigate from Layer 1 to Layer 4 in sequence. The majority of field issues (> 70%) belong to Layers 1 and 2. Layers 3 and 4 are relatively rare but carry the highest repair cost.

### 1.3 Visibility Thresholds for Artifacts

Different artifact types have different visual perception thresholds. Understanding these thresholds helps decide whether a fix is necessary:

| Artifact Type | Perception Threshold (reference) | Basis |
|---|---|---|
| Luminance deviation | ΔEV ≈ 0.15 (approximately 10% brightness difference) | Weber-Fechner law |
| Color deviation | ΔE2000 ≈ 2.0 (standard viewing conditions) | CIE 2000 color difference formula |
| Ringing width | > 2 px (1080p) | Human eye angular resolution limit |
| Noise (ISO) | SNR < 20 dB (gain ≈ 10×) | Barten contrast sensitivity function |
| Motion ghost | Displacement > 5 px (1080p, 3 m distance) | Visual motion perception |

---

## §2 Root-Cause Analysis and Diagnosis of Typical Artifacts

### 2.1 Color Cast Analysis

**Appearance:** White objects (white paper, white wall) appear yellowish, bluish, or greenish in the image.

**Systematic diagnostic steps:**

```
Step 1: Verify that AWB mode is set to AUTO (rule out manual white-balance misconfiguration)
Step 2: Capture a RAW image and observe whether the color cast remains without applying AWB
  → Cast present: problem is in BLC or the sensor
  → No cast: problem is in the AWB algorithm or AWB parameters
Step 3 (if AWB issue): Check whether the current scene CCT is within the AWB effective range (2300 K–7500 K)
Step 4: Verify that the AWB OTP calibration data is loaded correctly (BLC offset affects AWB estimation)
Step 5: Verify the CCM matrix (CCM errors cause hue-specific shifts rather than global color cast)
```

**Color cast caused by BLC:** When the BLC (Black Level Correction) value is set too low, the dark regions of the RAW data retain a residual DC offset, causing AWB estimation to be biased. Typical appearance: global green shift (because G pixels have the highest proportion in the Bayer array, so BLC errors most strongly affect G).

**Diagnostic tool:** Capture a dark-field image (lens fully covered) and analyze the mean and standard deviation of each R/G/B channel:
- Normal: all four-channel means approximately equal the configured BLC value (e.g., 64 DN for 12-bit)
- Abnormal: one channel mean is significantly higher (e.g., G channel at 130 DN) → BLC value is set too low

### 2.2 Moiré Analysis

**Appearance:** When shooting fine regular textures (fabric, screens, venetian blinds), irregular colored fringes or rainbow-like ripples appear in the image.

**Physical root cause:** Aliasing between the sensor pixel sampling frequency ($f_s = 1/\text{pixel\_pitch}$) and the spatial frequency of the subject pattern ($f_p$):

$$f_{\text{moiré}} = |f_s - f_p|$$

When $f_p > f_s/2$ (exceeding the Nyquist frequency), aliasing occurs and moiré appears.

**Diagnostic steps:**
```
Step 1: Change the shooting distance (alters the spatial frequency of the pattern on the sensor)
  → Moiré changes with distance → Confirmed real moiré (aliasing)
  → Pattern stays fixed → Possibly a sensor defect or demosaic grid issue

Step 2: Check whether the AA (Anti-Aliasing) filter is functioning
  → Camera/lens combinations without an OLPF (Optical Low Pass Filter) are more prone to moiré

Step 3: Check the high-frequency response characteristics of the demosaic algorithm
  → Use an ISO 12233 test chart to measure MTF; check for colored artifacts near the Nyquist frequency

Step 4: Optionally add adaptive low-pass filtering at the software level (at the cost of sharpness loss);
        evaluate the quality trade-off
```

### 2.3 Ringing/Halo Analysis

**Appearance:** White or black halos appear around high-contrast edges (e.g., text edges, tree branches against a bright sky), with widths of approximately 2–8 px.

**Physical root cause:** The Gibbs phenomenon produced by sharpening algorithms (USM, Unsharp Masking; or RL deconvolution) at strong edges — oscillation caused by the finite-bandwidth approximation of a step function.

$$\text{USM}(x) = I(x) + \alpha \cdot (I(x) - G_\sigma * I(x))$$

When $\alpha$ (sharpening gain) is too large, ringing amplitude exceeds the perception threshold.

**Diagnostic steps:**
```
Step 1: Disable the sharpening module (set sharpening strength = 0) and observe whether ringing disappears
  → Disappears → Sharpening parameters too strong; reduce alpha
  → Remains → May originate from demosaic or another module

Step 2: If ringing is from sharpening, check the following parameters:
  → alpha value: recommended 0.3–0.8; values above 1.0 will always produce ringing
  → Sharpening radius (sigma): too small a sigma makes high-frequency oscillation more visible
  → Edge threshold: raising the threshold suppresses sharpening at strong edges, reducing ringing

Step 3: Evaluate using adaptive sharpening (automatically adjusts sharpening strength based on local contrast)
  → Low contrast (fine textures): normal sharpening
  → High contrast (strong edges): reduce sharpening or use edge-preserving sharpening (EPS)
```

### 2.4 Noise Texture Artifacts

**NR over-smoothing (waxy / plastic appearance):**
- **Appearance:** Skin loses pore texture and looks "plastic"; grass, leaves, and other fine-texture regions become smoothly blurred.
- **Root cause:** Spatial NR (BM3D, bilateral filter) or TNR strength is too high, mistakenly treating real texture signals as noise.
- **Diagnosis:** Compare the high-frequency spectrum with NR on vs. off. If high-frequency components are largely lost when NR is on, the cause is over-smoothing.

**Uneven NR (block or grid noise):**
- **Appearance:** Flat regions (sky, white walls) show regularly arranged block-like or grid-like texture.
- **Root cause:** Block-based NR algorithms (e.g., BM3D's 8×8 blocks) produce discontinuities at block boundaries; alternatively, JPEG blocking artifacts (not an ISP problem).
- **Differentiation method:** Output in RAW format (bypassing JPEG encoding); if blocks still appear, it is an NR problem; otherwise it is JPEG blocking.

**Dark-field chroma noise:**
- **Appearance:** Flat regions in low-light scenes (ISO 3200+) show random colored speckles (random red, green, and blue distribution).
- **Root cause:** Sensor dark-field chroma noise (due to different readout noise levels in R/G/B channels); Chroma NR strength is insufficient.
- **Diagnosis:** Check chroma NR parameters; typically, colored noise should receive stronger filtering than luminance noise.

### 2.5 HDR Ghost Artifact

**Appearance:** In HDR merge results, moving objects (people, branches, water ripples) show double contours or transparent residual ghosts.

**Root cause:** In multi-frame HDR merging (short exposure + long exposure), inter-frame motion occurs. The alignment algorithm fails to correctly align the moving region, causing content from different positions to be overlaid during merging.

**Diagnostic steps:**
```
Step 1: Save the HDR short-exposure and long-exposure frames separately; visually confirm the positional
        difference in the moving region
Step 2: Check the motion detection map (alignment confidence map); confirm whether the ghost region
        is correctly flagged as "high motion"
Step 3: Check merge weights: in high-motion regions, the short-exposure frame should dominate
        (weight → 1), with the long-exposure frame as secondary
Step 4: Check alignment algorithm (optical flow / block matching) parameters: does the search range
        cover the actual motion amount?
```

### 2.6 PDPC Defect Pixel Artifact Analysis

**Fixed defect pixels (hot pixels / dead pixels):**
- **Hot pixel:** A bright spot at a fixed location, most visible in long-exposure or high-temperature conditions.
- **Dead pixel:** A dark spot at a fixed location, present in any scene.
- **Diagnosis:** Shoot a dark field (lens covered) — fixed bright spots are hot pixels; shoot a uniform bright field — fixed dark spots are dead pixels.
- **Fix:** The PDPC (Pixel Defect Correction) module replaces defect pixel values by neighborhood interpolation. If the defect count exceeds a threshold (typically > 0.1% of pixels), the sensor must be replaced.

**Dynamic defects:** Randomly appearing transient defects (not at a fixed location), typically caused by cosmic rays or strong electromagnetic interference. The probability of occurrence per frame is extremely low and generally does not require treatment.

---

## §3 Systematic Debug Methodology

### 3.1 ISP Module Isolation (Binary Isolation)

**Core idea:** Precisely locate the module introducing an artifact by sequentially disabling or bypassing ISP modules.

**Standard procedure:**
```
1. Confirm the symptom: in what scene and under what conditions does the artifact appear
   (reproduction conditions)
2. Minimize the scene: find the simplest reproducible test scene
3. Bypass modules one by one:
   a. Disable all post-processing (keep only BLC + Demosaic); check whether the artifact exists
   b. Gradually re-enable each module (NR → Sharpening → AWB → CCM → Gamma),
      observing at each step whether the artifact appears or disappears
4. Once the module is identified: adjust parameters within that module and observe how
   the artifact changes
5. Once the parameter is found: verify that the fix does not cause regression in other scenes
```

### 3.2 Differential Analysis

Compare a **reference image** (the desired result without the artifact) with the **problem image**; use a difference image to amplify subtle discrepancies:

$$\Delta I = (I_{\text{reference}} - I_{\text{problem}}) \times k_{\text{amplify}}$$

**Interpreting the difference image:**
- Fixed pattern in difference image (stripes, grid) → LSC or demosaic problem
- Difference concentrated at edges → Sharpening or demosaic edge-processing problem
- Difference uniformly distributed (random) → Noise level difference (NR strength problem)
- Difference concentrated in a specific hue → CCM or AWB problem

### 3.3 ADB RAW Capture Workflow

Capturing raw data at different ISP processing stages via ADB is the gold-standard tool for locating artifact root causes:

**Capture steps (Qualcomm platform):**
```bash
# 1. Enable ISP stage dump
adb shell setprop persist.camera.camx.dumpBitMask 0xFFFFFFFF
# Bit-mask meanings (Qualcomm ISP):
# 0x01 = Sensor RAW output (before BLC)
# 0x02 = RAW after BLC
# 0x04 = NV12 after Demosaic
# 0x08 = After NR
# 0x10 = YUV output after CCM/Gamma

# 2. Create dump directory
adb shell mkdir -p /data/camera_dump

# 3. Trigger camera capture (or wait for preview frame)
adb shell am start -a android.media.action.IMAGE_CAPTURE

# 4. Pull dump files
adb pull /data/camera_dump/ ./isp_dump/

# 5. Analyze RAW files (using Python tools)
python3 analyze_isp_dump.py --input isp_dump/ --stage demosaic
```

### 3.4 Toolchain Integration

**Complete ISP debug toolchain:**

| Tool | Purpose | Platform |
|---|---|---|
| Qualcomm IQ Tuning Tool | Real-time Chromatix parameter push, effect preview | Windows |
| MTK APTool | MTK ISP parameter adjustment tool | Windows |
| OpenCV / matplotlib | RAW image visualization, differential analysis | Cross-platform |
| dcraw / LibRaw | RAW file decoding (DNG / MIPI RAW) | Cross-platform |
| Android Systrace | ISP timing analysis, frame-rate jitter investigation | Android |
| Tektronix DSA8300 | MIPI physical-layer signal analysis | Hardware instrument |
| X-Rite i1Display | Monitor calibration (standardizing the evaluation environment) | Hardware instrument |
| Spectroradiometer (PhotoResearch PR-670) | Precise colorimetric measurement | Hardware instrument |

---

## §4 Artifact Quick-Reference Tables

### 4.1 Comprehensive Quick-Reference Table

| Symptom | Most Likely Root Cause | Quick Verification | Fix Direction |
|---|---|---|---|
| Global green / red / blue cast (fixed) | BLC value too low / too high | Shoot dark field and check per-channel mean | Recalibrate BLC |
| White scene appears yellow / blue | AWB estimation error | Force AWB to known CCT | Adjust AWB weights or CCT range |
| Regular colored edge fringing | Demosaic aliasing | Change shooting distance | Adjust demosaic interpolation or add AA filter |
| White / black edge halo | Sharpening too strong | Disable sharpening | Lower USM alpha value |
| Plastic-looking skin / no texture | NR over-smoothing | Disable NR | Reduce NR strength or raise noise threshold |
| Transparent ghost trail on motion | TNR ghost | Disable TNR | Optimize motion map computation |
| Dark corners | Insufficient LSC | Shoot a uniform white field | Recalibrate LSC |
| Fixed bright / dark spots | Defect pixel uncorrected | Shoot dark / bright field | Update PDPC defect pixel table |
| Fine-texture rainbow fringes | Moiré (demosaic aliasing) | Change distance | Adaptive anti-aliasing filter |
| Double contours in multi-frame HDR | HDR alignment failure | Compare single frames | Optimize motion detection + weights |
| Dark-field colored speckles | Insufficient chroma NR | Lower ISO | Strengthen chroma NR |
| Colored fringes in highlight region | HDR saturation handling error | Reduce exposure | Check highlight reconstruction algorithm |
| Inter-frame luminance fluctuation in video | AE hunting | Plot inter-frame EV curve | Increase AE dead zone / step limit |
| Periodic CCT change in video | AWB jitter | Plot inter-frame CCT curve | Reduce AWB update rate |

### 4.2 Scene–Artifact Association Table

| Shooting Scene | High-Occurrence Artifacts | Reason |
|---|---|---|
| Fabric / screen / fine texture | Moiré, demosaic colored fringing | Texture frequency near Nyquist |
| Night / low-light (ISO > 1600) | Dark-field chroma noise, NR over-smoothing, TNR ghost | Low SNR amplifies algorithm defects |
| High contrast (strong light source / window) | Highlight clipping, ringing, HDR banding | Dynamic range exceeded |
| Fast motion (sports / dancing) | TNR ghost, EIS distortion, motion blur | Excessive inter-frame motion |
| Mixed illumination (indoor + outdoor window) | AWB color cast (inconsistent CCT within scene) | Single AWB estimate cannot cover both |
| Portrait / skin | Over-smoothing, skin tone shift | NR + CCM are sensitive to skin tones |
| Fluorescent / LED indoor | Flicker, luminance banding | Light source frequency doesn't match exposure |
| Distant landscape / architecture | Atmospheric scatter blue cast, low color saturation | Wavelength-dependent scatter |

---

## §5 Evaluation

### 5.1 Automated Artifact Detection Framework

**Standardized test set:**
Evaluate under controlled conditions using a fixed set of test scenes:
- **Moiré test chart:** ISO 12233 resolution chart (including high-frequency regular texture regions)
- **Color test chart:** X-Rite ColorChecker Classic (24 patches), for evaluating color cast
- **Defect pixel test:** Uniform bright field (> 90% white) + uniform dark field (< 5% white) for detecting defect pixels
- **Sharpening/ringing:** Slant-edge test image; compute SFR (Spatial Frequency Response) and ringing amplitude
- **Noise test:** ISO 15739 uniform gray patch; measure SNR and texture quality at multiple ISO levels

### 5.2 Artifact Severity Scoring

Establish a unified artifact severity scoring system (1–5 points):

| Score | Meaning | Standard |
|---|---|---|
| 1 | Invisible | Cannot be perceived under standard viewing conditions |
| 2 | Barely visible | Requires deliberate searching to find; does not affect usability |
| 3 | Visible but acceptable | Perceptible during normal viewing, but does not affect the main subject |
| 4 | Noticeably degrades quality | Attracts user attention; affects viewing experience |
| 5 | Severe | Destroys the main subject; unacceptable |

**Release criterion:** Severity ≤ 3 in all test scenes; severity ≤ 2 in core scenes (portrait, everyday photography).

### 5.3 Quantitative Color Cast Evaluation

Shoot an 18% gray card under D65 illumination and measure the Lab values of the output image:
- **Pass criterion:** $|a^*| < 1.5$, $|b^*| < 1.5$ (the gray card should be near neutral, $a^* = b^* = 0$)
- **CCT dependence:** Measure once at each of four CCT points (3200 K / 4000 K / 5500 K / 6500 K); all points must pass

### 5.4 Moiré Quantification

Perform spatial frequency analysis on the slant-line region (moiré region) of an ISO 12233 test chart:
- Compute the power spectral density (PSD) of the chroma (Cb/Cr) components; find the peak power in the 1/2–1 Nyquist frequency range
- **Pass criterion:** Chroma PSD peak in this frequency range < 3 dB above the noise floor

### 5.5 Ringing Evaluation

Use a slant-edge (knife-edge) test:
- Compute the ESF (Edge Spread Function) and LSF (Line Spread Function)
- Ringing metric: ratio of LSF sidelobe amplitude to main-lobe amplitude
- **Pass criterion:** Ringing amplitude < 10% (−20 dB)

---

## §6 Code Examples

### 6.1 ISP Artifact Differential Analysis Tool

```python
import numpy as np
import cv2
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Optional, Tuple

def load_raw_image(
    filepath: str,
    width: int, height: int,
    bit_depth: int = 10,
    bayer_pattern: str = 'RGGB'
) -> np.ndarray:
    """
    Load MIPI RAW10 format raw data.

    Args:
        filepath: Path to the RAW file
        width, height: Image resolution
        bit_depth: RAW bit depth (10/12/14)
        bayer_pattern: Bayer array layout

    Returns:
        raw: uint16 array of shape (height, width), range [0, 2^bit_depth - 1]
    """
    raw_bytes = np.fromfile(filepath, dtype=np.uint8)

    if bit_depth == 10:
        # MIPI RAW10: each 5 bytes stores 4 ten-bit pixels
        n_pixels = (len(raw_bytes) * 4) // 5
        raw = np.zeros(n_pixels, dtype=np.uint16)
        for i in range(n_pixels // 4):
            b = raw_bytes[i*5:(i+1)*5]
            raw[i*4]   = (b[0] << 2) | (b[4] & 0x03)
            raw[i*4+1] = (b[1] << 2) | ((b[4] >> 2) & 0x03)
            raw[i*4+2] = (b[2] << 2) | ((b[4] >> 4) & 0x03)
            raw[i*4+3] = (b[3] << 2) | ((b[4] >> 6) & 0x03)
    elif bit_depth == 16:
        raw = np.frombuffer(raw_bytes, dtype=np.uint16)
    else:
        raw = raw_bytes.astype(np.uint16)

    return raw[:width * height].reshape(height, width)


def differential_analysis(
    img_reference: np.ndarray,
    img_problem: np.ndarray,
    amplify: float = 5.0,
    title: str = "Differential Analysis"
) -> np.ndarray:
    """
    Perform differential analysis between a reference image and a problem image,
    amplifying subtle differences.

    Args:
        img_reference: Reference image (expected result without artifact)
        img_problem: Problem image
        amplify: Difference amplification factor
        title: Chart title

    Returns:
        diff: Difference image (amplified and clipped to [0, 255])
    """
    ref = img_reference.astype(np.float32)
    prob = img_problem.astype(np.float32)

    diff = (ref - prob) * amplify + 128  # offset to midpoint 128
    diff = np.clip(diff, 0, 255).astype(np.uint8)

    # Statistics for the difference image
    diff_raw = (ref - prob)
    print(f"\nDiff statistics ({title}):")
    print(f"  Mean deviation: {diff_raw.mean():.2f}")
    print(f"  Std deviation:  {diff_raw.std():.2f}")
    print(f"  Max difference: {diff_raw.max():.2f}")
    print(f"  Min difference: {diff_raw.min():.2f}")
    print(f"  RMS:            {np.sqrt(np.mean(diff_raw**2)):.2f}")

    return diff


def detect_color_cast(
    image: np.ndarray,
    roi: Optional[Tuple[int,int,int,int]] = None
) -> dict:
    """
    Detect color cast in an image; suitable for white or gray regions.

    Args:
        image: BGR image, uint8
        roi: Analysis region (x, y, w, h); None uses the center region of the full image

    Returns:
        {'r_mean': float, 'g_mean': float, 'b_mean': float,
         'r_g_ratio': float, 'b_g_ratio': float, 'color_cast': str}
    """
    if roi is None:
        h, w = image.shape[:2]
        cx, cy = w // 2, h // 2
        roi = (cx - w//8, cy - h//8, w//4, h//4)

    x, y, rw, rh = roi
    region = image[y:y+rh, x:x+rw].astype(np.float32)

    b_mean = region[:, :, 0].mean()
    g_mean = region[:, :, 1].mean()
    r_mean = region[:, :, 2].mean()

    r_g = r_mean / (g_mean + 1e-6)
    b_g = b_mean / (g_mean + 1e-6)

    # Determine direction of color cast
    cast = "No color cast"
    if r_g > 1.15:
        cast = "Red / warm cast"
    elif r_g < 0.87:
        cast = "Cyan cast"
    elif b_g > 1.15:
        cast = "Blue / cool cast"
    elif b_g < 0.87:
        cast = "Yellow cast"
    elif abs(r_g - 1.0) < 0.08 and abs(b_g - 1.0) < 0.08:
        if g_mean > max(r_mean, b_mean) * 1.05:
            cast = "Green cast"

    return {
        'r_mean': r_mean, 'g_mean': g_mean, 'b_mean': b_mean,
        'r_g_ratio': r_g, 'b_g_ratio': b_g, 'color_cast': cast
    }


def detect_banding_artifact(
    image: np.ndarray,
    direction: str = 'horizontal'
) -> dict:
    """
    Detect banding artifacts in an image (flicker stripes, LSC non-uniformity, etc.).

    Args:
        image: Grayscale or BGR image
        direction: 'horizontal' (horizontal bands) or 'vertical' (vertical bands)

    Returns:
        {'has_banding': bool, 'frequency_hz': float, 'amplitude': float}
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    else:
        gray = image.astype(np.float32)

    # Project along the specified direction (compute mean)
    if direction == 'horizontal':
        profile = gray.mean(axis=1)  # row means
    else:
        profile = gray.mean(axis=0)  # column means

    # Detrend (remove low-frequency background)
    from scipy.signal import detrend
    profile_detrended = detrend(profile)

    # FFT analysis
    fft_mag = np.abs(np.fft.rfft(profile_detrended))
    # Exclude DC (0 frequency)
    fft_mag[0] = 0
    peak_idx = np.argmax(fft_mag)
    peak_amp = fft_mag[peak_idx]
    noise_floor = np.median(fft_mag)

    snr_db = 20 * np.log10(peak_amp / (noise_floor + 1e-6))
    has_banding = snr_db > 10  # > 10 dB indicates significant periodic banding

    return {
        'has_banding': has_banding,
        'peak_frequency_normalized': peak_idx / len(fft_mag),
        'snr_db': snr_db,
        'amplitude': float(peak_amp)
    }
```

### 6.2 Automated Artifact Audit Report Generation

```python
import json
from datetime import datetime

class ArtifactAuditReport:
    """ISP artifact audit report generator."""

    def __init__(self, device_name: str, isp_version: str):
        self.device_name = device_name
        self.isp_version = isp_version
        self.results = []
        self.timestamp = datetime.now().isoformat()

    def add_test(
        self,
        test_name: str,
        artifact_type: str,
        scene: str,
        score: float,  # 1–5 points
        details: dict
    ) -> None:
        """Add a single test result."""
        self.results.append({
            'test': test_name,
            'artifact_type': artifact_type,
            'scene': scene,
            'score': score,
            'pass': score <= 3.0,
            'details': details
        })

    def run_color_cast_audit(self, test_images: dict) -> None:
        """Execute color cast detection for multiple test scenes."""
        for scene_name, image_path in test_images.items():
            img = cv2.imread(image_path)
            if img is None:
                continue
            result = detect_color_cast(img)
            # Color cast score: based on R/G and B/G deviation
            rg_dev = abs(result['r_g_ratio'] - 1.0)
            bg_dev = abs(result['b_g_ratio'] - 1.0)
            max_dev = max(rg_dev, bg_dev)
            score = min(5.0, 1.0 + max_dev / 0.05)  # +1 point per 5% deviation

            self.add_test(
                test_name=f"ColorCast_{scene_name}",
                artifact_type="Color Cast",
                scene=scene_name,
                score=score,
                details=result
            )

    def run_banding_audit(self, test_images: dict) -> None:
        """Execute banding detection (flicker / LSC non-uniformity) for multiple scenes."""
        for scene_name, image_path in test_images.items():
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            for direction in ['horizontal', 'vertical']:
                result = detect_banding_artifact(img, direction)
                score = 1.0 if not result['has_banding'] else \
                        min(5.0, 1.0 + result['snr_db'] / 10)

                self.add_test(
                    test_name=f"Banding_{direction}_{scene_name}",
                    artifact_type="Banding",
                    scene=scene_name,
                    score=score,
                    details=result
                )

    def generate_report(self, output_path: str = "artifact_report.json") -> dict:
        """Generate an artifact audit report in JSON format."""
        n_total = len(self.results)
        n_pass = sum(1 for r in self.results if r['pass'])

        report = {
            'device': self.device_name,
            'isp_version': self.isp_version,
            'timestamp': self.timestamp,
            'summary': {
                'total_tests': n_total,
                'passed': n_pass,
                'failed': n_total - n_pass,
                'pass_rate': n_pass / n_total if n_total > 0 else 0,
                'overall_verdict': 'PASS' if n_pass == n_total else 'FAIL'
            },
            'results': self.results,
            'failed_items': [r for r in self.results if not r['pass']]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*50}")
        print(f"ISP Artifact Audit Report")
        print(f"{'='*50}")
        print(f"Device: {self.device_name} | ISP version: {self.isp_version}")
        print(f"Total tests: {n_total} | Passed: {n_pass} | "
              f"Failed: {n_total - n_pass}")
        print(f"Pass rate: {report['summary']['pass_rate']*100:.1f}%")
        print(f"Overall verdict: {report['summary']['overall_verdict']}")
        if report['failed_items']:
            print(f"\nFailed items:")
            for item in report['failed_items']:
                print(f"  X {item['test']}: score={item['score']:.1f}, "
                      f"scene={item['scene']}")
        return report


# Demo: run a complete artifact audit
def demo_artifact_audit():
    auditor = ArtifactAuditReport(
        device_name="Demo Phone X1",
        isp_version="ISP_v2.3.1"
    )

    # Simulate test results (pass real image paths for actual use)
    print("ISP Artifact Automated Audit Demo")
    print("(Provide real image paths for actual use)\n")

    # Manually add test result demonstrations
    auditor.add_test("ColorCast_D65", "Color Cast", "D65 Gray Card",
                     1.8, {'r_g_ratio': 1.03, 'b_g_ratio': 0.97, 'color_cast': 'No color cast'})
    auditor.add_test("ColorCast_A", "Color Cast", "A-light Gray Card",
                     2.5, {'r_g_ratio': 1.08, 'b_g_ratio': 0.88, 'color_cast': 'Warm cast'})
    auditor.add_test("Moire_Fabric", "Moire", "Fabric texture",
                     3.2, {'peak_snr_db': 12.5, 'at_frequency': '0.48 Nyquist'})
    auditor.add_test("Ringing_Edge", "Ringing", "Slant-edge test",
                     2.1, {'sidelobe_ratio': 0.07, 'ringing_width_px': 2.5})
    auditor.add_test("Banding_Flicker", "Banding", "Fluorescent light scene",
                     4.5, {'snr_db': 25.3, 'frequency': '100Hz'})  # fail

    report = auditor.generate_report("isp_artifact_report.json")
    return report
```

### 6.3 Dark-Field Defect Pixel Detection

```python
def detect_dead_hot_pixels(
    dark_frame: np.ndarray,
    bright_frame: np.ndarray,
    dark_threshold_sigma: float = 5.0,
    bright_threshold_sigma: float = 5.0
) -> dict:
    """
    Detect sensor defect pixels (dead pixels and hot pixels) using dark-field and
    bright-field images.

    Args:
        dark_frame: Dark-field image with lens covered, uint16
        bright_frame: Uniform bright-field image, uint16
        dark_threshold_sigma: Hot-pixel detection threshold in the dark field (multiples of std dev)
        bright_threshold_sigma: Dead-pixel detection threshold in the bright field (multiples of std dev)

    Returns:
        {'hot_pixels': list, 'dead_pixels': list, 'total_count': int,
         'defect_rate_percent': float}
    """
    h, w = dark_frame.shape
    total_pixels = h * w

    # Hot-pixel detection (abnormally bright pixels in the dark field)
    dark_mean = dark_frame.mean()
    dark_std = dark_frame.std()
    hot_threshold = dark_mean + dark_threshold_sigma * dark_std
    hot_mask = dark_frame > hot_threshold
    hot_coords = list(zip(*np.where(hot_mask)))

    # Dead-pixel detection (abnormally dark pixels in the bright field)
    bright_mean = bright_frame.mean()
    bright_std = bright_frame.std()
    dead_threshold = bright_mean - bright_threshold_sigma * bright_std
    dead_mask = bright_frame < dead_threshold
    dead_coords = list(zip(*np.where(dead_mask)))

    defect_count = len(hot_coords) + len(dead_coords)
    defect_rate = defect_count / total_pixels * 100

    print(f"Defect pixel detection result ({w}x{h} = {total_pixels:,} pixels):")
    print(f"  Hot pixels:  {len(hot_coords)}")
    print(f"  Dead pixels: {len(dead_coords)}")
    print(f"  Total defect rate: {defect_rate:.4f}% "
          f"({'PASS' if defect_rate < 0.1 else 'FAIL'})")

    return {
        'hot_pixels': hot_coords[:100],  # return first 100 to avoid large data
        'dead_pixels': dead_coords[:100],
        'total_count': defect_count,
        'defect_rate_percent': defect_rate
    }
```

---

## References

[1] Imatest LLC. (2023). "Image Quality Factors: Artifacts and Defects." Imatest Documentation. https://www.imatest.com/docs/

[2] ISO 12233:2017. "Photography — Electronic still picture imaging — Resolution and spatial frequency responses." ISO.

[3] ISO 15739:2023. "Photography — Electronic still picture imaging — Noise measurements." ISO.

[4] Danielyan, A., et al. (2012). "BM3D Frames and Variational Image Deblurring." *IEEE Transactions on Image Processing*, 21(4), 1715–1728.

[5] Buades, A., et al. (2005). "A Non-Local Means Denoising Algorithm." *SIAM Multiscale Modeling & Simulation*.

[6] Getreuer, P. (2011). "Malvar-He-Cutler Linear Image Demosaicking." *Image Processing On Line*, 1.

[7] Darmont, A. (2009). *High Dynamic Range Imaging: Sensors and Architectures*. SPIE Press.

[8] Debevec, P., & Malik, J. (1997). "Recovering High Dynamic Range Radiance Maps from Photographs." *ACM SIGGRAPH*.

[9] Kaur, M., & Singh, M. (2021). "Fusion Based Image Denoising in WFT Domain." *International Journal of Image and Graphics*.

[10] van Zwol, A., et al. (2020). "Automatic White Balance in Digital Still and Video Cameras." *SPIE Electronic Imaging*.

## §8 Glossary

| Term | Full Name | Description |
|---|---|---|
| Artifact | Image Artifact | Image artifact; a non-real visual anomaly introduced by ISP processing |
| Moiré | — | Moiré pattern; rainbow-colored fringes produced by aliasing between sampling frequency and pattern frequency |
| Ringing / Halo | — | Ringing / halo; halos at edges produced by excessively strong sharpening |
| Aliasing | — | Aliasing; spurious low-frequency components produced by undersampling of high-frequency signals |
| Color Cast | — | Color cast; overall bias of the image toward a particular color |
| Ghost | — | Ghost; residual image of a moving object in HDR merging or TNR |
| Hot Pixel | — | Hot pixel; an abnormally bright spot at a fixed location in the sensor |
| Dead Pixel | — | Dead pixel; an abnormally dark spot at a fixed location in the sensor |
| PDPC | Pixel Defect Correction | Defect pixel correction; replaces defect pixel values by neighborhood interpolation |
| Banding | — | Banding; regular horizontal or vertical luminance stripes in the image |
| Vignetting | — | Vignetting; lower luminance in the image corners compared to the center |
| Waxing Effect | — | Waxy / plastic appearance; loss of texture detail in skin caused by excessively strong NR |
| Chroma Noise | — | Chroma noise; random colored speckles in low-light scenes |
| ESF | Edge Spread Function | Edge spread function; measures edge sharpness |
| SFR | Spatial Frequency Response | Spatial frequency response; a way of measuring MTF |
| OLPF | Optical Low Pass Filter | Optical low-pass filter; an optical element that reduces moiré |
| JND | Just Noticeable Difference | Just-noticeable difference threshold |
