from pathlib import Path
from typing import Union, List, Optional, Dict, Tuple
import warnings

import numpy as np
import nibabel as nib


def load_motion_parameters(par_file: Union[str, Path]) -> np.ndarray:
    """
    Load FSL MCFLIRT motion parameter file (.par file).
    
    MCFLIRT .par files contain 6 columns:
    [rot_x, rot_y, rot_z, trans_x, trans_y, trans_z]
    
    Parameters
    ----------
    par_file : str or Path
        Path to the motion parameter file.
    
    Returns
    -------
    np.ndarray
        Array of shape (n_volumes, 6) containing motion parameters.
    """
    par_path = Path(par_file)
    if not par_path.exists():
        raise FileNotFoundError(f"Motion parameter file not found: {par_file}")
    
    params = np.loadtxt(str(par_path))
    if params.ndim == 1:
        params = params.reshape(1, -1)
    
    if params.shape[1] != 6:
        raise ValueError(
            f"Expected 6 motion parameters, got {params.shape[1]}"
        )
    
    return params


def compute_motion_derivatives(params: np.ndarray) -> np.ndarray:
    """
    Compute temporal derivatives of motion parameters.
    
    First row is set to zero (no derivative for the first frame).
    
    Parameters
    ----------
    params : np.ndarray
        Motion parameters array of shape (n_volumes, 6).
    
    Returns
    -------
    np.ndarray
        Derivatives array of shape (n_volumes, 6).
    """
    derivs = np.zeros_like(params)
    derivs[1:, :] = np.diff(params, axis=0)
    return derivs


def compute_framewise_displacement(params: np.ndarray) -> np.ndarray:
    """
    Compute Framewise Displacement (FD) from motion parameters.
    
    Power et al. (2012, NeuroImage) definition:
    FD_t = |Δrot_x| + |Δrot_y| + |Δrot_z| + |Δtrans_x| + |Δtrans_y| + |Δtrans_z|
    
    Rotations converted to mm displacement on a 50mm sphere.
    
    Parameters
    ----------
    params : np.ndarray
        Motion parameters array of shape (n_volumes, 6).
    
    Returns
    -------
    np.ndarray
        FD array of shape (n_volumes,).
    """
    delta = np.zeros_like(params)
    delta[1:, :] = np.abs(np.diff(params, axis=0))
    
    radius = 50.0
    delta[:, :3] = delta[:, :3] * radius * (np.pi / 180.0)
    
    fd = np.sum(delta, axis=1)
    return fd


def build_dummy_vars(n_volumes: int, outlier_volumes: List[int]) -> np.ndarray:
    """
    Build motion outlier regressors (one-hot encoded dummy variables).
    
    Parameters
    ----------
    n_volumes : int
        Total number of volumes.
    outlier_volumes : list of int
        List of outlier volume indices (0-based).
    
    Returns
    -------
    np.ndarray
        Dummy regressors matrix of shape (n_volumes, n_outliers).
    """
    outlier_volumes = sorted(set(outlier_volumes))
    outlier_volumes = [i for i in outlier_volumes if 0 <= i < n_volumes]
    
    if not outlier_volumes:
        return np.zeros((n_volumes, 0))
    
    dummy = np.zeros((n_volumes, len(outlier_volumes)))
    for col, vol_idx in enumerate(outlier_volumes):
        dummy[vol_idx, col] = 1.0
    
    return dummy


