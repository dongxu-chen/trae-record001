const mongoose = require('mongoose');

const entityAnnotationSchema = new mongoose.Schema({
  id: String,
  start: {
    type: Number,
    required: true
  },
  end: {
    type: Number,
    required: true
  },
  text: String,
  label: {
    type: String,
    required: true
  },
  color: String,
  isPreAnnotated: {
    type: Boolean,
    default: false
  },
  confidence: Number
});

const relationAnnotationSchema = new mongoose.Schema({
  id: String,
  sourceId: String,
  targetId: String,
  label: {
    type: String,
    required: true
  },
  color: String,
  isPreAnnotated: {
    type: Boolean,
    default: false
  },
  confidence: Number
});

const eventAnnotationSchema = new mongoose.Schema({
  id: String,
  triggerStart: Number,
  triggerEnd: Number,
  triggerText: String,
  label: {
    type: String,
    required: true
  },
  color: String,
  arguments: [{
    entityId: String,
    role: String
  }],
  isPreAnnotated: {
    type: Boolean,
    default: false
  },
  confidence: Number
});

const annotationSchema = new mongoose.Schema({
  documentId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Document',
    required: true
  },
  taskId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Task',
    required: true
  },
  entities: [entityAnnotationSchema],
  relations: [relationAnnotationSchema],
  events: [eventAnnotationSchema],
  annotator: String,
  comments: String,
  createdAt: {
    type: Date,
    default: Date.now
  },
  updatedAt: {
    type: Date,
    default: Date.now
  }
});

module.exports = mongoose.model('Annotation', annotationSchema);
