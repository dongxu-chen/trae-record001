import prisma from '~/server/utils/prisma'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { bookId, cfi, chapter, note } = body

  const existing = await prisma.bookmark.findFirst({
    where: { bookId, cfi }
  })

  if (existing) {
    return existing
  }

  const bookmark = await prisma.bookmark.create({
    data: {
      bookId,
      cfi,
      chapter,
      note
    }
  })

  return bookmark
})