def build_global_signal(nifti_file: Union[str, Path],
                        mask_file: Optional[Union[str, Path]] = None,
                        erode_mask: int = 1) -> np.ndarray:
    """
    Extract global signal from fMRI data.
    
    Parameters
    ----------
    nifti_file : str or Path
        Path to 4D fMRI NIfTI file.
    mask_file : str or Path, optional
        Path to binary brain mask. If None, uses all non-zero voxels.
    erode_mask : int, optional
        Number of erosion iterations for mask (to avoid edge effects), by default 1.
    
    Returns
    -------
    np.ndarray
        Global signal timeseries of shape (n_volumes,).
    """
    from scipy.ndimage import binary_erosion
    
    img = nib.load(str(nifti_file))
    data = img.get_fdata()
    
    if data.ndim != 4:
        raise ValueError(f"Expected 4D fMRI data, got {data.ndim}D")
    
    if mask_file is not None:
        mask_img = nib.load(str(mask_file))
        mask = mask_img.get_fdata() > 0
        for _ in range(erode_mask):
            mask = binary_erosion(mask)
    else:
        mask = np.any(data != 0, axis=-1)
    
    global_sig = np.mean(data[mask, :], axis=0)
    return global_sig


def build_confound_matrix(
    n_volumes: int,
    motion_params: Optional[np.ndarray] = None,
    include_motion_derivs: bool = True,
    include_motion_squares: bool = False,
    fd: Optional[np.ndarray] = None,
    fd_threshold: float = 0.5,
    global_signal: Optional[np.ndarray] = None,
    include_gs_deriv: bool = False,
    n_compcor: int = 0,
    compcor_data: Optional[np.ndarray] = None,
    add_intercept: bool = True,
    polynomial_degree: int = 0
) -> Tuple[np.ndarray, List[str]]:
    """
    Build a confound design matrix for nuisance regression.
    
    Parameters
    ----------
    n_volumes : int
        Number of fMRI volumes (time points).
    motion_params : np.ndarray, optional
        Motion parameters array of shape (n_volumes, 6), by default None.
    include_motion_derivs : bool, optional
        Include temporal derivatives of motion parameters (6 more regressors), by default True.
    include_motion_squares : bool, optional
        Include squared motion parameters and derivatives (12 more regressors), by default False.
        Implements the "24-parameter model" (Friston et al. 1996).
    fd : np.ndarray, optional
        Framewise displacement array of shape (n_volumes,), by default None.
        Used to identify outlier volumes for spike regression.
    fd_threshold : float, optional
        FD threshold for outlier detection (mm), by default 0.5.
    global_signal : np.ndarray, optional
        Global signal timeseries of shape (n_volumes,), by default None.
    include_gs_deriv : bool, optional
        Include derivative of global signal, by default False.
    n_compcor : int, optional
        Number of CompCor components to include, by default 0 (disabled).
    compcor_data : np.ndarray, optional
        Data matrix for CompCor (e.g., white matter signal), by default None.
        Shape should be (n_volumes, n_voxels/regions).
    add_intercept : bool, optional
        Add a constant intercept (column of ones), by default True.
    polynomial_degree : int, optional
        Degree of polynomial drift terms (0 = none, 1 = linear, 2 = quadratic...), by default 0.
    
    Returns
    -------
    tuple
        - confounds: Confound matrix of shape (n_volumes, n_regressors)
        - names: List of regressor names (same order as columns)
    """
    confounds = []
    names = []
    
    if motion_params is not None:
        if motion_params.shape[0] != n_volumes:
            raise ValueError(
                f"motion_params has {motion_params.shape[0]} rows, "
                f"expected {n_volumes}"
            )
        
        confounds.append(motion_params)
        names.extend(['motion_x', 'motion_y', 'motion_z',
                      'trans_x', 'trans_y', 'trans_z'])
        
        if include_motion_derivs:
            derivs = compute_motion_derivatives(motion_params)
            confounds.append(derivs)
            names.extend(['motion_dx', 'motion_dy', 'motion_dz',
                          'trans_dx', 'trans_dy', 'trans_dz'])
        
        if include_motion_squares:
            confounds.append(motion_params ** 2)
            names.extend(['motion_x2', 'motion_y2', 'motion_z2',
                          'trans_x2', 'trans_y2', 'trans_z2'])
            
            if include_motion_derivs:
                confounds.append(derivs ** 2)
                names.extend(['motion_dx2', 'motion_dy2', 'motion_dz2',
                              'trans_dx2', 'trans_dy2', 'trans_dz2'])
    
    if global_signal is not None:
        if len(global_signal) != n_volumes:
            raise ValueError(
                f"global_signal has {len(global_signal)} elements, "
                f"expected {n_volumes}"
            )
        
        gs = global_signal.reshape(-1, 1)
        confounds.append(gs)
        names.append('global_signal')
        
        if include_gs_deriv:
            gs_deriv = np.zeros_like(gs)
            gs_deriv[1:] = np.diff(gs, axis=0)
            confounds.append(gs_deriv)
            names.append('global_signal_deriv')
    
    if fd is not None:
        if len(fd) != n_volumes:
            raise ValueError(
                f"fd has {len(fd)} elements, expected {n_volumes}"
            )
        
        outliers = np.where(fd > fd_threshold)[0].tolist()
        if outliers:
            dummy = build_dummy_vars(n_volumes, outliers)
            confounds.append(dummy)
            names.extend([f'spike_{i}' for i in range(dummy.shape[1])])
    
    if n_compcor > 0 and compcor_data is not None:
        if compcor_data.shape[0] != n_volumes:
            raise ValueError(
                f"compcor_data has {compcor_data.shape[0]} rows, "
                f"expected {n_volumes}"
            )
        
        cc_centered = compcor_data - compcor_data.mean(axis=0)
        u, s, vh = np.linalg.svd(cc_centered, full_matrices=False)
        compcor_comps = u[:, :n_compcor]
        confounds.append(compcor_comps)
        names.extend([f'compcor_{i+1}' for i in range(n_compcor)])
    
    for deg in range(1, polynomial_degree + 1):
        trend = (np.arange(n_volumes) ** deg).reshape(-1, 1)
        confounds.append(trend)
        names.append(f'poly_{deg}')
    
    if add_intercept:
        intercept = np.ones((n_volumes, 1))
        confounds.append(intercept)
        names.append('intercept')
    
    if confounds:
        X = np.column_stack(confounds)
    else:
        X = np.zeros((n_volumes, 0))
    
    return X, names


