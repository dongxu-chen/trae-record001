const express = require('express');
const cors = require('cors');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

const auditLogs = [];
const maxAuditLogs = 1000;

const addAuditLog = (log) => {
  const newLog = {
    id: Date.now() + Math.random().toString(36).substr(2, 9),
    timestamp: new Date().toISOString(),
    ...log
  };
  auditLogs.unshift(newLog);
  if (auditLogs.length > maxAuditLogs) {
    auditLogs.splice(maxAuditLogs);
  }
  return newLog;
};

const permissionLevels = {
  admin: {
    level: 0,
    label: '管理员',
    description: '完全可见，不脱敏'
  },
  senior: {
    level: 1,
    label: '高级用户',
    description: '轻度脱敏，保留较多信息'
  },
  normal: {
    level: 2,
    label: '普通用户',
    description: '中度脱敏'
  },
  guest: {
    level: 3,
    label: '访客',
    description: '高度脱敏，仅保留格式'
  }
};

const strategyTemplates = {
  financial: {
    id: 'financial',
    name: '金融安全级',
    description: '适用于金融行业，高安全要求',
    icon: '🏦',
    color: '#dc2626',
    rules: {
      phone: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 3, keepEnd: 2, label: '手机号码' },
      idCard: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 3, keepEnd: 2, label: '身份证号' },
      email: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 1, keepEnd: 0, label: '邮箱地址' },
      name: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 1, keepEnd: 0, label: '姓名' },
      address: { enabled: true, method: 'truncate', maxLength: 6, label: '地址' }
    }
  },
  enterprise: {
    id: 'enterprise',
    name: '企业标准级',
    description: '适用于企业内部使用',
    icon: '🏢',
    color: '#2563eb',
    rules: {
      phone: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 3, keepEnd: 4, label: '手机号码' },
      idCard: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 6, keepEnd: 4, label: '身份证号' },
      email: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 2, keepEnd: 0, label: '邮箱地址' },
      name: { enabled: false, method: 'mask', pattern: 'adaptive', keepStart: 1, keepEnd: 1, label: '姓名' },
      address: { enabled: true, method: 'truncate', maxLength: 10, label: '地址' }
    }
  },
  basic: {
    id: 'basic',
    name: '基础保护级',
    description: '适用于一般数据保护场景',
    icon: '🛡️',
    color: '#059669',
    rules: {
      phone: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 3, keepEnd: 4, label: '手机号码' },
      idCard: { enabled: true, method: 'hash', hashAlgorithm: 'md5', hashSalt: 'basic-salt', label: '身份证号' },
      email: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 3, keepEnd: 2, label: '邮箱地址' },
      name: { enabled: false, method: 'mask', pattern: 'adaptive', keepStart: 1, keepEnd: 1, label: '姓名' },
      address: { enabled: false, method: 'truncate', maxLength: 15, label: '地址' }
    }
  },
  privacy: {
    id: 'privacy',
    name: '隐私合规级',
    description: '符合GDPR等隐私法规要求',
    icon: '🔒',
    color: '#7c3aed',
    rules: {
      phone: { enabled: true, method: 'hash', hashAlgorithm: 'sha256', hashSalt: 'privacy-2024', label: '手机号码' },
      idCard: { enabled: true, method: 'hash', hashAlgorithm: 'sha256', hashSalt: 'privacy-2024', label: '身份证号' },
      email: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 2, keepEnd: 0, label: '邮箱地址' },
      name: { enabled: true, method: 'hash', hashAlgorithm: 'sha256', hashSalt: 'privacy-2024', label: '姓名' },
      address: { enabled: true, method: 'truncate', maxLength: 4, label: '地址' }
    }
  },
  test: {
    id: 'test',
    name: '测试开发级',
    description: '适用于开发测试环境',
    icon: '🧪',
    color: '#f59e0b',
    rules: {
      phone: { enabled: true, method: 'shuffle', label: '手机号码' },
      idCard: { enabled: true, method: 'shuffle', label: '身份证号' },
      email: { enabled: true, method: 'replace', replacement: '*', pattern: 'adaptive', label: '邮箱地址' },
      name: { enabled: false, method: 'mask', pattern: 'adaptive', keepStart: 1, keepEnd: 1, label: '姓名' },
      address: { enabled: false, method: 'truncate', maxLength: 20, label: '地址' }
    }
  }
};

