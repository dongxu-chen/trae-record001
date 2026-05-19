import DataLoader from 'dataloader';

class CommentLoader {
  constructor(commentAPI) {
    this.commentAPI = commentAPI;
    
    this.batchLoader = new DataLoader(async (ids) => {
      console.log(`[CommentLoader] Batch loading ${ids.length} comments: ${ids.join(', ')}`);
      const comments = await this.commentAPI.getCommentsByIds(ids);
      return ids.map(id => comments.find(comment => comment.id === id) || null);
    }, {
      maxBatchSize: 100,
      cache: false,
    });

    this.byAuthorLoader = new DataLoader(async (authorIds) => {
      console.log(`[CommentLoader] Batch loading comments for ${authorIds.length} authors`);
      const comments = await this.commentAPI.getCommentsByAuthorIds(authorIds);
      return authorIds.map(authorId => comments.filter(comment => comment.authorId === authorId));
    }, {
      maxBatchSize: 50,
      cache: false,
    });

    this.byPostLoader = new DataLoader(async (postIds) => {
      console.log(`[CommentLoader] Batch loading comments for ${postIds.length} posts`);
      const comments = await this.commentAPI.getCommentsByPostIds(postIds);
      return postIds.map(postId => comments.filter(comment => comment.postId === postId));
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

  async loadByPostId(postId) {
    return this.byPostLoader.load(postId);
  }

  clear(id) {
    this.batchLoader.clear(id);
  }

  clearAll() {
    this.batchLoader.clearAll();
    this.byAuthorLoader.clearAll();
    this.byPostLoader.clearAll();
  }
}

export default CommentLoader;
