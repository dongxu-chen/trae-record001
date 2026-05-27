const express = require('express');
const cors = require('cors');
const yaml = require('js-yaml');
const { v4: uuidv4 } = require('uuid');
const http = require('http');
const WebSocket = require('ws');

const app = express();
const PORT = 3001;
const server = http.createServer(app);
const wss = new WebSocket.Server({ server, path: '/ws' });

app.use(cors());
app.use(express.json({ limit: '10mb' }));

const NODE_TYPES = {
  compile: { label: '编译', color: '#3b82f6', icon: '⚙️' },
  test: { label: '测试', color: '#10b981', icon: '🧪' },
  build: { label: '构建', color: '#f59e0b', icon: '📦' },
  deploy: { label: '部署', color: '#ef4444', icon: '🚀' },
  parallel: { label: '并发组', color: '#8b5cf6', icon: '⚡' }
};

const PARAM_TYPES = ['string', 'number', 'boolean', 'array', 'object'];

const TEMPLATES = {
  'react-spa': {
    name: 'React SPA 前端流水线',
    description: 'React单页应用标准CI/CD流程：安装依赖→代码检查→测试→构建→部署到CDN',
    category: 'frontend',
    icon: '⚛️',
    nodes: [
      {
        id: 'n1', type: 'compile', position: { x: 100, y: 150 },
        data: { label: '安装依赖', script: ['npm ci'], runsOn: 'ubuntu-latest', image: 'node:20-alpine' }
      },
      {
        id: 'n2', type: 'test', position: { x: 350, y: 80 },
        data: { label: 'ESLint检查', script: ['npm run lint'], runsOn: 'ubuntu-latest', image: 'node:20-alpine' }
      },
      {
        id: 'n3', type: 'test', position: { x: 350, y: 220 },
        data: { label: '单元测试', script: ['npm test -- --coverage'], runsOn: 'ubuntu-latest', image: 'node:20-alpine', env: { CI: 'true' } }
      },
      {
        id: 'n4', type: 'build', position: { x: 600, y: 150 },
        data: { label: '生产构建', script: ['npm run build'], runsOn: 'ubuntu-latest', image: 'node:20-alpine', artifacts: { paths: ['dist/'] } }
      },
      {
        id: 'n5', type: 'deploy', position: { x: 850, y: 150 },
        data: { label: '部署到CDN', script: ['aws s3 sync dist/ s3://my-bucket/ --delete'], runsOn: 'ubuntu-latest' }
      }
    ],
    edges: [
      { id: 'e1', source: 'n1', target: 'n2', animated: true },
      { id: 'e2', source: 'n1', target: 'n3', animated: true },
      { id: 'e3', source: 'n2', target: 'n4', animated: true },
      { id: 'e4', source: 'n3', target: 'n4', animated: true },
      { id: 'e5', source: 'n4', target: 'n5', animated: true }
    ]
  },
  'vue-spa': {
    name: 'Vue.js 前端流水线',
    description: 'Vue.js应用标准流程：依赖安装→类型检查→测试→构建→部署',
    category: 'frontend',
    icon: '💚',
    nodes: [
      {
        id: 'n1', type: 'compile', position: { x: 100, y: 150 },
        data: { label: 'pnpm安装', script: ['pnpm install --frozen-lockfile'], runsOn: 'ubuntu-latest', image: 'node:20-alpine' }
      },
      {
        id: 'n2', type: 'test', position: { x: 350, y: 80 },
        data: { label: '类型检查', script: ['npx vue-tsc --noEmit'], runsOn: 'ubuntu-latest', image: 'node:20-alpine' }
      },
      {
        id: 'n3', type: 'test', position: { x: 350, y: 220 },
        data: { label: '组件测试', script: ['pnpm test:unit'], runsOn: 'ubuntu-latest', image: 'node:20-alpine' }
      },
      {
        id: 'n4', type: 'build', position: { x: 600, y: 150 },
        data: { label: 'Vite构建', script: ['pnpm build'], runsOn: 'ubuntu-latest', image: 'node:20-alpine', artifacts: { paths: ['dist/'] } }
      },
      {
        id: 'n5', type: 'deploy', position: { x: 850, y: 150 },
        data: { label: '部署Vercel', script: ['npx vercel --prod'], runsOn: 'ubuntu-latest' }
      }
    ],
    edges: [
      { id: 'e1', source: 'n1', target: 'n2', animated: true },
      { id: 'e2', source: 'n1', target: 'n3', animated: true },
      { id: 'e3', source: 'n2', target: 'n4', animated: true },
      { id: 'e4', source: 'n3', target: 'n4', animated: true },
      { id: 'e5', source: 'n4', target: 'n5', animated: true }
    ]
  },
  'nodejs-api': {
    name: 'Node.js API 后端流水线',
    description: 'Node.js后端服务：构建→测试→镜像构建→部署到K8s',
    category: 'backend',
    icon: '🟢',
    nodes: [
      {
        id: 'n1', type: 'compile', position: { x: 100, y: 100 },
        data: { label: '安装依赖', script: ['npm ci --production=false'], runsOn: 'ubuntu-latest', image: 'node:18-alpine' }
      },
      {
        id: 'n2', type: 'test', position: { x: 350, y: 100 },
        data: { label: '集成测试', script: ['npm run test:integration'], runsOn: 'ubuntu-latest', image: 'node:18-alpine', env: { NODE_ENV: 'test' } }
      },
      {
        id: 'n3', type: 'build', position: { x: 600, y: 100 },
        data: { label: 'Docker镜像', script: ['docker build -t my-api:$CI_COMMIT_SHA .', 'docker push my-api:$CI_COMMIT_SHA'], runsOn: 'ubuntu-latest' }
      },
      {
        id: 'n4', type: 'deploy', position: { x: 850, y: 100 },
        data: { label: 'K8s部署', script: ['kubectl set image deployment/api api=my-api:$CI_COMMIT_SHA', 'kubectl rollout status deployment/api'], runsOn: 'ubuntu-latest' }
      }
    ],
    edges: [
      { id: 'e1', source: 'n1', target: 'n2', animated: true },
      { id: 'e2', source: 'n2', target: 'n3', animated: true },
      { id: 'e3', source: 'n3', target: 'n4', animated: true }
    ]
  },
  'java-spring': {
    name: 'Java Spring Boot 流水线',
    description: 'Java企业级应用：Maven构建→单元测试→集成测试→Sonar扫描→镜像部署',
    category: 'backend',
    icon: '☕',
    nodes: [
      {
        id: 'n1', type: 'compile', position: { x: 100, y: 150 },
        data: { label: 'Maven编译', script: ['mvn compile -q'], runsOn: 'ubuntu-latest', image: 'maven:3.9-eclipse-temurin-17' }
      },
      {
        id: 'n2', type: 'test', position: { x: 350, y: 80 },
        data: { label: '单元测试', script: ['mvn test -DskipITs'], runsOn: 'ubuntu-latest', image: 'maven:3.9-eclipse-temurin-17' }
      },
      {
        id: 'n3', type: 'test', position: { x: 350, y: 220 },
        data: { label: 'Sonar扫描', script: ['mvn sonar:sonar'], runsOn: 'ubuntu-latest', image: 'maven:3.9-eclipse-temurin-17' }
      },
      {
        id: 'n4', type: 'test', position: { x: 600, y: 150 },
        data: { label: '集成测试', script: ['mvn verify'], runsOn: 'ubuntu-latest', image: 'maven:3.9-eclipse-temurin-17' }
      },
      {
        id: 'n5', type: 'build', position: { x: 850, y: 80 },
        data: { label: '构建镜像', script: ['mvn spring-boot:build-image'], runsOn: 'ubuntu-latest', image: 'maven:3.9-eclipse-temurin-17' }
      },
      {
        id: 'n6', type: 'deploy', position: { x: 850, y: 220 },
        data: { label: '部署生产', script: ['helm upgrade --install myapp ./helm'], runsOn: 'ubuntu-latest' }
      }
    ],
    edges: [
      { id: 'e1', source: 'n1', target: 'n2', animated: true },
      { id: 'e2', source: 'n1', target: 'n3', animated: true },
      { id: 'e3', source: 'n2', target: 'n4', animated: true },
      { id: 'e4', source: 'n3', target: 'n4', animated: true },
      { id: 'e5', source: 'n4', target: 'n5', animated: true },
      { id: 'e6', source: 'n5', target: 'n6', animated: true }
    ]
  },
  'python-django': {
    name: 'Python Django 流水线',
    description: 'Python Web应用：依赖安装→代码检查→测试→Docker构建→部署',
    category: 'backend',
    icon: '🐍',
    nodes: [
      {
        id: 'n1', type: 'compile', position: { x: 100, y: 100 },
        data: { label: '安装依赖', script: ['pip install -r requirements.txt', 'pip install -r requirements-dev.txt'], runsOn: 'ubuntu-latest', image: 'python:3.11' }
      },
      {
        id: 'n2', type: 'test', position: { x: 350, y: 80 },
        data: { label: 'flake8检查', script: ['flake8 .'], runsOn: 'ubuntu-latest', image: 'python:3.11' }
      },
      {
        id: 'n3', type: 'test', position: { x: 350, y: 180 },
        data: { label: 'pytest测试', script: ['pytest --cov=app tests/'], runsOn: 'ubuntu-latest', image: 'python:3.11' }
      },
      {
        id: 'n4', type: 'build', position: { x: 600, y: 130 },
        data: { label: 'Docker构建', script: ['docker build -t my-django-app .'], runsOn: 'ubuntu-latest' }
      },
      {
        id: 'n5', type: 'deploy', position: { x: 850, y: 130 },
        data: { label: 'ECS部署', script: ['aws ecs update-service --cluster my-cluster --service my-service --force-new-deployment'], runsOn: 'ubuntu-latest' }
      }
    ],
    edges: [
      { id: 'e1', source: 'n1', target: 'n2', animated: true },
      { id: 'e2', source: 'n1', target: 'n3', animated: true },
      { id: 'e3', source: 'n2', target: 'n4', animated: true },
      { id: 'e4', source: 'n3', target: 'n4', animated: true },
      { id: 'e5', source: 'n4', target: 'n5', animated: true }
    ]
  },
  'fullstack-monorepo': {
    name: '全栈 Monorepo 流水线',
    description: '前后端同仓：并行构建前端和后端→联调测试→联合部署',
    category: 'fullstack',
    icon: '🏗️',
    nodes: [
      {
        id: 'n1', type: 'compile', position: { x: 100, y: 100 },
        data: { label: '根依赖安装', script: ['npm ci'], runsOn: 'ubuntu-latest', image: 'node:20' }
      },
      {
        id: 'n2', type: 'compile', position: { x: 350, y: 50 },
        data: { label: '前端构建', script: ['npm run build:frontend'], runsOn: 'ubuntu-latest', image: 'node:20' }
      },
      {
        id: 'n3', type: 'compile', position: { x: 350, y: 200 },
        data: { label: '后端构建', script: ['npm run build:backend'], runsOn: 'ubuntu-latest', image: 'node:20' }
      },
      {
        id: 'n4', type: 'test', position: { x: 600, y: 125 },
        data: { label: 'E2E联调测试', script: ['npm run test:e2e'], runsOn: 'ubuntu-latest', image: 'cypress/included:13' }
      },
      {
        id: 'n5', type: 'deploy', position: { x: 850, y: 125 },
        data: { label: '联合部署', script: ['npm run deploy:all'], runsOn: 'ubuntu-latest' }
      }
    ],
    edges: [
      { id: 'e1', source: 'n1', target: 'n2', animated: true },
      { id: 'e2', source: 'n1', target: 'n3', animated: true },
      { id: 'e3', source: 'n2', target: 'n4', animated: true },
      { id: 'e4', source: 'n3', target: 'n4', animated: true },
      { id: 'e5', source: 'n4', target: 'n5', animated: true }
    ]
  }
};

