import os
import io
import cv2
import numpy as np
from PIL import Image
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import uuid

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.content_detector import detector, RiskLevel, ContentType
from cache.redis_cache import cache
from config import config

@dataclass
class ViolationFrame:
    frame_number: int
    timestamp: float
    time_str: str
    risk_level: str
    main_content: str
    confidence: float
    predictions: Dict

@dataclass
class VideoAuditResult:
    video_id: str
    total_frames: int
    sampled_frames: int
    sample_interval: float
    duration: float
    overall_risk: str
    violation_count: int
    violation_frames: List[ViolationFrame]
    content_distribution: Dict
    process_time: float
    cached: bool

class VideoAuditor:
    def __init__(self):
        self.detector = detector
        self.cache = cache
        self.default_sample_interval = 1.0
        self.min_risk_level = RiskLevel.LOW_RISK
    
    def _format_timestamp(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    
    def _extract_frames(self, video_path: str, sample_interval: float = None) -> Tuple[List[Tuple[int, float, Image.Image]], float, int]:
        if sample_interval is None:
            sample_interval = self.default_sample_interval
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        frame_interval = max(1, int(fps * sample_interval))
        
        frames = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                timestamp = frame_count / fps if fps > 0 else frame_count
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                frames.append((frame_count, timestamp, pil_image))
            
            frame_count += 1
        
        cap.release()
        return frames, duration, total_frames
    
    def _extract_frames_from_bytes(self, video_data: bytes, sample_interval: float = None) -> Tuple[List[Tuple[int, float, Image.Image]], float, int]:
        temp_path = f"/tmp/video_{uuid.uuid4().hex}.mp4"
        try:
            with open(temp_path, 'wb') as f:
                f.write(video_data)
            return self._extract_frames(temp_path, sample_interval)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def _detect_violations(self, frames: List[Tuple[int, float, Image.Image]], 
                           min_risk_level: str = None) -> List[ViolationFrame]:
        if min_risk_level is None:
            min_risk_level = self.min_risk_level
        
        violations = []
        risk_priority = {RiskLevel.NO_RISK: 0, RiskLevel.LOW_RISK: 1, RiskLevel.HIGH_RISK: 2}
        
        for frame_num, timestamp, image in frames:
            result = self.detector.detect(image)
            risk_level = result["risk_level"]
            
            if risk_priority.get(risk_level, 0) >= risk_priority.get(min_risk_level, 0):
                violation = ViolationFrame(
                    frame_number=frame_num,
                    timestamp=round(timestamp, 2),
                    time_str=self._format_timestamp(timestamp),
                    risk_level=risk_level,
                    main_content=result["main_content"],
                    confidence=result["confidence"],
                    predictions=result["predictions"]
                )
                violations.append(violation)
        
        return violations
    
    def _calculate_overall_risk(self, violations: List[ViolationFrame]) -> str:
        if not violations:
            return RiskLevel.NO_RISK
        
        has_high = any(v.risk_level == RiskLevel.HIGH_RISK for v in violations)
        if has_high:
            return RiskLevel.HIGH_RISK
        
        has_low = any(v.risk_level == RiskLevel.LOW_RISK for v in violations)
        if has_low:
            return RiskLevel.LOW_RISK
        
        return RiskLevel.NO_RISK
    
    def _calculate_content_distribution(self, violations: List[ViolationFrame]) -> Dict:
        distribution = {
            ContentType.PORN: 0,
            ContentType.SWIMWEAR: 0,
            ContentType.VIOLENCE: 0,
            ContentType.ADVERTISEMENT: 0,
            ContentType.NORMAL: 0
        }
        
        for v in violations:
            if v.main_content in distribution:
                distribution[v.main_content] += 1
        
        return distribution
    
    def audit_video(
        self,
        video_data: bytes,
        sample_interval: float = None,
        min_risk_level: str = None,
        enable_cache: bool = True,
        video_id: str = None
    ) -> VideoAuditResult:
        start_time = datetime.now()
        
        if video_id is None:
            video_id = str(uuid.uuid4())
        
        if enable_cache:
            cached_result = self._get_cached_result(video_data)
            if cached_result:
                process_time = (datetime.now() - start_time).total_seconds()
                cached_result.process_time = process_time
                cached_result.cached = True
                return cached_result
        
        frames, duration, total_frames = self._extract_frames_from_bytes(video_data, sample_interval)
        
        violations = self._detect_violations(frames, min_risk_level)
        overall_risk = self._calculate_overall_risk(violations)
        content_distribution = self._calculate_content_distribution(violations)
        
        process_time = (datetime.now() - start_time).total_seconds()
        
        result = VideoAuditResult(
            video_id=video_id,
            total_frames=total_frames,
            sampled_frames=len(frames),
            sample_interval=sample_interval or self.default_sample_interval,
            duration=round(duration, 2),
            overall_risk=overall_risk,
            violation_count=len(violations),
            violation_frames=violations,
            content_distribution=content_distribution,
            process_time=round(process_time, 3),
            cached=False
        )
        
        if enable_cache:
            self._cache_result(video_data, result)
        
        return result
    
    def audit_video_file(
        self,
        video_path: str,
        sample_interval: float = None,
        min_risk_level: str = None,
        enable_cache: bool = True,
        video_id: str = None
    ) -> VideoAuditResult:
        with open(video_path, 'rb') as f:
            video_data = f.read()
        return self.audit_video(video_data, sample_interval, min_risk_level, enable_cache, video_id)
    
    def _get_video_cache_key(self, video_data: bytes) -> str:
        import hashlib
        md5_hash = hashlib.md5(video_data).hexdigest()
        return f"audit:video:{md5_hash}"
    
    def _get_cached_result(self, video_data: bytes) -> Optional[VideoAuditResult]:
        cache_key = self._get_video_cache_key(video_data)
        cached = self.cache.client.get(cache_key)
        if not cached:
            return None
        
        try:
            import json
            data = json.loads(cached)
            violations = [
                ViolationFrame(**vf) for vf in data.get("violation_frames", [])
            ]
            return VideoAuditResult(
                video_id=data["video_id"],
                total_frames=data["total_frames"],
                sampled_frames=data["sampled_frames"],
                sample_interval=data["sample_interval"],
                duration=data["duration"],
                overall_risk=data["overall_risk"],
                violation_count=data["violation_count"],
                violation_frames=violations,
                content_distribution=data["content_distribution"],
                process_time=0,
                cached=True
            )
        except Exception:
            return None
    
    def _cache_result(self, video_data: bytes, result: VideoAuditResult) -> None:
        import json
        cache_key = self._get_video_cache_key(video_data)
        
        data = {
            "video_id": result.video_id,
            "total_frames": result.total_frames,
            "sampled_frames": result.sampled_frames,
            "sample_interval": result.sample_interval,
            "duration": result.duration,
            "overall_risk": result.overall_risk,
            "violation_count": result.violation_count,
            "violation_frames": [vars(vf) for vf in result.violation_frames],
            "content_distribution": result.content_distribution
        }
        
        self.cache.client.setex(cache_key, config.CACHE_TTL, json.dumps(data))
    
    def result_to_dict(self, result: VideoAuditResult) -> Dict:
        return {
            "video_id": result.video_id,
            "total_frames": result.total_frames,
            "sampled_frames": result.sampled_frames,
            "sample_interval": result.sample_interval,
            "duration": result.duration,
            "overall_risk": result.overall_risk,
            "violation_count": result.violation_count,
            "violation_frames": [
                {
                    "frame_number": vf.frame_number,
                    "timestamp": vf.timestamp,
                    "time_str": vf.time_str,
                    "risk_level": vf.risk_level,
                    "main_content": vf.main_content,
                    "confidence": vf.confidence
                }
                for vf in result.violation_frames
            ],
            "content_distribution": result.content_distribution,
            "process_time": result.process_time,
            "cached": result.cached
        }

video_auditor = VideoAuditor()
