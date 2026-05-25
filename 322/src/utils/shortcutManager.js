import { ref, reactive } from 'vue'
import { DEFAULT_SHORTCUTS, TOOL_MODES } from '../constants'

class ShortcutManager {
  constructor() {
    this.shortcuts = reactive({ ...DEFAULT_SHORTCUTS })
    this.enabled = ref(true)
    this.listeners = new Map()
    this.isRecording = ref(false)
    this.recordedKey = ref(null)
    this.conflicts = ref([])
    
    this._handleKeyDown = this._handleKeyDown.bind(this)
  }

  init() {
    window.addEventListener('keydown', this._handleKeyDown)
    this.loadFromStorage()
  }

  destroy() {
    window.removeEventListener('keydown', this._handleKeyDown)
  }

  _handleKeyDown(e) {
    if (!this.enabled.value) return
    if (this.isRecording.value) return
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
      return
    }

    const key = this._normalizeKey(e.key)
    const shortcut = this._findMatchingShortcut(key, e.ctrlKey, e.altKey, e.shiftKey)
    
    if (shortcut) {
      e.preventDefault()
      this._executeAction(shortcut.action, e)
      this.emit('shortcut:triggered', { action: shortcut.action, shortcut: shortcut })
    }
  }

  _normalizeKey(key) {
    if (!key) return ''
    return key.toLowerCase()
  }

  _findMatchingShortcut(key, ctrl, alt, shift) {
    for (const [action, config] of Object.entries(this.shortcuts)) {
      if (this._matchShortcut(config, key, ctrl, alt, shift)) {
        return { action, ...config }
      }
    }
    return null
  }

  _matchShortcut(config, key, ctrl, alt, shift) {
    return config.key === key &&
           config.ctrl === ctrl &&
           config.alt === alt &&
           config.shift === shift
  }

  _executeAction(action, e) {
    switch (action) {
      case 'SELECT':
        this.emit('action:tool', TOOL_MODES.SELECT)
        break
      case 'RECTANGLE':
        this.emit('action:tool', TOOL_MODES.RECTANGLE)
        break
      case 'ARROW':
        this.emit('action:tool', TOOL_MODES.ARROW)
        break
      case 'TEXT':
        this.emit('action:tool', TOOL_MODES.TEXT)
        break
      case 'PAN':
        this.emit('action:tool', TOOL_MODES.PAN)
        break
      case 'UNDO':
        if (!e.shiftKey) {
          this.emit('action:undo')
        }
        break
      case 'REDO':
          this.emit('action:redo')
          break
      case 'DELETE':
      case 'BACKSPACE':
        this.emit('action:delete')
        break
      case 'SELECT_ALL':
        this.emit('action:select_all')
        break
      case 'ESCAPE':
        this.emit('action:escape')
        break
      case 'ZOOM_IN':
        this.emit('action:zoom_in')
        break
      case 'ZOOM_OUT':
        this.emit('action:zoom_out')
        break
      case 'TOGGLE_SNAP':
        this.emit('action:toggle_snap')
        break
    }
  }

  setShortcut(action, config) {
    const conflict = this._checkConflict(action, config)
    if (conflict) {
      this.conflicts.value.push({
        action,
        conflictingAction: conflict,
        config
      })
      return { success: false, conflict }
    }

    this.shortcuts[action] = {
      ...this.shortcuts[action],
      ...config
    }
    
    this._saveToStorage()
    this.emit('shortcut:changed', { action, config: this.shortcuts[action] })
    
    return { success: true }
  }

  _checkConflict(action, config) {
    for (const [existingAction, existingConfig] of Object.entries(this.shortcuts)) {
      if (existingAction === action) continue
      
      if (existingConfig.key === config.key &&
          existingConfig.ctrl === config.ctrl &&
          existingConfig.alt === config.alt &&
          existingConfig.shift === config.shift) {
        return existingAction
      }
    }
    return null
  }

  resetShortcut(action) {
    if (DEFAULT_SHORTCUTS[action]) {
      this.shortcuts[action] = { ...DEFAULT_SHORTCUTS[action] }
      this._saveToStorage()
      this.emit('shortcut:reset', { action, config: this.shortcuts[action] })
    }
  }

  resetAll() {
    Object.keys(this.shortcuts).forEach(action => {
      if (DEFAULT_SHORTCUTS[action]) {
        this.shortcuts[action] = { ...DEFAULT_SHORTCUTS[action] }
      }
    })
    this._saveToStorage()
    this.emit('shortcuts:reset_all')
  }

  startRecording(action) {
    this.isRecording.value = true
    this.recordedKey.value = null
    this.recordingAction = action
    
    return new Promise((resolve) => {
      this._recordResolve = resolve
      
      const handler = (e) => {
        e.preventDefault()
        e.stopPropagation()
        
        const key = this._normalizeKey(e.key)
        
        if (key === 'escape') {
          this.stopRecording()
          window.removeEventListener('keydown', handler)
          resolve({ success: false, canceled: true })
          return
        }
        
        if (key && key.length === 1 || ['delete', 'backspace', 'escape', 'enter', 'tab', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright', '+', '-'].includes(key)) {
          const config = {
            key,
            ctrl: e.ctrlKey,
            alt: e.altKey,
            shift: e.shiftKey,
            description: this.shortcuts[action]?.description || ''
          }
          
          this.recordedKey.value = this.formatShortcut(config)
          
          setTimeout(() => {
            const result = this.setShortcut(action, config)
            this.stopRecording()
            window.removeEventListener('keydown', handler)
            resolve({ success: result.success, conflict: result.conflict, config })
          }, 100)
        }
      }
      
      window.addEventListener('keydown', handler, { once: false, capture: true })
    })
  }

  stopRecording() {
    this.isRecording.value = false
    this.recordedKey.value = null
    this.recordingAction = null
  }

  formatShortcut(config) {
    const parts = []
    if (config.ctrl) parts.push('Ctrl')
    if (config.alt) parts.push('Alt')
    if (config.shift) parts.push('Shift')
    
    let key = config.key
    if (key === 'delete') key = 'Delete'
    else if (key === 'backspace') key = 'Backspace'
    else if (key === 'escape') key = 'Esc'
    else if (key === 'arrowup') key = '↑'
    else if (key === 'arrowdown') key = '↓'
    else if (key === 'arrowleft') key = '←'
    else if (key === 'arrowright') key = '→'
    else if (key === '+') key = '+'
    else if (key === '-') key = '-'
    else key = key.toUpperCase()
    
    parts.push(key)
    
    return parts.join(' + ')
  }

  getShortcutDisplay(action) {
    const config = this.shortcuts[action]
    if (!config) return ''
    return this.formatShortcut(config)
  }

  setEnabled(value) {
    this.enabled.value = value
  }

  clearConflicts() {
    this.conflicts.value = []
  }

  _saveToStorage() {
    try {
      const custom = {}
      Object.entries(this.shortcuts).forEach(([action, config]) => {
        const defaultConfig = DEFAULT_SHORTCUTS[action]
        if (defaultConfig && 
            (config.key !== defaultConfig.key ||
             config.ctrl !== defaultConfig.ctrl ||
             config.alt !== defaultConfig.alt ||
             config.shift !== defaultConfig.shift)) {
          custom[action] = config
        }
      })
      localStorage.setItem('annotation_shortcuts', JSON.stringify(custom))
    } catch (e) {
      console.warn('Failed to save shortcuts:', e)
    }
  }

  loadFromStorage() {
    try {
      const saved = localStorage.getItem('annotation_shortcuts')
      if (saved) {
        const custom = JSON.parse(saved)
        Object.entries(custom).forEach(([action, config]) => {
          if (this.shortcuts[action]) {
            this.shortcuts[action] = {
            ...this.shortcuts[action],
            ...config
          }
          }
        })
      }
    } catch (e) {
      console.warn('Failed to load shortcuts:', e)
    }
  }

  exportShortcuts() {
    return JSON.stringify(this.shortcuts, null, 2)
  }

  importShortcuts(jsonString) {
    try {
      const imported = JSON.parse(jsonString)
      Object.entries(imported).forEach(([action, config]) => {
        if (this.shortcuts[action]) {
          this.shortcuts[action] = config
        }
      })
      this._saveToStorage()
      return true
    } catch (e) {
      console.error('Failed to import shortcuts:', e)
      return false
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event).add(callback)
    return () => this.off(event, callback)
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(callback)
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data)
        } catch (e) {
          console.error(`Shortcut listener error [${event}]:`, e)
        }
      })
    }
  }

  getShortcutList() {
    return Object.entries(this.shortcuts).map(([action, config]) => ({
      action,
      ...config,
      display: this.formatShortcut(config),
      isDefault: this._isDefault(action)
    }))
  }

  _isDefault(action) {
    const config = this.shortcuts[action]
    const defaultConfig = DEFAULT_SHORTCUTS[action]
    if (!defaultConfig) return true
    return config.key === defaultConfig.key &&
           config.ctrl === defaultConfig.ctrl &&
           config.alt === defaultConfig.alt &&
           config.shift === defaultConfig.shift
  }

  getShortcutsByCategory() {
    const categories = {
      '工具切换': ['SELECT', 'RECTANGLE', 'ARROW', 'TEXT', 'PAN'],
      '编辑操作': ['UNDO', 'REDO', 'DELETE', 'BACKSPACE', 'SELECT_ALL', 'ESCAPE'],
      '视图控制': ['ZOOM_IN', 'ZOOM_OUT', 'TOGGLE_SNAP']
    }

    return Object.entries(categories).map(([category, actions]) => ({
      category,
      shortcuts: actions.map(action => ({
        action,
        ...this.shortcuts[action],
        display: this.formatShortcut(this.shortcuts[action])
      }))
    }))
  }
}

const shortcutManager = new ShortcutManager()
export default shortcutManager
