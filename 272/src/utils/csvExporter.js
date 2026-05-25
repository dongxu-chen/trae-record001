export const exportToCSV = (data, filename = 'heatmap_data.csv', options = {}) => {
  const {
    latField = 'lat',
    lngField = 'lng',
    valueField = 'value',
    includeHeaders = true,
    delimiter = ','
  } = options

  if (!data || data.length === 0) {
    console.warn('No data to export')
    return false
  }

  let csvContent = ''

  if (includeHeaders) {
    csvContent += `latitude${delimiter}longitude${delimiter}value\n`
  }

  for (let i = 0; i < data.length; i++) {
    const point = data[i]
    const lat = point[latField] != null ? point[latField] : ''
    const lng = point[lngField] != null ? point[lngField] : ''
    const value = point[valueField] != null ? point[valueField] : ''
    
    csvContent += `${lat}${delimiter}${lng}${delimiter}${value}\n`
  }

  const BOM = '\uFEFF'
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' })

  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  
  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  URL.revokeObjectURL(url)
  
  return true
}

export const exportGeoJSON = (data, filename = 'heatmap_data.geojson', options = {}) => {
  const {
    latField = 'lat',
    lngField = 'lng',
    valueField = 'value'
  } = options

  if (!data || data.length === 0) {
    console.warn('No data to export')
    return false
  }

  const features = data.map((point) => ({
    type: 'Feature',
    properties: {
      value: point[valueField]
    },
    geometry: {
      type: 'Point',
      coordinates: [point[lngField], point[latField]]
    }
  }))

  const geoJSON = {
    type: 'FeatureCollection',
    features: features
  }

  const blob = new Blob([JSON.stringify(geoJSON, null, 2)], { type: 'application/json' })
  
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  
  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  URL.revokeObjectURL(url)
  
  return true
}

export const filterDataByBounds = (data, bounds, options = {}) => {
  const {
    latField = 'lat',
    lngField = 'lng'
  } = options

  if (!data || data.length === 0 || !bounds) {
    return []
  }

  const filtered = []
  
  for (let i = 0; i < data.length; i++) {
    const point = data[i]
    const lat = point[latField]
    const lng = point[lngField]
    
    if (lat >= bounds.south && lat <= bounds.north &&
        lng >= bounds.west && lng <= bounds.east) {
      filtered.push(point)
    }
  }
  
  return filtered
}

export const getBoundsStats = (data, bounds, options = {}) => {
  const filteredData = filterDataByBounds(data, bounds, options)
  
  if (filteredData.length === 0) {
    return {
      count: 0,
      minValue: 0,
      maxValue: 0,
      avgValue: 0,
      sumValue: 0,
      data: []
    }
  }
  
  const valueField = options.valueField || 'value'
  let sumValue = 0
  let minValue = Infinity
  let maxValue = -Infinity
  
  for (let i = 0; i < filteredData.length; i++) {
    const value = filteredData[i][valueField] || 0
    sumValue += value
    if (value < minValue) minValue = value
    if (value > maxValue) maxValue = value
  }
  
  return {
    count: filteredData.length,
    minValue,
    maxValue,
    avgValue: sumValue / filteredData.length,
    sumValue,
    data: filteredData
  }
}
