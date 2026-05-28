const mongoose = require('mongoose');

const aiSuggestionSchema = new mongoose.Schema({
  document: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Document',
    required: true
  },
  revision: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Revision'
  },
  author: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  type: {
    type: String,
    enum: ['typo', 'grammar', 'style', 'clarity', 'format', 'consistency'],
    required: true
  },
  severity: {
    type: String,
    enum: ['low', 'medium', 'high', 'critical'],
    default: 'medium'
  },
  category: {
    type: String,
    enum: [
      'spelling',
      'grammar',
      'punctuation',
      'capitalization',
      'word_choice',
      'sentence_structure',
      'style',
      'clarity',
      'formatting',
      'terminology'
    ],
    required: true
  },
  originalText: {
    type: String,
    required: true
  },
  suggestedText: {
    type: String
  },
  explanation: {
    type: String,
    required: true
  },
  context: {
    type: String
  },
  startPos: {
    type: Number
  },
  endPos: {
    type: Number
  },
  status: {
    type: String,
    enum: ['pending', 'accepted', 'rejected', 'ignored'],
    default: 'pending'
  },
  resolvedBy: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User'
  },
  resolvedAt: {
    type: Date
  },
  ruleId: {
    type: String
  },
  confidence: {
    type: Number,
    min: 0,
    max: 1
  },
  metadata: {
    type: Object
  }
}, {
  timestamps: true
});

aiSuggestionSchema.index({ document: 1, status: 1 });
aiSuggestionSchema.index({ document: 1, type: 1 });
aiSuggestionSchema.index({ author: 1, createdAt: -1 });

module.exports = mongoose.model('AISuggestion', aiSuggestionSchema);
