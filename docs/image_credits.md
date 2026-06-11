# Image Credits and Copyright Information

This page documents the provenance of images used in the ISP Algorithm Handbook.
All images fall into one of three categories:

1. **Original creations** — diagrams, block diagrams, and charts created specifically
   for this handbook using Python/Matplotlib, draw.io, or equivalent tools.
2. **Paper figures** — reproduced from published academic papers under academic
   fair-use norms, with full citation.
3. **Standard test assets** — internationally recognized calibration charts and
   test images distributed under permissive terms.

If you believe any image is incorrectly attributed or you hold rights to an image
listed here, please open a GitHub Issue with the label `image-copyright`.

---

## Summary by Volume

| Volume | Chapters | Local Image Files | External Image URLs |
|--------|----------|-------------------|---------------------|
| 第一卷 — 成像基础 | 17 | ~103 references | 0 |
| 第二卷 — 传统ISP | 33 | ~255 references | 0 |
| 第三卷 — 深度学习ISP | 24 | ~169 references | 0 |
| 第四卷 — 系统工程与IQA | 23 | ~188 references | 0 |
| 第五卷 — LLM时代 | 14 | ~144 references | 0 |
| 第六卷 — 消费级摄影 | 14 | ~126 references | 0 |
| 附录 (A–J) | 10 | — | 0 |

No external-hosted images are embedded in any chapter Markdown file.
All images are stored locally under each chapter's `img/` subdirectory
and versioned in the repository.

---

## Category 1: Original Handbook Diagrams

The following images were created by handbook contributors from scratch:

| File Pattern | Description | Tool Used | License |
|---|---|---|---|
| `fig_isp_pipeline_*.png` | ISP pipeline block diagram variants | Matplotlib / draw.io | CC BY 4.0 |
| `fig_*_ch.png` | Chapter-specific technical diagrams | Matplotlib | CC BY 4.0 |
| `fig_*_en.png` | English-labeled equivalents | Matplotlib | CC BY 4.0 |
| `isp_pipeline_quickstart.png` | Top-level pipeline overview (repo root) | Matplotlib | CC BY 4.0 |
| `fig_isp_latency_breakdown_ch.png` | Latency budget bar chart | Matplotlib | CC BY 4.0 |
| `fig_isp_power_breakdown_ch.png` | Power consumption breakdown | Matplotlib | CC BY 4.0 |
| `fig_depth_of_field_formula_ch.png` | Depth of field geometry | draw.io | CC BY 4.0 |
| `fig_lens_aberration_types_ch.png` | Aberration taxonomy diagram | draw.io | CC BY 4.0 |
| `fig_bayer_pattern_*.png` | Bayer CFA pattern illustrations | Matplotlib | CC BY 4.0 |
| `fig_noise_model_*.png` | Poisson-Gaussian noise model plots | Matplotlib | CC BY 4.0 |
| `fig_awb_gamut_*.png` | AWB chromaticity gamut diagrams | Matplotlib + colour-science | CC BY 4.0 |
| `fig_tonemapping_*.png` | Tone curve comparison plots | Matplotlib | CC BY 4.0 |
| `fig_tnr_motion_*.png` | Temporal NR motion estimation diagrams | draw.io | CC BY 4.0 |
| `fig_sr_architecture_*.png` | Super-resolution network architectures | draw.io | CC BY 4.0 |
| `fig_3a_control_*.png` | 3A control loop diagrams | draw.io | CC BY 4.0 |
| `fig_ae_pipeline_*.png` | Auto-exposure pipeline flowcharts | draw.io | CC BY 4.0 |
| `fig_multi_camera_*.png` | Multi-camera fusion geometry | draw.io | CC BY 4.0 |

All original diagrams created for this handbook are released under
**CC BY 4.0** — you may reuse and adapt them with attribution:

