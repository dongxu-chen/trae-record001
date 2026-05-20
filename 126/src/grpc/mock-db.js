import { v4 as uuidv4 } from 'uuid';

const mockUsers = new Map();
const mockPosts = new Map();
const mockComments = new Map();

function initMockData() {
  const users = [
    { id: '1', name: '张三', email: 'zhang@example.com', role: 'admin', createdAt: new Date().toISOString() },
    { id: '2', name: '李四', email: 'li@example.com', role: 'user', createdAt: new Date().toISOString() },
    { id: '3', name: '王五', email: 'wang@example.com', role: 'user', createdAt: new Date().toISOString() },
  ];
  
  users.forEach(user => mockUsers.set(user.id, user));
  
  const posts = [
    { id: '1', title: 'GraphQL入门指南', content: 'GraphQL是一种API查询语言...', authorId: '1', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: '2', title: 'gRPC最佳实践', content: 'gRPC是一个高性能、开源的RPC框架...', authorId: '1', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: '3', title: '微服务架构设计', content: '微服务是一种架构风格...', authorId: '2', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  ];
  
  posts.forEach(post => mockPosts.set(post.id, post));
  
  const comments = [
    { id: '1', content: '非常详细的教程，感谢分享！', postId: '1', authorId: '2', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: '2', content: '学到了很多，期待更多内容', postId: '1', authorId: '3', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: '3', content: 'gRPC确实比REST快很多', postId: '2', authorId: '3', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  ];
  
  comments.forEach(comment => mockComments.set(comment.id, comment));
}

initMockData();

export const userDB = {
  get: (id) => mockUsers.get(id),
  getMany: (ids) => ids.map(id => mockUsers.get(id)).filter(Boolean),
  list: (limit, offset) => {
    const all = Array.from(mockUsers.values());
    return {
      users: all.slice(offset, offset + limit),
      total: all.length,
    };
  },
  create: (data) => {
    const user = {
      id: uuidv4(),
      ...data,
      createdAt: new Date().toISOString(),
    };
    mockUsers.set(user.id, user);
    return user;
  },
  update: (id, data) => {
    const user = mockUsers.get(id);
    if (!user) return null;
    const updated = { ...user, ...data };
    mockUsers.set(id, updated);
    return updated;
  },
  delete: (id) => mockUsers.delete(id),
};

export const postDB = {
  get: (id) => mockPosts.get(id),
  getMany: (ids) => ids.map(id => mockPosts.get(id)).filter(Boolean),
  getByAuthor: (authorId) => Array.from(mockPosts.values()).filter(p => p.authorId === authorId),
  list: (limit, offset) => {
    const all = Array.from(mockPosts.values());
    return {
      posts: all.slice(offset, offset + limit),
      total: all.length,
    };
  },
  create: (data) => {
    const post = {
      id: uuidv4(),
      ...data,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    mockPosts.set(post.id, post);
    return post;
  },
  update: (id, data) => {
    const post = mockPosts.get(id);
    if (!post) return null;
    const updated = { ...post, ...data, updatedAt: new Date().toISOString() };
    mockPosts.set(id, updated);
    return updated;
  },
  delete: (id) => mockPosts.delete(id),
};

export const commentDB = {
  get: (id) => mockComments.get(id),
  getMany: (ids) => ids.map(id => mockComments.get(id)).filter(Boolean),
  getByPost: (postId) => Array.from(mockComments.values()).filter(c => c.postId === postId),
  list: (limit, offset) => {
    const all = Array.from(mockComments.values());
    return {
      comments: all.slice(offset, offset + limit),
      total: all.length,
    };
  },
  create: (data) => {
    const comment = {
      id: uuidv4(),
      ...data,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    mockComments.set(comment.id, comment);
    return comment;
  },
  update: (id, data) => {
    const comment = mockComments.get(id);
    if (!comment) return null;
    const updated = { ...comment, ...data, updatedAt: new Date().toISOString() };
    mockComments.set(id, updated);
    return updated;
  },
  delete: (id) => mockComments.delete(id),
};

export default {
  userDB,
  postDB,
  commentDB,
};
