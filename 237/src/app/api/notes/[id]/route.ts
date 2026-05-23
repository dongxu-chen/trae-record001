import { NextResponse } from 'next/server'
import dbConnect from '@/lib/mongodb'
import Note from '@/models/Note'
import { createVersion, deleteVersionsByNoteId } from '@/lib/versionService'
import { indexDocument, removeDocumentFromIndex } from '@/lib/searchService'

export async function GET(request: Request, { params }: { params: { id: string } }) {
  try {
    await dbConnect()
    const note = await Note.findById(params.id).populate('tags')
    if (!note) {
      return NextResponse.json({ error: 'Note not found' }, { status: 404 })
    }
    return NextResponse.json(note)
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch note' }, { status: 500 })
  }
}

export async function PUT(request: Request, { params }: { params: { id: string } }) {
  try {
    await dbConnect()
    const body = await request.json()
    
    const oldNote = await Note.findById(params.id)
    if (!oldNote) {
      return NextResponse.json({ error: 'Note not found' }, { status: 404 })
    }

    const note = await Note.findByIdAndUpdate(params.id, body, { new: true })
    if (!note) {
      return NextResponse.json({ error: 'Note not found' }, { status: 404 })
    }

    if (oldNote.title !== note.title || oldNote.content !== note.content) {
      await createVersion(note._id.toString(), note.title, note.content)
    }

    if (oldNote.title !== note.title || oldNote.content !== note.content) {
      await indexDocument(note._id.toString(), note.title, note.content)
    }

    return NextResponse.json(note)
  } catch (error) {
    console.error('Update note error:', error)
    return NextResponse.json({ error: 'Failed to update note' }, { status: 500 })
  }
}

export async function DELETE(request: Request, { params }: { params: { id: string } }) {
  try {
    await dbConnect()
    const note = await Note.findByIdAndDelete(params.id)
    if (!note) {
      return NextResponse.json({ error: 'Note not found' }, { status: 404 })
    }

    await deleteVersionsByNoteId(params.id)
    await removeDocumentFromIndex(params.id)

    return NextResponse.json({ message: 'Note deleted successfully' })
  } catch (error) {
    return NextResponse.json({ error: 'Failed to delete note' }, { status: 500 })
  }
}
