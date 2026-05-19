import prisma from '~/server/utils/prisma'

export default defineEventHandler(async () => {
  const thirtyDaysAgo = new Date()
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

  const stats = await prisma.readingStats.findMany({
    where: {
      date: { gte: thirtyDaysAgo }
    },
    orderBy: { date: 'asc' }
  })

  const books = await prisma.book.findMany({
    select: {
      id: true,
      title: true,
      totalReadTime: true,
      isCompleted: true,
      createdAt: true
    },
    orderBy: { totalReadTime: 'desc' }
  })

  const totalStats = {
    totalReadTime: books.reduce((sum, b) => sum + b.totalReadTime, 0),
    booksCompleted: books.filter(b => b.isCompleted).length,
    totalBooks: books.length
  }

  return {
    daily: stats,
    books,
    total: totalStats
  }
})
