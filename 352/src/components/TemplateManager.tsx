import { useState, useEffect } from 'react';
import { 
  Save, 
  FolderOpen, 
  Trash2, 
  X, 
  Plus, 
  Tag, 
  Clock,
  FileText
} from 'lucide-react';
import { useAppStore } from '@/store';

interface TemplateManagerProps {
  onClose: () => void;
}

export default function TemplateManager({ onClose }: TemplateManagerProps) {
  const { 
    templates, 
    saveAsTemplate, 
    loadTemplate, 
    deleteTemplate, 
    refreshTemplates,
    targetFields,
    mappings
  } = useAppStore();
  
  const [showSaveForm, setShowSaveForm] = useState(false);
  const [templateName, setTemplateName] = useState('');
  const [templateDesc, setTemplateDesc] = useState('');
  const [templateCategory, setTemplateCategory] = useState('通用');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    refreshTemplates();
  }, [refreshTemplates]);

  const canSave = targetFields.length > 0 && mappings.filter(m => m.sourceFieldId).length > 0;

  const handleSave = async () => {
    if (!templateName.trim()) return;
    setIsSaving(true);
    try {
      await saveAsTemplate(templateName, templateDesc, templateCategory);
      setTemplateName('');
      setTemplateDesc('');
      setShowSaveForm(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleLoad = (templateId: number) => {
    loadTemplate(templateId);
    onClose();
  };

  const categories = [...new Set(templates.map(t => t.category))];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <FolderOpen className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-800">映射模板库</h2>
              <p className="text-sm text-slate-500">保存和复用常用映射配置</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-auto p-6">
          {!showSaveForm ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-slate-700">已保存的模板</h3>
                <button
                  onClick={() => setShowSaveForm(true)}
                  disabled={!canSave}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-500 text-white text-sm rounded-lg hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Save className="w-4 h-4" />
                  保存为模板
                </button>
              </div>

              {!canSave && (
                <p className="text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded-lg">
                  需要先配置目标字段和映射关系才能保存模板
                </p>
              )}

              {templates.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>暂无保存的模板</p>
                  <p className="text-sm mt-1">配置映射后点击"保存为模板"即可保存</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {categories.map(category => (
                    <div key={category} className="space-y-2">
                      <div className="flex items-center gap-2 text-sm font-medium text-slate-600">
                        <Tag className="w-4 h-4" />
                        {category}
                      </div>
                      <div className="grid gap-2">
                        {templates
                          .filter(t => t.category === category)
                          .map(template => (
                            <div
                              key={template.id}
                              className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-200 hover:border-purple-300 transition-colors"
                            >
                              <div className="flex-1">
                                <div className="font-medium text-slate-800">{template.name}</div>
                                {template.description && (
                                  <p className="text-sm text-slate-500 mt-0.5">{template.description}</p>
                                )}
                                <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                                  <span className="flex items-center gap-1">
                                    <FileText className="w-3 h-3" />
                                    {template.targetFields.length} 个目标字段
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <Save className="w-3 h-3" />
                                    {template.fieldMappings.length} 个映射
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {new Date(template.updatedAt).toLocaleDateString('zh-CN')}
                                  </span>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => handleLoad(template.id!)}
                                  className="px-3 py-1.5 text-sm text-purple-600 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors"
                                >
                                  加载
                                </button>
                                <button
                                  onClick={() => deleteTemplate(template.id!)}
                                  className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <h3 className="font-medium text-slate-700">保存为模板</h3>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">模板名称 *</label>
                <input
                  type="text"
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  placeholder="输入模板名称"
                  className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">分类</label>
                <div className="flex flex-wrap gap-2">
                  {['通用', '用户数据', '订单数据', '产品数据', '其他'].map(cat => (
                    <button
                      key={cat}
                      onClick={() => setTemplateCategory(cat)}
                      className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                        templateCategory === cat
                          ? 'bg-purple-500 text-white'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">描述</label>
                <textarea
                  value={templateDesc}
                  onChange={(e) => setTemplateDesc(e.target.value)}
                  placeholder="输入模板描述（可选）"
                  rows={3}
                  className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => setShowSaveForm(false)}
                  className="flex-1 px-4 py-2 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleSave}
                  disabled={!templateName.trim() || isSaving}
                  className="flex-1 px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                >
                  {isSaving ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      保存中...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      保存模板
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
