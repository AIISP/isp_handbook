# Part 5, Chapter 12: Privacy-Preserving Computational Photography

> The author's experience and background are limited; the content above represents only personal understanding. Experts from all relevant fields are warmly invited to improve this document. Corrections and additions via Issue or Pull Request are welcome.

---

## §1 Theory

### 1.1 Security Threat Landscape of the ISP Pipeline

As computational photography systems become deeply integrated with deep-learning perception models, cameras are no longer simple optical capture devices — they serve as the front-end entry point of intelligent perception chains. This transformation introduces an entirely new attack surface. From the perspective of attack layers, threats can be classified into three categories: the physical layer, the algorithmic layer, and the data layer. These layers are mutually coupled and together form the core challenges of ISP security research.

**Physical-layer attacks** target the photosensitive physical properties of image sensors. The most representative example is Camera Blinding via laser: an attacker directs a high-powered laser at the camera, saturating or permanently damaging sensor pixels, causing partial or total camera failure. A more covert variant is infrared injection attack — because CMOS sensors are sensitive to the near-infrared (NIR) band while the human eye cannot perceive it, attackers can project invisible infrared patterns to inject phantom images into the camera. When the ISP's IR-cut filter is bypassed or fails, such attacks directly deceive AI systems that rely on camera input.

**Algorithmic-layer attacks** are centered on the technique of adversarial examples. An attacker superimposes imperceptibly small perturbations on an image, causing downstream deep neural networks to produce incorrect outputs while human observers perceive no change in image content. This class of attack poses severe threats to safety-critical applications such as autonomous driving perception, face recognition, and medical image diagnosis.

**Data-layer attacks** (data poisoning) target the training process of ISP models. An attacker injects carefully crafted malicious samples into a training dataset, corrupting the parameter learning of neural network ISPs (e.g., learned denoising, AWB, and tone mapping models) so that they produce erroneous outputs under specific trigger conditions — introducing a "backdoor" vulnerability.

**Privacy leakage** represents a further dimension of security threat. Research has shown that it is possible to extract the inherent noise pattern of a sensor from images captured by a given camera, forming a unique "camera fingerprint." This fingerprint can be used to trace the source device of any image, threatening the anonymity of users.

### 1.2 Adversarial Examples and Their Relationship to the ISP

The concept of adversarial examples was first formally introduced by Szegedy et al. in 2013. The core observation is: for a trained deep neural network $f$, there exists a perturbed version $x + \delta$ that is visually nearly identical to the original input $x$ yet causes the network to output a completely different, incorrect prediction. The generation objective for the perturbation $\delta$ is:

$$\arg\max_{\delta} \mathcal{L}(f(x+\delta), y), \quad \text{s.t.} \quad \|\delta\|_\infty \leq \epsilon$$

where $\mathcal{L}$ is the cross-entropy loss, $y$ is the ground-truth label, and $\epsilon$ is the human perceptibility threshold (typically 1%–4% of the pixel value range, i.e., $\epsilon \in [2, 8]$ in the 0–255 pixel space).

**FGSM** (Fast Gradient Sign Method, Goodfellow et al., 2015) is the simplest single-step attack method, which perturbs the input one step in the sign direction of the loss gradient:

$$\delta = \epsilon \cdot \text{sign}(\nabla_x \mathcal{L}(f(x), y))$$

**PGD** (Projected Gradient Descent, Madry et al., ICLR 2018) is a stronger multi-step iterative attack, regarded as the standard white-box attack benchmark in adversarial robustness research:

$$x^{(t+1)} = \Pi_{x+\mathcal{S}} \left( x^{(t)} + \alpha \cdot \text{sign}(\nabla_x \mathcal{L}(f(x^{(t)}), y)) \right)$$

where $\Pi$ is the projection operator that maps the sample back to the valid perturbation set $\mathcal{S} = \{\delta : \|\delta\|_\infty \leq \epsilon\}$, $\alpha$ is the step size (typically $\alpha = \epsilon / 4$), and the number of iterations $k$ is typically between 10 and 40.

**The ISP's natural attenuation effect on digital-domain adversarial examples** deserves special attention. When adversarial examples are fed directly to neural networks in digital form, carefully crafted pixel-level perturbations are generally highly effective. However, when images pass through ISP processing steps, perturbations are degraded to varying degrees:

- **JPEG compression**: DCT quantization truncates high-frequency perturbation components;
- **Sharpening/USM**: edge enhancement may amplify or restructure local perturbation patterns;
- **Color correction matrix (CCM)**: the linear transform changes the relative amplitude of perturbations across color channels;
- **Gamma correction**: the nonlinear mapping causes uniform pixel perturbations to have inconsistent actual effects across different luminance regions;
- **Noise reduction (NR)**: spatial or frequency-domain filtering directly smooths adversarial perturbations.

These effects constitute a "natural defense" against digital-domain adversarial attacks, though they are not complete. Researchers have consequently developed physical-domain attack techniques specifically designed to survive ISP processing.