const executionStats = {
  byType: {
    compile: { count: 156, totalDuration: 46800, successCount: 148, avgDuration: 300 },
    test: { count: 234, totalDuration: 70200, successCount: 215, avgDuration: 300 },
    build: { count: 145, totalDuration: 58000, successCount: 138, avgDuration: 400 },
    deploy: { count: 98, totalDuration: 29400, successCount: 92, avgDuration: 300 }
  },
  recentRuns: [
    { id: 'run-1', name: 'React SPA 流水线', status: 'success', duration: 180, startedAt: Date.now() - 3600000 },
    { id: 'run-2', name: 'Node.js API 流水线', status: 'success', duration: 240, startedAt: Date.now() - 7200000 },
    { id: 'run-3', name: 'Java Spring 流水线', status: 'failed', duration: 120, startedAt: Date.now() - 10800000 },
    { id: 'run-4', name: 'Vue.js 流水线', status: 'success', duration: 150, startedAt: Date.now() - 14400000 },
    { id: 'run-5', name: 'Python Django 流水线', status: 'success', duration: 200, startedAt: Date.now() - 18000000 }
  ],
  totalRuns: 633,
  successRate: 0.942
};

const activeExecutions = new Map();
const clients = new Set();

wss.on('connection', (ws) => {
  clients.add(ws);
  console.log('WebSocket client connected');
  
  ws.on('close', () => {
    clients.delete(ws);
    console.log('WebSocket client disconnected');
  });
});

