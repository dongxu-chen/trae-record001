import { useState, useCallback, useMemo } from 'react';
import * as THREE from 'three';
import { ModelLoader } from '../utils/ModelLoader.js';
import { ModelExporter } from '../utils/ModelExporter.js';
import { CsgCutter } from '../utils/CsgCutter.js';

const modelLoader = new ModelLoader();
const modelExporter = new ModelExporter();
const csgCutter = new CsgCutter();

export default function Sidebar({
  modelInfo,
  onModelLoaded,
  planes,
  activePlaneIndex,
  onAddPlane,
  onRemovePlane,
  onSelectPlane,
  onRotatePlane,
  onFlipPlane,
  onResetPlane,
  showPreview,
  onShowPreviewChange,
  showPieces,
  cutPieces,
  onShowPiecesChange,
  onPerformCut,
  onReset,
  status,
  isProcessing,
  onStatusChange,
  onProcessingChange,
  drawingMode,
  onDrawingModeChange,
  fillEnabled,
  onFillEnabledChange,
  fillType,
  onFillTypeChange,
  fillDensity,
  onFillDensityChange,
  showAnimation,
  onShowAnimationChange,
  animationState
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [planeType, setPlaneType] = useState('y');
  const [showPlanes, setShowPlanes] = useState(true);
  const [exportFormat, setExportFormat] = useState('glb');
  const [hierarchicalCut, setHierarchicalCut] = useState(false);
  const [decimationRatio, setDecimationRatio] = useState(25);
  const [normalizeExport, setNormalizeExport] = useState(true);
  const [animSpeed, setAnimSpeed] = useState(1.0);

  const handleFileUpload = useCallback(async (file) => {
    if (!file) return;
    
    try {
      onProcessingChange(true);
      onStatusChange('正在加载模型...');
      
      const result = await modelLoader.loadFromLocalFile(file);
      
      onModelLoaded(result);
      onStatusChange('模型加载成功');
      
      setTimeout(() => {
        onStatusChange('就绪');
      }, 2000);
    } catch (error) {
      console.error('模型加载失败:', error);
      onStatusChange(`加载失败: ${error.message}`);
    } finally {
      onProcessingChange(false);
    }
  }, [onModelLoaded, onProcessingChange, onStatusChange]);

  const handleFileInput = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  }, [handleFileUpload]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  }, [handleFileUpload]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleAddPlane = useCallback(() => {
    let normal;
    switch (planeType) {
      case 'x':
        normal = new THREE.Vector3(1, 0, 0);
        break;
      case 'y':
        normal = new THREE.Vector3(0, 1, 0);
        break;
      case 'z':
        normal = new THREE.Vector3(0, 0, 1);
        break;
      case 'diagonal':
        normal = new THREE.Vector3(1, 1, 1).normalize();
        break;
      default:
        normal = new THREE.Vector3(0, 1, 0);
    }
    
    if (onAddPlane) {
      onAddPlane(normal);
    }
  }, [planeType, onAddPlane]);

  const handlePerformCut = useCallback(async () => {
    if (!window.__sceneApi) return;
    
    try {
      onProcessingChange(true);
      
      const cutOptions = {
        hierarchical: hierarchicalCut,
        decimationRatio: decimationRatio / 100,
        onProgress: (current, total, phase) => {
          if (phase === 'coarse') {
            onStatusChange(`粗切割中... (${current}/${total})`);
          } else if (phase === 'fine') {
            onStatusChange(`细分割中... (${current}/${total})`);
          } else if (phase === 'coarse-start') {
            onStatusChange('第一阶段: 粗切割分析...');
          } else if (phase === 'fine-start') {
            onStatusChange('第二阶段: 精细分割...');
          } else {
            onStatusChange(`切割中... (${current}/${total})`);
          }
        }
      };

      if (hierarchicalCut) {
        onStatusChange('分层切割模式: 粗切割 → 细分割');
      } else {
        onStatusChange('正在执行切割...');
      }
      
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const pieces = window.__sceneApi.performCut(cutOptions);
      
      if (pieces && pieces.length > 0) {
        onStatusChange(`切割完成，生成 ${pieces.length} 个切块`);
        if (onPerformCut) {
          onPerformCut(pieces);
        }
      } else {
        onStatusChange('切割失败，请检查切割平面设置');
      }
    } catch (error) {
      console.error('切割失败:', error);
      onStatusChange(`切割失败: ${error.message}`);
    } finally {
      onProcessingChange(false);
    }
  }, [onPerformCut, onProcessingChange, onStatusChange, hierarchicalCut, decimationRatio]);

  const handleCurveCut = useCallback(async () => {
    if (!window.__sceneApi) return;
    
    try {
      onProcessingChange(true);
      onStatusChange('正在执行曲线切割...');
      
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const pieces = window.__sceneApi.performCurveCut();
      
      if (pieces && pieces.length > 0) {
        onStatusChange(`曲线切割完成，生成 ${pieces.length} 个切块`);
        if (onPerformCut) {
          onPerformCut(pieces);
        }
      } else {
        onStatusChange('曲线切割失败，请确保绘制了足够的点');
      }
    } catch (error) {
      console.error('曲线切割失败:', error);
      onStatusChange(`曲线切割失败: ${error.message}`);
    } finally {
      onProcessingChange(false);
    }
  }, [onPerformCut, onProcessingChange, onStatusChange]);

  const handlePlayAnimation = useCallback(() => {
    if (!window.__sceneApi || !cutPieces || cutPieces.length === 0) return;
    
    window.__sceneApi.playCutAnimation(cutPieces, {
      duration: 2.0,
      speed: animSpeed,
      separationDistance: 1.5
    });
    
    if (onShowAnimationChange) onShowAnimationChange(true);
  }, [cutPieces, animSpeed, onShowAnimationChange]);

  const handleStopAnimation = useCallback(() => {
    if (!window.__sceneApi) return;
    window.__sceneApi.stopCutAnimation();
    if (onShowAnimationChange) onShowAnimationChange(false);
  }, [onShowAnimationChange]);

  const handleExportPiece = useCallback(async (piece, index) => {
    try {
      onProcessingChange(true);
      onStatusChange(`正在导出切块 ${index + 1}...`);
      
      const baseName = piece.name || `piece_${index + 1}`;
      const origPrepare = modelExporter.prepareMeshForExport.bind(modelExporter);
      modelExporter.prepareMeshForExport = (mesh) => origPrepare(mesh, normalizeExport);
      
      try {
        switch (exportFormat) {
          case 'glb':
            await modelExporter.exportToGLB(piece, baseName);
            break;
          case 'gltf':
            await modelExporter.exportToGLTF(piece, baseName);
            break;
          case 'obj':
            await modelExporter.exportToOBJ(piece, baseName);
            break;
          case 'stl':
            await modelExporter.exportToSTL(piece, baseName);
            break;
        }
      } finally {
        modelExporter.prepareMeshForExport = origPrepare;
      }
      
      onStatusChange(`切块 ${index + 1} 导出成功`);
    } catch (error) {
      console.error('导出失败:', error);
      onStatusChange(`导出失败: ${error.message}`);
    } finally {
      onProcessingChange(false);
    }
  }, [exportFormat, onProcessingChange, onStatusChange, normalizeExport]);

  const handleExportAll = useCallback(async () => {
    if (!cutPieces || cutPieces.length === 0) return;
    
    try {
      onProcessingChange(true);
      onStatusChange('正在导出所有切块...');
      
      const origPrepare = modelExporter.prepareMeshForExport.bind(modelExporter);
      modelExporter.prepareMeshForExport = (mesh) => origPrepare(mesh, normalizeExport);
      
      try {
        await modelExporter.exportAllPieces(cutPieces, 'piece', exportFormat);
      } finally {
        modelExporter.prepareMeshForExport = origPrepare;
      }
      
      onStatusChange(`成功导出 ${cutPieces.length} 个切块`);
    } catch (error) {
      console.error('导出失败:', error);
      onStatusChange(`导出失败: ${error.message}`);
    } finally {
      onProcessingChange(false);
    }
  }, [cutPieces, exportFormat, onProcessingChange, onStatusChange, normalizeExport]);

  const handleExportCombined = useCallback(async () => {
    if (!cutPieces || cutPieces.length === 0) return;
    
    try {
      onProcessingChange(true);
      onStatusChange('正在导出合并模型...');
      
      const origPrepare = modelExporter.prepareMeshForExport.bind(modelExporter);
      modelExporter.prepareMeshForExport = (mesh) => origPrepare(mesh, normalizeExport);
      
      try {
        await modelExporter.exportMultipleToGLB(cutPieces, 'cut_model');
      } finally {
        modelExporter.prepareMeshForExport = origPrepare;
      }
      
      onStatusChange('合并模型导出成功');
    } catch (error) {
      console.error('导出失败:', error);
      onStatusChange(`导出失败: ${error.message}`);
    } finally {
      onProcessingChange(false);
    }
  }, [cutPieces, onProcessingChange, onStatusChange, normalizeExport]);

  const handleTogglePlanesVisibility = useCallback((visible) => {
    setShowPlanes(visible);
    if (window.__sceneApi) {
      window.__sceneApi.setAllPlanesVisibility(visible);
    }
  }, []);

  const activePlane = useMemo(() => {
    return planes[activePlaneIndex] || null;
  }, [planes, activePlaneIndex]);

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const getPieceStats = (piece) => {
    return csgCutter.getMeshStats(piece);
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>✂️ 3D模型切割工具</h1>
      </div>
      
      <div className="sidebar-content">
        <div className="section">
          <h3 className="section-title">模型上传</h3>
          
          <div
            className={`upload-area ${isDragging ? 'dragging' : ''}`}
            onClick={() => document.getElementById('fileInput')?.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <div className="upload-icon">📁</div>
            <div className="upload-text">
              {isDragging ? '释放以上传' : '点击或拖拽上传'}
            </div>
            <div className="upload-subtext">
              支持 GLB / GLTF / OBJ / STL
            </div>
          </div>
          
          <input
            id="fileInput"
            type="file"
            accept=".glb,.gltf,.obj,.stl"
            style={{ display: 'none' }}
            onChange={handleFileInput}
          />
          
          {modelInfo && (
            <div className="model-info" style={{ marginTop: 12 }}>
              <div>文件名: <span>{modelInfo.uploadInfo?.originalName}</span></div>
              <div>大小: <span>{formatFileSize(modelInfo.uploadInfo?.size || 0)}</span></div>
              <div>网格数: <span>{modelInfo.stats?.meshCount}</span></div>
              <div>顶点数: <span>{modelInfo.stats?.vertexCount?.toLocaleString()}</span></div>
              <div>三角面: <span>{modelInfo.stats?.faceCount?.toLocaleString()}</span></div>
            </div>
          )}
        </div>
        
        <div className="divider" />
        
        <div className="section">
          <h3 className="section-title">✏️ 曲线切割</h3>
          
          <label className="toggle">
            <input
              type="checkbox"
              checked={drawingMode}
              onChange={(e) => onDrawingModeChange?.(e.target.checked)}
              disabled={!modelInfo || isProcessing}
            />
            曲线绘制模式
          </label>
          
          {drawingMode && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 12, color: '#888', marginBottom: 8 }}>
                在模型表面点击添加控制点，绘制切割曲线。至少需要3个点。
              </div>
              <div className="control-row">
                <button
                  className="btn btn-secondary"
                  onClick={() => window.__sceneApi?.clearCurveDrawing()}
                  disabled={isProcessing}
                >
                  清除曲线
                </button>
                <button
                  className="btn btn-primary"
                  onClick={handleCurveCut}
                  disabled={isProcessing}
                >
                  🔪 曲线切割
                </button>
              </div>
            </div>
          )}
        </div>
        
        <div className="divider" />
        
        <div className="section">
          <h3 className="section-title">切割平面</h3>
          
          <div className="control-group">
            <label className="control-label">平面方向</label>
            <select
              value={planeType}
              onChange={(e) => setPlaneType(e.target.value)}
              disabled={!modelInfo || isProcessing}
            >
              <option value="y">Y轴平面 (水平)</option>
              <option value="x">X轴平面 (垂直)</option>
              <option value="z">Z轴平面 (深度)</option>
              <option value="diagonal">对角平面</option>
            </select>
          </div>
          
          <button
            className="btn btn-primary"
            onClick={handleAddPlane}
            disabled={!modelInfo || isProcessing}
          >
            + 添加切割平面
          </button>
          
          <label className="toggle">
            <input
              type="checkbox"
              checked={showPlanes}
              onChange={(e) => handleTogglePlanesVisibility(e.target.checked)}
            />
            显示切割平面
          </label>
          
          <label className="toggle">
            <input
              type="checkbox"
              checked={showPreview}
              onChange={(e) => onShowPreviewChange?.(e.target.checked)}
              disabled={!modelInfo || planes.length === 0 || isProcessing}
            />
            实时预览切割
          </label>
          
          {planes.length > 0 && (
            <div className="plane-list" style={{ marginTop: 12 }}>
              {planes.map((plane, index) => (
                <div
                  key={index}
                  className={`plane-item ${index === activePlaneIndex ? 'active' : ''}`}
                  onClick={() => onSelectPlane?.(index)}
                >
                  <div className="plane-info">
                    <div
                      className="plane-color"
                      style={{ backgroundColor: `#${plane.color.toString(16).padStart(6, '0')}` }}
                    />
                    <span className="plane-name">{plane.name}</span>
                  </div>
                  <div className="plane-actions">
                    <button
                      className="icon-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        onFlipPlane?.(index);
                      }}
                      title="翻转平面"
                    >
                      🔄
                    </button>
                    <button
                      className="icon-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemovePlane?.(index);
                      }}
                      title="删除平面"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {activePlane && (
            <div style={{ marginTop: 16 }}>
              <div className="section-title" style={{ fontSize: 12, marginBottom: 8 }}>
                选中平面操作
              </div>
              <div className="control-row">
                <button
                  className="btn btn-secondary"
                  onClick={() => onRotatePlane?.(activePlaneIndex, new THREE.Vector3(1, 0, 0), Math.PI / 12)}
                  disabled={isProcessing}
                >
                  绕X轴+
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => onRotatePlane?.(activePlaneIndex, new THREE.Vector3(0, 1, 0), Math.PI / 12)}
                  disabled={isProcessing}
                >
                  绕Y轴+
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => onRotatePlane?.(activePlaneIndex, new THREE.Vector3(0, 0, 1), Math.PI / 12)}
                  disabled={isProcessing}
                >
                  绕Z轴+
                </button>
              </div>
              <div className="control-row">
                <button
                  className="btn btn-secondary"
                  onClick={() => onResetPlane?.(activePlaneIndex)}
                  disabled={isProcessing}
                >
                  重置平面
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => onFlipPlane?.(activePlaneIndex)}
                  disabled={isProcessing}
                >
                  翻转方向
                </button>
              </div>
            </div>
          )}
        </div>
        
        <div className="divider" />
        
        <div className="section">
          <h3 className="section-title">🧱 切割填充</h3>
          
          <label className="toggle">
            <input
              type="checkbox"
              checked={fillEnabled}
              onChange={(e) => onFillEnabledChange?.(e.target.checked)}
              disabled={!modelInfo || isProcessing}
            />
            启用截面填充
          </label>
          
          {fillEnabled && (
            <div style={{ marginLeft: 28 }}>
              <div className="control-group">
                <label className="control-label">填充类型</label>
                <select
                  value={fillType}
                  onChange={(e) => onFillTypeChange?.(e.target.value)}
                  disabled={isProcessing}
                >
                  <option value="grid">网格填充</option>
                  <option value="honeycomb">蜂窝填充</option>
                  <option value="lattice">晶格填充</option>
                  <option value="concentric">同心圆填充</option>
                  <option value="triangle">三角填充</option>
                </select>
              </div>
              
              <div className="control-group">
                <label className="control-label">
                  填充密度: {fillDensity}
                </label>
                <input
                  type="range"
                  min="2"
                  max="15"
                  value={fillDensity}
                  onChange={(e) => onFillDensityChange?.(Number(e.target.value))}
                  disabled={isProcessing}
                />
              </div>
            </div>
          )}
        </div>
        
        <div className="divider" />
        
        <div className="section">
          <h3 className="section-title">执行切割</h3>
          
          <label className="toggle">
            <input
              type="checkbox"
              checked={hierarchicalCut}
              onChange={(e) => setHierarchicalCut(e.target.checked)}
              disabled={!modelInfo || isProcessing}
            />
            分层切割模式
          </label>
          
          {hierarchicalCut && (
            <div className="control-group" style={{ marginLeft: 28 }}>
              <label className="control-label">
                粗切割采样率: {decimationRatio}%
              </label>
              <input
                type="range"
                min="5"
                max="80"
                value={decimationRatio}
                onChange={(e) => setDecimationRatio(Number(e.target.value))}
                disabled={!modelInfo || isProcessing}
              />
              <div style={{ fontSize: 11, color: '#888', marginTop: 6 }}>
                采样率越低，粗切割越快但精度略低。推荐 25%
              </div>
            </div>
          )}
          
          <button
            className="btn btn-primary"
            onClick={handlePerformCut}
            disabled={!modelInfo || planes.length === 0 || isProcessing}
          >
            {hierarchicalCut ? '🔧 分层切割' : '⚡ 执行切割'}
          </button>
          
          <label className="toggle">
            <input
              type="checkbox"
              checked={showPieces}
              onChange={(e) => onShowPiecesChange?.(e.target.checked)}
              disabled={!cutPieces || cutPieces.length === 0}
            />
            显示切割结果
          </label>
          
          <button
            className="btn btn-danger"
            onClick={onReset}
            disabled={isProcessing}
          >
            🔄 重置
          </button>
        </div>
        
        {cutPieces && cutPieces.length > 0 && (
          <>
            <div className="divider" />
            
            <div className="section">
              <h3 className="section-title">🎬 切割动画</h3>
              
              <div style={{ fontSize: 12, color: '#888', marginBottom: 8 }}>
                播放切割过程动画，展示模型分离效果
              </div>
              
              <div className="control-group">
                <label className="control-label">
                  动画速度: {animSpeed.toFixed(1)}x
                </label>
                <input
                  type="range"
                  min="0.2"
                  max="3.0"
                  step="0.1"
                  value={animSpeed}
                  onChange={(e) => setAnimSpeed(Number(e.target.value))}
                  disabled={isProcessing}
                />
              </div>
              
              <div className="control-row">
                <button
                  className="btn btn-secondary"
                  onClick={handlePlayAnimation}
                  disabled={isProcessing}
                >
                  ▶ 播放动画
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={handleStopAnimation}
                  disabled={isProcessing}
                >
                  ⏹ 停止
                </button>
              </div>
              
              {animationState && animationState !== 'idle' && (
                <div style={{ fontSize: 12, color: '#e94560', marginTop: 6 }}>
                  {animationState === 'completed' ? '✅ 动画完成' : 
                   animationState === 'stopped' ? '动画已停止' :
                   `动画进度: ${animationState.replace('playing:', '')}%`}
                </div>
              )}
            </div>
            
            <div className="divider" />
            
            <div className="section">
              <h3 className="section-title">切块导出 ({cutPieces.length}个)</h3>
              
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={normalizeExport}
                  onChange={(e) => setNormalizeExport(e.target.checked)}
                />
                坐标归一化 (居中+缩放)
              </label>
              
              {normalizeExport && (
                <div style={{ fontSize: 11, color: '#888', marginLeft: 28, marginBottom: 8 }}>
                  导出时将模型中心移至原点，并缩放至单位尺寸
                </div>
              )}
              
              <div className="control-group">
                <label className="control-label">导出格式</label>
                <select
                  value={exportFormat}
                  onChange={(e) => setExportFormat(e.target.value)}
                >
                  <option value="glb">GLB (二进制)</option>
                  <option value="gltf">GLTF (JSON)</option>
                  <option value="obj">OBJ</option>
                  <option value="stl">STL</option>
                </select>
              </div>
              
              <div className="control-row">
                <button
                  className="btn btn-secondary"
                  onClick={handleExportAll}
                  disabled={isProcessing}
                >
                  全部导出
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={handleExportCombined}
                  disabled={isProcessing}
                >
                  合并导出
                </button>
              </div>
              
              <div className="cut-pieces" style={{ marginTop: 12 }}>
                {cutPieces.map((piece, index) => {
                  const stats = getPieceStats(piece);
                  return (
                    <div key={index} className="cut-piece-item">
                      <div className="piece-info">
                        <div className="piece-name">{piece.name}</div>
                        {stats && (
                          <div className="piece-stats">
                            {stats.vertexCount.toLocaleString()} 顶点 · {stats.faceCount.toLocaleString()} 面
                          </div>
                        )}
                      </div>
                      <button
                        className="icon-btn"
                        onClick={() => handleExportPiece(piece, index)}
                        disabled={isProcessing}
                        title="导出此切块"
                      >
                        💾
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
