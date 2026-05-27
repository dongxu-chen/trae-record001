"""
数据加载模块
支持GDAL和tifffile两种方式读取TIFF遥感影像
"""

import os
import numpy as np

try:
    from osgeo import gdal
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False
    try:
        import tifffile
        TIFFFILE_AVAILABLE = True
    except ImportError:
        TIFFFILE_AVAILABLE = False


def read_geotiff(file_path):
    if GDAL_AVAILABLE:
        return _read_with_gdal(file_path)
    elif TIFFFILE_AVAILABLE:
        return _read_with_tifffile(file_path)
    else:
        raise ImportError("需要安装GDAL或tifffile来读取TIFF文件")


def _read_with_gdal(file_path):
    gdal.UseExceptions()
    dataset = gdal.Open(file_path, gdal.GA_ReadOnly)
    if dataset is None:
        raise FileNotFoundError(f"无法打开文件: {file_path}")

    width = dataset.RasterXSize
    height = dataset.RasterYSize
    bands = dataset.RasterCount
    projection = dataset.GetProjection()
    geotransform = dataset.GetGeoTransform()

    image = np.zeros((bands, height, width), dtype=np.float32)
    for i in range(bands):
        band = dataset.GetRasterBand(i + 1)
        image[i, :, :] = band.ReadAsArray().astype(np.float32)

    dataset = None
    return image, projection, geotransform, width, height, bands


def _read_with_tifffile(file_path):
    image = tifffile.imread(file_path)
    if len(image.shape) == 2:
        image = image[np.newaxis, :, :]
    elif len(image.shape) == 3:
        if image.shape[2] < image.shape[0] and image.shape[2] < image.shape[1]:
            image = np.transpose(image, (2, 0, 1))

    image = image.astype(np.float32)
    bands, height, width = image.shape

    return image, None, None, width, height, bands


def write_geotiff(file_path, image, projection=None, geotransform=None, dtype=None):
    if GDAL_AVAILABLE:
        _write_with_gdal(file_path, image, projection, geotransform, dtype)
    elif TIFFFILE_AVAILABLE:
        _write_with_tifffile(file_path, image)
    else:
        raise ImportError("需要安装GDAL或tifffile来写入TIFF文件")


def _write_with_gdal(file_path, image, projection, geotransform, dtype):
    gdal.UseExceptions()
    if len(image.shape) == 2:
        bands = 1
        height, width = image.shape
        image = image[np.newaxis, :, :]
    elif len(image.shape) == 3:
        bands, height, width = image.shape
    else:
        raise ValueError("图像维度必须为2或3")

    if dtype is None:
        dtype = gdal.GDT_Float32

    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(file_path, width, height, bands, dtype)

    if projection:
        dataset.SetProjection(projection)
    if geotransform:
        dataset.SetGeoTransform(geotransform)

    for i in range(bands):
        band = dataset.GetRasterBand(i + 1)
        band.WriteArray(image[i, :, :])
        band.FlushCache()

    dataset = None


def _write_with_tifffile(file_path, image):
    if len(image.shape) == 3 and image.shape[0] in [1, 3, 4]:
        image_to_write = np.transpose(image, (1, 2, 0))
    else:
        image_to_write = image
    tifffile.imwrite(file_path, image_to_write)


def normalize_image(image):
    min_val = np.min(image)
    max_val = np.max(image)
    if max_val - min_val < 1e-8:
        return np.zeros_like(image, dtype=np.float32)
    normalized = (image - min_val) / (max_val - min_val)
    return normalized.astype(np.float32)


