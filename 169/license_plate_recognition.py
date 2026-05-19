import os
import cv2
import numpy as np
import uuid
from datetime import datetime

from image_enhancer import ImageEnhancer
from plate_detector import PlateDetector
from plate_corrector import PlateCorrector
from ocr_recognizer import OCRRecognizer
from plate_classifier import PlateClassifier
from video_processor import VideoProcessor
from plate_blacklist import PlateListManager
from confidence_heatmap import ConfidenceHeatmap
from config import UPLOAD_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER


class LicensePlateRecognition:
    def __init__(self):
        self.enhancer = ImageEnhancer()
        self.detector = PlateDetector()
        self.corrector = PlateCorrector()
        self.ocr = OCRRecognizer()
        self.classifier = PlateClassifier()
        self.heatmap = ConfidenceHeatmap()
        self.plate_list_manager = PlateListManager()
        
        self.video_processor = None
        
        for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER]:
            os.makedirs(folder, exist_ok=True)

    def recognize(self, image_path=None, image_data=None, save_images=True, generate_heatmap=False, check_blacklist=False):
        if image_path:
            image = cv2.imread(image_path)
        elif image_data is not None:
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            return {'error': 'No image provided'}
        
        if image is None:
            return {'error': 'Failed to load image'}
        
        request_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        original_path = None
        if save_images and image_path:
            original_path = os.path.join(UPLOAD_FOLDER, f'{timestamp}_{request_id}_original.jpg')
            cv2.imwrite(original_path, image)
        
        enhanced = self.enhancer.enhance(image)
        
        enhanced_path = None
        if save_images:
            enhanced_path = os.path.join(TEMP_FOLDER, f'{timestamp}_{request_id}_enhanced.jpg')
            cv2.imwrite(enhanced_path, enhanced)
        
        plates = self.detector.detect_with_pyramid(enhanced)
        
        if not plates:
            plates = self.detector.detect_with_pyramid(image)
        
        results = []
        
        for idx, plate_info in enumerate(plates):
            if plate_info['confidence'] < 20:
                continue
            
            corrected = self.corrector.correct(enhanced, plate_info)
            
            if corrected is None:
                corrected = self.corrector.correct(image, plate_info)
            
            corrected_path = None
            if save_images and corrected is not None:
                corrected_path = os.path.join(OUTPUT_FOLDER, f'{timestamp}_{request_id}_plate_{idx}_corrected.jpg')
                cv2.imwrite(corrected_path, corrected)
            
            ocr_result = None
            if corrected is not None:
                ocr_result = self.ocr.recognize(corrected)
                if ocr_result is None:
                    ocr_result = self.ocr.recognize_with_augmentation(corrected)
            
            classification = None
            if corrected is not None:
                plate_text = ocr_result['text'] if ocr_result else None
                classification = self.classifier.classify(corrected, plate_text)
            
            result = {
                'plate_index': idx,
                'bbox': plate_info['bbox'],
                'rotated_box': plate_info['rotated_box'].tolist() if plate_info['rotated_box'] is not None else None,
                'detection_confidence': plate_info['confidence'],
                'plate_type': plate_info.get('type'),
                'plate_type_name': plate_info.get('type_name'),
                'aspect_ratio': plate_info.get('aspect_ratio'),
                'area': plate_info.get('area'),
                'ocr_text': ocr_result['text'] if ocr_result else None,
                'ocr_confidence': ocr_result['confidence'] if ocr_result else 0.0,
                'classification': classification,
                'corrected_image_path': corrected_path,
                'plate_image_path': corrected_path
            }
            
            if check_blacklist and result['ocr_text']:
                blacklist_result = self.plate_list_manager.check_and_alert(
                    result['ocr_text'],
                    extra_info={'request_id': request_id, 'timestamp': timestamp}
                )
                result['blacklist_check'] = blacklist_result
            
            results.append(result)
        
        annotated_image = self._draw_results(image, results)
        annotated_path = None
        if save_images:
            annotated_path = os.path.join(OUTPUT_FOLDER, f'{timestamp}_{request_id}_annotated.jpg')
            cv2.imwrite(annotated_path, annotated_image)
        
        heatmap_image = None
        heatmap_path = None
        heatmap_report = None
        if generate_heatmap and results:
            heatmap_image = self.heatmap.generate_full_image_heatmap(image, results)
            heatmap_report = self.heatmap.generate_quality_report(image, results)
            if save_images:
                heatmap_path = os.path.join(OUTPUT_FOLDER, f'{timestamp}_{request_id}_heatmap.jpg')
                cv2.imwrite(heatmap_path, heatmap_image)
        
        overall_confidence = 0.0
        best_result = None
        if results:
            best_result = max(results, key=lambda x: x['ocr_confidence'] if x['ocr_confidence'] else x['detection_confidence'])
            overall_confidence = best_result['ocr_confidence'] if best_result['ocr_confidence'] else best_result['detection_confidence']
        
        return {
            'request_id': request_id,
            'timestamp': timestamp,
            'success': len(results) > 0,
            'plate_count': len(results),
            'results': results,
            'best_result': best_result,
            'overall_confidence': overall_confidence,
            'original_image_path': original_path,
            'enhanced_image_path': enhanced_path,
            'annotated_image_path': annotated_path,
            'heatmap_image_path': heatmap_path,
            'heatmap_report': heatmap_report,
            'image_size': {
                'width': image.shape[1],
                'height': image.shape[0],
                'channels': image.shape[2] if len(image.shape) > 2 else 1
            }
        }

    def _draw_results(self, image, results):
        annotated = image.copy()
        
        colors = [
            (0, 255, 0),
            (0, 165, 255),
            (0, 255, 255),
            (255, 0, 0),
            (255, 0, 255)
        ]
        
        for idx, result in enumerate(results):
            color = colors[idx % len(colors)]
            
            if result.get('blacklist_check'):
                if result['blacklist_check']['is_blacklist']:
                    color = (0, 0, 255)
                elif result['blacklist_check']['is_whitelist']:
                    color = (0, 255, 0)
            
            x, y, w, h = result['bbox']
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            
            if result['rotated_box'] is not None:
                box = np.array(result['rotated_box'], dtype=np.int32)
                cv2.drawContours(annotated, [box], 0, color, 1)
            
            label_parts = []
            if result['ocr_text']:
                label_parts.append(result['ocr_text'])
            elif result['plate_type_name']:
                label_parts.append(result['plate_type_name'])
            
            if result.get('blacklist_check'):
                if result['blacklist_check']['is_blacklist']:
                    label_parts.append('[黑名单]')
                elif result['blacklist_check']['is_whitelist']:
                    label_parts.append('[白名单]')
            
            label = ' '.join(label_parts)
            
            if label:
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(
                    annotated,
                    (x, y - label_size[1] - 10),
                    (x + label_size[0], y),
                    color,
                    -1
                )
                cv2.putText(
                    annotated,
                    label,
                    (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )
        
        return annotated

    def recognize_batch(self, image_paths, **kwargs):
        results = []
        for path in image_paths:
            result = self.recognize(image_path=path, **kwargs)
            results.append(result)
        return results

    def process_video(self, video_source, output_path=None, max_frames=None, 
                     entry_zone=None, exit_zone=None, check_blacklist=False,
                     on_plate_detected=None, on_entry=None, on_exit=None, on_alert=None):
        if self.video_processor is None:
            config = {
                'frame_skip': 3,
                'track_timeout': 5.0,
                'iou_threshold': 0.3,
                'entry_zone': entry_zone,
                'exit_zone': exit_zone
            }
            self.video_processor = VideoProcessor(self, config)
        
        if on_plate_detected:
            self.video_processor.set_callback('on_plate_detected', on_plate_detected)
        if on_entry:
            self.video_processor.set_callback('on_entry', on_entry)
        if on_exit:
            self.video_processor.set_callback('on_exit', on_exit)
        
        if check_blacklist:
            def alert_callback(track):
                if track.plate_text:
                    self.plate_list_manager.check_and_alert(
                        track.plate_text,
                        extra_info={'track_id': track.track_id, 'video_source': video_source}
                    )
            self.video_processor.set_callback('on_plate_detected', alert_callback)
        
        return self.video_processor.process_video(video_source, output_path, max_frames)

    def stop_video_processing(self):
        if self.video_processor:
            self.video_processor.stop()

    def get_video_statistics(self):
        if self.video_processor:
            return self.video_processor.get_statistics()
        return {}

    def get_entry_exit_records(self):
        if self.video_processor:
            return self.video_processor.get_entry_exit_records()
        return []

    def generate_heatmap(self, image, plate_results):
        return self.heatmap.generate_full_image_heatmap(image, plate_results)

    def generate_quality_report(self, image, plate_results):
        return self.heatmap.generate_quality_report(image, plate_results)

    def add_to_whitelist(self, plate_number, **kwargs):
        return self.plate_list_manager.add_to_whitelist(plate_number, **kwargs)

    def add_to_blacklist(self, plate_number, **kwargs):
        return self.plate_list_manager.add_to_blacklist(plate_number, **kwargs)

    def remove_from_whitelist(self, plate_number):
        return self.plate_list_manager.remove_from_whitelist(plate_number)

    def remove_from_blacklist(self, plate_number):
        return self.plate_list_manager.remove_from_blacklist(plate_number)

    def check_plate(self, plate_number):
        return self.plate_list_manager.check_plate(plate_number)

    def get_whitelist(self, **kwargs):
        return self.plate_list_manager.get_whitelist(**kwargs)

    def get_blacklist(self, **kwargs):
        return self.plate_list_manager.get_blacklist(**kwargs)

    def get_alert_history(self, **kwargs):
        return self.plate_list_manager.get_alert_history(**kwargs)

    def acknowledge_alert(self, alert_id, **kwargs):
        return self.plate_list_manager.acknowledge_alert(alert_id, **kwargs)

    def get_list_statistics(self):
        return self.plate_list_manager.get_statistics()

    def batch_import_plates(self, whitelist_items=None, blacklist_items=None):
        return self.plate_list_manager.batch_import(whitelist_items, blacklist_items)

    def set_blacklist_callback(self, event_name, callback):
        self.plate_list_manager.set_callback(event_name, callback)

    def get_system_info(self):
        return {
            'modules': {
                'image_enhancer': True,
                'plate_detector': True,
                'plate_corrector': True,
                'ocr_recognizer': self.ocr._ocr is not None,
                'plate_classifier': True,
                'video_processor': True,
                'plate_list_manager': True,
                'confidence_heatmap': True
            },
            'supported_plate_types': [
                {'code': 'blue', 'name': '蓝牌', 'chars': 7},
                {'code': 'green', 'name': '绿牌(新能源)', 'chars': 8},
                {'code': 'yellow', 'name': '黄牌', 'chars': 7},
                {'code': 'new_energy_small', 'name': '新能源小车', 'chars': 8},
                {'code': 'new_energy_large', 'name': '新能源大车', 'chars': 8}
            ],
            'features': [
                '低光照图像增强',
                'MSRCR Retinex算法',
                '多角度车牌校正',
                '仿射变换校正',
                '透视变换校正',
                '大角度支持(±70°)',
                'HSV颜色空间检测',
                '多尺度金字塔检测',
                'PaddleOCR字符识别',
                '车牌类型分类',
                '新能源6-8位自适应识别',
                '视频流处理',
                '连续帧去重',
                '车牌轨迹追踪',
                '进出场记录',
                '黑白名单管理',
                '实时告警推送',
                '置信度热力图',
                '识别质量分析'
            ]
        }
