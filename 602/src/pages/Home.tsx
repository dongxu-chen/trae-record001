import { useState, useEffect, useCallback } from 'react';
import { Toolbar } from '@/components/Toolbar';
import { ElementPanel } from '@/components/panels/ElementPanel';
import { PropertyPanel } from '@/components/panels/PropertyPanel';
import { SVGCanvas } from '@/components/editor/SVGCanvas';
import { Timeline } from '@/components/timeline/Timeline';
import { PathEditor } from '@/components/editor/PathEditor';
import { FrameAnimationEditor } from '@/components/modals/FrameAnimationEditor';
import { CodePreview } from '@/components/modals/CodePreview';
import { Marketplace } from '@/components/modals/Marketplace';
import { useProjectStore } from '@/store/useProjectStore';
import { useEditorStore } from '@/store/useEditorStore';

export default function Home() {
  const { project } = useProjectStore();
  const { activeModal } = useEditorStore();
  const [leftPanelWidth, setLeftPanelWidth] = useState(240);
  const [rightPanelWidth, setRightPanelWidth] = useState(280);
  const [timelineHeight, setTimelineHeight] = useState(240);
  const [isResizing, setIsResizing] = useState<string | null>(null);
  const [editingPathId, setEditingPathId] = useState<string | null>(null);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isResizing) return;

    if (isResizing === 'left') {
      setLeftPanelWidth(Math.max(200, Math.min(400, e.clientX)));
    } else if (isResizing === 'right') {
      setRightPanelWidth(Math.max(200, Math.min(400, window.innerWidth - e.clientX)));
    } else if (isResizing === 'bottom') {
      setTimelineHeight(Math.max(150, Math.min(500, window.innerHeight - e.clientY)));
    }
  }, [isResizing]);

  const handleMouseUp = useCallback(() => {
    setIsResizing(null);
  }, []);

  useEffect(() => {
    if (isResizing) {
      const handleMouseMoveWrapper = (e: MouseEvent) => handleMouseMove(e);
      window.addEventListener('mousemove', handleMouseMoveWrapper);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMoveWrapper);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isResizing, handleMouseMove, handleMouseUp]);

  return (
    <div className="h-screen w-screen flex flex-col bg-bg-primary overflow-hidden">
      <Toolbar />

      <div className="flex flex-1 overflow-hidden">
        <div
          className="flex-shrink-0"
          style={{ width: leftPanelWidth }}
        >
          <ElementPanel />
        </div>

        <div
          className="resizer resizer-horizontal"
          style={{ left: leftPanelWidth - 4 }}
          onMouseDown={() => setIsResizing('left')}
        />

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden">
            <SVGCanvas width={project.width} height={project.height} />
          </div>

          <div
            className="resizer resizer-vertical cursor-row-resize"
            onMouseDown={() => setIsResizing('bottom')}
          />

          <div
            className="flex-shrink-0"
            style={{ height: timelineHeight }}
          >
            <Timeline />
          </div>
        </div>

        <div
          className="resizer resizer-horizontal"
          onMouseDown={() => setIsResizing('right')}
        />

        <div
          className="flex-shrink-0"
          style={{ width: rightPanelWidth }}
        >
          <PropertyPanel onEditPath={setEditingPathId} />
        </div>
      </div>

      {editingPathId && (
        <div className="absolute inset-0 z-50 pointer-events-none">
          <div className="pointer-events-auto">
            <PathEditor
              elementId={editingPathId}
              onClose={() => setEditingPathId(null)}
            />
          </div>
        </div>
      )}

      {activeModal === 'frameImport' && <FrameAnimationEditor />}
      {activeModal === 'codePreview' && <CodePreview />}
      {activeModal === 'marketplace' && <Marketplace />}
    </div>
  );
}