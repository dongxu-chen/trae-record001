import { EventEmitter } from 'events';
import YamlParser from './parser.js';
import ConfigWatcher from './watcher.js';
import ConfigValidator from './validator.js';
import ConfigCrypto from './crypto.js';
import ConfigAuditLogger from './audit.js';
import ConfigRegistry from './registry.js';

class ConfigManager extends EventEmitter {
  constructor(options = {}) {
    super();
    this.configPath = options.configPath;
    this.schema = options.schema || {};
    this.config = null;
    this.rawConfig = null;
    
    this.parser = new YamlParser(options.parser);
    this.validator = new ConfigValidator(this.schema);
    this.watcher = null;
    
    this.autoReload = options.autoReload !== false;
    this.validateOnLoad = options.validateOnLoad !== false;
    this.autoPush = options.autoPush || false;

    if (options.encryption) {
      this.crypto = new ConfigCrypto(options.encryption);
      this.encryptPaths = options.encryption.paths || [];
    }

    if (options.audit !== false) {
      this.audit = new ConfigAuditLogger(options.audit);
    }

    if (options.registry) {
      this.registry = new ConfigRegistry(options.registry);
    }
  }

  async load() {
    try {
      this.rawConfig = await this.parser.parseFile(this.configPath);
      this.config = { ...this.rawConfig };

      if (this.crypto) {
        this.config = this.crypto.decryptObject(this.config);
        if (this.audit) {
          this.audit.logDecrypt(this.encryptPaths);
        }
      }

      if (this.validateOnLoad) {
        const result = this.validator.validate(this.config);
        if (!result.valid) {
          if (this.audit) {
            this.audit.logValidationFail(result.errors);
          }
          throw new Error(`配置校验失败: ${JSON.stringify(result.errors, null, 2)}`);
        }
        if (this.audit) {
          this.audit.logValidationPass(this.config);
        }
      }

      if (this.audit) {
        this.audit.logLoad(this.config, this.configPath);
      }

      this.emit('loaded', this.config);
      return this.config;
    } catch (error) {
      this.emit('error', error);
      throw error;
    }
  }

  async reload() {
    try {
      const oldConfig = this.config;
      this.rawConfig = await this.parser.parseFile(this.configPath);
      this.config = { ...this.rawConfig };

      if (this.crypto) {
        this.config = this.crypto.decryptObject(this.config);
      }

      if (this.validateOnLoad) {
        const result = this.validator.validate(this.config);
        if (!result.valid) {
          this.config = oldConfig;
          if (this.audit) {
            this.audit.logValidationFail(result.errors);
          }
          throw new Error(`配置校验失败: ${JSON.stringify(result.errors, null, 2)}`);
        }
      }

      if (this.audit) {
        this.audit.logChange(oldConfig, this.config);
      }

      if (this.autoPush && this.registry) {
        await this.pushToRegistry();
      }

      this.emit('changed', {
        oldConfig,
        newConfig: this.config
      });
      return this.config;
    } catch (error) {
      this.emit('error', error);
      throw error;
    }
  }

  startWatcher() {
    if (!this.autoReload || this.watcher) {
      return this;
    }

    this.watcher = new ConfigWatcher(this.configPath);
    this.watcher.onChange(async () => {
      try {
        await this.reload();
      } catch (error) {
        console.error('热更新失败:', error.message);
      }
    });
    this.watcher.onError((error) => {
      this.emit('error', error);
    });
    this.watcher.start();

    return this;
  }

  stopWatcher() {
    if (this.watcher) {
      this.watcher.stop();
      this.watcher = null;
    }
    return this;
  }

  get(key = null, defaultValue = null) {
    if (!this.config) {
      return defaultValue;
    }

    if (key === null) {
      return this.config;
    }

    const keys = key.split('.');
    let value = this.config;

    for (const k of keys) {
      if (value && typeof value === 'object' && k in value) {
        value = value[k];
      } else {
        return defaultValue;
      }
    }

    return value !== undefined ? value : defaultValue;
  }

  setSchema(schema) {
    this.schema = schema;
    this.validator.setSchema(schema);
    return this;
  }

  validate() {
    return this.validator.validate(this.config);
  }

  encrypt(value) {
    if (!this.crypto) {
      throw new Error('加密功能未启用，请配置 encryption 选项');
    }
    return this.crypto.encrypt(value);
  }

  decrypt(value) {
    if (!this.crypto) {
      throw new Error('加密功能未启用，请配置 encryption 选项');
    }
    return this.crypto.decrypt(value);
  }

  async encryptConfig(paths = this.encryptPaths) {
    if (!this.crypto) {
      throw new Error('加密功能未启用，请配置 encryption 选项');
    }
    const encrypted = this.crypto.encryptObject(this.rawConfig || this.config, paths);
    if (this.audit) {
      this.audit.logEncrypt(paths);
    }
    return encrypted;
  }

  async connectRegistry() {
    if (!this.registry) {
      throw new Error('配置中心未配置，请配置 registry 选项');
    }
    await this.registry.connect();
    return this;
  }

  async pushToRegistry(options = {}) {
    if (!this.registry) {
      throw new Error('配置中心未配置，请配置 registry 选项');
    }

    const configToPush = options.encrypt && this.crypto 
      ? this.crypto.encryptObject(this.config, this.encryptPaths)
      : this.config;

    const result = await this.registry.pushObject(configToPush, options.prefix || '');

    if (this.audit) {
      this.audit.logPush(this.registry.type, result.success ? 'success' : 'failed', this.config);
    }

    return result;
  }

  async pullFromRegistry(key, options = {}) {
    if (!this.registry) {
      throw new Error('配置中心未配置，请配置 registry 选项');
    }

    const value = await this.registry.get(key, options);
    
    if (this.crypto && this.crypto.isEncrypted(value)) {
      return this.crypto.decrypt(value);
    }
    
    return value;
  }

  async getAuditHistory(filter = {}) {
    if (!this.audit) {
      throw new Error('审计日志未启用');
    }
    return await this.audit.getHistory(filter);
  }

  async init() {
    await this.load();
    this.startWatcher();
    
    if (this.registry) {
      try {
        await this.connectRegistry();
        if (this.autoPush) {
          await this.pushToRegistry();
        }
      } catch (error) {
        console.warn('连接配置中心失败:', error.message);
      }
    }
    
    return this;
  }

  destroy() {
    this.stopWatcher();
    if (this.registry) {
      this.registry.disconnect();
    }
    this.removeAllListeners();
    this.config = null;
    this.rawConfig = null;
  }
}

export default ConfigManager;
export { 
  YamlParser, 
  ConfigWatcher, 
  ConfigValidator,
  ConfigCrypto,
  ConfigAuditLogger,
  ConfigRegistry
};
