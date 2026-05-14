export const notify = (title, options = {}) => {
  if (!('Notification' in window)) {
    console.log('浏览器不支持通知')
    return Promise.resolve(false)
  }

  if (Notification.permission === 'granted') {
    try {
      new Notification(title, {
        icon: '🍅',
        renotify: false,
        ...options
      })
      return Promise.resolve(true)
    } catch (error) {
      console.error('通知发送失败:', error)
      return Promise.resolve(false)
    }
  }

  if (Notification.permission === 'denied') {
    console.log('通知权限已被拒绝')
    return Promise.resolve(false)
  }

  return Promise.resolve(false)
}

export const requestNotificationPermission = async () => {
  if (!('Notification' in window)) {
    return 'unsupported'
  }
  if (Notification.permission === 'granted') {
    return 'granted'
  }
  if (Notification.permission === 'denied') {
    return 'denied'
  }
  try {
    const permission = await Notification.requestPermission()
    return permission
  } catch (error) {
    console.error('请求通知权限失败:', error)
    return 'error'
  }
}

export const getNotificationPermission = () => {
  if (!('Notification' in window)) {
    return 'unsupported'
  }
  return Notification.permission
}

export const canSendNotification = () => {
  if (!('Notification' in window)) {
    return false
  }
  return Notification.permission === 'granted'
}
