import { ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import { HeatmapLayer } from '@deck.gl/aggregation-layers';

export const DISPLAY_MODES = {
  POINTS: 'points',
  CLUSTERS: 'clusters',
  HEATMAP: 'heatmap',
  HYBRID: 'hybrid'
};

const DEFAULT_COLOR_SCHEME = {
  A: [255, 100, 100],
  B: [100, 200, 255],
  C: [100, 255, 150],
  D: [255, 200, 100]
};

const RADIUS_UNITS = {
  PIXELS: 'pixels',
  METERS: 'meters',
  COMMON: 'common'
};

const DEFAULT_OPTIONS = {
  id: 'scatterplot-layer',
  data: [],
  pickable: true,
  opacity: 0.8,
  stroked: false,
  filled: true,
  radiusMinPixels: 1,
  radiusMaxPixels: 30,
  lineWidthMinPixels: 1
};

const HEATMAP_COLOR_SCHEMES = {
  default: [
    [255, 255, 178],
    [254, 217, 118],
    [254, 178, 76],
    [253, 141, 60],
    [240, 59, 32],
    [189, 0, 38]
  ],
  viridis: [
    [68, 1, 84],
    [72, 40, 120],
    [62, 74, 137],
    [49, 104, 142],
    [38, 130, 142],
    [31, 158, 137],
    [53, 183, 121],
    [109, 205, 89],
    [180, 222, 44],
    [253, 231, 37]
  ],
  plasma: [
    [13, 8, 135],
    [75, 3, 161],
    [125, 3, 168],
    [168, 34, 150],
    [203, 70, 121],
    [229, 107, 93],
    [248, 148, 65],
    [253, 195, 40],
    [240, 249, 33]
  ]
};

export class LayerManager {
  constructor(dataStore, options = {}) {
    this.dataStore = dataStore;
    this.options = options;
    this.currentMode = DISPLAY_MODES.POINTS;
    this._layerCache = new Map();
    this._preparedData = null;
    this._prepareData();
  }

  _prepareData() {
    if (!this.dataStore) {
      this._preparedData = {
        points: [],
        positions: new Float64Array(),
        values: new Float32Array(),
        categories: new Uint8Array(),
        count: 0
      };
      return;
    }

    const { count, positions, values, categories, timestamps, categoryMap, getPoint } = this.dataStore;
    
    this._preparedData = {
      positions,
      values,
      categories,
      timestamps,
      categoryMap,
      count,
      getPoint,
      heatmapData: this._createHeatmapData(positions, values, count)
    };
    
    console.log(`✅ 图层管理器初始化完成: ${count} 个点`);
  }

  _createHeatmapData(positions, values, count) {
    const data = new Array(count);
    for (let i = 0; i < count; i++) {
      data[i] = {
        position: [positions[i * 2], positions[i * 2 + 1]],
        weight: values[i] || 1
      };
    }
    return data;
  }

  setMode(mode) {
    if (!Object.values(DISPLAY_MODES).includes(mode)) {
      console.warn(`❌ 未知的显示模式: ${mode}`);
      return;
    }
    this.currentMode = mode;
    console.log(`📊 切换到模式: ${mode}`);
  }

  getMode() {
    return this.currentMode;
  }

  setDataStore(dataStore) {
    this.dataStore = dataStore;
    this._prepareData();
    this._layerCache.clear();
  }

  createLayers(options = {}) {
    const {
      highlightedObjectIndex = -1,
      zoom = 10,
      bounds = null,
      onHover = null,
      onClick = null,
      onClusterClick = null,
      heatmapColorScheme = 'default',
      heatmapRadius = 60,
      heatmapIntensity = 1,
      clusterManager = null,
      ...restOptions
    } = options;

    switch (this.currentMode) {
      case DISPLAY_MODES.POINTS:
        return this._createPointsLayers({
          highlightedObjectIndex,
          onHover,
          onClick,
          ...restOptions
        });
      
      case DISPLAY_MODES.CLUSTERS:
        return this._createClusterLayers({
          zoom,
          bounds,
          onHover,
          onClick,
          onClusterClick,
          clusterManager,
          ...restOptions
        });
      
      case DISPLAY_MODES.HEATMAP:
        return this._createHeatmapLayers({
          colorScheme: heatmapColorScheme,
          radius: heatmapRadius,
          intensity: heatmapIntensity,
          onHover,
          onClick,
          ...restOptions
        });
      
      case DISPLAY_MODES.HYBRID:
        return this._createHybridLayers({
          zoom,
          bounds,
          highlightedObjectIndex,
          onHover,
          onClick,
          onClusterClick,
          clusterManager,
          colorScheme: heatmapColorScheme,
          ...restOptions
        });
      
      default:
        return this._createPointsLayers({
          highlightedObjectIndex,
          onHover,
          onClick,
          ...restOptions
        });
    }
  }

  _createPointsLayers(options) {
    const {
      highlightedObjectIndex = -1,
      onHover = null,
      onClick = null,
      radiusUnits = RADIUS_UNITS.METERS,
      radiusScale = 1,
      ...restOptions
    } = options;

    if (!this._preparedData || this._preparedData.count === 0) {
      return [];
    }

    const layer = new ScatterplotLayer({
      ...DEFAULT_OPTIONS,
      id: 'main-scatterplot-layer',
      data: this._preparedData,
      pickable: true,
      radiusUnits,
      radiusScale,
      highlightedObjectIndex,
      highlightColor: [255, 255, 0, 255],
      autoHighlight: false,
      getPosition: (_, { index }) => [
        this._preparedData.positions[index * 2],
        this._preparedData.positions[index * 2 + 1]
      ],
      getFillColor: (_, { index }) => this._getPointColor(index),
      getRadius: (_, { index }) => this._getPointRadius(index),
      onHover,
      onClick,
      ...restOptions
    });

    return [layer];
  }

  _createClusterLayers(options) {
    const {
      zoom = 10,
      bounds = null,
      onHover = null,
      onClick = null,
      onClusterClick = null,
      clusterManager = null,
      ...restOptions
    } = options;

    if (!clusterManager) {
      console.warn('⚠️ 聚类模式需要 clusterManager');
      return this._createPointsLayers(options);
    }

    return clusterManager.createClusterLayers(zoom, bounds, {
      onClusterClick,
      onPointClick: onClick,
      onHover
    });
  }

  _createHeatmapLayers(options) {
    const {
      colorScheme = 'default',
      radius = 60,
      intensity = 1,
      threshold = 0.05,
      onHover = null,
      onClick = null,
      ...restOptions
    } = options;

    if (!this._preparedData || this._preparedData.count === 0) {
      return [];
    }

    const colorRange = HEATMAP_COLOR_SCHEMES[colorScheme] || HEATMAP_COLOR_SCHEMES.default;

    const layer = new HeatmapLayer({
      id: 'heatmap-layer',
      data: this._preparedData.heatmapData,
      radiusPixels: radius,
      intensity,
      threshold,
      colorRange,
      pickable: !!(onHover || onClick),
      aggregation: 'SUM',
      getPosition: (d) => d.position,
      getWeight: (d) => d.weight,
      onHover,
      onClick,
      ...restOptions
    });

    return [layer];
  }

  _createHybridLayers(options) {
    const {
      zoom = 10,
      clusterManager = null,
      ...restOptions
    } = options;

    const layers = [];

    const heatmapLayers = this._createHeatmapLayers({
      ...options,
      intensity: 0.7,
      threshold: 0.1
    });
    layers.push(...heatmapLayers);

    if (clusterManager && zoom < 12) {
      const clusterLayers = clusterManager.createClusterLayers(zoom, options.bounds, {
        onClusterClick: options.onClusterClick,
        onPointClick: options.onClick,
        onHover: options.onHover
      });
      layers.push(...clusterLayers);
    } else {
      const pointLayers = this._createPointsLayers(options);
      layers.push(...pointLayers);
    }

    return layers;
  }

  _getPointColor(index) {
    const categoryId = this._preparedData.categories[index];
    const value = this._preparedData.values[index];
    
    if (categoryId !== 255 && this._preparedData.categoryMap) {
      const catIdToName = new Map();
      this._preparedData.categoryMap.forEach((name, id) => catIdToName.set(id, name));
      const catName = catIdToName.get(categoryId);
      
      if (catName && DEFAULT_COLOR_SCHEME[catName]) {
        const baseColor = DEFAULT_COLOR_SCHEME[catName];
        const alpha = Math.min(180 + value * 0.7, 255);
        return [baseColor[0], baseColor[1], baseColor[2], alpha];
      }
    }
    
    const normalized = Math.min(Math.max(value / 100, 0), 1);
    const r = Math.floor(255 * (1 - normalized));
    const g = Math.floor(100 + 155 * normalized);
    const b = Math.floor(100 + 100 * (1 - Math.abs(normalized - 0.5) * 2));
    return [r, g, b, 200];
  }

  _getPointRadius(index) {
    const base = 30;
    const value = this._preparedData.values[index];
    const valueBonus = value * 0.5;
    return Math.max(base + valueBonus, base);
  }

  getPointByIndex(index) {
    if (!this._preparedData || !this._preparedData.getPoint) {
      return null;
    }
    return this._preparedData.getPoint(index);
  }

  destroy() {
    this._layerCache.clear();
    this._preparedData = null;
    this.dataStore = null;
  }
}

export function createLayerManager(dataStore, options) {
  return new LayerManager(dataStore, options);
}

export { DEFAULT_COLOR_SCHEME, RADIUS_UNITS, HEATMAP_COLOR_SCHEMES };
