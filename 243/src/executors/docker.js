const Docker = require('dockerode');
const fs = require('fs-extra');
const path = require('path');
const { PassThrough } = require('stream');

class DockerExecutor {
  constructor({ logger, config }) {
    this.logger = logger;
    this.config = config;
    this.docker = null;
  }

  async initialize() {
    try {
      this.docker = new Docker({
        socketPath: this.config.docker?.socketPath || '/var/run/docker.sock'
      });
      
      await this.docker.ping();
      this.logger.info('Docker连接成功');
      
      await this.ensureNetwork();
    } catch (err) {
      this.logger.warn('Docker连接失败，将使用本地执行模式', { error: err.message });
      this.docker = null;
    }
  }

  async ensureNetwork() {
    const networkName = this.config.docker?.network || 'cicd-network';
    
    try {
      const networks = await this.docker.listNetworks({ 
        filters: { name: [networkName] } 
      });
      
      if (networks.length === 0) {
        await this.docker.createNetwork({
          Name: networkName,
          Driver: 'bridge'
        });
        this.logger.info('Docker网络创建成功', { network: networkName });
      }
    } catch (err) {
      this.logger.warn('Docker网络配置失败', { error: err.message });
    }
  }

  async execute(options) {
    if (!this.docker) {
      return this.executeLocalFallback(options);
    }

    const {
      image,
      commands,
      workspace,
      environment = {},
      volumes = [],
      timeout = 3600000,
      user = 'root'
    } = options;

    this.logger.info('在Docker容器中执行命令', { image, commands: commands.length });

    try {
      await this.pullImageIfNeeded(image);

      const containerVolumes = this.buildVolumes(workspace, volumes);
      const containerEnv = this.buildEnvironment(environment);

      const container = await this.docker.createContainer({
        Image: image,
        Cmd: ['sh', '-c', commands.join(' && ')],
        Env: containerEnv,
        HostConfig: {
          Binds: containerVolumes,
          NetworkMode: this.config.docker?.network || 'bridge'
        },
        WorkingDir: '/workspace',
        User: user,
        Tty: false
      });

      const containerId = container.id;
      this.logger.info('容器已创建', { containerId });

      await container.start();
      
      const output = await this.captureContainerOutput(container, timeout);
      const result = await container.wait();

      await container.remove({ force: true });

      const success = result.StatusCode === 0;
      
      this.logger.info('容器执行完成', { 
        containerId, 
        exitCode: result.StatusCode,
        success 
      });

      return {
        success,
        exitCode: result.StatusCode,
        output,
        containerId
      };
    } catch (err) {
      this.logger.error('Docker执行失败', { error: err.message });
      return {
        success: false,
        error: err.message,
        output: ''
      };
    }
  }

  async pullImageIfNeeded(image) {
    try {
      const images = await this.docker.listImages({
        filters: { reference: [image] }
      });

      if (images.length === 0) {
        this.logger.info('拉取Docker镜像', { image });
        
        await new Promise((resolve, reject) => {
          this.docker.pull(image, (err, stream) => {
            if (err) return reject(err);
            
            this.docker.modem.followProgress(stream, (err) => {
              if (err) reject(err);
              else resolve();
            });
          });
        });

        this.logger.info('Docker镜像拉取完成', { image });
      }
    } catch (err) {
      this.logger.warn('拉取Docker镜像失败', { image, error: err.message });
    }
  }

  buildVolumes(workspace, additionalVolumes) {
    const volumes = [
      `${workspace}:/workspace:rw`
    ];

    const cacheDir = this.config.cacheDir;
    if (cacheDir) {
      volumes.push(`${cacheDir}:/cache:rw`);
    }

    additionalVolumes.forEach(vol => {
      if (typeof vol === 'string') {
        volumes.push(vol);
      } else if (typeof vol === 'object') {
        volumes.push(`${vol.source}:${vol.target}:${vol.mode || 'rw'}`);
      }
    });

    return volumes;
  }

  buildEnvironment(environment) {
    const env = [];
    
    for (const [key, value] of Object.entries(environment)) {
      env.push(`${key}=${value}`);
    }

    return env;
  }

  async captureContainerOutput(container, timeout) {
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        container.stop().catch(() => {});
        reject(new Error('执行超时'));
      }, timeout);

      const outputStream = new PassThrough();
      let output = '';

      outputStream.on('data', chunk => {
        output += chunk.toString();
      });

      container.logs({
        follow: true,
        stdout: true,
        stderr: true,
        timestamps: false
      }, (err, stream) => {
        if (err) {
          clearTimeout(timeoutId);
          return reject(err);
        }

        if (stream) {
          container.modem.demuxStream(stream, outputStream, outputStream);
          
          stream.on('end', () => {
            clearTimeout(timeoutId);
            resolve(output);
          });

          stream.on('error', (err) => {
            clearTimeout(timeoutId);
            reject(err);
          });
        } else {
          clearTimeout(timeoutId);
          resolve(output);
        }
      });
    });
  }

  async executeLocalFallback(options) {
    this.logger.info('使用本地执行模式（Docker不可用）');
    
    const { spawn } = require('child_process');
    const { commands, workspace, environment = {} } = options;
    
    const env = { ...process.env, ...environment };
    let output = '';

    for (const cmd of commands) {
      this.logger.info('执行命令', { command: cmd });
      
      try {
        const cmdOutput = await new Promise((resolve, reject) => {
          const parts = cmd.split(' ');
          const child = spawn(parts[0], parts.slice(1), {
            cwd: workspace,
            env,
            shell: true
          });

          let cmdOut = '';
          
          child.stdout.on('data', data => {
            cmdOut += data.toString();
            this.logger.info(data.toString().trim());
          });

          child.stderr.on('data', data => {
            cmdOut += data.toString();
            this.logger.warn(data.toString().trim());
          });

          child.on('close', code => {
            if (code === 0) {
              resolve(cmdOut);
            } else {
              reject(new Error(`命令执行失败，退出码: ${code}\n${cmdOut}`));
            }
          });
        });

        output += cmdOutput;
      } catch (err) {
        return {
          success: false,
          error: err.message,
          output
        };
      }
    }

    return {
      success: true,
      output,
      exitCode: 0
    };
  }

  async buildImage(dockerfilePath, imageName, options = {}) {
    if (!this.docker) {
      throw new Error('Docker不可用');
    }

    this.logger.info('构建Docker镜像', { dockerfilePath, imageName });

    const context = path.dirname(dockerfilePath);
    const dockerfileName = path.basename(dockerfilePath);

    const buildStream = await this.docker.buildImage({
      context,
      src: '.'
    }, {
      t: imageName,
      dockerfile: dockerfileName,
      ...options
    });

    return new Promise((resolve, reject) => {
      let output = '';
      
      buildStream.on('data', chunk => {
        output += chunk.toString();
      });

      buildStream.on('end', () => {
        resolve({ success: true, imageName, output });
      });

      buildStream.on('error', reject);
    });
  }

  async pushImage(imageName, registryConfig) {
    if (!this.docker) {
      throw new Error('Docker不可用');
    }

    this.logger.info('推送Docker镜像', { imageName });

    const image = this.docker.getImage(imageName);
    
    const pushStream = await image.push({
      authconfig: registryConfig
    });

    return new Promise((resolve, reject) => {
      let output = '';
      
      pushStream.on('data', chunk => {
        output += chunk.toString();
      });

      pushStream.on('end', () => {
        resolve({ success: true, imageName, output });
      });

      pushStream.on('error', reject);
    });
  }
}

module.exports = DockerExecutor;
