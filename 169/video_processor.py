import cv2
import numpy as np
import uuid
import time
from datetime import datetime
from collections import deque, defaultdict
import threading


class TrackedPlate:
    def __init__(self, plate_text, bbox, frame_id, confidence):
        self.plate_text = plate_text
        self.bbox = bbox
        self.confidence = confidence
        self.first_seen = frame_id
        self.last_seen = frame_id
        self.last_seen_time = time.time()
        self.track_id = str(uuid.uuid4())[:8]
        self.history = [(frame_id, bbox, confidence)]
        self.direction = None
        self.entry_recorded = False
        self.exit_recorded = False

    def update(self, bbox, frame_id, confidence):
        self.bbox = bbox
        self.last_seen = frame_id
        self.last_seen_time = time.time()
        self.confidence = max(self.confidence, confidence)
        self.history.append((frame_id, bbox, confidence))
        if len(self.history) > 10:
            self.history.pop(0)

    def get_history_positions(self):
        return [h[1] for h in self.history]

    def calculate_direction(self):
        if len(self.history) < 2:
            return None
        
        first_bbox = self.history[0][1]
        last_bbox = self.history[-1][1]
        
        first_center = (first_bbox[0] + first_bbox[2] // 2, first_bbox[1] + first_bbox[3] // 2)
        last_center = (last_bbox[0] + last_bbox[2] // 2, last_bbox[1] + last_bbox[3] // 2)
        
        dx = last_center[0] - first_center[0]
        
        if abs(dx) < 20:
            return 'stationary'
        elif dx > 0:
            return 'right'
        else:
            return 'left'


class VideoProcessor:
    def __init__(self, lpr_system, config=None):
        self.lpr = lpr_system
        self.config = config or {}
        
        self.frame_skip = self.config.get('frame_skip', 3)
        self.track_timeout = self.config.get('track_timeout', 5.0)
        self.iou_threshold = self.config.get('iou_threshold', 0.3)
        self.similarity_threshold = self.config.get('similarity_threshold', 0.7)
        
        self.tracked_plates = {}
        self.entry_exit_records = []
        self.frame_count = 0
        
        self.direction_line = self.config.get('direction_line', None)
        self.entry_zone = self.config.get('entry_zone', None)
        self.exit_zone = self.config.get('exit_zone', None)
        
        self.callbacks = {
            'on_plate_detected': None,
            'on_entry': None,
            'on_exit': None,
            'on_alert': None
        }
        
        self.is_running = False
        self._lock = threading.Lock()

    def set_callback(self, event_name, callback):
        if event_name in self.callbacks:
            self.callbacks[event_name] = callback

    def calculate_iou(self, bbox1, bbox2):
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        
        bbox1_area = w1 * h1
        bbox2_area = w2 * h2
        
        iou = intersection_area / float(bbox1_area + bbox2_area - intersection_area)
        return iou

    def plate_similarity(self, plate1, plate2):
        if not plate1 or not plate2:
            return 0.0
        
        if len(plate1) != len(plate2):
            return 0.0
        
        matches = sum(1 for a, b in zip(plate1, plate2) if a == b)
        return matches / len(plate1)

    def find_matching_track(self, plate_text, bbox):
        best_match = None
        best_score = 0
        
        with self._lock:
            for track_id, track in self.tracked_plates.items():
                iou = self.calculate_iou(bbox, track.bbox)
                sim = self.plate_similarity(plate_text, track.plate_text) if plate_text and track.plate_text else 0
                
                score = 0.6 * iou + 0.4 * sim
                
                if score > best_score and score > self.iou_threshold:
                    best_score = score
                    best_match = track_id
        
        return best_match, best_score

    def process_frame(self, frame, frame_id=None):
        if frame_id is None:
            self.frame_count += 1
            frame_id = self.frame_count
        
        if self.frame_count % self.frame_skip != 0:
            return frame, []
        
        try:
            _, img_encoded = cv2.imencode('.jpg', frame)
            results = self.lpr.recognize(image_data=img_encoded.tobytes(), save_images=False)
            detected_plates = results.get('results', []) if results.get('success') else []
        except Exception as e:
            print(f"Frame processing error: {e}")
            return frame, []
        
        updated_tracks = []
        
        for plate_info in detected_plates:
            plate_text = plate_info.get('ocr_text')
            bbox = plate_info.get('bbox')
            confidence = plate_info.get('ocr_confidence', 0) or plate_info.get('detection_confidence', 0)
            
            if not bbox:
                continue
            
            matched_track_id, score = self.find_matching_track(plate_text, bbox)
            
            with self._lock:
                if matched_track_id:
                    track = self.tracked_plates[matched_track_id]
                    track.update(bbox, frame_id, confidence)
                    if plate_text and (track.plate_text is None or 
                                    (confidence > track.confidence and len(plate_text) >= len(track.plate_text))):
                        track.plate_text = plate_text
                else:
                    track = TrackedPlate(plate_text, bbox, frame_id, confidence)
                    self.tracked_plates[track.track_id] = track
                
                updated_tracks.append(track)
                
                if self.callbacks['on_plate_detected']:
                    try:
                        self.callbacks['on_plate_detected'](track)
                    except Exception as e:
                        print(f"Callback error: {e}")
                
                self.check_entry_exit(track)
        
        self.cleanup_old_tracks()
        
        return frame, updated_tracks

    def check_entry_exit(self, track):
        track.direction = track.calculate_direction()
        
        if self.entry_zone and not track.entry_recorded:
            if self.is_in_zone(track.bbox, self.entry_zone):
                track.entry_recorded = True
                record = {
                    'track_id': track.track_id,
                    'plate_text': track.plate_text,
                    'timestamp': datetime.now().isoformat(),
                    'type': 'entry',
                    'direction': track.direction,
                    'confidence': track.confidence
                }
                self.entry_exit_records.append(record)
                if self.callbacks['on_entry']:
                    try:
                        self.callbacks['on_entry'](record)
                    except Exception as e:
                        print(f"Entry callback error: {e}")
        
        if self.exit_zone and track.entry_recorded and not track.exit_recorded:
            if self.is_in_zone(track.bbox, self.exit_zone):
                track.exit_recorded = True
                record = {
                    'track_id': track.track_id,
                    'plate_text': track.plate_text,
                    'timestamp': datetime.now().isoformat(),
                    'type': 'exit',
                    'direction': track.direction,
                    'confidence': track.confidence
                }
                self.entry_exit_records.append(record)
                if self.callbacks['on_exit']:
                    try:
                        self.callbacks['on_exit'](record)
                    except Exception as e:
                        print(f"Exit callback error: {e}")

    def is_in_zone(self, bbox, zone):
        if not zone or len(zone) != 4:
            return False
        
        x, y, w, h = bbox
        zx1, zy1, zw, zh = zone
        
        center_x = x + w // 2
        center_y = y + h // 2
        
        return (zx1 <= center_x <= zx1 + zw and zy1 <= center_y <= zy1 + zh)

    def cleanup_old_tracks(self):
        current_time = time.time()
        with self._lock:
            to_remove = [
                track_id for track_id, track in self.tracked_plates.items()
                if current_time - track.last_seen_time > self.track_timeout
            ]
            for track_id in to_remove:
                del self.tracked_plates[track_id]

    def process_video(self, video_source, output_path=None, max_frames=None):
        cap = cv2.VideoCapture(video_source)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video source: {video_source}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        self.is_running = True
        
        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            if max_frames and frame_count > max_frames:
                break
            
            processed_frame, tracks = self.process_frame(frame, frame_count)
            
            for track in tracks:
                processed_frame = self.draw_track(processed_frame, track)
            
            if writer:
                writer.write(processed_frame)
            
            yield frame_count, processed_frame, tracks
        
        cap.release()
        if writer:
            writer.release()
        
        self.is_running = False

    def draw_track(self, frame, track):
        x, y, w, h = track.bbox
        
        color = (0, 255, 0) if track.entry_recorded else (0, 165, 255)
        
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        
        label = f"{track.plate_text}" if track.plate_text else f"Track: {track.track_id}"
        cv2.putText(frame, label, (x, y - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        info = f"Conf: {track.confidence:.2f}"
        cv2.putText(frame, info, (x, y + h + 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        if track.direction:
            dir_label = f"Dir: {track.direction}"
            cv2.putText(frame, dir_label, (x, y + h + 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return frame

    def stop(self):
        self.is_running = False

    def get_all_tracks(self):
        with self._lock:
            return list(self.tracked_plates.values())

    def get_entry_exit_records(self):
        return self.entry_exit_records.copy()

    def get_statistics(self):
        with self._lock:
            return {
                'total_frames_processed': self.frame_count,
                'active_tracks': len(self.tracked_plates),
                'total_entries': sum(1 for r in self.entry_exit_records if r['type'] == 'entry'),
                'total_exits': sum(1 for r in self.entry_exit_records if r['type'] == 'exit'),
                'unique_plates': len(set(r['plate_text'] for r in self.entry_exit_records if r['plate_text']))
            }

    def reset(self):
        with self._lock:
            self.tracked_plates.clear()
            self.entry_exit_records.clear()
            self.frame_count = 0
