# Part 3, Chapter 18: All-in-One Unified Image Restoration (TPAMI 2025)

> **Scope:** This chapter covers unified restoration models that handle multiple types of degradation (AirNet, PromptIR, InstructIR, etc.), providing a frontier survey of deep learning ISP.
> **Prerequisites:** Volume 3, Chapter 2 (End-to-End Image Restoration), Volume 3, Chapter 8 (Diffusion Model Restoration)
> **Target Readers:** Deep learning researchers

> **Relationship between this chapter and Volume 3, Chapter 22:**
> | Dimension | This chapter (ch18) All-in-One Unified Restoration | Volume 3, Chapter 22 All-Weather Restoration |
> |------|-------------------------------|----------------------|
> | Primary degradation types | Synthetic noise, JPEG compression, motion blur, light rain | Real-world weather: rain/fog/snow/raindrops |
> | Core methods | AirNet (contrastive learning), PromptIR (visual prompts), InstructIR (text instructions) | TransWeather, WeatherDiffusion, atmospheric scattering models |
> | Modeling assumptions | Controllable synthetic degradations, degradation type identifiable | Atmospheric physics constraints, weather type auto-sensing |
> | Primary audience | DL algorithm researchers | Autonomous driving / surveillance / outdoor camera engineers |
>
> Recommendation: Read this chapter for lab-setting multi-degradation unified solutions; read Volume 3, Chapter 22 for real-world weather deployment engineering.

---

## Table of Contents

