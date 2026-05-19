import fs from 'fs'
import path from 'path'

export default defineEventHandler(async (event) => {
  const filename = getRouterParam(event, 'filename')
  const filePath = path.join(process.cwd(), 'uploads', 'books', filename || '')

  if (!fs.existsSync(filePath)) {
    throw createError({ statusCode: 404, message: 'File not found' })
  }

  const file = fs.readFileSync(filePath)
  setHeader(event, 'Content-Type', 'application/epub+zip')
  return file
})
