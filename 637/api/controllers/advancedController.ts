import { Request, Response } from 'express';
import type {
  TeamNamingConfig,
  TeamNamingRule,
  BatchRenameRequest,
  BatchRenameResult,
  ConflictDetectionRequest,
  ConflictDetectionResult
} from '../../shared/types';
import {
  loadTeamConfig,
  saveTeamConfig,
  resetTeamConfig,
  addTeamRule,
  updateTeamRule,
  deleteTeamRule,
  validateAgainstTeamRules,
  setEnforcedStyle,
  addForbiddenWord,
  removeForbiddenWord,
  syncTeamConfig,
  exportTeamConfig,
  importTeamConfig,
  generatePresetRules
} from '../services/teamNamingService.js';
import {
  performBatchRename,
  detectVariablesInCode,
  generateDiff,
  validateRename
} from '../services/batchRenameService.js';
import {
  detectConflicts,
  detectAllConflicts,
  validateName,
  checkScopeConflicts
} from '../services/conflictDetectionService.js';

export async function getTeamConfig(req: Request, res: Response) {
  try {
    const config = loadTeamConfig();
    res.json({
      success: true,
      data: config
    });
  } catch (error) {
    console.error('获取团队配置错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function updateTeamConfig(req: Request, res: Response) {
  try {
    const config = req.body as TeamNamingConfig;
    saveTeamConfig(config);
    
    res.json({
      success: true,
      message: '配置已更新'
    });
  } catch (error) {
    console.error('更新团队配置错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function resetConfig(req: Request, res: Response) {
  try {
    resetTeamConfig();
    res.json({
      success: true,
      message: '配置已重置'
    });
  } catch (error) {
    console.error('重置配置错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function addRule(req: Request, res: Response) {
  try {
    const rule = req.body as Omit<TeamNamingRule, 'id' | 'createdAt'>;
    const newRule = addTeamRule(rule);
    
    res.json({
      success: true,
      data: newRule
    });
  } catch (error) {
    console.error('添加规则错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function updateRule(req: Request, res: Response) {
  try {
    const { id } = req.params;
    const updates = req.body as Partial<TeamNamingRule>;
    const updatedRule = updateTeamRule(id, updates);
    
    if (!updatedRule) {
      return res.status(404).json({
        success: false,
        error: '规则未找到'
      });
    }
    
    res.json({
      success: true,
      data: updatedRule
    });
  } catch (error) {
    console.error('更新规则错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function deleteRule(req: Request, res: Response) {
  try {
    const { id } = req.params;
    const deleted = deleteTeamRule(id);
    
    if (!deleted) {
      return res.status(404).json({
        success: false,
        error: '规则未找到'
      });
    }
    
    res.json({
      success: true,
      message: '规则已删除'
    });
  } catch (error) {
    console.error('删除规则错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function validateNameAgainstRules(req: Request, res: Response) {
  try {
    const { name, variableType = 'variable' } = req.body;
    
    if (!name) {
      return res.status(400).json({
        success: false,
        error: '名称不能为空'
      });
    }
    
    const result = validateAgainstTeamRules(name, variableType);
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('验证名称错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function addForbiddenWordHandler(req: Request, res: Response) {
  try {
    const { word } = req.body;
    
    if (!word) {
      return res.status(400).json({
        success: false,
        error: '词汇不能为空'
      });
    }
    
    addForbiddenWord(word);
    
    res.json({
      success: true,
      message: '已添加禁用词'
    });
  } catch (error) {
    console.error('添加禁用词错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function removeForbiddenWordHandler(req: Request, res: Response) {
  try {
    const { word } = req.params;
    removeForbiddenWord(word);
    
    res.json({
      success: true,
      message: '已移除禁用词'
    });
  } catch (error) {
    console.error('移除禁用词错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function syncConfig(req: Request, res: Response) {
  try {
    const remoteConfig = req.body as Partial<TeamNamingConfig>;
    const mergedConfig = syncTeamConfig(remoteConfig);
    
    res.json({
      success: true,
      data: mergedConfig
    });
  } catch (error) {
    console.error('同步配置错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function exportConfig(req: Request, res: Response) {
  try {
    const json = exportTeamConfig();
    
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Content-Disposition', 'attachment; filename="team-naming-config.json"');
    res.send(json);
  } catch (error) {
    console.error('导出配置错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function importConfig(req: Request, res: Response) {
  try {
    const { json } = req.body;
    const success = importTeamConfig(json);
    
    if (!success) {
      return res.status(400).json({
        success: false,
        error: '配置格式无效'
      });
    }
    
    res.json({
      success: true,
      message: '配置已导入'
    });
  } catch (error) {
    console.error('导入配置错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function getPresetRules(req: Request, res: Response) {
  try {
    const { preset } = req.params;
    const rules = generatePresetRules(preset as any);
    
    res.json({
      success: true,
      data: rules
    });
  } catch (error) {
    console.error('获取预设规则错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function batchRename(req: Request, res: Response) {
  try {
    const request = req.body as BatchRenameRequest;
    const result = performBatchRename(request);
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('批量重命名错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function detectVariables(req: Request, res: Response) {
  try {
    const { code, language = 'javascript' } = req.body;
    
    if (!code) {
      return res.status(400).json({
        success: false,
        error: '代码不能为空'
      });
    }
    
    const variables = detectVariablesInCode(code, language);
    
    res.json({
      success: true,
      data: variables
    });
  } catch (error) {
    console.error('检测变量错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function generateDiffHandler(req: Request, res: Response) {
  try {
    const { oldCode, newCode } = req.body;
    
    if (!oldCode || !newCode) {
      return res.status(400).json({
        success: false,
        error: '新旧代码不能为空'
      });
    }
    
    const diff = generateDiff(oldCode, newCode);
    
    res.json({
      success: true,
      data: diff
    });
  } catch (error) {
    console.error('生成差异错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function validateRenameHandler(req: Request, res: Response) {
  try {
    const { code, oldName, newName } = req.body;
    
    if (!oldName || !newName) {
      return res.status(400).json({
        success: false,
        error: '新旧名称不能为空'
      });
    }
    
    const result = validateRename(code || '', oldName, newName);
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('验证重命名错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function detectConflictsHandler(req: Request, res: Response) {
  try {
    const request = req.body as ConflictDetectionRequest;
    
    if (!request.name) {
      return res.status(400).json({
        success: false,
        error: '名称不能为空'
      });
    }
    
    const result = detectConflicts(request);
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('检测冲突错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function detectAllConflictsHandler(req: Request, res: Response) {
  try {
    const { code } = req.body;
    
    if (!code) {
      return res.status(400).json({
        success: false,
        error: '代码不能为空'
      });
    }
    
    const conflicts = detectAllConflicts(code);
    
    res.json({
      success: true,
      data: conflicts
    });
  } catch (error) {
    console.error('检测所有冲突错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function validateNameHandler(req: Request, res: Response) {
  try {
    const { name, code, language } = req.body;
    
    if (!name) {
      return res.status(400).json({
        success: false,
        error: '名称不能为空'
      });
    }
    
    const result = validateName(name, code, language);
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('验证名称错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function checkScopeConflictsHandler(req: Request, res: Response) {
  try {
    const { name, code } = req.body;
    
    if (!name || !code) {
      return res.status(400).json({
        success: false,
        error: '名称和代码不能为空'
      });
    }
    
    const result = checkScopeConflicts(name, code);
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('检查作用域冲突错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}
