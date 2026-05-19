import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { guest: true }
  },
  {
    path: '/',
    component: () => import('@/layouts/Default.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue')
      },
      {
        path: 'forms',
        name: 'Forms',
        component: () => import('@/views/Forms/Index.vue')
      },
      {
        path: 'forms/create',
        name: 'CreateForm',
        component: () => import('@/views/Forms/Builder.vue')
      },
      {
        path: 'forms/:id/edit',
        name: 'EditForm',
        component: () => import('@/views/Forms/Builder.vue')
      },
      {
        path: 'forms/:id',
        name: 'ViewForm',
        component: () => import('@/views/Forms/View.vue')
      },
      {
        path: 'submissions',
        name: 'Submissions',
        component: () => import('@/views/Submissions/Index.vue')
      },
      {
        path: 'approvals',
        name: 'Approvals',
        component: () => import('@/views/Approvals/Index.vue')
      },
      {
        path: 'approval-flows',
        name: 'ApprovalFlows',
        component: () => import('@/views/ApprovalFlows/Index.vue')
      },
      {
        path: 'approval-flows/create',
        name: 'CreateApprovalFlow',
        component: () => import('@/views/ApprovalFlows/Form.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.guest && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
