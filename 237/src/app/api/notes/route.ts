import { NextResponse } from 'next/server'
import dbConnect from '@/lib/mongodb'
import Note from '@/models/Note'
import Version from '@/models/Version'
import { indexDocument } from '@/lib/searchService'
import { createInitialVersion } from '@/lib/versionService'

export async function GET() {
  try {
    await dbConnect()
    const notes = await Note.find().populate('tags').sort({ updatedAt: -1 })
    return NextResponse.json(notes)
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch notes' }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    await dbConnect()
    
    const body = await request.json()
    const note = new Note(body)
    await note.save()

    await createInitialVersion(note._id.toString(), note.title, note.content)
    await indexDocument(note._id.toString(), note.title, note.content)

    return NextResponse.json(note, { status: 201 })
  } catch (error) {
    console.error('Create note error:', error)
    return NextResponse.json({ error: 'Failed to create note' }, { status: 500 })
  }
}
