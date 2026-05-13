function generateUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

const LotteryAPI = {
  baseURL: '',
  pendingRequests: new Map(),

  async getPrizes() {
    try {
      const response = await fetch(`${this.baseURL}/api/prizes`);
      if (!response.ok) {
        throw new Error('获取奖品列表失败');
      }
      return await response.json();
    } catch (error) {
      console.error('获取奖品列表出错:', error);
      throw error;
    }
  },

  async draw(userId = 'anonymous') {
    const requestKey = `draw:${userId}`;

    if (this.pendingRequests.has(requestKey)) {
      throw new Error('抽奖请求正在处理中，请稍候');
    }

    const drawUuid = generateUUID();
    this.pendingRequests.set(requestKey, drawUuid);

    try {
      const response = await fetch(`${this.baseURL}/api/draw`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ userId, drawUuid })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || '抽奖失败');
      }

      return data;
    } catch (error) {
      console.error('抽奖出错:', error);
      throw error;
    } finally {
      this.pendingRequests.delete(requestKey);
    }
  },

  async getRecords() {
    try {
      const response = await fetch(`${this.baseURL}/api/records`);
      if (!response.ok) {
        throw new Error('获取抽奖记录失败');
      }
      return await response.json();
    } catch (error) {
      console.error('获取抽奖记录出错:', error);
      throw error;
    }
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = LotteryAPI;
}
