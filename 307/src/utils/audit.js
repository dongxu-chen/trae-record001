import { dbService } from './database.js';
import { PasswordGenerator, PasswordStrength } from './passwordGenerator.js';

export class AuditService {
  static async runFullAudit() {
    const passwords = await dbService.getAllPasswords(true);
    const results = {
      total: passwords.length,
      weakPasswords: [],
      duplicatePasswords: [],
      oldPasswords: [],
      reusedPasswords: [],
      score: 0,
      issues: []
    };

    const passwordMap = new Map();
    const ninetyDaysAgo = Date.now() - 90 * 24 * 60 * 60 * 1000;

    passwords.forEach(pwd => {
      if (pwd.strength === PasswordStrength.WEAK) {
        results.weakPasswords.push({
          ...pwd,
          reason: '密码强度为弱，建议立即更换'
        });
      }

      if (pwd.updatedAt < ninetyDaysAgo) {
        results.oldPasswords.push({
          ...pwd,
          reason: '密码已超过90天未更新，建议更换'
        });
      }

      if (pwd.password) {
        if (passwordMap.has(pwd.password)) {
          passwordMap.get(pwd.password).push(pwd);
        } else {
          passwordMap.set(pwd.password, [pwd]);
        }
      }
    });

    passwordMap.forEach((entries, password) => {
      if (entries.length > 1) {
        results.duplicatePasswords.push({
          password,
          count: entries.length,
          entries
        });
      }
    });

    const domainMap = new Map();
    passwords.forEach(pwd => {
      if (pwd.url) {
        try {
          const domain = new URL(pwd.url).hostname;
          if (domainMap.has(domain)) {
            domainMap.get(domain).push(pwd);
          } else {
            domainMap.set(domain, [pwd]);
          }
        } catch (e) {
        }
      }
    });

    domainMap.forEach((entries, domain) => {
      const uniquePasswords = new Set(entries.map(e => e.password));
      if (entries.length > 1 && uniquePasswords.size === 1) {
        results.reusedPasswords.push({
          domain,
          count: entries.length,
          password: entries[0].password,
          entries
        });
      }
    });

    const totalIssues = results.weakPasswords.length + 
                        results.duplicatePasswords.reduce((sum, d) => sum + d.count, 0) +
                        results.oldPasswords.length;

    if (results.weakPasswords.length > 0) {
      results.issues.push({
        type: 'danger',
        message: `发现 ${results.weakPasswords.length} 个弱密码`
      });
    }

    if (results.duplicatePasswords.length > 0) {
      results.issues.push({
        type: 'warning',
        message: `发现 ${results.duplicatePasswords.length} 组重复密码`
      });
    }

    if (results.oldPasswords.length > 0) {
      results.issues.push({
        type: 'warning',
        message: `发现 ${results.oldPasswords.length} 个长期未更新的密码`
      });
    }

    if (results.reusedPasswords.length > 0) {
      results.issues.push({
        type: 'warning',
        message: `发现 ${results.reusedPasswords.length} 个跨站重用密码`
      });
    }

    if (passwords.length > 0) {
      results.score = Math.max(0, 100 - (totalIssues / passwords.length) * 50);
      results.score = Math.round(results.score);
    } else {
      results.score = 100;
    }

    return results;
  }

  static async getAuditSummary() {
    const audit = await this.runFullAudit();
    return {
      score: audit.score,
      total: audit.total,
      weakCount: audit.weakPasswords.length,
      duplicateCount: audit.duplicatePasswords.length,
      oldCount: audit.oldPasswords.length,
      issues: audit.issues
    };
  }

