import prisma from '~/server/utils/prisma'

export default defineEventHandler(async () => {
  const books = await prisma.book.findMany({
    orderBy: { createdAt: 'desc' }
  })
  return books
})
