import { create } from 'zustand';
import { Board, Task, TaskStatus, TaskFilters, AutomationRule, TaskTemplate } from '@/types';
import { boardApi, taskApi } from '@/services/api';
import { defaultRules } from '@/utils/automationEngine';
import { defaultTemplates, createTaskFromTemplate } from '@/utils/taskTemplates';

interface AppState {
  boards: Board[];
  currentBoard: Board | null;
  tasks: Task[];
  selectedTask: Task | null;
  filters: TaskFilters;
  isLoading: boolean;
  error: string | null;
  
  automationRules: AutomationRule[];
  taskTemplates: TaskTemplate[];
  
  fetchBoards: () => Promise<void>;
  fetchBoard: (id: string) => Promise<void>;
  fetchTasks: (boardId: string) => Promise<void>;
  createBoard: (name: string, description: string) => Promise<Board>;
  deleteBoard: (id: string) => Promise<void>;
  
  createTask: (data: Partial<Task> & { boardId: string; title: string }) => Promise<Task>;
  createTaskFromTemplate: (templateId: string, boardId: string, overrides?: Partial<Task>) => Promise<Task>;
  updateTask: (id: string, data: Partial<Task>) => Promise<void>;
  deleteTask: (id: string) => Promise<void>;
  moveTask: (taskId: string, newStatus: TaskStatus, newOrder: number) => Promise<void>;
  selectTask: (task: Task | null) => void;
  refreshTask: (taskId: string) => Promise<void>;
  
  setFilters: (filters: Partial<TaskFilters>) => void;
  clearFilters: () => void;
  
  getFilteredTasks: () => Task[];
  
  toggleAutomationRule: (ruleId: string) => void;
  addTaskTemplate: (template: TaskTemplate) => void;
  deleteTaskTemplate: (templateId: string) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  boards: [],
  currentBoard: null,
  tasks: [],
  selectedTask: null,
  filters: {
    assignee: '',
    tags: [],
    priority: '',
  },
  isLoading: false,
  error: null,
  automationRules: defaultRules,
  taskTemplates: defaultTemplates,

  fetchBoards: async () => {
    set({ isLoading: true });
    try {
      const boards = await boardApi.getAll();
      set({ boards, isLoading: false, error: null });
    } catch (error) {
      set({ error: '获取看板列表失败', isLoading: false });
    }
  },

  fetchBoard: async (id: string) => {
    set({ isLoading: true });
    try {
      const board = await boardApi.get(id);
      set({ currentBoard: board, isLoading: false, error: null });
    } catch (error) {
      set({ error: '获取看板失败', isLoading: false });
    }
  },

  fetchTasks: async (boardId: string) => {
    set({ isLoading: true });
    try {
      const tasks = await boardApi.getTasks(boardId);
      set({ tasks, isLoading: false, error: null });
    } catch (error) {
      set({ error: '获取任务列表失败', isLoading: false });
    }
  },

  createBoard: async (name, description) => {
    const board = await boardApi.create({ name, description });
    set((state) => ({ boards: [board, ...state.boards] }));
    return board;
  },

  deleteBoard: async (id) => {
    await boardApi.delete(id);
    set((state) => ({ boards: state.boards.filter((b) => b._id !== id) }));
  },

  createTask: async (data) => {
    const task = await taskApi.create(data);
    set((state) => ({ tasks: [...state.tasks, task] }));
    return task;
  },

  updateTask: async (id, data) => {
    const updatedTask = await taskApi.update(id, data);
    set((state) => ({
      tasks: state.tasks.map((t) => (t._id === id ? updatedTask : t)),
      selectedTask: state.selectedTask?._id === id ? updatedTask : state.selectedTask,
    }));
  },

  deleteTask: async (id) => {
    await taskApi.delete(id);
    set((state) => ({
      tasks: state.tasks.filter((t) => t._id !== id),
      selectedTask: state.selectedTask?._id === id ? null : state.selectedTask,
    }));
  },

  moveTask: async (taskId, newStatus, newOrder) => {
    const updatedTask = await taskApi.updateOrder(taskId, newOrder, newStatus);
    set((state) => ({
      tasks: state.tasks.map((t) => (t._id === taskId ? updatedTask : t)),
    }));
  },

  selectTask: (task) => {
    set({ selectedTask: task });
  },

  refreshTask: async (taskId) => {
    const task = await taskApi.get(taskId);
    set((state) => ({
      tasks: state.tasks.map((t) => (t._id === taskId ? task : t)),
      selectedTask: state.selectedTask?._id === taskId ? task : state.selectedTask,
    }));
  },

  setFilters: (filters) => {
    set((state) => ({ filters: { ...state.filters, ...filters } }));
  },

  clearFilters: () => {
    set({ filters: { assignee: '', tags: [], priority: '' } });
  },

  getFilteredTasks: () => {
    const { tasks, filters } = get();
    return tasks.filter((task) => {
      if (filters.assignee && task.assignee !== filters.assignee) {
        return false;
      }
      if (filters.priority && task.priority !== filters.priority) {
        return false;
      }
      if (filters.tags.length > 0) {
        const hasTag = filters.tags.some((tag) => task.tags.includes(tag));
        if (!hasTag) return false;
      }
      return true;
    });
  },

  toggleAutomationRule: (ruleId) => {
    set((state) => ({
      automationRules: state.automationRules.map((rule) =>
        rule._id === ruleId
          ? { ...rule, enabled: !rule.enabled, updatedAt: new Date().toISOString() }
          : rule
      ),
    }));
  },

  addTaskTemplate: (template) => {
    set((state) => ({
      taskTemplates: [...state.taskTemplates, template],
    }));
  },

  deleteTaskTemplate: (templateId) => {
    set((state) => ({
      taskTemplates: state.taskTemplates.filter((t) => t._id !== templateId),
    }));
  },

  createTaskFromTemplate: async (templateId, boardId, overrides) => {
    const { taskTemplates } = get();
    const template = taskTemplates.find((t) => t._id === templateId);
    if (!template) {
      throw new Error('Template not found');
    }
    const taskData = createTaskFromTemplate(template, boardId, overrides);
    const task = await taskApi.create(taskData);
    set((state) => ({ tasks: [...state.tasks, task] }));
    return task;
  },
}));
