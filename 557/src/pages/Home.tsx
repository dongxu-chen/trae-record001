import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import FunctionInput from '../components/FunctionInput';
import FunctionList from '../components/FunctionList';
import ControlPanel from '../components/ControlPanel';
import CoordinateInfo from '../components/CoordinateInfo';
import { Surface3D } from '../components/Surface3D';
import { AnimationPanel } from '../components/AnimationPanel';
import { IntegrationPanel } from '../components/IntegrationPanel';
import { useGraphStore } from '../store/useGraphStore';
import { useCanvas } from '../hooks/useCanvas';
import { useZoomPan } from '../hooks/useZoomPan';
import { useAnimation } from '../hooks/useAnimation';
import { useIntegration } from '../hooks/useIntegration';
import { apiService } from '../services/apiService';
import { cn } from '@/lib/utils';
import type { Surface3D as Surface3DType } from '../types';

type TabType = '2d' | '3d';

export default function Home() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [activeTab, setActiveTab] = useState<TabType>('2d');
  const [surfaces, setSurfaces] = useState<Surface3DType[]>([]);

  const {
    functions,
    viewState,
    mouseState,
    resetView,
    setViewState,
    loadFromLocalStorage,
  } = useGraphStore();

  useEffect(() => {
    loadFromLocalStorage();
  }, [loadFromLocalStorage]);

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current;
        setDimensions({ width: clientWidth, height: clientHeight });
      }
    };

    updateDimensions();

    const resizeObserver = new ResizeObserver(updateDimensions);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    window.addEventListener('resize', updateDimensions);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', updateDimensions);
    };
  }, []);

  const firstFunction = useMemo(() => functions[0] || null, [functions]);

  const animationHook = useAnimation({
    expression: firstFunction?.expression || 'sin(x)',
    viewState: { xMin: viewState.xMin, xMax: viewState.xMax },
    numPoints: 800
  });

  const integrationHook = useIntegration({
    functions: functions.map(f => ({
      id: f.id,
      expression: f.expression,
      compiledFunction: f.compiledFunction
    })),
    viewState
  });

  const { canvasRef, exportToPNG } = useCanvas({
    width: dimensions.width,
    height: dimensions.height,
    integrationPoints: integrationHook.integrationPoints,
    integrationConfig: integrationHook.integrationConfig,
    animatedPoints: animationHook.animationConfig.enabled ? animationHook.currentPoints : [],
    animatedColor: firstFunction?.color || '#3b82f6',
    animatedEnabled: animationHook.animationConfig.enabled
  });

  const {
    handleWheel,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleMouseLeave,
  } = useZoomPan({
    canvasWidth: dimensions.width,
    canvasHeight: dimensions.height,
  });

  const zoomLevel = 20 / (viewState.xMax - viewState.xMin);

  const handleToggleGrid = useCallback(() => {
    setViewState({ gridVisible: !viewState.gridVisible });
  }, [viewState.gridVisible, setViewState]);

  const handleToggleAxes = useCallback(() => {
    setViewState({ axisVisible: !viewState.axisVisible });
  }, [viewState.axisVisible, setViewState]);

  const handleExportPNG = useCallback(() => {
    const dataUrl = exportToPNG();
    if (dataUrl) {
      apiService.downloadImage(dataUrl, 'graph.png');
    }
  }, [exportToPNG]);

  const simpleFunctionsForIntegration = useMemo(() =>
    functions.map(f => ({
      id: f.id,
      expression: f.expression,
      color: f.color
    })),
    [functions]
  );

  return (
    <div className="flex h-screen w-screen bg-slate-900 text-slate-200 overflow-hidden">
      <div className="w-80 flex flex-col bg-slate-800 border-r border-slate-700 overflow-hidden">
        <div className="p-4 border-b border-slate-700">
          <h1 className="text-xl font-bold text-cyan-400 mb-1">函数图像绘制器</h1>
          <p className="text-xs text-slate-400">支持2D/3D、动画、积分可视化</p>
        </div>

        <div className="flex border-b border-slate-700">
          <button
            onClick={() => setActiveTab('2d')}
            className={cn(
              'flex-1 py-2 text-sm font-medium transition-colors',
              activeTab === '2d'
                ? 'bg-slate-700 text-cyan-400 border-b-2 border-cyan-400'
                : 'text-slate-400 hover:text-slate-200'
            )}
          >
            📈 2D 绘图
          </button>
          <button
            onClick={() => setActiveTab('3d')}
            className={cn(
              'flex-1 py-2 text-sm font-medium transition-colors',
              activeTab === '3d'
                ? 'bg-slate-700 text-cyan-400 border-b-2 border-cyan-400'
                : 'text-slate-400 hover:text-slate-200'
            )}
          >
            🌐 3D 曲面
          </button>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {activeTab === '2d' && (
            <>
              <div className="p-4 border-b border-slate-700">
                <FunctionInput />
              </div>

              <div className="p-4 border-b border-slate-700">
                <FunctionList />
              </div>

              <div className="p-4 border-b border-slate-700">
                <AnimationPanel
                  expression={firstFunction?.expression || 'sin(x)'}
                  animationConfig={animationHook.animationConfig}
                  setAnimationConfig={animationHook.setAnimationConfig}
                  isPlaying={animationHook.isPlaying}
                  currentValue={animationHook.animationConfig.currentValue}
                  play={animationHook.play}
                  pause={animationHook.pause}
                  reset={animationHook.reset}
                  stepForward={animationHook.stepForward}
                  stepBackward={animationHook.stepBackward}
                  setParameterValue={animationHook.setParameterValue}
                  validation={animationHook.validation}
                  currentExpression={animationHook.currentExpression}
                />
              </div>

              <div className="p-4">
                <IntegrationPanel
                  integrationConfig={integrationHook.integrationConfig}
                  setIntegrationConfig={integrationHook.setIntegrationConfig}
                  functions={simpleFunctionsForIntegration}
                  selectedFunction={integrationHook.selectedFunction}
                  integrationResult={integrationHook.integrationResult}
                  setSelectedFunctionId={integrationHook.setSelectedFunctionId}
                  setLowerBound={integrationHook.setLowerBound}
                  setUpperBound={integrationHook.setUpperBound}
                  calculateIntegral={integrationHook.calculateIntegral}
                  error={integrationHook.error}
                />
              </div>
            </>
          )}

          {activeTab === '3d' && (
            <div className="p-4">
              <div className="mb-4 p-3 bg-blue-900/30 border border-blue-700 rounded-lg">
                <h4 className="text-blue-300 text-sm font-medium mb-1">💡 使用提示</h4>
                <ul className="text-xs text-blue-400 space-y-1">
                  <li>• 输入二元函数 z = f(x, y)</li>
                  <li>• 拖拽旋转视角，滚轮缩放</li>
                  <li>• 支持三角函数、指数、分段函数</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 relative" ref={containerRef}>
        {activeTab === '2d' && (
          <>
            <canvas
              ref={canvasRef}
              width={dimensions.width}
              height={dimensions.height}
              className={cn(
                'absolute inset-0 h-full w-full',
                mouseState.isDragging ? 'cursor-grabbing' : 'cursor-grab'
              )}
              onWheel={handleWheel}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseLeave}
            />

            <ControlPanel
              onResetView={resetView}
              showGrid={viewState.gridVisible}
              onToggleGrid={handleToggleGrid}
              showAxes={viewState.axisVisible}
              onToggleAxes={handleToggleAxes}
              onExportPNG={handleExportPNG}
              zoomLevel={zoomLevel}
            />

            <CoordinateInfo
              x={mouseState.mathX}
              y={mouseState.mathY}
              zoomLevel={zoomLevel}
            />

            {animationHook.animationConfig.enabled && (
              <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-gray-800/90 backdrop-blur-sm px-6 py-3 rounded-lg border border-gray-700">
                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <p className="text-xs text-gray-400">参数 {animationHook.animationConfig.parameterName}</p>
                    <p className="text-lg font-mono text-cyan-400">
                      {animationHook.animationConfig.currentValue.toFixed(3)}
                    </p>
                  </div>
                  <div className="text-xs text-gray-500">
                    <p>
                      f(x) = <span className="text-gray-300 font-mono">{animationHook.currentExpression}</span>
                    </p>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {activeTab === '3d' && (
          <div className="absolute inset-0 flex items-center justify-center p-4">
            <Surface3D
              width={Math.max(600, dimensions.width - 400)}
              height={Math.max(400, dimensions.height - 40)}
              surfaces={surfaces}
              onSurfacesChange={setSurfaces}
            />
          </div>
        )}
      </div>
    </div>
  );
}
