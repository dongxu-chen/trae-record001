import '../components/LineChart.js';
import '../components/BarChart.js';
import '../components/PieChart.js';
import { messageBus } from '../core/MessageBus.js';

const VERSION = '1.0.0';

export class DashboardSDK {
  constructor(options = {}) {
    this.version = VERSION;
    this.options = {
      theme: 'light',
      autoRegister: true,
      ...options
    };
    this.charts = new Map();
    this._messageBus = messageBus;

    if (this.options.autoRegister) {
      this._setupAutoRegister();
    }
  }

  _setupAutoRegister() {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === 1 && node.tagName?.endsWith('-CHART')) {
            this._registerChart(node);
          }
        });
        mutation.removedNodes.forEach((node) => {
          if (node.nodeType === 1 && node.componentId) {
            this.charts.delete(node.componentId);
          }
        });
      };
    });

    observer.observe(document.body, { childList: true, subtree: true });

    document.querySelectorAll('line-chart, bar-chart, pie-chart').forEach((el) => {
      this._registerChart(el);
    });
  }

  _registerChart(element) {
    if (element.componentId && !this.charts.has(element.componentId)) {
      this.charts.set(element.componentId, element);
    }
  }

  createLineChart(container, config = {}) {
    return this._createChart('line-chart', container, config);
  }

  createBarChart(container, config = {}) {
    return this._createChart('bar-chart', container, config);
  }

  createPieChart(container, config = {}) {
    return this._createChart('pie-chart', container, config);
  }

  _createChart(tagName, container, config = {}) {
    const element = document.createElement(tagName);
    
    Object.entries(config).forEach(([key, value]) => {
      if (typeof value === 'boolean') {
        if (value) element.setAttribute(key, '');
      } else if (typeof value !== 'object') {
        element[key.replace(/-([a-z])/g, (g) => g[1].toUpperCase())] = value;
      } else {
        element.setAttribute(key, value);
      }
    });

    if (typeof container === 'string') {
      document.querySelector(container)?.appendChild(element);
    } else if (container instanceof HTMLElement) {
      container.appendChild(element);
    }

    this._registerChart(element);
    return element;
  }

  getChartById(id) {
    return this.charts.get(id);
  }

  getAllCharts() {
    return Array.from(this.charts.values());
  }

  getChartsByType(type) {
    return this.getAllCharts().filter((c) => c.chartType === type);
  }

  refreshAll() {
    this.getAllCharts().forEach((chart) => chart.refresh());
  }

  refreshById(id) {
    this.getChartById(id)?.refresh();
  }

  setGlobalTheme(theme) {
    this._messageBus.broadcast('update-theme', { theme });
  }

  setChartData(id, data) {
    const chart = this.getChartById(id);
    if (chart) {
      chart.data = data;
    }
  }

  setAllChartData(dataMap) {
    Object.entries(dataMap).forEach(([id, data]) => {
      this.setChartData(id, data);
    });
  }

  on(type, callback) {
    return this._messageBus.subscribe(type, callback);
  }

  off(type, callback = null) {
    this._messageBus.unsubscribe(type, callback);
  }

  send(targetId, type, payload) {
    this._messageBus.sendTo(targetId, type, payload);
  }

  broadcast(type, payload) {
    this._messageBus.broadcast(type, payload);
  }

  exportConfig() {
    const config = {
      version: this.version,
      exportTime: new Date().toISOString(),
      charts: this.getAllCharts().map((chart) => ({
        id: chart.componentId,
        type: chart.chartType,
        title: chart.getAttribute('title'),
        theme: chart.getAttribute('theme'),
        attributes: this._getElementAttributes(chart)
      }))
    };
    
    const dataStr = JSON.stringify(config, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `dashboard-config-${Date.now()}.json';
    link.click();
    URL.revokeObjectURL(url);
    
    return config;
  }

  importConfig(config) {
    if (typeof config === 'string') {
      config = JSON.parse(config);
    }

    this.getAllCharts().forEach((chart) => chart.remove());
    this.charts.clear();

    config.charts.forEach((chartConfig) => {
      const tagName = `${chartConfig.type}-chart`;
      const element = document.createElement(tagName);
      
      Object.entries(chartConfig.attributes).forEach(([key, value]) => {
        if (value) {
          element.setAttribute(key, value);
        }
      });
      
      document.body.appendChild(element);
      this._registerChart(element);
    });
  }

  _getElementAttributes(element) {
    const attributes = {};
    for (let i = 0; i < element.attributes.length; i++) {
      const attr = element.attributes[i];
      attributes[attr.name] = attr.value;
    }
    return attributes;
  }

  destroy() {
    this.getAllCharts().forEach((chart) => chart.dispose());
    this.charts.clear();
    this._messageBus.clear();
  }

  static getInstance() {
    if (!DashboardSDK._instance) {
      DashboardSDK._instance = new DashboardSDK();
    }
    return DashboardSDK._instance;
  }
}

DashboardSDK._instance = null;

export function createDashboardSDK(options) {
  return new DashboardSDK(options);
}

export function getDashboardSDK() {
  return DashboardSDK.getInstance();
}

export { messageBus } from '../core/MessageBus.js';
export { LineChart } from '../components/LineChart.js';
export { BarChart } from '../components/BarChart.js';
export { PieChart } from '../components/PieChart.js';

export default {
  DashboardSDK,
  createDashboardSDK,
  getDashboardSDK,
  messageBus,
  VERSION
};
