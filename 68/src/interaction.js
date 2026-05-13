export class InteractionManager {
  constructor(options = {}) {
    this.container = options.container || document.body;
    this.onHover = options.onHover || null;
    this.onClick = options.onClick || null;
    this.dataStore = options.dataStore || null;
    this.tooltipElement = null;
    
    this.highlightedIndex = -1;
    this.previousHighlightedIndex = -1;
    this.currentHoveredObject = null;
    
    this._hoverTimeout = null;
    this._hoverDelay = 16;
    this._pendingHoverUpdate = false;
    this._lastHoverX = -1;
    this._lastHoverY = -1;
    
    this._needsLayerUpdate = false;
    this._animationFrameId = null;
    
    this.init();
  }

  init() {
    this.tooltipElement = document.createElement('div');
    this.tooltipElement.className = 'tooltip';
    this.tooltipElement.style.display = 'none';
    this.container.appendChild(this.tooltipElement);
  }

  setDataStore(dataStore) {
    this.dataStore = dataStore;
  }

  createHoverHandler() {
    return (info) => {
      const { x, y, index, object } = info;
      
      this._lastHoverX = x;
      this._lastHoverY = y;
      
      const newIndex = index !== undefined ? index : -1;
      
      if (newIndex !== this.highlightedIndex) {
        this.highlightedIndex = newIndex;
        this._needsLayerUpdate = true;
        
        if (this._hoverTimeout) {
          clearTimeout(this._hoverTimeout);
        }
        
        this._hoverTimeout = setTimeout(() => {
          this._processHover(x, y, index, object);
        }, this._hoverDelay);
      }
    };
  }

  _processHover(x, y, index, object) {
    if (index >= 0 && this.dataStore) {
      let point = object;
      if (!point && this.dataStore.getPoint) {
        point = this.dataStore.getPoint(index);
      }
      
      if (point) {
        this.currentHoveredObject = point;
        this.showTooltip(point, x, y);
        
        if (this.onHover) {
          this.onHover({
            object: point,
            x,
            y,
            highlightedIndex: index,
            needsLayerUpdate: this._needsLayerUpdate
          });
        }
      }
    } else {
      this.currentHoveredObject = null;
      this.hideTooltip();
      
      if (this.onHover) {
        this.onHover({
          object: null,
          x,
          y,
          highlightedIndex: -1,
          needsLayerUpdate: this._needsLayerUpdate
        });
      }
    }
    
    this._pendingHoverUpdate = false;
  }

  createClickHandler() {
    return (info) => {
      const { index, object } = info;
      
      if (index >= 0) {
        let point = object;
        if (!point && this.dataStore && this.dataStore.getPoint) {
          point = this.dataStore.getPoint(index);
        }
        
        if (point && this.onClick) {
          this.onClick({ object: point, index });
        }
      }
    };
  }

  getHighlightedIndex() {
    return this.highlightedIndex;
  }

  hasHighlightChanged() {
    return this.highlightedIndex !== this.previousHighlightedIndex;
  }

  markLayerUpdated() {
    this.previousHighlightedIndex = this.highlightedIndex;
    this._needsLayerUpdate = false;
  }

  needsLayerUpdate() {
    return this._needsLayerUpdate;
  }

  showTooltip(object, x, y) {
    if (!this.tooltipElement) return;
    
    const content = this.formatTooltipContent(object);
    if (this.tooltipElement.innerHTML !== content) {
      this.tooltipElement.innerHTML = content;
    }
    this.tooltipElement.style.display = 'block';
    
    const offsetX = 15;
    const offsetY = 15;
    
    let posX = x + offsetX;
    let posY = y + offsetY;
    
    const rect = this.container.getBoundingClientRect();
    const tooltipWidth = this.tooltipElement.offsetWidth;
    const tooltipHeight = this.tooltipElement.offsetHeight;
    
    if (posX + tooltipWidth > rect.width) {
      posX = x - tooltipWidth - offsetX;
    }
    if (posY + tooltipHeight > rect.height) {
      posY = y - tooltipHeight - offsetY;
    }
    
    this.tooltipElement.style.left = `${posX}px`;
    this.tooltipElement.style.top = `${posY}px`;
  }

  hideTooltip() {
    if (this.tooltipElement && this.tooltipElement.style.display !== 'none') {
      this.tooltipElement.style.display = 'none';
    }
  }

  formatTooltipContent(object) {
    if (!object) return '';
    
    const lines = [];
    
    lines.push(`<h3>点 #${object.id ?? 'N/A'}</h3>`);
    lines.push(`<p><strong>经度:</strong> ${object.longitude?.toFixed(6) ?? 'N/A'}</p>`);
    lines.push(`<p><strong>纬度:</strong> ${object.latitude?.toFixed(6) ?? 'N/A'}</p>`);
    
    if (object.value !== undefined && object.value !== null) {
      lines.push(`<p><strong>值:</strong> ${object.value.toFixed(2)}</p>`);
    }
    
    if (object.category) {
      lines.push(`<p><strong>类别:</strong> ${object.category}</p>`);
    }
    
    if (object.timestamp) {
      const date = new Date(object.timestamp);
      lines.push(`<p><strong>时间:</strong> ${date.toLocaleString()}</p>`);
    }
    
    return lines.join('');
  }

  getCurrentHoveredObject() {
    return this.currentHoveredObject;
  }

  clearHighlights() {
    if (this._hoverTimeout) {
      clearTimeout(this._hoverTimeout);
      this._hoverTimeout = null;
    }
    
    this.highlightedIndex = -1;
    this.previousHighlightedIndex = -1;
    this.currentHoveredObject = null;
    this._needsLayerUpdate = false;
    this.hideTooltip();
  }

  destroy() {
    if (this._hoverTimeout) {
      clearTimeout(this._hoverTimeout);
    }
    if (this._animationFrameId) {
      cancelAnimationFrame(this._animationFrameId);
    }
    
    if (this.tooltipElement && this.tooltipElement.parentNode) {
      this.tooltipElement.parentNode.removeChild(this.tooltipElement);
    }
    this.tooltipElement = null;
    this.currentHoveredObject = null;
    this.dataStore = null;
  }
}

export function createInteractionManager(options) {
  return new InteractionManager(options);
}

export function formatNumber(num) {
  return num.toLocaleString('zh-CN');
}

export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

export function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}
