import { mockComments } from './MockData.js';
import { globalRateLimiter } from '../utils/TokenBucket.js';

class CommentAPI {
  constructor(rateLimiter = globalRateLimiter) {
    this.comments = [...mockComments];
    this.rateLimiter = rateLimiter;
  }

  async acquireToken(options = {}) {
    try {
      await this.rateLimiter.acquire(options);
      return true;
    } catch (error) {
      console.warn(`[CommentAPI] Rate limit exceeded: ${error.message}`);
      throw new Error('Service rate limit exceeded. Please try again later.');
    }
  }

  async getComment(id) {
    await this.acquireToken({ priority: 1 });
    console.log(`[CommentAPI] Fetching comment with id: ${id}`);
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.comments.find(comment => comment.id === id);
  }

  async getCommentsByIds(ids) {
    await this.acquireToken({ tokens: Math.min(ids.length, 5), priority: 2 });
    console.log(`[CommentAPI] Batch fetching ${ids.length} comments`);
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.comments.filter(comment => ids.includes(comment.id));
  }

  async getCommentsByAuthorIds(authorIds) {
    await this.acquireToken({ tokens: Math.min(authorIds.length * 2, 5), priority: 2 });
    console.log(`[CommentAPI] Batch fetching comments for ${authorIds.length} authors`);
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.comments.filter(comment => authorIds.includes(comment.authorId));
  }

  async getCommentsByPostIds(postIds) {
    await this.acquireToken({ tokens: Math.min(postIds.length * 2, 5), priority: 2 });
    console.log(`[CommentAPI] Batch fetching comments for ${postIds.length} posts`);
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.comments.filter(comment => postIds.includes(comment.postId));
  }

  async getComments() {
    await this.acquireToken({ priority: 1 });
    console.log('[CommentAPI] Fetching all comments');
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.comments;
  }

  async getCommentsByAuthor(authorId) {
    await this.acquireToken({ priority: 1 });
    console.log(`[CommentAPI] Fetching comments by author: ${authorId}`);
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.comments.filter(comment => comment.authorId === authorId);
  }

  async getCommentsByPost(postId) {
    await this.acquireToken({ priority: 1 });
    console.log(`[CommentAPI] Fetching comments for post: ${postId}`);
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.comments.filter(comment => comment.postId === postId);
  }

  async createComment(content, authorId, postId) {
    await this.acquireToken({ tokens: 2, priority: 0 });
    console.log(`[CommentAPI] Creating comment for post: ${postId}`);
    const newComment = {
      id: String(this.comments.length + 1),
      content,
      authorId,
      postId,
      createdAt: new Date().toISOString().split('T')[0],
    };
    this.comments.push(newComment);
    return newComment;
  }
}

export default CommentAPI;
