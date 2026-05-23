import { NextResponse } from 'next/server'
import dbConnect from '@/lib/mongodb'
import Share from '@/models/Share'
import Note from '@/models/Note'

export async function GET(request: Request, { params }: { params: { id: string } }) {
  try {
    await dbConnect()
    const share = await Share.findOne({ noteId: params.id })
    return NextResponse.json(share)
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch share info' }, { status: 500 })
  }
}

export async function POST(request: Request, { params }: { params: { id: string } }) {
  try {
    await dbConnect()
    
    const note = await Note.findById(params.id)
    if (!note) {
      return NextResponse.json({ error: 'Note not found' }, { status: 404 })
    }

    let share = await Share.findOne({ noteId: params.id })
    if (share) {
      share.isActive = !share.isActive
      await share.save()
    } else {
      share = new Share({ noteId: params.id })
      await share.save()
    }

    note.isPublic = share.isActive
    await note.save()

    return NextResponse.json(share)
  } catch (error) {
    return NextResponse.json({ error: 'Failed to toggle share' }, { status: 500 })
  }
}

export async function DELETE(request: Request, { params }: { params: { id: string } }) {
  try {
    await dbConnect()
    await Share.findOneAndDelete({ noteId: params.id })
    await Note.findByIdAndUpdate(params.id, { isPublic: false })
    return NextResponse.json({ message: 'Share revoked successfully' })
  } catch (error) {
    return NextResponse.json({ error: 'Failed to revoke share' }, { status: 500 })
  }
}