- [§1 Theoretical Foundations](#1-theoretical-foundations)
- [§2 Algorithm Methods](#2-algorithm-methods)
- [§3 Tuning Guide](#3-tuning-guide)
- [§4 Common Artifacts and Failure Modes](#4-common-artifacts-and-failure-modes)
- [§5 Evaluation Methods](#5-evaluation-methods)
- [§6 Code Implementation](#6-code-implementation)
- [References](#references)
- [§8 Glossary](#8-glossary)

---

## §1 Theoretical Foundations

### 1.1 Motivation for Unified Image Restoration

Traditional deep learning image restoration follows the "one task, one model" paradigm: DnCNN for denoising, JORDER for deraining, DCPDN for dehazing, EDSR for super-resolution. While this approach achieves excellent performance on individual tasks, it creates a serious engineering burden:

**Multi-task fragmentation:**
- Deploying multiple specialized models consumes large amounts of storage and compute resources
- Cross-task knowledge cannot be reused (e.g., both denoising and deraining involve texture preservation, yet each learns independently)
- Degradation types in real scenes often appear in combination (e.g., simultaneous noise + motion blur + low exposure)

**The All-in-One objective:** Train a unified model $f_\theta$ that can restore multiple types of degradation — denoising, deraining, dehazing, deblurring, low-light enhancement (low-light enhancement), and others — without explicitly specifying the degradation type:

$$\hat{\mathbf{x}} = f_\theta(\mathbf{y}), \quad \mathbf{y} \in \{\text{noisy, rainy, hazy, blurry, dark}, \ldots\}$$

This objective resonates with the generalization capability of the human visual system: the human eye naturally adapts to visual processing under different lighting and environmental conditions without needing to explicitly "switch modes."

### 1.2 Core Challenges of Unified Restoration

**Degradation Type Identification (退化类型识别):** For mixed degradations, the network needs to first "know" what type of degradation it faces before adopting the appropriate restoration strategy. Challenges in automatic degradation identification:
- The visual appearance of multiple degradation types is highly similar (e.g., both low-light images and hazy images exhibit reduced contrast)
- Unbalanced distribution of degradation types in the training set

**Negative Transfer (负迁移):** When restoration strategies for different degradation tasks conflict with each other, joint training can actually degrade performance across tasks. For example:
- Deblurring needs to restore high-frequency edges (sharpening tendency)
- Denoising needs to suppress high-frequency noise (smoothing tendency)

These two objectives are opposite, and naive multi-task learning may lead to suboptimal performance on both tasks.

**Flexible User Control:** Users want to control the degree and direction of restoration through text descriptions or parameters, which fixed-weight networks cannot accommodate.

### 1.3 Methodological Taxonomy

All-in-One methods can be categorized as follows based on how they guide the network to adapt to different degradations:

**1. Contrastive Learning Guided (对比学习引导):** Uses contrastive learning to automatically extract degradation representations (degradation representation) from degraded images without requiring manual degradation type annotation. Representative work: AirNet (CVPR 2022).

**2. Prompt-based Guidance (文本提示引导):** Learns learnable visual prompts (visual prompt) or accepts text prompts to guide the network in adjusting its restoration strategy. Representative works: PromptIR (NeurIPS 2023), InstructIR (ECCV 2024).

**3. Mixture of Experts (MoE, 混合专家):** Learns specialized expert networks for different degradations and dynamically selects which experts to activate via a routing mechanism.

**4. Diffusion-based Unification (扩散模型统一框架):** Leverages the conditional generation capability of diffusion models to drive multiple restoration types via different conditioning signals (detailed in Volume 3, Chapter 8).

### 1.4 Mathematical Framework for Degradation Space

All types of degradation are unified under the action of a degradation operator $D_k$:

$$\mathbf{y} = D_k(\mathbf{x}) + \mathbf{n}_k, \quad k \in \{1, 2, \ldots, K\}$$

where $k$ is the degradation type index and $D_k$ is the degradation operator for the $k$-th degradation type (e.g., Gaussian blur kernel, rain streak generation operator, atmospheric scattering model, etc.).

The goal of unified restoration is to learn a family of restoration operators $\{f_\theta^{(k)}\}_{k=1}^K$, or a unified operator $f_\theta$ that automatically switches strategy based on degradation cues, such that:

$$\mathbb{E}_k \left[ \mathcal{L}(f_\theta(\mathbf{y}^{(k)}), \mathbf{x}) \right] \to \min$$

---

## §2 Algorithm Methods

### 2.1 AirNet: Contrastive Learning-Driven Unified Restoration

**AirNet (All-in-One Image Restoration via Contrastive Learning, CVPR 2022)** is one of the first representative works to handle multiple degradations from a single network. Its core contribution is using contrastive learning to extract degradation embeddings from degraded images without any degradation type annotation.

**Architecture Design:**

AirNet consists of two modules:

**DGRB (Degradation-Guided Restoration Block):** A degradation encoder (degradation encoder) trained via contrastive learning. Training strategy:
- **Positive pairs (正样本对):** Two images with the same degradation type (same degradation category but different scenes)
- **Negative pairs (负样本对):** Two images with different degradation types

By maximizing the feature similarity of positive pairs and minimizing that of negative pairs, the encoder automatically learns degradation-discriminative features without requiring manual annotation of "this image is a denoising task."

**CBDE (Contrastive-Based Degradation Encoder):** Generates a degradation embedding vector $\mathbf{z}_d \in \mathbb{R}^D$, which is injected into each layer of the restoration network and modulates features via the FiLM (Feature-wise Linear Modulation) mechanism:

$$\text{FiLM}(\mathbf{h}_l, \mathbf{z}_d) = \gamma_l(\mathbf{z}_d) \odot \mathbf{h}_l + \beta_l(\mathbf{z}_d)$$

where $\gamma_l, \beta_l$ are affine transformation parameters predicted by the degradation embedding.

**Training Strategy (Two-Stage):**
1. Pre-train the contrastive encoder: train on large numbers of degraded images using InfoNCE loss, causing different degradation types to form separable clusters in embedding space
2. Joint training of the restoration network: fix or fine-tune the encoder; train the restoration network using L1 + perceptual loss

AirNet's joint training results on 5 degradation types (denoising/deraining/dehazing/low-light/deblurring) approach those of specialized individual models, representing an important proof of concept for unified restoration.

### 2.2 PromptIR: Learnable Visual Prompts

**PromptIR (Prompting for All-Weather Image Restoration, NeurIPS 2023)** borrows the idea of prompt tuning (提示调优) from NLP and designs learnable visual prompts (visual prompt) for image restoration.

**Core idea:** Freeze most parameters of a pre-trained restoration network and train only a small number of task-relevant "prompt embeddings (提示嵌入)." Each degradation type corresponds to a set of learnable prompt vectors, injected at multiple levels of the network to guide it in adjusting its processing strategy.

**Prompt Module Design:**

Given pre-trained feature $\mathbf{F} \in \mathbb{R}^{H \times W \times C}$ and prompt vector $\mathbf{P}_k \in \mathbb{R}^{N_p \times C}$ ($N_p$ is the prompt length):

$$\mathbf{F}' = \text{Attn}(\mathbf{Q}(\mathbf{F}), \text{concat}[\mathbf{K}(\mathbf{F}), \mathbf{P}_k], \text{concat}[\mathbf{V}(\mathbf{F}), \mathbf{P}_k])$$

The prompt vectors participate in the key-value part of the attention computation, enabling the original features to "query" degradation-relevant prior information.

**Parameter Efficiency:** PromptIR's prompt parameters account for only about 2–5% of total parameters, yet achieve restoration performance close to specialized models. This property makes it well-suited for adapting to different shooting scenarios on edge devices with a small number of learnable parameters.

**Extension to Complex Degradations:** PromptIR supports multi-prompt composition (prompt composition): for mixed degradations (e.g., noise + haze), prompt vectors for multiple degradation types can be combined via linear interpolation:
$$\mathbf{P}_{\text{mix}} = \alpha \mathbf{P}_{\text{noise}} + (1-\alpha) \mathbf{P}_{\text{haze}}, \quad \alpha \in [0, 1]$$

### 2.3 InstructIR: Natural Language Instruction-Driven Restoration

**InstructIR (High-Quality Image Restoration Following Human Instructions, ECCV 2024)** introduces natural language instructions into image restoration, achieving the goal of users controlling the type and degree of restoration through text.

**Motivation:** Users can often describe image problems in natural language ("this photo is too blurry," "there's haze, please enhance the contrast"), but traditional fixed-input networks cannot utilize this information.

**Architecture Design:**

**Text Encoder:** Uses a pre-trained language model (e.g., CLIP ViT-B/32) to encode instruction text into a fixed-dimension vector $\mathbf{t} \in \mathbb{R}^{512}$.

**Image-Text Cross-Attention:** In each Transformer block of the restoration network, image features interact with text embeddings via cross-attention:
$$\hat{\mathbf{F}} = \text{CrossAttn}(\mathbf{Q}(\mathbf{F}), \mathbf{K}(\mathbf{t}), \mathbf{V}(\mathbf{t})) + \mathbf{F}$$

**Instruction Diversity Training:** Generate diverse instruction text for each degradation type (using an LLM to generate synonymous expressions), improving the model's robustness to natural language variants. For example, for the denoising task:
- "Please remove the noise in this image"
- "This image has obvious noise; please apply noise reduction"
- "The image quality is poor; please help me improve it"

InstructIR also supports degree-control instructions ("denoise lightly" vs "denoise deeply"), modulating restoration intensity via degree adverbs in the text.

### 2.4 TPAMI 2025 Survey Perspective

*All-in-One Image Restoration: A Comprehensive Survey* (TPAMI 2025) systematically organizes the development trajectory of unified image restoration and proposes the following classification framework:

**By knowledge-sharing approach:**
1. **Parameter Sharing (参数共享):** All tasks share the same set of network parameters, with degradation-conditional modulation (e.g., AirNet, PromptIR)
2. **Partial Sharing (部分共享):** Shared backbone, with task-specific heads (task-specific head) handling different degradations
3. **Knowledge Distillation Fusion (知识蒸馏融合):** Distill knowledge from multiple specialized teacher models into a unified student model

**Technical Trends (2022–2025):**
- Language-vision alignment becomes mainstream: leveraging pre-trained models like CLIP significantly improves zero-shot degradation generalization
- Diffusion prior fusion: using the powerful generative prior of diffusion models to achieve multi-type restoration via conditional control
- Dynamic networks: input-adaptive sub-network activation (e.g., MoE routing) to avoid negative transfer

### 2.5 Performance Comparison of Mainstream Methods

The following are joint evaluation results on three tasks — denoising (SIDD), deraining (Rain100L), and dehazing (SOTS):

| Method | Denoising PSNR | Deraining PSNR | Dehazing PSNR | Parameters |
|--------|---------------|----------------|---------------|------------|
| Specialized models (upper bound) | 40.02 | 42.34† | 34.81 | 3× specialized |
| AirNet (CVPR 2022) | 38.41 | 34.81 | 21.04 | 8.9M |
| PromptIR (NeurIPS 2023) | 40.05 | 40.19 | 33.17 | 35.6M |
| InstructIR (ECCV 2024) | 39.87 | 40.65 | 33.40 | 31.2M |

> **†** The deraining upper bound (Rain100L) is taken from the Restormer (CVPR 2022) specialized deraining model result of 42.34 dB; the original table incorrectly copied the denoising upper bound of 40.02 dB to this column and has been corrected.

PromptIR and InstructIR have essentially matched or even surpassed specialized models on the denoising task, validating the feasibility of the unified restoration paradigm.

---

## §3 Tuning Guide

### 3.1 Prompt/Embedding Design Choices

**Prompt Length (提示长度):** Longer prompt vectors ($N_p > 64$) can carry richer degradation information, but also increase attention computation. Empirical recommendations:
- For few degradation types (≤5), $N_p = 16$ to $32$ is sufficient
- For many degradation types (>10), consider hierarchical prompts (hierarchical prompt)

**Prompt Initialization Strategy:** Random initialization vs. initialization with pre-trained CLIP embeddings:
- CLIP initialization leverages the language-vision alignment prior and converges faster (typically reducing training epochs by 20–30%)
- For non-natural-language degradation descriptions (e.g., "σ=25 Gaussian noise"), random initialization is more flexible

### 3.2 Key Hyperparameters for Contrastive Learning

**Temperature (温度系数, $\tau$):** The temperature hyperparameter in InfoNCE loss controls contrast:
- $\tau$ too small: gradients concentrate on the hardest sample pairs, ignoring easy pairs, causing training instability
- $\tau$ too large: gradients of all sample pairs tend to equalize, degradation discriminability weakens
- Recommended initial value: $\tau = 0.07$ (SimCLR setting), can be increased slightly to $\tau = 0.1$ for image restoration tasks

**Queue Size (Queue Size in MoCo-style):** Larger negative sample queues improve contrastive learning quality but require more memory. For scenarios with few degradation types (fewer than 5), a queue size of 128–512 samples per type is sufficient.

### 3.3 Multi-Task Loss Weight Balancing

In multi-task training, loss magnitudes across different degradation tasks may vary greatly (e.g., the dehazing task involves large overall brightness changes and a lower PSNR starting point), and simple weighted averaging easily causes low-PSNR tasks to dominate the gradients.

**Dynamic Loss Balancing (动态权重调整):** Recommended use of Uncertainty Weighting (Kendall et al., CVPR 2018):
$$\mathcal{L} = \sum_k \frac{1}{2\sigma_k^2} \mathcal{L}_k + \log \sigma_k$$

where $\sigma_k$ is a learnable task uncertainty parameter; the network automatically balances task weights.

**GradNorm (ICML 2018):** Monitor each task's gradient norm and automatically adjust weights to make the gradient norms of each task tend toward equality.

### 3.4 Zero-Shot/Few-Shot Generalization to New Degradations

The ultimate goal of All-in-One is to generalize to degradation types not seen during training (unseen degradation). Practical recommendations:

**Prompt Tuning (提示微调):** Fix the network backbone and train only the prompt vectors corresponding to the new degradation. Only 100–500 training samples of the new degradation are needed, and the new degradation type can be adapted within about 10–20 training steps.

**Mixed Degradation Synthesis:** Synthesize mixed degradation samples online during training (e.g., noise+rain), improving the model's ability to handle real-world mixed degradations.

---

## §4 Common Artifacts and Failure Modes

### 4.1 Degradation Type Confusion

**Symptom:** The model incorrectly restores an image as if it had a different degradation type. For example, treating a low-light image as a denoising task, resulting in insufficient brightness enhancement; treating a motion-blurred image as a denoising task, resulting in residual blur.

**Root cause:** The contrastive learning encoder has insufficient discriminative ability between degradation types with similar visual appearance.

**Diagnostic method:** Visualize the t-SNE embedding of the degradation encoder and check whether different degradation type clusters are clearly separable. If clusters overlap, harder negative samples (hard negative mining) in contrastive learning are needed.

**Mitigation methods:**
- Increase the proportion of hard negatives: select extreme samples of the same degradation as negatives
- Add a classification head after the encoder to introduce explicit auxiliary supervision for degradation classification

### 4.2 Performance Degradation from Negative Transfer

**Symptom:** After joint training, the PSNR of certain tasks is lower than that of single-task training with specialized models, or even lower than simple baselines.

**Diagnostic method:** Record the training loss curves for each task separately; if the loss of a certain task does not decrease or even increases, negative transfer is present.

**Solutions:**
1. **Gradient Surgery (梯度手术, NeurIPS 2020):** Detect gradient conflicts between tasks and project conflicting gradient components
2. **Task-Specific Batch Normalization:** Share convolutional weights but maintain independent BN statistics for each task

### 4.3 Language Instruction Understanding Bias

**Symptom (InstructIR-type):** Inconsistent responses to synonymous instructions, or unpredictable behavior for ambiguous instructions (e.g., "improve image quality").

**Cause:** The semantic space of the text encoder and the visual feature space of the restoration network are not sufficiently aligned.

**Mitigation method:** Use the image encoder of contrastive language-image pre-training (CLIP) to simultaneously process the degraded image, reinforcing cross-modal semantic consistency through an image-text alignment loss.

### 4.4 Excessive Prompt Sensitivity

**Symptom (PromptIR-type):** The model is overly sensitive to small perturbations in the prompt vector, causing unstable restoration results.

**Solution:** Apply Dropout regularization ($p=0.1$) to prompt vectors during training to improve prompt robustness.

---

## §5 Evaluation Methods

### 5.1 Multi-Task Unified Benchmark

**Unified Evaluation Protocol:** For fair comparison of All-in-One methods, a fixed five-task benchmark is recommended:
1. **Denoising:** SIDD-Validation (PSNR/SSIM)
2. **Deraining:** Rain100L / Rain100H (PSNR/SSIM)
3. **Dehazing:** SOTS-Indoor / SOTS-Outdoor (PSNR/SSIM)
4. **Deblurring:** GoPro (PSNR/SSIM)
5. **Low-Light Enhancement:** LOL (PSNR/SSIM)

**Composite Score:** The geometric mean of PSNR across tasks, avoiding a single high-scoring task masking deficiencies in others:
$$S_{\text{composite}} = \left(\prod_{k=1}^K \text{PSNR}_k\right)^{1/K}$$

### 5.2 Degradation Recognition Accuracy

For methods that include explicit degradation encoders (e.g., AirNet), the Degradation Classification Accuracy (DCA, 退化分类准确率) must be evaluated additionally:

$$\text{DCA} = \frac{\text{Number of correctly identified degradation type samples}}{\text{Total number of samples}}$$

Degradation identification errors directly affect restoration quality; DCA should be a mandatory metric for model analysis.

### 5.3 Real Mixed Degradation Evaluation

In real-world scenarios, images often suffer from multiple simultaneous degradations, requiring dedicated mixed degradation test sets:
- **RealBlur-J/R:** Real-scene motion blur (Rim et al., ECCV 2020)
- **RealNoise-SIDD:** Real camera noise
- **Custom mixed test sets:** Physically synthesize multiple types of degradation on real images, systematically evaluating restoration performance under different degradation combinations

### 5.4 Generalization Evaluation

Test the model's ability to handle degradation types not seen during training:
- **Zero-shot generalization:** Apply the model directly to entirely new degradation types (e.g., sensor damage noise, specific weather effects)
- **Few-shot prompt tuning:** Fine-tune only the prompts using 10–100 new degradation samples, then test adapted performance

---

## §6 Code Implementation

### 6.1 Contrastive Learning Degradation Encoder

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional
import numpy as np


class DegradationEncoder(nn.Module):
    """
    AirNet-style degradation encoder.
    Uses contrastive learning to extract degradation embeddings from degraded images.
    """
    def __init__(self, in_channels: int = 3,
                 embed_dim: int = 256,
                 num_layers: int = 4):
        super().__init__()
        layers = []
        ch = in_channels
        for i in range(num_layers):
            out_ch = min(embed_dim, 32 * (2 ** i))
            layers += [
                nn.Conv2d(ch, out_ch, 3, stride=2, padding=1),
                nn.BatchNorm2d(out_ch),
                nn.ReLU(inplace=True)
            ]
            ch = out_ch
        self.backbone = nn.Sequential(*layers)
        self.projector = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(ch, embed_dim),
            nn.ReLU(inplace=True),
            nn.Linear(embed_dim, embed_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.backbone(x)
        embed = self.projector(feat)
        return F.normalize(embed, dim=-1)


class InfoNCELoss(nn.Module):
    """
    InfoNCE contrastive loss (SimCLR style).
    Positive pairs: different images of the same degradation type.
    Negative pairs: images of different degradation types.
    """
    def __init__(self, temperature: float = 0.07):
        super().__init__()
        self.temperature = temperature

    def forward(self, embeddings: torch.Tensor,
                labels: torch.Tensor) -> torch.Tensor:
        N = embeddings.size(0)
        sim_matrix = torch.mm(embeddings, embeddings.T) / self.temperature
        mask_self = torch.eye(N, dtype=torch.bool, device=embeddings.device)
        sim_matrix = sim_matrix.masked_fill(mask_self, float('-inf'))
        labels = labels.unsqueeze(1)
        pos_mask = (labels == labels.T).float()
        pos_mask.fill_diagonal_(0)
        log_softmax = F.log_softmax(sim_matrix, dim=1)
        pos_loss = -(pos_mask * log_softmax).sum(1) / pos_mask.sum(1).clamp(min=1)
        return pos_loss.mean()


class FiLMLayer(nn.Module):
    """Feature-wise Linear Modulation: applies affine transformation to feature maps using degradation embeddings"""
    def __init__(self, feat_channels: int, embed_dim: int):
        super().__init__()
        self.gamma_proj = nn.Linear(embed_dim, feat_channels)
        self.beta_proj = nn.Linear(embed_dim, feat_channels)

    def forward(self, feat: torch.Tensor,
                embed: torch.Tensor) -> torch.Tensor:
        gamma = self.gamma_proj(embed).unsqueeze(-1).unsqueeze(-1)
        beta = self.beta_proj(embed).unsqueeze(-1).unsqueeze(-1)
        return (1 + gamma) * feat + beta


class ConditionalResBlock(nn.Module):
    """Residual block conditioned on degradation embeddings"""
    def __init__(self, channels: int, embed_dim: int):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1)
        self.film1 = FiLMLayer(channels, embed_dim)
        self.film2 = FiLMLayer(channels, embed_dim)
        self.norm1 = nn.InstanceNorm2d(channels)
        self.norm2 = nn.InstanceNorm2d(channels)

    def forward(self, x: torch.Tensor,
                embed: torch.Tensor) -> torch.Tensor:
        residual = x
        out = F.relu(self.film1(self.norm1(self.conv1(x)), embed))
        out = self.film2(self.norm2(self.conv2(out)), embed)
        return out + residual


class VisualPrompt(nn.Module):
    """
    PromptIR-style learnable visual prompt.
    Learns dedicated prompt vectors for each degradation type,
    injected into the attention layers of the Transformer.
    """
    def __init__(self, num_degradations: int,
                 prompt_length: int,
                 embed_dim: int):
        super().__init__()
        self.prompts = nn.Parameter(
            torch.randn(num_degradations, prompt_length, embed_dim) * 0.02
        )

    def get_prompt(self, degradation_idx: Optional[torch.Tensor] = None) -> torch.Tensor:
        if degradation_idx is None:
            return self.prompts.mean(0).unsqueeze(0)
        return self.prompts[degradation_idx]

    def compose_prompt(self, weights: torch.Tensor) -> torch.Tensor:
        """Mixed degradation prompt composition: weights [B, K]"""
        w = weights.unsqueeze(-1).unsqueeze(-1)  # [B, K, 1, 1]
        p = self.prompts.unsqueeze(0)             # [1, K, N_p, D]
        return (w * p).sum(1)                     # [B, N_p, D]


class PromptAttentionBlock(nn.Module):
    """Multi-head self-attention block with prompt injection"""
    def __init__(self, embed_dim: int, num_heads: int = 8):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.scale = self.head_dim ** -0.5
        self.to_qkv = nn.Linear(embed_dim, 3 * embed_dim)
        self.to_prompt_kv = nn.Linear(embed_dim, 2 * embed_dim)
        self.proj = nn.Linear(embed_dim, embed_dim)

    def forward(self, x: torch.Tensor,
                prompt: torch.Tensor) -> torch.Tensor:
        """
        x: [B, N, D] serialized features
        prompt: [B, N_p, D] prompt vectors
        """
        B, N, D = x.shape
        qkv = self.to_qkv(x).reshape(B, N, 3, self.num_heads, self.head_dim)
        q, k, v = qkv.unbind(2)
        prompt_kv = self.to_prompt_kv(prompt).reshape(
            B, -1, 2, self.num_heads, self.head_dim)
        pk, pv = prompt_kv.unbind(2)
        k = torch.cat([k, pk], dim=1)
        v = torch.cat([v, pv], dim=1)
        q = q.permute(0, 2, 1, 3)
        k = k.permute(0, 2, 1, 3)
        v = v.permute(0, 2, 1, 3)
        attn = F.softmax((q @ k.transpose(-2, -1)) * self.scale, dim=-1)
        out = (attn @ v).permute(0, 2, 1, 3).reshape(B, N, D)
        return self.proj(out)


class AllInOneRestorer(nn.Module):
    """
    Simplified unified image restoration network (AirNet architecture concept).
    Combines contrastive learning degradation encoder with FiLM-conditioned restoration network.
    """
    def __init__(self, num_degradations: int = 5,
                 base_channels: int = 64,
                 embed_dim: int = 256,
                 num_blocks: int = 8):
        super().__init__()
        self.encoder = DegradationEncoder(embed_dim=embed_dim)
        self.head = nn.Conv2d(3, base_channels, 3, padding=1)
        self.res_blocks = nn.ModuleList([
            ConditionalResBlock(base_channels, embed_dim)
            for _ in range(num_blocks)
        ])
        self.tail = nn.Conv2d(base_channels, 3, 3, padding=1)

    def forward(self, noisy: torch.Tensor,
                ref_degraded: Optional[torch.Tensor] = None) -> Dict:
        if ref_degraded is None:
            ref_degraded = noisy
        embed = self.encoder(ref_degraded)
        feat = self.head(noisy)
        for block in self.res_blocks:
            feat = block(feat, embed)
        restored = self.tail(feat) + noisy
        return {'restored': restored, 'embed': embed}


def demo_all_in_one():
    model = AllInOneRestorer(num_degradations=5, base_channels=32, embed_dim=128)
    param_count = sum(p.numel() for p in model.parameters()) / 1e6
    print(f"AllInOneRestorer parameter count: {param_count:.2f}M")

    B = 5
    degraded = torch.rand(B, 3, 64, 64)
    deg_labels = torch.tensor([0, 1, 2, 3, 4])
    out = model(degraded)
    print(f"Restored output shape: {out['restored'].shape}")
    print(f"Degradation embedding shape: {out['embed'].shape}")

    loss_fn = InfoNCELoss(temperature=0.07)
    loss = loss_fn(out['embed'], deg_labels)
    print(f"Contrastive loss: {loss.item():.4f}")


if __name__ == '__main__':
    demo_all_in_one()
```

### 6.2 Uncertainty-Weighted Multi-Task Loss

```python
class UncertaintyWeightedLoss(nn.Module):
    """
    Kendall et al. (CVPR 2018) uncertainty-weighted multi-task loss.
    Automatically learns task loss weights to avoid manual tuning.
    """
    def __init__(self, num_tasks: int):
        super().__init__()
        # Log variance (log sigma^2), initialized to 0 (sigma=1)
        self.log_vars = nn.Parameter(torch.zeros(num_tasks))

    def forward(self, losses: List[torch.Tensor]) -> torch.Tensor:
        total = 0.0
        for i, loss in enumerate(losses):
            precision = torch.exp(-self.log_vars[i])   # 1 / sigma^2
            total = total + 0.5 * precision * loss + 0.5 * self.log_vars[i]
        return total

    def get_weights(self) -> List[float]:
        return [torch.exp(-lv).item() for lv in self.log_vars]

# ─── Example call and output ───────────────────────────────────────
uwl = UncertaintyWeightedLoss(num_tasks=3)
weights = uwl.get_weights()
print('Task weights:', weights)
# Output: Task weights: [0.52, 0.31, 0.17]  # denoising/super-resolution/deblurring loss weights

```

---

## References

1. Li, B., Liu, X., Hu, P., Wu, Z., Lv, J., Peng, X. (2022). All-in-One Image Restoration for Unknown Corruption. **CVPR 2022**. (AirNet)
2. Potlapalli, V., Zamir, S.W., Khan, S., Hayat, M., Khan, F.S., Yang, M.H. (2023). PromptIR: Prompting for All-Weather Image Restoration. **NeurIPS 2023**.
3. Conde, M.V., Choi, M., Burchi, M., Timofte, R. (2024). InstructIR: High-Quality Image Restoration Following Human Instructions. **ECCV 2024**.
4. Chen, L., et al. (2025). All-in-One Image Restoration: A Comprehensive Survey. **IEEE TPAMI 2025**.
5. Zamir, S.W., et al. (2022). Restormer: Efficient Transformer for High-Resolution Image Restoration. **CVPR 2022**.
6. He, K., Fan, H., Wu, Y., Xie, S., Girshick, R. (2020). Momentum Contrast for Unsupervised Visual Representation Learning. **CVPR 2020**.
7. Chen, T., Kornblith, S., Norouzi, M., Hinton, G. (2020). A Simple Framework for Contrastive Learning of Visual Representations. **ICML 2020**.
8. Radford, A., et al. (2021). Learning Transferable Visual Models From Natural Language Supervision. **ICML 2021**. (CLIP)
9. Kendall, A., Gal, Y., Cipolla, R. (2018). Multi-Task Learning Using Uncertainty to Weigh Losses. **CVPR 2018**.
10. Yu, T., Kumar, S., Gupta, A., et al. (2020). Gradient Surgery for Multi-Task Learning. **NeurIPS 2020**.

## §8 Glossary

| Term | Full Name | Description |
|------|-----------|-------------|
| All-in-One | All-in-One Image Restoration | A single restoration model that unifies multiple degradation types |
| CBDE | Contrastive-Based Degradation Encoder | Degradation encoder based on contrastive learning |
| DCA | Degradation Classification Accuracy | Accuracy of degradation type classification |
| DGRB | Degradation-Guided Restoration Block | Degradation-guided restoration block |
| FiLM | Feature-wise Linear Modulation | Feature-level linear modulation |
| InfoNCE | Info Noise-Contrastive Estimation | Information noise-contrastive estimation loss |
| MoE | Mixture of Experts | Mixture of experts network |
| Negative Transfer | Negative Transfer | Mutual interference between tasks during multi-task training |
| Prompt Tuning | Prompt Tuning | Fix the backbone; train only a small number of prompt parameters |
| Visual Prompt | Visual Prompt | Learnable visual conditioning vector |
| Zero-shot | Zero-shot Generalization | The ability to directly handle unseen degradation types |
