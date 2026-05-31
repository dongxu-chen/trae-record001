import React, { useState } from 'react';
import { File, Download, Upload, Grid, Magnet, ZoomIn, ZoomOut, Maximize2, Settings, Save, Code, Film, Sparkles } from 'lucide-react';
import { useProjectStore } from '@/store/useProjectStore';
import { useEditorStore } from '@/store/useEditorStore';
import { exportSVG, exportJS, exportProjectJSON, downloadFile } from '@/utils/exporters';

export const Toolbar: React.FC = () => {
  const { project, resetProject, loadProject } = useProjectStore();
  const { showGrid, setShowGrid, snapToGrid, setSnapToGrid, zoom, setZoom, setActiveModal } = useEditorStore();
  const [showExportMenu, setShowExportMenu] = useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleExportSVG = (compressed: boolean = false) => {
    const content = exportSVG(project, { compressed, minify: compressed });
    const suffix = compressed ? '.min' : '';
    downloadFile(content, `${project.name.replace(/\s+/g, '-').toLowerCase()}${suffix}.svg`, 'image/svg+xml');
    setShowExportMenu(false);
  };

  const handleExportJS = (compressed: boolean = false) => {
    const content = exportJS(project, { compressed, minify: compressed });
    const suffix = compressed ? '.min' : '';
    downloadFile(content, `${project.name.replace(/\s+/g, '-').toLowerCase()}${suffix}.html`, 'text/html');
    setShowExportMenu(false);
  };

  const handleExportJSON = (minify: boolean = false) => {
    const content = exportProjectJSON(project, minify);
    const suffix = minify ? '.min' : '';
    downloadFile(content, `${project.name.replace(/\s+/g, '-').toLowerCase()}${suffix}.json`, 'application/json');
    setShowExportMenu(false);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const projectData = JSON.parse(event.target?.result as string);
        loadProject(projectData);
      } catch (error) {
        console.error('Failed to load project:', error);
        alert('Failed to load project file. Please check the file format.');
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  return (
    <div className="h-12 bg-bg-secondary border-b border-border-primary flex items-center justify-between px-4">
      <div className="flex items-center gap-1">
        <div className="flex items-center gap-2 pr-4 border-r border-border-primary">
          <File size={18} className="text-accent-primary" />
          <span className="font-semibold text-sm text-text-primary">SVG Animator</span>
        </div>

        <button
          onClick={resetProject}
          className="btn-icon text-text-secondary hover:text-text-primary"
          title="New Project"
        >
          <File size={16} />
        </button>

        <button
          onClick={() => fileInputRef.current?.click()}
          className="btn-icon text-text-secondary hover:text-text-primary"
          title="Open Project"
        >
          <Upload size={16} />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          onChange={handleFileUpload}
          className="hidden"
        />

        <button
          onClick={handleExportJSON}
          className="btn-icon text-text-secondary hover:text-text-primary"
          title="Save Project"
        >
          <Save size={16} />
        </button>

        <div className="relative">
          <button
            onClick={() => setShowExportMenu(!showExportMenu)}
            className="btn-icon text-text-secondary hover:text-text-primary"
            title="Export"
          >
            <Download size={16} />
          </button>

          {showExportMenu && (
            <div className="absolute top-full left-0 mt-1 bg-bg-tertiary border border-border-primary rounded shadow-lg z-50 min-w-[200px]">
              <div className="px-3 py-2 text-xs text-text-muted border-b border-border-primary">Export as SVG</div>
              <button
                onClick={() => handleExportSVG(false)}
                className="w-full px-4 py-1.5 text-left text-sm text-text-secondary hover:bg-bg-primary hover:text-text-primary transition-colors"
              >
                Standard
              </button>
              <button
                onClick={() => handleExportSVG(true)}
                className="w-full px-4 py-1.5 text-left text-sm text-text-secondary hover:bg-bg-primary hover:text-text-primary transition-colors"
              >
                <span className="text-accent-secondary">Compressed</span> (minified)
              </button>
              
              <div className="px-3 py-2 text-xs text-text-muted border-t border-border-primary">Export as HTML/JS</div>
              <button
                onClick={() => handleExportJS(false)}
                className="w-full px-4 py-1.5 text-left text-sm text-text-secondary hover:bg-bg-primary hover:text-text-primary transition-colors"
              >
                Standard (readable)
              </button>
              <button
                onClick={() => handleExportJS(true)}
                className="w-full px-4 py-1.5 text-left text-sm text-text-secondary hover:bg-bg-primary hover:text-text-primary transition-colors"
              >
                <span className="text-accent-secondary">Compressed</span> (minified)
              </button>
              
              <div className="px-3 py-2 text-xs text-text-muted border-t border-border-primary">Export Project</div>
              <button
                onClick={() => handleExportJSON(false)}
                className="w-full px-4 py-1.5 text-left text-sm text-text-secondary hover:bg-bg-primary hover:text-text-primary transition-colors"
              >
                Standard (pretty)
              </button>
              <button
                onClick={() => handleExportJSON(true)}
                className="w-full px-4 py-1.5 text-left text-sm text-text-secondary hover:bg-bg-primary hover:text-text-primary transition-colors"
              >
                <span className="text-accent-secondary">Compressed</span> (minified)
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1">
        <div className="flex items-center gap-1 px-3 border-r border-border-primary">
          <button
            onClick={() => setActiveModal('frameImport')}
            className="btn-icon text-text-secondary hover:text-accent-primary"
            title="Frame Animation Editor"
          >
            <Film size={16} />
          </button>
          <button
            onClick={() => setActiveModal('codePreview')}
            className="btn-icon text-text-secondary hover:text-accent-secondary"
            title="Code Preview"
          >
            <Code size={16} />
          </button>
          <button
            onClick={() => setActiveModal('marketplace')}
            className="btn-icon text-text-secondary hover:text-accent-success"
            title="Animation Marketplace"
          >
            <Sparkles size={16} />
          </button>
        </div>

        <div className="flex items-center gap-1 px-3 border-r border-border-primary">
          <button
            onClick={() => setShowGrid(!showGrid)}
            className={`btn-icon ${showGrid ? 'text-accent-secondary' : 'text-text-secondary hover:text-text-primary'}`}
            title="Toggle Grid"
          >
            <Grid size={16} />
          </button>

          <button
            onClick={() => setSnapToGrid(!snapToGrid)}
            className={`btn-icon ${snapToGrid ? 'text-accent-secondary' : 'text-text-secondary hover:text-text-primary'}`}
            title="Snap to Grid"
          >
            <Magnet size={16} />
          </button>
        </div>

        <div className="flex items-center gap-1 px-3 border-r border-border-primary">
          <button
            onClick={() => setZoom(Math.max(0.25, zoom * 0.8))}
            className="btn-icon text-text-secondary hover:text-text-primary"
            title="Zoom Out"
          >
            <ZoomOut size={16} />
          </button>
          <span className="text-xs text-text-muted w-14 text-center font-mono">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={() => setZoom(Math.min(3, zoom * 1.25))}
            className="btn-icon text-text-secondary hover:text-text-primary"
            title="Zoom In"
          >
            <ZoomIn size={16} />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="btn-icon text-text-secondary hover:text-text-primary"
            title="Reset Zoom"
          >
            <Maximize2 size={16} />
          </button>
        </div>

        <button
          className="btn-icon text-text-secondary hover:text-text-primary"
          title="Settings"
        >
          <Settings size={16} />
        </button>
      </div>
    </div>
  );
};
