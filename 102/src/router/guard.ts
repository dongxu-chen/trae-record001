import type { Router, RouteLocationNormalized, NavigationGuardNext } from 'vue-router'

const TOKEN_KEY = 'auth_token'
const TOKEN_EXPIRE_KEY = 'token_expire_time'
const USER_INFO_KEY = 'user_info'

export interface UserInfo {
  id: number
  username: string
  avatar?: string
  roles: string[]
}

let isFetchingUser = false
let pendingNext: NavigationGuardNext | null = null
let userPromise: Promise<UserInfo | null> | null = null

export const authGuard = (to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
  console.log(`[RouterGuard] Navigating: ${from.path} -> ${to.path}`)
  console.log(`[RouterGuard] Requires auth: ${to.meta.requiresAuth}`)

  const isPublicRoute = to.meta.requiresAuth !== true

  if (isPublicRoute) {
    console.log('[RouterGuard] Public route, allowing access')
    next()
    return
  }

  const token = getToken()
  
  if (!token) {
    console.log('[RouterGuard] No token found, redirecting to login')
    next({
      name: 'Login',
      query: { redirect: to.fullPath }
    })
    return
  }

  if (isTokenExpired()) {
    console.log('[RouterGuard] Token expired, redirecting to login')
    clearAuth()
    next({
      name: 'Login',
      query: { redirect: to.fullPath }
    })
    return
  }

  const userInfo = getUserInfo()
  
  if (userInfo) {
    console.log('[RouterGuard] User info found in cache, checking roles')
    if (checkRoutePermission(to, userInfo)) {
      next()
    } else {
      console.log('[RouterGuard] Permission denied')
      next({ name: '403' })
    }
    return
  }

  if (isFetchingUser) {
    console.log('[RouterGuard] Already fetching user, queuing navigation')
    pendingNext = next
    return
  }

  console.log('[RouterGuard] Fetching user info...')
  fetchUserInfo(token, to, next)
}

export const checkRoutePermission = (to: RouteLocationNormalized, user: UserInfo): boolean => {
  const requiredRoles = to.meta.roles as string[] | undefined
  
  if (!requiredRoles || requiredRoles.length === 0) {
    return true
  }

  return requiredRoles.some(role => user.roles.includes(role))
}

export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY)
}

export const getTokenExpireTime = (): number | null => {
  const expireStr = localStorage.getItem(TOKEN_EXPIRE_KEY)
  return expireStr ? parseInt(expireStr, 10) : null
}

export const isTokenExpired = (): boolean => {
  const expireTime = getTokenExpireTime()
  if (!expireTime) {
    return false
  }
  const isExpired = Date.now() > expireTime
  console.log(`[RouterGuard] Token expire check: now=${Date.now()}, expire=${expireTime}, expired=${isExpired}`)
  return isExpired
}

export const getUserInfo = (): UserInfo | null => {
  const userStr = localStorage.getItem(USER_INFO_KEY)
  if (!userStr) {
    return null
  }
  try {
    return JSON.parse(userStr)
  } catch {
    return null
  }
}

export const fetchUserInfo = (token: string, to: RouteLocationNormalized, next: NavigationGuardNext): void => {
  isFetchingUser = true
  pendingNext = next

  if (!userPromise) {
    userPromise = new Promise((resolve) => {
      setTimeout(() => {
        const mockUser: UserInfo = {
          id: 1,
          username: 'admin',
          roles: ['admin', 'user']
        }
        localStorage.setItem(USER_INFO_KEY, JSON.stringify(mockUser))
        console.log('[RouterGuard] User info fetched successfully')
        resolve(mockUser)
      }, 500)
    })
  }

  userPromise.then((user) => {
    isFetchingUser = false
    userPromise = null

    const currentNext = pendingNext
    pendingNext = null

    if (currentNext) {
      if (user && checkRoutePermission(to, user)) {
        currentNext()
      } else {
        currentNext({ name: '403' })
      }
    }
  }).catch((error) => {
    console.error('[RouterGuard] Fetch user error:', error)
    isFetchingUser = false
    userPromise = null
    clearAuth()
    
    const currentNext = pendingNext
    pendingNext = null
    
    if (currentNext) {
      currentNext({
        name: 'Login',
        query: { redirect: to.fullPath }
      })
    }
  })
}

export const clearAuth = (): void => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(TOKEN_EXPIRE_KEY)
  localStorage.removeItem(USER_INFO_KEY)
}

export const setupRouterGuard = (router: Router): void => {
  router.beforeEach((to, from, next) => {
    authGuard(to, from, next)
  })

  router.afterEach(() => {
    console.log('[RouterGuard] Navigation completed')
  })
}

export const setAuthToken = (token: string, expireInSeconds: number, user?: UserInfo): void => {
  const expireTime = Date.now() + (expireInSeconds * 1000)
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(TOKEN_EXPIRE_KEY, expireTime.toString())
  if (user) {
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(user))
  }
  console.log(`[RouterGuard] Token set, expires at: ${new Date(expireTime).toLocaleString()}`)
}
