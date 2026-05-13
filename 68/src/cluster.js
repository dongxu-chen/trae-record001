import Supercluster from 'supercluster';
import { ScatterplotLayer, TextLayer } from '@deck.gl/layers';

const DEFAULT_CLUSTER_OPTIONS = {
  radius: 40,
  maxZoom: 16,
  minPoints: 2
};

const CLUSTER_COLORS = {
  small: [255, 200, 100, 220],
  medium: [255, 140, 0, 220],
  large: [255, 60, 60, 220]
};

export class ClusterManager {
  constructor(dataStore, options = {}) {
    this.dataStore = dataStore;
    this.options = { ...DEFAULT_CLUSTER_OPTIONS, ...options };
    this.supercluster = null;
    this.currentZoom = 0;
    this.clustersCache = new Map();
    this._initialized = false;
  }

  async init() {
    if (this._initialized) return;
    
    const points = this._convertToGeoJSON();
    this.supercluster = new Supercluster(this.options);
    this.supercluster.load(points);
    this._initialized = true;
    
    console.log(`✅ 聚类管理器初始化完成: ${points.length} 个点`);
  }

  _convertToGeoJSON() {
    if (!this.dataStore) return [];
    
    const { count, positions, values, categories, timestamps } = this.dataStore;
    const features = [];
    
    for (let i = 0; i < count; i++) {
      const lng = positions[i * 2];
      const lat = positions[i * 2 + 1];
      
      features.push({
        type: 'Feature',
        properties: {
          id: i,
          value: values[i],
          category: categories[i],
          timestamp: timestamps[i],
          isCluster: false
        },
        geometry: {
          type: 'Point',
          coordinates: [lng, lat]
        }
      });
    }
    
    return features;
  }

  getClusters(zoom, bounds) {
    if (!this.supercluster) return { clusters: [], leaves: [] };
    
    const cacheKey = `${zoom.toFixed(1)}`;
    if (this.clustersCache.has(cacheKey)) {
      return this.clustersCache.get(cacheKey);
    }
    
    const mapBounds = bounds || [-180, -90, 180, 90];
    const clusters = this.supercluster.getClusters(mapBounds, Math.floor(zoom));
    
    const result = {
      clusters: [],
      leaves: []
    };
    
    clusters.forEach((cluster, index) => {
      const isCluster = cluster.properties?.cluster;
      const [lng, lat] = cluster.geometry.coordinates;
      
      const item = {
        id: isCluster ? cluster.properties.cluster_id : cluster.properties.id,
        longitude: lng,
        latitude: lat,
        isCluster,
        pointCount: isCluster ? cluster.properties.point_count : 1,
        pointCountAbbreviated: isCluster ? 
          this._formatCount(cluster.properties.point_count) : '',
        properties: cluster.properties,
        zoom,
        index
      };
      
      if (isCluster) {
        item.clusterId = cluster.properties.cluster_id;
        result.clusters.push(item);
      } else {
        result.leaves.push(item);
      }
    });
    
    this.clustersCache.set(cacheKey, result);
    
    if (this.clustersCache.size > 10) {
      const keys = this.clustersCache.keys();
      const firstKey = keys.next().value;
      this.clustersCache.delete(firstKey);
    }
    
    return result;
  }

  getClusterLeaves(clusterId, limit = 10, offset = 0) {
    if (!this.supercluster) return [];
    return this.supercluster.getLeaves(clusterId, limit, offset);
  }

  getClusterExpansionZoom(clusterId) {
    if (!this.supercluster) return 0;
    return this.supercluster.getClusterExpansionZoom(clusterId);
  }

  createClusterLayers(zoom, bounds, options = {}) {
    const {
      onClusterClick = null,
      onPointClick = null,
      onHover = null
    } = options;
    
    const { clusters, leaves } = this.getClusters(zoom, bounds);
    
    const layers = [];
    
    if (clusters.length > 0) {
      const clusterLayer = new ScatterplotLayer({
        id: 'cluster-points',
        data: clusters,
        pickable: true,
        opacity: 0.9,
        stroked: true,
        filled: true,
        radiusUnits: 'pixels',
        getPosition: (d) => [d.longitude, d.latitude],
        getRadius: (d) => this._getClusterRadius(d.pointCount),
        getFillColor: (d) => this._getClusterColor(d.pointCount),
        getLineColor: [255, 255, 255, 200],
        lineWidthMinPixels: 2,
        onClick: (info) => {
          if (info.object && onClusterClick) {
            onClusterClick(info.object, info);
          }
        },
        onHover
      });
      
      const labelLayer = new TextLayer({
        id: 'cluster-labels',
        data: clusters,
        pickable: false,
        getPosition: (d) => [d.longitude, d.latitude],
        getText: (d) => d.pointCountAbbreviated,
        getSize: 14,
        getAngle: 0,
        getTextAnchor: 'middle',
        getAlignmentBaseline: 'center',
        getPixelOffset: [0, 0],
        getColor: [255, 255, 255, 255],
        sizeScale: 1,
        sizeMinPixels: 10,
        sizeMaxPixels: 24
      });
      
      layers.push(clusterLayer, labelLayer);
    }
    
    if (leaves.length > 0) {
      const leavesLayer = new ScatterplotLayer({
        id: 'cluster-leaves',
        data: leaves,
        pickable: true,
        opacity: 0.85,
        stroked: false,
        filled: true,
        radiusUnits: 'meters',
        radiusScale: 30,
        radiusMinPixels: 2,
        radiusMaxPixels: 20,
        getPosition: (d) => [d.longitude, d.latitude],
        getFillColor: this._getLeafColor,
        getRadius: (d) => 20 + (d.properties?.value || 0) * 0.3,
        onClick: (info) => {
          if (info.object && onPointClick) {
            onPointClick(info.object, info);
          }
        },
        onHover
      });
      
      layers.push(leavesLayer);
    }
    
    return layers;
  }

  _getClusterRadius(pointCount) {
    const baseRadius = 15;
    const maxRadius = 40;
    const scale = Math.min(pointCount / 100, 1);
    return baseRadius + scale * (maxRadius - baseRadius);
  }

  _getClusterColor(pointCount) {
    if (pointCount >= 100) {
      return CLUSTER_COLORS.large;
    } else if (pointCount >= 10) {
      return CLUSTER_COLORS.medium;
    }
    return CLUSTER_COLORS.small;
  }

  _getLeafColor(d) {
    const value = d.properties?.value || 50;
    const category = d.properties?.category;
    
    const categoryColors = {
      0: [255, 100, 100, 200],
      1: [100, 200, 255, 200],
      2: [100, 255, 150, 200],
      3: [255, 200, 100, 200]
    };
    
    if (category !== undefined && category !== 255 && categoryColors[category]) {
      return categoryColors[category];
    }
    
    const normalized = Math.min(Math.max(value / 100, 0), 1);
    const r = Math.floor(255 * (1 - normalized));
    const g = Math.floor(100 + 155 * normalized);
    const b = Math.floor(100 + 100 * (1 - Math.abs(normalized - 0.5) * 2));
    return [r, g, b, 200];
  }

  _formatCount(count) {
    if (count >= 1000) {
      return (count / 1000).toFixed(1) + 'k';
    }
    return count.toString();
  }

  clearCache() {
    this.clustersCache.clear();
  }

  destroy() {
    this.supercluster = null;
    this.dataStore = null;
    this.clearCache();
    this._initialized = false;
  }
}

export function createClusterManager(dataStore, options) {
  return new ClusterManager(dataStore, options);
}

export { DEFAULT_CLUSTER_OPTIONS, CLUSTER_COLORS };
