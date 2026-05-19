import { mockUsers } from './MockData.js';
import { globalRateLimiter } from '../utils/TokenBucket.js';

class UserAPI {
  constructor(rateLimiter = globalRateLimiter) {
    this.users = [...mockUsers];
    this.rateLimiter = rateLimiter;
  }

  async acquireToken(options = {}) {
    try {
      await this.rateLimiter.acquire(options);
      return true;
    } catch (error) {
      console.warn(`[UserAPI] Rate limit exceeded: ${error.message}`);
      throw new Error('Service rate limit exceeded. Please try again later.');
    }
  }

  async getUser(id) {
    await this.acquireToken({ priority: 1 });
    console.log(`[UserAPI] Fetching user with id: ${id}`);
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.users.find(user => user.id === id);
  }

  async getUsersByIds(ids) {
    await this.acquireToken({ tokens: Math.min(ids.length, 5), priority: 2 });
    console.log(`[UserAPI] Batch fetching ${ids.length} users`);
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.users.filter(user => ids.includes(user.id));
  }

  async getUsers() {
    await this.acquireToken({ priority: 1 });
    console.log('[UserAPI] Fetching all users');
    await new Promise(resolve => setTimeout(resolve, 50));
    return this.users;
  }

  async createUser(name, email) {
    await this.acquireToken({ tokens: 2, priority: 0 });
    console.log(`[UserAPI] Creating user: ${name}`);
    const newUser = {
      id: String(this.users.length + 1),
      name,
      email,
    };
    this.users.push(newUser);
    return newUser;
  }
}

export default UserAPI;
