import cv2
import numpy as np
from scipy.signal import find_peaks


class SceneDetector:
    def __init__(self, threshold=30.0, min_scene_length=1.0):
        self.threshold = threshold
        self.min_scene_length = min_scene_length

    def detect_scenes(self, frames_data, fps):
        scenes = []
        if len(frames_data) < 2:
            return [{"start_time": 0, "end_time": len(frames_data) / fps if fps > 0 else 0, "scene_idx": 0}]

        hist_diffs = []
        prev_hsv = None

        for i, frame_info in enumerate(frames_data):
            frame = frame_info["frame"]
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist_h = cv2.calcHist([hsv], [0], None, [50], [0, 180])
            hist_s = cv2.calcHist([hsv], [1], None, [60], [0, 256])
            hist_v = cv2.calcHist([hsv], [2], None, [60], [0, 256])

            cv2.normalize(hist_h, hist_h)
            cv2.normalize(hist_s, hist_s)
            cv2.normalize(hist_v, hist_v)

            if prev_hsv is not None:
                diff_h = cv2.compareHist(prev_hsv[0], hist_h, cv2.HISTCMP_CORREL)
                diff_s = cv2.compareHist(prev_hsv[1], hist_s, cv2.HISTCMP_CORREL)
                diff_v = cv2.compareHist(prev_hsv[2], hist_v, cv2.HISTCMP_CORREL)

                correlation = (diff_h + diff_s + diff_v) / 3.0
                change_score = 1.0 - correlation

                hist_diffs.append({
                    "frame_idx": i,
                    "timestamp": i / fps,
                    "change_score": float(change_score)
                })

            prev_hsv = (hist_h, hist_s, hist_v)

        changes = [d["change_score"] for d in hist_diffs]
        scene_threshold = 1.0 - (self.threshold / 100.0)
        peaks, properties = find_peaks(
            changes,
            height=scene_threshold,
            distance=int(fps * self.min_scene_length)
        )

        boundaries = [0]
        for peak_idx in peaks:
            frame_idx = hist_diffs[peak_idx]["frame_idx"]
            timestamp = hist_diffs[peak_idx]["timestamp"]
            boundaries.append(timestamp)
        boundaries.append(frames_data[-1]["timestamp"] if "timestamp" in frames_data[-1] else len(frames_data) / fps)

        for i in range(len(boundaries) - 1):
            scenes.append({
                "start_time": boundaries[i],
                "end_time": boundaries[i + 1],
                "scene_idx": i
            })

        return scenes

    def get_scene_thumbnail(self, frames_data, scene, fps):
        mid_time = (scene["start_time"] + scene["end_time"]) / 2
        mid_frame_idx = int(mid_time * fps)
        mid_frame_idx = min(mid_frame_idx, len(frames_data) - 1)
        mid_frame_idx = max(0, mid_frame_idx)
        frame = frames_data[mid_frame_idx]["frame"]
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buffer.tobytes()

    def classify_scene(self, frames_data, scene, fps):
        start_idx = max(0, int(scene["start_time"] * fps))
        end_idx = min(len(frames_data) - 1, int(scene["end_time"] * fps))

        if end_idx <= start_idx:
            return "unknown"

        total_motion = 0
        avg_brightness = 0
        avg_saturation = 0

        prev_gray = None
        for i in range(start_idx, end_idx + 1):
            frame = frames_data[i]["frame"]
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            avg_brightness += np.mean(gray)
            avg_saturation += np.mean(hsv[:, :, 1])

            if prev_gray is not None:
                delta = cv2.absdiff(prev_gray, gray)
                total_motion += np.mean(delta)

            prev_gray = gray

        count = end_idx - start_idx + 1
        avg_motion = total_motion / max(count - 1, 1)
        avg_brightness /= count
        avg_saturation /= count

        if avg_motion > 15:
            return "action"
        elif avg_brightness > 180 and avg_saturation > 120:
            return "bright_colorful"
        elif avg_brightness < 80:
            return "dark"
        elif avg_motion < 5:
            return "static"
        else:
            return "normal"
