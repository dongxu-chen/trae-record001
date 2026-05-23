import { NextResponse } from 'next/server'
import dbConnect from '@/lib/mongodb'
import { search } from '@/lib/searchService'

export async function GET(request: Request) {
  try {
    await dbConnect()
    
    const { searchParams } = new URL(request.url)
    const query = searchParams.get('q')
    const tagsParam = searchParams.get('tags')
    const folderId = searchParams.get('folderId')

    if (!query) {
      return NextResponse.json({ error: 'Query parameter is required' }, { status: 400 })
    }

    const tags = tagsParam ? tagsParam.split(',') : undefined
    const results = await search(query, { tags, folderId: folderId || undefined })

    return NextResponse.json(results.map(r => ({
      _id: r.noteId,
      title: r.title,
      content: r.content,
      score: r.score,
      highlight: r.highlight,
    })))
  } catch (error) {
    console.error('Search error:', error)
    return NextResponse.json({ error: 'Failed to search notes' }, { status: 500 })
  }
}
