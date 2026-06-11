# Appendix A — Math Foundations | 数学基础

> This appendix provides a self-contained review of the mathematical tools used throughout the handbook.
> Each section follows the pattern: **Definition → Key Equations → ISP Application**.

---

## A.1 Linear Algebra

### A.1.1 Vectors and Matrices

**Definition.** A vector **v** ∈ ℝⁿ is an ordered n-tuple of real numbers. A matrix **A** ∈ ℝ^{m×n} maps vectors from ℝⁿ to ℝᵐ.

**Key operations:**

| Operation | Notation | ISP Use |
|-----------|----------|---------|
| Matrix-vector product | **y** = **A****x** | CCM: apply 3×3 color matrix to RGB triplet |
| Transpose | **A**ᵀ | Least-squares normal equations |
| Matrix inverse | **A**⁻¹ | Solving calibration systems |
| Frobenius norm | ‖**A**‖_F = √(Σᵢⱼ Aᵢⱼ²) | CCM fitting residual |

**ISP application — CCM (Part 2 Ch06):** The color correction matrix maps sensor RGB to reference XYZ:

```
[X]   [m11  m12  m13] [R_sensor]
[Y] = [m21  m22  m23] [G_sensor]
[Z]   [m31  m32  m33] [B_sensor]
```

### A.1.2 Eigendecomposition

**Definition.** For a symmetric matrix **A** ∈ ℝ^{n×n}, eigendecomposition yields:

```
A = Q Λ Qᵀ
```

where **Q** is orthogonal (eigenvectors as columns) and **Λ** = diag(λ₁, …, λₙ) contains eigenvalues.

**Key property:** λᵢ ≥ 0 for all i when **A** is positive semi-definite (PSD).

**ISP application — Principal Component Analysis for noise modeling (Ch04):** PCA via eigendecomposition of the covariance matrix identifies dominant noise directions in multi-channel sensor data.

### A.1.3 Singular Value Decomposition (SVD)

**Definition.** Any matrix **A** ∈ ℝ^{m×n} can be factored as:

```
A = U Σ Vᵀ
```

where **U** ∈ ℝ^{m×m} and **V** ∈ ℝ^{n×n} are orthogonal, and **Σ** = diag(σ₁, …, σᵣ) with σ₁ ≥ σ₂ ≥ … ≥ σᵣ ≥ 0.

**Low-rank approximation (Eckart-Young theorem):** The best rank-k approximation is:

```
A_k = Σᵢ₌₁ᵏ σᵢ uᵢ vᵢᵀ
```

**ISP applications:**
- **LSC fitting (Ch25):** SVD solves ill-conditioned least-squares for lens shading surface fitting.
- **CCM fitting (Ch23):** SVD-based pseudoinverse gives minimum-norm solution when the measurement matrix is rank-deficient.
- **Low-rank denoising:** Noise reduction by truncating small singular values.

### A.1.4 Norms and Distance Measures

| Norm | Formula | ISP Use |
|------|---------|---------|
| L1 | ‖**x**‖₁ = Σᵢ |xᵢ| | Sparse noise penalties |
| L2 (Euclidean) | ‖**x**‖₂ = √(Σᵢ xᵢ²) | RMSE, CCM residual |
| L∞ | max|xᵢ| | Worst-case error bounds |
| Frobenius | ‖**A**‖_F | Matrix fitting residuals |

**ΔE color difference (Ch05, Ch23):**

```
ΔE₀₀ = √[(ΔL*/k_L S_L)² + (ΔC*/k_C S_C)² + (ΔH*/k_H S_H)² + R_T(ΔC*/k_C S_C)(ΔH*/k_H S_H)]
```

---

## A.2 Probability and Statistics

### A.2.1 Probability Distributions

#### Poisson Distribution

**Definition.** A discrete distribution modeling counts of independent events:

```
P(X = k) = (λᵏ e⁻λ) / k!,    k = 0, 1, 2, ...
```

**Properties:** E[X] = λ, Var[X] = λ (mean equals variance).

**ISP application — Photon shot noise (Ch04):** The number of photoelectrons collected in a pixel follows Poisson statistics. At high photon counts, Poisson → Gaussian (central limit theorem).

```
σ²_shot = λ = I  (signal-dependent noise)
```

#### Gaussian (Normal) Distribution

**Definition.**

```
f(x; μ, σ²) = (1 / √(2πσ²)) exp(-(x-μ)² / 2σ²)
```

**Properties:** E[X] = μ, Var[X] = σ².

**ISP application — Read noise (Ch04):** Thermal read noise is well-modeled as zero-mean Gaussian:

```
σ²_total = σ²_shot + σ²_read = α·I + σ²_read
```

This is the Poisson-Gaussian noise model used for denoising calibration.

#### Heteroscedastic Gaussian (Signal-Dependent Variance)

The combined noise variance is signal-dependent:

```
σ²(I) = α·I + β
```

where α is the photon transfer coefficient and β is the read noise floor. See Ch04 §2 (Calibration) for PTC measurement.

