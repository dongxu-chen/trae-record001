const mongoose = require('mongoose');

const userPreferenceSchema = new mongoose.Schema({
  userId: {
    type: String,
    required: true,
    unique: true,
    index: true
  },
  aggregationEnabled: {
    type: Boolean,
    default: true
  },
  aggregationCron: {
    type: String,
    default: '0 */30 * * * *'
  },
  aggregationChannels: [{
    type: String,
    enum: ['email', 'dingtalk', 'wework', 'slack']
  }],
  aggregationCategories: [{
    type: String,
    enum: ['notification', 'approval', 'alert', 'other']
  }],
  pushEnabled: {
    type: Boolean,
    default: true
  },
  pushChannels: [{
    type: String,
    enum: ['email', 'dingtalk', 'wework', 'slack']
  }],
  soundEnabled: {
    type: Boolean,
    default: true
  },
  quietHours: {
    enabled: {
      type: Boolean,
      default: false
    },
    start: {
      type: String,
      default: '22:00'
    },
    end: {
      type: String,
      default: '08:00'
    }
  },
  categorySettings: {
    notification: {
      enabled: {
        type: Boolean,
        default: true
      },
      push: {
        type: Boolean,
        default: false
      },
      sound: {
        type: Boolean,
        default: false
      }
    },
    approval: {
      enabled: {
        type: Boolean,
        default: true
      },
      push: {
        type: Boolean,
        default: true
      },
      sound: {
        type: Boolean,
        default: true
      }
    },
    alert: {
      enabled: {
        type: Boolean,
        default: true
      },
      push: {
        type: Boolean,
        default: true
      },
      sound: {
        type: Boolean,
        default: true
      }
    },
    other: {
      enabled: {
        type: Boolean,
        default: true
      },
      push: {
        type: Boolean,
        default: false
      },
      sound: {
        type: Boolean,
        default: false
      }
    }
  },
  notificationConfig: {
    email: {
      enabled: {
        type: Boolean,
        default: false
      },
      address: {
        type: String
      }
    },
    dingtalk: {
      enabled: {
        type: Boolean,
        default: false
      },
      webhook: {
        type: String
      }
    },
    wework: {
      enabled: {
        type: Boolean,
        default: false
      },
      webhook: {
        type: String
      }
    },
    slack: {
      enabled: {
        type: Boolean,
        default: false
      },
      webhook: {
        type: String
      }
    }
  },
  autoArchiveDays: {
    type: Number,
    default: 30
  },
  displaySettings: {
    sortBy: {
      type: String,
      enum: ['createdAt', 'priority'],
      default: 'createdAt'
    },
    pageSize: {
      type: Number,
      default: 20
    }
  }
}, {
  timestamps: true
});

userPreferenceSchema.statics.getByUserId = async function(userId) {
  let pref = await this.findOne({ userId });
  if (!pref) {
    pref = await this.create({
      userId,
      aggregationChannels: ['email', 'dingtalk', 'wework', 'slack'],
      aggregationCategories: ['notification', 'approval', 'alert', 'other']
    });
  }
  return pref;
};

module.exports = mongoose.model('UserPreference', userPreferenceSchema);
