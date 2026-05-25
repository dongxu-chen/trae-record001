const LOWERCASE = 'abcdefghijklmnopqrstuvwxyz';
const UPPERCASE = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
const NUMBERS = '0123456789';
const SYMBOLS = '!@#$%^&*()_+-=[]{}|;:,.<>?';

const COMMON_PASSWORDS = [
  'password', '123456', '123456789', 'qwerty', 'abc123',
  'password1', '12345678', 'password123', '1234567',
  'admin', 'letmein', 'welcome', 'monkey', 'dragon',
  'master', 'iloveyou', 'trustno1', 'sunshine', 'princess',
  'football', 'secret', 'andrew', 'dolphin', 'michael'
];

export const PasswordStrength = {
  WEAK: 'weak',
  FAIR: 'fair',
  GOOD: 'good',
  STRONG: 'strong'
};

export class PasswordGenerator {
  static secureRandomInt(max) {
    if (max < 1) {
      throw new Error('Max must be at least 1');
    }
    if (max > 0xFFFFFFFF) {
      throw new Error('Max must not exceed 2^32 - 1');
    }

    const range = max;
    const limit = Math.floor(0x100000000 / range) * range;
    
    const array = new Uint32Array(1);
    
    while (true) {
      crypto.getRandomValues(array);
      if (array[0] < limit) {
        return array[0] % range;
      }
    }
  }

  static secureRandomBytes(length) {
    const array = new Uint32Array(length);
    crypto.getRandomValues(array);
    return array;
  }

  static generate(options = {}) {
    const {
      length = 16,
      includeUppercase = true,
      includeLowercase = true,
      includeNumbers = true,
      includeSymbols = true,
      excludeAmbiguous = false
    } = options;

    if (length < 8) {
      throw new Error('Password length must be at least 8 characters');
    }

    if (length > 128) {
      throw new Error('Password length must not exceed 128 characters');
    }

    let charset = '';
    const requiredChars = [];

    if (includeLowercase) {
      let lowercase = LOWERCASE;
      if (excludeAmbiguous) {
        lowercase = lowercase.replace(/[il]/g, '');
      }
      charset += lowercase;
      requiredChars.push(lowercase);
    }

    if (includeUppercase) {
      let uppercase = UPPERCASE;
      if (excludeAmbiguous) {
        uppercase = uppercase.replace(/[IO]/g, '');
      }
      charset += uppercase;
      requiredChars.push(uppercase);
    }

    if (includeNumbers) {
      let numbers = NUMBERS;
      if (excludeAmbiguous) {
        numbers = numbers.replace(/[01]/g, '');
      }
      charset += numbers;
      requiredChars.push(numbers);
    }

    if (includeSymbols) {
      charset += SYMBOLS;
      requiredChars.push(SYMBOLS);
    }

    if (charset.length === 0) {
      throw new Error('At least one character type must be selected');
    }

    const passwordArray = [];
    const randomValues = new Uint32Array(length);
    crypto.getRandomValues(randomValues);

    const charsetLen = charset.length;
    const limit = Math.floor(0x100000000 / charsetLen) * charsetLen;

    for (let i = 0; i < length; i++) {
      let randomValue = randomValues[i];
      while (randomValue >= limit) {
        randomValue = this.secureRandomInt(0xFFFFFFFF) % 0x100000000;
      }
      const randomIndex = randomValue % charsetLen;
      passwordArray.push(charset[randomIndex]);
    }

    for (let i = 0; i < requiredChars.length; i++) {
      const charSet = requiredChars[i];
      const randomCharIndex = this.secureRandomInt(charSet.length);
      const position = this.secureRandomInt(length);
      passwordArray[position] = charSet[randomCharIndex];
    }

    return passwordArray.join('');
  }

  static generatePassphrase(wordCount = 4) {
    const words = [
      'correct', 'horse', 'battery', 'staple', 'apple', 'banana',
      'cherry', 'dragon', 'eagle', 'forest', 'garden', 'harbor',
      'island', 'jungle', 'kingdom', 'lemon', 'mountain', 'night',
      'ocean', 'palace', 'queen', 'river', 'sunset', 'tower',
      'umbrella', 'valley', 'water', 'xenon', 'yellow', 'zebra',
      'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta',
      'rocket', 'planet', 'star', 'moon', 'sun', 'comet',
      'crystal', 'diamond', 'emerald', 'ruby', 'sapphire', 'opal',
      'thunder', 'lightning', 'rainbow', 'cloud', 'storm', 'breeze'
    ];

    const passphrase = [];
    
    for (let i = 0; i < wordCount; i++) {
      const randomIndex = this.secureRandomInt(words.length);
      passphrase.push(words[randomIndex]);
    }

    return passphrase.join('-');
  }

