import grpc from '@grpc/grpc-js';
import protoLoader from '@grpc/proto-loader';
import path from 'path';
import { fileURLToPath } from 'url';
import ConsulClient from '../discovery/consul-client.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROTO_DIR = path.join(__dirname, '../../protos');

class GrpcServer {
  constructor(options = {}) {
    this.server = new grpc.Server();
    this.port = options.port || 50051;
    this.serviceName = options.serviceName;
    this.consul = options.enableConsul ? new ConsulClient(options.consul) : null;
    this.registered = false;
  }

  loadProto(protoFile) {
    const packageDefinition = protoLoader.loadSync(
      path.join(PROTO_DIR, protoFile),
      {
        keepCase: true,
        longs: String,
        enums: String,
        defaults: true,
        oneofs: true,
      }
    );
    return grpc.loadPackageDefinition(packageDefinition);
  }

  addService(service, handlers) {
    this.server.addService(service, handlers);
  }

  async start() {
    return new Promise((resolve, reject) => {
      this.server.bindAsync(
        `0.0.0.0:${this.port}`,
        grpc.ServerCredentials.createInsecure(),
        async (err, port) => {
          if (err) {
            reject(err);
            return;
          }

          this.port = port;
          this.server.start();

          if (this.consul && this.serviceName) {
            await this.registerWithConsul();
          }

          console.log(`✅ gRPC Server started on port ${port}`);
          resolve(port);
        }
      );
    });
  }

  async registerWithConsul() {
    if (!this.consul) return;

    const serviceDef = {
      name: this.serviceName,
      id: `${this.serviceName}-${this.port}`,
      address: 'localhost',
      port: this.port,
      tags: ['grpc', this.serviceName],
      meta: {
        protocol: 'grpc',
      },
    };

    this.registered = await this.consul.registerService(serviceDef);
  }

  async stop() {
    if (this.registered && this.consul) {
      await this.consul.deregisterService(`${this.serviceName}-${this.port}`);
    }

    await new Promise((resolve) => {
      this.server.tryShutdown(resolve);
    });

    console.log(`✅ gRPC Server stopped on port ${this.port}`);
  }
}

export default GrpcServer;
