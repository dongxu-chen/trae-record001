const mongoose = require('mongoose');

const channelSchema = new mongoose.Schema({
  type: {
    type: String,
    enum: ['email', 'dingtalk', 'wework', 'slack'],
    required: true,
    index: true
  },
  name: {
    type: String,
    required: true
  },
  isEnabled: {
    type: Boolean,
    default: true,
    index: true
  },
  config: {
    type: mongoose.Schema.Types.Mixed,
    required: true
  },
  status: {
    type: String,
    enum: ['active', 'inactive', 'error'],
    default: 'inactive'
  },
  lastSync: {
    type: Date
  },
  lastError: {
    type: String
  },
  syncInterval: {
    type: Number,
    default: 60000
  },
  metadata: {
    type: mongoose.Schema.Types.Mixed,
    default: {}
  }
}, {
  timestamps: true
});

channelSchema.index({ type: 1, isEnabled: 1 });

channelSchema.statics.getEnabledChannels = async function() {
  return this.find({ isEnabled: true, status: { $ne: 'error' } });
};

channelSchema.statics.getByType = async function(type) {
  return this.findOne({ type, isEnabled: true });
};

module.exports = mongoose.model('Channel', channelSchema);
