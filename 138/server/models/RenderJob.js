const mongoose = require('mongoose');

const renderJobSchema = new mongoose.Schema({
  modelId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Model',
    required: true
  },
  name: String,
  status: {
    type: String,
    enum: ['pending', 'processing', 'completed', 'failed'],
    default: 'pending'
  },
  settings: {
    width: Number,
    height: Number,
    samples: Number,
    engine: String,
    cameraAngle: { x: Number, y: Number, z: Number }
  },
  outputPath: String,
  createdAt: {
    type: Date,
    default: Date.now
  },
  completedAt: Date
});

module.exports = mongoose.model('RenderJob', renderJobSchema);
