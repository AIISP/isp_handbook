# Part 1, Chapter 09: Camera Calibration

> **Pipeline position:** Pre-processing; feeds into LSC, CCM, and 3D vision
> **Prerequisites:** Chapter 2 (Optics), Chapter 3 (Sensor Physics)
> **Reader path:** Algorithm Engineer, System Designer

---

## §1 Theory

### 1.1 Camera Imaging Model

Camera calibration is fundamentally about determining the transformation that maps 3D points in the real world to 2D pixel coordinates on the sensor. The most widely used model is the **Pinhole Camera Model**, which abstracts the camera as an ideal small aperture through which light travels in straight lines, ignoring lens thickness and aberrations.

> **Model assumptions vs. physical reality:** The pinhole model is an idealized mathematical framework that defines the goal of geometric correction. A smartphone lens is in practice a multi-element thick-lens system with finite aperture, aberrations, chief ray angle variation, and sensor packaging effects — it is not truly a "pinhole." However, for moderate field-of-view angles (FoV < 90°) and under the single-center-projection approximation, the pinhole model combined with a distortion model is sufficient to meet engineering accuracy requirements. **The LDC/GDC module in an ISP is essentially an inverse mapping that "restores" the distorted image captured by the real lens back to an ideal image consistent with the pinhole model.** For ultra-wide-angle (FoV > 110°) and fisheye lenses, the error from a pure pinhole + Brown distortion model rises significantly; specialized fisheye projection models such as Kannala-Brandt are typically used instead (see §1.3).

The entire imaging process can be decomposed into three levels of coordinate-system transformation:

1. **World coordinate system → Camera coordinate system** (extrinsics, describing camera pose)
2. **Camera coordinate system → Image plane coordinate system** (projection, describing perspective scaling)
3. **Image plane coordinate system → Pixel coordinate system** (intrinsics, describing physical sensor parameters)

Introducing **Homogeneous Coordinates** allows these three steps to be expressed compactly as a chain of matrix multiplications. Let a 3D point in the world coordinate system be $\mathbf{X}_w = [X, Y, Z, 1]^T$ and its corresponding pixel coordinate be $\mathbf{u} = [u, v, 1]^T$; then:

$$
s \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}
= \underbrace{\begin{bmatrix} f_x & s & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix}}_{\mathbf{K}}
\underbrace{\begin{bmatrix} \mathbf{R} & \mathbf{t} \end{bmatrix}}_{[\mathbf{R}|\mathbf{t}]}
\begin{bmatrix} X \\ Y \\ Z \\ 1 \end{bmatrix}
$$

Here $s$ is a scale factor (which can be normalized away in pixel coordinates), $\mathbf{K}$ is the **Intrinsic Matrix**, and $[\mathbf{R}|\mathbf{t}]$ are the **Extrinsic Parameters**.

**Projection from the camera coordinate system to the image plane:** Given a point $(X_c, Y_c, Z_c)$ in the camera coordinate system and focal length $f$, the perspective projection yields normalized image-plane coordinates:

$$
x = \frac{X_c}{Z_c}, \quad y = \frac{Y_c}{Z_c}
$$

This step loses depth information and is irreversible.

### 1.2 Intrinsic Matrix K

The intrinsic matrix $\mathbf{K}$ contains five parameters:

$$
\mathbf{K} = \begin{bmatrix} f_x & s & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix}
$$

Physical meaning of each parameter:

- **$f_x, f_y$ (focal length in pixels):** Obtained by dividing the focal length $f$ (mm) by the pixel pitch $p_x, p_y$ (mm/pixel). If the sensor pixels are square, $f_x = f_y$; in smartphone sensors, however, slight manufacturing differences can cause a small discrepancy (typically less than 1‰).
- **$c_x, c_y$ (principal point):** The intersection of the optical axis with the sensor plane; theoretically at the image center $(W/2, H/2)$, but in practice it may be offset by several to a dozen pixels due to lens assembly eccentricity.
- **$s$ (skew parameter):** Describes how far the row and column pixel axes deviate from perpendicularity. Modern CMOS sensors have nearly rectangular pixels, so $s \approx 0$ and it is typically fixed at 0 during calibration.

In practice, typical values of $f_x, f_y$ for a smartphone wide-angle lens are roughly 1000–2200 pixels, and for a telephoto lens they can exceed 5000 pixels (using a 12 MP, 4032×3024 sensor as reference).

### 1.3 Distortion Models

Real lenses are not ideal pinholes; they exhibit **Lens Distortion**. Without distortion correction, straight lines appear curved in the image, introducing systematic errors into downstream 3D reconstruction and AR alignment.

**Radial Distortion:** Caused by uneven lens curvature, distributed symmetrically along the radial direction. Pincushion distortion has $k > 0$; barrel distortion has $k < 0$.

$$
x' = x(1 + k_1 r^2 + k_2 r^4 + k_3 r^6)
$$
$$
y' = y(1 + k_1 r^2 + k_2 r^4 + k_3 r^6)
$$

where $r^2 = x^2 + y^2$, $(x, y)$ are the normalized image-plane coordinates, $(x', y')$ are the coordinates after applying distortion, and $k_1, k_2, k_3$ are the radial distortion coefficients.

**Tangential Distortion:** Caused by imperfect parallelism between the lens and the sensor plane (lens assembly tilt).

$$
x' = x + 2p_1 xy + p_2(r^2 + 2x^2)
$$
$$
y' = y + p_1(r^2 + 2y^2) + 2p_2 xy
$$

$p_1, p_2$ are the tangential distortion coefficients, typically one order of magnitude smaller than $k_1$.

The complete distortion vector is $\mathbf{d} = [k_1, k_2, p_1, p_2, k_3]$ (OpenCV default order). For smartphone lenses, **radial distortion is by far the dominant term**, especially for ultra-wide-angle lenses; tangential distortion is secondary; the higher-order coefficient $k_3$ is non-negligible for ultra-wide-angle lenses.

**Thin Prism Distortion:** Beyond the basic Brown-Conrady terms, high-precision applications (multi-camera alignment, SLAM) that have stringent requirements on lens eccentricity and tilt also need thin prism terms $s_1, s_2, s_3, s_4$:

$$x' = x + s_1(r^2 + 2x^2) + s_2 \cdot r^2, \quad y' = y + s_3(r^2 + 2y^2) + s_4 \cdot r^2$$

The thin prism terms describe asymmetric residuals caused by lens assembly eccentricity and tilt. Their magnitude is typically less than 0.1 pixel and can be ignored in single-camera photography, but they are non-negligible in stereo matching (dual/triple camera) and AR alignment. OpenCV's `CALIB_THIN_PRISM_MODEL` flag supports this parameter.

**Scaramuzza model for fisheye/wide-angle lenses:** When the field of view exceeds 120°, the traditional polynomial model is insufficiently accurate. The equidistant projection or Scaramuzza's polynomial catadioptric model is required instead. OpenCV's `fisheye` module implements the Kannala-Brandt model:

$$
r(\theta) = k_1\theta + k_2\theta^3 + k_3\theta^5 + k_4\theta^7
$$

where $\theta$ is the angle between the incident ray and the optical axis, and $r$ is the radial distance on the image plane.

> **Why only odd-degree terms?** The projection function $r(\theta)$ must be an odd function, satisfying $r(-\theta) = -r(\theta)$ (central symmetry: rays incident at angles $+\theta$ and $-\theta$ to the optical axis must project to symmetric positions on either side of the image center, at equal distances). The Taylor expansion of an odd function contains only odd-degree powers, so even-degree terms like $\theta^2$ and $\theta^4$ are physically forbidden — including them would break central symmetry.

### 1.4 Zhang's Calibration Method

The planar calibration target method proposed by Zhengyou Zhang in 2000 is the most widely used calibration algorithm in computer vision and is essentially ubiquitous in the field. Its core idea is as follows.

**Homography:** Since the calibration target is planar (set $Z=0$), the world coordinates degenerate to 2D $(X, Y)$. The mapping between the camera image of the target and the target plane is described by a $3\times3$ **homography matrix $\mathbf{H}$** (8 degrees of freedom):

$$
s\begin{bmatrix}u \\ v \\ 1\end{bmatrix} = \mathbf{H} \begin{bmatrix}X \\ Y \\ 1\end{bmatrix},\quad \mathbf{H} = \mathbf{K}[\mathbf{r}_1\ \mathbf{r}_2\ \mathbf{t}]
$$

where $\mathbf{r}_1, \mathbf{r}_2$ are the first two columns of the rotation matrix $\mathbf{R}$.

**Closed-form solution (Linear Initialization):** Using at least 4 point correspondences, the DLT (Direct Linear Transform) algorithm can solve for $\mathbf{H}$ linearly. Given $N$ images of the calibration target in different poses, there are $N$ homography matrices $\mathbf{H}_i$. Each $\mathbf{H}_i$ provides **2 linear constraints** on the intrinsic-related symmetric matrix $\mathbf{B} = \mathbf{K}^{-T}\mathbf{K}^{-1}$ (by exploiting orthogonality of the rotation matrix). $\mathbf{B}$ has 6 elements but only 5 degrees of freedom due to the overall scale ambiguity, so the **theoretical minimum number of images is $N \geq 3$** (yielding 6 constraints).

> ⚠️ **Theoretical minimum vs. engineering recommendation:** While 3 images are theoretically sufficient for a linear solution, this assumes noise-free conditions. In practice, corner detection errors, target flatness variations, and insufficient field-of-view coverage make results from 3 images highly unstable. **The engineering recommendation is to capture 10–20 images**, covering different distances (near/medium/far), different tilt angles (±30° or more), and with the target reaching all four corners of the image. Pose diversity is more important than sheer quantity.

**Nonlinear Refinement:** Starting from the closed-form solution as an initial estimate, the Levenberg-Marquardt algorithm minimizes the **Reprojection Error**:

$$
\min_{\mathbf{K}, \mathbf{d}, \{R_i, t_i\}} \sum_{i=1}^{N} \sum_{j=1}^{M} \left\| \mathbf{m}_{ij} - \hat{\mathbf{m}}(\mathbf{K}, \mathbf{d}, R_i, t_i, \mathbf{M}_j) \right\|^2
$$

$\mathbf{m}_{ij}$ is the detected coordinate of the $j$-th corner in the $i$-th image, $\hat{\mathbf{m}}$ is the predicted coordinate using the current parameters, and $\mathbf{M}_j$ is the 3D coordinate of the $j$-th corner on the calibration target.

### 1.5 Multi-Camera Stereo Calibration

