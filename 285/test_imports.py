import cv2
import numpy as np
import matplotlib
import scipy
print('OpenCV:', cv2.__version__)
print('NumPy:', np.__version__)
print('Matplotlib:', matplotlib.__version__)
print('SciPy:', scipy.__version__)

from edge_detection import EdgeDetection
from metrics import Metrics
from bsds_dataset import BSDS500, BSDSMetrics
print('All modules imported successfully!')

print('\n[1] 测试分离卷积高斯模糊...')
detector = EdgeDetection()
test_img = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
blurred = detector.gaussian_blur_separable(test_img, 5, 1.4)
print('  分离卷积高斯模糊 OK, shape:', blurred.shape)

print('\n[2] 测试优化版Canny...')
test_img_color = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
edges_opt = detector.canny_optimized(test_img_color, 50, 150)
print('  优化版Canny OK, shape:', edges_opt.shape)

print('\n[3] 测试并行NMS...')
mag = np.random.rand(100, 100) * 255
dir = np.random.rand(100, 100) * 180
nms = detector.non_maximum_suppression_parallel(mag, dir, num_workers=2)
print('  并行NMS OK, shape:', nms.shape)

print('\n[4] 测试BSDS指标...')
pred = np.random.randint(0, 2, (100, 100), dtype=np.uint8) * 255
gt = np.random.randint(0, 2, (100, 100), dtype=np.uint8) * 255
metrics_calc = Metrics()
bsds_metric = metrics_calc.compute_all_bsds_metrics(pred, gt)
print('  BSDS ODS F1:', bsds_metric['ods_f1'])
print('  BSDS OIS F1:', bsds_metric['ois_f1'])

print('\n[5] 测试合成BSDS数据集...')
bsds = BSDS500('test_bsds')
bsds.create_synthetic_bsds('test_bsds', num_images=5)
image_ids = bsds.get_image_ids('train')
print(f'  合成数据集 OK, train set images: {len(image_ids)}')

import shutil
shutil.rmtree('test_bsds', ignore_errors=True)

print('\n✓ All tests passed!')
