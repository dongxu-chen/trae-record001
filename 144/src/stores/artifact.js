import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useArtifactStore = defineStore('artifact', () => {
  const artifacts = ref([
    {
      id: 'artifact-001',
      name: 'frontend-app',
      version: 'v1.2.3',
      type: 'npm',
      buildNumber: 42,
      currentStage: 'prod',
      size: '2.5 MB',
      createdAt: '2024-01-15 10:30:00',
      createdBy: 'admin',
      stages: [
        { name: 'dev', status: 'success', time: '2024-01-15 10:35:00', approver: 'admin' },
        { name: 'test', status: 'success', time: '2024-01-15 14:20:00', approver: 'tester' },
        { name: 'uat', status: 'success', time: '2024-01-16 09:15:00', approver: 'qa-lead' },
        { name: 'prod', status: 'pending', time: null, approver: null }
      ],
      checks: {
        unitTests: { passed: true, coverage: '89%' },
        integrationTests: { passed: true, coverage: '76%' },
        securityScan: { passed: true, vulnerabilities: 0 },
        codeQuality: { passed: true, score: 'A' }
      }
    },
    {
      id: 'artifact-002',
      name: 'backend-service',
      version: 'v2.0.1',
      type: 'jar',
      buildNumber: 128,
      currentStage: 'test',
      size: '45 MB',
      createdAt: '2024-01-14 16:45:00',
      createdBy: 'developer1',
      stages: [
        { name: 'dev', status: 'success', time: '2024-01-14 17:00:00', approver: 'developer1' },
        { name: 'test', status: 'running', time: '2024-01-15 08:30:00', approver: null },
        { name: 'uat', status: 'pending', time: null, approver: null },
        { name: 'prod', status: 'pending', time: null, approver: null }
      ],
      checks: {
        unitTests: { passed: true, coverage: '92%' },
        integrationTests: { passed: false, coverage: '65%' },
        securityScan: { passed: true, vulnerabilities: 2 },
        codeQuality: { passed: true, score: 'B' }
      }
    },
    {
      id: 'artifact-003',
      name: 'mobile-app',
      version: 'v3.0.0-beta',
      type: 'apk',
      buildNumber: 15,
      currentStage: 'dev',
      size: '128 MB',
      createdAt: '2024-01-13 20:00:00',
      createdBy: 'mobile-dev',
      stages: [
        { name: 'dev', status: 'failed', time: '2024-01-13 21:30:00', approver: 'mobile-dev' },
        { name: 'test', status: 'blocked', time: null, approver: null },
        { name: 'uat', status: 'pending', time: null, approver: null },
        { name: 'prod', status: 'pending', time: null, approver: null }
      ],
      checks: {
        unitTests: { passed: false, coverage: '45%' },
        integrationTests: { passed: false, coverage: '30%' },
        securityScan: { passed: false, vulnerabilities: 5 },
        codeQuality: { passed: false, score: 'D' }
      }
    }
  ])

  const pipelineMetrics = ref([
    { date: '2024-01-10', duration: 12, status: 'success', pipeline: 'frontend-app' },
    { date: '2024-01-11', duration: 15, status: 'success', pipeline: 'frontend-app' },
    { date: '2024-01-12', duration: 8, status: 'failed', pipeline: 'frontend-app' },
    { date: '2024-01-13', duration: 18, status: 'success', pipeline: 'frontend-app' },
    { date: '2024-01-14', duration: 14, status: 'success', pipeline: 'frontend-app' },
    { date: '2024-01-15', duration: 11, status: 'success', pipeline: 'frontend-app' },
    { date: '2024-01-10', duration: 25, status: 'success', pipeline: 'backend-service' },
    { date: '2024-01-11', duration: 30, status: 'success', pipeline: 'backend-service' },
    { date: '2024-01-12', duration: 20, status: 'failed', pipeline: 'backend-service' },
    { date: '2024-01-13', duration: 28, status: 'success', pipeline: 'backend-service' },
    { date: '2024-01-14', duration: 22, status: 'success', pipeline: 'backend-service' },
    { date: '2024-01-15', duration: 26, status: 'running', pipeline: 'backend-service' }
  ])

  const prList = ref([
    {
      id: 1,
      title: 'feat: add user authentication module',
      branch: 'feature/auth',
      targetBranch: 'main',
      author: 'john.doe',
      status: 'success',
      buildNumber: 45,
      createdAt: '2024-01-15 09:30:00',
      commits: 5,
      filesChanged: 12,
      checks: { unitTests: true, lint: true, build: true }
    },
    {
      id: 2,
      title: 'fix: resolve database connection timeout',
      branch: 'fix/db-timeout',
      targetBranch: 'main',
      author: 'jane.smith',
      status: 'running',
      buildNumber: 46,
      createdAt: '2024-01-15 11:00:00',
      commits: 2,
      filesChanged: 3,
      checks: { unitTests: true, lint: true, build: null }
    },
    {
      id: 3,
      title: 'docs: update API documentation',
      branch: 'docs/api',
      targetBranch: 'main',
      author: 'doc.writer',
      status: 'failed',
      buildNumber: 44,
      createdAt: '2024-01-15 08:00:00',
      commits: 1,
      filesChanged: 2,
      checks: { unitTests: true, lint: false, build: true }
    }
  ])

  const gitOpsConfig = ref({
    enabled: true,
    provider: 'github',
    repoUrl: 'https://github.com/org/repo',
    webhookSecret: '***',
    autoBuildOnPR: true,
    autoMergeOnSuccess: false,
    requiredChecks: ['unitTests', 'lint', 'build']
  })

  const artifactTypes = computed(() => {
    return [...new Set(artifacts.value.map(a => a.type))]
  })

  const getArtifactsByStage = (stage) => {
    if (!stage) return artifacts.value
    return artifacts.value.filter(a => a.currentStage === stage)
  }

  const getArtifactById = (id) => {
    return artifacts.value.find(a => a.id === id)
  }

  const promoteArtifact = (artifactId, targetStage, approver) => {
    const artifact = getArtifactById(artifactId)
    if (artifact) {
      const stage = artifact.stages.find(s => s.name === targetStage)
      if (stage) {
        stage.status = 'success'
        stage.time = new Date().toLocaleString('zh-CN')
        stage.approver = approver
        artifact.currentStage = targetStage
        return true
      }
    }
    return false
  }

  const getPipelineStats = (pipelineName) => {
    const metrics = pipelineName
      ? pipelineMetrics.value.filter(m => m.pipeline === pipelineName)
      : pipelineMetrics.value

    const avgDuration = metrics.reduce((sum, m) => sum + m.duration, 0) / metrics.length
    const successRate = (metrics.filter(m => m.status === 'success').length / metrics.length) * 100
    const totalRuns = metrics.length

    return {
      avgDuration: avgDuration.toFixed(1),
      successRate: successRate.toFixed(1),
      totalRuns
    }
  }

  const getPRById = (id) => {
    return prList.value.find(p => p.id === id)
  }

  const triggerPRBuild = (prId) => {
    const pr = getPRById(prId)
    if (pr) {
      pr.status = 'running'
      return true
    }
    return false
  }

  return {
    artifacts,
    pipelineMetrics,
    prList,
    gitOpsConfig,
    artifactTypes,
    getArtifactsByStage,
    getArtifactById,
    promoteArtifact,
    getPipelineStats,
    getPRById,
    triggerPRBuild
  }
})