const dynamicMaskingRules = {
  admin: {
    phone: { keepStart: 11, keepEnd: 0 },
    idCard: { keepStart: 18, keepEnd: 0 },
    email: { keepStart: 100, keepEnd: 0 },
    name: { keepStart: 10, keepEnd: 0 },
    address: { maxLength: 100 }
  },
  senior: {
    phone: { keepStart: 5, keepEnd: 4 },
    idCard: { keepStart: 8, keepEnd: 4 },
    email: { keepStart: 4, keepEnd: 2 },
    name: { keepStart: 2, keepEnd: 1 },
    address: { maxLength: 15 }
  },
  normal: {
    phone: { keepStart: 3, keepEnd: 4 },
    idCard: { keepStart: 6, keepEnd: 4 },
    email: { keepStart: 2, keepEnd: 0 },
    name: { keepStart: 1, keepEnd: 0 },
    address: { maxLength: 10 }
  },
  guest: {
    phone: { keepStart: 2, keepEnd: 1 },
    idCard: { keepStart: 2, keepEnd: 1 },
    email: { keepStart: 1, keepEnd: 0 },
    name: { keepStart: 0, keepEnd: 0 },
    address: { maxLength: 4 }
  }
};

const adaptiveMask = (value, options = {}) => {
  if (!value) return value;
  const str = String(value);
  const len = str.length;
  
  const { 
    keepStart = 2, 
    keepEnd = 2, 
    maskChar = '*',
    minKeepChars = 4
  } = options;
  
  if (len <= minKeepChars) {
    return maskChar.repeat(len);
  }
  
  const actualKeepStart = Math.min(keepStart, Math.floor((len - 1) / 2));
  const actualKeepEnd = Math.min(keepEnd, Math.floor((len - 1) / 2));
  
  const maskLength = len - actualKeepStart - actualKeepEnd;
  
  return str.slice(0, actualKeepStart) + 
         maskChar.repeat(maskLength) + 
         str.slice(len - actualKeepEnd);
};

const maskingUtils = {
  mask: (value, pattern, options = {}) => {
    if (!value) return value;
    const str = String(value);
    
    switch (pattern) {
      case 'phone':
        return adaptiveMask(str, { keepStart: 3, keepEnd: 4, maskChar: options.maskChar || '*' });
      case 'idCard':
        return adaptiveMask(str, { keepStart: 6, keepEnd: 4, maskChar: options.maskChar || '*' });
      case 'email':
        const [local, domain] = str.split('@');
        if (!domain) return adaptiveMask(str, { maskChar: options.maskChar || '*' });
        const maskedLocal = adaptiveMask(local, { keepStart: 2, keepEnd: 0, maskChar: options.maskChar || '*' });
        return `${maskedLocal}@${domain}`;
      case 'adaptive':
        return adaptiveMask(str, { 
          keepStart: options.keepStart ?? 2, 
          keepEnd: options.keepEnd ?? 2,
          maskChar: options.maskChar || '*'
        });
      case 'all':
        return (options.maskChar || '*').repeat(str.length);
      default:
        return adaptiveMask(str, { maskChar: options.maskChar || '*' });
    }
  },

  replace: (value, replacement, pattern, options = {}) => {
    if (!value) return value;
    const str = String(value);
    const repl = replacement || '*';
    
    switch (pattern) {
      case 'phone':
        return maskingUtils.mask(str, 'phone', { maskChar: repl });
      case 'idCard':
        return maskingUtils.mask(str, 'idCard', { maskChar: repl });
      case 'email':
        return maskingUtils.mask(str, 'email', { maskChar: repl });
      case 'adaptive':
        return maskingUtils.mask(str, 'adaptive', { 
          maskChar: repl,
          keepStart: options.keepStart ?? 2,
          keepEnd: options.keepEnd ?? 2
        });
      case 'all':
        return repl.repeat(str.length);
      default:
        return maskingUtils.mask(str, 'adaptive', { maskChar: repl });
    }
  },

  hash: (value, algorithm = 'md5', salt = '') => {
    if (!value) return value;
    const str = String(value);
    const saltedValue = salt ? `${salt}:${str}` : str;
    return crypto.createHash(algorithm).update(saltedValue).digest('hex');
  },

  truncate: (value, maxLength = 10) => {
    if (!value) return value;
    const str = String(value);
    if (str.length <= maxLength) return str;
    return str.slice(0, maxLength) + '...';
  },

  shuffle: (value) => {
    if (!value) return value;
    const arr = String(value).split('');
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr.join('');
  }
};

