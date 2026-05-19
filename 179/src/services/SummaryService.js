const axios = require('axios');
const config = require('../config');
const logger = require('../utils/logger');

class SummaryService {
  constructor() {
    this.stopWords = new Set([
      '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
      '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '她', '他', '它', '们', '这个', '那个', '什么', '怎么', '为什么',
      '可以', '可能', '应该', '需要', '因为', '所以', '但是', '而且', '或者', '如果', '虽然', '然而', '因此', '于是',
      'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
      'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
      'can', 'will', 'just', 'like', 'get', 'got', 'make', 'made', 'take', 'took', 'come', 'came',
      'see', 'saw', 'know', 'knew', 'think', 'thought', 'want', 'wanted', 'use', 'used', 'find', 'found',
      'this', 'that', 'these', 'those', 'it', 'its', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by'
    ]);
    
    this.useExternalAI = config.ai?.summary?.useExternalAI || false;
    this.externalAIEndpoint = config.ai?.summary?.endpoint || '';
    this.externalAIKey = config.ai?.summary?.apiKey || '';
    this.minLengthForSummary = config.ai?.summary?.minLength || 200;
    this.defaultSummaryLength = config.ai?.summary?.defaultLength || 100;
  }

  segmentSentences(text) {
    const cleanedText = text.replace(/\s+/g, ' ').trim();
    
    const chinesePattern = /([。！？!?；;])/g;
    const englishPattern = /([.!?])/g;
    
    let sentences = [];
    let lastIndex = 0;
    
    const combinedPattern = /([。！？!?；;])/g;
    let match;
    
    while ((match = combinedPattern.exec(cleanedText)) !== null) {
      const sentence = cleanedText.substring(lastIndex, match.index + 1).trim();
      if (sentence.length > 5) {
        sentences.push(sentence);
      }
      lastIndex = match.index + 1;
    }
    
    if (lastIndex < cleanedText.length) {
      const remaining = cleanedText.substring(lastIndex).trim();
      if (remaining.length > 5) {
        sentences.push(remaining);
      }
    }
    
    if (sentences.length === 0 && cleanedText.length > 0) {
      sentences = cleanedText.split(/[。！？!?；;.]/).filter(s => s.trim().length > 5);
    }
    
    return sentences;
  }

  tokenize(text) {
    const words = [];
    
    const chineseChars = text.match(/[\u4e00-\u9fa5]/g) || [];
    for (let i = 0; i < chineseChars.length - 1; i++) {
      words.push(chineseChars[i] + chineseChars[i + 1]);
    }
    
    const englishWords = text.match(/[a-zA-Z]+/g) || [];
    words.push(...englishWords);
    
    return words.filter(word => 
      word.length > 1 && !this.stopWords.has(word.toLowerCase())
    );
  }

  calculateSimilarity(sent1, sent2) {
    const words1 = this.tokenize(sent1);
    const words2 = this.tokenize(sent2);
    
    if (words1.length === 0 || words2.length === 0) return 0;
    
    const wordSet1 = new Set(words1);
    const wordSet2 = new Set(words2);
    
    const intersection = new Set([...wordSet1].filter(x => wordSet2.has(x)));
    const union = new Set([...wordSet1, ...wordSet2]);
    
    return intersection.size / union.size;
  }