function broadcast(message) {
  const data = JSON.stringify(message);
  clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(data);
    }
  });
}

function detectCycle(nodes, edges) {
  const adjacencyList = new Map();
  const visited = new Set();
  const recStack = new Set();
  const cyclePath = [];

  nodes.forEach(node => {
    adjacencyList.set(node.id, []);
  });

  edges.forEach(edge => {
    if (adjacencyList.has(edge.source)) {
      adjacencyList.get(edge.source).push(edge.target);
    }
  });

  function dfs(nodeId, path = []) {
    visited.add(nodeId);
    recStack.add(nodeId);
    path.push(nodeId);

    const neighbors = adjacencyList.get(nodeId) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (dfs(neighbor, path)) {
          return true;
        }
      } else if (recStack.has(neighbor)) {
        const cycleStart = path.indexOf(neighbor);
        cyclePath.push(...path.slice(cycleStart), neighbor);
        return true;
      }
    }

    path.pop();
    recStack.delete(nodeId);
    return false;
  }

  for (const node of nodes) {
    if (!visited.has(node.id)) {
      cyclePath.length = 0;
      if (dfs(node.id)) {
        return { hasCycle: true, cycle: cyclePath };
      }
    }
  }

  return { hasCycle: false, cycle: [] };
}

function buildPipelineStructure(nodes, edges, maxParallel = 5) {
  const cycleCheck = detectCycle(nodes, edges);
  if (cycleCheck.hasCycle) {
    const cycleLabels = cycleCheck.cycle.map(id => {
      const node = nodes.find(n => n.id === id);
      return node?.data?.label || id;
    });
    throw new Error(`检测到循环依赖: ${cycleLabels.join(' → ')}`);
  }

  const nodeMap = new Map(nodes.map(n => [n.id, n]));
  const inDegree = new Map();
  const adjacencyList = new Map();

  nodes.forEach(node => {
    inDegree.set(node.id, 0);
    adjacencyList.set(node.id, []);
  });

  edges.forEach(edge => {
    const source = edge.source;
    const target = edge.target;
    adjacencyList.get(source).push(target);
    inDegree.set(target, (inDegree.get(target) || 0) + 1);
  });

  const stages = [];
  const visited = new Set();

  function topologicalSort() {
    const queue = [];
    inDegree.forEach((degree, nodeId) => {
      if (degree === 0) {
        queue.push(nodeId);
      }
    });

    while (queue.length > 0) {
      const levelSize = queue.length;
      const currentStage = [];

      for (let i = 0; i < levelSize; i++) {
        const nodeId = queue.shift();
        if (visited.has(nodeId)) continue;
        visited.add(nodeId);

        const node = nodeMap.get(nodeId);
        if (node) {
          currentStage.push(node);
        }

        const neighbors = adjacencyList.get(nodeId) || [];
        neighbors.forEach(neighbor => {
          inDegree.set(neighbor, inDegree.get(neighbor) - 1);
          if (inDegree.get(neighbor) === 0) {
            queue.push(neighbor);
          }
        });
      }

      if (currentStage.length > 0) {
        if (currentStage.length > maxParallel) {
          for (let i = 0; i < currentStage.length; i += maxParallel) {
            const chunk = currentStage.slice(i, i + maxParallel);
            const isLastChunk = i + maxParallel >= currentStage.length;
            stages.push({
              jobs: chunk,
              parallel: chunk.length > 1,
              queued: !isLastChunk,
              maxParallel
            });
          }
        } else {
          stages.push({
            jobs: currentStage,
            parallel: currentStage.length > 1,
            queued: false,
            maxParallel
          });
        }
      }
    }
  }

  topologicalSort();
  return stages;
}

