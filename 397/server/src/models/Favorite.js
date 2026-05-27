const mongoose = require('mongoose');

const favoriteSchema = new mongoose.Schema({
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
  createdAt: {
    type: Date,
    default: Date.now
  }
});

favoriteSchema.index({ userId: 1, templateId: 1 }, { unique: true });

module.exports = mongoose.model('Favorite', favoriteSchema);
