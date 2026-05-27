const Template = require('../models/Template');
const Download = require('../models/Download');
const Favorite = require('../models/Favorite');
const Comment = require('../models/Comment');
const Rating = require('../models/Rating');
const Joi = require('joi');
const { broadcastTemplateStats, broadcastGlobalStats } = require('../config/websocket');

const templateSchema = Joi.object({
  title: Joi.string().min(1).max(100).required(),
  description: Joi.string().min(1).max(2000).required(),
  category: Joi.string().valid('operation', 'sales', 'finance', 'ops').required(),
  tags: Joi.array().items(Joi.string()),
  complexity: Joi.string().valid('simple', 'medium', 'complex'),
  price: Joi.number().min(0),
  components: Joi.array(),
  layout: Joi.object()
});

exports.getTemplates = async (req, res) => {
  try {
    const {
      page = 1,
      limit = 12,
      category,
      complexity,
      sort = 'createdAt',
      order = 'desc',
      search,
      minRating = 0
    } = req.query;

    const query = { status: 'approved' };
    
    if (category) query.category = category;
    if (complexity) query.complexity = complexity;
    if (minRating) query.rating = { $gte: parseFloat(minRating) };
    if (search) {
      query.$or = [
        { title: { $regex: search, $options: 'i' } },
        { description: { $regex: search, $options: 'i' } },
        { tags: { $in: [new RegExp(search, 'i')] } }
      ];
    }

    const sortOptions = {};
    sortOptions[sort] = order === 'desc' ? -1 : 1;

    const templates = await Template.find(query)
      .populate('author', 'username avatar')
      .sort(sortOptions)
      .limit(limit * 1)
      .skip((page - 1) * limit);

    const total = await Template.countDocuments(query);

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
    res.status(500).json({ message: '获取模板列表失败', error: error.message });
  }
};

exports.getTemplateById = async (req, res) => {
  try {
    const template = await Template.findById(req.params.id)
      .populate('author', 'username avatar bio');

    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }

    template.viewCount += 1;
    await template.save();

    broadcastTemplateStats(req.params.id, {
      viewCount: template.viewCount,
      downloadCount: template.downloadCount,
      rating: template.rating,
      ratingCount: template.ratingCount
    });

    res.json({ template });
  } catch (error) {
    res.status(500).json({ message: '获取模板详情失败', error: error.message });
  }
};

exports.createTemplate = async (req, res) => {
  try {
    const { error } = templateSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ message: error.details[0].message });
    }

    let thumbnail = '';
    let previewImages = [];
    let fileUrl = '';

    if (req.files) {
      if (req.files.thumbnail) {
        thumbnail = `/uploads/${req.files.thumbnail[0].filename}`;
      }
      if (req.files.previewImages) {
        previewImages = req.files.previewImages.map(f => `/uploads/${f.filename}`);
      }
      if (req.files.file) {
        fileUrl = `/uploads/${req.files.file[0].filename}`;
      }
    }

    const template = new Template({
      ...req.body,
      author: req.user._id,
      thumbnail,
      previewImages,
      fileUrl
    });

    await template.save();
    await template.populate('author', 'username avatar');

    res.status(201).json({
      message: '模板创建成功',
      template
    });
  } catch (error) {
    res.status(500).json({ message: '创建模板失败', error: error.message });
  }
};

exports.updateTemplate = async (req, res) => {
  try {
    const template = await Template.findById(req.params.id);
    
    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }

    if (template.author.toString() !== req.user._id.toString() && req.user.role !== 'admin') {
      return res.status(403).json({ message: '无权限修改此模板' });
    }

    const updateData = { ...req.body };
    
    if (req.files) {
      if (req.files.thumbnail) {
        updateData.thumbnail = `/uploads/${req.files.thumbnail[0].filename}`;
      }
      if (req.files.previewImages) {
        updateData.previewImages = req.files.previewImages.map(f => `/uploads/${f.filename}`);
      }
      if (req.files.file) {
        updateData.fileUrl = `/uploads/${req.files.file[0].filename}`;
      }
    }

    const updatedTemplate = await Template.findByIdAndUpdate(
      req.params.id,
      updateData,
      { new: true }
    ).populate('author', 'username avatar');

    res.json({
      message: '模板更新成功',
      template: updatedTemplate
    });
  } catch (error) {
    res.status(500).json({ message: '更新模板失败', error: error.message });
  }
};