function parseParameterValue(value, type) {
  if (type === 'number') {
    const num = Number(value);
    return isNaN(num) ? value : num;
  } else if (type === 'boolean') {
    return value === 'true' || value === true;
  } else if (type === 'array') {
    if (Array.isArray(value)) return value;
    try {
      return JSON.parse(value);
    } catch {
      return value.split(',').map(s => s.trim());
    }
  } else if (type === 'object') {
    if (typeof value === 'object') return value;
    try {
      return JSON.parse(value);
    } catch {
      return { value };
    }
  }
  return String(value);
}

function generateYamlPipeline(nodes, edges, pipelineConfig = {}) {
  const maxParallel = pipelineConfig.maxParallel || 5;
  const stages = buildPipelineStructure(nodes, edges, maxParallel);
  const nodeMap = new Map(nodes.map(n => [n.id, n]));

  const pipeline = {
    name: pipelineConfig.name || 'my-pipeline',
    version: pipelineConfig.version || '1.0',
    trigger: pipelineConfig.trigger || {
      push: {
        branches: ['main', 'develop']
      }
    },
    max_parallel: maxParallel,
    stages: []
  };

  stages.forEach((stage, stageIndex) => {
    const stageData = {
      name: `stage-${stageIndex + 1}`,
      parallel: stage.parallel,
      max_parallel: stage.maxParallel,
      queued: stage.queued,
      jobs: []
    };

    stage.jobs.forEach(node => {
      const nodeType = NODE_TYPES[node.type] || { label: node.type };
      const job = {
        name: node.data.label || `${node.type}-${node.id}`,
        type: node.type,
        runs_on: node.data.runsOn || 'ubuntu-latest'
      };

      if (node.data.script) {
        job.script = node.data.script;
      }

      if (node.data.image) {
        job.image = node.data.image;
      }

      if (node.data.env && Object.keys(node.data.env).length > 0) {
        job.environment = node.data.env;
      }

      if (node.data.parameters && Object.keys(node.data.parameters).length > 0) {
        const typedParams = {};
        Object.entries(node.data.parameters).forEach(([key, param]) => {
          if (typeof param === 'object' && param !== null && 'type' in param) {
            typedParams[key] = {
              type: param.type,
              value: parseParameterValue(param.value, param.type),
              description: param.description || ''
            };
          } else {
            typedParams[key] = {
              type: 'string',
              value: String(param),
              description: ''
            };
          }
        });
        job.parameters = typedParams;
      }

      if (node.data.timeout) {
        job.timeout_minutes = node.data.timeout;
      }

      if (node.data.retry) {
        job.retry = node.data.retry;
      }

      const dependencies = edges
        .filter(e => e.target === node.id)
        .map(e => {
          const sourceNode = nodeMap.get(e.source);
          return sourceNode?.data?.label || e.source;
        });

      if (dependencies.length > 0) {
        job.needs = dependencies;
      }

      if (node.data.artifacts) {
        job.artifacts = node.data.artifacts;
      }

      job.description = `${nodeType.icon} ${nodeType.label}任务`;

      stageData.jobs.push(job);
    });

    pipeline.stages.push(stageData);
  });

  if (pipelineConfig.globalEnv && Object.keys(pipelineConfig.globalEnv).length > 0) {
    pipeline.global_environment = pipelineConfig.globalEnv;
  }

  if (pipelineConfig.notifications) {
    pipeline.notifications = pipelineConfig.notifications;
  }

  return yaml.dump(pipeline, {
    indent: 2,
    lineWidth: -1,
    noRefs: true
  });
}

