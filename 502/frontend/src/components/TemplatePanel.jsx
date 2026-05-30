import React, { useState, useEffect } from 'react';

function TemplatePanel({ apiBase, analysisResult, appliedTemplate, onApplyTemplate }) {
  const [templates, setTemplates] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(null);

  const categoryIcons = {
    vlog: 'videocam',
    short: 'smart_display',
    cinematic: 'movie',
    promo: 'campaign',
    travel: 'flight',
    sports: 'sports_soccer',
    educational: 'school',
    meme: 'emoji_events'
  };

  const categoryColors = {
    vlog: '#f97316',
    short: '#ec4899',
    cinematic: '#8b5cf6',
    promo: '#06b6d4',
    travel: '#14b8a6',
    sports: '#ef4444',
    educational: '#22c55e',
    meme: '#eab308'
  };

  useEffect(() => {
    loadTemplates();
  }, [selectedCategory, searchTerm]);

  const loadTemplates = async () => {
    setLoading(true);

    setTimeout(() => {
      const mockTemplates = [
        {
          id: 'tpl_vlog_daily',
          name: '日常Vlog',
          description: '轻快的日常记录风格，适合生活分享',
          category: 'vlog',
          author: 'System',
          rating: 4.5,
          use_count: 1234,
          target_duration: 60,
          transition_type: 'crossfade',
          quality_preset: 'high',
          music_mood: 'happy',
          enable_subtitles: true
        },
        {
          id: 'tpl_short_impact',
          name: '短视频冲击',
          description: '15秒高光集锦，适合社交媒体分享',
          category: 'short',
          author: 'System',
          rating: 4.8,
          use_count: 3456,
          target_duration: 15,
          transition_type: 'zoom',
          quality_preset: 'high',
          music_mood: 'energetic',
          enable_subtitles: false
        },
        {
          id: 'tpl_cinematic_epic',
          name: '电影史诗',
          description: '大气磅礴的电影风格剪辑',
          category: 'cinematic',
          author: 'System',
          rating: 4.9,
          use_count: 2345,
          target_duration: 120,
          transition_type: 'fade',
          quality_preset: 'ultra',
          music_mood: 'epic',
          enable_subtitles: true
        },
        {
          id: 'tpl_promo_product',
          name: '产品宣传',
          description: '专业产品展示风格',
          category: 'promo',
          author: 'System',
          rating: 4.6,
          use_count: 876,
          target_duration: 30,
          transition_type: 'crossfade',
          quality_preset: 'high',
          music_mood: 'adventurous',
          enable_subtitles: true
        },
        {
          id: 'tpl_travel_adventure',
          name: '旅行探险',
          description: '充满冒险感的旅行记录',
          category: 'travel',
          author: 'System',
          rating: 4.7,
          use_count: 1890,
          target_duration: 90,
          transition_type: 'crossfade',
          quality_preset: 'high',
          music_mood: 'adventurous',
          enable_subtitles: true
        },
        {
          id: 'tpl_sports_highlight',
          name: '运动高光',
          description: '动感十足的运动精彩瞬间',
          category: 'sports',
          author: 'System',
          rating: 4.8,
          use_count: 2100,
          target_duration: 45,
          transition_type: 'zoom',
          quality_preset: 'high',
          music_mood: 'intense',
          enable_subtitles: false
        },
        {
          id: 'tpl_edu_tutorial',
          name: '教程讲解',
          description: '清晰的教学视频风格',
          category: 'educational',
          author: 'System',
          rating: 4.4,
          use_count: 567,
          target_duration: 180,
          transition_type: 'fade',
          quality_preset: 'balanced',
          music_mood: 'calm',
          enable_subtitles: true
        },
        {
          id: 'tpl_meme_funny',
          name: '搞笑魔性',
          description: '快节奏搞笑风格',
          category: 'meme',
          author: 'System',
          rating: 4.5,
          use_count: 4321,
          target_duration: 20,
          transition_type: 'zoom',
          quality_preset: 'compact',
          music_mood: 'happy',
          enable_subtitles: true
        }
      ];

      const mockCategories = [
        { id: 'vlog', name: 'Vlog', icon: 'videocam' },
        { id: 'short', name: '短视频', icon: 'smart_display' },
        { id: 'cinematic', name: '电影感', icon: 'movie' },
        { id: 'promo', name: '宣传片', icon: 'campaign' },
        { id: 'travel', name: '旅行', icon: 'flight' },
        { id: 'sports', name: '运动', icon: 'sports_soccer' },
        { id: 'educational', name: '教育', icon: 'school' },
        { id: 'meme', name: '搞笑', icon: 'emoji_events' }
      ];

      let filtered = mockTemplates;
      if (selectedCategory) {
        filtered = filtered.filter(t => t.category === selectedCategory);
      }
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        filtered = filtered.filter(t => 
          t.name.toLowerCase().includes(term) || 
          t.description.toLowerCase().includes(term)
        );
      }

      setCategories(mockCategories);
      setTemplates(filtered);
      setLoading(false);
    }, 800);
  };

  const handleApplyTemplate = async (template) => {
    setApplying(template.id);

    setTimeout(() => {
      const result = {
        template_name: template.name,
        template_category: template.category,
        selected_highlights: analysisResult?.highlights?.slice(0, Math.min(5, analysisResult.highlights.length)) || [],
        export_config: {
          format: 'mp4',
          quality: template.quality_preset,
          resolution: '1080p',
          transition: template.transition_type,
          transition_duration: 0.5,
          enable_subtitles: template.enable_subtitles,
          music_mood: template.music_mood,
          target_duration: template.target_duration
        }
      };
      onApplyTemplate(result);
      setApplying(null);
    }, 1500);
  };

  const renderStars = (rating) => {
    return (
      <div className="star-rating">
        {[1, 2, 3, 4, 5].map(star => (
          <span 
            key={star} 
            className={`material-icons-round ${star <= Math.round(rating) ? 'star-filled' : 'star-empty'}`}
          >
            {star <= Math.round(rating) ? 'star' : 'star_border'}
          </span>
        ))}
      </div>
    );
  };

  return (
    <div className="template-panel">
      <div className="panel-section">
      <h3 className="panel-title">
        <span className="material-icons-round">widgets</span>
        模板市场
      </h3>

      {appliedTemplate && (
        <div className="applied-template">
          <span className="material-icons-round">check_circle</span>
          <div>
            <div className="applied-name">已应用: {appliedTemplate.template_name}</div>
            <div className="applied-desc">高光片段已根据模板筛选</div>
          </div>
        </div>
      )}

      <div className="template-search">
        <span className="material-icons-round search-icon">search</span>
        <input
          type="text"
          placeholder="搜索模板..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      <div className="category-tabs">
        <button
          className={`category-tab ${!selectedCategory ? 'active' : ''}`}
          onClick={() => setSelectedCategory(null)}
        >
          全部
        </button>
        {categories.map(cat => (
          <button
            key={cat.id}
            className={`category-tab ${selectedCategory === cat.id ? 'active' : ''}`}
            style={{ 
              borderColor: selectedCategory === cat.id ? categoryColors[cat.id] : 'transparent',
              color: selectedCategory === cat.id ? categoryColors[cat.id] : 'inherit'
            }}
            onClick={() => setSelectedCategory(cat.id)}
          >
            <span className="material-icons-round">{categoryIcons[cat.id]}</span>
            {cat.name}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading-state">
          <span className="material-icons-round loading-icon">widgets</span>
          <p>加载模板中...</p>
        </div>
      ) : (
        <div className="template-grid">
          {templates.map((template) => (
            <div 
              key={template.id}
              className={`template-card ${appliedTemplate?.template_name === template.name ? 'applied' : ''}`}
              style={{ borderColor: categoryColors[template.category] }}
            >
              <div 
                className="template-header"
                style={{ backgroundColor: categoryColors[template.category] + '20' }}
              >
                <span 
                  className="material-icons-round template-icon"
                  style={{ color: categoryColors[template.category] }}
                >
                  {categoryIcons[template.category]}
                </span>
                <div className="template-badge">
                  {categories.find(c => c.id === template.category)?.name || template.category}
                </div>
              </div>
              
              <div className="template-body">
                <h4 className="template-name">{template.name}</h4>
                <p className="template-desc">{template.description}</p>
                
                <div className="template-meta">
                  <div className="meta-item">
                    <span className="material-icons-round">timelapse</span>
                    {template.target_duration}秒
                  </div>
                  <div className="meta-item">
                    <span className="material-icons-round">transition_fade</span>
                    {template.transition_type === 'crossfade' ? '交叉溶解' : 
                     template.transition_type === 'zoom' ? '缩放' :
                     template.transition_type === 'fade' ? '淡入淡出' : '无'}
                  </div>
                  <div className="meta-item">
                    <span className="material-icons-round">subtitles</span>
                    {template.enable_subtitles ? '有字幕' : '无字幕'}
                  </div>
                </div>

                <div className="template-footer">
                  <div className="template-rating">
                    {renderStars(template.rating)}
                    <span className="use-count">{template.use_count}次使用</span>
                  </div>
                  
                  <button
                    className={`btn btn-small ${appliedTemplate?.template_name === template.name ? 'btn-primary' : ''}`}
                    onClick={() => handleApplyTemplate(template)}
                    disabled={applying === template.id}
                  >
                    {applying === template.id ? (
                      <>
                        <span className="material-icons-round loading-icon spin">sync</span>
                        应用中...
                      </>
                    ) : appliedTemplate?.template_name === template.name ? (
                      <>
                        <span className="material-icons-round">check</span>
                        已应用
                      </>
                    ) : (
                      <>
                        <span className="material-icons-round">bolt</span>
                        一键应用
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      </div>
    </div>
  );
}

export default TemplatePanel;
