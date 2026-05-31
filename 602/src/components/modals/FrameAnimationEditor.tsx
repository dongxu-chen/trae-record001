import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Plus, Trash2, Upload, Play, Pause, SkipBack, Copy, Film, Settings } from 'lucide-react';
import { useProjectStore } from '@/store/useProjectStore';
import { useEditorStore } from '@/store/useEditorStore';

export const FrameAnimationEditor: React.FC = () => {
  const { project, addFrameAnimation, deleteFrameAnimation, addFrame, deleteFrame, updateFrame, updateFrameAnimation, importFrameSequence } = useProjectStore();
  const { setActiveModal } = useEditorStore();
  const [selectedAnimId, setSelectedAnimId] = useState<string | null>(null);
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [newAnimName, setNewAnimName] = useState('Frame Animation');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const playIntervalRef = useRef<number | null>(null);

  const selectedAnim = project.frameAnimations.find(fa => fa.id === selectedAnimId);

  useEffect(() => {
    if (isPlaying && selectedAnim) {
      playIntervalRef.current = window.setInterval(() => {
        setCurrentFrameIndex(prev => {
          if (prev >= selectedAnim.frames.length - 1) {
            if (selectedAnim.loop) return 0;
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1000 / selectedAnim.fps);
    }
    return () => {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    };
  }, [isPlaying, selectedAnim]);

  const handleCreateAnimation = () => {
    const anim = addFrameAnimation(newAnimName, project.width, project.height);
    setSelectedAnimId(anim.id);
  };

  const handleImportFiles = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    if (!selectedAnimId) {
      const anim = addFrameAnimation(newAnimName, project.width, project.height);
      setSelectedAnimId(anim.id);
      await importFrameSequence(anim.id, files);
    } else {
      await importFrameSequence(selectedAnimId, files);
    }
    e.target.value = '';
  };

  const handleAddEmptyFrame = () => {
    if (!selectedAnimId) return;
    const emptySvg = `<svg xmlns="http://www.w3.org/2000/svg" width="${project.width}" height="${project.height}" viewBox="0 0 ${project.width} ${project.height}"><rect width="100%" height="100%" fill="#1a1a2e"/></svg>`;
    addFrame(selectedAnimId, emptySvg);
  };

  const currentFrame = selectedAnim?.frames[currentFrameIndex];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setActiveModal('none')}>
      <div className="bg-bg-secondary border border-border-primary rounded-xl w-[90vw] max-w-[1200px] h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-primary">
          <div className="flex items-center gap-3">
            <Film size={20} className="text-accent-primary" />
            <h2 className="text-lg font-semibold text-text-primary">Frame Animation Editor</h2>
          </div>
          <button onClick={() => setActiveModal('none')} className="btn-icon text-text-secondary hover:text-text-primary text-xl">×</button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          <div className="w-64 border-r border-border-primary flex flex-col">
            <div className="panel-header">Animations</div>
            <div className="p-3 border-b border-border-primary">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newAnimName}
                  onChange={(e) => setNewAnimName(e.target.value)}
                  className="flex-1 text-xs"
                  placeholder="Animation name"
                />
                <button onClick={handleCreateAnimation} className="btn-icon bg-accent-primary text-white">
                  <Plus size={14} />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto">
              {project.frameAnimations.map(fa => (
                <div
                  key={fa.id}
                  className={`flex items-center justify-between px-3 py-2 cursor-pointer transition-colors ${
                    selectedAnimId === fa.id ? 'bg-bg-tertiary' : 'hover:bg-bg-tertiary/50'
                  }`}
                  onClick={() => { setSelectedAnimId(fa.id); setCurrentFrameIndex(0); }}
                >
                  <div>
                    <div className="text-sm text-text-primary">{fa.name}</div>
                    <div className="text-xs text-text-muted">{fa.frames.length} frames · {fa.fps}fps</div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteFrameAnimation(fa.id); if (selectedAnimId === fa.id) setSelectedAnimId(null); }}
                    className="p-1 hover:bg-accent-primary/20 rounded"
                  >
                    <Trash2 size={12} className="text-accent-primary" />
                  </button>
                </div>
              ))}
              {project.frameAnimations.length === 0 && (
                <div className="p-4 text-center text-text-muted text-sm">No frame animations</div>
              )}
            </div>
          </div>

          <div className="flex-1 flex flex-col">
            {selectedAnim ? (
              <>
                <div className="flex-1 flex items-center justify-center p-4 bg-bg-primary">
                  <div className="border border-border-primary rounded overflow-hidden" style={{ width: 400, height: 300 }}>
                    {currentFrame ? (
                      <div dangerouslySetInnerHTML={{ __html: currentFrame.svgContent }} style={{ width: '100%', height: '100%' }} />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-text-muted text-sm">
                        No frames yet
                      </div>
                    )}
                  </div>
                </div>

                <div className="border-t border-border-primary p-3">
                  <div className="flex items-center gap-3 mb-3">
                    <button onClick={() => setCurrentFrameIndex(0)} className="btn-icon text-text-secondary hover:text-text-primary">
                      <SkipBack size={16} />
                    </button>
                    <button
                      onClick={() => setIsPlaying(!isPlaying)}
                      className="btn-icon bg-bg-tertiary text-accent-success hover:bg-accent-success hover:text-bg-primary"
                    >
                      {isPlaying ? <Pause size={16} /> : <Play size={16} />}
                    </button>
                    <span className="text-sm font-mono text-text-secondary">
                      Frame {currentFrameIndex + 1} / {selectedAnim.frames.length}
                    </span>
                    <div className="flex-1" />
                    <div className="flex items-center gap-2">
                      <label className="text-xs text-text-muted">FPS:</label>
                      <input
                        type="number"
                        min="1"
                        max="60"
                        value={selectedAnim.fps}
                        onChange={(e) => updateFrameAnimation(selectedAnim.id, { fps: Number(e.target.value) })}
                        className="w-14 font-mono text-xs"
                      />
                      <label className="text-xs text-text-muted ml-2">
                        <input
                          type="checkbox"
                          checked={selectedAnim.loop}
                          onChange={(e) => updateFrameAnimation(selectedAnim.id, { loop: e.target.checked })}
                          className="mr-1"
                        />
                        Loop
                      </label>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 mb-3">
                    <button onClick={handleAddEmptyFrame} className="btn-secondary text-xs flex items-center gap-1">
                      <Plus size={12} /> Add Frame
                    </button>
                    <button onClick={() => fileInputRef.current?.click()} className="btn-secondary text-xs flex items-center gap-1">
                      <Upload size={12} /> Import SVGs
                    </button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".svg"
                      multiple
                      onChange={handleImportFiles}
                      className="hidden"
                    />
                  </div>

                  <div className="flex gap-2 overflow-x-auto pb-2">
                    {selectedAnim.frames.map((frame, i) => (
                      <div
                        key={frame.id}
                        className={`flex-shrink-0 w-20 h-16 border rounded cursor-pointer transition-all relative group ${
                          i === currentFrameIndex ? 'border-accent-secondary ring-1 ring-accent-secondary' : 'border-border-primary hover:border-border-hover'
                        }`}
                        onClick={() => setCurrentFrameIndex(i)}
                      >
                        <div
                          className="w-full h-full overflow-hidden"
                          dangerouslySetInnerHTML={{ __html: frame.svgContent }}
                          style={{ pointerEvents: 'none' }}
                        />
                        <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-[10px] text-text-secondary text-center">
                          {i + 1}
                        </div>
                        <button
                          onClick={(e) => { e.stopPropagation(); deleteFrame(selectedAnim.id, frame.id); if (currentFrameIndex >= selectedAnim.frames.length - 1) setCurrentFrameIndex(Math.max(0, selectedAnim.frames.length - 2)); }}
                          className="absolute top-0 right-0 p-0.5 bg-accent-primary text-white rounded-bl opacity-0 group-hover:opacity-100 transition-opacity text-[10px]"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-text-muted">
                <div className="text-center">
                  <Film size={48} className="mx-auto mb-4 opacity-30" />
                  <p className="text-lg mb-2">No animation selected</p>
                  <p className="text-sm">Create a new frame animation or import SVG files to get started</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
