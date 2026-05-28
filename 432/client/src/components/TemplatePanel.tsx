import React, { useState } from 'react';
import { X, Plus, Trash2, Bookmark, Zap } from 'lucide-react';
import { usePdfContext } from '../contexts/PdfContext';
import { AnnotationType } from '../types';
import { generateId } from '../utils/coordinateUtils';

interface TemplatePanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const ANNOTATION_TYPES: { value: AnnotationType; label: string }[] = [
  { value: 'highlight', label: '高亮' },
  { value: 'underline', label: '下划线' },
  { value: 'strikeout', label: '删除线' },
  { value: 'comment', label: '批注' },
  { value: 'rectangle', label: '矩形' },
  { value: 'circle', label: '圆形' },
  { value: 'arrow', label: '箭头' },
];

const TEMPLATE_COLORS = [
  '#FFEB3B',
  '#4CAF50',
  '#F44336',
  '#2196F3',
  '#FF9800',
  '#9C27B0',
  '#00BCD4',
];

const TemplatePanel: React.FC<TemplatePanelProps> = ({ isOpen, onClose }) => {
  const { state, dispatch, applyTemplate } = usePdfContext();
  const { templates } = state;
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTemplate, setNewTemplate] = useState({
    name: '',
    type: 'highlight' as AnnotationType,
    color: '#FFEB3B',
    content: '',
    shortcut: '',
  });

  if (!isOpen) return null;

  const handleAddTemplate = () => {
    if (!newTemplate.name.trim()) return;

    const template = {
      id: generateId(),
      ...newTemplate,
      isGlobal: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    dispatch({ type: 'ADD_TEMPLATE', payload: template });
    setNewTemplate({
      name: '',
      type: 'highlight',
      color: '#FFEB3B',
      content: '',
      shortcut: '',
    });
    setShowAddForm(false);
  };

  const handleDeleteTemplate = (templateId: string) => {
    if (confirm('确定要删除此模板吗？')) {
      dispatch({ type: 'DELETE_TEMPLATE', payload: templateId });
    }
  };

  const handleApplyTemplate = (template: any) => {
    applyTemplate(template);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl w-full max-w-lg max-h-[80vh] overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Bookmark className="text-primary-600" size={24} />
            标注模板
          </h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-4 overflow-auto max-h-[60vh]">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-sm text-gray-600">点击模板快速应用到当前页面</span>
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="flex items-center gap-1 px-3 py-1.5 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700"
            >
              <Plus size={16} />
              新建模板
            </button>
          </div>

          {showAddForm && (
            <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <h4 className="text-sm font-medium text-gray-700 mb-3">新建模板</h4>
              
              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">模板名称</label>
                  <input
                    type="text"
                    value={newTemplate.name}
                    onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="例如：已审阅"
                  />
                </div>

                <div>
                  <label className="block text-xs text-gray-500 mb-1">标注类型</label>
                  <select
                    value={newTemplate.type}
                    onChange={(e) => setNewTemplate({ ...newTemplate, type: e.target.value as AnnotationType })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    {ANNOTATION_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-gray-500 mb-1">颜色</label>
                  <div className="flex gap-2">
                    {TEMPLATE_COLORS.map((color) => (
                      <button
                        key={color}
                        onClick={() => setNewTemplate({ ...newTemplate, color })}
                        className={`w-8 h-8 rounded-full border-2 ${newTemplate.color === color ? 'border-primary-600 ring-2 ring-primary-300' : 'border-white'} shadow-sm`}
                        style={{ backgroundColor: color }}
                      />
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs text-gray-500 mb-1">内容（批注类型）</label>
                  <input
                    type="text"
                    value={newTemplate.content}
                    onChange={(e) => setNewTemplate({ ...newTemplate, content: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="批注内容（可选）"
                  />
                </div>

                <div>
                  <label className="block text-xs text-gray-500 mb-1">快捷键（可选）</label>
                  <input
                    type="text"
                    value={newTemplate.shortcut}
                    onChange={(e) => setNewTemplate({ ...newTemplate, shortcut: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="例如：Ctrl+1"
                  />
                </div>
              </div>

              <div className="mt-4 flex gap-2">
                <button
                  onClick={handleAddTemplate}
                  className="flex-1 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700"
                >
                  保存模板
                </button>
                <button
                  onClick={() => setShowAddForm(false)}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-300"
                >
                  取消
                </button>
              </div>
            </div>
          )}

          <div className="space-y-2">
            {templates.map((template) => (
              <div
                key={template.id}
                className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-4 h-4 rounded-full border border-gray-300"
                        style={{ backgroundColor: template.color }}
                      />
                      <span className="font-medium text-gray-800">{template.name}</span>
                      {template.isGlobal && (
                        <Zap size={14} className="text-yellow-500" />
                      )}
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      {ANNOTATION_TYPES.find(t => t.value === template.type)?.label}
                      {template.content && ` • ${template.content.substring(0, 20)}`}
                      {template.shortcut && ` • ${template.shortcut}`}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => handleApplyTemplate(template)}
                      className="px-3 py-1 bg-primary-600 text-white rounded text-xs hover:bg-primary-700"
                    >
                      应用
                    </button>
                    {!template.isGlobal && (
                      <button
                        onClick={() => handleDeleteTemplate(template.id)}
                        className="p-1 text-red-500 hover:bg-red-50 rounded"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {templates.length === 0 && (
            <div className="text-center py-8 text-gray-400">
              <Bookmark size={48} className="mx-auto mb-2 opacity-50" />
              <p>暂无模板，点击上方按钮新建</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TemplatePanel;
