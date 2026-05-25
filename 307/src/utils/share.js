import { cryptoService } from './crypto.js';
import { dbService } from './database.js';

export class ShareService {
  static async createShareLink(passwordId, options = {}) {
    const {
      expiresIn = 24 * 60 * 60 * 1000,
      maxAccesses = 1,
      requirePassword = false
    } = options;

    const password = await dbService.getDecryptedPassword(passwordId);
    if (!password) {
      throw new Error('密码记录不存在');
    }

    const shareKey = await cryptoService.generateShareKey();
    const shareToken = this.generateShareToken();
    const expiresAt = Date.now() + expiresIn;

    const dataToShare = {
      id: passwordId,
      title: password.title,
      username: password.username,
      password: password.password,
      url: password.url,
      notes: password.notes,
      sharedAt: Date.now(),
      expiresAt,
      maxAccesses,
      accessCount: 0
    };

    const encryptedData = await cryptoService.encryptWithPublicKey(
      dataToShare,
      shareKey.publicKey
    );

    const shareRecord = {
      token: shareToken,
      passwordId,
      encryptedData,
      publicKey: shareKey.publicKey,
      privateKey: shareKey.privateKey,
      expiresAt,
      maxAccesses,
      accessCount: 0,
      requirePassword,
      sharePassword: requirePassword ? options.sharePassword : null,
      createdAt: Date.now()
    };

    const shareId = await dbService.addSharedPassword(shareRecord);

    const baseUrl = window.location.origin + window.location.pathname;
    const shareUrl = `${baseUrl}#/share/${shareToken}`;

    return {
      shareId,
      shareUrl,
      shareToken,
      expiresAt,
      maxAccesses,
      requirePassword,
      privateKey: shareKey.privateKey
    };
  }

  static async getSharedData(shareToken, sharePassword = null) {
    const sharedPasswords = await dbService.getSharedPasswords();
    const shareRecord = sharedPasswords.find(s => s.token === shareToken);

    if (!shareRecord) {
      throw new Error('分享链接无效或已过期');
    }

    if (shareRecord.expiresAt < Date.now()) {
      await dbService.deleteSharedPassword(shareRecord.id);
      throw new Error('分享链接已过期');
    }

    if (shareRecord.accessCount >= shareRecord.maxAccesses) {
      await dbService.deleteSharedPassword(shareRecord.id);
      throw new Error('分享链接已达到最大访问次数');
    }

    if (shareRecord.requirePassword) {
      if (!sharePassword) {
        throw new Error('需要输入分享密码');
      }
      if (sharePassword !== shareRecord.sharePassword) {
        throw new Error('分享密码错误');
      }
    }

    const decryptedData = await cryptoService.decryptWithPrivateKey(
      shareRecord.encryptedData,
      shareRecord.privateKey
    );

    shareRecord.accessCount++;
    await dbService._executeTransaction('shared', 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.put({ ...shareRecord, id: Number(shareRecord.id) });
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    });

    if (shareRecord.accessCount >= shareRecord.maxAccesses) {
      await dbService.deleteSharedPassword(shareRecord.id);
    }

    return {
      ...decryptedData,
      remainingAccesses: shareRecord.maxAccesses - shareRecord.accessCount,
      expiresAt: shareRecord.expiresAt
    };
  }

  static generateShareToken() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array)
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  }

  static async getActiveShares() {
    const sharedPasswords = await dbService.getSharedPasswords();
    const now = Date.now();

    const activeShares = sharedPasswords.filter(s => s.expiresAt > now);

    return Promise.all(
      activeShares.map(async (share) => {
        const password = await dbService.getPassword(share.passwordId);
        return {
          ...share,
          passwordTitle: password ? password.title : 'Unknown'
        };
      })
    );
  }

  static async revokeShare(shareId) {
    await dbService.deleteSharedPassword(shareId);
  }

  static async cleanupExpiredShares() {
    const sharedPasswords = await dbService.getSharedPasswords();
    const now = Date.now();
    let count = 0;

    for (const share of sharedPasswords) {
      if (share.expiresAt < now) {
        await dbService.deleteSharedPassword(share.id);
        count++;
      }
    }

    return count;
  }

  static createEmergencyKit(masterPassword, salt) {
    const kitData = {
      version: 1,
      createdAt: Date.now(),
      salt: salt,
      hint: this.createPasswordHint(masterPassword),
      recoveryCode: this.generateRecoveryCode()
    };

    return {
      ...kitData,
      qrData: btoa(JSON.stringify(kitData)),
      downloadUrl: this.createDownloadUrl(kitData)
    };
  }

  static createPasswordHint(password) {
    if (password.length <= 4) return '****';
    return password.substring(0, 2) + '*'.repeat(password.length - 4) + password.substring(password.length - 2);
  }

  static generateRecoveryCode() {
    const words = [
      'alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot',
      'golf', 'hotel', 'india', 'juliett', 'kilo', 'lima',
      'mike', 'november', 'oscar', 'papa', 'quebec', 'romeo',
      'sierra', 'tango', 'uniform', 'victor', 'whiskey', 'xray'
    ];

    const code = [];
    for (let i = 0; i < 8; i++) {
      const randomIndex = crypto.getRandomValues(new Uint32Array(1))[0] % words.length;
      code.push(words[randomIndex]);
    }

    return code.join('-');
  }

  static createDownloadUrl(data) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    return URL.createObjectURL(blob);
  }

  static validateRecoveryCode(code) {
    const pattern = /^[a-z]+(-[a-z]+){7}$/;
    return pattern.test(code);
  }
}
