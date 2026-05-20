import prisma from '~/server/utils/prisma'

export default defineEventHandler(async (event) => {
  const bookId = parseInt(getRouterParam(event, 'bookId') || '0')

  const book = await prisma.book.findUnique({
    where: { id: bookId },
    select: {
      summary: true,
      title: true
    }
  })

  if (!book) {
    throw createError({ statusCode: 404, message: 'Book not found' })
  }

  return {
    bookTitle: book.title,
    summary: book.summary
  }
})
