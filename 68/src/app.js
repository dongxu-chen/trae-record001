import { MapboxOverlay } from '@deck.gl/mapbox';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

import { loadCSVData, generateSampleData } from './data_loader';
import { LayerManager, DISPLAY_MODES } from './layer';
import { createClusterManager } from './cluster';
import { createHeatmapManager } from './heatmap';
import { createTimelineManager } from './timeline';
import { createInteractionManager, formatNumber } from './interaction';

const CONFIG = {
  initialViewState: {
    longitude: 116.4074,
    latitude: 39.9042,
    zoom: 11,
    pitch: 0,
    bearing: 0
  },
  mapStyle: 'https://demotiles.maplibre.org/style.json',
  pointCount: 100000,
  defaultMode: DISPLAY_MODES.POINTS
};

class PointCloudApp {
  constructor() {
    this.map = null;
    this.overlay = null;
    this.interactionManager = null;
    this.layerManager = null;
    this.clusterManager = null;
    this.heatmapManager = null;
    this.timelineManager = null;
    
    this.dataStore = null;
    this.filteredDataStore = null;
    this.currentMode = CONFIG.defaultMode;
    this.currentZoom = CONFIG.initialViewState.zoom;
    this.currentBounds = null;
    
    this._layerUpdateScheduled = false;
    this._currentLayers = [];
  }

  async init() {
    this.showLoading('正在初始化地图...', 0);
    this.initMap();
    this.initInteraction();
    await this.loadData();
    this.hideLoading();
    this.initManagers();
    this.createInitialLayers();
    this.updateStats();
    this.bindUIEvents();
  }

  initMap() {
    const mapContainer = document.getElementById('map');
    
    this.map = new maplibregl.Map({
      container: mapContainer,
      style: CONFIG.mapStyle,
      center: [CONFIG.initialViewState.longitude, CONFIG.initialViewState.latitude],
      zoom: CONFIG.initialViewState.zoom
    });

    this.overlay = new MapboxOverlay({
      interleaved: true,
      layers: []
    });
    this.map.addControl(this.overlay);

    this.map.on('load', () => {
      this.showLoading('地图加载完成，准备数据...', 20);
    });

    this.map.on('move', () => {
      this.currentZoom = this.map.getZoom();
      this.updateCenterDisplay();
    });

    this.map.on('moveend', () => {
      this.currentZoom = this.map.getZoom();
      const bounds = this.map.getBounds();
      this.currentBounds = [
        bounds.getWest(),
        bounds.getSouth(),
        bounds.getEast(),
        bounds.getNorth()
      ];
      
      if (this.currentMode === DISPLAY_MODES.CLUSTERS || this.currentMode === DISPLAY_MODES.HYBRID) {
        this.scheduleLayerUpdate();
      }
    });
  }

  initInteraction() {
    const container = document.getElementById('container');
    
    this.interactionManager = createInteractionManager({
      container,
      onHover: (info) => this.handleHover(info)
    });
  }

  async loadData() {
    this.showLoading('正在加载数据...', 30);
    
    try {
      const csvResult = await loadCSVData('./data/points.csv', {
        onProgress: (progress) => {
          this.showLoading(`正在解析 CSV 数据... ${Math.round(progress)}%`, 30 + progress * 0.5);
        }
      });
      
      this.dataStore = csvResult;
      this.filteredDataStore = csvResult;
      this.interactionManager.setDataStore(csvResult);
      this.fitToBounds(csvResult.bounds);
      
    } catch (error) {
      console.warn('无法加载 CSV 文件，使用生成的示例数据:', error.message);
      this.showLoading('生成示例数据...', 60);
      
      this.dataStore = generateSampleData(CONFIG.pointCount, {
        centerLng: CONFIG.initialViewState.longitude,
        centerLat: CONFIG.initialViewState.latitude,
        spread: 0.3
      });
      this.filteredDataStore = this.dataStore;
      this.interactionManager.setDataStore(this.dataStore);
    }
    
    this.showLoading('准备渲染层...', 90);
  }

