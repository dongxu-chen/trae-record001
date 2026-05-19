import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth/next'
import prisma from '@/lib/prisma'
import { invalidateSnippetCache } from '@/lib/services/snippetService'

export async function POST(
  request: Request,
  { params }: { params: { id: string; versionNumber: string } }
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

    if (snippet.authorId !== user.id) {
      return new NextResponse('Forbidden', { status: 403 })
    }

    const versionNum = parseInt(params.versionNumber)
    if (isNaN(versionNum)) {
      return new NextResponse('Invalid version number', { status: 400 })
    }

    const version = await prisma.snippetVersion.findUnique({
      where: {
        snippetId_versionNumber: {
          snippetId: params.id,
          versionNumber: versionNum
        }
      }
    })

    if (!version) {
      return new NextResponse('Version not found', { status: 404 })
    }

    const currentMaxVersion = await prisma.snippetVersion.aggregate({
      where: { snippetId: params.id },
      _max: { versionNumber: true }
    })

    const newVersionNumber = (currentMaxVersion._max.versionNumber || 0) + 1

    await prisma.$transaction([
      prisma.snippetVersion.create({
        data: {
          snippetId: params.id,
          title: snippet.title,
          description: snippet.description,
          code: snippet.code,
          language: snippet.language,
          versionNumber: newVersionNumber,
          createdById: user.id
        }
      }),

      prisma.snippet.update({
        where: { id: params.id },
        data: {
          title: version.title,
          description: version.description,
          code: version.code,
          language: version.language
        }
      })
    ])

    // 失效缓存
    await invalidateSnippetCache(params.id)

    return NextResponse.json({ success: true, newVersionNumber })
  } catch (error) {
    console.error(error)
    return new NextResponse('Internal server error', { status: 500 })
  }
}
