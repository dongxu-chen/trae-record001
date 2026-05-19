const app = getApp()
const BASE_URL = 'http://localhost:5000'

Page({
  data: {},
  
  onLoad() {},
  
  goToCounselors() {
    wx.navigateTo({
      url: '/pages/counselors/counselors'
    })
  },
  
  goToScl90() {
    wx.navigateTo({
      url: '/pages/scl90/scl90'
    })
  },
  
  goToConfessions() {
    wx.navigateTo({
      url: '/pages/confessions/confessions'
    })
  },
  
  goToAppointments() {
    wx.switchTab({
      url: '/pages/appointments/appointments'
    })
  }
})
