class WinBarrage {
  constructor(options = {}) {
    this.container = options.container || document.body;
    this.apiURL = options.apiURL || '';
    this.pollInterval = options.pollInterval || 3000;
    this.maxBarrages = options.maxBarrages || 8;
    this.latestId = 0;
    this.timer = null;
    this.barrages = [];
    this.autoStart = options.autoStart !== false;
    this._container = null;
    this._ensureContainer();
    if (this.autoStart) this.start();
  }

  _ensureContainer() {
    this._container = document.createElement('div');
    this._container.id = 'win-barrage-container';
    this._container.style.cssText = `
      position: fixed;
      top: 15px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 9999;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      gap: 8px;
    `;
    this.container.appendChild(this._container);
  }

  _createBarrage(record) {
    const div = document.createElement('div');
    div.style.cssText = `
      background: rgba(255, 255, 255, 0.95);
      border: 2px solid ${record.prize_color || '#FFD700'};
      border-radius: 20px;
      padding: 10px 18px;
      font-family: 'Microsoft YaHei', Arial, sans-serif;
      font-size: 14px;
      color: #333;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      animation: barrageIn 0.4s ease-out;
      white-space: nowrap;
      max-width: 90vw;
      overflow: hidden;
      text-overflow: ellipsis;
    `;
    div.innerHTML = `
      <span style="color: ${record.prize_color || '#E74C3C'}; font-weight: bold;">
        恭喜【${record.user_id}】
      </span>
      抽中
      <span style="color: ${record.prize_color || '#E74C3C'}; font-weight: bold;">
        ${record.prize_name}
      </span>
    `;
    return div;
  }

  _addBarrage(record) {
    const el = this._createBarrage(record);
    this._container.appendChild(el);
    this.barrages.push({ el, id: record.id, createdAt: Date.now() });

    while (this.barrages.length > this.maxBarrages) {
      const old = this.barrages.shift();
      this._removeBarrage(old.el);
    }

    setTimeout(() => this._removeBarrage(el), 6000);
  }

  _removeBarrage(el) {
    if (!el || !el.parentNode) return;
    el.style.transition = 'opacity 0.4s ease';
    el.style.opacity = '0';
    setTimeout(() => {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 400);
    this.barrages = this.barrages.filter(b => b.el !== el);
  }

  async _fetch() {
    try {
      const url = `${this.apiURL}/api/records/wins?limit=10`;
      const resp = await fetch(url);
      if (!resp.ok) return;
      const list = await resp.json();
      if (!Array.isArray(list)) return;

      const newRecords = list
        .filter(r => r.id > this.latestId)
        .sort((a, b) => a.id - b.id);

      newRecords.forEach((r, i) => {
        setTimeout(() => this._addBarrage(r), i * 600);
      });

      if (list.length > 0) {
        this.latestId = Math.max(this.latestId, ...list.map(r => r.id));
      }
    } catch (e) {}
  }

  async start() {
    if (this.timer) return;
    await this._fetch();
    this.timer = setInterval(() => this._fetch(), this.pollInterval);
  }

  stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  clear() {
    while (this._container.firstChild) {
      this._container.removeChild(this._container.firstChild);
    }
    this.barrages = [];
  }

  destroy() {
    this.stop();
    this.clear();
    if (this._container && this._container.parentNode) {
      this._container.parentNode.removeChild(this._container);
    }
  }
}

if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @keyframes barrageIn {
      from {
        transform: translateY(-20px) scale(0.9);
        opacity: 0;
      }
      to {
        transform: translateY(0) scale(1);
        opacity: 1;
      }
    }
  `;
  document.head.appendChild(style);
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = WinBarrage;
}
