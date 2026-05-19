import fs from 'fs';
import path from 'path';
import { EventEmitter } from 'events';

class ConfigWatcher extends EventEmitter {
  constructor(filePath, options = {}) {
    super();
    this.filePath = path.resolve(filePath);
    this.dirPath = path.dirname(this.filePath);
    this.fileName = path.basename(this.filePath);
    this.options = {
      debounce: options.debounce || 300,
      ...options
    };
    this.watcher = null;
    this.debounceTimer = null;
    this.lastMtime = 0;
  }

  start() {
    if (this.watcher) {
      return this;
    }

    try {
      const stats = fs.statSync(this.filePath);
      this.lastMtime = stats.mtimeMs;
    } catch (e) {
    }

    this.watcher = fs.watch(this.dirPath, { persistent: true }, (eventType, filename) => {
      if (filename === this.fileName && eventType === 'change') {
        this.handleChange();
      }
    });

    this.watcher.on('error', (error) => {
      this.emit('error', error);
    });

    return this;
  }

  handleChange() {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    this.debounceTimer = setTimeout(() => {
      try {
        const stats = fs.statSync(this.filePath);
        if (stats.mtimeMs === this.lastMtime) {
          return;
        }
        this.lastMtime = stats.mtimeMs;
      } catch (e) {
        return;
      }
      
      this.emit('change');
    }, this.options.debounce);
  }

  stop() {
    if (this.watcher) {
      this.watcher.close();
      this.watcher = null;
    }
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }
    return this;
  }

  onChange(callback) {
    this.on('change', callback);
    return this;
  }

  onError(callback) {
    this.on('error', callback);
    return this;
  }
}

export default ConfigWatcher;
