import { useState, useCallback, useEffect, useRef } from 'react';
import {
  FunctionConfig,
  PolarCurveConfig,
  FourierConfig,
  DisplayMode,
  Point,
  DEFAULT_FUNCTIONS,
  DEFAULT_POLAR_CURVES,
  DEFAULT_FOURIER_CONFIG,
  FUNCTION_COLORS,
  POLAR_CURVE_COLORS,
  X_RANGE,
  Y_RANGE,
} from './types';
import ChartCanvas from './components/ChartCanvas';
import ControlPanel from './components/ControlPanel';
import FunctionSelector from './components/FunctionSelector';
import CoordinateInfo from './components/CoordinateInfo';
import PolarChartCanvas from './components/PolarChartCanvas';
import PolarCurvePanel from './components/PolarCurvePanel';
import FourierDemo from './components/FourierDemo';
import FourierPanel from './components/FourierPanel';
import AnimationControl from './components/AnimationControl';
import { Activity, BarChart3, Globe, Waves } from 'lucide-react';

function App() {
  const [displayMode, setDisplayMode] = useState<DisplayMode>('cartesian');

  const [functions, setFunctions] = useState<FunctionConfig[]>(DEFAULT_FUNCTIONS);
  const [selectedFunctionId, setSelectedFunctionId] = useState<string | null>(
    DEFAULT_FUNCTIONS[0]?.id || null
  );
  const [mousePosition, setMousePosition] = useState<Point | null>(null);
  const [markedPoints, setMarkedPoints] = useState<Point[]>([]);

  const [polarCurves, setPolarCurves] = useState<PolarCurveConfig[]>(DEFAULT_POLAR_CURVES);
  const [selectedPolarCurveId, setSelectedPolarCurveId] = useState<string | null>(
    DEFAULT_POLAR_CURVES[0]?.id || null
  );

  const [fourierConfig, setFourierConfig] = useState<FourierConfig>(DEFAULT_FOURIER_CONFIG);

  const [animationState, setAnimationState] = useState({
    isPlaying: false,
    speed: 1,
    currentTime: 0,
    animationParam: 'phase' as const,
  });

  const animationRef = useRef<number>();

  useEffect(() => {
    if (animationState.isPlaying) {
      const animate = () => {
        setAnimationState((prev) => ({
          ...prev,
          currentTime: prev.currentTime + 0.016 * prev.speed,
        }));
        animationRef.current = requestAnimationFrame(animate);
      };
      animationRef.current = requestAnimationFrame(animate);
    } else {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    }

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [animationState.isPlaying, animationState.speed]);

  useEffect(() => {
    if (!animationState.isPlaying || displayMode !== 'cartesian' || !selectedFunctionId) return;

    const param = animationState.animationParam;
    const time = animationState.currentTime;

    setFunctions((prev) =>
      prev.map((func) => {
        if (func.id !== selectedFunctionId) return func;

        switch (param) {
          case 'phase':
            return { ...func, phase: Math.sin(time * 0.5) * Math.PI };
          case 'frequency':
            return { ...func, frequency: 1 + 0.5 * Math.sin(time * 0.5) };
          case 'amplitude':
            return { ...func, amplitude: 1 + 0.5 * Math.sin(time * 0.5) };
          default:
            return func;
        }
      })
    );
  }, [animationState.currentTime, animationState.isPlaying, animationState.animationParam, selectedFunctionId, displayMode]);

  const handleTogglePlay = useCallback(() => {
    setAnimationState((prev) => ({ ...prev, isPlaying: !prev.isPlaying }));
  }, []);

  const handleResetAnimation = useCallback(() => {
    setAnimationState((prev) => ({ ...prev, currentTime: 0 }));
  }, []);

  const handleUpdateFunction = useCallback((id: string, updates: Partial<FunctionConfig>) => {
    setFunctions((prev) =>
      prev.map((func) => (func.id === id ? { ...func, ...updates } : func))
    );
  }, []);

  const handleResetFunction = useCallback((id: string) => {
    setFunctions((prev) =>
      prev.map((func) =>
        func.id === id
          ? {
              ...func,
              frequency: 1,
              phase: 0,
              amplitude: 1,
            }
          : func
      )
    );
  }, []);

  const handleAddFunction = useCallback((type: any) => {
    const newFunction: FunctionConfig = {
      id: `func-${Date.now()}`,
      type,
      frequency: 1,
      phase: 0,
      amplitude: 1,
      color: FUNCTION_COLORS[type],
      visible: true,
      showDerivative: false,
      showIntegral: false,
    };
    setFunctions((prev) => [...prev, newFunction]);
    setSelectedFunctionId(newFunction.id);
  }, []);

  const handleRemoveFunction = useCallback((id: string) => {
    setFunctions((prev) => {
      const filtered = prev.filter((f) => f.id !== id);
      if (selectedFunctionId === id) {
        setSelectedFunctionId(filtered[0]?.id || null);
      }
      return filtered;
    });
  }, [selectedFunctionId]);

  const handleToggleVisibility = useCallback((id: string) => {
    setFunctions((prev) =>
      prev.map((func) =>
        func.id === id ? { ...func, visible: !func.visible } : func
      )
    );
  }, []);

  const handleToggleDerivative = useCallback((id: string) => {
    setFunctions((prev) =>
      prev.map((func) =>
        func.id === id ? { ...func, showDerivative: !func.showDerivative } : func
      )
    );
  }, []);

  const handleToggleIntegral = useCallback((id: string) => {
    setFunctions((prev) =>
      prev.map((func) =>
        func.id === id ? { ...func, showIntegral: !func.showIntegral } : func
      )
    );
  }, []);

  const handleMouseMove = useCallback((point: Point | null) => {
    setMousePosition(point);
  }, []);

  const handleChartClick = useCallback((point: Point) => {
    setMarkedPoints((prev) => [...prev, point]);
  }, []);

  const handleClearMarkedPoints = useCallback(() => {
    setMarkedPoints([]);
  }, []);

  const handleAddPolarCurve = useCallback((type: any) => {
    const newCurve: PolarCurveConfig = {
      id: `polar-${Date.now()}`,
      type,
      a: 1,
      b: 1,
      n: 3,
      color: POLAR_CURVE_COLORS[type],
      visible: true,
    };
    setPolarCurves((prev) => [...prev, newCurve]);
    setSelectedPolarCurveId(newCurve.id);
  }, []);

  const handleRemovePolarCurve = useCallback((id: string) => {
    setPolarCurves((prev) => {
      const filtered = prev.filter((c) => c.id !== id);
      if (selectedPolarCurveId === id) {
        setSelectedPolarCurveId(filtered[0]?.id || null);
      }
      return filtered;
    });
  }, [selectedPolarCurveId]);

  const handleTogglePolarVisibility = useCallback((id: string) => {
    setPolarCurves((prev) =>
      prev.map((curve) =>
        curve.id === id ? { ...curve, visible: !curve.visible } : curve
      )
    );
  }, []);

  const handleUpdatePolarCurve = useCallback((id: string, updates: Partial<PolarCurveConfig>) => {
    setPolarCurves((prev) =>
      prev.map((curve) => (curve.id === id ? { ...curve, ...updates } : curve))
    );
  }, []);

  const handleUpdateFourierConfig = useCallback((updates: Partial<FourierConfig>) => {
    setFourierConfig((prev) => ({ ...prev, ...updates }));
  }, []);

  const renderChart = () => {
    switch (displayMode) {
      case 'cartesian':
        return (
          <ChartCanvas
            functions={functions}
            mousePosition={mousePosition}
            markedPoints={markedPoints}
            onMouseMove={handleMouseMove}
            onChartClick={handleChartClick}
            xRange={X_RANGE}
            yRange={Y_RANGE}
          />
        );
      case 'polar':
        return (
          <PolarChartCanvas
            curves={polarCurves}
            selectedCurveId={selectedPolarCurveId}
            onSelectCurve={setSelectedPolarCurveId}
            animationTime={animationState.isPlaying ? animationState.currentTime : 0}
          />
        );
      case 'fourier':
        return (
          <FourierDemo
            config={fourierConfig}
            animationTime={animationState.isPlaying ? animationState.currentTime : 0}
          />
        );
      default:
        return null;
    }
  };

  const renderControlPanel = () => {
    switch (displayMode) {
      case 'cartesian':
        return (
          <>
            <FunctionSelector
              functions={functions}
              selectedFunctionId={selectedFunctionId}
              onSelectFunction={setSelectedFunctionId}
              onAddFunction={handleAddFunction}
              onRemoveFunction={handleRemoveFunction}
              onToggleVisibility={handleToggleVisibility}
              onToggleDerivative={handleToggleDerivative}
              onToggleIntegral={handleToggleIntegral}
            />
            <ControlPanel
              selectedFunctionId={selectedFunctionId}
              functions={functions}
              onUpdateFunction={handleUpdateFunction}
              onResetFunction={handleResetFunction}
            />
            <CoordinateInfo
              mousePosition={mousePosition}
              markedPoints={markedPoints}
              functions={functions}
              onClearMarkedPoints={handleClearMarkedPoints}
            />
          </>
        );
      case 'polar':
        return (
          <PolarCurvePanel
            curves={polarCurves}
            selectedCurveId={selectedPolarCurveId}
            onSelectCurve={setSelectedPolarCurveId}
            onAddCurve={handleAddPolarCurve}
            onRemoveCurve={handleRemovePolarCurve}
            onToggleVisibility={handleTogglePolarVisibility}
            onUpdateCurve={handleUpdatePolarCurve}
          />
        );
      case 'fourier':
        return (
          <FourierPanel
            config={fourierConfig}
            onUpdateConfig={handleUpdateFourierConfig}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  三角函数可视化工具
                </h1>
                <p className="text-xs text-gray-500">
                  Trigonometric Function Visualizer
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setDisplayMode('cartesian')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all ${
                  displayMode === 'cartesian'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                <BarChart3 className="w-4 h-4" />
                直角坐标
              </button>
              <button
                onClick={() => setDisplayMode('polar')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all ${
                  displayMode === 'polar'
                    ? 'bg-orange-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                <Globe className="w-4 h-4" />
                极坐标
              </button>
              <button
                onClick={() => setDisplayMode('fourier')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all ${
                  displayMode === 'fourier'
                    ? 'bg-cyan-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                <Waves className="w-4 h-4" />
                傅里叶
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-3 space-y-4">
            {renderControlPanel()}
            <AnimationControl
              state={animationState}
              onTogglePlay={handleTogglePlay}
              onReset={handleResetAnimation}
              onSpeedChange={(speed) => setAnimationState((prev) => ({ ...prev, speed }))}
              onParamChange={(param) => setAnimationState((prev) => ({ ...prev, animationParam: param }))}
            />
          </div>

          <div className="lg:col-span-9">
            <div className="h-[calc(100vh-180px)] min-h-[500px]">
              {renderChart()}
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-gray-800 mt-8">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <p className="text-center text-xs text-gray-600">
            使用 React + Chart.js + mathjs 构建 | 支持 sin, cos, tan, cot, sec, csc 函数 | 极坐标曲线 | 傅里叶级数
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
