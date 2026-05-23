import React, { useState, useRef } from 'react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';

const MAX_WAYPOINTS = 10;

const PRESET_LOCATIONS = {
  beijing: { name: '北京', lng: 116.4074, lat: 39.9042 },
  shanghai: { name: '上海', lng: 121.4737, lat: 31.2304 },
  guangzhou: { name: '广州', lng: 113.2644, lat: 23.1291 },
  shenzhen: { name: '深圳', lng: 114.0579, lat: 22.5431 },
  chengdu: { name: '成都', lng: 104.0668, lat: 30.5728 },
  hangzhou: { name: '杭州', lng: 120.1551, lat: 30.2741 },
  nanjing: { name: '南京', lng: 118.7969, lat: 32.0603 },
  wuhan: { name: '武汉', lng: 114.3055, lat: 30.5931 },
};

function RouteForm({ onCalculate, loading, waypoints, onWaypointsReorder, routeData, onGenerateShare }) {
  const [originLng, setOriginLng] = useState('116.4074');
  const [originLat, setOriginLat] = useState('39.9042');
  const [destLng, setDestLng] = useState('121.4737');
  const [destLat, setDestLat] = useState('31.2304');
  const [localWaypoints, setLocalWaypoints] = useState([]);
  const [errors, setErrors] = useState({});
  const draggedIndex = useRef(null);

  const isValidLng = (lng) => {
    const num = parseFloat(lng);
    return !isNaN(num) && num >= -180 && num <= 180;
  };

  const isValidLat = (lat) => {
    const num = parseFloat(lat);
    return !isNaN(num) && num >= -90 && num <= 90;
  };

  const validate = () => {
    const newErrors = {};
    if (!isValidLng(originLng)) newErrors.originLng = '经度无效';
    if (!isValidLat(originLat)) newErrors.originLat = '纬度无效';
    if (!isValidLng(destLng)) newErrors.destLng = '经度无效';
    if (!isValidLat(destLat)) newErrors.destLat = '纬度无效';

    localWaypoints.forEach((wp, idx) => {
      if (!isValidLng(wp.lng)) newErrors[`wp${idx}lng`] = '经度无效';
      if (!isValidLat(wp.lat)) newErrors[`wp${idx}lat`] = '纬度无效';
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;

    const origin = { lng: parseFloat(originLng), lat: parseFloat(originLat) };
    const destination = { lng: parseFloat(destLng), lat: parseFloat(destLat) };
    const wp = localWaypoints
      .filter(wp => wp.lng && wp.lat)
      .map(wp => ({ lng: parseFloat(wp.lng), lat: parseFloat(wp.lat) }));

    onCalculate(origin, destination, wp);
  };

  const addWaypoint = () => {
    if (localWaypoints.length >= MAX_WAYPOINTS) return;
    setLocalWaypoints([...localWaypoints, { lng: '', lat: '' }]);
  };

  const removeWaypoint = (index) => {
    const newWaypoints = localWaypoints.filter((_, i) => i !== index);
    setLocalWaypoints(newWaypoints);
    if (routeData) {
      onWaypointsReorder(newWaypoints.filter(wp => wp.lng && wp.lat).map(wp => ({
        lng: parseFloat(wp.lng),
        lat: parseFloat(wp.lat)
      })));
    }
  };

  const updateWaypoint = (index, field, value) => {
    const newWaypoints = [...localWaypoints];
    newWaypoints[index][field] = value;
    setLocalWaypoints(newWaypoints);
  };

  const handleDragStart = (start) => {
    draggedIndex.current = start.source.index;
  };

  const handleDragEnd = (result) => {
    if (!result.destination) return;

    const items = Array.from(localWaypoints);
    const [reorderedItem] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reorderedItem);

    setLocalWaypoints(items);
    draggedIndex.current = null;

    if (routeData) {
      const validWaypoints = items
        .filter(wp => wp.lng && wp.lat && isValidLng(wp.lng) && isValidLat(wp.lat))
        .map(wp => ({ lng: parseFloat(wp.lng), lat: parseFloat(wp.lat) }));
      onWaypointsReorder(validWaypoints);
    }
  };

  const applyPreset = (locationKey, type) => {
    const loc = PRESET_LOCATIONS[locationKey];
    if (type === 'origin') {
      setOriginLng(loc.lng.toString());
      setOriginLat(loc.lat.toString());
    } else if (type === 'destination') {
      setDestLng(loc.lng.toString());
      setDestLat(loc.lat.toString());
    }
  };

  const applyPresetRoute = () => {
    setOriginLng(PRESET_LOCATIONS.beijing.lng.toString());
    setOriginLat(PRESET_LOCATIONS.beijing.lat.toString());
    setDestLng(PRESET_LOCATIONS.shanghai.lng.toString());
    setDestLat(PRESET_LOCATIONS.shanghai.lat.toString());
    setLocalWaypoints([
      { lng: PRESET_LOCATIONS.nanjing.lng.toString(), lat: PRESET_LOCATIONS.nanjing.lat.toString() },
      { lng: PRESET_LOCATIONS.hangzhou.lng.toString(), lat: PRESET_LOCATIONS.hangzhou.lat.toString() },
    ]);
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-section">
        <h3>📍 起点</h3>
        <label className="label">经度 (Lng)</label>
        <div className="coord-input">
          <input
            type="number"
            step="0.0001"
            value={originLng}
            onChange={(e) => setOriginLng(e.target.value)}
            className={errors.originLng ? 'invalid' : ''}
            placeholder="例如: 116.4074"
          />
        </div>
        <label className="label">纬度 (Lat)</label>
        <div className="coord-input">
          <input
            type="number"
            step="0.0001"
            value={originLat}
            onChange={(e) => setOriginLat(e.target.value)}
            className={errors.originLat ? 'invalid' : ''}
            placeholder="例如: 39.9042"
          />
        </div>
        <p className="input-hint">东经为正，北纬为正</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {Object.entries(PRESET_LOCATIONS).map(([key, loc]) => (
            <button
              key={key}
              type="button"
              className="preset-btn"
              onClick={() => applyPreset(key, 'origin')}
            >
              {loc.name}
            </button>
          ))}
        </div>
      </div>

      <div className="form-section">
        <h3>🏁 终点</h3>
        <label className="label">经度 (Lng)</label>
        <div className="coord-input">
          <input
            type="number"
            step="0.0001"
            value={destLng}
            onChange={(e) => setDestLng(e.target.value)}
            className={errors.destLng ? 'invalid' : ''}
            placeholder="例如: 121.4737"
          />
        </div>
        <label className="label">纬度 (Lat)</label>
        <div className="coord-input">
          <input
            type="number"
            step="0.0001"
            value={destLat}
            onChange={(e) => setDestLat(e.target.value)}
            className={errors.destLat ? 'invalid' : ''}
            placeholder="例如: 31.2304"
          />
        </div>
        <p className="input-hint">东经为正，北纬为正</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {Object.entries(PRESET_LOCATIONS).map(([key, loc]) => (
            <button
              key={key}
              type="button"
              className="preset-btn"
              onClick={() => applyPreset(key, 'destination')}
            >
              {loc.name}
            </button>
          ))}
        </div>
      </div>

      <div className="form-section">
        <h3>🔄 途经点 ({localWaypoints.length}/{MAX_WAYPOINTS})</h3>
        <p className="input-hint">拖拽调整途经点顺序</p>

        <DragDropContext onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
          <Droppable droppableId="waypoints">
            {(provided, snapshot) => (
              <div
                {...provided.droppableProps}
                ref={provided.innerRef}
                className="waypoint-list"
              >
                {localWaypoints.map((wp, index) => (
                  <Draggable
                    key={`wp-${index}`}
                    draggableId={`waypoint-${index}`}
                    index={index}
                  >
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        className={`waypoint-item ${snapshot.isDragging ? 'dragging' : ''}`}
                      >
                        <span {...provided.dragHandleProps} className="drag-handle">
                          ⋮⋮
                        </span>
                        <span className="waypoint-number">{index + 1}</span>
                        <div className="waypoint-coord">
                          <input
                            type="number"
                            step="0.0001"
                            value={wp.lng}
                            onChange={(e) => updateWaypoint(index, 'lng', e.target.value)}
                            className={errors[`wp${index}lng`] ? 'invalid' : ''}
                            placeholder="经度"
                          />
                          <input
                            type="number"
                            step="0.0001"
                            value={wp.lat}
                            onChange={(e) => updateWaypoint(index, 'lat', e.target.value)}
                            className={errors[`wp${index}lat`] ? 'invalid' : ''}
                            placeholder="纬度"
                          />
                        </div>
                        <button
                          type="button"
                          className="remove-btn"
                          onClick={() => removeWaypoint(index)}
                        >
                          ×
                        </button>
                      </div>
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
              </div>
            )}
          </Droppable>
        </DragDropContext>

        {localWaypoints.length < MAX_WAYPOINTS ? (
          <button
            type="button"
            className="add-btn"
            onClick={addWaypoint}
            disabled={loading}
          >
            + 添加途经点
          </button>
        ) : (
          <p className="max-reached">已达到最大途经点数量</p>
        )}
      </div>

      <div className="form-section">
        <button
          type="button"
          className="preset-btn"
          onClick={applyPresetRoute}
          style={{ width: '100%' }}
        >
          🚀 加载示例路线 (北京→南京→杭州→上海)
        </button>
        <button
          type="submit"
          className="calculate-btn"
          disabled={loading}
        >
          {loading && <span className="loading"></span>}
          {loading ? '计算路线中...' : '计算最优路线'}
        </button>
        {routeData && (
          <button
            type="button"
            className="share-btn"
            onClick={onGenerateShare}
          >
            📤 分享这条路线
          </button>
        )}
      </div>
    </form>
  );
}

export default RouteForm;
