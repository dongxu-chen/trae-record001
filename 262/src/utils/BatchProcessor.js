class BatchProcessor {
  constructor() {
    this.images = []
    this.currentIndex = 0
    this.operations = []
    this.isProcessing = false
  }

  addImages(files) {
    return new Promise((resolve) => {
      const loadPromises = Array.from(files).map(file => {
        return new Promise((res) => {
          const reader = new FileReader()
          reader.onload = (e) => {
            const img = new Image()
            img.onload = () => {
              res({
                id: generateId(),
                name: file.name,
                file: file,
                image: img,
                dataUrl: e.target.result,
                processed: false,
                operations: []
              })
            }
            img.src = e.target.result
          }
          reader.readAsDataURL(file)
        })
      })

      Promise.all(loadPromises).then(images => {
        this.images.push(...images)
        resolve(this.images)
      })
    })
  }

  removeImage(imageId) {
    this.images = this.images.filter(img => img.id !== imageId)
    if (this.currentIndex >= this.images.length) {
      this.currentIndex = Math.max(0, this.images.length - 1)
    }
  }

  clearAll() {
    this.images = []
    this.currentIndex = 0
    this.operations = []
  }

  getImages() {
    return this.images
  }

  getCurrentImage() {
    return this.images[this.currentIndex]
  }

  setCurrentIndex(index) {
    if (index >= 0 && index < this.images.length) {
      this.currentIndex = index
    }
  }

  addOperation(operation) {
    this.operations.push({
      ...operation,
      timestamp: Date.now()
    })
  }

  setOperations(operations) {
    this.operations = operations
  }

  getOperations() {
    return this.operations
  }

  clearOperations() {
    this.operations = []
  }

  async applyOperationToImage(imageData, operation) {
    return new Promise((resolve) => {
      const canvas = document.createElement('canvas')
      canvas.width = imageData.image.width
      canvas.height = imageData.image.height
      const ctx = canvas.getContext('2d')
      ctx.drawImage(imageData.image, 0, 0)

      switch (operation.type) {
        case 'filter':
          this.applyFilter(ctx, canvas, operation.params)
          break
        case 'rotate':
          this.applyRotation(ctx, canvas, operation.params)
          break
        case 'resize':
          this.applyResize(ctx, canvas, operation.params)
          break
        case 'crop':
          this.applyCrop(ctx, canvas, operation.params)
          break
        default:
          break
      }

      const resultImg = new Image()
      resultImg.onload = () => {
        resolve({
          ...imageData,
          image: resultImg,
          dataUrl: canvas.toDataURL(),
          processed: true
        })
      }
      resultImg.src = canvas.toDataURL()
    })
  }

  applyFilter(ctx, canvas, params) {
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
    const data = imageData.data

    const brightness = (params.brightness || 0) * 255
    const contrastFactor = (1 + (params.contrast || 0)) / (1 - (params.contrast || 0) + 0.001)
    const saturation = 1 + (params.saturation || 0)

    for (let i = 0; i < data.length; i += 4) {
      let r = data[i]
      let g = data[i + 1]
      let b = data[i + 2]

      r = Math.max(0, Math.min(255, r + brightness))
      g = Math.max(0, Math.min(255, g + brightness))
      b = Math.max(0, Math.min(255, b + brightness))

      r = (r - 128) * contrastFactor + 128
      g = (g - 128) * contrastFactor + 128
      b = (b - 128) * contrastFactor + 128

      const gray = 0.299 * r + 0.587 * g + 0.114 * b
      r = gray + (r - gray) * saturation
      g = gray + (g - gray) * saturation
      b = gray + (b - gray) * saturation

      data[i] = Math.max(0, Math.min(255, r))
      data[i + 1] = Math.max(0, Math.min(255, g))
      data[i + 2] = Math.max(0, Math.min(255, b))
    }

    ctx.putImageData(imageData, 0, 0)
  }

  applyRotation(ctx, canvas, params) {
    const angle = params.angle || 0
    if (angle === 0) return

    const radians = (angle * Math.PI) / 180
    const sin = Math.abs(Math.sin(radians))
    const cos = Math.abs(Math.cos(radians))
    
    const newWidth = canvas.width * cos + canvas.height * sin
    const newHeight = canvas.width * sin + canvas.height * cos

    const tempCanvas = document.createElement('canvas')
    tempCanvas.width = newWidth
    tempCanvas.height = newHeight
    const tempCtx = tempCanvas.getContext('2d')

    tempCtx.translate(newWidth / 2, newHeight / 2)
    tempCtx.rotate(radians)
    tempCtx.drawImage(canvas, -canvas.width / 2, -canvas.height / 2)

    canvas.width = newWidth
    canvas.height = newHeight
    ctx.drawImage(tempCanvas, 0, 0)
  }

  applyResize(ctx, canvas, params) {
    const { width, height } = params
    const tempCanvas = document.createElement('canvas')
    tempCanvas.width = width
    tempCanvas.height = height
    const tempCtx = tempCanvas.getContext('2d')
    tempCtx.drawImage(canvas, 0, 0, width, height)

    canvas.width = width
    canvas.height = height
    ctx.drawImage(tempCanvas, 0, 0)
  }

  applyCrop(ctx, canvas, params) {
    const { x, y, width, height } = params
    const tempCanvas = document.createElement('canvas')
    tempCanvas.width = width
    tempCanvas.height = height
    const tempCtx = tempCanvas.getContext('2d')
    tempCtx.drawImage(canvas, x, y, width, height, 0, 0, width, height)

    canvas.width = width
    canvas.height = height
    ctx.drawImage(tempCanvas, 0, 0)
  }

  async processAll(onProgress) {
    if (this.isProcessing) return
    this.isProcessing = true

    const results = []
    for (let i = 0; i < this.images.length; i++) {
      let imageData = this.images[i]
      
      for (const operation of this.operations) {
        imageData = await this.applyOperationToImage(imageData, operation)
      }

      imageData.operations = [...this.operations]
      this.images[i] = imageData
      results.push(imageData)

      if (onProgress) {
        onProgress(i + 1, this.images.length, imageData)
      }
    }

    this.isProcessing = false
    return results
  }

  async exportAll(format = 'png', quality = 0.9) {
    const exportPromises = this.images.map((imageData, index) => {
      return new Promise((resolve) => {
        const canvas = document.createElement('canvas')
        canvas.width = imageData.image.width
        canvas.height = imageData.image.height
        const ctx = canvas.getContext('2d')
        ctx.drawImage(imageData.image, 0, 0)

        let dataUrl
        let filename = imageData.name.replace(/\.[^/.]+$/, '') + '_edited'

        if (format === 'jpeg') {
          dataUrl = canvas.toDataURL('image/jpeg', quality)
          filename += '.jpg'
        } else {
          dataUrl = canvas.toDataURL('image/png')
          filename += '.png'
        }

        resolve({
          name: filename,
          dataUrl: dataUrl,
          index: index
        })
      })
    })

    return Promise.all(exportPromises)
  }

  downloadAll(files) {
    files.forEach((file, index) => {
      setTimeout(() => {
        const link = document.createElement('a')
        link.download = file.name
        link.href = file.dataUrl
        link.click()
      }, index * 200)
    })
  }

  getStats() {
    return {
      total: this.images.length,
      processed: this.images.filter(img => img.processed).length,
      operations: this.operations.length,
      currentIndex: this.currentIndex
    }
  }
}

function generateId() {
  return 'batch_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
}

export const batchProcessor = new BatchProcessor()
export default BatchProcessor
