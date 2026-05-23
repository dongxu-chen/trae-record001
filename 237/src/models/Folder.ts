import mongoose, { Schema, Document, Types } from 'mongoose'

export interface IFolder extends Document {
  name: string
  parentId?: Types.ObjectId
  createdAt: Date
  updatedAt: Date
}

const FolderSchema: Schema = new Schema(
  {
    name: {
      type: String,
      required: true,
      trim: true,
    },
    parentId: {
      type: Schema.Types.ObjectId,
      ref: 'Folder',
      default: null,
    },
  },
  {
    timestamps: true,
  }
)

export default mongoose.models.Folder || mongoose.model<IFolder>('Folder', FolderSchema)