In addition to the intrinsics of each individual camera, a stereo (or multi-camera) system must also calibrate the **extrinsics**: the rotation $\mathbf{R}$ and translation $\mathbf{t}$ between cameras, as well as the **Essential Matrix $\mathbf{E}$** and **Fundamental Matrix $\mathbf{F}$** that describe the epipolar geometry.

$$
\mathbf{E} = [\mathbf{t}]_\times \mathbf{R}, \quad \mathbf{F} = \mathbf{K}_2^{-T} \mathbf{E} \mathbf{K}_1^{-1}
$$

$[\mathbf{t}]_\times$ is the **skew-symmetric matrix** of the translation vector $\mathbf{t}$:

$$
[\mathbf{t}]_\times = \begin{bmatrix} 0 & -t_z & t_y \\ t_z & 0 & -t_x \\ -t_y & t_x & 0 \end{bmatrix}
$$

The rank of $\mathbf{E}$ is **2** (in the non-degenerate case, $\mathbf{t} \neq \mathbf{0}$) — this is a necessary algebraic condition for the essential matrix: $\det(\mathbf{E}) = 0$ and its two non-zero singular values are equal. Both $\mathbf{E}$ and $\mathbf{F}$ satisfy the **Epipolar Constraint**:

$$
\mathbf{m}_2^T \mathbf{F} \mathbf{m}_1 = 0
$$

The corresponding point of a point $\mathbf{m}_1$ in the left image must lie on a line (the epipolar line) in the right image. This is the theoretical basis for accelerating stereo matching.

After stereo calibration, **Stereo Rectification** is applied to align the scan lines of both cameras (so that corresponding points lie on the same horizontal row), reducing stereo matching from a 2D search to a 1D line scan and greatly reducing computational cost.

---

## §2 Calibration

### 2.1 Calibration Target Design

The choice of calibration target directly affects corner detection accuracy.

**Checkerboard:** The most classic option; the intersections of black and white squares are well-defined, and sub-pixel refinement is mature. The drawback is the need to manually determine orientation (there is a 90° rotational symmetry ambiguity), and black squares may saturate under intense illumination. Recommended square size: print resolution ≥ 300 DPI; square side length covering 3–5% of the sensor's field of view.

**ChArUco board:** A hybrid of a checkerboard and ArUco markers, with each square containing an ArUco marker with a unique ID. Even with partial occlusion, robust detection is possible and orientation is unambiguous — valid corners can be extracted without a complete view. This gives a clear advantage **in production line scenarios where partial occlusion or robotic automated handling is required**. The classic checkerboard has theoretically slightly better corner accuracy (no ArUco texture interference) and a mature, stable algorithm; in practice both options are used in production, with the choice depending on the specific occlusion risk and accuracy requirements.

**Circle grid:** Symmetric or asymmetric dot patterns; circle center localization accuracy exceeds that of corners (by fitting an ellipse centroid, achieving theoretically higher sub-pixel precision). The corresponding OpenCV function is `findCirclesGrid()`.

**Engineering notes:**
- The calibration target must be **rigid and flat**. Inkjet prints glued to cardboard introduce large errors; aluminum plate with baked enamel coating or glass panels are recommended (flatness < 0.1 mm).
- The square size must be known and precisely measured; errors directly affect the scale accuracy of calibration.
- In production line settings, an LED backlit transmission panel can be used for uniform brightness unaffected by ambient light.

### 2.2 Image Acquisition Requirements

This step is the critical bottleneck for calibration quality — no algorithm can compensate for a poor acquisition strategy.

| Requirement | Recommended practice |
|------|----------|
| Field-of-view coverage | Target corners must cover the entire image area (especially all four corners); do not concentrate in the center |
| Pose diversity | Tilt ±30°, several images at near/medium/far distances, total images ≥ 20 |
| Image sharpness | No motion blur; accurate focus; use a fixed mount for handheld shooting |
| Exposure | Avoid overexposure (no histogram saturation); ensure sufficient checkerboard black-white contrast |
| Number of images | 20–50; more is not always better; diversity matters more than quantity |

A common mistake in practice: all images are taken head-on at the same distance, making it impossible to decouple tangential distortion from focal length, causing the calibration result to diverge.

### 2.3 Corner Detection and Sub-pixel Refinement

OpenCV's `findChessboardCorners()` first uses fast corner detection to locate initial positions to approximately 1-pixel accuracy. Then `cornerSubPix()` performs **Sub-pixel Refinement**:

Within a small window, the gradient field near the corner is used to find the position where the gradient direction is orthogonal to the vector pointing toward the corner:

$$
\sum_{\mathbf{q} \in W} (\nabla I(\mathbf{q}) \cdot (\mathbf{q} - \hat{\mathbf{c}})) = 0
$$

This is essentially a least-squares problem and can achieve precision of 0.01–0.1 pixel.

```python
import cv2
import numpy as np

# Corner detection and sub-pixel refinement example
def detect_corners(img, pattern_size=(9, 6)):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    ret, corners = cv2.findChessboardCorners(
        gray, pattern_size,
        flags=cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
    )

    if ret:
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

    return ret, corners
```

### 2.4 Complete OpenCV calibrateCamera Workflow

```python
import cv2
import numpy as np
import glob
import os

def calibrate_camera(image_dir, pattern_size=(9, 6), square_size=25.0):
    """
    Complete camera calibration workflow
    pattern_size: number of inner corners (columns, rows)
    square_size: physical square size (mm)
    """
    # Prepare corner coordinates in world coordinate system (target plane Z=0)
    objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
    objp *= square_size  # multiply by actual physical size

    obj_points = []  # 3D points in world coordinate system
    img_points = []  # 2D points in image coordinate system

    images = glob.glob(os.path.join(image_dir, '*.jpg'))
    img_size = None

    for fname in images:
        img = cv2.imread(fname)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_size = gray.shape[::-1]  # (width, height)

        ret, corners = cv2.findChessboardCorners(gray, pattern_size)
        if ret:
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            obj_points.append(objp)
            img_points.append(corners_refined)

    print(f"Valid calibration images: {len(obj_points)} / {len(images)}")

    # Run calibration
    # cv2.CALIB_RATIONAL_MODEL uses rational distortion model (k4,k5,k6), suitable for wide-angle
    # cv2.CALIB_FIX_K3 fixes k3=0 to prevent overfitting if k3 is not needed
    flags = 0  # default: use k1,k2,p1,p2,k3

    rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        obj_points, img_points, img_size,
        None, None, flags=flags
    )

    print(f"RMS reprojection error: {rms:.4f} pixel")
    print(f"Intrinsic matrix K:\n{K}")
    print(f"Distortion coefficients dist: {dist.ravel()}")

    return K, dist, rvecs, tvecs, rms

def compute_reprojection_errors(obj_points, img_points, rvecs, tvecs, K, dist):
    """Compute per-image reprojection errors for quality analysis"""
    errors = []
    for i in range(len(obj_points)):
        proj_pts, _ = cv2.projectPoints(obj_points[i], rvecs[i], tvecs[i], K, dist)
        err = cv2.norm(img_points[i], proj_pts, cv2.NORM_L2) / len(proj_pts)
        errors.append(err)
    return errors
```

### 2.5 Calibration Quality Verification

**Reprojection Error** is the most direct indicator of calibration quality:

- **RMS < 0.3 pixel:** Excellent; suitable for precision measurement
- **RMS 0.3–0.5 pixel:** Good; meets most visual tasks
- **RMS 0.5–1.0 pixel:** Marginal; recapture recommended
- **RMS > 1.0 pixel:** Calibration failed; check acquisition quality or detection algorithm

Review the per-image error distribution: if a few images have unusually large errors (outliers), removing them and re-running calibration typically leads to significant improvement.

---

## §3 Tuning

### 3.1 Intrinsic Accuracy vs. Distortion Model Complexity Trade-off

More distortion coefficients theoretically give a more accurate fit, but also increase the risk of **overfitting**: the parameters absorb acquisition noise and generalize poorly to new images.

Engineering experience:

| Scenario | Recommended distortion model |
|------|------------|
| Smartphone main camera (FoV < 90°) | $k_1, k_2, p_1, p_2$ (4 parameters) |
| Smartphone ultra-wide (FoV 120°+) | $k_1, k_2, k_3, p_1, p_2$ or fisheye model |
| Industrial lens (low distortion) | $k_1, p_1, p_2$ (3 parameters) |
| Fisheye lens (FoV 180°+) | Kannala-Brandt (OpenCV fisheye) |

To decide whether $k_3$ is needed: calibrate with $k_1, k_2$ alone, then inspect the residuals in the four corner regions of the image. If there is a systematic bias larger than 0.5 pixel, the model lacks higher-order terms — add $k_3$.

```python
# Fix unused parameters to prevent overfitting
flags_conservative = (cv2.CALIB_FIX_K3 |    # fix k3=0
                      cv2.CALIB_FIX_K4 |    # fix k4=0
                      cv2.CALIB_FIX_K5 |    # fix k5=0
                      cv2.CALIB_ZERO_TANGENT_DIST)  # if tangential distortion is negligible
```

### 3.2 Engineering Practice for Mobile Camera Calibration

**Factory calibration** and **in-field calibration** follow different strategies:

- **Factory:** Controlled environment (standard light source, fixed mount, precision calibration target); target RMS < 0.3 pixel. Factory calibration results are typically written to the **EEPROM** inside the camera module (rewritable; each module stores its own intrinsics, distortion coefficients, initial white balance values, etc.), and are read by the ISP driver at power-on. In some designs, the data is written to the main board or an ISP firmware partition rather than the module EEPROM. **OTP/eFuse is generally used for one-time data such as sensor IDs and factory gain compensation — it is not appropriate for storing camera calibration parameters that may need to be updated after a repair.**
- **In-field calibration:** Key frames collected automatically during normal user shooting; background continuous optimization. Mainly used to compensate for temperature drift and mechanical shifts after a drop. Accuracy requirements are slightly lower; RMS < 0.5 pixel is acceptable.

**Unit-to-unit variation:** Across units of the same device model, $f_x, f_y$ typically vary by ±1%, principal point offset can reach ±10 pixels, and $k_1$ can vary by ±5%. Therefore every individual unit requires its own calibration and cannot share a single set of parameters.

**Occlusion and partial visibility:** Production lines may encounter partially occluded targets; ChArUco boards handle this better than checkerboards.

### 3.3 Handling Temperature and Focus-Distance Dependence

A lens's focal length drifts with temperature (thermal expansion and contraction). In extreme temperature environments (−20°C industrial or 70°C automotive), focal length variation can reach 0.5–2%, which is sufficient to affect precision measurement tasks.

**Approaches:**
1. Calibrate at multiple temperature points (e.g., −10°C, 25°C, 50°C) and build a $f(T)$ lookup table.
2. Embed a temperature sensor reading and interpolate at runtime.
3. Zoom cameras must be calibrated independently at each zoom level.

