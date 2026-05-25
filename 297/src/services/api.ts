import { Project, Annotation, Statistics, User } from '@/types'

const API_BASE = '/api'

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem('token')
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`)
  }

  return response.json()
}

export const authApi = {
  login: async (username: string, password: string) => {
    const res = await request<{ user: User; token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    return res
  },
}

export const projectApi = {
  getAll: async () => {
    return request<Project[]>('/projects')
  },
  getById: async (id: string) => {
    return request<Project>(`/projects/${id}`)
  },
  create: async (data: { name: string; description: string }) => {
    return request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
  uploadPointCloud: async (projectId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const token = localStorage.getItem('token')
    
    const response = await fetch(`${API_BASE}/projects/${projectId}/upload`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    return response.json()
  },
}

export const annotationApi = {
  getByProjectId: async (projectId: string) => {
    return request<Annotation[]>(`/annotations/${projectId}`)
  },
  create: async (projectId: string, annotation: Omit<Annotation, 'id' | 'createdAt' | 'updatedAt'>) => {
    return request<Annotation>(`/annotations/${projectId}`, {
      method: 'POST',
      body: JSON.stringify(annotation),
    })
  },
  delete: async (projectId: string, annotationId: string) => {
    return request(`/annotations/${projectId}/${annotationId}`, {
      method: 'DELETE',
    })
  },
  export: async (projectId: string, format: 'json' | 'las') => {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/annotations/${projectId}/export?format=${format}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `annotations_${projectId}.${format}`
    a.click()
    window.URL.revokeObjectURL(url)
  },
}

export const statisticsApi = {
  getByProjectId: async (projectId: string) => {
    return request<Statistics>(`/statistics/${projectId}`)
  },
}
