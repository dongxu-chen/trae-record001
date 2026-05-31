export const regexComponents = [
  {
    category: '基础字符',
    items: [
      {
        id: 'digit',
        name: '数字',
        description: '匹配任意数字 0-9',
        pattern: '\\d',
        icon: '🔢',
        color: '#3b82f6'
      },
      {
        id: 'letter',
        name: '字母',
        description: '匹配任意字母 a-z, A-Z',
        pattern: '[a-zA-Z]',
        icon: '🔤',
        color: '#10b981'
      },
      {
        id: 'word',
        name: '单词字符',
        description: '匹配字母、数字、下划线',
        pattern: '\\w',
        icon: '📝',
        color: '#8b5cf6'
      },
      {
        id: 'whitespace',
        name: '空白字符',
        description: '匹配空格、制表符、换行',
        pattern: '\\s',
        icon: '⬜',
        color: '#6b7280'
      },
      {
        id: 'any',
        name: '任意字符',
        description: '匹配除换行外的任意字符',
        pattern: '.',
        icon: '🔮',
        color: '#f59e0b'
      }
    ]
  },
  {
    category: '常用模式',
    items: [
      {
        id: 'email',
        name: '邮箱地址',
        description: '匹配标准邮箱格式',
        pattern: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}',
        icon: '📧',
        color: '#ef4444'
      },
      {
        id: 'phone',
        name: '手机号码',
        description: '匹配中国大陆手机号',
        pattern: '1[3-9]\\d{9}',
        icon: '📱',
        color: '#22c55e'
      },
      {
        id: 'url',
        name: 'URL链接',
        description: '匹配HTTP/HTTPS网址',
        pattern: 'https?://[\\w\\-._~:/?#[\\]@!$&\'()*+,;=%]+',
        icon: '🔗',
        color: '#06b6d4'
      },
      {
        id: 'ip',
        name: 'IP地址',
        description: '匹配IPv4地址',
        pattern: '(?:(?:25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(?:25[0-5]|2[0-4]\\d|[01]?\\d\\d?)',
        icon: '🌐',
        color: '#84cc16'
      },
      {
        id: 'chinese',
        name: '中文字符',
        description: '匹配中文汉字',
        pattern: '[\\u4e00-\\u9fa5]',
        icon: '🀄',
        color: '#dc2626'
      }
    ]
  },
  {
    category: '量词',
    items: [
      {
        id: 'one-or-more',
        name: '一个或多个',
        description: '匹配前一项至少一次',
        pattern: '+',
        icon: '➕',
        color: '#f97316',
        isQuantifier: true
      },
      {
        id: 'zero-or-more',
        name: '零个或多个',
        description: '匹配前一项任意次',
        pattern: '*',
        icon: '✳️',
        color: '#f97316',
        isQuantifier: true
      },
      {
        id: 'zero-or-one',
        name: '零个或一个',
        description: '匹配前一项最多一次',
        pattern: '?',
        icon: '❓',
        color: '#f97316',
        isQuantifier: true
      },
      {
        id: 'exact',
        name: '精确次数',
        description: '匹配前一项恰好n次',
        pattern: '{n}',
        icon: '🔢',
        color: '#f97316',
        isQuantifier: true,
        hasInput: true,
        inputLabel: '输入次数n',
        inputPlaceholder: '例如: 3'
      },
      {
        id: 'range',
        name: '范围次数',
        description: '匹配前一项n到m次',
        pattern: '{n,m}',
        icon: '📏',
        color: '#f97316',
        isQuantifier: true,
        hasInput: true,
        inputLabel: '输入范围 n,m',
        inputPlaceholder: '例如: 2,5'
      }
    ]
  },
  {
    category: '边界与锚点',
    items: [
      {
        id: 'start',
        name: '行首',
        description: '匹配字符串开始位置',
        pattern: '^',
        icon: '🏁',
        color: '#8b5cf6',
        isAnchor: true
      },
      {
        id: 'end',
        name: '行尾',
        description: '匹配字符串结束位置',
        pattern: '$',
        icon: '🏁',
        color: '#8b5cf6',
        isAnchor: true
      },
      {
        id: 'word-boundary',
        name: '单词边界',
        description: '匹配单词边界位置',
        pattern: '\\b',
        icon: '🚧',
        color: '#8b5cf6',
        isAnchor: true
      }
    ]
  },
  {
    category: '特殊字符',
    items: [
      {
        id: 'dot',
        name: '点号',
        description: '匹配字面量 .',
        pattern: '\\.',
        icon: '⚫',
        color: '#64748b'
      },
      {
        id: 'hyphen',
        name: '连字符',
        description: '匹配字面量 -',
        pattern: '-',
        icon: '➖',
        color: '#64748b'
      },
      {
        id: 'underscore',
        name: '下划线',
        description: '匹配字面量 _',
        pattern: '_',
        icon: '＿',
        color: '#64748b'
      },
      {
        id: 'at',
        name: '@符号',
        description: '匹配字面量 @',
        pattern: '@',
        icon: '@',
        color: '#64748b'
      }
    ]
  },
  {
    category: '逻辑操作',
    items: [
      {
        id: 'or',
        name: '或 (OR)',
        description: '匹配左侧或右侧表达式',
        pattern: '|',
        icon: '🔀',
        color: '#ec4899',
        isOperator: true
      },
      {
        id: 'group',
        name: '捕获组',
        description: '将表达式分组并捕获',
        pattern: '()',
        icon: '📦',
        color: '#ec4899',
        isGroup: true,
        isOperator: true
      },
      {
        id: 'non-capture-group',
        name: '非捕获组',
        description: '分组但不捕获',
        pattern: '(?:)',
        icon: '📦',
        color: '#ec4899',
        isGroup: true,
        isOperator: true
      },
      {
        id: 'charset',
        name: '字符集',
        description: '匹配方括号内任意字符',
        pattern: '[]',
        icon: '🔲',
        color: '#ec4899',
        isGroup: true,
        isOperator: true
      }
    ]
  }
];

