import grpc from '@grpc/grpc-js';
import protoLoader from '@grpc/proto-loader';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROTO_DIR = path.join(__dirname, '../../protos');

const protoOptions = {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
};

export function loadProto(protoFile) {
  const packageDefinition = protoLoader.loadSync(
    path.join(PROTO_DIR, protoFile),
    protoOptions
  );
  return grpc.loadPackageDefinition(packageDefinition);
}

export function createService(packageDef, serviceName, handlers) {
  const ServiceConstructor = packageDef[serviceName].service;
  return {
    service: ServiceConstructor,
    handlers,
  };
}

export function startServer(port, services) {
  const server = new grpc.Server();
  
  services.forEach(({ service, handlers }) => {
    server.addService(service, handlers);
  });
  
  return new Promise((resolve, reject) => {
    server.bindAsync(
      `0.0.0.0:${port}`,
      grpc.ServerCredentials.createInsecure(),
      (err, port) => {
        if (err) {
          reject(err);
          return;
        }
        server.start();
        resolve({ server, port });
      }
    );
  });
}

export function createClient(packageDef, serviceName, address) {
  const Client = packageDef[serviceName];
  return new Client(
    address,
    grpc.credentials.createInsecure()
  );
}

export function promisifyClient(client) {
  const promisified = {};
  
  for (const methodName of Object.keys(client.constructor.service)) {
    const originalMethod = client[methodName].bind(client);
    promisified[methodName] = (request) => {
      return new Promise((resolve, reject) => {
        originalMethod(request, (error, response) => {
          if (error) {
            reject(error);
          } else {
            resolve(response);
          }
        });
      });
    };
  }
  
  return promisified;
}

export default {
  loadProto,
  createService,
  startServer,
  createClient,
  promisifyClient,
};
