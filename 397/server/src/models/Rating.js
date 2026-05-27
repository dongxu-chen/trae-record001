const mongoose = require('mongoose');

const ratingSchema = new mongoose.Schema({
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
  rating: {
    type: Number,
    required: true,
    min: 1,
    max: 5
  },
  createdAt: {
    type: Date,
    default: Date.now
  }
});

ratingSchema.index({ templateId: 1, userId: 1 }, { unique: true });

module.exports = mongoose.model('Rating', ratingSchema);
