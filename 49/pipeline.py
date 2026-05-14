from pathlib import Path
from nipype import Workflow, Node, IdentityInterface
from nipype.interfaces.fsl import BET, MCFLIRT, Smooth
from nipype.interfaces.dcm2nii import Dcm2niix
from nipype.interfaces.utility import Function


def _get_first_file(file_list):
    if isinstance(file_list, list):
        return file_list[0]
    return file_list


def preprocessing_workflow(dicom_dir, output_dir, subject_id='sub-01',
                          fwhm=6.0, frac=0.3, ref_vol=0,
                          smoothing_method='smooth', name='fmri_preproc'):
    """
    Create a complete fMRI preprocessing workflow using Nipype.
    
    Pipeline Steps:
    1. DICOM to NIfTI conversion
    2. Brain extraction (skull stripping)
    3. Motion correction
    4. Gaussian smoothing
    
    Parameters
    ----------
    dicom_dir : str
        Path to the directory containing DICOM files.
    output_dir : str
        Path to the directory where all output files will be saved.
    subject_id : str, optional
        Subject identifier for output naming, by default 'sub-01'.
    fwhm : float, optional
        Full width at half maximum for Gaussian smoothing in mm, by default 6.0.
    frac : float, optional
        Fractional intensity threshold for BET, by default 0.3.
        For fMRI, use 0.2-0.35 to prevent brain tissue loss.
        Smaller values = more inclusive brain outline.
    ref_vol : int, optional
        Reference volume index for motion correction, by default 0.
    smoothing_method : str, optional
        Smoothing method: 'smooth' (FSL Smooth) or 'susan' (FSL SUSAN), by default 'smooth'.
    name : str, optional
        Name of the workflow, by default 'fmri_preproc'.
    
    Returns
    -------
    nipype.pipeline.engine.Workflow
        The complete preprocessing workflow.
    """
    output_path = Path(output_dir)
    working_dir = output_path / 'working_dir'
    output_path.mkdir(parents=True, exist_ok=True)
    working_dir.mkdir(parents=True, exist_ok=True)
    
    wf = Workflow(name=name, base_dir=str(working_dir))
    
    inputspec = Node(IdentityInterface(fields=['dicom_dir']), name='inputspec')
    inputspec.inputs.dicom_dir = dicom_dir
    
    dcm2niix = Node(Dcm2niix(), name='dicom2nifti')
    dcm2niix.inputs.bids_format = True
    dcm2niix.inputs.compress = 'y'
    dcm2niix.inputs.verbose = True
    dcm2niix.inputs.output_dir = str(output_path / 'nifti')
    
    wf.connect(inputspec, 'dicom_dir', dcm2niix, 'source_dir')
    
    get_func = Node(
        Function(
            input_names=['file_list'],
            output_names=['func_file'],
            function=_get_first_file
        ),
        name='get_func_file'
    )
    wf.connect(dcm2niix, 'converted_files', get_func, 'file_list')
    
    bet = Node(BET(), name='brain_extraction')
    bet.inputs.frac = frac
    bet.inputs.mask = True
    bet.inputs.functional = True
    bet.inputs.robust = True
    bet.inputs.reduce_bias = True
    bet.inputs.out_file = str(output_path / f'{subject_id}_brain.nii.gz')
    
    wf.connect(get_func, 'func_file', bet, 'in_file')
    
    mcflirt = Node(MCFLIRT(), name='motion_correction')
    mcflirt.inputs.reference_vol = ref_vol
    mcflirt.inputs.cost = 'normcorr'
    mcflirt.inputs.dof = 6
    mcflirt.inputs.interpolation = 'spline'
    mcflirt.inputs.final_interpolation = 'spline'
    mcflirt.inputs.use_derivs = True
    mcflirt.inputs.use_movpar = True
    mcflirt.inputs.stages = 3
    mcflirt.inputs.save_plots = True
    mcflirt.inputs.save_rms = True
    mcflirt.inputs.save_mean = True
    mcflirt.inputs.out_file = str(output_path / f'{subject_id}_mc.nii.gz')
    
    wf.connect(bet, 'out_file', mcflirt, 'in_file')
    
    smooth = Node(Smooth(), name='smoothing')
    smooth.inputs.fwhm = fwhm
    smooth.inputs.out_file = str(output_path / f'{subject_id}_sm{int(fwhm)}.nii.gz')
    
    wf.connect(mcflirt, 'out_file', smooth, 'in_file')
    
    outputspec = Node(
        IdentityInterface(fields=[
            'nifti_file',
            'brain_file',
            'brain_mask',
            'motion_corrected',
            'motion_params',
            'rms_files',
            'mean_img',
            'smoothed_file'
        ]),
        name='outputspec'
    )
    
    wf.connect(get_func, 'func_file', outputspec, 'nifti_file')
    wf.connect(bet, 'out_file', outputspec, 'brain_file')
    wf.connect(bet, 'mask_file', outputspec, 'brain_mask')
    wf.connect(mcflirt, 'out_file', outputspec, 'motion_corrected')
    wf.connect(mcflirt, 'par_file', outputspec, 'motion_params')
    wf.connect(mcflirt, 'rms_files', outputspec, 'rms_files')
    wf.connect(mcflirt, 'mean_img', outputspec, 'mean_img')
    wf.connect(smooth, 'out_file', outputspec, 'smoothed_file')
    
    return wf


def run_preprocessing(dicom_dir, output_dir, **kwargs):
    """
    Run the complete fMRI preprocessing workflow.
    
    Parameters
    ----------
    dicom_dir : str
        Path to the directory containing DICOM files.
    output_dir : str
        Path to the directory where all output files will be saved.
    **kwargs
        Additional parameters passed to preprocessing_workflow().
    
    Returns
    -------
    dict
        Dictionary containing output file paths.
    """
    wf = preprocessing_workflow(dicom_dir, output_dir, **kwargs)
    results = wf.run()
    
    output_node = results.nodes[-1]
    outputs = output_node.result.outputs
    
    result_dict = {
        'nifti_file': outputs.nifti_file,
        'brain_file': outputs.brain_file,
        'brain_mask': outputs.brain_mask,
        'motion_corrected': outputs.motion_corrected,
        'motion_params': outputs.motion_params,
        'rms_files': outputs.rms_files,
        'mean_img': getattr(outputs, 'mean_img', None),
        'smoothed_file': outputs.smoothed_file
    }
    
    return {k: v for k, v in result_dict.items() if v is not None}
