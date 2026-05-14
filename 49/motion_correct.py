import os
import multiprocessing as mp
from pathlib import Path
from nipype.interfaces.fsl import MCFLIRT


def _process_single_subject(args):
    """
    Worker function for parallel processing.
    Unpacks arguments and calls motion_correction for a single subject.
    """
    (input_file, output_dir, subject_id, ref_vol, cost, interpolation,
     save_plots, dof, use_derivs, use_movpar, stages, final_interpolation) = args
    
    subject_output = Path(output_dir) / subject_id
    return motion_correction(
        input_file=input_file,
        output_dir=str(subject_output),
        ref_vol=ref_vol,
        cost=cost,
        interpolation=interpolation,
        save_plots=save_plots,
        dof=dof,
        use_derivs=use_derivs,
        use_movpar=use_movpar,
        stages=stages,
        final_interpolation=final_interpolation
    )


def motion_correction(input_file, output_dir, ref_vol=0, cost='normcorr',
                      interpolation='spline', save_plots=True,
                      dof=6, use_derivs=True, use_movpar=True,
                      stages=3, final_interpolation='spline'):
    """
    Perform motion correction on fMRI data using FSL MCFLIRT via Nipype.
    
    Includes stability improvements to prevent registration divergence.
    
    Parameters
    ----------
    input_file : str
        Path to the input 4D fMRI NIfTI file.
    output_dir : str
        Path to the directory where output files will be saved.
    ref_vol : int, optional
        Reference volume index for motion correction, by default 0.
    cost : str, optional
        Cost function for optimization, by default 'normcorr'.
        Options: 'mutualinfo', 'corratio', 'normcorr', 'normmi', 'leastssq'.
        For fMRI, 'normcorr' or 'corratio' are more stable than 'mutualinfo'.
    interpolation : str, optional
        Interpolation method for optimization stages, by default 'spline'.
        Options: 'trilinear', 'sinc', 'spline'.
    save_plots : bool, optional
        Whether to save motion parameter plots, by default True.
    dof : int, optional
        Degrees of freedom for transformation, by default 6 (rigid body).
        Options: 6 (rigid) or 12 (affine).
    use_derivs : bool, optional
        Whether to use derivatives in the cost function, by default True.
        Improves stability by including intensity gradient information.
    use_movpar : bool, optional
        Whether to use motion parameter regularization, by default True.
        Penalizes large motion jumps to prevent divergence.
    stages : int, optional
        Number of optimization stages, by default 3.
        More stages provide better convergence but slower.
    final_interpolation : str, optional
        Interpolation method for final resampling, by default 'spline'.
    
    Returns
    -------
    dict
        Dictionary containing output file paths.
    """
    input_path = Path(input_file)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    if cost not in ['mutualinfo', 'corratio', 'normcorr', 'normmi', 'leastssq']:
        raise ValueError(f"Invalid cost function: {cost}")
    
    if dof not in [6, 12]:
        raise ValueError(f"Invalid degrees of freedom: {dof}. Use 6 or 12.")
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    mcflirt = MCFLIRT()
    mcflirt.inputs.in_file = str(input_path)
    mcflirt.inputs.out_file = str(output_path / f'{input_path.stem}_mc.nii.gz')
    mcflirt.inputs.reference_vol = ref_vol
    mcflirt.inputs.cost = cost
    mcflirt.inputs.dof = dof
    mcflirt.inputs.interpolation = interpolation
    mcflirt.inputs.final_interpolation = final_interpolation
    mcflirt.inputs.use_derivs = use_derivs
    mcflirt.inputs.use_movpar = use_movpar
    mcflirt.inputs.stages = stages
    mcflirt.inputs.save_plots = save_plots
    mcflirt.inputs.save_rms = True
    mcflirt.inputs.save_mats = True
    mcflirt.inputs.save_mean = True
    
    result = mcflirt.run()
    
    outputs = {
        'out_file': result.outputs.out_file,
        'par_file': result.outputs.par_file,
        'rms_files': result.outputs.rms_files,
        'mat_files': result.outputs.mat_files,
        'mean_img': getattr(result.outputs, 'mean_img', None)
    }
    
    if save_plots:
        outputs['par_file_plot'] = getattr(result.outputs, 'par_file_plot', None)
    
    return outputs


def motion_correction_parallel(subjects, output_dir, n_jobs=None, **kwargs):
    """
    Perform motion correction for multiple subjects in parallel using
    multiprocessing.Pool.
    
    Parameters
    ----------
    subjects : dict
        Dictionary mapping subject IDs to input file paths.
        Example: {'sub-01': 'path/to/sub-01_bold.nii.gz', 'sub-02': 'path/to/sub-02_bold.nii.gz'}
    output_dir : str
        Base output directory. Each subject will have a subdirectory.
    n_jobs : int, optional
        Number of parallel processes. If None, uses os.cpu_count().
    **kwargs
        Additional arguments passed to motion_correction() for all subjects.
    
    Returns
    -------
    dict
        Dictionary mapping subject IDs to their motion correction results.
    """
    if n_jobs is None:
        n_jobs = max(1, os.cpu_count() - 1)
    else:
        n_jobs = max(1, min(n_jobs, os.cpu_count()))
    
    if not subjects:
        raise ValueError("No subjects provided for parallel processing")
    
    tasks = []
    for subject_id, input_file in subjects.items():
        if not Path(input_file).exists():
            raise FileNotFoundError(f"Input file not found for {subject_id}: {input_file}")
        
        tasks.append((
            input_file,
            output_dir,
            subject_id,
            kwargs.get('ref_vol', 0),
            kwargs.get('cost', 'normcorr'),
            kwargs.get('interpolation', 'spline'),
            kwargs.get('save_plots', True),
            kwargs.get('dof', 6),
            kwargs.get('use_derivs', True),
            kwargs.get('use_movpar', True),
            kwargs.get('stages', 3),
            kwargs.get('final_interpolation', 'spline')
        ))
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    if n_jobs == 1:
        results = [_process_single_subject(task) for task in tasks]
    else:
        with mp.Pool(processes=n_jobs) as pool:
            results = pool.map(_process_single_subject, tasks)
    
    return {subject_id: result for subject_id, result in zip(subjects.keys(), results)}
