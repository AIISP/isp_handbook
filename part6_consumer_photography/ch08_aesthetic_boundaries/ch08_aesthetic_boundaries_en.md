# Part 6, Chapter 08: The Aesthetic Boundaries of Computational Photography — From Standardized Image Quality to a Personalized Imaging Ecosystem

> The author's experience is limited; the content here represents personal understanding and carries strong subjectivity. **Experts, photographers, product managers, and users from all domains are warmly invited to improve this document** via Issues or Pull Requests.

> **Position:** Starting from the history of photographic aesthetics, this chapter analyzes divergent aesthetic schools, examines the tension between "standardization" and "personalization" in current computational photography, and proposes a community-driven parameter template ecosystem as the path forward.
>
> **Audience:** ISP algorithm engineers, product managers, imaging ecosystem designers

---

## §1 The Plurality of Photographic Aesthetics: No Single Correct Answer

### 1.1 Aesthetic Schools in the History of Photography

Photography has never had a universally accepted "correct aesthetic" since its invention. Photographers across different eras and cultural backgrounds have developed radically different visual languages, expressed across every dimension — light and shadow, color, contrast, grain, and sharpness. Understanding this history is a prerequisite for understanding the design philosophy divergences in ISP today.

#### 1.1.1 Straight Photography and the Zone System (f/64 Group, 1932)

In 1932, Ansel Adams, Edward Weston, Imogen Cunningham, and others formed the "f/64 Group" on the American West Coast, in opposition to the then-popular "Pictorialism" (deliberately soft-focus images imitating oil paintings). Their principles were:

- **Extreme sharpness**: use f/64 small apertures for maximum depth of field — sharp from near to far
- **Straight Photography**: prints without post-processing composites, truthfully recording natural detail
- **Zone System**: Adams divided scene luminance from Zone 0 (pure black, no detail) to Zone X (pure white, no detail) into 11 zones, and through precise control of exposure and darkroom development, placed each zone within its intended tonal range

The core philosophy of the Zone System is: **visualize the final print at the moment of capture** (Expose for the shadows, develop for the highlights), rather than "shoot now, fix in post." This has an intrinsic parallel to **Local Tone Mapping** and **multi-frame HDR merging** in today's ISP — both attempt to solve the dynamic range compression problem, only the tools have changed from darkroom chemistry to digital algorithms.

#### 1.1.2 The Decisive Moment: The Cartier-Bresson School (1952)

Henri Cartier-Bresson published *The Decisive Moment* (*Images à la Sauvette*) in 1952, establishing a completely different photographic philosophy:

- **High contrast**: strong separation of light and shadow; shadows can be completely black — detail need not be preserved
- **Black-and-white tonality**: color is a distraction; geometry and light are the core
- **No pursuit of technical perfection**: slight motion blur and grain are acceptable, even part of the emotional content
- **Instantaneity**: the moment passes and cannot be reshot

This aesthetic implies that **clipped highlights and crushed blacks are acceptable — even intentional**. But today's flagship smartphone ISP relentlessly recovers highlights and lifts shadows in every photograph — technically "better," yet in Cartier-Bresson's aesthetic framework precisely what destroys the dramatic tension.

#### 1.1.3 The Color Philosophy of Film Aesthetics: Kodak vs. Fujifilm

In the latter half of the twentieth century, two major film manufacturers established two starkly different color philosophies through commercial competition, profoundly shaping the aesthetics of digital photography today:

| Dimension | Kodak | Fujifilm |
|-----------|-------|----------|
| Skin tone rendering | Warm orange, flattering to Caucasian skin tones, portraits feel "alive" | Cool, with green-yellow cast, flattering to Asian skin tones, clean and luminous |
| Color saturation | Neutral to slightly low, high latitude, suitable for post adjustment | Medium-high saturation, especially vivid greens and blues |
| Contrast | Soft, shadows retain abundant detail | Higher; blacks are deeper, contrast is stronger |
| Grain texture | Coarse grain, painterly feel | Fine grain, delicate gradation, more regular grain |
| Representative products | Portra 400 (portrait standard), Ektar 100 (landscape), Gold 200 (everyday) | Provia 100F (standard landscape), Velvia 50 (vivid landscape), 400H (soft portrait) |

Commercially, both companies sold not just photosensitive emulsion — they sold **a complete definition of what a "good photograph" looks like**. Kodak's warm palette helped Hollywood establish a "cinematic" skin tone standard; Fujifilm's cool, clean rendering became a powerful "Japanese aesthetic" label in Japanese photography magazines.

In the digital era, Fujifilm extended this legacy by introducing **Film Simulation**, converting the color characteristics of classic film stocks into JPEG in-camera style options: Velvia (hyper-saturated landscape), Provia/Standard (balanced general), Astia/Soft (gentle portrait), Classic Chrome (faded documentary), Eterna (cinematic, low contrast, low saturation), Acros (dedicated black-and-white with grain texture). This system has created extremely strong brand loyalty among photography enthusiasts. Community websites such as Fuji X Weekly specifically document and share "Film Simulation Recipes" — users combine in-camera parameters to reproduce specific film effects. This community behavior has been self-organizing in the enthusiast camera space for years.

The essence of this strategy is: **do not pursue the "most accurate" color reproduction; pursue the color rendering that the target audience "loves most."**

#### 1.1.4 Japanese Photographic Aesthetics: Wabi-Sabi, Ma, and the Subtraction Approach

Japanese photographic aesthetics are influenced by the traditional concept of "Wabi-Sabi (侘寂)" — embracing beauty in imperfection, transience, and incompleteness. In photographic style this manifests as:

- **Low saturation, pale tones (Fade/Matte effect)**: blacks not crushed, highlights lightly blooming
- **Soft skin luminosity**: not pursuing three-dimensionality; preferring delicate texture in flat, diffuse light
- **VSCO Film Pack "Japanese film" presets** (A4, A6, etc.) as the digital form of this aesthetic
- Representative photographers: Nobuyoshi Araki (high-contrast private photography), Hiroshi Sugimoto (minimalist long exposure), Rinko Kawauchi (gently overexposed everyday records)

#### 1.1.5 The VSCO Effect: Filter Culture and the Rise of Community Aesthetics

In 2011, VSCO App brought professional-grade film filters to smartphones, becoming the representative early mobile photography post-processing community:

- Signature presets: A4/A6 (iconic Japanese fade), M5 (high-contrast black-and-white), C1 (fresh cool tones), HB1 (retro warm tones)
- 2019 official data: VSCO exceeded 100 million registered users, at the time the world's largest stylized photography community
- Business model: preset subscription fees + community sharing, proving that "style" itself has independent market value

VSCO's success delivered a clear signal: **users don't just want "accurate" photos; they want photos with "style," and they are willing to pay for that and invest time in it.**

#### 1.1.6 Aesthetic Label Analysis of Major Smartphone Brands

Entering the 2020s, each flagship smartphone brand has formed a distinct imaging aesthetic label:

