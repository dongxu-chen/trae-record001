import prisma from '~/server/utils/prisma'

export default defineEventHandler(async (event) => {
  const bookId = parseInt(getRouterParam(event, 'bookId') || '0')

  const bookmarks = await prisma.bookmark.findMany({
    where: { bookId },
    orderBy: { createdAt: 'desc' }
  })

  return bookmarks
})
