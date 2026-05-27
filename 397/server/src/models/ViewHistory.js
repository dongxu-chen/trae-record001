const mongoose = require('mongoose');

const viewHistorySchema = new mongoose.Schema({
  templateId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Template',
    required: true
  },
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  viewedAt: {
    type: Date,
    default: Date.now
  },
  duration: {
    type: Number,
    default: 0
  }
});

viewHistorySchema.index({ templateId: 1, userId: 1 });
viewHistorySchema.index({ userId: 1, viewedAt: -1 });

module.exports = mongoose.model('ViewHistory', viewHistorySchema);