For zoom lenses, intrinsics are functions of the zoom position $l$: $f_x(l), f_y(l), c_x(l), c_y(l), \mathbf{d}(l)$. Typically a polynomial is fit to the calibrated values at each zoom step, and interpolation is used between zoom levels.

---

## §4 Artifacts

### 4.1 Geometric Distortion from Uncorrected Lens Distortion

The most common problem: straight lines appear curved in the image. Without distortion correction, the edges of buildings in ultra-wide-angle shots exhibit pronounced barrel bending; telephoto cameras may show pincushion distortion.

Typical downstream algorithm impacts:
- **Feature matching:** SIFT/ORB descriptors extracted from distorted images are inconsistent with those from corrected images, reducing match rate.
- **Depth estimation:** Stereo matching assumes row alignment (after stereo rectification), which depends on accurate distortion parameters; poor calibration results in large depth errors.
- **Augmented reality (AR):** Virtual objects overlaid on distorted images have perspective relationships inconsistent with reality, producing a "drift" effect.

After distortion correction, black invalid regions appear at the corners of the image (because the correction maps some pixels outside the original image boundary). Use `cv2.getOptimalNewCameraMatrix()` to crop appropriately.

### 4.2 Systematic Error from Insufficient Target Flatness

The calibration target is assumed to be a perfect plane ($Z=0$). If the target is warped, the world coordinates and actual 3D coordinates disagree, introducing systematic error.

**Quantitative estimate:** If the calibration target at a distance of 1000 mm has 1 mm of warpage, the effect on focal length is approximately $\Delta f / f \approx 1/1000 = 0.1\%$ — seemingly small, but already non-negligible for precision triangulation tasks requiring sub-millimeter accuracy.

**Detection method:** Measure the actual flatness of the calibration target with a surface plate or coordinate measuring machine (CMM); alternatively, capture multiple images at different rotational orientations — if residuals are systematically large in certain orientations, the target is warped.

### 4.3 Corner Detection Errors and Reprojection Error Anomalies

**False corners:** Due to overexposure, heavy noise, or insufficient depth of field, `findChessboardCorners()` may detect non-corner points or produce incorrectly ordered corners. Symptom: RMS error suddenly very large (>5 pixel); a scatter plot of the errors reveals one or two obvious outliers far from the cluster.

**Remedies:**
1. Visualize corner detection results image by image (using `drawChessboardCorners()`) and verify visually.
2. Compute the per-image RMS; discard images with RMS greater than 2× the median.
3. Adjust the `flags` parameter of `findChessboardCorners()` (`CALIB_CB_ADAPTIVE_THRESH` helps with overexposure).

**Principal point drift:** If the calibrated principal point $c_x, c_y$ deviates from the image center by more than 10% of the image dimension (e.g., for a 400×300 image with center at (200, 150), the principal point landing at (230, 150) is a 15% offset), the likely cause is insufficient pose diversity in the capture set.

---

## §5 Evaluation

### 5.1 Reprojection Error Statistics

Beyond the global RMS, finer analysis includes:

```python
import matplotlib.pyplot as plt

def visualize_reprojection_errors(obj_points, img_points, rvecs, tvecs, K, dist):
    all_errors_x = []
    all_errors_y = []

    for i in range(len(obj_points)):
        proj_pts, _ = cv2.projectPoints(obj_points[i], rvecs[i], tvecs[i], K, dist)
        proj_pts = proj_pts.reshape(-1, 2)
        detected = img_points[i].reshape(-1, 2)

        errors = detected - proj_pts
        all_errors_x.extend(errors[:, 0].tolist())
        all_errors_y.extend(errors[:, 1].tolist())

    # Error distribution plot
    plt.figure(figsize=(8, 8))
    plt.scatter(all_errors_x, all_errors_y, alpha=0.3, s=5)
    plt.xlabel('Error X (pixel)')
    plt.ylabel('Error Y (pixel)')
    plt.title('Reprojection Error Distribution')
    plt.axhline(0, color='r', linewidth=0.5)
    plt.axvline(0, color='r', linewidth=0.5)
    plt.axis('equal')
    plt.grid(True)
    plt.show()

    rms_x = np.sqrt(np.mean(np.array(all_errors_x)**2))
    rms_y = np.sqrt(np.mean(np.array(all_errors_y)**2))
    print(f"RMS_x: {rms_x:.4f} px, RMS_y: {rms_y:.4f} px")
```

**Key indicators:**
- Errors symmetrically distributed around (0, 0) indicate no systematic bias.
- X-direction and Y-direction errors are of similar magnitude, as expected for cameras with $f_x \approx f_y$.
- If errors in one direction are far larger than the other, check for inappropriate distortion modeling along that axis.

### 5.2 3D Reconstruction Accuracy Verification

In a scene with known physical dimensions, use the calibrated camera to estimate lengths and compare against ground truth.

**Square-side length verification:** After calibration, treat the calibration target as a measurement object. Use `solvePnP()` with the calibrated intrinsics to estimate the 6DOF pose of the target, then compute the reprojected distance between two world-coordinate points of known distance and compare with the ground truth. The error should be < 0.5%.

**Stereo baseline verification:** After stereo calibration, place a rigid object of known length (e.g., a precision ruler) within the stereo field of view. Triangulate the 3D coordinates of its two endpoints and compute the 3D Euclidean distance, then compare with the ground truth.

### 5.3 Cross-Validation with MATLAB Camera Calibrator

The MATLAB Camera Calibrator Toolbox is the reference standard in both industry and academia. Cross-validating results between the two tools is an effective way to eliminate software bugs.

**Key parameter comparison:**

| Parameter | OpenCV symbol | MATLAB symbol | Notes |
|------|------------|------------|----------|
| Focal length | $f_x, f_y$ | `FocalLength(1), FocalLength(2)` | Same units (pixels) |
| Principal point | $c_x, c_y$ | `PrincipalPoint(1), PrincipalPoint(2)` | MATLAB origin starts at (1,1); OpenCV at (0,0) |
| Radial distortion | $k_1, k_2, k_3$ | `RadialDistortion(1:3)` | Same sign convention |
| Tangential distortion | $p_1, p_2$ | `TangentialDistortion(1:2)` | MATLAB disabled by default; must be enabled manually |

The principal point difference between OpenCV and MATLAB is approximately 0.5 pixel (due to different coordinate origins). The conversion is roughly $c_x^{OpenCV} = c_x^{MATLAB} - 0.5$ (this is disputed; verification by measurement is recommended).

---

## §6 Code

The complete Python implementation (including calibration, distortion correction, stereo calibration, and visualization analysis) is provided in:

*See §6 Code section for runnable examples.*

The code covers:
- Checkerboard corner detection and sub-pixel refinement
- Complete `cv2.calibrateCamera` workflow
- Reprojection error visualization (scatter plot + heat map)
- Distortion correction comparison (before and after)
- Stereo calibration and rectification
- Saving and loading calibration results (`.npz` format)

---

## §7 Quantum Efficiency (QE) Curve Calibration

> **Disclaimer: The content in this section is based on the publicly available EMVA 1288 standard and academic literature. All numerical values are typical reference figures from the literature and do not involve any proprietary measurement data or internal test results.**

Quantum efficiency (QE) is a core parameter of sensor photoelectric characteristics. It directly determines the white-balance gain range in the ISP calibration chain, the design space for the color correction matrix (CCM), and the spectral response of each module. This section systematically covers the physical meaning of the QE curve, the EMVA 1288 standard measurement framework, the experimental procedure, open-source tools, and their applications in ISP design — intended as reference for sensor evaluation and ISP algorithm development.

---

### 7.1 Physical Definition and Significance of QE

#### 7.1.1 Physical Definition

Quantum efficiency $\text{QE}(\lambda)$ is defined as the probability that one incident photon at wavelength $\lambda$ is converted into one photoelectron, ranging over $[0\%, 100\%]$:

$$
\text{QE}(\lambda) = \frac{\text{number of generated photoelectrons}}{\text{number of incident photons}} \times 100\%
$$

The more rigorous engineering definition (EMVA 1288 §5.6) is:

$$
\text{QE}(\lambda) = \frac{\overline{\mu}_e}{\overline{\mu}_p(\lambda)}
$$

where $\overline{\mu}_e$ is the mean number of photoelectrons per pixel and $\overline{\mu}_p(\lambda)$ is the mean number of incident photons per pixel. Note that QE here represents the overall photoelectric conversion efficiency, including the joint efficiency of a photon passing through the microlens, the color filter array (CFA), the passivation layer, and into the silicon layer.

#### 7.1.2 Typical BSI vs. FSI QE Comparison

Based on publicly available academic literature and typical reference values from vendor public datasheets:

| Wavelength | BSI CMOS Typical QE | FSI CMOS Typical QE | Notes |
|------|-----------------|-----------------|------|
| 400 nm (deep blue) | ~40% | ~25% | Blue-light absorption layer is shallow; BSI advantage is pronounced |
| 450 nm (blue) | ~55% | ~38% | — |
| 550 nm (green, peak) | ~70–80% | ~55–65% | BSI peak QE ~70–80% (literature typical value) |
| 650 nm (red) | ~60% | ~48% | — |
| 700 nm (deep red) | ~50–55% | ~40–45% | — |
| 800 nm (near-infrared) | ~35% | ~28% | Silicon photoabsorption cross-section decreases |
| 900 nm (near-infrared) | ~12–18% | ~8–12% | Cutoff region; IR filter required |

> **Data source note:** The values in the table are **typical literature reference values** compiled from published works (e.g., Fossum & Hondongwa 2014 IEEE JEDS, Innocenzi et al. 2016 SPIE, and OmniVision/STMicro public white papers). They do not represent measured data from any specific product.

The QE advantage of BSI (backside-illuminated) over FSI (frontside-illuminated) stems from the fact that photons enter from the back of the chip and need not pass through metal interconnect layers, so the fill factor is theoretically close to 100%. The improvement is most significant in the blue-violet range (400–500 nm).

#### 7.1.3 Impact of the QE Curve on ISP

The QE curve directly affects the following ISP calibration parameters:

1. **CCM matrix design:** The product of the CIE XYZ color matching functions and the sensor spectral response $S(\lambda) = \text{QE}(\lambda) \cdot T_\text{CFA}(\lambda) \cdot L(\lambda)$ determines the sensor's color response, which in turn governs the CCM design space and condition number. The ratio of QE peak values across the R/G/B channels determines the relative strength of the three-channel responses.

