import { useState, useCallback, useEffect } from 'react';
import * as THREE from 'three';
import Scene from './components/Scene.jsx';
import Sidebar from './components/Sidebar.jsx';

export default function App() {
  const [modelInfo, setModelInfo] = useState(null);
  const [modelGroup, setModelGroup] = useState(null);
  const [modelBounds, setModelBounds] = useState(new THREE.Box3());
  const [planes, setPlanes] = useState([]);
  const [activePlaneIndex, setActivePlaneIndex] = useState(-1);
  const [showPreview, setShowPreview] = useState(false);
  const [showPieces, setShowPieces] = useState(false);
  const [cutPieces, setCutPieces] = useState(null);
  const [status, setStatus] = useState('就绪');
  const [isProcessing, setIsProcessing] = useState(false);
  const [drawingMode, setDrawingMode] = useState(false);
  const [fillEnabled, setFillEnabled] = useState(false);
  const [fillType, setFillType] = useState('grid');
  const [fillDensity, setFillDensity] = useState(5);
  const [showAnimation, setShowAnimation] = useState(false);
  const [animationState, setAnimationState] = useState('idle');

  const refreshPlanesList = useCallback(() => {
    if (window.__sceneApi) {
      const planeList = window.__sceneApi.getPlanes();
      setPlanes(planeList.map(p => ({
        name: p.name,
        color: p.color,
        normal: p.plane.normal.clone(),
        constant: p.plane.constant
      })));
    }
  }, []);

  const handleModelLoaded = useCallback((result) => {
    setModelInfo(result);
    setModelGroup(result.group);
    setModelBounds(result.boundingBox);
    setCutPieces(null);
    setShowPieces(false);
    setShowPreview(false);
    setPlanes([]);
    setActivePlaneIndex(-1);
    setDrawingMode(false);
    
    setTimeout(() => {
      refreshPlanesList();
    }, 100);
  }, [refreshPlanesList]);

  const handleAddPlane = useCallback((normal) => {
    if (window.__sceneApi) {
      const result = window.__sceneApi.addPlane(normal);
      if (result) {
        refreshPlanesList();
        setActivePlaneIndex(result.index);
        setStatus(`已添加 ${planes.length + 1} 个切割平面`);
      }
    }
  }, [planes.length, refreshPlanesList]);

  const handleRemovePlane = useCallback((index) => {
    if (window.__sceneApi) {
      window.__sceneApi.removePlane(index);
      refreshPlanesList();
      setStatus('已删除切割平面');
    }
  }, [refreshPlanesList]);

  const handleSelectPlane = useCallback((index) => {
    if (window.__sceneApi) {
      setActivePlaneIndex(index);
      const planeList = window.__sceneApi.getPlanes();
      if (planeList[index]) {
        window.__sceneApi.setActivePlane(index);
      }
    }
  }, []);

  const handleRotatePlane = useCallback((index, axis, angle) => {
    if (window.__sceneApi) {
      window.__sceneApi.rotatePlane(index, axis, angle);
      refreshPlanesList();
    }
  }, [refreshPlanesList]);

  const handleFlipPlane = useCallback((index) => {
    if (window.__sceneApi) {
      window.__sceneApi.flipPlane(index);
      refreshPlanesList();
    }
  }, [refreshPlanesList]);

  const handleResetPlane = useCallback((index) => {
    if (window.__sceneApi) {
      window.__sceneApi.resetPlane(index);
      refreshPlanesList();
    }
  }, [refreshPlanesList]);

  const handleShowPreviewChange = useCallback((show) => {
    setShowPreview(show);
    if (show) {
      setStatus('预览模式 - 调整平面时实时显示切割效果');
    } else {
      setStatus('就绪');
    }
  }, []);

  const handleShowPiecesChange = useCallback((show) => {
    setShowPieces(show);
    if (show) {
      setStatus('显示切割结果');
    } else {
      setStatus('就绪');
    }
  }, []);

  const handleCutComplete = useCallback((pieces) => {
    setCutPieces(pieces);
    setShowPieces(true);
    setShowPreview(false);
  }, []);

  const handlePerformCut = useCallback((pieces) => {
    setCutPieces(pieces);
    setShowPieces(true);
    setShowPreview(false);
  }, []);

  const handleDrawingModeChange = useCallback((enabled) => {
    setDrawingMode(enabled);
    if (window.__sceneApi) {
      if (enabled) {
        window.__sceneApi.startCurveDrawing();
      } else {
        window.__sceneApi.stopCurveDrawing();
      }
    }
  }, []);

  const handleFillEnabledChange = useCallback((enabled) => {
    setFillEnabled(enabled);
  }, []);

  const handleFillTypeChange = useCallback((type) => {
    setFillType(type);
  }, []);

  const handleFillDensityChange = useCallback((density) => {
    setFillDensity(density);
  }, []);

  const handleShowAnimationChange = useCallback((show) => {
    setShowAnimation(show);
  }, []);

  const handleAnimationStateChange = useCallback((state) => {
    setAnimationState(state);
  }, []);

  const handleReset = useCallback(() => {
    setModelInfo(null);
    setModelGroup(null);
    setModelBounds(new THREE.Box3());
    setPlanes([]);
    setActivePlaneIndex(-1);
    setShowPreview(false);
    setShowPieces(false);
    setCutPieces(null);
    setDrawingMode(false);
    setStatus('就绪');
    
    window.location.reload();
  }, []);

  const handleStatusChange = useCallback((newStatus) => {
    setStatus(newStatus);
  }, []);

  const handleProcessingChange = useCallback((processing) => {
    setIsProcessing(processing);
  }, []);

  const handleViewReset = useCallback(() => {
    setStatus('视图已重置');
  }, []);

  const handleViewFit = useCallback(() => {
    setStatus('视图已居中');
  }, []);

  useEffect(() => {
    if (window.__sceneApi) {
      refreshPlanesList();
    }
  }, [refreshPlanesList]);

  return (
    <div className="app">
      <div className="canvas-container">
        {!modelGroup && (
          <div className="empty-state">
            <div className="empty-state-icon">📦</div>
            <div className="empty-state-text">暂无模型</div>
            <div className="empty-state-subtext">请从右侧上传3D模型文件开始使用</div>
          </div>
        )}
        
        {modelGroup && (
          <Scene
            modelGroup={modelGroup}
            modelBounds={modelBounds}
            onCutComplete={handleCutComplete}
            showPreview={showPreview}
            cutPieces={cutPieces}
            showPieces={showPieces}
            onStatusChange={handleStatusChange}
            drawingMode={drawingMode}
            fillEnabled={fillEnabled}
            fillType={fillType}
            fillDensity={fillDensity}
            showAnimation={showAnimation}
            onAnimationStateChange={handleAnimationStateChange}
          />
        )}
        
        {modelGroup && (
          <>
            <div className="status-bar">
              {status}
              {drawingMode && <span style={{ color: '#e94560', marginLeft: 8 }}>✏️ 绘制模式</span>}
            </div>
            
            <div className="toolbar">
              <button className="toolbar-btn" onClick={handleViewFit}>
                🎯 居中
              </button>
              <button className="toolbar-btn" onClick={handleViewReset}>
                🔄 重置视图
              </button>
            </div>
          </>
        )}
        
        {isProcessing && (
          <div className="progress-overlay">
            <div className="spinner" />
            <div>{status}</div>
          </div>
        )}
      </div>
      
      <Sidebar
        modelInfo={modelInfo}
        onModelLoaded={handleModelLoaded}
        planes={planes}
        activePlaneIndex={activePlaneIndex}
        onAddPlane={handleAddPlane}
        onRemovePlane={handleRemovePlane}
        onSelectPlane={handleSelectPlane}
        onRotatePlane={handleRotatePlane}
        onFlipPlane={handleFlipPlane}
        onResetPlane={handleResetPlane}
        showPreview={showPreview}
        onShowPreviewChange={handleShowPreviewChange}
        showPieces={showPieces}
        cutPieces={cutPieces}
        onShowPiecesChange={handleShowPiecesChange}
        onPerformCut={handlePerformCut}
        onReset={handleReset}
        status={status}
        isProcessing={isProcessing}
        onStatusChange={handleStatusChange}
        onProcessingChange={handleProcessingChange}
        drawingMode={drawingMode}
        onDrawingModeChange={handleDrawingModeChange}
        fillEnabled={fillEnabled}
        onFillEnabledChange={handleFillEnabledChange}
        fillType={fillType}
        onFillTypeChange={handleFillTypeChange}
        fillDensity={fillDensity}
        onFillDensityChange={handleFillDensityChange}
        showAnimation={showAnimation}
        onShowAnimationChange={handleShowAnimationChange}
        animationState={animationState}
      />
    </div>
  );
}
