# Part 3, Chapter 17: Self-Supervised and Unsupervised ISP Learning

> **Scope:** This chapter covers ISP learning methods that do not require paired data, from Noise2Noise to CycleISP, addressing the core problem of insufficient real-world training data.
> **Prerequisites:** Volume 3, Chapter 2 (End-to-End Image Restoration), Volume 3, Chapter 1 (DL ISP Overview)
> **Target Readers:** Deep learning researchers

---

## §1 Theoretical Foundations

### 1.1 The Root Cause of Paired Data Scarcity

A fundamental challenge in deep learning-based ISP is the **cost of acquiring paired training data**. An ideal training dataset should contain paired noisy/low-quality RAW images and their corresponding clean/high-quality ground truth (GT). However, in practice:

- **Physical paired capture:** Requires a fixed tripod, shooting static scenes separately at high ISO (noisy) and low ISO (clean). The process is cumbersome and cannot capture dynamic scenes;
- **Synthetic noise:** Simulating camera noise with AWGN (additive white Gaussian noise, 加性高斯白噪声) or Poisson noise produces a significant distribution gap from real camera noise, causing training-test domain mismatch (domain gap);
- **Annotation cost:** For subjective ISP tasks such as color enhancement and tone mapping, professional-grade GT annotation (e.g., MIT-Adobe FiveK's 5-expert retouching) is extremely expensive and difficult to scale.

The goal of self-supervised learning (Self-Supervised Learning) and unsupervised learning (Unsupervised Learning) methods is to train ISP models **without paired GT**, using only collections of noisy/unprocessed single-view or multi-view images for learning.

### 1.2 Theoretical Foundations of Noise2Noise

Noise2Noise (N2N), proposed by Lehtinen et al. (ICML 2018), is the foundational work in self-supervised image denoising. Its core insight comes from the following statistical observation:

Let the clean image be $\mathbf{x}$, and two independent noise realizations be $\tilde{\mathbf{y}}_1 = \mathbf{x} + \mathbf{n}_1$ and $\tilde{\mathbf{y}}_2 = \mathbf{x} + \mathbf{n}_2$, where noise $\mathbf{n}_1, \mathbf{n}_2$ are i.i.d. with zero mean: $\mathbb{E}[\mathbf{n}] = 0$.

For L2 loss, training network $f_\theta$ using $\tilde{\mathbf{y}}_2$ as the supervision signal (rather than $\mathbf{x}$):

$$
\arg\min_\theta \mathbb{E}\left[\|f_\theta(\tilde{\mathbf{y}}_1) - \tilde{\mathbf{y}}_2\|^2\right]
$$

Since $\mathbb{E}[\tilde{\mathbf{y}}_2|\mathbf{x}] = \mathbf{x}$, the optimal solution of this expectation is equivalent to:

$$
\arg\min_\theta \mathbb{E}\left[\|f_\theta(\tilde{\mathbf{y}}_1) - \mathbf{x}\|^2\right]
$$

That is, by training with noisy image pairs, the network equivalently learns the denoising mapping to the clean image $\mathbf{x}$. **Key condition:** The two noisy images must be conditionally independent (given $\mathbf{x}$) with zero-mean noise. N2N reduces the gap between self-supervised denoising PSNR and supervised methods (noisy-clean pairs) to approximately 0.1 dB.

### 1.3 Noise2Self's Self-Consistency Framework

Noise2Self (N2S), proposed by Batson & Royer (ICML 2019), further eliminates N2N's requirement for "two noisy images of the same scene," enabling training from a **single noisy image**.

Its core concept is **J-invariance (J-不变性):** A function $f$ is J-invariant if, for any pixel subset $J$, $f(\mathbf{y})_J$ depends only on $\mathbf{y}_{J^c}$ (the complement).

The self-supervised loss is:
$$
\mathcal{L}(f) = \mathbb{E}\left[\|f_J(\mathbf{y}) - \mathbf{y}_J\|^2\right]
$$

where $f_J$ is the predicted output at masked pixel set $J$ (the prediction of location $J$ does not use the input at that location). Noise2Self proves that minimizing this loss is equivalent to denoising, provided noise is conditionally independent across pixels.

### 1.4 Blind-Spot Networks (BSN, 盲点网络)

To efficiently implement J-invariance, Krull et al. (CVPR 2019) proposed Noise2Void (N2V), implementing a "blind spot" by modifying the convolutional receptive field: the center pixel is excluded from the receptive field, so the network can only use surrounding pixel information when predicting the center pixel:

$$
f_\theta(\mathbf{y})_i = g_\theta\!\left(\{y_j : j \neq i, j \in \mathcal{N}(i)\}\right)
$$

In practice, this is implemented via rotated/masked convolutions (masked convolution) or receptive field rearrangement. Training loss: $\|\hat{y}_i - y_i\|^2$ (using the real noisy pixel value as supervision; since the network cannot "see" that pixel during prediction, it is forced to learn denoising).

---

## §2 Algorithm Methods

### 2.1 Practical Implementation of Noise2Noise

N2N requires two independent noisy images of each scene. Practical acquisition strategies:

**Burst Pair:** Rapidly capture two frames of the same scene back-to-back; noise in the two frames is independent. The scene must be static (or motion regions must be aligned/masked).

**Temporal Pairs from Raw Bayer:** Use adjacent frames from a RAW video stream; noise is independent in the temporal domain. Naturally available in mobile video ISP scenarios.

**Half-Image Pairs:** Use odd rows and even rows of a single image as two independent noisy images (suitable for line-scan CCD sensors where odd/even row read noise is independent).

### 2.2 RAW Domain Extension of Noise2Noise

When applying N2N to camera RAW images, note the following:

**Zero-Mean Verification for Camera Noise Models:** Real camera noise includes Poisson noise (signal-dependent) and Gaussian read noise, both with zero mean, satisfying N2N's theoretical assumptions.

**Training in Bayer Format:** Train N2N directly in the Bayer domain (4-channel RGGB), avoiding the spatial noise correlation introduced by demosaicing, which would violate the pixel independence assumption.

**Noise Level Estimation:** If a noise level map is provided as an additional input during N2N training, generalization is significantly improved (PSNR improvement of 0.3–0.5 dB on unseen ISO values).

### 2.3 Unsupervised Application of CycleISP

The cycle consistency framework of CycleISP (Zamir et al., CVPR 2020), introduced in Volume 3, Chapter 17, can also be trained **without paired RAW-sRGB data**:

- Given a collection of RAW images $\mathcal{X}$ and a collection of sRGB images $\mathcal{Y}$ (without paired correspondence, e.g., sRGB images crawled from the web);
- Use cycle consistency loss to constrain $G(F(\mathbf{x})) \approx \mathbf{x}$ and $F(G(\mathbf{y})) \approx \mathbf{y}$;
- Simultaneously use discriminators to ensure $F(\mathbf{x})$ looks like real sRGB and $G(\mathbf{y})$ looks like real RAW.

This enables CycleISP to learn a camera's color style without labeled data, suitable for customized camera ISP color grading.

### 2.4 Zero-Shot Noise2Noise

Mansour & Heckel (ICLR 2023) proposed Zero-Shot Noise2Noise (ZS-N2N), extending the N2N idea to zero-shot single-image scenarios: without relying on any training dataset, performing test-time optimization (test-time optimization) exclusively on the target noisy image:

**Core idea:** Randomly downsample a single noisy image into two low-resolution noisy images (a sub-sampled pair), and use one to predict the other:

$$
\mathcal{L}_{\text{ZS-N2N}} = \|f_\theta(\mathbf{y}_1^{\downarrow}) - \mathbf{y}_2^{\downarrow}\|^2
$$

Downsampling breaks the spatial correlation of noise, making the noise in the two sub-images approximately independent, satisfying the N2N assumption. ZS-N2N requires no training set, has natural robustness to out-of-distribution noise types (e.g., structured noise, non-Gaussian noise), achieves approximately 0.5 dB higher PSNR than traditional BM3D, and is only approximately 0.8 dB lower than supervised methods.

### 2.5 Unsupervised ISP via Disentangled Learning

Disentangled Learning (解缠学习) encodes the content (scene information independent of the sensor) and style (the processing style of the camera ISP) of an image separately:

$$
\mathbf{z}_c = E_c(\mathbf{x}), \quad \mathbf{z}_s = E_s(\mathbf{x}), \quad \hat{\mathbf{x}} = G(\mathbf{z}_c, \mathbf{z}_s)
$$

By constraining content codes $\mathbf{z}_c$ to be the same for images of the same scene from different cameras, and style codes $\mathbf{z}_s$ to be the same for the same camera across different scenes, camera ISP style transfer can be achieved without paired data: rendering RAW images from camera A using the ISP style of camera B.

This approach has practical value in computational photography style customization (e.g., "making a Xiaomi phone produce iPhone-style photos").

### 2.6 Contrastive Learning Applied to ISP Quality Assessment

Self-supervised contrastive learning (Contrastive Learning, 对比学习) can be used for unsupervised image quality assessment (Blind IQA):

**Positive pairs:** Different augmented versions of the same image (crops, color jitter, without quality degradation);
**Negative pairs:** Different images, or different degraded versions of the same image (noise contamination, compression).

The feature encoder trained this way learns representations correlated with image quality. Performance on unlabeled evaluation datasets approaches supervised methods (a complementary path to the Blind IQA methods in Volume 4, Chapter 5).

---

## §3 Tuning Guide

### 3.1 Key Noise2Noise Hyperparameters

| Parameter | Recommended Setting | Notes |
|-----------|---------------------|-------|
| Paired frame time interval | <50ms (burst capture) | Too long: scene motion breaks independence assumption |
| Noise mean verification | Compute $\mathbb{E}[y_1 - y_2]$ on dataset | Should be close to zero; otherwise systematic bias exists (e.g., fixed pattern noise) |
| Motion alignment | Optical flow alignment (PWC-Net level) | Mandatory for dynamic scenes; otherwise denoising fails in motion regions |
| Loss function | L1 or L2 both work | L1 is more robust to outliers; L2 is cleaner theoretically |
| Network architecture | Same as supervised (UNet) | N2N's constraints come from data acquisition; the network itself needs no special design |

### 3.2 Blind-Spot Network (N2V) Tuning

| Parameter | Recommended Setting | Notes |
|-----------|---------------------|-------|
| Blind spot implementation | Masked convolution or pixel shuffle | Masked convolution is simpler but less efficient; pixel shuffle is faster |
| Mask ratio | 1.5–2% (N2V) or higher (50%, for Noise2Void-2D) | Too high reduces context information; too low produces sparse training signal |
| Activation replacement strategy | Uniform sampling within receptive field | Replace with a random neighbor pixel value to prevent the network from learning identity mapping |
| Training steps | 200 steps per image for independent optimization (ZS-N2N) | Or 50 epochs on dataset (N2V) |

### 3.3 CycleISP Unsupervised Tuning

- **Adversarial loss weight:** Start from 0.001 and gradually increase to 0.01, avoiding color collapse in early training;
- **Content loss (cycle consistency) weight:** Typically set to 10, much higher than adversarial loss, to ensure reasonable bidirectional mapping;
- **Dataset balance:** Recommended 1:1 ratio between RAW image collection and sRGB image collection, avoiding distributional imbalance from one side being too large;
- **Receptive field alignment:** Generator receptive field should cover sufficient context (≥64 pixels), otherwise local color correction is inconsistent.

---

## §4 Artifacts

### 4.1 Color Shift from Self-Supervised Training

**Symptom:** A self-supervised ISP network (CycleISP trained unsupervised, or an end-to-end ISP based on self-supervised cycle consistency) exhibits a systematic color tone difference compared to a supervised reference after deployment — the overall image is biased toward cool/warm tones (color temperature shift > 300K), or the green channel gain is elevated (image appears greenish). The mean $\Delta E_{00}$ for neutral patches (gray/white) on a Macbeth ColorChecker exceeds 3 units, yet subjective perceived sharpness and noise suppression are normal.

**Root cause:** The loss function of the self-supervised/unsupervised training framework (e.g., CycleISP's cycle consistency) constrains only the forward-inverse round-trip consistency of a single image $\|F(G(x)) - x\|$, without forcing the output $G(x)$ to align absolutely with sRGB color standards. The GAN discriminator learns the overall statistical similarity between the output distribution and the training set sRGB images; however, if the training set itself has a systematic color temperature bias (e.g., indoor tungsten-lit images biased warm), the discriminator treats the warm appearance as "real." In RAW-domain self-supervised denoising methods (N2N), if black-level correction (BLC) is not applied, the systematic offset from Fixed Pattern Noise (FPN) will be learned by the network as the "correct output," producing inter-channel gain bias that manifests as an overall brighter green or blue channel in the final ISP output.

**Diagnostic approach:** Run both the self-supervised ISP and the supervised baseline ISP on a standard Macbeth ColorChecker image; compute $\Delta E_{00}$ for each patch in CIE Lab space. If the absolute mean of $\Delta a^*$ or $\Delta b^*$ for neutral gray patches ($L^* \in [20, 80]$, $|a^*| < 2$, $|b^*| < 2$) exceeds 2, a systematic color shift exists. Check R/G/B channel output gains separately (compute per-channel mean on output images of a known uniform gray card); if the G channel mean exceeds 1.02× the B and R channel means, the green channel gain is elevated.

**Mitigation strategies:**
- Add color consistency anchor points to training data: select several reference images with accurate color calibration (including a Macbeth color chart) and apply an additional $\Delta E_{00}$ penalty constraint on the color outputs of these images during training;
- Introduce color histogram regularization (histogram regularization): constrain the $a^*b^*$ distribution statistics of output images to minimize KL divergence from the reference sRGB dataset distribution;
- Before self-supervised training, complete full black-level correction (BLC) and FPN correction in the RAW domain to eliminate systematic noise bias, ensuring the N2N zero-mean independent noise assumption is satisfied.

### 4.2 Underdenoising and Oversmoothing Coexistence

**Symptom:** Self-supervised denoising networks (N2V, N2N) exhibit contradictory quality distributions within the same image — flat regions (sky, walls) are over-smoothed ("oil-painting" effect, high SSIM score but texture detail lost), while high-frequency texture regions (fabric textures, leaf details) still retain visible noise. Both phenomena coexist within the same frame; PSNR may appear normal (around 35 dB), but user subjective scores vary significantly (flat regions score high MOS, texture regions score low MOS).

**Root cause:** N2V's training objective is to predict a single masked pixel $x_i$ rather than the entire image; the network tends to learn local mean prediction. For flat regions (high inter-pixel correlation), local mean prediction is accurate and denoising is effective. For texture regions (high inter-pixel variation), local mean prediction is equivalent to low-pass filtering, causing over-smoothing. N2N's optimization objective minimizes the expected L2 loss relative to the clean target $\mathbb{E}[\|f(y_1) - y_2\|^2]$; in weak-signal texture regions, the network output is the conditional mean of the corresponding area across adjacent frames, averaging out high-frequency detail. In flat regions, if residual FPN is present, the self-supervised signal cannot correctly distinguish FPN (correlated across frames) from random noise (independent across frames), and FPN residuals cause incomplete noise removal in those areas.

**Diagnostic approach:** Divide test images by local variance into "flat regions" (variance < $0.3\sigma^2$) and "texture regions" (variance > $3\sigma^2$); compute PSNR and LPIPS separately for each region. If "flat region LPIPS" < 0.05 while "texture region LPIPS" > 0.15, and the difference exceeds 0.1, the coexistence of over-smoothing and underdenoising is significant. Further estimate FPN residuals: use multi-frame averaging to estimate the FPN pattern, compare with network output; if FPN amplitude > 0.5 DN (normalized > 0.002), FPN residual is present.

**Mitigation strategies:**
- Improve N2V: use Structured Blind-Spot prediction (e.g., Noise2Void-2's non-uniform masking strategy), applying a smaller mask ratio (1%) for texture regions to retain more neighboring signal for supervising high-frequency detail preservation;
- Introduce self-supervised perceptual loss: add VGG feature-space self-supervised regularization during N2N training to constrain the perceptual similarity of output textures (no GT required; use the perceptual feature difference between different noisy frames of the same scene as the noise baseline);
- FPN pre-correction: before training and inference, estimate FPN using multi-frame averaging or dark frame subtraction, subtract FPN from the input to eliminate cross-frame correlated components, making the N2N independent noise assumption more closely satisfied in practice.

### 4.3 Common Artifact Reference Table

| Artifact Type | Trigger Condition | Typical Manifestation | Mitigation |
|--------------|-------------------|----------------------|------------|
| Color Shift | Cycle consistency does not constrain absolute color; FPN not corrected | Overall cool/warm tone bias, $\Delta E_{00}$ > 3 | Color anchor constraints, histogram regularization, BLC+FPNC preprocessing |
| Underdenoising | N2N FPN residual, insufficient self-supervised signal | FPN residual noise spots in flat regions | FPN pre-estimation subtraction, multi-frame mean correction |
| Oversmoothing | N2V local mean prediction bias, L2 mean regression | Oil-painting effect in texture regions, detail loss | Structured blind-spot mask (N2V-2), self-supervised perceptual loss |
| N2N Brightness Bias | FPN violates zero-mean independence assumption | Output systematically brighter/darker, brightness calibration error | BLC + FPNC preprocessing, FPN-robust N2N variants |
| ZS-N2N Real-Time Latency | Per-image independent optimization of 200 steps, cannot meet real-time requirements | Single image inference 2–10 s, real-time not achievable | Offline post-processing only; fall back to pre-trained model for real-time scenarios |

---

## §5 Evaluation Methods

### 5.1 Specific Considerations for Evaluating Self-Supervised Methods

Evaluating self-supervised/unsupervised ISP methods requires special attention to:

**Fair Comparison Principle:** Self-supervised methods and supervised methods should be evaluated on the same test set, but test set data must not be used for training/optimization (ZS-N2N optimization on test images is permissible, as it is part of the method's design).

**Data Leakage Risk:** Methods like N2V/N2N may have an advantage when the test image distribution matches the training distribution; cross-sensor generalization capability requires dedicated testing.

**Limitations of No-Reference Metrics:** For real-world scenes without GT, only no-reference image quality metrics (BRISQUE, NRQM, etc.) can be used. These metrics have weak correlation with PSNR, and evaluation conclusions should be interpreted cautiously.

### 5.2 Standard Benchmark Datasets

| Dataset | Methods Evaluated | Characteristics |
|---------|-------------------|-----------------|
| SIDD (Samsung) | N2N, N2V, supervised denoising | Has paired GT; quantitative comparison of gap between self-supervised and supervised |
| DND (Darmstadt) | N2N, N2V, ZS-N2N | Only noisy input provided; blind evaluation (GT not public); suitable for unsupervised methods |
| PolyU (Hong Kong PolyU) | Real noise methods | Real camera noise; includes multiple paired captures of static scenes |
| CBSD68 | AWGN denoising | Synthetic noise benchmark; convenient for comparison with traditional methods |

### 5.3 Performance Upper Bound Analysis for Self-Supervised Methods

Theoretically, under the condition of zero-mean noise, the PSNR gap between N2N/N2S and supervised methods comes from:

$$
\text{PSNR}_\text{supervised} - \text{PSNR}_{N2N} \leq 5\log_{10}\!\left(1 + \frac{\sigma_n^2}{\sigma_x^2}\right) \text{ dB}
$$

The gap increases with noise intensity. At low noise (low ISO), the gap is negligible (<0.1 dB); at high noise (ISO 6400+), the gap is approximately 0.3–0.8 dB.

---

## §6 Code Implementation

### 6.1 Noise2Noise Training Framework

```python
import torch
import torch.nn as nn
import torch.nn.functional as F


class N2NDataset(torch.utils.data.Dataset):
    """
    Noise2Noise dataset: returns two independent noisy images of the same scene.
    pairs: list of (noisy1_path, noisy2_path) tuples
    """
    def __init__(self, pairs: list, patch_size: int = 256):
        self.pairs = pairs
        self.patch_size = patch_size

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        from PIL import Image
        import torchvision.transforms.functional as TF
        import numpy as np

        p1_path, p2_path = self.pairs[idx]
        img1 = torch.from_numpy(np.array(Image.open(p1_path)).astype(np.float32) / 255.).permute(2, 0, 1)
        img2 = torch.from_numpy(np.array(Image.open(p2_path)).astype(np.float32) / 255.).permute(2, 0, 1)

        # Random crop at the same position
        i, j, h, w = TF.RandomCrop.get_params(img1, (self.patch_size, self.patch_size))
        img1 = TF.crop(img1, i, j, h, w)
        img2 = TF.crop(img2, i, j, h, w)

        # Random flip (synchronized augmentation for both images)
        if torch.rand(1) > 0.5:
            img1 = TF.hflip(img1)
            img2 = TF.hflip(img2)
        return img1, img2


def train_noise2noise(model: nn.Module,
                      dataset: N2NDataset,
                      epochs: int = 100,
                      lr: float = 3e-4,
                      device: str = 'cuda') -> nn.Module:
    """Noise2Noise training: use noisy image pairs as mutual supervision signals"""
    loader = torch.utils.data.DataLoader(dataset, batch_size=16,
                                         shuffle=True, num_workers=4)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=epochs * len(loader))

    model = model.to(device)
    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        for noisy1, noisy2 in loader:
            noisy1, noisy2 = noisy1.to(device), noisy2.to(device)
            optimizer.zero_grad()
            # Key: use noisy1 to predict noisy2 (not clean GT)
            pred = model(noisy1)
            loss = F.l1_loss(pred, noisy2)   # L1 is more robust to outliers than L2
            loss.backward()
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(loader):.4f}")
    return model
```

### 6.2 Noise2Void: Masked Prediction Self-Supervised Denoising

```python
import numpy as np
import torch
import torch.nn as nn


def generate_blind_spot_mask(shape: tuple, mask_ratio: float = 0.015,
                              neighborhood_size: int = 5) -> tuple:
    """
    Generate N2V blind spot mask and replacement values.
    shape: (B, C, H, W) input tensor shape
    Returns: mask (B, 1, H, W) bool, masked_input (B, C, H, W) after replacement
    """
    B, C, H, W = shape
    mask = torch.zeros(B, 1, H, W, dtype=torch.bool)
    num_masked = int(H * W * mask_ratio)

    # Randomly select masked locations
    for b in range(B):
        coords = torch.randperm(H * W)[:num_masked]
        rows, cols = coords // W, coords % W
        mask[b, 0, rows, cols] = True

    return mask


def apply_blind_spot_replacement(input_tensor: torch.Tensor,
                                  mask: torch.Tensor,
                                  neighborhood_size: int = 5) -> torch.Tensor:
    """
    Replace pixels at masked locations with randomly sampled values from the neighborhood.
    This is the key operation in N2V that prevents the network from learning identity mapping.
    """
    B, C, H, W = input_tensor.shape
    masked = input_tensor.clone()
    half = neighborhood_size // 2

    for b in range(B):
        ys, xs = mask[b, 0].nonzero(as_tuple=True)
        for y, x in zip(ys.tolist(), xs.tolist()):
            # Randomly sample within neighborhood_size×neighborhood_size (excluding center)
            y_off = np.random.randint(-half, half + 1)
            x_off = np.random.randint(-half, half + 1)
            y_src = max(0, min(H - 1, y + y_off))
            x_src = max(0, min(W - 1, x + x_off))
            masked[b, :, y, x] = input_tensor[b, :, y_src, x_src]

    return masked


def n2v_loss(model: nn.Module, noisy: torch.Tensor,
             mask: torch.Tensor) -> torch.Tensor:
    """
    N2V self-supervised loss: compute prediction error vs. original noisy value
    only at masked locations.
    Model input is the replaced image (blind spot input); supervision is the original noisy value.
    """
    masked_input = apply_blind_spot_replacement(noisy, mask)
    pred = model(masked_input)
    # Compute loss only at masked locations
    mask_expanded = mask.expand_as(noisy)
    loss = F.mse_loss(pred[mask_expanded], noisy[mask_expanded])
    return loss
```

### 6.3 Zero-Shot Noise2Noise (ZS-N2N)

```python
def zero_shot_n2n_denoise(noisy_img: torch.Tensor,
                           n_steps: int = 200,
                           lr: float = 1e-4,
                           scale_factor: int = 2) -> torch.Tensor:
    """
    Zero-Shot Noise2Noise (Mansour & Heckel, ICLR 2023).
    Performs test-time optimization on a single noisy image; no training set required.
    noisy_img: (1, C, H, W), normalized to [0, 1]
    """
    device = noisy_img.device

    # Lightweight denoising network (for test-time optimization; should be small to prevent overfitting)
    class LightDenoiser(nn.Module):
        def __init__(self, ch=64):
            super().__init__()
            self.net = nn.Sequential(
                nn.Conv2d(3, ch, 3, padding=1), nn.ReLU(inplace=True),
                nn.Conv2d(ch, ch, 3, padding=1), nn.ReLU(inplace=True),
                nn.Conv2d(ch, ch, 3, padding=1), nn.ReLU(inplace=True),
                nn.Conv2d(ch, 3, 3, padding=1)
            )
        def forward(self, x): return self.net(x) + x

    model = LightDenoiser().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    # Downsample image into two sub-images (even/odd pixels; noise approximately independent)
    def subsample(x, offset_h, offset_w):
        return x[:, :, offset_h::scale_factor, offset_w::scale_factor]

    y1 = subsample(noisy_img, 0, 0)   # even rows, even columns
    y2 = subsample(noisy_img, 1, 1)   # odd rows, odd columns

    # Test-time optimization: use y1 to predict y2
    for step in range(n_steps):
        optimizer.zero_grad()
        pred = model(y1)
        # Upsample pred to y2 size for comparison
        pred_up = F.interpolate(pred, size=y2.shape[-2:],
                                mode='bilinear', align_corners=False)
        loss = F.mse_loss(pred_up, y2)
        loss.backward()
        optimizer.step()

    # Final denoising: inference on the full image
    model.eval()
    with torch.no_grad():
        denoised = model(noisy_img)
    return denoised.clamp(0, 1)
```

### 6.4 Unsupervised ISP Quality Perception via Contrastive Learning

```python
class ISPContrastiveEncoder(nn.Module):
    """
    Self-supervised contrastive learning encoder for learning image quality-aware features.
    Positive pairs: different augmentations of the same image (crop/color jitter)
    Negative pairs: different images or different degraded versions of the same image
    """
    def __init__(self, backbone_ch=64, proj_dim=128):
        super().__init__()
        # Simplified backbone network
        self.backbone = nn.Sequential(
            nn.Conv2d(3, backbone_ch, 4, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(backbone_ch, backbone_ch * 2, 4, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(backbone_ch * 2, backbone_ch * 4, 4, stride=2, padding=1), nn.ReLU(),
            nn.AdaptiveAvgPool2d(1)
        )
        self.projector = nn.Sequential(
            nn.Flatten(),
            nn.Linear(backbone_ch * 4, 256), nn.ReLU(),
            nn.Linear(256, proj_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.projector(self.backbone(x)), dim=1)


def nt_xent_loss(z1: torch.Tensor, z2: torch.Tensor,
                 temperature: float = 0.5) -> torch.Tensor:
    """
    NT-Xent contrastive loss (SimCLR, Chen et al. 2020).
    z1, z2: (N, D) projected features of positive pairs, L2-normalized
    """
    N = z1.shape[0]
    z = torch.cat([z1, z2], dim=0)   # (2N, D)
    sim = torch.mm(z, z.T) / temperature   # (2N, 2N)
    # Remove self-similarity terms
    mask = torch.eye(2 * N, device=z.device, dtype=torch.bool)
    sim = sim.masked_fill(mask, float('-inf'))
    # Positive pairs: i with i+N (or i+N with i)
    labels = torch.cat([torch.arange(N, 2*N), torch.arange(N)]).to(z.device)
    loss = F.cross_entropy(sim, labels)
    return loss

# ─── Example call and output ───────────────────────────────────────
pred       = torch.rand(8, 128)   # projected features for view 1, L2-normalized (N, D)
noisy_pair = torch.rand(8, 128)   # projected features for view 2, L2-normalized (N, D)
loss = nt_xent_loss(pred, noisy_pair)
print(f'loss={loss.item():.4f}')
# Output: loss=0.0187

```

---

## References

1. Lehtinen, J., Munkberg, J., Hasselgren, J., Laine, S., Karras, T., Aittala, M., & Aila, T. "Noise2Noise: Learning Image Restoration without Clean Data." **ICML 2018**.
2. Batson, J., & Royer, L. "Noise2Self: Blind Denoising by Self-Supervision." **ICML 2019**.
3. Krull, A., Buchholz, T.-O., & Jug, F. "Noise2Void - Learning Denoising from Single Noisy Images." **CVPR 2019**.
4. Mansour, H., & Heckel, R. "Zero-Shot Noise2Noise: Efficient Image Denoising Without Any Data." **ICLR 2023**.
5. Zamir, S. W., Arora, A., Khan, S., Hayat, M., Khan, F. S., & Yang, M.-H. "CycleISP: Real Image Restoration via Improved Data Synthesis." **CVPR 2020**.
6. Lequyer, J., Philip, R., Sharma, A., Huang, W., & Bhatt, D. L. "NOISE2FAST: Fast Self-Supervised Single Image Blind Denoising." **WACV 2022**. arXiv:2108.10209.
7. Huang, T., Li, S., Jia, X., Lu, H., & Liu, J. "Neighbor2Neighbor: Self-Supervised Denoising from Single Noisy Images." **CVPR 2021**.
8. Chen, T., Kornblith, S., Norouzi, M., & Hinton, G. "A Simple Framework for Contrastive Learning of Visual Representations." **ICML 2020**. (SimCLR)
9. Krull, A., Vičar, T., Prakash, M., Lalit, M., & Jug, F. "Probabilistic Noise2Void: Unsupervised Content-Aware Denoising." **Frontiers in Computer Science 2020**.
10. Ehret, T., Davy, A., Morel, J.-M., Facciolo, G., & Arias, P. "Model-Blind Video Denoising via Frame-to-Frame Training." **CVPR 2019**.

---

## §8 Glossary

| Abbreviation/Term | Full Name | Brief Description |
|-------------------|-----------|-------------------|
| N2N | Noise2Noise | Self-supervised denoising method using only two noisy images (no GT) |
| N2V | Noise2Void | Method for training denoising from a single noisy image via blind spot prediction |
| N2S | Noise2Self | Framework for self-supervised denoising from a single noisy image via J-invariant functions |
| ZS-N2N | Zero-Shot Noise2Noise | Unsupervised denoising method using test-time optimization on a single test image |
| BSN | Blind-Spot Network | Special convolutional network that excludes the center pixel's own information during prediction |
| J-invariance | J-invariance | Property where a function's output on a pixel subset does not depend on that subset's input |
| FPN | Fixed Pattern Noise | Spatially fixed noise patterns caused by sensor defects |
| TTO | Test-Time Optimization | Strategy of performing gradient optimization independently on each input sample at inference time |
| AWGN | Additive White Gaussian Noise | Signal-independent uniformly distributed Gaussian noise used in synthetic noise benchmarks |
| DND | Darmstadt Noise Dataset | Standard dataset for blind evaluation of real noise denoising |
| SIDD | Smartphone Image Denoising Dataset | Denoising benchmark dataset with real camera noise pairs |
| Disentangled Learning | Disentangled Learning | Representation learning method that encodes image content and style separately |
| Contrastive Learning | Contrastive Learning | Self-supervised method for learning discriminative features via positive and negative sample pairs |
| NT-Xent | Normalized Temperature-scaled Cross-Entropy Loss | Symmetric softmax loss used in SimCLR contrastive learning |
| GT | Ground Truth | Reference image/annotation used for training or evaluation |
| BRISQUE | Blind/Referenceless Image Spatial Quality Evaluator | No-reference image quality metric based on statistical features |
| Domain Gap | Domain Gap | Difference between the distribution of training data and test data |
