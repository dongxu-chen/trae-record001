"""
生成多时相测试数据
用于测试时序分析功能
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


def create_multitemporal_data(output_dir='data', width=512, height=512, num_times=5):
    os.makedirs(output_dir, exist_ok=True)

    print(f"生成 {num_times} 个时相的合成测试数据...")

    np.random.seed(42)

    base_image = np.random.rand(4, height, width).astype(np.float32) * 200
    base_image = np.clip(base_image, 0, 255)

    dates = ['2020', '2021', '2022', '2023', '2024']
    if num_times > len(dates):
        dates = [f'2020+{i}' for i in range(num_times)]
    dates = dates[:num_times]

    change_events = [
        {'time': 1, 'type': 'construction', 'cx': 100, 'cy': 100, 'size': 50},
        {'time': 2, 'type': 'construction', 'cx': 300, 'cy': 200, 'size': 70},
        {'time': 2, 'type': 'demolition', 'cx': 400, 'cy': 400, 'size': 40},
        {'time': 3, 'type': 'vegetation', 'cx': 150, 'cy': 350, 'size': 60},
        {'time': 3, 'type': 'renovation', 'cx': 250, 'cy': 150, 'size': 45},
        {'time': 4, 'type': 'water', 'cx': 350, 'cy': 350, 'size': 55},
    ]

    srs = osr.SpatialReference() if GDAL_AVAILABLE else None
    if srs:
        srs.ImportFromEPSG(4326)
    projection = srs.ExportToWkt() if srs else None
    geotransform = (0.0, 0.5, 0.0, 0.0, 0.0, -0.5) if GDAL_AVAILABLE else None

    def write_tiff(path, image):
        if GDAL_AVAILABLE:
            from osgeo import gdal
            driver = gdal.GetDriverByName('GTiff')
            dataset = driver.Create(path, width, height, 4, gdal.GDT_Float32)
            if projection:
                dataset.SetProjection(projection)
            if geotransform:
                dataset.SetGeoTransform(geotransform)
            for i in range(4):
                dataset.GetRasterBand(i + 1).WriteArray(image[i])
            dataset = None
        else:
            import tifffile
            tifffile.imwrite(path, np.transpose(image, (1, 2, 0)))

    file_paths = []
    for t in range(num_times):
        image = base_image.copy()

        for event in change_events:
            if t >= event['time']:
                cx, cy, size = event['cx'], event['cy'], event['size']
                x1, x2 = max(0, cx - size // 2), min(width, cx + size // 2)
                y1, y2 = max(0, cy - size // 2), min(height, cy + size // 2)

                if event['type'] == 'construction':
                    image[0, y1:y2, x1:x2] += 80
                    image[1, y1:y2, x1:x2] += 60
                    image[2, y1:y2, x1:x2] += 20
                    image[3, y1:y2, x1:x2] -= 30
                elif event['type'] == 'demolition':
                    image[0, y1:y2, x1:x2] -= 40
                    image[1, y1:y2, x1:x2] += 30
                    image[2, y1:y2, x1:x2] += 50
                    image[3, y1:y2, x1:x2] += 80
                elif event['type'] == 'renovation':
                    image[0, y1:y2, x1:x2] += 50
                    image[1, y1:y2, x1:x2] += 40
                    image[2, y1:y2, x1:x2] += 30
                elif event['type'] == 'vegetation':
                    image[2, y1:y2, x1:x2] -= 60
                    image[3, y1:y2, x1:x2] += 90
                elif event['type'] == 'water':
                    image[1, y1:y2, x1:x2] += 60
                    image[3, y1:y2, x1:x2] -= 70

        image = np.clip(image, 0, 255).astype(np.float32)

        filename = f'time_{dates[t]}.tif'
        filepath = os.path.join(output_dir, filename)
        write_tiff(filepath, image)
        file_paths.append((filepath, dates[t]))

        print(f"  {dates[t]}: {filepath}")

    label = np.zeros((height, width), dtype=np.uint8)
    for event in change_events:
        cx, cy, size = event['cx'], event['cy'], event['size']
        x1, x2 = max(0, cx - size // 2), min(width, cx + size // 2)
        y1, y2 = max(0, cy - size // 2), min(height, cy + size // 2)

        if event['type'] == 'construction':
            label[y1:y2, x1:x2] = 1
        elif event['type'] == 'demolition':
            label[y1:y2, x1:x2] = 2
        elif event['type'] == 'renovation':
            label[y1:y2, x1:x2] = 3
        elif event['type'] == 'vegetation':
            label[y1:y2, x1:x2] = 4
        elif event['type'] == 'water':
            label[y1:y2, x1:x2] = 5

    label_path = os.path.join(output_dir, 'label_multitemporal.tif')
    if GDAL_AVAILABLE:
        from osgeo import gdal
        driver = gdal.GetDriverByName('GTiff')
        dataset = driver.Create(label_path, width, height, 1, gdal.GDT_Byte)
        if projection:
            dataset.SetProjection(projection)
        if geotransform:
            dataset.SetGeoTransform(geotransform)
        dataset.GetRasterBand(1).WriteArray(label)
        dataset = None
    else:
        import tifffile
        tifffile.imwrite(label_path, label)

    print(f"\n标签文件: {label_path}")
    print(f"\n变化事件:")
    for event in change_events:
        print(f"  {event['time']}期后: {event['type']} @ ({event['cx']}, {event['cy']})")

    return file_paths, label_path


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='生成多时相测试数据')
    parser.add_argument('--output', type=str, default='data', help='输出目录')
    parser.add_argument('--width', type=int, default=512, help='影像宽度')
    parser.add_argument('--height', type=int, default=512, help='影像高度')
    parser.add_argument('--num-times', type=int, default=5, help='时相数量')
    args = parser.parse_args()

    create_multitemporal_data(args.output, args.width, args.height, args.num_times)
