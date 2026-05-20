import { upload } from '~/server/plugins/multer'
import prisma from '~/server/utils/prisma'
import { checkEPubEncryption, EPubDecryptor } from '~/server/utils/epubCrypto'
import fs from 'fs'
import path from 'path'

export default defineEventHandler(async (event) => {
  await new Promise((resolve, reject) => {
    upload.single('file')(event.node.req as any, event.node.res as any, (err: any) => {
      if (err) reject(err)
      resolve(true)
    })
  })

  const file = (event.node.req as any).file
  if (!file) {
    throw createError({ statusCode: 400, message: 'No file uploaded' })
  }

  const encryptionInfo = await checkEPubEncryption(file.path)

  const book = await prisma.book.create({
    data: {
      title: file.originalname.replace('.epub', ''),
      filePath: file.filename,
      description: JSON.stringify({ 
        encrypted: encryptionInfo.isEncrypted, 
        encryptionMethod: encryptionInfo.method })
    }
  })

  return { 
    success: true, 
    book,
    encryption: encryptionInfo
  }
})
