const messageService = require('../services/MessageService');
const summaryService = require('../services/SummaryService');
const templateParserService = require('../services/TemplateParserService');
const logger = require('../utils/logger');

exports.getPinnedMessages = async (req, res) => {
  try {
    const { page = 1, pageSize = 20, category, isRead } = req.query;
    
    const filters = {};
    if (category) filters.category = category;
    if (isRead !== undefined) filters.isRead = isRead === 'true';
    
    const result = await messageService.getPinnedMessages(filters, {
      page: parseInt(page),
      pageSize: parseInt(pageSize)
    });
    
    res.json({
      success: true,
      ...result
    });
  } catch (error) {
    logger.error('Get pinned messages error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.pinMessage = async (req, res) => {
  try {
    const { messageId } = req.params;
    const message = await messageService.pinMessage(messageId);
    
    res.json({
      success: true,
      message: 'Message pinned successfully',
      data: message
    });
  } catch (error) {
    logger.error('Pin message error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.unpinMessage = async (req, res) => {
  try {
    const { messageId } = req.params;
    const message = await messageService.unpinMessage(messageId);
    
    res.json({
      success: true,
      message: 'Message unpinned successfully',
      data: message
    });
  } catch (error) {
    logger.error('Unpin message error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.getReminderMessages = async (req, res) => {
  try {
    const { category, priority } = req.query;
    const filters = {};
    if (category) filters['reminder.category'] = category;
    if (priority) filters['reminder.priority'] = priority;
    
    const result = await messageService.getReminderMessages(filters);
    
    res.json({
      success: true,
      ...result
    });
  } catch (error) {
    logger.error('Get reminder messages error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.getReminderStats = async (req, res) => {
  try {
    const stats = await messageService.getReminderStats();
    
    res.json({
      success: true,
      data: stats
    });
  } catch (error) {
    logger.error('Get reminder stats error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.generateSummary = async (req, res) => {
  try {
    const { text, maxLength } = req.body;
    
    if (!text) {
      return res.status(400).json({
        success: false,
        error: 'Text is required'
      });
    }
    
    const result = await summaryService.summarizeText(text, maxLength);
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    logger.error('Generate summary error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.regenerateMessageSummary = async (req, res) => {
  try {
    const { messageId } = req.params;
    const message = await messageService.regenerateSummary(messageId);
    
    res.json({
      success: true,
      message: 'Summary regenerated successfully',
      data: {
        summary: message.summary,
        summaryInfo: message.summaryInfo
      }
    });
  } catch (error) {
    logger.error('Regenerate message summary error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.regenerateAllSummaries = async (req, res) => {
  try {
    const { category } = req.query;
    const filters = {};
    if (category) filters.category = category;
    
    const result = await messageService.regenerateAllSummaries(filters);
    
    res.json({
      success: true,
      message: 'Summaries regeneration completed',
      data: result
    });
  } catch (error) {
    logger.error('Regenerate all summaries error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.parseTemplate = async (req, res) => {
  try {
    const { text, templateName } = req.body;
    
    if (!text) {
      return res.status(400).json({
        success: false,
        error: 'Text is required'
      });
    }
    
    let result;
    if (templateName) {
      result = templateParserService.testTemplate(templateName, text);
    } else {
      result = await templateParserService.parseMessage({ content: text, title: '' });
    }
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    logger.error('Parse template error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.reparseMessageTemplate = async (req, res) => {
  try {
    const { messageId } = req.params;
    const message = await messageService.reparseTemplate(messageId);
    
    res.json({
      success: true,
      message: 'Template reparsed successfully',
      data: {
        template: message.template,
        card: message.card,
        structuredData: message.structuredData
      }
    });
  } catch (error) {
    logger.error('Reparse message template error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.reparseAllTemplates = async (req, res) => {
  try {
    const { category } = req.query;
    const filters = {};
    if (category) filters.category = category;
    
    const result = await messageService.reparseAllTemplates(filters);
    
    res.json({
      success: true,
      message: 'Templates reparsing completed',
      data: result
    });
  } catch (error) {
    logger.error('Reparse all templates error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.getTemplates = async (req, res) => {
  try {
    const templates = templateParserService.getTemplates();
    
    res.json({
      success: true,
      data: templates
    });
  } catch (error) {
    logger.error('Get templates error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.getTemplateByName = async (req, res) => {
  try {
    const { templateName } = req.params;
    const template = templateParserService.getTemplateByName(templateName);
    
    if (!template) {
      return res.status(404).json({
        success: false,
        error: 'Template not found'
      });
    }
    
    res.json({
      success: true,
      data: template
    });
  } catch (error) {
    logger.error('Get template by name error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.addTemplate = async (req, res) => {
  try {
    const template = req.body;
    
    if (!template.name || !template.matchPatterns) {
      return res.status(400).json({
        success: false,
        error: 'Template name and matchPatterns are required'
      });
    }
    
    templateParserService.addTemplate(template);
    
    res.json({
      success: true,
      message: 'Template added successfully',
      data: template
    });
  } catch (error) {
    logger.error('Add template error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.removeTemplate = async (req, res) => {
  try {
    const { templateName } = req.params;
    const removed = templateParserService.removeTemplate(templateName);
    
    if (!removed) {
      return res.status(404).json({
        success: false,
        error: 'Template not found'
      });
    }
    
    res.json({
      success: true,
      message: 'Template removed successfully'
    });
  } catch (error) {
    logger.error('Remove template error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.reloadTemplates = async (req, res) => {
  try {
    templateParserService.reloadTemplates();
    
    res.json({
      success: true,
      message: 'Templates reloaded successfully'
    });
  } catch (error) {
    logger.error('Reload templates error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.getMessagesByTemplate = async (req, res) => {
  try {
    const { templateName } = req.params;
    const { page = 1, pageSize = 20, isRead } = req.query;
    
    const filters = {};
    if (isRead !== undefined) filters.isRead = isRead === 'true';
    
    const result = await messageService.getByTemplate(templateName, filters, {
      page: parseInt(page),
      pageSize: parseInt(pageSize)
    });
    
    res.json({
      success: true,
      ...result
    });
  } catch (error) {
    logger.error('Get messages by template error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.getMessageCard = async (req, res) => {
  try {
    const { messageId } = req.params;
    const card = await messageService.getCard(messageId);
    
    if (!card) {
      return res.status(404).json({
        success: false,
        error: 'Card not found'
      });
    }
    
    res.json({
      success: true,
      data: card
    });
  } catch (error) {
    logger.error('Get message card error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.getStructuredData = async (req, res) => {
  try {
    const { messageId } = req.params;
    const structuredData = await messageService.getStructuredData(messageId);
    
    res.json({
      success: true,
      data: structuredData
    });
  } catch (error) {
    logger.error('Get structured data error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.reanalyzeReminder = async (req, res) => {
  try {
    const { messageId } = req.params;
    const message = await messageService.reanalyzeReminder(messageId);
    
    res.json({
      success: true,
      message: 'Reminder reanalyzed successfully',
      data: {
        reminder: message.reminder,
        isPinned: message.isPinned
      }
    });
  } catch (error) {
    logger.error('Reanalyze reminder error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.batchGenerateSummaries = async (req, res) => {
  try {
    const { messages, maxLength } = req.body;
    
    if (!messages || !Array.isArray(messages)) {
      return res.status(400).json({
        success: false,
        error: 'Messages array is required'
      });
    }
    
    const results = await summaryService.summarizeBatch(messages, maxLength);
    
    res.json({
      success: true,
      data: results
    });
  } catch (error) {
    logger.error('Batch generate summaries error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

exports.batchParseTemplates = async (req, res) => {
  try {
    const { messages } = req.body;
    
    if (!messages || !Array.isArray(messages)) {
      return res.status(400).json({
        success: false,
        error: 'Messages array is required'
      });
    }
    
    const results = await templateParserService.batchParse(messages);
    
    res.json({
      success: true,
      data: results
    });
  } catch (error) {
    logger.error('Batch parse templates error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};
