import React, { useState, useCallback } from 'react';
import VideoUploader from './components/VideoUploader';
import AnalysisPanel from './components/AnalysisPanel';
import TimelineEditor from './components/TimelineEditor';
import HighlightList from './components/HighlightList';
import VideoPreview from './components/VideoPreview';
import ExportPanel from './components/ExportPanel';
import MusicPanel from './components/MusicPanel';
import SubtitlePanel from './components/SubtitlePanel';
import TemplatePanel from './components/TemplatePanel';
import './styles/App.css';

const API_BASE = 'http://localhost:3001/api';

const STEPS = {
  UPLOAD: 0,
  ANALYZE: 1,
  EDIT: 2,
  EXPORT: 3
};

const EDIT_TABS = {
  HIGHLIGHTS: 'highlights',
  MUSIC: 'music',
  SUBTITLES: 'subtitles',
  TEMPLATES: 'templates'
};

function App() {
  const [currentStep, setCurrentStep] = useState(STEPS.UPLOAD);
  const [videoInfo, setVideoInfo] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [selectedHighlights, setSelectedHighlights] = useState([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [editTab, setEditTab] = useState(EDIT_TABS.HIGHLIGHTS);
  const [selectedMusic, setSelectedMusic] = useState(null);
  const [subtitles, setSubtitles] = useState(null);
  const [appliedTemplate, setAppliedTemplate] = useState(null);

  const handleUploadComplete = useCallback((info) => {
    setVideoInfo(info);
    setCurrentStep(STEPS.ANALYZE);
  }, []);

  const handleAnalysisComplete = useCallback((result) => {
    setAnalysisResult(result);
    setSelectedHighlights(result.highlights || []);
    setSelectedMusic(null);
    setSubtitles(null);
    setAppliedTemplate(null);
    setCurrentStep(STEPS.EDIT);
  }, []);

  const handleHighlightToggle = useCallback((highlight) => {
    setSelectedHighlights(prev => {
      const exists = prev.find(h => h.id === highlight.id);
      if (exists) {
        return prev.filter(h => h.id !== highlight.id);
      }
      return [...prev, highlight];
    });
  }, []);

  const handleTimeSeek = useCallback((time) => {
    setCurrentTime(time);
  }, []);

  const handleTemplateApply = useCallback((result) => {
    if (result.selected_highlights && result.selected_highlights.length > 0) {
      setSelectedHighlights(result.selected_highlights);
      setAppliedTemplate(result);
    }
    if (result.export_config?.music_mood) {
      setSelectedMusic({ mood: result.export_config.music_mood });
    }
  }, []);

  const stepItems = [
    { key: STEPS.UPLOAD, label: '上传视频', icon: 'cloud_upload' },
    { key: STEPS.ANALYZE, label: '智能分析', icon: 'auto_awesome' },
    { key: STEPS.EDIT, label: '剪辑编辑', icon: 'content_cut' },
    { key: STEPS.EXPORT, label: '导出合成', icon: 'file_download' }
  ];

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-logo">
          <span className="material-icons-round logo-icon">movie_filter</span>
          <h1>视频智能剪辑工具</h1>
        </div>
        <div className="app-subtitle">AI驱动的视频高光检测与智能剪辑</div>
      </header>

      <nav className="step-nav">
        {stepItems.map((step, idx) => (
          <div
            key={step.key}
            className={`step-item ${currentStep === step.key ? 'active' : ''} ${currentStep > step.key ? 'completed' : ''}`}
            onClick={() => {
              if (step.key <= currentStep) setCurrentStep(step.key);
            }}
          >
            <div className="step-number">
              {currentStep > step.key ? (
                <span className="material-icons-round">check</span>
              ) : (
                idx + 1
              )}
            </div>
            <span className="step-icon material-icons-round">{step.icon}</span>
            <span className="step-label">{step.label}</span>
            {idx < stepItems.length - 1 && <div className="step-connector" />}
          </div>
        ))}
      </nav>

      <main className="app-main">
        {currentStep === STEPS.UPLOAD && (
          <VideoUploader
            apiBase={API_BASE}
            onUploadComplete={handleUploadComplete}
          />
        )}

        {currentStep === STEPS.ANALYZE && (
          <AnalysisPanel
            apiBase={API_BASE}
            videoInfo={videoInfo}
            onAnalysisComplete={handleAnalysisComplete}
            onBack={() => setCurrentStep(STEPS.UPLOAD)}
          />
        )}

        {currentStep === STEPS.EDIT && analysisResult && (
          <div className="editor-layout">
            <div className="editor-main">
              <VideoPreview
                apiBase={API_BASE}
                videoInfo={videoInfo}
                highlights={selectedHighlights}
                currentTime={currentTime}
                onTimeSeek={handleTimeSeek}
              />
              <TimelineEditor
                videoInfo={videoInfo}
                analysisResult={analysisResult}
                selectedHighlights={selectedHighlights}
                onHighlightToggle={handleHighlightToggle}
                onTimeSeek={handleTimeSeek}
                currentTime={currentTime}
              />
            </div>
            <div className="editor-sidebar">
              <div className="edit-tabs">
                {[
                  { key: EDIT_TABS.HIGHLIGHTS, label: '高光', icon: 'highlight' },
                  { key: EDIT_TABS.MUSIC, label: '配乐', icon: 'music_note' },
                  { key: EDIT_TABS.SUBTITLES, label: '字幕', icon: 'subtitles' },
                  { key: EDIT_TABS.TEMPLATES, label: '模板', icon: 'widgets' }
                ].map(tab => (
                  <button
                    key={tab.key}
                    className={`edit-tab ${editTab === tab.key ? 'active' : ''}`}
                    onClick={() => setEditTab(tab.key)}
                  >
                    <span className="material-icons-round">{tab.icon}</span>
                    <span>{tab.label}</span>
                  </button>
                ))}
              </div>

              <div className="tab-content">
                {editTab === EDIT_TABS.HIGHLIGHTS && (
                  <HighlightList
                    highlights={analysisResult.highlights || []}
                    selectedHighlights={selectedHighlights}
                    onToggle={handleHighlightToggle}
                    onTimeSeek={handleTimeSeek}
                    scenes={analysisResult.scenes || []}
                  />
                )}

                {editTab === EDIT_TABS.MUSIC && (
                  <MusicPanel
                    apiBase={API_BASE}
                    videoInfo={videoInfo}
                    analysisResult={analysisResult}
                    selectedMusic={selectedMusic}
                    onSelectMusic={setSelectedMusic}
                  />
                )}

                {editTab === EDIT_TABS.SUBTITLES && (
                  <SubtitlePanel
                    apiBase={API_BASE}
                    videoInfo={videoInfo}
                    subtitles={subtitles}
                    onUpdateSubtitles={setSubtitles}
                  />
                )}

                {editTab === EDIT_TABS.TEMPLATES && (
                  <TemplatePanel
                    apiBase={API_BASE}
                    analysisResult={analysisResult}
                    appliedTemplate={appliedTemplate}
                    onApplyTemplate={handleTemplateApply}
                  />
                )}
              </div>

              <button
                className="btn btn-primary btn-export"
                onClick={() => setCurrentStep(STEPS.EXPORT)}
                disabled={selectedHighlights.length === 0}
              >
                <span className="material-icons-round">file_download</span>
                导出高光合集 ({selectedHighlights.length}段)
              </button>
            </div>
          </div>
        )}

        {currentStep === STEPS.EXPORT && (
          <ExportPanel
            apiBase={API_BASE}
            videoInfo={videoInfo}
            selectedHighlights={selectedHighlights}
            onBack={() => setCurrentStep(STEPS.EDIT)}
          />
        )}
      </main>
    </div>
  );
}

export default App;
