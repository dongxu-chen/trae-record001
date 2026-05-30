import cv2
import numpy as np
import json
import os
import sys
import time

from .highlight_detector import HighlightDetector
from .scene_detector import SceneDetector
from .audio_analyzer import AudioAnalyzer
from .ffmpeg_processor import FFmpegProcessor
from .music_recommender import MusicRecommender
from .subtitle_generator import SubtitleGenerator
from .template_market import TemplateMarket


class VideoAnalyzer:
    def __init__(self, sensitivity=1.0, sample_fps=2):
        self.sensitivity = sensitivity
        self.sample_fps = sample_fps
        self.highlight_detector = HighlightDetector(sensitivity)
        self.scene_detector = SceneDetector()
        self.audio_analyzer = AudioAnalyzer(sensitivity)
        self.ffmpeg = FFmpegProcessor()
        self.music_recommender = MusicRecommender()
        self.subtitle_generator = SubtitleGenerator()
        self.template_market = TemplateMarket()

    def extract_frames(self, video_path, sample_fps=None):
        if sample_fps is None:
            sample_fps = self.sample_fps

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        original_fps = cap.get(cv2.CAP_PROP_FPS)
        if original_fps <= 0:
            original_fps = 30

        frame_interval = max(1, int(original_fps / sample_fps))
        frames_data = []
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                timestamp = frame_count / original_fps
                max_dim = 320
                h, w = frame.shape[:2]
                if max(h, w) > max_dim:
                    scale = max_dim / max(h, w)
                    frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

                frames_data.append({
                    "frame": frame,
                    "timestamp": timestamp,
                    "frame_idx": frame_count
                })

            frame_count += 1

        cap.release()
        return frames_data, original_fps

    def analyze(self, video_path, options=None):
        if options is None:
            options = {}

        start_time = time.time()

        sensitivity = options.get("sensitivity", self.sensitivity)
        self.highlight_detector.sensitivity = sensitivity
        self.audio_analyzer.sensitivity = sensitivity

        video_info = self.ffmpeg.get_video_info(video_path)
        if video_info is None:
            return {"error": "Cannot read video file info", "success": False}

        print(f"Video info: {json.dumps(video_info, indent=2)}", file=sys.stderr)

        frames_data, original_fps = self.extract_frames(video_path)
        print(f"Extracted {len(frames_data)} sample frames", file=sys.stderr)

        all_highlights = []

        if options.get("detect_motion", True):
            print("Detecting motion highlights...", file=sys.stderr)
            motion_highlights = self.highlight_detector.detect_motion_highlights(
                frames_data, self.sample_fps
            )
            all_highlights.extend(motion_highlights)
            print(f"Found {len(motion_highlights)} motion highlights", file=sys.stderr)

        if options.get("detect_color", True):
            print("Detecting color highlights...", file=sys.stderr)
            color_highlights = self.highlight_detector.detect_color_highlights(
                frames_data, self.sample_fps
            )
            all_highlights.extend(color_highlights)
            print(f"Found {len(color_highlights)} color highlights", file=sys.stderr)

        if options.get("detect_brightness", True):
            print("Detecting brightness changes...", file=sys.stderr)
            brightness_highlights = self.highlight_detector.detect_brightness_changes(
                frames_data, self.sample_fps
            )
            all_highlights.extend(brightness_highlights)
            print(f"Found {len(brightness_highlights)} brightness highlights", file=sys.stderr)

        energy_data = None
        audio_highlights = []
        if options.get("detect_audio", True):
            print("Analyzing audio...", file=sys.stderr)
            audio_path = self.audio_analyzer.extract_audio(video_path)
            if audio_path and os.path.exists(audio_path):
                energy_data = self.audio_analyzer.analyze_audio_energy(audio_path)
                if energy_data:
                    audio_peaks = self.audio_analyzer.detect_audio_highlights(energy_data)
                    audio_highlights.extend(audio_peaks)

                    if options.get("detect_laughter", True):
                        laughter = self.audio_analyzer.detect_laughter(energy_data)
                        audio_highlights.extend(laughter)

                    if os.path.exists(audio_path):
                        try:
                            os.remove(audio_path)
                        except OSError:
                            pass

        if energy_data and all_highlights and options.get("audio_visual_fusion", True):
            print("Fusing audio-visual highlights...", file=sys.stderr)
            all_highlights = self.audio_analyzer.detect_audio_visual_highlights(
                all_highlights, energy_data, self.sample_fps, video_info["duration"]
            )
            print("Audio-visual fusion complete", file=sys.stderr)

        all_highlights.extend(audio_highlights)

        min_duration = options.get("min_duration", 2.0)
        max_duration = options.get("max_duration", 30.0)
        all_highlights = self.highlight_detector.filter_by_duration(
            all_highlights, min_duration, max_duration
        )

        merge_gap = options.get("merge_gap", 2.0)
        merged_highlights = self.highlight_detector.merge_highlights(all_highlights, merge_gap)

        for i, h in enumerate(merged_highlights):
            h["id"] = i + 1
            h["duration"] = round(h["end_time"] - h["start_time"], 2)
            h["start_time"] = round(h["start_time"], 2)
            h["end_time"] = round(h["end_time"], 2)
            h["confidence"] = round(h.get("confidence", 0), 3)

        merged_highlights.sort(key=lambda x: x["confidence"], reverse=True)

        print("Detecting scenes...", file=sys.stderr)
        scenes = self.scene_detector.detect_scenes(frames_data, self.sample_fps)

        for i, scene in enumerate(scenes):
            scene["scene_idx"] = i
            scene["start_time"] = round(scene["start_time"], 2)
            scene["end_time"] = round(scene["end_time"], 2)
            scene["duration"] = round(scene["end_time"] - scene["start_time"], 2)
            scene["type"] = self.scene_detector.classify_scene(frames_data, scene, self.sample_fps)

        elapsed = time.time() - start_time

        result = {
            "success": True,
            "video_info": video_info,
            "highlights": merged_highlights,
            "scenes": scenes,
            "analysis_stats": {
                "total_frames_sampled": len(frames_data),
                "total_highlights": len(merged_highlights),
                "total_scenes": len(scenes),
                "analysis_time": round(elapsed, 2),
                "audio_visual_fusion": energy_data is not None and options.get("audio_visual_fusion", True)
            }
        }

        for frame_info in frames_data:
            del frame_info["frame"]

        return result

    def generate_compilation(self, video_path, highlights, output_path, options=None):
        if options is None:
            options = {}

        clip_duration = options.get("clip_duration", None)
        transition = options.get("transition", "none")
        transition_duration = options.get("transition_duration", 0.5)

        temp_dir = os.path.join(os.path.dirname(output_path), "temp_clips")
        os.makedirs(temp_dir, exist_ok=True)

        clip_paths = []

        try:
            for i, highlight in enumerate(highlights):
                start_time = highlight["start_time"]
                end_time = highlight["end_time"]

                if clip_duration:
                    end_time = min(start_time + clip_duration, highlight["end_time"])

                clip_path = os.path.join(temp_dir, f"clip_{i:04d}.mp4")
                success = self.ffmpeg.extract_clip(video_path, start_time, end_time, clip_path)

                if success and os.path.exists(clip_path):
                    clip_paths.append(clip_path)
                else:
                    print(f"Failed to extract clip {i}", file=sys.stderr)

            if not clip_paths:
                return {"error": "No clips could be extracted", "success": False}

            success = self.ffmpeg.concatenate_clips(
                clip_paths, output_path, transition, transition_duration
            )

            if not success:
                return {"error": "Failed to concatenate clips", "success": False}

            output_info = self.ffmpeg.get_video_info(output_path)

            return {
                "success": True,
                "output_path": output_path,
                "output_info": output_info,
                "clips_count": len(clip_paths)
            }
        finally:
            for clip_path in clip_paths:
                try:
                    if os.path.exists(clip_path):
                        os.remove(clip_path)
                except OSError:
                    pass
            try:
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except OSError:
                pass

    def recommend_music(self, video_path, highlights, scenes, options=None):
        if options is None:
            options = {}

        motion_profile = [h.get('intensity', 0.5) for h in highlights]
        
        rhythm = self.music_recommender.analyze_video_rhythm(
            video_path, highlights, scenes, motion_profile
        )
        
        target_duration = options.get('target_duration')
        genre_filter = options.get('genre_filter')
        mood_filter = options.get('mood_filter')
        top_k = options.get('top_k', 5)
        
        recommendations = self.music_recommender.recommend_music(
            rhythm, target_duration, genre_filter, mood_filter, top_k
        )
        
        result = {
            'video_rhythm': {
                'bpm': rhythm.bpm,
                'avg_motion_intensity': rhythm.avg_motion_intensity,
                'scene_change_rate': rhythm.scene_change_rate,
                'dominant_mood': rhythm.dominant_mood
            },
            'recommendations': []
        }
        
        for track, score in recommendations:
            result['recommendations'].append({
                'id': track.id,
                'name': track.name,
                'artist': track.artist,
                'genre': track.genre,
                'mood': track.mood,
                'bpm': track.bpm,
                'duration': track.duration,
                'energy': track.energy,
                'danceability': track.danceability,
                'match_score': round(score, 3)
            })
        
        return result

    def generate_subtitles(self, video_path, options=None):
        if options is None:
            options = {}

        language = options.get('language', 'zh')
        use_whisper = options.get('use_whisper', False)
        
        subtitle_track = self.subtitle_generator.generate_subtitles(
            video_path, language, use_whisper
        )
        
        result = {
            'language': subtitle_track.language,
            'cue_count': len(subtitle_track.cues),
            'cues': [
                {
                    'id': cue.id,
                    'start_time': round(cue.start_time, 2),
                    'end_time': round(cue.end_time, 2),
                    'text': cue.text,
                    'confidence': round(cue.confidence, 3)
                }
                for cue in subtitle_track.cues
            ]
        }
        
        return result

    def export_subtitles(self, video_path, output_path, options=None):
        if options is None:
            options = {}

        format_type = options.get('format', 'srt')
        language = options.get('language', 'zh')
        
        subtitle_track = self.subtitle_generator.generate_subtitles(
            video_path, language, options.get('use_whisper', False)
        )
        
        if format_type == 'srt':
            self.subtitle_generator.export_srt(subtitle_track, output_path)
        elif format_type == 'vtt':
            self.subtitle_generator.export_vtt(subtitle_track, output_path)
        elif format_type == 'ass':
            self.subtitle_generator.export_ass(subtitle_track, output_path)
        
        return {'success': True, 'format': format_type, 'output_path': output_path}

    def get_templates(self, options=None):
        if options is None:
            options = {}

        category = options.get('category')
        search_term = options.get('search')
        min_rating = options.get('min_rating', 0.0)
        limit = options.get('limit')
        
        templates = self.template_market.get_templates(
            category, search_term, min_rating, limit
        )
        
        return {
            'templates': [
                {
                    'id': tpl.id,
                    'name': tpl.name,
                    'description': tpl.description,
                    'category': tpl.category.value,
                    'author': tpl.author,
                    'rating': tpl.rating,
                    'use_count': tpl.use_count,
                    'target_duration': tpl.target_duration,
                    'transition_type': tpl.transition_type,
                    'quality_preset': tpl.quality_preset,
                    'music_mood': tpl.music_mood,
                    'enable_subtitles': tpl.enable_subtitles
                }
                for tpl in templates
            ],
            'categories': self.template_market.get_categories()
        }

    def apply_template(self, template_id, highlights, scenes, options=None):
        if options is None:
            options = {}

        template = self.template_market.get_template_by_id(template_id)
        if not template:
            return {'success': False, 'error': 'Template not found'}
        
        result = self.template_market.apply_template(template, highlights, scenes)
        self.template_market.increment_template_usage(template_id)
        
        return {'success': True, **result}

    def get_music_library(self):
        tracks = self.music_recommender.get_all_tracks()
        return {
            'tracks': [
                {
                    'id': track.id,
                    'name': track.name,
                    'artist': track.artist,
                    'genre': track.genre,
                    'mood': track.mood,
                    'bpm': track.bpm,
                    'duration': track.duration,
                    'energy': track.energy
                }
                for track in tracks
            ],
            'genres': self.music_recommender.get_genres(),
            'moods': self.music_recommender.get_moods()
        }
