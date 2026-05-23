const fs = require('fs-extra');
const path = require('path');

class TemplateManager {
  constructor({ logger, config }) {
    this.logger = logger;
    this.config = config;
    this.templatesDir = path.join(__dirname, '..', '..', 'templates');
    this.userTemplatesDir = path.join(this.config.workDir || './workspace', 'templates');
    this.templates = new Map();
  }

  async initialize() {
    await fs.ensureDir(this.templatesDir);
    await fs.ensureDir(this.userTemplatesDir);
    await this.loadBuiltInTemplates();
    await this.loadUserTemplates();
    this.logger.info('模板管理器初始化完成', { 
      builtIn: this.getBuiltInTemplates().length,
      user: this.getUserTemplates().length 
    });
  }

  async loadBuiltInTemplates() {
    const builtInTemplates = this.getBuiltInTemplateDefinitions();
    for (const template of builtInTemplates) {
      this.templates.set(`builtin:${template.id}`, {
        ...template,
        type: 'builtin',
        createdAt: new Date().toISOString()
      });
    }
  }

  getBuiltInTemplateDefinitions() {
    return [
      {
        id: 'nodejs-basic',
        name: 'Node.js 基础流水线',
        description: '适用于Node.js项目的基础CI/CD流水线，包含安装依赖、测试、构建',
        category: 'Node.js',
        icon: 'nodejs',
        tags: ['nodejs', 'npm', 'javascript'],
        stages: [
          {
            name: 'checkout',
            script: ['git clone $CLONE_URL .', 'git checkout $GIT_COMMIT']
          },
          {
            name: 'install',
            image: 'node:18-alpine',
            script: ['npm ci'],
            cache: {
              key: 'node-modules-{{ checksum "package-lock.json" }}',
              paths: ['node_modules']
            }
          },
          {
            name: 'test',
            image: 'node:18-alpine',
            script: ['npm test'],
            qualityGate: {
              coverageThreshold: 80,
              coverageFile: 'coverage/coverage-summary.json'
            }
          },
          {
            name: 'build',
            image: 'node:18-alpine',
            script: ['npm run build'],
            artifacts: {
              paths: ['dist/'],
              name: 'build-output'
            }
          }
        ]
      },
      {
        id: 'nodejs-docker-deploy',
        name: 'Node.js Docker部署',
        description: 'Node.js项目完整流水线，包含Docker镜像构建和部署',
        category: 'Node.js',
        icon: 'docker',
        tags: ['nodejs', 'docker', 'deploy'],
        stages: [
          {
            name: 'checkout',
            script: ['git clone $CLONE_URL .', 'git checkout $GIT_COMMIT']
          },
          {
            name: 'install',
            image: 'node:18-alpine',
            script: ['npm ci'],
            cache: {
              key: 'node-modules-{{ checksum "package-lock.json" }}',
              paths: ['node_modules']
            }
          },
          {
            name: 'test',
            image: 'node:18-alpine',
            script: ['npm test'],
            qualityGate: {
              coverageThreshold: 80
            }
          },
          {
            name: 'build',
            image: 'node:18-alpine',
            script: ['npm run build']
          },
          {
            name: 'docker-build',
            image: 'docker:latest',
            script: [
              'docker build -t $IMAGE_NAME:$GIT_COMMIT .',
              'docker tag $IMAGE_NAME:$GIT_COMMIT $IMAGE_NAME:latest'
            ],
            volumes: ['/var/run/docker.sock:/var/run/docker.sock'],
            condition: {
              branch: ['main', 'master']
            }
          }
        ]
      },
      {
        id: 'maven-java',
        name: 'Maven Java 流水线',
        description: 'Java项目Maven构建流水线，包含编译、测试、打包',
        category: 'Java',
        icon: 'java',
        tags: ['java', 'maven', 'spring-boot'],
        stages: [
          {
            name: 'checkout',
            script: ['git clone $CLONE_URL .', 'git checkout $GIT_COMMIT']
          },
          {
            name: 'build',
            image: 'maven:3.8-openjdk-17',
            script: ['mvn clean package -DskipTests'],
            cache: {
              key: 'maven-deps',
              paths: ['~/.m2/repository']
            }
          },
          {
            name: 'test',
            image: 'maven:3.8-openjdk-17',
            script: ['mvn test'],
            qualityGate: {
              coverageThreshold: 70,
              coverageFile: 'target/site/jacoco/jacoco.csv'
            }
          },
          {
            name: 'package',
            image: 'maven:3.8-openjdk-17',
            script: ['mvn package'],
            artifacts: {
              paths: ['target/*.jar'],
              name: 'jar-artifacts'
            }
          }
        ]
      },
      {
        id: 'python-basic',
        name: 'Python 基础流水线',
        description: 'Python项目基础CI流水线，包含依赖安装、测试、代码检查',
        category: 'Python',
        icon: 'python',
        tags: ['python', 'pytest', 'flake8'],
        stages: [
          {
            name: 'checkout',
            script: ['git clone $CLONE_URL .', 'git checkout $GIT_COMMIT']
          },
          {
            name: 'setup',
            image: 'python:3.11-slim',
            script: [
              'pip install -r requirements.txt',
              'pip install pytest flake8 pytest-cov'
            ],
            cache: {
              key: 'pip-packages',
              paths: ['~/.cache/pip']
            }
          },
          {
            name: 'lint',
            image: 'python:3.11-slim',
            script: ['flake8 . --max-line-length=120']
          },
          {
            name: 'test',
            image: 'python:3.11-slim',
            script: ['pytest --cov=./ --cov-report=term'],
            qualityGate: {
              coverageThreshold: 75,
              coverageFile: 'htmlcov/index.html'
            }
          }
        ]
      },
      {
        id: 'go-basic',
        name: 'Go 语言流水线',
        description: 'Go项目构建测试流水线',
        category: 'Go',
        icon: 'go',
        tags: ['golang', 'go-test', 'go-build'],
        stages: [
          {
            name: 'checkout',
            script: ['git clone $CLONE_URL .', 'git checkout $GIT_COMMIT']
          },
          {
            name: 'deps',
            image: 'golang:1.21-alpine',
            script: ['go mod download'],
            cache: {
              key: 'go-modules',
              paths: ['~/go/pkg/mod']
            }
          },
          {
            name: 'lint',
            image: 'golang:1.21-alpine',
            script: ['go vet ./...']
          },
          {
            name: 'test',
            image: 'golang:1.21-alpine',
            script: ['go test -v ./... -cover'],
            qualityGate: {
              coverageThreshold: 80
            }
          },
          {
            name: 'build',
            image: 'golang:1.21-alpine',
            script: ['go build -o app ./cmd/main.go'],
            artifacts: {
              paths: ['app'],
              name: 'binary'
            }
          }
        ]
      },
      {
        id: 'react-spa',
        name: 'React SPA 流水线',
        description: 'React单页应用流水线，包含测试、构建、部署',
        category: 'Frontend',
        icon: 'react',
        tags: ['react', 'spa', 'frontend'],
        stages: [
          {
            name: 'checkout',
            script: ['git clone $CLONE_URL .', 'git checkout $GIT_COMMIT']
          },
          {
            name: 'install',
            image: 'node:18-alpine',
            script: ['npm ci'],
            cache: {
              key: 'node-modules-{{ checksum "package-lock.json" }}',
              paths: ['node_modules']
            }
          },
          {
            name: 'lint',
            image: 'node:18-alpine',
            script: ['npm run lint']
          },
          {
            name: 'test',
            image: 'node:18-alpine',
            script: ['npm test -- --coverage'],
            qualityGate: {
              coverageThreshold: 85,
              coverageFile: 'coverage/coverage-final.json'
            }
          },
          {
            name: 'build',
            image: 'node:18-alpine',
            script: ['npm run build'],
            artifacts: {
              paths: ['build/'],
              name: 'static-build'
            }
          }
        ]
      },
      {
        id: 'vue-spa',
        name: 'Vue.js SPA 流水线',
        description: 'Vue.js单页应用流水线',
        category: 'Frontend',
        icon: 'vue',
        tags: ['vue', 'spa', 'frontend'],
        stages: [
          {
            name: 'checkout',
            script: ['git clone $CLONE_URL .', 'git checkout $GIT_COMMIT']
          },
          {
            name: 'install',
            image: 'node:18-alpine',
            script: ['npm ci'],
            cache: {
              key: 'node-modules-{{ checksum "package-lock.json" }}',
              paths: ['node_modules']
            }
          },
          {
            name: 'lint',
            image: 'node:18-alpine',
            script: ['npm run lint']
          },
          {
            name: 'test',
            image: 'node:18-alpine',
            script: ['npm run test:unit'],
            qualityGate: {
              coverageThreshold: 80
            }
          },
          {
            name: 'build',
            image: 'node:18-alpine',
            script: ['npm run build'],
            artifacts: {
              paths: ['dist/'],
              name: 'static-build'
            }
          }
        ]
      },
      {
        id: 'monorepo',
        name: 'Monorepo 多包流水线',
        description: '适用于Monorepo项目的并行构建流水线',
        category: 'Advanced',
        icon: 'monorepo',
        tags: ['monorepo', 'pnpm', 'turborepo'],
        stages: [
          {
            name: 'checkout',
            script: ['git clone $CLONE_URL .', 'git checkout $GIT_COMMIT']
          },
          {
            name: 'install',
            image: 'node:18-alpine',
            script: ['pnpm install --frozen-lockfile'],
            cache: {
              key: 'pnpm-store',
              paths: ['~/.pnpm-store']
            }
          },
          {
            name: 'build-all',
            image: 'node:18-alpine',
            parallel: true,
            tasks: [
              { name: 'build-package-a', script: ['pnpm --filter package-a build'] },
              { name: 'build-package-b', script: ['pnpm --filter package-b build'] }
            ]
          },
          {
            name: 'test-all',
            image: 'node:18-alpine',
            parallel: true,
            tasks: [
              { name: 'test-package-a', script: ['pnpm --filter package-a test'] },
              { name: 'test-package-b', script: ['pnpm --filter package-b test'] }
            ]
          }
        ]
      }
    ];
  }