  initManagers() {
    if (!this.filteredDataStore) return;

    this.layerManager = new LayerManager(this.filteredDataStore);
    this.layerManager.setMode(this.currentMode);

    this.clusterManager = createClusterManager(this.filteredDataStore);
    this.clusterManager.init();

    this.heatmapManager = createHeatmapManager(this.filteredDataStore);

    const container = document.getElementById('container');
    this.timelineManager = createTimelineManager(this.filteredDataStore, {
      container,
      onUpdate: (timeWindow) => this.handleTimelineUpdate(timeWindow)
    });
  }

  createInitialLayers() {
    if (!this.layerManager || !this.overlay) return;

    this._currentLayers = this.layerManager.createLayers({
      zoom: this.currentZoom,
      bounds: this.currentBounds,
      onHover: this.interactionManager.createHoverHandler(),
      onClick: this.interactionManager.createClickHandler(),
      onClusterClick: (cluster, info) => this.handleClusterClick(cluster, info),
      clusterManager: this.clusterManager,
      highlightedObjectIndex: -1
    });

    this.overlay.setProps({ layers: this._currentLayers });
    document.getElementById('render-status').textContent = '渲染中 ✓';
  }

  scheduleLayerUpdate() {
    if (this._layerUpdateScheduled) return;
    
    this._layerUpdateScheduled = true;
    requestAnimationFrame(() => {
      this.updateLayers();
      this._layerUpdateScheduled = false;
    });
  }

  updateLayers() {
    if (!this.layerManager || !this.overlay) return;

    const highlightedIndex = this.interactionManager.getHighlightedIndex();

    const newLayers = this.layerManager.createLayers({
      zoom: this.currentZoom,
      bounds: this.currentBounds,
      onHover: this.interactionManager.createHoverHandler(),
      onClick: this.interactionManager.createClickHandler(),
      onClusterClick: (cluster, info) => this.handleClusterClick(cluster, info),
      clusterManager: this.clusterManager,
      highlightedObjectIndex: highlightedIndex
    });

    this._currentLayers = newLayers;
    this.overlay.setProps({ layers: newLayers });
    this.interactionManager.markLayerUpdated();
  }

  handleHover(info) {
    if (info.needsLayerUpdate) {
      this.scheduleLayerUpdate();
    }
  }

  handleClusterClick(cluster, info) {
    if (!this.clusterManager || !cluster.isCluster) return;
    
    const expansionZoom = this.clusterManager.getClusterExpansionZoom(cluster.clusterId);
    const targetZoom = Math.max(expansionZoom, this.currentZoom + 1);
    
    this.map.flyTo({
      center: [cluster.longitude, cluster.latitude],
      zoom: targetZoom,
      duration: 500
    });
    
    console.log(`📍 点击聚类: ${cluster.pointCount} 个点, 展开到 zoom ${expansionZoom}`);
  }

  handleTimelineUpdate(timeWindow) {
    if (!this.timelineManager) return;
    
    const filtered = this.timelineManager.getPointsInWindow();
    this.filteredDataStore = filtered;
    
    if (this.layerManager) {
      this.layerManager.setDataStore(filtered);
    }
    
    if (this.clusterManager) {
      this.clusterManager.destroy();
      this.clusterManager = createClusterManager(filtered);
      this.clusterManager.init();
    }
    
    if (this.heatmapManager) {
      this.heatmapManager.destroy();
      this.heatmapManager = createHeatmapManager(filtered);
    }
    
    this.scheduleLayerUpdate();
    this.updateStats();
  }

