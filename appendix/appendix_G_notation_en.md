# Appendix G — Notation and Symbols | 符号表

> This glossary lists all symbols used consistently throughout the handbook.
> Where a symbol has context-specific variants, the context is noted.

---

## G.1 Image and Signal Notation

| Symbol | Meaning | Context / Notes |
|--------|---------|----------------|
| I(x,y) | Pixel intensity at spatial position (x,y) | General grayscale image; x = column, y = row |
| I[m,n] | Discrete pixel at row m, column n | Discrete notation; equivalent to I(x,y) with integer coordinates |
| I(x,y,c) | Pixel intensity at position (x,y), channel c | Color image; c ∈ {R,G,B} or c ∈ {0,1,2} |
| R, G, B | Red, Green, Blue channel values | Normalized to [0,1] unless stated otherwise |
| R', G', B' | Gamma-encoded (nonlinear) RGB values | After gamma encoding; cf. IEC 61966-2-1 sRGB |
| Y, Cb, Cr | Luma and chroma channels (YCbCr) | After CSC from RGB; used in video output |
| H(x,y) | Bayer CFA raw image (mosaiced) | Pre-demosaic; single-channel, alternating RGGB pattern |
| I_out | Pipeline output image | After all ISP stages |
| I_ref | Reference (ground truth) image | For IQA computation |
| I_hat | Estimated or reconstructed image | Output of a restoration algorithm |
| W, H | Image width (columns) and height (rows) | In pixels |
| N | Total pixel count = W × H | |

---

## G.2 Noise and Sensor Parameters

| Symbol | Meaning | Context / Notes |
|--------|---------|----------------|
| σ² | Noise variance | Ch04: σ²(I) = αI + β (signal-dependent) |
| σ | Noise standard deviation | σ = √σ² |
| α | Photon transfer coefficient (shot noise slope) | Ch04: slope of PTC; units: DN²/DN |
| β | Read noise variance (floor) | Ch04: PTC y-intercept; σ²_read |
| σ_shot | Shot noise std dev | σ_shot = √(αI) |
| σ_read | Read noise std dev | Gaussian, signal-independent |
| λ | Poisson parameter (mean photon count) | Ch04: λ = QE × Φ × t_exp |
| QE | Quantum efficiency | Fraction of photons converted to electrons (0–1) |
| FWC | Full well capacity | Maximum electrons per pixel before saturation; units: e⁻ |
| DN | Digital Number | Raw pixel value in ADC counts |
| ADU | Analog-to-Digital Unit | Equivalent to DN |
| K | System gain | e⁻/DN; conversion between electrons and ADC counts |
| DR | Dynamic range | DR = 20·log₁₀(FWC / σ_read) [dB] |
| SNR | Signal-to-Noise Ratio | SNR = I / σ(I) (linear); or 20·log₁₀(I/σ) [dB] |

---

## G.3 Color Science

| Symbol | Meaning | Context / Notes |
|--------|---------|----------------|
| X, Y, Z | CIE 1931 XYZ tristimulus values | Device-independent color space |
| x, y | CIE chromaticity coordinates | x = X/(X+Y+Z), y = Y/(X+Y+Z) |
| L*, a*, b* | CIE L*a*b* (CIELAB) values | Perceptually uniform; L*: lightness, a*: red-green, b*: yellow-blue |
| T_CCT | Correlated Color Temperature | Units: Kelvin (K); D65 ≈ 6500K, D50 ≈ 5000K, A ≈ 2856K |
| ΔE | Color difference | Generic; specify version: ΔE_ab (CIE76), ΔE₀₀ (CIEDE2000) |
| ΔE₀₀ | CIEDE2000 color difference | Perceptually uniform; ΔE₀₀ < 1: imperceptible; > 3: visible |
| CCM | Color Correction Matrix | 3×3 matrix mapping sensor RGB to reference color space |
| M_CCM | Color correction matrix (explicit) | **y** = M_CCM · **x**_sensor |
| g_R, g_G, g_B | White balance gain per channel | Ch22: multiply raw channels to achieve neutral gray |
| D65, D50, A, TL84 | Standard illuminants | D65: daylight 6500K; A: incandescent 2856K; TL84: fluorescent |
| Δu'v' | Chromaticity distance in u'v' | Used for CCT computation and AWB error |
| W_R, W_G, W_B | White point (per channel) | Reference neutral for AWB |

