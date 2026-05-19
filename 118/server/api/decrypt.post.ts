import prisma from '~/server/utils/prisma'
import { EPubDecryptor } from '~/server/utils/epubCrypto'
import fs from 'fs'
import path from 'path'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { bookId, password } = body

  const book = await prisma.book.findUnique({ where: { id: bookId } })
  if (!book) {
    throw createError({ statusCode: 404, message: 'Book not found' })
  }

  const filePath = path.join(process.cwd(), 'uploads', 'books', book.filePath)
  
  if (!fs.existsSync(filePath)) {
    throw createError({ statusCode: 404, message: 'File not found' })
  }

  const decryptor = new EPubDecryptor(filePath)
  const decryptedPath = path.join(process.cwd(), 'uploads', 'books', `decrypted_${book.filePath}')

  const success = await decryptor.decryptWithPassword(password)
  
  if (success) {
    await decryptor.saveDecrypted(decryptedPath)
    await prisma.book.update({
      where: { id: bookId },
      data: { 
        filePath: `decrypted_${book.filePath}`,
        description: JSON.stringify({ encrypted: false })
      }
    })
    return { success: true }
  } else {
    throw createError({ statusCode: 400, message: '解密失败，请检查密码是否正确' })
  }
})
