let JSZip = null

export class DownloadService {
  constructor() {
    this.isDownloading = false
    this.progress = 0
    this.downloadQueue = []
  }

  async init() {
    try {
      if (!JSZip) {
        JSZip = (await import('jszip')).default
      }
      console.log('下载管理器初始化完成')
    } catch (e) {
      console.warn('JSZip加载失败，将使用单张下载模式:', e)
    }
  }

  async downloadSingleImage(imageUrl, filename) {
    try {
      const response = await fetch(imageUrl)
      const blob = await response.blob()
      this.saveBlob(blob, filename)
      return true
    } catch (e) {
      console.error('下载图片失败:', e)
      return false
    }
  }

  async downloadBatch(imageUrls, options = {}) {
    if (this.isDownloading) {
      console.warn('已有下载任务进行中')
      return false
    }

    this.isDownloading = true
    this.progress = 0

    const {
      startPage = 1,
      cropImages = false,
      onProgress
    } = options

    try {
      if (JSZip) {
        await this.downloadAsZip(imageUrls, startPage, cropImages, onProgress)
      } else {
        await this.downloadAsIndividual(imageUrls, startPage, onProgress)
      }
      return true
    } catch (e) {
      console.error('批量下载失败:', e)
      return false
    } finally {
      this.isDownloading = false
      this.progress = 100
    }
  }

  async downloadAsZip(imageUrls, startPage, cropImages, onProgress) {
    const zip = new JSZip()
    const folder = zip.folder('comic_pages')
    
    const total = imageUrls.length
    
    for (let i = 0; i < imageUrls.length; i++) {
      const pageNum = startPage + i
      const filename = `page_${String(pageNum).padStart(3, '0')}.png`
      
      try {
        const response = await fetch(imageUrls[i])
        let blob = await response.blob()
        
        if (cropImages) {
          blob = await this.cropImageBlob(blob)
        }
        
        folder.file(filename, blob)
        
        this.progress = ((i + 1) / total) * 90
        if (onProgress) onProgress(this.progress, pageNum, total)
      } catch (e) {
        console.error(`处理第${pageNum}页失败:`, e)
      }
    }

    this.progress = 95
    if (onProgress) onProgress(this.progress, '打包中...', total)

    const zipBlob = await zip.generateAsync({
      type: 'blob',
      compression: 'DEFLATE',
      compressionOptions: { level: 6 }
    })

    this.progress = 100
    if (onProgress) onProgress(this.progress, '完成', total)

    this.saveBlob(zipBlob, `comic_${Date.now()}.zip`)
  }

  async downloadAsIndividual(imageUrls, startPage, onProgress) {
    const total = imageUrls.length
    
    for (let i = 0; i < imageUrls.length; i++) {
      const pageNum = startPage + i
      const filename = `page_${String(pageNum).padStart(3, '0')}.png`
      
      try {
        await this.downloadSingleImage(imageUrls[i], filename)
        this.progress = ((i + 1) / total) * 100
        if (onProgress) onProgress(this.progress, pageNum, total)
        
        await this.delay(200)
      } catch (e) {
        console.error(`下载第${pageNum}页失败:`, e)
      }
    }
  }

  async cropImageBlob(blob) {
    return new Promise((resolve) => {
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        const ctx = canvas.getContext('2d')
        canvas.width = img.width
        canvas.height = img.height
        ctx.drawImage(img, 0, 0)
        
        canvas.toBlob((croppedBlob) => {
          resolve(croppedBlob || blob)
        }, 'image/png')
      }
      img.onerror = () => resolve(blob)
      img.src = URL.createObjectURL(blob)
    })
  }

  saveBlob(blob, filename) {
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  getProgress() {
    return this.progress
  }

  isBusy() {
    return this.isDownloading
  }
}

export const downloadService = new DownloadService()
export default downloadService
