import { loadProto, createService, startServer } from '../grpc-utils.js';
import { userDB } from '../mock-db.js';

const userProto = loadProto('user.proto');

const userServiceHandlers = {
  GetUser: (call, callback) => {
    const { id } = call.request;
    const user = userDB.get(id);
    if (!user) {
      callback({ code: 5, message: `User ${id} not found` });
      return;
    }
    callback(null, user);
  },

  GetUsers: (call, callback) => {
    const { ids } = call.request;
    const users = userDB.getMany(ids);
    callback(null, { users });
  },

  ListUsers: (call, callback) => {
    const { limit = 10, offset = 0 } = call.request;
    const result = userDB.list(limit, offset);
    callback(null, result);
  },

  CreateUser: (call, callback) => {
    const { name, email, role } = call.request;
    const user = userDB.create({ name, email, role });
    callback(null, user);
  },

  UpdateUser: (call, callback) => {
    const { id, name, email, role } = call.request;
    const data = {};
    if (name !== undefined) data.name = name;
    if (email !== undefined) data.email = email;
    if (role !== undefined) data.role = role;
    const user = userDB.update(id, data);
    if (!user) {
      callback({ code: 5, message: `User ${id} not found` });
      return;
    }
    callback(null, user);
  },

  DeleteUser: (call, callback) => {
    const { id } = call.request;
    const success = userDB.delete(id);
    callback(null, {
      success,
      message: success ? `User ${id} deleted` : `User ${id} not found`,
    });
  },
};

export async function startUserService(port = 50051) {
  const userService = createService(userProto.user, 'UserService', userServiceHandlers);
  const { port: actualPort } = await startServer(port, [userService]);
  console.log(`✅ User gRPC Service started on port ${actualPort}`);
  return actualPort;
}

export default startUserService;
