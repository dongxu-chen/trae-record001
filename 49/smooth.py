import math
from pathlib import Path
from typing import Union, List, Optional, Tuple

import numpy as np
import nibabel as nib
from nipype.interfaces.fsl import Smooth, SUSAN

FWHM_TO_SIGMA = 1.0 / (2.0 * math.sqrt(2.0 * math.log(2.0)))
SIGMA_TO_FWHM = 1.0 / FWHM_TO_SIGMA


def _fwhm_to_sigma(fwhm: Union[float, List[float], np.ndarray]) -> np.ndarray:
    """
    Convert Full Width at Half Maximum (FWHM) to Gaussian sigma.
    
    Formula: sigma = FWHM / (2 * sqrt(2 * ln(2))) ≈ FWHM / 2.354820045
    
    Parameters
    ----------
    fwhm : float or list of float or np.ndarray
        Full width at half maximum in mm.
        Can be scalar (isotropic) or [fx, fy, fz] (anisotropic).
    
    Returns
    -------
    np.ndarray
        Gaussian sigma(s) in mm.
    """
    fwhm_arr = np.atleast_1d(fwhm)
    return fwhm_arr * FWHM_TO_SIGMA


def _sigma_to_fwhm(sigma: Union[float, List[float], np.ndarray]) -> np.ndarray:
    """
    Convert Gaussian sigma to Full Width at Half Maximum (FWHM).
    
    Formula: FWHM = 2 * sqrt(2 * ln(2)) * sigma ≈ 2.354820045 * sigma
    """
    sigma_arr = np.atleast_1d(sigma)
    return sigma_arr * SIGMA_TO_FWHM


def _gaussian_kernel_1d(sigma: float, size: Optional[int] = None) -> np.ndarray:
    """
    Create a 1D Gaussian kernel.
    
    Parameters
    ----------
    sigma : float
        Standard deviation in voxel units.
    size : int, optional
        Kernel size. If None, uses 2*ceil(3*sigma) + 1.
    
    Returns
    -------
    np.ndarray
        1D Gaussian kernel normalized to sum=1.
    """
    if size is None:
        size = int(2 * np.ceil(3 * sigma) + 1)
    
    if size % 2 == 0:
        size += 1
    
    x = np.arange(size) - (size - 1) / 2.0
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    kernel /= kernel.sum()
    
    return kernel


def _separable_convolve_3d(data: np.ndarray, sigma_mm: np.ndarray,
                          voxel_size: np.ndarray) -> np.ndarray:
    """
    Perform 3D separable Gaussian convolution.
    
    Parameters
    ----------
    data : np.ndarray
        3D or 4D array. If 4D, shape should be (X, Y, Z, T).
    sigma_mm : np.ndarray
        Gaussian sigma in mm for [x, y, z] axes.
    voxel_size : np.ndarray
        Voxel size in mm for [x, y, z] axes.
    
    Returns
    -------
    np.ndarray
        Smoothed data array.
    """
    sigma_vox = sigma_mm / voxel_size
    
    is_4d = data.ndim == 4
    if is_4d:
        nx, ny, nz, nt = data.shape
    else:
        nx, ny, nz = data.shape
        data = data[..., np.newaxis]
        nt = 1
    
    result = data.copy()
    
    for axis, sigma in enumerate(sigma_vox):
        if sigma <= 0:
            continue
        
        kernel = _gaussian_kernel_1d(sigma)
        kernel_size = len(kernel)
        pad_width = kernel_size // 2
        
        for t in range(nt):
            volume = result[..., t]
            
            if axis == 0:
                padded = np.pad(volume, ((pad_width, pad_width), (0, 0), (0, 0)), mode='reflect')
                for y in range(ny):
                    for z in range(nz):
                        profile = padded[:, y, z]
                        result[:, y, z, t] = np.convolve(profile, kernel, mode='valid')
            elif axis == 1:
                padded = np.pad(volume, ((0, 0), (pad_width, pad_width), (0, 0)), mode='reflect')
                for x in range(nx):
                    for z in range(nz):
                        profile = padded[x, :, z]
                        result[x, :, z, t] = np.convolve(profile, kernel, mode='valid')
            else:
                padded = np.pad(volume, ((0, 0), (0, 0), (pad_width, pad_width)), mode='reflect')
                for x in range(nx):
                    for y in range(ny):
                        profile = padded[x, y, :]
                        result[x, y, :, t] = np.convolve(profile, kernel, mode='valid')
    
    if not is_4d:
        result = result[..., 0]
    
    return result


