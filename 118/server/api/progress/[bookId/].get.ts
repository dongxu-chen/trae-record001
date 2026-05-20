import prisma from '~/server/utils/prisma'

export default defineEventHandler(async (event) => {
  const bookId = parseInt(getRouterParam(event, 'bookId') || '0')
  const progress = await prisma.progress.findFirst({
    where: { bookId },
    orderBy: { updatedAt: 'desc' }
  })
  return progress || { location: '', percentage: 0 }
})
