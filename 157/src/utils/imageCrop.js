export class ImageCropper {
  constructor() {
    this.canvas = document.createElement('canvas')
    this.ctx = this.canvas.getContext('2d')
    this.threshold = 240
    this.margin = 10
  }

  async cropImage(imageSource, autoCrop = true) {
    const img = await this.loadImage(imageSource)
    
    if (!autoCrop) {
      return img
    }

    const bounds = this.findContentBounds(img)
    return this.cropToBounds(img, bounds)
  }

  loadImage(source) {
    return new Promise((resolve, reject) => {
      if (source instanceof HTMLImageElement) {
        resolve(source)
      } else if (typeof source === 'string') {
        const img = new Image()
        img.crossOrigin = 'anonymous'
        img.onload = () => resolve(img)
        img.onerror = reject
        img.src = source
      } else {
        reject(new Error('不支持的图片源类型'))
      }
    })
  }

  findContentBounds(img) {
    this.canvas.width = img.width
    this.canvas.height = img.height
    this.ctx.drawImage(img, 0, 0)

    const imageData = this.ctx.getImageData(0, 0, img.width, img.height)
    const data = imageData.data

    let minX = img.width
    let maxX = 0
    let minY = img.height
    let maxY = 0

    const step = 4

    for (let y = 0; y < img.height; y += step) {
      for (let x = 0; x < img.width; x += step) {
        const i = (y * img.width + x) * 4
        const r = data[i]
        const g = data[i + 1]
        const b = data[i + 2]
        
        const brightness = (r + g + b) / 3
        
        if (brightness < this.threshold) {
          if (x < minX) minX = x
          if (x > maxX) maxX = x
          if (y < minY) minY = y
          if (y > maxY) maxY = y
        }
      }
    }

    if (minX > maxX || minY > maxY) {
      return { x: 0, y: 0, width: img.width, height: img.height }
    }

    minX = Math.max(0, minX - this.margin)
    minY = Math.max(0, minY - this.margin)
    maxX = Math.min(img.width, maxX + this.margin)
    maxY = Math.min(img.height, maxY + this.margin)

    return {
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY
    }
  }

  cropToBounds(img, bounds) {
    const croppedCanvas = document.createElement('canvas')
    const croppedCtx = croppedCanvas.getContext('2d')

    croppedCanvas.width = bounds.width
    croppedCanvas.height = bounds.height

    croppedCtx.drawImage(
      img,
      bounds.x, bounds.y, bounds.width, bounds.height,
      0, 0, bounds.width, bounds.height
    )

    return croppedCanvas.toDataURL('image/png')
  }

  setThreshold(value) {
    this.threshold = value
  }

  setMargin(value) {
    this.margin = value
  }

  async getImageFromTexture(texture) {
    if (texture.baseTexture && texture.baseTexture.resource) {
      return texture.baseTexture.resource.source
    }
    return null
  }
}

export const imageCropper = new ImageCropper()
export default imageCropper