2. **AWB gain prior range:** The reciprocal of the ratio of mean per-channel responses under D65 illumination gives a prior estimate of the AWB gains. The lower QE in the blue region (relative to green and red) means the B-channel gain is typically largest (typical ordering $G_B > G_G > G_R$, though exact values depend on CFA transmittance and illuminant).

3. **RAW white-balance gain range estimation:** With known $\text{QE}(\lambda)$ and typical CFA transmittance, the initial AWB gain range for different illuminants can be estimated by numerical integration without capturing a grey card — providing a prior initialization for the 3A algorithm.

4. **LSC and QE non-uniformity:** Edge pixels suffer reduced effective QE because the microlens chief ray angle (CRA) does not match the lens exit angle (CRA mismatch), which is the sensor-side component of vignetting. This systematic error must be distinguished from the optical vignetting component in LSC calibration.

---

### 7.2 EMVA 1288 Standard Measurement Framework

#### 7.2.1 Standard Overview

**EMVA 1288** (European Machine Vision Association Standard 1288) is the internationally accepted standard for measuring and characterizing industrial camera sensor performance. The current effective version is EMVA 1288 Release 4.0 (2021). The standard document is publicly available for download:

- Official URL: https://www.emva.org/standards-technology/emva-1288/

EMVA 1288 covers: quantum efficiency (QE), read noise, full well capacity (FWC), dark current, linearity, dynamic range, and other sensor parameters — one of the most frequently cited standards in sensor datasheets.

#### 7.2.2 Core QE Measurement Equation

According to EMVA 1288 §5.6, $\text{QE}(\lambda)$ is measured via the **Photon Transfer Curve (PTC)** method. The core derivation is as follows.

**Poisson photon statistics and shot noise separation:** Under uniform illumination, the mean output signal $\bar{\mu}_{DN}$ and variance $\sigma^2_{DN}$ of a pixel satisfy:

$$
\sigma^2_{\text{shot}} = \frac{\overline{\mu}_{DN}}{K}
$$

where $K$ is the overall system gain ($\text{e}^-/\text{DN}$), independently measured from the PTC slope.

**Incident photon count:** Let pixel area be $A_\text{pixel}$ ($\text{m}^2$), exposure time $t_\text{exp}$ (s), image-plane irradiance $E_\lambda$ ($\text{W/m}^2/\text{nm}$), and single-photon energy $E_\text{photon} = hc/\lambda$; then:

$$
\overline{\mu}_p(\lambda) = \frac{E_\lambda \cdot A_\text{pixel} \cdot t_\text{exp} \cdot \lambda}{h \cdot c}
$$

**QE calculation formula (EMVA 1288 §5.6):**

$$
\boxed{\text{QE}(\lambda) = \frac{\overline{\mu}_{DN} / K}{E_\lambda \cdot A_\text{pixel} \cdot t_\text{exp} \cdot \lambda \;/\; (h \cdot c)}}
$$

Expanded into the commonly used form:

$$
\text{QE}(\lambda) = \frac{\sigma^2_{\text{shot}} \cdot K}{E_\lambda \cdot A_\text{pixel} \cdot t_\text{exp}} \cdot \frac{h \cdot c}{\lambda}
$$

where:
- $h = 6.626 \times 10^{-34}\ \text{J·s}$ (Planck constant)
- $c = 2.998 \times 10^8\ \text{m/s}$ (speed of light)
- $\lambda$: wavelength (m)
- $K$: system gain ($\text{e}^-/\text{DN}$), independently calibrated from the PTC
- $E_\lambda$: image-plane irradiance ($\text{W/m}^2$), measured by a power meter
- $A_\text{pixel}$: single-pixel area ($\text{m}^2$, known)
- $t_\text{exp}$: exposure time (s, known)

> **Independent calibration of system gain $K$:** $K$ is obtained independently by capturing image pairs at different exposures and computing the slope of $\sigma^2_{DN}$ vs. $\bar{\mu}_{DN}$ (the Photon Transfer Curve), decoupled from the QE measurement. This is a core advantage of the EMVA 1288 framework.

#### 7.2.3 Equipment List

| Equipment Type | Function | Key Specification |
|---------|---------|------------|
| **Integrating Sphere** | Provides spatially uniform Lambertian radiation field; high-reflectance inner coating (barium sulfate or PTFE) diffuses all incident light uniformly | Uniformity < ±1% (exit face), diameter typically 10–30 cm |
| **Monochromator** | Selects a specific wavelength from a broadband source (halogen or xenon arc lamp) for step-by-step wavelength scanning | Wavelength range 380–1000 nm, half-bandwidth (FWHM) ≤ 5 nm |
| **Reference Power Meter** | Absolutely calibrates incident irradiance $E_\lambda$; NIST (or equivalent) traceable certificate | Absolute accuracy ±0.5%, wavelength coverage spanning measurement range |
| **Fiber Coupler** | Connects monochromator output to integrating sphere input; reduces stray light | Low attenuation, covering 350–1100 nm |
| **Temperature-Controlled Fixture** | Maintains sensor at a stable temperature during measurement, eliminating dark current thermal drift | Temperature stability ±0.5°C |
| **Light-Tight Dark Box** | Isolates environmental stray light | Light leakage < 1/10000 of signal level |

---

### 7.3 Calibration Experimental Procedure

> **Methodology note:** This section describes a general QE measurement procedure based on EMVA 1288 and publicly available academic literature. It does not involve any specific sensor model or internal measurement data.

**Step 1: Establish uniform illumination field**

Couple the monochromator output via optical fiber to the integrating sphere input port. The integrating sphere output (source port) provides spatially uniform Lambertian radiation to the sensor. Confirm uniformity < ±2% (within the exit aperture diameter) using a spatial uniformity scan of the exit-face irradiance distribution.

**Step 2: Power meter calibration of spectral irradiance $E(\lambda)$**

At each measurement wavelength, place a calibrated reference detector (with metrological traceability) at the sensor position and measure irradiance:

$$
E_\lambda = \frac{P_\text{meas}}{A_\text{det}} \quad [\text{W/m}^2]
$$

where $P_\text{meas}$ is the power meter reading (W) and $A_\text{det}$ is the effective detector area ($\text{m}^2$). This step establishes the wavelength-irradiance calibration curve $E(\lambda)$, which is critical to the absolute accuracy of QE.

**Step 3: Capture images at each wavelength (380–1000 nm, step 10 nm)**

Set the monochromator sequentially to 380, 390, 400, …, 1000 nm. At each wavelength:
- Set the sensor to operate in the linear range (avoid saturation; signal at ~40–60% of full well)
- Capture multiple frames (≥ 20 frames) for statistical averaging and variance computation
- Simultaneously record exposure time $t_\text{exp}$

**Step 4: Compute mean DN value at each wavelength**

For multi-frame images at each wavelength, compute the mean and variance of the region of interest (ROI, typically the central 100×100 pixels to avoid vignetting):

$$
\bar{\mu}_{DN}(\lambda) = \frac{1}{N_\text{frames}} \sum_{k=1}^{N_\text{frames}} \bar{I}_k(\lambda)
$$

$$
\sigma^2_{DN}(\lambda) = \text{Var}\left[\bar{I}_k(\lambda)\right] - \sigma^2_{\text{read}}
$$

where $\sigma^2_\text{read}$ is the read noise variance (independently measured from dark frames) and must be subtracted from the total variance.

**Step 5: Compute QE($\lambda$) using the EMVA formula**

Substitute $E_\lambda$ from Step 2, $\bar{\mu}_{DN}(\lambda)$ from Step 4, and the independently calibrated system gain $K$ into the QE formula from §7.2.2, computing per wavelength:

$$
\text{QE}(\lambda) = \frac{\bar{\mu}_{DN}(\lambda)}{K} \cdot \frac{h \cdot c}{E_\lambda \cdot A_\text{pixel} \cdot t_\text{exp} \cdot \lambda}
$$

**Step 6: Fit a smooth curve (Savitzky-Golay filtering)**

Due to monochromator step size and measurement noise, the raw QE point series contains high-frequency fluctuations. Apply a Savitzky-Golay filter (window width 5–7 points, polynomial order 3) to smooth:

```python
from scipy.signal import savgol_filter
qe_smooth = savgol_filter(qe_raw, window_length=5, polyorder=3)
```

The smoothed curve is the final $\text{QE}(\lambda)$ calibration result, which can be exported as a lookup table (LUT) for use in the ISP.

---

### 7.4 Open-Source Tools and Simulation

#### 7.4.1 EMVA 1288 Open-Source Implementation

**EMVACameraModel** (open-source on GitHub): Provides a Python implementation of sensor parameters (QE, gain $K$, read noise, FWC) under the EMVA 1288 framework, usable for:
- Fitting system gain $K$ from measured PTC data
- Automated generation of EMVA 1288 standard reports
- Simulating sensor SNR under different QE curves

Repository: https://github.com/EMVA1288/emva1288 (MIT License)