function parseYamlToFlow(yamlContent) {
  try {
    const pipeline = yaml.load(yamlContent);
    const nodes = [];
    const edges = [];
    const jobToNodeId = new Map();

    let positionX = 100;
    let positionY = 100;
    const nodeSpacing = 200;
    const stageSpacing = 250;

    const reverseNodeTypes = Object.entries(NODE_TYPES).reduce((acc, [key, val]) => {
      acc[val.label] = key;
      return acc;
    }, {});

    pipeline.stages?.forEach((stage, stageIndex) => {
      const jobsInStage = stage.jobs || [];
      const stageStartY = positionY;

      jobsInStage.forEach((job, jobIndex) => {
        const nodeId = uuidv4();
        jobToNodeId.set(job.name, nodeId);

        let nodeType = 'build';
        if (job.type && NODE_TYPES[job.type]) {
          nodeType = job.type;
        } else if (reverseNodeTypes[job.type]) {
          nodeType = reverseNodeTypes[job.type];
        } else {
          const jobName = job.name.toLowerCase();
          if (jobName.includes('compile') || jobName.includes('build')) nodeType = 'compile';
          else if (jobName.includes('test')) nodeType = 'test';
          else if (jobName.includes('deploy')) nodeType = 'deploy';
        }

        let parameters = {};
        if (job.parameters) {
          Object.entries(job.parameters).forEach(([key, param]) => {
            if (typeof param === 'object' && param !== null && 'type' in param) {
              parameters[key] = {
                type: param.type,
                value: param.value,
                description: param.description || ''
              };
            } else {
              parameters[key] = {
                type: 'string',
                value: param,
                description: ''
              };
            }
          });
        }

        nodes.push({
          id: nodeId,
          type: nodeType,
          position: {
            x: positionX + (stageIndex * stageSpacing),
            y: stageStartY + (jobIndex * nodeSpacing)
          },
          data: {
            label: job.name,
            runsOn: job.runs_on,
            script: job.script,
            image: job.image,
            env: job.environment || {},
            parameters,
            timeout: job.timeout_minutes,
            retry: job.retry,
            artifacts: job.artifacts
          }
        });

        if (job.needs && job.needs.length > 0) {
          job.needs.forEach(needName => {
            const sourceId = jobToNodeId.get(needName);
            if (sourceId) {
              edges.push({
                id: uuidv4(),
                source: sourceId,
                target: nodeId,
                animated: true,
                style: { stroke: '#6366f1', strokeWidth: 2 }
              });
            }
          });
        }
      });
    });

    return {
      nodes,
      edges,
      pipelineConfig: {
        name: pipeline.name,
        version: pipeline.version,
        trigger: pipeline.trigger,
        globalEnv: pipeline.global_environment,
        notifications: pipeline.notifications,
        maxParallel: pipeline.max_parallel || 5
      }
    };
  } catch (error) {
    throw new Error(`YAML解析失败: ${error.message}`);
  }
}

