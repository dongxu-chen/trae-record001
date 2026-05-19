const crypto = require('crypto');

class SimHash {
  constructor(hashBits = 64) {
    this.hashBits = hashBits;
    this.stopWords = new Set([
      '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
      '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '她', '他', '它', '们', '这个', '那个', '什么', '怎么', '为什么',
      'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
      'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
      'can', 'will', 'just', 'like', 'get', 'got', 'make', 'made', 'take', 'took', 'come', 'came',
      'see', 'saw', 'know', 'knew', 'think', 'thought', 'want', 'wanted', 'use', 'used', 'find', 'found'
    ]);
  }

  tokenize(text) {
    const cleanedText = text.toLowerCase()
      .replace(/[^\w\u4e00-\u9fa5\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    const words = [];
    
    const chineseChars = cleanedText.match(/[\u4e00-\u9fa5]/g) || [];
    for (let i = 0; i < chineseChars.length - 1; i++) {
      words.push(chineseChars[i] + chineseChars[i + 1]);
    }

    const englishWords = cleanedText.match(/[a-zA-Z]+/g) || [];
    words.push(...englishWords);

    return words.filter(word => 
      word.length > 1 && !this.stopWords.has(word.toLowerCase())
    );
  }

  hash(word) {
    const hash = crypto.createHash('sha256').update(word).digest('hex');
    const hashNum = BigInt('0x' + hash.substring(0, 16));
    return hashNum;
  }

  compute(text) {
    const tokens = this.tokenize(text);
    if (tokens.length === 0) {
      return BigInt(0);
    }

    const vector = new Array(this.hashBits).fill(0);

    for (const token of tokens) {
      const hash = this.hash(token);
      for (let i = 0; i < this.hashBits; i++) {
        const bit = (hash >> BigInt(i)) & BigInt(1);
        vector[i] += bit === BigInt(1) ? 1 : -1;
      }
    }

    let fingerprint = BigInt(0);
    for (let i = 0; i < this.hashBits; i++) {
      if (vector[i] > 0) {
        fingerprint |= (BigInt(1) << BigInt(i));
      }
    }

    return fingerprint;
  }

  hammingDistance(hash1, hash2) {
    let xor = hash1 ^ hash2;
    let distance = 0;
    while (xor > 0) {
      distance += Number(xor & BigInt(1));
      xor >>= BigInt(1);
    }
    return distance;
  }

  similarity(hash1, hash2) {
    const distance = this.hammingDistance(hash1, hash2);
    return 1 - (distance / this.hashBits);
  }

  areSimilar(text1, text2, threshold = 0.85) {
    const hash1 = this.compute(text1);
    const hash2 = this.compute(text2);
    const sim = this.similarity(hash1, hash2);
    return sim >= threshold;
  }

  similarityText(text1, text2) {
    const hash1 = this.compute(text1);
    const hash2 = this.compute(text2);
    return this.similarity(hash1, hash2);
  }

  toHexString(hash) {
    return '0x' + hash.toString(16).padStart(Math.ceil(this.hashBits / 4), '0');
  }

  fromHexString(hexString) {
    return BigInt(hexString);
  }
}

const defaultSimHash = new SimHash(64);

module.exports = {
  SimHash,
  compute: (text) => defaultSimHash.compute(text),
  similarity: (hash1, hash2) => defaultSimHash.similarity(hash1, hash2),
  areSimilar: (text1, text2, threshold) => defaultSimHash.areSimilar(text1, text2, threshold),
  similarityText: (text1, text2) => defaultSimHash.similarityText(text1, text2)
};
