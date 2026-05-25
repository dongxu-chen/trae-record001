import mongoose, { Document, Schema } from 'mongoose';
import { Priority } from './Task';

export interface ITaskTemplate extends Document {
  name: string;
  description: string;
  title: string;
  taskDescription: string;
  priority: Priority;
  assignee: string;
  tags: string[];
  dueDays: number;
  subTasks: string[];
  createdAt: Date;
  updatedAt: Date;
}

const TaskTemplateSchema = new Schema<ITaskTemplate>({
  name: {
    type: String,
    required: true,
    trim: true,
  },
  description: {
    type: String,
    trim: true,
  },
  title: {
    type: String,
    required: true,
    trim: true,
  },
  taskDescription: {
    type: String,
    default: '',
  },
  priority: {
    type: String,
    required: true,
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
  dueDays: {
    type: Number,
    required: true,
    default: 7,
    min: 1,
  },
  subTasks: [{
    type: String,
  }],
}, {
  timestamps: true,
});

export default mongoose.model<ITaskTemplate>('TaskTemplate', TaskTemplateSchema);