  async loadUserTemplates() {
    try {
      const files = await fs.readdir(this.userTemplatesDir);
      for (const file of files) {
        if (file.endsWith('.json')) {
          try {
            const content = await fs.readJson(path.join(this.userTemplatesDir, file));
            this.templates.set(`user:${content.id}`, {
              ...content,
              type: 'user',
              createdAt: content.createdAt || new Date().toISOString()
            });
          } catch (err) {
            this.logger.warn('加载用户模板失败', { file, error: err.message });
          }
        }
      }
    } catch (err) {
      this.logger.warn('加载用户模板目录失败', { error: err.message });
    }
  }

  getTemplates(category = null, search = null) {
    let templates = Array.from(this.templates.values());
    
    if (category) {
      templates = templates.filter(t => t.category === category);
    }
    
    if (search) {
      const searchLower = search.toLowerCase();
      templates = templates.filter(t => 
        t.name.toLowerCase().includes(searchLower) ||
        t.description.toLowerCase().includes(searchLower) ||
        t.tags?.some(tag => tag.toLowerCase().includes(searchLower))
      );
    }
    
    return templates;
  }

  getTemplate(id) {
    return this.templates.get(id) || null;
  }

  getBuiltInTemplates() {
    return Array.from(this.templates.values()).filter(t => t.type === 'builtin');
  }

