import os
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class TemplateCategory(Enum):
    VLOG = 'vlog'
    SHORT = 'short'
    CINEMATIC = 'cinematic'
    PROMO = 'promo'
    TRAVEL = 'travel'
    SPORTS = 'sports'
    EDUCATIONAL = 'educational'
    MEME = 'meme'


@dataclass
class ClipTemplate:
    id: str
    name: str
    description: str
    category: TemplateCategory
    thumbnail: Optional[str] = None
    author: str = 'System'
    rating: float = 4.5
    use_count: int = 0
    
    target_duration: Optional[float] = None
    min_clips: int = 1
    max_clips: Optional[int] = None
    
    highlight_filters: Optional[Dict[str, Any]] = None
    transition_type: str = 'crossfade'
    transition_duration: float = 0.5
    
    quality_preset: str = 'balanced'
    format: str = 'mp4'
    resolution: str = '1080p'
    
    music_mood: Optional[str] = None
    music_genre: Optional[str] = None
    enable_subtitles: bool = False
    
    text_overlays: Optional[List[Dict[str, Any]]] = None
    color_grading: Optional[str] = None
    effects: Optional[List[str]] = None


class TemplateMarket:
    def __init__(self, templates_dir: Optional[str] = None):
        self.templates: List[ClipTemplate] = []
        self.templates_dir = templates_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'templates'
        )
        self._load_default_templates()
        self._load_custom_templates()

    def _load_default_templates(self):
        default_templates = [
            {
                'id': 'tpl_vlog_daily',
                'name': '日常Vlog',
                'description': '轻快的日常记录风格，适合生活分享',
                'category': TemplateCategory.VLOG,
                'target_duration': 60.0,
                'min_clips': 3,
                'max_clips': 10,
                'transition_type': 'crossfade',
                'transition_duration': 0.4,
                'quality_preset': 'high',
                'music_mood': 'happy',
                'music_genre': 'Pop',
                'enable_subtitles': True,
                'color_grading': 'warm'
            },
            {
                'id': 'tpl_short_impact',
                'name': '短视频冲击',
                'description': '15秒高光集锦，适合社交媒体分享',
                'category': TemplateCategory.SHORT,
                'target_duration': 15.0,
                'min_clips': 5,
                'max_clips': 8,
                'transition_type': 'zoom',
                'transition_duration': 0.2,
                'quality_preset': 'high',
                'music_mood': 'energetic',
                'music_genre': 'Electronic',
                'enable_subtitles': False,
                'effects': ['slowmo', 'zoom']
            },
            {
                'id': 'tpl_cinematic_epic',
                'name': '电影史诗',
                'description': '大气磅礴的电影风格剪辑',
                'category': TemplateCategory.CINEMATIC,
                'target_duration': 120.0,
                'min_clips': 5,
                'max_clips': 15,
                'transition_type': 'fade',
                'transition_duration': 1.0,
                'quality_preset': 'ultra',
                'music_mood': 'epic',
                'music_genre': 'Epic',
                'enable_subtitles': True,
                'color_grading': 'teal_orange'
            },
            {
                'id': 'tpl_promo_product',
                'name': '产品宣传',
                'description': '专业产品展示风格',
                'category': TemplateCategory.PROMO,
                'target_duration': 30.0,
                'min_clips': 4,
                'max_clips': 8,
                'transition_type': 'crossfade',
                'transition_duration': 0.5,
                'quality_preset': 'high',
                'music_mood': 'adventurous',
                'music_genre': 'Pop',
                'enable_subtitles': True,
                'text_overlays': [
                    {'type': 'title', 'position': 'center', 'style': 'bold'},
                    {'type': 'features', 'position': 'bottom'}
                ]
            },
            {
                'id': 'tpl_travel_adventure',
                'name': '旅行探险',
                'description': '充满冒险感的旅行记录',
                'category': TemplateCategory.TRAVEL,
                'target_duration': 90.0,
                'min_clips': 6,
                'max_clips': 20,
                'transition_type': 'crossfade',
                'transition_duration': 0.6,
                'quality_preset': 'high',
                'music_mood': 'adventurous',
                'music_genre': 'World',
                'enable_subtitles': True,
                'color_grading': 'vibrant'
            },
            {
                'id': 'tpl_sports_highlight',
                'name': '运动高光',
                'description': '动感十足的运动精彩瞬间',
                'category': TemplateCategory.SPORTS,
                'target_duration': 45.0,
                'min_clips': 8,
                'max_clips': 15,
                'transition_type': 'zoom',
                'transition_duration': 0.3,
                'quality_preset': 'high',
                'music_mood': 'intense',
                'music_genre': 'Action',
                'enable_subtitles': False,
                'highlight_filters': {'types': ['motion', 'brightness'], 'min_confidence': 0.7},
                'effects': ['freeze_frame', 'zoom']
            },
            {
                'id': 'tpl_edu_tutorial',
                'name': '教程讲解',
                'description': '清晰的教学视频风格',
                'category': TemplateCategory.EDUCATIONAL,
                'target_duration': 180.0,
                'min_clips': 3,
                'transition_type': 'fade',
                'transition_duration': 0.5,
                'quality_preset': 'balanced',
                'music_mood': 'calm',
                'music_genre': 'Ambient',
                'enable_subtitles': True,
                'highlight_filters': {'types': ['color', 'brightness']}
            },
            {
                'id': 'tpl_meme_funny',
                'name': '搞笑魔性',
                'description': '快节奏搞笑风格',
                'category': TemplateCategory.MEME,
                'target_duration': 20.0,
                'min_clips': 6,
                'max_clips': 12,
                'transition_type': 'zoom',
                'transition_duration': 0.15,
                'quality_preset': 'compact',
                'music_mood': 'happy',
                'music_genre': 'Electronic',
                'enable_subtitles': True,
                'effects': ['speed_ramp', 'jump_cut']
            }
        ]
        
        for tpl_data in default_templates:
            self.templates.append(ClipTemplate(**tpl_data))

    def _load_custom_templates(self):
        if not os.path.exists(self.templates_dir):
            return
        
        for filename in os.listdir(self.templates_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(self.templates_dir, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'category' in data:
                            data['category'] = TemplateCategory(data['category'])
                        self.templates.append(ClipTemplate(**data))
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue

    def get_templates(
        self,
        category: Optional[TemplateCategory] = None,
        search_term: Optional[str] = None,
        min_rating: float = 0.0,
        limit: Optional[int] = None
    ) -> List[ClipTemplate]:
        result = self.templates.copy()
        
        if category:
            result = [t for t in result if t.category == category]
        
        if search_term:
            search_lower = search_term.lower()
            result = [
                t for t in result
                if search_lower in t.name.lower() or search_lower in t.description.lower()
            ]
        
        result = [t for t in result if t.rating >= min_rating]
        result.sort(key=lambda t: (t.rating, t.use_count), reverse=True)
        
        if limit:
            result = result[:limit]
        
        return result

    def get_template_by_id(self, template_id: str) -> Optional[ClipTemplate]:
        for tpl in self.templates:
            if tpl.id == template_id:
                return tpl
        return None

    def get_categories(self) -> List[Dict[str, str]]:
        return [
            {'id': 'vlog', 'name': 'Vlog', 'icon': 'videocam'},
            {'id': 'short', 'name': '短视频', 'icon': 'smart_display'},
            {'id': 'cinematic', 'name': '电影感', 'icon': 'movie'},
            {'id': 'promo', 'name': '宣传片', 'icon': 'campaign'},
            {'id': 'travel', 'name': '旅行', 'icon': 'flight'},
            {'id': 'sports', 'name': '运动', 'icon': 'sports_soccer'},
            {'id': 'educational', 'name': '教育', 'icon': 'school'},
            {'id': 'meme', 'name': '搞笑', 'icon': 'emoji_events'}
        ]

    def apply_template(
        self,
        template: ClipTemplate,
        highlights: List[Dict],
        scenes: List[Dict]
    ) -> Dict[str, Any]:
        selected_highlights = highlights.copy()
        
        if template.highlight_filters:
            if 'types' in template.highlight_filters:
                allowed_types = template.highlight_filters['types']
                selected_highlights = [
                    h for h in selected_highlights
                    if h.get('type') in allowed_types
                ]
            
            if 'min_confidence' in template.highlight_filters:
                min_conf = template.highlight_filters['min_confidence']
                selected_highlights = [
                    h for h in selected_highlights
                    if h.get('confidence', 0) >= min_conf
                ]
        
        selected_highlights.sort(key=lambda h: h.get('confidence', 0), reverse=True)
        
        if template.max_clips:
            selected_highlights = selected_highlights[:template.max_clips]
        
        if template.min_clips and len(selected_highlights) < template.min_clips:
            selected_highlights = highlights[:max(template.min_clips, len(highlights))]
        
        selected_highlights.sort(key=lambda h: h.get('start_time', 0))
        
        export_config = {
            'format': template.format,
            'quality': template.quality_preset,
            'resolution': template.resolution,
            'transition': template.transition_type,
            'transition_duration': template.transition_duration,
            'enable_subtitles': template.enable_subtitles,
            'music_mood': template.music_mood,
            'music_genre': template.music_genre,
            'target_duration': template.target_duration
        }
        
        return {
            'selected_highlights': selected_highlights,
            'export_config': export_config,
            'template_name': template.name,
            'template_category': template.category.value
        }

    def save_custom_template(self, template: ClipTemplate) -> bool:
        os.makedirs(self.templates_dir, exist_ok=True)
        
        template_path = os.path.join(self.templates_dir, f"{template.id}.json")
        try:
            data = asdict(template)
            data['category'] = template.category.value
            
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.templates.append(template)
            return True
        except (IOError, TypeError):
            return False

    def increment_template_usage(self, template_id: str):
        for tpl in self.templates:
            if tpl.id == template_id:
                tpl.use_count += 1
                break
