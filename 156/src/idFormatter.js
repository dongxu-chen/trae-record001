class IDFormatter {
  constructor(options = {}) {
    this.prefixMap = new Map();
    this.defaultPrefix = options.defaultPrefix || '';
    this.separator = options.separator || '_';
    this.enableTimestamp = options.enableTimestamp !== false;
    this.enableChecksum = options.enableChecksum || false;
  }

  registerPrefix(bizType, prefix) {
    this.prefixMap.set(bizType, prefix);
    console.log(`已注册业务类型[${bizType}]前缀: ${prefix}`);
  }

  getPrefix(bizType) {
    return this.prefixMap.get(bizType) || this.defaultPrefix;
  }

  generateTimestamp() {
    return Date.now().toString(36);
  }

  calculateChecksum(str) {
    let checksum = 0;
    for (let i = 0; i < str.length; i++) {
      checksum = ((checksum << 5) - checksum + str.charCodeAt(i)) & 0xFFFFFFFF;
    }
    return Math.abs(checksum % 36).toString(36);
  }

  format(id, bizType = 'default', options = {}) {
    const prefix = options.prefix || this.getPrefix(bizType);
    const separator = options.separator || this.separator;
    const enableTimestamp = options.enableTimestamp !== undefined ? options.enableTimestamp : this.enableTimestamp;
    const enableChecksum = options.enableChecksum !== undefined ? options.enableChecksum : this.enableChecksum;

    const parts = [];

    if (prefix) {
      parts.push(prefix);
    }

    if (enableTimestamp) {
      parts.push(this.generateTimestamp());
    }

    if (typeof id === 'bigint') {
      parts.push(id.toString());
    } else {
      parts.push(id.toString());
    }

    let formattedId = parts.join(separator);

    if (enableChecksum) {
      const checksum = this.calculateChecksum(formattedId);
      formattedId = `${formattedId}${separator}${checksum}`;
    }

    return formattedId;
  }

  parse(formattedId, separator = this.separator) {
    const parts = formattedId.split(separator);
    const result = {
      prefix: null,
      timestamp: null,
      id: null,
      checksum: null,
      valid: true
    };

    if (parts.length >= 3) {
      result.prefix = parts[0];
      result.timestamp = parseInt(parts[1], 36);
      result.id = BigInt(parts[2]);
      if (parts.length >= 4) {
        result.checksum = parts[3];
        const idWithoutChecksum = parts.slice(0, 3).join(separator);
        const expectedChecksum = this.calculateChecksum(idWithoutChecksum);
        result.valid = result.checksum === expectedChecksum;
      }
    } else if (parts.length === 2) {
      if (isNaN(parseInt(parts[0], 36))) {
        result.prefix = parts[0];
        result.timestamp = Date.now();
      } else {
        result.timestamp = parseInt(parts[0], 36);
      }
      result.id = BigInt(parts[1]);
    } else {
      result.id = BigInt(parts[0]);
      result.timestamp = Date.now();
    }

    return result;
  }

  shortId(id, bizType = 'default') {
    const prefix = this.getPrefix(bizType);
    const base36Id = typeof id === 'bigint' ? id.toString(36) : BigInt(id).toString(36);
    
    if (prefix) {
      return `${prefix}${this.separator}${base36Id}`;
    }
    return base36Id;
  }

  humanReadable(id, bizType = 'default') {
    const prefix = this.getPrefix(bizType);
    const timestamp = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const idStr = id.toString();
    const chunks = idStr.match(/.{1,4}/g) || [idStr];
    
    const parts = [];
    if (prefix) parts.push(prefix);
    parts.push(timestamp);
    parts.push(...chunks);
    
    return parts.join('-');
  }
}

module.exports = IDFormatter;