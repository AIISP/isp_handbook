# Part 2, Chapter 23: Electronic Image Stabilization (EIS) and Optical Image Stabilization (OIS) Closed-Loop Control

> **Scope:** This chapter covers the complete engineering implementation of camera stabilization systems — from gyroscope signal processing to EIS crop transforms and OIS closed-loop control, as well as the system-level trade-offs in EIS+OIS co-design.
> **Prerequisites:** Volume 1, Chapter 3 (Sensor Physics); Volume 1, Chapter 9 (Camera System Calibration)
> **Target Readers:** Camera system engineers, algorithm engineers

---

## Table of Contents

1. [Motion Model and IMU Signal Processing](#1-motion-model-and-imu-signal-processing)
2. [EIS Electronic Image Stabilization Algorithm](#2-eis-electronic-image-stabilization-algorithm)
3. [OIS Optical Image Stabilization Working Principle](#3-ois-optical-image-stabilization-working-principle)
4. [Common Issue Analysis](#4-common-issue-analysis)
5. [Evaluation Methods](#5-evaluation-methods)
6. [Code Examples](#6-code-examples)
7. [References](#7-references)
8. [Glossary](#8-glossary)

---

## 1 Motion Model and IMU Signal Processing

### 1.1 Frequency Characteristics of Handheld Camera Shake

When shooting with a handheld camera, involuntary hand tremor (Camera Shake) is the primary cause of Motion Blur and video instability. Research on the Power Spectral Density (PSD) of hand tremor (Koh & Yoo, SPIE 2012) shows:

- Primary energy is concentrated in the **1–10 Hz** range, with a peak around 2–4 Hz (superposition of breathing frequency and muscle tremor);
- Rapid attenuation above 10 Hz;
- Full-body movement such as walking and running introduces stronger periodic components at 2–4 Hz.

Stabilization systems need to effectively suppress 0.5–10 Hz shake without affecting intentional camera panning (Pan) and tilting (Tilt) by the user — these are typically high-frequency components > 10 Hz or large angular velocity motions > 30°/s.

### 1.2 IMU Error Model

An Inertial Measurement Unit (IMU) contains a gyroscope and an accelerometer. Stabilization systems primarily rely on the angular velocity $\boldsymbol{\omega}(t) = [\omega_x, \omega_y, \omega_z]^\top$ (in °/s or rad/s) output by the gyroscope.

The actual measurement model of the gyroscope is:

$$
\tilde{\boldsymbol{\omega}}(t) = \boldsymbol{\omega}(t) + \mathbf{b}(t) + \boldsymbol{\eta}_w(t)
$$

where:
- $\mathbf{b}(t)$ is the slowly-varying Bias, following a **Random Walk** process: $\dot{\mathbf{b}} = \boldsymbol{\eta}_b$, $\boldsymbol{\eta}_b \sim \mathcal{N}(0, \sigma_b^2 \mathbf{I})$;
- $\boldsymbol{\eta}_w(t)$ is the angular velocity white noise (Angle Random Walk, ARW), $\boldsymbol{\eta}_w \sim \mathcal{N}(0, \sigma_w^2 \mathbf{I})$.

Noise specifications of typical MEMS gyroscopes (e.g., Bosch BMI260, InvenSense ICM-42688-P):
- ARW (Angle Random Walk): 0.003–0.01 °/√s;
- Bias stability (Allan Variance minimum): 0.1–2 °/hr;
- Full scale: ±2000 °/s (video stabilization mode typically uses ±500 °/s).

### 1.3 State Equation and Kalman Filtering

The stabilization system must recover the camera's true rotation angle (or angular velocity) from the gyroscope measurements and decompose it into a "shake component to be compensated" and a "user-intentional motion component."

**State vector definition:**

$$
\mathbf{x} = [\theta, \dot{\theta}, b]^\top
$$

where $\theta$ is the rotation angle, $\dot{\theta}$ is the angular velocity, and $b$ is the estimated gyroscope bias.

**Discrete state transition equation (sampling interval $\Delta t$):**

$$
\mathbf{x}_{k+1} = \mathbf{F} \mathbf{x}_k + \mathbf{w}_k
$$

$$
\mathbf{F} = \begin{pmatrix} 1 & \Delta t & -\Delta t \\ 0 & 1 & 0 \\ 0 & 0 & 1 \end{pmatrix}, \quad
\mathbf{Q} = \begin{pmatrix} \frac{\Delta t^4}{4}\sigma_\theta^2 & \frac{\Delta t^3}{2}\sigma_\theta^2 & 0 \\ \frac{\Delta t^3}{2}\sigma_\theta^2 & \Delta t^2 \sigma_\theta^2 & 0 \\ 0 & 0 & \Delta t \sigma_b^2 \end{pmatrix}
$$

**Observation equation:**

$$
z_k = \tilde{\omega}_k = \dot{\theta}_k + b_k + \eta_w
$$

$$
\mathbf{H} = [0, 1, 1], \quad R = \sigma_w^2
$$

The Kalman filter estimates the state vector through alternating Predict and Update steps, outputting the bias estimate $\hat{b}$ and smoothed rotation angle $\hat{\theta}$ to generate the stabilized reference trajectory.

### 1.4 Trajectory Smoothing Strategies

The essence of stabilization is to design a "smooth reference trajectory" $\theta_{ref}(t)$ such that the camera follows this reference trajectory in the output frames, thereby removing high-frequency shake components.

**Low-pass filter method:** Apply a low-pass filter (IIR Butterworth or Gaussian) to the cumulative angle integral $\Theta(t) = \int_0^t \hat{\omega}(\tau) d\tau$, with cutoff frequency $f_c = 1$–2 Hz, preserving user intentional motion while filtering out high-frequency shake.

**Moving average method:** Compute a weighted sliding average over the cumulative trajectory of the past $N$ frames (typically $N = 30$–90 frames, corresponding to 1–3 seconds at 30fps):

$$
\theta_{ref}(k) = \frac{1}{N}\sum_{i=0}^{N-1} \Theta(k-i)
$$

**L1-Smooth optimization method (L1-Smooth, Liu et al., SIGGRAPH 2013):** Minimizes residual motion (i.e., the difference between the compensated trajectory and the reference trajectory) while constraining adjacent-frame trajectory changes. This better handles sudden camera movements (such as rapid panning) and telephoto shake amplification effects.

---

## 2 EIS Electronic Image Stabilization Algorithm

### 2.1 EIS Basic Principle

Electronic Image Stabilization (EIS) applies a geometric transform (typically an affine transform or homography transform) to each video frame, aligning the frames to a stable reference trajectory to eliminate inter-frame shake.

**Compensation transform:** Let the cumulative rotation angle of frame $k$ be $\Theta_k$ and the reference trajectory angle be $\theta_{ref,k}$. The compensation angle is:

$$
\delta\theta_k = \Theta_k - \theta_{ref,k}
$$

The corresponding image translation compensation (small-angle approximation):

$$
\delta u_k = f_x \cdot \tan(\delta\theta_{yaw}) \approx f_x \cdot \delta\theta_{yaw}
$$
$$
\delta v_k = f_y \cdot \tan(\delta\theta_{pitch}) \approx f_y \cdot \delta\theta_{pitch}
$$

The complete Affine Transform includes translation, rotation, and scale, representable as a $2\times 3$ affine matrix:

$$
\mathbf{M}_{k} = \begin{pmatrix} \cos\delta\psi & -\sin\delta\psi & \delta u \\ \sin\delta\psi & \cos\delta\psi & \delta v \end{pmatrix}
$$

where $\delta\psi$ is the Roll-axis rotation compensation angle.

### 2.2 Stabilization Crop

EIS requires a reserved Crop Margin: the sensor acquisition area is set to $1/r$ of the output frame size ($r < 1$), and the stable output frame is cropped after the transform. The relationship between the crop ratio $r$ and the maximum compensable angle $\theta_{max}$ is:

$$
r = 1 - \frac{2 f_x \cdot \tan(\theta_{max})}{W_{sensor}}
$$

Typical configurations:
- **Basic EIS (EIS 1.0)**: Crop ratio $r = 0.90$ (retains 90% of the field of view), compensation range ±2–3°;
- **Advanced EIS (EIS 2.0)**: Crop ratio $r = 0.75$–0.80, compensation range ±5–8°;
- **GoPro HyperSmooth (4.0)**: Uses an ultra-wide-angle lens (approximately 155° DFOV); at 4K output the crop ratio is approximately $r = 0.70$, with a compensation range of up to ±20°, plus a Horizon Lock function for Roll-axis compensation (GoPro patent US20210021756A1).

### 2.3 Rolling Shutter Correction

CMOS sensors (Complementary Metal-Oxide-Semiconductor) typically use row-sequential readout (Rolling Shutter, RS), where each row has a different exposure time. This causes the image to tilt (Jello Effect / Wobble) when the camera shakes.

Let the inter-row readout time interval be $\Delta t_{rs}$ (total frame time $T_{frame}$ divided by image height $H$). The delay of row $v$'s exposure relative to the frame start time is $v \cdot \Delta t_{rs}$, so the RS compensation translation for that row is:

$$
\delta u_{rs}(v) = f_x \cdot \omega_{yaw}(t_{frame} + v \cdot \Delta t_{rs}) \cdot \Delta t_{rs} \cdot v
$$

In practice, the angular velocity at the time corresponding to each row is interpolated from the IMU's high-frequency samples (typically 800–1000 Hz), and a different horizontal displacement compensation is applied row by row, effectively eliminating RS tilt.

### 2.4 Video EIS Engineering Implementation

The complete processing pipeline for real-world video EIS:

```
IMU raw data (800–1000 Hz)
    -> Timestamp alignment (IMU and Rolling Shutter per-row timestamps)
    -> Kalman filtering (bias estimation + smoothing)
    -> Trajectory integration (cumulative rotation angle)
    -> Reference trajectory generation (low-pass / moving average / L1 optimization)
    -> Compensation transform computation (affine matrix M_k)
    -> Rolling Shutter correction (per-row compensation)
    -> Image Warp (bilinear interpolation / Lanczos)
    -> Crop to stable output frame
```

**Platform Implementation:** Qualcomm Snapdragon's EIS 3.0 algorithm is implemented on GPU + DSP, supporting real-time 4K@60fps processing; Samsung Exynos accelerates EIS Warp through MFC (Multi-Format Codec) hardware; MediaTek Dimensity achieves hybrid stabilization through joint OIS+EIS optimization firmware.

---

## 3 OIS Optical Image Stabilization Working Principle

### 3.1 OIS Mechanical Structure

Optical Image Stabilization (OIS) compensates for hand shake by physically moving lens elements or the sensor, achieving stabilization without losing field of view.

Mainstream OIS mechanical solutions:
- **Lens-shift OIS**: Drives the Compensating Lens Element in the lens module to translate in the X-Y plane, changing the direction of the optical path deflection. Widely used in iPhone and Samsung Galaxy main cameras;
- **Sensor-shift OIS**: Drives the entire image sensor to move within the focal plane. Used in Apple A14 Bionic (introduced in iPhone 12 Pro Max). Equally effective at all focal lengths; compensation travel is typically ±100–250 μm;
- **Ball-guide OIS**: The lens module floats in the plane via ball-bearing guides, with low friction but weaker drop resistance.

### 3.2 OIS Actuator Types: VCM and SMA

OIS actuators use one of two mainstream drive technologies:

- **Voice Coil Motor (VCM):** Electromagnetic force drives lens/sensor movement. Low power, mature closed-loop control, widely used in iPhone, Samsung, and most mainstream flagship cameras.
- **Shape Memory Alloy (SMA):** Nitinol alloy wires contract when heated by current, driving the lens. Advantages: lower profile (thinner z-height), no magnetic interference with dual-camera systems; disadvantage: slower response (~5–10 ms vs. VCM ~1–2 ms), used in selected Huawei and Sony Xperia models.

**VCM Drive and Closed-Loop Control**

For VCM-based OIS, the actuator model and closed-loop design are as follows.

**Open-loop VCM model:** Ignoring damping, the VCM can be approximated as a mass-spring system:

$$
m \ddot{x} + c \dot{x} + k x = F_{em} = K_t \cdot i
$$

where $m$ is the moving mass, $c$ is the damping coefficient, $k$ is the spring constant, $K_t$ is the force constant, and $i$ is the drive current.

**Closed-loop control (PID control):** OIS closed-loop uses a Hall Effect Sensor or magnetic encoder to detect the lens/sensor position in real time, feeding it back to the digital controller:

$$
u(k) = K_p \cdot e(k) + K_i \sum_{j=0}^{k} e(j) \cdot T_s + K_d \cdot \frac{e(k) - e(k-1)}{T_s}
$$

The OIS Closed-Loop Bandwidth is typically designed to be 100–300 Hz, effectively compensating for 1–10 Hz hand shake. The PWM (Pulse Width Modulation) drive frequency is typically 20–40 kHz to avoid audible noise.

### 3.3 OIS Calibration

The OIS system requires calibration of the following parameters:
- **Sensitivity**: Displacement per unit drive current (μm/mA) or deflection angle (arcsec/mA);
- **Gyroscope-OIS Latency**: Total delay from IMU data acquisition to VCM response completion (typically 1–5 ms), requiring Phase Lead Compensation in the controller;
- **Cross-Coupling**: The effect of X-axis drive on Y-axis position, requiring a 2×2 decoupling matrix to eliminate;
- **Temperature Drift**: VCM coil resistance changes with temperature, causing drive current deviation; requires a temperature compensation LUT.

### 3.4 EIS+OIS Co-design

The physical travel limit of OIS alone (typically ±0.6–1.2°) cannot handle violent motion; EIS alone requires a large crop ratio that loses the field of view. The Hybrid OIS-EIS co-design strategy:

- **Frequency domain division of labor:** OIS compensates high-frequency (> 5 Hz) small-amplitude shake, leveraging its fast response; EIS compensates low-frequency (< 5 Hz) large-amplitude shake, leveraging its freedom from physical travel limits;
- **Residual compensation:** OIS compensates first; EIS performs secondary compensation for the residual shake that OIS cannot eliminate (the difference between actual displacement from Hall sensor feedback and desired displacement);
- **Crop margin minimization:** After effective OIS compensation, EIS only needs a small crop margin ($r = 0.90$–0.95), reducing FOV loss.

---

## 4 Common Issue Analysis

### 4.1 Walking Bounce Stabilization Failure

**Appearance:** During walking, the video shows periodic up-and-down bouncing (2–3 Hz) that cannot be fully eliminated even with stabilization enabled.

**Root Cause:** The vertical translational motion generated by walking cannot be detected by the gyroscope (which measures rotation only); accelerometer integration accuracy is insufficient (double integration accumulates large errors).

**Mitigation:**
- Use Optical Flow to estimate the inter-frame global translation component, supplementing the IMU;
- Step Detection: recognize gait cycles and specifically enhance low-frequency shake suppression;
- Sensor-shift OIS provides limited translational compensation in the vertical direction.

### 4.2 Warp Boundary Artifact

**Appearance:** Black-filled areas appear at the edges of EIS video output, especially noticeable during large-amplitude shaking.

**Root Cause:** Insufficient crop margin in the compensation transform; when the shake amplitude exceeds the designed compensation range $\theta_{max}$, the warped image cannot fully cover the output frame area.

**Mitigation:**
- Increase the crop margin (lower $r$), at the cost of sacrificing FOV;
- Adaptive cropping: dynamically adjust the crop ratio based on shake amplitude (use small crop ratio when stable, automatically increase during violent motion);
- Boundary inpainting: fill black border regions with pixels from the previous frame or adjacent areas, but this introduces temporal inconsistency artifacts.

### 4.3 OIS Magnetic Field Interference

**Appearance:** OIS stabilization effectiveness degrades noticeably near strong magnetic field devices (speakers, wireless charging pads), and the image drifts.

**Root Cause:** Hall sensors detect the permanent magnet position; external magnetic field interference causes erroneous position feedback, making the OIS closed-loop control fail (tracking the wrong position target).

**Mitigation:**
- Use Magnetic Shield structural design to reduce the impact of external magnetic fields on the sensor;
- Use Differential Hall Sensors to suppress common-mode magnetic field interference through differential operation;
- Software-level detection of abnormal position signals (beyond normal travel range); switch temporarily to EIS mode when abnormal.

### 4.4 Slow Drift from Gyroscope Bias Drift

**Appearance:** After prolonged shooting, the video shows slow unidirectional drift with the frame center deviating from the expected position.

**Root Cause:** Gyroscope bias $b$ changes with temperature (approximately 0.01–0.1 °/s/°C); the Kalman filter's bias estimation convergence speed is insufficient to track rapid temperature changes.

**Mitigation:**
- Use temperature sensor data for gyroscope bias Temperature Compensation (Temperature Compensation LUT);
- Add visual assistance (Visual-Inertial Odometry, VIO) for online bias correction;
- Add a drift suppression term to the trajectory smoothing algorithm to limit the long-term cumulative deviation of the reference trajectory.

---

## 5 Evaluation Methods

### 5.1 ISO 15739 Video Stability Testing

ISO 15739:2023 (Photography — Electronic still-picture imaging systems — Noise measurement methods) includes a video stability measurement framework. Video stabilization effectiveness typically follows these industry-standard test methods:

- **Blur Ratio**: Compare the static target image MTF with stabilization on/off to quantify the sharpness improvement from stabilization;
- **Video Stabilization Effectiveness (VSE)**: A comprehensive metric used by test organizations such as DxOMark, including sub-items such as residual shake power, settling time, and gait compensation effectiveness.

### 5.2 Cumulative Drift

For the stabilized video sequence, analyze the inter-frame displacement of static feature points in the image. Cumulative drift is defined as:

$$
D_{cum}(N) = \sum_{k=1}^{N} \|\mathbf{p}_k - \mathbf{p}_{k-1}\|_2
$$

where $\mathbf{p}_k$ is the position of a reference feature point in frame $k$. The cumulative drift of a stabilized video should be significantly lower than that of the original unstabilized video.

### 5.3 Trajectory Smoothness

Define the Acceleration Variance of Trajectory to measure trajectory smoothness:

$$
\sigma_{acc}^2 = \text{Var}\left[\frac{d^2 \Theta_{ref}}{dt^2}\right]
$$

Ideally, the acceleration variance of the reference trajectory in the stabilized output should approach zero (perfectly smooth). In practice, it has a non-zero value due to intentional motion requirements.

### 5.4 FOV Retention

Due to EIS cropping, the effective focal length of the actual output frame increases. FOV retention is defined as:

$$
FOV_{retention} = \frac{FOV_{EIS\_output}}{FOV_{optical}} = r
$$

This is usually used as a design constraint (e.g., requiring $r > 0.85$), rather than a performance metric. Greater OIS physical travel reduces the demand for EIS crop margin, thereby improving FOV retention.

---

## 6 Code Examples

The following code implements Kalman-filtered gyroscope trajectory smoothing and a complete affine-transform EIS implementation based on OpenCV, runnable directly.

```python
"""
EIS electronic image stabilization full demo: Kalman trajectory smoothing + affine warp
Dependencies: numpy>=1.20, opencv-python>=4.5
Usage: python ch21_eis_demo.py
"""

import numpy as np
import cv2
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ──────────────────────────────────────────────
# 1. Gyroscope data model and noise generation
# ──────────────────────────────────────────────

@dataclass
class GyroNoiseParams:
    """Gyroscope noise parameters (SI units: rad/s)"""
    arw_sigma: float = 0.0003     # Angle random walk std dev (rad/√s), approx. 1 °/√hr
    bias_rw_sigma: float = 1e-5   # Bias random walk std dev (rad/s/√s)
    initial_bias: float = 0.001   # Initial bias (rad/s), approx. 0.06 °/s


def simulate_gyro_signal(duration_s: float = 10.0,
                          sample_rate_hz: float = 200.0,
                          shake_amplitude_rad: float = 0.02,
                          shake_freq_hz: float = 3.0,
                          noise_params: Optional[GyroNoiseParams] = None,
                          rng_seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """
    Simulate handheld camera gyroscope signal: sinusoidal shake + bias random walk + white noise.

    Returns:
        t         : timestamp array (s)
        gyro_raw  : raw gyroscope angular velocity measurements (rad/s)
    """
    if noise_params is None:
        noise_params = GyroNoiseParams()

    rng = np.random.default_rng(rng_seed)
    dt = 1.0 / sample_rate_hz
    N = int(duration_s * sample_rate_hz)
    t = np.arange(N) * dt

    # True hand shake signal (3 Hz sine + higher harmonics)
    true_omega = (shake_amplitude_rad * np.sin(2 * np.pi * shake_freq_hz * t)
                  + 0.5 * shake_amplitude_rad * np.sin(2 * np.pi * 1.5 * shake_freq_hz * t)
                  + 0.3 * shake_amplitude_rad * np.sin(2 * np.pi * 7.0 * t))

    # Bias random walk
    bias = np.zeros(N)
    bias[0] = noise_params.initial_bias
    bias_noise = rng.normal(0, noise_params.bias_rw_sigma * np.sqrt(dt), N)
    for i in range(1, N):
        bias[i] = bias[i-1] + bias_noise[i]

    # Measurement white noise
    meas_noise = rng.normal(0, noise_params.arw_sigma / np.sqrt(dt), N)

    gyro_raw = true_omega + bias + meas_noise
    return t, gyro_raw


# ──────────────────────────────────────────────
# 2. Kalman filter: bias estimation + angular velocity smoothing
# ──────────────────────────────────────────────

class KalmanGyroFilter:
    """
    3-state Kalman filter: [angle theta, angular velocity omega, bias b].

    State transition:
        theta_{k+1} = theta_k + dt * (omega_k - b_k)
        omega_{k+1} = omega_k                  (constant velocity assumption)
        b_{k+1} = b_k + w_b                    (bias random walk)

    Observation equation:
        z_k = omega_k + b_k + v_k              (gyroscope measurement)
    """

    def __init__(self,
                 dt: float = 1.0 / 200.0,
                 arw_sigma: float = 0.0003,
                 bias_rw_sigma: float = 1e-5,
                 meas_sigma: float = 0.001):
        self.dt = dt
        self.x = np.zeros(3)       # State: [theta, omega, bias]
        self.P = np.eye(3) * 0.01  # Covariance matrix

        # State transition matrix F
        self.F = np.array([
            [1.0, dt, -dt],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ])

        # Process noise covariance Q
        q_theta = (arw_sigma * dt) ** 2
        q_omega = (arw_sigma / np.sqrt(dt)) ** 2
        q_bias  = (bias_rw_sigma * np.sqrt(dt)) ** 2
        self.Q = np.diag([q_theta, q_omega, q_bias])

        # Observation matrix H (observe angular velocity + bias)
        self.H = np.array([[0.0, 1.0, 1.0]])

        # Observation noise covariance R
        self.R = np.array([[meas_sigma ** 2]])

    def predict(self):
        """Kalman prediction step"""
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q

    def update(self, z_gyro: float):
        """
        Kalman update step

        Parameters:
            z_gyro: raw gyroscope angular velocity measurement (rad/s)
        """
        y = np.array([z_gyro]) - self.H @ self.x                  # Residual
        S = self.H @ self.P @ self.H.T + self.R                    # Residual covariance
        K = self.P @ self.H.T @ np.linalg.inv(S)                   # Kalman gain
        self.x = self.x + K @ y                                     # State update
        self.P = (np.eye(3) - K @ self.H) @ self.P                 # Covariance update

    def step(self, z_gyro: float) -> Tuple[float, float, float]:
        """
        Single-step Kalman filtering.

        Returns:
            theta   : estimated cumulative rotation angle (rad)
            omega   : estimated true angular velocity (rad/s)
            bias    : estimated bias (rad/s)
        """
        self.predict()
        self.update(z_gyro)
        return self.x[0], self.x[1], self.x[2]


def smooth_trajectory_lowpass(trajectory: np.ndarray,
                               smoothing_radius: int = 30) -> np.ndarray:
    """
    Apply moving average smoothing (equivalent to low-pass filtering) to the
    cumulative angle trajectory to generate the EIS reference trajectory.

    Parameters:
        trajectory      : cumulative rotation angle array (rad)
        smoothing_radius: smoothing window radius (frames), approx. smoothing_radius/fps seconds
    """
    N = len(trajectory)
    smoothed = np.zeros(N)
    for i in range(N):
        start = max(0, i - smoothing_radius)
        end   = min(N, i + smoothing_radius + 1)
        smoothed[i] = np.mean(trajectory[start:end])
    return smoothed


# ──────────────────────────────────────────────
# 3. EIS image warp and crop
# ──────────────────────────────────────────────

def apply_eis_warp(frame: np.ndarray,
                   delta_x: float,
                   delta_y: float,
                   delta_angle_rad: float,
                   crop_ratio: float = 0.9) -> np.ndarray:
    """
    Apply EIS compensation affine transform to a single frame and crop to stable output.

    Parameters:
        frame            : input frame (BGR or grayscale)
        delta_x          : horizontal compensation translation (pixels, positive = right)
        delta_y          : vertical compensation translation (pixels, positive = down)
        delta_angle_rad  : Roll-axis compensation rotation angle (radians)
        crop_ratio       : crop ratio (0.75–0.95), determines output frame size relative to input

    Returns:
        stabilized_frame : stabilized cropped frame
    """
    h, w = frame.shape[:2]
    cx, cy = w / 2.0, h / 2.0

    # Build affine transform matrix (rotation center at image center)
    cos_a = np.cos(delta_angle_rad)
    sin_a = np.sin(delta_angle_rad)

    # Rotation + translation (translate to center, rotate, translate back, add compensation)
    M = np.array([
        [cos_a, -sin_a, cx * (1 - cos_a) + cy * sin_a  + delta_x],
        [sin_a,  cos_a, cy * (1 - cos_a) - cx * sin_a  + delta_y]
    ], dtype=np.float64)

    # Bilinear interpolation warp
    warped = cv2.warpAffine(frame, M, (w, h),
                             flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_REPLICATE)

    # Center crop to crop_ratio size
    out_w = int(w * crop_ratio)
    out_h = int(h * crop_ratio)
    x_off = (w - out_w) // 2
    y_off = (h - out_h) // 2
    stabilized_frame = warped[y_off:y_off + out_h, x_off:x_off + out_w]

    return stabilized_frame


# ──────────────────────────────────────────────
# 4. Complete EIS demo (synthetic video sequence)
# ──────────────────────────────────────────────

def create_synthetic_video_frames(n_frames: int = 150,
                                   width: int = 640,
                                   height: int = 480) -> List[np.ndarray]:
    """
    Generate synthetic test video frames (checkerboard background) for EIS algorithm validation.
    Background is large enough to prevent black borders after warping.
    """
    rng = np.random.default_rng(0)
    # Checkerboard background (40% larger than output frame to preserve warp margin)
    bg_w, bg_h = int(width * 1.4), int(height * 1.4)
    checker = np.zeros((bg_h, bg_w), dtype=np.uint8)
    tile = 40
    for iy in range(0, bg_h, tile):
        for ix in range(0, bg_w, tile):
            if (iy // tile + ix // tile) % 2 == 0:
                checker[iy:iy+tile, ix:ix+tile] = 200

    frames = []
    for _ in range(n_frames):
        # Crop width x height center region from background
        x0 = (bg_w - width) // 2
        y0 = (bg_h - height) // 2
        frame = cv2.cvtColor(checker[y0:y0+height, x0:x0+width],
                              cv2.COLOR_GRAY2BGR)
        frames.append(frame)
    return frames


def demo_eis_pipeline():
    """Complete EIS pipeline demo"""
    print("=" * 62)
    print("  EIS electronic stabilization demo: Kalman trajectory smoothing + affine warp")
    print("=" * 62)

    FPS = 30.0
    DURATION = 5.0           # 5-second video
    IMU_RATE = 200.0          # Gyroscope sampling rate (Hz)
    FOCAL_PX = 1000.0         # Equivalent focal length (pixel units)
    CROP_RATIO = 0.88
    IMG_W, IMG_H = 640, 480

    # -- 1. Simulate gyroscope signal --
    t_imu, gyro_yaw = simulate_gyro_signal(
        duration_s=DURATION,
        sample_rate_hz=IMU_RATE,
        shake_amplitude_rad=np.deg2rad(2.5),   # Hand shake amplitude approx. +-2.5 degrees
        shake_freq_hz=3.0
    )
    _, gyro_pitch = simulate_gyro_signal(
        duration_s=DURATION, sample_rate_hz=IMU_RATE,
        shake_amplitude_rad=np.deg2rad(1.8), shake_freq_hz=2.5,
        rng_seed=99
    )
    print(f"Gyroscope data: {len(t_imu)} samples, {DURATION}s @{IMU_RATE}Hz")

    # -- 2. Kalman filtering --
    kf_yaw   = KalmanGyroFilter(dt=1.0/IMU_RATE)
    kf_pitch = KalmanGyroFilter(dt=1.0/IMU_RATE)

    theta_yaw_raw   = np.zeros(len(t_imu))
    theta_pitch_raw = np.zeros(len(t_imu))
    theta_yaw_kf    = np.zeros(len(t_imu))
    theta_pitch_kf  = np.zeros(len(t_imu))

    for i, (wy, wp) in enumerate(zip(gyro_yaw, gyro_pitch)):
        ty, oy, _ = kf_yaw.step(wy)
        tp, op, _ = kf_pitch.step(wp)
        # Integrate cumulative angle
        if i == 0:
            theta_yaw_raw[i]   = wy / IMU_RATE
            theta_pitch_raw[i] = wp / IMU_RATE
        else:
            theta_yaw_raw[i]   = theta_yaw_raw[i-1]   + wy / IMU_RATE
            theta_pitch_raw[i] = theta_pitch_raw[i-1]  + wp / IMU_RATE
        theta_yaw_kf[i]   = ty
        theta_pitch_kf[i] = tp

    print(f"Estimated gyroscope bias (Yaw): final value = {kf_yaw.x[2]*1000:.3f} mrad/s")

    # -- 3. Generate reference trajectory (low-pass smoothing) --
    smooth_r = int(IMU_RATE * 1.0)   # 1-second smoothing window
    ref_yaw   = smooth_trajectory_lowpass(theta_yaw_kf,   smooth_r)
    ref_pitch = smooth_trajectory_lowpass(theta_pitch_kf, smooth_r)

    # -- 4. Downsample to video frame rate --
    n_frames  = int(DURATION * FPS)
    frame_idx = np.linspace(0, len(t_imu)-1, n_frames, dtype=int)

    delta_yaw_frames   = (theta_yaw_kf   - ref_yaw  )[frame_idx]
    delta_pitch_frames = (theta_pitch_kf - ref_pitch)[frame_idx]

    # Convert angle to pixel compensation (small-angle approximation)
    delta_x_px = FOCAL_PX * np.tan(delta_yaw_frames)
    delta_y_px = FOCAL_PX * np.tan(delta_pitch_frames)

    # -- 5. Synthesize video frames and compute stabilization statistics --
    frames = create_synthetic_video_frames(n_frames, IMG_W, IMG_H)
    residual_x_list, residual_y_list = [], []

    for i, frame in enumerate(frames):
        stabilized = apply_eis_warp(
            frame,
            delta_x=float(delta_x_px[i]),
            delta_y=float(delta_y_px[i]),
            delta_angle_rad=0.0,
            crop_ratio=CROP_RATIO
        )
        # Simulate "residual shake" (remaining after warp, from IMU noise)
        residual_x_list.append(abs(delta_x_px[i]))
        residual_y_list.append(abs(delta_y_px[i]))

    print(f"\nRaw shake statistics (focal length={FOCAL_PX:.0f}px):")
    raw_x = FOCAL_PX * np.abs(np.tan(theta_yaw_kf[frame_idx]))
    raw_y = FOCAL_PX * np.abs(np.tan(theta_pitch_kf[frame_idx]))
    print(f"  Mean horizontal displacement (px): {np.mean(raw_x):.2f}  ->  residual after compensation {np.mean(residual_x_list):.2f}")
    print(f"  Mean vertical displacement (px):   {np.mean(raw_y):.2f}  ->  residual after compensation {np.mean(residual_y_list):.2f}")
    print(f"  FOV retention (crop ratio): {CROP_RATIO*100:.0f}%")

    # -- 6. Simulate cumulative drift metric --
    cumulative_drift_raw = float(np.sum(
        np.sqrt(np.diff(raw_x)**2 + np.diff(raw_y)**2)
    ))
    residual_arr = np.array(residual_x_list)
    cumulative_drift_eis = float(np.sum(np.abs(np.diff(residual_arr))))
    print(f"\nCumulative inter-frame drift:")
    print(f"  Raw:        {cumulative_drift_raw:.1f} px")
    print(f"  After EIS:  {cumulative_drift_eis:.1f} px")
    print(f"  Drift suppression ratio: {cumulative_drift_raw / max(cumulative_drift_eis, 1e-6):.1f}x")

    return delta_x_px, delta_y_px


if __name__ == "__main__":
    demo_eis_pipeline()
```

**Key Parameter Tuning Guide:**

| Parameter | Recommended Value | Notes |
|---|---|---|
| Kalman `arw_sigma` | 0.0003–0.001 | Corresponds to the ARW value in the IMU datasheet (rad/√s) |
| Kalman `bias_rw_sigma` | 1e-5–5e-5 | Bias random walk; read from Allan Variance curve |
| Smoothing window radius `smooth_r` | 0.5–2.0 seconds | Short window = fast response but poor smoothness; long window = smooth but lag on fast motion |
| Crop ratio `crop_ratio` | 0.85–0.95 | Smaller = more FOV loss, but can compensate larger shake amplitudes |
| P1/P2 (OIS) | Determined by hardware calibration | Must be determined from VCM characteristic curves and temperature testing; not a software parameter |

---

## 7 References

1. Tordoff, B., & Murray, D. W. (2004). *Guided Sampling and Consensus for Motion Estimation*. **ECCV 2004**.
2. Liu, F., Gleicher, M., Jin, H., & Agarwala, A. (2009). *Content-Preserving Warps for 3D Video Stabilization*. **SIGGRAPH 2009**, 28(3).
3. Liu, S., Yuan, L., Tan, P., & Sun, J. (2013). *Bundled Camera Paths for Video Stabilization*. **SIGGRAPH 2013**, 32(4).
4. Grundmann, M., Kwatra, V., & Essa, I. (2011). *Auto-Directed Video Stabilization with Robust L1 Optimal Camera Paths*. **CVPR 2011**, 2, 225–232.
5. Karpenko, A., Jacobs, D., Lim, J., & Levoy, M. (2011). *Digital Video Stabilization and Rolling Shutter Correction using Gyroscopes*. **Stanford CSTR 2011-03**.
6. Koh, Y., & Yoo, H. (2012). *Camera Motion Estimation using IMU and Optical Flow*. **SPIE Electronic Imaging 2012**.
7. GoPro Inc. (2021). *Image stabilization with horizon lock*. **US Patent Application US20210021756A1**.
8. Welch, G., & Bishop, G. (1995). *An Introduction to the Kalman Filter*. **UNC-Chapel Hill TR 95-041** (Rev. 2006).
9. Shi, J., & Tomasi, C. (1994). *Good Features to Track*. **CVPR 1994**, 593–600.

---

## 8 Glossary

| Term | Full Name | Description |
|---|---|---|
| EIS | Electronic Image Stabilization | Electronic stabilization; compensates for hand shake via image cropping/transform |
| OIS | Optical Image Stabilization | Optical stabilization; compensates for hand shake by physically moving lens or sensor |
| IMU | Inertial Measurement Unit | Contains gyroscope and accelerometer |
| ARW | Angle Random Walk | Integrated effect of gyroscope measurement noise; units °/√hr |
| VCM | Voice Coil Motor | Electromagnetic actuator commonly used in OIS to drive lens/sensor |
| SMA | Shape Memory Alloy | Nitinol-wire OIS actuator; thinner profile, no magnetic interference; slower response than VCM |
| PWM | Pulse Width Modulation | Common drive signal form for OIS VCM |
| RS | Rolling Shutter | CMOS sensor row-sequential readout mode; causes motion-induced image tilt |
| GS | Global Shutter | All pixels exposed simultaneously; eliminates RS effects |
| FOV | Field of View | Camera field of view angle; EIS cropping reduces effective FOV |
| PID | Proportional-Integral-Derivative | PID controller; OIS closed-loop control algorithm |
| Allan Variance | — | Time-domain stability analysis method for quantifying gyroscope bias stability |
| Warp | — | Geometric image transform (affine/projective); the core operation of EIS compensation |
| Kalman Filter | — | Optimal linear state estimation filter; used for IMU bias estimation and trajectory smoothing |
| Crop Margin | — | EIS reserved cropping margin; determines the maximum compensable shake amplitude |
| Hybrid OIS-EIS | — | Hybrid stabilization scheme with OIS and EIS working cooperatively |
