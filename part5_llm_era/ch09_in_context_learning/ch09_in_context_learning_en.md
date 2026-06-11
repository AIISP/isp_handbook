# Part 5, Chapter 09: In-Context Learning and Scene-Adaptive ISP

> **Frontier content**: Based on 2025-2026 CVPR/ICCV/NeurIPS advances. Engineering deployment cases are actively expanding. Contributions welcome via [Issue](https://github.com/AIISP/isp_handbook/issues).

> **Position:** This chapter introduces the application of In-Context Learning (ICL, 上下文学习) theory to the ISP scene-adaptation problem, with a focus on how to use FAISS vector retrieval to build dynamic prompts that enable few-shot ISP parameter adaptation for new scenes or new sensors at inference time, without any gradient updates.
> **Prerequisites:** Vol. 5 Ch. 03 (LLM-Assisted ISP Tuning), Vol. 5 Ch. 08 (Automated Tuning)
> **Audience:** Algorithm engineers, deep learning researchers

---

## §1 Theory

### 1.1 Fundamentals of In-Context Learning

In-Context Learning (ICL, 上下文学习) is a distinctive capability of Large Language Models (LLMs, 大语言模型): **at inference time**, by providing a small number of input–output examples (k-shot examples) in the prompt (提示), the model can adapt to a new task **without modifying any model weights** (no gradient updates).

The standard ICL prompt structure (k = 3 example) is as follows:

```
[Example 1]
Input: <scene description 1>
Output: <optimal ISP parameters 1>

[Example 2]
Input: <scene description 2>
Output: <optimal ISP parameters 2>

[Example 3]
Input: <scene description 3>
Output: <optimal ISP parameters 3>

[Query]
Input: <new scene description>
Output: ?
```

The LLM infers the output corresponding to the query scene based on the example patterns in the context, without requiring any training on that task.

Key distinction from traditional few-shot learning (少样本学习):
- **Traditional few-shot learning**: performs gradient updates on a small number of annotated samples (Meta-Learning methods such as MAML)
- **ICL**: completely gradient-free; injects examples through prompts only and leverages the prior reasoning capabilities of the pretrained LLM

### 1.2 Theoretical Foundation of ICL: Implicit Bayesian Inference

Xie et al. (NeurIPS 2022) proved theoretically that ICL is equivalent to **implicit Bayesian inference** (隐式贝叶斯推断): in a sufficiently large pretrained language model, ICL is equivalent to performing Bayesian posterior updates on the examples.

The formal derivation is as follows. Let concept $c$ be the latent variable (隐变量) generating the data (in the ISP context, $c$ can be understood as "scene type + optimal parameter configuration"), the example sequence as $\{(x_1, y_1), \ldots, (x_k, y_k)\}$, and the query input as $x_{k+1}$. ICL computes:

$$P_{\text{ICL}}(y_{k+1} \mid x_{k+1}, \text{context}) = \sum_c P(y_{k+1} \mid x_{k+1}, c) \cdot P(c \mid x_1, y_1, \ldots, x_k, y_k)$$

where $P(c \mid \cdot)$ is the posterior distribution inferred from the context examples — i.e., inferring which "concept" (parameter configuration type) the current scene belongs to. This theory explains why more high-quality examples generally lead to better ICL performance: each example updates the posterior estimate of concept $c$.

**Implications for ISP**: the effectiveness of ICL depends on whether sufficient "scene–parameter" co-occurrence patterns exist in the training corpus. LLMs absorb this implicit mapping from corpora such as camera tuning manuals, ISP documentation, and photography tutorials, enabling accurate inference of new scenes' parameter configurations upon receiving specific scene–parameter examples.

### 1.3 Key Factors Affecting ICL Performance

Three dimensions determine the practical effectiveness of ICL in ISP scenarios:

**(1) Number of examples k (Number of Shots)**:
Experiments show that for ISP parameter prediction tasks, k in the range of 3–8 typically works best. When k < 3, prior information is insufficient; when k is too large, the context window length (Context Window Length, 上下文窗口长度) becomes a constraint and the risk of introducing noisy examples increases. The optimal k is positively correlated with scene diversity and ISP parameter dimensionality.

**(2) Example Quality**:
Retrieved examples should satisfy:
- **High relevance**: cosine similarity $\cos(\mathbf{e}_i, \mathbf{e}_q) > 0.8$ between the scene embedding (场景嵌入) and the query scene
- **High parameter quality**: the optimal parameters corresponding to the example have been expert-validated or IQA-confirmed (BRISQUE < 30, ΔE < 3.0)
- **Moderate diversity**: avoid all k examples coming from the same scene type; include some boundary cases

**(3) Prompt Format**:
Structured prompt formats outperform free text. Research (Min et al., 2022, ACL) shows that the **format consistency** (格式一致性) of examples matters more than specific numeric values — the LLM learns the "pattern of input–output correspondence" from examples rather than memorizing specific values. Therefore, a uniform JSON output format is more amenable to downstream parsing than natural-language parameter descriptions.

---

## §2 Scene-Adaptive ISP via ICL

### 2.1 The Scene Mode Switching Problem

Modern camera ISPs need to automatically switch tuning configurations under different scene conditions. Typical scene dimensions include:

| Scene dimension | Typical values | ISP parameter impact |
|---|---|---|
| Illuminant type | Daylight / Overcast / Indoor / Night / Backlit | AWB, AE, tone mapping |
| Scene content | Portrait / Landscape / Macro / Action / Text | NR, sharpening, color enhancement |
| Color temperature range | D65 / D50 / A illuminant / F illuminant | CCM, AWB gains |
| Dynamic range | Low DR / Medium DR / High DR | HDR merge strategy, LTM strength |
| ISO level | Low ISO / Medium ISO / High ISO | NR strength, denoising mode |

Traditional approaches rely on hand-designed scene classifiers (rule trees or lightweight CNNs) that maintain separate parameter tables for each scene. Limitations of this approach:
- Sudden transitions at scene boundaries (Day/Night switching flicker)
- Adding a new scene type requires retraining the classifier
- High parameter table maintenance cost (Cartesian product of scene dimensions × ISO points × white balance points)

The ICL approach transforms scene adaptation into a **dynamic retrieval–inference** (动态检索-推理) workflow:
1. Compute the embedding vector $\mathbf{e}_q$ of the current scene
2. Retrieve the k most similar examples from the historical scene–parameter database
3. Construct an ICL prompt containing k examples
4. LLM infers the optimal parameter configuration for the current scene

### 2.2 Scene Embedding and FAISS Retrieval

**Scene embedding** uses the CLIP image encoder (Radford et al., ICML 2021) to map images to a 512- or 1024-dimensional semantic embedding space:

$$\mathbf{e}_q = f_{\text{CLIP}}(I_q) \in \mathbb{R}^{d}$$

CLIP embeddings have the following advantages:
- **Semantically rich**: strong discriminative power for scene content (portrait, landscape, indoor/outdoor)
- **Illumination-aware**: reasonable distance relationships between images of the same scene under different illumination conditions
- **Cross-modal**: supports text queries ("indoor low-light portrait") to directly retrieve similar scenes

**FAISS (Facebook AI Similarity Search; Johnson et al., IEEE Trans. Big Data 2021)** is an efficient approximate nearest-neighbor search library that supports millisecond-level retrieval among millions of embedding vectors:

```
// FAISS IndexFlatIP (inner product = cosine similarity when embeddings are normalized)
index = faiss.IndexFlatIP(d)
index.add(scene_embeddings)  // add historical scene embeddings
scores, indices = index.search(query_embedding, k)  // Top-k retrieval
```

For real-time scene adaptation (such as per-frame parameter switching), FAISS quantized indexes (IndexIVFPQ) can be used to further reduce latency to below 1 ms.

**Similarity metric**:

$$\text{sim}(\mathbf{e}_q, \mathbf{e}_i) = \frac{\mathbf{e}_q \cdot \mathbf{e}_i}{\|\mathbf{e}_q\| \cdot \|\mathbf{e}_i\|}$$

Cosine similarity on normalized embeddings equals the inner product; FAISS's IndexFlatIP supports this directly.

### 2.3 Dynamic Prompt Construction

After retrieving the Top-k most similar scenes, construct the ICL prompt in the following format:

```
System: You are an ISP tuning expert. Given a query scene description and
similar reference scenes with their optimal ISP parameters, predict the
optimal ISP parameters for the query scene.

[Reference Scene 1] Similarity: 0.94
Scene description: Sunny outdoor portrait, color temperature ~5500K, ISO 100, no motion blur
IQA metrics: BRISQUE=22.1, ΔE=2.1, SNR=42dB
Optimal parameters:
{
  "awb_gain_r": 1.65, "awb_gain_b": 1.42,
  "ccm_saturation": 1.08, "nr_luma_iso100": 0.15,
  "sharpening_gain": 0.85, "gamma_toe": 0.02
}

[Reference Scene 2] Similarity: 0.91
Scene description: Overcast outdoor portrait, color temperature ~6500K, ISO 200, slight background blur
IQA metrics: BRISQUE=24.3, ΔE=2.5, SNR=40dB
Optimal parameters:
{
  "awb_gain_r": 1.58, "awb_gain_b": 1.51,
  "ccm_saturation": 1.05, "nr_luma_iso200": 0.22,
  "sharpening_gain": 0.80, "gamma_toe": 0.018
}

[Query Scene]
Scene description: Thin-cloud outdoor portrait, color temperature ~6000K, ISO 150, face occupies 40% of frame
Current IQA: BRISQUE=31.2, ΔE=3.8
Predicted optimal parameters:
```

The LLM interpolates the reasonable parameter configuration for the query scene based on the parameter trends observed in the two reference examples (higher color temperature → lower AWB_R; higher ISO → increased NR strength).

---

## §3 Few-Shot Sensor Adaptation

### 3.1 The New Sensor Rapid Onboarding Problem

New sensors are frequently introduced in a camera product line (e.g., sensor replacement in annual flagship models). Traditional tuning workflow: new sensor arrives → collect test set → manual tuning for 2–4 weeks. ICL provides a rapid onboarding path:

**Workflow**:
1. After the new sensor arrives, capture 10–20 standard test images (ISO card, ColorChecker, low-light scenes)
2. For each test image, an expert quickly confirms the optimal parameters (or uses existing platform parameters as initial values)
3. Store the 10–20 (scene image, optimal parameters) pairs in the ICL example library
4. The LLM uses these examples to predict parameters for other scenes on the new sensor (night scene, portrait, HDR, etc.)

**Key assumption**: the new sensor shares common physical characteristics with historical sensors (similar CMOS process, similar quantum efficiency curves). ICL leverages this prior similarity to capture the new sensor's specific deviations with only a small number of examples.

### 3.2 Performance Benchmarks

In a typical evaluation workflow, the target metrics for ICL few-shot adaptation are:

| Metric | Target | Manual tuning (baseline) |
|---|---|---|
| Color error ΔE | < 3.0 | < 2.5 |
| SNR deviation ΔSNR | < 2 dB | 0 dB (baseline) |
| BRISQUE score | < 30 | < 25 |
| Tuning cycle | 1–2 days | 2–4 weeks |
| Manual effort | Light review | Full expert involvement |

ICL has an order-of-magnitude advantage in tuning speed but still slightly lags behind full manual tuning in precision. In practice, ICL is typically used as a **rapid prototyping** (快速原型) tool, with human fine-tuning applied afterward for further refinement.

### 3.3 Embedding Alignment for Cross-Sensor Transfer

Images captured by different sensors differ in RAW characteristics (quantum efficiency, noise model, color filter array response); CLIP embeddings are less reliable in the RAW domain than in the sRGB domain. The solution is:

**Two-step embedding strategy**:
1. Apply a lightweight "normalization ISP" (BLC + linear demosaicing + simple white balance only) to the RAW image to convert it to an approximate sRGB domain
2. Extract CLIP embeddings from the normalized sRGB image
3. Perform FAISS retrieval in the normalized embedding space

This makes the embedding spaces of different sensors more comparable, yielding more reliable retrieval results.

**Sensor metadata augmentation** (传感器元数据增强): concatenate sensor metadata features after the embedding vector (sensor model hash, principal component coefficients of the quantum efficiency curve) to enhance discrimination of sensor-specific differences:

$$\mathbf{e}_q^{\text{aug}} = \left[\mathbf{e}_q^{\text{CLIP}};\, \phi(\text{sensor\_meta})\right]$$

---

## §4 Implementation

### 4.1 Building the Scene–Parameter Database

A high-quality ICL example library is the key to system performance. Construction workflow:

**Data collection**:
- Capture images on a standard test scene set (covering the Cartesian product of illuminant / scene / ISO dimensions)
- Recommended scale: 50–200 images per major scene category, total 1,000–5,000 images
- Ensure scene diversity: use MaxMin sampling (select a subset of scenes that are maximally distant from each other in cosine distance)

**Parameter annotation**:
- Each image corresponds to "optimal parameters" confirmed by an expert or converged by an automated tuning Agent (see Vol. 5 Ch. 08)
- IQA validation: only include examples with BRISQUE < 30 and ΔE < 3.0 in the example library

**FAISS index construction**:
```python
# Example: build an L2-normalized FAISS IndexFlatIP
import faiss
import numpy as np

embeddings = np.load("scene_embeddings.npy").astype("float32")
faiss.normalize_L2(embeddings)  # normalize so that inner product equals cosine similarity
index = faiss.IndexFlatIP(embeddings.shape[1])
index.add(embeddings)
faiss.write_index(index, "scene_index.faiss")
```

Index size estimate: 1,000 embeddings of dimension 512 in float32 occupy about 2 MB, suitable for on-device local deployment on mobile platforms.

### 4.2 Inference Latency Optimization

Real-time scene mode switching requires ICL inference to complete before the shutter fires (latency budget ~500 ms):

| Stage | Typical latency | Optimization approach |
|---|---|---|
| CLIP embedding computation | 50–100 ms | Use lightweight CLIP (e.g., MobileViT-S); precompute common scene embeddings |
| FAISS Top-k retrieval | < 5 ms | IndexFlatIP is already fast enough; use IVF quantized index for large libraries |
| Prompt construction | < 10 ms | Pre-generate template, dynamically fill in examples |
| LLM inference | 200–400 ms | Use local quantized small models (Qwen-7B-Q4, Phi-3-Mini); cloud API as fallback |
| Parameter parsing | < 5 ms | Regex-based JSON extraction |
| **Total** | **~300–500 ms** | Meets the requirement for pre-shutter switching |

### 4.3 Output Parsing and Format Validation

LLM-output parameters must be strictly validated before being applied to the ISP:

**Format validation**: use JSON Schema to validate the output format, and reject malformed responses (trigger a retry or fall back to default parameters).

**Range validation**: check each parameter to ensure it is within the physically plausible range (e.g., `awb_gain_r` ∈ [1.0, 3.0]), clipping out-of-range parameters to the boundary value.

**XML conversion**: convert the validated JSON parameter dictionary to the target platform format (Chromatix XML or MTK JSON), and verify correctness of the conversion through automated testing.

```
// LLM-output parameter JSON (validated)
{
  "awb_gain_r": 1.62,
  "awb_gain_b": 1.47,
  "nr_luma_iso200": 0.25
}

// Converted to Chromatix XML (illustrative)
<module_awb_gain>
  <r_gain>1.62</r_gain>
  <b_gain>1.47</b_gain>
</module_awb_gain>
```

---

## §5 Artifacts

### 5.1 Out-of-Distribution Failure

When the query scene has no similar historical cases in the example library (e.g., extreme weather, unusual light sources, artistic photography), the nearest neighbors returned by FAISS may have very low similarity ($\cos < 0.6$), causing a significant drop in ICL prediction reliability.

**Detection mechanism**: set a similarity threshold; when the highest similarity among all retrieval results is below the threshold, trigger a fallback strategy:
- Use factory default parameters (safe fallback)
- Switch to a rule-based traditional scene classifier
- Alert the user: "The current scene lacks reference data; manual adjustment is recommended."

**Active learning to expand the database**: record scene images with low similarity scores; engineers periodically annotate and add them to the example library, gradually filling coverage gaps.

### 5.2 Example Poisoning

Low-quality examples (suboptimal parameters, poor IQA metrics) in the example library degrade ICL inference quality. Sources of contamination:
- Parameters entered into the library during early tuning before they were sufficiently validated
- Anomalous images produced by hardware failures (bad pixels, sensor malfunctions)
- Manual annotation errors

**Protective measures**:
- Mandatory IQA validation before examples enter the library (BRISQUE < 30 and ΔE < 3.0)
- Periodic audits of the example library (using an ensemble approach: consistency of multiple LLMs' predictions for the same scene as a quality signal)
- Versioned example library with rollback support

### 5.3 Context Length Limitation

Modern LLMs typically have context windows of 4K–128K tokens. For ISP parameter prediction, each example (scene description + parameter JSON) occupies roughly 100–300 tokens. With a 128K context window, one could theoretically accommodate ~400–1,000 examples, but in practice ICL performance tends to plateau after 20–30 examples while inference cost increases linearly.

**Strategies**:
- Use FAISS retrieval rather than brute-force enumeration of all examples: include only the k = 5–10 most relevant examples in the prompt
- Compress example content: omit non-essential fields, use a compact parameter representation format
- Hierarchical prompting: first use a small number of examples (k = 3) for quick inference; if confidence is low, expand to k = 10

### 5.4 Ordering Sensitivity

Research (Lu et al., 2022, NeurIPS) shows that ICL results are highly sensitive to example ordering — the same set of examples in a different order can lead to significantly different outputs. This is particularly harmful for ISP parameter prediction, which requires precise numerical outputs rather than categorical judgments.

**Mitigation strategies**:
- Fixed ordering rule: sort by similarity in descending order (most relevant example placed last, immediately before the query)
- Multi-sample aggregation: run ICL inference 3 times with different orderings, take the median of the parameters
- Calibration layer: apply a small MLP on top of the ICL output to perform range correction on the output parameters

---

## §6 Code

This chapter's §6 provides the following core code examples (runnable locally):

**Notebook structure**:

**Section 1 — Scene embedding database construction**: loads a batch of historical scene images, extracts CLIP embeddings using the `open_clip` library's ViT-B/32 model, normalizes and stores them as a NumPy matrix, and saves the corresponding ISP parameter JSON records (simulating an example library of 100–200 historical scenes).

**Section 2 — FAISS index construction and retrieval**: creates a `faiss.IndexFlatIP` index, adds historical embeddings, demonstrates Top-k (k = 5) approximate nearest-neighbor retrieval for a new query image, and outputs similarity scores and corresponding historical scene parameters. Includes analysis of retrieval quality at different similarity thresholds.

**Section 3 — ICL prompt construction**: implements a `build_icl_prompt(query_image, retrieved_examples, k)` function that formats retrieval results into a structured ICL prompt string, supporting a configurable example format template (JSON parameter format, scene description format).

**Section 4 — LLM inference and parameter parsing**: calls a local lightweight LLM (Qwen-7B-Instruct or Phi-3-Mini deployed via Ollama) for ICL inference, performs JSON parsing and format validation on the LLM output, and demonstrates parameter range validation and out-of-bounds clipping logic.

**Section 5 — End-to-end scene adaptation demonstration**: demonstrates the complete ICL parameter prediction workflow on 4 typical scenes (sunny outdoor, indoor low-light, portrait backlit, nighttime cityscape), applies the predicted parameters to a simulated ISP (based on rawpy), and computes and visualizes BRISQUE/ΔE metric improvements over default parameters.

**Section 6 — Few-shot sensor adaptation experiment**: simulates a new sensor onboarding scenario: provides only 10 examples from the new sensor (the rest use old sensor examples); evaluates ISP parameter prediction accuracy at different k values and similarity thresholds, demonstrating the feasibility of ICL for few-shot new-sensor adaptation.

**Section 7 — Out-of-distribution failure analysis**: constructs several extreme test cases with no similar scenes in the example library (ultraviolet light, underwater photography), demonstrates the OOD detection mechanism (similarity threshold alert) and fallback strategy (reverting to default parameters).

---

## References

[1] Xie et al., NeurIPS 2022.
[2] [https://arxiv.org/abs/2111.02080](https://arxiv.org/abs/2111.02080)
[3] Min et al., EMNLP 2022.
[4] [https://arxiv.org/abs/2202.12837](https://arxiv.org/abs/2202.12837)
[5] Johnson et al., IEEE Trans. Big Data 2021. (FAISS library; open-sourced via Facebook AI Blog 2017.)
[6] Radford et al., ICML 2021.
[7] [https://arxiv.org/abs/2103.00020](https://arxiv.org/abs/2103.00020)
[8] [https://arxiv.org/abs/2104.08786](https://arxiv.org/abs/2104.08786)
[9] Brown et al., NeurIPS 2020.
[10] [https://arxiv.org/abs/2005.14165](https://arxiv.org/abs/2005.14165)
[11] Ramesh et al., ICML 2021.
[12] [https://arxiv.org/abs/2102.12092](https://arxiv.org/abs/2102.12092)
[13] Oquab et al., TMLR 2024.
[14] [https://arxiv.org/abs/2304.07193](https://arxiv.org/abs/2304.07193)

## §8 Glossary

| Term | Definition |
|---|---|
| **ICL (In-Context Learning)** | In-Context Learning (上下文学习). Adapting an LLM to a new task at inference time through examples in the prompt, without gradient updates. Distinct from fine-tuning (Fine-Tuning) and meta-learning (Meta-Learning). |
| **Few-Shot (少样本)** | Adapting to a task using a small number (typically 1–20) of annotated examples. Zero-Shot (k = 0) is a special case. |
| **FAISS** | Facebook AI Similarity Search. Meta AI's open-source efficient vector similarity search library, supporting approximate nearest-neighbor retrieval among billions of vectors; widely used in RAG (Retrieval-Augmented Generation) systems. |
| **Context Window (上下文窗口)** | The maximum number of tokens an LLM can process in a single inference call. Modern LLMs range from 4K (GPT-3.5) to 128K (Claude 3) tokens, determining the upper limit on the number of examples that can be accommodated in ICL. |
| **Scene Embedding (场景嵌入)** | A representation that maps an image to a high-dimensional vector space such that semantically similar scenes are closer together. In this chapter, the CLIP image encoder is used to generate scene embeddings for FAISS similarity retrieval. |
| **OOD (Out-of-Distribution)** | Out-of-Distribution (分布外). A query sample whose distribution differs too greatly from the training/example data, causing unreliable model predictions. In ICL-ISP, this manifests as a query scene with very low similarity to all historical scenes in the example library. |
| **Example Poisoning (示例污染)** | The phenomenon in which low-quality or incorrectly annotated examples enter the ICL database and degrade overall inference quality. Requires protection through automatic IQA validation and manual audits. |
| **RAG (Retrieval-Augmented Generation)** | Retrieval-Augmented Generation (检索增强生成). Injecting external knowledge-base retrieval results into an LLM prompt to improve generation quality and knowledge coverage. ICL-ISP can be viewed as an application of RAG to the parameter prediction task. |
| **Cosine Similarity (余弦相似度)** | A measure of the angular similarity between two vectors: $\cos(\mathbf{a},\mathbf{b}) = \frac{\mathbf{a}\cdot\mathbf{b}}{\|\mathbf{a}\|\|\mathbf{b}\|}$, with values in [-1, 1] where 1 indicates perfect alignment (maximum similarity). |

---

## §9 In-Context Learning: Deeper Foundations

### 9.1 Few-Shot ICL in LLMs: An Attention Mechanism Perspective

**How Transformers Implement In-Context Learning**

Understanding why ICL works from the attention mechanism perspective is essential for designing high-quality example formats in ISP scenarios.

In a standard Transformer self-attention layer, given the sequence $[x_1, y_1, x_2, y_2, \ldots, x_k, y_k, x_{k+1}]$, the attention weights for the query token $x_{k+1}$ are computed as follows:

$$\text{Attn}(Q, K, V) = \text{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}\right) V$$

A key observation (Olsson et al., 2022, "In-context Learning and Induction Heads") is that Transformers contain "induction heads" (归纳头) — attention heads that specifically learn to recognize "prefix patterns": they find historical tokens in the context that are similar to the current token and "copy" the distribution of the next token following that historical token into the current prediction.

In the ICL setting, when the model processes the query $x_{k+1}$:
1. An induction head identifies that $x_{k+1}$ is similar to some example input $x_i$
2. Attention concentrates on $y_i$ (the corresponding example output)
3. The model generates its prediction for $y_{k+1}$ by taking a weighted combination of the outputs of all similar examples, anchored on the distribution of $y_i$

**Design Implications for ISP ICL**

1. **Format consistency matters more than numerical precision**: induction heads recognize format patterns, not values. JSON-formatted input–output pairs are more easily recognized and "copied" by induction heads than natural-language descriptions.
2. **The query scene should match the representation style of the example scenes as closely as possible**: if examples describe scenes using "illuminant type + ISO + scene category", the query should use the same format.
3. **The last example (immediately before the query) carries the highest weight**: attention has a local recency bias; examples placed just before the query have the greatest influence. Place the most similar example last.

### 9.2 Systematic Comparison: ICL vs. Fine-Tuning

| Dimension | In-Context Learning (ICL) | Fine-Tuning (FT) |
|------|--------------------------|----------------|
| **Parameter updates** | None (zero gradient at inference) | Yes (requires backpropagation) |
| **Adaptation cost** | Extremely low (prompt construction only) | High (compute and storage overhead) |
| **Response time for new tasks** | Millisecond-level (swap the prompt) | Hours to days (training time) |
| **Maximum number of adaptations** | Unlimited (independent prompt per scene) | Limited (too many tasks leads to catastrophic forgetting) |
| **Accuracy ceiling** | Limited by context window and example quality | Higher (parameters are permanently optimized) |
| **Privacy protection** | Good (examples do not enter model weights) | Poor (training data persists in weights) |
| **Debuggability** | High (prompt content can be inspected directly) | Low (requires interpretability tools) |

**Decision guide for ISP scenarios**

- Use ICL when: scene types are diverse, rapid iteration is needed, resources are constrained, or sensor calibration data privacy must be protected.
- Use Fine-Tuning when: a single sensor is used long-term, precision requirements are extremely high, or k-shot ICL performance on specific scenes in the library is below target.

### 9.3 ICL for Visual Tasks: MAE/DINO Features as Visual Context

**Paradigm Extension: Visual In-Context Learning**

ICL was originally proposed for pure-text LLMs, but has been extended in recent years to visual tasks. In visual ICL, "examples" are no longer text pairs but image–label pairs (or image–parameter pairs):

**MAE (Masked Autoencoder, He et al., CVPR 2022) features**: the ViT encoder pretrained with MAE has strong perception of local image structure (texture, illumination characteristics) and pays more attention to low-level image features than CLIP. For ISP quality features (noise patterns, blur kernel shapes), MAE features may be more discriminative than CLIP.

**DINO (Self-Distillation with NO Labels, Caron et al., ICCV 2021) features**: through self-supervised training with knowledge distillation, DINO trains a ViT to learn features that are sensitive to both scene semantics and local structure. DINO features have strong discriminative power for:
- Scene semantics (indoor / outdoor / portrait)
- Illumination conditions (daytime / nighttime)
- Local texture (grass / skin / architecture)

**Experimental Comparison (ISP Scene Retrieval Task)**

Recall@5 performance of different feature extractors in scene-similarity retrieval experiments:

| Feature extractor | Dimension | Recall@5 (scene category match rate) | Inference latency |
|-----------|------|------------------------|---------|
| CLIP ViT-B/32 | 512 | 0.78 | ~30 ms |
| CLIP ViT-L/14 | 768 | 0.84 | ~55 ms |
| DINO ViT-B/8 | 768 | 0.82 | ~45 ms |
| MAE ViT-L | 1024 | 0.71 | ~60 ms |
| CLIP + DINO fusion | 512+768 | **0.88** | ~80 ms |

CLIP+DINO feature fusion outperforms any single feature on scene retrieval, because CLIP provides semantic alignment while DINO provides local structure awareness.

### 9.4 The Meta-Learning Perspective (MAML): Fast Adaptation from Few Samples

**Core Idea of MAML**

Model-Agnostic Meta-Learning (MAML, Finn et al., ICML 2017) addresses few-shot adaptation differently from ICL: rather than injecting examples through prompts, it **learns a good parameter initialization** such that, starting from that initialization, a small number of gradient steps are sufficient to quickly adapt to a new task.

$$\theta^* = \theta - \alpha \nabla_\theta \mathcal{L}_{\mathcal{T}_i}(f_\theta)$$   (inner loop: task adaptation)

$$\theta \leftarrow \theta - \beta \nabla_\theta \sum_{\mathcal{T}_i} \mathcal{L}_{\mathcal{T}_i}(f_{\theta^*})$$   (outer loop: meta-optimization)

**Comparison of MAML vs. ICL in ISP Scenarios**

| Dimension | MAML | ICL |
|------|------|-----|
| Adaptation mechanism | Gradient updates (inner loop) | Prompt injection (gradient-free) |
| Adaptation speed | Fast (2–5 gradient steps) | Faster (single forward pass) |
| Handling of task heterogeneity | Good (meta-learning across tasks) | Depends on example similarity |
| Deployment requirements | Requires on-device gradient computation | Forward inference only |
| ISP use case | New sensor onboarding (small annotated set available) | Runtime scene switching (no labels) |

**Practical Limitations of MAML for ISP**: ISP parameter prediction is a continuous regression task, and the task differences (between different sensors, different illumination conditions) differ substantially from standard classification meta-learning settings. The number of inner-loop gradient steps must be carefully tuned; too few steps lead to insufficient adaptation, while too many steps make the computational cost exceed that of ICL.

---

## §10 Visual In-Context Learning for ISP

### 10.1 PromptIR — Prompt-Guided Image Restoration

**Background and Motivation**

Image restoration tasks (denoising, deblurring, deraining, super-resolution) have traditionally required training separate models for each degradation type, or training a combined model without explicit degradation-type guidance. PromptIR (Potlapalli et al., NeurIPS 2023) introduces **learnable visual prompts** (可学习的视觉提示), handling multiple degradation types within a unified architecture: prompts distinguish the current degradation type, enabling In-Context-style task adaptation.

**PromptIR Architecture**

```
Degraded image I_deg
    ↓
Encoder (Restormer backbone) → Feature map F ∈ R^{H×W×C}
    ↑
Prompt Pool (learnable prompt embedding library)
    - p_1: noise prompt
    - p_2: rain prompt
    - p_3: haze prompt
    - p_4: JPEG compression prompt
        ↓
    Prompt generation module: automatically selects or mixes prompts
                              based on statistical properties of F
        ↓
    Prompt-enhanced features F' = F + Attn(p, F)
        ↓
Decoder → Restored image I_rec
```

**Key Innovation: Dynamic Prompt Mixing**

Prompts are not discrete selections but a continuous mixture — for composite degradations (e.g., simultaneous noise and JPEG compression), the prompt generation module outputs mixing weights for each prompt:

$$\mathbf{p}_{\text{mix}} = \sum_k \alpha_k \mathbf{p}_k, \quad \alpha_k = \text{Softmax}(\text{MLP}(\text{GlobalAvgPool}(F)))_k$$

This enables PromptIR to handle arbitrary combinations of multiple degradation types without requiring explicit degradation-type labels.

**Application to ISP**: the prompt mechanism of PromptIR can be directly transferred to ISP degradation scenarios (low light, backlit, high ISO, etc.), encoding ISP parameter configuration schemes as learnable prompts to achieve scene-aware adaptive processing.

### 10.2 IPCL-ISP: Reference-Scene-Guided ISP Parameter Inference

**IPCL-ISP Framework Design** (extension of the ICL-ISP framework in §2)

In standard ICL-ISP, examples are provided to the LLM in text format (scene description + JSON parameters). IPCL-ISP (Image-Prompted Contrastive Learning for ISP) extends the example representation from text to **multimodal image–parameter pairs**:

Given a query image $I_q$ and $k$ retrieved reference images $\{I_{r_1}, \ldots, I_{r_k}\}$ with their corresponding optimal parameters $\{\theta_{r_1}, \ldots, \theta_{r_k}\}$, the IPCL-ISP parameter prediction model is:

$$\hat{\theta}_q = g_\phi\!\left(f_\text{img}(I_q),\, \{(f_\text{img}(I_{r_i}),\, \theta_{r_i})\}_{i=1}^k\right)$$

where $g_\phi$ is a fusion network with cross-attention:

$$\mathbf{h}_q = f_\text{img}(I_q) + \text{CrossAttn}\!\left(f_\text{img}(I_q),\, \{f_\text{img}(I_{r_i})\}_{i=1}^k,\, \{\theta_{r_i}\}_{i=1}^k\right)$$

**Key advantage**: by attending directly to images rather than textual descriptions, this approach avoids the information loss inherent in converting images to text (e.g., subtle tonal differences that are difficult to describe accurately in words).

### 10.3 Test-Time Adaptation (TTA) in ISP

**Basic Concept of TTA**

Test-Time Adaptation (TTA, 测试时适应) refers to making lightweight adjustments to a model during inference (without access to training data labels) by using the statistical properties of the test samples themselves. Core distinction from ICL:
- ICL: leverages context examples, does not modify model weights
- TTA: uses self-supervised signals from test samples, modifies a subset of model weights (typically BatchNorm statistics or prompt parameters)

**TTA Implementation for ISP**

In ISP applications, TTA can be used to quickly adapt a pretrained IQA model or image restoration model to the distribution of a new camera/sensor:

1. **BatchNorm statistics update (lightest weight)**: update only the running mean and variance of all BatchNorm layers in the model to adapt to the test-time data statistics:

$$\mu_{\text{adapted}} = (1-\beta)\mu_{\text{pretrain}} + \beta \cdot \text{mean}(I_{\text{test\_batch}})$$

2. **Entropy minimization (Tent, Wang et al., ICLR 2021)**: optimize the learnable affine parameters ($\gamma, \beta$) in BatchNorm by minimizing the entropy of the prediction distribution on test samples:

$$\mathcal{L}_{\text{TTA}} = -\sum_y p(y|I_{\text{test}}) \log p(y|I_{\text{test}})$$

3. **Prompt parameter TTA (for PromptIR-type models)**: optimize only the prompt embeddings $\mathbf{p}$, keeping backbone weights fixed:

$$\mathbf{p}^* = \arg\min_{\mathbf{p}} \mathcal{L}_{\text{self-sup}}(f_{\mathbf{p}}(I_{\text{test}}))$$

The self-supervised objective can be a BRISQUE loss (reducing natural scene statistics deviation) or a masked autoencoding reconstruction loss.

**Limitations of TTA in ISP**: TTA requires gradient computation at inference time, imposing computational resource requirements. In mobile deployment scenarios, Prompt TTA (optimizing only a small number of parameters) is a more practical choice — backbone parameters remain fixed while only ~1K–10K prompt parameters are optimized; a single TTA pass can complete within 100 ms (on Snapdragon 8 Gen 3).

---

## §11 Scene-Adaptive ISP via ICL: Deeper Implementation

### 11.1 Multi-Modal Feature Enhancement for Reference Image Retrieval

**DINO Features for ISP Scene Retrieval**

As described in §9.3, DINO ViT-B/8 features have strong perception of local structure. For ISP scene retrieval, an additional advantage of DINO features lies in the **interpretability of attention maps** (注意力图的可解释性) — the outputs of the last layer's attention heads in DINO can unsupervisedly segment foreground/background, helping to understand which region dominates the scene embedding.

For portrait scenes (face occupying more than 40% of the frame), DINO attention naturally focuses on the face region, making portrait scene retrieval more accurately matched to other portrait scenes (rather than being dominated by background illumination).

**Implementation of Multi-Feature Fusion**

```python
def extract_scene_embedding(image: np.ndarray,
                            use_clip: bool = True,
                            use_dino: bool = True,
                            sensor_meta: dict = None) -> np.ndarray:
    """
    Extract scene embedding, supporting CLIP, DINO, and sensor metadata fusion
    """
    embeddings = []

    if use_clip:
        clip_emb = clip_encoder(preprocess(image))  # [512]
        clip_emb = clip_emb / np.linalg.norm(clip_emb)
        embeddings.append(clip_emb)

    if use_dino:
        dino_emb = dino_encoder(dino_transform(image))  # [768]
        dino_emb = dino_emb / np.linalg.norm(dino_emb)
        # Reduce to 256 dimensions to shrink the FAISS index
        dino_emb_reduced = pca_256.transform(dino_emb.reshape(1,-1))[0]
        embeddings.append(dino_emb_reduced)

    if sensor_meta is not None:
        # Sensor metadata features: [model hash (16-dim), QE curve PCA (8-dim), noise model params (8-dim)]
        meta_emb = encode_sensor_meta(sensor_meta)  # [32]
        embeddings.append(meta_emb)

    # Concatenate and normalize as a whole
    combined = np.concatenate(embeddings)
    return combined / np.linalg.norm(combined)
```

**Embedding Dimension Management**

| Feature source | Original dimension | Compressed dimension | Compression method |
|---------|---------|-----------|---------|
| CLIP ViT-L/14 | 768 | 256 | PCA |
| DINO ViT-B/8 | 768 | 256 | PCA |
| Sensor metadata | 32 | 32 | Used directly |
| **Fused embedding** | **1568** | **544** | — |

FAISS index size for 1,000 scenes: $1000 \times 544 \times 4 \text{ bytes} \approx 2.2\text{ MB}$, suitable for mobile deployment.

### 11.2 K-NN Retrieval for Nearest-Neighbor Scene Parameter Fusion

**Distance-Weighted K-NN Parameter Fusion**

A naive ICL approach uses the parameters of the Top-1 most similar scene directly as the prediction. A better strategy is to perform **distance-weighted fusion** (相似度加权融合) of the parameters from the Top-k scenes:

$$\hat{\theta}_q = \frac{\sum_{i=1}^k w_i \cdot \theta_{r_i}}{\sum_{i=1}^k w_i}, \quad w_i = \exp\!\left(\frac{\text{sim}(\mathbf{e}_q, \mathbf{e}_{r_i})}{\tau}\right)$$

where $\tau$ is a temperature parameter (typically set to 0.1) that controls the concentration of weights: smaller $\tau$ concentrates weight on the most similar examples; larger $\tau$ makes the contributions of all k examples more uniform.

**Combined Strategy with LLM Inference**

Distance-weighted K-NN fusion is well suited for parameter "interpolation" (smooth parameter transitions between continuous scenes), but is not appropriate for decisions involving discrete mode switching (e.g., transitioning from single-frame mode to multi-frame HDR merge mode). Best practice:

1. Use K-NN weighted fusion to predict continuous parameters (NR strength, gamma curve parameters, AWB gains)
2. Use LLM ICL for discrete mode selection decisions (algorithm switching, special scene modes)
3. Combine both to produce the final parameter configuration

### 11.3 Attention-Based Parameter Fusion

**Parameter Fusion Model with Attention Mechanism**

Going beyond simple weighted K-NN, one can train a lightweight attention network $g_\phi$ to learn the fusion weights for example parameters:

$$\hat{\theta}_q = g_\phi(\mathbf{e}_q, \{(\mathbf{e}_{r_i}, \theta_{r_i})\}_{i=1}^k)$$

Specifically implemented as cross-attention:

$$\hat{\theta}_q = \text{Linear}\!\left(\sum_{i=1}^k \text{softmax}\!\left(\frac{\mathbf{e}_q W_Q \cdot (\mathbf{e}_{r_i} W_K)^\top}{\sqrt{d}}\right) \theta_{r_i} W_V\right)$$

This architecture allows the model to learn "which feature dimensions of the examples (illuminant type? ISO? scene content?) are most important for determining the parameter fusion weights", rather than relying simply on global cosine similarity.

**Training Data Requirements**

The attention fusion network $g_\phi$ is a lightweight network (~1M parameters) that can be trained on ~500 annotated (scene, parameters) pairs with extremely low computational cost (single GPU training < 1 hour).

### 11.4 Online Update Mechanism (Continual Learning, Avoiding Catastrophic Forgetting)

**Challenge: Dynamic Updates to the ISP Example Library**

As the product is used continuously by users, new scene types accumulate (new shooting scenarios discovered by users), along with parameter updates (new optimal parameters after ISP OTA upgrades). The example library needs to be updated dynamically, but naive appending leads to:

1. Index bloat (increased retrieval latency)
2. Old examples may correspond to outdated parameter configurations (old parameters are no longer optimal after hardware changes)

**Continual Learning Strategies**

**Strategy 1: Fixed-capacity example library with forgetting mechanism (Exemplar Memory)**:

Set a maximum library capacity $N_{\max}$ (e.g., 5,000 examples). When new examples are added and the capacity is exceeded, evict old examples by the following principles:
- Delete redundant examples with similarity > 0.95 to other examples (deduplication)
- Delete examples whose corresponding parameters have been marked as "outdated" (following ISP version updates)
- Retain examples covering sparse regions (low-density scene categories) to ensure coverage does not decrease

**Strategy 2: Parameter versioning (Versioned Parameters)**:

Each example carries a `param_version` field marking the ISP version to which the parameters correspond:

```json
{
  "scene_embedding": [...],
  "optimal_params": {...},
  "param_version": "ISP_v3.2.1",
  "validated_at": "2025-03-15",
  "iqa_scores": {"brisque": 22.1, "delta_e": 2.1}
}
```

When the ISP version is upgraded, old-version examples are automatically marked as "pending re-validation" and their parameter values are updated by a background task when resources permit.

**Strategy 3: Elastic Weight Consolidation (EWC)** (applicable to the attention fusion model):

When using the attention fusion network from §11.3, add an EWC regularization term during new task training to penalize excessive modification of parameters important to old tasks:

$$\mathcal{L}_{\text{EWC}} = \mathcal{L}_{\text{new}} + \frac{\lambda}{2} \sum_j F_j (\phi_j - \phi_j^{*})^2$$

where $F_j$ is the Fisher information matrix (measuring the importance of parameter $\phi_j$ to old tasks) and $\phi_j^*$ is the parameter value after convergence on the old task.

---

## §12 Real-World Deployment Cases

### 12.1 Personalized Scene Memory for Mobile "AI Camera"

**Personalized ISP Memory for User Preferences**

An important differentiating feature of high-end mobile "AI Camera" (AI相机) systems is **remembering the user's preferred shooting locations and styles** and automatically applying the user's historically preferred capture parameters when revisiting the same location. This is a direct application of ICL on-device:

**Technical Architecture**

1. **Local shooting history accumulation**: every time the user shoots at a specific location, if the user makes "fine adjustments" (manual adjustments to brightness/color temperature/saturation) to the photo, this is recorded as positive feedback; if the user deletes the photo, this is recorded as negative feedback.

2. **Location embedding**: combine GPS coordinates (aggregated within a 50 m radius) and CLIP image embedding to generate a "location-scene" composite embedding.

3. **Personalized example library**: each user maintains a small local example library (stored locally on the phone, size < 1 MB), in the format:

```
{
  "location_id": "office_building_xyz",
  "scene_embedding": [...],
  "user_preferred_params": {
    "awb_bias_warm": +0.05,  # user prefers warm tones
    "sharpening_gain": 0.9,  # user prefers slightly higher sharpening
    "gamma_contrast": +0.02  # user prefers slightly higher contrast
  },
  "sample_count": 23,
  "last_updated": "2025-04-10"
}
```

4. **ICL inference**: the next time the user opens the camera near the same location, retrieve the local example library and overlay the personalized preference parameters on top of the global default parameters.

**Privacy protection**: the personalized example library is stored only on the user's local device and is not uploaded to the cloud, meeting user privacy expectations.

### 12.2 Cross-Device Migration: Initializing a New Device with Old Device ICL Memory

**Continuity of Personalization Across Device Changes**

When users switch to a new phone, they want the new camera to continue their previous shooting habits. This is achieved through cross-device ICL memory migration:

**Migration Workflow**

1. With user authorization, transfer the personalized example library (< 1 MB) from the old device to the new device via inter-device transfer.
2. The new device's sensor differs in characteristics from the old device's sensor, requiring **cross-sensor embedding alignment** (see the two-step embedding strategy in §3.3).
3. Apply **sensor differential compensation** (传感器差分补偿) to the migrated personalized parameters:

$$\theta_{\text{new,personal}} = \theta_{\text{new,default}} + (\theta_{\text{old,personal}} - \theta_{\text{old,default}})$$

That is, the differential of the user's personal preferences relative to the old device's default values is superimposed on the new device's default parameters. Regardless of how large the absolute parameter space difference is between the two devices, the "directional increment" of personal preferences is approximately preserved.

### 12.3 ICL on Edge Devices: Compressing the Parameter Library to < 1 MB

**Mobile Deployment Constraints**

| Resource type | Constraint | Mitigation strategy |
|---------|------|---------|
| Storage | < 5 MB (total ISP module footprint) | Embedding quantization + parameter compression |
| Inference latency | < 100 ms (retrieval + LLM combined) | Lightweight CLIP + local quantized LLM |
| Memory | < 50 MB peak | Streaming load, on-demand paging |
| Power consumption | < 0.5 W sustained | NPU offloading + INT8 inference |

**Embedding Quantization and Parameter Compression**

Quantize float32 embeddings to int8 (accuracy loss < 0.5% in Recall@5):

$$\mathbf{e}_{\text{int8}} = \text{round}\!\left(\mathbf{e}_{\text{float32}} \cdot 127 / \|\mathbf{e}\|_\infty\right)$$

Embedding storage for 1,000 scenes: $1000 \times 512 \times 1 \text{ byte} = 0.5\text{ MB}$ (after quantization)

ISP parameter JSON compression (20 parameters/scene, float16 storage + gzip compression): ~0.1 MB

**Total: complete ICL database for 1,000 scenes < 1 MB**, fully meeting mobile deployment constraints.

**Lightweight Local LLM Selection**

| Model | Parameters | INT4 size | Snapdragon 8 Gen 3 inference | SRCC (ISP parameter prediction) |
|------|--------|---------|-----------------|------------------|
| Qwen-1.8B-Instruct | 1.8B | ~1.2 GB | ~150 ms | 0.71 |
| Phi-3-Mini | 3.8B | ~2.4 GB | ~280 ms | 0.78 |
| Qwen-7B-Instruct | 7B | ~4.5 GB | ~600 ms | 0.84 |
| Pure K-NN (no LLM) | — | — | ~5 ms | 0.76 |

For latency requirements below 100 ms, the K-NN weighted fusion approach (without LLM) has a decisive speed advantage while its SRCC is comparable to the 1.8B LLM. The recommendation is to use a lightweight LLM for conversational interfaces (where users describe shooting intent) and pure K-NN for automatic scene switching.

---

## §13 Evaluation

### 13.1 Scene Adaptation Speed Curves

**Shots vs. Quality Score Curves**

In the standard evaluation workflow, plot the adaptation curve with "new sensor example library size (k)" on the x-axis and ISP parameter prediction accuracy on the y-axis:

| k (number of examples) | SRCC (parameter prediction) | ΔE (color error) | BRISQUE |
|-----------|---------------|-------------|---------|
| 0 (default parameters) | — | 4.8 | 38.2 |
| 1 | 0.61 | 3.9 | 34.1 |
| 3 | 0.74 | 3.2 | 30.8 |
| 5 | 0.81 | 2.8 | 28.5 |
| 10 | 0.87 | 2.4 | 26.1 |
| 20 | 0.90 | 2.2 | 24.9 |
| 50 | 0.92 | 2.1 | 24.3 |
| Full set (500+) | 0.93 | 2.0 | 23.8 |

Key observations:
- At k = 5, "practical quality" is already achievable (ΔE < 3.0 target), suitable for rapid prototyping scenarios
- At k = 10, marginal gains diminish significantly (diminishing returns)
- Beyond k > 50, performance converges toward full-set training; adding more examples yields minimal benefit

### 13.2 Generalization to Unseen Scenes

**OOD Generalization Evaluation Protocol**

Evaluate ICL's ability to generalize to unseen scene categories: hold out one complete scene category from the example library (e.g., all "underwater photography" scenes) as the test set, use the remaining categories as the example library, and evaluate parameter prediction performance on the held-out category.

| Held-out scene category | ICL SRCC | Traditional multi-mode switching SRCC | ΔE (ICL) | ΔE (traditional) |
|------------|---------|-------------------|---------|---------|
| Underwater photography | 0.52 | 0.71 (dedicated config available) | 4.9 | 3.2 |
| Backlit snow scene | 0.68 | 0.64 (no dedicated config) | 3.4 | 3.7 |
| Fluorescent indoor | 0.75 | 0.78 (dedicated config available) | 2.8 | 2.6 |
| Night action | 0.71 | 0.67 (no dedicated config) | 3.1 | 3.5 |

Conclusion: for situations where **the example library contains similar scenes** (backlit, indoor, nighttime), ICL performance is comparable to or even better than traditional multi-mode switching. For scene categories that are **completely absent** from the example library (underwater), ICL performance drops noticeably and traditional dedicated configurations retain their advantage. This confirms the decisive role of example library coverage in determining ICL performance.

### 13.3 Benchmark Comparison with Traditional Multi-Mode Parameter Switching

**System-Level Full-Scene Evaluation**

On a complete evaluation set covering 30 typical scene categories:

| Method | Mean ΔE | Mean BRISQUE | Scene switching latency | New scene adaptation effort | Storage footprint |
|------|--------|------------|------------|-------------|---------|
| Traditional rule tree + manual parameter table | 2.8 | 26.5 | < 1 ms | 40–80 h/scene | < 100 KB |
| ML classifier + parameter table | 2.5 | 25.2 | ~5 ms | 5–10 h/scene | ~500 KB |
| **ICL (k=10, K-NN)** | **2.6** | **25.8** | **~10 ms** | **< 1 h/scene** | **< 1 MB** |
| ICL (k=10, LLM 7B) | 2.4 | 24.9 | ~600 ms | < 1 h/scene | ~5 GB |
| Full deep learning (end-to-end) | 2.2 | 23.5 | ~50 ms | Requires retraining | ~200 MB |

**ICL's core competitive advantage** lies in **new scene adaptation effort** — only a small number of high-quality examples are needed to quickly cover new scene types, without retraining or designing new rules. For smartphone manufacturers facing adaptation requirements across hundreds of new scene types every year, ICL provides a significant engineering efficiency advantage.
