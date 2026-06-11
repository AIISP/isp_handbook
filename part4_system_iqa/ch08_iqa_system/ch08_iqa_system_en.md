# Part 4, Chapter 08: IQA System Design for Production

> **Pipeline position:** Quality gate at the output of the ISP pipeline; also used throughout the tuning workflow
> **Prerequisites:** Part 4, Chapter 04 (Perceptual IQA: LPIPS/SSIM/DISTS), Part 4, Chapter 05 (DL Blind IQA: HyperIQA/MUSIQ/Q-Align)
> **Reader path:** Quality Engineer, Algorithm Engineer, MLOps Engineer
> **Scope note:** This chapter covers IQA **engineering systems** — metric framework design, automated testing pipelines, production quality gating, and A/B testing workflows. IQA **algorithm fundamentals** (perceptual similarity metrics, DL blind IQA models) are covered in **Part 4, Chapter 04** (Perceptual IQA) and **Part 4, Chapter 05** (DL Blind IQA).

---

## §1 原理 (Theory)

### Why a Systematic IQA Framework?

Image quality assessment (IQA) in production ISP is not a single metric — it is a multi-layer measurement system designed to answer different questions at different stages of the product lifecycle. A single metric like PSNR fails in practice because:

1. It correlates poorly with human perception at the same PSNR value across different distortion types (blur vs. noise vs. compression artifacts).
2. It provides no diagnostic information: a PSNR drop could come from noise, color error, or sharpness loss.
3. It cannot capture task-relevant quality (does the image allow a face detector to work correctly?).

A production IQA framework must be *hierarchical*, *multi-metric*, and *correlated to human judgments*. We define a 4-layer framework.

---

### The 4-Layer IQA Framework

**Layer 1 — Full-Reference (FR) Metrics:** PSNR, SSIM, MS-SSIM

FR metrics require a reference image (ground truth). They are used during:
- Algorithm development (comparing ISP variants against a DSLR reference).
- Regression testing (ensuring a code change does not reduce quality on a fixed test set).

*PSNR:*
```
PSNR = 10 * log10( MAX_VAL^2 / MSE )
```
Simple, invertible, but does not model the human visual system (HVS).

*SSIM:*
```
SSIM(x, y) = (2μ_x μ_y + C1)(2σ_xy + C2)
             / ( (μ_x² + μ_y² + C1)(σ_x² + σ_y² + C2) )
```
Decomposes quality into luminance, contrast, and structure components. **Range: [-1, 1] (in practice, SSIM for natural images is almost always positive; commonly reported range is [0, 1]); value of 1 indicates perfect similarity. High-quality reconstructions typically score > 0.90; high-fidelity restoration/super-resolution typically > 0.95.** Correlates better with perception than PSNR, especially for blur and structural degradation. Limitation: global SSIM averages over space; local failures (a single blurry region) are masked by high scores elsewhere — use alongside LPIPS for a more complete assessment.

**Layer 2 — No-Reference (NR) Metrics:** BRISQUE, NIQE, PIQE

NR metrics operate without a reference image. They are used for:
- Production monitoring: cameras in the field generate images without a paired reference.
- Automated quality gates in manufacturing test.

*BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator):*
BRISQUE models deviations of local luminance coefficients from a natural scene statistics (NSS) distribution, fitted as a Generalized Gaussian distribution. The feature vector (36 dimensions) is fed to an SVM regressor trained on human MOS scores.

```
BRISQUE_score = SVM( phi(img) )
```
Lower BRISQUE = higher quality. Range roughly 0–100.

*NIQE (Natural Image Quality Evaluator):*
NIQE is entirely unsupervised: it fits a multivariate Gaussian to NSS features of pristine images and measures Mahalanobis distance of the test image features to this distribution. No subjective training data required.

**Layer 3 — Perceptual Metrics:** LPIPS, DISTS

Perceptual metrics use deep network features to measure image similarity in a space that better corresponds to human perception.

*LPIPS (Learned Perceptual Image Patch Similarity):*
```
LPIPS(x, y) = sum_l  w_l * || phi_l(x) - phi_l(y) ||_2^2
```
where `phi_l` are activation maps from VGG/AlexNet layer `l` and `w_l` are learned weights fitted to human 2AFC judgments. LPIPS captures texture and structural differences that SSIM misses.

Perceptual metrics are used for:
- DNN-ISP training loss functions.
- Evaluation of night mode and portrait mode output.

**Layer 4 — Task-Driven Metrics:** Detection Accuracy, OCR Error Rate

The highest-level question is: *does the image support the downstream task?*
- **Face detection:** mAP or recall@precision=0.99 on the ISP output.
- **OCR:** character error rate on license plates or documents.
- **Segmentation:** mIoU.

Task-driven metrics are the ultimate quality arbiter but are expensive and scene-specific.

---

### ISP Quality Metrics Lifecycle

The framework maps layers to product lifecycle stages:

| Stage              | Primary Metrics      | Use                            |
|--------------------|----------------------|--------------------------------|
| Development        | PSNR, SSIM, LPIPS    | Algorithm selection            |
| Tuning             | BRISQUE, SSIM, LPIPS | Parameter optimization         |
| Factory test       | NIQE, BRISQUE        | Production pass/fail gate      |
| Field monitoring   | BRISQUE, NIQE        | Continuous quality dashboards  |
| Feature evaluation | Task-driven + LPIPS  | Portrait, Night, HDR launch    |

---

### Correlation Analysis: SRCC / PLCC

To validate that a metric is meaningful, measure its correlation with human MOS (Mean Opinion Score):