  getUserTemplates() {
    return Array.from(this.templates.values()).filter(t => t.type === 'user');
  }

  getCategories() {
    const categories = new Set();
    this.templates.forEach(t => categories.add(t.category));
    return Array.from(categories);
  }

  async saveUserTemplate(template) {
    const id = `user-template-${Date.now()}`;
    const templateData = {
      id,
      ...template,
      type: 'user',
      createdAt: new Date().toISOString()
    };

    const filePath = path.join(this.userTemplatesDir, `${id}.json`);
    await fs.writeJson(filePath, templateData, { spaces: 2 });
    
    this.templates.set(`user:${id}`, templateData);
    return templateData;
  }

  async deleteUserTemplate(id) {
    const key = `user:${id}`;
    if (!this.templates.has(key)) {
      return false;
    }

    const filePath = path.join(this.userTemplatesDir, `${id}.json`);
    if (await fs.pathExists(filePath)) {
      await fs.remove(filePath);
    }
    
    this.templates.delete(key);
    return true;
  }

  generateConfigFromTemplate(templateId, options = {}) {
    const template = this.getTemplate(templateId);
    if (!template) {
      throw new Error(`模板 ${templateId} 不存在`);
    }

    return {
      name: options.name || template.name,
      repository: options.repository || '',
      branch: options.branch || 'main',
      stages: template.stages.map(stage => ({
        ...stage,
        ...options.overrides?.[stage.name]
      }))
    };
  }
}

module.exports = TemplateManager;
