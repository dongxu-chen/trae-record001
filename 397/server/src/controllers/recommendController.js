const Template = require('../models/Template');
const ViewHistory = require('../models/ViewHistory');
const Download = require('../models/Download');
const Favorite = require('../models/Favorite');

exports.getRecommendations = async (req, res) => {
  try {
    const { limit = 8, type = 'hybrid' } = req.query;
    const userId = req.user._id;

    let recommendations = [];

    switch (type) {
      case 'history':
        recommendations = await getHistoryBasedRecommendations(userId, parseInt(limit));
        break;
      case 'popular':
        recommendations = await getPopularRecommendations(parseInt(limit));
        break;
      case 'similar':
        recommendations = await getSimilarRecommendations(userId, parseInt(limit));
        break;
      case 'hybrid':
      default:
        recommendations = await getHybridRecommendations(userId, parseInt(limit));
        break;
    }

    res.json({
      recommendations,
      type,
      count: recommendations.length
    });
  } catch (error) {
    res.status(500).json({ message: '获取推荐失败', error: error.message });
  }
};

const getHistoryBasedRecommendations = async (userId, limit) => {
  const viewHistory = await ViewHistory.find({ userId })
    .sort({ viewedAt: -1 })
    .limit(20)
    .populate('templateId', 'category tags _id');

  if (viewHistory.length === 0) {
    return getPopularRecommendations(limit);
  }

  const categoryCounts = {};
  const tagCounts = {};
  const viewedTemplateIds = new Set();

  viewHistory.forEach(vh => {
    if (!vh.templateId) return;
    viewedTemplateIds.add(vh.templateId._id.toString());
    
    categoryCounts[vh.templateId.category] = (categoryCounts[vh.templateId.category] || 0) + 1;
    vh.templateId.tags?.forEach(tag => {
      tagCounts[tag] = (tagCounts[tag] || 0) + 1;
    });
  });

  const topCategories = Object.entries(categoryCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([cat]) => cat);

  const topTags = Object.entries(tagCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([tag]) => tag);

  const query = {
    status: 'approved',
    _id: { $nin: Array.from(viewedTemplateIds) }
  };

  if (topCategories.length > 0) {
    query.category = { $in: topCategories };
  }

  let templates = await Template.find(query)
    .populate('author', 'username avatar')
    .sort({ rating: -1, downloadCount: -1, viewCount: -1 })
    .limit(limit * 2);

  if (templates.length < limit) {
    const additionalTemplates = await Template.find({
      status: 'approved',
      _id: { $nin: [...viewedTemplateIds, ...templates.map(t => t._id.toString())] }
    })
      .populate('author', 'username avatar')
      .sort({ rating: -1, downloadCount: -1 })
      .limit(limit - templates.length);
    
    templates = [...templates, ...additionalTemplates];
  }

  return templates.slice(0, limit).map(t => ({
    ...t.toObject(),
    reason: getRecommendationReason(t, topCategories, topTags)
  }));
};

const getPopularRecommendations = async (limit) => {
  const templates = await Template.find({ status: 'approved' })
    .populate('author', 'username avatar')
    .sort({ downloadCount: -1, viewCount: -1, rating: -1 })
    .limit(limit);

  return templates.map(t => ({
    ...t.toObject(),
    reason: '热门推荐'
  }));
};

const getSimilarRecommendations = async (userId, limit) => {
  const favorites = await Favorite.find({ userId })
    .populate('templateId', 'category tags _id')
    .limit(10);

  const downloads = await Download.find({ userId })
    .populate('templateId', 'category tags _id')
    .limit(10);

  const allInteractions = [...favorites, ...downloads];

  if (allInteractions.length === 0) {
    return getPopularRecommendations(limit);
  }

  const categories = new Set();
  const tags = new Set();
  const interactedIds = new Set();

  allInteractions.forEach(item => {
    if (!item.templateId) return;
    interactedIds.add(item.templateId._id.toString());
    categories.add(item.templateId.category);
    item.templateId.tags?.forEach(tag => tags.add(tag));
  });

  const templates = await Template.find({
    status: 'approved',
    _id: { $nin: Array.from(interactedIds) },
    $or: [
      { category: { $in: Array.from(categories) } },
      { tags: { $in: Array.from(tags) } }
    ]
  })
    .populate('author', 'username avatar')
    .sort({ rating: -1 })
    .limit(limit);

  return templates.map(t => ({
    ...t.toObject(),
    reason: '猜你喜欢'
  }));
};

const getHybridRecommendations = async (userId, limit) => {
  const historyRecs = await getHistoryBasedRecommendations(userId, Math.ceil(limit * 0.5));
  const popularRecs = await getPopularRecommendations(Math.ceil(limit * 0.3));
  const similarRecs = await getSimilarRecommendations(userId, Math.ceil(limit * 0.2));

  const seenIds = new Set();
  const combined = [];

  [...historyRecs, ...similarRecs, ...popularRecs].forEach(rec => {
    if (!seenIds.has(rec._id.toString())) {
      seenIds.add(rec._id.toString());
      combined.push(rec);
    }
  });

  return combined.slice(0, limit);
};

const getRecommendationReason = (template, topCategories, topTags) => {
  if (topCategories.includes(template.category)) {
    return `基于您浏览的${getCategoryLabel(template.category)}类模板推荐`;
  }
  
  const matchingTags = template.tags?.filter(tag => topTags.includes(tag)) || [];
  if (matchingTags.length > 0) {
    return `包含您感兴趣的标签: ${matchingTags.slice(0, 2).join(', ')}`;
  }
  
  return '为您推荐';
};

const getCategoryLabel = (category) => {
  const labels = {
    operation: '运营',
    sales: '销售',
    finance: '财务',
    ops: '运维'
  };
  return labels[category] || category;
};

exports.getViewHistory = async (req, res) => {
  try {
    const { page = 1, limit = 20 } = req.query;

    const history = await ViewHistory.find({ userId: req.user._id })
      .populate({
        path: 'templateId',
        populate: { path: 'author', select: 'username avatar' }
      })
      .sort({ viewedAt: -1 })
      .limit(limit * 1)
      .skip((page - 1) * limit);

    const total = await ViewHistory.countDocuments({ userId: req.user._id });

    res.json({
      history: history.filter(h => h.templateId),
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total,
        pages: Math.ceil(total / limit)
      }
    });
  } catch (error) {
    res.status(500).json({ message: '获取浏览历史失败', error: error.message });
  }
};

exports.recordView = async (req, res) => {
  try {
    const { templateId } = req.params;
    const { duration = 0 } = req.body;

    const template = await Template.findById(templateId);
    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }

    const existingView = await ViewHistory.findOne({
      templateId,
      userId: req.user._id
    }).sort({ viewedAt: -1 });

    const now = new Date();
    const shouldCreateNew = !existingView || 
      (now - existingView.viewedAt) > 30 * 60 * 1000;

    if (shouldCreateNew) {
      const viewHistory = new ViewHistory({
        templateId,
        userId: req.user._id,
        duration
      });
      await viewHistory.save();
    } else if (duration > 0) {
      existingView.duration += duration;
      existingView.viewedAt = now;
      await existingView.save();
    }

    res.json({ message: '浏览记录已更新' });
  } catch (error) {
    res.status(500).json({ message: '记录浏览失败', error: error.message });
  }
};