  buildSimilarityMatrix(sentences) {
    const n = sentences.length;
    const matrix = Array(n).fill(null).map(() => Array(n).fill(0));
    
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        if (i !== j) {
          matrix[i][j] = this.calculateSimilarity(sentences[i], sentences[j]);
        }
      }
    }
    
    return matrix;
  }

  textRank(sentences, maxIterations = 100, damping = 0.85, tolerance = 1e-4) {
    const n = sentences.length;
    if (n === 0) return [];
    if (n === 1) return [1.0];
    
    const matrix = this.buildSimilarityMatrix(sentences);
    
    const rowSums = matrix.map(row => row.reduce((a, b) => a + b, 0));
    
    for (let i = 0; i < n; i++) {
      if (rowSums[i] > 0) {
        for (let j = 0; j < n; j++) {
          matrix[i][j] = matrix[i][j] / rowSums[i];
        }
      }
    }
    
    let scores = Array(n).fill(1.0 / n);
    let prevScores = [...scores];
    
    for (let iter = 0; iter < maxIterations; iter++) {
      for (let j = 0; j < n; j++) {
        let sum = 0;
        for (let i = 0; i < n; i++) {
          sum += matrix[i][j] * prevScores[i];
        }
        scores[j] = (1 - damping) / n + damping * sum;
      }
      
      const diff = scores.reduce((acc, val, idx) => acc + Math.abs(val - prevScores[idx]), 0);
      if (diff < tolerance) break;
      
      prevScores = [...scores];
    }
    
    return scores;
  }

  async summarizeText(text, maxLength = null) {
    if (!text || text.trim().length === 0) {
      return { summary: '', method: 'none', length: 0 };
    }

    const targetLength = maxLength || this.defaultSummaryLength;
    
    if (text.length <= this.minLengthForSummary) {
      return {
        summary: text.substring(0, targetLength) + (text.length > targetLength ? '...' : ''),
        method: 'truncated',
        length: Math.min(text.length, targetLength)
      };
    }

    if (this.useExternalAI && this.externalAIEndpoint) {
      try {
        const externalSummary = await this.callExternalAI(text, targetLength);
        if (externalSummary) {
          return {
            summary: externalSummary,
            method: 'external_ai',
            length: externalSummary.length
          };
        }
      } catch (error) {
        logger.warn('External AI summary failed, falling back to TextRank:', error.message);
      }
    }

    return this.textRankSummary(text, targetLength);
  }

  textRankSummary(text, targetLength) {
    const sentences = this.segmentSentences(text);
    
    if (sentences.length === 0) {
      return {
        summary: text.substring(0, targetLength) + '...',
        method: 'truncated',
        length: targetLength
      };
    }
    
    if (sentences.length === 1) {
      const summary = sentences[0].length > targetLength 
        ? sentences[0].substring(0, targetLength) + '...'
        : sentences[0];
      return {
        summary,
        method: 'single_sentence',
        length: summary.length
      };
    }
    
    const scores = this.textRank(sentences);
    const scoredSentences = sentences.map((sent, idx) => ({
      text: sent,
      score: scores[idx],
      index: idx
    }));
    
    scoredSentences.sort((a, b) => b.score - a.score);
    
    const numSentences = Math.min(3, Math.max(1, Math.ceil(targetLength / 100)));
    const topSentences = scoredSentences
      .slice(0, numSentences)
      .sort((a, b) => a.index - b.index);
    
    let summary = topSentences.map(s => s.text).join(' ');
    
    if (summary.length > targetLength * 1.5) {
      summary = summary.substring(0, targetLength) + '...';
    }
    
    return {
      summary: summary.trim(),
      method: 'textrank',
      length: summary.length,
      keySentences: topSentences.map(s => ({
        text: s.text,
        score: s.score.toFixed(4)
      }))
    };
  }

  async callExternalAI(text, targetLength) {
    try {
      const response = await axios.post(
        this.externalAIEndpoint,
        {
          model: 'gpt-3.5-turbo',
          messages: [
            {
              role: 'system',
              content: `请将以下文本总结为${targetLength}字以内的摘要，保持关键信息。`
            },
            {
              role: 'user',
              content: text
            }
          ],
          max_tokens: Math.ceil(targetLength * 1.5),
          temperature: 0.3
        },
        {
          headers: {
            'Authorization': `Bearer ${this.externalAIKey}`,
            'Content-Type': 'application/json'
          },
          timeout: 10000
        }
      );

      if (response.data?.choices?.[0]?.message?.content) {
        return response.data.choices[0].message.content.trim();
      }
      
      return null;
    } catch (error) {
      throw error;
    }
  }

  async summarizeMessage(message) {
    const fullText = `${message.title || ''}\n${message.content || ''}`.trim();
    const result = await this.summarizeText(fullText);
    return result;
  }

  async summarizeBatch(messages, maxLength = null) {
    const results = [];
    for (const msg of messages) {
      try {
        const summary = await this.summarizeMessage(msg);
        results.push({
          messageId: msg.messageId,
          ...summary
        });
      } catch (error) {
        logger.error(`Failed to summarize message ${msg.messageId}:`, error);
        results.push({
          messageId: msg.messageId,
          summary: '',
          method: 'failed',
          length: 0,
          error: error.message
        });
      }
    }
    return results;
  }
}

module.exports = new SummaryService();
module.exports.SummaryService = SummaryService;
