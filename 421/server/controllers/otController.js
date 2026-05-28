const Diff = require('diff');
const otEngine = require('../ot/tableAwareOTEngine');
const richTextDiffEngine = require('../ot/richTextDiffEngine');
const Document = require('../models/Document');
const Revision = require('../models/Revision');
const Notification = require('../models/Notification');

class OTController {
  constructor() {
    this.io = null;
    this.shareDB = null;
    this.connection = null;
    this.activeUsers = new Map();
    this.userSockets = new Map();
  }

  initialize(io, shareDB, connection) {
    this.io = io;
    this.shareDB = shareDB;
    this.connection = connection;

    io.on('connection', (socket) => {
      console.log('Client connected:', socket.id);

      socket.on('register-user', ({ userId }) => {
        this.userSockets.set(userId, socket.id);
        socket.userId = userId;
      });

      socket.on('join-document', async ({ docId, userId, username }) => {
        socket.join(docId);
        
        if (!this.activeUsers.has(docId)) {
          this.activeUsers.set(docId, new Map());
        }
        this.activeUsers.get(docId).set(socket.id, { userId, username });
        
        const users = Array.from(this.activeUsers.get(docId).values());
        io.to(docId).emit('active-users', users);
        
        const doc = await Document.findOne({ docId }).populate('author', 'username');
        if (doc) {
          socket.emit('document-sync', {
            content: doc.content,
            richContent: doc.richContent || otEngine.parseToRichContent(doc.content),
            version: doc.version,
            document: doc
          });
        }
      });

      socket.on('operation', async ({ docId, op, userId }) => {
        try {
          const doc = await Document.findOne({ docId });
          if (!doc) return;

          const result = otEngine.applyOperation(docId, op, userId);
          
          const updateData = { 
            content: result.content, 
            version: result.version 
          };
          if (result.richContent) {
            updateData.richContent = result.richContent;
          }
          
          await Document.findOneAndUpdate({ docId }, updateData);

          socket.to(docId).emit('operation', {
            op: result.op,
            userId,
            version: result.version,
            richContent: result.richContent
          });
        } catch (error) {
          console.error('Operation error:', error);
        }
      });

      socket.on('table-operation', async ({ docId, op, userId }) => {
        try {
          const doc = await Document.findOne({ docId });
          if (!doc) return;

          const result = otEngine.applyOperation(docId, op, userId);
          
          await Document.findOneAndUpdate(
            { docId },
            { content: result.content, version: result.version }
          );

          io.to(docId).emit('table-operation', {
            op: result.op,
            userId,
            version: result.version
          });
        } catch (error) {
          console.error('Table operation error:', error);
        }
      });

      socket.on('format-operation', async ({ docId, op, userId }) => {
        try {
          const doc = await Document.findOne({ docId });
          if (!doc) return;

          const result = otEngine.applyOperation(docId, op, userId);
          
          await Document.findOneAndUpdate(
            { docId },
            { 
              content: result.content, 
              richContent: result.richContent,
              version: result.version 
            }
          );

          io.to(docId).emit('format-operation', {
            op: result.op,
            userId,
            version: result.version,
            richContent: result.richContent
          });
        } catch (error) {
          console.error('Format operation error:', error);
        }
      });

      socket.on('save-revision', async (data) => {
        try {
          const revision = await this.createRevision(data);
          io.to(data.documentId).emit('revision-created', revision);
          
          const doc = await Document.findOne({ docId: data.documentId }).populate('reviewers');
          if (doc && doc.reviewers) {
            for (const reviewer of doc.reviewers) {
              this.sendNotification(reviewer._id, {
                type: 'new_revision',
                title: '新修订待审核',
                message: `文档「${doc.title}」有新的修订需要审核`,
                documentId: data.documentId,
                revisionId: revision._id
              });
            }
          }
        } catch (error) {
          console.error('Save revision error:', error);
        }
      });

      socket.on('cursor-position', ({ docId, userId, username, position }) => {
        socket.to(docId).emit('cursor-update', {
          userId,
          username,
          position,
          socketId: socket.id
        });
      });

      socket.on('mark-notification-read', async ({ notificationId, userId }) => {
        try {
          await Notification.findByIdAndUpdate(notificationId, { read: true });
          socket.emit('notification-updated', { notificationId, read: true });
        } catch (error) {
          console.error('Mark notification read error:', error);
        }
      });

      socket.on('disconnect', () => {
        for (const [docId, users] of this.activeUsers) {
          users.delete(socket.id);
          const remainingUsers = Array.from(users.values());
          io.to(docId).emit('active-users', remainingUsers);
        }
        if (socket.userId) {
          this.userSockets.delete(socket.userId);
        }
        console.log('Client disconnected:', socket.id);
      });
    });
  }

  async sendNotification(userId, notificationData) {
    try {
      const notification = new Notification({
        user: userId,
        ...notificationData
      });
      await notification.save();
      await notification.populate('user', 'username');

      const socketId = this.userSockets.get(userId.toString());
      if (socketId) {
        this.io.to(socketId).emit('notification', notification);
      }

      return notification;
    } catch (error) {
      console.error('Send notification error:', error);
    }
  }