try:
    import torch
    from torch.utils.data import Dataset

    TORCH_AVAILABLE = True

    class ChangeDetectionDataset(Dataset):
        def __init__(self, image1_path, image2_path, label_path=None, patch_size=256, stride=128,
                     transform=None, is_train=True):
            self.patch_size = patch_size
            self.stride = stride
            self.transform = transform
            self.is_train = is_train

            self.image1, self.projection, self.geotransform, self.width, self.height, self.bands = \
                read_geotiff(image1_path)

            self.image2, _, _, _, _, _ = read_geotiff(image2_path)

            self.image1 = normalize_image(self.image1)
            self.image2 = normalize_image(self.image2)

            self.label = None
            if label_path and os.path.exists(label_path):
                self.label, _, _, _, _, _ = read_geotiff(label_path)
                if self.label.shape[0] == 1:
                    self.label = self.label.squeeze(0)

            self.patches = self._extract_patches()

        def _extract_patches(self):
            patches = []
            patch_size = self.patch_size
            stride = self.stride

            h, w = self.height, self.width
            for y in range(0, h - patch_size + 1, stride):
                for x in range(0, w - patch_size + 1, stride):
                    patches.append((y, x))

            last_y = h - patch_size
            last_x = w - patch_size
            if last_y > 0:
                for x in range(0, w - patch_size + 1, stride):
                    if (last_y, x) not in patches:
                        patches.append((last_y, x))
            if last_x > 0:
                for y in range(0, h - patch_size + 1, stride):
                    if (y, last_x) not in patches:
                        patches.append((y, last_x))
            if last_y > 0 and last_x > 0:
                if (last_y, last_x) not in patches:
                    patches.append((last_y, last_x))

            return patches

        def __len__(self):
            return len(self.patches)

        def __getitem__(self, idx):
            y, x = self.patches[idx]
            ps = self.patch_size

            img1_patch = self.image1[:, y:y + ps, x:x + ps].copy()
            img2_patch = self.image2[:, y:y + ps, x:x + ps].copy()

            img1_patch = torch.from_numpy(img1_patch)
            img2_patch = torch.from_numpy(img2_patch)

            if self.transform and self.is_train:
                img1_patch, img2_patch = self.transform(img1_patch, img2_patch)

            if self.label is not None:
                label_patch = self.label[y:y + ps, x:x + ps].copy()
                label_patch = torch.from_numpy(label_patch).long()
                return img1_patch, img2_patch, label_patch
            else:
                return img1_patch, img2_patch, torch.tensor([y, x])

    class FullImageDataset(Dataset):
        def __init__(self, image1_path, image2_path, patch_size=256, stride=128):
            self.patch_size = patch_size
            self.stride = stride

            self.image1, self.projection, self.geotransform, self.width, self.height, self.bands = \
                read_geotiff(image1_path)
            self.image2, _, _, _, _, _ = read_geotiff(image2_path)

            self.image1 = normalize_image(self.image1)
            self.image2 = normalize_image(self.image2)

            self.patches = self._extract_patches()

        def _extract_patches(self):
            patches = []
            ps = self.patch_size
            stride = self.stride

            for y in range(0, self.height - ps + 1, stride):
                for x in range(0, self.width - ps + 1, stride):
                    patches.append((y, x))

            last_y = self.height - ps
            last_x = self.width - ps
            if last_y > 0:
                for x in range(0, self.width - ps + 1, stride):
                    if (last_y, x) not in patches:
                        patches.append((last_y, x))
            if last_x > 0:
                for y in range(0, self.height - ps + 1, stride):
                    if (y, last_x) not in patches:
                        patches.append((y, last_x))
            if last_y > 0 and last_x > 0:
                if (last_y, last_x) not in patches:
                    patches.append((last_y, last_x))

            return patches

        def __len__(self):
            return len(self.patches)

        def __getitem__(self, idx):
            y, x = self.patches[idx]
            ps = self.patch_size

            img1 = self.image1[:, y:y + ps, x:x + ps].copy()
            img2 = self.image2[:, y:y + ps, x:x + ps].copy()

            img1 = torch.from_numpy(img1)
            img2 = torch.from_numpy(img2)

            return img1, img2, torch.tensor([y, x])

except ImportError:
    TORCH_AVAILABLE = False
