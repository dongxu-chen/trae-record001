import { getComponentById } from '../data/regexComponents';

export const MUTEX_RULES = [
  {
    components: ['digit', 'word'],
    reason: '\\w 已包含 \\d，重复定义'
  },
  {
    components: ['letter', 'word'],
    reason: '\\w 已包含字母，重复定义'
  },
  {
    components: ['digit', 'letter'],
    reason: '可以使用 \\w 替代'
  },
  {
    components: ['start', 'start'],
    reason: '重复的行首锚点'
  },
  {
    components: ['end', 'end'],
    reason: '重复的行尾锚点'
  }
];

export const OPTIMIZATION_RULES = [
  {
    name: '合并字符类',
    description: '[0-9] 可以简化为 \\d',
    pattern: /\[0-9\]/g,
    replacement: '\\d',
    improvement: '更简洁，性能更好'
  },
  {
    name: '合并字符类',
    description: '[a-zA-Z0-9_] 可以简化为 \\w',
    pattern: /\[a-zA-Z0-9_\]/g,
    replacement: '\\w',
    improvement: '更简洁，性能更好'
  },
  {
    name: '合并字符类',
    description: '[A-Za-z] 可以简化为 [a-zA-Z]',
    pattern: /\[A-Za-z\]/g,
    replacement: '[a-zA-Z]',
    improvement: '更符合标准写法'
  },
  {
    name: '简化量词',
    description: '{1,} 可以简化为 +',
    pattern: /\{1,\}/g,
    replacement: '+',
    improvement: '更简洁'
  },
  {
    name: '简化量词',
    description: '{0,} 可以简化为 *',
    pattern: /\{0,\}/g,
    replacement: '*',
    improvement: '更简洁'
  },
  {
    name: '简化量词',
    description: '{0,1} 可以简化为 ?',
    pattern: /\{0,1\}/g,
    replacement: '?',
    improvement: '更简洁'
  },
  {
    name: '移除重复转义',
    description: '\\\\\\\\ 可以简化为 \\\\',
    pattern: /\\\\\\\\/g,
    replacement: '\\\\',
    improvement: '避免双重转义错误'
  },
  {
    name: '优化字符集',
    description: '[0-9a-zA-Z_] 可以简化为 \\w',
    pattern: /\[0-9a-zA-Z_\]/g,
    replacement: '\\w',
    improvement: '更简洁'
  },
  {
    name: '优化空白字符',
    description: '[ \\t\\n\\r] 可以简化为 \\s',
    pattern: /\[ \\t\\n\\r\]/g,
    replacement: '\\s',
    improvement: '更简洁，涵盖更多空白字符'
  },
  {
    name: '避免不必要的分组',
    description: '(?:\\d) 可以简化为 \\d',
    pattern: /\(\?:([^()]+)\)/g,
    replacement: '$1',
    improvement: '移除不必要的非捕获组，提高性能'
  },
  {
    name: '优化重复模式',
    description: '(\\d)\\1+ 可以考虑使用量词',
    pattern: /\(([^()]+)\)\\1\+/g,
    replacement: '($1){2,}',
    improvement: '更清晰地表达重复意图'
  },
  {
    name: '合并相邻相同字符类',
    description: '\\d\\d 可以简化为 \\d{2}',
    pattern: /(\\[dwsDWS])(?=\1)/g,
    replacement: '',
    improvement: '使用量词合并，更高效'
  }
];

