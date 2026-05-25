import mongoose, { Schema, Document } from 'mongoose';

export type TaskStatus = 'todo' | 'in-progress' | 'done';
export type Priority = 'low' | 'medium' | 'high' | 'urgent';
export type OperationType =
  | 'create'
  | 'update'
  | 'delete'
  | 'status_change'
  | 'subtask_add'
  | 'subtask_remove'
  | 'subtask_complete'
  | 'comment_add'
  | 'comment_remove';

export interface ISubTask {
  _id: string;
  title: string;
  completed: boolean;
  createdAt: Date;
}

export interface IComment {
  _id: string;
  content: string;
  author: string;
  createdAt: Date;
}

export interface IHistoryEntry {
  _id: string;
  field: string;
  oldValue: any;
  newValue: any;
  changedBy: string;
  changedAt: Date;
}

export interface ITaskSnapshot {
  title: string;
  description: string;
  status: TaskStatus;
  priority: Priority;
  assignee: string;
  tags: string[];
  dueDate: Date | null;
  startDate: Date | null;
  subTasks: ISubTask[];
}

export interface IOperationLog {
  _id: string;
  operation: OperationType;
  operator: string;
  timestamp: Date;
  description: string;
  changes?: {
    field: string;
    oldValue: any;
    newValue: any;
  }[];
  snapshotBefore?: ITaskSnapshot;
  snapshotAfter?: ITaskSnapshot;
}

export interface ITask extends Document {
  boardId: mongoose.Types.ObjectId;
  title: string;
  description: string;
  status: TaskStatus;
  priority: Priority;
  assignee: string;
  tags: string[];
  dueDate: Date | null;
  startDate: Date | null;
  order: number;
  subTasks: ISubTask[];
  comments: IComment[];
  history: IHistoryEntry[];
  operationLogs: IOperationLog[];
  createdAt: Date;
  updatedAt: Date;
}

const subTaskSchema: Schema = new Schema({
  title: {
    type: String,
    required: true,
    trim: true,
  },
  completed: {
    type: Boolean,
    default: false,
  },
  createdAt: {
    type: Date,
    default: Date.now,
  },
});

const commentSchema: Schema = new Schema({
  content: {
    type: String,
    required: true,
    trim: true,
  },
  author: {
    type: String,
    default: '匿名用户',
  },
  createdAt: {
    type: Date,
    default: Date.now,
  },
});

const historySchema: Schema = new Schema({
  field: {
    type: String,
    required: true,
  },
  oldValue: Schema.Types.Mixed,
  newValue: Schema.Types.Mixed,
  changedBy: {
    type: String,
    default: '系统',
  },
  changedAt: {
    type: Date,
    default: Date.now,
  },
});

const snapshotSchema: Schema = new Schema({
  title: String,
  description: String,
  status: String,
  priority: String,
  assignee: String,
  tags: [String],
  dueDate: Date,
  startDate: Date,
  subTasks: [subTaskSchema],
});

const operationLogSchema: Schema = new Schema({
  operation: {
    type: String,
    enum: [
      'create',
      'update',
      'delete',
      'status_change',
      'subtask_add',
      'subtask_remove',
      'subtask_complete',
      'comment_add',
      'comment_remove',
    ],
    required: true,
  },
  operator: {
    type: String,
    default: '当前用户',
  },
  timestamp: {
    type: Date,
    default: Date.now,
  },
  description: {
    type: String,
    required: true,
  },
  changes: [{
    field: String,
    oldValue: Schema.Types.Mixed,
    newValue: Schema.Types.Mixed,
  }],
  snapshotBefore: snapshotSchema,
  snapshotAfter: snapshotSchema,
});

const taskSchema: Schema = new Schema({
  boardId: {
    type: Schema.Types.ObjectId,
    ref: 'Board',
    required: true,
  },
  title: {
    type: String,
    required: true,
    trim: true,
  },
  description: {
    type: String,
    default: '',
    trim: true,
  },
  status: {
    type: String,
    enum: ['todo', 'in-progress', 'done'],
    default: 'todo',
  },
  priority: {
    type: String,
    enum: ['low', 'medium', 'high', 'urgent'],
    default: 'medium',
  },
  assignee: {
    type: String,
    default: '',
  },
  tags: [{
    type: String,
  }],
  dueDate: {
    type: Date,
  },
  startDate: {
    type: Date,
  },
  order: {
    type: Number,
    default: 0,
  },
  subTasks: [subTaskSchema],
  comments: [commentSchema],
  history: [historySchema],
  operationLogs: [operationLogSchema],
}, {
  timestamps: true,
});

export default mongoose.model<ITask>('Task', taskSchema);
