import { dbService } from './database.js';
import { PasswordGenerator } from './passwordGenerator.js';
import { BreachService } from './breach.js';

const HEALTH_HISTORY_KEY = 'healthHistory';
const MAX_HISTORY_ENTRIES = 52;

export class HealthReportService {
  static async generateReport() {
    const passwords = await dbService.getAllPasswords(true);
    const breachStats = await BreachService.getBreachStats();

    const stats = this.calculateStats(passwords);
    const trends = await this.calculateTrends();
    const recommendations = this.generateRecommendations(stats, passwords);
    const score = this.calculateHealthScore(stats, passwords.length);

    return {
      generatedAt: Date.now(),
      totalPasswords: passwords.length,
      score,
      stats,
      trends,
      recommendations,
      breachStats
    };
  }

  static calculateStats(passwords) {
    const now = Date.now();
    const THREE_MONTHS = 90 * 24 * 60 * 60 * 1000;
    const SIX_MONTHS = 180 * 24 * 60 * 60 * 1000;
    const ONE_YEAR = 365 * 24 * 60 * 60 * 1000;

    let weakCount = 0;
    let fairCount = 0;
    let goodCount = 0;
    let strongCount = 0;
    let duplicateCount = 0;
    let expiredThreeMonths = 0;
    let expiredSixMonths = 0;
    let expiredOneYear = 0;
    let breachedCount = 0;
    let totalEntropy = 0;
    let avgEntropy = 0;

    const passwordMap = new Map();
    const duplicateGroups = [];

    for (const pwd of passwords) {
      if (pwd.strength === 'weak') weakCount++;
      else if (pwd.strength === 'fair') fairCount++;
      else if (pwd.strength === 'good') goodCount++;
      else if (pwd.strength === 'strong') strongCount++;

      if (pwd.entropy) {
        totalEntropy += pwd.entropy;
      }

      const age = now - (pwd.updatedAt || pwd.createdAt);
      if (age > THREE_MONTHS) expiredThreeMonths++;
      if (age > SIX_MONTHS) expiredSixMonths++;
      if (age > ONE_YEAR) expiredOneYear++;

      if (pwd.password) {
        if (passwordMap.has(pwd.password)) {
          passwordMap.get(pwd.password).push(pwd);
        } else {
          passwordMap.set(pwd.password, [pwd]);
        }
      }
    }

    passwordMap.forEach((entries, password) => {
      if (entries.length > 1) {
        duplicateCount++;
        duplicateGroups.push({
          password: password.substring(0, 4) + '***',
          count: entries.length,
          entries: entries.map(e => ({ id: e.id, title: e.title, username: e.username }))
        });
      }
    });

    if (passwords.length > 0) {
      avgEntropy = Math.round((totalEntropy / passwords.length) * 100) / 100;
    }

    return {
      byStrength: {
        weak: weakCount,
        fair: fairCount,
        good: goodCount,
        strong: strongCount
      },
      byAge: {
        threeMonths: expiredThreeMonths,
        sixMonths: expiredSixMonths,
        oneYear: expiredOneYear
      },
      duplicates: {
        count: duplicateCount,
        groups: duplicateGroups
      },
      entropy: {
        total: Math.round(totalEntropy * 100) / 100,
        average: avgEntropy
      },
      breached: breachedCount
    };
  }

  static async calculateTrends() {
    const history = await this.getHealthHistory();
    
    if (history.length === 0) {
      return {
        weekly: [],
        monthly: [],
        overall: 'stable'
      };
    }

    const weekly = history.slice(-7);
    const monthly = history.slice(-30);

    let overall = 'stable';
    if (history.length >= 2) {
      const first = history[0].score;
      const last = history[history.length - 1].score;
      const diff = last - first;
      
      if (diff > 10) overall = 'improving';
      else if (diff < -10) overall = 'declining';
    }

    return {
      weekly,
      monthly,
      overall,
      lastUpdated: history.length > 0 ? history[history.length - 1].timestamp : null
    };
  }

  static generateRecommendations(stats, passwords) {
    const recommendations = [];

    if (stats.byStrength.weak > 0) {
      recommendations.push({
        id: 'weak_passwords',
        priority: 'high',
        title: '替换弱密码',
        description: `您有 ${stats.byStrength.weak} 个弱密码，建议立即更换为更强的密码。`,
        count: stats.byStrength.weak,
        action: '查看弱密码'
      });
    }

    if (stats.duplicates.count > 0) {
      recommendations.push({
        id: 'duplicate_passwords',
        priority: 'high',
        title: '消除重复密码',
        description: `您有 ${stats.duplicates.count} 组重复使用的密码，每个账户应使用唯一密码。`,
        count: stats.duplicates.count,
        action: '查看重复密码'
      });
    }

    if (stats.byAge.oneYear > 0) {
      recommendations.push({
        id: 'old_passwords',
        priority: 'medium',
        title: '更新长期未修改的密码',
        description: `您有 ${stats.byAge.oneYear} 个密码超过1年未更新，建议定期更换重要账户密码。`,
        count: stats.byAge.oneYear,
        action: '查看老旧密码'
      });
    }

    if (stats.byStrength.fair > 0) {
      recommendations.push({
        id: 'improve_fair_passwords',
        priority: 'medium',
        title: '提升一般强度密码',
        description: `您有 ${stats.byStrength.fair} 个密码强度一般，可以进一步增强。`,
        count: stats.byStrength.fair,
        action: '查看并改进'
      });
    }

    if (stats.entropy.average < 60) {
      recommendations.push({
        id: 'low_entropy',
        priority: 'medium',
        title: '提升密码复杂度',
        description: `平均密码熵值为 ${stats.entropy.average} bits，建议使用更复杂的密码组合。`,
        count: null,
        action: '使用密码生成器'
      });
    }

    if (recommendations.length === 0) {
      recommendations.push({
        id: 'excellent',
        priority: 'low',
        title: '密码健康状况优秀',
        description: '您的密码安全习惯非常好，请继续保持！',
        count: null,
        action: null
      });
    }

    return recommendations;
  }

