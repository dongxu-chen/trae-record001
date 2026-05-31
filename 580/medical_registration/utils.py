import numpy as np
from scipy.ndimage import rotate, affine_transform


def load_image(filepath):
    import SimpleITK as sitk
    image = sitk.ReadImage(filepath)
    array = sitk.GetArrayFromImage(image)
    spacing = np.array(image.GetSpacing()[::-1])
    origin = np.array(image.GetOrigin()[::-1])
    direction = np.array(image.GetDirection()).reshape((image.GetDimension(),) * 2)
    return {
        "array": array.astype(np.float64),
        "spacing": spacing,
        "origin": origin,
        "direction": direction,
        "sitk_image": image,
    }


def array_to_sitk(array, reference_image=None, spacing=None, origin=None):
    import SimpleITK as sitk
    array = array.astype(np.float64)
    image = sitk.GetImageFromArray(array)
    if reference_image is not None:
        image.CopyInformation(reference_image)
    else:
        if spacing is not None:
            image.SetSpacing(spacing[::-1].tolist())
        if origin is not None:
            image.SetOrigin(origin[::-1].tolist())
    return image


def normalize_image(image):
    arr = image.copy()
    p2, p98 = np.percentile(arr, (2, 98))
    arr = np.clip(arr, p2, p98)
    min_val, max_val = arr.min(), arr.max()
    if max_val - min_val > 1e-10:
        arr = (arr - min_val) / (max_val - min_val)
    else:
        arr = np.zeros_like(arr)
    return arr


def normalize_joint(fixed, moving, target_range=(0.0, 1.0)):
    fixed_arr = fixed.copy().astype(np.float64)
    moving_arr = moving.copy().astype(np.float64)

    fp2, fp98 = np.percentile(fixed_arr, (2, 98))
    mp2, mp98 = np.percentile(moving_arr, (2, 98))

    fixed_arr = np.clip(fixed_arr, fp2, fp98)
    moving_arr = np.clip(moving_arr, mp2, mp98)

    combined_min = min(fixed_arr.min(), moving_arr.min())
    combined_max = max(fixed_arr.max(), moving_arr.max())

    range_size = combined_max - combined_min
    if range_size > 1e-10:
        target_min, target_max = target_range
        target_size = target_max - target_min
        fixed_normalized = (fixed_arr - combined_min) / range_size * target_size + target_min
        moving_normalized = (moving_arr - combined_min) / range_size * target_size + target_min
    else:
        fixed_normalized = np.zeros_like(fixed_arr)
        moving_normalized = np.zeros_like(moving_arr)

    return fixed_normalized, moving_normalized, {
        "combined_min": combined_min,
        "combined_max": combined_max,
        "fixed_original": (fp2, fp98),
        "moving_original": (mp2, mp98),
    }


def denormalize_image(normalized, norm_params):
    combined_min = norm_params["combined_min"]
    combined_max = norm_params["combined_max"]
    range_size = combined_max - combined_min
    if range_size > 1e-10:
        return normalized * range_size + combined_min
    return normalized


def resample_image(image, target_shape, interpolation="linear"):
    import SimpleITK as sitk
    if isinstance(image, dict):
        sitk_image = image["sitk_image"]
    else:
        sitk_image = image

    interpolator = sitk.sitkLinear if interpolation == "linear" else sitk.sitkNearestNeighbor

    original_size = np.array(sitk_image.GetSize(), dtype=np.float64)
    original_spacing = np.array(sitk_image.GetSpacing(), dtype=np.float64)
    new_spacing = original_spacing * (original_size / np.array(target_shape, dtype=np.float64))

    resampled = sitk.Resample(
        sitk_image,
        target_shape.tolist(),
        sitk.Transform(),
        interpolator,
        sitk_image.GetOrigin(),
        new_spacing.tolist(),
        sitk_image.GetDirection(),
        0.0,
        sitk_image.GetPixelIDValue(),
    )
    return resampled


def create_multiresolution_pyramid(image, num_levels=3, shrink_factors=None):
    import SimpleITK as sitk
    if isinstance(image, dict):
        sitk_image = image["sitk_image"]
    else:
        sitk_image = image

    if shrink_factors is None:
        shrink_factors = [2 ** i for i in range(num_levels - 1, 0, -1)] + [1]

    pyramid = []
    for i in range(num_levels):
        if i == num_levels - 1:
            pyramid.append(sitk_image)
        else:
            factor = shrink_factors[i]
            smoothed = sitk.SmoothingRecursiveGaussian(sitk_image, [factor * 0.5] * sitk_image.GetDimension())
            shrinked = sitk.SmoothingRecursiveGaussian(smoothed, [factor] * sitk_image.GetDimension())
            original_spacing = np.array(sitk_image.GetSpacing())
            new_spacing = original_spacing * factor
            original_size = np.array(sitk_image.GetSize(), dtype=np.float64)
            new_size = (original_size / factor).astype(int).tolist()

            shrinked = sitk.Resample(
                smoothed,
                new_size,
                sitk.Transform(),
                sitk.sitkLinear,
                sitk_image.GetOrigin(),
                new_spacing.tolist(),
                sitk_image.GetDirection(),
                0.0,
                sitk_image.GetPixelIDValue(),
            )
            pyramid.append(shrinked)

    pyramid.reverse()
    return pyramid
