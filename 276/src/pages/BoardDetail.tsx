import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  DndContext,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragOverEvent,
  DragStartEvent,
  DragCancelEvent,
} from '@dnd-kit/core';
import { arrayMove } from '@dnd-kit/sortable';
import { Plus, Filter, ArrowLeft, AlertCircle, Info, ClipboardList } from 'lucide-react';
import { useAppStore } from '@/store';
import { Task, TaskStatus } from '@/types';
import TaskColumn from '@/components/TaskColumn';
import TaskDetailModal from '@/components/TaskDetailModal';
import FilterPanel from '@/components/FilterPanel';
import TaskTemplateSelector from '@/components/TaskTemplateSelector';
import { canTransition, getTransitionBlockedReason, getStatusFlowDescription } from '@/utils/stateMachine';

const COLUMNS: TaskStatus[] = ['todo', 'in-progress', 'done'];

export default function BoardDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const {
    currentBoard,
    tasks,
    selectedTask,
    filters,
    fetchBoard,
    fetchTasks,
    createTask,
    moveTask,
    selectTask,
    setFilters,
    clearFilters,
    getFilteredTasks,
  } = useAppStore();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [showTemplateSelector, setShowTemplateSelector] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskStatus, setNewTaskStatus] = useState<TaskStatus>('todo');
  const [activeId, setActiveId] = useState<string | null>(null);
  const [blockedColumn, setBlockedColumn] = useState<TaskStatus | null>(null);
  const [blockedReason, setBlockedReason] = useState<string | null>(null);
  const [showStateTransitionError, setShowStateTransitionError] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  useEffect(() => {
    if (id) {
      fetchBoard(id);
      fetchTasks(id);
    }
  }, [id, fetchBoard, fetchTasks]);

  const filteredTasks = getFilteredTasks();

  const getTasksByStatus = (status: TaskStatus) => {
    return filteredTasks
      .filter((task) => task.status === status)
      .sort((a, b) => a.order - b.order);
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
    setBlockedColumn(null);
    setBlockedReason(null);
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    if (!over) {
      setBlockedColumn(null);
      setBlockedReason(null);
      return;
    }

    const activeId = active.id as string;
    const overId = over.id as string;

    const activeTask = tasks.find((t) => t._id === activeId);
    if (!activeTask) return;

    const overColumn = COLUMNS.includes(overId as TaskStatus)
      ? (overId as TaskStatus)
      : tasks.find((t) => t._id === overId)?.status;

    if (overColumn && activeTask.status !== overColumn) {
      if (!canTransition(activeTask.status, overColumn)) {
        setBlockedColumn(overColumn);
        setBlockedReason(getTransitionBlockedReason(activeTask.status, overColumn));
        return;
      }
      setBlockedColumn(null);
      setBlockedReason(null);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);
    setBlockedColumn(null);
    setBlockedReason(null);

    if (!over) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    const activeTask = tasks.find((t) => t._id === activeId);
    if (!activeTask) return;

    let newStatus: TaskStatus = activeTask.status;
    let newIndex: number = -1;

    if (COLUMNS.includes(overId as TaskStatus)) {
      newStatus = overId as TaskStatus;
      
      if (activeTask.status !== newStatus && !canTransition(activeTask.status, newStatus)) {
        setShowStateTransitionError(true);
        setTimeout(() => setShowStateTransitionError(false), 3000);
        return;
      }

      const overTasks = getTasksByStatus(newStatus);
      newIndex = overTasks.findIndex((t) => t._id === activeId) === -1 
        ? overTasks.length 
        : overTasks.findIndex((t) => t._id === activeId);
    } else {
      const overTask = tasks.find((t) => t._id === overId);
      if (!overTask) return;

      newStatus = overTask.status;

      if (activeTask.status !== newStatus && !canTransition(activeTask.status, newStatus)) {
        setShowStateTransitionError(true);
        setTimeout(() => setShowStateTransitionError(false), 3000);
        return;
      }

      const overTasks = getTasksByStatus(newStatus);
      const oldIndex = overTasks.findIndex((t) => t._id === activeId);
      newIndex = overTasks.findIndex((t) => t._id === overId);

      if (oldIndex !== -1 && oldIndex !== newIndex) {
        const reordered = arrayMove(overTasks, oldIndex, newIndex);
        reordered.forEach((t, i) => {
          if (t.order !== i) {
            t.order = i;
          }
        });
      }
    }

    const finalTasks = getTasksByStatus(newStatus);
    const finalIndex = finalTasks.findIndex((t) => t._id === activeId);
    const actualIndex = finalIndex === -1 ? finalTasks.length : finalIndex;
    
    moveTask(activeId, newStatus, actualIndex);
  };

  const handleDragCancel = (_event: DragCancelEvent) => {
    setActiveId(null);
    setBlockedColumn(null);
    setBlockedReason(null);
  };

  const handleCreateTask = async () => {
    if (!newTaskTitle.trim() || !id) return;
    await createTask({
      boardId: id,
      title: newTaskTitle,
      status: newTaskStatus,
    });
    setNewTaskTitle('');
    setShowCreateModal(false);
  };

  const handleCreateFromTemplate = async (task: Task) => {
    await createTask(task);
  };

  const handleOpenCreateTask = (status: TaskStatus) => {
    setNewTaskStatus(status);
    setShowCreateModal(true);
  };

  const hasActiveFilters = filters.assignee || filters.tags.length > 0 || filters.priority;

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {currentBoard?.name || '加载中...'}
            </h1>
            {currentBoard?.description && (
              <p className="text-gray-500 mt-1">{currentBoard.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <button
              onClick={() => setShowFilterPanel(!showFilterPanel)}
              className={`btn flex items-center gap-2 ${
                hasActiveFilters ? 'btn-primary' : 'btn-secondary'
              }`}
            >
              <Filter className="w-4 h-4" />
              筛选
              {hasActiveFilters && (
                <span className="bg-white text-primary-600 text-xs px-1.5 py-0.5 rounded-full">
                  {filters.tags.length + (filters.assignee ? 1 : 0) + (filters.priority ? 1 : 0)}
                </span>
              )}
            </button>
            {showFilterPanel && (
              <div className="absolute right-0 top-full mt-2 z-50">
                <FilterPanel
                  filters={filters}
                  tasks={tasks}
                  onFilterChange={setFilters}
                  onClear={clearFilters}
                  onClose={() => setShowFilterPanel(false)}
                />
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowTemplateSelector(true)}
              className="btn btn-secondary flex items-center gap-2"
            >
              <ClipboardList className="w-4 h-4" />
              从模板
            </button>
            <button
              onClick={() => handleOpenCreateTask('todo')}
              className="btn btn-primary flex items-center gap-2"
            >
              <Plus className="w-5 h-5" />
              添加任务
            </button>
          </div>
        </div>
      </div>

      <div className="mb-4 flex items-center gap-2 text-sm text-gray-500">
        <Info className="w-4 h-4" />
        <span>状态流转规则：{getStatusFlowDescription()}</span>
      </div>

      {showStateTransitionError && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 animate-fade-in">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <span className="text-red-700">
            状态流转不合法！请按照 {getStatusFlowDescription()} 的规则流转任务。
          </span>
        </div>
      )}

      {blockedReason && activeId && (
        <div className="mb-4 p-4 bg-orange-50 border border-orange-200 rounded-lg flex items-center gap-3 animate-fade-in">
          <AlertCircle className="w-5 h-5 text-orange-500 flex-shrink-0" />
          <span className="text-orange-700">{blockedReason}</span>
        </div>
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {COLUMNS.map((status) => (
            <TaskColumn
              key={status}
              status={status}
              tasks={getTasksByStatus(status)}
              onTaskClick={(task) => selectTask(task)}
              onAddTask={() => handleOpenCreateTask(status)}
              isBlocked={blockedColumn === status}
            />
          ))}
        </div>
      </DndContext>

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div
            className="modal-content animate-fade-in max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold">创建新任务</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  任务标题
                </label>
                <input
                  type="text"
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  placeholder="输入任务标题..."
                  className="input"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  初始状态
                </label>
                <select
                  value={newTaskStatus}
                  onChange={(e) => setNewTaskStatus(e.target.value as TaskStatus)}
                  className="select"
                >
                  <option value="todo">待办</option>
                  <option value="in-progress">进行中</option>
                  <option value="done">已完成</option>
                </select>
              </div>
            </div>
            <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="btn btn-secondary"
              >
                取消
              </button>
              <button
                onClick={handleCreateTask}
                disabled={!newTaskTitle.trim()}
                className="btn btn-primary"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedTask && (
        <TaskDetailModal task={selectedTask} onClose={() => selectTask(null)} />
      )}

      {showTemplateSelector && id && (
        <TaskTemplateSelector
          boardId={id}
          onSelect={handleCreateFromTemplate}
          onClose={() => setShowTemplateSelector(false)}
        />
      )}
    </div>
  );
}
