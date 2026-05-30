import { useState } from 'react';
import {
  Eye,
  Move,
  RotateCw,
  Maximize2,
  Download,
  Upload,
  Play,
  Trash2,
  ChevronDown,
  Cuboid,
  FileBox,
  Atom,
} from 'lucide-react';
import { useSceneStore } from '../../store/useSceneStore';
import { exportSceneAsJSON } from '../../utils/sceneExporter';
import type { ViewMode, TransformMode } from '../../types/scene';

interface ViewModeOption {
  id: ViewMode;
  label: string;
}

interface TransformModeOption {
  id: TransformMode;
  label: string;
  icon: React.ReactNode;
}

const viewModes: ViewModeOption[] = [
  { id: 'perspective', label: '透视图' },
  { id: 'front', label: '正视图' },
  { id: 'top', label: '顶视图' },
  { id: 'side', label: '侧视图' },
];

const transformModes: TransformModeOption[] = [
  { id: 'translate', label: '移动', icon: <Move size={16} /> },
  { id: 'rotate', label: '旋转', icon: <RotateCw size={16} /> },
  { id: 'scale', label: '缩放', icon: <Maximize2 size={16} /> },
];

export function Toolbar() {
  const {
    viewMode,
    transformMode,
    setViewMode,
    setTransformMode,
    isPreviewMode,
    togglePreviewMode,
    exportScene,
    importScene,
    clearScene,
    objects,
    showNormalMaps,
    setShowNormalMaps,
    physicsEnabled,
    setPhysicsEnabled,
  } = useSceneStore();

  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showViewMenu, setShowViewMenu] = useState(false);
  const [exporting, setExporting] = useState(false);

  const handleExportJSON = () => {
    const data = exportScene();
    exportSceneAsJSON(data);
    setShowExportMenu(false);
  };

  const handleExportGLTF = async () => {
    setExporting(true);
    setShowExportMenu(false);
    try {
      const { exportSceneAsGLTF } = await import('../../utils/sceneExporter');
      const threeScene = (window as any).__threeScene;
      if (threeScene) {
        await exportSceneAsGLTF(threeScene);
      }
    } catch (err) {
      console.error('glTF export failed:', err);
    } finally {
      setExporting(false);
    }
  };

  const handleImportJSON = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const data = JSON.parse(event.target?.result as string);
          importScene(data);
        } catch (error) {
          console.error('Failed to import scene:', error);
        }
      };
      reader.readAsText(file);
    }
  };

  const handlePreviewRender = () => {
    const canvas = document.querySelector('canvas');
    if (canvas) {
      const link = document.createElement('a');
      link.download = `render-${Date.now()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    }
  };

  return (
    <div className="h-14 bg-gray-900 border-b border-gray-700 flex items-center justify-between px-4">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 pr-4 border-r border-gray-700">
          <Cuboid size={24} className="text-cyan-400" />
          <span className="text-white font-semibold">3D 场景编辑器</span>
        </div>

        <div className="flex items-center gap-1 px-3">
          {transformModes.map((mode) => (
            <button
              key={mode.id}
              onClick={() => setTransformMode(mode.id)}
              className={`p-2 rounded transition-all ${
                transformMode === mode.id
                  ? 'bg-cyan-500 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
              }`}
              title={mode.label}
            >
              {mode.icon}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1 px-3 border-l border-gray-700">
          <button
            onClick={() => setShowNormalMaps(!showNormalMaps)}
            className={`px-3 py-2 rounded text-sm transition-all ${
              showNormalMaps
                ? 'bg-cyan-500 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
            }`}
            title="法线贴图显示开关"
          >
            法线贴图
          </button>
        </div>

        <div className="flex items-center gap-1 px-3 border-l border-gray-700">
          <button
            onClick={() => setPhysicsEnabled(!physicsEnabled)}
            className={`flex items-center gap-2 px-3 py-2 rounded text-sm transition-all ${
              physicsEnabled
                ? 'bg-orange-500 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
            }`}
            title="物理模拟开关"
          >
            <Atom size={16} />
            物理模拟
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="relative">
          <button
            onClick={() => setShowViewMenu(!showViewMenu)}
            className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white rounded transition-all"
          >
            <Eye size={16} />
            <span className="text-sm">
              {viewModes.find((v) => v.id === viewMode)?.label}
            </span>
            <ChevronDown size={14} />
          </button>

          {showViewMenu && (
            <div className="absolute top-full left-0 mt-1 bg-gray-800 border border-gray-700 rounded shadow-lg overflow-hidden z-50">
              {viewModes.map((mode) => (
                <button
                  key={mode.id}
                  onClick={() => {
                    setViewMode(mode.id);
                    setShowViewMenu(false);
                  }}
                  className={`w-full px-4 py-2 text-left text-sm transition-colors ${
                    viewMode === mode.id
                      ? 'bg-cyan-500 text-white'
                      : 'text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  {mode.label}
                </button>
              ))}
            </div>
          )}
        </div>

        <button
          onClick={togglePreviewMode}
          className={`flex items-center gap-2 px-3 py-2 rounded transition-all ${
            isPreviewMode
              ? 'bg-green-500 text-white'
              : 'bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white'
          }`}
        >
          <Play size={16} />
          <span className="text-sm">预览</span>
        </button>

        <button
          onClick={handlePreviewRender}
          className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white rounded transition-all"
        >
          <Eye size={16} />
          <span className="text-sm">渲染</span>
        </button>

        <div className="relative">
          <button
            onClick={() => setShowExportMenu(!showExportMenu)}
            className="flex items-center gap-2 px-3 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded transition-all"
            disabled={exporting}
          >
            <Download size={16} />
            <span className="text-sm">{exporting ? '导出中...' : '导出'}</span>
            <ChevronDown size={14} />
          </button>

          {showExportMenu && (
            <div className="absolute top-full right-0 mt-1 bg-gray-800 border border-gray-700 rounded shadow-lg overflow-hidden z-50 min-w-[160px]">
              <button
                onClick={handleExportJSON}
                className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 transition-colors flex items-center gap-2"
              >
                <Download size={14} />
                导出 JSON
              </button>
              <button
                onClick={handleExportGLTF}
                className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 transition-colors flex items-center gap-2"
              >
                <FileBox size={14} />
                导出 glTF (内联纹理)
              </button>
              <label className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 transition-colors flex items-center gap-2 cursor-pointer">
                <Upload size={14} />
                导入 JSON
                <input
                  type="file"
                  accept=".json"
                  onChange={handleImportJSON}
                  className="hidden"
                />
              </label>
            </div>
          )}
        </div>

        <button
          onClick={clearScene}
          disabled={objects.length === 0}
          className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed text-gray-300 hover:text-white rounded transition-all"
        >
          <Trash2 size={16} />
          <span className="text-sm">清空</span>
        </button>
      </div>
    </div>
  );
}
