const express = require('express');
const { auth, requireRole } = require('../middleware/auth');
const reviewStatsService = require('../services/reviewStatsService');

const router = express.Router();

router.get('/reviewer/overview', auth, requireRole(['reviewer', 'admin']), async (req, res) => {
  try {
    const { startDate, endDate, period } = req.query;

    const stats = await reviewStatsService.getReviewerStats(req.user.id, {
      startDate: startDate ? new Date(startDate) : undefined,
      endDate: endDate ? new Date(endDate) : undefined
    });

    const workload = await reviewStatsService.getReviewerWorkload(
      req.user.id,
      period || 'month'
    );

    const efficiency = await reviewStatsService.getReviewerEfficiency(req.user.id);

    const aiStats = await reviewStatsService.getAISuggestionStats(req.user.id);

    res.json({
      stats,
      workload,
      efficiency,
      aiStats
    });
  } catch (error) {
    console.error('Reviewer overview error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/reviewer/workload', auth, requireRole(['reviewer', 'admin']), async (req, res) => {
  try {
    const { period = 'month' } = req.query;
    const workload = await reviewStatsService.getReviewerWorkload(req.user.id, period);
    res.json(workload);
  } catch (error) {
    console.error('Get workload error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/reviewer/efficiency', auth, requireRole(['reviewer', 'admin']), async (req, res) => {
  try {
    const efficiency = await reviewStatsService.getReviewerEfficiency(req.user.id);
    res.json(efficiency);
  } catch (error) {
    console.error('Get efficiency error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/document/:documentId', auth, async (req, res) => {
  try {
    const stats = await reviewStatsService.getDocumentStats(req.params.documentId);
    res.json(stats);
  } catch (error) {
    console.error('Get document stats error:', error);
    if (error.message === 'Document not found') {
      return res.status(404).json({ message: error.message });
    }
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/team', auth, requireRole(['admin']), async (req, res) => {
  try {
    const { startDate, endDate } = req.query;
    const teamIds = req.query.teamIds ? JSON.parse(req.query.teamIds) : null;
    
    const stats = await reviewStatsService.getTeamStats(
      teamIds,
      startDate ? new Date(startDate) : new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
      endDate ? new Date(endDate) : new Date()
    );

    res.json(stats);
  } catch (error) {
    console.error('Get team stats error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/ai-suggestions', auth, async (req, res) => {
  try {
    const stats = await reviewStatsService.getAISuggestionStats(req.user.id);
    res.json(stats);
  } catch (error) {
    console.error('Get AI stats error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/overall', auth, requireRole(['admin']), async (req, res) => {
  try {
    const stats = await reviewStatsService.getOverallStats();
    res.json(stats);
  } catch (error) {
    console.error('Get overall stats error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

module.exports = router;