| Brand | Color Temperature | Saturation Strategy | Skin Rendering | Sharpness Style | HDR Aggression | Aesthetic Label |
|-------|-------------------|---------------------|----------------|-----------------|----------------|-----------------|
| **Apple iPhone** | Cool-white (cyan-blue cast) | Heavy boost for blue sky / green foliage | Pale, strong dimensionality | High sharpness, clean edges | Medium-high (Neural Engine multi-frame) | "Precise, cool-white, digital feel" |
| **Google Pixel** | Near-neutral | Neutral, natural | Natural skin tones, HDR+ corrected | Medium, slightly soft | High (HDR+) but more natural | "Documentary feel, truth-first" |
| **Huawei / Honor** | Warm (Leica / "German taste") | Medium-high, rich and saturated | Warm orange, "blood color" vitality | Medium-high, fine detail | High (RYYB sensor latitude) | "German taste, dramatic, warm color" |
| **Samsung** | Warm but correcting toward natural in recent years | High saturation (toned down from past excess) | Natural + skin clarity | Extremely high ("Samsung Sharpening") | High | "Vivid, clear; more natural in recent years" |
| **Xiaomi / Leica** | Dual mode (Leica Authentic / Vibrant) | Leica Authentic: lower saturation | Leica Authentic: close to film skin tone | Medium, with lens rendering | Medium | "Film feel, low-saturation premium look" |
| **OPPO / Hasselblad** | Hasselblad natural color | Color accuracy first | Accurate and natural | Medium, delicate | Medium | "Accurate, professional, color-faithful" |
| **vivo / Zeiss** | Zeiss T* tone (cool-clean) | Medium | Cool-white | Medium-high, optical feel | Medium | "Clean, Zeiss blue tone" |

**Key insight**: Every brand, beyond the IQA target of "accurate color," deliberately preserves and reinforces differentiated aesthetic tendencies, demonstrating that aesthetic differentiation is an intentional product strategy — not a technical limitation.

### 1.2 AI Aesthetic Scoring Models: Quantifying "Beautiful"

#### 1.2.1 NIMA (Neural Image Assessment, Google 2018)

Google published NIMA (Talebi & Milanfar, arXiv:1709.05424) in 2018, the first neural network to predict the distribution of photographic aesthetic ratings:

