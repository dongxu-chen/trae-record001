import * as echarts from 'echarts';

export class BaseChart extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.chartInstance = null;
    this._data = null;
    this._options = {};
    this._theme = 'light';
    this._componentId = this._generateId();
  }

  static get observedAttributes() {
    return ['title', 'theme', 'width', 'height', 'data-source', 'refresh-interval'];
  }

  connectedCallback() {
    this.render();
    this.initChart();
    this._setupMessageBus();
    this._setupResizeObserver();
    this.dispatchEvent(new CustomEvent('chart-connected', {
      detail: { id: this._componentId, type: this.chartType }
    }));
  }

  disconnectedCallback() {
    this._cleanup();
    this.dispatchEvent(new CustomEvent('chart-disconnected', {
      detail: { id: this._componentId }
    }));
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue !== newValue) {
      this[`_${name.replace('-', '')}`] = newValue;
      if (this.chartInstance) {
        this.updateChart();
      }
    }
  }

  render() {
    const width = this.getAttribute('width') || '100%';
    const height = this.getAttribute('height') || '400px';
    
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          width: ${width};
          height: ${height};
          position: relative;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .chart-container {
          width: 100%;
          height: 100%;
          background: var(--chart-bg, #fff);
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          overflow: hidden;
        }
        .chart-header {
          padding: 12px 16px;
          background: var(--header-bg, #fafafa);
          border-bottom: 1px solid var(--border-color, #f0f0f0);
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .chart-title {
          font-weight: 500;
          font-size: 14px;
          color: var(--text-color, #262626);
        }
        .chart-badge {
          padding: 2px 8px;
          background: #1890ff;
          color: #fff;
          border-radius: 10px;
          font-size: 12px;
          margin-left: 8px;
        }
        .chart-body {
          width: 100%;
          height: calc(100% - 48px);
        }
        :host([theme="dark"]) .chart-container {
          background: #141414;
        }
        :host([theme="dark"]) .chart-header {
          background: #1f1f1f;
          border-color: #333;
        }
        :host([theme="dark"]) .chart-title {
          color: #fff;
        }
      </style>
      <div class="chart-container">
        <div class="chart-header">
          <span class="chart-title">
            ${this.getAttribute('title') || '图表'}
            ${this.hasAttribute('enable-link') ? '<span class="chart-badge">联动中</span>' : ''}
          </span>
          <slot name="actions"></slot>
        </div>
        <div class="chart-body" id="chart"></div>
      </div>
    `;
  }

  initChart() {
    const chartDom = this.shadowRoot.getElementById('chart');
    if (!chartDom) return;

    this._theme = this.getAttribute('theme') || 'light';
    this.chartInstance = echarts.init(chartDom, this._theme === 'dark' ? 'dark' : null);
    
    this.updateChart();
    this._setupClickHandler();
  }

  updateChart() {
    if (!this.chartInstance) return;
    
    const option = this.getChartOption();
    this.chartInstance.setOption(option, { notMerge: false, lazyUpdate: true });
  }

  getChartOption() {
    return {};
  }

  set data(value) {
    this._data = value;
    this.updateChart();
    this._publish('data-updated', { data: value });
  }

  get data() {
    return this._data;
  }

  set options(value) {
    this._options = { ...this._options, ...value };
    this.updateChart();
  }

  get options() {
    return this._options;
  }

  refresh() {
    this.updateChart();
    this._publish('chart-refreshed', { id: this._componentId });
  }

  resize() {
    this.chartInstance?.resize();
  }

  dispose() {
    this._cleanup();
  }

  _generateId() {
    return `chart-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  _setupClickHandler() {
    if (!this.chartInstance) return;

    this.chartInstance.on('click', (params) => {
      this._handleChartClick(params);
    });
  }

  _handleChartClick(params) {
    const enableLink = this.hasAttribute('enable-link');
    const linkTargets = this.getAttribute('link-targets') || '';
    
    if (enableLink) {
      this._publish('chart-click', {
        sourceId: this._componentId,
        targets: linkTargets.split(',').map(t => t.trim()).filter(Boolean),
        data: params
      });
    }

    this.dispatchEvent(new CustomEvent('chart-click', {
      detail: params,
      bubbles: true,
      composed: true
    }));
  }

  _setupMessageBus() {
    this._messageHandler = (event) => {
      if (event.data && event.data.type) {
        this._handleMessage(event.data);
      }
    };
    window.addEventListener('message', this._messageHandler);
  }

  _handleMessage(message) {
    const { type, payload, targetId } = message;
    
    if (targetId && targetId !== this._componentId && targetId !== 'all') {
      return;
    }

    switch (type) {
      case 'refresh-chart':
        this.refresh();
        break;
      case 'update-data':
        this.data = payload.data;
        break;
      case 'update-theme':
        this.setAttribute('theme', payload.theme);
        this._theme = payload.theme;
        this._recreateChart();
        break;
      case 'update-options':
        this.options = payload.options;
        break;
    }
  }

  _publish(type, payload) {
    const message = {
      type,
      payload,
      sourceId: this._componentId,
      timestamp: Date.now()
    };
    
    window.postMessage(message, '*');
    
    this.dispatchEvent(new CustomEvent(type, {
      detail: payload,
      bubbles: true,
      composed: true
    }));
  }

  _setupResizeObserver() {
    this._resizeObserver = new ResizeObserver(() => {
      this.resize();
    });
    
    const chartDom = this.shadowRoot.getElementById('chart');
    if (chartDom) {
      this._resizeObserver.observe(chartDom);
    }
  }

  _recreateChart() {
    if (this.chartInstance) {
      this.chartInstance.dispose();
    }
    this.initChart();
  }

  _cleanup() {
    if (this._messageHandler) {
      window.removeEventListener('message', this._messageHandler);
    }
    
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
    }
    
    if (this.chartInstance) {
      this.chartInstance.dispose();
      this.chartInstance = null;
    }
  }

  get componentId() {
    return this._componentId;
  }

  get chartType() {
    return 'base';
  }
}

export default BaseChart;
