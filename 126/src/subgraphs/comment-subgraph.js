import { ApolloServer } from '@apollo/server';
import { startStandaloneServer } from '@apollo/server/standalone';
import { buildSubgraphSchema } from '@apollo/subgraph';
import gql from 'graphql-tag';

const typeDefs = gql`
  extend schema
    @link(url: "https://specs.apollo.dev/federation/v2.0",
          import: ["@key", "@shareable", "@external"])

  type Comment @key(fields: "id") {
    id: ID!
    content: String!
    authorId: ID!
    postId: ID!
    author: User
    post: Post
    likes: Int!
    createdAt: String!
  }

  type User @key(fields: "id") {
    id: ID! @external
    comments: [Comment!]!
  }

  type Post @key(fields: "id") {
    id: ID! @external
    comments: [Comment!]!
    commentCount: Int!
  }

  type Query {
    getComment(id: ID!): Comment
    getComments(limit: Int = 10): [Comment!]!
    getCommentsByAuthor(authorId: ID!): [Comment!]!
    getCommentsByPost(postId: ID!): [Comment!]!
  }

  type Mutation {
    createComment(content: String!, authorId: ID!, postId: ID!): Comment!
    updateComment(id: ID!, content: String!): Comment
    deleteComment(id: ID!): Boolean!
    likeComment(id: ID!): Comment!
  }
`;

const comments = [
  { id: '1', content: '非常棒的教程！', authorId: '2', postId: '1', likes: 15, createdAt: '2024-01-01' },
  { id: '2', content: '学到了很多，感谢分享', authorId: '3', postId: '1', likes: 8, createdAt: '2024-01-02' },
  { id: '3', content: '写得很详细', authorId: '1', postId: '2', likes: 12, createdAt: '2024-01-03' },
  { id: '4', content: '期待更多内容', authorId: '3', postId: '2', likes: 5, createdAt: '2024-01-04' },
];

const resolvers = {
  Query: {
    getComment: (_, { id }) => comments.find(c => c.id === id),
    getComments: (_, { limit }) => comments.slice(0, limit),
    getCommentsByAuthor: (_, { authorId }) => comments.filter(c => c.authorId === authorId),
    getCommentsByPost: (_, { postId }) => comments.filter(c => c.postId === postId),
  },
  Mutation: {
    createComment: (_, { content, authorId, postId }) => {
      const newComment = {
        id: String(comments.length + 1),
        content,
        authorId,
        postId,
        likes: 0,
        createdAt: new Date().toISOString().split('T')[0],
      };
      comments.push(newComment);
      return newComment;
    },
    updateComment: (_, { id, content }) => {
      const index = comments.findIndex(c => c.id === id);
      if (index === -1) return null;
      comments[index].content = content;
      return comments[index];
    },
    deleteComment: (_, { id }) => {
      const index = comments.findIndex(c => c.id === id);
      if (index === -1) return false;
      comments.splice(index, 1);
      return true;
    },
    likeComment: (_, { id }) => {
      const comment = comments.find(c => c.id === id);
      if (!comment) return null;
      comment.likes++;
      return comment;
    },
  },
  Comment: {
    __resolveReference: (reference) => {
      return comments.find(c => c.id === reference.id);
    },
  },
  User: {
    comments: (user) => comments.filter(c => c.authorId === user.id),
  },
  Post: {
    comments: (post) => comments.filter(c => c.postId === post.id),
    commentCount: (post) => comments.filter(c => c.postId === post.id).length,
  },
};

async function startCommentSubgraph(port = 4003) {
  const server = new ApolloServer({
    schema: buildSubgraphSchema({ typeDefs, resolvers }),
  });

  const { url } = await startStandaloneServer(server, {
    listen: { port },
  });

  console.log(`💬 Comment Subgraph ready at ${url}`);
  return { server, url };
}

export default startCommentSubgraph;
