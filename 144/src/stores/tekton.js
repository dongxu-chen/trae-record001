import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { cloneDeep } from 'lodash-es'
import YAML from 'yaml'

export const useTektonStore = defineStore('tekton', () => {
  const namespace = ref('default')
const tasks = ref([
  {
    id: 'task-git-clone',
    name: 'git-clone',
    description: 'Clone a git repository',
    category: 'git',
    params: [
      { name: 'url', type: 'string', description: 'Git repository URL', default: '' },
      { name: 'revision', type: 'string', description: 'Git revision', default: 'main' }
    ],
    workspaces: [{ name: 'output', description: 'Workspace for cloned code' }],
    steps: [
      {
        name: 'clone',
        image: 'alpine/git:latest',
        script: 'git clone -b $(params.revision) $(params.url) $(workspaces.output.path)'
      }
    ]
  },
  {
    id: 'task-npm',
    name: 'npm',
    description: 'Run npm commands',
    category: 'nodejs',
    params: [
      { name: 'command', type: 'string', description: 'npm command', default: 'install' }
    ],
    workspaces: [{ name: 'source', description: 'Source code workspace' }],
    steps: [
      {
        name: 'npm',
        image: 'node:18-alpine',
        script: 'cd $(workspaces.source.path) && npm $(params.command)'
      }
    ]
  },
  {
    id: 'task-maven',
    name: 'maven',
    description: 'Run maven commands',
    category: 'java',
    params: [
      { name: 'goals', type: 'string', description: 'Maven goals', default: 'clean install' }
    ],
    workspaces: [{ name: 'source', description: 'Source code workspace' }],
    steps: [
      {
        name: 'maven',
        image: 'maven:3.9-eclipse-temurin-17',
        script: 'cd $(workspaces.source.path) && mvn $(params.goals)'
      }
    ]
  },
  {
    id: 'task-docker-build',
    name: 'docker-build',
    description: 'Build and push docker image',
    category: 'docker',
    params: [
      { name: 'image', type: 'string', description: 'Image name', default: '' },
      { name: 'tag', type: 'string', description: 'Image tag', default: 'latest' }
    ],
    workspaces: [{ name: 'source', description: 'Source code workspace' }],
    steps: [
      {
        name: 'build',
        image: 'gcr.io/kaniko-project/executor:v1.9.0',
        script: '/kaniko/executor --dockerfile=$(workspaces.source.path)/Dockerfile --context=$(workspaces.source.path) --destination=$(params.image):$(params.tag)'
      }
    ]
  },
  {
    id: 'task-kubectl',
    name: 'kubectl',
    description: 'Apply Kubernetes manifests',
    category: 'k8s',
    params: [
      { name: 'command', type: 'string', description: 'kubectl command', default: 'apply -f deployment.yaml' },
      { name: 'namespace', type: 'string', description: 'Kubernetes namespace', default: 'default' }
    ],
    workspaces: [{ name: 'manifest', description: 'Manifest files workspace' }],
    steps: [
      {
        name: 'kubectl',
        image: 'bitnami/kubectl:latest',
        script: 'cd $(workspaces.manifest.path) && kubectl $(params.command) -n $(params.namespace)'
      }
    ]
  }
])

  const pipelines = ref([
    {
      id: 'pipeline-sample',
      name: 'sample-pipeline',
      description: 'Sample CI/CD pipeline',
      params: [
        { name: 'git-url', type: 'string', default: '' },
        { name: 'git-revision', type: 'string', default: 'main' },
        { name: 'image-name', type: 'string', default: 'myapp' },
        { name: 'image-tag', type: 'string', default: 'latest' }
      ],
      workspaces: [{ name: 'shared-workspace', description: 'Shared workspace for all tasks' }],
      tasks: [
        {
          name: 'fetch-source',
          taskRef: { name: 'git-clone', kind: 'Task' },
          params: [
            { name: 'url', value: '$(params.git-url)' },
            { name: 'revision', value: '$(params.git-revision)' }
          ],
          workspaces: [{ name: 'output', workspace: 'shared-workspace' }]
        },
        {
          name: 'build-app',
          taskRef: { name: 'npm', kind: 'Task' },
          runAfter: ['fetch-source'],
          params: [{ name: 'command', value: 'run build' }],
          workspaces: [{ name: 'source', workspace: 'shared-workspace' }]
        },
        {
          name: 'build-image',
          taskRef: { name: 'docker-build', kind: 'Task' },
          runAfter: ['build-app'],
          params: [
            { name: 'image', value: '$(params.image-name)' },
            { name: 'tag', value: '$(params.image-tag)' }
          ],
          workspaces: [{ name: 'source', workspace: 'shared-workspace' }]
        }
      ]
    }
  ])

  const pipelineRuns = ref([
    {
      id: 'run-1',
      name: 'sample-pipeline-run-1',
      pipelineRef: { name: 'sample-pipeline' },
      params: [
        { name: 'git-url', value: 'https://github.com/example/repo.git' },
        { name: 'git-revision', value: 'main' }
      ],
      workspaces: [{ name: 'shared-workspace', volumeClaimTemplate: { spec: { accessModes: ['ReadWriteOnce'], resources: { requests: { storage: '1Gi' } } } } }],
      status: 'Succeeded',
      startTime: '2024-01-15T10:30:00Z',
      completionTime: '2024-01-15T10:45:00Z',
      results: []
    },
    {
      id: 'run-2',
      name: 'sample-pipeline-run-2',
      pipelineRef: { name: 'sample-pipeline' },
      params: [],
      workspaces: [],
      status: 'Failed',
      startTime: '2024-01-16T09:00:00Z',
      completionTime: '2024-01-16T09:10:00Z',
      results: []
    },
    {
      id: 'run-3',
      name: 'sample-pipeline-run-3',
      pipelineRef: { name: 'sample-pipeline' },
      params: [],
      workspaces: [],
      status: 'Running',
      startTime: '2024-01-17T14:00:00Z',
      completionTime: null,
      results: []
    }
  ])

  const triggers = ref([
    {
      id: 'trigger-github',
      name: 'github-trigger',
      description: 'Trigger pipeline on GitHub push event',
      eventListener: {
        serviceAccountName: 'tekton-triggers-github-sa',
        triggers: [
          {
            name: 'github-push',
            interceptors: [
              { ref: { name: 'github' }, params: [{ name: 'eventTypes', value: ['push'] }] }
            ],
            bindings: [{ ref: { name: 'github-push-binding' } }],
            template: { ref: { name: 'pipeline-template' } }
          }
        ]
      },
      triggerBinding: {
        params: [
          { name: 'git-revision', value: '$(body.head_commit.id)' },
          { name: 'git-url', value: '$(body.repository.clone_url)' },
          { name: 'image-tag', value: '$(body.head_commit.id)' }
        ]
      },
      triggerTemplate: {
        params: [
          { name: 'git-revision' },
          { name: 'git-url' },
          { name: 'image-tag' }
        ],
        pipelineRef: { name: 'sample-pipeline' }
      }
    }
  ])

  const editorPipeline = ref({
    name: 'new-pipeline',
    description: '',
    params: [],
    workspaces: [{ name: 'shared-workspace', description: 'Shared workspace' }],
    tasks: []
  })

  const selectedTask = ref(null)

  const addTaskToPipeline = (taskTemplate) => {
    const newPipelineTask = {
      id: `task-${Date.now()}`,
      name: `${taskTemplate.name}-${editorPipeline.value.tasks.length + 1}`,
      taskRef: { name: taskTemplate.name, kind: 'Task' },
      params: taskTemplate.params.map(p => ({ name: p.name, value: p.default || '' })),
      workspaces: taskTemplate.workspaces.map(w => ({ name: w.name, workspace: 'shared-workspace' })),
      runAfter: []
    }
    editorPipeline.value.tasks.push(newPipelineTask)
  }

  const removeTaskFromPipeline = (taskId) => {
    const index = editorPipeline.value.tasks.findIndex(t => t.id === taskId)
    if (index > -1) {
      editorPipeline.value.tasks.splice(index, 1)
    }
  }

  const updatePipelineTask = (taskId, updates) => {
    const task = editorPipeline.value.tasks.find(t => t.id === taskId)
    if (task) {
      Object.assign(task, updates)
    }
  }

  const addParam = (param) => {
    editorPipeline.value.params.push({
      name: param.name,
      type: param.type || 'string',
      default: param.default || '',
      description: param.description || ''
    })
  }

  const removeParam = (paramName) => {
    const index = editorPipeline.value.params.findIndex(p => p.name === paramName)
    if (index > -1) {
      editorPipeline.value.params.splice(index, 1)
    }
  }

  const generateTaskYAML = (task) => {
    const taskCR = {
      apiVersion: 'tekton.dev/v1beta1',
      kind: 'Task',
      metadata: {
        name: task.name,
        namespace: namespace.value,
        labels: { 'app.kubernetes.io/managed-by': 'tekton-builder' }
      },
      spec: {
        params: task.params.map(p => ({
          name: p.name,
          type: p.type,
          description: p.description,
          default: p.default
        })),
        workspaces: task.workspaces.map(w => ({
          name: w.name,
          description: w.description
        })),
        steps: task.steps
      }
    }
    return YAML.stringify(taskCR, null, 2)
  }

  const generatePipelineYAML = () => {
    const pipeline = editorPipeline.value
    const pipelineCR = {
      apiVersion: 'tekton.dev/v1beta1',
      kind: 'Pipeline',
      metadata: {
        name: pipeline.name,
        namespace: namespace.value,
        labels: { 'app.kubernetes.io/managed-by': 'tekton-builder' }
      },
      spec: {
        params: pipeline.params.map(p => ({
          name: p.name,
          type: p.type,
          default: p.default,
          description: p.description
        })),
        workspaces: pipeline.workspaces.map(w => ({
          name: w.name,
          description: w.description
        })),
        tasks: pipeline.tasks.map(t => ({
          name: t.name,
          taskRef: t.taskRef,
          params: t.params.map(p => ({ name: p.name, value: p.value })),
          workspaces: t.workspaces.map(w => ({ name: w.name, workspace: w.workspace })),
          runAfter: t.runAfter && t.runAfter.length > 0 ? t.runAfter : undefined
        })).filter(Boolean)
      }
    }
    return YAML.stringify(pipelineCR, null, 2)
  }

  const generatePipelineRunYAML = (pipelineName, params = {}) => {
    const pipelineRunCR = {
      apiVersion: 'tekton.dev/v1beta1',
      kind: 'PipelineRun',
      metadata: {
        generateName: `${pipelineName}-run-`,
        namespace: namespace.value,
        labels: { 'app.kubernetes.io/managed-by': 'tekton-builder' }
      },
      spec: {
        pipelineRef: { name: pipelineName },
        params: Object.entries(params).map(([name, value]) => ({ name, value })),
        workspaces: [{
          name: 'shared-workspace',
          volumeClaimTemplate: {
            spec: {
              accessModes: ['ReadWriteOnce'],
              resources: { requests: { storage: '1Gi' } }
            }
          }
        }]
      }
    }
    return YAML.stringify(pipelineRunCR, null, 2)
  }

  const generateTriggerYAML = (trigger) => {
    const eventListenerCR = {
      apiVersion: 'triggers.tekton.dev/v1beta1',
      kind: 'EventListener',
      metadata: { name: trigger.name, namespace: namespace.value },
      spec: {
        serviceAccountName: trigger.eventListener.serviceAccountName,
        triggers: trigger.eventListener.triggers
      }
    }

    const triggerBindingCR = {
      apiVersion: 'triggers.tekton.dev/v1beta1',
      kind: 'TriggerBinding',
      metadata: { name: `${trigger.name}-binding`, namespace: namespace.value },
      spec: { params: trigger.triggerBinding.params }
    }

    const triggerTemplateCR = {
      apiVersion: 'triggers.tekton.dev/v1beta1',
      kind: 'TriggerTemplate',
      metadata: { name: `${trigger.name}-template`, namespace: namespace.value },
      spec: {
        params: trigger.triggerTemplate.params,
        resourcetemplates: [{
          apiVersion: 'tekton.dev/v1beta1',
          kind: 'PipelineRun',
          metadata: { generateName: '$(tt.params.pipeline-name)-run-' },
          spec: {
            pipelineRef: { name: trigger.triggerTemplate.pipelineRef.name },
            params: trigger.triggerTemplate.params.map(p => ({ name: p.name, value: `$(tt.params.${p.name})` })),
            workspaces: [{
              name: 'shared-workspace',
              volumeClaimTemplate: {
                spec: {
                  accessModes: ['ReadWriteOnce'],
                  resources: { requests: { storage: '1Gi' } }
                }
              }
            }]
          }
        }]
      }
    }

    return `# EventListener\n${YAML.stringify(eventListenerCR, null, 2)}\n\n---\n\n# TriggerBinding\n${YAML.stringify(triggerBindingCR, null, 2)}\n\n---\n\n# TriggerTemplate\n${YAML.stringify(triggerTemplateCR, null, 2)}`
  }

  const resetEditorPipeline = () => {
    editorPipeline.value = {
      name: 'new-pipeline',
      description: '',
      params: [],
      workspaces: [{ name: 'shared-workspace', description: 'Shared workspace' }],
      tasks: []
    }
    selectedTask.value = null
  }

  const savePipeline = () => {
    const existing = pipelines.value.findIndex(p => p.name === editorPipeline.value.name)
    const pipelineCopy = cloneDeep(editorPipeline.value)
    if (existing > -1) {
      pipelines.value[existing] = pipelineCopy
    } else {
      pipelineCopy.id = `pipeline-${Date.now()}`
      pipelines.value.push(pipelineCopy)
    }
  }

  const deletePipeline = (pipelineId) => {
    const index = pipelines.value.findIndex(p => p.id === pipelineId)
    if (index > -1) {
      pipelines.value.splice(index, 1)
    }
  }

  const loadPipeline = (pipelineId) => {
    const pipeline = pipelines.value.find(p => p.id === pipelineId)
    if (pipeline) {
      editorPipeline.value = cloneDeep(pipeline)
    }
  }

  const taskStats = computed(() => {
    return {
      total: pipelineRuns.value.length,
      succeeded: pipelineRuns.value.filter(r => r.status === 'Succeeded').length,
      failed: pipelineRuns.value.filter(r => r.status === 'Failed').length,
      running: pipelineRuns.value.filter(r => r.status === 'Running').length,
      successRate: pipelineRuns.value.length > 0
        ? Math.round((pipelineRuns.value.filter(r => r.status === 'Succeeded').length / pipelineRuns.value.length) * 100)
        : 0
    }
  })

  return {
    namespace,
    tasks,
    pipelines,
    pipelineRuns,
    triggers,
    editorPipeline,
    selectedTask,
    taskStats,
    addTaskToPipeline,
    removeTaskFromPipeline,
    updatePipelineTask,
    addParam,
    removeParam,
    generateTaskYAML,
    generatePipelineYAML,
    generatePipelineRunYAML,
    generateTriggerYAML,
    resetEditorPipeline,
    savePipeline,
    deletePipeline,
    loadPipeline
  }
})
