class AIBackgroundRemover {
  constructor() {
    this.workerCanvas = document.createElement('canvas')
    this.workerCtx = this.workerCanvas.getContext('2d')
  }

  removeBackground(imageElement, options = {}) {
    return new Promise((resolve) => {
      const {
        method = 'auto',
        threshold = 30,
        colorTolerance = 40,
        edgeDetection = true
      } = options

      const width = imageElement.naturalWidth || imageElement.width
      const height = imageElement.naturalHeight || imageElement.height

      this.workerCanvas.width = width
      this.workerCanvas.height = height
      this.workerCtx.drawImage(imageElement, 0, 0)

      const imageData = this.workerCtx.getImageData(0, 0, width, height)
      const data = imageData.data

      let backgroundColor = { r: 255, g: 255, b: 255 }
      
      if (method === 'auto') {
        backgroundColor = this.detectBackgroundColor(data, width, height)
      } else if (method === 'green') {
        backgroundColor = { r: 0, g: 255, b: 0 }
      } else if (method === 'blue') {
        backgroundColor = { r: 0, g: 0, b: 255 }
      } else if (method === 'custom' && options.backgroundColor) {
        backgroundColor = options.backgroundColor
      }

      this.removeColorBackground(data, width, height, backgroundColor, colorTolerance)

      if (edgeDetection) {
        this.applyEdgeSmoothing(data, width, height)
      }

      this.workerCtx.putImageData(imageData, 0, 0)

      const resultCanvas = document.createElement('canvas')
      resultCanvas.width = width
      resultCanvas.height = height
      const resultCtx = resultCanvas.getContext('2d')
      resultCtx.drawImage(this.workerCanvas, 0, 0)

      resolve(resultCanvas)
    })
  }

  detectBackgroundColor(data, width, height) {
    const sampleSize = 5
    const edgePixels = []

    for (let x = 0; x < width; x += Math.ceil(width / sampleSize)) {
      for (let y = 0; y < sampleSize; y++) {
        const i = (y * width + x) * 4
        edgePixels.push({ r: data[i], g: data[i + 1], b: data[i + 2] })
      }
      for (let y = height - sampleSize; y < height; y++) {
        const i = (y * width + x) * 4
        edgePixels.push({ r: data[i], g: data[i + 1], b: data[i + 2] })
      }
    }

    for (let y = 0; y < height; y += Math.ceil(height / sampleSize)) {
      for (let x = 0; x < sampleSize; x++) {
        const i = (y * width + x) * 4
        edgePixels.push({ r: data[i], g: data[i + 1], b: data[i + 2] })
      }
      for (let x = width - sampleSize; x < width; x++) {
        const i = (y * width + x) * 4
        edgePixels.push({ r: data[i], g: data[i + 1], b: data[i + 2] })
      }
    }

    const colorCounts = {}
    edgePixels.forEach(pixel => {
      const key = `${Math.round(pixel.r / 20) * 20},${Math.round(pixel.g / 20) * 20},${Math.round(pixel.b / 20) * 20}`
      colorCounts[key] = (colorCounts[key] || 0) + 1
    })

    let maxCount = 0
    let dominantColor = { r: 255, g: 255, b: 255 }
    
    Object.entries(colorCounts).forEach(([key, count]) => {
      if (count > maxCount) {
        maxCount = count
        const [r, g, b] = key.split(',').map(Number)
        dominantColor = { r, g, b }
      }
    })

    return dominantColor
  }

  removeColorBackground(data, width, height, targetColor, tolerance) {
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const i = (y * width + x) * 4
        
        const r = data[i]
        const g = data[i + 1]
        const b = data[i + 2]

        const distance = Math.sqrt(
          Math.pow(r - targetColor.r, 2) +
          Math.pow(g - targetColor.g, 2) +
          Math.pow(b - targetColor.b, 2)
        )

        if (distance < tolerance) {
          const alpha = Math.max(0, Math.min(1, distance / tolerance))
          data[i + 3] = Math.round(alpha * 255)
        }
      }
    }
  }

  applyEdgeSmoothing(data, width, height) {
    const tempData = new Uint8ClampedArray(data)
    const kernelSize = 3
    const halfKernel = Math.floor(kernelSize / 2)

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const i = (y * width + x) * 4
        
        if (data[i + 3] > 0 && data[i + 3] < 255) {
          let alphaSum = 0
          let alphaCount = 0

          for (let ky = -halfKernel; ky <= halfKernel; ky++) {
            for (let kx = -halfKernel; kx <= halfKernel; kx++) {
              const ny = y + ky
              const nx = x + kx
              
              if (ny >= 0 && ny < height && nx >= 0 && nx < width) {
                const ni = (ny * width + nx) * 4
                alphaSum += tempData[ni + 3]
                alphaCount++
              }
            }
          }

          data[i + 3] = Math.round(alphaSum / alphaCount)
        }
      }
    }
  }

  magicWand(imageElement, startX, startY, tolerance = 30) {
    return new Promise((resolve) => {
      const width = imageElement.naturalWidth || imageElement.width
      const height = imageElement.naturalHeight || imageElement.height

      this.workerCanvas.width = width
      this.workerCanvas.height = height
      this.workerCtx.drawImage(imageElement, 0, 0)

      const imageData = this.workerCtx.getImageData(0, 0, width, height)
      const data = imageData.data

      const startI = (Math.floor(startY) * width + Math.floor(startX)) * 4
      const targetColor = {
        r: data[startI],
        g: data[startI + 1],
        b: data[startI + 2]
      }

      const visited = new Set()
      const stack = [[Math.floor(startX), Math.floor(startY)]]

      while (stack.length > 0) {
        const [x, y] = stack.pop()
        const key = `${x},${y}`

        if (visited.has(key)) continue
        if (x < 0 || x >= width || y < 0 || y >= height) continue

        visited.add(key)

        const i = (y * width + x) * 4
        const r = data[i]
        const g = data[i + 1]
        const b = data[i + 2]

        const distance = Math.sqrt(
          Math.pow(r - targetColor.r, 2) +
          Math.pow(g - targetColor.g, 2) +
          Math.pow(b - targetColor.b, 2)
        )

        if (distance < tolerance) {
          data[i + 3] = 0

          stack.push([x + 1, y])
          stack.push([x - 1, y])
          stack.push([x, y + 1])
          stack.push([x, y - 1])
        }
      }

      this.workerCtx.putImageData(imageData, 0, 0)

      const resultCanvas = document.createElement('canvas')
      resultCanvas.width = width
      resultCanvas.height = height
      const resultCtx = resultCanvas.getContext('2d')
      resultCtx.drawImage(this.workerCanvas, 0, 0)

      resolve(resultCanvas)
    })
  }

  dispose() {
    this.workerCanvas.width = 1
    this.workerCanvas.height = 1
    this.workerCanvas = null
    this.workerCtx = null
  }
}

export const aiBackgroundRemover = new AIBackgroundRemover()
export default AIBackgroundRemover
