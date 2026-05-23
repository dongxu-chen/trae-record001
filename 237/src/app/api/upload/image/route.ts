import { NextRequest, NextResponse } from 'next/server'
import { writeFile, mkdir } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import Tesseract from 'tesseract.js'

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get('file') as File

    if (!file) {
      return NextResponse.json(
        { error: 'No file provided' },
        { status: 400 }
      )
    }

    if (!file.type.startsWith('image/')) {
      return NextResponse.json(
        { error: 'File must be an image' },
        { status: 400 }
      )
    }

    const uploadDir = path.join(process.cwd(), 'public', 'uploads')
    if (!existsSync(uploadDir)) {
      await mkdir(uploadDir, { recursive: true })
    }

    const fileId = `img-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    const fileExt = path.extname(file.name) || '.png'
    const fileName = `${fileId}${fileExt}`
    const filePath = path.join(uploadDir, fileName)

    const buffer = Buffer.from(await file.arrayBuffer())
    await writeFile(filePath, buffer)

    const worker = await Tesseract.createWorker('chi_sim+eng')
    const { data } = await worker.recognize(filePath)
    await worker.terminate()

    const imageUrl = `/uploads/${fileName}`

    return NextResponse.json({
      id: fileId,
      url: imageUrl,
      name: file.name,
      size: file.size,
      ocrText: data.text || '',
      confidence: data.confidence || 0,
    })
  } catch (error) {
    console.error('Image upload error:', error)
    return NextResponse.json(
      { error: 'Failed to upload image' },
      { status: 500 }
    )
  }
}
