import prisma from '~/server/utils/prisma'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { bookId, startCfi } = body

  const session = await prisma.readingSession.create({
    data: {
      bookId,
      startCfi
    }
  })

  return session
})
