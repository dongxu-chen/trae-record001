import axios from 'axios'

const jenkinsApi = {
  client: null,
  crumb: null,
  config: null,

  init(config) {
    this.config = config
    this.client = axios.create({
      baseURL: config.url || '/jenkins',
      auth: {
        username: config.username || '',
        password: config.token || ''
      },
      headers: {
        'Content-Type': 'application/json'
      },
      withCredentials: true
    })

    this.client.interceptors.request.use(async (request) => {
      if (this.crumb && request.method !== 'get') {
        request.headers[this.crumb.crumbRequestField] = this.crumb.crumb
      }
      return request
    })
  },

  async getCrumb() {
    try {
      const response = await this.client.get('/crumbIssuer/api/json')
      this.crumb = response.data
      return this.crumb
    } catch (error) {
      console.warn('获取CSRF crumb失败，可能Jenkins未启用CSRF保护:', error.message)
      return null
    }
  },

  async getJobs() {
    try {
      await this.getCrumb()
      const response = await this.client.get('/api/json?tree=jobs[name,color,lastBuild[number,result]]')
      return response.data
    } catch (error) {
      console.error('获取任务列表失败:', error)
      throw error
    }
  },

  async getJobDetails(jobName) {
    try {
      await this.getCrumb()
      const response = await this.client.get(`/job/${jobName}/api/json?tree=name,displayName,healthReport[description,score],lastBuild[number,result,timestamp,duration,building],builds[number,result,timestamp,duration,building]{0,20},actions[parameterDefinitions[name,type,defaultParameterValue[value]]]`)
      return response.data
    } catch (error) {
      console.error('获取任务详情失败:', error)
      throw error
    }
  },

  async buildJob(jobName, params = {}) {
    try {
      await this.getCrumb()
      const hasParams = Object.keys(params).length > 0
      const url = hasParams 
        ? `/job/${jobName}/buildWithParameters`
        : `/job/${jobName}/build`
      
      const response = await this.client.post(url, null, {
        params: hasParams ? params : {}
      })
      return response.data
    } catch (error) {
      console.error('触发构建失败:', error)
      throw error
    }
  },

  async getBuildConsole(jobName, buildNumber) {
    try {
      await this.getCrumb()
      const response = await this.client.get(`/job/${jobName}/${buildNumber}/consoleText`)
      return response.data
    } catch (error) {
      console.error('获取控制台输出失败:', error)
      throw error
    }
  },

  async validateJenkinsfile(jenkinsfile) {
    try {
      await this.getCrumb()
      const response = await this.client.post('/pipeline-model-converter/validate', {
        jenkinsfile: jenkinsfile
      })
      return response.data
    } catch (error) {
      console.error('验证Jenkinsfile失败:', error)
      throw error
    }
  }
}

export default jenkinsApi
