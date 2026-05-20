import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'

export async function GET() {
  try {
    const languages = await prisma.snippet.findMany({
      where: {
        isPublic: true
      },
      select: {
        language: true
      },
      distinct: ['language']
    })

    const languageList = languages
      .map((s) => s.language)
      .filter(Boolean)
      .sort()

    return NextResponse.json(languageList)
  } catch (error) {
    console.error(error)
    return new NextResponse('Internal server error', { status: 500 })
  }
}