**Related Python ecosystem:**
- `colour-science` (https://www.colour-science.org/): spectral integration, CIE color computation, camera spectral response modeling
- `numpy` / `scipy`: numerical integration, curve fitting
- `matplotlib`: QE curve visualization

#### 7.4.2 Typical BSI CMOS QE Curve Simulation Code

The following code uses Gaussian superposition to approximate the spectral shape of BSI/FSI CMOS QE, based on publicly available literature typical values. It is for **teaching demonstration and ISP algorithm prototype validation only** and does not represent measured data from any real sensor:

```python
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from scipy.interpolate import PchipInterpolator

# ========================================================
# Typical BSI/FSI CMOS QE curve simulation
# Data based on public literature typical reference values (not real measurement data)
# Reference: Fossum & Hondongwa (2014), EMVA 1288 typical examples
# ========================================================

wavelengths = np.arange(380, 1010, 10)  # 380–1000 nm, step 10 nm

# ---- BSI typical control points (based on literature reference values) ----
bsi_ctrl_wl  = np.array([380, 400, 450, 500, 550, 600, 650,
                          700, 750, 800, 850, 900, 950, 1000])
bsi_ctrl_qe  = np.array([ 28,  40,  55,  68,  75,  70,  60,
                           50,  38,  25,  18,  12,   5,   2]) / 100.0

# ---- FSI typical control points (based on literature reference values) ----
fsi_ctrl_wl  = np.array([380, 400, 450, 500, 550, 600, 650,
                          700, 750, 800, 850, 900, 950, 1000])
fsi_ctrl_qe  = np.array([ 15,  25,  38,  52,  62,  57,  48,
                           40,  30,  20,  14,   9,   4,   1]) / 100.0

# PCHIP interpolation (shape-preserving, no Runge oscillation)
bsi_interp = PchipInterpolator(bsi_ctrl_wl, bsi_ctrl_qe)
fsi_interp = PchipInterpolator(fsi_ctrl_wl, fsi_ctrl_qe)

qe_bsi = np.clip(bsi_interp(wavelengths), 0, 1)
qe_fsi = np.clip(fsi_interp(wavelengths), 0, 1)

# Add simulated measurement noise (±1% RMS, simulating experimental random error)
rng = np.random.default_rng(42)
qe_bsi_noisy = qe_bsi + rng.normal(0, 0.01, len(wavelengths))
qe_fsi_noisy = qe_fsi + rng.normal(0, 0.01, len(wavelengths))

# Savitzky-Golay smoothing (EMVA recommended post-processing)
qe_bsi_smooth = savgol_filter(np.clip(qe_bsi_noisy, 0, 1), 5, 3)
qe_fsi_smooth = savgol_filter(np.clip(qe_fsi_noisy, 0, 1), 5, 3)
```

---

### 7.5 ISP Applications of QE Calibration Results

#### 7.5.1 Deriving AWB Gain Prior Range from QE($\lambda$)

For an illuminant $L(\lambda)$ ($\text{W/m}^2/\text{nm}$), the sensor response for CFA channel $c \in \{R, G, B\}$ is:

$$
S_c = \int_{380}^{780} L(\lambda) \cdot \text{QE}_c(\lambda) \cdot T_c^{\text{CFA}}(\lambda) \cdot d\lambda
$$

where $T_c^{\text{CFA}}(\lambda)$ is the transmittance curve of CFA channel $c$ (available from vendor public spectral data).

The AWB gain prior is:

$$
g_c^{\text{prior}} \propto \frac{1}{S_c} \cdot S_G \quad \Rightarrow \quad g_R = \frac{S_G}{S_R},\quad g_B = \frac{S_G}{S_B}
$$

**Practical significance:** Without capturing a grey card, the initial AWB gain range for different illuminants can be estimated by numerically integrating $\text{QE}(\lambda)$ + $T_c^\text{CFA}(\lambda)$ + $L_{D65}(\lambda)$, providing a prior constraint for the 3A AWB algorithm (gain range clipping) and preventing AWB from converging to incorrect extremes.

For a typical BSI sensor under D65, the channel response ratio $S_R : S_G : S_B \approx 0.85 : 1.00 : 0.70$ (varies with CFA design), corresponding to gain priors $g_R \approx 1.18$, $g_B \approx 1.43$ — consistent with D65 AWB gain distributions commonly observed in engineering practice.

#### 7.5.2 Effect of QE Non-uniformity on LSC Calibration

LSC (Lens Shading Correction) calibration typically assumes that all sensor pixels have identical responses, but in practice there are two types of non-uniformity:

1. **Optical vignetting:** Caused by lens aperture and the vignetting effect — the primary target of LSC correction.
2. **Sensor CRA mismatch effect:** Effective QE at edge pixels decreases because the microlens does not match the chief ray angle of the incident light, a sensor-side non-uniformity.

These two effects **combine and overlay** in LSC calibration and cannot be separated from a single flat-field image. If the sensor's CRA vs. QE characteristic is known (from QE calibration or vendor public data), a prior model can be built to help decompose the LSC gain table into an optical component and a sensor component, improving LSC robustness across illuminants.

#### 7.5.3 Multi-Camera QE Consistency Acceptance

In multi-camera cooperative systems (main + ultra-wide, main + telephoto, front + rear fusion), QE differences between cameras affect the color consistency of fused images.

Engineering acceptance criterion (based on public literature and EMVA 1288 accuracy framework):

$$
\Delta\text{QE}@550\text{nm} < 5\% \quad \Rightarrow \quad \text{same-batch sensor acceptance passed}
$$

> This 5% threshold is an empirical industry standard derived from the tolerance requirement of post-AWB residual color error $<\Delta E_{ab}^* = 3$. The exact value varies by product specification; the final criterion should be based on system-level IQA test results.

---

### 7.6 Common Measurement Error Sources

| Error Type | Source Description | Typical Magnitude | Mitigation |
|---------|---------|---------|---------|
| **Integrating sphere uniformity** | Non-uniform inner-wall reflectance; spatial irradiance gradient at exit face | ±2–3% | Multi-point calibration; increase sphere-to-sensor area ratio; use dual-port sphere (monitor port for real-time correction) |
| **Monochromator stray light** | Higher-order diffraction or scattering from the grating entering the detection channel | ±0.5–2% | Use a double monochromator (series-coupled); add long-pass filter at UV end |
| **Dark current contribution** | Thermally generated electrons accumulate during long exposures or at high temperatures, causing QE overestimation | ±0.5–1% | Dark-frame subtraction before measurement; verify linearity with short-exposure comparison |
| **Temperature drift** | Sensor self-heating increases dark current over time; silicon bandgap temperature coefficient causes red-shift in response | ±1–2% (no temperature control) | Add temperature-controlled fixture; allow sensor thermal stabilization (≥10 min warm-up); record measurement temperature |
| **Power meter absolute calibration** | Uncertainty in the absolute responsivity calibration of the reference detector (NIST traceability error) | ±0.5% | Use reference detector with certified metrology traceability; send for recalibration periodically |
| **Pixel PRNU** | Photo response non-uniformity introduces bias in the ROI mean | ±0.3–1% | Select a small central ROI (100×100 px); multi-frame averaging; normalize with flat-field image |
| **Fiber polarization effect** | Optical fiber may introduce polarization state changes at certain wavelengths, affecting integrating sphere uniformity | ±0.5–1% (UV end) | Use multimode polarization-maintaining fiber; add scattering element inside integrating sphere |

**Combined measurement uncertainty:** Combining the above independent uncertainty contributions (RSS):

$$
u_\text{total} = \sqrt{u_\text{sphere}^2 + u_\text{stray}^2 + u_\text{dark}^2 + u_\text{temp}^2 + u_\text{power}^2 + u_\text{PRNU}^2} \approx \pm 3\text{–}5\%
$$

This means that under basic laboratory conditions without temperature control and with a single-port integrating sphere, the absolute QE measurement uncertainty is approximately ±3–5% ($k=2$, 95% confidence interval), consistent with the uncertainty declarations reported in EMVA 1288 documentation.

---

## §8 ISP Sensor Baseline Calibration (BLC / LSC / CCM / AWB / Linearity / Noise / Defect)

> This section focuses on the sensor baseline calibration actually performed in mobile ISP production lines and engineering debug flows. It is orthogonal to the geometric calibration in §2. Geometric calibration handles "where does the ray go"; this section handles "the errors, non-uniformities, and color distortions introduced when a photon is converted to a digital value."

---

### 8.1 Black Level Calibration (BLC Calibration)

**Physical background:** Under completely light-blocked conditions, CMOS sensors still exhibit dark current and read-noise offset, causing the ADC output for a "zero-signal" condition to be a positive bias that depends on gain and temperature — called the black level (BL). Without black level correction, the baseline for all subsequent signal processing shifts, causing AWB, CCM, and noise models to become inaccurate.

**Calibration procedure:**

1. Capture a dark-frame sequence under fully light-blocked conditions (lens cap or sensor OB row readout mode), typically covering:
   - All working gain steps (ISO 100 / 200 / 400 / 800 / 1600 / 3200 / 6400)
   - Multiple exposure times (shortest: 1/30000 s, longest: 1/30 s, 3–5 steps in between)
   - Room temperature (25°C) calibration with supplemental high-temperature (50°C) calibration

2. For each (Gain, ET) combination, compute the mean and variance of the dark frames separately for the four channels (R / Gr / Gb / B):

$$\text{BL}_{c}(g, T_{\text{exp}}) = \frac{1}{N} \sum_{i} \text{RAW}_{c,i}, \quad c \in \{R, Gr, Gb, B\}$$

3. Fit the linear relationship between black level and gain (offset increases at higher gain):

$$\text{BL}(g) = a_0 + a_1 \cdot g$$

4. If significant temperature drift is present, build a temperature compensation table $\text{BL}(g, T)$, indexed by the ISP register `BLC_TEMP_TABLE` (Qualcomm Chromatix) or `AE_BLC_gain_temperature_table` (MediaTek NDD format).

**Platform configuration:**

| Platform | Parameter Name | Storage Location |
|------|--------|---------|
| Qualcomm Spectra | `BLC_R / Gr / Gb / B` (per-channel 14-bit offset) | Chromatix `.bin` → `BlackLevelCorrectionModule` |
| MediaTek Imagiq | `BLC_OFFSET_R/G/B`, supports per-frame dynamic update | `module_nvram.xml`, associated via NDD noise data |
| HiSilicon/Huawei | `OBOffset_R/Gr/Gb/B`; Kirin ISP supports OB-row real-time statistics (no LUT needed) | `isp_blc.json`, loaded by Yueying HAL driver |
| Apple (inferred) | BLC is hardwired: A-series chip sensor interface subtracts OB statistical mean directly in the hardware path; user-configurable BLC parameters are not exposed | — |

**Acceptance criterion:** After correction, dark-frame four-channel mean deviation < ±1 DN (12-bit); inter-channel consistency < 2 DN; Gr/Gb channel difference (green imbalance) < 1 DN.

---

### 8.2 Defect Pixel Calibration (DPC / BPC Calibration)

**Physical background:** Sensor manufacturing defects cause a small number of pixels to have abnormal responses: hot pixels (always bright), dead pixels (always dark), or stuck pixels. For a smartphone sensor with 1.0 µm pixels in a 200 MP sensor, the allowable number of static defect pixels is typically < 200 (factory specification); in high-gain dark-field conditions, more dynamic hot pixels may appear.

**Calibration procedure:**

1. **Static defect map generation:**
   - Capture 4–8 dark frames (light-blocked) at standard gains (×1, ×4, ×16); take the frame mean to eliminate random noise
   - Compute for each pixel the difference from the same-color-channel neighbor median: $\Delta_{ij} = |P_{ij} - \text{median}(N_{ij})|$; pixels exceeding threshold $T_{\text{hot}}$ (typically 10–15 DN @ 12-bit) are flagged as hot pixels
   - Capture a uniform flat field (fully white) and similarly identify abnormally dark pixels (dead pixels): $P_{ij} < \mu_{\text{neighbor}} - T_{\text{dead}}$

2. **Write defect coordinate list to EEPROM/OTP:**
   - Format: `(row, col, type)` triplet list; stored independently per module
   - Qualcomm Chromatix: `DPC_Static_Defect_Map`, supports up to 2048 static defects
   - MediaTek: `PDAF_defect_map.dat` + `BPC_hot_pixel_table`
   - HiSilicon: Yueying ISP driver loads `defect_pixel_table.bin` in RAW-domain pre-processing

3. **Dynamic defect detection (not fully calibratable at production):** Hot pixels that appear only at extreme high gain (ISO 3200+) are handled in real time by the ISP dynamic DPC module using gradient-based detection; parameter `DPC_Dynamic_Strength` controls detection sensitivity.

**Acceptance criterion:** Static defect repair rate 100% (no missed repairs allowed); over-repair rate (incorrectly rewriting a normal pixel) < 0.01%; at the repaired pixel location, deviation from neighboring pixels < 3 DN.

---

### 8.3 Lens Shading Calibration (LSC Calibration)

**Physical background:** Lens vignetting makes image edges and corners darker than the center, caused by: (1) the cosine-fourth-power law (cos⁴ θ attenuation); (2) mechanical vignetting (rays blocked by lens element edges); (3) sensor CRA mismatch reducing effective QE at edge pixels. LSC compensates by multiplying a gain table.

**Calibration procedure:**

1. **Capture uniform flat field:** Use an integrating sphere or a uniform diffusion panel; capture flat-field images at a standard color temperature (D65) with target signal level 50%–70% of full well (avoid saturation and noise dominance); typically average 16–32 frames to further suppress spatial noise.

2. **Gain table generation:**

$$G_{c}(r, s) = \frac{I_{c,\text{center}}}{\bar{I}_{c}(r, s)}, \quad c \in \{R, Gr, Gb, B\}$$

where $(r, s)$ is the pixel position, $I_{c,\text{center}}$ is the brightness in the central region (typically the mean of the central 1/9 region), and $\bar{I}_{c}(r, s)$ is the multi-frame averaged brightness at the current position. The generated gain table is typically a sparse 17×13 or 33×25 mesh (the ISP bilinearly interpolates to full resolution at runtime).

3. **Multi-illuminant / multi-focus-distance calibration:**
   - Smartphone main cameras require independent calibration under D65, A-source (2856 K), and CW fluorescent (4150 K), because the sensor's CRA response varies slightly under different spectra
   - Telephoto / macro modes involve structural changes in the lens; LSC must be built separately per focus distance and zoom step, indexed by the 3A state machine

4. **LSC gain range constraints:**
   - Regions with very large gain (corner gain > 3.5×) amplify noise significantly; in practice a gain cap `LSC_GAIN_LIMIT = 3.5` is set; anything exceeding this is compensated by wider AE exposure
   - Qualcomm Chromatix: `LSC_MESH_ROLLOFF_TABLE` (17×13, four channels), supports interpolation across 16 illuminant scenarios
   - MediaTek: `mesh_shading_table_R/Gr/Gb/B`; `msf_scene_count` controls number of scenes (up to 16 groups)
   - HiSilicon: Yueying platform `lsc_correction_coeff[channel][row][col]`, supports runtime dynamic illuminant switching

**Acceptance criterion:** After LSC correction, center-to-corner brightness difference on a uniform flat field < 5% (R/B channels allowed up to 7%); four-channel consistency < 3%; shading ratio < 3% across different illuminants after correction.

---

### 8.4 Sensor Linearity Calibration

**Physical background:** An ideal sensor response satisfies `output DN ∝ incident photon count` (linearity), but real CMOS sensors deviate at low illuminance or near saturation due to pixel non-linear response, ADC non-linearity, and FPN. This deviation is the non-linearity error. Without linearity correction, CCM matrices and AWB gains are accurate only in one luminance range; color accuracy degrades across the dynamic range.

**Calibration method:**

1. **Capture a step-wedge chart:** Use 16–24 neutral grey density steps (NDI ND 0 to ND 5), covering 0.5% to 95% of full well from bright to dark; expose sequentially under a standard illuminant at fixed color temperature.

2. **Linearity curve fitting:**

$$R_{\text{ideal}}(\text{EV}) = k \cdot \Phi \cdot t_{\text{exp}}$$

The non-linearity error is defined as $\epsilon(L) = R_{\text{actual}}(L) / R_{\text{ideal}}(L) - 1$.

3. **Correction LUT generation:** The inverse function $\text{LUT}_{\text{linear}}[DN] = f^{-1}(DN)$ is written into the ISP Linearization module (typically a 256–1024 point LUT), mapping the actual response to the linear domain.

4. **Common sources of non-linearity:**
   - **Pre-saturation compression (knee):** Near 85%–95% of full well, pixel response begins to compress; must be handled separately in the linearization LUT (or trigger HDR mode earlier)
   - **Dark-region pedestal effect:** Limited quantization precision and FPN of the ADC at low signal levels introduce a systematic offset
   - **Gain dependence:** Linearity varies slightly with analog gain; the linear range narrows at high gain

**Platform support:**
- Qualcomm Chromatix: `LinearizationModule34`, supports 64-point LUT per channel, 3D-interpolated with gain
- MediaTek Imagiq: `lsc_linearization_table` (joint processing with LSC); `nonlinear_strength` parameter for high-gain adjustment
- The linearity acceptance method defined in EMVA 1288 is the industry general reference (see §7)

**Acceptance criterion:** Non-linearity error < ±1% in the 2%–90% full-well range (< ±0.5% target for high-end flagship main cameras).

---

### 8.5 Noise Model Calibration

**Core model:** The industry standard for ISP noise modeling is the Poisson-Gaussian mixed noise model:

$$\sigma^2(I) = \alpha \cdot I + \beta$$

where $I$ is the signal intensity (DN, after normalization), $\alpha$ (photon shot noise coefficient) and $\beta$ (read noise variance) are the two parameters to be calibrated. Each gain step corresponds to one pair $(\alpha_g, \beta_g)$.

> ⚠️ **Common error:** Approximating the Poisson-Gaussian model with AWGN (Additive White Gaussian Noise, $\sigma = \text{const}$) introduces very large errors at low-light high-gain conditions (up to 5–10 dB SNR deviation), causing denoising networks to perform poorly on real scenes.

**Calibration procedure (PTC / Photon Transfer Curve method):**

1. Under uniform flat-field illumination, fix the color temperature; vary exposure level (EV step 0.5 EV), covering signal from 5% to 90% of full well; capture ≥ 32 frames per step.

2. For each exposure step, take the difference frame between two adjacent frames (Difference Frame) to cancel FPN and spatial non-uniformity, extracting pure temporal noise:

$$\sigma^2_{\text{temporal}} = \frac{1}{2} \text{Var}(\text{Frame}_1 - \text{Frame}_2)$$

3. For each gain step, plot $\sigma^2$ vs. $\bar{I}$ (mean) scatter and fit linearly:

$$\sigma^2 = \hat{\alpha} \cdot \bar{I} + \hat{\beta}$$

The slope $\hat{\alpha}$ corresponds to the shot noise component; the intercept $\hat{\beta}$ corresponds to the read noise variance.

4. Repeat across all gain steps to generate the noise parameter table: $\{(g_k, \alpha_{g_k}, \beta_{g_k})\}$, stored as a noise model LUT.

**Platform configuration:**

| Platform | Noise Model Data Format | Usage |
|------|-------------|------|
| Qualcomm Chromatix | `ADRC_NOISE_PROFILE_TABLE`, storing $(\alpha, \beta)$ per ISO step, calibrated by `NoiseMeasure` module | MFNR weight maps, ghost detection thresholds |
| MediaTek NDD | `NDD_noise_params_gain_table` (core: $(\alpha, \beta)$ table), generated by MTK `NoiseTune` calibration tool from PTC data | FeaturePipe NR strength, AI denoising prior |
| HiSilicon Yueying | `noise_sigma_table[gain_index][2]`, storing $(\alpha, \beta)$; used as noise prior input for AI NR model inference | Kirin NPU AI-NR |

**Acceptance criterion:** Fit residual $R^2 > 0.995$; deviation between measured $\sigma^2$ and model prediction < 5% per gain step; $\alpha / \beta$ monotonically increasing with gain (violation indicates a systematic error).

---

### 8.6 White Balance Gain Calibration (AWB Initial Calibration)

**Definition:** The goal of AWB calibration is not tuning the runtime AWB algorithm (that is §3 tuning territory), but rather determining the **white-balance gain reference points** for major illuminants (D65, A, TL84/F11 fluorescent, H) to be written into ISP parameters, serving as the initial convergence point and valid gain range constraint for the AWB algorithm.

**Calibration procedure:**

1. Under D65, A, CW (4150 K), and TL84 (3000 K) illuminants in a standard light box, capture an X-Rite ColorChecker 24-patch chart (or an 18% grey card) under each illuminant.

2. For each illuminant, compute R/G/B channel means on the neutral grey patch; the white-balance gains $g_c$ are:

$$g_R = \frac{\bar{G}}{\bar{R}}, \quad g_G = 1.0, \quad g_B = \frac{\bar{G}}{\bar{B}}$$

3. Plot the per-illuminant gain points in the RG/BG plane (AWB gain space); fit a polynomial or piecewise linear curve to the **illuminant locus**, defining the valid gain region for AWB at runtime.

4. Verify that the valid gain region is reasonable: D65 typical values $g_R \approx 1.6$–$2.1$, $g_B \approx 1.5$–$2.0$; A-source $g_R \approx 1.1$, $g_B \approx 2.5$–$3.2$ (warm illuminant requires higher blue gain).

**Color accuracy verification (pre-requisite for CCM calibration):**
After AWB gain calibration, verify with a ColorChecker capture that $\Delta E_{00}$ (CIE 2000 color difference) < 5.0 (post-AWB, before CCM), confirming that the channel gain direction is correct before proceeding with CCM matrix calibration.

---

### 8.7 Color Correction Matrix Calibration (CCM Calibration)

**Physical basis:** The sensor's spectral response curve does not match the human visual color matching function (CIE XYZ), causing the camera's captured RGB values to systematically deviate from standard color spaces (sRGB). The CCM is a 3×3 linear transformation (with bias term) mapping camera RGB to sRGB:

$$\begin{bmatrix} R_{\text{out}} \\ G_{\text{out}} \\ B_{\text{out}} \end{bmatrix} = M_{3\times3} \begin{bmatrix} R_{\text{cam}} \\ G_{\text{cam}} \\ B_{\text{cam}} \end{bmatrix} + \mathbf{b}$$

**Calibration procedure:**

1. Under each major illuminant (at minimum D65 + A; engineering practice also adds TL84), capture a ColorChecker 24-patch chart (using RAW linear values after applying AWB gains).

2. For each patch $i$, form the equation $M \cdot \mathbf{r}_i \approx \mathbf{t}_i$, where $\mathbf{r}_i$ is the three-channel camera response and $\mathbf{t}_i$ is the CIE XYZ or sRGB reference value (from ColorChecker official measurement data).

3. Solve via least squares:

$$M^* = \arg\min_M \sum_{i=1}^{24} \left\| M \cdot \mathbf{r}_i - \mathbf{t}_i \right\|_2^2$$

In matrix form: $M^* = (\mathbf{T} \mathbf{R}^T)(\mathbf{R} \mathbf{R}^T)^{-1}$, where $\mathbf{R} \in \mathbb{R}^{3 \times 24}$, $\mathbf{T} \in \mathbb{R}^{3 \times 24}$.

4. **Multi-CCM strategy:** Calibrate independent matrices $M_{D65}$, $M_A$, $M_{TL84}$ for different illuminants; interpolate between matrices at runtime based on the CCT estimated by the AWB algorithm.

5. **Matrix condition number check:** A high condition number ($\kappa(M) > 10$) means the matrix is sensitive to measurement noise, causing color accuracy to degrade under sensor noise. This can be mitigated by adjusting the AWB gain reference points or by using regularized least squares (Tikhonov regularization) to reduce the condition number (see Part 2, Chapter 6, §3.2).

**Acceptance criterion:** ColorChecker 24-patch mean $\Delta E_{00}$ < 3.0 (D65 illuminant), maximum < 6.0; saturated colors (rows 1–6) individually meet $\Delta E_{00}$ < 5.0; neutral grey column (6 patches) color error < 1.5.

**Platform parameter locations:**
- Qualcomm Chromatix: `ChromaticityModule` → `CCM_Matrix_D65 / CCM_Matrix_A`, interpolated with AWB CCT
- MediaTek: `color_correction_transform_matrix[3][3]` + `color_range_adjust`
- HiSilicon Yueying: `ccm_coef[light_source_index][3][3]`, light source index mapped from AWB output

---

### 8.8 Factory Production-Line Integration of Calibration Modules

Before a smartphone camera module (Camera Module Assembly) leaves the factory, the above calibrations are typically executed serially on an automated calibration line in the following order, with each individual module calibrated and written to EEPROM/OTP independently:

```
1. Power-on self-test (POST)
     └── Sensor ID, I²C communication, basic frame rate verification

2. Dark field capture → BLC calibration
     └── 5 gain steps × 2 exposure points = 10 dark frame groups
     └── Compute BLC_R/Gr/Gb/B, write to EEPROM

3. Defect calibration → Static defect map generation
     └── Dark field hot-pixel detection + flat field dead-pixel detection
     └── Defect list written to EEPROM (≤ 200 entries @ 200MP)

4. Flat-field capture → LSC calibration (D65 primary + A-source secondary)
     └── Generate 17×13 four-channel gain table, write to EEPROM

5. Sensor linearity verification
     └── Quick PTC (3 exposure points), confirm non-linearity error < 2%

6. Noise parameter calibration (full-gain PTC)
     └── Fit (α, β), write to ISP debug parameters (firmware partition, not EEPROM)

7. AWB gain point calibration (standard light box)
     └── D65 / A two-illuminant gain points written to ISP

8. CCM matrix calibration
     └── ColorChecker 24 patches, least squares, ΔE₀₀ < 3.0 pass criterion
     └── CCM written to ISP Chromatix / NDD parameter package

9. Final acceptance capture
     └── Capture standardized colour chart + resolution target under D65
     └── Automated pass/fail decision
```

Typical per-module calibration time: **30–90 seconds** (high-end flagships with more complete multi-illuminant / multi-gain coverage typically take 60–90 s; mid-range devices can be reduced to 30–45 s).

**Production-line calibration data management:** Each module's serial number (SN) is bound to its calibration results for after-sales traceability. The cloud calibration database records batch statistical distributions; anomalous clustering (e.g., a batch with collectively elevated BLC values) triggers a supplier quality alert.

---

> **Engineer's Note: Calibration Engineering Thresholds and Thermal Drift Pitfalls**
>
> **Reprojection error acceptance threshold:** After camera calibration, reprojection error (RPE) is the standard quality metric. For ISP parameter alignment (especially multi-camera alignment, AR overlay, and ranging applications), the RPE acceptance criterion should be set to < 0.5 pixel; some high-precision AR scenarios require < 0.3 pixel. Common causes of out-of-spec RPE in production calibration: insufficient target flatness (tolerance < 0.1 mm), insufficient angular coverage of calibration frames (recommended ±30° pitch + horizontal), and corner detection offset due to non-uniform illumination. An easily overlooked detail: RPE is averaged across all calibration frames, so individual frames with large errors can be diluted by averaging. The inter-frame RPE distribution dispersion should also be checked (P95 < 1.0 px).
>
> **Thermal drift of calibration parameters:** Smartphone main cameras commonly use f/1.8–f/2.2 plastic aspherical lenses with a thermal expansion coefficient of approximately 60–90 ppm/°C, far higher than glass (~8 ppm/°C). At a typical equivalent focal length of ~5 mm, a 1°C temperature rise shifts the back focal distance by ~2 µm, corresponding to a lateral principal point drift of ~0.1–0.3 pixels. In practice, from room temperature 25°C to high temperature 50°C (smartphone full-load scenario), accumulated principal point drift can reach 2–5 pixels — sufficient to cause multi-camera disparity alignment failure. Engineering countermeasures: (1) store multi-temperature-point calibration data in OTP (at least 25°C and 40°C), with the ISP interpolating in real time based on the NTC temperature sensor; (2) design a thermal stability correction block that triggers a software correction periodically (every 30 s or when temperature rise ΔT > 5°C).
>
> **Factory calibration validity and field update frequency:** Factory calibration is performed in a temperature-controlled production environment and achieves the highest accuracy, but it gradually drifts over the device lifetime due to drops, aging, and other factors. Field calibration updates rely on unobtrusive triggers during normal use; the common strategy is self-calibration using stationary feature points in motion video (online calibration), which typically achieves accuracy 0.2–0.5 pixel lower than factory calibration. In practice, factory calibration validity is approximately 6–12 months; beyond this period, multi-camera 3D ranging errors may exceed product specifications if no self-calibration is in place.
>
> *References: Zhang, Z. "A Flexible New Technique for Camera Calibration", IEEE TPAMI 2000; Bradski & Kaehler "Learning OpenCV 3", Ch.18; Apple Vision Pro Spatial Audio Calibration Technical Note (2023)*

---

## Figures

![calibration checkerboard](img/fig_calibration_checkerboard_ch.png)
*Figure 1. Camera calibration checkerboard target schematic (Image source: Zhang, "A flexible new technique for camera calibration", IEEE TPAMI, 2000)*

![calibration target types](img/fig_calibration_target_types_ch.png)
*Figure 2. Comparison of common camera calibration target types (checkerboard, circle grid, AprilTag, etc.) (Image source: author illustration)*

![calibration workflow](img/fig_calibration_workflow_ch.png)
*Figure 3. Complete camera intrinsic/extrinsic calibration workflow (Image source: Bouguet, "Camera Calibration Toolbox for Matlab", 2004)*

![lens distortion models](img/fig_lens_distortion_models_ch.png)
*Figure 4. Radial and tangential distortion (Brown-Conrady model) schematic (Image source: Brown, "Decentering distortion of lenses", Photogrammetric Engineering, 1966)*

![reprojection error distribution](img/fig_reprojection_error_distribution_ch.png)
*Figure 5. Calibration reprojection error distribution plot (Image source: author illustration)*

---

## References

1. **Zhang, Z. (2000)**. "A flexible new technique for camera calibration." *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 22(11), 1330–1334.
   — The original paper on Zhang's calibration method; essential reading; the 3-page derivation is very clear.

2. **OpenCV Camera Calibration Documentation**.
   https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html
   — The official OpenCV tutorial; code is directly reusable; note version differences (4.x vs 3.x API differ slightly).

3. **Bouguet, J.-Y. (2004)**. "Camera calibration toolbox for Matlab."
   http://www.vision.caltech.edu/bouguet/calib_doc/
   — MATLAB calibration toolbox documentation; useful as a reference for cross-checking OpenCV results.

4. **Kannala, J., & Brandt, S. S. (2006)**. "A generic camera model and calibration method for conventional, wide-angle, and fish-eye lenses." *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 28(8), 1335–1340.
   — The standard reference for fisheye lens calibration and the theoretical basis of OpenCV's `fisheye` module.

5. **Hartley, R., & Zisserman, A. (2004)**. *Multiple View Geometry in Computer Vision* (2nd ed.). Cambridge University Press.
   — Complete theoretical derivation of epipolar geometry, essential matrix, and fundamental matrix; Chapters 9–10.

6. **Scaramuzza, D., Martinelli, A., & Siegwart, R. (2006)**. "A toolbox for easily calibrating omnidirectional cameras." *Proceedings of the IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)*.
   — Authoritative toolbox for omnidirectional camera calibration; reference for wide-angle/fisheye scenarios.