- **SRCC (Spearman Rank Correlation Coefficient):** Rank-order correlation, robust to monotone nonlinearities. Measures monotonic relationship.
- **PLCC (Pearson Linear Correlation Coefficient):** Linear correlation after fitting a 4-parameter logistic function:

```
MOS_predicted = β1 * ( 0.5 - 1/(1 + exp(β2*(metric - β3))) ) + β4
```

Standard benchmarks (LIVE, KADID-10k, CSIQ) report both SRCC and PLCC. A well-calibrated metric should achieve SRCC > 0.85 on IQA benchmark databases.

For ISP-specific data, collect 200+ ISP output samples spanning: noise level, blur, color error, compression, HDR tone mapping artifacts. Label with MOS from 15+ trained raters using ITU-R BT.500 / ITU-T P.910 methodology (5-point ACR scale: 1=Bad, 5=Excellent). Then compute SRCC/PLCC between each objective metric and MOS.

> **Note**: ITU-R BT.500 is the primary standard for video/image quality evaluation;
> ITU-T P.910 is the equivalent for multimedia applications. Both use the
> 5-point ACR (Absolute Category Rating) scale and are widely cited interchangeably
> in the IQA literature.

---

### Building an Automated IQA Pipeline

A production pipeline has four stages:

1. **Capture:** Standardized scene charts (ISO 12233 for sharpness, Macbeth ColorChecker for color, uniform gray for noise) captured under controlled illumination.
2. **Compute:** All metrics computed in batch. Store in a time-series database keyed by firmware version, scene ID, ISO, and illuminant.
3. **Correlate:** Map objective metrics to MOS using the fitted logistic function.
4. **Gate:** Apply thresholds to flag regressions. Alert if any metric drops more than 3% relative from the previous firmware build baseline.

The pipeline should be fully reproducible: all scene captures, metric computations, and threshold decisions are version-controlled alongside the firmware.

---

### Metric Gaming and Its Prevention

A known failure mode is *metric gaming*: an ISP (especially DNN-ISP) tuned to maximize PSNR/SSIM can learn to add artificial sharpening or noise suppression that improves the scalar metric while degrading perceptual quality. Prevention strategies:

1. Use multiple metrics from different layers; require all to improve simultaneously.
2. Include human evaluators in the loop for final launch decisions.
3. Use LPIPS as a constraint (not just PSNR) in DNN training loss.
4. Periodically re-evaluate the correlation of metrics with fresh MOS data.

---

## §2 标定 (Calibration)

### MOS Collection Protocol

- **Sample size:** Minimum 200 ISP output images spanning diverse scenes, ISP parameter settings, and quality levels. Balance distortion types (noise, blur, color, HDR artifacts).
- **Rater pool:** 15–25 trained raters; exclude scores with high within-session variance (std > 1.5 points).
- **Scale:** ITU-R BT.500 / ITU-T P.910 ACR 5-point scale: 5=Excellent, 4=Good, 3=Fair, 2=Poor, 1=Bad.
- **MOS computation:** Mean score per image after z-score normalization per rater.

### Metric-to-MOS Mapping

Fit the 4-parameter logistic function independently for each metric using least-squares minimization. Report SRCC and PLCC on a held-out 20% split.

---

## §3 调参 (Tuning)

### Quality Gate Threshold Setting

For each metric, the threshold is chosen to achieve a target pass rate on known-good samples:

- Set threshold so that false positive rate (good image classified as fail) < 2%.
- Use ROC analysis: plot TPR vs FPR as threshold sweeps; select operating point at desired FPR.
- For BRISQUE: typically pass if BRISQUE < 35 (device-specific; recalibrate per ISP pipeline).

### Multi-Metric Gate

Require all of the following simultaneously:

```python
PASS = (
    psnr   >= PSNR_THRESHOLD    and   # e.g., 35 dB
    ssim   >= SSIM_THRESHOLD    and   # e.g., 0.92
    brisque <= BRISQUE_THRESHOLD and   # e.g., 35
    lpips  <= LPIPS_THRESHOLD         # e.g., 0.12
)
```

This prevents any single metric from being gamed or failing silently.

---

## §4 Artifacts

| Issue | Cause | Mitigation |
|-------|-------|------------|
| Metric gaming | DNN-ISP maximizes PSNR at expense of texture | Add LPIPS to loss; periodic human re-evaluation |
| Metric shift on new sensor | NSS statistics differ for new BSI/stacked sensor | Recalibrate BRISQUE/NIQE on new sensor images |
| MOS drift over time | Rater fatigue or reference drift | Anchor images in every MOS session |
| False alarm from metric outlier | Single bad patch drives global score | Use patch-level statistics with percentile aggregation |

---

## §5 评测 (Evaluation)

### Pearson and Spearman Correlation with MOS

Primary evaluation of any IQA metric on the ISP test set:

- Compute SRCC and PLCC on the held-out 20% split.
- Acceptable: SRCC > 0.80 (moderate), Good: SRCC > 0.88, Excellent: SRCC > 0.93.
- Report confidence intervals (bootstrap 1000 resamples).

### Production Pass Rate at Different Thresholds

- Plot the pass rate curve as a function of threshold for each metric.
- Identify the threshold that maximizes F1 score (harmonic mean of precision and recall) against human-labeled good/bad images.
- Report the ROC AUC for the metric as a binary quality gate.

---

## §6 Automated Test Chart Capture Pipeline

### 6.1 Standard Test Chart System

Production IQA systems rely on standardized test charts captured under controlled conditions. The following chart types cover the primary ISP quality dimensions:

