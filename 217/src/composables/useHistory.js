import { ref, computed } from 'vue'

export function useHistory() {
  const history = ref([])
  const currentIndex = ref(-1)
  const maxHistory = 100

  const canUndo = computed(() => currentIndex.value > 0)
  const canRedo = computed(() => currentIndex.value < history.value.length - 1)

  const executeCommand = (command) => {
    if (currentIndex.value < history.value.length - 1) {
      history.value = history.value.slice(0, currentIndex.value + 1)
    }

    command.execute()

    history.value.push(command)

    if (history.value.length > maxHistory) {
      history.value.shift()
    } else {
      currentIndex.value++
    }
  }

  const undo = () => {
    if (!canUndo.value) return

    const command = history.value[currentIndex.value]
    if (command && command.undo) {
      command.undo()
    }
    currentIndex.value--
  }

  const redo = () => {
    if (!canRedo.value) return

    currentIndex.value++
    const command = history.value[currentIndex.value]
    if (command && command.redo) {
      command.redo()
    } else if (command && command.execute) {
      command.execute()
    }
  }

  const reset = () => {
    history.value = []
    currentIndex.value = -1
  }

  return {
    canUndo,
    canRedo,
    executeCommand,
    undo,
    redo,
    reset
  }
}

export function createAddNodeCommand(nodeData, addFn, removeFn) {
  return {
    type: 'ADD_NODE',
    data: { node: { ...nodeData } },
    execute() {
      addFn(this.data.node)
    },
    undo() {
      removeFn(this.data.node.id)
    },
    redo() {
      addFn(this.data.node)
    }
  }
}

export function createDeleteNodeCommand(nodeData, relatedConnections, addFn, removeFn, addConnFn, removeConnFn) {
  return {
    type: 'DELETE_NODE',
    data: {
      node: { ...nodeData },
      connections: relatedConnections.map(c => ({ ...c }))
    },
    execute() {
      removeFn(this.data.node.id)
    },
    undo() {
      addFn(this.data.node)
      this.data.connections.forEach(conn => {
        const existing = { ...conn, fabricObject: null }
        addConnFn(existing, true)
      })
    },
    redo() {
      removeFn(this.data.node.id)
    }
  }
}

export function createUpdateNodeCommand(nodeId, oldData, newData, updateFn) {
  return {
    type: 'UPDATE_NODE',
    data: {
      nodeId,
      oldData: { ...oldData },
      newData: { ...newData }
    },
    execute() {
      updateFn(nodeId, this.data.newData)
    },
    undo() {
      updateFn(nodeId, this.data.oldData)
    },
    redo() {
      updateFn(nodeId, this.data.newData)
    }
  }
}

export function createMoveNodeCommand(nodeId, oldPos, newPos, moveFn) {
  return {
    type: 'MOVE_NODE',
    data: {
      nodeId,
      oldPos: { ...oldPos },
      newPos: { ...newPos }
    },
    execute() {
      moveFn(nodeId, this.data.newPos.x, this.data.newPos.y)
    },
    undo() {
      moveFn(nodeId, this.data.oldPos.x, this.data.oldPos.y)
    },
    redo() {
      moveFn(nodeId, this.data.newPos.x, this.data.newPos.y)
    }
  }
}

export function createAddConnectionCommand(connData, addFn, removeFn) {
  return {
    type: 'ADD_CONNECTION',
    data: { connection: { ...connData } },
    execute() {
      addFn(this.data.connection, true)
    },
    undo() {
      removeFn(this.data.connection.id)
    },
    redo() {
      addFn(this.data.connection, true)
    }
  }
}

export function createDeleteConnectionCommand(connData, addFn, removeFn) {
  return {
    type: 'DELETE_CONNECTION',
    data: { connection: { ...connData } },
    execute() {
      removeFn(this.data.connection.id)
    },
    undo() {
      addFn(this.data.connection, true)
    },
    redo() {
      removeFn(this.data.connection.id)
    }
  }
}

export function createAutoLayoutCommand(oldPositions, newPositions, moveFn) {
  return {
    type: 'AUTO_LAYOUT',
    data: {
      oldPositions: oldPositions.map(p => ({ ...p })),
      newPositions: newPositions.map(p => ({ ...p }))
    },
    execute() {
      this.data.newPositions.forEach(pos => {
        moveFn(pos.id, pos.x, pos.y)
      })
    },
    undo() {
      this.data.oldPositions.forEach(pos => {
        moveFn(pos.id, pos.x, pos.y)
      })
    },
    redo() {
      this.data.newPositions.forEach(pos => {
        moveFn(pos.id, pos.x, pos.y)
      })
    }
  }
}

export function createClearAllCommand(oldNodes, oldConnections, addFn, removeAllFn, addConnFn) {
  return {
    type: 'CLEAR_ALL',
    data: {
      nodes: oldNodes.map(n => ({ ...n, fabricObject: null })),
      connections: oldConnections.map(c => ({ ...c, fabricObject: null }))
    },
    execute() {
      removeAllFn()
    },
    undo() {
      this.data.nodes.forEach(node => {
        addFn(node)
      })
      this.data.connections.forEach(conn => {
        addConnFn(conn, true)
      })
    },
    redo() {
      removeAllFn()
    }
  }
}
