export const mockUsers = [
  { id: '1', name: '张三', email: 'zhangsan@example.com' },
  { id: '2', name: '李四', email: 'lisi@example.com' },
  { id: '3', name: '王五', email: 'wangwu@example.com' },
];

export const mockPosts = [
  { id: '1', title: 'GraphQL入门指南', content: 'GraphQL是一种API查询语言...', authorId: '1', createdAt: '2024-01-01' },
  { id: '2', title: 'Apollo Server最佳实践', content: '使用Apollo Server构建高性能API...', authorId: '2', createdAt: '2024-01-02' },
  { id: '3', title: '微服务架构设计', content: '微服务架构的核心原则...', authorId: '1', createdAt: '2024-01-03' },
  { id: '4', title: 'Node.js性能优化', content: 'Node.js应用性能优化技巧...', authorId: '3', createdAt: '2024-01-04' },
];

export const mockComments = [
  { id: '1', content: '非常棒的教程！', authorId: '2', postId: '1', createdAt: '2024-01-01' },
  { id: '2', content: '学到了很多，感谢分享', authorId: '3', postId: '1', createdAt: '2024-01-02' },
  { id: '3', content: '写得很详细', authorId: '1', postId: '2', createdAt: '2024-01-03' },
  { id: '4', content: '期待更多内容', authorId: '3', postId: '2', createdAt: '2024-01-04' },
];