### A.2.2 Bayesian Estimation

**Bayes' theorem:**

```
P(θ | x) = P(x | θ) · P(θ) / P(x)
```

- **Likelihood** P(x | θ): probability of observing data given parameters.
- **Prior** P(θ): prior belief about parameter distribution.
- **Posterior** P(θ | x): updated belief after observing data.

**MAP (Maximum A Posteriori) estimation:**

```
θ_MAP = argmax_θ log P(x | θ) + log P(θ)
```

**ISP application — Denoising (Ch20):** MAP denoising with Gaussian noise likelihood and total variation (TV) prior:

```
x̂ = argmin_x (1/2σ²)‖y - x‖² + λ·TV(x)
```

**ISP application — AWB (Ch22):** Bayesian color constancy estimates illuminant probability given observed image statistics and a prior over natural illuminants.

### A.2.3 Expectation and Variance

| Property | Formula |
|----------|---------|
| Linearity of expectation | E[aX + bY] = aE[X] + bE[Y] |
| Variance | Var[X] = E[X²] - (E[X])² |
| Covariance | Cov[X,Y] = E[(X-μX)(Y-μY)] |
| Covariance matrix | **Σ** = E[(**x**-**μ**)(**x**-**μ**)ᵀ] |

---

## A.3 Signal Processing

### A.3.1 Convolution

**Discrete convolution (2D):**

```
(f * g)[m,n] = Σₖ Σₗ f[k,l] · g[m-k, n-l]
```

**Key properties:**
- Commutativity: f * g = g * f
- Associativity: f * (g * h) = (f * g) * h
- Distributivity over addition: f * (g + h) = f*g + f*h

**ISP application — Sharpening (Ch21):** Unsharp masking uses:

```
I_sharp = I + α · (I - I * G_σ)
```

where G_σ is a Gaussian blur kernel.

**ISP application — Denoising (Ch20):** Linear spatial filters (box, Gaussian) are convolutions. Bilateral filter extends this to edge-preserving filtering:

```
I_bilateral[p] = (1/W_p) Σ_q G_s(‖p-q‖) · G_r(|I[p]-I[q]|) · I[q]
```

### A.3.2 Fourier Transform

**Continuous Fourier transform:**

```
F(ω) = ∫ f(t) e^{-jωt} dt
f(t) = (1/2π) ∫ F(ω) e^{jωt} dω
```

**Discrete Fourier Transform (DFT):**

```
X[k] = Σₙ₌₀^{N-1} x[n] e^{-j2πkn/N}
```

**Convolution theorem:** Convolution in spatial domain = multiplication in frequency domain:

```
F{f * g} = F{f} · F{g}
```

**2D DFT for images:**

```
F[u,v] = Σₘ Σₙ I[m,n] e^{-j2π(um/M + vn/N)}
```

**ISP applications:**
- **Sharpening (Ch21):** Frequency-domain view of high-frequency boosting.
- **LSC analysis (Ch25):** Detecting low-frequency vignetting components.
- **Demosaic aliasing analysis (Ch19):** CFA sampling creates aliasing at Nyquist, visible in frequency domain.

### A.3.3 Modulation Transfer Function (MTF)

**Definition.** MTF is the magnitude of the normalized Optical Transfer Function (OTF):

```
OTF(f) = FT{PSF}
MTF(f) = |OTF(f)|
```

where PSF (Point Spread Function) is the spatial impulse response of the optical/sensor system.

**Slanted-edge MTF measurement (ISO 12233):** Edge is tilted ~5° to provide sub-pixel sampling. The Edge Spread Function (ESF) is differentiated to get the Line Spread Function (LSF), then Fourier-transformed for MTF.

```
ESF(x) → diff → LSF(x) → FT → MTF(f)
```

**MTF50:** The spatial frequency at which MTF falls to 50% of peak. Key sharpness metric. See Ch21 §5 (Evaluation).

**ISP applications:**
- **Sharpening (Ch21):** Unsharp mask boosts MTF at mid-to-high frequencies.
- **Demosaic (Ch19):** Demosaic algorithm quality measured partly by MTF50 preservation.
- **Lens calibration (Ch02):** MTF50 measured at multiple field positions for lens characterization.

### A.3.4 Sampling and the Nyquist Theorem

**Nyquist-Shannon sampling theorem:** A bandlimited signal with maximum frequency f_max can be perfectly reconstructed from samples taken at rate f_s ≥ 2·f_max.

**ISP application — CFA demosaicing aliasing (Ch19):** The Bayer CFA samples R and B channels at half the spatial resolution of G. Aliasing occurs when scene spatial frequency exceeds the Nyquist limit of the undersampled channel. The optical anti-aliasing (OLPF) filter band-limits the signal before sampling.

---

## A.4 Optimization

### A.4.1 Least Squares

**Linear least squares:** Given overdetermined system **A****x** = **b** (m > n equations):

```
x̂ = argmin_x ‖Ax - b‖²
```

