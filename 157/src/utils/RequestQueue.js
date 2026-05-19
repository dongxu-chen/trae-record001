export class RequestQueue {
  constructor(maxConcurrent = 3) {
    this.maxConcurrent = maxConcurrent
    this.queue = []
    this.activeCount = 0
    this.processing = false
  }

  add(task) {
    return new Promise((resolve, reject) => {
      this.queue.push({ task, resolve, reject })
      this.process()
    })
  }

  async process() {
    if (this.processing || this.activeCount >= this.maxConcurrent) {
      return
    }

    this.processing = true

    while (this.queue.length > 0 && this.activeCount < this.maxConcurrent) {
      const item = this.queue.shift()
      this.activeCount++
      
      try {
        const result = await item.task()
        item.resolve(result)
      } catch (error) {
        item.reject(error)
      } finally {
        this.activeCount--
      }
    }

    this.processing = false
  }

  clear() {
    this.queue = []
  }

  size() {
    return this.queue.length + this.activeCount
  }

  pendingCount() {
    return this.queue.length
  }

  activeCount() {
    return this.activeCount
  }
}

export default RequestQueue
