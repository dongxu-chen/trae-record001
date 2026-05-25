import { useState } from 'react';
import {
  X,
  Calendar,
  User,
  Flag,
  Tag,
  CheckSquare,
  MessageSquare,
  Clock,
  Trash2,
  Plus,
  Send,
  FileText,
  ChevronDown,
  ChevronUp,
  UserPlus,
  Edit3,
  CheckCircle,
  XCircle,
  MessageCircle,
  PlusCircle,
  MinusCircle,
} from 'lucide-react';
import { Task, Priority, TaskStatus, SubTask, Comment, OperationLog, OperationType } from '@/types';
import { useAppStore } from '@/store';
import { taskApi } from '@/services/api';
import {
  formatDate,
  formatDateTime,
  priorityLabels,
  statusLabels,
  getPriorityColor,
  getStatusColor,
  getFieldLabel,
} from '@/utils';

interface TaskDetailModalProps {
  task: Task;
  onClose: () => void;
}

const getOperationIcon = (operation: OperationType) => {
  const icons: Record<OperationType, any> = {
    create: PlusCircle,
    update: Edit3,
    delete: XCircle,
    status_change: Clock,
    subtask_add: PlusCircle,
    subtask_remove: MinusCircle,
    subtask_complete: CheckCircle,
    comment_add: MessageCircle,
    comment_remove: XCircle,
  };
  return icons[operation] || FileText;
};

const getOperationColor = (operation: OperationType): string => {
  const colors: Record<OperationType, string> = {
    create: 'text-green-600 bg-green-100',
    update: 'text-blue-600 bg-blue-100',
    delete: 'text-red-600 bg-red-100',
    status_change: 'text-amber-600 bg-amber-100',
    subtask_add: 'text-green-600 bg-green-100',
    subtask_remove: 'text-red-600 bg-red-100',
    subtask_complete: 'text-emerald-600 bg-emerald-100',
    comment_add: 'text-purple-600 bg-purple-100',
    comment_remove: 'text-red-600 bg-red-100',
  };
  return colors[operation] || 'text-gray-600 bg-gray-100';
};

const getOperationLabel = (operation: OperationType): string => {
  const labels: Record<OperationType, string> = {
    create: '创建',
    update: '更新',
    delete: '删除',
    status_change: '状态变更',
    subtask_add: '添加子任务',
    subtask_remove: '删除子任务',
    subtask_complete: '完成子任务',
    comment_add: '添加评论',
    comment_remove: '删除评论',
  };
  return labels[operation] || operation;
};

