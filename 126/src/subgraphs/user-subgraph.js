import { ApolloServer } from '@apollo/server';
import { startStandaloneServer } from '@apollo/server/standalone';
import { buildSubgraphSchema } from '@apollo/subgraph';
import gql from 'graphql-tag';

const typeDefs = gql`
  extend schema
    @link(url: "https://specs.apollo.dev/federation/v2.0",
          import: ["@key", "@shareable"])

  type User @key(fields: "id") {
    id: ID!
    name: String!
    email: String!
    role: String!
    createdAt: String!
  }

  type Query {
    getUser(id: ID!): User
    getUsers: [User!]!
    searchUsers(query: String!): [User!]!
  }

  type Mutation {
    createUser(name: String!, email: String!, role: String = "USER"): User!
    updateUser(id: ID!, name: String, email: String, role: String): User
    deleteUser(id: ID!): Boolean!
  }
`;

const users = [
  { id: '1', name: '张三', email: 'zhangsan@example.com', role: 'ADMIN', createdAt: '2024-01-01' },
  { id: '2', name: '李四', email: 'lisi@example.com', role: 'USER', createdAt: '2024-01-02' },
  { id: '3', name: '王五', email: 'wangwu@example.com', role: 'USER', createdAt: '2024-01-03' },
];

const resolvers = {
  Query: {
    getUser: (_, { id }) => users.find(u => u.id === id),
    getUsers: () => users,
    searchUsers: (_, { query }) => users.filter(u => 
      u.name.includes(query) || u.email.includes(query)
    ),
  },
  Mutation: {
    createUser: (_, { name, email, role }) => {
      const newUser = {
        id: String(users.length + 1),
        name,
        email,
        role,
        createdAt: new Date().toISOString().split('T')[0],
      };
      users.push(newUser);
      return newUser;
    },
    updateUser: (_, { id, name, email, role }) => {
      const index = users.findIndex(u => u.id === id);
      if (index === -1) return null;
      if (name) users[index].name = name;
      if (email) users[index].email = email;
      if (role) users[index].role = role;
      return users[index];
    },
    deleteUser: (_, { id }) => {
      const index = users.findIndex(u => u.id === id);
      if (index === -1) return false;
      users.splice(index, 1);
      return true;
    },
  },
  User: {
    __resolveReference: (reference) => {
      return users.find(u => u.id === reference.id);
    },
  },
};

async function startUserSubgraph(port = 4001) {
  const server = new ApolloServer({
    schema: buildSubgraphSchema({ typeDefs, resolvers }),
  });

  const { url } = await startStandaloneServer(server, {
    listen: { port },
  });

  console.log(`👤 User Subgraph ready at ${url}`);
  return { server, url };
}

export default startUserSubgraph;
