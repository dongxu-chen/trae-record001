# API聚合与编排引擎 - 示例查询

## 1. 简单查询 - 获取用户
```graphql
query GetUser {
  getUser(id: "1") {
    id
    name
    email
  }
}
```

## 2. 嵌套查询 - 用户及其文章
```graphql
query GetUserWithPosts {
  getUser(id: "1") {
    id
    name
    posts {
      id
      title
      createdAt
    }
  }
}
```

## 3. 深度嵌套查询 - 用户->文章->评论->作者
```graphql
query GetDeepNested {
  getUser(id: "1") {
    id
    name
    posts {
      id
      title
      comments {
        id
        content
        author {
          id
          name
        }
      }
    }
  }
}
```

## 4. 获取所有文章及评论
```graphql
query GetPostsWithComments {
  getPosts(limit: 10) {
    id
    title
    author {
      id
      name
    }
    comments {
      id
      content
      author {
        name
      }
    }
  }
}
```

## 5. 创建用户 (Mutation)
```graphql
mutation CreateUser {
  createUser(name: "赵六", email: "zhaoliu@example.com") {
    id
    name
    email
  }
}
```

## 6. 创建文章
```graphql
mutation CreatePost {
  createPost(
    title: "GraphQL缓存策略"
    content: "深入探讨GraphQL字段级缓存实现..."
    authorId: "1"
  ) {
    id
    title
    createdAt
  }
}
```

## 7. 创建评论
```graphql
mutation CreateComment {
  createComment(
    content: "这篇文章太实用了！"
    authorId: "2"
    postId: "1"
  ) {
    id
    content
    createdAt
  }
}
```

## 功能说明

### 🔹 多数据源聚合
- UserAPI: 用户数据
- PostAPI: 文章数据
- CommentAPI: 评论数据

### 🔹 字段级缓存
- 使用 LRU Cache 缓存字段结果
- 自动缓存命中/未命中日志输出
- Mutation 后自动失效相关缓存

### 🔹 查询复杂度分析
- @cost 指令定义字段复杂度
- 支持 multipliers 参数乘法计算
- 超过最大复杂度限制时拒绝查询

### 🔹 嵌套查询支持
- 支持任意深度的嵌套解析
- 自动处理关联数据加载
