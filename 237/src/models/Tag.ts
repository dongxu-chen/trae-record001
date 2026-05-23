import mongoose, { Schema, Document } from 'mongoose'

export interface ITag extends Document {
  name: string
  color: string
  createdAt: Date
  updatedAt: Date
}

const TagSchema: Schema = new Schema(
  {
    name: {
      type: String,
      required: true,
      unique: true,
      trim: true,
    },
    color: {
      type: String,
      default: '#3b82f6',
    },
  },
  {
    timestamps: true,
  }
)

export default mongoose.models.Tag || mongoose.model<ITag>('Tag', TagSchema)