- **Dataset**: AVA (Aesthetic Visual Analysis, ~255,000 photos, each rated by 200+ annotators on a 1–10 scale)
- **Method**: InceptionV3 backbone → outputs a 10-dimensional discrete score probability distribution $\hat{p} = [p_1, p_2, ..., p_{10}]$
- **Loss function (Earth Mover's Distance / Wasserstein)**:

$$\mathcal{L}_\text{NIMA} = W_1(\hat{p},\, p) = \sum_{k=1}^{10} \left| \text{CDF}_{\hat{p}}(k) - \text{CDF}_p(k) \right|$$

Where $p$ is the ground-truth score distribution and $\hat{p}$ is the predicted distribution. Compared to directly regressing the mean score, EMD preserves the variance information of ratings (i.e., the "controversy" of an image).

- **ISP application of NIMA scores**: Can serve as a reference-free aesthetic score for automatic evaluation in A/B style experiments, helping screen candidate parameter sets.

#### 1.2.2 CLIP-IQA (AAAI 2023)

CLIP-IQA (Wang et al., AAAI 2023) leverages CLIP's vision-language alignment capability for no-reference image quality/aesthetic assessment:

- Defines "quality good/bad" as text description pairs: "Good photo / Bad photo", "Beautiful / Ugly"
- Computes the cosine similarity difference between image embeddings and text embeddings as the quality score
- Advantage: Strong zero-shot generalization; custom text prompts enable domain adaptation (e.g., "suitable for social media sharing")

#### 1.2.3 Limitations of IAA Models in Smartphone ISP

The training data for mainstream aesthetic scoring models (AVA, AADB) consists primarily of DSLR photography, causing a **distribution shift**: the stylistic characteristics of mobile computational photography (high HDR, ultra-wide angle, multi-frame synthesis) are underrepresented in training sets. Directly applying NIMA scores to evaluate smartphone photos tends to produce systematic biases. The solution direction is to fine-tune or jointly train on mobile photography datasets (e.g., SPAQ, ~11,000 smartphone photos).

---

## §2 The "Standardization Trap" in Current Computational Photography

### 2.1 IQA Metric-Driven Homogenization

The core orientation of modern smartphone camera tuning is objective benchmark scoring:

- **DXOMark Mobile Score**: color accuracy (ΔE), MTF50 sharpness, low-light noise (SNR10), dynamic range (DR), portrait blur quality
- **Industry internal IQA systems**: PSNR/SSIM for fidelity, NIQE/BRISQUE for reference-free naturalness, and each manufacturer's proprietary subjective scoring system

This orientation is reasonable at the engineering level — objective metrics provide a consistent, quantifiable optimization target and avoid the instability of subjective judgment. But it also creates a structural trap: **all manufacturers are measuring themselves with the same ruler, and ultimately producing photos in the same style.**

The "machine look" of flagship smartphones has distinctive characteristics: high saturation (especially vivid blue skies and green foliage), high sharpness (over-sharpened edges, a hard texture feel), aggressive HDR (both highlights and shadows pulled back, a "flat" image), and no grain (over-denoised, waxy detail — colloquially called "wax skin"). These characteristics score "excellent" on metrics, but may not actually be what users want.

### 2.2 Usage Barriers of "Pro Mode"

Smartphone manufacturers offer "Pro Mode" as a solution to personalization needs, but this solution has fundamental defects:

- **Starting from scratch every time**: portraits need one set of parameters, landscapes another — no memory mechanism
- **Requires professional knowledge**: understanding the interaction of ISO/shutter/white balance/focus modes is beyond the capability of most users
- **Post-processing still required**: RAW format needs to be imported into Lightroom/Snapseed and processed again — the whole workflow is time-consuming and laborious
- **Extremely low usage rate**: industry common experience suggests Pro Mode actual usage is typically less than 3%

This means smartphone manufacturers spend enormous effort on "Pro Mode" that ultimately serves very few users — and that subset of users was already using professional cameras.

### 2.3 Structural Fragmentation of Real User Needs

User needs can roughly be divided into three tiers:

| User type | Estimated proportion | Real need | Current solution |
|-----------|---------------------|-----------|------------------|
| **Ordinary users** | ~80% | Satisfying results as soon as the shutter is pressed; no desire to think about any parameters | Auto mode (but one style fits all) |
| **Style-conscious users** | ~15% | A consistent personal visual style, but unwilling to adjust parameters manually each time | **No good solution exists** |
| **Advanced users / photography enthusiasts** | ~5% | Full control, precise adjustment of every parameter | Pro Mode (but they also use professional cameras) |

**The most neglected group is precisely the middle 15%**: they are perceptive about visuals, willing to invest some effort to get "good-looking photos," but "Pro Mode" is too high a barrier, and "Auto Mode" cannot meet their personalization needs. This group is the core user base for VSCO, Lightroom Presets, and film filter apps — they spend significant time post-processing outside of shooting. This shows the demand is real; it has simply been forced into a post-processing workflow.

### 2.4 User Preference Modeling and A/B Testing Methodology

#### 2.4.1 User Segmentation and Preference Differences

Different user groups assign markedly different weights to the dimensions of "a good photo":

| User Group | Core Evaluation Dimensions | Tolerance for Over-processing | Typical Platform |
|------------|---------------------------|-------------------------------|-----------------|
| **Gen Z (18–25)** | Visual impact, social shareability | High (accepts exaggerated filters) | TikTok, Xiaohongshu |
| **Urban professionals (25–40)** | Naturalness, skin rendering | Medium | Instagram, WeChat Moments |
| **Photography enthusiasts** | Color accuracy, tonal gradation, grain feel | Low (rejects "plastic" look) | 500px, photography forums |
| **East Asian aesthetic preference** | Low saturation, faded feel, lighter skin | Medium-high (accepts major tone shifts) | VSCO, Japanese indie |
| **Western users** | Natural color, high dynamic range | Low (prefers realistic look) | Google Photos, Flickr |

**Engineering impact of cultural differences**: Asia-Pacific markets (especially China, Japan, Korea) favor lighter skin tones, with users on average expecting skin brightening of approximately 5–15% ($\Delta L^* \approx +3$ to $+8$); Western markets have low tolerance for skin modification, and excessive brightening reduces satisfaction. This directly affects default skin enhancement parameter values in regional product versions.

#### 2.4.2 A/B Testing Methodology

Smartphone manufacturers use A/B testing to quantify user preferences during ISP style tuning. Key design considerations:

**Sample size calculation:** Given detection effect size $\delta$ (e.g., MOS change of 0.3), significance level $\alpha = 0.05$, test power $\beta = 0.8$, the required sample size is:

$$N \approx \frac{2\sigma^2 (z_{\alpha/2} + z_\beta)^2}{\delta^2}$$

Where $\sigma$ is the standard deviation of MOS scores (typical value 0.8–1.2). Usually 300–500 evaluators per group are needed.

**Comparison design principles:**
- Render A and B versions of the same scene (only the tested parameter varies); all other conditions are identical
- Blind test (users do not know which version comes from which phone), avoiding brand bias
- Use 2AFC (Two-Alternative Forced Choice) rather than absolute scoring to reduce scale inconsistency
- Multi-scene testing (night / portrait / landscape / indoor) in separate groups — a parameter's effect may invert across scenes

**Implicit behavioral signals:** In large user populations (>1 million users), behavioral data can substitute for subjective scoring:
- **Share rate** (proportion uploaded to SNS): highly correlated with aesthetic satisfaction
- **Save rate** (archived rather than deleted): measures user approval
- **Post-editing rate** (opening an editor immediately after capture): a negative signal indicating dissatisfaction with the direct output
- **Note**: behavioral data has selection bias; it should be combined with cohort analysis and formal subjective testing

---

## §3 Product Vision: A Personalized Ecosystem of Scene Recognition + Parameter Templates

### 3.1 Core Architecture Concept

The solution is not "a better Pro Mode" but rather **adding an intelligent personalization layer on top of the baseline ISP processing**:

```
Traditional ISP pipeline (BLC → Demosaic → Denoise → CCM → Gamma → Sharpening ...)
                          ↓
               [User Personalization Layer] (new addition)
    ┌─────────────────────────────────────────────┐
    │  Scene recognition → scene tags (portrait/landscape/night/food ...)  │
    │        ↓                                    │
    │  Template matching engine → selects the best parameter template from the user library  │
    │        ↓                                    │
    │  Parameter overlay rendering → applies style offset on top of ISP baseline  │
    └─────────────────────────────────────────────┘
                          ↓
               Final photo (styled + fully automatic direct output)
```

**Four key design principles:**

1. **Baseline processing unchanged**: the underlying ISP algorithm guarantees correct exposure, reasonable denoising, and sharp focus — this is the floor
2. **Style layer independent**: a LUT (3D Look-Up Table) or parameter offset is layered on top of baseline processing; the two are decoupled
3. **Scene auto-matching**: different scenes automatically apply the corresponding style parameters; no user selection required each time
4. **Templates downloadable and replaceable**: users or community creators can produce, publish, and share parameter packages

### 3.2 Technical Implementation of Parameter Templates

```python
# Parameter template structure example (proof of concept)
class ISPStyleTemplate:
    # Metadata
    name: str               # "Leica Film Portrait v2"
    author: str             # community username or verified photographer
    version: str            # "1.2.0"
    target_scenes: list     # ["portrait", "street", "indoor"]
    preview_thumbnail: str  # preview image URL

    # Global parameter offsets (deltas on top of ISP baseline)
    saturation_offset: float        # -0.15 (slight desaturation, film feel)
    contrast_curve: np.ndarray      # gentle mid-high tone compression, shadow detail preserved
    white_balance_shift: tuple      # (R: +0.02, B: -0.03) slightly warm
    exposure_bias: float            # within ±0.3 EV range

    # Local processing parameters
    skin_tone_hue_shift: float      # skin tone hue offset
    skin_softness: float            # 0.3 (light smoothing, not skin retouching)
    sky_saturation_boost: float     # 0.0 (no additional sky saturation boost)
    shadow_lift: float              # 0.05 (slight shadow lift, film latitude feel)

    # 3D LUT (optional, for advanced styles)
    lut_3d: Optional[np.ndarray]    # 33×33×33 color mapping table (~87 KB)
    lut_strength: float             # 0.7 (blend ratio with baseline color)

    # Safety constraints (verified during platform review)
    max_exposure_deviation: float   # must not exceed ±0.5 EV
    max_delta_e: float              # mean ΔE must not exceed 10 (relative to sRGB reference)
```

**Technical notes:**
- **Choice of 3D LUT**: a 33³ LUT is approximately 87 KB; interpolation computation is low; mainstream ISP SoCs (e.g., Qualcomm Hexagon DSP, MediaTek APU) have hardware acceleration support, enabling real-time preview
- **Parameter offsets vs. full LUT**: offset-based approach is portable across devices, suitable for community sharing; LUT approach is precise but requires per-device calibration
- **Style layer takes effect in the RAW domain** (not as JPEG post-processing): results are more natural and do not introduce secondary compression artifacts

### 3.3 Community Ecosystem Model

Drawing on the mature operational model of the Lightroom Preset community, the VSCO filter marketplace, and the App Store:

| Role | Behavior | Value created |
|------|----------|---------------|
| **Verified photographers** | Create and upload style packages with portfolio showcase | Personal brand monetization; users get professional-grade direct output |
| **Brand / IP partners** | License official style packages (e.g., "Palace Museum Color," "Fujifilm Velvia Licensed") | Digital brand extension; platform differentiated assets |
| **Ordinary users** | Download, subscribe, rate, share output in the community | Low-barrier access to professional styles; community belonging |
| **ISP engineers** | Maintain the baseline processing layer; provide a stable parameter API | Ensures the style layer never breaks fundamental image quality in any scenario |
| **Smartphone platform** | Provide distribution, review, and monetization infrastructure | Ecosystem control; subscription revenue |

**Fundamental difference from existing approaches:**
- **Not a "filter app"** (like beauty camera or Snapseed): parameters take effect within the ISP pipeline, operating in the RAW domain or early YUV stage — results are natural, unlike processing a JPEG output
- **Not "offline post-processing"** (like Lightroom Mobile): real-time preview — what-you-see-is-what-you-get while framing; direct output on capture
- **Different from manufacturer-preset "color styles"** (like Sony Picture Profile, Nikon Picture Control): fully open to third-party creation; infinitely extensible

### 3.4 Technical Challenges and Solution Paths

| Challenge | Problem description | Solution direction |
|-----------|--------------------|--------------------|
| **Scene recognition accuracy** | Incorrect scene tags trigger the wrong style (dusk architecture misclassified as portrait) | Multi-scale multi-label classification + confidence threshold; fall back to general template at low confidence |
| **Cross-device parameter migration** | Template calibrated on Device A drifts on Device B (different sensor spectral response) | Camera-Aware Normalization; normalize parameter space under a standard color chart |
| **LUT computation overhead** | Real-time trilinear interpolation for 33³ LUT may drop frames on low-end chips | Hardware LUT engine (Qualcomm Hexagon, MTK APU both natively support); degrade to 17³ on low-end |
| **Copyright and content review** | User uploads "perfect Fujifilm Velvia recreation" may infringe IP | Platform copyright agreement; perceptual-hash-based similarity detection; official licensing channel |
| **Extreme parameters breaking baseline** | Malicious or incorrect templates may push exposure to unusable range | Platform mandatory safety constraints: exposure deviation ≤ ±0.5 EV, mean ΔE ≤ 10, negative saturation < -0.5 prohibited |
| **Personalization cold start** | New users have no preference history, making template recommendations difficult | Guide users through a "style test" (pick preferred images from 5 pairs) to build an initial preference vector |

---

## §4 Industry Status: Different Attempts by Each Manufacturer

### 4.1 Fujifilm Film Simulation — The Most Successful Precedent

Fujifilm's Film Simulation system is the most commercially successful example of a "non-standardized color philosophy" to date:

- **Product level**: The X-series cameras offer 18 or more film simulations (as of 2024), each with a clear color personality and applicable scenes
- **Community level**: Communities like Fuji X Weekly and FujiFilmRecipe.com self-organize to maintain thousands of "recipes" combining film simulations with other in-camera parameters (grain, tone curves, highlight/shadow settings) into reproducible recipes, categorized by scene and style
- **Commercial result**: Fujifilm's market share and brand premium in the interchangeable-lens camera segment have grown continuously; "Fujifilm color" has become an independent aesthetic label with strong brand stickiness

**Limitation**: closed system — only usable within Fujifilm cameras; no open API; does not support user creation of new simulation types.

### 4.2 Apple Photographic Styles (iOS 16, iPhone 14 onward)

Apple introduced "Photographic Styles" with iPhone 14/15 — the most clearly direction-setting personalization effort among smartphone manufacturers:

- **Preset styles**: Rich Contrast, Vibrant, Warm, Cool + default Standard
- **Adjustable parameters**: Tone (contrast curve control) + Warmth (color temperature offset) — two slider dimensions
- **Key technical point**: Photographic Styles take effect in the RAW domain within the ProRAW workflow (not as JPEG post-processing), so the style is more natural and highlight/shadow detail is not lost due to post-processing
- **iPhone 16 improvement**: supports re-applying or switching styles on existing photos after capture (non-destructive editing), greatly improving usage flexibility

**Limitation**: only 4 presets; very few adjustable parameter dimensions; does not open third-party style creation; does not form a community.

### 4.3 Google Pixel Camera — AI-Driven Style Exploration

- Pixel 8/9's "Best Take" and "Add Me" are more scene-level functions; style personalization is relatively weak
- Google Photos' "Suggested Edits" predicts adjustments the user might prefer based on ML, but this is still post-processing rather than direct output
- Pixel's "Magic Eraser," "Photo Unblur," and similar features focus more on correction than on stylization

Google's overall commitment to style personalization is weaker than Apple and Fujifilm; it relies more heavily on a lead in AI correction capabilities.

### 4.4 Smartphone Manufacturer Brand Collaboration Model

The recent trend of "camera brand co-branding" is essentially **a fixed parameter package backed by brand authority**:

- **Xiaomi × Leica** (from Xiaomi 12S Ultra onward): Leica Authentic (restores the darker, lower-saturation film feel of Leica lenses) and Leica Vibrant (vivid style more suitable for ordinary users) modes; Leica Summicron lens simulation (flare, bokeh rendering)
- **OPPO × Hasselblad** (from Find X5 Pro onward): Hasselblad Natural Colour Solution (HNCS), calibrated using X-Rite color charts, combined with Hasselblad-style tone curves
- **vivo × Zeiss** (from X70 Pro onward): Zeiss Color (optical characteristics of T* coating translated into a digital filter), Zeiss Portrait style
- **Honor × S.T. Dupont**: luxury brand co-branding — more a marketing concept than a technical one

The technical essence of these collaborations is: a few sets of color curves and LUTs co-confirmed by the brand partner are fixed at the factory; users cannot modify them, and no community is formed. They solve the problem of "a tasteful default style" but do not solve the "personalization" problem.

### 4.5 The Aesthetic Cost of Computational Photography Over-Processing

As AI capabilities grow stronger, the "side effects" of computational photography have become increasingly prominent, giving rise to new aesthetic boundary debates:

#### 4.5.1 Plastic Skin Effect

**Phenomenon:** Deep learning portrait enhancement over-smooths skin, turning it into a texture-free surface resembling plastic — pores and skin texture disappear entirely.

**Root cause:** Portrait denoising model training data uses "clean" skin as positive samples, but the skin's natural texture is misidentified as noise; skin region mask accuracy is insufficient, causing smoothing to spread into hair and eyelashes.

**Diagnostic criterion:** When the HF energy ratio of the skin region (MTF band 150–300 lp/mm) relative to non-skin regions falls below 0.3, the "plastic skin" artifact is typically visible.

#### 4.5.2 Over-HDR "Oil Painting" Artifact

**Phenomenon:** Overly aggressive local tone mapping produces unnatural contrast enhancement — sky cloud outlines resemble pencil sketch lines, shadow-area details "float up," and the overall image feels over-textured — colloquially called the "oil painting effect."

**Root cause:** The spatial radius of local tone mapping operators (e.g., Reinhard Local, Bilateral Tone Mapping) is too small, causing high-frequency structures to be treated as local luminance variations and compressed, producing halos and an "etched" look.

**Mitigation direction:** Increase the spatial kernel radius (reducing high-frequency mishandling), or perform the TMO on the CIELAB lightness channel and then recombine with the original chroma channels (Edge-Aware approach).

#### 4.5.3 Boundary Artifacts from AI Sky Enhancement

**Phenomenon:** AI sky segmentation + auto-enhancement produces a color boundary near the horizon — the sky region is brightened/saturated while the ground region remains unchanged, creating a visible color seam ($\Delta E_{00} > 3$ luminance/color discontinuity).

**Root cause:** Insufficient precision of sky segmentation mask edges (non-continuous alpha values at foreground/background boundaries), combined with overly steep blending parameters applied to mask edges in the ISP.

#### 4.5.4 Super-Resolution Hallucination

**Phenomenon:** Generative super-resolution creates non-existent high-frequency details in repetitive textures (fabric, brick, grass) — at high magnification, clearly visible "fake texture" appears that does not correspond to the real scene.

**Effect boundary:** Normal super-resolution restoration within 4× upscaling is generally reliable; beyond 4× or with very low-quality input, the generative component proportion increases and hallucination risk rises significantly.

#### 4.5.5 Over-Saturation and Sharpening Failure Cascade

**Phenomenon:** Saturation enhancement and sharpening appear to be independent parameters, but in high-contrast HDR scenes they have a multiplicative coupling effect — combined adjustments cause colored halos (Colored Edge Halo) at highlight boundaries, commonly blue-purple edges or yellow-green inner halos, most visible at the boundary between dark clothing and bright backgrounds.

**Failure cascade:** HDR local contrast enhancement → Highlight expansion → Saturation gain unsuppressed in bright regions continues to amplify → Hue shift in highlights → USM sharpening further amplifies color gradient errors → Colored halos at high-contrast edges.

**Quantitative safety limits** (based on ISP tuning engineering experience):

| Parameter | Safe Upper Limit | Typical Artifact When Exceeded |
|-----------|-----------------|-------------------------------|
| USM gain (`sharpen_gain`) | ≤ 1.8× | Chroma fringe — demosaic residuals amplified into visible colored bands |
| Global saturation gain | ≤ 1.3× (+30%) | High-saturation gamut clipping, Lab skin tone shift |
| Skin region saturation offset | Within ±5% | Skin tone distortion, DXOMark skin color accuracy score drops |
| Highlight region (Y > 230) saturation | Must be suppressed (saturation × attenuation factor < 0.6) | Color bloom in highlights |

**Skin tone protection mask (YUV gamut window):** Cb ∈ [90, 130], Cr ∈ [140, 170], Y ∈ [80, 220] — pixels within this window receive independently lower saturation gain and soft-limited sharpening; pixels outside receive global parameters normally.

**Tuning order constraint:** Contrast → Saturation → Sharpening (strict sequence). Adjusting a later parameter changes the effective operating point of earlier steps; reversing the order causes the final state to drift outside the safety limits.

> **Engineering recommendation (aesthetic parameterization design principle):** Before building a personalized ISP ecosystem, clarify where the style layer is inserted in the pipeline — because the position determines what can be done and what might be broken. Fujifilm Film Simulation inserts after: 3A convergence → baseline ISP (BLC/Demosaic/CCM/Gamma) → before JPEG compression, so the style layer does not interfere with AE's luminance measurement or AWB's color temperature estimation. Apple Photographic Styles takes effect earlier in the ProRAW workflow, at the cost of re-running the full ISP every time the style is switched. Implementation recommendation: store style parameters in **delta form** (offsets) rather than absolute values — `saturation_delta = -0.15` rather than `saturation = 0.55` — so the baseline ISP factory calibration is unaffected, and the same style package can be applied across device models without modification. Hard constraints must be enforced at the architecture level: exposure offset $|bias_{EV}| \leq 0.5$, local tone mapping spatial kernel radius $r_{LTM} \geq 150\,\text{px}$ (prevents oil-painting effect), skin region smoothing strength $\leq 0.4$ (prevents plastic skin), mean color difference $\bar{\Delta E}_{00} \leq 8$. Embedding these four constraints into the style package upload review process is far cheaper than discovering problems in post-launch QA.

---

## §5 Technical Frontier of Personalized ISP Ecosystems

### 5.1 User Preference Learning and RLHF

*(See Vol.5 Ch.98 RLHF Camera Tuning section of this handbook)*

The approach of Reinforcement Learning from Human Feedback (RLHF) has begun entering the photography personalization space:

- **PickScore** (Kirstain et al., NeurIPS 2023, arXiv:2305.01569): trains an image quality preference prediction model from users' comparative selection behavior among generated images. Core idea: show users two photos of similar composition but different processing styles and record the choice; iteratively converge to the user's preference space
- **ImageReward** (Xu et al., NeurIPS 2023, arXiv:2304.05977): similar approach, focused on text-to-image generation, but the methodology is fully transferable to ISP parameter preference prediction
- **Lightweight personal preference model**: a lightweight preference vector of approximately 1–5 MB can be stored locally on the device, avoiding user privacy uploads while achieving genuine personalization

**Engineering challenge**: preference learning for ISP style requires constructing specialized paired contrast samples — different style versions of the same scene. This requires the camera system to internally save multiple rendered versions (substantial compute and storage overhead), or to offline-generate contrast versions afterward for user scoring.

### 5.2 Language-Guided Color Control

*(See Vol.5 Ch.97 Sony Language-based Color ISP Tuning section)*

Work published by Sony Group at CIC 2025 (arXiv:2509.10765) demonstrates a method for directly optimizing ISP parameters using natural language descriptions:

- User input: "Shoot a Japanese-style soft portrait, cool-white skin, soft highlight bloom in the background"
- CLIP embeds the text description into a space aligned with color/style features
- An optimizer adjusts the ISP parameter vector based on semantic similarity

This lowers the "creation" barrier for parameter templates from "requires knowledge of color grading" to "just be able to describe the desired effect," dramatically expanding the potential pool of template creators.

### 5.3 Style Extraction and Rapid Parameterization

*(See Vol.3 Ch.05 Style Transfer section)*

Extract a photographer's style from a small number of reference photos (10–20 images) and generate a corresponding ISP parameter package:

- **AdaIN (Adaptive Instance Normalization)**: aligns mean/variance of content and style images to achieve real-time style transfer, convertible to a 3D LUT
- **IA-SISR / CSRGAN-style methods**: transfer target image statistics while preserving content
- **Practical scenario**: a photographer uploads 20 representative works; the system automatically extracts their style fingerprint and generates a downloadable parameter package for others

### 5.4 Aesthetic Quality Assessment System

#### 5.4.1 Standardization of Subjective Evaluation Methods

Aesthetic subjective evaluation requires a dedicated design to avoid conflation with traditional IQA subjective testing:

| Method | Applicable Scenario | Key Design |
|--------|--------------------|-----------|
| **MOS (Mean Opinion Score)** | Absolute scoring, global preference | 5/7/9-point scale; requires 30+ evaluators; statistics: mean + confidence interval |
| **2AFC (Two-Alternative Forced Choice)** | Comparative preference, relative preference | A vs. B forced choice; Bradley-Terry model ranking; no absolute standard needed |
| **Pairwise Ranking** | Multi-version ordering | N versions compared pairwise, totaling $N(N-1)/2$ pairs; Fisher's exact test |
| **DSIS (Double Stimulus Impairment Scale)** | Degradation perception | Reference image + test image side by side; evaluates quality degradation from processing |

**A 7-dimension evaluation framework for mobile aesthetic assessment:**

| Dimension | Meaning | Typical Subjective Description |
|-----------|---------|-------------------------------|
| **Overall color feel** | Whether colors are pleasant and distinctive | "The color tone is appealing" |
| **Skin tone naturalness** | Whether portrait skin looks real and healthy | "Skin doesn't look over-processed" |
| **Detail sense** | Whether texture, hair, distant details are sharp | "Clear and textured" |
| **Noise perception** | Whether dark areas have unpleasant noise | "Night shots look clean" |
| **HDR naturalness** | Whether highlights/shadows converge naturally | "No blown-out areas" |
| **Sharpness appropriateness** | Presence of over-sharpening, ringing, or blur | "Sharpening is just right" |
| **Overall impression** | Combined first impression — "does it look good?" | "I'd want to post this" |

#### 5.4.2 Aesthetic IQA Benchmark Datasets

| Dataset | Scale | Source | Score Type | Primary Use |
|---------|-------|--------|-----------|------------|
| **AVA** | 255,530 images | DPChallenge photography site | 1–10 aesthetic scores (~200 raters/image) | Aesthetic model training/evaluation |
| **AADB (Aesthetic And Attribute Database)** | 10,000 images | Flickr | 11 aesthetic attribute dimensions + overall score | Multi-dimensional aesthetic understanding |
| **SPAQ (Smartphone Photography Attribute Quality)** | 11,125 images | Real smartphone captures | MOS + 6-dimension attributes | Smartphone photography quality evaluation |
| **KonIQ-10k** | 10,073 images | Flickr (authentic distortions) | MOS | NR-IQA benchmark |
| **LIVE-FB** | 39,810 images | Facebook user photos | MOS | Social media scene IQA |

**Note**: AVA/AADB primarily contain DSLR/mirrorless photography; SPAQ most closely matches real smartphone photography usage. **For evaluating smartphone ISP aesthetic effects, SPAQ should be the preferred dataset.**

---

## §6 Looking Ahead: Image Quality Taste Should Be Yours to Set

### 6.1 Prerequisites

The maturation of a personalized imaging ecosystem requires the following conditions:

1. **Hardware layer**: ISP provides a programmable parameter interface (Open ISP API); chipmakers (Qualcomm, MediaTek) need to expose sufficient API granularity. Camera HAL 3 already provides some interfaces, but granularity is insufficient
2. **Normalization standard**: a cross-device parameter normalization standard (Camera-Device Abstraction Layer, CDA-L), analogous to ICC color profiles, ensuring parameter packages produce consistent results across different phones
3. **Ecosystem platform**: a distribution platform (app store model) + creation tools (visual color grading tool, like a simplified DaVinci Resolve color wheel) + community (creator incentive mechanisms)
4. **Industry standard**: a parameter package format standard (analogous to .cube files for LUTs, but extended to more ISP parameter dimensions)

### 6.2 A Deeper Connection to the Democratization of Imaging

Historically, every democratization of imaging tools has sparked a burst of diversification in photographic aesthetics:

- **Kodak Brownie (1900)**: cameras became mass consumer products; family photography aesthetics were born
- **Kodachrome (1935)**: color film became widespread; amateur photographic color language began diversifying
- **Digital cameras (1990s)**: instant preview and zero-cost capture sparked an explosion of street and documentary photography
- **Smartphones (2007–)**: photography reached ultimate ubiquity, giving rise to visual cultures like Instagram and VSCO
- **Personalized ISP ecosystem (?)**: the next step — not just tools democratized, but **aesthetics democratized**

"Image quality as something you can set yourself" is not a technical compromise; it is the inevitable transition from an engineer-centric to a user-centric definition of "what a good photograph is." The ultimate mission of the ISP engineer is not to tune every photograph to rank first on DXOMark, but to make it easy for every user to capture the photograph that exists in their imagination.

---

---

## §7 Extended Reading

### 7.1 AIGC Enters Photography: Reshaping the Aesthetic Boundary

The intervention of generative AI is changing the very definition of "a photograph":

- **Samsung Galaxy AI Generative Edit**: allows AI-based outpainting/infilling of the captured frame; the fill content is created by a generative model. This is the first time generated content has been legitimately incorporated into an "ordinary shooting" workflow.
- **Apple Photos Clean Up / Remove Person**: AI removes people from a frame and visually fills the background seamlessly — the definition of "truthfulness" in photographic records begins to loosen.
- **The aesthetic boundary question**: when 30% of the image is AI-generated, is this still a photographic work? Contest rules, news photo verification, and legal evidentiary value all face redefinition.

### 7.2 The Privacy Paradox of Personalized Style

User preference learning requires collecting users' selection behavior data, but this data can precisely characterize a user's visual preferences, emotional states, and lifestyle — highly sensitive personal information.

- **Federated learning approach**: train the personal preference model locally on the device; upload only gradients, not raw images (similar to iOS On-Device ML)
- **Differential privacy**: inject random noise into uploaded preference statistics to ensure individual non-identifiability
- **See also**: Vol. 5, Ch. 12 (Privacy-Preserving Computational Photography)

### 7.3 Cross-Reference Map to This Handbook

| Related Chapter | Connection |
|----------------|-----------|
| Vol. 2, Ch. 27 (Computational Bokeh) | Aesthetic boundaries of bokeh rendering — natural blur vs. generative background |
| Vol. 3, Ch. 05 (Style Transfer) | Technical foundation for automated parameter template generation |
| Vol. 3, Ch. 23 (Personalized Color Grading) | Reference-based color grading as a template generation tool |
| Vol. 4, Ch. 04/05 (Perceptual/Blind IQA) | Technical details of NIMA / CLIP-IQA |
| Vol. 5, Ch. 03 (LLM-Assisted ISP Tuning) | Natural language generation of style parameters |
| Vol. 5, Ch. 12 (Privacy-Preserving Photography) | Privacy design for user preference learning |
| Vol. 6, Ch. 02 (Night Sight) | Concrete implementation of Google's realism-first aesthetic |

---

## §8 Glossary

**Aesthetic Score / IAA (Image Aesthetic Assessment)**
Technology for predicting image aesthetic quality using neural networks, exemplified by NIMA (AVA dataset) and CLIP-IQA (language alignment). Distinction from IQA: IQA assesses technical fidelity (presence of distortion); aesthetic scoring assesses visual appeal (whether it looks good).

**AVA Dataset (Aesthetic Visual Analysis Database)**
Published by Murray et al. (2012), collected from the DPChallenge photography competition website; approximately 255,000 photos, each with approximately 200 ratings on a 1–10 scale. The most widely used benchmark for aesthetic quality assessment.

**Film Simulation**
Technology that digitalizes the color characteristics of a specific film stock (tone curve, color cast, grain texture) into a camera direct-output style. Fujifilm's Film Simulation system (18+ types) is the most commercially successful implementation.

**2AFC (Two-Alternative Forced Choice)**
A forced binary choice method: the evaluator is presented with two stimuli (A and B) and must choose one, eliminating the scale inconsistency of absolute scoring. The recommended method for aesthetic comparison testing.

**Plastic Skin Effect**
An artifact in which AI portrait enhancement over-smooths skin, causing skin texture to disappear and the surface to appear plastic-like. Quantitative criterion: skin region high-frequency energy ratio < 0.3 relative to non-skin regions.

**Bradley-Terry Model**
A statistical model for estimating global preference rankings for items from pairwise comparison data (2AFC). Commonly used in aesthetic preference ranking analysis.

**Wabi-Sabi (侘寂)**
A Japanese aesthetic concept emphasizing beauty in imperfection, transience, and incompleteness. Expressed photographically as low saturation, pale tones, and an embrace of technical imperfection.

**Zone System**
An exposure control system proposed by Ansel Adams, dividing scene luminance into 11 zones (Zone 0 pure black to Zone X pure white), ensuring each zone falls within its intended tonal range through precise exposure and development control — the forerunner of local tone mapping in modern ISP.

---

## §9 Technical Deep-Dive: Advances in Aesthetic Quantification Research and Industry Debates (2024)

### 9.1 Systematic Robustness Study of Aesthetic Evaluation (2024 New Findings)

In 2024, Wiley published a systematic study "Towards Robust Evaluation of Aesthetic and Photographic Quality" (Giudice et al., Computational Aesthetics, 2024), cross-validating five mainstream computational aesthetics metrics:

**Metrics tested:**
- **BRISQUE** (Blind/Referenceless Image Spatial Quality Evaluator)
- **NIMA Technical** (technical quality score)
- **NIMA Aesthetic** (aesthetic score, trained on the AVA dataset)
- **PhotoILike** (specialized for smartphone photography aesthetics)
- **Stable Diffusion Aesthetics** (generative image aesthetic score)

**Core findings:** Different metrics show systematic disagreement in judging "over-computationally-processed" scenes:
- NIMA Aesthetic assigns higher scores to high-saturation, strong-HDR computational photography images (training set dominated by DPChallenge DSLR work, where high-contrast images are popular)
- BRISQUE has good sensitivity to the "waxy" feel after AI denoising (abnormally low high-frequency energy)
- PhotoILike makes more reliable judgments for smartphone shooting scenarios, but still struggles to distinguish "aesthetic over-processing" from "technically subpar"

**Implication for ISP engineers:** A single aesthetic metric cannot substitute for multi-dimensional subjective evaluation. It is recommended to use the combination of NIMA Aesthetic + BRISQUE + PhotoILike together; when any one metric deviates significantly, trigger subjective verification.

### 9.2 Emotion-Driven ISP: The EMOVIS Framework (arXiv, 2025)

EMOVIS (Emotion-Optimized VISual processing, arXiv:2605.03131, 2025) proposes a new framework for directly incorporating emotional context into ISP parameter control:

**Core concept:** Establishing a systematic mapping between emotional states (Happy / Calm / Angry / Sad) and ISP low-level control parameters (color saturation, hue, brightness, local tone mapping, sharpness):

| Emotional State | Saturation | Warm Tone | Local Contrast | Sharpness |
|----------------|-----------|-----------|----------------|-----------|
| Happy | Increase | Warm | Enhance | Slightly high |
| Calm | Medium-low | Neutral | Reduce | Low |
| Angry | High | Cool-red | Strong | High |
| Sad | Low saturation | Cool | Compress | Low |

**Blind test validation results:** When the target emotion matches the scene context, 87% of viewers prefer the emotion-optimized ISP rendering; when the emotion does not match, the preference rate drops to 24% — proving that the validity of emotion-parameter mapping is conditional on semantic consistency.

**Engineering significance:** ISP color rendering strategy is no longer just a trade-off between "color accuracy" and "user preference"; it also involves matching the emotional context of the scene. The EMOVIS framework provides an engineering path for incorporating the emotional dimension into ISP tuning.

**Connection to this chapter:** EMOVIS operates at the ISP layer (RAW/linear domain), superior to post-processing approaches, because adjustments on high-dynamic-range linear data preserve highlight detail, while equivalent adjustments in the JPEG domain cause clipping and gamut artifacts.

### 9.3 Case Record: Industry "Realism" Debates

#### 9.3.1 Samsung Galaxy Over-Processing Controversy (2019–2023)

Samsung Galaxy S23 Ultra's "hundred-megapixel" super-resolution feature triggered large-scale controversy in 2023:

- **Original problem (March 2023):** Reddit user **ibreakphotos** designed a controlled experiment (photographing a printed low-resolution moon image), proving that Galaxy S23 Ultra automatically overlays pre-stored moon texture details. Subsequently widely reported by The Verge (journalist Mitchell Clark) and other media, attracting global attention.
- **Samsung's response:** Acknowledged the use of "scene optimization" technology, but characterized it as "HDR merging and detail enhancement," not fabrication.
- **ISP engineering perspective:** The problem is essentially a **super-resolution network generative hallucination** issue — the network encountered large numbers of moon photos in training, and at inference time uses the scene recognition result (moon) as a prior to generate corresponding high-frequency details that do not originate from sensor information.
- **Samsung's subsequent correction (2023):** Starting with the Galaxy S23 series, "factual constraints" on AI processing were strengthened, the proportion of generative components in super-resolution results was significantly reduced, and overall moon capture quality became closer to the optical physics limit rather than AI generation.

#### 9.3.2 Google Night Sight's "Realism" Philosophy

Google engineer Marc Levoy (core designer of the Pixel camera) explicitly articulated Night Sight's aesthetic position in a 2018 interview (a position that stands in stark contrast to Samsung's):