### 1.3 Physical-Domain Adversarial Attacks

Physical-domain adversarial attacks must solve a harder problem: the adversarial perturbation must not only be effective in the digital domain but also survive the following complete physical chain:

$$\text{Print/Project} \rightarrow \text{Real illumination} \rightarrow \text{Camera capture} \rightarrow \text{ISP processing} \rightarrow \text{AI inference}$$

Eykholt et al.'s RP2 (Robust Physical Perturbations) attack at CVPR 2018 designed physical stickers attached to the surface of Stop Signs, causing object detection models to misclassify them as speed limit signs in normal driving scenes. This attack needed to remain effective across a variety of lighting angles and capture distances, fully illustrating the challenges of physical-domain attacks.

**EOT (Expectation over Transformations)**, proposed by Athalye et al. at ICML 2018, is the most influential framework for physical-domain adversarial attacks. Its core idea is to incorporate the ISP transform distribution $T$ into the optimization expectation when generating adversarial examples:

$$\delta^* = \arg\max_\delta \; \mathbb{E}_{t \sim T}\left[\mathcal{L}(f(t(x+\delta)), y)\right]$$

where the transform distribution $T$ covers the various random transformations that can occur in a real ISP pipeline, including:
- **Random gamma correction**: $\gamma \sim \mathcal{U}(0.8, 1.2)$, simulating exposure variation;
- **AWB color temperature shift**: random multiplication by a color gain vector $(r_g, g_g, b_g)$, simulating different light sources;
- **JPEG compression**: quality factor $Q \sim \mathcal{U}(50, 95)$;
- **Spatial transforms**: random rotation, scaling, and perspective warping to simulate different capture angles;
- **Sensor noise**: addition of Gaussian or Poisson noise.

By optimizing over the expected gradient from a large number (typically 30 to 100) of randomly transformed samples, EOT-generated adversarial examples exhibit significant robustness to ISP transforms.

**Practical attack scenarios:**
- **Autonomous vehicle object detection spoofing**: adversarial stickers on road signs or vehicles cause YOLO-class detectors to miss-detect;
- **Face recognition access control spoofing**: printed or worn accessories containing adversarial patterns bypass face recognition systems;
- **Medical imaging diagnosis disruption**: adversarial noise superimposed on X-ray or CT images interferes with AI-assisted diagnosis.

### 1.4 Camera Fingerprinting

Every digital camera's image sensor inevitably exhibits small pixel response non-uniformities during manufacture. This property is called **PRNU (Photo Response Non-Uniformity)**. PRNU is intrinsically a spatial noise pattern unique to a given sensor, stable over time, and is widely recognized as the most reliable "camera fingerprint."

Lukas et al. (IEEE TIFS 2006) and Chen et al. (IEEE TIFS 2008) established the theoretical foundations of PRNU-based camera identification. The PRNU pattern $K$ is defined as the multiplicative noise component of the sensor response:

$$I = I_0 \cdot (1 + K) + \Xi$$

where $I_0$ is the ideal uniform response, $K$ is the PRNU pattern, and $\Xi$ is additive noise (shot noise, read noise, etc.).

**Extraction method**: the PRNU fingerprint is extracted from a large set of images (at least 50 recommended) captured by the same camera:

1. For each image $I_i$, use a denoising filter $F$ to estimate the scene content, and compute the noise residual: $W_i = I_i - F(I_i)$;
2. Compute a weighted average of all residuals to cancel scene-correlated noise: $\hat{K} = \frac{\sum_i W_i \cdot I_i}{\sum_i I_i^2}$;
3. Apply zero-mean normalization to the estimated PRNU.

**Privacy threat**: once an attacker has built a PRNU fingerprint database for a given camera, they can extract the PRNU from any image captured by that camera and use Normalized Cross-Correlation (NCC) to determine the image's source, thereby tracing anonymously published images back to a specific device — and thus to the device owner.

**Defense methods (camera anonymization)**: before publishing an image, add specially designed adversarial noise or frequency-domain perturbations to confuse PRNU features and cause fingerprint matching to fail, while keeping the image's visual quality unaffected.

### 1.5 Impact of ISP Parameters on AI Model Robustness

There is a strong coupling between ISP parameter configuration and downstream AI model performance. Guo et al.'s work at ECCV 2022 systematically studied the "ISP Domain Gap" problem: detection models trained on data collected and annotated under specific ISP parameters (e.g., color temperature, contrast, sharpening strength) suffer significant performance degradation under different ISP configurations, with mAP drops of 10%–20% or more.

This problem is especially prominent in multi-camera deployments for autonomous driving, security surveillance, and similar applications, because cameras from different production batches and different ISP vendors produce images with systematic differences in color, sharpness, and noise characteristics.

**ISP-aware adversarial training** is an effective mitigation strategy: during training, randomly sample different ISP parameter configurations for each mini-batch and apply ISP transform simulation to the input images, making the model more robust to ISP parameter variation. This is essentially an extension of data augmentation, targeting the ISP parameter space rather than the conventional geometric transform space.