7. **Brown, D. C. (1966)**. "Decentering distortion of lenses." *Photogrammetric Engineering*, 32(3), 444–462.
   — Original paper on the Brown-Conrady radial + tangential distortion model.

8. **Bradski, G., & Kaehler, A. (2008)**. *Learning OpenCV: Computer Vision with the OpenCV Library*. O'Reilly Media.
   — Standard reference for the OpenCV camera calibration API, including descriptions of `calibrateCamera` and `stereoCalibrate` implementations.

9. **Garrido-Jurado, S., et al. (2014)**. "Automatic generation and detection of highly reliable fiducial markers under occlusion." *Pattern Recognition*, 47(6), 2280–2292.
   — Original ArUco marker paper; the theoretical foundation of the ChArUco board.

10. **Heikkila, J., & Silven, O. (1997)**. "A four-step camera calibration procedure with implicit image correction." *Proceedings of IEEE CVPR*.
    — An early comprehensive distortion correction procedure including full treatment of tangential distortion.

11. **EMVA 1288 Release 4.0 (2021)**. "Standard for Characterization of Image Sensors and Cameras." European Machine Vision Association. URL: https://www.emva.org/standards-technology/emva-1288/

12. **Fossum, E. R., & Hondongwa, D. B. (2014)**. "A review of the pinned photodiode for CCD and CMOS image sensors." *IEEE Journal of the Electron Devices Society*, 2(3), 33–43.

