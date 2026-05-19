const zookeeper = require('node-zookeeper-client');
const config = require('../config');
const CreateMode = zookeeper.CreateMode;
const Event = zookeeper.Event;

class ZooKeeperManager {
  constructor() {
    this.client = null;
    this.workerId = null;
    this.workerPath = null;
    this.basePath = config.zookeeper.basePath;
    this.workersPath = config.zookeeper.basePath + config.zookeeper.workerPath;
    this.maxWorkerId = config.snowflake.maxWorkerId;
    this.isConnected = false;
    this.isReconnecting = false;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 1000;
    this.onReconnectCallback = null;
  }
  
  connect() {
    return new Promise((resolve, reject) => {
      this.client = zookeeper.createClient(
        config.zookeeper.connectionString,
        {
          sessionTimeout: config.zookeeper.sessionTimeout,
          spinDelay: config.zookeeper.spinDelay,
          retries: config.zookeeper.retries
        }
      );
      
      this.setupEventListeners();
      
      this.client.once('connected', () => {
        console.log('ZooKeeper连接成功');
        this.isConnected = true;
        resolve();
      });
      
      this.client.once('error', (error) => {
        console.error('ZooKeeper连接失败:', error);
        this.isConnected = false;
        reject(error);
      });
      
      this.client.connect();
    });
  }
  
  setupEventListeners() {
    this.client.on('state', (state) => {
      console.log(`ZooKeeper状态变更: ${state}`);
      
      if (state === 'disconnected') {
        this.isConnected = false;
        console.log('ZooKeeper连接断开');
      } else if (state === 'syncConnected') {
        this.isConnected = true;
        console.log('ZooKeeper重新连接');
      } else if (state === 'expired') {
        this.isConnected = false;
        console.log('ZooKeeper会话过期，尝试重新连接并注册...');
        this.handleSessionExpired();
      }
    });
    
    this.client.on('error', (error) => {
      console.error('ZooKeeper错误:', error);
    });
  }
  
  async handleSessionExpired() {
    if (this.isReconnecting) {
      return;
    }
    
    this.isReconnecting = true;
    let attempts = 0;
    
    while (attempts < this.maxReconnectAttempts) {
      try {
        console.log(`尝试重新连接ZooKeeper (${attempts + 1}/${this.maxReconnectAttempts})...`);
        await this.reconnect();
        
        console.log('重新注册Worker ID...');
        const oldWorkerId = this.workerId;
        this.workerId = null;
        this.workerPath = null;
        
        await this.ensurePath(this.basePath);
        await this.ensurePath(this.workersPath);
        await this.acquireWorkerId();
        
        console.log(`会话恢复成功，旧Worker ID: ${oldWorkerId}, 新Worker ID: ${this.workerId}`);
        
        if (this.onReconnectCallback) {
          this.onReconnectCallback(this.workerId);
        }
        
        this.isReconnecting = false;
        return;
      } catch (error) {
        attempts++;
        console.error(`重连失败 (${attempts}/${this.maxReconnectAttempts}):`, error.message);
        
        if (attempts >= this.maxReconnectAttempts) {
          console.error('达到最大重连次数，服务退出');
          this.isReconnecting = false;
          process.exit(1);
        }
        
        await new Promise(resolve => setTimeout(resolve, this.reconnectDelay * attempts));
      }
    }
  }
  
  reconnect() {
    return new Promise((resolve, reject) => {
      this.client.close();
      
      this.client = zookeeper.createClient(
        config.zookeeper.connectionString,
        {
          sessionTimeout: config.zookeeper.sessionTimeout,
          spinDelay: config.zookeeper.spinDelay,
          retries: config.zookeeper.retries
        }
      );
      
      this.setupEventListeners();
      
      this.client.once('connected', () => {
        console.log('ZooKeeper重连成功');
        this.isConnected = true;
        resolve();
      });
      
      this.client.once('error', (error) => {
        this.isConnected = false;
        reject(error);
      });
      
      this.client.connect();
    });
  }
  
