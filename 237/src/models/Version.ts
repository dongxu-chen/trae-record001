import mongoose, { Schema, Document, Types } from 'mongoose'

export interface IVersion extends Document {
  noteId: Types.ObjectId
  title: string
  content: string
  versionNumber: number
  isFullVersion: boolean
  baseVersion?: number
  createdAt: Date
}

const VersionSchema: Schema = new Schema(
  {
    noteId: {
      type: Schema.Types.ObjectId,
      ref: 'Note',
      required: true,
    },
    title: {
      type: String,
      required: true,
    },
    content: {
      type: String,
      required: true,
    },
    versionNumber: {
      type: Number,
      required: true,
      default: 1,
    },
    isFullVersion: {
      type: Boolean,
      default: true,
    },
    baseVersion: {
      type: Number,
      default: null,
    },
  },
  {
    timestamps: true,
  }
)

VersionSchema.index({ noteId: 1, versionNumber: -1 })
VersionSchema.index({ noteId: 1, isFullVersion: 1 })

export default mongoose.models.Version || mongoose.model<IVersion>('Version', VersionSchema)
