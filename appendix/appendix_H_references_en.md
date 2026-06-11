# Appendix H — References | 参考文献

> Master reference list for the ISP Algorithm Handbook, organized by topic.
> Citations are in author-year format. Full bibliographic details provided where available.

---

## H.1 Textbooks — Imaging Physics & Optics

**[Hecht2017]** Hecht, E. (2017). *Optics* (5th ed.). Pearson.
> Canonical optics textbook. Covers wave optics, geometric optics, aberrations, interference, diffraction. Referenced in Ch02.

**[Born1999]** Born, M., & Wolf, E. (1999). *Principles of Optics* (7th ed.). Cambridge University Press.
> Comprehensive treatment of physical optics including coherence theory and image formation. Advanced reference for Ch02.

**[Holst2011]** Holst, G. C., & Lomheim, T. S. (2011). *CMOS/CCD Sensors and Camera Systems* (2nd ed.). JCD Publishing.
> Sensor physics reference: quantum efficiency, full well capacity, dark current, noise sources. Referenced in Ch04.

**[Nakamura2006]** Nakamura, J. (2006). *Image Sensors and Signal Processing for Digital Still Cameras*. CRC Press.
> Practical reference covering CMOS/CCD sensor design and ISP pipeline implementation. Referenced in Part 1 and Part 2.

---

## H.2 Noise Models

**[Foi2008]** Foi, A., Trimeche, M., Katkovnik, V., & Egiazarian, K. (2008). Practical Poissonian-Gaussian noise modeling and fitting for single-image raw-data. *IEEE Transactions on Image Processing*, 17(10), 1737–1754.
> The standard Poisson-Gaussian noise model for RAW images. Defines the PTC model σ²(I) = αI + β. Referenced in Ch04.

**[Healey1994]** Healey, G. E., & Kondepudy, R. (1994). Radiometric CCD camera calibration and noise estimation. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 16(3), 267–276.
> Early work on CCD noise calibration. Foundation for PTC measurement methodology.

**[Plotz2017]** Plötz, T., & Roth, S. (2017). Benchmarking denoising algorithms with real photographs. *CVPR 2017*.
> Introduces the DND denoising benchmark dataset. Describes methodology for capturing real noisy-clean pairs.

**[Abdelhamed2018]** Abdelhamed, A., Lin, S., & Brown, M. S. (2018). A high-quality denoising dataset for smartphone cameras. *CVPR 2018*.
> Introduces the SIDD dataset. Details the capture protocol for real smartphone noise ground truth. Referenced in Ch20, App E.

---

## H.3 Color Science

**[Wyszecki1982]** Wyszecki, G., & Stiles, W. S. (1982). *Color Science: Concepts and Methods, Quantitative Data and Formulae* (2nd ed.). Wiley.
> The definitive color science reference. Covers CIE standards, color matching functions, color difference formulas. Referenced in Ch05.

**[Fairchild2013]** Fairchild, M. D. (2013). *Color Appearance Models* (3rd ed.). Wiley.
> Color appearance models including CIECAM02. Covers chromatic adaptation, color constancy, and perceptual attributes. Referenced in Ch05, Ch22.

**[Sharma2005]** Sharma, G., Wu, W., & Dalal, E. N. (2005). The CIEDE2000 color-difference formula. *Color Research & Application*, 30(1), 21–30.
> The definitive paper defining the CIEDE2000 (ΔE₀₀) color difference formula. Referenced in Ch23, App A, App G.

**[Reinhard2010]** Reinhard, E., Heidrich, W., Debevec, P., Pattanaik, S., Ward, G., & Myszkowski, K. (2010). *High Dynamic Range Imaging: Acquisition, Display, and Image-Based Lighting* (2nd ed.). Morgan Kaufmann.
> Comprehensive HDR imaging reference. Covers tone mapping, HDR capture, and display. Referenced in Ch24, Ch27.

**[Ebner2007]** Ebner, M. (2007). *Color Constancy*. Wiley.
> Comprehensive coverage of color constancy algorithms. Foundation for Ch22 AWB.

---

## H.4 Traditional ISP Algorithms

### Demosaicing