13. **Li, Z., et al. (2022)**. "StereoISP: Rethinking Image Signal Processing for Dual Camera Systems." *arXiv:2211.07390*.
    — Joint framework for dual-camera ISP and stereo matching using dual RAW pairs for demosaicking and denoising.

14. **MIPI Alliance (2023)**. "MIPI CSI-2 Specification v4.0." Official document. URL: https://www.mipi.org/specifications/csi-2
    — Mobile sensor interface specification; protocol basis for calibration data transmission and EEPROM readout.

---

## §9 Glossary

**Pinhole Camera Model**
A central projection model that abstracts the camera as an ideal small aperture, describing the geometric relationship by which 3D world-coordinate points are mapped to 2D pixel coordinates via perspective projection: $s\mathbf{u} = \mathbf{K}[\mathbf{R}|\mathbf{t}]\mathbf{X}_w$. The pinhole model is the mathematical foundation of CV calibration but does not describe lens thickness, aberrations, or sensor packaging effects. The LDC/GDC module in an ISP aims to restore images produced by a real lens (which deviates from the pinhole model) back to ideal pinhole images through a nonlinear inverse mapping. For ultra-wide-angle and fisheye lenses with FoV > 110°, the pure pinhole model error rises significantly and specialized models such as Kannala-Brandt must be used.

