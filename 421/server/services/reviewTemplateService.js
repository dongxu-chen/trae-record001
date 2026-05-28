const ReviewTemplate = require('../models/ReviewTemplate');
const AISuggestion = require('../models/AISuggestion');
const aiAuditService = require('./aiAuditService');

class ReviewTemplateService {
  async getTemplates(userId, options = {}) {
    const query = {
      $or: [
        { author: userId },
        { isPublic: true }
      ]
    };

    if (options.category) {
      query.category = options.category;
    }

    const templates = await ReviewTemplate.find(query)
      .populate('author', 'username')
      .sort({ isDefault: -1, usageCount: -1, createdAt: -1 });

    return templates;
  }

  async getTemplate(templateId, userId) {
    const template = await ReviewTemplate.findOne({
      _id: templateId,
      $or: [
        { author: userId },
        { isPublic: true }
      ]
    }).populate('author', 'username');

    if (!template) {
      throw new Error('Template not found');
    }

    return template;
  }

  async createTemplate(userId, templateData) {
    const template = new ReviewTemplate({
      ...templateData,
      author: userId
    });

    await template.save();
    await template.populate('author', 'username');

    return template;
  }

  async updateTemplate(templateId, userId, updates) {
    const template = await ReviewTemplate.findOne({
      _id: templateId,
      author: userId
    });

    if (!template) {
      throw new Error('Template not found or not authorized');
    }

    Object.assign(template, updates);
    await template.save();
    await template.populate('author', 'username');

    return template;
  }

  async deleteTemplate(templateId, userId) {
    const template = await ReviewTemplate.findOne({
      _id: templateId,
      author: userId
    });

    if (!template) {
      throw new Error('Template not found or not authorized');
    }

    if (template.isDefault) {
      throw new Error('Cannot delete default template');
    }

    await ReviewTemplate.findByIdAndDelete(templateId);
  }

  async duplicateTemplate(templateId, userId) {
    const original = await this.getTemplate(templateId, userId);
    
    const duplicate = new ReviewTemplate({
      name: `${original.name} (副本)`,
      description: original.description,
      category: original.category,
      author: userId,
      isDefault: false,
      isPublic: false,
      rules: original.rules.map(rule => ({ ...rule })),
      checkpoints: original.checkpoints.map(cp => ({ ...cp })),
      settings: { ...original.settings }
    });

    await duplicate.save();
    await duplicate.populate('author', 'username');

    return duplicate;
  }

  async applyTemplate(templateId, documentId, content, userId) {
    const template = await this.getTemplate(templateId, userId);
    
    template.usageCount++;
    template.lastUsedAt = new Date();
    await template.save();

    const enabledRules = template.rules.filter(rule => rule.enabled);
    const allSuggestions = [];

    for (const rule of enabledRules) {
      const suggestions = this.checkRule(rule, content);
      allSuggestions.push(...suggestions.map(s => ({
        ...s,
        document: documentId,
        author: userId,
        ruleId: rule.id
      })));
    }

    const aiSuggestions = await aiAuditService.analyzeText(content, {
      limit: template.settings.maxSuggestions,
      detectFormat: true
    });

    const filteredAISuggestions = aiSuggestions.filter(
      s => s.confidence >= template.settings.minConfidence
    );

    allSuggestions.push(...filteredAISuggestions.map(s => ({
      ...s,
      document: documentId,
      author: userId
    })));

    const savedSuggestions = await AISuggestion.insertMany(allSuggestions);

    const checkpoints = template.checkpoints.map(cp => ({
      ...cp,
      status: 'pending'
    }));

    return {
      suggestions: savedSuggestions,
      checkpoints,
      summary: {
        total: allSuggestions.length,
        byType: this.groupBy(allSuggestions, 'type'),
        bySeverity: this.groupBy(allSuggestions, 'severity'),
        byCategory: this.groupBy(allSuggestions, 'category')
      }
    };
  }

