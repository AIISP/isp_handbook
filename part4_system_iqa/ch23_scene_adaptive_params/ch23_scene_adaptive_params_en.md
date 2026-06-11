# Part 4, Chapter 23: Scene-Adaptive ISP Parameter Switching

> **Position:** This chapter provides a systematic treatment of how ISP parameter sets are dynamically selected, interpolated, and switched in response to real-time scene detection results — enabling a single camera pipeline to deliver optimal quality across all shooting scenarios. Parameter version management is covered in Vol.4 Ch.20; the semantics of individual ISP module parameters are detailed in Vol.2 Ch.01–Ch.12.
> **Prerequisites:** Vol.4 Ch.20 (ISP Multi-Scene Parameter Version Management), Vol.2 Ch.01–Ch.12 (Traditional ISP Modules), Vol.4 Ch.02 (Auto-Exposure Algorithms)
> **Audience:** ISP Algorithm Engineers, Camera System Engineers
> **Scope:** Scene detection algorithms, parameter-switching architecture, smoothing strategies, and key per-scene tuning guidance. 3A exposure/focus control loops are out of scope (see Vol.4 Ch.01); multi-camera switching is out of scope (see Vol.4 Ch.14).

---

## §1 Theory

### 1.1 Why Scene-Adaptive Parameter Switching Is Needed

A modern smartphone ISP pipeline chains more than ten processing modules in series — BLC, PDPC, LSC, demosaicking, AWB, CCM, denoising, gamma/tone-mapping, sharpening, color enhancement, and others. Each module exposes tunable parameters. A **fixed-parameter pipeline**, calibrated at the factory against some "average scene" (e.g., standard D65 even illumination, nominal exposure), is forced to accept a quality compromise that is suboptimal for every specific scenario:

- **Night (low-light):** Fixed denoising strength is either too weak (random noise remains visible at high ISO) or too strong (fine texture is erased).
- **Backlight (high dynamic range):** A fixed metering strategy clips highlights or crushes shadows; multi-exposure HDR merging is never triggered.
- **Portrait (skin tone):** A general-purpose CCM mis-renders skin hue; aggressive sharpening on faces creates a coarse, unpleasant texture.
- **Document (high-contrast text):** Generic denoising blurs character edges; insufficient sharpening reduces OCR accuracy.

**Quantifying scene diversity.** Let the scene feature space be $\mathcal{S} \subset \mathbb{R}^d$, spanned by dimensions such as:

| Feature Dimension | Proxy Metric | Typical Range |
|-------------------|--------------|---------------|
| Scene brightness | Mean exposure value $\mathrm{EV}$, $\log_2(\text{lux})$ | $[-4,+12]$ EV |
| Color temperature | AWB-estimated CCT (K) | $[2000,9000]$ K |
| Contrast | Image histogram std-dev $\sigma_I$ | $[5,80]$ DN |
| Texture complexity | Mean local gradient magnitude $\bar{g}$ | $[0,50]$ |
| Face area fraction | Face-detection confidence × area ratio $r_f$ | $[0,1]$ |
| Motion | Normalized inter-frame optical flow density $\bar{m}$ | $[0,1]$ |

Different scenes cluster in this space. A fixed parameter vector $\mathbf{P}^*$ occupies only a single point — a compromise that cannot simultaneously optimize every cluster. **Scene-adaptive parameter switching** elevates the parameter vector from a constant to a function of the scene feature:

$$\mathbf{P} = f(\mathbf{s}), \quad \mathbf{s} \in \mathcal{S}$$

### 1.2 Scene Detection System

#### 1.2.1 Traditional Statistics-Based Methods

Traditional methods exploit global image statistics or ISP-internal statistics (already computed by the 3A engine), requiring no separate neural network and adding negligible compute overhead:

**Luminance histogram analysis.** Partition the Y-channel histogram into a dark bin $H_\text{dark}$ ($< 32/255$), midtone bin $H_\text{mid}$, and highlight bin $H_\text{hi}$ ($> 220/255$). The energy ratio across bins signals low-light or high dynamic range conditions.

**Color distribution analysis.** In the $uv$ chromaticity plane, compute the mean distance of sampled pixels from the achromatic axis and the dominant color angle $\theta_c$. Green-biased CCT (fluorescent indoor), orange-biased (tungsten), and blue-biased (clear sky) each form distinct clusters.

**Texture gradient features.** Compute the mean $3\times 3$ Sobel gradient magnitude $\bar{g}$. High $\bar{g}$ indicates landscape or architecture (rich high-frequency content); low $\bar{g}$ corresponds to night sky or defocused backgrounds.

**Example rule-based decision tree:**

```
if EV < 1.5 and σ_I < 30:
    scene = "night"
elif face_ratio > 0.15 and EV > 3:
    scene = "portrait_day"
elif H_hi / H_total > 0.15 and H_dark / H_total > 0.10:
    scene = "backlight_hdr"
elif CCT > 6500 and g_bar > 20:
    scene = "landscape"
else:
    scene = "normal"
```

#### 1.2.2 Deep-Learning Classification

