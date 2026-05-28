const mongoose = require('mongoose');

const revisionSchema = new mongoose.Schema({
  document: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Document',
    required: true
  },
  author: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  version: {
    type: Number,
    required: true
  },
  operations: [{
    type: Object,
    required: true
  }],
  diff: {
    type: String,
    required: true
  },
  richDiff: {
    type: String
  },
  sideBySideDiff: {
    type: String
  },
  contentBefore: {
    type: String,
    required: true
  },
  contentAfter: {
    type: String,
    required: true
  },
  richContentBefore: {
    type: Object
  },
  richContentAfter: {
    type: Object
  },
  status: {
    type: String,
    enum: ['pending', 'approved', 'rejected', 'applied'],
    default: 'pending'
  },
  reviewedBy: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User'
  },
  reviewedAt: {
    type: Date
  },
  reviewComment: {
    type: String
  }
}, {
  timestamps: true
});

module.exports = mongoose.model('Revision', revisionSchema);
