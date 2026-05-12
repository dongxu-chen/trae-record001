import * as THREE from 'three'

export function generateBrushedMetalTexture(size = 512) {
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')
  
  const imageData = ctx.createImageData(size, size)
  const data = imageData.data
  
  for (let i = 0; i < data.length; i += 4) {
    const y = Math.floor((i / 4) / size)
    const noise = (Math.random() - 0.5) * 20
    const base = 180 + Math.sin(y * 0.1) * 10 + noise
    
    data[i] = Math.min(255, Math.max(0, base))
    data[i + 1] = Math.min(255, Math.max(0, base + 5))
    data[i + 2] = Math.min(255, Math.max(0, base + 10))
    data[i + 3] = 255
  }
  
  ctx.putImageData(imageData, 0, 0)
  
  const texture = new THREE.CanvasTexture(canvas)
  texture.wrapS = THREE.RepeatWrapping
  texture.wrapT = THREE.RepeatWrapping
  texture.repeat.set(2, 2)
  texture.needsUpdate = true
  
  return texture
}

export function generateScratchedTexture(size = 512) {
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')
  
  ctx.fillStyle = '#888888'
  ctx.fillRect(0, 0, size, size)
  
  for (let i = 0; i < 200; i++) {
    const x1 = Math.random() * size
    const y1 = Math.random() * size
    const angle = Math.random() * Math.PI * 2
    const length = 20 + Math.random() * 100
    
    const x2 = x1 + Math.cos(angle) * length
    const y2 = y1 + Math.sin(angle) * length
    
    ctx.strokeStyle = `rgba(255, 255, 255, ${0.3 + Math.random() * 0.5})`
    ctx.lineWidth = 0.5 + Math.random() * 2
    ctx.beginPath()
    ctx.moveTo(x1, y1)
    ctx.lineTo(x2, y2)
    ctx.stroke()
  }
  
  const texture = new THREE.CanvasTexture(canvas)
  texture.wrapS = THREE.RepeatWrapping
  texture.wrapT = THREE.RepeatWrapping
  texture.repeat.set(1, 1)
  texture.needsUpdate = true
  
  return texture
}

export function generateHammersTexture(size = 512) {
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')
  
  ctx.fillStyle = '#666666'
  ctx.fillRect(0, 0, size, size)
  
  const gridSize = 40
  const cols = Math.ceil(size / gridSize)
  const rows = Math.ceil(size / gridSize)
  
  for (let i = 0; i < cols; i++) {
    for (let j = 0; j < rows; j++) {
      const cx = i * gridSize + gridSize / 2 + (Math.random() - 0.5) * 10
      const cy = j * gridSize + gridSize / 2 + (Math.random() - 0.5) * 10
      const radius = 12 + Math.random() * 8
      
      const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius)
      gradient.addColorStop(0, 'rgba(200, 200, 200, 0.8)')
      gradient.addColorStop(0.5, 'rgba(100, 100, 100, 0.6)')
      gradient.addColorStop(1, 'rgba(50, 50, 50, 0.3)')
      
      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.arc(cx, cy, radius, 0, Math.PI * 2)
      ctx.fill()
    }
  }
  
  const texture = new THREE.CanvasTexture(canvas)
  texture.wrapS = THREE.RepeatWrapping
  texture.wrapT = THREE.RepeatWrapping
  texture.repeat.set(1, 1)
  texture.needsUpdate = true
  
  return texture
}

export function getMetalnessMap(type) {
  switch (type) {
    case 'brushed':
      return generateBrushedMetalTexture()
    case 'scratched':
      return generateScratchedTexture()
    case 'hammers':
      return generateHammersTexture()
    default:
      return null
  }
}
