const { parentPort, workerData } = require('worker_threads');
const crypto = require('crypto');
const fs = require('fs');

const CHUNK_SIZE = 64 * 1024;

async function calculateSHA256(filePath) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    const stream = fs.createReadStream(filePath, { highWaterMark: CHUNK_SIZE });
    let processed = 0;
    let lastProgress = 0;
    
    stream.on('data', (chunk) => {
      hash.update(chunk);
      processed += chunk.length;
      
      const progress = Math.floor((processed / stream.bytesRead) * 100);
      if (progress - lastProgress >= 10) {
        lastProgress = progress;
        parentPort.postMessage({
          type: 'progress',
          filePath,
          progress
        });
      }
    });
    
    stream.on('end', () => {
      const digest = hash.digest('hex');
      resolve(digest);
    });
    
    stream.on('error', reject);
  });
}

async function calculateSHA256ForFiles(filePaths) {
  const results = {};
  
  for (let i = 0; i < filePaths.length; i++) {
    const filePath = filePaths[i];
    try {
      const hash = await calculateSHA256(filePath);
      results[filePath] = {
        success: true,
        hash
      };
      
      parentPort.postMessage({
        type: 'file-complete',
        filePath,
        hash,
        index: i,
        total: filePaths.length
      });
    } catch (error) {
      results[filePath] = {
        success: false,
        error: error.message
      };
      
      parentPort.postMessage({
        type: 'file-error',
        filePath,
        error: error.message,
        index: i,
        total: filePaths.length
      });
    }
  }
  
  return results;
}

parentPort.on('message', async (message) => {
  try {
    if (message.type === 'calculate-single') {
      const hash = await calculateSHA256(message.filePath);
      parentPort.postMessage({
        type: 'single-result',
        filePath: message.filePath,
        hash
      });
    } else if (message.type === 'calculate-batch') {
      const results = await calculateSHA256ForFiles(message.filePaths);
      parentPort.postMessage({
        type: 'batch-result',
        results
      });
    }
  } catch (error) {
    parentPort.postMessage({
      type: 'error',
      error: error.message
    });
  }
});

if (workerData && workerData.filePath) {
  calculateSHA256(workerData.filePath)
    .then(hash => {
      parentPort.postMessage({
        type: 'single-result',
        filePath: workerData.filePath,
        hash
      });
    })
    .catch(error => {
      parentPort.postMessage({
        type: 'error',
        error: error.message
      });
    });
}
