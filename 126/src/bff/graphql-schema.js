export const typeDefs = `#graphql
  type User {
    id: ID!
    name: String!
    email: String!
    role: String!
    createdAt: String!
    posts: [Post!]!
    comments: [Comment!]!
  }

  type Post {
    id: ID!
    title: String!
    content: String!
    authorId: String!
    createdAt: String!
    updatedAt: String!
    author: User
    comments: [Comment!]!
    commentCount: Int!
  }

  type Comment {
    id: ID!
    content: String!
    postId: String!
    authorId: String!
    createdAt: String!
    updatedAt: String!
    author: User
    post: Post
  }

  type Query {
    getUser(id: ID!): User
    getUsers(ids: [ID!]!): [User!]!
    listUsers(limit: Int, offset: Int): UserList!
    
    getPost(id: ID!): Post
    getPosts(ids: [ID!]!): [Post!]!
    getPostsByAuthor(authorId: ID!): [Post!]!
    listPosts(limit: Int, offset: Int): PostList!
    
    getComment(id: ID!): Comment
    getComments(ids: [ID!]!): [Comment!]!
    getCommentsByPost(postId: ID!): [Comment!]!
    listComments(limit: Int, offset: Int): CommentList!
    
    executeWorkflow(name: String!, variables: JSON): WorkflowResult
  }

  type UserList {
    users: [User!]!
    total: Int!
  }

  type PostList {
    posts: [Post!]!
    total: Int!
  }

  type CommentList {
    comments: [Comment!]!
    total: Int!
  }

  scalar JSON

  type WorkflowResult {
    success: Boolean!
    data: JSON
    error: String
    executionTime: Int
  }

  type Mutation {
    createUser(name: String!, email: String!, role: String): User!
    updateUser(id: ID!, name: String, email: String, role: String): User
    deleteUser(id: ID!): DeleteResult!
    
    createPost(title: String!, content: String!, authorId: ID!): Post!
    updatePost(id: ID!, title: String, content: String): Post
    deletePost(id: ID!): DeleteResult!
    
    createComment(content: String!, postId: ID!, authorId: ID!): Comment!
    updateComment(id: ID!, content: String): Comment
    deleteComment(id: ID!): DeleteResult!
  }

  type DeleteResult {
    success: Boolean!
    message: String!
  }
`;

export default typeDefs;