**Intrinsic Matrix (K)**
A linear mapping from normalized image-plane coordinates in the camera coordinate system to pixel coordinates, containing 5 parameters: focal lengths $f_x, f_y$ (in pixels), principal point $c_x, c_y$ (intersection of the optical axis with the sensor), and skew $s$ (typically 0 for modern sensors). For a typical 12 MP smartphone main camera (4032×3024): $f_x \approx 1100$–$2200$ px, $c_x \approx 2016$ px, $c_y \approx 1512$ px; principal point eccentricity is usually within ±15 px. Intrinsics vary slightly with focus distance (zoom cameras require independent calibration per zoom level) and exhibit thermal drift with temperature (on the order of ±2% over extreme temperature ranges).

**Extrinsic Parameters**
The rigid-body transformation from the world coordinate system to the camera coordinate system: rotation matrix $\mathbf{R}$ (3×3, $\text{SO}(3)$) and translation vector $\mathbf{t}$ (3×1). Extrinsics are a byproduct of the calibration process (each calibration image yields one set of extrinsics) describing the pose of the calibration target within the camera's field of view. In a multi-camera system, the extrinsics between cameras (relative rotation and translation) are the core output of stereo calibration, determining epipolar geometry accuracy.

**Homogeneous Coordinates**
A coordinate representation that introduces an additional dimension in $n$-dimensional space, allowing nonlinear transformations such as perspective projection to be expressed as matrix multiplications. A 3D point $(X, Y, Z)$ is represented in homogeneous coordinates as $(X, Y, Z, 1)^T$; a 2D pixel $(u, v)$ as $(u, v, 1)^T$. Homogeneous coordinates allow perspective projection, rotation, and translation to be combined into a single matrix multiplication, making them a central tool of projective geometry.

**Radial Distortion**
A geometric aberration caused by uneven lens curvature, distributed symmetrically around the optical axis and adding along the radial direction. Brown-Conrady model: $x' = x(1 + k_1 r^2 + k_2 r^4 + k_3 r^6)$, $r^2 = x^2 + y^2$. $k_1 < 0$ produces barrel distortion (wide-angle lenses; image bulges inward); $k_1 > 0$ produces pincushion distortion (telephoto lenses; image bulges outward). Radial distortion is the dominant distortion term for smartphone lenses; $k_1$ can reach approximately $-0.2$ for ultra-wide-angle lenses; $k_3$ is non-negligible when FoV > 100°.

**Tangential Distortion**
Asymmetric distortion caused by imperfect parallelism between the lens plane and the sensor plane (assembly tilt): $\Delta x = 2p_1 xy + p_2(r^2+2x^2)$, $\Delta y = p_1(r^2+2y^2) + 2p_2 xy$. Tangential distortion coefficients $p_1, p_2$ are typically one order of magnitude smaller than radial coefficients ($|p_1|, |p_2| < 0.005$). Modern automated lens module assembly achieves high precision, and tangential distortion has negligible impact on image quality for most smartphone main cameras, though it cannot be omitted for precision measurement and stereo vision.

**Thin Prism Distortion**
Asymmetric residual distortion caused by lens assembly eccentricity and tilt, modeled by coefficients $s_1, s_2, s_3, s_4$ that describe global stretch or compression in the image plane analogous to a thin prism effect. Magnitude is typically < 0.1 pixel and negligible for single-camera photography; in dual/triple stereo matching, AR alignment, and SLAM — applications requiring high-precision geometric alignment — thin prism residuals are non-negligible. OpenCV's `CALIB_THIN_PRISM_MODEL` flag supports this calibration.

**Zhang's Calibration Method**
A planar calibration target method proposed by Zhengyou Zhang (2000) that jointly solves camera intrinsics and distortion coefficients from multiple images of a checkerboard at different poses. Core principle: each image yields a homography matrix $\mathbf{H}$; each $\mathbf{H}$ provides 2 linear constraints on the intrinsic-related matrix $\mathbf{B} = \mathbf{K}^{-T}\mathbf{K}^{-1}$; the theoretical minimum of 3 images allows a linear solution ($\mathbf{B}$ has 5 degrees of freedom); engineering practice recommends 10–20 images covering different distances and tilt angles. Integrated into OpenCV's `calibrateCamera()`, it is the most widely used calibration method in both industry and academia.

**Homography Matrix (H)**
A $3\times3$ matrix (8 degrees of freedom, with an overall scale ambiguity) that describes the point-to-point mapping relationship between two planes. In Zhang's calibration method, the calibration target is planar ($Z=0$), and the mapping between the camera image and the target plane can be described by the homography $\mathbf{H} = \mathbf{K}[\mathbf{r}_1\ \mathbf{r}_2\ \mathbf{t}]$. At least 4 point correspondences can be used to solve for $\mathbf{H}$ with the Direct Linear Transform (DLT) algorithm (8 degrees of freedom).

**Kannala-Brandt Fisheye Model**
A projection model for large field-of-view (fisheye/ultra-wide-angle) lenses proposed by Kannala and Brandt (2006): $r(\theta) = k_1\theta + k_2\theta^3 + k_3\theta^5 + k_4\theta^7$, where $\theta$ is the angle between the incident ray and the optical axis and $r$ is the radial distance on the image plane. The polynomial contains only odd-degree terms because the projection function must be odd ($r(-\theta) = -r(\theta)$, satisfying central symmetry). OpenCV's `fisheye` module implements this model and is appropriate for calibrating ultra-wide-angle and fisheye lenses with FoV > 120°, where the Brown model is significantly inaccurate.

**Reprojection Error**
The core quantitative indicator of calibration quality: using the current calibration parameters, 3D corner points in the world coordinate system are reprojected onto the image plane; the RMS Euclidean distance from these reprojections to the detected 2D corner positions is computed, in units of pixels. An excellent calibration achieves < 0.3 px; < 0.5 px is acceptable for engineering purposes; > 1.0 px requires recalibration. Per-image analysis of the error distribution can identify anomalous images (poor capture quality, motion blur, etc.); removing outlier images and recalibrating typically produces significant improvement.

**Sub-pixel Refinement**
An algorithm that refines corner detection to sub-pixel accuracy using constraints from the gradient field near the corner: $\sum_{\mathbf{q} \in W}(\nabla I(\mathbf{q}) \cdot (\mathbf{q} - \hat{\mathbf{c}})) = 0$ (the gradient direction at the corner is orthogonal to the vector pointing toward the corner). OpenCV's `cornerSubPix()` implements this algorithm, improving corner localization accuracy from ~1 pixel to 0.01–0.1 pixel; it is a necessary preprocessing step for high-accuracy calibration.

**Essential Matrix (E)**
A geometric constraint matrix encoding the rotation and translation relationship between two cameras without camera intrinsics: $\mathbf{E} = [\mathbf{t}]_\times \mathbf{R}$, where $[\mathbf{t}]_\times$ is the skew-symmetric matrix of the translation vector and $\mathbf{R}$ is the rotation matrix. The essential matrix has rank **2** (in the non-degenerate case), with two equal non-zero singular values and $\det(\mathbf{E}) = 0$. It satisfies the epipolar constraint: $\mathbf{m}_2^T \mathbf{E} \mathbf{m}_1 = 0$ ($\mathbf{m}_1, \mathbf{m}_2$ are normalized camera coordinates).

**Fundamental Matrix (F)**
The pixel-coordinate version of the essential matrix, encoding combined intrinsic and extrinsic constraints for two cameras: $\mathbf{F} = \mathbf{K}_2^{-T} \mathbf{E} \mathbf{K}_1^{-1}$. It also satisfies the epipolar constraint $\mathbf{m}_2^T \mathbf{F} \mathbf{m}_1 = 0$ ($\mathbf{m}_1, \mathbf{m}_2$ are homogeneous pixel coordinates). The fundamental matrix also has rank 2 and can be solved from at least 7 point correspondences (7-point algorithm); in practice the 8-point algorithm with RANSAC is commonly used.

**Stereo Rectification**
A transformation that reprojects both stereo camera images so that scan lines are strictly aligned, ensuring that the corresponding point of any point in the left image lies on the same horizontal row in the right image (epipolar constraint). This reduces stereo matching from a 2D search to a 1D row scan, greatly reducing computational cost. Stereo rectification is implemented by OpenCV's `stereoRectify()`; the output rectification maps are applied to images using `remap()`.

**Homography Constraint**
Using the planar calibration target ($Z=0$) constraint to establish a projective correspondence between the camera image and the target plane. Each point correspondence provides 2 linear equations; 4 correspondences allow the homography matrix $\mathbf{H}$ to be solved linearly (8 degrees of freedom). In Zhang's calibration method, each $\mathbf{H}$ contributes 2 linear constraints on the intrinsic matrix, making it the core intermediate step of the entire calibration algorithm.

**EEPROM (Calibration Data Storage)**
A rewritable non-volatile memory (Electrically Erasable Programmable Read-Only Memory) inside smartphone camera modules used to store factory calibration data, typically integrated on the module FPC and communicating with the ISP driver via the I²C interface. Stored contents: camera intrinsics ($f_x, f_y, c_x, c_y$), distortion coefficients ($k_1, k_2, p_1, p_2, k_3$), LSC gain tables, AWB initial reference values, etc. Unlike OTP/eFuse (one-time programmable, used for permanent parameters such as sensor IDs), EEPROM can be rewritten after a module replacement during repair.

**ChArUco Calibration Board**
A calibration target that combines a checkerboard (Chessboard) with ArUco fiducial markers, embedding an ArUco marker with a unique ID inside each square. Compared to a pure checkerboard, the key advantage of a ChArUco board is **local visibility**: even if the target is partially occluded or extends beyond the field of view, the visible ArUco markers still provide valid corner coordinates (each ArUco marker has 4 checkerboard corners uniquely located around it); orientation is also unambiguous (a checkerboard rotated 180° is indistinguishable). Suitable for robotic automated production lines and occluded scenarios; the classic checkerboard has theoretically slightly better corner accuracy and is still widely used in controlled environments without occlusion.
