import mongoose, { Schema, Document } from 'mongoose';

export interface IBoard extends Document {
  name: string;
  description: string;
  createdAt: Date;
  updatedAt: Date;
}

const boardSchema: Schema = new Schema({
  name: {
    type: String,
    required: true,
    trim: true,
  },
  description: {
    type: String,
    default: '',
    trim: true,
  },
}, {
  timestamps: true,
});

export default mongoose.model<IBoard>('Board', boardSchema);
