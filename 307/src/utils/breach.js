import { cryptoService } from './crypto.js';
import { dbService } from './database.js';

const HIBP_API_BASE = 'https://api.pwnedpasswords.com/range/';
const BREACH_CHECK_CACHE_KEY = 'breachCheckCache';
const BREACH_CHECK_INTERVAL = 7 * 24 * 60 * 60 * 1000;

export class BreachService {
  static async sha1(password) {
    const encoder = new TextEncoder();
    const data = encoder.encode(password);
    const hashBuffer = await crypto.subtle.digest('SHA-1', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('').toUpperCase();
    return hashHex;
  }

  static async checkPasswordBreach(password) {
    try {
      const hash = await this.sha1(password);
      const prefix = hash.substring(0, 5);
      const suffix = hash.substring(5);

      const response = await fetch(`${HIBP_API_BASE}${prefix}`, {
        headers: {
          'Add-Padding': 'true'
        }
      });

      if (!response.ok) {
        throw new Error(`HIBP API error: ${response.status}`);
      }

      const text = await response.text();
      const lines = text.split('\n');

      for (const line of lines) {
        const [hashSuffix, count] = line.split(':');
        if (hashSuffix.trim() === suffix) {
          return {
            breached: true,
            count: parseInt(count.trim(), 10),
            hash
          };
        }
      }

      return {
        breached: false,
        count: 0,
        hash
      };
    } catch (error) {
      console.warn('密码泄露检查失败:', error.message);
      return {
        breached: false,
        count: 0,
        error: error.message
      };
    }
  }

  static async checkAllPasswords(progressCallback = null) {
    if (!cryptoService.isInitialized()) {
      throw new Error('请先解锁密码管理器');
    }

    const passwords = await dbService.getAllPasswords(true);
    const results = [];
    const cache = await this.getBreachCache();

    for (let i = 0; i < passwords.length; i++) {
      const pwd = passwords[i];
      
      if (!pwd.password) continue;

      const cachedResult = cache[pwd.id];
      const now = Date.now();
      
      if (cachedResult && (now - cachedResult.checkedAt < BREACH_CHECK_INTERVAL)) {
        results.push({
          ...pwd,
          breachInfo: cachedResult.breachInfo
        });
      } else {
        const breachInfo = await this.checkPasswordBreach(pwd.password);
        
        cache[pwd.id] = {
          breachInfo,
          checkedAt: now
        };

        results.push({
          ...pwd,
          breachInfo
        });
      }

      if (progressCallback) {
        progressCallback(i + 1, passwords.length);
      }

      await new Promise(resolve => setTimeout(resolve, 100));
    }

    await this.saveBreachCache(cache);

    const breachedPasswords = results.filter(r => r.breachInfo?.breached);

    return {
      total: passwords.length,
      checked: results.length,
      breachedCount: breachedPasswords.length,
      breachedPasswords,
      allResults: results
    };
  }

  static async getBreachCache() {
    try {
      const cached = await dbService.getSetting(BREACH_CHECK_CACHE_KEY);
      return cached ? JSON.parse(cached) : {};
    } catch {
      return {};
    }
  }

  static async saveBreachCache(cache) {
    await dbService.setSetting(BREACH_CHECK_CACHE_KEY, JSON.stringify(cache));
  }

  static async clearBreachCache() {
    await dbService.deleteSetting(BREACH_CHECK_CACHE_KEY);
  }

  static async getBreachedPasswords() {
    const cache = await this.getBreachCache();
    const passwords = await dbService.getAllPasswords(true);
    const now = Date.now();
    
    return passwords.filter(pwd => {
      const cached = cache[pwd.id];
      if (!cached) return false;
      if (now - cached.checkedAt > BREACH_CHECK_INTERVAL) return false;
      return cached.breachInfo?.breached;
    }).map(pwd => ({
      ...pwd,
      breachInfo: cache[pwd.id].breachInfo
    }));
  }

  static async getBreachStats() {
    const cache = await this.getBreachCache();
    const breached = Object.values(cache).filter(c => c.breachInfo?.breached);
    
    let totalExposures = 0;
    breached.forEach(b => {
      totalExposures += b.breachInfo?.count || 0;
    });

    return {
      totalChecked: Object.keys(cache).length,
      breachedCount: breached.length,
      totalExposures
    };
  }

  static async checkPasswordById(passwordId) {
    const pwd = await dbService.getDecryptedPassword(passwordId);
    if (!pwd || !pwd.password) {
      throw new Error('密码记录不存在');
    }

    const breachInfo = await this.checkPasswordBreach(pwd.password);
    
    const cache = await this.getBreachCache();
    cache[passwordId] = {
      breachInfo,
      checkedAt: Date.now()
    };
    await this.saveBreachCache(cache);

    return {
      ...pwd,
      breachInfo
    };
  }
}
