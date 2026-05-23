import { NextResponse } from 'next/server'
import dbConnect from '@/lib/mongodb'
import Share from '@/models/Share'
import Note from '@/models/Note'

export async function GET(request: Request, { params }: { params: { token: string } }) {
  try {
    await dbConnect()
    
    const share = await Share.findOne({ shareToken: params.token, isActive: true })
    if (!share) {
      return NextResponse.json({ error: 'Share not found or expired' }, { status: 404 })
    }

    if (share.expiresAt && new Date(share.expiresAt) < new Date()) {
      return NextResponse.json({ error: 'Share has expired' }, { status: 404 })
    }

    const note = await Note.findById(share.noteId)
    if (!note) {
      return NextResponse.json({ error: 'Note not found' }, { status: 404 })
    }

    return NextResponse.json(note)
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch shared note' }, { status: 500 })
  }
}