export const PERFORMANCE_FACTORS = {
  backreferences: {
    name: '反向引用',
    description: '每增加一个反向引用，性能下降约 30%',
    multiplier: 1.3,
    pattern: /\\[1-9]/g
  },
  nestedGroups: {
    name: '嵌套分组',
    description: '嵌套分组会增加回溯复杂度',
    multiplier: 1.25,
    pattern: /\((?=[^()]*\()/g
  },
  alternations: {
    name: '多选分支',
    description: '多个 | 分支会增加匹配尝试次数',
    multiplier: 1.2,
    pattern: /\|/g
  },
  greedyQuantifiers: {
    name: '贪婪量词',
    description: '.* 或 .+ 可能导致大量回溯',
    multiplier: 1.5,
    pattern: /\.(\*|\+)(?!\?)/g
  },
  lazyQuantifiers: {
    name: '惰性量词',
    description: '*? 或 +? 比贪婪量词稍慢',
    multiplier: 1.15,
    pattern: /(\*|\+)\?/g
  },
  lookaheads: {
    name: '正向前瞻',
    description: '(?=...) 增加匹配复杂度',
    multiplier: 1.3,
    pattern: /\(\?=/g
  },
  lookbehinds: {
    name: '正向后顾',
    description: '(?<=...) 性能开销较大',
    multiplier: 1.4,
    pattern: /\(\?<=/g
  },
  negLookaheads: {
    name: '负向前瞻',
    description: '(?!...) 增加匹配复杂度',
    multiplier: 1.35,
    pattern: /\(\?!/g
  },
  charSets: {
    name: '复杂字符集',
    description: '长字符集 [...] 增加匹配时间',
    multiplier: 1.1,
    pattern: /\[[^\]]{10,}\]/g
  },
  exactQuantifiers: {
    name: '精确量词',
    description: '{n,m} 范围越大性能越低',
    multiplier: 1.1,
    pattern: /\{(\d+),(\d*)\}/g
  }
};

export const PASSWORD_TEMPLATES = [
  {
    id: 'password-weak',
    name: '弱密码',
    description: '至少6位，包含字母和数字',
    pattern: '^[a-zA-Z0-9]{6,}$',
    icon: '🔓',
    color: '#ef4444',
    strength: 'weak'
  },
  {
    id: 'password-medium',
    name: '中等强度密码',
    description: '至少8位，包含大小写字母和数字',
    pattern: '^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)[a-zA-Z\\d]{8,}$',
    icon: '🔐',
    color: '#f59e0b',
    strength: 'medium'
  },
  {
    id: 'password-strong',
    name: '强密码',
    description: '至少8位，包含大小写字母、数字和特殊字符',
    pattern: '^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]{8,}$',
    icon: '🔒',
    color: '#22c55e',
    strength: 'strong'
  },
  {
    id: 'password-very-strong',
    name: '极强密码',
    description: '至少12位，包含大小写字母、数字和特殊字符',
    pattern: '^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]{12,}$',
    icon: '🛡️',
    color: '#0891b2',
    strength: 'very-strong'
  },
  {
    id: 'password-no-sequence',
    name: '无连续字符密码',
    description: '不包含连续3个相同或顺序字符',
    pattern: '^(?!.*(.)\\1{2})(?!.*(012|123|234|345|456|567|678|789|abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)).{8,}$',
    icon: '🚫',
    color: '#7c3aed',
    strength: 'strong'
  }
];

export const URL_TEMPLATES = [
  {
    id: 'url-basic',
    name: '基础URL',
    description: '匹配HTTP/HTTPS网址',
    pattern: 'https?://[\\w\\-._~:/?#[\\]@!$&\'()*+,;=%]+',
    icon: '🔗',
    color: '#06b6d4'
  },
  {
    id: 'url-strict',
    name: '严格URL',
    description: '严格匹配带域名的URL',
    pattern: 'https?://(?:www\\.)?[a-zA-Z0-9][-a-zA-Z0-9]*\\.[a-zA-Z]{2,}(?:/[^\\s]*)?',
    icon: '🌐',
    color: '#0891b2'
  },
  {
    id: 'url-with-params',
    name: '带参数URL',
    description: '匹配带查询参数的URL',
    pattern: 'https?://[\\w\\-._~:/?#[\\]@!$&\'()*+,;=%]+\\?[\\w\\-._~:/?#[\\]@!$&\'()*+,;=%]*',
    icon: '📊',
    color: '#0e7490'
  },
  {
    id: 'url-image',
    name: '图片URL',
    description: '匹配图片文件URL',
    pattern: 'https?://[\\w\\-._~:/?#[\\]@!$&\'()*+,;=%]+\\.(?:jpg|jpeg|png|gif|bmp|webp|svg)',
    icon: '🖼️',
    color: '#14b8a6'
  },
  {
    id: 'url-ftp',
    name: 'FTP URL',
    description: '匹配FTP地址',
    pattern: 'ftp://[\\w\\-._~:/?#[\\]@!$&\'()*+,;=%]+',
    icon: '📁',
    color: '#6366f1'
  }
];

export const EMAIL_TEMPLATES = [
  {
    id: 'email-basic',
    name: '基础邮箱',
    description: '匹配标准邮箱格式',
    pattern: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}',
    icon: '📧',
    color: '#ef4444'
  },
  {
    id: 'email-strict',
    name: '严格邮箱',
    description: '严格匹配RFC标准邮箱',
    pattern: '[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\\.[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+)*@(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?',
    icon: '✉️',
    color: '#dc2626'
  },
  {
    id: 'email-domain',
    name: '指定域名邮箱',
    description: '仅匹配指定域名邮箱（示例：gmail.com）',
    pattern: '[a-zA-Z0-9._%+-]+@gmail\\.com',
    icon: '📩',
    color: '#b91c1c'
  },
  {
    id: 'email-corporate',
    name: '企业邮箱',
    description: '匹配企业域名邮箱',
    pattern: '[a-zA-Z0-9._%+-]+@(?!gmail\\.com|yahoo\\.com|hotmail\\.com|outlook\\.com)[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}',
    icon: '🏢',
    color: '#991b1b'
  }
];

export const OTHER_TEMPLATES = [
  {
    id: 'id-card',
    name: '身份证号',
    description: '匹配18位中国身份证号',
    pattern: '[1-9]\\d{5}(?:18|19|20)\\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\\d|3[01])\\d{3}[0-9Xx]',
    icon: '🪪',
    color: '#8b5cf6'
  },
  {
    id: 'bank-card',
    name: '银行卡号',
    description: '匹配16-19位银行卡号',
    pattern: '[1-9]\\d{15,18}',
    icon: '💳',
    color: '#7c3aed'
  },
  {
    id: 'postal-code',
    name: '邮政编码',
    description: '匹配6位中国邮政编码',
    pattern: '[1-9]\\d{5}',
    icon: '📮',
    color: '#6d28d9'
  },
  {
    id: 'license-plate',
    name: '车牌号',
    description: '匹配中国车牌号',
    pattern: '[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-HJ-NP-Z0-9]{5}',
    icon: '🚗',
    color: '#5b21b6'
  },
  {
    id: 'ipv6',
    name: 'IPv6地址',
    description: '匹配IPv6地址',
    pattern: '(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}',
    icon: '🌍',
    color: '#4c1d95'
  },
  {
    id: 'mac-address',
    name: 'MAC地址',
    description: '匹配MAC地址',
    pattern: '(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}',
    icon: '🔌',
    color: '#84cc16'
  },
  {
    id: 'hex-color',
    name: '十六进制颜色',
    description: '匹配CSS十六进制颜色值',
    pattern: '#(?:[0-9a-fA-F]{3}){1,2}',
    icon: '🎨',
    color: '#65a30d'
  },
  {
    id: 'date-iso',
    name: 'ISO日期',
    description: '匹配YYYY-MM-DD格式日期',
    pattern: '\\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\\d|3[01])',
    icon: '📅',
    color: '#4d7c0f'
  },
  {
    id: 'time-24h',
    name: '24小时制时间',
    description: '匹配HH:MM:SS格式时间',
    pattern: '(?:[01]\\d|2[0-3]):[0-5]\\d:[0-5]\\d',
    icon: '⏰',
    color: '#3f6212'
  },
  {
    id: 'uuid',
    name: 'UUID',
    description: '匹配标准UUID格式',
    pattern: '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',
    icon: '🆔',
    color: '#365314'
  },
  {
    id: 'html-tag',
    name: 'HTML标签',
    description: '匹配HTML标签',
    pattern: '<([a-zA-Z][a-zA-Z0-9]*)\\b[^>]*>(.*?)</\\1>',
    icon: '🏷️',
    color: '#166534'
  },
  {
    id: 'chinese-name',
    name: '中文姓名',
    description: '匹配2-4个汉字的中文姓名',
    pattern: '[\\u4e00-\\u9fa5]{2,4}',
    icon: '👤',
    color: '#14532d'
  }
];

export const checkMutexRules = (builderItems, newComponentId) => {
  const warnings = [];
  
  if (!builderItems || builderItems.length === 0) return warnings;
  
  const existingIds = builderItems.map(item => item.componentId);
  
  for (const rule of MUTEX_RULES) {
    const [compA, compB] = rule.components;
    if (newComponentId === compA && existingIds.includes(compB)) {
      warnings.push(rule.reason);
    }
    if (newComponentId === compB && existingIds.includes(compA)) {
      warnings.push(rule.reason);
    }
  }
  
  return warnings;
};

export const generatePattern = (builderItems) => {
  if (!builderItems || builderItems.length === 0) return '';
  
  const buildPattern = (items) => {
    let pattern = '';
    let groupStack = [];
    
    for (const item of items) {
      if (item.componentId === 'custom-pattern' && item.customPattern) {
        pattern += item.customPattern;
        continue;
      }
      
      const component = getComponentById(item.componentId);
      
      if (!component) continue;
      
      let itemPattern = component.pattern;
      
      if (component.hasInput && item.inputValue) {
        if (component.id === 'exact') {
          itemPattern = `{${item.inputValue}}`;
        } else if (component.id === 'range') {
          const [min, max] = item.inputValue.split(',');
          itemPattern = `{${min || 0},${max || ''}}`;
        }
      }
      
      if (component.isGroup) {
        const groupPattern = itemPattern;
        const openPart = groupPattern.slice(0, Math.floor(groupPattern.length / 2));
        const closePart = groupPattern.slice(Math.floor(groupPattern.length / 2));
        
        if (item.children && item.children.length > 0) {
          pattern += openPart + buildPattern(item.children) + closePart;
        } else {
          groupStack.push({ openPart, closePart });
          pattern += openPart;
        }
      } else {
        pattern += itemPattern;
      }
    }
    
    while (groupStack.length > 0) {
      const group = groupStack.pop();
      pattern += group.closePart;
    }
    
    return pattern;
  };
  
  return buildPattern(builderItems);
};

export const testPattern = (pattern, testText, flags = 'g') => {
  if (!pattern || !testText) {
    return { matches: [], isValid: true };
  }
  
  try {
    const regex = new RegExp(pattern, flags);
    const matches = [];
    let match;
    
    if (flags.includes('g')) {
      while ((match = regex.exec(testText)) !== null) {
        matches.push({
          text: match[0],
          index: match.index,
          groups: match.slice(1),
          length: match[0].length
        });
        
        if (match[0].length === 0) {
          regex.lastIndex++;
        }
      }
    } else {
      match = regex.exec(testText);
      if (match) {
        matches.push({
          text: match[0],
          index: match.index,
          groups: match.slice(1),
          length: match[0].length
        });
      }
    }
    
    return { matches, isValid: true };
  } catch (error) {
    return { matches: [], isValid: false, error: error.message };
  }
};

export const testPatternChunked = async (pattern, testText, flags = 'g', chunkSize = 10000, overlap = 100) => {
  if (!pattern || !testText) {
    return { matches: [], isValid: true, chunks: 0 };
  }
  
  const allMatches = [];
  let isValid = true;
  let errorMsg = null;
  let chunkCount = 0;
  
  try {
    new RegExp(pattern, flags);
  } catch (error) {
    return { matches: [], isValid: false, error: error.message, chunks: 0 };
  }
  
  const totalChunks = Math.ceil(testText.length / chunkSize);
  
  for (let i = 0; i < totalChunks; i++) {
    chunkCount++;
    const start = i * chunkSize;
    const end = Math.min(start + chunkSize + overlap, testText.length);
    const chunk = testText.slice(start, end);
    
    const result = testPattern(pattern, chunk, flags);
    
    if (!result.isValid) {
      isValid = false;
      errorMsg = result.error;
      break;
    }
    
    for (const match of result.matches) {
      const actualIndex = start + match.index;
      const existingMatch = allMatches.find(m => m.index === actualIndex && m.text === match.text);
      if (!existingMatch && actualIndex + match.length <= testText.length) {
        allMatches.push({
          ...match,
          index: actualIndex,
          chunk: i + 1
        });
      }
    }
    
    await new Promise(resolve => setTimeout(resolve, 0));
  }
  
  allMatches.sort((a, b) => a.index - b.index);
  
  return {
    matches: allMatches,
    isValid,
    error: errorMsg,
    chunks: chunkCount
  };
};

export const highlightMatches = (text, matches) => {
  if (!matches || matches.length === 0) return text;
  
  const sortedMatches = [...matches].sort((a, b) => a.index - b.index);
  let result = '';
  let lastIndex = 0;
  
  for (const match of sortedMatches) {
    if (match.index > lastIndex) {
      result += text.slice(lastIndex, match.index);
    }
    result += `<span class="highlight">${text.slice(match.index, match.index + match.length)}</span>`;
    lastIndex = match.index + match.length;
  }
  
  if (lastIndex < text.length) {
    result += text.slice(lastIndex);
  }
  
  return result;
};

export const escapeRegex = (str) => {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
};

export const addToGroup = (builderItems, groupId, newItem) => {
  const addToGroupRecursive = (items) => {
    return items.map(item => {
      if (item.id === groupId) {
        return {
          ...item,
          children: [...(item.children || []), newItem]
        };
      }
      if (item.children) {
        return {
          ...item,
          children: addToGroupRecursive(item.children)
        };
      }
      return item;
    });
  };
  
  return addToGroupRecursive(builderItems);
};

export const removeFromBuilder = (builderItems, itemId) => {
  const removeRecursive = (items) => {
    return items.filter(item => item.id !== itemId).map(item => {
      if (item.children) {
        return {
          ...item,
          children: removeRecursive(item.children)
        };
      }
      return item;
    });
  };
  
  return removeRecursive(builderItems);
};

export const findItemGroup = (builderItems, itemId) => {
  let groupPath = [];
  
  const findRecursive = (items, path = []) => {
    for (const item of items) {
      if (item.id === itemId) {
        groupPath = path;
        return true;
      }
      if (item.children) {
        if (findRecursive(item.children, [...path, item.id])) {
          return true;
        }
      }
    }
    return false;
  };
  
  findRecursive(builderItems);
  return groupPath;
};

export const optimizePattern = (pattern) => {
  if (!pattern) return { optimizations: [], optimizedPattern: pattern };

  const optimizations = [];
  let optimizedPattern = pattern;

  for (const rule of OPTIMIZATION_RULES) {
    let matchCount = 0;
    const testPattern = new RegExp(rule.pattern.source, rule.pattern.flags);
    
    const countMatch = pattern.match(testPattern);
    if (countMatch && countMatch.length > 0) {
      matchCount = countMatch.length;
    }

    if (matchCount > 0) {
      const matches = [...pattern.matchAll(testPattern)];
      for (const match of matches) {
        const original = match[0];
        const improved = original.replace(rule.pattern, rule.replacement);
        
        if (original !== improved) {
          optimizations.push({
            name: rule.name,
            description: rule.description,
            original,
            improved,
            improvement: rule.improvement,
            index: match.index
          });
        }
      }
      
      optimizedPattern = optimizedPattern.replace(rule.pattern, rule.replacement);
    }
  }

  const adjacentMergePattern = /(\\[dwsDWS])(?=\1)/g;
  const adjacentMatches = [...pattern.matchAll(adjacentMergePattern)];
  if (adjacentMatches.length > 0) {
    const charClasses = {};
    let i = 0;
    while (i < pattern.length) {
      const match = pattern.slice(i).match(/^\\[dwsDWS]/);
      if (match) {
        const charClass = match[0];
        charClasses[charClass] = (charClasses[charClass] || 0) + 1;
        i += charClass.length;
      } else {
        i++;
      }
    }
    
    for (const [charClass, count] of Object.entries(charClasses)) {
      if (count >= 2) {
        const originalSequence = charClass.repeat(count);
        const improved = `${charClass}{${count}}`;
        const index = pattern.indexOf(originalSequence);
        if (index !== -1) {
          optimizations.push({
            name: '合并相邻相同字符类',
            description: `${charClass}重复${count}次可以使用量词`,
            original: originalSequence,
            improved,
            improvement: '使用量词合并，更高效',
            index
          });
          optimizedPattern = optimizedPattern.replace(originalSequence, improved);
        }
      }
    }
  }

  const groupPattern = /\(([^()]*)\)\1\+/g;
  const groupMatches = [...pattern.matchAll(groupPattern)];
  for (const match of groupMatches) {
    optimizations.push({
      name: '优化重复模式',
      description: `(${match[1]})${match[1]}+ 可以使用量词`,
      original: match[0],
      improved: `(${match[1]}){2,}`,
      improvement: '更清晰地表达重复意图',
      index: match.index
    });
    optimizedPattern = optimizedPattern.replace(match[0], `(${match[1]}){2,}`);
  }

  optimizations.sort((a, b) => a.index - b.index);

  return {
    optimizations,
    optimizedPattern,
    canOptimize: optimizations.length > 0
  };
};

export const evaluatePerformance = (pattern, sampleText = '') => {
  if (!pattern) {
    return {
      score: 100,
      grade: 'N/A',
      factors: [],
      estimatedTime: 0,
      complexity: 'unknown'
    };
  }

  const factors = [];
  let baseTime = 0.01;
  let score = 100;

  for (const [key, factor] of Object.entries(PERFORMANCE_FACTORS)) {
    const matches = pattern.match(factor.pattern);
    const count = matches ? matches.length : 0;
    
    if (count > 0) {
      const impact = Math.pow(factor.multiplier, count);
      baseTime *= impact;
      score -= count * 5;
      
      factors.push({
        id: key,
        name: factor.name,
        description: factor.description,
        count,
        impact: Math.round((impact - 1) * 100),
        multiplier: factor.multiplier
      });
    }
  }

  const patternLength = pattern.length;
  if (patternLength > 100) {
    const lengthPenalty = Math.floor((patternLength - 100) / 50) * 5;
    score -= lengthPenalty;
    factors.push({
      id: 'long-pattern',
      name: '长表达式',
      description: '表达式过长会增加解析时间',
      count: patternLength,
      impact: lengthPenalty,
      multiplier: 1 + lengthPenalty / 100
    });
  }

  const quantifierPattern = /\{(\d+),(\d*)\}/g;
  let maxRange = 0;
  let rangeMatch;
  while ((rangeMatch = quantifierPattern.exec(pattern)) !== null) {
    const min = parseInt(rangeMatch[1]);
    const max = rangeMatch[2] ? parseInt(rangeMatch[2]) : Infinity;
    if (max === Infinity) {
      maxRange = Math.max(maxRange, 100);
    } else {
      maxRange = Math.max(maxRange, max - min);
    }
  }
  
  if (maxRange > 10) {
    const rangePenalty = Math.min(Math.floor(maxRange / 10) * 3, 15);
    score -= rangePenalty;
    factors.push({
      id: 'wide-quantifier',
      name: '宽范围量词',
      description: '大范围量词增加匹配尝试次数',
      count: maxRange,
      impact: rangePenalty,
      multiplier: 1 + rangePenalty / 100
    });
  }

  const anchors = {
    start: pattern.startsWith('^'),
    end: pattern.endsWith('$')
  };
  
  if (anchors.start || anchors.end) {
    score += 5;
    factors.push({
      id: 'anchors',
      name: '使用锚点',
      description: '^ 和 $ 锚点可以加快匹配失败',
      count: (anchors.start ? 1 : 0) + (anchors.end ? 1 : 0),
      impact: -5,
      multiplier: 0.95
    });
  }

  const nonCaptureGroups = pattern.match(/\(\?:/g);
  if (nonCaptureGroups) {
    score += 2;
    factors.push({
      id: 'non-capture',
      name: '使用非捕获组',
      description: '(?:...) 比 (...) 性能更好',
      count: nonCaptureGroups.length,
      impact: -2,
      multiplier: 0.98
    });
  }

  const charClasses = pattern.match(/\[[^\]]+\]/g) || [];
  const negatedClasses = charClasses.filter(c => c.startsWith('[^')).length;
  if (negatedClasses > 0) {
    score += negatedClasses;
    factors.push({
      id: 'negated-class',
      name: '否定字符类',
      description: '[^...] 通常比 [...] 更高效',
      count: negatedClasses,
      impact: -negatedClasses,
      multiplier: 0.99
    });
  }

  score = Math.max(0, Math.min(100, score));

  let grade, complexity;
  if (score >= 90) {
    grade = 'A';
    complexity = '简单';
  } else if (score >= 75) {
    grade = 'B';
    complexity = '中等';
  } else if (score >= 60) {
    grade = 'C';
    complexity = '复杂';
  } else if (score >= 40) {
    grade = 'D';
    complexity = '非常复杂';
  } else {
    grade = 'F';
    complexity = '性能风险高';
  }

  let estimatedTime = baseTime;
  if (sampleText) {
    estimatedTime = baseTime * (sampleText.length / 1000);
  }

  return {
    score: Math.round(score),
    grade,
    complexity,
    factors,
    estimatedTime: Math.max(0.001, estimatedTime),
    patternLength,
    recommendations: generateRecommendations(factors, pattern)
  };
};

const generateRecommendations = (factors, pattern) => {
  const recommendations = [];
  
  const hasGreedyDot = factors.find(f => f.id === 'greedyQuantifiers');
  if (hasGreedyDot) {
    recommendations.push({
      type: 'warning',
      message: '考虑使用惰性量词 *? 或 +? 代替贪婪量词，减少回溯'
    });
  }

  const hasBackrefs = factors.find(f => f.id === 'backreferences');
  if (hasBackrefs) {
    recommendations.push({
      type: 'info',
      message: '反向引用会降低性能，如果不需要捕获请使用非捕获组 (?:...)'
    });
  }

  const hasNested = factors.find(f => f.id === 'nestedGroups');
  if (hasNested && hasNested.count > 2) {
    recommendations.push({
      type: 'warning',
      message: '嵌套分组过深可能导致灾难性回溯，考虑扁平化结构'
    });
  }

  const hasAlternations = factors.find(f => f.id === 'alternations');
  if (hasAlternations && hasAlternations.count > 3) {
    recommendations.push({
      type: 'info',
      message: '多个 | 分支按顺序匹配，将高频模式放在前面可提高性能'
    });
  }

  if (!pattern.startsWith('^') && pattern.length > 10) {
    recommendations.push({
      type: 'success',
      message: '可以考虑添加 ^ 锚点加速匹配失败检测'
    });
  }

  if (!pattern.endsWith('$') && pattern.length > 10) {
    recommendations.push({
      type: 'success',
      message: '可以考虑添加 $ 锚点确保完整匹配'
    });
  }

  if (recommendations.length === 0) {
    recommendations.push({
      type: 'success',
      message: '表达式结构良好，性能优秀！'
    });
  }

  return recommendations;
};

export const getPasswordStrength = (password) => {
  if (!password) return { score: 0, level: 'none', label: '请输入密码' };

  let score = 0;
  const checks = [];

  if (password.length >= 6) { score += 10; checks.push('长度≥6'); }
  if (password.length >= 8) { score += 15; checks.push('长度≥8'); }
  if (password.length >= 12) { score += 15; checks.push('长度≥12'); }
  if (password.length >= 16) { score += 10; checks.push('长度≥16'); }

  if (/[a-z]/.test(password)) { score += 10; checks.push('包含小写字母'); }
  if (/[A-Z]/.test(password)) { score += 15; checks.push('包含大写字母'); }
  if (/\d/.test(password)) { score += 15; checks.push('包含数字'); }
  if (/[@$!%*?&]/.test(password)) { score += 20; checks.push('包含特殊字符'); }

  if (!/(.)\1{2,}/.test(password)) { score += 5; checks.push('无连续重复字符'); }
  if (!/(012|123|234|345|456|567|678|789|abc|bcd|cde|def)/i.test(password)) { 
    score += 5; checks.push('无顺序字符'); 
  }

  let level, label, color;
  if (score >= 90) {
    level = 'very-strong';
    label = '非常强';
    color = '#0891b2';
  } else if (score >= 70) {
    level = 'strong';
    label = '强';
    color = '#22c55e';
  } else if (score >= 50) {
    level = 'medium';
    label = '中等';
    color = '#f59e0b';
  } else if (score >= 30) {
    level = 'weak';
    label = '弱';
    color = '#ef4444';
  } else {
    level = 'very-weak';
    label = '非常弱';
    color = '#991b1b';
  }

  return {
    score: Math.min(100, score),
    level,
    label,
    color,
    checks,
    suggestions: [
      { text: '增加长度到8位以上', met: password.length >= 8 },
      { text: '包含大小写字母', met: /[a-z]/.test(password) && /[A-Z]/.test(password) },
      { text: '包含数字', met: /\d/.test(password) },
      { text: '包含特殊字符 @$!%*?&', met: /[@$!%*?&]/.test(password) }
    ]
  };
};
