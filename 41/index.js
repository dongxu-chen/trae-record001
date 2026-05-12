const { ApolloServer } = require('apollo-server-express');
const { createServer } = require('http');
const { WebSocketServer } = require('ws');
const { useServer } = require('graphql-ws/lib/use/ws');
const { makeExecutableSchema } = require('@graphql-tools/schema');
const express = require('express');
const fs = require('fs');
const path = require('path');
const { connectDB, closeDB } = require('./db/mongo');
const { closePubSub } = require('./pubsub');
const { apiLimiter, subscriptionLimiter } = require('./rate_limit');
const booksResolver = require('./resolvers/books');
const usersResolver = require('./resolvers/users');

const typeDefs = fs.readFileSync(path.join(__dirname, 'schema.graphql'), 'utf8');

const dateTimeResolver = {
  DateTime: {
    parseValue(value) {
      return new Date(value);
    },
    serialize(value) {
      if (value instanceof Date) {
        return value.toISOString();
      }
      return value;
    },
    parseLiteral(ast) {
      if (ast.kind === 'StringValue') {
        return new Date(ast.value);
      }
      return null;
    }
  }
};

function mergeResolvers(...resolvers) {
  const merged = {
    Query: {},
    Mutation: {},
    Subscription: {}
  };

  for (const resolver of resolvers) {
    for (const [key, value] of Object.entries(resolver)) {
      if (key === 'Query' || key === 'Mutation' || key === 'Subscription') {
        merged[key] = { ...merged[key], ...value };
      } else {
        merged[key] = value;
      }
    }
  }

  return merged;
}

const resolvers = mergeResolvers(dateTimeResolver, booksResolver, usersResolver);

async function startServer() {
  await connectDB();

  const app = express();
  app.use(apiLimiter);

  const schema = makeExecutableSchema({ typeDefs, resolvers });

  const server = new ApolloServer({
    schema,
    context: ({ req }) => ({ req })
  });

  await server.start();
  server.applyMiddleware({ app, path: '/graphql' });

  const httpServer = createServer(app);

  const wsServer = new WebSocketServer({
    server: httpServer,
    path: '/graphql'
  });

  const serverCleanup = useServer(
    {
      schema,
      onConnect: () => {
        console.log('Client connected to subscription');
      },
      onDisconnect: () => {
        console.log('Client disconnected from subscription');
      }
    },
    wsServer
  );

  const PORT = process.env.PORT || 4000;

  httpServer.listen(PORT, () => {
    console.log(`GraphQL server running at http://localhost:${PORT}/graphql`);
    console.log(`WebSocket subscriptions available at ws://localhost:${PORT}/graphql`);
  });

  const shutdown = async () => {
    console.log('\nShutting down gracefully...');
    await serverCleanup.dispose();
    wsServer.close();
    await server.stop();
    await closeDB();
    await closePubSub();
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

startServer();