A lightweight CNN classifier ingests an ISP thumbnail (e.g., $224\times 224$ RGB or $112\times 112$ NV12) and outputs a posterior probability vector $\mathbf{q} \in \Delta^{K-1}$ over $K$ scene classes.

**Backbone selection:**

| Backbone | Params | Latency (NPU, INT8) | Top-1 Acc (7-class) |
|----------|--------|---------------------|---------------------|
| MobileNetV3-Small | 2.5 M | ~0.8 ms | 88.3% |
| EfficientNet-B0 | 5.3 M | ~1.5 ms | 91.2% |
| ShuffleNetV2-0.5× | 1.4 M | ~0.5 ms | 86.7% |
| ResNet-18 (baseline) | 11.7 M | ~4.0 ms | 93.1% |

For production deployment, MobileNetV3-Small or ShuffleNetV2 is recommended; both complete inference within 1 ms on flagship NPUs (Qualcomm Hexagon, MediaTek APU), satisfying real-time video pipeline requirements.

**Training strategy.** Adopt **multi-label classification**: certain scenes (e.g., "night portrait") simultaneously activate multiple labels, allowing continuous probability outputs to drive parameter interpolation rather than hard switching.

#### 1.2.3 Multi-Signal Fusion

Relying on image content alone introduces ambiguity (a white wall looks similar at night and during the day). Incorporating auxiliary sensor signals substantially improves classification robustness:

| Signal Source | Information | Fusion Mechanism |
|---------------|-------------|------------------|
| Ambient light sensor (ALS) | Illuminance $E_v$ (lux) | Direct mapping to EV interval |
| Face detection | Count, location, size | Boosts prior probability for portrait classes |
| Accelerometer / Gyroscope | Device motion magnitude | Distinguishes handheld shake from stable scenes |
| EXIF / User preset | Shooting mode selection | Hard constraint: overrides scene classification |
| Previous frame label | Historical scene sequence | Temporal smoothing, suppresses spurious detections |

The fused scene probability vector is updated as:

$$\mathbf{q}_\text{fused} = \mathrm{softmax}\!\left(\mathbf{z}_\text{img} + \lambda_\text{als}\mathbf{z}_\text{als} + \lambda_\text{face}\mathbf{z}_\text{face}\right)$$

where $\mathbf{z}$ denotes the logit vector from each source and $\lambda$ are tunable fusion weights.

#### 1.2.4 Standard Scene Category Definitions

This chapter uses 7 canonical scene categories (practical products may extend to 20+):

| Scene Label | Typical Condition | Primary Optimization Goal |
|-------------|-------------------|---------------------------|
| `night` | $\mathrm{EV} < 2$, no strong light sources | Denoising, long exposure, multi-frame NR |
| `night_portrait` | $\mathrm{EV} < 2$, face confidence $> 0.6$ | Face brightness boost, skin denoising |
| `portrait_day` | $\mathrm{EV} \geq 3$, face area $> 0.1$ | Skin color, background blur |
| `landscape` | High texture, wide field, low face ratio | Sharpening, saturation, sky rendering |
| `backlight_hdr` | Dual-peak histogram (highlights + shadows) | Multi-exposure HDR merge, local tone-mapping |
| `indoor` | Moderate EV, warm CCT | AWB offset correction, mild denoising |
| `document` | Very high contrast, close focus, low motion | Maximum sharpening, minimum denoising |

### 1.3 Parameter-Switching Architectures

#### 1.3.1 Look-Up Table (LUT-Based) Switching

The simplest approach: calibrate one complete ISP parameter set (Tuning Bin) $\mathbf{P}^{(k)}$ per scene label $k$, then select directly at runtime:

$$\mathbf{P}_\text{out} = \mathbf{P}^{(k^*)}, \quad k^* = \arg\max_k q_k$$

**Advantages:** Conceptually simple; parameter semantics remain fully transparent to tuning engineers; easy to manage in XML/JSON databases.

**Disadvantages:** Hard switch at scene boundaries can produce a visible single-frame quality jump (switching flicker).

#### 1.3.2 Interpolation-Based Continuous Switching

Interpolating between adjacent scene parameter sets yields a continuously varying output parameter vector, eliminating hard-switch transients.

**Binary linear interpolation (two-scene blend):**

$$\mathbf{P}_\text{out} = (1-w)\,\mathbf{P}^{(k_1)} + w\,\mathbf{P}^{(k_2)}, \quad w = q_{k_2} \in [0,1]$$

**Multi-scene softmax-weighted interpolation:**

$$\mathbf{P}_\text{out} = \sum_{k=1}^{K} q_k \cdot \mathbf{P}^{(k)}, \quad \sum_k q_k = 1$$

Not all parameters are suitable for linear interpolation. Parameters with non-linear perceptual semantics (e.g., gamma curve control points, tone-mapping nodes) should be interpolated in an appropriate transform domain (log domain, CIE Lab) to ensure perceptual continuity:

$$\mathbf{P}_\text{out}^{(\gamma)} = \exp\!\left(\sum_k q_k \ln \mathbf{P}^{(k,\gamma)}\right)$$

#### 1.3.3 Model-Based Continuous Parameter Generation (Hypernetwork)

A more advanced approach feeds the scene feature vector $\mathbf{s}$ directly into a lightweight neural network (Hypernetwork) to generate the full ISP parameter vector:

