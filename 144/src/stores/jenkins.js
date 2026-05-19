import { defineStore } from 'pinia'
import { ref } from 'vue'
import jenkinsApi from '@/api/jenkins'

export const useJenkinsStore = defineStore('jenkins', () => {
  const config = ref({
    url: '',
    username: '',
    token: ''
  })

  const jobs = ref([
    { name: 'frontend-app', color: 'blue', lastBuild: { number: 42, result: 'SUCCESS' } },
    { name: 'backend-service', color: 'red', lastBuild: { number: 128, result: 'FAILURE' } },
    { name: 'mobile-app', color: 'blue_anime', lastBuild: { number: 15, result: 'BUILDING' } },
    { name: 'deploy-scripts', color: 'blue', lastBuild: { number: 8, result: 'SUCCESS' } }
  ])

  const isConnected = ref(false)

  const connect = async (settings) => {
    config.value = settings
    try {
      jenkinsApi.init(settings)
      const data = await jenkinsApi.getJobs()
      jobs.value = data.jobs || []
      isConnected.value = true
      return true
    } catch (error) {
      console.error('Jenkins连接失败:', error)
      return false
    }
  }

  const buildJob = async (jobName, params = {}) => {
    try {
      await jenkinsApi.buildJob(jobName, params)
      return true
    } catch (error) {
      console.error('触发构建失败:', error)
      return false
    }
  }

  const getJobDetails = async (jobName) => {
    try {
      return await jenkinsApi.getJobDetails(jobName)
    } catch (error) {
      console.error('获取任务详情失败:', error)
      return null
    }
  }

  return {
    config,
    jobs,
    isConnected,
    connect,
    buildJob,
    getJobDetails
  }
})
