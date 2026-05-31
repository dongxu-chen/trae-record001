import { Request, Response } from 'express';
import type { NamingRequest, NamingResponse, ConvertRequest, ConvertResponse } from '../../shared/types';
import { generateRecommendations, convertNamingStyle } from '../services/namingService.js';
import { detectLanguage } from '../services/languageService.js';
import { addToHistory } from '../services/learningService.js';
import { inferTypeFromContext } from '../services/typeInferenceService.js';

export async function recommendNames(req: Request, res: Response) {
  const startTime = Date.now();
  
  try {
    const { input, inputType = 'description', targetStyle, variableType, context } = req.body as NamingRequest;
    
    if (!input || input.trim().length === 0) {
      return res.status(400).json({
        success: false,
        error: '输入不能为空'
      });
    }
    
    const detectedLanguage = detectLanguage(input);
    const typeInference = context ? inferTypeFromContext(context, input) : null;
    const recommendations = generateRecommendations(input, targetStyle, variableType, 10, context);
    
    const processingTime = Date.now() - startTime;
    
    const response: NamingResponse = {
      success: true,
      recommendations,
      detectedLanguage,
      detectedType: recommendations[0]?.type || 'variable',
      processingTime,
      typeInference
    };
    
    res.json(response);
  } catch (error) {
    console.error('命名推荐错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function convertName(req: Request, res: Response) {
  try {
    const { name, targetStyle } = req.body as ConvertRequest;
    
    if (!name || name.trim().length === 0) {
      return res.status(400).json({
        success: false,
        error: '名称不能为空'
      });
    }
    
    const result = convertNamingStyle(name, targetStyle);
    
    const response: ConvertResponse = {
      success: true,
      result
    };
    
    res.json(response);
  } catch (error) {
    console.error('命名转换错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function recordSelection(req: Request, res: Response) {
  try {
    const { input, selectedName, style, feedback } = req.body;
    
    const historyItem = addToHistory({
      input,
      selectedName,
      style,
      feedback
    });
    
    res.json({
      success: true,
      data: historyItem
    });
  } catch (error) {
    console.error('记录选择错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}
