import React, { useState } from 'react';
import { useCanvasStore } from '../store/canvasStore';
import {
  SHAPE_NAMES, SHAPE_COLORS,
  SHAPE3D_NAMES, SHAPE3D_COLORS,
  RELATION_NAMES, RELATION_ICONS,
} from '../../shared/types';
import type { Shape, Shape3D, ShapeRelation } from '../../shared/types';

export const PropertyPanel: React.FC = () => {
  const {
    shapes,
    shapes3D,
    relations,
    selectedShapeId,
    selectedShape3DId,
    selectedRelationIds,
    viewMode,
    selectShape,
    selectShape3D,
    toggleRelationSelection,
    updateShapePoints,
    setShapes,
    calibration,
    setCalibration,
    resetCalibration,
    getRealValue,
    getUnitLabel,
    exportToDXF,
    setToolMode,
  } = useCanvasStore();
  const [scale, setScale] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [activeTab, setActiveTab] = useState<'2d' | '3d' | 'relations' | 'export'>('2d');
  const [dxfOptions, setDxfOptions] = useState({
    separateLayers: true,
    includeConstructionLines: true,
  });

  const selectedShape = shapes.find(s => s.id === selectedShapeId);
  const selectedShape3D = shapes3D.find(s => s.id === selectedShape3DId);
  const unitLabel = getUnitLabel();
  const isCalibrated = calibration.enabled;

  const formatValue = (pixelValue: number, isArea = false, isVolume = false): string => {
    if (isCalibrated) {
      let realVal: number;
      if (isVolume) {
        realVal = getRealValue(Math.cbrt(pixelValue)) ** 3;
      } else if (isArea) {
        realVal = getRealValue(Math.sqrt(pixelValue)) ** 2;
      } else {
        realVal = getRealValue(pixelValue);
      }
      return realVal.toFixed(2);
    }
    return pixelValue.toFixed(1);
  };

  const handleDeleteShape = (shapeId: string) => {
    setShapes(shapes.filter(s => s.id !== shapeId));
    if (selectedShapeId === shapeId) {
      selectShape(null);
    }
  };

  const handleColorChange = (shapeId: string, color: string) => {
    const updatedShapes = shapes.map(s =>
      s.id === shapeId ? { ...s, color } : s
    );
    setShapes(updatedShapes);
  };

  const handleTransform = (shape: Shape, newScale: number, newRotation: number) => {
    const center = shape.center;
    const cos = Math.cos(newRotation - (shape.rotation || 0));
    const sin = Math.sin(newRotation - (shape.rotation || 0));
    const scaleFactor = newScale / scale;

    const newPoints = shape.points.map(p => {
      const dx = p.x - center.x;
      const dy = p.y - center.y;

      const scaledX = dx * scaleFactor;
      const scaledY = dy * scaleFactor;

      const rotatedX = scaledX * cos - scaledY * sin;
      const rotatedY = scaledX * sin + scaledY * cos;

      return {
        x: rotatedX + center.x,
        y: rotatedY + center.y,
      };
    });

    updateShapePoints(shape.id, newPoints);
    setScale(newScale);
    setRotation(newRotation);
  };

  React.useEffect(() => {
    if (selectedShape) {
      setScale(1);
      setRotation(selectedShape.rotation || 0);
    }
  }, [selectedShapeId, selectedShape?.rotation]);

  const getShapeIcon = (type: string) => {
    switch (type) {
      case 'rectangle': return '▢';
      case 'circle': return '○';
      case 'triangle': return '△';
      case 'polygon': return '⬡';
      default: return '◇';
    }
  };

  const getShape3DIcon = (type: string) => {
    switch (type) {
      case 'cube': return '🧊';
      case 'sphere': return '🔮';
      case 'cylinder': return '🛢️';
      case 'cone': return '📐';
      case 'pyramid': return '🔺';
      case 'prism': return '⬚';
      default: return '🎲';
    }
  };

  const getRelatedShapes = (relation: ShapeRelation) => {
    const shapeA = shapes.find(s => s.id === relation.shapeAId);
    const shapeB = relation.shapeBId ? shapes.find(s => s.id === relation.shapeBId) : null;
    return { shapeA, shapeB };
  };

  const tabs = [
    { id: '2d', label: '2D形状', icon: '📐' },
    { id: '3d', label: '3D模型', icon: '🎲' },
    { id: 'relations', label: '关系', icon: '🔗' },
    { id: 'export', label: '导出', icon: '📤' },
  ];

  return (
    <div className="w-80 h-full bg-slate-800 border-l border-slate-700 flex flex-col overflow-hidden">
      <div className="p-4 border-b border-slate-700">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <span>📊</span>
          属性面板
        </h2>
      </div>

      <div className="flex border-b border-slate-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex-1 px-2 py-2 text-xs font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-slate-700 text-white border-b-2 border-cyan-500'
                : 'text-slate-400 hover:bg-slate-700/50'
            }`}
          >
            <span className="mr-1">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === '2d' && (
          <div className="p-4 space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider flex items-center gap-2">
                <span>📏</span>
                标定设置
              </h3>

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <label className="text-slate-400 text-sm w-16">参考长度</label>
                  <input
                    type="number"
                    min="0.001"
                    step="0.1"
                    value={calibration.realLength || ''}
                    onChange={(e) => setCalibration({ realLength: parseFloat(e.target.value) || 0 })}
                    className="flex-1 px-2 py-1.5 bg-slate-700 text-white rounded text-sm border border-slate-600 focus:border-cyan-500 focus:outline-none"
                    placeholder="输入实际长度"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <label className="text-slate-400 text-sm w-16">单位</label>
                  <select
                    value={calibration.unit}
                    onChange={(e) => setCalibration({ unit: e.target.value })}
                    className="flex-1 px-2 py-1.5 bg-slate-700 text-white rounded text-sm border border-slate-600 focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="px">px (像素)</option>
                    <option value="mm">mm (毫米)</option>
                    <option value="cm">cm (厘米)</option>
                    <option value="m">m (米)</option>
                    <option value="in">in (英寸)</option>
                    <option value="ft">ft (英尺)</option>
                  </select>
                </div>

                {calibration.pixelLength > 1 && (
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <div className="text-slate-400 text-xs mb-1">像素长度</div>
                    <div className="text-white font-mono text-sm">{calibration.pixelLength.toFixed(1)} px</div>
                  </div>
                )}

                {isCalibrated && (
                  <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
                    <div className="text-amber-300 text-sm font-medium mb-1">✓ 标定已启用</div>
                    <div className="text-amber-200/70 text-xs">
                      1 {calibration.unit} = {calibration.pixelLength.toFixed(1)} px
                      <br />
                      比例: {(calibration.realLength / calibration.pixelLength).toFixed(4)} {calibration.unit}/px
                    </div>
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    onClick={() => setToolMode('calibrate')}
                    className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-1 ${
                      useCanvasStore.getState().toolMode === 'calibrate'
                        ? 'bg-amber-500 text-black'
                        : 'bg-amber-600/80 text-white hover:bg-amber-500'
                    }`}
                  >
                    <span>📏</span>
                    标定
                  </button>
                  <button
                    onClick={resetCalibration}
                    className="px-3 py-2 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 text-sm transition-all"
                  >
                    重置
                  </button>
                </div>
              </div>
            </div>

            <div className="border-t border-slate-700 pt-4">
              <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">
                形状列表 ({shapes.length})
              </h3>

              {shapes.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <div className="text-4xl mb-2">📐</div>
                  <p className="text-sm">暂无识别的形状</p>
                  <p className="text-xs mt-1">手绘形状或上传图像后点击识别</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {shapes.map((shape, index) => (
                    <div
                      key={shape.id}
                      onClick={() => selectShape(shape.id)}
                      className={`p-3 rounded-lg cursor-pointer transition-all ${
                        selectedShapeId === shape.id
                          ? 'bg-cyan-500/20 border border-cyan-500/50'
                          : 'bg-slate-700/50 border border-transparent hover:bg-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div
                            className="w-8 h-8 rounded flex items-center justify-center text-lg"
                            style={{ backgroundColor: `${shape.color || SHAPE_COLORS[shape.type]}30` }}
                          >
                            <span style={{ color: shape.color || SHAPE_COLORS[shape.type] }}>
                              {getShapeIcon(shape.type)}
                            </span>
                          </div>
                          <div>
                            <div className="text-white font-medium text-sm">
                              {SHAPE_NAMES[shape.type]} #{index + 1}
                              {shape.corrected && <span className="text-cyan-400 ml-1 text-xs">✓</span>}
                              {shape.shape3DId && <span className="text-violet-400 ml-1 text-xs">3D</span>}
                            </div>
                            <div className="text-slate-400 text-xs">
                              置信度: {(shape.confidence * 100).toFixed(0)}%
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteShape(shape.id);
                          }}
                          className="p-1 text-slate-400 hover:text-red-400 transition-colors"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {selectedShape && (
              <div className="border-t border-slate-700 pt-4 space-y-4">
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                  形状属性
                </h3>

                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <div className="text-slate-400 text-xs mb-1">面积</div>
                    <div className="text-white font-bold text-lg">
                      {formatValue(selectedShape.area, true)}
                      <span className="text-xs text-slate-400 ml-1">{unitLabel}²</span>
                    </div>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <div className="text-slate-400 text-xs mb-1">周长</div>
                    <div className="text-white font-bold text-lg">
                      {formatValue(selectedShape.perimeter)}
                      <span className="text-xs text-slate-400 ml-1">{unitLabel}</span>
                    </div>
                  </div>
                </div>

                {selectedShape.radius && (
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <div className="text-slate-400 text-xs mb-1">半径</div>
                    <div className="text-white font-bold text-lg">
                      {formatValue(selectedShape.radius)}
                      <span className="text-xs text-slate-400 ml-1">{unitLabel}</span>
                    </div>
                  </div>
                )}

                {isCalibrated && (
                  <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-xs text-amber-200/80">
                    📏 显示值已转换为 {calibration.unit}
                  </div>
                )}

                <div className="space-y-3">
                  <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                    样式
                  </h4>
                  <div className="flex gap-2 flex-wrap">
                    {Object.values(SHAPE_COLORS).map((color) => (
                      <button
                        key={color}
                        onClick={() => handleColorChange(selectedShape.id, color)}
                        className={`w-8 h-8 rounded-lg border-2 transition-all ${
                          selectedShape.color === color ? 'border-white scale-110' : 'border-transparent'
                        }`}
                        style={{ backgroundColor: color }}
                      />
                    ))}
                    <input
                      type="color"
                      value={selectedShape.color || SHAPE_COLORS[selectedShape.type]}
                      onChange={(e) => handleColorChange(selectedShape.id, e.target.value)}
                      className="w-8 h-8 rounded-lg cursor-pointer bg-transparent border-2 border-slate-600"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === '3d' && (
          <div className="p-4 space-y-4">
            <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">
              3D模型列表 ({shapes3D.length})
            </h3>

            {shapes3D.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <div className="text-4xl mb-2">🎲</div>
                <p className="text-sm">暂无3D模型</p>
                <p className="text-xs mt-1">点击「推断3D」按钮从2D形状生成</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {shapes3D.map((shape3d, index) => (
                  <div
                    key={shape3d.id}
                    onClick={() => selectShape3D(shape3d.id)}
                    className={`p-3 rounded-lg cursor-pointer transition-all ${
                      selectedShape3DId === shape3d.id
                        ? 'bg-violet-500/20 border border-violet-500/50'
                        : 'bg-slate-700/50 border border-transparent hover:bg-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-8 h-8 rounded flex items-center justify-center text-lg"
                        style={{ backgroundColor: `${shape3d.color || SHAPE3D_COLORS[shape3d.type]}30` }}
                      >
                        <span style={{ color: shape3d.color || SHAPE3D_COLORS[shape3d.type] }}>
                          {getShape3DIcon(shape3d.type)}
                        </span>
                      </div>
                      <div>
                        <div className="text-white font-medium text-sm">
                          {SHAPE3D_NAMES[shape3d.type]} #{index + 1}
                        </div>
                        <div className="text-slate-400 text-xs">
                          置信度: {(shape3d.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {selectedShape3D && (
              <div className="border-t border-slate-700 pt-4 space-y-4">
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                  3D属性
                </h3>

                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <div className="text-slate-400 text-xs mb-1">宽度</div>
                    <div className="text-white font-bold">
                      {formatValue(selectedShape3D.size.width)}
                      <span className="text-xs text-slate-400 ml-1">{unitLabel}</span>
                    </div>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <div className="text-slate-400 text-xs mb-1">高度</div>
                    <div className="text-white font-bold">
                      {formatValue(selectedShape3D.size.height)}
                      <span className="text-xs text-slate-400 ml-1">{unitLabel}</span>
                    </div>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <div className="text-slate-400 text-xs mb-1">深度</div>
                    <div className="text-white font-bold">
                      {formatValue(selectedShape3D.size.depth)}
                      <span className="text-xs text-slate-400 ml-1">{unitLabel}</span>
                    </div>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <div className="text-slate-400 text-xs mb-1">顶点数</div>
                    <div className="text-white font-bold">
                      {selectedShape3D.vertices.length}
                    </div>
                  </div>
                </div>

                {selectedShape3D.volume && (
                  <div className="bg-violet-700/50 rounded-lg p-3">
                    <div className="text-slate-300 text-xs mb-1">体积</div>
                    <div className="text-white font-bold text-lg">
                      {formatValue(selectedShape3D.volume, false, true)}
                      <span className="text-xs text-slate-400 ml-1">{unitLabel}³</span>
                    </div>
                  </div>
                )}

                {selectedShape3D.surfaceArea && (
                  <div className="bg-violet-700/50 rounded-lg p-3">
                    <div className="text-slate-300 text-xs mb-1">表面积</div>
                    <div className="text-white font-bold text-lg">
                      {formatValue(selectedShape3D.surfaceArea, true)}
                      <span className="text-xs text-slate-400 ml-1">{unitLabel}²</span>
                    </div>
                  </div>
                )}

                <div className="bg-slate-700/50 rounded-lg p-3">
                  <div className="text-slate-400 text-xs mb-2">中心坐标</div>
                  <div className="text-white text-sm font-mono space-y-1">
                    <div>X: {formatValue(selectedShape3D.center.x)}</div>
                    <div>Y: {formatValue(selectedShape3D.center.y)}</div>
                    <div>Z: {formatValue(selectedShape3D.center.z)}</div>
                  </div>
                </div>

                <div className="bg-slate-700/50 rounded-lg p-3">
                  <div className="text-slate-400 text-xs mb-2">旋转角度</div>
                  <div className="text-white text-sm font-mono space-y-1">
                    <div>X: {(selectedShape3D.rotation.x * 180 / Math.PI).toFixed(1)}°</div>
                    <div>Y: {(selectedShape3D.rotation.y * 180 / Math.PI).toFixed(1)}°</div>
                    <div>Z: {(selectedShape3D.rotation.z * 180 / Math.PI).toFixed(1)}°</div>
                  </div>
                </div>

                <div className="bg-slate-700/50 rounded-lg p-3 text-xs text-slate-400">
                  <div className="flex justify-between">
                    <span>来源2D形状:</span>
                    <span className="text-cyan-400">
                      {shapes.find(s => s.id === selectedShape3D.sourceShapeId)
                        ? SHAPE_NAMES[shapes.find(s => s.id === selectedShape3D.sourceShapeId)!.type]
                        : '未知'}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'relations' && (
          <div className="p-4 space-y-4">
            <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">
              关系列表 ({relations.length})
            </h3>

            {relations.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <div className="text-4xl mb-2">🔗</div>
                <p className="text-sm">暂无检测到的关系</p>
                <p className="text-xs mt-1">点击「关系检测」按钮分析形状关系</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {relations.map((rel) => {
                  const { shapeA, shapeB } = getRelatedShapes(rel);
                  const isSelected = selectedRelationIds.has(rel.id);
                  return (
                    <div
                      key={rel.id}
                      onClick={() => toggleRelationSelection(rel.id)}
                      className={`p-3 rounded-lg cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-emerald-500/20 border border-emerald-500/50'
                          : 'bg-slate-700/50 border border-transparent hover:bg-slate-700'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded flex items-center justify-center text-lg">
                          {RELATION_ICONS[rel.type]}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-white font-medium text-sm truncate">
                            {RELATION_NAMES[rel.type]}
                          </div>
                          <div className="text-slate-400 text-xs truncate">
                            {shapeA && shapeB
                              ? `${SHAPE_NAMES[shapeA.type]} → ${SHAPE_NAMES[shapeB.type]}`
                              : shapeA
                                ? SHAPE_NAMES[shapeA.type]
                                : '多个形状'}
                            {' · '}置信度: {(rel.confidence * 100).toFixed(0)}%
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {selectedRelationIds.size > 0 && (
              <div className="border-t border-slate-700 pt-4">
                <h4 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">
                  已选关系 ({selectedRelationIds.size})
                </h4>
                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3 text-xs text-emerald-200">
                  <p>已高亮显示 {selectedRelationIds.size} 个关系</p>
                  <p className="mt-1 text-emerald-300/70">关系线已在画布中加粗显示</p>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'export' && (
          <div className="p-4 space-y-4">
            <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">
              DXF导出选项
            </h3>

            <div className="space-y-3">
              <div className="bg-slate-700/50 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-white text-sm font-medium">分层导出</div>
                    <div className="text-slate-400 text-xs">按形状类型分到不同图层</div>
                  </div>
                  <button
                    onClick={() => setDxfOptions({ ...dxfOptions, separateLayers: !dxfOptions.separateLayers })}
                    className={`w-12 h-6 rounded-full transition-all ${
                      dxfOptions.separateLayers ? 'bg-cyan-500' : 'bg-slate-600'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-full bg-white transition-transform ${
                        dxfOptions.separateLayers ? 'translate-x-6' : 'translate-x-0.5'
                      }`}
                    />
                  </button>
                </div>
              </div>

              <div className="bg-slate-700/50 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-white text-sm font-medium">构造线</div>
                    <div className="text-slate-400 text-xs">包含构造线和标注</div>
                  </div>
                  <button
                    onClick={() => setDxfOptions({ ...dxfOptions, includeConstructionLines: !dxfOptions.includeConstructionLines })}
                    className={`w-12 h-6 rounded-full transition-all ${
                      dxfOptions.includeConstructionLines ? 'bg-cyan-500' : 'bg-slate-600'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-full bg-white transition-transform ${
                        dxfOptions.includeConstructionLines ? 'translate-x-6' : 'translate-x-0.5'
                      }`}
                    />
                  </button>
                </div>
              </div>

              <div className="bg-slate-700/50 rounded-lg p-3">
                <div className="text-slate-400 text-xs mb-2">导出单位</div>
                <div className="text-white font-mono text-sm">
                  {calibration.enabled ? calibration.unit : 'px'}
                  {calibration.enabled && (
                    <span className="text-slate-400 ml-2">
                      (比例: 1:{(calibration.pixelLength / calibration.realLength).toFixed(2)})
                    </span>
                  )}
                </div>
              </div>

              <div className="bg-slate-700/50 rounded-lg p-3">
                <div className="text-slate-400 text-xs mb-2">导出内容</div>
                <div className="text-white text-sm space-y-1">
                  <div className="flex justify-between">
                    <span>2D形状:</span>
                    <span className="text-cyan-400">{shapes.length} 个</span>
                  </div>
                  <div className="flex justify-between">
                    <span>3D模型:</span>
                    <span className="text-violet-400">{shapes3D.length} 个</span>
                  </div>
                </div>
              </div>
            </div>

            <button
              onClick={() => exportToDXF(dxfOptions)}
              disabled={shapes.length === 0 && shapes3D.length === 0}
              className="w-full py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-500 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium shadow-lg shadow-orange-500/30"
            >
              <span>📐</span>
              导出 DXF 文件
            </button>

            <div className="bg-slate-700/50 rounded-lg p-3 text-xs text-slate-400 space-y-2">
              <p className="font-medium text-slate-300">💡 DXF导出说明:</p>
              <ul className="space-y-1 list-disc list-inside">
                <li>兼容 AutoCAD R12 及以上版本</li>
                <li>支持多图层，按形状类型分类</li>
                <li>自动应用标定比例转换</li>
                <li>3D模型导出为2D等轴测投影</li>
              </ul>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-slate-700 bg-slate-800/90">
        <div className="text-xs text-slate-500 space-y-1">
          <p>💡 「编辑」模式拖拽顶点修改形状</p>
          <p>💡 「推断3D」从2D生成3D模型</p>
          <p>💡 「关系检测」分析形状逻辑关系</p>
        </div>
      </div>
    </div>
  );
};
