const express = require('express');
const { auth, requireRole } = require('../middleware/auth');
const Document = require('../models/Document');
const Revision = require('../models/Revision');
const crypto = require('crypto');

const router = express.Router();

router.post('/', auth, async (req, res) => {
  try {
    const { title, content, reviewers } = req.body;
    
    const docId = crypto.randomUUID();
    
    const document = new Document({
      title,
      content: content || '',
      docId,
      author: req.user.id,
      collaborators: [req.user.id],
      reviewers: reviewers || [],
      status: 'draft'
    });

    await document.save();
    await document.populate('author', 'username');
    await document.populate('reviewers', 'username');

    res.status(201).json(document);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/', auth, async (req, res) => {
  try {
    const documents = await Document.find({
      $or: [
        { author: req.user.id },
        { collaborators: req.user.id },
        { reviewers: req.user.id }
      ]
    })
      .populate('author', 'username')
      .populate('reviewers', 'username')
      .sort({ updatedAt: -1 });

    res.json(documents);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/:docId', auth, async (req, res) => {
  try {
    const document = await Document.findOne({ docId: req.params.docId })
      .populate('author', 'username')
      .populate('collaborators', 'username')
      .populate('reviewers', 'username');

    if (!document) {
      return res.status(404).json({ message: 'Document not found' });
    }

    res.json(document);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.put('/:docId', auth, async (req, res) => {
  try {
    const { title, content, reviewers, status } = req.body;
    
    const document = await Document.findOne({ docId: req.params.docId });
    if (!document) {
      return res.status(404).json({ message: 'Document not found' });
    }

    if (document.author.toString() !== req.user.id && 
        !document.collaborators.includes(req.user.id)) {
      return res.status(403).json({ message: 'Not authorized' });
    }

    const updatedDoc = await Document.findOneAndUpdate(
      { docId: req.params.docId },
      { title, content, reviewers, status },
      { new: true }
    )
      .populate('author', 'username')
      .populate('reviewers', 'username');

    res.json(updatedDoc);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.delete('/:docId', auth, async (req, res) => {
  try {
    const document = await Document.findOne({ docId: req.params.docId });
    if (!document) {
      return res.status(404).json({ message: 'Document not found' });
    }

    if (document.author.toString() !== req.user.id) {
      return res.status(403).json({ message: 'Not authorized' });
    }

    await Document.findOneAndDelete({ docId: req.params.docId });
    await Revision.deleteMany({ document: document._id });

    res.json({ message: 'Document deleted' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/:docId/revisions', auth, async (req, res) => {
  try {
    const document = await Document.findOne({ docId: req.params.docId });
    if (!document) {
      return res.status(404).json({ message: 'Document not found' });
    }

    const revisions = await Revision.find({ document: document._id })
      .populate('author', 'username')
      .populate('reviewedBy', 'username')
      .sort({ createdAt: -1 });

    res.json(revisions);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/:docId/submit-review', auth, async (req, res) => {
  try {
    const document = await Document.findOne({ docId: req.params.docId });
    if (!document) {
      return res.status(404).json({ message: 'Document not found' });
    }

    const isAuthor = document.author.toString() === req.user.id;
    const isCollaborator = document.collaborators.includes(req.user.id);
    
    if (!isAuthor && !isCollaborator) {
      return res.status(403).json({ message: 'Not authorized to submit for review' });
    }

    document.status = 'in_review';
    await document.save();

    const otController = require('../controllers/otController');
    await otController.notifyWorkflowChange(req.params.docId, 'document_submitted', {});

    res.json({ message: 'Document submitted for review', document });
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

module.exports = router;