| Chart Type | Standard | Measurement Target | Key Metrics |
|-----------|----------|--------------------|-------------|
| Resolution chart | ISO 12233:2017 | Spatial frequency response (SFR/MTF) | MTF50, MTF10 |
| Color chart | X-Rite Macbeth ColorChecker Classic (24 patches) | Color accuracy | ΔE₀₀, white balance deviation |
| Uniform gray target | Uniform reflectance (18% gray card × multiple luminance levels) | Noise, uniformity | SNR, PRNU, FPN |
| Dynamic range chart | Imatest Dynamic Range | Sensor dynamic range | DR_stops |
| Face test image | ISO/IEC 39794-5 | Face AE/AWB accuracy | Skin ΔE₀₀, EV error |

### 6.2 Capture Control Software Architecture

The automated capture system is organized in three layers:

```
┌──────────────────────────────────────────────────────────────┐
│  Scheduler Layer                                              │
│  - Triggers capture jobs (CI/CD pipeline / manual / cron)    │
│  - Records firmware version, ISP tuning version, Chromatix   │
└──────────────┬───────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────────────┐
│  Light Chamber Controller                                     │
│  - Sets color temperature: 2856K (A) / 4230K (CWF/F2) /     │
│    6504K (D65)                                                │
│  - Sets illuminance (lux): 0.1 / 1 / 10 / 100 / 1000 /      │
│    10000 lux                                                  │
│  - Confirms chamber stability (illuminance variation < 0.5%) │
│    before issuing capture-ready signal                        │
└──────────────┬───────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────────────┐
│  Camera Control Layer                                         │
│  - ADB / MIPI Camera HAL3 ACapture interface                 │
│  - Sets capture parameters (ISO, shutter, AF mode, AE lock)  │
│  - Captures RAW + JPEG/HEIF dual output                      │
│  - Triggers repeated shots (N=10 per scene for repeatability)│
└──────────────────────────────────────────────────────────────┘
```

### 6.3 SFR Measurement Procedure (ISO 12233)

Spatial Frequency Response (SFR) is the core sharpness descriptor for a camera system, measured using the ISO 12233 slanted-edge method:

**Step 1:** Capture the ISO 12233 chart (slanted-edge regions) at each target ISO level.

**Step 2:** Detect the slanted edge (angle 5°–10°); extract cross-edge profiles perpendicular to the edge direction.

**Step 3:** 4× oversampling to reconstruct a super-resolved ESF (Edge Spread Function).

**Step 4:** Differentiate ESF to obtain LSF (Line Spread Function); apply DFT to LSF to obtain the MTF curve.

**Step 5:** Read MTF50 (spatial frequency where contrast drops to 50%) and MTF10 (contrast drops to 10%).

```python
# SFR key metric extraction (conceptual pseudocode)
def compute_sfr(edge_image_crop):
    """
    Input:  image crop containing slanted edge (grayscale, float32)
    Output: MTF50, MTF10 (units: lp/ph, line pairs per pixel height)
    """
    esf = detect_and_oversample_edge(edge_image_crop, oversample=4)
    lsf = np.gradient(esf)
    lsf_windowed = lsf * np.hamming(len(lsf))   # Hamming window reduces spectral leakage
    mtf = np.abs(np.fft.rfft(lsf_windowed))
    mtf /= mtf[0]   # normalize: DC component = 1
    freq = np.fft.rfftfreq(len(lsf_windowed))
    # Linear interpolation for MTF50/MTF10 — more accurate than argmin
    # MTF is monotonically decreasing → reverse so xp is increasing for np.interp
    mtf50 = float(np.interp(0.5, mtf[::-1], freq[::-1]))
    mtf10 = float(np.interp(0.1, mtf[::-1], freq[::-1]))
    return mtf50, mtf10
```

**Production acceptance thresholds (reference values; actual thresholds are device-specific):**

| Resolution | ISO | MTF50 lower limit | MTF10 lower limit |
|-----------|-----|-------------------|-------------------|
| 12MP (4032×3024) | ISO 100 | ≥ 0.35 lp/ph | ≥ 0.45 lp/ph |
| 12MP | ISO 3200 | ≥ 0.28 lp/ph | ≥ 0.38 lp/ph |
| 48MP | ISO 100 | ≥ 0.38 lp/ph | ≥ 0.50 lp/ph |

### 6.4 Color Accuracy Measurement (Macbeth ColorChecker)

**ΔE₀₀ (CIE 2000 Color Difference)** is the core metric for production color acceptance:

