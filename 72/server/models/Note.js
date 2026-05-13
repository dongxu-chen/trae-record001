const mongoose = require('mongoose');

const wordSchema = new mongoose.Schema({
  word: String,
  start: Number,
  end: Number,
});

const segmentSchema = new mongoose.Schema({
  id: Number,
  start: Number,
  end: Number,
  text: String,
  words: [wordSchema],
  _id: false,
});

const transcriptionDataSchema = new mongoose.Schema({
  text: String,
  segments: [segmentSchema],
  duration: Number,
  language: String,
  _id: false,
});

const noteSchema = new mongoose.Schema({
  transcript: {
    type: String,
    default: '',
  },
  whisperTranscript: {
    type: String,
    default: '',
  },
  audioPath: {
    type: String,
    default: null,
  },
  transcriptionData: {
    type: transcriptionDataSchema,
    default: null,
  },
  duration: {
    type: Number,
    default: 0,
  },
}, {
  timestamps: true,
});

noteSchema.virtual('audioUrl').get(function() {
  if (!this.audioPath) return null;
  return `${process.env.APP_URL || 'http://localhost:5000'}${this.audioPath}`;
});

noteSchema.virtual('allText').get(function() {
  return this.whisperTranscript || this.transcript || '';
});

noteSchema.statics.searchByKeyword = function(keyword) {
  const regex = new RegExp(keyword, 'i');
  return this.find({
    $or: [
      { transcript: regex },
      { whisperTranscript: regex },
      { 'transcriptionData.text': regex },
      { 'transcriptionData.segments.text': regex },
    ],
  }).sort({ createdAt: -1 });
};

noteSchema.set('toJSON', {
  virtuals: true,
});

module.exports = mongoose.model('Note', noteSchema);