**[Malvar2004]** Malvar, H. S., He, L., & Cutler, R. (2004). High-quality linear interpolation for demosaicing of Bayer-patterned color images. *ICASSP 2004*.
> The Malvar-He-Cutler (MHC) demosaic algorithm. Fast, second-order accurate. Referenced in Ch19.

**[Menon2007]** Menon, D., Andriani, S., & Calvagno, G. (2007). Demosaicing with directional filtering and a posteriori decision. *IEEE Transactions on Image Processing*, 16(1), 132–141.
> DDFAPD demosaic algorithm. Referenced in Ch19.

**[Getreuer2011]** Getreuer, P. (2011). Malvar-He-Cutler linear image demosaicking. *Image Processing On Line*, 1.
> Open-access IPOL paper with full algorithm derivation and code. Referenced in Ch19.

**[Zhang2005]** Zhang, L., & Wu, X. (2005). Color demosaicking via directional linear minimum mean square-error estimation. *IEEE Transactions on Image Processing*, 14(12), 2167–2178.
> LMMSE demosaic; referenced in RawTherapee implementation.

### Denoising

**[Dabov2007]** Dabov, K., Foi, A., Katkovnik, V., & Egiazarian, K. (2007). Image denoising by sparse 3-D transform-domain collaborative filtering. *IEEE Transactions on Image Processing*, 16(8), 2080–2095.
> BM3D algorithm. State-of-the-art non-local denoising. Referenced in Ch20.

**[Buades2005]** Buades, A., Coll, B., & Morel, J. M. (2005). A non-local algorithm for image denoising. *CVPR 2005*.
> NL-means algorithm. Foundation for non-local denoising. Referenced in Ch20.

**[Tomasi1998]** Tomasi, C., & Manduchi, R. (1998). Bilateral filtering for gray and color images. *ICCV 1998*.
> Bilateral filter — edge-preserving spatial denoising. Referenced in Ch20.

### White Balance

**[Buchsbaum1980]** Buchsbaum, G. (1980). A spatial processor model for object colour perception. *Journal of the Franklin Institute*, 310(1), 1–26.
> Gray world assumption for color constancy. Referenced in Ch22.

**[Joze2012]** Joze, H. R. V., & Drew, M. S. (2012). Exemplar-based color constancy and multiple illumination. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 36(5), 860–873.
> Overview of color constancy methods. Referenced in Ch22.

**[Cheng2014]** Cheng, D., Price, B., Cohen, S., & Brown, M. S. (2014). Illuminant estimation for color constancy: why spatial-domain methods work and the role of the color distribution. *Journal of the Optical Society of America A*, 31(5), 1049–1058.

### Lens Shading Correction

**[Goldman2010]** Goldman, D. B. (2010). Vignette and exposure calibration and compensation. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 32(12), 2276–2288.
> Vignetting model and calibration. Referenced in Ch25.

### Color Correction Matrix

**[Finlayson2015]** Finlayson, G. D., & Mackiewicz, M. (2015). Optimization of colour correction matrices. *IS&T/SPIE Electronic Imaging*.
> CCM optimization strategies. Referenced in Ch23.

---

## H.5 Deep Learning ISP

**[Chen2018]** Chen, C., Chen, Q., Xu, J., & Koltun, V. (2018). Learning to see in the dark. *CVPR 2018*.
> See-in-the-Dark (SID) network. End-to-end RAW to RGB in extreme low light. Referenced in Ch35.

**[Ignatov2020]** Ignatov, A., Timofte, R., et al. (2020). AIM 2020 challenge on learned image signal processing pipeline. *ECCV Workshops 2020*.
> Learned ISP competition. Reviews multiple end-to-end ISP approaches. Referenced in Ch34.

**[Zamir2022]** Zamir, S. W., et al. (2022). Restormer: Efficient transformer for high-resolution image restoration. *CVPR 2022*.
> Transformer-based image restoration architecture. Referenced in Ch35.

**[Chen2022]** Chen, L., et al. (2022). Simple baselines for image restoration (NAFNet). *ECCV 2022*.
> NAFNet architecture; strong SIDD benchmark result. Referenced in Ch35, App D.

