from pathlib import Path
from nipype.interfaces.fsl import BET


def _get_default_frac(functional):
    """
    Get default fractional intensity threshold based on image type.
    
    For anatomical images: frac ≈ 0.5
    For fMRI (functional) images: frac ≈ 0.3 (lower = more inclusive = less brain tissue loss)
    """
    return 0.3 if functional else 0.5


def brain_extraction(input_file, output_dir, frac=None, functional=True,
                     mask=True, threshold=False, robust=True,
                     reduce_bias=True, outline=False, out_prefix=None):
    """
    Perform brain extraction (skull stripping) using FSL BET via Nipype.
    
    Optimized to prevent brain tissue loss, especially for fMRI data.
    
    Parameters
    ----------
    input_file : str
        Path to the input NIfTI file.
    output_dir : str
        Path to the directory where output files will be saved.
    frac : float, optional
        Fractional intensity threshold (0-1).
        - None (default): Use type-appropriate default (0.3 for functional, 0.5 for anatomical)
        - Smaller values give larger brain outline estimates (more inclusive)
        - Larger values give smaller brain outline estimates (more exclusive)
        For fMRI, use 0.2-0.35 to prevent tissue loss.
    functional : bool, optional
        Whether the input is a 4D fMRI time series, by default True.
        Set to True for fMRI data, enables BET's functional mode (-F).
    mask : bool, optional
        Whether to generate a binary brain mask, by default True.
    threshold : bool, optional
        Whether to apply thresholding to the brain mask, by default False.
        When True, uses segmented volume instead of binary mask.
    robust : bool, optional
        Whether to use robust brain center estimation (-R), by default True.
        Essential for fMRI and images with large neck or poor background.
    reduce_bias : bool, optional
        Whether to run bias-field cleanup and neck cleanup (-S), by default True.
        Helps with gradient-echo fMRI data that has intensity inhomogeneities.
    outline : bool, optional
        Whether to save the brain surface outline overlay, by default False.
    out_prefix : str, optional
        Prefix for output files, by default None.
        If None, uses the input filename.
    
    Returns
    -------
    dict
        Dictionary containing output file paths.
    """
    input_path = Path(input_file)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    if frac is None:
        frac = _get_default_frac(functional)
    
    if frac < 0.0 or frac > 1.0:
        raise ValueError(f"frac must be between 0 and 1, got: {frac}")
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    prefix = out_prefix if out_prefix else input_path.stem
    out_file = str(output_path / f'{prefix}_brain.nii.gz')
    
    bet = BET()
    bet.inputs.in_file = str(input_path)
    bet.inputs.out_file = out_file
    bet.inputs.frac = frac
    bet.inputs.functional = functional
    bet.inputs.mask = mask
    bet.inputs.threshold = threshold
    bet.inputs.robust = robust
    bet.inputs.reduce_bias = reduce_bias
    
    if outline:
        bet.inputs.outline = True
    
    result = bet.run()
    
    outputs = {
        'out_file': result.outputs.out_file,
        'frac_used': frac
    }
    
    if mask:
        outputs['mask_file'] = result.outputs.mask_file
    
    if threshold:
        outputs['threshold_file'] = result.outputs.threshold_file
    
    if outline:
        outputs['outline_file'] = getattr(result.outputs, 'outline_file', None)
    
    return outputs
