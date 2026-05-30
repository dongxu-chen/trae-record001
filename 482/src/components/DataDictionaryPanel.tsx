import { BookOpen, Tag, Hash, Type, ToggleLeft, List, Link2, Clock } from 'lucide-react';
import { useLineageStore } from '@/stores/useLineageStore';
import { FieldDictionary, EnumValue } from '@/types';

const EnumValueRow = ({ enumVal }: { enumVal: EnumValue }) => (
  <div className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
    <code className="text-xs font-mono bg-gray-100 px-2 py-0.5 rounded">{enumVal.value}</code>
    <span className="text-sm text-gray-700 flex-1">{enumVal.label}</span>
    {enumVal.frequency !== undefined && (
      <div className="flex items-center gap-2">
        <div className="w-20 h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-primary-400 rounded-full"
            style={{ width: `${enumVal.frequency}%` }}
          />
        </div>
        <span className="text-xs text-gray-500 w-8">{enumVal.frequency}%</span>
      </div>
    )}
  </div>
);

export const DataDictionaryPanel = () => {
  const { fieldDictionary, selectedField, loadFieldDictionary } = useLineageStore();

  const handleLoad = () => {
    if (selectedField) {
      loadFieldDictionary(selectedField.id);
    }
  };

  if (!selectedField && !fieldDictionary) {
    return (
      <div className="p-4 text-center text-gray-500">
        <BookOpen className="w-10 h-10 mx-auto mb-2 text-gray-300" />
        <p className="text-sm">请在图谱中选择一个字段节点</p>
        <button
          onClick={handleLoad}
          className="mt-3 btn-primary text-sm"
          disabled={!selectedField}
        >
          加载数据字典
        </button>
      </div>
    );
  }

  if (!fieldDictionary) {
    return (
      <div className="p-4 text-center">
        <BookOpen className="w-10 h-10 mx-auto mb-2 text-gray-300" />
        <p className="text-sm text-gray-500 mb-3">点击下方按钮加载字段数据字典</p>
        <button onClick={handleLoad} className="btn-primary text-sm" disabled={!selectedField}>
          加载数据字典
        </button>
      </div>
    );
  }

  const dict = fieldDictionary;

  return (
    <div className="space-y-5">
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
            <BookOpen className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h4 className="font-semibold text-gray-900 font-mono">{dict.fieldName}</h4>
            <p className="text-xs text-gray-500">{dict.database}.{dict.table}</p>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between py-1.5">
            <span className="text-xs text-gray-500 flex items-center gap-1"><Type className="w-3 h-3" /> 数据类型</span>
            <code className="text-xs font-mono bg-white/60 px-2 py-0.5 rounded">{dict.dataType}</code>
          </div>
          <div className="flex items-center justify-between py-1.5">
            <span className="text-xs text-gray-500 flex items-center gap-1"><ToggleLeft className="w-3 h-3" /> 是否可空</span>
            <span className={`text-xs px-2 py-0.5 rounded ${dict.nullable ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'}`}>
              {dict.nullable ? '可为空' : '非空'}
            </span>
          </div>
          {dict.defaultValue && (
            <div className="flex items-center justify-between py-1.5">
              <span className="text-xs text-gray-500 flex items-center gap-1"><Hash className="w-3 h-3" /> 默认值</span>
              <code className="text-xs font-mono bg-white/60 px-2 py-0.5 rounded">{dict.defaultValue}</code>
            </div>
          )}
          {dict.valueRange && (dict.valueRange.min !== undefined || dict.valueRange.max !== undefined) && (
            <div className="flex items-center justify-between py-1.5">
              <span className="text-xs text-gray-500">值范围</span>
              <code className="text-xs font-mono bg-white/60 px-2 py-0.5 rounded">
                {dict.valueRange.min ?? '-∞'} ~ {dict.valueRange.max ?? '+∞'}
              </code>
            </div>
          )}
        </div>
      </div>

      <div>
        <h5 className="text-xs font-medium text-gray-500 uppercase mb-2">业务含义</h5>
        <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">{dict.businessMeaning}</p>
      </div>

      <div>
        <h5 className="text-xs font-medium text-gray-500 uppercase mb-2">技术描述</h5>
        <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">{dict.description}</p>
      </div>

      {dict.enumValues && dict.enumValues.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-500 uppercase mb-2 flex items-center gap-1">
            <List className="w-3 h-3" /> 枚举值
          </h5>
          <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
            <div className="px-3 py-2 bg-gray-50 flex items-center gap-3 text-xs text-gray-500 font-medium">
              <span className="w-16">值</span>
              <span className="flex-1">标签</span>
              <span className="w-28">频率分布</span>
            </div>
            <div className="px-3">
              {dict.enumValues.map((ev, idx) => (
                <EnumValueRow key={idx} enumVal={ev} />
              ))}
            </div>
          </div>
        </div>
      )}

      <div>
        <h5 className="text-xs font-medium text-gray-500 uppercase mb-2 flex items-center gap-1">
          <Tag className="w-3 h-3" /> 示例值
        </h5>
        <div className="flex flex-wrap gap-2">
          {dict.sampleValues.map((val, idx) => (
            <code key={idx} className="text-xs font-mono bg-gray-100 px-2 py-1 rounded">
              {val}
            </code>
          ))}
        </div>
      </div>

      <div>
        <h5 className="text-xs font-medium text-gray-500 uppercase mb-2">数据模式</h5>
        <div className="flex flex-wrap gap-2">
          {dict.patterns.map((pattern, idx) => (
            <span key={idx} className="px-2 py-1 text-xs bg-indigo-50 text-indigo-700 rounded-full">
              {pattern}
            </span>
          ))}
        </div>
      </div>

      {dict.relatedFields.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-500 uppercase mb-2 flex items-center gap-1">
            <Link2 className="w-3 h-3" /> 关联字段
          </h5>
          <div className="space-y-1">
            {dict.relatedFields.map((field, idx) => (
              <div key={idx} className="text-xs text-gray-600 bg-gray-50 rounded px-2 py-1.5 font-mono">
                {field}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center gap-2 text-xs text-gray-400 pt-2 border-t border-gray-100">
        <Clock className="w-3 h-3" />
        <span>最后更新: {dict.lastUpdated} · {dict.updatedBy}</span>
      </div>
    </div>
  );
};
