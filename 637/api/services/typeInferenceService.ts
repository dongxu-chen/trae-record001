import type { VariableType } from '../../shared/types';

export interface InferredTypeInfo {
  type: VariableType;
  confidence: number;
  hints: string[];
  originalContext: string;
}

const typePatterns: Record<VariableType, RegExp[]> = {
  function: [
    /function\s+(\w+)/g,
    /const\s+(\w+)\s*=\s*(?:async\s+)?\s*\([^)]*\)\s*=>/g,
    /const\s+(\w+)\s*=\s*function/g,
    /(\w+)\s*:\s*\([^)]*\)\s*=>/g,
    /def\s+(\w+)/g,
    /func\s+(\w+)/g,
    /fn\s+(\w+)/g,
    /method\s+(\w+)/gi
  ],
  class: [
    /class\s+(\w+)/g,
    /interface\s+(\w+)/g,
    /type\s+(\w+)\s*=/g,
    /struct\s+(\w+)/g,
    /enum\s+(\w+)/g,
    /class_def\s+(\w+)/gi
  ],
  constant: [
    /const\s+([A-Z_][A-Z0-9_]+)/g,
    /constexpr\s+(\w+)/g,
    /final\s+(\w+)/g,
    /readonly\s+(\w+)/gi,
    /#define\s+(\w+)/g
  ],
  boolean: [
    /\b(is|has|can|should|will|did|are|was|were|been|being|have|had|do|does|did)\s+([A-Z][a-zA-Z]+)/g,
    /(\w+)\s*:\s*boolean/g,
    /(\w+)\s*:\s*Bool/g,
    /\b(is|has|can|should)[A-Z][a-zA-Z]+\b/g
  ],
  variable: []
};

const semanticTypeHints: Record<string, VariableType> = {
  'manager': 'class',
  'controller': 'class',
  'service': 'class',
  'handler': 'class',
  'factory': 'class',
  'builder': 'class',
  'provider': 'class',
  'repository': 'class',
  'util': 'class',
  'utils': 'class',
  'helper': 'class',
  'get': 'function',
  'set': 'function',
  'calculate': 'function',
  'compute': 'function',
  'process': 'function',
  'handle': 'function',
  'create': 'function',
  'update': 'function',
  'delete': 'function',
  'fetch': 'function',
  'load': 'function',
  'save': 'function',
  'validate': 'function',
  'check': 'function',
  'is': 'boolean',
  'has': 'boolean',
  'can': 'boolean',
  'should': 'boolean',
  'enabled': 'boolean',
  'disabled': 'boolean',
  'active': 'boolean',
  'visible': 'boolean',
  'valid': 'boolean',
  'invalid': 'boolean',
  'max': 'constant',
  'min': 'constant',
  'default': 'constant',
  'config': 'constant',
  'timeout': 'constant',
  'interval': 'constant',
  'threshold': 'constant'
};

const commonTypeKeywords: Record<VariableType, string[]> = {
  function: ['function', 'method', 'func', 'def', 'async', 'callback', 'handler'],
  class: ['class', 'interface', 'type', 'struct', 'enum', 'abstract', 'implements', 'extends'],
  constant: ['const', 'constant', 'final', 'readonly', 'immutable'],
  boolean: ['boolean', 'bool', 'true', 'false', 'predicate', 'flag'],
  variable: ['let', 'var', 'variable', 'field', 'property', 'attr']
};

