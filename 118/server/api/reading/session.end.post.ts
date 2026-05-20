import prisma from '~/server/utils/prisma'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { sessionId, endCfi, pagesRead } = body

  const session = await prisma.readingSession.findUnique({
    where: { id: sessionId }
  })

  if (!session) {
    throw createError({ statusCode: 404, message: 'Session not found' })
  }

  const endTime = new Date()
  const duration = Math.floor((endTime.getTime() - session.startTime.getTime()) / 1000)

  const updatedSession = await prisma.readingSession.update({
    where: { id: sessionId },
    data: {
      endTime,
      duration,
      endCfi,
      pagesRead
    }
  })

  await prisma.book.update({
    where: { id: session.bookId },
    data: {
      totalReadTime: { increment: duration }
    }
  })

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  await prisma.readingStats.upsert({
    where: { date: today },
    create: {
      date: today,
      totalReadTime: duration,
      pagesRead
    },
    update: {
      totalReadTime: { increment: duration },
      pagesRead: { increment: pagesRead }
    }
  })

  return updatedSession
})
