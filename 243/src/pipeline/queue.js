const { EventEmitter } = require('events');

class PipelineQueue extends EventEmitter {
  constructor({ logger, config }) {
    super();
    this.logger = logger;
    this.config = config;
    this.queues = new Map();
    this.activePipelines = new Set();
    this.maxConcurrent = config.pipeline?.maxConcurrentPerGroup || 1;
  }

  getGroupKey(repository, branch) {
    return `${repository}:${branch}`;
  }

  async enqueue(pipelineId, triggerData, executeFn) {
    const groupKey = this.getGroupKey(triggerData.repository, triggerData.branch);
    
    if (!this.queues.has(groupKey)) {
      this.queues.set(groupKey, []);
    }

    const queue = this.queues.get(groupKey);
    const queueItem = {
      pipelineId,
      triggerData,
      executeFn,
      queuedAt: Date.now(),
      position: queue.length + 1
    };

    queue.push(queueItem);
    
    this.logger.info('流水线已加入队列', {
      pipelineId,
      groupKey,
      position: queueItem.position,
      queueLength: queue.length
    });

    this.emit('queued', { pipelineId, groupKey, position: queueItem.position });

    this.processQueue(groupKey);

    return queueItem.position;
  }

  async processQueue(groupKey) {
    const queue = this.queues.get(groupKey);
    if (!queue || queue.length === 0) {
      return;
    }

    const activeInGroup = Array.from(this.activePipelines).filter(id => {
      const item = this.findPipelineInQueues(id);
      return item && this.getGroupKey(item.triggerData.repository, item.triggerData.branch) === groupKey;
    });

    if (activeInGroup.length >= this.maxConcurrent) {
      this.logger.debug('队列组已满，等待空闲', { 
        groupKey, 
        active: activeInGroup.length 
      });
      return;
    }

    const nextItem = queue.shift();
    if (!nextItem) return;

    this.activePipelines.add(nextItem.pipelineId);

    this.logger.info('开始执行队列中的流水线', {
      pipelineId: nextItem.pipelineId,
      groupKey,
      waitTime: Date.now() - nextItem.queuedAt
    });

    this.emit('dequeued', { pipelineId: nextItem.pipelineId, groupKey });

    try {
      await nextItem.executeFn();
    } finally {
      this.activePipelines.delete(nextItem.pipelineId);
      
      queue.forEach((item, index) => {
        item.position = index + 1;
      });

      this.processQueue(groupKey);
    }
  }

  findPipelineInQueues(pipelineId) {
    for (const [, queue] of this.queues) {
      const item = queue.find(i => i.pipelineId === pipelineId);
      if (item) return item;
    }
    return null;
  }

  getQueueStatus(groupKey) {
    const queue = this.queues.get(groupKey) || [];
    return {
      groupKey,
      queued: queue.length,
      active: Array.from(this.activePipelines).filter(id => {
        const item = this.findPipelineInQueues(id);
        return item && this.getGroupKey(item.triggerData.repository, item.triggerData.branch) === groupKey;
      }).length,
      items: queue.map(item => ({
        pipelineId: item.pipelineId,
        position: item.position,
        queuedAt: item.queuedAt,
        triggerData: {
          repository: item.triggerData.repository,
          branch: item.triggerData.branch,
          commit: item.triggerData.commit
        }
      }))
    };
  }

  getAllQueueStatus() {
    const statuses = [];
    for (const groupKey of this.queues.keys()) {
      statuses.push(this.getQueueStatus(groupKey));
    }
    return statuses;
  }

  cancelPipeline(pipelineId) {
    for (const [groupKey, queue] of this.queues) {
      const index = queue.findIndex(i => i.pipelineId === pipelineId);
      if (index !== -1) {
        queue.splice(index, 1);
        queue.forEach((item, i) => {
          item.position = i + 1;
        });
        
        this.logger.info('流水线已从队列中取消', { pipelineId, groupKey });
        this.emit('cancelled', { pipelineId, groupKey });
        
        return true;
      }
    }
    return false;
  }

  clearQueue(groupKey) {
    if (this.queues.has(groupKey)) {
      const queue = this.queues.get(groupKey);
      const count = queue.length;
      queue.length = 0;
      
      this.logger.info('队列已清空', { groupKey, count });
      return count;
    }
    return 0;
  }

  clearAllQueues() {
    let total = 0;
    for (const groupKey of this.queues.keys()) {
      total += this.clearQueue(groupKey);
    }
    return total;
  }
}

module.exports = PipelineQueue;