export function inferTypeFromContext(context: string, input?: string): InferredTypeInfo {
  const hints: string[] = [];
  let detectedType: VariableType = 'variable';
  let confidence = 0.3;
  
  if (!context && !input) {
    return {
      type: 'variable',
      confidence: 0.1,
      hints: ['No context provided'],
      originalContext: context || ''
    };
  }
  
  const fullContext = `${context || ''} ${input || ''}`.toLowerCase();
  
  for (const [type, patterns] of Object.entries(typePatterns)) {
    for (const pattern of patterns) {
      const matches = [...fullContext.matchAll(pattern)];
      if (matches.length > 0) {
        detectedType = type as VariableType;
        confidence = Math.max(confidence, 0.7 + matches.length * 0.05);
        hints.push(`Pattern match: ${pattern.source}`);
      }
    }
  }
  
  for (const [keyword, type] of Object.entries(semanticTypeHints)) {
    if (fullContext.includes(keyword.toLowerCase())) {
      if (type === detectedType) {
        confidence = Math.min(0.95, confidence + 0.05);
      } else if (confidence < 0.6) {
        detectedType = type;
        confidence = 0.5;
      }
      hints.push(`Semantic hint: ${keyword} -> ${type}`);
    }
  }
  
  for (const [type, keywords] of Object.entries(commonTypeKeywords)) {
    const foundKeywords = keywords.filter(k => fullContext.includes(k.toLowerCase()));
    if (foundKeywords.length > 0) {
      if (type === detectedType) {
        confidence = Math.min(0.95, confidence + foundKeywords.length * 0.03);
      } else if (confidence < 0.5) {
        detectedType = type as VariableType;
        confidence = 0.4;
      }
      hints.push(`Type keywords: ${foundKeywords.join(', ')}`);
    }
  }
  
  if (input) {
    const lowerInput = input.toLowerCase();
    if (lowerInput.startsWith('is') || lowerInput.startsWith('has') || 
        lowerInput.startsWith('can') || lowerInput.startsWith('should')) {
      if (detectedType !== 'boolean') {
        detectedType = 'boolean';
        confidence = Math.max(confidence, 0.6);
        hints.push('Boolean prefix detected');
      }
    }
    
    if (/^[A-Z_][A-Z0-9_]+$/.test(input)) {
      if (detectedType !== 'constant') {
        detectedType = 'constant';
        confidence = Math.max(confidence, 0.8);
        hints.push('UPPER_SNAKE_CASE indicates constant');
      }
    }
  }
  
  const codeIndicators = ['{', '}', ';', '=', ':', '(', ')', '=>', 'function', 'class', 'const'];
  const hasCodeContext = codeIndicators.some(ind => (context || '').includes(ind));
  if (hasCodeContext) {
    confidence = Math.min(0.95, confidence + 0.1);
    hints.push('Code context detected');
  }
  
  return {
    type: detectedType,
    confidence: Math.min(0.98, Math.max(0.1, confidence)),
    hints: hints.slice(0, 5),
    originalContext: context || ''
  };
}

export function getTypeNamingConventions(type: VariableType): {
  prefixes: string[];
  suffixes: string[];
  preferredStyles: string[];
} {
  const conventions: Record<VariableType, {
    prefixes: string[];
    suffixes: string[];
    preferredStyles: string[];
  }> = {
    function: {
      prefixes: ['get', 'set', 'is', 'has', 'can', 'should', 'calculate', 'process', 'handle', 'create', 'update', 'delete', 'fetch', 'load', 'save', 'validate', 'check'],
      suffixes: [],
      preferredStyles: ['camelCase', 'snake_case']
    },
    class: {
      prefixes: [],
      suffixes: ['Manager', 'Controller', 'Service', 'Handler', 'Factory', 'Builder', 'Provider', 'Repository', 'Util', 'Helper'],
      preferredStyles: ['PascalCase']
    },
    constant: {
      prefixes: ['MAX', 'MIN', 'DEFAULT', 'CONFIG', 'TIMEOUT', 'INTERVAL', 'THRESHOLD'],
      suffixes: [],
      preferredStyles: ['SCREAMING_SNAKE_CASE', 'PascalCase']
    },
    boolean: {
      prefixes: ['is', 'has', 'can', 'should', 'are', 'were', 'will', 'did'],
      suffixes: ['Enabled', 'Disabled', 'Active', 'Visible', 'Valid', 'Invalid'],
      preferredStyles: ['camelCase', 'snake_case']
    },
    variable: {
      prefixes: [],
      suffixes: ['Count', 'List', 'Array', 'Map', 'Set', 'Id', 'Name', 'Type', 'Status', 'Date', 'Time', 'Info', 'Data'],
      preferredStyles: ['camelCase', 'snake_case']
    }
  };
  
  return conventions[type];
}

export function applyTypeNamingHints(words: string[], type: VariableType): string[] {
  const conventions = getTypeNamingConventions(type);
  const result = [...words];
  const lowerWords = words.map(w => w.toLowerCase());
  
  if (type === 'boolean' && words.length > 0) {
    const hasPrefix = conventions.prefixes.some(p => lowerWords[0] === p.toLowerCase());
    if (!hasPrefix && !lowerWords[0].match(/^(is|has|can|should)/)) {
      result.unshift('is');
    }
  }
  
  if (type === 'class' && words.length > 0) {
    const hasSuffix = conventions.suffixes.some(s => 
      lowerWords[lowerWords.length - 1] === s.toLowerCase()
    );
    if (!hasSuffix && words.length < 3) {
      const commonSuffixes = ['Manager', 'Service', 'Controller', 'Handler'];
      const contextSuffix = commonSuffixes.find(s => 
        words.some(w => s.toLowerCase().includes(w.toLowerCase()))
      );
      if (contextSuffix) {
        result.push(contextSuffix);
      }
    }
  }
  
  return result;
}
