const mongoose = require('mongoose');

const aggregationLogSchema = new mongoose.Schema({
  userId: {
    type: String,
    required: true,
    index: true
  },
  type: {
    type: String,
    enum: ['summary', 'alert', 'digest'],
    required: true
  },
  title: {
    type: String,
    required: true
  },
  content: {
    type: String,
    required: true
  },
  messageCount: {
    type: Number,
    default: 0
  },
  categories: [{
    category: String,
    count: Number
  }],
  channels: [{
    type: String,
    enum: ['email', 'dingtalk', 'wework', 'slack']
  }],
  sentAt: {
    type: Date,
    default: Date.now
  },
  status: {
    type: String,
    enum: ['sent', 'failed', 'pending'],
    default: 'pending'
  },
  error: {
    type: String
  },
  metadata: {
    type: mongoose.Schema.Types.Mixed,
    default: {}
  }
}, {
  timestamps: true
});

aggregationLogSchema.index({ userId: 1, sentAt: -1 });
aggregationLogSchema.index({ type: 1, status: 1 });

module.exports = mongoose.model('AggregationLog', aggregationLogSchema);
