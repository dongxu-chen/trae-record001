const AdminAPI = {
  baseURL: '',

  async getStats() {
    const resp = await fetch(`${this.baseURL}/api/admin/stats`);
    if (!resp.ok) throw new Error('获取统计失败');
    return resp.json();
  },

  async resetInventory(password, prizeId = null) {
    const body = { password };
    if (prizeId !== null) body.prizeId = prizeId;

    const resp = await fetch(`${this.baseURL}/api/admin/reset-inventory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });

    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || '操作失败');
    return data;
  },

  async getRecords(limit = 50) {
    const resp = await fetch(`${this.baseURL}/api/records?limit=${limit}`);
    if (!resp.ok) throw new Error('获取记录失败');
    return resp.json();
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = AdminAPI;
}
