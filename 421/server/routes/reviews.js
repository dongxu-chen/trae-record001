const express = require('express');
const { auth, requireRole } = require('../middleware/auth');
const Revision = require('../models/Revision');
const Document = require('../models/Document');
const otController = require('../controllers/otController');

const router = express.Router();

router.post('/:revisionId/approve', auth, requireRole(['reviewer', 'admin']), async (req, res) => {
  try {
    const { comment } = req.body;
    const revision = await otController.applyRevision(
      req.params.revisionId,
      true,
      req.user.id,
      comment
    );

    await revision.populate('author', 'username');
    await revision.populate('reviewedBy', 'username');

    res.json(revision);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/:revisionId/reject', auth, requireRole(['reviewer', 'admin']), async (req, res) => {
  try {
    const { comment } = req.body;
    const revision = await otController.applyRevision(
      req.params.revisionId,
      false,
      req.user.id,
      comment
    );

    await revision.populate('author', 'username');
    await revision.populate('reviewedBy', 'username');

    res.json(revision);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/pending', auth, requireRole(['reviewer', 'admin']), async (req, res) => {
  try {
    const documents = await Document.find({ reviewers: req.user.id, status: 'in_review' })
      .populate('author', 'username')
      .sort({ updatedAt: -1 });

    const revisions = await Revision.find({ status: 'pending' })
      .populate('document')
      .populate('author', 'username')
      .sort({ createdAt: -1 });

    const pendingRevisions = revisions.filter(
      r => r.document && r.document.reviewers.includes(req.user.id)
    );

    res.json({ documents, revisions: pendingRevisions });
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/document/:docId/final-approve', auth, requireRole(['reviewer', 'admin']), async (req, res) => {
  try {
    const { comment } = req.body;
    const document = await Document.findOne({ docId: req.params.docId });
    
    if (!document) {
      return res.status(404).json({ message: 'Document not found' });
    }

    if (!document.reviewers.includes(req.user.id)) {
      return res.status(403).json({ message: 'Not authorized' });
    }

    document.status = 'approved';
    await document.save();

    await otController.notifyWorkflowChange(req.params.docId, 'document_approved', { comment });

    res.json({ message: 'Document approved', document });
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/document/:docId/final-reject', auth, requireRole(['reviewer', 'admin']), async (req, res) => {
  try {
    const { comment } = req.body;
    const document = await Document.findOne({ docId: req.params.docId });
    
    if (!document) {
      return res.status(404).json({ message: 'Document not found' });
    }

    if (!document.reviewers.includes(req.user.id)) {
      return res.status(403).json({ message: 'Not authorized' });
    }

    document.status = 'rejected';
    await document.save();

    await otController.notifyWorkflowChange(req.params.docId, 'document_rejected', { comment });

    res.json({ message: 'Document rejected', document });
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
});

module.exports = router;
