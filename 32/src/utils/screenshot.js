import * as THREE from 'three'

export function takeScreenshot(gl) {
  const width = gl.drawingBufferWidth
  const height = gl.drawingBufferHeight
  const pixels = new Uint8Array(width * height * 4)
  
  gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels)
  
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  
  const imageData = ctx.createImageData(width, height)
  
  for (let i = 0; i < pixels.length; i += 4) {
    const row = Math.floor(i / 4 / width)
    const col = (i / 4) % width
    const targetRow = height - 1 - row
    const targetIndex = (targetRow * width + col) * 4
    
    imageData.data[targetIndex] = pixels[i]
    imageData.data[targetIndex + 1] = pixels[i + 1]
    imageData.data[targetIndex + 2] = pixels[i + 2]
    imageData.data[targetIndex + 3] = 255
  }
  
  ctx.putImageData(imageData, 0, 0)
  
  return canvas.toDataURL('image/png')
}

export function downloadScreenshot(dataUrl, filename = 'screenshot.png') {
  const link = document.createElement('a')
  link.download = filename
  link.href = dataUrl
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

export function captureAndDownload(gl, filename = 'product-config.png') {
  const dataUrl = takeScreenshot(gl)
  downloadScreenshot(dataUrl, filename)
  return dataUrl
}
