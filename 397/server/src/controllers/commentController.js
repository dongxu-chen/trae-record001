const Comment = require('../models/Comment');
const Template = require('../models/Template');
const Joi = require('joi');

const commentSchema = Joi.object({
  content: Joi.string().min(1).max(1000).required(),
  rating: Joi.number().min(1).max(5).required()
});

exports.getComments = async (req, res) => {
  try {
    const { templateId } = req.params;
    const { page = 1, limit = 10 } = req.query;

    const comments = await Comment.find({ templateId })
      .populate('userId', 'username avatar')
      .populate('replies.userId', 'username avatar')
      .sort({ createdAt: -1 })
      .limit(limit * 1)
      .skip((page - 1) * limit);

    const total = await Comment.countDocuments({ templateId });

    res.json({
      comments,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total,
        pages: Math.ceil(total / limit)
      }
    });
  } catch (error) {
    res.status(500).json({ message: '获取评论失败', error: error.message });
  }
};

exports.createComment = async (req, res) => {
  try {
    const { error } = commentSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ message: error.details[0].message });
    }

    const { templateId } = req.params;
    const { content, rating } = req.body;

    const template = await Template.findById(templateId);
    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }

    const existingComment = await Comment.findOne({
      templateId,
      userId: req.user._id
    });

    if (existingComment) {
      return res.status(400).json({ message: '您已对此模板发表过评论' });
    }

    const comment = new Comment({
      templateId,
      userId: req.user._id,
      content,
      rating
    });

    await comment.save();
    await comment.populate('userId', 'username avatar');

    const totalRating = template.rating * template.ratingCount + rating;
    template.ratingCount += 1;
    template.rating = totalRating / template.ratingCount;
    await template.save();

    res.status(201).json({
      message: '评论发表成功',
      comment
    });
  } catch (error) {
    res.status(500).json({ message: '发表评论失败', error: error.message });
  }
};

exports.replyComment = async (req, res) => {
  try {
    const { commentId } = req.params;
    const { content } = req.body;

    if (!content || content.length > 500) {
      return res.status(400).json({ message: '回复内容不能为空且不能超过500字' });
    }

    const comment = await Comment.findById(commentId);
    if (!comment) {
      return res.status(404).json({ message: '评论不存在' });
    }

    comment.replies.push({
      userId: req.user._id,
      content
    });

    await comment.save();
    await comment.populate('replies.userId', 'username avatar');

    res.json({
      message: '回复成功',
      reply: comment.replies[comment.replies.length - 1]
    });
  } catch (error) {
    res.status(500).json({ message: '回复失败', error: error.message });
  }
};

exports.deleteComment = async (req, res) => {
  try {
    const { commentId } = req.params;

    const comment = await Comment.findById(commentId);
    if (!comment) {
      return res.status(404).json({ message: '评论不存在' });
    }

    if (comment.userId.toString() !== req.user._id.toString() && req.user.role !== 'admin') {
      return res.status(403).json({ message: '无权限删除此评论' });
    }

    await Comment.findByIdAndDelete(commentId);
    res.json({ message: '评论删除成功' });
  } catch (error) {
    res.status(500).json({ message: '删除评论失败', error: error.message });
  }
};
