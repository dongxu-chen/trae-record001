import type { TeamNamingConfig, TeamNamingRule, VariableType, NamingStyle } from '../../shared/types';
import { convertStyle } from '../utils/namingUtils.js';

const DEFAULT_TEAM_CONFIG: TeamNamingConfig = {
  teamName: 'Default Team',
  rules: [],
  defaultStyle: 'camelCase',
  enforcedStyles: {
    variable: 'camelCase',
    function: 'camelCase',
    class: 'PascalCase',
    constant: 'SCREAMING_SNAKE_CASE',
    boolean: 'camelCase'
  },
  forbiddenWords: ['temp', 'tmp', 'test', 'foo', 'bar', 'baz', 'qux', 'data', 'info', 'val', 'value'],
  preferredAbbreviations: {},
  lastSyncTime: Date.now()
};

let inMemoryTeamConfig: TeamNamingConfig = { ...DEFAULT_TEAM_CONFIG };

export function loadTeamConfig(): TeamNamingConfig {
  return inMemoryTeamConfig;
}

export function saveTeamConfig(config: TeamNamingConfig): void {
  inMemoryTeamConfig = { ...config, lastSyncTime: Date.now() };
}

export function resetTeamConfig(): void {
  inMemoryTeamConfig = { ...DEFAULT_TEAM_CONFIG, lastSyncTime: Date.now() };
}