---

## G.4 Optics and Lens

| Symbol | Meaning | Context / Notes |
|--------|---------|----------------|
| f | Focal length | Units: mm |
| f/# | F-number (aperture) | f/# = f / D_aperture; higher = narrower aperture |
| N | F-number (alternative notation) | Same as f/#; N = f/D |
| λ | Wavelength of light | Units: nm; visible: 380–700 nm |
| NA | Numerical aperture | NA = n · sin(θ_max); n = refractive index |
| d_Airy | Airy disk diameter | d = 2.44 · λ · f/# (for circular aperture) |
| PSF(x,y) | Point Spread Function | Spatial impulse response of optical system |
| OTF(f_x,f_y) | Optical Transfer Function | OTF = FT{PSF} |
| MTF(f) | Modulation Transfer Function | MTF(f) = |OTF(f)| |
| MTF50 | Spatial frequency at MTF = 50% | Key sharpness metric; units: cycles/pixel or lp/mm |
| MTF50P | MTF50 as percentage of Nyquist | MTF50P = MTF50 / f_Nyquist × 100% |
| ESF(x) | Edge Spread Function | Derivative = LSF; used for MTF measurement |
| LSF(x) | Line Spread Function | LSF = dESF/dx; 1D PSF slice |
| k₁, k₂ | Radial distortion coefficients | Brown-Conrady model: x_d = x_u(1 + k₁r² + k₂r⁴ + ...) |
| p₁, p₂ | Tangential distortion coefficients | Brown-Conrady model |
| EV | Exposure Value | EV = log₂(N²/t); N=f/#, t=shutter time [s] |
| LV | Luminance Value | Scene luminance in cd/m² |

---

## G.5 ISP Pipeline Modules (Abbreviations)

| Symbol | Meaning | Chapter |
|--------|---------|---------|
| CFA | Color Filter Array | Part 1 Ch06, Part 2 Ch02 |
| OB | Optical Black | Part 2 Ch01 |
| BLC | Black Level Correction | Part 2 Ch01 |
| PDPC | Phase Detection Defect Pixel Correction | Part 2 Ch01 |
| DPC | Defect Pixel Correction (generic) | Part 2 Ch01 |
| LSC | Lens Shading Correction | Part 2 Ch08 |
| CCM | Color Correction Matrix | Part 2 Ch06 |
| AWB | Auto White Balance | Part 2 Ch05 |
| TM | Tone Mapping | Part 2 Ch07 |
| HDR | High Dynamic Range | Part 2 Ch10 |
| CSC | Color Space Conversion | Part 2 Ch09 |
| NR | Noise Reduction | Part 2 Ch03 |
| TNR | Temporal Noise Reduction | Part 2 Ch03 |
| SNR | Spatial Noise Reduction | Part 2 Ch03 |
| USM | Unsharp Masking | Part 2 Ch04 |
| AE | Auto Exposure | Part 4 Ch01–02 |
| AF | Auto Focus | Part 4 Ch03 |
| 3A | Auto Exposure + Auto Focus + Auto White Balance | Part 4 Ch01–03 |

---

## G.6 Image Quality Metrics

