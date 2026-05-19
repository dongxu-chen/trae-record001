import { loadProto, createClient, promisifyClient } from '../grpc/grpc-utils.js';

const userProto = loadProto('user.proto');
const postProto = loadProto('post.proto');
const commentProto = loadProto('comment.proto');

const defaultServiceAddresses = {
  user: 'localhost:50051',
  post: 'localhost:50052',
  comment: 'localhost:50053',
};

class GrpcClientFactory {
  constructor(serviceAddresses = {}) {
    this.addresses = { ...defaultServiceAddresses, ...serviceAddresses };
    this.clients = {};
  }

  getUserClient() {
    if (!this.clients.user) {
      const client = createClient(userProto.user, 'UserService', this.addresses.user);
      this.clients.user = promisifyClient(client);
    }
    return this.clients.user;
  }

  getPostClient() {
    if (!this.clients.post) {
      const client = createClient(postProto.post, 'PostService', this.addresses.post);
      this.clients.post = promisifyClient(client);
    }
    return this.clients.post;
  }

  getCommentClient() {
    if (!this.clients.comment) {
      const client = createClient(commentProto.comment, 'CommentService', this.addresses.comment);
      this.clients.comment = promisifyClient(client);
    }
    return this.clients.comment;
  }

  setServiceAddress(serviceName, address) {
    this.addresses[serviceName] = address;
    delete this.clients[serviceName];
  }
}

export default GrpcClientFactory;
