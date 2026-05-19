export class MessageBus {
  constructor() {
    this.subscribers = new Map();
    this._setupMessageListener();
  }

  _setupMessageListener() {
    window.addEventListener('message', (event) => {
      const message = event.data;
      if (!message || !message.type) return;

      this._notifySubscribers(message);
      this._handleLinkEvent(message);
    });
  }

  _notifySubscribers(message) {
    const callbacks = this.subscribers.get(message.type) || [];
    callbacks.forEach((cb) => {
      try {
        cb(message.payload, message);
      } catch (e) {
        console.error('[MessageBus] 回调执行失败:', e);
      }
    });
  }

  _handleLinkEvent(message) {
    if (message.type === 'chart-click' && message.payload.targets) {
      const targets = message.payload.targets;
      
      if (targets.includes('all')) {
        this.publish('refresh-chart', {}, 'all');
      } else {
        targets.forEach((targetId) => {
          this.publish('refresh-chart', { sourceId: message.sourceId }, targetId);
        });
      }
    }
  }

  subscribe(type, callback) {
    if (!this.subscribers.has(type)) {
      this.subscribers.set(type, new Set());
    }
    this.subscribers.get(type).add(callback);

    return () => {
      this.subscribers.get(type)?.delete(callback);
    };
  }

  publish(type, payload, targetId = null) {
    const message = {
      type,
      payload,
      targetId,
      timestamp: Date.now()
    };

    window.postMessage(message, '*');
    return message;
  }

  broadcast(type, payload) {
    return this.publish(type, payload, 'all');
  }

  sendTo(targetId, type, payload) {
    return this.publish(type, payload, targetId);
  }

  unsubscribe(type, callback = null) {
    if (callback) {
      this.subscribers.get(type)?.delete(callback);
    } else {
      this.subscribers.delete(type);
    }
  }

  clear() {
    this.subscribers.clear();
  }

  getSubscribersCount(type) {
    return this.subscribers.get(type)?.size || 0;
  }
}

export const messageBus = new MessageBus();

export default MessageBus;