**Normal equations solution:**

```
x̂ = (AᵀA)⁻¹Aᵀb
```

**Pseudoinverse via SVD:** When **A** = **U**Σ**V**ᵀ:

```
x̂ = A⁺b = V Σ⁺ Uᵀ b
```

where Σ⁺ inverts only non-zero singular values. Numerically stable even for ill-conditioned systems.

**Weighted least squares:**

```
x̂ = argmin_x (Ax - b)ᵀ W (Ax - b)
   = (AᵀWA)⁻¹AᵀWb
```

**ISP application — CCM fitting (Ch23):** Fit a 3×3 matrix to N color patch measurements:

```
M̂ = argmin_M Σᵢ wᵢ · ΔE²(M · x_i^{sensor}, x_i^{reference})
```

Weights wᵢ can encode patch reliability or perceptual importance.

**ISP application — LSC fitting (Ch25):** Fit a smooth polynomial surface to vignetting measurements from a flat-field image:

```
G(x,y) = Σₖ aₖ φₖ(x,y)
â = argmin_a ‖Φa - g‖²
```

where φₖ are polynomial basis functions and g are per-pixel gain measurements.

### A.4.2 Regularization

**Tikhonov (L2) regularization:**

```
x̂ = argmin_x ‖Ax - b‖² + λ‖x‖²
   = (AᵀA + λI)⁻¹Aᵀb
```

**L1 regularization (LASSO):**

```
x̂ = argmin_x ‖Ax - b‖² + λ‖x‖₁
```

Promotes sparsity; solved via iterative soft thresholding (ISTA/FISTA).

**Total Variation (TV) regularization:**

```
TV(x) = Σᵢⱼ √((∂x/∂i)² + (∂x/∂j)²)
```

Promotes piecewise-smooth solutions; preserves edges while suppressing noise.

**ISP application:** TV regularization used in denoising (Ch20), demosaic (Ch19), and HDR tone mapping (Ch24).

### A.4.3 Gradient Descent and Deep Learning Training

**Gradient descent update rule:**

```
θ_{t+1} = θ_t - η · ∇_θ L(θ_t)
```

**Stochastic Gradient Descent (SGD):** Uses mini-batch gradient estimate:

```
θ_{t+1} = θ_t - η · ∇_θ L(θ_t; x_batch)
```

**Adam optimizer:**

```
m_t = β₁ m_{t-1} + (1-β₁) g_t          (first moment)
v_t = β₂ v_{t-1} + (1-β₂) g_t²         (second moment)
m̂_t = m_t/(1-β₁ᵗ),  v̂_t = v_t/(1-β₂ᵗ)  (bias correction)
θ_{t+1} = θ_t - η · m̂_t / (√v̂_t + ε)
```

Default: β₁=0.9, β₂=0.999, ε=10⁻⁸.

**Loss functions for DL ISP (Ch34–Ch35):**

| Loss | Formula | Application |
|------|---------|-------------|
| L1 loss | Σ|ŷ-y| | Robust to outliers |
| L2 / MSE | Σ(ŷ-y)² | Minimizes PSNR |
| SSIM loss | 1 - SSIM(ŷ,y) | Structural similarity |
| Perceptual loss | ‖φ(ŷ)-φ(y)‖² | VGG feature matching |
| GAN adversarial | -log D(ŷ) | Perceptual sharpness |

**ISP application — DL ISP training (Part 3):** End-to-end denoising and restoration networks are trained with combined losses, typically L1 + perceptual + optionally GAN.

### A.4.4 Optimization Convergence Conditions

| Condition | Statement |
|-----------|-----------|
| First-order (necessary) | ∇L(θ*) = 0 |
| Second-order (sufficient) | ∇²L(θ*) ≻ 0 (positive definite Hessian) |
| Convexity | f(λx + (1-λ)y) ≤ λf(x) + (1-λ)f(y) |

Linear least squares with full-rank **A** has a unique global minimum. Most DL training problems are non-convex; convergence to local minima is generally sufficient in practice.

---

## A.5 Quick Reference Summary

| Mathematical Tool | Key Equation | ISP Module |
|-------------------|-------------|-----------|
| Matrix product | y = Ax | CCM (Ch23) |
| SVD pseudoinverse | x̂ = A⁺b | CCM, LSC fitting |
| Poisson noise | Var[X] = E[X] = λ | Noise model (Ch04) |
| MAP denoising | argmin ‖y-x‖² + λR(x) | Denoising (Ch20) |
| 2D convolution | (f*g)[m,n] | Sharpening (Ch21) |
| Fourier MTF | MTF(f) = |FT{LSF}| | Sharpening, lens (Ch02, Ch21) |
| Least squares | x̂ = (AᵀA)⁻¹Aᵀb | CCM, LSC (Ch23, Ch25) |
| Gradient descent | θ ← θ - η∇L | DL ISP (Part 3) |
| ΔE₀₀ | Perceptual color error | CCM eval (Ch23) |
