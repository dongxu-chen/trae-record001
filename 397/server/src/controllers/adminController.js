const Template = require('../models/Template');
const Comment = require('../models/Comment');
const User = require('../models/User');

exports.getPendingTemplates = async (req, res) => {
  try {
    const { page = 1, limit = 20 } = req.query;

    if (req.user.role !== 'admin') {
      return res.status(403).json({ message: '无权限访问' });
    }

    const templates = await Template.find({ status: 'pending' })
      .populate('author', 'username avatar email')
      .sort({ createdAt: -1 })
      .limit(limit * 1)
      .skip((page - 1) * limit);

    const total = await Template.countDocuments({ status: 'pending' });

    res.json({
      templates,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total,
        pages: Math.ceil(total / limit)
      }
    });
  } catch (error) {
    res.status(500).json({ message: '获取待审核模板失败', error: error.message });
  }
};

exports.approveTemplate = async (req, res) => {
  try {
    const { id } = req.params;
    const { note = '' } = req.body;

    if (req.user.role !== 'admin') {
      return res.status(403).json({ message: '无权限操作' });
    }

    const template = await Template.findById(id);
    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }

    if (template.status !== 'pending') {
      return res.status(400).json({ message: '此模板无需审核' });
    }

    template.status = 'approved';
    template.reviewNote = note;
    template.reviewedAt = new Date();
    template.reviewedBy = req.user._id;

    await template.save();

    res.json({
      message: '模板审核通过',
      template
    });
  } catch (error) {
    res.status(500).json({ message: '审核失败', error: error.message });
  }
};

exports.rejectTemplate = async (req, res) => {
  try {
    const { id } = req.params;
    const { reason = '' } = req.body;

    if (req.user.role !== 'admin') {
      return res.status(403).json({ message: '无权限操作' });
    }

    const template = await Template.findById(id);
    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }

    if (template.status !== 'pending') {
      return res.status(400).json({ message: '此模板无需审核' });
    }

    template.status = 'rejected';
    template.rejectReason = reason;
    template.reviewedAt = new Date();
    template.reviewedBy = req.user._id;

    await template.save();

    res.json({
      message: '模板已拒绝',
      template
    });
  } catch (error) {
    res.status(500).json({ message: '拒绝失败', error: error.message });
  }
};

exports.getTemplateReviewStatus = async (req, res) => {
  try {
    const { id } = req.params;

    const template = await Template.findById(id)
      .populate('reviewedBy', 'username');

    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }

    if (template.author.toString() !== req.user._id.toString() && req.user.role !== 'admin') {
      return res.status(403).json({ message: '无权限查看' });
    }

    res.json({
      status: template.status,
      reviewNote: template.reviewNote || '',
      rejectReason: template.rejectReason || '',
      reviewedAt: template.reviewedAt || null,
      reviewedBy: template.reviewedBy || null,
      submittedAt: template.createdAt
    });
  } catch (error) {
    res.status(500).json({ message: '获取审核状态失败', error: error.message });
  }
};

exports.getStatistics = async (req, res) => {
  try {
    if (req.user.role !== 'admin') {
      return res.status(403).json({ message: '无权限访问' });
    }

    const totalTemplates = await Template.countDocuments();
    const pendingTemplates = await Template.countDocuments({ status: 'pending' });
    const approvedTemplates = await Template.countDocuments({ status: 'approved' });
    const rejectedTemplates = await Template.countDocuments({ status: 'rejected' });
    const totalUsers = await User.countDocuments();
    const totalComments = await Comment.countDocuments();

    const categoryStats = await Template.aggregate([
      { $match: { status: 'approved' } },
      {
        $group: {
          _id: '$category',
          count: { $sum: 1 },
          avgRating: { $avg: '$rating' },
          totalDownloads: { $sum: '$downloadCount' }
        }
      }
    ]);

    const dailyStats = await Template.aggregate([
      {
        $group: {
          _id: { $dateToString: { format: '%Y-%m-%d', date: '$createdAt' } },
          count: { $sum: 1 }
        }
      },
      { $sort: { _id: -1 } },
      { $limit: 7 }
    ]);

    res.json({
      overview: {
        totalTemplates,
        pendingTemplates,
        approvedTemplates,
        rejectedTemplates,
        totalUsers,
        totalComments
      },
      categoryStats,
      dailyStats
    });
  } catch (error) {
    res.status(500).json({ message: '获取统计数据失败', error: error.message });
  }
};
