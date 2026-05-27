import { useState } from 'react';
import { 
  Settings, 
  Plus, 
  Trash2, 
  ArrowRight,
  Scissors,
  Merge,
  Search,
  FormatClear,
  ArrowUpFromLine,
  ArrowDownFromLine,
  Type,
  Replace,
  ChevronDown,
  Hash,
  Calendar,
  CheckSquare
} from 'lucide-react';
import { useAppStore } from '@/store';
import { generateTransformId } from '@/utils/transforms';
import type { TransformFunction, TransformType, FieldType } from '@/types';

const transformTypes: { type: TransformType; label: string; icon: React.ReactNode; description: string }[] = [
  { type: 'trim', label: '去除空格', icon: <FormatClear className="w-4 h-4" />, description: '去除首尾空白字符' },
  { type: 'uppercase', label: '转大写', icon: <ArrowUpFromLine className="w-4 h-4" />, description: '转换为大写字母' },
  { type: 'lowercase', label: '转小写', icon: <ArrowDownFromLine className="w-4 h-4" />, description: '转换为小写字母' },
  { type: 'concat', label: '拼接', icon: <Merge className="w-4 h-4" />, description: '拼接多个字段' },
  { type: 'split', label: '拆分', icon: <Scissors className="w-4 h-4" />, description: '按分隔符拆分字符串' },
  { type: 'lookup', label: '查表映射', icon: <Search className="w-4 h-4" />, description: '根据值查找映射' },
  { type: 'format', label: '格式化', icon: <Type className="w-4 h-4" />, description: '自定义格式模板' },
  { type: 'prefix', label: '添加前缀', icon: <ArrowRight className="w-4 h-4" />, description: '在值前添加文本' },
  { type: 'suffix', label: '添加后缀', icon: <ArrowRight className="w-4 h-4" />, description: '在值后添加文本' },
  { type: 'replace', label: '替换', icon: <Replace className="w-4 h-4" />, description: '替换指定文本' },
];

const outputTypeOptions: { value: FieldType | 'auto'; label: string; icon: React.ReactNode }[] = [
  { value: 'auto', label: '自动推断', icon: <Settings className="w-3.5 h-3.5" /> },
  { value: 'string', label: '字符串', icon: <Type className="w-3.5 h-3.5" /> },
  { value: 'number', label: '数字', icon: <Hash className="w-3.5 h-3.5" /> },
  { value: 'date', label: '日期', icon: <Calendar className="w-3.5 h-3.5" /> },
  { value: 'boolean', label: '布尔值', icon: <CheckSquare className="w-3.5 h-3.5" /> },
];

const typeColors: Record<string, string> = {
  auto: 'bg-slate-100 text-slate-600',
  string: 'bg-blue-100 text-blue-600',
  number: 'bg-emerald-100 text-emerald-600',
  date: 'bg-amber-100 text-amber-600',
  boolean: 'bg-purple-100 text-purple-600',
};

