import { ApolloServer } from '@apollo/server';
import { startStandaloneServer } from '@apollo/server/standalone';
import { typeDefs } from './schema.js';
import { resolvers } from './resolvers.js';
import UserAPI from './datasources/UserAPI.js';
import PostAPI from './datasources/PostAPI.js';
import CommentAPI from './datasources/CommentAPI.js';
import UserLoader from './dataloaders/UserLoader.js';
import PostLoader from './dataloaders/PostLoader.js';
import CommentLoader from './dataloaders/CommentLoader.js';
import { fieldCache } from './cache/FieldCache.js';
import { complexityAnalysis } from './utils/complexityAnalysis.js';
import { globalRateLimiter } from './utils/TokenBucket.js';

const server = new ApolloServer({
  typeDefs,
  resolvers,
  plugins: [
    complexityAnalysis.createPlugin(),
    {
      async requestDidStart() {
        return {
          async willSendResponse() {
            const stats = globalRateLimiter.getStats();
            console.log(`[RateLimit] Tokens: ${stats.availableTokens.toFixed(2)}/${stats.capacity}, Queue: ${stats.waitingQueueSize}`);
          },
        };
      },
    },
    {
      async serverWillStart() {
        console.log('🚀 Apollo Server starting...');
      },
    },
  ],
  introspection: true,
});

async function startServer() {
  const { url } = await startStandaloneServer(server, {
    listen: { port: 4000 },
    context: async () => {
      const userAPI = new UserAPI(globalRateLimiter);
      const postAPI = new PostAPI(globalRateLimiter);
      const commentAPI = new CommentAPI(globalRateLimiter);

      return {
        dataSources: {
          userAPI,
          postAPI,
          commentAPI,
        },
        dataLoaders: {
          userLoader: new UserLoader(userAPI),
          postLoader: new PostLoader(postAPI),
          commentLoader: new CommentLoader(commentAPI),
        },
        fieldCache,
        rateLimiter: globalRateLimiter,
      };
    },
  });

  console.log(`\n✨ API聚合与编排引擎已启动`);
  console.log(`📡 GraphQL Playground: ${url}`);
  console.log(`\n📋 功能特性:`);
  console.log(`  ✅ 多数据源聚合 (UserAPI, PostAPI, CommentAPI)`);
  console.log(`  ✅ DataLoader批量加载 - 解决N+1查询问题`);
  console.log(`  ✅ 字段级缓存 (LRU Cache + TTL)`);
  console.log(`  ✅ 支持按需刷新缓存 (_refresh, _ttl参数)`);
  console.log(`  ✅ 查询复杂度分析 (深度+广度因子)`);
  console.log(`  ✅ 令牌桶限流 (10请求/秒)`);
  console.log(`  ✅ 嵌套查询支持\n`);
}

startServer().catch(console.error);
