import { defineStore } from 'pinia'
import { ref } from 'vue'
import { cloneDeep } from 'lodash-es'

export const usePipelineStore = defineStore('pipeline', () => {
  const envVariables = ref([
    { key: 'BRANCH_NAME', value: 'main', description: '构建分支' },
    { key: 'BUILD_ENV', value: 'dev', description: '构建环境' }
  ])

  const stages = ref([
    {
      id: 'stage-1',
      name: '代码检出',
      parallel: false,
      when: { condition: 'always', expression: '' },
      tasks: [
        { id: 'task-1-1', name: 'Git Clone', type: 'git', config: { url: '', branch: 'main' } }
      ]
    },
    {
      id: 'stage-2',
      name: '构建与测试',
      parallel: true,
      when: { condition: 'success', expression: '' },
      parallelStages: [
        {
          id: 'parallel-1',
          name: '前端构建',
          tasks: [{ id: 'ptask-1', name: 'NPM Build', type: 'npm', config: { command: 'build' } }]
        },
        {
          id: 'parallel-2',
          name: '后端构建',
          tasks: [{ id: 'ptask-2', name: 'Maven Build', type: 'shell', config: { command: 'mvn clean install' } }]
        }
      ],
      tasks: []
    },
    {
      id: 'stage-3',
      name: '部署',
      parallel: false,
      when: { condition: 'expression', expression: "currentBuild.result == 'SUCCESS'" },
      tasks: [
        { id: 'task-3-1', name: 'Docker部署', type: 'docker', config: {} }
      ]
    }
  ])

  const buildHistory = ref([
    { id: 1, name: '构建 #1', status: 'success', startTime: '2024-01-15 10:30:00', duration: '2m 30s', stages: [{ name: '代码检出', status: 'success' }, { name: '构建与测试', status: 'success' }, { name: '部署', status: 'success' }] },
    { id: 2, name: '构建 #2', status: 'failed', startTime: '2024-01-15 11:00:00', duration: '1m 15s', stages: [{ name: '代码检出', status: 'success' }, { name: '构建与测试', status: 'failed' }, { name: '部署', status: 'pending' }] },
    { id: 3, name: '构建 #3', status: 'running', startTime: '2024-01-15 14:00:00', duration: '进行中', stages: [{ name: '代码检出', status: 'success' }, { name: '构建与测试', status: 'running' }, { name: '部署', status: 'pending' }] }
  ])

  const deepCloneStage = (stage) => {
    return cloneDeep(stage)
  }

  const addStage = (name, options = {}) => {
    const newStage = {
      id: `stage-${Date.now()}`,
      name: name || `阶段 ${stages.value.length + 1}`,
      parallel: options.parallel || false,
      when: { condition: 'success', expression: '' },
      parallelStages: options.parallel ? [] : undefined,
      tasks: options.parallel ? [] : []
    }
    stages.value.push(newStage)
  }

  const removeStage = (stageId) => {
    const index = stages.value.findIndex(s => s.id === stageId)
    if (index > -1) {
      stages.value.splice(index, 1)
    }
  }

  const addTask = (stageId, task, parallelStageId = null) => {
    const stage = stages.value.find(s => s.id === stageId)
    if (stage) {
      const newTask = {
        id: `task-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        ...cloneDeep(task)
      }
      
      if (parallelStageId && stage.parallel && stage.parallelStages) {
        const pStage = stage.parallelStages.find(p => p.id === parallelStageId)
        if (pStage) {
          pStage.tasks.push(newTask)
        }
      } else {
        stage.tasks.push(newTask)
      }
    }
  }

  const removeTask = (stageId, taskId, parallelStageId = null) => {
    const stage = stages.value.find(s => s.id === stageId)
    if (stage) {
      if (parallelStageId && stage.parallel && stage.parallelStages) {
        const pStage = stage.parallelStages.find(p => p.id === parallelStageId)
        if (pStage) {
          const index = pStage.tasks.findIndex(t => t.id === taskId)
          if (index > -1) {
            pStage.tasks.splice(index, 1)
          }
        }
      } else {
        const index = stage.tasks.findIndex(t => t.id === taskId)
        if (index > -1) {
          stage.tasks.splice(index, 1)
        }
      }
    }
  }

  const addParallelStage = (stageId, name) => {
    const stage = stages.value.find(s => s.id === stageId)
    if (stage) {
      if (!stage.parallel) {
        stage.parallel = true
        stage.parallelStages = []
      }
      stage.parallelStages.push({
        id: `parallel-${Date.now()}`,
        name: name || `并行阶段 ${stage.parallelStages.length + 1}`,
        tasks: []
      })
    }
  }

  const removeParallelStage = (stageId, parallelStageId) => {
    const stage = stages.value.find(s => s.id === stageId)
    if (stage && stage.parallelStages) {
      const index = stage.parallelStages.findIndex(p => p.id === parallelStageId)
      if (index > -1) {
        stage.parallelStages.splice(index, 1)
      }
    }
  }

  const updateStages = (newStages) => {
    stages.value = cloneDeep(newStages)
  }

  const updateStageWhen = (stageId, whenConfig) => {
    const stage = stages.value.find(s => s.id === stageId)
    if (stage) {
      stage.when = cloneDeep(whenConfig)
    }
  }

  const addEnvVariable = (key, value, description = '') => {
    envVariables.value.push({ key, value, description })
  }

  const removeEnvVariable = (key) => {
    const index = envVariables.value.findIndex(e => e.key === key)
    if (index > -1) {
      envVariables.value.splice(index, 1)
    }
  }

  const generateJenkinsfile = () => {
    const generateWhenBlock = (when, indent = 6) => {
      const spaces = ' '.repeat(indent)
      if (!when || when.condition === 'always') return ''
      
      let whenBlock = `${spaces}when {\n`
      
      switch (when.condition) {
        case 'success':
          whenBlock += `${spaces}  success()\n`
          break
        case 'failed':
          whenBlock += `${spaces}  failure()\n`
          break
        case 'expression':
          whenBlock += `${spaces}  expression { ${when.expression} }\n`
          break
        case 'branch':
          whenBlock += `${spaces}  branch '${when.branch || 'main'}'\n`
          break
        case 'buildingTag':
          whenBlock += `${spaces}  buildingTag()\n`
          break
        case 'changeRequest':
          whenBlock += `${spaces}  changeRequest()\n`
          break
      }
      
      whenBlock += `${spaces}}\n`
      return whenBlock
    }

    const generateTaskStep = (task, indent = 8) => {
      const spaces = ' '.repeat(indent)
      switch (task.type) {
        case 'git':
          return `${spaces}git url: '${task.config.url || ''}', branch: '${task.config.branch || 'main'}'\n`
        case 'npm':
          return `${spaces}sh 'npm ${task.config.command || 'install'}'\n`
        case 'shell':
          return `${spaces}sh '${task.config.command || 'echo hello'}'\n`
        case 'docker':
          return `${spaces}sh 'docker build -t app:latest .'\n`
        case 'test':
          return `${spaces}sh 'npm test'\n`
        case 'deploy':
          return `${spaces}sh 'kubectl apply -f deployment.yaml'\n`
        default:
          return `${spaces}sh 'echo ${task.name}'\n`
      }
    }

    const generateStageBody = (stage, indent = 4) => {
      const spaces = ' '.repeat(indent)
      let body = ''
      
      body += generateWhenBlock(stage.when, indent + 2)
      body += `${spaces}  steps {\n`
      
      stage.tasks.forEach(task => {
        body += generateTaskStep(task, indent + 4)
      })
      
      body += `${spaces}  }\n`
      return body
    }

    let jenkinsfile = `pipeline {
  agent any
  
  environment {
`

    envVariables.value.forEach(env => {
      jenkinsfile += `    ${env.key} = '${env.value}'\n`
    })

    jenkinsfile += `  }
  
  stages {
`

    stages.value.forEach(stage => {
      jenkinsfile += `    stage('${stage.name}') {\n`
      
      if (stage.parallel && stage.parallelStages && stage.parallelStages.length > 0) {
        jenkinsfile += generateWhenBlock(stage.when, 6)
        jenkinsfile += `      parallel {\n`
        
        stage.parallelStages.forEach(pStage => {
          jenkinsfile += `        stage('${pStage.name}') {\n`
          jenkinsfile += `          steps {\n`
          pStage.tasks.forEach(task => {
            jenkinsfile += generateTaskStep(task, 12)
          })
          jenkinsfile += `          }\n`
          jenkinsfile += `        }\n`
        })
        
        jenkinsfile += `      }\n`
      } else {
        jenkinsfile += generateStageBody(stage, 4)
      }
      
      jenkinsfile += `    }\n`
    })

    jenkinsfile += `  }
  
  post {
    success {
      echo 'Pipeline completed successfully!'
    }
    failure {
      echo 'Pipeline failed!'
    }
  }
}`

    return jenkinsfile
  }

  const triggerBuild = () => {
    const newBuild = {
      id: buildHistory.value.length + 1,
      name: `构建 #${buildHistory.value.length + 1}`,
      status: 'running',
      startTime: new Date().toLocaleString('zh-CN'),
      duration: '进行中',
      stages: stages.value.map(s => ({ name: s.name, status: 'pending' }))
    }
    buildHistory.value.unshift(cloneDeep(newBuild))
    return newBuild
  }

  return {
    stages,
    buildHistory,
    envVariables,
    addStage,
    removeStage,
    addTask,
    removeTask,
    addParallelStage,
    removeParallelStage,
    updateStages,
    updateStageWhen,
    addEnvVariable,
    removeEnvVariable,
    deepCloneStage,
    generateJenkinsfile,
    triggerBuild
  }
})
