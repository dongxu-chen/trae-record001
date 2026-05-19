import startUserSubgraph from './subgraphs/user-subgraph.js';
import startPostSubgraph from './subgraphs/post-subgraph.js';
import startCommentSubgraph from './subgraphs/comment-subgraph.js';

async function startAllSubgraphs() {
  console.log('🚀 Starting all subgraphs...\n');
  
  await Promise.all([
    startUserSubgraph(4001),
    startPostSubgraph(4002),
    startCommentSubgraph(4003),
  ]);
  
  console.log('\n✅ All subgraphs are running!');
  console.log('📋 Subgraph URLs:');
  console.log('   - User:    http://localhost:4001');
  console.log('   - Post:    http://localhost:4002');
  console.log('   - Comment: http://localhost:4003');
}

startAllSubgraphs().catch(console.error);
