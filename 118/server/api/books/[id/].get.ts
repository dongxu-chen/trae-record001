import prisma from '~/server/utils/prisma'

export default defineEventHandler(async (event) => {
  const id = parseInt(getRouterParam(event, 'id') || '0')
  const book = await prisma.book.findUnique({
    where: { id }
  })
  if (!book) {
    throw createError({ statusCode: 404, message: 'Book not found' })
  }
  return book
})
