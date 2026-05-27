const Template = require('../models/Template');
const Favorite = require('../models/Favorite');
const Download = require('../models/Download');

exports.getMyTemplates = async (req, res) => {
  try {
    const { page = 1, limit = 12 } = req.query;

    const templates = await Template.find({ author: req.user._id })
      .sort({ createdAt: -1 })
      .limit(limit * 1)
      .skip((page - 1) * limit);

    const total = await Template.countDocuments({ author: req.user._id });

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
    res.status(500).json({ message: '获取我的模板失败', error: error.message });
  }
};

exports.getFavorites = async (req, res) => {
  try {
    const { page = 1, limit = 12 } = req.query;

    const favorites = await Favorite.find({ userId: req.user._id })
      .populate({
        path: 'templateId',
        populate: { path: 'author', select: 'username avatar' }
      })
      .sort({ createdAt: -1 })
      .limit(limit * 1)
      .skip((page - 1) * limit);

    const templates = favorites.map(f => f.templateId);
    const total = await Favorite.countDocuments({ userId: req.user._id });

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
    res.status(500).json({ message: '获取收藏失败', error: error.message });
  }
};

exports.addFavorite = async (req, res) => {
  try {
    const { id } = req.params;

    const template = await Template.findById(id);
    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }

    const existingFavorite = await Favorite.findOne({
      userId: req.user._id,
      templateId: id
    });

    if (existingFavorite) {
      return res.status(400).json({ message: '已收藏此模板' });
    }

    const favorite = new Favorite({
      userId: req.user._id,
      templateId: id
    });

    await favorite.save();

    res.json({ message: '收藏成功' });
  } catch (error) {
    res.status(500).json({ message: '收藏失败', error: error.message });
  }
};

exports.removeFavorite = async (req, res) => {
  try {
    const { id } = req.params;

    const favorite = await Favorite.findOneAndDelete({
      userId: req.user._id,
      templateId: id
    });

    if (!favorite) {
      return res.status(404).json({ message: '未收藏此模板' });
    }

    res.json({ message: '取消收藏成功' });
  } catch (error) {
    res.status(500).json({ message: '取消收藏失败', error: error.message });
  }
};

exports.getDownloadHistory = async (req, res) => {
  try {
    const { page = 1, limit = 12 } = req.query;

    const downloads = await Download.find({ userId: req.user._id })
      .populate({
        path: 'templateId',
        populate: { path: 'author', select: 'username avatar' }
      })
      .sort({ downloadedAt: -1 })
      .limit(limit * 1)
      .skip((page - 1) * limit);

    const templates = downloads.map(d => d.templateId);
    const total = await Download.countDocuments({ userId: req.user._id });

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
    res.status(500).json({ message: '获取下载历史失败', error: error.message });
  }
};

exports.getStatistics = async (req, res) => {
  try {
    const templateCount = await Template.countDocuments({ author: req.user._id });
    const totalDownloads = await Template.aggregate([
      { $match: { author: req.user._id } },
      { $group: { _id: null, total: { $sum: '$downloadCount' } } }
    ]);
    const totalViews = await Template.aggregate([
      { $match: { author: req.user._id } },
      { $group: { _id: null, total: { $sum: '$viewCount' } } }
    ]);
    const avgRating = await Template.aggregate([
      { $match: { author: req.user._id, ratingCount: { $gt: 0 } } },
      { $group: { _id: null, avg: { $avg: '$rating' } } }
    ]);

    const downloadTrend = await Download.aggregate([
      {
        $lookup: {
          from: 'templates',
          localField: 'templateId',
          foreignField: '_id',
          as: 'template'
        }
      },
      { $match: { 'template.author': req.user._id } },
      {
        $group: {
          _id: { $dateToString: { format: '%Y-%m-%d', date: '$downloadedAt' } },
          count: { $sum: 1 }
        }
      },
      { $sort: { _id: 1 } },
      { $limit: 30 }
    ]);

    res.json({
      statistics: {
        templateCount,
        totalDownloads: totalDownloads[0]?.total || 0,
        totalViews: totalViews[0]?.total || 0,
        avgRating: avgRating[0]?.avg || 0
      },
      downloadTrend
    });
  } catch (error) {
    res.status(500).json({ message: '获取统计数据失败', error: error.message });
  }
};
