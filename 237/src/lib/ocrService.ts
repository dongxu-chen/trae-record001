import Tesseract from 'tesseract.js'
import { saveImageOffline, getImageOffline } from './offlineDB'

let worker: Tesseract.Worker | null = null

export async function initOCR(): Promise<void> {
  if (!worker) {
    worker = await Tesseract.createWorker('chi_sim+eng', 1, {
      logger: m => console.log(m),
    })
  }
}

export async function recognizeImage(imageFile: File | Blob): Promise<{
  text: string
  confidence: number
}> {
  await initOCR()

  if (!worker) {
    throw new Error('OCR not initialized')
  }

  try {
    const { data } = await worker.recognize(imageFile)
    return {
      text: data.text || '',
      confidence: data.confidence || 0,
    }
  } catch (error) {
    console.error('OCR recognition error:', error)
    throw error
  }
}

export async function recognizeAndSaveImage(
  imageFile: File
): Promise<{
  imageId: string
  text: string
  confidence: number
  imageUrl: string
}> {
  const imageId = `img-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  
  const { text, confidence } = await recognizeImage(imageFile)
  
  const reader = new FileReader()
  const imageUrl = await new Promise<string>((resolve, reject) => {
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(imageFile)
  })

  await saveImageOffline(imageId, imageFile, text)

  return {
    imageId,
    text,
    confidence,
    imageUrl,
  }
}

export async function getImageWithOCR(imageId: string): Promise<{
  imageUrl: string
  ocrText: string
} | null> {
  const imageData = await getImageOffline(imageId)
  if (!imageData) return null

  const imageUrl = await new Promise<string>((resolve) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.readAsDataURL(imageData.blob)
  })

  return {
    imageUrl,
    ocrText: imageData.ocrText || '',
  }
}

export function extractTextForSearch(ocrText: string): string {
  return ocrText
    .replace(/\s+/g, ' ')
    .replace(/[^\w\u4e00-\u9fa5]/g, ' ')
    .trim()
}

export async function terminateOCR(): Promise<void> {
  if (worker) {
    await worker.terminate()
    worker = null
  }
}