def nuisance_regression(
    func_file: Union[str, Path],
    confound_matrix: np.ndarray,
    output_file: Union[str, Path],
    mask_file: Optional[Union[str, Path]] = None
) -> str:
    """
    Perform nuisance regression on fMRI data.
    
    Parameters
    ----------
    func_file : str or Path
        Path to 4D fMRI NIfTI file.
    confound_matrix : np.ndarray
        Confound design matrix of shape (n_volumes, n_regressors).
    output_file : str or Path
        Path to save the residual NIfTI file.
    mask_file : str or Path, optional
        Path to binary brain mask. If None, processes all voxels.
    
    Returns
    -------
    str
        Path to the output residual NIfTI file.
    """
    func_path = Path(func_file)
    output_path = Path(output_file)
    
    if not func_path.exists():
        raise FileNotFoundError(f"Functional file not found: {func_file}")
    
    img = nib.load(str(func_path))
    data = img.get_fdata()
    
    if data.ndim != 4:
        raise ValueError(f"Expected 4D fMRI data, got {data.ndim}D")
    
    nx, ny, nz, nt = data.shape
    
    if confound_matrix.shape[0] != nt:
        raise ValueError(
            f"Confound matrix has {confound_matrix.shape[0]} rows, "
            f"data has {nt} volumes"
        )
    
    if mask_file is not None:
        mask_img = nib.load(str(mask_file))
        mask = mask_img.get_fdata() > 0
    else:
        mask = np.ones((nx, ny, nz), dtype=bool)
    
    Y = data[mask, :].T
    
    X = confound_matrix
    X = np.asarray(X, dtype=float)
    
    if X.shape[1] > 0:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", np.RankWarning)
            beta, residuals, rank, s = np.linalg.lstsq(X, Y, rcond=None)
        
        Y_resid = Y - X @ beta
    else:
        Y_resid = Y
    
    resid_data = np.zeros_like(data)
    resid_data[mask, :] = Y_resid.T
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    resid_img = nib.Nifti1Image(resid_data, img.affine, img.header)
    nib.save(resid_img, str(output_path))
    
    return str(output_path)