$$\mathbf{P}_\text{out} = f_\theta(\mathbf{s})$$

Here $\mathbf{s} \in \mathbb{R}^d$ encodes multi-dimensional scene features (brightness, CCT, texture complexity, face ratio, etc.), $f_\theta$ is a small MLP with 2–3 fully connected layers (~10 K–100 K parameters), and $\mathbf{P}_\text{out} \in \mathbb{R}^M$ is the $M$-dimensional continuous parameter vector.

The training objective is typically:

$$\mathcal{L} = \underbrace{\mathcal{L}_\text{IQA}(\mathrm{ISP}(\mathbf{x};\mathbf{P}_\text{out}), \mathbf{y})}_{\text{quality loss}} + \lambda_\text{smooth} \underbrace{\|\mathbf{P}_\text{out} - \mathbf{P}_\text{ref}\|_2^2}_{\text{smoothness regularizer}}$$

**Comparison of switching architectures:**

| Dimension | LUT-Based | Interpolation | Hypernetwork |
|-----------|-----------|---------------|--------------|
| Switch smoothness | Poor (hard) | Moderate | Excellent |
| Parameter interpretability | High | Moderate | Low |
| Compute overhead | Negligible | Low | Low (small MLP) |
| Tuning difficulty | Medium (one set per class) | High | Very high (end-to-end training) |
| Industry maturity | High (widely deployed) | Moderate | Low (mainly research) |

### 1.4 Parameter-Switching Granularity

#### 1.4.1 Global Switching vs. Local Region-Adaptive Switching

**Per-frame global switching:** The entire frame uses a single parameter set. This is the dominant industry approach. Suitable when scene content is spatially uniform (all-night, all-document, etc.).

**Per-region local adaptive switching:** The frame is partitioned into tiles; each tile independently estimates scene features and applies its own parameters. Examples:
- In a portrait scene, the face bounding box uses skin-protective parameters while the background uses generic or blur-enhancing parameters.
- In a backlit scene, highlight tiles and shadow tiles apply separate local tone-mapping curves.

Local adaptive switching requires ISP hardware support for **tile-based parameter injection** (e.g., Qualcomm CamX `RegionConfig`, MediaTek Imagiq `ZoneControl`) and must handle smooth blending between adjacent tile boundaries to prevent blocking artifacts.

#### 1.4.2 Per-Frame Switching vs. Temporally Continuous Switching

**Per-frame switching:** Scene classification and parameter selection are re-evaluated every frame. Response is fast (good for rapidly changing scenes) but risks single-frame flicker when consecutive frames flip between scene labels.

**Temporally continuous switching (EMA smoothing):** Parameter values transition smoothly over time using Exponential Moving Average. See §3.1 for details.

---

## §2 Calibration

### 2.1 Scene Parameter Set Calibration Workflow

Calibrating a scene-adaptive system requires completing full ISP tuning independently for each scene category:

**Phase 1: Scene dataset acquisition**
- Capture RAW data using standard test charts (X-Rite ColorChecker, ISO 12233 resolution chart) under the corresponding lighting conditions for each scene class.
- Natural-scene samples: collect at least 50 independent scenes per class, covering diverse times of day, locations, and device orientations.
- Boundary samples: prioritize ambiguous scenes near class boundaries (e.g., dimly lit night portraits) to calibrate interpolation coefficients between adjacent parameter sets.

**Phase 2: Objective-metric-driven tuning**
- For each scene parameter set, optimize toward SNR, MTF50, and $\Delta E_{00}$ as objective targets.
- Use automated tuning tools (Qualcomm QIAA, MTK IQTuner, or internal genetic-algorithm optimizers) to search the parameter space.
- Parameter constraints: each parameter must remain within its pre-defined safe range $[P_\min^{(k)}, P_\max^{(k)}]$ to prevent extreme values from introducing artifacts (see §4.3).

**Phase 3: Subjective blind test validation**
- Submit sample images from each scene parameter set to a blind evaluation by 5+ expert image raters using MOS scoring (1–5 scale).
- Target: MOS $\geq 4.0$ per scene class; MOS improvement $\geq 0.3$ versus the fixed-parameter baseline.

### 2.2 Parameter Space Constraints and Inter-Bin Smoothness

**Range constraints:** Define $[P_\min, P_\max]$ and maximum single-step delta $\Delta P_\max$ for every parameter to prevent:
- `NR_strength` exceeding 1.0 (total texture erasure)
- `Sharp_gain` exceeding 3.0 (ringing artifacts)
- `EV_comp` exceeding $\pm 2.0$ EV (severe clipping)

**Inter-scene smoothness constraint:** For two adjacent scene parameter sets connected via interpolation, define the normalized parameter discrepancy:

$$D_{12} = \frac{1}{M}\sum_{m=1}^{M} \frac{|P_m^{(k_1)} - P_m^{(k_2)}|}{P_{\max,m} - P_{\min,m}}$$

Require $D_{12} < \delta_\text{smooth}$ (typically 0.3) to guarantee a perceptually continuous interpolation path. If $D_{12}$ is too large, introduce an intermediate anchor parameter set between the two endpoints.

