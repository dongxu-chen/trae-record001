import { cryptoService } from './crypto.js';
import { dbService } from './database.js';

const EMERGENCY_CONTACTS_KEY = 'emergencyContacts';
const EMERGENCY_REQUESTS_KEY = 'emergencyRequests';
const EMERGENCY_GRANTS_KEY = 'emergencyGrants';
const DEFAULT_WAITING_PERIOD = 24 * 60 * 60 * 1000;

export class EmergencyAccessService {
  static async addContact(contact) {
    const contacts = await this.getContacts();
    
    if (contacts.some(c => c.email === contact.email)) {
      throw new Error('该联系人已存在');
    }

    const keyPair = await cryptoService.generateShareKey();

    const newContact = {
      id: Date.now(),
      name: contact.name,
      email: contact.email,
      publicKey: keyPair.publicKey,
      privateKey: keyPair.privateKey,
      waitingPeriod: contact.waitingPeriod || DEFAULT_WAITING_PERIOD,
      permissions: contact.permissions || ['read'],
      createdAt: Date.now(),
      status: 'active'
    };

    contacts.push(newContact);
    await this.saveContacts(contacts);

    return newContact;
  }

  static async getContacts() {
    try {
      const data = await dbService.getSetting(EMERGENCY_CONTACTS_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  static async saveContacts(contacts) {
    await dbService.setSetting(EMERGENCY_CONTACTS_KEY, JSON.stringify(contacts));
  }

  static async removeContact(contactId) {
    const contacts = await this.getContacts();
    const filtered = contacts.filter(c => c.id !== contactId);
    await this.saveContacts(filtered);

    const requests = await this.getRequests();
    const filteredRequests = requests.filter(r => r.contactId !== contactId);
    await this.saveRequests(filteredRequests);
  }

  static async updateContact(contactId, updates) {
    const contacts = await this.getContacts();
    const index = contacts.findIndex(c => c.id === contactId);
    
    if (index === -1) {
      throw new Error('联系人不存在');
    }

    contacts[index] = { ...contacts[index], ...updates };
    await this.saveContacts(contacts);
    
    return contacts[index];
  }

  static async createRequest(contactId, reason = '') {
    const contacts = await this.getContacts();
    const contact = contacts.find(c => c.id === contactId);
    
    if (!contact) {
      throw new Error('紧急联系人不存在');
    }

    if (contact.status !== 'active') {
      throw new Error('该联系人未激活');
    }

    const requests = await this.getRequests();
    
    const pendingRequest = requests.find(
      r => r.contactId === contactId && r.status === 'pending'
    );
    
    if (pendingRequest) {
      throw new Error('已有待处理的紧急访问请求');
    }

    const newRequest = {
      id: Date.now(),
      contactId,
      contactName: contact.name,
      contactEmail: contact.email,
      reason,
      status: 'pending',
      requestedAt: Date.now(),
      waitingPeriodEnds: Date.now() + contact.waitingPeriod,
      grantedAt: null,
      expiresAt: null
    };

    requests.push(newRequest);
    await this.saveRequests(requests);

    return newRequest;
  }

  static async getRequests() {
    try {
      const data = await dbService.getSetting(EMERGENCY_REQUESTS_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  static async saveRequests(requests) {
    await dbService.setSetting(EMERGENCY_REQUESTS_KEY, JSON.stringify(requests));
  }

  static async approveRequest(requestId, options = {}) {
    const requests = await this.getRequests();
    const request = requests.find(r => r.id === requestId);
    
    if (!request) {
      throw new Error('请求不存在');
    }

    const contacts = await this.getContacts();
    const contact = contacts.find(c => c.id === request.contactId);
    
    if (!contact) {
      throw new Error('联系人不存在');
    }

    const duration = options.duration || 1 * 60 * 60 * 1000;
    const now = Date.now();

    const accessToken = this.generateAccessToken();
    
    const encryptedData = await this.encryptVaultData(contact.publicKey, {
      accessToken,
      permissions: contact.permissions,
      expiresAt: now + duration
    });

    const grants = await this.getGrants();
    const newGrant = {
      id: Date.now(),
      requestId,
      contactId: contact.id,
      contactName: contact.name,
      accessToken,
      encryptedData,
      permissions: contact.permissions,
      grantedAt: now,
      expiresAt: now + duration,
      status: 'active'
    };

    grants.push(newGrant);
    await this.saveGrants(grants);

    request.status = 'approved';
    request.grantedAt = now;
    request.expiresAt = now + duration;
    request.accessToken = accessToken;
    await this.saveRequests(requests);

    return {
      request,
      grant: newGrant,
      accessUrl: this.generateAccessUrl(accessToken)
    };
  }

  static async denyRequest(requestId, reason = '') {
    const requests = await this.getRequests();
    const request = requests.find(r => r.id === requestId);
    
    if (!request) {
      throw new Error('请求不存在');
    }

    request.status = 'denied';
    request.deniedAt = Date.now();
    request.denyReason = reason;
    await this.saveRequests(requests);

    return request;
  }

  static async cancelRequest(requestId) {
    const requests = await this.getRequests();
    const request = requests.find(r => r.id === requestId);
    
    if (!request) {
      throw new Error('请求不存在');
    }

    if (request.status !== 'pending') {
      throw new Error('只能取消待处理的请求');
    }

    request.status = 'cancelled';
    request.cancelledAt = Date.now();
    await this.saveRequests(requests);

    return request;
  }

  static async getGrants() {
    try {
      const data = await dbService.getSetting(EMERGENCY_GRANTS_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  static async saveGrants(grants) {
    await dbService.setSetting(EMERGENCY_GRANTS_KEY, JSON.stringify(grants));
  }

  static async revokeGrant(grantId) {
    const grants = await this.getGrants();
    const grant = grants.find(g => g.id === grantId);
    
    if (!grant) {
      throw new Error('授权不存在');
    }

    grant.status = 'revoked';
    grant.revokedAt = Date.now();
    await this.saveGrants(grants);

    return grant;
  }

  static async validateAccessToken(accessToken) {
    const grants = await this.getGrants();
    const grant = grants.find(g => g.accessToken === accessToken);
    
    if (!grant) {
      return { valid: false, error: '无效的访问令牌' };
    }

    if (grant.status !== 'active') {
      return { valid: false, error: '访问授权已被撤销' };
    }

    if (Date.now() > grant.expiresAt) {
      grant.status = 'expired';
      await this.saveGrants(grants);
      return { valid: false, error: '访问授权已过期' };
    }

    return { valid: true, grant };
  }

  static async getEmergencyAccessData(accessToken) {
    const validation = await this.validateAccessToken(accessToken);
    
    if (!validation.valid) {
      throw new Error(validation.error);
    }

    const { grant } = validation;

    if (grant.permissions.includes('read')) {
      const passwords = await dbService.getAllPasswords(true);
      return {
        passwords,
        permissions: grant.permissions,
        expiresAt: grant.expiresAt
      };
    }

    throw new Error('没有读取权限');
  }

  static async getPendingRequests() {
    const requests = await this.getRequests();
    return requests.filter(r => r.status === 'pending');
  }

  static async getActiveGrants() {
    const grants = await this.getGrants();
    const now = Date.now();
    return grants.filter(g => g.status === 'active' && g.expiresAt > now);
  }

  static generateAccessToken() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array)
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  }

  static generateAccessUrl(token) {
    return `${window.location.origin}${window.location.pathname}#/emergency/${token}`;
  }

  static async encryptVaultData(publicKey, data) {
    return await cryptoService.encryptWithPublicKey(data, publicKey);
  }

  static async decryptVaultData(privateKey, encryptedData) {
    return await cryptoService.decryptWithPrivateKey(encryptedData, privateKey);
  }

  static getWaitingPeriodOptions() {
    return [
      { value: 0, label: '立即批准（无等待期）' },
      { value: 1 * 60 * 60 * 1000, label: '1小时' },
      { value: 6 * 60 * 60 * 1000, label: '6小时' },
      { value: 12 * 60 * 60 * 1000, label: '12小时' },
      { value: 24 * 60 * 60 * 1000, label: '24小时' },
      { value: 3 * 24 * 60 * 60 * 1000, label: '3天' },
      { value: 7 * 24 * 60 * 60 * 1000, label: '7天' }
    ];
  }

  static getDurationOptions() {
    return [
      { value: 30 * 60 * 1000, label: '30分钟' },
      { value: 1 * 60 * 60 * 1000, label: '1小时' },
      { value: 4 * 60 * 60 * 1000, label: '4小时' },
      { value: 12 * 60 * 60 * 1000, label: '12小时' },
      { value: 24 * 60 * 60 * 1000, label: '24小时' }
    ];
  }
}