export default function TransformPanel() {
  const { 
    selectedMapping, 
    mappings, 
    sourceFields, 
    addTransform, 
    removeTransform,
    updateTransform,
    updateMapping,
    removeMapping
  } = useAppStore();
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [showTypeMenu, setShowTypeMenu] = useState(false);

  const currentMapping = mappings.find((m) => m.id === selectedMapping);
  const sourceField = sourceFields.find((f) => f.id === currentMapping?.sourceFieldId);

  const handleAddTransform = (type: TransformType) => {
    if (!selectedMapping) return;

    const baseTransform = {
      id: generateTransformId(),
      type,
    };

    let transform: TransformFunction;
    switch (type) {
      case 'concat':
        transform = { ...baseTransform, type: 'concat', separator: '', fields: [] };
        break;
      case 'split':
        transform = { ...baseTransform, type: 'split', separator: ',', index: 0 };
        break;
      case 'lookup':
        transform = { ...baseTransform, type: 'lookup', mapping: {}, defaultValue: '' };
        break;
      case 'format':
        transform = { ...baseTransform, type: 'format', pattern: '{value}' };
        break;
      case 'prefix':
        transform = { ...baseTransform, type: 'prefix', value: '' };
        break;
      case 'suffix':
        transform = { ...baseTransform, type: 'suffix', value: '' };
        break;
      case 'replace':
        transform = { ...baseTransform, type: 'replace', search: '', replace: '', global: true };
        break;
      case 'trim':
        transform = { ...baseTransform, type: 'trim' };
        break;
      case 'uppercase':
        transform = { ...baseTransform, type: 'uppercase' };
        break;
      case 'lowercase':
        transform = { ...baseTransform, type: 'lowercase' };
        break;
      default:
        return;
    }

    addTransform(selectedMapping, transform);
    setShowAddMenu(false);
  };

  const handleOutputTypeChange = (type: FieldType | null) => {
    if (!selectedMapping) return;
    updateMapping(selectedMapping, { outputType: type });
    setShowTypeMenu(false);
  };

  const currentOutputType = currentMapping?.outputType ?? 'auto';
  const currentOutputTypeInfo = outputTypeOptions.find(o => o.value === currentOutputType) || outputTypeOptions[0];

  const renderTransformConfig = (transform: TransformFunction) => {
    switch (transform.type) {
      case 'concat':
        return (
          <div className="space-y-2">
            <div>
              <label className="block text-xs text-slate-500 mb-1">分隔符</label>
              <input
                type="text"
                value={transform.separator}
                onChange={(e) => updateTransform(selectedMapping!, transform.id, { separator: e.target.value } as any)}
                className="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md"
                placeholder="如: 空格、逗号等"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">选择字段 (可多选)</label>
              <div className="flex flex-wrap gap-1">
                {sourceFields.map((field) => (
                  <label key={field.id} className="inline-flex items-center gap-1 px-2 py-1 bg-slate-100 rounded text-xs cursor-pointer hover:bg-slate-200">
                    <input
                      type="checkbox"
                      checked={transform.fields.includes(field.name)}
                      onChange={(e) => {
                        const newFields = e.target.checked
                          ? [...transform.fields, field.name]
                          : transform.fields.filter((f) => f !== field.name);
                        updateTransform(selectedMapping!, transform.id, { fields: newFields } as any);
                      }}
                      className="rounded"
                    />
                    {field.name}
                  </label>
                ))}
              </div>
            </div>
          </div>
        );

      case 'split':
        return (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-slate-500 mb-1">分隔符</label>
              <input
                type="text"
                value={transform.separator}
                onChange={(e) => updateTransform(selectedMapping!, transform.id, { separator: e.target.value } as any)}
                className="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">取第几个部分</label>
              <input
                type="number"
                min="0"
                value={transform.index}
                onChange={(e) => updateTransform(selectedMapping!, transform.id, { index: parseInt(e.target.value) || 0 } as any)}
                className="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md"
              />
            </div>
          </div>
        );

      case 'lookup':
        return (
          <div className="space-y-2">
            <div>
              <label className="block text-xs text-slate-500 mb-1">默认值</label>
              <input
                type="text"
                value={transform.defaultValue}
                onChange={(e) => updateTransform(selectedMapping!, transform.id, { defaultValue: e.target.value } as any)}
                className="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">映射表 (JSON格式)</label>
              <textarea
                value={JSON.stringify(transform.mapping, null, 2)}
                onChange={(e) => {
                  try {
                    const mapping = JSON.parse(e.target.value);
                    updateTransform(selectedMapping!, transform.id, { mapping } as any);
                  } catch {}
                }}
                className="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md font-mono h-20"
              />
            </div>
          </div>
        );

      case 'format':
        return (
          <div>
            <label className="block text-xs text-slate-500 mb-1">格式模板 (使用 {`{value}`} 表示当前值，{`{字段名}`} 表示其他字段)</label>
            <input
              type="text"
              value={transform.pattern}
              onChange={(e) => updateTransform(selectedMapping!, transform.id, { pattern: e.target.value } as any)}
              className="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md"
              placeholder="例如: ID-{value}"
            />
          </div>
        );

      case 'prefix':
      case 'suffix':
        return (
          <div>
            <label className="block text-xs text-slate-500 mb-1">{transform.type === 'prefix' ? '前缀内容' : '后缀内容'}</label>
            <input
              type="text"
              value={transform.value}
              onChange={(e) => updateTransform(selectedMapping!, transform.id, { value: e.target.value } as any)}
              className="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md"
            />
          </div>
        );

      case 'replace':
        return (
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-slate-500 mb-1">查找</label>
                <input
                  type="text"
                  value={transform.search}
                  onChange={(e) => updateTransform(selectedMapping!, transform.id, { search: e.target.value } as any)}
                  className="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">替换为</label>
                <input
                  type="text"
                  value={transform.replace}
                  onChange={(e) => updateTransform(selectedMapping!, transform.id, { replace: e.target.value } as any)}
                  className="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md"
                />
              </div>
            </div>
            <label className="inline-flex items-center gap-2 text-xs text-slate-600">
              <input
                type="checkbox"
                checked={transform.global}
                onChange={(e) => updateTransform(selectedMapping!, transform.id, { global: e.target.checked } as any)}
                className="rounded"
              />
              全部替换
            </label>
          </div>
        );

      default:
        return null;
    }
  };

  if (!currentMapping) {
    return (
      <div className="h-full flex items-center justify-center text-slate-400">
        <div className="text-center">
          <Settings className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-sm">点击连线以配置转换函数</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <div>
              <h3 className="font-semibold text-slate-800 text-sm">转换函数配置</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                源字段: <span className="font-medium text-blue-600">{sourceField?.name || '未选择'}</span>
              </p>
            </div>
            <div className="relative">
              <button
                onClick={() => setShowTypeMenu(!showTypeMenu)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${typeColors[currentOutputType]}`}
              >
                {currentOutputTypeInfo.icon}
                {currentOutputTypeInfo.label}
                <ChevronDown className="w-3 h-3" />
              </button>
              {showTypeMenu && (
                <div className="absolute left-0 top-full mt-1 w-36 bg-white border border-slate-200 rounded-lg shadow-lg z-10 overflow-hidden">
                  {outputTypeOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => handleOutputTypeChange(option.value === 'auto' ? null : option.value as FieldType)}
                      className={`w-full flex items-center gap-2 px-3 py-2 hover:bg-slate-50 text-left ${
                        currentOutputType === option.value ? 'bg-blue-50' : ''
                      }`}
                    >
                      <span className={typeColors[option.value] + ' p-1 rounded'}>
                        {option.icon}
                      </span>
                      <span className="text-xs font-medium text-slate-700">{option.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <button
              onClick={() => setShowAddMenu(!showAddMenu)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600 transition-colors"
            >
              <Plus className="w-4 h-4" />
              添加转换
              <ChevronDown className="w-3 h-3" />
            </button>
            {showAddMenu && (
              <div className="absolute right-0 top-full mt-1 w-56 bg-white border border-slate-200 rounded-lg shadow-lg z-10 overflow-hidden">
                {transformTypes.map((t) => (
                  <button
                    key={t.type}
                    onClick={() => handleAddTransform(t.type)}
                    className="w-full flex items-center gap-3 px-3 py-2 hover:bg-slate-50 text-left"
                  >
                    <span className="p-1.5 bg-slate-100 rounded text-slate-600">
                      {t.icon}
                    </span>
                    <div>
                      <div className="text-sm font-medium text-slate-800">{t.label}</div>
                      <div className="text-xs text-slate-500">{t.description}</div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={() => removeMapping(currentMapping.id)}
            className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {currentMapping.transforms.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-400">
            <p className="text-sm">点击"添加转换"按钮添加数据转换规则</p>
          </div>
        ) : (
          <div className="space-y-3">
            {currentMapping.transforms.map((transform, index) => {
              const transformInfo = transformTypes.find((t) => t.type === transform.type);
              return (
                <div key={transform.id} className="border border-slate-200 rounded-lg overflow-hidden">
                  <div className="flex items-center justify-between px-3 py-2 bg-slate-50 border-b border-slate-200">
                    <div className="flex items-center gap-2">
                      <span className="flex items-center justify-center w-6 h-6 bg-blue-500 text-white text-xs font-bold rounded">
                        {index + 1}
                      </span>
                      <span className="p-1 bg-white border border-slate-200 rounded text-slate-600">
                        {transformInfo?.icon}
                      </span>
                      <span className="text-sm font-medium text-slate-700">
                        {transformInfo?.label}
                      </span>
                    </div>
                    <button
                      onClick={() => removeTransform(currentMapping.id, transform.id)}
                      className="p-1 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="p-3">
                    {renderTransformConfig(transform)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
