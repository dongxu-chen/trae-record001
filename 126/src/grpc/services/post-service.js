import { loadProto, createService, startServer } from '../grpc-utils.js';
import { postDB } from '../mock-db.js';

const postProto = loadProto('post.proto');

const postServiceHandlers = {
  GetPost: (call, callback) => {
    const { id } = call.request;
    const post = postDB.get(id);
    if (!post) {
      callback({ code: 5, message: `Post ${id} not found` });
      return;
    }
    callback(null, post);
  },

  GetPosts: (call, callback) => {
    const { ids } = call.request;
    const posts = postDB.getMany(ids);
    callback(null, { posts });
  },

  GetPostsByAuthor: (call, callback) => {
    const { authorId } = call.request;
    const posts = postDB.getByAuthor(authorId);
    callback(null, { posts });
  },

  ListPosts: (call, callback) => {
    const { limit = 10, offset = 0 } = call.request;
    const result = postDB.list(limit, offset);
    callback(null, result);
  },

  CreatePost: (call, callback) => {
    const { title, content, authorId } = call.request;
    const post = postDB.create({ title, content, authorId });
    callback(null, post);
  },

  UpdatePost: (call, callback) => {
    const { id, title, content } = call.request;
    const data = {};
    if (title !== undefined) data.title = title;
    if (content !== undefined) data.content = content;
    const post = postDB.update(id, data);
    if (!post) {
      callback({ code: 5, message: `Post ${id} not found` });
      return;
    }
    callback(null, post);
  },

  DeletePost: (call, callback) => {
    const { id } = call.request;
    const success = postDB.delete(id);
    callback(null, {
      success,
      message: success ? `Post ${id} deleted` : `Post ${id} not found`,
    });
  },
};

export async function startPostService(port = 50052) {
  const postService = createService(postProto.post, 'PostService', postServiceHandlers);
  const { port: actualPort } = await startServer(port, [postService]);
  console.log(`✅ Post gRPC Service started on port ${actualPort}`);
  return actualPort;
}

export default startPostService;