**Calibration validation matrix example:**

| Parameter | Night | Portrait Day | Landscape | Document | Max Allowed Diff |
|-----------|-------|-------------|-----------|----------|-----------------|
| NR_strength | 0.85 | 0.40 | 0.35 | 0.15 | 0.70 |
| Sharp_gain | 0.8 | 1.2 | 1.8 | 2.5 | 1.7 |
| Saturation | 1.0 | 1.1 | 1.3 | 0.9 | 0.4 |
| Gamma_knee | 0.45 | 0.50 | 0.52 | 0.55 | 0.10 |
| CCM_skin_bias | +0.02 | +0.08 | 0.0 | 0.0 | 0.08 |

---

## §3 Tuning Guide

### 3.1 Switch-Smoothing Strategies

#### 3.1.1 EMA Inter-Frame Smoothing

The primary risk of scene switching is inter-frame parameter transients that cause flicker. **Exponential Moving Average (EMA)** smooths parameter transitions over time:

$$\mathbf{P}_{t+1} = \alpha\,\mathbf{P}_t + (1-\alpha)\,\mathbf{P}_\text{target}(t)$$

where $\alpha \in (0,1)$ is the forgetting factor and $\mathbf{P}_\text{target}(t)$ is the target parameter vector determined by the current frame's scene classification.

**Recommended $\alpha$ values by parameter type:**

| Parameter Type | Recommended $\alpha$ | Rationale |
|----------------|----------------------|-----------|
| Exposure / gain (fast tracking) | 0.5–0.7 | Exposure must track luminance changes quickly |
| Denoising / sharpening (slow) | 0.7–0.85 | Small incremental changes are imperceptible; stability preferred |
| Tone-mapping curve | 0.8–0.9 | Tone curve changes must be extremely gradual |
| White-balance gains | 0.85–0.95 | AWB already has its own smoothing; be conservative here |

At the typical value $\alpha = 0.7$, the $e^{-1}$ settling time from current to target parameters is approximately 3 frames (~100 ms at 30 fps).

#### 3.1.2 Hysteresis Anti-Oscillation Mechanism

When scene features oscillate near a class decision boundary (e.g., the user panning between indoor fluorescent light and outdoor sunlight), the scene label alternates between "indoor" and "normal" — producing periodic parameter oscillations visible even with EMA smoothing.

**Hysteresis decision rule.** Let the currently confirmed scene be $k_\text{current}$ and the candidate new scene be $k_\text{new}$:

$$\text{Switch condition:} \quad q_{k_\text{new}} > q_{k_\text{current}} + \Delta_\text{hys}$$

where $\Delta_\text{hys} \in [0.1, 0.2]$ is the hysteresis margin. The new scene must decisively outperform the current scene in confidence before a switch is triggered.

**Multi-frame majority voting.** Record the scene classification result for the most recent $N_\text{vote} = 3\text{–}5$ frames and switch only when the majority of those frames agree on the new scene:

$$k_\text{confirmed} = \arg\max_k \sum_{t=T-N+1}^{T} \mathbf{1}[k_t^* = k]$$

At $N_\text{vote} = 3$, the switch response latency is ~100 ms at 30 fps — imperceptible to users.

### 3.2 Night Scene Parameter Set: Key Parameters

| Parameter | Recommended Value / Strategy | Rationale |
|-----------|------------------------------|-----------|
| NR_spatial_strength | 0.75–0.90 | Dense high-ISO noise requires strong spatial denoising |
| NR_temporal_strength | 0.80–0.95 | Activate TNR; multi-frame accumulation reduces random noise |
| Sharp_gain | 0.6–0.9 | Reduce sharpening gain to avoid amplifying noise |
| ISO_max | 3200–12800 | Sensor-specific DR ceiling |
| Exposure_time_max | 1/8–1/4 s | Maximum handheld shutter within stabilization budget |
| Tone_curve_mode | `log_boost` | Lift shadows while preserving highlights |
| Saturation | 0.9–1.0 | Reduce saturation to suppress chroma noise |
| Multi-frame_NR_frames | 3–8 | Burst frame count; more frames = lower noise (limited by motion) |

In the night scene, **joint ISO–shutter optimization** is paramount: excessive ISO raises random noise; excessive shutter time causes motion blur. The recommended ISO selection policy is:

$$\mathrm{ISO}^* = \min\!\left(\mathrm{ISO}_\max,\; \frac{L}{t_\text{exp,max} \cdot A}\right)$$

where $L$ is scene luminance, $t_\text{exp,max}$ is the stabilization-limited maximum shutter time, and $A$ is the aperture factor.

### 3.3 Portrait Scene Parameter Set: Key Parameters

| Parameter | Recommended Value / Strategy | Rationale |
|-----------|------------------------------|-----------|
| CCM_skin_bias | $+0.02$–$+0.05$ (red channel) | Slight red boost produces healthier-looking skin |
| Face_NR_strength | 0.60–0.75 | Moderate face denoising preserves skin micro-texture |
| Face_Sharp_gain | 0.8–1.0 | Reduced sharpening inside face bounding box |
| Background_blur | Enabled (synthetic bokeh) | Separates subject from distracting background |
| Eye_enhance | Enabled (local sharpening) | Iris detail boost improves perceived portrait quality |
| Lip_color_enhance | Mild saturation +0.1 | Subtle lip color enhancement |
| Skin_smoothing | Mild ($\sigma = 1.0$) | Tasteful smoothing; avoid over-processing |
| Face_exposure_bias | $+0.3$–$+0.5$ EV | Face-region metering bias prevents under-exposed faces |

