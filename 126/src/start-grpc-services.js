import { startUserService } from './grpc/services/user-service.js';
import { startPostService } from './grpc/services/post-service.js';
import { startCommentService } from './grpc/services/comment-service.js';

async function startAllServices() {
  console.log('🚀 Starting gRPC Microservices...\n');
  
  try {
    await Promise.all([
      startUserService(50051),
      startPostService(50052),
      startCommentService(50053),
    ]);
    
    console.log('\n✅ All gRPC services started successfully!');
    console.log('📋 Service Ports:');
    console.log('   - User Service:    50051');
    console.log('   - Post Service:    50052');
    console.log('   - Comment Service: 50053');
  } catch (error) {
    console.error('❌ Failed to start gRPC services:', error);
    process.exit(1);
  }
}

startAllServices();
