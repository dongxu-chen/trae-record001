import { Task } from '@/types';
import { differenceInDays, addDays, isSameDay } from 'date-fns';

export interface GanttTaskLayout {
  task: Task;
  row: number;
  left: number;
  width: number;
  startDate: Date;
  endDate: Date;
}

export interface CalendarSlot {
  date: Date;
  tasks: string[];
}

export const getTaskDateRange = (task: Task): { start: Date; end: Date } => {
  const start = task.startDate ? new Date(task.startDate) : new Date(task.createdAt);
  const end = task.dueDate ? new Date(task.dueDate) : addDays(start, 3);
  return { start, end };
};

export const tasksOverlap = (task1: Task, task2: Task): boolean => {
  const range1 = getTaskDateRange(task1);
  const range2 = getTaskDateRange(task2);
  
  return (
    range1.start <= range2.end &&
    range2.start <= range1.end
  );
};

export const assignTimeSlots = (tasks: Task[]): Map<string, number> => {
  const taskRowMap = new Map<string, number>();
  const rows: Task[][] = [];

  const sortedTasks = [...tasks].sort((a, b) => {
    const rangeA = getTaskDateRange(a);
    const rangeB = getTaskDateRange(b);
    return rangeA.start.getTime() - rangeB.start.getTime();
  });

  for (const task of sortedTasks) {
    let assignedRow = -1;

    for (let rowIndex = 0; rowIndex < rows.length; rowIndex++) {
      const row = rows[rowIndex];
      const canPlace = !row.some(existingTask => tasksOverlap(task, existingTask));
      
      if (canPlace) {
        assignedRow = rowIndex;
        row.push(task);
        break;
      }
    }

    if (assignedRow === -1) {
      assignedRow = rows.length;
      rows.push([task]);
    }

    taskRowMap.set(task._id, assignedRow);
  }

  return taskRowMap;
};

export const calculateGanttLayout = (
  tasks: Task[],
  viewStart: Date,
  dayWidth: number
): GanttTaskLayout[] => {
  const rowMap = assignTimeSlots(tasks);

  return tasks.map(task => {
    const { start, end } = getTaskDateRange(task);
    const daysFromStart = differenceInDays(start, viewStart);
    const duration = Math.max(differenceInDays(end, start), 1);

    return {
      task,
      row: rowMap.get(task._id) || 0,
      left: Math.max(daysFromStart, 0) * dayWidth,
      width: duration * dayWidth,
      startDate: start,
      endDate: end,
    };
  });
};

export const getMaxRows = (tasks: Task[]): number => {
  const rowMap = assignTimeSlots(tasks);
  const maxRow = Math.max(...Array.from(rowMap.values()), -1);
  return maxRow + 1;
};

export const generateCalendarSlots = (
  tasks: Task[],
  startDate: Date,
  endDate: Date
): CalendarSlot[] => {
  const slots: CalendarSlot[] = [];
  const days = differenceInDays(endDate, startDate);

  for (let i = 0; i <= days; i++) {
    const date = addDays(startDate, i);
    const dayTasks: string[] = [];

    for (const task of tasks) {
      const { start, end } = getTaskDateRange(task);
      const normalizedDate = new Date(date);
      normalizedDate.setHours(0, 0, 0, 0);
      const normalizedStart = new Date(start);
      normalizedStart.setHours(0, 0, 0, 0);
      const normalizedEnd = new Date(end);
      normalizedEnd.setHours(0, 0, 0, 0);

      if (normalizedDate >= normalizedStart && normalizedDate <= normalizedEnd) {
        dayTasks.push(task._id);
      }
    }

    slots.push({ date, tasks: dayTasks });
  }

  return slots;
};

export const getTaskRowCount = (tasks: Task[]): number => {
  const rowMap = assignTimeSlots(tasks);
  return Math.max(...Array.from(rowMap.values()), 0) + 1;
};