Portrait parameters **must be tied to face detection results**: apply skin-protective parameters only within the face bounding box; apply generic (or background-blur) parameters outside it.

### 3.4 Backlight / HDR Scene Parameter Set

The core challenge in backlit scenes is that dynamic range (DR $> 90$ dB) exceeds the single-exposure sensor DR (typically $70$–$80$ dB). Key strategies:

**Trigger multi-exposure HDR merge:** When backlight confidence $q_\text{backlight} > 0.7$, activate multi-frame HDR capture mode (see Vol.2 Ch.10 for HDR merge algorithms).

**Activate local tone mapping (LTM):** Engage the LTM module (see Vol.2 Ch.18) to compress highlights and lift shadows, recovering detail at both ends of the tonal range.

**Recommended parameters:**

| Parameter | Recommended Value | Notes |
|-----------|-------------------|-------|
| HDR_merge_ratio | Auto (1:3 or 1:6) | Select exposure ratio based on estimated scene DR |
| LTM_strength | 0.7–0.9 | Local contrast restoration strength |
| Highlight_compression | $-1.5$–$-2.0$ EV | Highlight region metering compensation |
| Shadow_boost | $+0.5$–$+1.0$ EV | Shadow region lifting |
| Deghosting_enable | True | Essential for multi-frame HDR with moving subjects |

---

## §4 Common Artifacts

### 4.1 Parameter Switching Flicker

**Symptom description.** When scene features oscillate near the boundary between two scene classes, the scene label alternates frame-by-frame (e.g., "night" → "indoor" → "night" → ...). This causes ISP parameters to oscillate between two tuning bins, producing periodically varying brightness, color, or sharpness that is perceived as **switching flicker**.

**Perceptibility threshold.** When $\Delta\mathrm{EV} > 0.2$ between consecutive frames at a frequency $> 2$ Hz, the flicker is visible to the human eye.

**Root cause analysis:**
1. Scene classification confidence near the boundary is noisy ($|q_{k_1} - q_{k_2}| < 0.1$).
2. EMA forgetting factor $\alpha$ is too small (too-fast tracking amplifies oscillations).
3. No hysteresis protection is in place.

**Mitigation:**
- Increase hysteresis margin $\Delta_\text{hys}$ to 0.15–0.20.
- Increase EMA $\alpha$ to $\geq 0.85$ for visually sensitive parameters (tone curve, saturation).
- Enable majority voting ($N_\text{vote} = 3$–$5$).
- Implement a "no-switch" conservative policy: when $\max_k q_k < 0.6$, hold the current parameter set.

### 4.2 Scene Misclassification

**Representative misclassification cases:**

| Misclassification | Erroneous Label | Correct Label | Consequence |
|-------------------|-----------------|---------------|-------------|
| Night-time white wall | `normal` (uniform bright) | `night` | Insufficient denoising; high-ISO noise visible |
| Dusk blue sky | `night` | `landscape` | Over-denoising; sky detail lost |
| Bright indoor document | `indoor` | `document` | Insufficient sharpening; lower OCR accuracy |
| Handheld backlit portrait | `portrait_day` | `backlight_hdr` | HDR merge not triggered; highlights clipped |

**Mitigation strategies:**
1. **Multi-signal fusion:** Incorporate ALS-measured illuminance to break image-content ambiguity.
2. **Multi-frame majority voting:** As described in §3.1.2, require 3–5 consecutive frames to agree before confirming a switch.
3. **Confidence gating:** When the maximum classifier output $< \tau_\text{conf}$ (typically 0.6–0.7), fall back to the "normal" generic parameter set.
4. **Incremental hard-negative mining:** Continuously collect misclassified examples and add them to the training set.

### 4.3 Parameter Incompatibility Artifacts

When parameter values differ too greatly between two scene bins, the intermediate interpolation state can introduce new artifacts, even with EMA smoothing applied:

- **Ringing.** Interpolating between the night bin (`Sharp_gain = 0.8`) and the document bin (`Sharp_gain = 2.5`) passes through `Sharp_gain ≈ 1.65`. If the nonlinear sharpening kernel remains active in this range, ringing appears at high-contrast edges.
  - Fix: Apply an independent amplitude clamp on the nonlinear sharpening path during interpolation.

- **Color shift (Color Blocking).** Linear interpolation of two CCM matrices may violate the row-sum-to-unity constraint, introducing a global colorcast.
  - Fix: Interpolate in the white-point-normalized CCM domain; enforce row normalization after interpolation.

- **Noise amplification.** When TNR temporal strength switches from a high value (night: 0.9) to a low value (daytime: 0.3), previously suppressed residual noise suddenly becomes visible.
  - Fix: Apply a 2× slower switching rate for TNR parameters (larger $\alpha$) compared to other parameters.

