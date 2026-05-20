import { ApolloServer } from '@apollo/server';
import { startStandaloneServer } from '@apollo/server/standalone';
import { buildSubgraphSchema } from '@apollo/subgraph';
import gql from 'graphql-tag';

const typeDefs = gql`
  extend schema
    @link(url: "https://specs.apollo.dev/federation/v2.0",
          import: ["@key", "@shareable", "@external"])

  type Post @key(fields: "id") {
    id: ID!
    title: String!
    content: String!
    authorId: ID!
    author: User
    category: String!
    tags: [String!]!
    status: String!
    createdAt: String!
    updatedAt: String!
  }

  type User @key(fields: "id") {
    id: ID! @external
    posts: [Post!]!
  }

  type Query {
    getPost(id: ID!): Post
    getPosts(limit: Int = 10, offset: Int = 0, category: String): [Post!]!
    getPostsByAuthor(authorId: ID!): [Post!]!
    searchPosts(query: String!): [Post!]!
  }

  type Mutation {
    createPost(title: String!, content: String!, authorId: ID!, category: String = "GENERAL", tags: [String!] = []): Post!
    updatePost(id: ID!, title: String, content: String, category: String, tags: [String!], status: String): Post
    deletePost(id: ID!): Boolean!
  }
`;

const posts = [
  { id: '1', title: 'GraphQL入门指南', content: 'GraphQL是一种API查询语言...', authorId: '1', category: 'TECH', tags: ['graphql', 'api'], status: 'PUBLISHED', createdAt: '2024-01-01', updatedAt: '2024-01-01' },
  { id: '2', title: 'Apollo Server最佳实践', content: '使用Apollo Server构建高性能API...', authorId: '2', category: 'TECH', tags: ['apollo', 'nodejs'], status: 'PUBLISHED', createdAt: '2024-01-02', updatedAt: '2024-01-02' },
  { id: '3', title: '微服务架构设计', content: '微服务架构的核心原则...', authorId: '1', category: 'ARCHITECTURE', tags: ['microservices', 'design'], status: 'PUBLISHED', createdAt: '2024-01-03', updatedAt: '2024-01-03' },
  { id: '4', title: 'Node.js性能优化', content: 'Node.js应用性能优化技巧...', authorId: '3', category: 'TECH', tags: ['nodejs', 'performance'], status: 'DRAFT', createdAt: '2024-01-04', updatedAt: '2024-01-04' },
];

const resolvers = {
  Query: {
    getPost: (_, { id }) => posts.find(p => p.id === id),
    getPosts: (_, { limit, offset, category }) => {
      let result = posts;
      if (category) {
        result = result.filter(p => p.category === category);
      }
      return result.slice(offset, offset + limit);
    },
    getPostsByAuthor: (_, { authorId }) => posts.filter(p => p.authorId === authorId),
    searchPosts: (_, { query }) => posts.filter(p => 
      p.title.includes(query) || p.content.includes(query)
    ),
  },
  Mutation: {
    createPost: (_, { title, content, authorId, category, tags }) => {
      const newPost = {
        id: String(posts.length + 1),
        title,
        content,
        authorId,
        category,
        tags,
        status: 'DRAFT',
        createdAt: new Date().toISOString().split('T')[0],
        updatedAt: new Date().toISOString().split('T')[0],
      };
      posts.push(newPost);
      return newPost;
    },
    updatePost: (_, { id, title, content, category, tags, status }) => {
      const index = posts.findIndex(p => p.id === id);
      if (index === -1) return null;
      if (title) posts[index].title = title;
      if (content) posts[index].content = content;
      if (category) posts[index].category = category;
      if (tags) posts[index].tags = tags;
      if (status) posts[index].status = status;
      posts[index].updatedAt = new Date().toISOString().split('T')[0];
      return posts[index];
    },
    deletePost: (_, { id }) => {
      const index = posts.findIndex(p => p.id === id);
      if (index === -1) return false;
      posts.splice(index, 1);
      return true;
    },
  },
  Post: {
    __resolveReference: (reference) => {
      return posts.find(p => p.id === reference.id);
    },
  },
  User: {
    posts: (user) => posts.filter(p => p.authorId === user.id),
  },
};

async function startPostSubgraph(port = 4002) {
  const server = new ApolloServer({
    schema: buildSubgraphSchema({ typeDefs, resolvers }),
  });

  const { url } = await startStandaloneServer(server, {
    listen: { port },
  });

  console.log(`📝 Post Subgraph ready at ${url}`);
  return { server, url };
}

export default startPostSubgraph;
