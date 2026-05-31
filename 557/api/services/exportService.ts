import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const tempDir = path.join(__dirname, '..', 'temp')

export async function exportPNG(
  imageData: string,
  width: number,
  height: number,
): Promise<{ success: boolean; downloadUrl?: string; error?: string }> {
  try {
    if (!imageData || !imageData.startsWith('data:image/png;base64,')) {
      return { success: false, error: '无效的 imageData 格式，必须是 base64 编码的 PNG 图片' }
    }

    if (typeof width !== 'number' || width <= 0 || !isFinite(width)) {
      return { success: false, error: '无效的 width 参数' }
    }

    if (typeof height !== 'number' || height <= 0 || !isFinite(height)) {
      return { success: false, error: '无效的 height 参数' }
    }

    const base64Data = imageData.replace(/^data:image\/png;base64,/, '')
    const buffer = Buffer.from(base64Data, 'base64')

    const timestamp = Date.now()
    const filename = `graph_${timestamp}.png`
    const filePath = path.join(tempDir, filename)

    try {
      await fs.access(tempDir)
    } catch {
      await fs.mkdir(tempDir, { recursive: true })
    }

    await fs.writeFile(filePath, buffer)

    const downloadUrl = `/api/download/${filename}`

    return { success: true, downloadUrl }
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : '未知错误'
    return { success: false, error: `导出 PNG 失败: ${errorMessage}` }
  }
}

export async function savePNG(imageData: string, width: number, height: number): Promise<string> {
  const result = await exportPNG(imageData, width, height)
  if (!result.success || !result.downloadUrl) {
    throw new Error(result.error || '保存 PNG 失败')
  }
  const filename = result.downloadUrl.replace('/api/download/', '')
  return filename
}

export function getPNGPath(filename: string): string | null {
  if (!filename || !/^graph_\d+\.png$/.test(filename)) {
    return null
  }
  const filePath = path.join(tempDir, filename)
  return filePath
}