---

## §5 Evaluation

### 5.1 Scene Detection Accuracy

**Benchmark dataset construction.** Cover all 7 scene classes with $\geq 100$ images each; boundary samples must represent at least 20% of the total.

**Metric definitions:**

$$\mathrm{Top\text{-}1\ Accuracy} = \frac{1}{N}\sum_{i=1}^N \mathbf{1}[\hat{k}_i = k_i^*]$$

$$\text{Confusion matrix:} \quad C_{jk} = \frac{|\{i: k_i^* = j,\, \hat{k}_i = k\}|}{|\{i: k_i^* = j\}|}$$

**Target values:** 7-class Top-1 Accuracy $> 90\%$. Night and HDR classes carry higher misclassification cost and should achieve per-class accuracy $> 95\%$.

**Real-time requirement:** End-to-end scene detection (including CNN inference) must complete in $< 5$ ms (NPU execution) to satisfy a 30 fps video pipeline.

### 5.2 Switching Smoothness Quantification

**Inter-frame PSNR variation ($\Delta$PSNR).** Around each scene-switch event (3 frames before, 3 frames after), compute the deviation of adjacent-frame PSNR from the steady-state average:

$$\Delta\mathrm{PSNR}_{t} = |\mathrm{PSNR}(I_t, I_{t-1})|_\text{switch frame} - |\mathrm{PSNR}(I_t, I_{t-1})|_\text{steady-state mean}$$

**Target:** $\Delta\mathrm{PSNR} < 0.5$ dB.

**Subjective flicker threshold (Video Quality Expert Group).** Apply the ITU-R BT.500 Double Stimulus Continuous Quality Scale (DSCQS) methodology specifically targeting temporal annoyance during scene transitions. Target MOS-T $> 4.0$ (no annoyance).

**Flicker frequency analysis.** Extract parameter time series (e.g., exposure value, gamma nodes) and inspect their power spectrum. The 2–10 Hz band should contain no significant periodic component (this band corresponds to peak human sensitivity to luminance flicker).

### 5.3 Per-Scene Quality Gain Assessment

Compare scene-specific parameter sets against the fixed generic parameter baseline on objective IQA metrics:

| Scene | Metric | Fixed Baseline | Scene-Adaptive | Gain |
|-------|--------|---------------|----------------|------|
| Night | SNR (dB) | 28.5 | 32.1 | +3.6 dB |
| Portrait Day | $\Delta E_{00}$ (skin) | 4.2 | 2.8 | −33% |
| Landscape | MTF50 (lp/ph) | 1820 | 2150 | +18% |
| Backlight | Highlight retention (%) | 62% | 84% | +22% |
| Document | OCR accuracy | 91.2% | 96.7% | +5.5% |

**Overall subjective MOS:**

$$\mathrm{MOS}_\text{overall} = \frac{1}{K}\sum_{k=1}^K \mathrm{MOS}_k$$

Target: overall MOS improvement $\geq 0.3$ points vs. fixed-parameter baseline.

---

## §6 Code Example

The following Python code demonstrates the core logic of scene-adaptive parameter switching: scene feature extraction, an EMA parameter interpolator with hysteresis switching, and a scene parameter bin configuration.