  setDisplayMode(mode) {
    if (!Object.values(DISPLAY_MODES).includes(mode)) {
      console.warn(`❌ 未知的显示模式: ${mode}`);
      return;
    }
    
    if (mode === this.currentMode) return;
    
    this.currentMode = mode;
    
    if (this.layerManager) {
      this.layerManager.setMode(mode);
    }
    
    this.scheduleLayerUpdate();
    console.log(`🎨 切换显示模式: ${mode}`);
  }

  fitToBounds(bounds) {
    if (!bounds || !this.map) return;

    const { minLng, maxLng, minLat, maxLat } = bounds;
    
    this.map.fitBounds([
      [minLng, minLat],
      [maxLng, maxLat]
    ], {
      padding: 50,
      duration: 1000
    });
  }

  updateStats() {
    const dataStore = this.filteredDataStore || this.dataStore;
    if (!dataStore) return;

    const countElement = document.getElementById('point-count');
    if (countElement) {
      countElement.textContent = formatNumber(dataStore.count);
    }

    if (dataStore.memoryUsage) {
      const statusElement = document.getElementById('render-status');
      if (statusElement) {
        statusElement.textContent = `渲染中 (${dataStore.memoryUsage}) ✓`;
      }
    }
    
    const modeElement = document.getElementById('display-mode');
    if (modeElement) {
      modeElement.textContent = this.getModeDisplayName();
    }

    this.updateCenterDisplay();
  }

  getModeDisplayName() {
    const names = {
      [DISPLAY_MODES.POINTS]: '点云',
      [DISPLAY_MODES.CLUSTERS]: '聚类',
      [DISPLAY_MODES.HEATMAP]: '热力图',
      [DISPLAY_MODES.HYBRID]: '混合'
    };
    return names[this.currentMode] || this.currentMode;
  }

  updateCenterDisplay() {
    if (!this.map) return;

    const center = this.map.getCenter();
    const centerElement = document.getElementById('center-coord');
    
    if (centerElement) {
      centerElement.textContent = 
        `${center.lng.toFixed(4)}, ${center.lat.toFixed(4)}`;
    }
  }

  bindUIEvents() {
    const modeButtons = document.querySelectorAll('[data-mode]');
    modeButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const mode = e.target.dataset.mode;
        if (mode) {
          this.setDisplayMode(mode);
          this.updateModeButtons(mode);
        }
      });
    });
  }

  updateModeButtons(activeMode) {
    const modeButtons = document.querySelectorAll('[data-mode]');
    modeButtons.forEach(btn => {
      if (btn.dataset.mode === activeMode) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  showLoading(text, progress) {
    const loadingElement = document.getElementById('loading');
    const textElement = document.getElementById('loading-text');
    const barElement = document.getElementById('loading-bar');

    if (loadingElement) {
      loadingElement.style.display = 'flex';
    }
    if (textElement) {
      textElement.textContent = text;
    }
    if (barElement) {
      barElement.style.width = `${progress}%`;
    }
  }

  hideLoading() {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
      loadingElement.style.display = 'none';
    }
  }

  destroy() {
    if (this.timelineManager) {
      this.timelineManager.destroy();
    }
    if (this.clusterManager) {
      this.clusterManager.destroy();
    }
    if (this.heatmapManager) {
      this.heatmapManager.destroy();
    }
    if (this.layerManager) {
      this.layerManager.destroy();
    }
    if (this.interactionManager) {
      this.interactionManager.destroy();
    }
    if (this.overlay) {
      this.overlay.finalize();
    }
    if (this.map) {
      this.map.remove();
    }
  }
}

const app = new PointCloudApp();

window.addEventListener('DOMContentLoaded', () => {
  app.init().catch(error => {
    console.error('应用初始化失败:', error);
    const loadingText = document.getElementById('loading-text');
    if (loadingText) {
      loadingText.textContent = `初始化失败: ${error.message}`;
      loadingText.style.color = '#ff6b6b';
    }
  });
});

window.addEventListener('beforeunload', () => {
  app.destroy();
});

window.setDisplayMode = (mode) => app.setDisplayMode(mode);

export default app;
