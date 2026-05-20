import fs from 'fs/promises';
import yaml from 'js-yaml';

class YamlParser {
  constructor(options = {}) {
    this.envPrefix = options.envPrefix || 'CONFIG_';
    this.envEnabled = options.envEnabled !== false;
    this.yamlOptions = options.yamlOptions || {};
  }

  async parseFile(filePath) {
    const content = await fs.readFile(filePath, 'utf-8');
    return this.parse(content);
  }

  parse(content) {
    const config = yaml.load(content, {
      ...this.yamlOptions,
      json: false
    });
    if (this.envEnabled) {
      return this.applyEnvOverrides(config);
    }
    return config;
  }

  applyEnvOverrides(config, path = '') {
    const result = { ...config };
    
    for (const [key, value] of Object.entries(result)) {
      const currentPath = path ? `${path}_${key}` : key;
      
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        result[key] = this.applyEnvOverrides(value, currentPath);
      } else {
        const envKey = this.envPrefix + currentPath.toUpperCase().replace(/\./g, '_');
        const envValue = process.env[envKey];
        
        if (envValue !== undefined) {
          result[key] = this.parseEnvValue(envValue, value);
        }
      }
    }
    
    return result;
  }

  parseEnvValue(envValue, originalValue) {
    if (typeof originalValue === 'number') {
      return Number(envValue);
    }
    if (typeof originalValue === 'boolean') {
      return envValue.toLowerCase() === 'true';
    }
    if (Array.isArray(originalValue)) {
      try {
        return JSON.parse(envValue);
      } catch {
        return envValue.split(',').map(s => s.trim());
      }
    }
    return envValue;
  }
}

export default YamlParser;