> "We don't generate details in an image that don't exist. What Night Sight does is multi-frame merging — it only uses the photon information that actually reached the sensor. If a detail doesn't exist in any single frame, it won't appear in the final result either."

This "Photon Faithfulness" principle became the core differentiating point of Pixel's photography aesthetic:
- **Night Sight does not do AI face enhancement** (facial super-resolution has not been enabled by default to date)
- **Sky enhancement performs only HDR recovery**, without generating non-existent cloud textures
- **Dynamic range expansion** comes from real multi-frame exposure merging, not single-frame HDR simulation

**Quantitative comparison (external testing organization data, ~2022):** In the same low-light scene, comparing Pixel 6 Pro with Galaxy S22 Ultra, the S22 Ultra's PSNR was slightly higher (~+1.2 dB), but its Texture Hallucination Rate (THR) was 3.8 times that of Pixel — demonstrating that a higher PSNR does not equal greater "realism."

#### 9.3.3 Huawei RYYB Sensor and Saturation Controversy

The Huawei P40 Pro/Mate 40 Pro series uses an RYYB (replacing green pixels with yellow) sensor, improving low-light throughput by approximately 40%, but introducing a different category of aesthetic controversy:

- The RYYB sensor's yellow filter has different spectral response in the green channel compared to RGGB, requiring a CCM with stronger negative coefficients to suppress sky color leakage (Sky Spill)
- Under conditions of excessive color enhancement, RYYB photos' blue skies can exhibit unnatural cyan-green shifts, and green foliage tends toward yellow
- This phenomenon was recorded in DXOMark evaluations as "Color Rendering Artifact," but scores remained high — indicating that the current IQA system applies insufficient penalty weight to this type of "stylistic deviation"