exports.deleteTemplate = async (req, res) => {
  try {
    const template = await Template.findById(req.params.id);
    
    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }

    if (template.author.toString() !== req.user._id.toString() && req.user.role !== 'admin') {
      return res.status(403).json({ message: '无权限删除此模板' });
    }

    await Template.findByIdAndDelete(req.params.id);
    await Comment.deleteMany({ templateId: req.params.id });
    await Download.deleteMany({ templateId: req.params.id });
    await Favorite.deleteMany({ templateId: req.params.id });
    await Rating.deleteMany({ templateId: req.params.id });

    res.json({ message: '模板删除成功' });
  } catch (error) {
    res.status(500).json({ message: '删除模板失败', error: error.message });
  }
};

exports.downloadTemplate = async (req, res) => {
  try {
    const template = await Template.findById(req.params.id);
    
    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }

    const existingDownload = await Download.findOne({
      templateId: req.params.id,
      userId: req.user._id
    });

    if (!existingDownload) {
      const download = new Download({
        templateId: req.params.id,
        userId: req.user._id
      });
      await download.save();
      
      template.downloadCount += 1;
      await template.save();

      broadcastTemplateStats(req.params.id, {
        downloadCount: template.downloadCount,
        viewCount: template.viewCount,
        rating: template.rating,
        ratingCount: template.ratingCount
      });
    }

    res.json({
      message: '下载成功',
      downloadUrl: template.fileUrl,
      template: {
        _id: template._id,
        title: template.title,
        components: template.components,
        layout: template.layout
      }
    });
  } catch (error) {
    res.status(500).json({ message: '下载模板失败', error: error.message });
  }
};

exports.rateTemplate = async (req, res) => {
  try {
    const { rating } = req.body;
    
    if (rating < 1 || rating > 5) {
      return res.status(400).json({ message: '评分必须在1-5之间' });
    }

    const template = await Template.findById(req.params.id);
    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }

    const existingRating = await Rating.findOne({
      templateId: req.params.id,
      userId: req.user._id
    });

    if (existingRating) {
      return res.status(400).json({ message: '您已对此模板评分，每个模板只能评分一次' });
    }

    const newRating = new Rating({
      templateId: req.params.id,
      userId: req.user._id,
      rating
    });
    await newRating.save();

    const totalRating = template.rating * template.ratingCount + rating;
    template.ratingCount += 1;
    template.rating = totalRating / template.ratingCount;
    await template.save();

    broadcastTemplateStats(req.params.id, {
      rating: template.rating,
      ratingCount: template.ratingCount,
      downloadCount: template.downloadCount,
      viewCount: template.viewCount
    });

    res.json({
      message: '评分成功',
      rating: template.rating,
      ratingCount: template.ratingCount,
      userRating: rating
    });
  } catch (error) {
    if (error.code === 11000) {
      return res.status(400).json({ message: '您已对此模板评分，每个模板只能评分一次' });
    }
    res.status(500).json({ message: '评分失败', error: error.message });
  }
};

exports.applyTemplate = async (req, res) => {
  try {
    const { mode = 'merge', backup } = req.body;
    const template = await Template.findById(req.params.id);
    
    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }

    if (!['merge', 'overwrite'].includes(mode)) {
      return res.status(400).json({ message: '无效的应用模式' });
    }

    if (mode === 'overwrite' && backup) {
      console.log('备份原始配置:', backup);
    }

    res.json({
      message: `模板${mode === 'merge' ? '合并' : '覆盖'}应用成功`,
      mode,
      template: {
        _id: template._id,
        title: template.title,
        components: template.components,
        layout: template.layout
      },
      backup: backup || null,
      appliedAt: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ message: '应用模板失败', error: error.message });
  }
};

exports.getUserRating = async (req, res) => {
  try {
    const rating = await Rating.findOne({
      templateId: req.params.id,
      userId: req.user._id
    });

    res.json({
      hasRated: !!rating,
      userRating: rating?.rating || null
    });
  } catch (error) {
    res.status(500).json({ message: '获取用户评分失败', error: error.message });
  }
};