```python
"""
scene_adaptive_isp.py
Scene-Adaptive ISP Parameter Switching — Core Logic Demonstration
Volume 4, Chapter 23 — Companion Code
"""

import numpy as np
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ──────────────────────────────────────────────
# 1. Scene parameter bin configuration
# ──────────────────────────────────────────────

SCENE_PARAM_BINS: Dict[str, Dict] = {
    "normal": {
        "NR_spatial":    0.50,
        "NR_temporal":   0.50,
        "sharp_gain":    1.20,
        "saturation":    1.00,
        "gamma_knee":    0.50,
        "ev_bias":       0.00,
        "ccm_skin_bias": 0.00,
    },
    "night": {
        "NR_spatial":    0.85,
        "NR_temporal":   0.90,
        "sharp_gain":    0.80,
        "saturation":    0.95,
        "gamma_knee":    0.45,
        "ev_bias":       0.30,
        "ccm_skin_bias": 0.00,
    },
    "portrait_day": {
        "NR_spatial":    0.45,
        "NR_temporal":   0.40,
        "sharp_gain":    1.00,
        "saturation":    1.05,
        "gamma_knee":    0.52,
        "ev_bias":       0.35,
        "ccm_skin_bias": 0.04,
    },
    "landscape": {
        "NR_spatial":    0.30,
        "NR_temporal":   0.30,
        "sharp_gain":    1.80,
        "saturation":    1.20,
        "gamma_knee":    0.53,
        "ev_bias":       0.00,
        "ccm_skin_bias": 0.00,
    },
    "backlight_hdr": {
        "NR_spatial":    0.40,
        "NR_temporal":   0.45,
        "sharp_gain":    1.10,
        "saturation":    1.00,
        "gamma_knee":    0.55,
        "ev_bias":      -0.50,
        "ccm_skin_bias": 0.00,
    },
    "document": {
        "NR_spatial":    0.15,
        "NR_temporal":   0.20,
        "sharp_gain":    2.50,
        "saturation":    0.85,
        "gamma_knee":    0.58,
        "ev_bias":       0.00,
        "ccm_skin_bias": 0.00,
    },
}

PARAM_KEYS = list(SCENE_PARAM_BINS["normal"].keys())


# ──────────────────────────────────────────────
# 2. Scene feature extraction (histogram-based)
# ──────────────────────────────────────────────

def extract_scene_features(
    y_channel: np.ndarray,
    uv_channel: Optional[np.ndarray] = None,
    face_ratio: float = 0.0,
    als_lux: float = 500.0,
) -> Dict[str, float]:
    """
    Extract scene classification features from the luma channel (Y).
    y_channel: HxW float32, range [0, 255].
    Returns a feature dictionary.
    """
    hist, _ = np.histogram(y_channel.flatten(), bins=256, range=(0, 255))
    hist_norm = hist / hist.sum()

    dark_ratio = hist_norm[:32].sum()        # Y < 32/255
    hi_ratio   = hist_norm[220:].sum()       # Y > 220/255
    mean_y     = float(y_channel.mean())
    std_y      = float(y_channel.std())

    # Texture complexity via gradient magnitude
    gy = np.diff(y_channel, axis=0)
    gx = np.diff(y_channel, axis=1)
    grad_mean = float(
        np.sqrt(gy[:, :-1]**2 + gx[:-1, :]**2).mean()
    )

    # Approximate exposure value
    ev = float(np.log2(max(mean_y, 1.0) / 18.0) + 4.0)

    return {
        "ev":         ev,
        "dark_ratio": float(dark_ratio),
        "hi_ratio":   float(hi_ratio),
        "std_y":      std_y,
        "grad_mean":  grad_mean,
        "face_ratio": face_ratio,
        "als_lux":    als_lux,
    }


# ──────────────────────────────────────────────
# 3. Rule-based scene classifier
# ──────────────────────────────────────────────

def classify_scene_rule(features: Dict[str, float]) -> Dict[str, float]:
    """
    Rule-based scene classifier.
    Returns per-scene confidence scores (normalized to sum to 1).
    Can be replaced with a neural network inference call.
    """
    ev     = features["ev"]
    dark_r = features["dark_ratio"]
    hi_r   = features["hi_ratio"]
    grad   = features["grad_mean"]
    face_r = features["face_ratio"]

    scores = {k: 0.0 for k in SCENE_PARAM_BINS}

    if ev < 2.0:
        scores["night"] += 0.8
        if face_r > 0.10:
            scores["night"] -= 0.3
            scores["portrait_day"] += 0.3   # simplified: night portrait
    if hi_r > 0.12 and dark_r > 0.08:
        scores["backlight_hdr"] += 0.7
    if face_r > 0.10 and ev >= 2.5:
        scores["portrait_day"] += 0.7
    if grad > 18 and face_r < 0.05 and ev > 3.0:
        scores["landscape"] += 0.6
    if features["std_y"] > 60 and grad > 25 and face_r < 0.01:
        scores["document"] += 0.65
    scores["normal"] += 0.1   # fallback prior

    total = sum(scores.values()) + 1e-8
    return {k: v / total for k, v in scores.items()}


# ──────────────────────────────────────────────
# 4. Hysteresis scene state machine + EMA smoother
# ──────────────────────────────────────────────

@dataclass
class SceneAdaptiveISP:
    alpha: float = 0.75          # EMA forgetting factor
    hysteresis: float = 0.15     # hysteresis margin
    vote_window: int = 3         # majority-vote frame window
    conf_threshold: float = 0.55 # minimum confidence gate

    current_scene: str = "normal"
    current_params: Dict[str, float] = field(default_factory=dict)
    vote_buffer: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.current_params = dict(SCENE_PARAM_BINS["normal"])

    def _majority_vote(self, candidate: str) -> str:
        """Majority vote over a sliding window; returns confirmed label."""
        self.vote_buffer.append(candidate)
        if len(self.vote_buffer) > self.vote_window:
            self.vote_buffer.pop(0)
        counts: Dict[str, int] = {}
        for s in self.vote_buffer:
            counts[s] = counts.get(s, 0) + 1
        return max(counts, key=counts.get)

    def update(
        self,
        scene_probs: Dict[str, float],
        frame_id: int = 0,
    ) -> Tuple[str, Dict[str, float]]:
        """
        Accept a scene probability distribution; return
        (confirmed scene label, EMA-smoothed ISP parameter dict).
        """
        # Step 1: confidence gate
        best_scene = max(scene_probs, key=scene_probs.get)
        best_conf  = scene_probs[best_scene]
        if best_conf < self.conf_threshold:
            best_scene = self.current_scene

        # Step 2: hysteresis check
        cur_conf = scene_probs.get(self.current_scene, 0.0)
        if best_scene != self.current_scene:
            if best_conf <= cur_conf + self.hysteresis:
                best_scene = self.current_scene

        # Step 3: majority vote
        confirmed = self._majority_vote(best_scene)

        # Step 4: EMA parameter smoothing
        target = SCENE_PARAM_BINS[confirmed]
        smoothed = {
            key: self.alpha * self.current_params[key]
                 + (1.0 - self.alpha) * target[key]
            for key in PARAM_KEYS
        }

        self.current_scene  = confirmed
        self.current_params = smoothed
        return confirmed, smoothed


# ──────────────────────────────────────────────
# 5. Demo: simulated frame-sequence scene transition
# ──────────────────────────────────────────────

if __name__ == "__main__":
    isp = SceneAdaptiveISP(alpha=0.75, hysteresis=0.15, vote_window=3)

    # Simulated sequence: 10 frames "night" → 6 boundary frames → 10 "landscape"
    mock_sequence = (
        [{"night": 0.85, "normal": 0.10, "landscape": 0.05,
          "portrait_day": 0.0, "backlight_hdr": 0.0, "document": 0.0}] * 10
        + [{"night": 0.45, "landscape": 0.42, "normal": 0.08,
            "portrait_day": 0.03, "backlight_hdr": 0.01, "document": 0.01},
           {"landscape": 0.52, "night": 0.38, "normal": 0.07,
            "portrait_day": 0.02, "backlight_hdr": 0.01, "document": 0.0}] * 3
        + [{"landscape": 0.88, "normal": 0.07, "night": 0.03,
            "portrait_day": 0.01, "backlight_hdr": 0.01, "document": 0.0}] * 10
    )

    print(f"{'Frame':>5} | {'Scene':>15} | {'NR_spatial':>10} | "
          f"{'sharp_gain':>10} | {'saturation':>10}")
    print("-" * 62)

    for fid, probs in enumerate(mock_sequence):
        scene, params = isp.update(probs, frame_id=fid)
        print(f"{fid:>5} | {scene:>15} | "
              f"{params['NR_spatial']:>10.3f} | "
              f"{params['sharp_gain']:>10.3f} | "
              f"{params['saturation']:>10.3f}")
```