export function addTeamRule(rule: Omit<TeamNamingRule, 'id' | 'createdAt'>): TeamNamingRule {
  const config = loadTeamConfig();
  const newRule: TeamNamingRule = {
    ...rule,
    id: `rule-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    createdAt: Date.now()
  };
  
  config.rules.push(newRule);
  saveTeamConfig(config);
  
  return newRule;
}

export function updateTeamRule(id: string, updates: Partial<TeamNamingRule>): TeamNamingRule | null {
  const config = loadTeamConfig();
  const ruleIndex = config.rules.findIndex(r => r.id === id);
  
  if (ruleIndex === -1) return null;
  
  config.rules[ruleIndex] = { ...config.rules[ruleIndex], ...updates };
  saveTeamConfig(config);
  
  return config.rules[ruleIndex];
}

export function deleteTeamRule(id: string): boolean {
  const config = loadTeamConfig();
  const initialLength = config.rules.length;
  config.rules = config.rules.filter(r => r.id !== id);
  saveTeamConfig(config);
  
  return config.rules.length < initialLength;
}

export function getApplicableRules(variableType: VariableType): TeamNamingRule[] {
  const config = loadTeamConfig();
  return config.rules
    .filter(rule => 
      rule.enabled && 
      (rule.variableTypes.length === 0 || rule.variableTypes.includes(variableType))
    )
    .sort((a, b) => b.priority - a.priority);
}

export function applyTeamRules(words: string[], variableType: VariableType): string[] {
  const rules = getApplicableRules(variableType);
  let result = [...words];
  
  for (const rule of rules) {
    if (rule.type === 'prefix' && rule.value) {
      if (!result[0]?.toLowerCase().startsWith(rule.value.toLowerCase())) {
        result = [rule.value, ...result];
      }
    }
    
    if (rule.type === 'suffix' && rule.value) {
      if (!result[result.length - 1]?.toLowerCase().endsWith(rule.value.toLowerCase())) {
        result = [...result, rule.value];
      }
    }
  }
  
  return result;
}

export function validateAgainstTeamRules(name: string, variableType: VariableType): {
  valid: boolean;
  violations: Array<{ rule: string; message: string }>;
  suggestions: string[];
} {
  const config = loadTeamConfig();
  const rules = getApplicableRules(variableType);
  const violations: Array<{ rule: string; message: string }> = [];
  const suggestions: string[] = [];
  const lowerName = name.toLowerCase();
  
  for (const rule of rules) {
    if (rule.type === 'forbidden' && rule.value) {
      if (lowerName.includes(rule.value.toLowerCase())) {
        violations.push({
          rule: rule.name,
          message: `名称包含禁用词: ${rule.value}`
        });
      }
    }
    
    if (rule.type === 'required' && rule.value) {
      if (!lowerName.includes(rule.value.toLowerCase())) {
        violations.push({
          rule: rule.name,
          message: `名称必须包含: ${rule.value}`
        });
      }
    }
    
    if (rule.type === 'prefix' && rule.value) {
      if (!lowerName.startsWith(rule.value.toLowerCase())) {
        violations.push({
          rule: rule.name,
          message: `名称必须以 ${rule.value} 开头`
        });
        suggestions.push(rule.value + name.charAt(0).toUpperCase() + name.slice(1));
      }
    }
    
    if (rule.type === 'suffix' && rule.value) {
      if (!lowerName.endsWith(rule.value.toLowerCase())) {
        violations.push({
          rule: rule.name,
          message: `名称必须以 ${rule.value} 结尾`
        });
        suggestions.push(name + rule.value.charAt(0).toUpperCase() + rule.value.slice(1));
      }
    }
  }
  
  for (const word of config.forbiddenWords) {
    if (lowerName === word.toLowerCase() || lowerName.includes(word.toLowerCase())) {
      violations.push({
        rule: 'Forbidden Words',
        message: `名称包含禁用词汇: ${word}`
      });
    }
  }
  
  const enforcedStyle = config.enforcedStyles[variableType];
  if (enforcedStyle) {
    const styledName = convertStyle(name.split(/[-_]/), enforcedStyle);
    if (styledName !== name) {
      violations.push({
        rule: 'Style Enforcement',
        message: `${variableType} 必须使用 ${enforcedStyle} 风格`
      });
      if (!suggestions.includes(styledName)) {
        suggestions.push(styledName);
      }
    }
  }
  
  return {
    valid: violations.length === 0,
    violations,
    suggestions
  };
}

export function getEnforcedStyle(variableType: VariableType): NamingStyle {
  const config = loadTeamConfig();
  return config.enforcedStyles[variableType] || config.defaultStyle;
}

export function setEnforcedStyle(variableType: VariableType, style: NamingStyle): void {
  const config = loadTeamConfig();
  config.enforcedStyles[variableType] = style;
  saveTeamConfig(config);
}

export function addForbiddenWord(word: string): void {
  const config = loadTeamConfig();
  if (!config.forbiddenWords.includes(word)) {
    config.forbiddenWords.push(word);
    saveTeamConfig(config);
  }
}

export function removeForbiddenWord(word: string): void {
  const config = loadTeamConfig();
  config.forbiddenWords = config.forbiddenWords.filter(w => w !== word);
  saveTeamConfig(config);
}

export function setPreferredAbbreviation(abbreviation: string, full: string): void {
  const config = loadTeamConfig();
  config.preferredAbbreviations[abbreviation] = full;
  saveTeamConfig(config);
}

export function removePreferredAbbreviation(abbreviation: string): void {
  const config = loadTeamConfig();
  delete config.preferredAbbreviations[abbreviation];
  saveTeamConfig(config);
}

export function syncTeamConfig(remoteConfig: Partial<TeamNamingConfig>): TeamNamingConfig {
  const currentConfig = loadTeamConfig();
  const mergedConfig: TeamNamingConfig = {
    ...currentConfig,
    ...remoteConfig,
    lastSyncTime: Date.now()
  };
  saveTeamConfig(mergedConfig);
  return mergedConfig;
}

export function exportTeamConfig(): string {
  const config = loadTeamConfig();
  return JSON.stringify(config, null, 2);
}

export function importTeamConfig(json: string): boolean {
  try {
    const config = JSON.parse(json) as TeamNamingConfig;
    saveTeamConfig({
      ...config,
      lastSyncTime: Date.now()
    });
    return true;
  } catch (e) {
    return false;
  }
}

export function generatePresetRules(preset: 'react' | 'vue' | 'angular' | 'python' | 'java' | 'go'): TeamNamingRule[] {
  const presets: Record<string, TeamNamingRule[]> = {
    react: [
      {
        id: 'react-component',
        name: '组件命名',
        description: 'React 组件必须使用 PascalCase',
        type: 'pattern',
        value: 'PascalCase',
        variableTypes: ['class'],
        enabled: true,
        priority: 100,
        createdAt: Date.now()
      },
      {
        id: 'react-hook',
        name: 'Hook 命名',
        description: '自定义 Hook 必须以 use 开头',
        type: 'prefix',
        value: 'use',
        variableTypes: ['function'],
        enabled: true,
        priority: 90,
        createdAt: Date.now()
      },
      {
        id: 'react-boolean-prop',
        name: '布尔属性',
        description: '布尔属性使用 is/has 前缀',
        type: 'prefix',
        value: 'is',
        variableTypes: ['boolean'],
        enabled: true,
        priority: 80,
        createdAt: Date.now()
      }
    ],
    vue: [
      {
        id: 'vue-component',
        name: '组件命名',
        description: 'Vue 组件必须使用 PascalCase',
        type: 'pattern',
        value: 'PascalCase',
        variableTypes: ['class'],
        enabled: true,
        priority: 100,
        createdAt: Date.now()
      },
      {
        id: 'vue-composable',
        name: 'Composable 命名',
        description: 'Composable 必须使用 use 前缀',
        type: 'prefix',
        value: 'use',
        variableTypes: ['function'],
        enabled: true,
        priority: 90,
        createdAt: Date.now()
      }
    ],
    angular: [
      {
        id: 'ng-class',
        name: '类后缀',
        description: 'Angular 类必须添加类型后缀',
        type: 'suffix',
        value: 'Component',
        variableTypes: ['class'],
        enabled: true,
        priority: 100,
        createdAt: Date.now()
      },
      {
        id: 'ng-service',
        name: '服务后缀',
        description: '服务类必须以 Service 结尾',
        type: 'suffix',
        value: 'Service',
        variableTypes: ['class'],
        enabled: true,
        priority: 90,
        createdAt: Date.now()
      }
    ],
    python: [
      {
        id: 'py-function',
        name: '函数命名',
        description: 'Python 函数使用 snake_case',
        type: 'pattern',
        value: 'snake_case',
        variableTypes: ['function'],
        enabled: true,
        priority: 100,
        createdAt: Date.now()
      },
      {
        id: 'py-class',
        name: '类命名',
        description: 'Python 类使用 PascalCase',
        type: 'pattern',
        value: 'PascalCase',
        variableTypes: ['class'],
        enabled: true,
        priority: 100,
        createdAt: Date.now()
      },
      {
        id: 'py-constant',
        name: '常量命名',
        description: 'Python 常量使用 UPPER_SNAKE_CASE',
        type: 'pattern',
        value: 'SCREAMING_SNAKE_CASE',
        variableTypes: ['constant'],
        enabled: true,
        priority: 100,
        createdAt: Date.now()
      }
    ],
    java: [
      {
        id: 'java-class',
        name: '类命名',
        description: 'Java 类使用 PascalCase',
        type: 'pattern',
        value: 'PascalCase',
        variableTypes: ['class'],
        enabled: true,
        priority: 100,
        createdAt: Date.now()
      },
      {
        id: 'java-constant',
        name: '常量命名',
        description: 'Java 常量使用 UPPER_SNAKE_CASE',
        type: 'pattern',
        value: 'SCREAMING_SNAKE_CASE',
        variableTypes: ['constant'],
        enabled: true,
        priority: 100,
        createdAt: Date.now()
      }
    ],
    go: [
      {
        id: 'go-exported',
        name: '导出命名',
        description: '导出函数和类型使用 PascalCase',
        type: 'pattern',
        value: 'PascalCase',
        variableTypes: ['function', 'class'],
        enabled: true,
        priority: 100,
        createdAt: Date.now()
      },
      {
        id: 'go-unexported',
        name: '私有命名',
        description: '私有变量使用 camelCase',
        type: 'pattern',
        value: 'camelCase',
        variableTypes: ['variable'],
        enabled: true,
        priority: 90,
        createdAt: Date.now()
      }
    ]
  };
  
  return presets[preset] || [];
}
