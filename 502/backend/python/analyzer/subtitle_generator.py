import os
import re
import json
import subprocess
import tempfile
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SubtitleCue:
    id: int
    start_time: float
    end_time: float
    text: str
    confidence: float = 1.0


@dataclass
class SubtitleTrack:
    cues: List[SubtitleCue]
    language: str = 'zh'
    format: str = 'srt'


class SubtitleGenerator:
    def __init__(self):
        self.ffmpeg_path = 'ffmpeg'
        self.ffprobe_path = 'ffprobe'

    def extract_audio(self, video_path: str, output_path: Optional[str] = None) -> str:
        if output_path is None:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"subtitle_audio_{os.getpid()}.wav")
        
        cmd = [
            self.ffmpeg_path,
            '-y',
            '-i', video_path,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
        except subprocess.CalledProcessError:
            raise Exception("Failed to extract audio from video")

    def generate_subtitles(
        self,
        video_path: str,
        language: str = 'zh',
        use_whisper: bool = False
    ) -> SubtitleTrack:
        audio_path = self.extract_audio(video_path)
        
        try:
            if use_whisper:
                cues = self._transcribe_with_whisper(audio_path, language)
            else:
                cues = self._generate_demo_subtitles(video_path, language)
            
            return SubtitleTrack(
                cues=cues,
                language=language,
                format='srt'
            )
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

    def _transcribe_with_whisper(self, audio_path: str, language: str) -> List[SubtitleCue]:
        try:
            import whisper
            model = whisper.load_model('base')
            result = model.transcribe(audio_path, language=language)
            
            cues = []
            for i, segment in enumerate(result['segments'], 1):
                cue = SubtitleCue(
                    id=i,
                    start_time=segment['start'],
                    end_time=segment['end'],
                    text=segment['text'].strip(),
                    confidence=segment.get('confidence', 0.8)
                )
                cues.append(cue)
            
            return cues
        except ImportError:
            return self._generate_demo_subtitles(audio_path, language)

    def _generate_demo_subtitles(self, video_path: str, language: str) -> List[SubtitleCue]:
        duration = self._get_video_duration(video_path)
        
        demo_texts = [
            "精彩片段开始",
            "画面切换中",
            "注意关键动作",
            "这是一个高光时刻",
            "场景转换",
            "音乐节奏变化",
            "情绪达到高潮",
            "精彩继续",
            "接近尾声",
            "完美结束"
        ]
        
        if language == 'en':
            demo_texts = [
                "Highlight begins",
                "Scene transition",
                "Key action moment",
                "This is a highlight",
                "Scene change",
                "Music rhythm shift",
                "Emotional climax",
                "Action continues",
                "Coming to an end",
                "Perfect finish"
            ]
        
        cues = []
        segment_duration = max(3.0, duration / len(demo_texts))
        
        for i, text in enumerate(demo_texts):
            start_time = i * segment_duration
            end_time = min((i + 1) * segment_duration, duration)
            
            if start_time >= duration:
                break
            
            cue = SubtitleCue(
                id=i + 1,
                start_time=start_time,
                end_time=end_time,
                text=text,
                confidence=0.9
            )
            cues.append(cue)
        
        return cues

    def _get_video_duration(self, video_path: str) -> float:
        cmd = [
            self.ffprobe_path,
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            return 60.0

    def export_srt(self, track: SubtitleTrack, output_path: str):
        lines = []
        for cue in track.cues:
            lines.append(str(cue.id))
            lines.append(self._format_timestamp_srt(cue.start_time) + ' --> ' + self._format_timestamp_srt(cue.end_time))
            lines.append(cue.text)
            lines.append('')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def export_vtt(self, track: SubtitleTrack, output_path: str):
        lines = ['WEBVTT', '']
        for cue in track.cues:
            lines.append(self._format_timestamp_vtt(cue.start_time) + ' --> ' + self._format_timestamp_vtt(cue.end_time))
            lines.append(cue.text)
            lines.append('')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def export_ass(self, track: SubtitleTrack, output_path: str, style_name: str = 'Default'):
        ass_header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 384
PlayResY: 288
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,16,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
        lines = [ass_header]
        
        for cue in track.cues:
            start = self._format_timestamp_ass(cue.start_time)
            end = self._format_timestamp_ass(cue.end_time)
            text = self._escape_ass_text(cue.text)
            line = f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}"
            lines.append(line)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _format_timestamp_srt(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _format_timestamp_vtt(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
        return f"{minutes:02d}:{secs:02d}.{millis:03d}"

    def _format_timestamp_ass(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

    def _escape_ass_text(self, text: str) -> str:
        return text.replace('\\n', '\\N').replace('\n', '\\N')

    def burn_subtitles_to_video(
        self,
        video_path: str,
        subtitle_track: SubtitleTrack,
        output_path: str,
        style: str = 'default'
    ):
        temp_srt = tempfile.mktemp(suffix='.srt')
        self.export_srt(subtitle_track, temp_srt)
        
        try:
            style_filter = ''
            if style == 'large':
                style_filter = ":force_style='FontSize=24,OutlineColour=&H00000000,Outline=2'"
            elif style == 'colored':
                style_filter = ":force_style='PrimaryColour=&H00FFFF00,OutlineColour=&H00000000,Outline=2'"
            
            cmd = [
                self.ffmpeg_path,
                '-y',
                '-i', video_path,
                '-vf', f"subtitles='{temp_srt}'{style_filter}",
                '-c:a', 'copy',
                output_path
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
        finally:
            if os.path.exists(temp_srt):
                os.remove(temp_srt)

    def merge_subtitle_to_mp4(
        self,
        video_path: str,
        subtitle_track: SubtitleTrack,
        output_path: str,
        language: str = 'chi'
    ):
        temp_srt = tempfile.mktemp(suffix='.srt')
        self.export_srt(subtitle_track, temp_srt)
        
        try:
            cmd = [
                self.ffmpeg_path,
                '-y',
                '-i', video_path,
                '-i', temp_srt,
                '-c:v', 'copy',
                '-c:a', 'copy',
                '-c:s', 'mov_text',
                '-metadata:s:s:0', f'language={language}',
                output_path
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
        finally:
            if os.path.exists(temp_srt):
                os.remove(temp_srt)

    def parse_srt(self, srt_path: str) -> SubtitleTrack:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        cues = []
        blocks = re.split(r'\n\n+', content.strip())
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    cue_id = int(lines[0])
                    time_line = lines[1]
                    text = '\n'.join(lines[2:])
                    
                    start_str, end_str = time_line.split(' --> ')
                    start_time = self._parse_srt_timestamp(start_str)
                    end_time = self._parse_srt_timestamp(end_str)
                    
                    cue = SubtitleCue(
                        id=cue_id,
                        start_time=start_time,
                        end_time=end_time,
                        text=text
                    )
                    cues.append(cue)
                except (ValueError, IndexError):
                    continue
        
        return SubtitleTrack(cues=cues)

    def _parse_srt_timestamp(self, timestamp: str) -> float:
        match = re.match(r'(\d+):(\d+):(\d+)[,.](\d+)', timestamp.strip())
        if match:
            hours, minutes, seconds, millis = map(int, match.groups())
            return hours * 3600 + minutes * 60 + seconds + millis / 1000
        return 0.0
