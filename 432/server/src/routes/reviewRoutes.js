import express from 'express';
import { v4 as uuidv4 } from 'uuid';
import { generateId } from '../utils/generateId.js';

const router = express.Router();

const reviewSessions = new Map();

const REVIEWER_COLORS = [
  '#165DFF',
  '#FF7D00',
  '#4CAF50',
  '#9C27B0',
  '#00BCD4',
];

router.post('/session', (req, res) => {
  try {
    const { fileId, reviewerName } = req.body;

    if (!fileId || !reviewerName) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    const sessionId = uuidv4();
    const reviewerId = uuidv4();

    const session = {
      sessionId,
      fileId,
      ownerId: reviewerId,
      reviewers: [
        {
          id: reviewerId,
          name: reviewerName,
          color: REVIEWER_COLORS[0],
          role: 'owner',
        },
      ],
      annotations: [],
      status: 'active',
      createdAt: Date.now(),
    };

    reviewSessions.set(sessionId, session);

    res.json({
      sessionId,
      reviewerId,
      session,
    });
  } catch (error) {
    console.error('Create session error:', error);
    res.status(500).json({ error: 'Failed to create session' });
  }
});

router.post('/session/:sessionId/join', (req, res) => {
  try {
    const { sessionId } = req.params;
    const { reviewerName } = req.body;

    const session = reviewSessions.get(sessionId);
    if (!session) {
      return res.status(404).json({ error: 'Session not found' });
    }

    if (session.status !== 'active') {
      return res.status(400).json({ error: 'Session is not active' });
    }

    if (!reviewerName) {
      return res.status(400).json({ error: 'Reviewer name is required' });
    }

    const colorIndex = session.reviewers.length % REVIEWER_COLORS.length;
    const reviewerId = uuidv4();

    const reviewer = {
      id: reviewerId,
      name: reviewerName,
      color: REVIEWER_COLORS[colorIndex],
      role: 'reviewer',
    };

    session.reviewers.push(reviewer);

    res.json({
      sessionId,
      reviewerId,
      session,
    });
  } catch (error) {
    console.error('Join session error:', error);
    res.status(500).json({ error: 'Failed to join session' });
  }
});

router.get('/session/:sessionId', (req, res) => {
  try {
    const { sessionId } = req.params;

    const session = reviewSessions.get(sessionId);
    if (!session) {
      return res.status(404).json({ error: 'Session not found' });
    }

    res.json({
      session,
      annotations: session.annotations,
    });
  } catch (error) {
    console.error('Get session error:', error);
    res.status(500).json({ error: 'Failed to get session' });
  }
});

router.post('/session/:sessionId/annotations', (req, res) => {
  try {
    const { sessionId } = req.params;
    const { annotation, reviewerId } = req.body;

    const session = reviewSessions.get(sessionId);
    if (!session) {
      return res.status(404).json({ error: 'Session not found' });
    }

    if (!annotation || !reviewerId) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    const reviewer = session.reviewers.find((r) => r.id === reviewerId);
    if (!reviewer) {
      return res.status(403).json({ error: 'Reviewer not in session' });
    }

    const annotationWithReviewer = {
      ...annotation,
      reviewerId,
      reviewerName: reviewer.name,
      reviewerColor: reviewer.color,
      id: annotation.id || generateId(),
    };

    session.annotations.push(annotationWithReviewer);

    res.json({ success: true, annotation: annotationWithReviewer });
  } catch (error) {
    console.error('Add annotation error:', error);
    res.status(500).json({ error: 'Failed to add annotation' });
  }
});

router.post('/session/:sessionId/merge', (req, res) => {
  try {
    const { sessionId } = req.params;
    const { selectedIds } = req.body;

    const session = reviewSessions.get(sessionId);
    if (!session) {
      return res.status(404).json({ error: 'Session not found' });
    }

    if (!selectedIds || !Array.isArray(selectedIds)) {
      return res.status(400).json({ error: 'Selected IDs must be an array' });
    }

    const annotationsToMerge = session.annotations.filter((a) =>
      selectedIds.includes(a.id)
    );

    const conflicts = [];
    const mergedAnnotations = [];

    annotationsToMerge.forEach((annotation) => {
      const overlap = mergedAnnotations.some((merged) => {
        if (
          merged.pageIndex === annotation.pageIndex &&
          Math.abs(merged.position.x - annotation.position.x) < 0.05 &&
          Math.abs(merged.position.y - annotation.position.y) < 0.05
        ) {
          return true;
        }
        return false;
      });

      if (overlap) {
        conflicts.push({
          type: 'overlap',
          annotationA: mergedAnnotations.find((m) =>
            m.pageIndex === annotation.pageIndex &&
            Math.abs(m.position.x - annotation.position.x) < 0.05
          ),
          annotationB: annotation,
        });
      } else {
        mergedAnnotations.push(annotation);
      }
    });

    session.status = 'merged';

    res.json({
      mergedAnnotations,
      conflicts,
    });
  } catch (error) {
    console.error('Merge annotations error:', error);
    res.status(500).json({ error: 'Failed to merge annotations' });
  }
});

export default router;