  static checkStrength(password) {
    let score = 0;
    const feedback = [];

    if (!password || password.length === 0) {
      return {
        strength: PasswordStrength.WEAK,
        score: 0,
        feedback: ['请输入密码']
      };
    }

    if (COMMON_PASSWORDS.includes(password.toLowerCase())) {
      return {
        strength: PasswordStrength.WEAK,
        score: 0,
        feedback: ['这是一个常见密码，请更换']
      };
    }

    if (password.length < 8) {
      feedback.push('密码长度至少8位');
    } else if (password.length >= 8 && password.length < 12) {
      score += 1;
    } else if (password.length >= 12 && password.length < 16) {
      score += 2;
    } else {
      score += 3;
    }

    if (/[a-z]/.test(password)) {
      score += 1;
    } else {
      feedback.push('建议包含小写字母');
    }

    if (/[A-Z]/.test(password)) {
      score += 1;
    } else {
      feedback.push('建议包含大写字母');
    }

    if (/[0-9]/.test(password)) {
      score += 1;
    } else {
      feedback.push('建议包含数字');
    }

    if (/[^a-zA-Z0-9]/.test(password)) {
      score += 1;
    } else {
      feedback.push('建议包含特殊字符');
    }

    const uniqueChars = new Set(password).size;
    if (uniqueChars < password.length * 0.5) {
      score -= 1;
      feedback.push('重复字符过多');
    }

    if (/(.)\1{2,}/.test(password)) {
      score -= 1;
      feedback.push('连续重复字符');
    }

    if (/012|123|234|345|456|567|678|789|abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz/i.test(password)) {
      score -= 1;
      feedback.push('包含连续序列');
    }

    score = Math.max(0, Math.min(score, 6));

    let strength;
    if (score <= 2) {
      strength = PasswordStrength.WEAK;
    } else if (score <= 3) {
      strength = PasswordStrength.FAIR;
    } else if (score <= 4) {
      strength = PasswordStrength.GOOD;
    } else {
      strength = PasswordStrength.STRONG;
    }

    if (strength === PasswordStrength.STRONG && feedback.length === 0) {
      feedback.push('密码强度非常好！');
    }

    return {
      strength,
      score,
      feedback,
      entropy: this.calculateEntropy(password)
    };
  }

  static calculateEntropy(password) {
    if (!password) return 0;

    let charsetSize = 0;
    if (/[a-z]/.test(password)) charsetSize += 26;
    if (/[A-Z]/.test(password)) charsetSize += 26;
    if (/[0-9]/.test(password)) charsetSize += 10;
    if (/[^a-zA-Z0-9]/.test(password)) charsetSize += 32;

    if (charsetSize === 0) return 0;

    const entropy = password.length * Math.log2(charsetSize);
    return Math.round(entropy * 100) / 100;
  }

  static getStrengthLabel(strength) {
    const labels = {
      [PasswordStrength.WEAK]: '弱',
      [PasswordStrength.FAIR]: '一般',
      [PasswordStrength.GOOD]: '良好',
      [PasswordStrength.STRONG]: '强'
    };
    return labels[strength] || '未知';
  }

  static getStrengthColor(strength) {
    const colors = {
      [PasswordStrength.WEAK]: '#ef4444',
      [PasswordStrength.FAIR]: '#f59e0b',
      [PasswordStrength.GOOD]: '#3b82f6',
      [PasswordStrength.STRONG]: '#22c55e'
    };
    return colors[strength] || '#6b7280';
  }

  static getStrengthClass(strength) {
    const classes = {
      [PasswordStrength.WEAK]: 'strength-weak',
      [PasswordStrength.FAIR]: 'strength-fair',
      [PasswordStrength.GOOD]: 'strength-good',
      [PasswordStrength.STRONG]: 'strength-strong'
    };
    return classes[strength] || '';
  }
}