| Symbol | Meaning | Formula / Notes |
|--------|---------|----------------|
| PSNR | Peak Signal-to-Noise Ratio | PSNR = 10·log₁₀(MAX²/MSE) [dB] |
| MSE | Mean Squared Error | MSE = (1/N)·Σ(I_hat - I_ref)² |
| RMSE | Root Mean Squared Error | RMSE = √MSE |
| SSIM | Structural Similarity Index | SSIM ∈ [0,1]; higher = better; 1 = identical |
| MS-SSIM | Multi-Scale SSIM | Computed at multiple image scales |
| LPIPS | Learned Perceptual Image Patch Similarity | Lower = better; deep feature distance |
| MOS | Mean Opinion Score | Subjective quality score, typically 1–5 scale |
| DMOS | Differential MOS | MOS of distorted relative to reference |
| SRCC | Spearman Rank Correlation Coefficient | Rank-based correlation ∈ [−1,1]; measures monotonicity |
| PLCC | Pearson Linear Correlation Coefficient | Linear correlation ∈ [−1,1] |
| RMSE_p | RMSE between predicted and subjective scores | IQA model evaluation metric |
| BRISQUE | Blind/Referenceless Image Spatial Quality Evaluator | NR-IQA; lower = better |
| NIQE | Natural Image Quality Evaluator | NR-IQA; lower = better |
| NRQM | No-Reference Quality Metric | NR-IQA |
| FID | Fréchet Inception Distance | GAN generation quality; lower = better |

---

## G.7 Deep Learning and Optimization

| Symbol | Meaning | Context / Notes |
|--------|---------|----------------|
| θ | Model parameters | Weights of a neural network |
| L(θ) | Loss function | Scalar; minimized during training |
| η | Learning rate | Gradient descent step size |
| ∇_θ L | Gradient of loss w.r.t. parameters | Used in gradient descent update |
| **W** | Weight matrix (neural network layer) | |
| **b** | Bias vector | |
| σ(·) | Activation function | E.g., ReLU, Sigmoid (context-dependent; not noise σ) |
| φ(·) | Feature extractor (perceptual loss) | Typically VGG or ResNet features |
| G(·) | Generator (GAN) | Maps input to output image |
| D(·) | Discriminator (GAN) | Binary classifier: real vs. generated |
| N_params | Number of model parameters | Model complexity measure |
| FLOPs | Floating Point Operations | Computational cost measure |
| MACs | Multiply-Accumulate Operations | Common equivalent to FLOPs/2 |

---

## G.8 Mathematical Notation

| Symbol | Meaning |
|--------|---------|
| ∈ | Element of (set membership) |
| ∀ | For all |
| ∃ | There exists |
| ≈ | Approximately equal |
| ∝ | Proportional to |
| argmin | Argument of the minimum |
| argmax | Argument of the maximum |
| Σ | Summation |
| Π | Product |
| ‖·‖ | Norm (subscript specifies type: ‖·‖₁, ‖·‖₂, ‖·‖_F) |
| ⊗ | Convolution (or element-wise product, context-dependent) |
| * | Convolution operator (signal processing context) |
| ·ᵀ | Transpose |
| ·⁻¹ | Matrix inverse |
| ·⁺ | Moore-Penrose pseudoinverse |
| E[·] | Expected value |
| Var[·] | Variance |
| Cov[·,·] | Covariance |
| P(·) | Probability |
| p(·) | Probability density function |
| FT{·} | Fourier Transform |
| IFT{·} | Inverse Fourier Transform |
| ℝ | Real numbers |
| ℝⁿ | n-dimensional real vector space |
| ℝ^{m×n} | m×n real matrix space |

---

## G.9 Disambiguation Notes

Several symbols are reused in different contexts within the handbook. The intended meaning is always clear from context, but key ambiguities are:

| Symbol | Context 1 | Context 2 |
|--------|-----------|-----------|
| σ | Noise standard deviation (Ch04) | Activation function in neural networks (Part 3) |
| λ | Poisson noise parameter / mean photon count (Ch04) | Wavelength of light (Ch02) / regularization parameter (optimization) |
| G | Gray channel in CFA (Ch18–Ch19) | Generator network (Part 3 GAN) |
| f | Focal length (Ch02) | Spatial frequency in MTF (Part 2 Ch04) / function name |
| N | F-number (Ch02) | Number of samples / images in a dataset |
| W | Image width | Weight matrix in neural networks |
| `SNR` | Signal-to-Noise Ratio (general, Part 1, Ch04, Part 2) vs. Spatial Noise Reduction (ISP pipeline abbreviation, Appendix G, Section G.5) | Use context: measurement context = ratio; pipeline stage = reduction |
