class ConsulClient {
  constructor(options = {}) {
    this.host = options.host || 'localhost';
    this.port = options.port || 8500;
    this.protocol = options.protocol || 'http';
    this.serviceCache = new Map();
    this.lastRefresh = 0;
    this.refreshInterval = options.refreshInterval || 30000;
  }

  get baseUrl() {
    return `${this.protocol}://${this.host}:${this.port}/v1`;
  }

  async registerService(serviceDef) {
    const registration = {
      ID: serviceDef.id || serviceDef.name,
      Name: serviceDef.name,
      Address: serviceDef.address || 'localhost',
      Port: serviceDef.port,
      Tags: serviceDef.tags || [],
      Meta: serviceDef.meta || {},
      Check: serviceDef.check || {
        TCP: `${serviceDef.address || 'localhost'}:${serviceDef.port}`,
        Interval: '10s',
        Timeout: '5s',
      },
    };

    try {
      const response = await fetch(`${this.baseUrl}/agent/service/register`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(registration),
      });

      if (response.ok) {
        console.log(`✅ Service registered with Consul: ${serviceDef.name}`);
        return true;
      } else {
        console.error(`❌ Failed to register service: ${response.statusText}`);
        return false;
      }
    } catch (error) {
      console.warn('⚠️ Consul registration failed (running in standalone mode):', error.message);
      return false;
    }
  }

  async deregisterService(serviceId) {
    try {
      const response = await fetch(`${this.baseUrl}/agent/service/deregister/${serviceId}`, {
        method: 'PUT',
      });

      if (response.ok) {
        console.log(`✅ Service deregistered from Consul: ${serviceId}`);
        return true;
      }
      return false;
    } catch (error) {
      console.warn('⚠️ Consul deregistration failed:', error.message);
      return false;
    }
  }

  async discoverService(serviceName) {
    const now = Date.now();
    if (now - this.lastRefresh < this.refreshInterval && this.serviceCache.has(serviceName)) {
      return this.serviceCache.get(serviceName);
    }

    try {
      const response = await fetch(`${this.baseUrl}/health/service/${serviceName}?passing`);

      if (!response.ok) {
        throw new Error(`Consul discovery failed: ${response.statusText}`);
      }

      const services = await response.json();
      const instances = services.map(s => ({
        id: s.Service.ID,
        name: s.Service.Service,
        address: s.Service.Address,
        port: s.Service.Port,
        tags: s.Service.Tags,
        meta: s.Service.Meta,
      }));

      this.serviceCache.set(serviceName, instances);
      this.lastRefresh = now;

      return instances;
    } catch (error) {
      console.warn(`⚠️ Failed to discover service ${serviceName}:`, error.message);
      return this.serviceCache.get(serviceName) || [];
    }
  }

  async getServiceAddress(serviceName, strategy = 'round-robin') {
    const instances = await this.discoverService(serviceName);

    if (instances.length === 0) {
      throw new Error(`No healthy instances found for service: ${serviceName}`);
    }

    let selectedInstance;

    switch (strategy) {
      case 'round-robin':
        const counter = this.getCounter(serviceName);
        selectedInstance = instances[counter % instances.length];
        this.incrementCounter(serviceName);
        break;

      case 'random':
        selectedInstance = instances[Math.floor(Math.random() * instances.length)];
        break;

      case 'first':
      default:
        selectedInstance = instances[0];
    }

    return `${selectedInstance.address}:${selectedInstance.port}`;
  }

  getCounter(serviceName) {
    if (!this.counters) this.counters = {};
    return this.counters[serviceName] || 0;
  }

  incrementCounter(serviceName) {
    if (!this.counters) this.counters = {};
    this.counters[serviceName] = (this.counters[serviceName] || 0) + 1;
  }

  async healthCheck() {
    try {
      const response = await fetch(`${this.baseUrl}/status/leader`);
      return response.ok;
    } catch {
      return false;
    }
  }

  clearCache() {
    this.serviceCache.clear();
    this.lastRefresh = 0;
  }
}

export default ConsulClient;
