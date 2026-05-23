import { NextResponse } from 'next/server'
import dbConnect from '@/lib/mongodb'
import { getVersions, getVersionDiff } from '@/lib/versionService'

export async function GET(request: Request, { params }: { params: { id: string } }) {
  try {
    await dbConnect()
    
    const { searchParams } = new URL(request.url)
    const compare = searchParams.get('compare')
    
    if (compare) {
      const [v1, v2] = compare.split(',').map(Number)
      const diff = await getVersionDiff(params.id, v1, v2)
      return NextResponse.json(diff)
    }
    
    const versions = await getVersions(params.id)
    return NextResponse.json(versions)
  } catch (error) {
    console.error('Get versions error:', error)
    return NextResponse.json({ error: 'Failed to fetch versions' }, { status: 500 })
  }
}
