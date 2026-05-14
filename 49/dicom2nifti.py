from pathlib import Path
from nipype.interfaces.dcm2nii import Dcm2niix


def dicom_to_nifti(dicom_dir, output_dir, compress=True, bids=True):
    """
    Convert DICOM files to NIfTI format using dcm2niix via Nipype.
    
    Parameters
    ----------
    dicom_dir : str
        Path to the directory containing DICOM files.
    output_dir : str
        Path to the directory where converted NIfTI files will be saved.
    compress : bool, optional
        Whether to compress the output NIfTI files (.nii.gz), by default True.
    bids : bool, optional
        Whether to use BIDS naming convention, by default True.
    
    Returns
    -------
    dict
        Dictionary containing output file paths.
    """
    dicom_path = Path(dicom_dir)
    output_path = Path(output_dir)
    
    if not dicom_path.exists():
        raise FileNotFoundError(f"DICOM directory not found: {dicom_dir}")
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    converter = Dcm2niix()
    converter.inputs.source_dir = str(dicom_path)
    converter.inputs.output_dir = str(output_path)
    converter.inputs.compress = 'y' if compress else 'n'
    converter.inputs.bids_format = bids
    converter.inputs.verbose = True
    
    result = converter.run()
    
    return {
        'converted_files': result.outputs.converted_files,
        'bids': result.outputs.bids,
        'bval': getattr(result.outputs, 'bval', None),
        'bvec': getattr(result.outputs, 'bvec', None)
    }
