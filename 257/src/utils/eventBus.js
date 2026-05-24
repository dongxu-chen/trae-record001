class EventBus {
  constructor() {
    this.events = {}
    this.onceEvents = {}
  }

  on(event, callback) {
    if (!this.events[event]) {
      this.events[event] = []
    }
    this.events[event].push(callback)
    return () => this.off(event, callback)
  }

  once(event, callback) {
    const onceCallback = (...args) => {
      callback(...args)
      this.off(event, onceCallback)
    }
    return this.on(event, onceCallback)
  }

  off(event, callback) {
    if (!this.events[event]) return
    this.events[event] = this.events[event].filter(cb => cb !== callback)
    if (this.events[event].length === 0) {
      delete this.events[event]
    }
  }

  emit(event, ...args) {
    if (!this.events[event]) return
    this.events[event].forEach(callback => {
      try {
        callback(...args)
      } catch (error) {
        console.error(`[EventBus] Error in event '${event}':`, error)
      }
    })
  }

  clear(event) {
    if (event) {
      delete this.events[event]
    } else {
      this.events = {}
    }
  }

  hasListeners(event) {
    return !!this.events[event] && this.events[event].length > 0
  }

  getListenerCount(event) {
    return this.events[event] ? this.events[event].length : 0
  }
}

export const eventBus = new EventBus()

export const EVENTS = {
  FILTER_CHANGED: 'filter:changed',
  FILTER_CLEARED: 'filter:cleared',
  DATA_REFRESHED: 'data:refreshed',
  LAYOUT_CHANGED: 'layout:changed',
  COMPONENT_ADDED: 'component:added',
  COMPONENT_REMOVED: 'component:removed',
}

export default eventBus