**Implication:** The superposition effect of sensor physical characteristics and ISP color enhancement can produce aesthetic problems that exceed the scope of single-dimension analysis, requiring analysis from the complete sensor-ISP-evaluation chain.

### 9.4 User Perception Experiment Data Summary

The following data comes from publicly published user research, providing quantitative support for the arguments in this chapter:

**Exaggerated HDR perceptual threshold (Reinhard et al., 2002 classic study):**
- When local tone mapping gain exceeds 3:1, 70% of viewers report "unnatural"
- When gain is < 1.5:1, unnaturalness perception rate is < 12%
- Current flagship phone local HDR gain peaks are estimated in the 2:1–5:1 range (varies widely by brand and scene)

**Denoising strength and user satisfaction (Samsung internal data, publicly stated at ISP conference):**
- The relationship between skin region denoising strength and user satisfaction is an inverted U: light denoising (~30% noise reduction) achieves highest satisfaction
- Over-denoising (>70% noise reduction) achieves satisfaction lower than light denoising, approaching the level of no denoising at all
- The optimum is approximately SNR improvement of +4 to +6 dB (skin region)

**Color saturation and "like" rate cross-cultural study (IJsselsteijn et al., 2005):**
- European users: peak "like" rate when color saturation is 10% above reference; significant decline beyond 20%
- Asian users (China, Japan, Korea): peak at 20–30% higher; tolerance limit approximately 40%
- This cultural difference gap has been replicated in multiple subsequent studies and is the academic basis for "regional version differentiation" by smartphone manufacturers

