import DataLoader from 'dataloader';

class UserLoader {
  constructor(userAPI) {
    this.userAPI = userAPI;
    this.batchLoader = new DataLoader(async (ids) => {
      console.log(`[UserLoader] Batch loading ${ids.length} users: ${ids.join(', ')}`);
      const users = await this.userAPI.getUsersByIds(ids);
      return ids.map(id => users.find(user => user.id === id) || null);
    }, {
      maxBatchSize: 100,
      cache: false,
    });
  }

  async load(id) {
    return this.batchLoader.load(id);
  }

  async loadMany(ids) {
    return this.batchLoader.loadMany(ids);
  }

  clear(id) {
    this.batchLoader.clear(id);
  }

  clearAll() {
    this.batchLoader.clearAll();
  }
}

export default UserLoader;
