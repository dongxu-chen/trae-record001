import { ApolloServer } from '@apollo/server';
import { startStandaloneServer } from '@apollo/server/standalone';
import { ApolloGateway, IntrospectAndCompose } from '@apollo/gateway';
import { gatewayRateLimiter } from './gateway/rate-limiter.js';
import { queryAnalyzer } from './gateway/query-analyzer.js';
import { orchestrator } from './orchestration/orchestrator.js';
import UserAPI from './datasources/UserAPI.js';
import PostAPI from './datasources/PostAPI.js';
import CommentAPI from './datasources/CommentAPI.js';

const GATEWAY_PORT = process.env.GATEWAY_PORT || 4000;
const SUBGRAPH_URLS = {
  user: process.env.USER_SUBGRAPH_URL || 'http://localhost:4001',
  post: process.env.POST_SUBGRAPH_URL || 'http://localhost:4002',
  comment: process.env.COMMENT_SUBGRAPH_URL || 'http://localhost:4003',
};

async function createGateway() {
  const supergraphSdl = new IntrospectAndCompose({
    subgraphs: Object.entries(SUBGRAPH_URLS).map(([name, url]) => ({ name, url })),
  });

  const gateway = new ApolloGateway({
    supergraphSdl,
  });

  const server = new ApolloServer({
    gateway,
    plugins: [
      {
        async requestDidStart(requestContext) {
          const { request, contextValue } = requestContext;
          
          const analysis = queryAnalyzer.analyzeQuery(
            {
              query: request.query,
              operationName: request.operationName,
              variables: request.variables,
              userId: contextValue?.userId,
              ip: contextValue?.ip,
              userAgent: contextValue?.userAgent,
            },
            requestContext.document,
            request.variables
          );

          return {
            async willSendResponse(requestContext) {
              const { response } = requestContext;
              const completedAnalysis = queryAnalyzer.completeQuery(analysis, response);
              
              contextValue.analysis = completedAnalysis;
            },
          };
        },
      },
      {
        async serverWillStart() {
          console.log('🚀 Federation Gateway starting...');
          console.log('📋 Subgraphs:', SUBGRAPH_URLS);
          return {
            async serverWillStop() {
              console.log('🛑 Gateway stopping...');
              await queryAnalyzer.saveLogsToFile();
            },
          };
        },
      },
    ],
    introspection: true,
  });

  const { url } = await startStandaloneServer(server, {
    listen: { port: GATEWAY_PORT },
    context: async ({ req }) => {
      const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
      const userAgent = req.headers['user-agent'];
      const userId = req.headers['x-user-id'];

      const rateLimitResult = gatewayRateLimiter.checkRateLimit(ip, userId);
      
      if (!rateLimitResult.allowed) {
        throw new Error(`Rate limit exceeded: ${rateLimitResult.reason}`);
      }

      const userAPI = new UserAPI();
      const postAPI = new PostAPI();
      const commentAPI = new CommentAPI();

      orchestrator.registerDataSource('user', userAPI);
      orchestrator.registerDataSource('post', postAPI);
      orchestrator.registerDataSource('comment', commentAPI);

      return {
        ip,
        userId,
        userAgent,
        rateLimit: rateLimitResult,
        dataSources: {
          userAPI,
          postAPI,
          commentAPI,
        },
        orchestrator,
      };
    },
  });

  console.log(`\n✅ Federation Gateway ready at ${url}`);
  console.log(`\n🛡️  Rate Limiting:`);
  console.log(`   IP Limit: ${gatewayRateLimiter.getLimits().ip.max} requests/${gatewayRateLimiter.getLimits().ip.windowMs / 1000}s`);
  console.log(`   User Limit: ${gatewayRateLimiter.getLimits().user.max} requests/${gatewayRateLimiter.getLimits().user.windowMs / 1000}s`);
  console.log(`   Global Limit: ${gatewayRateLimiter.getLimits().global.max} requests/${gatewayRateLimiter.getLimits().global.windowMs / 1000}s`);

  console.log(`\n📊 Query Analysis:`);
  console.log(`   Slow Query Threshold: 1000ms`);
  console.log(`   Complexity Threshold: 100`);

  console.log(`\n🎯 Orchestration DSL:`);
  console.log(`   - Conditional steps (if/else)`);
  console.log(`   - Loop constructs (foreach, while)`);
  console.log(`   - Parallel execution`);
  console.log(`   - Try/Catch/Finally`);
  console.log(`   - Expression evaluation\n`);

  return { server, url };
}

process.on('SIGTERM', async () => {
  console.log('Received SIGTERM, saving query logs...');
  await queryAnalyzer.saveLogsToFile();
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('Received SIGINT, saving query logs...');
  await queryAnalyzer.saveLogsToFile();
  process.exit(0);
});

if (import.meta.url === `file://${process.argv[1]}`) {
  createGateway().catch(console.error);
}

export { createGateway, gatewayRateLimiter, queryAnalyzer, orchestrator };
