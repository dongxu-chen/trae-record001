class BaseCommand {
  constructor(type, targetId = null) {
    this.type = type
    this.targetId = targetId
    this.timestamp = Date.now()
  }

  execute() {
    throw new Error('execute() must be implemented')
  }

  undo() {
    throw new Error('undo() must be implemented')
  }

  getSize() {
    return JSON.stringify(this).length
  }
}

class AddObjectCommand extends BaseCommand {
  constructor(fabricCanvas, fabricObject) {
    super('add', fabricObject.id || generateId())
    this.canvas = fabricCanvas
    this.objectData = null
    this.object = fabricObject
  }

  execute() {
    if (this.objectData) {
      return new Promise((resolve) => {
        fabric.util.enlivenObjects([this.objectData], (objects) => {
          if (objects.length > 0) {
            this.canvas.add(objects[0])
            this.canvas.renderAll()
            resolve(objects[0])
          }
        })
      })
    }
    this.objectData = this.object.toObject()
    return Promise.resolve(this.object)
  }

  undo() {
    const obj = this.canvas.getObjects().find(o => o.id === this.targetId)
    if (obj) {
      this.canvas.remove(obj)
      this.canvas.renderAll()
    }
  }
}

class RemoveObjectCommand extends BaseCommand {
  constructor(fabricCanvas, fabricObject) {
    super('remove', fabricObject.id || generateId())
    this.canvas = fabricCanvas
    this.objectData = fabricObject.toObject()
  }

  execute() {
    const obj = this.canvas.getObjects().find(o => o.id === this.targetId)
    if (obj) {
      this.canvas.remove(obj)
      this.canvas.renderAll()
    }
  }

  undo() {
    return new Promise((resolve) => {
      fabric.util.enlivenObjects([this.objectData], (objects) => {
        if (objects.length > 0) {
          this.canvas.add(objects[0])
          this.canvas.renderAll()
          resolve(objects[0])
        }
      })
    })
  }
}

class ModifyObjectCommand extends BaseCommand {
  constructor(fabricCanvas, fabricObject, oldProps, newProps) {
    super('modify', fabricObject.id || generateId())
    this.canvas = fabricCanvas
    this.oldProps = { ...oldProps }
    this.newProps = { ...newProps }
  }

  execute() {
    const obj = this.canvas.getObjects().find(o => o.id === this.targetId)
    if (obj) {
      obj.set(this.newProps)
      obj.setCoords()
      this.canvas.renderAll()
    }
  }

  undo() {
    const obj = this.canvas.getObjects().find(o => o.id === this.targetId)
    if (obj) {
      obj.set(this.oldProps)
      obj.setCoords()
      this.canvas.renderAll()
    }
  }

  getSize() {
    return Object.keys(this.oldProps).length * 20 + Object.keys(this.newProps).length * 20
  }
}

class MoveLayerCommand extends BaseCommand {
  constructor(fabricCanvas, fabricObject, oldIndex, newIndex) {
    super('moveLayer', fabricObject.id || generateId())
    this.canvas = fabricCanvas
    this.oldIndex = oldIndex
    this.newIndex = newIndex
  }

  execute() {
    const obj = this.canvas.getObjects().find(o => o.id === this.targetId)
    if (obj) {
      const objects = this.canvas.getObjects()
      this.canvas.moveObjectTo(obj, this.newIndex)
      this.canvas.renderAll()
    }
  }

  undo() {
    const obj = this.canvas.getObjects().find(o => o.id === this.targetId)
    if (obj) {
      this.canvas.moveObjectTo(obj, this.oldIndex)
      this.canvas.renderAll()
    }
  }

  getSize() {
    return 32
  }
}

class FilterCommand extends BaseCommand {
  constructor(fabricCanvas, fabricObject, oldFilters, newFilters) {
    super('filter', fabricObject.id || generateId())
    this.canvas = fabricCanvas
    this.oldFilters = oldFilters ? oldFilters.map(f => f.toObject()) : []
    this.newFilters = newFilters ? newFilters.map(f => f.toObject()) : []
  }

  execute() {
    const obj = this.canvas.getObjects().find(o => o.id === this.targetId)
    if (obj && obj.type === 'image') {
      applyFiltersToObject(obj, this.newFilters)
      this.canvas.renderAll()
    }
  }

  undo() {
    const obj = this.canvas.getObjects().find(o => o.id === this.targetId)
    if (obj && obj.type === 'image') {
      applyFiltersToObject(obj, this.oldFilters)
      this.canvas.renderAll()
    }
  }

  getSize() {
    return (this.oldFilters.length + this.newFilters.length) * 50
  }
}

class CropCommand extends BaseCommand {
  constructor(fabricCanvas, oldState, newState) {
    super('crop', null)
    this.canvas = fabricCanvas
    this.oldState = oldState
    this.newState = newState
  }

  execute() {
    this.canvas.loadFromJSON(this.newState, () => {
      this.canvas.renderAll()
    })
  }

  undo() {
    this.canvas.loadFromJSON(this.oldState, () => {
      this.canvas.renderAll()
    })
  }

  getSize() {
    return 200
  }
}

class CompoundCommand extends BaseCommand {
  constructor(commands = []) {
    super('compound', null)
    this.commands = commands
  }

  addCommand(command) {
    this.commands.push(command)
  }

