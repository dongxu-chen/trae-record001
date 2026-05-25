import { Task, WorkloadStats, Priority } from '@/types';
import { differenceInHours, differenceInDays, isWithinInterval, subDays, startOfDay, endOfDay } from 'date-fns';

export const getPriorityPoints = (priority: Priority): number => {
  const points: Record<Priority, number> = {
    'low': 1,
    'medium': 2,
    'high': 4,
    'urgent': 8,
  };
  return points[priority] || 1;
};

export const calculateWorkloadStats = (tasks: Task[], days: number = 30): WorkloadStats[] => {
  const assignees = [...new Set(tasks.map(t => t.assignee).filter(Boolean)];
  
  const now = new Date();
  const periodStart = subDays(now, days);

  return assignees.map(assignee => {
    const assigneeTasks = tasks.filter(t => t.assignee === assignee);
    const completedTasks = assigneeTasks.filter(t => 
      t.status === 'done' && 
      new Date(t.updatedAt) >= periodStart
    );
    const inProgressTasks = assigneeTasks.filter(t => t.status === 'in-progress');
    const todoTasks = assigneeTasks.filter(t => t.status === 'todo');

    const totalPoints = completedTasks.reduce((sum, t) => sum + getPriorityPoints(t.priority), 0);
    
    let totalCompletionTime = 0;
    completedTasks.forEach(task => {
      if (task.startDate && task.updatedAt) {
        const timeSpent = differenceInHours(new Date(task.updatedAt), new Date(task.startDate || task.createdAt));
        totalCompletionTime += Math.max(0, timeSpent);
      }
    });

    return {
      assignee: assignee!,
      totalTasks: assigneeTasks.length,
      completedTasks: completedTasks.length,
      inProgressTasks: inProgressTasks.length,
      todoTasks: todoTasks.length,
      completionRate: assigneeTasks.length > 0 
        ? Math.round((completedTasks.length / assigneeTasks.length) * 100) 
        : 0,
      averageCompletionTime: completedTasks.length > 0 
        ? Math.round(totalCompletionTime / completedTasks.length) 
        : 0,
      points: totalPoints,
    };
  }).sort((a, b) => b.points - a.points);
};

export const getTaskStatsForPeriod = (tasks: Task[], startDate: Date, endDate: Date) => {
  return tasks.filter(task => 
    isWithinInterval(new Date(task.createdAt), {
      start: startOfDay(startDate),
      end: endOfDay(endDate),
    })
  );
};

export const generateEfficiencyReport = (tasks: Task[]) => {
  const stats = calculateWorkloadStats(tasks);
  
  const totalCompleted = tasks.filter(t => t.status === 'done').length;
  const totalInProgress = tasks.filter(t => t.status === 'in-progress').length;
  const totalTodo = tasks.filter(t => t.status === 'todo').length;
  const totalPoints = tasks
    .filter(t => t.status === 'done')
    .reduce((sum, t) => sum + getPriorityPoints(t.priority), 0);

  return {
    overview: {
      totalTasks: tasks.length,
      completedTasks: totalCompleted,
      inProgressTasks: totalInProgress,
      todoTasks: totalTodo,
      completionRate: tasks.length > 0 ? Math.round((totalCompleted / tasks.length) * 100 : 0,
      totalPoints,
    },
    byAssignee: stats,
    topPerformers: stats.slice(0, 3),
    needsAttention: stats.filter(s => s.completionRate < 50 && s.totalTasks > 0),
  };
};

export const getDailyTrend = (tasks: Task[], days: number = 14) => {
  const trend = [];
  const now = new Date();

  for (let i = days - 1; i >= 0; i--) {
    const date = subDays(now, i);
    const dayStart = startOfDay(date);
    const dayEnd = endOfDay(date);

    const dayTasks = tasks.filter(t => 
      isWithinInterval(new Date(t.createdAt), { start: dayStart, end: dayEnd })
    );
    const completed = dayTasks.filter(t => t.status === 'done').length;
    const points = dayTasks
      .filter(t => t.status === 'done')
      .reduce((sum, t) => sum + getPriorityPoints(t.priority), 0);

    trend.push({
      date: dayStart.toISOString(),
      created: dayTasks.length,
      completed,
      points,
    });
  }

  return trend;
};

export const formatDuration = (hours: number): string => {
  if (hours < 24) {
    return `${hours} 小时`;
  }
  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;
  if (remainingHours === 0) {
    return `${days} 天`;
  }
  return `${days} 天 ${remainingHours} 小时`;
};
