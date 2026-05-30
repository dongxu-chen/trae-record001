const mongoose = require('mongoose');

const achievementDefinitionSchema = new mongoose.Schema({
  id: {
    type: String,
    required: true,
    unique: true
  },
  name: {
    type: String,
    required: true
  },
  description: {
    type: String,
    required: true
  },
  category: {
    type: String,
    enum: ['annotation', 'quality', 'speed', 'streak', 'special'],
    required: true
  },
  icon: {
    type: String,
    default: '🏆'
  },
  points: {
    type: Number,
    default: 10
  },
  requirement: {
    type: {
      type: String,
      enum: ['annotations', 'entities', 'relations', 'consistency', 'streak', 'templates_used', 'accuracy'],
      required: true
    },
    value: {
      type: Number,
      required: true
    },
    taskId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Task',
      default: null
    }
  },
  isGlobal: {
    type: Boolean,
    default: true
  },
  rarity: {
    type: String,
    enum: ['common', 'rare', 'epic', 'legendary'],
    default: 'common'
  },
  createdAt: {
    type: Date,
    default: Date.now
  }
});

const userAchievementSchema = new mongoose.Schema({
  achievementId: {
    type: String,
    required: true
  },
  annotator: {
    type: String,
    required: true
  },
  taskId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Task'
  },
  progress: {
    type: Number,
    default: 0
  },
  unlocked: {
    type: Boolean,
    default: false
  },
  unlockedAt: {
    type: Date
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

userAchievementSchema.index({ annotator: 1, achievementId: 1, taskId: 1 }, { unique: true });

const leaderboardSchema = new mongoose.Schema({
  taskId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Task',
    required: true
  },
  period: {
    type: String,
    enum: ['daily', 'weekly', 'monthly', 'all_time'],
    required: true
  },
  rankings: [{
    annotator: String,
    score: Number,
    annotations: Number,
    accuracy: Number,
    rank: Number,
    previousRank: Number
  }],
  startDate: {
    type: Date,
    required: true
  },
  endDate: {
    type: Date,
    required: true
  },
  createdAt: {
    type: Date,
    default: Date.now
  }
});

leaderboardSchema.index({ taskId: 1, period: 1 }, { unique: true });

const AchievementDefinition = mongoose.model('AchievementDefinition', achievementDefinitionSchema);
const UserAchievement = mongoose.model('UserAchievement', userAchievementSchema);
const Leaderboard = mongoose.model('Leaderboard', leaderboardSchema);

module.exports = {
  AchievementDefinition,
  UserAchievement,
  Leaderboard
};
