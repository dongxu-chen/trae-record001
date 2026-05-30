const mongoose = require('mongoose');

const qualityScoreSchema = new mongoose.Schema({
  annotator: {
    type: String,
    required: true
  },
  taskId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Task',
    required: true
  },
  totalAnnotations: {
    type: Number,
    default: 0
  },
  entitiesAnnotated: {
    type: Number,
    default: 0
  },
  relationsAnnotated: {
    type: Number,
    default: 0
  },
  eventsAnnotated: {
    type: Number,
    default: 0
  },
  consistencyScore: {
    type: Number,
    default: 0,
    min: 0,
    max: 100
  },
  accuracyScore: {
    type: Number,
    default: 0,
    min: 0,
    max: 100
  },
  speedScore: {
    type: Number,
    default: 0,
    min: 0,
    max: 100
  },
  overallScore: {
    type: Number,
    default: 0,
    min: 0,
    max: 100
  },
  preAnnotateAcceptRate: {
    type: Number,
    default: 0,
    min: 0,
    max: 100
  },
  preAnnotateModifyRate: {
    type: Number,
    default: 0,
    min: 0,
    max: 100
  },
  preAnnotateRejectRate: {
    type: Number,
    default: 0,
    min: 0,
    max: 100
  },
  avgTimePerDocument: {
    type: Number,
    default: 0
  },
  totalTimeSpent: {
    type: Number,
    default: 0
  },
  lastActiveAt: {
    type: Date,
    default: Date.now
  },
  weeklyStats: [{
    week: String,
    annotations: Number,
    avgScore: Number
  }],
  dailyStats: [{
    date: String,
    annotations: Number,
    avgScore: Number
  }],
  createdAt: {
    type: Date,
    default: Date.now
  },
  updatedAt: {
    type: Date,
    default: Date.now
  }
});

qualityScoreSchema.index({ annotator: 1, taskId: 1 }, { unique: true });

module.exports = mongoose.model('QualityScore', qualityScoreSchema);
