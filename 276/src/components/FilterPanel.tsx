import { X, User, Tag, Flag } from 'lucide-react';
import { TaskFilters, Priority, Task } from '@/types';
import { priorityLabels } from '@/utils';

interface FilterPanelProps {
  filters: TaskFilters;
  tasks: Task[];
  onFilterChange: (filters: Partial<TaskFilters>) => void;
  onClear: () => void;
  onClose: () => void;
}

export default function FilterPanel({ filters, tasks, onFilterChange, onClear, onClose }: FilterPanelProps) {
  const assignees = [...new Set(tasks.map((t) => t.assignee).filter(Boolean))];
  const allTags = [...new Set(tasks.flatMap((t) => t.tags))];
  const priorities: Priority[] = ['low', 'medium', 'high', 'urgent'];

  const hasActiveFilters = filters.assignee || filters.tags.length > 0 || filters.priority;

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-4 w-72">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900">筛选任务</h3>
        <button
          onClick={onClose}
          className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-4">
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
            <User className="w-4 h-4" />
            负责人
          </label>
          <select
            value={filters.assignee}
            onChange={(e) => onFilterChange({ assignee: e.target.value })}
            className="select text-sm"
          >
            <option value="">全部</option>
            {assignees.map((assignee) => (
              <option key={assignee} value={assignee}>
                {assignee}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
            <Flag className="w-4 h-4" />
            优先级
          </label>
          <select
            value={filters.priority}
            onChange={(e) => onFilterChange({ priority: e.target.value as Priority | '' })}
            className="select text-sm"
          >
            <option value="">全部</option>
            {priorities.map((priority) => (
              <option key={priority} value={priority}>
                {priorityLabels[priority]}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
            <Tag className="w-4 h-4" />
            标签
          </label>
          <div className="flex flex-wrap gap-2">
            {allTags.map((tag) => (
              <button
                key={tag}
                onClick={() => {
                  const newTags = filters.tags.includes(tag)
                    ? filters.tags.filter((t) => t !== tag)
                    : [...filters.tags, tag];
                  onFilterChange({ tags: newTags });
                }}
                className={`px-2 py-1 text-xs rounded-full transition-colors ${
                  filters.tags.includes(tag)
                    ? 'bg-primary-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {tag}
              </button>
            ))}
            {allTags.length === 0 && (
              <span className="text-sm text-gray-400">暂无标签</span>
            )}
          </div>
        </div>
      </div>

      {hasActiveFilters && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <button onClick={onClear} className="btn btn-ghost w-full text-sm">
            清除筛选
          </button>
        </div>
      )}
    </div>
  );
}
