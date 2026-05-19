import prisma from '~/server/utils/prisma'

export default defineEventHandler(async (event) => {
  const bookId = parseInt(getRouterParam(event, 'bookId') || '0')

  const chapterSummaries = await prisma.chapterSummary.findMany({
    where: { bookId },
    orderBy: { chapterIndex: 'asc' }
  })

  return chapterSummaries
})