$$\Delta E_{00} = \sqrt{\left(\frac{\Delta L'}{k_L S_L}\right)^2 + \left(\frac{\Delta C'}{k_C S_C}\right)^2 + \left(\frac{\Delta H'}{k_H S_H}\right)^2 + R_T \cdot \frac{\Delta C'}{k_C S_C} \cdot \frac{\Delta H'}{k_H S_H}}$$

where the rotation term $R_T$ (ISO 11664-6:2022 §6.3) is:

$$R_T = -2\sqrt{\frac{\bar{C}'^7}{\bar{C}'^7 + 25^7}} \cdot \sin(2\Delta\Theta)$$

$$\Delta\Theta = 30^\circ \exp\!\left(-\left(\frac{\bar{H}' - 275^\circ}{25^\circ}\right)^2\right)$$

$R_T$ introduces a chroma-hue cross-correction in the blue region ($\bar{H}' \approx 275°$). Engineering implementations should use `colormath.color_diff.delta_e_cie2000()` or `skimage.color.deltaE_ciede2000()` to avoid manual implementation errors.

**Measurement procedure:**
1. Capture the 24-patch Macbeth ColorChecker under D65 illumination (6504K).
2. Extract mean RGB values per patch from the image; apply the ISP CCM to convert to sRGB.
3. Convert sRGB to CIE L*a*b* (D65 white point); compare against ColorChecker reference values.
4. Compute ΔE₀₀ for each patch; report mean and maximum.

**Acceptance standards:**

| Scenario | Mean ΔE₀₀ | Max ΔE₀₀ |
|----------|-----------|----------|
| Flagship phone (tuned CCM) | ≤ 2.0 | ≤ 5.0 |
| Mid-range phone | ≤ 3.5 | ≤ 8.0 |
| Raw ISP CCM only | ≤ 5.0 | ≤ 12.0 |

### 6.5 Noise Measurement (Uniform Gray Target)

**SNR (Signal-to-Noise Ratio) measurement:**

```python
def measure_snr_flat_field(images: list, roi: tuple):
    """
    images: N captures of the same scene (for temporal noise evaluation)
    roi: (x, y, w, h) uniform region of interest
    Returns: SNR (dB), sigma_temporal, sigma_spatial
    """
    stack = np.stack([img[roi[1]:roi[1]+roi[3], roi[0]:roi[0]+roi[2]]
                      for img in images], axis=0)  # shape: (N, H, W)
    mean_signal = stack.mean(axis=0).mean()          # spatial + temporal mean = signal
    sigma_temporal = stack.std(axis=0).mean()        # temporal noise (per-pixel std across frames)
    sigma_spatial  = stack.mean(axis=0).std()        # spatial noise (std of mean frame)
    snr_db = 20 * np.log10(mean_signal / sigma_temporal)
    return snr_db, sigma_temporal, sigma_spatial
```

**Fixed Pattern Noise (FPN) and Photo Response Non-Uniformity (PRNU):**

- **FPN:** Spatial standard deviation of a single dark-frame (lens covered), reflecting dark current non-uniformity.
- **PRNU:** Spatial standard deviation of the temporal mean frame under uniform illumination minus the global mean — reflects pixel gain variation. Typical pass criterion: PRNU < 0.5% of full-scale signal.

---

---

## 参考资料

- Wang, Z. et al. "Image Quality Assessment: From Error Visibility to Structural Similarity," IEEE TIP 2004.
- Mittal, A. et al. "No-Reference Image Quality Assessment in the Spatial Domain," IEEE TIP 2012 (BRISQUE).
- Zhang, R. et al. "The Unreasonable Effectiveness of Deep Features as a Perceptual Metric," CVPR 2018 (LPIPS).
- LIVE IQA Database: https://live.ece.utexas.edu/research/quality/
- KADID-10k Database: https://database.mmsp-kn.de/kadid-10k-database.html
- ITU-T P.910: Subjective video quality assessment methods for multimedia applications.
- ISO 12233:2017 — Photography. Electronic still picture imaging. Resolution and spatial frequency responses.
- Ke, J. et al. "MUSIQ: Multi-scale image quality transformer," ICCV 2021.
- Wu, H. et al. "Q-Align: Teaching LMMs for visual scoring via discrete text-defined levels," ICML 2024.

---

## §7 Per-Module IQA Metric Assignment

Each ISP module introduces characteristic artifacts; a well-designed IQA system assigns specific metrics to each stage:

| ISP Module | Primary Artifact | Recommended Metric | Threshold (typical) |
|------------|-----------------|-------------------|---------------------|
| BLC / DPC | Dead pixels, color bias | Hot pixel count, BRISQUE | < 3 hot pixels, BRISQUE < 40 |
| Demosaic | Zipper, false color, moiré | MTF50 (at Nyquist), chroma noise | MTF50 > 0.4 cy/px |
| NR (denoising) | Over-smoothing, texture loss | NIQE, SNR at ISO 400 | NIQE < 3.5 |
| Sharpening (EE) | Halo, overshooting | Ringing measure (ISO 12233) | Ringing index < 15% |
| AWB | Color cast, memory color error | ΔE₀₀ on gray patches | ΔE₀₀ < 2.0 |
| CCM | Hue/chroma error | ΔE₀₀ on ColorChecker | Mean ΔE₀₀ < 3.5 |
| Gamma / TM | Clipping, banding | DR (stops), gradient smoothness | DR > 10 stops |
| Compression | Blocking, ringing | SSIM, LPIPS | SSIM > 0.88 |

The key principle: **measure at the module output, not only at the final output**. An NR problem masked by downstream sharpening is harder to diagnose after the fact.

---

## §8 Defect Classification Catalog

### 8.1 ISP Defect Severity Classification (P0 / P1 / P2)

| Level | Definition | Handling Priority | Example |
|-------|-----------|-------------------|---------|
| **P0** | Functional defect — image unusable | Block release immediately | Full black frame, all-noise output, completely wrong color |
| **P1** | Major perceptual defect — subjective score < 2/5 | Fix in next build | Severe color cast (ΔE₀₀ > 15), obvious HDR halo, severe under/overexposure |
| **P2** | Minor perceptual defect — subjective score 2–3/5 | Schedule fix | Mild hue shift, moderate noise, slight vignette |

### 8.2 Common ISP Failure Mode Catalog

**Noise defects:**

| Defect Name | Symptom | Root Cause | Detection Metric |
|------------|---------|-----------|-----------------|
| High-frequency noise residual | Visible grain in dark areas | Insufficient NR strength / ISO too high | SNR < threshold, BRISQUE > 40 |
| Over-smoothing | Texture disappears, "plastic" look | NR strength too aggressive | SSIM detail drop, MTF50 reduction |
| Fixed Pattern Noise (FPN) | Vertical/horizontal stripes | Sensor manufacturing defect / insufficient BLC | FPN index > 1.0 DN rms |
| Chroma noise | Random colored dots in flat regions | Insufficient CNR | Chroma SNR < Luma SNR − 6 dB |

**Color defects:**

| Defect Name | Symptom | Root Cause | Detection Metric |
|------------|---------|-----------|-----------------|
| AWB color cast | Image globally shifted to yellow/blue | AWB convergence error / wrong illuminant classification | White point Δuv > 0.005 |
| CCM color error | Specific hues off (e.g., skin too red) | Insufficient CCM calibration | Macbeth ΔE₀₀ > 5 (on affected patch) |
| Oversaturated tone mapping | Colors unnaturally vivid | Saturation gain too high | CIECAM02 saturation deviation |
| Chroma moiré | Colored fringes over regular textures | Demosaic filter design deficiency | CPIQ chroma moiré spectral peak |

**Sharpness / focus defects:**

| Defect Name | Symptom | Root Cause | Detection Metric |
|------------|---------|-----------|-----------------|
| Over-sharpening / ringing | Bright/dark halo at high-contrast edges | Sharpening coefficient too high | Ringing index > threshold |
| Under-sharpening | Image globally soft | Insufficient sharpening / NR too aggressive | MTF50 < 0.3 lp/ph |
| Local defocus | Partial region blurry | AF convergence error / lens field curvature | Local MTF50 < global mean × 0.7 |

**HDR / exposure defects:**

| Defect Name | Symptom | Root Cause | Detection Metric |
|------------|---------|-----------|-----------------|
| Highlight clipping | Bright regions fully white, no detail | AE overexposure / insufficient tone mapping | Highlight clip ratio > 0.5% |
| Shadow crushing | Shadow regions fully black | AE underexposure / incorrect gamma curve | Shadow histogram clip ratio > 1% |
| HDR ghosting | Motion subject shows double exposure | Ghost rejection weight failure | MOS < 3.0 (scenes with motion) |
| Tone-mapping halo | Halo at high-contrast boundaries | Local tone-mapping radius too small | Detected by manual review |

### 8.3 Defect Tracking Database Schema

Each defect record contains the following fields:

```json
{
  "defect_id": "ISP-2024-0342",
  "severity": "P1",
  "module": "AWB",
  "symptom": "2700K tungsten scene shifted blue",
  "root_cause": "FFCC illuminant classifier misclassifies low CCT as D50",
  "detection_metric": "white_point_delta_uv > 0.008",
  "detected_version": "ISP_v3.2.1",
  "fixed_version": "ISP_v3.2.3",
  "regression_test_id": "AWB_TC_0021",
  "iqa_before": {"delta_uv": 0.012, "mos": 2.1},
  "iqa_after":  {"delta_uv": 0.003, "mos": 4.2}
}
```

---

## §9 CI/CD Integration for ISP Regression Tracking

### 9.1 IQA as a CI/CD Quality Gate

Manual testing lacks the frequency needed to catch ISP regressions quickly. When a tuning engineer modifies a single Chromatix node, the quality impact on other modules may not surface until two iterations later — by which point root-cause attribution is difficult. Embedding IQA in the CI/CD pipeline ensures every commit is tested against the full suite, and regressions are blocked at the originating commit:

```
Code commit / tuning parameter update
    ↓ git push → CI/CD server (Jenkins / GitLab CI)
    ↓ Trigger ISP firmware build
    ↓ Trigger IQA automated test suite
        ├── Scene capture (automated light chamber, ~20 minutes)
        ├── Metric computation (PSNR / SSIM / MTF50 / ΔE₀₀ / BRISQUE / LPIPS)
        └── Compare against baseline version
    ↓ Quality gate decision
        ├── PASS: all metrics within acceptable regression bounds → allow merge
        └── FAIL: any metric degraded beyond threshold → block merge, trigger alert
    ↓ Report pushed to Slack / email / dashboard
```

### 9.2 Regression Threshold Definition

Regression detection uses statistical significance rather than absolute values to avoid false alarms from measurement noise:

**Continuous metrics (e.g., MTF50, SNR, PSNR):**
- Collect N=10 repeated captures per scene for both versions.
- Apply Welch's t-test (assumes unequal variance) to test mean difference.
- Declare regression if p < 0.05 AND effect size Cohen's d > 0.5.

**Categorical metrics (e.g., AWB pass rate):**
- Use McNemar's test to compare pass/fail counts across the same test set for both builds.

**Practical simplified thresholds (fast gate, suitable for sub-minute CI checks):**

| Metric | Regression Threshold | Trigger Level |
|--------|---------------------|---------------|
| MTF50 | Drop > 5% | P1 block |
| SNR | Drop > 1 dB | P1 block |
| ΔE₀₀ (Macbeth mean) | Rise > 0.5 | P1 block |
| PSNR (vs. reference) | Drop > 1 dB | P1 block |
| BRISQUE | Rise > 5 | P2 alert |
| LPIPS | Rise > 0.02 | P2 alert |

### 9.3 ISP Version Regression Database Schema

```sql
-- ISP version table
CREATE TABLE isp_versions (
    version_id      VARCHAR(32) PRIMARY KEY,  -- e.g. "ISP_v3.2.1"
    build_timestamp DATETIME,
    tuning_hash     VARCHAR(64),              -- SHA256 of Chromatix/tuning files
    firmware_hash   VARCHAR(64),
    commit_message  TEXT,
    author          VARCHAR(64)
);

-- Test scene table
CREATE TABLE test_scenes (
    scene_id        VARCHAR(32) PRIMARY KEY,  -- e.g. "ISO100_D65_12233"
    chart_type      ENUM('sfr','macbeth','flat','face','hdr'),
    illuminant      VARCHAR(16),              -- "D65","A","CWF","D50"
    lux_level       FLOAT,
    iso_setting     INT
);

-- IQA measurement results table
CREATE TABLE iqa_results (
    result_id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    version_id      VARCHAR(32) REFERENCES isp_versions(version_id),
    scene_id        VARCHAR(32) REFERENCES test_scenes(scene_id),
    measured_at     DATETIME,
    mtf50           FLOAT,
    mtf10           FLOAT,
    snr_db          FLOAT,
    delta_e00_mean  FLOAT,
    delta_e00_max   FLOAT,
    psnr            FLOAT,
    ssim            FLOAT,
    brisque         FLOAT,
    lpips           FLOAT,
    mos_predicted   FLOAT
);

-- Regression event table
CREATE TABLE regression_events (
    event_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    detected_at     DATETIME,
    version_from    VARCHAR(32),
    version_to      VARCHAR(32),
    scene_id        VARCHAR(32),
    metric_name     VARCHAR(32),
    value_before    FLOAT,
    value_after     FLOAT,
    delta_percent   FLOAT,
    severity        ENUM('P0','P1','P2'),
    status          ENUM('open','investigating','fixed','wontfix')
);
```

### 9.4 Version Trend Visualization

ISP version iteration trend charts should include the following time-series curves:

- MTF50 trend (mean ± standard deviation per firmware version)
- SNR@ISO3200 trend (core night-mode capability indicator)
- ΔE₀₀ mean trend (color accuracy)
- BRISQUE@natural-scene trend (blind IQA perceptual proxy)

When any metric shows consecutive decline over two versions, an automatic trend alert is triggered. This early-warning signal catches gradual degradation that would be invisible to per-build threshold checks.

---

## §16 Glossary

| Term | Definition |
|------|-----------|
| **IQA** | Image Quality Assessment — systematic measurement of perceptual image quality |
| **FR-IQA** | Full-Reference IQA — requires a reference image; e.g., PSNR, SSIM, LPIPS |
| **NR-IQA** | No-Reference (Blind) IQA — no reference; e.g., BRISQUE, NIQE, HyperIQA |
| **MOS** | Mean Opinion Score — aggregate human rating, typically 1–5 scale |
| **SRCC** | Spearman Rank Correlation — rank agreement between predicted and human scores |
| **PLCC** | Pearson Linear Correlation — linear alignment after nonlinear fitting |
| **PSNR** | Peak Signal-to-Noise Ratio — pixel fidelity, in dB; 30 dB = acceptable, 40 dB = excellent |
| **SSIM** | Structural Similarity Index — perceptual quality (luminance, contrast, structure) |
| **LPIPS** | Learned Perceptual Image Patch Similarity — deep-feature distance; lower = better |
| **MTF50** | Modulation Transfer Function at 50% contrast — spatial resolution measure (cy/px) |
| **ΔE₀₀** | CIEDE2000 color difference metric; < 2.0 considered just-noticeable |
| **DR** | Dynamic Range — ratio of maximum to minimum recordable luminance, in stops (log₂) |
| **Quality gate** | Automated pass/fail criterion in the ISP production pipeline |
| **Regression test** | Automated comparison of current build vs. baseline to detect performance drops |
| **P0/P1/P2/P3** | Defect severity levels: P0 = blocking, P1 = visible, P2 = on inspection, P3 = barely visible |

---

## §10 A/B Testing Framework and Statistical Significance

### 10.1 Why ISP Tuning Needs A/B Testing

A common situation in NR curve tuning: SNR improves by 0.8 dB but MTF50 drops 4% — objective metrics point in opposite directions, and the right call is unclear from metrics alone. At this point, the decision cannot rest on engineering intuition. A blind human evaluation must determine which version users actually prefer.

**Blind A/B testing** solves exactly this: when objective metrics conflict, quantified human preference data breaks the tie.

### 10.2 A/B Test Procedure

```
Preparation:
  ├── Version A (Control):   current baseline tuning
  ├── Version B (Treatment): new tuning under evaluation
  ├── Test scene set: 100+ images spanning different lighting conditions and scene types
  └── Raters: 15–25, no version labels visible (double-blind)

Evaluation:
  ├── 2AFC (Two-Alternative Forced Choice): for each pair, select the higher-quality image
  ├── OR DMOS (Differential MOS): rate quality difference on a [-3, +3] scale
  └── Randomize presentation order (prevents order bias)

Statistical analysis:
  ├── 2AFC results: binomial test — is preference rate significantly different from 50%?
  ├── DMOS results: paired t-test or Wilcoxon signed-rank test
  └── Report effect size (Cohen's d) and confidence intervals
```

### 10.3 Statistical Test Methods

**2AFC Binomial Test:**

If version B is preferred k times out of N trials, under H₀ (no difference, p = 0.5):

```python
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

def ab_test_2afc(n_total, n_prefer_b, alpha=0.05):
    """
    n_total:    total number of evaluations
    n_prefer_b: number of times version B was preferred
    alpha:      significance level
    """
    # Two-sided binomial test (scipy >= 1.7 uses binomtest)
    p_value = stats.binomtest(n_prefer_b, n_total, p=0.5, alternative='two-sided').pvalue
    preference_rate = n_prefer_b / n_total
    # 95% confidence interval (Wilson interval)
    ci_low, ci_high = proportion_confint(n_prefer_b, n_total, alpha=alpha, method='wilson')

    result = {
        'preference_rate_B': preference_rate,
        'p_value': p_value,
        'significant': p_value < alpha,
        'ci_95': (ci_low, ci_high),
        'conclusion': 'B significantly better' if (p_value < alpha and preference_rate > 0.5)
                      else 'A significantly better' if (p_value < alpha and preference_rate < 0.5)
                      else 'No significant difference'
    }
    return result
```

**DMOS Wilcoxon Signed-Rank Test:**

```python
def ab_test_dmos(dmos_scores, alpha=0.05):
    """
    dmos_scores: array of DMOS values per scene (positive = B is better)
    """
    stat, p_value = stats.wilcoxon(dmos_scores, alternative='two-sided')
    # Effect size r = Z / sqrt(N)  (Rosenthal 1991)
    n = len(dmos_scores)
    from scipy.stats import norm as _norm
    z_score = _norm.ppf(1 - p_value / 2) if p_value < 1.0 else 0.0
    effect_size = z_score / (n ** 0.5)   # r < 0.3 small, 0.3-0.5 medium, > 0.5 large
    return {
        'median_dmos': np.median(dmos_scores),
        'p_value': p_value,
        'significant': p_value < alpha,
        'effect_size': effect_size
    }
```

### 10.4 Minimum Sample Size Calculation

To achieve statistical power ≥ 0.80 at effect size d = 0.5:

```
n_min = 2 * (z_α/2 + z_β)² / d²
      = 2 * (1.96 + 0.84)² / 0.5²
      ≈ 63 image pairs (2AFC)
```

In practice, use **100–200 image pairs** covering different scene categories to ensure sub-group analysis (night, portrait, HDR) is reliable.

### 10.5 Multiple Comparison Correction

When running several A/B tests simultaneously (e.g., testing NR, sharpening, and color parameters in parallel), apply multiple comparison correction (Bonferroni or Benjamini-Hochberg FDR) to avoid false positives:

```python
from statsmodels.stats.multitest import multipletests

p_values = [0.03, 0.01, 0.08]  # p-values from three independent A/B tests
reject, corrected_p, _, _ = multipletests(p_values, alpha=0.05, method='fdr_bh')
# Use corrected_p as the final decision basis
```

---

## §11 Fleet Monitoring Dashboard

### 11.1 Production Fleet IQA Monitoring Architecture

Laboratory testing cannot cover real-world user scenarios — there are no backlit subjects, camera shake, or mixed light sources in the light chamber. Devices shipped to consumers photograph in every conceivable real-world condition, and this data is the most direct signal for detecting systemic ISP issues. By collecting quality metrics via **anonymous telemetry** (computed on-device, then stripped of PII before upload), problems can be caught and acted on before they reach large-scale user complaints:

```
User device (production)
    ↓ Periodically compute anonymous quality metrics (BRISQUE, exposure stats, WB stats)
    ↓ Anonymize (strip GPS / timestamp / face data)
    ↓ Upload to quality monitoring backend
         ├── Real-time dashboard (Grafana / DataDog)
         │     ├── Device breakdown: by model / region / firmware version
         │     ├── Exposure failure rate (severe over/under-exposure event frequency)
         │     └── AWB deviation distribution (95th percentile Δuv)
         └── Alert rules (threshold trigger → PagerDuty / Slack)
```

### 11.2 Fleet Monitoring Key Metrics

| Monitoring Metric | Data Source | Alert Threshold | Significance |
|------------------|-------------|-----------------|--------------|
| Anonymous image BRISQUE | On-device offline computation | 95th percentile > 45 | Perceptual quality degradation |
| Exposure failure rate | AE convergence status log | > 0.5% of capture events | AE stability |
| AWB white point Δuv | AWB convergence result log | 95th percentile > 0.008 | Systematic AWB bias |
| AF miss-focus rate | AF HAL status log | > 2% NOT_FOCUSED_LOCKED | AF system issue |
| HDR merge failure rate | ISP internal status codes | > 1% of HDR scenes | Multi-frame merge issue |
| Crash / exception rate | Crash reporting | Any upward trend | Stability problem |

### 11.3 A/B Gray-Release Monitoring

When a new ISP firmware is rolling out to a subset of devices, use a controlled experiment framework to compare field metrics between old and new versions:

```
Devices randomly split:
  ├── Control group (10%):   old firmware ISP_v3.2.1
  └── Treatment group (10%): new firmware ISP_v3.3.0

Observation window: 7 days
Comparison metrics: BRISQUE mean, exposure failure rate, AWB deviation
Statistical method: Welch's t-test (continuous) / chi-square test (discrete event rates)

Gray-release decision rule:
  - Treatment group shows no significant regression on any metric → expand to 50% → full rollout
  - Any metric shows significant regression → halt rollout, roll back to old firmware
```

---

## §12 Reference Image Database Management

### 12.1 Reference Image Library Composition

The reference image library is the foundation of the entire IQA system — thresholds, MOS mapping, and regression judgments all depend on it. Inadequate coverage means detection blind spots; stale references mean thresholds lose validity. Four image categories are all required:

| Category | Recommended Count | Capture Device | Purpose |
|----------|------------------|----------------|---------|
| Standard chart references (controlled illumination) | 200+ per sensor model | Calibrated professional camera (DSLR/mirrorless) | FR metric baseline |
| Natural scenes (diverse lighting) | 500+ | Professional camera RAW + manual ISP | MOS annotation baseline |
| Edge cases (extreme dark / backlit / motion) | 100+ per distortion type | Professional camera + simulated distortion | Robustness testing |
| Real user scenes (anonymized) | 1000+ | Production devices | In-field quality baseline |

### 12.2 Reference Library Version Control

```
Reference image library directory structure:
reference_db/
├── version.json              # current library version + changelog
├── sensor_A_ov50c40/
│   ├── sfr_ISO100_D65/       # SFR test scenes (ISO × illuminant combinations)
│   ├── macbeth_D65/          # color chart images
│   ├── flat_ISO3200/         # noise test scenes
│   └── natural_scenes/       # natural scenes
└── sensor_B_imx989/
    └── ...
```

**Reference image update rules:**
1. When a new sensor comes online, build a separate reference library for that sensor (do not share across sensor models).
2. Reference library updates require IQA team review; after updating, all historical version metrics must be recomputed.
3. Reference library files are identified by hash to prevent accidental modification.

### 12.3 New Sensor IQA Calibration Procedure

When introducing a new image sensor, complete the following calibration steps:

```
Step 1: Capture new sensor reference image library (see §12.1)
Step 2: Collect MOS annotations (100+ images, 15+ raters)
Step 3: Re-fit MOS mapping model for each NR metric (BRISQUE, NIQE)
        → The new sensor's NSS statistics differ from the training distribution
Step 4: Re-determine pass/fail thresholds using ROC analysis
        → Target: false positive rate (FPR) < 2%, true positive rate (TPR) > 95%
Step 5: Validate new thresholds on internal test image set for consistency
Step 6: Commit new sensor configuration to the IQA config file (version-controlled with firmware)
```

---

## §13 Production Quality Gate Architecture

### 13.1 Three-Level Quality Gate System

Running the full light-chamber test suite (30–60 minutes) on every commit is too expensive, but running only a fast check on every commit risks missing real problems. The three-level gate resolves the tradeoff between coverage and speed: fast gates run frequently at high-impact change points (every commit), thorough gates run at lower-frequency but higher-stakes milestones (release candidates):

```
┌─────────────────────────────────────────────────────────────────┐
│ Level 1 Gate: Development Gate                                   │
│ Trigger: code commit / unit test                                 │
│ Test set: 50 standard charts (fast)                              │
│ Metrics: MTF50, SNR, ΔE₀₀                                       │
│ Time: < 10 minutes                                               │
│ Pass condition: no significant regression (simplified thresholds)│
└─────────────────────────────────────────────────────────────────┘
           ↓ pass →
┌─────────────────────────────────────────────────────────────────┐
│ Level 2 Gate: Integration Gate                                   │
│ Trigger: branch merge / nightly build                            │
│ Test set: 200+ full test suite                                   │
│ Metrics: full set (PSNR, SSIM, LPIPS, MTF50, SNR, ΔE₀₀, BRISQUE)│
│ Time: 30–60 minutes (including light-chamber capture)            │
│ Pass condition: statistical significance test (see §9.2)         │
└─────────────────────────────────────────────────────────────────┘
           ↓ pass →
┌─────────────────────────────────────────────────────────────────┐
│ Level 3 Gate: Production Gate                                    │
│ Trigger: release candidate                                       │
│ Test set: full test suite + manual A/B evaluation                │
│ Metrics: full objective set + MOS subjective evaluation          │
│ Time: 3–5 days (including human evaluation)                      │
│ Pass condition: MOS ≥ 3.5/5.0; no P0/P1 defects; all objective  │
│                metrics pass                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 13.2 Quality Gate Decision Matrix

| Metric type | Pass | Alert (P2) | Block (P1) | Emergency block (P0) |
|-------------|------|-----------|-----------|---------------------|
| MTF50 change | ≤ 3% drop | 3–5% drop | > 5% drop | > 15% drop |
| SNR change | ≤ 0.5 dB drop | 0.5–1 dB drop | > 1 dB drop | > 3 dB drop |
| ΔE₀₀ change | ≤ 0.3 rise | 0.3–0.5 rise | > 0.5 rise | > 2.0 rise |
| MOS change | ≤ 0.1 drop | 0.1–0.3 drop | > 0.3 drop | > 1.0 drop |
| P0 defect count | 0 | — | — | ≥ 1 |
| P1 defect count | 0 | — | ≥ 1 | — |

### 13.3 Factory Production Line IQA Inspection

At the factory production stage, every unit must pass a rapid IQA check before shipping (target: < 30 seconds per unit):

**Inspection content:**
1. Dead pixel check: hot pixel count in dark frame / dark pixel count in bright frame < threshold (typically < 5 dead pixels).
2. Lens shading uniformity: corner/center luminance ratio > 0.6 (after LSC correction).
3. Quick color accuracy test: shoot 2 gray targets (white point deviation Δuv < 0.005).
4. Quick resolution test: MTF50 above minimum threshold.
5. Focus accuracy: AF locks at standard distance (1 m), MTF50 > baseline × 0.8.

---

## §14 Benchmark Summary Table

Consolidated reference for IQA metrics used across the ISP quality system:

| Metric | Type | Range | Better | Typical threshold | Compute | Use case |
|--------|------|--------|--------|------------------|---------|---------|
| PSNR | FR | 20–50 dB | Higher | > 30 dB acceptable | CPU < 1 ms | Codec/NR regression |
| SSIM | FR | [−1, 1] | Higher (≈1) | > 0.88 (practical) | CPU < 2 ms | Overall fidelity |
| LPIPS | FR | [0, 1] | Lower | < 0.12 | GPU ~10 ms | Perceptual quality |
| BRISQUE | NR | [0, 100] | Lower | < 40 acceptable | CPU < 5 ms | Stage-1 online filter |
| NIQE | NR | [0, ∞) | Lower | < 4.0 | CPU < 5 ms | Unsupervised filter |
| MTF50 | FR | [0, 0.5] cy/px | Higher | > 0.38 cy/px | CPU < 20 ms | Sharpness / demosaic |
| ΔE₀₀ | FR | [0, ∞) | Lower | < 3.5 mean | CPU < 10 ms | Color accuracy |
| SNR | FR | dB | Higher | > 36 dB @ ISO 100 | CPU < 5 ms | Noise performance |
| HyperIQA | NR | [0, 1] | Higher | scene-dependent | GPU ~20 ms | Deep quality score |
| Q-Align | NR | [1, 5] | Higher | > 3.5 | GPU ~500 ms | Tuning diagnostics |
