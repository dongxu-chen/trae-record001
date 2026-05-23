import mongoose, { Schema, Document, Types } from 'mongoose'

export interface IInvertedIndex extends Document {
  term: string
  postings: {
    noteId: Types.ObjectId
    positions: number[]
    frequency: number
    fieldWeight: number
  }[]
  documentFrequency: number
  createdAt: Date
  updatedAt: Date
}

const PostingSchema = new Schema({
  noteId: {
    type: Schema.Types.ObjectId,
    ref: 'Note',
    required: true,
  },
  positions: {
    type: [Number],
    default: [],
  },
  frequency: {
    type: Number,
    default: 0,
  },
  fieldWeight: {
    type: Number,
    default: 1,
  },
}, { _id: false })

const InvertedIndexSchema: Schema = new Schema(
  {
    term: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    postings: {
      type: [PostingSchema],
      default: [],
    },
    documentFrequency: {
      type: Number,
      default: 0,
    },
  },
  {
    timestamps: true,
  }
)

InvertedIndexSchema.index({ term: 'text' })
InvertedIndexSchema.index({ 'postings.noteId': 1 })

export default mongoose.models.InvertedIndex || mongoose.model<IInvertedIndex>('InvertedIndex', InvertedIndexSchema)
