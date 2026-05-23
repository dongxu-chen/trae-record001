import { NextResponse } from 'next/server'
import dbConnect from '@/lib/mongodb'
import Folder from '@/models/Folder'

export async function GET() {
  try {
    await dbConnect()
    const folders = await Folder.find().sort({ name: 1 })
    return NextResponse.json(folders)
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch folders' }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    await dbConnect()
    const body = await request.json()
    const folder = new Folder(body)
    await folder.save()
    return NextResponse.json(folder, { status: 201 })
  } catch (error) {
    return NextResponse.json({ error: 'Failed to create folder' }, { status: 500 })
  }
}
