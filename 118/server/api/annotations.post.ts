import prisma from '~/server/utils/prisma'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { bookId, cfi, text, note, color } = body

  const annotation = await prisma.annotation.create({
    data: { bookId, cfi, text, note, color }
  })

  return annotation
})
