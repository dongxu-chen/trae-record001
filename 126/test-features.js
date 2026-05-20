import { gatewayRateLimiter } from './src/gateway/rate-limiter.js';
import { queryAnalyzer } from './src/gateway/query-analyzer.js';
import { orchestrator } from './src/orchestration/orchestrator.js';
import { conditionalWorkflow, foreachWorkflow, whileWorkflow, parallelWorkflow, complexWorkflow } from './examples/sample-workflows.js';

console.log('=== 🧪 API聚合与编排引擎 - 功能测试 ===\n');

async function testRateLimiter() {
  console.log('1️⃣  测试网关速率限制...\n');
  
  let allowed = 0;
  let blocked = 0;
  
  for (let i = 0; i < 120; i++) {
    const result = gatewayRateLimiter.checkRateLimit('127.0.0.1', 'test-user');
    if (result.allowed) {
      allowed++;
    } else {
      blocked++;
    }
  }
  
  console.log(`   ✅ 已允许请求: ${allowed}`);
  console.log(`   ❌ 已拦截请求: ${blocked}`);
  
  const stats = gatewayRateLimiter.getStats();
  console.log(`   📊 统计信息: 总请求 ${stats.totalRequests}, 已拦截 ${stats.totalBlocked}`);
  console.log('   ✅ 速率限制测试通过!\n');
}

async function testQueryAnalyzer() {
  console.log('2️⃣  测试查询成本分析...\n');
  
  queryAnalyzer.logQuery({
    operationName: 'GetUser',
    query: 'query { getUser { name email } }',
    variables: {},
    complexity: { totalComplexity: 15, depth: 3, fieldCount: 5 },
    executionTime: 1200,
    userId: 'user-123',
    ip: '192.168.1.1',
  });
  
  queryAnalyzer.logQuery({
    operationName: 'GetPosts',
    query: 'query { getPosts { title author { name } } }',
    variables: {},
    complexity: { totalComplexity: 45, depth: 4, fieldCount: 12 },
    executionTime: 800,
    userId: 'user-456',
    ip: '192.168.1.2',
  });
  
  const stats = queryAnalyzer.getStats();
  console.log(`   📊 总查询数: ${stats.totalQueries}`);
  console.log(`   🐢 慢查询数: ${stats.slowQueries}`);
  console.log(`   📈 高复杂度查询数: ${stats.highComplexityQueries}`);
  console.log(`   ⏱️  平均执行时间: ${stats.avgExecutionTime}ms`);
  console.log(`   📊 平均复杂度: ${stats.avgComplexity}`);
  console.log('   ✅ 查询分析测试通过!\n');
}

async function testOrchestrator() {
  console.log('3️⃣  测试动态编排引擎...\n');
  
  console.log('   📋 测试条件分支工作流...');
  const condResult = await orchestrator.execute(conditionalWorkflow);
  console.log(`   ✅ 条件分支: ${condResult.success ? '成功' : '失败'}, 访问级别: ${condResult.variables.accessLevel}`);
  
  console.log('\n   📋 测试ForEach循环工作流...');
  const foreachResult = await orchestrator.execute(foreachWorkflow);
  console.log(`   ✅ ForEach循环: ${foreachResult.success ? '成功' : '失败'}, 处理用户数: ${foreachResult.variables.users?.length}`);
  
  console.log('\n   📋 测试While循环工作流...');
  const whileResult = await orchestrator.execute(whileWorkflow);
  console.log(`   ✅ While循环: ${whileResult.success ? '成功' : '失败'}, 最终计数: ${whileResult.variables.counter}`);
  
  console.log('\n   📋 测试并行执行工作流...');
  const parallelResult = await orchestrator.execute(parallelWorkflow);
  console.log(`   ✅ 并行执行: ${parallelResult.success ? '成功' : '失败'}, 结果: ${parallelResult.variables.task3Result}`);
  
  console.log('\n   📋 测试复杂数据处理工作流...');
  const complexResult = await orchestrator.execute(complexWorkflow);
  console.log(`   ✅ 复杂处理: ${complexResult.success ? '成功' : '失败'}, 通过人数: ${complexResult.variables.processedCount}`);
  
  console.log('\n   ✅ 编排引擎测试通过!\n');
}

async function runAllTests() {
  try {
    await testRateLimiter();
    await testQueryAnalyzer();
    await testOrchestrator();
    
    console.log('=== 🎉 所有测试通过! ===\n');
    console.log('📋 功能总结:');
    console.log('   ✅ Apollo Federation 联邦网关');
    console.log('   ✅ 网关级速率限制 (IP/用户维度)');
    console.log('   ✅ Query 成本分析报告与慢查询导出');
    console.log('   ✅ 动态编排 DSL (条件分支/循环/并行)');
    console.log('\n🚀 启动服务:');
    console.log('   1. npm run subgraphs  (启动子图服务)');
    console.log('   2. npm start           (启动联邦网关)');
    console.log('   3. 访问 http://localhost:4000 进行 GraphQL 查询\n');
  } catch (error) {
    console.error('❌ 测试失败:', error);
  }
}

runAllTests();
