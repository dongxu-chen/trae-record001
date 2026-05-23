const axios = require('axios');
const fs = require('fs');
const path = require('path');
const FormData = require('form-data');

class CloudAPI {
  constructor() {
    this.baseURL = 'https://api.example.com';
    this.apiKey = null;
    this.timeout = 30000;
  }

  configure(config) {
    if (config.baseURL) {
      this.baseURL = config.baseURL;
    }
    if (config.apiKey) {
      this.apiKey = config.apiKey;
    }
    if (config.timeout) {
      this.timeout = config.timeout;
    }
  }

  getHeaders() {
    const headers = {
      'Content-Type': 'application/json'
    };
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }
    return headers;
  }

  async request(method, endpoint, data = null, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      method,
      url,
      headers: this.getHeaders(),
      timeout: this.timeout,
      ...options
    };

    if (data && method !== 'get') {
      config.data = data;
    }

    try {
      const response = await axios(config);
      return response.data;
    } catch (error) {
      if (error.response) {
        throw new Error(`API Error: ${error.response.status} - ${error.response.data?.message || error.message}`);
      } else if (error.request) {
        throw new Error('Network Error: No response received');
      } else {
        throw new Error(`Request Error: ${error.message}`);
      }
    }
  }

  async testConnection() {
    return await this.request('get', '/health');
  }

  async getFileList() {
    return await this.request('get', '/files');
  }

  async getFileMetadata(filePath) {
    return await this.request('get', `/files/metadata?path=${encodeURIComponent(filePath)}`);
  }

  async getBatchMetadata(filePaths) {
    return await this.request('post', '/files/batch-metadata', { filePaths });
  }

  async downloadFile(filePath, localPath, options = {}) {
    const { onProgress, startByte = 0 } = options;
    
    const url = `${this.baseURL}/files/download?path=${encodeURIComponent(filePath)}`;
    const headers = this.getHeaders();
    
    if (startByte > 0) {
      headers['Range'] = `bytes=${startByte}-`;
    }

    const response = await axios({
      method: 'get',
      url,
      headers,
      responseType: 'stream',
      timeout: this.timeout
    });

    const totalSize = parseInt(response.headers['content-length'] || '0', 10);
    const fileSize = startByte + totalSize;
    
    const writer = fs.createWriteStream(localPath, { flags: startByte > 0 ? 'a' : 'w' });
    let downloaded = startByte;

    return new Promise((resolve, reject) => {
      response.data.on('data', (chunk) => {
        downloaded += chunk.length;
        if (onProgress) {
          onProgress({
            filePath,
            downloaded,
            total: fileSize,
            progress: fileSize > 0 ? (downloaded / fileSize) * 100 : 0
          });
        }
      });

      response.data.pipe(writer);

      writer.on('finish', () => {
        resolve({
          success: true,
          filePath,
          localPath,
          size: downloaded
        });
      });

      writer.on('error', reject);
      response.data.on('error', reject);
    });
  }

  async uploadFile(localPath, filePath, options = {}) {
    const { onProgress, startByte = 0 } = options;
    const fileSize = fs.statSync(localPath).size;
    
    const url = `${this.baseURL}/files/upload`;
    const formData = new FormData();
    
    const fileStream = fs.createReadStream(localPath, { start: startByte });
    formData.append('file', fileStream, { filename: path.basename(filePath) });
    formData.append('path', filePath);
    formData.append('startByte', startByte.toString());

    const response = await axios.post(url, formData, {
      headers: {
        ...this.getHeaders(),
        'Content-Type': 'multipart/form-data'
      },
      timeout: this.timeout,
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const uploaded = startByte + (progressEvent.loaded || 0);
          onProgress({
            filePath,
            uploaded,
            total: fileSize,
            progress: fileSize > 0 ? (uploaded / fileSize) * 100 : 0
          });
        }
      }
    });

    return response.data;
  }

  async getUploadStatus(filePath) {
    return await this.request('get', `/files/upload-status?path=${encodeURIComponent(filePath)}`);
  }

  async deleteFile(filePath) {
    return await this.request('delete', `/files?path=${encodeURIComponent(filePath)}`);
  }

  async createFolder(folderPath) {
    return await this.request('post', '/folders', { path: folderPath });
  }

  async deleteFolder(folderPath) {
    return await this.request('delete', `/folders?path=${encodeURIComponent(folderPath)}`);
  }

  async getFileChecksum(filePath) {
    return await this.request('get', `/files/checksum?path=${encodeURIComponent(filePath)}`);
  }

  async getBatchChecksums(filePaths) {
    return await this.request('post', '/files/batch-checksum', { filePaths });
  }

  async uploadChunk(localPath, filePath, options = {}) {
    const { chunkIndex, startByte, endByte, totalChunks, fileSize, onProgress } = options;
    
    const url = `${this.baseURL}/files/upload-chunk`;
    const chunkSize = endByte - startByte;
    
    const fileHandle = await fs.promises.open(localPath, 'r');
    const buffer = Buffer.alloc(chunkSize);
    const { bytesRead } = await fileHandle.read(buffer, 0, chunkSize, startByte);
    await fileHandle.close();
    
    const chunkData = buffer.slice(0, bytesRead);
    
    const formData = new FormData();
    formData.append('chunk', chunkData, { filename: `chunk_${chunkIndex}` });
    formData.append('path', filePath);
    formData.append('chunkIndex', chunkIndex.toString());
    formData.append('startByte', startByte.toString());
    formData.append('endByte', endByte.toString());
    formData.append('totalChunks', totalChunks.toString());
    formData.append('fileSize', fileSize.toString());
    
    const response = await axios.post(url, formData, {
      headers: {
        ...this.getHeaders(),
        ...formData.getHeaders()
      },
      timeout: this.timeout,
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const chunkProgress = progressEvent.total > 0 
            ? (progressEvent.loaded / progressEvent.total) * 100 
            : 0;
          onProgress({
            chunkIndex,
            chunkProgress,
            uploaded: startByte + progressEvent.loaded,
            total: fileSize
          });
        }
      }
    });
    
    return response.data;
  }

  async completeUpload(filePath, options = {}) {
    const { fileSize, sha256, totalChunks } = options;
    return await this.request('post', '/files/complete-upload', {
      path: filePath,
      fileSize,
      sha256,
      totalChunks
    });
  }

  async downloadChunk(filePath, options = {}) {
    const { startByte, endByte, chunkIndex, totalChunks, onProgress } = options;
    
    const url = `${this.baseURL}/files/download-chunk`;
    const headers = {
      ...this.getHeaders(),
      'Range': `bytes=${startByte}-${endByte}`
    };
    
    const params = new URLSearchParams({
      path: filePath,
      startByte: startByte.toString(),
      endByte: endByte.toString()
    });
    
    const response = await axios({
      method: 'get',
      url: `${url}?${params.toString()}`,
      headers,
      responseType: 'arraybuffer',
      timeout: this.timeout,
      onDownloadProgress: (progressEvent) => {
        if (onProgress) {
          const chunkProgress = progressEvent.total > 0 
            ? (progressEvent.loaded / progressEvent.total) * 100 
            : 0;
          onProgress({
            chunkIndex,
            chunkProgress,
            downloaded: startByte + progressEvent.loaded
          });
        }
      }
    });
    
    return Buffer.from(response.data);
  }

  async getChunkStatus(filePath) {
    return await this.request('get', `/files/chunk-status?path=${encodeURIComponent(filePath)}`);
  }
}

module.exports = CloudAPI;
