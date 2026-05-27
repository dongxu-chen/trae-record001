"""
生成测试数据脚本
用于创建模拟的遥感影像和标签数据，便于测试变化检测系统
支持GDAL和tifffile两种方式
"""

import os
import numpy as np

try:
    from osgeo import gdal, osr
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False
    try:
        import tifffile
        TIFFFILE_AVAILABLE = True
    except ImportError:
        TIFFFILE_AVAILABLE = False


def create_synthetic_data(output_dir='data', width=512, height=512):
    os.makedirs(output_dir, exist_ok=True)

    print("生成合成测试数据...")

    np.random.seed(42)

    time1 = np.random.rand(4, height, width).astype(np.float32) * 255
    time1 = np.clip(time1, 0, 255)

    time2 = time1.copy()

    change_map = np.zeros((height, width), dtype=np.uint8)

    num_changes = 5
    for i in range(num_changes):
        cx = np.random.randint(50, width - 50)
        cy = np.random.randint(50, height - 50)
        cw = np.random.randint(30, 100)
        ch = np.random.randint(30, 100)

        x1, x2 = max(0, cx - cw // 2), min(width, cx + cw // 2)
        y1, y2 = max(0, cy - ch // 2), min(height, cy + ch // 2)

        change_type = i % 4 + 1
        change_map[y1:y2, x1:x2] = change_type

        if change_type == 1:
            time2[0, y1:y2, x1:x2] += np.random.uniform(50, 100)
            time2[1, y1:y2, x1:x2] += np.random.uniform(30, 80)
            time2[2, y1:y2, x1:x2] += np.random.uniform(-30, 30)
            time2[3, y1:y2, x1:x2] += np.random.uniform(-50, -10)
        elif change_type == 2:
            time2[2, y1:y2, x1:x2] += np.random.uniform(-80, -50)
            time2[3, y1:y2, x1:x2] += np.random.uniform(50, 100)
        elif change_type == 3:
            time2[1, y1:y2, x1:x2] += np.random.uniform(50, 100)
            time2[3, y1:y2, x1:x2] += np.random.uniform(-100, -50)
        else:
            time2[:, y1:y2, x1:x2] += np.random.uniform(-50, 50, (4, 1, 1))

    time2 = np.clip(time2, 0, 255).astype(np.float32)

    if GDAL_AVAILABLE:
        _write_with_gdal(output_dir, width, height, time1, time2, change_map)
    elif TIFFFILE_AVAILABLE:
        _write_with_tifffile(output_dir, time1, time2, change_map)
    else:
        raise ImportError("需要安装GDAL或tifffile来生成TIFF文件")

    time1_path = os.path.join(output_dir, 'time1.tif')
    time2_path = os.path.join(output_dir, 'time2.tif')
    label_path = os.path.join(output_dir, 'label.tif')

    print(f"测试数据已生成:")
    print(f"  时相1影像: {time1_path}")
    print(f"  时相2影像: {time2_path}")
    print(f"  标签影像: {label_path}")
    print(f"  影像尺寸: {width}x{height}")
    print(f"  变化区域数量: {num_changes}")

    return time1_path, time2_path, label_path


def _write_with_gdal(output_dir, width, height, time1, time2, change_map):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    projection = srs.ExportToWkt()
    geotransform = (0.0, 1.0, 0.0, 0.0, 0.0, 1.0)

    def write_tiff(path, image, is_label=False):
        bands = image.shape[0] if len(image.shape) == 3 else 1
        dtype = gdal.GDT_Byte if is_label else gdal.GDT_Float32

        driver = gdal.GetDriverByName('GTiff')
        dataset = driver.Create(path, width, height, bands, dtype)
        dataset.SetProjection(projection)
        dataset.SetGeoTransform(geotransform)

        if bands == 1:
            dataset.GetRasterBand(1).WriteArray(image)
        else:
            for i in range(bands):
                dataset.GetRasterBand(i + 1).WriteArray(image[i])

        dataset = None

    write_tiff(os.path.join(output_dir, 'time1.tif'), time1)
    write_tiff(os.path.join(output_dir, 'time2.tif'), time2)
    write_tiff(os.path.join(output_dir, 'label.tif'), change_map, is_label=True)


def _write_with_tifffile(output_dir, time1, time2, change_map):
    tifffile.imwrite(os.path.join(output_dir, 'time1.tif'), np.transpose(time1, (1, 2, 0)))
    tifffile.imwrite(os.path.join(output_dir, 'time2.tif'), np.transpose(time2, (1, 2, 0)))
    tifffile.imwrite(os.path.join(output_dir, 'label.tif'), change_map)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='生成测试数据')
    parser.add_argument('--output', type=str, default='data', help='输出目录')
    parser.add_argument('--width', type=int, default=512, help='影像宽度')
    parser.add_argument('--height', type=int, default=512, help='影像高度')
    args = parser.parse_args()

    create_synthetic_data(args.output, args.width, args.height)
