const fs = require('fs');
const path = require('path');
const logger = require('../utils/logger');

class TemplateParserService {
  constructor() {
    this.templates = [];
    this.defaultTemplate = null;
    this.templatePath = path.join(__dirname, '../data/message_templates.json');
    this.loadTemplates();
  }

  loadTemplates() {
    try {
      if (fs.existsSync(this.templatePath)) {
        const data = JSON.parse(fs.readFileSync(this.templatePath, 'utf-8'));
        this.templates = data.templates || [];
        this.defaultTemplate = data.defaultTemplate || null;
        logger.info(`Loaded ${this.templates.length} message templates`);
      } else {
        logger.warn(`Template file not found: ${this.templatePath}`);
        this.templates = [];
        this.defaultTemplate = {
          name: 'default',
          displayName: '通用消息',
          category: 'notification',
          icon: 'message-square',
          color: '#6b7280',
          priority: 'low',
          cardLayout: [],
          actionButtons: []
        };
      }
    } catch (error) {
      logger.error('Failed to load templates:', error);
      this.templates = [];
      this.defaultTemplate = {
        name: 'default',
        displayName: '通用消息',
        category: 'notification',
        icon: 'message-square',
        color: '#6b7280',
        priority: 'low',
        cardLayout: [],
        actionButtons: []
      };
    }
  }

  matchTemplate(message) {
    const text = `${message.title || ''} ${message.content || ''}`;
    
    let bestMatch = null;
    let bestScore = 0;

    for (const template of this.templates) {
      let matchCount = 0;
      for (const pattern of template.matchPatterns) {
        if (text.includes(pattern)) {
          matchCount++;
        }
      }

      if (matchCount > 0) {
        const score = matchCount / template.matchPatterns.length;
        if (score > bestScore) {
          bestScore = score;
          bestMatch = template;
        }
      }
    }

    if (bestMatch && bestScore >= 0.3) {
      return {
        template: bestMatch,
        matchScore: bestScore,
        matched: true
      };
    }

    return {
      template: this.defaultTemplate,
      matchScore: 0,
      matched: false
    };
  }

  extractFields(text, extractRules) {
    const fields = {};
    const errors = [];

    for (const [fieldName, rule] of Object.entries(extractRules)) {
      try {
        const pattern = new RegExp(rule.pattern, 'i');
        const match = text.match(pattern);

        if (match && match[1]) {
          let value = match[1].trim();
          
          value = this.convertType(value, rule.type);
          
          if (rule.mapping && rule.mapping[value]) {
            value = rule.mapping[value];
          }

          fields[fieldName] = value;
        }
      } catch (error) {
        errors.push(`Field ${fieldName}: ${error.message}`);
      }
    }

    return {
      fields,
      errors,
      extractedCount: Object.keys(fields).length,
      totalFields: Object.keys(extractRules).length
    };
  }

  convertType(value, type) {
    if (!value) return value;

    switch (type) {
      case 'number':
        const num = parseFloat(value.replace(/,/g, ''));
        return isNaN(num) ? value : num;

      case 'date':
        try {
          const date = new Date(value);
          return isNaN(date.getTime()) ? value : date.toISOString();
        } catch {
          return value;
        }

      case 'currency':
        const currencyNum = parseFloat(value.replace(/[,\s￥¥$€£]/g, ''));
        return isNaN(currencyNum) ? value : currencyNum;

      case 'boolean':
        return /^(true|yes|是|对)$/i.test(value);

      default:
        return value;
    }
  }

  generateCard(message, template, extractedFields) {
    const cardData = {
      templateName: template.name,
      displayName: template.displayName,
      category: template.category,
      icon: template.icon,
      color: template.color,
      priority: template.priority,
      title: message.title || extractedFields.title || this.extractTitle(message),
      summary: extractedFields.summary || message.summary || '',
      fields: [],
      actionButtons: template.actionButtons || [],
      matchScore: template.matchScore || 0
    };

    for (const layoutItem of template.cardLayout) {
      if (!layoutItem.showInCard) continue;

      const value = extractedFields[layoutItem.key] || message[layoutItem.key];
      
      if (value !== undefined && value !== null && value !== '') {
        cardData.fields.push({
          key: layoutItem.key,
          label: layoutItem.label,
          value: value,
          highlight: layoutItem.highlight || false
        });
      }
    }

    return cardData;
  }

