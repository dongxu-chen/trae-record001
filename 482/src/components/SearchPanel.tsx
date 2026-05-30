import { useState, useEffect } from 'react';
import { Search, Database, Clock, Loader2, X } from 'lucide-react';
import { useLineageStore } from '@/stores/useLineageStore';
import { mockSearchFields } from '@/mock/data';

export const SearchPanel = () => {
  const {
    searchKeyword,
    setSearchKeyword,
    dataSources,
    selectedDataSources,
    toggleDataSource,
    analyzeLineage,
    isAnalyzing,
    selectedField,
    setSelectedField,
    searchHistory,
  } = useLineageStore();

  const [showSuggestions, setShowSuggestions] = useState(false);

  const filteredFields = mockSearchFields.filter(
    (f) =>
      f.name.toLowerCase().includes(searchKeyword.toLowerCase()) ||
      f.table.toLowerCase().includes(searchKeyword.toLowerCase())
  );

  const handleFieldSelect = (field: typeof mockSearchFields[0]) => {
    const fullField = {
      id: field.id,
      name: field.name,
      table: field.table,
      database: field.database,
      datasource: 'ds-001',
      type: 'field' as const,
    };
    setSelectedField(fullField);
    setSearchKeyword(`${field.database}.${field.table}.${field.name}`);
    setShowSuggestions(false);
  };

  const handleAnalyze = () => {
    if (selectedField) {
      analyzeLineage(selectedField.id);
    }
  };

  const handleHistoryClick = (history: { fieldName: string; fieldId: string }) => {
    setSearchKeyword(history.fieldName);
    const field = mockSearchFields.find((f) => f.id === history.fieldId);
    if (field) {
      handleFieldSelect(field);
    }
  };

  return (
    <div className="w-80 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
      <div className="p-4 border-b border-gray-200">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              字段名称
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchKeyword}
                onChange={(e) => {
                  setSearchKeyword(e.target.value);
                  setShowSuggestions(true);
                }}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                placeholder="输入字段名搜索..."
                className="input-field pl-10 pr-10"
              />
              {searchKeyword && (
                <button
                  onClick={() => {
                    setSearchKeyword('');
                    setSelectedField(null);
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                >
                  <X className="w-4 h-4 text-gray-400 hover:text-gray-600" />
                </button>
              )}

              {showSuggestions && searchKeyword && filteredFields.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-100 max-h-60 overflow-y-auto z-50">
                  {filteredFields.map((field) => (
                    <button
                      key={field.id}
                      onMouseDown={() => handleFieldSelect(field)}
                      className="w-full px-3 py-2 text-left hover:bg-gray-50 flex flex-col"
                    >
                      <span className="text-sm font-medium text-gray-900 font-mono">
                        {field.name}
                      </span>
                      <span className="text-xs text-gray-500">
                        {field.database}.{field.table}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <Database className="w-4 h-4" />
              数据源
            </label>
            <div className="space-y-2">
              {dataSources.map((ds) => (
                <label
                  key={ds.id}
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-white cursor-pointer transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selectedDataSources.includes(ds.id)}
                    onChange={() => toggleDataSource(ds.id)}
                    className="w-4 h-4 text-primary-500 rounded focus:ring-primary-500"
                  />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-700">
                      {ds.name}
                    </div>
                    <div className="text-xs text-gray-500">
                      {ds.type.toUpperCase()} · {ds.host}
                    </div>
                  </div>
                  <span
                    className={`w-2 h-2 rounded-full ${
                      ds.status === 'connected'
                        ? 'bg-green-500'
                        : ds.status === 'connecting'
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                  />
                </label>
              ))}
            </div>
          </div>

          <button
            onClick={handleAnalyze}
            disabled={!selectedField || isAnalyzing}
            className="w-full btn-primary flex items-center justify-center gap-2"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                分析中...
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                开始分析
              </>
            )}
          </button>
        </div>
      </div>

      {searchHistory.length > 0 && (
        <div className="flex-1 p-4 overflow-y-auto">
          <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
            <Clock className="w-4 h-4" />
            搜索历史
          </h3>
          <div className="space-y-2">
            {searchHistory.map((item) => (
              <button
                key={item.id}
                onClick={() => handleHistoryClick(item)}
                className="w-full p-3 text-left bg-white rounded-lg border border-gray-100 hover:border-primary-200 hover:shadow-sm transition-all"
              >
                <div className="text-sm font-medium text-gray-900 font-mono">
                  {item.fieldName}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {new Date(item.timestamp).toLocaleString()}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
