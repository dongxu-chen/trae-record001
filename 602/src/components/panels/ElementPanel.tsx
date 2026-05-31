import React from 'react';
import { Square, Circle, Diamond, Minus, PenTool, Triangle, Type, Eye, EyeOff, Lock, Unlock, Trash2, Copy } from 'lucide-react';
import { useProjectStore } from '@/store/useProjectStore';
import { useEditorStore } from '@/store/useEditorStore';
import type { ElementType } from '@/types';

const elementTypes: { type: ElementType; icon: React.ReactNode; label: string }[] = [
  { type: 'rect', icon: <Square size={18} />, label: 'Rectangle' },
  { type: 'circle', icon: <Circle size={18} />, label: 'Circle' },
  { type: 'ellipse', icon: <Diamond size={18} />, label: 'Ellipse' },
  { type: 'line', icon: <Minus size={18} />, label: 'Line' },
  { type: 'path', icon: <PenTool size={18} />, label: 'Path' },
  { type: 'polygon', icon: <Triangle size={18} />, label: 'Polygon' },
  { type: 'text', icon: <Type size={18} />, label: 'Text' },
];

export const ElementPanel: React.FC = () => {
  const { project, addElement, updateElement, deleteElement, duplicateElement } = useProjectStore();
  const { selectedElementId, setSelectedElementId } = useEditorStore();

  return (
    <div className="h-full flex flex-col bg-bg-secondary border-r border-border-primary">
      <div className="panel-header">
        Elements
      </div>
      
      <div className="p-2 border-b border-border-primary">
        <div className="grid grid-cols-4 gap-1">
          {elementTypes.map(({ type, icon, label }) => (
            <button
              key={type}
              onClick={() => addElement(type)}
              className="flex flex-col items-center justify-center p-2 rounded hover:bg-bg-tertiary transition-colors group"
              title={label}
            >
              <span className="text-text-secondary group-hover:text-text-primary transition-colors">
                {icon}
              </span>
              <span className="text-[10px] text-text-muted mt-1">{label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="panel-header border-t-0">
        Layers
      </div>

      <div className="flex-1 overflow-y-auto">
        {project.elements.length === 0 ? (
          <div className="p-4 text-center text-text-muted text-sm">
            No elements yet
            <br />
            <span className="text-xs">Click an element above to add</span>
          </div>
        ) : (
          <div className="py-1">
            {[...project.elements].reverse().map((element) => (
              <div
                key={element.id}
                className={`flex items-center px-2 py-1.5 cursor-pointer transition-colors group ${
                  selectedElementId === element.id
                    ? 'bg-bg-tertiary'
                    : 'hover:bg-bg-tertiary/50'
                }`}
                onClick={() => setSelectedElementId(element.id)}
              >
                <button
                  className="p-1 hover:bg-bg-primary rounded mr-1"
                  onClick={(e) => {
                    e.stopPropagation();
                    updateElement(element.id, { visible: !element.visible });
                  }}
                >
                  {element.visible ? (
                    <Eye size={14} className="text-text-secondary" />
                  ) : (
                    <EyeOff size={14} className="text-text-muted" />
                  )}
                </button>
                
                <button
                  className="p-1 hover:bg-bg-primary rounded mr-2"
                  onClick={(e) => {
                    e.stopPropagation();
                    updateElement(element.id, { locked: !element.locked });
                  }}
                >
                  {element.locked ? (
                    <Lock size={14} className="text-text-muted" />
                  ) : (
                    <Unlock size={14} className="text-text-secondary" />
                  )}
                </button>

                <span className={`flex-1 text-sm truncate ${
                  element.locked ? 'text-text-muted' : 'text-text-primary'
                }`}>
                  {element.name}
                </span>

                <div className="flex opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    className="p-1 hover:bg-bg-primary rounded"
                    onClick={(e) => {
                      e.stopPropagation();
                      duplicateElement(element.id);
                    }}
                  >
                    <Copy size={14} className="text-text-secondary" />
                  </button>
                  <button
                    className="p-1 hover:bg-accent-primary/20 rounded"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteElement(element.id);
                      if (selectedElementId === element.id) {
                        setSelectedElementId(null);
                      }
                    }}
                  >
                    <Trash2 size={14} className="text-accent-primary" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
