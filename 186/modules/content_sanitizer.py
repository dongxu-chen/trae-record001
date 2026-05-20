import os
import subprocess
import json
import re
import shutil
from typing import List, Dict, Optional, Tuple
from config.config import FFMPEG_PATH, FFPROBE_PATH, UPLOAD_DIR
from models import ViolationModel


class ContentSanitizer:
    def __init__(self, video_path: str, video_id: int):
        self.video_path = video_path
        self.video_id = video_id
        self.output_dir = os.path.join(UPLOAD_DIR, 'sanitized')
        os.makedirs(self.output_dir, exist_ok=True)
        self.sanitized_path = None

    def _get_video_duration(self) -> float:
        cmd = [
            FFPROBE_PATH,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_entries', 'format=duration',
            self.video_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return float(data.get('format', {}).get('duration', 0))
        except:
            pass
        return 0.0

    def _generate_filter_complex(self, violations: List[Dict], video_duration: float,
                               blur_strength: int = 30) -> str:
        if not violations:
            return ''

        filter_parts = []
        blur_ranges = []

        for v in violations:
            start_time = max(0, v.get('timestamp', 0) - 0.5)
            end_time = min(video_duration, v.get('timestamp', 0) + 1.0)
            
            blur_ranges.append((start_time, end_time))

        if not blur_ranges:
            return ''

        merged_ranges = self._merge_time_ranges(blur_ranges)

        for i, (start, end) in enumerate(merged_ranges):
            filter_parts.append(
                f"[0:v]boxblur=luma_radius={blur_strength}:luma_power=1,"
                f"enable='between(t,{start:.3f},{end:.3f})'[blur{i}];"
            )

        if len(filter_parts) > 1:
            base_expr = f"[0:v]"
            for i in range(len(merged_ranges)):
                base_expr += f"[blur{i}]"
            
            blend_expr = f"{base_expr}blend=all_mode='overlay':all_opacity=1"
            filter_parts.append(blend_expr)
        elif len(filter_parts) == 1:
            filter_parts.append("[blur0]")

        return ';'.join(filter_parts)

    def _merge_time_ranges(self, ranges: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if not ranges:
            return []

        sorted_ranges = sorted(ranges, key=lambda x: x[0])
        merged = [sorted_ranges[0]]

        for current in sorted_ranges[1:]:
            last = merged[-1]
            if current[0] <= last[1] + 0.3:
                merged[-1] = (last[0], max(last[1], current[1]))
            else:
                merged.append(current)

        return merged

    def blur_violation_areas(self, violations: List[Dict], output_filename: str = None,
                           blur_strength: int = 30) -> Optional[str]:
        if not violations:
            return None

        video_duration = self._get_video_duration()
        if video_duration <= 0:
            return None

        if not output_filename:
            base_name = os.path.splitext(os.path.basename(self.video_path))[0]
            output_filename = f"{base_name}_sanitized.mp4"

        self.sanitized_path = os.path.join(self.output_dir, output_filename)

        filter_complex = self._generate_filter_complex(
            violations, video_duration, blur_strength
        )

        if not filter_complex:
            shutil.copy2(self.video_path, self.sanitized_path)
            return self.sanitized_path

        cmd = [
            FFMPEG_PATH,
            '-i', self.video_path,
            '-filter_complex', filter_complex,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'copy',
            self.sanitized_path,
            '-y'
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=600)
            if os.path.exists(self.sanitized_path) and os.path.getsize(self.sanitized_path) > 0:
                return self.sanitized_path
        except Exception as e:
            print(f"Video blurring failed: {e}")

        return None

    def create_video_mask(self, violations: List[Dict], video_duration: float) -> List[Dict]:
        if not violations:
            return []

        masks = []
        for v in violations:
            start_time = max(0, v.get('timestamp', 0) - 0.5)
            end_time = min(video_duration, v.get('timestamp', 0) + 1.0)
            
            masks.append({
                'violation_id': v.get('id'),
                'violation_type': v.get('violation_type'),
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'mask_type': 'boxblur',
                'blur_strength': 30
            })

        return masks

    def replace_sensitive_text(self, text: str, sensitive_words: List[str],
                              replace_char: str = '*') -> Tuple[str, List[Dict]]:
        if not text or not sensitive_words:
            return text, []

        replaced_text = text
        replacements = []

        for word in sensitive_words:
            if word and word in text:
                replacement = replace_char * len(word)
                count = text.lower().count(word.lower())
                
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                replaced_text = pattern.sub(replacement, replaced_text)
                
                replacements.append({
                    'word': word,
                    'replacement': replacement,
                    'count': count
                })

        return replaced_text, replacements

    def generate_srt_with_masked_text(self, subtitle_path: str, sensitive_words: List[str],
                                     output_path: str = None) -> Optional[str]:
        if not os.path.exists(subtitle_path):
            return None

        if not output_path:
            base_name = os.path.splitext(subtitle_path)[0]
            output_path = f"{base_name}_masked.srt"

        try:
            with open(subtitle_path, 'r', encoding='utf-8') as f:
                content = f.read()

            text_pattern = r'(\d+\s+\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}\s+)(.*?)(\n\s*\n)'
            
            def replace_text(match):
                header = match.group(1)
                text = match.group(2)
                footer = match.group(3)
                
                replaced_text, _ = self.replace_sensitive_text(text, sensitive_words)
                return f"{header}{replaced_text}{footer}"

            masked_content = re.sub(text_pattern, replace_text, content, flags=re.DOTALL)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(masked_content)

            return output_path
        except Exception as e:
            print(f"Subtitle masking failed: {e}")
            return None

    def get_sanitization_summary(self) -> Dict:
        if not self.sanitized_path or not os.path.exists(self.sanitized_path):
            return {'success': False}

        original_size = os.path.getsize(self.video_path)
        sanitized_size = os.path.getsize(self.sanitized_path)

        return {
            'success': True,
            'original_path': self.video_path,
            'sanitized_path': self.sanitized_path,
            'original_size': original_size,
            'sanitized_size': sanitized_size,
            'size_diff': sanitized_size - original_size,
            'size_diff_percent': ((sanitized_size - original_size) / original_size * 100) if original_size > 0 else 0
        }


class TextSanitizer:
    @staticmethod
    def mask_text(text: str, sensitive_words: List[str], mask_char: str = '*') -> Tuple[str, List[Dict]]:
        if not text or not sensitive_words:
            return text, []

        result = text
        masked_words = []

        for word in sensitive_words:
            if not word:
                continue
            
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            matches = list(pattern.finditer(text))
            
            if matches:
                replacement = mask_char * len(word)
                result = pattern.sub(replacement, result)
                
                masked_words.append({
                    'word': word,
                    'count': len(matches),
                    'positions': [(m.start(), m.end()) for m in matches]
                })

        return result, masked_words

    @staticmethod
    def partial_mask(text: str, sensitive_words: List[str], 
                     keep_first: int = 1, keep_last: int = 0, mask_char: str = '*') -> Tuple[str, List[Dict]]:
        if not text or not sensitive_words:
            return text, []

        result = text
        masked_words = []

        for word in sensitive_words:
            if not word or len(word) <= keep_first + keep_last:
                continue
            
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            matches = list(pattern.finditer(text))
            
            if matches:
                mask_len = len(word) - keep_first - keep_last
                mask = mask_char * mask_len
                replacement = word[:keep_first] + mask + word[-keep_last:] if keep_last > 0 else word[:keep_first] + mask
                
                result = pattern.sub(replacement, result)
                
                masked_words.append({
                    'word': word,
                    'replacement': replacement,
                    'count': len(matches)
                })

        return result, masked_words
