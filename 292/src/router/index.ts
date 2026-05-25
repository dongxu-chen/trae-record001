import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Designer',
    component: () => import('@/pages/Designer.vue')
  },
  {
    path: '/preview',
    name: 'Preview',
    component: () => import('@/pages/Preview.vue')
  },
  {
    path: '/schema',
    name: 'SchemaView',
    component: () => import('@/pages/SchemaView.vue')
  },
  {
    path: '/approval',
    name: 'Approval',
    component: () => import('@/pages/Approval.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
