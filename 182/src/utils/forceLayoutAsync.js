class ForceLayoutWorker {
  constructor() {
    this.worker = null
    this.pendingRequests = new Map()
    this.requestId = 0
  }

  _initWorker() {
    if (this.worker) return

    try {
      this.worker = new Worker(new URL('../workers/forceLayoutWorker.js', import.meta.url), {
        type: 'module'
      })

      this.worker.onmessage = (e) => {
        const { requestId, type, result, error } = e.data
        const resolver = this.pendingRequests.get(requestId)
        if (resolver) {
          if (type === 'success') {
            resolver.resolve(result)
          } else {
            resolver.reject(new Error(error))
          }
          this.pendingRequests.delete(requestId)
        }
      }

      this.worker.onerror = (error) => {
        console.error('Force layout worker error:', error)
        this.pendingRequests.forEach((resolver) => {
          resolver.reject(error)
        })
        this.pendingRequests.clear()
        this._destroyWorker()
      }
    } catch (e) {
      console.warn('Failed to create web worker, falling back to synchronous calculation:', e)
      this.worker = null
    }
  }

  _destroyWorker() {
    if (this.worker) {
      this.worker.terminate()
      this.worker = null
    }
  }

  async calculate(nodes, edges, options = {}) {
    const { prepareLayoutNodes, restoreChildPositions } = await import('./layoutEngine.js')

    const { layoutNodes, layoutEdges, placeholderMap } = prepareLayoutNodes(nodes, edges)

    if (!this.worker) {
      this._initWorker()
    }

    if (!this.worker) {
      const { applyForceDirectedLayout } = await import('./layoutEngine.js')
      return applyForceDirectedLayout(nodes, edges, options)
    }

    return new Promise((resolve, reject) => {
      const requestId = ++this.requestId
      this.pendingRequests.set(requestId, { resolve, reject })

      try {
        this.worker.postMessage({
          requestId,
          nodes: layoutNodes,
          edges: layoutEdges,
          options
        })
      } catch (e) {
        this.pendingRequests.delete(requestId)
        reject(e)
      }
    }).then((nodePositions) => {
      placeholderMap.forEach((placeholder, groupId) => {
        const pos = nodePositions[groupId]
        if (pos) {
          placeholder.x = pos.x
          placeholder.y = pos.y
          const groupNode = nodes.find(n => n.id === groupId)
          if (groupNode) {
            restoreChildPositions(groupNode, placeholder, nodes)
          }
        }
      })
      return nodePositions
    })
  }

  dispose() {
    this._destroyWorker()
    this.pendingRequests.clear()
  }
}

let instance = null

export function getForceLayoutWorker() {
  if (!instance) {
    instance = new ForceLayoutWorker()
  }
  return instance
}

export async function applyForceDirectedLayoutAsync(nodes, edges, options = {}) {
  return getForceLayoutWorker().calculate(nodes, edges, options)
}