**[Liang2021]** Liang, J., et al. (2021). SwinIR: Image restoration using swin transformer. *ICCV Workshops 2021*.
> SwinIR; Swin Transformer for image restoration. Referenced in Ch35, Ch36.

**[Wang2021]** Wang, X., et al. (2021). Real-ESRGAN: Training real-world blind super-resolution with pure synthetic data. *ICCV Workshops 2021*.
> Real-ESRGAN; practical blind SR. Referenced in Ch36, App D.

**[Lehtinen2018]** Lehtinen, J., et al. (2018). Noise2Noise: Learning image restoration without clean data. *ICML 2018*.
> Denoising without clean target images. Referenced in Ch20, App D.

**[Zhang2017]** Zhang, K., Zuo, W., Chen, Y., Meng, D., & Zhang, L. (2017). Beyond a Gaussian denoiser: Residual learning of deep CNN for image denoising. *IEEE Transactions on Image Processing*, 26(7), 3142–3155.
> DnCNN. Residual learning for denoising. Referenced in Ch20, Ch34.

**[Ho2020]** Ho, J., Jain, A., & Abbeel, P. (2020). Denoising diffusion probabilistic models. NeurIPS 2020. https://arxiv.org/abs/2006.11239
> DDPM; foundational generative model using iterative diffusion. Referenced in Part 5.

**[Radford2021]** Radford, A., Kim, J. W., Hallacy, C., Ramesh, A., Goh, G., Agarwal, S., ... & Sutskever, I. (2021). Learning transferable visual models from natural language supervision. ICML 2021. https://arxiv.org/abs/2103.00020
> CLIP; contrastive language-image pretraining. Foundation model for vision-language alignment. Referenced in Ch56, Part 5.

**[Kirillov2023]** Kirillov, A., Mintun, E., Ravi, N., Mao, H., Rolland, C., Gustafson, L., ... & Girshick, R. (2023). Segment anything. ICCV 2023. https://arxiv.org/abs/2304.02643
> SAM (Segment Anything Model); promptable segmentation foundation model. Referenced in Ch56, Part 5.

---

## H.6 Image Quality Assessment

**[Wang2004]** Wang, Z., Bovik, A. C., Sheikh, H. R., & Simoncelli, E. P. (2004). Image quality assessment: From error visibility to structural similarity. *IEEE Transactions on Image Processing*, 13(4), 600–612.
> SSIM. Most cited IQA paper. Referenced throughout Part 4.

**[Zhang2018]** Zhang, R., Isola, P., Efros, A. A., Shechtman, E., & Wang, O. (2018). The unreasonable effectiveness of deep features as a perceptual metric. *CVPR 2018*.
> LPIPS. Perceptual similarity via deep features. Referenced in Ch47.

**[Mittal2012]** Mittal, A., Moorthy, A. K., & Bovik, A. C. (2012). No-reference image quality assessment in the spatial domain. *IEEE Transactions on Signal Processing*, 60(12), 6248–6261.
> BRISQUE. Blind spatial-domain NR-IQA. Referenced in Ch47.

**[Zhang2015]** Zhang, L., Zhang, L., & Bovik, A. C. (2015). A feature-enriched completely blind image quality evaluator. *IEEE Transactions on Image Processing*, 24(8), 2579–2591.
> IL-NIQE. Natural image quality evaluator. Referenced in Ch47.

**[Fang2020]** Fang, Y., Zhu, H., Zeng, Y., Ma, K., & Wang, Z. (2020). Perceptual quality assessment of smartphone photography. *CVPR 2020*.
> SPAQ dataset and model. Referenced in Ch47.

---

## H.7 Datasets

**[Ponomarenko2015]** Ponomarenko, N., et al. (2015). Image database TID2013: Peculiarities, results and perspectives. *Signal Processing: Image Communication*, 30, 57–77.
> TID2013 dataset. Referenced in App E.

**[Peng2021]** Peng, J., et al. (2021). KADID-10k: A large-scale artificially distorted IQA database. *QoMEX 2021*.
> KADID-10k dataset. Referenced in App E.