export const getAllComponents = () => {
  const baseComponents = regexComponents.flatMap(cat => cat.items);
  const templateComponents = templateCategories.flatMap(cat => cat.items);
  return [...baseComponents, ...templateComponents];
};

export const getComponentById = (id) => {
  return getAllComponents().find(item => item.id === id);
};

export const passwordTemplates = [
  {
    id: 'password-weak',
    name: '弱密码',
    description: '至少6位，包含字母和数字',
    pattern: '^[a-zA-Z0-9]{6,}$',
    icon: '🔓',
    color: '#ef4444',
    strength: 'weak',
    isTemplate: true
  },
  {
    id: 'password-medium',
    name: '中等强度密码',
    description: '至少8位，包含大小写字母和数字',
    pattern: '^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)[a-zA-Z\\d]{8,}$',
    icon: '🔐',
    color: '#f59e0b',
    strength: 'medium',
    isTemplate: true
  },
  {
    id: 'password-strong',
    name: '强密码',
    description: '至少8位，包含大小写字母、数字和特殊字符',
    pattern: '^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]{8,}$',
    icon: '🔒',
    color: '#22c55e',
    strength: 'strong',
    isTemplate: true
  },
  {
    id: 'password-very-strong',
    name: '极强密码',
    description: '至少12位，包含大小写字母、数字和特殊字符',
    pattern: '^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]{12,}$',
    icon: '🛡️',
    color: '#0891b2',
    strength: 'very-strong',
    isTemplate: true
  },
  {
    id: 'password-no-sequence',
    name: '无连续字符密码',
    description: '不包含连续3个相同或顺序字符',
    pattern: '^(?!.*(.)\\1{2})(?!.*(012|123|234|345|456|567|678|789|abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)).{8,}$',
    icon: '🚫',
    color: '#7c3aed',
    strength: 'strong',
    isTemplate: true
  }
];

export const urlTemplates = [
  {
    id: 'url-basic',
    name: '基础URL',
    description: '匹配HTTP/HTTPS网址',
    pattern: 'https?://[\\w\\-._~:/?#[\\]@!$&\'()*+,;=%]+',
    icon: '🔗',
    color: '#06b6d4',
    isTemplate: true
  },
  {
    id: 'url-strict',
    name: '严格URL',
    description: '严格匹配带域名的URL',
    pattern: 'https?://(?:www\\.)?[a-zA-Z0-9][-a-zA-Z0-9]*\\.[a-zA-Z]{2,}(?:/[^\\s]*)?',
    icon: '🌐',
    color: '#0891b2',
    isTemplate: true
  },
  {
    id: 'url-with-params',
    name: '带参数URL',
    description: '匹配带查询参数的URL',
    pattern: 'https?://[\\w\\-._~:/?#[\\]@!$&\'()*+,;=%]+\\?[\\w\\-._~:/?#[\\]@!$&\'()*+,;=%]*',
    icon: '📊',
    color: '#0e7490',
    isTemplate: true
  },
  {
    id: 'url-image',
    name: '图片URL',
    description: '匹配图片文件URL',
    pattern: 'https?://[\\w\\-._~:/?#[\\]@!$&\'()*+,;=%]+\\.(?:jpg|jpeg|png|gif|bmp|webp|svg)',
    icon: '🖼️',
    color: '#14b8a6',
    isTemplate: true
  },
  {
    id: 'url-ftp',
    name: 'FTP URL',
    description: '匹配FTP地址',
    pattern: 'ftp://[\\w\\-._~:/?#[\\]@!$&\'()*+,;=%]+',
    icon: '📁',
    color: '#6366f1',
    isTemplate: true
  }
];