async function simulateExecution(executionId, nodes, edges, pipelineConfig) {
  const stages = buildPipelineStructure(nodes, edges, pipelineConfig.maxParallel || 5);
  
  const execution = {
    id: executionId,
    status: 'running',
    stages: [],
    currentStage: 0,
    logs: [],
    startedAt: Date.now(),
    completedAt: null
  };
  
  activeExecutions.set(executionId, execution);

  broadcast({
    type: 'execution-started',
    executionId,
    totalStages: stages.length
  });

  for (let stageIndex = 0; stageIndex < stages.length; stageIndex++) {
    const stage = stages[stageIndex];
    const stageData = {
      name: `Stage ${stageIndex + 1}`,
      jobs: [],
      status: 'running',
      startedAt: Date.now()
    };
    
    execution.currentStage = stageIndex;
    execution.stages.push(stageData);

    broadcast({
      type: 'stage-started',
      executionId,
      stageIndex,
      jobCount: stage.jobs.length
    });

    const jobPromises = stage.jobs.map(async (job, jobIndex) => {
      const jobData = {
        id: job.id,
        name: job.data.label,
        type: job.type,
        status: 'running',
        startedAt: Date.now(),
        duration: 0
      };
      stageData.jobs.push(jobData);

      const logPrefix = `[${job.data.label}]`;
      
      const addLog = (message, level = 'info') => {
        const log = {
          timestamp: Date.now(),
          stage: stageIndex,
          job: job.data.label,
          message,
          level
        };
        execution.logs.push(log);
        broadcast({
          type: 'log',
          executionId,
          ...log
        });
      };

      addLog('🚀 任务开始执行...', 'info');
      await delay(500);

      addLog(`📦 运行环境: ${job.data.runsOn || 'ubuntu-latest'}`, 'info');
      if (job.data.image) {
        addLog(`🐳 使用镜像: ${job.data.image}`, 'info');
      }
      await delay(300);

      if (job.data.script) {
        for (const script of job.data.script) {
          addLog(`$ ${script}`, 'command');
          await delay(800 + Math.random() * 700);
          
          const mockOutputs = {
            'npm install': [
              'added 1234 packages in 45s',
              '128 packages are looking for funding'
            ],
            'npm run build': [
              'vite v5.0.0 building for production...',
              '✓ 267 modules transformed.',
              'build completed in 12.34s'
            ],
            'npm test': [
              '  PASS  src/App.test.js',
              '  PASS  src/utils.test.js',
              '',
              'Test Suites: 2 passed, 2 total',
              'Tests:       8 passed, 8 total'
            ],
            'npm run lint': [
              '✔ No ESLint warnings or errors'
            ]
          };

          const outputs = mockOutputs[script] || [
            'processing...',
            'done.'
          ];

          for (const output of outputs) {
            addLog(output, 'output');
            await delay(400);
          }
        }
      }

      const success = Math.random() > 0.1;
      const duration = Math.floor(5 + Math.random() * 10);
      
      if (success) {
        jobData.status = 'success';
        addLog(`✅ 任务完成 (用时 ${duration}s)`, 'success');
      } else {
        jobData.status = 'failed';
        addLog(`❌ 任务失败: 模拟错误发生`, 'error');
        addLog('exit code 1', 'error');
      }
      
      jobData.duration = duration;
      jobData.completedAt = Date.now();
      
      return { success, jobType: job.type, duration };
    });

    const results = await Promise.all(jobPromises);
    stageData.completedAt = Date.now();
    
    const allSuccess = results.every(r => r.success);
    stageData.status = allSuccess ? 'success' : 'failed';

    results.forEach(({ success, jobType, duration }) => {
      const stats = executionStats.byType[jobType] || { count: 0, totalDuration: 0, successCount: 0 };
      stats.count++;
      stats.totalDuration += duration;
      stats.successCount += success ? 1 : 0;
      stats.avgDuration = Math.floor(stats.totalDuration / stats.count);
      executionStats.byType[jobType] = stats;
    });

    broadcast({
      type: 'stage-completed',
      executionId,
      stageIndex,
      status: stageData.status,
      results
    });

    if (!allSuccess) {
      execution.status = 'failed';
      execution.completedAt = Date.now();
      broadcast({
        type: 'execution-completed',
        executionId,
        status: 'failed',
        totalDuration: Math.floor((Date.now() - execution.startedAt) / 1000)
      });
      activeExecutions.delete(executionId);
      return;
    }
  }

  execution.status = 'success';
  execution.completedAt = Date.now();
  
  executionStats.totalRuns++;
  const successRuns = Object.values(executionStats.byType).reduce((sum, t) => sum + t.successCount, 0);
  const totalRuns = Object.values(executionStats.byType).reduce((sum, t) => sum + t.count, 0);
  executionStats.successRate = successRuns / totalRuns;

  executionStats.recentRuns.unshift({
    id: executionId,
    name: pipelineConfig.name || '流水线执行',
    status: 'success',
    duration: Math.floor((Date.now() - execution.startedAt) / 1000),
    startedAt: execution.startedAt
  });
  executionStats.recentRuns = executionStats.recentRuns.slice(0, 10);

  broadcast({
    type: 'execution-completed',
    executionId,
    status: 'success',
    totalDuration: Math.floor((Date.now() - execution.startedAt) / 1000)
  });
  
  activeExecutions.delete(executionId);
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'CI/CD Pipeline Server is running' });
});

