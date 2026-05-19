import { mockPosts } from './MockData.js';
import { globalRateLimiter } from '../utils/TokenBucket.js';

class PostAPI {
  constructor(rateLimiter = globalRateLimiter) {
    this.posts = [...mockPosts];
    this.rateLimiter = rateLimiter;
  }

  async acquireToken(options = {}) {
    try {
      await this.rateLimiter.acquire(options);
      return true;
    } catch (error) {
      console.warn(`[PostAPI] Rate limit exceeded: ${error.message}`);
      throw new Error('Service rate limit exceeded. Please try again later.');
    }
  }

  async getPost(id) {
    await this.acquireToken({ priority: 1 });
    console.log(`[PostAPI] Fetching post with id: ${id}`);
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.posts.find(post => post.id === id);
  }

  async getPostsByIds(ids) {
    await this.acquireToken({ tokens: Math.min(ids.length, 5), priority: 2 });
    console.log(`[PostAPI] Batch fetching ${ids.length} posts`);
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.posts.filter(post => ids.includes(post.id));
  }

  async getPostsByAuthorIds(authorIds) {
    await this.acquireToken({ tokens: Math.min(authorIds.length * 2, 5), priority: 2 });
    console.log(`[PostAPI] Batch fetching posts for ${authorIds.length} authors`);
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.posts.filter(post => authorIds.includes(post.authorId));
  }

  async getPosts(limit = 10) {
    await this.acquireToken({ tokens: Math.ceil(limit / 10), priority: 1 });
    console.log(`[PostAPI] Fetching ${limit} posts`);
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.posts.slice(0, limit);
  }

  async getPostsByAuthor(authorId) {
    await this.acquireToken({ priority: 1 });
    console.log(`[PostAPI] Fetching posts by author: ${authorId}`);
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.posts.filter(post => post.authorId === authorId);
  }

  async createPost(title, content, authorId) {
    await this.acquireToken({ tokens: 3, priority: 0 });
    console.log(`[PostAPI] Creating post: ${title}`);
    const newPost = {
      id: String(this.posts.length + 1),
      title,
      content,
      authorId,
      createdAt: new Date().toISOString().split('T')[0],
    };
    this.posts.push(newPost);
    return newPost;
  }
}

export default PostAPI;
