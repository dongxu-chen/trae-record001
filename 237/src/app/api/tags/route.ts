import { NextResponse } from 'next/server'
import dbConnect from '@/lib/mongodb'
import Tag from '@/models/Tag'

export async function GET() {
  try {
    await dbConnect()
    const tags = await Tag.find().sort({ name: 1 })
    return NextResponse.json(tags)
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch tags' }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    await dbConnect()
    const body = await request.json()
    const tag = new Tag(body)
    await tag.save()
    return NextResponse.json(tag, { status: 201 })
  } catch (error) {
    return NextResponse.json({ error: 'Failed to create tag' }, { status: 500 })
  }
}
