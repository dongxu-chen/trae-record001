import http from 'http';

class ConfigRegistry {
  constructor(options = {}) {
    this.type = options.type || 'consul';
    this.host = options.host || 'localhost';
    this.port = options.port || (this.type === 'consul' ? 8500 : 2181);
    this.basePath = options.basePath || '/config';
    this.timeout = options.timeout || 5000;
    this.token = options.token || process.env.CONSUL_TOKEN;
    this.client = null;
  }

  async connect() {
    if (this.type === 'consul') {
      return this.connectConsul();
    } else if (this.type === 'zookeeper') {
      return this.connectZooKeeper();
    }
    throw new Error(`不支持的配置中心类型: ${this.type}`);
  }

  async connectConsul() {
    try {
      await this.httpRequest('/v1/status/leader', 'GET');
      this.client = 'consul';
      return true;
    } catch (error) {
      throw new Error(`连接Consul失败: ${error.message}`);
    }
  }

  async connectZooKeeper() {
    this.client = 'zookeeper-mock';
    console.warn('ZooKeeper 使用 mock 模式，实际使用请安装 node-zookeeper-client');
    return true;
  }

  async push(key, value, options = {}) {
    const configValue = typeof value === 'object' ? JSON.stringify(value) : String(value);
    
    if (this.type === 'consul') {
      return this.pushConsul(key, configValue, options);
    } else if (this.type === 'zookeeper') {
      return this.pushZooKeeper(key, configValue, options);
    }
    throw new Error(`不支持的配置中心类型: ${this.type}`);
  }

  async pushConsul(key, value, options = {}) {
    const path = `/v1/kv${this.basePath}/${key}`;
    const headers = {};
    
    if (this.token) {
      headers['X-Consul-Token'] = this.token;
    }

    await this.httpRequest(path, 'PUT', {
      headers,
      body: value
    });

    return { success: true, key: `${this.basePath}/${key}`, backend: 'consul' };
  }

  async pushZooKeeper(key, value, options = {}) {
    const path = `${this.basePath}/${key}`;
    
    console.log(`[ZooKeeper Mock] 推送配置: ${path}`);
    return { success: true, key: path, backend: 'zookeeper' };
  }

  async pushObject(config, prefix = '') {
    const results = [];
    const errors = [];

    const flatten = (obj, path = '') => {
      const items = [];
      for (const [key, value] of Object.entries(obj)) {
        const fullPath = path ? `${path}.${key}` : key;
        if (value && typeof value === 'object' && !Array.isArray(value)) {
          items.push(...flatten(value, fullPath));
        } else {
          items.push({ key: fullPath, value });
        }
      }
      return items;
    };

    const items = flatten(config, prefix);

    for (const item of items) {
      try {
        const result = await this.push(item.key, item.value);
        results.push(result);
      } catch (error) {
        errors.push({ key: item.key, error: error.message });
      }
    }

    return {
      success: errors.length === 0,
      pushed: results,
      failed: errors
    };
  }

  async get(key, options = {}) {
    if (this.type === 'consul') {
      return this.getConsul(key, options);
    } else if (this.type === 'zookeeper') {
      return this.getZooKeeper(key, options);
    }
    throw new Error(`不支持的配置中心类型: ${this.type}`);
  }

  async getConsul(key, options = {}) {
    const path = `/v1/kv${this.basePath}/${key}`;
    const headers = {};
    
    if (this.token) {
      headers['X-Consul-Token'] = this.token;
    }

    const response = await this.httpRequest(path, 'GET', { headers });
    
    if (Array.isArray(response) && response[0] && response[0].Value) {
      const value = Buffer.from(response[0].Value, 'base64').toString();
      try {
        return JSON.parse(value);
      } catch {
        return value;
      }
    }

    return null;
  }

  async getZooKeeper(key, options = {}) {
    const path = `${this.basePath}/${key}`;
    console.log(`[ZooKeeper Mock] 获取配置: ${path}`);
    return null;
  }

  async delete(key) {
    if (this.type === 'consul') {
      const path = `/v1/kv${this.basePath}/${key}`;
      const headers = {};
      if (this.token) {
        headers['X-Consul-Token'] = this.token;
      }
      await this.httpRequest(path, 'DELETE', { headers });
      return { success: true, key: `${this.basePath}/${key}` };
    }
    throw new Error(`不支持的配置中心类型: ${this.type}`);
  }

  async list(prefix = '') {
    if (this.type === 'consul') {
      const path = `/v1/kv${this.basePath}/${prefix}?keys`;
      const headers = {};
      if (this.token) {
        headers['X-Consul-Token'] = this.token;
      }
      return await this.httpRequest(path, 'GET', { headers });
    }
    throw new Error(`不支持的配置中心类型: ${this.type}`);
  }

  httpRequest(path, method = 'GET', options = {}) {
    return new Promise((resolve, reject) => {
      const req = http.request({
        hostname: this.host,
        port: this.port,
        path,
        method,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        timeout: this.timeout
      }, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            try {
              resolve(data ? JSON.parse(data) : null);
            } catch {
              resolve(data);
            }
          } else {
            reject(new Error(`HTTP ${res.statusCode}: ${data}`));
          }
        });
      });

      req.on('error', reject);
      req.on('timeout', () => {
        req.destroy();
        reject(new Error('请求超时'));
      });

      if (options.body) {
        req.write(typeof options.body === 'string' ? options.body : JSON.stringify(options.body));
      }
      req.end();
    });
  }

  disconnect() {
    this.client = null;
  }
}

export default ConfigRegistry;