**RAW-domain adversarial training** offers an alternative: train perception models directly on RAW data, bypassing the domain shift introduced by the ISP. This requires the camera to output RAW data and the model architecture to handle Bayer-format RAW images. The trade-off is higher computational complexity for both training and inference, and the absence of a universal RAW format standard.

### 1.6 Privacy-Preserving Photography Techniques

**Face anonymization** is the most direct application scenario for privacy-preserving photography. Traditional methods (Gaussian blur, pixelated mosaic) can obscure facial features but produce visually jarring results, and in some cases the original identity can still be partially recovered.

**DeepPrivacy2** (Hukkelås et al., WACV 2023) represents the state of the art in GAN-based approaches: detected human face regions in an image are replaced with synthetic faces generated by a conditional GAN. The newly generated faces maintain high consistency with the original scene in lighting, pose, and skin tone, with far better visual naturalness than traditional mosaic methods, while completely erasing the original face identity.

**Differential privacy applied to images**: differential privacy provides a rigorous mathematical definition of privacy protection from a statistical perspective. For image data, this can be achieved by adding calibrated Gaussian noise that satisfies a differential privacy guarantee (satisfying $(\varepsilon, \delta)$-differential privacy) to the image, so that an attacker cannot infer any individual's sensitive information from the published image with high confidence. The trade-off is a fundamental tension between image quality degradation and the privacy budget $\varepsilon$.

---

## §2 Calibration

### 2.1 Adversarial Perturbation Strength Calibration

Selecting the perturbation magnitude $\epsilon$ requires striking a balance between **Attack Success Rate (ASR)** and **perceptual quality**. The table below provides commonly used reference values (L∞ norm, pixel values normalized to $[0,1]$):

| $\epsilon$ value | Pixel range (0–255) | Typical ASR (ResNet-50, ImageNet) | Estimated PSNR loss |
|:--------------:|:-------------------:|:---------------------------------:|:-------------------:|
| 1/255 ≈ 0.004 | ±1 | ~40% (FGSM) | < 0.5 dB |
| 4/255 ≈ 0.016 | ±4 | ~85% (PGD-20) | ~1–2 dB |
| 8/255 ≈ 0.031 | ±8 | ~98% (PGD-40) | ~3–4 dB |
| 16/255 ≈ 0.063 | ±16 | >99% | ~6 dB, visible noise |

In practice, end-to-end ASR testing should be performed under the specific processing pipeline of the target ISP system, because ISP denoising and compression raise the effective $\epsilon$ threshold — a larger $\epsilon$ is needed to maintain the attack after ISP processing. Physical-domain attacks generally require $\epsilon \geq 8/255$ combined with the EOT method for robustness.

### 2.2 ISP Robustness Test Baseline

When evaluating AI system robustness to ISP variation, it is recommended to use the following standardized ISP operation test set:

| ISP operation | Test range | Evaluation metric |
|:------------:|:----------:|:-----------------:|
| Brightness/exposure adjustment | ±2 EV (i.e., ×0.25 to ×4.0) | Detection mAP / Classification Top-1 Acc |
| Color temperature variation | 2500K to 7500K (step 500K) | Same as above |
| JPEG compression quality | Q = 50, 60, 70, 80, 90, 95 | Same as above + SSIM |
| Sharpening strength | USM Amount 0 to 2.0 | Same as above |
| Denoising strength | Light / Medium / Heavy | Same as above + detail retention rate |

For ISP survival rate testing of adversarial examples, the following should be recorded: (1) pure digital-domain ASR; (2) ASR after each individual ISP operation; (3) ASR after the full ISP pipeline (Gamma + CCM + NR + JPEG). Comparing all three quantifies the degree to which the ISP attenuates the attack.

### 2.3 PRNU Calibration Requirements

The quality of PRNU fingerprint extraction is influenced by the following factors, which should be carefully controlled during calibration:

- **Number of flat-field images**: $N \geq 50$ is recommended; insufficient image count causes scene texture to contaminate the PRNU estimate;
- **Capture conditions**: shoot under a uniform light source (uniform gray card or white wall), avoiding strong-texture scenes;
- **Exposure settings**: use fixed ISO (ISO 100–400 recommended) and fixed shutter speed, avoiding exposure variation that introduces response nonlinearity;
- **ISP state**: disable noise reduction (or use a uniform NR strength), as denoising suppresses the PRNU signal.

For the IMX477 sensor (RPi4B), it is recommended to extract PRNU in RAW format, because the PRNU signal in RGB images is disturbed by ISP denoising and color transforms.

---

## §3 Tuning

### 3.1 Adversarial Training Hyperparameters

**PGD adversarial training** is currently the most mainstream method for improving robustness (Madry et al., ICLR 2018). Key hyperparameters are as follows:

| Parameter | Meaning | Recommended value |
|:---------:|:-------:|:-----------------:|
| $\epsilon$ | L∞ perturbation budget | 8/255 (image classification), 4/255 (object detection) |
| $\alpha$ | PGD step size | $\epsilon / 4$ (standard setting) |
| $k$ | PGD iteration count | 7–10 steps during training, 20–40 steps during evaluation |
| Training epochs | Number of adversarial training rounds | Typically 2–3× the original training schedule |

Note: $k=1$ degrades PGD to FGSM — higher training efficiency but weaker robustness; $k \geq 10$ provides stronger adversarial training at the cost of increasing training time per batch by a factor of $k$. On resource-constrained embedded platforms (e.g., RPi4B) running inference, adversarial training does not need to be run on-device; a pre-trained robust model from PC training can be loaded directly.

### 3.2 EOT Physical Attack Hyperparameters

| Parameter | Meaning | Recommended value |
|:---------:|:-------:|:-----------------:|
| EOT sample count $n$ | Number of transform samples per gradient computation | 30–100 |
| Optimization iterations | Total gradient update steps | 200–1000 |
| Learning rate | Adam optimizer learning rate | 0.01 |
| Transform strength | Gamma offset range, color temperature offset range, etc. | Refer to the standard ISP operation set in §2.2 |

A larger EOT sample count $n$ yields better expected robustness of the generated adversarial examples to ISP transforms, but computational cost scales linearly with $n$. In laboratory settings, $n=50$ is typically used as a balance point.

### 3.3 ISP-Aware Data Augmentation Tuning

In ISP-aware training, the strength of ISP simulation augmentation must be carefully calibrated; excessively strong ISP perturbation can cause training instability. Recommended augmentation probabilities and intensity ranges:

| Augmentation type | Application probability | Intensity range |
|:-----------------:|:----------------------:|:---------------:|
| Gamma correction | 0.5 | $\gamma \in [0.7, 1.4]$ |
| Brightness adjustment | 0.5 | Multiplicative factor $[0.5, 2.0]$ |
| Color gain | 0.3 | R/B channel gain $[0.8, 1.2]$ |
| JPEG compression | 0.5 | Quality factor $Q \in [60, 95]$ |
| Gaussian blur | 0.2 | $\sigma \in [0.5, 1.5]$ |

---

## §4 Artifacts

### 4.1 Adversarial Noise Visibility Artifacts

When the adversarial perturbation $\epsilon$ is too large, the human eye can perceive colored noise spots or texture anomalies in the image — the most direct artifact of adversarial examples. Manifestations include:

- **Colored speckle**: irregular colored pixels appearing in flat regions (sky, walls);
- **Edge halos**: abnormal brightness variations near strong edges, resembling over-sharpening artifacts from excessive USM;
- **Periodic texture**: when optimization has not fully converged, low-frequency checkerboard or stripe artifacts may appear.

In practice, at $\epsilon > 8/255$ (more than ±8 in the 0–255 pixel range), trained observers will notice some visibility; at $\epsilon > 16/255$, the noise is clearly perceptible to the naked eye.

### 4.2 Degraded Cross-ISP Transferability of Adversarial Examples

Adversarial examples generated under a specific ISP parameter configuration (e.g., color temperature 5500K, Gamma 2.2, JPEG Q80) suffer significant drops in attack success rate when the target system uses different ISP parameters. This phenomenon is called the **ISP transferability gap** and is one of the core challenges facing physical-domain attacks.

In practice: adversarial examples tuned against one smartphone's ISP may completely fail on another smartphone's ISP, because the two differ fundamentally in their color curves, sharpening algorithms, and JPEG encoders. The EOT method partially mitigates this by taking expectations over multiple ISP configurations, but cannot fully eliminate it — and proprietary algorithmic parameters of different ISP vendors cannot be accurately modeled.

### 4.3 PRNU Extraction Errors and Contamination

Typical error sources in the PRNU extraction process include:

- **Scene texture contamination**: if flat-field images contain strong textures (fine grids, wood grain, etc.), the denoising residual mixes in scene information and contaminates the PRNU estimate. Remedy: strictly use a uniform light source and increase the number of flat-field images;
- **Motion blur contamination**: slight camera shake during handheld capture introduces directional streaks into the PRNU estimate;
- **Compression artifact interference**: DCT block effects from high-compression-ratio JPEG alias with the PRNU signal; RAW format or high-quality JPEG (Q ≥ 90) is recommended for PRNU extraction;
- **Sensor temperature variation**: extended exposure or high ISO causes the sensor temperature to rise, increasing the dark current noise component and degrading PRNU stability.

### 4.4 Adversarial Training Accuracy Cost

Adversarial training is an effective method for improving model robustness but carries an inherent **accuracy–robustness trade-off**. Standard adversarial training typically results in:

- A 2%–5% drop in clean-sample classification accuracy (ImageNet classification task);
- A slight decrease in inference speed due to deeper feature representations;
- A 2–10× increase in training time (depending on the number of PGD steps).

