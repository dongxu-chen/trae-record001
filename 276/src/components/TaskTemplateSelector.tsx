import { useState } from 'react';
import { TaskTemplate, Task, Priority } from '@/types';
import { defaultTemplates, createTaskFromTemplate } from '@/utils/taskTemplates';
import { X, Plus, ClipboardList } from 'lucide-react';

interface TaskTemplateSelectorProps {
  boardId: string;
  onSelect: (task: Task) => void;
  onClose: () => void;
}

const priorityColors: Record<Priority, string> = {
  'low': 'bg-gray-100 text-gray-600',
  'medium': 'bg-blue-100 text-blue-600',
  'high': 'bg-orange-100 text-orange-600',
  'urgent': 'bg-red-100 text-red-600',
};

const priorityLabels: Record<Priority, string> = {
  'low': '低',
  'medium': '中',
  'high': '高',
  'urgent': '紧急',
};

const TaskTemplateSelector = ({ boardId, onSelect, onClose }: TaskTemplateSelectorProps) => {
  const [templates] = useState<TaskTemplate[]>(defaultTemplates);
  const [selectedTemplate, setSelectedTemplate] = useState<TaskTemplate | null>(null);

  const handleUseTemplate = () => {
    if (!selectedTemplate) return;
    const newTask = createTaskFromTemplate(selectedTemplate, boardId);
    onSelect(newTask);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <ClipboardList className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">选择任务模板</h2>
              <p className="text-sm text-gray-500">快速创建标准化任务</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {templates.map(template => (
              <div
                key={template._id}
                onClick={() => setSelectedTemplate(template)}
                className={`p-4 border-2 rounded-xl cursor-pointer transition-all ${
                  selectedTemplate?._id === template._id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-gray-900">{template.name}</h3>
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${priorityColors[template.priority]}`}>
                    {priorityLabels[template.priority]}
                  </span>
                </div>
                <p className="text-sm text-gray-500 mb-3">{template.description}</p>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span className="bg-gray-100 px-2 py-1 rounded">{template.dueDays} 天截止</span>
                  <span className="bg-gray-100 px-2 py-1 rounded">{template.subTasks.length} 个子任务</span>
                </div>
                {selectedTemplate?._id === template._id && (
                  <div className="mt-3 pt-3 border-t border-blue-200">
                    <div className="text-xs text-gray-600">
                      <span className="font-medium">标签：</span>
                      {template.tags.map((tag, i) => (
                        <span key={i} className="ml-1 bg-blue-200 text-blue-700 px-1.5 py-0.5 rounded">
                          {tag}
                        </span>
                      ))}
                    </div>
                    {template.subTasks.length > 0 && (
                      <div className="mt-2 text-xs text-gray-600">
                        <span className="font-medium">子任务：</span>
                        <ul className="mt-1 space-y-0.5">
                          {template.subTasks.slice(0, 3).map((st, i) => (
                            <li key={i} className="flex items-center gap-1">
                              <span className="w-1.5 h-1.5 bg-blue-400 rounded-full"></span>
                              {st}
                            </li>
                          ))}
                          {template.subTasks.length > 3 && (
                            <li className="text-gray-400">+{template.subTasks.length - 3} 更多...</li>
                          )}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between p-6 border-t border-gray-200">
          <div className="text-sm text-gray-500">
            {selectedTemplate ? (
              <span>已选择：<strong className="text-gray-900">{selectedTemplate.name}</strong></span>
            ) : (
              <span>请选择一个模板</span>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleUseTemplate}
              disabled={!selectedTemplate}
              className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
                selectedTemplate
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              <Plus className="w-4 h-4" />
              使用模板
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TaskTemplateSelector;
