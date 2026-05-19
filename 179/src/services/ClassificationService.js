const logger = require('../utils/logger');
const { FastTextClassifier, trainDefault } = require('./FastTextClassifier');
const synonymService = require('./SynonymService');

class ClassificationService {
  constructor() {
    this.classifier = new FastTextClassifier({
      learningRate: 0.05,
      epochs: 150,
      dim: 128,
      wordNgrams: 2
    });
    this.isTrained = false;
    this.useKeywordFallback = true;

    this.categoryKeywords = {
      approval: [
        '审批', '批准', '审核', '同意', '驳回', '发起审批', '待审批',
        '审批通过', '审批拒绝', '请假', '加班', '报销', '采购', '合同',
        'approve', 'approval', 'review', 'reject', 'agree'
      ],
      alert: [
        '告警', '报警', '错误', '异常', '失败', '故障', '宕机', '超时',
        '严重', '紧急', 'critical', 'error', 'alert', 'warn', 'warning',
        'failure', 'down', 'timeout', 'exception', 'panic', 'fatal'
      ],
      notification: [
        '通知', '公告', '提醒', '消息', '更新', '发布', '上线',
        'notification', 'notice', 'reminder', 'update', 'announce'
      ]
    };

    this.priorityKeywords = {
      urgent: [
        '紧急', '立即', '马上', '立刻', 'urgent', 'immediate', 'asap',
        'critical', 'fatal', 'severity 1', 'p0'
      ],
      high: [
        '重要', '优先', 'high', 'priority', 'important', 'severity 2', 'p1'
      ],
      medium: [
        '普通', '常规', 'normal', 'medium', 'severity 3', 'p2'
      ],
      low: [
        '次要', '低', 'low', 'minor', 'severity 4', 'p3'
      ]
    };
  }

  async initialize() {
    if (this.isTrained) return;

    try {
      await synonymService.loadSynonyms();
      await trainDefault();
      this.classifier = require('./FastTextClassifier').classifier;
      this.isTrained = this.classifier.isTrained;
      logger.info('FastText classifier initialized');
    } catch (error) {
      logger.error('Failed to initialize FastText classifier, using keyword fallback:', error.message);
      this.isTrained = false;
    }
  }

  async classify(message) {
    const text = `${message.title || ''} ${message.content || ''}`;
    const lowerText = text.toLowerCase();

    if (this.isTrained) {
      try {
        const predictions = await this.classifier.predict(text, 3);
        
        if (predictions.length > 0 && predictions[0].probability > 0.3) {
          const category = predictions[0].label;
          const priority = this.determinePriority(lowerText);
          const scores = {};
          
          for (const pred of predictions) {
            scores[pred.label] = pred.probability;
          }

          return {
            category,
            priority,
            scores,
            method: 'fasttext',
            predictions
          };
        }
      } catch (error) {
        logger.warn('FastText classification failed, falling back to keyword method:', error.message);
      }
    }

    return this.keywordClassify(lowerText);
  }

  keywordClassify(lowerText) {
    const scores = {
      approval: this.calculateScore(lowerText, this.categoryKeywords.approval),
      alert: this.calculateScore(lowerText, this.categoryKeywords.alert),
      notification: this.calculateScore(lowerText, this.categoryKeywords.notification)
    };

    let category = 'other';
    let maxScore = 0;

    for (const [cat, score] of Object.entries(scores)) {
      if (score > maxScore) {
        maxScore = score;
        category = cat;
      }
    }

    const priority = this.determinePriority(lowerText);

    return {
      category,
      priority,
      scores,
      method: 'keyword'
    };
  }

  calculateScore(text, keywords) {
    let score = 0;
    for (const keyword of keywords) {
      const lowerKeyword = keyword.toLowerCase();
      const regex = new RegExp(this.escapeRegex(lowerKeyword), 'gi');
      const matches = text.match(regex);
      if (matches) {
        score += matches.length * (lowerKeyword.length > 2 ? 2 : 1);
      }

      const synonyms = synonymService.getSynonyms(keyword);
      for (const syn of synonyms) {
        if (syn !== keyword) {
          const synRegex = new RegExp(this.escapeRegex(syn.toLowerCase()), 'gi');
          const synMatches = text.match(synRegex);
          if (synMatches) {
            score += synMatches.length;
          }
        }
      }
    }
    return score;
  }

  determinePriority(text) {
    for (const keyword of this.priorityKeywords.urgent) {
      if (text.includes(keyword.toLowerCase())) {
        return 'urgent';
      }
      const synonyms = synonymService.getSynonyms(keyword);
      for (const syn of synonyms) {
        if (text.includes(syn.toLowerCase())) {
          return 'urgent';
        }
      }
    }

    for (const keyword of this.priorityKeywords.high) {
      if (text.includes(keyword.toLowerCase())) {
        return 'high';
      }
      const synonyms = synonymService.getSynonyms(keyword);
      for (const syn of synonyms) {
        if (text.includes(syn.toLowerCase())) {
          return 'high';
        }
      }
    }

    for (const keyword of this.priorityKeywords.low) {
      if (text.includes(keyword.toLowerCase())) {
        return 'low';
      }
    }

    return 'medium';
  }

  escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  addCategoryKeyword(category, keyword) {
    if (!this.categoryKeywords[category]) {
      this.categoryKeywords[category] = [];
    }
    if (!this.categoryKeywords[category].includes(keyword)) {
      this.categoryKeywords[category].push(keyword);
    }
    logger.info(`Added keyword '${keyword}' to category '${category}'`);
  }

  removeCategoryKeyword(category, keyword) {
    if (this.categoryKeywords[category]) {
      const index = this.categoryKeywords[category].indexOf(keyword);
      if (index > -1) {
        this.categoryKeywords[category].splice(index, 1);
        logger.info(`Removed keyword '${keyword}' from category '${category}'`);
      }
    }
  }

  getCategoryKeywords() {
    return { ...this.categoryKeywords };
  }

  async classifyBatch(messages) {
    const results = [];
    for (const msg of messages) {
      const classification = await this.classify(msg);
      results.push({
        ...msg,
        ...classification
      });
    }
    return results;
  }

  async retrain(trainingData) {
    try {
      await this.classifier.train(trainingData);
      this.isTrained = true;
      logger.info('FastText classifier retrained with new data');
      return true;
    } catch (error) {
      logger.error('Failed to retrain classifier:', error);
      return false;
    }
  }

  async addTrainingSample(text, label) {
    logger.info(`Added training sample: [${label}] ${text.substring(0, 50)}...`);
  }

  getModelInfo() {
    return {
      isTrained: this.isTrained,
      vocabSize: this.classifier.getVocabSize(),
      numLabels: this.classifier.getNumLabels(),
      useKeywordFallback: this.useKeywordFallback
    };
  }
}

const service = new ClassificationService();

module.exports = service;
module.exports.ClassificationService = ClassificationService;