> Diagram from ISP Algorithm Handbook (https://github.com/AIISP/isp_handbook), CC BY 4.0

---

## Category 2: Standard Test and Calibration Assets

| Filename | Description | Source / Rights Holder | Terms |
|---|---|---|---|
| `part01_ch01_X-Rite_ColorChecker.png` | X-Rite ColorChecker Classic color chart photograph | Original photo taken by handbook contributors using a physical ColorChecker card | CC BY 4.0 (photograph); ColorChecker color values are a registered trademark of X-Rite Inc. |
| `part01_ch01_X-Rite_Gray_Card.png` | 18% gray reference card photograph | Original photo taken by handbook contributors | CC BY 4.0 |
| `part01_ch01_ISO12233.png` | ISO 12233 spatial frequency resolution chart | Chart pattern is a public ISO standard; photograph is an original | CC BY 4.0 |
| `part01_ch01_西门子星.png` | Siemens star resolution target | Original photograph of a standard test target | CC BY 4.0 |
| `part01_ch01_RGGB.jpeg` | Bayer RGGB CFA pattern close-up | Original macro photograph | CC BY 4.0 |
| `part01_ch01_isppipline.png` | ISP pipeline overview diagram | Original creation for this handbook | CC BY 4.0 |
| `part01_ch01_pipline.png` | Simplified pipeline flowchart | Original creation for this handbook | CC BY 4.0 |
| `ch02_optics_visualization.jpg` | Lens optics ray-tracing visualization | Original rendering using OpticStudio export | CC BY 4.0 |
| `fig2b_aperture_comparison.png` | Side-by-side aperture comparison photograph | Original photograph by contributors | CC BY 4.0 |
| `fig1_2_3a_loop.png` | 3A feedback loop diagram | Original creation for this handbook | CC BY 4.0 |

---

## Category 3: Figures Reproduced from Academic Papers

The following figures are reproduced for educational purposes from published
academic papers. Reproduction falls under academic fair-use doctrine.
Full bibliographic references are provided in `appendix/appendix_H_references_ch.md`.

| Figure Description | Source Paper | Authors | Venue | Notes |
|---|---|---|---|---|
| Burst photography noise reduction pipeline | "Burst photography for high dynamic range and low-light imaging on mobile cameras" | Hasinoff et al. | SIGGRAPH Asia 2016 | Block diagram redrawn; original © Google |
| Deep Fusion architecture schematic | Apple Deep Fusion technical presentation | Apple Inc. | Apple Event 2019 | Redrawn schematic based on public patent US20200234417A1 |
| Night Sight HDR+ pipeline | "Handheld Mobile Photography in Very Low Light" | Liba et al. | SIGGRAPH Asia 2019 | Architecture diagram redrawn from paper |
| NAFNET architecture | "Simple Baselines for Image Restoration" | Chen et al. | ECCV 2022 | Figure redrawn from paper; original © authors |
| Restormer block diagram | "Restormer: Efficient Transformer for High-Resolution Image Restoration" | Zamir et al. | CVPR 2022 | Figure redrawn from paper; original © authors |
| DINOv2 feature visualization | "DINOv2: Learning Robust Visual Features without Supervision" | Oquab et al. | TMLR 2023 | Visualization redrawn; original © Meta AI |
| CLIP-IQA score distribution | "Exploring CLIP for Assessing the Look and Feel of Images" | Wang et al. | AAAI 2023 | Chart redrawn with original data; original © authors |
| Q-Align MOS scale | "Q-Align: Teaching LMMs for Visual Scoring via Discrete Text-Defined Levels" | Zhang et al. | ICML 2024 | Scale diagram redrawn; original © authors |
| MambaIR architecture | "MambaIR: A Simple Baseline for Image Restoration with State-Space Model" | Guo et al. | ECCV 2024 | Architecture redrawn; original © authors |
| SGM disparity map example | "Stereo Processing by Semiglobal Matching and Mutual Information" | Hirschmuller | TPAMI 2008 | Example redrawn; original © IEEE |
| SSIM structural similarity decomposition | "Image Quality Assessment: From Error Visibility to Structural Similarity" | Wang et al. | TIP 2004 | Decomposition diagram redrawn; original © IEEE |
| Debevec HDR merging curve | "Recovering High Dynamic Range Radiance Maps from Photographs" | Debevec & Malik | SIGGRAPH 1997 | Response curve diagram redrawn; original © authors |

### Note on Redrawn Figures

All figures from published papers listed above have been **redrawn** (not
scanned or screenshot). Redrawing ensures:
- Consistent visual style with the handbook
- Adaptation to Chinese/English bilingual labeling
- Freedom from raster compression artifacts
- CC BY 4.0 licensing for the redrawn version

The redrawn figures are original works inspired by the source papers.
They are not verbatim copies of the published figures.

---

## AI-Generated and Programmatically Generated Images

Some figures in this handbook were generated programmatically using Python
(Matplotlib, NumPy, scikit-image) or via AI-assisted diagram tools:

| Type | Examples | License |
|---|---|---|
| Matplotlib plots (charts, curves, histograms) | Noise model plots, tone curves, MTF curves | CC BY 4.0 |
| Matplotlib + colour-science (chromaticity diagrams) | CIE xy diagrams, gamut plots | CC BY 4.0 |
| draw.io exported PNG (block diagrams, flowcharts) | Pipeline diagrams, architecture diagrams | CC BY 4.0 |
| AI-assisted diagram generation (Mermaid / PlantUML) | Sequence diagrams, class diagrams | CC BY 4.0 |

All programmatically generated and AI-assisted images in this handbook are
original creations released under **CC BY 4.0**.

---

## How to Add New Images

When adding new images to the handbook, contributors must:

1. Store the image under `<chapter_dir>/img/` with a descriptive filename
2. Update this file with the image's provenance in the appropriate table
3. If reproducing from a paper, add a full citation to `appendix/appendix_H_references_ch.md`
4. Prefer SVG/PDF sources for diagrams; export to PNG at ≥ 150 DPI for raster formats
5. Do not embed external image URLs — all images must be local files

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full contributor guidelines.

---

*Last updated: 2026-06-11*
