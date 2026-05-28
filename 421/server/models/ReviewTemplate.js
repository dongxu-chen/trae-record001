const mongoose = require('mongoose');

const reviewTemplateSchema = new mongoose.Schema({
  name: {
    type: String,
    required: true,
    trim: true
  },
  description: {
    type: String,
    default: ''
  },
  category: {
    type: String,
    enum: ['general', 'technical', 'legal', 'academic', 'business', 'marketing', 'custom'],
    default: 'general'
  },
  author: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  isDefault: {
    type: Boolean,
    default: false
  },
  isPublic: {
    type: Boolean,
    default: false
  },
  rules: [{
    id: {
      type: String,
      required: true
    },
    name: {
      type: String,
      required: true
    },
    description: {
      type: String,
      required: true
    },
    category: {
      type: String,
      enum: ['spelling', 'grammar', 'punctuation', 'style', 'clarity', 'format', 'consistency', 'terminology', 'custom'],
      default: 'custom'
    },
    severity: {
      type: String,
      enum: ['low', 'medium', 'high', 'critical'],
      default: 'medium'
    },
    pattern: {
      type: String
    },
    patternType: {
      type: String,
      enum: ['regex', 'keyword', 'custom'],
      default: 'keyword'
    },
    suggestedFix: {
      type: String
    },
    enabled: {
      type: Boolean,
      default: true
    },
    priority: {
      type: Number,
      default: 0
    }
  }],
  checkpoints: [{
    id: {
      type: String,
      required: true
    },
    name: {
      type: String,
      required: true
    },
    description: {
      type: String
    },
    required: {
      type: Boolean,
      default: false
    },
    examples: {
      type: [String],
      default: []
    }
  }],
  settings: {
    autoCheck: {
      type: Boolean,
      default: true
    },
    checkOnSubmit: {
      type: Boolean,
      default: true
    },
    requireAllCheckpoints: {
      type: Boolean,
      default: false
    },
    maxSuggestions: {
      type: Number,
      default: 50
    },
    minConfidence: {
      type: Number,
      default: 0.5,
      min: 0,
      max: 1
    }
  },
  usageCount: {
    type: Number,
    default: 0
  },
  lastUsedAt: {
    type: Date
  }
}, {
  timestamps: true
});

reviewTemplateSchema.index({ author: 1, createdAt: -1 });
reviewTemplateSchema.index({ category: 1, isPublic: 1 });

module.exports = mongoose.model('ReviewTemplate', reviewTemplateSchema);
