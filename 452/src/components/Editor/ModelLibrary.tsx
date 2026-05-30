import { useState } from 'react';
import { Box, Circle, Upload, ChevronDown, ChevronRight } from 'lucide-react';
import { useSceneStore } from '../../store/useSceneStore';
import type { ObjectType } from '../../types/scene';

interface ModelItem {
  type: ObjectType;
  name: string;
  icon: React.ReactNode;
  description: string;
}

const basicModels: ModelItem[] = [
  { type: 'box', name: '立方体', icon: <Box size={24} />, description: '基础立方体几何体' },
  { type: 'sphere', name: '球体', icon: <Circle size={24} />, description: '高精度球体几何体' },
];

export function ModelLibrary() {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isGLTFExpanded, setIsGLTFExpanded] = useState(true);
  const { addObject } = useSceneStore();

  const handleDragStart = (e: React.DragEvent, type: ObjectType) => {
    e.dataTransfer.setData('modelType', type);
    e.dataTransfer.effectAllowed = 'copy';
  };

  const handleClick = (type: ObjectType) => {
    addObject(type);
  };

  const handleGLTFUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      addObject('gltf');
    }
  };

  return (
    <div className="w-64 bg-gray-900 border-r border-gray-700 flex flex-col h-full">
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Box size={20} className="text-cyan-400" />
          模型库
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        <div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full flex items-center gap-2 text-gray-300 hover:text-white transition-colors mb-2"
          >
            {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            <span className="text-sm font-medium">基础几何体</span>
          </button>
          
          {isExpanded && (
            <div className="grid grid-cols-2 gap-2">
              {basicModels.map((model) => (
                <div
                  key={model.type}
                  draggable
                  onDragStart={(e) => handleDragStart(e, model.type)}
                  onClick={() => handleClick(model.type)}
                  className="bg-gray-800 hover:bg-gray-700 border border-gray-600 hover:border-cyan-500 rounded-lg p-3 cursor-grab active:cursor-grabbing transition-all group"
                >
                  <div className="flex flex-col items-center gap-2">
                    <div className="text-cyan-400 group-hover:text-cyan-300 transition-colors">
                      {model.icon}
                    </div>
                    <span className="text-xs text-gray-300">{model.name}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <button
            onClick={() => setIsGLTFExpanded(!isGLTFExpanded)}
            className="w-full flex items-center gap-2 text-gray-300 hover:text-white transition-colors mb-2"
          >
            {isGLTFExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            <span className="text-sm font-medium">自定义模型</span>
          </button>
          
          {isGLTFExpanded && (
            <div className="space-y-2">
              <label className="flex flex-col items-center justify-center w-full h-24 bg-gray-800 hover:bg-gray-700 border-2 border-dashed border-gray-600 hover:border-cyan-500 rounded-lg cursor-pointer transition-all group">
                <Upload size={24} className="text-gray-400 group-hover:text-cyan-400 mb-2" />
                <span className="text-xs text-gray-400 group-hover:text-gray-300">
                  上传 glTF/GLB 文件
                </span>
                <input
                  type="file"
                  accept=".gltf,.glb"
                  onChange={handleGLTFUpload}
                  className="hidden"
                />
              </label>
              
              <div className="text-xs text-gray-500 text-center">
                支持 .gltf 和 .glb 格式
              </div>
            </div>
          )}
        </div>

        <div className="pt-4 border-t border-gray-700">
          <p className="text-xs text-gray-500 mb-2">提示</p>
          <ul className="text-xs text-gray-400 space-y-1">
            <li>• 点击模型快速添加到场景</li>
            <li>• 拖拽模型到指定位置</li>
            <li>• 选中后可调整属性</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
