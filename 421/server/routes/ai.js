const express = require('express');
const { auth } = require('../middleware/auth');
const AISuggestion = require('../models/AISuggestion');
const aiAuditService = require('../services/aiAuditService');
const Document = require('../models/Document');

const router = express.Router();

router.post('/analyze', auth, async (req, res) => {
  try {
    const { documentId, content, options } = req.body;
    
    const suggestions = await aiAuditService.analyzeText(content, options || {});
    
    const savedSuggestions = await AISuggestion.insertMany(
      suggestions.map(s => ({
        ...s,
        document: documentId,
        author: req.user.id
      }))
    );

    const summary = aiAuditService.generateSummary(savedSuggestions);

    res.json({
      suggestions: savedSuggestions,
      summary
    });
  } catch (error) {
    console.error('AI analyze error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/document/:documentId', auth, async (req, res) => {
  try {
    const { status, type, category } = req.query;
    
    const document = await Document.findOne({ docId: req.params.documentId });
    if (!document) {
      return res.status(404).json({ message: 'Document not found' });
    }

    const query = { document: document._id };
    if (status) query.status = status;
    if (type) query.type = type;
    if (category) query.category = category;

    const suggestions = await AISuggestion.find(query)
      .sort({ severity: 1, createdAt: -1 })
      .limit(100);

    const summary = aiAuditService.generateSummary(suggestions);

    res.json({ suggestions, summary });
  } catch (error) {
    console.error('Get suggestions error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/:suggestionId/accept', auth, async (req, res) => {
  try {
    const suggestion = await AISuggestion.findOneAndUpdate(
      { _id: req.params.suggestionId, status: 'pending' },
      { 
        status: 'accepted',
        resolvedBy: req.user.id,
        resolvedAt: new Date()
      },
      { new: true }
    ).populate('resolvedBy', 'username');

    if (!suggestion) {
      return res.status(404).json({ message: 'Suggestion not found' });
    }

    res.json(suggestion);
  } catch (error) {
    console.error('Accept suggestion error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/:suggestionId/reject', auth, async (req, res) => {
  try {
    const suggestion = await AISuggestion.findOneAndUpdate(
      { _id: req.params.suggestionId, status: 'pending' },
      { 
        status: 'rejected',
        resolvedBy: req.user.id,
        resolvedAt: new Date()
      },
      { new: true }
    ).populate('resolvedBy', 'username');

    if (!suggestion) {
      return res.status(404).json({ message: 'Suggestion not found' });
    }

    res.json(suggestion);
  } catch (error) {
    console.error('Reject suggestion error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/:suggestionId/ignore', auth, async (req, res) => {
  try {
    const suggestion = await AISuggestion.findOneAndUpdate(
      { _id: req.params.suggestionId, status: 'pending' },
      { 
        status: 'ignored',
        resolvedBy: req.user.id,
        resolvedAt: new Date()
      },
      { new: true }
    ).populate('resolvedBy', 'username');

    if (!suggestion) {
      return res.status(404).json({ message: 'Suggestion not found' });
    }

    res.json(suggestion);
  } catch (error) {
    console.error('Ignore suggestion error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/batch-accept', auth, async (req, res) => {
  try {
    const { suggestionIds } = req.body;
    
    const result = await AISuggestion.updateMany(
      { 
        _id: { $in: suggestionIds },
        status: 'pending'
      },
      { 
        status: 'accepted',
        resolvedBy: req.user.id,
        resolvedAt: new Date()
      }
    );

    res.json({ 
      message: `Accepted ${result.modifiedCount} suggestions`,
      modifiedCount: result.modifiedCount
    });
  } catch (error) {
    console.error('Batch accept error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/batch-ignore', auth, async (req, res) => {
  try {
    const { suggestionIds } = req.body;
    
    const result = await AISuggestion.updateMany(
      { 
        _id: { $in: suggestionIds },
        status: 'pending'
      },
      { 
        status: 'ignored',
        resolvedBy: req.user.id,
        resolvedAt: new Date()
      }
    );

    res.json({ 
      message: `Ignored ${result.modifiedCount} suggestions`,
      modifiedCount: result.modifiedCount
    });
  } catch (error) {
    console.error('Batch ignore error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

module.exports = router;
