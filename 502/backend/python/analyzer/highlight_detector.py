import cv2
import numpy as np
from scipy.signal import find_peaks
import json
import os


class HighlightDetector:
    def __init__(self, sensitivity=1.0):
        self.sensitivity = sensitivity

    def detect_motion_highlights(self, frames_data, fps):
        highlights = []
        motion_scores = []
        prev_gray = None

        for i, frame_info in enumerate(frames_data):
            frame = frame_info["frame"]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if prev_gray is not None:
                frame_delta = cv2.absdiff(prev_gray, gray)
                thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
                motion_score = np.count_nonzero(thresh) / thresh.size
                motion_scores.append({
                    "frame_idx": i,
                    "timestamp": i / fps,
                    "score": float(motion_score)
                })

            prev_gray = gray

        if not motion_scores:
            return highlights

        scores = [m["score"] for m in motion_scores]
        threshold = np.mean(scores) + self.sensitivity * np.std(scores)
        peaks, properties = find_peaks(
            scores,
            height=threshold,
            distance=int(fps * 2),
            prominence=0.01
        )

        for peak_idx in peaks:
            start_frame = max(0, peak_idx - int(fps * 2))
            end_frame = min(len(frames_data) - 1, peak_idx + int(fps * 2))
            highlights.append({
                "type": "motion",
                "start_time": start_frame / fps,
                "end_time": end_frame / fps,
                "confidence": min(1.0, float(scores[peak_idx]) / (threshold * 2)),
                "peak_score": float(scores[peak_idx])
            })

        return highlights

    def detect_color_highlights(self, frames_data, fps):
        highlights = []
        color_scores = []

        for i, frame_info in enumerate(frames_data):
            frame = frame_info["frame"]
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            saturation = np.mean(hsv[:, :, 1])
            value = np.mean(hsv[:, :, 2])
            color_variance = np.std(hsv[:, :, 0])
            score = (saturation / 255 * 0.4 + value / 255 * 0.3 + color_variance / 180 * 0.3)
            color_scores.append({
                "frame_idx": i,
                "timestamp": i / fps,
                "score": float(score)
            })

        scores = [m["score"] for m in color_scores]
        threshold = np.mean(scores) + self.sensitivity * 1.5 * np.std(scores)
        peaks, _ = find_peaks(
            scores,
            height=threshold,
            distance=int(fps * 3),
            prominence=0.02
        )

        for peak_idx in peaks:
            start_frame = max(0, peak_idx - int(fps * 1.5))
            end_frame = min(len(frames_data) - 1, peak_idx + int(fps * 1.5))
            highlights.append({
                "type": "color",
                "start_time": start_frame / fps,
                "end_time": end_frame / fps,
                "confidence": min(1.0, float(scores[peak_idx]) / (threshold * 1.5)),
                "peak_score": float(scores[peak_idx])
            })

        return highlights

    def detect_brightness_changes(self, frames_data, fps):
        highlights = []
        brightness_scores = []

        for i, frame_info in enumerate(frames_data):
            frame = frame_info["frame"]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            brightness_scores.append({
                "frame_idx": i,
                "timestamp": i / fps,
                "score": float(brightness)
            })

        if len(brightness_scores) < 2:
            return highlights

        diffs = []
        for i in range(1, len(brightness_scores)):
            diff = abs(brightness_scores[i]["score"] - brightness_scores[i - 1]["score"])
            diffs.append({
                "frame_idx": i,
                "timestamp": i / fps,
                "score": diff
            })

        diff_scores = [d["score"] for d in diffs]
        threshold = np.mean(diff_scores) + self.sensitivity * 2 * np.std(diff_scores)
        peaks, _ = find_peaks(
            diff_scores,
            height=threshold,
            distance=int(fps * 2)
        )

        for peak_idx in peaks:
            start_frame = max(0, peak_idx - int(fps))
            end_frame = min(len(frames_data) - 1, peak_idx + int(fps))
            highlights.append({
                "type": "brightness",
                "start_time": start_frame / fps,
                "end_time": end_frame / fps,
                "confidence": min(1.0, float(diff_scores[peak_idx]) / (threshold * 2)),
                "peak_score": float(diff_scores[peak_idx])
            })

        return highlights

    def merge_highlights(self, highlights, merge_gap=2.0):
        if not highlights:
            return []

        sorted_h = sorted(highlights, key=lambda x: x["start_time"])
        merged = [sorted_h[0].copy()]

        for h in sorted_h[1:]:
            last = merged[-1]
            if h["start_time"] - last["end_time"] <= merge_gap:
                last["end_time"] = max(last["end_time"], h["end_time"])
                last["confidence"] = max(last["confidence"], h["confidence"])
                if "types" not in last:
                    last["types"] = [last["type"]]
                last["types"].append(h["type"])
                last["type"] = "multi" if len(last["types"]) > 1 else last["type"]
            else:
                merged.append(h.copy())

        return merged

    def filter_by_duration(self, highlights, min_duration=2.0, max_duration=30.0):
        return [
            h for h in highlights
            if min_duration <= (h["end_time"] - h["start_time"]) <= max_duration
        ]