  extractTitle(message) {
    if (message.title) return message.title;
    
    const content = message.content || '';
    const firstLine = content.split(/[。！？!\n]/)[0];
    return firstLine.substring(0, 50) + (firstLine.length > 50 ? '...' : '');
  }

  async parseMessage(message) {
    const text = `${message.title || ''}\n${message.content || ''}`;
    
    const { template, matchScore, matched } = this.matchTemplate(message);
    const templateWithScore = { ...template, matchScore };

    let extractionResult = { fields: {}, errors: [], extractedCount: 0, totalFields: 0 };
    
    if (matched && template.extractRules) {
      extractionResult = this.extractFields(text, template.extractRules);
    }

    const card = this.generateCard(message, templateWithScore, extractionResult.fields);

    return {
      template: template.name,
      templateDisplayName: template.displayName,
      matched,
      matchScore,
      extractedFields: extractionResult.fields,
      extractionErrors: extractionResult.errors,
      extractedCount: extractionResult.extractedCount,
      totalFields: extractionResult.totalFields,
      card,
      structuredData: {
        ...extractionResult.fields,
        _template: template.name,
        _category: template.category,
        _priority: template.priority
      }
    };
  }

  async batchParse(messages) {
    const results = [];
    
    for (const msg of messages) {
      try {
        const result = await this.parseMessage(msg);
        results.push({
          messageId: msg.messageId,
          ...result
        });
      } catch (error) {
        logger.error(`Failed to parse message ${msg.messageId}:`, error);
        results.push({
          messageId: msg.messageId,
          template: 'default',
          matched: false,
          matchScore: 0,
          error: error.message
        });
      }
    }

    return results;
  }

  getTemplates() {
    return this.templates.map(t => ({
      name: t.name,
      displayName: t.displayName,
      category: t.category,
      icon: t.icon,
      color: t.color,
      priority: t.priority,
      matchPatterns: t.matchPatterns,
      fieldCount: Object.keys(t.extractRules || {}).length,
      actionCount: (t.actionButtons || []).length
    }));
  }

  getTemplateByName(name) {
    return this.templates.find(t => t.name === name) || this.defaultTemplate;
  }

  addTemplate(template) {
    if (!template.name || !template.matchPatterns) {
      throw new Error('Template name and matchPatterns are required');
    }
    
    const existingIndex = this.templates.findIndex(t => t.name === template.name);
    if (existingIndex >= 0) {
      this.templates[existingIndex] = template;
    } else {
      this.templates.push(template);
    }
    
    this.saveTemplates();
    logger.info(`Template ${template.name} added/updated`);
  }

  removeTemplate(name) {
    const index = this.templates.findIndex(t => t.name === name);
    if (index >= 0) {
      this.templates.splice(index, 1);
      this.saveTemplates();
      logger.info(`Template ${name} removed`);
      return true;
    }
    return false;
  }

  saveTemplates() {
    try {
      const data = {
        templates: this.templates,
        defaultTemplate: this.defaultTemplate
      };
      fs.writeFileSync(this.templatePath, JSON.stringify(data, null, 2), 'utf-8');
    } catch (error) {
      logger.error('Failed to save templates:', error);
      throw error;
    }
  }

  reloadTemplates() {
    this.loadTemplates();
  }

  testTemplate(templateName, text) {
    const template = this.getTemplateByName(templateName);
    if (!template || !template.extractRules) {
      return { success: false, error: 'Template not found or has no extract rules' };
    }

    const result = this.extractFields(text, template.extractRules);
    const card = this.generateCard({ content: text, title: '' }, template, result.fields);

    return {
      success: true,
      template: template.name,
      extractedFields: result.fields,
      errors: result.errors,
      card
    };
  }
}

module.exports = new TemplateParserService();
module.exports.TemplateParserService = TemplateParserService;
