const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { Worker } = require('worker_threads');

class HashCalculator {
  constructor() {
    this.worker = null;
    this.pendingRequests = new Map();
    this.requestId = 0;
  }

  async calculateSHA256(filePath) {
    return new Promise((resolve, reject) => {
      const id = this.requestId++;
      this.pendingRequests.set(id, { resolve, reject });

      if (!this.worker) {
        this.worker = new Worker(path.join(__dirname, '../workers/HashWorker.js'));
        
        this.worker.on('message', (message) => {
          if (message.type === 'single-result') {
            const req = this.pendingRequests.get(id);
            if (req) {
              req.resolve(message.hash);
              this.pendingRequests.delete(id);
            }
          } else if (message.type === 'error') {
            const req = this.pendingRequests.get(id);
            if (req) {
              req.reject(new Error(message.error));
              this.pendingRequests.delete(id);
            }
          }
        });

        this.worker.on('error', (error) => {
          const req = this.pendingRequests.get(id);
          if (req) {
            req.reject(error);
            this.pendingRequests.delete(id);
          }
        });
      }

      this.worker.postMessage({
        type: 'calculate-single',
        filePath
      });
    });
  }

  async calculateBatch(filePaths) {
    return new Promise((resolve, reject) => {
      const id = this.requestId++;
      this.pendingRequests.set(id, { resolve, reject });

      if (!this.worker) {
        this.worker = new Worker(path.join(__dirname, '../workers/HashWorker.js'));
      }

      this.worker.on('message', (message) => {
        if (message.type === 'batch-result') {
          const req = this.pendingRequests.get(id);
          if (req) {
            req.resolve(message.results);
            this.pendingRequests.delete(id);
          }
        } else if (message.type === 'file-complete') {
          // Progress callback can be added here
        }
      });

      this.worker.postMessage({
        type: 'calculate-batch',
        filePaths
      });
    });
  }

  terminate() {
    if (this.worker) {
      this.worker.terminate();
      this.worker = null;
    }
  }
}

const hashCalculator = new HashCalculator();

class FileUtils {
  static async calculateChecksum(filePath, algorithm = 'md5') {
    return new Promise((resolve, reject) => {
      const hash = crypto.createHash(algorithm);
      const stream = fs.createReadStream(filePath);
      
      stream.on('data', (data) => {
        hash.update(data);
      });
      
      stream.on('end', () => {
        resolve(hash.digest('hex'));
      });
      
      stream.on('error', reject);
    });
  }

  static async calculateSHA256(filePath) {
    return await hashCalculator.calculateSHA256(filePath);
  }

  static async calculateBatchSHA256(filePaths) {
    return await hashCalculator.calculateBatch(filePaths);
  }

  static async walkDirectory(dir, baseDir = null) {
    const results = [];
    const rootDir = baseDir || dir;
    
    const items = await fs.promises.readdir(dir, { withFileTypes: true });
    
    for (const item of items) {
      const fullPath = path.join(dir, item.name);
      const relativePath = path.relative(rootDir, fullPath);
      
      if (item.isDirectory()) {
        const subResults = await this.walkDirectory(fullPath, rootDir);
        results.push(...subResults);
      } else if (item.isFile()) {
        const stats = await fs.promises.stat(fullPath);
        results.push({
          path: relativePath.replace(/\\/g, '/'),
          fullPath,
          size: stats.size,
          mtime: stats.mtime.getTime(),
          isDirectory: false
        });
      }
    }
    
    return results;
  }

  static async getFileInfo(filePath, baseDir) {
    const stats = await fs.promises.stat(filePath);
    const relativePath = path.relative(baseDir, filePath).replace(/\\/g, '/');
    
    return {
      path: relativePath,
      fullPath: filePath,
      size: stats.size,
      mtime: stats.mtime.getTime(),
      isDirectory: stats.isDirectory()
    };
  }

  static async ensureDirectory(dirPath) {
    try {
      await fs.promises.access(dirPath);
    } catch {
      await fs.promises.mkdir(dirPath, { recursive: true });
    }
  }

  static async ensureFileDirectory(filePath) {
    const dir = path.dirname(filePath);
    await this.ensureDirectory(dir);
  }

  static async deleteFile(filePath) {
    try {
      await fs.promises.unlink(filePath);
      return true;
    } catch (error) {
      if (error.code === 'ENOENT') {
        return true;
      }
      throw error;
    }
  }

  static async fileExists(filePath) {
    try {
      await fs.promises.access(filePath);
      return true;
    } catch {
      return false;
    }
  }

  static async getFileSize(filePath) {
    const stats = await fs.promises.stat(filePath);
    return stats.size;
  }

  static formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  static normalizePath(filePath) {
    return filePath.replace(/\\/g, '/');
  }

  static joinPath(...parts) {
    return path.join(...parts).replace(/\\/g, '/');
  }
}

module.exports = FileUtils;