---

> **Engineering Note: Aesthetic Boundaries, Engineering Ethics, and Product Compliance**
>
> **The boundary between enhancement and reality is hard to quantify in product implementations:** Removing wrinkles and adjusting skin tone are two operations of entirely different natures, but at the product implementation layer they share the same technical means (pixel modification in facial regions). This makes "where is the boundary?" a real dilemma engineers face daily. An industry-accepted distinction framework is: Enhancement (preserving real information in its presentation — e.g., correcting color cast, reducing noise) vs. Alteration (changing real physical features — e.g., removing wrinkles, slimming the nose). Engineeringly, any modification-class operations (smoothing degree >20%, any facial adjustment) should be flagged in EXIF metadata with a marker field `XMP:RetouchLevel`, enabling downstream platforms to identify processed images.
>
> **Platform compliance policy and engineering response:** Since 2023, Meta and TikTok have successively required disclosure of AI-generated or heavily AI-modified images/videos. This has a direct impact on the smartphone ISP supply chain: if a camera app has enabled strong beauty enhancement or AI generative fill, the exported image needs to carry standardized content credentials (e.g., C2PA standard digital signatures) to certify the modification scope. Implementing C2PA compliance requires injecting a signing process at the ISP output stage: recording the original RAW hash, ISP processing step summaries, and parameters at capture time, and attaching an embedded signature at JPEG export. This process adds approximately 80 ms of write latency, requiring asynchronous processing for ZSL (Zero Shutter Lag) scenarios.
>
> *References: Adobe Content Credentials / C2PA Specification v1.3, contentauthenticity.org 2023; EU Artificial Intelligence Act, Official Journal of the European Union 2024*

