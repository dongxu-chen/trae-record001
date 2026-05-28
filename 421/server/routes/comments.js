const express = require('express');
const { auth } = require('../middleware/auth');
const Comment = require('../models/Comment');
const Document = require('../models/Document');

const router = express.Router();

router.post('/', auth, async (req, res) => {
  try {
    const { documentId, revisionId, content, startPos, endPos, selectedText } = req.body;

    const document = await Document.findOne({ docId: documentId });
    if (!document) {
      return res.status(404).json({ message: 'Document not found' });
    }

    const comment = new Comment({
      document: document._id,
      author: req.user.id,
      revision: revisionId,
      content,
      startPos,
      endPos,
      selectedText
    });

    await comment.save();
    await comment.populate('author', 'username');

    res.status(201).json(comment);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/document/:docId', auth, async (req, res) => {
  try {
    const document = await Document.findOne({ docId: req.params.docId });
    if (!document) {
      return res.status(404).json({ message: 'Document not found' });
    }

    const comments = await Comment.find({ document: document._id })
      .populate('author', 'username')
      .populate('resolvedBy', 'username')
      .populate('replies.author', 'username')
      .sort({ createdAt: -1 });

    res.json(comments);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/:commentId/reply', auth, async (req, res) => {
  try {
    const { content } = req.body;
    const comment = await Comment.findById(req.params.commentId);
    
    if (!comment) {
      return res.status(404).json({ message: 'Comment not found' });
    }

    comment.replies.push({
      author: req.user.id,
      content
    });

    await comment.save();
    await comment.populate('replies.author', 'username');

    res.json(comment);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/:commentId/resolve', auth, async (req, res) => {
  try {
    const comment = await Comment.findById(req.params.commentId);
    
    if (!comment) {
      return res.status(404).json({ message: 'Comment not found' });
    }

    comment.resolved = true;
    comment.resolvedBy = req.user.id;
    comment.resolvedAt = new Date();

    await comment.save();
    await comment.populate('author', 'username');
    await comment.populate('resolvedBy', 'username');

    res.json(comment);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.delete('/:commentId', auth, async (req, res) => {
  try {
    const comment = await Comment.findById(req.params.commentId);
    
    if (!comment) {
      return res.status(404).json({ message: 'Comment not found' });
    }

    if (comment.author.toString() !== req.user.id) {
      return res.status(403).json({ message: 'Not authorized' });
    }

    await Comment.findByIdAndDelete(req.params.commentId);
    res.json({ message: 'Comment deleted' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

module.exports = router;
