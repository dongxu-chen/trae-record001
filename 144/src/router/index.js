import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/layout/index.vue'

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/pipeline',
    children: [
      {
        path: 'pipeline',
        name: 'Pipeline',
        component: () => import('@/views/PipelineEditor.vue'),
        meta: { title: '流水线编辑器' }
      },
      {
        path: 'templates',
        name: 'Templates',
        component: () => import('@/views/Templates.vue'),
        meta: { title: '模板市场' }
      },
      {
        path: 'pipelines',
        name: 'Pipelines',
        component: () => import('@/views/PipelineRuns.vue'),
        meta: { title: '流水线运行' }
      },
      {
        path: 'triggers',
        name: 'Triggers',
        component: () => import('@/views/Triggers.vue'),
        meta: { title: 'GitOps触发器' }
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('@/views/Tasks.vue'),
        meta: { title: '任务库' }
      },
      {
        path: 'analytics',
        name: 'Analytics',
        component: () => import('@/views/Analytics.vue'),
        meta: { title: '趋势分析' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/Settings.vue'),
        meta: { title: '系统设置' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
