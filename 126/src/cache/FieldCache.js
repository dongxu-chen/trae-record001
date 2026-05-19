import { LRUCache } from 'lru-cache';

class FieldCache {
  constructor(options = {}) {
    this.defaultTTL = options.defaultTTL || 1000 * 60 * 5;
    this.fieldTTLs = options.fieldTTLs || {};
    
    this.cache = new LRUCache({
      max: options.max || 1000,
      ttl: this.defaultTTL,
      ttlAutopurge: true,
    });
  }

  generateKey(typeName, fieldName, args = {}, parent = null) {
    const argsKey = Object.keys(args).sort().map(k => `${k}:${JSON.stringify(args[k])}`).join(',');
    const parentKey = parent ? JSON.stringify(parent) : '';
    return `${typeName}:${fieldName}:${argsKey}:${parentKey}`;
  }

  getFieldTTL(typeName, fieldName) {
    return this.fieldTTLs[`${typeName}.${fieldName}`] || this.defaultTTL;
  }

  setFieldTTL(typeName, fieldName, ttl) {
    this.fieldTTLs[`${typeName}.${fieldName}`] = ttl;
    console.log(`[Cache TTL] Set ${typeName}.${fieldName} TTL to ${ttl}ms`);
  }

  async get(typeName, fieldName, args, parent, fetcher, options = {}) {
    const key = this.generateKey(typeName, fieldName, args, parent);
    
    if (!options.forceRefresh) {
      const cached = this.cache.get(key);
      if (cached !== undefined) {
        const remainingTTL = this.cache.getRemainingTTL(key);
        console.log(`[Cache HIT] ${key} (TTL remaining: ${Math.round(remainingTTL/1000)}s)`);
        return cached;
      }
    }

    console.log(`[Cache ${options.forceRefresh ? 'FORCE REFRESH' : 'MISS'}] ${key}`);
    const value = await fetcher();
    const ttl = options.ttl || this.getFieldTTL(typeName, fieldName);
    this.cache.set(key, value, { ttl });
    return value;
  }

  set(typeName, fieldName, args, parent, value, options = {}) {
    const key = this.generateKey(typeName, fieldName, args, parent);
    const ttl = options.ttl || this.getFieldTTL(typeName, fieldName);
    this.cache.set(key, value, { ttl });
    console.log(`[Cache SET] ${key} (TTL: ${ttl}ms)`);
  }

  refresh(typeName, fieldName, args, parent, fetcher) {
    return this.get(typeName, fieldName, args, parent, fetcher, { forceRefresh: true });
  }

  refreshByPattern(pattern) {
    const keysToRefresh = [];
    for (const key of this.cache.keys()) {
      if (pattern instanceof RegExp ? pattern.test(key) : key.includes(pattern)) {
        keysToRefresh.push(key);
      }
    }
    keysToRefresh.forEach(key => this.cache.delete(key));
    console.log(`[Cache REFRESH] Refreshed ${keysToRefresh.length} entries matching pattern`);
    return keysToRefresh.length;
  }

  getRemainingTTL(typeName, fieldName, args, parent) {
    const key = this.generateKey(typeName, fieldName, args, parent);
    return this.cache.getRemainingTTL(key);
  }

  invalidate(typeName, fieldName) {
    const keysToDelete = [];
    for (const key of this.cache.keys()) {
      if (key.startsWith(`${typeName}:${fieldName}`)) {
        keysToDelete.push(key);
      }
    }
    keysToDelete.forEach(key => this.cache.delete(key));
    console.log(`[Cache INVALIDATE] ${keysToDelete.length} entries for ${typeName}.${fieldName}`);
    return keysToDelete.length;
  }

  invalidateByKey(key) {
    const deleted = this.cache.delete(key);
    if (deleted) {
      console.log(`[Cache INVALIDATE] Deleted ${key}`);
    }
    return deleted;
  }

  clear() {
    const size = this.cache.size;
    this.cache.clear();
    console.log(`[Cache CLEAR] Cleared ${size} entries`);
    return size;
  }

  getStats() {
    return {
      size: this.cache.size,
      max: this.cache.max,
      defaultTTL: this.defaultTTL,
      fieldTTLs: this.fieldTTLs,
    };
  }

  peek(typeName, fieldName, args, parent) {
    const key = this.generateKey(typeName, fieldName, args, parent);
    return this.cache.peek(key);
  }

  has(typeName, fieldName, args, parent) {
    const key = this.generateKey(typeName, fieldName, args, parent);
    return this.cache.has(key);
  }
}

export const fieldCache = new FieldCache({
  max: 1000,
  defaultTTL: 1000 * 60 * 5,
  fieldTTLs: {
    'Query.getUser': 1000 * 60 * 10,
    'Query.getPost': 1000 * 60 * 15,
    'User.posts': 1000 * 60 * 5,
    'Post.comments': 1000 * 60 * 2,
  },
});

export const withFieldCache = (resolver, typeName, fieldName) => {
  return async (parent, args, context, info) => {
    const forceRefresh = args._refresh || false;
    const customTTL = args._ttl;
    
    delete args._refresh;
    delete args._ttl;
    
    return context.fieldCache.get(
      typeName,
      fieldName,
      args,
      parent,
      () => resolver(parent, args, context, info),
      { forceRefresh, ttl: customTTL }
    );
  };
};
