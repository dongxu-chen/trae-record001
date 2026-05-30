const mongoose = require('mongoose');

const documentSchema = new mongoose.Schema({
  taskId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Task',
    required: true
  },
  text: {
    type: String,
    required: true
  },
  meta: {
    source: String,
    timestamp: Date,
    author: String
  },
  status: {
    type: String,
    enum: ['pending', 'annotated', 'reviewed', 'skipped'],
    default: 'pending'
  },
  isPreAnnotated: {
    type: Boolean,
    default: false
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

module.exports = mongoose.model('Document', documentSchema);
