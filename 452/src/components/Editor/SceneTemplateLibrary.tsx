import { useState } from 'react';
import { LayoutTemplate, ChevronDown, ChevronRight } from 'lucide-react';
import { useSceneStore } from '../../store/useSceneStore';
import { sceneTemplates } from '../../data/sceneTemplates';
import type { SceneTemplate } from '../../types/scene';

export function SceneTemplateLibrary() {
  const [isExpanded, setIsExpanded] = useState(true);
  const [activeCategory, setActiveCategory] = useState<'indoor' | 'outdoor'>('indoor');
  const { applyTemplate } = useSceneStore();

  const handleApplyTemplate = (template: SceneTemplate) => {
    applyTemplate(template.data);
  };

  const filteredTemplates = sceneTemplates.filter(
    (t) => t.category === activeCategory
  );

  return (
    <div className="w-64 bg-gray-900 border-r border-gray-700 flex flex-col h-full">
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <LayoutTemplate size={20} className="text-cyan-400" />
          场景模板
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        <div className="flex gap-1 bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setActiveCategory('indoor')}
            className={`flex-1 py-1.5 text-xs rounded-md transition-all ${
              activeCategory === 'indoor'
                ? 'bg-cyan-500 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            🏠 室内
          </button>
          <button
            onClick={() => setActiveCategory('outdoor')}
            className={`flex-1 py-1.5 text-xs rounded-md transition-all ${
              activeCategory === 'outdoor'
                ? 'bg-cyan-500 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            🌳 室外
          </button>
        </div>

        <div className="space-y-2">
          {filteredTemplates.map((template) => (
            <button
              key={template.id}
              onClick={() => handleApplyTemplate(template)}
              className="w-full bg-gray-800 hover:bg-gray-700 border border-gray-600 hover:border-cyan-500 rounded-lg p-3 text-left transition-all group"
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl">{template.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-200 group-hover:text-cyan-300 transition-colors">
                    {template.name}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {template.description}
                  </div>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-xs text-gray-600">
                      {template.data.objects.length} 物体
                    </span>
                    <span className="text-xs text-gray-600">
                      {template.data.lights.length} 光源
                    </span>
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>

        <div className="pt-4 border-t border-gray-700">
          <p className="text-xs text-gray-500 mb-2">说明</p>
          <ul className="text-xs text-gray-400 space-y-1">
            <li>• 点击模板一键应用到场景</li>
            <li>• 模板会替换当前场景内容</li>
            <li>• 应用后可自由编辑修改</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