  checkRule(rule, text) {
    const suggestions = [];
    
    if (!rule.pattern) return suggestions;

    try {
      let regex;
      if (rule.patternType === 'regex') {
        regex = new RegExp(rule.pattern, 'gi');
      } else {
        regex = new RegExp(rule.pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
      }

      let match;
      while ((match = regex.exec(text)) !== null) {
        suggestions.push({
          type: rule.category === 'custom' ? 'style' : rule.category,
          category: rule.category,
          severity: rule.severity,
          originalText: match[0],
          suggestedText: rule.suggestedFix,
          explanation: rule.description,
          startPos: match.index,
          endPos: match.index + match[0].length,
          confidence: 0.8
        });
      }
    } catch (e) {
      console.error('Rule check error:', rule.id, e.message);
    }

    return suggestions;
  }

  groupBy(items, key) {
    return items.reduce((acc, item) => {
      acc[item[key]] = (acc[item[key]] || 0) + 1;
      return acc;
    }, {});
  }

  async getDefaultTemplates() {
    return ReviewTemplate.find({ isDefault: true })
      .populate('author', 'username')
      .sort({ category: 1, name: 1 });
  }

  async createDefaultTemplates(userId) {
    const existingDefaults = await ReviewTemplate.countDocuments({ isDefault: true });
    if (existingDefaults > 0) return [];

    const defaultTemplates = [
      {
        name: '通用文档审核',
        description: '适用于大多数文档的基础审核规则',
        category: 'general',
        author: userId,
        isDefault: true,
        isPublic: true,
        rules: [
          {
            id: 'check_spelling',
            name: '拼写检查',
            description: '检查常见拼写错误',
            category: 'spelling',
            severity: 'high',
            enabled: true,
            priority: 1
          },
          {
            id: 'check_grammar',
            name: '语法检查',
            description: '检查基本语法问题',
            category: 'grammar',
            severity: 'high',
            enabled: true,
            priority: 2
          },
          {
            id: 'check_punctuation',
            name: '标点符号',
            description: '检查标点符号使用',
            category: 'punctuation',
            severity: 'medium',
            enabled: true,
            priority: 3
          }
        ],
        checkpoints: [
          {
            id: 'cp_content',
            name: '内容完整性',
            description: '文档内容是否完整',
            required: true
          },
          {
            id: 'cp_format',
            name: '格式规范',
            description: '文档格式是否规范',
            required: true
          }
        ]
      },
      {
        name: '技术文档审核',
        description: '技术文档专用审核规则',
        category: 'technical',
        author: userId,
        isDefault: true,
        isPublic: true,
        rules: [
          {
            id: 'check_terminology',
            name: '术语一致性',
            description: '检查专业术语使用是否一致',
            category: 'terminology',
            severity: 'high',
            enabled: true,
            priority: 1
          },
          {
            id: 'check_code_format',
            name: '代码格式',
            description: '检查代码块格式是否正确',
            category: 'format',
            severity: 'medium',
            enabled: true,
            priority: 2
          }
        ],
        checkpoints: [
          {
            id: 'cp_accuracy',
            name: '技术准确性',
            description: '技术内容是否准确',
            required: true
          },
          {
            id: 'cp_terminology',
            name: '术语规范',
            description: '术语使用是否规范',
            required: true
          }
        ]
      },
      {
        name: '法律文档审核',
        description: '法律文档专用审核规则',
        category: 'legal',
        author: userId,
        isDefault: true,
        isPublic: true,
        rules: [
          {
            id: 'check_legal_terms',
            name: '法律术语',
            description: '检查法律术语使用',
            category: 'terminology',
            severity: 'critical',
            enabled: true,
            priority: 1
          }
        ],
        checkpoints: [
          {
            id: 'cp_legal',
            name: '法律合规性',
            description: '文档是否符合法律要求',
            required: true
          }
        ]
      }
    ];

    const created = await ReviewTemplate.insertMany(defaultTemplates);
    return created;
  }
}

module.exports = new ReviewTemplateService();
