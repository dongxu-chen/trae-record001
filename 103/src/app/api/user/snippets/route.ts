import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth/next'
import prisma from '@/lib/prisma'
import { cache, CACHE_KEYS } from '@/lib/redis'

export async function GET(request: Request) {
  try {
    const session = await getServerSession()

    if (!session?.user?.email) {
      return new NextResponse('Unauthorized', { status: 401 })
    }

    const user = await prisma.user.findUnique({
      where: { email: session.user.email }
    })

    if (!user) {
      return new NextResponse('User not found', { status: 404 })
    }

    const cacheKey = CACHE_KEYS.USER_SNIPPETS(user.id)
    const cached = await cache.get(cacheKey)

    if (cached) {
      return NextResponse.json(cached)
    }

    const snippets = await prisma.snippet.findMany({
      where: { authorId: user.id },
      include: {
        author: {
          select: {
            id: true,
            name: true,
            email: true
          }
        }
      },
      orderBy: { createdAt: 'desc' }
    })

    await cache.set(cacheKey, snippets, 120) // 2分钟缓存

    return NextResponse.json(snippets)
  } catch (error) {
    console.error('Failed to fetch user snippets:', error)
    return new NextResponse('Internal server error', { status: 500 })
  }
}
