import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { cloneDeep } from 'lodash-es'

export const useTemplateStore = defineStore('template', () => {
  const templates = ref([
    {
      id: 'java-maven',
      name: 'Java Maven 流水线',
      category: 'Java',
      icon: 'Coffee',
      description: '标准Java Maven项目流水线，包含编译、单元测试、代码质量检查、打包部署',
      tags: ['Maven', 'JUnit', 'SonarQube', 'Docker'],
      stages: [
        {
          id: 'checkout',
          name: '代码检出',
          parallel: false,
          when: { condition: 'always', expression: '' },
          tasks: [
            { id: 't1', name: 'Git Clone', type: 'git', config: { branch: 'main' } }
          ]
        },
        {
          id: 'build',
          name: '编译构建',
          parallel: false,
          when: { condition: 'success', expression: '' },
          tasks: [
            { id: 't2', name: 'Maven Compile', type: 'shell', config: { command: 'mvn clean compile' } }
          ]
        },
        {
          id: 'test',
          name: '单元测试',
          parallel: false,
          when: { condition: 'success', expression: '' },
          tasks: [
            { id: 't3', name: 'JUnit Test', type: 'test', config: {} }
          ]
        },
        {
          id: 'quality',
          name: '代码质量',
          parallel: false,
          when: { condition: 'success', expression: '' },
          tasks: [
            { id: 't4', name: 'SonarQube Scan', type: 'shell', config: { command: 'mvn sonar:sonar' } }
          ]
        },
        {
          id: 'package',
          name: '打包制品',
          parallel: false,
          when: { condition: 'success', expression: '' },
          tasks: [
            { id: 't5', name: 'Maven Package', type: 'shell', config: { command: 'mvn package -DskipTests' } }
          ]
        },
        {
          id: 'deploy',
          name: '部署发布',
          parallel: false,
          when: { condition: 'expression', expression: "env.BRANCH_NAME == 'main'" },
          tasks: [
            { id: 't6', name: 'Docker Build & Push', type: 'docker', config: {} }
          ]
        }
      ],
      envVariables: [
        { key: 'JAVA_VERSION', value: '17', description: 'JDK版本' },
        { key: 'MAVEN_OPTS', value: '-Xmx1024m', description: 'Maven参数' }
      ]
    },
    {
      id: 'node-npm',
      name: 'Node.js NPM 流水线',
      category: 'Node',
      icon: 'Box',
      description: 'Node.js项目标准流水线，包含依赖安装、代码检查、单元测试、构建、发布',
      tags: ['NPM', 'ESLint', 'Jest', 'Nginx'],
      stages: [
        {
          id: 'checkout',
          name: '代码检出',
          parallel: false,
          when: { condition: 'always', expression: '' },
          tasks: [
            { id: 't1', name: 'Git Clone', type: 'git', config: { branch: 'main' } }
          ]
        },
        {
          id: 'install',
          name: '依赖安装',
          parallel: false,
          when: { condition: 'success', expression: '' },
          tasks: [
            { id: 't2', name: 'NPM Install', type: 'npm', config: { command: 'install' } }
          ]
        },
        {
          id: 'lint',
          name: '代码检查',
          parallel: false,
          when: { condition: 'success', expression: '' },
          tasks: [
            { id: 't3', name: 'ESLint Check', type: 'npm', config: { command: 'run lint' } }
          ]
        },
        {
          id: 'test',
          name: '单元测试',
          parallel: false,
          when: { condition: 'success', expression: '' },
          tasks: [
            { id: 't4', name: 'Jest Test', type: 'npm', config: { command: 'test' } }
          ]
        },
        {
          id: 'build',
          name: '项目构建',
          parallel: false,
          when: { condition: 'success', expression: '' },
          tasks: [
            { id: 't5', name: 'NPM Build', type: 'npm', config: { command: 'build' } }
          ]
        },
        {
          id: 'deploy',
          name: '部署发布',
          parallel: false,
          when: { condition: 'branch', branch: 'main' },
          tasks: [
            { id: 't6', name: 'NPM Publish', type: 'npm', config: { command: 'publish' } }
          ]
        }
      ],
      envVariables: [
        { key: 'NODE_VERSION', value: '18', description: 'Node.js版本' },
        { key: 'NPM_REGISTRY', value: 'https://registry.npmjs.org', description: 'NPM仓库地址' }
      ]
    },
    {
      id: 'python-pip',
      name: 'Python Pip 流水线',
      category: 'Python',
      icon: 'Files',
      description: 'Python项目标准流水线，包含虚拟环境、依赖安装、代码规范检查、单元测试、打包发布',
      tags: ['Pip', 'Flake8', 'PyTest', 'PyPI'],
      stages: [
        {
          id: 'checkout',
          name: '代码检出',
          parallel: false,
          when: { condition: 'always', expression: '' },
          tasks: [
            { id: 't1', name: 'Git Clone', type: 'git', config: { branch: 'main' } }
          ]
        },
        {
          id: 'venv',
          name: '虚拟环境',
          parallel: false,
          when: { condition: 'success', expression: '' },
          tasks: [
            { id: 't2', name: 'Create Venv', type: 'shell', config: { command: 'python -m venv venv' } }
          ]
        },
        {
          id: 'install',
          name: '依赖安装',
          parallel: false,
          when: { condition: 'success', expression: '' },
          tasks: [
            { id: 't3', name: 'Pip Install', type: 'shell', config: { command: 'pip install -r requirements.txt' } }
          ]
        },
        {
          id: 'lint',
          name: '代码检查',
          parallel: false,
          when: { condition: 'success', expression: '' },
          tasks: [
            { id: 't4', name: 'Flake8 Lint', type: 'shell', config: { command: 'flake8 .' } }
          ]
        },
        {
          id: 'test',
          name: '单元测试',
          parallel: false,
          when: { condition: 'success', expression: '' },
          tasks: [
            { id: 't5', name: 'PyTest', type: 'test', config: {} }
          ]
        },
        {
          id: 'package',
          name: '打包发布',
          parallel: false,
          when: { condition: 'branch', branch: 'main' },
          tasks: [
            { id: 't6', name: 'Build & Upload', type: 'shell', config: { command: 'python setup.py sdist upload' } }
          ]
        }
      ],
      envVariables: [
        { key: 'PYTHON_VERSION', value: '3.10', description: 'Python版本' },
        { key: 'PIP_INDEX_URL', value: 'https://pypi.org/simple', description: 'Pypi镜像地址' }
      ]
    },
    {
      id: 'microservice',
      name: '微服务并行流水线',
      category: '通用',
      icon: 'Link',
      description: '微服务架构的并行构建流水线，支持多服务同时构建',
      tags: ['微服务', '并行构建', 'Docker', 'K8s'],
      stages: [
        {
          id: 'checkout',
          name: '代码检出',
          parallel: false,
          when: { condition: 'always', expression: '' },
          tasks: [
            { id: 't1', name: 'Git Clone', type: 'git', config: { branch: 'main' } }
          ]
        },
        {
          id: 'parallel-build',
          name: '并行构建',
          parallel: true,
          when: { condition: 'success', expression: '' },
          parallelStages: [
            {
              id: 'ps1',
              name: '服务A构建',
              tasks: [{ id: 'pt1', name: 'Service A Build', type: 'shell', config: { command: 'cd service-a && mvn package' } }]
            },
            {
              id: 'ps2',
              name: '服务B构建',
              tasks: [{ id: 'pt2', name: 'Service B Build', type: 'npm', config: { command: 'build' } }]
            },
            {
              id: 'ps3',
              name: '服务C构建',
              tasks: [{ id: 'pt3', name: 'Service C Build', type: 'shell', config: { command: 'cd service-c && go build' } }]
            }
          ],
          tasks: []
        },
        {
          id: 'deploy',
          name: '统一部署',
          parallel: false,
          when: { condition: 'success', expression: '' },
          tasks: [
            { id: 't6', name: 'K8s Deploy', type: 'deploy', config: {} }
          ]
        }
      ],
      envVariables: [
        { key: 'K8S_NAMESPACE', value: 'production', description: 'K8s命名空间' }
      ]
    }
  ])

  const categories = computed(() => {
    const cats = new Set(templates.value.map(t => t.category))
    return Array.from(cats)
  })

  const getTemplateById = (id) => {
    return templates.value.find(t => t.id === id)
  }

  const getTemplatesByCategory = (category) => {
    if (!category) return templates.value
    return templates.value.filter(t => t.category === category)
  }

  const applyTemplate = (pipelineStore, templateId) => {
    const template = getTemplateById(templateId)
    if (template) {
      pipelineStore.stages = cloneDeep(template.stages)
      pipelineStore.envVariables = cloneDeep(template.envVariables)
      return true
    }
    return false
  }

  return {
    templates,
    categories,
    getTemplateById,
    getTemplatesByCategory,
    applyTemplate
  }
})
