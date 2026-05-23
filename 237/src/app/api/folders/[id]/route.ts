import { NextResponse } from 'next/server'
import dbConnect from '@/lib/mongodb'
import Folder from '@/models/Folder'
import Note from '@/models/Note'

export async function PUT(request: Request, { params }: { params: { id: string } }) {
  try {
    await dbConnect()
    const body = await request.json()
    const folder = await Folder.findByIdAndUpdate(params.id, body, { new: true })
    if (!folder) {
      return NextResponse.json({ error: 'Folder not found' }, { status: 404 })
    }
    return NextResponse.json(folder)
  } catch (error) {
    return NextResponse.json({ error: 'Failed to update folder' }, { status: 500 })
  }
}

export async function DELETE(request: Request, { params }: { params: { id: string } }) {
  try {
    await dbConnect()
    const folder = await Folder.findByIdAndDelete(params.id)
    if (!folder) {
      return NextResponse.json({ error: 'Folder not found' }, { status: 404 })
    }

    await Note.updateMany({ folderId: params.id }, { $set: { folderId: null } })
    await Folder.updateMany({ parentId: params.id }, { $set: { parentId: null } })

    return NextResponse.json({ message: 'Folder deleted successfully' })
  } catch (error) {
    return NextResponse.json({ error: 'Failed to delete folder' }, { status: 500 })
  }
}