def gaussian_smooth_3d(
    input_file: Union[str, Path],
    output_dir: Union[str, Path],
    fwhm: Union[float, List[float], Tuple[float, float, float]] = 6.0,
    output_prefix: Optional[str] = None
) -> dict:
    """
    Apply 3D Gaussian smoothing using pure numpy (no FSL dependency).
    
    Supports both isotropic (scalar FWHM) and anisotropic (FWHM vector) smoothing.
    
    Parameters
    ----------
    input_file : str or Path
        Path to the input NIfTI file (3D or 4D).
    output_dir : str or Path
        Path to the output directory.
    fwhm : float or list/tuple of 3 floats
        Full width at half maximum in mm.
        - float: isotropic smoothing (same for all axes)
        - [fx, fy, fz]: anisotropic smoothing (different per axis)
    output_prefix : str, optional
        Prefix for output file. If None, uses input filename stem.
    
    Returns
    -------
    dict
        Dictionary containing:
        - out_file: Path to the smoothed NIfTI file
        - fwhm: FWHM(s) used
        - sigma: Gaussian sigma(s) used
        - voxel_size: Voxel size of the input
    """
    input_path = Path(input_file)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    fwhm_arr = np.atleast_1d(fwhm)
    if len(fwhm_arr) == 1:
        fwhm_arr = np.full(3, fwhm_arr[0])
    elif len(fwhm_arr) != 3:
        raise ValueError(
            f"FWHM must be scalar or 3-element vector, got {len(fwhm_arr)} elements"
        )
    
    if np.any(fwhm_arr <= 0):
        raise ValueError(f"FWHM must be positive, got: {fwhm_arr}")
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    img = nib.load(str(input_path))
    data = img.get_fdata()
    affine = img.affine
    header = img.header.copy()
    
    voxel_size = np.array(img.header.get_zooms()[:3])
    
    if data.ndim not in (3, 4):
        raise ValueError(
            f"Input must be 3D or 4D, got {data.ndim}D array"
        )
    
    sigma_mm = _fwhm_to_sigma(fwhm_arr)
    
    smoothed_data = _separable_convolve_3d(data, sigma_mm, voxel_size)
    
    if output_prefix is None:
        output_prefix = input_path.stem
    
    is_anisotropic = not np.allclose(fwhm_arr, fwhm_arr[0])
    if is_anisotropic:
        fwhm_str = f"{int(fwhm_arr[0])}x{int(fwhm_arr[1])}x{int(fwhm_arr[2])}"
    else:
        fwhm_str = f"{int(fwhm_arr[0])}"
    
    output_file = output_path / f'{output_prefix}_sm{fwhm_str}.nii.gz'
    
    out_img = nib.Nifti1Image(smoothed_data, affine, header)
    nib.save(out_img, str(output_file))
    
    return {
        'out_file': str(output_file),
        'fwhm': fwhm_arr.tolist(),
        'sigma': sigma_mm.tolist(),
        'voxel_size': voxel_size.tolist(),
        'is_anisotropic': is_anisotropic
    }


