const BASE_URL = 'http://localhost:5000'

Page({
  data: {
    content: '',
    list: [],
    loading: false
  },
  
  onLoad() {
    this.loadList()
  },
  
  onShow() {
    this.loadList()
  },
  
  onInput(e) {
    this.setData({
      content: e.detail.value
    })
  },
  
  publish() {
    if (!this.data.content.trim()) return
    
    wx.showLoading({ title: '发布中...' })
    
    wx.request({
      url: `${BASE_URL}/api/confessions`,
      method: 'POST',
      data: { content: this.data.content },
      header: { 'content-type': 'application/json' },
      success: (res) => {
        if (res.data.success) {
          if (res.data.crisis_level && res.data.crisis_level !== '正常') {
            wx.showModal({
              title: '⚠️ 温馨提示',
              content: `检测到内容可能存在${res.data.crisis_level}风险，建议及时寻求专业帮助。如遇紧急情况请拨打心理援助热线：400-161-9995`,
              showCancel: false
            })
          } else {
            wx.showToast({ title: '发布成功', icon: 'success' })
          }
          this.setData({ content: '' })
          this.loadList()
        } else {
          wx.showToast({ title: '发布失败', icon: 'error' })
        }
      },
      fail: () => {
        wx.showToast({ title: '网络错误', icon: 'error' })
      },
      complete: () => {
        wx.hideLoading()
      }
    })
  },
  
  loadList() {
    this.setData({ loading: true })
    
    wx.request({
      url: `${BASE_URL}/api/confessions`,
      method: 'GET',
      success: (res) => {
        if (Array.isArray(res.data)) {
          this.setData({ list: res.data })
        }
      },
      fail: () => {
        wx.showToast({ title: '加载失败', icon: 'none' })
      },
      complete: () => {
        this.setData({ loading: false })
      }
    })
  },
  
  showReply(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '回复功能',
      content: '回复功能开发中，敬请期待',
      showCancel: false
    })
  },
  
  onPullDownRefresh() {
    this.loadList()
    wx.stopPullDownRefresh()
  }
})
