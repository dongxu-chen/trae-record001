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

const mask = (value, pattern, options = {}) => {
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
};

const replace = (value, replacement, pattern, options = {}) => {
  if (!value) return value;
  const str = String(value);
  const repl = replacement || '*';
  
  switch (pattern) {
    case 'phone':
      return mask(str, 'phone', { maskChar: repl });
    case 'idCard':
      return mask(str, 'idCard', { maskChar: repl });
    case 'email':
      return mask(str, 'email', { maskChar: repl });
    case 'adaptive':
      return mask(str, 'adaptive', { 
        maskChar: repl,
        keepStart: options.keepStart ?? 2,
        keepEnd: options.keepEnd ?? 2
      });
    case 'all':
      return repl.repeat(str.length);
    default:
      return mask(str, 'adaptive', { maskChar: repl });
  }
};

const simpleHash = (str) => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash).toString(16);
};

const hash = (value, algorithm = 'md5', salt = '') => {
  if (!value) return value;
  const str = String(value);
  const saltedValue = salt ? `${salt}:${str}` : str;
  
  const hashValue = simpleHash(saltedValue);
  
  switch (algorithm) {
    case 'md5':
      return hashValue.padStart(32, '0');
    case 'sha1':
      return hashValue.padStart(40, 'f');
    case 'sha256':
      return hashValue.padStart(64, 'a');
    default:
      return hashValue.padStart(32, '0');
  }
};

const truncate = (value, maxLength = 10, suffix = '...') => {
  if (!value) return value;
  const str = String(value);
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength) + suffix;
};

const shuffle = (value) => {
  if (!value) return value;
  const arr = String(value).split('');
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr.join('');
};

export const maskData = (data, rules) => {
  const result = { ...data };
  
  Object.entries(rules).forEach(([field, rule]) => {
    if (result[field] !== undefined && rule.enabled) {
      const value = result[field];
      const { 
        method, 
        pattern, 
        replacement, 
        hashAlgorithm, 
        hashSalt,
        maxLength,
        keepStart,
        keepEnd,
        maskChar
      } = rule;
      
      switch (method) {
        case 'mask':
          result[field] = mask(value, pattern, { keepStart, keepEnd, maskChar });
          break;
        case 'replace':
          result[field] = replace(value, replacement, pattern, { keepStart, keepEnd });
          break;
        case 'hash':
          result[field] = hash(value, hashAlgorithm, hashSalt);
          break;
        case 'truncate':
          result[field] = truncate(value, maxLength);
          break;
        case 'shuffle':
          result[field] = shuffle(value);
          break;
        default:
          break;
      }
    }
  });
  
  return result;
};

export const validatePattern = (value, pattern) => {
  const patterns = {
    phone: /^1[3-9]\d{9}$/,
    idCard: /^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/,
    email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  };
  
  if (patterns[pattern]) {
    return patterns[pattern].test(value);
  }
  
  return true;
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

export const maskDataWithPermission = (data, rules, permission = 'normal') => {
  const result = { ...data };
  const permRules = dynamicMaskingRules[permission] || dynamicMaskingRules.normal;
  
  Object.entries(rules).forEach(([field, rule]) => {
    if (result[field] !== undefined && rule.enabled) {
      const value = result[field];
      const dynamicRule = permRules[field] || {};
      
      const { method, pattern, replacement, hashAlgorithm, hashSalt, maxLength } = rule;
      
      if (permission === 'admin') {
        return;
      }
      
      const finalRule = { ...rule };
      
      if (method === 'mask' || method === 'replace') {
        finalRule.keepStart = dynamicRule.keepStart ?? rule.keepStart;
        finalRule.keepEnd = dynamicRule.keepEnd ?? rule.keepEnd;
      } else if (method === 'truncate') {
        finalRule.maxLength = dynamicRule.maxLength ?? rule.maxLength;
      }
      
      switch (method) {
        case 'mask':
          result[field] = mask(value, pattern, { 
            keepStart: finalRule.keepStart, 
            keepEnd: finalRule.keepEnd 
          });
          break;
        case 'replace':
          result[field] = replace(value, replacement, pattern, { 
            keepStart: finalRule.keepStart, 
            keepEnd: finalRule.keepEnd 
          });
          break;
        case 'hash':
          result[field] = hash(value, hashAlgorithm, hashSalt);
          break;
        case 'truncate':
          result[field] = truncate(value, finalRule.maxLength);
          break;
        case 'shuffle':
          result[field] = shuffle(value);
          break;
        default:
          break;
      }
    }
  });
  
  return result;
};

export { mask, replace, hash, truncate, shuffle, adaptiveMask, dynamicMaskingRules };
