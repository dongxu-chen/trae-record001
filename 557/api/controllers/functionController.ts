import type { Request, Response } from 'express'
import { validateExpression as validate, computeDerivative as compute, evaluateExpression as evaluate } from '../services/mathService.js'

export const validateExpression = async (req: Request, res: Response): Promise<void> => {
  try {
    const { expression } = req.body

    if (!expression) {
      res.status(400).json({
        valid: false,
        error: '表达式不能为空',
      })
      return
    }

    const result = validate(expression)

    res.status(200).json(result)
  } catch (error) {
    res.status(400).json({
      valid: false,
      error: error instanceof Error ? error.message : '表达式无效',
    })
  }
}

export const computeDerivative = async (req: Request, res: Response): Promise<void> => {
  try {
    const { expression, variable = 'x' } = req.body

    if (!expression) {
      res.status(400).json({
        success: false,
        error: '表达式不能为空',
      })
      return
    }

    const result = compute(expression, variable)

    res.status(200).json(result)
  } catch (error) {
    res.status(400).json({
      success: false,
      error: error instanceof Error ? error.message : '求导失败',
    })
  }
}

export const evaluateExpression = async (req: Request, res: Response): Promise<void> => {
  try {
    const { expression, xValues } = req.body

    if (!expression) {
      res.status(400).json({
        success: false,
        error: '表达式不能为空',
        yValues: [],
      })
      return
    }

    if (!Array.isArray(xValues)) {
      res.status(400).json({
        success: false,
        error: 'xValues 必须是数字数组',
        yValues: [],
      })
      return
    }

    const result = evaluate(expression, xValues)

    res.status(200).json(result)
  } catch (error) {
    res.status(400).json({
      success: false,
      error: error instanceof Error ? error.message : '计算失败',
      yValues: [],
    })
  }
}
