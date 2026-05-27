import type { WorkerMessage, WorkerResponse, CleaningResult, CleaningRules } from '../types';
import { processDataCleaning } from '../utils/dataProcessor';
import { calculateDatasetStats } from '../utils/statistics';
import { generatePythonScript } from '../utils/scriptGenerator';

let currentData: any[][] = [];
let currentColumns: string[] = [];
let isCancelled = false;

self.onmessage = function (e: MessageEvent<WorkerMessage>) {
  const message = e.data;

  switch (message.type) {
    case 'INIT':
      handleInit(message.payload.data, message.payload.columns);
      break;
    case 'CLEAN':
      handleClean(message.payload.rules);
      break;
    case 'CANCEL':
      isCancelled = true;
      break;
    case 'GET_STATS':
      sendStats();
      break;
  }
};

function handleInit(data: any[][], columns: string[]) {
  currentData = data;
  currentColumns = columns;
  isCancelled = false;
  sendStats();
}

function sendStats() {
  if (currentData.length === 0) return;
  const stats = calculateDatasetStats(currentData, currentColumns);
  const response: WorkerResponse = {
    type: 'STATS',
    payload: stats,
  };
  self.postMessage(response);
}

async function handleClean(rules: CleaningRules) {
  isCancelled = false;
  const startTime = Date.now();

  try {
    const beforeStats = calculateDatasetStats(currentData, currentColumns);

    const onProgress = (step: string, progress: number) => {
      if (isCancelled) {
        throw new Error('清洗已取消');
      }
      const response: WorkerResponse = {
        type: 'PROGRESS',
        payload: { step, progress, message: `正在${step}...` },
      };
      self.postMessage(response);
    };

    const { data, changes, logs } = await processDataCleaning(
      currentData,
      currentColumns,
      rules,
      onProgress
    );

    if (isCancelled) {
      throw new Error('清洗已取消');
    }

    const stats = calculateDatasetStats(data, currentColumns);
    const script = generatePythonScript(rules, currentColumns, beforeStats.columns);

    const duration = (Date.now() - startTime) / 1000;

    const result: CleaningResult = {
      success: true,
      data,
      columns: currentColumns,
      stats,
      beforeStats,
      changes,
      script,
      logs,
      duration,
    };

    const response: WorkerResponse = {
      type: 'COMPLETE',
      payload: result,
    };
    self.postMessage(response);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '清洗过程中发生错误';
    const response: WorkerResponse = {
      type: 'ERROR',
      payload: errorMessage,
    };
    self.postMessage(response);
  }
}

export {};
