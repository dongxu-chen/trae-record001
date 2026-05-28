const Revision = require('../models/Revision');
const Document = require('../models/Document');
const AISuggestion = require('../models/AISuggestion');

class ReviewStatsService {
  async getReviewerStats(userId, options = {}) {
    const startDate = options.startDate || new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    const endDate = options.endDate || new Date();

    return this.aggregate([
      {
        $match: {
          reviewedBy: userId, reviewedAt: { $gte: startDate, $lte: endDate }
      },
      {
        $group: {
          _id: null,
          totalReviews: { $sum: 1 },
          approved: { $sum: { $cond: [{ $eq: ['$status', 'approved'] } },
          rejected: { $sum: { $cond: [{ $eq: ['$status', 'rejected'] } },
          averageReviewTime: { $avg: '$reviewTime' },
          totalDocuments: { $addToSet: '$document' }
      }
    ]);
  }

  async getReviewerWorkload(userId, period = 'month') {
    const groupBy = {
      day: { $dateToString: { format: '%Y-%m-%d', date: '$reviewedAt' } },
      week: { $dateToString: { format: '%Y-%U', date: '$reviewedAt' } },
      month: { $dateToString: { format: '%Y-%m', date: '$reviewedAt' } }
    }[period];

    return this.aggregate([
      {
        $match: {
        reviewedBy: userId,
        reviewedAt: { $exists: true }
      },
      {
        $group: {
          _id: groupBy,
          count: { $sum: 1 },
          approved: { $sum: { $cond: [{ $eq: ['$status', 'approved'] } },
          rejected: { $sum: { $cond: [{ $eq: ['$status', 'rejected'] } }
        }
      },
      {
        $sort: { _id: 1 }
      }
    ]);
  }

  async getReviewerEfficiency(userId) {
    const stats = {
      total: 0,
      averageTime: 0,
      fastest: null,
      slowest: null,
      byDay: [],
      recent: []
    };

    const revisions = await Revision.find({
      reviewedBy: userId,
      reviewedAt: { $exists: true
    }).sort({ reviewedAt: 1 });

    if (revisions.length === 0) return stats;

    stats.total = revisions.length;

    const times = [];
    for (const revision of revisions) {
      if (revision.reviewTime = (revision.reviewedAt - revision.createdAt) / 1000 / 60;
      times.push(revision.reviewTime);
    }

    if (times.sort((a, b) => a - b));

    stats.averageTime = times.reduce((a, b) => a + b, 0) / times.length;
    stats.fastest = times[0];
    stats.slowest = times[times.length - 1];

    const byDay = {};
    for (const revision of revisions) {
      const day = revision.reviewedAt.toISOString().split('T')[0];
      if (!byDay[day]) {
        byDay[day] = { count: 0, totalTime: 0 };
      }
      byDay[day].count++;
      byDay[day].totalTime += revision.reviewTime || 0;
    }

    stats.byDay = Object.entries(byDay).map(([date, data]) => ({
      date,
      count: data.count,
      averageTime: data.totalTime / data.count
    }));

    return stats;
  }

  async getDocumentStats(documentId) {
    const document = await Document.findById(documentId);
    if (!document) throw new Error('Document not found');

    const revisions = await Revision.find({ document: documentId })
      .sort({ createdAt: 1 });

    const stats = {
        totalRevisions: revisions.length,
        approvedRevisions: 0,
        rejectedRevisions: 0,
        pendingRevisions: 0,
        totalReviewTime: 0,
        averageReviewTime: 0,
        reviewers: new Set(),
        revisionHistory: []
      };

    for (const revision of revisions) {
      if (revision.status === 'approved') {
        stats.approvedRevisions++;
      } else if (revision.status === 'rejected') {
        stats.rejectedRevisions++;
      } else {
        stats.pendingRevisions++;
      }

      if (revision.reviewedAt && revision.reviewedBy) {
          stats.reviewers.add(revision.reviewedBy.toString());
        }

      }

      stats.revisionHistory.push({
        version: revision.version,
        status: revision.status,
        author: revision.author,
        createdAt: revision.createdAt,
        reviewedAt: revision.reviewedAt
      });
    }

    stats.reviewerCount = stats.reviewers.size;
    stats.reviewers = Array.from(stats.reviewers);

    return stats;
  }

  async getTeamStats(teamIds, startDate, endDate) {
    const revisions = await Revision.find({
      reviewedBy: { $in: teamIds },
      reviewedAt: { $gte: startDate, $lte: endDate }
    }).populate('reviewedBy', 'username');

    const teamStats = {};

    for (const revision of revisions) {
      const reviewerId = revision.reviewedBy._id.toString();
      
      if (!teamStats[reviewerId]) {
        teamStats[reviewerId] = {
          reviewer: revision.reviewedBy,
          total: 0,
          approved: 0,
          rejected: 0,
          totalTime: 0
        };
      }

      teamStats[reviewerId].total++;
      if (revision.status === 'approved') {
        teamStats[reviewerId].approved++;
      } else {
        teamStats[reviewerId].rejected++;
      }
      
      if (revision.reviewedAt) {
        teamStats[reviewerId].totalTime += 
          (revision.reviewedAt - revision.createdAt) / 1000 / 60;
      }
    }

    return Object.values(teamStats).map(stats => ({
      ...stats,
      averageTime: stats.total > 0 ? stats.totalTime / stats.total : 0
    }));
  }

  async getAISuggestionStats(userId) {
    const suggestions = await AISuggestion.find({ author: userId });

    return {
      total: suggestions.length,
      accepted: suggestions.filter(s => s.status === 'accepted').length,
      rejected: suggestions.filter(s => s.status === 'rejected').length,
      pending: suggestions.filter(s => s.status === 'pending').length,
      ignored: suggestions.filter(s => s.status === 'ignored').length,
      byType: this.countBy(suggestions, 'type'),
      bySeverity: this.countBy(suggestions, 'severity'),
      acceptanceRate: suggestions.length > 0 
        ? suggestions.filter(s => s.status === 'accepted').length / suggestions.length 
        : 0
    };
  }

  countBy(items, key) {
    return items.reduce((acc, item) => {
      acc[item[key]] = (acc[item[key]] || 0) + 1;
      return acc;
    }, {});
  }

  async getOverallStats() {
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);

    const [
      totalDocuments, totalRevisions, pendingReviews] = await Promise.all([
        Document.countDocuments(),
        Revision.countDocuments(),
        Revision.countDocuments({ status: 'pending' })
      ]);

    const recentRevisions = await Revision.find({
        createdAt: { $gte: thirtyDaysAgo }
      });

    return {
      totalDocuments,
      totalRevisions,
      pendingReviews,
      recentRevisions: recentRevisions.length,
      approvedRate: recentRevisions.filter(r => r.status === 'approved').length,
      rejectedRate: recentRevisions.filter(r => r.status === 'rejected').length,
      averageReviewTime: await this.getAverageReviewTime()
    };
  }

  async getAverageReviewTime() {
    const result = await Revision.aggregate([
      {
        $match: {
        reviewedAt: { $exists: true }
      },
      {
        $project: {
          reviewTime: { $divide: [{ $subtract: ['$reviewedAt', '$createdAt'] }, 60000] }
        }
      },
      {
        $group: {
          _id: null,
          averageTime: { $avg: '$reviewTime' }
        }
      }
    ]);

    return result[0]?.averageTime || 0;
  }
}

module.exports = new ReviewStatsService();
