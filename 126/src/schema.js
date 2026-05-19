export const typeDefs = `#graphql
  type User {
    id: ID!
    name: String!
    email: String! @cost(multipliers: ["complexity"], complexity: 2)
    posts: [Post!]! @cost(multipliers: ["complexity"], complexity: 5)
    comments: [Comment!]! @cost(multipliers: ["complexity"], complexity: 3)
  }

  type Post {
    id: ID!
    title: String! @cost(complexity: 1)
    content: String! @cost(complexity: 2)
    author: User @cost(complexity: 3)
    comments: [Comment!]! @cost(multipliers: ["limit"], complexity: 2)
    createdAt: String!
  }

  type Comment {
    id: ID!
    content: String!
    author: User @cost(complexity: 2)
    post: Post
    createdAt: String!
  }

  type Query {
    getUser(id: ID!): User
    getUsers: [User!]!
    getPost(id: ID!): Post
    getPosts(limit: Int = 10): [Post!]! @cost(complexity: 1)
    getComment(id: ID!): Comment
    getComments: [Comment!]!
  }

  type Mutation {
    createUser(name: String!, email: String!): User!
    createPost(title: String!, content: String!, authorId: ID!): Post!
    createComment(content: String!, authorId: ID!, postId: ID!): Comment!
  }
`;
