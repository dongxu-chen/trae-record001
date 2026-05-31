import React, { useState } from 'react';
import { useProjectStore } from '@/store/useProjectStore';
import { useEditorStore } from '@/store/useEditorStore';
import type { AnimationProperty } from '@/types';
import { Plus, Trash2, Edit3, ChevronDown, ChevronUp } from 'lucide-react';
import { EasingEditor } from './EasingEditor';

interface PropertyPanelProps {
  onEditPath?: (elementId: string) => void;
}

export const PropertyPanel: React.FC<PropertyPanelProps> = ({ onEditPath }) => {
  const { project, updateElement, addTrack, updateTrack, deleteTrack, addKeyframe, deleteKeyframe } = useProjectStore();
  const { selectedElementId, currentTime } = useEditorStore();
  const [expandedTracks, setExpandedTracks] = useState<Set<string>>(new Set());

  const selectedElement = project.elements.find(e => e.id === selectedElementId);
  const elementTracks = project.tracks.filter(t => t.elementId === selectedElementId);

  const toggleTrackExpand = (trackId: string) => {
    setExpandedTracks(prev => {
      const next = new Set(prev);
      if (next.has(trackId)) {
        next.delete(trackId);
      } else {
        next.add(trackId);
      }
      return next;
    });
  };

  const handleTransformChange = (key: string, value: number) => {
    if (!selectedElement) return;
    updateElement(selectedElementId!, {
      transform: {
        ...selectedElement.transform,
        [key]: value,
      },
    });
  };

  const handleAttributeChange = (key: string, value: any) => {
    if (!selectedElement) return;
    updateElement(selectedElementId!, {
      attributes: {
        ...selectedElement.attributes,
        [key]: value,
      },
    });
  };

  const handleNameChange = (name: string) => {
    if (!selectedElement) return;
    updateElement(selectedElementId!, { name });
  };

  const properties: AnimationProperty[] = ['x', 'y', 'rotation', 'scale', 'opacity', 'fill', 'stroke'];

  if (!selectedElement) {
    return (
      <div className="h-full bg-bg-secondary border-l border-border-primary">
        <div className="panel-header">
          Properties
        </div>
        <div className="p-4 text-center text-text-muted text-sm">
          Select an element to edit its properties
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-bg-secondary border-l border-border-primary">
      <div className="panel-header">
        Properties
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-3 border-b border-border-primary">
          <label className="block text-xs text-text-muted mb-1">Name</label>
          <input
            type="text"
            value={selectedElement.name}
            onChange={(e) => handleNameChange(e.target.value)}
            className="w-full"
          />
        </div>

        <div className="p-3 border-b border-border-primary">
          <h4 className="text-xs font-semibold text-text-secondary mb-3 uppercase">Transform</h4>
          
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-text-muted mb-1">X</label>
                <input
                  type="number"
                  value={Math.round(selectedElement.transform.x)}
                  onChange={(e) => handleTransformChange('x', Number(e.target.value))}
                  className="w-full font-mono"
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">Y</label>
                <input
                  type="number"
                  value={Math.round(selectedElement.transform.y)}
                  onChange={(e) => handleTransformChange('y', Number(e.target.value))}
                  className="w-full font-mono"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-text-muted mb-1">Rotation</label>
                <input
                  type="number"
                  value={Math.round(selectedElement.transform.rotation)}
                  onChange={(e) => handleTransformChange('rotation', Number(e.target.value))}
                  className="w-full font-mono"
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">Scale</label>
                <input
                  type="number"
                  step="0.1"
                  value={selectedElement.transform.scaleX.toFixed(2)}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    handleTransformChange('scaleX', val);
                    handleTransformChange('scaleY', val);
                  }}
                  className="w-full font-mono"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="p-3 border-b border-border-primary">
          <h4 className="text-xs font-semibold text-text-secondary mb-3 uppercase">Appearance</h4>
          
          <div className="space-y-2">
            {selectedElement.type !== 'line' && selectedElement.type !== 'path' && (
              <div>
                <label className="block text-xs text-text-muted mb-1">Fill</label>
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={selectedElement.attributes.fill || '#000000'}
                    onChange={(e) => handleAttributeChange('fill', e.target.value)}
                    className="w-8 h-8 p-0 border-0 cursor-pointer"
                  />
                  <input
                    type="text"
                    value={selectedElement.attributes.fill || ''}
                    onChange={(e) => handleAttributeChange('fill', e.target.value)}
                    className="flex-1 font-mono"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs text-text-muted mb-1">Stroke</label>
              <div className="flex gap-2">
                <input
                  type="color"
                  value={selectedElement.attributes.stroke || '#000000'}
                  onChange={(e) => handleAttributeChange('stroke', e.target.value)}
                  className="w-8 h-8 p-0 border-0 cursor-pointer"
                />
                <input
                  type="text"
                  value={selectedElement.attributes.stroke || ''}
                  onChange={(e) => handleAttributeChange('stroke', e.target.value)}
                  className="flex-1 font-mono"
                  placeholder="none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-text-muted mb-1">Stroke Width</label>
              <input
                type="number"
                min="0"
                value={selectedElement.attributes.strokeWidth || 0}
                onChange={(e) => handleAttributeChange('strokeWidth', Number(e.target.value))}
                className="w-full font-mono"
              />
            </div>

            {(selectedElement.type === 'rect') && (
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-text-muted mb-1">Width</label>
                  <input
                    type="number"
                    value={selectedElement.attributes.width}
                    onChange={(e) => handleAttributeChange('width', Number(e.target.value))}
                    className="w-full font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-muted mb-1">Height</label>
                  <input
                    type="number"
                    value={selectedElement.attributes.height}
                    onChange={(e) => handleAttributeChange('height', Number(e.target.value))}
                    className="w-full font-mono"
                  />
                </div>
              </div>
            )}

            {selectedElement.type === 'circle' && (
              <div>
                <label className="block text-xs text-text-muted mb-1">Radius</label>
                <input
                  type="number"
                  value={selectedElement.attributes.r}
                  onChange={(e) => handleAttributeChange('r', Number(e.target.value))}
                  className="w-full font-mono"
                />
              </div>
            )}

            {selectedElement.type === 'text' && (
              <>
                <div>
                  <label className="block text-xs text-text-muted mb-1">Text</label>
                  <input
                    type="text"
                    value={selectedElement.attributes.text || ''}
                    onChange={(e) => handleAttributeChange('text', e.target.value)}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-muted mb-1">Font Size</label>
                  <input
                    type="number"
                    value={selectedElement.attributes.fontSize || 16}
                    onChange={(e) => handleAttributeChange('fontSize', Number(e.target.value))}
                    className="w-full font-mono"
                  />
                </div>
              </>
            )}

            {selectedElement.type === 'path' && (
              <div>
                <label className="block text-xs text-text-muted mb-1">Path Data</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={selectedElement.attributes.d || ''}
                    onChange={(e) => handleAttributeChange('d', e.target.value)}
                    className="flex-1 font-mono text-xs"
                    placeholder="M 0 0 L 100 100"
                  />
                  {onEditPath && (
                    <button
                      onClick={() => onEditPath(selectedElementId!)}
                      className="btn-icon bg-bg-tertiary text-accent-secondary hover:text-white"
                      title="Edit path visually"
                    >
                      <Edit3 size={14} />
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="p-3">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-semibold text-text-secondary uppercase">Animations</h4>
          </div>

          <div className="space-y-2 mb-3">
            {elementTracks.map((track) => {
              const isExpanded = expandedTracks.has(track.id);
              return (
                <div
                  key={track.id}
                  className="bg-bg-tertiary/50 rounded border border-border-primary overflow-hidden"
                >
                  <div
                    className="flex items-center justify-between p-2 cursor-pointer hover:bg-bg-tertiary/70 transition-colors"
                    onClick={() => toggleTrackExpand(track.id)}
                  >
                    <div className="flex items-center gap-2">
                      {isExpanded ? (
                        <ChevronDown size={14} className="text-text-muted" />
                      ) : (
                        <ChevronUp size={14} className="text-text-muted" />
                      )}
                      <span className="text-sm text-text-primary">{track.property}</span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteTrack(track.id);
                      }}
                      className="p-1 hover:bg-accent-primary/20 rounded"
                    >
                      <Trash2 size={12} className="text-accent-primary" />
                    </button>
                  </div>

                  {isExpanded && (
                    <div className="p-2 pt-0 border-t border-border-primary">
                      <div className="grid grid-cols-2 gap-2 mb-3 mt-2">
                        <div>
                          <label className="block text-[10px] text-text-muted mb-1">Duration</label>
                          <input
                            type="number"
                            step="0.1"
                            value={track.duration}
                            onChange={(e) => updateTrack(track.id, { duration: Number(e.target.value) })}
                            className="w-full font-mono text-xs"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] text-text-muted mb-1">Delay</label>
                          <input
                            type="number"
                            step="0.1"
                            value={track.delay}
                            onChange={(e) => updateTrack(track.id, { delay: Number(e.target.value) })}
                            className="w-full font-mono text-xs"
                          />
                        </div>
                      </div>

                      <EasingEditor
                        value={track.easing}
                        onChange={(value) => updateTrack(track.id, { easing: value })}
                      />

                      {track.keyframes.length > 0 && (
                        <div className="mt-3 pt-2 border-t border-border-primary">
                          <div className="text-[10px] text-text-muted mb-2">Keyframes</div>
                          <div className="flex flex-wrap gap-1">
                            {track.keyframes.map((kf) => (
                              <div
                                key={kf.id}
                                className="flex items-center gap-1 px-2 py-1 bg-bg-primary rounded text-xs"
                              >
                                <span>{kf.time.toFixed(1)}s</span>
                                <button
                                  onClick={() => deleteKeyframe(track.id, kf.id)}
                                  className="text-accent-primary hover:text-white"
                                >
                                  ×
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <button
                        onClick={() => addKeyframe(track.id, currentTime, 0)}
                        className="mt-3 w-full py-1.5 text-xs bg-bg-primary text-text-secondary hover:text-text-primary rounded transition-colors"
                      >
                        + Add keyframe at {currentTime.toFixed(1)}s
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="space-y-1">
            <div className="text-[10px] text-text-muted mb-2">Add Animation Track</div>
            <div className="grid grid-cols-2 gap-1">
              {properties.map((prop) => {
                const hasTrack = elementTracks.some(t => t.property === prop);
                return (
                  <button
                    key={prop}
                    onClick={() => !hasTrack && addTrack(selectedElementId!, prop)}
                    disabled={hasTrack}
                    className={`flex items-center justify-center gap-1 py-1.5 text-xs rounded transition-colors ${
                      hasTrack
                        ? 'bg-bg-tertiary/30 text-text-muted cursor-not-allowed'
                        : 'bg-bg-tertiary hover:bg-accent-primary text-text-secondary hover:text-white'
                    }`}
                  >
                    {!hasTrack && <Plus size={12} />}
                    {prop}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
