const mongoose = require('mongoose');

const notificationSchema = new mongoose.Schema({
  user: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  type: {
    type: String,
    enum: [
      'new_revision',
      'document_submitted',
      'revision_approved',
      'revision_rejected',
      'document_approved',
      'document_rejected',
      'new_comment',
      'comment_replied',
      'comment_resolved'
    ],
    required: true
  },
  title: {
    type: String,
    required: true
  },
  message: {
    type: String,
    required: true
  },
  documentId: {
    type: String
  },
  revisionId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Revision'
  },
  commentId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Comment'
  },
  data: {
    type: Object
  },
  read: {
    type: Boolean,
    default: false
  },
  readAt: {
    type: Date
  }
}, {
  timestamps: true
});

notificationSchema.index({ user: 1, createdAt: -1 });
notificationSchema.index({ user: 1, read: 1 });

module.exports = mongoose.model('Notification', notificationSchema);
