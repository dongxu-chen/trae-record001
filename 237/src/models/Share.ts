import mongoose, { Schema, Document, Types } from 'mongoose'
import { v4 as uuidv4 } from 'uuid'

export interface IShare extends Document {
  noteId: Types.ObjectId
  shareToken: string
  isActive: boolean
  expiresAt?: Date
  createdAt: Date
}

const ShareSchema: Schema = new Schema(
  {
    noteId: {
      type: Schema.Types.ObjectId,
      ref: 'Note',
      required: true,
      unique: true,
    },
    shareToken: {
      type: String,
      required: true,
      unique: true,
      default: () => uuidv4(),
    },
    isActive: {
      type: Boolean,
      default: true,
    },
    expiresAt: {
      type: Date,
      default: null,
    },
  },
  {
    timestamps: true,
  }
)

ShareSchema.index({ shareToken: 1, isActive: 1 })

export default mongoose.models.Share || mongoose.model<IShare>('Share', ShareSchema)
