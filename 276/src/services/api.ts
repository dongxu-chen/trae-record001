import { Board, Task, TaskStatus, Priority } from '@/types';

const API_BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export const boardApi = {
  getAll: () => request<Board[]>('/boards'),
  get: (id: string) => request<Board>(`/boards/${id}`),
  create: (data: { name: string; description: string }) =>
    request<Board>('/boards', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  update: (id: string, data: { name: string; description: string }) =>
    request<Board>(`/boards/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request(`/boards/${id}`, { method: 'DELETE' }),
  getTasks: (id: string) => request<Task[]>(`/boards/${id}/tasks`),
};

export const taskApi = {
  getAll: (boardId?: string) =>
    request<Task[]>(`/tasks${boardId ? `?boardId=${boardId}` : ''}`),
  get: (id: string) => request<Task>(`/tasks/${id}`),
  create: (data: Partial<Task> & { boardId: string; title: string }) =>
    request<Task>('/tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Partial<Task>) =>
    request<Task>(`/tasks/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request(`/tasks/${id}`, { method: 'DELETE' }),
  updateStatus: (id: string, status: TaskStatus) =>
    request<Task>(`/tasks/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
  updateOrder: (id: string, order: number, status?: TaskStatus) =>
    request<Task>(`/tasks/${id}/order`, {
      method: 'PATCH',
      body: JSON.stringify({ order, status }),
    }),
  addSubTask: (taskId: string, title: string) =>
    request<Task>(`/tasks/${taskId}/subtasks`, {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),
  updateSubTask: (taskId: string, subId: string, data: { title?: string; completed?: boolean }) =>
    request<Task>(`/tasks/${taskId}/subtasks/${subId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  deleteSubTask: (taskId: string, subId: string) =>
    request<Task>(`/tasks/${taskId}/subtasks/${subId}`, {
      method: 'DELETE',
    }),
  addComment: (taskId: string, content: string, author: string) =>
    request<Task>(`/tasks/${taskId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ content, author }),
    }),
  deleteComment: (taskId: string, commentId: string) =>
    request<Task>(`/tasks/${taskId}/comments/${commentId}`, {
      method: 'DELETE',
    }),
};
