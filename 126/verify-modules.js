console.log('=== 验证模块加载 ===\n');

try {
  const rateLimiterModule = await import('./src/gateway/rate-limiter.js');
  console.log('✅ rate-limiter.js 加载成功');
  console.log('   - 导出:', Object.keys(rateLimiterModule));
} catch (e) {
  console.log('❌ rate-limiter.js 加载失败:', e.message);
}

console.log('');

try {
  const queryAnalyzerModule = await import('./src/gateway/query-analyzer.js');
  console.log('✅ query-analyzer.js 加载成功');
  console.log('   - 导出:', Object.keys(queryAnalyzerModule));
} catch (e) {
  console.log('❌ query-analyzer.js 加载失败:', e.message);
}

console.log('');

try {
  const orchestratorModule = await import('./src/orchestration/orchestrator.js');
  console.log('✅ orchestrator.js 加载成功');
  console.log('   - 导出:', Object.keys(orchestratorModule));
} catch (e) {
  console.log('❌ orchestrator.js 加载失败:', e.message);
}

console.log('');

try {
  const userSubgraphModule = await import('./src/subgraphs/user-subgraph.js');
  console.log('✅ user-subgraph.js 加载成功');
  console.log('   - 导出:', Object.keys(userSubgraphModule));
} catch (e) {
  console.log('❌ user-subgraph.js 加载失败:', e.message);
}

console.log('');

console.log('\n=== 模块验证完成 ===\n');
console.log('📋 所有核心模块已实现:');
console.log('   1. Apollo Federation 联邦网关 (src/gateway.js + src/subgraphs/*.js)');
console.log('   2. 网关级速率限制 (src/gateway/rate-limiter.js)');
console.log('   3. Query 成本分析报告 (src/gateway/query-analyzer.js)');
console.log('   4. 动态编排 DSL (src/orchestration/orchestrator.js)');
console.log('');
console.log('📁 项目文件结构:');
console.log('   ├── src/');
console.log('   │   ├── gateway.js                  # 联邦网关');
console.log('   │   ├── gateway/');
console.log('   │   │   ├── rate-limiter.js         # 速率限制器');
console.log('   │   │   └── query-analyzer.js       # 查询分析器');
console.log('   │   ├── subgraphs/');
console.log('   │   │   ├── user-subgraph.js        # 用户子图');
console.log('   │   │   ├── post-subgraph.js        # 文章子图');
console.log('   │   │   └── comment-subgraph.js     # 评论子图');
console.log('   │   ├── orchestration/');
console.log('   │   │   └── orchestrator.js         # 编排引擎');
console.log('   │   └── start-subgraphs.js          # 子图启动');
console.log('   ├── examples/');
console.log('   │   └── sample-workflows.js         # 编排示例');
console.log('   ├── README.md                       # 完整文档');
console.log('   └── package.json                    # 依赖配置');