def gaussian_smooth(
    input_file: Union[str, Path],
    output_dir: Union[str, Path],
    fwhm: Union[float, List[float]] = 6.0,
    method: str = 'smooth',
    brightness_threshold: Optional[float] = None,
    use_median: bool = False,
    output_prefix: Optional[str] = None
) -> dict:
    """
    Apply Gaussian smoothing to fMRI data.
    
    Supports multiple backends and both isotropic/anisotropic smoothing.
    
    Parameters
    ----------
    input_file : str or Path
        Path to the input NIfTI file.
    output_dir : str or Path
        Path to the output directory.
    fwhm : float or list of float
        Full width at half maximum (FWHM) of the Gaussian kernel in mm.
        - float: isotropic smoothing
        - [fx, fy, fz]: anisotropic smoothing (requires method='numpy3d')
    method : str, optional
        Smoothing method/backend, by default 'smooth'.
        Options:
        - 'smooth': FSL's IsotropicSmooth (only isotropic)
        - 'susan': FSL's SUSAN (edge-preserving, isotropic)
        - 'numpy3d': Pure numpy 3D separable convolution (any FWHM vector)
    brightness_threshold : float, optional
        Brightness threshold for SUSAN method, by default None.
        Only used for method='susan'.
    use_median : bool, optional
        Apply median filtering before SUSAN, by default False.
        Only used for method='susan'.
    output_prefix : str, optional
        Output file prefix, by default None.
    
    Returns
    -------
    dict
        Dictionary containing output file paths and kernel parameters.
    """
    input_path = Path(input_file)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    fwhm_arr = np.atleast_1d(fwhm)
    is_anisotropic = len(fwhm_arr) > 1
    
    if is_anisotropic and method != 'numpy3d':
        raise ValueError(
            "Anisotropic FWHM vector only supported with method='numpy3d'. "
            f"Got method='{method}'."
        )
    
    if np.any(fwhm_arr <= 0):
        raise ValueError(f"FWHM must be positive, got: {fwhm_arr}")
    
    valid_methods = ['smooth', 'susan', 'numpy3d']
    if method not in valid_methods:
        raise ValueError(
            f"Unknown method: {method}. Use one of: {', '.join(valid_methods)}"
        )
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    if output_prefix is None:
        output_prefix = input_path.stem
    
    sigma = _fwhm_to_sigma(fwhm_arr)
    
    if method == 'numpy3d':
        return gaussian_smooth_3d(
            input_file=input_file,
            output_dir=output_dir,
            fwhm=fwhm,
            output_prefix=output_prefix
        )
    
    fwhm_scalar = float(fwhm_arr[0])
    if is_anisotropic:
        fwhm_str = f"{int(fwhm_arr[0])}x{int(fwhm_arr[1])}x{int(fwhm_arr[2])}"
    else:
        fwhm_str = f"{int(fwhm_scalar)}"
    
    output_file = str(output_path / f'{output_prefix}_sm{fwhm_str}.nii.gz')
    
    if method == 'smooth':
        smoother = Smooth()
        smoother.inputs.in_file = str(input_path)
        smoother.inputs.out_file = output_file
        smoother.inputs.fwhm = fwhm_scalar
        
        result = smoother.run()
        
        return {
            'out_file': result.outputs.out_file,
            'fwhm': fwhm_scalar,
            'sigma': float(sigma[0]),
            'method': method
        }
    
    elif method == 'susan':
        susan = SUSAN()
        susan.inputs.in_file = str(input_path)
        susan.inputs.out_file = output_file
        susan.inputs.sigma = float(sigma[0])
        
        if brightness_threshold is not None:
            if brightness_threshold <= 0:
                raise ValueError(
                    f"brightness_threshold must be positive, got: {brightness_threshold}"
                )
            susan.inputs.brightness_threshold = brightness_threshold
        else:
            susan.inputs.usans = [str(input_path)]
        
        if use_median:
            susan.inputs.use_median = True
        
        result = susan.run()
        
        return {
            'out_file': result.outputs.smoothed_file,
            'usan_size': result.outputs.usan_size,
            'fwhm': fwhm_scalar,
            'sigma': float(sigma[0]),
            'method': method
        }
    
    else:
        raise ValueError(f"Unknown method: {method}")
