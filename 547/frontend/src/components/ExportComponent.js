import React, { useState, useCallback } from 'react';

function ExportComponent({ contours, bounds }) {
  const [exportFormat, setExportFormat] = useState('geojson');
  const [includeProperties, setIncludeProperties] = useState(true);
  const [exportStatus, setExportStatus] = useState('');

  const exportGeoJSON = useCallback(() => {
    if (!contours || !contours.features || contours.features.length === 0) {
      setExportStatus('❌ 没有可导出的等高线数据');
      return;
    }

    try {
      let exportData;

      if (exportFormat === 'geojson') {
        exportData = generateStandardGeoJSON();
      } else if (exportFormat === 'geojson-3d') {
        exportData = generate3DGeoJSON();
      } else if (exportFormat === 'shapefile-json') {
        exportData = generateShapefileJSON();
      }

      const jsonString = JSON.stringify(exportData, null, 2);
      const blob = new Blob([jsonString], { type: 'application/geo+json' });
      const url = URL.createObjectURL(blob);

      const link = document.createElement('a');
      link.href = url;
      link.download = `contours_${exportFormat}_${Date.now()}.geojson`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setExportStatus(`✅ 已导出 ${contours.features.length} 条等高线`);
      setTimeout(() => setExportStatus(''), 3000);
    } catch (error) {
      setExportStatus('❌ 导出失败: ' + error.message);
    }
  }, [contours, exportFormat, includeProperties, bounds]);

  const generateStandardGeoJSON = () => {
    const features = contours.features.map(feature => {
      const props = includeProperties ? { ...feature.properties } : {
        elevation: feature.properties.elevation
      };

      return {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: feature.geometry.coordinates
        },
        properties: {
          ...props,
          contour_interval: props.elevation,
          contour_type: props.elevation % 250 === 0 ? 'major' : 'minor'
        }
      };
    });

    return {
      type: 'FeatureCollection',
      name: 'contour_lines',
      crs: {
        type: 'name',
        properties: {
          name: 'urn:ogc:def:crs:EPSG::4326'
        }
      },
      features: features,
      metadata: {
        generatedAt: new Date().toISOString(),
        totalFeatures: features.length,
        bounds: bounds || {},
        source: 'Contour Extractor Tool'
      }
    };
  };

  const generate3DGeoJSON = () => {
    const features = contours.features.map((feature, idx) => {
      const elevation = feature.properties.elevation;
      const coords3D = feature.geometry.coordinates.map(c => [c[0], c[1], elevation]);

      return {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: coords3D
        },
        properties: {
          id: idx + 1,
          elevation: elevation,
          contour_interval: elevation,
          point_count: feature.geometry.coordinates.length,
          contour_type: elevation % 250 === 0 ? 'major' : 'minor'
        }
      };
    });

    return {
      type: 'FeatureCollection',
      name: 'contour_lines_3d',
      crs: {
        type: 'name',
        properties: {
          name: 'urn:ogc:def:crs:EPSG::4979'
        }
      },
      features: features,
      metadata: {
        generatedAt: new Date().toISOString(),
        totalFeatures: features.length,
        is3D: true,
        bounds: bounds || {},
        source: 'Contour Extractor Tool'
      }
    };
  };

  const generateShapefileJSON = () => {
    const features = contours.features.map((feature, idx) => {
      return {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: feature.geometry.coordinates
        },
        properties: {
          FID: idx + 1,
          ELEV: feature.properties.elevation,
          CONTOUR: feature.properties.elevation,
          TYPE: feature.properties.elevation % 250 === 0 ? 1 : 0,
          LENGTH_KM: calculateLength(feature.geometry.coordinates)
        }
      };
    });

    return {
      type: 'FeatureCollection',
      name: 'contour_lines',
      crs: {
        type: 'name',
        properties: {
          name: 'urn:ogc:def:crs:EPSG::4326'
        }
      },
      features: features
    };
  };

  const calculateLength = (coords) => {
    let length = 0;
    for (let i = 1; i < coords.length; i++) {
      const dLat = (coords[i][1] - coords[i - 1][1]) * Math.PI / 180;
      const dLon = (coords[i][0] - coords[i - 1][0]) * Math.PI / 180;
      const a = Math.sin(dLat / 2) ** 2 +
        Math.cos(coords[i - 1][1] * Math.PI / 180) *
        Math.cos(coords[i][1] * Math.PI / 180) *
        Math.sin(dLon / 2) ** 2;
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      length += 6371 * c;
    }
    return Math.round(length * 1000) / 1000;
  };

  const getFeatureCount = () => {
    if (!contours || !contours.features) return 0;
    return contours.features.length;
  };

  const getElevationRange = () => {
    if (!contours || !contours.features || contours.features.length === 0) return '-';
    const elevations = contours.features.map(f => f.properties.elevation);
    return `${Math.min(...elevations)}m - ${Math.max(...elevations)}m`;
  };

  const getTotalPoints = () => {
    if (!contours || !contours.features) return 0;
    return contours.features.reduce((sum, f) => sum + (f.geometry.coordinates?.length || 0), 0);
  };

  return (
    <div className="export-panel">
      <h3>📤 导出GeoJSON</h3>

      <div className="export-info">
        <div className="export-info-item">
          <span>等高线数量</span>
          <strong>{getFeatureCount()}</strong>
        </div>
        <div className="export-info-item">
          <span>高程范围</span>
          <strong>{getElevationRange()}</strong>
        </div>
        <div className="export-info-item">
          <span>总坐标点</span>
          <strong>{getTotalPoints()}</strong>
        </div>
      </div>

      <div className="form-group">
        <label>导出格式</label>
        <select
          value={exportFormat}
          onChange={(e) => setExportFormat(e.target.value)}
        >
          <option value="geojson">GeoJSON (标准 2D)</option>
          <option value="geojson-3d">GeoJSON (3D 含高程)</option>
          <option value="shapefile-json">Shapefile 兼容格式</option>
        </select>
      </div>

      <div className="form-group">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={includeProperties}
            onChange={(e) => setIncludeProperties(e.target.checked)}
          />
          包含完整属性信息
        </label>
      </div>

      {exportFormat === 'geojson' && (
        <div className="export-hint">
          标准WGS84坐标系(EPSG:4326)，可直接导入QGIS/ArcGIS
        </div>
      )}
      {exportFormat === 'geojson-3d' && (
        <div className="export-hint">
          3D坐标(EPSG:4979)，含Z值高程，支持3D GIS分析
        </div>
      )}
      {exportFormat === 'shapefile-json' && (
        <div className="export-hint">
          Shapefield兼容属性名，可直接用ogr2ogr转换
        </div>
      )}

      <button
        className="btn btn-export"
        onClick={exportGeoJSON}
        disabled={!contours || getFeatureCount() === 0}
      >
        📥 导出GeoJSON文件
      </button>

      {exportStatus && (
        <div className={`export-status ${exportStatus.startsWith('✅') ? 'success' : 'error'}`}>
          {exportStatus}
        </div>
      )}
    </div>
  );
}

export default ExportComponent;
