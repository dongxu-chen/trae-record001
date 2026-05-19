import { loadProto, createService, startServer } from '../grpc-utils.js';
import { commentDB } from '../mock-db.js';

const commentProto = loadProto('comment.proto');

const commentServiceHandlers = {
  GetComment: (call, callback) => {
    const { id } = call.request;
    const comment = commentDB.get(id);
    if (!comment) {
      callback({ code: 5, message: `Comment ${id} not found` });
      return;
    }
    callback(null, comment);
  },

  GetComments: (call, callback) => {
    const { ids } = call.request;
    const comments = commentDB.getMany(ids);
    callback(null, { comments });
  },

  GetCommentsByPost: (call, callback) => {
    const { postId } = call.request;
    const comments = commentDB.getByPost(postId);
    callback(null, { comments });
  },

  ListComments: (call, callback) => {
    const { limit = 10, offset = 0 } = call.request;
    const result = commentDB.list(limit, offset);
    callback(null, result);
  },

  CreateComment: (call, callback) => {
    const { content, postId, authorId } = call.request;
    const comment = commentDB.create({ content, postId, authorId });
    callback(null, comment);
  },

  UpdateComment: (call, callback) => {
    const { id, content } = call.request;
    const data = {};
    if (content !== undefined) data.content = content;
    const comment = commentDB.update(id, data);
    if (!comment) {
      callback({ code: 5, message: `Comment ${id} not found` });
      return;
    }
    callback(null, comment);
  },

  DeleteComment: (call, callback) => {
    const { id } = call.request;
    const success = commentDB.delete(id);
    callback(null, {
      success,
      message: success ? `Comment ${id} deleted` : `Comment ${id} not found`,
    });
  },
};

export async function startCommentService(port = 50053) {
  const commentService = createService(commentProto.comment, 'CommentService', commentServiceHandlers);
  const { port: actualPort } = await startServer(port, [commentService]);
  console.log(`✅ Comment gRPC Service started on port ${actualPort}`);
  return actualPort;
}

export default startCommentService;
