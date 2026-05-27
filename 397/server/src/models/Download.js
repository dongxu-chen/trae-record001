const mongoose = require('mongoose');

const downloadSchema = new mongoose.Schema({
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
  downloadedAt: {
    type: Date,
    default: Date.now
  }
});

downloadSchema.index({ templateId: 1 });
downloadSchema.index({ userId: 1 });
downloadSchema.index({ downloadedAt: -1 });
downloadSchema.index({ templateId: 1, userId: 1 }, { unique: true });

module.exports = mongoose.model('Download', downloadSchema);