**Code notes:**
- `extract_scene_features()`: Extracts 7 scene features from the luma channel and auxiliary sensors.
- `classify_scene_rule()`: Rule-based classifier; replace with a neural-network inference call (`model.predict(thumbnail)`) for production use.
- `SceneAdaptiveISP.update()`: A complete per-frame state machine encapsulating confidence gating, hysteresis, majority voting, and EMA smoothing. Call once per frame; returns the confirmed scene label and the smoothed parameter dictionary.
- In production, `SCENE_PARAM_BINS` should be loaded from an XML/JSON parameter database; parameter keys should map to the actual SoC HAL parameter IDs.

---

## References

1. He, J. et al., "Neural-Symbolic ISP: Scene-Aware Parameter Generation with LLM-Guided Tuning," *CVPR*, 2024.
2. Qualcomm Technologies, *CamX CHI-CDK Scene Mode Switching Configuration Reference*, Snapdragon Camera XML Open Sample, 2023.
3. Apple Inc., "Photographic Styles: technical overview," *WWDC 2021*, Session 10214, 2021.
4. Liang, Z. et al., "DML-ISP: Dynamic Multi-Label ISP Parameter Control," *ECCV*, 2022.
5. MediaTek, *Imagiq FeaturePipe Scene-Aware Tuning Technology White Paper*, Hot Chips 2023, 2023.
6. ITU-R Recommendation BT.500-14, *Methodologies for the Subjective Assessment of the Quality of Television Images*, ITU-R, 2019.
7. Howard, A. G. et al., "MobileNets: Efficient Convolutional Neural Networks for Mobile Vision Applications," *arXiv:1704.04861*, 2017.
8. Tan, M. and Le, Q. V., "EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks," *ICML*, 2019.

---

## §8 Glossary

| Term | Definition |
|------|------------|
| Scene-Adaptive | Dynamically adjusting system behavior parameters in response to the real-time detected scene category. |
| Parameter Set / Tuning Bin | A complete set of ISP parameters pre-calibrated for a specific scene category. |
| Hysteresis | A decision bias that requires the new scene's confidence to exceed the current scene's confidence by a margin $\Delta_\text{hys}$ before triggering a switch, preventing oscillation near class boundaries. |
| Exponential Moving Average (EMA) | A time-domain smoothing technique: $\mathbf{P}_{t+1} = \alpha\mathbf{P}_t + (1-\alpha)\mathbf{P}_\text{target}$. Controls how quickly parameters track target changes. |
| Hypernetwork | A meta-learning architecture that takes scene features as input and outputs the parameters of another (ISP) network; enables continuous, jointly-trained parameter generation. |
| Local Adaptive | Applying different parameters to distinct spatial regions of the image, as opposed to a single global parameter set. |
| Majority Voting | Determining the confirmed scene label by taking the mode of scene classification results across the most recent $N$ frames, improving robustness against single-frame misclassifications. |
| Switching Flicker | Periodically varying brightness, color, or sharpness caused by scene-label oscillation near a decision boundary driving parameters back and forth between two tuning bins. |
| Confidence Gating | A protective mechanism that refuses to execute a scene switch when the classification confidence falls below a threshold $\tau_\text{conf}$, defaulting to the current parameter set. |
| Tone Mapping | A nonlinear transformation that maps high dynamic range luminance signals into the limited range of a display device. |