app.get('/api/node-types', (req, res) => {
  res.json(NODE_TYPES);
});

app.get('/api/param-types', (req, res) => {
  res.json(PARAM_TYPES);
});

app.get('/api/templates', (req, res) => {
  const category = req.query.category;
  let templates = Object.entries(TEMPLATES).map(([id, t]) => ({ id, ...t }));
  
  if (category && category !== 'all') {
    templates = templates.filter(t => t.category === category);
  }
  
  res.json(templates);
});

app.get('/api/templates/:id', (req, res) => {
  const template = TEMPLATES[req.params.id];
  if (!template) {
    return res.status(404).json({ error: '模板不存在' });
  }
  res.json({ id: req.params.id, ...template });
});

app.get('/api/stats', (req, res) => {
  res.json(executionStats);
});

app.post('/api/executions', (req, res) => {
  const { nodes, edges, pipelineConfig } = req.body;
  
  if (!nodes || !Array.isArray(nodes)) {
    return res.status(400).json({ error: '无效的节点数据' });
  }

  const cycleCheck = detectCycle(nodes, edges || []);
  if (cycleCheck.hasCycle) {
    const cycleLabels = cycleCheck.cycle.map(id => {
      const node = nodes.find(n => n.id === id);
      return node?.data?.label || id;
    });
    return res.status(400).json({
      error: `检测到循环依赖，无法执行: ${cycleLabels.join(' → ')}`,
      cycle: cycleLabels
    });
  }

  const executionId = `exec-${Date.now()}-${uuidv4().slice(0, 8)}`;
  simulateExecution(executionId, nodes, edges || [], pipelineConfig || {});
  
  res.json({
    success: true,
    executionId,
    message: '执行已开始'
  });
});

app.get('/api/executions/:id', (req, res) => {
  const execution = activeExecutions.get(req.params.id);
  if (!execution) {
    return res.status(404).json({ error: '执行不存在或已完成' });
  }
  res.json(execution);
});

app.post('/api/generate-yaml', (req, res) => {
  try {
    const { nodes, edges, pipelineConfig } = req.body;

    if (!nodes || !Array.isArray(nodes)) {
      return res.status(400).json({ error: '无效的节点数据' });
    }

    const cycleCheck = detectCycle(nodes, edges || []);
    if (cycleCheck.hasCycle) {
      const cycleLabels = cycleCheck.cycle.map(id => {
        const node = nodes.find(n => n.id === id);
        return node?.data?.label || id;
      });
      return res.status(400).json({
        error: `检测到循环依赖，禁止保存: ${cycleLabels.join(' → ')}`,
        cycle: cycleLabels
      });
    }

    const yamlContent = generateYamlPipeline(nodes, edges || [], pipelineConfig || {});

    res.json({
      success: true,
      yaml: yamlContent,
      preview: yamlContent.slice(0, 500) + (yamlContent.length > 500 ? '...' : '')
    });
  } catch (error) {
    console.error('生成YAML失败:', error);
    res.status(400).json({ error: error.message });
  }
});

