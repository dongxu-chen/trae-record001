import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Calendar, User, MessageSquare, CheckSquare, Flag } from 'lucide-react';
import { Task } from '@/types';
import { formatDate, getPriorityColor, getDueDateStatus, priorityLabels } from '@/utils';

interface TaskCardProps {
  task: Task;
  onClick: () => void;
}

export default function TaskCard({ task, onClick }: TaskCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task._id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const dueDateStatus = getDueDateStatus(task.dueDate);
  const completedSubtasks = task.subTasks.filter((st) => st.completed).length;
  const totalSubtasks = task.subTasks.length;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className={`task-card ${isDragging ? 'dragging' : ''}`}
    >
      <div className="flex items-start justify-between mb-3">
        <h4 className="font-medium text-gray-900 line-clamp-2">{task.title}</h4>
        <span
          className={`${getPriorityColor(
            task.priority
          )} text-white text-xs px-2 py-0.5 rounded-full flex-shrink-0 ml-2`}
        >
          {priorityLabels[task.priority]}
        </span>
      </div>

      {task.description && (
        <p className="text-sm text-gray-500 line-clamp-2 mb-3">
          {task.description}
        </p>
      )}

      {task.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {task.tags.slice(0, 3).map((tag, index) => (
            <span
              key={index}
              className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded"
            >
              {tag}
            </span>
          ))}
          {task.tags.length > 3 && (
            <span className="text-gray-400 text-xs">+{task.tags.length - 3}</span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-gray-400">
        <div className="flex items-center gap-3">
          {task.assignee && (
            <div className="flex items-center gap-1">
              <User className="w-3.5 h-3.5" />
              <span className="truncate max-w-[80px]">{task.assignee}</span>
            </div>
          )}

          {totalSubtasks > 0 && (
            <div className="flex items-center gap-1">
              <CheckSquare className="w-3.5 h-3.5" />
              <span>
                {completedSubtasks}/{totalSubtasks}
              </span>
            </div>
          )}

          {task.comments.length > 0 && (
            <div className="flex items-center gap-1">
              <MessageSquare className="w-3.5 h-3.5" />
              <span>{task.comments.length}</span>
            </div>
          )}
        </div>

        {task.dueDate && (
          <div
            className={`flex items-center gap-1 ${
              dueDateStatus === 'overdue'
                ? 'text-red-500'
                : dueDateStatus === 'today'
                ? 'text-orange-500'
                : ''
            }`}
          >
            <Calendar className="w-3.5 h-3.5" />
            <span>{formatDate(task.dueDate)}</span>
          </div>
        )}
      </div>
    </div>
  );
}