**[Agustsson2017]** Agustsson, E., & Timofte, R. (2017). NTIRE 2017 challenge on single image super-resolution: Dataset and study. *CVPR Workshops 2017*.
> DIV2K dataset. Referenced in App E.

---

## H.8 Standards and Technical Reports

**[IEC61966]** IEC 61966-2-1:1999. *Multimedia systems and equipment — Colour measurement and management — Part 2-1: Colour management — Default RGB colour space — sRGB*. International Electrotechnical Commission.
> sRGB standard. Defines the sRGB transfer function and primaries. Referenced in Ch26.

**[ITU-R BT.709]** ITU-R BT.709-6:2015. *Parameter values for the HDTV standards for production and international programme exchange*. International Telecommunication Union.
> Rec. 709 standard. HDTV primaries, transfer function. Referenced in Ch26.

**[ITU-R BT.2020]** ITU-R BT.2020-2:2015. *Parameter values for ultra-high definition television systems for production and international programme exchange*. International Telecommunication Union.
> Rec. 2020 / BT.2020. Wide gamut standard for UHD/HDR video. Referenced in Ch26.

**[ITU-R BT.2100]** ITU-R BT.2100-2:2018. *Image parameter values for high dynamic range television for use in production and international programme exchange*.
> HDR standards: HLG and PQ (ST 2084) transfer functions. Referenced in Ch24, Ch27.

**[ISO12233]** ISO 12233:2017. *Photography — Electronic still picture imaging — Resolution and spatial frequency responses*. International Organization for Standardization.
> Slanted-edge MTF measurement standard. Referenced in Ch21, App B.

**[EMVA1288]** EMVA Standard 1288, Release 4.0. *Standard for Characterization of Image Sensors and Cameras*. European Machine Vision Association. https://www.emva.org/standards-technology/emva-1288/
> Defines PTC measurement, noise model calibration, SNR characterization for machine vision cameras. Referenced in Ch04.

---

## H.9 Open-Access Courses and Tutorials

**[Szeliski2022]** Szeliski, R. (2022). *Computer Vision: Algorithms and Applications* (2nd ed.). Springer. Free PDF: https://szeliski.org/Book/
> Comprehensive computer vision textbook. Chapters on image formation, sensors, and image processing. Referenced throughout Part 1.

**[Brown2019]** Brown, M. S. (2019). Understanding the in-camera image processing pipeline for computer vision. *CVPR 2019 Tutorial*. https://www.eecg.utoronto.ca/~mbrown/CVPR2019_ISP_tutorial.html
> Excellent overview of the ISP pipeline from a computer vision perspective. Highly recommended introductory material.

**[Imatest Documentation]** Imatest LLC. *Imatest Documentation*. https://www.imatest.com/docs/
> Public documentation covering MTF, noise, color, distortion, and other IQA measurement methods. Primary reference for evaluation methodology throughout the handbook.

**[colour-science Documentation]** colour-science.org contributors. *colour — Colour Science for Python*. https://colour.readthedocs.io/
> Comprehensive color science library documentation with mathematical background for each function. Referenced in Ch05, Ch22, Ch23.

**[Stanford CS231n]** Li, F., Johnson, J., & Yeung, S. (2017). *CS231n: Convolutional Neural Networks for Visual Recognition*. Stanford University. http://cs231n.stanford.edu/
> Deep learning for visual recognition course. Referenced in Part 3 DL ISP.

---

## H.10 Key Survey Papers

**[Kaur2021]** Kaur, R., et al. (2021). A survey on image restoration: Insights and future directions. *Image and Vision Computing*, 108, 104090.
> Survey of traditional and deep learning image restoration methods.

**[Liu2020]** Liu, J., et al. (2020). Deep learning for pixel-level image fusion: Recent advances and future prospects. *Information Fusion*, 90, 31–52.

**[Zamir2020]** Zamir, S. W., et al. (2020). Learning enriched features for real image restoration and enhancement. *ECCV 2020*.
> MIRNet; multi-scale feature learning for restoration.

**[Chen2021]** Chen, C., et al. (2021). Pre-trained image processing transformer. *CVPR 2021*.
> IPT; Transformer for multiple image restoration tasks.