  async notifyWorkflowChange(docId, action, data) {
    const doc = await Document.findOne({ docId })
      .populate('author', 'username')
      .populate('reviewers', 'username');
    
    if (!doc) return;

    const notifications = [];

    switch (action) {
      case 'document_submitted':
        for (const reviewer of doc.reviewers) {
          notifications.push(this.sendNotification(reviewer._id, {
            type: 'document_submitted',
            title: '文档提交审核',
            message: `「${doc.title}」已提交审核`,
            documentId: docId,
            data
          }));
        }
        break;

      case 'revision_approved':
        notifications.push(this.sendNotification(doc.author._id, {
          type: 'revision_approved',
          title: '修订已通过',
          message: `您在「${doc.title}」中的修订已被审核通过`,
          documentId: docId,
          revisionId: data.revisionId
        }));
        break;

      case 'revision_rejected':
        notifications.push(this.sendNotification(doc.author._id, {
          type: 'revision_rejected',
          title: '修订被拒绝',
          message: `您在「${doc.title}」中的修订被拒绝`,
          documentId: docId,
          revisionId: data.revisionId,
          comment: data.comment
        }));
        break;

      case 'document_approved':
        notifications.push(this.sendNotification(doc.author._id, {
          type: 'document_approved',
          title: '文档已通过',
          message: `文档「${doc.title}」已审核通过`,
          documentId: docId
        }));
        for (const reviewer of doc.reviewers) {
          notifications.push(this.sendNotification(reviewer._id, {
            type: 'document_approved',
            title: '文档已通过',
            message: `您审核的「${doc.title}」已最终通过`,
            documentId: docId
          }));
        }
        break;

      case 'document_rejected':
        notifications.push(this.sendNotification(doc.author._id, {
          type: 'document_rejected',
          title: '文档被拒绝',
          message: `文档「${doc.title}」审核未通过`,
          documentId: docId,
          comment: data.comment
        }));
        for (const reviewer of doc.reviewers) {
          notifications.push(this.sendNotification(reviewer._id, {
            type: 'document_rejected',
            title: '文档被拒绝',
            message: `您审核的「${doc.title}」已被拒绝`,
            documentId: docId
          }));
        }
        break;

      case 'new_comment':
        if (data.authorId !== doc.author._id.toString()) {
          notifications.push(this.sendNotification(doc.author._id, {
            type: 'new_comment',
            title: '新批注',
            message: `「${doc.title}」有新的批注`,
            documentId: docId,
            commentId: data.commentId
          }));
        }
        break;
    }

    await Promise.all(notifications);

    this.io.to(docId).emit('workflow-update', {
      action,
      documentId: docId,
      data
    });
  }

  async createRevision({ documentId, userId, operations, contentBefore, contentAfter, diff, richContentBefore, richContentAfter }) {
    const doc = await Document.findOne({ docId: documentId });
    if (!doc) throw new Error('Document not found');

    const richDiff = richTextDiffEngine.computeRichDiff(
      contentBefore, 
      contentAfter,
      richContentBefore,
      richContentAfter
    );

    const sideBySideDiff = richTextDiffEngine.generateSideBySideDiff(
      contentBefore,
      contentAfter,
      richContentBefore,
      richContentAfter
    );

    const revision = new Revision({
      document: doc._id,
      author: userId,
      version: doc.version,
      operations,
      diff,
      richDiff: JSON.stringify(richDiff),
      sideBySideDiff: JSON.stringify(sideBySideDiff),
      contentBefore,
      contentAfter,
      richContentBefore,
      richContentAfter,
      status: 'pending'
    });

    await revision.save();
    await revision.populate('author', 'username');

    return revision;
  }

  computeDiff(oldContent, newContent) {
    const changes = Diff.diffChars(oldContent, newContent);
    return JSON.stringify(changes);
  }

  computeRichDiff(oldContent, newContent, oldRichContent, newRichContent) {
    const richDiff = richTextDiffEngine.computeRichDiff(
      oldContent, 
      newContent,
      oldRichContent,
      newRichContent
    );
    return JSON.stringify(richDiff);
  }

  async applyRevision(revisionId, approved, reviewerId, comment = '') {
    const revision = await Revision.findById(revisionId).populate('document');
    if (!revision) throw new Error('Revision not found');

    revision.status = approved ? 'approved' : 'rejected';
    revision.reviewedBy = reviewerId;
    revision.reviewedAt = new Date();
    revision.reviewComment = comment;

    if (approved && revision.document) {
      await Document.findByIdAndUpdate(revision.document._id, {
        content: revision.contentAfter,
        richContent: revision.richContentAfter,
        version: revision.version
      });
    }

    await revision.save();

    if (revision.document) {
      await this.notifyWorkflowChange(revision.document.docId, 
        approved ? 'revision_approved' : 'revision_rejected',
        { revisionId, comment }
      );
    }

    return revision;
  }
}

module.exports = new OTController();
