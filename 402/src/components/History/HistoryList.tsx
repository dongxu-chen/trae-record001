import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, Trash2, FileJson, FileSpreadsheet } from 'lucide-react';
import { HistoryItem } from './HistoryItem';
import { SearchBar } from './SearchBar';
import { useHistory } from '../../hooks/useHistory';
import { useSettings } from '../../hooks/useSettings';
import { exportRecords } from '../../utils/export';

export function HistoryList() {
  const navigate = useNavigate();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showExportMenu, setShowExportMenu] = useState(false);
  
  const {
    filteredRecords,
    searchQuery,
    setSearchQuery,
    deleteRecord,
    deleteRecords,
    clearRecords,
    updateNote,
  } = useHistory();
  
  const { settings } = useSettings();

  const handleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedIds.size === filteredRecords.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredRecords.map((r) => r.id)));
    }
  };

  const handleDeleteSelected = () => {
    deleteRecords(Array.from(selectedIds));
    setSelectedIds(new Set());
  };

  const handleClearAll = () => {
    if (confirm('确定要清空所有历史记录吗？此操作不可恢复。')) {
      clearRecords();
      setSelectedIds(new Set());
    }
  };

  const handleExport = (format: 'csv' | 'json') => {
    const recordsToExport = selectedIds.size > 0
      ? filteredRecords.filter((r) => selectedIds.has(r.id))
      : filteredRecords;
    
    if (recordsToExport.length === 0) {
      alert('没有可导出的记录');
      return;
    }
    
    exportRecords(recordsToExport, format);
    setShowExportMenu(false);
    setSelectedIds(new Set());
  };

  return (
    <div className="min-h-screen bg-[#0d1117]">
      <div className="sticky top-0 z-40 bg-[#0d1117]/95 backdrop-blur-xl border-b border-gray-800">
        <div className="px-4 py-3">
          <div className="flex items-center gap-3 mb-3">
            <button
              onClick={() => navigate('/')}
              className="p-2 -ml-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-lg font-semibold text-white">历史记录</h1>
            <span className="ml-auto text-sm text-gray-500">
              {filteredRecords.length} 条记录
            </span>
          </div>
          
          <SearchBar value={searchQuery} onChange={setSearchQuery} />
        </div>
      </div>

      <div className="p-4 space-y-3">
        {filteredRecords.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-800 flex items-center justify-center">
              <FileJson className="w-8 h-8 text-gray-600" />
            </div>
            <p className="text-gray-400 mb-1">暂无扫码记录</p>
            <p className="text-gray-500 text-sm">扫描的二维码会自动保存到这里</p>
          </div>
        ) : (
          filteredRecords.map((record) => (
            <HistoryItem
              key={record.id}
              record={record}
              selected={selectedIds.has(record.id)}
              onSelect={handleSelect}
              onDelete={deleteRecord}
              onUpdateNote={updateNote}
            />
          ))
        )}
      </div>

      {(selectedIds.size > 0 || filteredRecords.length > 0) && (
        <div className="fixed bottom-0 left-0 right-0 z-40">
          <div className="mx-auto max-w-lg px-4 pb-6">
            <div className="flex items-center justify-between gap-3 p-2 bg-gray-900/95 backdrop-blur-xl rounded-2xl border border-gray-700/50 shadow-2xl">
              <button
                onClick={handleSelectAll}
                className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                {selectedIds.size === filteredRecords.length ? '取消全选' : '全选'}
              </button>

              <div className="flex items-center gap-2">
                {selectedIds.size > 0 && (
                  <>
                    <span className="text-sm text-gray-500">
                      已选 {selectedIds.size}
                    </span>
                    <button
                      onClick={handleDeleteSelected}
                      className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                      title="删除选中"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </>
                )}

                <div className="relative">
                  <button
                    onClick={() => setShowExportMenu(!showExportMenu)}
                    className="p-2 text-gray-400 hover:text-white hover:bg-gray-700/50 rounded-lg transition-colors"
                    title="导出"
                  >
                    <Download className="w-5 h-5" />
                  </button>
                  
                  {showExportMenu && (
                    <>
                      <div
                        className="fixed inset-0 z-50"
                        onClick={() => setShowExportMenu(false)}
                      />
                      <div className="absolute bottom-full right-0 mb-2 min-w-[140px] bg-[#161b22] rounded-xl border border-gray-700 shadow-xl overflow-hidden">
                        <button
                          onClick={() => handleExport('json')}
                          className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-gray-300 hover:bg-gray-700 transition-colors"
                        >
                          <FileJson className="w-4 h-4" />
                          导出为 JSON
                        </button>
                        <button
                          onClick={() => handleExport('csv')}
                          className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-gray-300 hover:bg-gray-700 transition-colors"
                        >
                          <FileSpreadsheet className="w-4 h-4" />
                          导出为 CSV
                        </button>
                      </div>
                    </>
                  )}
                </div>

                {filteredRecords.length > 0 && (
                  <button
                    onClick={handleClearAll}
                    className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                    title="清空全部"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