---

## Figures

![fig aesthetics metrics](img/fig_aesthetics_metrics_ch.png)

*Figure 1. Image aesthetic quality evaluation metrics*

![aesthetic isp tuning preferences](img/fig_aesthetic_isp_tuning_preferences_ch.png)

*Figure 2. ISP aesthetic tuning user preference analysis*

![ai vs human aesthetic](img/fig_ai_vs_human_aesthetic_ch.png)

*Figure 3. Comparison of AI and human aesthetic judgment*

![beauty enhancement spectrum](img/fig_beauty_enhancement_spectrum_ch.png)

*Figure 4. Beauty enhancement degree continuum*

![isp style clustering](img/fig_isp_style_clustering_ch.png)

*Figure 5. ISP style clustering distribution*

---

## References

- Adams, A. (1948). *The Negative*. Little, Brown and Company.
- Adams, A. (1981). *The Print*. New York Graphic Society.
- Cartier-Bresson, H. (1952). *The Decisive Moment* (*Images à la Sauvette*). Simon & Schuster / Éditions Verve.
- VSCO (2019). *Community Impact Report*. vsco.co/about.
- Fujifilm Corporation (2023). *X Series Film Simulation: A Color Philosophy*. Fujifilm X-Series whitepaper. [community-verified at fujixweekly.com]
- Apple Inc. (2022). *iPhone 14 Photographic Styles: Technical Overview*. developer.apple.com.
- Apple Inc. (2024). *iPhone 16 — Photographic Styles Redesign*. apple.com/iphone-16.
- Kirstain, Y., Polyak, A., Singer, U. et al. (2023). *Pick-a-Pic: An Open Dataset of User Preferences for Text-to-Image Generation*. NeurIPS 2023. arXiv:2305.01569.
- Xu, J., Liu, X., Wu, Y. et al. (2023). *ImageReward: Learning and Evaluating Human Preferences for Text-to-Image Generation*. NeurIPS 2023. arXiv:2304.05977.
- Sony Group (2025). *Language-based Color ISP Tuning*. CIC 2025. arXiv:2509.10765.
- Huang, X., & Belongie, S. (2017). *Arbitrary Style Transfer in Real-time with Adaptive Instance Normalization*. ICCV 2017.
- Afifi, M. et al. (2019). *When Color Constancy Goes Wrong: Correcting Improperly White-Balanced Images*. CVPR 2019.
- Hu, Y., He, H., Xu, C. et al. (2018). *Exposure: A White-Box Photo Post-Processing Framework*. ACM TOG 2018.
- Murray, N., Marchesotti, L., & Perronnin, F. (2012). *AVA: A Large-Scale Database for Aesthetic Visual Analysis*. CVPR 2012.
- Talebi, H., & Milanfar, P. (2018). *NIMA: Neural Image Assessment*. IEEE Transactions on Image Processing 2018. arXiv:1709.05424.
- Wang, J., Chan, K. C. K., & Loy, C. C. (2023). *Exploring CLIP for Assessing the Look and Feel of Images (CLIP-IQA)*. AAAI 2023. arXiv:2207.12396.
- Fang, Y., Zhu, H., Zeng, Y., Ma, K., & Wang, Z. (2020). *Perceptual Quality Assessment of Smartphone Photography*. CVPR 2020. (SPAQ dataset)
- Kong, S., Shen, X., Lin, Z., Mech, R., & Fowlkes, C. (2016). *Photo Aesthetics Ranking Network with Attributes and Content Adaptation*. ECCV 2016. (AADB dataset)
- Apple Inc. (2024). *Generative Clean Up and Remove Distractions — iOS 18 Photos*. developer.apple.com.
- Samsung Electronics (2024). *Galaxy AI: Generative Edit Technical Overview*. news.samsung.com.
- Giudice, O. et al. (2024). *Towards Robust Evaluation of Aesthetic and Photographic Quality*. Computational Aesthetics, Wiley.
- EMOVIS Research Team (2025). *EMOVIS: Emotion-Optimized Image Processing*. arXiv:2605.03131.
- Reinhard, E., Stark, M., Shirley, P., & Ferwerda, J. (2002). *Photographic Tone Reproduction for Digital Images*. SIGGRAPH 2002.
- IJsselsteijn, W. et al. (2005). *Perceptual factors in the appreciation of still photographic images*. Journal of Imaging Science and Technology.
