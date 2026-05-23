import mongoose, { Schema, Document, Types } from 'mongoose'

export interface INote extends Document {
  title: string
  content: string
  ocrText: string
  folderId?: Types.ObjectId
  tags: Types.ObjectId[]
  isPublic: boolean
  createdAt: Date
  updatedAt: Date
}

const NoteSchema: Schema = new Schema(
  {
    title: {
      type: String,
      required: true,
      trim: true,
      default: 'Untitled Note',
    },
    content: {
      type: String,
      default: '',
    },
    ocrText: {
      type: String,
      default: '',
    },
    folderId: {
      type: Schema.Types.ObjectId,
      ref: 'Folder',
      default: null,
    },
    tags: [
      {
        type: Schema.Types.ObjectId,
        ref: 'Tag',
      },
    ],
    isPublic: {
      type: Boolean,
      default: false,
    },
  },
  {
    timestamps: true,
  }
)

NoteSchema.index({ title: 'text', content: 'text' })

export default mongoose.models.Note || mongoose.model<INote>('Note', NoteSchema)
