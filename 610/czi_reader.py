import numpy as np
import warnings


class CZIReader:
    @staticmethod
    def available():
        try:
            import czifile
            return True
        except ImportError:
            return False

    @staticmethod
    def read_czi(filepath):
        try:
            import czifile
        except ImportError:
            raise ImportError(
                "czifile library not installed. "
                "Install with: pip install czifile"
            )

        with czifile.CziFile(filepath) as czi:
            image = czi.asarray()
            metadata = CZIReader._parse_metadata(czi)

        image = CZIReader._reorder_dimensions(image)
        return image, metadata

    @staticmethod
    def _parse_metadata(czi):
        metadata = {}
        try:
            from xml.etree import ElementTree as ET
            xml_str = czi.metadata
            if xml_str:
                root = ET.fromstring(xml_str)
                for elem in root.iter():
                    if 'SizeX' in elem.tag:
                        metadata['SizeX'] = int(elem.text) if elem.text else None
                    if 'SizeY' in elem.tag:
                        metadata['SizeY'] = int(elem.text) if elem.text else None
                    if 'SizeZ' in elem.tag:
                        metadata['SizeZ'] = int(elem.text) if elem.text else None
                    if 'SizeC' in elem.tag:
                        metadata['SizeC'] = int(elem.text) if elem.text else None
                    if 'SizeT' in elem.tag:
                        metadata['SizeT'] = int(elem.text) if elem.text else None
        except Exception as e:
            warnings.warn(f"Could not parse CZI metadata: {e}")
        return metadata

    @staticmethod
    def _reorder_dimensions(image):
        ndim = image.ndim
        if ndim == 2:
            return image[np.newaxis, np.newaxis, :, :]
        elif ndim == 3:
            return image[np.newaxis, :, :, :]
        elif ndim == 4:
            return image
        elif ndim >= 5:
            return image[0, :, :, :, :]
        else:
            return image

    @staticmethod
    def get_channels(image, channel_idx=None):
        if image.ndim == 4:
            if channel_idx is None:
                return image
            return image[channel_idx:channel_idx+1]
        return image

    @staticmethod
    def get_zslice(image, z_idx):
        if image.ndim == 4:
            return image[:, z_idx, :, :]
        return image

    @staticmethod
    def normalize_to_float(image):
        if np.issubdtype(image.dtype, np.integer):
            max_val = np.iinfo(image.dtype).max
            return image.astype(np.float64) / max_val
        return image.astype(np.float64)


class SimulatedCZIGenerator:
    @staticmethod
    def generate_test_3d(size_z=16, size_y=256, size_x=256, num_channels=2,
                         num_spots_per_slice=8):
        from image_utils import ImageProcessor
        from scipy.ndimage import gaussian_filter

        image = np.zeros((num_channels, size_z, size_y, size_x), dtype=np.float64)

        for c in range(num_channels):
            for z in range(size_z):
                slice_img = np.zeros((size_y, size_x))
                num_spots = num_spots_per_slice + np.random.randint(-2, 3)
                for _ in range(num_spots):
                    x, y = np.random.randint(20, size_x-20), np.random.randint(20, size_y-20)
                    r = np.random.randint(2, 6)
                    for dy in range(-r, r+1):
                        for dx in range(-r, r+1):
                            if dx*dx + dy*dy <= r*r:
                                ny, nx = y+dy, x+dx
                                if 0 <= ny < size_y and 0 <= nx < size_x:
                                    slice_img[ny, nx] = 1.0
                z_factor = 1.0 - 0.3 * abs(z - size_z/2) / (size_z/2)
                slice_img = gaussian_filter(slice_img, sigma=0.8 + 0.1 * abs(z - size_z/2))
                image[c, z] = slice_img * z_factor

        return image

    @staticmethod
    def generate_blurred_3d(image, psf_xy, psf_z=None):
        from scipy.signal import fftconvolve

        num_channels, size_z, size_y, size_x = image.shape
        result = np.zeros_like(image)

        if psf_z is None:
            psf_z = np.ones(3) / 3

        for c in range(num_channels):
            for z in range(size_z):
                result[c, z] = fftconvolve(image[c, z], psf_xy, mode='same')

            for y in range(size_y):
                for x in range(size_x):
                    line = result[c, :, y, x]
                    result[c, :, y, x] = np.convolve(line, psf_z, mode='same')

        result += np.random.normal(0, 0.01, result.shape)
        return np.clip(result, 0, 1)