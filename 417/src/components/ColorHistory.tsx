import { useState, useEffect } from 'react';
import { History, Trash2, Tag, Plus, X, ChevronDown } from 'lucide-react';
import { useColorStore } from '@/hooks/useColorStore';
import { addColorToHistory, getColorHistory, deleteColorFromHistory, getProjects, updateColorProject } from '@/hooks/useColorHistory';
import type { ColorHistory as ColorHistoryType } from '@/types';

export default function ColorHistory() {
  const { currentColor, colorSpaces, setCurrentColor, currentProject, setCurrentProject } = useColorStore();
  const [history, setHistory] = useState<ColorHistoryType[]>([]);
  const [projects, setProjects] = useState<string[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<string>('all');
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [newProjectName, setNewProjectName] = useState('');

  const loadHistory = async () => {
    const records = await getColorHistory(selectedFilter);
    setHistory(records);
  };

  const loadProjects = async () => {
    const projList = await getProjects();
    setProjects(projList);
  };

  useEffect(() => {
    loadProjects();
    loadHistory();
  }, [selectedFilter]);

  useEffect(() => {
    const save = async () => {
      await addColorToHistory(currentColor, colorSpaces.rgb, currentProject || undefined);
      await loadHistory();
      await loadProjects();
    };
    const timer = setTimeout(save, 800);
    return () => clearTimeout(timer);
  }, [currentColor, currentProject]);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    await deleteColorFromHistory(id);
    await loadHistory();
    await loadProjects();
  };

  const handleSetProject = async (id: string, project: string | undefined) => {
    await updateColorProject(id, project);
    setEditingId(null);
    await loadHistory();
    await loadProjects();
  };

  return (
    <div className="bg-[#1e1e2e] rounded-xl p-5 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-gray-300" />
          <h3 className="text-gray-200 font-medium">颜色历史</h3>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <button
              onClick={() => setIsFilterOpen(!isFilterOpen)}
              className="flex items-center gap-1.5 bg-[#2a2a3e] hover:bg-[#3a3a4e] text-gray-300 rounded-lg px-2.5 py-1.5 text-xs transition-colors"
            >
              <Tag className="w-3.5 h-3.5" />
              <span>{selectedFilter === 'all' ? '全部' : selectedFilter}</span>
              <ChevronDown className={`w-3 h-3 transition-transform ${isFilterOpen ? 'rotate-180' : ''}`} />
            </button>
            {isFilterOpen && (
              <div className="absolute right-0 z-20 mt-1 bg-[#2a2a3e] rounded-lg shadow-xl border border-white/5 overflow-hidden min-w-[120px]">
                <button
                  onClick={() => {
                    setSelectedFilter('all');
                    setIsFilterOpen(false);
                  }}
                  className={`w-full px-3 py-2 text-left text-xs hover:bg-[#3a3a4e] transition-colors ${
                    selectedFilter === 'all' ? 'text-[#8b8cf7] bg-[#2a2a4e]' : 'text-gray-300'
                  }`}
                >
                  全部
                </button>
                {projects.map((proj) => (
                  <button
                    key={proj}
                    onClick={() => {
                      setSelectedFilter(proj);
                      setIsFilterOpen(false);
                    }}
                    className={`w-full px-3 py-2 text-left text-xs hover:bg-[#3a3a4e] transition-colors ${
                      selectedFilter === proj ? 'text-[#8b8cf7] bg-[#2a2a4e]' : 'text-gray-300'
                    }`}
                  >
                    {proj}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-4">
        <span className="text-gray-500 text-xs">当前项目:</span>
        <input
          type="text"
          value={currentProject}
          onChange={(e) => setCurrentProject(e.target.value)}
          placeholder="输入项目名称..."
          className="flex-1 bg-[#2a2a3e] text-gray-300 rounded-lg px-2.5 py-1.5 text-xs outline-none border border-transparent focus:border-[#5b5fc7]"
        />
      </div>

      {history.length === 0 ? (
        <p className="text-gray-500 text-sm text-center py-4">暂无历史记录</p>
      ) : (
        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin">
          {history.map((item) => (
            <div key={item.id} className="relative group flex-shrink-0">
              <button
                onClick={() => setCurrentColor(item.hex)}
                className="w-10 h-10 rounded-lg border border-white/10 hover:scale-110 transition-transform"
                style={{ backgroundColor: item.hex }}
                title={item.project ? `${item.hex} (${item.project})` : item.hex}
              />
              {item.project && (
                <span className="absolute -bottom-1 left-1/2 -translate-x-1/2 bg-[#5b5fc7] text-white text-[9px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                  {item.project}
                </span>
              )}
              <div className="absolute -top-1 -right-1 flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                {editingId !== item.id ? (
                  <>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingId(item.id);
                        setNewProjectName(item.project || '');
                      }}
                      className="w-4 h-4 bg-[#5b5fc7] rounded-full flex items-center justify-center hover:bg-[#6b6fd7]"
                      title="设置项目标签"
                    >
                      <Plus className="w-2.5 h-2.5 text-white" />
                    </button>
                    <button
                      onClick={(e) => handleDelete(item.id, e)}
                      className="w-4 h-4 bg-red-500 rounded-full flex items-center justify-center hover:bg-red-400"
                      title="删除"
                    >
                      <Trash2 className="w-2.5 h-2.5 text-white" />
                    </button>
                  </>
                ) : (
                  <div className="absolute right-0 top-0 flex items-center gap-1 bg-[#2a2a3e] rounded-lg p-1 shadow-xl z-30">
                    <input
                      type="text"
                      value={newProjectName}
                      onChange={(e) => setNewProjectName(e.target.value)}
                      placeholder="项目名"
                      className="w-20 bg-[#1e1e2e] text-gray-200 rounded px-2 py-1 text-xs outline-none"
                      onClick={(e) => e.stopPropagation()}
                    />
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSetProject(item.id, newProjectName.trim() || undefined);
                      }}
                      className="w-5 h-5 bg-[#5b5fc7] rounded flex items-center justify-center"
                    >
                      <Plus className="w-3 h-3 text-white" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingId(null);
                      }}
                      className="w-5 h-5 bg-gray-600 rounded flex items-center justify-center"
                    >
                      <X className="w-3 h-3 text-white" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
