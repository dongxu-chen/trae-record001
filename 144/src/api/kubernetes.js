import axios from 'axios'

class KubernetesClient {
  constructor() {
    this.baseURL = '/k8s-api'
    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'Content-Type': 'application/json'
      }
    })
  }

  setAuthToken(token) {
    this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`
  }

  async getNamespaces() {
    try {
      const response = await this.client.get('/api/v1/namespaces')
      return response.data.items.map(item => item.metadata.name)
    } catch (error) {
      console.error('Failed to get namespaces:', error)
      return ['default']
    }
  }

  async listTasks(namespace = 'default') {
    try {
      const response = await this.client.get(`/apis/tekton.dev/v1beta1/namespaces/${namespace}/tasks`)
      return response.data.items
    } catch (error) {
      console.error('Failed to list tasks:', error)
      return []
    }
  }

  async createTask(namespace, taskYAML) {
    try {
      const response = await this.client.post(
        `/apis/tekton.dev/v1beta1/namespaces/${namespace}/tasks`,
        taskYAML,
        { headers: { 'Content-Type': 'application/yaml' } }
      )
      return response.data
    } catch (error) {
      console.error('Failed to create task:', error)
      throw error
    }
  }

  async deleteTask(namespace, taskName) {
    try {
      const response = await this.client.delete(
        `/apis/tekton.dev/v1beta1/namespaces/${namespace}/tasks/${taskName}`
      )
      return response.data
    } catch (error) {
      console.error('Failed to delete task:', error)
      throw error
    }
  }

  async listPipelines(namespace = 'default') {
    try {
      const response = await this.client.get(`/apis/tekton.dev/v1beta1/namespaces/${namespace}/pipelines`)
      return response.data.items
    } catch (error) {
      console.error('Failed to list pipelines:', error)
      return []
    }
  }

  async createPipeline(namespace, pipelineYAML) {
    try {
      const response = await this.client.post(
        `/apis/tekton.dev/v1beta1/namespaces/${namespace}/pipelines`,
        pipelineYAML,
        { headers: { 'Content-Type': 'application/yaml' } }
      )
      return response.data
    } catch (error) {
      console.error('Failed to create pipeline:', error)
      throw error
    }
  }

  async deletePipeline(namespace, pipelineName) {
    try {
      const response = await this.client.delete(
        `/apis/tekton.dev/v1beta1/namespaces/${namespace}/pipelines/${pipelineName}`
      )
      return response.data
    } catch (error) {
      console.error('Failed to delete pipeline:', error)
      throw error
    }
  }

  async listPipelineRuns(namespace = 'default') {
    try {
      const response = await this.client.get(`/apis/tekton.dev/v1beta1/namespaces/${namespace}/pipelineruns`)
      return response.data.items
    } catch (error) {
      console.error('Failed to list pipeline runs:', error)
      return []
    }
  }

  async createPipelineRun(namespace, pipelineRunYAML) {
    try {
      const response = await this.client.post(
        `/apis/tekton.dev/v1beta1/namespaces/${namespace}/pipelineruns`,
        pipelineRunYAML,
        { headers: { 'Content-Type': 'application/yaml' } }
      )
      return response.data
    } catch (error) {
      console.error('Failed to create pipeline run:', error)
      throw error
    }
  }

  async deletePipelineRun(namespace, runName) {
    try {
      const response = await this.client.delete(
        `/apis/tekton.dev/v1beta1/namespaces/${namespace}/pipelineruns/${runName}`
      )
      return response.data
    } catch (error) {
      console.error('Failed to delete pipeline run:', error)
      throw error
    }
  }

  async getPipelineRunLogs(namespace, runName) {
    try {
      const response = await this.client.get(
        `/apis/tekton.dev/v1beta1/namespaces/${namespace}/pipelineruns/${runName}/log`
      )
      return response.data
    } catch (error) {
      console.error('Failed to get pipeline run logs:', error)
      return ''
    }
  }

  async listEventListeners(namespace = 'default') {
    try {
      const response = await this.client.get(`/apis/triggers.tekton.dev/v1beta1/namespaces/${namespace}/eventlisteners`)
      return response.data.items
    } catch (error) {
      console.error('Failed to list event listeners:', error)
      return []
    }
  }

  async createEventListener(namespace, elYAML) {
    try {
      const response = await this.client.post(
        `/apis/triggers.tekton.dev/v1beta1/namespaces/${namespace}/eventlisteners`,
        elYAML,
        { headers: { 'Content-Type': 'application/yaml' } }
      )
      return response.data
    } catch (error) {
      console.error('Failed to create event listener:', error)
      throw error
    }
  }

  async listTriggerBindings(namespace = 'default') {
    try {
      const response = await this.client.get(`/apis/triggers.tekton.dev/v1beta1/namespaces/${namespace}/triggerbindings`)
      return response.data.items
    } catch (error) {
      console.error('Failed to list trigger bindings:', error)
      return []
    }
  }

  async listTriggerTemplates(namespace = 'default') {
    try {
      const response = await this.client.get(`/apis/triggers.tekton.dev/v1beta1/namespaces/${namespace}/triggertemplates`)
      return response.data.items
    } catch (error) {
      console.error('Failed to list trigger templates:', error)
      return []
    }
  }

  async checkTektonInstalled() {
    try {
      const response = await this.client.get('/apis/tekton.dev')
      return response.status === 200
    } catch (error) {
      console.error('Tekton not installed:', error)
      return false
    }
  }

  async checkTriggersInstalled() {
    try {
      const response = await this.client.get('/apis/triggers.tekton.dev')
      return response.status === 200
    } catch (error) {
      console.error('Tekton Triggers not installed:', error)
      return false
    }
  }

  async watchPipelineRuns(namespace = 'default', onMessage) {
    const eventSource = new EventSource(`${this.baseURL}/apis/tekton.dev/v1beta1/namespaces/${namespace}/pipelineruns?watch=true`)
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (e) {
        console.error('Failed to parse watch event:', e)
      }
    }
    eventSource.onerror = (error) => {
      console.error('Watch error:', error)
      eventSource.close()
    }
    return eventSource
  }
}

export const k8sClient = new KubernetesClient()

export default k8sClient