app.post('/api/parse-yaml', (req, res) => {
  try {
    const { yaml: yamlContent } = req.body;

    if (!yamlContent || typeof yamlContent !== 'string') {
      return res.status(400).json({ error: '请提供有效的YAML内容' });
    }

    const flowData = parseYamlToFlow(yamlContent);

    const cycleCheck = detectCycle(flowData.nodes, flowData.edges);
    if (cycleCheck.hasCycle) {
      return res.status(400).json({
        error: '导入的YAML包含循环依赖，无法导入'
      });
    }

    res.json({
      success: true,
      ...flowData
    });
  } catch (error) {
    console.error('解析YAML失败:', error);
    res.status(400).json({ error: error.message });
  }
});

app.post('/api/validate-pipeline', (req, res) => {
  try {
    const { nodes, edges } = req.body;
    const errors = [];
    const warnings = [];

    if (!nodes || nodes.length === 0) {
      errors.push('流水线不能为空，请至少添加一个任务节点');
    }

    const nodeIds = new Set(nodes?.map(n => n.id) || []);
    edges?.forEach(edge => {
      if (!nodeIds.has(edge.source)) {
        errors.push(`边 ${edge.id} 引用了不存在的源节点 ${edge.source}`);
      }
      if (!nodeIds.has(edge.target)) {
        errors.push(`边 ${edge.id} 引用了不存在的目标节点 ${edge.target}`);
      }
    });

    const cycleCheck = detectCycle(nodes || [], edges || []);
    if (cycleCheck.hasCycle) {
      const cycleLabels = cycleCheck.cycle.map(id => {
        const node = nodes.find(n => n.id === id);
        return node?.data?.label || id;
      });
      errors.push(`检测到循环依赖: ${cycleLabels.join(' → ')}`);
    }

    if (errors.length === 0) {
      try {
        const stages = buildPipelineStructure(nodes || [], edges || []);
        
        nodes?.forEach(node => {
          if (!node.data?.label) {
            warnings.push(`节点 ${node.id} 没有设置名称`);
          }
          if (!node.data?.script && node.type !== 'parallel') {
            warnings.push(`节点 ${node.data?.label || node.id} 没有配置执行脚本`);
          }
        });

        res.json({
          valid: true,
          errors: [],
          warnings,
          stages: stages.length,
          totalJobs: nodes?.length || 0
        });
      } catch (buildError) {
        res.json({
          valid: false,
          errors: [buildError.message],
          warnings: [],
          stages: 0,
          totalJobs: nodes?.length || 0
        });
      }
    } else {
      res.json({
        valid: false,
        errors,
        warnings,
        stages: 0,
        totalJobs: nodes?.length || 0
      });
    }
  } catch (error) {
    console.error('验证流水线失败:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/export-pipeline', (req, res) => {
  try {
    const { nodes, edges, pipelineConfig } = req.body;

    const cycleCheck = detectCycle(nodes, edges || []);
    if (cycleCheck.hasCycle) {
      const cycleLabels = cycleCheck.cycle.map(id => {
        const node = nodes.find(n => n.id === id);
        return node?.data?.label || id;
      });
      return res.status(400).json({
        error: `检测到循环依赖，无法导出: ${cycleLabels.join(' → ')}`
      });
    }

    const yamlContent = generateYamlPipeline(nodes, edges || [], pipelineConfig || {});

    res.setHeader('Content-Type', 'application/x-yaml');
    res.setHeader('Content-Disposition', `attachment; filename="${pipelineConfig?.name || 'pipeline'}.yaml"`);
    res.send(yamlContent);
  } catch (error) {
    console.error('导出流水线失败:', error);
    res.status(400).json({ error: error.message });
  }
});

app.post('/api/import-pipeline', (req, res) => {
  try {
    const { fileContent } = req.body;
    const flowData = parseYamlToFlow(fileContent);

    const cycleCheck = detectCycle(flowData.nodes, flowData.edges);
    if (cycleCheck.hasCycle) {
      return res.status(400).json({
        error: '导入的YAML包含循环依赖，无法导入'
      });
    }

    res.json({
      success: true,
      message: '流水线导入成功',
      ...flowData
    });
  } catch (error) {
    console.error('导入流水线失败:', error);
    res.status(400).json({ error: error.message });
  }
});

server.listen(PORT, () => {
  console.log(`CI/CD Pipeline Server 运行在 http://localhost:${PORT}`);
  console.log(`WebSocket 端点: ws://localhost:${PORT}/ws`);
});