  async ensurePath(path) {
    return new Promise((resolve, reject) => {
      this.client.exists(path, (error, stat) => {
        if (error) return reject(error);
        if (stat) return resolve();
        
        this.client.mkdirp(path, (error) => {
          if (error) return reject(error);
          resolve();
        });
      });
    });
  }
  
  async getExistingWorkers() {
    return new Promise((resolve, reject) => {
      this.client.getChildren(this.workersPath, (error, children) => {
        if (error) return reject(error);
        
        const workerIds = children
          .map(child => {
            const match = child.match(/^worker-(\d+)$/);
            return match ? parseInt(match[1], 10) : null;
          })
          .filter(id => id !== null);
        
        resolve(workerIds);
      });
    });
  }
  
  findAvailableWorkerId(existingIds, excludeId = null) {
    const existingSet = new Set(existingIds);
    for (let i = 0; i <= this.maxWorkerId; i++) {
      if (!existingSet.has(i) && i !== excludeId) {
        return i;
      }
    }
    throw new Error('没有可用的workerID');
  }
  
  async registerWorker(workerId) {
    return new Promise((resolve, reject) => {
      const path = `${this.workersPath}/worker-${workerId}`;
      const data = Buffer.from(JSON.stringify({
        registeredAt: Date.now(),
        hostname: require('os').hostname()
      }));
      
      this.client.create(
        path,
        data,
        zookeeper.ACL.OPEN_ACL_UNSAFE,
        CreateMode.EPHEMERAL,
        (error, createdPath) => {
          if (error) return reject(error);
          this.workerPath = createdPath;
          console.log(`成功注册Worker ID: ${workerId}, 路径: ${createdPath}`);
          resolve(workerId);
        }
      );
    });
  }
  
  async acquireWorkerId() {
    await this.ensurePath(this.basePath);
    await this.ensurePath(this.workersPath);
    
    const maxRetries = 10;
    let retries = 0;
    
    while (retries < maxRetries) {
      try {
        const existingWorkers = await this.getExistingWorkers();
        const availableId = this.findAvailableWorkerId(existingWorkers);
        
        try {
          await this.registerWorker(availableId);
          this.workerId = availableId;
          return this.workerId;
        } catch (registerError) {
          if (registerError.getCode() === zookeeper.Exception.NODE_EXISTS) {
            console.log(`Worker ID ${availableId} 已被占用，重试...`);
            retries++;
            continue;
          }
          throw registerError;
        }
      } catch (error) {
        retries++;
        if (retries >= maxRetries) {
          throw error;
        }
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
    
    throw new Error('获取Worker ID失败，已达到最大重试次数');
  }
  
  async refreshWorkerId(oldWorkerId) {
    console.log(`主动刷新Worker ID，旧ID: ${oldWorkerId}`);
    
    const maxRetries = 5;
    let retries = 0;
    
    while (retries < maxRetries) {
      try {
        const existingWorkers = await this.getExistingWorkers();
        const availableId = this.findAvailableWorkerId(existingWorkers, oldWorkerId);
        
        try {
          await this.registerWorker(availableId);
          const newWorkerId = availableId;
          console.log(`成功刷新Worker ID: ${oldWorkerId} -> ${newWorkerId}`);
          return newWorkerId;
        } catch (registerError) {
          if (registerError.getCode() === zookeeper.Exception.NODE_EXISTS) {
            retries++;
            continue;
          }
          throw registerError;
        }
      } catch (error) {
        retries++;
        if (retries >= maxRetries) {
          throw error;
        }
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
    
    throw new Error('刷新Worker ID失败');
  }
  
  setOnReconnectCallback(callback) {
    this.onReconnectCallback = callback;
  }
  
  close() {
    if (this.client) {
      this.client.close();
      this.isConnected = false;
      console.log('ZooKeeper连接已关闭');
    }
  }
  
  getWorkerId() {
    return this.workerId;
  }
  
  getConnectionState() {
    return this.isConnected;
  }
}

module.exports = ZooKeeperManager;