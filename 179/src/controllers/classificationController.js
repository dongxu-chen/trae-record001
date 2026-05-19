const Joi = require('joi');
const classificationService = require('../services/ClassificationService');
const synonymService = require('../services/SynonymService');
const logger = require('../utils/logger');

const classifySchema = Joi.object({
  title: Joi.string().required(),
  content: Joi.string().required()
});

const addSynonymSchema = Joi.object({
  word: Joi.string().required(),
  synonym: Joi.string().required(),
  category: Joi.string().valid('approval', 'alert', 'notification', 'general').default('general')
});

exports.classify = async (req, res) => {
  try {
    const { error, value } = classifySchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const result = await classificationService.classify(value);

    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    logger.error('Classify error:', error);
    res.status(500).json({ error: 'Failed to classify message' });
  }
};

exports.getClassificationKeywords = async (req, res) => {
  try {
    const keywords = classificationService.getCategoryKeywords();

    res.json({
      success: true,
      data: keywords
    });
  } catch (error) {
    logger.error('Get classification keywords error:', error);
    res.status(500).json({ error: 'Failed to get classification keywords' });
  }
};

exports.addClassificationKeyword = async (req, res) => {
  try {
    const { category, keyword } = req.body;

    if (!category || !keyword) {
      return res.status(400).json({ error: 'Category and keyword are required' });
    }

    classificationService.addCategoryKeyword(category, keyword);

    res.json({
      success: true,
      message: `Keyword '${keyword}' added to category '${category}'`
    });
  } catch (error) {
    logger.error('Add classification keyword error:', error);
    res.status(500).json({ error: 'Failed to add classification keyword' });
  }
};

exports.removeClassificationKeyword = async (req, res) => {
  try {
    const { category, keyword } = req.body;

    if (!category || !keyword) {
      return res.status(400).json({ error: 'Category and keyword are required' });
    }

    classificationService.removeCategoryKeyword(category, keyword);

    res.json({
      success: true,
      message: `Keyword '${keyword}' removed from category '${category}'`
    });
  } catch (error) {
    logger.error('Remove classification keyword error:', error);
    res.status(500).json({ error: 'Failed to remove classification keyword' });
  }
};

exports.getSynonyms = async (req, res) => {
  try {
    const synonyms = synonymService.getSynonymMap();

    res.json({
      success: true,
      data: synonyms
    });
  } catch (error) {
    logger.error('Get synonyms error:', error);
    res.status(500).json({ error: 'Failed to get synonyms' });
  }
};

exports.addSynonym = async (req, res) => {
  try {
    const { error, value } = addSynonymSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    synonymService.addSynonym(value.word, value.synonym, value.category);

    res.json({
      success: true,
      message: `Synonym '${value.synonym}' added for word '${value.word}'`
    });
  } catch (error) {
    logger.error('Add synonym error:', error);
    res.status(500).json({ error: 'Failed to add synonym' });
  }
};

exports.getWordSynonyms = async (req, res) => {
  try {
    const { word } = req.params;

    if (!word) {
      return res.status(400).json({ error: 'Word is required' });
    }

    const synonyms = synonymService.getSynonyms(word);

    res.json({
      success: true,
      data: {
        word,
        synonyms
      }
    });
  } catch (error) {
    logger.error('Get word synonyms error:', error);
    res.status(500).json({ error: 'Failed to get word synonyms' });
  }
};

exports.getModelInfo = async (req, res) => {
  try {
    const info = classificationService.getModelInfo();

    res.json({
      success: true,
      data: info
    });
  } catch (error) {
    logger.error('Get model info error:', error);
    res.status(500).json({ error: 'Failed to get model info' });
  }
};

exports.reloadSynonyms = async (req, res) => {
  try {
    synonymService.isLoaded = false;
    await synonymService.loadSynonyms();

    res.json({
      success: true,
      message: 'Synonyms reloaded successfully'
    });
  } catch (error) {
    logger.error('Reload synonyms error:', error);
    res.status(500).json({ error: 'Failed to reload synonyms' });
  }
};
