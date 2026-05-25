import { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Layers,
  AlertCircle,
} from 'lucide-react';
import {
  eachDayOfInterval,
  format,
  addMonths,
  subMonths,
  startOfMonth,
  endOfMonth,
  isToday,
} from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { useAppStore } from '@/store';
import { Task, TaskStatus } from '@/types';
import { getStatusColor, priorityLabels, getPriorityColor, formatDate } from '@/utils';
import {
  calculateGanttLayout,
  getTaskRowCount,
  assignTimeSlots,
  getTaskDateRange,
  GanttTaskLayout,
} from '@/utils/ganttLayout';

export default function GanttView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentBoard, tasks, fetchBoard, fetchTasks, selectTask } = useAppStore();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [zoomLevel, setZoomLevel] = useState(1);
  const [hoveredTask, setHoveredTask] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      fetchBoard(id);
      fetchTasks(id);
    }
  }, [id, fetchBoard, fetchTasks]);

  const dayWidth = 120 * zoomLevel;
  const rowHeight = 72;
  const headerHeight = 80;
  const taskBarHeight = 36;
  const rowGap = 8;

  const days = useMemo(() => {
    const start = startOfMonth(currentDate);
    const end = endOfMonth(currentDate);
    return eachDayOfInterval({ start, end });
  }, [currentDate]);

  const rowMap = useMemo(() => {
    return assignTimeSlots(tasks);
  }, [tasks]);

  const taskLayouts = useMemo(() => {
    const viewStart = startOfMonth(currentDate);
    return calculateGanttLayout(tasks, viewStart, dayWidth);
  }, [tasks, currentDate, dayWidth]);

  const totalRows = useMemo(() => {
    return getTaskRowCount(tasks);
  }, [tasks]);

  const tasksByRow = useMemo(() => {
    const map = new Map<number, Task[]>();
    tasks.forEach((task) => {
      const row = rowMap.get(task._id) || 0;
      if (!map.has(row)) {
        map.set(row, []);
      }
      map.get(row)!.push(task);
    });
    return map;
  }, [tasks, rowMap]);

  const getLayoutForTask = (taskId: string): GanttTaskLayout | undefined => {
    return taskLayouts.find((l) => l.task._id === taskId);
  };

  const getOverlappingCount = (row: number): number => {
    return tasksByRow.get(row)?.length || 0;
  };

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/board/${id}`)}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {currentBoard?.name || '加载中...'}
            </h1>
            <p className="text-gray-500 mt-1">甘特图视图 - 时间槽分配模式</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setZoomLevel(Math.max(0.5, zoomLevel - 0.25))}
              className="p-2 hover:bg-white rounded-md transition-colors"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-sm text-gray-600 w-12 text-center">
              {Math.round(zoomLevel * 100)}%
            </span>
            <button
              onClick={() => setZoomLevel(Math.min(2, zoomLevel + 0.25))}
              className="p-2 hover:bg-white rounded-md transition-colors"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setCurrentDate(subMonths(currentDate, 1))}
              className="p-2 hover:bg-white rounded-md transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm font-medium text-gray-700 w-32 text-center">
              {format(currentDate, 'yyyy年 M月', { locale: zhCN })}
            </span>
            <button
              onClick={() => setCurrentDate(addMonths(currentDate, 1))}
              className="p-2 hover:bg-white rounded-md transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-3">
        <Layers className="w-5 h-5 text-blue-500 flex-shrink-0" />
        <div className="text-sm text-blue-700">
          <span className="font-medium">时间槽分配模式：</span>
          自动检测任务时间重叠，重叠的任务分配到不同行避免遮挡。
          {totalRows > 1 && (
            <span className="ml-2">
              共 {totalRows} 行，最多 {Math.max(...Array.from(tasksByRow.values()).map(arr => arr.length))} 个任务在同一时间重叠
            </span>
          )}
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="flex overflow-hidden">
          <div
            className="flex-shrink-0 border-r border-gray-200 bg-gray-50"
            style={{ width: '280px' }}
          >
            <div
              className="flex items-center justify-between px-4 font-medium text-gray-600 text-sm border-b border-gray-200"
              style={{ height: `${headerHeight}px` }}
            >
              <span>任务</span>
              <span className="text-xs text-gray-400">按时间排序</span>
            </div>
            <div style={{ height: `${totalRows * rowHeight}px` }}>
              {Array.from(tasksByRow.entries())
                .sort(([a], [b]) => a - b)
                .map(([rowIndex, rowTasks]) => (
                  <div
                    key={rowIndex}
                    className="relative border-b border-gray-100"
                    style={{ height: `${rowHeight}px` }}
                  >
                    {rowTasks.map((task, taskIndex) => {
                      const dateRange = getTaskDateRange(task);
                      const isHovered = hoveredTask === task._id;
                      return (
                        <div
                          key={task._id}
                          onClick={() => selectTask(task)}
                          onMouseEnter={() => setHoveredTask(task._id)}
                          onMouseLeave={() => setHoveredTask(null)}
                          className={`absolute left-0 right-0 flex items-center px-4 cursor-pointer transition-colors
                            ${isHovered ? 'bg-gray-100' : 'hover:bg-gray-50'}
                            ${taskIndex > 0 ? 'border-t border-dashed border-gray-200' : ''}`}
                          style={{
                            top: `${taskIndex * (taskBarHeight + rowGap / 2)}px`,
                            height: `${taskBarHeight}px`,
                          }}
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <div
                                className={`w-2 h-2 rounded-full ${getStatusColor(
                                  task.status as TaskStatus
                                )}`}
                              />
                              <span className="font-medium text-gray-900 text-sm truncate">
                                {task.title}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span
                                className={`${getPriorityColor(
                                  task.priority
                                )} text-white text-xs px-1.5 py-0.5 rounded`}
                              >
                                {priorityLabels[task.priority]}
                              </span>
                              <span className="text-xs text-gray-400">
                                {formatDate(dateRange.start)} → {formatDate(dateRange.end)}
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))}
            </div>
          </div>

          <div className="flex-1 overflow-x-auto">
            <div style={{ minWidth: `${days.length * dayWidth}px` }}>
              <div
                className="flex border-b border-gray-200 bg-gray-50 sticky top-0"
                style={{ height: `${headerHeight}px` }}
              >
                {days.map((day, index) => (
                  <div
                    key={index}
                    className={`flex-shrink-0 flex flex-col items-center justify-center border-r border-gray-100 ${
                      isToday(day) ? 'bg-primary-50' : ''
                    }`}
                    style={{ width: `${dayWidth}px` }}
                  >
                    <span className="text-xs text-gray-500">
                      {format(day, 'EEE', { locale: zhCN })}
                    </span>
                    <span
                      className={`text-lg font-semibold ${
                        isToday(day) ? 'text-primary-600' : 'text-gray-700'
                      }`}
                    >
                      {format(day, 'd')}
                    </span>
                    {index === 0 && (
                      <span className="text-xs text-gray-400">
                        {format(day, 'MMM', { locale: zhCN })}
                      </span>
                    )}
                  </div>
                ))}
              </div>

              <div
                className="relative"
                style={{ height: `${totalRows * rowHeight}px` }}
              >
                {Array.from({ length: totalRows }).map((_, rowIndex) => (
                  <div
                    key={rowIndex}
                    className="absolute left-0 right-0 border-b border-gray-100"
                    style={{
                      top: `${rowIndex * rowHeight}px`,
                      height: `${rowHeight}px`,
                    }}
                  >
                    {days.map((_, dayIndex) => (
                      <div
                        key={dayIndex}
                        className="absolute top-0 bottom-0 border-r border-gray-50"
                        style={{
                          left: `${dayIndex * dayWidth}px`,
                          width: `${dayWidth}px`,
                        }}
                      />
                    ))}
                  </div>
                ))}

                {taskLayouts.map((layout) => {
                  const isHovered = hoveredTask === layout.task._id;
                  return (
                    <div
                      key={layout.task._id}
                      onClick={() => selectTask(layout.task)}
                      onMouseEnter={() => setHoveredTask(layout.task._id)}
                      onMouseLeave={() => setHoveredTask(null)}
                      className={`absolute rounded-lg shadow-sm cursor-pointer transition-all duration-200 overflow-hidden
                        ${
                          layout.task.status === 'done'
                            ? 'bg-gradient-to-r from-green-400 to-green-500'
                            : layout.task.status === 'in-progress'
                            ? 'bg-gradient-to-r from-amber-400 to-amber-500'
                            : 'bg-gradient-to-r from-gray-400 to-gray-500'
                        }
                        ${isHovered ? 'shadow-lg scale-y-105 z-10' : 'hover:shadow-md'}`}
                      style={{
                        left: `${layout.left}px`,
                        top: `${layout.row * rowHeight + (rowHeight - taskBarHeight) / 2}px`,
                        width: `${Math.max(layout.width, 60)}px`,
                        height: `${taskBarHeight}px`,
                      }}
                    >
                      <div className="h-full px-3 flex items-center">
                        <span className="text-white text-sm font-medium truncate">
                          {layout.task.title}
                        </span>
                      </div>
                      {isHovered && (
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg whitespace-nowrap z-20">
                          <div className="font-medium">{layout.task.title}</div>
                          <div className="text-gray-300 mt-1">
                            {formatDate(layout.startDate)} → {formatDate(layout.endDate)}
                          </div>
                          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 w-2 h-2 bg-gray-900 rotate-45" />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {tasks.length === 0 && (
          <div className="text-center py-16">
            <Calendar className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">暂无任务</p>
            <p className="text-gray-400 text-sm mt-1">创建任务后可在甘特图中查看</p>
          </div>
        )}
      </div>

      <div className="mt-6 flex items-center justify-center gap-8">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-gray-400" />
          <span className="text-sm text-gray-600">待办</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-amber-500" />
          <span className="text-sm text-gray-600">进行中</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-green-500" />
          <span className="text-sm text-gray-600">已完成</span>
        </div>
        <div className="flex items-center gap-2 border-l border-gray-200 pl-8 ml-4">
          <Layers className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-600">时间槽自动分配</span>
        </div>
      </div>
    </div>
  );
}
