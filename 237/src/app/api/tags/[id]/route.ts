import { NextResponse } from 'next/server'
import dbConnect from '@/lib/mongodb'
import Tag from '@/models/Tag'
import Note from '@/models/Note'

export async function PUT(request: Request, { params }: { params: { id: string } }) {
  try {
    await dbConnect()
    const body = await request.json()
    const tag = await Tag.findByIdAndUpdate(params.id, body, { new: true })
    if (!tag) {
      return NextResponse.json({ error: 'Tag not found' }, { status: 404 })
    }
    return NextResponse.json(tag)
  } catch (error) {
    return NextResponse.json({ error: 'Failed to update tag' }, { status: 500 })
  }
}

export async function DELETE(request: Request, { params }: { params: { id: string } }) {
  try {
    await dbConnect()
    const tag = await Tag.findByIdAndDelete(params.id)
    if (!tag) {
      return NextResponse.json({ error: 'Tag not found' }, { status: 404 })
    }

    await Note.updateMany({ tags: params.id }, { $pull: { tags: params.id } })

    return NextResponse.json({ message: 'Tag deleted successfully' })
  } catch (error) {
    return NextResponse.json({ error: 'Failed to delete tag' }, { status: 500 })
  }
}
