import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth/next'
import prisma from '@/lib/prisma'

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const comments = await prisma.comment.findMany({
      where: {
        snippetId: params.id,
        parentId: null
      },
      include: {
        author: {
          select: {
            id: true,
            name: true,
            email: true
          }
        },
        replies: {
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
            createdAt: 'asc'
          }
        }
      },
      orderBy: {
        createdAt: 'desc'
      }
    })

    return NextResponse.json(comments)
  } catch (error) {
    console.error(error)
    return new NextResponse('Internal server error', { status: 500 })
  }
}

export async function POST(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession()

    if (!session?.user?.email) {
      return new NextResponse('Unauthorized', { status: 401 })
    }

    const body = await request.json()
    const { content, parentId } = body

    if (!content || content.trim().length === 0) {
      return new NextResponse('Content is required', { status: 400 })
    }

    const user = await prisma.user.findUnique({
      where: { email: session.user.email }
    })

    if (!user) {
      return new NextResponse('User not found', { status: 404 })
    }

    const snippet = await prisma.snippet.findUnique({
      where: { id: params.id },
      include: { author: true }
    })

    if (!snippet) {
      return new NextResponse('Snippet not found', { status: 404 })
    }

    let parentComment = null
    let notificationRecipientId = null

    if (parentId) {
      parentComment = await prisma.comment.findUnique({
        where: { id: parentId },
        include: { author: true }
      })

      if (!parentComment) {
        return new NextResponse('Parent comment not found', { status: 404 })
      }

      if (parentComment.authorId !== user.id) {
        notificationRecipientId = parentComment.authorId
      }
    } else {
      if (snippet.authorId !== user.id) {
        notificationRecipientId = snippet.authorId
      }
    }

    const comment = await prisma.$transaction(async (tx) => {
      const newComment = await tx.comment.create({
        data: {
          snippetId: params.id,
          authorId: user.id,
          content: content.trim(),
          parentId: parentId || null
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

      if (notificationRecipientId && notificationRecipientId !== user.id) {
        await tx.notification.create({
          data: {
            userId: notificationRecipientId,
            type: parentId ? 'REPLY' : 'COMMENT',
            title: parentId ? '有人回复了你的评论' : '有人评论了你的代码片段',
            content: content.length > 100 ? content.substring(0, 100) + '...' : content,
            relatedId: params.id
          }
        })
      }

      return newComment
    })

    return NextResponse.json(comment)
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

    const { searchParams } = new URL(request.url)
    const commentId = searchParams.get('commentId')

    if (!commentId) {
      return new NextResponse('Comment ID is required', { status: 400 })
    }

    const user = await prisma.user.findUnique({
      where: { email: session.user.email }
    })

    if (!user) {
      return new NextResponse('User not found', { status: 404 })
    }

    const comment = await prisma.comment.findUnique({
      where: { id: commentId },
      include: { snippet: true }
    })

    if (!comment) {
      return new NextResponse('Comment not found', { status: 404 })
    }

    if (comment.authorId !== user.id && comment.snippet.authorId !== user.id) {
      return new NextResponse('Forbidden', { status: 403 })
    }

    await prisma.comment.delete({
      where: { id: commentId }
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error(error)
    return new NextResponse('Internal server error', { status: 500 })
  }
}
