import prisma from '~/server/utils/prisma'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { bookId, location, percentage } = body

  let progress = await prisma.progress.findFirst({
    where: { bookId }
  })

  if (progress) {
    progress = await prisma.progress.update({
      where: { id: progress.id },
      data: { location, percentage }
    })
  } else {
    progress = await prisma.progress.create({
      data: { bookId, location, percentage }
    })
  }

  return progress
})