def denoise_fmri(
    func_file: Union[str, Path],
    output_dir: Union[str, Path],
    motion_par_file: Optional[Union[str, Path]] = None,
    mask_file: Optional[Union[str, Path]] = None,
    global_signal_file: Optional[Union[str, Path]] = None,
    include_motion: bool = True,
    include_motion_derivs: bool = True,
    include_motion_squares: bool = False,
    include_global_signal: bool = False,
    fd_threshold: float = 0.5,
    include_spikes: bool = True,
    polynomial_degree: int = 1,
    output_prefix: Optional[str] = None
) -> Dict:
    """
    High-level convenience function for fMRI denoising with nuisance regression.
    
    Parameters
    ----------
    func_file : str or Path
        Path to 4D fMRI NIfTI file.
    output_dir : str or Path
        Directory to save outputs.
    motion_par_file : str or Path, optional
        Path to MCFLIRT .par motion parameter file.
    mask_file : str or Path, optional
        Path to binary brain mask.
    global_signal_file : str or Path, optional
        Path to text file with global signal (one value per line).
        If None and include_global_signal=True, will compute from func_file.
    include_motion : bool, optional
        Include 6 motion parameters, by default True.
    include_motion_derivs : bool, optional
        Include 6 motion parameter derivatives, by default True.
    include_motion_squares : bool, optional
        Include squared motion terms (24-parameter model), by default False.
    include_global_signal : bool, optional
        Include global signal regression, by default False.
    fd_threshold : float, optional
        FD threshold for spike regression, by default 0.5.
    include_spikes : bool, optional
        Include spike regressors for high-motion volumes, by default True.
    polynomial_degree : int, optional
        Polynomial drift model degree, by default 1 (linear drift).
    output_prefix : str, optional
        Prefix for output files, by default uses func_file stem.
    
    Returns
    -------
    dict
        Dictionary containing output paths and regressor information.
    """
    func_path = Path(func_file)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if output_prefix is None:
        output_prefix = func_path.stem
    
    img = nib.load(str(func_path))
    n_volumes = img.shape[-1] if img.ndim == 4 else 1
    
    motion_params = None
    fd = None
    if motion_par_file and include_motion:
        motion_params = load_motion_parameters(motion_par_file)
        if include_spikes:
            fd = compute_framewise_displacement(motion_params)
    
    global_signal = None
    if include_global_signal:
        if global_signal_file and Path(global_signal_file).exists():
            global_signal = np.loadtxt(str(global_signal_file))
        else:
            global_signal = build_global_signal(func_file, mask_file)
    
    confound_matrix, regressor_names = build_confound_matrix(
        n_volumes=n_volumes,
        motion_params=motion_params if include_motion else None,
        include_motion_derivs=include_motion_derivs,
        include_motion_squares=include_motion_squares,
        fd=fd if include_spikes else None,
        fd_threshold=fd_threshold,
        global_signal=global_signal,
        polynomial_degree=polynomial_degree,
        add_intercept=True
    )
    
    resid_file = output_path / f'{output_prefix}_residual.nii.gz'
    nuisance_regression(
        func_file=func_file,
        confound_matrix=confound_matrix,
        output_file=str(resid_file),
        mask_file=mask_file
    )
    
    design_file = output_path / f'{output_prefix}_design_matrix.tsv'
    header = '\t'.join(regressor_names)
    np.savetxt(str(design_file), confound_matrix, delimiter='\t',
               header=header, comments='')
    
    return {
        'residual_file': str(resid_file),
        'design_matrix_file': str(design_file),
        'n_regressors': len(regressor_names),
        'regressor_names': regressor_names
    }
