import { clipboard, NativeImage } from 'electron'
import * as os from 'os'
import type { Clipboard } from 'electron'
import type { ClipboardContent, ClipboardDataType, FileData } from '@shared/types'
import { ClipboardDataType as DataType } from '@shared/types'
import { generateId, hashData } from '@shared/utils'

interface ClipboardMonitorOptions {
  onClipboardChange: (content: ClipboardContent) => void
  checkInterval?: number
}

export class ClipboardMonitor {
  private clipboard: Clipboard
  private options: ClipboardMonitorOptions
  private timer: NodeJS.Timeout | null = null
  private lastHash: string = ''
  private lastContent: ClipboardContent | null = null
  private deviceName: string
  private deviceId: string

  constructor(clipboard: Clipboard, options: ClipboardMonitorOptions) {
    this.clipboard = clipboard
    this.options = {
      checkInterval: 500,
      ...options
    }
    this.deviceName = os.hostname()
    this.deviceId = this.generateDeviceId()
  }

  private generateDeviceId(): string {
    const ifaces = os.networkInterfaces()
    let mac = ''
    for (const name of Object.keys(ifaces)) {
      for (const iface of ifaces[name]!) {
        if (iface.family === 'IPv4' && !iface.internal) {
          mac = iface.mac
          break
        }
      }
      if (mac) break
    }
    return mac || os.hostname()
  }

  start(): void {
    if (this.timer) return
    this.lastHash = this.calculateCurrentHash()
    this.timer = setInterval(() => this.checkClipboard(), this.options.checkInterval)
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
  }

  private checkClipboard(): void {
    const currentHash = this.calculateCurrentHash()
    if (currentHash !== this.lastHash && currentHash !== '') {
      this.lastHash = currentHash
      const content = this.getCurrentContent()
      if (content) {
        this.lastContent = content
        this.options.onClipboardChange(content)
      }
    }
  }

  private calculateCurrentHash(): string {
    try {
      let data = ''
      
      const text = this.clipboard.readText()
      if (text) {
        data = `text:${text}`
      }
      
      const image = this.clipboard.readImage()
      if (!image.isEmpty()) {
        const pngData = image.toPNG()
        data = `image:${hashData(pngData.toString('base64'))}`
      }
      
      const files = this.clipboard.read('file')
      if (files && files.length > 0) {
        data = `files:${files.join('|')}`
      }
      
      return data ? hashData(data) : ''
    } catch (e) {
      console.error('计算剪贴板哈希失败:', e)
      return ''
    }
  }

  getCurrentHash(): string {
    return this.lastHash
  }

  getCurrentContent(): ClipboardContent | null {
    try {
      const text = this.clipboard.readText()
      const image = this.clipboard.readImage()
      const files = this.clipboard.read('file')

      let type: ClipboardDataType | null = null
      let data: string | FileData | FileData[] | null = null

      if (files && files.length > 0) {
        type = files.length === 1 ? DataType.FILE : DataType.FILES
        data = files.map(filePath => this.readFileData(filePath))
        if (files.length === 1) {
          data = data[0]
        }
      } else if (!image.isEmpty()) {
        type = DataType.IMAGE
        data = {
          name: 'clipboard-image.png',
          size: image.getSize().width * image.getSize().height * 4,
          type: 'image/png',
          data: image.toPNG().toString('base64')
        }
      } else if (text) {
        type = DataType.TEXT
        data = text
      }

      if (!type || !data) return null

      const content: ClipboardContent = {
        id: generateId(),
        type,
        data,
        timestamp: Date.now(),
        deviceId: this.deviceId,
        deviceName: this.deviceName,
        hash: this.lastHash || this.calculateCurrentHash()
      }

      return content
    } catch (e) {
      console.error('读取剪贴板内容失败:', e)
      return null
    }
  }

  private readFileData(filePath: string): FileData {
    const fs = require('fs')
    const path = require('path')
    const stats = fs.statSync(filePath)
    const buffer = fs.readFileSync(filePath)
    
    return {
      name: path.basename(filePath),
      size: stats.size,
      type: this.getMimeType(filePath),
      data: buffer.toString('base64')
    }
  }

  private getMimeType(filePath: string): string {
    const ext = require('path').extname(filePath).toLowerCase()
    const mimeTypes: Record<string, string> = {
      '.txt': 'text/plain',
      '.json': 'application/json',
      '.html': 'text/html',
      '.css': 'text/css',
      '.js': 'application/javascript',
      '.png': 'image/png',
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.gif': 'image/gif',
      '.pdf': 'application/pdf',
      '.doc': 'application/msword',
      '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      '.xls': 'application/vnd.ms-excel',
      '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      '.zip': 'application/zip',
      '.rar': 'application/x-rar-compressed'
    }
    return mimeTypes[ext] || 'application/octet-stream'
  }

  writeToClipboard(content: ClipboardContent): void {
    try {
      switch (content.type) {
        case DataType.TEXT:
          this.clipboard.writeText(content.data as string)
          break
          
        case DataType.IMAGE: {
          const imageData = content.data as FileData
          const image = NativeImage.createFromBuffer(Buffer.from(imageData.data, 'base64'))
          this.clipboard.writeImage(image)
          break
        }
          
        case DataType.FILE:
        case DataType.FILES: {
          const files = Array.isArray(content.data) ? content.data as FileData[] : [content.data as FileData]
          const fs = require('fs')
          const path = require('path')
          const tmpDir = path.join(require('os').tmpdir(), 'clipboard-sync')
          
          if (!fs.existsSync(tmpDir)) {
            fs.mkdirSync(tmpDir, { recursive: true })
          }
          
          const filePaths: string[] = []
          for (const file of files) {
            const filePath = path.join(tmpDir, file.name)
            fs.writeFileSync(filePath, Buffer.from(file.data, 'base64'))
            filePaths.push(filePath)
          }
          
          this.clipboard.write('file', filePaths)
          break
        }
      }
      
      this.lastHash = content.hash
      this.lastContent = content
    } catch (e) {
      console.error('写入剪贴板失败:', e)
      throw e
    }
  }

  setDeviceInfo(name: string, id: string): void {
    this.deviceName = name
    this.deviceId = id
  }
}
