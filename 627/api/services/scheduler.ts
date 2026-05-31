import cron from 'node-cron';
import type { ScheduledTask } from '../../shared/types.js';
import { tasksRepository, rulesRepository, executionsRepository, issuesRepository } from '../db/repositories.js';
import { executeRules } from './ruleEngine.js';

const runningTasks = new Map<string, cron.ScheduledTask>();

export function startScheduledTask(task: ScheduledTask): void {
  if (!task.enabled && runningTasks.has(task.id)) {
    const cronTask = runningTasks.get(task.id)!;
    cronTask.stop();
    runningTasks.delete(task.id);
    return;
  }

  if (!task.enabled) return;

  try {
    const cronTask = cron.schedule(task.cronExpression, () => {
      void runTaskExecution(task);
    });
    runningTasks.set(task.id, cronTask);
  } catch (error) {
    console.error(`Failed to schedule task ${task.id}:`, error);
  }
}

export async function runTaskExecution(task: ScheduledTask): Promise<void> {
  console.log(`Starting task execution: ${task.name}`);

  const startTime = new Date();
  const execution = executionsRepository.create({
    taskId: task.id,
    taskName: task.name,
    status: 'running',
    startTime: startTime.toISOString(),
    totalRecords: 0,
    failedRecords: 0,
    qualityScore: 100,
  });

  try {
    const rules = rulesRepository.getAll().filter(r => task.ruleIds.includes(r.id));

    const { results, totalRecords, failedRecords, qualityScore } = executeRules(rules);

    results.forEach(result => {
      result.issues.forEach(issue => {
        issuesRepository.create({
          ...issue,
          executionId: execution.id,
          status: 'open',
          priority: failedRecords > 10 ? 'high' : failedRecords > 0 ? 'medium' : 'low',
        });
      });
    });

    executionsRepository.update(execution.id, {
      status: 'success',
      endTime: new Date().toISOString(),
      totalRecords,
      failedRecords,
      qualityScore,
    });

    tasksRepository.updateLastRun(task.id, startTime);

    console.log(`Task ${task.name} completed. Score: ${qualityScore}%`);
  } catch (error) {
    console.error(`Task ${task.name} failed:`, error);
    executionsRepository.update(execution.id, {
      status: 'failed',
      endTime: new Date().toISOString(),
    });
  }
}

export function initializeScheduler(): void {
  const tasks = tasksRepository.getAll();
  tasks.forEach(task => {
    startScheduledTask(task);
  });
  console.log(`Scheduler initialized with ${tasks.length} tasks`);
}

export function stopAllTasks(): void {
  runningTasks.forEach(task => task.stop());
  runningTasks.clear();
}

export function restartTask(task: ScheduledTask): void {
  stopTask(task.id);
  startScheduledTask(task);
}

export function stopTask(taskId: string): void {
  if (runningTasks.has(taskId)) {
    const cronTask = runningTasks.get(taskId)!;
    cronTask.stop();
    runningTasks.delete(taskId);
  }
}
