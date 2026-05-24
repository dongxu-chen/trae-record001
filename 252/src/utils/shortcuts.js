export function createShortcutManager() {
  const shortcuts = new Map()
  let isEnabled = true

  function normalizeKey(key) {
    return key.toLowerCase().trim()
  }

  function parseShortcut(shortcut) {
    const parts = shortcut.toLowerCase().split('+').map(s => s.trim())
    const modifiers = {
      ctrl: false,
      shift: false,
      alt: false,
      meta: false
    }
    let key = ''

    parts.forEach(part => {
      switch (part) {
        case 'ctrl':
        case 'control':
          modifiers.ctrl = true
          break
        case 'shift':
          modifiers.shift = true
          break
        case 'alt':
        case 'option':
          modifiers.alt = true
          break
        case 'meta':
        case 'cmd':
        case 'command':
          modifiers.meta = true
          break
        default:
          key = part
      }
    })

    return { modifiers, key }
  }

  function matchEvent(event, parsed) {
    const { modifiers, key } = parsed
    
    if (modifiers.ctrl !== event.ctrlKey) return false
    if (modifiers.shift !== event.shiftKey) return false
    if (modifiers.alt !== event.altKey) return false
    if (modifiers.meta !== event.metaKey) return false
    
    const eventKey = event.key.toLowerCase()
    if (key === 'delete') {
      return eventKey === 'delete' || eventKey === 'backspace'
    }
    if (key === 'enter') {
      return eventKey === 'enter' || eventKey === 'return'
    }
    return eventKey === key
  }

  function register(shortcut, handler, options = {}) {
    const normalizedShortcut = normalizeKey(shortcut)
    const parsed = parseShortcut(normalizedShortcut)
    shortcuts.set(normalizedShortcut, {
      handler,
      parsed,
      preventDefault: options.preventDefault !== false,
      stopPropagation: options.stopPropagation !== false
    })
  }

  function unregister(shortcut) {
    const normalizedShortcut = normalizeKey(shortcut)
    shortcuts.delete(normalizedShortcut)
  }

  function handleKeyDown(event) {
    if (!isEnabled) return
    
    const target = event.target
    if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
      return
    }

    for (const [, { handler, parsed, preventDefault, stopPropagation }] of shortcuts) {
      if (matchEvent(event, parsed)) {
        if (preventDefault) event.preventDefault()
        if (stopPropagation) event.stopPropagation()
        handler(event)
        return true
      }
    }
    return false
  }

  function enable() {
    isEnabled = true
  }

  function disable() {
    isEnabled = false
  }

  function clear() {
    shortcuts.clear()
  }

  return {
    register,
    unregister,
    handleKeyDown,
    enable,
    disable,
    clear
  }
}
