import prisma from '~/server/utils/prisma'
import { generateBookSummary, generateChapterSummary } from '~/server/utils/llm'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { bookId, chapterIndex, chapterTitle, content } = body

  const book = await prisma.book.findUnique({
    where: { id: bookId }
  })

  if (!book) {
    throw createError({ statusCode: 404, message: 'Book not found' })
  }

  if (chapterIndex !== undefined) {
    const summary = await generateChapterSummary(
      book.title,
      chapterTitle || `第 ${chapterIndex + 1} 章`,
      content || ''
    )

    const existingSummary = await prisma.chapterSummary.findFirst({
      where: { bookId, chapterIndex }
    })

    if (existingSummary) {
      await prisma.chapterSummary.update({
        where: { id: existingSummary.id },
        data: { summary }
      })
    } else {
      await prisma.chapterSummary.create({
        data: {
          bookId,
          chapterIndex,
          chapterTitle: chapterTitle || `第 ${chapterIndex + 1} 章`,
          summary
        }
      })
    }

    return { type: 'chapter', summary }
  } else {
    const summary = await generateBookSummary(book.title, content || '')

    await prisma.book.update({
      where: { id: bookId },
      data: { summary }
    })

    return { type: 'book', summary }
  }
})
