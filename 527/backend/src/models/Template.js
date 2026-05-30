const mongoose = require('mongoose');

const templateSchema = new mongoose.Schema({
  name: {
    type: String,
    required: true,
    trim: true
  },
  description: {
    type: String,
    trim: true
  },
  category: {
    type: String,
    enum: ['entity', 'relation', 'event', 'composite'],
    required: true
  },
  taskId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Task',
    default: null
  },
  isGlobal: {
    type: Boolean,
    default: false
  },
  entities: [{
    label: String,
    color: String,
    description: String,
    examples: [String]
  }],
  relations: [{
    label: String,
    color: String,
    sourceLabel: String,
    targetLabel: String,
    description: String
  }],
  events: [{
    label: String,
    color: String,
    description: String,
    roleTypes: [{
      role: String,
      description: String,
      entityLabel: String
    }]
  }],
  usageCount: {
    type: Number,
    default: 0
  },
  rating: {
    type: Number,
    default: 0,
    min: 0,
    max: 5
  },
  ratingCount: {
    type: Number,
    default: 0
  },
  createdBy: {
    type: String,
    default: 'system'
  },
  createdAt: {
    type: Date,
    default: Date.now
  },
  updatedAt: {
    type: Date,
    default: Date.now
  }
});

module.exports = mongoose.model('Template', templateSchema);
