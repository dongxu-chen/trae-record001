import type { Request, Response } from 'express'
import { savePNG, getPNGPath } from '../services/exportService.js'

export const exportPNG = async (req: Request, res: Response): Promise<void> => {
  try {
    const { imageData, width, height } = req.body

    if (!imageData) {
      res.status(400).json({
        success: false,
        error: 'imageData is required',
      })
      return
    }

    if (typeof width !== 'number' || typeof height !== 'number') {
      res.status(400).json({
        success: false,
        error: 'width and height must be numbers',
      })
      return
    }

    const filename = await savePNG(imageData, width, height)

    res.status(200).json({
      success: true,
      data: {
        filename,
        downloadUrl: `/api/download/${filename}`,
      },
    })
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Failed to export PNG',
    })
  }
}

export const downloadPNG = async (req: Request, res: Response): Promise<void> => {
  try {
    const { filename } = req.params

    if (!filename) {
      res.status(400).json({
        success: false,
        error: 'filename is required',
      })
      return
    }

    const filePath = getPNGPath(filename)

    if (!filePath) {
      res.status(404).json({
        success: false,
        error: 'File not found',
      })
      return
    }

    res.download(filePath, filename, (error) => {
      if (error) {
        res.status(500).json({
          success: false,
          error: 'Failed to download file',
        })
      }
    })
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Failed to download PNG',
    })
  }
}
