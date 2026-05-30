import React from 'react';

function Legend({ contours }) {
  const getContourColor = (elevation) => {
    const colors = [
      { max: 0, color: '#1a9850' },
      { max: 200, color: '#66bd63' },
      { max: 500, color: '#a6d96a' },
      { max: 1000, color: '#d9ef8b' },
      { max: 1500, color: '#fee08b' },
      { max: 2000, color: '#fdae61' },
      { max: 2500, color: '#f46d43' },
      { max: 3000, color: '#d73027' },
      { max: Infinity, color: '#a50026' }
    ];
    
    for (const range of colors) {
      if (elevation <= range.max) {
        return range.color;
      }
    }
    return '#a50026';
  };

  const elevations = contours.features
    .map(f => f.properties.elevation)
    .filter((v, i, a) => a.indexOf(v) === i)
    .sort((a, b) => a - b);

  const displayElevations = elevations.length > 10 
    ? elevations.filter((_, i) => i % Math.ceil(elevations.length / 10) === 0)
    : elevations;

  return (
    <div className="legend">
      <h4>🎨 高程图例</h4>
      {displayElevations.map((elevation, index) => (
        <div key={index} className="legend-item">
          <div 
            className="legend-color" 
            style={{ backgroundColor: getContourColor(elevation) }}
          />
          <span>{elevation} m</span>
        </div>
      ))}
    </div>
  );
}

export default Legend;