  static calculateHealthScore(stats, total) {
    if (total === 0) return 0;

    let score = 100;

    const weakRatio = stats.byStrength.weak / total;
    const fairRatio = stats.byStrength.fair / total;
    const duplicateRatio = stats.duplicates.count / total;
    const oldRatio = stats.byAge.sixMonths / total;

    score -= weakRatio * 50;
    score -= fairRatio * 20;
    score -= duplicateRatio * 30;
    score -= oldRatio * 15;

    if (stats.entropy.average >= 80) score += 10;
    else if (stats.entropy.average >= 60) score += 5;

    const strongRatio = stats.byStrength.strong / total;
    if (strongRatio >= 0.7) score += 10;
    else if (strongRatio >= 0.5) score += 5;

    return Math.max(0, Math.min(100, Math.round(score)));
  }

  static async saveHealthSnapshot() {
    const report = await this.generateReport();
    const history = await this.getHealthHistory();

    const snapshot = {
      timestamp: report.generatedAt,
      score: report.score,
      totalPasswords: report.totalPasswords,
      stats: {
        byStrength: report.stats.byStrength,
        byAge: report.stats.byAge,
        duplicates: report.stats.duplicates.count,
        avgEntropy: report.stats.entropy.average
      }
    };

    history.push(snapshot);

    if (history.length > MAX_HISTORY_ENTRIES) {
      history.splice(0, history.length - MAX_HISTORY_ENTRIES);
    }

    await dbService.setSetting(HEALTH_HISTORY_KEY, JSON.stringify(history));

    return snapshot;
  }

  static async getHealthHistory() {
    try {
      const data = await dbService.getSetting(HEALTH_HISTORY_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  static async clearHealthHistory() {
    await dbService.deleteSetting(HEALTH_HISTORY_KEY);
  }

  static getScoreLabel(score) {
    if (score >= 90) return { label: '优秀', color: '#22c55e', class: 'success' };
    if (score >= 75) return { label: '良好', color: '#3b82f6', class: 'info' };
    if (score >= 50) return { label: '一般', color: '#f59e0b', class: 'warning' };
    return { label: '较差', color: '#ef4444', class: 'danger' };
  }

  static async generateDetailedReport() {
    const report = await this.generateReport();
    const passwords = await dbService.getAllPasswords(true);

    const categoryBreakdown = {};
    passwords.forEach(pwd => {
      const cat = pwd.category || 'general';
      if (!categoryBreakdown[cat]) {
        categoryBreakdown[cat] = {
          total: 0,
          weak: 0,
          fair: 0,
          good: 0,
          strong: 0
        };
      }
      categoryBreakdown[cat].total++;
      categoryBreakdown[cat][pwd.strength || 'weak']++;
    });

    return {
      ...report,
      categoryBreakdown,
      passwordList: passwords.map(p => ({
        id: p.id,
        title: p.title,
        username: p.username,
        strength: p.strength,
        entropy: p.entropy,
        updatedAt: p.updatedAt,
        age: Date.now() - (p.updatedAt || p.createdAt)
      }))
    };
  }

  static formatAge(age) {
    const days = Math.floor(age / (24 * 60 * 60 * 1000));
    if (days < 30) return `${days}天`;
    if (days < 365) return `${Math.floor(days / 30)}个月`;
    return `${Math.floor(days / 365)}年${Math.floor((days % 365) / 30)}个月`;
  }

  static async exportReport(format = 'json') {
    const report = await this.generateDetailedReport();
    
    if (format === 'json') {
      return JSON.stringify(report, null, 2);
    } else if (format === 'csv') {
      const headers = ['标题', '用户名', '强度', '熵值(bits)', '最后更新', '密码年龄'];
      const rows = report.passwordList.map(p => [
        p.title,
        p.username,
        p.strength,
        p.entropy,
        new Date(p.updatedAt).toLocaleDateString('zh-CN'),
        this.formatAge(p.age)
      ]);
      
      return [headers, ...rows]
        .map(row => row.map(cell => `"${cell}"`).join(','))
        .join('\n');
    }
    
    throw new Error('不支持的导出格式');
  }
}
