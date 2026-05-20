import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth/next'
import prisma from '@/lib/prisma'
import { invalidateSnippetCache } from '@/lib/services/snippetService'

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession()

    const likesCount = await prisma.like.count({
      where: { snippetId: params.id }
    })

    let userLiked = false
    if (session?.user?.email) {
      const user = await prisma.user.findUnique({
        where: { email: session.user.email }
      })

      if (user) {
        const like = await prisma.like.findUnique({
          where: {
            snippetId_userId: {
              snippetId: params.id,
              userId: user.id
            }
          }
        })
        userLiked = !!like
      }
    }

    return NextResponse.json({ count: likesCount, userLiked })
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

    const user = await prisma.user.findUnique({
      where: { email: session.user.email }
    })

    if (!user) {
      return new NextResponse('User not found', { status: 404 })
    }

    const snippet = await prisma.snippet.findUnique({
      where: { id: params.id }
    })

    if (!snippet) {
      return new NextResponse('Snippet not found', { status: 404 })
    }

    const existingLike = await prisma.like.findUnique({
      where: {
        snippetId_userId: {
          snippetId: params.id,
          userId: user.id
        }
      }
    })

    if (existingLike) {
      return new NextResponse('Already liked', { status: 400 })
    }

    await prisma.$transaction(async (tx) => {
      await tx.like.create({
        data: {
          snippetId: params.id,
          userId: user.id
        }
      })

      if (snippet.authorId !== user.id) {
        await tx.notification.create({
          data: {
            userId: snippet.authorId,
            type: 'LIKE',
            title: '有人点赞了你的代码片段',
            content: snippet.title,
            relatedId: params.id
          }
        })
      }
    })

    // 失效缓存
    await invalidateSnippetCache(params.id)

    return NextResponse.json({ success: true })
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

    const user = await prisma.user.findUnique({
      where: { email: session.user.email }
    })

    if (!user) {
      return new NextResponse('User not found', { status: 404 })
    }

    const snippet = await prisma.snippet.findUnique({
      where: { id: params.id }
    })

    if (!snippet) {
      return new NextResponse('Snippet not found', { status: 404 })
    }

    const existingLike = await prisma.like.findUnique({
      where: {
        snippetId_userId: {
          snippetId: params.id,
          userId: user.id
        }
      }
    })

    if (!existingLike) {
      return new NextResponse('Not liked', { status: 400 })
    }

    await prisma.like.delete({
      where: { id: existingLike.id }
    })

    // 失效缓存
    await invalidateSnippetCache(params.id)

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error(error)
    return new NextResponse('Internal server error', { status: 500 })
  }
}
