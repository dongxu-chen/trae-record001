import { HeatmapLayer } from '@deck.gl/aggregation-layers';
import { ScatterplotLayer } from '@deck.gl/layers';

const DEFAULT_HEATMAP_OPTIONS = {
  radiusPixels: 60,
  intensity: 1,
  threshold: 0.05,
  colorRange: [
    [255, 255, 178],
    [254, 217, 118],
    [254, 178, 76],
    [253, 141, 60],
    [240, 59, 32],
    [189, 0, 38]
  ]
};

const VIRIDIS_COLOR_RANGE = [
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
];

const PLASMA_COLOR_RANGE = [
  [13, 8, 135],
  [75, 3, 161],
  [125, 3, 168],
  [168, 34, 150],
  [203, 70, 121],
  [229, 107, 93],
  [248, 148, 65],
  [253, 195, 40],
  [240, 249, 33]
];

const COLOR_SCHEMES = {
  default: DEFAULT_HEATMAP_OPTIONS.colorRange,
  viridis: VIRIDIS_COLOR_RANGE,
  plasma: PLASMA_COLOR_RANGE,
  hot: [
    [0, 0, 0],
    [127, 0, 0],
    [255, 0, 0],
    [255, 127, 0],
    [255, 255, 0],
    [255, 255, 255]
  ],
  cool: [
    [0, 255, 255],
    [0, 191, 255],
    [0, 127, 255],
    [0, 63, 255],
    [0, 0, 255],
    [63, 0, 191]
  ]
};

export class HeatmapManager {
  constructor(dataStore, options = {}) {
    this.dataStore = dataStore;
    this.options = { ...DEFAULT_HEATMAP_OPTIONS, ...options };
    this._preparedData = null;
    this._initializeData();
  }

  _initializeData() {
    if (!this.dataStore) {
      this._preparedData = [];
      return;
    }

    const { count, positions, values } = this.dataStore;
    this._preparedData = new Array(count);
    
    for (let i = 0; i < count; i++) {
      this._preparedData[i] = {
        position: [positions[i * 2], positions[i * 2 + 1]],
        weight: values[i] || 1
      };
    }
    
    console.log(`✅ 热力图数据准备完成: ${count} 个点`);
  }

  setColorScheme(schemeName) {
    if (COLOR_SCHEMES[schemeName]) {
      this.options.colorRange = COLOR_SCHEMES[schemeName];
    }
  }

  setOptions(options) {
    this.options = { ...this.options, ...options };
  }

  getPreparedData() {
    return this._preparedData;
  }

  createHeatmapLayer(options = {}) {
    const mergedOptions = { ...this.options, ...options };
    const {
      id = 'heatmap-layer',
      radiusPixels,
      intensity,
      threshold,
      colorRange,
      onHover = null,
      onClick = null
    } = mergedOptions;

    return new HeatmapLayer({
      id,
      data: this._preparedData,
      radiusPixels,
      intensity,
      threshold,
      colorRange,
      pickable: !!(onHover || onClick),
      aggregation: 'SUM',
      getPosition: (d) => d.position,
      getWeight: (d) => d.weight,
      onHover,
      onClick
    });
  }

  createDualModeLayers(options = {}) {
    const {
      showPoints = false,
      pointOpacity = 0.3,
      ...heatmapOptions
    } = options;
    
    const layers = [this.createHeatmapLayer(heatmapOptions)];
    
    if (showPoints && this.dataStore) {
      const pointsLayer = new ScatterplotLayer({
        id: 'heatmap-overlay-points',
        data: this._preparedData,
        pickable: false,
        opacity: pointOpacity,
        stroked: false,
        filled: true,
        radiusUnits: 'pixels',
        radiusMinPixels: 1,
        radiusMaxPixels: 5,
        getPosition: (d) => d.position,
        getFillColor: [255, 255, 255, 150],
        getRadius: 2
      });
      layers.push(pointsLayer);
    }
    
    return layers;
  }

  createAnimatedHeatmapLayer(timeFilter, options = {}) {
    if (!this.dataStore || !timeFilter) {
      return this.createHeatmapLayer(options);
    }

    const { positions, values, timestamps, count } = this.dataStore;
    const filteredData = [];
    
    for (let i = 0; i < count; i++) {
      const ts = timestamps[i];
      if (timeFilter(ts)) {
        filteredData.push({
          position: [positions[i * 2], positions[i * 2 + 1]],
          weight: values[i] || 1
        });
      }
    }
    
    const mergedOptions = { ...this.options, ...options };
    
    return new HeatmapLayer({
      id: 'animated-heatmap-layer',
      data: filteredData,
      radiusPixels: mergedOptions.radiusPixels,
      intensity: mergedOptions.intensity,
      threshold: mergedOptions.threshold,
      colorRange: mergedOptions.colorRange,
      pickable: false,
      aggregation: 'SUM',
      getPosition: (d) => d.position,
      getWeight: (d) => d.weight
    });
  }

  destroy() {
    this._preparedData = null;
    this.dataStore = null;
  }
}

export function createHeatmapManager(dataStore, options) {
  return new HeatmapManager(dataStore, options);
}

export { 
  DEFAULT_HEATMAP_OPTIONS, 
  COLOR_SCHEMES, 
  VIRIDIS_COLOR_RANGE, 
  PLASMA_COLOR_RANGE 
};
