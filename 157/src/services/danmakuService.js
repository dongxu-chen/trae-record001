class DanmakuService {
  constructor() {
    this.danmakuList = []
    this.activeDanmaku = []
    this.pageDanmakuMap = new Map()
    this.isConnected = false
    this.ws = null
    this.messageId = 0
    this.colorPresets = [
      '#ffffff', '#ff6b6b', '#4ecdc4', '#ffe66d', 
      '#95e1d3', '#f38181', '#aa96da', '#fcbad3'
    ]
  }

  init() {
    this.loadLocalDanmaku()
    this.connectMockWebSocket()
    console.log('弹幕系统初始化完成')
  }

  loadLocalDanmaku() {
    try {
      const data = localStorage.getItem('comic_danmaku')
      if (data) {
        const saved = JSON.parse(data)
        saved.forEach(d => {
          if (!this.pageDanmakuMap.has(d.page)) {
            this.pageDanmakuMap.set(d.page, [])
          }
          this.pageDanmakuMap.get(d.page).push(d)
        })
      }
    } catch (e) {
      console.error('加载本地弹幕失败:', e)
    }
  }

  saveLocalDanmaku(danmaku) {
    try {
      const data = localStorage.getItem('comic_danmaku')
      const list = data ? JSON.parse(data) : []
      list.push(danmaku)
      localStorage.setItem('comic_danmaku', JSON.stringify(list.slice(-500)))
    } catch (e) {
      console.error('保存本地弹幕失败:', e)
    }
  }

  connectMockWebSocket() {
    setTimeout(() => {
      this.isConnected = true
      console.log('弹幕WebSocket已连接（模拟）')
      
      this.simulateIncomingDanmaku()
    }, 500)
  }

  simulateIncomingDanmaku() {
    setInterval(() => {
      const texts = [
        '哈哈哈哈太好笑了',
        '这个画面太美了',
        '作者太强了！',
        '前排围观',
        '打卡打卡',
        '这里泪目了',
        '高能预警！',
        '这波操作666'
      ]
      const randomText = texts[Math.floor(Math.random() * texts.length)]
      const randomPage = Math.floor(Math.random() * 12) + 1
      const randomColor = this.colorPresets[Math.floor(Math.random() * this.colorPresets.length)]
      
      const mockDanmaku = {
        id: `sys_${Date.now()}`,
        text: randomText,
        page: randomPage,
        color: randomColor,
        fontSize: 24,
        isSystem: true,
        timestamp: Date.now()
      }
      
      if (!this.pageDanmakuMap.has(randomPage)) {
        this.pageDanmakuMap.set(randomPage, [])
      }
      this.pageDanmakuMap.get(randomPage).push(mockDanmaku)
    }, 8000)
  }

  sendDanmaku(text, page, options = {}) {
    const danmaku = {
      id: `user_${Date.now()}_${this.messageId++}`,
      text,
      page,
      color: options.color || '#ffffff',
      fontSize: options.fontSize || 24,
      isSystem: false,
      timestamp: Date.now()
    }

    if (!this.pageDanmakuMap.has(page)) {
      this.pageDanmakuMap.set(page, [])
    }
    this.pageDanmakuMap.get(page).push(danmaku)
    this.saveLocalDanmaku(danmaku)

    console.log('发送弹幕:', danmaku)
    return danmaku
  }

  getDanmakuForPage(page) {
    return this.pageDanmakuMap.get(page) || []
  }

  getAllDanmaku() {
    const all = []
    this.pageDanmakuMap.forEach(list => {
      all.push(...list)
    })
    return all
  }

  clearPageDanmaku(page) {
    this.pageDanmakuMap.delete(page)
  }

  clearAllDanmaku() {
    this.pageDanmakuMap.clear()
    localStorage.removeItem('comic_danmaku')
  }
}

export const danmakuService = new DanmakuService()
export default danmakuService
