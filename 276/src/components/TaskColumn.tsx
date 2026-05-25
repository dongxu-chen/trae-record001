import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { Plus } from 'lucide-react';
import { Task, TaskStatus } from '@/types';
import TaskCard from './TaskCard';
import { statusLabels, getStatusColor } from '@/utils';

interface TaskColumnProps {
  status: TaskStatus;
  tasks: Task[];
  onTaskClick: (task: Task) => void;
  onAddTask: () => void;
  isBlocked?: boolean;
}

export default function TaskColumn({ status, tasks, onTaskClick, onAddTask, isBlocked = false }: TaskColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: status,
  });

  const getColumnStyle = () => {
    if (isBlocked) {
      return 'bg-red-50 ring-2 ring-red-200 opacity-70';
    }
    if (isOver) {
      return 'bg-primary-50 ring-2 ring-primary-200';
    }
    return '';
  };

  return (
    <div
      ref={setNodeRef}
      className={`column transition-all duration-200 ${getColumnStyle()}`}
    >
      <div className="column-header">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${getStatusColor(status)}`} />
          <h3 className="font-semibold text-gray-700">{statusLabels[status]}</h3>
          <span className="text-sm text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
            {tasks.length}
          </span>
        </div>
        <button
          onClick={onAddTask}
          className="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-gray-200 rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5" />
        </button>
      </div>

      <SortableContext items={tasks.map((t) => t._id)} strategy={verticalListSortingStrategy}>
        <div className="flex-1 space-y-3 overflow-y-auto">
          {tasks.map((task) => (
            <TaskCard key={task._id} task={task} onClick={() => onTaskClick(task)} />
          ))}

          {tasks.length === 0 && (
            <div className="text-center py-8 text-gray-400 text-sm">
              暂无任务
            </div>
          )}
        </div>
      </SortableContext>
    </div>
  );
}
