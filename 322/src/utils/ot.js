import { OT_OPERATION_TYPES } from '../constants'

class OperationalTransform {
  constructor() {
    this.version = 0
    this.history = []
    this.pendingOperations = []
    this.maxHistory = 1000
  }

  createOperation(type, annotationId, data, userId) {
    return {
      id: this.generateOpId(),
      type,
      annotationId,
      data,
      userId,
      version: this.version,
      timestamp: Date.now()
    }
  }

  generateOpId() {
    return `op_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  applyOperation(operation, annotations) {
    const { type, annotationId, data } = operation
    let result = [...annotations]

    switch (type) {
      case OT_OPERATION_TYPES.CREATE:
        if (!result.find(a => a.id === annotationId)) {
          result.push(data)
        }
        break

      case OT_OPERATION_TYPES.UPDATE:
        result = result.map(a => 
          a.id === annotationId ? { ...a, ...data, updatedAt: Date.now() } : a
        )
        break

      case OT_OPERATION_TYPES.DELETE:
        result = result.filter(a => a.id !== annotationId)
        break

      case OT_OPERATION_TYPES.MOVE:
        result = result.map(a => {
          if (a.id === annotationId) {
            return {
              ...a,
              canvasCoords: data.canvasCoords || a.canvasCoords,
              imageCoords: data.imageCoords || a.imageCoords,
              updatedAt: Date.now()
            }
          }
          return a
        })
        break

      case OT_OPERATION_TYPES.RESIZE:
        result = result.map(a => {
          if (a.id === annotationId) {
            return {
              ...a,
              canvasCoords: data.canvasCoords || a.canvasCoords,
              imageCoords: data.imageCoords || a.imageCoords,
              updatedAt: Date.now()
            }
          }
          return a
        })
        break
    }

    this.history.push(operation)
    if (this.history.length > this.maxHistory) {
      this.history.shift()
    }
    this.version++

    return result
  }

  transform(op1, op2) {
    if (op1.annotationId !== op2.annotationId) {
      return { left: op1, right: op2 }
    }

    if (op1.timestamp <= op2.timestamp) {
      return { left: op1, right: this.transformAgainst(op2, op1) }
    } else {
      return { left: this.transformAgainst(op1, op2), right: op2 }
    }
  }

  transformAgainst(op, againstOp) {
    const transformed = { ...op, version: againstOp.version + 1 }

    if (op.type === OT_OPERATION_TYPES.MOVE && againstOp.type === OT_OPERATION_TYPES.RESIZE) {
      if (op.data.canvasCoords && againstOp.data.canvasCoords) {
        const deltaX = (againstOp.data.canvasCoords.left || 0) - (againstOp.data.prevLeft || 0)
        const deltaY = (againstOp.data.canvasCoords.top || 0) - (againstOp.data.prevTop || 0)
        
        transformed.data = {
          ...op.data,
          canvasCoords: {
            ...op.data.canvasCoords,
            left: (op.data.canvasCoords.left || 0) + deltaX * 0.5,
            top: (op.data.canvasCoords.top || 0) + deltaY * 0.5
          }
        }
      }
    }

    if (op.type === OT_OPERATION_TYPES.RESIZE && againstOp.type === OT_OPERATION_TYPES.RESIZE) {
      if (op.data.canvasCoords && againstOp.data.canvasCoords) {
        const prevRight = (againstOp.data.prevLeft || 0) + (againstOp.data.prevWidth || 0)
        const prevBottom = (againstOp.data.prevTop || 0) + (againstOp.data.prevHeight || 0)
        const newRight = (againstOp.data.canvasCoords.left || 0) + (againstOp.data.canvasCoords.width || 0)
        const newBottom = (againstOp.data.canvasCoords.top || 0) + (againstOp.data.canvasCoords.height || 0)
        
        const rightDelta = newRight - prevRight
        const bottomDelta = newBottom - prevBottom

        transformed.data = {
          ...op.data,
          canvasCoords: {
            ...op.data.canvasCoords,
            width: Math.max(20, (op.data.canvasCoords.width || 0) + rightDelta * 0.3),
            height: Math.max(20, (op.data.canvasCoords.height || 0) + bottomDelta * 0.3)
          }
        }
      }
    }

    return transformed
  }

  mergeOperations(localOps, remoteOps) {
    const merged = []
    let localIndex = 0
    let remoteIndex = 0

    while (localIndex < localOps.length && remoteIndex < remoteOps.length) {
      const localOp = localOps[localIndex]
      const remoteOp = remoteOps[remoteIndex]

      if (localOp.timestamp <= remoteOp.timestamp) {
        merged.push(localOp)
        localIndex++
      } else {
        let transformedRemote = remoteOp
        for (let i = 0; i < localIndex; i++) {
          const { right } = this.transform(localOps[i], transformedRemote)
          transformedRemote = right
        }
        merged.push(transformedRemote)
        remoteIndex++
      }
    }

    while (localIndex < localOps.length) {
      merged.push(localOps[localIndex++])
    }

    while (remoteIndex < remoteOps.length) {
      let transformedRemote = remoteOps[remoteIndex]
      for (let i = 0; i < localIndex; i++) {
        const { right } = this.transform(localOps[i], transformedRemote)
        transformedRemote = right
      }
      merged.push(transformedRemote)
      remoteIndex++
    }

    return merged
  }

  canMerge(op1, op2) {
    if (op1.type !== op2.type) return false
    if (op1.annotationId !== op2.annotationId) return false
    if (op1.userId !== op2.userId) return false
    
    const timeDiff = op2.timestamp - op1.timestamp
    return timeDiff < 500
  }

  mergeAdjacentOps(operations) {
    if (operations.length < 2) return operations

    const result = [operations[0]]
    for (let i = 1; i < operations.length; i++) {
      const last = result[result.length - 1]
      const current = operations[i]

      if (this.canMerge(last, current)) {
        result[result.length - 1] = {
          ...last,
          data: { ...last.data, ...current.data },
          timestamp: current.timestamp
        }
      } else {
        result.push(current)
      }
    }

    return result
  }

  getOperationsSince(version) {
    return this.history.filter(op => op.version > version)
  }

  reset() {
    this.version = 0
    this.history = []
    this.pendingOperations = []
  }
}

const ot = new OperationalTransform()
export default ot
