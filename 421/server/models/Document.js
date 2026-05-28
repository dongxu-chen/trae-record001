const mongoose = require('mongoose');

const documentSchema = new mongoose.Schema({
  title: {
    type: String,
    required: true,
    trim: true
  },
  content: {
    type: String,
    default: ''
  },
  richContent: {
    type: Object,
    default: null
  },
  docId: {
    type: String,
    required: true,
    unique: true
  },
  author: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  collaborators: [{
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User'
  }],
  reviewers: [{
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User'
  }],
  status: {
    type: String,
    enum: ['draft', 'in_review', 'approved', 'rejected'],
    default: 'draft'
  },
  version: {
    type: Number,
    default: 1
  },
  currentRevision: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Revision'
  }
}, {
  timestamps: true
});

module.exports = mongoose.model('Document', documentSchema);