const applyDynamicMasking = (data, rules, permission) => {
  const result = { ...data };
  const permRules = dynamicMaskingRules[permission] || dynamicMaskingRules.normal;
  
  Object.entries(rules).forEach(([field, rule]) => {
    if (result[field] !== undefined && rule.enabled) {
      const value = result[field];
      const dynamicRule = permRules[field] || {};
      
      const { method, pattern, replacement, hashAlgorithm, hashSalt, maxLength } = rule;
      
      const finalRule = { ...rule };
      
      if (permission === 'admin') {
        return;
      }
      
      if (method === 'mask' || method === 'replace') {
        finalRule.keepStart = dynamicRule.keepStart ?? rule.keepStart;
        finalRule.keepEnd = dynamicRule.keepEnd ?? rule.keepEnd;
      } else if (method === 'truncate') {
        finalRule.maxLength = dynamicRule.maxLength ?? rule.maxLength;
      }
      
      switch (method) {
        case 'mask':
          result[field] = maskingUtils.mask(value, pattern, { 
            keepStart: finalRule.keepStart, 
            keepEnd: finalRule.keepEnd 
          });
          break;
        case 'replace':
          result[field] = maskingUtils.replace(value, replacement, pattern, { 
            keepStart: finalRule.keepStart, 
            keepEnd: finalRule.keepEnd 
          });
          break;
        case 'hash':
          result[field] = maskingUtils.hash(value, hashAlgorithm, hashSalt);
          break;
        case 'truncate':
          result[field] = maskingUtils.truncate(value, finalRule.maxLength);
          break;
        case 'shuffle':
          result[field] = maskingUtils.shuffle(value);
          break;
        default:
          break;
      }
    }
  });
  
  return result;
};