This trade-off is a fundamental theoretical limitation (Tsipras et al., ICLR 2019) and not something that can be fully eliminated through engineering. Practical deployment decisions must balance the security requirements and accuracy tolerance of the target use case.

---

## §5 Evaluation

### 5.1 Attack Success Rate (ASR)

Attack Success Rate is the core metric for measuring adversarial attack effectiveness:

$$\text{ASR} = \frac{\text{Number of successful attacks}}{\text{Total attack samples}} \times 100\%$$

For untargeted attacks, "success" means the model outputs any class different from the ground-truth label; for targeted attacks, "success" means the model outputs the specific target class designated by the attacker (harder, typically lower ASR).

### 5.2 ASR Before and After ISP Processing

Quantifying the ISP's attenuation of adversarial examples is critical for evaluating the feasibility of adversarial attacks in real deployment scenarios. Standard evaluation procedure:

1. Generate adversarial examples in the digital domain and record the baseline $\text{ASR}_\text{digital}$;
2. Apply ISP transforms to the adversarial examples (using the test set from §2.2) and record $\text{ASR}_\text{ISP}^{(i)}$ for each ISP operation;
3. Apply the full ISP pipeline and record $\text{ASR}_\text{full ISP}$;
4. Compute the **ISP reduction rate**: $\text{Reduction} = (\text{ASR}_\text{digital} - \text{ASR}_\text{full ISP}) / \text{ASR}_\text{digital}$.

In general, digital-domain PGD attacks see a 30%–60% reduction in ASR after passing through a full ISP pipeline (including JPEG compression). However, physical-domain adversarial examples specifically generated with the EOT method typically show less than 20% ISP reduction.

### 5.3 PRNU Camera Identification Evaluation

The accuracy of camera fingerprint identification is quantified via **Normalized Cross-Correlation (NCC)**:

$$\text{NCC}(K_1, K_2) = \frac{\sum_{i,j} K_1(i,j) \cdot K_2(i,j)}{\sqrt{\sum_{i,j} K_1^2(i,j)} \cdot \sqrt{\sum_{i,j} K_2^2(i,j)}}$$

Decision rules:
- $\text{NCC} > 0.8$: images are judged to originate from the same camera (same source);
- $\text{NCC} < 0.3$: images are judged to originate from different cameras (different source);
- $0.3 \leq \text{NCC} \leq 0.8$: ambiguous region — additional images are needed to confirm.

Standard evaluation datasets typically include 50+ cameras with 100 images per camera. The area under the ROC curve (AUC) is computed as a comprehensive performance metric; a high-quality PRNU identification system can achieve AUC above 0.99.

### 5.4 Comprehensive Adversarial Robustness Evaluation

When conducting a comprehensive robustness evaluation, the following metrics should be reported simultaneously:

| Metric | Meaning | Evaluation tool |
|:------:|:-------:|:---------------:|
| Clean Accuracy | Accuracy on clean samples | Standard evaluation set |
| FGSM Accuracy | Accuracy under FGSM attack | $\epsilon=8/255$ |
| PGD-20 Accuracy | Accuracy under 20-step PGD | $\epsilon=8/255, \alpha=2/255$ |
| AutoAttack Accuracy | Accuracy under strongest adaptive attack | AutoAttack library (Croce & Hein, 2020) |
| ISP-PGD Accuracy | PGD robustness accuracy after ISP transforms | Standard ISP operation set from §2.2 |

RobustBench (Croce et al., 2021) is the most authoritative adversarial robustness benchmarking platform, where rankings of different architectures and training methods under standard adversarial evaluation can be queried.

---

## §6 Code

The following code examples are based on Python 3.x and depend on `numpy`, `opencv-python`, and `torch`. They can be run on a PC; key functions can also be executed on an RPi4B (CPU mode).