  execute() {
    this.commands.forEach(cmd => cmd.execute())
  }

  undo() {
    for (let i = this.commands.length - 1; i >= 0; i--) {
      this.commands[i].undo()
    }
  }

  getSize() {
    return this.commands.reduce((sum, cmd) => sum + cmd.getSize(), 0)
  }
}

function generateId() {
  return 'obj_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
}

function applyFiltersToObject(obj, filterData) {
  if (!obj.filters) obj.filters = []
  obj.filters = []

  filterData.forEach((fData) => {
    const filterClass = fabric.Image.filters[fData.type]
    if (filterClass) {
      const filter = new filterClass(fData)
      obj.filters.push(filter)
    }
  })

  obj.applyFilters()
}

class CommandHistory {
  constructor(options = {}) {
    this.undoStack = []
    this.redoStack = []
    this.maxHistorySize = options.maxHistorySize || 100
    this.maxMemoryBytes = options.maxMemoryBytes || 10 * 1024 * 1024
    this.currentMemoryUsage = 0
    this.canvas = null
    this.activeCommand = null
    this.batchMode = false
    this.batchCommands = []
  }

  setCanvas(canvas) {
    this.canvas = canvas
  }

  startBatch() {
    this.batchMode = true
    this.batchCommands = []
  }

  endBatch() {
    this.batchMode = false
    if (this.batchCommands.length > 0) {
      const compound = new CompoundCommand(this.batchCommands)
      this.executeCommand(compound)
    }
    this.batchCommands = []
  }

  executeCommand(command) {
    if (this.batchMode) {
      this.batchCommands.push(command)
      return
    }

    command.execute()

    this.undoStack.push(command)
    this.currentMemoryUsage += command.getSize()

    this.redoStack = []
    this.trimHistory()
  }

  addObject(object) {
    const cmd = new AddObjectCommand(this.canvas, object)
    this.executeCommand(cmd)
    return cmd
  }

  removeObject(object) {
    const cmd = new RemoveObjectCommand(this.canvas, object)
    this.executeCommand(cmd)
    return cmd
  }

  modifyObject(object, oldProps, newProps) {
    const significantChanges = Object.keys(newProps).filter(
      key => JSON.stringify(oldProps[key]) !== JSON.stringify(newProps[key])
    )

    if (significantChanges.length === 0) return null

    const oldDiff = {}
    const newDiff = {}
    significantChanges.forEach(key => {
      oldDiff[key] = oldProps[key]
      newDiff[key] = newProps[key]
    })

    const cmd = new ModifyObjectCommand(this.canvas, object, oldDiff, newDiff)
    this.executeCommand(cmd)
    return cmd
  }

  moveLayer(object, oldIndex, newIndex) {
    const cmd = new MoveLayerCommand(this.canvas, object, oldIndex, newIndex)
    this.executeCommand(cmd)
    return cmd
  }

  applyFilter(object, oldFilters, newFilters) {
    const cmd = new FilterCommand(this.canvas, object, oldFilters, newFilters)
    this.executeCommand(cmd)
    return cmd
  }

  crop(oldState, newState) {
    const cmd = new CropCommand(this.canvas, oldState, newState)
    this.executeCommand(cmd)
    return cmd
  }

  undo() {
    if (this.undoStack.length === 0) return false

    const command = this.undoStack.pop()
    this.currentMemoryUsage -= command.getSize()
    command.undo()
    this.redoStack.push(command)

    return true
  }

  redo() {
    if (this.redoStack.length === 0) return false

    const command = this.redoStack.pop()
    command.execute()
    this.undoStack.push(command)
    this.currentMemoryUsage += command.getSize()

    return true
  }

  canUndo() {
    return this.undoStack.length > 0
  }

  canRedo() {
    return this.redoStack.length > 0
  }

  trimHistory() {
    while (this.undoStack.length > this.maxHistorySize) {
      const removed = this.undoStack.shift()
      this.currentMemoryUsage -= removed.getSize()
    }

    while (this.currentMemoryUsage > this.maxMemoryBytes && this.undoStack.length > 10) {
      const removed = this.undoStack.shift()
      this.currentMemoryUsage -= removed.getSize()
    }
  }

  getStats() {
    return {
      undoCount: this.undoStack.length,
      redoCount: this.redoStack.length,
      memoryUsage: this.formatSize(this.currentMemoryUsage),
      memoryLimit: this.formatSize(this.maxMemoryBytes),
      compressionRatio: this.calculateCompressionRatio()
    }
  }

  formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
  }

  calculateCompressionRatio() {
    const estimatedFullJsonSize = this.undoStack.length * 50000
    if (estimatedFullJsonSize === 0) return '100%'
    const ratio = (1 - this.currentMemoryUsage / estimatedFullJsonSize) * 100
    return ratio.toFixed(1) + '%'
  }

  clear() {
    this.undoStack = []
    this.redoStack = []
    this.currentMemoryUsage = 0
    this.batchMode = false
    this.batchCommands = []
  }

  dispose() {
    this.clear()
    this.canvas = null
  }
}

export const commandHistory = new CommandHistory()
export default CommandHistory
export {
  BaseCommand,
  AddObjectCommand,
  RemoveObjectCommand,
  ModifyObjectCommand,
  MoveLayerCommand,
  FilterCommand,
  CropCommand,
  CompoundCommand,
  generateId
}
