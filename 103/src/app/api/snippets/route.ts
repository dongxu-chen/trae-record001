import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth/next'
import prisma from '@/lib/prisma'
import { SNIPPET, MESSAGES } from '@/lib/constants'
import { invalidateSnippetCache } from '@/lib/services/snippetService'

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const search = searchParams.get('search') || ''
    const language = searchParams.get('language') || ''

    const where: any = {
      isPublic: true
    }

    if (search) {
      where.OR = [
        { title: { contains: search, mode: 'insensitive' } },
        { description: { contains: search, mode: 'insensitive' } },
        { code: { contains: search, mode: 'insensitive' } }
      ]
    }

    if (language) {
      where.language = language
    }

    const snippets = await prisma.snippet.findMany({
      where,
      include: {
        author: {
          select: {
            id: true,
            name: true,
            email: true
          }
        }
      },
      orderBy: {
        createdAt: 'desc'
      }
    })

    return NextResponse.json(snippets)
  } catch (error) {
    console.error(error)
    return new NextResponse('Internal server error', { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    const session = await getServerSession()

    if (!session?.user?.email) {
      return new NextResponse('Unauthorized', { status: 401 })
    }

    const body = await request.json()
    const { title, description, code, language, isPublic } = body

    if (!title || !code || !language) {
      return new NextResponse('Missing required fields', { status: 400 })
    }

    if (title.length > SNIPPET.MAX_TITLE_LENGTH) {
      return new NextResponse(MESSAGES.TITLE_TOO_LONG, { status: 400 })
    }

    if (description && description.length > SNIPPET.MAX_DESCRIPTION_LENGTH) {
      return new NextResponse(MESSAGES.DESCRIPTION_TOO_LONG, { status: 400 })
    }

    if (code.length > SNIPPET.MAX_CODE_LENGTH) {
      return new NextResponse(MESSAGES.CODE_TOO_LONG, { status: 400 })
    }

    const user = await prisma.user.findUnique({
      where: {
        email: session.user.email
      }
    })

    if (!user) {
      return new NextResponse('User not found', { status: 404 })
    }

    const snippet = await prisma.snippet.create({
      data: {
        title,
        description,
        code,
        language,
        isPublic: isPublic ?? true,
        authorId: user.id
      },
      include: {
        author: {
          select: {
            id: true,
            name: true,
            email: true
          }
        }
      }
    })

    // 失效缓存
    await invalidateSnippetCache()

    return NextResponse.json(snippet)
  } catch (error) {
    console.error(error)
    return new NextResponse('Internal server error', { status: 500 })
  }
}