```python
"""
ch12_privacy_photography_demo.py

ISP Security and Adversarial Attack Demo Code
Dependencies: numpy, opencv-python, torch, torchvision
Hardware: PC (GPU/CPU) or RPi4B (CPU only, torch inference)
"""

import numpy as np
import cv2
import io
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image


# ─────────────────────────────────────────────────────────────
# §6.1 FGSM Attack
# ─────────────────────────────────────────────────────────────

def fgsm_attack(model: nn.Module,
                image: torch.Tensor,
                label: torch.Tensor,
                epsilon: float = 8/255) -> torch.Tensor:
    """
    Fast Gradient Sign Method (Goodfellow et al., 2015).

    Args:
        model:   PyTorch classification model with loaded weights, eval mode
        image:   Input image tensor, shape [1, C, H, W], values in [0, 1]
        label:   Ground-truth label tensor, shape [1], integer class index
        epsilon: L-inf perturbation budget, default 8/255

    Returns:
        adv_image: Adversarial example tensor, same shape as image, values in [0, 1]
    """
    image = image.clone().detach().requires_grad_(True)

    output = model(image)
    loss = F.cross_entropy(output, label)
    model.zero_grad()
    loss.backward()

    # Perturb in the sign direction of the gradient
    perturbation = epsilon * image.grad.data.sign()
    adv_image = image + perturbation

    # Clip to valid value range
    adv_image = torch.clamp(adv_image, 0.0, 1.0)
    return adv_image.detach()


# ─────────────────────────────────────────────────────────────
# §6.2 PGD Attack
# ─────────────────────────────────────────────────────────────

def pgd_attack(model: nn.Module,
               image: torch.Tensor,
               label: torch.Tensor,
               epsilon: float = 8/255,
               alpha: float = 2/255,
               num_steps: int = 20) -> torch.Tensor:
    """
    Projected Gradient Descent attack (Madry et al., ICLR 2018).

    Args:
        model:     PyTorch classification model, eval mode
        image:     Input image tensor [1, C, H, W], values in [0, 1]
        label:     Ground-truth label tensor [1]
        epsilon:   L-inf perturbation budget
        alpha:     Step size per iteration, recommended epsilon/4
        num_steps: Number of iterations; k=1 is equivalent to FGSM, recommended 20-40

    Returns:
        adv_image: Adversarial example, values in [0, 1]
    """
    # Random initialization of perturbation (uniform sampling within epsilon ball)
    delta = torch.zeros_like(image).uniform_(-epsilon, epsilon)
    delta = torch.clamp(image + delta, 0.0, 1.0) - image
    delta.requires_grad_(True)

    for _ in range(num_steps):
        adv_image = image + delta
        output = model(adv_image)
        loss = F.cross_entropy(output, label)
        model.zero_grad()
        loss.backward()

        # Gradient sign step
        with torch.no_grad():
            delta.data = delta.data + alpha * delta.grad.data.sign()
            # Project back to L-inf ball
            delta.data = torch.clamp(delta.data, -epsilon, epsilon)
            # Ensure adv_image stays in valid value range
            delta.data = torch.clamp(image + delta.data, 0.0, 1.0) - image
        delta.grad.zero_()

    return (image + delta).detach()


# ─────────────────────────────────────────────────────────────
# §6.3 Camera PRNU Fingerprint Extraction
# ─────────────────────────────────────────────────────────────

def extract_prnu(flat_images_list: list) -> np.ndarray:
    """
    Extract camera PRNU fingerprint from multiple flat-field images
    (Lukas et al., IEEE TIFS 2006).

    Args:
        flat_images_list: List of flat-field images, each as np.ndarray [H, W] or
                          [H, W, C], grayscale or color, float32, values in [0, 1].
                          At least N >= 50 images recommended, shot against a
                          uniform white wall or gray card.

    Returns:
        prnu: Estimated PRNU fingerprint, same size as input images, zero-mean normalized.
    """
    assert len(flat_images_list) >= 10, \
        "At least 10 images recommended; 50+ images give better quality"

    # Convert color images to grayscale if needed
    gray_images = []
    for img in flat_images_list:
        if img.ndim == 3:
            g = cv2.cvtColor((img * 255).astype(np.uint8),
                             cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        else:
            g = img.astype(np.float32)
        gray_images.append(g)

    # Use a denoising filter to estimate scene content; compute noise residual.
    # A simple Gaussian filter is used here as an approximation
    # (production PRNU extraction should use the Mihcak wavelet denoiser).
    numerator = np.zeros_like(gray_images[0], dtype=np.float64)
    denominator = np.zeros_like(gray_images[0], dtype=np.float64)

    for img in gray_images:
        # Gaussian filter approximation (wavelet denoiser recommended in practice)
        smoothed = cv2.GaussianBlur(img, (5, 5), sigmaX=1.0)
        noise_residual = img - smoothed  # W_i = I_i - F(I_i)

        # Weighted accumulation: numerator sum(W_i * I_i), denominator sum(I_i^2)
        numerator += noise_residual * img
        denominator += img ** 2

    # Avoid division by zero
    denominator = np.maximum(denominator, 1e-10)
    prnu = numerator / denominator

    # Zero-mean normalization
    prnu -= prnu.mean()
    std = prnu.std()
    if std > 1e-10:
        prnu /= std

    return prnu.astype(np.float32)


# ─────────────────────────────────────────────────────────────
# §6.4 Normalized Cross-Correlation (NCC) Camera Identification
# ─────────────────────────────────────────────────────────────

def compute_ncc(prnu1: np.ndarray, prnu2: np.ndarray) -> float:
    """
    Compute the Normalized Cross-Correlation (NCC) between two PRNU fingerprints.

    Args:
        prnu1: First PRNU fingerprint, np.ndarray, zero-mean normalized
        prnu2: Second PRNU fingerprint, np.ndarray, zero-mean normalized,
               must have the same shape as prnu1

    Returns:
        ncc: Normalized cross-correlation coefficient, range [-1, 1]
             > 0.8: highly likely to be the same camera
             < 0.3: likely to be different cameras

    Decision rules (Chen et al., IEEE TIFS 2008):
        Same source     : NCC > 0.8
        Different source: NCC < 0.3
    """
    assert prnu1.shape == prnu2.shape, "Both PRNU fingerprints must have the same shape"

    p1 = prnu1.flatten().astype(np.float64)
    p2 = prnu2.flatten().astype(np.float64)

    norm1 = np.linalg.norm(p1)
    norm2 = np.linalg.norm(p2)

    if norm1 < 1e-10 or norm2 < 1e-10:
        return 0.0

    ncc = np.dot(p1, p2) / (norm1 * norm2)
    return float(ncc)


# ─────────────────────────────────────────────────────────────
# §6.5 ISP Transform Simulation (EOT-Style Data Augmentation)
# ─────────────────────────────────────────────────────────────

def simulate_isp_transform(image: np.ndarray,
                           seed: int = None) -> np.ndarray:
    """
    Randomly simulate ISP processing transforms for EOT-style physical adversarial
    attacks or robustness-augmentation training.

    Includes: random gamma correction, color gain (simulating AWB shift),
              Gaussian blur (simulating NR smoothing), JPEG compression
              (simulating encoder quantization loss).

    Args:
        image: Input BGR image, np.ndarray [H, W, 3], uint8, values in [0, 255]
        seed:  Random seed (optional), for reproducibility

    Returns:
        transformed: ISP-transformed image, same size, uint8
    """
    if seed is not None:
        rng = np.random.RandomState(seed)
    else:
        rng = np.random.RandomState()

    img = image.astype(np.float32) / 255.0

    # 1. Random gamma correction (simulating exposure / tone curve variation)
    gamma = rng.uniform(0.7, 1.4)
    img = np.power(np.clip(img, 1e-6, 1.0), gamma)

    # 2. Random color gain (simulating AWB color temperature shift)
    # Independent gain on R and B channels; G channel held as reference
    r_gain = rng.uniform(0.85, 1.15)
    b_gain = rng.uniform(0.85, 1.15)
    img[:, :, 2] *= r_gain  # OpenCV BGR: channel 2 = R
    img[:, :, 0] *= b_gain  # channel 0 = B
    img = np.clip(img, 0.0, 1.0)

    # 3. Random brightness adjustment
    brightness = rng.uniform(0.7, 1.3)
    img = np.clip(img * brightness, 0.0, 1.0)

    # 4. Light Gaussian blur (simulating NR smoothing)
    if rng.rand() < 0.5:
        sigma = rng.uniform(0.3, 1.0)
        ksize = 3  # Fixed 3×3 kernel to avoid excessive blurring
        img = cv2.GaussianBlur(img, (ksize, ksize), sigmaX=sigma)

    # 5. JPEG compression (simulating encoder quantization loss)
    quality = int(rng.uniform(60, 95))
    img_uint8 = (img * 255).clip(0, 255).astype(np.uint8)
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    _, enc = cv2.imencode('.jpg', img_uint8, encode_param)
    img_uint8 = cv2.imdecode(enc, cv2.IMREAD_COLOR)

    return img_uint8


# ─────────────────────────────────────────────────────────────
# §6.6 Demo: Full Attack Evaluation Pipeline
# ─────────────────────────────────────────────────────────────

def evaluate_attack_under_isp(model: nn.Module,
                               image_tensor: torch.Tensor,
                               label: torch.Tensor,
                               epsilon: float = 8/255,
                               n_isp_trials: int = 20) -> dict:
    """
    Evaluate the survival rate of PGD adversarial examples under random ISP transforms.

    Args:
        model:         Classification model, eval mode
        image_tensor:  Original image tensor [1, C, H, W], values in [0, 1]
        label:         Ground-truth label
        epsilon:       L-inf perturbation budget
        n_isp_trials:  Number of random ISP transform samples

    Returns:
        results dict:
            'digital_asr':   Attack success rate in the pure digital domain (0 or 1,
                             single sample)
            'isp_asr':       Average attack success rate after ISP transforms
            'isp_reduction': ISP reduction rate of the attack
    """
    model.eval()

    # Generate PGD adversarial example
    adv = pgd_attack(model, image_tensor, label,
                     epsilon=epsilon, alpha=epsilon/4, num_steps=20)

    # Digital-domain ASR
    with torch.no_grad():
        pred_digital = model(adv).argmax(dim=1)
    digital_success = int(pred_digital.item() != label.item())

    # ASR after ISP transforms
    adv_np = (adv.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)

    isp_successes = 0
    for trial in range(n_isp_trials):
        # Apply random ISP transform
        adv_isp = simulate_isp_transform(adv_np, seed=trial)

        # Convert back to tensor
        adv_isp_t = torch.from_numpy(adv_isp).float() / 255.0
        adv_isp_t = adv_isp_t.permute(2, 0, 1).unsqueeze(0)

        with torch.no_grad():
            pred_isp = model(adv_isp_t).argmax(dim=1)
        if pred_isp.item() != label.item():
            isp_successes += 1

    isp_asr = isp_successes / n_isp_trials
    isp_reduction = (digital_success - isp_asr) / (digital_success + 1e-10)

    return {
        'digital_asr': digital_success,
        'isp_asr': isp_asr,
        'isp_reduction': max(0.0, isp_reduction)
    }


# ─────────────────────────────────────────────────────────────
# §6.7 RPi4B + IMX477 Flat-Field Image Acquisition Notes (picamera2)
# ─────────────────────────────────────────────────────────────

PICAMERA2_PRNU_NOTES = """
Steps for acquiring PRNU calibration flat-field images on RPi4B + IMX477 (HQ Camera):

1. Install dependencies:
   sudo apt install python3-picamera2

2. Hardware preparation:
   - Point the camera at a uniform diffuse light source (white LED light box or
     white paper under uniform natural light)
   - Ensure the scene has no strong textures; uniformity requirement: brightness
     difference between image center and edges < 10%
   - Mount the camera on a tripod to avoid vibration-induced displacement

3. Acquisition script sketch (picamera2 API):

    from picamera2 import Picamera2
    import numpy as np, time

    cam = Picamera2()
    # Configure RAW format (recommended for PRNU extraction to avoid ISP processing)
    config = cam.create_still_configuration(
        raw={"format": "SRGGB12", "size": (4056, 3040)},
        main={"format": "BGR888", "size": (4056, 3040)}
    )
    cam.configure(config)

    # Fix exposure parameters (disable AE, fix ISO and shutter speed)
    cam.set_controls({
        "AeEnable": False,
        "ExposureTime": 10000,   # 10 ms; adjust based on light source brightness
        "AnalogueGain": 1.0,     # ISO 100 equivalent
        "AwbEnable": False,
        "ColourGains": (1.0, 1.0)  # Disable AWB, fix color gains
    })
    cam.start()
    time.sleep(2)  # Wait for exposure to stabilize

    flat_images = []
    for i in range(60):  # Capture 60 images, exceeding the recommended minimum of 50
        arr = cam.capture_array("main").astype(np.float32) / 255.0
        flat_images.append(arr)
        time.sleep(0.5)
        print(f"Capture progress: {i+1}/60")

    cam.stop()

    # Extract PRNU
    prnu = extract_prnu(flat_images)
    np.save("imx477_prnu.npy", prnu)
    print(f"PRNU extraction complete, shape: {prnu.shape}, std: {prnu.std():.4f}")

4. Notes:
   - Begin acquisition at least 5 minutes after camera startup to allow sensor
     temperature to stabilize
   - Keep light source brightness constant during acquisition; avoid power fluctuations
   - RAW-format PRNU is cleaner than RGB PRNU because it has not been processed by
     ISP denoising
   - Re-calibration is recommended on each occasion (sensor characteristics change
     slightly over usage time)
"""
```

