import os
import cv2
import numpy as np
import urllib.request


class DeepEdgeDetector:
    def __init__(self, model_dir='models'):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self.hed_net = None
        self.rcf_net = None

    def download_file(self, url, filename):
        filepath = os.path.join(self.model_dir, filename)
        if os.path.exists(filepath):
            return filepath

        print(f"下载模型: {filename}...")
        try:
            def progress_hook(block_num, block_size, total_size):
                downloaded = block_num * block_size
                percent = 100.0 * downloaded / total_size
                print(f"\r  进度: {percent:.1f}%", end='')

            urllib.request.urlretrieve(url, filepath, reporthook=progress_hook)
            print("\n  下载完成!")
            return filepath
        except Exception as e:
            print(f"\n  下载失败: {e}")
            return None

    def load_hed(self):
        if self.hed_net is not None:
            return True

        prototxt_url = "https://raw.githubusercontent.com/s9xie/hed/master/examples/hed/deploy.prototxt"
        caffemodel_url = "http://vcl.ucsd.edu/hed/hed_pretrained_bsds.caffemodel"

        prototxt_path = os.path.join(self.model_dir, 'hed_deploy.prototxt')
        caffemodel_path = os.path.join(self.model_dir, 'hed_pretrained.caffemodel')

        if not os.path.exists(prototxt_path):
            self.download_file(prototxt_url, 'hed_deploy.prototxt')
        if not os.path.exists(caffemodel_path):
            self.download_file(caffemodel_url, 'hed_pretrained.caffemodel')

        try:
            self.hed_net = cv2.dnn.readNetFromCaffe(prototxt_path, caffemodel_path)
            if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                self.hed_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                self.hed_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            return True
        except Exception as e:
            print(f"HED模型加载失败: {e}")
            return False

    def load_rcf(self):
        if self.rcf_net is not None:
            return True

        prototxt_url = "https://raw.githubusercontent.com/yun-liu/rcf/master/examples/rcf/RCF_deploy.prototxt"
        caffemodel_url = "https://github.com/yun-liu/rcf/releases/download/model/bsds500_pascal_model.caffemodel"

        prototxt_path = os.path.join(self.model_dir, 'rcf_deploy.prototxt')
        caffemodel_path = os.path.join(self.model_dir, 'rcf_pretrained.caffemodel')

        if not os.path.exists(prototxt_path):
            self.download_file(prototxt_url, 'rcf_deploy.prototxt')
        if not os.path.exists(caffemodel_path):
            self.download_file(caffemodel_url, 'rcf_pretrained.caffemodel')

        try:
            self.rcf_net = cv2.dnn.readNetFromCaffe(prototxt_path, caffemodel_path)
            if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                self.rcf_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                self.rcf_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            return True
        except Exception as e:
            print(f"RCF模型加载失败: {e}")
            return False

    def detect_hed(self, image, threshold=30):
        if not self.load_hed():
            return None

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        blob = cv2.dnn.blobFromImage(
            gray, scalefactor=1.0, size=(gray.shape[1], gray.shape[0]),
            mean=(104.00698793, 116.66876762, 122.67891434),
            swapRB=False, crop=False
        )

        self.hed_net.setInput(blob)
        output = self.hed_net.forward()
        edges = output[0, 0]
        
        edges = cv2.normalize(edges, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        _, edges = cv2.threshold(edges, threshold, 255, cv2.THRESH_BINARY)
        
        return edges

    def detect_rcf(self, image, threshold=30):
        if not self.load_rcf():
            return None

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        blob = cv2.dnn.blobFromImage(
            gray, scalefactor=1.0, size=(gray.shape[1], gray.shape[0]),
            mean=(104.00698793, 116.66876762, 122.67891434),
            swapRB=False, crop=False
        )

        self.rcf_net.setInput(blob)
        output = self.rcf_net.forward()
        edges = output[0, 0]
        
        edges = cv2.normalize(edges, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        _, edges = cv2.threshold(edges, threshold, 255, cv2.THRESH_BINARY)
        
        return edges

    def detect(self, image, method='hed', threshold=30):
        if method == 'hed':
            return self.detect_hed(image, threshold)
        elif method == 'rcf':
            return self.detect_rcf(image, threshold)
        else:
            raise ValueError(f"Unknown deep method: {method}. Use 'hed' or 'rcf'")


class EdgeGuidedFilter:
    @staticmethod
    def guided_filter(image, guidance, radius=5, eps=0.01):
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if len(guidance.shape) == 3:
            guidance = cv2.cvtColor(guidance, cv2.COLOR_BGR2GRAY)

        image = image.astype(np.float64) / 255.0
        guidance = guidance.astype(np.float64) / 255.0

        mean_I = cv2.boxFilter(guidance, cv2.CV_64F, (radius, radius))
        mean_p = cv2.boxFilter(image, cv2.CV_64F, (radius, radius))
        mean_Ip = cv2.boxFilter(guidance * image, cv2.CV_64F, (radius, radius))
        cov_Ip = mean_Ip - mean_I * mean_p

        mean_II = cv2.boxFilter(guidance * guidance, cv2.CV_64F, (radius, radius))
        var_I = mean_II - mean_I * mean_I

        a = cov_Ip / (var_I + eps)
        b = mean_p - a * mean_I

        mean_a = cv2.boxFilter(a, cv2.CV_64F, (radius, radius))
        mean_b = cv2.boxFilter(b, cv2.CV_64F, (radius, radius))

        q = mean_a * guidance + mean_b
        return (q * 255).astype(np.uint8)

    @staticmethod
    def edge_guided_smoothing(image, edges, smooth_strength=15, edge_weight=0.7):
        if len(image.shape) == 3:
            result = np.zeros_like(image)
            for c in range(3):
                result[:, :, c] = EdgeGuidedFilter.edge_guided_smoothing_single(
                    image[:, :, c], edges, smooth_strength, edge_weight
                )
            return result
        else:
            return EdgeGuidedFilter.edge_guided_smoothing_single(
                image, edges, smooth_strength, edge_weight
            )

    @staticmethod
    def edge_guided_smoothing_single(channel, edges, smooth_strength, edge_weight):
        edges_normalized = edges.astype(np.float64) / 255.0
        edges_blurred = cv2.GaussianBlur(edges_normalized, (5, 5), 2)
        
        weight = 1.0 - edge_weight * edges_blurred
        weight = np.clip(weight, 0.1, 1.0)
        
        smoothed = cv2.bilateralFilter(channel, smooth_strength, smooth_strength * 2, smooth_strength / 2)
        
        result = channel * (1 - weight) + smoothed * weight
        return result.astype(np.uint8)

    @staticmethod
    def edge_enhancement(image, edges, strength=1.5):
        edge_mask = edges.astype(np.float64) / 255.0
        edge_mask = cv2.GaussianBlur(edge_mask, (3, 3), 0.5)
        
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel = lab[:, :, 0].astype(np.float64)
            l_channel += edge_mask * strength * 20
            l_channel = np.clip(l_channel, 0, 255)
            lab[:, :, 0] = l_channel.astype(np.uint8)
            return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            img_float = image.astype(np.float64)
            img_float += edge_mask * strength * 20
            return np.clip(img_float, 0, 255).astype(np.uint8)

    @staticmethod
    def edge_aware_blur(image, edges, blur_kernel=21):
        edge_mask = edges.astype(np.float64) / 255.0
        edge_mask = cv2.dilate(edge_mask, np.ones((5, 5), np.uint8))
        edge_mask = cv2.GaussianBlur(edge_mask, (blur_kernel, blur_kernel), 0)
        
        blurred = cv2.GaussianBlur(image, (blur_kernel, blur_kernel), 0)
        
        weight = edge_mask[..., np.newaxis] if len(image.shape) == 3 else edge_mask
        result = image * weight + blurred * (1 - weight)
        return result.astype(np.uint8)


class RealtimeEdgeDetection:
    def __init__(self, camera_id=0):
        self.camera_id = camera_id
        self.detector = None
        self.deep_detector = None
        self.running = False

    def start(self, method='canny', display_fps=True):
        cap = cv2.VideoCapture(self.camera_id)
        if not cap.isOpened():
            print(f"无法打开摄像头 {self.camera_id}")
            return

        from edge_detection import EdgeDetection
        self.detector = EdgeDetection()
        
        if method in ['hed', 'rcf']:
            self.deep_detector = DeepEdgeDetector()
            self.deep_detector.load_hed() if method == 'hed' else self.deep_detector.load_rcf()

        print(f"实时边缘检测已启动 (方法: {method})")
        print("按 'q' 退出")
        print("按 's' 保存当前帧")
        print("按 '1'-'5' 切换方法 (1:Canny, 2:Sobel, 3:Laplacian, 4:HED, 5:RCF)")

        current_method = method
        frame_count = 0
        fps = 0
        start_time = cv2.getTickCount()

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if current_method in ['hed', 'rcf']:
                if self.deep_detector:
                    edges = self.deep_detector.detect(frame, method=current_method)
                    if edges is None:
                        edges = np.zeros_like(frame[:, :, 0])
            else:
                edges = self.detector.detect_edges(
                    frame, method=current_method, preprocess='gaussian'
                )

            edges_color = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            combined = np.hstack([frame, edges_color])

            if display_fps:
                frame_count += 1
                if frame_count % 10 == 0:
                    elapsed = (cv2.getTickCount() - start_time) / cv2.getTickFrequency()
                    fps = frame_count / elapsed
                    frame_count = 0
                    start_time = cv2.getTickCount()
                
                cv2.putText(combined, f"FPS: {fps:.1f}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(combined, f"Method: {current_method}", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            cv2.imshow('Real-time Edge Detection', combined)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                cv2.imwrite(f'snapshot_{current_method}_{int(time.time())}.png', combined)
                print("截图已保存")
            elif key == ord('1'):
                current_method = 'canny'
            elif key == ord('2'):
                current_method = 'sobel'
            elif key == ord('3'):
                current_method = 'laplacian'
            elif key == ord('4'):
                current_method = 'hed'
                if self.deep_detector is None:
                    self.deep_detector = DeepEdgeDetector()
                self.deep_detector.load_hed()
            elif key == ord('5'):
                current_method = 'rcf'
                if self.deep_detector is None:
                    self.deep_detector = DeepEdgeDetector()
                self.deep_detector.load_rcf()

        cap.release()
        cv2.destroyAllWindows()
        print("实时检测已停止")


import time
