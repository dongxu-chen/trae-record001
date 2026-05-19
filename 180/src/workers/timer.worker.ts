let intervalId: number | null = null
let endTime: number | null = null
let duration: number = 0

self.onmessage = (e: MessageEvent) => {
  const { type, payload } = e.data

  switch (type) {
    case 'START':
      if (intervalId) {
        clearInterval(intervalId)
      }
      duration = payload.duration
      endTime = payload.endTime || Date.now() + duration * 1000
      
      const checkTime = () => {
        if (!endTime) return
        
        const now = Date.now()
        const remaining = Math.max(0, Math.floor((endTime - now) / 1000))
        
        self.postMessage({
          type: 'TICK',
          payload: { remaining, endTime }
        })
        
        if (remaining <= 0) {
          if (intervalId) {
            clearInterval(intervalId)
            intervalId = null
          }
          self.postMessage({ type: 'TIME_UP' })
        }
      }
      
      checkTime()
      intervalId = self.setInterval(checkTime, 1000) as unknown as number
      break
      
    case 'STOP':
      if (intervalId) {
        clearInterval(intervalId)
        intervalId = null
      }
      break
      
    case 'RESET':
      if (intervalId) {
        clearInterval(intervalId)
        intervalId = null
      }
      endTime = null
      self.postMessage({ type: 'RESET' })
      break
      
    case 'GET_STATE':
      if (endTime) {
        const now = Date.now()
        const remaining = Math.max(0, Math.floor((endTime - now) / 1000))
        self.postMessage({
          type: 'STATE',
          payload: { remaining, endTime, isRunning: intervalId !== null }
        })
      } else {
        self.postMessage({
          type: 'STATE',
          payload: { remaining: duration, endTime: null, isRunning: false }
        })
      }
      break
  }
}

self.addEventListener('beforeunload', () => {
  if (intervalId) {
    clearInterval(intervalId)
  }
})
