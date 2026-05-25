import { useState, useCallback, useEffect } from 'react';
import { Upload, Github, Settings, HelpCircle, Maximize2, Minimize2, User, Wrench } from 'lucide-react';
import { Viewport3D } from '@/components/editor/Viewport3D';
import { SkeletonHierarchy } from '@/components/editor/SkeletonHierarchy';
import { TransformPanel } from '@/components/editor/TransformPanel';
import { Timeline } from '@/components/editor/Timeline';
import { CurveEditor } from '@/components/editor/CurveEditor';
import { AnimationBlender } from '@/components/editor/AnimationBlender';
import { Skeleton2DPreview } from '@/components/editor/Skeleton2DPreview';
import { AdvancedToolsPanel } from '@/components/editor/AdvancedToolsPanel';
import { DockPanel } from '@/components/layout/DockPanel';
import { ResizableHandle } from '@/components/layout/ResizableHandle';
import { Button } from '@/components/ui/Button';
import { useEditorStore } from '@/store/editorStore';
import { useModelLoader } from '@/hooks/useModelLoader';
import { cn } from '@/lib/utils';

export default function Home() {
  const [showCurveEditor, setShowCurveEditor] = useState(true);
  const [show2DPreview, setShow2DPreview] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [leftPanelWidth, setLeftPanelWidth] = useState(280);
  const [rightPanelWidth, setRightPanelWidth] = useState(320);
  const [bottomPanelHeight, setBottomPanelHeight] = useState(280);
  const [previewPanelSize, setPreviewPanelSize] = useState({ width: 220, height: 280 });

  const { loadModel, model, clearModel, loadSampleModel } = useEditorStore();
  const { handleFileInput, isLoading, error } = useModelLoader();

  const handleLeftResize = useCallback((delta: number) => {
    setLeftPanelWidth(prev => Math.max(200, Math.min(400, prev + delta)));
  }, []);

  const handleRightResize = useCallback((delta: number) => {
    setRightPanelWidth(prev => Math.max(240, Math.min(500, prev - delta)));
  }, []);

  const handleBottomResize = useCallback((delta: number) => {
    setBottomPanelHeight(prev => Math.max(160, Math.min(500, prev - delta)));
  }, []);

  const handleLoadModel = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await handleFileInput(e);
    }
  }, [handleFileInput]);

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  }, []);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  return (
    <div className="h-screen w-screen flex flex-col bg-space-950 overflow-hidden">
      {/* 顶部菜单栏 */}
      <header className="h-12 bg-space-900 border-b border-cyber-900/50 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-gradient-to-br from-cyber-400 to-cyber-600 flex items-center justify-center shadow-cyber-glow-sm">
              <span className="text-white font-bold text-sm">3D</span>
            </div>
            <h1 className="font-display font-semibold text-lg text-cyber-400 tracking-wide">
              骨骼动画编辑器
            </h1>
          </div>

          <div className="h-6 w-px bg-cyber-900/50" />

          <div className="flex items-center gap-2">
            <label className="cursor-pointer">
              <input
                type="file"
                accept=".fbx,.glb,.gltf"
                onChange={handleLoadModel}
                className="hidden"
              />
              <Button
                variant="primary"
                size="sm"
                className="gap-2 ripple"
                loading={isLoading}
              >
                <Upload size={16} />
                导入模型
              </Button>
            </label>

            <Button
              variant="secondary"
              size="sm"
              className="gap-2"
              onClick={loadSampleModel}
            >
              <User size={16} />
              示例模型
            </Button>

            {model && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearModel}
                className="text-neon-red hover:text-neon-red hover:bg-neon-red/10"
              >
                清除
              </Button>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {error && (
            <span className="text-xs text-neon-red mr-4">{error}</span>
          )}

          <Button variant="ghost" size="sm" className="text-space-400">
            <HelpCircle size={18} />
          </Button>
          <Button variant="ghost" size="sm" className="text-space-400">
            <Settings size={18} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleFullscreen}
            className="text-space-400"
          >
            {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </Button>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-space-400 hover:text-cyber-400 transition-colors"
          >
            <Github size={18} />
          </a>
        </div>
      </header>

      {/* 主内容区域 */}
      <div className="flex-1 flex overflow-hidden relative grid-pattern">
        {/* 左侧面板 - 骨骼层级 */}
        <DockPanel
          position="left"
          title="骨骼层级"
          width={leftPanelWidth}
          onClose={() => setLeftPanelWidth(0)}
        >
          <SkeletonHierarchy />
        </DockPanel>

        {/* 左侧可拖拽分隔条 */}
        {leftPanelWidth > 0 && (
          <ResizableHandle
            direction="horizontal"
            onResize={handleLeftResize}
          />
        )}

        {/* 中间主区域 */}
        <div className="flex-1 flex flex-col relative min-w-0">
          {/* 3D视口 */}
          <div className="flex-1 relative min-h-0">
            <Viewport3D />

            {/* 右上角2D骨骼预览 */}
            {show2DPreview && model && (
              <div className="absolute top-4 right-4 z-10">
                <div className="panel-border rounded-lg overflow-hidden bg-space-900/90 backdrop-blur-sm">
                  <div className="flex items-center justify-between px-3 py-1.5 border-b border-cyber-900/50">
                    <span className="text-xs font-medium text-cyber-400">2D 骨骼示意</span>
                    <button
                      onClick={() => setShow2DPreview(false)}
                      className="text-space-500 hover:text-cyber-400 transition-colors"
                    >
                      ×
                    </button>
                  </div>
                  <div
                    style={{ width: previewPanelSize.width, height: previewPanelSize.height }}
                    className="relative"
                  >
                    <Skeleton2DPreview />
                    {/* 右下角拖拽调整大小 */}
                    <div
                      className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize"
                      onMouseDown={(e) => {
                        e.preventDefault();
                        const startX = e.clientX;
                        const startY = e.clientY;
                        const startW = previewPanelSize.width;
                        const startH = previewPanelSize.height;
                        const handleMove = (ev: MouseEvent) => {
                          setPreviewPanelSize({
                            width: Math.max(160, startW + (ev.clientX - startX)),
                            height: Math.max(160, startH + (ev.clientY - startY)),
                          });
                        };
                        const handleUp = () => {
                          document.removeEventListener('mousemove', handleMove);
                          document.removeEventListener('mouseup', handleUp);
                        };
                        document.addEventListener('mousemove', handleMove);
                        document.addEventListener('mouseup', handleUp);
                      }}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* 显示2D预览按钮 */}
            {!show2DPreview && model && (
              <Button
                variant="secondary"
                size="sm"
                className="absolute top-4 right-4 z-10"
                onClick={() => setShow2DPreview(true)}
              >
                显示2D预览
              </Button>
            )}
          </div>

          {/* 曲线编辑器展开/折叠按钮 */}
          {showCurveEditor && bottomPanelHeight > 0 && (
            <ResizableHandle
              direction="vertical"
              onResize={handleBottomResize}
            />
          )}

          {/* 曲线编辑器 */}
          {showCurveEditor && bottomPanelHeight > 0 && (
            <div
              className="border-t border-cyber-900/50 bg-space-900/50 shrink-0"
              style={{ height: bottomPanelHeight }}
            >
              <div className="flex items-center justify-between px-4 py-1.5 border-b border-cyber-900/30">
                <h3 className="text-sm font-medium text-cyber-400">曲线编辑器</h3>
                <button
                  onClick={() => setShowCurveEditor(false)}
                  className="text-space-500 hover:text-cyber-400 transition-colors text-lg"
                >
                  ×
                </button>
              </div>
              <div className="h-[calc(100%-36px)]">
                <CurveEditor />
              </div>
            </div>
          )}

          {/* 曲线编辑器展开按钮 */}
          {!showCurveEditor && (
            <button
              onClick={() => setShowCurveEditor(true)}
              className="h-8 bg-space-900 border-t border-cyber-900/50 flex items-center justify-center text-space-500 hover:text-cyber-400 transition-colors shrink-0"
            >
              <span className="text-xs">展开曲线编辑器</span>
            </button>
          )}
        </div>

        {/* 右侧可拖拽分隔条 */}
        {rightPanelWidth > 0 && (
          <ResizableHandle
            direction="horizontal"
            onResize={handleRightResize}
          />
        )}

        {/* 右侧面板 - 属性和动画混合 */}
        <div
          className="flex flex-col bg-space-900/30 shrink-0 border-l border-cyber-900/50"
          style={{ width: rightPanelWidth }}
        >
          {/* 变换属性面板 */}
          <DockPanel position="right" title="变换属性" height={200}>
            <TransformPanel />
          </DockPanel>

          {/* 高级工具面板 */}
          <DockPanel position="right" title="高级工具" height={300} icon={<Wrench size={14} />}>
            <AdvancedToolsPanel />
          </DockPanel>

          <div className="flex-1 min-h-0 border-t border-cyber-900/30">
            <DockPanel position="right" title="动画混合" className="h-full">
              <AnimationBlender />
            </DockPanel>
          </div>
        </div>
      </div>

      {/* 底部时间轴 */}
      <div className="h-44 border-t border-cyber-900/50 bg-space-900/80 shrink-0">
        <Timeline />
      </div>

      {/* 底部状态栏 */}
      <footer className="h-6 bg-space-950 border-t border-cyber-900/30 flex items-center justify-between px-4 text-xs text-space-500 shrink-0">
        <div className="flex items-center gap-4">
          <span>帧率: 60 FPS</span>
          <span className={cn(
            "w-2 h-2 rounded-full",
            isLoading ? "bg-neon-amber animate-pulse" : "bg-neon-green"
          )} />
          <span>{isLoading ? "加载中..." : model ? "模型已加载" : "等待导入"}</span>
        </div>
        <div className="flex items-center gap-4">
          <span>Three.js r160</span>
          <span>|</span>
          <span>v0.1.0</span>
        </div>
      </footer>
    </div>
  );
}
