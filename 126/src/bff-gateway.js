import { ApolloServer } from '@apollo/server';
import { startStandaloneServer } from '@apollo/server/standalone';
import DataLoader from 'dataloader';
import GrpcClientFactory from './bff/grpc-client-factory.js';
import { typeDefs } from './bff/graphql-schema.js';
import { createResolvers } from './bff/graphql-resolvers.js';

class BffGateway {
  constructor(options = {}) {
    this.port = options.port || 4000;
    this.grpcClientFactory = new GrpcClientFactory(options.grpcAddresses);
    this.orchestrator = options.orchestrator || null;
    this.server = null;
  }

  async start() {
    console.log('🚀 Starting BFF Gateway...\n');

    const resolvers = createResolvers(this.grpcClientFactory, this.orchestrator);

    this.server = new ApolloServer({
      typeDefs,
      resolvers,
      introspection: true,
    });

    const { url } = await startStandaloneServer(this.server, {
      listen: { port: this.port },
      context: async ({ req }) => {
        const loaders = this.createLoaders();
        const grpcClients = {
          user: this.grpcClientFactory.getUserClient(),
          post: this.grpcClientFactory.getPostClient(),
          comment: this.grpcClientFactory.getCommentClient(),
        };

        return {
          loaders,
          grpcClients,
          req,
        };
      },
    });

    console.log('✅ BFF Gateway started successfully!');
    console.log(`📡 GraphQL endpoint: ${url}`);
    console.log('\n📋 Connected gRPC services:');
    console.log('   - User Service:    ' + this.grpcClientFactory.addresses.user);
    console.log('   - Post Service:    ' + this.grpcClientFactory.addresses.post);
    console.log('   - Comment Service: ' + this.grpcClientFactory.addresses.comment);

    return url;
  }

  createLoaders() {
    const userClient = this.grpcClientFactory.getUserClient();
    const postClient = this.grpcClientFactory.getPostClient();
    const commentClient = this.grpcClientFactory.getCommentClient();

    return {
      userLoader: new DataLoader(async (userIds) => {
        const { users } = await userClient.GetUsers({ ids: userIds });
        const userMap = new Map(users.map(u => [u.id, u]));
        return userIds.map(id => userMap.get(id) || null);
      }),

      postLoader: new DataLoader(async (postIds) => {
        const { posts } = await postClient.GetPosts({ ids: postIds });
        const postMap = new Map(posts.map(p => [p.id, p]));
        return postIds.map(id => postMap.get(id) || null);
      }),

      commentLoader: new DataLoader(async (commentIds) => {
        const { comments } = await commentClient.GetComments({ ids: commentIds });
        const commentMap = new Map(comments.map(c => [c.id, c]));
        return commentIds.map(id => commentMap.get(id) || null);
      }),

      postsByAuthorLoader: new DataLoader(async (authorIds) => {
        const results = await Promise.all(
          authorIds.map(id => postClient.GetPostsByAuthor({ authorId: id }))
        );
        return results.map(r => r.posts);
      }),

      commentsByPostLoader: new DataLoader(async (postIds) => {
        const results = await Promise.all(
          postIds.map(id => commentClient.GetCommentsByPost({ postId: id }))
        );
        return results.map(r => r.comments);
      }),
    };
  }

  async stop() {
    if (this.server) {
      await this.server.stop();
      console.log('✅ BFF Gateway stopped');
    }
  }
}

export default BffGateway;

async function main() {
  const gateway = new BffGateway();
  await gateway.start();
}

if (import.meta.url === `file:///${process.argv[1]}`.replace(/\\/g, '/')) {
  main().catch((err) => {
    console.error('❌ Failed to start BFF Gateway:', err);
    process.exit(1);
  });
}