  static async generateRecommendations() {
    const audit = await this.runFullAudit();
    const recommendations = [];

    if (audit.weakPasswords.length > 0) {
      recommendations.push({
        priority: 'high',
        title: '更换弱密码',
        description: `您有 ${audit.weakPasswords.length} 个密码强度为弱。弱密码容易被破解，建议立即更换为强密码。`,
        action: '立即更换',
        items: audit.weakPasswords.slice(0, 5)
      });
    }

    if (audit.duplicatePasswords.length > 0) {
      recommendations.push({
        priority: 'high',
        title: '解决重复密码',
        description: `您有 ${audit.duplicatePasswords.length} 组密码重复使用。如果一个账户泄露，其他使用相同密码的账户也会处于风险中。`,
        action: '查看详情',
        items: audit.duplicatePasswords.slice(0, 5)
      });
    }

    if (audit.oldPasswords.length > 0) {
      recommendations.push({
        priority: 'medium',
        title: '更新老旧密码',
        description: `您有 ${audit.oldPasswords.length} 个密码超过90天未更新。定期更换密码是良好的安全习惯。`,
        action: '查看列表',
        items: audit.oldPasswords.slice(0, 5)
      });
    }

    if (audit.reusedPasswords.length > 0) {
      recommendations.push({
        priority: 'medium',
        title: '避免跨站密码重用',
        description: `您在 ${audit.reusedPasswords.length} 个不同网站使用了相同密码。建议每个网站使用唯一密码。`,
        action: '查看详情',
        items: audit.reusedPasswords.slice(0, 5)
      });
    }

    if (recommendations.length === 0) {
      recommendations.push({
        priority: 'low',
        title: '密码安全状况良好！',
        description: '您的密码安全习惯很好，请继续保持。',
        action: null,
        items: []
      });
    }

    return recommendations;
  }

  static async getBreachCheck(password) {
    const hash = await crypto.subtle.digest(
      'SHA-1',
      new TextEncoder().encode(password)
    );
    
    const hashHex = Array.from(new Uint8Array(hash))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('')
      .toUpperCase();

    return {
      hashPrefix: hashHex.substring(0, 5),
      hashSuffix: hashHex.substring(5),
      checked: false,
      breached: false,
      count: 0
    };
  }

  static async checkPasswordAgainstCommon(password) {
    const commonPasswords = [
      'password', '123456', '123456789', 'qwerty', 'abc123',
      'password1', '12345678', 'password123', '1234567',
      'admin', 'letmein', 'welcome', 'monkey', 'dragon',
      'master', 'iloveyou', 'trustno1', 'sunshine', 'princess',
      'football', 'secret', 'andrew', 'dolphin', 'michael',
      'login', 'princess', 'qwerty123', '696969', 'abc123',
      '123123', 'football', 'welcome', 'monkey', '654321',
      'superman', 'qazwsx', 'michael', 'ninja', 'mustang'
    ];

    const lowerPassword = password.toLowerCase();
    const isCommon = commonPasswords.some(common => 
      lowerPassword === common || 
      lowerPassword.includes(common) ||
      common.includes(lowerPassword)
    );

    return {
      isCommon,
      message: isCommon ? '这是一个常见密码，非常容易被破解' : '不是常见密码'
    };
  }

  static async analyzePasswordPatterns(password) {
    const patterns = [];

    if (/^[a-z]+$/.test(password)) {
      patterns.push('仅使用小写字母');
    }

    if (/^[A-Z]+$/.test(password)) {
      patterns.push('仅使用大写字母');
    }

    if (/^[0-9]+$/.test(password)) {
      patterns.push('仅使用数字');
    }

    if (/^(.)\1+$/.test(password)) {
      patterns.push('所有字符相同');
    }

    if (/(.)\1{2,}/.test(password)) {
      patterns.push('包含3个以上连续重复字符');
    }

    if (/012|123|234|345|456|567|678|789|987|876|765|654|543|432|321|210/.test(password)) {
      patterns.push('包含连续数字序列');
    }

    if (/abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz/i.test(password)) {
      patterns.push('包含连续字母序列');
    }

    if (/qwerty|asdfgh|zxcvbn|123456|password|letmein|welcome/i.test(password)) {
      patterns.push('包含键盘常见序列');
    }

    const strength = PasswordGenerator.checkStrength(password);

    return {
      patterns,
      strength: strength.strength,
      score: strength.score,
      entropy: strength.entropy,
      feedback: strength.feedback
    };
  }
}
