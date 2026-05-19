import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth/next'
import prisma from '@/lib/prisma'
import { SNIPPET, MESSAGES } from '@/lib/constants'
import { invalidateSnippetCache } from '@/lib/services/snippetService'

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const snippet = await prisma.snippet.findUnique({
      where: {
        id: params.id
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

    if (!snippet) {
      return new NextResponse('Snippet not found', { status: 404 })
    }

    return NextResponse.json(snippet)
  } catch (error) {
    console.error(error)
    return new NextResponse('Internal server error', { status: 500 })
  }
}

export async function PATCH(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession()

    if (!session?.user?.email) {
      return new NextResponse('Unauthorized', { status: 401 })
    }

    const body = await request.json()
    const { title, description, code, language, isPublic } = body

    if (title && title.length > SNIPPET.MAX_TITLE_LENGTH) {
      return new NextResponse(MESSAGES.TITLE_TOO_LONG, { status: 400 })
    }

    if (description && description.length > SNIPPET.MAX_DESCRIPTION_LENGTH) {
      return new NextResponse(MESSAGES.DESCRIPTION_TOO_LONG, { status: 400 })
    }

    if (code && code.length > SNIPPET.MAX_CODE_LENGTH) {
      return new NextResponse(MESSAGES.CODE_TOO_LONG, { status: 400 })
    }

    const snippet = await prisma.snippet.findUnique({
      where: {
        id: params.id
      }
    })

    if (!snippet) {
      return new NextResponse('Snippet not found', { status: 404 })
    }

    const user = await prisma.user.findUnique({
      where: {
        email: session.user.email
      }
    })

    if (!user || snippet.authorId !== user.id) {
      return new NextResponse('Forbidden', { status: 403 })
    }

    const currentMaxVersion = await prisma.snippetVersion.aggregate({
      where: { snippetId: params.id },
      _max: { versionNumber: true }
    })

    const newVersionNumber = (currentMaxVersion._max.versionNumber || 0) + 1

    const updatedSnippet = await prisma.$transaction(async (tx) => {
      await tx.snippetVersion.create({
        data: {
          snippetId: params.id,
          title: snippet.title,
          description: snippet.description,
          code: snippet.code,
          language: snippet.language,
          versionNumber: newVersionNumber,
          createdById: user.id
        }
      })

      return tx.snippet.update({
        where: {
          id: params.id
        },
        data: {
          title,
          description,
          code,
          language,
          isPublic
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
    })

    // 失效缓存
    await invalidateSnippetCache(params.id)

    return NextResponse.json(updatedSnippet)
  } catch (error) {
    console.error(error)
    return new NextResponse('Internal server error', { status: 500 })
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession()

    if (!session?.user?.email) {
      return new NextResponse('Unauthorized', { status: 401 })
    }

    const snippet = await prisma.snippet.findUnique({
      where: {
        id: params.id
      }
    })

    if (!snippet) {
      return new NextResponse('Snippet not found', { status: 404 })
    }

    const user = await prisma.user.findUnique({
      where: {
        email: session.user.email
      }
    })

    if (!user || snippet.authorId !== user.id) {
      return new NextResponse('Forbidden', { status: 403 })
    }

    await prisma.snippet.delete({
      where: {
        id: params.id
      }
    })

    // 失效缓存
    await invalidateSnippetCache(params.id)

    return new NextResponse('Snippet deleted successfully', { status: 200 })
  } catch (error) {
    console.error(error)
    return new NextResponse('Internal server error', { status: 500 })
  }
}