export default function TaskDetailModal({ task: initialTask, onClose }: TaskDetailModalProps) {
  const [task, setTask] = useState<Task>(initialTask);
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({
    title: task.title,
    description: task.description,
    priority: task.priority,
    assignee: task.assignee,
    dueDate: task.dueDate ? task.dueDate.split('T')[0] : '',
    tags: task.tags.join(', '),
  });
  const [newSubTask, setNewSubTask] = useState('');
  const [newComment, setNewComment] = useState('');
  const [activeTab, setActiveTab] = useState<'subtasks' | 'comments' | 'logs'>('subtasks');
  const [expandedLog, setExpandedLog] = useState<string | null>(null);
  const { updateTask, deleteTask, refreshTask } = useAppStore();

  const handleSave = async () => {
    const updateData = {
      title: editData.title,
      description: editData.description,
      priority: editData.priority as Priority,
      assignee: editData.assignee,
      dueDate: editData.dueDate ? new Date(editData.dueDate).toISOString() : null,
      tags: editData.tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
    };
    await updateTask(task._id, updateData);
    await refreshTask(task._id);
    const updatedTask = (useAppStore.getState().tasks.find((t) => t._id === task._id) || task) as Task;
    setTask(updatedTask);
    setIsEditing(false);
  };

  const handleAddSubTask = async () => {
    if (!newSubTask.trim()) return;
    const updatedTask = await taskApi.addSubTask(task._id, newSubTask);
    setTask(updatedTask);
    setNewSubTask('');
    await refreshTask(task._id);
  };

  const handleToggleSubTask = async (subTask: SubTask) => {
    const updatedTask = await taskApi.updateSubTask(task._id, subTask._id, {
      completed: !subTask.completed,
    });
    setTask(updatedTask);
    await refreshTask(task._id);
  };

  const handleDeleteSubTask = async (subTaskId: string) => {
    const updatedTask = await taskApi.deleteSubTask(task._id, subTaskId);
    setTask(updatedTask);
    await refreshTask(task._id);
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) return;
    const updatedTask = await taskApi.addComment(task._id, newComment, '当前用户');
    setTask(updatedTask);
    setNewComment('');
    await refreshTask(task._id);
  };

  const handleDeleteTask = async () => {
    if (confirm('确定要删除这个任务吗？')) {
      await deleteTask(task._id);
      onClose();
    }
  };

  const operationLogs = task.operationLogs && task.operationLogs.length > 0 
    ? task.operationLogs 
    : task.history.map((h, i) => ({
        _id: h._id,
        operation: 'update' as OperationType,
        operator: h.changedBy,
        timestamp: h.changedAt,
        description: `更改了 ${getFieldLabel(h.field)}`,
        changes: [{ field: h.field, oldValue: h.oldValue, newValue: h.newValue }],
      }));

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 border-b border-gray-200 flex items-start justify-between">
          <div className="flex-1">
            {isEditing ? (
              <input
                type="text"
                value={editData.title}
                onChange={(e) => setEditData({ ...editData, title: e.target.value })}
                className="text-xl font-semibold w-full input"
              />
            ) : (
              <h2 className="text-xl font-semibold text-gray-900">{task.title}</h2>
            )}
            <div className="flex items-center gap-4 mt-2">
              <span className={`${getStatusColor(task.status as TaskStatus)} text-white text-xs px-2 py-1 rounded-full`}>
                {statusLabels[task.status as TaskStatus]}
              </span>
              <span className={`${getPriorityColor(task.priority)} text-white text-xs px-2 py-1 rounded-full`}>
                {priorityLabels[task.priority]}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 ml-4">
            {isEditing ? (
              <>
                <button onClick={() => setIsEditing(false)} className="btn btn-secondary text-sm">
                  取消
                </button>
                <button onClick={handleSave} className="btn btn-primary text-sm">
                  保存
                </button>
              </>
            ) : (
              <button onClick={() => setIsEditing(true)} className="btn btn-secondary text-sm">
                编辑
              </button>
            )}
            <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="p-6 grid grid-cols-3 gap-6">
            <div className="col-span-2 space-y-6">
              {isEditing ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">描述</label>
                  <textarea
                    value={editData.description}
                    onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                    rows={4}
                    className="input resize-none"
                  />
                </div>
              ) : (
                task.description && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">描述</h3>
                    <p className="text-gray-600 whitespace-pre-wrap">{task.description}</p>
                  </div>
                )
              )}

              <div className="border-t border-gray-200 pt-4">
                <div className="flex gap-1 mb-4">
                  {[
                    { key: 'subtasks', label: '子任务', icon: CheckSquare, count: task.subTasks.length },
                    { key: 'comments', label: '评论', icon: MessageSquare, count: task.comments.length },
                    { key: 'logs', label: '操作日志', icon: Clock, count: operationLogs.length },
                  ].map((tab) => (
                    <button
                      key={tab.key}
                      onClick={() => setActiveTab(tab.key as any)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        activeTab === tab.key
                          ? 'bg-primary-100 text-primary-700'
                          : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      <tab.icon className="w-4 h-4" />
                      {tab.label}
                      {tab.count > 0 && (
                        <span className="bg-gray-200 text-gray-600 text-xs px-2 py-0.5 rounded-full">
                          {tab.count}
                        </span>
                      )}
                    </button>
                  ))}
                </div>

                {activeTab === 'subtasks' && (
                  <div className="space-y-3">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newSubTask}
                        onChange={(e) => setNewSubTask(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAddSubTask()}
                        placeholder="添加子任务..."
                        className="input flex-1"
                      />
                      <button onClick={handleAddSubTask} className="btn btn-primary">
                        <Plus className="w-5 h-5" />
                      </button>
                    </div>
                    {task.subTasks.map((subTask) => (
                      <div key={subTask._id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg group">
                        <input
                          type="checkbox"
                          checked={subTask.completed}
                          onChange={() => handleToggleSubTask(subTask)}
                          className="w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        <span className={`flex-1 ${subTask.completed ? 'line-through text-gray-400' : 'text-gray-700'}`}>
                          {subTask.title}
                        </span>
                        <button
                          onClick={() => handleDeleteSubTask(subTask._id)}
                          className="p-1 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                    {task.subTasks.length === 0 && (
                      <p className="text-gray-400 text-sm text-center py-4">暂无子任务</p>
                    )}
                  </div>
                )}

                {activeTab === 'comments' && (
                  <div className="space-y-3">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newComment}
                        onChange={(e) => setNewComment(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAddComment()}
                        placeholder="添加评论..."
                        className="input flex-1"
                      />
                      <button onClick={handleAddComment} className="btn btn-primary">
                        <Send className="w-5 h-5" />
                      </button>
                    </div>
                    {task.comments
                      .slice()
                      .reverse()
                      .map((comment) => (
                        <div key={comment._id} className="p-4 bg-gray-50 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-gray-900">{comment.author}</span>
                            <span className="text-xs text-gray-400">{formatDateTime(comment.createdAt)}</span>
                          </div>
                          <p className="text-gray-600">{comment.content}</p>
                        </div>
                      ))}
                    {task.comments.length === 0 && (
                      <p className="text-gray-400 text-sm text-center py-4">暂无评论</p>
                    )}
                  </div>
                )}

                {activeTab === 'logs' && (
                  <div className="space-y-3">
                    {operationLogs
                      .slice()
                      .reverse()
                      .map((log: OperationLog) => {
                        const OpIcon = getOperationIcon(log.operation);
                        const colorClass = getOperationColor(log.operation);
                        const isExpanded = expandedLog === log._id;
                        const hasSnapshot = log.snapshotBefore || log.snapshotAfter;
                        return (
                          <div key={log._id} className="bg-gray-50 rounded-lg overflow-hidden">
                            <div
                              className={`flex items-start gap-3 p-3 cursor-pointer hover:bg-gray-100 transition-colors"
                              onClick={() => setExpandedLog(isExpanded ? null : log._id)}
                            >
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${colorClass}`}>
                                <OpIcon className="w-4 h-4" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium text-gray-900">{log.operator}</span>
                                  <span className={`text-xs px-2 py-0.5 rounded-full ${colorClass}`}>
                                    {getOperationLabel(log.operation)}
                                  </span>
                                </div>
                                <p className="text-sm text-gray-600 mt-0.5">{log.description}</p>
                                <p className="text-xs text-gray-400 mt-1">{formatDateTime(log.timestamp)}</p>
                              </div>
                              {(log.changes || hasSnapshot) && (
                                <div className="flex-shrink-0">
                                  {isExpanded ? (
                                    <ChevronUp className="w-4 h-4 text-gray-400" />
                                  ) : (
                                    <ChevronDown className="w-4 h-4 text-gray-400" />
                                  )}
                                </div>
                              )}
                            </div>

                            {isExpanded && (
                              <div className="border-t border-gray-200 p-3 space-y-3">
                                {log.changes && log.changes.length > 0 && (
                                  <div>
                                    <h4 className="text-xs font-medium text-gray-500 mb-2">变更详情</h4>
                                  <div className="space-y-2">
                                    {log.changes.map((change, i) => (
                                      <div key={i} className="flex items-start gap-2 text-sm">
                                        <span className="text-gray-600 font-medium">{getFieldLabel(change.field)}:</span>
                                        {change.oldValue !== null && change.oldValue !== undefined && (
                                          <span className="text-red-500 line-through">{String(change.oldValue)}</span>
                                        )}
                                        {change.oldValue !== null && change.oldValue !== undefined && change.newValue !== null && change.newValue !== undefined && (
                                            <span className="text-gray-400">→</span>
                                          )}
                                        {change.newValue !== null && change.newValue !== undefined && (
                                          <span className="text-green-600 font-medium">{String(change.newValue)}</span>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>

                                {hasSnapshot && (
                                  <div>
                                    <h4 className="text-xs font-medium text-gray-500 mb-2">快照对比</h4>
                                  <div className="grid grid-cols-2 gap-3">
                                    {log.snapshotBefore && (
                                      <div className="bg-white rounded p-3 border border-gray-200">
                                        <h5 className="text-xs font-medium text-gray-500 mb-2">变更前</h5>
                                        <div className="space-y-1 text-xs">
                                          <p><span className="text-gray-500">状态:</span> {statusLabels[log.snapshotBefore.status as TaskStatus]}</p>
                                          <p><span className="text-gray-500">优先级:</span> {priorityLabels[log.snapshotBefore.priority as Priority]}</p>
                                          <p><span className="text-gray-500">负责人:</span> {log.snapshotBefore.assignee || '-'}</p>
                                          <p><span className="text-gray-500">子任务:</span> {log.snapshotBefore.subTasks.length} 个</p>
                                        </div>
                                      </div>
                                    )}
                                    {log.snapshotAfter && (
                                      <div className="bg-white rounded p-3 border border-gray-200">
                                        <h5 className="text-xs font-medium text-gray-500 mb-2">变更后</h5>
                                        <div className="space-y-1 text-xs">
                                          <p><span className="text-gray-500">状态:</span> {statusLabels[log.snapshotAfter.status as TaskStatus]}</p>
                                          <p><span className="text-gray-500">优先级:</span> {priorityLabels[log.snapshotAfter.priority as Priority]}</p>
                                          <p><span className="text-gray-500">负责人:</span> {log.snapshotAfter.assignee || '-'}</p>
                                          <p><span className="text-gray-500">子任务:</span> {log.snapshotAfter.subTasks.length} 个</p>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    {operationLogs.length === 0 && (
                      <p className="text-gray-400 text-sm text-center py-4">暂无操作日志</p>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-4">
              {isEditing ? (
                <>
                  <div>
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                      <User className="w-4 h-4" />
                      负责人
                    </label>
                    <input
                      type="text"
                      value={editData.assignee}
                      onChange={(e) => setEditData({ ...editData, assignee: e.target.value })}
                      placeholder="输入负责人"
                      className="input text-sm"
                    />
                  </div>
                  <div>
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                      <Flag className="w-4 h-4" />
                      优先级
                    </label>
                    <select
                      value={editData.priority}
                      onChange={(e) => setEditData({ ...editData, priority: e.target.value as Priority })}
                      className="select text-sm"
                    >
                      {(['low', 'medium', 'high', 'urgent'] as Priority[]).map((p) => (
                        <option key={p} value={p}>
                          {priorityLabels[p]}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                      <Calendar className="w-4 h-4" />
                      截止日期
                    </label>
                    <input
                      type="date"
                      value={editData.dueDate}
                      onChange={(e) => setEditData({ ...editData, dueDate: e.target.value })}
                      className="input text-sm"
                    />
                  </div>
                  <div>
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                      <Tag className="w-4 h-4" />
                      标签
                    </label>
                    <input
                      type="text"
                      value={editData.tags}
                      onChange={(e) => setEditData({ ...editData, tags: e.target.value })}
                      placeholder="用逗号分隔多个标签"
                      className="input text-sm"
                    />
                  </div>
                </>
              ) : (
                <>
                  {task.assignee && (
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                        <User className="w-4 h-4" />
                        负责人
                      </div>
                      <p className="text-gray-900">{task.assignee}</p>
                    </div>
                  )}
                  {task.dueDate && (
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                        <Calendar className="w-4 h-4" />
                        截止日期
                      </div>
                      <p className="text-gray-900">{formatDate(task.dueDate)}</p>
                    </div>
                  )}
                  {task.tags.length > 0 && (
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                        <Tag className="w-4 h-4" />
                        标签
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {task.tags.map((tag, index) => (
                          <span key={index} className="bg-primary-100 text-primary-700 text-xs px-2 py-1 rounded-full">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

              <div className="pt-4 border-t border-gray-200">
                <button onClick={handleDeleteTask} className="btn btn-danger w-full text-sm">
                  <Trash2 className="w-4 h-4 mr-2" />
                  删除任务
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
