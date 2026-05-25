export const generateRandomPoints = (count, centerLat, centerLng, radius = 0.1) => {
  const points = []
  
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2
    const distance = Math.sqrt(Math.random()) * radius
    
    const lat = centerLat + distance * Math.cos(angle)
    const lng = centerLng + distance * Math.sin(angle)
    
    const value = Math.floor(Math.random() * 100) + 1
    
    points.push({
      lat,
      lng,
      value
    })
  }
  
  return points
}

export const generateClusterPoints = (clusterCount, pointsPerCluster, centerLat, centerLng, spread = 0.5) => {
  const points = []
  
  for (let c = 0; c < clusterCount; c++) {
    const clusterLat = centerLat + (Math.random() - 0.5) * spread
    const clusterLng = centerLng + (Math.random() - 0.5) * spread
    const clusterRadius = 0.02 + Math.random() * 0.05
    
    for (let i = 0; i < pointsPerCluster; i++) {
      const angle = Math.random() * Math.PI * 2
      const distance = Math.sqrt(Math.random()) * clusterRadius
      
      points.push({
        lat: clusterLat + distance * Math.cos(angle),
        lng: clusterLng + distance * Math.sin(angle),
        value: Math.floor(Math.random() * 80) + 20
      })
    }
  }
  
  return points
}

export const generateMillionPoints = (centerLat = 39.9042, centerLng = 116.4074) => {
  return new Promise((resolve) => {
    const chunkSize = 100000
    const totalChunks = 10
    let points = []
    let chunkIndex = 0
    
    const generateChunk = () => {
      const chunk = []
      for (let i = 0; i < chunkSize; i++) {
        const lat = centerLat + (Math.random() - 0.5) * 2
        const lng = centerLng + (Math.random() - 0.5) * 2
        const value = Math.floor(Math.random() * 100) + 1
        
        chunk.push({ lat, lng, value })
      }
      
      points = points.concat(chunk)
      chunkIndex++
      
      if (chunkIndex < totalChunks) {
        setTimeout(generateChunk, 10)
      } else {
        resolve(points)
      }
    }
    
    generateChunk()
  })
}

export const getMaxValue = (points, valueField = 'value') => {
  if (!points || points.length === 0) return 100
  return Math.max(...points.map(p => p[valueField] || 0))
}