---

## References

1. **Szegedy, C., Zaremba, W., Sutskever, I., et al.** (2013). Intriguing properties of neural networks. *arXiv preprint arXiv:1312.6199*.

2. **Goodfellow, I. J., Shlens, J., & Szegedy, C.** (2015). Explaining and harnessing adversarial examples. *ICLR 2015*. arXiv:1412.6572.

3. **Madry, A., Makelov, A., Schmidt, L., Tsipras, D., & Vladu, A.** (2018). Towards deep learning models resistant to adversarial attacks. *ICLR 2018*. arXiv:1706.06083.

4. **Eykholt, K., Evtimov, I., Fernandes, E., et al.** (2018). Robust physical-world attacks on deep learning visual classification. *CVPR 2018*. arXiv:1707.08945.

5. **Athalye, A., Engstrom, L., Ilyas, A., & Kwok, K.** (2018). Synthesizing robust adversarial examples. *ICML 2018*. arXiv:1707.07397.

6. **Lukas, J., Fridrich, J., & Goljan, M.** (2006). Digital camera identification from sensor pattern noise. *IEEE Transactions on Information Forensics and Security*, 1(2), 205–214.

7. **Chen, M., Fridrich, J., Goljan, M., & Lukas, J.** (2008). Determining image origin and integrity using sensor noise. *IEEE Transactions on Information Forensics and Security*, 3(1), 74–90.

8. **Hukkelås, H., Mester, R., & Lindseth, F.** (2023). DeepPrivacy2: Towards realistic full-body anonymization. *WACV 2023*. arXiv:2211.09454.

9. **Tsipras, D., Santurkar, S., Engstrom, L., Turner, A., & Madry, A.** (2019). Robustness may be at odds with accuracy. *ICLR 2019*. arXiv:1805.12152.

10. **Croce, F., & Hein, M.** (2020). Reliable evaluation of adversarial robustness with an ensemble of diverse parameter-free attacks. *ICML 2020*. arXiv:2003.01690.

---

*Corresponding code file for this chapter: `ch12_privacy_photography_demo.py`*
*Reference hardware platform: Raspberry Pi 4B + IMX477 (HQ Camera Module)*