export const emailTemplates = [
  {
    id: 'email-basic',
    name: '基础邮箱',
    description: '匹配标准邮箱格式',
    pattern: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}',
    icon: '📧',
    color: '#ef4444',
    isTemplate: true
  },
  {
    id: 'email-strict',
    name: '严格邮箱',
    description: '严格匹配RFC标准邮箱',
    pattern: '[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\\.[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+)*@(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?',
    icon: '✉️',
    color: '#dc2626',
    isTemplate: true
  },
  {
    id: 'email-domain',
    name: '指定域名邮箱',
    description: '仅匹配指定域名邮箱（示例：gmail.com）',
    pattern: '[a-zA-Z0-9._%+-]+@gmail\\.com',
    icon: '📩',
    color: '#b91c1c',
    isTemplate: true
  },
  {
    id: 'email-corporate',
    name: '企业邮箱',
    description: '匹配企业域名邮箱',
    pattern: '[a-zA-Z0-9._%+-]+@(?!gmail\\.com|yahoo\\.com|hotmail\\.com|outlook\\.com)[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}',
    icon: '🏢',
    color: '#991b1b',
    isTemplate: true
  }
];

export const otherTemplates = [
  {
    id: 'id-card',
    name: '身份证号',
    description: '匹配18位中国身份证号',
    pattern: '[1-9]\\d{5}(?:18|19|20)\\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\\d|3[01])\\d{3}[0-9Xx]',
    icon: '🪪',
    color: '#8b5cf6',
    isTemplate: true
  },
  {
    id: 'bank-card',
    name: '银行卡号',
    description: '匹配16-19位银行卡号',
    pattern: '[1-9]\\d{15,18}',
    icon: '💳',
    color: '#7c3aed',
    isTemplate: true
  },
  {
    id: 'postal-code',
    name: '邮政编码',
    description: '匹配6位中国邮政编码',
    pattern: '[1-9]\\d{5}',
    icon: '📮',
    color: '#6d28d9',
    isTemplate: true
  },
  {
    id: 'license-plate',
    name: '车牌号',
    description: '匹配中国车牌号',
    pattern: '[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-HJ-NP-Z0-9]{5}',
    icon: '🚗',
    color: '#5b21b6',
    isTemplate: true
  },
  {
    id: 'ipv6',
    name: 'IPv6地址',
    description: '匹配IPv6地址',
    pattern: '(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}',
    icon: '🌍',
    color: '#4c1d95',
    isTemplate: true
  },
  {
    id: 'mac-address',
    name: 'MAC地址',
    description: '匹配MAC地址',
    pattern: '(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}',
    icon: '🔌',
    color: '#84cc16',
    isTemplate: true
  },
  {
    id: 'hex-color',
    name: '十六进制颜色',
    description: '匹配CSS十六进制颜色值',
    pattern: '#(?:[0-9a-fA-F]{3}){1,2}',
    icon: '🎨',
    color: '#65a30d',
    isTemplate: true
  },
  {
    id: 'date-iso',
    name: 'ISO日期',
    description: '匹配YYYY-MM-DD格式日期',
    pattern: '\\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\\d|3[01])',
    icon: '📅',
    color: '#4d7c0f',
    isTemplate: true
  },
  {
    id: 'time-24h',
    name: '24小时制时间',
    description: '匹配HH:MM:SS格式时间',
    pattern: '(?:[01]\\d|2[0-3]):[0-5]\\d:[0-5]\\d',
    icon: '⏰',
    color: '#3f6212',
    isTemplate: true
  },
  {
    id: 'uuid',
    name: 'UUID',
    description: '匹配标准UUID格式',
    pattern: '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',
    icon: '🆔',
    color: '#365314',
    isTemplate: true
  },
  {
    id: 'html-tag',
    name: 'HTML标签',
    description: '匹配HTML标签',
    pattern: '<([a-zA-Z][a-zA-Z0-9]*)\\b[^>]*>(.*?)</\\1>',
    icon: '🏷️',
    color: '#166534',
    isTemplate: true
  },
  {
    id: 'chinese-name',
    name: '中文姓名',
    description: '匹配2-4个汉字的中文姓名',
    pattern: '[\\u4e00-\\u9fa5]{2,4}',
    icon: '👤',
    color: '#14532d',
    isTemplate: true
  }
];

export const templateCategories = [
  { category: '🔒 密码强度', items: passwordTemplates },
  { category: '🔗 URL地址', items: urlTemplates },
  { category: '📧 邮箱格式', items: emailTemplates },
  { category: '📋 其他常用', items: otherTemplates }
];
