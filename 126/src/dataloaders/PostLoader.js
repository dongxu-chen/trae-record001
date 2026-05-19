import DataLoader from 'dataloader';

class PostLoader {
  constructor(postAPI) {
    this.postAPI = postAPI;
    
    this.batchLoader = new DataLoader(async (ids) => {
      console.log(`[PostLoader] Batch loading ${ids.length} posts: ${ids.join(', ')}`);
      const posts = await this.postAPI.getPostsByIds(ids);
      return ids.map(id => posts.find(post => post.id === id) || null);
    }, {
      maxBatchSize: 100,
      cache: false,
    });

    this.byAuthorLoader = new DataLoader(async (authorIds) => {
      console.log(`[PostLoader] Batch loading posts for ${authorIds.length} authors`);
      const posts = await this.postAPI.getPostsByAuthorIds(authorIds);
      return authorIds.map(authorId => posts.filter(post => post.authorId === authorId));
    }, {
      maxBatchSize: 50,
      cache: false,
    });
  }

  async load(id) {
    return this.batchLoader.load(id);
  }

  async loadByAuthorId(authorId) {
    return this.byAuthorLoader.load(authorId);
  }

  clear(id) {
    this.batchLoader.clear(id);
  }

  clearAll() {
    this.batchLoader.clearAll();
    this.byAuthorLoader.clearAll();
  }
}

export default PostLoader;