app.post('/api/mask', (req, res) => {
  try {
    const { data, rules, permission = 'normal', userId = 'anonymous', userName = '匿名用户' } = req.body;
    
    if (!data || !rules) {
      return res.status(400).json({ error: '缺少必要参数' });
    }

    const result = applyDynamicMasking(data, rules, permission);
    
    const sensitiveFields = Object.entries(rules)
      .filter(([_, rule]) => rule.enabled)
      .map(([field]) => field);
    
    addAuditLog({
      action: 'mask',
      userId,
      userName,
      permission,
      sensitiveFields,
      dataKeys: Object.keys(data),
      ip: req.ip || req.connection.remoteAddress
    });

    res.json({ result, original: data, permission });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/mask/batch', (req, res) => {
  try {
    const { dataList, rules, permission = 'normal', userId = 'anonymous', userName = '匿名用户' } = req.body;
    
    if (!dataList || !rules) {
      return res.status(400).json({ error: '缺少必要参数' });
    }

    const results = dataList.map(data => applyDynamicMasking(data, rules, permission));
    
    const sensitiveFields = Object.entries(rules)
      .filter(([_, rule]) => rule.enabled)
      .map(([field]) => field);
    
    addAuditLog({
      action: 'mask_batch',
      userId,
      userName,
      permission,
      sensitiveFields,
      recordCount: dataList.length,
      ip: req.ip || req.connection.remoteAddress
    });

    res.json({ results, original: dataList, permission });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/templates', (req, res) => {
  res.json(Object.values(strategyTemplates));
});

app.get('/api/templates/:id', (req, res) => {
  const template = strategyTemplates[req.params.id];
  if (!template) {
    return res.status(404).json({ error: '模板不存在' });
  }
  res.json(template);
});

app.get('/api/permissions', (req, res) => {
  res.json(Object.entries(permissionLevels).map(([key, value]) => ({
    value: key,
    ...value
  })));
});

app.get('/api/audit/logs', (req, res) => {
  const { limit = 50, offset = 0, action, userId } = req.query;
  
  let filteredLogs = [...auditLogs];
  
  if (action) {
    filteredLogs = filteredLogs.filter(log => log.action === action);
  }
  
  if (userId) {
    filteredLogs = filteredLogs.filter(log => log.userId === userId);
  }
  
  const paginatedLogs = filteredLogs.slice(parseInt(offset), parseInt(offset) + parseInt(limit));
  
  res.json({
    logs: paginatedLogs,
    total: filteredLogs.length,
    limit: parseInt(limit),
    offset: parseInt(offset)
  });
});

app.post('/api/audit/logs', (req, res) => {
  const log = addAuditLog(req.body);
  res.json(log);
});

app.get('/api/rules/default', (req, res) => {
  res.json({
    phone: {
      enabled: true,
      method: 'mask',
      pattern: 'adaptive',
      label: '手机号码',
      placeholder: '13800138000',
      keepStart: 3,
      keepEnd: 4,
      hashSalt: '',
      hashAlgorithm: 'md5',
      replacement: '*',
      maxLength: 10
    },
    idCard: {
      enabled: true,
      method: 'mask',
      pattern: 'adaptive',
      label: '身份证号',
      placeholder: '110101199001011234',
      keepStart: 6,
      keepEnd: 4,
      hashSalt: '',
      hashAlgorithm: 'md5',
      replacement: '*',
      maxLength: 10
    },
    email: {
      enabled: true,
      method: 'mask',
      pattern: 'adaptive',
      label: '邮箱地址',
      placeholder: 'example@email.com',
      keepStart: 2,
      keepEnd: 0,
      hashSalt: '',
      hashAlgorithm: 'md5',
      replacement: '*',
      maxLength: 10
    },
    name: {
      enabled: false,
      method: 'mask',
      pattern: 'adaptive',
      label: '姓名',
      placeholder: '张三',
      keepStart: 1,
      keepEnd: 0,
      hashSalt: '',
      hashAlgorithm: 'md5',
      replacement: '*',
      maxLength: 10
    },
    address: {
      enabled: false,
      method: 'truncate',
      label: '地址',
      placeholder: '北京市朝阳区某某街道123号',
      keepStart: 2,
      keepEnd: 2,
      hashSalt: '',
      hashAlgorithm: 'md5',
      replacement: '*',
      maxLength: 10
    }
  });
});

app.get('/api/methods', (req, res) => {
  res.json([
    { value: 'mask', label: '掩码脱敏', description: '自适应掩码，按输入长度动态调整' },
    { value: 'replace', label: '替换脱敏', description: '自定义替换字符' },
    { value: 'hash', label: '哈希脱敏', description: '不可逆哈希加密，支持盐值' },
    { value: 'truncate', label: '截断脱敏', description: '截断超出长度的内容' },
    { value: 'shuffle', label: '打乱脱敏', description: '随机打乱字符顺序' }
  ]);
});

app.get('/api/patterns', (req, res) => {
  res.json([
    { value: 'adaptive', label: '自适应', description: '按输入长度动态调整掩码' },
    { value: 'phone', label: '手机号模式', regex: /^1[3-9]\d{9}$/ },
    { value: 'idCard', label: '身份证模式', regex: /^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/ },
    { value: 'email', label: '邮箱模式', regex: /^[^\s@]+@[^\s@]+\.[^\s@]+$/ },
    { value: 'all', label: '全部掩码', description: '全部内容替换为*' }
  ]);
});

app.listen(PORT, () => {
  console.log(`服务器运行在 http://localhost:${PORT}`);
  console.log('✅ 自适应掩码 · 一致性哈希 · 表格化批量配置');
  console.log('✅ 策略模板 · 动态脱敏 · 审计日志');
});
